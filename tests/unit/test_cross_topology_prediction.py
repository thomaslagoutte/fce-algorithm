"""Spec 12 T020/T021 — FR-005 (prediction via the identical extraction
call path), FR-010 (held-out disjointness assertion), FR-011 (Hermiticity
gate before any prediction is attempted)."""

from __future__ import annotations

import math

import pytest
from qiskit.circuit.library import RYGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.cross_topology import (
    CrossTopologyModel,
    CrossTopologyRow,
    assert_held_out_disjoint,
    canonical_frequencies,
    fit_cross_topology_lasso,
    predict,
)
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm

OBSERVABLE = SparsePauliOp("Z")


def _ir(theta: float) -> PauliEncodedCircuitIR:
    gates = (
        FixedGate(RYGate(theta), (0,)),
        PauliTerm(pauli="X", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0),
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=OBSERVABLE)


def test_held_out_disjointness_passes_when_absent() -> None:
    training = (_ir(0.3), _ir(0.9), _ir(1.7))
    assert_held_out_disjoint(training, _ir(2.4))  # must not raise


def test_held_out_disjointness_raises_when_present() -> None:
    training = (_ir(0.3), _ir(0.9), _ir(1.7))
    with pytest.raises(ValueError):
        assert_held_out_disjoint(training, _ir(0.9))


def test_predict_uses_the_same_extraction_path_as_training() -> None:
    """FR-005: `predict` must call `extract_feature_vector` on `x_star`
    exactly as every training row does -- verified here by confirming
    `predict`'s own output matches a manual, independent computation built
    from the SAME public `extract_feature_vector`/`stack_real` functions
    (not a distinct, ad hoc extraction path)."""
    from fourierlearn.cross_topology import extract_feature_vector, stack_real

    thetas = (0.3, 0.9, 1.7, 2.1)
    rows = [CrossTopologyRow(ir=_ir(t), label=math.cos(t)) for t in thetas]
    model = fit_cross_topology_lasso(rows, OBSERVABLE, shots=5_000, seed=1)

    x_star = _ir(2.8)
    got = predict(model, x_star, shots=5_000, seed=2)

    manual_coeffs = extract_feature_vector(x_star, OBSERVABLE, shots=5_000, seed=2)
    manual_stacked = stack_real(manual_coeffs, canonical_frequencies(x_star))
    expected = float(manual_stacked @ model.weights)

    assert got == expected


def test_predict_rejects_non_hermitian_observable_before_fitting() -> None:
    """FR-011: a non-Hermitian observable is rejected before any
    prediction is attempted -- checked at fit time (fit_cross_topology_
    lasso), the same way Spec 4's own extraction layer rejects it, so no
    model built from one can ever reach `predict` in the first place."""
    non_hermitian = SparsePauliOp(["X", "Y"], coeffs=[1.0, 1.0j])
    rows = [CrossTopologyRow(ir=_ir(0.3), label=0.5), CrossTopologyRow(ir=_ir(0.9), label=0.2)]
    with pytest.raises(ValueError):
        fit_cross_topology_lasso(rows, non_hermitian, shots=1_000, seed=1)
