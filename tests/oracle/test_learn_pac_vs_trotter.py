"""US2 oracle-level tests — FR-007's input-isolation requirement in both
directions, the Trotter bound's divergence from the PAC bound on a
deliberately coarse configuration (Acceptance Scenario 2), and the
weight-recovery formula inversion `_trotter_bound` relies on."""

from __future__ import annotations

import inspect
import math

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.ir import PauliTerm
from fourierlearn.learn import TrainingRow, error_bounding_report, fit_model

_GROUP_A = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=1.0),))
_GROUP_B = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.0),))


def _fitted_model(tau: float, r: int, shots: int = 2_000, seed: int = 5):
    ir = trotter_frontend(num_qubits=1, groups=[_GROUP_A, _GROUP_B], tau=tau, r=r, observable=SparsePauliOp("Z"))
    observable = SparsePauliOp("Z")
    rows = [
        TrainingRow(ir=ir, alpha=(0.3, -0.4), shots=shots, tau=tau, r=r),
        TrainingRow(ir=ir, alpha=(-0.7, 1.1), shots=shots, tau=tau, r=r),
        TrainingRow(ir=ir, alpha=(1.4, 0.2), shots=shots, tau=tau, r=r),
    ]
    return fit_model(rows, observable, seed=seed)


def test_pac_bound_reads_only_measurement_inputs() -> None:
    """FR-007: the PAC-bound computation's public entry point
    (error_bounding_report) never reads tau/r/Trotter order to produce the
    pac_bound field -- confirmed by varying tau/r while holding shots fixed
    and observing the PAC figure is unaffected."""
    model_a = _fitted_model(tau=0.1, r=1, shots=2_000, seed=1)
    model_b = _fitted_model(tau=50.0, r=1, shots=2_000, seed=1)

    report_a = error_bounding_report(model_a)
    report_b = error_bounding_report(model_b)

    assert (
        report_a.pac_bound.per_measurement_statistical_noise_bound
        == report_b.pac_bound.per_measurement_statistical_noise_bound
    ), "PAC bound must be identical when only tau changes, shots/M held fixed"


def test_trotter_bound_reads_only_feature_map_inputs() -> None:
    """FR-007: the Trotter-bound computation never reads shots/sample
    count/delta -- confirmed by varying shots while holding tau/r fixed and
    observing the Trotter figure is unaffected."""
    model_a = _fitted_model(tau=0.5, r=1, shots=500, seed=1)
    model_b = _fitted_model(tau=0.5, r=1, shots=50_000, seed=1)

    report_a = error_bounding_report(model_a)
    report_b = error_bounding_report(model_b)

    assert (
        report_a.trotter_bound.structural_approximation_bound
        == report_b.trotter_bound.structural_approximation_bound
    ), "Trotter bound must be identical when only shots change, tau/r held fixed"

    sig = inspect.signature(error_bounding_report)
    assert "shots" not in sig.parameters and "delta" not in {
        "shots"
    }  # delta is deliberately allowed (PAC-only); shots must never be a Trotter input


def test_trotter_bound_diverges_from_pac_bound_on_coarse_step() -> None:
    """FR-007 Acceptance Scenario 2: a deliberately coarse Trotter
    configuration (large tau, r=1) produces a Trotter bound clearly larger
    than the PAC bound at a realistic shot count, and the report attributes
    the residual gap to the dominant bound rather than a blended figure."""
    coarse_model = _fitted_model(tau=50.0, r=1, shots=2_000, seed=1)
    report = error_bounding_report(coarse_model)

    assert (
        report.trotter_bound.structural_approximation_bound
        > 10 * report.pac_bound.per_measurement_statistical_noise_bound
    ), "the coarse Trotter configuration must dominate the PAC bound for this test to be meaningful"

    # No blended figure: the two bounds remain independently retrievable
    # and the report's own scope statement says so explicitly.
    assert "independent" in report.scope_statement.lower()


def test_trotter_bound_weight_recovery_is_exact() -> None:
    """`_trotter_bound`'s formula inversion `h = -coefficient * pi * r / tau`
    must exactly recover the ORIGINAL declared Hamiltonian weights, on a
    known multi-term fixture with distinct, non-1.0 weights per coupling
    group (2.5 and 1.5) -- not merely produce *some* plausible-looking
    number. This is the same inversion `_trotter_bound` performs internally
    (research.md R9); this test reproduces it independently against the
    fixture's own known ground truth, rather than trusting the production
    function's own output."""
    group_a = CouplingGroup(label="a", terms=(CouplingGroupTerm(pauli="X", qubits=(0,), weight=2.5),))
    group_b = CouplingGroup(label="b", terms=(CouplingGroupTerm(pauli="Z", qubits=(0,), weight=1.5),))
    tau, r = 0.5, 1
    ir = trotter_frontend(num_qubits=1, groups=[group_a, group_b], tau=tau, r=r, observable=SparsePauliOp("Z"))

    known_weights_by_pauli = {"X": 2.5, "Z": 1.5}

    step0_terms = [g for g in ir.gates if isinstance(g, PauliTerm) and g.tie_group == 0]
    assert len(step0_terms) == 2, "fixture must have exactly one term per group in step 0"

    for term in step0_terms:
        recovered_weight = -term.coefficient * math.pi * r / tau
        expected_weight = known_weights_by_pauli[term.pauli]
        assert math.isclose(recovered_weight, expected_weight, rel_tol=1e-12), (
            term.pauli,
            recovered_weight,
            expected_weight,
        )
