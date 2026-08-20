# Feature Specification: Circuits Layer

**Feature Branch**: `003-circuits-layer`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Circuits Layer for FCE. Deliverables: (a) A compiler for the unconditional unitary A(U) that implements the parity-fold logic. (b) A compiler for the controlled unitary A(U, P) that interleaves the controlled parameter shifts. (c) The basis-change sandwich trick for observables. CRITICAL MANDATE: Every single sign, coefficient, phase, or gate-ordering claim made during the research and planning phases of this spec MUST be computationally verified against Operator.equiv or scipy.linalg.expm before it is written down as a decision. You are explicitly forbidden from stating a derivation or formula for the parity-fold, controlled counter, or basis change without showing the accompanying computational proof that it produces the exact target unitary. This strict verification discipline is required to prevent the silent conjugacy/ordering bugs we caught in Specs 1 and 2."

## Clarifications

### Session 2026-08-20

- Q: Is the parity ancilla genuinely one single qubit shared across the whole
  compiled circuit (all parameters, all gates), or one per parameter? → A:
  Genuinely one single, shared qubit for the entire circuit — confirmed by
  direct citation, not inferred: Barthe thesis §5.7.3 states explicitly "There
  is also a single additional ancillary qubit that is used to compute
  parities," and that omitting this sharing (i.e., not reusing one ancilla)
  "occurs an overhead exponential in the locality of Pauli strings" — the
  shared-and-reused design is specifically what avoids that blow-up. Every
  encoding gate, regardless of which parameter it drives, computes its parity
  onto this same physical qubit and uncomputes it (resetting it to `|0>`)
  before the next encoding gate uses it — never held across two gates at
  once, so no race condition or entanglement leakage between gates is
  possible as long as gates are compiled in the circuit's own sequential
  order.
- Q: What exactly is "the reversed pass" for `A(U, P)` — a literal
  `.inverse()` of the assembled forward-compiled circuit, or a separately
  constructed reverse-order loop using adjoint/role-swapped shift primitives
  (`V+` in place of `V-` and vice versa)? → A: **Computationally verified
  in-session, not assumed**: both candidates were built as explicit small
  matrices (a 1-qubit circuit, two untied encoding gates around a fixed `S`
  gate, `Z` observable) and compared directly. (1) Adjointing the compiled
  `G(j) = C(a)V+ + C̄(a)V-` block gives `G(j)^dagger = C(a)V- + C̄(a)V+` —
  algebraically and numerically the *exact* role-swapped block, to
  floating-point exactness (`max|R1-R2| = 0.0`). (2) The resulting full
  construction — forward pass, fixed observable insertion, and this reversed
  pass — was checked end-to-end against an independently computed
  brute-force Nyquist-grid-and-FFT ground truth for the same toy circuit and
  matched exactly (relative error ≤ 1e-9) across every frequency, including a
  genuinely non-DC, non-degenerate coefficient. Because the two candidate
  constructions are *provably the same operation*, the compiler MUST
  implement the reversed pass as the literal inverse of the already-assembled
  forward circuit (e.g. one call to the underlying circuit framework's own
  `.inverse()`), not as a second, independently written and maintained
  construction — a single code path, per Constitution §9.4, rather than two
  that happen to coincide. This same toy verification also caught and fixed
  two unrelated modeling bugs on the way to this result (a reversed
  control/target CNOT direction, and an undersized frequency register for a
  2-upload case, which silently aliased `l=+4` and `l=-4` into the same
  register slot) — both are carried forward as explicit findings for
  `/speckit-plan`'s own research.md, not silently corrected and discarded.
  **Re-verified on a genuinely stronger stress case, not just the minimal
  d=1 toy** (follow-up check, same session): a 2-parameter circuit — Parameter
  `A` with tied multiplicity `r_A=2` (its two tied `Z`-type terms deliberately
  *not* adjacent in the gate list), Parameter `B` untied, gates interleaved as
  `[A-term1, B, A-term2]`, all sharing the single global ancilla, with the two
  frequency registers correctly independently sized (`A`: `r_j=2, L=1` → 16
  states; `B`: `r_j=1, L=1` → 8 states). Every primitive (the parity CNOT, the
  controlled shift, the local gate embedding) was built *programmatically*
  from its own definition (iterating every basis state and computing where it
  maps), not hand-typed as a matrix literal, to avoid repeating the earlier
  manual-indexing bug class. Result: `R1` (literal inverse of the assembled
  forward circuit) and `R2` (independently reconstructed reverse-order pass
  with role-swapped shift primitives) matched to `max|R1-R2| = 0.0`, and the
  full `A(U,P)` construction using `R1` matched an independent brute-force
  2-D Nyquist-grid-and-FFT ground truth exactly, across the entire sampled
  `(l_A, l_B)` grid (45 points), for a genuinely multi-parameter, tied,
  interleaved, ancilla-sharing case — not only the single-parameter case the
  original verification used. FR-006's mandate (literal circuit inverse, not
  a second hand-maintained construction) is confirmed to hold under
  contention on the shared ancilla, not merely in the case too simple to
  exercise it.
