# Phase 0 Research: Learning Backend Layer

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Note on this revision**: This research.md replaces the version written
before the 2026-08-21 clarify-session correction (an external review
correctly identified that the previous row model — a training row is one
directly-measured Fourier coefficient — gives an identity sensing matrix, on
which LASSO cannot perform genuine sparse recovery). Every section below is
either newly executed against the corrected model, or explicitly marked as
carried over unaffected.

## R1 — Corrected row/column semantics (Clarifications, 2026-08-21)

**Decision**: A training row is `(alpha_j, y_j)`: a concrete numeric
assignment `alpha_j` of every encoded parameter, and the real-valued
expectation `y_j = <0|U^dagger(alpha_j) P U(alpha_j)|0>` measured at that
assignment by a **new** primitive (R2/FR-014). `M` such rows form a genuine
Fourier sensing matrix (R3/FR-015), making `y = A b` an actually
under-determined linear system LASSO can solve for the sparse
`L`-dimensional coefficient vector `b` from `M << L` measurements.

**Why the previous decision was wrong**: measuring `b_l` directly makes the
sensing matrix the identity (one row = one one-hot coordinate of `b`).
LASSO on an identity design matrix is exactly per-coordinate soft
thresholding — it cannot recover any coefficient that was never itself
directly measured, so there is no sparse-recovery content in that setup at
all, regardless of how the rest of the pipeline were built.

## R2 — FR-014: the new `y(alpha)` primitive (executed proof, genuinely simpler circuit)

**Decision**: `y(alpha)` is measured by an ancilla-Hadamard-test wrapping a
**new**, smaller circuit built directly from `ir.gates` — reusing
`fourierlearn.reference`'s own plain forward-circuit construction pattern
(`_build_circuit`: `PauliTerm.to_gate()`/`FixedGate` applied directly, no
frequency register) and Circuits Layer's shared `_insert_observable`
helper (observable folded in via the same basis-change convention
`compile_observable_circuit` already uses) — **not** `compile_frequency_circuit`
/`compile_observable_circuit` themselves, which build Theorem 5.1's
frequency-register shift-encoding construction, a fundamentally different
circuit from "the plain parameterized circuit with the observable folded
in." This addresses planning mandate #2 directly: the new circuit must be
genuinely simpler (no frequency register or controlled-shift gates *at
all*), not merely reuse Spec 4's `V_l`-carrying circuit with an
identity-shift `V_l` (same qubit count, same gate types, just zero
repetitions — which would NOT be a simpler circuit, only a no-op parameter).

**Executed verification, on the mandated conjugate-symmetric fixture**:

```
=== Circuit simplification check (FR-014 vs Spec 4's V_l-based A(U,O)) ===
  compile_observable_circuit(ir, observable).num_qubits = 6
    registers: [('freq0', 4), ('ancilla', 1), ('circuit', 1)]
  FR-014 plain folded circuit.num_qubits                = 1
    registers: [('q', 1)]
  FR-014 circuit has 5 fewer qubit(s) -- no frequency register, no
  ancilla-controlled shift gates at all (genuinely simpler, not an
  identity-shift V_l)

  compile_observable_circuit instruction names: ['circuit-47', 'circuit-47_dg',
  ..., 'cx', 'h', 's', 'sdg', 't', 'tdg', 'z']
  FR-014 plain folded circuit instruction names: ['PauliEvolution', 'h', 's',
  'sdg', 't', 'tdg', 'z']
```

5 fewer qubits (no frequency register, no parity-fold ancilla at all — not
just an unused/no-op one), and zero `cx`/controlled-increment instructions
present in Spec 4's circuit but absent here — a structural, not merely
parametric, simplification.

**Exact cross-check** (Statevector, research-only — never used in
production): the Hadamard-test-ancilla-wrapped construction was compared
against a fully independent computation of `y(alpha)` (`reference.py`'s own
`_build_circuit` + `Statevector.expectation_value(observable).real`, no
ancilla trick at all) at 5 concrete `alpha` values:

