"""The ONE module in this project, besides `reference.py` itself, narrowly
authorized to import `fourierlearn.reference` (FR-011, Clarifications
2026-08-21; `tests/ci/test_no_forbidden_imports.py`'s
`_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY`). It exists for exactly one purpose:
Constitution §8.2's generalization check (`fourierlearn.experiment`) needs
a genuinely exact comparison target to distinguish a real capability from
an overfitting artifact — a finite-shot measurement or a finer-Trotter
approximation cannot serve that purpose, however close, because both a
real capability and an artifact would "pass" against either (research.md
R1's executed refutation guard).

This module MUST NOT be used for training-set construction, feature-map
construction, or any other purpose. `fourierlearn.experiment` MUST NOT
import `fourierlearn.reference` itself — only this module's one function.
"""

from __future__ import annotations

import math

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.extract import _is_canonical_representative
from fourierlearn.ir import PauliEncodedCircuitIR
from fourierlearn.reference import coefficients as _oracle_coefficients


def exact_dynamics(
    ir: PauliEncodedCircuitIR,
    observable: SparsePauliOp,
    alpha: tuple[float, ...],
) -> float:
    """The exact expectation value `<0|U^dagger(alpha) P U(alpha)|0>` at a
    concrete numeric `alpha`, computed from `fourierlearn.reference`'s own
    exact Fourier coefficients — never from a finite-shot measurement or an
    approximate feature map. Uses the same real-form reconstruction
    (`2*cos`, `-2*sin` on each canonical coefficient's `.real`/`.imag`
    parts) `fourierlearn.learn.predict` uses, so the two never silently
    diverge in convention.
    """
    if observable != ir.observable:
        raise ValueError(
            "exact_dynamics requires observable == ir.observable — "
            "fourierlearn.reference.coefficients() computes exact coefficients "
            "for ir.observable internally, and silently ignoring a different "
            "explicitly-passed observable would compute the exact value for the "
            "wrong operator without any indication of the mismatch"
        )
    exact = _oracle_coefficients(ir)
    parameters = ir.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)

    total = 0.0
    for freq, b in exact.items():
        if not _is_canonical_representative(freq):
            continue
        if all(c == 0 for c in freq):
            total += b.real
            continue
        phase = math.pi * sum(l * c * a for l, c, a in zip(freq, parameter_coefficients, alpha))
        total += 2.0 * b.real * math.cos(phase) - 2.0 * b.imag * math.sin(phase)
    return total
