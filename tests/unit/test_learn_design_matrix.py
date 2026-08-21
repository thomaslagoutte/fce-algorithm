"""FR-006/FR-015 dedicated tests — the EXACT linear-algebra plumbing round
trip (research.md R4): an exactly-determined system (M >= P, ordinary least
squares, NO LASSO), bind alpha -> exact y -> build the real sensing matrix
-> solve -> reconstruct complex b -> compare to the oracle.

Deliberately kept in its own dedicated file, separate from the STATISTICAL
sparse-recovery test (test_learn_sparse_recovery.py, T008) -- the two
claims (exact plumbing vs. statistical M<<P recovery) are never merged into
one test function or one test file (explicit guardrail, this round)."""

from __future__ import annotations

import numpy as np
from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.learn import _canonical_columns, _reconstruct_complex, build_sensing_matrix
from fourierlearn.reference import _build_circuit as _oracle_build_circuit
from fourierlearn.reference import coefficients as oracle_coefficients

_SEED = 20260821


def _mandated_fixture_ir() -> PauliEncodedCircuitIR:
    """Spec 3 research.md R8's own construction, reused unchanged."""
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def _direct_expectation_y(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, alpha: float) -> float:
    """Test-only exact evaluation (reference.py's own plain circuit builder
    + Statevector, no shots) -- isolates "is the plumbing correct" from
    shot noise entirely, per this round's mandate."""
    symbols = ir.parameter_symbols()
    (idx,) = symbols.keys()
    qc = _oracle_build_circuit(ir)
    bound = qc.assign_parameters({symbols[idx]: alpha})
    state = Statevector.from_instruction(bound)
    return state.expectation_value(observable).real


def _build_end_to_end(ir: PauliEncodedCircuitIR, observable: SparsePauliOp, num_samples: int):
    """Shared setup for both tests below: canonical columns, sampled
    alphas, exact y values, and the sensing matrix -- NOT the assertions
    themselves, which stay in separate test functions."""
    oracle = oracle_coefficients(ir)
    canonical = sorted(f for f in oracle if _is_canonical_representative(f))
    columns = _canonical_columns(canonical)

    rng = np.random.default_rng(_SEED)
    alphas = [(float(a),) for a in rng.uniform(-2.0, 2.0, size=num_samples)]
    y = np.array([_direct_expectation_y(ir, observable, a[0]) for a in alphas])

    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    A = build_sensing_matrix(alphas, columns, parameter_coefficients)
    return oracle, columns, A, y


def test_fr006_end_to_end_exact_round_trip() -> None:
    """research.md R4: M=25 >= P=13, ordinary least squares (no LASSO),
    reconstructed b matches the oracle to within 1e-8 for every
    representable frequency, including the mirrored half."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    oracle, columns, A, y = _build_end_to_end(ir, observable, num_samples=25)

    assert np.linalg.matrix_rank(A) == len(columns), "sensing matrix is not full column rank"

    x_hat, *_ = np.linalg.lstsq(A, y, rcond=None)
    recon = _reconstruct_complex(x_hat, columns)

    assert set(recon.keys()) == set(oracle.keys())
    max_err = max(abs(recon[f] - oracle[f]) for f in oracle)
    assert max_err < 1e-8, f"end-to-end round trip is NOT exact: max error {max_err}"


def test_fr006_end_to_end_negative_control_sign_flip() -> None:
    """research.md R4's negative control: flipping the sign convention of
    every sensing-matrix Im column (-sin -> +sin) must be DETECTED --
    proving the exact round-trip test above is not vacuous."""
    ir = _mandated_fixture_ir()
    observable = SparsePauliOp("X")
    oracle, columns, A, y = _build_end_to_end(ir, observable, num_samples=25)

    A_bad = A.copy()
    for k, (_, part) in enumerate(columns):
        if part == "Im":
            A_bad[:, k] = -A_bad[:, k]

    x_bad, *_ = np.linalg.lstsq(A_bad, y, rcond=None)
    recon_bad = _reconstruct_complex(x_bad, columns)

    mismatch = any(abs(recon_bad[f] - oracle[f]) > 1e-6 for f in oracle)
    assert mismatch, "negative control failed to be detected -- end-to-end check is vacuous!"
