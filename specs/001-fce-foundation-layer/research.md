# Phase 0 Research: FCE Foundation Layer

Each entry resolves one technology choice or open design question from the Technical
Context. Constitution §9.7 requires verifying current API signatures in-session rather
than from memory; where a Qiskit/numpy signature is load-bearing below, it was checked
against the installed versions (see R2) in this session. Constitution §2.5 requires
source verification against `docs/references/` rather than an "unverified" marker;
where a claim about Barthe's construction or its equivariant extension is load-bearing
(R8, R12), it was checked in-session against `docs/references/Barthe_thesis.pdf` and
`docs/references/equivariant FCE Z2LGT report.pdf`, cited by file, page, and
equation/definition number.

---

## R1. Project layout and build backend

**Decision**: `src/`-layout single package, `src/fourierlearn/`, built with `hatchling` via
`pyproject.toml` (no `setup.py`).

**Rationale**: `src/`-layout prevents accidentally importing the package from the
repository root instead of the installed artifact — a common source of import-guard
false negatives (a stray `import fourierlearn` picking up the wrong path could make FR-014's CI
check pass or fail for the wrong reason). `hatchling` needs no boilerplate beyond
`pyproject.toml`'s `[build-system]` table for a single pure-Python package.

**Alternatives considered**: Flat layout (`fourierlearn/` at repo root) — rejected, since it
makes `import fourierlearn` resolvable from the repo root without installing, which would let
the CI import-guard test (or any test) accidentally exercise an uninstalled tree and
mask packaging errors. `setuptools` with `setup.py` — rejected as unnecessary
boilerplate for a single pure-Python package with no compiled extensions.

---

## R2. Version pinning (FR-019, §9.7, §8.5)

**Decision**: Pin `python = ">=3.12,<3.13"`, `qiskit==2.3.1`, `qiskit-aer==0.17.2`,
`numpy==1.26.4` in `pyproject.toml`. These are the exact versions verified installed
and importable in this session (`python3 --version` → 3.12.2; `pip3 show qiskit` →
2.3.1; `pip3 show qiskit-aer` → 0.17.2; `numpy.__version__` → 1.26.4).

**Dependency-floor check (re-verified this session, not assumed)**: the concern was
whether Qiskit 2.3.1 forces a `numpy` 2.x floor that `numpy==1.26.4` would violate.
Checked directly via `importlib.metadata.distribution(...).requires` and
`packaging.requirements.Requirement`:

```text
qiskit 2.3.1      -> requires numpy<3,>=1.21   -> satisfied by 1.26.4: True
qiskit-aer 0.17.2 -> requires numpy>=1.16.3    -> satisfied by 1.26.4: True
```

Neither declares a `numpy` 2.x floor; `numpy==1.26.4` is a valid pin for both as
installed. No version change was needed as a result of this check.

**Rationale**: §9.7 requires pinning the Qiskit/Aer versions a plan relies on,
verifying signatures in-session rather than trusting memory, and — per this
correction — verifying declared dependency constraints in-session rather than
assuming compatibility. Recording the exact installed versions now means this
layer's dependency-version check (FR-019, scoped down — see R11) has real, checked
values from day one rather than placeholders.

**Alternatives considered**: Open version ranges (e.g. `qiskit>=2.0`) — rejected;
Qiskit's `quantum_info` surface has changed across majors before, and an open range
would let CI silently pick up a future version whose `Statevector`/`Operator`/
`SparsePauliOp` signatures were never verified (§9.7, §2.2). A `numpy>=2.0` pin —
considered because Qiskit's own newer releases sometimes recommend it — rejected
once the check above showed neither installed dependency requires it; pinning ahead
of an actual requirement would be an unverified, unmotivated version bump.

---

## R3. IR representation: real Qiskit `Gate` objects, not a parallel gate ontology

