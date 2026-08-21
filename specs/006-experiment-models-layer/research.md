# Phase 0 Research: Experiment and Models Layer

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1 — Refutation guard: executed negative control against the exact oracle (mandate #1)

**Claim to verify**: the generalization check must correctly return
`refuted` for a genuine overfitting artifact — a model that looks
suspiciously good (closer than its own Trotter bound) at its training
points but does not actually capture the true dynamics — and must
correctly return `generalizes` for a model that genuinely does track exact
dynamics. Both must be shown by execution, not asserted.

**Construction** (not hand-injected fake numbers — a naturally-arising
overfitting mechanism): on a small two-coupling-group fixture (`X` and `Z`
terms, `tau=0.5`, `r=1`, Trotter bound `= 5.00e-01`, `L=25` representable
frequencies, `P=25` real-stacked dimensions), fit an **under-determined,
unregularized** ordinary-least-squares model on `M=22 < P=25` training
points. The minimum-norm solution alone already interpolates training
points near-exactly but stays numerically mild; to model a genuine
"spurious explanation" artifact, a component along the training sensing
matrix's own **null space** (obtained via SVD) is added at an amplitude
comparable to the true signal (`3x` the minimum-norm solution's own norm).
Because this null-space vector satisfies `A_train @ v = 0` by construction,
the training equations still hold exactly — the artifact model still looks
perfect on its own training data — but its prediction at any other point
is displaced by the null vector's own (nonzero, generically large) basis
value there.

**Executed output**:

```
=== Fixture: L_total=25 representable frequencies, P=25 real-stacked dims ===
Trotter bound (structural_approximation_bound) = 5.000000e-01

=== Step 1: overfit model fit on M=22 < P=25 training points (OLS, no regularization) ===
max |predicted - exact| AT TRAINING POINTS = 2.331e-15
Trotter bound                                = 5.000e-01
--> at training points, this model IS suspiciously good (closer than the Trotter
bound) -- exactly the condition that would set generalization_check_required=True
in Spec 5's error_bounding_report.

=== Step 2: generalization check at a genuinely new, shifted point ===
shifted_alpha = (3.8384694192003885, 5.853196490992537)
predicted     = +3.307625
exact (oracle)= -0.766850
|gap|         = 4.074476e+00
trotter_bound = 5.000000e-01
VERDICT       = 'refuted'

=== REFUTATION GUARD VERIFIED: the overfit artifact correctly returns 'refuted' at a
genuinely unseen point, despite looking suspiciously good at its own training points ===

=== Positive control: a model using the TRUE oracle coefficients directly ===
|gap| = 1.110e-16  VERDICT = 'generalizes'
=== POSITIVE CONTROL VERIFIED: the true (non-artifact) model correctly 'generalizes' ===
```

Both the negative control (`refuted`, gap `4.07` vs. bound `0.5`) and the
positive control (`generalizes`, gap `1.1e-16`) executed and matched their
expected outcome — the check discriminates a real artifact from a genuine
capability, not merely a formula that looks plausible.

**Constraint on `/speckit-tasks`**: this exact scenario (the null-space
injection construction, on this exact fixture) MUST be promoted to a
permanent, named regression test for the generalization-check mechanism —
this is the single most important correctness property this feature has,
since a check that could be fooled by *any* overfitting artifact would
defeat Constitution §8.2's entire purpose.

## R2 — Threshold determinism: executed boundary cases (mandate #3)

**Decision**: `verdict = "generalizes" if abs(predicted - exact) <= trotter_bound else "refuted"`
— inclusive (`<=`), absolute, with no noise-based hedging near the
boundary, because both `predicted` (a fitted model's deterministic
prediction) and `exact` (a deterministic oracle value, R1/R3) carry no
randomness at evaluation time. This also resolves spec.md's own
previously-open "boundary tie" edge case: an exact tie is decided in favor
of `generalizes` by the `<=`, not treated as a separate ambiguous outcome.

**Executed** (same fixture as R1, `trotter_bound = 0.5`):

```
gap = 99.9% of trotter_bound (4.995000e-01 vs 5.000000e-01) -> verdict = 'generalizes'
gap = exactly 100% (boundary tie) of trotter_bound (5.000000e-01 vs 5.000000e-01) -> verdict = 'generalizes'
gap = 100.1% of trotter_bound (5.005000e-01 vs 5.000000e-01) -> verdict = 'refuted'
```

All three matched their expected, definitive outcome — no "inconclusive"
or hedged result anywhere near the boundary, confirmed by execution at
exactly the boundary itself (not only comfortably on either side of it).

## R3 — CI Guard Exception: exact code change, executed against synthetic modules (mandate #2)

**Decision**: extend `tests/ci/test_no_forbidden_imports.py` with one new
module-level constant and a three-line change to `find_violations`, rather
than a broader whitelist mechanism — the narrowest change that grants the
one named module (`_exact_dynamics.py`, R4) an exemption from the
`reference` forbidden-name only, never from `Statevector`/`Operator`/
`expm`.

**Exact code change**:

```python
# Constitution Clarifications (Spec 6, 2026-08-21): the generalization-check
# mechanism must compare a fitted model's prediction against genuinely EXACT
# ground-truth dynamics -- never a finite-shot measurement or a finer-Trotter
# approximation, because neither can distinguish a real capability from an
# artifact of interpolating imperfect training labels (Constitution §8.2's
# entire point -- verified computationally, research.md R1). This is the ONE
# other module in the project narrowly authorized to import
# `fourierlearn.reference`, and ONLY for that purpose: it is NOT exempted
# from the Statevector/Operator/expm prohibition, since it has no legitimate
# reason to import those directly -- it only calls reference.py's own
# already-exempted function.
_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY = "_exact_dynamics.py"


def find_violations(src_root: Path, exempt_module: str = _EXEMPT_MODULE) -> dict[str, set[str]]:
    violations: dict[str, set[str]] = {}
    for path in sorted(src_root.rglob("*.py")):
        if path.name == exempt_module:
            continue
        found = _scan_module(path)
        if path.name == _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY:
            found = found - {"reference"}
        if found:
            violations[str(path.relative_to(src_root))] = found
    return violations
```

`_scan_module` itself is unchanged — the exemption is applied only in
`find_violations`'s own aggregation step, keeping the scanner itself
blind to any exemption (defense in depth: the scanner still *sees* the
`reference` import, `find_violations` is the only place that chooses to
ignore it, for exactly one file).

**Executed proof**, against a synthetic temp tree (never the real `src/`
tree, so this proves the *logic*, not a lucky current state):

```
=== Violations found ===
  _exact_dynamics_but_also_statevector.py: {'Statevector', 'reference'}
  some_other_experiment_module.py: {'reference'}

=== CI GUARD PROTOTYPE VERIFIED ===
- _exact_dynamics.py: exempted for `reference` only -- PASS (no violation)
- some_other_experiment_module.py: still rejected for `reference` -- PASS
- clean_module.py: no violation -- PASS

=== Second check: the exempt module ITSELF also importing Statevector ===
  _exact_dynamics.py: {'Statevector'}
PASS: exempt module is still flagged for Statevector; only `reference` is waived
```

Three properties confirmed by execution: (1) the named module is exempted
for `reference` only; (2) a *different* module importing `reference` is
still rejected — the exemption does not widen; (3) the named module itself
is still rejected if it imports `Statevector`/`Operator`/`expm` directly —
the exemption is not a blanket pass for that one file.

**Constraint on `/speckit-tasks`**: apply this exact diff to
`tests/ci/test_no_forbidden_imports.py`, and add the two new test functions
this research exercised (`some_other_experiment_module` rejection;
exempt-module-still-flagged-for-Statevector) as permanent, named tests —
not merely leave this prototype in research.md.

## R4 — Module architecture: isolating the oracle-access surface

**Decision**: the narrow oracle-access exemption (FR-011) is granted to
exactly one, minimal module: `src/fourierlearn/_exact_dynamics.py`,
containing only:

```python
def exact_dynamics(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, alpha: tuple[float, ...]) -> float:
    """The ONLY function in this project (outside reference.py itself)
    permitted to call fourierlearn.reference. Used exclusively by the
    generalization check (experiment.py) to obtain a genuinely exact
    comparison target -- never for training or feature construction."""
```

All other generalization-check logic — selecting the shifted input,
calling `predict()`, computing the verdict via R2's threshold rule,
constructing the immutable result object, and asserting
`ErrorBoundingReport`/`PacBound.weight_space_translation_status` are
untouched (FR-003/FR-004) — lives in a separate `experiment.py` module that
does **not** import `fourierlearn.reference` itself, only
`_exact_dynamics.exact_dynamics`. This keeps the whitelisted surface at
exactly one function in exactly one file, rather than exempting a larger
module that also contains unrelated logic.

**Rationale**: minimizing the exempted surface area directly serves the
"narrow, explicitly justified" framing the Clarifications session
mandated — a reviewer auditing this exception only ever needs to read one
small file, not trace which of several responsibilities in a larger module
actually needed the oracle.

## R5 — TFIM model construction (User Story 2)

**Decision**: the model-construction API groups Pauli terms by an explicit,
caller-supplied group label per declared coupling — defaulting to *one*
shared label across all graph edges (the common, uniform-coupling TFIM:
`H = -J * sum_{(i,j) in E} Z_i Z_j - h * sum_i X_i`, exactly two
`CouplingGroup`s: one `ZZ`-term group spanning every edge, sharing the
single learned coupling `J`; one `X`-term group spanning every site,
sharing the single learned field `h`) — while still permitting a caller to
assign distinct labels per edge or per site for a heterogeneous
(random-bond) TFIM variant, which produces one `CouplingGroup` per distinct
label instead. This resolves an ambiguity between spec.md's FR-005
("edges each carrying one coupling strength") and Acceptance Scenario 1
("the graph's edges sharing one coupling constant") — both are correct,
for different caller choices; the default is the uniform case, but nothing
in the API forces it.

**Rationale**: `CouplingGroup`'s own constraint (all terms in one group
share the exact same weight, enforced by `encodings/trotter.py`'s own
`_validate_inputs`) already draws the line correctly — grouping is exactly
"which terms share one physical, to-be-learned constant," so exposing an
explicit group label is the natural API shape, not a new convention this
feature invents.

**Alternatives considered**: always forcing one shared coupling for all
edges (rejected — silently forecloses the heterogeneous-TFIM case FR-005's
own wording already allows for); one `CouplingGroup` per individual edge
unconditionally (rejected — makes the common uniform case the awkward one,
and produces the same result as explicit per-edge labeling, so it adds no
capability, only a worse default).

## R6 — Constitution §11 attach points (User Story 3)

**Decision**: two additive, always-optional fields, populated by nothing in
this spec:

- A `symmetry: SymmetryDeclaration | None = None` field on the
  model-construction result (User Story 2's output) — inert data a future
  spec's §11.1 equivariance check would read and evaluate.
- A `containment_record: ContainmentRecord | None = None` and
  `sparsity_mechanism: str | None = None` field on the generalization-check
  result / experiment report (User Story 1's output) — inert, always
  `None` in every code path this spec implements, reserved for a future
  spec's §11.6/§11.7 output.

**Rationale**: both are pure data additions with no behavior attached —
satisfying User Story 3's own Acceptance Scenario 1 ("behaves exactly as
before" when absent) trivially, since nothing reads or branches on them.

## R7 — Optimisation discipline (Constitution §5.3)

**Decision**: no caching, batching, or memoization anywhere in this
feature's design. The generalization check computes one exact oracle value
per invocation (R1/R4) and performs one `predict()` call — both already
`O(1)` in the number of representable frequencies for a single evaluation,
with no repeated-call pattern in this spec's own scope that a profile could
target. The TFIM model-construction capability (R5) runs once per model
description, not in a hot loop. Nothing here was optimized absent a
recorded profile and a bottleneck it targets.