- Q: Should the encoding-gate basis change (User Story 1) and the
  observable basis change (User Story 3) be two independent
  implementations, or one shared helper? → A: One single, shared helper
  function, used by both. Both roles solve the identical sub-problem — given
  a Pauli string, produce the fixed conjugating gate pair that maps it to an
  equivalent `Z`-type string — and a second, independently written
  implementation of that same mapping would be exactly the duplicated call
  path Constitution §9.4 prohibits, with no principled reason for the two
  copies to ever diverge.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature's "users" are the developers who build the `extract` layer (the
  next pipeline stage, which will run these compiled circuits with finite shots
  and post-process the counts) on top of the Foundation Layer (Spec 1) and the
  Encodings Layer (Spec 2). Those two layers already produce a
  `PauliEncodedCircuitIR` instance and validate it against an exact reference
  oracle; this layer is the first thing that turns that IR into the actual
  circuit that a Fourier-coefficient-extraction algorithm executes, rather than
  requiring every caller to hand-derive the frequency-register bookkeeping and
  observable-folding logic themselves.
-->

### User Story 1 - Reveal a circuit's frequency spectrum without re-running it (Priority: P1)

A developer who has a Pauli-encoded circuit (Spec 1's `PauliEncodedCircuitIR`,
however it was produced — by hand, by Spec 2's Pauli-PQC frontend, or by its
Trotter frontend) wants a single, fixed (non-parameterized) circuit that, when
prepared and measured, directly reveals which integer frequencies compose that
circuit's output — instead of having to run the original circuit once per
candidate parameter value and infer the spectrum indirectly.

**Why this priority**: This is the foundational compilation step every other
deliverable in this spec builds on (Barthe thesis Theorem 5.1's algorithm `A`).
Without it, there is no frequency register to fold an observable's contribution
into (User Story 2) and no register to apply a basis change against (User
Story 3).

**Independent Test**: Can be fully tested by compiling a small, explicit
`PauliEncodedCircuitIR` (one or two parameters, at most a handful of qubits),
preparing the compiled circuit's exact quantum state, and confirming the
amplitude on each frequency-register value matches the same circuit's
analytically known (or independently, numerically pre-verified) Fourier
decomposition — independent of any observable or sampling concern.

**Acceptance Scenarios**:

1. **Given** a Pauli-encoded circuit with one encoded parameter uploaded
   several times, **When** the compiler produces its unconditional circuit,
   **Then** the resulting circuit adds exactly one frequency-counter register
   sized per the Foundation Layer's own register-width rule, and no other
   register.
2. **Given** the same circuit, **When** the compiled circuit's exact state is
   inspected, **Then** the amplitude on each frequency-register value matches
   that circuit's known Fourier decomposition to floating-point precision.
3. **Given** a circuit with two or more encoded parameters, **When** the
   compiler runs, **Then** each parameter gets its own independent
   frequency-counter register, sized independently, and every encoding gate
   only ever affects its own parameter's register.
4. **Given** a circuit where one parameter has tied, multiplicity-greater-
   than-one uploads (Spec 1 FR-005), **When** the compiler runs, **Then** every
   tied gate contributes its own increment or decrement onto that parameter's
   single shared register, rather than each tied gate receiving an
   independent register.
5. **Given** a circuit whose encoding gates use Pauli letters other than `Z`
   (e.g. `X`, `Y`, or a multi-letter string), **When** the compiler runs,
   **Then** the resulting circuit still correctly reveals that circuit's
   frequency spectrum, without requiring the caller to have rewritten the
   circuit into an all-`Z` form themselves.

---

### User Story 2 - Extract a specific observable's Fourier coefficients (Priority: P2)

A developer who already has User Story 1's frequency-revealing compiler wants
to go one step further: given a Pauli-encoded circuit *and* a chosen Hermitian
observable, produce a circuit whose frequency register directly encodes the
Fourier coefficients of that specific observable's expectation-value function
— the actual quantity Fourier Coefficient Extraction is for — rather than just
the raw spectrum of the circuit's own output state.

**Why this priority**: Builds directly on User Story 1 (Barthe thesis
Corollary 5.1, Figure 5.4): the observable-folded circuit is built by combining
User Story 1's construction for the forward circuit, a fixed insertion of the
observable, and the same construction again for the reversed circuit, all
sharing one set of frequency registers. Without User Story 1 existing first,
this story would have to reimplement the same frequency-register logic from
scratch, duplicating a call path (Constitution §9.4).

**Independent Test**: Can be fully tested by compiling a small circuit together
with a chosen Pauli-string observable, preparing the compiled circuit's exact
state, and confirming the frequency register's amplitudes match that specific
observable's known Fourier coefficients (not merely the circuit's own raw
spectrum from User Story 1) to floating-point precision.

