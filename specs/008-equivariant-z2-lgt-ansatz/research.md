# Phase 0 Research: Equivariant Z2 LGT Ansatz and Containment Verification

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

All computations below were executed in-session against the actual project
code (not hand-derived and merely asserted) and against the primary source
PDF (not recalled from memory), per Constitution §2.2/§2.5. The full script
is preserved at the end of this document's R2–R4 sections' own inline code
blocks; every printed number is a real, executed result.

## R1 — Mandate 1: is the target Hamiltonian's local parametrization a citation or a Constitution §2.3 EXTENSION? (executed)

**Question**: does the primary source (`docs/references/equivariant FCE
Z2LGT report.pdf`) use global scalar couplings `J, m, f` in eq. 1–4, or
local per-vertex/per-edge couplings?

**Verified verbatim (§2.3, p.5)**:

```
H = JHhop + mHm + fHg, (1)
with J, m, f in R the coupling constants (these are the physical quantities
one would want to learn).
```

**Finding, part 1 — the architect's factual premise is confirmed**: eq. 1–4
(§2.3, "The Hamiltonian, term by term") does use exactly three **global**
scalar coupling constants, not local ones.

**Finding, part 2 — but the SAME report's own §5.1–5.3 already specifies
local couplings, independently of eq. 1–4**. Verified verbatim (§5.1–5.3,
p.12–13):

```
Gamma_enc = {Z_v}_mass  U  {X_e}_electric  U  {h_e = (1/2)(A_e+B_e)}_hopping
                                                              (eq. 25)

Ws(x,alpha) = V_fix_s(x) * prod_v e^{i*pi*alpha^(m)_v*Z_v}
                          * prod_e e^{i*pi*alpha^(g)_e*X_e}
                          * prod_e [e^{i*pi*alpha^(h)_e*A_e} e^{i*pi*alpha^(h)_e*B_e}]
                                                              (eq. 26)

"We write r_j for the number of gates driven by parameter j in one layer...
r_j = 1 for mass and electric parameters, r_j = 2 for hopping parameters.
The parameter count is
    d = |V| + |E| + |E| = |V| + 2|E|.                        (eq. 27)"
```

This is the *exact* local-coupling, `d = |V| + 2|E|` parametrization
Spec 8's corrected FR-002 requires — `alpha^(m)_v`, `alpha^(g)_e`,
`alpha^(h)_e` are already per-vertex/per-edge encoded parameters in the
report's own circuit form, not the three global scalars from eq. 1. The
report's symbol table (p.5) independently confirms this: it defines
`l^(m)_v, l^(g)_e, l^(h)_e` as "components of l for the mass, electric and
hopping parameters" — a notation that is only meaningful if those
parameters are already indexed per vertex/edge.

**Resolution (per Constitution §2.2's own instruction not to conflate a
refinement with an error)**: eq. 1–4 (§2.3) is the report's **physical
motivation/narrative** statement of the Hamiltonian, in terms of the three
physical constants a physicist would ultimately want to learn or fit. Eq.
25–27 (§5.1–5.3) is the report's own, separate, **already-local**
specification of the actual Pauli-encoded ansatz circuit — the object
Barthe's FCE algorithm and this spec's Theorem 6.1 sparsity claim are
stated in terms of. **The local-coupling Hamiltonian in spec.md's FR-002
is therefore directly, verbatim citable to the SAME report's §5.1–5.3 (eq.
25–27), not a Constitution §2.3 EXTENSION beyond it** — it targets a
different, already-local part of the same source that mandate 1 did not
originally point to, rather than adding content the source lacks entirely.
This distinction is transparently flagged to the architect in the plan
completion report, matching this session's own established practice of
correcting a factual premise rather than silently complying with an
instruction whose stated justification does not hold under verification.

**Constraint on `/speckit-tasks`**: FR-002's implementation MUST cite
§5.1–5.3/eq. 25–27 as its source, not eq. 1 alone — and MUST NOT carry an
`EXTENSION` marker for the local-coupling structure itself (only for any
genuinely novel choice Spec 8 makes beyond what eq. 25–27 already
specifies, e.g. the concrete `build_z2_lgt_model` API shape).

## R2 — Mandate 2: executed containment verification (Ω ⊆ Λ ⊊ ambient)

**Fixture**: the smallest full matter+gauge instance — `|V|=2` matter
sites (`v0`=qubit 0, `v1`=qubit 1), `|E|=1` gauge link (`e01`=qubit 2),
`num_qubits=3`. `tau=1.0`, `r=1` Trotter step (`L=1` — the smallest
tractable choice; Proposition 5.1(iii) guarantees the hopping split is
exact even at `r=1`, so no generality is lost for this verification).

