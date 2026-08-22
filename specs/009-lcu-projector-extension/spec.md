# Feature Specification: LCU and Projector-Observable Extension for FCE

**Feature Branch**: `009-lcu-projector-extension`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "LCU (Linear Combination of Unitaries) and Projector-Observable Extension for FCE (Spec 9). Deliverables: (a) Extend Spec 3's observable-folding compiler (compile_observable_circuit) to accept a weighted sum of polynomially many Pauli strings, O = Sum_h beta_h P_h, via a genuine LCU construction (Barthe thesis Appendix 5.7.3, eq. 5.49-5.51, Figure 5.5, verified in-session): a shared A(U) forward/A(U-dagger) inverse pair (run ONCE, not once per term), with an additional LCU selector register of ceil(log(#terms)) qubits preparing V_beta|0> = (1/||beta||) Sum_h beta_h|h>, a MULTIPLEXED controlled-P_h gate (controlled on the selector register's basis state |h>) inserted at the exact position the single observable-fold gate occupies today, then V_beta-dagger, with post-selection on BOTH the existing frequency-extraction ancilla AND the new selector register landing in |0>. (b) Extend the same compiler to support the probability/projector observable |0><0| (i.e., the probability of the original circuit's own |0> outcome) via the (U tensor U*) construction (Barthe thesis eq. 5.52, Figure 5.6, verified in-session) -- running A(U) on one register and a second, independently-constructed A(U*) (the complex-conjugate circuit) on a parallel register, then reading out the joint amplitude. CRITICAL MANDATES: 1. Reuse, do not duplicate. 2. Verification (Constitution §4.1/§5.2) deferred to /speckit.plan. 3. Honest scope (Constitution §10.3): post-selection overhead reported separately. 4. Extension Register (Constitution §2.3): both deliverables formally tracked. CORRECTION TO FLAG: the thesis construction runs A(U)/A(U-dagger) exactly once, shared across all terms — not once per term."

## Clarifications

### Session 2026-08-21 (`/speckit-clarify`)

- **Critical mathematical correction to FR-003, independently re-derived
  and numerically confirmed before applying (diff ≈1e-16 for the corrected
  formula vs. ≈0.2 for the original, on a random 2-term worked example)**:
  the standard LCU post-selection mechanism — prepare the selector into
  `Σ_h c_h|h⟩`, apply the multiplexed `P_h`, un-prepare with the adjoint,
  and post-select the selector on `|0⟩` — produces a state proportional to
  `Σ_h |c_h|² P_h`, **never** `Σ_h c_h P_h` directly (the post-selection
  amplitude is quadratic in the preparation amplitude, not linear). FR-003
  as originally drafted transcribed eq. 5.51 literally
  (`c_h = β_h/‖β‖`), which would make the recovered combination
  quadratic in `β_h` — wrong. The corrected requirement (below) states the
  precise amplitude the mechanism actually needs: `c_h = √(β_h/S)` with
  `S = Σ_h|β_h|` (the L1 norm), so that `|c_h|² = β_h/S` and
  post-selection recovers `(1/S)·Σ_h β_h P_h` — linear in `β_h`, as
  required. This is a necessary precise elaboration of eq. 5.51's own
  shorthand, not a claim that the thesis is wrong about anything it
  states explicitly (Constitution §2.2) — eq. 5.51 does not itself spell
  out the amplitude-vs-probability relationship the mechanism depends on.
- **A required non-degenerate verification fixture, added to Assumptions**:
  FR-011 already requires `/speckit-plan` to verify the LCU construction
  computationally; this session adds that the fixture used MUST have
  highly asymmetric weights (e.g. `β_1=1, β_2=4`), because an equal-weight
  fixture would silently mask exactly this error — with `β_1=β_2`, both
  the correct (`√`) and incorrect (linear) formulas preserve the same
  1:1 ratio between terms and differ only by an overall scale factor,
  which a test that does not check exact magnitude could pass either way.
- **A missing architectural cost in FR-008, added**: the `U⊗U*`
  projector construction requires **two independent** forward frequency-
  counting registers (one for `A(U)`, one for `A(U*)`) — not a single
  shared or difference register — doubling the total frequency-register
  qubit budget relative to a single-observable extraction. This cost MUST
  be predicted and logged before being paid (Constitution §10.3), matching
  this project's existing discipline (e.g. `reference.py`'s
  `predict_grid_cost`).

### Session 2026-08-21 (drafted during `/speckit-specify`, not a `/speckit-clarify` session)

