"""kernel.py: Gram-matrix assembly and (noisy) kernel ridge regression, Spec 10.

Deliverable (b), thesis §5.7.7-§5.7.8, eq. 5.72-5.94. This module is pure
NumPy linear algebra over already-estimated kernel values and labels — it
never imports `circuits`, `reference`, or any Qiskit object (Constitution
§3.4's CI import guard applies to every production module, and this one has
no legitimate exact-simulation or circuit-construction need at all): the
caller supplies the Gram matrix (however it was measured — exact oracle in
tests, finite-shot circuit execution in production) as a plain array.

No caching, batching, or memoization is introduced anywhere below
(Constitution §5.3, this round's Strict Constraint) — every function here
is `O(1)` or the feature's own already-declared `O(T^2)`/`O(T^3)` cost
(Gram-matrix assembly, KRR's linear solve), and none of it has been
profiled as a bottleneck, so none of it is optimised.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

import numpy as np
import numpy.typing as npt

T_Input = TypeVar("T_Input")

# --- Deliverable (b), FR-005: Gram-matrix assembly -------------------------


def build_gram_matrix(
    inputs: Sequence[T_Input], overlap: Callable[[T_Input, T_Input], float]
) -> npt.NDArray[np.float64]:
    """FR-005 Acceptance Scenario 1: exactly `O(T^2)` calls to `overlap`
    (never more, never fewer) — `overlap` is an injected callable, never a
    hardcoded reference to `reference.kernel_overlap_oracle` or a compiled
    circuit, so this module stays agnostic to how each entry was actually
    measured (exact oracle for tests, finite-shot circuit execution for
    production). Constitution §5.3: no caching, batching, or memoization —
    every entry is computed fresh, unprofiled and by design."""
    size = len(inputs)
    gram = np.zeros((size, size), dtype=np.float64)
    for i in range(size):
        for j in range(size):
            gram[i, j] = overlap(inputs[i], inputs[j])
    return gram


# --- Noiseless kernel ridge regression --------------------------------------


def krr_fit_predict(
    gram: npt.NDArray[np.float64],
    labels: npt.NDArray[np.float64],
    lambda0: float,
    test_row: npt.NDArray[np.float64],
) -> float:
    """The exact (noiseless) KRR prediction `h_{K,Y}(x') = k(x')^T (K +
    lambda0 I)^{-1} Y` — the reference every noisy prediction (below) is
    compared against. Constitution §5.3: no caching of the solved
    coefficients across calls — each call re-solves from scratch."""
    size = gram.shape[0]
    coefficients = np.linalg.solve(gram + lambda0 * np.eye(size), labels)
    return float(np.asarray(test_row) @ coefficients)


# --- Noisy kernel ridge regression, eq. 5.79-5.94 ---------------------------


class InvalidBoundInputsError(ValueError):
    """FR-008: raised when any of the noisy-KRR bound's own required inputs
    (`epsilon_k`, `epsilon_y`, `lambda0`, `kappa`, `label_bound`) is missing
    or non-positive — the bound is undefined/vacuous in that case and MUST
    be reported as such rather than silently computed as a nonsensical or
    negative number (Constitution §10.1)."""


# research.md R2's three-way tightness classification, its cutoffs chosen
# from the executed realistic-noise sweep's own distribution (research.md
# R1: median ratio 0.070-0.225 at informative/borderline shot counts, mean
# ratio 0.587-1.919 at loose-to-vacuous ones) -- these two CONSTANTS are the
# only fixed numbers in this classification; the ratio they classify is
# always a fresh, per-call value (see `_reference_magnitude` below), never a
# number carried over from that sweep.
TIGHTNESS_INFORMATIVE_MAX_RATIO = 0.2
"""Ratios strictly below this classify as `"informative"`."""

TIGHTNESS_VACUOUS_MIN_RATIO = 1.0
"""Ratios at or above this classify as `"vacuous"`; ratios in between
classify as `"loose"`."""


def _classify_tightness(ratio: float) -> str:
    """Three-way classification using strict `<` at both cutoffs only, so
    there is exactly one comparison outcome at each exact boundary value —
    never an ambiguity between adjacent branches:

    - `ratio == TIGHTNESS_INFORMATIVE_MAX_RATIO` (`0.2`) fails the first
      `<` test and falls through to `"loose"` (not `"informative"`).
    - `ratio == TIGHTNESS_VACUOUS_MIN_RATIO` (`1.0`) fails the second `<`
      test and falls through to `"vacuous"` (not `"loose"`).

    Verified directly by a dedicated boundary test constructing ratios just
    below, exactly at, and just above each cutoff."""
    if ratio < TIGHTNESS_INFORMATIVE_MAX_RATIO:
        return "informative"
    if ratio < TIGHTNESS_VACUOUS_MIN_RATIO:
        return "loose"
    return "vacuous"


@dataclass(frozen=True)
class NoisyKRRBound:
    """research.md R2: mirrors `learn.py`'s `PacBound.weight_space_
    translation_status` pattern — a required, always-populated status field
    recorded directly on the result object, never only in a docstring.

    `error_bound` is eq. 5.94's own right-hand side, computed from the
    bound's OWN required inputs (`epsilon_k`, `epsilon_y`, `lambda0`,
    `kappa`, `label_bound` — the last being eq. 5.94's `M`, an a priori
    assumed sup-bound on the labels, NOT a live measurement).

    `reference_magnitude` and `bound_to_reference_ratio`, by contrast, are
    THIS call's own live signal magnitude and the resulting bound-to-signal
    ratio (this round's Critical Guardrail 1) — never a constant copied
    from any prior sweep. `tightness_status` is derived from that ratio via
    `_classify_tightness`."""

    error_bound: float
    reference_magnitude: float
    bound_to_reference_ratio: float
    tightness_status: str
    epsilon_k: float
    epsilon_y: float
    lambda0: float
    kappa: float
    label_bound: float


def noisy_krr_bound_value(epsilon_k: float, epsilon_y: float, lambda0: float, kappa: float, label_bound: float) -> float:
    """eq. 5.94: `|h_{K̂,Ŷ}(x')-h_{K,Y}(x')| ≤ (κM/λ₀²)ε_k + (κ/λ₀)ε_y +
    (M/λ₀)ε_k` — transcribed literally, verified never violated across 500
    Monte Carlo trials at both generic-magnitude noise (spec.md Finding 3)
    and realistic, Spec-4-derived Hoeffding shot-noise scales (research.md
    R1)."""
    return (kappa * label_bound / lambda0**2) * epsilon_k + (kappa / lambda0) * epsilon_y + (
        label_bound / lambda0
    ) * epsilon_k


def _project_psd(matrix: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """A noisy `K̂=K+E_K` need not be positive semi-definite; this
    eigenvalue-clipping projection (the specific PSD-correction method this
    plan-level decision selects, per the thesis's own citation [167] for eq.
    5.94's context) symmetrizes first (entrywise noise need not itself be
    symmetric) and clips every negative eigenvalue to `0`."""
    symmetric = (matrix + matrix.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    clipped = np.clip(eigenvalues, 0.0, None)
    return (eigenvectors * clipped) @ eigenvectors.T


def _validate_bound_inputs(epsilon_k: float, epsilon_y: float, lambda0: float, kappa: float, label_bound: float) -> None:
    for name, value in (
        ("epsilon_k", epsilon_k),
        ("epsilon_y", epsilon_y),
        ("lambda0", lambda0),
        ("kappa", kappa),
        ("label_bound", label_bound),
    ):
        if value is None or not isinstance(value, (int, float)) or not (value > 0):
            raise InvalidBoundInputsError(
                f"noisy_krr_predict requires {name} to be a positive, finite number, "
                f"got {value!r} (FR-008) -- the eq. 5.94 bound is undefined without it, "
                "and this feature reports that explicitly rather than computing a "
                "vacuous or negative 'bound'"
            )


def _reference_magnitude(predicted: float, labels_hat: npt.NDArray[np.float64]) -> float:
    """This round's Critical Guardrail 1: the bound's own denominator is
    THIS call's live signal magnitude, computed fresh every time -- the
    predicted value's own magnitude, falling back to the noisy labels'
    Euclidean norm only when the prediction is exactly zero (a genuinely
    degenerate instance, not a shortcut). Never a constant copied from
    research.md R1's own illustrative sweep numbers."""
    magnitude = abs(predicted)
    if magnitude == 0.0:
        magnitude = float(np.linalg.norm(labels_hat))
    return magnitude


def noisy_krr_predict(
    gram_hat: npt.NDArray[np.float64],
    labels_hat: npt.NDArray[np.float64],
    test_row_hat: npt.NDArray[np.float64],
    epsilon_k: float,
    epsilon_y: float,
    lambda0: float,
    kappa: float,
    label_bound: float,
) -> tuple[float, NoisyKRRBound]:
    """FR-006/FR-007: the noisy-KRR prediction on a noisy Gram matrix
    `K̂=K+E_K`, noisy labels `Ŷ=Y+E_Y`, and a noisy test-evaluation row
    `F̂=F+E_F`, together with its eq. 5.94 error bound and honesty sentinel
    (`NoisyKRRBound`) — FR-006 Acceptance Scenario 3: a prediction is never
    returned without its accompanying bound. Constitution §5.3: no
    caching, batching, or memoization — every call re-projects `K̂` to PSD
    and re-solves KRR from scratch, unprofiled and by design."""
    _validate_bound_inputs(epsilon_k, epsilon_y, lambda0, kappa, label_bound)

    gram_psd = _project_psd(np.asarray(gram_hat, dtype=np.float64))
    predicted = krr_fit_predict(gram_psd, np.asarray(labels_hat, dtype=np.float64), lambda0, np.asarray(test_row_hat, dtype=np.float64))

    bound = noisy_krr_bound_value(epsilon_k, epsilon_y, lambda0, kappa, label_bound)
    reference_magnitude = _reference_magnitude(predicted, np.asarray(labels_hat, dtype=np.float64))
    ratio = bound / reference_magnitude if reference_magnitude > 0.0 else math.inf
    status = _classify_tightness(ratio)

    return predicted, NoisyKRRBound(
        error_bound=bound,
        reference_magnitude=reference_magnitude,
        bound_to_reference_ratio=ratio,
        tightness_status=status,
        epsilon_k=epsilon_k,
        epsilon_y=epsilon_y,
        lambda0=lambda0,
        kappa=kappa,
        label_bound=label_bound,
    )
