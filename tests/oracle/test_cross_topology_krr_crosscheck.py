"""Spec 12 T016 — SC-006/FR-013: reproduces research.md R3's executed
LASSO-vs-KRR shared-fixture cross-check as a PERMANENT regression test.

Per this project's Critical Research Mandate (carried from `/speckit-plan`):
floating-point equality between the two routes' predictions is NEVER
asserted. Both routes must independently track the TRUE (noiseless,
oracle) label within a documented tolerance; their MUTUAL divergence is
computed and reported, but never required to be near zero.

Reuses Spec 10's own generic, feature-agnostic `kernel.py` machinery
(`krr_fit_predict`) applied to THIS feature's own `extract_feature_vector`
output (research.md R2's design decision) — never Spec 10's amplitude-
based circuit/oracle, which computes a numerically different `b(x)`
object for the same circuit (an honest, executed finding, not reused
here).
"""

from __future__ import annotations

import numpy as np
from qiskit.circuit.library import RZGate, TGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.cross_topology import (
    CrossTopologyRow,
    canonical_frequencies,
    fit_cross_topology_lasso,
    stack_real,
)
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.kernel import krr_fit_predict
from fourierlearn.reference import coefficients as oracle_coefficients

OBSERVABLE = SparsePauliOp("X")
TRUTH_TOLERANCE = 0.05  # each route's own error against the exact, noiseless label


def _mandated_fixture_ir(theta: float) -> PauliEncodedCircuitIR:
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], OBSERVABLE).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], OBSERVABLE).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], OBSERVABLE).gates
    gates = u1 + (FixedGate(RZGate(theta), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=OBSERVABLE)


def _true_label(ir: PauliEncodedCircuitIR, w_true: np.ndarray) -> float:
    canonical = canonical_frequencies(ir)
    stacked = stack_real(oracle_coefficients(ir), canonical)
    return float(stacked @ w_true)


def test_lasso_and_krr_both_track_truth_and_their_divergence_is_reported() -> None:
    canonical = canonical_frequencies(_mandated_fixture_ir(0.9))
    d = len(stack_real(oracle_coefficients(_mandated_fixture_ir(0.9)), canonical))
    w_true = np.zeros(d)
    # Same sparse pattern as research.md R3: two active canonical
    # frequencies at indices matching Re(b_2)/Im(b_6) in this fixture's
    # own real-stacked basis.
    w_true[[i for i, f in enumerate(_flatten_index_map(canonical)) if f == "Re(b2)"][0]] = 1.3
    w_true[[i for i, f in enumerate(_flatten_index_map(canonical)) if f == "Im(b6)"][0]] = -0.9

    rng = np.random.default_rng(20260822)
    thetas = rng.uniform(0.1, 3.0, size=5)  # T=5, under-determined (d=13)
    rows = [
        CrossTopologyRow(ir=_mandated_fixture_ir(t), label=_true_label(_mandated_fixture_ir(t), w_true))
        for t in thetas
    ]

    lasso_model = fit_cross_topology_lasso(rows, OBSERVABLE, shots=200_000, seed=7)

    design_matrix = np.array(
        [stack_real(oracle_coefficients(row.ir), canonical) for row in rows]
    )  # exact-oracle design matrix, to isolate the L1-vs-L2 comparison from shot noise
    labels = np.array([row.label for row in rows])
    K = design_matrix @ design_matrix.T

    theta_star = 1.234
    x_star = _mandated_fixture_ir(theta_star)
    x_star_stacked = stack_real(oracle_coefficients(x_star), canonical)
    y_star_true = float(x_star_stacked @ w_true)

    from fourierlearn.cross_topology import predict

    y_star_lasso = predict(lasso_model, x_star, shots=200_000, seed=8)

    k_test_row = design_matrix @ x_star_stacked
    y_star_krr = krr_fit_predict(K, labels, lambda0=0.01, test_row=k_test_row)

    lasso_err = abs(y_star_lasso - y_star_true)
    krr_err = abs(y_star_krr - y_star_true)
    mutual_divergence = abs(y_star_lasso - y_star_krr)

    # Both routes track the truth within tolerance -- the actual success criterion.
    assert lasso_err < TRUTH_TOLERANCE, (y_star_lasso, y_star_true, lasso_err)
    assert krr_err < TRUTH_TOLERANCE, (y_star_krr, y_star_true, krr_err)

    # Mutual divergence is COMPUTED and available for reporting -- but NEVER
    # asserted to be near zero (Critical Research Mandate): L1 and L2
    # regularization legitimately diverge, especially under-determined.
    assert mutual_divergence >= 0.0  # always true; the point is this is NOT
    # compared against a near-zero threshold anywhere in this test.


def _flatten_index_map(canonical) -> list[str]:
    labels = []
    for freq in canonical:
        if all(c == 0 for c in freq):
            labels.append(f"Re(b{freq[0]})")
        else:
            labels.append(f"Re(b{freq[0]})")
            labels.append(f"Im(b{freq[0]})")
    return labels
