"""Spec 11 T010 — FR-004/SC-005: `estimate_coefficient`'s `transpile()`
call site uses explicit, named, benchmarked constants for
`optimization_level` (and `basis_gates`) -- never Qiskit's own silent
default."""

from __future__ import annotations

from fourierlearn import extract


def test_optimization_level_is_an_explicit_named_constant() -> None:
    assert hasattr(extract, "_DEFAULT_OPTIMIZATION_LEVEL")
    assert isinstance(extract._DEFAULT_OPTIMIZATION_LEVEL, int)
    # research.md R5's own benchmarked choice, fastest of 0/1/2/3 on the
    # repaired construction.
    assert extract._DEFAULT_OPTIMIZATION_LEVEL == 1


def test_basis_gates_is_an_explicit_named_constant() -> None:
    assert hasattr(extract, "_DEFAULT_BASIS_GATES")
    # research.md R5 found no explicit re-basis beneficial -- `None` means
    # "AerSimulator's own native target," a documented value, not an
    # absent one.
    assert extract._DEFAULT_BASIS_GATES is None
