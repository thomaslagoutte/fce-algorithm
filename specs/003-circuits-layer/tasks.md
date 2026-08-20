---

description: "Task list for Circuits Layer implementation"
---

# Tasks: Circuits Layer

**Input**: Design documents from `/specs/003-circuits-layer/`

**Prerequisites**: plan.md, spec.md, research.md (present); data-model.md, contracts/,
quickstart.md deliberately not generated for this spec — plan.md's Project Structure
scopes them out; research.md fully specifies the one new module's data shapes and
verified decisions instead.

**Tests**: Included — the feature spec itself requires dedicated sign/ordering
equivalence tests (FR-011) and oracle-backed validation with a genuinely complex
case (FR-012/FR-013), and the architect's own guardrails require every one of
research.md R9's equivalence tests (parity-fold block, the reversed-pass stress
test, the basis-change gate match, and each paired flipped-sign sanity check) to
be scheduled **before** the compiler implementation task it guards.

**Organization**: Tasks are grouped by user story (US1–US3, from spec.md), in
priority order. As with Spec 2 (and unlike Spec 1), priority order and
dependency order coincide: US1 (`compile_frequency_circuit`) is the more
primitive construction US2 (`compile_observable_circuit`) delegates to
(FR-006), and US3 (non-diagonal observables) reuses US2's own construction
unchanged (research.md R7) rather than adding new code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task names the FR(s)/SC(s) it satisfies and the specific research.md
  decision (e.g. R3, R5.4, R6) it relies on — no task in this list is
  untraceable to a verified decision.
- **Zero tasks in this list introduce caching, batching, or parameterised-
  template reuse of any kind** (Constitution §5.3, research.md R10) — enforced
  by omission throughout, and checked explicitly in Polish (T016).

## Path Conventions

Continuation of the single project from Spec 1/2: `src/fourierlearn/`,
`tests/` at repository root. New module: `src/fourierlearn/circuits.py`. No
existing Spec 1/2 file is modified by any task below — every task here only
imports from them.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new module; no story-specific logic yet.

- [x] T001 Create `src/fourierlearn/circuits.py` as an empty placeholder module
  (module docstring only — will hold `compile_frequency_circuit()`,
  `compile_observable_circuit()`, and the shared basis-change helper) —
  scaffolds **FR-001** (plan.md Project Structure, research.md R1).

**Checkpoint**: Module skeleton exists; nothing importable yet beyond the
docstring.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The one prerequisite every user story implicitly relies on: that
the Foundation Layer (Spec 1) and Encodings Layer (Spec 2) this spec builds on
are still exactly as verified, since all three stories import `frequency.py`,
`ir.py`, `contracts.py`, `reference.py`, and `encodings/` without modifying any
of them.

**⚠️ CRITICAL**: No user story's test results can be trusted if this regresses.

