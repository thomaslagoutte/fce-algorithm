# Feature Specification: Learning Backend Layer

**Feature Branch**: `005-learning-backend-layer`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Learning Backend Layer for FCE. Deliverables: (a) A classical regression engine (e.g., sparse LASSO) that consumes the extracted Fourier coefficients to output the learned Hamiltonian model. (b) An error-bounding framework that contextualizes the learning error against the shot noise and Trotterization bounds. CRITICAL MANDATES: 1. **The $t^2$-Penalty Bug:** You MUST explicitly define how the regularization parameter scales with the extracted coefficient magnitudes to prevent the historical penalty-anchoring bug. 2. **PAC vs. Trotter Error:** The specification MUST include a strict analytical separation between statistical learning error (PAC bounds) and structural approximation error (Trotter noise) to prevent the 'PAC-beats-Trotter false triumph' seen in the legacy codebase. Do not allow Trotter error to artificially inflate the perceived success of the learning algorithm."

## Clarifications

### Session 2026-08-20

- Q: Since the regression engine requires real-valued inputs but
  `FourierCoefficients` are complex, must the spec mandate that
  `/speckit-plan` computationally verify the complex-to-real design-matrix
  stacking and its reconstruction back to complex weights against a
  conjugate-symmetric fixture, to rule out a sign or ordering error in that
  classical memory mapping before implementation relies on it? → A: Yes,
  mandated. FR-006 now requires this computational verification as a
  precondition `/speckit-plan`'s design must satisfy before relying on any
  particular real/imaginary stacking convention, mirroring how Spec 4's
  FR-006 required the Hadamard-test estimator's own conjugate-symmetry
  behavior to be verified computationally rather than assumed. A new Key
  Entity ("Real-valued design matrix") documents the stacking/reconstruction
  contract this check applies to.
- Q: May a single model fit combine training rows produced under different
  Trotter configurations (different step count `r` or step size `tau`), or
  must every row in one fit share an identical configuration, with the
  engine explicitly rejecting a heterogeneous mix? → A: Must share an
  identical configuration; the engine explicitly checks and rejects
  heterogeneous training data. This closes a second path to the
  "PAC-beats-Trotter false triumph": FR-007's Trotter bound is only
  well-defined for one feature map (one step size, order, and evolution
  time) per fit — mixing configurations would make the reported Trotter
  bound apply to no actual row in the training set. Mixed-configuration
  support is out of scope and deferred to a future spec, per the same
  named-`TODO` convention Specs 3-4 already use. New FR-013 and an Edge
  Case entry added.
- Q: For FR-009's generalization-check requirement, is this spec responsible
  only for the *policy* of flagging that a generalization check is required,
  or must it also implement the *mechanism* that runs shifted-parameter
  dynamics to perform that check? → A: Policy only. This spec raises a
  "generalization check required" flag/state and stops there; it does not
  implement, and MUST NOT implement, the mechanism that actually runs
  dynamics at a shifted parameter value. That mechanism is out of scope,
  owned by a downstream experiment layer (Spec 6, not yet specified).
  FR-009, User Story 2's Acceptance Scenario 3, and SC-004 updated to state
  this division of labor explicitly.

### Session 2026-08-21