**Decision (corrected)**: The IR (`src/fourierlearn/ir.py`) is a set of frozen
`dataclasses` — `PauliTerm`, `FixedGate`, `PauliEncodedCircuitIR` — but they hold
**real Qiskit objects** for anything Qiskit already models, rather than reinventing
one: `FixedGate.gate` is an actual `qiskit.circuit.Gate` instance (e.g. `SGate()`),
and `PauliTerm` exposes a `to_gate(parameter: Parameter) -> PauliEvolutionGate`
method that builds the real `qiskit.circuit.library.PauliEvolutionGate` for that
term (`PauliEvolutionGate(SparsePauliOp(self.pauli), time=-math.pi * self.coefficient
* parameter)` — see R6 for why the `-math.pi` factor is there, verified in-session
against the installed Qiskit version rather than assumed), rather than the IR
carrying its own matrix/gate-name resolution table. The dataclasses *do* still carry fields Qiskit itself has no concept of —
`parameter_index`, `coefficient`, `tie_group` — because these are this layer's own
bookkeeping (which of our parameter indices a gate is tied to, and with what
multiplicity), not a reimplementation of anything Qiskit provides.

**This corrects the original R3**, which claimed the IR should be
"Qiskit-independent" and resolve `FixedGate` via a `name: str` looked up against a
hand-written matrix table in `reference.py`. That was exactly the "parallel gate
representation" this correction rejects: Qiskit already has an exact, verified
`SGate`, `HGate`, etc., and an exact, verified `PauliEvolutionGate` for a single
Pauli string's rotation (no Trotter error, since a single term's exponential has no
non-commuting pieces to approximate) — reimplementing either is pure risk with no
benefit, in a package whose entire premise is *being* a Qiskit package.

