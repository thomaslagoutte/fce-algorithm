# Feature Specification: Extract Layer

**Feature Branch**: `004-extract-layer`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Extract Layer for FCE. Deliverables: (a) A shot-based execution engine that runs the compiled A(U, P) circuit and extracts the Fourier coefficients from the measurement counts. (b) A statistical convergence test validating the finite-shot sampling against the exact Foundation oracle. CRITICAL MANDATES: 1. Constitution Article II (Measurement-only production path) applies absolutely: the production extraction code MUST be measurement-only (finite shots). Strictly forbidden from using Statevector or Operator simulators in the production code. 2. For the convergence test's genuinely complex fixture, do NOT blindly search for one. Explicitly reuse the non-Clifford fixture discovered in Spec 3's research.md R8 (X, X, Z uploads with S and T fixed gates, observable X) to guarantee complex coefficients and save research time."

## Clarifications

### Session 2026-08-20

- Q: Can `b_{-l} = conj(b_l)` (FR-006's conjugate-symmetry shortcut) be
  assumed to hold for the actual Hadamard-test estimator, or must it be
  verified against Spec 1's specific frequency/two's-complement convention
  first? → A: Verified, not assumed — partially now, fully required before
  `/speckit-plan` accepts the shortcut. Checked in-session against Spec 1's
  exact oracle, using this spec's own mandated reuse fixture (research.md
  R8's `X,X,Z`-with-`S`-then-`T` construction): `b_{-l}` matches `conj(b_l)`
  exactly for every nonzero frequency pair (`l=±2,±4,±6`), and the DC term
  (`l=0`) comes out exactly real. This confirms the identity holds under
  Spec 1's frequency convention at the *exact* (oracle) level — it does
  **not** yet confirm the *Hadamard-test estimator's own* raw output (which
  does not exist as code until `/speckit-plan`/`/speckit-implement`) is free
  of an accidental sign flip in its own measurement-to-Re/Im formula or in
  which register value its "`-l`" state-preparation step actually targets.
  FR-006 now mandates that specific, additional check explicitly, before the
  shortcut may be relied upon in the implementation.
- Q: Should the new shot-count/circuit-count cost-budget guard (FR-007)
  define its own, independently-styled interface, or match Spec 1's existing
  grid-cost guard's interface conventions? → A: Intentionally mirror Spec 1's
  interface *style* — an equivalently-named exception type and the same
  `confirm=True` keyword-argument pattern — without importing anything from
  `fourierlearn.reference` (which this feature's own FR-001 already forbids,
  since only `reference.py` itself is exempt from the measurement-only CI
  guard). FR-007 updated accordingly.
