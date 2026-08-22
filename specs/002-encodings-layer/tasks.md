---

description: "Task list for Encodings Layer implementation"
---

# Tasks: Encodings Layer

**Input**: Design documents from `/specs/002-encodings-layer/`

**Prerequisites**: plan.md, spec.md, research.md (present); data-model.md, contracts/,
quickstart.md deliberately not generated for this spec — plan.md's Project Structure
scopes them out; research.md R1–R3 carry the data shapes/contracts instead.

**Tests**: Included — the feature spec itself requires an oracle-backed validation
suite per frontend (FR-011–FR-013, SC-003, SC-004) and several specific non-trivial
rejection/ordering checks (research.md R5, R6, R7) that this list schedules
test-first, per explicit instruction. Every rejection check called out by the
architect ahead of time (non-commuting tie groups, `tau=0`) gets its own dedicated
test task, scheduled strictly before the implementation task it guards — not folded
into a larger, harder-to-audit test task.

**Organization**: Tasks are grouped by user story (US1–US3, from spec.md). Unlike
Spec 1, where dependency order and priority order diverged, **here priority order
and dependency order coincide exactly**: US1 (Pauli-PQC) is the more primitive
frontend US2 (Trotter) must delegate to (FR-009), and US3 (oracle validation) needs
both frontends to already exist. No "Phase Ordering Deviation" section is needed —
build in the order the phases below are written.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task names the FR(s)/SC(s) it satisfies, and the research.md decision (R1–R9)
  it implements or verifies where applicable — no task in this list is untraceable.
- **Zero tasks in this list introduce caching, batching, or parameterised-template
  reuse of any kind** (Constitution §5.3, research.md R9) — this is enforced by
  omission throughout, and checked explicitly in Polish (T019).

## Path Conventions

Continuation of the single project from Spec 1: `src/fourierlearn/`, `tests/` at
repository root. New subpackage: `src/fourierlearn/encodings/`. No existing Spec 1
file (`frequency.py`, `ir.py`, `contracts.py`, `reference.py`) is modified by any
task below — every task here only imports from them.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new subpackage; no story-specific logic yet.

- [x] T001 Create the `src/fourierlearn/encodings/` package skeleton: `__init__.py`,
  and empty placeholder modules `pauli_pqc.py` (module docstring only — will hold
  `PauliUpload`/`build_ir`, research.md R2) and `trotter.py` (module docstring only —
  will hold `CouplingGroupTerm`/`CouplingGroup`/`trotter_frontend`, research.md R3) —
  scaffolds **FR-001**, **FR-006** (plan.md Project Structure, research.md R1).

**Checkpoint**: Package skeleton exists; nothing importable yet beyond empty modules.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The one prerequisite every user story implicitly relies on: that the
Foundation Layer this spec builds on top of is still exactly as verified, since all
three stories import `frequency.py`, `ir.py`, `contracts.py`, and (US3 only)
`reference.py` without modifying any of them.

**⚠️ CRITICAL**: No user story's test results can be trusted if this regresses.

