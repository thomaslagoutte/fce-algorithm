---

description: "Task list for the Equivariant Z2 LGT Ansatz and Containment Verification (Spec 8)"
---

# Tasks: Equivariant Z2 LGT Ansatz and Containment Verification

**Input**: Design documents from `/specs/008-equivariant-z2-lgt-ansatz/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories), [research.md](./research.md)

**Tests**: Included throughout — this project's own established discipline
(Specs 5-7) writes tests first and keeps distinct claims in distinct test
functions; Spec 8 follows this unchanged.

**Guardrails acknowledged** (from the `/speckit.tasks` invocation):

1. **Scalable CI Exemption**: `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` becomes
   a tuple; `find_violations` iterates it (`in`, not `==`); the 3 existing
   Spec 6 tests are updated to index `[0]`; a new test independently
   exercises `[1]` the same way — proving the mechanism generalizes to any
   future count of exempt modules without a further signature change
   (T014/T015 below).
2. **Asymptotic Honesty**: `ContainmentVerificationResult`'s reduction
   factor is populated *only* from the exact, computed
   `len(ambient)/len(Λ)` for the declared instance, with a separate,
   explicit field/docstring distinguishing it from the report's asymptotic
   `2^{-(d+|V|)}` CLT-heuristic value — enforced by a dedicated test
   asserting the reported number equals the exact ratio (`45.0` for the
   research fixture) and explicitly does **not** equal the asymptotic
   value (`64`) (T025/T026 below).
3. **State-Prep Flip**: an explicit task implements the `FixedGate`
   initial-occupation flip as an optional, defaulted parameter (never
   changing existing behavior when omitted), with a dedicated regression
   test that first reproduces the degeneracy on the *unflipped* fixture
   before proving the flip fixes it (T020-T022 below).
4. **Strict Constraints**: no task in this list adds caching, batching,
   memoization, or any other unprofiled optimisation (Constitution §5.3) —
   every new function here is a single, direct pass with no repeated-call
   pattern to justify one.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Confirm the existing project already satisfies Spec 8's
dependency needs — no new setup is required.

- [x] T001 Confirm `pyproject.toml`'s existing pins (`qiskit`, `numpy`,
      `scipy`) already satisfy Spec 8's needs (plan.md Technical Context:
      no new dependency) — run `python -c "import qiskit, numpy, scipy"`
      inside the project venv and record the versions in the PR
      description; no file changes expected from this task.
      **Done**: qiskit 2.3.1, numpy 1.26.4, scipy 1.13.1 — all already
      pinned, no changes needed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**None required.** Every existing module this feature reuses
(`encodings/trotter.CouplingGroup`, `models.PhysicalModelDescription`,
`symmetry.verify_symmetry`, `frequency.pre_parity_range`/`register_width`,
`reference.coefficients`/`predict_grid_cost`) is used completely
unmodified (research.md R5, confirmed by direct execution). The one
genuinely blocking prerequisite this feature introduces — the CI-guard
widening — is scoped specifically to User Story 3 (only its
`_containment_oracle_check.py` module needs it) and is placed as the first
sub-phase of User Story 3 below, rather than here, so User Stories 1 and 2
remain startable immediately and in parallel.

**Checkpoint**: Setup complete — User Stories 1 and 2 can begin
immediately; User Story 3 can begin immediately for its `Λ`/state-prep
work (T017-T023) and reaches its CI-guard-gated sub-phase (T014+) whenever
convenient.

---

## Phase 3: User Story 1 - Construct a Gauss-law-equivariant ansatz for the full matter+gauge Z₂ LGT Hamiltonian (Priority: P1) 🎯 MVP

**Goal**: `build_z2_lgt_model` produces a Pauli-encoded ansatz restricted
to exactly `{Z_v}∪{X_e}∪{h_e}`, targeting the full local-coupling
Hamiltonian (`d=|V|+2|E|`, research.md R1), with its Gauss law generators
declared and verified via Spec 7's existing, unmodified enforcement before
any circuit is trusted.

**Independent Test**: Declare a small lattice, build the ansatz, confirm
the term list is restricted to the three families with local couplings,
confirm the Gauss law passes `verify_symmetry` unmodified, and confirm a
corrupted generator is rejected before any circuit compiles.

### Tests for User Story 1 ⚠️

> Write these tests FIRST; they must FAIL (the module does not exist yet)
> before any implementation task below.

- [x] T002 [P] [US1] Write `tests/unit/test_z2lgt_hamiltonian_construction.py`:
      given a 2-matter-site/1-edge graph (research.md R2's own fixture),
      `build_z2_lgt_model(...)` produces a `PhysicalModelDescription`
      whose flattened Hamiltonian terms are exactly the mass/electric/
      hopping families (never an arbitrary Pauli string), with **local**
      per-vertex/per-edge couplings (`ir.num_parameters == 4 == |V|+2|E|`
      via the underlying IR, multiplicities `(1,1,1,2)` for
      mass/electric/hopping — reproduces research.md R2's Step 1 exactly).
- [x] T003 [P] [US1] Write `tests/unit/test_z2lgt_gauss_law_hook.py`: the
      same graph's derived Gauss law `SymmetryDeclaration` passes
      `PhysicalModelDescription.__post_init__`'s existing, unmodified
      Spec 7 enforcement (construction succeeds); a **hand-corrupted**
      generator (constructed directly, bypassing `_gauss_law_generators`,
      e.g. `Z_v0` alone with no electric factor) raises
      `InvalidSymmetryError` when passed to `PhysicalModelDescription`
      directly — reproduces research.md R4's negative control.
- [x] T004 [P] [US1] Write `tests/unit/test_z2lgt_gate_contiguity.py`:
      asserts, directly on the compiled IR's own `.gates` tuple (never
      only in a comment, per Constitution §11.9/§11.10), that every
      mass/electric `PauliTerm` entry precedes every hopping `PauliTerm`
      entry — the commuting family `F={Z_v}∪{X_e}` stays one contiguous
      block.

### Implementation for User Story 1

- [x] T005 [P] [US1] Implement `Z2LGTEdge` and `Z2LGTGraph` dataclasses in
      `src/fourierlearn/z2lgt.py`: `Z2LGTGraph` holds `num_matter_sites`
      and a tuple of `Z2LGTEdge(site_i, site_j)` — one gauge qubit per
      edge, total qubits `= |V| + |E|`, matter qubits indexed
      `0..|V|-1`, gauge qubits indexed `|V|..|V|+|E|-1` (one fixed,
      documented convention, never ad hoc per call site).
- [x] T006 [US1] Implement `_gauss_law_generators(graph)` in
      `src/fourierlearn/z2lgt.py`: one `G_v = Z_v · ∏_{e∋v} X_e` per
      vertex (report eq. 5), built via the existing, unmodified
      `pauli_pqc._pad_to_full_width_little_endian` helper — never a
      hand-rolled padding (depends on T005).
- [x] T007 [US1] Implement `build_z2_lgt_model(graph, mass_couplings,
      electric_couplings, hopping_couplings) -> PhysicalModelDescription`
      in `src/fourierlearn/z2lgt.py`: build one `CouplingGroup` per vertex
      for mass (weight `(-1)^v`, label `f"mass_{v}"`), one per edge for
      electric (weight `1.0`, label `f"electric_{e}"`), one per edge for
      hopping (`A_e`, `B_e` terms both weight `0.5`, one shared label
      `f"hopping_{e}"` — ties them via the existing, unmodified
      `CouplingGroup` tie-group mechanism, Constitution §11.2), declared
      in the fixed order mass → electric → hopping (gate contiguity,
      T004), and **always** attaches the `_gauss_law_generators(graph)`
      result as a non-optional `SymmetryDeclaration` (never `None` — this
      is what makes Spec 7's existing enforcement run unconditionally,
      Critical Mandate 1) (depends on T005, T006).
- [x] T008 [US1] Reject a zero mass/electric/hopping coupling explicitly
      in `build_z2_lgt_model` (reuse Spec 6's existing `ZeroCouplingError`
      pattern/message style for consistency, not a new error type unless
      the existing one cannot be imported cleanly — if it cannot, define
      a locally-scoped equivalent in `z2lgt.py` with the same rationale)
      (depends on T007). **Done**: imports `ZeroCouplingError` directly
      from `fourierlearn.models` (no local equivalent defined), per the
      critical implementation instruction resolving this task's stated
      ambiguity.
- [x] T009 [US1] Run T002-T004 against T005-T008's implementation; fix
      until green. `mypy src/fourierlearn/z2lgt.py` clean.

**Checkpoint**: User Story 1 is fully functional and independently
testable — a caller can build a real, Gauss-law-verified ansatz for any
declared matter+gauge lattice.

---

## Phase 4: User Story 2 - Tie the hopping generators A_e and B_e to one shared parameter per edge (Priority: P2)

**Goal**: Computationally confirm (not merely construct) that the tied
`A_e`/`B_e` split is exact (no Trotter error) and that untying them
genuinely breaks `U(1)_Q`.

**Independent Test**: Build both a tied and an untied two-gate sequence
for one edge and compare `Operator`s/commutators directly — this does
**not** require User Story 1's `build_z2_lgt_model` to exist; it only
needs the already-existing, unmodified `CouplingGroup`/`build_ir`
mechanism (research.md R3 built and verified this exact way).

### Tests for User Story 2 ⚠️

- [x] T010 [P] [US2] Write `tests/unit/test_z2lgt_tying_exactness.py`:
      using a shared test-only fixture (T012), build the **tied**
      two-gate sequence for one edge, bind a concrete `alpha`, and assert
      its `Operator` equals `scipy.linalg.expm(1j*pi*alpha*(A_e+B_e))`
      to machine precision (`< 1e-10`) — a dedicated `Operator`-
      equivalence test, independent of any coefficient-level test (this
      project's own standing rule for gate-construction claims;
      reproduces research.md R3(a)).
- [x] T011 [P] [US2] Write `tests/unit/test_z2lgt_untying_breaks_charge.py`:
      using the same shared fixture (T012) built with two **independent**
      parameters, assert the resulting `Operator` does **not** commute
      with `Q = Σ_v Z_v` at two distinct concrete angles
      (`max|[U,Q]| > 0.1`), and assert it **does** commute exactly
      (`< 1e-10`) when the two angles are set equal — the sanity control
      isolating that independence, specifically, is the failure mode
      (reproduces research.md R3(b)).

### Implementation for User Story 2

- [x] T012 [P] [US2] Implement a shared, test-only fixture helper
      `two_gate_circuit(a_param_label, b_param_label)` in
      `tests/unit/_hopping_fixtures.py` (mirrors research.md R3 verbatim):
      builds the bare 3-qubit `A_e`-then-`B_e` circuit via
      `encodings.pauli_pqc.PauliUpload`/`build_ir` directly (coefficient
      `1.0` for both terms, reproducing Proposition 5.1(iii) in its own
      literal form) — used by both T010 and T011, so the construction is
      not duplicated across the two test files. **No new `src/` code is
      needed for tying itself** — Constitution §9.4: tying already exists
      via the unmodified `CouplingGroup` mechanism (T007 already uses it
      for the full model; this task only isolates it for a standalone,
      minimal proof).
- [x] T013 [US2] Run T010-T011 against T012's fixture; fix until green.

**Checkpoint**: User Story 2 is fully functional and independently
testable, with no dependency on User Story 1.

---

## Phase 5: User Story 3 - Verify the ansatz's active frequencies are contained in, and strictly fewer than, the ambient frequency box (Priority: P3)

**Goal**: Compute `Λ` (Theorem 6.1), extract `Ω` via the oracle, and
assert `Ω ⊆ Λ ⊊ ambient` on a real instance — honestly labeled as a
constant-factor effect, never a separation claim.

**Independent Test**: On the research.md R2 fixture, compute `Λ`,
extract `Ω`, and confirm containment with a concrete, exact reduction
factor — reusing User Story 1's `build_z2_lgt_model` for the concrete
ansatz circuit (a disclosed, reasonable dependency; spec.md permits a
story to "integrate with US1/US2" while remaining independently
testable), but not reusing or duplicating its CI-guard/oracle-access
concerns, which are wholly new to this story.

### Sub-phase A: Scalable CI exemption (Guardrail 1 — must precede T024)

- [x] T014 [US3] In `tests/ci/test_no_forbidden_imports.py`: widen
      `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` from
      `"_exact_dynamics.py"` (a `str`) to
      `("_exact_dynamics.py", "_containment_oracle_check.py")` (a
      `tuple[str, ...]`); change `find_violations`'s internal check from
      `path.name == narrow_exempt_module` to
      `path.name in narrow_exempt_module` (its default value becomes the
      widened tuple, so every existing call site that omits this
      parameter is unaffected); update the existing
      `test_narrow_exemption_still_rejects_statevector_and_operator` and
      `test_narrow_exemption_waives_only_reference_for_the_named_module`
      (both currently do
      `tmp_path / _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY`, which breaks once
      the constant is a tuple) to instead use
      `tmp_path / _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[0]`, preserving
      their exact existing assertions unchanged (they still test the
      `_exact_dynamics.py` case specifically).
- [x] T015 [P] [US3] Add
      `test_narrow_exemption_generalizes_to_a_second_module` to
      `tests/ci/test_no_forbidden_imports.py`: independently reproduces
      T014's two updated tests' exact assertions but indexed at
      `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[1]`
      (`"_containment_oracle_check.py"`) — proving the widened mechanism
      genuinely generalizes to a second, independent module rather than
      being special-cased for exactly two hardcoded names (Guardrail 1).
- [x] T016 [US3] Run the full `tests/ci/test_no_forbidden_imports.py`
      suite (including `test_narrow_exemption_does_not_widen_to_other_modules`,
      unaffected by this change); confirm every test green before
      proceeding to T024, which depends on this exemption existing.

### Sub-phase B: Λ computation and its independent controls

- [x] T017 [P] [US3] Write `tests/unit/test_containment_lambda_predicate.py`:
      the 7 hand-derived positive/negative controls from research.md R2
      (evenness, charge-only failure, Gauss-only failure, combined pass)
      against `containment.compute_lambda`'s predicate, hand-derived
      *before* running (not fitted to the implementation's output, per
      research.md's own documented practice) — written to fail first (the
      module does not exist yet).
- [x] T018 [US3] Implement `compute_ambient_box(ir)` and
      `compute_lambda(ir, mass_axes, electric_axes, hopping_axes,
      incidence)` in `src/fourierlearn/containment.py`: `compute_ambient_box`
      reuses `frequency.pre_parity_range` per parameter (no new logic);
      `compute_lambda` applies Theorem 6.1 eq. 36 (additive charge, on raw
      `l`, over `mass_axes` only) and eq. 37 (multiplicative Gauss, on
      `l/2 mod 2`, per vertex via `incidence`) — taking the coordinate-
      role metadata as explicit arguments (never hardcoded to one
      instance); no `Statevector`/`Operator`/`expm`/`reference` import.
- [x] T019 [US3] Run T017 against T018's implementation; fix until green.
      `mypy src/fourierlearn/containment.py` clean.

### Sub-phase C: State-prep flip (Guardrail 3)

- [x] T020 [P] [US3] Write
      `tests/oracle/test_z2lgt_state_prep_degeneracy_regression.py`:
      reproduces research.md R2's caught degeneracy directly — on the
      *unflipped* (default) fixture, extracting the exact oracle's
      coefficients for the hopping-only observable gives a frequency
      support of `{(0,0,0,0)}` only (the `h_e`-zero-eigenspace
      degeneracy) — a regression control proving the upcoming fix (T021)
      is load-bearing, not cosmetic. This test asserts the *degenerate*
      behavior explicitly, so a future accidental fix of the underlying
      physics (unlikely, but possible via an unrelated refactor) is
      caught as a meaningful change, not silently absorbed.
- [x] T021 [US3] Implement the state-prep flip in
      `src/fourierlearn/z2lgt.py`: add an optional, defaulted
      `initial_occupation: tuple[int, ...] = ()` parameter to
      `build_z2_lgt_model` — for each matter site index in
      `initial_occupation`, prepend a `FixedGate(XGate(), (site,))` to the
      returned model's gate sequence ahead of every parameterized gate
      (never changing existing behavior when `initial_occupation=()`, so
      T002-T009's tests remain valid unchanged) (depends on T007).
- [x] T022 [US3] Write
      `tests/oracle/test_z2lgt_state_prep_flip_resolves_degeneracy.py`:
      the positive counterpart to T020 — with `initial_occupation`
      set to place the matter pair in the off-diagonal sector (research.md
      R2's exact fixture), the extracted frequency support is genuinely
      non-degenerate (`|Ω| == 2`, at `(0, ±4, 0, 0)` — reproduces
      research.md R2's own executed numbers exactly).
- [x] T023 [US3] Run T020 and T022 against T021's implementation; fix
      until both pass (T020 passes by correctly reproducing the
      degeneracy; T022 passes by correctly resolving it).

### Sub-phase D: Oracle-based Ω extraction and the full containment proof (Guardrail 2)

- [x] T024 [US3] Implement the single function in
      `src/fourierlearn/_containment_oracle_check.py` that calls
      `reference.coefficients(ir, budget=..., confirm=...)` and returns
      the extracted `{frequency: coefficient}` dict unchanged — the one
      production import of `fourierlearn.reference` outside `reference.py`
      itself for this feature, isolated in its own single-function module
      per Spec 6's `_exact_dynamics.py` precedent; never used for training
      or feature construction (depends on T014-T016).
- [x] T025 [US3] Implement `ContainmentVerificationResult` (fields:
      `ambient_size: int`, `lambda_size: int`, `omega: frozenset[tuple[int,...]]`,
      `reduction_factor: float`, `no_separation_caveat: str`) and
      `verify_containment(ir, observable, mass_axes, electric_axes,
      hopping_axes, incidence, budget=..., confirm=...)` in
      `src/fourierlearn/containment.py`: composes `compute_ambient_box`/
      `compute_lambda` (T018) with the oracle-extracted `Ω` (T024),
      asserts `Ω ⊆ Λ` (raising a dedicated `DerivationDefectError` if not
      — Constitution §11.6, never silently tolerated) and `Λ ⊊ ambient`
      (strict), and populates `reduction_factor` **only** from the exact
      computed `ambient_size / lambda_size` for this declared instance —
      `no_separation_caveat` is a required, non-empty, always-populated
      field (never optional prose) stating this is a constant-factor
      effect and no separation claim is made on this validation platform
      (Constitution §11.7/§11.8, Guardrail 2) (depends on T018, T024).
- [x] T026 [P] [US3] Write
      `tests/oracle/test_containment_omega_subset_lambda.py`: end to end,
      on the research.md R2 fixture with the state-prep flip (T021)
      applied, asserts `Ω ⊆ Λ ⊊ ambient` holds, asserts
      `result.reduction_factor == 45.0` exactly (the fixture's own
      computed value) and asserts this is explicitly **not** equal to
      `2 ** -(d + abs(V))`'s reciprocal (`64`) — the asymptotic
      CLT-heuristic value research.md found does not match at this
      instance's finite `L=1` — and asserts `result.no_separation_caveat`
      is a non-empty string on every call (Guardrail 2, structurally
      enforced, not just documented).
- [x] T027 [US3] Run T026 and the full project test suite (`pytest`);
      fix until every test is green. `mypy` clean across
      `src/fourierlearn/z2lgt.py`, `containment.py`, and
      `_containment_oracle_check.py`.

**Checkpoint**: All three user stories are independently functional; the
full Spec 8 deliverable (equivariant ansatz, verified tying, verified
containment) is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 [P] Add module-level docstrings to `z2lgt.py`, `containment.py`,
      and `_containment_oracle_check.py` citing the exact report
      sections/equations each function implements (eq. 1-5, 25-27, 36-37;
      Constitution §2.1/§2.2/§2.5 discipline), matching this project's
      established documentation style (see `symmetry.py`'s own module
      docstring for the precedent).
- [x] T029 Determine, and record the determination in
      `.specify/memory/extension-register.md`, whether any part of this
      feature's implementation constitutes a Constitution §2.3 `EXTENSION`
      beyond the primary source. Per research.md R1, the Hamiltonian
      itself is **not** an extension (cited to §5.1-5.3/eq. 25-27); this
      task confirms whether any other implementation choice (e.g. the
      specific `build_z2_lgt_model`/`compute_lambda` function signatures,
      which are this codebase's own API design, not physics content)
      warrants a register entry — if none does, record that explicit
      "no extension" finding rather than leaving the question
      unaddressed.
- [x] T030 Run the complete project test suite (`pytest`) and `mypy`
      across all of `src/fourierlearn/` one final time; confirm the
      combined Spec 1-8 suite is fully green before requesting review.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Empty — nothing blocks any user story at the
  project level (see Phase 2's own note).
- **User Story 1 (Phase 3)**: Depends only on Setup. No dependency on
  User Stories 2 or 3.
- **User Story 2 (Phase 4)**: Depends only on Setup. Fully independent of
  User Story 1 (uses `CouplingGroup`/`build_ir` directly, not
  `build_z2_lgt_model`).
- **User Story 3 (Phase 5)**: Depends on Setup; its containment proof
  (T026) depends on User Story 1's `build_z2_lgt_model` existing (T007)
  and its state-prep flip (T021, itself layered onto T007) — so in
  practice, User Story 3's sub-phase D should follow User Story 1's
  completion, even though sub-phases A-C (T014-T023) can start immediately
  and in parallel with User Stories 1-2.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within User Story 3

- T014 → T015 → T016 (CI-guard widening, sequential: same file, one
  logical change).
- T016 → T024 (the oracle-check module needs the exemption to exist
  first).
- T017 → T018 → T019 (Λ predicate: test-first, then implement, then run).
- T020 → T021 → T022 → T023 (state-prep: regression control first,
  then the fix, then its positive counterpart, then run both).
- T007 (US1) and T021 → T024, T025 → T026 → T027 (the full containment
  proof needs the ansatz (T007), the flip (T021), the oracle module
  (T024), and the Λ/result composition (T025) all in place first).

### Parallel Opportunities

- T002, T003, T004 (US1 tests, different files, no dependencies among
  them).
- T010, T011, T012 (US2: the two tests and their shared fixture can be
  drafted in parallel, since the fixture's shape is fully specified by
  research.md R3 already — but T010/T011 cannot be run green until T012
  exists).
- T015 (independent test file addition, parallel with T017-T023 once
  T014 lands).
- T017 and T020 (different files, independent claims — Λ's predicate vs.
  the state-prep degeneracy — can be developed in parallel).
- T026 and T028 (final proof test vs. documentation polish, once their
  respective dependencies are met).
- User Stories 1 and 2 can be staffed and completed entirely in parallel
  by different developers; User Story 3's sub-phases A-C can proceed in
  parallel with both, with only its final sub-phase D waiting on User
  Story 1.

---

## Parallel Example: User Story 1

```bash
# Launch all three US1 tests together (different files, no dependencies):
Task: "Write tests/unit/test_z2lgt_hamiltonian_construction.py"
Task: "Write tests/unit/test_z2lgt_gauss_law_hook.py"
Task: "Write tests/unit/test_z2lgt_gate_contiguity.py"
```

## Parallel Example: User Story 3, sub-phases A and C

```bash
# T014-T016 (CI guard) and T020 (degeneracy regression control) touch
# entirely different files and have no dependency on each other:
Task: "Widen _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY to a tuple in tests/ci/test_no_forbidden_imports.py"
Task: "Write tests/oracle/test_z2lgt_state_prep_degeneracy_regression.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 3: User Story 1 (T002-T009).
3. **STOP and VALIDATE**: a real, Gauss-law-verified equivariant ansatz
   exists and is independently testable — this alone is a genuine,
   demonstrable increment of Constitution §11.0's stated research target.

