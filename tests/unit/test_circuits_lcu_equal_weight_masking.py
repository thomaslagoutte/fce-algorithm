"""T005 — an explicit negative control (Constitution §8.4): documents
that an equal-weight fixture (beta_1=beta_2) CANNOT distinguish the
correct (sqrt) LCU formula from the incorrect (linear, no-sqrt) one --
both give the identical term-to-term ratio AND identical overall scale on
this fixture. Recorded so this fixture is never mistaken for a sufficient
verification on its own; the real correctness proof lives in
test_circuits_lcu_negative_weight.py and
test_circuits_lcu_asymmetric_positive_weight.py, which use genuinely
asymmetric weights specifically because they can distinguish the two
formulas."""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import _insert_observable_lcu


def _wrong_linear_prep_post_selected(beta1: float, beta2: float, psi_angle: float) -> np.ndarray:
    """The FR-003-violating hypothesis AS LITERALLY TRANSCRIBED from eq.
    5.51: c_h = beta_h / ||beta||_2 (the L2 norm -- the only norm for
    which this ratio is already a normalized, directly Ry-buildable
    amplitude pair)."""
    l2 = math.sqrt(beta1**2 + beta2**2)
    c1, c2 = beta1 / l2, beta2 / l2
    theta = 2 * math.atan2(c2, c1)

    circuit_reg = QuantumRegister(1, "circuit")
    selector_reg = QuantumRegister(1, "sel")
    qc = QuantumCircuit(circuit_reg, selector_reg)
    qc.ry(psi_angle, circuit_reg[0])
    qc.ry(theta, selector_reg[0])
    from qiskit.circuit.library import XGate, ZGate

    qc.append(ZGate().control(1, ctrl_state=0), [selector_reg[0], circuit_reg[0]])
    qc.append(XGate().control(1, ctrl_state=1), [selector_reg[0], circuit_reg[0]])
    qc.ry(-theta, selector_reg[0])

    sv = Statevector(qc)
    return np.array([sv.data[i] for i in range(4) if (i >> 1) == 0])


def _correct_post_selected(beta1: float, beta2: float, psi_angle: float) -> np.ndarray:
    circuit_reg = QuantumRegister(1, "circuit")
    qc = QuantumCircuit(circuit_reg)
    observable = SparsePauliOp(["Z", "X"], coeffs=[beta1, beta2])
    selector_reg = _insert_observable_lcu(qc, observable, circuit_reg)

    full = QuantumCircuit(circuit_reg, selector_reg)
    full.ry(psi_angle, circuit_reg[0])
    full.compose(qc, inplace=True)
    sv = Statevector(full)
    return np.array([sv.data[i] for i in range(2 ** (1 + len(selector_reg))) if (i >> 1) == 0])


def test_equal_weights_cannot_distinguish_correct_from_wrong_formula() -> None:
    psi_angle = 0.83
    correct = _correct_post_selected(2.0, 2.0, psi_angle)
    wrong = _wrong_linear_prep_post_selected(2.0, 2.0, psi_angle)

    ratio_correct = correct[1] / correct[0]
    ratio_wrong = wrong[1] / wrong[0]
    assert abs(ratio_correct - ratio_wrong) < 1e-9, (
        "at equal weights, the correct and incorrect formulas are expected "
        "to give the identical term-to-term ratio -- this is the documented "
        "masking effect, not a bug in either construction"
    )
    assert abs(np.linalg.norm(correct) - np.linalg.norm(wrong)) < 1e-9, (
        "and the identical overall scale -- confirming an equal-weight "
        "fixture alone could never have caught the square-root error"
    )
