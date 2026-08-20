"""Circuits layer — FR-001..FR-014.

Compiles a Foundation-Layer `PauliEncodedCircuitIR` into two circuits:

- `compile_frequency_circuit` — the unconditional "parity-fold" circuit
  `A(U)` (Barthe thesis Theorem 5.1): one frequency-counter register per
  encoded parameter, one single shared ancilla, controlled increment/decrement
  per encoding gate.
- `compile_observable_circuit` — the observable-folded circuit `A(U, O)`
  (Barthe thesis Corollary 5.1, Figure 5.4): a forward pass, the observable
  folded in via the shared basis-change helper, and the literal inverse of
  the assembled forward circuit as the reversed pass.

Both reuse Spec 1's `frequency.register_width` and the single shared
`basis_change_gates` helper (FR-014) — neither reimplements the other's logic
(Constitution §9.4).
"""

from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from qiskit.quantum_info import SparsePauliOp

from fourierlearn import frequency
from fourierlearn.ir import FixedGate, GateOp, PauliEncodedCircuitIR, PauliTerm

_VALID_PAULI_LETTERS = frozenset("IXYZ")


def basis_change_gates(pauli_letter: str) -> tuple[QuantumCircuit, QuantumCircuit]:
    """The single shared basis-change helper (FR-014): given a Pauli letter,
    return `(W_dagger, W)` as 1-qubit `QuantumCircuit`s such that
    `P = W @ Z @ W_dagger` (research.md R6) — i.e. applying `W_dagger` then a
    Z-type operation then `W` correctly represents the letter's own Pauli
    operator. Used identically by encoding-gate compilation (`compile_frequency_circuit`)
    and observable folding (`compile_observable_circuit`) — neither
    reimplements this mapping independently (Constitution §9.4).
    """
    if pauli_letter not in _VALID_PAULI_LETTERS:
        raise ValueError(f"basis_change_gates requires a Pauli letter in I/X/Y/Z, got {pauli_letter!r}")
    if pauli_letter in ("I", "Z"):
        identity = QuantumCircuit(1)
        return identity, identity.copy()
    if pauli_letter == "X":
        # W_X = H (self-adjoint): H @ Z @ H == X (research.md R6)
        h = QuantumCircuit(1)
        h.h(0)
        return h, h.copy()
    # pauli_letter == "Y": W_Y = S @ H, W_Y_dagger = H @ S_dagger (research.md
    # R6 — verified computationally; three other candidate orderings were
    # tried and rejected).
    w_dagger = QuantumCircuit(1)
    w_dagger.sdg(0)
    w_dagger.h(0)
    w = QuantumCircuit(1)
    w.h(0)
    w.s(0)
    return w_dagger, w


def _increment_circuit(width: int) -> QuantumCircuit:
    """Cyclic increment (mod 2**width) on a `width`-qubit register, built as
    a standard ripple-carry sequence (verified against the explicit
    permutation matrix before use, not assumed correct by construction
    alone). Qubit 0 is the least-significant bit."""
    qc = QuantumCircuit(width)
    for k in range(width - 1, 0, -1):
        qc.mcx(list(range(k)), k)
    qc.x(0)
    return qc


def _build_registers(
    ir: PauliEncodedCircuitIR,
) -> tuple[dict[int, QuantumRegister], QuantumRegister, QuantumRegister]:
    """One frequency register per encoded parameter (sized via Spec 1's own
    `register_width` — reused, not redefined, FR-002/FR-010), one ancilla
    register shared by the whole circuit (FR-003, research.md R4), and the
    original circuit register."""
    freq_registers = {
        p.index: QuantumRegister(frequency.register_width(p.upload_count, p.multiplicity), name=f"freq{p.index}")
        for p in ir.parameters()
    }
    ancilla = QuantumRegister(1, name="ancilla")
    circuit_reg = QuantumRegister(ir.num_qubits, name="circuit")
    return freq_registers, ancilla, circuit_reg


def _active_letters_and_qubits(term: PauliTerm, circuit_reg: QuantumRegister) -> list[tuple[str, Qubit]]:
    """Pairs of (Pauli letter, circuit qubit) for a term's non-identity
    letters only — an 'I' entry contributes nothing to parity and needs no
    basis change (FR-008's "any combination of I/X/Y/Z")."""
    return [
        (letter, circuit_reg[qubit])
        for letter, qubit in zip(term.pauli, term.qubits)
        if letter != "I"
    ]


