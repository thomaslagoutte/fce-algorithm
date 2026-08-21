---

description: "Task list for Extract Layer implementation"
---

# Tasks: Extract Layer

**Input**: Design documents from `/specs/004-extract-layer/`

**Prerequisites**: plan.md, spec.md, research.md (present); data-model.md, contracts/,
quickstart.md deliberately not generated for this spec — plan.md's Project Structure
scopes them out; research.md fully specifies the one new module's data shapes and
verified decisions instead.

**Tests**: Included — the feature spec itself requires dedicated oracle-agreement,
conjugate-symmetry, and non-degeneracy checks (FR-009/FR-010, Constitution §4.1-§4.4),
and the architect's own guardrails require R3 (exact-limit oracle match), R4
(conjugate symmetry on the estimator's own output), and the fixture's
non-degeneracy to each be their own dedicated, separately-named test task — never
folded into one generic "matches oracle" test.

**Organization**: Tasks are grouped by user story (US1–US3, from spec.md), in
priority order. As with Specs 2/3, priority order and dependency order coincide:
US1 (`estimate_coefficient`) is the primitive US2 (`extract_coefficients`) is
built from, and US3 (the statistical convergence test) validates both without
adding new production code, exactly mirroring Spec 3's own US3 (no separate
implementation task follows it).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task names the FR(s)/SC(s) it satisfies and the specific research.md
  decision (R1–R9) it relies on — no task in this list is untraceable to a
  verified decision.
- **Zero tasks in this list introduce caching, batching, or parameterised-
  template reuse of any kind** (Constitution §5.3, research.md R9) — enforced
  by omission throughout, and checked explicitly in Polish (T017).

## Path Conventions

Continuation of the single project from Specs 1-3: `src/fourierlearn/`,
`tests/` at repository root. New module: `src/fourierlearn/extract.py`. No
existing Spec 1-3 file is modified by any task below — every task here only
imports from them.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new module; no story-specific logic yet.

- [x] T001 Create `src/fourierlearn/extract.py` as an empty placeholder module
  (module docstring only — will hold `estimate_coefficient()`,
  `extract_coefficients()`, and `ShotBudgetExceeded`) — scaffolds **FR-001**
  (plan.md Project Structure, research.md R1).

**Checkpoint**: Module skeleton exists; nothing importable yet beyond the
docstring.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The one prerequisite every user story implicitly relies on: that
the Foundation Layer (Spec 1), Encodings Layer (Spec 2), and Circuits Layer
(Spec 3) this spec builds on are still exactly as verified, since all three
stories import `circuits.py` (and, for tests only, `reference.py`) without
modifying any of them.

**⚠️ CRITICAL**: No user story's test results can be trusted if this regresses.

