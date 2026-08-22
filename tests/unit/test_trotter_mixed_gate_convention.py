"""Mixed Fixed/Encoded Trotter Frontend — FR-003/FR-011/SC-002.

Permanent regression tests reproducing research.md R1 (isolated fixed-term
angle convention, two independent fixtures) and R2 (genuinely mixed,
multi-qubit, multi-parameter case) as executable `Operator.equiv` checks
against independently hand-built target circuits — never against this
project's own gate-construction code path.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, SparsePauliOp
from scipy.linalg import expm

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, FixedCouplingGroup, mixed_trotter_frontend
from fourierlearn.ir import PauliTerm


def _bind_and_operator(ir, alpha_values: list[float]) -> Operator:
    symbols = ir.parameter_symbols()
    qc = QuantumCircuit(ir.num_qubits)
    for gate in ir.gates:
        if isinstance(gate, PauliTerm):
            qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
        else:
            qc.append(gate.gate, gate.qubits)
    binding = {symbols[i]: v for i, v in enumerate(alpha_values)}
    return Operator(qc.assign_parameters(binding))


_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)


@pytest.mark.parametrize(
    "weight, tau, r, value, pauli, matrix",
    [
        (0.8, 1.09, 3, 1.5, "Z", _Z),
        (1.37, 0.62, 5, -0.9, "X", _X),
    ],
)
def test_isolated_fixed_term_matches_independent_expm_target(
    weight: float, tau: float, r: int, value: float, pauli: str, matrix: np.ndarray
) -> None:
    """research.md R1: a single-fixed-term-only mixed construction's
    Operator matches e^{-i*theta*P} (theta = weight*tau*value/r) built
    directly via scipy.linalg.expm on the raw Pauli matrix — independent of
    every Qiskit gate-construction path this project's own code uses."""
    group_fixed = FixedCouplingGroup((CouplingGroupTerm(pauli, (0,), weight),), value=value)
    observable = SparsePauliOp(pauli)

    ir = mixed_trotter_frontend(
        num_qubits=1, group_specs=[group_fixed], tau=tau, r=r, observable=observable
    )
    actual = _bind_and_operator(ir, []).data

    theta = weight * tau * value / r
    target = np.linalg.matrix_power(expm(-1j * theta * matrix), r)

    assert np.abs(actual - target).max() < 1e-9


def test_mixed_multi_parameter_case_matches_independent_expm_target() -> None:
    """research.md R2: two DISTINCT encoded parameters (h1, h2) interleaved
    with one fixed ZZ group, in caller order [h1, fixed, h2], on 3 qubits —
    matches an independently hand-built scipy.linalg.expm target, confirming
    the interleaving logic and FR-011's angle formula generalize beyond a
    single encoded parameter (spec.md Assumptions multi-parameter mandate)."""
    group_h1 = CouplingGroup("h1", (CouplingGroupTerm("X", (0,), 1.0),))
    group_h2 = CouplingGroup("h2", (CouplingGroupTerm("Z", (1,), 1.0),))
    group_fixed = FixedCouplingGroup((CouplingGroupTerm("ZZ", (0, 2), 1.0),), value=0.8)
    group_specs = [group_h1, group_fixed, group_h2]

    tau, r = 0.95, 3
    observable = SparsePauliOp("ZII")
    alpha_h1, alpha_h2 = 0.6, -0.4

    ir = mixed_trotter_frontend(
        num_qubits=3, group_specs=group_specs, tau=tau, r=r, observable=observable
    )
    actual = _bind_and_operator(ir, [alpha_h1, alpha_h2]).data

    i2 = np.eye(2, dtype=complex)
    x0 = np.kron(i2, np.kron(i2, _X))  # X on q0 (rightmost tensor factor)
    z1 = np.kron(i2, np.kron(_Z, i2))  # Z on q1 (middle tensor factor)
    zz02 = np.kron(_Z, np.kron(i2, _Z))  # ZZ on q0,q2 (q2 leftmost, q0 rightmost)

    theta_h1 = 1.0 * tau * alpha_h1 / r
    theta_h2 = 1.0 * tau * alpha_h2 / r
    theta_fixed = 1.0 * tau * 0.8 / r

    u_h1 = expm(-1j * theta_h1 * x0)
    u_fixed = expm(-1j * theta_fixed * zz02)
    u_h2 = expm(-1j * theta_h2 * z1)

    # caller order [h1, fixed, h2] applied to the state in that order ->
    # matrix product (last-applied gate is the leftmost factor) = h2 @ fixed @ h1
    u_step = u_h2 @ u_fixed @ u_h1
    target = np.linalg.matrix_power(u_step, r)

    assert np.abs(actual - target).max() < 1e-9
