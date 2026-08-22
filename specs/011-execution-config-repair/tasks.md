---

description: "Task list for Execution Configuration and Controlled-Circuit Defect Repair (Spec 11)"
---

# Tasks: Execution Configuration and Controlled-Circuit Defect Repair

**Input**: Design documents from `/specs/011-execution-config-repair/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md)

**Tests**: Included — this project's own established convention, and
spec.md's own Acceptance Scenarios are stated as verifiable proof
obligations (the Two-Tiered Equivalence Proof), not aspirations.

**Organization**: Tasks are grouped by user story (US1/US2/US3, matching
spec.md's P1/P2/P3 priorities).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (controlled-circuit defect repair), US2 (explicit
  transpile configuration), US3 (additive `simulator` parameter)

## Path Conventions

Single project (per plan.md's Structure Decision): `src/fourierlearn/`,
`tests/unit/`, `tests/oracle/`.

---

## Phase 1: Setup

**None required.** This feature repairs two functions and adds parameters
to three functions, all within `src/fourierlearn/extract.py` (including
`estimate_kernel_overlap`, which — corrected during implementation — also
lives in `extract.py`, not `circuits.py` as an earlier draft of this file
stated) — no new module, no new dependency, no new top-level directory.
`tfim_dynamics_sweep_profile.py` (repo root) stays
exactly as-is: it is the "BASELINE PROFILING ONLY" script this feature's
own research phase already reused unmodified (research.md R1) and
continues to reuse for the implementation-time re-verification below —
it is not touched or imported into `src/fourierlearn`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**None required beyond Phase 0 research, already complete.** research.md
already executed and verified (a) the inline-assembly construction logic
(Tier 1, 20/20 checks) and (b) its correctness at the actual baseline
scale (Tier 2, 4/4 checks) as a PROTOTYPE, before this task list existed.
US1's own tasks below port that already-verified logic into the real
`extract.py` and re-confirm it there — this is not new design work.

---

## Phase 3: User Story 1 - Repair the whole-block `.control()` construction defect (Priority: P1) 🎯 MVP

**Goal**: Replace both `.control()`-wrap violation sites (FR-001,
FR-002) with an inline, gate-by-gate controlled assembly (Constitution
§5.7), proven correct by the Two-Tiered Equivalence Proof (FR-003/FR-012/
FR-013) and by a reproduced, substantial wall-clock improvement (FR-005).

**Independent Test**: Tier 1 + Tier 2 both pass on the actual shipped
code (not just research.md's prototype), and the documented baseline
configuration's wall-clock time drops substantially and reproducibly.

### Tests for User Story 1

- [x] T001 [P] [US1] Add Tier 1 proof (FR-012) to
      `tests/unit/test_extract_hadamard_test.py`: `Operator.equiv`
      between the OLD (pre-repair) and NEW (inline-assembled)
      `_hadamard_test_circuit`/`_v_l_dagger_circuit` construction, on the
      file's own existing "mandated fixture" plus the minimal 2-qubit/
      2-parameter fixture research.md R3 verified (`register_width(1,1)`
      per parameter — deliberately NOT the wider, tied-parameter fixture
      R3 found intractable). Reproduce research.md R3's representative
      sampling (min/`0`/max/one-interior value per frequency axis, both
      `real`/`imag` parts) — not an exhaustive sweep.
- [x] T002 [US1] Add Tier 2 proof (FR-013) as a NEW file,
      `tests/oracle/test_extract_hadamard_test_scale_equivalence.py`, in
      the DEFAULT suite — explicitly NOT marked slow/optional (Critical
      Research Mandate 3; this repo has no such marker mechanism at all).
      Build the actual documented-baseline fixture (`n=3, r=2, t=1.09`
      TFIM, via `tfim_dynamics_sweep_profile.get_tfim_ir`), compare the
      OLD and NEW `_hadamard_test_circuit` via `Statevector` on the
      all-zero state and a seeded Haar-random state
      (`qiskit.quantum_info.random_statevector`), for both `real`/`imag`
      parts — reproducing research.md R4's exact 4/4-check result against
      the REAL, shipped construction (not the scratch prototype it was
      first proven on).
- [x] T003 [P] [US1] Regression test in
      `tests/unit/test_extract_hadamard_test.py` (Edge Case, spec.md): a
      target frequency component of exactly `0` produces a correct,
      empty-block-safe controlled assembly (no error, no meaningless
      no-op control appended).

### Implementation for User Story 1

- [x] T004 [US1] Add a shared helper `_append_controlled_block(qc,
      block, control_qubit, target_qubits)` to `src/fourierlearn/
      extract.py`: `block.decompose()` once (research.md R3: sufficient
      to reach only natively-controllable gates for every block this
      module builds — no opaque custom gate survives one `decompose()`
      call), then individually `.control(1)` each resulting instruction
      and append in original order (Constitution §5.7:
      `c-(U_K⋯U₁)=c-U_K⋯c-U₁`) — used by BOTH T005 and T006 below
      (Constitution §9.4: neither repair site reimplements this loop
      independently).
- [x] T005 [US1] FR-001: in `_hadamard_test_circuit`, replace
      `circuit.to_gate(label="A(U,O)").control(1)` with a call to
      T004's `_append_controlled_block`. Must make T001's small-fixture
      checks pass BEFORE T002's baseline-scale check is attempted
      (Critical Mandate 1's ordering, mirrored at implementation time:
      cheap correctness first).
- [x] T006 [US1] FR-002: in the same function, replace `_v_l_dagger_
      circuit(...).to_gate(label="Vl_dag").control(1)` with a second
      call to T004's `_append_controlled_block` — independently verified
      by T001/T002 (a second, separate construction site, not folded
      into T005's own verification).
- [x] T007 [US1] Re-run T001 (Tier 1) and T002 (Tier 2) against the
      ACTUAL, now-repaired `extract.py` (not the scratch prototype
      research.md R3/R4 verified) and confirm the same 20/20 and 4/4
      passing results reproduce on the real, shipped code.
- [x] T008 [US1] Re-run research.md R1/R6's exact before/after benchmark
      (`n=3, r=2, shots=20000, seed=7, t=1.09`, via `tfim_dynamics_
      sweep_profile`'s own fixture functions) against the ACTUAL shipped
      `extract_coefficients`, 2 trials, and confirm a substantial,
      reproducible improvement over the documented `1108.00s`/research.md
      R1's own re-measured `1213.23s` mean — satisfies FR-005/SC-001 for
      the real implementation, not only the prototype.
- [x] T009 [P] [US1] Run every existing Spec 4 test (`tests/unit/
      test_extract_hadamard_test.py`, `tests/oracle/test_extract_
      convergence.py`) and every Spec 10 test depending on this module
      (`tests/oracle/test_extract_kernel_overlap_shots.py`) UNMODIFIED
      and confirm all pass (FR-008/SC-002) — any disagreement found here
      is this feature's OWN defect to fix, never grounds to weaken the
      disagreeing test.

**Checkpoint**: User Story 1 is independently functional, proven correct
at both scales, and benchmarked.

---

## Phase 4: User Story 2 - Make `transpile()`'s configuration explicit (Priority: P2)

**Goal**: `optimization_level` and the basis-gate set become named,
benchmarked, documented values in this codebase (FR-004), chosen against
the User-Story-1-repaired circuit, not the defective one.

**Independent Test**: Reading `estimate_coefficient`'s source shows an
explicit, named `optimization_level`; the benchmark backing that choice
is reproducible from this codebase alone.

### Tests for User Story 2

- [x] T010 [P] [US2] Unit test in `tests/unit/test_extract_hadamard_
      test.py` (or a new `tests/unit/test_extract_transpile_config.py`):
      assert `estimate_coefficient`'s `transpile()` call site uses a
      named module-level constant for `optimization_level` (and
      `basis_gates`, if non-`None`) — not a bare `transpile(qc,
      simulator)` call with no explicit level (SC-005).

### Implementation for User Story 2

- [x] T011 [US2] Add named constants to `src/fourierlearn/extract.py`:
      `_DEFAULT_OPTIMIZATION_LEVEL = 1` and `_DEFAULT_BASIS_GATES = None`
      (meaning "AerSimulator's own native target," documented as such in
      a comment — research.md R5 found no explicit re-basis beneficial),
      each with a docstring/comment citing research.md R5's own executed
      sweep numbers (`0`: `89.0s`, `1`: `80.4s` sample-projected /
      `189.66s`/`214.04s` actual full-run, `2`: `119.8s`, `3`: `107.9s` —
      `1` fastest) as the reason for the chosen value — a benchmarked
      choice, not a silent default (FR-004).
- [x] T012 [US2] Update `estimate_coefficient`'s `transpile()` calls to
      pass `optimization_level=_DEFAULT_OPTIMIZATION_LEVEL` (and
      `basis_gates=_DEFAULT_BASIS_GATES` if not `None`) explicitly,
      satisfying T010.

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - Accept a caller-supplied, pre-configured simulator (Priority: P3)

**Goal**: `estimate_coefficient`, `extract_coefficients`, and
`estimate_kernel_overlap` each accept an additive `simulator: AerSimulator
| None = None` (FR-006), with `None` reproducing today's exact behavior
(FR-007) and a supplied instance genuinely honored — including being
REUSED across every internal sub-call within `extract_coefficients`, per
research.md R9's own conclusion that this is a semantic-correctness
requirement (a caller-configured backend should apply to every
sub-circuit), independent of R9's finding that raw `AerSimulator()`
construction cost is negligible (`0.0000s/call`) and therefore NOT a
performance problem this parameter is fixing.

**Independent Test**: `simulator=None` is behaviorally indistinguishable
from today; a differently-configured instance is genuinely used, on
EVERY sub-circuit `extract_coefficients` builds, not just the first.

### Tests for User Story 3

- [x] T013 [P] [US3] Unit test: `estimate_coefficient(..., simulator=None)`
      and `estimate_coefficient(...)` (omitted) behave identically to
      today's unmodified behavior — existing seed-determinism contract
      preserved (FR-007 Acceptance Scenario 1).
- [x] T014 [P] [US3] Unit test: a caller-supplied `AerSimulator` instance
      passed to `estimate_coefficient` is the exact object used for
      execution (e.g. via a lightweight instrumented/subclassed
      `AerSimulator` recording whether `.run()` was called on it) — never
      silently replaced (FR-007 Acceptance Scenario 2).
- [x] T015 [US3] Unit test (research.md R9's own semantic-correctness
      requirement): a single caller-supplied `AerSimulator` instance
      passed to `extract_coefficients` is reused across ALL of its
      internal per-frequency `estimate_coefficient` calls — not
      reconstructed fresh per frequency internally when a non-`None`
      instance is supplied. Use an instrumented instance counting `.run()`
      invocations against object identity to confirm the SAME instance
      served every one of the fixture's canonical frequencies.
- [x] T016 [P] [US3] Unit test: `estimate_kernel_overlap(..., simulator=
      None)` is identical to today's behavior; a differently-configured
      instance is genuinely used (mirrors T013/T014 for the Spec 10
      function).

### Implementation for User Story 3

- [x] T017 [US3] Add `simulator: AerSimulator | None = None` to
      `estimate_coefficient`: when `None`, construct a fresh
      `AerSimulator()` exactly as today (FR-007); when supplied, use it
      as-is.
- [x] T018 [US3] Add `simulator: AerSimulator | None = None` to
      `extract_coefficients`: when `None`, preserve today's exact
      behavior (each internal `estimate_coefficient` call constructs its
      own fresh `AerSimulator()`, unchanged); when supplied, pass the
      SAME instance through to every internal `estimate_coefficient`
      call (satisfies T015 — this is the one behavioral difference
      between "supplied" and "not supplied," and it is a semantic
      (identity/configuration-fidelity) requirement, not a performance
      optimisation, per research.md R9).
- [x] T019 [US3] Add `simulator: AerSimulator | None = None` to
      `estimate_kernel_overlap` (`src/fourierlearn/circuits.py`),
      mirroring T017's `None`-preserves-behavior contract exactly.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T020 Update `_hadamard_test_circuit`'s and `extract_coefficients`'s
      own module/function docstrings in `src/fourierlearn/extract.py` to
      state PLAINLY (research.md R9/R10, per this round's own framing
      requirements) — not only in research.md — that: (a) `AerSimulator()`
      reconstruction overhead is NOT a meaningful cost (measured
      `0.0000s/call`) and deliverable (c)'s `simulator` parameter does
      not "fix" it because nothing there needed fixing; the remaining
      pre-repair cost was `transpile()` (`~1.02s/call` in isolation) and
      actual execution (`~1.32s/call` in isolation); and (b) the measured
      ~6.0x speedup is for ONE time-point, ONE `(n,r)` instance, on ONE
      laptop, with no caching/batching/template reuse on either side —
      closing any further gap to a different codebase's previously-
      reported multi-graph performance figure is explicitly out of this
      feature's scope (Critical Mandate 4) and left to a future profiling
      spec, not silently implied as already achieved here.
- [x] T021 [P] Update `.specify/memory/extension-register.md` (if this
      repair is registered there) or add a brief note where Spec 4/EXT
      entries live, recording this repair's completion and citing
      research.md's own R1/R6 before/after figures — mirroring this
      project's own established convention of recording defect repairs
      where future readers will look for them.
- [x] T022 [P] Run `mypy` across the modified `src/fourierlearn/
      extract.py` and `src/fourierlearn/circuits.py`, fixing any type
      errors.
- [x] T023 Run the full `pytest` suite and confirm green, including
      `tests/ci/test_no_forbidden_imports.py` (this repair introduces no
      new import of `reference`/`Statevector`/`Operator`/`expm` into any
      production module — T001/T002's own `Statevector`/`Operator` usage
      lives in `tests/`, never in `src/fourierlearn/extract.py` itself).
- [x] T024 [P] Constitution §5.3 audit: confirm no transpile-caching,
      parametrized-template reuse, or cross-circuit/cross-graph batching
      was introduced anywhere in T004-T019 (Critical Mandate 4) — every
      new function still constructs, transpiles, and executes fresh per
      call, matching research.md R11's own audit of the prototype.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Empty.
- **Foundational (Phase 2)**: Empty — Phase 0 research already did the
  design-proving work.
- **User Story 1 (Phase 3)**: Can start immediately. MUST complete before
  User Story 2 begins (spec.md: benchmarking `transpile()` against the
  still-defective circuit produces numbers that don't transfer once
  US1's fix lands).
- **User Story 2 (Phase 4)**: Depends on User Story 1's repair (T005/T006)
  being in place before T011's benchmark-driven constant choice is made.
- **User Story 3 (Phase 5)**: Independent of US1/US2's own internal
  logic — the `simulator` parameter is a pure pass-through seam — but
  ordered last per spec.md's own priority (P3): tuning execution of a
  not-yet-repaired circuit is not a meaningful benchmark, so US3's own
  "why this priority" explicitly defers to US1/US2 landing first even
  though nothing here is a hard code dependency.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests (T001-T003, T010, T013-T016) are written and run FAILING before
  their corresponding implementation tasks, per this project's
  established TDD convention.
- T005/T006 (the two repair sites) MUST both pass T001 (Tier 1) before
  T002 (Tier 2, expensive) is attempted — mirrors Critical Mandate 1's
  strict ordering at implementation time, not only at research time.

### Parallel Opportunities

- T001 and T003 (different concerns, same file, but no ordering
  dependency between them).
- T009 (regression-run existing suites) can run any time after T007.
- T013, T014, T016 (independent US3 test files/concerns).
- T021, T022, T024 (Polish, different concerns, no shared file conflict).

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 3 (User Story 1) — the actual defect repair, proven by
   the Two-Tiered Equivalence Proof and a reproduced benchmark
   improvement, is independently valuable on its own.
2. **STOP and VALIDATE**: T007/T008/T009 all pass.

### Incremental Delivery

1. Phase 3 (US1) → validate → repaired construction, proven and
   benchmarked.
2. Phase 4 (US2) → validate T010 → `transpile()` configuration is now
   explicit and benchmarked, not inherited.
3. Phase 5 (US3) → validate T013-T016 → callers can supply their own
   simulator, with the one genuine behavioral difference (reuse across
   `extract_coefficients`'s internal loop) explicitly tested.
4. Phase 6 (Polish) closes out the feature, including plainly stating
   the cost-breakdown and speedup-scope framing directly in the shipped
   code's own docstrings (T020), not only in research.md.

## Notes

- No task in this list introduces caching, batching, or memoization
  (Constitution §5.3, Critical Mandate 4) — T024 is the explicit audit
  closing this out.
- `[P]` tasks touch different files (or independent concerns within one
  file) with no dependency on an incomplete task in the same phase.
- Commit after each task or logical group, per this project's existing
  practice on Specs 1-10.
