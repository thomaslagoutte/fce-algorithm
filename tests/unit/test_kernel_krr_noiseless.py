"""T010 — `krr_fit_predict`'s exact (noiseless) KRR solve matches an
independently-computed closed-form ridge regression, on a small
hand-constructed problem."""

from __future__ import annotations

import numpy as np

from fourierlearn.kernel import krr_fit_predict


def test_krr_matches_independent_closed_form_ridge_regression() -> None:
    rng = np.random.default_rng(20260821)
    x = rng.normal(size=(5, 3))
    gram = x @ x.T
    labels = rng.normal(size=5)
    lambda0 = 0.3
    test_point = rng.normal(size=3)
    test_row = x @ test_point

    predicted = krr_fit_predict(gram, labels, lambda0, test_row)

    # Independent closed-form computation, never calling krr_fit_predict.
    coefficients = np.linalg.inv(gram + lambda0 * np.eye(5)) @ labels
    expected = float(test_row @ coefficients)

    assert np.isclose(predicted, expected, atol=1e-10)


def test_krr_reduces_to_a_hand_solved_two_point_problem() -> None:
    # K = [[1, 0], [0, 1]], Y = [2, 4], lambda0 = 1 -> alpha = Y / 2 = [1, 2]
    gram = np.eye(2)
    labels = np.array([2.0, 4.0])
    lambda0 = 1.0
    test_row = np.array([1.0, 0.0])

    predicted = krr_fit_predict(gram, labels, lambda0, test_row)

    assert np.isclose(predicted, 1.0, atol=1e-10)