**Acceptance Scenarios**:

1. **Given** a Pauli-encoded circuit and a Pauli-string observable, **When**
   the compiler produces the observable-folded circuit, **Then** the result
   shares the identical per-parameter frequency registers User Story 1 would
   produce for that same circuit — no additional or differently-sized
   registers are introduced by folding in the observable.
2. **Given** that same construction, **When** the compiled circuit's exact
   state is inspected and post-selected on the original circuit register
   reading all-zero, **Then** the resulting frequency-register amplitudes
   match that observable's known Fourier coefficients to floating-point
   precision.
3. **Given** a circuit with more than one encoded parameter, **When** the
   observable-folded circuit is compiled, **Then** the frequency register for
   every parameter reflects the *difference* between the forward pass's and
   the reversed pass's contributions to that parameter, not merely the
   forward pass's contribution alone.

---

### User Story 3 - Fold in an observable that is not already diagonal (Priority: P3)

A developer who has User Story 2's observable-folded compiler wants to supply
an observable expressed as an arbitrary Hermitian Pauli string (e.g. one built
from `X` or `Y`, not only `Z`), without first manually rewriting it into an
equivalent all-`Z` form themselves.

**Why this priority**: User Story 2's construction (Barthe thesis Corollary
5.1, Figure 5.4) is stated for an observable that is already a `Z`-type string;
the thesis notes this is without loss of generality because any Pauli string
can be turned into a `Z` string by "local changes of basis" (§5.7.3). This
story is the compiler-facing realization of that reduction, applied
specifically to the observable (the encoding gates' own analogous reduction is
already folded into User Story 1's own compilation, since Definition 5.1's
encoding gates are already general Pauli strings there).

**Independent Test**: Can be fully tested by supplying the same small circuit
and target Fourier coefficient from User Story 2's test, once with an
observable already expressed as a `Z`-type string and once with a
*Hamiltonian-equivalent* observable expressed using `X`/`Y` instead, and
confirming both compilations produce the identical frequency-register
amplitudes.

**Acceptance Scenarios**:

1. **Given** a Hermitian Pauli-string observable that is not purely a `Z`-type
   string, **When** the compiler folds it into the circuit, **Then** it
   inserts a fixed pair of basis-change gates (one before, one after) around
   the point where the observable would otherwise need to act directly in the
   `Z` basis, rather than rejecting the observable or requiring the caller to
   rewrite it.
2. **Given** the same physical observable expressed two different but
   equivalent ways (already `Z`-type, versus requiring a basis change),
   **When** each is compiled and evaluated, **Then** both produce the same
   frequency-register amplitudes to floating-point precision.

---

### Edge Cases

- What happens when a Pauli-encoded circuit contains fixed (non-parameterized)
  gates interspersed among its encoding gates? They must pass through the
  compiled circuit unchanged, acting only on the original circuit's own
  qubits, never on a frequency register or the parity ancilla.
- What happens when an encoded parameter's tied gates (multiplicity `r_j > 1`)
  are compiled? Every tied gate contributes its own increment/decrement onto
  that one shared register — never independent registers, and never a single
  combined step that skips intermediate values (Constitution §11.2, §11.3;
  Z2LGT report §5.2).
- What happens when the input circuit has zero encoded parameters (only fixed
  gates)? The compiler must raise rather than silently produce a circuit with
  no frequency register at all (Constitution §10.1) — there is nothing for
  User Story 1 or 2 to reveal.
- What happens when two different encoded parameters' encoding gates act on
  overlapping qubits? Each parameter's parity computation and register
  increment/decrement must still act only on that parameter's own frequency
  register — shared circuit qubits do not cause shared or merged registers.
