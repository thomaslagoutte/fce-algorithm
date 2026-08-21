---

description: "Task list for the Symmetry Verification Layer"
---

# Tasks: Symmetry Verification Layer

**Input**: Design documents from `/specs/007-symmetry-verification-layer/` (spec.md, plan.md, research.md)

**Tests**: Included — this project's own established test-first convention (Specs 1-6) continues here.

**Organization**: Tasks are grouped by user story (spec.md: US1 P1, US2 P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2)

## Path Conventions

Single Python library, matching Specs 1-6: `src/fourierlearn/`, `tests/unit/`.

## Guardrail note on the physics fixture (read before T006 onward)

Every test task below that needs a concrete Z₂ Gauss law/gauge-field
fixture uses the **full matter+gauge** formulation
(`G_v = Z_v · prod_{e touching v} X_e` — explicitly including the matter
qubit at each vertex), **not** research.md R2/R3's simplified pure-gauge
fixture (`G_v = prod_{e touching v} X_e`, no matter qubits). This was
re-verified by execution during task generation, on a 3-vertex path
lattice with 3 matter qubits + 2 gauge qubits (5 qubits total):

```
G_v0 = IXIIZ   G_v1 = XXIZI   G_v2 = XIZII
H_g_e01 = IXIII   H_g_e12 = XIIII                 (pure-gauge kinetic terms)
H_hop_e01 = IZIXX   H_hop_e12 = ZIXXI              (matter-gauge hopping terms)
```

All three `G_v` commute with all four Hamiltonian terms (non-annihilating:
PASS), pairwise commute (Abelian: PASS), and carry no symbolic coefficient
(internal: PASS). A Z-twirl candidate on this same 5-qubit fixture
(`Z_twirl_v0 = IZIIX`, swapping `X<->Z` relative to the true `G_v0 = IXIIZ`)
was confirmed to anticommute with `H_g_e01` (`IXIII`) — failing
non-annihilating on the full fixture too. Use these exact labels (or
recompute them with the same `make_label`-style helper) in T006-T009 —
do not fall back to the simpler pure-gauge-only labels research.md itself
used.

---

## Phase 1: Setup

- [x] T001 Confirm no new third-party dependency is needed (`qiskit`
  already pinned) — no `pyproject.toml` change for this feature.

**Checkpoint**: Setup complete.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `SymmetryDeclaration`'s new `generators` field must exist
before either user story's tests can construct a declaration carrying
real algebraic content.

- [x] T002 In `src/fourierlearn/models.py`, add a new, defaulted field
  `generators: tuple[SparsePauliOp, ...] = ()` to `SymmetryDeclaration`
  (FR-012) — additive only; `name` and `description` are unchanged, and
  every existing call site in Spec 6's own test suite
  (`SymmetryDeclaration(name=..., description=...)`, no `generators`)
  MUST continue to construct a valid object with `generators == ()`
  unchanged.
