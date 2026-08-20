# Feature Specification: FCE Foundation Layer

**Feature Branch**: `001-fce-foundation-layer`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Foundation layer for a shot-based implementation of Barthe's Fourier Coefficient Extraction. Deliverables: (a) a typed contracts module defining the Protocols for every cross-layer boundary; (b) an intermediate representation for Pauli-encoded parameterised circuits, carrying per-parameter upload counts and per-parameter coefficients, with parameter multiplicity representable; (c) a single frequency-convention module that is the sole source of truth for frequency sign, pre-/post-parity indexing, two's-complement decoding, and coordinate ordering; (d) an exact reference oracle computing Fourier coefficients by Nyquist-grid evaluation and d-dimensional FFT, quarantined per constitution; (e) the CI check that fails the build if any production module imports Statevector, Operator, expm, or reference. Validation: the oracle reproduces analytically known coefficients for single-upload and two-upload cases, including a case with genuinely complex coefficients."

## User Scenarios & Testing *(mandatory)*

<!--
  This feature's "users" are the developers who build the downstream layers of the
  FCE pipeline (`ir → encodings → circuits → extract → backends → learn → models →
  experiment`, per Constitution §9.1). The foundation layer's value is measured by
  whether those developers can build and validate their layer independently, against
  a stable contract, without reading or waiting on any other layer's implementation.
-->

### User Story 1 - Build any layer against a stable typed contract (Priority: P1)

A developer implementing the two boundaries this foundation spec actually crosses —
an encoding producing the IR, and the reference oracle consuming it — needs a typed
Protocol for each of those boundaries, and a shared representation of a Pauli-encoded
parameterised circuit that already carries per-parameter upload counts, per-parameter
coefficients, and parameter multiplicity — so they can write and test each side in
isolation. Protocols for pipeline layers that do not exist yet (circuits, extract,
backends, learn, models, experiment) are added later, by their own specs, through a
documented extension point in this module — this spec does not pre-define them.

**Why this priority**: Nothing else in the pipeline can start without this. It is the
single dependency every other layer's spec and implementation will cite (Constitution
§9.2), and it is what makes independent, parallel layer development possible at all.

**Independent Test**: Can be fully tested by writing a minimal fake implementation of
the `Encoding` Protocol (a stub encoder) and one IR instance (a Pauli-encoded circuit
with a tied, multiplicity->2 parameter), and verifying both type-check against the
contracts module and round-trip through the IR's accessors with the correct upload
count, coefficient, and multiplicity recovered.

**Acceptance Scenarios**:

1. **Given** the contracts module, **When** a developer implements the `Encoding`
   Protocol for a concrete encoding, **Then** the implementation is accepted by static
   type checking without modifying the contracts module.
2. **Given** an intermediate representation instance for a circuit where two Pauli
   strings share one parameter index with multiplicity `r_j = 2`, **When** the IR is
   queried for that parameter's upload count and multiplicity, **Then** it reports the
   tied structure correctly and does not allow the two strings to be given independent
   parameters (Constitution §11.2).
3. **Given** an IR instance with per-parameter coefficients, **When** those
   coefficients are read back, **Then** they match what was supplied at construction,
   for both single-upload and multi-upload parameters.
4. **Given** the contracts module's documented extension point, **When** a later spec
   adds a Protocol for a not-yet-existing layer (e.g. circuits or backends), **Then** it
   does so without modifying the `Encoding -> IR` or `IR -> Oracle` Protocols already
   defined here.

---

### User Story 2 - Consult one authoritative source for frequency conventions (Priority: P2)

A developer working on any layer that produces or consumes a frequency (encodings,
extract, learn, experiment) needs one module that fixes frequency sign, pre-/post-parity
indexing, two's-complement decoding, and coordinate ordering, so that two layers can
never silently disagree on what a given integer or index means.

**Why this priority**: A convention mismatch between layers is a correctness defect
that is invisible until two layers are composed and produces a plausible-looking wrong
answer — exactly the failure mode Constitution §10.1 prohibits. Fixing it once, early,
in a single importable place is cheaper than discovering it later.

