"""T003 — FR-003/FR-004 (Critical Mandate 1): build_z2_lgt_model always
declares its Gauss law generators as a SymmetryDeclaration and, via
PhysicalModelDescription's existing, UNMODIFIED Spec 7 __post_init__
enforcement, they must pass verify_symmetry before any circuit is
trusted. A hand-corrupted generator, constructed directly (bypassing
_gauss_law_generators), must be rejected."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.models import InvalidSymmetryError, PhysicalModelDescription, SymmetryDeclaration
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, _gauss_law_generators, build_z2_lgt_model


def _two_site_one_edge_graph() -> Z2LGTGraph:
    return Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))


def test_build_z2_lgt_model_attaches_a_verified_gauss_law_declaration() -> None:
    graph = _two_site_one_edge_graph()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    assert model.symmetry is not None
    assert model.symmetry.generators, "the Gauss law generators must be non-empty (never optional)"
    assert len(model.symmetry.generators) == graph.num_matter_sites


def test_gauss_law_generators_are_genuinely_different_per_vertex() -> None:
    graph = _two_site_one_edge_graph()
    generators = _gauss_law_generators(graph)
    labels = [str(g.paulis[0]) for g in generators]
    assert len(set(labels)) == len(labels), "G_v0 and G_v1 must be genuinely distinct"


def test_corrupted_generator_is_rejected_before_any_circuit_compiles() -> None:
    graph = _two_site_one_edge_graph()
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    # A hand-corrupted G_v0: Z on v0 alone, missing the electric/X_e01
    # factor entirely -- anticommutes with the hopping A_e/B_e terms.
    corrupted = SymmetryDeclaration(
        name="corrupted_gauss_law",
        generators=(SparsePauliOp("I" * (graph.num_qubits - 1) + "Z"),),
    )
    with pytest.raises(InvalidSymmetryError):
        PhysicalModelDescription(
            num_sites=model.num_sites,
            coupling_groups=model.coupling_groups,
            symmetry=corrupted,
        )
