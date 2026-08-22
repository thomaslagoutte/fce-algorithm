# Feature Specification: Execution Configuration and Controlled-Circuit Defect Repair

**Feature Branch**: `011-execution-config-repair`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Execution Configuration and Controlled-Circuit Defect Repair. Deliverables: (a) Fix a genuine Constitution Section 1 (§1.7) violation in extract.py's _hadamard_test_circuit and _v_l_dagger_circuit: both currently wrap an assembled multi-gate circuit in .control(), forcing dense-unitary synthesis (Quantum Shannon Decomposition) on blocks far larger than "a few qubits" — this is the exact anti-pattern the section names, and it is very likely the root cause of a measured 1108-second single-time-point baseline on a trivial n=3, r=2 instance (14 qubits, 850 circuits) on ordinary consumer hardware. The fix replaces whole-block .control() with inline, gate-by-gate controlled assembly, following this project's own established pattern from Spec 3's circuit-construction work. (b) Make transpile()'s optimization_level and basis-gate set explicit, deliberate parameters instead of silent defaults. (c) Add an additive simulator: AerSimulator | None = None parameter to estimate_coefficient, extract_coefficients, and estimate_kernel_overlap so a caller can supply a device/parallelism-configured simulator instead of each call constructing a fresh bare AerSimulator() — None must preserve exactly today's behavior."

## Clarifications

### Session 2026-08-21

- **Two-Tiered Equivalence Proof**: a full `Operator()` reconstruction at
  the documented 14-qubit baseline scale is intractable — it requires a
  `2^14 x 2^14` dense matrix and will crash or hang during Quantum Shannon
  Decomposition synthesis, the exact intractability wall Spec 3's own
  research.md already discovered and documented. The single-tier
  `Operator.equiv`-on-existing-fixtures proof obligation (originally
  FR-003) is therefore replaced by a two-tier obligation (FR-003, FR-012,
  FR-013 below): **Tier 1 (Construction Correctness)** — full
  `Operator.equiv` on genuinely small (1-2 qubit) fixtures, proving the
  inline-assembly LOGIC has no baseline construction bug — and **Tier 2
  (Scale Correctness)** — a `Statevector`-based comparison of the old
  `.control()`-based circuit against the new inline-assembled one AT THE
  ACTUAL 14-qubit baseline scale, on at least two input states (the
  all-zero state and a Haar-random state), citing Spec 3's research.md as
  established precedent for this exact two-tier pattern. Evaluating the
  OLD `.control()`-based circuit at 14 qubits for Tier 2 is expected to be
  extremely slow — this is a one-time verification cost the research
  phase MUST pay, not a cost to avoid by substituting a smaller,
  unrepresentative fixture (see Assumptions).

## User Scenarios & Testing *(mandatory)*

