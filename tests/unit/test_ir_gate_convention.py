"""FR-021, SC-009: PauliTerm.to_gate()'s sign convention, isolated from any oracle
coefficient-level check.

A sign error here silently conjugates every Fourier coefficient the oracle ever
returns (l <-> -l), and is invisible on any real-coefficient test (including
FR-016's single-upload case) — this is the only test that catches it directly.
"""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator

from fourierlearn.ir import PauliTerm

_Z = np.array([[1, 0], [0, -1]])


def test_to_gate_z_upload_is_operator_equivalent_to_hand_built_rotation() -> None:
    coefficient = 1.0
    alpha_value = 0.4123

    alpha = Parameter("alpha")
    term = PauliTerm("Z", (0,), parameter_index=0, coefficient=coefficient, tie_group=0)

    qc = QuantumCircuit(1)
    qc.append(term.to_gate(alpha), [0])
    bound = qc.assign_parameters({alpha: alpha_value})
    actual = Operator(bound).data

    # The encoding convention this layer pins is e^{i*pi*c*alpha*P} (spec FR-021).
    expected_angle = math.pi * coefficient * alpha_value
    expected = np.array(
        [
            [np.exp(1j * expected_angle), 0],
            [0, np.exp(-1j * expected_angle)],
        ]
    )
    assert np.allclose(actual, expected)


def test_flipped_sign_would_fail_this_test() -> None:
    """Sanity check on the test itself: the *wrong* mapping (t = +c*alpha instead of
    -pi*c*alpha) must NOT match — otherwise this test could not catch the bug it
    exists for."""
    coefficient = 1.0
    alpha_value = 0.4123

    alpha = Parameter("alpha")
    from qiskit.circuit.library import PauliEvolutionGate
    from qiskit.quantum_info import SparsePauliOp

    wrong_gate = PauliEvolutionGate(SparsePauliOp("Z"), time=coefficient * alpha)
    qc = QuantumCircuit(1)
    qc.append(wrong_gate, [0])
    bound = qc.assign_parameters({alpha: alpha_value})
    wrong_actual = Operator(bound).data

    expected_angle = math.pi * coefficient * alpha_value
    expected = np.array(
        [
            [np.exp(1j * expected_angle), 0],
            [0, np.exp(-1j * expected_angle)],
        ]
    )
    assert not np.allclose(wrong_actual, expected)
