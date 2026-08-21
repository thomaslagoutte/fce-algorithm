"""Experiment layer — FR-001..FR-004, FR-008..FR-010: the generalization-
check mechanism that resolves Spec 5's `ErrorBoundingReport.generalization_check_required`
flag (Constitution §8.2).

Compares a fitted model's (deterministic) prediction against the genuinely
exact ground-truth dynamics at a classical input shifted away from every
training input, using `fourierlearn._exact_dynamics.exact_dynamics` — the
one, narrowly-authorized oracle access (FR-011) — never a finite-shot
measurement or a finer-Trotter approximation, neither of which can
distinguish a real capability from an overfitting artifact
(research.md R1's executed refutation guard).

This module MUST NOT import `fourierlearn.reference` itself, only
`fourierlearn._exact_dynamics.exact_dynamics`. It never mutates the
`ErrorBoundingReport` it consumes (FR-003) and never sets or upgrades
`PacBound.weight_space_translation_status` (FR-004) — it has no code path
that could, since it only ever reads report fields, never constructs a new
`PacBound`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from fourierlearn._exact_dynamics import exact_dynamics
from fourierlearn.learn import ErrorBoundingReport, LearnedModel, predict

# Shift-leakage tolerance (FR-009): mirrors the discipline of Spec 5's own
# tau tolerance (learn.py's _TAU_REL_TOL/_TAU_ABS_TOL) -- pinned constants,
# not inline magic numbers.
_SHIFT_REL_TOL = 1e-9
_SHIFT_ABS_TOL = 1e-9

# Default shift offset applied to `suspect_input` when the caller does not
# supply an explicit one -- large enough to be unambiguously "a different
# point," never chosen per call.
_DEFAULT_SHIFT_MAGNITUDE = 5.0


class TrainingInputLeakageError(ValueError):
    """Raised when the generalization check's selected shifted input
    coincides with (or is numerically indistinguishable from) a training
    input — FR-009. A degenerate "shift" that lands back on a training
    point is not a generalization test at all."""


@dataclass(frozen=True)
class GeneralizationCheckResult:
    """FR-001/FR-002's output — spec.md's "Generalization check result" Key
    Entity. `containment_record`/`sparsity_mechanism` are Constitution §11
    attach points (User Story 3): always `None` here, never populated by
    this module."""

    shifted_input: tuple[float, ...]
    exact_value: float
    predicted_value: float
    trotter_bound: float
    verdict: str
    boundary_tie: bool
    containment_record: str | None = None
    sparsity_mechanism: str | None = None


def _is_shifted_away(alpha: tuple[float, ...], training_alphas: Sequence[tuple[float, ...]]) -> bool:
    for train_alpha in training_alphas:
        if len(alpha) == len(train_alpha) and all(
            math.isclose(a, t, rel_tol=_SHIFT_REL_TOL, abs_tol=_SHIFT_ABS_TOL)
            for a, t in zip(alpha, train_alpha)
        ):
            return False
    return True


def select_shifted_input(
    suspect_input: tuple[float, ...],
    training_alphas: Sequence[tuple[float, ...]],
    shift: tuple[float, ...] | None = None,
) -> tuple[float, ...]:
    """FR-001/FR-009: select a classical input strictly shifted away from
    every training input the original model used. Defaults to offsetting
    every component of `suspect_input` by `_DEFAULT_SHIFT_MAGNITUDE`; a
    caller may supply an explicit `shift` instead. Asserts — after
    selection, not before — that the result does not coincide with any
    training input, raising `TrainingInputLeakageError` if it does."""
    if shift is None:
        shift = tuple(_DEFAULT_SHIFT_MAGNITUDE for _ in suspect_input)
    shifted = tuple(a + s for a, s in zip(suspect_input, shift))
    if not _is_shifted_away(shifted, training_alphas):
        raise TrainingInputLeakageError(
            f"selected shifted input {shifted} coincides with a training input — "
            "not a valid generalization test"
        )
    return shifted


def run_generalization_check(
    report: ErrorBoundingReport,
    model: LearnedModel,
    training_alphas: Sequence[tuple[float, ...]],
    suspect_input: tuple[float, ...] | None = None,
    shift: tuple[float, ...] | None = None,
) -> GeneralizationCheckResult:
    """FR-001, FR-002, FR-003, FR-004: run the generalization check that
    resolves `report.generalization_check_required`.

    `suspect_input` defaults to `report.suspect_input` if not given
    explicitly. The comparison threshold is read directly from
    `report.trotter_bound.structural_approximation_bound` (Spec 5's own
    shipped field) — never a flattened or re-derived value on `model`.
    The verdict is `"generalizes"` if
    `abs(predicted - exact) <= trotter_bound` (inclusive — an exact
    boundary tie counts as `generalizes`, recorded separately via
    `boundary_tie`) and `"refuted"` otherwise. Both sides of the
    comparison are deterministic, so this is an absolute rule with no
    noise-based hedging (research.md R2).

    Never mutates `report` — only reads
    `report.suspect_input`/`report.trotter_bound.structural_approximation_bound`.
    """
    if suspect_input is None:
        if report.suspect_input is None:
            raise ValueError(
                "run_generalization_check requires a suspect_input, either explicitly "
                "or via report.suspect_input"
            )
        suspect_input = report.suspect_input

    shifted_input = select_shifted_input(suspect_input, training_alphas, shift)

    exact_value = exact_dynamics(model.ir, model.observable, shifted_input)
    predicted_value = predict(model, shifted_input)

    trotter_bound = report.trotter_bound.structural_approximation_bound
    gap = abs(predicted_value - exact_value)
    boundary_tie = gap == trotter_bound
    verdict = "generalizes" if gap <= trotter_bound else "refuted"

    return GeneralizationCheckResult(
        shifted_input=shifted_input,
        exact_value=exact_value,
        predicted_value=predicted_value,
        trotter_bound=trotter_bound,
        verdict=verdict,
        boundary_tie=boundary_tie,
    )
