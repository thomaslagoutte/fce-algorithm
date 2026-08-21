"""T009, T012, T026 — FR-003 (Immutable Reports): the generalization check
never mutates the ErrorBoundingReport it consumes. FR-011's own scoping
requirement: experiment.py itself never imports fourierlearn.reference.
User Story 3: containment_record/sparsity_mechanism are always None."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.experiment import run_generalization_check
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.learn import LearnedModel, error_bounding_report
from tests.ci.test_no_forbidden_imports import _scan_module

_TAU, _R = 0.5, 1
_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))


def _fitted_model_and_training_alphas():
    from fourierlearn.reference import coefficients as oracle_coefficients

    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=_TAU, r=_R, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    oracle = oracle_coefficients(ir)
    canonical = tuple(sorted(f for f in oracle if _is_canonical_representative(f)))
    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    model = LearnedModel(
        coefficients=dict(oracle),
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
    training_alphas = [(0.3, -0.4), (-0.7, 1.1)]
    return model, training_alphas


def test_generalization_check_does_not_mutate_report() -> None:
    model, training_alphas = _fitted_model_and_training_alphas()
    report = error_bounding_report(model)
    before = dataclasses.replace(report)  # a snapshot copy for comparison

    run_generalization_check(report, model, training_alphas, suspect_input=training_alphas[0])

    assert report.pac_bound == before.pac_bound
    assert report.trotter_bound == before.trotter_bound
    assert report.noise_characterization == before.noise_characterization
    assert report.scope_statement == before.scope_statement
    assert report.generalization_check_required == before.generalization_check_required
    assert report.suspect_input == before.suspect_input
    assert report == before


def test_exact_dynamics_is_the_only_reference_importer() -> None:
    experiment_path = Path(__file__).resolve().parents[2] / "src" / "fourierlearn" / "experiment.py"
    assert experiment_path.exists()
    found = _scan_module(experiment_path)
    assert "reference" not in found, (
        "experiment.py must not import fourierlearn.reference directly — "
        "only fourierlearn._exact_dynamics.exact_dynamics"
    )


def test_experiment_result_containment_and_sparsity_fields_always_none() -> None:
    model, training_alphas = _fitted_model_and_training_alphas()
    report = error_bounding_report(model)
    result = run_generalization_check(report, model, training_alphas, suspect_input=training_alphas[0])
    assert result.containment_record is None
    assert result.sparsity_mechanism is None
