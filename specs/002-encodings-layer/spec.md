# Feature Specification: Encodings Layer

**Feature Branch**: `002-encodings-layer`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Encodings layer for FCE. Deliverables: (a) A Pauli-PQC frontend that accepts a list of Pauli strings and lowers them into the PauliEncodedCircuitIR. (b) A Trotter frontend (first-order) that accepts a Pauli operator and evolution time, lowering to the same IR. (c) Validation tests ensuring both frontends execute against the Foundation Layer's integer-indexed oracle. CRITICAL REQUIREMENT (per Web Claude): The validation tests for BOTH frontends MUST use circuit constructions that produce genuinely complex coefficients (nonzero real and imaginary parts). A test where both frontends happen to produce purely real coefficients would pass while hiding a coeff_per_param scaling error. This must be explicitly guarded against in the spec to enforce Constitution §6.4 and §4.3."

## Clarifications

### Session 2026-08-20

- Q: Does the Foundation Layer's IR enforce that all terms sharing one encoded
  parameter (a tie group, and every repeated upload of that parameter) use the
  exact same coefficient, or could the Trotter frontend rely on heterogeneous
  tied coefficients? → A: It did not — this was a latent, unvalidated gap in Spec 1
  (every one of its own tests used `coefficient=1.0`). Verified numerically that
  heterogeneous coefficients alias the extracted spectrum. Spec 1 is amended (its
  FR-007) to require and enforce coefficient uniformity across every term of one
  parameter, rejecting heterogeneous constructions at IR-construction time.
- Q: Should Spec 1's reference oracle also be fixed now to correctly support
  non-unit coefficients (which the Trotter frontend's `c_k = -h_k/(πL)` formula
  requires in general), or should that fix be deferred past this spec? → A: Fixed
  now. Verified that the oracle's fixed-length grid domain silently aliases any
  non-unit coefficient, even an untied, single-term one; the fix (rescaling the
  domain by `1/coefficient` per parameter) is now in Spec 1 (its FR-022). Without
  it, this spec's own Trotter frontend could not be validated against correct
  ground truth at all.
