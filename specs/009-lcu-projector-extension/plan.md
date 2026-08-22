# Implementation Plan: LCU and Projector-Observable Extension

**Branch**: `009-lcu-projector-extension` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-lcu-projector-extension/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Two extensions to Spec 3's `circuits.py`, neither duplicating its existing
single-Pauli path:

- **Deliverable (a)**: `compile_observable_circuit` gains an internal
  branch for a multi-term `SparsePauliOp`. It prepares an LCU selector
  register into `Σ_h √(|β_h|/S)|h⟩` (`S` = L1 norm — research.md R1,
  corrected from spec.md's Clarifications after independently re-deriving
  and numerically confirming the "square root trap"), applies a diagonal
  sign-correction gate absorbing each `sign(β_h)` into its own branch, then
  the multiplexed, selector-controlled `P_h` at the exact position the
  existing single-observable fold occupies, then un-prepares. A one-term
  observable takes the existing, completely unmodified code path (Critical
  Mandate 1).
- **Deliverable (b)**: a new entry point builds `A(U)` and an
  independently-constructed `A(U*)` on two full, independent register
  copies (research.md R2: `n_total = 2*n_circuit +
  2*Σ_j⌈log2(4r_jL_j+1)⌉ + 2`), reading off the joint `U⊗U*` amplitude —
  never attempting a Pauli decomposition of `|0⟩⟨0|` (spec.md
  Clarifications: exponential, the wrong tool).

Both of this round's critical mandates were executed, not promised
(research.md R1/R2):

1. **R1**: a concrete 2-qubit circuit (`P_1=Z, P_2=X`, `β_1=1, β_2=-4`)
   built and verified to machine precision (diff `1.1e-16`) using
   `c_h=√(|β_h|/S)` plus a diagonal sign gate on the selector register —
   with an isolating sanity control (removing only the sign gate
   reproduces the all-positive-weight combination, differing from the
   correct target by `1.46`) and a re-confirmation, on this same fixture,
   of why an equal-weight test would have masked the original bug
   (correct and incorrect formulas give *identical* ratio and *identical*
   scale at `β_1=β_2`).
2. **R2**: the exact integer qubit-cost formula for `U⊗U*` derived from
   Spec 3's own existing `_build_registers` structure and verified on a
   worked example (`n_circuit=2, d=2` params → `n_single=11`,
   `n_total=22`, `+1` for the unchanged, un-doubled Hadamard-test readout
   ancilla → `23`) — explicitly contrasted with deliverable (a)'s own
   additive-only `⌈log2(#terms)⌉` overhead, so the two deliverables' costs
   are never conflated.
3. No optimisation anywhere in this design (§5.3, research.md R4).

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-8; unchanged).

**Primary Dependencies**: `qiskit` 2.3.1 (`SparsePauliOp` multi-term
support, `QuantumCircuit.append(...).control(...)` for the multiplexed
fold gate). No new dependency.

**Storage**: N/A — pure circuit-construction and in-memory computation,
as Specs 1-8.

**Testing**: `pytest`. research.md R1's negative-weight/asymmetric-weight
fixture and its sign-gate isolation control become permanent, named
tests, kept separate from a same-sign asymmetric test and from a
single-term regression test (Critical Mandate 1) — distinct claims,
distinct tests, this project's established discipline.