- **Correction, verified in-session against `docs/references/Barthe_thesis.pdf` pages
  144–145 (Figure 5.5)**: the request's phrase "each term's controlled-A(U,P_h)"
  would, read literally, repeat the entire frequency-counting forward/inverse
  pass `A(U)`/`A(U†)` once per Pauli term `h` — needlessly expensive, and not
  what the thesis depicts. The verified construction runs `A(U)` and `A(U†)`
  **exactly once each**, shared across every term; only the single
  observable-fold gate `P` in the existing construction (Figure 5.4) is
  replaced by one **multiplexed**, selector-controlled `P_h` gate. This
  spec's FRs reflect the corrected, cheaper construction throughout.
- **A second fact, verified in-session while grounding deliverable (b)**: the
  projector `|0⟩⟨0|` is *not* a special case of deliverable (a)'s
  weighted-Pauli-sum machinery, even though it could in principle be written
  as `O = (1/2^n) Σ_{P∈{I,Z}^n} P`. That decomposition has `2^n` terms —
  exponential, not polynomial — so deliverable (a)'s LCU construction
  (built for "polynomially many terms," per its own thesis source) is the
  wrong tool for it. This is exactly why the thesis gives the projector its
  own, separate `U⊗U*` construction (eq. 5.52, Figure 5.6), which never
  decomposes the projector into Pauli strings at all. Deliverable (b) is
  therefore a genuinely distinct capability, not a special input to
  deliverable (a)'s.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature activates EXT-001 (LCU, already registered as "deferred —
  scheduled after Z₂ LGT validation," now complete per Spec 8) and adds a
  new, previously-unregistered extension for the projector construction.
  Both deliverables extend Spec 3's `compile_observable_circuit` — the one
  place in this codebase a caller-supplied observable is folded into the
  Fourier-coefficient-extraction circuit — rather than adding a parallel
  compiler.
-->

### User Story 1 - Extract Fourier coefficients of a weighted sum of Pauli observables (Priority: P1)

A developer has an observable that is a genuine linear combination of
several Pauli strings, `O = Σ_h β_h P_h` (not just one), and wants the
existing Fourier-coefficient-extraction pipeline to handle it directly —
producing the same frequency-domain result Barthe's algorithm already
gives for a single Pauli string, but for the full weighted sum, via one
shared frequency-counting pass rather than one full pass per term.

**Why this priority**: This is the foundational deliverable and the one
already registered as a scheduled extension (EXT-001). It unblocks a
whole class of physically meaningful observables (e.g. a Hamiltonian's
own multi-term expectation value) that today can only be measured one
Pauli string at a time, with no way to combine them into a single
Fourier-coefficient set through this codebase's own machinery.

**Independent Test**: Can be fully tested by declaring a small, explicit
weighted sum of 2–4 Pauli strings, running it through the extended
compiler, and confirming the extracted Fourier coefficients agree with
what would be obtained by extracting each term separately and combining
them classically by linearity (the same identity the construction itself
relies on, eq. 5.50) — on a small instance where both routes are
tractable to compute directly.

**Acceptance Scenarios**:

1. **Given** an observable declared as more than one Pauli string with
   explicit real weights, `O = Σ_h β_h P_h`, **When** the extended
   compiler folds it into the circuit, **Then** the frequency-counting
   forward pass `A(U)` and its inverse `A(U†)` each appear **exactly
   once** in the resulting circuit — never once per term `h` (the
   corrected construction, Clarifications above).
2. **Given** the same declaration, **When** the compiler builds the
   observable-fold stage, **Then** it prepares an additional selector
   register of `⌈log(#terms)⌉` qubits into `V_β|0⟩ = (1/‖β‖)Σ_h β_h|h⟩`
   (eq. 5.51), applies one multiplexed gate that applies `P_h` to the
   circuit register precisely when the selector register holds `|h⟩`,
   and un-prepares the selector register with `V_β†` — never a separate,
   independently-synthesized circuit per term.
3. **Given** an observable declared with exactly **one** Pauli string
   (the case Spec 3 already supports), **When** it is passed through the
   extended compiler, **Then** the resulting circuit is byte-for-byte
   identical to what Spec 3's existing, unmodified single-Pauli path
   already produces — the generalization changes nothing for the case
   that already worked (Critical Mandate 1).
4. **Given** the extended construction, **When** its Fourier-coefficient
   extraction result is reported, **Then** the report states the
   selector register's own post-selection success probability as an
   explicit, separate figure from the pre-existing frequency-extraction
   ancilla's own success probability — never blended into one combined
   number that hides which stage is responsible for how much overhead
   (Constitution §10.3).