**Coupling groups** (reusing `encodings/trotter.CouplingGroup` unchanged):
`mass_v0` (weight `+1.0`), `mass_v1` (weight `-1.0`), `electric_e01`
(weight `1.0`), `hopping_e01` (two terms, `A_e`=`XZX`@(0,2,1) and
`B_e`=`YZY`@(0,2,1), both weight `0.5`, same group ⇒ tied).

**Executed — parameter structure** (`trotter_frontend` + `ir.parameters()`,
unmodified):

```
num_parameters = 4   (d = |V|+2|E| = 2+2 = 4, confirmed)
index=0 label='electric_e01'  upload_count=1 multiplicity=1
index=1 label='hopping_e01'   upload_count=1 multiplicity=2
index=2 label='mass_v0'       upload_count=1 multiplicity=1
index=3 label='mass_v1'       upload_count=1 multiplicity=1
```

Multiplicities `r_j = (1,1,1,2)` exactly reproduce the report's own §5.3
table (mass/electric `r_j=1`, hopping `r_j=2`) — `frequency.register_width`
and `frequency.pre_parity_range` (already sourced from this exact report,
per their own docstrings) require no modification for this feature.

**Honest finding, checked before proceeding (Constitution §4.3)**: the
default all-`|0...0>` initial state every `PauliEncodedCircuitIR` starts
from puts both matter qubits in the *diagonal* ("both empty") sector, which
`h_e=(1/2)(A_e+B_e)` **annihilates exactly** — verified via
`h_e^2 = (1/2)(I - Z_v Z_v')`, which is exactly `0` whenever `Z_v=Z_v'`.
This is a genuine, checked physical fact (hopping only acts when exactly
one particle is present to move), not a bug — but it makes the default
fixture degenerate for testing the hopping coordinate. Fixed by prepending
a non-parameterized `FixedGate(XGate(), qubits=(1,))` (flips `v1` to `|1>`
before any parameterized gate runs), placing the matter pair in the
off-diagonal ("exactly one particle") sector where hopping is genuinely
active. Verified numerically (`<Z_v0>` computed at several distinct
`(alpha_electric, alpha_hopping)` pairs with `alpha_mass` fixed) that
`<Z_v0>` is, in this specific fixture/observable pairing, exactly
independent of `alpha_electric` and `alpha_mass` — the mass gates act as a
pure global phase on any `|0>`/`|1>` product state (both are `Z`
eigenstates), and the electric parameter's effect on the gauge qubit does
not propagate into this particular single-site observable's expectation
value for this minimal instance. **Recorded honestly, not smoothed over**:
this means the extracted `Ω` below is non-trivial (two genuinely nonzero,
non-DC frequencies) but exercises only the hopping axis directly — the
Gauss-law/charge cross-coupling between mass and electric coordinates is
verified separately, against hand-derived controls (below), rather than
against this specific extracted `Ω`. A richer multi-edge instance would
exercise this jointly and is noted as follow-up scope, not a blocker.

**Executed — ambient box and Ω** (`reference.predict_grid_cost`,
`reference.coefficients`, unmodified, `budget` explicitly confirmed per
§11.5 before paying it):

```
predict_grid_cost (ambient box size) = 1125   (= 5*9*5*5, i.e. prod(4*r_j*L+1))
len(coeffs) = 1125  (every ambient point, confirmed)
|Omega| (eps=5.000e-10) = 2
Omega = {(0,-4,0,0): 0.5, (0,4,0,0): 0.5}   (axis order: electric, hopping, mass_v0, mass_v1)
```

**Executed — Λ (Theorem 6.1, eq. 36/37) and hand-verified controls**,
axis order `(electric, hopping, mass_v0, mass_v1)`:

- eq. 13 (generic evenness, no symmetry needed): every component even.
- eq. 36 (additive charge, **on raw `l`**): `l_v0^(m) + l_v1^(m) = 0`.
- eq. 37 (multiplicative Gauss, **on `l/2` mod 2**), per vertex:
  `l_v^(m)/2 + sum_{e touching v} l_e^(g)/2 ≡ 0 (mod 2)`.
- §7.1: the hopping coordinate `l_e^(h)` is **unconstrained** by either
  relation (`h_e` is not in the commuting family `F`, since it contains
  `Z_e`, which anticommutes with `X_e`).

**Verified this is the correct reading of the report's own `l`** (not
assumed): `frequency.register_width`/`pre_parity_range`'s own docstrings
already cite this report's §5.3 register-sizing table verbatim, and that
table's index ranges (`{-2L,...,2L}` for `r_j=1`, `{-4L,...,4L}` for
`r_j=2`) match this codebase's `pre_parity_range(r_j, L)` exactly — so the
report's `l` **is** this codebase's own pre-parity `l`, not an
independently-scaled quantity, confirmed by direct formula comparison
rather than assumed compatible.

