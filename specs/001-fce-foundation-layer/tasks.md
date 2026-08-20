---

description: "Task list for FCE Foundation Layer implementation"
---

# Tasks: FCE Foundation Layer

**Input**: Design documents from `/specs/001-fce-foundation-layer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included — the feature spec itself requires ground-truth/consistency tests
per component (§4.1, §4.5, SC-005) and two specific non-trivial checks (FR-020,
FR-021) that this list schedules test-first, per explicit instruction.

**Organization**: Tasks are grouped by user story (US1–US4, from spec.md), but the
*phase order below is dependency-order, not priority-order* — see the note under
"Phase Ordering Deviation" below before assuming P1 → P2 → P3 → P4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every task names the FR(s) (or SC(s), which each trace to an FR) it satisfies —
  no task in this list is FR-untraceable.

## Path Conventions

Single project, per plan.md: `src/fourierlearn/`, `tests/` at repository root.

## Phase Ordering Deviation (read before executing)

spec.md's user stories are numbered by priority: US1 (P1, contracts+IR), US2 (P2,
frequency convention), US3 (P3, reference oracle), US4 (P4, CI guard). **This task
list schedules US2 before US1**, because `ir.py` (US1) imports `frequency.py`'s
`coordinate_order` and `register_width` (US2) — Constitution §9.1 ("no layer reaches
around another") makes this an actual import dependency, not a preference. The
canonical dependency chain enforced below is **`frequency.py` → `ir.py`/`contracts.py`
→ `reference.py` → CI guard**, i.e. US2 → US1 → US3 → US4. Each user story remains
independently *testable* exactly as spec.md describes (its own tests pass in
isolation); only the *build order* is dependency-first rather than priority-first.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — no story-specific logic yet.

- [ ] T001 Create `pyproject.toml` at repo root: `src/`-layout, `hatchling` build
  backend, pinned `python=">=3.12,<3.13"`, `qiskit==2.3.1`, `qiskit-aer==0.17.2`,
  `numpy==1.26.4` (verified compatible — research.md R2), `pytest`/`mypy`/`packaging`
  as dev extras (`packaging` is needed explicitly by T005's pin-parsing, not just
  relied on as an undeclared transitive dependency of `qiskit`) — **FR-019**.
- [ ] T002 [P] Create the `src/fourierlearn/` package skeleton: `__init__.py`, and
  empty placeholder modules `contracts.py`, `ir.py`, `frequency.py`, `reference.py`
  (module docstring only, no logic yet) — scaffolds **FR-001** (contracts.py),
  **FR-004** (ir.py), **FR-008** (frequency.py), **FR-011** (reference.py).
- [ ] T003 [P] Create the `tests/` skeleton: `tests/conftest.py`, and empty
  `tests/unit/`, `tests/oracle/`, `tests/ci/` directories — scaffolds the isolated,
  per-component ground-truth tests **SC-005** requires.
- [ ] T004 [P] Configure `mypy` strict mode (`disallow_untyped_defs`,
  `disallow_any_generics`) targeting `src/fourierlearn/` in `pyproject.toml` —
  **FR-001**, **SC-001** (typed-Protocol conformance must be mechanically checked,
  not just documented).

**Checkpoint**: Package and test skeletons exist; nothing importable yet.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The one prerequisite check that is not owned by any single user story,
but that every story's test results implicitly rely on being true.

**⚠️ CRITICAL**: No user story's tests can be trusted until this passes.

- [ ] T005 Write `tests/unit/test_dependency_versions.py`: read the declared
  `qiskit`/`qiskit-aer` pins **from `pyproject.toml` at test time** (e.g. via
  `tomllib` + `packaging.requirements.Requirement` — do not duplicate the version
  strings as separate literals in the test file, which would let the test and the pin
  drift apart silently) and assert the installed `qiskit.__version__`/
  `qiskit_aer.__version__` match that declared pin exactly; separately assert the
  installed `numpy.__version__` satisfies `numpy<3,>=1.21` (Qiskit's own constraint)
  and `numpy>=1.16.3` (Aer's own constraint) — **FR-019** (research.md R2, R11 — this
  is the scoped-down dependency-version check; full run-manifest scaffolding is out of
  scope, deferred to Spec 6 per spec.md's Assumptions). Reading the pin from
  `pyproject.toml` rather than hardcoding it keeps FR-019's "matches that pin" check
  meaningful — a deliberate upgrade is a one-line `pyproject.toml` edit that the test
  automatically checks against, rather than a hardcoded assertion someone comments out
  the first time it blocks an intentional upgrade.

**Checkpoint**: Environment verified consistent with the pin. User story work may
begin, in dependency order (US2 → US1 → US3 → US4 below).

---

## Phase 3: User Story 2 - Consult one authoritative source for frequency conventions (Priority: P2, built first)

**Goal**: `frequency.py` is the sole source of truth for frequency sign,
pre-/post-parity indexing, two's-complement decoding, coordinate ordering, and
register width — importable standalone, with no dependency on the IR, contracts, or
oracle.

**Independent Test** (from spec.md): Feed the module hand-derived integer
frequencies and index positions; sign, parity annotation, decoding, and ordering all
match hand-computed values.

### Tests for User Story 2 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [ ] T006 [US2] Write unit tests in `tests/unit/test_frequency.py` for
  `pre_parity_range(r_j, upload_count)`, `to_post_parity`/`to_pre_parity` (including
  the required `ValueError` on odd input to `to_post_parity`), `decode_twos_complement`,
  `coordinate_order`, and `dft_frequencies(num_points)` (the FFT-bin-index-to-signed-`l`
  mapping — asserts, e.g., for `num_points=5`, bin order `[0,1,2,-2,-1]`) against
  hand-computed values — **FR-008**, **FR-009** (`dft_frequencies` belongs here, not
  inlined in `reference.py`, per FR-009's "every function that produces or consumes a
  frequency imports from the convention module" — an ad hoc FFT-bin mapping in
  `reference.py` would be exactly the kind of independent sign/indexing definition
  FR-009 prohibits, and another silent-conjugation opportunity alongside FR-021's).
- [ ] T008 [US2] Add unit tests in `tests/unit/test_frequency.py` for
  `register_width(uploads, r_j)` against the hand-computed table:
  **`(uploads=1, r_j=1)` → width `3`** (the smallest valid boundary case:
  `4*1*1+1 = 5` states, `ceil(log2(5)) = 3` — include this exact case explicitly, to
  prove the old `max(2, ...)` floor is safely omitted now that `uploads=0`/`r_j=0`
  raise instead of silently under-sizing; there is no valid input below this boundary
  for the floor to have ever protected), `(uploads=2, r_j=1)`, `(uploads=1, r_j=2)`,
  and one `(uploads=2, r_j=2)` combined case — citing the Z2LGT report §5.3 formula
  directly (research.md R12). Also test the degenerate-input cases: `register_width(0,
  r_j)` and `register_width(uploads, 0)` each raise `ValueError` rather than
  returning a plausible-looking width (§10.1) — **FR-010**. (Note: a
  `ceil(log2(4*r_j*uploads+2))`
  variant was considered and rejected — `4*r_j*uploads+1` is always odd for valid
  `uploads,r_j ≥ 1`, so it is never itself a power of two, and `ceil(log2(N))` ==
  `ceil(log2(N+1))` identically for every odd `N>1`; verified exhaustively in-session
  for `r_j*uploads` from 1 to 1999. No test case can discriminate between the two
  forms because none differ — do not add one.)

### Implementation for User Story 2

- [ ] T007 [US2] Implement `pre_parity_range`, `to_post_parity`, `to_pre_parity`,
  `decode_twos_complement`, `coordinate_order`, and `dft_frequencies(num_points)` in
  `src/fourierlearn/frequency.py` per the pinned convention: canonical pre-parity
  `l ∈ {-2r_jL,...,2r_jL}`, sign `l = Λ - Λ'` (§6.1). `dft_frequencies` MUST assume
  (and assert) `num_points` is odd — always true for `4r_jL+1` — and return bin `k`'s
  signed frequency as `k` for `k ≤ num_points//2`, `k - num_points` otherwise, matching
  `numpy.fft.fftfreq(num_points) * num_points` rounded to int — **FR-008**, **FR-009**
  (depends on T006; makes it pass).
