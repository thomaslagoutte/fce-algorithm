---

description: "Task list for the Learning Backend Layer"
---

# Tasks: Learning Backend Layer

**Input**: Design documents from `/specs/005-learning-backend-layer/` (spec.md, plan.md, research.md)

**Tests**: Included — this project's own established convention (Specs 1-4) is test-first, with dedicated, named tests per verified claim; this feature continues that convention.

**Organization**: Tasks are grouped by user story (spec.md: US1 P1, US2 P2, US3 P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)

## Path Conventions

Single Python library, matching Specs 1-4: `src/fourierlearn/`, `tests/unit/`, `tests/oracle/`.

---

## Phase 1: Setup

- [x] T001 Add `scikit-learn==1.8.0` to `pyproject.toml`'s `dependencies` and a `[[tool.mypy.overrides]] module = "sklearn.*" / ignore_missing_imports = true` entry (research.md R7/R12) — **already applied during `/speckit-plan`**; confirmed present and `sklearn.__version__ == "1.8.0"`.
- [x] T002 Created `src/fourierlearn/learn.py` with a module docstring citing FR-001..FR-015 and the two deliberately-separate verification classes (research.md R4 exact plumbing vs. R5 statistical recovery). **Implementation-time correction recorded here**: the docstring (and T012/T034 below) originally assumed `estimate_y`'s plain-circuit builder would import and reuse `fourierlearn.reference._build_circuit`. That is not actually possible: Spec 1's CI import guard (`tests/ci/test_no_forbidden_imports.py`) forbids *every* production module other than `reference.py` itself from importing `fourierlearn.reference` at all (confirmed by reading the guard's own source, not assumed). The module docstring was corrected to say so, and `_plain_forward_circuit` was implemented as its own independently-defined function in `learn.py` — structurally identical to `reference.py`'s internal loop, reusing the real shared logic (`PauliTerm.to_gate()`/`FixedGate`) rather than reimplementing it, but not literally importing `reference.py`.

**Checkpoint**: Setup complete.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one shared, typed cross-layer interface every story's implementation sits behind (Constitution §9.2's own named extension point in `contracts.py`) — must exist before any story's implementation task references it.

