# Feature Specification: Mixed Fixed/Encoded Trotter Frontend

**Feature Branch**: `013-mixed-trotter-frontend`

**Created**: 2026-08-22

**Status**: Draft

**Input**: User description: "Mixed Fixed/Encoded Trotter Frontend. Deliverable: extend the encodings layer with a construction that accepts BOTH FixedGate-style terms (concrete, per-instance-known coupling values — e.g. a graph's own edges) and CouplingGroup-style tied terms (the genuinely unknown, shared encoded parameter(s) — e.g. a field strength), interleaved correctly per Trotter step, producing one PauliEncodedCircuitIR whose `gates` tuple contains both PauliTerm and FixedGate elements — the mixed construction this project's cross-topology regression layer (Spec 12) requires and currently has no way to build. Reuse pauli_pqc.build_ir's existing tie-group-commutativity check and coordinate_order/PauliTerm machinery for the encoded portion; do not duplicate or bypass it. CRITICAL MANDATE: every claim about the fixed-term angle convention and its consistency with trotter_frontend's existing coefficient formula (-weight*tau/(pi*r)) MUST be verified via Operator.equiv against a small worked example BEFORE being accepted — in particular, confirm that calling this new construction with EVERY term marked as encoded reduces EXACTLY to trotter_frontend's existing output on the same input, per this project's standing discipline."

## Clarifications

### Session 2026-08-22 (pre-FR verification, per this project's standing discipline)

This feature's critical mandate was fully discharged, computationally,
*before* this spec was written — not deferred to `/speckit-plan`'s research
phase, and not asserted from the existing `trotter_frontend`/`pauli_pqc`
convention by memory alone.

