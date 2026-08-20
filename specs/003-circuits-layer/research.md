# Phase 0 Research: Circuits Layer

Every sign, coefficient, phase, and gate-ordering decision below was checked
computationally in this session — against a hand-built target matrix, an
independent brute-force ground truth, or (where the mandate names it
explicitly) `qiskit.quantum_info.Operator.equiv` — before being written down
as a decision. Verification code, exact matrices, and numeric results are
inlined, not merely referenced, per explicit instruction: this document is
what the test implementation is anchored to, not a summary of spec.md's
Clarifications.

Two of the checks below (R5, R6) caught real bugs in the verification code
itself (a reversed CNOT control/target direction; a doubled S/S† gate from a
copy-paste slip) before they produced a false result — both are documented as
findings, not silently fixed and hidden, per Constitution §8.4.

---

## R1. Module layout

**Decision**: `src/fourierlearn/circuits.py` — a single new module, matching
the constitution's `ir → encodings → circuits → extract → ...` pipeline
naming (§9.1) directly. It exposes:

- `compile_frequency_circuit(ir: PauliEncodedCircuitIR) -> QuantumCircuit`
  (User Story 1 — `A(U)`)
- `compile_observable_circuit(ir: PauliEncodedCircuitIR, observable: SparsePauliOp) -> QuantumCircuit`
  (User Story 2/3 — `A(U, O)`, observable folding with basis change built in)
- `basis_change_gates(pauli_letter: str) -> tuple[Gate, Gate]` (FR-014's single
  shared helper, module-private naming TBD at `/speckit-tasks`)

**Rationale**: `compile_observable_circuit` internally calls
`compile_frequency_circuit` for its forward pass, and reuses the same
`basis_change_gates` helper `compile_frequency_circuit` uses for encoding
gates — making reuse the only path, not an option (Constitution §9.4), as
required by FR-006/FR-014.

---

## R2. Frequency-counter register sizing — reused, not redefined

**Decision**: one register per encoded parameter, width computed by calling
`frequency.register_width(uploads, r_j)` (Spec 1, already implemented and
tested) — never a redefined or duplicated formula (FR-002, FR-010,
Constitution §6.3/§9.4). No new verification needed here: this module already
has 9/9 passing tests in Spec 1 and is reused as-is.

---

## R3. The parity-fold primitives `D` and `G` — structural identities verified

**Decision**: for each encoding gate, `D` computes the parity of the gate's
affected qubits onto the single shared ancilla via a CNOT chain (control =
each affected circuit qubit, target = ancilla); `G` applies a controlled
cyclic shift to the gate's parameter's frequency register, conditioned on the
ancilla (Barthe thesis §5.7.3, Theorem 5.1).

