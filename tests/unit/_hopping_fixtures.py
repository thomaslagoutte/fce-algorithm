"""Shared test-only fixture for T010/T011 (User Story 2): the bare
3-qubit A_e-then-B_e circuit, built directly via `PauliUpload`/`build_ir`
(Constitution §9.4 — reuses the existing tie-group mechanism verbatim, no
new production code). Mirrors research.md R3 exactly: coefficient `1.0`
for both terms reproduces Proposition 5.1(iii) in its own literal form,
`e^{i*pi*alpha*(Ae+Be)} = e^{i*pi*alpha*Ae} e^{i*pi*alpha*Be}` — distinct
from the model's own `h_e=(1/2)(Ae+Be)`-scaled encoding (T007's
`weight=0.5*J_e`), which serves the separate purpose of representing the
physical `H = J_e*h_e` term."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import PauliEncodedCircuitIR

# Qubit layout: 0=v0 (matter), 1=e01 (gauge), 2=v1 (matter) -- matches
# research.md R2's own convention (A_e=X_v0 Z_e01 X_v1, qubits=(0,2,1)).
_QUBITS = (0, 2, 1)


def two_gate_circuit(a_param_label: str, b_param_label: str) -> tuple[QuantumCircuit, dict[int, Parameter], PauliEncodedCircuitIR]:
    """Build the bare 3-qubit circuit applying A_e's gate then B_e's gate,
    each tied to its own declared `parameter_label` (same label -> tied;
    distinct labels -> untied, two independent parameters)."""
    uploads = [
        PauliUpload(pauli="XZX", qubits=_QUBITS, parameter_label=a_param_label, tie_group=0, coefficient=1.0),
        PauliUpload(pauli="YZY", qubits=_QUBITS, parameter_label=b_param_label, tie_group=0, coefficient=1.0),
    ]
    small_ir = build_ir(num_qubits=3, uploads=uploads, observable=SparsePauliOp("III"))
    symbols = small_ir.parameter_symbols()
    qc = QuantumCircuit(3)
    for gate in small_ir.gates:
        qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
    return qc, symbols, small_ir
