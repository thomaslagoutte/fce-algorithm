# Phase 0 Research: LCU and Projector-Observable Extension

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1 — Mandate 1: negative-weight LCU fixture (executed)

**Question**: does the corrected FR-003 formula (`c_h = √(β_h/S)`,
Clarifications 2026-08-21) actually work when a weight `β_h` is negative,
and how is the sign absorbed into the construction without producing an
invalid imaginary amplitude?

**Executed, Step 1 — the naive failure mode, made concrete**: with
`β_1=1, β_2=-4` (`S = Σ|β_h| = 5`):

```
beta2/S = -0.8
naive c2 = sqrt(beta2/S) = (5.5e-17+0.894j)   <-- IMAGINARY
```

Confirms explicitly: `c_h = √(β_h/S)` (using the *signed* `β_h` directly
inside the square root) is not just numerically wrong but structurally
inapplicable whenever `β_h<0` — it cannot be built with a real rotation
gate at all, since a Ry-type state-prep circuit only ever produces real,
non-negative-under-the-radical amplitudes from a real angle.

**Executed, Step 2 — the corrected, signed construction**. Uses
`c_h = √(|β_h|/S)` (absolute value under the radical — always real and
well-defined) for the *magnitude* of the preparation amplitude, and
absorbs `sign(β_h)` into the construction via one additional diagonal
gate on the selector register — concretely, for a 2-term case with the
negative weight on the `|1⟩` branch, a single `Z` gate on the selector
qubit (since `Z|0⟩=+|0⟩, Z|1⟩=-|1⟩`), applied once, anywhere between
`PREP` and `PREP†` (it commutes with the selector-controlled multiplexed
gate, since both are diagonal/block-diagonal in the same selector basis).
Built as an explicit 2-qubit circuit (`P_1=Z`, `P_2=X`, selector qubit
controlling which is applied):

```
c1 = sqrt(|beta1|/S) = 0.4472135954999579
c2 = sqrt(|beta2|/S) = 0.8944271909999159

post-selected (selector=0) amplitudes: [-0.13952868+0j, -0.81273104+0j]
target (1/S)(beta1*Z + beta2*X)|psi>:  [-0.13952868+0j, -0.81273104+0j]
max |post_selected - target| = 1.110e-16
```

**Exact match, to machine precision**, including the negative weight.

**Executed sanity control** (isolating that the sign gate specifically is
responsible, not some other artifact): removing only the `Z` sign gate
from the same circuit reproduces the *all-positive-weight* combination
`(1/S)(|β_1|Z+|β_2|X)|ψ⟩` exactly (diff `2.2e-16`), which differs from the
correct, signed target by `1.46` — a large, unambiguous difference. The
sign gate is load-bearing, not decorative.

**Executed, Step 3 — re-confirming the asymmetric-weight mandate
(Clarifications 2026-08-21) on this same fixture**, using the *literal*
transcription of eq. 5.51 (`c_h = β_h/‖β‖` with `‖β‖` the L2/Euclidean
norm — the only norm for which that ratio is already a normalized qubit
amplitude pair, hence directly Ry-buildable) as the concrete "wrong"
hypothesis to compare against:

```
asymmetric (beta1=1, beta2=4):
  correct construction matches (1/S)(Z+4X)|psi>, S=L1 norm: diff=2.22e-16
  wrong (c_h=beta_h/||beta||_2) matches a (1/17, 16/17)-weighted combo: diff=0.0
  correct vs. wrong differ by 1.86e-01 -- easily caught by any exact-value check

equal weights (beta1=beta2=2):
  correct term-to-term ratio: 0.3883212946666845
  wrong  term-to-term ratio:  0.3883212946666845   <-- IDENTICAL
  overall scale: |correct|=0.7071, |wrong|=0.7071  <-- ALSO IDENTICAL
```

**Confirms the mandate's own reasoning exactly**: with equal weights, the
correct and incorrect formulas are literally indistinguishable on this
fixture (identical ratio *and* identical scale) — not merely "hard to
tell apart," but mathematically identical outputs. Only an
asymmetric-weight fixture can catch the bug, exactly as Clarifications
2026-08-21 requires.

**Constraint on `/speckit-tasks`**: the implementation's verification test
MUST use the asymmetric, signed fixture (`β_1=1, β_2=-4` or equivalent)
reproduced above, not a simplified or equal-weight substitute, and MUST
include the negative-weight case specifically — a same-sign-only
asymmetric fixture (e.g. `β_1=1, β_2=4`, both positive) would catch the
square-root bug but not a sign-absorption bug.

## R2 — Mandate 2: concrete qubit-cost formula for `U⊗U*` (derived and verified)

**Question**: what is the exact, integer qubit-count formula for the
`U⊗U*` projector construction (deliverable b), not merely "it doubles"?

**Grounding in the existing, unmodified implementation**: Spec 3's
`circuits._build_registers` already defines the single-copy register
budget for one `A(U)` construction as:

