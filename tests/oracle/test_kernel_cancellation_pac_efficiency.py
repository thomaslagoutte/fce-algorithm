"""T022/T023 — spec.md Finding 1, made permanent (FR-009/FR-010):

1. `Rz(alpha_s)*Y*Rz(alpha_s) = Y` exactly, independent of `alpha_s`, for
   two tied `PauliTerm('Z', ...)` uploads of the SAME parameter (each its
   own `tie_group`, `upload_count=2`) sandwiching a `FixedGate(YGate())`,
   built in this project's own `e^{i*pi*c*alpha*P}` convention.
2. A 2-qubit IR with one surviving parameter (a single, `r_j=1` `X`
   upload) and one cancelling parameter (the sandwich above) has an
   extracted support of exactly 2 nonzero elements, `{(-2,0), (2,0)}`,
   against an ambient box of `45` (`5*9`).
3. Extending to TWO independent cancelling parameters grows the ambient
   box multiplicatively (`405=45*9`) while the extracted support size
   stays fixed at exactly 2 elements, `{(-2,0,0), (2,0,0)}`.

Deliverable (c)'s own scope precision (FR-013, spec.md Clarifications):
this is a PURPOSE-BUILT demonstration fixture. No claim is made, and none
is implied, that this project's existing Z2/TFIM models (Specs 6-8)
exhibit this cancellation property naturally.
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import YGate
from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import coefficients, predict_grid_cost


def _build_cancelling_parameter_fixture(surviving_count: int, cancelling_count: int) -> PauliEncodedCircuitIR:
    """A reusable fixture-builder helper (tasks.md T025's design decision:
    placed directly in this test module, not a new production module --
    FR-009's "a way to construct" this concept class is already satisfied
    compositionally by Spec 1's existing `PauliTerm`/`FixedGate`/IR-builder
    primitives, so no new production abstraction is warranted for this
    alone). One qubit is reused for every surviving upload (an `X` term)
    and every cancelling sandwich (a `Z`-`Y`-`Z` sandwich on a SEPARATE
    qubit, so a cancelling parameter never shares a qubit with, or
    otherwise interferes with, the surviving one)."""
    if surviving_count != 1:
        raise ValueError("this fixture builder only supports exactly one surviving parameter")
    gates: list = []
    gates.append(PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0))
    num_qubits = 1 + cancelling_count
    tie_counter = 0
    for i in range(cancelling_count):
        qubit = 1 + i
        param_index = 1 + i
        gates.append(
            PauliTerm(pauli="Z", qubits=(qubit,), parameter_index=param_index, coefficient=1.0, tie_group=tie_counter)
        )
        tie_counter += 1
        gates.append(_YFixedGate(qubit))
        gates.append(
            PauliTerm(pauli="Z", qubits=(qubit,), parameter_index=param_index, coefficient=1.0, tie_group=tie_counter)
        )
        tie_counter += 1
    # Qiskit's Pauli-label convention is little-endian (rightmost letter =
    # qubit 0) -- Z must be the RIGHTMOST character to land on the
    # surviving qubit (qubit 0), never the cancelling qubits (verified
    # in-session: "Z" + "I"*cancelling_count instead measures a cancelling
    # qubit's own post-sandwich Y-conjugated Z, giving a trivial, alpha-
    # independent constant, not the surviving parameter's own oscillation).
    observable_label = "I" * cancelling_count + "Z"
    return PauliEncodedCircuitIR(
        num_qubits=num_qubits, gates=tuple(gates), observable=SparsePauliOp(observable_label)
    )


def _YFixedGate(qubit: int):
    from fourierlearn.ir import FixedGate

    return FixedGate(YGate(), (qubit,))


def test_rz_y_rz_sandwich_cancels_to_y_exactly_independent_of_alpha() -> None:
    for alpha_s in (0.0, 0.3, 0.61, 1.0, -0.4):
        term_a = PauliTerm(pauli="Z", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0)
        term_b = PauliTerm(pauli="Z", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=1)

        p = Parameter("alpha")
        qc = QuantumCircuit(1)
        qc.append(term_a.to_gate(p), term_a.qubits)
        qc.append(YGate(), (0,))
        qc.append(term_b.to_gate(p), term_b.qubits)
        bound = qc.assign_parameters({p: alpha_s})

        got = Operator(bound).data
        expected = Operator(YGate()).data
        diff = float(abs(got - expected).max())
        assert diff < 2.3e-16, (alpha_s, diff)


def test_one_cancelling_parameter_ambient_45_support_stays_at_two_elements() -> None:
    ir = _build_cancelling_parameter_fixture(surviving_count=1, cancelling_count=1)

    assert predict_grid_cost(ir) == 45  # 5 (surviving axis) * 9 (cancelling axis)

    result = coefficients(ir)
    nonzero = {freq: value for freq, value in result.items() if abs(value) > 1e-6}

    assert set(nonzero.keys()) == {(-2, 0), (2, 0)}


def test_two_independent_cancelling_parameters_ambient_405_support_stays_at_two_elements() -> None:
    ir = _build_cancelling_parameter_fixture(surviving_count=1, cancelling_count=2)

    assert predict_grid_cost(ir) == 405  # 45 * 9, exponential in the number of cancelling parameters

    result = coefficients(ir, budget=1_000, confirm=True)
    nonzero = {freq: value for freq, value in result.items() if abs(value) > 1e-6}

    assert set(nonzero.keys()) == {(-2, 0, 0), (2, 0, 0)}
