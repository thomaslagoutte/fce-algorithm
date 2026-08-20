"""Dedicated sign/ordering equivalence tests for the Circuits Layer — FR-011.

Every sign, gate-ordering, and basis-change claim this module's design relies
on is checked here directly against a hand-built target or a real Qiskit
gate, independent of any end-to-end oracle agreement (research.md R3, R5, R6).
"""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import Operator, SparsePauliOp, Statevector

from fourierlearn.circuits import (
    _append_parity_fold_block_swapped,
    _build_registers,
    _increment_circuit,
    basis_change_gates,
    compile_frequency_circuit,
)
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir

# --- T003/T004: parity-fold block sign convention (research.md R3) --------


def _h_z_h_ir():
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="alpha", tie_group=0, coefficient=1.0),
    ]
    return build_ir(num_qubits=1, uploads=uploads, observable=SparsePauliOp("Z"))


def _amplitude_at(state: Statevector, freq_val: int, ancilla_val: int, circuit_val: int, freq_width: int) -> complex:
    """Global qubit index for a state built from registers added in order
    (freq[freq_width qubits], ancilla[1 qubit], circuit[1 qubit]): Qiskit
    numbers qubit 0 as the least-significant bit overall, and registers are
    laid out contiguously in the order they were added to the circuit."""
    index = freq_val | (ancilla_val << freq_width) | (circuit_val << (freq_width + 1))
    return complex(state.data[index])


def test_parity_fold_block_matches_hand_built_target() -> None:
    """research.md R3: H-Z(theta)-H, r_j=1, L=1 (width-3 register). The
    correct convention (ancilla=0/even parity -> increment, ancilla=1/odd ->
    decrement) must reproduce the independently hand-derived 4-term
    superposition: l=+1,k=0: 0.5; l=+1,k=1: 0.5; l=-1,k=0: 0.5; l=-1,k=1: -0.5.
    """
    ir = _h_z_h_ir()
    qc = compile_frequency_circuit(ir)
    circuit_qubit = qc.qregs[-1][0]

    full = QuantumCircuit(*qc.qregs)
    full.h(circuit_qubit)
    full.compose(qc, inplace=True)
    full.h(circuit_qubit)

    state = Statevector(full)
    freq_width = len(qc.qregs[0])

    got_p1_k0 = _amplitude_at(state, 1, 0, 0, freq_width)
    got_p1_k1 = _amplitude_at(state, 1, 0, 1, freq_width)
    got_m1_k0 = _amplitude_at(state, (-1) % (2**freq_width), 0, 0, freq_width)
    got_m1_k1 = _amplitude_at(state, (-1) % (2**freq_width), 0, 1, freq_width)

    assert math.isclose(got_p1_k0.real, 0.5, abs_tol=1e-9) and math.isclose(got_p1_k0.imag, 0.0, abs_tol=1e-9)
    assert math.isclose(got_p1_k1.real, 0.5, abs_tol=1e-9) and math.isclose(got_p1_k1.imag, 0.0, abs_tol=1e-9)
    assert math.isclose(got_m1_k0.real, 0.5, abs_tol=1e-9) and math.isclose(got_m1_k0.imag, 0.0, abs_tol=1e-9)
    assert math.isclose(got_m1_k1.real, -0.5, abs_tol=1e-9) and math.isclose(got_m1_k1.imag, 0.0, abs_tol=1e-9)


def test_mcx_ctrl_state_bit_ordering_truth_table() -> None:
    """Minimal, dedicated truth-table check of Qiskit's own `MCX` `ctrl_state`
    string convention (rightmost character = first control qubit in the
    `controls` list) -- the exact assumption `_controlled_increment_direct`
    depends on (research.md R5.7: determined experimentally, not assumed from
    the docstring, after the first attempt used the opposite ordering and
    silently produced a different operator). Independent of the larger
    parity-fold/reversed-pass tests: if Qiskit ever changes this convention,
    this test fails specifically, pointing directly at the one assumption
    that broke rather than surfacing as an opaque mismatch inside a much
    larger circuit."""
    # 2 controls (q0, q1), 1 target (q2). ctrl_state="01" should require
    # control q1 = 0 and control q0 = 1 (rightmost char = first control, q0).
    qc = QuantumCircuit(3)
    qc.mcx([0, 1], 2, ctrl_state="01")
    op = Operator(qc).data

    for q0 in (0, 1):
        for q1 in (0, 1):
            index = q0 + 2 * q1  # q0 is qubit 0 (LSB), q1 is qubit 1
            column = op[:, index]
            flipped = int(np.argmax(np.abs(column))) != index
            expected_flip = q0 == 1 and q1 == 0
            assert flipped == expected_flip, (q0, q1, flipped, expected_flip)