- Q: Should the Trotter frontend produce a multi-dimensional IR (one encoded
  parameter per distinct Hamiltonian coupling constant) to handle realistic,
  multi-coupling-constant Hamiltonians, or should this spec instead restrict the
  Trotter frontend to Hamiltonians where every tied term shares one coupling
  constant, keeping a single-time-parameter IR? → A: Multi-dimensional IR, one
  parameter per distinct coupling constant. Terms sharing the exact same coupling
  constant may still be tied together (their derived coefficients are then equal,
  satisfying Spec 1's uniformity requirement); terms with different coupling
  constants get separate parameters and must not be tied. Reconstructing a single
  physical evolution-time Fourier series from this multi-dimensional output is out
  of scope for this spec (Constitution §6.4 — that reconstruction belongs to a
  later interpretation layer, not the Trotter frontend itself).
- **Paradigm shift** (superseding the "evolution time is the encoded parameter"
  framing above): a deeper architectural review determined the Trotter frontend had
  the wrong quantity playing the role of "encoded parameter" altogether. → The
  encoded (unknown, extracted) parameters are the Hamiltonian's **coupling
  constants** (e.g. `J`, `m`, `f`) — not evolution time. Evolution time `τ` and the
  Trotter step count `r` are both **fixed, known classical arguments** the caller
  supplies before any circuit is built, exactly like the step count already was;
  neither is swept or extracted. Callers designate **groups** of Hamiltonian Pauli
  terms that share one unknown coupling (e.g., the hopping term's `A_e` and `B_e`
  both scale with `J`). Because grouping is *by shared coupling*, and every term in
  a group carries the same fixed structural weight within it, the derived
  per-term coefficient is identical across the group — the Foundation Layer's
  tie-group coefficient-uniformity invariant (Spec 1 FR-007) is satisfied by
  construction, not by a separate rejection rule bolted on afterward. The exact
  formula is `c = -h·τ/(π·r)` (verified in-session against the actual target
  unitary, not assumed — see FR-007). This also **eliminates** the earlier
  "reconstruction is out of scope" caveat: each encoded parameter now directly *is*
  a physical coupling constant, so there is no multi-dimensional-to-1-D
  reconstruction step to defer at all. Every acceptance scenario, FR, and
  Assumption below reflects this corrected framing; the two entries above are kept
  for their still-valid findings (coefficient uniformity, oracle domain rescaling)
  but their "evolution time is the parameter" framing is superseded.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature's "users" are the developers who build encoded feature maps on top
  of the Foundation Layer (Spec 1). The Foundation Layer defines the shared IR and
  its typed `Encoding` boundary but ships no concrete encoding; this layer is the
  first thing that actually produces a usable, physically meaningful circuit
  description from a higher-level, domain-familiar description (a list of Pauli
  strings, or a Hamiltonian and an evolution time) rather than requiring every
  caller to hand-build IR internals directly.
-->

### User Story 1 - Build a feature map from a list of Pauli strings (Priority: P1)

A developer who has a Pauli-encoded ansatz in mind — expressed the way the
literature expresses it, as an ordered list of Pauli strings, each tied to one of
several encoded parameters, with some strings possibly tied together (summed as one
generator driving a single parameter, per the equivariant construction) — needs to
turn that description into a Foundation-Layer IR instance without hand-writing the
IR's internal bookkeeping (upload counts, multiplicity, tie groups) themselves.

**Why this priority**: This is the more general and more primitive of the two
frontends — it can express any Pauli-encoded circuit the Foundation Layer's IR is
capable of representing, including the tied, multiplicity-`r_j` structures the
equivariant research programme depends on. The Trotter frontend (User Story 2) is a
convenience layer built on top of this one's IR-construction logic, not the other
way around.

**Independent Test**: Can be fully tested by supplying a small, explicit list of
Pauli strings (including at least one case where two strings are tied to the same
parameter) and confirming the resulting IR instance's per-parameter upload count,
multiplicity, and coefficients match what was supplied — independent of any
Hamiltonian or evolution-time concept.

**Acceptance Scenarios**:

1. **Given** a list of Pauli strings where each is tied to its own distinct
   parameter, **When** the frontend lowers it, **Then** the resulting IR has one
   upload per parameter, in the supplied order, with the supplied structural
   coefficients.
2. **Given** a list where two Pauli strings are tied to the same parameter within
   one upload (multiplicity `r_j = 2`), **When** the frontend lowers it, **Then**
   the resulting IR reports that parameter's multiplicity as 2 and does not allow
   the two strings to be treated as independent parameters.
3. **Given** a list where the same parameter is uploaded more than once (repeated,
   untied applications), **When** the frontend lowers it, **Then** the resulting
   IR's upload count for that parameter reflects the number of repetitions.
4. **Given** an empty list of Pauli strings, **When** the frontend is asked to
   lower it, **Then** it raises rather than returning a circuit with no encoded
   parameters and no indication anything is wrong.

---

### User Story 2 - Build a feature map for an unknown Hamiltonian coupling, at a fixed evolution time and Trotter depth (Priority: P2)

A developer wants to learn one or more of a Hamiltonian's own coupling constants
(e.g. a hopping strength `J`, a mass `m`, an electric coupling `f`) via Fourier
extraction. Evolution time and Trotter step count are experimental knobs they
already control and choose classically — they are not what's being learned. They
need to turn "evolve under this Hamiltonian for this long, in this many first-order
Trotter steps, treating this coupling as unknown" into a Foundation-Layer IR
instance, designating which Hamiltonian terms share which unknown coupling, without
manually working out each term's per-step rotation angle themselves.

**Why this priority**: Builds directly on User Story 1 — a Trotterized circuit is,
structurally, a list of Pauli strings (one per Hamiltonian term per Trotter step)
with a specific, mechanical rule for each string's coefficient and parameter
assignment. This story's value is removing the manual Hamiltonian-to-Pauli-string-
list translation and the per-step coefficient arithmetic from the developer, not
introducing new IR capability.

**Why this priority is P2, not P1**: this frontend is a convenience wrapper —
without User Story 1's lowering logic to delegate to, this story would still need
to reimplement the same IR-construction rules from scratch, duplicating a call
path (Constitution §9.4).

**Why the encoded parameter is the coupling, not evolution time** (superseding an
earlier draft of this story): evolution time and Trotter step count are properties
of *how the experiment is run*, chosen and known by the experimenter — Constitution
§7.1's "classical input... selects fixed gates." What's physically unknown, and
what Fourier extraction is for, is the Hamiltonian's own coupling strength. Framing
time as the encoded parameter was a mistake corrected in this session: it required
one encoded parameter per distinct coupling *anyway* (since each term's angle scales
by its own coupling), forcing a multi-dimensional-output-to-1-D-time reconstruction
this feature never actually needed to perform. Framing the couplings themselves as
the encoded parameters removes that reconstruction step entirely — each output
parameter already *is* the physically meaningful quantity.

**Independent Test**: Can be fully tested by supplying a small Hamiltonian, a
grouping of its Pauli terms by shared unknown coupling (at least one group with two
terms, to exercise tying), a fixed evolution time, and a fixed Trotter step count,
then confirming the resulting IR gives each coupling group its own parameter with
the correct per-term coefficient (`c = -h·τ/(π·r)`) and the correct upload count
(the step count itself).

**Acceptance Scenarios**:

1. **Given** a Hamiltonian with two coupling groups (each a set of Pauli terms
   sharing one unknown coupling), a fixed evolution time `τ`, and a fixed Trotter
   step count `r`, **When** the frontend lowers it, **Then** the resulting IR has
   two separate encoded parameters, one per coupling group, each with upload count
   `r`.
2. **Given** a coupling group with two Pauli terms that share the same fixed
   structural weight `h` within that group, **When** the frontend lowers it,
   **Then** both terms are tied to that group's one encoded parameter (multiplicity
   2), each with the identical coefficient `c = -h·τ/(π·r)` — satisfying the
   Foundation Layer's per-parameter uniformity requirement by construction, not by
   a separate check bolted on afterward.
