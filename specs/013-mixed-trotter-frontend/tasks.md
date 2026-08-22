---

description: "Task list for the Mixed Fixed/Encoded Trotter Frontend (Spec 13)"
---

# Tasks: Mixed Fixed/Encoded Trotter Frontend

**Input**: Design documents from `/specs/013-mixed-trotter-frontend/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: Included — spec.md's own Acceptance Scenarios are directly test-shaped (structural interleaving, `Operator.equiv` checks, error-identity checks), matching this project's established precedent (every prior spec ships tests alongside implementation).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

Single project (per plan.md): `src/fourierlearn/`, `tests/unit/` at repository root — this feature extends one existing module (`encodings/trotter.py`), no new top-level directory.

---

## Phase 1: Setup

**Purpose**: Establish the pre-change regression baseline the CRITICAL MANDATE requires, before any code changes.

- [x] T001 Run the full existing test suite (`pytest tests/`) and record which tests currently pass, as this feature's own pre-change baseline — `trotter_frontend` becomes a delegating wrapper around the new `mixed_trotter_frontend` in this feature (plan.md's key design decision), so every existing test anywhere in the suite that exercises Trotter evolution is effectively a regression test for this change; this baseline is what the Polish-phase full-suite rerun (T019) is diffed against.

**Checkpoint**: Baseline recorded — proceed to Foundational phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new dataclasses and the core two-pass `mixed_trotter_frontend` construction — every user story (US1's interleaving, US2's reuse boundary, US3's exact-reduction guarantee) exercises this SAME function, so it must exist before any story-specific test can be written against it.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `FixedCouplingGroup(terms: tuple[CouplingGroupTerm, ...], value: float)` dataclass and the `GroupSpec = CouplingGroup | FixedCouplingGroup` type alias to `src/fourierlearn/encodings/trotter.py`, alongside the existing `CouplingGroupTerm`/`CouplingGroup` (spec.md Key Entities, plan.md Source Code structure).
- [x] T003 Implement `mixed_trotter_frontend`'s Pass 1 in `src/fourierlearn/encodings/trotter.py`: collect ONLY the encoded (`CouplingGroup`) groups' uploads, in step-major/caller-declared-group order, and route them through `pauli_pqc.build_ir` completely unchanged (FR-004; reuses `build_ir`'s existing tie-group-commutativity check and `coordinate_order`/`PauliTerm` construction, never duplicated).
- [x] T004 Implement `mixed_trotter_frontend`'s Pass 2 in `src/fourierlearn/encodings/trotter.py`: walk the SAME nested `(step, group)` order a second time, building a `FixedGate` per fixed-group term via `PauliTerm(pauli, qubits, parameter_index=-1, coefficient=-weight*tau/(pi*r), tie_group=0).to_gate(value)` (FR-003/FR-011's verified angle formula) and pulling the next already-validated `PauliTerm` from Pass 1's `build_ir` output for encoded-group terms, assembling the final `PauliEncodedCircuitIR` with both interleaved in the caller's declared order (FR-002).
- [x] T005 Reuse (not duplicate) `trotter_frontend`'s existing `_validate_inputs` inside `mixed_trotter_frontend` for the shared empty-group-sequence/`r<=0`/`tau==0` rejection (FR-007) — its existing per-group uniform-weight check already operates on `CouplingGroupTerm`, which `FixedCouplingGroup` also uses, so no change to `_validate_inputs` itself is needed, only widening its call site to accept `Sequence[GroupSpec]`.
- [x] T006 Refactor `trotter_frontend` in `src/fourierlearn/encodings/trotter.py` to `return mixed_trotter_frontend(num_qubits, groups, tau, r, observable)` — `groups: Sequence[CouplingGroup]` already satisfies `Sequence[GroupSpec]` — making FR-005's exact-reduction guarantee structural (one interleaving implementation, Constitution §9.4) rather than two call paths kept in sync by convention.

**Checkpoint**: Foundation ready — `mixed_trotter_frontend` exists and `trotter_frontend` delegates to it; user story implementation (mostly test-writing against the now-complete construction) can begin.

---

## Phase 3: User Story 1 - Build one IR mixing fixed graph couplings with a shared encoded field parameter (Priority: P1) 🎯 MVP

**Goal**: One `PauliEncodedCircuitIR` whose `gates` tuple correctly interleaves `FixedGate` and `PauliTerm` elements per Trotter step, in the caller's declared group order, with the fixed-term angle formula verified correct.

**Independent Test**: Declare a mix of fixed and encoded groups, build the IR, confirm the `gates` tuple's per-step order matches the caller's declaration, and confirm the bound `Operator` matches an independently hand-built target exactly.

### Tests for User Story 1

- [x] T007 [P] [US1] Structural interleaving test in `tests/unit/test_trotter_mixed.py`: declare a multi-group sequence mixing fixed and encoded groups, build via `mixed_trotter_frontend`, and assert the `gates` tuple's per-step type/order sequence (`PauliTerm`/`FixedGate`) matches the caller's declared group order exactly (FR-001, FR-002).
- [x] T008 [P] [US1] `Operator.equiv` regression test in `tests/unit/test_trotter_mixed_gate_convention.py` reproducing research.md R1's isolated single-fixed-term case (both fixtures: `w=0.8,tau=1.09,r=3,v=1.5,P=Z` and `w=1.37,tau=0.62,r=5,v=-0.9,P=X`) against an independently hand-built `scipy.linalg.expm` target, asserting machine-precision agreement (FR-003, FR-011, SC-002).
- [x] T009 [P] [US1] `Operator.equiv` regression test in `tests/unit/test_trotter_mixed_gate_convention.py` reproducing research.md R2's genuinely mixed, multi-qubit, multi-parameter case (2 distinct encoded parameters `h1`/`h2` + 1 fixed `ZZ` group, 3 qubits, caller order `[h1, fixed, h2]`, `tau=0.95`, `r=3`) against an independently hand-built `scipy.linalg.expm` target, asserting machine-precision agreement (SC-002; the Assumptions multi-parameter mandate).

### Implementation for User Story 1

- [x] T010 [US1] Confirm and, if needed, adjust `mixed_trotter_frontend` (`src/fourierlearn/encodings/trotter.py`) so a fixed group's declared value of exactly `0` produces a valid `FixedGate` (never a special-cased omission or error), and so an all-fixed-groups call (zero encoded groups) produces a valid IR without invoking `pauli_pqc.build_ir` at all (FR-006, FR-008) — add the corresponding assertions to `tests/unit/test_trotter_mixed.py`.

**Checkpoint**: User Story 1 is fully functional and independently testable — the mixed construction interleaves correctly and its fixed-term angle formula is verified.

---

## Phase 4: User Story 2 - Reuse `pauli_pqc.build_ir`'s validation for the encoded portion, never duplicate it (Priority: P2)

**Goal**: The encoded portion's tie-group-commutativity check and `coordinate_order`/`PauliTerm` construction come from `pauli_pqc.build_ir` exactly — never a second, parallel implementation inside `mixed_trotter_frontend`.

**Independent Test**: Declare an encoded group whose terms do not commute across the same tie group; confirm the mixed construction raises the EXACT SAME error `pauli_pqc.build_ir` raises directly for that input.

### Tests for User Story 2

- [x] T011 [P] [US2] Error-identity test in `tests/unit/test_trotter_mixed_commutativity_reuse.py`: construct an encoded group whose terms fail `pauli_pqc.build_ir`'s own tie-group-commutativity check when called directly, then build the same group via `mixed_trotter_frontend`, and assert the raised error is the IDENTICAL error type and message `build_ir` itself raises (FR-004, FR-010, SC-004).
- [x] T012 [P] [US2] `coordinate_order` mapping test in `tests/unit/test_trotter_mixed.py`: declare a mixed construction with multiple distinct encoded parameter labels, and assert each maps to the same `parameter_index` `pauli_pqc.build_ir` would assign if called directly on just those groups' uploads (User Story 2 Acceptance Scenario 2).

### Implementation for User Story 2

- [x] T013 [US2] Static verification: re-read `mixed_trotter_frontend`'s implementation (`src/fourierlearn/encodings/trotter.py`, from T003/T004) and confirm no tie-group-commutativity or `coordinate_order` logic has been reimplemented locally outside the `pauli_pqc.build_ir` call from Pass 1 — if any local duplication is found, remove it and route through `build_ir` instead (Constitution §9.4).

**Checkpoint**: User Stories 1 AND 2 both work independently — the encoded portion is confirmed to be a thin pass-through to `pauli_pqc.build_ir`, not a parallel reimplementation.

---

## Phase 5: User Story 3 - Confirm the all-encoded case reduces exactly to `trotter_frontend`'s existing behavior (Priority: P3)

**Goal**: Calling the mixed construction with zero fixed groups is a strict, non-regressive superset of `trotter_frontend`'s existing capability — not a divergent reimplementation.

**Independent Test**: Call the mixed construction with zero fixed groups on an input `trotter_frontend` already accepts; confirm the resulting IR is exactly (structurally, and via `Operator.equiv`) `trotter_frontend`'s own output for the same input.

### Tests for User Story 3

- [x] T014 [P] [US3] Structural exact-reduction test in `tests/unit/test_trotter_mixed_exact_reduction.py`: build a 2-qubit, 2-group (`J`: tied `ZZ`; `h`: two tied `X`) encoded-only example via both `trotter_frontend` and `mixed_trotter_frontend` (zero fixed groups) with identical `tau=1.09`, `r=2`, and assert the two `gates` tuples are structurally identical (Python `==`) (FR-005).
- [x] T015 [P] [US3] `Operator.equiv` exact-reduction test in `tests/unit/test_trotter_mixed_exact_reduction.py`: bind both IRs from T014 to the same parameter values (`alpha=[0.6,-0.3]`) and assert `Operator.equiv` with `diff=0.0` exactly, not merely approximately equivalent (SC-003).
- [x] T016 [US3] Confirm `tests/unit/test_trotter.py` (Spec 2's existing test file, unmodified) still passes after the T006 `trotter_frontend` refactor — this is the most direct, existing regression signal that the delegation preserves `trotter_frontend`'s own established behavior exactly.

**Checkpoint**: All three user stories are independently functional — interleaving, reuse-boundary, and exact-reduction are each verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final static and dynamic checks confirming the feature is complete and introduces zero regressions anywhere in the codebase.

- [x] T017 [P] Run `mypy` across `src/fourierlearn/` and confirm it is clean, including the new `FixedCouplingGroup`/`GroupSpec`/`mixed_trotter_frontend` additions and the refactored `trotter_frontend` in `src/fourierlearn/encodings/trotter.py`.
- [x] T018 [P] Update `src/fourierlearn/encodings/trotter.py`'s module docstring to document `mixed_trotter_frontend`, `FixedCouplingGroup`, and `trotter_frontend`'s new delegating relationship to it.
- [x] T019 **CRITICAL MANDATE — full-suite regression gate**: Run the ENTIRE existing test suite (`pytest tests/`, not merely this feature's own new test files) and diff the result against T001's pre-change baseline. Because `trotter_frontend` is now a thin delegating wrapper around `mixed_trotter_frontend` (T006), every pre-existing test anywhere in the suite that exercises Trotter evolution is effectively a regression test for this feature. **Zero regressions in any legacy test are permitted** — every test that passed in the T001 baseline MUST still pass; any newly failing legacy test blocks completion of this task and MUST be root-caused and fixed (in this feature's own new code, never by weakening or deleting the legacy test) before this task may be marked done.

**Checkpoint**: Feature complete — all new tests pass, all legacy tests still pass, `mypy` is clean.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001's baseline should exist first, though it does not block T002-T006's code itself) — BLOCKS all user stories, since US1/US2/US3 all test the same `mixed_trotter_frontend`/`trotter_frontend` this phase creates.
- **User Stories (Phase 3-5)**: All depend on Foundational phase (T002-T006) completion.
  - User Story 1 (T007-T010): no dependency on US2/US3.
  - User Story 2 (T011-T013): no dependency on US1/US3 (exercises the same Pass 1 `build_ir` delegation T003 already established, independently of US1's own tests).
  - User Story 3 (T014-T016): no dependency on US1/US2 (exercises the T006 delegation directly).
- **Polish (Phase 6)**: Depends on all three user stories being complete — T019 in particular requires every new test file from T007-T016 to exist and pass first.

### Within Each User Story

- Tests are written against the Foundational phase's already-complete `mixed_trotter_frontend`/`trotter_frontend` (this feature does not follow strict TDD ordering within a story, since the core construction is shared Foundational-phase work all three stories test from different angles).
- Story complete before moving to the next priority, per the Implementation Strategy below.

### Parallel Opportunities

- T007, T008, T009 (US1 tests, different test files/functions) can run in parallel.
- T011, T012 (US2 tests) can run in parallel.
- T014, T015 (US3 tests) can run in parallel.
- T017, T018 (Polish, independent concerns) can run in parallel; T019 MUST run after both (a full-suite run is only meaningful once the new code and its own docstring/type-check pass are settled).
- Once Foundational (Phase 2) completes, US1/US2/US3's test-writing work can proceed in parallel if staffed — none of the three stories' tests depend on another story's tests existing.

---

## Parallel Example: User Story 1

```bash
# Launch all three User Story 1 tests together:
Task: "Structural interleaving test in tests/unit/test_trotter_mixed.py"
Task: "Operator.equiv isolated fixed-term test in tests/unit/test_trotter_mixed_gate_convention.py"
Task: "Operator.equiv multi-parameter mixed test in tests/unit/test_trotter_mixed_gate_convention.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 — record baseline).
2. Complete Phase 2: Foundational (T002-T006 — CRITICAL, blocks all stories).
3. Complete Phase 3: User Story 1 (T007-T010).
4. **STOP and VALIDATE**: User Story 1's tests pass independently — the mixed construction interleaves correctly and its angle formula is verified.

