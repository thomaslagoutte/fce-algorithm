# Implementation Plan: Mixed Fixed/Encoded Trotter Frontend

**Branch**: `013-mixed-trotter-frontend` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-mixed-trotter-frontend/spec.md`

## Summary

Extend the encodings layer with a construction that interleaves
`FixedGate`-style terms (concrete, per-instance-known coupling values,
e.g. a graph's own edges) and `CouplingGroup`-style tied terms (a
genuinely unknown, shared encoded parameter) into one
`PauliEncodedCircuitIR`, per Trotter step, in the caller's declared group
order — the construction Spec 12's cross-topology regression layer needs
and currently has no way to build. Phase 0 research executed both of
this round's critical mandates before this plan was finalized: (1) a
Sign Transcription Audit of FR-011's rotation-angle formula, re-derived
and reverified from the raw Pauli matrix via `scipy.linalg.expm` —
independent of every gate library used in this feature's earlier
verification — on two fixtures, confirming FR-011's stated sign is
CORRECT (`diff=5.55e-17`/`2.22e-16`) and decisively ruling out the
flipped-sign alternative (`diff=0.84`); (2) an executed multi-parameter
generalization check (2 distinct encoded parameters + 1 fixed group, 3
qubits), confirming the interleaving logic and FR-011's formula remain
exact (`diff=7.1e-16` against an independent `scipy.expm`-built target) —
catching and correcting, along the way, a second independent bug in this
feature's own verification code (a matrix-composition-order error,
documented in research.md R2 per Constitution §8.4), not in the
construction under test.

This plan's key design decision (driving Constitution §9.4 compliance):
`trotter_frontend` becomes a thin wrapper delegating to the new, more
general `mixed_trotter_frontend` with zero fixed groups — making FR-005's
"exact reduction" guarantee structural (one interleaving implementation,
not two call paths that must be kept in sync) rather than merely
verified by a test after the fact.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `src/fourierlearn/`).

**Primary Dependencies**: Qiskit (circuit/gate construction, reused
unchanged from Spec 2's `pauli_pqc`/`trotter` modules and Spec 1's
`PauliTerm`/`FixedGate`/`PauliEncodedCircuitIR`) — no new dependency.

**Storage**: N/A (in-memory circuits/IRs, matching every prior spec).

**Testing**: pytest, `tests/unit/` — this feature's `Operator`/
`Operator.equiv` verification work (FR-003, FR-011, SC-002, SC-003) is
construction-convention testing in the same vein as the existing
`tests/unit/test_circuits_gate_convention.py`/`test_ir_gate_convention.py`
precedent, not oracle/analytic-coefficient testing (`tests/oracle/`
remains reserved for tests against `reference.py`'s frequency/coefficient
oracle, which this feature does not add new claims about).

**Target Platform**: local CPU simulation via Qiskit `Operator`
construction — no Aer execution is needed for this feature's own tests
(it verifies circuit *construction* equivalence, not measurement); matches
every prior spec's simulation-only scope.

**Project Type**: single Python library (`src/fourierlearn/`) — this
feature extends one existing module (`encodings/trotter.py`), no new
top-level directory or module.

**Performance Goals**: none newly imposed; no optimisation claim is made
by this feature (Constitution §5.3 — nothing here requires a profile,
since nothing is being sped up relative to an existing baseline).

**Constraints**: Constitution §9.4 (no duplicated call paths — see the
`trotter_frontend`-delegates-to-`mixed_trotter_frontend` design decision
above); §9.1 (encodings layer only, no reaching into `circuits`/`extract`);
§5.2 (every construction ships an equivalence proof — FR-003/FR-005/
FR-011, discharged in spec.md Clarifications and this plan's research.md);
§8.4 (negative results — two caught-and-corrected verification-code bugs —
documented, not erased).

**Scale/Scope**: small, exactly-representable fixtures (1-3 qubits, up to
2 distinct encoded parameters plus 1-2 fixed groups) — matching every
prior spec's own declared validation scale for construction-convention
checks; no claim is made about circuit-construction behavior at larger
qubit counts (spec.md Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Gate | Requirement | How this feature satisfies it |
|------|-------------|-------------------------------|
| §9.4 | Strategy selection is configuration/injection, never duplicated call paths | `trotter_frontend` is refactored to delegate to `mixed_trotter_frontend` (zero fixed groups) rather than keeping two independent interleaving implementations — FR-005's exact-reduction guarantee becomes structural |
| §9.1 | Dependencies point one way; no layer reaches around another | This feature stays entirely within the `encodings` layer (`trotter.py`, calling `pauli_pqc.build_ir` — already a same-layer dependency `trotter_frontend` has today); no new dependency on `circuits`/`extract`/`learn` |
| §5.2 | Every construction ships an equivalence proof (`Operator.equiv`) | FR-003/FR-011 (fixed-term angle formula, research.md R1), FR-005 (exact reduction, spec.md Clarifications Finding 2), research.md R2 (multi-parameter case) |
| §5.3 | No optimisation without a recorded profile | N/A — this feature makes no optimisation or performance claim |
| §2.2/§4.1 (verify before asserting) | Claims about a source/convention are verified in-session before being accepted | research.md R1 (Sign Transcription Audit, re-derived from the raw Pauli matrix, independent of every gate library used so far) and R2 (multi-parameter generalization) — both executed before this plan was finalized |
| §8.4 | Negative results documented with failure mechanism, never erased | research.md R2's "Negative result" — the second caught-and-corrected bug in this feature's own verification code (a composition-order error), recorded alongside spec.md's first (a sign error converting to `RX`/`RZZ` convention) |
| §9.5 | Physics-structure decisions (which terms/gates exist) live in the model/caller layer, not as a generic pruning heuristic in a circuit builder | The caller declares which groups are fixed vs. encoded and their concrete values/weights; `mixed_trotter_frontend` performs no term-existence decisions of its own — it only interleaves what the caller declared, exactly as `trotter_frontend` already does today for encoded-only input |

**Result**: PASS — no violations requiring justification. Complexity Tracking table below is empty by design.

## Project Structure

### Documentation (this feature)

```text
specs/013-mixed-trotter-frontend/
├── plan.md              # This file
├── research.md          # Phase 0 output — Sign Transcription Audit (R1),
│                         #   multi-parameter verification (R2)
├── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

