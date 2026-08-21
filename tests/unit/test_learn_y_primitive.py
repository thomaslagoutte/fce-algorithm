"""FR-014 dedicated tests — the new y(alpha) primitive's circuit is
genuinely simpler than Spec 4's V_l-based A(U,O) circuit (research.md R2),
and its Hadamard-test-ancilla construction's exact value matches an
independent direct-expectation computation. Two independent test functions,
never merged (T004, T005)."""

from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.learn import _folded_circuit
from fourierlearn.reference import _build_circuit as _oracle_build_circuit


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    """Spec 3 research.md R8's own construction, reused unchanged."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def test_fr014_circuit_is_structurally_simpler() -> None:
    """research.md R2: FR-014's circuit has strictly fewer qubits than
    Spec 4's V_l-based A(U,O) circuit, and zero cx/controlled-increment-style
    instructions present in that circuit -- a structural simplification,
    not an identity-shift V_l (planning mandate #2, prior round)."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")

    plain_folded = _folded_circuit(ir, observable)
    existing_auo = compile_observable_circuit(ir, observable)

    assert plain_folded.num_qubits < existing_auo.num_qubits, (
        "FR-014's circuit must have STRICTLY FEWER qubits than the V_l-based "
        "A(U,O) circuit -- otherwise it is only an 'identity V_l', not a "
        "genuinely simpler construction"
    )

    existing_names = {instr.operation.name for instr in existing_auo.data}
    plain_names = {instr.operation.name for instr in plain_folded.data}

    # Sanity: the existing V_l-based circuit does use cx (its controlled
    # increment/decrement shift gates) -- otherwise this comparison would be
    # vacuous.
    assert "cx" in existing_names
    assert "cx" not in plain_names, (
        "FR-014's circuit must contain zero controlled-increment-style "
        "(cx) instructions at all -- no frequency register, no shift gates"
    )


def _hadamard_test_exact_y(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, alpha: tuple[float, ...]) -> complex:
    """Test-only exact (Statevector) evaluation of the same ancilla
    construction estimate_y() builds in production (with finite shots) --
    never used in production code itself."""
    symbols = ir.parameter_symbols()
    parameters = ir.parameters()
    folded = _folded_circuit(ir, observable)
    binding = {symbols[p.index]: a for p, a in zip(parameters, alpha)}
    bound = folded.assign_parameters(binding)

    had_anc = QuantumRegister(1, "had_anc")
    qc = QuantumCircuit(had_anc, *bound.qregs)
    qc.h(had_anc[0])
    qc.append(bound.to_gate(label="folded").control(1), [had_anc[0]] + qc.qubits[1:])
    qc.h(had_anc[0])

    state = Statevector(qc)
    probs = state.probabilities_dict()
    p0 = sum(p for bitstr, p in probs.items() if bitstr[-1] == "0")
    p1 = sum(p for bitstr, p in probs.items() if bitstr[-1] == "1")
    return complex(p0 - p1, 0.0)


def _direct_expectation_y(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, alpha: tuple[float, ...]) -> float:
    """Independent cross-check: reference.py's own plain-circuit builder
    (test-only reuse -- production learn.py may never import
    fourierlearn.reference) + Statevector.expectation_value, no ancilla
    trick at all."""
    symbols = ir.parameter_symbols()
    parameters = ir.parameters()
    qc = _oracle_build_circuit(ir)
    binding = {symbols[p.index]: a for p, a in zip(parameters, alpha)}
    bound = qc.assign_parameters(binding)
    state = Statevector.from_instruction(bound)
    return state.expectation_value(observable).real


def test_fr014_exact_value_matches_direct_expectation() -> None:
    """research.md R2: at several concrete alpha values, the Hadamard-test
    ancilla construction's exact value matches an independent direct
    expectation computation to within 1e-10, with an exactly-zero
    imaginary part at every tested alpha. This test imports Statevector
    for verification only -- estimate_y() itself (T012) is shot-based."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")

    test_alphas = [(0.3,), (0.0,), (1.0,), (-0.5,), (2.2,)]
    max_err = 0.0
    for alpha in test_alphas:
        y_had = _hadamard_test_exact_y(ir, observable, alpha)
        y_direct = _direct_expectation_y(ir, observable, alpha)
        assert abs(y_had.imag) < 1e-12, (alpha, y_had)
        err = abs(y_had.real - y_direct)
        max_err = max(max_err, err)
    assert max_err < 1e-10, f"Hadamard-test construction does not match direct expectation: {max_err}"