- [ ] T009 [US2] Implement `register_width(uploads, r_j) = ceil(log2(4 * r_j *
  uploads + 1))` in `src/fourierlearn/frequency.py`, citing Z2LGT report §5.3 in a
  docstring, and raising `ValueError` for `uploads < 1` or `r_j < 1` (§10.1 — a
  degenerate input must raise, not silently return a width computed from an
  out-of-range value) — **FR-010** (depends on T008; makes it pass).

**Checkpoint**: `frequency.py` complete and independently testable — zero dependency
on `ir.py`, `contracts.py`, or `reference.py`.

---

## Phase 4: User Story 1 - Build any layer against a stable typed contract (Priority: P1, built second)

**Goal**: `contracts.py` defines the `Encoding` and `Oracle` Protocols (plus a
documented extension point) scoped to exactly the two boundaries this spec crosses;
`ir.py` defines the Pauli-encoded circuit IR with per-parameter upload count,
coefficients, and tied multiplicity `r_j`, plus the verified sign-correct
`PauliTerm.to_gate()` mapping.

**Independent Test** (from spec.md): A stub `Encoding` implementation and a tied,
`r_j = 2` IR instance both type-check and round-trip correctly, with no dependency on
`reference.py`.

### Tests for User Story 1 ⚠️

> Write these first; they MUST fail before the corresponding implementation task.

