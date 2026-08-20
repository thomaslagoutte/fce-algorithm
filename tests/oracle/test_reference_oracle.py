"""FR-016, FR-017, FR-018, FR-020, SC-002, SC-008: the reference oracle reproduces
analytically known Fourier coefficients for a single-upload and a two-upload
(genuinely complex) case, and every odd pre-parity coefficient vanishes in both.

Ground truth below was derived analytically and independently cross-checked
numerically (Statevector + a standalone DFT, not this module's own code) before
being encoded here — see the session notes for the derivation. A single Z-upload
acting on |0> with a diagonal generator never leaves the Z-eigenbasis, so both test
circuits include a fixed Hadamard to make the parameter's phase observable at all;
this does not change which parameter is "single-upload" vs "two-upload" (that is
the count of PauliTerm uploads of the *parameterised* gate).
"""

from __future__ import annotations

import cmath

import numpy as np
import pytest
from qiskit.circuit.library import HGate, SGate
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm
from fourierlearn.reference import coefficients

_TOL = 1e-9


def _assert_close(actual: complex, expected: complex) -> None:
    assert abs(actual - expected) <= _TOL, f"expected {expected}, got {actual}"


def _assert_odd_l_vanish(result: dict[tuple[int, ...], complex]) -> None:
    """FR-020/SC-008: every odd pre-parity coefficient must be zero — a live,
    falsifiable check of the parity mechanism, not an assumed property."""
    found_any_odd = False
    for (l,), value in result.items():
        if l % 2 != 0:
            found_any_odd = True
            assert abs(value) <= _TOL, f"odd coefficient l={l} is nonzero: {value}"
    assert found_any_odd, "grid must sample the full domain, exposing odd-l slots"


# --- FR-016: single-upload, real coefficients ------------------------------------


def _single_upload_ir() -> PauliEncodedCircuitIR:
    return PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(
            FixedGate(HGate(), (0,)),
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
        ),
        observable=SparsePauliOp("X"),
    )


def test_single_upload_reproduces_analytic_coefficients() -> None:
    result = coefficients(_single_upload_ir())
    # Analytic: f(alpha) = cos(2*pi*alpha) = 0.5*e^{i*pi*2*alpha} + 0.5*e^{-i*pi*2*alpha}
    # -> b_2 = b_{-2} = 0.5, all else 0. Verified numerically against Statevector
    # before being encoded here (not derived from this module's own output).
    _assert_close(result[(2,)], 0.5 + 0j)
    _assert_close(result[(-2,)], 0.5 + 0j)
    for (l,), value in result.items():
        if l not in (2, -2):
            _assert_close(value, 0j)


def test_single_upload_odd_l_vanish() -> None:
    _assert_odd_l_vanish(coefficients(_single_upload_ir()))


# --- FR-017, FR-018: two-upload, genuinely complex coefficients -----------------


def _two_upload_ir() -> PauliEncodedCircuitIR:
    return PauliEncodedCircuitIR(
        num_qubits=1,
        gates=(
            FixedGate(HGate(), (0,)),
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),
            FixedGate(SGate(), (0,)),  # FR-018 symmetry-breaking gate
            PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=1),
        ),
        # X+Y (not X alone): verified numerically that S with a plain X or Y
        # observable gives a *purely* imaginary or *purely* real coefficient for
        # this single-qubit construction — satisfying FR-018's letter requires
        # nonzero real AND imaginary parts, which X+Y provides while still using S
        # exactly as documented in quickstart.md/data-model.md.
        observable=SparsePauliOp(["X", "Y"], coeffs=[1.0, 1.0]),
    )


def test_two_upload_reproduces_analytic_complex_coefficients() -> None:
    result = coefficients(_two_upload_ir())
    # Analytic (numerically verified independently): b_4 = 0.5 - 0.5j,
    # b_{-4} = 0.5 + 0.5j, all else 0.
    _assert_close(result[(4,)], 0.5 - 0.5j)
    _assert_close(result[(-4,)], 0.5 + 0.5j)
    for (l,), value in result.items():
        if l not in (4, -4):
            _assert_close(value, 0j)


def test_two_upload_coefficient_is_genuinely_complex_not_degenerate() -> None:
    """Constitution §4.3: the test must not pass on a degenerate, real-only or
    imaginary-only case."""
    result = coefficients(_two_upload_ir())
    non_dc = result[(4,)]
    assert abs(non_dc.real) > _TOL
    assert abs(non_dc.imag) > _TOL


def test_two_upload_odd_l_vanish() -> None:
    _assert_odd_l_vanish(coefficients(_two_upload_ir()))
