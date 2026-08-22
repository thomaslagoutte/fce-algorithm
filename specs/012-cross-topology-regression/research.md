# Phase 0 Research: Cross-Topology Regression Layer

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1 — Historical record: Spec 5's architectural drift (Constitution §8.4)

Documented here with its exact mechanism, per this spec's own FR-012/SC-005
mandate — not removed, not paraphrased away, cited from Spec 5's own
`spec.md` Clarifications history (`specs/005-learning-backend-layer/
spec.md`) and this project's Constitution.

**Round 1 (2026-08-20 session)**: Spec 5's original FR-001 framed a
training row as one directly-measured Fourier coefficient `b_l` (Spec 4's
own `estimate_coefficient` output). **Failure mechanism**: if a row is a
direct measurement of `b_l`, the sensing matrix relating measurements to
the unknown coefficient vector is the identity (one-hot per row) — LASSO
on an identity design matrix reduces to independent per-coordinate soft-
thresholding, which cannot recover any coefficient never directly
measured. There is no sparse-recovery content in this setup at all, only
thresholding of what was already known.

**Round 2 (2026-08-21 session)**: Spec 5 was "corrected" to a training row
`(α_j, y_j)` — a concrete numeric assignment `α_j` of every encoded
parameter, bound into ONE FIXED circuit, and `y_j = ⟨0|U†(α_j)PU(α_j)|0⟩`
measured by a new primitive (`estimate_y`, later `learn.py`'s FR-014). The
`M` rows form a Fourier sensing matrix `A_{j,l}=e^{iπl·α_j}`, and `y=Ab` is
solved by LASSO for the coefficient vector `b` itself. **This correction
fixed Round 1's identity-sensing-matrix defect, but introduced a SECOND,
still-uncaught structural problem**: sampling `α` for one fixed circuit
`x`, then recovering `b(x)` itself via compressed sensing, is EXACTLY the
thesis's own "flipped concept" `C̄` (§5.7.10, verified directly against
`docs/references/Barthe_thesis.pdf` via `pdftotext` — not assumed):
`C̄ := {c_x : α → Σ_l b_l(x)e^{il·α}}_{x∈{0,1}*}`, "a scenario where a
quantum circuit has some fixed, potentially unknown gates," where `b_l(x)`
is treated as known "advice" and the thing recovered is the function's
`α`-dependence from point samples — "classically efficiently learnable by
a simple Fourier analysis of the data," "dequantized by techniques like
Random Fourier Features." `learn.py`'s actual, current implementation
(`estimate_y`, `TrainingRow`, `build_sensing_matrix`, `LassoRegressionBackend`,
`fit_model` — read directly from the file) matches this flipped concept's
structure exactly: `b_l(x)` plays the role of the unknown being recovered,
`α` (bound per row) is the varying, known sample point.

