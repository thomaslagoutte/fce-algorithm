"""T004 — research.md R1 Step 3: the same-sign asymmetric fixture
(beta_1=1, beta_2=4, both positive) -- a SEPARATE test from the
negative-weight test (distinct claim: the square-root formula itself is
correct, independent of the sign-absorption mechanism)."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import _insert_observable_lcu

_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)


def test_asymmetric_positive_weights_recover_the_linear_combination() -> None:
    beta1, beta2 = 1.0, 4.0
    circuit_reg = QuantumRegister(1, "circuit")
    qc = QuantumCircuit(circuit_reg)
    observable = SparsePauliOp(["Z", "X"], coeffs=[beta1, beta2])
    selector_reg = _insert_observable_lcu(qc, observable, circuit_reg)

    psi_angle = 0.83
    full = QuantumCircuit(circuit_reg, selector_reg)
    full.ry(psi_angle, circuit_reg[0])
    full.compose(qc, inplace=True)

    sv = Statevector(full)
    post = np.array([sv.data[i] for i in range(2 ** (1 + len(selector_reg))) if (i >> 1) == 0])

    psi_circuit = QuantumCircuit(1)
    psi_circuit.ry(psi_angle, 0)
    psi = Statevector(psi_circuit).data
    S = beta1 + beta2
    target = (beta1 * _Z + beta2 * _X) @ psi / S

    diff = np.max(np.abs(post - target))
    assert diff < 1e-10, f"expected the linear (not quadratic) combination, got diff={diff}"
