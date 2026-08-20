"""Trotter frontend — FR-006..FR-010. Reuses `pauli_pqc.build_ir` (FR-009,
Constitution §9.4) rather than reimplementing IR construction or the
tie-group commutativity check it performs.

The encoded (unknown, extracted) parameters are each coupling group's own
Hamiltonian coupling constant — not evolution time. Evolution time `tau` and
Trotter step count `r` are fixed, known classical constructor arguments
(Constitution §7.1), used only to compute each term's coefficient
`c = -h*tau/(pi*r)` (research.md R4 — the negative sign is load-bearing,
verified in-session against the actual target unitary, not assumed from an
earlier, sign-omitted candidate formula) and to determine how many times each
coupling group's tied block is repeated. Multiple groups are composed
*interleaved*: for each of the `r` Trotter steps, every declared group is
applied once, in the caller's declared order, then the next step follows
(research.md R5) — not `r` repetitions of one group followed by `r`
repetitions of the next.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import PauliEncodedCircuitIR


@dataclass(frozen=True)
class CouplingGroupTerm:
    """One Hamiltonian Pauli term within a coupling group, with its own fixed,
    known structural weight `h` — distinct from the group's unknown coupling
    value, which is bound only at circuit-evaluation time."""

    pauli: str
    qubits: tuple[int, ...]
    weight: float


@dataclass(frozen=True)
class CouplingGroup:
    """A caller-declared set of Hamiltonian Pauli terms sharing one unknown
    coupling constant. Becomes one encoded parameter (FR-007)."""

    label: str
    terms: tuple[CouplingGroupTerm, ...]


def _validate_inputs(groups: Sequence[CouplingGroup], tau: float, r: int) -> None:
    if r <= 0:
        raise ValueError(
            f"trotter_frontend requires a positive Trotter step count r, got {r}"
        )
    if math.isclose(tau, 0.0, abs_tol=1e-15) or tau == 0.0:
        raise ValueError(
            "trotter_frontend requires a nonzero evolution time tau — every "
            "derived coefficient c = -h*tau/(pi*r) collapses to exactly 0 at "
            "tau=0, which PauliTerm itself rejects, and a zero evolution time "
            "carries no information about any coupling to extract (FR-010)"
        )
    if not groups:
        raise ValueError("trotter_frontend requires at least one CouplingGroup, got none")
    for group in groups:
        if not group.terms:
            raise ValueError(f"coupling group {group.label!r} has zero Pauli terms")
        weights = {term.weight for term in group.terms}
        if len(weights) != 1:
            raise ValueError(
                f"coupling group {group.label!r} has non-uniform structural weights "
                f"{sorted(weights)} across its terms — every term within one "
                "declared coupling group MUST share the exact same weight h; "
                "'sharing a coupling' alone does not guarantee the Foundation "
                "Layer's per-parameter coefficient-uniformity requirement (FR-008)"
            )


def trotter_frontend(
    num_qubits: int,
    groups: Sequence[CouplingGroup],
    tau: float,
    r: int,
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR:
    """Lower one or more coupling groups, a fixed evolution time `tau`, and a
    fixed Trotter step count `r` into a `PauliEncodedCircuitIR`, by delegating
    to `pauli_pqc.build_ir` (FR-009) rather than reimplementing IR
    construction or tie-group commutativity checking.
    """
    _validate_inputs(groups, tau, r)

    uploads: list[PauliUpload] = []
    for step in range(r):
        for group in groups:
            for term in group.terms:
                coefficient = -term.weight * tau / (math.pi * r)
                uploads.append(
                    PauliUpload(
                        pauli=term.pauli,
                        qubits=term.qubits,
                        parameter_label=group.label,
                        tie_group=step,
                        coefficient=coefficient,
                    )
                )

    return build_ir(num_qubits=num_qubits, uploads=uploads, observable=observable)
