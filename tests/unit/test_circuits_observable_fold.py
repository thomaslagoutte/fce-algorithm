"""Core `compile_observable_circuit` acceptance tests — FR-006, FR-007,
FR-008 (research.md R5, R7)."""

from __future__ import annotations

import math
from unittest import mock

from qiskit.circuit.library import HGate
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn import circuits
from fourierlearn.circuits import compile_frequency_circuit, compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients


def _h_z_h_ir_with_fixed_gates() -> PauliEncodedCircuitIR:
    """1 qubit, H - Z(alpha) - H, observable folded separately per test."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="alpha", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))
    gates = (FixedGate(HGate(), (0,)),) + ir.gates + (FixedGate(HGate(), (0,)),)
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=ir.observable)


def _post_selected_amplitude_table(qc, freq_widths, num_circuit_qubits):
    state = Statevector(qc)
    table = {}
    total_freq_qubits = sum(freq_widths)
    for raw_flat in range(2**total_freq_qubits):
        # decompose raw_flat into per-parameter raw register values (little
        # register order matches qc.qregs[:len(freq_widths)])
        remaining = raw_flat
        raw_values = []
        for width in freq_widths:
            raw_values.append(remaining % (2**width))
            remaining //= 2**width
        index = raw_flat | (0 << total_freq_qubits) | (0 << (total_freq_qubits + 1))
        amp = complex(state.data[index])
        if abs(amp) > 1e-9:
            ls = tuple(int(_signed(v, w)) for v, w in zip(raw_values, freq_widths))
            table[ls] = amp
    return table


def _signed(raw_value: int, width: int) -> int:
    half = 2 ** (width - 1)
    return raw_value if raw_value <= half else raw_value - 2**width


def test_observable_circuit_shares_identical_registers_with_frequency_circuit() -> None:
    """Acceptance Scenario 1: no additional or differently-sized registers
    are introduced by folding in the observable."""
    ir = _h_z_h_ir_with_fixed_gates()
    freq_only = compile_frequency_circuit(ir)
    with_obs = compile_observable_circuit(ir, SparsePauliOp("Z"))

    assert [len(r) for r in freq_only.qregs] == [len(r) for r in with_obs.qregs]
    assert freq_only.qregs[0].name == with_obs.qregs[0].name


def test_post_selected_amplitudes_match_hand_derived_coefficients_one_parameter() -> None:
    """Acceptance Scenario 2: post-selected on ancilla/circuit register = 0,
    the frequency register's amplitudes match the observable's known Fourier
    coefficients -- checked against Spec 1's own oracle directly."""
    ir = _h_z_h_ir_with_fixed_gates()
    expected = oracle_coefficients(ir)

    qc = compile_observable_circuit(ir, SparsePauliOp("Z"))
    freq_width = len(qc.qregs[0])
    got = _post_selected_amplitude_table(qc, [freq_width], ir.num_qubits)

    for l_tuple, expected_val in expected.items():
        got_val = got.get(l_tuple, 0j)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=1e-9)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=1e-9)