<!--
  This is an internal defect-repair and configuration-surface feature for
  this project's own Extract Layer (Spec 4) and its Spec 10 kernel-overlap
  extension — as with Specs 1-10, "the user" is a developer of/experimenter
  with this pipeline, and the feature IS the implementation being repaired,
  so the acceptance scenarios below are stated in terms of circuit
  construction and measured wall-clock behavior, not a generic end-user
  workflow (checklists/requirements.md Notes documents this same, now-
  established departure from the template's generic "no implementation
  details" framing).
-->

### User Story 1 - Repair the whole-block `.control()` construction defect (Priority: P1)

A developer running `extract_coefficients` on a realistic (double-digit
qubit) instance currently waits over eighteen minutes for a single
time-point's extraction, on ordinary consumer hardware, for what the
underlying algorithm's own circuit depth and shot count do not by
themselves justify. The cause is that `_hadamard_test_circuit` and
`_v_l_dagger_circuit` each wrap an already-ASSEMBLED, multi-gate circuit
block in a single `.control(1)` call — forcing Qiskit to synthesize a
dense controlled-unitary (Quantum Shannon Decomposition) over the block's
full qubit width, an anti-pattern this project's own Constitution already
names and prohibits (§1.7) but that Spec 4's shipped code violates. The
developer needs this replaced with the constitutionally-required
construction: each gate of the block controlled individually and composed
in sequence (§5.7's `c-(U_K⋯U₁) = c-U_K⋯c-U₁`), so the controlled
circuit's cost scales with the block's own gate count, not with an
exponential-in-block-width synthesis step.

**Why this priority**: Every other deliverable in this feature (deliberate
transpile configuration, an injectable simulator) is secondary to this one
— reconfiguring how an exponentially-expensive circuit gets executed
cannot fix an exponentially-expensive circuit. This is also the only
deliverable that changes what circuit gets built, so it alone carries the
correctness-preservation obligation (Critical Mandate 1/5).

**Independent Test**: Can be fully tested by the Two-Tiered Equivalence
Proof (Clarifications, 2026-08-21): Tier 1 — comparing, via `Operator.equiv`,
the existing `.control()`-based circuit against the new inline-assembled
circuit on every genuinely small (1-2 qubit) fixture already used by Spec
4's own test suite; and Tier 2 — comparing, via `Statevector` (not a full
`Operator()` reconstruction, which is intractable at this scale), the same
two constructions' output on the all-zero state and a Haar-random state at
the ACTUAL documented 14-qubit baseline scale. A passing result on both
tiers, plus the documented baseline configuration's wall-clock time
dropping substantially and reproducibly (§5.4/§5.5), constitutes the test.

**Acceptance Scenarios**:

1. **Given** the current `_hadamard_test_circuit`, which wraps the entire
   compiled `A(U,O)` block in `circuit.to_gate().control(1)`, **When** it
   is replaced with an inline, gate-by-gate controlled assembly of that
   same block's own gate sequence, **Then** Tier 1's `Operator.equiv`
   confirms the two constructions compute the IDENTICAL operator on every
   genuinely small (1-2 qubit) fixture in Spec 4's test suite, checked
   BEFORE the replacement is trusted (Constitution §4.1/§5.2), not assumed
   from the algebraic identity alone.
2. **Given** the current `_v_l_dagger_circuit`'s own `.control()` wrap
   (over its own assembled sequence of cyclic-increment/decrement
   sub-circuits), **When** it is likewise replaced with an inline,
   gate-by-gate controlled assembly, **Then** the same Tier 1
   `Operator.equiv` proof obligation holds, independently of Scenario 1's
   proof (this is a second, separate construction site named explicitly
   in the defect report, not a single shared fix).
3. **Given** both repair sites (Scenarios 1-2) integrated into the FULL
   compiled Hadamard-test circuit at the documented 14-qubit baseline
   scale, **When** the old `.control()`-based circuit and the new
   inline-assembled circuit are each evaluated, via `Statevector`, on the
   all-zero state and on a Haar-random state, **Then** the resulting
   statevectors are confirmed equivalent (Tier 2, Scale Correctness) —
   this is required IN ADDITION TO Tier 1, since Tier 1's small fixtures
   alone cannot rule out a defect that only manifests when the two repair
   sites are integrated at the actual baseline scale.
4. **Given** the documented baseline configuration (`n=3, r=2, shots=20000,
   seed=7, t=1.09` → 14 qubits, 425 frequencies, 850 circuits, `1108.00s`
   on the unmodified code, measured on consumer (M1) hardware), **When**
   the repaired construction is benchmarked on the exact same
   configuration, **Then** the before-and-after timings are each
   reproduced across at least 2 trials (Constitution §5.4/§5.5's
   reproducibility discipline) and reported together as a genuine
   before/after comparison — not a single anecdotal run of either.
5. **Given** every existing Spec 4 test (Hadamard-test circuit equivalence,
   oracle-convergence, conjugate-symmetry) and every existing Spec 10 test
   that depends on this module, **When** the repaired construction
   replaces the old one, **Then** every one of those tests passes
   UNMODIFIED — any fixture on which the two constructions disagree is
   this feature's own defect to find and fix, never grounds to loosen or
   remove the disagreeing test (Critical Mandate 5).

---

### User Story 2 - Make `transpile()`'s configuration explicit (Priority: P2)

A developer reading `estimate_coefficient` currently sees a bare
`transpile(qc, simulator)` call and cannot tell, without consulting
Qiskit's own version-dependent defaults, what optimization level or
target gate set is actually being applied — and, per the defect report,
that silent default (`optimization_level=1`) re-optimizes whatever the
User-Story-1 defect's dense synthesis already produced, compounding cost
rather than merely adding to it. The developer needs the optimization
level and basis-gate set to be visible, deliberate values a reader can
find in this codebase, chosen AFTER User Story 1's repair (so they are
benchmarked against the corrected circuit, not the defective one).

**Why this priority**: Depends on User Story 1 being complete — benchmarking
`transpile()` configuration against a circuit that still contains the
whole-block `.control()` defect would produce numbers that do not transfer
once that defect is fixed, exactly the transferability trap Critical
Mandate 2 warns against for a different parameter (device/parallelism)
but which applies here too.

