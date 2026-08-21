"""T024-T025 — User Story 3: the symmetry attach point is additive,
optional, and never evaluated by this feature."""

from __future__ import annotations

from fourierlearn.models import SymmetryDeclaration, TFIMEdge, TFIMGraph, build_tfim_model


def _path_graph_3() -> TFIMGraph:
    edges = (
        TFIMEdge(site_i=0, site_j=1, coupling_strength=1.5),
        TFIMEdge(site_i=1, site_j=2, coupling_strength=1.5),
    )
    return TFIMGraph(num_sites=3, edges=edges, field_strength=0.7)


def test_model_construction_unchanged_without_symmetry_declaration() -> None:
    graph = _path_graph_3()
    model_without = build_tfim_model(graph)
    model_with_explicit_none = build_tfim_model(graph, symmetry=None)

    assert model_without.symmetry is None
    assert model_without.coupling_groups == model_with_explicit_none.coupling_groups
    assert model_without.num_sites == model_with_explicit_none.num_sites


def test_symmetry_declaration_carried_through_unevaluated() -> None:
    graph = _path_graph_3()
    declaration = SymmetryDeclaration(name="Z2_global_flip", description="global spin flip")

    model = build_tfim_model(graph, symmetry=declaration)

    assert model.symmetry is declaration
    # Carrying the declaration through must not change the coupling-group
    # construction at all -- this feature never checks §11.1's conditions.
    model_without = build_tfim_model(graph)
    assert model.coupling_groups == model_without.coupling_groups
