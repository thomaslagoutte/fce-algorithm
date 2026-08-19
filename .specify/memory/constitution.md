# Constitution — `fce`: Fourier Coefficient Extraction

**Version:** 1.3.0 · **Scope:** all specs, plans, tasks, and code in this repository.

Implements Barthe's FCE algorithm and learning pipeline as a shot-based Qiskit package,
extended to an equivariant Pauli-encoded ansatz for lattice gauge theory.

Every rule below was written after a specific failure. Where a rule carries a
*Rationale*, that rule has previously been violated by well-intentioned optimisation —
read it before overriding. Where a plan conflicts with a rule, the rule wins until
amended; stop and report the conflict.

---

## 1. Hard prohibitions

Never, regardless of instruction, benchmark, or apparent benefit:

1. Read amplitudes (`Statevector(...).data`, `.probabilities()`, amplitude indexing) to
   obtain any extracted or learned quantity, in any production-path module.
2. Provide an "exact" / `shots=None` / infinite-shot execution mode.
3. Synthesise shot noise by sampling around an exactly computed value.
4. Train on labels produced by the same approximation as the feature map.
5. Reduce the extracted frequency set below what the spec requires.
6. Restrict extraction to a sublattice whose containment has not been empirically verified
   (§12.6).
7. Wrap a circuit block beyond a few qubits in `.control()`.
8. Assert what a source says without verifying it in-session.

*Rationale (1–4):* each of these **improves** apparent accuracy or speed while destroying
the result's meaning. They are the failure modes an optimising agent reaches for first.

---

## 2. Scientific fidelity

**2.1** Every algorithmic decision cites its source section/definition/theorem inline.

**2.2** Unverifiable claims about a source are marked as unverified in the spec and
flagged for human confirmation. Claiming a source contains an error requires in-session
verification. Refining a source's bound is not the same as the source being wrong; state
it as a refinement.

**2.3** Anything not in the source is marked `EXTENSION` with what it adds and assumes,
and is listed in one in-repo extension register with its validation status.

**2.4** Where faithful is slower than approximate, faithful ships. Approximations exist
only as named non-default alternatives with documented error.

---

## 3. Measurement-only production path

**3.1** The path is: build circuits → execute with finite shots → counts → estimated
expectations → Fourier coefficients.

**3.2** Aer's `statevector` *method* is permitted and expected as the simulator. The
prohibition is on inspecting the state, not on how it is simulated.

**3.3** Exact statevector and dense-matrix computation live only in `reference.py` plus
test helpers. It supplies ground truth and training labels; no production module imports it.

**3.4** CI fails if any production module imports `Statevector`, `Operator`, `expm`, or
`reference`.

---

## 4. Validation protocol

**4.1** Validate each component against exact ground truth in isolation before composing
it. A component with no passing oracle test is not done, however well it runs.

**4.2** Every layer has a ground truth: encodings vs. analytic coefficients; circuits vs.
oracle coefficients; sampled extractor vs. oracle within a statistical tolerance; learners
vs. the oracle's evaluated function.

**4.3** Every agreement test also asserts the quantity under test is non-trivial (e.g.
coefficients genuinely complex when testing a phase convention). A test that would pass on
a degenerate input is a defect.

**4.4** Shot-based tolerances are derived from a concentration bound for the configured
shot count and documented in the test. Tests pass for **any** seed. Choosing a seed until
a test passes is prohibited; loosening a tolerance requires a stated justification.

**4.5** Each phase ends with the full suite green and its oracle validation in place. No
phase is left partly integrated.

**4.6** Code not executed in the session that produced it is marked with what remains
unverified and which check settles it.

**4.7** Deferred work is a named `TODO` with its blocking condition. Silent partial
implementation is prohibited.

---

## 5. Optimisation discipline

**5.1** An optimisation is *physics-neutral* iff the resulting circuit is the same operator
and the estimator is the same estimator. Speed is the only permitted difference.

**5.2** Every circuit optimisation ships with an equivalence proof: `Operator.equiv`, or
oracle-coefficient agreement for pipeline changes. With ancillas: equivalence on the
non-ancilla subspace **plus** an ancilla-clean assertion. Unproven optimisations do not merge.

**5.3** No optimisation without a recorded profile identifying the bottleneck it targets.
Profile the path production actually uses — a profile of an alternative or abandoned
construction is not evidence about the live one.

**5.4** Device, parallelism, batch size, and synthesis mode are chosen by benchmark on
target hardware, and every default cites its benchmark. Timings count only if reproduced
across ≥2 trials; non-reproducible timings indicate contention, not a code property.

**5.5** Performance claims carry: before/after, hardware, qubits, depth, circuit count,
shots.

**5.6** Shots are configuration, not optimisation: reducing them for iteration changes only
the noise floor of an unchanged estimator, and every result records its shot count.

**5.7** Controlled constructions are assembled gate-by-gate using
`c-(U_K⋯U₁) = c-U_K⋯c-U₁` and `c-(Φ⁻¹MΦ) = Φ⁻¹(c-M)Φ` for self-inverse `Φ` applied
unconditionally. Both are exact; the result is still subject to 5.2.

