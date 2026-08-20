"""FR-013: the oracle predicts and logs its grid cost, and refuses to exceed a
configured budget without explicit confirmation.
"""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import CostBudgetExceeded, coefficients, predict_grid_cost


def _ir_with_upload_count(uploads: int) -> PauliEncodedCircuitIR:
    gates = tuple(
        PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=t)
        for t in range(uploads)
    )
    return PauliEncodedCircuitIR(num_qubits=1, gates=gates, observable=SparsePauliOp("Z"))


def test_predict_grid_cost_matches_formula() -> None:
    ir = _ir_with_upload_count(uploads=3)  # r_j=1, L=3 -> 4*1*3+1 = 13 grid points
    assert predict_grid_cost(ir) == 13


def test_coefficients_raises_when_cost_exceeds_budget_without_confirmation() -> None:
    ir = _ir_with_upload_count(uploads=50)  # large grid, deliberately over budget
    with pytest.raises(CostBudgetExceeded):
        coefficients(ir, budget=100)


def test_coefficients_proceeds_when_confirmed() -> None:
    ir = _ir_with_upload_count(uploads=1)
    # Small grid, well under any reasonable budget — should not raise.
    result = coefficients(ir, budget=5, confirm=True)
    assert isinstance(result, dict)


def test_coefficients_proceeds_when_within_budget_without_confirmation() -> None:
    ir = _ir_with_upload_count(uploads=1)  # cost = 5, within default budget
    result = coefficients(ir, budget=1000)
    assert isinstance(result, dict)