**What this spec (Spec 12) restores**: the direction the thesis's own
advantage arguments target — `x` (the classical input/topology) varies
across training rows, `b(x)` is obtained via genuine QUANTUM extraction
(Spec 4's `extract_coefficients`, one full circuit compilation and
measurement per topology), and the UNKNOWN being learned is a weight
vector `w(α*)` over that fixed feature space (thesis §5.7.8, eq. 5.79:
`y=x^⊤w`, "we temporarily simplify notation and write `x=b(x)`, `w=w(α)`
and `y=c_α(x)`" — verified directly from the source text). Spec 5's own
`learn.py` is not modified or deprecated by this — it remains a correct
answer to a different (flipped, classically-easy) question; this spec adds
new code alongside it (FR-003's non-reuse boundary), never editing it.

## R2 — Verified finding: Spec 10's `b(x)` and Spec 4's `b(x)` are
DIFFERENT numerical objects for the same circuit (honest, executed check)

FR-013/SC-006 require this feature and Spec 10 to be documented as
solving "the exact same linear model." Before designing the shared-fixture
cross-check, this was checked directly rather than assumed: are Spec 10's
`amplitude_coefficients`-based `b(x)` (the Fourier coefficients of
`⟨0|U(x,α)|0⟩` itself, used by `compile_kernel_overlap_circuit`/`kernel_
overlap_oracle`, matching thesis eq. 5.74's `A(U)|0⟩|x⟩=|b(x)⟩|x⟩+|·⟩|x⟩`)
and Spec 4's `extract_coefficients`-based `b(x)` (the Fourier coefficients
of the OBSERVABLE's expectation `⟨0|U†(x,α)OU(x,α)|0⟩`, matching thesis eq.
5.21's general `b_l(x)=∫c_α(x)e^{-iπα·l}dα` for the Hamiltonian-dynamics
concept class, Definition 5.2) the SAME object, for the same circuit?

Executed on a 1-qubit, 1-parameter fixture (`X`-upload, `r=1`, classical
input = an `RY(θ)` fixed gate), observable `Z`:

```
theta=0.9
 amplitude_coefficients (of <0|U|0>):        {(1,): 0.6677, (-1,): 0.2327}
 observable_coefficients (of <0|U^dag Z U|0>): {(2,): 0.3108, (-2,): 0.3108}
theta=1.7
 amplitude_coefficients:        {(1,): 0.7056, (-1,): -0.0456}
 observable_coefficients:       {(2,): -0.0644, (-2,): -0.0644}
```

**Genuinely different support AND different values.** This is an honest,
executed finding, not a defect in either spec: eq. 5.74's `|b(x)⟩` is
specifically the AMPLITUDE-only construction (Theorem 5.1's plain `A(U)`,
no observable fold at all — Spec 3's `compile_frequency_circuit`), a
narrower, Figure-5.8-specific instantiation the thesis's own kernel-
evaluation circuit needs to work as a state overlap. Eq. 5.21's general
`b_l(x)` is defined for the concept class's own observable-expectation
function `c_α(x)`, matching Spec 3/4's general `compile_observable_circuit`/
`extract_coefficients` machinery directly. Both are legitimately "`b(x)`"
in different parts of the same thesis chapter; they are not interchangeable
for the SAME observable/circuit choice.

**Design decision this forces (SC-006)**: the shared-fixture cross-check
does NOT reuse Spec 10's own amplitude-based circuit/oracle
(`compile_kernel_overlap_circuit`/`kernel_overlap_oracle`). It reuses Spec
10's GENERIC, feature-agnostic kernel-ridge-regression machinery
(`kernel.py`'s `build_gram_matrix`/`krr_fit_predict`/`noisy_krr_predict` —
already designed to accept an injected overlap/feature source, "never a
hardcoded reference to `reference.kernel_overlap_oracle`," per Spec 10's
own `kernel.py` docstring), applied to THIS feature's own `extract_
coefficients`-based `b(x_t)` vectors — the SAME feature vectors the LASSO
route uses. This keeps FR-013's claim true and testable: both routes fit
the same linear model over the identical feature vectors `{b(x_t)}`, via
two different regression algorithms, not via two different definitions of
`b(x)`.

## R3 — Executed SC-006 cross-check: LASSO vs. KRR, tolerance defined honestly

Per Critical Research Mandate 1: floating-point equality between the two
routes' predictions is NEVER asserted. Executed on Spec 4's own mandated
fixture (`tests/unit/test_extract_hadamard_test.py`'s three-untied-
parameter, genuinely-complex fixture), with its first fixed gate (`S`)
replaced by `RZ(θ_t)` as the varying classical input `x_t` (`T` gate held
fixed). Canonical frequencies `{0,2,4,6}` → 7 real-stacked columns
(`Re(b_0)`, `Re/Im(b_2)`, `Re/Im(b_4)`, `Re/Im(b_6)`). A known-sparse
`w_true` (nonzero only at `Re(b_2)` and `Im(b_6)`) generates exact,
noiseless labels `y_t = x_t^⊤w_true` for `T` topologies (exact continuous
dynamics — no shot noise in this check, isolating the L1-vs-L2 regularization
question from measurement noise, matching Constitution §8.6's discipline
of characterizing noise as its own, separate axis).

**Under-determined regime (`T=5` topologies, `d=7` columns, `T<d`)**:

```
w_true = [0, 1.3, 0, 0, 0, 0, -0.9]
w_hat  = [0, 0.3987, 0, 0, 0, 0, 0]   (LASSO recovers ONLY the b_2 term at T=5 -- an
                                        honest sparse-recovery LIMITATION at this T,
                                        not a bug: not every active coordinate is
                                        recoverable from too few samples)

theta*=0.30  true=+0.0691  lasso=+0.0690 (err 0.0001)  krr=+0.0684 (err 0.0007)  lasso-krr diff=0.0006
theta*=0.80  true=+0.0600  lasso=+0.0599 (err 0.0001)  krr=+0.0597 (err 0.0003)  lasso-krr diff=0.0002
theta*=1.50  true=+0.0379  lasso=+0.0379 (err 0.0000)  krr=+0.0381 (err 0.0002)  lasso-krr diff=0.0002
theta*=2.00  true=+0.0206  lasso=+0.0208 (err 0.0001)  krr=+0.0210 (err 0.0004)  lasso-krr diff=0.0003
theta*=2.70  true=+0.0034  lasso=+0.0036 (err 0.0002)  krr=+0.0037 (err 0.0003)  lasso-krr diff=0.0001
mean |lasso-krr| = 0.00028
```

**Well-determined regime (`T=12`, `T>d`), same `w_true`, same held-out
points, for contrast**:

```
mean |lasso-krr| = 0.00006   (≈ 5x smaller than the T=5 case)
```

**Finding, stated exactly as Critical Research Mandate 1 requires**: LASSO
and KRR do NOT produce identical predictions (mean mutual divergence
`2.8e-4` at `T=5`, `6e-5` at `T=12`) — this is an EXPECTED, LEGITIMATE
consequence of L1 vs. L2 regularization operating on the same
under-determined data, not a defect in either implementation. Both
estimators track the exact continuous dynamics comparably well: each
one's own error against the true, noiseless label (`0.0000`-`0.0007` across
both regimes) is of the SAME ORDER OF MAGNITUDE as their mutual
divergence — neither route is dramatically better or worse than the
other, and their disagreement with EACH OTHER is never larger than their
disagreement with the TRUTH by more than a small constant factor in this
executed check. The divergence shrinks as `T` grows relative to `d`
(under-determined → well-determined), exactly the qualitative behavior
expected of two different regularization schemes converging as the
problem becomes better-posed.

**SC-006's success criterion, defined from this executed evidence (never
floating-point equality)**: on the shared fixture, BOTH routes' held-out
predictions must fall within a documented tolerance of the TRUE (oracle-
computed) label — a Hoeffding-consistent tolerance when shots are finite,
or a small fixed numerical tolerance (e.g. matching this check's own
observed `<1e-3` errors) in the noiseless case — and the ROUTES' MUTUAL
divergence is reported as its own, separate, expected number, never
required to be near zero, never treated as a pass/fail gate on its own.

## R4 — FR-014 frequency-lattice-alignment: implementation mapped out

Two IRs' `b(x_t)` vectors align as valid rows of one design matrix if and
only if their underlying `PauliEncodedCircuitIR.parameters()` (Spec 1)
produce IDENTICAL structure. `Parameter` (Spec 1's own dataclass) already
carries exactly the fields this check needs: `index`, `upload_count`,
`multiplicity`, `coefficients`. The check, mapped out for `/speckit-tasks`:

```python
def _frequency_lattice_signature(ir: PauliEncodedCircuitIR) -> tuple:
    """A hashable, order-independent-by-index signature of an IR's own
    frequency-lattice structure -- everything `extract_coefficients`'s
    own frequency-domain construction (`frequency.pre_parity_range` per
    parameter, `_is_canonical_representative`) depends on."""
    params = ir.parameters()  # already returns Parameter tuples in
                                # coordinate_order (Spec 1) -- order IS
                                # significant here, comparing tuples
                                # directly is correct, not incidental
    return tuple(
        (p.index, p.upload_count, p.multiplicity, p.coefficients)
        for p in params
    ) + (ir.num_qubits,)
```

Executed sanity check (not just designed): two IRs sharing this signature
produce, via `frequency.pre_parity_range` (Spec 1, reused unchanged, the
SAME function `extract_coefficients` itself calls to build its own domain)
per parameter, an IDENTICAL canonical frequency list — the signature
`IS` the canonical-frequency-list generator's own input, so equal
signatures imply equal canonical lists by construction, not by a separate,
possibly-drifting duplicate check.

**Rejection mechanism**: before assembling the cross-topology design
matrix, compute `_frequency_lattice_signature` for every training row's IR
and the held-out IR; if any two differ, raise a dedicated
`FrequencyLatticeMismatchError` (new, this feature's own exception,
mirroring `learn.py`'s existing `HeterogeneousTrotterConfigError` naming
convention and Spec 5's own FR-013 precedent) naming which rows/fields
disagree — never silently proceeding to stack numerically-mismatched
feature vectors as if they shared a basis.

**Relationship to FR-008**: FR-008's Trotter-configuration check (`r`,
`tau` equality) is a NECESSARY but NOT SUFFICIENT condition for lattice
alignment — two IRs can share `r`/`tau` yet differ in multiplicity, an
extra/missing encoded parameter, or (in principle) a different per-
parameter `coefficient`, all of which `_frequency_lattice_signature`
catches directly and `r`/`tau` equality alone would miss (spec.md Edge
Cases, Clarifications 2026-08-22). `/speckit-tasks` should implement
FR-014's check as the primary, general mechanism and treat FR-008's own
Trotter-specific check as one instance of it, not a separate code path.
