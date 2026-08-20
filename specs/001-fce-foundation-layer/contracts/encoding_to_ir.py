"""Contract: the `Encoding -> IR` boundary (spec FR-001).

This is the only Protocol this spec defines for the producing side of the IR. It
intentionally says nothing about *how* a concrete encoding decides its gate sequence,
qubit count, or observable — that is each encoding's own concern, in its own later
spec (Constitution §9.1: no layer reaches around another).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ir_types import PauliEncodedCircuitIR


@runtime_checkable
class Encoding(Protocol):
    """Produces a `PauliEncodedCircuitIR` from an encoding's own configuration.

    A concrete `Encoding` is free to take any constructor arguments it needs (e.g. a
    lattice size, a symmetry group, an upload schedule) — those are not part of this
    Protocol, since they differ per encoding and are exactly what "interchangeable by
    configuration" (Constitution §9.2, §9.4) means: this module never inspects them.
    """

    def build(self) -> PauliEncodedCircuitIR:
        """Return this encoding's circuit as an IR instance.

        MUST NOT branch on parameter count (Constitution §9.3) — per-parameter
        structure belongs in the returned IR's `gates`, not in this method's control
        flow.
        """
        ...


# --- Extension point (spec FR-002) ---------------------------------------------
#
# Later specs add their own `Protocol` classes to `src/fourierlearn/contracts.py` for
# boundaries that do not exist yet (`circuits`, `extract`, `backends`, `learn`,
# `models`, `experiment` — Constitution §9.1). They MUST NOT modify `Encoding`'s
# method signature above to do so; a new boundary gets a new Protocol class,
# co-located in the same module, with its own docstring citing which layers it
# connects.
