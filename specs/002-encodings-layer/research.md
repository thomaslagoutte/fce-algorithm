# Phase 0 Research: Encodings Layer

Every decision below that introduces a coefficient, sign, or scaling factor was
checked computationally against the actual target unitary in this session before
being written down — per explicit instruction, none is asserted from the formula's
resemblance to a previous one. Verification code and output are summarized inline;
full sessions are reproducible from the exact snippets quoted.

---

## R1. Module layout

**Decision**: `src/fourierlearn/encodings/` package, matching the constitution's
`ir → encodings → circuits → ...` layer name (§9.1) directly rather than inventing a
different name:

- `src/fourierlearn/encodings/__init__.py`
- `src/fourierlearn/encodings/pauli_pqc.py` — User Story 1 (spec FR-001–FR-005)
- `src/fourierlearn/encodings/trotter.py` — User Story 2 (spec FR-006–FR-010),
  imports from `pauli_pqc.py`

**Rationale**: The Trotter frontend must reuse the Pauli-PQC frontend's
IR-construction logic (spec FR-009, Constitution §9.4) — putting them in the same
package with an explicit import dependency makes that reuse the only path, not an
option.

---

## R2. Pauli-PQC data model and `build_ir` (spec FR-001–FR-004)

**Decision**:

```python
@dataclass(frozen=True)
class PauliUpload:
    pauli: str
    qubits: tuple[int, ...]
    parameter_label: str   # caller's own label; mapped to a canonical integer index
    tie_group: int
    coefficient: float

def build_ir(
    num_qubits: int,
    uploads: Sequence[PauliUpload],
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR: ...
```

`build_ir` maps distinct `parameter_label` strings to canonical integer parameter
indices via `frequency.coordinate_order` (the same function Spec 1's own
`PauliEncodedCircuitIR.parameters()` uses), builds one `PauliTerm` per upload, and
delegates all structural validation (tie-group size and coefficient uniformity,
qubit bounds, observable Hermiticity) to `PauliEncodedCircuitIR`'s own constructor —
no re-validation of what Spec 1 already checks.

**Verified finding, not assumed**: Spec 1's IR does **not** raise on an empty
`gates` tuple — `_validate_tying()` iterates `self._terms_by_index()`, which is
simply empty for zero `PauliTerm`s, so the loop does nothing and construction
succeeds with zero encoded parameters. Confirmed by inspection of
`PauliEncodedCircuitIR.__post_init__`/`_validate_tying` (`src/fourierlearn/ir.py`):
neither checks `len(self.gates)`. This means **`build_ir` itself must explicitly
reject an empty `uploads` sequence** (spec FR-004) — Spec 1 does not backstop this
one, unlike the coefficient-uniformity case (research.md R6 below) where it does.

---

## R3. Trotter data model (spec FR-006)

**Decision**:

```python
@dataclass(frozen=True)
class CouplingGroupTerm:
    pauli: str
    qubits: tuple[int, ...]
    weight: float   # this term's own fixed, known structural weight

@dataclass(frozen=True)
class CouplingGroup:
    label: str                       # this group's own coupling's name, e.g. "J"
    terms: tuple[CouplingGroupTerm, ...]

def trotter_frontend(
    num_qubits: int,
    groups: Sequence[CouplingGroup],
    tau: float,
    r: int,
    observable: SparsePauliOp,
) -> PauliEncodedCircuitIR: ...
```

`tau` (evolution time) and `r` (Trotter step count) are ordinary Python arguments,
not `PauliUpload`/`PauliTerm` fields — they are fixed, known classical values used
only to *compute* each term's coefficient (R4), never encoded parameters themselves
(spec FR-006, Constitution §7.1).

---

## R4. The coefficient formula `c = -h·τ/(π·r)` — re-derived and verified, not assumed

**The user's stated formula (`c = h·τ/(π·r)`, no minus sign) was checked against the
actual target unitary and does not match.** Derivation: one first-order Lie-Trotter
step for a coupling-group term with fixed weight `h`, coupling value `α` (bound at
evaluation time), is `exp(-i·h·α·P·(τ/r))`. Spec 1's own gate convention (verified in
its own session, FR-021) is `PauliTerm.to_gate()` → `exp(+iπ·c·α·P)`. Equating:
`iπcα = -ihα(τ/r)` → `πc = -hτ/r` → `c = -hτ/(πr)`.

