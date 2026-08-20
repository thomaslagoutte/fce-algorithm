"""Pauli-encoded circuit intermediate representation — FR-004..FR-007, FR-021.

Holds real Qiskit objects wherever Qiskit already models the concept (a gate, an
observable) rather than a parallel gate/matrix ontology (research.md R3). Carries
the bookkeeping fields Qiskit has no native concept of — parameter_index,
coefficient, tie_group — since that is this layer's own, non-redundant contribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Union

from qiskit.circuit import Gate
from qiskit.circuit import Parameter as QiskitParameter
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.frequency import coordinate_order

_VALID_PAULI_LETTERS = frozenset("IXYZ")


@dataclass(frozen=True)
class PauliTerm:
    """One Pauli-rotation gate instance, tied to exactly one parameter index.

    `coefficient` is the real, structural scale factor multiplying the parameter in
    the rotation angle (Constitution §6.4) — never complex; the oracle's *output*
    Fourier coefficients are the ones required to be genuinely complex (FR-018), and
    are not stored here.
    """

    pauli: str
    qubits: tuple[int, ...]
    parameter_index: int
    coefficient: float
    tie_group: int

    def __post_init__(self) -> None:
        if len(self.pauli) != len(self.qubits):
            raise ValueError(
                f"PauliTerm.pauli (len {len(self.pauli)}) must have one letter per "
                f"qubits entry (len {len(self.qubits)})"
            )
        if len(set(self.qubits)) != len(self.qubits):
            raise ValueError(f"PauliTerm.qubits must be distinct, got {self.qubits}")
        if not set(self.pauli) <= _VALID_PAULI_LETTERS:
            raise ValueError(f"PauliTerm.pauli letters must be in I/X/Y/Z, got {self.pauli!r}")

    def to_gate(self, parameter: QiskitParameter) -> PauliEvolutionGate:
        """The real, exact gate this term applies — no hand-built matrix or `expm`.

        `PauliEvolutionGate(SparsePauliOp(self.pauli[::-1]), time=-math.pi *
        self.coefficient * parameter)`.

        Two load-bearing corrections, both verified in-session (§9.7), not assumed:

        - The `-math.pi` factor maps this layer's `e^{iπcαP}` encoding convention
          onto Qiskit's `PauliEvolutionGate(P, time=t) = e^{-itP}` convention.
        - `self.pauli` is reversed before constructing `SparsePauliOp`: Qiskit's
          Pauli-label convention is little-endian (the rightmost character acts on
          qubit 0), so passing `self.pauli` unreversed with `qargs=self.qubits`
          would silently act `pauli[0]` on `qubits[-1]` instead of `qubits[0]` for
          any multi-qubit term — invisible on every single-qubit test case this spec
          itself validates against.
        """
        padded = SparsePauliOp(self.pauli[::-1])
        return PauliEvolutionGate(padded, time=-math.pi * self.coefficient * parameter)


@dataclass(frozen=True)
class FixedGate:
    """A real, non-parameterised Qiskit gate — not a name resolved against a
    hand-written matrix table."""

    gate: Gate
    qubits: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.qubits) != self.gate.num_qubits:
            raise ValueError(
                f"FixedGate.qubits (len {len(self.qubits)}) must match "
                f"gate.num_qubits ({self.gate.num_qubits})"
            )
        if len(set(self.qubits)) != len(self.qubits):
            raise ValueError(f"FixedGate.qubits must be distinct, got {self.qubits}")


GateOp = Union[PauliTerm, FixedGate]


@dataclass(frozen=True)
class Parameter:
    """Read-only view over one parameter's structure."""

    index: int
    upload_count: int
    multiplicity: int
    coefficients: tuple[float, ...]


@dataclass(frozen=True)
class PauliEncodedCircuitIR:
    """A Pauli-encoded parameterised circuit plus the observable defining f(alpha)."""

    num_qubits: int
    gates: tuple[GateOp, ...]
    observable: SparsePauliOp
    _parameter_symbols_cache: dict[int, QiskitParameter] = field(
        default_factory=dict, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        for gate in self.gates:
            for q in gate.qubits:
                if not (0 <= q < self.num_qubits):
                    raise ValueError(
                        f"qubit index {q} out of range for num_qubits={self.num_qubits}"
                    )
        if self.observable.num_qubits != self.num_qubits:
            raise ValueError(
                f"observable acts on {self.observable.num_qubits} qubits, "
                f"expected {self.num_qubits}"
            )
        if self.observable != self.observable.adjoint():
            raise ValueError("observable must be Hermitian (§7.6)")
        self._validate_tying()

    def _pauli_terms(self) -> list[PauliTerm]:
        return [g for g in self.gates if isinstance(g, PauliTerm)]

    def _terms_by_index(self) -> dict[int, list[PauliTerm]]:
        result: dict[int, list[PauliTerm]] = {}
        for term in self._pauli_terms():
            result.setdefault(term.parameter_index, []).append(term)
        return result

    def _tie_groups(self, parameter_index: int) -> dict[int, list[PauliTerm]]:
        groups: dict[int, list[PauliTerm]] = {}
        for term in self._terms_by_index().get(parameter_index, []):
            groups.setdefault(term.tie_group, []).append(term)
        return groups

    def _validate_tying(self) -> None:
        for parameter_index in self._terms_by_index():
            groups = self._tie_groups(parameter_index)
            sizes = {len(terms) for terms in groups.values()}
            if len(sizes) != 1:
                raise ValueError(
                    f"parameter_index {parameter_index} has inconsistent tie-group "
                    f"sizes {sorted(sizes)} — multiplicity r_j must be uniform "
                    "across every tie_group for one parameter (§11.2, §6.3)"
                )

    def parameters(self) -> tuple[Parameter, ...]:
        indices = list(self._terms_by_index().keys())
        ordered_labels = coordinate_order([str(i) for i in indices])
        ordered_indices = [int(label) for label in ordered_labels]
        return tuple(
            Parameter(
                index=i,
                upload_count=self.upload_count(i),
                multiplicity=self.multiplicity(i),
                coefficients=self.coefficients(i),
            )
            for i in ordered_indices
        )

    def upload_count(self, parameter_index: int) -> int:
        return len(self._tie_groups(parameter_index))

    def multiplicity(self, parameter_index: int) -> int:
        groups = self._tie_groups(parameter_index)
        (size,) = {len(terms) for terms in groups.values()}
        return size

    def coefficients(self, parameter_index: int) -> tuple[float, ...]:
        return tuple(term.coefficient for term in self._terms_by_index()[parameter_index])

    @property
    def num_parameters(self) -> int:
        return len(self._terms_by_index())

    def parameter_symbols(self) -> dict[int, QiskitParameter]:
        """Exactly one real `qiskit.circuit.Parameter` per distinct
        `parameter_index`, memoized on first access. This is the structural
        enforcement of FR-005: every caller building a circuit from this IR looks up
        the shared symbol here rather than minting a fresh `Parameter` per term."""
        if not self._parameter_symbols_cache:
            for i in self._terms_by_index():
                self._parameter_symbols_cache[i] = QiskitParameter(f"alpha_{i}")
        return self._parameter_symbols_cache
