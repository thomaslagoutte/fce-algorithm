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

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import _pad_to_full_width_little_endian
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm
from fourierlearn.symmetry import verify_symmetry

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
    """Constitution §11 attach point (Spec 6 FR-007; Spec 7 FR-012 adds
    `generators`): `name`/`description` are inert metadata; `generators`
    (new, additive, defaulted to `()`) is the actual algebraic content —
    one or more full-qubit-width `SparsePauliOp` operators, in the same
    little-endian qubit indexing `PhysicalModelDescription.__post_init__`
    uses for its own flattened Hamiltonian terms — that Spec 7's
    `fourierlearn.symmetry.verify_symmetry` checks against Constitution
    §11.1. A declaration with no `generators` is carried through exactly
    as Spec 6 shipped it: never evaluated, never checked."""

    name: str
    description: str = ""
    generators: tuple[SparsePauliOp, ...] = ()


def _flatten_hamiltonian_terms(
    coupling_groups: tuple[CouplingGroup, ...], num_sites: int
) -> tuple[SparsePauliOp, ...]:
    """Flatten every declared `CouplingGroupTerm` into a full-`num_sites`-
    qubit `SparsePauliOp`, reusing `pauli_pqc`'s own
    `_pad_to_full_width_little_endian` helper (Constitution §9.4) — the
    exact same little-endian padding convention this project already uses
    everywhere else a `PauliTerm`/`CouplingGroupTerm`'s own left-to-right
    `pauli[i]` acts on `qubits[i]` and must be reconciled with Qiskit's
    little-endian `SparsePauliOp` label convention (rightmost character =
    qubit 0). Getting this wrong would silently place a term's Pauli
    letters on the wrong physical qubits whenever a term does not already
    span every qubit symmetrically."""
    terms = []
    for group in coupling_groups:
        for term in group.terms:
            label = _pad_to_full_width_little_endian(term.pauli, term.qubits, num_sites)
            terms.append(SparsePauliOp(label))
    return tuple(terms)


@dataclass(frozen=True)
class PhysicalModelDescription:
    """FR-005's output: the `CouplingGroup`s Spec 2's encodings layer
    already accepts, plus the number of sites (qubits) and the optional
    §11 attach point.

    **Structural enforcement (Spec 7 FR-010, Guardrail #2)**: if
    `symmetry` carries any `generators`, `__post_init__` verifies them
    against this model's own (flattened) Hamiltonian terms immediately,
    unconditionally — this makes verification automatic for *every* code
    path that ever produces a `PhysicalModelDescription`, including direct
    instantiation, not only `build_tfim_model`'s own call site. No field
    is assigned or mutated here — this frozen dataclass's `__post_init__`
    only validates.
    """

    num_sites: int
    coupling_groups: tuple[CouplingGroup, ...]
    symmetry: SymmetryDeclaration | None = None

    def __post_init__(self) -> None:
        if self.symmetry is not None and self.symmetry.generators:
            hamiltonian_terms = _flatten_hamiltonian_terms(self.coupling_groups, self.num_sites)
            result = verify_symmetry(self.symmetry.generators, hamiltonian_terms)
            if not result.accepted:
                raise InvalidSymmetryError(
                    f"symmetry declaration {self.symmetry.name!r} failed §11.1 check(s): "
                    f"{result.failure_reason}"
                )


class InvalidSymmetryError(ValueError):
    """Raised by `PhysicalModelDescription.__post_init__` when an attached
    symmetry declaration fails any of Constitution §11.1's three
    conditions (FR-010) — before any circuit-compilation module is ever
    reached, since constructing this object is the earliest point any
    caller can reach with a symmetry-carrying model at all."""


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
