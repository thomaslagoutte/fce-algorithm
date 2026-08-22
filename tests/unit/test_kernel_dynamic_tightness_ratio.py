"""T012 — Critical Guardrail 1 (this round): `bound_to_reference_ratio` and
`tightness_status` MUST be computed from each call's own LIVE signal
magnitude, never a constant carried over from research.md R1's own
Phase-0 sweep numbers. Proof: two problem instances sharing the exact same
`error_bound` but with deliberately different signal magnitudes (`Y` vs
`10*Y`) must classify differently.
"""

from __future__ import annotations

import numpy as np

from fourierlearn.kernel import noisy_krr_predict


def _fixed_instance(label_scale: float):
    gram = np.eye(3) * 5.0  # large diagonal -> tiny KRR coefficients -> small predicted magnitude scales with label_scale
    labels = np.array([1.0, 1.0, 1.0]) * label_scale
    test_row = np.array([5.0, 0.0, 0.0])
    lambda0 = 1.0
    kappa = 5.0
    label_bound = max(1.0, label_scale)
    eps_k = 1e-3
    eps_y = 1e-3
    return gram, labels, test_row, eps_k, eps_y, lambda0, kappa, label_bound


def test_bound_to_reference_ratio_depends_on_live_signal_not_a_constant() -> None:
    gram, labels_small, test_row, eps_k, eps_y, lambda0, kappa, label_bound_small = _fixed_instance(1.0)
    _, _, _, _, _, _, _, label_bound_large = _fixed_instance(10.0)
    gram_large, labels_large, _, _, _, _, _, _ = _fixed_instance(10.0)

    predicted_small, bound_small = noisy_krr_predict(
        gram, labels_small, test_row, eps_k, eps_y, lambda0, kappa, label_bound_small
    )
    predicted_large, bound_large = noisy_krr_predict(
        gram_large, labels_large, test_row, eps_k, eps_y, lambda0, kappa, label_bound_large
    )

    # Same error_bound magnitude structure is NOT assumed identical here --
    # what matters is that reference_magnitude tracks the live prediction.
    assert np.isclose(predicted_large, 10 * predicted_small, atol=1e-9)
    assert np.isclose(bound_small.reference_magnitude, abs(predicted_small), atol=1e-12)
    assert np.isclose(bound_large.reference_magnitude, abs(predicted_large), atol=1e-12)
    assert bound_small.reference_magnitude != bound_large.reference_magnitude


def test_identical_error_bound_different_signal_magnitude_classifies_differently() -> None:
    """The core proof: force `error_bound` to be numerically IDENTICAL
    across two calls (same eps_k, eps_y, lambda0, kappa, label_bound), vary
    only the live signal magnitude, and confirm the resulting ratio/status
    differ -- proving the ratio is never a frozen constant."""
    eps_k, eps_y, lambda0, kappa, label_bound = 1e-3, 1e-3, 1.0, 5.0, 1.0

    gram = np.eye(2) * 2.0
    small_labels = np.array([0.02, 0.02])
    large_labels = np.array([20.0, 20.0])
    test_row = np.array([2.0, 0.0])

    predicted_small, bound_small = noisy_krr_predict(
        gram, small_labels, test_row, eps_k, eps_y, lambda0, kappa, label_bound
    )
    predicted_large, bound_large = noisy_krr_predict(
        gram, large_labels, test_row, eps_k, eps_y, lambda0, kappa, label_bound
    )

    # error_bound is identical -- it does not depend on labels at all.
    assert bound_small.error_bound == bound_large.error_bound

    assert bound_small.reference_magnitude < bound_large.reference_magnitude
    assert bound_small.bound_to_reference_ratio > bound_large.bound_to_reference_ratio
    assert bound_small.tightness_status != bound_large.tightness_status