- [ ] T010 [P] [US1] Write unit tests in `tests/unit/test_ir.py`: a tied, `r_j = 2`
  parameter's upload count/multiplicity/coefficients round-trip correctly; a
  multiplicity/tied-term-count mismatch is rejected at construction; an
  out-of-range qubit index is rejected; a non-Hermitian observable is rejected; **and**
  `PauliEncodedCircuitIR.parameter_symbols()` returns exactly one `qiskit.circuit.Parameter`
  object per distinct `parameter_index`, and calling it twice (or looking up the same
  index from two different tied `PauliTerm`s) returns the *identical* object — not
  merely an equal one. Assert this with an explicit object-identity check,
  `ir.parameter_symbols()[0] is ir.parameter_symbols()[0]` (i.e. `is`, not `==`),
  across two *separate* calls to `parameter_symbols()` — an equality-only assertion
  would pass even if memoization were broken and a fresh, merely-equal `Parameter`
  were minted per call, since Qiskit's `assign_parameters` binds by object identity,
  not by name or equality: a distinct-but-equal `Parameter` object silently fails to
  bind, or binds the wrong symbol, rather than raising. So every term sharing a
  parameter index is structurally guaranteed to bind to the same symbol (FR-005's
  "MUST NOT permit... independent
  parameters" enforced by the IR itself, not left to whichever caller builds a circuit
  from it). **Also test FR-007 directly**: build two `PauliEncodedCircuitIR`
  instances identical in every respect (same `pauli`, `qubits`, `parameter_index`,
  `tie_group` for every gate) except their `PauliTerm.coefficient` values differ, and
  assert `upload_count(j)`, `multiplicity(j)`, and any grid-shape value derived from
  them (e.g. `4*multiplicity(j)*upload_count(j)+1` per parameter) are identical
  between the two IRs — proving `coefficient` never leaks into anything
  frequency/register-sized; only `pauli`/`qubits`/`parameter_index`/`tie_group`
  structure does — **FR-004**, **FR-005**, **FR-006**, **FR-007**.
