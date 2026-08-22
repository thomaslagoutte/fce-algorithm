"""T008 — FR-004 (Critical Mandate 1, Constitution §11.11):
`compile_kernel_overlap_circuit` accepts only two classical-input
declarations sharing an identical encoded-parameter structure. It has no
code path that would silently treat two DIFFERENTLY-encoded IRs (different
`α` structure) as a fidelity kernel over `α` — any structural mismatch is
rejected explicitly via `KernelInputStructureMismatchError`, never silently
accepted.
"""

from __future__ import annotations

import pytest
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.circuits import KernelInputStructureMismatchError, compile_kernel_overlap_circuit
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm


def _ir(theta: float, coefficient: float = 1.0) -> PauliEncodedCircuitIR:
    gates = (
        FixedGate(RYGate(theta), (0,)),
        PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=coefficient, tie_group=0),
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("Z"))


def test_two_classical_inputs_sharing_encoded_structure_is_accepted() -> None:
    ir_x = _ir(0.9)
    ir_x_prime = _ir(1.7)
    # Differ only in their FixedGate -- must be accepted (this is exactly
    # what "two classical inputs" means).
    compile_kernel_overlap_circuit(ir_x, ir_x_prime)


def test_differently_encoded_alpha_structure_is_rejected_not_silently_accepted() -> None:
    """Constitution §11.11: this feature must NOT drift into a fidelity
    kernel over `alpha` -- passing two IRs with a DIFFERENT `alpha`-encoding
    structure (a different coefficient here) is not "two classical inputs
    sharing a structure," and must be rejected explicitly."""
    ir_x = _ir(0.9, coefficient=1.0)
    ir_alpha_varied = _ir(0.9, coefficient=2.0)  # same fixed gate, DIFFERENT encoded structure

    with pytest.raises(KernelInputStructureMismatchError):
        compile_kernel_overlap_circuit(ir_x, ir_alpha_varied)


def test_mismatched_qubit_count_is_rejected() -> None:
    ir_x = _ir(0.9)
    two_qubit_ir = PauliEncodedCircuitIR(
        num_qubits=2,
        gates=(
            FixedGate(RYGate(0.9), (0,)),
            PauliTerm(pauli="XI", qubits=(0, 1), parameter_index=0, coefficient=1.0, tie_group=0),
        ),
        observable=SparsePauliOp("ZI"),
    )
    with pytest.raises(KernelInputStructureMismatchError):
        compile_kernel_overlap_circuit(ir_x, two_qubit_ir)