- [x] T003 Add a `RegressionBackend` `Protocol` to `src/fourierlearn/contracts.py` (Constitution §9.2's own "later specs add their own Protocol classes to this same module for their own boundary" extension point) — a `fit(A: np.ndarray, y: np.ndarray) -> np.ndarray` method returning the fitted real-stacked coefficient vector, documented as the Extract→Learn boundary this feature's `LassoRegressionBackend` (T014) satisfies. Do **not** modify the existing `Encoding`/`Oracle` Protocols.

**Checkpoint**: Foundation ready — User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 - Learn a sparse Hamiltonian model from few expectation-value measurements (Priority: P1) 🎯 MVP

**Goal**: Estimate `y(alpha)` at concrete inputs via a new, genuinely simpler finite-shot primitive (FR-014), build the real Fourier sensing matrix (FR-015), and recover the sparse Fourier-coefficient vector via `LassoCV` from `M << L` measurements (FR-001..FR-006, FR-012, FR-013).

**Independent Test**: spec.md's own User Story 1 Independent Test — build a small circuit from a Hamiltonian with known sparse structure, measure `y(alpha)` at `M` random concrete inputs with `M` strictly fewer than the representable frequency count, fit, and confirm recovery of the known-active frequencies.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; confirm they FAIL before the corresponding implementation task.

- [x] T004 [P] [US1] `test_fr014_circuit_is_structurally_simpler` in `tests/unit/test_learn_y_primitive.py` — reproduce research.md R2's circuit-simplification assertion: `estimate_y`'s internal circuit-builder has strictly fewer qubits than `compile_observable_circuit`'s output on the mandated fixture (Spec 3 research.md R8), and its instruction-name set contains zero `cx`/controlled-increment-style gates present in `compile_observable_circuit`'s output — proving a genuinely simpler construction, not an identity-shift `V_l` (planning mandate #2, prior round).
- [x] T005 [P] [US1] `test_fr014_exact_value_matches_direct_expectation` in `tests/unit/test_learn_y_primitive.py` — reproduce research.md R2's exact cross-check: at several concrete `alpha` values, the Hadamard-test-ancilla circuit's exact (`Statevector`, test-only) value matches `fourierlearn.reference._build_circuit` + `Statevector.expectation_value(observable).real` to within `1e-10`, and its imaginary part is `~0` at every tested `alpha`. This test file imports `Statevector` for verification only — never `estimate_y` itself, which MUST be shot-based (T013).
- [x] T006 [US1] `test_fr006_end_to_end_exact_round_trip` in `tests/unit/test_learn_design_matrix.py` — reproduce research.md R4 **exactly**: an exactly-determined system (`M >= P`, ordinary least squares, **no LASSO**) on the mandated fixture — bind `alpha` → exact `y` → build the real sensing matrix (T011) → solve → reconstruct complex `b` (T012) → compare to `fourierlearn.reference.coefficients`, asserting `max |error| < 1e-8`. **This test file and this test function MUST NOT also contain, or be merged with, the statistical sparse-recovery test (T007) — they are dedicated, separate test tasks per this round's explicit guardrail.**
- [x] T007 [US1] `test_fr006_end_to_end_negative_control_sign_flip` in `tests/unit/test_learn_design_matrix.py` — reproduce research.md R4's negative control: flipping the sign convention of every sensing-matrix `Im` column (`-sin` → `+sin`) must be **detected** (reconstructed vector no longer matches the oracle) — proving T006 is not vacuous. Same file as T006 (both are the "exact plumbing" dedicated test file), but a distinct test function.
- [x] T008 [US1] `test_sc001_statistical_sparse_recovery` in `tests/unit/test_learn_sparse_recovery.py` — reproduce research.md R5 **exactly, in its own dedicated file, never merged with T006/T007**: a *different*, deliberately wider/sparser fixture (`L=25`, 2 genuinely nonzero canonical frequencies), `M=9 << P=25` random `alpha` samples, exact (noiseless) `y`, real `LassoCV` fit (T014) on an explicit pinned `alphas` grid, asserting `max |error|` on the active frequency `< 0.05` and `max |recovered value|` on every inactive frequency `< 0.05`.
- [x] T009 [P] [US1] `test_learn_fit_is_deterministic_given_seed` in `tests/unit/test_learn_fit.py` — fit the same training set twice with the same seed; assert bit-identical fitted coefficient vectors (FR-012, User Story 1 Acceptance Scenario 4).
- [x] T010 [P] [US1] `test_learn_rejects_non_hermitian_observable`, `test_learn_predict_is_real_for_hermitian_observable`, `test_learn_asserts_zero_train_eval_overlap`, `test_learn_under_determined_regime_does_not_raise` in `tests/unit/test_learn_fit.py` — four independent test functions (do not merge): FR-006's Hermiticity rejection, FR-006's conjugate-symmetry-enforced real prediction, FR-005's post-split leakage assertion (build a split, mutate it to force an overlap, confirm the assertion fires — reachability, not merely defense-in-depth, mirroring Spec 4's own reachability discipline), and FR-002's "never raises for `M < L`" guarantee.
- [x] T011 [US1] `test_tau_tolerance_cases` and `test_heterogeneous_trotter_config_rejected` in `tests/unit/test_learn_trotter_config.py` — reproduce research.md R6's six `tau`/`r` cases (same-tau-different-derivation, accumulated rounding, genuine mismatch, near-zero boundary, exact-`r`-equality) as one test function, and a second, independent test function that fits on two rows sharing `tau` but differing `r` (and vice versa) and confirms rejection (FR-013, SC-007).

### Implementation for User Story 1

- [x] T012 [US1] Implement `estimate_y(ir, observable, alpha, shots, seed=None) -> tuple[float, int]` in `src/fourierlearn/learn.py` (FR-014): build the plain forward circuit directly from `ir.gates` (reusing `PauliTerm.to_gate()`/`FixedGate` exactly as `fourierlearn.reference._build_circuit` already does — import and reuse that function, do not reimplement it), fold the observable via `fourierlearn.circuits._insert_observable`/`basis_change_gates` (reused unchanged), bind `alpha` via `assign_parameters`, wrap in one Hadamard-test ancilla (`H`, controlled-`[forward; observable; forward.inverse()]`, `H`), measure only the real part (`P(0) - P(1)`; no `Sdg`/imaginary sub-circuit — research.md R2 confirmed the imaginary part is exactly zero for this construction). Production path MUST use `AerSimulator.run()` + `get_counts()` with `transpile()` first (Constitution Article II/§9.6) — `Statevector` MUST NOT appear in this function. Depends on T003 not existing as a blocker (no Protocol dependency here); makes T004/T005 pass.
- [x] T013 [US1] Implement `_stack_real(coefficients: dict, canonical: list) -> np.ndarray` and `_reconstruct_complex(x: np.ndarray, canonical: list) -> dict` in `src/fourierlearn/learn.py` (FR-006): the real/imaginary stacking-and-reconstruction convention research.md R2 (prior round) and R4 (this round, end-to-end) already verified — DC gets one `Re` column, every other canonical frequency gets `(Re, Im)` columns in that fixed order; reconstruction derives every mirrored frequency via `.conjugate()`. Reuse `fourierlearn.extract._is_canonical_representative` for the canonical-frequency selection (Constitution §9.4) — do not reimplement it.
- [x] T014 [US1] Implement `build_sensing_matrix(alphas: np.ndarray, canonical: list, coefficients: tuple[float, ...]) -> np.ndarray` in `src/fourierlearn/learn.py` (FR-015): `A[j, k] = 1.0` for the DC column; `2*cos(pi*l*coefficient*alpha_j)` for a `Re` column; `-2*sin(pi*l*coefficient*alpha_j)` for an `Im` column — the exact real-form derivation research.md R3 derives from `fourierlearn.reference`'s own DFT/grid convention (not an independently invented formula). `coefficient` is the per-parameter structural scale factor already carried by `PauliTerm.coefficient` (§6.4) — for the single-parameter case this reduces to `coefficient=1.0`.
- [x] T015 [US1] Implement `LassoRegressionBackend` (satisfying T003's `RegressionBackend` Protocol) in `src/fourierlearn/learn.py`: wraps `sklearn.linear_model.LassoCV(alphas=<pinned module-level constant grid>, cv=min(K_DEFAULT, M), fit_intercept=False, random_state=seed, selection="cyclic")` — `fit_intercept=False` because the DC column already carries the constant term (T014); `K_DEFAULT` is a pinned module-level constant (e.g. `5`), and `cv` is capped at the actual row count `M` only as a mechanical `LassoCV` fold-count requirement, never a refusal to fit for `M < L` (FR-002).
- [x] T016 [US1] Implement `fit_model(ir, observable, alphas, shots, seed=None, budget=..., confirm=False) -> LearnedModel` in `src/fourierlearn/learn.py` (FR-001, FR-005, FR-006, FR-012): reject a non-Hermitian `observable` before any measurement (FR-006); call `estimate_y` (T012) once per `alpha` in the training set; build the sensing matrix (T014); fit via `LassoRegressionBackend` (T015); reconstruct the complex coefficient dict (T013). Given an explicit `(train_alphas, eval_alphas)` split, assert — after the split, not before — zero set overlap (FR-005), raising if violated. Seeded end-to-end; writes a run manifest (config, library versions, timings) beside its return value (FR-012, Constitution §8.5).
- [x] T017 [US1] Implement `predict(model: LearnedModel, alpha: float) -> float` in `src/fourierlearn/learn.py` (FR-006): rebuilds `y(alpha)` from the fitted real-stacked vector via the same real-form basis T014 uses (never re-measures a circuit) and asserts the imaginary contribution is structurally absent by construction (the real-form basis has no imaginary output path at all, not merely a numerically-small one).
- [x] T018 [US1] Implement the `tau`/`r` homogeneity guard in `src/fourierlearn/learn.py` (FR-013): module-level constants `_TAU_REL_TOL = 1e-9`, `_TAU_ABS_TOL = 1e-12` (research.md R6, named constants — not inline magic numbers, so T011's tests can assert against the exact pinned values); a `_same_trotter_config(tau_a, r_a, tau_b, r_b) -> bool` helper using `math.isclose(tau_a, tau_b, rel_tol=_TAU_REL_TOL, abs_tol=_TAU_ABS_TOL) and r_a == r_b`; `fit_model` (T016) calls this across every training row's declared `(tau, r)` and raises a clear, named error on the first mismatch.

**Checkpoint**: User Story 1 is fully functional and independently testable — T004-T011 all pass.

---

## Phase 4: User Story 2 - Report PAC and Trotter error as two independent bounds (Priority: P2)

**Goal**: An error-bounding report with the PAC bound and Trotter bound as two permanently separate figures (FR-007, FR-008, FR-010, FR-011), a policy-only "generalization check required" flag (FR-009), and — this round's central guardrail — the PAC bound strictly labeled as a per-measurement statistical noise bound, never a fitted-model weight-space error bound.

**Independent Test**: spec.md's own User Story 2 Independent Test — a model whose feature map has a known, deliberately coarse Trotter step; request the report; confirm the two bounds are separately labeled, separately computed, and the report states what it does/does not establish.

### Tests for User Story 2 ⚠️

- [x] T019 [P] [US2] `test_error_report_labels_pac_bound_as_measurement_noise_not_weight_error` in `tests/unit/test_learn_error_report.py` — **this round's PAC-bound truth-in-labeling guardrail**: assert the report's PAC-bound field name/label is exactly `"per_measurement_statistical_noise_bound"` (not `"model_error"`, `"weight_error"`, or any name implying it bounds the fitted coefficient vector); assert a `weight_space_translation_status` field (or equivalent) is present and equals a fixed sentinel value such as `"out_of_scope_requires_sensing_matrix_conditioning"`; assert the report's own docstring/`__repr__`/textual summary contains the literal phrase "per-measurement statistical noise bound" and does **not** contain any phrase asserting a bound on "model weights," "fitted coefficients," or "the learned model" in connection with this figure.
- [x] T020 [P] [US2] `test_error_report_never_combines_pac_and_trotter` in `tests/unit/test_learn_error_report.py` — generate several reports across different fixtures/shot counts/Trotter configs; assert no single combined/blended/ratio figure exists anywhere in the report's fields or its textual summary (FR-008).
- [x] T021 [P] [US2] `test_error_report_flags_generalization_check_without_resolving_it` in `tests/unit/test_learn_error_report.py` — construct a case where the model's agreement with exact dynamics exceeds its own Trotter bound; assert `generalization_check_required=True` and a named `suspect_input`; assert **no** code path in `learn.py` calls, imports, or stubs a shifted-parameter-dynamics mechanism (FR-009's policy-only scope, out of scope: Spec 6).
- [x] T022 [US2] `test_pac_bound_reads_only_measurement_inputs`, `test_trotter_bound_reads_only_feature_map_inputs` in `tests/oracle/test_learn_pac_vs_trotter.py` — two independent test functions asserting, via direct inspection of each bound function's signature/behavior, that the PAC bound computation never reads `tau`/`r`/Trotter order and the Trotter bound computation never reads `shots`/sample count/`delta` (FR-007's input-isolation requirement, in both directions).
- [x] T023 [US2] `test_trotter_bound_diverges_from_pac_bound_on_coarse_step` in `tests/oracle/test_learn_pac_vs_trotter.py` — a deliberately coarse Trotter configuration produces a Trotter bound clearly larger than the PAC bound at a realistic shot count, and the report attributes the residual gap to the dominant (Trotter) bound rather than a blended figure (FR-007 Acceptance Scenario 2).

### Implementation for User Story 2

- [x] T024 [US2] Implement `PacBound` as its own small, explicitly-named type in `src/fourierlearn/learn.py` (**PAC bound truth-in-labeling, Option A — this round's central guardrail**): field name `per_measurement_statistical_noise_bound: float`, computed as `sqrt(2 * ln(2*M/delta) / shots)` (research.md R8) from `shots`, `M` (measured-row count), and `delta` only. Include a field `weight_space_translation_status: str = "out_of_scope_requires_sensing_matrix_conditioning"` on the SAME returned object (not just in a docstring) recording that translating this per-measurement bound into a bound on the fitted coefficient vector requires the sensing matrix's conditioning (research.md R8) and is explicitly not implemented here. **Code comment requirement**: a `# TODO(out-of-scope):` comment directly above this type's definition states, in full sentences, that this bound is per-measurement label noise, not a weight-space error bound, and that the translation is future work requiring the sensing matrix's condition number — matching the report object's own field, not merely restating it once.
- [x] T025 [US2] Implement `TrotterBound` as its own small, explicitly-named type in `src/fourierlearn/learn.py`: `structural_approximation_bound: float`, computed as `(tau**2 / r) * sum(...)` (research.md R9, first-order Lie-Trotter) from `tau`, `r`, and the declared Hamiltonian term weights/commutators only.
- [x] T026 [US2] Implement `error_bounding_report(model: LearnedModel, ...) -> ErrorBoundingReport` in `src/fourierlearn/learn.py` (FR-007, FR-008, FR-010, FR-011): composes `PacBound` (T024) and `TrotterBound` (T025) as two separate fields, never combined into any blended figure anywhere in the returned object or its `__repr__`; adds a `noise_characterization` field as a third, independent axis (FR-010); adds a `scope_statement: str` field stating explicitly what the report does and does not establish (FR-007 Acceptance Scenario 4); computes both bounds' constants once globally over the whole training set (FR-011), never per individual row.
- [x] T027 [US2] Implement the `generalization_check_required`/`suspect_input` policy flag on `ErrorBoundingReport` in `src/fourierlearn/learn.py` (FR-009): set when the model's measured agreement with exact dynamics is closer than `TrotterBound.structural_approximation_bound` permits; MUST NOT call, import, or reference any shifted-parameter-dynamics execution mechanism — that remains entirely unimplemented here (Spec 6, out of scope).

**Checkpoint**: User Stories 1 AND 2 both work independently — T019-T023 all pass, with zero blended PAC/Trotter figures and the PAC bound's label unambiguous.

---

## Phase 5: User Story 3 - Guard against the penalty-anchoring bug (Priority: P3)

**Goal**: The regularization penalty grid and its cross-validation selection are provably invariant to shot count and Trotter evolution time (FR-003, FR-004, SC-002 — the "$t^2$-penalty bug" guardrail).

**Independent Test**: spec.md's own User Story 3 Independent Test — fit twice at two different shot counts with the grid/CV procedure held fixed; confirm the grid and procedure are identical between runs, not merely that the selected penalties happen to match.

### Tests for User Story 3 ⚠️

- [x] T028 [P] [US3] `test_penalty_grid_and_cv_procedure_are_shot_count_invariant` in `tests/unit/test_learn_penalty_integrity.py` — fit on the same `(alpha_j)` inputs at a small shot count and a much larger shot count (hence different label noise); assert `LassoRegressionBackend`'s configured `alphas` grid object and `cv` fold count are identical (by value, and — since T029 pins the grid as a module-level constant — by identity) between the two calls, not merely that the two selected `alpha_` values happen to match (FR-004's own stronger requirement).
- [x] T029 [P] [US3] `test_penalty_selection_reads_only_training_data` in `tests/unit/test_learn_penalty_integrity.py` — directly inspect `fit_model`/`LassoRegressionBackend`'s call signature and source to confirm neither the penalty grid construction nor the CV selection call ever receives `shots`, `tau`, or `r` as an argument (FR-003/FR-004's input-isolation requirement, verified structurally, not just by outcome).
- [x] T030 [US3] `test_held_out_input_never_influences_penalty_selection` in `tests/unit/test_learn_penalty_integrity.py` — fit with and without a held-out evaluation input present in scope; assert the selected penalty and fitted coefficients for the training-only case are unaffected by the held-out input's mere presence (FR-003 Acceptance Scenario 3, US3 Acceptance Scenario 3).