**Independent Test**: Can be fully tested standalone by feeding the convention module a
set of hand-derived integer frequencies and index positions and checking that sign,
parity annotation, two's-complement decoding, and coordinate order all match worked-by-hand
expected values — with no dependency on the IR, contracts, or oracle.

**Acceptance Scenarios**:

1. **Given** a frequency index in pre-parity form, **When** it is converted to
   post-parity form via the convention module, **Then** the result matches a
   hand-derived value, and the pre-parity count and post-parity count are each
   labeled with their annotation rather than treated as interchangeable (§6.2).
2. **Given** a signed frequency encoded in two's-complement, **When** it is decoded via
   the convention module, **Then** the decoded integer and its sign match the
   hand-derived expected value.
3. **Given** a multi-dimensional frequency tuple, **When** its coordinates are ordered
   via the convention module, **Then** the resulting order is the same regardless of
   which layer requested it.

---

### User Story 3 - Validate any layer against an exact ground truth (Priority: P3)

A developer who has built a layer needs an exact reference computation of the Fourier
coefficients a given Pauli-encoded circuit produces, so they can test that layer's
output against ground truth before composing it with anything else (Constitution §4.1).

**Why this priority**: Useful once the contracts/IR/convention foundation exists to
describe what is being validated, but the oracle itself is an isolated, independently
testable component — it can be built and validated against hand-derived analytic cases
without any shot-based or circuit-execution layer existing yet.

**Independent Test**: Can be fully tested standalone by running the oracle on a small,
fully specified Pauli-encoded circuit description with a known analytic Fourier
coefficient set (single-upload and two-upload cases) and diffing its output against the
hand-derived values, with no dependency on shot-based extraction.

**Acceptance Scenarios**:

1. **Given** a single-upload Pauli-encoded circuit whose Fourier coefficients are known
   analytically, **When** the oracle evaluates it on a Nyquist-sufficient grid and
   applies the d-dimensional FFT, **Then** the returned coefficients match the analytic
   values to floating-point precision.
2. **Given** a two-upload Pauli-encoded circuit that inserts a fixed, non-parameterised
   symmetry-breaking gate (e.g. an `S` gate) between its two `Z`-rotation uploads of the
   same parameter — breaking the `α -> -α` symmetry that would otherwise make the
   encoded function even and its coefficients real — so its Fourier coefficients are
   known analytically and are genuinely complex (nonzero real and imaginary parts on at
   least one non-DC coefficient), **When** the oracle evaluates it, **Then** the
   returned coefficients match the analytic complex values to floating-point precision
   (Constitution §4.3 — the test must not pass on a degenerate, even/real-only case).
3. **Given** the oracle module, **When** any production module (outside the oracle's
   own module and test helpers) attempts to import it, **Then** this is flagged as a
   constitutional violation to be caught by the CI check in User Story 4.

---

### User Story 4 - Automatically block exact-computation leakage into production (Priority: P4)

A developer or reviewer needs an automated build check that fails whenever a production
module imports `Statevector`, `Operator`, `expm`, or the reference oracle module, so
that the measurement-only production path (Constitution §3.1, §3.3-3.4) is enforced
mechanically rather than by manual review discipline alone.

**Why this priority**: This check has no value until there is a reference oracle and a
notion of "production module" to check (Priorities 1-3), but once those exist, it is
cheap to add and closes off the most tempting and consequential shortcut in the whole
codebase.

**Independent Test**: Can be fully tested standalone by adding a throwaway production
module that imports one of the four forbidden symbols and verifying the check fails the
build, then removing the import and verifying the check passes.

**Acceptance Scenarios**:

1. **Given** a production module that imports `Statevector`, **When** the CI check
   runs, **Then** the build fails and identifies the offending module and import.
2. **Given** a production module that imports `Operator`, `expm`, or the reference
   oracle module, **When** the CI check runs, **Then** the build fails identically for
   each case.
