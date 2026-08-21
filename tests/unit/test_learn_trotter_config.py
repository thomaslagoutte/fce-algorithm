"""FR-013 dedicated tests — the pinned tau float-comparison tolerance
(research.md R6) and the heterogeneous-Trotter-configuration rejection
guard (SC-007). Two independent test functions."""

from __future__ import annotations

import math

import pytest
from qiskit.circuit.library import SGate, TGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR
from fourierlearn.learn import (
    _TAU_ABS_TOL,
    _TAU_REL_TOL,
    HeterogeneousTrotterConfigError,
    TrainingRow,
    _same_trotter_config,
    fit_model,
)


def test_tau_tolerance_cases() -> None:
    """research.md R6's six cases, using the module's own pinned
    _TAU_REL_TOL/_TAU_ABS_TOL constants -- not re-derived inline values."""
    assert _TAU_REL_TOL == 1e-9
    assert _TAU_ABS_TOL == 1e-12

    # Case A: same tau, different float derivation.
    tau_literal = 3.7
    tau_recomputed = 11.1 / 3.0
    assert tau_literal != tau_recomputed  # not bit-identical
    assert _same_trotter_config(tau_literal, 12, tau_recomputed, 12)

    # Case B: same tau, accumulated rounding.
    r = 12
    step = tau_literal / r
    tau_reaccumulated = 0.0
    for _ in range(r):
        tau_reaccumulated += step
    assert _same_trotter_config(tau_literal, r, tau_reaccumulated, r)

    # Case C: genuinely different tau -- the real bug this guards against.
    assert not _same_trotter_config(3.7, 12, 3.9, 12)

    # Case D: near-zero boundary.
    assert _same_trotter_config(0.0, 1, 1e-13, 1)
    assert not _same_trotter_config(0.0, 1, 1e-10, 1)

    # Case E: r uses exact int equality, not this tolerance.
    assert not _same_trotter_config(3.7, 12, 3.7, 13)
    assert math.isclose(3.7, 3.7, rel_tol=_TAU_REL_TOL, abs_tol=_TAU_ABS_TOL)


def _fixture_ir() -> PauliEncodedCircuitIR:
    u1 = build_ir(1, [PauliUpload("X", (0,), "alpha", 0, 1.0)], SparsePauliOp("Z")).gates
    u2 = build_ir(1, [PauliUpload("X", (0,), "alpha", 1, 1.0)], SparsePauliOp("Z")).gates
    u3 = build_ir(1, [PauliUpload("Z", (0,), "alpha", 2, 1.0)], SparsePauliOp("Z")).gates
    gates = u1 + (FixedGate(SGate(), (0,)),) + u2 + (FixedGate(TGate(), (0,)),) + u3
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("X"))


def test_heterogeneous_trotter_config_rejected() -> None:
    """FR-013, SC-007: fitting on rows sharing tau but differing r (and
    vice versa) is rejected with a clear, named error -- not silently
    fit across a heterogeneous feature map."""
    ir = _fixture_ir()
    observable = SparsePauliOp("X")

    rows_differing_r = [
        TrainingRow(ir=ir, alpha=(0.3,), shots=1_000, tau=3.7, r=12),
        TrainingRow(ir=ir, alpha=(-0.7,), shots=1_000, tau=3.7, r=13),  # differs only in r
    ]
    with pytest.raises(HeterogeneousTrotterConfigError):
        fit_model(rows_differing_r, observable, seed=1)

    rows_differing_tau = [
        TrainingRow(ir=ir, alpha=(0.3,), shots=1_000, tau=3.7, r=12),
        TrainingRow(ir=ir, alpha=(-0.7,), shots=1_000, tau=3.9, r=12),  # differs only in tau
    ]
    with pytest.raises(HeterogeneousTrotterConfigError):
        fit_model(rows_differing_tau, observable, seed=1)

    # Sanity: identical (tau, r) rows do NOT raise.
    rows_homogeneous = [
        TrainingRow(ir=ir, alpha=(0.3,), shots=1_000, tau=3.7, r=12),
        TrainingRow(ir=ir, alpha=(-0.7,), shots=1_000, tau=3.7, r=12),
    ]
    fit_model(rows_homogeneous, observable, seed=1)
