# Feature Specification: Symmetry Verification Layer

**Feature Branch**: `007-symmetry-verification-layer`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Symmetry Verification Layer for FCE. Deliverables: (a) An algebraic verification engine that consumes a SymmetryDeclaration and rigorously proves it satisfies Constitution §11.1 (symmetries must be internal, Abelian, and non-annihilating). (b) A classical validation hook that rejects invalid symmetry declarations before any quantum circuit compilation occurs. CRITICAL MANDATES: 1. Pure Algebra, No Quantum Execution: The symmetry verification must be purely algebraic (manipulating Pauli strings and commutators via qiskit.quantum_info). It MUST NOT execute quantum circuits or use Statevector to 'test' symmetries. 2. Generic Architecture: The engine must be agnostic to the specific physics model. It must verify the symmetry rules generically, paving the way for the specific Z2 LGT ansatz in the next spec."

## Clarifications

### Session 2026-08-21

- Q: Is "internal" (§11.1(a)) correctly operationalized as "the generator
  acts uniformly across every declared site" (this spec's original
  FR-001 wording)? → A: **No — a critical physics error, not a
  refinement.** That operationalization would wrongly *reject* the `Z₂`
  Gauss law, the exact local gauge-symmetry generator Constitution §11.0
  names as this research programme's own validation platform: a Gauss
  law generator `G_v` is declared **per lattice vertex `v`** (a product of
  Pauli operators over the links incident to `v`), so two different
  vertices carry genuinely different generators — the opposite of
  "uniform across sites." "Internal" does not mean spatially uniform; it
  means each declared generator is a **fixed operator on the Hilbert
  space, independent of the classical input selection** (the encoded
  parameter `alpha`) — Constitution §11.1(a)'s own rationale is explicit
  about what "internal" excludes: *"a label-acting symmetry acts on the
  classical input, restricting admissible inputs and collapsing the
  concept class"* — restricting which classical inputs are admissible is
  the failure mode, not spatial non-uniformity of the operator itself. A
  site-indexed, per-vertex generator like the Gauss law is exactly as
  "internal" as a site-uniform one, provided neither depends on the
  classical input. FR-001 is corrected below, and explicitly states the
  `Z₂` Gauss law MUST pass this check.
- Q: Should FR-002's non-annihilating check be validated only against
  hypothetical, unnamed negative controls, or against a concrete case
  already implicated in this project's own theory? → A: **Grounded in a
  concrete, named case.** Constitution §11.1(b)'s own rationale already
  names the mechanism: *"annihilating a term deletes its dynamics;
  deleting gauge-field dynamics freezes the links and yields a
  classically simulable free-fermion family."* The concrete instance of
  this failure mode is a naive candidate symmetry built from a **global
  `Z`-twirl** (symmetrizing by a global `Z`-type operator) checked against
  the lattice gauge theory's own gauge-field Hamiltonian term `H_g`: a
  `Z`-twirl anticommutes with `H_g`, so symmetrizing by it would silently
  annihilate the gauge-field dynamics entirely — precisely the failure
  §11.1(b) exists to catch. FR-002 now mandates this exact case as a
  required negative control, not an arbitrary or hypothetical one.
- Q: Should User Story 1's genericity test (Acceptance Scenario 5) use an
  arbitrary, unrelated second toy model, or the actual physics this
  research programme targets? → A: **The actual physics.** An arbitrary
  toy model would prove genericity in principle but would not prove the
  engine gives the *theoretically correct verdict on the case this
  project actually cares about* — Constitution §11.0 names `Z₂` lattice
  gauge theory as this programme's own validation platform. Acceptance
  Scenario 5 is corrected to require a small fragment of the actual `Z₂`
  LGT Hamiltonian (the Gauss law generator(s) plus a few gauge-field Pauli
  terms, including `H_g`) as one of the (at least two) structurally
  different models the genericity test exercises, alongside TFIM — not a
  substitute for TFIM, an addition to it.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature is the first to give real algebraic teeth to Spec 6's
  `SymmetryDeclaration` (User Story 3 there: "an optional, additive attach
  point... never evaluated by this feature"). Its "users" are the
  developers who will implement Constitution §11's actual equivariant,
  Pauli-encoded ansatz for lattice gauge theory in a *later* spec, and who
  need §11.1's three legality conditions (internal, non-annihilating,
  Abelian) checked and enforced *before* that ansatz work begins — on
  whichever physical model is declared, not only the eventual Z2 LGT one.
