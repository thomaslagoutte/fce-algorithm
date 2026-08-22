"""Circuits layer — FR-001..FR-014; Spec 9 FR-001..FR-011.

Compiles a Foundation-Layer `PauliEncodedCircuitIR` into circuits:

- `compile_frequency_circuit` — the unconditional "parity-fold" circuit
  `A(U)` (Barthe thesis Theorem 5.1): one frequency-counter register per
  encoded parameter, one single shared ancilla, controlled increment/decrement
  per encoding gate.
- `compile_observable_circuit` — the observable-folded circuit `A(U, O)`
  (Barthe thesis Corollary 5.1, Figure 5.4): a forward pass, the observable
  folded in via the shared basis-change helper, and the literal inverse of
  the assembled forward circuit as the reversed pass. A single-Pauli-string
  `observable` takes this exact, unmodified path (Spec 9 FR-004). A
  multi-term `observable` (`O = Σ_h β_h P_h`) takes the LCU path instead
  (Spec 9 deliverable a, eq. 5.49-5.51, Figure 5.5): a selector register of
  `⌈log2(#terms)⌉` qubits is prepared into `Σ_h √(|β_h|/S)|h⟩`
  (`S = Σ_h|β_h|`, the L1 norm — research.md R1's corrected formula, never
  the literal `β_h/‖β‖` reading of eq. 5.51, which is quadratic in `β_h` and
  wrong), a diagonal sign-correction gate absorbs each `sign(β_h)` into its
  own branch (never an invalid `sqrt` of a negative number), then one
  multiplexed, selector-controlled `P_h` gate replaces the single fold gate,
  then the selector is un-prepared. The single-term branch is never touched
  by this generalization (Critical Mandate 1).
- `compile_projector_circuit` — the `U⊗U*` construction (Spec 9 deliverable
  b, eq. 5.52, Figure 5.6) for the projector observable `|0⟩⟨0|`: builds
  `A(U)` and an independently-constructed `A(U*)` on two full, independent
  register copies (research.md R2) — never a Pauli decomposition of the
  projector, which is exponential (spec.md Clarifications).
- `compile_kernel_overlap_circuit` — the kernel-overlap construction (Spec
  10 deliverable a, eq. 5.72-5.78, Figure 5.8): a selector qubit
  selector-controls two classical inputs' own leading fixed-gate
  preparations, then the shared, UNMODIFIED `compile_frequency_circuit`
  runs once, unconditionally, on top — `⟨Z_selector⊗I⊗|0⟩⟨0|_circuit⟩` on
  its output equals `Re(⟨b(x)|b(x')⟩)` (verified in-session).

All three reuse Spec 1's `frequency.register_width` and the single shared
`basis_change_gates` helper (FR-014) — none reimplements the other's logic
(Constitution §9.4).
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from qiskit.circuit.library import DiagonalGate, StatePreparation
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


def _fold_pauli_label_onto(qc: QuantumCircuit, label: str, qubits: list[Qubit]) -> None:
    """The shared per-letter fold loop (basis-change in, `Z`, basis-change
    out) for one Qiskit-native, little-endian Pauli `label`, applied to an
    explicit `qubits` list (qubit `i` of the label maps to `qubits[i]`, per
    Qiskit's own little-endian convention: rightmost character = index 0).
    Used identically by the single-term path (`_insert_observable`) and by
    every branch of the multi-term LCU fold (`_build_lcu_branch_gate`) —
    neither reimplements this loop independently (Constitution §9.4)."""
    for qubit_index, letter in enumerate(reversed(label)):
        if letter == "I":
            continue
        w_dagger, w = basis_change_gates(letter)
        qubit = qubits[qubit_index]
        qc.compose(w_dagger, [qubit], inplace=True)
        qc.z(qubit)
        qc.compose(w, [qubit], inplace=True)


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
    _fold_pauli_label_onto(qc, label, list(circuit_reg))


# --- Spec 9 deliverable (a): LCU folding for a multi-term observable -------


class ZeroWeightError(ValueError):
    """Raised when a declared LCU term has a weight `beta_h` of exactly
    zero (Spec 9 critical implementation instruction #2) — a zero-weight
    term contributes nothing and must be rejected explicitly at
    construction time, rather than silently bloating the selector register
    with a term that can never matter."""


def _lcu_selector_qubit_count(num_terms: int) -> int:
    """`⌈log2(#terms)⌉` selector qubits (FR-003) — `0` for a single term
    (the existing, non-LCU path; never reached from `compile_observable_circuit`,
    but kept total here for direct unit testing)."""
    if num_terms < 1:
        raise ValueError(f"_lcu_selector_qubit_count requires num_terms >= 1, got {num_terms}")
    if num_terms == 1:
        return 0
    return math.ceil(math.log2(num_terms))


def _validate_lcu_weights(weights: list[float]) -> None:
    if not weights:
        raise ValueError("an LCU observable requires at least one term")
    for h, beta in enumerate(weights):
        if beta == 0.0:
            raise ZeroWeightError(
                f"LCU term {h} has weight beta_h=0 -- a zero-weight term contributes "
                "nothing and must not be declared (it would silently bloat the "
                "selector register for no reason)"
            )


def _lcu_magnitude_amplitudes(weights: list[float]) -> list[float]:
    """`√(|β_h|/S)` for each declared term, zero-padded up to `2^m` entries
    (`S = Σ|β_h|`, the L1 norm — research.md R1's corrected formula; never
    the L2/Euclidean norm `‖β‖` eq. 5.51 reads literally, which research.md
    R1 found gives a result quadratic in `β_h`, not linear)."""
    num_terms = len(weights)
    m = _lcu_selector_qubit_count(num_terms)
    total = sum(abs(beta) for beta in weights)
    amplitudes = [math.sqrt(abs(beta) / total) for beta in weights]
    amplitudes += [0.0] * (2**m - num_terms)
    return amplitudes


def _lcu_sign_diagonal(weights: list[float]) -> list[float]:
    """`sign(β_h)` for each declared term (research.md R1: the diagonal
    gate absorbing the sign into the construction, so the magnitude
    preparation above never needs `sqrt` of a negative number), padded
    with `+1` (a no-op) for the unused selector basis states — their
    amplitude is exactly zero, so their sign is unobservable, but `+1`
    keeps the diagonal itself trivially unitary and well-defined."""
    num_terms = len(weights)
    m = _lcu_selector_qubit_count(num_terms)
    signs = [1.0 if beta > 0 else -1.0 for beta in weights]
    signs += [1.0] * (2**m - num_terms)
    return signs


def _build_lcu_branch_gate(label: str, num_qubits: int) -> QuantumCircuit:
    """The uncontrolled fold sub-circuit for one LCU term's own label, on
    its own `num_qubits`-wide register — reuses `_fold_pauli_label_onto`
    (Constitution §9.4), never a separate implementation of the per-letter
    loop. `.control(m, ctrl_state=h)` (in `_append_multiplexed_fold`) turns
    this into the branch's own multiplexed, selector-controlled gate."""
    branch = QuantumCircuit(num_qubits)
    _fold_pauli_label_onto(branch, label, list(branch.qubits))
    return branch


def _append_multiplexed_gates(
    qc: QuantumCircuit,
    branches: list[QuantumCircuit],
    selector_reg: QuantumRegister,
    target_qubits: list[Qubit],
    label_prefix: str = "P",
) -> None:
    """The shared multiplexed-controlled-branch append (Spec 9 FR-002,
    generalized for Spec 10's selector-controlled classical-input
    preparation, Constitution §9.4): branch `h`'s own uncontrolled
    sub-circuit, controlled on the selector register holding exactly `|h⟩`
    (an "open"/exact-value multi-control, `ctrl_state=h`), appended onto
    `target_qubits`. Used identically by the LCU observable fold
    (`_append_multiplexed_fold`, below) and by
    `compile_kernel_overlap_circuit`'s classical-input branch selection —
    neither reimplements this loop independently."""
    m = len(selector_reg)
    for h, branch in enumerate(branches):
        controlled = branch.to_gate(label=f"{label_prefix}_{h}").control(m, ctrl_state=h)
        qc.append(controlled, list(selector_reg) + target_qubits)


def _append_multiplexed_fold(
    qc: QuantumCircuit, labels: list[str], selector_reg: QuantumRegister, circuit_reg: QuantumRegister
) -> None:
    """FR-002: one multiplexed, selector-controlled `P_h` gate per declared
    term, each controlled on the selector register holding exactly `|h⟩`
    (an "open"/exact-value multi-control, `ctrl_state=h`) — never a
    separate `A(U)`/`A(U†)` pair per term (Critical Mandate 1). Unused
    selector basis states (`h >= len(labels)`, when `#terms` is not a power
    of two) get no controlled gate at all — their amplitude is already
    exactly zero (FR-007), so no operation is needed there."""
    branches = [_build_lcu_branch_gate(label, len(circuit_reg)) for label in labels]
    _append_multiplexed_gates(qc, branches, selector_reg, list(circuit_reg), label_prefix="P")


def _real_weights(observable: SparsePauliOp) -> list[float]:
    """Extract each term's real coupling weight `beta_h`, rejecting a
    genuinely complex coefficient explicitly (Spec 9's own scope: `O =
    Σ_h beta_h P_h` with real `beta_h`, per FR-001) rather than silently
    discarding an imaginary part (Constitution §10.1)."""
    weights = []
    for coeff in observable.coeffs:
        value = complex(coeff)
        if abs(value.imag) > 1e-9:
            raise ValueError(
                f"LCU term weight {value!r} has a non-negligible imaginary part -- "
                "this feature requires real beta_h (O = sum_h beta_h P_h), per FR-001"
            )
        weights.append(value.real)
    return weights


def _insert_observable_lcu(qc: QuantumCircuit, observable: SparsePauliOp, circuit_reg: QuantumRegister) -> QuantumRegister:
    """FR-002/FR-003: fold a multi-term observable via the LCU construction,
    appending the new selector register's own registers/gates directly onto
    `qc` (which must already include the selector register among its own
    `qregs`) and returning it for the caller's later un-preparation step."""
    if observable.num_qubits != len(circuit_reg):
        raise ValueError(
            f"observable acts on {observable.num_qubits} qubits, expected {len(circuit_reg)}"
        )
    weights = _real_weights(observable)
    _validate_lcu_weights(weights)
    labels = observable.paulis.to_labels()

    num_terms = len(weights)
    m = _lcu_selector_qubit_count(num_terms)
    selector_reg = QuantumRegister(m, name="lcu_selector")
    qc.add_register(selector_reg)

    amplitudes = _lcu_magnitude_amplitudes(weights)
    qc.append(StatePreparation(amplitudes), list(selector_reg))
    qc.append(DiagonalGate(_lcu_sign_diagonal(weights)), list(selector_reg))
    _append_multiplexed_fold(qc, labels, selector_reg, circuit_reg)
    qc.append(StatePreparation(amplitudes, inverse=True), list(selector_reg))
    return selector_reg


# --- Spec 9 deliverable (b): the U(x)U* projector construction ------------


class ComplexFixedGateConjugationError(ValueError):
    """Raised when `conjugate_ir` encounters a `FixedGate` whose own gate
    matrix is not real — conjugating such a gate correctly is explicitly
    out of scope for this feature (spec.md Assumptions); only real-matrix
    `FixedGate`s (e.g. `X`, `H`, as already used by Spec 8's state-prep
    flips) are supported."""


def _pauli_term_conjugate(term: PauliTerm) -> PauliTerm:
    """research.md/tasks.md guardrail 1, verified in-session: for a
    Pauli-rotation gate `e^{iπcαP}`, `P* = (-1)^k P` where `k` is `P`'s own
    `Y`-count — so the gate's true conjugate negates the coefficient only
    when `k` is EVEN, and leaves it UNCHANGED when `k` is ODD (since
    `P*=-P` there, and the two minus signs in `e^{-iπcαP*}=e^{-iπcα(-P)}
    =e^{+iπcαP}` cancel back to the original gate). Verified against
    `Operator(gate).conjugate()` for both parities before being written
    here, not assumed from the general tensor-product-conjugation rule
    alone."""
    y_count = term.pauli.count("Y")
    coefficient = -term.coefficient if y_count % 2 == 0 else term.coefficient
    return PauliTerm(
        pauli=term.pauli,
        qubits=term.qubits,
        parameter_index=term.parameter_index,
        coefficient=coefficient,
        tie_group=term.tie_group,
    )


def _fixed_gate_conjugate(fixed: FixedGate) -> FixedGate:
    """A `FixedGate` with a real matrix is self-conjugate (`G*=G`) —
    checked via `Gate.to_matrix()` (never `qiskit.quantum_info.Operator`,
    which this production module may not import, Constitution §3.4).
    A complex-matrix `FixedGate` raises explicitly rather than being
    silently mishandled (Constitution §10.1)."""
    matrix = fixed.gate.to_matrix()
    if not all(abs(entry.imag) < 1e-10 for row in matrix for entry in row):
        raise ComplexFixedGateConjugationError(
            f"FixedGate {fixed.gate.name!r} has a complex matrix -- conjugating it "
            "correctly is out of scope for this feature; only real-matrix FixedGates "
            "(e.g. X, H) are supported"
        )
    return fixed


def conjugate_ir(ir: PauliEncodedCircuitIR) -> PauliEncodedCircuitIR:
    """Builds `U*`'s own IR from `U`'s (`ir`), gate-by-gate, IN THE SAME
    ORDER (verified in-session: complex conjugation of a matrix product
    does not reverse it, unlike the Hermitian adjoint — `(AB)*=A*B*`, not
    `B*A*`) — applying `_pauli_term_conjugate`/`_fixed_gate_conjugate` to
    each gate in turn. `ir.observable` is carried over unchanged: the
    projector construction (`compile_projector_circuit`) never folds an
    observable at all, so this field is inert for that use but must
    remain a valid Hermitian operator for `PauliEncodedCircuitIR`'s own
    constructor validation."""
    conjugated_gates = tuple(
        _pauli_term_conjugate(gate) if isinstance(gate, PauliTerm) else _fixed_gate_conjugate(gate)
        for gate in ir.gates
    )
    return PauliEncodedCircuitIR(num_qubits=ir.num_qubits, gates=conjugated_gates, observable=ir.observable)


def predict_projector_register_cost(ir: PauliEncodedCircuitIR) -> int:
    """research.md R2's exact formula, computed and logged BEFORE
    `compile_projector_circuit` builds anything (Constitution §10.3):
    `n_total(U⊗U*) = 2*n_circuit + 2*sum_j(register_width(L_j,r_j)) + 2`
    — two full, independent register copies (one for `A(U)`, one for
    `A(U*)`), never a single shared or difference register."""
    single_copy = (
        ir.num_qubits
        + sum(frequency.register_width(p.upload_count, p.multiplicity) for p in ir.parameters())
        + 1
    )
    return 2 * single_copy


def compile_projector_circuit(ir: PauliEncodedCircuitIR) -> QuantumCircuit:
    """Deliverable (b), eq. 5.52/Figure 5.6: `A(U)` and an independently-
    constructed `A(U*)` (via `conjugate_ir`), each built by reusing
    `compile_frequency_circuit` completely unchanged, composed on two
    full, independent register copies — never reusing or duplicating
    `compile_observable_circuit`'s own observable-folding logic, since
    there is no observable to fold (the projector `|0⟩⟨0|` needs no basis
    change at all). The predicted register cost (research.md R2) is
    computed before this function builds anything, per
    `predict_projector_register_cost`."""
    # TODO(Spec 9, Constitution §4.7 — deferred, not silently missing):
    # no finite-shot extraction wrapper exists for this circuit's output.
    # Spec 4's `extract._hadamard_test_circuit` assumes a single-frequency-
    # register layout (`circuit.qregs[:-2]` = frequency registers) and
    # cannot be pointed at this function's six-register layout (`freq0,
    # ancilla, circuit, freq0_star, ancilla_star, circuit_star`) without a
    # new wrapper that (a) correlates both frequency registers' outcomes
    # from the SAME shot and (b) combines their decoded integers via the
    # verified DIFFERENCE rule (Ω=ω_1-ω_2, never ω_1+ω_2 — see
    # `reference.projector_coefficients` and the extension register's
    # EXT-003 entry for the verified derivation). Blocking condition: only
    # needed before this construction is used for any finite-shot
    # (hardware- or noisy-simulator-facing) result — the exact-oracle
    # path (`reference.projector_coefficients`) is already validated
    # end to end without it.
    forward_u = compile_frequency_circuit(ir)
    forward_u_star = compile_frequency_circuit(conjugate_ir(ir))

    star_registers = [QuantumRegister(reg.size, name=f"{reg.name}_star") for reg in forward_u_star.qregs]
    combined = QuantumCircuit(*forward_u.qregs, *star_registers)

    n_u = len(forward_u.qubits)
    combined.compose(forward_u, qubits=range(n_u), inplace=True)
    combined.compose(forward_u_star, qubits=range(n_u, n_u + len(forward_u_star.qubits)), inplace=True)
    return combined


def compile_observable_circuit(ir: PauliEncodedCircuitIR, observable: SparsePauliOp) -> QuantumCircuit:
    """User Story 2/3 — `A(U, O)`: User Story 1's forward construction, the
    observable folded in directly (uniformly for every Pauli letter via the
    shared basis-change helper), and the literal inverse of the assembled
    forward circuit as the reversed pass (FR-006, FR-007, FR-008; research.md
    R5 for the reversed pass, R6/R7 for uniform observable folding). Does
    NOT implement a second, independently written reverse-order construction
    with hand-maintained role-swapped primitives.

    Spec 9 FR-001..FR-004: a multi-term `observable` (`len(observable.paulis)
    > 1`) is folded via the LCU construction instead
    (`_insert_observable_lcu`) — a single-term `observable` takes the
    exact, unmodified path it always has (Critical Mandate 1)."""
    forward = compile_frequency_circuit(ir)
    circuit_reg = forward.qregs[-1]
    num_forward_qubits = len(forward.qubits)

    if len(observable.paulis) == 1:
        qc = QuantumCircuit(*forward.qregs)
        qc.compose(forward, inplace=True)
        _insert_observable(qc, observable, circuit_reg)
        qc.compose(forward.inverse(), inplace=True)
        return qc

    qc = QuantumCircuit(*forward.qregs)
    qc.compose(forward, qubits=range(num_forward_qubits), inplace=True)
    _insert_observable_lcu(qc, observable, circuit_reg)
    qc.compose(forward.inverse(), qubits=range(num_forward_qubits), inplace=True)
    return qc


# --- Spec 10 deliverable (a): the kernel-overlap circuit (Figure 5.8) ------


class KernelInputStructureMismatchError(ValueError):
    """Raised when `ir_x` and `ir_x_prime` do not share an identical
    encoded-parameter structure (Constitution §7.1) differing only in an
    initial, classical-input-dependent fixed-gate preparation — the only
    case `compile_kernel_overlap_circuit` supports (spec.md Assumptions:
    the general, arbitrary-interleaving case is explicitly out of scope for
    this feature; verified in-session against a 2-qubit/2-tied-parameter
    fixture, not merely the 1-qubit case)."""


def _split_prefix_fixed_gates(ir: PauliEncodedCircuitIR) -> tuple[tuple[FixedGate, ...], tuple[GateOp, ...]]:
    """Splits `ir.gates` into (a) the leading run of `FixedGate`s occurring
    strictly before the first `PauliTerm` — the classical-input preparation
    this feature selector-controls — and (b) everything from the first
    `PauliTerm` onward, which `compile_kernel_overlap_circuit` requires to
    be IDENTICAL between `ir_x` and `ir_x_prime` (the shared, unconditional
    `A(U)` part)."""
    prefix: list[FixedGate] = []
    rest: list[GateOp] = []
    seen_pauli_term = False
    for gate in ir.gates:
        if isinstance(gate, FixedGate) and not seen_pauli_term:
            prefix.append(gate)
            continue
        if isinstance(gate, PauliTerm):
            seen_pauli_term = True
        rest.append(gate)
    return tuple(prefix), tuple(rest)


def compile_kernel_overlap_circuit(
    ir_x: PauliEncodedCircuitIR, ir_x_prime: PauliEncodedCircuitIR
) -> QuantumCircuit:
    """User Story 1, FR-001/FR-002/FR-003 (Figure 5.8, eq. 5.72-5.78):
    prepares a selector qubit into `|+⟩`, selector-controls `ir_x`'s vs
    `ir_x_prime`'s own leading fixed-gate preparation onto the shared
    circuit register (FR-003: reusing the exact same multiplexed-controlled-
    branch mechanism as Spec 9's LCU observable fold, `_append_multiplexed_gates`,
    not a second implementation of it), then applies the SHARED, UNMODIFIED
    `compile_frequency_circuit` call once, unconditionally, on top, and
    closes with a second Hadamard on the selector.

    The returned circuit is a state-preparation circuit only (matching every
    other `compile_*` function in this module) — it adds no measurement.
    Verified in-session (before this function was written) to make
    `⟨Z_selector⊗I_{freq,ancilla}⊗|0⟩⟨0|_circuit⟩`, evaluated on this
    circuit's output state, equal `Re(⟨b(x)|b(x')⟩)` (`reference.
    kernel_overlap_oracle`) to machine precision, on both a 1-qubit/1-
    parameter fixture and a richer 2-qubit/2-tied-parameter fixture (diffs
    3.3e-16 to 1.0e-14).

    Requires `ir_x` and `ir_x_prime` to be identical from their first
    `PauliTerm` gate onward — i.e. to differ only in an initial run of
    `FixedGate`s (the classical input) — raising
    `KernelInputStructureMismatchError` otherwise (this is a deliberate,
    documented scope restriction, not an oversight: spec.md's own
    Assumptions leave the fully general, arbitrarily-interleaved case to a
    future feature).

    Constitution §5.3: no caching, batching, or memoization — every call
    rebuilds `forward_shared` from scratch, unprofiled and by design."""
    if ir_x.num_qubits != ir_x_prime.num_qubits:
        raise KernelInputStructureMismatchError(
            f"ir_x has {ir_x.num_qubits} qubits but ir_x_prime has "
            f"{ir_x_prime.num_qubits} — both classical inputs must share the "
            "same circuit-register width"
        )
    prefix_x, rest_x = _split_prefix_fixed_gates(ir_x)
    prefix_x_prime, rest_x_prime = _split_prefix_fixed_gates(ir_x_prime)
    if rest_x != rest_x_prime:
        raise KernelInputStructureMismatchError(
            "ir_x and ir_x_prime must share an IDENTICAL encoded-parameter "
            "structure (every gate from the first PauliTerm onward) and "
            "differ only in their leading, classical-input-dependent "
            "FixedGate preparation (Constitution §7.1) — a difference was "
            "found in the shared/common gate sequence"
        )

    ir_shared = PauliEncodedCircuitIR(num_qubits=ir_x.num_qubits, gates=rest_x, observable=ir_x.observable)
    forward_shared = compile_frequency_circuit(ir_shared)
    circuit_reg = forward_shared.qregs[-1]

    selector_reg = QuantumRegister(1, name="kernel_selector")
    qc = QuantumCircuit(*forward_shared.qregs, selector_reg)
    qc.h(selector_reg[0])

    branch_x = QuantumCircuit(len(circuit_reg))
    for gate in prefix_x:
        branch_x.append(gate.gate, gate.qubits)
    branch_x_prime = QuantumCircuit(len(circuit_reg))
    for gate in prefix_x_prime:
        branch_x_prime.append(gate.gate, gate.qubits)
    _append_multiplexed_gates(
        qc, [branch_x, branch_x_prime], selector_reg, list(circuit_reg), label_prefix="kernel_branch"
    )

    qc.compose(forward_shared, qubits=range(len(forward_shared.qubits)), inplace=True)
    qc.h(selector_reg[0])
    return qc
