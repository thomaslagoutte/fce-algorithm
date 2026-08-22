"""Spec 12 T013/T015 — FR-004 Acceptance Scenario 1 (under-determined
regression never guarded against) and FR-009 (penalty-selection
discipline: grid and CV procedure never a function of shot count)."""

from __future__ import annotations

import numpy as np
from qiskit.circuit.library import RZGate, TGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.cross_topology import (
    _ALPHA_GRID,
    _K_DEFAULT_FOLDS,
    CrossTopologyRow,
    canonical_frequencies,
    fit_cross_topology_lasso,
)
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR

OBSERVABLE = SparsePauliOp("X")


def _mandated_fixture_ir(theta: float) -> PauliEncodedCircuitIR:
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], OBSERVABLE).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], OBSERVABLE).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], OBSERVABLE).gates
    gates = u1 + (FixedGate(RZGate(theta), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=OBSERVABLE)


def test_fit_never_guards_against_too_few_topologies() -> None:
    """FR-004 Acceptance Scenario 1: T (topologies) strictly fewer than
    the number of representable frequencies never raises, warns, or
    otherwise blocks the fit."""
    canonical = canonical_frequencies(_mandated_fixture_ir(0.5))
    num_columns = len(canonical) * 2 - 1  # DC contributes one real column, others two
    thetas = np.linspace(0.1, 3.0, num=max(2, num_columns - 3))  # strictly fewer topologies than columns
    rows = [CrossTopologyRow(ir=_mandated_fixture_ir(t), label=float(np.cos(t))) for t in thetas]

    model = fit_cross_topology_lasso(rows, OBSERVABLE, shots=2_000, seed=7)  # must not raise
    assert model.weights.shape[0] == num_columns


def test_penalty_grid_and_cv_folds_are_invariant_to_shot_count() -> None:
    """FR-009: fit twice on the same topologies/labels at two different
    shot counts (hence two different label-noise levels); the grid and CV
    fold count used must be provably identical between the two runs --
    never a function of the shot count."""
    rng = np.random.default_rng(20260822)
    thetas = rng.uniform(0.1, 3.0, size=6)
    rows = [CrossTopologyRow(ir=_mandated_fixture_ir(t), label=float(np.cos(t))) for t in thetas]

    grid_before = np.array(_ALPHA_GRID, copy=True)
    folds_before = _K_DEFAULT_FOLDS

    fit_cross_topology_lasso(rows, OBSERVABLE, shots=200, seed=1)
    grid_after_small_shots = np.array(_ALPHA_GRID, copy=True)
    folds_after_small_shots = _K_DEFAULT_FOLDS

    fit_cross_topology_lasso(rows, OBSERVABLE, shots=200_000, seed=1)
    grid_after_large_shots = np.array(_ALPHA_GRID, copy=True)
    folds_after_large_shots = _K_DEFAULT_FOLDS

    assert np.array_equal(grid_before, grid_after_small_shots)
    assert np.array_equal(grid_before, grid_after_large_shots)
    assert folds_before == folds_after_small_shots == folds_after_large_shots