-->

### User Story 1 - Algebraically verify a declared symmetry against Constitution §11.1 (Priority: P1)

A developer who has declared a candidate symmetry for a physical model
(Spec 6's `SymmetryDeclaration`, now carrying the generator(s) needed to
reason about it algebraically) wants a rigorous, purely algebraic proof —
manipulating Pauli strings and their commutators only — of whether that
symmetry actually satisfies all three of Constitution §11.1's conditions:
internal, non-annihilating, and Abelian. When it does not, they need to
know exactly which condition failed and why, not just a bare rejection.

**Why this priority**: This is the foundational deliverable — every other
capability in this spec (the classical validation hook) exists to act on
this engine's verdict. Without it, "verify a symmetry" is not a capability
that exists anywhere in this codebase, and Constitution §11.1's own
requirement ("checked in the spec before implementation") has no
mechanical enforcement at all.

**Independent Test**: Can be fully tested by declaring several symmetries
against a small, explicit Hamiltonian term list — one that genuinely
satisfies all three §11.1 conditions, and one deliberately constructed
negative control for each condition (fails internal only; fails
non-annihilating only; fails Abelian only) — and confirming the engine
accepts the first and rejects each negative control with the specific
condition that failed.

**Acceptance Scenarios**:

1. **Given** a symmetry declaration and a Hamiltonian's own list of
   declared terms, **When** the engine verifies it, **Then** it checks all
   three of §11.1's conditions using only Pauli-string algebra (e.g.
   commutator/anticommutator relations) — never by constructing or
   executing a quantum circuit, and never by inspecting a `Statevector`.
2. **Given** a symmetry whose generator's action depends on, or would
   restrict, which classical input (encoded parameter) is admissible
   (fails "internal" — Clarifications, 2026-08-21: this is about
   classical-input independence, never about spatial uniformity across
   sites), **When** the engine verifies it, **Then** it rejects the
   declaration and records "internal" as the specific failed condition
   (Constitution §8.4). A site-indexed, per-vertex generator (e.g. the
   `Z₂` Gauss law generator `G_v`, declared once per lattice vertex `v`,
   genuinely different at different vertices) MUST still pass this check —
   site-to-site variation in the generator is not itself a failure.
