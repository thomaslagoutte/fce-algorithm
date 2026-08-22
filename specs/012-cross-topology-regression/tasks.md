---

description: "Task list for the Cross-Topology Regression Layer (Spec 12)"
---

# Tasks: Cross-Topology Regression Layer

**Input**: Design documents from `/specs/012-cross-topology-regression/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md)

**Tests**: Included — this project's own established convention; spec.md's
own Acceptance Scenarios are stated as verifiable requirements, not
aspirations.

**Organization**: Tasks are grouped by user story (US1/US2/US3, matching
spec.md's P1/P2/P3 priorities).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (training row + extraction + lattice alignment), US2
  (LASSO fit across topologies), US3 (held-out prediction)

## Path Conventions

Single project (per plan.md's Structure Decision): `src/fourierlearn/`,
`tests/unit/`, `tests/oracle/`.

---

## Phase 1: Setup

- [x] T001 Create `src/fourierlearn/cross_topology.py` with a module
      docstring only (stating this module's own non-reuse boundary
      against `learn.py`, per FR-003) — no logic yet. No other setup is
      needed: this feature adds no new dependency (`scikit-learn`'s
      `LassoCV` is already a dependency via `learn.py`) and no new
      top-level directory.

---

## Phase 2: Foundational (Blocking Prerequisites)

**None required.** Phase 0 research already resolved every design
question a shared foundation would otherwise need to settle: the `b(x)`
object-identity finding (research.md R2), the executed LASSO-vs-KRR
cross-check defining SC-006's own tolerance (research.md R3), and the
frequency-lattice-signature mechanism (research.md R4). US1's own tasks
below implement these directly; nothing here blocks US2/US3 beyond US1's
own natural data dependency (US2 needs US1's feature vectors; US3 needs
US2's fitted model).

---

## Phase 3: User Story 1 - Training row, extraction, and lattice alignment (Priority: P1) 🎯 MVP

**Goal**: A `(x_t, y_t)` training-row abstraction (FR-001), per-row feature
extraction via Spec 4's real `extract_coefficients` (FR-002), a verified
conjugate-symmetric real-stacking convention (FR-006), a structural
frequency-lattice-alignment check with surgical rejection errors
(FR-008/FR-014), and a structurally enforced non-reuse boundary against
`learn.py` (FR-003).

**Independent Test**: Build several topologies sharing one lattice,
extract each row's `b(x_t)` via a genuinely separate circuit per topology,
confirm the stacking round-trips exactly, confirm a lattice mismatch is
rejected with a surgical error message, and confirm the module never
imports `learn.py`'s flipped-direction symbols.

### Tests for User Story 1

- [x] T002 [P] [US1] **Critical Mandate 2**: new file
      `tests/unit/test_cross_topology_no_learn_reuse.py` — an AST-based
      scanner (mirroring `tests/ci/test_no_forbidden_imports.py`'s own
      technique, but its own file: that file's scope is a project-wide
      invariant unrelated to this one-module-vs-one-module boundary)
      asserting `src/fourierlearn/cross_topology.py` never imports
      `learn.py`'s `estimate_y`, `TrainingRow`, `build_sensing_matrix`,
      `LassoRegressionBackend`, or `fit_model` (FR-003/SC-002). **This
      test file MUST run unconditionally in the default `pytest tests/`
      suite — no `@pytest.mark.skip`, `@pytest.mark.slow`, or any other
      conditional marker may be applied to it or to any test function
      inside it.** (This repository has no such marker mechanism
      configured at all — `pyproject.toml`'s `[tool.pytest.ini_options]`
      has only `testpaths`, confirmed during Spec 11 — so this is a
      structural default, not merely a stated intention.)
- [x] T003 [P] [US1] Unit test: `CrossTopologyRow` holds `(x_t, y_t)`
      where `x_t` is a classical-input/topology declaration (an IR, or
      the IR-construction inputs identifying which fixed gates it
      selects) — never a bound numeric `alpha` value. Assert the
      dataclass has no field whose semantics is "a bound encoded-
      parameter assignment" (FR-001).
- [x] T004 [US1] Oracle test in `tests/oracle/`: `extract_feature_vector`
      calls Spec 4's `extract_coefficients` and requires a genuinely
      SEPARATE circuit compilation per topology — verified via an
      instrumented call-counter (mirroring Spec 11's own
      `_InstrumentedAerSimulator` pattern) confirming `compile_
      observable_circuit` (or `extract_coefficients`'s own internal
      compile step) runs once per distinct topology, never once for a
      shared circuit with only a bound parameter varying (FR-002).
- [x] T005 [US1] Unit test: FR-006's conjugate-symmetric real-stacking
      round trip, verified end to end through `extract_coefficients`
      itself (not only the stacking sub-piece in isolation) on a
      genuinely complex fixture (research.md R3's own `RZ(θ)`-varied
      mandated fixture, or Spec 4's own three-untied-parameter fixture) —
      stack, then reconstruct, and confirm the reconstructed complex
      coefficients match the original `extract_coefficients` output
      exactly (within numerical tolerance).
- [x] T006 [P] [US1] **Critical Mandate 1**: Unit test for
      `FrequencyLatticeMismatchError` — construct two rows' IRs sharing
      identical Trotter configuration but differing in `multiplicity` for
      one parameter, and assert the raised error's message contains BOTH
      the exact `parameter_index` that mismatched AND the specific field
      name (`"multiplicity"`) that differed — parse/assert on the actual
      message content, not merely the exception type. Repeat for a
      `coefficients` mismatch and an `upload_count` mismatch (three
      distinct field-mismatch cases, each asserted by message content) —
      **a generic "lattices differ" message must make this test fail.**
- [x] T007 [P] [US1] Unit test: the FR-008 case (identical multiplicity/
      coefficients, but different Trotter `r`/`tau`, which changes
      `upload_count`) is caught by the SAME `_frequency_lattice_signature`
      mechanism T006 exercises — not a separate code path — confirming
      FR-008 is one instance of FR-014's general check.
- [x] T008 [P] [US1] Unit test: multiple rows sharing an IDENTICAL
      frequency lattice (differing only in their classical-input-selected
      fixed gates) pass validation with no error raised.

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement `CrossTopologyRow` (a frozen dataclass
      pairing a topology declaration and its label) in `cross_topology.py`
      (FR-001) — satisfies T003.
- [x] T010 [US1] Implement `extract_feature_vector(ir_x, observable,
      shots, seed=None, simulator=None)` in `cross_topology.py`: a thin
      wrapper around `extract.extract_coefficients` (Spec 4, Spec-11-
      repaired, including its own additive `simulator` parameter) — FR-002
      — satisfies T004. Must import ONLY `fourierlearn.extract` (and
      `fourierlearn.ir`/`fourierlearn.circuits` as needed for type
      signatures) — never `fourierlearn.learn`.
- [x] T011 [US1] Implement the real-stacking/reconstruction functions in
      `cross_topology.py` — original code, NOT imported from `learn.py`'s
      `_stack_real`/`_reconstruct_complex` (FR-003's non-reuse boundary
      applies here too, even though the underlying conjugate-symmetry
      IDENTITY is the same one Constitution §7.6 already establishes) —
      satisfies T005 (FR-006).
- [x] T012 [US1] Implement `_frequency_lattice_signature(ir)`,
      `FrequencyLatticeMismatchError`, and `validate_lattice_alignment
      (rows)` in `cross_topology.py` (FR-014, research.md R4; FR-008 as
      one instance of this check). **The raised error's message MUST
      name the exact `parameter_index` and the exact field
      (`upload_count`, `multiplicity`, or `coefficients`) that mismatched
      between the two offending rows** — e.g.
      `f"frequency lattice mismatch at parameter_index={idx}: "
      f"field={field!r} row[{i}]={val_i!r} != row[{j}]={val_j!r}"` — never
      a generic "lattices differ" message (Critical Mandate 1) — satisfies
      T006/T007.

**Checkpoint**: User Story 1 is independently functional and tested.

---

## Phase 4: User Story 2 - LASSO fit across topologies, honestly under-determined (Priority: P2)

**Goal**: A LASSO fit for a sparse weight vector `w(α*)` across
`{(b(x_t), y_t)}` pairs (FR-004), with data-driven-only penalty selection
(FR-009), and both specs' shared linear-model relationship made concrete
via an executed, permanent cross-check against Spec 10's KRR route
(FR-013/SC-006).

**Independent Test**: Fit LASSO on `T` topologies with `T` strictly fewer
than the frequency-column count, confirm no "not enough samples" guard
fires, confirm sparse recovery on a validation case, and confirm the
LASSO/KRR cross-check reproduces research.md R3's own tolerance-based
(never equality-based) result.

### Tests for User Story 2

- [x] T013 [P] [US2] Unit test: fitting on `T` topologies with `T`
      strictly fewer than the number of real-stacked frequency columns
      never raises, warns, or otherwise guards against "too few" training
      topologies (FR-004 Acceptance Scenario 1).
- [x] T014 [US2] Oracle test (SC-001) in `tests/oracle/test_cross_
      topology_lasso_recovery.py`: a known-sparse validation case whose
      active frequencies are FULLY recovered by the fit. **Implementation
      note, from research.md R3's own executed finding**: at `T=5` (the
      research-phase fixture's own under-determined point) `LassoCV`
      recovered only the numerically larger of two active terms, and even
      research.md's own `T=12` (well-determined) run with the SAME `w_
      true` did not recover the smaller term either — this task MUST
      empirically re-tune the validation case (e.g. more separated active-
      term magnitudes, a different `T`, or an explicit, non-CV-selected
      alpha) until FULL support recovery is genuinely observed, rather
      than assuming research.md's own exact fixture/weights achieves it —
      document whatever adjustment was needed and why, per this project's
      "verify before asserting" discipline.
- [x] T015 [P] [US2] Unit test (FR-009, mirroring Spec 5's own FR-004
      guardrail test style): fit twice on the same topologies and labels,
      once at a small shot count (large label noise) and once at a much
      larger shot count, with the penalty grid and cross-validation
      procedure held fixed; confirm the grid and procedure are provably
      identical between the two runs — never a function of the shot
      count.
- [x] T016 [US2] Oracle test (SC-006) in `tests/oracle/test_cross_
      topology_krr_crosscheck.py`: reproduce research.md R3's executed
      LASSO-vs-KRR cross-check as a PERMANENT regression test — same
      fixture, same `w_true`, same held-out points. Assert: (a) both
      routes' held-out predictions fall within a documented, non-zero
      tolerance of the TRUE (oracle) label; (b) the two routes' MUTUAL
      divergence is computed and logged/reported, but the test MUST NOT
      assert it is below some near-zero threshold or equal to zero —
      only that both individually track the truth within tolerance
      (Critical Research Mandate 1, carried from `/speckit-plan`). Reuses
      Spec 10's `kernel.py` (`build_gram_matrix`/`krr_fit_predict`)
      applied to THIS feature's own `extract_feature_vector` output
      (research.md R2's own design decision) — never Spec 10's amplitude-
      based circuit/oracle.

### Implementation for User Story 2

- [x] T017 [US2] Implement `fit_cross_topology_lasso(rows, observable,
      ...)` in `cross_topology.py`: validates lattice alignment (T012)
      across all rows first, builds the real-stacked design matrix (T011)
      and label vector, and fits via `sklearn.linear_model.LassoCV`
      (matching `learn.py`'s own established library convention, per
      plan.md) — FR-004 — satisfies T013/T014.
- [x] T018 [US2] Implement FR-009's penalty-selection discipline
      explicitly in `fit_cross_topology_lasso`: an explicit, version-
      pinned candidate grid and a fixed cross-validation fold count,
      neither read from shot count nor from any noise-bound quantity —
      satisfies T015.
- [x] T019 [US2] Document FR-013 (the Spec 10/Spec 12 primal/dual
      relationship) directly in `cross_topology.py`'s own module or
      `fit_cross_topology_lasso` docstring, citing research.md R2's `b(x)`
      object-identity finding and R3's executed cross-check numbers
      plainly — mirroring Spec 11's own precedent of writing this kind of
      framing directly into shipped docstrings, not only into research.md.

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - Prediction on a held-out topology (Priority: P3)

**Goal**: `ŷ* = b(x*)^⊤ŵ` via the identical extraction path as every
training row (FR-005), with an explicit held-out-disjointness assertion
(FR-010) and Hermiticity-gated real-valued predictions (FR-011).

**Independent Test**: Hold out one topology, confirm it is absent from
the training set, predict via the same extraction call path, confirm
rejection on a non-Hermitian observable before any prediction is
attempted.

### Tests for User Story 3

- [x] T020 [P] [US3] Unit test (FR-010): after generating a training/
      held-out split (including a randomly generated one), the pipeline
      asserts zero overlap between the held-out topology and the training
      set — checked explicitly, never assumed.
- [x] T021 [US3] Unit test (FR-005/FR-011): prediction calls the SAME
      `extract_feature_vector` function as every training row (asserted
      via, e.g., a shared instrumented call path, not merely by code
      inspection); a non-Hermitian observable is rejected with a clear
      error before any prediction is attempted, mirroring Spec 4's own
      rejection convention.

### Implementation for User Story 3

- [x] T022 [US3] Implement `predict(model, x_star, observable, shots,
      seed=None, simulator=None)` in `cross_topology.py`: extracts
      `b(x*)` via T010's `extract_feature_vector` (never a distinct
      prediction-time extraction path), applies T011's stacking
      convention, and computes `ŷ* = b(x*)^⊤ŵ` — FR-005 — satisfies T021.
- [x] T023 [US3] Implement the held-out-split assertion helper (FR-010) —
      satisfies T020.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T024 [P] Run `mypy` across `src/fourierlearn/cross_topology.py`,
      fixing any type errors.
- [x] T025 Run the full `pytest` suite and confirm green, including
      `tests/ci/test_no_forbidden_imports.py` and this feature's own new
      `tests/unit/test_cross_topology_no_learn_reuse.py` (Critical Mandate
      2 — confirm it ran, was not skipped, and passed, in a plain
      `pytest tests/` invocation with no marker filters).
- [x] T026 [P] Constitution §5.3 audit: confirm no caching, batching, or
      memoization was introduced anywhere in `cross_topology.py` — add a
      one-line docstring note on each new public function recording this,
      matching Spec 10/11's own established convention.
- [x] T027 [P] Extension-register determination: this feature repairs/
      restores a core part of the thesis's own advantage-relevant
      learning direction (not an `EXTENSION` beyond the source, per
      Constitution §2.3's own scope) — mirroring Spec 11's own reasoned
      decision, explicitly confirm and record that no
      `.specify/memory/extension-register.md` entry is warranted, rather
      than silently skipping the question.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty.
- **User Story 1 (Phase 3)**: Can start immediately after Setup.
- **User Story 2 (Phase 4)**: Depends on User Story 1's `extract_feature_
  vector`, stacking convention, and lattice-validation existing (T010-
  T012) before T017 can build its design matrix.
- **User Story 3 (Phase 5)**: Depends on User Story 2's fitted model
  (T017) existing, and reuses User Story 1's `extract_feature_vector`
  (T010) directly.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests (T002-T008, T013-T016, T020-T021) are written and run FAILING
  before their corresponding implementation tasks, per this project's
  established TDD convention.
- T012 (the lattice-mismatch error) and T006/T007 (its own tests) are the
  tasks directly answering this round's Critical Mandate 1 — T012 may not
  be marked complete until T006/T007 both pass against it.
- T002 is the task directly answering this round's Critical Mandate 2 —
  it must be verified to run unconditionally (T025) before Polish is
  considered complete.

### Parallel Opportunities

- T002, T003, T006, T007, T008 (distinct US1 test concerns/files).
- T009 (independent of T010-T012's own sequencing, though all in one file).
- T013, T015 (distinct US2 test concerns).
- T020 (independent US3 test concern).
- T024, T026, T027 (Polish, different concerns).

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 3 (User Story 1) — training rows, real extraction, a
   verified stacking convention, and surgical lattice-mismatch rejection
   are independently valuable and independently demonstrable.
3. **STOP and VALIDATE**: T002 (unconditional, must pass), T005-T008 all
   pass.

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → this is the MVP.
2. Add Phase 4 (US2) → validate T014's re-tuned recovery case and T016's
   tolerance-based (never equality-based) cross-check.
3. Add Phase 5 (US3) → validate T020-T021 → held-out prediction via the
   identical extraction path.
4. Phase 6 (Polish) closes out the feature.

## Notes

- No task in this list introduces caching, batching, or memoization
  (Constitution §5.3) — T026 is the explicit audit closing this out.
- `[P]` tasks touch different files or independent concerns with no
  dependency on an incomplete task in the same phase.
- Commit after each task or logical group, per this project's existing
  practice on Specs 1-11.
