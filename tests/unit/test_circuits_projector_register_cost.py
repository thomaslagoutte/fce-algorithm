"""T014 — research.md R2: the predicted total register count for the
U⊗U* construction matches the exact formula
n_total = 2*n_circuit + 2*sum_j(register_width(L_j,r_j)) + 2, computed
BEFORE any circuit is compiled (Constitution §10.3)."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.circuits import compile_projector_circuit, predict_projector_register_cost
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.frequency import register_width


def test_predicted_register_cost_matches_the_exact_formula() -> None:
    groups = [
        CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),)),
        CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(1,), weight=1.0),)),
    ]
    ir = trotter_frontend(num_qubits=2, groups=groups, tau=1.0, r=3, observable=SparsePauliOp("II"))

    predicted = predict_projector_register_cost(ir)

    freq_widths = [register_width(p.upload_count, p.multiplicity) for p in ir.parameters()]
    single_copy = ir.num_qubits + sum(freq_widths) + 1
    expected = 2 * single_copy
    assert predicted == expected

    compiled = compile_projector_circuit(ir)
    assert compiled.num_qubits == predicted, "the actually-compiled circuit must match the predicted cost exactly"