3. **Given** a symmetry generator that anticommutes with at least one
   declared Hamiltonian term (fails "non-annihilating"), **When** the
   engine verifies it, **Then** it rejects the declaration and records
   "non-annihilating" as the failed condition, naming the specific term
   that anticommutes. **Required concrete case (Clarifications,
   2026-08-21)**: a naive candidate symmetry built from a global `Z`-twirl,
   checked against a lattice gauge theory's own gauge-field Hamiltonian
   term `H_g`, MUST be correctly flagged as failing this condition — the
   `Z`-twirl anticommutes with `H_g`, and symmetrizing by it would
   silently annihilate the gauge-field dynamics entirely (the exact
   mechanism Constitution §11.1(b)'s own rationale names: "deleting
   gauge-field dynamics freezes the links and yields a classically
   simulable free-fermion family").
4. **Given** a symmetry declared with two or more generators that do not
   all pairwise commute (fails "Abelian"), **When** the engine verifies
   it, **Then** it rejects the declaration and records "Abelian" as the
   failed condition, naming the specific pair of generators that do not
   commute.
5. **Given** a symmetry that satisfies all three conditions, **When** the
   engine verifies it against structurally different physical models
   (Generic Architecture mandate), **Then** the same, single verification
   engine accepts each, with no branch keyed to which physical model
   produced the declaration or its Hamiltonian terms. **Required test
   models (Clarifications, 2026-08-21 — not an arbitrary, unrelated toy)**:
   a small Transverse-Field Ising Model instance, **and** a small fragment
   of the actual `Z₂` lattice gauge theory Hamiltonian (at least one Gauss
   law generator `G_v` plus a few gauge-field Pauli terms including
   `H_g`) — proving the engine gives the theoretically correct verdict on
   the physics this research programme (Constitution §11.0) actually
   targets, not only on physics unrelated to it.

---

### User Story 2 - Reject an invalid symmetry declaration before any circuit compilation (Priority: P2)

A developer constructing a physical model (Spec 6) who attaches a
symmetry declaration to it wants that declaration checked immediately, at
model-construction time — classically, with no quantum circuit ever
built — so an invalid declaration is caught and rejected before any
downstream compilation (Circuits Layer, Spec 3) is even attempted.

**Why this priority**: Depends on User Story 1's engine existing, but is
not optional polish — Constitution §11.1 requires this check "before
implementation," and the whole point of catching it early is to avoid
wasting compilation/execution effort validating physics that was never
legal to try in the first place. Ranked below User Story 1 because the
engine itself is the substantive, reusable deliverable; this story is
"wire it in early," a single integration point.

**Independent Test**: Can be fully tested by constructing a physical model
with an attached, deliberately invalid symmetry declaration and confirming
construction is rejected — with the specific failed condition surfaced —
before any circuit-compilation code path is reached; and confirming a
model with a valid declaration (or none at all) still constructs exactly
as before this feature existed.

**Acceptance Scenarios**:

1. **Given** a physical model description with an attached symmetry
   declaration that fails any one of §11.1's three conditions, **When**
   the model is constructed, **Then** construction is rejected before any
   circuit-compilation module is invoked, with the specific failed
   condition and its details surfaced in the rejection.
2. **Given** a physical model description with an attached symmetry
   declaration that satisfies all three conditions, **When** the model is
   constructed, **Then** construction succeeds exactly as it would without
   this feature.
3. **Given** a physical model description with no symmetry declaration
   attached at all, **When** the model is constructed, **Then** this
   feature's validation hook does not run at all and construction behaves
   exactly as Spec 6 already shipped it — the hook is additive, never a
   required step.

---

### Edge Cases

- What happens when a symmetry declaration names zero generators? Rejected
  as a degenerate declaration — a "symmetry" with no generator asserts
  nothing and cannot be meaningfully checked against any of §11.1's three
  conditions.
- What happens when a declared generator is the identity operator (a
  trivial, no-op "symmetry")? Rejected as degenerate for the same reason —
  it vacuously satisfies all three conditions without asserting any actual
  structure, and accepting it would let a meaningless declaration pass
  silently.
- What happens when the Hamiltonian's own declared term list is empty?
  "Non-annihilating" is vacuously satisfied (there is no term to
  anticommute with), but this is recorded explicitly as a vacuous pass,
  not presented identically to a genuine, substantively-checked pass
  (Constitution §8.3 — every result states what it does and does not
  establish).
- What happens when a symmetry fails more than one of the three
  conditions at once? The engine still evaluates and reports every
  condition it can algebraically check, not only the first one it happens
  to test — a caller fixing only the first reported failure should not be
  surprised by a second, previously-unreported one on the next attempt.
- What happens when the physical model's own declared Hamiltonian terms
  and the symmetry generator act on different numbers of qubits/sites
  (e.g. a generator declared for 4 sites checked against a 3-site model)?
  Rejected explicitly as a structural mismatch, distinct from and checked
  before any of §11.1's three substantive conditions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (revised, Clarifications 2026-08-21): The engine MUST verify,
  for a given symmetry declaration and a given Hamiltonian term list,
  whether the declared symmetry is **internal** (Constitution §11.1(a):
  acts trivially on lattice labels). **Correct operationalization: each
  declared generator MUST be a fixed operator on the Hilbert space,
  completely independent of the classical input selection (the encoded
  parameter `alpha`)** — never a generator whose action varies with, or
  which would restrict, the admissible classical input (§11.1(a)'s own
  rationale: a label-acting symmetry "acts on the classical input,
  restricting admissible inputs and collapsing the concept class").
  **This is explicitly NOT a requirement that the generator act
  uniformly/identically across every declared site** — a site-indexed
  generator declared once per site with genuinely different Pauli content
  at different sites (e.g. the `Z₂` Gauss law generator `G_v`, one per
  lattice vertex `v`) is still internal, and MUST pass this check, because
  each `G_v` remains a fixed, classical-input-independent operator. The
  engine only needs to reject a generator whose own declared content
  actually varies with, or is parameterized by, the classical input —
  never merely because it differs from site to site.
- **FR-002** (revised, Clarifications 2026-08-21): The engine MUST verify
  whether the declared symmetry is **non-annihilating** (§11.1(b): no
  Hamiltonian term is odd under it) — for every declared Hamiltonian
  term, the symmetry's generator(s) MUST commute with it; any term that
  anticommutes with any generator fails this condition, and that specific
  term MUST be identified in the result. **Required concrete negative
  control**: a global `Z`-twirl candidate symmetry checked against a
  lattice gauge theory's own gauge-field Hamiltonian term `H_g` MUST be
  correctly flagged as failing this condition (the `Z`-twirl anticommutes
  with `H_g`; symmetrizing by it would annihilate the gauge-field
  dynamics — the exact mechanism §11.1(b)'s own rationale names, not a
  hypothetical case).
- **FR-003**: The engine MUST verify whether the declared symmetry is
  **Abelian** (§11.1(c): 1-d irreps) — every pair of the symmetry's
  declared generators MUST pairwise commute; any non-commuting pair fails
  this condition, and that specific pair MUST be identified in the result.
- **FR-004** (**Pure Algebra, No Quantum Execution**): The engine MUST
  perform all three checks (FR-001, FR-002, FR-003) using only Pauli-string
  algebra (commutator/anticommutator relations over `qiskit.quantum_info`
  Pauli/operator representations) — it MUST NOT construct or execute a
  `QuantumCircuit`, and MUST NOT import or invoke `Statevector`, `Operator`,
  or `expm` — mechanically enforced by the Foundation Layer's existing CI
  import guard (which already recursively scans this feature's own new
  module and requires no modification, unlike Spec 6's narrowly-scoped
  exception — this feature needs no such exception at all).
- **FR-005** (**Generic Architecture**): The engine MUST be implemented as
  a single code path with no branch keyed to which physical model produced
  the symmetry declaration or Hamiltonian term list — verified by running
  the identical engine against at least two structurally different
  physical models in this feature's own test suite (User Story 1
  Acceptance Scenario 5), not merely asserted.
- **FR-006**: The engine MUST report every one of the three conditions it
  evaluated and their individual pass/fail outcome — not only the first
  failure encountered — so a caller sees the complete picture on every run
  (Edge Cases).
- **FR-007**: Every rejection MUST record its specific failure mode
  (Constitution §8.4): which condition(s) failed, and for
  non-annihilating/Abelian failures, the specific term or generator pair
  responsible — never a bare "invalid symmetry" with no further detail.
- **FR-008**: The engine MUST reject a degenerate declaration (zero
  generators, or a declared generator equal to the identity operator)
  explicitly, rather than allowing it to vacuously "pass" all three
  conditions unremarked (Edge Cases).
- **FR-009**: The engine MUST reject, as a structural mismatch checked
  before the three substantive §11.1 conditions, a symmetry declaration
  and Hamiltonian term list that disagree on the number of qubits/sites
  they are declared over.
- **FR-010** (**Classical Validation Hook**): Constructing a physical model
  (Spec 6) with an attached symmetry declaration MUST invoke this
  feature's verification engine, and MUST reject model construction —
  before any circuit-compilation module (Spec 3) is invoked — if the
  declaration fails any of §11.1's three conditions or FR-008/FR-009's
  degenerate/mismatch checks.
- **FR-011**: Constructing a physical model with no symmetry declaration
  attached, or with one that passes all checks, MUST behave exactly as
  Spec 6 already shipped it — this feature's hook is additive and MUST NOT
  change behavior for either case.
- **FR-012**: Spec 6's `SymmetryDeclaration` MUST be extended with the
  generator data (one or more Pauli strings, and the qubits/sites each
  acts on) this engine needs to perform FR-001..FR-003's checks — its
  existing `name`/`description` fields and its status as an optional,
  additive attach point on a physical model are unchanged; only new fields
  are added, so every existing call site from Spec 6's own test suite
  continues to construct a valid `SymmetryDeclaration` unchanged.

### Key Entities *(include if feature involves data)*

- **Symmetry verification result**: The engine's output for one
  declaration — an overall accept/reject verdict, the individual
  pass/fail outcome of each of the three §11.1 conditions (FR-006), and,
  for any failure, the specific term or generator pair responsible
  (FR-007).
- **Symmetry declaration (extended)**: Spec 6's existing attach point,
  now additionally carrying one or more generator Pauli strings and the
  qubits/sites each acts on (FR-012) — the actual algebraic content this
  feature's engine consumes.
- **Hamiltonian term list**: The physical model's own declared Pauli
  terms (already produced by Spec 6's model-construction capability) —
  reused as this engine's other input, not re-derived or redeclared by
  this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can submit a symmetry declaration and a
  Hamiltonian term list and receive a definite accept/reject verdict
  covering all three of Constitution §11.1's conditions, with every
  rejection naming its specific failure mode.
- **SC-002**: No verification this feature's own test suite exercises ever
  constructs or executes a quantum circuit, or imports `Statevector`,
  `Operator`, or `expm` — verified by the Foundation Layer's existing CI
  import guard, with zero new violations and zero new exemptions
  introduced.
- **SC-003** (revised, Clarifications 2026-08-21): The same, single
  verification engine correctly accepts a valid symmetry and correctly
  rejects each of the three single-condition negative controls
  (internal-only failure; non-annihilating-only failure — including the
  required `Z`-twirl-vs-`H_g` case; Abelian-only failure) on both TFIM
  and a small fragment of the actual `Z₂` LGT Hamiltonian (Gauss law
  generator(s) plus gauge-field terms), with no model-specific code path,
  and correctly accepts the `Z₂` Gauss law itself as internal despite its
  site-indexed, non-uniform generator content.
- **SC-004**: Constructing a physical model with an invalid attached
  symmetry declaration is always rejected before any circuit-compilation
  module runs; constructing one with no declaration, or a valid one,
  always behaves identically to Spec 6's own already-shipped behavior.
- **SC-005**: A degenerate declaration (zero generators, or an
  identity-operator generator) is always rejected explicitly, never
  silently accepted as vacuously valid.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1),
  Encodings Layer (Spec 2), Circuits Layer (Spec 3), Extract Layer
  (Spec 4), Learning Backend Layer (Spec 5), and Experiment and Models
  Layer (Spec 6: `SymmetryDeclaration`, `PhysicalModelDescription`,
  `build_tfim_model`) — none of these are re-specified here.
- **`SymmetryDeclaration` must be extended, not replaced (FR-012).** Spec
  6 built this attach point specifically so a later spec could give it
  real algebraic content (Spec 6 User Story 3's own stated purpose); this
  is that later spec. The extension is additive (new fields with sensible
  requirements, not a redesign of the existing `name`/`description`
  fields or of `PhysicalModelDescription`'s own optional-attachment
  behavior).
- **This spec implements none of Constitution §11's equivariant ansatz
  itself.** It only implements §11.1's legality *check* — the next spec in
  this research programme (the specific `Z₂` lattice-gauge-theory ansatz,
  per §11.0) is what this feature's genericity requirement (FR-005) exists
  to make straightforward, not something this feature builds.
- **(revised, Clarifications 2026-08-21)** The exact algebraic mechanism
  used to confirm a declared generator is classical-input-independent
  (FR-001's corrected definition) is a `/speckit-plan`-level decision —
  for a `SymmetryDeclaration` whose generator is represented as static,
  already-fixed Pauli-string data (not a parameterized expression in
  `alpha`), this may reduce to a check on the declaration's own data
  representation rather than a nontrivial algebraic derivation; this spec
  requires only that whatever mechanism is chosen is purely algebraic
  (FR-004), generic (FR-005), never conflates classical-input-independence
  with spatial uniformity across sites, and correctly accepts the `Z₂`
  Gauss law.
- A precise, citable Pauli-operator convention for the `Z₂` LGT Gauss law
  generator `G_v` and the gauge-field term `H_g` (e.g. which Pauli letter
  represents the "electric field" degree of freedom on a link, per this
  research programme's own conventions) is a `/speckit-plan`-level
  verification task (Constitution §2.2/§2.5: verified in-session against a
  cited source before being relied upon) — this spec requires only that
  `G_v` is site-indexed (declared per vertex) and that `H_g` is a
  gauge-field Hamiltonian term the Gauss law must commute with and a
  naive `Z`-twirl must not.
- The exact data representation of a "Hamiltonian term list" (e.g., reusing
  Spec 6's `CouplingGroup`/`CouplingGroupTerm` shape directly, or a
  flattened Pauli-string list derived from it) is a `/speckit-plan`-level
  decision — this spec requires only that it is Spec 6's own existing
  model output, not a new, independently-invented representation.
- This feature validates against small, explicit, hand-constructed
  Hamiltonian term lists and symmetry declarations (including the
  mandated negative controls, User Story 1) — no production-scale lattice
  is targeted here.
