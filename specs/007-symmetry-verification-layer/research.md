# Phase 0 Research: Symmetry Verification Layer

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1 — The Vacuous Truth Test (mandate #1, executed)

**Question**: can a `SymmetryDeclaration`'s generator representation
(`qiskit.quantum_info.SparsePauliOp`) even represent a generator that
depends on the classical input `alpha`? If not, FR-001's "internal" check
would be a runtime check that always trivially passes — which must be
documented as a type-level guarantee, not shipped as a live check.

**Executed** (three attempts against the actual `SparsePauliOp` API, not a
hypothetical):

```
=== Attempt 1: embed a symbolic (Parameter) coefficient into a SparsePauliOp ===
Result: SparsePauliOp(['X'], coeffs=[<qiskit._accelerate.circuit.ParameterExpression ...>])
coeffs dtype: object
contains a ParameterExpression: True
```

**Finding — the opposite of the hypothesis**: `SparsePauliOp`'s own
constructor does **not** reject a symbolic (`qiskit.circuit.Parameter`)
coefficient. A generator whose coefficient is a `ParameterExpression` is a
legitimate, constructible `SparsePauliOp` — the representation this
feature will use for generators does **not** structurally guarantee
classical-input independence. FR-001's "internal" check is therefore
**not vacuous** and must be a real, executable runtime check, not a
documented type-level guarantee.

**Executed, the resulting real check**:

```
=== Attempt 2: the real, non-vacuous check this finding requires ===
is_classical_input_independent(SparsePauliOp('X')) = True
is_classical_input_independent(SparsePauliOp('X', coeffs=[alpha])) = False
```

`is_classical_input_independent(generator) := not any(isinstance(c, ParameterExpression) for c in generator.coeffs)`
correctly distinguishes both cases — confirmed by execution, not merely
defined.

**A second, independent gate** (Attempt 3, executed): a plain Python
callable "standing in" for an alpha-dependent generator (a function
`alpha -> Pauli string`) is rejected earlier, by `isinstance(candidate,
SparsePauliOp)`, before R1's own coefficient check would ever run — two
complementary gates, not one doing double duty.

**Constraint on `/speckit-tasks`**: FR-001's implementation MUST include
`is_classical_input_independent` (or an equivalently-named function) as an
actual runtime check with its own dedicated test reproducing both Attempt
1 and Attempt 2's cases — this MUST NOT be simplified away into a
docstring claiming a type-level guarantee, since R1 proved that guarantee
does not hold.

## R2 — Gauss law positive control (mandate #2, executed)

**Fixture**: a 3-vertex path lattice `v0 - v1 - v2`, gauge qubits on the
two links `e01` (qubit 0) and `e12` (qubit 1). Standard Z₂ lattice gauge
theory (Wegner-type) conventions: the Gauss law generator at vertex `v` is
`G_v = product of X over every link incident to v`; the gauge-field
kinetic ("dynamics") term is one `X_e` per link. **Citation-verification
flag (Constitution §2.2/§2.5)**: this exact Pauli-letter convention (`X`
for the Gauss law and kinetic term) is recorded here from standard
Kogut-Susskind-type Z₂ gauge theory, but has not yet been checked in-session
against a specific cited reference in `docs/references/` — this MUST be
verified against a named source before `/speckit-tasks` relies on it as
more than a structural example, per the Assumptions section's own note.

**Executed**:

```
=== Gauss law generators (site-indexed -- genuinely different per vertex) ===
G_v0 = IX
G_v1 = XX
G_v2 = XI

--- 'internal' check (classical-input independence) ---
G_v0: internal = True
G_v1: internal = True
G_v2: internal = True

--- 'Abelian' check (pairwise commutation among Gauss law generators) ---
G_v0 vs G_v1: commute = True
G_v1 vs G_v2: commute = True
G_v0 vs G_v2: commute = True

--- 'non-annihilating' check (Gauss law vs. H_g) ---
G_v0 vs H_g terms: non-annihilating = True
G_v1 vs H_g terms: non-annihilating = True
G_v2 vs H_g terms: non-annihilating = True

=== Gauss law: PASSES all three §11.1 conditions (internal, Abelian, non-annihilating) ===
```

Three genuinely different generators (`IX`, `XX`, `XI` — confirmed
unequal, not merely assumed), each independently confirmed internal
(despite being site-indexed, resolving the 2026-08-21 correction directly)
and pairwise commuting, and each confirmed to commute with every declared
`H_g` term. This is the concrete, executed proof spec.md's Acceptance
Scenario 2/SC-003 require, not a restatement of the definition.

## R3 — Z-twirl negative control against `H_g` (mandate #3, executed)

**Construction**: the naive, physically-wrong candidate symmetry that
substitutes `Z` for `X` at each vertex (`Z_twirl_v = product of Z over
every link incident to v`) — recreating the exact failure mode
Constitution §11.1(b)'s rationale names, on the same fixture as R2.

**Executed**:

```
=== Mandate #3: Z-twirl negative control (must FAIL non-annihilating against H_g) ===
Z_twirl_v0 = IZ
internal = True  (expected True -- still a fixed operator)
non-annihilating = False
FAILING TERM: IX (H_g's X_e01 term)

=== Z-TWIRL NEGATIVE CONTROL VERIFIED: correctly flagged as annihilating H_g's dynamics ===
(anticommutes with the IX term specifically -- Z and X on the same link/qubit)

Sanity: the Z-twirl generators still pairwise commute (Abelian: PASS) and are each a fixed,
classical-input-independent operator (internal: PASS) -- this negative control isolates
the non-annihilating failure specifically, not a confound of several failures at once.
```

The mechanism is exactly what Constitution §11.1(b) names: `Z_twirl_v0`
(`IZ`) anticommutes with `H_g`'s `IX` term (`Z` and `X` on the same
link/qubit always anticommute) — symmetrizing by this candidate would
annihilate that gauge-field kinetic term, "freezing the link." The sanity
check (Z-twirl still passes internal and Abelian) confirms this negative
control isolates the non-annihilating failure specifically — a caller
cannot dismiss the rejection as some other, unrelated problem with the
candidate.

