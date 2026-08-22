"""T014 — Critical Guardrail 2 (this round): the sentinel transition test.
One FIXED problem instance (same T, d, lambda0, kappa, and signal
magnitude), evaluated on the noisy-KRR path TWICE -- once with `eps_k=
eps_y` set to the 2,000-shot Hoeffding value and once to the 200,000-shot
value, all other inputs identical -- must show `tightness_status`
transitioning from `"vacuous"` to `"informative"`, isolating shot count as
the only varying input across the two calls.
"""

from __future__ import annotations

import math

import numpy as np

from fourierlearn.kernel import noisy_krr_predict

_DELTA = 0.01


def _hoeffding_eps(shots: int, delta: float = _DELTA) -> float:
    return math.sqrt(2 * math.log(2 / delta) / shots)


def _fixed_instance():
    """A hand-picked instance whose bound coefficient `C = kappa*M/lambda0^2
    + kappa/lambda0 + M/lambda0` sits precisely in the range that makes
    `ratio(2,000 shots) = 2*C*eps(2000) >= 1.0` (vacuous) while
    `ratio(200,000 shots) = 2*C*eps(200000) < 0.2` (informative) --
    `kappa=label_bound=2.5`, `lambda0=1.0` gives `C=2.5*2.5+2.5+2.5=11.25`,
    so `ratio(2000)=2*11.25*0.07279=1.638` (>= 1.0) and
    `ratio(200000)=2*11.25*0.00728=0.164` (< 0.2). Single training point
    `gram=[[1]]`, `labels=[0.5]`, `test_row=[2]` -> `predicted=0.5`
    exactly, in both calls (the SAME instance)."""
    gram = np.array([[1.0]])
    labels = np.array([0.5])
    test_row = np.array([2.0])
    lambda0 = 1.0
    kappa = 2.5
    label_bound = 2.5
    return gram, labels, test_row, lambda0, kappa, label_bound


def test_tightness_status_transitions_from_vacuous_to_informative_on_the_same_instance() -> None:
    gram, labels, test_row, lambda0, kappa, label_bound = _fixed_instance()

    eps_2000 = _hoeffding_eps(2_000)
    eps_200000 = _hoeffding_eps(200_000)

    predicted_low, bound_low_shots = noisy_krr_predict(
        gram, labels, test_row, eps_2000, eps_2000, lambda0, kappa, label_bound
    )
    predicted_high, bound_high_shots = noisy_krr_predict(
        gram, labels, test_row, eps_200000, eps_200000, lambda0, kappa, label_bound
    )

    # The only varying input across the two calls is the shot-count-derived
    # eps_k/eps_y -- everything else (predicted value, hence
    # reference_magnitude) is identical between the two calls.
    assert math.isclose(predicted_low, predicted_high, abs_tol=1e-12)
    assert math.isclose(bound_low_shots.reference_magnitude, bound_high_shots.reference_magnitude, abs_tol=1e-12)

    assert bound_low_shots.tightness_status == "vacuous"
    assert bound_high_shots.tightness_status == "informative"
    assert bound_low_shots.error_bound > bound_high_shots.error_bound
    assert bound_low_shots.bound_to_reference_ratio > bound_high_shots.bound_to_reference_ratio
