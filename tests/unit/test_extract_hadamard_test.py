"""Dedicated Hadamard-test equivalence tests for the Extract Layer — FR-003,
FR-006, FR-010 (research.md R2, R3, R4).

R3 (exact-limit oracle match), R4 (conjugate symmetry on the estimator's OWN
output), and the fixture's own non-degeneracy are each their own test
function, per explicit instruction — never merged into one generic "matches
oracle" check.

Spec 11 T001: adds the Two-Tiered Equivalence Proof's Tier 1 (Construction
Correctness, FR-012) -- a frozen, hand-copied reference of the PRE-REPAIR
`.control()`-based construction (`_pre_repair_hadamard_test_circuit`,
`_pre_repair_v_l_dagger_circuit` below) is kept permanently in this file so
the equivalence claim against the now-repaired, inline-assembled
`fourierlearn.extract._hadamard_test_circuit` remains checkable forever,
independent of what production code looks like today (Constitution §5.2).
"""

from __future__ import annotations

import math

import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import Operator, SparsePauliOp, Statevector

from fourierlearn.circuits import _increment_circuit, compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import _hadamard_test_circuit, estimate_coefficient
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients

_NONTRIVIAL = 1e-2
_VALID_PARTS = ("real", "imag")


def _pre_repair_v_l_dagger_circuit(component: int, width: int) -> QuantumCircuit:
    """Frozen, byte-for-byte copy of `extract._v_l_dagger_circuit` as it
    existed before Spec 11's repair -- this function's OWN internal logic
    never changes (only how it gets controlled does), kept here only so
    `_pre_repair_hadamard_test_circuit` below is fully self-contained."""
    qc = QuantumCircuit(width)
    step = _increment_circuit(width).inverse() if component >= 0 else _increment_circuit(width)
    for _ in range(abs(component)):
        qc.compose(step, inplace=True)
    return qc


def _pre_repair_hadamard_test_circuit(circuit: QuantumCircuit, frequency: tuple[int, ...], part: str) -> QuantumCircuit:
    """Frozen, byte-for-byte copy of `extract._hadamard_test_circuit` as it
    existed before Spec 11's repair (Constitution §1.7 violation: wraps each
    of the `A(U,O)` block and the `V_l^dagger` block in a single whole-block
    `.control(1)` call). Permanently retained as Tier 1's own reference
    construction -- never itself repaired."""
    if part not in _VALID_PARTS:
        raise ValueError(f"part must be one of {_VALID_PARTS}, got {part!r}")
    freq_registers = circuit.qregs[:-2]
    if len(frequency) != len(freq_registers):
        raise ValueError(
            f"frequency has {len(frequency)} components, but the compiled circuit has "
            f"{len(freq_registers)} frequency register(s)"
        )
    for component, freq_reg in zip(frequency, freq_registers):
        width = len(freq_reg)
        low, high = -(2 ** (width - 1)), 2 ** (width - 1) - 1
        if not (low <= component <= high):
            raise ValueError(
                f"frequency component {component} is not representable by a "
                f"{width}-qubit register (valid range [{low}, {high}])"
            )

    had_anc = QuantumRegister(1, "had_anc")
    qc = QuantumCircuit(had_anc, *circuit.qregs)
    qc.h(had_anc[0])
    qc.append(
        circuit.to_gate(label="A(U,O)").control(1),
        [had_anc[0]] + qc.qubits[1 : 1 + circuit.num_qubits],
    )
    for component, freq_reg in zip(frequency, freq_registers):
        v_gate = _pre_repair_v_l_dagger_circuit(component, len(freq_reg)).to_gate(label="Vl_dag").control(1)
        qc.append(v_gate, [had_anc[0]] + list(freq_reg))
    if part == "imag":
        qc.sdg(had_anc[0])
    qc.h(had_anc[0])
    return qc


def _minimal_two_qubit_two_parameter_ir() -> PauliEncodedCircuitIR:
    """research.md R3's own minimal 2-qubit/2-parameter fixture --
    deliberately minimal multiplicities (r_j=1, upload_count=1 each,
    `register_width(1,1)=3` per parameter) to stay genuinely small: an
    EARLIER, richer 2-qubit/2-TIED-parameter attempt (second upload
    coefficient=0.5) was found INTRACTABLE for a full `Operator()` at the
    pre-repair construction (research.md R3's own executed, honest negative
    finding) -- this is why Tier 1 uses this minimal fixture, not that one."""
    return build_ir(
        2,
        [
            PauliUpload("XI", (0, 1), "a", 0, 1.0),
            PauliUpload("IZ", (0, 1), "b", 0, 1.0),
        ],
        SparsePauliOp("ZI"),
    )