- Q: Should the DC-frequency-is-real check (previously only an Edge Case
  note) be a one-off observation, or a standing, load-bearing test
  assertion? → A: Load-bearing and continuous — every extraction the test
  suite exercises must assert the DC coefficient comes out real (within the
  shot count's own tolerance), not only the dedicated convergence test's own
  fixture. This is not a redundant restatement of Hermiticity: it is a
  live, per-run check that the whole measurement pipeline still respects the
  Hermiticity invariant FR-006's shortcut depends on. New FR-012 and SC-006
  added.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature's "users" are the developers who build the `backends`/`learn`
  pipeline stages (the next stages, which will call this layer repeatedly
  during training and inference) on top of the Circuits Layer (Spec 3) and
  the Foundation Layer (Spec 1). Spec 3 already compiles the observable-folded
  circuit `A(U, O)`; this layer is the first thing that actually *runs* it —
  with finite shots, the way the real algorithm must always be executed
  (Constitution §3) — and turns the resulting counts into estimated Fourier
  coefficients, rather than requiring every caller to hand-build a Hadamard
  test and interpret raw counts themselves.
-->

### User Story 1 - Estimate one Fourier coefficient from finite shots (Priority: P1)

A developer who has a circuit compiled by the Circuits Layer (`A(U, O)`)
wants to estimate a single, specific Fourier coefficient of the observable's
expectation-value function, using only a finite number of measurement shots
— the way any real quantum device or noiseless-but-still-sampled simulator
run must work — without hand-building the Hadamard-test circuit or
interpreting raw measurement counts themselves.

**Why this priority**: This is the foundational, single-frequency extraction
primitive (Barthe thesis Corollary 5.1/5.2: "extract any coefficient `b_l` up
to additive error, by using controlled versions of `A(U)` in a Hadamard
test"). Every other deliverable in this spec — extracting the full
coefficient set (User Story 2) and validating shot-based convergence (User
Story 3) — is built by repeating or checking this one primitive.

**Independent Test**: Can be fully tested by compiling a small, explicit
circuit whose Fourier coefficients are already known (from Spec 1's exact
oracle), requesting one specific frequency with a generous shot count, and
confirming the returned estimate is close to the known value by an amount
consistent with that shot count's own statistical uncertainty.

**Acceptance Scenarios**:

1. **Given** a compiled observable-folded circuit and one requested integer
   frequency, **When** the engine estimates that frequency's coefficient
   using a specified, finite, positive shot count, **Then** it returns a
   complex estimate together with the exact shot count actually used.
2. **Given** the same request repeated with a much larger shot count,
   **When** both estimates are compared against the Foundation Layer's exact
   oracle value for that frequency, **Then** the larger-shot-count estimate
   is no less accurate, consistent with a shot-noise process that shrinks
   with more shots rather than a fixed or growing error.
3. **Given** a request for a shot count of zero or a negative number,
   **When** the engine is asked to estimate a coefficient, **Then** it raises
   rather than silently defaulting to some other shot count or returning a
   fabricated result.
4. **Given** any two runs of the same request with the same shot count but
   different random seeds, **When** both are checked against the exact oracle
   value using the same statistically-derived tolerance, **Then** both pass —
   the tolerance is not tuned to one particular seed.

---

### User Story 2 - Extract the full Fourier coefficient set efficiently (Priority: P2)

A developer who already has User Story 1's single-frequency estimator wants
to extract every Fourier coefficient the compiled circuit's frequency
register can represent, in one call, without paying for a separate circuit
execution for both a frequency and its "mirror" frequency when one is
mathematically redundant given the other.

**Why this priority**: Builds directly on User Story 1. Because the folded
observable is Hermitian, the resulting function is real-valued, which forces
every coefficient's "mirror" (negative-frequency) partner to be its complex
conjugate. Extracting both independently would be a wasted, redundant circuit
execution for every mirrored pair — this story is the efficient, complete
extraction built from the single-frequency primitive, not a new estimation
method.

**Independent Test**: Can be fully tested by compiling a small circuit,
requesting the full coefficient set, and confirming that (a) every frequency
the frequency register can represent is present in the result, and (b) the
number of circuit executions actually performed is consistent with only the
non-mirrored half of the frequencies being independently estimated.

**Acceptance Scenarios**:

1. **Given** a compiled circuit with a known frequency domain, **When** the
   full coefficient set is requested, **Then** the result contains exactly
   one estimate for every representable frequency, including the zero
   (DC) frequency, which is its own mirror.
2. **Given** the same request, **When** the number of circuit executions is
   counted, **Then** it reflects estimating only one frequency of each
   mirrored pair directly and deriving its partner by conjugation, not
   estimating every frequency independently.
3. **Given** a non-Hermitian observable were ever supplied (a caller error,
   since the Foundation Layer already requires Hermitian observables),
   **When** the engine is about to rely on the mirrored-conjugate shortcut,
   **Then** it raises rather than silently applying a shortcut that assumes
   a property that does not hold.

---

### User Story 3 - Validate shot-based convergence against exact ground truth (Priority: P3)

A developer who has built the shot-based extraction engine needs proof that
its estimates actually converge toward the Foundation Layer's exact oracle
values as more shots are used — not just that the code runs — and needs a
validation fixture that is already known to produce genuinely complex
coefficients, rather than spending time re-discovering one.

**Why this priority**: Depends on both prior stories existing, but is not
optional polish: Constitution §4.1 treats a component with no passing
ground-truth validation as not done "however well it runs," and §4.4 requires
shot-based tolerances to be derived from a concentration bound for the
configured shot count, not chosen because a particular run happened to pass.

**Independent Test**: Can be fully tested standalone: take the exact
non-Clifford construction already verified in the Circuits Layer's own
research (three untied uploads — `X`, `X`, `Z` — with a fixed `S` gate then a
fixed `T` gate interspersed, observable `X`), which is already known to
produce a genuinely complex non-DC coefficient; run the shot-based engine at
several increasing shot counts; and confirm each estimate falls within that
shot count's own derived tolerance of the Foundation Layer's exact value.

**Acceptance Scenarios**:

1. **Given** the reused non-Clifford fixture from the Circuits Layer's own
   research (not a newly searched-for one), **When** the shot-based engine
   estimates its known-genuinely-complex non-DC coefficient at a stated shot
   count, **Then** both the real and imaginary parts of the estimate fall
   within a tolerance derived from that shot count's own concentration bound
   of the Foundation Layer's exact value.
2. **Given** the same fixture estimated at several increasing shot counts,
   **When** the resulting errors are compared, **Then** they are consistent
   with shrinking as the shot count grows, not flat or growing.
3. **Given** the same validation run repeated with a different random seed,
   **When** it is checked against the same derived tolerance, **Then** it
   still passes — the tolerance was not chosen by trying seeds until one
   worked.

---

### Edge Cases

- What happens when the zero (DC) frequency is requested? It is its own
  mirror under negation, so the conjugate-symmetry shortcut (User Story 2)
  does not apply to it — it is always estimated directly, and its estimate
  must come out real (zero imaginary part, within shot noise). This is
  elevated to a load-bearing test assertion (FR-012), not left as an
  informational note: every full-coefficient-set test in this feature's own
  suite checks it, on every run, as a continuous live check that the whole
  measurement pipeline still respects the Hermiticity invariant FR-006's
  shortcut depends on.
- What happens when the requested shot count is extremely large, making the
  predicted number of circuit executions expensive? The engine must predict
  and log that cost before running, and refuse to exceed a configured budget
  without explicit confirmation — mirroring the Foundation Layer's own
  cost-budget guard for its (different) grid-size cost dimension, not
  duplicating its implementation.
- What happens when a caller requests a frequency the compiled circuit's
  frequency register cannot represent? The engine must raise rather than
  silently returning a meaningless or zero-filled result.
- What happens when the same request is run twice with the same seed and
  shot count? It must return the identical estimate both times (deterministic
  given a fixed seed), even though the extraction is inherently a sampling
  process.
- What happens when a caller asks for an exact, infinite-shot, or `shots=None`
  result? This must be rejected outright — no such mode exists in this
  feature, by design (Constitution §1.2).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The engine MUST estimate a Fourier coefficient using only
  finite-shot measurement execution — never by inspecting an exact quantum
  amplitude or state. This is Constitution Article II's measurement-only
  production path applied without exception, and is mechanically enforced by
  the Foundation Layer's own existing CI import guard (Spec 1 FR-014/FR-015),
  which already scans every module under this project's source tree,
  including any this feature adds.
- **FR-002**: The engine MUST NOT provide, and MUST reject any attempt to
  request, an exact / infinite-shot / `shots=None` execution mode (§1.2).
  Every entry point requires an explicit, finite, positive shot count.
- **FR-003**: For a single requested integer frequency, the engine MUST
  construct a Hadamard-test circuit wrapping the Circuits Layer's own
  compiled observable-folded circuit (Spec 3's `compile_observable_circuit`,
  reused unchanged — not reimplemented), execute it with the caller's
  specified finite shot count, and derive both the real and imaginary parts
  of that frequency's coefficient from the resulting measurement counts
  (Barthe thesis Corollary 5.1/5.2).
- **FR-004**: The engine MUST NOT synthesize shot noise by sampling around an
  exactly-computed value (§1.3) — every returned estimate MUST come from
  counts produced by an actually-executed, finite-shot circuit.
- **FR-005**: The engine MUST be able to extract the full set of Fourier
  coefficients for every frequency the compiled circuit's frequency
  register(s) can represent, in one call, built from FR-003's single-frequency
  primitive.
- **FR-006**: When extracting the full coefficient set, the engine MUST
  exploit the conjugate-symmetry identity that holds for a Hermitian
  observable's real-valued expectation function (every coefficient's
  negative-frequency mirror is its complex conjugate) to avoid a redundant
  circuit execution for both a frequency and its mirror (Constitution §7.6).
  It MUST first confirm the observable is Hermitian before relying on this
  shortcut, and MUST always estimate the zero (DC) frequency directly, since
  it is its own mirror. **Before `/speckit-plan`'s design may rely on this
  shortcut, it MUST computationally verify — on a small circuit, using this
  spec's own mandated reuse fixture (FR-010) — that the actual Hadamard-test
  estimator's raw output at `+l` and its raw output at the register-decoded
  `-l` (under Spec 1's specific two's-complement/frequency convention) are
  exact complex conjugates of each other**, not merely assume the general
  Fourier identity carries through the estimator's own measurement-to-Re/Im
  formula and register-decoding path unchanged (Clarifications, 2026-08-20:
  the identity was already confirmed, in-session, to hold at the *exact*
  oracle level for this exact fixture — `l=±2,±4,±6` all matched conjugates
  exactly, and `l=0` came out exactly real — but that check cannot stand in
  for verifying the estimator itself, which does not exist as code yet).
- **FR-007**: The engine MUST predict and log the total execution cost
  (number of circuit executions times shots per execution) before running,
  and refuse to exceed a configured budget without explicit confirmation
  (Constitution §10.3) — analogous to, but not a reuse of, the Foundation
  Layer's own grid-size cost-budget guard, since this feature's cost
  dimension (shots × circuits) is different from that oracle's (grid points).
  **This new guard MUST intentionally mirror Spec 1's existing guard's
  interface style — an equivalently-named exception type (e.g. a
  `ShotBudgetExceeded`-style name, paralleling `CostBudgetExceeded`) and the
  same `confirm=True` keyword-argument pattern** — so callers already
  familiar with Spec 1's oracle guard find a consistent pattern here, not a
  divergent one. This exception type MUST be defined locally in this
  feature's own module, not imported from `fourierlearn.reference` (FR-001
  already forbids importing `reference` in any production module here).
