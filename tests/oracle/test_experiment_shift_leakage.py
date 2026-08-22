"""T011 — FR-009: the generalization check's shifted-input selection
rejects a shift that degenerates back onto a training input, mirroring
Spec 5's own FR-005 leakage-check discipline."""

from __future__ import annotations

import pytest

from fourierlearn.experiment import TrainingInputLeakageError, select_shifted_input


def test_shifted_input_never_coincides_with_training_input() -> None:
    training_alphas = [(0.3, -0.4), (-0.7, 1.1)]
    suspect_input = (0.3, -0.4)

    # A degenerate "shift" of exactly zero lands back on a training input.
    with pytest.raises(TrainingInputLeakageError):
        select_shifted_input(suspect_input, training_alphas, shift=(0.0, 0.0))


def test_default_shift_is_genuinely_disjoint_from_training_inputs() -> None:
    training_alphas = [(0.3, -0.4), (-0.7, 1.1)]
    suspect_input = (0.3, -0.4)

    shifted = select_shifted_input(suspect_input, training_alphas)
    assert shifted not in training_alphas
    assert shifted != suspect_input