**Verified computationally** (concrete `h=1.0`, `τ=0.8`, `r=3`, `α=0.55`):
built `PauliEvolutionGate(SparsePauliOp('Z'), time=-π·c·α)` for both the negative-sign
candidate and the user's positive-sign candidate, compared each against
`scipy.linalg.expm(-1j·(h·α)·Z·(τ/r))` via `Operator`. Negative-sign candidate
matched exactly; positive-sign candidate did not. This is the same class of error as
Spec 1's own `PauliEvolutionGate` sign trap (FR-021) — flagged in this project's
memory of prior sessions as a recurring risk, confirmed recurring here.

**Verified to generalize to multi-qubit Pauli strings, not just single-qubit `Z`**:
repeated the check for `h=1.3` on a 2-qubit `'ZZ'` term (`τ=0.9`, `r=4`, `α=0.62`)
against `expm(-1j·h·α·(Z⊗Z)·(τ/r))` — matched exactly. The derivation is generic in
`P` (any Hermitian Pauli string, single- or multi-qubit); this confirms nothing
qubit-count-specific was silently assumed.

---

## R5. Multi-group composition within one Trotter layer — verified, not guessed

**Decision**: groups are applied **interleaved**: for each of the `r` steps, apply
every declared coupling group once, in the order the caller supplied them, then
repeat for the next step. This is the literal reading of the Lie-Trotter product
formula `(∏_k exp(-i h_k α_k P_k (τ/r)))^r` — the product over groups `k` happens
*inside* each of the `r` repetitions, not as `r` copies of group 1 followed by `r`
copies of group 2.

**Verified computationally**: built a 2-group example — Group A: single `'ZZ'` term
(qubits (0,1), weight 1.3, coupling `α_A=0.62`); Group B: single `'X'` term (qubit 0,
weight -0.7, coupling `α_B=-0.44`) — deliberately non-commuting (`ZZ` and `X` on
qubit 0 do not commute). Built the circuit as "for each of `r=4` steps: append
group A's gate, then group B's gate" and compared the resulting `Operator` against
`(exp(-i·h_B·α_B·X_0·(τ/r)) @ exp(-i·h_A·α_A·ZZ·(τ/r)))^r`
(matrix-multiplication order matching "A's unitary is applied first" = rightmost
factor) — **matched exactly**. Separately confirmed the interleaved and
"block" (`r` reps of A, then `r` reps of B) orderings give **different** unitaries
for this same non-commuting pair — proving the interleaving choice is a real,
distinguishable convention this plan is pinning, not an arbitrary detail that
wouldn't have mattered either way.

---

## R6. Within-group tied multiplicity (`r_j > 1`) — verified combined-generator behavior, plus a new commutativity check Spec 1 does not perform

**Verified**: for a coupling group with two **commuting** tied terms (`'ZZ'` and
`'XX'` on qubits (0,1), confirmed commuting via direct matrix check: both orderings
of their product give `-Y⊗Y`), same weight `h=1.1`, applying them sequentially
within each of `r=3` steps reproduces the combined-generator formula
`(exp(-i·h·α·(ZZ+XX)·(τ/r)))^r` exactly — confirming sequential application of
tied, commuting terms correctly represents "one generator, applied `r` times," not
merely "two separate generators that happen to be labeled the same."

**New finding, requiring a design decision**: Spec 1's IR does **not** check that
tied `PauliTerm`s actually commute — confirmed by direct construction: a
`PauliEncodedCircuitIR` with `'X'` and `'Z'` tied to the same `parameter_index` and
`tie_group` on the same qubit (which do **not** commute) is accepted without error.
Sequential application of non-commuting "tied" terms does **not** equal
exponentiating their sum — the whole physical justification for tying
(Constitution §11.2, "sum of commuting Pauli strings") would silently fail to hold.