### Incremental Delivery

1. Setup → User Story 1 (MVP: the ansatz itself, verified equivariant).
2. Add User Story 2 (the tying proof) → test independently → demonstrates
   Critical Mandate/Deliverable (b) is not just constructed but *proven*.
3. Add User Story 3 (the containment proof) → test independently →
   demonstrates Deliverable (c), the full `Ω ⊆ Λ ⊊ ambient` claim, honestly
   scoped per Guardrail 2.
4. Polish (Phase 6).

### Parallel Team Strategy

With multiple developers: one completes User Story 1 (T002-T009), a
second completes User Story 2 (T010-T013) entirely independently, and a
third begins User Story 3's sub-phases A-C (T014-T023) immediately,
joining sub-phase D (T024-T027) once User Story 1's `build_z2_lgt_model`
lands.

---

## Notes

- `[P]` tasks = different files, no dependencies.
- `[Story]` label maps task to specific user story for traceability.
- Every test task is written, and confirmed to fail, before its
  corresponding implementation task — this project's own established
  discipline (Specs 5-7), continued unchanged.
- No task in this list introduces caching, batching, memoization, or any
  other unprofiled optimisation (Constitution §5.3, Guardrail 4) — every
  new function is a single, direct, small-instance computation with
  nothing to profile at this feature's declared scope.
- Commit after each task or logical group; stop at either checkpoint to
  validate a story independently before continuing.
