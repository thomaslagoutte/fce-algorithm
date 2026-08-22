"""Mixed Fixed/Encoded Trotter Frontend tests — Spec 013 FR-001/002/006/007/008.

Structural interleaving, edge cases (zero-value fixed term, all-fixed case),
and `coordinate_order` parameter-index mapping (User Story 2 Acceptance
Scenario 2).
"""

from __future__ import annotations

import math

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import build_ir
from fourierlearn.encodings.trotter import (
    CouplingGroup,
    CouplingGroupTerm,
    FixedCouplingGroup,
    mixed_trotter_frontend,
)
from fourierlearn.ir import FixedGate, PauliTerm


def test_mixed_construction_interleaves_in_caller_declared_order() -> None:
    """FR-001/FR-002: for each of the r Trotter steps, the gates tuple
    contains one contiguous run per declared group, in EXACTLY the caller's
    declared order — never all fixed terms collected before all encoded
    terms (or vice versa)."""
    group_h1 = CouplingGroup("h1", (CouplingGroupTerm("X", (0,), 1.0),))
    group_fixed = FixedCouplingGroup((CouplingGroupTerm("ZZ", (0, 2), 1.0),), value=0.8)
    group_h2 = CouplingGroup("h2", (CouplingGroupTerm("Z", (1,), 1.0),))
    group_specs = [group_h1, group_fixed, group_h2]

    ir = mixed_trotter_frontend(
        num_qubits=3, group_specs=group_specs, tau=0.95, r=3, observable=SparsePauliOp("ZII")
    )

    gate_types = [type(g).__name__ for g in ir.gates]
    expected_step = ["PauliTerm", "FixedGate", "PauliTerm"]
    assert gate_types == expected_step * 3
    assert len(ir.parameters()) == 2


def test_mixed_construction_all_fixed_groups_produces_only_fixed_gates() -> None:
    """FR-006: zero encoded groups (every group fixed) MUST still produce a
    valid IR whose gates tuple consists entirely of FixedGate elements,
    without invoking pauli_pqc.build_ir at all."""
    group_fixed_a = FixedCouplingGroup((CouplingGroupTerm("X", (0,), 1.0),), value=0.4)
    group_fixed_b = FixedCouplingGroup((CouplingGroupTerm("Z", (0,), 1.0),), value=-0.2)

    ir = mixed_trotter_frontend(
        num_qubits=1,
        group_specs=[group_fixed_a, group_fixed_b],
        tau=0.5,
        r=2,
        observable=SparsePauliOp("Z"),
    )

    assert all(isinstance(g, FixedGate) for g in ir.gates)
    assert len(ir.gates) == 4  # r=2 steps * 2 fixed groups (1 term each)
    assert ir.num_parameters == 0


def test_mixed_construction_zero_value_fixed_term_is_accepted() -> None:
    """FR-008: a fixed group's declared coupling value of exactly 0 MUST
    still produce a valid FixedGate (the identity-equivalent rotation),
    never a special-cased omission or an error — a zero coupling is a
    legitimate physical value (e.g. a genuinely absent graph edge)."""
    group_fixed = FixedCouplingGroup((CouplingGroupTerm("Z", (0,), 1.0),), value=0.0)

    ir = mixed_trotter_frontend(
        num_qubits=1, group_specs=[group_fixed], tau=0.5, r=2, observable=SparsePauliOp("Z")
    )

    assert len(ir.gates) == 2
    assert all(isinstance(g, FixedGate) for g in ir.gates)


def test_mixed_construction_maps_distinct_labels_via_build_ir_coordinate_order() -> None:
    """User Story 2 Acceptance Scenario 2: distinct encoded parameter labels
    map to a parameter_index via pauli_pqc.build_ir's own coordinate_order-
    based assignment — the SAME mapping build_ir would produce if called
    directly on just those groups' uploads."""
    group_h1 = CouplingGroup("h1", (CouplingGroupTerm("X", (0,), 1.0),))
    group_h2 = CouplingGroup("h2", (CouplingGroupTerm("Z", (1,), 1.0),))
    group_fixed = FixedCouplingGroup((CouplingGroupTerm("ZZ", (0, 1), 1.0),), value=0.3)
    tau, r = 0.7, 2
    observable = SparsePauliOp("ZI")

    mixed_ir = mixed_trotter_frontend(
        num_qubits=2,
        group_specs=[group_h1, group_fixed, group_h2],
        tau=tau,
        r=r,
        observable=observable,
    )

    from fourierlearn.encodings.pauli_pqc import PauliUpload

    direct_uploads = []
    for step in range(r):
        for group in (group_h1, group_h2):
            for term in group.terms:
                coefficient = -term.weight * tau / (math.pi * r)
                direct_uploads.append(
                    PauliUpload(
                        pauli=term.pauli,
                        qubits=term.qubits,
                        parameter_label=group.label,
                        tie_group=step,
                        coefficient=coefficient,
                    )
                )
    direct_ir = build_ir(num_qubits=2, uploads=direct_uploads, observable=observable)

    mixed_encoded_terms = [g for g in mixed_ir.gates if isinstance(g, PauliTerm)]
    assert [t.parameter_index for t in mixed_encoded_terms] == [
        t.parameter_index for t in direct_ir.gates
    ]
