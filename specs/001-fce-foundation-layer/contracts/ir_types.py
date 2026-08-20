"""Contract: the IR value types that flow across both boundaries this spec defines.

Not a Protocol itself — these are the concrete, frozen data shapes that `Encoding`
(contracts/encoding_to_ir.py) produces and `Oracle` (contracts/ir_to_oracle.py)
consumes. See data-model.md for field-by-field validation rules; this file fixes only
the shape, for both boundaries to agree on.

This is a design contract, not the final implementation — it will be copied into
`src/fourierlearn/ir.py` during /speckit-tasks + /speckit-implement, verifying the Qiskit
`SparsePauliOp`/`PauliEvolutionGate`/`Gate` signatures in-session at that point
(Constitution §9.7).

Corrected: this IR holds real Qiskit objects wherever Qiskit already models the
concept (a gate, an observable), rather than a parallel gate/matrix ontology
(research.md R3). It still carries the bookkeeping fields Qiskit has no native
concept of — which parameter index and tie group a gate belongs to, and the real
scale factor on its rotation angle — since that is this layer's own, non-redundant
contribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from qiskit.circuit import Gate, Parameter as QiskitParameter
from qiskit.circuit.library import PauliEvolutionGate

# Qiskit's SparsePauliOp is the observable type (data-model.md: PauliEncodedCircuitIR.observable)
# and the constructor argument PauliTerm.to_gate() uses to build a real PauliEvolutionGate.
# Imported here only for the type signature; contracts.py's Oracle Protocol does not
# evaluate it — only reference.py (the quarantined oracle) does (Constitution §3.3).
from qiskit.quantum_info import SparsePauliOp


@dataclass(frozen=True)
class PauliTerm:
    """One Pauli-rotation gate instance, tied to exactly one parameter index.

    `coefficient` is the real, structural scale factor multiplying the parameter in
    the rotation angle (e.g. a Trotter-step scale, Constitution §6.4) — it is never
    complex; the oracle's *output* Fourier coefficients are the ones required to be
    genuinely complex in the validation case (spec FR-018), and are not stored here.

    `pauli`, `parameter_index`, `coefficient`, and `tie_group` are this layer's own
    bookkeeping — Qiskit has no native concept of any of them. `to_gate()` is where
    this term becomes a real Qiskit gate, rather than this class reimplementing one.
    """

    pauli: str  # e.g. "XZ" — one Pauli letter per entry in `qubits`.
    qubits: tuple[int, ...]
    parameter_index: int
    coefficient: float
    tie_group: int  # groups the `r_j` simultaneously-applied terms for one upload.

    def to_gate(self, parameter: QiskitParameter) -> PauliEvolutionGate:
        """The real, exact gate this term applies — no hand-built matrix or `expm`
        (research.md R3, R6):
        `PauliEvolutionGate(SparsePauliOp(self.pauli), time=-math.pi * self.coefficient
        * parameter)`.

        The `-math.pi` factor is load-bearing, not cosmetic (spec FR-021): this
        layer's encoding convention is `e^{iπcαP}`, while Qiskit's
        `PauliEvolutionGate(P, time=t)` implements `e^{-itP}` (verified in-session
        against the installed Qiskit version, research.md R6 — not assumed from the
        generic QML-literature `e^{+itP}` convention). Equating the two gives
        `t = -π c α`. Getting this sign wrong silently conjugates every returned
        Fourier coefficient (`l ↔ -l`) and is invisible on any real-coefficient test;
        it is caught only by the `Operator`-equivalence test spec FR-021/SC-009
        requires, comparing this method's output for a `Z`-upload against a
        hand-built rotation gate at the angle the encoding convention implies. Exact
        because a single Pauli string's exponential has no non-commuting terms to
        Trotterize."""
        ...


@dataclass(frozen=True)
class FixedGate:
    """A real, non-parameterised Qiskit gate (e.g. the FR-018 symmetry-breaking `S`
    gate — `FixedGate(SGate(), (0,))`), not a name resolved against a hand-written
    matrix table (research.md R3, correcting the original design)."""

    gate: Gate
    qubits: tuple[int, ...]


GateOp = Union[PauliTerm, FixedGate]


@dataclass(frozen=True)
class PauliEncodedCircuitIR:
    """A Pauli-encoded parameterised circuit plus the observable defining f(theta).

    Construction MUST validate (data-model.md):
      - every `qubits` index is < num_qubits, across every gate;
      - `observable` acts on exactly `num_qubits` qubits and is Hermitian;
      - for every parameter index: the tied `PauliTerm` count is evenly divisible by
        a single, uniform multiplicity `r_j` (Constitution §11.2, §6.3) — otherwise
        construction raises rather than silently accepting an inconsistent structure.
    """

    num_qubits: int
    gates: tuple[GateOp, ...]
    observable: SparsePauliOp

    # Derived accessors (never stored independently of `gates` — see data-model.md's
    # "Parameter" entity for why: storing them separately risks exactly the drift
    # Constitution §6.3's deferred aliasing regression test is meant to catch).
    def parameters(self) -> tuple["Parameter", ...]:
        """Ordered per `frequency.coordinate_order()` — see Constitution §6.1."""
        ...

    def upload_count(self, parameter_index: int) -> int:
        """`L_j` — number of times this parameter's tied block is applied."""
        ...

    def multiplicity(self, parameter_index: int) -> int:
        """`r_j` — Pauli strings tied to this one parameter index (Constitution §11.2)."""
        ...

    def coefficients(self, parameter_index: int) -> tuple[float, ...]:
        """Real per-upload coefficients for this parameter, in gate order."""
        ...

    @property
    def num_parameters(self) -> int:
        """`d` — count of distinct parameter indices; NOT a parity-dependent count
        (spec Assumptions, correcting the original derivation defect that conflated
        the FFT dimension with parity indexing)."""
        ...

    def parameter_symbols(self) -> dict[int, QiskitParameter]:
        """Exactly one real `qiskit.circuit.Parameter` per distinct `parameter_index`,
        built once and memoized. This is the structural enforcement of FR-005: every
        caller building a circuit from this IR (the oracle; later, the `circuits`
        layer) MUST look up the shared symbol here for a term's `parameter_index`
        rather than minting a fresh `Parameter` per `PauliTerm` — doing the latter
        silently unties the parameter, turning a `d`-dimensional circuit into a
        `Σ_j r_j·L_j`-dimensional one. Tying is a property of the IR, not a
        convention each caller must independently get right."""
        ...


@dataclass(frozen=True)
class Parameter:
    """Read-only view over one parameter's structure — see data-model.md."""

    index: int
    upload_count: int
    multiplicity: int
    coefficients: tuple[float, ...]
