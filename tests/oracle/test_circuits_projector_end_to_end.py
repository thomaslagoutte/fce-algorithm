"""T015 — the U⊗U* construction's joint amplitude matches the classical
Fourier series of |<0|U(alpha)|0>|^2, via the STANDARD reference-oracle
machinery (`reference.projector_coefficients`, added to `reference.py`
specifically for this deliverable — Constitution §9.4: the existing
`reference.coefficients` is hardcoded to `circuit.observable`'s own
expectation value and is not modified; this is a new, separate function
for a genuinely different quantity).

Architect-caught correction (resolved before this file was written, not
after): `compile_projector_circuit` produces a circuit with TWO
independent frequency registers (one for `A(U)`, one for `A(U*)`) — there
is no single combined register to read. Combining the two registers'
decoded integers by SUMMING them (`Omega = omega_1 + omega_2`) was tried
first and found WRONG (verified numerically: max error `0.25` against an
independent grid+DFT ground truth on this exact fixture). The correct
combination is the per-axis DIFFERENCE, `Omega = omega_1 - omega_2`
(verified to match the ground truth to machine precision, `1.1e-16`) --
matching the underlying math directly:
`<0|U(alpha)|0> = sum_l a_l e^{i l.alpha}`, so its complex conjugate
contributes `e^{-i l.alpha}`, and the product's `e^{i m.alpha}`
coefficient sits at `m = l1 - l2`, never `l1 + l2`.
"""

from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import compile_frequency_circuit, compile_projector_circuit, conjugate_ir
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import PauliEncodedCircuitIR
from fourierlearn.reference import projector_coefficients

_TOL = 1e-9


def _small_ir() -> PauliEncodedCircuitIR:
    # A single-qubit circuit with a genuinely complex <0|U(alpha)|0>: two
    # untied uploads of the SAME parameter (X then Z) -- both real-matrix
    # Pauli GENERATORS, but e^{i*pi*c*alpha*Z}=diag(e^{i*pi*c*alpha},
    # e^{-i*pi*c*alpha}) is itself complex for generic alpha, so no
    # FixedGate is needed at all here -- deliberately avoiding any
    # complex-matrix FixedGate (e.g. S), which is explicitly out of scope
    # for `conjugate_ir` (ComplexFixedGateConjugationError).
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    return PauliEncodedCircuitIR(num_qubits=1, gates=u1 + u2, observable=SparsePauliOp("Z"))


def _independent_classical_fourier_series_of_probability(ir: PauliEncodedCircuitIR) -> dict[tuple[int, ...], complex]:
    """A FULLY independent computation (never calling `amplitude_coefficients`
    or `projector_coefficients` internally): grid+DFT of `|<0|U(alpha)|0>|^2`
    directly, matching this project's own established oracle-test pattern
    (Statevector-based, test-only exact computation). Uses a grid TWICE as
    wide as a single copy's own ambient range, to avoid aliasing the
    doubled-range combined frequency `m = l1 - l2`."""
    (parameter,) = ir.parameters()
    (coefficient,) = set(parameter.coefficients)
    domain_length = 2 / coefficient
    single_copy_points = 4 * parameter.multiplicity * parameter.upload_count + 1
    n_points = 2 * (single_copy_points - 1) + 1  # doubled ambient half-width, still odd

    p = Parameter("a")
    qc = QuantumCircuit(ir.num_qubits)
    for gate in ir.gates:
        qc.append(gate.to_gate(p), gate.qubits)

    values = []
    for m in range(n_points):
        alpha_val = domain_length * m / n_points
        bound = qc.assign_parameters({p: alpha_val})
        sv = Statevector(bound)
        values.append(abs(sv.data[0]) ** 2)
    transformed = np.fft.fft(np.array(values)) / n_points

    result = {}
    for k in range(n_points):
        m = k if k <= n_points // 2 else k - n_points
        result[(m,)] = complex(transformed[k])
    return result


def test_projector_coefficients_matches_the_classical_fourier_series_of_probability() -> None:
    """Requirement #3: `reference.projector_coefficients` (the standard
    oracle for this deliverable) matches a fully independent classical
    Fourier-series computation of `|<0|U(alpha)|0>|^2` exactly."""
    ir = _small_ir()
    expected = _independent_classical_fourier_series_of_probability(ir)
    got = projector_coefficients(ir)

    max_diff = 0.0
    non_trivial_confirmed = False
    for m, expected_val in expected.items():
        got_val = got.get(m, 0j)
        diff = abs(got_val - expected_val)
        max_diff = max(max_diff, diff)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=_TOL), (m, got_val, expected_val)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=_TOL), (m, got_val, expected_val)
        if m != (0,) and abs(expected_val) > 1e-2:
            non_trivial_confirmed = True

    assert non_trivial_confirmed, "expected at least one genuinely nonzero, non-DC coefficient"
    assert max_diff < _TOL


def test_compiled_projector_circuit_matches_the_standard_oracle() -> None:
    """The actual `compile_projector_circuit` output -- read out by
    decoding BOTH of its two independent frequency registers and
    combining them via the verified DIFFERENCE rule -- matches
    `reference.projector_coefficients` exactly, closing the gap between
    the oracle's own claim and what the compiled circuit's two disjoint
    registers actually produce."""
    ir = _small_ir()
    expected = projector_coefficients(ir)

    combined = compile_projector_circuit(ir)
    sv = Statevector(combined)
    freq_width = len(combined.qregs[0])  # freq0 (U side)
    n_u_qubits = len(compile_frequency_circuit(ir).qubits)
    freq_width_star = len(combined.qregs[3])  # freq0_star (U* side): qregs[3] after freq0,ancilla,circuit

    def two_complement_decode(raw: int, width: int) -> int:
        return raw - (1 << width) if raw >= (1 << (width - 1)) else raw

    got: dict[tuple[int, ...], complex] = {}
    for raw1 in range(2**freq_width):
        for raw2 in range(2**freq_width_star):
            index = raw1 | (raw2 << n_u_qubits)
            amplitude = complex(sv.data[index])
            if abs(amplitude) < 1e-9:
                continue
            l1 = two_complement_decode(raw1, freq_width)
            l2 = two_complement_decode(raw2, freq_width_star)
            m = (l1 - l2,)
            got[m] = got.get(m, 0j) + amplitude

    max_diff = 0.0
    for m, expected_val in expected.items():
        got_val = got.get(m, 0j)
        diff = abs(got_val - expected_val)
        max_diff = max(max_diff, diff)
        assert diff < _TOL, (m, got_val, expected_val)
    assert max_diff < _TOL