---

### User Story 2 - Extract the probability of the original circuit's own |0⟩ outcome (Priority: P2)

A developer wants to know `P(0) = |⟨0|U|0⟩|²`, the probability that the
*original* (unmodified, unfolded) circuit `U` — with no explicit
observable at all — returns the all-zeros outcome, as a function of the
encoded classical input, via this codebase's own Fourier-coefficient
machinery.

**Why this priority**: Depends on nothing from User Story 1 (a genuinely
separate construction, Clarifications above) but is ranked second because
it answers a narrower, more specific question (one fixed outcome
probability) than User Story 1's general weighted-observable capability.
It is still a distinct, independently valuable deliverable, not optional
polish: without it, there is no way to ask this codebase for a
measurement-outcome probability at all — every existing capability
answers a Pauli-*observable* expectation value, never a projector.

**Independent Test**: Can be fully tested by declaring a small circuit
`U`, running the projector construction to extract its Fourier
coefficients, and confirming the result agrees with directly computing
`|⟨0|U(α)|0⟩|²`'s own Fourier series on a small instance where both are
independently computable.

**Acceptance Scenarios**:

1. **Given** a circuit `U` with no explicit Pauli observable declared,
   **When** the projector construction is invoked, **Then** the system
   builds a second, independently-constructed circuit representing `U*`
   (the complex-conjugate circuit, eq. 5.52) and runs the frequency-
   counting construction on the joint `U ⊗ U*` action on `|0⟩⊗|0⟩` —
   never by attempting to express `|0⟩⟨0|` as a Pauli-string sum first
   (Clarifications: that decomposition is exponential, the wrong tool).
2. **Given** the joint construction, **When** its result is reported,
   **Then** the report explicitly labels which stage of the construction
   the frequency spectrum belongs to — the joint `U ⊗ U*` amplitude
   (eq. 5.52), not a Pauli-observable expectation value — so the two
   deliverables' outputs are never presented as interchangeable.

---

### Edge Cases

- What happens when an observable declared for User Story 1 has only one
  term? Acceptance Scenario 3 above requires this reduces exactly to
  Spec 3's existing, unmodified behavior — not a degenerate LCU
  construction with a zero-qubit selector register that happens to work,
  but the literal existing code path.
- What happens when an observable declared for User Story 1 is not
  Hermitian (so it has no well-defined real expectation value)? Rejected
  explicitly, consistent with Spec 4's existing Hermiticity precondition
  on `extract_coefficients` (Constitution §7.6) — this feature does not
  relax that requirement.
- What happens when the number of terms in a User Story 1 observable is
  not a power of two (so the selector register has "unused" basis
  states)? The unused selector states must never contribute a spurious
  post-selection success — this is a required, explicitly tested
  behavior, not an assumed consequence of the construction.
- What happens if a Pauli string in a User Story 1 observable contains an
  odd number of `Y` factors, for User Story 2's separate `U*` construction
  (a circuit containing such a term is a legitimate input to User Story
  1, independently of User Story 2)? The two deliverables are independent
  constructions; an odd-`Y` term affects only how `U*` would need to be
  built (User Story 2), which is a `/speckit-plan`-level verification
  question (Assumptions), not a User Story 1 concern at all.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (Deliverable a): The system MUST accept, as the observable
  input to the Fourier-coefficient-extraction pipeline, a weighted sum of
  more than one Pauli string, `O = Σ_h β_h P_h` — generalizing, not
  replacing, the existing single-Pauli-string input.
- **FR-002**: The system MUST fold a multi-term observable into the
  circuit via the corrected construction (Clarifications): the existing
  frequency-counting forward pass `A(U)` and its inverse `A(U†)` each
  appear exactly once, with a single multiplexed, selector-controlled
  `P_h` gate inserted at the position the existing single-observable fold
  gate occupies — never a separate `A(U)`/`A(U†)` pair per term.