```
alpha=0.3 : hadamard_test=-0.693630870421  direct=-0.693630870421  |err|=1.44e-15
alpha=0.0 : hadamard_test=+0.000000000000  direct=+0.000000000000  |err|=1.67e-16
alpha=1.0 : hadamard_test=+0.000000000000  direct=+0.000000000000  |err|=1.65e-16
alpha=-0.5: hadamard_test=+0.000000000000  direct=+0.000000000000  |err|=1.67e-16
alpha=2.2 : hadamard_test=-0.713973100677  direct=-0.713973100677  |err|=1.22e-15
MAX ERROR = 1.44e-15 (< 1e-10)
```

`y(alpha)` came out with an exactly-zero imaginary part at every tested
`alpha` (asserted in-script), confirming the ancilla construction's `P(0) -
P(1)` real-part read-out is the correct, sufficient measurement for this
Hermitian-observable expectation — no separate imaginary-part sub-circuit is
needed (unlike Spec 4's `estimate_coefficient`, which measures a genuinely
complex `b_l`).

**Constraint on `/speckit-tasks`**: FR-014's production implementation MUST
use `AerSimulator.run()` + `get_counts()` + `transpile()` (Constitution
Article II/§9.6), exactly like Spec 4's own primitive — the Statevector path
above is verification-only and must not appear outside test/research code.
This is this feature's **first** production measurement/circuit-execution
path (previously, this feature only called Spec 4's already-shipped
`estimate_coefficient()`; after the 2026-08-21 correction it no longer calls
that function at all, and instead owns its own execution path end to end).

## R3 — FR-015: the Fourier sensing matrix (derivation)

**Decision**: `A_{j,l} = exp(i*pi*l*alpha_j)` (single-parameter case),
generalized to `A_{j,l} = exp(i*pi*l . (c ⊙ alpha_j))` for multiple
parameters, where `c` is the per-parameter structural coefficient vector
Spec 1's IR already carries.

**Derivation** (from `fourierlearn.reference`'s own, already-shipped grid
convention — not a freshly invented formula): `_build_grid` samples
`alpha_m = domain_length * m / n_points` with `domain_length = 2/coefficient`
over `n_points` points, then `_fft_and_index` computes `b_l = (1/N) sum_m
f(alpha_m) exp(-2*pi*i*l*m/N)` (`numpy.fft.fftn`, normalized). Inverting
this (`f(alpha_m) = sum_l b_l exp(+2*pi*i*l*m/N)`) and substituting
`m/N = alpha_m / domain_length = alpha_m * coefficient / 2` gives:

```
f(alpha) = sum_l b_l * exp(i * pi * l * coefficient * alpha)
```

— exactly the sensing-matrix formula above, confirming it is the *same*
Fourier basis `reference.py`'s own oracle already reconstructs against, not
a new convention this feature invents independently (a second,
independently-derived convention would risk exactly the kind of silent
mismatch this project's own conventions discipline, Constitution §6.1,
exists to prevent).

**Real form actually used by the regression engine** (derived from
conjugate symmetry `b_{-l} = conj(b_l)`, folding the sum over `+l`/`-l`
pairs): for `l > 0`,

```
2 * Re(b_l * exp(i*pi*l*alpha)) = 2*cos(pi*l*alpha)*Re(b_l) - 2*sin(pi*l*alpha)*Im(b_l)
```

so `y(alpha) = Re(b_0) + sum_{l=1}^{L} [2*cos(pi*l*alpha)*Re(b_l) -
2*sin(pi*l*alpha)*Im(b_l)]` — a real linear combination of the *same*
real-stacked coefficient vector FR-006 already specifies (one `Re`/`Im`
column pair per canonical non-DC frequency, one `Re` column for DC). This is
why FR-006's already-designed stacking convention did not need to be
reinvented after the row-model correction — only what multiplies it (a
one-hot column, before; `2cos(pi l alpha)`/`-2sin(pi l alpha)`, now) changed.

## R4 — FR-006: end-to-end exact plumbing verification (executed proof, separate from R5)

Per planning mandate #1, this is a **deliberately separate** script from
R5's statistical check: an exactly-determined (`M >= P`, no shot noise, no
LASSO — ordinary least squares) linear system, isolating "is the stacking
and sensing-matrix plumbing correct" from "does compressed-sensing recovery
work under sub-sampling."

**Executed**, on the mandated fixture (`L=13` representable frequencies,
`P=13` real-stacked dimensions, `M=25` randomly chosen `alpha` values,
`y_j` computed exactly via R2's direct-expectation cross-check):

```
A condition number: 2.068e+02
rank(A) = 13 (expected 13)

  l=(0,): oracle=-0.3535533906+0.0000000000j  recon=-0.3535533906+0.0000000000j  |err|=2.00e-15
  l=(2,): oracle=+0.0883883476+0.0883883476j  recon=+0.0883883476+0.0883883476j  |err|=2.08e-15
  l=(4,): oracle=+0.1767766953+0.1767766953j  recon=+0.1767766953+0.1767766953j  |err|=8.69e-16
  l=(6,): oracle=-0.0883883476+0.0883883476j  recon=-0.0883883476+0.0883883476j  |err|=2.09e-16
  ... (all 13 representable frequencies, including the mirrored half)