### Implementation for User Story 3

- [x] T031 [US3] Pin the regularization grid as a module-level constant `_ALPHA_GRID = np.geomspace(1e-4, 1.0, 30)` (or equivalent explicit, version-committed array — research.md R5's own executed grid) in `src/fourierlearn/learn.py`, referenced by `LassoRegressionBackend` (T015) — never constructed from `shots`, `tau`, `r`, or any other non-training-data quantity, and never regenerated per call (same object reused, so T028's identity check is meaningful).
- [x] T032 [US3] Confirm (by code review, no new production code) that `fit_model` (T016) never threads `shots`/`tau`/`r` into `LassoRegressionBackend.fit()`'s call — only the sensing matrix `A` and measured `y` — closing the "$t^2$-penalty bug" path structurally, not merely by convention.

**Checkpoint**: All three user stories are independently functional — T028-T030 all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T033 [P] Full suite: `pytest tests/ -q` → **137 passed** (Specs 1-5 together, up from 115 before this feature). `mypy src/fourierlearn/` → **Success: no issues found in 11 source files** (after parametrizing `npt.NDArray[np.float64]` in both `contracts.py` and `learn.py`, and adding the missing `import numpy as np` to `contracts.py` — both genuine type-annotation gaps, not design changes).
- [x] T034 [P] Audit confirms zero duplicated logic — **corrected from the task's own original wording** (see T002's note): `estimate_y` cannot call `fourierlearn.reference._build_circuit` at all (CI guard forbids it). It instead reuses the same underlying gate-construction primitives (`PauliTerm.to_gate()`, `FixedGate`) directly, plus `fourierlearn.circuits._insert_observable` (imported and reused unchanged) — confirmed by reading `learn.py` end to end: no second implementation of Pauli-rotation-gate construction or observable-folding exists anywhere in the file.
- [x] T035 [P] Confirmed by reading `learn.py`: no caching, batching, or memoization anywhere. One deliberate addition beyond the original plan: `LassoCV(..., max_iter=10_000)` (default is `1000`) — added because the default was tripping `ConvergenceWarning`s on this feature's own under-determined test fixtures. This is a convergence-correctness fix (ensuring the solver actually reaches its optimum before returning), not a performance optimization, and required no profiling per §5.3's own scope (§5.3 governs *performance* optimizations, not numerical-convergence parameters).
- [x] T036 [P] Confirmed by reading `learn.py`: zero `Statevector`/`Operator`/`expm` imports. `pytest tests/ci/test_no_forbidden_imports.py -v` → **4 passed**, zero violations for `learn.py`, guard unmodified.
- [x] T037 [P] **SC → test mapping**: SC-001 → `test_sc001_statistical_sparse_recovery` (`test_learn_sparse_recovery.py`). SC-002 → `test_penalty_grid_and_cv_procedure_are_shot_count_invariant` (`test_learn_penalty_integrity.py`). SC-003 → `test_error_report_never_combines_pac_and_trotter` (`test_learn_error_report.py`). SC-004 → `test_error_report_flags_generalization_check_without_resolving_it` (`test_learn_error_report.py`). SC-005 → `test_learn_asserts_zero_train_eval_overlap` (`test_learn_fit.py`). SC-006 → `test_learn_rejects_non_hermitian_observable` + `test_learn_predict_is_real_for_hermitian_observable` + `test_learn_predict_is_structurally_real` (`test_learn_fit.py`) + `test_fr006_end_to_end_exact_round_trip` (`test_learn_design_matrix.py`). SC-007 → `test_heterogeneous_trotter_config_rejected` (`test_learn_trotter_config.py`). All seven confirmed passing.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS User Story 1 (the `RegressionBackend` Protocol T015 satisfies).
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on User Stories 2/3.
- **User Story 2 (Phase 4)**: Depends on User Story 1's `LearnedModel`/`fit_model` existing (an error-bounding report is generated *from* a fitted model) — but is independently testable once US1 is done.
- **User Story 3 (Phase 5)**: Depends on User Story 1's `fit_model`/`LassoRegressionBackend` existing (there is otherwise no regularization parameter to guard) — independently testable once US1 is done.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within User Story 1

