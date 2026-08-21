"""Typed contracts — FR-001, FR-002, FR-003.

Defines a typed Protocol for each boundary this spec's scope actually crosses:
`Encoding -> IR` and `IR -> Oracle`. Does NOT define Protocols for pipeline layers
that do not yet exist (circuits, extract, backends, learn, models, experiment) —
those are added by their own specs as each layer is built (§9.1, §9.2).

Extension point (FR-002): later specs add their own Protocol classes to this same
module for their own boundary (e.g. `Circuits -> Extract`). They MUST NOT modify the
`Encoding` or `Oracle` Protocols defined below to do so — a new boundary gets a new
Protocol class, co-located in this module, with its own docstring citing which
layers it connects.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

from fourierlearn.ir import PauliEncodedCircuitIR

FourierCoefficients = dict[tuple[int, ...], complex]


@runtime_checkable
class Encoding(Protocol):
    """Produces a `PauliEncodedCircuitIR` from an encoding's own configuration.

    A concrete `Encoding` is free to take any constructor arguments it needs — those
    are not part of this Protocol, since "interchangeable by configuration" (§9.2,
    §9.4) means this module never inspects them.
    """

    def build(self) -> PauliEncodedCircuitIR:
        """Return this encoding's circuit as an IR instance.

        MUST NOT branch on parameter count (§9.3) — per-parameter structure belongs
        in the returned IR's `gates`, not in this method's control flow.
        """
        ...


@runtime_checkable
class Oracle(Protocol):
    """Maps a `PauliEncodedCircuitIR` to its exact (or, later, sampled) Fourier
    coefficients.

    Implementations MUST predict and log the cost of whatever evaluation they
    perform before running it, and refuse to exceed a configured budget without
    explicit confirmation (§10.3).
    """

    def coefficients(self, circuit: PauliEncodedCircuitIR) -> FourierCoefficients:
        """Return every Fourier coefficient this implementation computes, keyed by
        integer frequency tuple `l` (pre-parity, per frequency.py's convention)."""
        ...


@runtime_checkable
class RegressionBackend(Protocol):
    """The Extract -> Learn boundary (Spec 5, Learning Backend Layer): maps a
    real-valued Fourier sensing matrix and its measured labels to a fitted
    real-stacked coefficient vector.

    `fit` MUST accept exactly `(A, y)` — no third parameter of any kind. This
    is a structural, not merely conventional, guarantee: it makes it
    impossible for a concrete backend's regularization-penalty selection to
    ever receive `shots`, `tau`, or `r` as an input, closing the historical
    "$t^2$-penalty bug" (penalty anchored to the shot-noise bound or
    Trotter evolution time) at the interface level, not just by review
    discipline. A concrete `RegressionBackend` is free to take any
    constructor arguments it needs (e.g. a penalty grid, a cross-validation
    fold count, a random seed) — those are not part of this Protocol, since
    "interchangeable by configuration" (§9.2, §9.4) means this module never
    inspects them.
    """

    def fit(self, A: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """Return the fitted real-stacked coefficient vector `x` solving the
        (generally under-determined) linear system `y = A @ x`."""
        ...