def test_flipped_ancilla_convention_would_fail_this_test() -> None:
    """Sanity check on the sign-convention test itself (mirrors Spec 1's own
    test_flipped_sign_would_fail_this_test pattern): the wrong parity
    assignment (ancilla=1 -> increment, ancilla=0 -> decrement) must NOT
    reproduce research.md R3's target -- otherwise T003 could not catch the
    bug it exists for."""
    freq_width = 3
    qc = QuantumCircuit(freq_width + 2)
    freq = list(range(freq_width))
    anc = freq_width
    circ = freq_width + 1

    increment = _increment_circuit(freq_width)
    decrement = increment.inverse()

    qc.h(circ)
    qc.cx(circ, anc)
    # WRONG convention (deliberately swapped relative to research.md R3):
    qc.append(increment.to_gate(label="V+").control(1, ctrl_state=1), [anc] + freq)
    qc.append(decrement.to_gate(label="V-").control(1, ctrl_state=0), [anc] + freq)
    qc.cx(circ, anc)
    qc.h(circ)

    state = Statevector(qc)
    got_p1_k0 = _amplitude_at(state, 1, 0, 0, freq_width)
    got_p1_k1 = _amplitude_at(state, 1, 0, 1, freq_width)
    got_m1_k0 = _amplitude_at(state, (-1) % (2**freq_width), 0, 0, freq_width)
    got_m1_k1 = _amplitude_at(state, (-1) % (2**freq_width), 0, 1, freq_width)

    matches = (
        math.isclose(got_p1_k0.real, 0.5, abs_tol=1e-9)
        and math.isclose(got_p1_k1.real, 0.5, abs_tol=1e-9)
        and math.isclose(got_m1_k0.real, 0.5, abs_tol=1e-9)
        and math.isclose(got_m1_k1.real, -0.5, abs_tol=1e-9)
    )
    assert not matches


# --- T005: basis-change gate equivalence (research.md R6) ------------------


def _z_rotation_gate(alpha_value: float) -> QuantumCircuit:
    """e^{i pi alpha Z} via Qiskit's RZ: RZ(theta) = e^{-i theta/2 Z}, so
    theta = -2*pi*alpha gives e^{i pi alpha Z} exactly."""
    qc = QuantumCircuit(1)
    qc.rz(-2 * math.pi * alpha_value, 0)
    return qc


def test_basis_change_x_matches_real_pauli_evolution_gate() -> None:
    alpha_value = 0.4123
    w_dagger, w = basis_change_gates("X")

    qc = QuantumCircuit(1)
    qc.compose(w_dagger, [0], inplace=True)
    qc.compose(_z_rotation_gate(alpha_value), [0], inplace=True)
    qc.compose(w, [0], inplace=True)

    actual = Operator(qc)
    expected = Operator(PauliEvolutionGate(SparsePauliOp("X"), time=-math.pi * alpha_value))
    assert actual.equiv(expected)


def test_basis_change_y_matches_real_pauli_evolution_gate() -> None:
    alpha_value = 0.5321
    w_dagger, w = basis_change_gates("Y")

    qc = QuantumCircuit(1)
    qc.compose(w_dagger, [0], inplace=True)
    qc.compose(_z_rotation_gate(alpha_value), [0], inplace=True)
    qc.compose(w, [0], inplace=True)

    actual = Operator(qc)
    expected = Operator(PauliEvolutionGate(SparsePauliOp("Y"), time=-math.pi * alpha_value))
    assert actual.equiv(expected)


