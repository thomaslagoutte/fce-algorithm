"""T010 — FR-004 (PAC-Bound Rigidity): the generalization check never
sets, upgrades, or otherwise resolves `PacBound.weight_space_translation_status`,
in either a 'generalizes' or a 'refuted' outcome."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.experiment import run_generalization_check
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.learn import LearnedModel, error_bounding_report
from fourierlearn.reference import coefficients as oracle_coefficients

_TAU, _R = 0.5, 1
_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))
_EXPECTED_STATUS = "out_of_scope_requires_sensing_matrix_conditioning"


def _model_and_alphas(dc_override: complex | None = None):
    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=_TAU, r=_R, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    oracle = oracle_coefficients(ir)
    canonical = tuple(sorted(f for f in oracle if _is_canonical_representative(f)))
    coefficients = dict(oracle)
    if dc_override is not None:
        dc = next(f for f in canonical if all(c == 0 for c in f))
        coefficients[dc] = dc_override
    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)
    model = LearnedModel(
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
    return model, [(0.3, -0.4), (-0.7, 1.1)]


def test_weight_space_translation_status_never_changes() -> None:
    # Case 1: a true (non-artifact) model -- expect 'generalizes'.
    model_true, alphas_true = _model_and_alphas()
    report_true = error_bounding_report(model_true)
    assert report_true.pac_bound.weight_space_translation_status == _EXPECTED_STATUS
    result_true = run_generalization_check(report_true, model_true, alphas_true, suspect_input=alphas_true[0])
    assert result_true.verdict == "generalizes"
    assert report_true.pac_bound.weight_space_translation_status == _EXPECTED_STATUS

    # Case 2: a badly displaced model -- expect 'refuted'.
    model_bad, alphas_bad = _model_and_alphas(dc_override=1.0e6 + 0j)
    report_bad = error_bounding_report(model_bad)
    assert report_bad.pac_bound.weight_space_translation_status == _EXPECTED_STATUS
    result_bad = run_generalization_check(report_bad, model_bad, alphas_bad, suspect_input=alphas_bad[0])
    assert result_bad.verdict == "refuted"
    assert report_bad.pac_bound.weight_space_translation_status == _EXPECTED_STATUS
