# Feature Specification: Quantum Kernel Method for FCE (PAC-Efficient Regime)

**Feature Branch**: `010-quantum-kernel-method`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Quantum Kernel Method for FCE, PAC-efficient regime (Spec 10). Deliverables: (a) The kernel evaluation circuit (Barthe thesis Figure 5.8, detailed in §5.7.7, eq. 5.72-5.78) estimating k(x,x') = b(x)·b(x') via overlap of the extracted Fourier-coefficient feature states for two classical inputs x, x' — reusing Spec 3's compile_frequency_circuit (A(U)) unchanged, plus a new Hadamard-test-style selector qubit that conditionally prepares the x-vs-x' branch before the shared A(U) runs, and Spec 9's LCU construction where the observable is a weighted sum. (b) Kernel ridge regression on the resulting T×T Gram matrix, including the noisy variant (§5.7.8, eq. 5.79-5.94) accounting for finite-shot kernel-estimate noise — never a noiseless placeholder, per this project's measurement-only discipline. (c) The PAC-efficiency conditions themselves (§5.7.7, §5.5.1-5.5.2): the concept-class construction where an a priori exponential frequency spectrum collapses to polynomial support via parameter cancellation (the thesis's own Rz(αs)YRz(αs) example). CRITICAL MANDATES: 1. Scope discipline (§11.11): classical-input kernel only, never a fidelity kernel over α. 2. No advantage claim on Z₂ (§11.8). 3. Pre-FR numerical verification (§2.2/§4.1), already executed this session using this project's own actual pipeline code — three findings (cancellation identity + exponential-ambient/fixed-support scaling; kernel-overlap circuit exact match to 5.6e-16; noisy-KRR bound 0/500 Monte Carlo violations) must ground the FRs directly."

## Clarifications

### Session 2026-08-21 (`/speckit-clarify`)

- **Fixture scope precision**: User Story 3's cancelling-parameter
  concept class is a purpose-built demonstration fixture. No claim is
  made, and none was intended, that this project's existing Z₂/TFIM
  models (Specs 6-8) exhibit this cancellation property naturally — no
  such analysis exists. FR-013 (below) and User Story 3's own
  introduction and Acceptance Scenario 4 are updated to make this
  explicit, since the original wording could be read as connecting the
  two.
- **Noisy-KRR bound realism**: the pre-FR Monte Carlo verification
  (Finding 3) used generic, arbitrary-magnitude noise (`ε_k, ε_y` drawn
  from `1e-4` to `1e-2`) to confirm the bound formula (eq. 5.94) is
  transcribed correctly and never violated — it does NOT by itself show
  the bound is *practically tight* (a useful, actionable constraint) at
  the noise scales this project's own shot-based pipeline (Spec 4) would
  actually produce. The Assumptions section now requires `/speckit-plan`
  to test the bound's tightness using realistic shot-noise scales derived
  from Spec 4's own Hoeffding-type concentration bounds for actual
  pipeline shot counts, and to report honestly (Constitution §8.3) if the
  bound turns out loose or practically vacuous at those scales, rather
  than silently presenting it as a tight constraint.

## User Scenarios & Testing *(mandatory)*