This is correctly Spec 1's IR being domain-agnostic, not a Spec 1 defect: whether a
set of tied strings represents a valid physical generator is a model/physics
decision (Constitution §9.5 — "logic that changes which terms... exist because of
the model's structure... lives in the model layer"), which is exactly this
encodings layer, not the generic Foundation IR. **Decision**: both frontends (via a
shared helper in `pauli_pqc.py`, used by `trotter.py`) validate that every pair of
Pauli strings within one declared tie group commutes, and raise if not.

**Verified mechanism**: `qiskit.quantum_info.Pauli.commutes()` on same-length,
full-`num_qubits`-width Pauli labels (each term's own `pauli`/`qubits` padded with
`I` elsewhere, reversed for the little-endian convention Spec 1's `ir.py` already
uses) — confirmed correct for three cases: `X`@q0 vs. `Z`@q0 (same qubit, correctly
`False`), `X`@q0 vs. `Z`@q1 (different qubits, correctly `True`, trivially
commuting), and `ZZ`@(0,1) vs. `XX`@(0,1) (correctly `True`, matching R6's own
verified-commuting pair above). `Pauli.commutes(..., qargs=...)` was tried first and
rejected — its `qargs` semantics reinterpret the *caller's own* indices, not two
independently-sized operands against a shared external qubit map, and raised an
`IndexError` on the first mismatched-width attempt; full-width padding sidesteps this
entirely and was verified to give the same, correct answers.

---

## R7. Frontend-level validation, not reliance on Spec 1's backstop

**Decision**: `trotter_frontend` explicitly validates and raises, with a clear,
domain-specific message naming the actual problem, for every one of:

- `r <= 0`
- `tau == 0`
- a coupling group with zero terms, or no groups supplied at all
- a coupling group whose terms have non-uniform `weight`
- a coupling group whose terms do not pairwise commute (R6)

**Explicit instruction, not left implicit**: `tau == 0` makes every group's derived
coefficient `c = -h·0/(πr) = 0` exactly, which Spec 1's `PauliTerm.__post_init__`
*would* separately reject (`coefficient` must not be exactly 0) — but relying on
that alone would surface a generic "coefficient must not be 0" error from deep
inside IR construction, naming neither `tau` nor the actual mistake. The frontend
checks `tau == 0` itself, first, with a message that says evolution time must be
nonzero. **A dedicated test is required or this is not verified**:
`trotter_frontend(groups, tau=0, r=5, ...)` must be asserted to raise, directly —
not inferred from Spec 1's own, separately-scoped coefficient-zero test.

Similarly, the empty-coupling-groups and non-uniform-weight cases are validated by
the frontend itself (clear, group-naming messages) even though Spec 1's IR would
also eventually reject the resulting heterogeneous or gate-less construction —
matching the same "fail with a message that names the actual mistake" reasoning.

---

## R8. Genuinely complex validation constructions — verified, no fixed gates needed

**Finding**: neither frontend's spec (FR-011, FR-012) requires fixed-gate support,
and neither `build_ir` nor `trotter_frontend` (R2, R3) expose one — matching spec
FR-001's literal scope (parameterised Pauli strings only). This raised a question:
can a genuinely complex (nonzero real *and* imaginary non-DC coefficient) validation
case be constructed at all without a fixed symmetry-breaking gate (the mechanism
Spec 1's own two-upload case needed, FR-018)? **Verified yes, for both frontends**:

- **Pauli-PQC** (FR-011): one qubit, parameter `α` uploaded twice, untied
  (`upload_count=2`, `r_j=1`): first upload `'X'`, second upload `'Z'`, coefficient
  `1.0` for both (required uniform), observable `SparsePauliOp(['X','Y'],
  coeffs=[1,1])`. Grid `N=9` (`r_j=1, L=2`): non-DC coefficient at `l=4` is
  `-0.25-0.25j` — both parts nonzero. (A plain `X` or `Z` observable alone gives a
  *purely* imaginary result for this construction — the same structural
  degeneracy found in Spec 1's own S-gate audit; the combined `X+Y` observable is
  what breaks it, verified by direct search over single-Pauli and pairwise-sum
  observables.) The key mechanism: starting with a non-diagonal upload (`X`, not
  `Z`) already escapes the trivial `|0⟩`-eigenbasis degeneracy Spec 1 needed a fixed
  Hadamard for — no fixed gate is required here because the *first* parameterised
  gate itself is already non-diagonal.
- **Trotter** (FR-012): two qubits, two coupling groups — Group A: single `'X'`
  term (qubit 0, weight 1.0); Group B: two tied, commuting terms `'ZZ'`+`'XX'`
  (qubits (0,1), weight 1.0 each, `r_j=2`) — with `τ=0.8`, `r=2`.

**Correction made during `/speckit-implement` (2026-08-20), recorded here per
Constitution §8.4 — a negative result is documented, not quietly dropped**: the
figure originally written above (`'IX'`, `l=(0,1)`: `-0.1212+0.0467j`) was never
independently computed against the actual oracle before being drafted, and turned
out to be wrong in kind, not just value — direct computation against the real
`fourierlearn.reference.coefficients()` oracle for this exact construction showed
**every** single-Pauli-string 2-qubit observable (all 15 non-identity labels,
checked exhaustively, including every `Y`-containing one) gives a **purely real**
Fourier spectrum at every non-DC `l`, for any `r` from 1 to 3. This is not
incidental: every gate this Trotter construction applies (`'X'`, `'ZZ'`, `'XX'`) is
a real-valued matrix (no `Y` anywhere in the circuit itself), and starting from the
real state `|00>`, a standard symmetry argument shows `U(-alpha) = conj(U(alpha))`
term-by-term, hence `f(-alpha) = f(alpha)` for any real-matrix observable (forcing
real Fourier coefficients) and `f(-alpha) = -f(alpha)` for any purely-imaginary
observable (forcing purely imaginary coefficients) — a single Pauli string is
always one or the other, so no single-Pauli-string observable can ever produce a
genuinely complex coefficient for this gate set, exactly the same structural
degeneracy R8's Pauli-PQC case above already identified for a single-observable
choice, now confirmed to apply here too and exhaustively, not just for the one
label first tried.

**The fix is the same one used for the Pauli-PQC case above**: use a *combined*
observable summing a real-matrix term and a purely-imaginary-matrix term, breaking
the clean even/odd split. Searched combined pairs (one even-`Y`-count label plus
one odd-`Y`-count label, 220 genuinely-complex hits found across the combinations
tried); the pair `SparsePauliOp(['IX', 'IY'], coeffs=[1, 1])` (mirroring the
Pauli-PQC case's own `X+Y` choice, applied to qubit 0) gives, at `l=(2, 4)`:
`-0.125+0.125j` (i.e. exactly `-1/8+1/8j` to float precision, confirmed against
the oracle directly, not assumed) — both parts individually nonzero, well above
any numerical-noise threshold. This construction still exercises R5 (two groups,
composed) and R6 (Group B's tied multiplicity `r_j=2`) simultaneously, per spec
FR-012's explicit requirement; only the **observable** and the **target `l`**
changed from the original draft above, not the Hamiltonian/coupling-group
structure itself.

Exact numeric fixtures for the implementation's test files are finalized during
`/speckit-tasks`/`/speckit-implement`, consistent with how Spec 1's own plan handled
this (research.md documents the verified *existence and mechanism* of a working
construction; tasks/implementation pin the literal encoded assertion values) — this
Trotter fixture is a case in point: the mechanism (interleaved composition + tied
multiplicity) was correctly anticipated here, but the specific observable/`l` pair
was not actually checked until implementation, and was wrong until corrected above.

---

## R9. No optimisation (Constitution §5.3)

**Decision**: `build_ir`/`trotter_frontend` construct one `PauliUpload`/`PauliTerm`
sequence per call and return; there is no caching of built IR instances across
calls, no batching of multiple Hamiltonians/groups into one call, and no
parametrised-circuit-template reuse across different coupling-group structures.
Each call is independent and does the same, single pass of validation and
construction regardless of input size (Constitution §9.3 — one code path
regardless of parameter count; §5.3 — no optimisation without a recorded profile
identifying a bottleneck, and none exists at this layer, which does no circuit
execution at all — that happens only when the resulting IR is later handed to
Spec 1's oracle or a future `circuits`/`extract` layer).

**Alternatives considered and rejected**: caching `build_ir`'s parameter-label→index
mapping across repeated calls with the same labels — rejected; this layer has no
profiled bottleneck to justify it (§5.3), and it would be exactly the kind of
premature optimisation this project's own discipline prohibits.
