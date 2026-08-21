"""Symmetry Verification Layer — FR-001..FR-009: algebraically verify a
declared symmetry against Constitution §11.1's three conditions
(internal, non-annihilating, Abelian), using only Pauli-string algebra
(`qiskit.quantum_info.SparsePauliOp`/`Pauli.commutes()`) — no
`QuantumCircuit` is ever constructed, and no `Statevector`, `Operator`,
`expm`, or `fourierlearn.reference` is imported anywhere in this module
(confirmed by the existing, unmodified CI import guard — no exemption
needed, research.md R4).

**"Internal" (§11.1(a))**: research.md R1's executed Vacuous Truth Test
found that `SparsePauliOp` legitimately accepts a symbolic
(`qiskit.circuit.ParameterExpression`) coefficient — so classical-input
independence is a genuine, non-vacuous runtime check, not a type-level
guarantee. It is emphatically **not** a requirement that a generator act
uniformly across sites: a site-indexed generator (e.g. the `Z₂` Gauss law
`G_v`, declared once per lattice vertex with genuinely different Pauli
content at each vertex) is exactly as internal as a uniform one, provided
its own content does not vary with the classical input (Clarifications,
2026-08-21; research.md R2's executed Gauss law positive control).

**NumPy bool trap (research.md R3)**: `Pauli.commutes()` returns a
`numpy.bool_`, and `numpy.bool_(True) is True` is `False` despite being
truthy. Every commutation result in this module is compared with `==`/
`bool(...)`, never `is True`/`is False`.
"""

from __future__ import annotations

from dataclasses import dataclass

from qiskit.circuit import ParameterExpression
from qiskit.quantum_info import Pauli, SparsePauliOp


class DegenerateSymmetryError(ValueError):
    """Raised when a symmetry declaration is degenerate (FR-008): zero
    generators, or a generator equal to the identity operator. Neither
    asserts any actual structure, and accepting either would let a
    meaningless declaration pass silently."""


class QubitCountMismatchError(ValueError):
    """Raised when a generator and the Hamiltonian term list are declared
    over different numbers of qubits (FR-009) — checked before any of
    §11.1's three substantive conditions."""


class MultiTermPauliError(ValueError):
    """Raised when a declared generator or Hamiltonian term is a
    multi-term `SparsePauliOp` (a linear combination of more than one
    Pauli string). Multi-term Pauli observables / LCUs are currently out
    of scope for this feature — allowing one through would silently
    check only its first term (`.paulis[0]`) against the rest of the
    declaration, an unannounced partial check rather than a real one."""


def _single_pauli(op: SparsePauliOp) -> Pauli:
    """Extract the one Pauli string a generator/Hamiltonian term must be —
    raising, not silently truncating to `.paulis[0]`, if `op` actually
    carries more than one term."""
    if len(op.paulis) != 1:
        raise MultiTermPauliError(
            "Multi-term Pauli observables / LCUs are currently out of scope for "
            f"the Symmetry Verification Layer — got {len(op.paulis)} terms in {op!r}"
        )
    return op.paulis[0]


def is_classical_input_independent(generator: SparsePauliOp) -> bool:
    """FR-001 (research.md R1): a generator is "internal" only if none of
    its coefficients are symbolic. This is a genuine runtime check — a
    `SparsePauliOp` legitimately accepts a `ParameterExpression`
    coefficient, so this can and does fail on a legitimately constructed
    input, not only on something structurally impossible."""
    _single_pauli(generator)  # reject a multi-term generator here too
    return not any(isinstance(c, ParameterExpression) for c in generator.coeffs)


def _is_identity(generator: SparsePauliOp, num_qubits: int) -> bool:
    """Robust identity check: compares the Pauli string's own label
    directly, never `SparsePauliOp` object equality — `==` also compares
    the coefficient, so a trivial (identity) generator carrying a
    non-unit coefficient (e.g. `SparsePauliOp('II', coeffs=[2.0])`) would
    otherwise silently NOT be flagged as degenerate, since it is not
    `==`-equal to `SparsePauliOp('II')` despite being the identity
    operator up to that scalar."""
    pauli = _single_pauli(generator)
    return str(pauli) == "I" * num_qubits


