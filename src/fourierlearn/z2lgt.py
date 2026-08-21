"""Z2 LGT ansatz construction — FR-001..FR-006 (Spec 8, deliverables a+b).

Builds the full matter+gauge Z2 lattice gauge theory Hamiltonian with
*local*, independently learnable couplings per vertex/edge — cited to the
primary report's own §5.1-5.3/eq. 25-27 (research.md R1), giving an
encoded-parameter count `d = |V| + 2|E|`. This is a citation to a
different, already-local part of the same report than its eq. 1-4
(global-scalar `J, m, f`) — NOT a Constitution §2.3 EXTENSION.

Generator set (eq. 25): `{Z_v}_mass ∪ {X_e}_electric ∪ {h_e=(1/2)(A_e+B_e)}_hopping`,
with `A_e = X_v Z_e X_v'`, `B_e = Y_v Z_e Y_v'` for edge `e=(v,v')` (eq. 2).
`A_e`/`B_e` are tied under one shared `CouplingGroup` per edge, reusing
the existing, unmodified tie-group mechanism (Constitution §11.2) — no new
tying primitive is introduced.

The Gauss law generators `G_v = Z_v · prod_{e touching v} X_e` (eq. 5) are
always attached as a non-optional `SymmetryDeclaration`, so Spec 7's
existing, unmodified `PhysicalModelDescription.__post_init__` enforcement
runs unconditionally (Critical Mandate 1) — this module adds no new
verification hook of its own.

Gates are declared in the fixed order mass -> electric -> hopping, so the
commuting family `F = {Z_v} ∪ {X_e}` (Constitution §11.9/§11.10) forms one
contiguous block by construction; `circuits.py` never reorders IR gates,
so no separate reordering-contiguity check is needed downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from qiskit.circuit.library import XGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import _pad_to_full_width_little_endian
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.frequency import coordinate_order
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.models import PhysicalModelDescription, SymmetryDeclaration, ZeroCouplingError


@dataclass(frozen=True)
class Z2LGTEdge:
    """One gauge link `e=(v,v')` connecting two matter sites."""

    site_i: int
    site_j: int


@dataclass(frozen=True)
class Z2LGTGraph:
    """A classical-input, domain-vocabulary Z2 LGT lattice description
    (structural analogue of Spec 6's `TFIMGraph`): `num_matter_sites`
    matter qubits, indexed `0..num_matter_sites-1`, plus one gauge qubit
    per declared edge, indexed `num_matter_sites..num_matter_sites+len(edges)-1`
    in `edges` declaration order — one fixed, documented convention."""

    num_matter_sites: int
    edges: tuple[Z2LGTEdge, ...]

    @property
    def num_qubits(self) -> int:
        return self.num_matter_sites + len(self.edges)

    def gauge_qubit(self, edge_index: int) -> int:
        return self.num_matter_sites + edge_index

    def edges_touching(self, vertex: int) -> tuple[int, ...]:
        """Indices (into `self.edges`) of every edge incident to `vertex`."""
        return tuple(
            i for i, e in enumerate(self.edges) if vertex in (e.site_i, e.site_j)
        )


def _gauss_law_generators(graph: Z2LGTGraph) -> tuple[SparsePauliOp, ...]:
    """FR-003 (report eq. 5): one `G_v = Z_v · prod_{e touching v} X_e` per
    matter site `v`, mechanically derived from the graph's own incidence
    structure (Constitution §11.9 — no caller-supplied ambiguity)."""
    generators = []
    for v in range(graph.num_matter_sites):
        touching = graph.edges_touching(v)
        pauli = "Z" + "X" * len(touching)
        qubits = (v,) + tuple(graph.gauge_qubit(e) for e in touching)
        label = _pad_to_full_width_little_endian(pauli, qubits, graph.num_qubits)
        generators.append(SparsePauliOp(label))
    return tuple(generators)


def _require_all_declared(
    keys: range, couplings: Mapping[int, float], what: str
) -> None:
    missing = [k for k in keys if k not in couplings]
    if missing:
        raise ValueError(f"{what} coupling(s) not declared for index/indices {missing}")


def build_z2_lgt_model(
    graph: Z2LGTGraph,
    mass_couplings: Mapping[int, float],
    electric_couplings: Mapping[int, float],
    hopping_couplings: Mapping[int, float],
) -> PhysicalModelDescription:
    """FR-001/FR-002/FR-003/FR-004 (deliverables a+b): the full
    matter+gauge Hamiltonian with local couplings,
    `H = sum_e J_e*h_e + sum_v m_v*(-1)^v*Z_v + sum_e f_e*X_e`
    (report §5.1-5.3/eq. 25-27), with the Gauss law generators always
    attached as a `SymmetryDeclaration` — Spec 7's existing
    `PhysicalModelDescription.__post_init__` verifies them unconditionally.

    `mass_couplings`/`electric_couplings`/`hopping_couplings` are keyed by
    vertex index / edge index (into `graph.edges`) respectively; every
    vertex and edge MUST have a declared coupling (raises `ValueError`
    otherwise) — no silently-defaulted coupling.
    """
    _require_all_declared(range(graph.num_matter_sites), mass_couplings, "mass")
    _require_all_declared(range(len(graph.edges)), electric_couplings, "electric")
    _require_all_declared(range(len(graph.edges)), hopping_couplings, "hopping")

    coupling_groups = []

    for v in range(graph.num_matter_sites):
        m_v = mass_couplings[v]
        if m_v == 0.0:
            raise ZeroCouplingError(
                f"mass coupling for vertex {v} is exactly zero — a zero coupling has no "
                "well-defined period and cannot be represented as a learnable parameter"
            )
        sign = -1.0 if v % 2 else 1.0  # (-1)^v, report eq. 3
        coupling_groups.append(
            CouplingGroup(
                label=f"mass_{v}",
                terms=(CouplingGroupTerm(pauli="Z", qubits=(v,), weight=sign * m_v),),
            )
        )

    for e_index, edge in enumerate(graph.edges):
        f_e = electric_couplings[e_index]
        if f_e == 0.0:
            raise ZeroCouplingError(
                f"electric coupling for edge {e_index} is exactly zero — a zero coupling has "
                "no well-defined period and cannot be represented as a learnable parameter"
            )
        gauge_qubit = graph.gauge_qubit(e_index)
        coupling_groups.append(
            CouplingGroup(
                label=f"electric_{e_index}",
                terms=(CouplingGroupTerm(pauli="X", qubits=(gauge_qubit,), weight=f_e),),
            )
        )

    for e_index, edge in enumerate(graph.edges):
        j_e = hopping_couplings[e_index]
        if j_e == 0.0:
            raise ZeroCouplingError(
                f"hopping coupling for edge {e_index} is exactly zero — a zero coupling has "
                "no well-defined period and cannot be represented as a learnable parameter"
            )
        gauge_qubit = graph.gauge_qubit(e_index)
        qubits = (edge.site_i, gauge_qubit, edge.site_j)
        coupling_groups.append(
            CouplingGroup(
                label=f"hopping_{e_index}",
                terms=(
                    CouplingGroupTerm(pauli="XZX", qubits=qubits, weight=0.5 * j_e),  # A_e
                    CouplingGroupTerm(pauli="YZY", qubits=qubits, weight=0.5 * j_e),  # B_e
                ),
            )
        )

    symmetry = SymmetryDeclaration(
        name="z2_gauss_law", generators=_gauss_law_generators(graph)
    )

    return PhysicalModelDescription(
        num_sites=graph.num_qubits,
        coupling_groups=tuple(coupling_groups),
        symmetry=symmetry,
    )


def coordinate_roles(
    graph: Z2LGTGraph,
) -> tuple[dict[int, int], dict[int, int], frozenset[int]]:
    """The coordinate-role metadata `containment.compute_lambda` needs:
    which encoded-parameter *index* is each mass/electric axis (hopping
    axes are returned separately, since they carry no Theorem 6.1
    constraint — report §7.1). Computed independently of any built IR, via
    the exact same `frequency.coordinate_order` function `build_ir` itself
    uses on the exact label set `build_z2_lgt_model` declares
    (`mass_{v}`, `electric_{e}`, `hopping_{e}`) — reproduces the resulting
    parameter indices deterministically, without needing the IR to store
    its own label-to-index mapping (which it does not)."""
    labels = (
        [f"mass_{v}" for v in range(graph.num_matter_sites)]
        + [f"electric_{e}" for e in range(len(graph.edges))]
        + [f"hopping_{e}" for e in range(len(graph.edges))]
    )
    ordered = coordinate_order(labels)
    index_by_label = {label: i for i, label in enumerate(ordered)}
    mass_axis_by_vertex = {v: index_by_label[f"mass_{v}"] for v in range(graph.num_matter_sites)}
    electric_axis_by_edge = {
        e: index_by_label[f"electric_{e}"] for e in range(len(graph.edges))
    }
    hopping_axes = frozenset(
        index_by_label[f"hopping_{e}"] for e in range(len(graph.edges))
    )
    return mass_axis_by_vertex, electric_axis_by_edge, hopping_axes


def to_circuit_ir(
    model: PhysicalModelDescription,
    tau: float,
    r: int,
    observable: SparsePauliOp,
    initial_occupation: tuple[int, ...] = (),
) -> PauliEncodedCircuitIR:
    """The mechanical, single conversion step from a verified
    `PhysicalModelDescription` (whose Gauss law was already checked at
    construction time, FR-004) to an actual `PauliEncodedCircuitIR` —
    reuses `trotter_frontend` unchanged, so no verification logic is
    duplicated here.

    `initial_occupation` (Guardrail 3 — the state-prep flip): a tuple of
    matter-site indices to flip from the default `|0>` to `|1>` via a
    non-parameterized `FixedGate(XGate(), (site,))`, prepended ahead of
    every parameterized gate. Defaults to `()` (no flip), preserving prior
    behaviour exactly. Needed because the default all-`|0>` initial state
    sits in `h_e`'s exact zero-eigenspace (research.md R2): `h_e`
    annihilates the "both matter sites equal" sector, making the hopping
    parameter's own effect structurally invisible unless the matter pair
    starts in the off-diagonal ("exactly one particle") sector.
    """
    base_ir = trotter_frontend(
        num_qubits=model.num_sites,
        groups=model.coupling_groups,
        tau=tau,
        r=r,
        observable=observable,
    )
    if not initial_occupation:
        return base_ir
    flips = tuple(FixedGate(XGate(), (site,)) for site in initial_occupation)
    return PauliEncodedCircuitIR(
        num_qubits=base_ir.num_qubits,
        gates=flips + base_ir.gates,
        observable=base_ir.observable,
    )