**Rationale**: This is a Qiskit package (constitution preamble: "a shot-based
Qiskit package"); the pipeline order `ir → encodings → circuits → ...` (§9.1) means
`ir` is still the shared vocabulary the `encodings` layer instantiates, but "shared
vocabulary" does not require reinventing Qiskit's own gate/operator types — it only
requires the extra per-parameter bookkeeping those types don't carry. Holding real
`Gate` objects also means `mypy` checks the IR against Qiskit's actual, current
type stubs rather than a hand-maintained shadow of them.

**Alternatives considered**: The original "pure stdlib types only" design (rejected,
per this correction, as reinventing gate representation). Wrapping the *entire*
circuit as a single pre-bound `QuantumCircuit` with Qiskit `Parameter` objects
instead of a `PauliTerm`/`FixedGate` sequence — considered, and partially adopted:
R6 below does build one shared, `Parameter`-bound `QuantumCircuit` from the IR's
gate sequence once per instance (not once per grid point). The IR itself still
keeps the `PauliTerm`/`FixedGate` sequence, rather than being *only* a
`QuantumCircuit`, because the per-parameter bookkeeping (`upload_count`,
`multiplicity`, `coefficients` — data-model.md's `Parameter` entity) has no Qiskit-
native home to live in otherwise.

**Correction (task-planning review): parameter sharing must be structural, not a
caller convention.** `PauliTerm.to_gate()` accepts an externally-supplied `Parameter`
by design (R6 needs to bind it per grid point), but that design left an open question
— *which* `Parameter` object does a caller pass for two `PauliTerm`s that share one
`parameter_index`? An implementation that minted a fresh `Parameter` per term would
silently untie every parameter, turning a `d`-dimensional circuit into a
`Σ_j r_j·L_j`-dimensional one — precisely what FR-005 prohibits, and invisible in any
diagnostic short of noticing the coefficient count is wrong. Fixed by adding
`PauliEncodedCircuitIR.parameter_symbols() -> dict[int, Parameter]` (data-model.md),
memoizing exactly one `Parameter` per distinct index, so R6's oracle (and any later
`circuits`-layer spec) looks up the shared symbol rather than independently
reimplementing the tying rule.

---

## R4. Contracts module scope and extension point (FR-001, FR-002)

**Decision**: `src/fourierlearn/contracts.py` defines exactly two `typing.Protocol` classes:
`Encoding` (produces a `PauliEncodedCircuitIR` from whatever configuration a concrete
encoding needs) and `Oracle` (consumes a `PauliEncodedCircuitIR` and an observable,
returns Fourier coefficients). Both are `@runtime_checkable`. A module-level docstring
states the extension point: later specs add new `Protocol` classes to this same module
for their own boundary (e.g. `Circuits -> Extract`), and must not modify `Encoding` or
`Oracle`'s signatures to do so.

**Rationale**: Directly implements spec FR-001/FR-002's narrowing — defining
Protocols only for the boundaries this spec crosses avoids guessing at the interface
of layers (`circuits`, `extract`, `backends`, `learn`, `models`, `experiment`) that
have not been designed yet, which would risk an interface later specs would need to
break (churn the exact thing §9.2 is meant to prevent).

**Alternatives considered**: Defining stub Protocols for all eight pipeline layers now
(matching the original, pre-correction FR-001) — rejected per the spec's own §9.2-
driven correction: an undesigned Protocol is worse than no Protocol, since the first
real layer to implement it would likely need to change its signature, defeating the
appeal to `runtime_checkable` "interchangeable by configuration" stability.

---

## R5. Frequency convention module internals (FR-008, FR-009, FR-010)

**Decision**: `src/fourierlearn/frequency.py` exposes, as its complete public surface:

- `PRE_PARITY_RANGE(r_j: int, L: int) -> range` — returns `range(-2*r_j*L, 2*r_j*L+1)`,
  the pre-parity integer domain `l ∈ {-2L, ..., 2L}^{\text{(per axis, scaled by } r_j)}`.
- `to_post_parity(l: int) -> int` and `to_pre_parity(m: int) -> int` — the explicit,
  named `l -> l/2` transform and its inverse; `to_post_parity` raises on odd `l` rather
  than silently truncating (§10.1 — no plausible wrong answer on a degenerate input).
- `decode_twos_complement(bits: Sequence[int]) -> int` — two's-complement decoding.
- `coordinate_order(labels: Sequence[str]) -> tuple[str, ...]` — the one canonical
  ordering of frequency-vector coordinates.
- `register_width(uploads: int, r_j: int) -> int` — one named function, unit-tested
  directly against hand-computed values (FR-010); the *behavioral* aliasing regression
  test against a real, under-sized register is deferred to Spec 3 per the TODO already
  recorded in spec.md's Assumptions.
- Sign convention is documented, not a runtime function: `l = Λ - Λ'` (§ FR-008),
  where `Λ`/`Λ'` are the even/odd-parity occupation counts a later encodings-layer
  spec will define concretely; this module fixes only the resulting integer's sign and
  range, which is all a foundation layer can pin before that layer exists.

**Rationale**: Directly implements the pinned convention from spec FR-008, keeping
sign, parity transform, decoding, and ordering each a separate, independently testable
function so that Constitution §6.1's "every function consuming or producing a
frequency states its convention" is satisfied by construction — a caller only ever
imports these functions rather than re-deriving them.

**Alternatives considered**: Folding `register_width` into the IR module — rejected;
§6.3 requires it be "one named function" reachable independently of any specific IR
instance, since Spec 3's later regression test needs to call it directly against
hand-chosen `(uploads, r_j)` pairs, not through a constructed circuit.

---

## R6. Reference oracle simulation strategy (FR-011, FR-012) — corrected, split

**Scope correction**: Spec 1's oracle computes exactly one thing — the *circuit*
Fourier coefficients of `f(α) = ⟨0|U†(α) O U(α)|0⟩` for a finite gate sequence
(Barthe's Definition 2.4 / the Z2LGT report's Definition 5.1, §3.1 — see R8). It
does **not** simulate continuous-time Hamiltonian dynamics, and so has no legitimate
use for `expm` or a dense Hamiltonian matrix at all. The original R6 reached for
`scipy.linalg.expm` and a hand-built dense unitary out of habit ("`reference.py` is
allowed to use it"), not because this oracle needs it — that was the defect this
correction fixes.

**Decision**: `reference.py` builds **one** `qiskit.circuit.QuantumCircuit` per IR
instance (not per grid point), obtaining its parameter symbols via
**`ir.parameter_symbols()`** — never an ad hoc, independently-built dict. For each
`PauliTerm`, it appends `term.to_gate(symbols[term.parameter_index])` — the exact
`PauliEvolutionGate(SparsePauliOp(term.pauli), time=-math.pi * term.coefficient *
parameter)` from R3 — to `term.qubits`; for each `FixedGate`, it appends `fixed.gate`
(already a real Qiskit `Gate`, R3) to `fixed.qubits`. Per grid point `α`, it calls
`bound = qc.assign_parameters({symbols[j]: alpha[j] for j in symbols})`, then
`Statevector.from_instruction(bound)`, then
`state.expectation_value(circuit.observable).real`. `Operator` and `expm` are not
imported by this oracle at all. **Using `ir.parameter_symbols()` here — rather than
the oracle building its own `{index: Parameter(...)}` mapping locally — is load-
bearing, not stylistic**: it is the only way two `PauliTerm`s tied to the same
`parameter_index` are guaranteed to bind to the *identical* `Parameter` object (see
R3's parameter-sharing correction); an oracle-local dict that happened to get this
right would still leave any later `circuits`-layer spec free to get it wrong
independently.

**Sign convention correction — verified in-session, not assumed (§9.7)**: An earlier
draft of `to_gate()` used `time=term.coefficient * parameter` directly, silently
assuming `PauliEvolutionGate(P, time=t)` implements `e^{+itP}`. Checked directly this
session (`Operator` of a one-qubit circuit containing
`PauliEvolutionGate(SparsePauliOp('Z'), time=0.37)`, compared against
`scipy.linalg.expm(-1j*0.37*Z)` and `expm(+1j*0.37*Z)`): it matches `exp(-itP)`
exactly, not `exp(+itP)`. Since this layer's encoding convention is `e^{iπcαP}`
(Barthe Definition 2.4 / Z2LGT report eq. 7, R8), the correct mapping is
`t = -π c α`, verified end-to-end this session by binding a `Parameter`-valued
`time = -math.pi * c * alpha` and confirming, via `Operator`, that the resulting
gate equals `expm(iπcαP)` for a concrete `(c, α)` — not just the unparameterised
case. **Getting this sign wrong silently conjugates every returned coefficient
(`l ↔ -l`)**, which is undetectable on any real-valued (single-upload) test and is
exactly the failure mode spec FR-021/SC-009 requires a dedicated `Operator.equiv`
test to catch, independent of any coefficient-level comparison. This is the same
class of sign error that broke the "template_binding" work in the predecessor
repository — worth a standing reminder in `tasks.md`, not just a one-time fix, since
every future spec that constructs a `PauliEvolutionGate`-style gate from an encoding
convention (`circuits`, and again in any later re-derivation) reintroduces the same
risk if it doesn't re-verify the sign against the installed Qiskit version.

**Forward reference (Spec 6 — Experiment)**: `expm` and dense-Hamiltonian
construction are for *exact continuous-time dynamics* — e.g. computing training
labels by exactly evolving under a physical Hamiltonian `H` for a real time `t`
(`expm(-1j * H * t)`), which is a Spec 6 (Experiment) concern once an actual
Hamiltonian and a learning target exist (constitution §7.2, §8.1 — approximation
error against exact dynamics). Constitution §3.3/§3.4 still permit `expm`/`Operator`
inside `reference.py` generally; this spec's own oracle simply has no use for them,
and Spec 6's use of them, when it arrives, MUST live in `reference.py` too, not a
new quarantine module.

**Rationale**: Using `Statevector` alone, over a circuit built from real,
already-exact Qiskit primitives (R3), keeps the oracle's unitary exact by
construction with no synthesis or decomposition choice to defend, and with nothing
for the CI import guard (FR-014) to ever flag even hypothetically, since the oracle
touches only the one symbol (`Statevector`) that has no production-path meaning
outside exact simulation.

**Alternatives considered**: The original expm/dense-matrix approach — rejected,
per this correction, as unnecessary complexity solving a problem (continuous-time
evolution) this oracle does not have. `qiskit.circuit.library.PauliEvolutionGate`
plus circuit transpilation for the *whole* circuit — rejected specifically for
*transpilation*: the un-transpiled `PauliEvolutionGate`/`Gate` sequence is already
exact for a single-term-per-gate circuit (no Trotter error, since each gate is one
exponential of one Pauli string, not a sum), so transpiling before `Statevector`
evaluation would introduce a synthesis dependency with no accuracy benefit.

---

## R7. Nyquist grid construction and FFT normalization (FR-011, FR-020, FR-022)

**Decision**: Per parameter `j`, the grid has `N_j = 4 r_j L_j + 1` points (pre-parity,
per spec FR-011/Assumptions and directly sourced in R12 from the Z2LGT report §5.3),
evenly spaced over the **full** period-`2/coefficient` domain (e.g. `α_j ∈ [0, 2/c)`),
now definitively resolved to be period **2** in `coefficient·α` — not `2π`, and not a
domain of fixed length 2 regardless of `coefficient` (see R8, and the correction
below).

**Correction (2026-08-20 audit, ahead of Spec 2): the domain must be rescaled by
`1/coefficient`, not fixed at length 2.** The original version of this decision
sampled a fixed `α ∈ [0, 2)` domain unconditionally. That is only correct when
`coefficient = 1` for every term of the parameter — `to_gate()` applies the physical
rotation angle `-π·coefficient·α` (R3, R6), so the circuit's true periodicity in `α`
is `2/coefficient`, not `2`. Verified numerically: `coefficient=0.37` on a single,
untied term (no tying involved at all) already produced results disagreeing with an
independent, much finer (`N=2001`) reference computation of the same circuit — the
fixed-domain grid was silently aliasing. Rescaling the sampled domain to
`2/coefficient` (same point count `N_j`) was confirmed, for both a positive and a
negative coefficient, to reproduce exactly the `coefficient=1` answer at the same
raw integer `l`. This is what makes `coefficient` usable as a genuine physical scale
(§6.4's "Trotter-step" example) rather than merely documented but broken for any
value besides 1 — required for Spec 2's Trotter frontend, whose coefficients
(`c_k = -h_k/(πL)`) are essentially never 1. `PauliEncodedCircuitIR` now requires
`coefficient` to be uniform (and nonzero) across every term of one parameter
(FR-007 amendment) precisely because this rescaling is per-parameter, not per-term —
a heterogeneous parameter has no single rescaling that avoids aliasing. The oracle evaluates `f`
on the full outer-product grid (`numpy.meshgrid` / direct nested evaluation), applies
`numpy.fft.fftn` over all `d` axes at once, and divides by the total point count
`prod(N_j)` to convert the raw DFT sum into Fourier series coefficients, then reads
off the coefficient at each integer frequency `l` via `frequency.dft_frequencies()`
(added to frequency.py per the task-planning correction below) — **not** an inline
`fftfreq`/`fftshift` computation in `reference.py` itself.

**Correction (task-planning review): the bin-to-`l` mapping belongs in `frequency.py`,
not inlined here.** The original draft of this decision described converting DFT bin
index to signed `l` directly inside `reference.py`. That is exactly the kind of
frequency-indexing decision FR-009 requires live in the single convention module —
an inline `fftfreq`-style computation in the oracle is one more place a sign could
silently flip (alongside FR-021's `PauliEvolutionGate` sign), and would be invisible
to anyone auditing `frequency.py` for "every frequency-producing/consuming function."
Fixed by adding `frequency.dft_frequencies(num_points)` (contracts/frequency_convention.md),
which the oracle now calls instead.

**Domain choice: full period-2 grid, not the half-domain parity would justify
(FR-020)**: Eq. 13 (Barthe thesis / Z2LGT report §3.2, R8) proves every admissible
pre-parity `l` is even — meaning `f` actually has period **1**, not 2, and a grid over
`α_j ∈ [0, 1)` with the same `4 r_j L_j + 1` point count would resolve exactly the
same admissible coefficients at half the evaluation cost. **This was considered and
rejected**: sampling only `[0, 1)` would make every odd-`l` slot structurally
unobservable — the grid would never contain the information needed to tell "this
coefficient is exactly zero" apart from "this coefficient was never sampled." That
bakes the parity theorem in as an unverified premise of the oracle's own construction,
exactly backwards from Constitution §4.3 ("every agreement test also asserts the
quantity under test is non-trivial... a test that would pass on a degenerate input is
a defect") — here the failure mode is the mirror image: a test that *cannot fail*
because it never measures the thing being claimed. Sampling the full `[0, 2)` domain
keeps every odd-`l` slot live in the DFT output, so `tests/oracle/test_reference_oracle.py`
can assert those slots are zero to floating-point precision as a real, falsifiable
check (spec FR-020/SC-008) — independently validating the mechanism behind the
`2^{-d}` sparsity factor the Z2LGT report's abstract claims (§11.7), rather than
assuming it. This doubles the grid's point count at this layer's scale, which is
cheap enough here to be worth the independent verification.

**Rationale**: This is the literal Nyquist-grid-evaluation-plus-d-dimensional-FFT
oracle spec FR-011 requires; `numpy.fft.fftn`'s dimension order matches the axis order
of the input array, so passing axes in `frequency.coordinate_order()`'s canonical order
keeps grid axis order and reported-coefficient axis order consistent by construction —
this is the "coordinate ordering" §6.1 requires, and is a different ordering concern
from Qiskit's own little-endian qubit-index convention used inside R6, which this
research explicitly does not conflate with it.

**Alternatives considered**: A direct (non-FFT) discrete Fourier sum — rejected; the
spec explicitly requires an FFT-based oracle (deliverable (d)), and `numpy.fft.fftn` is
the direct, verified stdlib-adjacent tool for it. The half-domain (`[0,1)`, period-1)
grid — rejected per the domain-choice discussion above; it is cheaper but makes the
parity claim untestable rather than tested.

---

## R8. Rotation-angle period — resolved in-session against docs/references/ (§2.5)

**Decision (definitive, sourced)**: Each parameter's native domain is `α_j ∈ [0,1]`
and its rotation angle is `π α_j` (not `2π α_j`, not `α_j` in radians directly); the
resulting function `f(α)` has period **2** in `α_j` — not `2π`. The oracle's grid
(R7) spans one full period of length 2 per axis (e.g. `α_j ∈ [0, 2)` or `[-1, 1)`),
subdivided into `N_j = 4 r_j L_j + 1` points, exactly as R7 already specified.

**Source verification (Constitution §2.5 — checked in-session against
`docs/references/`, not asserted from memory)**:

- `docs/references/Barthe_thesis.pdf`, **Definition 2.4** ("Pauli encoding", p. 20,
  extracted page 31): a Pauli-encoded circuit's parameterised gates are
  `V_l(x) := e^{iπ P_l x_{i_l}}`, `x ∈ [0,1]^D`. **Eq. (2.29)–(2.30)** (p. 20–21,
  extracted pages 31–32): the resulting function is
  `f(x) = Σ_{l ∈ [-2L,2L]^D} b_l e^{iπ x·l}` — an explicit `e^{iπ x l}` phase, integer
  `l`, confirming period 2 in `x` (`e^{iπ(x+2)l} = e^{iπxl}·e^{i2πl} = e^{iπxl}` for
  integer `l`; period `2π` would require the phase to be `e^{ixl}`, which it is not).
- `docs/references/equivariant FCE Z2LGT report.pdf`, **§3.1** ("Pauli encoding
  (Definition 5.1)", extracted page 7), **eq. (7)**: `V_{s,j}(α) = e^{iπ P_{s,j} α_j}`,
  the same `π α_j` convention, generalised to `L` re-uploads (`s = 1,...,L`) and (§5.2,
  extracted page 12) multiplicity `r_j` tied gates per parameter. **§3.2 derivation**,
  **eq. (8)–(13)** (extracted pages 7–8): the accumulated frequency
  `Λ_j = Σ_s ϵ_{s,j} ∈ {-L,...,L}` and the net frequency `l = Λ - Λ'` give
  `f_x(α) = Σ_l b_l(x) e^{iπ l·α}` (eq. 12) — the identical `e^{iπ l·α}` phase,
  confirming the period-2 convention carries over unchanged to the multiplicity-`r_j`
  generalisation this spec's IR represents.
- **§5.3** ("Register sizing", extracted pages 12–13) gives, per coordinate: ambient
  ("frequency register") width `⌈log2(4 r_j L + 1)⌉` and the admissible-value count
  `4 r_j L + 1` (pre-parity) — this is the exact source of the grid-size formula R7
  and spec FR-011 already use, and of `register_width` in R12 below.

**This closes the action item the previous revision of this document left open.**
The period is 2, in `α`'s own native units (the units Barthe's `x ∈ [0,1]^D` and the
Z2LGT report's `α ∈ [0,1]^d` already use) — **not** `2π` radians. A design that
samples the grid over a `2π` interval (treating `α` as if it were already a radian
angle) would be wrong: it would double the effective period and alias every
coefficient. This is why R7's `N_j = 4 r_j L_j + 1` formula must be paired with a
period-2 (not period-`2π`) grid, and why this correction was load-bearing rather
than cosmetic.

**Alternatives considered**: `4π` period (possible for a half-integer-spin generator
convention with an extra factor of 1/2 in the exponent) — ruled out directly by
Definition 2.4 and eq. (7)'s literal `e^{iπPα}` (no factor of 1/2 anywhere in the
generator's exponent); `2π` (the generic QML-literature convention for an
`RZ(θ)`-style gate) — ruled out because Barthe's own gate is defined as `e^{iπPα}`,
not `e^{iθP/2}`, so the generic convention does not apply here.

---

## R9. CI import guard mechanism (FR-014, FR-015)

**Decision**: `tests/ci/test_no_forbidden_imports.py` walks `src/fourierlearn/*.py` using the
stdlib `ast` module (`ast.parse` + `ast.walk` over `Import`/`ImportFrom` nodes),
collects every imported name, and asserts none of `Statevector`, `Operator`, `expm`,
or `fourierlearn.reference` are imported by any file other than `src/fourierlearn/reference.py`. Because
this is a pytest test, any CI runner that executes `pytest` fails the build on a
violation — satisfying FR-014 without coupling the guard's existence to a specific CI
vendor (spec Assumptions). `.github/workflows/ci.yml` runs `pytest` (and `mypy`) on
every push, since deliverable (e) explicitly asks for a CI check and none exists yet.

**Rationale**: An AST-based static scan can never itself execute (or need to import)
`Statevector`/`Operator`/`expm`, so the guard cannot accidentally trip its own
prohibition — a runtime `sys.modules` inspection approach would risk exactly that if
any transitively-imported production module pulled in Aer for unrelated reasons.

**Alternatives considered**: A `flake8`/`ruff` custom lint rule — rejected as
heavier tooling than a ~30-line AST walk needs for a single, stable check; a pre-commit
hook alone — rejected as insufficient by itself, since §3.4 requires *CI* to fail the
build, not just a local hook a developer could skip.

---

## R10. Type checking for the contracts module (SC-001)

**Decision**: `mypy` (strict mode: `disallow_untyped_defs`, `disallow_any_generics`)
runs in CI over `src/fourierlearn/`, checking that concrete `Encoding`/`Oracle` implementations
satisfy their Protocols structurally.

**Rationale**: Spec SC-001 and the Assumptions section both require "typed Protocols"
to mean something checkable, not just documentation; `mypy` is the standard tool for
structural Protocol conformance in Python and needs no additional runtime dependency
beyond a dev-only install.

**Alternatives considered**: `pyright` — comparable capability, rejected only for
being a Node-based toolchain in an otherwise pure-Python dev environment; runtime
`isinstance` checks alone via `@runtime_checkable` — kept as a *complement* (useful in
tests), not a replacement, since `runtime_checkable` only checks method presence, not
signature correctness.

---

## R11. Dependency-version check — scoped down; full manifest deferred to Spec 6

**Scope correction**: The previous revision of this document scaffolded a general
`fourierlearn.manifest.current()` mechanism here. That overbuilds this layer: a run
manifest (§8.5) exists to sit *beside a reportable experimental output* — hardware,
timings, seeds, config — and this foundation layer produces no such output. All it
actually needs is confirmation that the environment it runs in matches its own pin.

**Decision (scoped)**: `tests/unit/test_dependency_versions.py` reads the declared
`qiskit`/`qiskit-aer` pins from `pyproject.toml` itself at test time (not duplicated
as separate hardcoded literals in the test — see the correction below) and asserts
the installed `qiskit.__version__`/`qiskit_aer.__version__` match that pin exactly;
separately asserts the installed `numpy.__version__` satisfies the ranges verified in
R2 (`numpy<3,>=1.21` and `numpy>=1.16.3`) — read from the actually-imported modules,
not hardcoded expectations of what `pip` installed. No `manifest.py` module, no
`current()` function, no hardware/timings/seed fields ship in this spec.

**Correction (task-planning review): don't duplicate the pin as a second hardcoded
literal.** The original draft of this decision had the test assert
`qiskit.__version__ == "2.3.1"` directly — a version string duplicated between
`pyproject.toml` (the actual pin) and the test file. That duplication is exactly what
makes a version-pin test brittle in practice: a deliberate upgrade requires editing
both, and the test becomes the one someone comments out the first time it blocks an
intentional bump. Reading the pin from `pyproject.toml` (via `tomllib` +
`packaging.requirements.Requirement`) keeps FR-019's "verify... matches that pin"
check meaningful with a single source of truth: upgrading is a one-line
`pyproject.toml` edit, and the test automatically checks against the new pin without
needing a matching edit anywhere else.

**Forward reference (Spec 6 — Experiment)**: Full run-manifest scaffolding —
recording hardware, timings, seeds, and config beside an actual experimental result
(§8.5) — is deferred to Spec 6, the first layer with a reportable output to attach
one to (see the TODO in spec.md's Assumptions, mirroring the register-width
aliasing deferral to Spec 3). That spec's manifest MUST still report the same
`qiskit`/`qiskit_aer`/`numpy`/`python` versions this layer pins, read the same way
(live `__version__` attributes, never a duplicated hardcoded string), so the two
are consistent when Spec 6 arrives rather than needing to be reconciled then.

**Rationale**: Matches FR-019 as scoped down (spec.md, this revision) — a
dependency-version check, not a manifest. Building the general mechanism now, before
any layer produces an experimental result, would be exactly the kind of premature
abstraction the constitution's own discipline (§9.4, "never duplicated call paths")
and this project's "don't add it until something needs it" norm argue against.

**Alternatives considered**: The original general manifest scaffold — rejected per
this correction as overbuilt for this layer. A static YAML/JSON file recording the
pin — still rejected as a Spec 6 concern, not this layer's, for the same reason as
before: it would go stale the moment a dependency changes without a live check.

---

## R12. `register_width` formula and its unit-test table (FR-010) — directly sourced

**Decision**: `register_width(uploads: int, r_j: int) -> int` returns
`ceil(log2(4 * r_j * uploads + 1))` — the number of bits needed to address the
pre-parity frequency range `{-2 r_j \cdot \text{uploads}, ..., 2 r_j \cdot
\text{uploads}\}` in two's-complement. Its unit tests cover, at minimum:
`(uploads=1, r_j=1)`, `(uploads=2, r_j=1)`, `(uploads=1, r_j=2)`, and one case where
`r_j > 1` and `uploads > 1` together, each checked against a hand-computed width.

**Source verification (§2.5)**: This is not an inferred formula — it is
`docs/references/equivariant FCE Z2LGT report.pdf`, **§5.3** ("Register sizing",
extracted page 13), stated directly: *"Frequency register width per coordinate:
`⌈log2(4 r_j L + 1)⌉`"*, with *"Barthe's `⌈log2(2L + 1)⌉` [state-register width] is
the case `r_j = 1`"* given as the un-tied special case. The same section's warning
is the exact failure mode Spec 3's deferred aliasing regression test (§6.3) targets
verbatim: *"If the hopping sub-registers are given Barthe's default width
`⌈log2(2L + 1)⌉`, the counter wraps around modulo the register size and the
extracted coefficients are aliased sums — silently wrong, with no error flag."*

**Rationale**: Implementing the literal sourced formula, rather than re-deriving an
equivalent one, keeps this function citable at the exact section a reviewer would
check it against, per Constitution §2.1/§2.5.

**Alternatives considered**: A fixed, pre-allocated register width regardless of
`r_j`/`uploads` — this is precisely the aliasing failure the source itself warns
against by name (quoted above), not a hypothetical this spec invented. A
`ceil(log2(4*r_j*uploads + 2))` variant — proposed during task-planning review on the
theory that two's-complement's asymmetric range (one extra negative value) means the
symmetric range `{-M,...,M}` needs `2M+2` addressable states, not `2M+1` — **checked
computationally and rejected**: `N = 4*r_j*uploads+1` is always odd (since
`4*r_j*uploads` is even), and an odd integer greater than 1 is never itself a power of
two, so "the smallest power of two ≥ N" and "the smallest power of two ≥ N+1" are
identical in every case. Verified exhaustively for `r_j*uploads` from 1 to 1999
against a brute-force minimal-two's-complement-width computation: zero mismatches,
and the `+1` formula matches the brute-force result exactly in every case, the `+2`
variant is numerically identical to it in every case, and both match the source's own
formula. No input exists that would discriminate between the two forms, so none was
added to the test table (T008, tasks.md) — what T008/T009 add instead is a
degenerate-input guard (`register_width(0, r_j)` and `register_width(uploads, 0)`
raise `ValueError`, §10.1), which is the real gap a naive implementation could have
had.
