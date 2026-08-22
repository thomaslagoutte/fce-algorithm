"""T020 — Guardrail 3: reproduces research.md R2's caught degeneracy
directly. On the DEFAULT (unflipped) fixture, the matter pair starts in
the diagonal ("both empty") sector, which h_e=(1/2)(A_e+B_e) annihilates
EXACTLY (h_e^2 = (1/2)(I - Z_v Z_v'), which is 0 whenever Z_v=Z_v') --
making the extracted frequency support collapse to {DC only}. This test
asserts the DEGENERATE behavior explicitly, so an unrelated future
refactor that accidentally "fixes" the underlying physics is caught as a
meaningful change, not silently absorbed."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn import reference
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, build_z2_lgt_model, to_circuit_ir


def test_default_unflipped_fixture_gives_degenerate_dc_only_support() -> None:
    graph = Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    observable = SparsePauliOp("IIZ")  # Z_v0
    ir = to_circuit_ir(model, tau=1.0, r=1, observable=observable)  # no initial_occupation

    cost = reference.predict_grid_cost(ir)
    coeffs = reference.coefficients(ir, budget=cost, confirm=True)
    max_mag = max(abs(v) for v in coeffs.values())
    eps = 1e-9 * max_mag if max_mag > 0 else 1e-9
    omega = {l for l, v in coeffs.items() if abs(v) > eps}

    assert omega == {(0, 0, 0, 0)}, (
        "the unflipped fixture must collapse to DC-only -- if this ever "
        "fails, the state-prep flip (T021) is no longer load-bearing and "
        "this regression control (and the reason it exists) must be "
        "re-examined, not silently deleted"
    )
