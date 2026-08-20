"""Core `compile_frequency_circuit` acceptance tests — FR-001..FR-005,
FR-009, FR-010 (research.md R2, R3, R4, R6)."""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn import frequency
from fourierlearn.circuits import compile_frequency_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm


def test_one_frequency_register_per_parameter_sized_by_register_width() -> None:
    """Acceptance Scenario 1: exactly one frequency-counter register per
    encoded parameter, sized via Spec 1's register_width, and no other
    register besides the shared ancilla and the circuit register."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=i, coefficient=1.0)
        for i in range(3)
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))
    qc = compile_frequency_circuit(ir)

    assert len(qc.qregs) == 1 + 1 + 1  # one freq register + ancilla + circuit
    expected_width = frequency.register_width(uploads=3, r_j=1)
    assert len(qc.qregs[0]) == expected_width
    assert len(qc.qregs[1]) == 1  # ancilla
    assert len(qc.qregs[2]) == 1  # circuit


def _amplitude_table_via_grid_and_fft(ir: PauliEncodedCircuitIR) -> dict[tuple[int, ...], complex]:
    """Independent ground truth for a_{l,k}: brute-force per-k Nyquist grid +
    FFT of the ORIGINAL (uncompiled) circuit, built directly from the IR's
    own PauliTerm.to_gate() -- the same method research.md R3 used, not a
    second call into the circuit under test."""
    from qiskit import QuantumCircuit

    parameters = ir.parameters()
    symbols = ir.parameter_symbols()
    axes = []
    for p in parameters:
        n_points = 4 * p.multiplicity * p.upload_count + 1
        (coefficient,) = set(p.coefficients)
        domain_length = 2 / coefficient
        axes.append(np.array([domain_length * m / n_points for m in range(n_points)]))

    qc = QuantumCircuit(ir.num_qubits)
    for gate in ir.gates:
        if isinstance(gate, PauliTerm):
            qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
        else:
            qc.append(gate.gate, gate.qubits)

    shape = tuple(len(axis) for axis in axes)
    values = np.zeros(shape + (2**ir.num_qubits,), dtype=complex)
    for index in itertools.product(*(range(n) for n in shape)):
        binding = {symbols[p.index]: axes[axis_i][index[axis_i]] for axis_i, p in enumerate(parameters)}
        bound = qc.assign_parameters(binding)
        values[index] = Statevector(bound).data

    transformed = np.fft.fftn(values, axes=range(len(shape))) / np.prod(shape)
    result = {}
    for index in itertools.product(*(range(n) for n in shape)):
        l_tuple = tuple(int(frequency.dft_frequencies(shape[axis])[idx]) for axis, idx in enumerate(index))
        for k in range(2**ir.num_qubits):
            result[l_tuple + (k,)] = complex(transformed[index + (k,)])
    return result


def test_amplitudes_match_independent_ground_truth_two_parameters() -> None:
    """Acceptance Scenario 2/3: two encoded parameters, each with their own
    independently sized register; compiled amplitudes match an independently
    computed a_{l,k} table (per-k grid+FFT of the uncompiled circuit)."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="b", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=2, uploads=uploads, observable=SparsePauliOp("II"))
    expected = _amplitude_table_via_grid_and_fft(ir)

    qc = compile_frequency_circuit(ir)
    state = Statevector(qc)
    freq_widths = [len(reg) for reg in qc.qregs[:-2]]

    for (la, lb, k), expected_amp in expected.items():
        freq_a_val = la % (2 ** freq_widths[0])
        freq_b_val = lb % (2 ** freq_widths[1])
        index = (
            freq_a_val
            | (freq_b_val << freq_widths[0])
            | (0 << (freq_widths[0] + freq_widths[1]))  # ancilla
            | (k << (freq_widths[0] + freq_widths[1] + 1))
        )
        got = complex(state.data[index])
        assert math.isclose(got.real, expected_amp.real, abs_tol=1e-9)
        assert math.isclose(got.imag, expected_amp.imag, abs_tol=1e-9)


def test_tied_multiplicity_contributes_independent_increments_onto_shared_register() -> None:
    """Acceptance Scenario 4: a tied (r_j=2) parameter's two terms each
    contribute their own increment/decrement onto the SAME register -- not
    two independent registers, and not a single combined step."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="a", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=2, uploads=uploads, observable=SparsePauliOp("II"))
    qc = compile_frequency_circuit(ir)

    assert len(qc.qregs) == 3  # one shared register for the tied parameter + ancilla + circuit
    expected_width = frequency.register_width(uploads=1, r_j=2)
    assert len(qc.qregs[0]) == expected_width

    expected = _amplitude_table_via_grid_and_fft(ir)
    state = Statevector(qc)
    freq_width = len(qc.qregs[0])
    for (l, k), expected_amp in expected.items():
        freq_val = l % (2**freq_width)
        index = freq_val | (0 << freq_width) | (k << (freq_width + 1))
        got = complex(state.data[index])
        assert math.isclose(got.real, expected_amp.real, abs_tol=1e-9)
        assert math.isclose(got.imag, expected_amp.imag, abs_tol=1e-9)


def test_non_z_encoding_gate_compiled_transparently() -> None:
    """Acceptance Scenario 5: an X-encoding gate is handled transparently --
    the caller-visible IR/API is identical to the Z case; correctness is
    checked against the same independent ground truth method."""
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))
    expected = _amplitude_table_via_grid_and_fft(ir)

    qc = compile_frequency_circuit(ir)
    state = Statevector(qc)
    freq_width = len(qc.qregs[0])
    for (l, k), expected_amp in expected.items():
        freq_val = l % (2**freq_width)
        index = freq_val | (0 << freq_width) | (k << (freq_width + 1))
        got = complex(state.data[index])
        assert math.isclose(got.real, expected_amp.real, abs_tol=1e-9)
        assert math.isclose(got.imag, expected_amp.imag, abs_tol=1e-9)


def test_zero_parameters_raises() -> None:
    """FR-009: a zero-parameter IR must raise, not silently compile a
    meaningless circuit."""
    ir = PauliEncodedCircuitIR(num_qubits=1, gates=(), observable=SparsePauliOp("Z"))
    with pytest.raises(ValueError):
        compile_frequency_circuit(ir)