def _check_non_annihilating(
    generators: tuple[SparsePauliOp, ...], hamiltonian_terms: tuple[SparsePauliOp, ...]
) -> tuple[bool, SparsePauliOp | None]:
    """FR-002: every generator MUST commute with every Hamiltonian term.
    Returns (passed, first_failing_term)."""
    for generator in generators:
        generator_pauli = _single_pauli(generator)
        for term in hamiltonian_terms:
            term_pauli = _single_pauli(term)
            if not bool(generator_pauli.commutes(term_pauli)):
                return False, term
    return True, None


def _check_abelian(
    generators: tuple[SparsePauliOp, ...],
) -> tuple[bool, tuple[SparsePauliOp, SparsePauliOp] | None]:
    """FR-003: every pair of generators MUST pairwise commute. Returns
    (passed, first_non_commuting_pair)."""
    for i in range(len(generators)):
        pauli_i = _single_pauli(generators[i])
        for j in range(i + 1, len(generators)):
            pauli_j = _single_pauli(generators[j])
            if not bool(pauli_i.commutes(pauli_j)):
                return False, (generators[i], generators[j])
    return True, None


@dataclass(frozen=True)
class SymmetryVerificationResult:
    """FR-006/FR-007: every one of §11.1's three conditions' individual
    outcome, plus (on any failure) the specific offending term or
    generator pair — never a bare "invalid symmetry" with no further
    detail."""

    accepted: bool
    internal: bool
    non_annihilating: bool
    abelian: bool
    failing_term: SparsePauliOp | None = None
    non_commuting_pair: tuple[SparsePauliOp, SparsePauliOp] | None = None
    failure_reason: str | None = None


def verify_symmetry(
    generators: tuple[SparsePauliOp, ...],
    hamiltonian_terms: tuple[SparsePauliOp, ...],
) -> SymmetryVerificationResult:
    """FR-001..FR-007: verify a declared symmetry (`generators`) against a
    Hamiltonian's own declared term list, purely algebraically. Runs ALL
    three §11.1 checks unconditionally — never short-circuiting on the
    first failure (FR-006) — and reports every one of them.

    Raises `DegenerateSymmetryError` for zero generators or an
    identity-operator generator (FR-008), and `QubitCountMismatchError`
    for a generator/Hamiltonian-term qubit-count mismatch (FR-009) —
    both checked before any of the three substantive conditions.

    **Generic Architecture (FR-005)**: this function takes only
    `(generators, hamiltonian_terms)` — no model-identifying parameter
    exists for a branch to key on.
    """
    if not generators:
        raise DegenerateSymmetryError("verify_symmetry requires at least one generator, got zero")

    num_qubits = generators[0].num_qubits
    for generator in generators:
        if generator.num_qubits != num_qubits:
            raise QubitCountMismatchError(
                f"generators declared over inconsistent qubit counts: "
                f"{num_qubits} vs. {generator.num_qubits}"
            )
        generator_pauli = _single_pauli(generator)
        if _is_identity(generator, num_qubits):
            raise DegenerateSymmetryError(
                f"generator {generator_pauli.to_label()!r} is the identity operator — "
                "a trivial, no-op 'symmetry' asserts no structure"
            )
    for term in hamiltonian_terms:
        if term.num_qubits != num_qubits:
            raise QubitCountMismatchError(
                f"a Hamiltonian term is declared over {term.num_qubits} qubits, "
                f"but the generator(s) are declared over {num_qubits}"
            )
        _single_pauli(term)

    internal = all(is_classical_input_independent(g) for g in generators)
    non_annihilating, failing_term = _check_non_annihilating(generators, hamiltonian_terms)
    abelian, non_commuting_pair = _check_abelian(generators)

    accepted = internal and non_annihilating and abelian
    failure_reasons = []
    if not internal:
        failure_reasons.append("internal")
    if not non_annihilating:
        failure_reasons.append("non-annihilating")
    if not abelian:
        failure_reasons.append("Abelian")

    return SymmetryVerificationResult(
        accepted=accepted,
        internal=internal,
        non_annihilating=non_annihilating,
        abelian=abelian,
        failing_term=failing_term,
        non_commuting_pair=non_commuting_pair,
        failure_reason=", ".join(failure_reasons) if failure_reasons else None,
    )