- [ ] T011 [P] [US1] Write the gate-convention equivalence test in
  `tests/unit/test_ir_gate_convention.py`: build `PauliTerm("Z", (0,), 0, 1.0,
  0).to_gate(Parameter("a"))`, bind `a` to a concrete value, and assert
  `Operator`-equivalence against a hand-built `e^{iπ·1.0·a·Z}` matrix — **FR-021**,
  **SC-009** (this MUST be written and failing *before* `to_gate()` is implemented in
  T012 — a sign error here is invisible on any real-coefficient test, so this test is
  the only thing that catches it).
- [ ] T013 [P] [US1] Write Protocol-conformance unit tests in
  `tests/unit/test_contracts.py`: a minimal stub `Encoding` implementation and a
  minimal stub `Oracle` implementation both satisfy `@runtime_checkable` conformance;
  adding a new Protocol at the documented extension point does not require modifying
  `Encoding` or `Oracle` — **FR-001**, **FR-002**, **FR-003**.

### Implementation for User Story 1

- [ ] T012 [US1] Implement `Parameter`, `PauliTerm` (including `to_gate()` using the
  verified mapping `time = -math.pi * self.coefficient * parameter`), `FixedGate`,
  and `PauliEncodedCircuitIR` (derived accessors `parameters()`, `upload_count()`,
  `multiplicity()`, `coefficients()`, `num_parameters`, plus construction-time
  validation) in `src/fourierlearn/ir.py`, importing `coordinate_order` from
  `frequency.py`. **Also implement `PauliEncodedCircuitIR.parameter_symbols() ->
  dict[int, qiskit.circuit.Parameter]`**: builds and memoizes exactly one
  `Parameter` per distinct `parameter_index` on first access, so every caller (this
  spec's oracle in T020, and any later `circuits`-layer spec) obtains the same shared
  symbol for every term tied to one index, rather than each independently
  reimplementing — correctly or not — the "one Parameter per index" rule — **FR-004**,
  **FR-005**, **FR-006**, **FR-007**, **FR-021** (depends on T007, T010, T011; makes
  T010 and T011 pass).
- [ ] T014 [US1] Implement `contracts.py`: `Encoding` and `Oracle`
  `@runtime_checkable` Protocols, plus a module-level docstring documenting the
  extension point for later specs' Protocols, importing `PauliEncodedCircuitIR` from
  `ir.py` — **FR-001**, **FR-002**, **FR-003** (depends on T012, T013; makes T013
  pass).

**Checkpoint**: `contracts.py` and `ir.py` complete and independently testable —
`reference.py` does not exist yet.

---

## Phase 5: User Story 3 - Validate any layer against an exact ground truth (Priority: P3, built third)

**Goal**: `reference.py`'s quarantined oracle computes exact Fourier coefficients via
a Nyquist grid over the *full* period-2 domain and a d-dimensional FFT, broken into
separately implementable pieces (cost-budget guard, grid construction, circuit
evaluation, FFT + coefficient indexing), validated against single-upload and
symmetry-broken two-upload analytic cases plus the odd-`l` vanishing check.

**Independent Test** (from spec.md): Run the oracle on a small, fully specified IR
instance with known analytic coefficients; diff against hand-derived values — no
dependency on shot-based extraction.

### Tests for User Story 3 ⚠️

> Write these first; they MUST fail before the corresponding implementation tasks.

- [ ] T015 [US3] Write the single-upload oracle test in
  `tests/oracle/test_reference_oracle.py`: a one-qubit, single-`Z`-upload IR with
  `SparsePauliOp("Z")` observable reproduces its analytically known (real) Fourier
  coefficients to floating-point precision (relative error ≤ 1e-9), **and** asserts
  every *odd* pre-parity coefficient is zero to floating-point precision — **FR-016**,
  **FR-020**, **SC-002**, **SC-008**.
- [ ] T016 [US3] Write the two-upload, symmetry-breaking oracle test in
  `tests/oracle/test_reference_oracle.py`: a one-qubit IR with two `Z`-uploads of the
  same parameter and an `S` `FixedGate` between them reproduces its analytically
  known, genuinely complex Fourier coefficients (nonzero real and imaginary parts on
  a non-DC coefficient) to floating-point precision, **and** asserts every odd
  pre-parity coefficient is zero — **FR-017**, **FR-018**, **FR-020**, **SC-002**,
  **SC-008**.
- [ ] T017 [P] [US3] Write the cost-budget-guard test in
  `tests/oracle/test_cost_budget.py`: the oracle predicts and logs the grid's point
  count/cost before evaluating, and raises (rather than silently proceeding) when a
  circuit's parameter count would exceed a configured budget without explicit
  confirmation — **FR-013**.

### Implementation for User Story 3

> `reference.py` is broken into four separately implementable pieces plus one
> composition task — none of these are to be merged into a single task.

- [ ] T018 [US3] Implement the **cost-budget guard** in `src/fourierlearn/reference.py`:
  a function that computes the total grid point count (`prod(4*r_j*L_j+1)` over all
  parameters), logs the predicted cost, and raises unless the caller has confirmed
  proceeding past a configured budget — **FR-013** (depends on T017; makes it pass).
- [ ] T019 [US3] Implement **Nyquist grid construction** in
  `src/fourierlearn/reference.py`: for each parameter, build the `4*r_j*L_j+1`-point
  grid over the full period-2 domain (not the period-1 half-domain — FR-020), calling
  the cost-budget guard (T018) before constructing the full outer-product grid —
  **FR-011**, **FR-020** (depends on T018, T012).
- [ ] T020 [US3] Implement **circuit evaluation** in `src/fourierlearn/reference.py`:
  obtain the shared parameter symbols via `ir.parameter_symbols()` (T012) — **do not
  create a fresh `Parameter` per `PauliTerm`** — and build one `QuantumCircuit` from
  the IR's gate sequence, appending `term.to_gate(symbols[term.parameter_index])` for
  each `PauliTerm` (every term sharing a `parameter_index`, across all its
  `tie_group`s, MUST reference the identical `Parameter` object) and `fixed.gate` for
  each `FixedGate`; per grid point, bind via `assign_parameters` and compute
  `Statevector.from_instruction(bound).expectation_value(observable).real` — **FR-011**,
  **FR-012** (depends on T019, T012, T014; uses only `Statevector` — no `Operator`/
  `expm`, per research.md R6). Binding a fresh `Parameter` per term instead of reusing
  `parameter_symbols()` would silently untie every parameter, producing a `d' = Σ_j
  r_j·L_j`-dimensional oracle instead of the correct `d`-dimensional one — a defect
  FR-005 already prohibits, that T016's two-upload test (which ties two `Z`-uploads
  to one index) would likely fail on, but only opaquely, as "wrong coefficients,"
  rather than pointing at the actual cause.
