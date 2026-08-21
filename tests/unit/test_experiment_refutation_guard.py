"""T006/T007 — the refutation guard: a dedicated negative control (a
genuine overfitting artifact must be REFUTED at a shifted point) and its
positive-control counterpart (a true, non-artifact model must GENERALIZE),
kept as two separate test functions in the same file so neither can pass
by accident if the other half of the discrimination is broken
(research.md R1)."""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.experiment import run_generalization_check
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.learn import (
    LearnedModel,
    _canonical_columns,
    _reconstruct_complex,
    build_sensing_matrix,
    error_bounding_report,
)
from fourierlearn.reference import coefficients as oracle_coefficients

_TAU, _R = 0.5, 1
_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))
_SEED = 20260821


def _fixture():
    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=_TAU, r=_R, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    oracle = oracle_coefficients(ir)
    canonical = sorted(f for f in oracle if _is_canonical_representative(f))
    columns = _canonical_columns(canonical)
    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    return ir, observable, oracle, canonical, columns, parameter_coefficients


def _make_model(ir, observable, canonical, coefficients, parameter_coefficients):
    return LearnedModel(
        coefficients=coefficients,
        canonical=tuple(canonical),
        parameter_coefficients=parameter_coefficients,
        observable=observable,
        ir=ir,
        tau=_TAU,
        r=_R,
        seed=_SEED,
        shots_per_row=(1_000,) * 22,
        run_manifest={},
    )


def _build_overfit_model_and_training_alphas():
    """research.md R1's exact construction: an under-determined (M < P),
    unregularized least-squares fit that interpolates training points
    exactly, with a null-space component injected at 3x the minimum-norm
    solution's magnitude to model a genuine "spurious explanation"
    overfitting artifact -- not a hand-injected fake coefficient."""
    ir, observable, oracle, canonical, columns, parameter_coefficients = _fixture()
    P = len(columns)

    rng = np.random.default_rng(_SEED)
    M = P - 3
    training_alphas = [tuple(rng.uniform(-1.5, 1.5, size=2)) for _ in range(M)]

    def exact_y(alpha):
        import math

        total = 0j
        for freq, b in oracle.items():
            phase = math.pi * sum(l * c * a for l, c, a in zip(freq, parameter_coefficients, alpha))
            total += b * complex(math.cos(phase), math.sin(phase))
        return total.real

    y_train = np.array([exact_y(a) for a in training_alphas])
    A_train = build_sensing_matrix(training_alphas, columns, parameter_coefficients)

    x_min_norm, *_ = np.linalg.lstsq(A_train, y_train, rcond=None)
    _, _, Vt = np.linalg.svd(A_train, full_matrices=True)
    assert Vt.shape[0] - np.linalg.matrix_rank(A_train) > 0, "training set must be under-determined"
    null_vector = Vt[-1]
    amplitude = 3.0 * float(np.linalg.norm(x_min_norm))
    x_overfit = x_min_norm + amplitude * null_vector
    coefficients = _reconstruct_complex(x_overfit, columns)

    model = _make_model(ir, observable, canonical, coefficients, parameter_coefficients)
    return model, training_alphas


def test_refutation_guard_detects_overfitting_artifact() -> None:
    """The negative control (Guardrail #4): a genuine overfitting artifact
    looks suspiciously good at its own training points but is REFUTED by
    the generalization check at a genuinely shifted point."""
    model, training_alphas = _build_overfit_model_and_training_alphas()
    report = error_bounding_report(model)
    assert report.trotter_bound.structural_approximation_bound > 0.0

    suspect_input = training_alphas[0]
    result = run_generalization_check(report, model, training_alphas, suspect_input=suspect_input)

    assert result.verdict == "refuted", (
        f"refutation guard FAILED: expected 'refuted', got {result.verdict!r} "
        f"(predicted={result.predicted_value}, exact={result.exact_value}, "
        f"trotter_bound={result.trotter_bound})"
    )


def test_true_model_generalizes() -> None:
    """The positive control: a model built directly from the TRUE oracle
    coefficients (no fitting, no artifact) correctly GENERALIZES at the
    same kind of shifted point -- proving the check above doesn't just
    always say 'refuted'. This uses the oracle only as standard test-only
    ground truth to construct a known-correct model for the test fixture
    itself -- an ordinary, already-established testing pattern throughout
    this project's own test suite (e.g. every prior spec's oracle-
    comparison tests) -- and is completely distinct from
    fourierlearn._exact_dynamics's narrow PRODUCTION exemption, which
    exists only inside run_generalization_check's own implementation, not
    in this test file."""
    ir, observable, oracle, canonical, columns, parameter_coefficients = _fixture()
    model = _make_model(ir, observable, canonical, dict(oracle), parameter_coefficients)
    report = error_bounding_report(model)

    training_alphas = [(0.3, -0.4), (-0.7, 1.1), (1.4, 0.2)]
    suspect_input = training_alphas[0]
    result = run_generalization_check(report, model, training_alphas, suspect_input=suspect_input)

    assert result.verdict == "generalizes", (
        f"positive control FAILED: expected 'generalizes', got {result.verdict!r} "
        f"(predicted={result.predicted_value}, exact={result.exact_value})"
    )
    assert abs(result.predicted_value - result.exact_value) < 1e-9
