"""T015 (renumbered from tasks.md's T015 into a standalone file) — FR-008:
`noisy_krr_predict` reports an explicit, structured error
(`InvalidBoundInputsError`) rather than silently computing a vacuous or
negative "bound" when any of `eps_k, eps_y, lambda0, kappa, label_bound`
is missing or non-positive.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from fourierlearn.kernel import InvalidBoundInputsError, noisy_krr_predict

_VALID = dict(
    gram_hat=np.array([[1.0]]),
    labels_hat=np.array([0.5]),
    test_row_hat=np.array([2.0]),
    epsilon_k=1e-3,
    epsilon_y=1e-3,
    lambda0=1.0,
    kappa=1.0,
    label_bound=1.0,
)


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("epsilon_k", 0.0),
        ("epsilon_k", -1e-3),
        ("epsilon_y", 0.0),
        ("epsilon_y", -1e-3),
        ("lambda0", 0.0),
        ("lambda0", -0.5),
        ("kappa", 0.0),
        ("kappa", -1.0),
        ("label_bound", 0.0),
        ("label_bound", -2.0),
        ("epsilon_k", math.nan),
        ("lambda0", None),
    ],
)
def test_non_positive_or_missing_bound_input_raises_explicitly(field: str, bad_value) -> None:
    kwargs = dict(_VALID)
    kwargs[field] = bad_value
    with pytest.raises(InvalidBoundInputsError):
        noisy_krr_predict(**kwargs)


def test_all_valid_positive_inputs_do_not_raise() -> None:
    noisy_krr_predict(**_VALID)