**5.8** Dense `UnitaryGate` caching and parametrised-template transpilation are mutually
exclusive for the same sub-circuit — a frozen matrix cannot carry a `Parameter`. Plans state
which they use.

**5.9** Prefer the simple correct construction, validated, then optimise. Never deliver an
optimised construction whose unoptimised reference was never validated.

*Rationale (5.3–5.4):* configurations assumed beneficial and measured harmful include GPU
execution below ~20 qubits and forcing maximal experiment-level parallelism. Do not
generalise from a plausible mechanism to a setting.

---

## 6. Conventions

**6.1** Frequency sign, integer vs. relabelled (pre-/post-parity) indexing,
two's-complement decoding, and coordinate ordering are defined once, in one module, and
imported. Every function consuming or producing a frequency states its convention.

**6.2** Every frequency-count expression is annotated `pre-parity` or `post-parity`. Two
counts differing only in that annotation are not a contradiction; do not "reconcile" them
by changing a number.

**6.3** Register width is computed from upload count **and** per-parameter multiplicity
`r_j` by one named function. A regression test deliberately under-sizes a tied (`r_j > 1`)
parameter and asserts the aliasing signature is detected.

**6.4** Per-parameter scaling (e.g. Trotter step) never enters the frequency register,
which counts integers only; physical frequency is reconstructed in the interpretation layer.

---

## 7. Learning semantics

**7.1** Encoded parameters carry the frequencies and are unknown to the learner; the
classical input is known and selects fixed gates. Coefficients depend on the input, weights
on the unknown parameters.

**7.2** Training labels are exact. Trotterisation enters only through the feature map, as
bounded label noise.

**7.3** Under-determined regression is intended — sample complexity is logarithmic in the
frequency count. Never add a guard requiring more samples than features.

**7.4** The label-noise bound governs shot budget only. It must **not** scale or anchor the
regularisation penalty. Penalty selection is data-driven over an explicit, version-pinned
grid.

**7.5** Bounds that must hold uniformly over a concept class use constants computed
globally over the training set, not per input.

**7.6** Enforce conjugate symmetry so predictions are real. This shortcut is valid only for
Hermitian observables; assert that condition where it is used.

**7.7** Penalty selection uses only training data — k-fold cross-validation over the
training inputs, or an isolated holdout drawn from them. The held-out evaluation input and
its label may not influence penalty selection, feature scaling, or any other fitted
quantity, directly or by manual tuning against a reported metric.

**7.8** Assert that no evaluation input appears in the training set. Where inputs are
generated randomly, assert it after generation rather than assuming it.

*Rationale (7.4):* a penalty growing with evolution time shrinks small coefficients toward
zero and produces spurious late-time flattening indistinguishable from physics.

*Rationale (7.7):* tuning a hyperparameter until the reported curve looks better is
indistinguishable, in code, from tuning it properly — and converts a validation experiment
into a fit.

---

## 8. Honest results

**8.1** The learner's ceiling is its own feature map. Measure learner error against the
approximation the features encode, and approximation error against exact dynamics,
separately. Reporting only the gap to exact conflates two independent sources.

**8.2** If a prediction tracks exact dynamics **better** than its own feature map does,
treat it as a suspected artifact — typically label interpolation at a single parameter
value — and investigate. It may not be reported as a capability without a generalisation
test at a shifted parameter.

**8.3** Every experiment states in output and figure what it does and does not establish,
and which programme role it serves (§12.0).

**8.4** Negative results are documented in-repo with their failure mechanism. Removing
evidence of a failed direction is prohibited.

**8.5** Seed end to end, pin version-dependent defaults, write a run manifest (config,
versions, hardware, timings) beside outputs.

**8.6** Noise is a third, independent error source alongside learner error and
approximation error (§8.1), and is characterised in its own experiment, never folded into
correctness gates: §4 validation is noiseless, against the oracle. A noise characterisation
spec states the model used, reports the depth and circuit count it applies to, and reports
degradation rather than pass/fail. Any claim of hardware feasibility requires it.

---

## 9. Architecture

**9.1** `ir → encodings → circuits → extract → backends → learn → models → experiment`.
Dependencies point one way; no layer reaches around another.

**9.2** Cross-layer boundaries are typed Protocols in one contracts module. Backends,
learners, and encodings are interchangeable by configuration.

**9.3** One code path regardless of parameter count. Branching on dimensionality is
prohibited; per-parameter structure is data, not control flow.

**9.4** Strategy selection is configuration and injection, never duplicated call paths.

**9.5** Logic that changes which terms, frequencies, or gates exist *because of the model's
structure* is a physics decision: it lives in the model layer, derives from the Hamiltonian's
term structure, is documented, and is never a generic pruning heuristic in a circuit builder.

**9.6** Execution uses either `AerSimulator.run()` with `get_counts()` (the Aer-native
batched path) or `SamplerV2`. Prohibited: `qiskit.execute()`, V1 primitives, and
**`EstimatorV2` anywhere in the extraction path** — Estimator returns expectation values
rather than counts, abstracting away the layer §3.1 requires and permitting non-sampled
computation. Estimator may appear only inside `reference.py`.