**Pitfall found and fixed during this research**: `Pauli.commutes()`
returns a `numpy.bool_`, not a Python `bool` — an initial draft of this
script asserted `result is True`, which fails for `numpy.bool_(True)`
despite being truthy (`numpy.bool_(True) is True` is `False` — a distinct
object identity, common numpy gotcha). Fixed by comparing with `==`
instead of `is`. **Constraint on `/speckit-tasks`**: implementation code
and its tests MUST compare `.commutes()`'s return value with `==` (or
`bool(...)`), never `is True`/`is False`.

## R4 — Module architecture and the classical validation hook

**Decision**: one new module, `src/fourierlearn/symmetry.py`, exposing
`verify_symmetry(generators: tuple[SparsePauliOp, ...], hamiltonian_terms: tuple[SparsePauliOp, ...]) -> SymmetryVerificationResult`
— pure Pauli algebra only (R1-R3's checks), no `QuantumCircuit`,
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` import
anywhere. This module needs **no** CI-guard exception at all (unlike Spec
6's `_exact_dynamics.py`) — it is fully compliant with the existing,
unmodified blanket rule.

**`SymmetryDeclaration` extension (FR-012)**: Spec 6's
`src/fourierlearn/models.py` gains one new, defaulted field:
`generators: tuple[SparsePauliOp, ...] = ()` on `SymmetryDeclaration` —
additive; every existing call site in Spec 6's own test suite (which
constructs `SymmetryDeclaration(name=..., description=...)` with no
`generators`) continues to construct a valid object unchanged.

**Classical validation hook (FR-010, User Story 2)**: `build_tfim_model`
(Spec 6) is the one, single place a `symmetry` is ever attached to a
model. When `symmetry.generators` is non-empty, `build_tfim_model` calls
`symmetry.verify_symmetry(...)` against the Hamiltonian term list it is
already constructing (the same `CouplingGroup`/`CouplingGroupTerm` data
this function already builds — reused directly, not re-derived), and
raises before returning `PhysicalModelDescription` if verification fails.
Since `build_tfim_model` never itself invokes any circuit-compilation
module, this ordering trivially satisfies "before any circuit compilation"
— there is no compilation step in this function's own call graph to race
against.

## R5 — Optimisation discipline (Constitution §5.3)

**Decision**: no caching, batching, or memoization anywhere in this
design. `verify_symmetry` performs `O(G + G*T + G^2)` pairwise
Pauli-algebra checks for `G` generators and `T` Hamiltonian terms — all
small, fixed-size inputs for this spec's own scope (a handful of
generators/terms per model), with no repeated-call pattern to profile.