- [x] T002 Run the existing Spec 1 suite (`pytest tests/ -v` and `mypy
  src/fourierlearn/`) and confirm it is green **before** adding any encodings code —
  this spec modifies no Spec 1 file, so a failure here means the environment, not
  this feature, is the problem, and must be resolved before proceeding — prerequisite
  for **FR-001** through **FR-013** (plan.md Constraints: "No existing Spec 1 file is
  modified").

**Checkpoint**: Foundation Layer confirmed intact. User story work may begin, in
priority order (US1 → US2 → US3 below).

---

## Phase 3: User Story 1 - Build a feature map from a list of Pauli strings (Priority: P1) 🎯 MVP

**Goal**: `pauli_pqc.py`'s `build_ir()` lowers an ordered list of `PauliUpload`s into
a Foundation-Layer `PauliEncodedCircuitIR`, delegating all structural validation
(tie-group size/coefficient uniformity, qubit bounds, Hermiticity) to
`PauliEncodedCircuitIR`'s own constructor, while itself owning the two checks Spec 1
does **not** perform: rejecting an empty upload sequence (research.md R2) and
rejecting a tie group whose Pauli strings do not pairwise commute (research.md R6,
Constitution §9.5/§11.2).

**Independent Test** (from spec.md): Supply a small, explicit list of Pauli strings,
including at least one tied pair, and confirm the resulting IR's per-parameter
upload count, multiplicity, and coefficients match what was supplied — independent
of any Hamiltonian or evolution-time concept.

### Tests for User Story 1 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T003 [US1] Write the core `build_ir` acceptance tests in
  `tests/unit/test_pauli_pqc.py`: (a) an ordered list of uploads each tied to its own
  distinct parameter yields one upload per parameter, in supplied order, with the
  supplied coefficients (Acceptance Scenario 1); (b) two uploads tied to the same
  parameter within one declared tie group (multiplicity `r_j = 2`) yields
  `multiplicity == 2` for that parameter, not two independent parameters (Acceptance
  Scenario 2); (c) the same parameter uploaded more than once, untied, yields an
  upload count equal to the repetition count (Acceptance Scenario 3); (d) an empty
  `uploads` sequence raises rather than returning a zero-parameter IR (Acceptance
  Scenario 4); (e) two uploads tied to one parameter with **different** coefficients
  raises Spec 1's own `ValueError` (FR-007 in `ir.py`) uncaught and unmodified — this
  is a deliberate design choice, not an oversight: `build_ir` MUST NOT duplicate
  Spec 1's own coefficient-uniformity validation logic (Constitution §9.4 — no
  duplicated call paths), so this assertion proves `build_ir` propagates Spec 1's
  own rejection rather than re-implementing or swallowing it — **FR-001**, **FR-002**,
  **FR-003**, **FR-004**, **FR-005**.
