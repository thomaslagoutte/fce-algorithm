"""T006 — Gauss law positive control, on the FULL matter+gauge Z2
lattice gauge theory fixture (Guardrail #1: G_v = Z_v * prod_{e touching
v} X_e, explicitly including matter qubits — not the simplified
pure-gauge limit).

Fixture: a 3-vertex path lattice v0-v1-v2, 5 qubits total (3 matter + 2
gauge). Qubit order: [m0, m1, m2, g01, g12] (qubit0=m0 ... qubit4=g12).
Labels verified by execution during /speckit-tasks (tasks.md's own header
note) -- reproduced here as the permanent regression test."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.symmetry import verify_symmetry

# Full matter+gauge Gauss law generators.
G_V0 = SparsePauliOp("IXIIZ")
G_V1 = SparsePauliOp("XXIZI")
G_V2 = SparsePauliOp("XIZII")

# Hamiltonian terms: pure-gauge kinetic terms + matter-gauge hopping terms.
H_G_E01 = SparsePauliOp("IXIII")
H_G_E12 = SparsePauliOp("XIIII")
H_HOP_E01 = SparsePauliOp("IZIXX")
H_HOP_E12 = SparsePauliOp("ZIXXI")

HAMILTONIAN_TERMS = (H_G_E01, H_G_E12, H_HOP_E01, H_HOP_E12)


def test_full_matter_gauge_gauss_law_passes_all_conditions() -> None:
    generators = (G_V0, G_V1, G_V2)

    # The three generators are genuinely distinct -- proving this is the
    # site-indexed case, not an accidentally uniform one.
    assert len({g.paulis[0].to_label() for g in generators}) == 3

    result = verify_symmetry(generators, HAMILTONIAN_TERMS)

    assert result.internal is True
    assert result.non_annihilating is True
    assert result.abelian is True
    assert result.accepted is True
    assert result.failing_term is None
    assert result.non_commuting_pair is None