- What happens when encoding gates for *different* parameters are
  interleaved in the circuit (parameter A's gate, then parameter B's, then
  parameter A's again)? The single shared parity ancilla (Clarifications,
  2026-08-20) is reused serially by each gate in turn — every encoding gate's
  own parity-compute/shift/uncompute block leaves the ancilla reset to `|0>`
  before the next gate (of any parameter) uses it, so interleaving gates from
  different parameters is safe and never causes cross-parameter
  interference.
- What happens when the observable folded in by User Story 2 acts on qubits
  that are also touched by encoding gates? This is expected and required (an
  observable is generally a function of the same circuit register the
  encoding gates act on); the compiler must not treat this as an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The compiler MUST accept a Foundation-Layer `PauliEncodedCircuitIR`
  (Spec 1) as its structural input, and MUST NOT require any encoding-specific
  knowledge of how that IR was produced (Spec 2's frontends, or any other
  `Encoding`) — matching the Foundation Layer's own typed `Encoding -> IR`
  boundary (Spec 1 FR-001, Constitution §9.1, §9.2).
- **FR-002**: For User Story 1, the compiler MUST produce a non-parameterized
  circuit that appends exactly one frequency-counter register per encoded
  parameter, each sized by the Foundation Layer's own `register_width` rule
  (Spec 1 FR-010) — not a redefined or duplicated width formula (Constitution
  §6.3, §9.4).
