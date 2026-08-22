"""tfim_dynamics_sweep.py — cross-topology FCE validation (Spec 12/13 pipeline).

Trains across several TFIM graphs (topologies) at ONE shared, unknown field
strength ALPHA_STAR, extracts each graph's b(x_t) via Spec 4's real shot-based
extraction (Spec-11-execution-repaired), fits w(alpha*) via LASSO
(fourierlearn.cross_topology), and predicts on a held-out graph -- compared
against that graph's own Trotter ceiling and true continuous-time exact
dynamics across a time sweep.

Three reference quantities per time point, each independently sourced so
none can silently collapse into another:

  * "Exact"   -- true continuous dynamics, e^{-iHt}|0>, H built directly as a
                 dense matrix (numpy/scipy) from the graph's OWN edges and
                 ALPHA_STAR. Deliberately NOT built via fourierlearn.reference
                 or fourierlearn._exact_dynamics.
  * "Trotter" -- the held-out graph's OWN compiled circuit (this sweep's r),
                 evaluated exactly (fourierlearn.reference.coefficients,
                 zero shot noise) at alpha=ALPHA_STAR.
  * "PAC"     -- fit_cross_topology_lasso on shot-based b(x_t) (Spec 4
                 extraction) across TRAINING graphs, labeled by each graph's
                 TRUE continuous exact_continuous_expectation at ALPHA_STAR.

NOT fourierlearn.learn (the flipped-concept path) and NOT the field baked
into models.py's PhysicalModelDescription -- build_row_ir constructs
GroupSpecs directly so the field stays a genuinely unbound, tied Parameter.

device/backend: pass a pre-configured AerSimulator via SIMULATOR below for
server runs (Constitution Article V.3 -- benchmark fresh on this codebase).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
from scipy.linalg import expm

from fourierlearn.cross_topology import (
    CrossTopologyRow,
    fit_cross_topology_lasso,
    predict,
)
from fourierlearn.encodings.trotter import (
    CouplingGroup,
    CouplingGroupTerm,
    FixedCouplingGroup,
    mixed_trotter_frontend,
)
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.ir import PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients

# ---- Safely defining data models locally to avoid models.py import errors ----
@dataclass(frozen=True)
class TFIMEdge:
    site_i: int
    site_j: int
    coupling_strength: float

@dataclass(frozen=True)
class TFIMGraph:
    num_sites: int
    edges: tuple[TFIMEdge, ...]
    field_strength: float

# ---- configuration ----------------------------------------------------------
N_SITES = 3
R_STEPS = 5
SHOTS = 20_000
SEED = 7
ALPHA_STAR = 1.0                       # true field strength: known to THIS SCRIPT
N_TRAIN_GRAPHS = 6
T_VALUES = np.linspace(0.27, 3.0, 12)  # sweep to t~3s
OBSERVABLE = SparsePauliOp("I" * (N_SITES - 1) + "Z")

# Pass a pre-configured AerSimulator for the server run
SIMULATOR = AerSimulator(device="CPU")


# ---- IR construction: edges fixed, field the one shared encoded parameter --

def build_row_ir(graph: TFIMGraph, tau: float, r: int, observable: SparsePauliOp) -> PauliEncodedCircuitIR:
    """One graph's IR: its OWN edges as FixedCouplingGroups, the transverse field as the
    ONE CouplingGroup shared identically across EVERY graph in the sweep.
    """
    fixed_groups = tuple(
        FixedCouplingGroup(
            terms=(CouplingGroupTerm(pauli="ZZ", qubits=(edge.site_i, edge.site_j), weight=1.0),),
            value=edge.coupling_strength,
        )
        for edge in graph.edges
    )
    field_group = CouplingGroup(
        label="field",
        terms=tuple(
            CouplingGroupTerm(pauli="X", qubits=(site,), weight=1.0)
            for site in range(graph.num_sites)
        ),
    )
    return mixed_trotter_frontend(
        num_qubits=graph.num_sites,
        group_specs=fixed_groups + (field_group,),
        tau=tau,
        r=r,
        observable=observable,
    )


# ---- true continuous-time dynamics (independent of Trotter, built here) ---

def _pauli_label(active: dict[int, str], n: int) -> str:
    """Qiskit little-endian label: rightmost character = qubit 0."""
    chars = ["I"] * n
    for qubit, letter in active.items():
        chars[n - 1 - qubit] = letter
    return "".join(chars)


def _dense_hamiltonian(graph: TFIMGraph, alpha: float) -> np.ndarray:
    """H = sum_edges (coupling_strength) Z_i Z_j + alpha * sum_site X_site"""
    n = graph.num_sites
    terms = [
        (_pauli_label({edge.site_i: "Z", edge.site_j: "Z"}, n), float(edge.coupling_strength))
        for edge in graph.edges
    ]
    terms += [(_pauli_label({site: "X"}, n), float(alpha)) for site in range(n)]
    return SparsePauliOp.from_list(terms).to_matrix()


def exact_continuous_expectation(
    graph: TFIMGraph, alpha: float, t: float, observable: SparsePauliOp
) -> float:
    """True continuous dynamics <0|e^{iHt} O e^{-iHt}|0>, H built directly as
    a dense matrix."""
    n = graph.num_sites
    H = _dense_hamiltonian(graph, alpha)
    psi0 = np.zeros(2**n, dtype=complex)
    psi0[0] = 1.0
    psi = expm(-1j * H * t) @ psi0 if t != 0.0 else psi0
    O = observable.to_matrix()
    return float(np.real(np.conj(psi) @ O @ psi))


# ---- Trotter ceiling: exact (noiseless) value of the compiled circuit ------

def trotter_reference_value(ir: PauliEncodedCircuitIR, alpha: float) -> float:
    """The r-step Trotter circuit's OWN exact value at alpha (zero shot noise)."""
    exact = oracle_coefficients(ir)
    parameter_coefficients = tuple(p.coefficients[0] for p in ir.parameters())
    total = 0.0
    for freq, b in exact.items():
        if not _is_canonical_representative(freq):
            continue
        if all(c == 0 for c in freq):
            total += b.real
            continue
        phase = math.pi * sum(l * c * alpha for l, c in zip(freq, parameter_coefficients))
        total += 2.0 * b.real * math.cos(phase) - 2.0 * b.imag * math.sin(phase)
    return total