3. **Given** a codebase with no production module importing any of the four forbidden
   symbols, **When** the CI check runs, **Then** the build passes.
4. **Given** the reference oracle module and its own test helpers, **When** the CI
   check runs, **Then** it does not flag the oracle's own internal use of the forbidden
   symbols as a violation.

---

### Edge Cases

- What happens when a parameter's declared multiplicity `r_j` does not match the number
  of Pauli strings actually tied to it in the IR? The IR must make this a detectable,
  invalid state rather than silently accepting an inconsistent structure. This layer
  unit-tests the `register_width(uploads, r_j)` formula itself for correctness (§6.3);
  the behavioral regression test that under-sizes a real register and asserts the
  resulting aliasing is detected is deferred to Spec 3 (Circuit Construction) — see the
  TODO in Assumptions — since no register exists until circuits are built.
- How does the frequency convention module handle a frequency count that is correct in
  pre-parity form but would look wrong if compared directly to a post-parity count?
  It must not "reconcile" the two by silently adjusting either number (§6.2).
- What happens when the reference oracle is asked to evaluate a circuit whose parameter
  count makes the Nyquist grid too large to be tractable? The cost must be predicted and
  logged, and the oracle must refuse to proceed past a configured budget without explicit
  confirmation, rather than silently running an expensive computation (§10.3).
- What happens when the CI import check encounters a module that imports the forbidden
  symbols only inside a test file or the oracle's own module? These are in-scope
  exclusions, not violations, and must not be flagged.
- What happens when two independently-written layers each define their own notion of
  frequency sign or coordinate order instead of importing the convention module? This is
  the specific failure this feature exists to prevent; the convention module must be the
  only place these are defined, and nothing downstream may redefine them.
- What happens if the oracle samples only the half-domain the parity result would seem
  to justify? It must not: doing so would make the parity claim untestable rather than
  falsified, silently converting a checked property into an assumed one (FR-020).
- What happens if `PauliTerm.to_gate()`'s sign convention is inverted relative to the
  encoding's own `e^{iπcαP}`? Every returned coefficient is silently conjugated
  (`l ↔ -l`) — indistinguishable from a correct result on a real-valued (single-upload)
  test, and caught only by FR-021's direct gate-equivalence test, not by any coefficient
  comparison alone. This is the same sign-convention failure mode that previously broke
  the "template_binding" work in the predecessor repository.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The contracts module MUST define a typed Protocol for each boundary this
  spec's scope actually crosses: `Encoding -> IR` (an encoding producing IR) and
  `IR -> Oracle` (the oracle consuming IR). It MUST NOT define Protocols for pipeline
  layers that do not yet exist (circuits, extract, backends, learn, models, experiment);
  those are added by their own specs as each layer is built (§9.1, §9.2).
- **FR-002**: The contracts module MUST document a stated extension point (e.g. a
  module-level convention or docstring) describing how later specs add their own
  Protocols to this module for the remaining pipeline layers, without modifying the
  `Encoding -> IR` or `IR -> Oracle` Protocols already defined here.
- **FR-003**: Encodings MUST be interchangeable purely by configuration against the
  `Encoding` Protocol, without modifying the contracts module or the layers that consume
  it (§9.2, §9.4).
- **FR-004**: The intermediate representation (IR) MUST represent a Pauli-encoded
  parameterised circuit together with, for every parameter: its upload count, its
  per-parameter coefficient(s), and its multiplicity `r_j` (§6.3, §11.3).
- **FR-005**: The IR MUST be able to represent multiple Pauli strings sharing exactly
  one parameter index (a tied parameter driving `r_j` gates), and MUST NOT permit a
  design where those strings receive independent parameters instead (§11.2).
- **FR-006**: The IR MUST represent per-parameter structure as data rather than as
  branching logic keyed on parameter count, so that one code path handles any number of
  parameters (§9.3).
- **FR-007**: The IR MUST NOT fold any per-parameter scaling factor (e.g. a Trotter
  step) into the frequency register it carries; the register counts integers only
  (§6.4).