- **FR-003**: For each parameterized (Pauli-encoded) gate, the compiler MUST
  compute the parity of that gate's affected qubits onto **one single ancilla
  qubit, shared across the entire compiled circuit** — not one ancilla per
  parameter, and not one per gate (Clarifications, 2026-08-20; Barthe thesis
  §5.7.3: "There is also a single additional ancillary qubit that is used to
  compute parities" — omitting this sharing costs an overhead exponential in
  Pauli-string locality). The compiler MUST apply a controlled increment or
  decrement to that gate's own parameter's frequency register conditioned on
  that parity, and then uncompute the ancilla, leaving it reset to `|0>` for
  reuse by the next encoding gate — of any parameter — in circuit order
  (Barthe thesis Theorem 5.1, §5.7.3's algorithm `A`).
- **FR-004**: The compiler MUST NOT alter the physical meaning of a tied
  parameter's multiplicity: every gate sharing one `tie_group`/parameter MUST
  contribute its own increment/decrement step onto that parameter's single
  shared register, in the order the Foundation Layer's IR lists them
  (Constitution §11.2, §11.3; Z2LGT report §5.2 — "Barthe's algorithm A
  handles this unchanged").
- **FR-005**: The compiler MUST correctly compile encoding gates whose Pauli
  string is not already a pure `Z`-type string, by inserting a fixed
  basis-change gate pair (before/after) — obtained from the single shared
  basis-change helper (FR-014) — so the parity-and-increment logic, which is
  only directly meaningful for `Z`-type strings, applies to the correct,
  equivalent generator (Barthe thesis §5.7.3: "if encoding with X or Y appear
  they can be changed to Z with local unitary gates, which can be absorbed in
  the set of fixed gates").
- **FR-006**: For User Story 2, the compiler MUST accept, in addition to the
  circuit, one Hermitian Pauli-string observable, and MUST produce a circuit
  that combines User Story 1's construction for the forward circuit, a fixed
  insertion of that observable, and **the literal inverse of the already-
  assembled forward-compiled circuit** (reversed gate order, each gate
  individually adjointed) as the reversed pass — all sharing the identical
  per-parameter frequency registers User Story 1 alone would produce (Barthe
  thesis Corollary 5.1, Figure 5.4). The compiler MUST NOT implement the
  reversed pass as a second, independently written construction (e.g. a
  hand-maintained loop with role-swapped shift primitives): Clarifications
  (2026-08-20) computationally confirmed, on both a minimal single-parameter
  test case and a subsequent, deliberately harder stress case (two
  parameters, one with tied multiplicity, their encoding gates interleaved,
  all sharing the single global ancilla under real contention), that such a
  construction is provably identical to the literal circuit inverse — so
  implementing both would be exactly the duplicated call path Constitution
  §9.4 prohibits, not a genuine design choice between two different
  behaviors.
- **FR-007**: The observable-folded circuit's frequency register, once
  post-selected on the original circuit register reading all-zero, MUST
  encode the Fourier coefficients of the PQC function
  `f(alpha) = <0|U(alpha)^dagger O U(alpha)|0>` for the supplied observable
  `O` — not merely the raw frequency spectrum of `U(alpha)|0>` alone (Barthe
  thesis Corollary 5.1, equations 5.44-5.48).
- **FR-008**: For User Story 3, the compiler MUST accept a Hermitian
  Pauli-string observable using any combination of `I`/`X`/`Y`/`Z`, and MUST
  fold it in by conjugating with a fixed basis-change unitary — obtained from
  the same single shared basis-change helper FR-005 uses for encoding gates
  (FR-014) — rather than rejecting it, requiring the caller to supply an
  already-`Z`-type equivalent, or maintaining a second, independent
  implementation of the same Pauli-string-to-`Z` mapping (Barthe thesis
  §5.7.3 — "the Pauli string measurement can be considered a Z string").
- **FR-009**: The compiler MUST raise, rather than silently compile a
  meaningless circuit, when given a `PauliEncodedCircuitIR` with zero encoded
  parameters (Constitution §10.1).
- **FR-010**: The compiler's frequency registers MUST use the Foundation
  Layer's own frequency sign and indexing convention (Spec 1's
  `frequency.py`) — the compiler MUST NOT define its own increment/decrement
  sign, register layout, or two's-complement decoding independently
  (Constitution §6.1, §9.4).
- **FR-011**: A dedicated test MUST exist for every sign, coefficient, phase,
  and gate-ordering decision this compiler's design embodies (the parity
  convention, which parity increments versus decrements, the controlled-gate
  and basis-change ordering, and the forward/reverse composition of User
  Story 2), directly comparing the constructed unitary (or a small, explicit
  instance of it) against a hand-built target matrix via operator equivalence
  or matrix-exponential comparison — not inferred from end-to-end coefficient
  agreement alone (Constitution §2.1, §9.7; mirrors Spec 1 FR-021 and Spec 2's
  Trotter-formula verification, both of which caught a real sign error this
  way).
- **FR-012**: Both compiled-circuit constructions (User Story 1 and User
  Story 2) MUST be validated against the Foundation Layer's own exact
  reference oracle on small, explicit test circuits — reproducing the same
  Fourier coefficients the oracle already computes exactly, to floating-point
  precision — rather than introducing a second, independent notion of ground
  truth (Constitution §4.1, §4.2).
- **FR-013**: Every validation case for User Story 2 and User Story 3 MUST
  include at least one non-DC Fourier coefficient with independently
  confirmed nonzero real and imaginary parts, so that a scaling, sign, or
  basis-change defect cannot hide behind a validation case that happens to be
  purely real (Constitution §4.3, §6.4 — mirroring Spec 1 FR-018 and Spec 2
  FR-011/FR-012).
- **FR-014** (new, Clarifications 2026-08-20): There MUST be exactly one
  shared basis-change helper — given a Pauli letter (or string), it returns
  the fixed conjugating gate pair that maps it to an equivalent `Z`-type
  generator — used by both User Story 1's encoding-gate compilation (FR-005)
  and User Story 3's observable folding (FR-008). Neither MAY maintain its
  own, independently written copy of this mapping (Constitution §9.4).

### Key Entities *(include if feature involves data)*

- **Pauli-encoded circuit (input)**: The Foundation Layer's
  `PauliEncodedCircuitIR`, produced by any `Encoding` (Spec 2's frontends or
  otherwise) — this spec's structural input, not re-specified here.
- **Frequency-counter register**: One per encoded parameter, sized by the
  Foundation Layer's `register_width` rule, holding the accumulated pre-parity
  integer frequency in two's complement (Spec 1's own convention).
- **Parity ancilla**: A single qubit, shared across the entire compiled
  circuit (not one per parameter or per gate — Clarifications, 2026-08-20),
  that briefly holds the parity of one encoding gate's affected circuit
  qubits, drives a controlled increment/decrement of that gate's own
  parameter's frequency register, and is then uncomputed (reset to `|0>`) for
  reuse by the next encoding gate, regardless of which parameter it belongs
  to.
- **A(U) — the parity-fold compiler (User Story 1)**: Produces the
  unconditional, non-parameterized circuit whose state directly encodes the
  input circuit's raw Fourier-frequency decomposition.
