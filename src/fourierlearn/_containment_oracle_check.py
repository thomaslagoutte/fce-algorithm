"""The ONE production import of `fourierlearn.reference` outside
`reference.py` itself for Spec 8 (Constitution §11.6): extracts `Omega`,
the ansatz's true nonzero-coefficient frequency support, via the exact
oracle — isolated in its own single-function module, mirroring Spec 6's
`_exact_dynamics.py` precedent exactly. Never used for training or
feature construction; only for this one empirical containment check.

No optimisation (Constitution §5.3): one call to `reference.coefficients`
per invocation, already the minimal possible call count — nothing to
cache or batch.
"""

from __future__ import annotations

from fourierlearn import reference
from fourierlearn.ir import PauliEncodedCircuitIR


def extract_omega(
    ir: PauliEncodedCircuitIR,
    budget: int = reference.DEFAULT_BUDGET,
    confirm: bool = False,
    relative_eps: float = 1e-9,
) -> frozenset[tuple[int, ...]]:
    """The ansatz's true nonzero-coefficient frequency support, extracted
    by brute force against the exact oracle. A frequency is treated as
    "in Omega" if its magnitude exceeds `relative_eps` times the largest
    coefficient's magnitude — floating-point roundoff tolerance for an
    exact (noiseless) computation, not a shot-noise statistical bound."""
    coefficients = reference.coefficients(ir, budget=budget, confirm=confirm)
    max_magnitude = max(abs(value) for value in coefficients.values())
    threshold = relative_eps * max_magnitude if max_magnitude > 0 else relative_eps
    return frozenset(
        frequency for frequency, value in coefficients.items() if abs(value) > threshold
    )