- Q: Was the 2026-08-20 session's row model — a training row is one
  directly-measured Fourier coefficient `b_l` from Spec 4 — actually a valid
  compressed-sensing setup? → A: **No — a fundamental correction, not a
  refinement.** If a row is a direct measurement of `b_l`, the sensing
  matrix relating measurements to the unknown coefficient vector is the
  identity (one-hot per row): LASSO on an identity design matrix reduces to
  independent per-coordinate soft-thresholding, which cannot recover any
  coefficient that was never directly measured — there is no "sparse
  recovery" happening at all, only thresholding of what was already known.
  Every FR, Key Entity, and Assumption built on the 2026-08-20 row model
  (FR-001, User Story 1, SC-001) is corrected below to a genuine
  compressed-sensing setup: a training row is an `(input, output)` pair
  `(alpha_j, y_j)`, where `alpha_j` is a concrete numeric assignment of
  every encoded parameter and `y_j` is the real-valued expectation
  `<0|U^dagger(alpha_j) P U(alpha_j)|0>`, estimated via finite shots by a
  **new** primitive (FR-014) — a Hadamard test on Circuits Layer's compiled
  `A(U,O)` circuit with its parameters bound to `alpha_j`, but *without*
  Spec 4's `V_l` frequency-shift component (Spec 4's own primitive shifts by
  a specific target frequency; this one does not shift at all, it directly
  reads the bound circuit's own expectation value). The `M` rows then form a
  genuine Fourier sensing matrix `A_{j,l} = exp(i*pi*l*alpha_j)` (FR-015),
  making `y = A b` a genuinely under-determined linear system LASSO can
  solve for the sparse `L`-dimensional coefficient vector `b` from `M << L`
  measurements — the actual literature setup Constitution §7.3's "sample
  complexity is logarithmic in the frequency count" describes. FR-006's
  already-verified real/imaginary stacking-and-reconstruction contract
  (2026-08-20 session, research.md R2 once `/speckit-plan` re-runs) is
  **not** invalidated by this correction — every real/complex Fourier
  coefficient `b_l` this new sensing matrix relates `y` to is the exact same
  object FR-006 already specifies the stacking convention for; only *how a
  row is obtained* was wrong, not the representation of the thing being
  recovered. `/speckit-plan` must re-verify FR-006's round trip in this
  corrected context (the stacking/reconstruction mechanics are unchanged,
  but the design matrix `A` that used to not exist at all now does, and the
  full pipeline — bind `alpha_j`, measure `y_j`, build `A`, fit, reconstruct
  — must be re-verified end to end, not assumed to still hold merely because
  its sub-piece did).

## User Scenarios & Testing *(mandatory)*

<!--
  This feature's "users" are the developers who build the `models`/`experiment`
  pipeline stages (Constitution §9.1) on top of the Extract Layer (Spec 4).
  Unlike Spec 4's own primitive (which extracts one exact Fourier coefficient
  directly, at the cost of one circuit execution per frequency), this layer's
  point is to recover the FULL sparse Fourier-coefficient vector from far
  fewer circuit executions than there are representable frequencies, by
  evaluating the compiled circuit's real-valued expectation at M concrete,
  chosen classical inputs and solving a genuine compressed-sensing linear
  system for the sparse coefficient vector (Clarifications, 2026-08-21).
-->

### User Story 1 - Learn a sparse Hamiltonian model from few expectation-value measurements (Priority: P1)

A developer who can evaluate the compiled circuit's real-valued expectation
`y(alpha) = <0|U^dagger(alpha) P U(alpha)|0>` at any concrete numeric
assignment `alpha` of the encoded parameters (a new, finite-shot primitive
this spec adds, FR-014) wants to choose `M` such inputs, measure `y` at each,
and recover the full `L`-dimensional sparse Fourier-coefficient vector via a
genuine compressed-sensing linear system `y = A b` (FR-015) — using far
fewer measurements `M` than the number of representable frequencies `L`,
because the true underlying Hamiltonian is expected to be sparse.

**Why this priority**: This is the foundational deliverable — every other
capability in this spec (the error-bounding framework, the penalty-integrity
guardrail) exists to characterize or protect the correctness of this model.
Without it, there is nothing to bound the error of.

**Independent Test**: Can be fully tested by building a small circuit from a
Hamiltonian with a known, sparse term structure, measuring `y(alpha)` at
`M` randomly chosen concrete inputs with `M` strictly fewer than the number
of representable frequencies, fitting the regression engine on the
resulting `(alpha_j, y_j)` pairs, and confirming the fitted coefficient
vector recovers the known-active frequencies and assigns near-zero weight
to the known-inactive ones.

**Acceptance Scenarios**:

1. **Given** a training set of `M` `(alpha_j, y_j)` pairs strictly smaller in
   count than the number of representable frequencies, **When** the
   regression engine is fit on the Fourier sensing matrix built from the
   `alpha_j` values, **Then** it produces a model without ever raising a
   "not enough samples" guard — under-determined compressed-sensing
   regression is the intended operating regime, not an error condition.
2. **Given** a fitted model and a Hermitian observable, **When** the model
   predicts an expectation value for a new classical input, **Then** the
   prediction is real-valued, because conjugate symmetry between mirrored
   frequency weights is enforced rather than left to numerical accident.
