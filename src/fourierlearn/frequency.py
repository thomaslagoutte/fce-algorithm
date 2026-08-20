"""Frequency convention — FR-008, FR-009, FR-010, FR-020.

The single source of truth for frequency sign, pre-/post-parity indexing,
two's-complement decoding, coordinate ordering, the FFT-bin-to-l mapping, and
register width. Every function elsewhere that produces or consumes a frequency
MUST import from this module rather than redefining any part of it (Constitution
§6.1, spec FR-009).

Sign convention (spec FR-008): the pre-parity integer l = Λ - Λ' accumulates +1 per
even-parity contribution and -1 per odd-parity one, so l carries the same sign as
the exponent in e^{iπ c α l}. The concrete meaning of Λ/Λ' is fixed by whichever
encoding produces the IR; this module fixes only the arithmetic on the resulting
integer.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import numpy.typing as npt


def pre_parity_range(r_j: int, upload_count: int) -> range:
    """The canonical pre-parity integer domain for one coordinate:
    l in {-2*r_j*upload_count, ..., 2*r_j*upload_count}.
    """
    bound = 2 * r_j * upload_count
    return range(-bound, bound + 1)


def to_post_parity(l: int) -> int:
    """l -> l/2. Raises ValueError on odd `l` (§10.1 — no plausible wrong answer on
    a degenerate input); never silently truncates."""
    if l % 2 != 0:
        raise ValueError(f"to_post_parity requires an even pre-parity value, got {l}")
    return l // 2


def to_pre_parity(m: int) -> int:
    """Inverse of `to_post_parity`: m -> 2*m."""
    return 2 * m


def decode_twos_complement(bits: Sequence[int]) -> int:
    """Standard two's-complement decoding of a fixed-width bit sequence (MSB-first)
    into a signed integer."""
    n = len(bits)
    if n == 0:
        raise ValueError("decode_twos_complement requires at least one bit")
    value = -bits[0] * (1 << (n - 1))
    for i in range(1, n):
        value += bits[i] * (1 << (n - 1 - i))
    return value


def coordinate_order(labels: Sequence[str]) -> tuple[str, ...]:
    """The one canonical ordering of frequency-vector coordinates: numeric labels
    sort by their integer value (so "10" never sorts before "2"), non-numeric labels
    sort lexicographically after all numeric ones. Every function that builds or
    indexes a multi-dimensional frequency array MUST order its axes this way."""

    def key(label: str) -> tuple[int, object]:
        try:
            return (0, int(label))
        except ValueError:
            return (1, label)

    return tuple(sorted(labels, key=key))


def dft_frequencies(num_points: int) -> npt.NDArray[np.int_]:
    """The FFT-bin-index-to-signed-l mapping: for `numpy.fft.fft`/`fftn`'s bin k
    (0-indexed), returns k for k <= num_points//2 and k - num_points otherwise —
    equivalent to `numpy.fft.fftfreq(num_points) * num_points` rounded to int.

    Requires `num_points` odd (raises otherwise) — always true for the oracle's
    4*r_j*L+1-point grids, since 4*r_j*L is always even. Any function reading an FFT
    output array by frequency MUST call this rather than inlining `fftfreq`/
    `fftshift` arithmetic itself (FR-009) — verified in-session (research.md R7) that
    no extra conjugation or reflection is needed given the oracle's period-2 grid
    sampling convention (α_m = 2m/N).
    """
    if num_points % 2 == 0:
        raise ValueError(f"dft_frequencies requires an odd num_points, got {num_points}")
    k = np.arange(num_points)
    return np.where(k <= num_points // 2, k, k - num_points)


def register_width(uploads: int, r_j: int) -> int:
    """Number of bits needed to address the pre-parity range
    `pre_parity_range(r_j, uploads)` in two's complement:
    ceil(log2(4 * r_j * uploads + 1)).

    Directly sourced (research.md R12): `docs/references/equivariant FCE Z2LGT
    report.pdf`, §5.3, states this exact formula as the "Frequency register width
    per coordinate." Raises ValueError for uploads < 1 or r_j < 1 (§10.1) rather than
    returning a width computed from an out-of-range value.
    """
    if uploads < 1:
        raise ValueError(f"register_width requires uploads >= 1, got {uploads}")
    if r_j < 1:
        raise ValueError(f"register_width requires r_j >= 1, got {r_j}")
    return math.ceil(math.log2(4 * r_j * uploads + 1))
