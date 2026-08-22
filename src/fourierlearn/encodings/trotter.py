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

Spec 013 extends this with `FixedCouplingGroup` — a group sharing one
concrete, per-instance-known coupling value (e.g. a graph's own edge weight)
rather than an unknown, shared encoded parameter — and
`mixed_trotter_frontend`, which interleaves `CouplingGroup` and
`FixedCouplingGroup` terms together, per Trotter step, in the caller's
declared order (spec.md FR-001/FR-002). `trotter_frontend` itself is now a
thin wrapper delegating to `mixed_trotter_frontend` with zero fixed groups
(spec.md FR-005, Constitution §9.4 — one interleaving implementation, not
two call paths kept in sync by convention) — its own public behavior is
unchanged (spec.md Assumptions).

The fixed-term rotation-angle formula (spec.md FR-011, verified via
`Operator.equiv` against independently hand-built targets, research.md R1):
for a fixed term with Pauli operator `P`, structural weight `w`, and concrete
known value `v`, under evolution time `tau` and step count `r`, the term's
per-step gate is exactly `e^{-i*theta*P}` with `theta = w*tau*v/r` — obtained
by calling `PauliTerm.to_gate(v)` on a `PauliTerm` whose `coefficient` is set
to the SAME formula encoded terms use, `c = -w*tau/(pi*r)`, evaluated with
the group's concrete `v` in place of a bound symbolic parameter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, GateOp, PauliEncodedCircuitIR, PauliTerm

# The parameter_index a fixed term's transient PauliTerm carries is never
# read: PauliTerm is only a vehicle for `to_gate`'s already-verified angle
# formula, and the resulting gate is immediately rewrapped as a FixedGate,
# never included in an IR's own `gates` tuple as a PauliTerm.
_FIXED_TERM_TRANSIENT_PARAMETER_INDEX = -1


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


@dataclass(frozen=True)
class FixedCouplingGroup:
    """A caller-declared set of Hamiltonian Pauli terms sharing one concrete,
    per-instance-known coupling value (e.g. a graph's own edge weight) —
    distinct from `CouplingGroup`, whose shared coupling is an unknown,
    encoded parameter (spec.md 013 FR-001, Key Entities)."""

    terms: tuple[CouplingGroupTerm, ...]
    value: float


GroupSpec = CouplingGroup | FixedCouplingGroup


def _group_identifier(group: GroupSpec) -> str:
    if isinstance(group, CouplingGroup):
        return group.label
    return f"<fixed group, value={group.value}>"


def _validate_inputs(groups: Sequence[GroupSpec], tau: float, r: int) -> None:
    if r <= 0:
        raise ValueError(
            f"trotter frontend requires a positive Trotter step count r, got {r}"
        )
    if math.isclose(tau, 0.0, abs_tol=1e-15) or tau == 0.0:
        raise ValueError(
            "trotter frontend requires a nonzero evolution time tau — every "
            "derived coefficient c = -h*tau/(pi*r) collapses to exactly 0 at "
            "tau=0, which PauliTerm itself rejects, and a zero evolution time "
            "carries no information about any coupling to extract (FR-010)"
        )
    if not groups:
        raise ValueError("trotter frontend requires at least one group, got none")
    for group in groups:
        identifier = _group_identifier(group)
        if not group.terms:
            raise ValueError(f"coupling group {identifier!r} has zero Pauli terms")
        weights = {term.weight for term in group.terms}
        if len(weights) != 1:
            raise ValueError(
                f"coupling group {identifier!r} has non-uniform structural weights "
                f"{sorted(weights)} across its terms — every term within one "
                "declared coupling group MUST share the exact same weight h; "
                "'sharing a coupling' alone does not guarantee the Foundation "
                "Layer's per-parameter coefficient-uniformity requirement (FR-008)"
            )


def mixed_trotter_frontend(
    num_qubits: int,
    group_specs: Sequence[GroupSpec],
    tau: float,
    r: int,
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR:
    """Lower a mix of `CouplingGroup` (encoded, unknown-coupling) and
    `FixedCouplingGroup` (concrete, per-instance-known-coupling) groups into
    one `PauliEncodedCircuitIR`, interleaving both kinds of term per Trotter
    step in the caller's declared group order (spec.md 013 FR-001/FR-002).

    Two passes, deliberately kept separate:

    Pass 1 collects ONLY the encoded groups' uploads, in the same step-major/
    caller-declared-group order the final interleaving uses, and routes them
    through `pauli_pqc.build_ir` completely unchanged — reusing its existing
    tie-group-commutativity check and `coordinate_order`/`PauliTerm`
    construction exactly (FR-004/FR-010; Constitution §9.4 — never
    duplicated or bypassed).

    Pass 2 walks the SAME nested `(step, group)` order a second time,
    interleaving a freshly-built `FixedGate` for each fixed-group term (using
    the verified angle formula, FR-003/FR-011) with the next already-
    validated `PauliTerm` pulled from Pass 1's `build_ir` output for each
    encoded-group term — reproducing the caller's declared order exactly.

    Calling this with zero `FixedCouplingGroup`s (every group encoded)
    reduces EXACTLY to `trotter_frontend`'s own interleaving on the same
    input (FR-005): Pass 1 alone already reproduces `trotter_frontend`'s
    original upload-collection loop verbatim, and Pass 2 then does nothing
    but re-emit Pass 1's own output in order.
    """
    _validate_inputs(group_specs, tau, r)

    encoded_uploads: list[PauliUpload] = []
    for step in range(r):
        for spec in group_specs:
            if isinstance(spec, CouplingGroup):
                for term in spec.terms:
                    coefficient = -term.weight * tau / (math.pi * r)
                    encoded_uploads.append(
                        PauliUpload(
                            pauli=term.pauli,
                            qubits=term.qubits,
                            parameter_label=spec.label,
                            tie_group=step,
                            coefficient=coefficient,
                        )
                    )

    encoded_terms: tuple[GateOp, ...] = (
        build_ir(num_qubits=num_qubits, uploads=encoded_uploads, observable=observable).gates
        if encoded_uploads
        else ()
    )
    encoded_iter = iter(encoded_terms)

    gates: list[GateOp] = []
    for step in range(r):
        for spec in group_specs:
            if isinstance(spec, FixedCouplingGroup):
                for term in spec.terms:
                    coefficient = -term.weight * tau / (math.pi * r)
                    transient_term = PauliTerm(
                        pauli=term.pauli,
                        qubits=term.qubits,
                        parameter_index=_FIXED_TERM_TRANSIENT_PARAMETER_INDEX,
                        coefficient=coefficient,
                        tie_group=0,
                    )
                    gates.append(FixedGate(gate=transient_term.to_gate(spec.value), qubits=term.qubits))
            else:
                for _ in spec.terms:
                    gates.append(next(encoded_iter))

    return PauliEncodedCircuitIR(num_qubits=num_qubits, gates=tuple(gates), observable=observable)


def trotter_frontend(
    num_qubits: int,
    groups: Sequence[CouplingGroup],
    tau: float,
    r: int,
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR:
    """Lower one or more coupling groups, a fixed evolution time `tau`, and a
    fixed Trotter step count `r` into a `PauliEncodedCircuitIR`.

    A thin wrapper around `mixed_trotter_frontend` with zero fixed groups
    (Constitution §9.4, spec.md 013 FR-005) — this function's own public
    behavior is unchanged; the interleaving logic itself now lives in one
    place only.
    """
    return mixed_trotter_frontend(num_qubits, groups, tau, r, observable)