3. **Given** the same Hamiltonian with a larger fixed Trotter step count `r`,
   **When** the frontend lowers it, **Then** each parameter's upload count equals
   `r`, and each term's coefficient is scaled accordingly
   (`c = -h·τ/(π·r)`) so the accumulated rotation over all `r` steps corresponds to
   evolving under that coupling for the fixed time `τ`.
4. **Given** a fixed Trotter step count of zero or negative, **When** the frontend
   is asked to lower the Hamiltonian, **Then** it raises rather than returning a
   circuit with no meaningful evolution.
5. **Given** a fixed evolution time of exactly zero, **When** the frontend is asked
   to lower the Hamiltonian, **Then** it raises — every derived coefficient would be
   exactly zero, which the Foundation Layer's IR itself rejects, and a zero
   evolution time carries no information about any coupling to extract in the first
   place.
6. **Given** a Hamiltonian with zero terms, or no coupling groups declared at all,
   **When** the frontend is asked to lower it, **Then** it raises rather than
   returning a circuit with no encoded parameter.

---

### User Story 3 - Validate both frontends against exact ground truth, with a test that could actually fail (Priority: P3)

A developer who has built either frontend needs proof that the circuits it
produces are not just structurally valid IR objects but *physically correct* —
that running the lowered IR through the Foundation Layer's oracle reproduces the
Fourier coefficients the construction is analytically known to have — and needs
that proof to be incapable of passing on an implementation that silently applies
the wrong per-term coefficient scaling.

