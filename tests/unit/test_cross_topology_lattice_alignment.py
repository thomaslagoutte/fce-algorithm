"""Spec 12 T003, T006, T007, T008 — FR-001 (`CrossTopologyRow` never holds
a bound `alpha`), FR-014 (surgical `FrequencyLatticeMismatchError`
messages, this round's Critical Mandate 1), and FR-008 (Trotter-config
mismatch caught by the SAME general mechanism)."""

from __future__ import annotations

import dataclasses

import pytest
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.cross_topology import (
    CrossTopologyRow,
    FrequencyLatticeMismatchError,
    validate_lattice_alignment,
)
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm

OBSERVABLE = SparsePauliOp("Z")


def _ir(theta: float, *, coefficient: float = 1.0, upload_count: int = 1, multiplicity: int = 1):
    """`upload_count` tie groups, each containing `multiplicity` PauliTerm
    entries (matching `ir.py`'s own `Parameter.upload_count`/`multiplicity`
    definitions exactly -- `upload_count = len(tie groups)`,
    `multiplicity = size of each tie group`)."""
    gates: list = [FixedGate(RYGate(theta), (0,))]
    for tie_group in range(upload_count):
        for _ in range(multiplicity):
            gates.append(
                PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=coefficient, tie_group=tie_group)
            )
    return PauliEncodedCircuitIR(num_qubits=1, gates=tuple(gates), observable=OBSERVABLE)


def test_cross_topology_row_has_no_bound_parameter_field() -> None:
    """FR-001: the row is (x_t, y_t) -- an IR (the topology declaration)
    and a label -- never a field whose semantics is a bound `alpha`
    assignment."""
    row = CrossTopologyRow(ir=_ir(0.9), label=1.23)
    field_names = {f.name for f in dataclasses.fields(row)}
    assert field_names == {"ir", "label"}
    assert not any("alpha" in name.lower() for name in field_names)


def test_valid_matching_lattice_passes_without_error() -> None:
    rows = [CrossTopologyRow(ir=_ir(theta), label=0.0) for theta in (0.3, 0.9, 1.7, 2.4)]
    validate_lattice_alignment(rows)  # must not raise


def test_multiplicity_mismatch_names_exact_parameter_index_and_field() -> None:
    rows = [
        CrossTopologyRow(ir=_ir(0.3, upload_count=1, multiplicity=1), label=0.0),
        CrossTopologyRow(ir=_ir(0.9, upload_count=1, multiplicity=2), label=0.0),
    ]
    with pytest.raises(FrequencyLatticeMismatchError) as exc_info:
        validate_lattice_alignment(rows)
    message = str(exc_info.value)
    assert "parameter_index=0" in message
    assert "field='multiplicity'" in message
    assert "lattices differ" not in message.lower()


def test_coefficient_mismatch_names_exact_parameter_index_and_field() -> None:
    rows = [
        CrossTopologyRow(ir=_ir(0.3, coefficient=1.0), label=0.0),
        CrossTopologyRow(ir=_ir(0.9, coefficient=0.5), label=0.0),
    ]
    with pytest.raises(FrequencyLatticeMismatchError) as exc_info:
        validate_lattice_alignment(rows)
    message = str(exc_info.value)
    assert "parameter_index=0" in message
    assert "field='coefficients'" in message
    assert "lattices differ" not in message.lower()


def test_upload_count_mismatch_names_exact_parameter_index_and_field() -> None:
    """FR-008's own Trotter-configuration-style case (differing upload
    count, as two tie groups vs one) caught by the SAME mechanism T006
    exercises -- not a separate code path."""
    rows = [
        CrossTopologyRow(ir=_ir(0.3, upload_count=1, multiplicity=1), label=0.0),
        CrossTopologyRow(ir=_ir(0.9, upload_count=2, multiplicity=1), label=0.0),
    ]
    with pytest.raises(FrequencyLatticeMismatchError) as exc_info:
        validate_lattice_alignment(rows)
    message = str(exc_info.value)
    assert "parameter_index=0" in message
    assert "field='upload_count'" in message
    assert "lattices differ" not in message.lower()
