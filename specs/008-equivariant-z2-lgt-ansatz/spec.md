# Feature Specification: Equivariant Z2 LGT Ansatz and Containment Verification

**Feature Branch**: `008-equivariant-z2-lgt-ansatz`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Equivariant Z2 LGT Ansatz and Containment Verification (Spec 8). Deliverables: (a) The equivariant ansatz circuit construction that preserves the Z2 Gauss law by construction, built only from the generator set {Z_v}_mass, {X_e}_electric, {h_e=(1/2)(A_e+B_e)}_hopping (A_e=X_v Z_e X_v', B_e=Y_v Z_e Y_v'), targeting the full matter+gauge Hamiltonian H = J*H_hop + m*H_m + f*H_g. (b) Parameter tying: A_e and B_e must be driven by one shared coupling parameter per edge (the physically correct Trotterization; treating them independently breaks U(1)_Q charge conservation and is the unphysical/rejected choice). (c) A Containment Verification mechanism proving, on small tractable instances, that the ansatz's true nonzero frequency support (Omega) is a subset of the symmetry-restricted sublattice (Lambda) derived via Constitution Sec 11.4's polynomial-time F2/integer-kernel elimination procedure -- Omega is subset of Lambda is subset of (but strictly smaller than) the ambient frequency box. CRITICAL MANDATES: 1. Symmetry Integration: the ansatz must explicitly declare its Gauss law generators (G_v = Z_v * product of X_e over edges at v) as a SymmetryDeclaration and pass them through Spec 7's verify_symmetry hook before any circuit is trusted. 2. Honest Measurement-Advantage Claim: the containment check must report Lambda strictly smaller than ambient as a concrete, computed constant-factor reduction (not an asymptotic separation) per Constitution Sec 11.7/11.8 -- this Z2 platform is validation-only, no separation claim is permitted. 3. Target Hamiltonian: must be the full matter+gauge Z2 LGT Hamiltonian (mass + electric + hopping terms), not a simplified stand-in."

## Clarifications

### Session 2026-08-21

