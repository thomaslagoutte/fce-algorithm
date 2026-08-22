"""T011 — spec.md Finding 3, made permanent: a 500-trial Monte Carlo sweep
with generic, arbitrary-magnitude noise (`eps_k, eps_y` in `1e-4`-`1e-2`)
never violates eq. 5.94's bound. Uses a fixed, arbitrarily chosen seed --
not tuned by trying seeds until the test passed.
"""

from __future__ import annotations

import numpy as np

from fourierlearn.kernel import krr_fit_predict, noisy_krr_predict

_SEED = 20260821


def test_noisy_krr_bound_is_never_violated_across_500_generic_noise_trials() -> None:
    rng = np.random.default_rng(_SEED)
    trials = 500
    violations = 0
    max_ratio = 0.0

    for _ in range(trials):
        t = int(rng.integers(3, 8))
        d = int(rng.integers(2, 6))
        x = rng.normal(size=(t, d))
        gram = x @ x.T
        kappa = float(max(1.0, np.max(np.diag(gram)) + 0.5))
        label_bound = 1.0
        labels = rng.uniform(-label_bound, label_bound, size=t)
        lambda0 = float(rng.uniform(0.05, 1.0))

        eps_k = float(rng.uniform(1e-4, 1e-2))
        eps_y = float(rng.uniform(1e-4, 1e-2))

        noise_k = rng.uniform(-eps_k, eps_k, size=(t, t))
        noise_k = (noise_k + noise_k.T) / 2
        noise_y = rng.uniform(-eps_y, eps_y, size=t)
        gram_hat = gram + noise_k
        labels_hat = labels + noise_y

        test_point = rng.normal(size=d)
        test_row = x @ test_point
        noise_f = rng.uniform(-eps_k, eps_k, size=t)
        test_row_hat = test_row + noise_f

        exact_prediction = krr_fit_predict(gram, labels, lambda0, test_row)
        noisy_prediction, bound = noisy_krr_predict(
            gram_hat, labels_hat, test_row_hat, eps_k, eps_y, lambda0, kappa, label_bound
        )

        lhs = abs(noisy_prediction - exact_prediction)
        assert lhs <= bound.error_bound, (lhs, bound.error_bound)
        max_ratio = max(max_ratio, lhs / bound.error_bound)
        if lhs > bound.error_bound:
            violations += 1

    assert violations == 0
    assert max_ratio < 1.0