# ---- training-graph construction -------------------------------------------

def build_training_graphs(rng: np.random.Generator, n_graphs: int) -> list[TFIMGraph]:
    """Random graphs on N_SITES, distinct edge sets, same field strength
    ALPHA_STAR for every graph."""
    all_pairs = [(i, j) for i in range(N_SITES) for j in range(i + 1, N_SITES)]
    graphs = []
    for _ in range(n_graphs):
        edges = tuple(
            TFIMEdge(site_i=i, site_j=j, coupling_strength=1.0)
            for (i, j) in all_pairs
            if rng.random() < 0.6
        )
        if not edges:
            i, j = all_pairs[0]
            edges = (TFIMEdge(site_i=i, site_j=j, coupling_strength=1.0),)
        graphs.append(TFIMGraph(num_sites=N_SITES, edges=edges, field_strength=ALPHA_STAR))
    return graphs


# ---- main sweep -------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(SEED)
    train_graphs = build_training_graphs(rng, N_TRAIN_GRAPHS)
    held_out_graph = build_training_graphs(rng, 1)[0]

    exact_pts, trotter_pts, pac_pts = [], [], []

    print(f"n={N_SITES} r={R_STEPS} shots={SHOTS} alpha*={ALPHA_STAR} "
          f"| {N_TRAIN_GRAPHS} training graphs\n" + "-" * 60)

    for t in T_VALUES:
        t0 = time.time()

        # 1. build every training row's IR at this time point
        train_rows = [
            CrossTopologyRow(
                ir=build_row_ir(g, tau=float(t), r=R_STEPS, observable=OBSERVABLE),
                label=exact_continuous_expectation(g, ALPHA_STAR, float(t), OBSERVABLE),
            )
            for g in train_graphs
        ]

        # 2. fit across topologies
        model = fit_cross_topology_lasso(
            train_rows, OBSERVABLE, shots=SHOTS, seed=SEED, simulator=SIMULATOR
        )

        # 3. predict on the held-out graph
        held_out_ir = build_row_ir(held_out_graph, tau=float(t), r=R_STEPS, observable=OBSERVABLE)
        pac_val = predict(model, held_out_ir, shots=SHOTS, seed=SEED, simulator=SIMULATOR)

        # 4. references
        exact_val = exact_continuous_expectation(held_out_graph, ALPHA_STAR, float(t), OBSERVABLE)
        trotter_val = trotter_reference_value(held_out_ir, ALPHA_STAR)

        exact_pts.append(exact_val)
        trotter_pts.append(trotter_val)
        pac_pts.append(pac_val)

        print(f"t={t:5.2f} | exact {exact_val:+.4f} | trotter {trotter_val:+.4f} "
              f"| pac {pac_val:+.4f} | {time.time()-t0:6.1f}s")

    exact_pts, trotter_pts, pac_pts = map(np.array, (exact_pts, trotter_pts, pac_pts))
    mse_pac = float(np.mean((pac_pts - exact_pts) ** 2))
    mse_trotter = float(np.mean((trotter_pts - exact_pts) ** 2))
    print("-" * 60)
    print(f"MSE(PAC vs Exact)     = {mse_pac:.5f}")
    print(f"MSE(Trotter vs Exact) = {mse_trotter:.5f}")

    # ---- dense reference curve for visual context ---
    t_dense = np.linspace(T_VALUES[0], T_VALUES[-1], 80)
    exact_dense = [
        exact_continuous_expectation(held_out_graph, ALPHA_STAR, float(t), OBSERVABLE)
        for t in t_dense
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t_dense, exact_dense, color="#a8cce3", lw=4, label="Exact")
    ax.plot(T_VALUES, trotter_pts, "--", color="#1f78b4", lw=2, label=f"Trotter (r={R_STEPS})")
    ax.scatter(T_VALUES, pac_pts, color="black", zorder=5, label="PAC (cross-topology)")
    ax.set_xlabel("time t"); ax.set_ylabel(r"$\langle Z_0(t)\rangle$")
    ax.set_title("Cross-topology FCE — TFIM dynamics tracking (Spec 12/13 pipeline)")
    ax.legend()
    fig.tight_layout()
    fig.savefig("tfim_dynamics_sweep.png", dpi=300)
    print("saved tfim_dynamics_sweep.png")


if __name__ == "__main__":
    main()