# Feature Specification: Experiment and Models Layer

**Feature Branch**: `006-experiment-models-layer`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Experiment and Models Layer for FCE. Deliverables: (a) The execution mechanism for the generalization check (evaluating dynamics at shifted parameters) that Spec 5 flags. (b) The classical-input model construction (e.g., TFIM graphs) that maps physical Hamiltonians into the learning pipeline. (c) The architectural attach points for Constitution §11's research programme (equivariant Z2 LGT ansatz, containment verification). CRITICAL MANDATES: 1. PAC-Bound Rigidity: Spec 6 performs an empirical generalization check. It MUST NOT mutate or 'upgrade' Spec 5's weight_space_translation_status. The analytical weight-space bound remains strictly out of scope until a dedicated theoretical spec addresses sensing-matrix conditioning. 2. Immutable Reports: Spec 6 must consume Spec 5's ErrorBoundingReport immutably. It can use the report to trigger the generalization check, but it cannot alter the report's original noise or Trotter bounds."

## Clarifications

### Session 2026-08-21

- Q: The original Assumptions section proposed a finite-shot proxy for
  "real dynamics" at the generalization check's shifted input (a finer
  Trotter step, or a direct re-measurement of the same Trotterized
  circuit) to avoid the CI import guard's blanket prohibition on
  `fourierlearn.reference`. Is that proxy scientifically valid? → A:
  **No — a fatal flaw, not a refinement.** Constitution §8.2's entire
  purpose is to detect whether a model's suspiciously good agreement with
  *exact* dynamics is a real capability or an artifact of interpolating
  imperfect (Trotter-approximate) training labels. Comparing the model's
  prediction against *another* Trotter-approximate value — however fine
  the step, however it's obtained — cannot distinguish those two cases:
  both a genuine capability and an artifact would track a closer
  approximation "well enough," so the check would pass either way and
  prove nothing. The comparison target must be genuinely exact. **Decision
  (Option 1 of the choices considered): grant a narrow, explicitly
  justified constitutional exception.** The generalization-check mechanism
  (User Story 1) is authorized to import `fourierlearn.reference` — and
  only `fourierlearn.reference` — strictly to compute the exact
  ground-truth dynamics value at the shifted input. It may never be used
  for training-set construction, feature-map construction, or any other
  purpose anywhere else in this feature or this project. The Foundation
  Layer's CI import guard (`tests/ci/test_no_forbidden_imports.py`) MUST be
  updated to whitelist this one specific module by name, with the
  scientific necessity of the exception documented directly in the guard's
  own code (not only in this spec) — the exemption list is widened from
  one module (`reference.py` itself) to two, each independently justified,
  not opened generally. FR-001, FR-002, Acceptance Scenario 1, the
  "measurement uncertainty" Edge Case, the "Generalization check result"
  Key Entity, SC-001, and the Assumptions section are all updated below;
  two new requirements (FR-011, FR-012) record the exception and the guard
  update explicitly. Because the comparison (a deterministic model
  prediction vs. a deterministic exact value) no longer involves any
  finite-shot measurement, the previous "inconclusive due to measurement
  uncertainty" outcome no longer applies — the check's outcome is now
  strictly binary (generalizes / refuted), with a separately identified
  boundary/degenerate case (an exactly-zero Trotter bound) rather than a
  noise-driven ambiguity.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature covers the last two named stages of Constitution §9.1's
  pipeline (`ir → encodings → circuits → extract → backends → learn →
  models → experiment`). Its "users" are the developers who (a) need Spec
  5's own explicitly-deferred "generalization check required" flag
  (FR-009) to actually resolve to something, rather than stay permanently
  unresolved, (b) want to describe a real physical Hamiltonian (starting
  with the Transverse-Field Ising Model, the standard entry point before
  Constitution §11's lattice-gauge-theory target) in its own domain
  vocabulary rather than by hand-building `PauliUpload`/`CouplingGroup`
  objects, and (c) are laying the groundwork for §11's research programme
  without yet implementing it — this spec's own scope is the *attach
  points*, not the equivariant ansatz itself.
-->

### User Story 1 - Resolve a flagged generalization check (Priority: P1)

A developer who has an `ErrorBoundingReport` from Spec 5 with
`generalization_check_required=True` and a `suspect_input` wants to
actually run the check that flag names — evaluating the fitted model's
agreement with real dynamics at a classical input shifted away from every
training input — and get back a verdict: does the model's suspiciously good
fit generalize, or was it an artifact (e.g., label interpolation at a
single training point)?

**Why this priority**: This is the single capability Spec 5 explicitly
deferred and left unresolved (Clarifications, 2026-08-20/21: "this spec is
responsible only for this policy — raising and recording that flag ... that
mechanism belongs to a downstream experiment layer"). Every other
deliverable in this spec is either a prerequisite for a *future* check of
this kind (User Story 2, giving the check something realistic to run
against) or forward-looking scaffolding (User Story 3) — this is the one
capability whose absence directly blocks a promise already made and shipped
in Spec 5.

**Independent Test**: Can be fully tested by taking a fitted model whose
`ErrorBoundingReport` has `generalization_check_required=True` and a known
`suspect_input`, running this feature's check at a classical input shifted
away from every training input used to fit that model, and confirming the
result states plainly whether the fit's earlier suspiciously good agreement
held up or was refuted — without ever modifying the original
`ErrorBoundingReport` object.

**Acceptance Scenarios**:

1. **Given** an `ErrorBoundingReport` with `generalization_check_required=True`
   and a `suspect_input`, **When** this feature runs the generalization
   check, **Then** it selects a classical input strictly shifted away from
   every training input the original model used, computes the genuinely
   exact ground-truth dynamics value there (Clarifications, 2026-08-21: via
   the narrowly-authorized, explicitly justified oracle access — never a
   finite-shot measurement of the same Trotter-approximate circuit, which
   cannot distinguish a real capability from an artifact), and reports
   whether the model's prediction at that shifted input agrees with the
   exact value to within the model's own reported Trotter bound.
2. **Given** the same `ErrorBoundingReport` object, **When** the
   generalization check runs to completion (pass or fail), **Then** the
   original report's `pac_bound`, `trotter_bound`, `noise_characterization`,
   and `scope_statement` fields are byte-for-byte unchanged from before the
   check ran — this feature only ever reads that report, never mutates it
   (Clarifications: "Immutable Reports").
3. **Given** the same completed generalization check, **When** its own
   result is inspected, **Then** `weight_space_translation_status` on the
   consumed report's `pac_bound` still reads exactly
   `"out_of_scope_requires_sensing_matrix_conditioning"` — this feature's
   empirical check never upgrades, resolves, or otherwise touches that
   field, because doing so would misrepresent an empirical check as having
   produced the analytical weight-space bound Spec 5 explicitly deferred
   (Clarifications: "PAC-Bound Rigidity").
4. **Given** an `ErrorBoundingReport` with `generalization_check_required=False`,
   **When** a caller asks this feature to run the check anyway, **Then** it
   still runs and reports a result — a caller is not forbidden from
   double-checking a model Spec 5's own policy did not flag, but the
   feature never runs this check *automatically* behind a caller's back
   merely because a report exists.

---

### User Story 2 - Construct a physical model in its own domain vocabulary (Priority: P2)

A developer who wants to learn a real physical Hamiltonian — starting with
the Transverse-Field Ising Model (TFIM) on an arbitrary graph, the standard
first target before Constitution §11's lattice-gauge-theory programme —
wants to describe it the way a physicist would (a graph of sites and
couplings, plus a transverse-field strength) and get back whatever this
project's encodings layer (Spec 2) already needs to build a circuit,
without hand-assembling `CouplingGroup`/`PauliUpload` objects themselves.

**Why this priority**: Depends on nothing in this spec (it is a pure
translation into Spec 2's already-existing input shapes), but is lower
priority than User Story 1 because Spec 5's already-shipped test fixtures
already exercise the full pipeline end to end without it — this story's
value is ergonomic and forward-looking (feeding realistic, recognizable
physics models into the pipeline), not unblocking something already
promised.

**Independent Test**: Can be fully tested by describing a small TFIM
instance (e.g., a 3-node path graph, one coupling strength, one field
strength) through this feature's own model-construction API, and confirming
the resulting `CouplingGroup`s/`PauliEncodedCircuitIR` are exactly what a
developer would have hand-built directly from the TFIM Hamiltonian's own
Pauli-term decomposition.

**Acceptance Scenarios**:

1. **Given** a graph of sites and couplings plus a transverse-field
   strength, **When** this feature constructs the model, **Then** it
   produces exactly the `ZZ`-coupling and `X`-field `CouplingGroup`s the
   TFIM Hamiltonian's own term structure implies — one group per distinct
   physical coupling constant to be learned (the graph's edges sharing one
   coupling constant; the field strength as a second, separate coupling
   constant), not one group per individual Pauli term.
2. **Given** the same TFIM model construction, **When** it is hand-checked
   against the TFIM Hamiltonian written out explicitly for a small instance,
   **Then** every declared term's Pauli string, qubits, and group
   membership matches the Hamiltonian's own decomposition exactly.
3. **Given** a graph with an isolated node (no edges), **When** the model
   is constructed, **Then** it succeeds — an isolated site under a
   transverse field alone is a physically valid (if trivial) instance, not
   an error condition.

---

### User Story 3 - Leave attach points for the symmetry-restricted research programme (Priority: P3)

A developer who will later implement Constitution §11's equivariant,
Pauli-encoded ansatz for lattice gauge theory (`Z₂` as the validation
platform, `U(1)` as the separation target) wants this spec's model and
experiment constructions to expose the specific extension points §11's own
rules already name — a symmetry declaration a model can carry, and a place
in an experiment's report to record a sparsity claim's mechanism and a
`Λ`-containment verification result — without this spec itself implementing
any of §11's actual equivariance machinery.

**Why this priority**: Explicitly scoped as forward-looking architecture,
not a working capability — lowest priority because nothing in User Stories
1-2 depends on it, and no §11 work is unblocked *by* it alone (§11's actual
implementation is its own future spec, per §11.0's "every spec states which
[target] it serves").

**Independent Test**: Can be fully tested by confirming the model
construction API (User Story 2) accepts an optional symmetry declaration
without requiring one, and that the experiment report structure (User Story
1) has a defined, named place for a future sparsity-mechanism/`Λ`-containment
record, even though no code path in this spec ever populates the symmetry
declaration with an internal/non-annihilating/abelian check (§11.1) or
performs `Λ`-enumeration (§11.4) or containment verification (§11.6) itself.

**Acceptance Scenarios**:

1. **Given** the model-construction API (User Story 2), **When** it is
   called without any symmetry declaration, **Then** it behaves exactly as
   before — the attach point is optional and additive, not a required
   parameter that changes existing behavior.
2. **Given** the same API called *with* a symmetry declaration, **When**
   the resulting model is inspected, **Then** the declaration is carried
   through unchanged as data on the model, and this spec raises neither an
   error nor a false claim of having checked §11.1's three conditions
   (internal, non-annihilating, abelian) against it — checking those
   conditions is explicitly out of scope here.
3. **Given** any generalization-check or experiment report this feature
   produces, **When** it is inspected for a sparsity or containment claim,
   **Then** no such claim is ever present unless a future spec's code
   populates it — this spec's own reports never claim a `Λ`-restriction or
   sparsity mechanism (§11.7) that this spec itself never computed.

---

### Edge Cases

- What happens when the generalization check's shifted input accidentally
  coincides with (or is numerically indistinguishable from) a training
  input? Rejected — the check requires a classical input genuinely shifted
  away from every training input, the same leakage-style guarantee Spec 5's
  own FR-005 already establishes for its own training/evaluation split; a
  degenerate "shift" that lands back on a training point is not a
  generalization test at all.
- What happens when the model's own reported Trotter bound is exactly zero
  (Clarifications, 2026-08-21 — the comparison threshold, now that the
  ground-truth side is a genuinely exact, deterministic value with no
  measurement noise of its own)? Any nonzero gap between the prediction and
  the exact value immediately refutes; an exactly-zero gap is a boundary
  tie the result must state explicitly as such (Constitution §8.4:
  negative/inconclusive results are documented, not silently resolved),
  rather than being silently classified either way.
- What happens when a caller passes an `ErrorBoundingReport` object to the
  generalization check and then inspects that *same* object afterward
  expecting it to now show a resolved status? It does not — the
  immutability guarantee (Acceptance Scenario 2) means the original report
  object is unchanged; any resolution this feature produces is returned as
  a new, separate result, never written back onto the consumed report.
- What happens when a TFIM model's graph has a coupling strength of exactly
  zero on some edge? That edge contributes no `CouplingGroup` term at all
  (a zero-coefficient Pauli term is already rejected elsewhere in this
  project, Constitution/§6.4-adjacent convention: a zero coefficient has no
  well-defined period) — the model construction must reject a zero coupling
  explicitly rather than silently passing it through to a downstream
  rejection with a less specific error.
- What happens when a symmetry declaration (User Story 3) is attached to a
  TFIM model that does not actually possess that symmetry? This spec does
  not check — verifying §11.1's three conditions is out of scope here, by
  design; the attach point exists so a *future* spec can perform that
  check, and this spec must not claim, imply, or silently assume the check
  has already happened.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (revised, Clarifications 2026-08-21): The feature MUST provide
  a mechanism that, given a fitted model's `ErrorBoundingReport` (Spec 5)
  and its `suspect_input`, selects a classical input strictly shifted away
  from every training input the original model was fit on, and computes
  the genuinely exact ground-truth dynamics value there via FR-011's
  narrowly-authorized oracle access — not finite-shot measurement of the
  Trotter-approximate circuit, which cannot serve as a valid comparison
  target for this check (Clarifications, 2026-08-21).
- **FR-002** (revised, Clarifications 2026-08-21): The mechanism MUST
  compare the fitted model's prediction at the shifted input against the
  exact ground-truth value computed there, and report whether the earlier
  suspiciously good agreement (the reason `generalization_check_required`
  was set) still holds (`generalizes`) or does not (`refuted`) relative to
  the model's own reported Trotter bound as the comparison threshold. Both
  sides of this comparison are deterministic (a fitted model's prediction;
  an exact oracle value) — there is no measurement-noise-driven
  "inconclusive" outcome; the one identified boundary case (an exactly-zero
  Trotter bound) is handled explicitly (Edge Cases; Constitution §8.4).
- **FR-003** (**Immutable Reports**, Clarifications): consuming an
  `ErrorBoundingReport` to trigger or inform the generalization check MUST
  NOT mutate that report object — its `pac_bound`, `trotter_bound`,
  `noise_characterization`, and `scope_statement` fields MUST be identical
  before and after the check runs, checked by a dedicated equality
  assertion, not merely assumed from the report's own immutable-dataclass
  construction (Spec 5 already makes `ErrorBoundingReport` a frozen
  dataclass — this requirement is about this feature's own behavior around
  it, not merely inheriting frozen-ness incidentally).
- **FR-004** (**PAC-Bound Rigidity**, Clarifications): this feature's
  generalization check MUST NEVER set, upgrade, or otherwise resolve
  `PacBound.weight_space_translation_status` away from its existing
  `"out_of_scope_requires_sensing_matrix_conditioning"` value. An empirical,
  shifted-input agreement check is not, and must never be presented as, the
  analytical weight-space error bound Spec 5 explicitly deferred — that
  bound remains out of scope until a dedicated theoretical spec addresses
  the sensing matrix's conditioning.
- **FR-005**: The feature MUST provide a model-construction capability that
  translates a classical-input physical-model description (starting with a
  Transverse-Field Ising Model on an arbitrary graph: sites, edges each
  carrying one coupling strength, and one transverse-field strength) into
  the `CouplingGroup`/`PauliUpload`-level input Spec 2's encodings layer
  already accepts — one distinct physical coupling constant (to be learned)
  per declared group, not per individual Pauli term.
- **FR-006**: The model-construction capability MUST reject a declared
  coupling strength of exactly zero with a clear, specific error (Edge
  Cases) rather than silently omitting the term or passing it through to a
  less specific downstream rejection.
- **FR-007**: The model-construction capability MUST accept an *optional*
  symmetry declaration as an additive attach point for Constitution §11's
  research programme, carried through unchanged as data on the constructed
  model. This feature MUST NOT check §11.1's three conditions (internal,
  non-annihilating, abelian) against a supplied declaration, and MUST NOT
  behave any differently when a declaration is present versus absent,
  beyond carrying the data through (Edge Cases; User Story 3).
- **FR-008**: Every report this feature produces (the generalization-check
  result, and any experiment-level summary) MUST have a defined, named
  place to record a future sparsity-mechanism classification (additive vs.
  multiplicative, §11.7) and a `Λ`-containment verification result (§11.6),
  and MUST leave that place empty/absent whenever this feature itself has
  not computed such a claim — never populated with an unearned or assumed
  value.
- **FR-009**: The generalization check's shifted-input selection MUST
  assert, after selection, that the chosen input does not coincide with (or
  fall within the same leakage tolerance as) any training input the
  original model used — checked explicitly, never assumed, mirroring Spec
  5's own FR-005 discipline for its training/evaluation split.
- **FR-010** (revised, Clarifications 2026-08-21): Every part of this
  feature other than the one module FR-011 names MUST NOT import or invoke
  `Statevector`, `Operator`, `expm`, or `fourierlearn.reference`
  (Constitution Article II/§1.1, §9.6) — this includes User Story 2's
  model construction, User Story 3's attach points, and any other module
  this feature adds. FR-011 defines the one, narrow, explicitly justified
  exception; this requirement is the general rule everything else remains
  bound by.
- **FR-011** (new, **Narrow Oracle Access**, Clarifications 2026-08-21): The
  generalization-check mechanism (FR-001/FR-002) is explicitly authorized
  to import `fourierlearn.reference` — and only for the single purpose of
  computing the exact ground-truth dynamics value at the shifted input
  selected by FR-001. This authorization is narrowly scoped to that one
  purpose in that one module: it MUST NOT be used for training-set
  construction, feature-map/sensing-matrix construction, or any other
  purpose anywhere else in this feature. A dedicated test MUST assert this
  scoping holds (e.g., that no other module in this feature imports
  `fourierlearn.reference`, and that this module's own use of it is
  confined to the exact-value computation).
- **FR-012** (new, **CI Guard Exception**, Clarifications 2026-08-21): The
  Foundation Layer's CI import guard
  (`tests/ci/test_no_forbidden_imports.py`) MUST be updated to whitelist
  the specific module FR-011 names, in addition to (not instead of) its
  existing `reference.py` exemption. The updated guard MUST document, in
  its own code, the scientific necessity of this second exemption (that a
  finite-shot or finer-approximation proxy cannot validly serve as the
  generalization check's comparison target — Clarifications, 2026-08-21) —
  not merely list the module name without justification. The guard's own
  test suite MUST gain a dedicated case confirming it still fires for every
  *other* module that attempts to import `fourierlearn.reference`, so the
  exemption is proven narrow, not a general widening of the rule.

### Key Entities *(include if feature involves data)*

- **Generalization check result** (revised, Clarifications 2026-08-21): The
  output of User Story 1's mechanism — the shifted classical input actually
  used, the exact ground-truth dynamics value computed there via FR-011's
  narrowly-authorized oracle access, the model's (deterministic) prediction
  there, the comparison outcome (`generalizes` / `refuted`, with the
  zero-Trotter-bound boundary case stated explicitly when it occurs), and
  an explicit statement that this result does not alter, and was not
  derived from mutating, the `ErrorBoundingReport` that triggered it.
- **Physical model description**: A classical-input, domain-vocabulary
  description of a Hamiltonian (first: TFIM — a graph of sites/edges, one
  coupling strength per edge or shared edge-group, one transverse-field
  strength), translated by this feature into Spec 2's
  `CouplingGroup`/`PauliUpload` input shape.
- **Symmetry declaration** (attach point only, User Story 3): optional data
  carried on a physical model description, naming a symmetry a future
  spec's equivariance check (§11.1) would evaluate — never evaluated by
  this feature itself.
- **Sparsity/containment record** (attach point only, User Story 3): a
  named, currently-always-empty place in this feature's reports where a
  future spec's `Λ`-containment verification (§11.6) and sparsity-mechanism
  classification (§11.7) would be recorded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (revised, Clarifications 2026-08-21): A developer can take any
  `ErrorBoundingReport` with `generalization_check_required=True` and
  obtain a definite `generalizes`/`refuted` verdict (or an explicitly
  stated boundary tie, Edge Cases) by comparing the model's prediction
  against the genuinely exact ground-truth dynamics value — computed via
  FR-011's narrowly-authorized oracle access — at a classical input
  genuinely shifted from every training input.
- **SC-002**: Running the generalization check never changes any field of
  the `ErrorBoundingReport` object it was given — verified by an exact
  before/after equality check on every run this feature's own test suite
  exercises.
- **SC-003**: `PacBound.weight_space_translation_status` reads the same
  `"out_of_scope_requires_sensing_matrix_conditioning"` value after every
  generalization check this feature's test suite runs, with zero instances
  of this feature setting it to anything else.
- **SC-004**: A developer can describe a TFIM instance by its graph and
  field strength alone and obtain the exact `CouplingGroup` structure a
  hand-built decomposition of that same Hamiltonian would produce.
- **SC-005**: The model-construction API accepts every existing call
  pattern (no symmetry declaration) unchanged after the symmetry-attach
  point (User Story 3) is added, and every report structure this feature
  defines has a named place for a future sparsity/containment record that
  remains empty in every case this feature's own suite exercises.
- **SC-006** (revised, Clarifications 2026-08-21): No production code path
  in this feature ever imports or invokes `Statevector`, `Operator`,
  `expm`, or `fourierlearn.reference`, **except** the one module FR-011
  names, whose sole use of `fourierlearn.reference` is confined to
  computing the generalization check's exact ground-truth value — verified
  by the Foundation Layer's CI import guard *after* it is updated (FR-012)
  to carry this one additional, documented exemption, with zero
  violations for every other module in this feature or elsewhere in the
  project.
- **SC-007** (new, Clarifications 2026-08-21): The CI import guard's own
  test suite demonstrates it still fires for any module other than
  `reference.py` or FR-011's named module that imports
  `fourierlearn.reference` — the exemption is proven narrow, not a general
  widening, by a dedicated passing test.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1), Encodings
  Layer (Spec 2: `CouplingGroup`/`PauliUpload`/`trotter_frontend`), Circuits
  Layer (Spec 3), Extract Layer (Spec 4), and Learning Backend Layer (Spec
  5: `ErrorBoundingReport`, `PacBound`, `LearnedModel`) — none of these are
  re-specified here.
- **Measurement-only discipline extends to this layer, with one narrow,
  explicitly justified exception (Clarifications, 2026-08-21 — supersedes
  this Assumption's original wording).** This feature adds its own new
  production module(s) under this project's source tree; the Foundation
  Layer's CI import guard already recursively scans the entire tree and
  forbids every production module except `reference.py` itself from
  importing `fourierlearn.reference` at all. The original version of this
  Assumption proposed working around that by comparing the model's
  prediction against a finite-shot proxy for "real dynamics" (a finer
  Trotter step, or a direct re-measurement of the same Trotterized
  circuit) — this was a **fatal flaw**, not a valid design choice: any
  Trotter-approximate comparison target, however close to exact, cannot
  distinguish a genuine capability from an artifact of interpolating
  imperfect training labels (Constitution §8.2's whole point), because
  both would appear to "pass" against it. The corrected decision (FR-011,
  FR-012): the generalization-check mechanism alone is granted a narrow,
  explicitly justified import exception to `fourierlearn.reference`, used
  strictly to compute the exact ground-truth value at the shifted input —
  never for training or feature construction anywhere in this feature.
  Every other module this feature adds remains fully bound by the
  measurement-only discipline (FR-010) with no exception.
- **Scope of the "models" deliverable is TFIM only, for now.** Constitution
  §11.0 names `Z₂` lattice gauge theory as the validation platform and
  `U(1)` as the separation target for the *research programme*; this
  spec's own model-construction deliverable (User Story 2) is scoped to
  TFIM as the standard, simpler entry point, with lattice-gauge-theory
  model construction deferred to whichever future spec actually implements
  §11's equivariant ansatz (User Story 3 only leaves attach points, it does
  not build LGT models).
- **§11 is not implemented by this spec.** User Story 3's attach points are
  additive, inert scaffolding — no code in this feature checks §11.1's
  three conditions, performs `Λ`-enumeration (§11.4), or verifies `Ω ⊆ Λ`
  containment (§11.6). That is explicitly a future spec's work, per §11.0's
  "every spec states which [target] it serves."
- **(revised, Clarifications 2026-08-21)** The generalization check's
  comparison threshold is the model's own already-reported
  `TrotterBound.structural_approximation_bound` (Spec 5) — not a freshly
  chosen or shot-count-derived tolerance — since both sides of the
  comparison (FR-002) are now deterministic. The exact module boundary
  (which file FR-011's exception applies to) and the precise CI-guard code
  change (FR-012) are `/speckit-plan`-level decisions; this spec requires
  only that the exception is narrow, named, and documented.