- [ ] T021 [US3] Implement **FFT + coefficient indexing** in
  `src/fourierlearn/reference.py`: apply `numpy.fft.fftn` over the evaluated grid,
  normalize by total point count, and index the result by integer pre-parity
  frequency tuple `l` using `frequency.dft_frequencies()` (T007) for the per-axis
  bin-to-`l` mapping and `frequency.coordinate_order()` for axis order — **do not**
  inline an ad hoc `fftfreq`/`fftshift` computation here, since that would be exactly
  the independent frequency-indexing definition FR-009 prohibits, and another place a
  sign could silently flip — **FR-011**, **FR-009** (depends on T020, T007).
- [ ] T022 [US3] Implement the oracle's `coefficients()` entry point in
  `src/fourierlearn/reference.py`, composing the cost-budget guard (T018) → grid
  construction (T019) → circuit evaluation (T020) → FFT/indexing (T021) into the one
  method the `Oracle` Protocol (T014) requires — **FR-011**, **FR-012**, **FR-013**
  (depends on T018–T021, T014; makes T015 and T016 pass).

**Checkpoint**: `reference.py` complete and independently testable against analytic
ground truth; `Operator`/`expm` are not imported anywhere in this module (research.md
R6) — nothing yet enforces that mechanically (Phase 6 does).

---

## Phase 6: User Story 4 - Automatically block exact-computation leakage into production (Priority: P4, built fourth)