### Incremental Delivery

1. Setup + Foundational → the shared `mixed_trotter_frontend`/`trotter_frontend` delegation exists.
2. Add User Story 1 → validate independently (MVP: interleaving + angle-formula correctness).
3. Add User Story 2 → validate independently (reuse-boundary: no duplicated commutativity/`coordinate_order` logic).
4. Add User Story 3 → validate independently (exact-reduction guarantee against `trotter_frontend`'s pre-existing behavior).
5. Phase 6 Polish, ending with T019's full-suite, zero-legacy-regressions gate.

---

## Notes

- [P] tasks touch different files or independent test functions within a shared file, with no dependency ordering between them.
- [Story] labels map each task to spec.md's User Story 1/2/3 for traceability.
- T001 and T019 are a deliberately matched pair: T001 establishes what "zero regressions" means concretely (the exact baseline), and T019 is the CRITICAL MANDATE's gate enforcing it — this pairing exists specifically because T006's `trotter_frontend` refactor makes the ENTIRE existing test suite a de facto regression suite for this feature, not only its own new tests.
- Avoid: re-deriving the angle formula or the interleaving order from scratch during implementation — T004/T008/T009 exist precisely so the already-verified research.md R1/R2 findings are encoded directly as executable tests, not re-derived by whoever implements T003/T004.
