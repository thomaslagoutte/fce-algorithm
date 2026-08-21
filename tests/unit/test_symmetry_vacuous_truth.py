"""T004/T005 — the Vacuous Truth Test (research.md R1): "internal"
(classical-input independence) is a genuine, non-vacuous runtime check,
not a type-level guarantee — SparsePauliOp legitimately accepts a
symbolic coefficient. Kept as separate test functions per each attempt."""

from __future__ import annotations

from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.symmetry import is_classical_input_independent


def test_symbolic_coefficient_generator_is_rejected() -> None:
    alpha = Parameter("alpha")
    generator = SparsePauliOp("X", coeffs=[alpha])
    assert is_classical_input_independent(generator) is False


def test_concrete_generator_is_accepted() -> None:
    generator = SparsePauliOp("X")
    assert is_classical_input_independent(generator) is True


def test_callable_generator_is_rejected_by_type() -> None:
    """research.md R1 Attempt 3: a plain callable standing in for an
    alpha-dependent generator is rejected by a type check, independent of
    and before the coefficient check above would ever run."""

    def alpha_dependent_generator(alpha_value: float) -> str:
        return "X" if alpha_value > 0 else "Z"

    assert not isinstance(alpha_dependent_generator, SparsePauliOp)
