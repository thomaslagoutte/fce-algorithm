"""SC-001 dedicated test — the STATISTICAL sparse-recovery claim
(research.md R5): M << P concrete alpha samples, exact (noiseless) y
measurements, a real LassoCV fit on the real Fourier sensing matrix,
compared against a KNOWN ground-truth sparse coefficient vector, on a
DIFFERENT fixture than the exact-plumbing test.

Deliberately kept in its own dedicated file, separate from
test_learn_design_matrix.py's exact (M >= P) plumbing check -- never
merged into that file or that test function (explicit guardrail, this
round)."""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import SparsePauliOp, Statevector

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.learn import LassoRegressionBackend, _canonical_columns, _reconstruct_complex, build_sensing_matrix
from fourierlearn.reference import _build_circuit as _oracle_build_circuit
from fourierlearn.reference import coefficients as oracle_coefficients

_SEED = 20260821


def test_sc001_statistical_sparse_recovery() -> None:
    """research.md R5: a wider, deliberately sparser single-parameter
    fixture (6 tied upload groups -> L=25 representable frequencies, only
    2 genuinely nonzero canonical frequencies), M=9 << P=25 random alpha
    samples, exact (noiseless) y, real LassoCV fit recovers the one active
    frequency to within 0.05 and assigns near-zero weight to every
    inactive frequency."""
    uploads = [PauliUpload("X", (0,), "alpha", g, 1.0) for g in range(6)]
    ir = build_ir(1, uploads, SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")

    oracle = oracle_coefficients(ir)
    canonical = sorted(f for f in oracle if _is_canonical_representative(f))
    columns = _canonical_columns(canonical)
    P = len(columns)

    active = {f: v for f, v in oracle.items() if abs(v) > 1e-9}
    assert active, "fixture must have at least one genuinely active frequency"

    M = 9
    assert M < P, "this is a statistical UNDER-DETERMINED recovery test -- M must be < P"

    rng = np.random.default_rng(_SEED)
    alphas = [(float(a),) for a in rng.uniform(-2.0, 2.0, size=M)]

    symbols = ir.parameter_symbols()
    (idx,) = symbols.keys()
    qc = _oracle_build_circuit(ir)

    def direct_expectation_y(alpha: float) -> float:
        bound = qc.assign_parameters({symbols[idx]: alpha})
        state = Statevector.from_instruction(bound)
        return state.expectation_value(observable).real

    y = np.array([direct_expectation_y(a[0]) for a in alphas])

    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    A = build_sensing_matrix(alphas, columns, parameter_coefficients)

    backend = LassoRegressionBackend(seed=0)
    x_hat = backend.fit(A, y)
    recon = _reconstruct_complex(x_hat, columns)

    max_active_err = max(abs(recon[f] - oracle[f]) for f in canonical if abs(oracle[f]) > 1e-9)
    max_inactive_val = max(abs(recon[f]) for f in canonical if abs(oracle[f]) <= 1e-9)

    assert max_active_err < 0.05, f"LASSO failed to recover the active coefficient(s): {max_active_err}"
    assert max_inactive_val < 0.05, f"LASSO assigned non-negligible weight to an inactive frequency: {max_inactive_val}"
