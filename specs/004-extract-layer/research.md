# Phase 0 Research: Extract Layer

Every formula below — the Hadamard-test circuit, the counts-to-amplitude
conversion, and the conjugate-symmetry claim it depends on — was checked
computationally in this session using the **exact same construction and
counts-processing formula this spec intends to ship**, not a simplified
stand-in: the same `compile_observable_circuit` call, the same `V_l`
construction, the same `AerSimulator.run()` + `get_counts()` execution path,
and the same `P(0) - P(1)` conversion. Where a check could be done exactly
(at the infinite-shot limit, via `Statevector`/`Operator` — a research-only
tool, never used in the production path itself, Constitution §3.3) it was,
specifically to rule out a small systematic bias that a single finite-shot
run could hide inside ordinary statistical noise.

One real bug surfaced and is recorded, not silently fixed: the first
`AerSimulator.run()` attempt raised `AerError: unknown instruction:
ccircuit-114` — controlled custom-gate objects must be `transpile()`d for
the target backend before `.run()`, not appended and run directly.

---

## R1. Module layout

**Decision**: `src/fourierlearn/extract.py` — a single new module, matching
the constitution's `ir → encodings → circuits → extract → ...` pipeline
naming (§9.1). It exposes:

- `estimate_coefficient(circuit: QuantumCircuit, l: tuple[int, ...], shots: int, seed: int | None = None) -> complex`
  (User Story 1 — single-frequency Hadamard-test estimate)
- `extract_coefficients(circuit: QuantumCircuit, shots: int, seed: int | None = None, budget: int = DEFAULT_SHOT_BUDGET, confirm: bool = False) -> dict[tuple[int, ...], complex]`
  (User Story 2 — full coefficient set, conjugate-symmetry shortcut)
- `ShotBudgetExceeded(RuntimeError)` (FR-007's locally-defined,
  interface-consistent-with-Spec-1 exception)

**Rationale**: `circuit` here is exactly Spec 3's `compile_observable_circuit`
output — this module never builds or duplicates that construction, only
wraps it with a Hadamard-test ancilla and executes it (Constitution §9.4).

---

## R2. The Hadamard-test circuit — the exact production construction

**Decision**: for one target frequency `l`, wrap the already-compiled
`A(U,O)` circuit (Spec 3) with:

1. One additional ancilla qubit (distinct from `A(U,O)`'s own internal
   parity-fold ancilla), initialised to `|0⟩`.
2. `H` on this new ancilla.
3. **Controlled**-`A(U,O)` (the entire compiled circuit, controlled by the
   new ancilla).
4. **Controlled**-`V_l†` on the frequency register(s), where `V_l := (V+)^l`
   — literally `l` repetitions of Circuits Layer's own cyclic-increment
   circuit (`_increment_circuit`, reused unchanged, not reimplemented,
   Constitution §9.4). `V_l† = (V-)^l`, `l` repetitions of its inverse.
   Negative `l` uses `|l|` repetitions of `V+` instead (since `(V-)^{-|l|}
   = (V+)^{|l|}`).
5. For the **real** part: `H` on the ancilla, then measure it.
   For the **imaginary** part: `S†` then `H` on the ancilla, then measure.
6. `P(\text{ancilla}=0) - P(\text{ancilla}=1)` (from `get_counts()`) gives
   `Re(b_l)` (real-part circuit) or `Im(b_l)` (imaginary-part circuit).

```python
def v_l_dagger_circuit(l0: int, freq_width: int) -> QuantumCircuit:
    qc = QuantumCircuit(freq_width)
    step = _increment_circuit(freq_width).inverse() if l0 >= 0 else _increment_circuit(freq_width)
    for _ in range(abs(l0)):
        qc.compose(step, inplace=True)
    return qc

def hadamard_test_circuit(l0: int, part: str) -> QuantumCircuit:
    had_anc = QuantumRegister(1, "had_anc")
    creg = ClassicalRegister(1, "c")
    qc = QuantumCircuit(had_anc, *qc_AUP.qregs, creg)
    qc.h(had_anc[0])
    qc.append(qc_AUP.to_gate(label="A(U,P)").control(1),
              [had_anc[0]] + qc.qubits[1 : 1 + qc_AUP.num_qubits])
    freq_qubits = list(qc.qregs[1])
    qc.append(v_l_dagger_circuit(l0, freq_width).to_gate(label="Vl_dag").control(1),
              [had_anc[0]] + freq_qubits)
    if part == "imag":
        qc.sdg(had_anc[0])
    qc.h(had_anc[0])
    qc.measure(had_anc[0], creg[0])
    return qc
```

