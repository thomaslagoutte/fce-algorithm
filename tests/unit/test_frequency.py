"""FR-008, FR-009, FR-010: the frequency-convention module is the sole source of
truth for sign, pre-/post-parity indexing, two's-complement decoding, coordinate
ordering, the FFT-bin-to-l mapping, and register width.
"""

from __future__ import annotations

import numpy as np
import pytest

from fourierlearn import frequency


# --- pre_parity_range (FR-008) ---------------------------------------------------


def test_pre_parity_range_r1_l1() -> None:
    assert list(frequency.pre_parity_range(r_j=1, upload_count=1)) == [-2, -1, 0, 1, 2]


def test_pre_parity_range_scales_with_r_j_and_uploads() -> None:
    assert list(frequency.pre_parity_range(r_j=2, upload_count=1)) == list(range(-4, 5))


# --- to_post_parity / to_pre_parity (FR-008, FR-009) -----------------------------


def test_to_post_parity_halves_even_values() -> None:
    assert frequency.to_post_parity(4) == 2
    assert frequency.to_post_parity(-4) == -2
    assert frequency.to_post_parity(0) == 0


def test_to_post_parity_raises_on_odd_input() -> None:
    with pytest.raises(ValueError):
        frequency.to_post_parity(3)


def test_to_pre_parity_is_inverse_of_to_post_parity() -> None:
    for l in range(-6, 7, 2):
        assert frequency.to_pre_parity(frequency.to_post_parity(l)) == l


# --- decode_twos_complement (FR-008) ---------------------------------------------


def test_decode_twos_complement_positive() -> None:
    assert frequency.decode_twos_complement([0, 1, 0, 1]) == 5


def test_decode_twos_complement_negative() -> None:
    assert frequency.decode_twos_complement([1, 1, 0, 1]) == -3


def test_decode_twos_complement_zero_and_minus_one() -> None:
    assert frequency.decode_twos_complement([0, 0, 0]) == 0
    assert frequency.decode_twos_complement([1, 1, 1]) == -1


# --- coordinate_order (FR-008) ---------------------------------------------------


def test_coordinate_order_is_numerically_stable_beyond_single_digits() -> None:
    # A naive lexicographic sort would put "10" before "2" — coordinate_order must not.
    assert frequency.coordinate_order(["10", "2", "1"]) == ("1", "2", "10")


def test_coordinate_order_deterministic_regardless_of_caller() -> None:
    labels = ["3", "1", "2"]
    assert frequency.coordinate_order(labels) == frequency.coordinate_order(list(reversed(labels)))


# --- dft_frequencies (FR-008, FR-009, FR-011) ------------------------------------


def test_dft_frequencies_matches_hand_computed_bin_order() -> None:
    assert list(frequency.dft_frequencies(5)) == [0, 1, 2, -2, -1]


def test_dft_frequencies_larger_odd_case() -> None:
    assert list(frequency.dft_frequencies(9)) == [0, 1, 2, 3, 4, -4, -3, -2, -1]


def test_dft_frequencies_rejects_even_input() -> None:
    with pytest.raises(ValueError):
        frequency.dft_frequencies(4)


def test_dft_frequencies_matches_numpy_fftfreq_convention() -> None:
    n = 7
    expected = np.round(np.fft.fftfreq(n) * n).astype(int)
    assert list(frequency.dft_frequencies(n)) == list(expected)


# --- register_width (FR-010) -----------------------------------------------------


@pytest.mark.parametrize(
    "uploads,r_j,expected_width",
    [
        (1, 1, 3),  # boundary case: 4*1*1+1=5 states, ceil(log2(5))=3 — proves the
        # old max(2, ...) floor is safely omitted now that uploads=0/r_j=0 raise.
        (2, 1, 4),
        (1, 2, 4),
        (2, 2, 5),
    ],
)
def test_register_width_matches_hand_computed_table(uploads: int, r_j: int, expected_width: int) -> None:
    assert frequency.register_width(uploads, r_j) == expected_width


def test_register_width_rejects_zero_uploads() -> None:
    with pytest.raises(ValueError):
        frequency.register_width(uploads=0, r_j=1)


def test_register_width_rejects_zero_multiplicity() -> None:
    with pytest.raises(ValueError):
        frequency.register_width(uploads=1, r_j=0)
