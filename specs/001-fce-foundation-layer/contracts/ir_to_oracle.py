"""Contract: the `IR -> Oracle` boundary (spec FR-001).

The second and last Protocol this spec defines. `reference.py`'s exact oracle is the
one implementation shipped by this spec; a later, shot-based extractor implements the
*same* Protocol against a sampled estimate instead of an exact one (Constitution
§4.2's "sampled extractor vs. oracle" validation rung), which is why this boundary is
worth fixing now even though only one exact implementation exists yet.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ir_types import PauliEncodedCircuitIR

# Fourier coefficients, keyed by integer frequency tuple `l` in
# frequency.coordinate_order()'s canonical order, PRE-PARITY (frequency.py's pinned
# canonical representation — spec FR-008). Post-parity relabeling, if a caller wants
# it, is an explicit, separate call to `frequency.to_post_parity`, never implicit here.
FourierCoefficients = dict[tuple[int, ...], complex]


@runtime_checkable
class Oracle(Protocol):
    """Maps a `PauliEncodedCircuitIR` to its exact (or, later, sampled) Fourier
    coefficients.

    Implementations MUST predict and log the cost of whatever evaluation they perform
    before running it, and refuse to exceed a configured budget without explicit
    confirmation (Constitution §10.3) — this applies to `reference.py`'s Nyquist-grid
    cost now, and will apply equally to a later shot-based implementation's shot-count
    cost.
    """

    def coefficients(self, circuit: PauliEncodedCircuitIR) -> FourierCoefficients:
        """Return every Fourier coefficient this implementation computes.

        `reference.py`'s concrete oracle returns coefficients over the full
        Nyquist-sufficient grid (Constitution deliverable (d)); it is exact
        (floating-point precision only, no statistical tolerance — Constitution §4.4's
        shot-based tolerance rule does not apply to this implementation).
        """
        ...
