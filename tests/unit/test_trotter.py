"""Trotter frontend tests — FR-006..FR-010 (research.md R4, R5, R6, R7)."""

from __future__ import annotations

import math

import numpy as np
import pytest
import scipy.linalg
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend


def test_two_coupling_groups_yield_two_parameters_with_upload_count_r() -> None:
    groups = [
        CouplingGroup("J", (CouplingGroupTerm("Z", (0,), 1.0),)),
        CouplingGroup("m", (CouplingGroupTerm("X", (1,), 1.0),)),
    ]
    ir = trotter_frontend(num_qubits=2, groups=groups, tau=0.8, r=3, observable=SparsePauliOp("II"))

    assert ir.num_parameters == 2
    assert all(p.upload_count == 3 for p in ir.parameters())


def test_tied_same_weight_terms_get_multiplicity_two_and_identical_coefficient() -> None:
    h, tau, r = 1.1, 0.7, 1
    group = CouplingGroup("J", (CouplingGroupTerm("Z", (0,), h), CouplingGroupTerm("X", (1,), h)))
    ir = trotter_frontend(num_qubits=2, groups=[group], tau=tau, r=r, observable=SparsePauliOp("II"))

    (parameter,) = ir.parameters()
    assert parameter.multiplicity == 2
    assert parameter.upload_count == 1
    expected_c = -h * tau / (math.pi * r)
    assert parameter.coefficients == (expected_c, expected_c)


def test_larger_step_count_scales_upload_count_and_rescales_coefficient() -> None:
    h, tau = 1.1, 0.7
    group = CouplingGroup("J", (CouplingGroupTerm("Z", (0,), h), CouplingGroupTerm("X", (1,), h)))

    ir_small_r = trotter_frontend(2, [group], tau=tau, r=2, observable=SparsePauliOp("II"))
    ir_large_r = trotter_frontend(2, [group], tau=tau, r=5, observable=SparsePauliOp("II"))

    (p_small,) = ir_small_r.parameters()
    (p_large,) = ir_large_r.parameters()
    assert p_small.upload_count == 2
    assert p_large.upload_count == 5

    expected_c_large = -h * tau / (math.pi * 5)
    assert p_large.coefficients == tuple([expected_c_large] * (2 * 5))


def test_nonpositive_r_raises() -> None:
    group = CouplingGroup("J", (CouplingGroupTerm("Z", (0,), 1.0),))
    with pytest.raises(ValueError):
        trotter_frontend(1, [group], tau=0.5, r=0, observable=SparsePauliOp("Z"))
    with pytest.raises(ValueError):
        trotter_frontend(1, [group], tau=0.5, r=-3, observable=SparsePauliOp("Z"))


def test_empty_group_or_no_groups_raises() -> None:
    with pytest.raises(ValueError):
        trotter_frontend(1, [], tau=0.5, r=2, observable=SparsePauliOp("Z"))
    with pytest.raises(ValueError):
        trotter_frontend(1, [CouplingGroup("J", ())], tau=0.5, r=2, observable=SparsePauliOp("Z"))


def test_trotter_frontend_rejects_nonuniform_group_weight() -> None:
    """Dedicated rejection test for FR-008: 'sharing a coupling' alone must not
    be treated as satisfying the Foundation Layer's per-parameter coefficient
    uniformity requirement — every term within one declared group must carry
    the exact same structural weight h."""
    group = CouplingGroup(
        "J", (CouplingGroupTerm("Z", (0,), 1.0), CouplingGroupTerm("X", (1,), 2.0))
    )
    with pytest.raises(ValueError, match="non-uniform"):
        trotter_frontend(2, [group], tau=0.5, r=2, observable=SparsePauliOp("II"))


def test_trotter_frontend_rejects_zero_evolution_time() -> None:
    """Dedicated rejection test for research.md R7: `tau=0` is asserted to
    raise directly, not inferred from Spec 1's separately-scoped
    coefficient-must-not-be-zero rejection — every derived coefficient would
    otherwise collapse to exactly 0, and a zero evolution time carries no
    information about the coupling being extracted."""
    group = CouplingGroup("J", (CouplingGroupTerm("Z", (0,), 1.0),))
    with pytest.raises(ValueError):
        trotter_frontend(1, [group], tau=0.0, r=5, observable=SparsePauliOp("Z"))


def test_trotter_frontend_rejects_noncommuting_group() -> None:
    """Dedicated rejection test for research.md R6, reached via Trotter's own
    delegation to pauli_pqc.build_ir (FR-009): confirms the shared
    commutativity check is actually exercised through Trotter's own
    group-to-upload translation, not bypassed by it."""
    group = CouplingGroup(
        "J", (CouplingGroupTerm("X", (0,), 1.0), CouplingGroupTerm("Z", (0,), 1.0))
    )
    with pytest.raises(ValueError, match="non-commuting"):
        trotter_frontend(1, [group], tau=0.5, r=2, observable=SparsePauliOp("Z"))


def test_trotter_frontend_preserves_declared_group_order() -> None:
    """research.md R5: groups are composed *interleaved* — for each Trotter
    step, every declared group is applied once, in the caller's declared
    order — not as r reps of one group followed by r reps of the next
    ("block" ordering). Group A ('ZZ' on qubits (0, 1)) and Group B ('X' on
    qubit 0) are deliberately non-commuting, so interleaved and block
    ordering give numerically different unitaries; asserting both the match
    and the mismatch is what makes this test discriminate on order rather
    than pass vacuously."""
    h_a, alpha_a = 1.3, 0.62
    h_b, alpha_b = -0.7, -0.44
    tau, r = 0.8, 4

    groups = [
        CouplingGroup("A", (CouplingGroupTerm("ZZ", (0, 1), h_a),)),
        CouplingGroup("B", (CouplingGroupTerm("X", (0,), h_b),)),
    ]
    ir = trotter_frontend(
        num_qubits=2, groups=groups, tau=tau, r=r, observable=SparsePauliOp("II")
    )

    symbols = ir.parameter_symbols()
    qc = QuantumCircuit(2)
    for gate in ir.gates:
        qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
    bound = qc.assign_parameters({symbols[0]: alpha_a, symbols[1]: alpha_b})
    actual = Operator(bound).data

    z_mat = np.array([[1, 0], [0, -1]])
    x_mat = np.array([[0, 1], [1, 0]])
    identity = np.eye(2)
    zz = np.kron(z_mat, z_mat)
    x_on_qubit0 = np.kron(identity, x_mat)

    step_a = scipy.linalg.expm(-1j * h_a * alpha_a * zz * (tau / r))
    step_b = scipy.linalg.expm(-1j * h_b * alpha_b * x_on_qubit0 * (tau / r))
    interleaved = np.linalg.matrix_power(step_b @ step_a, r)
    block = np.linalg.matrix_power(step_b, r) @ np.linalg.matrix_power(step_a, r)

    assert np.allclose(actual, interleaved, atol=1e-9)
    assert not np.allclose(actual, block, atol=1e-9)