def _sample_frequency_axis(width: int) -> list[int]:
    """research.md R3's own representative sample per frequency axis (min,
    `0`, max, and one interior value) -- not an exhaustive sweep, which is
    Tier 2's job at actual baseline scale, not Tier 1's at small scale."""
    low, high = -(2 ** (width - 1)), 2 ** (width - 1) - 1
    values = {low, 0, high}
    if high - low > 2:
        values.add(low + 1)
    return sorted(values)


def test_tier1_operator_equiv_mandated_fixture() -> None:
    """FR-012 (Tier 1, Construction Correctness): the pre-repair reference
    construction and the current (post-repair) `_hadamard_test_circuit`
    compute the IDENTICAL operator on the mandated fixture, for a
    representative sample of frequencies and both real/imag parts."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    freq_width = len(circuit.qregs[0])

    checked_any = False
    for component in _sample_frequency_axis(freq_width):
        for part in _VALID_PARTS:
            old = _pre_repair_hadamard_test_circuit(circuit, (component,), part)
            new = _hadamard_test_circuit(circuit, (component,), part)
            assert Operator(old).equiv(Operator(new)), (component, part)
            checked_any = True
    assert checked_any


def test_tier1_operator_equiv_minimal_two_qubit_fixture() -> None:
    """FR-012 (Tier 1): the same proof, on the minimal 2-qubit/2-parameter
    fixture (research.md R3) -- confirms the repair generalizes beyond a
    1-qubit circuit register, not only the mandated fixture.

    A HAND-PICKED, small sample of (frequency, part) combos, exactly
    matching research.md R3's own executed set -- NOT an exhaustive
    `itertools.product` over both sampled axes: even at this fixture's
    minimal multiplicities, a full 2-axis cross product makes `Operator()`
    reconstruction of the PRE-REPAIR (`.control()`-based) reference circuit
    the dominant cost (research.md R3's own executed profiling: ~9-17s per
    `Operator()` call at this fixture's 10-total-qubit scale) -- confirmed
    in-session to make an exhaustive sweep here take tens of minutes, which
    is disproportionate for Tier 1's own purpose (proving the inline-
    assembly LOGIC has no baseline bug, not exhaustively covering every
    frequency)."""
    ir = _minimal_two_qubit_two_parameter_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("ZI"))

    checked_any = False
    for frequency, part in [((0, 0), "real"), ((0, 0), "imag"), ((1, -1), "real"), ((-1, 1), "imag")]:
        old = _pre_repair_hadamard_test_circuit(circuit, frequency, part)
        new = _hadamard_test_circuit(circuit, frequency, part)
        assert Operator(old).equiv(Operator(new)), (frequency, part)
        checked_any = True
    assert checked_any


def test_tier1_zero_frequency_component_empty_block_handled() -> None:
    """Edge Case (spec.md): a target frequency component of exactly `0`
    (an identity `V_l^dagger`, zero-gate block) must not error and must
    still produce an operator-equivalent circuit."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    for part in _VALID_PARTS:
        old = _pre_repair_hadamard_test_circuit(circuit, (0,), part)
        new = _hadamard_test_circuit(circuit, (0,), part)
        assert Operator(old).equiv(Operator(new))


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    """Spec 3 research.md R8's own construction, reused unchanged per FR-010
    -- NOT re-derived or re-searched for this spec: three untied uploads of
    the same parameter (X, X, Z), a fixed S gate after the first, a fixed T
    gate after the second, observable X."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def _exact_p0_minus_p1(circuit, frequency, part) -> float:
    """Research/test-only exact evaluation via Statevector -- never used in
    extract.py's own production path, which uses only AerSimulator.run() +
    get_counts()."""
    qc = _hadamard_test_circuit(circuit, frequency, part)
    state = Statevector(qc)
    probs = state.probabilities_dict()
    p0 = sum(p for bitstr, p in probs.items() if bitstr[-1] == "0")
    p1 = sum(p for bitstr, p in probs.items() if bitstr[-1] == "1")
    return p0 - p1


def _exact_estimate(circuit, frequency) -> complex:
    return complex(
        _exact_p0_minus_p1(circuit, frequency, "real"),
        _exact_p0_minus_p1(circuit, frequency, "imag"),
    )


def test_hadamard_test_exact_limit_matches_oracle() -> None:
    """research.md R3: the exact (infinite-shot-limit) Hadamard-test
    construction, evaluated via Statevector (research/test-only), must match
    fourierlearn.reference.coefficients()'s own exact value for every
    representable frequency of the mandated fixture, to within 1e-9."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    circuit = compile_observable_circuit(ir, observable)
    expected = oracle_coefficients(ir)

    freq_width = len(circuit.qregs[0])
    low, high = -(2 ** (freq_width - 1)), 2 ** (freq_width - 1) - 1
    checked_any = False
    for l in range(low, high + 1):
        exp = expected.get((l,))
        if exp is None:
            continue
        got = _exact_estimate(circuit, (l,))
        assert math.isclose(got.real, exp.real, abs_tol=1e-9), (l, got, exp)
        assert math.isclose(got.imag, exp.imag, abs_tol=1e-9), (l, got, exp)
        checked_any = True
    assert checked_any


