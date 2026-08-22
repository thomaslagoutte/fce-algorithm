"""T026 — FR-010..FR-014 (Critical Mandates 2 and the "Richer Fixture"
implementation instruction): the full, end-to-end containment proof
`Omega subset-of Lambda subset-of ambient`, on two instances:

1. The cheap `r=1` fixture (research.md R2): Omega is non-trivial (two
   genuinely nonzero, non-DC frequencies) but only directly exercises the
   hopping axis — mass/electric sit at 0 in every extracted Omega element
   (a genuine, checked fact of this specific observable/instance pairing,
   research.md's own honest finding).
2. A RICHER `r=2` fixture, discovered by ad hoc execution during
   implementation (mirroring the plan/research discipline): with two
   Trotter layers instead of one, the extracted Omega now contains
   elements with BOTH a nonzero mass AND a nonzero electric component
   simultaneously (e.g. `(-2,-8,-2,2)`: electric=-2, mass_v0=-2,
   mass_v1=2) -- the joint Gauss-law/charge cross-coupling (eq. 37 links
   `l_v^(m)/2` to `sum_e l_e^(g)/2`) is actively, non-vacuously exercised,
   not merely permitted by a trivially-zero coordinate. This second proof
   is intentionally slower (ambient box = 12393 points, predicted via
   `predict_grid_cost` and confirmed before being paid, Constitution
   §11.5) -- accepted as the one-time cost of a genuinely richer proof,
   not deferred.

Both assert the reported `reduction_factor` is the exact, computed
`ambient_size / lambda_size` ratio for THAT instance -- never the
report's asymptotic `2^{-(d+|V|)}` CLT-heuristic value (Guardrail 2)."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn._containment_oracle_check import extract_omega
from fourierlearn.containment import compute_ambient_box, compute_lambda, verify_containment
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, build_z2_lgt_model, coordinate_roles, to_circuit_ir


def _graph_and_roles():
    graph = Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))
    mass_axis_by_vertex, electric_axis_by_edge, _hopping_axes = coordinate_roles(graph)
    incidence = {v: graph.edges_touching(v) for v in range(graph.num_matter_sites)}
    return graph, mass_axis_by_vertex, electric_axis_by_edge, incidence


def test_omega_subset_lambda_subset_ambient_on_the_r1_fixture() -> None:
    graph, mass_axis, electric_axis, incidence = _graph_and_roles()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    observable = SparsePauliOp("IIZ")  # Z_v0
    ir = to_circuit_ir(model, tau=1.0, r=1, observable=observable, initial_occupation=(1,))

    omega = extract_omega(ir, budget=1125, confirm=True)

    # Exact frequency set, not a loose containment/subset check -- guards
    # against the 1e-9 relative threshold in extract_omega silently
    # leaking floating-point roundoff into Omega as spurious "nonzero"
    # entries (which an issubset-only check would never catch, since a
    # leaked entry could still happen to land inside Lambda).
    assert omega == {(0, -4, 0, 0), (0, 4, 0, 0)}

    result = verify_containment(ir, omega, mass_axis, electric_axis, incidence)

    assert result.ambient_size == 1125
    assert result.lambda_size == 25
    assert result.reduction_factor == 45.0, "must be the EXACT computed ratio, not the asymptotic value"
    asymptotic_value = 2 ** 6  # 2^(d+|V|) = 2^(4+2) = 64, report eq. 41's L-large heuristic
    assert result.reduction_factor != float(asymptotic_value), (
        "the exact, finite-L reduction must NOT be presented as, or coincide with, "
        "the report's own asymptotic CLT-heuristic value"
    )
    assert result.no_separation_caveat, "the no-separation caveat must always be a non-empty field"


def test_omega_subset_lambda_exercises_joint_mass_and_electric_coupling_on_a_richer_fixture() -> None:
    """The 'richer fixture' implementation instruction: r=2 (two Trotter
    layers) breaks the r=1 fixture's degeneracy on mass/electric,
    producing an Omega with elements where mass AND electric are BOTH
    nonzero at once -- proving the Gauss-law cross-coupling (eq. 37) is
    genuinely, non-vacuously exercised, not just permitted by a trivially
    -zero coordinate."""
    graph, mass_axis, electric_axis, incidence = _graph_and_roles()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    observable = SparsePauliOp("IIZ")  # Z_v0

    # Predicted and logged BEFORE being paid (Constitution §11.5): 9*9*9*17
    # = 12393 grid points -- confirmed explicitly via confirm=True below.
    ir = to_circuit_ir(model, tau=1.0, r=2, observable=observable, initial_occupation=(1,))
    predicted_cost = 12393

    omega = extract_omega(ir, budget=predicted_cost, confirm=True)

    # Exact frequency set (all 15 elements), captured by the ad hoc
    # discovery run during implementation -- not a loose issubset/
    # membership check. This is the guard against the 1e-9 relative
    # threshold in extract_omega silently leaking floating-point roundoff
    # into Omega: a leaked spurious entry would change this set's exact
    # membership even if it happened to still land inside Lambda (where a
    # subset-only check would miss it entirely).
    expected_omega = {
        (-2, -8, -2, 2), (-2, -8, 2, -2),
        (-2, 0, -2, 2), (-2, 0, 2, -2),
        (-2, 8, -2, 2), (-2, 8, 2, -2),
        (0, -8, 0, 0), (0, 0, 0, 0), (0, 8, 0, 0),
        (2, -8, -2, 2), (2, -8, 2, -2),
        (2, 0, -2, 2), (2, 0, 2, -2),
        (2, 8, -2, 2), (2, 8, 2, -2),
    }
    assert omega == expected_omega

    # The richness claim itself, re-asserted directly on the now-fixed
    # exact set: at least one Omega element has BOTH a nonzero mass
    # component and a nonzero electric component.
    richly_coupled = [
        l for l in omega
        if l[electric_axis[0]] != 0
        and any(l[mass_axis[v]] != 0 for v in mass_axis)
    ]
    assert richly_coupled, (
        f"Omega={sorted(omega)} has no element with both mass and electric "
        "nonzero -- the richer fixture did not exercise the joint "
        "Gauss-law/charge cross-coupling as required"
    )

    result = verify_containment(ir, omega, mass_axis, electric_axis, incidence)
    assert result.ambient_size == predicted_cost
    assert result.lambda_size == 117
    assert result.reduction_factor == predicted_cost / 117
    asymptotic_value = 2 ** 6  # d=4, |V|=2 -- unchanged by r; still not the exact value
    assert result.reduction_factor != float(asymptotic_value)
    assert result.no_separation_caveat