- [x] T004 [US1] Write the dedicated non-commuting tie-group rejection tests in
  `tests/unit/test_pauli_pqc.py` (`test_build_ir_rejects_noncommuting_tie_group`):
  (a) two uploads tied to the same parameter and tie group, Pauli strings `'X'` and
  `'Z'` on the **same** qubit, on a 1-qubit register (verified non-commuting,
  research.md R6's direct matrix check), asserted to raise — with a message naming
  the offending parameter/tie group, not a generic Spec 1 message; (b) a second,
  dedicated case on a **3-qubit** register (`num_qubits=3`) with overlapping
  operators on a higher-index qubit: one upload `pauli='XZ'`, `qubits=(0, 2)` (`X` on
  qubit 0, `Z` on qubit 2, per this project's own left-to-right `pauli[i]`-acts-on-
  `qubits[i]` convention) tied to a second upload `pauli='Y'`, `qubits=(2,)` — `Z`@2
  and `Y`@2 anticommute (an odd number of anticommuting single-qubit positions once
  qubit 0's `X`-vs-identity trivially commutes), so the pair overall anticommutes and
  the tie group must be rejected. This second case specifically exercises the
  little-endian padding/reversal at a qubit index **other than 0** (this project's
  own pinned little-endian trap — see the pauli-gate-sign-convention memory): a
  reversal bug would place the `Z` at the wrong register position and could silently
  evaluate commutativity against the wrong qubit instead of raising, a defect the
  1-qubit case in (a) is structurally incapable of catching. Both cases asserted to
  raise **before** the commutativity-check helper exists (T006), so this test is
  confirmed failing for the right reason first — Constitution §9.5, §11.2; **FR-003**
  (research.md R6). *(Guardrail: dedicated R6 rejection tests, including a
  multi-qubit/higher-index case, scheduled before their implementation task.)*

### Implementation for User Story 1

- [x] T005 [US1] Implement the `PauliUpload` dataclass and `build_ir()` core in
  `src/fourierlearn/encodings/pauli_pqc.py`: map each distinct `parameter_label` to a
  canonical integer `parameter_index` via `frequency.coordinate_order` (the same
  function `PauliEncodedCircuitIR.parameters()` already uses — no independent
  ordering rule is invented here); build one `PauliTerm` per upload, preserving
  supplied order and tie structure exactly; raise on an empty `uploads` sequence
  (research.md R2 — Spec 1's own `_validate_tying()` does not itself reject zero
  gates); construct and return the `PauliEncodedCircuitIR`, letting its own
  constructor perform tie-group size/coefficient-uniformity/qubit-bounds/Hermiticity
  validation without any re-validation of what Spec 1 already checks. **This
  delegation is intentional, not incomplete**: `build_ir` deliberately does not
  re-implement tie-group coefficient-uniformity checking — that logic already exists,
  correctly, in `PauliEncodedCircuitIR`'s own constructor (Spec 1 FR-007), and
  duplicating it here would create exactly the two-call-paths-for-one-invariant
  situation Constitution §9.4 prohibits — **FR-001**, **FR-002**, **FR-003**,
  **FR-004**, **FR-005** (depends on T003; makes it pass).
- [x] T006 [US1] Implement the shared tie-group commutativity-check helper in
  `src/fourierlearn/encodings/pauli_pqc.py`, invoked by `build_ir` for every declared
  tie group of size ≥ 2 (before delegating to `PauliEncodedCircuitIR`): pad each
  term's own `pauli`/`qubits` to the full `num_qubits` width with `'I'` elsewhere,
  reversed for the little-endian convention `ir.py` already uses (this project's own
  pinned little-endian trap — see the pauli-gate-sign-convention memory), and check
  every pair within the tie group via `qiskit.quantum_info.Pauli.commutes()` on the
  padded, full-width labels (not `Pauli.commutes(..., qargs=...)`, which research.md
  R6 found raises `IndexError` on mismatched-width operands); raise `ValueError`
  naming the parameter/tie group on the first non-commuting pair found — Constitution
  §9.5, §11.2; **FR-003** (research.md R6) (depends on T004, T005; makes T004 pass).

**Checkpoint**: `pauli_pqc.py` complete and independently testable — `trotter.py`
does not exist yet, and this frontend has no dependency on it (research.md R1).

---

## Phase 4: User Story 2 - Build a feature map for an unknown Hamiltonian coupling, at a fixed evolution time and Trotter depth (Priority: P2)

**Goal**: `trotter.py`'s `trotter_frontend()` lowers one or more caller-declared
`CouplingGroup`s, a fixed `τ`, and a fixed `r` into a `PauliEncodedCircuitIR`, giving
each coupling group its own encoded parameter with per-term coefficient
`c = -h·τ/(π·r)` (research.md R4), composing multiple groups in the caller's declared
order once per Trotter step (research.md R5), and delegating all IR construction —
including the commutativity check from US1 — to `pauli_pqc.build_ir()` rather than
reimplementing it (FR-009, Constitution §9.4).

**Independent Test** (from spec.md): Supply a small Hamiltonian grouped by shared
unknown coupling (at least one group with two tied terms), a fixed `τ`, and a fixed
`r`, and confirm the resulting IR gives each group its own parameter with the correct
per-term coefficient and upload count `r`.

### Tests for User Story 2 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [x] T007 [US2] Write the core `trotter_frontend` acceptance tests in
  `tests/unit/test_trotter.py`: (a) two coupling groups yield two separate encoded
  parameters, each with upload count `r` (Acceptance Scenario 1); (b) a group with two
  tied, same-weight terms yields multiplicity 2 and an identical coefficient
  `c = -h·τ/(π·r)` on both terms (Acceptance Scenario 2, research.md R4's verified
  formula — recompute the exact expected float from `h`, `τ`, `r` in the test itself,
  do not hardcode a value copied from research.md's illustrative decimals); (c) a
  larger fixed `r` scales the upload count and rescales every coefficient consistently
  with the same formula (Acceptance Scenario 3); (d) `r <= 0` raises (Acceptance
  Scenario 4); (e) zero Pauli strings in a declared group, or no groups at all, raises
  (Acceptance Scenario 6) — **FR-006**, **FR-007**, **FR-009**, **FR-010**.
- [x] T008 [US2] Write the dedicated non-uniform-weight rejection test in
  `tests/unit/test_trotter.py` (`test_trotter_frontend_rejects_nonuniform_group_weight`):
  a coupling group whose two terms declare **different** structural weights `h`
  raises, with a message naming the offending group — "sharing a coupling" alone
  must not be treated as satisfying uniformity (Edge Cases) — **before** the
  weight-uniformity check exists (T012) — **FR-008**.
- [x] T009 [US2] Write the dedicated zero-evolution-time rejection test in
  `tests/unit/test_trotter.py` (`test_trotter_frontend_rejects_zero_evolution_time`):
  `trotter_frontend(groups, tau=0.0, r=5, ...)` is asserted to raise **directly** —
  per explicit instruction, not inferred from Spec 1's separately-scoped
  coefficient-must-not-be-zero rejection — with a message naming evolution time as
  the problem, not a generic downstream IR error — **before** this check exists
  (T012) — **FR-010** (research.md R7). *(Guardrail: dedicated R7 rejection test,
  scheduled before its implementation task.)*
- [x] T010 [US2] Write the dedicated non-commuting coupling-group rejection test in
  `tests/unit/test_trotter.py` (`test_trotter_frontend_rejects_noncommuting_group`): a
  coupling group with two tied terms `'X'` and `'Z'` on the same qubit is asserted to
  raise when lowered through `trotter_frontend` — confirming that FR-009's reuse of
  `build_ir` actually reaches the US1 commutativity check (T006) rather than being
  bypassed by Trotter's own group-to-`PauliUpload` translation — **before** T013
  exists to make this concrete path work — Constitution §9.4; **FR-009** (research.md
  R6, R7). *(Guardrail: dedicated R6-via-Trotter rejection test, scheduled before its
  implementation task.)*
- [x] T011 [US2] Write the caller-declared group-order composition test in
  `tests/unit/test_trotter.py`
  (`test_trotter_frontend_preserves_declared_group_order`): reproduce research.md
  R5's verified two-group, deliberately non-commuting construction — Group A: a
  single `'ZZ'` term on qubits `(0, 1)`, weight `1.3`; Group B: a single `'X'` term on
  qubit `0`, weight `-0.7` — with a fixed `τ` and `r = 4`, lower it via
  `trotter_frontend`, bind concrete coupling values (`α_A = 0.62`, `α_B = -0.44`,
  matching R5's own verification), and assert the resulting circuit's `Operator`
  matches the **interleaved** reference unitary
  `(exp(-i·h_B·α_B·X₀·(τ/r)) @ exp(-i·h_A·α_A·(Z⊗Z)·(τ/r)))^r` (A applied first each
  step, matching the caller's declared A-then-B order) to floating-point precision —
  **and separately assert it does NOT match** the "block" ordering (`r` reps of A's
  gate followed by `r` reps of B's gate), which research.md R5 confirmed gives a
  numerically different unitary for this same non-commuting pair. Asserting both the
  match and the mismatch is what makes this test actually discriminate on order,
  rather than passing vacuously on a construction where every ordering happens to
  coincide — **FR-006**, **FR-007**, **FR-009** (research.md R5). *(Guardrail:
  caller-order-preservation test, strict A-then-B assertion plus a discriminating
  negative check.)*

### Implementation for User Story 2

- [x] T012 [US2] Implement `CouplingGroupTerm`, `CouplingGroup`, and
  `trotter_frontend()`'s own input validation in `src/fourierlearn/encodings/trotter.py`:
  raise, each with a message naming the actual problem, on `r <= 0`; a declared group
  with zero terms; no groups declared at all; or a declared group whose terms'
  weights are not all identical — **FR-008**, **FR-010** (research.md R7). **Check
  `tau` against zero via `math.isclose(tau, 0.0, abs_tol=1e-15)` (equivalently, a bare
  `tau == 0.0` also satisfies this — either form rejects cleanly)** rather than any
  looser or relative tolerance, so both a literal `tau = 0.0` and a floating-point
  value indistinguishable from zero at that absolute tolerance are treated identically
  as the degenerate case FR-010/Edge Cases requires rejecting — a relative-tolerance
  check would be wrong here since it is undefined/unstable exactly at zero (depends on
  T008, T009; makes them pass).
- [x] T013 [US2] Implement `trotter_frontend()`'s coefficient computation and
  multi-group composition in `src/fourierlearn/encodings/trotter.py`: compute
  `c = -h·τ/(π·r)` per term (research.md R4's verified derivation — the sign is
  load-bearing, confirmed against the actual target unitary, not assumed from the
  originally-proposed positive-sign formula); build one tied `PauliUpload` group per
  declared `CouplingGroup` (multiplicity equal to that group's term count, upload
  count `r`); for each of the `r` Trotter steps, emit every declared group once, in
  the caller's supplied order (research.md R5's verified interleaved convention, not
  a "block" ordering); pass the resulting `PauliUpload` sequence to
  `pauli_pqc.build_ir()` rather than re-implementing any IR-construction or
  commutativity-checking logic (Constitution §9.4) — **FR-006**, **FR-007**,
  **FR-009** (research.md R4, R5; R6 covered by delegation to T006 via `build_ir`)
  (depends on T007, T010, T011, T012; makes T007, T010, T011 pass).

**Checkpoint**: `trotter.py` complete and independently testable; it imports
`pauli_pqc.build_ir` and duplicates none of its logic (research.md R1, R9).

---

## Phase 5: User Story 3 - Validate both frontends against exact ground truth, with a test that could actually fail (Priority: P3)

**Goal**: Both frontends' lowered IR instances, run through Spec 1's reference
oracle, reproduce independently pre-verified analytic Fourier coefficients —
including, for each frontend separately, a non-DC coefficient with individually
nonzero real and imaginary parts, so that a per-upload coefficient-scaling defect
cannot hide behind an accidentally-real-valued test case (Constitution §6.4, §4.3).

**Independent Test** (from spec.md): Take each frontend's own validation circuit,
lower it, run it through the Foundation Layer's oracle, and confirm the returned
coefficients match pre-verified analytic values — including at least one non-DC
coefficient with both parts individually nonzero, for each frontend separately.

### Tests for User Story 3 ⚠️

- [x] T014 [US3] Write the genuinely-complex Pauli-PQC oracle validation test in
  `tests/oracle/test_encodings_validation.py`: build the one-qubit, two-untied-upload
  circuit from research.md R8 via `build_ir` — first upload `'X'`, second upload
  `'Z'`, coefficient `1.0` for both, observable `SparsePauliOp(['X', 'Y'], coeffs=[1,
  1])` — run it through `fourierlearn.reference.coefficients()`, and assert the
  `l=4` coefficient matches its exact recomputed analytic value (research.md R8's
  verified approximate figure is `-0.25-0.25j`; recompute to full precision rather
  than hardcoding the rounded decimal) to relative error ≤ 1e-9. **Include, as a code
  comment directly above the observable, exactly why the combined `X+Y` observable is
  used**: a plain `X`, `Y`, or `Z` observable alone gives a purely real or purely
  imaginary result for this specific construction (research.md R8, confirmed by
  direct search over single- and paired-Pauli observables) — the combined observable
  is what breaks that degeneracy. Assert the `l=4` coefficient's real part and
  imaginary part **individually** exceed a numeric tolerance (not merely that the
  coefficient's magnitude is nonzero) — **FR-011**, **FR-013**, **SC-003** (research.md
  R8). *(Guardrail: degeneracy documented inline, both parts asserted individually.)*
- [x] T015 [US3] Write the genuinely-complex Trotter oracle validation test in
  `tests/oracle/test_encodings_validation.py`: build the two-qubit, two-coupling-group
  circuit from research.md R8 via `trotter_frontend` — Group A: a single `'X'` term
  (qubit 0, weight `1.0`); Group B: two tied, commuting terms `'ZZ'` + `'XX'` (qubits
  `(0, 1)`, weight `1.0` each, multiplicity `r_j = 2`) — with `τ = 0.8`, `r = 2`,
  observable `SparsePauliOp(['IX', 'IY'], coeffs=[1, 1])` **(corrected during
  `/speckit-implement`, research.md R8's addendum — the originally-drafted single-label
  `'IX'` observable at `l=(0, 1)` was verified computationally to give a purely real
  spectrum for every single-Pauli-string observable, a structural degeneracy this
  gate set shares with the Pauli-PQC case above; a combined real+imaginary
  observable is required for the same reason `X+Y` was required there)**; run it
  through `fourierlearn.reference.coefficients()`, and assert the `l=(2, 4)`
  coefficient matches its exact recomputed analytic value (verified against the
  oracle directly: `-0.125+0.125j`, i.e. exactly `-1/8+1/8j` to float precision) to
  relative error ≤ 1e-9, with the real and imaginary parts asserted individually
  nonzero beyond tolerance. This single construction exercises both multi-group
  composition (research.md R5) and tied multiplicity (research.md R6)
  simultaneously, as FR-012 explicitly requires — **FR-012**, **FR-013**, **SC-003**
  (research.md R8).
- [x] T016 [US3] Verify SC-004's sensitivity claim by deliberate, temporary construction:
  one at a time, introduce an incorrect per-upload coefficient scaling into each
  frontend (e.g. drop the negative sign in `trotter.py`'s `c = -h·τ/(π·r)`, or divide
  by `r - 1` instead of `r`) and confirm the corresponding validation test (T014 or
  T015) fails as a result; revert the deliberate defect immediately after each check —
  the defect must not remain in the codebase at the end of this task — **SC-004**
  (Constitution §4.3 — an agreement test must be shown incapable of passing on a
  wrong implementation, not merely assumed to be).

**Checkpoint**: Both frontends validated end-to-end against Spec 1's oracle; the
validation suite is proven, by construction, sensitive to the exact per-upload
coefficient scaling it exists to guard.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-layer verification once both frontends and the validation suite
exist. **No performance, caching, or batching tasks** — this layer performs no
circuit execution itself and has no throughput target (Constitution §5.3; research.md
R9).

- [x] T017 [P] Run the full suite (`pytest tests/ -v` and `mypy src/fourierlearn/`),
  Spec 1 and Spec 2 together, and confirm everything is green — **SC-001**–**SC-005**.
- [x] T018 [P] Audit `src/fourierlearn/encodings/trotter.py` (grep/manual review) to
  confirm every `PauliTerm`/`PauliEncodedCircuitIR` construction path it exercises
  goes through `pauli_pqc.build_ir()` — zero parallel or duplicated IR-construction
  logic anywhere in `trotter.py` — Constitution §9.4; **FR-009**.
- [x] T019 [P] Confirm, by reading both modules, that zero caching, batching, or
  parameterised-circuit-template reuse was introduced anywhere in
  `src/fourierlearn/encodings/`: no memoization of `build_ir`'s
  parameter-label-to-index mapping across separate calls, no cached or shared IR
  instances, no template reuse across different coupling-group structures — every
  call performs the same single pass of validation and construction regardless of
  input size — Constitution §5.3, §9.3 (research.md R9). *(Guardrail: explicit
  zero-optimisation confirmation.)*
- [x] T020 [P] Cross-check that all five Success Criteria (SC-001 through SC-005)
  each have a corresponding passing test, and record the mapping (e.g. a short note
  in this file or a follow-up commit message) — **SC-001**–**SC-005**.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup existing (nothing to run against
  otherwise) — BLOCKS all user stories only in the sense that it must stay green.
- **US1 / `pauli_pqc.py` (Phase 3)**: Depends on Foundational. No dependency on any
  other user story — the more primitive, more general frontend, per spec.md's own
  stated priority ordering.
- **US2 / `trotter.py` (Phase 4)**: Depends on US1 (`trotter_frontend` imports and
  calls `pauli_pqc.build_ir` — FR-009; T013 cannot be implemented, let alone pass
  T007/T010/T011, before T005/T006 exist).
- **US3 / oracle validation (Phase 5)**: Depends on US1 and US2 both existing (there
  is nothing to lower and validate before both frontends exist).
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests are written first and MUST fail before their paired implementation task.
- Within US1: the core acceptance test (T003) and the dedicated non-commuting
  rejection test (T004) both precede any implementation; T005 (core `build_ir`) must
  exist before T006 (commutativity helper) can be wired into it, since T006 modifies
  the same function T005 defines.
- Within US2: all five test tasks (T007–T011) precede both implementation tasks;
  T012 (validation) is implemented before T013 (coefficient computation and
  composition), since T013's composition logic assumes T012's guards already reject
  malformed input before any coefficient is computed.
- Within US3: T014 and T015 (the two per-frontend validation tests) both exist before
  T016, which needs both to already be in place in order to break each one in turn.

### Parallel Opportunities

This spec has less intra-phase file-level parallelism than Spec 1: US1's two test
tasks (T003, T004) share `tests/unit/test_pauli_pqc.py`; US2's five test tasks
(T007–T011) share `tests/unit/test_trotter.py`; US3's tasks share
`tests/oracle/test_encodings_validation.py`. Marking same-file tasks `[P]` would
invite merge conflicts, so none of T003/T004, T007–T011, or T014–T016 carry a `[P]`
marker, unlike Spec 1's more file-separated task set.

- T017, T018, T019, T020 (Polish) — four independent, read-only verification tasks
  over different concerns, safely parallel.
- Test-*writing* (not implementation) for a later story does not strictly require an
  earlier story's implementation to exist yet — a second contributor could begin
  drafting T007–T011 while T005/T006 are still in progress, since tests are written
  to fail first regardless.

---

## Parallel Example: Polish (Phase 6)

```bash
# Launch all four Polish verification tasks together:
Task: "Run the full test suite and mypy, confirm green (SC-001-SC-005)"
Task: "Audit trotter.py for zero duplicated IR-construction logic (FR-009)"
Task: "Confirm zero caching/batching/template-reuse in encodings/ (research.md R9)"
Task: "Cross-check SC-001-SC-005 each have a passing test"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1–2: Setup + Foundational — Spec 1 confirmed still green.
2. Phase 3 (US1): `pauli_pqc.py` complete and independently tested — **first
   genuinely useful increment**: any caller with an explicit Pauli-string ansatz in
   mind can already build a valid IR from it, with no Hamiltonian/Trotter concept
   involved at all.
3. **STOP and VALIDATE**: Confirm US1's own tests (T003, T004) pass independently of
   `trotter.py`, which does not need to exist yet.

### Incremental Delivery

1. Complete Setup + Foundational → environment confirmed intact.
2. Add US1 (`pauli_pqc.py`) → test independently (MVP!).
3. Add US2 (`trotter.py`) → test independently — depends on US1's `build_ir`
   existing, per FR-009's mandated reuse, so this increment is only reachable after
   US1's checkpoint.
4. Add US3 (oracle validation) → test independently — this is the spec's own proof
   both frontends are not just structurally valid but physically correct
   (Constitution §4.1, §4.3).
5. Phase 6: Polish — whole-layer confirmation, no new logic.

### Test-First Discipline

Every implementation task above is paired with a test task that precedes it and is
expected to fail first. This is explicit, not incidental, for the three
architect-flagged rejection/ordering checks: T004 before T006 (research.md R6, tie
groups), T009 before T012 (research.md R7, `tau = 0`), and T010 before T013
(research.md R6 reached via Trotter's delegation to `build_ir`) — plus T011 before
T013 for the caller-declared group-order assertion (research.md R5). None of these
four are folded into a larger test task; each stands alone so a regression in
exactly one of them points at exactly one cause.

---

## Notes

- `[Story]` label maps every user-story-phase task to US1/US2/US3 for traceability;
  Setup, Foundational, and Polish tasks carry no story label by convention.
- Every task cites the FR(s) or SC(s) it satisfies, and the research.md decision
  (R1–R9) it implements or verifies where one exists — verify this before marking any
  task complete during `/speckit-implement`.
- No task in this list touches performance, caching, batching, or parameterised-
  template reuse — by design (Constitution §5.3; research.md R9 explicitly rejected
  caching `build_ir`'s label→index mapping across calls, since no profiled bottleneck
  justifies it).
- Two numeric fixtures (T014, T015) are described here with research.md R8's
  verified *approximate* decimal values for readability only — the implementing task
  must recompute the exact expected value analytically/numerically to full precision
  before asserting on it, not copy the rounded figure shown in research.md or here.