- **FR-003** (**revised, Clarifications 2026-08-21 — the Square Root
  Trap**): The system MUST prepare a selector register of
  `⌈log(#terms)⌉` qubits into
  `V_β|0⟩ = Σ_h √(β_h / S) |h⟩`, where `S = Σ_h |β_h|` is the **L1 norm**
  of the weights (never the L2/Euclidean norm `‖β‖`) — **not**
  `Σ_h (β_h/S)|h⟩` as a literal reading of eq. 5.51 would suggest. This
  precise amplitude is load-bearing: the standard post-selection
  mechanism (prepare, apply the multiplexed fold, un-prepare, post-select
  the selector on `|0⟩`) yields a result proportional to the *squared*
  preparation amplitude, `Σ_h |c_h|² P_h`; only `c_h = √(β_h/S)` makes
  `|c_h|² = β_h/S`, recovering `(1/S)·Σ_h β_h P_h` — linear in `β_h`, the
  actually-desired combination. A preparation using `c_h = β_h/S`
  directly would recover a combination quadratic in `β_h` instead — a
  silent, wrong result the system MUST NOT produce. The selector is
  un-prepared with `V_β†` afterward, as originally stated.
- **FR-004** (**Reuse, not duplication**, Critical Mandate 1): An
  observable containing exactly one Pauli string, passed through this
  feature's generalized compiler, MUST produce a circuit identical to
  Spec 3's existing, unmodified `compile_observable_circuit` output for
  that same term — verified directly (e.g. `Operator.equiv` or an exact
  gate-sequence comparison), not merely argued.
- **FR-005** (**Honest scope**, Critical Mandate 3, Constitution §10.3):
  Every reported extraction using this feature's multi-term construction
  MUST state the selector register's own post-selection success
  probability as a figure explicitly separate from the pre-existing
  frequency-extraction ancilla's own success probability — the two MUST
  NOT be blended, averaged, or reported as one combined number.
- **FR-006**: The system MUST reject a non-Hermitian multi-term
  observable with the same explicit precondition check Spec 4's
  `extract_coefficients` already applies to a single-term observable
  (Constitution §7.6) — not a relaxed or separately-implemented check.
- **FR-007**: For a declared term count that is not an exact power of
  two, the system MUST ensure the selector register's unused basis
  states never contribute a spurious post-selection success (Edge Cases).
- **FR-008** (Deliverable b, **revised, Clarifications 2026-08-21 —
  Register Doubling Cost**): The system MUST support extracting the
  Fourier coefficients of the projector observable `|0⟩⟨0|` — the
  probability of the original circuit `U`'s own `|0⟩` outcome — via the
  `U ⊗ U*` construction (eq. 5.52, Figure 5.6), operating on the original
  circuit `U` and an independently-constructed conjugate circuit `U*`,
  never by attempting a Pauli-string decomposition of the projector
  (Clarifications: that decomposition is exponential). This construction
  requires **two independent forward frequency-counting registers** — one
  for `A(U)`'s own construction, one for `A(U*)`'s — never a single
  shared or difference register standing in for both; the total
  frequency-register qubit budget is therefore double what a single-
  observable extraction (deliverable a, or Spec 3's existing single-Pauli
  path) requires for the same circuit. This doubled cost MUST be
  predicted and logged explicitly before it is paid (Constitution
  §10.3), matching this project's existing discipline (e.g.
  `reference.py`'s `predict_grid_cost`).
- **FR-009**: The system MUST report the projector construction's result
  labeled explicitly as a joint `U ⊗ U*` amplitude (eq. 5.52) — distinct
  from, and never presented as interchangeable with, a Pauli-observable
  expectation value from deliverable (a).
- **FR-010** (**Extension Register**, Critical Mandate 4, Constitution
  §2.3): This feature MUST update `.specify/memory/extension-register.md`:
  EXT-001's validation status MUST be updated from "deferred — scheduled
  after Z₂ LGT validation" to reflect that its scheduled implementation
  is now underway/complete, and a **new** register entry MUST be added
  for the `U⊗U*` projector construction (eq. 5.52, Figure 5.6), which has
  no existing entry.
- **FR-011** (**Verification deferred to `/speckit-plan`**, Critical
  Mandate 2, Constitution §4.1/§5.2): Every claim this feature's
  `/speckit-plan` phase makes about the LCU construction's post-selection
  probability, selector register size, or success amplitude, and about
  how `U*` is built for this codebase's own real-coefficient
  Pauli-rotation gate library, MUST be verified computationally (e.g.
  `Operator.equiv`, or explicit amplitude calculation against a small
  worked example) before being accepted as a design decision — this spec
  requires the verification to happen, not any specific claimed formula.

### Key Entities *(include if feature involves data)*

- **Weighted Pauli-sum observable**: `O = Σ_h β_h P_h` — a caller-declared
  set of Pauli strings and real weights, Hermitian as a whole (FR-006),
  replacing the single-Pauli-string observable Spec 3/4 accept today as
  this feature's generalized input.