- [x] T002 Run the existing Spec 1 + Spec 2 suite (`pytest tests/ -v` and
  `mypy src/fourierlearn/`) and confirm it is green **before** adding any
  circuits code — this spec modifies no Spec 1/2 file, so a failure here means
  the environment, not this feature, is the problem — prerequisite for
  **FR-001** through **FR-014** (plan.md Constraints: "No existing Spec 1/2
  file is modified").

**Checkpoint**: Foundation and Encodings Layers confirmed intact. User story
work may begin, in priority order (US1 → US2 → US3 below).

---

## Phase 3: User Story 1 - Reveal a circuit's frequency spectrum without re-running it (Priority: P1) 🎯 MVP

**Goal**: `compile_frequency_circuit()` lowers a `PauliEncodedCircuitIR` into
the unconditional, non-parameterized `A(U)` circuit: one frequency-counter
register per encoded parameter (sized via Spec 1's `register_width`), one
single shared ancilla computing each encoding gate's parity and driving a
controlled increment (even parity) or decrement (odd parity), with non-`Z`
encoding gates compiled via the shared basis-change helper.

**Independent Test** (from spec.md): Compile a small, explicit
`PauliEncodedCircuitIR`, prepare the compiled circuit's exact state, and
confirm the amplitude on each frequency-register value matches the circuit's
known Fourier decomposition — independent of any observable.

### Tests for User Story 1 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T003 [US1] Write the dedicated parity-fold-block equivalence test in
  `tests/unit/test_circuits_gate_convention.py`
  (`test_parity_fold_block_matches_hand_built_target`): build the minimal
  `H`-`Z(θ)`-`H` construction (one qubit, one untied `Z` upload, a fixed `H`
  before and after), compile it, and assert its exact state matches
  research.md R3's own hand-derived, independently-verified 4-term
  superposition target (`l=+1,k=0: 0.5`; `l=+1,k=1: 0.5`; `l=-1,k=0: 0.5`;
  `l=-1,k=1: -0.5`) via `Statevector`/`Operator` equivalence, to
  floating-point precision — **FR-003**, **FR-011** (research.md R3).
- [x] T004 [US1] Write the dedicated "flipped ancilla convention would fail"
  sanity test in `tests/unit/test_circuits_gate_convention.py`
  (`test_flipped_ancilla_convention_would_fail_this_test`): construct the
  *wrong* parity assignment (ancilla=1→increment, ancilla=0→decrement — the
  candidate research.md R3 tried first and rejected) against the same `H`-
  `Z(θ)`-`H` construction, and assert it does **NOT** match T003's target —
  proving T003 is discriminating, not vacuously true regardless of the sign
  convention — **FR-003**, **FR-011** (research.md R3). *(Guardrail: paired
  flipped-sign sanity check, scheduled alongside its positive test, both
  before T008's implementation.)*
- [x] T005 [US1] Write the dedicated basis-change gate equivalence tests in
  `tests/unit/test_circuits_gate_convention.py`
  (`test_basis_change_x_matches_real_pauli_evolution_gate`,
  `test_basis_change_y_matches_real_pauli_evolution_gate`): at a concrete,
  non-trivial `alpha`, assert the `H`-sandwiched compiled `X`-encoding block
  and the `S·H`-sandwiched compiled `Y`-encoding block each match
  `Operator(PauliEvolutionGate(SparsePauliOp("X"/"Y"), time=-math.pi*alpha))`
  (Spec 1's own FR-021 sign convention) via `Operator.equiv` — **FR-005**,
  **FR-011**, **FR-014** (research.md R6). Include a paired sanity check that
  swapping the `S`/`S†` order in `W_Y` (the three rejected candidates from
  research.md R6's own sweep) does **NOT** match, proving the test
  discriminates the correct ordering.
- [x] T006 [US1] Write the core `compile_frequency_circuit` acceptance tests
  in `tests/unit/test_circuits_parity_fold.py`: (a) exactly one
  frequency-counter register per parameter, sized via `register_width`
  (Acceptance Scenario 1); (b) compiled state's amplitudes match an
  independently computed `a_{l,k}` table — built via the same per-`k`
  brute-force grid-and-FFT method research.md R3 used, not by calling the
  circuit under test a second time — for a 2-parameter circuit (Scenario 2,
  3); (c) a tied-multiplicity (`r_j>1`) parameter's every tied gate
  contributes its own increment/decrement onto that one shared register
  (Scenario 4); (d) a non-`Z` encoding gate is compiled transparently, with no
  caller-visible difference from a `Z` gate (Scenario 5) — **FR-001**..
  **FR-005**, **FR-009**, **FR-010** (research.md R2, R3, R4, R6).

### Implementation for User Story 1

- [x] T007 [US1] Implement the shared basis-change helper in
  `src/fourierlearn/circuits.py`: given a Pauli letter, return `(W, W_dagger)`
  — `(I, I)` for `'Z'` (no change needed), `(H, H)` for `'X'` (self-adjoint),
  `(S@H, H@S_dagger)` for `'Y'` (research.md R6's own verified, non-obvious
  ordering — three other candidate orderings were tried and rejected) —
  **FR-005**, **FR-014** (research.md R6) (depends on T005; makes it pass).
- [x] T008 [US1] Implement `compile_frequency_circuit()` in
  `src/fourierlearn/circuits.py`: allocate one frequency register per
  parameter via `frequency.register_width` (Spec 1, reused not redefined) and
  one single ancilla shared by the whole circuit; for each `PauliTerm` in the
  IR's `gates`, in order, apply the shared basis-change helper's `W_dagger`
  (T007) if its Pauli letter is not `'Z'`, compute the parity of its affected
  qubits onto the ancilla via a CNOT chain, apply the controlled increment
  (ancilla=0, even parity)/decrement (ancilla=1, odd parity) to that term's
  parameter's register (research.md R3's verified sign convention — the
  opposite assignment was tried and rejected), uncompute the ancilla, then
  apply `W` to undo the basis change; pass `FixedGate`s through unchanged;
  raise on zero encoded parameters — **FR-001**..**FR-005**, **FR-009**,
  **FR-010** (research.md R2, R3, R4, R6) (depends on T003, T004, T006, T007;
  makes them pass).

**Checkpoint**: `compile_frequency_circuit()` complete and independently
testable — `compile_observable_circuit()` does not exist yet, and this
construction has no dependency on it (research.md R1).

---

## Phase 4: User Story 2 - Extract a specific observable's Fourier coefficients (Priority: P2)

**Goal**: `compile_observable_circuit()` lowers a `PauliEncodedCircuitIR` and a
Hermitian Pauli-string observable into `A(U, O)`: User Story 1's forward
construction, the observable folded in via the shared basis-change helper
(`W_O · Z · W_O_dagger`, uniform for every Pauli letter including `'Z'` itself,
where `W_Z=I`), and the **literal inverse of the assembled forward circuit**
as the reversed pass.

**Independent Test** (from spec.md): Compile a small circuit with a chosen
observable, prepare the compiled circuit's exact state, post-select on the
original circuit register reading all-zero, and confirm the frequency
register's amplitudes match that observable's known Fourier coefficients.

### Tests for User Story 2 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T009 [US2] Write the dedicated reversed-pass stress-test equivalence
  check in `tests/unit/test_circuits_gate_convention.py`
  (`test_reversed_pass_equals_literal_circuit_inverse`): reproduce research.md
  R5.4's final stress construction — 3 parameters, **two** (`A` and `B`) with
  tied multiplicity 2 whose tied terms are deliberately non-adjacent in the
  gate list, one (`C`) untied, gates interleaved `[A1, B1, C, A2, B2]`, all
  sharing the single ancilla, correctly and independently sized registers —
  and assert `Operator(compiled.inverse())` is **exactly equal** (`==`, not
  merely `.equiv()`) to `Operator` of an independently constructed
  reverse-order pass built with role-swapped shift primitives — **FR-006**,
  **FR-011** (research.md R5.4, R5.5). **Keep `==`, do not weaken to
  `.equiv()`**: a global-phase concern was raised and checked directly with
  real `QuantumCircuit`/`Operator` objects at this same tied/interleaved
  scale (research.md R5.6) — the two constructions matched exactly (`==`),
  with the ~1e-14 residual confirmed to be ordinary gate-synthesis float
  noise, not a phase (the amplitude ratio at a nonzero entry is `≈1`, not
  `e^{iθ}` for `θ≠0`); `.equiv()` would pass even if a future bug introduced a
  genuine wrong phase, exactly the class of defect this test exists to catch
  (mirroring Spec 1/2's own exact, not up-to-phase, sign-convention tests).
  *(Guardrail: the reversed-pass equivalence test, scheduled before T012's
  implementation, at the stress level that actually exercises shared-ancilla
  contention — not only the minimal case.)*
- [x] T010 [US2] Write the core `compile_observable_circuit` acceptance tests
  in `tests/unit/test_circuits_observable_fold.py`: (a) the observable-folded
  circuit shares identical, identically-sized per-parameter frequency
  registers with `compile_frequency_circuit` for the same IR (Acceptance
  Scenario 1); (b) the compiled circuit's exact state, post-selected on the
  circuit register reading all-zero, matches a hand-derived observable
  Fourier-coefficient table for a small 1-parameter case (Scenario 2); (c) for
  a 2-parameter circuit, each parameter's register reflects the forward-minus-
  reverse difference, not the forward contribution alone (Scenario 3) —
  **FR-006**, **FR-007** (research.md R5, R7).
- [x] T011 [US2] Write the oracle-level validation test in
  `tests/oracle/test_circuits_validation.py`
  (`test_compile_observable_circuit_matches_reference_oracle`): build the
  genuinely-complex three-untied-upload circuit from research.md R8 (`X`,
  `X`, `Z` encoding letters with a fixed `S` gate then a fixed `T` gate
  interspersed, observable `X` — found by exhaustive search; the originally
  assumed two-upload `X`-encoding-with-`S`-gate construction from R6 turned
  out, when actually computed, to be purely real, not complex, and is NOT a
  valid fixture here), run `fourierlearn.reference.coefficients()` on the IR
  directly (Spec 1's own oracle, unmodified) and separately run
  `compile_observable_circuit` + post-selection on the identical IR and
  observable, and assert both give the identical Fourier-coefficient table
  to relative error ≤ 1e-9, with at least one non-DC coefficient's real and
  imaginary parts each individually confirmed nonzero (e.g. `l=4:
  0.1767766952966368+0.1767766952966368j`) — **FR-012**, **FR-013**
  (research.md R8; Constitution §4.1–§4.3).
  **Normalization convention (must be stated explicitly, not left implicit)**:
  the comparison MUST use the **raw** complex amplitude read directly off the
  full statevector at the post-selected register index (ancilla and circuit
  register both `|0⟩`) — the same convention research.md's own toy
  verifications (R5.2–R5.4, R6) used throughout, where the raw amplitude
  already equals `b_l` with no further scaling. The test MUST NOT renormalize
  that amplitude by dividing by the post-selection success probability (or its
  square root) before comparing — that renormalization is the natural thing
  to do if the post-selected branch were being turned back into a valid
  standalone quantum state for further use, but it is the **wrong**
  normalization for this comparison and would introduce a systematic
  magnitude mismatch against the oracle's own `b_l`, which carries no such
  factor.

### Implementation for User Story 2

- [x] T012 [US2] Implement `compile_observable_circuit()` in
  `src/fourierlearn/circuits.py`: call `compile_frequency_circuit()` (T008)
  for the forward pass; fold in the supplied observable by applying the
  shared basis-change helper's (T007) `W_dagger`, inserting the Pauli's
  `Z`-projection directly as a gate, then applying `W` — uniformly for every
  Pauli letter, including `'Z'` itself (where `W=W_dagger=I`), so there is no
  branch on "is this observable already `Z`-type" (Constitution §9.3); append
  the **literal inverse of the already-assembled forward circuit** as the
  reversed pass — do **not** implement a second, independently written
  reverse-order construction with hand-maintained role-swapped primitives —
  **FR-006**, **FR-007**, **FR-009** (research.md R5 [reversed pass], R6/R7
  [uniform observable folding via the shared helper]) (depends on T009, T010,
  T011; makes T009 and T010 pass, and T011 pass against the real oracle).

**Checkpoint**: `compile_observable_circuit()` complete and independently
testable against Spec 1's own oracle; it imports `compile_frequency_circuit`
and the shared basis-change helper and duplicates neither (research.md R1, R10).

---

## Phase 5: User Story 3 - Fold in an observable that is not already diagonal (Priority: P3)

**Goal**: Confirm that `compile_observable_circuit()` (T012) already correctly
folds in any Hermitian Pauli-string observable — `X`, `Y`, or any combination
— with **no additional implementation work**, per research.md R7's own
verified finding: T012 already routes every Pauli letter through the shared
basis-change helper uniformly (`W_Z=I` for `'Z'` is exactly the "already
diagonal, no change" case), so there is no letter-dependent special case left
to add.

**Independent Test** (from spec.md): Supply the same small circuit and target
Fourier coefficient from User Story 2's own test, once with an observable
already expressed as a `Z`-type string and once with a Hamiltonian-equivalent
observable expressed using `X`/`Y` instead, and confirm both compilations
produce identical frequency-register amplitudes.

### Tests for User Story 3 ⚠️

- [x] T013 [US3] Write the non-diagonal-observable acceptance tests in
  `tests/unit/test_circuits_observable_fold.py`: (a) a Hermitian Pauli-string
  observable that is not purely `Z`-type is folded in without being rejected
  or requiring caller-side rewriting (Acceptance Scenario 1); (b) the same
  physical observable expressed two different but equivalent ways (a `Z`-type
  string versus an `X`/`Y` string requiring the basis change) produces
  identical frequency-register amplitudes to floating-point precision, using
  the exact `X`/`Y`-observable constructions research.md R7 independently
  verified against `⟨0|U(α)†PU(α)|0⟩` ground truth (Scenario 2) — **FR-008**
  (research.md R7). **No new implementation task follows this one** — T012
  (Phase 4) already provides full, uniform coverage; this test is what proves
  that rather than assumes it.
  **Architectural spy (programmatic proof of the single-code-path requirement,
  Constitution §9.4 — numeric agreement alone cannot distinguish "reuses the
  shared helper" from "has its own, coincidentally-identical implementation")**:
  in a dedicated test (`test_compile_observable_circuit_uses_shared_basis_change_helper`),
  use `unittest.mock.patch` to wrap `circuits.basis_change_gates` (or whatever
  T007 ultimately names the shared helper) with a `MagicMock(wraps=...)` spy,
  call `compile_observable_circuit` with a non-`Z` (`X` or `Y`) observable, and
  assert the spy was actually called with that Pauli letter — not merely that
  the numeric result happens to match. This is a distinct assertion from (a)/(b)
  above: those prove the *output* is correct; this proves the *implementation
  path* is the shared one, which is what FR-014/T012's "no branch, one helper"
  design actually requires.

**Checkpoint**: All three user stories independently functional and tested;
`compile_observable_circuit` handles any single Hermitian Pauli-string
observable through one uniform code path.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-layer verification once both compilers exist. **No
performance, caching, or batching tasks** — this layer performs no circuit
*execution*, only construction, and has no throughput target (Constitution
§5.3; research.md R10).

- [x] T014 [P] Run the full suite (`pytest tests/ -v` and `mypy
  src/fourierlearn/`), Specs 1, 2, and 3 together, and confirm everything is
  green — **SC-001**–**SC-005**.
- [x] T015 [P] Audit `src/fourierlearn/circuits.py` (grep/manual review) to
  confirm `compile_observable_circuit()` contains zero duplicated
  frequency-register, parity-fold, or basis-change logic — every such
  operation goes through `compile_frequency_circuit()` and the one shared
  basis-change helper — Constitution §9.4; **FR-006**, **FR-014**.
- [x] T016 [P] Confirm, by reading `circuits.py`, that zero caching, batching,
  or parameterised-circuit-template reuse was introduced: no memoization of
  compiled circuits across calls with the same IR, no batching of multiple
  IRs into one compilation pass, no template reuse across different
  parameter/tie-group structures — every call performs the same single
  compilation pass regardless of input size — Constitution §5.3, §9.3
  (research.md R10). *(Guardrail: explicit zero-optimisation confirmation.)*
- [x] T017 [P] Cross-check that all five Success Criteria (SC-001 through
  SC-005) each have a corresponding passing test, and record the mapping
  (e.g. a short note in this file or a follow-up commit message) —
  **SC-001**–**SC-005**.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup existing — BLOCKS all user
  stories only in the sense that it must stay green.
- **US1 / `compile_frequency_circuit` (Phase 3)**: Depends on Foundational. No
  dependency on any other user story — the more primitive construction, per
  spec.md's own stated priority ordering.
- **US2 / `compile_observable_circuit` (Phase 4)**: Depends on US1
  (`compile_observable_circuit` calls `compile_frequency_circuit` — FR-006;
  T012 cannot be implemented, let alone pass T009/T010/T011, before T007/T008
  exist).
- **US3 / non-diagonal observables (Phase 5)**: Depends on US2 (T013 tests the
  capability T012 already provides — there is nothing new to build, only to
  confirm).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests are written first and MUST fail before their paired implementation
  task.
- Within US1: T003/T004 (the parity-sign positive/negative pair) and T005
  (basis-change gates) both precede T007 (the shared helper) and T008 (the
  compiler); T007 precedes T008 since T008 calls the helper T007 defines.
- Within US2: T009 (reversed-pass stress equivalence), T010 (structural
  acceptance), and T011 (oracle validation) all precede T012 (the compiler
  implementation) — T012 is expected to make all three pass at once, since
  they exercise different facets of the same construction.
- Within US3: T013 alone — no implementation task follows it, per research.md
  R7's finding that T012 already provides uniform coverage.

### Parallel Opportunities

This spec shares Spec 2's file-level constraint: multiple test tasks within
one user story often share a test file (T003/T004/T005 all write to
`tests/unit/test_circuits_gate_convention.py`; T009 also writes there; T010
and T013 share `tests/unit/test_circuits_observable_fold.py`). Marking
same-file tasks `[P]` would invite merge conflicts, so none of T003–T005,
T009–T011, or T013 carry a `[P]` marker.

- T014, T015, T016, T017 (Polish) — four independent, read-only verification
  tasks over different concerns, safely parallel.
- Test-*writing* (not implementation) for a later story does not strictly
  require an earlier story's implementation to exist yet — T009–T011 could be
  drafted while T007/T008 are still in progress, since tests are written to
  fail first regardless.

---

## Parallel Example: Polish (Phase 6)

```bash
# Launch all four Polish verification tasks together:
Task: "Run the full test suite and mypy, confirm green (SC-001-SC-005)"
Task: "Audit circuits.py for zero duplicated frequency/parity/basis-change logic (FR-006, FR-014)"
Task: "Confirm zero caching/batching/template-reuse in circuits.py (research.md R10)"
Task: "Cross-check SC-001-SC-005 each have a passing test"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2: Setup + Foundational — Spec 1/2 confirmed still green.
2. Phase 3 (US1): `compile_frequency_circuit()` complete and independently
   tested — **first genuinely useful increment**: any caller can already
   reveal a Pauli-encoded circuit's raw frequency spectrum, with no observable
   concept involved at all.
3. **STOP and VALIDATE**: Confirm US1's own tests (T003–T006) pass
   independently of `compile_observable_circuit`, which does not need to
   exist yet.

### Incremental Delivery

1. Complete Setup + Foundational → environment confirmed intact.
2. Add US1 (`compile_frequency_circuit`) → test independently (MVP!).
3. Add US2 (`compile_observable_circuit`) → test independently, including
   against Spec 1's own oracle — depends on US1's construction existing, per
   FR-006's mandated reuse.
4. Add US3 (non-diagonal observables) → test independently — this increment
   adds no new code, only the test proving US2's own construction already
   generalizes (research.md R7).
5. Phase 6: Polish — whole-layer confirmation, no new logic.

### Test-First Discipline

Every implementation task above is paired with test tasks that precede it and
are expected to fail first. This is explicit, not incidental, for every one of
research.md R9's own named equivalence tests: T003/T004 (the parity-sign
convention and its flipped-sign sanity check) and T005 (the basis-change gate
match, with its own rejected-ordering sanity check) both before T008; T009
(the reversed-pass stress test, at the multi-parameter/tied/interleaved level
that actually exercises shared-ancilla contention, not only the minimal case)
before T012. None of these are folded into a larger, harder-to-audit test
task — each stands alone so a regression in exactly one of them points at
exactly one cause.

---

## Notes

- `[Story]` label maps every user-story-phase task to US1/US2/US3 for
  traceability; Setup, Foundational, and Polish tasks carry no story label by
  convention.
- Every task cites the FR(s) or SC(s) it satisfies and the specific
  research.md decision (R1–R10, including sub-sections like R5.4/R5.5) it
  relies on — verify this before marking any task complete during
  `/speckit-implement`.
- No task in this list touches performance, caching, batching, or
  parameterised-template reuse — by design (Constitution §5.3; research.md R10
  explicitly rejected caching the basis-change helper's per-letter output
  across calls, since recomputing it is O(1) regardless and no profiled
  bottleneck justifies the added complexity).
- T013 (User Story 3) is the one task in this list with no implementation
  task following it — this is intentional, not an omission: research.md R7
  found, computationally, that `compile_observable_circuit` (T012) already
  handles every Pauli letter uniformly, so User Story 3 has nothing left to
  implement, only to verify.