def test_hadamard_test_conjugate_symmetry_on_own_output() -> None:
    """research.md R4 (the specific check /speckit-clarify mandated before
    FR-006's shortcut may be relied upon): the ESTIMATOR's own raw output at
    +l and its own raw output at the register-decoded -l must be exact
    complex conjugates of EACH OTHER -- not a comparison against the
    oracle's b_{-l} value (that is T003's job), but the estimator's two
    outputs compared directly."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    circuit = compile_observable_circuit(ir, observable)
    freq_width = len(circuit.qregs[0])
    high = 2 ** (freq_width - 1) - 1

    checked_any = False
    for l in range(1, high + 1):
        est_plus = _exact_estimate(circuit, (l,))
        est_minus = _exact_estimate(circuit, (-l,))
        assert math.isclose(est_minus.real, est_plus.real, abs_tol=1e-9), (l, est_plus, est_minus)
        assert math.isclose(est_minus.imag, -est_plus.imag, abs_tol=1e-9), (l, est_plus, est_minus)
        checked_any = True
    assert checked_any


def test_mandated_fixture_is_genuinely_complex_in_this_suite() -> None:
    """Guardrail: independently re-confirm, in THIS spec's own suite (not by
    trusting Spec 3's memory alone), that the mandated fixture still
    produces at least one non-DC coefficient with both real and imaginary
    parts individually above a non-triviality threshold -- proving the
    reused fixture has not silently degraded to a real-only case in this
    new context."""
    ir = _mandated_fixture_ir()
    expected = oracle_coefficients(ir)

    found_complex = False
    for (l,), value in expected.items():
        if l == 0:
            continue
        if abs(value.real) > _NONTRIVIAL and abs(value.imag) > _NONTRIVIAL:
            found_complex = True
            break
    assert found_complex, "mandated fixture must remain genuinely complex in this suite"


def test_estimate_coefficient_returns_estimate_and_shot_count() -> None:
    """Acceptance Scenario 1: returns a complex estimate together with the
    exact shot count used."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    estimate, shots_used = estimate_coefficient(circuit, (4,), shots=50_000, seed=1)
    assert isinstance(estimate, complex)
    assert shots_used == 50_000


def test_estimate_coefficient_larger_shots_not_less_accurate() -> None:
    """Acceptance Scenario 2: a much larger shot count is no less accurate
    against the oracle than a smaller one."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    expected = oracle_coefficients(ir)[(4,)]

    small_estimate, _ = estimate_coefficient(circuit, (4,), shots=200, seed=2)
    large_estimate, _ = estimate_coefficient(circuit, (4,), shots=500_000, seed=2)

    small_err = abs(small_estimate - expected)
    large_err = abs(large_estimate - expected)
    # Allow generous slack: this is a statistical, not deterministic,
    # comparison, but 2500x more shots must not leave the estimate *worse*
    # by more than a wide margin consistent with 1/sqrt(shots) scaling.
    assert large_err < small_err + 0.05


@pytest.mark.parametrize("bad_shots", [0, -1, -100])
def test_estimate_coefficient_rejects_nonpositive_shots(bad_shots: int) -> None:
    """Acceptance Scenario 3: a shot count of zero or negative raises."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    with pytest.raises(ValueError):
        estimate_coefficient(circuit, (4,), shots=bad_shots, seed=1)


def test_estimate_coefficient_seed_independent_tolerance() -> None:
    """Acceptance Scenario 4: two runs with the same shot count but
    different seeds both pass the same Hoeffding-derived tolerance
    (research.md R6) -- the tolerance is not tuned to one particular seed."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    expected = oracle_coefficients(ir)[(4,)]

    shots = 200_000
    delta = 0.01
    eps = math.sqrt(2 * math.log(2 / delta) / shots)

    for seed in (11, 22, 33):
        estimate, _ = estimate_coefficient(circuit, (4,), shots=shots, seed=seed)
        assert abs(estimate.real - expected.real) < eps
        assert abs(estimate.imag - expected.imag) < eps
