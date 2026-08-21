---

description: "Task list for the Experiment and Models Layer"
---

# Tasks: Experiment and Models Layer

**Input**: Design documents from `/specs/006-experiment-models-layer/` (spec.md, plan.md, research.md)

**Tests**: Included — this project's own established test-first convention (Specs 1-5) continues here.

**Organization**: Tasks are grouped by user story (spec.md: US1 P1, US2 P2, US3 P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)

## Path Conventions

Single Python library, matching Specs 1-5: `src/fourierlearn/`, `tests/unit/`, `tests/oracle/`, `tests/ci/`.

---

## Phase 1: Setup

- [x] T001 Confirm no new third-party dependency is needed (`qiskit`, `qiskit-aer`, `numpy`, `scikit-learn` already pinned) — no `pyproject.toml` change for this feature.

**Checkpoint**: Setup complete.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The CI import guard must accept the narrow exemption *before*
`_exact_dynamics.py` (User Story 1) is created — otherwise creating that
file immediately breaks `test_clean_tree_reports_no_violations` for every
other spec's own suite, not just this one. This is shared test
infrastructure, not any one user story's business logic, so it is
Foundational.

- [x] T002 Apply research.md R3's exact diff to
  `tests/ci/test_no_forbidden_imports.py`: add the
  `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY = "_exact_dynamics.py"` module-level
  constant with its full scientific-necessity comment (verbatim from
  research.md R3, citing Constitution §8.2 and the executed refutation
  guard), and change `find_violations`'s body to subtract `{"reference"}`
  from a matched module's findings. **Guardrail #2 (CI Guard Backwards
  Compatibility)**: implement this as a **new keyword parameter**
  `narrow_exempt_module: str = _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` on
  `find_violations` — not a hardcoded reference to the module-level
  constant inside the function body — so every existing call site
  (`find_violations(root)`, `find_violations(root, exempt_module=...)`)
  continues to work completely unchanged via the new parameter's default
  value. `_scan_module` itself is NOT modified (research.md R3: the
  scanner stays blind to any exemption; only `find_violations`'s
  aggregation step applies one).