def _controlled_increment_direct(freq_reg: QuantumRegister, ancilla_qubit: Qubit, ancilla_ctrl_state: int) -> QuantumCircuit:
    """The ancilla-controlled increment, built by adding `ancilla_qubit` as
    one extra control directly on each gate of the plain ripple-carry
    increment (`_increment_circuit`), rather than wrapping the whole
    assembled sub-circuit in a further `.control()` layer. Verified
    numerically to give the identical operator to the `.control()`-wrapped
    construction, at far lower synthesis cost — `.control()` on a circuit
    that already contains multi-controlled gates triggers expensive nested
    synthesis; adding one control per gate directly does not."""
    width = len(freq_reg)
    qc = QuantumCircuit(freq_reg.size + 1)
    anc = 0
    freq = list(range(1, width + 1))
    for k in range(width - 1, 0, -1):
        controls = [anc] + freq[:k]
        # Qiskit's ctrl_state string: rightmost character = first control
        # qubit in the list (little-endian) — verified experimentally, not
        # assumed from the docstring alone.
        ctrl_state = "1" * k + str(ancilla_ctrl_state)
        qc.mcx(controls, freq[k], ctrl_state=ctrl_state)
    qc.mcx([anc], freq[0], ctrl_state=str(ancilla_ctrl_state))
    return qc


def _append_controlled_shift(qc: QuantumCircuit, freq_reg: QuantumRegister, ancilla_qubit: Qubit) -> None:
    """research.md R3's verified sign convention: ancilla=0 (even parity) ->
    increment; ancilla=1 (odd parity) -> decrement. The opposite assignment
    was tried first and rejected (research.md R3; test_flipped_ancilla_
    convention_would_fail_this_test)."""
    increment0 = _controlled_increment_direct(freq_reg, ancilla_qubit, ancilla_ctrl_state=0)
    decrement1 = _controlled_increment_direct(freq_reg, ancilla_qubit, ancilla_ctrl_state=1).inverse()
    qc.append(increment0.to_gate(label="C0-V+"), [ancilla_qubit] + list(freq_reg))
    qc.append(decrement1.to_gate(label="C1-V-"), [ancilla_qubit] + list(freq_reg))


def _append_controlled_shift_swapped(qc: QuantumCircuit, freq_reg: QuantumRegister, ancilla_qubit: Qubit) -> None:
    """The role-swapped controlled shift (ancilla=0 -> decrement, ancilla=1
    -> increment) -- exactly `_append_controlled_shift`'s own adjoint
    (research.md R5.1: `G_dagger` swaps `V+`/`V-` between the two ancilla
    branches). Used only to independently reconstruct a reversed pass for
    the dedicated equivalence test (FR-011) — never as an alternative
    implementation of the forward pass itself."""
    increment1 = _controlled_increment_direct(freq_reg, ancilla_qubit, ancilla_ctrl_state=1)
    decrement0 = _controlled_increment_direct(freq_reg, ancilla_qubit, ancilla_ctrl_state=0).inverse()
    qc.append(increment1.to_gate(label="C1-V+"), [ancilla_qubit] + list(freq_reg))
    qc.append(decrement0.to_gate(label="C0-V-"), [ancilla_qubit] + list(freq_reg))


def _append_parity_fold_block(
    qc: QuantumCircuit,
    term: PauliTerm,
    freq_reg: QuantumRegister,
    ancilla_qubit: Qubit,
    circuit_reg: QuantumRegister,
) -> None:
    """Replace one encoding gate with pure frequency-register bookkeeping
    (Barthe thesis Theorem 5.1, §5.7.3): basis-change in (per qubit, via the
    shared helper), compute parity onto the shared ancilla, controlled
    increment/decrement, uncompute parity, basis-change out. The circuit
    register itself is never rotated by this term — its own gate is entirely
    replaced, not augmented."""
    active = _active_letters_and_qubits(term, circuit_reg)

    for letter, qubit in active:
        w_dagger, _ = basis_change_gates(letter)
        qc.compose(w_dagger, [qubit], inplace=True)
    for _, qubit in active:
        qc.cx(qubit, ancilla_qubit)
    _append_controlled_shift(qc, freq_reg, ancilla_qubit)
    for _, qubit in active:
        qc.cx(qubit, ancilla_qubit)
    for letter, qubit in active:
        _, w = basis_change_gates(letter)
        qc.compose(w, [qubit], inplace=True)


