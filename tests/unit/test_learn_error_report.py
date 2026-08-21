"""US2 dedicated tests — PAC-bound truth-in-labeling (this round's central
guardrail), zero blended PAC/Trotter figures (FR-008), and the
generalization-check flag's policy-only scope (FR-009)."""

from __future__ import annotations

import dataclasses
import inspect

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.learn import TrainingRow, error_bounding_report, fit_model, predict

_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))


def _two_group_fixture(tau: float = 0.5, r: int = 1):
    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=tau, r=r, observable=SparsePauliOp("Z"))
    return ir


def _fitted_model(tau: float = 0.5, r: int = 1, seed: int = 5):
    ir = _two_group_fixture(tau=tau, r=r)
    observable = SparsePauliOp("Z")
    rows = [
        TrainingRow(ir=ir, alpha=(0.3, -0.4), shots=2_000, tau=tau, r=r),
        TrainingRow(ir=ir, alpha=(-0.7, 1.1), shots=2_000, tau=tau, r=r),
        TrainingRow(ir=ir, alpha=(1.4, 0.2), shots=2_000, tau=tau, r=r),
    ]
    return fit_model(rows, observable, seed=seed)


def test_error_report_labels_pac_bound_as_measurement_noise_not_weight_error() -> None:
    """This round's PAC-bound truth-in-labeling guardrail: the field name,
    the weight_space_translation_status sentinel, and the report's OWN
    instantiated __str__ all correctly label the PAC figure -- checked
    against the real object, not a hand-written string."""
    model = _fitted_model()
    report = error_bounding_report(model)

    assert report.pac_bound.per_measurement_statistical_noise_bound > 0.0
    assert (
        report.pac_bound.weight_space_translation_status
        == "out_of_scope_requires_sensing_matrix_conditioning"
    )

    field_names = {f.name for f in dataclasses.fields(report.pac_bound)}
    assert field_names == {"per_measurement_statistical_noise_bound", "weight_space_translation_status"}
    assert "model_error" not in field_names
    assert "weight_error" not in field_names

    rendered = str(report)  # the ACTUAL instantiated report object's own __str__
    assert "per-measurement statistical noise bound" in rendered

    overclaiming_phrases = ("model weights", "fitted coefficients", "the learned model")
    # The PAC-bound section of the rendered text is everything up to the
    # Trotter-bound line -- confirm none of the overclaiming phrases appear
    # anywhere in that section (in connection with the PAC figure).
    pac_section = rendered.split("Trotter bound")[0].lower()
    for phrase in overclaiming_phrases:
        assert phrase not in pac_section, f"overclaiming phrase {phrase!r} found near the PAC bound"


def test_error_report_never_combines_pac_and_trotter() -> None:
    """FR-008: across several different fits, no single combined/blended
    figure exists anywhere in the report's fields or its textual summary."""
    for tau, r, seed in [(0.5, 1, 1), (2.0, 1, 2), (0.1, 1, 3)]:
        model = _fitted_model(tau=tau, r=r, seed=seed)
        report = error_bounding_report(model)

        top_level_fields = {f.name for f in dataclasses.fields(report)}
        forbidden_names = {"combined_bound", "blended_error", "total_error", "error_ratio", "overall_bound"}
        assert not (top_level_fields & forbidden_names)

        rendered = str(report)
        for forbidden_word in ("combined", "blended", "overall error", "total error"):
            assert forbidden_word not in rendered.lower()

        # The two bounds must be independently retrievable and distinct
        # fields, never merged into one number.
        assert isinstance(report.pac_bound.per_measurement_statistical_noise_bound, float)
        assert isinstance(report.trotter_bound.structural_approximation_bound, float)


def test_error_report_flags_generalization_check_without_resolving_it() -> None:
    """FR-009: a model whose prediction matches a caller-supplied "exact"
    value more closely than its own Trotter bound sets
    generalization_check_required=True and a named suspect_input -- and
    error_bounding_report's own signature has no parameter through which a
    shifted-parameter-dynamics mechanism could be invoked (structural check
    on the live function, not a hand-written claim)."""
    model = _fitted_model()
    report_no_eval = error_bounding_report(model)
    assert report_no_eval.trotter_bound.structural_approximation_bound > 0.0, (
        "fixture must have a genuinely nonzero Trotter bound for this test to be meaningful"
    )

    alpha = (0.15, 0.25)
    predicted = predict(model, alpha)
    # Exact match (zero residual) is strictly closer than any positive bound.
    report_flagged = error_bounding_report(model, eval_points=[(alpha, predicted)])

    assert report_flagged.generalization_check_required is True
    assert report_flagged.suspect_input == alpha

    sig = inspect.signature(error_bounding_report)
    assert set(sig.parameters.keys()) == {"model", "eval_points", "delta"}, (
        "error_bounding_report must expose no parameter through which a "
        "shifted-parameter-dynamics mechanism could be threaded in"
    )
