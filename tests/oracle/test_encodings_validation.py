"""Oracle validation suite for both encodings frontends — FR-011..FR-013, SC-003,
SC-004 (research.md R8).

Constitution §4.3/§6.4: each frontend gets its own genuinely complex (nonzero real
*and* imaginary parts, on a non-DC coefficient) validation case, so a per-upload
coefficient-scaling defect cannot hide behind an accidentally-real-valued test.
"""

from __future__ import annotations

import math

from qiskit.quantum_info import SparsePauliOp

from fourierlearn import reference
from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, trotter_frontend
from fourierlearn.ir import PauliEncodedCircuitIR

_TOL = 1e-9
_NONTRIVIAL = 1e-2  # threshold for "individually nonzero", well above float noise


def test_pauli_pqc_validation_case_is_genuinely_complex() -> None:
    """FR-011: one qubit, parameter `alpha` uploaded twice, untied
    (upload_count=2, r_j=1): first upload `'X'`, second upload `'Z'`,
    coefficient 1.0 for both.

    The combined `X+Y` observable is used deliberately, not arbitrarily: a
    plain `X`, `Y`, or `Z` observable alone is provably degenerate for this
    construction — starting from a real state with only `X`- and
    `Z`-generators produces a state whose amplitudes have a fixed relative
    phase structure that makes any single-Pauli expectation value's Fourier
    coefficients purely real or purely imaginary (never both), the same
    structural degeneracy Spec 1's own two-upload case needed a fixed S-gate
    to escape (research.md R8). Combining `X+Y` breaks that degeneracy.

    Analytically: with theta = pi*alpha, the circuit's state is
    |psi> = cos(theta) e^{i theta}|0> + i sin(theta) e^{-i theta}|1>, giving
    f(alpha) = <psi|X+Y|psi> = 1/2 - (1/2) cos(4 pi alpha) + (1/2) sin(4 pi alpha),
    whose l=4 Fourier coefficient is exactly -(1+i)/4 = -0.25 - 0.25j — derived
    by hand and independently confirmed against the oracle's own output before
    being pinned here (not merely asserted from research.md's illustrative
    figure).
    """
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="alpha", tie_group=0, coefficient=1.0),
        PauliUpload(pauli="Z", qubits=(0,), parameter_label="alpha", tie_group=1, coefficient=1.0),
    ]
    observable = SparsePauliOp(["X", "Y"], coeffs=[1, 1])
    ir = build_ir(num_qubits=1, uploads=uploads, observable=observable)

    result = reference.coefficients(ir)
    coefficient = result[(4,)]

    expected = complex(-0.25, -0.25)
    assert abs(coefficient - expected) / abs(expected) <= _TOL

    assert abs(coefficient.real) > _NONTRIVIAL
    assert abs(coefficient.imag) > _NONTRIVIAL


def test_trotter_validation_case_is_genuinely_complex() -> None:
    """FR-012: two qubits, two coupling groups — Group A: a single `'X'` term
    (qubit 0, weight 1.0); Group B: two tied, commuting terms `'ZZ'`+`'XX'`
    (qubits (0, 1), weight 1.0 each, multiplicity `r_j=2`) — with `tau=0.8`,
    `r=2`. Exercises multi-group composition (research.md R5) and tied
    multiplicity (research.md R6) simultaneously.

    The observable `SparsePauliOp(['IX', 'IY'], coeffs=[1, 1])` was *not* the
    first one tried. A single-Pauli-string observable (e.g. plain `'IX'`) was
    checked first and found, computationally, to give a **purely real**
    spectrum at every non-DC frequency: every gate in this construction
    ('X', 'ZZ', 'XX') is a real-valued matrix, and starting from the real
    state |00>, that forces `f(-alpha) = f(alpha)` for any real-matrix
    observable (real Fourier coefficients) and `f(-alpha) = -f(alpha)` for any
    purely-imaginary one (purely imaginary coefficients) — the same
    even/odd degeneracy the Pauli-PQC case above needed `X+Y` to escape.
    Combining a real term (`'IX'`) with an imaginary one (`'IY'`) breaks it
    here too (research.md R8's addendum)."""
    groups = [
        CouplingGroup("A", (CouplingGroupTerm("X", (0,), 1.0),)),
        CouplingGroup(
            "B",
            (CouplingGroupTerm("ZZ", (0, 1), 1.0), CouplingGroupTerm("XX", (0, 1), 1.0)),
        ),
    ]
    observable = SparsePauliOp(["IX", "IY"], coeffs=[1, 1])
    ir = trotter_frontend(num_qubits=2, groups=groups, tau=0.8, r=2, observable=observable)

    parameters = ir.parameters()
    assert len(parameters) == 2
    assert {p.multiplicity for p in parameters} == {1, 2}  # Group A untied, Group B tied

    result = reference.coefficients(ir)
    coefficient = result[(2, 4)]

    expected = complex(-0.125, 0.125)
    assert abs(coefficient - expected) / abs(expected) <= _TOL

    assert abs(coefficient.real) > _NONTRIVIAL
    assert abs(coefficient.imag) > _NONTRIVIAL


def _trotter_ir_with_coefficient(coefficient: float) -> PauliEncodedCircuitIR:
    """Build the exact same IR structure as
    `test_trotter_validation_case_is_genuinely_complex`, but with every
    per-upload coefficient replaced by the given value — used only to inject
    a deliberately wrong formula below, never to change the real
    implementation."""
    observable = SparsePauliOp(["IX", "IY"], coeffs=[1, 1])
    uploads = [
        PauliUpload(pauli="X", qubits=(0,), parameter_label="A", tie_group=step, coefficient=coefficient)
        for step in range(2)
    ] + [
        PauliUpload(pauli=pauli, qubits=(0, 1), parameter_label="B", tie_group=step, coefficient=coefficient)
        for step in range(2)
        for pauli in ("ZZ", "XX")
    ]
    return build_ir(num_qubits=2, uploads=uploads, observable=observable)


def test_sc004_coefficient_scaling_defect_breaks_validation() -> None:
    """SC-004: the Trotter validation test above is only meaningful if it is
    actually sensitive to the exact coefficient formula `c = -h*tau/(pi*r)`,
    not merely to its sign or to the fact that a scaling is applied at all
    (Constitution §4.3). The Pauli-PQC frontend has no analogous per-upload
    scaling *formula* to perturb — its `build_ir` passes the caller-supplied
    coefficient through unchanged (T003's own propagation test already
    covers that boundary) — so this check is specific to Trotter's own
    formula, per the guardrail's own worked examples.

    Two deliberately wrong variants of the formula are checked against the
    correct, pinned expected value `-0.125+0.125j` at `l=(2, 4)`: dropping
    the load-bearing negative sign (research.md R4's own historical bug),
    and using `r - 1` instead of `r` as the divisor. Both must fail to
    match — proving a real regression in either direction would be caught,
    not silently accepted."""
    h, tau, r = 1.0, 0.8, 2
    correct_coefficient = -h * tau / (math.pi * r)
    expected = complex(-0.125, 0.125)

    sign_dropped = h * tau / (math.pi * r)
    off_by_one_r = -h * tau / (math.pi * (r - 1))
    assert sign_dropped != correct_coefficient
    assert off_by_one_r != correct_coefficient

    for wrong_coefficient in (sign_dropped, off_by_one_r):
        wrong_ir = _trotter_ir_with_coefficient(wrong_coefficient)
        wrong_value = reference.coefficients(wrong_ir)[(2, 4)]
        assert abs(wrong_value - expected) / abs(expected) > _TOL
