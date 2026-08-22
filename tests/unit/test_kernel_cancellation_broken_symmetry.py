"""T024 — Edge Case (spec.md): a cancelling-parameter fragment whose two
uploads break the exact `Rz(alpha_s)*Y*Rz(alpha_s)` sandwich symmetry MUST
NOT be assumed to cancel. Two distinct ways the symmetry can break:

1. Mismatched COEFFICIENTS across the tied sandwich -- already rejected
   outright by `PauliEncodedCircuitIR`'s own construction-time validation
   (Spec 1, `_validate_tying`) — confirmed here, not merely assumed.
2. Mismatched PAULI LETTERS across the two uploads (same parameter_index,
   same coefficient) -- NOT rejected by IR construction (letter identity
   is not a structural invariant `_validate_tying` checks), so this
   feature must demonstrate NUMERICALLY that such a fragment does NOT
   cancel to `Y` (or to anything alpha-independent), rather than silently
   assuming it does.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import YGate
from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm


def test_mismatched_coefficients_across_the_sandwich_are_rejected_at_construction() -> None:
    term_a = PauliTerm(pauli="Z", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0)
    term_b = PauliTerm(pauli="Z", qubits=(0,), parameter_index=0, coefficient=2.0, tie_group=1)

    with pytest.raises(ValueError, match="non-uniform coefficients"):
        PauliEncodedCircuitIR(
            num_qubits=1, gates=(term_a, term_b), observable=SparsePauliOp("Z")
        )


def test_mismatched_pauli_letters_across_the_sandwich_do_not_cancel_to_y() -> None:
    """Same `parameter_index`, same coefficient (so IR construction does
    NOT reject this) -- but a `Z`-then-`X` sandwich, not the exact tied
    `Z`-then-`Z` (`Rz`-`Y`-`Rz`) symmetry Finding 1 verified. The resulting
    gate must NOT be assumed to equal `Y`, and indeed does not, for a
    generic `alpha_s`."""
    term_a = PauliTerm(pauli="Z", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0)
    term_b = PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=1)
    # Constructs without error -- IR validation has no reason to reject this.
    PauliEncodedCircuitIR(num_qubits=1, gates=(term_a, term_b), observable=SparsePauliOp("Z"))

    alpha_s = 0.61
    p = Parameter("alpha")
    qc = QuantumCircuit(1)
    qc.append(term_a.to_gate(p), term_a.qubits)
    qc.append(YGate(), (0,))
    qc.append(term_b.to_gate(p), term_b.qubits)
    bound = qc.assign_parameters({p: alpha_s})

    got = Operator(bound).data
    expected_if_it_wrongly_cancelled = Operator(YGate()).data
    diff = float(abs(got - expected_if_it_wrongly_cancelled).max())

    assert diff > 0.1, "a Z-then-X sandwich must not be assumed to cancel to Y like the exact Z-then-Z sandwich"