**9.7** API surfaces change between Qiskit versions. Verify the current signature of any
execution, transpilation, or synthesis call in-session rather than from memory (§2.2), and
pin the Qiskit and Aer versions in the run manifest (§8.5).

---

## 10. Failure behaviour

**10.1** Degenerate, under-sampled, or out-of-range conditions raise or return an explicit
"unknown" — never a plausible wrong answer. A recovery routine that could be wrong on
insufficient data reports insufficiency instead.

**10.2** Unavailable hardware, method, or precision raises by default. Fallback is opt-in
and logged.

**10.3** Operations whose cost grows sharply with configuration predict and log that cost,
and refuse to exceed a configured budget without confirmation.

**10.4** Warnings are fixed or explicitly filtered with a recorded justification.

---

## 11. Research programme: symmetry-restricted extraction

**11.0** Target: extend FCE with an equivariant, Pauli-encoded ansatz for lattice gauge
theory, where an internal symmetry confines the frequency support to a classically
computable sublattice `Λ`, so extraction runs over `Λ` rather than the ambient box. `Z₂` is
the **validation platform**; `U(1)` is the **separation target**. Every spec states which
it serves.

**11.1** A symmetry may be used for equivariance only if all three hold, checked in the
spec before implementation:

 (a) **internal** — acts trivially on lattice labels;
 (b) **non-annihilating** — no Hamiltonian term is odd under it;
 (c) **abelian** — 1-d irreps, so sector-supported states lie in the commutant.

Rejections are recorded with their failure mode (§8.4).

*Rationale:* (a) a label-acting symmetry acts on the classical input, restricting admissible
inputs and collapsing the concept class. (b) annihilating a term deletes its dynamics;
deleting gauge-field dynamics freezes the links and yields a classically simulable
free-fermion family.

**11.2** Where the equivariant generator is a sum of commuting Pauli strings, those strings
share **one** parameter index, enforced in the IR — one parameter driving `r_j` gates.
A design in which they *can* receive independent parameters is rejected. The tied form is
the physically correct Trotterisation; untied breaks the symmetry and leaves the physical
sector.

**11.3** Multiplicity `r_j` propagates into counter range, register width, ambient count,
and extraction plan. Formulas valid only for `r_j = 1` are generalised or annotated.

**11.4** `Λ` is a named pre-processing stage with its own module, tests, and recorded cost —
derived in polynomial time from symmetry data (`F₂` elimination for parity constraints,
integer kernel/hyperplane intersection for additive ones) before any circuit runs. Not an
inline filter.

**11.5** `Λ`-enumeration must be polynomial in the ambient description; cost is predicted
and logged before it is paid. An exponential enumeration re-imports the cost the
restriction was meant to remove.

**11.6** Verify `Ω ⊆ Λ` empirically by brute-force support extraction against the oracle on
the smallest tractable instances, before `Λ`-restricted extraction is used for any reported
result. A violation is a **derivation defect**, localised to the specific constraint
violated. Λ-restricted extraction against an unverified `Λ` is prohibited (§1.6).

**11.7** Every sparsity claim states its mechanism: **additive** relations reduce
`rank Λ` and change the exponent; **multiplicative** relations reduce the index and change
only a prefactor. A constant-factor index gain is never described in language implying a
changed efficiency threshold, however large the constant.

**11.8** No separation claim on the validation platform. Because `Λ` is computable
classically from data the learner already has, symmetry-induced sparsity makes both
classical and quantum learners cheaper and cannot by itself be a separation. Any separation
claim identifies explicitly what the learner does **not** know.

**11.9** Assert theorem hypotheses in code, not comments: sector membership of state and
observable, circuit equivariance, the commuting-and-contiguous block, and graph
connectedness wherever a rank or Betti-number claim is used. Where a hypothesis has been
proven unnecessary, cite the proof and remove the assertion deliberately.

**11.10** Any stage that could reorder gates asserts the commuting block remains contiguous,
or the sublattice theorem does not apply to its output.

*Rationale:* transpilation and gate cancellation can break contiguity while preserving the
unitary — the one case where `Operator.equiv` (§5.2) is insufficient, because it invalidates
a *theorem* rather than a circuit.

**11.11** The thesis kernel is over classical inputs, `k(x,x') = b(x)·b(x')`. A fidelity
kernel over encoded parameters is a different construction and may not be presented as it.
The kernel route is reserved for the regime where rank collapse makes the support polynomial;
invoking it where the support stays exponential is prohibited, as its guarantee does not
hold there.

---

## Governance

**Amendment** requires stated rationale, motivating evidence, a version bump, and
propagation to dependent specs. Silent reinterpretation is not amendment.

**Versioning:** MAJOR removes/reverses a rule, MINOR adds one, PATCH clarifies without
changing obligations.

**Precedence:** constitution › specs › plans › tasks › code.

**Compliance:** every plan includes a check naming the rules it touches and how it
satisfies them; every PR states which were load-bearing.