- **FR-008**: A single frequency-convention module MUST be the sole source of truth for
  frequency sign, pre-/post-parity indexing, two's-complement decoding, and coordinate
  ordering (§6.1), pinned as follows:
  - The canonical internal representation is the pre-parity integer
    `l ∈ {-2L, ..., 2L}^d` (per coordinate, for that coordinate's upload bound `L`).
  - Post-parity relabeling (`l -> l/2`) is an explicit, separately named and annotated
    transform — never applied implicitly, and never conflated with the pre-parity value
    (§6.2).
  - Frequency sign is fixed as `l = Λ - Λ'`, i.e. accumulating `+1` for each even-parity
    contribution and `-1` for each odd-parity one, so `l` carries the same sign as the
    exponent in `e^{iπ c α l}`. No function may introduce an independent sign
    convention.
- **FR-009**: Every function in the codebase that produces or consumes a frequency MUST
  import sign, indexing, decoding, and ordering behavior from the frequency-convention
  module rather than redefining any of them locally (§6.1).
- **FR-010**: Register width MUST be computed from upload count and per-parameter
  multiplicity `r_j` by one named function, `register_width(uploads, r_j)`, in the
  convention module. This layer MUST unit-test that function's return values directly
  against hand-computed widths for representative `uploads`/`r_j` pairs (including
  `r_j > 1`). It MUST NOT attempt the behavioral aliasing regression test against a real
  register — that test requires a constructed circuit and is deferred to Spec 3 (Circuit
  Construction), per the TODO in Assumptions (§4.7, §6.3).
- **FR-011**: The reference oracle MUST compute exact Fourier coefficients for a given
  IR-described circuit by evaluating on a Nyquist-sufficient grid — per coordinate,
  `4 r_j L + 1` points over the full pre-parity domain (length 2 in native parameter
  units, not the length-1 half-domain a later parity argument would justify — see
  FR-020) — and applying a d-dimensional FFT, where `d` is the number of independent
  parameter indices and grid sizing never depends on parity (see Assumptions).
- **FR-012**: The reference oracle and any exact statevector/dense-matrix computation
  MUST be quarantined to a `reference.py` module (plus test helpers) and MUST NOT be
  imported by any production module (§3.3).
- **FR-013**: The reference oracle MUST predict and log the cost of its grid evaluation
  before running it, and MUST refuse to exceed a configured budget without explicit
  confirmation (§10.3).
- **FR-014**: A CI check MUST fail the build if any production module imports
  `Statevector`, `Operator`, `expm`, or the reference oracle module (§3.4).
- **FR-015**: The CI check MUST exclude the reference oracle's own module and its test
  helpers from being flagged for using the four forbidden symbols internally.
- **FR-016**: The reference oracle MUST reproduce analytically known Fourier
  coefficients for a single-upload test case, to floating-point precision.
- **FR-017**: The reference oracle MUST reproduce analytically known Fourier
  coefficients for a two-upload test case, to floating-point precision.
- **FR-018**: The two-upload validation case used to satisfy §4.3's non-triviality
  requirement MUST break the `α -> -α` symmetry that otherwise makes the encoded
  function even and its Fourier coefficients real — e.g. by inserting a fixed
  (non-parameterised) gate such as `S` between the two `Z`-rotation uploads of the same
  parameter — so that at least one non-DC coefficient has nonzero real and imaginary
  parts. A validation case lacking this symmetry-breaking gate is a defect: it would
  pass on a degenerate, real-only case and would not exercise the phase convention §4.3
  requires be checked.
- **FR-019**: This layer MUST pin the Qiskit and Aer versions its API surfaces are
  verified against, and MUST verify in CI that the installed environment actually
  matches that pin (§9.7). Full run-manifest scaffolding — recording hardware,
  timings, seeds, and config beside reportable outputs (§8.5) — is deferred to Spec 6
  (Experiment), the first layer that produces an actual experimental result to attach
  a manifest to; see the TODO in Assumptions. This layer only needs its own dependency
  pin verified, not a general-purpose manifest mechanism.
- **FR-020**: The reference oracle's Nyquist grid MUST sample the full pre-parity
  domain (length 2 in native parameter units) rather than the length-1 half-domain the
  parity result (every admissible pre-parity frequency is even) would, in principle,
  make sufficient. Every oracle validation test MUST assert that every *odd*
  pre-parity coefficient returned is zero to floating-point precision. Sampling the
  half-domain instead would bake the parity claim in as an unverified premise rather
  than a live, falsifiable check of the sparsity mechanism §11.7 relies on — exactly
  the kind of test §4.3 requires be able to fail.
- **FR-021**: `PauliTerm`'s mapping from this layer's encoding convention
  (`e^{iπ c α P}`) to a concrete Qiskit gate MUST be verified in-session against the
  installed Qiskit version (§9.7), not assumed: `PauliEvolutionGate(P, time=t)`
  implements `e^{-i t P}`, so the mapping is `t = -π c α`, not `t = c α`. This mapping
  MUST be covered by a direct `Operator`-equivalence test comparing the constructed
  gate, for a single-qubit `Z`-upload, against a hand-built rotation gate at the angle
  the encoding convention implies. A sign error here silently conjugates every
  returned frequency (`l ↔ -l`) and is invisible on any real-coefficient test —
  including FR-016's single-upload case — so it can only be caught structurally, not
  by inspection of a real-valued result.

### Key Entities *(include if feature involves data)*

- **Contracts module**: The typed Protocol definitions for the boundaries this spec
  crosses (`Encoding -> IR`, `IR -> Oracle`), plus a documented extension point for
  later specs to add Protocols for the remaining pipeline layers named in §9.1. Carries
  no Fourier or circuit logic of its own.
- **Pauli-encoded circuit IR**: The intermediate representation of a parameterised
  circuit. Key attributes per parameter: upload count, coefficient(s), and multiplicity
  `r_j` (how many Pauli strings are tied to that one parameter index).
- **Frequency convention**: The single named set of rules — sign, pre-/post-parity
  indexing, two's-complement decoding, coordinate ordering, and the register-width
  formula — that every frequency-producing or -consuming function must use.
- **Reference oracle**: The exact, quarantined computation that maps an IR-described
  circuit to its Fourier coefficients via Nyquist-grid evaluation and d-dimensional FFT.
  Ground truth for every other layer's validation; never imported by production code.
  Samples the full pre-parity domain so the parity result is a live check, not a
  baked-in premise (FR-020).
- **CI import guard**: The build check that inspects production modules for forbidden
  imports (`Statevector`, `Operator`, `expm`, the reference oracle) and fails the build
  if any are found outside their permitted scope.
- **Dependency version pin**: The pinned Qiskit/Aer/numpy versions this layer verifies
  against the installed environment (§9.7). Full run-manifest scaffolding (§8.5) is a
  Spec 6 concern, not this layer's — see the TODO in Assumptions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can implement a complete new encoding against the `Encoding`
  Protocol and the IR alone, without reading the oracle's implementation, and a later
  spec can add a Protocol for a not-yet-existing layer via the documented extension
  point without modifying the `Encoding -> IR` or `IR -> Oracle` Protocols.
- **SC-002**: The reference oracle's coefficients match hand-derived analytic values to
  floating-point precision (relative error ≤ 1e-9) for both the single-upload and the
  two-upload test case, including the case with genuinely complex coefficients.
- **SC-003**: Zero locations in the codebase outside the frequency-convention module
  define frequency sign, parity indexing, two's-complement decoding, or coordinate
  ordering independently.
- **SC-004**: A change that introduces a production import of `Statevector`, `Operator`,
  `expm`, or the reference oracle is caught and fails the build 100% of the time, before
  merge.
- **SC-005**: All four foundation components (contracts, IR, frequency convention,
  oracle) each pass their own isolated ground-truth or consistency test before any
  dependent layer's spec is written (§4.1, §4.5).
- **SC-006**: The `register_width(uploads, r_j)` function returns values matching
  hand-computed widths for every representative `uploads`/`r_j` pair in its unit tests
  (including `r_j > 1`). The behavioral regression test that under-sizes a real,
  constructed register and confirms the resulting aliasing is detected is deferred to
  Spec 3 (Circuit Construction) per the TODO in Assumptions.
- **SC-007**: A CI check confirms the installed Qiskit, Aer, and numpy versions match
  this layer's pin on every run. Full run-manifest scaffolding is deferred to Spec 6
  per the TODO in Assumptions — this criterion covers only this layer's own dependency
  pin, not a general manifest mechanism.
- **SC-008**: Every odd pre-parity coefficient returned by the oracle, in both the
  single-upload and two-upload validation cases, is zero to floating-point precision
  (absolute value ≤ 1e-9) — an assertion capable of failing, not an assumed property
  (FR-020, §4.3).
- **SC-009**: A dedicated test confirms `PauliTerm.to_gate()`, for a single-qubit
  `Z`-upload, is `Operator`-equivalent to a hand-built rotation gate at the angle the
  `e^{iπcαP}` encoding convention implies (`t = -π c α`); flipping the sign in the
  mapping fails this test (FR-021).

## Assumptions

- "Production module" means any module outside `reference.py` and test helpers, per
  Constitution §3.3 — this is the scope the CI import check (FR-014/FR-015) enforces.
- A Pauli-encoded parameterised circuit is the class of ansatz already implied by the
  constitution's Pauli-string/multiplicity language (§6.3, §11.2); this feature defines
  its representation, not a new encoding scheme.
- The dimension `d` of the reference oracle's grid and FFT is strictly the number of
  independent parameter indices after tying (i.e. the number of distinct parameters once
  multiplicity is accounted for) — a count, not a parity annotation. Per-coordinate
  Nyquist grid resolution is set independently, by that coordinate's own frequency
  range: `4 r_j L + 1` points in pre-parity form, spanning the *full* length-2 native
  domain per coordinate (not a length-1 half-domain — see FR-020, which requires the
  full domain specifically so the parity result is independently checked rather than
  assumed). Parity relabeling (§6.2) is a labeling step applied to already-computed
  coefficients after the FFT; it is never an input to grid size or FFT dimension.
- "Two-upload case" means a single parameter whose associated frequency is generated by
  two uploads (encoding repetitions) of that parameter, the smallest case beyond
  single-upload that can expose upload-count-dependent bugs.
- The CI check's mechanism (e.g. a static import scan versus a runtime check) and the CI
  platform it runs on are implementation choices left to the plan; this spec fixes only
  its observable behavior (fails the build under the stated conditions).
- No performance or scale target is set for this foundation layer beyond the cost-budget
  guard on the oracle (FR-013); its purpose is correctness and a stable interface, not
  throughput.
- Type checking (for "typed Protocols" and IR round-tripping) is verified by a static
  type checker as part of the test suite, consistent with the module being described as
  "typed" in the request.
- **TODO (deferred to Spec 3 — Circuit Construction)**: The regression test that
  deliberately under-sizes a tied (`r_j > 1`) parameter's register and asserts the
  resulting aliasing is detected (§6.3) is out of scope here, because no circuit or
  register exists in this foundation layer to under-size — only the `register_width`
  formula does, and it is unit-tested directly (FR-010). This test is blocked on Spec 3
  constructing an actual register from `register_width(uploads, r_j)`; that spec MUST
  include it before circuit construction is considered done (§4.7).
- **TODO (deferred to Spec 6 — Experiment)**: Full run-manifest scaffolding (§8.5) —
  recording hardware, timings, seeds, and config beside a reportable experimental
  output — is out of scope here, because this foundation layer produces no
  experimental output to attach a manifest to; it only has its own dependency pin to
  verify (FR-019). This is blocked on Spec 6 producing an actual reportable result;
  that spec MUST include full manifest scaffolding before any experiment result is
  reported (§4.7, §8.5).