- **FR-008**: The engine MUST raise when given a zero, negative, or otherwise
  degenerate shot count (§10.1), or when asked to extract a frequency the
  compiled circuit's frequency register cannot represent, rather than
  returning a plausible-looking but meaningless result.
- **FR-009**: A dedicated statistical convergence test MUST compare the
  engine's shot-based estimates against the Foundation Layer's exact oracle
  values, at more than one increasing shot count, with a tolerance at each
  shot count derived from a stated concentration bound for that shot count
  (Constitution §4.4) — not a tolerance chosen because one particular run
  happened to pass. The test MUST pass for any random seed; choosing a seed
  until it passes is prohibited.
- **FR-010**: The convergence test's genuinely-complex validation fixture
  MUST reuse, unchanged, the non-Clifford construction already verified in
  the Circuits Layer's own research (research.md R8: three untied uploads —
  `X`, `X`, `Z` — with a fixed `S` gate then a fixed `T` gate interspersed,
  observable `X`) — it MUST NOT be independently re-derived or re-searched
  for this spec, per explicit instruction.
- **FR-011**: Every shot-based result the engine returns MUST record the
  exact shot count used to produce it (Constitution §5.6), so that any
  consumer of the result can independently reason about its expected
  statistical uncertainty.
- **FR-012** (new, Clarifications 2026-08-20): Every test in this feature's
  test suite that extracts a full coefficient set — not only the dedicated
  convergence test's own fixture — MUST assert, as a load-bearing check (not
  an optional or informational one), that the extracted DC (`l=0`)
  coefficient's imaginary part is zero within that run's own shot-based
  tolerance. This is not a restatement of FR-006's Hermiticity precondition:
  it is a continuous, live check that the measurement pipeline as actually
  implemented and executed still respects the Hermiticity invariant FR-006's
  conjugate-symmetry shortcut depends on, on every run, not only once at
  design time.