MAX ERROR = 2.08e-15 (< 1e-8)
```

**Negative control** (proving the check is not vacuous): flipping the sign
convention of every `Im` column in the sensing matrix (`-sin` → `+sin`) was
confirmed **detected** — the reconstructed vector no longer matches the
oracle (`mismatch = True`).

**Constraint on `/speckit-tasks`**: this exact end-to-end round trip
(bind `alpha` → measure `y` → build `A` → solve → reconstruct → compare to
oracle) MUST be promoted to a permanent, named test, independent of the
statistical test R5 promotes.

## R5 — SC-001: statistical sparse-recovery verification (executed proof, separate from R4)

**Executed**, on a deliberately different, wider single-parameter fixture
(6 tied upload groups, `L=25` representable frequencies, only **2**
genuinely nonzero — `l=+12` and its mirror `l=-12`, a maximally sparse
case), `M=9` randomly chosen `alpha` values (`M << P=25`), exact
(noiseless) `y_j`, `sklearn.linear_model.LassoCV` on an explicit
`np.geomspace(1e-4, 1.0, 30)` penalty grid:

```
selected penalty (alpha_): 3.290e-03
  l=(12,) [ACTIVE]:  oracle=+0.500000+0.000000j  recovered=+0.498282-0.000000j  |err|=0.0017
  (all 12 other canonical frequencies, all inactive): recovered magnitude ~0.0000

