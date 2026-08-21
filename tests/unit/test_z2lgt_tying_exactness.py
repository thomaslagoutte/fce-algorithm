"""T010 — FR-006/FR-007 (Critical Mandate/Deliverable b): the tied A_e/B_e
two-gate sequence is EXACTLY equal to a direct matrix exponential of the
combined generator (Proposition 5.1(iii): [A_e,B_e]=0, so the split is
exact, no Trotter error) -- a dedicated Operator-equivalence test,
independent of any coefficient-level test (this project's own standing
rule for gate-construction sign/decomposition claims). Reproduces
research.md R3(a) exactly."""

from __future__ import annotations

import math

import numpy as np
from qiskit.quantum_info import Operator
from scipy.linalg import expm

from tests.unit._hopping_fixtures import two_gate_circuit

_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)


def _kron3(q0: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    # Little-endian: qubit 0 is the rightmost (innermost) kron factor.
    return np.kron(q2, np.kron(q1, q0))


def test_tied_sequence_equals_combined_generator_evolution_exactly() -> None:
    qc, symbols, ir = two_gate_circuit("hop", "hop")
    assert ir.num_parameters == 1, "tying must collapse to exactly one parameter"

    alpha = 0.37
    bound = qc.assign_parameters({symbols[0]: alpha})
    op_tied = Operator(bound).data

    a_e = _kron3(_X, _X, _Z)  # q0=X(v0), q1=X(v1), q2=Z(e01)
    b_e = _kron3(_Y, _Y, _Z)
    target = expm(1j * math.pi * alpha * (a_e + b_e))

    diff = np.max(np.abs(op_tied - target))
    assert diff < 1e-10, f"tied split must be EXACT (Prop 5.1(iii)), got diff={diff}"


def test_a_e_and_b_e_commute_exactly() -> None:
    a_e = _kron3(_X, _X, _Z)
    b_e = _kron3(_Y, _Y, _Z)
    commutator = a_e @ b_e - b_e @ a_e
    assert np.max(np.abs(commutator)) == 0.0, "Proposition 5.1(i): [A_e, B_e] must be exactly 0"
