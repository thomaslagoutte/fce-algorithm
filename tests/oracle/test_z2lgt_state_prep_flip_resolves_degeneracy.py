"""T022 — Guardrail 3, positive counterpart to T020: WITH the state-prep
flip (initial_occupation=(1,), placing the matter pair in the
off-diagonal "exactly one particle" sector where h_e is genuinely
active), the extracted frequency support is non-degenerate -- reproduces
research.md R2's own executed numbers exactly."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn import reference
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, build_z2_lgt_model, to_circuit_ir


def test_flipped_fixture_gives_nondegenerate_hopping_support() -> None:
    graph = Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    observable = SparsePauliOp("IIZ")  # Z_v0
    ir = to_circuit_ir(model, tau=1.0, r=1, observable=observable, initial_occupation=(1,))

    cost = reference.predict_grid_cost(ir)
    coeffs = reference.coefficients(ir, budget=cost, confirm=True)
    max_mag = max(abs(v) for v in coeffs.values())
    eps = 1e-9 * max_mag
    omega = {l for l, v in coeffs.items() if abs(v) > eps}

    assert omega == {(0, -4, 0, 0), (0, 4, 0, 0)}, (
        "the flipped fixture must reproduce research.md R2's own executed "
        f"Omega exactly; got {sorted(omega)}"
    )
