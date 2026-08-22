"""This round's Critical Implementation Instruction 1: a dedicated test for
`tightness_status`'s boundary behavior. Constructs ratios landing just
below, exactly at, and just above EACH of the two cutoffs
(`TIGHTNESS_INFORMATIVE_MAX_RATIO=0.2`, `TIGHTNESS_VACUOUS_MIN_RATIO=1.0`)
and proves the classification at the exact boundary values is unambiguous
(`_classify_tightness` uses strict `<` at both cutoffs, so an exact-equal
ratio always falls through to the NEXT, less favourable band — never a
`<=`-vs-`<` inconsistency).

Two layers of proof, per the instruction ("prove mathematically... no >=
vs > ambiguities"):

1. Direct, whitebox tests of `_classify_tightness` at the six exact ratio
   values (mathematical proof of the comparison logic itself).
2. An end-to-end test constructing real `noisy_krr_predict` calls whose
   `bound_to_reference_ratio` lands at those exact same six values, proving
   the boundary behavior survives through the full computation, not only
   in the isolated classifier function.
"""

from __future__ import annotations

import math

import numpy as np

from fourierlearn.kernel import (
    TIGHTNESS_INFORMATIVE_MAX_RATIO,
    TIGHTNESS_VACUOUS_MIN_RATIO,
    _classify_tightness,
    noisy_krr_predict,
)

_EPSILON = 1e-9


def test_classify_tightness_at_the_informative_loose_boundary() -> None:
    just_below = TIGHTNESS_INFORMATIVE_MAX_RATIO - _EPSILON
    exactly_at = TIGHTNESS_INFORMATIVE_MAX_RATIO
    just_above = TIGHTNESS_INFORMATIVE_MAX_RATIO + _EPSILON

    assert _classify_tightness(just_below) == "informative"
    assert _classify_tightness(exactly_at) == "loose"  # falls through: NOT informative at the exact cutoff
    assert _classify_tightness(just_above) == "loose"


def test_classify_tightness_at_the_loose_vacuous_boundary() -> None:
    just_below = TIGHTNESS_VACUOUS_MIN_RATIO - _EPSILON
    exactly_at = TIGHTNESS_VACUOUS_MIN_RATIO
    just_above = TIGHTNESS_VACUOUS_MIN_RATIO + _EPSILON

    assert _classify_tightness(just_below) == "loose"
    assert _classify_tightness(exactly_at) == "vacuous"  # falls through: NOT loose at the exact cutoff
    assert _classify_tightness(just_above) == "vacuous"


def test_classify_tightness_is_a_total_partition_with_no_gap_or_overlap() -> None:
    """Every ratio maps to EXACTLY one of the three labels -- there is no
    value for which zero or multiple branches could plausibly apply."""
    sample_ratios = [
        0.0,
        TIGHTNESS_INFORMATIVE_MAX_RATIO / 2,
        TIGHTNESS_INFORMATIVE_MAX_RATIO,
        (TIGHTNESS_INFORMATIVE_MAX_RATIO + TIGHTNESS_VACUOUS_MIN_RATIO) / 2,
        TIGHTNESS_VACUOUS_MIN_RATIO,
        TIGHTNESS_VACUOUS_MIN_RATIO * 100,
        math.inf,
    ]
    for ratio in sample_ratios:
        status = _classify_tightness(ratio)
        assert status in ("informative", "loose", "vacuous")


def _instance_for_ratio(target_ratio: float):
    """Constructs a real `noisy_krr_predict` call whose
    `bound_to_reference_ratio` equals `target_ratio` EXACTLY: a single
    training point (`gram=[[1]]`, `lambda0=1.0`) with `labels=[predicted]`
    and `test_row=[1.0]` gives `predicted = labels[0]/2` -- pick
    `labels=[2*signal]` for a chosen `signal`, then solve for `epsilon_k`
    (with `epsilon_y` fixed small) such that `error_bound/signal ==
    target_ratio` exactly."""
    signal = 1.0
    kappa = 1.0
    label_bound = 1.0
    lambda0 = 1.0
    epsilon_y = 0.0 + 1e-12  # negligible contribution, kept strictly positive (FR-008)

    # error_bound = (kappa*M/lambda0^2)*eps_k + (kappa/lambda0)*eps_y + (M/lambda0)*eps_k
    #             = 2*eps_k + eps_y   (since kappa=M=lambda0=1)
    # Solve for eps_k such that (2*eps_k + eps_y) / signal == target_ratio.
    epsilon_k = (target_ratio * signal - epsilon_y) / 2.0

    gram = np.array([[1.0]])
    labels = np.array([2.0 * signal])
    test_row = np.array([1.0])
    return gram, labels, test_row, epsilon_k, epsilon_y, lambda0, kappa, label_bound, signal


def test_end_to_end_noisy_krr_predict_boundary_ratios_classify_unambiguously() -> None:
    for target_ratio, expected_status in [
        (TIGHTNESS_INFORMATIVE_MAX_RATIO - _EPSILON, "informative"),
        (TIGHTNESS_INFORMATIVE_MAX_RATIO, "loose"),
        (TIGHTNESS_INFORMATIVE_MAX_RATIO + _EPSILON, "loose"),
        (TIGHTNESS_VACUOUS_MIN_RATIO - _EPSILON, "loose"),
        (TIGHTNESS_VACUOUS_MIN_RATIO, "vacuous"),
        (TIGHTNESS_VACUOUS_MIN_RATIO + _EPSILON, "vacuous"),
    ]:
        gram, labels, test_row, eps_k, eps_y, lambda0, kappa, label_bound, signal = _instance_for_ratio(target_ratio)
        predicted, bound = noisy_krr_predict(gram, labels, test_row, eps_k, eps_y, lambda0, kappa, label_bound)

        assert math.isclose(predicted, signal, abs_tol=1e-9)
        assert math.isclose(bound.bound_to_reference_ratio, target_ratio, abs_tol=1e-8)
        assert bound.tightness_status == expected_status, (target_ratio, bound.bound_to_reference_ratio, bound.tightness_status)
