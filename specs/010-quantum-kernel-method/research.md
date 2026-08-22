# Phase 0 Research: Quantum Kernel Method for FCE

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Note on scope**: spec.md's FR-012 already recorded that this feature's
three core grounding claims (the `Rz(α_s)YRz(α_s)` cancellation and its
exponential-ambient/fixed-support scaling; the Figure 5.8 kernel-overlap
circuit's exact formula; the noisy-KRR bound formula itself) were verified
computationally BEFORE the spec was written, and instructed this phase to
cite and extend those findings rather than re-derive them. This document
does exactly that — R1 below is new work (this round's own critical
mandate); R2 briefly recaps, without re-executing, what spec.md's
Assumptions already established.

## R1 — Mandate 1: realistic-noise tightness of the noisy-KRR bound (executed)

**Question**: is eq. 5.94's bound (`|h_{K̂,Ŷ}-h_{K,Y}| ≤ (κM/λ₀²)ε_k +
(κ/λ₀)ε_y + (M/λ₀)ε_k`) practically tight, or loose/vacuous, at the noise
scales this project's own shot-based pipeline would actually produce?

**Realistic `ε_k, ε_y` derived from Spec 4's own Hoeffding formula**
(`tests/oracle/test_extract_convergence.py`'s own
`_hoeffding_eps(shots, delta) = sqrt(2*ln(2/delta)/shots)`, `δ=0.01` — the
exact convention this project already tests with, not a new one invented
for this spec) — at the exact shot counts that same test already exercises
(`2,000`, `20,000`, `200,000`):

```
shots=2,000    -> eps = 0.07279
shots=20,000   -> eps = 0.02302
shots=200,000  -> eps = 0.00728
```

**Executed — 500-trial sweep at each shot count** (random `T∈[3,7]`,
`d∈[2,5]` regression problems, `λ₀` drawn uniformly from `[0.05, 1.0]`,
`ε_k=ε_y` set to that shot count's own Hoeffding value, noise drawn
adversarially within the entrywise bound):

```
shots=  2,000  violations=0/500  mean(rhs/M)=1.919  median(rhs/M)=0.713  p90(rhs/M)=4.359
shots= 20,000  violations=0/500  mean(rhs/M)=0.587  median(rhs/M)=0.225  p90(rhs/M)=1.120
shots=200,000  violations=0/500  mean(rhs/M)=0.188  median(rhs/M)=0.070  p90(rhs/M)=0.443
```

(`rhs` = eq. 5.94's own bound value; `M` = the label-magnitude scale the
bound itself is stated in terms of — `rhs/M` is therefore the bound's own
size relative to the quantity it is bounding, the natural measure of
whether it is "tight" or "vacuous.")

**Finding — the bound is a valid but often LOOSE-TO-VACUOUS guarantee at
realistic pipeline shot counts, confirmed by execution, not assumed**:

- **Zero violations at every shot count** (`0/500` in all three sweeps):
  the bound formula itself, as transcribed in spec.md FR-007, is correct
  and never breached — this reconfirms, at REALISTIC noise magnitudes,
  what the original pre-FR Monte Carlo check (spec.md Finding 3) already
  established at arbitrary noise magnitudes.
- **At `2,000` shots** (a plausible "quick" pipeline default): the bound
  EXCEEDS the label magnitude on average (`mean rhs/M=1.92`) and is
  `4.4×` the label magnitude in the worst 10% of cases (`p90=4.36`) — a
  bound larger than the quantity it constrains is **vacuous**: it
  permits "the prediction could be off by more than the entire signal,"
  which asserts nothing useful.
- **At `20,000` shots**: `median rhs/M=0.225` (loose but not vacuous in
  the typical case) while `p90=1.12` (still vacuous in the worse cases) —
  a MIXED, honestly-reportable picture, not uniformly one or the other.
- **At `200,000` shots** (a large, expensive shot count): `median
  rhs/M=0.070`, `p90=0.443` — the bound becomes reasonably informative in
  typical cases, though still loose (up to `~44%` of the label magnitude)
  in worse cases.
- **The bound is always far looser than the ACTUAL error**: across every
  sweep, the true error (`lhs`) is only `~3.5%` of the bound (`mean
  lhs/rhs` between `0.035` and `0.038` in all three sweeps) — the bound's
  looseness is not merely "sometimes wide," it is systematically
  pessimistic by roughly a factor of `~28×` on average, at every tested
  shot count.

**Executed — `λ₀` sensitivity** (fixed regression problem, `20,000`
shots' own `ε=0.02302`): the bound scales as `1/λ₀²`, so its tightness
depends strongly on the regularization strength, independent of shot
count:

```
lambda0=0.02: rhs/M=32.60   (wildly vacuous)
lambda0=0.05: rhs/M=6.07    (vacuous)
lambda0=0.1:  rhs/M=1.87    (vacuous)
lambda0=0.2:  rhs/M=0.65    (loose)
lambda0=0.5:  rhs/M=0.19    (borderline informative)
lambda0=1.0:  rhs/M=0.08    (informative)
lambda0=2.0:  rhs/M=0.04    (informative)
```

**Conclusion, honestly stated (Constitution §8.3)**: the noisy-KRR bound
is a mathematically valid (never-violated) but frequently LOOSE, and at
low shot counts or weak regularization VACUOUS, guarantee. It becomes
genuinely informative only at the combination of large shot counts
(`≳200,000`) and moderate-to-strong regularization (`λ₀≳0.5`). This is not
a defect in the transcription (R1's own `0/500` violations at every
tested scale prove the formula is correctly applied) — it is a property
of the bound itself, and MUST be surfaced structurally, not buried in
this document (Critical Mandate 1 below).

## R2 — Module architecture for the structural tightness sentinel (Critical Mandate 1)

**Decision — a new `NoisyKRRBound` result type**, analogous in spirit to
Spec 5's `PacBound`/`weight_space_translation_status` (a structural field
recording a known limitation directly on the result object, never only in
a docstring or markdown file):

```python
@dataclass(frozen=True)
class NoisyKRRBound:
    error_bound: float                     # eq. 5.94's own rhs value
    reference_magnitude: float              # M -- the scale the bound is stated against
    bound_to_reference_ratio: float         # error_bound / reference_magnitude
    tightness_status: str                   # "informative" | "loose" | "vacuous"
    epsilon_k: float
    epsilon_y: float
    lambda0: float
    kappa: float
```

**Decision — the three-way `tightness_status` thresholds**, chosen from
R1's own executed distribution (not an arbitrary round number invented
without evidence): `ratio < 0.2` → `"informative"` (R1's `200,000`-shot
median `0.070` and `20,000`-shot median `0.225` straddle this line,
matching the qualitative "typical case is usable" finding); `0.2 ≤ ratio
< 1.0` → `"loose"` (covers R1's `20,000`-shot median/`200,000`-shot p90
range, where the bound is a real but weak constraint); `ratio ≥ 1.0` →
`"vacuous"` (covers R1's `2,000`-shot mean/`20,000`-shot p90 — the bound
permits an error at least as large as the signal itself). These exact
cut points are a `/speckit-tasks`-level constant, not hardcoded
per-call — a future spec may recalibrate them without touching this
type's own shape.

**Decision — `tightness_status` is always populated, never optional**:
every noisy-KRR prediction (spec.md FR-006/FR-007) MUST return a
`NoisyKRRBound` alongside the prediction — mirroring Spec 5's own
non-negotiable rule that `weight_space_translation_status` is a required,
always-present field, never a field a caller can accidentally omit or
silently ignore.

## R3 — Constraint on `/speckit-tasks`

- The Hoeffding-derived `ε_k`/`ε_y` inputs to `NoisyKRRBound` MUST be
  computed via the SAME formula this project already uses
  (`sqrt(2*ln(2/δ)/shots)`, reused from
  `tests/oracle/test_extract_convergence.py`'s own convention) — never a
  new, independently-invented tolerance formula.
- A dedicated test MUST reproduce R1's own three-shot-count sweep
  (`2,000`/`20,000`/`200,000`) and assert the resulting `tightness_status`
  matches R1's own qualitative finding at each (`"vacuous"` at `2,000`
  shots' mean case, `"loose"`-or-`"vacuous"` mixed at `20,000`,
  improving at `200,000`) — not merely that the field exists.
- No task may present a noisy-KRR prediction's error bound as a bare
  number without its accompanying `NoisyKRRBound.tightness_status` —
  Constitution §8.3's "state what is and is not established" applies to
  every reported prediction, not just a documentation aside.

## R4 — Optimisation discipline (Constitution §5.3)

**Decision**: no caching, batching, or memoization anywhere in this
design. `NoisyKRRBound`'s own computation is `O(1)` given `K, Y, F` and
their noise bounds; the kernel-overlap circuit (User Story 1) and Gram-
matrix construction (`O(T²)` calls, spec.md FR-005) already state their
own cost explicitly — no additional optimisation is proposed or needed at
this feature's declared small-instance scope.