- [x] T002 Run the existing Spec 1 + Spec 2 + Spec 3 suite (`pytest tests/ -v`
  and `mypy src/fourierlearn/`) and confirm it is green **before** adding any
  extract code — this spec modifies no Spec 1-3 file, so a failure here means
  the environment, not this feature, is the problem — prerequisite for
  **FR-001** through **FR-012** (plan.md Constraints: "No existing Spec 1-3
  file is modified").

**Checkpoint**: Foundation, Encodings, and Circuits Layers confirmed intact.
User story work may begin, in priority order (US1 → US2 → US3 below).

---

## Phase 3: User Story 1 - Estimate one Fourier coefficient from finite shots (Priority: P1) 🎯 MVP

**Goal**: `estimate_coefficient()` wraps Spec 3's compiled `A(U,O)` circuit
with a Hadamard-test ancilla for one target frequency `l` (reusing Circuits
Layer's own `_increment_circuit` to build `V_l`, not reimplementing it),
executes it with a caller-specified finite shot count via
`AerSimulator.run()` + `get_counts()`, and returns the estimated coefficient
together with the exact shot count used.

**Independent Test** (from spec.md): Compile a small circuit whose Fourier
coefficients are already known (Spec 1's exact oracle), request one specific
frequency with a generous shot count, and confirm the returned estimate is
close to the known value by an amount consistent with that shot count's own
statistical uncertainty.

### Tests for User Story 1 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T003 [US1] Write the dedicated exact-limit oracle-match test in
  `tests/unit/test_extract_hadamard_test.py`
  (`test_hadamard_test_exact_limit_matches_oracle`): build the Hadamard-test
  circuit (no measurement) for every representable frequency of the mandated
  Spec 3 research.md R8 fixture (`X, X, Z` untied uploads, `S` then `T` fixed
  gates, observable `X` — reused unchanged, per **FR-010**, not re-derived),
  evaluate each via `Statevector` (research/test-only tool, never used in
  `extract.py` itself) as `P(ancilla=0) - P(ancilla=1)` for both the real-part
  and imaginary-part circuit variants, and assert the result matches
  `fourierlearn.reference.coefficients()`'s own value for that frequency to
  within `1e-9` for every frequency — **FR-003**, **FR-010** (research.md R2,
  R3: the exact `~1e-14`-agreement table). *(Guardrail: R3's own dedicated
  test, not folded into a generic "matches oracle" test.)*
- [x] T004 [US1] Write the dedicated conjugate-symmetry test on the
  estimator's own output in `tests/unit/test_extract_hadamard_test.py`
  (`test_hadamard_test_conjugate_symmetry_on_own_output`): using the same
  exact-limit (no-measurement, `Statevector`-evaluated) construction as T003,
  for every positive frequency `l` in the mandated fixture's domain, assert
  the estimator's own raw output at `+l` is the *exact* complex conjugate of
  its own raw output at the register-decoded `-l` — **not** a comparison
  against the oracle's `b_{-l}` value, but the estimator's two outputs
  compared directly against each other — **FR-006** (research.md R4: the
  specific check `/speckit-clarify` mandated before FR-006's shortcut may be
  relied upon). *(Guardrail: R4's own dedicated test, distinct from T003.)*
- [x] T005 [US1] Write the dedicated non-degeneracy assertion test in
  `tests/unit/test_extract_hadamard_test.py`
  (`test_mandated_fixture_is_genuinely_complex_in_this_suite`): assert, using
  the mandated fixture's own exact oracle values (not re-searching for a new
  fixture), that at least one non-DC frequency has both its real and
  imaginary parts individually greater than a stated non-triviality
  threshold (e.g. `1e-2`) — confirming, independently in *this* spec's own
  suite, that reusing Spec 3's fixture here still produces genuine complexity
  rather than silently degrading to a real-only case in a new context —
  **FR-010** (research.md R3; Constitution §4.3). *(Guardrail: a third,
  separately-named test — not merged with T003 or T004.)*
- [x] T006 [US1] Write the core `estimate_coefficient` acceptance tests in
  `tests/unit/test_extract_hadamard_test.py`: (a) a request with a specified,
  finite, positive shot count returns a complex estimate together with the
  exact shot count used (Acceptance Scenario 1); (b) a much larger shot count
  produces an estimate no less accurate against the oracle than a smaller one
  (Scenario 2); (c) a shot count of zero or negative raises (Scenario 3); (d)
  two runs with the same shot count but different seeds both pass the same
  Hoeffding-derived tolerance from research.md R6 (Scenario 4) — **FR-001**,
  **FR-002**, **FR-004**, **FR-008** (research.md R5, R6).

### Implementation for User Story 1

- [x] T007 [US1] Implement the `V_l`/`V_l†` construction and the Hadamard-test
  circuit builder as private helpers in `src/fourierlearn/extract.py`: `V_l`
  is `|l|` repetitions of Circuits Layer's own `_increment_circuit` (or its
  `.inverse()` for negative `l`) — reused unchanged, not reimplemented
  (Constitution §9.4); the Hadamard-test circuit wraps a fresh ancilla, `H`,
  controlled-`A(U,O)` (the caller's compiled circuit, controlled by the fresh
  ancilla), controlled-`V_l†` on the frequency register(s), an `S†` before the
  final `H` for the imaginary-part variant only, then measurement — **FR-003**
  (research.md R2) (depends on T003, T004, T005; makes them pass).
- [x] T008 [US1] Implement the public `estimate_coefficient()` function in
  `src/fourierlearn/extract.py`: `transpile()` the real-part and
  imaginary-part Hadamard-test circuits (T007) for an `AerSimulator` instance
  before every `.run()` call (research.md R5 — required, not optional: Aer
  rejects an un-transpiled controlled custom-gate circuit), run each with the
  caller's specified finite shot count, convert `get_counts()` output via
  `P(0) - P(1)` into `Re`/`Im`, and return the complex estimate plus the exact
  shot count used; raise on a zero/negative shot count or an unrepresentable
  frequency (FR-008). **Seed-determinism contract (MUST be stated explicitly
  in the public docstring, not left as an internal implementation detail)**:
  when a caller supplies `seed`, the real-part circuit MUST be run with
  `seed_simulator=seed` and the imaginary-part circuit with
  `seed_simulator=seed + 1` — two *different* seeds are required so the two
  circuits' shot noise is statistically independent of each other (reusing
  the same seed for both would make the real and imaginary sampling errors
  spuriously correlated) — and this exact offset-by-one convention is a
  documented part of the function's public contract, not an internal detail
  callers cannot rely on — **FR-001**, **FR-002**, **FR-004** (research.md
  R5) (depends on T007; makes T006 pass).

**Checkpoint**: `estimate_coefficient()` complete and independently testable
— `extract_coefficients()` does not exist yet, and this primitive has no
dependency on it (research.md R1).

---

## Phase 4: User Story 2 - Extract the full Fourier coefficient set efficiently (Priority: P2)

**Goal**: `extract_coefficients()` builds the complete frequency-to-coefficient
mapping from `estimate_coefficient()` (User Story 1), directly estimating
only the non-mirrored half of the representable frequencies plus the
always-direct DC term, and deriving the remaining half by complex
conjugation — after first confirming the folded observable is Hermitian.

**Independent Test** (from spec.md): Compile a small circuit, request the
full coefficient set, and confirm every representable frequency is present
and that the number of circuit executions performed reflects only the
non-mirrored half being independently estimated.

### Tests for User Story 2 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T009 [US2] Write the core `extract_coefficients` acceptance tests in
  `tests/unit/test_extract_full_coefficients.py`: (a) the result contains
  exactly one estimate for every representable frequency, including DC
  (Acceptance Scenario 1); (b) the number of circuit executions actually
  performed (via a call-counting spy on the underlying execution primitive)
  reflects estimating only the non-mirrored half directly, deriving the rest
  by conjugation, not estimating every frequency independently (Scenario 2)
  — **FR-005**, **FR-006** (research.md R2, R4).
- [x] T010 [US2] Write the dedicated DC-Hermiticity load-bearing test in
  `tests/unit/test_extract_full_coefficients.py`
  (`test_dc_coefficient_is_real_load_bearing`): for every
  full-coefficient-set extraction this test file exercises (not only a single
  fixture), assert the DC (`l=0`/all-zero-tuple) coefficient's imaginary part
  is within that run's own Hoeffding tolerance (research.md R6) of zero — a
  strict, load-bearing assertion, not an optional or informational check —
  **FR-012** (research.md R8; Constitution §7.6). *(Guardrail: elevated per
  Clarifications 2026-08-20 from a one-off note to a standing per-run test
  requirement.)*
- [x] T011 [US2] Write the cost-budget guard tests in
  `tests/unit/test_extract_full_coefficients.py`: (a) a predicted execution
  cost (circuits × shots) exceeding a configured budget raises
  `ShotBudgetExceeded` unless `confirm=True` is passed, mirroring Spec 1's
  `CostBudgetExceeded`/`confirm=True` interface style exactly, defined
  locally in `extract.py` (not imported from `fourierlearn.reference`, which
  FR-001 already forbids importing here); (b) a request for a frequency the
  compiled circuit's frequency register cannot represent raises rather than
  returning a meaningless result — **FR-007**, **FR-008** (research.md R7).
- [x] T012 [US2] Write the non-Hermitian-observable rejection test in
  `tests/unit/test_extract_full_coefficients.py`: constructing a compiled
  circuit whose folded observable is not Hermitian (a caller error the
  Foundation Layer would already reject upstream — construct this directly
  against `extract_coefficients`'s own Hermiticity check, not by bypassing
  Spec 1's own construction-time validation) must raise before the
  conjugate-symmetry shortcut is ever applied — **FR-006** (Acceptance
  Scenario 3; Constitution §7.6).

### Implementation for User Story 2

- [x] T013 [US2] Implement `ShotBudgetExceeded(RuntimeError)` and the
  predicted-cost check in `src/fourierlearn/extract.py`: compute total
  predicted circuit executions × shots, log it, and raise
  `ShotBudgetExceeded` unless `confirm=True` — **FR-007** (research.md R7)
  (depends on T011; makes it pass).
- [x] T014 [US2] Implement the public `extract_coefficients()` function in
  `src/fourierlearn/extract.py`: confirm the compiled circuit's folded
  observable is Hermitian before relying on the conjugate-symmetry shortcut
  (raise otherwise, FR-006); call `estimate_coefficient()` (T008) directly
  once per non-mirrored frequency plus once for DC, deriving each mirrored
  partner by complex conjugation rather than a second circuit execution;
  invoke `ShotBudgetExceeded`'s check (T013) before running anything.
  **Opaque execution interface (MUST be stated explicitly, not left
  implicit)**: the function's public signature (compiled circuit, shot
  count, seed, budget, confirm) MUST expose none of `AerSimulator`'s own
  `run()`/`transpile()`/`get_counts()` details — no backend object, no raw
  counts dictionary, no per-circuit seed list — so that a future internal
  refactor introducing batched multi-circuit `sim.run()` submission (an
  optimisation explicitly NOT implemented in this spec, research.md R9)
  could be made without changing this function's calling contract at all —
  **FR-005**, **FR-006**, **FR-007** (research.md R1, R4, R7, R9) (depends
  on T009, T010, T012, T013; makes them pass).

**Checkpoint**: `extract_coefficients()` complete and independently testable;
it imports `estimate_coefficient()` and duplicates none of its Hadamard-test
construction (research.md R1, R9).

---

## Phase 5: User Story 3 - Validate shot-based convergence against exact ground truth (Priority: P3)

**Goal**: A dedicated statistical convergence test proves, at more than one
increasing shot count, that `extract_coefficients()`'s real, finite-shot
estimates converge toward the Foundation Layer's exact oracle values within
a Hoeffding-derived tolerance — using the mandated Spec 3 fixture, not a
newly searched-for one, and passing for any random seed.

**Independent Test** (from spec.md): Run the shot-based engine at several
increasing shot counts on the mandated fixture and confirm each estimate
falls within that shot count's own derived tolerance of the exact oracle
value.

### Tests for User Story 3 ⚠️

- [x] T015 [US3] Write the statistical convergence test in
  `tests/oracle/test_extract_convergence.py`
  (`test_shot_based_estimates_converge_to_oracle`): using the mandated
  fixture (research.md R8, reused unchanged per **FR-010** — do not
  re-derive or re-search for a genuinely-complex construction), run
  `extract_coefficients()` at least at the four shot counts research.md R5
  already measured (`1e3, 1e4, 1e5, 1e6`), and at each shot count assert
  every real and imaginary part is within `eps(N, delta) =
  sqrt(2*ln(2/delta)/N)` (research.md R6, a stated `delta`, e.g. `0.01`) of
  `fourierlearn.reference.coefficients()`'s own exact value — **FR-009**
  (research.md R5, R6; Constitution §4.4). The test MUST NOT choose a seed by
  trial and error; run with a fixed, arbitrarily-chosen seed and document
  that no seed-shopping occurred.
  **No separate implementation task follows this one** — `extract_coefficients`
  (Phase 4) and `estimate_coefficient` (Phase 3) already provide full
  coverage; this test is what proves the convergence claim rather than
  assumes it, exactly mirroring Spec 3's own User Story 3.

**Checkpoint**: All three user stories independently functional and tested;
the shot-based extraction engine is validated end-to-end against exact
ground truth, at multiple shot counts, for any seed.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-layer verification once both the primitive and the
full-set extraction exist. **No performance, caching, or batching tasks** —
Constitution §5.3; research.md R9 explicitly considered and rejected
batching multiple circuits into one `sim.run()` call absent a recorded
profile.

- [x] T016 [P] Run the full suite (`pytest tests/ -v` and `mypy
  src/fourierlearn/`), Specs 1-4 together, and confirm everything is green —
  **SC-001**–**SC-006**. *(Confirmed: `pytest tests/ -q` → 115 passed, 98
  warnings in 213.00s; `mypy src/fourierlearn` → Success: no issues found in
  10 source files, after adding a `[[tool.mypy.overrides]]` entry for
  `qiskit_aer.*` — the first module in this project to import it — and
  annotating `all_frequencies: list[tuple[int, ...]]` in
  `extract_coefficients`.)*
- [x] T017 [P] Audit `src/fourierlearn/extract.py` (grep/manual review) to
  confirm `extract_coefficients()` contains zero duplicated Hadamard-test or
  `V_l` construction logic — every such operation goes through
  `estimate_coefficient()` and Circuits Layer's own `_increment_circuit` —
  Constitution §9.4; **FR-005**, **FR-006**. *(Confirmed: `extract_coefficients`
  calls `estimate_coefficient` exactly once per canonical frequency and derives
  the mirror via `.conjugate()`; `_hadamard_test_circuit` and
  `_v_l_dagger_circuit` each have exactly one definition, used only from
  `estimate_coefficient`.)*
- [x] T018 [P] Confirm, by reading `extract.py`, that zero caching, batching,
  or parameterised-circuit-template reuse was introduced: no memoization of
  Hadamard-test circuits across calls with the same frequency, no batched
  multi-circuit `sim.run()` submission, no template reuse across different
  target frequencies — every call performs the same single execution
  regardless of how many frequencies have already been estimated —
  Constitution §5.3, §9.3 (research.md R9). *(Guardrail: explicit
  zero-optimisation confirmation.)* *(Confirmed: grep for
  `cache|batch|template` in `extract.py` matches only prose in docstrings
  describing what was deliberately NOT done; no `lru_cache`, no memo dict, no
  batched `sim.run()` call.)*
- [x] T019 [P] Confirm, by grep/manual review of `src/fourierlearn/extract.py`,
  that no production code path imports `Statevector`, `Operator`, or `expm`
  — and separately re-run the Foundation Layer's own CI import guard test
  (`tests/ci/test_no_forbidden_imports.py`) to confirm it reports zero
  violations for the new module without any modification to the guard itself
  — Constitution Article II, §3.3-§3.4; **FR-001** (spec.md Assumptions: the
  guard's recursive scan already covers this feature). *(Confirmed: grep
  matches in `extract.py` are docstring-only; `pytest
  tests/ci/test_no_forbidden_imports.py -v` → 4 passed, guard file
  unmodified.)*
- [x] T020 [P] Cross-check that all six Success Criteria (SC-001 through
  SC-006) each have a corresponding passing test, and record the mapping
  (e.g. a short note in this file or a follow-up commit message) —
  **SC-001**–**SC-006**. *(Mapping — SC-001:
  `test_estimate_coefficient_returns_estimate_and_shot_count`; SC-002:
  `test_full_extraction_performs_only_half_the_circuit_executions`; SC-003:
  `test_estimate_coefficient_seed_independent_tolerance` and
  `test_shot_based_estimates_converge_to_oracle`; SC-004:
  `tests/ci/test_no_forbidden_imports.py` (all 4 tests); SC-005:
  `test_estimate_coefficient_returns_estimate_and_shot_count`; SC-006:
  `test_dc_coefficient_is_real_load_bearing`.)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup existing — BLOCKS all user
  stories only in the sense that it must stay green.
- **US1 / `estimate_coefficient` (Phase 3)**: Depends on Foundational. No
  dependency on any other user story — the more primitive construction, per
  spec.md's own stated priority ordering.
- **US2 / `extract_coefficients` (Phase 4)**: Depends on US1
  (`extract_coefficients` calls `estimate_coefficient` directly — FR-005;
  T014 cannot be implemented, let alone pass T009/T010/T012, before
  T007/T008 exist).
- **US3 / statistical convergence (Phase 5)**: Depends on US1 and US2 both
  existing (T015 calls `extract_coefficients`, which itself calls
  `estimate_coefficient`) — there is nothing to validate before both exist.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests are written first and MUST fail before their paired implementation
  task.
- Within US1: T003 (R3's exact-limit oracle match), T004 (R4's
  conjugate-symmetry-on-own-output check), and T005 (the non-degeneracy
  assertion) are three separate, independently-failing tests before T007 (the
  shared Hadamard-test/`V_l` helper); T006 (core acceptance) also precedes
  T007/T008. T007 precedes T008 since T008 calls the circuit builder T007
  defines.
- Within US2: T009 (core acceptance), T010 (DC-Hermiticity load-bearing),
  T011 (cost-budget guard), and T012 (non-Hermitian rejection) all precede
  T013/T014 (the implementation) — T013 (the guard itself) precedes T014
  (which invokes it).
- Within US3: T015 alone — no implementation task follows it, per Spec 3's
  own precedent for a pure-validation user story.

### Parallel Opportunities

As with Specs 2/3, multiple test tasks within one user story often share a
test file (T003/T004/T005/T006 all write to
`tests/unit/test_extract_hadamard_test.py`; T009/T010/T011/T012 share
`tests/unit/test_extract_full_coefficients.py`). Marking same-file tasks
`[P]` would invite merge conflicts, so none of T003–T006 or T009–T012 carry
a `[P]` marker.

- T016, T017, T018, T019, T020 (Polish) — five independent, read-only
  verification tasks over different concerns, safely parallel.
- Test-*writing* (not implementation) for a later story does not strictly
  require an earlier story's implementation to exist yet — T015 could be
  drafted while T007/T008/T013/T014 are still in progress, since tests are
  written to fail first regardless.

---

## Parallel Example: Polish (Phase 6)

```bash
# Launch all five Polish verification tasks together:
Task: "Run the full test suite and mypy, confirm green (SC-001-SC-006)"
Task: "Audit extract.py for zero duplicated Hadamard-test/V_l logic (FR-005, FR-006)"
Task: "Confirm zero caching/batching/template-reuse in extract.py (research.md R9)"
Task: "Re-run the CI import guard, confirm zero violations for the new module"
Task: "Cross-check SC-001-SC-006 each have a passing test"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1-2: Setup + Foundational — Specs 1-3 confirmed still green.
2. Phase 3 (US1): `estimate_coefficient()` complete and independently tested
   — **first genuinely useful increment**: any caller can already estimate a
   single Fourier coefficient from real, finite-shot measurement, with no
   full-set or convergence concept involved at all.
3. **STOP and VALIDATE**: Confirm US1's own tests (T003–T006) pass
   independently of `extract_coefficients`, which does not need to exist yet.

### Incremental Delivery

1. Complete Setup + Foundational → environment confirmed intact.
2. Add US1 (`estimate_coefficient`) → test independently (MVP!).
3. Add US2 (`extract_coefficients`) → test independently, including the
   conjugate-symmetry shortcut and cost-budget guard — depends on US1's
   primitive existing, per FR-005/FR-006's mandated reuse.
4. Add US3 (statistical convergence) → test independently — this increment
   adds no new production code, only the test proving both prior increments'
   shot-based behavior actually converges (research.md R5, R6).
5. Phase 6: Polish — whole-layer confirmation, no new logic.

### Test-First Discipline

Every implementation task above is paired with test tasks that precede it
and are expected to fail first. This is explicit, not incidental, for each
of the three guardrail-mandated dedicated checks: T003 (R3, exact-limit
oracle match), T004 (R4, conjugate symmetry on the estimator's own output —
distinct from T003, not merged with it), and T005 (the fixture's own
non-degeneracy, re-confirmed in this spec's own suite) all precede T007/T008.
None of these three are folded into a single generic "matches oracle" test
— each stands alone so a regression in exactly one of them points at exactly
one cause.

---

## Notes

- `[Story]` label maps every user-story-phase task to US1/US2/US3 for
  traceability; Setup, Foundational, and Polish tasks carry no story label by
  convention.
- Every task cites the FR(s) or SC(s) it satisfies and the specific
  research.md decision (R1–R9) it relies on — verify this before marking any
  task complete during `/speckit-implement`.
- No task in this list touches caching, batching, or parameterised-template
  reuse — by design (Constitution §5.3; research.md R9 explicitly considered
  and rejected batched multi-circuit `sim.run()` submission absent a
  recorded profile). T014's "opaque execution interface" requirement exists
  specifically so that a *future* batching refactor — if a profile someday
  justifies one — would not require changing `extract_coefficients`'s own
  calling contract; it does not itself introduce any batching now.
- T008's seed-offset contract (`seed` for the real-part circuit, `seed + 1`
  for the imaginary-part circuit) is a permanent part of
  `estimate_coefficient`'s public docstring, not an internal detail — a
  future implementation MUST NOT change this offset convention without it
  being a documented, deliberate contract change.
- T015 (User Story 3) is the one task in this list with no implementation
  task following it — intentional, not an omission, mirroring Spec 3's own
  User Story 3: Phases 3-4 already provide full coverage, so User Story 3
  has nothing left to implement, only to verify.
