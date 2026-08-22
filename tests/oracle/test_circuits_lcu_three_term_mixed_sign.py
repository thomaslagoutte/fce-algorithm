"""Critical implementation instruction #1 (Spec 9 /speckit.implement): a
3-term LCU fixture with at least two different signs (beta = +1, -2, +3),
proving -- end to end, against the exact reference oracle, matching Spec
3's own established validation methodology (test_circuits_lcu_single_term_unchanged.py's
sibling `tests/oracle/test_circuits_validation.py`) -- that the folded
circuit correctly handles:

- multi-qubit selector amplitude encoding (3 terms -> ceil(log2(3))=2
  selector qubits, not just 1),
- a multi-qubit diagonal sign gate (not just a single-qubit Z, since two
  of the three signs differ), and
- safe zero-padding of the unused 4th computational basis state.
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


def _genuinely_complex_ir(observable: SparsePauliOp) -> PauliEncodedCircuitIR:
    """Reuses the exact fixture shape from `tests/oracle/test_circuits_validation.py`'s
    own `_genuinely_complex_ir` (Constitution §9.4 -- not reinvented)."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], observable).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], observable).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], observable).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=observable)


def test_three_term_mixed_sign_lcu_matches_oracle_linear_combination() -> None:
    weights = {"Z": 1.0, "X": -2.0, "Y": 3.0}
    total = sum(abs(b) for b in weights.values())

    per_term_oracle = {p: oracle_coefficients(_genuinely_complex_ir(SparsePauliOp(p))) for p in weights}
    expected_combined = {
        l: sum(weights[p] * per_term_oracle[p][l] for p in weights) / total for l in per_term_oracle["Z"]
    }

    lcu_observable = SparsePauliOp(list(weights.keys()), coeffs=list(weights.values()))
    ir = PauliEncodedCircuitIR(
        num_qubits=1,
        gates=_genuinely_complex_ir(SparsePauliOp("Z")).gates,
        observable=lcu_observable,
    )

    qc = compile_observable_circuit(ir, lcu_observable)

    selector_reg = qc.qregs[-1]
    assert selector_reg.name == "lcu_selector"
    assert len(selector_reg) == 2, "3 terms require ceil(log2(3))=2 selector qubits, not 1"

    freq_width = len(qc.qregs[0])
    state = Statevector(qc)

    def raw_amplitude_at(l: int) -> complex:
        raw = l % (2**freq_width)
        return complex(state.data[raw])  # ancilla=0, circuit=0, selector=00 -- all at index 0 offset

    max_diff = 0.0
    non_dc_confirmed_complex = False
    for (l,), expected_val in expected_combined.items():
        got_val = raw_amplitude_at(l)
        diff = abs(got_val - expected_val)
        max_diff = max(max_diff, diff)
        assert math.isclose(got_val.real, expected_val.real, abs_tol=_TOL), (l, got_val, expected_val)
        assert math.isclose(got_val.imag, expected_val.imag, abs_tol=_TOL), (l, got_val, expected_val)
        if l != 0 and abs(expected_val.real) > 1e-2 and abs(expected_val.imag) > 1e-2:
            non_dc_confirmed_complex = True

    assert non_dc_confirmed_complex, "expected at least one genuinely complex non-DC coefficient"
    assert max_diff < 1e-9
