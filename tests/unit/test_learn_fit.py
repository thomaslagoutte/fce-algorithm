"""US1 acceptance tests — determinism (FR-012), conjugate-symmetry-enforced
real prediction and Hermiticity rejection (FR-006), post-split leakage
assertion (FR-005), and the under-determined-regime guarantee (FR-002).
Four independent test functions plus the determinism test — none merged."""

from __future__ import annotations

from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp

import dataclasses
import math

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.learn import TrainingRow, fit_model, predict

_TAU = 3.7
_R = 12


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def _rows(alphas: list[float], shots: int = 2_000) -> list[TrainingRow]:
    ir = _mandated_fixture_ir()
    return [TrainingRow(ir=ir, alpha=(a,), shots=shots, tau=_TAU, r=_R) for a in alphas]


def test_learn_fit_is_deterministic_given_seed() -> None:
    """FR-012, User Story 1 Acceptance Scenario 4: fitting the same training
    set twice with the same seed produces bit-identical fitted coefficient
    vectors."""
    observable = SparsePauliOp("X")
    rows = _rows([0.3, -0.7, 1.1, 2.0, -1.5])

    model_a = fit_model(rows, observable, seed=7)
    model_b = fit_model(rows, observable, seed=7)

    assert model_a.canonical == model_b.canonical
    for freq in model_a.canonical:
        assert model_a.coefficients[freq] == model_b.coefficients[freq], freq


def test_learn_rejects_non_hermitian_observable() -> None:
    """FR-006: a non-Hermitian observable is rejected before any
    measurement is taken."""
    rows = _rows([0.3, -0.7])
    non_hermitian = SparsePauliOp("Z", coeffs=[1j])
    try:
        fit_model(rows, non_hermitian, seed=1)
    except ValueError:
        pass
    else:
        raise AssertionError("fit_model must reject a non-Hermitian observable")


def test_learn_predict_is_real_for_hermitian_observable() -> None:
    """FR-006: predictions for a fitted model of a Hermitian observable are
    real-valued (predict() returns a Python float by construction --
    see test_learn_predict_is_structurally_real in this same module's
    companion test file for the structural, not merely numerical, check)."""
    observable = SparsePauliOp("X")
    rows = _rows([0.3, -0.7, 1.1, 2.0, -1.5])
    model = fit_model(rows, observable, seed=3)

    value = predict(model, (0.42,))
    assert isinstance(value, float)


def test_learn_predict_is_structurally_real() -> None:
    """T017 critical instruction: predict() must use the real-form basis
    (2*cos, -2*sin) directly on each coefficient's .real/.imag parts, and
    must NOT compute a complex intermediate and then assert its imaginary
    part is small. Behavioral proof: inject an artificially HUGE fake
    imaginary component into a fitted model's coefficients (far larger than
    any numerical residual) and confirm predict() (a) does not raise --
    there is no 'assert imaginary part small' gate for a huge value to trip
    -- and (b) returns exactly the real-form value computed independently
    here from the same .real/.imag parts, proving the imaginary path has no
    other effect on the result at all (structurally absent, not merely
    numerically negligible)."""
    observable = SparsePauliOp("X")
    rows = _rows([0.3, -0.7, 1.1, 2.0, -1.5])
    model = fit_model(rows, observable, seed=3)

    huge_fake_imag = 1.0e6
    poisoned_coefficients = dict(model.coefficients)
    target_freq = next(f for f in model.canonical if not all(c == 0 for c in f))
    original = poisoned_coefficients[target_freq]
    poisoned_coefficients[target_freq] = complex(original.real, huge_fake_imag)
    poisoned_model = dataclasses.replace(model, coefficients=poisoned_coefficients)

    alpha = (0.42,)
    # Must not raise, despite the deliberately huge fake imaginary part.
    value = predict(poisoned_model, alpha)
    assert isinstance(value, float)

    expected = 0.0
    for freq in poisoned_model.canonical:
        b = poisoned_coefficients[freq]
        if all(c == 0 for c in freq):
            expected += b.real
            continue
        phase = math.pi * sum(
            l * c * a for l, c, a in zip(freq, poisoned_model.parameter_coefficients, alpha)
        )
        expected += 2.0 * b.real * math.cos(phase) - 2.0 * b.imag * math.sin(phase)

    assert value == expected, (value, expected)


def test_learn_asserts_zero_train_eval_overlap() -> None:
    """FR-005: an evaluation input that also appears in the training set
    is DETECTED and rejected -- constructed here to make the check
    genuinely fire (reachability, not merely defense-in-depth), mirroring
    Spec 4's own reachability discipline."""
    observable = SparsePauliOp("X")
    train_rows = _rows([0.3, -0.7, 1.1])
    leaking_eval_rows = _rows([0.3])  # deliberately identical to a training alpha

    try:
        fit_model(train_rows, observable, seed=1, eval_rows=leaking_eval_rows)
    except ValueError:
        pass
    else:
        raise AssertionError("fit_model must detect and reject training/evaluation overlap")

    # Sanity: a genuinely disjoint eval set does NOT raise.
    non_leaking_eval_rows = _rows([9.9])
    fit_model(train_rows, observable, seed=1, eval_rows=non_leaking_eval_rows)


def test_learn_under_determined_regime_does_not_raise() -> None:
    """FR-002: fitting with strictly fewer training rows than representable
    frequencies never raises a 'not enough samples' guard -- the
    under-determined regime is the intended operating mode."""
    observable = SparsePauliOp("X")
    rows = _rows([0.3, -0.7, 1.1])  # 3 rows, far fewer than the fixture's 13 frequencies
    model = fit_model(rows, observable, seed=1)
    assert len(model.canonical) > 0