- **A(U, O) — the observable-folded compiler (User Story 2/3)**: Produces the
  circuit combining a forward pass, a fixed insertion of the (possibly
  basis-changed) observable `O`, and a reversed pass — the literal inverse of
  the assembled forward-compiled circuit (Clarifications, 2026-08-20;
  computationally confirmed identical to a separately constructed,
  role-swapped reverse loop) — all sharing the same frequency registers, so
  its post-selected state directly encodes that observable's Fourier
  coefficients.
- **Basis-change sandwich**: A single, shared helper (used by both User
  Story 1's encoding gates and User Story 3's observable folding —
  Clarifications, 2026-08-20, FR-014) producing the fixed pair of conjugating
  gates that lets an arbitrary Hermitian Pauli string be folded in as though
  it were an equivalent `Z`-type string.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can turn any small Foundation-Layer Pauli-encoded
  circuit into a fixed circuit whose exact state directly reveals which
  integer frequencies that circuit's output contains, without re-running the
  original circuit at multiple parameter values.
- **SC-002**: A developer can turn that same circuit, plus a chosen Hermitian
  Pauli-string observable, into a fixed circuit whose exact, post-selected
  state directly reveals that observable's Fourier coefficients.
- **SC-003**: Both compiled constructions reproduce the Foundation Layer's own
  exact reference oracle's coefficients, on small test circuits, to
  floating-point precision (relative error ≤ 1e-9, matching Spec 1 SC-002's
  tolerance) — including at least one genuinely complex non-DC coefficient
  per construction.
- **SC-004**: A developer can supply an observable expressed with any
  combination of Pauli letters, not only `Z`, and get back the identical
  Fourier coefficients as an equivalent, already-`Z`-type expression of the
  same physical observable.
- **SC-005**: Every sign, coefficient, phase, and gate-ordering decision this
  compiler's design embodies is independently, computationally proven correct
  against a hand-built target unitary before being accepted as a design
  decision — not merely asserted from a source formula's resemblance to a
  previously-used one.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1:
  `PauliEncodedCircuitIR`, the `Encoding`/`Oracle` Protocols, `frequency.py`'s
  conventions, and the reference oracle) and the completed Encodings Layer
  (Spec 2: the Pauli-PQC and Trotter frontends) — neither is re-specified
  here.
- **Verification discipline (explicit process mandate for this spec's own
  `/speckit-clarify` and `/speckit-plan` phases)**: every sign, coefficient,
  phase, and gate-ordering claim this spec's later research and planning work
  derives for the parity-fold, the controlled/observable-folded construction,
  or the basis-change sandwich MUST be independently, computationally
  verified — via direct operator equivalence or matrix-exponential comparison
  against a small, explicit target unitary — before being written down as an
  accepted decision. No such claim may be stated on the strength of its
  resemblance to a source formula or a previous spec's result alone. This
  mirrors the exact discipline that caught a real sign error in Spec 1 (the
  `PauliEvolutionGate` convention, FR-021) and a real sign error in Spec 2
  (the Trotter coefficient formula, FR-007) — both silent, coefficient-level
  bugs that would not have been caught by end-to-end agreement testing alone.
- The compiler is scoped to a **single** Hermitian Pauli-string observable per
  compilation (Barthe thesis Corollary 5.1 and Figure 5.4's literal
  construction). Extending User Story 2/3 to a weighted **sum** of Pauli
  strings (Barthe thesis §5.7.3's "linear combination of Pauli observables,"
  Figure 5.5) is a real, separate extension — requiring an additional
  ancilla register and post-selection overhead — and is explicitly deferred
  as a `TODO` to a later spec (Constitution §4.7), not silently assumed to be
  either in or out of scope. Note that Spec 1/2's own *validation* oracle
  already accepts arbitrary multi-term `SparsePauliOp` observables (via exact
  `Statevector` evaluation, not this compiler) — that oracle-level capability
  is unaffected by this spec's narrower single-Pauli-string compilation
  scope.
- The probability/projector-observable extension (Barthe thesis Figure 5.6,
  the `U ⊗ U*` construction for measuring `|0><0|`-type observables) is out
  of scope for this spec; only the single Pauli-string observable case
  (Figure 5.4) is addressed here.
- This spec's own validation (FR-012) compares the compiled circuits' exact
  quantum state against Spec 1's existing reference oracle — no new,
  independent notion of ground truth is introduced, and no shot-based/sampled
  extraction is addressed here (that is the scope of a later `extract` layer
  spec, per Constitution §9.1's pipeline order).
- Neither compiler branches on parameter count, qubit count, or observable
  weight (Constitution §9.3); per-parameter and per-gate structure is carried
  as data into the compiled circuit's structure, not as control flow.
