"""T017 — FR-009: `containment.compute_lambda`'s predicate, checked
against the 7 hand-derived positive/negative controls from research.md
R2 (evenness/eq.13, additive charge/eq.36, multiplicative Gauss/eq.37) --
hand-derived on paper before running, not fitted to the implementation's
output."""

from __future__ import annotations

from fourierlearn.containment import compute_lambda
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, coordinate_roles


def _roles():
    graph = Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))
    mass_axis_by_vertex, electric_axis_by_edge, _hopping_axes = coordinate_roles(graph)
    incidence = {v: graph.edges_touching(v) for v in range(graph.num_matter_sites)}
    return mass_axis_by_vertex, electric_axis_by_edge, incidence


# Axis order (from coordinate_roles/coordinate_order, alphabetical on labels
# "electric_0" < "hopping_0" < "mass_0" < "mass_1"): 0=electric, 1=hopping,
# 2=mass_v0, 3=mass_v1 -- matches research.md R2 exactly.
_CONTROLS = [
    ((0, 0, 0, 0), True, "all-zero: trivially satisfies charge and both Gauss checks"),
    ((0, 0, 2, -2), False, "charge OK (2-2=0) but Gauss FAILS at v0: 2/2 + 0/2 = 1 (mod 2)"),
    ((0, 0, 2, 2), False, "charge FAILS: 2+2=4 != 0"),
    ((2, 0, 2, 0), False, "charge FAILS: mass sum=2 != 0 (electric is irrelevant to charge)"),
    ((0, 0, -2, 2), False, "charge OK (0) but Gauss FAILS at v0: -2/2 + 0/2 = -1 = 1 (mod 2)"),
    ((1, 0, 0, 0), False, "odd component (electric=1): fails generic evenness (eq. 13)"),
    ((2, 0, -2, 2), True, "charge OK (-2+2=0); Gauss v0: -1+1=0 OK; Gauss v1: 1+1=2=0 OK"),
]


def test_lambda_predicate_matches_all_seven_hand_derived_controls() -> None:
    mass_axis_by_vertex, electric_axis_by_edge, incidence = _roles()
    lam = compute_lambda(
        ambient=[l for l, _, _ in _CONTROLS],
        mass_axis_by_vertex=mass_axis_by_vertex,
        electric_axis_by_edge=electric_axis_by_edge,
        incidence=incidence,
    )
    for l, expected, why in _CONTROLS:
        got = l in lam
        assert got == expected, f"in_lambda{l} = {got}, expected {expected} ({why})"
