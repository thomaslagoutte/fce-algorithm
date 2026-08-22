# Feature Specification: Cross-Topology Regression Layer

**Feature Branch**: `012-cross-topology-regression`

**Created**: 2026-08-22

**Status**: Draft

**Input**: User description: "Cross-Topology Regression Layer (the pipeline Spec 5 was originally meant to build). Deliverables: (a) A training-row abstraction where each row is (x_t, y_t) — a classical input/topology and its label — NOT (alpha_j, y_j) for one fixed circuit. (b) Feature extraction per training row via Spec 4's own extract_coefficients (the direct FCE Hadamard-test machinery, now post-Spec-11 execution-repaired), giving each row's b(x_t) as a genuine feature vector — explicitly NOT learn.py's estimate_y/compressed-sensing path, which answers the flipped, classically-easy direction (per this project's own Constitution and the thesis's Appendix-H RFF discussion) and must not be reused here. (c) A regression fitting w(alpha*) across the collected {(b(x_t), y_t)} pairs via LASSO, honestly under-determined (fewer graphs than frequencies, per Constitution §7.3) — this is the actual advantage-relevant learning task. (d) Prediction on a held-out x*: extract b(x*) via the same Spec-4 machinery, compute y-hat* = b(x*).w-hat. CRITICAL MANDATE: this spec exists BECAUSE Spec 5 drifted from this exact design during its own bug-fix process — research.md must document that history explicitly (Constitution §8.4, negative results recorded), and every claim distinguishing this pipeline's advantage-relevant direction from learn.py's flipped/easy direction must be verified before being asserted, per this project's standing discipline."

## Clarifications

### Session 2026-08-22 (pre-FR verification, per this project's standing discipline)

- **Source citation correction**: the user's own framing cites "the thesis's
  Appendix-H RFF discussion." Verified in-session against
  `docs/references/Barthe_thesis.pdf` (via `pdftotext`, not assumed from
  memory): the RFF discussion is **§5.7.10, "Flipped concept and connection
  to RFF"** (page 144, main body of Chapter 5) — there is no "Appendix H" in
  this thesis. §5.7.10 is cited by its actual location throughout this spec.
- **The flipped concept, verified directly from the source text (§5.7.10)**:
  the thesis defines `C̄ := {c_x : α → Σ_l b_l(x) e^{il·α}}_{x∈{0,1}*}` — "a
  scenario where a quantum circuit has some fixed, potentially unknown gates
  and some parameterized gates," where the `b_l(x)` are treated as a
  polynomially sized, KNOWN "advice" list, and the thing recovered is the
  function's dependence on `α` from point samples. The thesis states this
  concept "is classically efficiently learnable by a simple Fourier analysis
  of the data" and is exactly the scenario "dequantized by techniques like
  Random Fourier Features." This concept class is INVERTED relative to the
  one the thesis's own advantage arguments target (`C_U`, studied earlier in
  the same chapter): there, the classical input `x` varies and indexes which
  member of a family of circuits to query, `b(x)` is the genuinely
  quantum-extracted feature vector, and the UNKNOWN being learned is a
  weight vector over that feature space — not a per-input scalar recovered
  from bound-parameter samples of one fixed circuit.