3. **Given** a training set of concrete inputs and a held-out evaluation
   input, **When** the evaluation input is checked against the training set
   after the split is generated, **Then** the check confirms no overlap —
   this is asserted explicitly, not assumed.
4. **Given** the same training set fit twice with the same random seed,
   **When** both fitted models are compared, **Then** they are identical —
   fitting is deterministic given a fixed seed, versioned solver, and pinned
   regularization grid.

---

### User Story 2 - Report PAC and Trotter error as two independent bounds (Priority: P2)

A developer who has a fitted model from User Story 1 wants an honest report
of how good it is — but split into the two genuinely independent things that
can make a prediction wrong: the *statistical* error of learning from a
finite, noisy sample (a PAC-style bound), and the *structural* error already
baked into the feature map before any learning happens, because the encoding
circuit only ever approximated the true dynamics via Trotterization. The
developer must never receive one number that blends the two.

**Why this priority**: Depends on User Story 1's model existing, but is not
optional polish — Constitution §8.1 treats "reporting only the gap to exact"
as conflating two independent error sources, and the explicit legacy failure
mode this spec must prevent ("PAC-beats-Trotter false triumph") is a report
that looks like a learning success only because the underlying feature map's
own approximation error happened to be large enough to make finite-sample
noise look small by comparison.

**Independent Test**: Can be fully tested standalone: take a fitted model
whose feature map has a known, deliberately coarse Trotter step (so its own
structural error against exact dynamics is large and computable), request
the error-bounding report, and confirm the report exposes the PAC bound and
the Trotter bound as two separately labeled, separately computed numbers,
with the PAC bound computed only from training-sample statistics and the
Trotter bound computed only from the feature map's own step size and order —
neither computation reads from the other.

**Acceptance Scenarios**:

1. **Given** a fitted model and its training set, **When** the error-bounding
   report is generated, **Then** it states a PAC-style statistical learning
   error bound derived only from sample count, frequency count, and the
   training label noise level (never from the Trotter step size), and a
   Trotter approximation error bound derived only from the feature map's step
   size, order, and evolution time (never from the sample count or shot
   noise).
2. **Given** a case where the feature map's own Trotter error is large
   relative to the learner's statistical error, **When** the model's
   agreement with exact dynamics is measured, **Then** the report explicitly
   attributes the residual gap to the dominant bound rather than presenting
   a single blended "error" figure that could be misread as learning
   success.
3. **Given** a fitted model whose predictions track exact dynamics *more*
   closely than its own reported Trotter bound would permit, **When** the
   report is generated, **Then** it flags this as a suspected artifact (for
   example, label interpolation at a single training parameter value) and
   sets a "generalization check required" state — this spec is responsible
   only for raising that flag (the policy); it does not run, and must not
   attempt to run, the shifted-parameter dynamics that would actually clear
   or confirm it, which is a downstream experiment layer's mechanism (Spec
   6, not yet specified), out of scope here.