**Why `V_l = (V+)^l` is the correct choice, not an arbitrary one satisfying
"any unitary with `V_l|0⟩ = |l⟩`"** (Barthe thesis Corollary 5.1 only
requires that property, which under-specifies `V_l`'s action on every other
basis state): for the formula `b_l = ⟨0|(V_l†⊗I)A(U,O)|0⟩` to correctly
isolate *only* the `l`-th term of `A(U,O)|0⟩ = Σ_l b_l|l⟩|0⟩ + \text{trash}`,
`V_l†` must send *every* `|l'⟩` (not just `|l⟩`) to something orthogonal to
`|0⟩` unless `l'=l`. A cyclic shift satisfies this exactly:
`(V-)^l|l'⟩ = |l'-l \bmod 2^w⟩`, which equals `|0⟩` iff `l'=l` (mod the
register's own range) — confirmed computationally below, not merely argued.

---

## R3. Exact-limit verification against the oracle — the full production formula, not a toy

Using the exact fixture this spec's own FR-010 mandates reuse of (Spec 3
research.md R8: `X, X, Z` untied uploads, `S` then `T` fixed gates,
observable `X`), the Hadamard-test circuit above was evaluated **exactly**
(via `Statevector` on the no-measurement version — a research-only tool) for
every representable frequency:

```
l    exact_estimate                    oracle b_l                      |diff|
-6   -0.08838834764829911-0.08838834764829567j   -0.08838834764831863-0.08838834764831831j   3.0e-14
-4    0.17677669529659445-0.17677669529659923j    0.1767766952966368-0.1767766952966368j     5.7e-14
-2    0.08838834764829667-0.08838834764830100j    0.08838834764831861-0.08838834764831831j    2.8e-14
 0   -0.35355339059320195+2.2e-15j                -0.3535533905932736+0j                      7.2e-14
 2    0.08838834764830000+0.08838834764829656j    0.08838834764831861+0.08838834764831831j    2.9e-14
 4    0.17677669529660234+0.17677669529660062j    0.1767766952966368+0.1767766952966368j      5.0e-14
 6   -0.08838834764829550+0.08838834764830023j   -0.08838834764831863+0.08838834764831831j    2.9e-14
(odd l: exactly 0, matching the oracle exactly)
ALL MATCH (< 1e-9): True
```

Agreement is at the ~1e-14 level (floating-point noise from repeated gate
composition, not a physical discrepancy) — this is the exact production
circuit and formula, evaluated at infinite shots, matching the oracle
essentially to machine precision.

---

## R4. Conjugate symmetry, verified on the estimator's own exact output — the Clarifications mandate

**This is the specific check `/speckit-clarify` (2026-08-20) required before
FR-006's shortcut may be relied upon**: not just that the oracle's own `b_l`
values satisfy `b_{-l}=\overline{b_l}` (already confirmed separately at the
clarify stage), but that *this estimator's own* raw output at `+l` and its
raw output at the register-decoded `-l` are exact conjugates:

```
l=2: est(+l)=0.08838834764830+0.08838834764829656j
     est(-l)=0.08838834764829667-0.08838834764830100j
     conj(est(+l))=0.08838834764830-0.08838834764829656j
     match=True
l=4: est(+l)=0.17677669529660234+0.17677669529660062j
     est(-l)=0.17677669529659445-0.17677669529659923j
     conj(est(+l))=0.17677669529660234-0.17677669529660062j
     match=True
l=6: est(+l)=-0.08838834764829550+0.08838834764830017j
     est(-l)=-0.08838834764829911-0.08838834764829567j
     conj(est(+l))=-0.08838834764829550-0.08838834764830017j
     match=True

ALL CONJUGATE MATCHES EXACT: True
```

