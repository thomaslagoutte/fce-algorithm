"""FR-004, FR-005, FR-006, FR-007: the Pauli-encoded circuit IR.

Also covers the parameter_symbols() object-identity guarantee (FR-005's structural
tying enforcement) and a multi-qubit little-endian sanity check: `to_gate()` must
respect Qiskit's convention that a Pauli label's rightmost character acts on the
lowest-indexed qubit, which none of this spec's own single-qubit oracle validation
cases would otherwise exercise.
"""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator, SparsePauliOp
from scipy.linalg import expm

from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm

_Z = np.array([[1, 0], [0, -1]])
_X = np.array([[0, 1], [1, 0]])


def _single_upload_ir() -> PauliEncodedCircuitIR:
    return PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),),
        observable=SparsePauliOp("Z"),
    )


def _tied_ir(coefficients: tuple[float, float] = (1.0, 1.0)) -> PauliEncodedCircuitIR:
    """r_j=2: two Pauli strings sharing parameter_index=0 in one tie_group."""
    return PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(
            PauliTerm("Z", (0,), parameter_index=0, coefficient=coefficients[0], tie_group=0),
            PauliTerm("X", (0,), parameter_index=0, coefficient=coefficients[1], tie_group=0),
        ),
        observable=SparsePauliOp("Z"),
    )


# --- FR-004, FR-005: tied-parameter round-trip -----------------------------------


def test_tied_parameter_round_trips_upload_count_multiplicity_coefficients() -> None:
    ir = _tied_ir(coefficients=(1.5, 2.5))
    assert ir.upload_count(0) == 1
    assert ir.multiplicity(0) == 2
    assert ir.coefficients(0) == (1.5, 2.5)


def test_untied_multi_upload_reports_correct_upload_count_and_multiplicity() -> None:
    ir = PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=1),
        ),
        observable=SparsePauliOp("Z"),
    )
    assert ir.upload_count(0) == 2
    assert ir.multiplicity(0) == 1


# --- FR-005: multiplicity mismatch is a detectable, rejected invalid state -------


def test_uneven_tie_group_sizes_are_rejected() -> None:
    with pytest.raises(ValueError):
        PauliEncodedCircuitIR(
            num_qubits=1,
            gates=(
                PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
                PauliTerm("X", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
                PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=1),
            ),
            observable=SparsePauliOp("Z"),
        )


# --- Construction-time validation -------------------------------------------------


def test_out_of_range_qubit_index_is_rejected() -> None:
    with pytest.raises(ValueError):
        PauliEncodedCircuitIR(
            num_qubits=1,
            gates=(PauliTerm("Z", (5,), parameter_index=0, coefficient=1.0, tie_group=0),),
            observable=SparsePauliOp("Z"),
        )


def test_non_hermitian_observable_is_rejected() -> None:
    non_hermitian = SparsePauliOp(["Z", "Y"], coeffs=[1.0, 1j])
    with pytest.raises(ValueError):
        PauliEncodedCircuitIR(
            num_qubits=1,
            gates=(PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),),
            observable=non_hermitian,
        )


def test_fixed_gate_qubit_count_must_match_gate_arity() -> None:
    from qiskit.circuit.library import SGate

    with pytest.raises(ValueError):
        PauliEncodedCircuitIR(
            num_qubits=2,
            gates=(FixedGate(SGate(), (0, 1)),),  # SGate is 1-qubit, 2 qubits given
            observable=SparsePauliOp("ZI"),
        )


# --- parameter_symbols(): structural tying (FR-005) -------------------------------


def test_parameter_symbols_returns_identical_object_across_calls() -> None:
    ir = _tied_ir()
    # `is`, not `==`: Qiskit's assign_parameters binds by object identity, so a
    # fresh-but-equal Parameter minted per call would silently fail to tie terms
    # together even though it would pass an equality-only assertion.
    assert ir.parameter_symbols()[0] is ir.parameter_symbols()[0]


def test_parameter_symbols_one_per_distinct_index() -> None:
    ir = PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
            PauliTerm("X", (0,), parameter_index=1, coefficient=1.0, tie_group=0),
        ),
        observable=SparsePauliOp("Z"),
    )
    symbols = ir.parameter_symbols()
    assert set(symbols.keys()) == {0, 1}
    assert symbols[0] is not symbols[1]


# --- FR-007: coefficient never leaks into anything frequency/register-sized -----


def test_coefficient_does_not_affect_upload_count_multiplicity_or_grid_shape() -> None:
    ir_a = _tied_ir(coefficients=(1.0, 1.0))
    ir_b = _tied_ir(coefficients=(0.37, -12.9))  # only coefficients differ

    assert ir_a.upload_count(0) == ir_b.upload_count(0)
    assert ir_a.multiplicity(0) == ir_b.multiplicity(0)

    def grid_size(ir: PauliEncodedCircuitIR, j: int) -> int:
        return 4 * ir.multiplicity(j) * ir.upload_count(j) + 1

    assert grid_size(ir_a, 0) == grid_size(ir_b, 0)


# --- to_gate(): sign convention (FR-021) and little-endian qubit mapping ---------


def test_to_gate_single_qubit_matches_encoding_convention() -> None:
    alpha = Parameter("alpha")
    term = PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0)
    gate = term.to_gate(alpha)

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(1)
    qc.append(gate, [0])
    bound = qc.assign_parameters({alpha: 0.6})
    actual = Operator(bound).data
    expected = expm(1j * np.pi * 1.0 * 0.6 * _Z)
    assert np.allclose(actual, expected)


def test_to_gate_respects_little_endian_qubit_mapping_for_multi_qubit_terms() -> None:
    """pauli[i] must act on qubits[i] regardless of Qiskit's little-endian label
    convention — confirmed in-session that a naive (unreversed) SparsePauliOp
    construction places pauli[0] on the *last* entry of qubits instead."""
    alpha = Parameter("alpha")
    # pauli[0]='X' on qubits[0]=0, pauli[1]='Z' on qubits[1]=1
    term = PauliTerm("XZ", (0, 1), parameter_index=0, coefficient=1.0, tie_group=0)
    gate = term.to_gate(alpha)

    from qiskit import QuantumCircuit

    qc = QuantumCircuit(2)
    qc.append(gate, [0, 1])
    bound = qc.assign_parameters({alpha: 0.5})
    actual = Operator(bound).data

    # Qiskit ordering: qubit 0 is least-significant, so X-on-q0,Z-on-q1 is kron(Z, X).
    xz_correct = np.kron(_Z, _X)
    expected = expm(1j * np.pi * 1.0 * 0.5 * xz_correct)
    assert np.allclose(actual, expected)
