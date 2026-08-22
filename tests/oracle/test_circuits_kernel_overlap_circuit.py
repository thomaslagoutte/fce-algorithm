"""T002/T003 — `compile_kernel_overlap_circuit`'s
`⟨Z_selector⊗I_{freq,ancilla}⊗|0⟩⟨0|_circuit⟩` readout matches
`reference.kernel_overlap_oracle`'s `Re(⟨b(x)|b(x')⟩)` to machine
precision (FR-002 Acceptance Scenario 2), on both the already-verified
1-qubit/1-parameter fixture (spec.md Finding 2) and a richer
2-qubit/2-tied-parameter fixture (spec.md's own Assumptions: this
construction must be checked against more than the single-qubit case
before being trusted generally).

FR-003 note: `compile_kernel_overlap_circuit`'s selector-controlled
classical-input preparation is built from the exact same
`_append_multiplexed_gates` helper Spec 9's LCU observable fold uses
(`circuits._append_multiplexed_fold`) — literal code reuse, not a second
implementation of the controlled-branch-append idiom (Constitution §9.4).
This feature does NOT fold a weighted-Pauli-sum OBSERVABLE into the kernel-
overlap construction itself: `b(x)`'s own definition (the Fourier
coefficients of `⟨0|U(alpha)|0⟩`, verified against `reference.
amplitude_coefficients`) has no observable to fold in the first place — an
`O`-sandwiched generalization (`⟨0|U†OU|0⟩`-based feature vectors) would be
a structurally different construction, out of this feature's scope. Spec
9's own existing LCU test suite (unchanged by the `_append_multiplexed_
fold`/`_append_multiplexed_gates` refactor here) is the regression coverage
proving that refactor preserved its behavior exactly.
"""

from __future__ import annotations

import math

from qiskit.circuit.library import RXGate, RYGate
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import compile_kernel_overlap_circuit
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import kernel_overlap_oracle

_TOL = 1e-9


def _readout(qc) -> float:
    """Exact, test-only computation of `⟨Z_selector⊗I⊗|0⟩⟨0|_circuit⟩` via
    `Statevector` — never used in production (Constitution §3.4)."""
    state = Statevector(qc)
    circuit_reg = qc.qregs[-2]
    selector_reg = qc.qregs[-1]
    qubit_order = list(qc.qubits)
    selector_position = qubit_order.index(selector_reg[0])
    circuit_positions = [qubit_order.index(q) for q in circuit_reg]

    n = len(qubit_order)
    total = 0.0
    for index, amplitude in enumerate(state.data):
        bits = [(index >> k) & 1 for k in range(n)]
        if any(bits[p] != 0 for p in circuit_positions):
            continue
        sign = 1.0 if bits[selector_position] == 0 else -1.0
        total += sign * abs(amplitude) ** 2
    return total


def _one_qubit_ir(theta: float) -> PauliEncodedCircuitIR:
    gates = (
        FixedGate(RYGate(theta), (0,)),
        PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0),
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("Z"))


def test_kernel_overlap_circuit_matches_oracle_on_one_qubit_fixture() -> None:
    """spec.md Finding 2's own fixture: `RY(0.9)` vs `RY(1.7)`."""
    ir_x = _one_qubit_ir(0.9)
    ir_x_prime = _one_qubit_ir(1.7)

    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_value = _readout(qc)
    oracle_value = kernel_overlap_oracle(ir_x, ir_x_prime)

    assert math.isclose(circuit_value, oracle_value, abs_tol=_TOL), (circuit_value, oracle_value)


def test_kernel_overlap_circuit_diagonal_entry_matches_oracle() -> None:
    """Edge case (spec.md): `x=x'` — the selector's two branches are
    identical, but the overlap formula itself must still reduce cleanly to
    `k(x,x)=‖b(x)‖^2`, a valid, real, non-negative value."""
    ir_x = _one_qubit_ir(0.3)
    ir_x_prime = _one_qubit_ir(0.3)

    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_value = _readout(qc)
    oracle_value = kernel_overlap_oracle(ir_x, ir_x_prime)

    assert circuit_value >= 0.0
    assert math.isclose(circuit_value, oracle_value, abs_tol=_TOL)


def _richer_two_qubit_ir(theta_a: float, theta_b: float) -> PauliEncodedCircuitIR:
    """A 2-qubit, 2-parameter fixture where one parameter (index 1) is tied
    across two Pauli strings — a genuinely richer structure than the
    1-qubit case above, satisfying spec.md's own Assumptions requirement."""
    gates = (
        FixedGate(RYGate(theta_a), (0,)),
        FixedGate(RXGate(theta_b), (1,)),
        PauliTerm(pauli="XI", qubits=(0, 1), parameter_index=0, coefficient=1.0, tie_group=0),
        PauliTerm(pauli="IZ", qubits=(0, 1), parameter_index=1, coefficient=0.5, tie_group=0),
        PauliTerm(pauli="YX", qubits=(0, 1), parameter_index=0, coefficient=1.0, tie_group=1),
    )
    return PauliEncodedCircuitIR(num_qubits=2, gates=gates, observable=SparsePauliOp("ZI"))


def test_kernel_overlap_circuit_matches_oracle_on_richer_two_qubit_fixture() -> None:
    ir_x = _richer_two_qubit_ir(0.9, 0.4)
    ir_x_prime = _richer_two_qubit_ir(1.7, -0.2)

    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_value = _readout(qc)
    oracle_value = kernel_overlap_oracle(ir_x, ir_x_prime)

    assert math.isclose(circuit_value, oracle_value, abs_tol=1e-8), (circuit_value, oracle_value)


def test_kernel_overlap_circuit_richer_fixture_diagonal_entry() -> None:
    ir_x = _richer_two_qubit_ir(0.5, 0.5)
    ir_x_prime = _richer_two_qubit_ir(0.5, 0.5)

    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_value = _readout(qc)
    oracle_value = kernel_overlap_oracle(ir_x, ir_x_prime)

    assert circuit_value >= 0.0
    assert math.isclose(circuit_value, oracle_value, abs_tol=1e-8)
