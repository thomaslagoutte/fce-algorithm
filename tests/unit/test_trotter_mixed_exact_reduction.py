"""Mixed Fixed/Encoded Trotter Frontend — FR-005/SC-003.

Calling `mixed_trotter_frontend` with EVERY group marked encoded (zero
fixed groups) MUST reduce EXACTLY to `trotter_frontend`'s own existing
output on the identical input — both structurally and via `Operator.equiv`
with zero deviation.
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, SparsePauliOp

from fourierlearn.encodings.trotter import (
    CouplingGroup,
    CouplingGroupTerm,
    mixed_trotter_frontend,
    trotter_frontend,
)
from fourierlearn.ir import PauliTerm


def _groups() -> list[CouplingGroup]:
    return [
        CouplingGroup("J", (CouplingGroupTerm("ZZ", (0, 1), 1.0),)),
        CouplingGroup(
            "h", (CouplingGroupTerm("X", (0,), 1.0), CouplingGroupTerm("X", (1,), 1.0))
        ),
    ]


def test_zero_fixed_groups_gates_tuple_structurally_identical_to_trotter_frontend() -> None:
    tau, r = 1.09, 2
    observable = SparsePauliOp("ZI")

    old_ir = trotter_frontend(2, _groups(), tau=tau, r=r, observable=observable)
    new_ir = mixed_trotter_frontend(2, _groups(), tau=tau, r=r, observable=observable)

    assert old_ir.gates == new_ir.gates


def test_zero_fixed_groups_operator_equiv_diff_is_exactly_zero() -> None:
    tau, r = 1.09, 2
    observable = SparsePauliOp("ZI")

    old_ir = trotter_frontend(2, _groups(), tau=tau, r=r, observable=observable)
    new_ir = mixed_trotter_frontend(2, _groups(), tau=tau, r=r, observable=observable)

    def bind(ir):
        symbols = ir.parameter_symbols()
        qc = QuantumCircuit(ir.num_qubits)
        for gate in ir.gates:
            if isinstance(gate, PauliTerm):
                qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
            else:
                qc.append(gate.gate, gate.qubits)
        return Operator(qc.assign_parameters({symbols[i]: v for i, v in enumerate([0.6, -0.3])}))

    op_old = bind(old_ir)
    op_new = bind(new_ir)

    assert op_old.equiv(op_new)
    assert abs(op_old.data - op_new.data).max() == 0.0