- T004, T005 (US1 primitive tests) can run in parallel with each other; both depend on T012 to actually pass (write-first, confirm-fail, then implement).
- T006, T007 (exact plumbing) depend on T013 (stacking) and T014 (sensing matrix).
- T008 (statistical recovery) depends on T014 (sensing matrix) and T015 (`LassoRegressionBackend`) — kept in its own file, never merged with T006/T007.
- T016 (`fit_model`) depends on T012, T013, T014, T015, T018.
- T017 (`predict`) depends on T013, T016.

### Parallel Opportunities

- T004, T005, T009, T010 (different concerns, same or independent files) can be written in parallel.
- T019, T020, T021 (independent report-shape assertions) can run in parallel.
- T028, T029 (independent structural assertions) can run in parallel.
- T033-T037 (Polish) can all run in parallel — independent audits.

---

## Parallel Example: User Story 1

```bash
# Tests, written first:
Task: "test_fr014_circuit_is_structurally_simpler in tests/unit/test_learn_y_primitive.py"
Task: "test_fr014_exact_value_matches_direct_expectation in tests/unit/test_learn_y_primitive.py"
Task: "test_learn_fit_is_deterministic_given_seed in tests/unit/test_learn_fit.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (User Story 1).
2. **STOP and VALIDATE**: T004-T011 all pass independently — the new `y(alpha)` primitive is genuinely simpler than Spec 4's circuit, the exact plumbing (T006/T007) and the statistical recovery (T008) are separately verified, never conflated.

### Incremental Delivery

1. Setup + Foundational → Foundation ready.
2. User Story 1 → validate independently → MVP.
3. User Story 2 → validate independently (PAC bound correctly labeled, never blended with Trotter).
4. User Story 3 → validate independently (penalty grid/CV provably shot-count-invariant).
5. Polish.