**Why this priority**: Depends on both prior stories existing (there is nothing to
validate before a frontend produces an IR), but is not optional polish: Constitution
§4.1 treats a component with no passing oracle test as not done "however well it
runs," and §4.3 requires every agreement test to assert the tested quantity is
non-trivial. A validation suite built from circuits whose coefficients happen to
come out purely real would satisfy every other check while leaving exactly the
defect this feature is most at risk of — an incorrect per-upload coefficient scale,
Constitution §6.4's "per-parameter scaling" concern — completely unexercised.

**Independent Test**: Can be fully tested standalone: take each frontend's own
validation circuit, lower it, run it through the Foundation Layer's oracle, and
confirm the returned coefficients match hand-derived (or independently,
numerically pre-verified) analytic values — including, for each frontend
separately, at least one non-DC coefficient with both a nonzero real part and a
nonzero imaginary part.

**Acceptance Scenarios**:

1. **Given** a Pauli-PQC-frontend-lowered circuit whose Fourier coefficients are
   known analytically to include at least one coefficient with nonzero real and
   imaginary parts, **When** the Foundation Layer's oracle evaluates it, **Then**
   the returned coefficients match the analytic values to floating-point
   precision, and that non-DC coefficient's real and imaginary parts are each
   individually confirmed nonzero (not merely that the coefficient as a whole is
   nonzero).
2. **Given** a Trotter-frontend-lowered circuit, independently constructed from
   the Pauli-PQC frontend's own validation case, whose Fourier coefficients are
   likewise known analytically to include at least one genuinely complex non-DC
   coefficient, **When** the Foundation Layer's oracle evaluates it, **Then** the
   returned coefficients match the analytic values to floating-point precision
   with the same real-and-imaginary non-triviality check.
3. **Given** either frontend's per-upload coefficient scaling is deliberately
   altered (e.g. an incorrect Trotter-step division), **When** that frontend's
   validation test runs, **Then** the test fails — because the validation case's
   expected values are sensitive to that exact scaling, not merely to its sign or
   presence.

---

### Edge Cases

- What happens when the Pauli-PQC frontend receives Pauli strings tied to the same
  parameter that act on different qubits? The Foundation Layer's IR does not by
  itself require tied terms to share a qubit set (§11.2's tied generators are
  commuting Pauli strings, not necessarily coincident ones); this is accepted, and
  responsibility for physical sensibility of the tie stays with the caller.
- What happens when the Trotter frontend's fixed evolution time is exactly zero?
  It must raise (superseding an earlier draft's "must not raise, degenerate but
  valid"): every derived coefficient `c = -h·τ/(π·r)` collapses to exactly zero,
  which the Foundation Layer's IR itself rejects (`PauliTerm.coefficient` must be
  nonzero) — and a zero evolution time carries no information about the coupling
  being extracted regardless.
