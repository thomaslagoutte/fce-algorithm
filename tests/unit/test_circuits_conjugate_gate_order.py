"""T013 — the dedicated proof that complex conjugation preserves gate
order (unlike the Hermitian adjoint, which reverses it): for a 3-gate
mixed sequence (odd-Y, even-Y, odd-Y terms), `conjugate_ir` (applying the
per-gate rule IN THE SAME ORDER) must match `Operator(U).conjugate()`
exactly; reversing the gate order must NOT."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.circuits import _pauli_term_conjugate, conjugate_ir
from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm

_ALPHA = 0.44


def _ir_operator(gates: tuple, num_qubits: int) -> np.ndarray:
    p = Parameter("a")
    qc = QuantumCircuit(num_qubits)
    for term in gates:
        qc.append(term.to_gate(p), term.qubits)
    bound = qc.assign_parameters({p: _ALPHA})
    return Operator(bound).data


def test_conjugate_ir_preserves_gate_order() -> None:
    terms = (
        PauliTerm(pauli="Y", qubits=(0,), parameter_index=0, coefficient=0.3, tie_group=0),
        PauliTerm(pauli="YY", qubits=(0, 1), parameter_index=1, coefficient=0.6, tie_group=0),
        PauliTerm(pauli="XY", qubits=(0, 1), parameter_index=2, coefficient=0.2, tie_group=0),
    )
    ir = PauliEncodedCircuitIR(num_qubits=2, gates=terms, observable=SparsePauliOp("II"))

    true_conjugate = _ir_operator(terms, 2).conjugate()

    conjugated = conjugate_ir(ir)
    same_order_operator = _ir_operator(conjugated.gates, 2)
    diff_same_order = np.max(np.abs(true_conjugate - same_order_operator))
    assert diff_same_order < 1e-10, "same-order, per-gate conjugation must match exactly"

    reversed_terms = tuple(reversed(conjugated.gates))
    reversed_operator = _ir_operator(reversed_terms, 2)
    diff_reversed = np.max(np.abs(true_conjugate - reversed_operator))
    assert diff_reversed > 0.1, "reversing gate order must NOT match (conjugation != adjoint)"
