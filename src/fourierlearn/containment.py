"""Containment verification — FR-009..FR-014 (Spec 8, deliverable c).

Pure combinatorics over an ambient frequency box: no `Statevector`,
`Operator`, `expm`, or `fourierlearn.reference` import anywhere in this
module (that one production import, for the empirical `Omega` extraction
Constitution §11.6 requires, is isolated in the separate, narrowly-exempt
`_containment_oracle_check.py`).

`compute_lambda` applies Theorem 6.1 (report eq. 33, instantiated for Z2 at
eq. 36/37):

- eq. 13 (generic evenness, no symmetry needed): every frequency component
  is even.
- eq. 36 (additive charge, on the RAW pre-parity `l`): `sum_v l_v^(m) = 0`.
- eq. 37 (multiplicative Gauss, on `l/2 mod 2`), per vertex `v`:
  `l_v^(m)/2 + sum_{e touching v} l_e^(g)/2 == 0 (mod 2)`.
- The hopping coordinates are UNCONSTRAINED by either relation (report
  §7.1: `h_e` is not in the commuting family `F`, since it contains `Z_e`,
  which anticommutes with `X_e`) — `compute_lambda` takes no `hopping_axes`
  argument at all, since there is nothing to check there.

research.md R2 independently confirmed this reading of the report's own
`l` is this codebase's own pre-parity `l` (not a rescaled quantity) by
direct formula comparison against `frequency.register_width`'s own
docstring citation of the same report section.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from fourierlearn import frequency
from fourierlearn.ir import PauliEncodedCircuitIR

# Constitution §11.7/§11.8: every containment result MUST carry this
# caveat as a structural field, never only as prose that could be dropped.
NO_SEPARATION_CAVEAT = (
    "This is a constant-factor reduction (Constitution §11.7: Gauss's law "
    "is multiplicative, reducing only the index/prefactor, never the "
    "exponent). No quantum learning separation is claimed on this Z2 "
    "validation platform (Constitution §11.8): Lambda is itself "
    "classically computable in polynomial time and would reduce a "
    "classical learner's cost by the identical factor."
)


class DerivationDefectError(ValueError):
    """Raised when the empirically extracted Omega is found NOT to be a
    subset of the computed Lambda (Constitution §11.6) — a defect in this
    feature's own ansatz derivation, never silently tolerated or hidden by
    loosening Lambda after the fact."""


def compute_ambient_box(ir: PauliEncodedCircuitIR) -> frozenset[tuple[int, ...]]:
    """The full, symmetry-unaware ambient frequency box for `ir`'s own
    parameter structure (Constitution §11.3) — axis order matches
    `ir.parameters()`'s own order. Reuses `frequency.pre_parity_range`
    per parameter; no new logic."""
    domain_per_axis = [
        list(frequency.pre_parity_range(p.multiplicity, p.upload_count))
        for p in ir.parameters()
    ]
    ambient: list[tuple[int, ...]] = [()]
    for axis_values in domain_per_axis:
        ambient = [prefix + (value,) for prefix in ambient for value in axis_values]
    return frozenset(ambient)


def _in_lambda(
    l: tuple[int, ...],
    mass_axis_by_vertex: Mapping[int, int],
    electric_axis_by_edge: Mapping[int, int],
    incidence: Mapping[int, tuple[int, ...]],
) -> bool:
    if any(component % 2 != 0 for component in l):
        return False  # eq. 13: generic evenness, no symmetry needed
    charge = sum(l[mass_axis_by_vertex[v]] for v in mass_axis_by_vertex)
    if charge != 0:
        return False  # eq. 36: additive total-charge relation
    for v, edges in incidence.items():
        mass_half = l[mass_axis_by_vertex[v]] // 2
        electric_half_sum = sum(l[electric_axis_by_edge[e]] // 2 for e in edges)
        if (mass_half + electric_half_sum) % 2 != 0:
            return False  # eq. 37: multiplicative Gauss-law parity relation
    return True


def compute_lambda(
    ambient: Iterable[tuple[int, ...]],
    mass_axis_by_vertex: Mapping[int, int],
    electric_axis_by_edge: Mapping[int, int],
    incidence: Mapping[int, tuple[int, ...]],
) -> frozenset[tuple[int, ...]]:
    """Theorem 6.1's symmetry-restricted sublattice (report eq. 33/36/37):
    filters `ambient` by the additive charge and multiplicative Gauss
    relations (hopping axes are unconstrained, so no argument for them is
    needed). A single pass over `ambient` — no caching/batching
    (Constitution §5.3)."""
    return frozenset(
        l
        for l in ambient
        if _in_lambda(l, mass_axis_by_vertex, electric_axis_by_edge, incidence)
    )


@dataclass(frozen=True)
class ContainmentVerificationResult:
    """FR-009..FR-014: the full, honestly-scoped containment result for
    one declared instance.

    `reduction_factor` is populated ONLY from the exact, computed
    `ambient_size / lambda_size` ratio for THIS instance — never from, and
    never presented as confirming, the report's own asymptotic
    `2^{-(d+|V|)}` CLT-heuristic formula (research.md R2 found these do
    not numerically agree at finite `L`; Guardrail 2). `no_separation_caveat`
    is always non-empty (Constitution §11.7/§11.8)."""

    ambient_size: int
    lambda_size: int
    omega: frozenset[tuple[int, ...]]
    reduction_factor: float
    no_separation_caveat: str = NO_SEPARATION_CAVEAT

    def __post_init__(self) -> None:
        if not self.no_separation_caveat:
            raise ValueError("no_separation_caveat must never be empty (Constitution §11.7/§11.8)")


def verify_containment(
    ir: PauliEncodedCircuitIR,
    omega: frozenset[tuple[int, ...]],
    mass_axis_by_vertex: Mapping[int, int],
    electric_axis_by_edge: Mapping[int, int],
    incidence: Mapping[int, tuple[int, ...]],
) -> ContainmentVerificationResult:
    """Composes `compute_ambient_box`/`compute_lambda` with a caller-
    supplied, already-extracted `omega` (extraction itself lives in the
    narrowly-exempt `_containment_oracle_check.py`, never imported here)
    and asserts `Omega subset-of Lambda subset-of ambient` (Constitution
    §11.6) — raises `DerivationDefectError`, never silently tolerating a
    violation."""
    ambient = compute_ambient_box(ir)
    lam = compute_lambda(ambient, mass_axis_by_vertex, electric_axis_by_edge, incidence)

    not_contained = omega - lam
    if not_contained:
        raise DerivationDefectError(
            f"Omega is not a subset of Lambda -- {len(not_contained)} frequency "
            f"tuple(s) outside Lambda: {sorted(not_contained)[:5]}"
        )
    if not (len(lam) < len(ambient)):
        raise DerivationDefectError(
            f"Lambda ({len(lam)}) is not a strict, proper subset of ambient ({len(ambient)})"
        )

    return ContainmentVerificationResult(
        ambient_size=len(ambient),
        lambda_size=len(lam),
        omega=omega,
        reduction_factor=len(ambient) / len(lam),
    )
