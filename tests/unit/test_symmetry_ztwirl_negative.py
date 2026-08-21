"""T007 — Z-twirl negative control, on the SAME full matter+gauge
fixture as test_symmetry_gauss_law_positive.py (Guardrail #1). Kept in
its own file: the positive and negative controls are distinct claims,
never merged."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.symmetry import verify_symmetry
from tests.unit.test_symmetry_gauss_law_positive import G_V0, HAMILTONIAN_TERMS

# The naive, WRONG candidate: X<->Z swapped relative to the true G_v0 ("IXIIZ").
Z_TWIRL_V0 = SparsePauliOp("IZIIX")


def test_ztwirl_fails_non_annihilating_on_full_fixture() -> None:
    assert Z_TWIRL_V0 != G_V0

    result = verify_symmetry((Z_TWIRL_V0,), HAMILTONIAN_TERMS)

    assert result.non_annihilating is False
    assert result.failing_term is not None
    assert result.failing_term.paulis[0].to_label() == "IXIII"  # H_g_e01
    assert result.accepted is False

    # Isolation: this negative control fails non-annihilating SPECIFICALLY --
    # internal and Abelian (trivially, with only one generator) still pass,
    # proving the rejection is not a confound of several failures at once.
    assert result.internal is True
    assert result.abelian is True
