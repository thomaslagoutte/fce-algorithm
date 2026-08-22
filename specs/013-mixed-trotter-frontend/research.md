# Phase 0 Research: Mixed Fixed/Encoded Trotter Frontend

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1 — Sign Transcription Audit (FR-011): the spec's stated formula is CORRECT, independently reverified

**Mandate**: the user flagged a specific, concrete hypothesis before this
research phase began — FR-011 states `θ = w·τ·v/r` for the fixed term's
gate `e^{-iθP}`, while the coefficient feeding `PauliTerm.to_gate` is
`c = -w·τ/(π·r)`; if `to_gate` multiplies by `π` internally, the resulting
angle could come out with the opposite sign from what FR-011's prose
transcribes. This was NOT waved away by re-reading the earlier session's
own (already-passing) `Operator.equiv` checks — those checks used
Qiskit's native `RZGate`/`RXGate`/`RZZGate` as the independent comparison
target, and a *second*, independent bug was later found and fixed inside
that comparison code itself (spec.md Clarifications, "Negative result").
The mandate here is stronger: re-derive and re-check the sign from
first principles, using a THIRD, even more independent method — direct
`scipy.linalg.expm` of the raw 2×2 Pauli matrix, bypassing `Qiskit`'s own
gate library (`RZGate`/`RXGate`/`RZZGate`) entirely, not just
`PauliTerm.to_gate` — before accepting FR-011's prose as correct.

**Executed check.** For `PauliTerm(pauli, qubits, parameter_index=-1,
coefficient=c, tie_group=0).to_gate(v)`, with `c = -w·τ/(π·r)`, compare
`Operator(gate).data` against BOTH candidate signs of
`scipy.linalg.expm(±iθP)`, `θ = w·τ·v/r`, on two independent, unrelated
`(w, τ, r, v, P)` tuples:

```
Fixture 1: w=0.8, tau=1.09, r=3, v=1.5, P=Z, theta=0.436
  diff vs e^{-i*theta*Z}  (FR-011's stated sign): 5.551115123125783e-17
  diff vs e^{+i*theta*Z}  (flipped-sign alternative): 0.8446341211052386

Fixture 2: w=1.37, tau=0.62, r=5, v=-0.9, P=X
  diff vs e^{-i*theta*X}: 2.220446049250313e-16
```

