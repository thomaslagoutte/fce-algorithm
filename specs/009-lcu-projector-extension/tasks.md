---

description: "Task list for the LCU and Projector-Observable Extension (Spec 9)"
---

# Tasks: LCU and Projector-Observable Extension

**Input**: Design documents from `/specs/009-lcu-projector-extension/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories), [research.md](./research.md)

**Tests**: Included throughout — this project's own established discipline
(Specs 5-8) writes tests first and keeps distinct claims in distinct test
functions; Spec 9 follows this unchanged.

**Guardrails acknowledged** (from the `/speckit.tasks` invocation, both
independently verified computationally before being written into a task
below — not taken on faith):

1. **The Odd-Y Conjugate Trap**: verified in-session before writing
   T014/T015 below. `Operator(U).conjugate()` (Qiskit's own ground truth)
   was compared against two hypotheses for a Pauli-rotation gate
   `e^{iπcαP}`: naively negating the angle for every term (fails for a
   term with an odd number of `Y` factors — measured diff `1.39` for a
   lone `Y`, `1.64` for `XY`) vs. the corrected rule (negate the angle
   only when `P` has an *even* `Y`-count; leave it unchanged when *odd*,
   because `P*=-P` there) — matched Qiskit's true conjugate to `0.0`
   in both the even- and odd-`Y` case, and on a 3-gate mixed sequence
   verified the SAME gate order must be kept (conjugation does not
   reverse a product, unlike the Hermitian adjoint: reversing gave a
   `0.368` diff instead of `0.0`).
2. **Negative-Weight Sign Gate**: research.md R1's diagonal `Z`-gate on
   the selector register gets its own explicit task (T007) — not folded
   silently into the selector-preparation task, so it can be tested and
   reviewed as its own, independently-necessary step.
3. **Strict Constraints**: no task below adds caching, batching,
   memoization, or any other unprofiled optimisation (Constitution §5.3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup

- [x] T001 Confirm `pyproject.toml`'s existing pins (`qiskit`) already
      satisfy Spec 9's needs (plan.md Technical Context: no new
      dependency; `SparsePauliOp` multi-term support and
      `Gate.control(...)` are already available in qiskit 2.3.1) — no
      file changes expected from this task.

---

## Phase 2: Foundational (Blocking Prerequisites)

**None required.** Both deliverables extend `circuits.py` (Spec 3)
additively; `extract.py`'s Hermiticity check and Hadamard-test readout
ancilla (Spec 4) are reused completely unmodified (research.md R2/R3).
Deliverables (a) and (b) share no new code between them (the sign gate
belongs only to (a); the conjugate-circuit rule belongs only to (b)), so
neither blocks the other's start.

**Checkpoint**: Setup complete — User Stories 1 and 2 can begin
immediately and in parallel.

---

## Phase 3: User Story 1 - Extract Fourier coefficients of a weighted sum of Pauli observables (Priority: P1) 🎯 MVP

**Goal**: `compile_observable_circuit` accepts a multi-term `SparsePauliOp`
and folds it via the verified LCU construction (research.md R1): a shared
`A(U)`/`A(U†)` pair, a selector register prepared into
`Σ_h √(|β_h|/S)|h⟩` (`S`=L1 norm), a diagonal sign-correction gate, and a
multiplexed controlled-`P_h` gate — while a single-term observable still
takes today's exact, unmodified code path.

**Independent Test**: Declare 2-4 Pauli terms with asymmetric, signed
weights; run the extended compiler; confirm the folded circuit's
post-selected amplitude matches the classical linear combination
`(1/S)Σβ_h⟨target⟩_h` to machine precision, and confirm a one-term
observable's compiled circuit is byte-for-byte unchanged from Spec 3's
existing output.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; they must FAIL before implementation.

- [x] T002 [P] [US1] Write
      `tests/unit/test_circuits_lcu_single_term_unchanged.py`: a one-term
      `SparsePauliOp` passed through the extended
      `compile_observable_circuit` produces a circuit `Operator`-equivalent
      (and, if reasonably assertable, gate-for-gate identical) to Spec 3's
      existing, unmodified single-Pauli output (FR-004) — the
      generalization must change nothing for the case that already worked.
- [x] T003 [P] [US1] Write
      `tests/unit/test_circuits_lcu_negative_weight.py`: reproduces
      research.md R1's exact fixture (`β_1=1, P_1=Z`; `β_2=-4, P_2=X`) —
      asserts the folded construction's post-selected amplitude matches
      `(1/S)(β_1 Z + β_2 X)|ψ⟩` to machine precision (`<1e-10`), AND
      includes the isolating sanity control: removing only the sign gate
      must reproduce the all-positive-weight combination instead (Guardrail
      2 — this is the dedicated negative-weight regression test).
- [x] T004 [P] [US1] Write
      `tests/unit/test_circuits_lcu_asymmetric_positive_weight.py`:
      research.md R1 Step 3's same-sign asymmetric fixture (`β_1=1,
      β_2=4`, both positive) — a SEPARATE test from T003 (distinct claim:
      the square-root formula itself, independent of the sign mechanism).
- [x] T005 [P] [US1] Write
      `tests/unit/test_circuits_lcu_equal_weight_masking.py`: an explicit
      negative control documenting that an equal-weight fixture
      (`β_1=β_2`) cannot distinguish the correct (`√`) formula from the
      incorrect (linear) one — asserts both give the identical ratio and
      identical overall scale on this fixture — recorded so this fixture
      is never mistaken for a sufficient verification on its own
      (Constitution §8.4: a known limitation, documented, not hidden).

### Implementation for User Story 1

- [x] T006 [US1] In `src/fourierlearn/circuits.py`, add the branch point:
      `compile_observable_circuit`/`_insert_observable` detect whether
      `observable.paulis` has one term (existing, untouched code path) or
      more than one (new LCU path below) — the single-term branch must
      call the exact existing code, not a refactored equivalent.
- [x] T007 [US1] Implement the selector-register preparation in
      `src/fourierlearn/circuits.py`: given weights `{β_h}`, build the
      state-prep circuit for `Σ_h √(|β_h|/S)|h⟩` (`S=Σ|β_h|`, the L1
      norm — never the L2/Euclidean norm) on `⌈log2(#terms)⌉` qubits, its
      adjoint, **and the separate diagonal sign-correction gate**
      (Guardrail 2: one gate — e.g. a product of `Z`/controlled-`Z` gates
      keyed to each `h` with `β_h<0` — applied once, anywhere between the
      preparation and its adjoint) absorbing `sign(β_h)` into the
      construction (research.md R1). Unused selector basis states (when
      `#terms` is not a power of two) MUST carry zero amplitude (FR-007).
- [x] T008 [US1] Implement the multiplexed, selector-controlled `P_h`
      gate in `src/fourierlearn/circuits.py`, reusing the existing shared
      `basis_change_gates` helper per Pauli letter (Constitution §9.4 —
      no reimplementation) — inserted at the exact position the existing
      single-observable fold gate occupies in the forward pass.
- [x] T009 [US1] Wire T006-T008 together in `compile_observable_circuit`'s
      multi-term branch: selector prep → sign gate → multiplexed fold →
      selector prep-adjoint, positioned exactly where the existing single
      fold gate sits (depends on T006, T007, T008).
- [x] T010 [US1] Reject a non-Hermitian multi-term observable using the
      exact same precondition check already applied to a single-term
      observable (FR-006) — no separately-implemented check.
- [x] T011 [US1] Run T002-T005 against T006-T010's implementation; fix
      until green. `mypy src/fourierlearn/circuits.py` clean.

**Checkpoint**: User Story 1 is fully functional and independently
testable.

---

## Phase 4: User Story 2 - Extract the probability of the original circuit's own |0⟩ outcome (Priority: P2)

**Goal**: a new entry point builds `A(U)` and an independently-constructed
`A(U*)` on two full register copies, reading off the joint `U⊗U*`
amplitude (eq. 5.52) — never decomposing `|0⟩⟨0|` into Pauli strings.

**Independent Test**: Declare a small circuit `U` containing at least one
odd-`Y`-count term and one even-`Y`-count term; build `A(U)⊗A(U*)`;
confirm the result agrees with a direct computation of
`|⟨0|U(α)|0⟩|²`'s Fourier series on a small instance, and confirm the
predicted register count matches research.md R2's formula before the
circuit is compiled.

### Tests for User Story 2 ⚠️

- [x] T012 [P] [US2] Write
      `tests/unit/test_circuits_conjugate_gate_rule.py`: for a single
      Pauli-rotation gate, `Operator(gate).conjugate()` (Qiskit's own
      ground truth) is compared against (a) naively negating the angle
      for an ODD-`Y`-count term (`P="Y"` and `P="XY"`) — MUST fail
      (assert a large, non-machine-precision diff) — and (b) the
      corrected rule (no negation for odd-`Y`, negate for even-`Y`,
      e.g. `P="YY"`) — MUST match to machine precision (`<1e-10`) for
      both parities (Guardrail 1, reproduces research.md's own executed
      verification exactly).
- [x] T013 [P] [US2] Write
      `tests/unit/test_circuits_conjugate_gate_order.py`: for a 3-gate
      mixed sequence (odd-`Y`, even-`Y`, odd-`Y` terms), building the
      conjugate circuit gate-by-gate IN THE SAME ORDER (per-gate rule
      from T012) matches `Operator(U).conjugate()` exactly (`<1e-10`),
      while reversing the gate order does NOT (assert a large diff) —
      the dedicated proof that complex conjugation preserves gate order
      (unlike the Hermitian adjoint, which reverses it).
- [x] T014 [P] [US2] Write
      `tests/unit/test_circuits_projector_register_cost.py`: for a small
      IR (2-3 qubits, 1-2 parameters), the predicted total register count
      for the `U⊗U*` construction matches research.md R2's exact formula
      `n_total = 2*n_circuit + 2*Σ_j⌈log2(4r_jL_j+1)⌉ + 2`, computed and
      logged BEFORE any circuit is compiled (Constitution §10.3).
- [x] T015 [US2] Write
      `tests/oracle/test_circuits_projector_end_to_end.py`: on a small
      circuit containing at least one odd-`Y` term, the `U⊗U*`
      construction's extracted joint amplitude matches a direct,
      independently-computed `|⟨0|U(α)|0⟩|²` Fourier series (test-only
      exact computation, matching this project's established oracle-test
      pattern) on a small instance.

### Implementation for User Story 2

- [x] T016 [US2] Implement the per-gate conjugation rule in
      `src/fourierlearn/circuits.py`: a function taking a `PauliTerm` and
      returning its conjugated counterpart — negate `coefficient` when
      `pauli.count("Y")` is even, leave unchanged when odd (Guardrail 1,
      verified in-session before this task was written).
- [x] T017 [US2] Implement the IR-level conjugate-circuit builder in
      `src/fourierlearn/circuits.py`: applies T016's rule to every
      `PauliTerm` in a `PauliEncodedCircuitIR`'s gate sequence, IN THE
      SAME ORDER (never reversed, T013) — for any `FixedGate` encountered,
      require its underlying gate matrix to be real (self-conjugate,
      e.g. `X`, `H`, as already used by Spec 8's state-prep flips) and
      raise an explicit, named error otherwise (Constitution §10.1: an
      out-of-scope case reports insufficiency, never a silently wrong
      answer) — a general complex-`FixedGate` conjugation is explicitly
      out of scope for this spec.
- [x] T018 [US2] Implement the register-cost prediction function in
      `src/fourierlearn/circuits.py` (mirroring `reference.predict_grid_cost`'s
      existing pattern): computes `n_total(U⊗U*)` per research.md R2's
      formula from an IR's own parameter structure, before any circuit is
      built.
- [x] T019 [US2] Implement the new `U⊗U*` compile entry point in
      `src/fourierlearn/circuits.py`: builds `A(U)` (reusing
      `compile_frequency_circuit` unchanged) and `A(U*)` (via T017's
      conjugate IR, also through `compile_frequency_circuit` unchanged)
      on two independent, full register copies (research.md R3) — never
      reusing or duplicating `compile_observable_circuit`'s own
      observable-folding logic, since there is no observable to fold.
- [x] T020 [US2] Run T012-T015 against T016-T019's implementation; fix
      until green. `mypy src/fourierlearn/circuits.py` clean.

**Checkpoint**: User Story 2 is fully functional and independently
testable, with no dependency on User Story 1.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T021 [P] Add module-level docstring updates to
      `src/fourierlearn/circuits.py` citing the exact thesis
      equations/figures each new function implements (eq. 5.49-5.52,
      Figures 5.5-5.6; Constitution §2.1/§2.2/§2.5 discipline), matching
      this project's established documentation style.
- [x] T022 Update `.specify/memory/extension-register.md`: mark EXT-001
      **validated** (deliverable a complete and tested) and EXT-003
      **validated** for its even/odd-`Y` `U*` construction and
      register-doubling cost (deliverable b complete and tested) — or, if
      either remains partially scoped (e.g. general `FixedGate`
      conjugation out of scope per T017), record that scope boundary
      explicitly rather than marking full validation.
- [x] T023 Run the complete project test suite (`pytest`) and `mypy`
      across all of `src/fourierlearn/` one final time; confirm the
      combined Spec 1-9 suite is fully green before requesting review.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty.
- **User Story 1 (Phase 3)** and **User Story 2 (Phase 4)**: Both depend
  only on Setup; fully independent of each other (Guardrail-mapped
  1-to-1: the sign gate is US1-only, the odd-Y rule is US2-only).
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Within Each User Story

- US1: T002-T005 (tests, parallel) → T006 → T007, T008 (can overlap once
  T006 lands) → T009 (needs T007+T008) → T010 → T011 (run).
- US2: T012, T013, T014 (tests, parallel) → T015 (needs T012's rule
  conceptually settled, but is itself a test, written before T016-T019
  exist) → T016 → T017 (needs T016) → T018 (independent of T016/T017,
  parallel-safe) → T019 (needs T017 and T018) → T020 (run).

### Parallel Opportunities

- T002, T003, T004, T005 (US1 tests, different files, no dependencies).
- T012, T013, T014 (US2 tests, different files, no dependencies).
- User Stories 1 and 2 can be staffed and completed entirely in parallel
  by different developers.
- T018 (register-cost prediction) can be implemented in parallel with
  T016/T017 (conjugation rule), since neither depends on the other —
  T019 is the join point needing both.

---

## Parallel Example: User Story 2 tests

```bash
# T012, T013, T014 touch different files and have no dependency on each other:
Task: "Write tests/unit/test_circuits_conjugate_gate_rule.py"
Task: "Write tests/unit/test_circuits_conjugate_gate_order.py"
Task: "Write tests/unit/test_circuits_projector_register_cost.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 3: User Story 1 (T002-T011).
3. **STOP and VALIDATE**: weighted-Pauli-sum extraction works, activating
   EXT-001, independently of deliverable (b).

### Incremental Delivery

1. Setup → User Story 1 (MVP: LCU weighted-sum extraction).
2. Add User Story 2 (the projector construction) → test independently →
   activates EXT-003.
3. Polish (Phase 5), including the extension-register status update.

### Parallel Team Strategy

With two developers: one completes User Story 1 (T002-T011) entirely
independently while the other completes User Story 2 (T012-T020) — no
shared files, no shared logic, per Phase 2's own "neither blocks the
other" finding.

---

## Notes

- `[P]` tasks = different files, no dependencies.
- `[Story]` label maps task to specific user story for traceability.
- Every test task is written, and confirmed to fail, before its
  corresponding implementation task — this project's own established
  discipline (Specs 5-8), continued unchanged.
- No task in this list introduces caching, batching, memoization, or any
  other unprofiled optimisation (Constitution §5.3, Guardrail 3).
- T017's `FixedGate` scope boundary (real gates only) is a deliberate,
  documented limitation (Constitution §10.1), not an oversight — a future
  spec may extend it if a complex-valued `FixedGate` is ever needed.