- One frequency register per encoded parameter `j` (`j=1..d`), each of
  width `register_width(L_j, r_j) = ⌈log2(4·r_j·L_j+1)⌉` qubits (Spec 1's
  `frequency.register_width`, unmodified) — reflecting the pre-existing
  formula this codebase already uses for every single-observable
  extraction.
- One shared ancilla qubit (Spec 3's `FR-003`/research.md R4).
- The original circuit register, `n_circuit` qubits.

So a single `A(U)` copy's own qubit budget is:

```
n_single(U) = n_circuit + sum_{j=1}^{d} ceil(log2(4*r_j*L_j + 1)) + 1
```

**The `U⊗U*` construction (eq. 5.52) requires an independent, complete
second copy of every one of these registers** — its own `n_circuit`-qubit
circuit register (for `U*`'s own action, since eq. 5.52's `⟨k|⊗⟨l|`
structure ranges over the full computational basis on *two separate*
copies of the state space), its own set of `d` frequency registers (one
`A(U*)` construction, with the identical `L_j, r_j` structure as `A(U)`,
since `U*` shares the same encoding-gate structure as `U`, differing only
in gate-level sign/phase, never in parameter count or upload structure),
and its own ancilla qubit. Hence:

```
n_total(U tensor U*) = 2 * n_single(U)
                      = 2*n_circuit + 2*sum_{j=1}^{d} ceil(log2(4*r_j*L_j+1)) + 2
```

**Executed, concrete worked example** (`n_circuit=2`, `d=2` parameters,
each `L_j=3, r_j=1`):

```
freq_widths per parameter = [4, 4]   (register_width(3,1) = ceil(log2(13)) = 4)
n_single(U)               = 2 + 4 + 4 + 1 = 11
n_total(U tensor U*)      = 2 * 11 = 22
```

**Separately, the existing extraction layer's own Hadamard-test readout
ancilla (Spec 4's `_hadamard_test_circuit`, unmodified) adds exactly one
further qubit** — not doubled, since only one overall coefficient-readout
ancilla is needed regardless of how many internal copies of `A(U)` the
compiled circuit contains:

```
n_total_including_readout = n_total(U tensor U*) + 1 = 23   (for the worked example above)
```

**Honest scope note (Constitution §10.3, Guardrail: predict and log
before paying)**: this doubling is an unavoidable structural cost of the
`U⊗U*` construction itself (not an implementation inefficiency to be
optimised away, Constitution §5.3) — it must be predicted and logged
before a projector extraction is run, exactly as `reference.py`'s
existing `predict_grid_cost` already does for grid-evaluation cost.

**Contrast with deliverable (a)'s own, additive (not multiplicative)
overhead**: the LCU selector register adds `⌈log2(#terms)⌉` qubits on top
of a *single* `n_single(U)` — never doubling anything. Stating this
contrast explicitly (rather than letting "doubling" bleed across both
deliverables) is itself part of the honest-scope requirement: the two
deliverables have genuinely different, differently-shaped costs.

**Constraint on `/speckit-tasks`**: the projector construction's
implementation MUST expose a cost-prediction function (mirroring
`reference.predict_grid_cost`'s existing pattern) that computes
`n_total(U tensor U*)` from the IR's own parameter structure before any
circuit is compiled, and this predicted count MUST be logged.

## R3 — Module architecture

**Decision — extend, do not duplicate, `compile_observable_circuit`**:
`circuits.py`'s existing `_insert_observable`/`compile_observable_circuit`
remain the single entry point. A new internal branch inspects whether the
supplied `SparsePauliOp` has one term (existing, unmodified code path —
`_insert_observable` unchanged) or more than one (new LCU path: prepare
the selector register per R1's verified construction, apply the
multiplexed, sign-corrected controlled-`P_h` gate at the exact position
the single `_insert_observable` call occupies today, un-prepare). No
parallel `compile_observable_circuit`-equivalent function is introduced
(Critical Mandate 1).

**Decision — the projector construction is a separate entry point**,
since it does not fold any observable at all (it operates on `U` and `U*`
directly, per Clarifications). It reuses `compile_frequency_circuit`
(Spec 3, unmodified) twice — once for `U`, once for a new,
independently-constructed `U*` IR — never reusing or duplicating
`compile_observable_circuit`'s own observable-folding logic, since there
is no observable to fold.

**Deferred, explicitly, not resolved in this plan**: exactly how `U*` is
constructed from this codebase's own `PauliEncodedCircuitIR` for a Pauli
term with an *odd* number of `Y` factors (spec.md's own Assumptions
already flag this as an open question for a real Hermitian generator vs.
a purely imaginary one) is not addressed by this plan's own critical
mandates (negative-weight LCU fixture; qubit-cost formula) and is left as
a named, explicit task for `/speckit-tasks` to schedule its own dedicated
computational verification — not silently assumed solved by this
research round.

## R4 — Optimisation discipline (Constitution §5.3)

**Decision**: no caching, batching, or memoization anywhere in this
design. The LCU selector-register construction and the doubled `U⊗U*`
registers are structural costs of the algorithms themselves (R1/R2), not
targets for optimisation — Constitution §5.3 requires a recorded profile
identifying a bottleneck before any optimisation, and none is proposed
here.