- [x] T003 Run `pytest tests/unit/test_models_symmetry_attach_point.py -v`
  (Spec 6's own existing suite) and confirm it still passes unmodified —
  proving T002's field addition broke nothing before any new Spec 7 code
  exists.

**Checkpoint**: Foundation ready — User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 - Algebraically verify a declared symmetry against Constitution §11.1 (Priority: P1) 🎯 MVP

**Goal**: `verify_symmetry(generators, hamiltonian_terms)` checks all
three of §11.1's conditions using only Pauli-string algebra, reports every
condition's individual outcome, and correctly gives the Gauss law an
accept and the Z-twirl a reject — on the full matter+gauge fixture.

**Independent Test**: spec.md's own User Story 1 Independent Test.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; confirm they FAIL before the corresponding implementation task.

- [x] T004 [P] [US1] `test_symbolic_coefficient_generator_is_rejected` and
  `test_concrete_generator_is_accepted` in
  `tests/unit/test_symmetry_vacuous_truth.py` — reproduce research.md
  R1's two executed attempts as two independent test functions: a
  `SparsePauliOp` built with a `qiskit.circuit.Parameter` coefficient
  fails `is_classical_input_independent`; a plain `SparsePauliOp("X")`
  passes it. **Do not merge these into one test** — a single test
  asserting both could pass even if one direction of the check were
  broken.
- [x] T005 [P] [US1] `test_callable_generator_is_rejected_by_type` in
  `tests/unit/test_symmetry_vacuous_truth.py` — research.md R1 Attempt 3:
  a plain Python callable passed where a generator is expected is
  rejected by a type check, independent of and before T004's coefficient
  check would run.
- [x] T006 [US1] **Gauss law positive control (guardrail #1: full
  matter+gauge fixture)** — `test_full_matter_gauge_gauss_law_passes_all_conditions`
  in `tests/unit/test_symmetry_gauss_law_positive.py`: build the 3-vertex,
  5-qubit (3 matter + 2 gauge) fixture from this file's own header note
  above; call `verify_symmetry` with the three `G_v` generators and the
  four Hamiltonian terms (`H_g_e01`, `H_g_e12`, `H_hop_e01`,
  `H_hop_e12`); assert the result accepts, with `internal`,
  `non_annihilating`, and `abelian` each individually `True`. Also assert
  the three generators are pairwise distinct (`G_v0 != G_v1 != G_v2`) —
  proving this is genuinely the site-indexed case, not an accidental
  uniform one.
- [x] T007 [US1] **Z-twirl negative control (guardrail #1: full
  matter+gauge fixture)** — `test_ztwirl_fails_non_annihilating_on_full_fixture`
  in `tests/unit/test_symmetry_ztwirl_negative.py`: on the SAME 5-qubit
  fixture as T006, build the naive `Z_twirl_v0` candidate (`X<->Z` swapped
  relative to the true `G_v0`); call `verify_symmetry`; assert the result
  rejects with `non_annihilating=False` naming the specific failing term
  (`H_g_e01`), while `internal=True` and `abelian=True` — proving this
  negative control isolates the non-annihilating failure specifically,
  not a confound of several failures. **Kept in its own file, separate
  from T006** — the positive and negative controls are distinct claims.
- [x] T008 [P] [US1] `test_abelian_failure_is_detected` in
  `tests/unit/test_symmetry_abelian_failure.py`: two generators that do
  NOT commute (e.g. `X` and `Z` on the same qubit) are correctly rejected
  with `abelian=False`, naming the specific non-commuting pair — a
  negative control not covered by T006/T007, both of which are entirely
  `X`-and-`Z`-mixed-but-still-commuting by construction.
- [x] T009 [P] [US1] `test_zero_generators_rejected`,
  `test_identity_generator_rejected`,
  `test_qubit_count_mismatch_rejected` in
  `tests/unit/test_symmetry_degenerate_declarations.py` — three
  independent test functions (FR-008/FR-009): an empty generator tuple is
  rejected; a generator equal to the identity operator is rejected; a
  generator and Hamiltonian term list declared over different numbers of
  qubits is rejected as a structural mismatch, checked before the three
  §11.1 conditions.
- [x] T010 [P] [US1] `test_verify_symmetry_reports_every_condition_not_just_first_failure`
  in `tests/unit/test_symmetry_abelian_failure.py`: a symmetry
  deliberately constructed to fail **two** conditions at once (e.g. an
  `alpha`-dependent generator that is also part of a non-commuting pair)
  still reports both individual failures in the result (FR-006) — not
  only the first one checked.

### Implementation for User Story 1

- [x] T011 [US1] Create `src/fourierlearn/symmetry.py` with
  `SymmetryVerificationResult` (frozen dataclass: `accepted: bool`,
  `internal: bool`, `non_annihilating: bool`, `abelian: bool`,
  `failing_term: SparsePauliOp | None`, `non_commuting_pair: tuple[SparsePauliOp, SparsePauliOp] | None`,
  `failure_reason: str | None`) per spec.md's "Symmetry verification
  result" Key Entity. Module docstring states this module imports no
  `QuantumCircuit`, `Statevector`, `Operator`, `expm`, or
  `fourierlearn.reference` — confirmed by the *existing, unmodified* CI
  guard, no exemption needed (research.md R4).
- [x] T012 [US1] Implement `is_classical_input_independent(generator: SparsePauliOp) -> bool`
  in `symmetry.py` (research.md R1, FR-001): `not any(isinstance(c, ParameterExpression) for c in generator.coeffs)`.
  **NumPy Bool Trap (Guardrail #3, research.md R3's own pitfall)**: this
  function and every other check in this module MUST NOT compare any
  `Pauli.commutes(...)` result with `is True`/`is False` — `.commutes()`
  returns a `numpy.bool_`, and `numpy.bool_(True) is True` is `False`
  despite being truthy. Use `==` or `bool(...)` everywhere a commutation
  result is checked.
- [x] T013 [US1] Implement the **non-annihilating** check in `symmetry.py`
  (FR-002): for each generator, iterate every Hamiltonian term and check
  `bool(generator.paulis[0].commutes(term.paulis[0]))`; record the first
  (or every, per T010) failing term.
- [x] T014 [US1] Implement the **Abelian** check in `symmetry.py`
  (FR-003): for every pair of declared generators, check
  `bool(a.paulis[0].commutes(b.paulis[0]))`; record the first (or every)
  non-commuting pair.
- [x] T015 [US1] Implement the degenerate/structural rejections in
  `symmetry.py` (FR-008/FR-009): zero generators; a generator equal to
  `SparsePauliOp("I" * n)` (the identity, for the declared qubit count
  `n`); a generator/Hamiltonian-term qubit-count mismatch — checked
  before FR-001..FR-003's substantive conditions.
- [x] T016 [US1] Implement `verify_symmetry(generators: tuple[SparsePauliOp, ...], hamiltonian_terms: tuple[SparsePauliOp, ...]) -> SymmetryVerificationResult`
  in `symmetry.py` (FR-001..FR-007): runs T015's structural checks first;
  then T012 (internal), T013 (non-annihilating), and T014 (Abelian) —
  ALL three, unconditionally, never short-circuiting on the first
  failure (FR-006); composes the result with every condition's individual
  outcome and, on any failure, the specific offending term/pair
  (FR-007). **Generic Architecture (FR-005)**: this function's signature
  takes only `(generators, hamiltonian_terms)` — no model-identifying
  parameter exists anywhere for a branch to key on.

**Checkpoint**: User Story 1 is fully functional and independently
testable — T004-T010 all pass, including the Gauss law positive control
(T006) and Z-twirl negative control (T007) on the full matter+gauge
fixture.

---

## Phase 4: User Story 2 - Reject an invalid symmetry declaration before any circuit compilation (Priority: P2)

**Goal**: A `PhysicalModelDescription` carrying an invalid symmetry
declaration cannot be constructed at all — through any code path, not
only the blessed `build_tfim_model` factory.

**Independent Test**: spec.md's own User Story 2 Independent Test.

### Tests for User Story 2 ⚠️

- [x] T017 [P] [US2] `test_build_tfim_model_rejects_invalid_symmetry_before_compilation`
  in `tests/unit/test_models_symmetry_validation_hook.py`: constructing a
  TFIM model via `build_tfim_model` with an attached symmetry declaration
  that fails any §11.1 condition raises, with the specific failed
  condition surfaced, and — since `build_tfim_model` itself never invokes
  any circuit-compilation module — this is structurally guaranteed to
  happen before compilation, not merely observed to happen first in this
  test.
- [x] T018 [P] [US2] `test_build_tfim_model_unchanged_for_valid_or_absent_symmetry`
  in `tests/unit/test_models_symmetry_validation_hook.py`: a model with no
  symmetry declaration, and a model with a declaration that passes all
  checks, both construct exactly as Spec 6 already shipped them (FR-011).
- [x] T019 [US2] **Unguarded Bypass Prevention (Guardrail #2)** —
  `test_direct_physical_model_description_construction_cannot_bypass_verification`
  in `tests/unit/test_models_symmetry_validation_hook.py`: instantiate
  `PhysicalModelDescription` **directly** (not via `build_tfim_model`) with
  an attached symmetry declaration that fails a §11.1 condition, and
  confirm construction still raises — proving the check is enforced by
  the entity itself (`__post_init__`, T021), not merely by one factory
  function a caller could route around.
- [x] T020 [P] [US2] `test_physical_model_description_direct_construction_succeeds_for_valid_symmetry`
  in `tests/unit/test_models_symmetry_validation_hook.py`: direct
  construction with no declaration, or a valid one, still succeeds —
  T019's guard is not a blanket rejection of direct construction, only of
  an invalid declaration.

### Implementation for User Story 2

- [x] T021 [US2] **Structural enforcement (Guardrail #2)** — add
  `__post_init__` to `PhysicalModelDescription` in
  `src/fourierlearn/models.py`: when `self.symmetry is not None and
  self.symmetry.generators`, call `symmetry.verify_symmetry(self.symmetry.generators, <this model's own Hamiltonian terms, flattened from self.coupling_groups>)`
  and raise (naming the failed condition) if the result does not accept.
  This makes verification **automatic and unavoidable** for every code
  path that ever produces a `PhysicalModelDescription` — including direct
  instantiation (T019) — not only `build_tfim_model`'s own call site.
  `PhysicalModelDescription` remains a frozen dataclass; `__post_init__`
  only validates, it does not assign or mutate any field.
- [x] T022 [US2] Remove/simplify any symmetry-checking logic that would
  otherwise have been added directly inside `build_tfim_model` itself
  (per the original research.md R4 sketch) — after T021, `build_tfim_model`
  needs no explicit call to `verify_symmetry` of its own at all, since
  constructing the `PhysicalModelDescription` it returns already triggers
  T021's `__post_init__` unconditionally. Confirms there is exactly one
  enforcement point, not two redundant ones.

**Checkpoint**: Both user stories are independently functional — T017-T020
all pass, and T019 specifically proves the check cannot be bypassed by
constructing the entity directly.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T023 [P] Full suite: `pytest tests/ -q` → **173 passed** (Specs 1-7 together, up from 158 before this feature). `mypy src/fourierlearn/` → **Success: no issues found in 15 source files**.
- [x] T024 [P] Audit confirmed: `symmetry.py` has exactly one implementation of each check (`is_classical_input_independent`, `_check_non_annihilating`, `_check_abelian`); `models.py`'s `__post_init__` is the ONLY call site of `verify_symmetry` in `models.py` — `build_tfim_model` was confirmed to need no explicit call of its own (T022), since constructing the `PhysicalModelDescription` it returns already triggers `__post_init__`.
- [x] T025 [P] Confirmed by reading `symmetry.py`: zero `cache`/`lru_cache`/`batch`/`memo` hits (grep-confirmed). Every `verify_symmetry` call recomputes all three checks from scratch.
- [x] T026 [P] Confirmed by grep: zero `is True`/`is False` occurrences in `symmetry.py`'s actual code (the two hits found are both inside the module docstring's own explanation of the trap, not executable comparisons). Every commutation result is compared via `bool(...)` at the point `.commutes()` is called, or via plain Python `True`/`False` literals returned from the check functions (never a raw `numpy.bool_` propagated through an `is` comparison).
- [x] T027 [P] Confirmed by grep: `symmetry.py` imports only `dataclasses`, `qiskit.circuit.ParameterExpression`, and `qiskit.quantum_info.SparsePauliOp` — no `Statevector`/`Operator`/`expm`/`fourierlearn.reference`, no `QuantumCircuit` construction anywhere. `pytest tests/ci/test_no_forbidden_imports.py -v` → **7 passed**, same count as before this feature (zero new exemptions added).
- [x] T028 [P] **SC → test mapping**: SC-001 → `test_full_matter_gauge_gauss_law_passes_all_conditions` + `test_ztwirl_fails_non_annihilating_on_full_fixture`. SC-002 → `test_clean_tree_reports_no_violations` (CI guard, unmodified). SC-003 → the same two tests, on the full matter+gauge fixture with distinct per-vertex generators. SC-004 → `test_build_tfim_model_rejects_invalid_symmetry_before_compilation` + `test_direct_physical_model_description_construction_cannot_bypass_verification`. SC-005 → `test_zero_generators_rejected` + `test_identity_generator_rejected`. All five confirmed passing.

**Implementation-time addition beyond the original task list**: a sixth
US2 test, `test_asymmetric_padding_is_evaluated_on_the_correct_physical_qubits`
(`tests/unit/test_models_symmetry_validation_hook.py`), was added per a
critical implementation instruction not present in this file's original
T017-T020: a dedicated regression test using an asymmetric case (a
Hamiltonian term on qubit 1 only, checked against a generator spanning
qubits 0 and 1) whose correct-vs-incorrect-padding answers provably
differ (`commute` vs. `anticommute`) — verified by deliberately
reproducing the buggy (unreversed) padding in an isolated scratch check
and confirming it flips the answer, before confirming the shipped
implementation (which reuses `pauli_pqc._pad_to_full_width_little_endian`
unchanged) gives the correct one.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS User Story 1 (T002's `generators` field is what T004-T010's tests construct declarations with).
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on User Story 2.
- **User Story 2 (Phase 4)**: Depends on User Story 1's `verify_symmetry`/`SymmetryVerificationResult` (T011-T016) existing — `__post_init__` (T021) calls it directly.
- **Polish (Phase 5)**: Depends on both user stories being complete.

### Within User Story 1

- T004, T005 (vacuous truth test) have no dependency beyond Foundational.
- T011 (module skeleton) has no dependency beyond Foundational.
- T012-T015 each depend on T011.
- T016 (`verify_symmetry`) depends on T012, T013, T014, T015.
- T006-T010 depend on T016 to actually pass (write-first, confirm-fail, then implement).

### Within User Story 2

- T021 (`__post_init__`) depends on User Story 1's T016 (`verify_symmetry`) and T002 (the `generators` field).
- T022 depends on T021 existing, to confirm it supersedes the original sketch.
- T017-T020 depend on T021/T022 to actually pass.

### Parallel Opportunities

- T004, T005, T008, T009 (independent US1 test files/functions) can be written in parallel.
- T017, T018, T020 (independent US2 assertions) can run in parallel; T019 is written alongside them but is the guardrail's own central proof.
- T023-T028 (Polish) can all run in parallel — independent audits.

---

## Parallel Example: User Story 1

```bash
# Tests, written first:
Task: "test_symbolic_coefficient_generator_is_rejected in tests/unit/test_symmetry_vacuous_truth.py"
Task: "test_abelian_failure_is_detected in tests/unit/test_symmetry_abelian_failure.py"
Task: "test_zero_generators_rejected in tests/unit/test_symmetry_degenerate_declarations.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (User Story 1).
2. **STOP and VALIDATE**: T004-T010 all pass — the Gauss law (T006) and
   Z-twirl (T007) controls both give the theoretically correct verdict on
   the full matter+gauge fixture, not a simplified stand-in.

### Incremental Delivery

1. Setup + Foundational → the `generators` field exists.
2. User Story 1 → validate independently → the engine itself is correct and generic.
3. User Story 2 → validate independently → the check is structurally unavoidable, not merely wired into one factory.
4. Polish.