def _append_parity_fold_block_swapped(
    qc: QuantumCircuit,
    term: PauliTerm,
    freq_reg: QuantumRegister,
    ancilla_qubit: Qubit,
    circuit_reg: QuantumRegister,
) -> None:
    """The adjoint of `_append_parity_fold_block` for this one term (CNOT
    chain self-adjoint and unchanged in order; the controlled shift
    role-swapped; the two basis-change halves individually adjointed and
    swapped in position). Used only to independently reconstruct a reversed
    pass for the dedicated equivalence test (research.md R5.1/R5.4) — never
    as part of `compile_frequency_circuit`/`compile_observable_circuit`
    themselves, which use the literal circuit inverse instead (FR-006)."""
    active = _active_letters_and_qubits(term, circuit_reg)

    for letter, qubit in active:
        _, w = basis_change_gates(letter)
        qc.compose(w, [qubit], inplace=True)
    for _, qubit in active:
        qc.cx(qubit, ancilla_qubit)
    _append_controlled_shift_swapped(qc, freq_reg, ancilla_qubit)
    for _, qubit in active:
        qc.cx(qubit, ancilla_qubit)
    for letter, qubit in active:
        w_dagger, _ = basis_change_gates(letter)
        qc.compose(w_dagger, [qubit], inplace=True)


def compile_frequency_circuit(ir: PauliEncodedCircuitIR) -> QuantumCircuit:
    """User Story 1 — `A(U)`: the unconditional, non-parameterized circuit
    whose state directly encodes the input circuit's raw Fourier-frequency
    decomposition (Barthe thesis Theorem 5.1). Raises on a zero-parameter IR
    (FR-009) rather than silently compiling a meaningless circuit."""
    if ir.num_parameters == 0:
        raise ValueError(
            "compile_frequency_circuit requires at least one encoded parameter — "
            "a zero-parameter IR has no frequency spectrum to reveal (FR-009)"
        )

    freq_registers, ancilla, circuit_reg = _build_registers(ir)
    parameters = ir.parameters()
    qc = QuantumCircuit(*[freq_registers[p.index] for p in parameters], ancilla, circuit_reg)

    for gate in ir.gates:
        if isinstance(gate, PauliTerm):
            _append_parity_fold_block(qc, gate, freq_registers[gate.parameter_index], ancilla[0], circuit_reg)
        elif isinstance(gate, FixedGate):
            qc.append(gate.gate, [circuit_reg[q] for q in gate.qubits])
        else:  # pragma: no cover - exhaustive by GateOp's definition
            raise TypeError(f"unknown gate type: {type(gate)!r}")
    return qc


def _insert_observable(qc: QuantumCircuit, observable: SparsePauliOp, circuit_reg: QuantumRegister) -> None:
    """Fold a single Hermitian Pauli-string observable in directly as a gate,
    routing every letter through the shared basis-change helper (FR-014)
    uniformly — including `'Z'` itself, where `W=W_dagger=I` is exactly the
    "already diagonal, no change" case — so there is no branch on "is this
    observable already Z-type" (Constitution §9.3). research.md R7 found
    this direct insertion (rather than a bespoke non-`Z`-only wrapper) is
    both correct and the uniform, no-special-case design."""
    if observable.num_qubits != len(circuit_reg):
        raise ValueError(
            f"observable acts on {observable.num_qubits} qubits, expected {len(circuit_reg)}"
        )
    (label,) = observable.paulis.to_labels()
    # Qiskit's own SparsePauliOp label is little-endian (rightmost char =
    # qubit 0) -- distinct from this project's PauliTerm convention, and
    # handled directly here since `observable` is a native SparsePauliOp.
    for qubit_index, letter in enumerate(reversed(label)):
        if letter == "I":
            continue
        w_dagger, w = basis_change_gates(letter)
        qubit = circuit_reg[qubit_index]
        qc.compose(w_dagger, [qubit], inplace=True)
        qc.z(qubit)
        qc.compose(w, [qubit], inplace=True)


def compile_observable_circuit(ir: PauliEncodedCircuitIR, observable: SparsePauliOp) -> QuantumCircuit:
    """User Story 2/3 — `A(U, O)`: User Story 1's forward construction, the
    observable folded in directly (uniformly for every Pauli letter via the
    shared basis-change helper), and the literal inverse of the assembled
    forward circuit as the reversed pass (FR-006, FR-007, FR-008; research.md
    R5 for the reversed pass, R6/R7 for uniform observable folding). Does
    NOT implement a second, independently written reverse-order construction
    with hand-maintained role-swapped primitives."""
    forward = compile_frequency_circuit(ir)
    circuit_reg = forward.qregs[-1]

    qc = QuantumCircuit(*forward.qregs)
    qc.compose(forward, inplace=True)
    _insert_observable(qc, observable, circuit_reg)
    qc.compose(forward.inverse(), inplace=True)
    return qc