**Finding: FR-011's prose is CORRECT as written, confirmed to machine
precision on two independent fixtures, and the flipped-sign alternative
is decisively ruled out** (`diff=0.84`, not a rounding-level discrepancy).
`PauliTerm.to_gate`'s internal `π` multiplication does not flip the sign
relative to FR-011's transcription: `to_gate(v)` implements
`e^{iπcαP}` (this project's own established convention, pinned memory),
so with `α=v` and `c=-w·τ/(π·r)`:

```
exponent = iπ·c·v·P = iπ·(-w·τ/(π·r))·v·P = -i·(w·τ·v/r)·P
```

— the two `π` factors (one from the convention's own `iπc`, one in the
denominator of `c`) cancel exactly, leaving `θ = w·τ·v/r` with a `-i`
prefactor, exactly as FR-011 states. **This is a genuinely resolved
concern, not a dismissed one**: the hypothesis was concrete and the
arithmetic non-obvious enough (two independent sign flips composing) that
re-deriving it from the raw matrix, independently of every gate library
used so far in this feature's own verification, was the correct response
— and it confirms the spec's prose rather than finding an error in it.

## R2 — Executed multi-parameter verification: ≥2 distinct encoded parameters + 1 fixed group, 3 qubits

**Mandate** (spec.md SC-006, Assumptions "Phase 0 multi-parameter
verification mandate"): this feature's earlier verification (Clarifications
Findings 1-3) used at most ONE distinct encoded parameter at a time — this
must not be treated as evidence the interleaving logic or FR-011's angle
formula generalize to multiple simultaneous encoded parameters.

**Executed check.** A 3-qubit fixture with THREE declared groups, in this
caller order: encoded group `h1` (`X(q0)`, weight `1.0`), fixed group
(`ZZ(q0,q2)`, weight `1.0`, known `value=0.8` — a graph's own known edge
coupling), encoded group `h2` (`Z(q1)`, weight `1.0`) — two DISTINCT
encoded parameters (`h1`, `h2`), each with its own `parameter_index`, with
a fixed group interleaved BETWEEN them in the caller's declared order.
`tau=0.95`, `r=3` steps.

The mixed construction (the same refined, correctly-interleaved prototype
from Clarifications Findings 2-3) produced, for `r=3` steps, the gate-type
sequence:

```
['PauliTerm', 'FixedGate', 'PauliTerm',   # step 1: h1, fixed, h2
 'PauliTerm', 'FixedGate', 'PauliTerm',   # step 2: h1, fixed, h2
 'PauliTerm', 'FixedGate', 'PauliTerm']   # step 3: h1, fixed, h2
```

— correctly repeating the caller's declared `[h1, fixed, h2]` order at
every step, with exactly 2 distinct parameters registered
(`len(mixed_ir.parameters()) == 2`).

Its bound `Operator` (`alpha_h1=0.6`, `alpha_h2=-0.4`) was compared
against an INDEPENDENT hand-built target using raw `scipy.linalg.expm` on
full 3-qubit tensor-product Pauli matrices (bypassing every project and
Qiskit gate-construction code path used elsewhere in this feature — the
most independent check performed for this feature to date):

```
diff vs independent hand build: 7.108895957933346e-16
equiv: True
```

**Finding: the interleaving logic and the FR-011 angle formula generalize
exactly to a genuinely multi-parameter case** — machine-precision
agreement with an independent construction, confirming SC-006's mandate
is satisfied for at least the `2`-encoded-parameter case this check
exercises.

**Negative result, caught and corrected before being accepted (Constitution
§8.4) — the SECOND such episode in this feature's own verification
history**: the first attempt at this check reported `diff=0.2476`,
`equiv=False`. Root cause, on inspection, was NOT in the construction
under test but in this check's OWN independent hand-built comparison
circuit: the per-step unitary was assembled as
`U_h1 @ U_fixed @ U_h2` (matrix-multiplication order matching the
caller-declared group order left-to-right), which is backwards — circuit
composition order (`h1` applied first, then `fixed`, then `h2`, matching
`qc.append` order) corresponds to the matrix product
`U_h2 @ U_fixed @ U_h1` (the LAST-applied gate is the LEFTMOST matrix
factor). Correcting the composition order alone (no change to the
construction under test) brought the check to machine-precision agreement
above. This is the second time in this feature's own history that an
`Operator`-equivalence check's first attempt failed due to a bug in the
INDEPENDENT verification code rather than the construction being
verified (the first was Clarifications Finding 3's sign error in
converting to `RX`/`RZZ`'s native angle convention) — both are recorded
here per Constitution §8.4 rather than silently corrected and erased,
since each is itself evidence of how easy it is for an "independent"
check to be wrong in a way that looks like the construction under test
failing, and both were caught only by treating a failing equivalence
check as requiring root-cause diagnosis rather than either (a) trusting
the failure and reworking already-verified construction logic, or (b)
silently patching the check without recording why.

## R3 — Implementation shape confirmed, no new design questions raised

Both mandates for this Phase 0 round were resolved without requiring any
change to the mixed construction's design already verified in spec.md's
Clarifications (Findings 1-3): the two-pass approach (collect encoded
uploads in caller-declared step-major order, route them through
`pauli_pqc.build_ir` unchanged, then walk the same nested order a second
time interleaving pre-built `FixedGate`s with `build_ir`'s own validated
`PauliTerm` output) already generalizes correctly to ≥2 encoded
parameters (R2) and its angle formula was already correct as transcribed
into FR-011 (R1). `/speckit-tasks` can proceed directly from spec.md's
FR-001 through FR-011 and this file's R1/R2 findings without additional
Phase 0 design iteration.