**Goal**: A CI check fails the build if any production module imports
`Statevector`, `Operator`, `expm`, or `reference`, excluding `reference.py` itself and
test helpers — and this is *proven* to actually fire, not just implemented.

**Independent Test** (from spec.md): Add a throwaway production module importing one
of the four forbidden symbols; verify the check fails the build; remove it; verify
the check passes.

### Tests for User Story 4 ⚠️

> Write first; MUST fail before T024 exists.

- [ ] T023 [US4] Write `tests/ci/test_no_forbidden_imports.py`'s core assertions
  against the current, clean `src/fourierlearn/` tree: no violations are reported,
  and `reference.py`'s own internal use of the forbidden symbols is not flagged —
  **FR-014**, **FR-015**.

### Implementation for User Story 4

- [ ] T024 [US4] Implement the AST-based import-scanning function
  `tests/ci/test_no_forbidden_imports.py` exercises: parse each `src/fourierlearn/*.py`
  file with the stdlib `ast` module, collect `Import`/`ImportFrom` names, and flag any
  of `Statevector`, `Operator`, `expm`, or `fourierlearn.reference` found outside
  `reference.py` — **FR-014**, **FR-015** (depends on T023; makes it pass).
- [ ] T025 [US4] **Guard-validation task (explicit architectural requirement)**: add a
  `tmp_path`-based regression test to `tests/ci/test_no_forbidden_imports.py` that
  writes a throwaway module importing a forbidden symbol outside the exempted paths,
  runs the scanner (T024) against it, and asserts the violation is reported; then
  asserts the scan is clean once that throwaway module is removed. **This `tmp_path`
  test is the durable check** — it re-runs on every future CI invocation, so the guard
  cannot silently rot without a test failing. Separately, **as a one-time manual
  acceptance step** (which by nature cannot itself run in CI and will not recur):
  create a real throwaway file (`src/fourierlearn/_throwaway_ci_check.py`, `from
  qiskit.quantum_info import Statevector`), run the full `pytest`/CI check locally,
  confirm it fails and names the offending file, delete the file, and re-run to
  confirm it passes again. **Record that this manual step was performed** — e.g. a
  dated note in this task's commit message or PR description — precisely because
  nothing else will re-prove it happened; the `tmp_path` test above is what carries
  the ongoing guarantee forward, not this one-time step — **FR-014** (depends on
  T024).
- [ ] T026 [US4] Create `.github/workflows/ci.yml` running `pytest` (including the
  import-guard test from T023–T025) and `mypy` on every push and pull request —
  **FR-014** (deliverable (e); depends on T025).

**Checkpoint**: All four foundation components exist, are independently validated,
and the CI guard mechanically enforces the quarantine going forward.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Whole-layer verification once all four components exist. **No
performance, caching, or batching tasks** — this foundation layer has no throughput
target (spec.md Assumptions; Constitution §5.3 forbids optimisation without a
recorded profile and bottleneck, neither of which exists or is warranted here).

- [ ] T027 [P] Run the full validation suite (`pytest tests/ -v` and `mypy
  src/fourierlearn/`) and confirm everything is green, per quickstart.md end-to-end —
  **SC-005** (Constitution §4.5: each phase ends with the full suite green).
- [ ] T028 [P] Audit `src/fourierlearn/` (grep/manual review) to confirm zero modules
  outside `frequency.py` define frequency sign, parity indexing, two's-complement
  decoding, or coordinate ordering independently — **SC-003**.
- [ ] T029 [P] Cross-check that all nine Success Criteria (SC-001 through SC-009)
  each have a corresponding passing test, and record the mapping (e.g. in
  quickstart.md or a short note). Note explicitly that SC-006's *behavioral aliasing-
  regression* clause is out of scope here by design — deferred to Spec 3 per the TODO
  in spec.md's Assumptions — so SC-006 is satisfied for this layer by T008/T009's
  formula-level tests alone; do not treat its absence as an incomplete cross-check —
  **SC-001**–**SC-009**.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (needs `pyproject.toml`'s pin to check
  against) — BLOCKS all user stories.
