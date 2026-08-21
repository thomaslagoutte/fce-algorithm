"""T017-T020 — the classical validation hook: build_tfim_model rejects
an invalid attached symmetry before any circuit compilation, behaves
unchanged for no/valid declarations, and — Guardrail #2 — the check
cannot be bypassed by constructing PhysicalModelDescription directly.

Also: the dedicated asymmetric-padding/endianness regression test
(critical implementation instruction #2)."""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm
from fourierlearn.models import (
    InvalidSymmetryError,
    PhysicalModelDescription,
    SymmetryDeclaration,
    TFIMEdge,
    TFIMGraph,
    build_tfim_model,
)


def _path_graph_3() -> TFIMGraph:
    edges = (
        TFIMEdge(site_i=0, site_j=1, coupling_strength=1.5),
        TFIMEdge(site_i=1, site_j=2, coupling_strength=1.5),
    )
    return TFIMGraph(num_sites=3, edges=edges, field_strength=0.7)


def test_build_tfim_model_rejects_invalid_symmetry_before_compilation() -> None:
    graph = _path_graph_3()
    # A bare Z on site 0 only: anticommutes with the X field term at site 0.
    invalid_symmetry = SymmetryDeclaration(name="bad", generators=(SparsePauliOp("IIZ"),))

    with pytest.raises(InvalidSymmetryError) as exc_info:
        build_tfim_model(graph, symmetry=invalid_symmetry)
    assert "non-annihilating" in str(exc_info.value)


def test_build_tfim_model_unchanged_for_valid_or_absent_symmetry() -> None:
    graph = _path_graph_3()

    model_no_symmetry = build_tfim_model(graph)
    assert model_no_symmetry.symmetry is None

    # Global X flip: commutes with every ZZ and X term of a TFIM model.
    valid_symmetry = SymmetryDeclaration(name="global_x_flip", generators=(SparsePauliOp("XXX"),))
    model_valid_symmetry = build_tfim_model(graph, symmetry=valid_symmetry)
    assert model_valid_symmetry.symmetry is valid_symmetry
    assert model_valid_symmetry.coupling_groups == model_no_symmetry.coupling_groups


def test_direct_physical_model_description_construction_cannot_bypass_verification() -> None:
    """Guardrail #2: instantiating PhysicalModelDescription DIRECTLY (not
    via build_tfim_model) with an invalid attached symmetry still raises
    -- the check is enforced by the entity's own __post_init__, not
    merely by one factory function a caller could route around."""
    graph = _path_graph_3()
    model = build_tfim_model(graph)
    invalid_symmetry = SymmetryDeclaration(name="bad", generators=(SparsePauliOp("IIZ"),))

    with pytest.raises(InvalidSymmetryError):
        PhysicalModelDescription(
            num_sites=model.num_sites,
            coupling_groups=model.coupling_groups,
            symmetry=invalid_symmetry,
        )


def test_physical_model_description_direct_construction_succeeds_for_valid_symmetry() -> None:
    graph = _path_graph_3()
    model = build_tfim_model(graph)

    # No declaration.
    direct_no_symmetry = PhysicalModelDescription(
        num_sites=model.num_sites, coupling_groups=model.coupling_groups
    )
    assert direct_no_symmetry.symmetry is None

    # A valid declaration.
    valid_symmetry = SymmetryDeclaration(name="global_x_flip", generators=(SparsePauliOp("XXX"),))
    direct_valid_symmetry = PhysicalModelDescription(
        num_sites=model.num_sites, coupling_groups=model.coupling_groups, symmetry=valid_symmetry
    )
    assert direct_valid_symmetry.symmetry is valid_symmetry


def test_asymmetric_padding_is_evaluated_on_the_correct_physical_qubits() -> None:
    """Critical implementation instruction #2: a dedicated test designed
    specifically to catch a padding/endianness error. A Hamiltonian term
    declared on qubit 1 ONLY, checked against a generator declared
    (already full-width) on BOTH qubits 0 and 1, with Pauli letters
    chosen so that correct little-endian padding gives 'commute' while
    an incorrectly-unreversed padding would give 'anticommute' --
    the two implementations produce genuinely different, checkable
    answers, not the same answer by coincidence.

    Term: CouplingGroupTerm(pauli="Z", qubits=(1,)) on a 2-qubit model.
    Correct padding (_pad_to_full_width_little_endian("Z", (1,), 2)) gives
    the label "ZI" (qubit1=Z, qubit0=I) -- Qiskit's little-endian
    convention, rightmost character = qubit 0.

    Generator (already full-width, as SymmetryDeclaration.generators
    always is): SparsePauliOp("ZX") -- qubit1=Z, qubit0=X.

    Correct: "ZI" vs "ZX" -> qubit0: I vs X (trivial), qubit1: Z vs Z
    (trivial) -> COMMUTE (0 anticommuting factors) -> construction
    succeeds.

    If padding were WRONG (not reversed, i.e. the term's "Z" landed on
    qubit 0 instead of qubit 1, giving "IZ" instead of "ZI"): "IZ" vs
    "ZX" -> qubit0: Z vs X (ANTICOMMUTE), qubit1: I vs Z (trivial) ->
    ANTICOMMUTE (1 anticommuting factor) -> construction would incorrectly
    raise InvalidSymmetryError. This test asserts construction SUCCEEDS,
    which only happens if the padding is correct.
    """
    coupling_groups = (
        CouplingGroup(
            label="asymmetric_term",
            terms=(CouplingGroupTerm(pauli="Z", qubits=(1,), weight=1.0),),
        ),
    )
    generator_on_both_qubits = SparsePauliOp("ZX")
    symmetry = SymmetryDeclaration(name="asymmetric_probe", generators=(generator_on_both_qubits,))

    # Must NOT raise -- an incorrect (unreversed) padding would make this
    # anticommute and raise InvalidSymmetryError instead.
    model = PhysicalModelDescription(num_sites=2, coupling_groups=coupling_groups, symmetry=symmetry)
    assert model.symmetry is symmetry
