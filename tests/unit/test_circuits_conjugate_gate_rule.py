"""T012 — Guardrail 1 (the Odd-Y Conjugate Trap): for a Pauli-rotation
gate, `Operator(gate).conjugate()` (Qiskit's own ground truth) is
compared against (a) naively negating the angle for an ODD-Y-count term
-- MUST fail -- and (b) the corrected rule (no negation for odd-Y,
negate for even-Y) -- MUST match to machine precision for both parities."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator

from fourierlearn.circuits import _pauli_term_conjugate
from fourierlearn.ir import PauliTerm

_ALPHA = 0.61


def _gate_operator(pauli: str, qubits: tuple, coefficient: float) -> np.ndarray:
    p = Parameter("a")
    term = PauliTerm(pauli=pauli, qubits=qubits, parameter_index=0, coefficient=coefficient, tie_group=0)
    width = max(qubits) + 1
    qc = QuantumCircuit(width)
    qc.append(term.to_gate(p), term.qubits)
    bound = qc.assign_parameters({p: _ALPHA})
    return Operator(bound).data


def test_odd_y_true_conjugate_matches_unchanged_gate_not_negated_angle() -> None:
    for pauli, qubits in [("Y", (0,)), ("XY", (0, 1))]:
        term = PauliTerm(pauli=pauli, qubits=qubits, parameter_index=0, coefficient=0.4, tie_group=0)
        true_conjugate = _gate_operator(pauli, qubits, 0.4).conjugate()

        naive_negated = _gate_operator(pauli, qubits, -0.4)
        diff_naive = np.max(np.abs(true_conjugate - naive_negated))
        assert diff_naive > 0.5, f"naive angle-negation must FAIL for odd-Y term {pauli}, got diff={diff_naive}"

        corrected = _pauli_term_conjugate(term)
        assert corrected.coefficient == term.coefficient, "odd-Y term's conjugate must NOT negate the angle"
        corrected_operator = _gate_operator(pauli, qubits, corrected.coefficient)
        diff_corrected = np.max(np.abs(true_conjugate - corrected_operator))
        assert diff_corrected < 1e-10, f"corrected rule must match to machine precision for {pauli}"


def test_even_y_true_conjugate_matches_negated_angle_not_unchanged_gate() -> None:
    pauli, qubits = "YY", (0, 1)
    term = PauliTerm(pauli=pauli, qubits=qubits, parameter_index=0, coefficient=0.7, tie_group=0)
    true_conjugate = _gate_operator(pauli, qubits, 0.7).conjugate()

    no_negation = _gate_operator(pauli, qubits, 0.7)
    diff_no_negation = np.max(np.abs(true_conjugate - no_negation))
    assert diff_no_negation > 0.5, f"leaving the angle unchanged must FAIL for even-Y term, got diff={diff_no_negation}"

    corrected = _pauli_term_conjugate(term)
    assert corrected.coefficient == -term.coefficient, "even-Y term's conjugate MUST negate the angle"
    corrected_operator = _gate_operator(pauli, qubits, corrected.coefficient)
    diff_corrected = np.max(np.abs(true_conjugate - corrected_operator))
    assert diff_corrected < 1e-10
