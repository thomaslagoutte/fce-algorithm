"""T011 — FR-008 (Critical Mandate/Deliverable b): untying A_e and B_e
(independent parameters) genuinely breaks [U, Q]=0 at distinct angles,
with an equal-angle sanity control isolating that independence,
specifically, is the failure mode -- not some unrelated artifact.
Reproduces research.md R3(b) exactly."""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import Operator

from tests.unit._hopping_fixtures import two_gate_circuit

_I2 = np.eye(2, dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)


def _kron3(q0: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    return np.kron(q2, np.kron(q1, q0))


_Q_MATRIX = _kron3(_Z, _I2, _I2) + _kron3(_I2, _Z, _I2)  # Q = Z_v0 + Z_v1


def test_untied_distinct_angles_break_commutation_with_q() -> None:
    qc, symbols, ir = two_gate_circuit("only_A", "only_B")
    assert ir.num_parameters == 2, "untied must be two genuinely independent parameters"

    bound = qc.assign_parameters({symbols[0]: 0.3, symbols[1]: 0.9})
    op = Operator(bound).data
    commutator = op @ _Q_MATRIX - _Q_MATRIX @ op
    max_comm = np.max(np.abs(commutator))
    assert max_comm > 0.1, "untying at distinct angles must genuinely break [U, Q]=0"


def test_untied_equal_angles_recover_commutation_with_q_exactly() -> None:
    """Sanity isolation: the SAME untied construction, at EQUAL angles,
    must recover [U, Q]=0 exactly -- proving the failure above is caused
    specifically by the two angles being independent, not by some other
    artifact of using two separate parameters."""
    qc, symbols, _ = two_gate_circuit("only_A", "only_B")
    bound = qc.assign_parameters({symbols[0]: 0.37, symbols[1]: 0.37})
    op = Operator(bound).data
    commutator = op @ _Q_MATRIX - _Q_MATRIX @ op
    max_comm = np.max(np.abs(commutator))
    assert max_comm < 1e-10, "equal angles must recover [U, Q]=0 exactly"