- [x] T003 [P] Add `test_narrow_exemption_does_not_widen_to_other_modules`
  to `tests/ci/test_no_forbidden_imports.py` (research.md R3, "some other
  module" case): a module named anything other than
  `_exact_dynamics.py` that imports `fourierlearn.reference` MUST still be
  rejected — proving the exemption is narrow, not a general widening.
- [x] T004 [P] Add `test_narrow_exemption_still_rejects_statevector_and_operator`
  to `tests/ci/test_no_forbidden_imports.py` (research.md R3, "exempt
  module itself" case): a synthetic module literally named
  `_exact_dynamics.py` that imports `fourierlearn.reference` **and**
  `Statevector` (or `Operator`/`expm`) MUST still be flagged for
  `Statevector`/`Operator`/`expm` — the exemption covers `reference` only,
  never a blanket pass for that filename.
- [x] T005 Run `pytest tests/ci/test_no_forbidden_imports.py -v` and confirm
  all tests pass (the pre-existing four plus T003/T004's two new ones) —
  **before** any file named `_exact_dynamics.py` exists in `src/fourierlearn/`,
  so this checkpoint proves the guard change alone, independent of the
  module it will later exempt.

**Checkpoint**: CI guard accepts the narrow exemption; User Story 1
implementation can now begin.

---

## Phase 3: User Story 1 - Resolve a flagged generalization check (Priority: P1) 🎯 MVP

**Goal**: Given a Spec 5 `ErrorBoundingReport` flagged
`generalization_check_required=True`, compute the exact ground-truth value
at a shifted input via the one narrowly-exempt module, compare it
deterministically against the model's prediction, and return
`generalizes`/`refuted` without ever mutating the consumed report.

**Independent Test**: spec.md's own User Story 1 Independent Test —
confirmed by research.md R1's executed refutation guard (an artifact
returns `refuted`; a true model returns `generalizes`) and R2's threshold
cases.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; confirm they FAIL before the corresponding implementation task.

- [x] T006 [US1] **Negative Control (Guardrail #4)** —
  `test_refutation_guard_detects_overfitting_artifact` in
  `tests/unit/test_experiment_refutation_guard.py`: reproduce research.md
  R1's exact construction — a two-coupling-group `X`/`Z` fixture
  (`tau=0.5, r=1`), an under-determined (`M=22 < P=25`) ordinary
  least-squares fit on training points, with a component along the
  training sensing matrix's own null space added at `3x` the minimum-norm
  solution's magnitude (via SVD) to model a genuine overfitting artifact —
  confirm it looks suspiciously good at its own training points
  (`max |predicted-exact| < trotter_bound`), then confirm the
  generalization check run at a genuinely shifted point (never used in
  training) returns exactly `"refuted"`.
- [x] T007 [P] [US1] `test_true_model_generalizes` in
  `tests/unit/test_experiment_refutation_guard.py` — the positive control
  from research.md R1: a model built directly from the true oracle
  coefficients (no fitting, no artifact) returns exactly `"generalizes"`
  at the same shifted point used in T006, with `gap ≈ 0`. Kept as its own
  test function in the same file as T006 (both are the "does the guard
  actually discriminate" dedicated file) but never merged into one test —
  a single test asserting both outcomes could pass by accident if either
  half were broken independently.
- [x] T008 [P] [US1] `test_threshold_is_absolute_at_the_boundary` in
  `tests/unit/test_experiment_threshold.py` — reproduce research.md R2's
  three executed cases (gap at 99.9%, exactly 100%, and 100.1% of the
  model's own Trotter bound) as one parametrized test, asserting
  `"generalizes"` for the first two (the exact tie included, per the
  inclusive `<=` rule) and `"refuted"` for the third — no third,
  "inconclusive" outcome anywhere.
- [x] T009 [P] [US1] `test_generalization_check_does_not_mutate_report` in
  `tests/unit/test_experiment_immutability.py` (FR-003): capture every
  field of an `ErrorBoundingReport` before running the generalization
  check against it, run the check, and assert every field is identical
  (by value, not merely by the dataclass being frozen) afterward.
- [x] T010 [P] [US1] `test_weight_space_translation_status_never_changes`
  in `tests/unit/test_experiment_pac_rigidity.py` (FR-004): run the
  generalization check (both a `"generalizes"` case and a `"refuted"`
  case) and assert `report.pac_bound.weight_space_translation_status`
  still reads exactly `"out_of_scope_requires_sensing_matrix_conditioning"`
  after each — the empirical check never sets, upgrades, or otherwise
  touches this field.
- [x] T011 [US1] `test_shifted_input_never_coincides_with_training_input`
  in `tests/oracle/test_experiment_shift_leakage.py` (FR-009): construct a
  case where the shift-selection step would degenerate back onto a
  training input, and confirm this is rejected explicitly — mirroring
  Spec 5's own FR-005 leakage-check discipline (checked, never assumed).
- [x] T012 [P] [US1] `test_exact_dynamics_is_the_only_reference_importer`
  in `tests/unit/test_experiment_immutability.py` (FR-011's own scoping
  requirement): a structural test — `ast`-scan (or reuse
  `tests/ci/test_no_forbidden_imports.py`'s own `_scan_module`) confirms
  `experiment.py` itself does not import `fourierlearn.reference` at all,
  only `_exact_dynamics.exact_dynamics`.

### Implementation for User Story 1

- [x] T013 [US1] Create `src/fourierlearn/_exact_dynamics.py` (research.md
  R4): exactly one function,
  `exact_dynamics(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, alpha: tuple[float, ...]) -> float`,
  computing the exact expectation value at `alpha` from
  `fourierlearn.reference.coefficients(ir)`'s own exact Fourier
  coefficients (the same real-form reconstruction `fourierlearn.learn`
  already uses for `predict()` — reuse that reconstruction logic's
  *shape*, do not silently diverge from it). Module docstring states, in
  full sentences, that this is the only module besides `reference.py`
  authorized to import it, and names the one purpose (Constitution §8.2's
  generalization check) it exists for. **Nothing else lives in this
  file** (Guardrail #3, R4's isolation): no comparison logic, no verdict
  construction, no report handling.
- [x] T014 [US1] Create `src/fourierlearn/experiment.py` with
  `ShiftedInputResult`/`GeneralizationCheckResult` (or equivalently named)
  immutable dataclasses per spec.md's "Generalization check result" Key
  Entity: the shifted input used, the exact value (from T013), the
  model's prediction, the verdict, and the two always-`None` §11 attach
  fields (`containment_record`, `sparsity_mechanism` — User Story 3, not
  populated here).
- [x] T015 [US1] Implement `select_shifted_input(model, suspect_input, ...) -> tuple[float, ...]`
  in `experiment.py` (FR-001/FR-009): selects a classical input strictly
  shifted away from every training input the model used, and asserts —
  after selection — that it does not coincide with (or fall within
  leakage tolerance of) any training input, raising if it does (makes
  T011 pass).
- [x] T016 [US1] Implement `run_generalization_check(report, model, suspect_input=None) -> GeneralizationCheckResult`
  in `experiment.py` (FR-001, FR-002, FR-003, FR-004): calls
  `select_shifted_input` (T015), calls `_exact_dynamics.exact_dynamics`
  (T013) for the exact value, calls `fourierlearn.learn.predict` for the
  model's prediction, and computes the verdict via **exactly**
  `"generalizes" if abs(predicted - exact) <= model.trotter_bound_value else "refuted"`
  (research.md R2 — inclusive `<=`, no other branch, no
  "inconclusive"). MUST NOT read, construct, or return a new `PacBound`,
  and MUST NOT write back onto the `report` argument in any way (makes
  T009/T010 pass). Explicitly states the zero-Trotter-bound boundary case
  (spec.md Edge Cases) in the result when it occurs, without changing the
  deterministic verdict computed by the same inclusive rule.

**Checkpoint**: User Story 1 is fully functional and independently
testable — T006-T012 all pass, including the negative control (T006) and
its positive-control counterpart (T007).

---

## Phase 4: User Story 2 - Construct a physical model in its own domain vocabulary (Priority: P2)

**Goal**: Translate a TFIM graph-and-field description into Spec 2's
`CouplingGroup` input shape.

**Independent Test**: spec.md's own User Story 2 Independent Test.

### Tests for User Story 2 ⚠️

- [x] T017 [P] [US2] `test_tfim_uniform_coupling_produces_two_groups` in
  `tests/unit/test_models_tfim_construction.py` — **Guardrail #1 (R5
  sign-off)**: a 3-node path graph with a single, shared edge-coupling
  strength and a single field strength, constructed via the
  model-construction API's **default** call (no explicit per-edge
  labels), produces exactly two `CouplingGroup`s — one spanning all `ZZ`
  edge terms, one spanning all `X` field terms — matching the uniform
  TFIM Hamiltonian's own term structure hand-checked for this instance.
- [x] T018 [P] [US2] `test_tfim_heterogeneous_coupling_produces_one_group_per_label`
  in `tests/unit/test_models_tfim_construction.py` — **Guardrail #1 (R5
  sign-off)**: the same graph, but with the caller explicitly assigning a
  distinct group label to each edge, produces one `CouplingGroup` per
  edge (a random-bond TFIM variant) — confirming the default-vs-explicit
  behavior research.md R5 specifies, not merely the uniform case alone.
- [x] T019 [P] [US2] `test_tfim_isolated_node_succeeds` in
  `tests/unit/test_models_tfim_construction.py`: a graph with an isolated
  node (no edges) constructs successfully — a lone site under a
  transverse field is a valid, if trivial, instance (spec.md Edge Cases).
- [x] T020 [P] [US2] `test_tfim_rejects_zero_coupling` in
  `tests/unit/test_models_tfim_construction.py` (FR-006): a declared edge
  or field coupling of exactly `0.0` raises a clear, specific error at
  construction time, not a generic downstream rejection.

### Implementation for User Story 2

- [x] T021 [US2] Create `src/fourierlearn/models.py` with a
  `TFIMGraph`/`TFIMModel` (or equivalently named) input dataclass: sites,
  edges (each `(site_i, site_j, coupling_strength, group_label=None)`),
  and one field strength (`field_strength`, `field_group_label=None`).
- [x] T022 [US2] Implement `build_tfim_model(graph) -> PhysicalModelDescription`
  in `models.py` (FR-005, research.md R5's sign-off): groups edges by
  `group_label`, defaulting **all** edges lacking an explicit label to
  one shared default label (the uniform-coupling case, T017); groups
  under distinct explicit labels separately (T018); builds exactly one
  `CouplingGroup` per distinct resulting label for the `ZZ` edge terms,
  plus one separate `CouplingGroup` for the `X` field terms (defaulting
  to one shared field label unless the caller overrides it the same way).
  Raises on any zero coupling strength (T020, FR-006) before constructing
  any `CouplingGroup`.
- [x] T023 [US2] Add the optional `symmetry: SymmetryDeclaration | None = None`
  field (User Story 3's attach point, FR-007) to
  `PhysicalModelDescription` now, so T021/T022 do not need to be revisited
  when User Story 3 is implemented — populated with `None` by every code
  path in this story, never evaluated.

**Checkpoint**: User Stories 1 AND 2 both work independently — T017-T020
all pass.

---

## Phase 5: User Story 3 - Leave attach points for the symmetry-restricted research programme (Priority: P3)

**Goal**: Confirm the additive, inert §11 attach points behave exactly as
spec.md's Edge Cases and Acceptance Scenarios require — present, optional,
never evaluated.

**Independent Test**: spec.md's own User Story 3 Independent Test.

### Tests for User Story 3 ⚠️

- [x] T024 [P] [US3] `test_model_construction_unchanged_without_symmetry_declaration`
  in `tests/unit/test_models_symmetry_attach_point.py`: `build_tfim_model`
  called without any symmetry declaration behaves identically to before
  this attach point existed (same `CouplingGroup`s, same rejection
  behavior) — the field is additive, not a required parameter that
  changes existing behavior.
- [x] T025 [P] [US3] `test_symmetry_declaration_carried_through_unevaluated`
  in `tests/unit/test_models_symmetry_attach_point.py`: constructing a
  model *with* a symmetry declaration carries it through unchanged on the
  result, and raises neither an error nor any claim of having checked
  §11.1's three conditions against it.
- [x] T026 [P] [US3] `test_experiment_result_containment_and_sparsity_fields_always_none`
  in `tests/unit/test_experiment_immutability.py`: every
  `GeneralizationCheckResult` this feature's own suite produces (T006-T011)
  has `containment_record is None` and `sparsity_mechanism is None` — no
  code path in this spec ever populates either.

### Implementation for User Story 3

- [x] T027 [US3] Confirm (by code review, no new production logic beyond
  T014's field declarations and T023's field declaration) that
  `GeneralizationCheckResult.containment_record`/`.sparsity_mechanism` and
  `PhysicalModelDescription.symmetry` are the only three places §11-related
  data can be attached, and that no function in `experiment.py` or
  `models.py` reads or branches on any of them.

**Checkpoint**: All three user stories are independently functional —
T024-T026 all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 [P] Full suite: `pytest tests/ -q` → **158 passed** (Specs 1-6 together, up from 138 before this feature). `mypy src/fourierlearn/` → **Success: no issues found in 14 source files**.
- [x] T029 [P] Audit confirmed: `experiment.py` calls `fourierlearn.learn.predict` and `_exact_dynamics.exact_dynamics` exactly (grep-confirmed imports, no reimplementation of the real-form reconstruction anywhere in `experiment.py`); `models.py` calls `fourierlearn.encodings.trotter.CouplingGroup`/`CouplingGroupTerm` exactly, no fresh Pauli-term construction.
- [x] T030 [P] Confirmed by reading `experiment.py`, `models.py`, `_exact_dynamics.py`: zero `cache`/`lru_cache`/`batch`/`memo` hits (grep-confirmed). `models.py`'s group-by-label dict construction is a one-pass, non-cached grouping, not an optimization.
- [x] T031 [P] Confirmed by grep: `experiment.py`/`models.py` import neither `Statevector`/`Operator`/`expm` nor `fourierlearn.reference`; `_exact_dynamics.py` imports `fourierlearn.reference` and nothing else forbidden. `pytest tests/ci/test_no_forbidden_imports.py -v` → **7 passed** against the real `src/` tree with `_exact_dynamics.py` actually present.
- [x] T032 [P] **SC → test mapping**: SC-001 → `test_refutation_guard_detects_overfitting_artifact` + `test_true_model_generalizes`. SC-002 → `test_generalization_check_does_not_mutate_report`. SC-003 → `test_weight_space_translation_status_never_changes`. SC-004 → `test_tfim_uniform_coupling_produces_two_groups`. SC-005 → `test_model_construction_unchanged_without_symmetry_declaration` + `test_experiment_result_containment_and_sparsity_fields_always_none`. SC-006 → `test_exact_dynamics_is_the_only_reference_importer` + the CI guard's own 3 narrow-exemption tests. SC-007 → `test_narrow_exemption_does_not_widen_to_other_modules` + `test_narrow_exemption_still_rejects_statevector_and_operator`. All seven confirmed passing.

**Implementation-time correction recorded here**: while implementing T013 (`_exact_dynamics.py`), discovered that `fourierlearn.reference.coefficients(ir)` computes coefficients for `ir.observable` internally and has no separate observable parameter — but `exact_dynamics`'s own signature (matching `estimate_y`'s convention) takes `observable` as an explicit, separate argument. Passing a different `observable` than `ir.observable` would have silently computed the exact value for the wrong operator. Fixed by asserting `observable == ir.observable` inside `exact_dynamics`, raising `ValueError` on mismatch — verified this actually fires (see the module's own smoke test during implementation).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS User Story 1, because creating `_exact_dynamics.py` (US1) before the guard is updated would break every other spec's own passing CI-guard test, not just this feature's.
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on User Stories 2/3.
- **User Story 2 (Phase 4)**: Depends on nothing in User Story 1 — independently testable once Setup is done (does not need the CI guard change or `_exact_dynamics.py` at all).
- **User Story 3 (Phase 5)**: Depends on User Story 1's `GeneralizationCheckResult` (T014) and User Story 2's `PhysicalModelDescription` (T021) existing, to have fields to attach to — independently testable once both exist.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within User Story 1

- T013 (`_exact_dynamics.py`) has no dependency beyond Foundational (T002-T005).
- T014 (result dataclasses) has no dependency beyond Foundational.
- T015 (shift selection) depends on T014.
- T016 (the check itself) depends on T013, T014, T015.
- T006/T007 (negative/positive control) depend on T016 to actually pass (write-first, confirm-fail, then implement).
- T012 (structural "only importer" test) depends on T013/T016 existing as files to scan.

### Parallel Opportunities

- T003, T004 (independent CI-guard test additions) can run in parallel.
- T007, T008, T009, T010, T012 (independent US1 test files/functions) can run in parallel.
- T017-T020 (independent US2 test functions, same file but independent assertions) can be written in parallel.
- T024, T025, T026 (independent US3 assertions) can run in parallel.
- T028-T032 (Polish) can all run in parallel — independent audits.

---

## Parallel Example: User Story 1

```bash
# Tests, written first:
Task: "test_true_model_generalizes in tests/unit/test_experiment_refutation_guard.py"
Task: "test_threshold_is_absolute_at_the_boundary in tests/unit/test_experiment_threshold.py"
Task: "test_generalization_check_does_not_mutate_report in tests/unit/test_experiment_immutability.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational — CI guard update) → Phase 3 (User Story 1).
2. **STOP and VALIDATE**: T006-T012 all pass — the negative control (T006)
   correctly returns `refuted`, the positive control (T007) correctly
   returns `generalizes`, and the CI guard change (Foundational) is proven
   narrow before `_exact_dynamics.py` even exists.

### Incremental Delivery

1. Setup + Foundational → CI guard ready for the one exemption it will grant.
2. User Story 1 → validate independently → MVP (the generalization check actually resolves Spec 5's deferred flag).
3. User Story 2 → validate independently (TFIM construction, both uniform and heterogeneous coupling).
4. User Story 3 → validate independently (attach points present, inert, additive).
5. Polish.
