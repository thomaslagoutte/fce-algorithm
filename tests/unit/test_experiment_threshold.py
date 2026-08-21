"""T008 — Threshold Determinism: the generalization check's verdict is an
absolute, inclusive rule (research.md R2). Executed at the exact boundary
(99.9% / exactly 100% / 100.1% of the model's own Trotter bound), not only
comfortably on either side of it."""

from __future__ import annotations

import math

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn._exact_dynamics import exact_dynamics
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.experiment import run_generalization_check
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.learn import LearnedModel, _trotter_bound, error_bounding_report

_TAU, _R = 0.5, 1
_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))


def _model_with_fixed_prediction(fixed_value: float) -> LearnedModel:
    """A model whose canonical coefficients are chosen so predict() returns
    exactly `fixed_value` for any alpha -- i.e. only the DC term is
    nonzero, since the DC basis function is the constant 1 regardless of
    alpha (fourierlearn.learn.predict's own real-form basis)."""
    from fourierlearn.reference import coefficients as oracle_coefficients

    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=_TAU, r=_R, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    oracle = oracle_coefficients(ir)
    canonical = tuple(sorted(f for f in oracle if _is_canonical_representative(f)))
    dc = next(f for f in canonical if all(c == 0 for c in f))
    coefficients = {f: 0j for f in oracle}
    coefficients[dc] = complex(fixed_value, 0.0)
    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    return LearnedModel(
        coefficients=coefficients,
        canonical=canonical,
        parameter_coefficients=parameter_coefficients,
        observable=observable,
        ir=ir,
        tau=_TAU,
        r=_R,
        seed=1,
        shots_per_row=(1_000,),
        run_manifest={},
    )


@pytest.mark.parametrize(
    "fraction, expected_verdict",
    [
        (0.999, "generalizes"),
        (1.0, "generalizes"),  # exact boundary tie -- inclusive `<=`
        (1.001, "refuted"),
    ],
)
def test_threshold_is_absolute_at_the_boundary(fraction: float, expected_verdict: str) -> None:
    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=_TAU, r=_R, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    trotter_bound = _trotter_bound(ir, _TAU, _R).structural_approximation_bound
    assert trotter_bound > 0.0

    training_alphas = [(0.1, 0.1)]
    shifted_alpha = tuple(a + 5.0 for a in training_alphas[0])
    exact_value = exact_dynamics(ir, observable, shifted_alpha)

    predicted_value = exact_value + fraction * trotter_bound
    model_at_gap = _model_with_fixed_prediction(predicted_value)
    report_at_gap = error_bounding_report(model_at_gap)

    result = run_generalization_check(
        report_at_gap, model_at_gap, training_alphas, suspect_input=training_alphas[0]
    )

    assert math.isclose(result.exact_value, exact_value, rel_tol=1e-12)
    assert result.verdict == expected_verdict, (
        fraction,
        result.predicted_value,
        result.exact_value,
        result.trotter_bound,
    )