**Independent Test**: Can be fully tested by inspecting the call site and
confirming `optimization_level` and the basis-gate set are named,
documented values (constants or parameters) rather than an implicit
`transpile(qc, simulator)` default, and by confirming a benchmark exists
comparing at least two candidate configurations against the User-Story-1-
repaired circuit before one is selected as the default.

**Acceptance Scenarios**:

1. **Given** the repaired construction from User Story 1, **When**
   `estimate_coefficient` transpiles a circuit for execution, **Then** the
   `optimization_level` and basis-gate set used are explicit, named values
   in this codebase — never an un-named, implicit default silently
   inherited from Qiskit's own version.
2. **Given** at least two candidate `optimization_level` configurations,
   **When** each is benchmarked against the documented baseline
   configuration (post-User-Story-1-repair), **Then** the benchmark
   numbers themselves (not a plausible-sounding assumption about which
   level "should" be faster) determine which becomes this codebase's
   default.

---

### User Story 3 - Accept a caller-supplied, pre-configured simulator (Priority: P3)

A developer who has determined (or wants to determine) a
device/parallelism configuration that measurably helps THIS codebase's
own circuit shapes currently has no way to supply it: `estimate_coefficient`,
`extract_coefficients`, and `estimate_kernel_overlap` each construct a
fresh, bare `AerSimulator()` internally, with no seam for a caller to
inject a differently-configured one. The developer needs an additive
`simulator: AerSimulator | None = None` parameter on all three functions,
where `None` reproduces exactly today's behavior (a fresh, bare
`AerSimulator()`), so no existing caller or test observes any difference
unless it explicitly opts in.

**Why this priority**: This is the actual long-term configuration surface
the feature exists to deliver, but it is the least urgent of the three:
User Story 1's repair is what makes ANY device/parallelism configuration
worth tuning in the first place (tuning execution of an exponentially
mis-constructed circuit is not a meaningful benchmark), and User Story 2's
transpile parameters are a prerequisite for a fair device benchmark.

**Independent Test**: Can be fully tested by calling each of the three
functions once with `simulator=None` and once with an explicitly
constructed, functionally-identical `AerSimulator()` passed in, and
confirming the two calls produce statistically indistinguishable results
(same seed-determinism contract, same shot-count behavior) — then calling
with a DIFFERENTLY-configured simulator and confirming that configuration
is genuinely used (not silently discarded).

**Acceptance Scenarios**:

1. **Given** `estimate_coefficient`, `extract_coefficients`, or
   `estimate_kernel_overlap` called with `simulator=None` (or omitted),
   **When** the call executes, **Then** its behavior — including the
   existing seed-determinism contract (`seed`/`seed+1` for the real/
   imaginary sub-circuits) — is IDENTICAL to today's unmodified behavior,
   verified by every existing test for these three functions passing
   unmodified.
2. **Given** a caller-supplied, differently-configured `AerSimulator`
   instance, **When** any of the three functions is called with it,
   **Then** that exact instance is used for execution — never silently
   replaced by an internally-constructed one.
