"""Reference oracle — FR-011, FR-012, FR-013, FR-020. QUARANTINED per Constitution
§3.3/§3.4: exact statevector computation lives only here plus test helpers; no
production module may import this or `Statevector`/`Operator`/`expm` (enforced by
the CI import guard, tests/ci/test_no_forbidden_imports.py).

This oracle computes exactly one thing — the circuit Fourier coefficients of
f(alpha) = <0|U^dagger(alpha) O U(alpha)|0> for a finite gate sequence. It does NOT
simulate continuous-time Hamiltonian dynamics, and so has no legitimate use for
`expm` or a dense Hamiltonian matrix — only `Statevector` is used (research.md R6).
`Operator`/`expm` remain available in this module for a later Spec 6 (Experiment)
need; this oracle simply never imports them.

Broken into four separately implementable pieces plus one composition entry point,
per architectural instruction — none merged into a single function:
  1. cost-budget guard   (predict_grid_cost, _check_budget)
  2. grid construction   (_build_grid)
  3. circuit evaluation  (_build_circuit, _evaluate_grid)
  4. FFT + indexing      (_fft_and_index)
  5. composition         (coefficients)
"""

from __future__ import annotations

import itertools
import logging
import math

import numpy as np
import numpy.typing as npt
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from fourierlearn.frequency import dft_frequencies
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm

logger = logging.getLogger(__name__)

DEFAULT_BUDGET = 10_000


class CostBudgetExceeded(RuntimeError):
    """Raised when a grid evaluation would exceed the configured cost budget
    without explicit confirmation (§10.3)."""


# --- 1. Cost-budget guard (FR-013) -----------------------------------------------


def predict_grid_cost(circuit: PauliEncodedCircuitIR) -> int:
    """Total number of grid points (= circuit evaluations) the oracle would need:
    the product, over every parameter, of `4 * r_j * L_j + 1` (FR-011)."""
    total = 1
    for p in circuit.parameters():
        total *= 4 * p.multiplicity * p.upload_count + 1
    return total


def _check_budget(circuit: PauliEncodedCircuitIR, budget: int, confirm: bool) -> int:
    cost = predict_grid_cost(circuit)
    logger.info("Predicted grid cost: %d circuit evaluations (budget=%d)", cost, budget)
    if cost > budget and not confirm:
        raise CostBudgetExceeded(
            f"Grid evaluation would require {cost} circuit evaluations, exceeding "
            f"budget {budget}. Pass confirm=True to proceed anyway (§10.3)."
        )
    return cost


# --- 2. Nyquist grid construction (FR-011, FR-020) -------------------------------


def _build_grid(circuit: PauliEncodedCircuitIR) -> list[npt.NDArray[np.float64]]:
    """Per parameter (in coordinate_order), the `4*r_j*L_j+1`-point grid over the
    FULL period-`2/coefficient` domain — not the period-1 half-domain the parity
    result would, in principle, justify (FR-020): sampling only the half-domain
    would make every odd-l coefficient structurally unobservable, baking the parity
    claim in as an assumption rather than a checked property.

    The domain length is `2/coefficient`, not a fixed `2` (audit finding, 2026-08-20):
    `to_gate()` applies the physical rotation angle `-pi*coefficient*alpha`, so the
    circuit's true periodicity in `alpha` is `2/coefficient`, not `2`. Sampling a
    fixed length-2 domain regardless of `coefficient` silently aliases the extracted
    spectrum for any non-unit coefficient — confirmed numerically in-session
    (coefficient=0.37 on a single, untied term already reproduces a wrong result
    against an independent fine-grid ground truth). The IR's own construction-time
    validation (`PauliEncodedCircuitIR._validate_tying`) guarantees `coefficient` is
    uniform across every term of one parameter, so this rescaling is well-defined
    per parameter; the extracted integer `l` is then conjugate to `coefficient*alpha`,
    not to `alpha` itself — physical frequency is `coefficient * l` (§6.4's "physical
    frequency is reconstructed in the interpretation layer")."""
    axes = []
    for p in circuit.parameters():
        n_points = 4 * p.multiplicity * p.upload_count + 1
        (coefficient,) = set(p.coefficients)  # uniform by construction (ir.py)
        domain_length = 2 / coefficient
        axes.append(np.array([domain_length * m / n_points for m in range(n_points)]))
    return axes


# --- 3. Circuit evaluation (FR-011, FR-012) --------------------------------------


def _build_circuit(circuit: PauliEncodedCircuitIR) -> QuantumCircuit:
    """One QuantumCircuit built from the IR's gate sequence, using
    `ir.parameter_symbols()` — never a fresh Parameter per term — so every term
    sharing a parameter_index binds to the identical symbol (FR-005)."""
    symbols = circuit.parameter_symbols()
    qc = QuantumCircuit(circuit.num_qubits)
    for gate in circuit.gates:
        if isinstance(gate, PauliTerm):
            qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
        elif isinstance(gate, FixedGate):
            qc.append(gate.gate, gate.qubits)
        else:  # pragma: no cover - exhaustive by GateOp's definition
            raise TypeError(f"unknown gate type: {type(gate)!r}")
    return qc

def _evaluate_grid(circuit: PauliEncodedCircuitIR) -> npt.NDArray[np.complex128]:
    """Evaluate f(alpha) = <0|U^dagger(alpha) O U(alpha)|0> at every grid point,
    using only `Statevector` — no `Operator`, no `expm` (research.md R6)."""
    parameters = circuit.parameters()
    symbols = circuit.parameter_symbols()
    qc = _build_circuit(circuit)
    axes = _build_grid(circuit)
    shape = tuple(len(axis) for axis in axes)

    values = np.zeros(shape, dtype=complex)
    for index in itertools.product(*(range(n) for n in shape)):
        binding = {
            symbols[p.index]: axes[axis_i][index[axis_i]]
            for axis_i, p in enumerate(parameters)
        }
        bound = qc.assign_parameters(binding)
        state = Statevector.from_instruction(bound)
        values[index] = state.expectation_value(circuit.observable).real
    return values


# --- 4. FFT + coefficient indexing (FR-011, FR-009) ------------------------------


def _fft_and_index(values: npt.NDArray[np.complex128]) -> dict[tuple[int, ...], complex]:
    """Apply `numpy.fft.fftn`, normalize by total point count, and index the
    result by integer pre-parity frequency tuple `l` using
    `frequency.dft_frequencies()` — never an inline `fftfreq`/`fftshift`
    computation (FR-009)."""
    total_points = values.size
    transformed = np.fft.fftn(values) / total_points

    per_axis_frequencies = [dft_frequencies(n) for n in values.shape]
    result: dict[tuple[int, ...], complex] = {}
    for index in itertools.product(*(range(n) for n in values.shape)):
        l_tuple = tuple(int(per_axis_frequencies[axis][idx]) for axis, idx in enumerate(index))
        result[l_tuple] = complex(transformed[index])
    return result


# --- 5. Composition: the Oracle Protocol's entry point ---------------------------


def coefficients(
    circuit: PauliEncodedCircuitIR,
    budget: int = DEFAULT_BUDGET,
    confirm: bool = False,
) -> dict[tuple[int, ...], complex]:
    """Maps a PauliEncodedCircuitIR to its exact Fourier coefficients. Satisfies the
    `Oracle` Protocol (contracts.py) — composes the cost-budget guard, grid
    construction, circuit evaluation, and FFT/indexing steps above."""
    _check_budget(circuit, budget, confirm)
    values = _evaluate_grid(circuit)
    return _fft_and_index(values)
