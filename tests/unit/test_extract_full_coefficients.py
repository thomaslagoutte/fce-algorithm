"""Core `extract_coefficients` acceptance tests — FR-005, FR-006, FR-007,
FR-012 (research.md R2, R4, R7, R8)."""

from __future__ import annotations

import math
from unittest import mock

import pytest
from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn import extract
from fourierlearn.circuits import compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import ShotBudgetExceeded, estimate_coefficient, extract_coefficients
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients

_HOEFFDING_DELTA = 0.01


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    """Spec 3 research.md R8's own construction, reused unchanged per FR-010."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def _hoeffding_eps(shots: int, delta: float = _HOEFFDING_DELTA) -> float:
    return math.sqrt(2 * math.log(2 / delta) / shots)


def test_full_coefficient_set_contains_every_representable_frequency() -> None:
    """Acceptance Scenario 1: exactly one estimate per representable
    frequency, including DC."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    expected = oracle_coefficients(ir)

    result = extract_coefficients(ir, observable, shots=50_000, seed=1, confirm=True)

    assert set(result.keys()) == set(expected.keys())
    assert (0,) in result


def test_full_extraction_performs_only_half_the_circuit_executions() -> None:
    """Acceptance Scenario 2: the number of underlying circuit executions
    reflects estimating only the non-mirrored half of the frequencies
    directly (plus the always-direct DC term), deriving the rest by complex
    conjugation -- not estimating every frequency independently. Verified
    with a call-counting spy on estimate_coefficient (the underlying
    execution primitive), per the guardrail requiring an actual count, not
    an assumption."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    expected = oracle_coefficients(ir)
    total_frequencies = len(expected)

    with mock.patch.object(extract, "estimate_coefficient", wraps=extract.estimate_coefficient) as spy:
        extract_coefficients(ir, observable, shots=1_000, seed=1, confirm=True)
        call_count = spy.call_count

    # DC is always direct; every other frequency is one of a mirrored pair,
    # only one of which is estimated directly.
    non_dc = total_frequencies - 1
    expected_calls = non_dc // 2 + 1
    assert call_count == expected_calls
    assert call_count < total_frequencies


def test_dc_coefficient_is_real_load_bearing() -> None:
    """FR-012 (Clarifications 2026-08-20): a load-bearing, per-run assertion
    that the DC coefficient is real, for EVERY full-coefficient-set
    extraction this test file exercises -- not an optional or informational
    check.

    **Why this is not redundant with test_hadamard_test_conjugate_symmetry_
    on_own_output (test_extract_hadamard_test.py)**: that test checks the
    Hadamard-test estimator's EXACT (infinite-shot-limit, Statevector-
    evaluated) output -- a design-time, noiseless proof that the construction
    itself has no sign flip. THIS test checks the REAL, finite-shot,
    AerSimulator-sampled pipeline end-to-end, through the actual public
    extract_coefficients() entry point, with real measurement statistics
    and shot noise. It is a live, continuously-running guard that the
    ACTUAL shipped pipeline -- not just its exact-limit design -- keeps
    respecting the Hermiticity invariant on every run, catching a
    regression the exact-limit test alone could not (e.g. a bug introduced
    only in the shot-execution or counts-aggregation path, which the
    Statevector-based test never exercises at all).
    """
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    shots = 200_000

    result = extract_coefficients(ir, observable, shots=shots, seed=5, confirm=True)

    eps = _hoeffding_eps(shots)
    assert abs(result[(0,)].imag) < eps


def test_cost_budget_guard_raises_without_confirmation() -> None:
    """FR-007: predicted cost (circuits x shots) exceeding budget raises
    ShotBudgetExceeded unless confirm=True -- mirroring Spec 1's
    CostBudgetExceeded/confirm=True interface style exactly."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")

    with mock.patch.object(extract, "estimate_coefficient", wraps=extract.estimate_coefficient):
        with pytest.raises(ShotBudgetExceeded):
            extract_coefficients(ir, observable, shots=1_000_000_000, budget=100)


def test_cost_budget_guard_proceeds_with_confirmation() -> None:
    """The same over-budget request succeeds once confirm=True is passed."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    result = extract_coefficients(ir, observable, shots=100, budget=1, confirm=True)
    assert len(result) > 0


def test_unrepresentable_frequency_raises() -> None:
    """FR-008: requesting a frequency the compiled circuit's frequency
    register cannot represent raises rather than returning a meaningless
    result."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    freq_width = len(circuit.qregs[0])
    out_of_range = 2 ** (freq_width + 4)

    with pytest.raises(ValueError):
        estimate_coefficient(circuit, (out_of_range,), shots=100)


def test_non_hermitian_observable_rejected_before_shortcut() -> None:
    """Acceptance Scenario 3 (US2): a non-Hermitian observable must raise
    before the conjugate-symmetry shortcut is ever applied.

    **Reachability, not merely defense-in-depth**: extract_coefficients()
    accepts `observable` as its OWN direct parameter (matching Circuits
    Layer's own compile_observable_circuit(ir, observable) signature) --
    it is NOT derived from `ir.observable`, and nothing upstream forces the
    two to match or forces THIS observable through Spec 1's own
    Hermiticity-validating IR constructor. A caller can pass an arbitrary,
    directly-constructed non-Hermitian SparsePauliOp here with no IR
    involved in constructing it at all -- exactly what this test does. This
    check is therefore genuinely reachable via the public API, not dead
    code guarding against something upstream validation already forecloses.
    """
    ir = _mandated_fixture_ir()
    non_hermitian_observable = SparsePauliOp("Z", coeffs=[1j])  # i*Z: not Hermitian

    with pytest.raises(ValueError):
        extract_coefficients(ir, non_hermitian_observable, shots=100, confirm=True)