def test_two_parameter_register_reflects_forward_minus_reverse_difference() -> None:
    """Acceptance Scenario 3: for a 2-parameter circuit, each parameter's
    register reflects forward-minus-reverse, not the forward contribution
    alone -- checked against the oracle directly."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="a", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="b", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=2, uploads=uploads, observable=SparsePauliOp("ZZ"))
    expected = oracle_coefficients(ir)

    qc = compile_observable_circuit(ir, SparsePauliOp("ZZ"))
    freq_widths = [len(qc.qregs[0]), len(qc.qregs[1])]
    got = _post_selected_amplitude_table(qc, freq_widths, ir.num_qubits)

    for l_tuple, expected_val in expected.items():
        got_val = got.get(l_tuple, 0j)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=1e-9)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=1e-9)


# --- T013 (User Story 3): non-diagonal observables ------------------------


def test_non_diagonal_observable_is_folded_in_without_rejection() -> None:
    """Acceptance Scenario 1 (US3): a non-Z observable is accepted and
    folded in, not rejected."""
    ir = _h_z_h_ir_with_fixed_gates()
    qc = compile_observable_circuit(ir, SparsePauliOp("X"))
    assert qc is not None


def test_non_diagonal_observable_matches_equivalent_z_type_expression() -> None:
    """Acceptance Scenario 2 (US3): the same physical observable expressed
    as X (via the basis-change path) matches the independently-verified
    <0|U(alpha)^dagger X U(alpha)|0> ground truth from research.md R7 --
    an X/Y observable is genuinely non-degenerate here (not the trivial
    all-zero case a single Z-fold-only circuit would give)."""
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="alpha", tie_group=0, coefficient=1.0),
    ]
    ir = build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("X"))
    from qiskit.circuit.library import SGate

    gates = ir.gates + (FixedGate(SGate(), (0,)),) + ir.gates
    ir_two_upload = PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))
    expected = oracle_coefficients(ir_two_upload)

    qc = compile_observable_circuit(ir_two_upload, SparsePauliOp("X"))
    freq_width = len(qc.qregs[0])
    got = _post_selected_amplitude_table(qc, [freq_width], ir_two_upload.num_qubits)

    for l_tuple, expected_val in expected.items():
        got_val = got.get(l_tuple, 0j)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=1e-9)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=1e-9)


def test_asymmetric_multiqubit_observable_respects_little_endian_labels() -> None:
    """`_insert_observable` reverses the SparsePauliOp label before indexing
    qubits (Qiskit's own little-endian convention: rightmost character =
    qubit 0). This test proves that reversal is correct, not merely present,
    by using a deliberately ASYMMETRIC observable ('IXZ': Z@q0, X@q1, I@q2)
    on a circuit where qubit 0 and qubit 2 have DIFFERENT structure -- q0
    gets H-Z(alpha)-H (genuinely alpha-dependent under a Z observable), q2
    gets no gates at all (stays |0>, so a Z observable there would read a
    trivial constant `1`, not alpha-dependent). Getting the reversal
    backwards would silently apply the observable's `Z` half to q2 and its
    `I` half to q0 instead of the reverse -- discarding q0's genuine
    alpha-dependence entirely and replacing it with q2's trivial constant.
    A symmetric observable (e.g. 'ZIZ') could not catch this, since swapping
    two identical halves is invisible."""
    upload = build_ir(3, [PauliUpload("Z", (0,), "alpha", 0, 1.0)], SparsePauliOp("III")).gates
    gates = (
        (FixedGate(HGate(), (0,)), FixedGate(HGate(), (1,)))
        + upload
        + (FixedGate(HGate(), (0,)),)
    )
    ir = PauliEncodedCircuitIR(num_qubits=3, gates=gates, observable=SparsePauliOp("IXZ"))
    expected = oracle_coefficients(ir)

    qc = compile_observable_circuit(ir, SparsePauliOp("IXZ"))
    freq_width = len(qc.qregs[0])
    got = _post_selected_amplitude_table(qc, [freq_width], ir.num_qubits)

    non_dc_confirmed = False
    for l_tuple, expected_val in expected.items():
        got_val = got.get(l_tuple, 0j)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=1e-9)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=1e-9)
        if l_tuple != (0,) and abs(expected_val) > 1e-2:
            non_dc_confirmed = True

    assert non_dc_confirmed, "expected genuine alpha-dependence at a non-DC l from q0's H-Z-H structure"


def test_compile_observable_circuit_uses_shared_basis_change_helper() -> None:
    """Architectural spy (programmatic proof of Constitution §9.4's
    single-code-path requirement): compiling a non-Z observable must
    actually call the shared `basis_change_gates` helper -- numeric
    agreement alone cannot distinguish "reuses the shared helper" from
    "has its own, coincidentally-identical implementation"."""
    ir = _h_z_h_ir_with_fixed_gates()
    with mock.patch.object(circuits, "basis_change_gates", wraps=circuits.basis_change_gates) as spy:
        compile_observable_circuit(ir, SparsePauliOp("X"))
        called_letters = {call.args[0] for call in spy.call_args_list}
        assert "X" in called_letters
