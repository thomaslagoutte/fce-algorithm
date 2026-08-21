"""T017-T020 — TFIM model construction: the default uniform-coupling case
produces exactly two CouplingGroups (Guardrail #1, research.md R5),
explicit per-edge labels produce one group per label, an isolated node
succeeds, and a zero coupling is rejected explicitly."""

from __future__ import annotations

import pytest

from fourierlearn.models import TFIMEdge, TFIMGraph, ZeroCouplingError, build_tfim_model


def _path_graph_3(coupling: float = 1.5, field: float = 0.7) -> TFIMGraph:
    edges = (
        TFIMEdge(site_i=0, site_j=1, coupling_strength=coupling),
        TFIMEdge(site_i=1, site_j=2, coupling_strength=coupling),
    )
    return TFIMGraph(num_sites=3, edges=edges, field_strength=field)


def test_tfim_uniform_coupling_produces_two_groups() -> None:
    graph = _path_graph_3(coupling=1.5, field=0.7)
    model = build_tfim_model(graph)

    assert len(model.coupling_groups) == 2
    labels = {g.label for g in model.coupling_groups}
    assert len(labels) == 2

    zz_group = next(g for g in model.coupling_groups if g.terms[0].pauli == "ZZ")
    x_group = next(g for g in model.coupling_groups if g.terms[0].pauli == "X")

    assert len(zz_group.terms) == 2
    assert {t.qubits for t in zz_group.terms} == {(0, 1), (1, 2)}
    assert all(t.weight == 1.5 for t in zz_group.terms)

    assert len(x_group.terms) == 3
    assert {t.qubits for t in x_group.terms} == {(0,), (1,), (2,)}
    assert all(t.weight == 0.7 for t in x_group.terms)


def test_tfim_heterogeneous_coupling_produces_one_group_per_label() -> None:
    edges = (
        TFIMEdge(site_i=0, site_j=1, coupling_strength=1.5, group_label="edge_01"),
        TFIMEdge(site_i=1, site_j=2, coupling_strength=2.5, group_label="edge_12"),
    )
    graph = TFIMGraph(num_sites=3, edges=edges, field_strength=0.7)
    model = build_tfim_model(graph)

    # 2 distinct edge labels + 1 field label = 3 groups.
    assert len(model.coupling_groups) == 3
    zz_groups = [g for g in model.coupling_groups if g.terms[0].pauli == "ZZ"]
    assert len(zz_groups) == 2
    weights = {g.terms[0].weight for g in zz_groups}
    assert weights == {1.5, 2.5}


def test_tfim_isolated_node_succeeds() -> None:
    graph = TFIMGraph(num_sites=1, edges=(), field_strength=0.7)
    model = build_tfim_model(graph)
    assert len(model.coupling_groups) == 1
    (field_group,) = model.coupling_groups
    assert field_group.terms[0].pauli == "X"
    assert field_group.terms[0].qubits == (0,)


def test_tfim_rejects_zero_coupling() -> None:
    graph = _path_graph_3(coupling=0.0, field=0.7)
    with pytest.raises(ZeroCouplingError):
        build_tfim_model(graph)

    graph_zero_field = _path_graph_3(coupling=1.5, field=0.0)
    with pytest.raises(ZeroCouplingError):
        build_tfim_model(graph_zero_field)