**Target Platform**: Developer workstation and CI runner — unchanged.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`) — extends `circuits.py`; no new top-level module is
strictly required, though the LCU selector-preparation and multiplexed-
fold logic may be factored into private helper functions within
`circuits.py` (a `/speckit-tasks`-level file-layout decision).

**Performance Goals**: None (§5.3 — research.md R4: no caching, batching,
or memoization; the LCU selector and doubled `U⊗U*` registers are
structural costs of the algorithms, not optimisation targets).

**Constraints**: A single-term observable passed through the generalized
`compile_observable_circuit` MUST produce a circuit identical to today's
unmodified output (FR-004) — verified directly, not argued. The LCU
selector preparation MUST use `c_h=√(|β_h|/S)` with `S` the L1 norm
(FR-003, research.md R1) — never the literal `β_h/‖β‖` (L2 norm) reading
of eq. 5.51, which research.md R1 confirms is quadratic-in-`β_h`, wrong.
The `U⊗U*` construction's doubled register cost (FR-008, research.md R2)
MUST be predicted and logged before being paid (Constitution §10.3),
mirroring `reference.py`'s existing `predict_grid_cost` pattern.

**Scale/Scope**: Small, explicit, hand-constructed multi-term observables
(2-4 Pauli terms) and small circuits (a handful of qubits) — matching
spec.md's own Assumptions; no production-scale observable or circuit is
targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Reuse, not duplication | Critical Mandate 1; FR-004 | **PASS** | research.md R3: single entry point retained; single-term path untouched; no parallel compiler. Byte-for-byte equivalence is a required, verified test (T-level), not argued. |
| LCU amplitude correctness | FR-003; Clarifications 2026-08-21 | **PASS** | research.md R1: `c_h=√(\|β_h\|/S)` + sign gate verified to machine precision, including a negative weight, with an isolating sanity control. |
| Non-degenerate verification fixture | Assumptions; Clarifications 2026-08-21 | **PASS** | research.md R1 Step 3: equal-weight masking re-confirmed on the same concrete fixture before being trusted. |
| Honest scope — register doubling | FR-008; Constitution §10.3 | **PASS** | research.md R2: exact formula derived from the existing, unmodified `_build_registers` structure, verified on a worked example, explicitly contrasted with deliverable (a)'s additive-only cost. |
| Exponential-decomposition trap avoided | FR-008; Clarifications | **PASS** | spec.md's own Clarifications section; this plan does not revisit it, only relies on it. |
| Optimisation discipline | §5.3 | **PASS** | research.md R4. |
| Verification before design acceptance | Constitution §4.1/§5.2; FR-011 | **PARTIAL — one item explicitly deferred** | R1/R2 executed. The `U*` construction for odd-`Y`-count Pauli terms (spec.md Assumptions) is NOT resolved by this plan's own critical mandates and is carried forward as a named, explicit `/speckit-tasks` item, not silently assumed. |

No violations requiring Complexity Tracking — the one open item above is
a scheduled follow-up, not a constitutional violation.

### Post-design re-check (after Phase 0 research)

Both of this round's critical mandates were resolved by execution: the
negative-weight sign-absorption mechanism (R1) and the exact `U⊗U*`
qubit-cost formula (R2). The one explicitly carried-forward open item —
verifying `U*`'s construction for a Pauli string with an odd number of
`Y` factors — does not block `/speckit-tasks` from proceeding with
deliverable (a) and with deliverable (b)'s even-`Y`-only case; it must,
however, be scheduled as its own dedicated task with its own dedicated
verification before deliverable (b) is considered complete for a general
observable.

## Project Structure

### Documentation (this feature)

```text
specs/009-lcu-projector-extension/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2-8's own
precedent.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py            # Spec 1 — unchanged; register_width reused
    │                             verbatim for the R2 qubit-cost formula
    ├── ir.py                    # Spec 1 — unchanged
    ├── reference.py             # Spec 1 — unchanged; not imported by this feature
    ├── encodings/               # Spec 2 — unchanged
    ├── circuits.py              # Spec 3 — MODIFIED: compile_observable_circuit
    │                             gains the multi-term LCU branch (deliverable a);
    │                             a new entry point for the U⊗U* projector
    │                             construction is added (deliverable b);
    │                             _insert_observable's existing single-term
    │                             path is untouched
    ├── extract.py               # Spec 4 — unchanged; Hermiticity precondition
    │                             (FR-006) and Hadamard-test readout ancilla
    │                             reused unmodified for both deliverables
    ├── learn.py                 # Spec 5 — unchanged
    ├── models.py, symmetry.py   # Specs 6/7 — unchanged
    └── z2lgt.py, containment.py,
        _containment_oracle_check.py  # Spec 8 — unchanged

tests/
└── unit/
    ├── test_circuits_lcu_single_term_unchanged.py  # FR-004: byte-for-byte
    │                                                  regression vs. today's
    │                                                  single-Pauli output
    ├── test_circuits_lcu_negative_weight.py          # research.md R1: the
    │                                                    signed, asymmetric
    │                                                    fixture (beta1=1,
    │                                                    beta2=-4), plus the
    │                                                    sign-gate isolation
    │                                                    control
    ├── test_circuits_lcu_asymmetric_positive_weight.py  # research.md R1
    │                                                       Step 3: same-sign
    │                                                       asymmetric weights,
    │                                                       kept SEPARATE from
    │                                                       the negative-weight
    │                                                       test (distinct claims)
    ├── test_circuits_lcu_equal_weight_masking.py     # documents, as an
    │                                                    explicit negative
    │                                                    control, that an
    │                                                    equal-weight fixture
    │                                                    cannot distinguish
    │                                                    correct from wrong
    │                                                    (never used as the
    │                                                    ONLY verification)
    └── test_circuits_projector_register_cost.py      # research.md R2: the
                                                          n_total(U⊗U*) formula,
                                                          predicted and logged
                                                          before being paid
```

**Structure Decision**: one modified module (`circuits.py`), extended
additively — no new top-level module, since both deliverables are
circuit-*compilation* concerns squarely inside Spec 3's existing scope.
`extract.py`'s Hermiticity check and Hadamard-test readout are reused
completely unmodified for both deliverables, confirmed by direct
inspection in research.md R2 (the readout ancilla is `+1`, never
doubled).

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted. The one
open item (odd-`Y` `U*` construction) is a scheduled, explicitly-named
follow-up task, not a violation requiring justification.*