max |error| on ACTIVE frequencies: 0.0017
max |recovered value| on INACTIVE frequencies: 0.0000
```

9 measurements recovered a 25-dimensional sparse vector to within `0.0017`
on its one genuinely active canonical frequency, with zero spurious weight
on any of the 12 inactive canonical frequencies — direct, executed
confirmation of SC-001's sparse-recovery claim, kept deliberately separate
from R4's exact-plumbing check (different fixture, different `M`/`P`
regime, LASSO instead of exact least-squares).

**Constraint on `/speckit-tasks`**: this sparse-recovery scenario (or an
equivalent one built at task time) MUST be promoted to User Story 1's
permanent acceptance test.

## R6 — FR-013: `tau` float-comparison tolerance (carried over, unaffected by the row-model pivot)

**Unaffected by the 2026-08-21 correction** — FR-013 (single Trotter
configuration per fit) concerns the encoding circuit's own feature map, not
how a training row's label is obtained, so the row-model fix does not touch
this decision. Repeated here for completeness (originally executed in the
prior planning pass; re-confirmed still executes cleanly):

**Decision**: `math.isclose(tau_a, tau_b, rel_tol=1e-9, abs_tol=1e-12)`
combined with exact `r_a == r_b` (int equality, no tolerance).
`encodings/trotter.py`'s `trotter_frontend(tau, r)` defines `tau` as the
**total evolution time**, `r` as the Trotter step count.

| Case | `tau_a` | `tau_b` | `same_tau()` | Meaning |
|---|---|---|---|---|
| A | `3.7` | `11.1/3.0` (not bit-identical) | `True` | same tau, different derivation |
| B | `3.7` | 12-fold re-accumulated sum | `True` | same tau, accumulated rounding |
| C | `3.7` | `3.9` | `False` | genuinely different tau — the real bug |
| D | `0.0` | `1e-13` / `1e-10` | `True` / `False` | near-zero boundary |
| E | `r=12` | `r=13` | `False` (`==`) | `r` uses exact int equality |

All cases executed and matched expected outcomes (script exit code 0).

## R7 — Regression solver (carried over, re-confirmed against the corrected model)

**Decision**: `sklearn.linear_model.LassoCV(alphas=<explicit pinned grid>,
cv=min(K_DEFAULT, M), fit_intercept=False, random_state=<seed>)` —
`fit_intercept=False` because the DC column is already an explicit real
column in the sensing matrix (R3), matching FR-003/FR-004's data-driven,
never-shot-noise-anchored grid requirement. Re-confirmed working directly
against the corrected sensing-matrix input in R5's executed script (not
merely asserted to still apply).

## R8 — PAC-style statistical bound (revised: `y_j` is now a single real value per row, not a complex `b_l`)

**Decision, revised**: since a training row now measures one **real**
scalar `y_j` (not a complex `b_l`), the per-row concentration bound is a
single Hoeffding-type bound (Spec 4's own `eps(N, delta) =
sqrt(2*ln(2/delta)/N)` formula, reused unchanged, `N` = shots for that
row), and the reported PAC-style bound unions over the `M` measured rows
(not `2M` real components, as the pre-correction research.md incorrectly
stated when a row was assumed to contribute a `Re`/`Im` pair):

```
eps_PAC(shots, M, delta) = sqrt(2 * ln(2 * M / delta) / shots)
```

This bounds, with probability `>= 1 - delta`, the maximum per-row error
`|y_hat_j - y_j|` across the `M` measured rows — translating this into a
bound on the *fitted coefficient vector*'s error additionally depends on
the sensing matrix's conditioning (R4 measured a condition number of
`2.068e+02` for one 25-sample draw; a tighter, sampling-scheme-specific
bound is a `/speckit-tasks`-level refinement, not required by this spec's
own FR-007, which only requires the two bounds be computed from disjoint
inputs and reported separately).

## R9 — Trotter structural-error bound (carried over, unaffected by the row-model pivot)

**Unaffected**: the first-order Lie-Trotter product-formula bound
`eps_Trotter(tau, r, {h_j}) = (tau^2/r) * sum_{j<k} |h_j||h_k| ||[H_j,H_k]||`
depends only on the feature map's own structure (`tau`, `r`, declared
Hamiltonian term weights) — never on how many training rows there are or
what they measure, so the row-model correction does not touch this
decision.

## R10 — Generalization-check flag (carried over, unaffected)

**Unaffected**: FR-009's `generalization_check_required` policy-only flag
concerns what the error-bounding report does when a fit looks
suspiciously good, independent of the row model.

## R11 — Optimisation discipline (Constitution §5.3, carried over, unaffected)

**Unaffected, re-confirmed**: no caching, warm-starting, or memoization is
introduced by this feature beyond `LassoCV`'s own already-existing internal
defaults. R5's executed script called `LassoCV.fit()` fresh, with no
caching of the sensing matrix or prior fits, consistent with this.

## R12 — Dependency addition (carried over, already applied)

**Unaffected, already applied**: `scikit-learn==1.8.0` pinned in
`pyproject.toml`'s `dependencies`, plus a `sklearn.*` mypy
`ignore_missing_imports` override — both already present from the prior
planning pass and confirmed still valid (R5's script imports and runs
`sklearn.linear_model.LassoCV` successfully against this environment).
