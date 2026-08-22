"""T013 — reproduces research.md R1's exact three-shot-count sweep
(`2,000`/`20,000`/`200,000` shots, `delta=0.01`, this project's own
`sqrt(2*ln(2/delta)/shots)` Hoeffding formula) and asserts the resulting
`tightness_status` matches R1's own qualitative finding at each scale:
loose at low shot counts, improving toward informative at high shot
counts, on one deterministic, hand-computed instance (never left to chance
via an unlucky random draw -- kappa=1, label_bound=1, lambda0=1, a single
training point with `gram=[[1]]`, `labels=[0.5]`, `test_row=[2]`, giving
the exact, hand-verifiable prediction `0.5` and bound `3*eps`)."""

from __future__ import annotations

import math

import numpy as np

from fourierlearn.kernel import noisy_krr_predict

_DELTA = 0.01


def _hoeffding_eps(shots: int, delta: float = _DELTA) -> float:
    return math.sqrt(2 * math.log(2 / delta) / shots)


def _hand_verifiable_instance():
    """A single training point with `gram=[[1.0]]`, `lambda0=1.0`,
    `labels=[0.5]` -> `alpha = 0.5/(1+1) = 0.25`; `test_row=[2.0]` ->
    `predicted = 2.0*0.25 = 0.5` exactly. `kappa=label_bound=1.0` gives
    `error_bound = 3*eps` (all three eq. 5.94 terms collapse to `eps` each
    when `kappa=label_bound=lambda0=1`)."""
    gram = np.array([[1.0]])
    labels = np.array([0.5])
    test_row = np.array([2.0])
    lambda0 = 1.0
    kappa = 1.0
    label_bound = 1.0
    return gram, labels, test_row, lambda0, kappa, label_bound


def test_tightness_status_is_loose_at_2000_shots_on_the_hand_verifiable_instance() -> None:
    """research.md R1: at 2,000 shots the bound is comparable to (here,
    smaller than but not negligible relative to) the signal -- `bound=3*
    eps(2000)=0.2184`, `predicted=0.5`, `ratio=0.4368`, in the `[0.2, 1.0)`
    "loose" band, exactly reproducing R1's qualitative finding of a
    non-vacuous-but-not-yet-informative bound at this shot count."""
    gram, labels, test_row, lambda0, kappa, label_bound = _hand_verifiable_instance()
    eps = _hoeffding_eps(2_000)

    predicted, bound = noisy_krr_predict(gram, labels, test_row, eps, eps, lambda0, kappa, label_bound)

    assert math.isclose(predicted, 0.5, abs_tol=1e-12)
    assert math.isclose(bound.error_bound, 3 * eps, abs_tol=1e-12)
    assert bound.tightness_status == "loose"


def test_tightness_status_becomes_informative_at_200000_shots_on_the_same_instance() -> None:
    """research.md R1: at 200,000 shots on the SAME instance, `bound=3*
    eps(200000)=0.02184`, `ratio=0.04368 < 0.2` -- "informative"."""
    gram, labels, test_row, lambda0, kappa, label_bound = _hand_verifiable_instance()
    eps = _hoeffding_eps(200_000)

    predicted, bound = noisy_krr_predict(gram, labels, test_row, eps, eps, lambda0, kappa, label_bound)

    assert math.isclose(predicted, 0.5, abs_tol=1e-12)
    assert bound.tightness_status == "informative"


def test_tightness_ratio_strictly_improves_from_2000_to_20000_to_200000_shots() -> None:
    gram, labels, test_row, lambda0, kappa, label_bound = _hand_verifiable_instance()
    ratios = []
    for shots in (2_000, 20_000, 200_000):
        eps = _hoeffding_eps(shots)
        _, bound = noisy_krr_predict(gram, labels, test_row, eps, eps, lambda0, kappa, label_bound)
        ratios.append(bound.bound_to_reference_ratio)

    assert ratios[0] > ratios[1] > ratios[2]