- **The target linear model, verified directly from the source text
  (§5.7.8, eq. 5.79)**: "For consistency with earlier sections, we
  temporarily simplify notation and write `x = b(x)`, `w = w(α)` and
  `y = c_α(x)`" — giving the linear model `y = x^⊤w` (`w ∈ R^d` unknown).
  This confirms `w(α*)` (the label the user's own request uses) is the
  thesis's own notation for the unknown weight vector characterizing the
  target concept `α*` — not a per-training-row bound parameter value. The
  thesis's own §5.7.7/§5.7.8 solves this same linear model via kernel ridge
  regression (KRR, already implemented by Spec 10) without ever forming `w`
  explicitly; this spec's own deliverable (c) is a genuinely different,
  complementary strategy for the SAME linear model — an explicit, sparse
  (LASSO) solve for `w` itself, motivated by §5.7.9's own closing remark
  that efficient learnability follows "if the spectrum is sparse."
- **`learn.py`'s actual, current implementation, verified by reading the
  file directly**: `estimate_y` (FR-014 of Spec 5), `TrainingRow` (holding
  one `ir`/`alpha` pair bound to ONE FIXED circuit), `build_sensing_matrix`
  (the Fourier sensing matrix `A_{j,l}=exp(iπl·α_j)`), and
  `LassoRegressionBackend`/`fit_model` recover the coefficient vector `b`
  ITSELF via compressed sensing from `(α_j, y_j)` samples of one fixed
  circuit — this is precisely the flipped concept `C̄` above: `b_l(x)` (here
  playing the role of the thing recovered) treated as the unknown, and `α`
  (bound per row) as the varying, known sample point. This is a genuine,
  verified structural match, not an assumed analogy.
- **Spec 10 relationship, made an explicit FR (not only Assumptions
  prose)**: this spec (Spec 12) and Spec 10 (Quantum Kernel Method) solve
  the EXACT SAME linear model (thesis §5.7.8, eq. 5.79: `y = x^⊤w`) via
  two different routes — Spec 10's kernel ridge regression is the
  implicit/dual route (never forming `w` explicitly); Spec 12's LASSO fit
  is the explicit/primal/sparse route (solving for `w` directly). FR-013
  below states this relationship as a testable requirement, and SC-006
  requires a shared-fixture cross-check proving both routes solve the
  same problem: run both on the IDENTICAL fixture (same training graphs,
  same target concept `α*`, same held-out `x*`) and compare their
  predictions.
- **Frequency lattice alignment, made its own FR**: extracting `b(x_t)`
  across different topologies only produces a valid design matrix if
  every row's IR shares the exact same frequency lattice (identical
  encoded parameters, multiplicity, and canonical frequency list) — this
  was previously only implied by FR-008's Trotter-configuration framing.
  FR-014 below makes the general structural-alignment check (and its
  explicit rejection error on mismatch) its own, directly implementable
  requirement, checked against the actual IR/frequency structure rather
  than only `r`/`tau` equality.

## User Scenarios & Testing *(mandatory)*

<!--
  As with Specs 1-11, this is an internal pipeline-layer feature for this
  project's own learning stack (Constitution §9.1's `learn` stage) — "the
  user" is a developer building on top of the Extract Layer (Spec 4, now
  Spec-11-repaired), and the acceptance scenarios are stated in terms of
  the actual regression pipeline being built, matching this project's own
  established departure from the template's generic framing
  (checklists/requirements.md Notes documents this precedent).
-->

### User Story 1 - Build a training row from a classical input/topology, not a bound parameter (Priority: P1)

A developer has a family of classical inputs (topologies) `x_t` — each
selecting its own fixed gates within an otherwise-identical encoded-
parameter structure (Constitution §7.1) — and a label `y_t` for each, and
wants a training-row abstraction that pairs them as `(x_t, y_t)`. Each
row's feature vector `b(x_t)` must come from Spec 4's own
`extract_coefficients` — the genuine, quantum Hadamard-test-with-frequency-
shift machinery, now Spec-11-execution-repaired — compiling and measuring
a SEPARATE circuit per topology, never from binding a numeric value into
one fixed circuit and reading its bare expectation.

**Why this priority**: This is the foundational abstraction distinguishing
this pipeline from Spec 5's own, already-drifted design (Clarifications).
Every other deliverable (the LASSO fit, the held-out prediction) is
meaningless without training rows built this way — get this wrong and the
whole pipeline silently re-becomes the flipped, classically-easy direction
this spec exists to avoid.

**Independent Test**: Can be fully tested by declaring several distinct
classical-input topologies sharing one encoded-parameter structure,
extracting each one's `b(x_t)` via `extract_coefficients`, and confirming
each row's feature vector required a genuinely separate circuit
compilation and measurement (never a single shared circuit with only a
bound-parameter value differing between rows).

**Acceptance Scenarios**:

1. **Given** several classical-input topologies `x_1, ..., x_T` sharing one
   encoded-parameter structure, **When** a training row is built for each,
   **Then** each row's feature vector `b(x_t)` is obtained via a
   SEPARATE call to Spec 4's `extract_coefficients` on that topology's own
   compiled circuit — never via a shared circuit with only a bound
   numeric parameter value varying between rows.
