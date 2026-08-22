"""T003 — FR-003 (Critical Mandate/Guardrail 2): reproduces research.md
R1's exact fixture (beta_1=1, P_1=Z; beta_2=-4, P_2=X) -- the folded LCU
construction's post-selected amplitude must match
(1/S)(beta_1*Z + beta_2*X)|psi> to machine precision, INCLUDING the
negative weight, absorbed via the diagonal sign gate -- never an invalid
sqrt of a negative number. Includes the isolating sanity control: removing
only the sign gate must reproduce the (wrong) all-positive-weight
combination instead."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import DiagonalGate, StatePreparation
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import _insert_observable_lcu, _lcu_magnitude_amplitudes

_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)


def _post_selected_amplitudes(full_circuit: QuantumCircuit, n_selector: int) -> np.ndarray:
    sv = Statevector(full_circuit)
    return np.array([sv.data[i] for i in range(2 ** (1 + n_selector)) if (i >> 1) == 0])


def test_negative_weight_is_absorbed_via_sign_gate_not_sqrt() -> None:
    beta1, beta2 = 1.0, -4.0
    circuit_reg = QuantumRegister(1, "circuit")
    qc = QuantumCircuit(circuit_reg)
    observable = SparsePauliOp(["Z", "X"], coeffs=[beta1, beta2])
    selector_reg = _insert_observable_lcu(qc, observable, circuit_reg)

    psi_angle = 0.83
    full = QuantumCircuit(circuit_reg, selector_reg)
    full.ry(psi_angle, circuit_reg[0])
    full.compose(qc, inplace=True)

    post = _post_selected_amplitudes(full, len(selector_reg))

    psi_circuit = QuantumCircuit(1)
    psi_circuit.ry(psi_angle, 0)
    psi = Statevector(psi_circuit).data
    S = abs(beta1) + abs(beta2)
    target = (beta1 * _Z + beta2 * _X) @ psi / S

    diff = np.max(np.abs(post - target))
    assert diff < 1e-10, f"expected the signed target to machine precision, got diff={diff}"


def test_removing_only_the_sign_gate_gives_the_wrong_all_positive_result() -> None:
    """Isolating sanity control (research.md R1): the sign gate specifically
    is responsible for the correct negative sign -- dropping only it must
    give the all-positive-weight combination instead."""
    beta1, beta2 = 1.0, -4.0
    S = abs(beta1) + abs(beta2)
    amplitudes = _lcu_magnitude_amplitudes([beta1, beta2])

    circuit_reg = QuantumRegister(1, "circuit")
    selector_reg = QuantumRegister(1, "lcu_selector")
    qc_unsigned = QuantumCircuit(circuit_reg, selector_reg)
    qc_unsigned.append(StatePreparation(amplitudes), list(selector_reg))
    # deliberately SKIP the diagonal sign gate here
    from fourierlearn.circuits import _append_multiplexed_fold

    _append_multiplexed_fold(qc_unsigned, ["Z", "X"], selector_reg, circuit_reg)
    qc_unsigned.append(StatePreparation(amplitudes, inverse=True), list(selector_reg))

    psi_angle = 0.83
    full = QuantumCircuit(circuit_reg, selector_reg)
    full.ry(psi_angle, circuit_reg[0])
    full.compose(qc_unsigned, inplace=True)
    post = _post_selected_amplitudes(full, len(selector_reg))

    psi_circuit = QuantumCircuit(1)
    psi_circuit.ry(psi_angle, 0)
    psi = Statevector(psi_circuit).data
    wrong_target = (abs(beta1) * _Z + abs(beta2) * _X) @ psi / S
    correct_target = (beta1 * _Z + beta2 * _X) @ psi / S

    assert np.max(np.abs(post - wrong_target)) < 1e-10
    assert np.max(np.abs(post - correct_target)) > 0.1, "must genuinely differ from the correct, signed result"