def test_basis_change_y_wrong_ordering_would_fail() -> None:
    """Sanity check: the rejected orderings from research.md R6's own sweep
    (e.g. W = H@S instead of S@H) must NOT reproduce the correct Y-encoding
    gate, proving the accepted ordering was not arbitrary."""
    alpha_value = 0.5321
    wrong_w_dagger = QuantumCircuit(1)
    wrong_w_dagger.h(0)
    wrong_w_dagger.s(0)
    wrong_w = QuantumCircuit(1)
    wrong_w.sdg(0)
    wrong_w.h(0)

    qc = QuantumCircuit(1)
    qc.compose(wrong_w_dagger, [0], inplace=True)
    qc.compose(_z_rotation_gate(alpha_value), [0], inplace=True)
    qc.compose(wrong_w, [0], inplace=True)

    actual = Operator(qc)
    expected = Operator(PauliEvolutionGate(SparsePauliOp("Y"), time=-math.pi * alpha_value))
    assert not actual.equiv(expected)


# --- T009: reversed-pass stress-test equivalence (research.md R5.4/R5.5/R5.6) --


def _tied_interleaved_stress_ir():
    """3 parameters: A, B both tied multiplicity 2 (non-adjacent tied terms),
    C untied, gates interleaved [A1, B1, C, A2, B2] -- research.md R5.4."""
    uploads = [
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="A", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="B", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="C", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(1,), parameter_label="A", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="B", tie_group=0, coefficient=1.0),
    ]
    return build_ir(num_qubits=2, uploads=uploads, observable=SparsePauliOp("II"))


def test_reversed_pass_equals_literal_circuit_inverse() -> None:
    """research.md R5.4/R5.5/R5.6: the literal inverse of the assembled
    forward circuit must be exactly equal to an independently constructed
    reverse-order pass with role-swapped shift primitives, at a genuinely
    multi-parameter, tied-multiplicity, interleaved, shared-ancilla stress
    level -- not only the minimal case.

    **Performance note, decided during implementation**: at this stress
    level the combined circuit spans 14 qubits (register widths 4+4+3, one
    ancilla, two circuit qubits). `qiskit.quantum_info.Operator` reconstructs
    the full 16384x16384 dense matrix, whose fixed cost was measured directly
    at ~10s for a *single* gate on 14 qubits (~3+ minutes for this circuit's
    full gate count) -- impractical for a test suite. `Statevector` evolution
    of the same two circuits was measured at ~2-3s each. Since two distinct
    unitaries agreeing on a Haar-random state (checked here via exact complex
    amplitudes, not just probabilities, so a global-phase-only difference
    would still be caught) has probability zero of occurring by chance, and
    research.md R5.6 already established `==` (not just `.equiv()`) holds
    for this exact construction via real dense `Operator` objects at a
    smaller-but-still-representative 2-parameter scale, checking exact
    statevector agreement on `|0...0>` *and* an independent random state here
    is the computationally tractable equivalent of the full operator
    equality this test's docstring originally specified -- not a weakening
    of what is actually being verified.
    """
    ir = _tied_interleaved_stress_ir()
    forward = compile_frequency_circuit(ir)
    reversed_circuit = forward.inverse()

    freq_registers, ancilla, circuit_reg = _build_registers(ir)
    manually_reversed = QuantumCircuit(*[freq_registers[p.index] for p in ir.parameters()], ancilla, circuit_reg)
    for gate in reversed(ir.gates):
        _append_parity_fold_block_swapped(
            manually_reversed, gate, freq_registers[gate.parameter_index], ancilla[0], circuit_reg
        )

    n = reversed_circuit.num_qubits
    zero_state = Statevector.from_label("0" * n)
    rng = np.random.default_rng(20260820)
    random_vec = rng.normal(size=2**n) + 1j * rng.normal(size=2**n)
    random_vec /= np.linalg.norm(random_vec)
    random_state = Statevector(random_vec)

    for initial_state in (zero_state, random_state):
        r1_state = initial_state.evolve(reversed_circuit)
        r2_state = initial_state.evolve(manually_reversed)
        assert np.allclose(r1_state.data, r2_state.data, atol=1e-9)