- **Selector register**: The `⌈log(#terms)⌉`-qubit register prepared into
  `V_β|0⟩` and later post-selected on `|0⟩` — the LCU construction's own
  bookkeeping structure, additive to the circuit's existing registers,
  never replacing any of them.
- **Projector construction result**: The joint `U⊗U*` amplitude output
  (FR-008/FR-009) — a structurally distinct entity from a Pauli-
  observable's extracted Fourier-coefficient set, even though both are
  ultimately reported as frequency-indexed coefficients.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can declare a weighted sum of several Pauli
  strings and extract its Fourier coefficients through this codebase's
  existing pipeline, with the result agreeing with the classical, per-term
  linear combination on a small, independently-checkable instance.
- **SC-002**: The generalized compiler produces byte-for-byte the same
  circuit Spec 3 already produces today for every existing single-Pauli-
  string case — zero regressions in previously-passing behavior.
- **SC-003**: Every result produced by the multi-term construction states
  the selector register's post-selection success probability as its own,
  separately-labeled figure — audited by that figure being a required,
  distinct field of the result, never optional or merged prose.
- **SC-004**: A developer can extract the Fourier coefficients of the
  probability of the original circuit's own `|0⟩` outcome, with the
  result agreeing with a direct, independent computation of
  `|⟨0|U(α)|0⟩|²`'s Fourier series on a small instance.
- **SC-005**: `.specify/memory/extension-register.md` records both
  deliverables — EXT-001 updated, and a new entry added for the
  projector construction — before this feature's implementation is
  considered complete.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1),
  Encodings Layer (Spec 2), Circuits Layer (Spec 3: `compile_frequency_circuit`,
  `compile_observable_circuit`, reused and extended, never duplicated),
  and Extract Layer (Spec 4: `extract_coefficients`'s Hermiticity
  precondition, reused unchanged for the generalized observable). Specs
  5–8 are not touched by this feature.
- **Primary source**: `docs/references/Barthe_thesis.pdf` (verified
  in-session, pages 144–145) — eq. 5.44–5.48 (the existing single-Pauli
  construction, Figure 5.4, already implemented), eq. 5.49–5.51 and
  Figure 5.5 (the LCU construction, deliverable a), and eq. 5.52 and
  Figure 5.6 (the projector construction, deliverable b).
- **`SparsePauliOp` already natively represents a multi-term weighted
  sum.** Qiskit's own `SparsePauliOp` type already supports more than one
  Pauli string with individual coefficients (used elsewhere in this
  project, e.g. for LCU-context error handling in Spec 7's
  `MultiTermPauliError`). This feature's FR-001 is about *accepting and
  correctly folding* such an observable through the circuit-compilation
  pipeline — not about inventing a new representation for it.
- **How to construct `U*` for this codebase's own gate library is an open
  verification question, deliberately left to `/speckit-plan` (FR-011).**
  A Pauli string with an even number of `Y` factors has a real matrix
  representation (so `U*`'s corresponding gate is plausibly obtained by
  negating the encoded angle); a string with an odd number of `Y` factors
  does not, and needs its own verified construction. This spec requires
  only that the eventual construction is verified computationally for
  both cases before being relied upon, not that either case's mechanism
  is decided here.
- **The exact multiplexed-gate synthesis strategy for the selector-
  controlled `P_h` (FR-002/FR-003) is a `/speckit-plan`-level decision** —
  this spec requires only that it is a single, shared construction (not
  one per term) and that it is verified equivalent to the direct,
  unfolded linear combination on a small instance (FR-004, User Story 1's
  own Independent Test).
- **Non-degenerate verification mandate (Clarifications 2026-08-21)**:
  the `/speckit-plan` verification fixture FR-011 already requires MUST
  use highly asymmetric weights (e.g. `β_1=1, β_2=4`), never equal
  weights — an equal-weight fixture (`β_1=β_2`) cannot distinguish the
  correct preparation amplitude (`c_h=√(β_h/S)`, FR-003) from the
  incorrect one (`c_h=β_h/S`), since both give the same 1:1 ratio between
  terms and differ only in overall scale, which a test that does not
  check exact magnitude could pass under either formula. The
  verification MUST explicitly demonstrate the post-selected amplitude is
  linear in `β_h`, not quadratic, on a fixture where the two hypotheses
  produce genuinely different relative proportions between terms.
- This feature validates against small, explicit, hand-constructed
  multi-term observables and circuits (2–4 Pauli terms; a handful of
  qubits) — no production-scale observable or circuit is targeted here.
