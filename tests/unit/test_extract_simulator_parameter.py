"""Spec 11 T013/T014/T015 — FR-006/FR-007 (deliverable c, User Story 3):
the additive `simulator: AerSimulator | None = None` parameter on
`estimate_coefficient` and `extract_coefficients`.
"""

from __future__ import annotations

import math

from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

from fourierlearn.circuits import compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import estimate_coefficient, extract_coefficients
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    """Same fixture as `tests/unit/test_extract_hadamard_test.py` (Spec 3
    research.md R8's own construction, reused unchanged)."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


class _InstrumentedAerSimulator(AerSimulator):
    """A real `AerSimulator` subclass that additionally counts `.run()`
    invocations against its own object identity -- used to prove a
    caller-supplied instance is genuinely used (T014) and genuinely
    REUSED across every internal call (T015), never silently replaced or
    reconstructed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_call_count = 0

    def run(self, *args, **kwargs):
        self.run_call_count += 1
        return super().run(*args, **kwargs)


def test_estimate_coefficient_simulator_none_matches_unmodified_behavior() -> None:
    """FR-007 Acceptance Scenario 1: `simulator=None` (or omitted) behaves
    identically to today's unmodified code -- checked against the oracle
    within the shot count's own Hoeffding tolerance, same as the existing
    Spec 4 test suite already does for the omitted case."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    expected = oracle_coefficients(ir)[(4,)]

    shots = 200_000
    eps = math.sqrt(2 * math.log(2 / 0.01) / shots)

    est_omitted, _ = estimate_coefficient(circuit, (4,), shots=shots, seed=42)
    est_explicit_none, _ = estimate_coefficient(circuit, (4,), shots=shots, seed=42, simulator=None)

    assert est_omitted == est_explicit_none
    assert abs(est_omitted.real - expected.real) < eps
    assert abs(est_omitted.imag - expected.imag) < eps


def test_estimate_coefficient_uses_the_supplied_simulator_instance() -> None:
    """FR-007 Acceptance Scenario 2: a caller-supplied instance is the
    exact object used for execution -- never silently replaced."""
    ir = _mandated_fixture_ir()
    circuit = compile_observable_circuit(ir, SparsePauliOp("X"))
    sim = _InstrumentedAerSimulator()

    estimate_coefficient(circuit, (4,), shots=1_000, seed=1, simulator=sim)

    # Two sub-circuits (real, imag) -> exactly 2 .run() calls on THIS instance.
    assert sim.run_call_count == 2


def test_extract_coefficients_reuses_one_supplied_simulator_across_the_loop() -> None:
    """research.md R9's own semantic-correctness requirement (T015): a
    single caller-supplied `AerSimulator` instance passed to
    `extract_coefficients` is reused across ALL internal per-frequency
    `estimate_coefficient` calls -- not reconstructed fresh per frequency.

    Independently computes the expected canonical-frequency count via the
    same public building blocks `extract_coefficients` itself uses
    (`frequency.pre_parity_range`, `_is_canonical_representative`) --
    never by reading the number back off the instrumented counter itself,
    which would make the assertion circular."""
    from fourierlearn import frequency as frequency_mod
    from fourierlearn.extract import _is_canonical_representative

    ir = _mandated_fixture_ir()
    sim = _InstrumentedAerSimulator()

    extract_coefficients(ir, SparsePauliOp("X"), shots=1_000, seed=1, simulator=sim)

    domain_per_axis = [
        list(frequency_mod.pre_parity_range(p.multiplicity, p.upload_count)) for p in ir.parameters()
    ]
    all_frequencies: list[tuple[int, ...]] = [()]
    for axis_values in domain_per_axis:
        all_frequencies = [prefix + (v,) for prefix in all_frequencies for v in axis_values]
    expected_canonical_count = sum(1 for f in all_frequencies if _is_canonical_representative(f))

    # Every canonical frequency contributes exactly 2 .run() calls (real,
    # imag) on the SAME shared instance -- confirmed by object-identity-
    # bound call counting, not merely "a simulator of the same type was
    # used somewhere."
    assert sim.run_call_count == 2 * expected_canonical_count
