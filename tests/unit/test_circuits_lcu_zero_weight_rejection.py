"""Critical implementation instruction #2 (Spec 9 /speckit.implement):
a term with beta_h=0 must be rejected explicitly, at construction time,
with a clear ValueError -- never silently accepted (which would bloat the
LCU selector register for a term that can never contribute)."""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.circuits import ZeroWeightError, _insert_observable_lcu, _validate_lcu_weights


def test_zero_weight_term_is_rejected_at_construction() -> None:
    circuit_reg = QuantumRegister(1, "circuit")
    qc = QuantumCircuit(circuit_reg)
    observable = SparsePauliOp(["Z", "X"], coeffs=[1.0, 0.0])
    with pytest.raises(ZeroWeightError, match="beta_h=0"):
        _insert_observable_lcu(qc, observable, circuit_reg)


def test_validate_lcu_weights_rejects_any_zero_entry_regardless_of_position() -> None:
    with pytest.raises(ZeroWeightError):
        _validate_lcu_weights([1.0, 2.0, 0.0])
    with pytest.raises(ZeroWeightError):
        _validate_lcu_weights([0.0, 1.0, 2.0])
    # A declaration with no zero weights must pass without raising.
    _validate_lcu_weights([1.0, -2.0, 3.0])
