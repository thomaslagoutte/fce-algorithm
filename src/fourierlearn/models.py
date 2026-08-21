"""Models layer — FR-005..FR-008: translate a classical-input, domain-
vocabulary physical-model description (first: the Transverse-Field Ising
Model, TFIM) into Spec 2's own `CouplingGroup` input shape, plus the
additive, always-inert Constitution §11 attach point (`symmetry`,
FR-007) — no §11 equivariance checking happens here (User Story 3).

`H = -J * sum_{(i,j) in E} Z_i Z_j - h * sum_i X_i` for the common
uniform-coupling case; a caller may instead assign a distinct
`group_label` per edge (or per field term) for a heterogeneous
(random-bond) variant — one `CouplingGroup` per distinct resulting label
(research.md R5).
"""

from __future__ import annotations

from dataclasses import dataclass

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm

_DEFAULT_EDGE_LABEL = "__default_zz_coupling__"
_DEFAULT_FIELD_LABEL = "__default_x_field__"


@dataclass(frozen=True)
class TFIMEdge:
    """One `ZZ` coupling edge. `group_label=None` defaults to the shared
    uniform-coupling group (`_DEFAULT_EDGE_LABEL`); an explicit label
    assigns this edge to its own (or another explicitly shared) group."""

    site_i: int
    site_j: int
    coupling_strength: float
    group_label: str | None = None


@dataclass(frozen=True)
class TFIMGraph:
    """A classical-input, domain-vocabulary TFIM description: sites,
    edges, and one transverse-field strength (FR-005)."""

    num_sites: int
    edges: tuple[TFIMEdge, ...]
    field_strength: float
    field_group_label: str | None = None


@dataclass(frozen=True)
class SymmetryDeclaration:
    """Constitution §11 attach point (FR-007, User Story 3): inert data
    naming a symmetry a future spec's §11.1 equivariance check would
    evaluate. Never evaluated by this feature."""

    name: str
    description: str = ""


@dataclass(frozen=True)
class PhysicalModelDescription:
    """FR-005's output: the `CouplingGroup`s Spec 2's encodings layer
    already accepts, plus the number of sites (qubits) and the optional
    §11 attach point."""

    num_sites: int
    coupling_groups: tuple[CouplingGroup, ...]
    symmetry: SymmetryDeclaration | None = None


class ZeroCouplingError(ValueError):
    """Raised when a declared coupling or field strength is exactly zero
    (FR-006) — rejected explicitly here, rather than silently omitted or
    passed through to a less specific downstream rejection."""


class InconsistentGroupLabelError(ValueError):
    """Raised when two terms sharing one group label declare different
    coupling strengths — a group's terms must share exactly one physical,
    to-be-learned constant (Constitution's own `CouplingGroup` invariant,
    `encodings/trotter.py`'s `_validate_inputs`); this feature checks it
    here for a clearer, more specific error than that downstream check
    would give."""


def _group_by_label(
    labeled_strengths: list[tuple[str, float]],
) -> dict[str, float]:
    strength_by_label: dict[str, float] = {}
    for label, strength in labeled_strengths:
        if strength == 0.0:
            raise ZeroCouplingError(
                f"a coupling/field strength of exactly zero was declared for group "
                f"{label!r} — a zero coupling has no well-defined period and cannot "
                "be represented as a learnable parameter"
            )
        if label in strength_by_label and strength_by_label[label] != strength:
            raise InconsistentGroupLabelError(
                f"group {label!r} was declared with inconsistent strengths "
                f"({strength_by_label[label]!r} vs. {strength!r}) — every term "
                "sharing one group label must share the exact same physical constant"
            )
        strength_by_label[label] = strength
    return strength_by_label


def build_tfim_model(
    graph: TFIMGraph, symmetry: SymmetryDeclaration | None = None
) -> PhysicalModelDescription:
    """FR-005/FR-006/FR-007: build the `CouplingGroup`s for a TFIM
    instance. Edges/field terms without an explicit `group_label` default
    to one shared label each (the uniform-coupling case); explicit labels
    produce one `CouplingGroup` per distinct label (research.md R5). An
    isolated site (no edges) is a valid instance (Edge Cases)."""
    edge_labeled_strengths = [
        (edge.group_label if edge.group_label is not None else _DEFAULT_EDGE_LABEL, edge.coupling_strength)
        for edge in graph.edges
    ]
    field_label = graph.field_group_label if graph.field_group_label is not None else _DEFAULT_FIELD_LABEL
    all_labeled_strengths = edge_labeled_strengths + [(field_label, graph.field_strength)]
    strength_by_label = _group_by_label(all_labeled_strengths)

    edges_by_label: dict[str, list[TFIMEdge]] = {}
    for edge in graph.edges:
        label = edge.group_label if edge.group_label is not None else _DEFAULT_EDGE_LABEL
        edges_by_label.setdefault(label, []).append(edge)

    coupling_groups = []
    for label, edges in edges_by_label.items():
        terms = tuple(
            CouplingGroupTerm(pauli="ZZ", qubits=(edge.site_i, edge.site_j), weight=strength_by_label[label])
            for edge in edges
        )
        coupling_groups.append(CouplingGroup(label=label, terms=terms))

    field_terms = tuple(
        CouplingGroupTerm(pauli="X", qubits=(site,), weight=strength_by_label[field_label])
        for site in range(graph.num_sites)
    )
    coupling_groups.append(CouplingGroup(label=field_label, terms=field_terms))

    return PhysicalModelDescription(
        num_sites=graph.num_sites,
        coupling_groups=tuple(coupling_groups),
        symmetry=symmetry,
    )
