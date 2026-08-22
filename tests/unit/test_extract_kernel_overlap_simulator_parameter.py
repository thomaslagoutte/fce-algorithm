"""Spec 11 T016 — FR-006/FR-007 (deliverable c) mirrored for
`estimate_kernel_overlap` (Spec 10): the additive `simulator: AerSimulator
| None = None` parameter behaves identically to today's code when
omitted/`None`, and genuinely uses a caller-supplied instance otherwise.
"""

from __future__ import annotations

from qiskit.circuit.library import RYGate
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

from fourierlearn.circuits import compile_kernel_overlap_circuit
from fourierlearn.extract import estimate_kernel_overlap
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import kernel_overlap_oracle


class _InstrumentedAerSimulator(AerSimulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_call_count = 0

    def run(self, *args, **kwargs):
        self.run_call_count += 1
        return super().run(*args, **kwargs)


def _one_qubit_ir(theta: float) -> PauliEncodedCircuitIR:
    gates = (
        FixedGate(RYGate(theta), (0,)),
        PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0),
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("Z"))


def _fixture_circuit_and_registers():
    ir_x = _one_qubit_ir(0.9)
    ir_x_prime = _one_qubit_ir(1.7)
    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_reg = qc.qregs[-2]
    selector = qc.qregs[-1][0]
    expected = kernel_overlap_oracle(ir_x, ir_x_prime)
    return qc, selector, circuit_reg, expected


def test_estimate_kernel_overlap_simulator_none_matches_omitted() -> None:
    qc, selector, circuit_reg, _ = _fixture_circuit_and_registers()

    est_omitted, shots_omitted = estimate_kernel_overlap(qc, selector, circuit_reg, shots=5_000, seed=3)
    est_explicit_none, shots_none = estimate_kernel_overlap(
        qc, selector, circuit_reg, shots=5_000, seed=3, simulator=None
    )

    assert est_omitted == est_explicit_none
    assert shots_omitted == shots_none == 5_000


def test_estimate_kernel_overlap_uses_the_supplied_simulator_instance() -> None:
    qc, selector, circuit_reg, expected = _fixture_circuit_and_registers()
    sim = _InstrumentedAerSimulator()

    estimate, _ = estimate_kernel_overlap(qc, selector, circuit_reg, shots=200_000, seed=3, simulator=sim)

    assert sim.run_call_count == 1
    assert abs(estimate - expected) < 0.05