Hand-derived positive/negative controls (worked out on paper before
running, then checked against the executed predicate — not fitted
afterward):

```
in_lambda(0,0,0,0)   = True   (all-zero: trivially satisfies both relations)
in_lambda(0,0,2,-2)  = False  (charge OK 2-2=0; Gauss v0 FAILS: 1+0=1 mod 2)
in_lambda(0,0,2,2)   = False  (charge FAILS: 2+2=4 != 0)
in_lambda(2,0,2,0)   = False  (charge FAILS: mass sum=2 != 0)
in_lambda(0,0,-2,2)  = False  (charge OK 0; Gauss v0 FAILS: -1+0=-1=1 mod 2)
in_lambda(1,0,0,0)   = False  (odd component: fails generic evenness)
in_lambda(2,0,-2,2)  = True   (charge OK -2+2=0; Gauss v0: -1+1=0; Gauss v1: 1+1=2=0)
```

All seven matched their hand-derived expectation exactly — the predicate
is discriminating (not vacuously true or false), on both the additive and
multiplicative mechanisms independently.

**Executed — full instance, the core containment claim**:

```
|ambient| = 1125
|Lambda|  = 25
reduction factor |ambient|/|Lambda| = 45.0
Omega elements NOT in Lambda: []   -> Omega subset-of Lambda: CONFIRMED
Lambda (25) is a strict, proper subset of ambient (1125): CONFIRMED
```

`Ω ⊆ Λ ⊊ ambient` holds, verified empirically on this instance (Constitution
§11.6) — not merely by re-stating the theorem. **Honest scope note on the
numeric factor**: the report's own asymptotic reduction `2^{-(d+|V|)}` (eq.
41) is stated in the `L -> infinity` limit and is explicit that the charge
factor is only a heuristic (Gaussian/CLT) approximation, exact only for the
parity and Gauss factors combined; at this instance's `L=1` the exact
per-coordinate parity ratios are `3/5` (`r_j=1` axes) and `5/9` (`r_j=2`
axis), not the asymptotic `1/2` — so the executed `45x` reduction for this
finite instance is **not** expected to numerically equal `2^{6}=64`, and is
reported as its own, independently computed, honest number for this
instance, not as a confirmation of the asymptotic formula.

## R3 — Mandate 3: executed parameter-tying proof

**(a) Tied — exact, no Trotter error (Proposition 5.1(iii))**. Built the
bare two-gate sequence (`A_e` then `B_e`, `PauliUpload` with
`coefficient=1.0` each, same `parameter_label` ⇒ tied), bound to a concrete
`alpha=0.37`, compared its `Operator` against a direct, single matrix
exponential of the combined generator (`scipy.linalg.expm`, no Trotter
splitting at all) — reproducing Prop 5.1(iii) verbatim in this project's
own `e^{i*pi*c*alpha*P}` convention (pinned-memory sign convention,
independently re-confirmed here via a single-qubit sanity check giving an
exact `0.0` diff before trusting the 3-qubit case):

```
max |op_tied - e^{i*pi*alpha*(Ae+Be)}| = 3.331e-16   (machine precision)
max |[A_e,B_e]| = 0.0   (Prop 5.1(i), exact)
```

**(b) Untied — genuinely breaks `[U,Q]=0`**. Built the same two gates under
two *independent* parameter labels (`"only_A"`, `"only_B"` — confirmed
`ir.num_parameters == 2`), bound to distinct concrete values
`alpha_A=0.3, alpha_B=0.9`, computed the commutator with
`Q = Z_v0 + Z_v1` (embedded on the full 3-qubit space):

```
alpha_A=0.3, alpha_B=0.9 (distinct): max |[U_untied, Q]| = 3.804226
alpha_A=alpha_B=0.37 (equal, sanity isolation): max |[U_untied, Q]| = 1.110e-15
```

The equal-angle sanity check is load-bearing: it confirms the failure above
is caused specifically by the two angles being *independent*, not by some
unrelated artifact of using two separate `PauliUpload`s — recovering exact
commutation (`~1e-15`) the instant the two parameters are forced equal.

## R4 — Mandate 4: executed symmetry-verification-hook proof

Gauss law generators for this instance (report eq. 5,
`G_v = Z_v * prod_{e touching v} X_e`), built via the project's existing
shared little-endian padding helper (`pauli_pqc._pad_to_full_width_little_endian`,
unmodified):