<!--
  This feature activates EXT-002 (Quantum Kernel, already registered as
  "deferred — scheduled after Z₂ LGT validation," now complete per Spec 8).
  All three deliverables were numerically grounded BEFORE this spec was
  drafted (Constitution §2.2/§4.1's own discipline, applied at the
  specify stage per this round's explicit mandate) — every quoted number
  below is an executed result, not a promise.
-->

### User Story 1 - Evaluate the kernel overlap k(x,x')=b(x)·b(x') for two classical inputs (Priority: P1)

A developer has two classical inputs `x, x'` (each selecting its own fixed
gates within an otherwise-identical encoded-parameter structure, per
Constitution §7.1) and wants the kernel value `k(x,x')=b(x)·b(x')` — the
inner product of their respective Fourier-coefficient feature vectors —
estimated directly on a quantum circuit, without ever materializing either
feature vector classically first.

**Why this priority**: This is the foundational deliverable — every other
capability in this spec (kernel ridge regression, the PAC-efficiency
demonstration) either consumes this evaluation's output or exists to
justify it. Without it, "estimate a kernel value" is not a capability this
codebase has at all.

**Independent Test**: Can be fully tested by declaring a small circuit
with two distinct classical inputs, running the overlap circuit, and
confirming the result matches an independently-computed
`Re(⟨b(x)|b(x')⟩)` — already done (Verified Finding 2, below) to a
diff of `5.6e-16` on a concrete 1-qubit/1-parameter fixture (two `RY`
fixed-gate choices, `0.9` and `1.7` radians, selecting `x` and `x'`
respectively), reusing Spec 3's `compile_frequency_circuit` completely
unmodified.

**Acceptance Scenarios**:

1. **Given** two classical inputs `x, x'` sharing the same encoded-
   parameter structure, **When** the overlap circuit is built, **Then** it
   prepares a selector qubit into `|+⟩`, selector-controls which of `x`'s
   or `x'`'s own fixed gates are applied to the circuit register, then
   applies the SAME, UNMODIFIED `A(U)` construction (Spec 3's
   `compile_frequency_circuit`) regardless of the selector's state — never
   a separately-compiled `A(U)` per branch.
2. **Given** the same circuit, **When** its result is read out, **Then**
   it is the expectation value of `Z` on the selector qubit, tensored with
   identity on the frequency/ancilla registers, tensored with a `|0⟩⟨0|`
   projector on the circuit register (eq. 5.78) — **verified** (Verified
   Finding 2) to equal `Re(⟨b(x)|b(x')⟩)` to machine precision, not merely
   asserted from the thesis's own derivation.
3. **Given** an observable expressed as a weighted sum of Pauli strings
   rather than a single Pauli string, **When** this feature needs to fold
   it into the overlap construction, **Then** it reuses Spec 9's LCU
   construction (`compile_observable_circuit`'s multi-term branch)
   unmodified — never a second, independently-implemented weighted-sum
   folding mechanism.
4. **Given** any declared classical input pair, **When** this feature's
   own circuit or estimate is described, **Then** it is described as a
   kernel over the classical inputs `x, x'` only — **never** as, and
   never silently drifting into, a fidelity kernel over the encoded
   parameters `α` (Critical Mandate 1, Constitution §11.11 — a
   structurally different, unrelated construction this spec does not
   build).

---

### User Story 2 - Perform kernel ridge regression on the estimated Gram matrix, honestly accounting for finite-shot noise (Priority: P2)

A developer has `T` classical training inputs, wants the `T×T` Gram
matrix `K=[⟨b(x_t)|b(x_t')⟩]` built from `O(T²)` calls to User Story 1's
overlap evaluation, and wants to run kernel ridge regression (KRR) on it —
with the estimate's own finite-shot noise on `K`, the training labels
`Y`, and any new test-point evaluation `F` propagated honestly into the
reported prediction error, never silently treated as if the estimate were
exact (Constitution §1.1/§3.1's measurement-only discipline).

**Why this priority**: Depends on User Story 1 (there is no Gram matrix
without the overlap evaluation), but is not optional polish — a
noiseless-Gram-matrix KRR implementation would misrepresent every
measurement-derived kernel value in this project as if it had zero
uncertainty, which this project's own foundational discipline forbids
for every other quantity it reports.

**Independent Test**: Can be fully tested by declaring a small, explicit
regression problem (a data matrix, weights, and a test point), computing
exact KRR and a noisy variant with entrywise-bounded, adversarially-drawn
noise on `K`, `Y`, and the test-evaluation vector `F`, and confirming the
resulting prediction-error bound (eq. 5.94) is never violated — already
done (Verified Finding 3, below): `500` random Monte Carlo trials
(`T` up to `7`, `d` up to `5`, random noise magnitudes drawn per trial),
**zero** bound violations, with the largest observed ratio of actual
error to the theoretical bound being `0.259` (i.e., the bound held with
margin in every trial, not just on average).

**Acceptance Scenarios**:

1. **Given** `T` training inputs and their estimated feature vectors,
   **When** the Gram matrix is built, **Then** it requires exactly
   `O(T²)` calls to User Story 1's overlap evaluation — never more.
2. **Given** a noisy Gram matrix `K̂=K+E_K`, noisy labels `Ŷ=Y+E_Y`, and a
   noisy test-evaluation vector `F̂=F+E_F`, each bounded entrywise by
   `ε_k` or `ε_y` respectively, **When** KRR is performed, **Then** the
   reported prediction error satisfies
   `|h_{K̂,Ŷ}(x')-h_{K,Y}(x')| ≤ (κM/λ₀²)ε_k + (κ/λ₀)ε_y + (M/λ₀)ε_k`
   (eq. 5.94) — **verified** (Verified Finding 3) never to be violated
   across `500` random trials, not merely cited from the thesis.
3. **Given** any reported KRR prediction, **When** it is presented,
   **Then** it is presented alongside this noise bound (or the
   quantities needed to compute it) — never as a bare number implying
   exactness, per Constitution §1.1/§3.1.

---

### User Story 3 - Demonstrate a concept class whose a priori exponential spectrum collapses to polynomial support (Priority: P3)

A developer wants to construct — and computationally verify, not merely
assert — a concept class with `d∈O(poly(n))` a priori encoded parameters
whose AMBIENT frequency box therefore scales exponentially in the number
of parameters, but whose ACTUAL, extracted nonzero frequency support
stays fixed regardless of how many such parameters are added, because
most of them cancel by construction (the thesis's own worked example,
`Rz(α_s)YRz(α_s)`) — leaving only a handful of "surviving" parameters
that determine the function's real content.

**Scope precision (Clarifications 2026-08-21)**: this concept class is a
**purpose-built fixture**, assembled specifically to exhibit the
cancellation property — it is a deliberately constructed demonstration,
not an analysis of any existing model. It is entirely unrelated to, and
makes no claim whatsoever about, whether this project's existing Z₂/TFIM
models (Specs 6-8) happen to exhibit this same cancellation naturally;
no such analysis has been performed, and none is implied by anything in
this User Story. Acceptance Scenario 4, below, is a separate, general
guardrail about labeling — it governs any *unrelated, optional*
pipeline-validation fixture someone might separately choose to build on
the `Z₂` platform, not the cancelling-parameter construction itself.

**Why this priority**: This is the theoretical justification for why User
Stories 1-2's kernel approach can be PAC-efficient at all in a regime
where a naive parameter count would suggest otherwise — but it is ranked
last because it demonstrates a *property of a constructed example*,
independent of whether the kernel-evaluation circuit or KRR exist yet.

**Independent Test**: Can be fully tested by declaring a circuit with one
"surviving" parameter and one or more "cancelling" `Rz(α_s)YRz(α_s)`-
sandwich parameters, extracting its Fourier coefficients via the exact
oracle, and confirming the extracted support size stays constant as
cancelling parameters are added while the ambient box grows — already
done (Verified Finding 1, below).

**Acceptance Scenarios**:

1. **Given** the gate identity `Rz(α_s)·Y·Rz(α_s)`, **When** it is built
   in this project's own `e^{iπcαP}` gate convention (two tied uploads of
   the same parameter sandwiching a fixed `Y` gate) and evaluated at a
   concrete `α_s`, **Then** the result equals `Y` exactly — **verified**
   (Verified Finding 1) to a diff of `0` to `2.2e-16` across five tested
   values of `α_s` (including `0`, positive, and negative), confirming
   the cancellation is exact and `α_s`-independent, not approximate.
2. **Given** a small IR with one surviving parameter (a single, r_j=1
   upload) and one cancelling parameter (the sandwich above, upload_count
   `2`), **When** its Fourier coefficients are extracted via the exact
   oracle, **Then** the extracted support has exactly `2` nonzero
   elements, both with the cancelling parameter's own coordinate pinned
   at `0` — **verified** (Verified Finding 1) as `{(-2,0), (2,0)}`
   against an ambient box of `45` points (`5×9`).
3. **Given** the same construction extended to TWO independent cancelling
   parameters, **When** its Fourier coefficients are extracted the same
   way, **Then** the ambient box grows multiplicatively (to `405=45×9`,
   confirming exponential-in-the-number-of-cancelling-parameters growth)
   while the extracted support size stays fixed at exactly `2` elements
   (`{(-2,0,0), (2,0,0)}`, both cancelling coordinates still pinned at
   `0`) — **verified** (Verified Finding 1), not asserted by extrapolation
   from the one-cancelling-parameter case alone.
4. **Given** any *separate, optional* fixture someone chooses to build for
   pipeline-validation purposes on the `Z₂` LGT platform (Specs 6-8) —
   distinct from, and not a substitute for, this User Story's own
   purpose-built cancelling-parameter construction (Scenarios 1-3) —
   **When** it is presented, **Then** it is labeled explicitly as
   pipeline-validation only — **never** as a demonstrated quantum
   learning advantage (Critical Mandate 2, Constitution §11.8): this
   platform's own frequency-restriction mechanisms are classically
   computable and would help a classical learner exactly as much as a
   quantum one, independent of anything this spec's own cancellation
   construction demonstrates.

---

### Edge Cases

- What happens when `x=x'` (the kernel's own diagonal entry,
  `k(x,x)=‖b(x)‖²`)? The overlap circuit must still return a valid,
  real, non-negative value — a degenerate input for the *selector*
  register (both branches identical) but not for the overlap formula
  itself, which reduces cleanly to the squared norm case.
- What happens when the declared observable for the overlap fold is a
  single Pauli string rather than a weighted sum? Spec 9's LCU
  construction already reduces to Spec 3's original, unmodified single-
  term path in that case (Spec 9 FR-004) — this feature relies on that
  existing guarantee rather than re-implementing a single-term special
  case.
- What happens if the noisy-KRR bound's inputs (`ε_k, ε_y, λ₀, κ, M`) are
  not all available or not all positive? The bound is undefined/vacuous
  in that case and MUST be reported as such rather than silently
  computing a nonsensical or negative "bound."
- What happens when a concept-class fixture (User Story 3) declares a
  cancelling parameter whose two uploads use DIFFERENT structural
  weights (breaking the exact `Rz(α_s)YRz(α_s)` symmetry)? The
  cancellation is no longer guaranteed and MUST NOT be assumed — this
  feature's own verified claim (Verified Finding 1) applies only to the
  exact, tied, equal-weight sandwich construction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (Deliverable a): The system MUST provide a kernel overlap
  evaluation circuit for two classical inputs `x, x'`, built from a
  selector qubit prepared into `|+⟩`, a selector-controlled preparation
  of `x`'s or `x'`'s own fixed gates, and Spec 3's `compile_frequency_circuit`
  reused completely unmodified as the shared `A(U)` (eq. 5.72-5.77).
- **FR-002**: The system MUST read out the kernel value as the
  expectation of `Z` on the selector qubit, tensored with identity on the
  frequency/ancilla registers and a `|0⟩⟨0|` projector on the circuit
  register (eq. 5.78) — verified (Finding 2) to reproduce
  `Re(⟨b(x)|b(x')⟩)` to machine precision (`5.6e-16` on the concrete
  fixture cited above).
- **FR-003**: When the observable folded into the overlap construction is
  a weighted sum of Pauli strings, the system MUST reuse Spec 9's LCU
  construction (`compile_observable_circuit`'s multi-term branch)
  unmodified — never a second, independently-implemented weighted-sum
  folding mechanism (Constitution §9.4).
- **FR-004** (**Scope discipline**, Critical Mandate 1, Constitution
  §11.11): Every capability this feature provides MUST operate over
  classical inputs `x, x'` only. The system MUST NOT provide, and MUST
  NOT be extendable by accident into providing, a fidelity kernel over
  the encoded parameters `α` — a structurally different, unrelated
  construction.
- **FR-005** (Deliverable b): The system MUST build the `T×T` Gram matrix
  `K=[⟨b(x_t)|b(x_t')⟩]` using exactly `O(T²)` calls to FR-001/FR-002's
  overlap evaluation.
- **FR-006**: The system MUST perform kernel ridge regression on the
  resulting Gram matrix, and MUST provide the noisy variant (eq. 5.79-
  5.94) accounting for entrywise-bounded noise on the Gram matrix, the
  training labels, and any new test-point evaluation — never a noiseless
  placeholder (Constitution §1.1/§3.1).
- **FR-007**: The system MUST report, alongside every noisy-KRR
  prediction, the error bound `|h_{K̂,Ŷ}(x')-h_{K,Y}(x')| ≤
  (κM/λ₀²)ε_k + (κ/λ₀)ε_y + (M/λ₀)ε_k` (eq. 5.94) or the quantities
  needed to compute it — verified (Finding 3) not to be violated across
  `500` random Monte Carlo trials (max observed ratio of actual error to
  bound: `0.259`).
- **FR-008**: If any of the bound's own required inputs (`ε_k, ε_y, λ₀,
  κ, M`) is missing or non-positive, the system MUST report this
  explicitly rather than compute or display a vacuous or negative
  "bound" (Constitution §10.1).
- **FR-009** (Deliverable c): The system MUST provide a way to construct
  a concept-class fixture containing one or more "cancelling" parameters
  built from the exact `Rz(α_s)YRz(α_s)` sandwich (two tied uploads of one
  parameter around a fixed `Y` gate) — verified (Finding 1) to cancel to
  `Y` exactly (diff `0`-`2.2e-16`) independent of `α_s`'s value or sign.
- **FR-010**: The system MUST demonstrate, via the exact reference oracle
  (not a shot-based or approximate extraction), that adding cancelling
  parameters grows the ambient frequency box multiplicatively while the
  actual extracted support size stays fixed — verified (Finding 1) for
  one cancelling parameter (ambient `45`, support `2`) and two independent
  cancelling parameters (ambient `405`, support still `2`).
- **FR-011** (**No advantage claim on Z₂**, Critical Mandate 2,
  Constitution §11.8): Any fixture for FR-009/FR-010 built on the `Z₂`
  LGT validation platform (Specs 6-8) MUST be labeled explicitly as
  pipeline-validation only in every place it is reported — never
  presented, or presentable by omission, as a demonstrated quantum
  learning advantage.
- **FR-012** (**Pre-FR verification already performed**, Critical
  Mandate 3, Constitution §2.2/§4.1): This spec's own three grounding
  claims (FR-001/FR-002's overlap formula, FR-006/FR-007's noisy-KRR
  bound, FR-009/FR-010's cancellation mechanism) were verified
  computationally, using this project's own actual pipeline code, BEFORE
  this specification was written — the verification is not deferred
  future work, and `/speckit-plan`'s own Phase 0 research MUST cite and
  extend these exact findings (with their concrete numbers) rather than
  re-deriving them from scratch.
- **FR-013** (**Fixture scope precision**, Clarifications 2026-08-21):
  FR-009/FR-010's cancelling-parameter concept class is a purpose-built
  demonstration fixture. The system MUST NOT claim, state, or imply —
  anywhere it is reported — that this project's existing Z₂/TFIM models
  (Specs 6-8) exhibit this cancellation property naturally; no such
  analysis has been performed as part of this feature, and none is a
  prerequisite for FR-009/FR-010's own claim, which concerns only the
  purpose-built fixture itself.

### Key Entities *(include if feature involves data)*

- **Classical input pair `(x, x')`**: Two declarations of which fixed
  gates to apply within an otherwise-shared encoded-parameter structure
  (Constitution §7.1) — the kernel's own two arguments; never encoded
  parameters (`α`) themselves (FR-004).
- **Kernel overlap circuit**: The selector-qubit-based construction
  (FR-001/FR-002) whose `Z⊗I⊗|0⟩⟨0|` expectation value is
  `Re(⟨b(x)|b(x')⟩)`.
- **Gram matrix and noise bookkeeping**: The `T×T` matrix `K` (FR-005),
  its noisy counterpart `K̂=K+E_K`, and the accompanying noisy labels
  `Ŷ=Y+E_Y` and test-evaluation vector `F̂=F+E_F` — each with its own
  entrywise noise bound (`ε_k` or `ε_y`), carried through to the reported
  prediction-error bound (FR-006/FR-007).
- **Cancelling-parameter fixture**: A declared circuit fragment
  (`Rz(α_s)YRz(α_s)`, FR-009) whose own frequency coordinate is
  guaranteed pinned at `0` in the extracted support, used to construct
  the a-priori-exponential/actually-polynomial concept class (FR-010).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can declare two classical inputs and obtain a
  kernel value matching an independently-computed `Re(⟨b(x)|b(x')⟩)` to
  machine precision, without ever materializing either input's full
  feature vector classically.
- **SC-002**: A developer can build a `T×T` Gram matrix using exactly
  `O(T²)` overlap evaluations, and obtain a kernel ridge regression
  prediction accompanied by an explicit, never-violated error bound
  whenever finite-shot noise bounds are supplied.
- **SC-003**: A developer can construct a concept-class fixture where
  adding another cancelling parameter leaves the extracted frequency
  support size unchanged while the ambient frequency box grows
  multiplicatively — demonstrated for at least two independent
  cancelling parameters, not merely one.
- **SC-004**: No result produced by this feature is ever presented, or
  presentable, as a fidelity kernel over encoded parameters, or as a
  demonstrated learning advantage on the `Z₂` validation platform —
  audited by both being structurally impossible (FR-004) or explicitly
  labeled (FR-011) in every reported result.
- **SC-005** (Clarifications 2026-08-21): The noisy-KRR bound's practical
  tightness at realistic, pipeline-derived shot-noise scales is reported
  honestly — either as a genuinely useful, actionable constraint at those
  scales, or explicitly flagged as loose/practically vacuous there — never
  silently presented as tight based only on the generic, arbitrary-
  magnitude Monte Carlo check already performed (Finding 3).

## Assumptions

- This feature builds on the completed Foundation Layer (Spec 1),
  Encodings Layer (Spec 2), Circuits Layer (Spec 3:
  `compile_frequency_circuit`, reused unmodified), Extract Layer (Spec 4),
  and the LCU extension (Spec 9: `compile_observable_circuit`'s multi-term
  branch, reused unmodified for FR-003). Specs 5-8 are not touched by this
  feature, except as an explicitly labeled (FR-011), never load-bearing,
  source of optional pipeline-validation fixtures.
- **Primary source**: `docs/references/Barthe_thesis.pdf` (verified
  in-session): §5.5.1 (p.120, "Exponentially large spectrum"), §5.5.2
  (p.121-122, the kernel definition eq. 5.21-5.22 and the
  `Rz(α_s)YRz(α_s)` worked example), §5.7.7 (p.140-141, the concept class
  and Gram-matrix setup, eq. 5.72-5.73, and Figure 5.8/eq. 5.74-5.78, the
  overlap circuit), §5.7.8 (p.141-143, the noisy-KRR derivation, eq.
  5.79-5.94).
- **All three of this spec's grounding claims were verified computationally
  in-session, before this spec was written** (Constitution §2.2/§4.1,
  Critical Mandate 3) — see Functional Requirements above for the exact
  cited numbers. This is a documented departure from this project's usual
  phase sequencing (verification normally lives in `/speckit-plan`'s Phase
  0 research) — done here because the user explicitly required it before
  the FRs could be trusted to state a correct formula.
- **The exact circuit-level mechanism for the selector-controlled `x`-vs-
  `x'` fixed-gate preparation (FR-001) for an ARBITRARY pair of classical
  inputs (not just the two-branch, single-qubit selector case already
  verified) is a `/speckit-plan`-level decision** — this spec requires
  only that it reuses `compile_frequency_circuit` unmodified and is
  verified against the same `Re(⟨b(x)|b(x')⟩)` ground truth on at least
  one additional, richer fixture before being trusted generally.
- **The noisy-KRR implementation's exact numerical-linear-algebra
  approach (e.g., how a corrected-to-be-positive-semi-definite `K̂` is
  obtained per the thesis's own citation [167]) is a `/speckit-plan`-level
  decision** — this spec requires only that the resulting bound (FR-007)
  is verified, not any specific PSD-correction algorithm.
- **Noisy-KRR bound realism mandate (Clarifications 2026-08-21,
  Constitution §4.4/§8.3)**: Finding 3's `500`-trial Monte Carlo check
  used generic, arbitrary-magnitude noise (`ε_k, ε_y` in `1e-4`-`1e-2`) to
  confirm the bound formula (eq. 5.94) is transcribed correctly — it does
  **not** by itself establish that the bound is *practically tight* (a
  useful, actionable constraint) at the noise scales this project's own
  shot-based pipeline would actually produce. `/speckit-plan`'s own
  Phase 0 research MUST additionally re-test the bound using `ε_k, ε_y`
  values DERIVED from Spec 4's own Hoeffding-type concentration-bound
  tolerances for realistic pipeline shot counts (Constitution §4.4) —
  not generic random magnitudes. If the bound turns out loose or
  practically vacuous at those realistic scales (e.g., so wide it permits
  almost any prediction error, or requiring shot counts far beyond what
  this project's pipeline would use), this MUST be reported honestly as a
  documented limitation (Constitution §8.3 — state what is and is not
  established) rather than silently presented as a tight, actionable
  constraint.
- This feature validates against small, explicit, hand-constructed
  classical-input pairs, regression problems, and cancelling-parameter
  fixtures — no production-scale dataset or circuit is targeted here.