- What happens when a caller declares a coupling group whose Pauli terms have
  *different* fixed structural weights (even though they nominally "share a
  coupling")? The frontend must raise: their derived coefficients would differ
  even though they are tied to one parameter, violating the Foundation Layer's
  per-parameter coefficient-uniformity requirement (Spec 1 FR-007) the moment the
  group is lowered — "sharing a coupling" alone does not automatically satisfy
  that invariant; equal per-term weight within the declared group is what does.
- What happens when a coupling group contains exactly one Pauli term (multiplicity
  1)? This is the simplest, fully valid case — tying only matters once a group has
  two or more terms; a single-term group is not an error.
- What happens when different coupling groups happen to use numerically equal
  weights (but represent physically distinct, independently unknown couplings)?
  They still get separate encoded parameters — grouping is by which coupling a term
  belongs to, as the caller declares it, never inferred from numerically-equal
  weights alone.
- What happens when a single validation test case is reused for both frontends'
  "genuinely complex" requirement? This is explicitly insufficient (User Story 3):
  each frontend needs its own case, because a scaling defect can be specific to one
  frontend's own coefficient computation and invisible in a shared, differently
  structured test.
- What happens when the Trotter step count is very large, making the resulting
  circuit's parameter count or the oracle's grid cost expensive? The Foundation
  Layer's oracle already predicts and refuses to exceed a configured cost budget
  without confirmation (its own FR-013); this feature does not need to duplicate
  that guard, only avoid bypassing it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Pauli-PQC frontend MUST accept an ordered description of Pauli
  strings, where each string specifies: the Pauli letters it applies, which encoded
  parameter it uploads, which other strings (if any) it is tied to within that
  upload (its multiplicity group), and its own real structural coefficient.
- **FR-002**: The Pauli-PQC frontend MUST lower its input into a Foundation-Layer
  `PauliEncodedCircuitIR` satisfying the `Encoding` Protocol, preserving the
  supplied order, tie structure, and coefficients exactly (Spec 1 FR-004, FR-005).
- **FR-003**: The Pauli-PQC frontend MUST support multiple Pauli strings tied to
  one encoded parameter within a single upload (multiplicity `r_j > 1`) and MUST
  NOT permit a construction in which tied strings receive independent parameters
  instead (Spec 1 FR-005, Constitution §11.2).
- **FR-004**: The Pauli-PQC frontend MUST raise rather than return a degenerate
  circuit when given no Pauli strings at all (§10.1).
- **FR-005**: The Pauli-PQC frontend MUST propagate, not swallow or obscure, the
  Foundation Layer's own construction-time rejection when a caller requests tied
  Pauli strings with heterogeneous coefficients (Spec 1 FR-007 — every term sharing
  a parameter_index must carry the exact same coefficient; Clarifications,
  2026-08-20). The frontend does not need to duplicate that check — it relies on
  the IR raising — but MUST NOT catch and discard the resulting error.
- **FR-006** (revised — paradigm shift, Clarifications 2026-08-20): The Trotter
  frontend MUST accept: (a) one or more **coupling groups**, each a set of Pauli
  strings sharing one unknown coupling constant, with each string's own fixed,
  known structural weight within that group; (b) a fixed, known evolution time
  `τ`; and (c) a fixed, known first-order Trotter step count `r`. The coupling
  constants themselves are the encoded (unknown) parameters the Foundation Layer's
  oracle extracts — `τ` and `r` are NOT encoded parameters; they are ordinary
  constructor arguments, fixed before any circuit is built (Constitution §7.1 — the
  classical input selects fixed gates; the unknown parameter is what carries the
  frequencies).
- **FR-007** (revised — paradigm shift, Clarifications 2026-08-20): The Trotter
  frontend MUST lower its input into a `PauliEncodedCircuitIR` by giving **each
  declared coupling group its own encoded parameter**, tying together every Pauli
  string in that group (multiplicity equal to the number of strings in the group)
  and repeating that tied block once per Trotter step (upload count `r`), with
  every term in the group assigned the identical coefficient:

  ```
  c = -h·τ / (π·r)
  ```

  where `h` is the group's common per-term structural weight, `τ` is the fixed
  evolution time, and `r` is the fixed Trotter step count. This is derived from
  equating one first-order Lie-Trotter step for a coupling-group term,
  `exp(-i·h·α·P·(τ/r))` (`α` the group's coupling value, bound at evaluation time),
  against this project's own gate convention `exp(+iπ·c·α·P)` (Spec 1 FR-021):
  `π c = -h τ/r`. **Verified in-session against the actual target unitary — not
  assumed from the formula's resemblance to the earlier, now-superseded
  `c_k = -h_k/(πL)` time-based formula**: an initially-proposed sign-omitted variant
  (`c = +hτ/(πr)`) was checked against the exact physics and does not match; the
  negative sign is load-bearing, the same class of error this project has hit
  before (Spec 1 FR-021's own sign convention).
- **FR-008** (new, Clarifications 2026-08-20): The Trotter frontend MUST validate
  that every Pauli string within one declared coupling group carries the exact
  same structural weight `h`, and MUST raise — with a clear, domain-specific error
  naming the group — if this does not hold. "Sharing a coupling" does not, by
  itself, guarantee the Foundation Layer's per-parameter coefficient-uniformity
  requirement (Spec 1 FR-007): if a caller mistakenly declares a group whose terms
  have different weights, the derived per-term coefficients would differ despite
  nominally sharing one coupling, and lowering that group would either be rejected
  by the IR with a message that doesn't name the actual mistake, or — if the
  frontend computed a single coefficient from only one term's weight — silently
  produce a physically wrong circuit for the other terms.
- **FR-009**: The Trotter frontend MUST reuse the Pauli-PQC frontend's
  IR-construction logic rather than independently reimplementing it (Constitution
  §9.4 — no duplicated call paths).
- **FR-010**: The Trotter frontend MUST raise when given: a Trotter step count `r`
  that is zero or negative; an evolution time `τ` of exactly zero (every derived
  coefficient would then be exactly zero, which the Foundation Layer's IR itself
  rejects, and a zero evolution time carries no information about any coupling to
  extract); a coupling group with zero Pauli strings; or no coupling groups
  declared at all (§10.1).
- **FR-011**: A validation test MUST exist for the Pauli-PQC frontend that lowers a
  circuit whose Fourier coefficients are known analytically (or independently,
  numerically pre-verified) to include at least one non-DC coefficient with both a
  nonzero real part and a nonzero imaginary part, and MUST assert both parts are
  individually nonzero — not merely that the coefficient's magnitude is nonzero
  (Constitution §4.3).
- **FR-012**: A validation test MUST exist for the Trotter frontend, using its own
  independently constructed circuit with **at least two distinct coupling groups,
  one of which has multiplicity greater than one** (exercising both the
  multi-parameter grouping FR-007 requires and the tied, common-weight coefficient
  computation FR-008 guards), that likewise reproduces at least one non-DC
  coefficient with both parts individually confirmed nonzero (Constitution §4.3,
  §6.4). A validation suite in which both frontends' tests happen to produce only
  real-valued coefficients is a defect: it cannot distinguish a correct per-upload
  coefficient computation from one with an undetected scaling error, nor can a
  single-group, single-term Trotter test exercise FR-007's `c = -h·τ/(π·r)`
  computation meaningfully (it would pass even with a wrong `h`, `τ`, or `r`
  entering the formula, as long as the result happened to be nonzero).
- **FR-013**: Both frontends' validation tests MUST execute their lowered IR
  through the Foundation Layer's reference oracle and compare the returned
  coefficients to the tests' known analytic values to floating-point precision
  (relative error ≤ 1e-9, matching Spec 1 SC-002's tolerance).

### Key Entities *(include if feature involves data)*

- **Pauli-PQC frontend**: Converts an explicit, ordered description of Pauli
  strings — with parameter assignment, tie structure, and coefficients — into a
  Foundation-Layer IR instance. The more general and more primitive of the two
  frontends.
- **Trotter frontend**: Converts one or more coupling groups (each a set of Pauli
  strings sharing one unknown coupling constant, with known per-term weights), a
  fixed evolution time `τ`, and a fixed first-order Trotter step count `r`, into a
  Foundation-Layer IR instance, by delegating to the Pauli-PQC frontend's
  IR-construction logic with a mechanically derived per-group coefficient
  (`c = -h·τ/(π·r)`). Produces one encoded parameter per coupling group — a
  multi-dimensional IR when more than one coupling is unknown (Clarifications,
  2026-08-20) — where each parameter *directly is* a physical coupling constant, not
  a scaled proxy for time; no reconstruction step is needed to interpret the output.
- **Coupling group**: A caller-declared set of Hamiltonian Pauli strings, each with
  its own known structural weight, that all share one unknown coupling constant
  (e.g. every term contributing to a hopping strength `J`). The Trotter frontend's
  unit of grouping — one coupling group becomes one encoded parameter.
- **Pauli operator (Hamiltonian)**: A weighted sum of Pauli strings — the Trotter
  frontend's structural input. Its per-term weights are known and fixed; its
  coupling constants (grouped via coupling groups) are the encoded, unknown
  parameters this feature extracts. Evolution time and Trotter step count are
  separate, also-known-and-fixed inputs, distinct from both the weights and the
  couplings.
- **Validation suite**: The set of tests confirming each frontend's lowered IR
  reproduces known-correct Fourier coefficients via the Foundation Layer's oracle,
  including the mandatory per-frontend genuinely-complex-coefficient case.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can construct a Pauli-encoded feature map — including one
  with tied, multiplicity-`r_j` parameters — by describing it as a list of Pauli
  strings, without writing any Foundation-Layer IR internals directly.
- **SC-002** (revised — paradigm shift, Clarifications 2026-08-20): A developer can
  construct a Trotterized feature map for one or more unknown Hamiltonian couplings
  — at a fixed evolution time and Trotter step count they already know — by
  describing coupling groups, without manually computing any per-term rotation
  angle.
- **SC-003**: Both frontends' lowered IR instances, evaluated by the Foundation
  Layer's oracle, reproduce their known analytic Fourier coefficients to
  floating-point precision (relative error ≤ 1e-9), and each frontend's own
  validation case includes at least one non-DC coefficient with independently
  confirmed nonzero real and imaginary parts.
- **SC-004**: A per-upload coefficient scaling defect introduced into either
  frontend (e.g. an incorrect Trotter-step division) causes that frontend's
  validation test to fail — verified by construction (the validation case's
  expected values are numerically sensitive to the exact scaling), not merely
  assumed.
- **SC-005** (revised — paradigm shift, Clarifications 2026-08-20): The Trotter
  frontend correctly lowers a Hamiltonian with at least two coupling groups into a
  multi-dimensional IR (one parameter per group), correctly ties same-weight terms
  within one group (satisfying the Foundation Layer's uniformity requirement by
  construction), and rejects a declared group whose terms have different weights.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1): the
  `PauliEncodedCircuitIR`, the `Encoding` Protocol, and the reference oracle already
  exist and are not re-specified here.
- The Trotter frontend's encoded parameters are the Hamiltonian's own coupling
  constants (one per declared coupling group) — **not** evolution time
  (superseding this spec's original framing; corrected in this session's second
  paradigm-shift round of Clarifications). Evolution time `τ` and Trotter step
  count `r` are both fixed, known classical constructor arguments, exactly like
  each other, neither swept nor extracted (Constitution §7.1). Each term's
  structural weight within its coupling group is likewise a fixed, known quantity
  supplied by the caller, distinct from the group's own unknown coupling value.
- "First-order Trotter" means the Lie-Trotter product formula
  (`U(τ) ≈ (∏_k exp(-i h_k α_k P_k (τ/r)))^r` for fixed `τ`, `r`, with `α_k` the
  unknown coupling value for term `k`'s group and `h_k` that term's fixed weight);
  higher-order (e.g. Suzuki-Trotter) product formulas are out of scope for this
  spec.
- Because each encoded parameter directly *is* a physical coupling constant, this
  spec's validation (FR-011/FR-012/FR-013) needs no reconstruction step at all —
  unlike the abandoned time-as-parameter framing, there is no multi-dimensional
  output to recombine into a 1-D series; each parameter's own raw coefficients are
  already the physically meaningful answer.
- Both the Trotter step count `r` and the evolution time `τ` are required inputs
  with no default: `r` affects physical approximation quality and a
  silently-chosen default could misrepresent accuracy (§10.1); `τ = 0` is rejected
  outright (Edge Cases) rather than defaulted away from. Reasonable choices for a
  given accuracy target and experiment are left to the caller (and, later, to the
  experiment layer).
- "Genuinely complex" analytic ground truth for each frontend's validation case is
  established the same way it was for the Foundation Layer's own two-upload case:
  derived analytically and independently cross-checked numerically before being
  encoded in the test, not asserted from memory.
- Neither frontend introduces branching on parameter count or circuit size
  (Constitution §9.3); per-parameter and per-term structure is carried as data
  through to the IR, matching the Foundation Layer's own architectural constraint.
