"""Pauli-PQC frontend — FR-001..FR-005 (reused by trotter.py, FR-009).

Lowers an ordered list of caller-declared Pauli-string uploads into a
Foundation-Layer `PauliEncodedCircuitIR`, delegating all structural validation
(tie-group size and coefficient uniformity, qubit bounds, observable
Hermiticity) entirely to `PauliEncodedCircuitIR`'s own constructor: `build_ir`
deliberately does not re-implement that logic — it already exists, correctly,
in Spec 1's IR, and duplicating it here would create two call paths enforcing
one invariant (Constitution §9.4).

Owns exactly the two checks Spec 1's IR does not perform itself: rejecting an
empty upload sequence (research.md R2 — `_validate_tying()` has nothing to
iterate over zero gates, so it does not raise) and rejecting a declared tie
group whose Pauli strings do not pairwise commute (research.md R6,
Constitution §9.5/§11.2 — whether a set of tied strings represents a valid
physical generator is a model/physics decision, not a generic structural one
the Foundation Layer's IR is agnostic to).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qiskit.quantum_info import Pauli, SparsePauliOp

from fourierlearn.frequency import coordinate_order
from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm


@dataclass(frozen=True)
class PauliUpload:
    """One caller-declared Pauli-string upload: `pauli[i]` acts on
    `qubits[i]`, tied to `parameter_label` within upload `tie_group`, with its
    own real structural `coefficient`."""

    pauli: str
    qubits: tuple[int, ...]
    parameter_label: str
    tie_group: int
    coefficient: float


def _pad_to_full_width_little_endian(pauli: str, qubits: tuple[int, ...], num_qubits: int) -> str:
    """Full-`num_qubits`-width, little-endian Pauli label for `Pauli.commutes()`.

    This project's own convention (pauli-gate-sign-convention memory) is that
    `pauli[i]` acts on `qubits[i]` in natural left-to-right order, while
    Qiskit's Pauli-label convention is little-endian (the rightmost character
    acts on qubit 0). Padding to the full register width — rather than
    `Pauli.commutes(..., qargs=...)`, which research.md R6 found raises
    `IndexError` on mismatched-width operands — lets two terms acting on
    different, possibly overlapping qubits be compared directly.
    """
    letters = ["I"] * num_qubits
    for letter, qubit in zip(pauli, qubits):
        letters[qubit] = letter
    return "".join(reversed(letters))


def _assert_tie_group_commutes(
    terms: Sequence[PauliTerm], num_qubits: int, parameter_label: str, tie_group: int
) -> None:
    """Raise unless every pair of Pauli strings in one declared tie group
    pairwise commutes (research.md R6). Tying only claims something once a
    group has two or more terms."""
    if len(terms) < 2:
        return
    padded = [
        Pauli(_pad_to_full_width_little_endian(term.pauli, term.qubits, num_qubits))
        for term in terms
    ]
    for i in range(len(padded)):
        for j in range(i + 1, len(padded)):
            if not padded[i].commutes(padded[j]):
                raise ValueError(
                    f"tie group {tie_group} for parameter {parameter_label!r} contains "
                    f"non-commuting Pauli strings ({terms[i].pauli}@{terms[i].qubits} vs "
                    f"{terms[j].pauli}@{terms[j].qubits}) — tied terms must represent one "
                    "physically valid generator, a sum of commuting Pauli strings (§11.2); "
                    "sequential application of non-commuting 'tied' terms does not equal "
                    "exponentiating their sum"
                )


def build_ir(
    num_qubits: int,
    uploads: Sequence[PauliUpload],
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR:
    """Lower an ordered list of `PauliUpload`s into a `PauliEncodedCircuitIR`.

    Maps each distinct `parameter_label` to a canonical integer
    `parameter_index` via `frequency.coordinate_order` — the same function
    `PauliEncodedCircuitIR.parameters()` itself uses, so no independent
    ordering rule is invented here.
    """
    if not uploads:
        raise ValueError(
            "build_ir requires at least one PauliUpload — an empty upload "
            "sequence would silently return a zero-parameter IR (FR-004)"
        )

    distinct_labels = coordinate_order(list({upload.parameter_label for upload in uploads}))
    label_to_index = {label: index for index, label in enumerate(distinct_labels)}
    index_to_label = {index: label for label, index in label_to_index.items()}

    terms = tuple(
        PauliTerm(
            pauli=upload.pauli,
            qubits=upload.qubits,
            parameter_index=label_to_index[upload.parameter_label],
            coefficient=upload.coefficient,
            tie_group=upload.tie_group,
        )
        for upload in uploads
    )

    groups: dict[tuple[int, int], list[PauliTerm]] = {}
    for term in terms:
        groups.setdefault((term.parameter_index, term.tie_group), []).append(term)
    for (parameter_index, tie_group), group_terms in groups.items():
        _assert_tie_group_commutes(
            group_terms, num_qubits, index_to_label[parameter_index], tie_group
        )

    return PauliEncodedCircuitIR(num_qubits=num_qubits, gates=terms, observable=observable)
