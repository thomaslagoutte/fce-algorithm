"""T007 — `extract.estimate_kernel_overlap`'s finite-shot estimate of
`⟨Z_selector⊗I⊗|0⟩⟨0|_circuit⟩` converges to `reference.kernel_overlap_
oracle`'s exact `Re(⟨b(x)|b(x')⟩)` within that shot count's own
Hoeffding-derived tolerance (Constitution §4.4), matching this project's
own established convergence-test convention (`test_extract_convergence.py`).
"""

from __future__ import annotations

import math

from qiskit.circuit.library import RYGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.circuits import compile_kernel_overlap_circuit
from fourierlearn.extract import estimate_kernel_overlap
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import kernel_overlap_oracle

_DELTA = 0.01
_SEED = 20260821  # fixed, arbitrarily chosen -- not tuned by trying seeds


def _one_qubit_ir(theta: float) -> PauliEncodedCircuitIR:
    gates = (
        FixedGate(RYGate(theta), (0,)),
        PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0),
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("Z"))


def _hoeffding_eps(shots: int, delta: float = _DELTA) -> float:
    return math.sqrt(2 * math.log(2 / delta) / shots)


def test_shot_based_kernel_overlap_estimate_converges_to_oracle() -> None:
    ir_x = _one_qubit_ir(0.9)
    ir_x_prime = _one_qubit_ir(1.7)
    qc = compile_kernel_overlap_circuit(ir_x, ir_x_prime)
    circuit_reg = qc.qregs[-2]
    selector = qc.qregs[-1][0]

    expected = kernel_overlap_oracle(ir_x, ir_x_prime)

    shot_counts = [2_000, 20_000, 200_000]
    errors_by_shots: dict[int, float] = {}
    for shots in shot_counts:
        eps = _hoeffding_eps(shots)
        estimate, used_shots = estimate_kernel_overlap(qc, selector, circuit_reg, shots=shots, seed=_SEED)
        assert used_shots == shots
        error = abs(estimate - expected)
        assert error < eps, (shots, estimate, expected, eps)
        errors_by_shots[shots] = error

    assert errors_by_shots[shot_counts[-1]] <= errors_by_shots[shot_counts[0]] + 1e-6
