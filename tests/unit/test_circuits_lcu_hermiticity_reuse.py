"""T010 — FR-006: a non-Hermitian multi-term observable is rejected by
Spec 4's existing, UNMODIFIED `extract_coefficients` precondition check
(`observable != observable.adjoint()`) -- this check already generalizes
correctly to a multi-term `SparsePauliOp` with zero code changes, since
`SparsePauliOp.adjoint()` already handles a multi-term sum correctly.
No separate, circuits.py-level Hermiticity check is added (FR-006: "not a
relaxed or separately-implemented check")."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import extract_coefficients


def test_non_hermitian_multi_term_observable_is_rejected_by_the_existing_check() -> None:
    uploads = [PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=0.3)]
    # Z + iX is NOT Hermitian: (Z+iX)^dagger = Z - iX != Z + iX.
    non_hermitian = SparsePauliOp(["Z", "X"], coeffs=[1.0, 1.0j])
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("I"))

    with pytest.raises(ValueError, match="Hermitian"):
        extract_coefficients(ir, non_hermitian, shots=100)


def test_hermitian_multi_term_observable_passes_the_same_check() -> None:
    uploads = [PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=0.3)]
    hermitian = SparsePauliOp(["Z", "X"], coeffs=[1.0, -2.0])
    assert hermitian == hermitian.adjoint()