### Key Entities *(include if feature involves data)*

- **Hadamard-test circuit**: The circuit this layer builds by wrapping the
  Circuits Layer's own compiled `A(U, O)` circuit with an additional ancilla
  and a state-preparation step for one target frequency, whose ancilla
  measurement statistics reveal that frequency's coefficient (Barthe thesis
  Corollary 5.1/5.2, Figure 5.7).
- **Shot-based estimate**: One complex number (a Fourier coefficient
  estimate) together with the exact finite shot count that produced it.
- **Concentration-bound tolerance**: The statistically-derived acceptable
  error margin for a shot-based estimate at a given shot count, used by the
  convergence test (User Story 3) instead of an arbitrarily chosen number.
- **Full coefficient set**: The complete mapping from every representable
  frequency to its estimated coefficient, built from independently estimating
  only the non-mirrored half of the frequencies (User Story 2) plus the
  always-direct DC term.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can obtain an estimated Fourier coefficient for any
  single requested frequency of a compiled circuit, using only a specified,
  finite number of measurement shots.
- **SC-002**: A developer can obtain the complete set of Fourier coefficients
  for a compiled circuit in one call, performing independent circuit
  executions for only the non-mirrored half of the representable frequencies
  (plus the always-direct DC term), not for every frequency independently.
