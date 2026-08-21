"""T002 — FR-001/FR-002: build_z2_lgt_model's Hamiltonian term library is
restricted to exactly {Z_v}_mass, {X_e}_electric, {h_e=(1/2)(A_e+B_e)}_hopping,
with LOCAL per-vertex/per-edge couplings (research.md R1: cited to the
primary report's own §5.1-5.3/eq. 25-27, giving d = |V| + 2|E| encoded
parameters) -- never the report's separate, global-scalar eq. 1-4 form."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import trotter_frontend
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, build_z2_lgt_model


def _two_site_one_edge_graph() -> Z2LGTGraph:
    return Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))


def test_parameter_count_is_local_d_equals_v_plus_2e() -> None:
    graph = _two_site_one_edge_graph()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    ir = trotter_frontend(
        num_qubits=model.num_sites,
        groups=model.coupling_groups,
        tau=1.0,
        r=1,
        observable=SparsePauliOp("I" * model.num_sites),
    )
    assert ir.num_parameters == 4, "d = |V| + 2|E| = 2 + 2 = 4 (local couplings, eq. 25-27)"
    multiplicities = sorted(p.multiplicity for p in ir.parameters())
    assert multiplicities == [1, 1, 1, 2], "mass/electric r_j=1, hopping r_j=2 (report §5.3 table)"


def test_hamiltonian_terms_are_restricted_to_the_three_generator_families() -> None:
    graph = _two_site_one_edge_graph()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    all_paulis = {term.pauli for group in model.coupling_groups for term in group.terms}
    # Full matter+gauge library only: single-qubit Z (mass), single-qubit X
    # (electric), and the two 3-qubit hopping strings XZX/YZY (A_e, B_e).
    assert all_paulis <= {"Z", "X", "XZX", "YZY"}
    assert "XZX" in all_paulis and "YZY" in all_paulis, "hopping (A_e, B_e) must be present"
    assert "Z" in all_paulis, "mass term must be present"
    assert "X" in all_paulis, "electric term must be present"


def test_hopping_group_ties_a_e_and_b_e_under_one_shared_label() -> None:
    graph = _two_site_one_edge_graph()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    hopping_groups = [g for g in model.coupling_groups if {t.pauli for t in g.terms} & {"XZX", "YZY"}]
    assert len(hopping_groups) == 1, "A_e and B_e must live in exactly one shared CouplingGroup"
    (hopping_group,) = hopping_groups
    assert {t.pauli for t in hopping_group.terms} == {"XZX", "YZY"}
    weights = {t.weight for t in hopping_group.terms}
    assert len(weights) == 1, "A_e and B_e must share the exact same structural weight"


def test_zero_coupling_is_rejected() -> None:
    from fourierlearn.models import ZeroCouplingError

    graph = _two_site_one_edge_graph()
    with pytest.raises(ZeroCouplingError):
        build_z2_lgt_model(
            graph,
            mass_couplings={0: 0.0, 1: -1.0},
            electric_couplings={0: 1.0},
            hopping_couplings={0: 1.0},
        )


def test_missing_coupling_declaration_is_rejected() -> None:
    graph = _two_site_one_edge_graph()
    with pytest.raises(ValueError):
        build_z2_lgt_model(
            graph,
            mass_couplings={0: 1.0},  # missing vertex 1
            electric_couplings={0: 1.0},
            hopping_couplings={0: 1.0},
        )
