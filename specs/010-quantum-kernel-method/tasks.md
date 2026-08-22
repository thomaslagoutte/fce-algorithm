---

description: "Task list for Quantum Kernel Method for FCE (Spec 10)"
---

# Tasks: Quantum Kernel Method for FCE (PAC-Efficient Regime)

**Input**: Design documents from `/specs/010-quantum-kernel-method/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md)

**Tests**: Included — this project's own established convention (every prior
spec) is tests-before-code with an oracle/unit split, and spec.md's own
Acceptance Scenarios are stated as verifiable claims, not aspirations.

**Organization**: Tasks are grouped by user story (US1/US2/US3, matching
spec.md's P1/P2/P3 priorities).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (kernel overlap circuit), US2 (KRR + noisy variant +
  `NoisyKRRBound`), US3 (cancellation/PAC-efficiency demonstration)

## Path Conventions

Single project (per plan.md's Structure Decision): `src/fourierlearn/`,
`tests/unit/`, `tests/oracle/`.

---

## Phase 1: Setup

- [x] T001 Create `src/fourierlearn/kernel.py` with a module docstring only
      (`"""kernel.py: Gram-matrix assembly and (noisy) kernel ridge
      regression, Spec 10."""`) — no logic yet, per plan.md's Project
      Structure. No other setup is needed: this feature adds no new
      dependency and no new top-level directory.

---

## Phase 2: Foundational (Blocking Prerequisites)

**None required.** Every primitive each user story below builds on already
exists and is already validated: `circuits.compile_frequency_circuit`,
`circuits.compile_observable_circuit` (Spec 9's LCU branch),
`ir.PauliTerm`/`ir.FixedGate`/the IR builder (Spec 1),
`reference.coefficients`/`reference.amplitude_coefficients` (Specs 1, 9),
and `extract.estimate_coefficient` (Spec 4). Nothing new is shared-and-
blocking across US1/US2/US3, so no tasks are listed in this phase.

---

## Phase 3: User Story 1 - Evaluate k(x,x')=b(x)·b(x') (Priority: P1) 🎯 MVP

**Goal**: A selector-qubit-based overlap circuit that reuses
`compile_frequency_circuit` unmodified as `A(U)` and reads out
`Re(⟨b(x)|b(x')⟩)` (FR-001/FR-002).

**Independent Test**: Build the circuit for a concrete `x, x'` pair, compare
its readout against an independently-computed `Re(⟨b(x)|b(x')⟩)` — already
verified once (Finding 2, diff `5.6e-16`, 1-qubit/1-parameter fixture);
this phase reproduces that as a permanent test and extends it to a richer
fixture per spec.md's own Assumptions.

### Tests for User Story 1

- [x] T002 [P] [US1] Oracle regression test in
      `tests/oracle/test_circuits_kernel_overlap_circuit.py`: reproduce the
      already-verified 1-qubit/1-parameter fixture (`RY(0.9)` vs `RY(1.7)`
      as the `x`/`x'` fixed gates) and assert the compiled circuit's
      `Z_selector⊗I⊗|0⟩⟨0|_circuit` expectation matches
      `reference.kernel_overlap_oracle`'s `Re(⟨b(x)|b(x')⟩)` to
      `abs_tol=1e-9` (FR-002 Acceptance Scenario 2).
- [x] T003 [US1] Same file: add the RICHER fixture spec.md's own
      Assumptions require before this construction is "trusted generally"
      — a ≥2-qubit/2-parameter IR pair AND a case where the folded
      observable is a weighted Pauli sum reused via Spec 9's
      `compile_observable_circuit` LCU branch (FR-003) — asserting the same
      machine-precision match against `reference.kernel_overlap_oracle`.

### Implementation for User Story 1

- [x] T004 [P] [US1] Add `kernel_overlap_oracle(ir_x, ir_x_prime,
      observable=None) -> complex` to `src/fourierlearn/reference.py`
      (new section, "Spec 10 deliverable (a)"), computing
      `Re(⟨b(x)|b(x')⟩)` from two independent calls to the existing
      `_evaluate_grid_amplitude`-based machinery — oracle-only, per
      Constitution §3.3/§3.4 (never imported by production code).
- [x] T005 [US1] Implement `compile_kernel_overlap_circuit(ir_x,
      ir_x_prime, observable=None) -> QuantumCircuit` in
      `src/fourierlearn/circuits.py`: selector qubit prepared into `|+⟩`,
      selector-controlled preparation of `ir_x`'s vs `ir_x_prime`'s own
      fixed gates, then the shared, UNMODIFIED `compile_frequency_circuit`
      call applied unconditionally on top (FR-001) — must make T002 pass
      before T003's richer fixture is attempted.
- [x] T006 [US1] Add the eq. 5.78 readout (`Z_selector⊗I⊗|0⟩⟨0|_circuit`
      expectation, computed via exact statevector in the test helper only)
      wired into T002/T003 — depends on T004, T005.
- [x] T007 [US1] Finite-shot extension check: determine whether Spec 4's
      `extract.estimate_coefficient`/`extract._hadamard_test_circuit` is
      directly reusable for a shot-based estimate of this circuit's
      `Z⊗I⊗|0⟩⟨0|` observable. If yes, add the minimal wrapper in
      `src/fourierlearn/circuits.py` or `src/fourierlearn/extract.py`. If
      not directly reusable, do NOT silently omit it — add a named
      `# TODO(Spec 10, Constitution §4.7)` comment at
      `compile_kernel_overlap_circuit` documenting exactly what is
      missing and why, mirroring Spec 9's own EXT-003 precedent, and
      record the same TODO in `.specify/memory/extension-register.md`
      under EXT-002.
- [x] T008 [P] [US1] Scope-discipline regression test (FR-004) in
      `tests/unit/test_kernel_scope_discipline.py`: assert
      `compile_kernel_overlap_circuit`'s signature and behavior only ever
      accept two classical-input declarations (`ir_x`, `ir_x_prime`
      differing solely in fixed-gate choice, sharing the same
      encoded-parameter structure) — there is no code path through which
      two differently-*encoded* (`α`-varying) IRs would be silently
      treated as a fidelity kernel over `α`.

**Checkpoint**: User Story 1 is independently functional and tested.

---

## Phase 4: User Story 2 - KRR with an honest noisy-bound sentinel (Priority: P2)

**Goal**: Gram-matrix construction, noiseless KRR, and the noisy-KRR
variant (eq. 5.79-5.94) whose every prediction carries a `NoisyKRRBound`
with a `tightness_status` computed dynamically from the live problem
instance (research.md R1/R2, and this round's Critical Guardrails 1-2).

**Independent Test**: A hand-constructed regression problem's exact KRR
prediction is reproduced in closed form; the noisy variant's bound is
never violated across the reproduced 500-trial sweep (Finding 3); the
`tightness_status` sentinel demonstrably transitions with shot count on
one fixed instance (Guardrail 2, T018 below).

### Tests for User Story 2

- [x] T009 [P] [US2] Unit test in `tests/unit/test_kernel_gram_matrix.py`:
      assert Gram-matrix construction issues exactly `O(T²)` calls to
      User Story 1's overlap evaluation (FR-005 Acceptance Scenario 1) —
      e.g. via a call-counting stub substituted for
      `compile_kernel_overlap_circuit`'s readout.
- [x] T010 [P] [US2] Unit test in
      `tests/unit/test_kernel_krr_noiseless.py`: exact KRR solve on a
      small hand-constructed problem, checked against closed-form ridge
      regression computed independently (plain NumPy, not the module
      under test).
- [x] T011 [P] [US2] Unit test in
      `tests/unit/test_kernel_noisy_bound_formula.py`: reproduce Finding
      3's generic-noise 500-trial sweep as a PERMANENT regression test
      (not an ad hoc script) — assert zero violations of eq. 5.94 and
      report the max observed `lhs/rhs` ratio.
- [x] T012 [P] [US2] Unit test in
      `tests/unit/test_kernel_dynamic_tightness_ratio.py` (**Critical
      Guardrail 1**): construct two problem instances with the SAME
      numerical `error_bound` but deliberately different signal
      magnitudes (e.g. `Y` and `Y_scaled = 10·Y`, everything else held
      fixed) and assert `bound_to_reference_ratio` and `tightness_status`
      differ between the two calls — proving the ratio is computed from
      each call's own live signal magnitude, never a constant carried
      over from research.md R1's Phase-0 numbers.
- [x] T013 [US2] Unit test in
      `tests/unit/test_kernel_noisy_bound_tightness.py`: reproduce
      research.md R1's exact three-shot-count sweep (`2,000`/`20,000`/
      `200,000` shots, `δ=0.01`, using this project's own
      `sqrt(2·ln(2/δ)/shots)` Hoeffding formula, reused verbatim — never
      a new tolerance formula) and assert the resulting
      `tightness_status` values match R1's own qualitative finding at
      each scale.
- [x] T014 [US2] **Sentinel transition test (Critical Guardrail 2)** in
      `tests/unit/test_kernel_tightness_transition.py`: construct ONE
      FIXED problem instance (same `T`, `d`, `λ₀`, `κ`, and signal
      magnitude) and call the noisy-KRR path on it TWICE — once with
      `ε_k=ε_y` set to the `2,000`-shot Hoeffding value (`0.07279`) and
      once with the `200,000`-shot value (`0.00728`), all other inputs
      identical — and assert `tightness_status` is exactly `"vacuous"`
      in the first call and exactly `"informative"` in the second,
      isolating shot count as the only varying input across the two
      calls.
- [x] T015 [P] [US2] Unit test in
      `tests/unit/test_kernel_bound_missing_inputs.py` (FR-008): assert
      the noisy-KRR path reports an explicit, structured error/sentinel —
      never a silently-computed negative or nonsensical bound — when any
      of `ε_k, ε_y, λ₀, κ, M` is missing or non-positive.

### Implementation for User Story 2

- [x] T016 [US2] Implement `build_gram_matrix(pairs) -> np.ndarray` and
      `krr_fit_predict(K, Y, lambda0, k_test_row) -> float` (noiseless
      path) in `src/fourierlearn/kernel.py`, satisfying T009-T010.
- [x] T017 [US2] Implement the noisy-KRR path in `kernel.py`:
      `noisy_krr_predict(K_hat, Y_hat, F_hat, eps_k, eps_y, lambda0,
      kappa, M) -> tuple[float, NoisyKRRBound]`, including a documented
      PSD-correction step for `K̂` (a plan-level decision — cite the
      specific method chosen, e.g. eigenvalue clipping, in a code comment
      referencing the thesis's own citation [167] for eq. 5.94's context)
      and eq. 5.94's rhs computation (FR-006/FR-007) — satisfies T011.
- [x] T018 [US2] Implement the `NoisyKRRBound` dataclass in `kernel.py`
      per research.md R2: `error_bound`, `reference_magnitude`,
      `bound_to_reference_ratio`, `tightness_status`, `epsilon_k`,
      `epsilon_y`, `lambda0`, `kappa` — `tightness_status` a REQUIRED,
      always-populated field (never `Optional`), mirroring `learn.py`'s
      `PacBound.weight_space_translation_status` non-optional-field
      pattern exactly.
- [x] T019 [US2] **Dynamic tightness-threshold implementation (Critical
      Guardrail 1)**: implement `reference_magnitude` and
      `bound_to_reference_ratio` inside `noisy_krr_predict` as PER-CALL
      computed quantities derived from THIS call's own predicted-value
      magnitude (`abs(predicted_value)`, falling back to `norm(Y_hat)`
      only if the predicted value is exactly zero — document this
      fallback explicitly) — never a constant copied from research.md
      R1's own sweep numbers (`1.919`/`0.587`/`0.188` are illustrative
      findings from Phase 0, not defaults to hardcode). The three-way
      `tightness_status` cutoffs themselves (`<0.2` informative,
      `0.2-1.0` loose, `≥1.0` vacuous, chosen from R1's own executed
      distribution per research.md R2) MAY be named module-level
      constants — it is only the ratio's own numerator/denominator that
      must be live per-call values, never frozen. Satisfies T012, T013,
      T014.
- [x] T020 [P] [US2] Implement FR-008's explicit-failure path in
      `noisy_krr_predict`: raise a dedicated, named exception (e.g.
      `InvalidBoundInputsError`) when any of `ε_k, ε_y, λ₀, κ, M` is
      missing or non-positive — satisfies T015.
- [x] T021 [US2] Confirm the returned `(predicted_value, NoisyKRRBound)`
      pair together satisfy FR-006 Acceptance Scenario 3 — no code path
      in `kernel.py` returns a bare prediction float without its
      accompanying bound object.

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 - Exponential-ambient/fixed-support demonstration (Priority: P3)

**Goal**: Reproduce, as permanent tests, the already-verified cancellation
identity and ambient/support scaling (Finding 1) — no new production
module needed, since Spec 1's existing IR primitives already suffice
compositionally.

**Independent Test**: Already done once ad hoc (Finding 1); this phase
converts that into permanent, re-runnable tests.

### Tests for User Story 3

- [x] T022 [P] [US3] Oracle test in
      `tests/oracle/test_kernel_cancellation_pac_efficiency.py`:
      reproduce the exact `Rz(α_s)·Y·Rz(α_s)=Y` identity check (two tied
      `PauliTerm('Z', ...)` uploads sandwiching a `FixedGate(YGate())`,
      built directly from existing `ir.py` primitives) for the same five
      `α_s` values as Finding 1, asserting `Operator`-level diff `≤
      2.2e-16` in each case (FR-009 Acceptance Scenario 1).
- [x] T023 [US3] Same file: reproduce the one-cancelling-parameter fixture
      (ambient `45`, extracted support `{(-2,0), (2,0)}`) and the
      two-cancelling-parameter fixture (ambient `405`, support still
      `{(-2,0,0), (2,0,0)}`) as permanent assertions against
      `reference.coefficients` (FR-010 Acceptance Scenarios 2-3).
- [x] T024 [P] [US3] Edge-case unit test in
      `tests/unit/test_kernel_cancellation_broken_symmetry.py`: construct
      a "cancelling" fragment whose two uploads use DIFFERENT structural
      weights (breaking the exact tied-sandwich symmetry) and assert the
      resulting support is NOT silently treated as pinned at `0` — either
      the existing tie-group validation (Spec 9 precedent) rejects the
      construction outright, or the test explicitly demonstrates the
      cancellation no longer holds numerically.

### Implementation for User Story 3

- [x] T025 [US3] Add a small, reusable fixture-builder helper —
      `_build_cancelling_parameter_fixture(surviving_count,
      cancelling_count) -> PauliEncodedCircuitIR` — placed directly in
      `tests/oracle/test_kernel_cancellation_pac_efficiency.py` (not a
      new production module): FR-009's "a way to construct" requirement
      is already satisfied compositionally by Spec 1's existing
      `PauliTerm`/`FixedGate`/IR-builder primitives, so no new production
      abstraction is introduced for this alone (Constitution's
      minimalism — no design for hypothetical future reuse beyond this
      feature's own declared scope).
- [x] T026 [US3] Update `.specify/memory/extension-register.md` (EXT-002)
      recording FR-011/Acceptance Scenario 4's labeling guardrail as
      checked: this feature introduces no Z₂-platform fixture of its
      own, so there is nothing to mislabel — document that explicitly
      rather than leaving it unstated.

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T027 [P] Update `.specify/memory/extension-register.md` EXT-002
      status from "in progress — scheduled implementation underway" to
      "implemented," citing this feature's file list (`kernel.py`,
      `circuits.py`/`reference.py` additions) and test counts.
- [x] T028 [P] Run `mypy` across `src/fourierlearn/kernel.py` and the
      modified `circuits.py`/`reference.py`, fixing any type errors, per
      this project's existing convention.
- [x] T029 Run the full `pytest` suite and confirm green; confirm
      `tests/ci/test_no_forbidden_imports.py` still passes with
      `kernel.py`'s noisy-KRR path importing NEITHER `reference`,
      `Statevector`, `Operator`, nor `expm` (Constitution §3.4 — this
      feature's KRR math is pure NumPy on already-estimated values, not
      exact simulation).
- [x] T030 [P] Constitution §5.3 audit (**Strict Constraint**): confirm no
      caching, batching, or memoization was introduced anywhere in
      `kernel.py` or the new `circuits.py`/`reference.py` functions —
      add a one-line docstring note on each new public function
      recording this, per research.md R4, so the discipline is visible
      at the call site and not only in this planning document.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Empty — no blocking prerequisites beyond
  Setup.
- **User Story 1 (Phase 3)**: Can start immediately after Setup.
- **User Story 2 (Phase 4)**: Its Gram-matrix construction (T016) calls
  User Story 1's overlap evaluation (FR-005) — T016 depends on T005/T006
  being complete. T017-T021 (the noisy-KRR/`NoisyKRRBound` path) do NOT
  depend on User Story 1 at all — they operate on an already-given `K̂`
  — and MAY be implemented and tested in parallel with Phase 3.
- **User Story 3 (Phase 5)**: Fully independent of Phases 3-4 — uses only
  Spec 1's existing IR primitives and `reference.coefficients`. Can run
  in parallel with either.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests (T002-T003, T009-T015, T022-T024) are written and run FAILING
  before their corresponding implementation tasks, per this project's
  established TDD convention.
- T019 (dynamic tightness ratio) and T014 (transition test) are the two
  tasks directly answering this round's Critical Guardrails 1 and 2 —
  neither may be marked complete until the OTHER's corresponding test
  passes on the same implementation.

### Parallel Opportunities

- T002 and T008 (different files, US1).
- T009, T010, T011, T012, T015 (five distinct US2 test files, no
  cross-dependency at the test-writing stage).
- T022 and T024 (different files, US3).
- Phase 3 (US1), Phase 4's noisy-KRR sub-path (T017-T021), and all of
  Phase 5 (US3) can proceed in parallel once Setup is done.
- T027, T028, T030 (Polish, different concerns).

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 3 (User Story 1) — a working, verified kernel-overlap
   circuit is independently valuable and independently demonstrable.
3. **STOP and VALIDATE**: T002/T003 pass against
   `reference.kernel_overlap_oracle`.

### Incremental Delivery

1. Setup → Phase 3 (US1) → validate → this is the MVP.
2. Add Phase 4 (US2) → validate T009-T015, especially T014's transition
   test (Critical Guardrail 2) → KRR with an honestly-labeled bound.
3. Add Phase 5 (US3) → validate T022-T024 → the PAC-efficiency
   justification is now a permanent, re-runnable proof, not an ad hoc
   session artifact.
4. Phase 6 (Polish) closes out the feature.

## Notes

- No task in this list introduces caching, batching, or memoization
  (Constitution §5.3, Strict Constraint) — Phase 6's T030 is the explicit
  audit closing this out, but every implementation task above is written
  to require none in the first place.
- `[P]` tasks touch different files with no dependency on an incomplete
  task in the same phase.
- Commit after each task or logical group, per this project's existing
  practice on Specs 1-9.