**Pinned sign convention (verified against the actual Fourier decomposition,
not assumed from the thesis's own informal parity-sign remark)**: ancilla
`= 0` (even parity) → **increment** (`V+`); ancilla `= 1` (odd parity) →
**decrement** (`V-`). This was confirmed by directly comparing a compiled
circuit's amplitudes against an independent brute-force grid-and-FFT ground
truth for a real physical circuit (`H`-`Z(θ)`-`H`, a textbook Ramsey
interferometer) — the *opposite* assignment (ancilla=1→increment) was tried
first and gave a mismatch (all weight collapsed onto one frequency slot
instead of the correct four-term superposition); only the assignment above
reproduced the correct, independently-computed `a_{l,k}` table below.

```python
# D: CNOT(control=affected circuit qubit, target=ancilla), built PROGRAMMATICALLY
# from its own definition (iterate every basis state, compute where it maps),
# not hand-typed -- an earlier hand-typed 4x4 CNOT had the control/target
# direction backwards and was only caught by comparing against ground truth.
def cnot_on_full_space(dims, control_axis, target_axis):
    n = len(dims); total = int(np.prod(dims))
    strides = [int(np.prod(dims[i+1:])) for i in range(n)]
    M = np.zeros((total, total))
    for flat in range(total):
        idx = []; rem = flat
        for i in range(n):
            idx.append(rem // strides[i]); rem %= strides[i]
        new_idx = list(idx)
        if idx[control_axis] == 1:
            new_idx[target_axis] = 1 - idx[target_axis]
        new_flat = sum(new_idx[i]*strides[i] for i in range(n))
        M[new_flat, flat] = 1.0
    return M

# G: controlled cyclic shift -- anc=0 -> V+ (increment), anc=1 -> V- (decrement)
def controlled_shift(dims, freq_axis, freq_dim, ancilla_axis, shift_anc1, shift_anc0):
    ...  # shift_anc1=-1, shift_anc0=+1 is the verified-correct assignment
```

**Ground truth this pinned the sign against** (1 qubit, `H`-`Z(θ)`-`H`, `θ=πα`,
`N=5` grid points for `r_j=1, L=1`):

```
l=  1  k=0  amp=0.5   l=  1  k=1  amp=0.5
l= -1  k=0  amp=0.5   l= -1  k=1  amp=-0.5
```

Compiled circuit (with the pinned sign convention) reproduced this table
exactly. `Block = D @ G @ D` is the reusable per-encoding-gate unit; `D`
being a CNOT chain is self-adjoint (`D† = D`) — a fact used directly in R5.

---

## R4. Shared ancilla concurrency — one, reused serially, verified under contention

**Decision**: exactly one ancilla qubit, shared by every encoding gate in the
compiled circuit regardless of which parameter it drives (Barthe thesis
§5.7.3: "There is also a single additional ancillary qubit that is used to
compute parities" — omitting the sharing costs an overhead exponential in
Pauli-string locality). Each encoding gate's own `D`-`G`-`D` block leaves the
ancilla reset to `|0⟩` before the next gate (of any parameter) uses it.

This was stress-tested, not merely asserted — see R5, which builds and
verifies a 2- and then a 3-parameter circuit with tied multiplicity and fully
interleaved gates, all sharing this one ancilla, and confirms no
cross-parameter or cross-gate interference results.

---

## R5. The reversed-pass identity for `A(U, O)` — verified at three levels of stress

**Decision (FR-006)**: the reversed pass is the **literal inverse of the
already-assembled forward-compiled circuit** (`compiled_circuit.inverse()` in
Qiskit) — not a second, independently written reverse-order construction.
This is not a design preference stated without proof: the two candidates were
proven identical, algebraically and then computationally, at increasing
levels of stress.

### R5.1 Algebraic identity (why this must be true in general)

`D` is self-adjoint (a CNOT chain: `D† = D`). `G = C(a=0)V+ + C(a=1)V-` has
`G† = C(a=0)V+† + C(a=1)V-† = C(a=0)V- + C(a=1)V+` — exactly the role-swapped
block (`V+`/`V-` exchanged), since `V-  = V+†`. For **any** product of gates
`ABC...`, `(ABC...)† = ...C†B†A†` — reversed order, each factor individually
adjointed. Since every factor in a compiled circuit is one of `D` (self-adjoint),
`G` (adjoint = role-swapped `G`), or an ordinary fixed gate (adjoint = its own
adjoint), the full-circuit inverse and a separately-reconstructed reverse-order
pass with role-swapped primitives are the **same expression** by pure
associativity — true regardless of parameter count, tying, or interleaving.
This is why R5.2–R5.4 below are expected to hold structurally; they were run
anyway, because an algebraic argument is not the same as a verified one
(exactly the discipline this spec's mandate exists to enforce).

### R5.2 Minimal case (1 parameter, `L=2` uploads, one fixed gate)

```python
AU_forward = FixedH @ Block @ FixedS @ Block @ FixedH   # H-Z(a)-S-Z(a)-H
R1 = AU_forward.conj().T
R2 = FixedH @ Block_swapped @ FixedSdag @ Block_swapped @ FixedH
# R1 == R2: True   (max|R1-R2| = 0.0)
```

Full `A(U,P)` (forward, insert `Z` observable, `R1` as reversed pass) matched
an independent brute-force 9-point grid + FFT ground truth exactly at every
`l ∈ {-4,...,4}`, including the genuinely non-DC, non-degenerate coefficient
`l=±4: ∓0.5j` (real error ≤ 1e-9).

### R5.3 Stress case (2 parameters, one tied `r_j=2`, fully interleaved)

Parameter `A` tied with multiplicity 2 (its two `Z`-type terms deliberately
**not** adjacent in the gate list); Parameter `B` untied; gate order
`[A-term1, B, A-term2]`; both frequency registers independently and correctly
sized (`A`: `r_j=2,L=1` → 16 states; `B`: `r_j=1,L=1` → 8 states); one shared
ancilla.

```python
AU_forward = FixedH_q0 @ Block_A_q1 @ Block_B_q1 @ Block_A_q0 @ FixedH_q0
R1 = AU_forward.conj().T
R2 = FixedH_q0 @ Block_A_q0_swapped @ Block_B_q1_swapped @ Block_A_q1_swapped @ FixedH_q0
# R1 == R2: True   (max|R1-R2| = 0.0)
```

Full `A(U,P)` (observable `Z@q0`) matched an independent 2-D brute-force
(`9×5` grid) ground truth exactly across the whole grid, including
`(l_A,l_B)=(±4,0): ∓0.5j`.

### R5.4 Final stress case (3 parameters, TWO tied `r_j=2`, fully interleaved) — this spec's own mandate

Parameters `A` and `B` **both** tied with multiplicity 2; Parameter `C`
untied; gate order `[A1, B1, C, A2, B2]` (both tied pairs split apart by other
parameters' gates); circuit qubits reused across parameters (`A1=Z@q0,
B1=Z@q1, C=Z@q0, A2=Z@q1, B2=Z@q0`) to additionally stress qubit overlap;
registers: `A`,`B`: `r_j=2,L=1`→16 states each, `C`: `r_j=1,L=1`→8 states.
Total Hilbert space dimension `16×16×8×2×2×2 = 16384` — built with
`scipy.sparse` (every primitive here is a permutation or ≤2-nonzero-per-row
matrix, so construction and multiplication stay fast and light even at this
size; a dense array here would be a ~4.3 GB matrix multiply, not run).

```python
AU_forward = FixedH_q0 @ Block_B2 @ Block_A2 @ Block_C @ Block_B1 @ Block_A1 @ FixedH_q0
R1 = AU_forward.conj().T
R2 = FixedH_q0 @ Block_A1_sw @ Block_B1_sw @ Block_C_sw @ Block_A2_sw @ Block_B2_sw @ FixedH_q0

diff = (R1 - R2)
# R1 == R2: True
# max|R1-R2| = 0.0
# R1 nnz: 65536  (out of 16384^2 = 268,435,456 possible entries -- confirms
#                 the primitives really do stay sparse/structured throughout)
```

Full `A(U,P)` (observable `Z@q0`) matched an independent 3-D brute-force
(`9×9×5 = 405`-point grid) ground truth **exactly across the entire grid**
(post-select probability `0.5`, nonzero coefficients at
`(l_A,l_B,l_C) = (±2,±2,±2): 0.5` exactly, matching to the FFT's own float
noise floor).

**Conclusion**: FR-006's mandate (literal circuit inverse, not a second
hand-maintained construction) holds under genuine multi-parameter,
multi-tied, fully-interleaved, shared-ancilla contention — not only in the
simplest case capable of exercising it.

### R5.5 Confirmed with the actual implementation technology (`qiskit.quantum_info.Operator.equiv`)

The minimal case (R5.2) was rebuilt as a real `QuantumCircuit` (Qiskit's own
`UnitaryGate.control()` for the ancilla-controlled `V+`/`V-`, real `cx`, `h`,
`s`/`sdg`) and compared via the actual API the mandate names:

```python
qc = QuantumCircuit(6)                     # 4 freq qubits, 1 ancilla, 1 circuit qubit
qc.h(circ); build_block(qc, ...); qc.s(circ); build_block(qc, ...); qc.h(circ)
R1_qiskit = Operator(qc.inverse())

qc_reversed = QuantumCircuit(6)
qc_reversed.h(circ); build_block_swapped(qc_reversed, ...)
qc_reversed.sdg(circ)
build_block_swapped(qc_reversed, ...); qc_reversed.h(circ)
R2_qiskit = Operator(qc_reversed)

R1_qiskit.equiv(R2_qiskit)   # True
R1_qiskit == R2_qiskit       # True -- exact, not just equal up to global phase
```

**Finding, recorded per Constitution §8.4**: the first attempt at this Qiskit
check returned `False` for both `.equiv()` and `==`. Cause: a copy-paste slip
applied `qc_reversed.s(circ).inverse()` **and then also** `qc_reversed.sdg(circ)`
to the reversed circuit — two gates instead of one. Fixing it to a single
`sdg(circ)` call (correctly adjointing the one `S` gate in the forward
circuit) gave the `True`/`True` result above. This is exactly the kind of
verification-code bug this spec's own discipline exists to catch before it
becomes a false "confirmed" result — recorded, not quietly corrected.

### R5.6 `==` vs `.equiv()` for the dedicated test — checked, not assumed either way

A later review raised a reasonable general concern: `QuantumCircuit.inverse()`
and a separately hand-built reverse circuit can, in Qiskit, sometimes differ
by an unobservable global phase, so the dedicated equivalence test should use
`.equiv()` rather than exact `==`. This was checked directly, at the scale it
actually matters (R5.3's 2-parameter, tied-multiplicity, interleaved,
shared-ancilla case — the same mechanism the concern is about, not just the
1-qubit minimal case above), using real `QuantumCircuit`/`UnitaryGate.control()`
objects, not raw numpy:

```python
R1_qiskit = Operator(qc.inverse())          # 10-qubit circuit: 4+3 freq qubits, 1 ancilla, 2 circuit qubits
R2_qiskit = Operator(qc_reversed_separate)  # independently built, role-swapped reverse pass

R1_qiskit.equiv(R2_qiskit)   # True
R1_qiskit == R2_qiskit       # True
max(abs(R1_qiskit.data - R2_qiskit.data))       # 2.4e-14 (gate-synthesis float noise, not a phase)
(R1_qiskit.data / R2_qiskit.data)[first nonzero]  # 1.0000000000000082+9.68e-15j -- ratio is 1, not e^{i*theta!=0}
```

**Result: `==` holds, not merely `.equiv()`, and the tiny residual (~1e-14) is
ordinary floating-point noise from Qiskit's own gate-decomposition machinery,
not a phase discrepancy** — the amplitude ratio at a nonzero entry is `≈1`
with a negligible imaginary part, not `e^{iθ}` for any real `θ≠0`. This
matches the algebraic argument in R5.1: every factor's adjoint (`D`
self-adjoint, `G→G_swapped`, fixed gates → their own adjoint) is an exact,
phase-free operation, so no global phase has anywhere to enter.
**Conclusion: T009's dedicated test correctly asserts exact `==`, not
`.equiv()`.** Downgrading to `.equiv()` would make the test strictly weaker
without a verified reason — it would still pass if a future implementation
bug introduced a real, wrong phase (the same class of defect Spec 1/2's own
sign-convention tests were specifically built to catch via exact, not
up-to-phase, comparison) — so the stronger assertion is kept because it was
checked to hold, not loosened on the strength of a general worry about
Qiskit that does not apply to this specific construction.

### R5.7 Implementation-time finding: `Operator()` is impractical at 14 qubits; controlled-shift gates rebuilt for direct control injection

Two findings surfaced while implementing T009's actual pytest test, both
recorded here rather than silently worked around:

1. **`gate.control(1, ctrl_state=...)` wrapping an already-multi-controlled
   sub-circuit is not how `_append_controlled_shift` should be built.**
   Wrapping the whole `_increment_circuit` (itself built from nested `MCX`
   gates) in a further `.control()` layer works, but `Operator()`
   reconstruction of the resulting circuit at the 14-qubit stress scale did
   not complete in several minutes. Rebuilt as `_controlled_increment_direct`:
   add the ancilla as one extra control directly on each `MCX`/`X` gate of the
   plain increment circuit, rather than control-wrapping the assembled
   sub-circuit — verified to give the numerically identical operator to the
   `.control()`-wrapped version (`np.allclose` on the full matrix, small
   width) before adopting it, and confirmed correct end-to-end via T003/T004's
   own equivalence tests passing unchanged. This also required determining
   Qiskit's own `ctrl_state` string bit-ordering experimentally (rightmost
   character = first control qubit in the list) rather than assuming it.
   **This assumption now has its own minimal, dedicated regression test**
   (`test_mcx_ctrl_state_bit_ordering_truth_table`, added on review): a
   direct 2-control/1-target truth table against `Operator`, independent of
   the larger parity-fold/reversed-pass tests, so a future Qiskit convention
   change fails here specifically rather than as an opaque mismatch inside a
   14-qubit circuit.
2. **Even with the faster gate construction, full `Operator()` reconstruction
   at 14 qubits remains impractical for a test suite.** Measured directly:
   `Operator()` on a trivial 14-qubit, 1-gate circuit alone costs ~10.5s
   (fixed dense-matrix-reconstruction overhead, independent of gate
   complexity) — a full multi-gate circuit at this scale would cost minutes.
   `Statevector` evolution of the same circuit costs ~2-3s. T009's actual
   test therefore compares `Statevector` evolution of `forward.inverse()`
   against the independently-built reversed pass on **two** input states
   (`|0...0⟩` and an independent Haar-random state), asserting exact complex
   amplitude agreement (not just probabilities, so a phase-only difference
   would still be caught) rather than reconstructing the full operator. Two
   distinct unitaries agreeing exactly on a Haar-random state has probability
   zero by chance, and R5.6 already established `==` (full operator equality,
   not just `.equiv()`) holds for this exact construction via real, dense
   `Operator` objects at a smaller-but-structurally-identical 2-parameter
   scale — so this substitution preserves what R5.6's own finding is meant to
   guard against, at a scale where reconstructing the full operator is
   simply not a practical implementation choice.

---

## R6. Basis-change sandwich for encoding gates (User Story 1, FR-005) — derived and verified per Pauli letter

**Decision**: for a non-`Z` encoding gate `e^{iπαP}`, find the fixed unitary
`W_P` such that `P = W_P · Z · W_P†`, then compile the gate as
`W_P† (temporal-first) → standard Z-fold block → W_P (temporal-last)` —
i.e. `e^{iπαP} = W_P · e^{iπαZ} · W_P†` (a standard similarity-conjugation
identity for matrix exponentials, valid for any unitary `W_P`).

**`X`**: `W_X = H` (self-adjoint, so `W_X = W_X†`).

```python
>>> np.allclose(H @ Z @ H, X)
True
>>> np.allclose(H @ Ez(theta) @ H, expm(1j*theta*X))   # for a concrete theta=0.37
True
```

**`Y`**: searched computationally rather than assumed — `W_Y = S · H`:

```python
>>> W_Y = S @ H
>>> np.allclose(W_Y @ Z @ W_Y.conj().T, Y)
True
>>> np.allclose(expm(1j*theta*Y), W_Y @ Ez(theta) @ W_Y.conj().T)   # theta=0.53
True
```

(Three other candidate orderings — `H@S†`, `H@S`, `S†@H` — were tried in the
same sweep and rejected; only `S@H` satisfies `W Z W† = Y` with this phase
convention. `W_Y† = H·S†`.)

**End-to-end verification against a REAL physical gate (not just the algebraic
identity)**: two untied `X`-encoding uploads (`L=2`) with a fixed `S` gate
between them, each compiled as `H`-`Zfold`-`H`, observable `Z`:

```
l   compiled(basis-change X-encoding x2)   ground_truth(real e^{i theta X} gates)
-4  0.25                                    0.25
 0  0.5                                     0.5
+4  0.25                                    0.25
(all other l: 0, matching to float noise)
ALL MATCH: True
```

Same construction repeated with `Y` (`W_Y`-sandwiched) against real
`e^{iθY}` gates: **identical table, ALL MATCH: True.**

Both are genuinely non-degenerate (post-select probability `0.375`, three
distinct nonzero coefficients) — not a trivial all-zero or single-term case
that could mask a sign or ordering defect (Constitution §4.3). **Note (added
during implementation, not silently corrected): "non-degenerate" here means
several distinct nonzero terms, not "genuinely complex" — every value in this
specific table (`0.25`, `0.5`, `0.25`) is purely real.** This construction is
sufficient for R6's own purpose (confirming the basis-change-compiled gate
matches a real `e^{iθP}` gate), but it is **not** a valid fixture for
FR-013's genuinely-complex-coefficient requirement. That requirement is
addressed separately below (R8) with a construction found, by exhaustive
search, to actually produce a complex non-DC coefficient — a mix-up that was
only caught because T011's own test asserted non-triviality explicitly and
failed on the first (wrong) fixture, exactly the kind of thing Constitution
§4.3 exists to catch.

---

## R7. Observable folding (User Story 2/3, FR-006–FR-008, FR-014) — a real architectural finding

**Finding, verified computationally, not assumed from the thesis's prose**: a
**single Pauli-string observable is Hermitian and unitary**, so it can be
inserted directly as an actual gate at the `A(U,P)` insertion point — no
basis-change wrapping is structurally required *at that specific point* for
correctness. This was confirmed by comparing "insert `X` directly" against
"insert `H·Z·H`" (the *same matrix*, by R6's own identity) — both,
necessarily, give identical results — and separately confirming direct
insertion of `X` and of `Y` against independently computed ground truth for
`f(α) = ⟨0|U(α)†PU(α)|0⟩` on a genuinely non-degenerate circuit:

```
observable=X (direct insertion): l=-4: 0.5j   l=+4: -0.5j   ALL MATCH: True
observable=Y (direct insertion): l=-4: 0.5    l=+4: 0.5     ALL MATCH: True
```

**Why this does not contradict FR-014's "single shared helper" mandate**: the
helper's output (`W_P`, `W_P†`) can still be used to construct
`W_P · Z · W_P† ≡ P` as the inserted gate — this is provably the identical
matrix to inserting `P` directly (R6's own defining identity), so both are
correct, and using the shared helper here is a matter of **implementation
uniformity** (treating every Pauli letter through the one helper, avoiding a
branch on "is this letter already `Z`?" — Constitution §9.3) rather than a
second, independently necessary derivation. FR-005's need for the helper is
structural (the encoding gate is *replaced*, not inserted, so it must be
expressed in terms of the `Z`-fold primitives); FR-008's use of the same
helper is for architectural consistency, not because direct insertion would
otherwise be wrong. Both are recorded so `/speckit-tasks` does not have to
re-derive this distinction from scratch.

**`_insert_observable`'s little-endian reversal, verified with an
asymmetric fixture (added on review)**: `_insert_observable` reads a
`SparsePauliOp` label and reverses it before indexing qubits (Qiskit's
label convention is little-endian: rightmost character = qubit 0). A
symmetric test observable (e.g. `'ZIZ'`) cannot catch a backwards reversal —
swapping two identical halves is invisible. `test_asymmetric_multiqubit_
observable_respects_little_endian_labels` uses `'IXZ'` (`Z@q0`, `X@q1`,
`I@q2`) on a circuit where qubit 0 (`H`-`Z(alpha)`-`H`, genuinely
alpha-dependent under `Z`) and qubit 2 (no gates, stays `|0⟩`, so `Z` there
reads a trivial constant) are deliberately different — confirmed
computationally that a backwards (non-reversed) reading of the label
collapses the result to a trivial `l=0: 1.0` constant (discarding qubit 0's
genuine structure entirely), while the correct reversal reproduces the
oracle's own `l=±2: 0.5` result exactly. This is a real discriminating check,
not merely a passing one.

---

## R8. A genuinely complex fixture for FR-012/FR-013's oracle validation — found by exhaustive search, not assumed

**Finding, recorded per Constitution §8.4**: while implementing T011's oracle
validation test, the construction R6 described as "genuinely non-degenerate"
(two `X`-encoding uploads with a fixed `S` gate, observable `Z`) was reused,
by mistake, as if it were also "genuinely complex." It is not — every value
in that table (`0.25`, `0.5`, `0.25`) is purely real. The mistake was caught
by the test itself: T011 asserts non-triviality (both real and imaginary
parts individually `>1e-2`) explicitly, and the assertion failed on the first
attempt, exactly what that check exists to catch (Constitution §4.3) — not a
defect in `compile_observable_circuit`, but in the fixture chosen to validate
it.

**A single-Pauli-string observable case cannot always be found trivially**:
an exhaustive search over every combination of two untied encoding letters
(`X`/`Y`/`Z`), a single fixed gate (`S` or `H`) between them, and a
single-letter observable (`X`/`Y`/`Z`) — 3×3×2×3 = 54 combinations — found
**zero** genuinely complex non-DC coefficients. Broadening to three untied
uploads with two interspersed fixed gates (`S`, `H`, or `T`) found the first
hit at `(X, X, Z)` encoding, `S` then `T` fixed gates, observable `X`:

```python
u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
ir = PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))
```

`fourierlearn.reference.coefficients(ir)` (Spec 1's own oracle) gives, among
several nonzero terms:

```
l=-6: -0.08838834764831863-0.08838834764831831j
l=-4:  0.17677669529663680-0.17677669529663680j
l=-2:  0.08838834764831861-0.08838834764831831j
l= 0: -0.35355339059327360+0j
l=+2:  0.08838834764831861+0.08838834764831831j
l=+4:  0.17677669529663680+0.17677669529663680j
l=+6: -0.08838834764831863+0.08838834764831831j
```

`compile_observable_circuit(ir, SparsePauliOp("X"))`'s raw post-selected
amplitude at each `l` matches this table exactly (relative error ≤ 1e-9),
including `l=4: 0.1767766952966368+0.1767766952966368j` — both parts
individually well above the `1e-2` non-triviality threshold. The `T` gate
turned out to matter: sweeps using only `S`/`H` as the interspersed fixed
gate (with any letter/observable combination, up to three uploads) found no
complex case; only introducing `T` (an eighth-root phase, not a Clifford
gate) broke whatever residual symmetry was otherwise keeping every candidate
purely real or purely imaginary.

---

## R9. Concrete anchoring for FR-011 (dedicated equivalence tests)

The following are the actual test shapes `/speckit-tasks`/`/speckit-implement`
will instantiate — sketched here with real Qiskit constructs, not pseudocode,
matching Spec 1's `test_ir_gate_convention.py` precedent:

```python
def test_parity_fold_block_matches_hand_built_target():
    """R3: the D-G-D block for a single-qubit Z encoding gate, compared
    directly against the hand-derived 4-term superposition target."""
    qc = QuantumCircuit(freq_reg, ancilla, circuit_reg)
    qc.h(circuit_reg)                       # break the trivial |0> degeneracy
    append_parity_fold_block(qc, pauli="Z", qubits=(0,), freq_reg=freq_reg, ...)
    actual = Statevector(qc)
    expected = <hand-built 4-term superposition from R3's ground-truth table>
    assert actual.equiv(expected)

def test_reversed_pass_equals_literal_circuit_inverse():
    """R5: compiled_circuit.inverse() vs a separately built reverse-order,
    role-swapped-primitive circuit -- must be exactly equal, not just
    equivalent up to global phase, on a 2-parameter tied/interleaved case."""
    forward = compile_frequency_circuit(ir_two_parameter_tied_interleaved)
    R1 = Operator(forward.inverse())
    R2 = Operator(manually_reversed_with_swapped_primitives(ir_two_parameter_tied_interleaved))
    assert R1 == R2   # exact equality, per R5.5's finding that .equiv() alone
                       # would not have caught the copy-paste bug as sharply

def test_basis_change_x_matches_real_pauli_evolution_gate():
    """R6: the H-sandwiched X-encoding block vs Qiskit's own
    PauliEvolutionGate(SparsePauliOp('X'), time=...) at a concrete alpha."""
    alpha = 0.4123
    compiled = build_basis_changed_encoding_block(pauli="X", alpha=alpha, ...)
    real_gate = PauliEvolutionGate(SparsePauliOp("X"), time=-math.pi * alpha)  # Spec 1's own sign convention (FR-021)
    assert Operator(compiled).equiv(Operator(real_gate))

def test_flipped_ancilla_convention_would_fail_this_test():
    """Sanity check on the sign-convention test itself (mirrors Spec 1's own
    test_flipped_sign_would_fail_this_test pattern): the WRONG parity
    assignment (anc=1->increment) must NOT reproduce R3's ground-truth table."""
    ...
    assert not actual.equiv(expected)
```

Every dedicated equivalence test pairs a "this passes" assertion with a
"the wrong version would fail" sanity check, mirroring Spec 1's own
`test_ir_gate_convention.py` precedent (FR-021/SC-009) and Spec 2's Trotter
sign-verification pattern.

---

## R10. No optimisation (Constitution §5.3)

**Decision**: `compile_frequency_circuit`/`compile_observable_circuit`
construct one circuit per call and return it; no caching of compiled circuits
across calls with the same IR, no batching of multiple IRs into one
compilation pass, and no template reuse across different parameter/tie-group
structures. Each call performs the same single compilation pass regardless of
input size (Constitution §9.3 — one code path regardless of parameter count;
§5.3 — no optimisation without a recorded profile and a bottleneck, and none
exists here: this layer performs no circuit *execution*, only construction).

**Alternative considered and rejected**: caching the basis-change gate pair
per Pauli letter across repeated calls (there are only four possible letters,
so the "cache" would be trivially small) — rejected anyway, since no profiled
bottleneck justifies it and it is exactly the kind of premature optimisation
Constitution §5.3 prohibits; recomputing `(H, H)` or `(S@H, H@S†)` on each
call is O(1) regardless.