3. **Given** this feature's own recommended, benchmarked device/parallelism
   DEFAULT (if any is promoted beyond "a configurable knob" to "what a
   caller gets by not overriding a non-`simulator` setting"), **When**
   that recommendation is reported, **Then** it cites a benchmark
   performed on THIS codebase's own post-User-Story-1-repair circuit
   shapes — never a number carried over from a different codebase's
   prior measurements (Critical Mandate 2, Constitution §5.4/§5.5's
   rationale note on GPU-below-20-qubits and
   `max_parallel_experiments=112` not transferring across codebases).

---

### Edge Cases

- What happens when a target frequency component is exactly `0` (an
  identity `V_l^dagger`, i.e., a zero-gate block)? The inline controlled
  assembly must handle an empty gate sequence correctly — no controlled
  gate is needed, and the construction must not error or insert a
  meaningless no-op control.
- What happens when the block being controlled is already only one or two
  qubits (e.g. a minimal fixture)? The repair applies uniformly regardless
  of block size — this feature does not special-case "small enough that
  `.control()` was fine anyway," since the defect is in the CONSTRUCTION
  PATTERN, not merely in blocks that happen to be large in today's
  fixtures.
- What happens when a caller supplies a simulator instance that is
  mid-use, misconfigured, or otherwise unsuitable for the circuit being
  run? Out of scope — this feature adds a pass-through seam, not
  simulator-compatibility validation; Qiskit Aer's own error surface
  applies unchanged.
- What happens to the existing shot-budget/cost-prediction logic
  (`ShotBudgetExceeded`, `predicted_cost`) once the construction defect is
  fixed? It is unchanged by this feature — it predicts CIRCUIT COUNT x
  SHOTS, not construction cost, and remains correct regardless of how a
  circuit is internally assembled.
- What happens if the inline-assembled replacement and the old
  `.control()`-based construction disagree on some fixture NOT already in
  Spec 4's existing test suite? Out of scope for this feature's own proof
  obligation (Critical Mandate 1 names "existing small fixtures"
  specifically), but any such disagreement discovered during
  implementation is Constitution §8.4 (negative results documented, not
  discarded) territory, not silently ignored.
- What happens if Tier 1 (small-fixture `Operator.equiv`) passes but Tier 2
  (14-qubit-scale `Statevector` comparison) fails? This is precisely the
  failure mode the two-tier proof exists to catch — a defect that only
  manifests once both repair sites are integrated at the actual baseline
  scale. It is this feature's own defect to find and fix before either
  repair site is trusted, never grounds to skip Tier 2 or report Tier 1
  alone as sufficient.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (Deliverable a): `_hadamard_test_circuit` MUST replace its
  current `circuit.to_gate(label="A(U,O)").control(1)` whole-block wrap
  with an inline, gate-by-gate controlled assembly of that block's own
  gate sequence, per Constitution §5.7 (`c-(U_K⋯U₁) = c-U_K⋯c-U₁`).
- **FR-002** (Deliverable a): `_v_l_dagger_circuit`'s own use inside
  `_hadamard_test_circuit` (`v_gate = ....to_gate(label="Vl_dag").control(1)`)
  MUST receive the same treatment — an inline, gate-by-gate controlled
  assembly of `_v_l_dagger_circuit`'s own gate sequence, independently
  verified (this is a second, separate construction site, not a single
  shared fix).
- **FR-003** (Critical Mandate 1, Constitution §4.1/§5.2; Clarifications
  2026-08-21): Before either replacement construction (FR-001, FR-002) is
  trusted, a **Two-Tiered Equivalence Proof** MUST be completed —
  Tier 1 (FR-012, Construction Correctness) AND Tier 2 (FR-013, Scale
  Correctness), together, never either alone. A full `Operator.equiv`
  comparison at the documented 14-qubit baseline scale is intractable (a
  `2^14 x 2^14` dense-matrix reconstruction will crash or hang during
  Quantum Shannon Decomposition synthesis — the same wall Spec 3's own
  research.md already documented), which is why this obligation is
  two-tiered rather than a single `Operator.equiv` pass at full scale.
- **FR-004** (Deliverable b): `estimate_coefficient`'s `transpile()` calls
  MUST use an explicit, named `optimization_level` and basis-gate set
  (constants or parameters in this codebase) instead of Qiskit's own
  silent default.
- **FR-005** (Critical Mandate 3, Constitution §5.4/§5.5): The repair's
  own research/benchmarking phase MUST report a genuine before/after
  wall-clock comparison on the documented baseline configuration (`n=3,
  r=2, shots=20000, seed=7, t=1.09` → 14 qubits, 425 frequencies, 850
  circuits), with both the "before" and "after" timings each reproduced
  across at least 2 trials.
- **FR-006** (Deliverable c): `estimate_coefficient`, `extract_coefficients`,
  and `estimate_kernel_overlap` MUST each accept an additive
  `simulator: AerSimulator | None = None` parameter.
- **FR-007** (Backward compatibility, Critical Mandate 5): When
  `simulator=None` (or omitted), all three functions in FR-006 MUST behave
  IDENTICALLY to their current, unmodified behavior — including the
  existing seed-determinism contract — verified by every existing test
  for these three functions passing UNMODIFIED.
- **FR-008** (Critical Mandate 5): Every existing Spec 4 test (Hadamard-test
  circuit equivalence, oracle-convergence, conjugate-symmetry) and every
  Spec 10 test depending on this module MUST pass unmodified after this
  feature's changes. A fixture on which the repaired construction disagrees
  with the old one is this feature's own defect to resolve, never grounds
  to weaken the disagreeing test.
- **FR-009** (Correctness-of-cost, not correctness-of-result): This feature
  MUST NOT change the numeric value (within existing shot-noise tolerance)
  of any previously-extracted Fourier coefficient on any existing fixture —
  it changes construction COST only.
- **FR-010** (Critical Mandate 2, Constitution §5.4/§5.5): Any
  device/parallelism configuration this feature promotes from "a
  configurable knob" to "a recommended default" MUST be benchmarked fresh
  on this codebase's own post-repair circuit shapes, with the benchmark
  numbers reported — never inherited from a different codebase's prior
  findings, regardless of how similar those findings may seem.
- **FR-011** (Critical Mandate 4, Constitution §5.3 scope limit): This
  feature MUST NOT introduce transpile-caching, parametrized-template
  reuse, or batching across multiple circuits/graphs — those remain
  explicitly out of scope for this feature regardless of any speedup they
  might plausibly offer, absent their own bottleneck profile.
- **FR-012** (Two-Tiered Equivalence Proof, Tier 1 — Construction
  Correctness; Clarifications 2026-08-21): On genuinely small (1-2 qubit)
  fixtures — where a full `Operator()` reconstruction is tractable for
  BOTH the existing `.control()`-based construction and the new
  inline-assembled one — `Operator.equiv` MUST confirm the two compute the
  identical operator. This proves the inline-assembly LOGIC itself has no
  baseline construction bug, independent of scale.
- **FR-013** (Two-Tiered Equivalence Proof, Tier 2 — Scale Correctness;
  Clarifications 2026-08-21): At the ACTUAL documented 14-qubit baseline
  scale, a `Statevector`-based comparison MUST be performed in place of an
  intractable full `Operator()` reconstruction: both the old
  `.control()`-based circuit and the new inline-assembled circuit,
  integrating both FR-001/FR-002 repair sites, are evaluated on at least
  two input states — the all-zero state and a Haar-random state — and
  their resulting statevectors MUST be confirmed equivalent. This mirrors
  Spec 3's own established precedent (research.md) for proving equivalence
  at a scale where a dense-operator proof is intractable.

### Key Entities *(include if feature involves data)*

- **Controlled Hadamard-Test Circuit**: `_hadamard_test_circuit`'s own
  output — the object whose internal `A(U,O)`-block controlled-gate
  construction is being repaired (FR-001), and the object Tier 2's
  14-qubit-scale `Statevector` comparison (FR-013) is performed against.
- **Controlled `V_l^dagger` Block**: `_v_l_dagger_circuit`'s own
  cyclic-increment/decrement sequence, as it appears controlled inside the
  Hadamard-test circuit — the second, independent repair site (FR-002).
- **Two-Tiered Equivalence Proof**: the pairing of Tier 1 (FR-012,
  small-fixture `Operator.equiv`) and Tier 2 (FR-013, baseline-scale
  `Statevector` comparison) — both required together (FR-003) before
  either repair site (FR-001, FR-002) is trusted.
- **Execution Configuration**: the pairing of (a) `transpile()`'s explicit
  `optimization_level`/basis-gate set (FR-004) and (b) the additive,
  optional `simulator` parameter (FR-006) — together, what a caller can
  now deliberately control that was previously silent or hardcoded.
- **Benchmark Report**: the before/after wall-clock comparison on the
  documented baseline configuration (FR-005), and any fresh
  device/parallelism benchmark backing a promoted default (FR-010) —
  both reproduced across ≥2 trials and reported with hardware, qubits,
  depth, circuit count, and shots (Constitution §5.5).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the documented baseline configuration (`n=3, r=2,
  shots=20000, seed=7, t=1.09`), the repaired construction's wall-clock
  time is substantially and reproducibly lower than the unmodified
  code's measured `1108.00s`, with both figures reproduced across at
  least 2 trials each.
- **SC-002**: Every test in this project's existing test suite that
  exercises the Extract Layer or its Spec 10 dependents passes with zero
  modifications after this feature ships.
- **SC-003**: A developer can supply a pre-configured `AerSimulator` to
  any of the three affected functions and observe that configuration
  genuinely take effect, while a developer who supplies nothing observes
  behavior indistinguishable from before this feature shipped.
- **SC-004** (Clarifications 2026-08-21): Every claim in this feature's own
  implementation record that the repaired construction computes the same
  result as the old one is backed by BOTH an executed Tier 1
  `Operator.equiv` result (small fixtures) AND an executed Tier 2
  `Statevector`-equivalence result (14-qubit baseline scale, all-zero and
  Haar-random states) reported alongside the claim — never asserted from
  inspection, algebraic reasoning, or Tier 1 alone.
- **SC-005**: A developer reading `estimate_coefficient`'s source can
  identify the exact `optimization_level` and basis-gate set used for
  transpilation without consulting Qiskit's own version-dependent
  documentation.

## Assumptions

- This feature repairs and configures already-shipped Spec 4 (Extract
  Layer) and Spec 10 (kernel-overlap extraction) code; it introduces no
  new user-facing capability beyond the execution-configuration surface
  named in deliverable (c) — Specs 1-10's own extracted quantities and
  their public function signatures (beyond the additive `simulator`
  parameter) are unchanged.
- The SPECIFIC `optimization_level` value and basis-gate set (deliverable
  b) are determined by benchmarking during `/speckit-plan`'s Phase 0
  research, against the User-Story-1-repaired circuit — not decided in
  this spec, per Critical Mandate 2's own insistence that such defaults be
  freshly measured rather than assumed.
- Likewise, whether any device/parallelism configuration is promoted to a
  recommended default (as opposed to remaining a caller-supplied,
  unopinionated knob) is a `/speckit-plan`-level decision, contingent on
  what the fresh, post-repair benchmark on this codebase actually shows —
  this spec does not presuppose the old repository's GPU-below-20-qubits
  or `max_parallel_experiments` findings apply here.
- "Existing small fixtures" (FR-012's Tier 1 proof obligation) means the
  genuinely small (1-qubit) fixture already present in and reused
  unchanged across `tests/unit/test_extract_hadamard_test.py` and
  `tests/oracle/test_extract_convergence.py` (both built on the same
  "mandated fixture": three untied uploads of one parameter, `S`/`T` fixed
  gates interleaved, observable `X`) — not a newly-invented fixture set.
  `tests/unit/test_extract_full_coefficients.py` also exists and exercises
  `extract_coefficients`/`estimate_coefficient` at a higher level (full
  coefficient set, cost budget, non-Hermitian rejection) on a similar
  1-qubit fixture, but does not import `_hadamard_test_circuit`/`_v_l_
  dagger_circuit` directly, so it is a FR-008 "must pass unmodified"
  regression file rather than a Tier 1 `Operator.equiv` fixture itself.
  (Corrected TWICE during implementation, Constitution §1.8 — first
  during `/speckit-plan` research: an earlier draft of this bullet cited
  this file at the wrong path, `tests/oracle/test_extract_full_
  coefficients.py`, which does not exist, and was "corrected" to say the
  file does not exist at all anywhere in the repo — which was ALSO wrong,
  since the file genuinely exists at `tests/unit/test_extract_full_
  coefficients.py`. Both verified directly against the actual file tree
  in-session, not assumed from memory either time.) `tests/oracle/
  test_extract_kernel_overlap_shots.py` (Spec 10) does NOT exercise
  `_hadamard_test_circuit`/`_v_l_dagger_circuit` at all (its `estimate_
  kernel_overlap` uses a direct measurement, no Hadamard-test ancilla), so
  it is not a Tier 1 fixture either, though FR-006/FR-007 (deliverable c)
  still apply to it. Tier 2 (FR-013), by contrast, deliberately does NOT
  reuse a small fixture — it targets the actual documented 14-qubit
  baseline scale specifically.
- **(Clarifications 2026-08-21)** Evaluating the OLD, unmodified
  `.control()`-based circuit at the documented 14-qubit baseline scale for
  Tier 2's `Statevector` comparison is expected to be extremely slow (the
  same dense-synthesis cost this whole feature exists to repair). This is
  an accepted, ONE-TIME verification cost that the research phase MUST
  pay in full — substituting a smaller, unrepresentative fixture to avoid
  this cost is strictly forbidden, because doing so would make Tier 2
  incapable of catching exactly the integration-at-scale defect it exists
  to catch (see Edge Cases: "Tier 1 passes but Tier 2 fails").
- The documented baseline (`n=3, r=2, shots=20000, seed=7, t=1.09` → 14
  qubits, 425 frequencies, 850 circuits, `1108.00s`, M1 hardware) is taken
  as given for this spec's own before/after comparison; `/speckit-plan`
  reproduces the "before" measurement itself (≥2 trials) rather than
  trusting the single cited figure as one of the required ≥2 trials.
- No hardware beyond "ordinary consumer hardware" (the same class the
  1108s baseline was measured on) is assumed available for this feature's
  own benchmarking; a GPU- or cluster-specific benchmark is out of scope
  unless such hardware is already the developer's own machine.