No `data-model.md`/`contracts/`/`quickstart.md`: this feature adds two
small dataclasses and one function to an existing module, with no new
persisted entity, no new external interface contract beyond the Python
function signature itself, and no multi-step setup/validation flow beyond
what spec.md's own Acceptance Scenarios already specify — Phase 1 design
is fully captured by this plan's Project Structure and Constitution Check
sections, matching Specs 9/11's own precedent for skipping these optional
artifacts when they would only restate spec.md.

### Source Code (repository root)

```text
src/fourierlearn/encodings/trotter.py    # EXTENDED (this feature) --
    # existing: CouplingGroupTerm, CouplingGroup, _validate_inputs,
    #   trotter_frontend (Spec 2, UNCHANGED public behavior -- FR-005)
    # NEW:
    #   - FixedCouplingGroup(terms: tuple[CouplingGroupTerm, ...], value: float)
    #     -- reuses CouplingGroupTerm's existing (pauli, qubits, weight)
    #     shape for a fixed group's own terms, distinguished from
    #     CouplingGroup only by carrying one concrete `value` instead of a
    #     shared `label` (FR-001, Key Entities)
    #   - GroupSpec = CouplingGroup | FixedCouplingGroup  (type alias)
    #   - mixed_trotter_frontend(num_qubits, group_specs: Sequence[GroupSpec],
    #     tau, r, observable) -> PauliEncodedCircuitIR
    #     -- Pass 1: collects ONLY encoded (CouplingGroup) uploads, in
    #        step-major/caller-declared-group order, through
    #        `pauli_pqc.build_ir` UNCHANGED (FR-004/FR-010 -- reuses its
    #        tie-group-commutativity check and coordinate_order/PauliTerm
    #        construction exactly, never duplicated)
    #     -- Pass 2: walks the SAME nested (step, group) order again,
    #        interleaving pre-built FixedGates (FR-003/FR-011's verified
    #        angle formula) with the next already-validated PauliTerm
    #        pulled from Pass 1's build_ir output, in the caller's
    #        declared order (FR-002)
    #   - `_validate_inputs` is REUSED (not duplicated) for the shared
    #     r>0/tau!=0/non-empty-groups checks (FR-007); its per-group
    #     uniform-weight check already operates on `CouplingGroupTerm`,
    #     which `FixedCouplingGroup` also uses, so no change is needed
    #     there
    #   - `trotter_frontend` is REFACTORED to
    #     `return mixed_trotter_frontend(num_qubits, groups, tau, r, observable)`
    #     (`groups: Sequence[CouplingGroup]` already satisfies
    #     `Sequence[GroupSpec]`) -- Constitution §9.4, FR-005 made structural

tests/
├── unit/
│   ├── test_trotter.py                                # EXISTING (Spec 2) --
│   │                                                    #   unchanged; still
│   │                                                    #   passes unmodified,
│   │                                                    #   confirming the
│   │                                                    #   trotter_frontend
│   │                                                    #   refactor is
│   │                                                    #   behavior-preserving
│   ├── test_trotter_mixed.py                # NEW: FR-001/002/006/007/008 --
│   │                                          #   structural interleaving
│   │                                          #   (gate-type sequence, order),
│   │                                          #   all-fixed case, empty/r<=0/
│   │                                          #   tau==0 rejection, zero-value
│   │                                          #   fixed term acceptance
│   ├── test_trotter_mixed_gate_convention.py  # NEW: FR-003/FR-011/SC-002 --
│   │                                          #   Operator.equiv checks
│   │                                          #   reproducing research.md
│   │                                          #   R1 (isolated fixed term,
│   │                                          #   both fixtures) and R2 (2
│   │                                          #   encoded params + 1 fixed
│   │                                          #   group, 3 qubits) as
│   │                                          #   permanent regression tests
│   ├── test_trotter_mixed_exact_reduction.py  # NEW: FR-005/SC-003 --
│   │                                          #   zero-fixed-groups case
│   │                                          #   reduces exactly (== and
│   │                                          #   Operator.equiv diff=0.0)
│   │                                          #   to trotter_frontend's own
│   │                                          #   output on the same input
│   └── test_trotter_mixed_commutativity_reuse.py  # NEW: FR-004/FR-010/SC-004 --
│                                              #   a non-commuting
│                                              #   parameterized group raises
│                                              #   the IDENTICAL error
│                                              #   pauli_pqc.build_ir's own
│                                              #   check raises directly
```

**Structure Decision**: Single project (Option 1) — this feature extends
one existing module (`encodings/trotter.py`) rather than adding a new
module or top-level directory, since `mixed_trotter_frontend` is a direct
generalization of `trotter_frontend` sharing the same abstraction
(interleaved Trotter groups) and the same immediate dependency
(`pauli_pqc.build_ir`) — matching Spec 2's own module boundary rather
than Spec 12's precedent of a new module (which was new *layer*
functionality, not a same-layer extension).

## Complexity Tracking

*No violations — table intentionally empty.*