4. **Given** any generated report, **When** it is inspected, **Then** it
   states explicitly, in its own output, what it does and does not
   establish (for example: "this bounds statistical learning error only;
   it does not bound hardware noise").

---

### User Story 3 - Guard against the penalty-anchoring bug (Priority: P3)

A developer configuring the regression engine's regularization strength
needs a guarantee that the penalty is never selected by, or scaled against,
quantities that belong to a *different* error source — specifically, the
shot-noise bound that governs how many measurement shots were used to
produce the training labels. Anchoring the penalty to that bound was a
historical bug: it shrinks small-but-real coefficients toward zero and
produces a spurious flattening at large evolution times that is
indistinguishable, in a plotted report, from genuine physics.

**Why this priority**: Explicitly named as a critical mandate to prevent a
recurrence of a specific historical bug (the "$t^2$-penalty bug"). It is
made its own priority tier, below the two functional deliverables, because
it is a guardrail on how User Story 1's fitting procedure is allowed to
choose one internal parameter — not a new capability — but it is promoted to
an independently-tested, first-class requirement precisely because the bug
it prevents is silent: a badly-anchored penalty still produces a model that
runs and looks plausible. It also depends on User Story 1's fitting
procedure existing, since there is otherwise no regularization parameter to
guard.

**Independent Test**: Can be fully tested standalone: fit the regression
engine twice on the same training inputs and coefficient values, once
using a small shot count (large label noise) and once using a much larger
shot count (small label noise), with the data-driven penalty grid and
cross-validation procedure held fixed; confirm the selected penalty value
is chosen by the same fixed, version-pinned grid and cross-validation
procedure both times, and is not a function of the shot count or of the
Trotterization evolution-time parameter.

**Acceptance Scenarios**:

1. **Given** the regression engine's regularization parameter, **When** its
   value is selected, **Then** the selection uses only an explicit,
   version-pinned grid of candidate values evaluated by cross-validation (or
   an isolated holdout) over the training data — never a formula that reads
   the shot-noise bound or the Trotterization evolution time as an input.
2. **Given** two training sets differing only in shot count used to produce
   the labels (and therefore in label noise), **When** the penalty is
   selected for each, **Then** the candidate grid and selection procedure
   used are identical between the two runs — the shot count is not read by
   the selection step at all.
3. **Given** a held-out evaluation input, **When** penalty selection,
   feature scaling, or any other fitted quantity is chosen, **Then** none of
   them are influenced by that evaluation input's label, directly or by
   manual tuning against a reported metric.

---

### Edge Cases

- What happens when the number of training inputs exceeds the number of
  frequencies? Still supported — the under-determined regime (User Story 1)
  is the expected common case, not a required one, and this feature must
  not special-case or branch on which regime it is in (Constitution §9.3).
- What happens when a fitted model's prediction is *better* than its own
  feature map's Trotter bound predicts is possible? Flagged as a suspected
  artifact rather than reported as success, with a "generalization check
  required" flag set (User Story 2, Acceptance Scenario 3) — this feature
  raises that flag only; clearing it by actually running shifted-parameter
  dynamics is a downstream experiment layer's mechanism (Spec 6), out of
  scope here.
- What happens when the shot-noise bound and Trotter bound are of comparable
  size? Both are still reported separately; no averaging, ratio, or single
  combined score is ever produced by this feature.
- What happens when cross-validation is not able to reduce the candidate
  grid to a single best value because two candidates score within noise of
  each other? This is a negative or inconclusive result and must be
  documented as such (Constitution §8.4), not silently resolved by picking
  the smaller or larger candidate.
- What happens when an observable is non-Hermitian? The conjugate-symmetry
  shortcut this feature depends on for real-valued predictions does not
  apply; this must be rejected the same way Spec 4's extraction layer
  already rejects it, not silently produce a complex-valued prediction.
- What happens when training rows come from different Trotter configurations
  (different step count `r` or step size `tau`)? A single fit MUST reject
  this outright rather than silently fitting across a heterogeneous feature
  map — FR-007's Trotter bound is defined for one feature map per fit, and a
  mixed-configuration training set would make that bound apply to no actual
  row. Mixed-configuration support is deferred to a future spec.
- What happens when two or more training rows use the same (or
  numerically indistinguishable) `alpha_j` value (Clarifications,
  2026-08-21)? The Fourier sensing matrix `A` gains a duplicate row, which
  cannot add new information toward recovering `b` and effectively wastes
  one measurement's shot budget — this is a data-quality concern for
  whatever process chooses the `alpha_j` values (a `/speckit-plan`-level
  detail, e.g. checking for and warning about near-duplicate inputs), not a
  correctness violation this engine must reject outright the way FR-013
  rejects heterogeneous Trotter configurations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (revised, Clarifications 2026-08-21): The regression engine
  MUST consume a training set of `(alpha_j, y_j)` pairs — a concrete numeric
  assignment `alpha_j` of every encoded parameter, and the corresponding
  real-valued expectation `y_j` measured by FR-014's new primitive — build
  the Fourier sensing matrix `A` from the `alpha_j` values (FR-015), and
  solve the resulting under-determined linear system for the sparse,
  complex Fourier-coefficient vector `b` (one entry per representable
  frequency, real/imaginary-stacked per FR-006) via the LASSO regression
  engine (Constitution §7.1). This supersedes the 2026-08-20 session's
  incorrect framing of a training row as one directly-measured Fourier
  coefficient (Clarifications, 2026-08-21) — that framing produces an
  identity sensing matrix, on which no sparse recovery is possible.
- **FR-002**: The engine MUST support the under-determined regime (fewer
  training inputs than frequencies) as its intended operating mode
  (Constitution §7.3) and MUST NOT raise, warn, or otherwise guard against
  having "too few" training inputs relative to frequency count.
- **FR-003**: Selection of the regularization penalty MUST use only an
  explicit, version-pinned grid of candidate values, evaluated by k-fold
  cross-validation over the training inputs, or an isolated holdout drawn
  from them (Constitution §7.7). Neither the grid values nor the selection
  procedure may be a function of the shot-noise bound or the Trotterization
  evolution-time parameter.
- **FR-004** (the "$t^2$-penalty bug" guardrail): The label-noise (shot-noise)
  bound MUST govern shot budget only, exactly as Spec 4 already reports it,
  and MUST NOT scale, anchor, or otherwise influence the regularization
  penalty in any way (Constitution §7.4). A dedicated test MUST fit the
  engine on the same training data at two different shot counts (hence two
  different label-noise levels) with the penalty grid and cross-validation
  procedure held fixed, and confirm the grid and procedure are provably
  identical between the two runs — not merely that the two selected
  penalties happen to match.
- **FR-005**: The engine MUST assert, after any training/evaluation split is
  generated (including a randomly generated one), that no evaluation input
  appears in the training set — checked explicitly, never assumed
  (Constitution §7.8).
- **FR-006**: Predictions MUST enforce conjugate symmetry between a
  frequency's weight and its mirror's weight so that predictions for a
  Hermitian observable are real-valued (Constitution §7.6). The engine MUST
  first confirm the observable is Hermitian before relying on this shortcut,
  the same way Spec 4's extraction layer already does, and MUST reject a
  non-Hermitian observable rather than silently producing a complex-valued
  prediction. Because `y_j` (FR-014) is real while the Fourier-coefficient
  vector `b` being recovered is complex, the real-valued LASSO fit
  necessarily operates on a real-valued reduction of `b`: stacking real and
  imaginary parts of the canonical, non-mirrored half of the frequencies
  plus the always-real DC term, per the conjugate-symmetry identity — this
  same stacking, applied to the sensing-matrix columns of FR-015's
  `A_{j,l} = exp(i*pi*l*alpha_j)` rather than to a directly-measured
  coefficient (Clarifications, 2026-08-20 and 2026-08-21) — and
  reconstructing a complex weight back from the fitted real-valued result.
  **Before `/speckit-plan`'s design may rely on any particular
  stacking/reconstruction convention, it MUST computationally verify — on a
  small, genuinely-complex conjugate-symmetric fixture, end to end through
  FR-014's measurement primitive and FR-015's sensing matrix, not only the
  stacking/reconstruction sub-piece in isolation — that the round trip
  introduces no sign or ordering error**, not merely assume the general
  identity carries through the specific memory layout chosen (the same class
  of assumption-vs.-verification gap Spec 4's FR-006 closed for the
  Hadamard-test estimator).
- **FR-007**: The error-bounding framework MUST report a PAC-style
  statistical learning error bound and a structural Trotterization
  approximation-error bound as two separately computed, separately labeled
  quantities (Constitution §8.1). The PAC bound computation MUST take only
  sample count, frequency count, and training label noise as inputs; the
  Trotter bound computation MUST take only the feature map's step size,
  order, and evolution time as inputs. Neither computation may read an input
  that belongs to the other.
- **FR-008**: The framework MUST NOT combine the PAC bound and the Trotter
  bound into any single blended error figure, ratio, or score anywhere in
  its output (Constitution §8.1) — this is the specific "PAC-beats-Trotter
  false triumph" failure mode this spec exists to prevent.
- **FR-009**: If a fitted model's agreement with exact dynamics is closer
  than its own reported Trotter bound permits, the framework MUST flag this
  as a suspected artifact rather than report it as a capability, and MUST
  set an explicit "generalization check required" state naming the input
  such a check would need to use (Constitution §8.2). **Division of labor
  (Clarifications, 2026-08-20): this spec is responsible only for this
  policy — raising and recording that flag.** It MUST NOT implement the
  mechanism that actually runs shifted-parameter dynamics to resolve it;
  that mechanism belongs to a downstream experiment layer (Spec 6, not yet
  specified) and is out of scope here. No result gated by this flag may be
  reported as genuine until that separate, out-of-scope mechanism clears it.
- **FR-010**: Noise (shot noise) MUST be reported as a third, independent
  error axis alongside the PAC bound and the Trotter bound — never folded
  into either as a correctness gate (Constitution §8.6).
- **FR-011**: Any bound that must hold uniformly over a concept class (as
  opposed to one specific training set) MUST use constants computed once,
  globally over the whole training set — never recomputed per individual
  input (Constitution §7.5).
- **FR-012**: Every fitting run MUST be seeded end-to-end and MUST record a
  run manifest (configuration, library versions, hardware, timings) beside
  its outputs (Constitution §8.5), so that a reported bound or fitted model
  can be reproduced exactly.
- **FR-013** (new, Clarifications 2026-08-20): A single model fit MUST
  require every training row's feature map to share an identical Trotter
  configuration (step count `r` and step size `tau`) — the engine MUST
  explicitly check this and reject a heterogeneous training set with a clear
  error rather than silently fitting across it. Mixed-Trotter-configuration
  training is out of scope for this spec and deferred to a future spec; this
  closes a second path to the "PAC-beats-Trotter false triumph," since
  FR-007's Trotter bound is defined for exactly one feature map per fit —
  a heterogeneous training set would make that bound apply to no actual row.
- **FR-014** (new, Clarifications 2026-08-21): This feature MUST provide a
  new primitive that estimates the real-valued expectation
  `y(alpha) = <0|U^dagger(alpha) P U(alpha)|0>` at a concrete numeric
  assignment `alpha` of every encoded parameter, using only finite-shot
  measurement (Constitution Article II — never `Statevector`/`Operator`).
  This is a Hadamard test on Circuits Layer's compiled `A(U,O)` circuit with
  its parameters bound to `alpha`, structurally identical to Spec 4's own
  Hadamard test except that it MUST NOT include Spec 4's `V_l`
  frequency-shift component — it reads the bound circuit's own expectation
  directly, at no target frequency. This primitive is added by this feature
  (not by modifying Spec 4's already-shipped `extract.py`), reusing Circuits
  Layer's `compile_observable_circuit` exactly as Spec 4 already does.
- **FR-015** (new, Clarifications 2026-08-21): The regression engine's
  design matrix `A` MUST be the Fourier sensing matrix evaluated at the
  training set's concrete inputs: for training row `j` and representable
  frequency `l`, `A_{j,l} = exp(i * pi * l * alpha_j)` — generalized, for a
  multi-parameter model, to `A_{j,l} = exp(i * pi * l . (c ⊙ alpha_j))`
  where `c` is the per-parameter structural coefficient vector Spec 1's IR
  already carries (`PauliTerm.coefficient`) and `.`/`⊙` are the dot product
  and elementwise product over parameter dimensions — matching exactly the
  same per-parameter coefficient rescaling `fourierlearn.reference`'s own
  oracle already performs (`_build_grid`'s `domain_length = 2/coefficient`),
  not a newly invented convention. This makes `y = A b` (real part) a
  genuinely under-determined linear system solvable by LASSO for the sparse
  complex vector `b`, per FR-006's real-valued stacking of both `A`'s
  columns and `b`.

### Key Entities *(include if feature involves data)*

- **Learned Hamiltonian model**: A sparse mapping from Hamiltonian term (one
  per representable frequency) to a fitted weight on the unknown encoded
  parameters, produced by the regression engine from a training set of
  `(alpha_j, y_j)` input-output pairs (Clarifications, 2026-08-21).
- **Training input-output pair** (new, Clarifications 2026-08-21): One
  training row, `(alpha_j, y_j)` — a concrete numeric assignment `alpha_j`
  of every encoded parameter, and the real-valued expectation `y_j`
  measured at that assignment by FR-014's new primitive.
- **Fourier sensing matrix** (new, Clarifications 2026-08-21; supersedes the
  2026-08-20 "Real-valued design matrix" entity's role as the regression
  engine's actual input — see below): the matrix `A` with
  `A_{j,l} = exp(i*pi*l*alpha_j)` (FR-015), relating the `M` measured
  `y_j` values to the `L`-dimensional sparse Fourier-coefficient vector `b`
  via the genuinely under-determined linear system `y = A b`.
- **Real-valued stacking/reconstruction convention** (Clarifications
  2026-08-20, retargeted 2026-08-21): the regression engine's actual
  real-valued input is built by stacking the real and imaginary parts of
  each canonical (non-mirrored) frequency's column of the Fourier sensing
  matrix (and of the coefficient vector `b` it multiplies) as two real
  columns, plus one real column for the always-real DC term, per the
  conjugate-symmetry identity (FR-006) — together with the reconstruction
  of a complex weight per frequency from the fitted real-valued result.
  `/speckit-plan` MUST computationally verify this stacking/reconstruction
  round trip, end to end through FR-014's primitive and FR-015's sensing
  matrix, against a conjugate-symmetric fixture before relying on it.
- **Regularization grid**: An explicit, version-pinned list of candidate
  penalty values, evaluated by cross-validation or an isolated holdout over
  the training data only — never a function of shot-noise or evolution-time
  quantities.
- **Error-bounding report**: The output of the error-bounding framework,
  stating the PAC-style statistical learning bound and the Trotterization
  structural bound as two independent, separately labeled figures, plus a
  reported noise characterization, and an explicit statement of what the
  report does and does not establish.
- **Training/evaluation split**: An explicit partition of classical inputs
  into a training set and a held-out evaluation set, with an asserted,
  checked guarantee (not an assumption) that no input appears in both.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (revised, Clarifications 2026-08-21): A developer can recover a
  sparse, `L`-dimensional Fourier-coefficient vector from `M` measured
  `(alpha_j, y_j)` pairs with `M` strictly fewer than `L`, by solving the
  genuine compressed-sensing linear system `y = A b` (FR-015) — the fitted
  vector recovers a known-sparse term structure's active frequencies on a
  validation case built with a known ground truth. (Supersedes the
  2026-08-20 wording, which described fitting from directly-measured
  coefficients — a setup with no actual sparse-recovery content, since its
  sensing matrix was the identity.)
- **SC-002**: The regularization penalty selected for a given training set is
  provably identical in grid and selection procedure regardless of the
  shot count used to produce that training set's labels — verified by a
  dedicated test that varies shot count alone while holding the grid and
  procedure fixed (the "$t^2$-penalty bug" guardrail).
- **SC-003**: Every error-bounding report a developer receives states the
  PAC-style statistical learning bound and the Trotterization structural
  bound as two separately computed, separately labeled numbers, with zero
  instances anywhere in this feature's output of a single blended
  error/success figure combining the two.
- **SC-004**: A model whose agreement with exact dynamics exceeds its own
  reported Trotter bound always has a "generalization check required" flag
  set — this feature's own responsibility ends at raising that flag
  (Clarifications, 2026-08-20); resolving it via shifted-parameter dynamics
  is a downstream experiment layer's mechanism (Spec 6), out of scope here.
- **SC-005**: Every training/evaluation split this feature's test suite
  exercises is checked, after generation, to confirm zero overlap between
  the two sets — not assumed correct because the split code "looks right."
- **SC-006**: Predictions for a Hermitian observable are always real-valued,
  and a non-Hermitian observable is always rejected before any prediction is
  attempted; the complex-to-real-and-back stacking this relies on is
  computationally verified against a conjugate-symmetric fixture, not
  assumed.
- **SC-007** (new, Clarifications 2026-08-20): A single fit always rejects a
  training set whose rows do not share one identical Trotter configuration
  (`r` and `tau`), with zero instances of a fit silently proceeding across a
  heterogeneous feature map.

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1), Encodings
  Layer (Spec 2, including `encodings/trotter.py`'s step/order parameters),
  Circuits Layer (Spec 3), and Extract Layer (Spec 4:
  `FourierCoefficients = dict[tuple[int, ...], complex]`,
  `fourierlearn.contracts`) — none of these are re-specified here. Per the
  2026-08-21 correction, this feature's own primary training-label input is
  no longer Spec 4's `FourierCoefficients` output directly; Circuits Layer's
  `compile_observable_circuit` (Spec 3, already reused unchanged by Spec 4)
  is reused unchanged again by FR-014's new primitive.
- Scoped to a single Hermitian Pauli-string observable per model, matching
  the scope already established by Spec 3 and Spec 4 — the
  weighted-sum/linear-combination-of-Paulis extension remains the same
  named, deferred `TODO` those specs already recorded.
- The specific PAC-bound formula (e.g., a Rademacher-complexity-style bound
  or a sparse-recovery-specific bound) and the specific Trotter-error
  formula (e.g., first-order product-formula commutator bound) are
  `/speckit-plan`-level decisions — this spec requires only that each is
  computed from the inputs FR-007 specifies and reported separately, not
  which closed-form expression is used.
- The specific classical regression solver (e.g., an existing sparse-LASSO
  implementation from a numerical library, or a hand-rolled coordinate
  descent) is likewise a `/speckit-plan`-level decision — this spec requires
  only the behavior FR-001 through FR-006 specify.
- The regularization grid's specific candidate values and the number of
  cross-validation folds are `/speckit-plan`-level decisions, provided the
  grid is explicit, version-pinned, and never a function of shot-noise or
  evolution-time quantities (FR-003, FR-004).
- This feature validates against Spec 1's exact oracle and against
  deliberately-coarse Trotter feature maps under noiseless (Aer) shot
  sampling; physical hardware noise characterization remains the separate,
  later concern Constitution §8.6 already scopes out.
- **Policy/mechanism split (Clarifications, 2026-08-20)**: this feature owns
  only the policy decision of flagging that a "generalization check" is
  required when a model appears to beat its own Trotter bound (FR-009). The
  mechanism that actually resolves that flag — running dynamics at a
  classical input shifted away from every training input — belongs to a
  downstream experiment layer, referred to here as Spec 6, which does not
  yet exist and is not specified by this feature.
- **Single-Trotter-configuration scope (Clarifications, 2026-08-20)**: a
  single fit requires every training row to share one identical Trotter
  configuration (FR-013); mixed-configuration training (rows fit together
  from more than one `r`/`tau` pair) is the same named, deferred `TODO`
  pattern Specs 3-4 already use, and remains out of scope for this feature.
- **New-primitive ownership (Clarifications, 2026-08-21)**: FR-014's
  concrete-input expectation-value primitive is added by this feature
  (Spec 5) as new code, not by modifying Spec 4's already-shipped, tested,
  and committed `extract.py` — the same non-invasive-reuse posture Spec 4
  itself took toward Spec 3's `compile_observable_circuit` (calling it
  unchanged rather than modifying Spec 3). After the 2026-08-21 correction,
  this feature no longer calls Spec 4's `estimate_coefficient()` at all
  (FR-001's training rows come from FR-014's new primitive instead); Spec 4
  remains a dependency only via `fourierlearn.contracts`'
  `FourierCoefficients` type and (indirectly, via Spec 3) circuit-compiling
  building blocks.
- **`alpha_j` sampling scheme deferred (Clarifications, 2026-08-21)**: how
  the `M` concrete training inputs `alpha_j` are chosen (e.g. uniform random
  over each parameter's period, a fixed pinned/seeded pseudo-random
  sequence, or a structured low-coherence design known to favor compressed
  sensing recovery) is a `/speckit-plan`-level decision — this spec requires
  only that `M` is strictly fewer than `L` for the intended operating
  regime (FR-002) and that no two training rows share the exact same
  `alpha_j` value in a way that wastes shot budget without adding recovery
  information (Edge Cases).
- **Per-parameter coefficient scaling (Clarifications, 2026-08-21)**:
  FR-015's general sensing-matrix formula includes the same per-parameter
  structural coefficient rescaling `fourierlearn.reference`'s own oracle
  already applies (`_build_grid`'s `domain_length = 2/coefficient`) — for
  the mandated single-coefficient-`1.0` fixture this reduces to the simple
  `exp(i*pi*l*alpha_j)` form, but the general formula is required so this
  feature is not silently wrong for any fixture with a non-unit
  per-parameter coefficient, mirroring an audit finding `reference.py`'s own
  docstring already records for the oracle's grid construction.
