"""Pauli-PQC frontend tests — FR-001..FR-005 (research.md R2, R6)."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir


def test_distinct_parameters_preserve_order_and_coefficients() -> None:
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="b", tie_group=0, coefficient=2.0),
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))

    assert ir.num_parameters == 2
    params = ir.parameters()
    assert params[0].upload_count == 1
    assert params[0].coefficients == (1.0,)
    assert params[1].upload_count == 1
    assert params[1].coefficients == (2.0,)
    assert [gate.pauli for gate in ir.gates] == ["X", "Z"]  # supplied order preserved


def test_tied_pair_yields_multiplicity_two_not_two_parameters() -> None:
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=5, coefficient=0.5),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="a", tie_group=5, coefficient=0.5),
    ]
    ir = build_ir(num_qubits=2, uploads=uploads, observable=SparsePauliOp("ZZ"))

    assert ir.num_parameters == 1
    (parameter,) = ir.parameters()
    assert parameter.multiplicity == 2
    assert parameter.upload_count == 1
    assert parameter.coefficients == (0.5, 0.5)


def test_repeated_untied_uploads_increment_upload_count() -> None:
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=i, coefficient=1.0)
        for i in range(3)
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))

    (parameter,) = ir.parameters()
    assert parameter.upload_count == 3
    assert parameter.multiplicity == 1


def test_empty_uploads_raises() -> None:
    with pytest.raises(ValueError):
        build_ir(num_qubits=1, uploads=[], observable=SparsePauliOp("Z"))


def test_heterogeneous_tied_coefficient_propagates_spec1_rejection() -> None:
    """`build_ir` deliberately does not re-implement tie-group coefficient
    uniformity checking (Constitution §9.4) — this proves Spec 1's own
    ValueError (ir.py FR-007) surfaces uncaught and unmodified rather than
    being duplicated, swallowed, or reworded here."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=2.0),
    ]
    with pytest.raises(ValueError, match="non-uniform coefficients"):
        build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))


def test_build_ir_rejects_noncommuting_tie_group() -> None:
    """Dedicated rejection test for research.md R6: a declared tie group whose
    Pauli strings do not pairwise commute must raise. `'X'` and `'Z'` on the
    same qubit anticommute — the physical claim behind tying (§11.2, "sum of
    commuting Pauli strings") does not hold, so sequential application would
    not equal exponentiating their sum."""
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
    ]
    with pytest.raises(ValueError, match="non-commuting"):
        build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))


def test_build_ir_rejects_noncommuting_tie_group_on_higher_index_qubit() -> None:
    """Multi-qubit, higher-index-qubit variant of the above (guardrail): on a
    3-qubit register, one upload's Pauli string spans qubits (0, 2) ('X' on
    qubit 0, 'Z' on qubit 2); it is tied to a second upload acting with 'Y' on
    qubit 2 alone. 'Z'@2 and 'Y'@2 anticommute (qubit 0's 'X' vs. identity
    trivially commutes, contributing nothing), so the pair overall
    anticommutes and the tie group must be rejected. This specifically
    exercises the little-endian padding/reversal (pauli-gate-sign-convention
    memory) at a qubit index other than 0: a reversal bug would place the 'Z'
    at the wrong register position, which the 1-qubit case above cannot
    detect."""
    uploads = [
        PauliUpload(pauli="XZ", qubits=(0, 2), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Y", qubits=(2,), parameter_label="a", tie_group=0, coefficient=1.0),
    ]
    with pytest.raises(ValueError, match="non-commuting"):
        build_ir(num_qubits=3, uploads=uploads, observable=SparsePauliOp("III"))
