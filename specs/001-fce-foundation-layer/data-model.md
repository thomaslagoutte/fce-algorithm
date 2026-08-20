# Phase 1 Data Model: FCE Foundation Layer

Entities below live in `src/fourierlearn/ir.py` unless noted. All are immutable
(`@dataclass(frozen=True)`) — the IR is a value type; nothing here mutates in place,
consistent with §9.3's "per-parameter structure is data, not control flow."

---

## Parameter

Derived, not stored directly — `PauliEncodedCircuitIR` exposes it as a read-only view
over the gate sequence, so upload count and multiplicity can never drift out of sync
with the gates that actually define them (the exact failure mode §6.3's regression
test, deferred to Spec 3, will probe).

| Field | Type | Meaning |
|---|---|---|
| `index` | `int` | The parameter's position, `j`, in coordinate order (§ frequency.coordinate_order). |
| `upload_count` | `int` (`L_j`, ≥ 1) | Number of times this parameter's tied Pauli-rotation block is applied (e.g. Trotter steps). |
| `multiplicity` | `int` (`r_j`, ≥ 1) | Number of Pauli strings tied to this one parameter index within a single application of its block (§11.2). |
| `coefficients` | `tuple[float, ...]` | One real coefficient `c` per `PauliTerm` tied to this parameter, in gate order — length `upload_count * multiplicity`. |

**Validation rules**:
- `upload_count = (# PauliTerm with this index) / multiplicity`; constructing a
  `PauliEncodedCircuitIR` where this is not an integer (i.e. multiplicity does not
  evenly divide the tied term count) is a detectable, rejected invalid state (spec
  Edge Cases — must not silently accept an inconsistent structure).
- `multiplicity` for a given index MUST be the same across every group of
  simultaneously-applied `PauliTerm`s sharing that index (§11.2 — one parameter, one
  multiplicity; a design where tied strings could carry different multiplicities is
  rejected by construction, not merely by convention).

---

## PauliTerm

A single Pauli-rotation gate instance in the circuit's gate sequence. Holds this
layer's own bookkeeping (`parameter_index`, `coefficient`, `tie_group` — none of
which Qiskit has a native concept of) plus enough to produce a **real** Qiskit gate
on demand, rather than a parallel gate/matrix representation (research.md R3,
correcting the original "Qiskit-independent IR" design).

| Field | Type | Meaning |
|---|---|---|
| `pauli` | `str` | Pauli letters (`I`/`X`/`Y`/`Z`), one per entry in `qubits`, e.g. `"XZ"` — the constructor argument for the real `SparsePauliOp`/`PauliEvolutionGate` this term produces. |
| `qubits` | `tuple[int, ...]` | Qubit indices this Pauli string acts on (same length as `pauli`). |
| `parameter_index` | `int` | Which `Parameter` (by `index`) this term's rotation angle is tied to — this layer's bookkeeping, not a Qiskit-native field. |
| `coefficient` | `float` | Real scalar `c` multiplying the parameter in the rotation angle (`angle = c * α_{j}`, e.g. a Trotter-step scale, §6.4). |
| `tie_group` | `int` | Which simultaneous application of the tied block this term belongs to — all `PauliTerm`s sharing one `(parameter_index, tie_group)` pair are the `r_j` strings applied together in one of that parameter's `upload_count` repetitions. |

**Method**: `to_gate(parameter: qiskit.circuit.Parameter) -> PauliEvolutionGate` —
returns the real, exact `qiskit.circuit.library.PauliEvolutionGate(SparsePauliOp(self.pauli),
time=-math.pi * self.coefficient * parameter)` (research.md R3, R6; spec FR-021). This
is the gate the oracle (and, later, the `circuits` layer) actually appends to a
`QuantumCircuit` — there is no separate, hand-maintained unitary-construction path.
The `-math.pi` factor maps this layer's `e^{iπcαP}` encoding convention onto Qiskit's
`PauliEvolutionGate(P, time=t) = e^{-itP}` convention (verified in-session against the
installed Qiskit version, not assumed — research.md R6); an inverted sign here
silently conjugates every returned Fourier coefficient (`l ↔ -l`), invisibly on any
real-coefficient test, which is why FR-021/SC-009 require a dedicated
`Operator`-equivalence test for this method independent of any coefficient-level check.

**Validation rules**:
- `len(pauli) == len(qubits)`, all `qubits` distinct, `pauli` characters in
  `{"I","X","Y","Z"}`.
- `coefficient` is real (not complex) — see research.md R6/spec FR-004: the IR's
  per-parameter coefficient is a circuit-structural scale factor, distinct from the
  oracle's output Fourier coefficients, which are genuinely complex by construction in
  the validation case (FR-018) but are never stored in the IR itself.
- `to_gate()`'s sign mapping is covered by `tests/unit/test_ir_gate_convention.py`
  (spec FR-021/SC-009), not merely by the oracle's coefficient-level validation tests.

---

## FixedGate

A structural, non-parameterised gate — e.g. the symmetry-breaking `S` gate FR-018
requires between two `Z`-rotation uploads of the same parameter in the two-upload
validation circuit.

| Field | Type | Meaning |
|---|---|---|
| `gate` | `qiskit.circuit.Gate` | A real Qiskit gate instance, e.g. `SGate()` — not a name resolved against a hand-written matrix table (research.md R3, correcting the original design). |
| `qubits` | `tuple[int, ...]` | Qubit indices this gate acts on. |

