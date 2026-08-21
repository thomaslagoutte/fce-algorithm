"""T008/T010 — a genuine Abelian-failure negative control (not covered
by the Gauss law/Z-twirl fixtures, both of which are entirely X-or-Z and
trivially commuting either way), and confirmation that verify_symmetry
reports every failing condition, not only the first one checked."""

from __future__ import annotations

from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.symmetry import verify_symmetry


def test_abelian_failure_is_detected() -> None:
    x_on_q0 = SparsePauliOp("X")
    z_on_q0 = SparsePauliOp("Z")
    harmless_term = SparsePauliOp("I")

    result = verify_symmetry((x_on_q0, z_on_q0), (harmless_term,))

    assert result.abelian is False
    assert result.non_commuting_pair is not None
    pair_labels = {p.paulis[0].to_label() for p in result.non_commuting_pair}
    assert pair_labels == {"X", "Z"}
    assert result.accepted is False


def test_verify_symmetry_reports_every_condition_not_just_first_failure() -> None:
    """A generator that fails BOTH 'internal' (symbolic coefficient) and
    'Abelian' (does not commute with the second generator) at once must
    have both failures reported, not only whichever is checked first."""
    alpha = Parameter("alpha")
    symbolic_and_noncommuting = SparsePauliOp("X", coeffs=[alpha])
    other_generator = SparsePauliOp("Z")
    harmless_term = SparsePauliOp("I")

    result = verify_symmetry((symbolic_and_noncommuting, other_generator), (harmless_term,))

    assert result.internal is False
    assert result.abelian is False
    assert result.accepted is False
    assert result.failure_reason is not None
    assert "internal" in result.failure_reason
    assert "Abelian" in result.failure_reason
