"""T009 — FR-008/FR-009: degenerate and structurally mismatched
declarations are rejected explicitly, before any of §11.1's three
substantive conditions. Independent test functions.

Plus two post-review safety patches: multi-term Pauli observables/LCUs
are explicitly out of scope (rejected, not silently truncated to their
first term), and the identity check is robust to a non-unit coefficient
on an otherwise-trivial generator."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.symmetry import (
    DegenerateSymmetryError,
    MultiTermPauliError,
    QubitCountMismatchError,
    verify_symmetry,
)


def test_zero_generators_rejected() -> None:
    with pytest.raises(DegenerateSymmetryError):
        verify_symmetry((), (SparsePauliOp("X"),))


def test_identity_generator_rejected() -> None:
    with pytest.raises(DegenerateSymmetryError):
        verify_symmetry((SparsePauliOp("II"),), (SparsePauliOp("XI"),))


def test_identity_generator_with_non_unit_coefficient_still_rejected() -> None:
    """Robust Identity Check (post-review safety patch): a generator whose
    Pauli content is pure identity but carries a non-unit coefficient
    (e.g. 2.0) must still be flagged as degenerate — `==` against
    `SparsePauliOp('II')` would miss this, since `==` also compares the
    coefficient; the check must compare the Pauli string's own label."""
    trivial_but_scaled = SparsePauliOp("II", coeffs=[2.0])
    with pytest.raises(DegenerateSymmetryError):
        verify_symmetry((trivial_but_scaled,), (SparsePauliOp("XI"),))


def test_qubit_count_mismatch_rejected() -> None:
    with pytest.raises(QubitCountMismatchError):
        verify_symmetry((SparsePauliOp("XX"),), (SparsePauliOp("X"),))


def test_multi_term_generator_rejected() -> None:
    """Strict Single-Pauli Assertion (post-review safety patch): a
    generator that is a linear combination of more than one Pauli string
    must be rejected outright, never silently checked via only its first
    term (`.paulis[0]`) while the rest of the declaration is ignored."""
    multi_term_generator = SparsePauliOp(["X", "Z"], coeffs=[1.0, 1.0])
    with pytest.raises(MultiTermPauliError):
        verify_symmetry((multi_term_generator,), (SparsePauliOp("X"),))


def test_multi_term_hamiltonian_term_rejected() -> None:
    """The same strict single-Pauli assertion applies to a declared
    Hamiltonian term, not only to generators."""
    multi_term_hamiltonian_term = SparsePauliOp(["X", "Z"], coeffs=[1.0, 1.0])
    with pytest.raises(MultiTermPauliError):
        verify_symmetry((SparsePauliOp("X"),), (multi_term_hamiltonian_term,))