- **SC-003**: Shot-based estimates agree with the Foundation Layer's exact
  oracle values within a tolerance derived from a stated concentration bound
  for the shot count used, on a genuinely complex validation case, regardless
  of random seed.
- **SC-004**: No production code path in this feature ever imports or invokes
  exact-state inspection (`Statevector`, `Operator`, or `expm`) — verified
  mechanically by the Foundation Layer's existing CI import guard, with zero
  new violations introduced.
- **SC-005**: Every shot-based result a caller receives states the exact shot
  count used to produce it.
- **SC-006** (new, Clarifications 2026-08-20): Every full-coefficient-set
  extraction this feature's own test suite exercises confirms, as a
  load-bearing assertion, that the DC coefficient's imaginary part is zero
  within that run's own tolerance — a continuous, per-run check on the
  Hermiticity invariant the conjugate-symmetry shortcut (SC-002) depends on.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1:
  `PauliEncodedCircuitIR`, `frequency.py`'s conventions, and the reference
  oracle) and the completed Circuits Layer (Spec 3:
  `compile_observable_circuit`) — neither is re-specified here.
- **Measurement-only discipline (explicit process mandate)**: Constitution
  Article II / §3 (the measurement-only production path) applies to this
  feature without exception. No production module in this feature may import
  or invoke `Statevector`, `Operator`, or `expm` — enforced mechanically by
  the Foundation Layer's own CI import guard, which already recursively scans
  the entire source tree and therefore requires no changes for this feature.
- **Fixture reuse (explicit instruction, not a preference)**: the
  statistical convergence test's genuinely-complex validation case is the
  exact non-Clifford construction already verified in the Circuits Layer's
  research (research.md R8) — reused as-is, not independently re-derived or
  re-searched, to avoid redundant verification effort for a fixture already
  known to work.
- Scoped to a single Hermitian Pauli-string observable per compiled circuit,
  matching the Circuits Layer's own scope (Spec 3 Assumptions). The
  weighted-sum/linear-combination-of-Paulis extension remains out of scope,
  deferred with the same named `TODO` Spec 3 already recorded (Constitution
  §4.7) — this feature does not need to resolve it to extract coefficients
  for the single-Pauli-string case.
- The specific finite-shot execution primitive this feature calls (e.g. an
  Aer-native batched run with counts, or a sampler-style primitive) is a
  `/speckit-plan`-level decision — Constitution §9.6 permits more than one
  compliant choice for the extraction path, and this spec only requires that
  some finite-shot, counts-producing path is used, not which specific one.
- This feature validates shot (sampling) noise only, against Aer's noiseless
  simulator backend — physical hardware noise characterization is a
  separate, later concern (Constitution §8.6) and is out of scope here.
- The convergence test's "increasing shot counts" requirement (FR-009) needs
  at least two distinct shot counts to demonstrate a shrinking-error trend;
  the exact counts and how many are chosen during `/speckit-plan`, not
  specified here.