No sign flip anywhere in the counts-to-amplitude formula or in the
register-decoded `-l` construction: `V_{-l}† = (V+)^{l}` is exactly what
`_increment_circuit`'s own `.inverse()` composition already gives for a
negative shift amount, with no separate sign-handling code path to get
wrong. The DC term (`l=0`) is its own mirror and came out exactly real
(`2.2e-15` imaginary part) — the same check FR-012 elevates to a permanent,
per-run test assertion, not only a one-time design-time observation.

---

## R5. Real, finite-shot execution — measurement-only, the actual production path

The same circuits were then run with **real** `AerSimulator.run()` +
`get_counts()` (Constitution §9.6's Aer-native batched path; no `Statevector`
or `Operator` anywhere in this step):

```python
sim = AerSimulator()
re_qc = transpile(hadamard_test_circuit(l0, "real"), sim)
im_qc = transpile(hadamard_test_circuit(l0, "imag"), sim)
re_counts = sim.run(re_qc, shots=shots, seed_simulator=seed).result().get_counts()
im_counts = sim.run(im_qc, shots=shots, seed_simulator=seed + 1).result().get_counts()
p0_re, p1_re = re_counts.get("0", 0) / shots, re_counts.get("1", 0) / shots
p0_im, p1_im = im_counts.get("0", 0) / shots, im_counts.get("1", 0) / shots
estimate = complex(p0_re - p1_re, p0_im - p1_im)
```

**Bug found and fixed (recorded per Constitution §8.4, not silently
corrected)**: the first attempt called `sim.run(qc, ...)` directly on the
circuit containing a controlled custom `Gate` object and failed with
`AerError: unknown instruction: ccircuit-114` — Aer does not know how to
execute an un-decomposed composite controlled-gate instruction. Fix:
`transpile(qc, sim)` before `.run()`, which decomposes it into Aer-native
basis gates. This is now a required step in the production execution path,
not an optional performance nicety.

At `shots=200,000` (all 7 nonzero frequencies of the mandated fixture,
seed=42):

```
l    estimate                         oracle b_l                     |diff|
-6   -0.08653-0.09096j                -0.08838834764831863-0.08838834764831831j  0.0032
-4    0.17510-0.18045j                 0.1767766952966368-0.1767766952966368j    0.0040
-2    0.08763-0.08641j                 0.08838834764831861-0.08838834764831831j   0.0021
 0   -0.35639+0.00008j                -0.3535533905932736+0j                     0.0028
 2    0.09166+0.08766j                 0.08838834764831861+0.08838834764831831j   0.0034
 4    0.17944+0.17573j                 0.1767766952966368+0.1767766952966368j    0.0029
 6   -0.08878+0.08783j                -0.08838834764831863+0.08838834764831831j   0.0007
```

Every error is `O(1/\sqrt{200000}) \approx 0.0022` — consistent with shot
noise, not a systematic offset (verified: R3/R4 already ruled out a
systematic bias at the exact-limit level; this table confirms the *finite*
shot execution path reproduces that same unbiased estimator).

**Convergence trend** (target `l=4`, increasing shot counts, same seed
pattern):

```
shots=      1000  |error|=0.05513  1/sqrt(shots)=0.03162  ratio=1.74
shots=     10000  |error|=0.02178  1/sqrt(shots)=0.01000  ratio=2.18
shots=    100000  |error|=0.00293  1/sqrt(shots)=0.00316  ratio=0.93
shots=   1000000  |error|=0.00063  1/sqrt(shots)=0.00100  ratio=0.63
```

Error shrinks monotonically as shots increase, at the expected
`1/\sqrt{\text{shots}}` order of magnitude — this is the concrete evidence
FR-009's convergence test formalizes.

---

