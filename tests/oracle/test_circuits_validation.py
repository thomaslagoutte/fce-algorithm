"""Oracle-level validation for the Circuits Layer — FR-012, FR-013
(research.md R6; Constitution §4.1-§4.3).
"""

from __future__ import annotations

import math

from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.circuits import compile_observable_circuit
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as oracle_coefficients

_TOL = 1e-9
_NONTRIVIAL = 1e-2


def _genuinely_complex_ir() -> PauliEncodedCircuitIR:
    """research.md R6 (corrected): three untied uploads of the same
    parameter (X, X, Z), with a fixed S gate after the first and a fixed T
    gate after the second, observable X. Found by exhaustive search over
    letter/fixed-gate/observable combinations after the originally-assumed
    two-upload X-encoding-with-S-gate construction turned out, when actually
    computed, to be purely real (0.25/0.5/0.25) -- not complex at all. This
    construction gives multiple genuinely complex non-DC coefficients
    (e.g. l=4: 0.1767766952966368+0.1767766952966368j)."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def test_compile_observable_circuit_matches_reference_oracle() -> None:
    """FR-012/FR-013: compile_observable_circuit's post-selected amplitudes
    MUST match fourierlearn.reference.coefficients() (Spec 1's own oracle,
    unmodified) exactly, using the RAW (un-renormalized-by-post-selection-
    probability) amplitude read directly off the statevector -- normalizing
    by the post-selection success probability would be the natural thing to
    do to turn the post-selected branch back into a standalone state, but it
    is the WRONG normalization for this comparison and would introduce a
    systematic magnitude mismatch against the oracle's own b_l, which
    carries no such factor."""
    ir = _genuinely_complex_ir()
    observable = SparsePauliOp("X")

    expected = oracle_coefficients(ir)

    qc = compile_observable_circuit(ir, observable)
    freq_width = len(qc.qregs[0])
    state = Statevector(qc)

    def raw_amplitude_at(l: int) -> complex:
        raw = l % (2**freq_width)
        index = raw | (0 << freq_width) | (0 << (freq_width + 1))
        return complex(state.data[index])  # raw amplitude -- NOT divided by post-select probability

    non_dc_confirmed_complex = False
    for (l,), expected_val in expected.items():
        got_val = raw_amplitude_at(l)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=_TOL), (l, got_val, expected_val)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=_TOL), (l, got_val, expected_val)
        if l != 0 and abs(expected_val.real) > _NONTRIVIAL and abs(expected_val.imag) > _NONTRIVIAL:
            non_dc_confirmed_complex = True

    assert non_dc_confirmed_complex, "expected at least one genuinely complex non-DC coefficient"