2. **Given** `learn.py`'s existing `estimate_y`/`TrainingRow`/`build_sensing_
   matrix`/`LassoRegressionBackend`/`fit_model` (Spec 5's own, already-
   drifted implementation), **When** this feature's own training-row
   abstraction or feature extraction is implemented, **Then** none of
   those symbols are imported or reused — verified by an explicit,
   automated check, not merely by code review.
3. **Given** a training row's extracted `b(x_t)`, **When** it is used as a
   regression input, **Then** it is represented via the same real/
   imaginary conjugate-symmetric stacking convention this project already
   established (Constitution §7.6), computationally re-verified for THIS
   feature's own object (a per-topology extracted feature vector, not a
   sensing-matrix column) on a genuinely complex fixture before being
   relied upon.

---

### User Story 2 - Fit a sparse weight vector across topologies via LASSO, honestly under-determined (Priority: P2)

A developer who has collected `{(b(x_t), y_t)}` pairs across `T` classical
topologies wants to fit a sparse weight vector `w(α*)` (the thesis's own
notation, §5.7.8 — the unknown weight vector characterizing the target
concept, verified NOT to mean a per-row bound parameter) via LASSO, with
`T` (the number of topologies/graphs) honestly allowed to be far fewer
than `L` (the number of representable frequencies) — the actual
advantage-relevant regime Constitution §7.3 describes ("sample complexity
is logarithmic in the frequency count").

**Why this priority**: Depends on User Story 1's training rows existing,
but is the actual learning task this spec exists to deliver — the same
underlying linear model (`y = b(x)^⊤w`, thesis eq. 5.79) Spec 10's kernel
ridge regression already solves implicitly, but here solved explicitly
and sparsely, recovering `w` itself rather than only predictions.

**Independent Test**: Can be fully tested by building a small validation
case with a known, sparse ground-truth weight vector, collecting `T`
topologies' `(b(x_t), y_t)` pairs with `T` strictly fewer than the number
of representable frequencies, fitting LASSO, and confirming the fitted
weight vector recovers the known-active frequencies and assigns near-zero
weight to the known-inactive ones — without the fitting procedure ever
raising a "not enough samples" guard.

**Acceptance Scenarios**:

1. **Given** `T` topologies' `(b(x_t), y_t)` pairs with `T` strictly fewer
   than the number of representable frequencies `L`, **When** LASSO is fit
   on the resulting design matrix (rows = topologies, columns = the
   conjugate-symmetric real-stacked frequency basis), **Then** it produces
   a fitted weight vector without ever raising a "not enough samples"
   guard — under-determined regression across topologies is the intended
   operating regime (Constitution §7.3), not an error condition.
2. **Given** a validation case with a known-sparse ground-truth weight
   vector, **When** LASSO is fit on topologies sampled from it, **Then**
   the fitted weight vector's support recovers the known-active
   frequencies and assigns near-zero weight to the known-inactive ones.
3. **Given** the regularization penalty this fit selects, **When** it is
   chosen, **Then** selection uses only an explicit, version-pinned grid
   evaluated by cross-validation or an isolated holdout over the training
   topologies (Constitution §7.7) — never a function of the shot-noise
   bound governing how each `b(x_t)` was measured (Constitution §7.4's
   "t²-penalty bug" guardrail, generalized here from Spec 5's own
   Trotter-evolution-time framing to this pipeline's own shot-noise axis).

---

### User Story 3 - Predict on a held-out topology using the same extraction machinery (Priority: P3)

A developer with a fitted weight vector `ŵ` wants a prediction `ŷ* =
b(x*)^⊤ŵ` for a held-out classical topology `x*` never seen during
training — with `b(x*)` extracted via the exact same Spec 4
`extract_coefficients` machinery used for every training row, never a
different, ad hoc evaluation path.

**Why this priority**: Depends on User Story 2's fitted weight vector
existing; ranked last because it is the pipeline's final consumer step,
not a capability with independent value of its own.

**Independent Test**: Can be fully tested by holding out one topology from
the training set, confirming (Constitution §7.8) it does not appear in
the training set, extracting its `b(x*)` via the identical
`extract_coefficients` call path User Story 1 uses, computing the
prediction, and confirming the prediction pipeline never falls back to a
different extraction mechanism for the held-out case.

**Acceptance Scenarios**:

1. **Given** a held-out topology `x*` and a fitted weight vector `ŵ`,
   **When** a prediction is requested, **Then** `b(x*)` is extracted via
   the SAME `extract_coefficients` call path as every training row —
   never a distinct "prediction-time" extraction mechanism — and the
   prediction is `ŷ* = b(x*)^⊤ŵ`.
2. **Given** a training set and a held-out topology, **When** the split is
   generated (including a randomly generated one), **Then** the pipeline
   asserts, after generation, that `x*` does not appear in the training
   set — checked explicitly, never assumed (Constitution §7.8).
3. **Given** a Hermitian observable, **When** a prediction is computed,
   **Then** it is real-valued because the conjugate-symmetric stacking
   convention (User Story 1, Acceptance Scenario 3) is enforced on both
   sides of the inner product — a non-Hermitian observable is rejected
   before any prediction is attempted, the same way Spec 4's own
   extraction layer already rejects it.

---

### Edge Cases

- What happens when the number of training topologies `T` exceeds the
  number of representable frequencies `L`? Still supported — the under-
  determined regime (`T ≪ L`) is the expected common case, not a required
  one, and this feature must not special-case or branch on which regime it
  is in (Constitution §9.3, mirroring Spec 5's own FR-002 precedent).
- What happens if a caller attempts to reuse `learn.py`'s `estimate_y` or
  any of its flipped-direction symbols as a shortcut (e.g. to avoid
  compiling `T` separate circuits)? This MUST be structurally prevented,
  not merely discouraged in documentation — an automated check (e.g. an
  import guard analogous to Spec 1's own CI forbidden-import check) MUST
  fail if this feature's own module imports any of them.
- What happens when two training topologies happen to produce numerically
  identical `b(x_t)` vectors (e.g. two different graphs with the same
  extracted Fourier support and coefficients)? The design matrix gains a
  duplicate row, which cannot add new recovery information and wastes one
  topology's own extraction cost — a data-quality concern for whichever
  process chooses the topologies (a `/speckit-plan`-level detail), not a
  correctness violation this engine must reject outright.
- What happens when the observable is non-Hermitian? The conjugate-
  symmetry shortcut this feature depends on for real-valued predictions
  does not apply; this MUST be rejected the same way Spec 4's extraction
  layer already rejects it, not silently produce a complex-valued
  prediction.
- What happens if two or more topologies require DIFFERENT Trotter
  configurations (step count `r` or step size `tau`) or otherwise
  structurally different encoded-parameter setups? Mirroring Spec 5's own
  FR-013 precedent: a single fit MUST require every training row's
  feature map to share an identical encoded-parameter structure (only the
  classical-input-selected fixed gates may differ between rows, per
  Constitution §7.1) and MUST reject a heterogeneous training set
  explicitly rather than silently fitting across it.
- What happens if two training rows' IRs otherwise differ structurally —
  same Trotter configuration, but a different multiplicity, a different
  set of encoded parameters, or a canonical frequency list that does not
  match (Clarifications 2026-08-22)? FR-014's frequency-lattice-alignment
  check MUST catch this even when the Trotter-configuration check (FR-008)
  alone would not — the mismatch is checked against the actual IR/
  frequency structure directly, and an explicit rejection error identifies
  it before any design matrix is assembled.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (Deliverable a): The system MUST provide a training-row
  abstraction where each row is `(x_t, y_t)` — a classical-input/topology
  declaration (selecting its own fixed gates within an otherwise-shared
  encoded-parameter structure, Constitution §7.1) and its label — NEVER
  `(alpha_j, y_j)` for one fixed circuit with a bound numeric parameter
  value (Clarifications: this is precisely `learn.py`'s own, already-
  drifted row model, and precisely the "flipped concept" `C̄` the thesis's
  §5.7.10 identifies as classically easy).
- **FR-002** (Deliverable b): Each training row's feature vector `b(x_t)`
  MUST be obtained via a SEPARATE call to Spec 4's `extract_coefficients`
  (the direct FCE Hadamard-test machinery, Spec-11-execution-repaired) on
  that topology's own compiled circuit — never via `learn.py`'s
  `estimate_y` or any bound-parameter-based primitive.
- **FR-003** (Explicit non-reuse boundary, Critical Mandate): This
  feature's own module(s) MUST NOT import `learn.py`'s `estimate_y`,
  `TrainingRow`, `build_sensing_matrix`, `LassoRegressionBackend`, or
  `fit_model` — verified by a dedicated, automated check (mirroring Spec
  1's own CI forbidden-import guard pattern), not by documentation or code
  review alone.
- **FR-004** (Deliverable c): The system MUST fit a sparse weight vector
  `w(α*)` (thesis §5.7.8's own notation for the linear model `y=b(x)^⊤w`,
  verified in-session — Clarifications) across the collected `{(b(x_t),
  y_t)}` pairs via LASSO, supporting the honestly under-determined regime
  (`T` topologies strictly fewer than `L` representable frequencies,
  Constitution §7.3) as the intended operating mode — MUST NOT raise,
  warn, or otherwise guard against having "too few" training topologies
  relative to frequency count.
- **FR-005** (Deliverable d): The system MUST predict on a held-out
  topology `x*` by extracting `b(x*)` via the exact same `extract_
  coefficients` call path User Story 1 uses for every training row (never
  a distinct prediction-time extraction mechanism), and computing `ŷ* =
  b(x*)^⊤ŵ`.
- **FR-006**: Both the training feature vectors `b(x_t)` and the held-out
  `b(x*)` MUST be represented via the conjugate-symmetric real/imaginary
  stacking convention this project already established (Constitution
  §7.6) for a Hermitian observable's real-valued predictions. **Before
  `/speckit-plan`'s design may rely on any particular stacking/
  reconstruction convention for THIS feature's own object (a per-topology
  extracted feature vector, structurally different from Spec 5's sensing-
  matrix column, even though it reuses the same underlying conjugate-
  symmetry identity), it MUST computationally verify the round trip end to
  end — through `extract_coefficients` itself, not only the stacking
  sub-piece in isolation — on a genuinely complex, conjugate-symmetric
  fixture**, mirroring Spec 5's own FR-006 verification mandate and Spec
  4's FR-006 precedent before it.
- **FR-007** (Scope discipline, Constitution §11.11 analog): This pipeline
  is over classical inputs `x_t` only. It MUST NOT be presented as, and
  MUST NOT structurally drift into, a fidelity kernel or regression over
  the encoded parameters `α` themselves — a structurally different,
  unrelated construction (matching the exact discipline Spec 10's own
  FR-004 already enforces for the kernel-overlap circuit).
- **FR-008**: A single fit MUST require every training row's encoded-
  parameter structure to be identical (Trotter configuration or otherwise)
  across all topologies — only the classical-input-selected fixed gates
  may differ between rows — and MUST reject a heterogeneous training set
  explicitly, mirroring Spec 5's own FR-013 precedent.
- **FR-009**: Selection of the regularization penalty MUST use only an
  explicit, version-pinned grid of candidate values, evaluated by k-fold
  cross-validation or an isolated holdout over the training topologies
  (Constitution §7.7), and MUST NOT be a function of the shot-noise bound
  governing how any `b(x_t)` was measured (Constitution §7.4, generalized
  from Spec 5's Trotter-evolution-time framing to this pipeline's own
  shot-noise axis, since there is no per-row evolution-time parameter
  here).
- **FR-010**: The system MUST assert, after any training/held-out split is
  generated (including a randomly generated one), that the held-out
  topology `x*` does not appear in the training set — checked explicitly,
  never assumed (Constitution §7.8).
- **FR-011**: Predictions MUST enforce conjugate symmetry so that
  predictions for a Hermitian observable are real-valued; a non-Hermitian
  observable MUST be rejected before any prediction is attempted, the same
  way Spec 4's extraction layer already rejects it (Constitution §7.6).
- **FR-012** (Pre-FR verification already performed, Constitution §2.2/
  §4.1): This spec's own historical and structural claims — the exact
  location and content of the thesis's "flipped concept" discussion
  (actually §5.7.10, not "Appendix H"), the thesis's own `w(α*)` linear-
  model notation (§5.7.8, eq. 5.79), and `learn.py`'s actual current
  implementation matching the flipped concept's own structure — were
  verified computationally/textually in-session before this spec was
  written (Clarifications), not asserted from memory or the user's own
  framing alone.
- **FR-013** (Spec 10 relationship, Clarifications 2026-08-22): This
  feature and Spec 10 (Quantum Kernel Method) MUST be documented, in both
  specs' own implementation records, as solving the EXACT SAME linear
  model (thesis §5.7.8, eq. 5.79: `y = x^⊤w`) via two different routes:
  Spec 10's kernel ridge regression is the implicit/dual route (predicting
  without ever forming `w` explicitly); this feature's LASSO fit is the
  explicit/primal/sparse route (solving for `w` directly). Neither route
  supersedes the other; both must be presented as complementary strategies
  for one shared underlying problem, never as unrelated or competing
  capabilities.
- **FR-014** (Frequency lattice alignment, Clarifications 2026-08-22): The
  system MUST validate, before assembling the cross-topology design
  matrix, that every training row's IR shares the EXACT SAME frequency
  lattice — identical encoded parameters, identical multiplicity per
  parameter, and an identical canonical frequency list — as every other
  row's IR (only the classical-input-selected fixed gates may differ,
  per FR-008). If any row's IR fails this check, the system MUST raise an
  explicit, named rejection error identifying the mismatch — never
  silently proceed to build a design matrix whose rows would not actually
  align to the same frequency basis. This is the general, directly
  checkable mechanism underlying FR-008's Trotter-configuration-specific
  framing — validated against the actual IR/frequency structure, not only
  `r`/`tau` equality.

### Key Entities *(include if feature involves data)*

- **Cross-topology training row**: `(x_t, y_t)` — a classical-input/
  topology declaration and its label (FR-001) — never a bound encoded-
  parameter value.
- **Extracted feature vector `b(x_t)`**: The Fourier-coefficient vector
  Spec 4's `extract_coefficients` produces for one topology's own compiled
  circuit (FR-002), conjugate-symmetric real/imaginary-stacked (FR-006).
- **Sparse weight vector `w(α*)`**: The unknown weight vector
  characterizing the target concept (thesis §5.7.8's own notation,
  verified — Clarifications), fit via LASSO across `{(b(x_t), y_t)}`
  pairs (FR-004), honestly allowed `T ≪ L` (Constitution §7.3).
- **Cross-topology design matrix**: The matrix whose rows are training
  topologies' stacked, real-valued `b(x_t)` vectors — structurally
  distinct from Spec 5's Fourier sensing matrix `A_{j,l}=exp(iπl·α_j)`,
  since its rows come from genuinely different compiled circuits, not
  bound-parameter samples of one fixed circuit.
- **Held-out prediction**: `ŷ* = b(x*)^⊤ŵ`, computed via the identical
  extraction call path as every training row (FR-005).
- **Frequency lattice** (Clarifications 2026-08-22): the shared structure
  — identical encoded parameters, per-parameter multiplicity, and
  canonical frequency list — every training row's IR must exhibit for its
  `b(x_t)` to align as a valid row of the cross-topology design matrix
  (FR-014). Checked structurally before the design matrix is assembled,
  not assumed from `r`/`tau` equality alone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can recover a sparse weight vector from `T`
  topologies' `(b(x_t), y_t)` pairs with `T` strictly fewer than `L` (the
  representable frequency count), correctly recovering a known-sparse
  ground truth's active frequencies on a validation case.
- **SC-002**: Every extracted feature vector this feature produces —
  training or held-out — is obtained via Spec 4's `extract_coefficients`,
  verified by an automated check that this feature's own module never
  imports `learn.py`'s `estimate_y`/`TrainingRow`/`build_sensing_matrix`/
  `LassoRegressionBackend`/`fit_model`.
- **SC-003**: The conjugate-symmetric real-stacking round trip for this
  feature's own extracted-feature-vector object is computationally
  verified end to end against a genuinely complex fixture before any
  implementation relies on it — not assumed to carry over from Spec 5's
  differently-shaped object.
- **SC-004**: Every held-out evaluation topology this feature's test suite
  exercises is checked, after split generation, to confirm zero overlap
  with the training set.
- **SC-005**: This spec's own historical claim (that Spec 5 drifted away
  from this exact cross-topology design during its own bug-fix/
  clarification process) is documented in `/speckit-plan`'s research.md
  with its exact failure mechanism (Constitution §8.4) — citing Spec 5's
  own spec.md Clarifications history and the verified thesis sections
  (§5.7.8, §5.7.10) — not merely asserted in this spec's own prose.
- **SC-006** (Primal/dual shared-fixture cross-check, Clarifications
  2026-08-22): On one IDENTICAL fixture — the same training topologies,
  the same target concept `α*`, and the same held-out `x*` — this
  feature's explicit/primal LASSO route and Spec 10's implicit/dual
  kernel-ridge-regression route are both run, and their predictions on
  `x*` are compared, demonstrating (FR-013) that the two routes solve the
  same underlying linear model rather than merely resembling each other in
  prose.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1),
  Encodings Layer (Spec 2), Circuits Layer (Spec 3), Extract Layer (Spec 4,
  `extract_coefficients`/`estimate_coefficient`), and Spec 11's execution
  repair (the same `extract_coefficients` this feature calls, now with the
  Constitution §1.7 controlled-circuit defect fixed and a substantially
  lower per-topology extraction cost) — none of these are re-specified
  here.
- **Relationship to Spec 10 (Quantum Kernel Method), not a duplicate**:
  Spec 10's kernel ridge regression already solves the same underlying
  linear model (`y = b(x)^⊤w(α)`, thesis eq. 5.79) implicitly, via the
  kernel trick, without ever forming `w` explicitly. This feature is a
  genuinely different, complementary strategy for the SAME linear model —
  an explicit, sparse (LASSO) solve for `w` itself, motivated by the
  thesis's own §5.7.9 closing remark that efficient learnability follows
  when the spectrum is sparse. Both may coexist; neither supersedes the
  other.
- **Relationship to Spec 5/`learn.py`, an explicit non-reuse boundary, not
  a replacement of Spec 5 itself**: this feature does not modify or
  deprecate `learn.py` — Spec 5's own (drifted) implementation remains in
  the codebase, answering a different (flipped, classically-easy)
  question, which may still have its own legitimate uses this spec does
  not evaluate. This feature is new code, added alongside it, that
  structurally cannot import Spec 5's flipped-direction primitives
  (FR-003).
- **`/speckit-plan`'s own required historical documentation
  (Constitution §8.4, Critical Mandate)**: `/speckit-plan`'s research.md
  MUST document, with its exact failure mechanism, how Spec 5's own
  2026-08-20 → 2026-08-21 clarification history moved from an (also
  incorrect) "training row = one directly-measured Fourier coefficient"
  framing to the current, still-flipped "training row = `(alpha_j, y_j)`
  for one fixed circuit" framing — never removing or rewriting that
  history, only citing and building on it (this spec's own Clarifications
  section above already performs the source-verification half of this
  obligation; the historical-narrative half is `/speckit-plan`'s to
  complete).
- Scoped to a single Hermitian Pauli-string observable per model, matching
  the scope already established by Specs 3-5 and Spec 10 — the weighted-
  sum/linear-combination-of-Paulis extension (Spec 9's LCU machinery)
  remains the same named, deferred `TODO` those specs already recorded;
  this spec does not extend that scope.
- The specific classical topologies/graphs `x_t` sampled for training, the
  specific LASSO solver/implementation, and the regularization grid's
  candidate values are `/speckit-plan`-level decisions — this spec
  requires only the behavior FR-001 through FR-014 specify, mirroring Spec
  5's own precedent for deferring these exact categories of decision.
- This feature validates against Spec 1's exact oracle under noiseless
  (Aer) shot sampling; physical hardware noise characterization remains
  the separate, later concern Constitution §8.6 already scopes out.