## R6. Concentration-bound tolerance (Constitution §4.4) — Hoeffding, derived not guessed

**Decision**: each Hadamard-test circuit's ancilla measurement is a Bernoulli
draw; `\hat P(0) = \frac{1}{N}\sum_i X_i` (`X_i \in \{0,1\}`, `N` = shots)
is a mean of bounded `[0,1]` variables. Hoeffding's inequality gives
`P(|\hat P(0) - P(0)| \ge t) \le 2\exp(-2Nt^2)`. Since the reported estimate
is `2\hat P(0) - 1` (twice the error of `\hat P(0)`), substituting
`\varepsilon = 2t`:

```
P(|estimate - true| >= eps) <= 2 exp(-N eps^2 / 2)
```

Solving for `\varepsilon` at confidence `1-\delta`:

```
eps(N, delta) = sqrt(2 * ln(2/delta) / N)
```

This is the per-part (real or imaginary) bound; the convergence test (FR-009)
applies it independently to the real and imaginary parts of each checked
coefficient, at a fixed, stated `\delta` (e.g. `0.01`), and the ratio table
in R5 above (`0.63`-`2.18`, all `O(1)`) confirms this is the right *order* of
bound to use — not so loose it never fails, not so tight it fails on
ordinary statistical fluctuation.

---

## R7. Cost-budget guard — mirrors Spec 1's interface style, not its implementation

**Decision** (Clarifications 2026-08-20): `extract_coefficients` predicts the
total execution cost (number of Hadamard-test circuits × shots per circuit)
before running, logs it, and raises `ShotBudgetExceeded` (defined locally in
`extract.py` — never imported from `fourierlearn.reference`, which only
`reference.py` itself may import, per this spec's own FR-001) unless
`confirm=True` is passed — the same `RuntimeError`-subclass-plus-`confirm=True`
kwarg pattern as Spec 1's `CostBudgetExceeded`/`coefficients(budget=...,
confirm=...)`, so callers familiar with one guard immediately recognize the
other, per explicit instruction.

---

## R8. DC Hermiticity check — load-bearing, not informational (FR-012)

**Decision**: `extract_coefficients`'s own test suite asserts, for every
full-coefficient-set extraction it exercises (not only the dedicated
convergence-test fixture), that the DC (`l=0` / all-zero-tuple) coefficient's
imaginary part is within that run's own R6-derived tolerance of zero. R3/R4
above already confirm this holds at the exact-limit level for the mandated
fixture (`Im(b_0) = 2.2\times10^{-15}`); the *test* assertion is what carries
this check forward into every future run of the actual, shot-based
implementation — a live regression guard on the Hermiticity precondition
FR-006's conjugate-symmetry shortcut depends on, not merely a design-time
note.

---

## R9. No optimisation (Constitution §5.3)

**Decision**: `estimate_coefficient`/`extract_coefficients` build one
Hadamard-test circuit per (frequency, real-or-imaginary-part) pair and
execute it once per call; no caching of compiled Hadamard-test circuits
across calls with the same frequency, no batching of multiple frequencies'
circuits into one `sim.run()` call (Qiskit/Aer does support submitting a
*list* of circuits to one `run()` call, which is a legitimate, physics-neutral
batching of *independent* circuit executions rather than a shortcut that
changes what is computed — but no profiled bottleneck exists yet to justify
adopting it, so it is deliberately not done here, per §5.3's "no
optimisation without a recorded profile identifying the bottleneck it
targets"), and no template reuse across different target frequencies beyond
the already-existing reuse of Spec 3's `compile_observable_circuit` and
Circuits Layer's own `_increment_circuit` (reuse of *existing, already-built*
components is not the kind of optimisation §5.3 restricts — duplicating
either would itself violate §9.4).

**Alternative considered and rejected**: submitting all of one coefficient's
real- and imaginary-part circuits (or all frequencies') as a single batched
`sim.run([...])` call — plausible future speedup, but not adopted without a
recorded profile showing execution-call overhead, specifically, is the
bottleneck (as opposed to, e.g., shot count itself, which no batching
changes).
