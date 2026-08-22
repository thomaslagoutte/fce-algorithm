"""T009 — FR-005 Acceptance Scenario 1: Gram-matrix construction issues
exactly `O(T^2)` calls to the injected overlap callable."""

from __future__ import annotations

import numpy as np

from fourierlearn.kernel import build_gram_matrix


def test_gram_matrix_issues_exactly_t_squared_overlap_calls() -> None:
    inputs = ["a", "b", "c", "d"]
    call_count = 0

    def overlap(u, v):
        nonlocal call_count
        call_count += 1
        return float(len(u) + len(v))

    gram = build_gram_matrix(inputs, overlap)

    assert call_count == len(inputs) ** 2
    assert gram.shape == (len(inputs), len(inputs))


def test_gram_matrix_entries_match_the_overlap_callable() -> None:
    inputs = [1.0, 2.0, 3.0]

    def overlap(u, v):
        return u * v

    gram = build_gram_matrix(inputs, overlap)
    expected = np.outer(inputs, inputs)

    assert np.allclose(gram, expected)