- Q: Should the target Hamiltonian (FR-002) use global scalar couplings
  `J, m, f` (the report's own eq. 1–4 form), or independently learnable
  local couplings per vertex/edge? → A: **Local couplings — a critical
  architectural inconsistency, not a stylistic choice.** Global scalars
  give an encoded-parameter count of `d = 3` (one classical input
  dimension per Hamiltonian term-*type*), which directly contradicts
  FR-006's already-correct requirement that every edge `e` gets its *own*
  tied hopping parameter `α_e` — under global couplings there is only one
  hopping parameter total, not one per edge, so FR-006 would have nothing
  distinct to tie per edge. It also trivializes User Story 3's own
  containment/complexity claim: Theorem 6.1's sublattice `Λ ⊆ 2Z^d` is
  only a meaningful, instance-scaling object when `d` scales with the
  lattice's own size. FR-002 is corrected below to local couplings
  `{J_e}_{e∈E}, {m_v}_{v∈V}, {f_e}_{e∈E}`, giving `d = |V| + 2|E|` —
  matching the primary report's own register-sizing (§5.3/eq. 26:
  multiplicities `r_j=1` for mass/electric, `r_j=2` for hopping) and
  Constitution §11.3's multiplicity-propagation rule, and matching the
  independent corroborating source's own explicit framing of this exact
  question (`docs/references/Local Parametrization in Z2 LGT - Google
  Gemini.pdf`: "the number of learning parameters in FCE is not constant
  `d=3` but `d=|V|+2|E|=poly(n)`").

## User Scenarios & Testing *(mandatory)*

<!--
  This is the first feature in this research programme (Constitution §11)
  to actually build the equivariant ansatz Spec 7's verification engine was
  built to gate, and the first to give Theorem 6.1's Λ/Ω containment claim
  (docs/references/equivariant FCE Z2LGT report.pdf) a concrete, checked
  instance rather than a citation. Its "users" are the developers/
  researchers extending this codebase toward the U(1) separation target
  (Constitution §11.0) — they need a trustworthy, gauge-invariant-by-
  construction ansatz for the Z₂ validation platform, and a mechanical,
  non-circular check that its own frequency-support claim actually holds
  before any downstream result relies on it.
-->

### User Story 1 - Construct a Gauss-law-equivariant ansatz for the full matter+gauge Z₂ LGT Hamiltonian (Priority: P1)

A developer wants to build a Pauli-encoded ansatz circuit for the Z₂
lattice gauge theory Hamiltonian, with independently learnable local
couplings `{J_e}_{e∈E}, {m_v}_{v∈V}, {f_e}_{e∈E}` (Clarifications,
2026-08-21: never the report's own global-scalar `J, m, f` shorthand,
which collapses the encoded-parameter count to `d=3`), whose term
library is restricted, at construction time, to exactly the three
gauge-invariant generator families the Gauss law permits — so that Gauss's
law `G_v = Z_v·∏_{e∋v}X_e` holds by construction, not by a later twirl or
patch — and who wants that claim mechanically checked, not merely asserted.

**Why this priority**: This is the foundational deliverable. Deliverable
(b)'s parameter tying is a construction detail *of* this ansatz, and
deliverable (c)'s containment verification has nothing to measure the
frequency support *of* until this ansatz exists. Without it, Constitution
§11.0's stated target ("an equivariant, Pauli-encoded ansatz for a lattice
gauge theory") is still just a citation, not a capability in this codebase.

**Independent Test**: Can be fully tested by declaring a small lattice
(a handful of matter sites and gauge links), building the ansatz, and
confirming (1) every term in the resulting Hamiltonian is one of `{Z_v}`,
`{X_e}`, or `{h_e}` — never an arbitrary Pauli string — and (2) the
declared Gauss law generators pass Spec 7's `verify_symmetry` unmodified,
while a deliberately corrupted generator set (e.g. a single bit flipped in
one `G_v`'s Pauli label) is rejected before any circuit compiles.

**Acceptance Scenarios**:

1. **Given** a small lattice (matter sites `V`, gauge links `E`) and
   independently declared local coupling values `m_v` (per vertex) and
   `f_e`, `J_e` (per edge), **When** the ansatz is constructed, **Then**
   the resulting Hamiltonian's term list contains only mass terms
   `m_v·(-1)^v Z_v`, electric terms `f_e·X_e`, and hopping generators
   `J_e·h_e = J_e·(1/2)(A_e + B_e)` with `A_e = X_v Z_e X_v'`,
   `B_e = Y_v Z_e Y_v'` — the full matter+gauge Hamiltonian with local
   couplings (Critical Mandate 3; Clarifications, 2026-08-21), never a
   partial stand-in that drops the mass or electric term, and never
   collapsed to a single global coupling per term-type.
2. **Given** the constructed ansatz, **When** its Gauss law generators
   `G_v = Z_v·∏_{e∋v}X_e` (one per matter site `v`) are declared as a
   `SymmetryDeclaration`, **Then** they are passed through Spec 7's
   `verify_symmetry` and accepted on all three of Constitution §11.1's
   conditions (internal, non-annihilating, Abelian) — reusing Spec 7's
   engine unmodified, not a separate re-implementation (Critical
   Mandate 1).
3. **Given** a deliberately invalid Gauss law declaration (e.g. one
   generator missing a link-qubit factor, so it no longer commutes with
   `H_hop`), **When** ansatz construction is attempted, **Then**
   construction is rejected — via Spec 7's existing
   `InvalidSymmetryError`/`PhysicalModelDescription.__post_init__`
   enforcement pattern, not a new, separately-bypassable check — before
   any circuit-compilation module (Spec 3) is invoked.
4. **Given** the compiled ansatz circuit, **When** its gate ordering is
   inspected, **Then** the commuting family `F = {Z_v} ∪ {X_e}` used by
   the containment derivation (Theorem 6.1) is applied as one contiguous,
   uninterrupted block — any construction stage that would reorder gates
   MUST re-assert this contiguity or fail loudly (Constitution §11.9/
   §11.10), never silently produce a circuit the containment theorem no
   longer covers.

---

### User Story 2 - Tie the hopping generators A_e and B_e to one shared parameter per edge (Priority: P2)

A developer wants each gauge-covariant hopping term's two constituent
Pauli strings, `A_e = X_v Z_e X_v'` and `B_e = Y_v Z_e Y_v'`, driven by
exactly one shared coupling parameter per edge — the physically correct
Trotterization — and wants it computationally confirmed, not merely
asserted from the reference report, that (i) this tying introduces no
Trotter error, and (ii) untying them (the naive "one Pauli string, one
parameter" reading) genuinely breaks `U(1)_Q` charge conservation.

**Why this priority**: Depends on User Story 1's ansatz existing (the
hopping term is one of its three generator families), but is not optional
polish — Constitution §11.2 requires tied Pauli strings sharing one
commuting-generator sum to share one parameter, and this is the one place
in the ansatz where getting that wrong silently breaks the very symmetry
User Story 1 exists to preserve.

**Independent Test**: Can be fully tested in isolation from the full
lattice — given a single edge `e = (v, v')`, construct both the tied
two-gate sequence and an untied version with independent angles, and
confirm computationally that the tied sequence exactly equals
`e^{iπα(A_e+B_e)}` (no Trotter error) while the untied sequence does not
commute with `Q = Σ_v Z_v` for a generic choice of its two angles.

**Acceptance Scenarios**:

1. **Given** an edge `e` and one coupling parameter `α_e`, **When** the
   ansatz drives `A_e` and `B_e`'s Pauli-encoded gates, **Then** both
   gates use exactly `α_e` — reusing this codebase's existing tie-group
   mechanism (Constitution §11.2; the `CouplingGroup` tie-group index
   already shipped in Specs 2/6) — never two independent parameters for
   the same edge.
2. **Given** a concrete numeric value of `α_e`, **When** the tied
   two-gate sequence's `Operator` is compared against a direct matrix
   exponential of the combined generator `e^{iπα_e(A_e+B_e)}`, **Then**
   they are exactly equal (Proposition 5.1(iii): `[A_e, B_e] = 0`, so the
   split is exact, not a first-order approximation) — checked as its own
   dedicated `Operator`-equivalence test, independent of any
   coefficient-level or end-to-end test (this project's own standing rule
   for gate-construction sign/decomposition claims).
3. **Given** the same edge with `A_e` and `B_e` instead assigned two
   independent angles, **When** their commutator with the total charge
   `Q = Σ_v Z_v` is computed for a generic (non-degenerate) choice of the
   two angles, **Then** it is nonzero — confirming untying genuinely
   breaks `U(1)_Q` (Remark 5.2) as a checked property of this codebase's
   own constructed gates, not an assertion taken on the reference report's
   word alone.

---

### User Story 3 - Verify the ansatz's active frequencies are contained in, and strictly fewer than, the ambient frequency box (Priority: P3)

A developer wants to confirm, on a small enough lattice instance that
brute-force checking is still tractable, that the ansatz's own true
nonzero-coefficient frequency support `Ω` is contained in the
symmetry-restricted sublattice `Λ` derived from the Gauss law and total-
charge constraints (Theorem 6.1), and that `Λ` is itself a strict, concrete
subset of the separate, larger, symmetry-unaware ambient frequency box
already used by this codebase's Foundation/Extract layers (Specs 1–4) —
reported honestly as a constant-factor measurement reduction, never as an
asymptotic learning separation.

**Why this priority**: Depends on User Story 1's ansatz existing (there is
no `Ω` to extract without a real circuit) and benefits from, but does not
strictly require, User Story 2's tying being in place first. Ranked below
both because it is the *verification* of a claim about the ansatz, not the
ansatz itself — but it is not optional: without it, "the ansatz is
equivariant" and "extraction over `Λ` is sound" remain unverified claims,
exactly the gap Constitution §11.6 exists to close.

**Independent Test**: Can be fully tested by declaring one small lattice
instance, computing `Λ` via the polynomial-time procedure, extracting `Ω`
by brute force against the existing Extract Layer oracle (Spec 4), and
confirming `Ω ⊆ Λ` and `Λ ⊊ ambient` both hold, with the size reduction
`|ambient| / |Λ|` reported as a specific number alongside an explicit
statement that this is a constant-factor effect, not a separation claim.

**Acceptance Scenarios**:

1. **Given** a small lattice instance's Gauss law and total-charge
   constraints, **When** `Λ` is computed, **Then** it is derived via
   Constitution §11.4's named, polynomial-time pre-processing stage — F2
   Gaussian elimination for the per-vertex multiplicative Gauss law parity
   checks (report §7.3) intersected with integer-hyperplane elimination
   for the additive total-charge constraint (report §7.2) — never an
   inline filter folded into extraction itself.
2. **Given** the same instance, **When** `Ω` (the ansatz circuit's actual
   nonzero frequencies) is extracted by brute force against the existing,
   already-verified Extract Layer oracle (Spec 4), **Then** `Ω ⊆ Λ` holds
   — and if it does not, this is reported and treated as a derivation
   defect in this feature's own ansatz construction (Constitution §11.6),
   never silently tolerated, hidden, or worked around by loosening `Λ`.
3. **Given** the same instance's separately-computed ambient frequency box
   (the full `{-2L,...,2L}^d` set Specs 1–4 already use, sized per
   Constitution §11.3's multiplicity-adjusted `L`), **When** `Λ` and the
   ambient box are compared, **Then** `Λ ⊊ ambient` (strict) is asserted
   with the concrete reduction factor computed and reported, labeled
   explicitly as a constant-factor effect (`2^{-(d+|V|)}` per report §7.4,
   arising because the Gauss law's constraints are multiplicative — index-
   reducing, not rank-reducing, per Constitution §11.7). **Clarifications,
   2026-08-21**: both `d` (the encoded-parameter/frequency-lattice
   dimension) and the resulting ambient box size MUST be computed
   dynamically from the declared instance's own actual vertex and edge
   counts as `d = |V| + 2|E|` (FR-002's corrected local-coupling form) —
   never hard-coded or treated as a fixed constant such as the report's
   own global-scalar `d=3`.
4. **Given** any containment result this feature produces, **When** it is
   reported, **Then** it carries, as a structural part of the result
   (never only as prose that could be dropped), an explicit statement that
   no quantum learning separation is being claimed on this `Z₂` validation
   platform (Constitution §11.8) — because `Λ` is itself classically
   computable in polynomial time and would help a classical learner
   exactly as much as a quantum one.

---

### Edge Cases

- What happens if the declared lattice instance is too large for the
  Extract Layer's brute-force oracle extraction (User Story 3) to remain
  tractable? The instance size must be chosen so the extraction cost is
  predicted and logged before it is paid (Constitution §11.5) — this
  feature does not attempt containment verification on an instance whose
  brute-force cost was not estimated first.
- What happens if a bug in the ansatz construction causes the actual `Ω`
  to exceed the derived `Λ`? This is treated and reported explicitly as a
  derivation defect in this feature's own construction (Constitution
  §11.6) — not as evidence the theorem is wrong, and not silently patched
  by recomputing a looser `Λ` after the fact.
- What happens for a lattice with zero gauge links (`E = ∅`, matter only,
  no hopping or electric terms)? The hopping and electric generator
  families are vacuously absent; mass-only Gauss law reduces to a trivial
  per-site check — this degenerate instance is not this feature's
  headline containment claim (Critical Mandate 3 requires the full
  matter+gauge Hamiltonian) but must not crash construction.
- What happens for a "pure-gauge" instance (links only, no matter sites)?
  The Gauss-law-only constraint gives a cycle-space (first-Betti-number)
  reduction, not the full matter+gauge counting result (report §7.5) —
  this is explicitly out of scope for this spec's primary claim (Critical
  Mandate 3) and is not required to be exercised, though nothing in this
  spec precludes it as an additional check.
- What happens if two different lattice instances give a different
  numeric constant-factor reduction? This is expected and correct — the
  reduction factor `2^{-(d+|V|)}` depends on the instance's own
  dimension `d` and vertex count `|V|`; the requirement (Acceptance
  Scenario US3-3) is that the reported factor is the one actually computed
  for the declared instance, never a fixed or hard-coded number.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST construct a Pauli-encoded ansatz circuit
  whose Hamiltonian term library is restricted, at construction time, to
  exactly the generator set `Γ_enc = {Z_v}_mass ∪ {X_e}_electric ∪
  {h_e = (1/2)(A_e+B_e)}_hopping` — never admitting an arbitrary Pauli
  string outside these three families.
- **FR-002** (**revised, Clarifications 2026-08-21**): The ansatz's target
  Hamiltonian MUST be the full matter+gauge Z₂ LGT Hamiltonian with
  **independently learnable local couplings**, not global scalars:
  `H = Σ_{e=(v,v')} J_e·h_e + Σ_v m_v·(-1)^v Z_v + Σ_e f_e·X_e`, where
  `h_e = (1/2)(A_e+B_e)` — never a simplified stand-in that omits any of
  the three term-families, and never collapsed to the report's own
  global-scalar `H = J·H_hop+m·H_m+f·H_g` form, which would give only
  `d=3` encoded parameters. This local-coupling form gives an encoded-
  parameter count `d = |V| + 2|E|` (`|V|` mass parameters `m_v`, `|E|`
  electric parameters `f_e`, `|E|` tied hopping parameters `J_e`) — this
  is what makes FR-002 consistent with FR-006's per-edge tying: FR-006
  ties `A_e`/`B_e` to **one shared parameter per edge**, which only has
  meaning as a distinct, per-edge quantity because FR-002 already declares
  one independent `J_e` per edge, not one global `J` shared by every edge.
- **FR-003**: The ansatz MUST explicitly declare its Gauss law generators
  `G_v = Z_v·∏_{e∋v} X_e`, one per matter site `v`, as a Spec 7
  `SymmetryDeclaration`.
- **FR-004** (**Symmetry Integration**, Critical Mandate 1): Before an
  ansatz circuit is trusted for any reported result, its Gauss law
  `SymmetryDeclaration` MUST be passed through Spec 7's `verify_symmetry`
  hook and pass all three of Constitution §11.1's conditions; construction
  MUST be rejected — via Spec 7's existing `PhysicalModelDescription.
  __post_init__` enforcement pattern — if it does not.
- **FR-005**: Any construction or compilation stage that reorders the
  ansatz circuit's gates MUST assert, not merely comment, that the
  commuting family `F = {Z_v} ∪ {X_e}` remains a contiguous, uninterrupted
  block afterward (Constitution §11.9/§11.10) — failing loudly if it does
  not, since Theorem 6.1's containment derivation requires this
  contiguity.
- **FR-006** (**Parameter Tying**, Critical Mandate/Deliverable b): For
  every edge `e`, the ansatz MUST drive the Pauli-encoded gates generated
  by `A_e` and `B_e` with exactly one shared coupling parameter — reusing
  this codebase's existing tie-group mechanism (Constitution §11.2) —
  never two independent parameters for the same edge.
- **FR-007**: The system MUST verify, via a dedicated `Operator`-
  equivalence test at a concrete parameter value (independent of and in
  addition to any coefficient-level or end-to-end test), that the tied
  two-gate sequence for `A_e, B_e` exactly equals `e^{iπα(A_e+B_e)}` with
  no Trotter error (Proposition 5.1(iii): `[A_e,B_e]=0`).
- **FR-008**: The system MUST verify, via a dedicated commutator
  computation at concrete, independent parameter values, that an untied
  version of the same two gates (independent angles for `A_e` and `B_e`)
  does not commute with the total charge `Q = Σ_v Z_v` for a generic
  choice of those angles — confirming untying is the rejected, unphysical
  choice (Remark 5.2), not merely citing it.
- **FR-009** (**Containment Verification**, Deliverable c): The system
  MUST compute `Λ`, the symmetry-restricted sublattice of Theorem 6.1, for
  a declared small lattice instance via Constitution §11.4's named,
  polynomial-time pre-processing stage: F2 Gaussian elimination for the
  Gauss law's multiplicative parity constraints intersected with integer-
  hyperplane elimination for the additive total-charge constraint — `Λ`
  MUST NOT be produced as an inline filter folded into extraction.
- **FR-010**: The system MUST extract `Ω`, the ansatz circuit's own true
  nonzero-coefficient frequency support, on the same small lattice
  instance by brute-force support extraction against the existing Extract
  Layer oracle (Spec 4) — reusing that already-verified extraction, not
  reimplementing frequency extraction independently.
- **FR-011**: The system MUST assert `Ω ⊆ Λ` for at least one small,
  tractable declared instance before any `Λ`-restricted extraction result
  from this ansatz is trusted for any reported claim (Constitution §11.6);
  a violation MUST be reported as a derivation defect in this feature's
  own construction, never silently tolerated.
- **FR-012** (**terminology correction** — see Assumptions): The system
  MUST also compute the separate ambient frequency box (the full,
  symmetry-unaware `{-2L,...,2L}^d` set, sized per Constitution §11.3's
  multiplicity-adjusted `L`) for the same instance, and assert the strict
  containment `Λ ⊊ ambient`, reporting the concrete, computed reduction
  factor `|ambient| / |Λ|` for that instance.
- **FR-013** (**Honest Measurement-Advantage Claim**, Critical Mandate 2):
  Every reported `Λ ⊊ ambient` reduction MUST be labeled explicitly as a
  constant-factor reduction (mechanism: the Gauss law's multiplicative
  constraints reduce only the index/prefactor, Constitution §11.7) — the
  system MUST NOT present, or allow this reduction to be read as, an
  asymptotic or exponential learning separation.
- **FR-014**: Every containment result this feature produces MUST carry,
  as a structural field (not only prose), an explicit statement that no
  quantum learning separation is claimed on this `Z₂` validation platform
  (Constitution §11.8) — because `Λ` is itself classically computable and
  would reduce a classical learner's cost by the same factor.

### Key Entities *(include if feature involves data)*

- **Z₂ LGT lattice description**: The matter-site/gauge-link topology
  (matter sites `V`, gauge links `E` each connecting two matter sites) a
  concrete instance is declared over — the structural analogue, for this
  Hamiltonian, of Spec 6's `TFIMGraph`/`TFIMEdge`.
- **Equivariant ansatz description**: The full matter+gauge Hamiltonian
  (FR-001/FR-002), its tied hopping parameters (FR-006), and its attached,
  Spec-7-verified Gauss law `SymmetryDeclaration` (FR-003/FR-004) — the
  single object User Stories 1–2 build and User Story 3 measures.
  **Clarifications, 2026-08-21**: its coupling values are per-term *local*
  data, not global scalars — one `m_v` per matter site, one `f_e` and one
  `J_e` per gauge link — the structural precedent being Spec 6's
  `TFIMEdge`, which already attaches one independent `coupling_strength`
  to each declared edge rather than a single model-wide constant; this
  feature's lattice/coupling data follows that same per-vertex/per-edge
  pattern, extended to three coupling families instead of one.
- **Containment verification result**: For one declared instance — the
  computed `Λ`, the extracted `Ω`, the separately-computed ambient box,
  the `Ω ⊆ Λ ⊊ ambient` verdicts, the concrete numeric reduction factor,
  and the mandatory constant-factor/no-separation caveat (FR-012–FR-014).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a declared small Z₂ LGT instance, the system produces
  one equivariant ansatz circuit whose term list contains only mass,
  electric, and hopping generators, and whose declared Gauss law symmetry
  passes Spec 7's verification unmodified; a corrupted or invalid Gauss
  law declaration is always rejected before any circuit compiles.
- **SC-002**: For every edge in a declared instance, exactly one coupling
  parameter drives both that edge's `A_e` and `B_e` gates — verified
  across every edge in the instance, not a single sampled edge.
- **SC-003**: A dedicated computational check confirms the tied two-gate
  sequence exactly equals the combined hopping generator's evolution (no
  Trotter error) at a concrete parameter value, and a second dedicated
  check confirms the untied version fails to commute with the total
  charge at concrete, independent parameter values.
- **SC-004**: For at least one small tractable instance, the system
  computes `Λ` and independently extracts `Ω`, confirms `Ω ⊆ Λ ⊊ ambient`,
  and reports the specific numeric reduction factor for that instance.
- **SC-005**: No containment result produced by this feature is ever
  reported without its structural constant-factor/no-separation caveat —
  audited by that caveat being a required field of the result type, not
  optional prose that can be silently dropped.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1),
  Encodings Layer (Spec 2), Circuits Layer (Spec 3), Extract Layer
  (Spec 4), Learning Backend Layer (Spec 5), Experiment and Models Layer
  (Spec 6), and Symmetry Verification Layer (Spec 7) — reusing, not
  re-specifying: Specs 2/6's tie-group mechanism (FR-006), Spec 4's
  oracle-based frequency extraction (FR-010), and Spec 7's
  `verify_symmetry`/`PhysicalModelDescription` enforcement pattern
  (FR-004).
- **Primary source**: `docs/references/equivariant FCE Z2LGT report.pdf`
  (read and verified in-session) — the full Hamiltonian (eq. 1–4), the
  Gauss law (eq. 5), the hopping generators `A_e`/`B_e` (eq. 2), the
  exactness of the tied split (Proposition 5.1), the physical
  justification for tying (Remark 5.2), the formal `Λ` construction
  (Theorem 6.1, eq. 33), and the Z₂-specific counting result (§7.1–§7.5,
  including the `2^{-(d+|V|)}` constant-factor reduction and the explicit
  caution against a separation claim on this platform, §8.4 risk R1). A
  secondary source, `docs/references/Local Parametrization in Z2 LGT -
  Google Gemini.pdf`, independently corroborates the same Hamiltonian,
  Gauss law, and `A_e`/`B_e` tying derivation via an explicit fermionic-
  charge-cancellation argument — it does not contradict the primary
  report and is not separately cited beyond this corroboration.
- **Citation mandate for `/speckit-plan` (Clarifications, 2026-08-21)**:
  the `/speckit-plan` phase MUST explicitly re-verify the corrected
  `d = |V| + 2|E|` encoded-parameter scaling (FR-002) against the primary
  source PDF (`docs/references/equivariant FCE Z2LGT report.pdf`,
  §5.3/eq. 26's register-sizing and multiplicity derivation) in-session —
  not merely restate the number from this spec or from the secondary
  Gemini-transcript source — per Constitution §2.2/§2.5's discipline that
  every physics/convention claim be verified against a cited source before
  being relied upon.
- **Terminology correction**: the original request's phrase "the ambient
  frequency set (`Λ`)" conflated two distinct objects. Per Theorem 6.1 and
  Constitution §11.0/§11.4, `Λ` is the symmetry-*restricted* sublattice,
  strictly smaller than the separate, larger, symmetry-unaware ambient
  frequency box that Specs 1–4 already use. This spec's requirements and
  success criteria use `Λ` and "ambient" as two distinct terms throughout,
  with the corrected three-way relationship `Ω ⊆ Λ ⊊ ambient` (FR-009
  through FR-013), rather than treating `Λ` itself as the ambient set.
- State preparation (the Gauss-law eigenstate initial state, report §5.4)
  and the Wilson-loop observable (report §5.5) are out of scope for this
  spec — this feature is about the encoding circuit's construction and
  its frequency-support containment, not about running dynamics or
  generalization checks (Spec 6's existing territory). A future spec may
  integrate this ansatz into Spec 6's experiment pipeline.
- The exact size (vertex/edge count) of the "small tractable instance(s)"
  used for containment verification (FR-010/FR-011) is a
  `/speckit-plan`-level decision, bounded only by keeping brute-force
  oracle extraction (Spec 4) tractable and by Constitution §11.5's
  requirement that its cost be predicted and logged before it is paid.
- Pure-gauge (no-matter) and matter-only (no-link) degenerate instances
  are not this spec's headline containment claim (Critical Mandate 3
  requires the full matter+gauge instance) but must not crash
  construction (Edge Cases).