```
G_v0 = XIZ   (Z on v0, X on e01)
G_v1 = XZI   (Z on v1, X on e01)
```

Passed, together with the **full matter+gauge Hamiltonian's** flattened
term list (`mass_v0, mass_v1, electric_e01, A_e, B_e` — including the
hopping terms, a strictly stronger check than Spec 7's own original
fixture, which did not include a hopping-type term), through Spec 7's
`verify_symmetry`, completely unmodified:

```
internal=True non_annihilating=True abelian=True accepted=True
```

**Negative control** (discriminating, not vacuous): a deliberately
corrupted `G_v0` (missing its electric/`X_e01` factor entirely, i.e. just
`Z_v0` alone) is correctly rejected:

```
corrupted generator: accepted=False failure_reason='non-annihilating'
```

## R5 — Module architecture

**Decision — reuse Spec 7's enforcement unchanged**: `PhysicalModelDescription.__post_init__`
already runs `verify_symmetry` unconditionally whenever `symmetry.generators`
is non-empty (Spec 7 FR-010, Guardrail #2). Spec 8's ansatz construction
needs **no new enforcement hook** — it only needs to *always* attach a
non-empty Gauss law `SymmetryDeclaration` (never optional, unlike Spec 6's
TFIM, since Spec 8's whole point is Gauss-law equivariance by construction)
and let the existing `__post_init__` do the work, exactly as R4 executed it.

**Decision — new module `src/fourierlearn/z2lgt.py`** (not an addition to
`models.py`, to keep the existing TFIM-specific helpers untouched):
`Z2LGTEdge`, `Z2LGTGraph` (classical-input description, structural analogue
of Spec 6's `TFIMEdge`/`TFIMGraph`), `_gauss_law_generators(graph)` (a
mechanical, purely graph-structural derivation — one `G_v` per vertex, no
caller-supplied ambiguity, satisfying Constitution §11.9's "assert theorem
hypotheses in code"), and `build_z2_lgt_model(graph, mass_couplings,
electric_couplings, hopping_couplings) -> PhysicalModelDescription` —
builds the mass/electric/hopping `CouplingGroup`s (declared in that fixed
order: mass, then electric, then hopping — satisfying FR-005's gate-
contiguity requirement by construction, since `circuits.py` preserves IR
gate order exactly and never reorders), and always attaches the derived
Gauss law `SymmetryDeclaration`.

**Decision — a narrow, explicitly-justified CI-guard exception is required
for Ω-extraction (mandate 2/FR-010), mirroring Spec 6's precedent exactly**.
Constitution §11.6 *requires* verifying `Ω ⊆ Λ` "by brute-force support
extraction against the oracle" — this is not optional, and the oracle is
`reference.coefficients`, importable only from `reference.py` itself absent
an exception. Following Spec 6's isolation pattern (Guardrail: "the exact
oracle access must be completely isolated in its own single-function
module"), this feature adds a **second, single-function module**,
`src/fourierlearn/_containment_oracle_check.py`, whose sole function calls
`reference.coefficients` to extract `Ω` and returns it — never used for
training or feature construction, only for this one verification. `Λ`/
ambient computation themselves need no such exception (pure combinatorics
over the IR's own parameter structure) and live in the separate, unexempted
`src/fourierlearn/containment.py`.

**Required, backward-compatible CI-guard change**: `tests/ci/test_no_forbidden_imports.py`'s
`_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` constant must widen from a single
string to a tuple of names (adding `"_containment_oracle_check.py"`
alongside the existing `"_exact_dynamics.py"`), and `find_violations`'s
internal check must change from `path.name == narrow_exempt_module` to
`path.name in narrow_exempt_module`. The **existing three Spec 6 tests**
that construct a throwaway file at `tmp_path / _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY`
(passing the bare constant as a path segment) must be updated to index a
specific element (e.g. `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[0]`), since a
tuple can no longer be used directly as a path segment — this is a
required, explicitly-flagged consequence of the widening, not an
incidental breakage to discover later. `find_violations`'s own
`narrow_exempt_module` parameter keeps a safe default (the widened tuple),
so no external call site not already discussed here needs to change.

## R6 — Optimisation discipline (Constitution §5.3)

**Decision**: no caching, batching, or memoization anywhere in this design.
`compute_lambda` performs one pass over the ambient box (already
enumerated by `predict_grid_cost`'s own cost prediction) checking two small,
fixed-size linear/parity relations per point — no repeated-call pattern to
profile at this feature's own declared scope (small, hand-sized instances,
per spec.md's own Assumptions). The oracle-extraction module makes exactly
one call to `reference.coefficients` per verification, already the
minimal possible call count.