- **VERIFIED FINDING 1 (isolated fixed-term angle convention)**: a
  prototype construction on a 1-qubit, `r=3`-step, single-fixed-term case
  (`h_known=0.8`, `value_known=1.5`, `tau=1.09`) produced 3 `FixedGate`s,
  each built via `pauli_term.to_gate(spec.value)` where
  `pauli_term.coefficient = -weight*tau/(pi*r)` — the exact same
  coefficient formula `trotter_frontend` already uses for its encoded
  terms, now applied with a concrete, known value in place of a bound
  symbolic parameter. Its `Operator` was compared against an
  INDEPENDENTLY hand-built target: `r` repetitions of Qiskit's native
  `RZGate(2*theta_per_step)`, `theta_per_step = h_known*value_known*tau/r`
  (derived from `RZ(φ)=e^{-iφ/2·Z}`, so `e^{-iθZ}=RZ(2θ)`, entirely outside
  this project's own gate-construction code path). Result: `equiv=True`,
  `diff=2.2887833992611187e-16` — machine precision.
- **VERIFIED FINDING 2 (exact reduction when every term is encoded)**: a
  refined, correctly-interleaved mixed construction was built that (a)
  collects only the encoded groups' uploads, in step-major/caller-declared-
  group order, and passes them through `pauli_pqc.build_ir` completely
  unchanged — reusing its tie-group-commutativity check and
  `coordinate_order`/`PauliTerm` construction exactly — then (b) walks the
  SAME nested `(step, group)` order a second time, interleaving pre-built
  `FixedGate`s for fixed groups with the next already-validated
  `PauliTerm` pulled from `build_ir`'s own output for encoded groups, in
  the caller's declared order. Calling this construction with ZERO fixed
  groups (every term marked "encoded") on a 2-qubit, 2-group (`J`: a tied
  `ZZ` term; `h`: two tied `X` terms), `tau=1.09`, `r=2` example reduces
  EXACTLY to `trotter_frontend`'s own existing output on the identical
  input: the resulting `gates` tuples are structurally identical (Python
  `==` is `True` — the same `PauliTerm` objects, in the same order), and
  `Operator.equiv` on a bound instance (`alpha=[0.6,-0.3]`) gives
  `diff=0.0` exactly.
- **VERIFIED FINDING 3 (genuinely mixed, multi-qubit, correctly
  interleaved)**: using the same refined construction, a 2-qubit example
  was built with ONE encoded `CouplingGroup` (`h`: tied `X(q0)`/`X(q1)`
  terms sharing one parameter `alpha_h`) AND ONE fixed group (a
  `ZZ(q0,q1)` term with known `value=0.8` — e.g. a graph's own known edge
  coupling), `tau=1.09`, `r=2`. The resulting `gates` tuple interleaves
  `PauliTerm`/`PauliTerm`/`FixedGate` per step, in the caller's declared
  order (`['PauliTerm','PauliTerm','FixedGate','PauliTerm','PauliTerm','FixedGate']`
  for `r=2`). Its bound `Operator` (`alpha_h=0.6`) was compared against an
  INDEPENDENTLY hand-built target circuit (`r` repetitions of native
  `RXGate(2*theta_encoded)` on each of `q0`/`q1`, then native
  `RZZGate(2*theta_fixed)` on `(q0,q1)`, with `theta_encoded=-pi*c*alpha_h`
  and `theta_fixed=-pi*c*0.8`, `c=-weight*tau/(pi*r)`): `equiv=True`,
  `diff=1.2412670766236366e-16` — machine precision.
- **Negative result, caught and corrected before being accepted
  (Constitution §8.4)**: the first attempt at Finding 3's comparison
  reported a large `diff` (`1.25`, not machine precision), which on
  inspection was traced entirely to a sign error in the INDEPENDENT
  hand-built verification circuit itself — a spurious extra negation
  when converting the internal `θ` (defined so that the term's gate is
  `e^{-iθP}`) into Qiskit's native `RX`/`RZZ` angle convention (`RX(φ) =
  e^{-iφ/2·X}`, so `φ=2θ`, not `φ=-2θ`). The construction under test was
  never wrong; the hand-built comparison target was. This was caught,
  the comparison circuit corrected, and the check rerun to machine
  precision before this finding was accepted — exactly the standing
  discipline of never trusting a single unverified comparison, applied
  to the verification code itself, not only to the feature under test.
- **Reuse boundary, made explicit**: per the user's own critical mandate,
  `pauli_pqc.build_ir`'s tie-group-commutativity check and
  `coordinate_order`/`PauliTerm` construction machinery are reused
  UNCHANGED for this feature's encoded portion (Finding 2's own
  construction already demonstrates this directly) — this feature MUST
  NOT duplicate or bypass either mechanism (Constitution §9.4).

### Session 2026-08-22 (round 2 — spec gaps identified before planning)

- **Commutativity enforcement was implied by FR-004/User Story 2's reuse
  mandate but not stated as its own directly testable requirement.**
  FR-010 below now states explicitly that the mixed construction MUST
  enforce the tie-group-commutativity check for every parameterized
  (encoded) group — either by delegating to `pauli_pqc.build_ir` (this
  spec's own Findings 2-3 already demonstrate this route) or, only if a
  future implementation constraint forces a different code path, by
  reimplementing `build_ir`'s exact commutativity logic — and that a
  dedicated test MUST confirm an error is raised for a non-commuting
  parameterized group, mirroring FR-004/User Story 2's existing intent
  but now checkable on its own, independent of the reuse-boundary framing.
- **The FixedGate rotation angle formula was stated only as "the same
  coefficient formula" (FR-003) and left the reader to derive the actual
  rotation angle.** FR-011 below writes the exact, fully-derived formula
  into the Functional Requirements directly — the per-step exponent `θ`
  in the fixed term's gate `e^{-iθP}` — so the implementation phase has no
  occasion to re-derive it (correctly or otherwise) from the coefficient
  formula alone.
- **Multi-parameter generalization mandate for `/speckit-plan`'s Phase 0
  research**: this spec's own Clarifications Findings 1-3 verify the
  fixed-term angle convention and the mixed-interleaving logic using AT
  MOST one distinct encoded parameter at a time (Finding 3's mixed case
  has exactly one encoded parameter, `alpha_h`). Before `/speckit-plan`'s
  design may be treated as verified for the general case, Phase 0
  research MUST include an executed `Operator`/`Operator.equiv`
  verification check on a mixed case with AT LEAST TWO distinct encoded
  parameters (in addition to at least one fixed group), confirming the
  interleaving logic generalizes beyond the single-encoded-parameter case
  already checked here — not assumed to follow trivially from Findings
  1-3, and not deferred past the research phase into implementation
  (Assumptions; SC-006).

## User Scenarios & Testing *(mandatory)*

<!--
  As with Specs 1-12, this is an internal pipeline-layer feature for this
  project's own encodings stack (Constitution §9.1's `encodings` stage) —
  "the user" is a developer building a Trotterized circuit that mixes
  concrete, per-instance-known couplings (a graph's own edges) with
  genuinely unknown, shared encoded parameters (a field strength), matching
  this project's established departure from the template's generic framing.
-->

### User Story 1 - Build one IR mixing fixed graph couplings with a shared encoded field parameter (Priority: P1)

A developer has a graph whose edge couplings are concretely known per
instance (e.g. a cross-topology training row's own topology, Spec 12) and
wants to Trotterize a Hamiltonian that ALSO contains a genuinely unknown,
shared field-strength parameter tied across all of its terms — and wants
one `PauliEncodedCircuitIR` whose `gates` tuple correctly interleaves both
kinds of term, per Trotter step, in the order the caller declared its
groups.

**Why this priority**: This is the entire deliverable. Every other
concern (matching `trotter_frontend`'s existing convention, enabling
Spec 12) is meaningless without a construction that actually interleaves
fixed and encoded terms correctly within a single IR.

**Independent Test**: Can be fully tested by declaring a small set of
groups mixing at least one fixed-coupling group and at least one
encoded-parameter group, building the IR, and confirming (a) the `gates`
tuple contains both `PauliTerm` and `FixedGate` elements in the caller's
declared per-step order, and (b) the resulting circuit's `Operator`
matches an independently hand-built target circuit exactly (Clarifications
Finding 3).

**Acceptance Scenarios**:

1. **Given** a caller-declared sequence of groups where some are marked
   fixed (a concrete, per-instance-known value) and some are marked
   encoded (a shared, tied parameter), **When** the mixed IR is built for
   `r` Trotter steps, **Then** the resulting `gates` tuple contains, for
   each of the `r` steps, one gate per declared term in EXACTLY the
   caller's declared group order — fixed terms appearing as `FixedGate`,
   encoded terms appearing as `PauliTerm` — never all fixed terms
   collected before all encoded terms (or vice versa) regardless of the
   caller's declared order.
2. **Given** the same mixed IR, **When** its bound `Operator` is compared
   against an independently hand-built target circuit constructed from
   the same physical coupling values via Qiskit's own native gates (never
   this project's own gate-construction code path), **Then** they are
   exactly equivalent to machine precision (Clarifications Finding 3: 
   `diff=1.24e-16`).

---

### User Story 2 - Reuse `pauli_pqc.build_ir`'s validation for the encoded portion, never duplicate it (Priority: P2)

A developer building the mixed construction wants the encoded portion's
tie-group-commutativity check and `coordinate_order`/`PauliTerm`
construction to come from `pauli_pqc.build_ir` exactly as `trotter_frontend`
already uses it — never a second, parallel implementation of either
mechanism inside this new construction.

**Why this priority**: Depends on User Story 1's construction existing;
ranked second because it is a structural discipline requirement
(Constitution §9.4) rather than new externally-visible capability, but it
is still directly mandated and independently checkable.

**Independent Test**: Can be fully tested by declaring an encoded group
whose terms do NOT commute across the same tie group, and confirming the
mixed construction raises the EXACT SAME error `pauli_pqc.build_ir`'s own
tie-group-commutativity check raises for that case — not a distinct,
locally reimplemented check.

**Acceptance Scenarios**:

1. **Given** an encoded group whose terms fail `pauli_pqc.build_ir`'s
   tie-group-commutativity check on their own, **When** the mixed
   construction is built with that group included, **Then** it raises the
   identical error `pauli_pqc.build_ir` itself raises for that input,
   confirming the encoded portion is actually routed through `build_ir`
   rather than through a duplicated local check.
2. **Given** a mixed construction whose encoded groups use distinct
   parameter labels, **When** the IR is built, **Then** each label maps to
   a `parameter_index` via `pauli_pqc.build_ir`'s own
   `coordinate_order`-based assignment — the same mapping `build_ir` would
   produce if called directly on just those groups' uploads (Clarifications
   Finding 2 already demonstrates this for the all-encoded case).

---

### User Story 3 - Confirm the all-encoded case reduces exactly to `trotter_frontend`'s existing behavior (Priority: P3)

A developer relying on the existing `trotter_frontend` function wants
assurance that adopting the new mixed construction never silently changes
behavior for inputs that use only encoded groups (no fixed groups at
all) — i.e., that the mixed construction is a strict superset of
`trotter_frontend`'s existing capability, not a divergent reimplementation.

**Why this priority**: Ranked last because it is a non-regression
guarantee rather than new capability — but it was the user's own named,
critical mandate, and is independently, directly checkable.

**Independent Test**: Can be fully tested by calling the mixed
construction with zero fixed groups on an input `trotter_frontend` already
accepts, and confirming the resulting IR is exactly (structurally, and via
`Operator.equiv`) `trotter_frontend`'s own output for the same input
(Clarifications Finding 2).

**Acceptance Scenarios**:

1. **Given** a set of encoded-only groups, `tau`, and `r` that
   `trotter_frontend` already accepts, **When** the mixed construction is
   called with the same groups (all marked encoded, zero fixed groups),
   **Then** the resulting IR's `gates` tuple is structurally identical
   (same `PauliTerm` objects, same order) to `trotter_frontend`'s own
   output on the identical input (Clarifications Finding 2: Python `==`
   is `True`).
2. **Given** the same encoded-only input, **When** both IRs' circuits are
   bound to the same parameter values and compared via `Operator.equiv`,
   **Then** the comparison succeeds with `diff=0.0` exactly (Clarifications
   Finding 2) — not merely approximately equivalent.

---

### Edge Cases

- What happens when a caller declares zero fixed groups? User Story 3
  requires this to reduce EXACTLY to `trotter_frontend`'s own existing
  output — this is not an edge case to special-case away but the feature's
  own explicit non-regression guarantee.
- What happens when a caller declares zero encoded groups (every group
  fixed)? The construction MUST still produce a valid IR whose `gates`
  tuple is entirely `FixedGate` elements — `pauli_pqc.build_ir` is simply
  never invoked (there being no encoded uploads to validate), matching
  Finding 1's own isolated-fixed-term verification.
- What happens when the same parameter label is reused across multiple
  encoded groups spanning multiple Trotter steps? This MUST be handled
  identically to how `trotter_frontend` already handles it today (tied
  parameter, one shared `parameter_index`, one tie group per step) — this
  feature changes nothing about that existing behavior for the encoded
  portion.
- What happens when a fixed group's declared value is `0`? This MUST
  still produce a valid `FixedGate` (the identity-equivalent rotation at
  that qubit/Pauli, not a special-cased omission) — a zero coupling is a
  legitimate physical value for a per-instance-known coupling (e.g. a
  genuinely absent graph edge), distinct from Spec 6/Spec 8's
  `ZeroCouplingError` guard, which concerns encoded Hamiltonian *weights*
  being structurally zero, not a per-instance fixed value.
- What happens if a caller declares an empty group sequence, or an `r<=0`,
  or `tau==0`? These MUST be rejected the same way `trotter_frontend`'s own
  `_validate_inputs` already rejects them today — this feature does not
  relax any of `trotter_frontend`'s existing input validation.
- What happens when a fixed group's term count differs from an encoded
  group's term count within the same Trotter step? Each group's own
  declared term count is used independently for interleaving — a group
  with more terms simply contributes more consecutive gates at its
  position in the caller's declared order; there is no requirement that
  fixed and encoded groups declare equal term counts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (Deliverable): The system MUST provide a construction that
  accepts a sequence of groups where each group is EITHER a fixed group
  (one or more Pauli terms sharing a single, concrete, per-instance-known
  coupling value) OR an encoded group (one or more Pauli terms tied to a
  single, genuinely unknown, shared parameter — `trotter_frontend`'s
  existing `CouplingGroup`), and produces one `PauliEncodedCircuitIR`.
- **FR-002** (Correct interleaving): For each of the `r` Trotter steps,
  the resulting `gates` tuple MUST contain one contiguous run of gates per
  declared group, in EXACTLY the caller's declared group order — fixed
  groups contributing `FixedGate` elements, encoded groups contributing
  `PauliTerm` elements — matching `trotter_frontend`'s own existing
  "interleaved, not block-repeated" per-step convention (its module
  docstring), extended to mixed group kinds (Clarifications Finding 3;
  User Story 1).
- **FR-003** (Fixed-term angle convention, verified): A fixed group's
  gate(s) per step MUST be constructed using the SAME coefficient formula
  `trotter_frontend` already uses for encoded terms
  (`coefficient = -weight*tau/(pi*r)`), applied via `PauliTerm.to_gate`
  with the group's own concrete, known value in place of a bound symbolic
  parameter — verified via `Operator.equiv` against an independently
  hand-built target circuit at machine precision (Clarifications Finding
  1: `diff=2.29e-16`; Finding 3: `diff=1.24e-16`), not merely asserted by
  analogy to the encoded case.
- **FR-004** (Reuse boundary, Constitution §9.4, Critical Mandate): The
  encoded portion of the mixed construction MUST route through
  `pauli_pqc.build_ir` completely unchanged — reusing its existing
  tie-group-commutativity check and `coordinate_order`/`PauliTerm`
  construction exactly (Clarifications Finding 2; User Story 2) — and MUST
  NOT duplicate or bypass either mechanism with a second, parallel
  implementation.
- **FR-005** (Exact reduction, Critical Mandate): Calling this
  construction with EVERY group marked encoded (zero fixed groups) on any
  input `trotter_frontend` already accepts MUST reduce EXACTLY to
  `trotter_frontend`'s own existing output on the identical input — both
  structurally (the same `PauliTerm` objects, in the same order) and via
  `Operator.equiv` on a bound instance, with zero deviation (Clarifications
  Finding 2: `diff=0.0` exactly; User Story 3).
- **FR-006**: Calling this construction with EVERY group marked fixed
  (zero encoded groups) MUST produce a valid IR whose `gates` tuple
  consists entirely of `FixedGate` elements, without invoking
  `pauli_pqc.build_ir` at all (there being no encoded uploads to
  validate).
- **FR-007**: The construction MUST reject an empty group sequence,
  `r<=0`, or `tau==0` using the same validation `trotter_frontend`'s own
  `_validate_inputs` already performs today — this feature MUST NOT relax
  any of `trotter_frontend`'s existing input validation for either group
  kind.
- **FR-008**: A fixed group's declared coupling value of exactly `0` MUST
  still produce a valid `FixedGate` (the corresponding identity-equivalent
  rotation), never a special-cased omission or an error — distinct from
  Spec 6/8's `ZeroCouplingError`, which concerns encoded Hamiltonian
  weights being structurally zero, not a per-instance fixed value.
- **FR-009** (Pre-FR verification already performed, Constitution §2.2/
  §4.1): This spec's own three central claims — the fixed-term angle
  convention's correctness in isolation, the exact reduction to
  `trotter_frontend` in the all-encoded case, and the correctness of a
  genuinely mixed, correctly-interleaved multi-qubit case — were verified
  computationally in-session via `Operator`/`Operator.equiv` comparisons
  against independently hand-built target circuits BEFORE this spec was
  written (Clarifications), not asserted from the existing convention by
  analogy or deferred as future work.
- **FR-010** (Explicit commutativity enforcement, Clarifications round 2):
  The mixed construction MUST enforce the tie-group-commutativity check
  (Constitution's own commutativity requirement for any set of terms
  tied to the same encoded parameter within one Trotter step) for EVERY
  parameterized (encoded) group it is given — either by delegating to
  `pauli_pqc.build_ir`'s existing check (this spec's own verified,
  preferred route; FR-004) or, only if a future implementation cannot
  route through `build_ir` for a specific group, by reimplementing
  `build_ir`'s exact commutativity logic rather than a weaker or
  different check. A dedicated test MUST confirm that a parameterized
  group whose terms do not commute across the same tie group causes the
  mixed construction to raise an error — never silently produce an IR
  from a non-commuting tied group.
- **FR-011** (Explicit FixedGate rotation-angle formula, Clarifications
  round 2 — verified, not to be re-derived): A fixed group's term with
  Pauli operator `P`, declared weight `w`, and concrete known value `v`,
  under Trotter step size `tau` and step count `r`, MUST produce a gate
  whose action is EXACTLY `e^{-iθP}` with
  `θ = w · tau · v / r`
  per Trotter step (so that after all `r` steps, the term's cumulative
  action is `e^{-iθ·r·P} = e^{-i·w·tau·v·P}`). This `θ` MUST be obtained,
  not independently re-derived, by calling `PauliTerm.to_gate(v)` on a
  `PauliTerm` whose `coefficient` field is set to
  `c = -w · tau / (pi · r)`
  — the SAME coefficient formula `trotter_frontend` already uses for its
  encoded terms (FR-003), evaluated with the group's concrete value `v` in
  place of a bound symbolic parameter. This formula (and the `θ` it
  produces) was verified via `Operator.equiv` against an independently
  hand-built target circuit at machine precision in both the isolated
  single-fixed-term case (Clarifications Finding 1: `diff=2.29e-16`) and
  the genuinely mixed multi-qubit case (Clarifications Finding 3:
  `diff=1.24e-16`).

### Key Entities *(include if feature involves data)*

- **Fixed group**: One or more Pauli terms sharing a single, concrete,
  per-instance-known coupling value (e.g. a graph's own edge weight) — 
  contributes `FixedGate` elements to the IR (FR-001, FR-003).
- **Encoded group**: `trotter_frontend`'s existing `CouplingGroup` — one or
  more Pauli terms tied to a single, genuinely unknown, shared parameter
  — contributes `PauliTerm` elements to the IR via `pauli_pqc.build_ir`,
  unchanged (FR-004).
- **Mixed `PauliEncodedCircuitIR`**: The single IR this feature produces,
  whose `gates` tuple contains both `PauliTerm` and `FixedGate` elements,
  interleaved per Trotter step in the caller's declared group order
  (FR-002).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can build one `PauliEncodedCircuitIR` from a
  caller-declared sequence mixing fixed and encoded groups, with the
  resulting `gates` tuple correctly interleaving both kinds of term per
  Trotter step in the caller's declared order — verified directly on a
  multi-qubit fixture (Clarifications Finding 3).
- **SC-002**: The fixed-term angle convention this feature introduces is
  confirmed, via `Operator.equiv` against an independently hand-built
  target circuit, to be physically correct to machine precision in both
  an isolated single-fixed-term case (`diff=2.29e-16`) and a genuinely
  mixed multi-qubit case (`diff=1.24e-16`).
- **SC-003**: Calling this feature's construction with every group marked
  encoded reduces EXACTLY to `trotter_frontend`'s own existing output on
  the identical input — verified both structurally (`==` on the `gates`
  tuples) and via `Operator.equiv` (`diff=0.0` exactly) — confirming this
  feature is a strict, non-regressive superset of `trotter_frontend`'s
  existing capability.
- **SC-004**: The encoded portion of this feature's construction is
  verified, by a dedicated test, to raise the identical error
  `pauli_pqc.build_ir`'s own tie-group-commutativity check raises for a
  non-commuting tie group — confirming the encoded portion is actually
  routed through `build_ir`, never a duplicated local check.
- **SC-005**: This spec's own critical mandate — every claim about the
  fixed-term angle convention verified via `Operator.equiv` before being
  accepted, including the caught-and-corrected sign error in the
  verification circuit itself — is documented as an executed,
  already-completed finding (Constitution §8.4), not promised as future
  verification work.
- **SC-006** (Multi-parameter generalization, Clarifications round 2):
  `/speckit-plan`'s Phase 0 research demonstrates, via an executed
  `Operator`/`Operator.equiv` verification check, that the mixed
  construction's interleaving logic and fixed-term angle formula (FR-011)
  remain exact on a case with AT LEAST TWO distinct encoded parameters
  together with at least one fixed group — generalizing this spec's own
  Findings 1-3 (each of which used at most one distinct encoded
  parameter) before the design is treated as verified for the general,
  multi-parameter case.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1) and
  Encodings Layer (Spec 2, `pauli_pqc.build_ir`, `trotter_frontend`) — 
  neither is re-specified here; both are reused, and `trotter_frontend`'s
  own existing public behavior is left entirely unchanged (this feature is
  purely additive).
- **Relationship to Spec 12 (Cross-Topology Regression), motivating but
  not re-specified here**: Spec 12's cross-topology regression layer needs
  training rows whose IRs mix a graph's own known edge couplings (varying
  per topology) with a shared, genuinely unknown encoded parameter
  (constant across topologies) — this is precisely the construction this
  feature provides. This spec does not modify Spec 12's own module or
  requirements; Spec 12 gains the ability to consume this feature's output
  as a new, valid way to build its training rows' IRs, as a separate
  concern from this spec's own scope.
- The specific fixed-group/encoded-group declaration API surface (e.g.
  the exact dataclass name and field layout for a "fixed group" analogous
  to `CouplingGroup`) is a `/speckit-plan`-level decision — this spec
  requires only the behavior FR-001 through FR-011 specify.
- **`/speckit-plan`'s own required Phase 0 multi-parameter verification
  mandate (Clarifications round 2, Critical Mandate)**: Phase 0 research
  MUST include an executed `Operator`/`Operator.equiv` verification check
  on a mixed case with at least two distinct encoded parameters plus at
  least one fixed group (SC-006) — this spec's own Clarifications
  Findings 1-3 verify only single-encoded-parameter cases, and that MUST
  NOT be treated as sufficient evidence that the interleaving logic or
  the FR-011 angle formula generalize to multiple simultaneous encoded
  parameters without this additional, explicit check.
- Scoped to Pauli-string terms only, matching `trotter_frontend`'s and
  `pauli_pqc.build_ir`'s existing scope — no new gate types beyond what
  `PauliTerm.to_gate` and `FixedGate` already support.
- This feature's verification (Clarifications) used `Operator`/
  `Operator.equiv` on small, exactly-representable fixtures (1-2 qubits);
  no claim is made here about circuit-construction performance at the
  larger qubit counts other specs' baselines use — that remains a
  separate, unscoped concern.