**Validation rules**: `len(qubits) == gate.num_qubits`; construction relies on
Qiskit's own `Gate` type to guarantee the gate is a valid, exact unitary — this layer
adds no separate correctness claim about `gate` itself.

---

## PauliEncodedCircuitIR

The top-level IR instance — one Pauli-encoded parameterised circuit, plus the fixed
observable whose expectation value is the function being Fourier-analyzed.

| Field | Type | Meaning |
|---|---|---|
| `num_qubits` | `int` | Circuit width. |
| `gates` | `tuple[PauliTerm \| FixedGate, ...]` | The ordered gate sequence defining the circuit. The oracle (research.md R6) builds one real `QuantumCircuit` from this sequence — one `Parameter` per distinct `parameter_index`, `term.to_gate(parameter)` appended for each `PauliTerm`, `fixed.gate` appended for each `FixedGate` — rather than evaluating the IR in the abstract. Order matters both for that evaluation and, separately, for whether a non-contiguous tied block would violate §11.10 in a later, gate-reordering spec (not a concern for this foundation layer, which never reorders gates). |
| `observable` | `SparsePauliOp` (Qiskit type) | The Hermitian observable whose expectation value, as a function of all parameters, is what the oracle Fourier-analyzes. Assumed diagonal-in-computational-basis or general Hermitian — either way, Hermiticity is asserted at construction (§7.6 — the conjugate-symmetry shortcut is valid only for a Hermitian observable, and this IR is exactly where that assumption must be checked once, at the source). |

**Derived accessors** (computed from `gates`, never stored separately, so they cannot
drift out of sync — see Parameter above):

- `parameters() -> tuple[Parameter, ...]` — in `frequency.coordinate_order()`'s
  canonical order.
- `upload_count(parameter_index: int) -> int`
- `multiplicity(parameter_index: int) -> int`
- `coefficients(parameter_index: int) -> tuple[float, ...]`
- `num_parameters -> int` — `d`, the FFT dimension (research.md R7); the count of
  distinct `parameter_index` values, **not** a parity-dependent count (spec
  Assumptions — corrected to decouple `d` from parity indexing).
- `parameter_symbols() -> dict[int, qiskit.circuit.Parameter]` — exactly one real
  Qiskit `Parameter` per distinct `parameter_index`, built once and memoized on first
  access. This is the structural enforcement of FR-005's "MUST NOT permit... independent
  parameters": every caller that builds a circuit from this IR (this spec's oracle,
  and any later `circuits`-layer spec) looks up the shared symbol for a term's
  `parameter_index` here rather than minting a fresh `Parameter` per term — which
  would silently untie the parameter and turn a `d`-dimensional circuit into a
  `Σ_j r_j·L_j`-dimensional one. Tying is a property of the IR, not a convention each
  caller must independently get right.

**Validation rules** (checked once, at construction, so every consumer gets a
guaranteed-consistent instance rather than re-validating):

- Every `qubits` entry across every gate is `< num_qubits`.
- `observable` acts on exactly `num_qubits` qubits and is Hermitian
  (`SparsePauliOp.equiv(observable.adjoint())` — the specific isinstance/Hermiticity
  check is verified against the installed Qiskit API at implementation time, per
  §9.7).
- The `Parameter` consistency rules above (upload count divides evenly, multiplicity
  uniform per index).

---

## Contracts (`src/fourierlearn/contracts.py`)

Not data entities but the typed boundaries consuming/producing the above (see
`contracts/` for the literal Protocol signatures):

- **`Encoding`** (`Encoding -> IR` boundary): a `Protocol` with one method producing a
  `PauliEncodedCircuitIR` from whatever configuration a concrete encoding needs. This
  spec defines the Protocol only — no concrete `Encoding` implementation ships here
  (that begins with the `encodings` layer's own, later spec).
- **`Oracle`** (`IR -> Oracle` boundary): a `Protocol` with one method mapping a
  `PauliEncodedCircuitIR` to its Fourier coefficients, indexed by integer frequency
  tuple `l ∈ ℤ^d` (pre-parity, per frequency.py's pinned convention). `reference.py`'s
  concrete oracle is the one implementation this spec ships.

## Frequency convention (`src/fourierlearn/frequency.py`)

Not an entity with instances — a fixed set of module-level functions (research.md R5)
that every other entity's accessors and the oracle's coefficient indexing must import
rather than reimplement (§6.1). This includes `dft_frequencies(num_points)` — the
FFT-bin-index-to-signed-`l` mapping the oracle's FFT/indexing step uses (research.md
R7) — which lives here rather than being inlined in `reference.py`, for the same
reason `coordinate_order` does: it is exactly the kind of frequency-indexing decision
FR-009 requires be defined once and imported, not re-derived per call site.

## Dependency version check (`tests/unit/test_dependency_versions.py`)

Not a shipped entity — a test-only check, scoped down from a full run-manifest
mechanism (research.md R11, correcting the original design). It reads
`qiskit.__version__`, `qiskit_aer.__version__`, and `numpy.__version__` live and
asserts they match this layer's pin (`pyproject.toml`) and the compatibility ranges
verified in research.md R2. No `manifest.py` module or persisted record ships in this
spec; full run-manifest scaffolding (hardware, timings, seeds, config beside a
reportable output, §8.5) is deferred to Spec 6 per the TODO in spec.md's Assumptions.