- **US2 / frequency.py (Phase 3)**: Depends on Foundational. No dependency on any
  other user story — the first substantive phase, per the Strict Dependency Order
  guardrail.
- **US1 / contracts.py + ir.py (Phase 4)**: Depends on US2 (`ir.py` imports
  `frequency.coordinate_order`; `frequency.register_width`).
- **US3 / reference.py (Phase 5)**: Depends on US1 (`ir.py`'s IR types, `contracts.py`'s
  `Oracle` Protocol) and US2 (`frequency.coordinate_order` for FFT axis ordering).
- **US4 / CI guard (Phase 6)**: Depends on US1, US2, US3 all existing (there must be
  a real `src/fourierlearn/` tree, including `reference.py`, to scan).
- **Polish (Phase 7)**: Depends on all four user stories being complete.

### Within Each User Story

- Tests are written first and MUST fail before their paired implementation task.
- `frequency.py` (US2) before `ir.py`/`contracts.py` (US1) before `reference.py` (US3)
  before the CI guard (US4) — strict, not merely suggested.
- Within US3: cost-budget guard → grid construction → circuit evaluation → FFT/
  indexing → the composed `coefficients()` entry point, in that order.

### Parallel Opportunities

- T002, T003, T004 (Setup) — different files, no shared state.
- T010, T011, T013 (US1 tests) — three different test files, none depending on the
  others' content.
- T017 (US3 cost-budget test) — a different file from T015/T016, can be written in
  parallel with them.
- T027, T028, T029 (Polish) — independent, read-only verification tasks.

---

## Parallel Example: User Story 1 (Phase 4)

```bash
# Launch all three US1 test-writing tasks together:
Task: "Write unit tests in tests/unit/test_ir.py for tied-parameter IR construction and validation (FR-004, FR-005, FR-006)"
Task: "Write the Operator-equivalence gate-convention test in tests/unit/test_ir_gate_convention.py (FR-021, SC-009)"
Task: "Write Protocol-conformance tests in tests/unit/test_contracts.py (FR-001, FR-002, FR-003)"
```

---

## Implementation Strategy

### Dependency-First Build (not pure MVP-by-priority)

Because `ir.py` (US1, P1) actually imports `frequency.py` (US2, P2), the smallest
buildable increment is **US2 then US1** together — there is no working `ir.py`
without `frequency.py` existing first, regardless of priority numbering. Suggested
increments:

1. Phase 1–2: Setup + Foundational — environment verified.
2. Phase 3 (US2): `frequency.py` complete and independently tested.
3. Phase 4 (US1): `contracts.py` + `ir.py` complete and independently tested —
   **first genuinely useful increment**: a downstream `encodings` spec could start
   against this alone.
4. Phase 5 (US3): `reference.py` complete and independently tested — **this is the
   suggested MVP scope**: the full foundation layer's scientific claim (exact,
   ground-truth Fourier coefficients, including the non-trivial complex and
   odd-`l`-vanishing checks) is now validated end-to-end.
5. Phase 6 (US4): CI guard — closes the loop by mechanically enforcing what Phases
   3–5 established by convention.
6. Phase 7: Polish — whole-layer confirmation, no new logic.

### Test-First Discipline

Every implementation task above is paired with a test task that precedes it and is
expected to fail first — this is explicit, not incidental, for FR-020 (T015/T016
before T018–T022) and FR-021 (T011 before T012), per architectural instruction, and
applied consistently to every other component for the same reason (Constitution §4.1:
"a component with no passing oracle test is not done, however well it runs").

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work.
- [Story] label maps every user-story-phase task to US1/US2/US3/US4 for traceability;
  Setup, Foundational, and Polish tasks carry no story label by convention.
- Every task cites the FR(s) or SC(s) it satisfies — verify this before marking any
  task complete during `/speckit-implement`.
- No task in this list touches performance, caching, batching, or throughput — by
  design (Constitution §5.3: no optimisation without a recorded profile and a
  bottleneck it targets, and none exists at this layer).
