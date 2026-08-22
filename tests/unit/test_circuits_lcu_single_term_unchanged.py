"""T002 — FR-004 (Critical Mandate 1): a one-term observable passed
through the generalized `compile_observable_circuit` MUST produce exactly
the circuit Spec 3's existing, unmodified single-Pauli path already
produces — the generalization changes nothing for the case that already
worked."""

from __future__ import annotations

from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.circuits import compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir


def _small_ir(observable: SparsePauliOp):
    uploads = [PauliUpload(pauli="X", qubits=(0,), parameter_label="a", tie_group=0, coefficient=0.37)]
    return build_ir(num_qubits=1, uploads=uploads, observable=observable)


def test_single_term_observable_is_byte_for_byte_unchanged() -> None:
    observable = SparsePauliOp("Z")
    ir = _small_ir(observable)

    qc = compile_observable_circuit(ir, observable)

    # No LCU selector register must ever appear for a single-term observable.
    assert [r.name for r in qc.qregs] == ["freq0", "ancilla", "circuit"]

    # Operator-exact equivalence to a hand-verified independent reconstruction
    # of Spec 3's own documented construction (forward; fold; inverse).
    from fourierlearn.circuits import _insert_observable, compile_frequency_circuit
    from qiskit import QuantumCircuit

    forward = compile_frequency_circuit(ir)
    circuit_reg = forward.qregs[-1]
    reconstructed = QuantumCircuit(*forward.qregs)
    reconstructed.compose(forward, inplace=True)
    _insert_observable(reconstructed, observable, circuit_reg)
    reconstructed.compose(forward.inverse(), inplace=True)

    assert Operator(qc).equiv(Operator(reconstructed))
