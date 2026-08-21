"""Learning Backend Layer — FR-001..FR-015.

Two responsibilities, kept in this one module (§9.1's `learn` pipeline
stage): (1) a **new** finite-shot primitive, `estimate_y`, that measures the
real-valued expectation `y(alpha) = <0|U^dagger(alpha) P U(alpha)|0>` at a
concrete numeric parameter assignment (FR-014) — genuinely simpler than
Spec 4's `V_l`-based circuit (no frequency register, no controlled-shift
gates at all: research.md R2) — together with the real Fourier sensing
matrix it feeds (FR-015, research.md R3) and a sparse-recovery regression
engine (`LassoRegressionBackend`, FR-001..FR-006, FR-012, FR-013) built on
it; (2) an error-bounding framework (`error_bounding_report`, FR-007..011)
reporting a PAC-style statistical bound and a structural Trotter bound as
two permanently separate figures.

Deliberately separate, executed verification classes underlie this module
(never conflated, per explicit planning mandate): research.md R4 is an
exactly-determined (`M >= P`) linear-algebra plumbing check with **no**
LASSO; research.md R5 is a genuinely under-determined (`M << P`) statistical
sparse-recovery check with real `LassoCV` fitting, on a *different* fixture.

No `Statevector`, `Operator`, `expm`, or `fourierlearn.reference` import
anywhere in this module — the last is enforced mechanically by Spec 1's own
CI import guard (`tests/ci/test_no_forbidden_imports.py`), which forbids
every production module except `reference.py` itself from importing it.
This module's plain-forward-circuit builder (`_plain_forward_circuit`) is
therefore its own, independently-defined function — structurally identical
to `reference.py`'s internal circuit-construction loop, but not imported
from it — reusing the actual shared logic (`PauliTerm.to_gate()`,
`FixedGate`, Circuits Layer's `_insert_observable`/`basis_change_gates`)
rather than reimplementing any of that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import numpy.typing as npt
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import Pauli, SparsePauliOp
from qiskit_aer import AerSimulator
from sklearn.linear_model import LassoCV

from fourierlearn import frequency
from fourierlearn.circuits import _insert_observable
from fourierlearn.encodings.pauli_pqc import _pad_to_full_width_little_endian
from fourierlearn.extract import _is_canonical_representative
from fourierlearn.ir import FixedGate, PauliEncodedCircuitIR, PauliTerm

_DEFAULT_DELTA = 0.01
DEFAULT_SHOT_BUDGET = 10_000_000

# FR-013 (research.md R6): the pinned float-comparison tolerance for `tau`
# (total evolution time, `encodings/trotter.py`'s own naming) — `r` (step
# count) is an int, compared with exact `==`, never this tolerance.
_TAU_REL_TOL = 1e-9
_TAU_ABS_TOL = 1e-12

# FR-003/FR-004 (the "$t^2$-penalty bug" guardrail, research.md R5): an
# explicit, version-pinned, never-regenerated penalty grid. Reused as the
# same object on every call — never rebuilt from `shots`, `tau`, or `r`.
_ALPHA_GRID: npt.NDArray[np.float64] = np.geomspace(1e-4, 1.0, 30)
_K_DEFAULT_FOLDS = 5


class ShotBudgetExceeded(RuntimeError):
    """Raised when a fit's predicted total shot cost would exceed the
    configured budget without explicit confirmation (§10.3) — mirrors Spec
    1's `CostBudgetExceeded`/`confirm=True` interface style and Spec 4's
    `ShotBudgetExceeded`, defined locally here rather than imported from
    either (neither may be imported: `reference.py` is off-limits per the
    CI guard, and this feature no longer calls `extract.py` at all after
    the 2026-08-21 row-model correction)."""


class HeterogeneousTrotterConfigError(ValueError):
    """Raised when a single fit's training rows do not all share one
    identical Trotter configuration `(tau, r)` — FR-013. Mixed-configuration
    training is out of scope, deferred to a future spec."""


def _same_trotter_config(tau_a: float, r_a: int, tau_b: float, r_b: int) -> bool:
    """FR-013's pinned tolerance (research.md R6): `r` uses exact `==`;
    `tau` uses `math.isclose` with the module-level `_TAU_REL_TOL`/`_TAU_ABS_TOL`
    constants — never an inline magic number."""
    return r_a == r_b and math.isclose(tau_a, tau_b, rel_tol=_TAU_REL_TOL, abs_tol=_TAU_ABS_TOL)


@dataclass(frozen=True)
class TrainingRow:
    """One training row: a concrete numeric assignment `alpha` of every
    encoded parameter, the finite shot count used to measure `y` there, and
    the Trotter configuration `(tau, r)` the row's own `ir` was built with
    (FR-013 — carried explicitly per row, not read back out of `ir`, since
    `PauliEncodedCircuitIR` itself only stores the already-combined
    `coefficient = -weight*tau/(pi*r)`, not `tau`/`r` separately)."""

    ir: PauliEncodedCircuitIR
    alpha: tuple[float, ...]
    shots: int
    tau: float
    r: int


def _plain_forward_circuit(ir: PauliEncodedCircuitIR) -> QuantumCircuit:
    """The plain, unconditional parameterized circuit built directly from
    `ir.gates` — no frequency register, no ancilla-controlled shift gates at
    all (research.md R2: 1 qubit vs. Spec 4's 6, on the mandated fixture).
    Structurally identical to `fourierlearn.reference`'s own internal
    circuit-construction loop, but independently defined here since this
    (production) module may not import `fourierlearn.reference` at all
    (Spec 1's CI import guard) — reuses `PauliTerm.to_gate()`/`FixedGate`
    directly, the actual shared gate-construction logic, rather than
    reimplementing it."""
    symbols = ir.parameter_symbols()
    qc = QuantumCircuit(ir.num_qubits)
    for gate in ir.gates:
        if isinstance(gate, PauliTerm):
            qc.append(gate.to_gate(symbols[gate.parameter_index]), gate.qubits)
        elif isinstance(gate, FixedGate):
            qc.append(gate.gate, gate.qubits)
        else:  # pragma: no cover - exhaustive by GateOp's definition
            raise TypeError(f"unknown gate type: {type(gate)!r}")
    return qc


def _folded_circuit(ir: PauliEncodedCircuitIR, observable: SparsePauliOp) -> QuantumCircuit:
    """Forward pass, observable folded in via Circuits Layer's shared
    `_insert_observable` helper (reused unchanged, Constitution §9.4), and
    the literal inverse of the forward pass — structurally the same pattern
    `compile_observable_circuit` uses, applied to the plain (frequency-
    register-free) forward circuit instead."""
    forward = _plain_forward_circuit(ir)
    circuit_reg = forward.qregs[0]
    qc = QuantumCircuit(circuit_reg)
    qc.compose(forward, inplace=True)
    _insert_observable(qc, observable, circuit_reg)
    qc.compose(forward.inverse(), inplace=True)
    return qc


def estimate_y(
    ir: PauliEncodedCircuitIR,
    observable: SparsePauliOp,
    alpha: tuple[float, ...],
    shots: int,
    seed: int | None = None,
) -> tuple[float, int]:
    """FR-014 — the new primitive: estimate the real-valued expectation
    `y(alpha) = <0|U^dagger(alpha) P U(alpha)|0>` at a concrete numeric
    `alpha`, using only finite-shot measurement (Constitution Article
    II/§9.6: `AerSimulator.run()` + `get_counts()`, `transpile()` first —
    never `Statevector`/`Operator`). An ancilla-Hadamard-test wrapping
    `_folded_circuit`, measuring only the real part (`P(0) - P(1)`) — no
    `Sdg`/imaginary sub-circuit, since research.md R2 confirmed the
    imaginary part is exactly zero for this construction (a Hermitian
    observable's expectation value is real by construction, not merely
    numerically small).

    Returns `(estimate, shots)` — the exact shot count used (§5.6).
    """
    if shots <= 0:
        raise ValueError(f"estimate_y requires shots > 0, got {shots}")

    parameters = ir.parameters()
    if len(alpha) != len(parameters):
        raise ValueError(
            f"alpha has {len(alpha)} components, but the IR has {len(parameters)} "
            "encoded parameter(s)"
        )
    symbols = ir.parameter_symbols()
    binding = {symbols[p.index]: a for p, a in zip(parameters, alpha)}

    folded = _folded_circuit(ir, observable)
    bound = folded.assign_parameters(binding)

    had_anc = QuantumRegister(1, "had_anc")
    creg = ClassicalRegister(1, "c")
    qc = QuantumCircuit(had_anc, *bound.qregs, creg)
    qc.h(had_anc[0])
    qc.append(bound.to_gate(label="folded").control(1), [had_anc[0]] + qc.qubits[1 : 1 + bound.num_qubits])
    qc.h(had_anc[0])
    qc.measure(had_anc[0], creg[0])

    simulator = AerSimulator()
    qc = transpile(qc, simulator)
    kwargs = {} if seed is None else {"seed_simulator": seed}
    counts = simulator.run(qc, shots=shots, **kwargs).result().get_counts()

    p0 = counts.get("0", 0) / shots
    p1 = counts.get("1", 0) / shots
    return p0 - p1, shots


def _canonical_columns(canonical: Sequence[tuple[int, ...]]) -> list[tuple[tuple[int, ...], str]]:
    """FR-006's real-column layout: one `Re` column for DC, `(Re, Im)`
    column pairs (in that fixed order) for every other canonical
    frequency."""
    columns: list[tuple[tuple[int, ...], str]] = []
    for freq in canonical:
        is_dc = all(c == 0 for c in freq)
        columns.append((freq, "Re"))
        if not is_dc:
            columns.append((freq, "Im"))
    return columns


def _stack_real(
    coefficients: dict[tuple[int, ...], complex], columns: Sequence[tuple[tuple[int, ...], str]]
) -> npt.NDArray[np.float64]:
    """FR-006: complex coefficient dict -> real-stacked vector, per
    `_canonical_columns`'s layout (research.md R2/R4, verified round trip)."""
    vec = np.empty(len(columns))
    for k, (freq, part) in enumerate(columns):
        z = coefficients[freq]
        vec[k] = z.real if part == "Re" else z.imag
    return vec


def _reconstruct_complex(
    x: npt.NDArray[np.float64], columns: Sequence[tuple[tuple[int, ...], str]]
) -> dict[tuple[int, ...], complex]:
    """FR-006: real-stacked vector -> complex coefficient dict over every
    representable frequency, deriving each mirror via `.conjugate()`
    (research.md R2/R4, verified round trip)."""
    canonical_complex: dict[tuple[int, ...], complex] = {}
    for (freq, part), val in zip(columns, x):
        is_dc = all(c == 0 for c in freq)
        if is_dc:
            canonical_complex[freq] = complex(float(val), 0.0)
        elif part == "Re":
            prev = canonical_complex.get(freq, 0j)
            canonical_complex[freq] = complex(float(val), prev.imag)
        else:
            prev = canonical_complex.get(freq, 0j)
            canonical_complex[freq] = complex(prev.real, float(val))
    full = dict(canonical_complex)
    for freq, z in canonical_complex.items():
        mirror = tuple(-c for c in freq)
        if mirror != freq:
            full[mirror] = z.conjugate()
    return full


def build_sensing_matrix(
    alphas: Sequence[tuple[float, ...]],
    columns: Sequence[tuple[tuple[int, ...], str]],
    parameter_coefficients: tuple[float, ...],
) -> npt.NDArray[np.float64]:
    """FR-015: the real Fourier sensing matrix (research.md R3, derived from
    `fourierlearn.reference`'s own DFT/grid convention, not invented
    independently): `A[j,k] = 1` for the DC column; `2*cos(pi * l . (c ⊙
    alpha_j))` for a `Re` column; `-2*sin(...)` for an `Im` column."""
    M = len(alphas)
    P = len(columns)
    A = np.empty((M, P))
    for j, alpha in enumerate(alphas):
        for k, (freq, part) in enumerate(columns):
            if all(c == 0 for c in freq):
                A[j, k] = 1.0
                continue
            phase = math.pi * sum(l * c * a for l, c, a in zip(freq, parameter_coefficients, alpha))
            A[j, k] = 2.0 * math.cos(phase) if part == "Re" else -2.0 * math.sin(phase)
    return A


class LassoRegressionBackend:
    """Satisfies `fourierlearn.contracts.RegressionBackend`: `fit(A, y)`
    accepts exactly those two parameters — structurally, not just by
    convention, making it impossible for `shots`/`tau`/`r` to ever reach the
    regularization-penalty selection (the historical "$t^2$-penalty bug"'s
    entry point), closed at the interface level (T029: verified via
    `inspect.signature`, not source-text grepping)."""

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed

    def fit(self, A: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        cv = min(_K_DEFAULT_FOLDS, A.shape[0])
        model = LassoCV(
            alphas=_ALPHA_GRID,
            cv=cv,
            fit_intercept=False,
            random_state=self._seed,
            selection="cyclic",
            max_iter=10_000,
        )
        model.fit(A, y)
        return model.coef_


@dataclass(frozen=True)
class LearnedModel:
    """FR-001's output: a sparse mapping from Hamiltonian term (one per
    representable frequency) to a fitted complex weight, plus the metadata
    needed to predict new points and generate an error-bounding report."""

    coefficients: dict[tuple[int, ...], complex]
    canonical: tuple[tuple[int, ...], ...]
    parameter_coefficients: tuple[float, ...]
    observable: SparsePauliOp
    ir: PauliEncodedCircuitIR
    tau: float
    r: int
    seed: int | None
    shots_per_row: tuple[int, ...]
    run_manifest: dict[str, object]


def fit_model(
    rows: Sequence[TrainingRow],
    observable: SparsePauliOp,
    seed: int | None = None,
    budget: int = DEFAULT_SHOT_BUDGET,
    confirm: bool = False,
    eval_rows: Sequence[TrainingRow] = (),
) -> LearnedModel:
    """FR-001, FR-002, FR-005, FR-006, FR-012, FR-013: fit a sparse
    Hamiltonian model from `M = len(rows)` measured `(alpha_j, y_j)` pairs.

    Raises `ValueError` if `observable` is not Hermitian (checked before any
    measurement — FR-006), if `rows` is empty, or if any evaluation input in
    `eval_rows` also appears in `rows` (FR-005 — checked explicitly after
    the split is given, never assumed). Raises `HeterogeneousTrotterConfigError`
    if `rows` do not all share one identical `(tau, r)` (FR-013). Raises
    `ShotBudgetExceeded` if the total predicted shot cost exceeds `budget`
    unless `confirm=True` (§10.3). Never raises for `len(rows)` being
    "too few" relative to the frequency count — the under-determined regime
    is this function's intended operating mode (FR-002/FR-003).
    """
    if observable != observable.adjoint():
        raise ValueError(
            "fit_model requires a Hermitian observable — the conjugate-symmetry "
            "reconstruction (FR-006) only holds for a Hermitian observable's "
            "real-valued expectation function"
        )
    if not rows:
        raise ValueError("fit_model requires at least one training row")

    tau0, r0 = rows[0].tau, rows[0].r
    for row in rows[1:]:
        if not _same_trotter_config(tau0, r0, row.tau, row.r):
            raise HeterogeneousTrotterConfigError(
                f"training rows do not share one Trotter configuration: "
                f"(tau={tau0}, r={r0}) vs. (tau={row.tau}, r={row.r})"
            )

    if eval_rows:
        train_alphas = {row.alpha for row in rows}
        eval_alphas = {row.alpha for row in eval_rows}
        overlap = train_alphas & eval_alphas
        if overlap:
            raise ValueError(f"training/evaluation leakage detected: {sorted(overlap)}")

    predicted_cost = sum(row.shots for row in rows)
    if predicted_cost > budget and not confirm:
        raise ShotBudgetExceeded(
            f"Fitting on {len(rows)} rows would require {predicted_cost} total shots, "
            f"exceeding budget {budget}. Pass confirm=True to proceed anyway (§10.3)."
        )

    ir0 = rows[0].ir
    parameters = ir0.parameters()
    parameter_coefficients = tuple(p.coefficients[0] for p in parameters)

    domain_per_axis = [list(frequency.pre_parity_range(p.multiplicity, p.upload_count)) for p in parameters]
    all_frequencies: list[tuple[int, ...]] = [()]
    for axis_values in domain_per_axis:
        all_frequencies = [prefix + (v,) for prefix in all_frequencies for v in axis_values]
    canonical = tuple(f for f in all_frequencies if _is_canonical_representative(f))
    columns = _canonical_columns(canonical)

    y_values = np.empty(len(rows))
    shots_per_row: list[int] = []
    for i, row in enumerate(rows):
        row_seed = None if seed is None else seed + i
        y_j, shots_used = estimate_y(row.ir, observable, row.alpha, row.shots, seed=row_seed)
        y_values[i] = y_j
        shots_per_row.append(shots_used)

    alphas = [row.alpha for row in rows]
    A = build_sensing_matrix(alphas, columns, parameter_coefficients)

    backend = LassoRegressionBackend(seed=seed)
    x_hat = backend.fit(A, y_values)

    coefficients = _reconstruct_complex(x_hat, columns)

    run_manifest: dict[str, object] = {
        "seed": seed,
        "n_rows": len(rows),
        "shots_per_row": tuple(shots_per_row),
        "tau": tau0,
        "r": r0,
    }

    return LearnedModel(
        coefficients=coefficients,
        canonical=canonical,
        parameter_coefficients=parameter_coefficients,
        observable=observable,
        ir=ir0,
        tau=tau0,
        r=r0,
        seed=seed,
        shots_per_row=tuple(shots_per_row),
        run_manifest=run_manifest,
    )


def predict(model: LearnedModel, alpha: tuple[float, ...]) -> float:
    """FR-006: predict `y(alpha)` from a fitted model. Uses the real-form
    basis (`2*cos`, `-2*sin`) directly on each canonical coefficient's
    already-separate `.real`/`.imag` components — the running total is a
    `float` from its first assignment onward. There is no complex
    intermediate representing the prediction anywhere in this function: the
    imaginary contribution has no code path to travel through at all, it is
    not merely asserted small after the fact.
    """
    total = 0.0
    for freq in model.canonical:
        b = model.coefficients[freq]
        if all(c == 0 for c in freq):
            total += b.real
            continue
        phase = math.pi * sum(
            l * c * a for l, c, a in zip(freq, model.parameter_coefficients, alpha)
        )
        total += 2.0 * b.real * math.cos(phase) - 2.0 * b.imag * math.sin(phase)
    return total


# TODO(out-of-scope): `per_measurement_statistical_noise_bound` bounds only
# the per-row label noise on each measured `y_j` (a Hoeffding concentration
# bound, research.md R8) — it is NOT a bound on the fitted model's weights
# or coefficients. Translating this measurement-noise bound into a
# weight-space error bound on `LearnedModel.coefficients` requires the
# sensing matrix's own conditioning (e.g. its singular values or a
# restricted-isometry-style constant), which this feature does not compute
# and does not claim. That translation is future work, not implemented
# here — see `weight_space_translation_status` below, which records this on
# every returned report object, not only in this comment.
@dataclass(frozen=True)
class PacBound:
    per_measurement_statistical_noise_bound: float
    weight_space_translation_status: str = "out_of_scope_requires_sensing_matrix_conditioning"


@dataclass(frozen=True)
class TrotterBound:
    structural_approximation_bound: float


@dataclass(frozen=True)
class ErrorBoundingReport:
    """FR-007..FR-011: the PAC-style bound and the Trotter bound as two
    permanently separate figures — never combined into any blended
    error/success figure anywhere in this object or its `__str__` (FR-008).
    Noise is reported as a third, independent axis (FR-010). `__str__` is
    the report's own textual summary (FR-007 Acceptance Scenario 4) — this
    is the actual instantiated summary a caller receives, not a paraphrase
    maintained separately from the real object."""

    pac_bound: PacBound
    trotter_bound: TrotterBound
    noise_characterization: str
    scope_statement: str
    generalization_check_required: bool
    suspect_input: tuple[float, ...] | None

    def __str__(self) -> str:
        lines = [
            "Error-bounding report",
            "  PAC bound (per-measurement statistical noise bound): "
            f"{self.pac_bound.per_measurement_statistical_noise_bound:.6e}",
            "    weight-space translation status: "
            f"{self.pac_bound.weight_space_translation_status}",
            "  Trotter bound (structural approximation bound): "
            f"{self.trotter_bound.structural_approximation_bound:.6e}",
            f"  Noise characterization: {self.noise_characterization}",
            f"  Scope: {self.scope_statement}",
            f"  Generalization check required: {self.generalization_check_required}",
        ]
        if self.suspect_input is not None:
            lines.append(f"  Suspect input: {self.suspect_input}")
        return "\n".join(lines)


def _pac_bound(shots_per_row: Sequence[int], delta: float = _DEFAULT_DELTA) -> PacBound:
    """research.md R8: a single Hoeffding-type bound per measured row
    (`y_j` is now one real scalar, not a complex `b_l` — the union bound is
    over `M` rows, not `2M` real components)."""
    M = len(shots_per_row)
    min_shots = min(shots_per_row)
    value = math.sqrt(2.0 * math.log(2.0 * M / delta) / min_shots)
    return PacBound(per_measurement_statistical_noise_bound=value)


def _trotter_bound(ir: PauliEncodedCircuitIR, tau: float, r: int) -> TrotterBound:
    """research.md R9: the first-order Lie-Trotter product-formula bound,
    computed only from `tau`, `r`, and the declared Hamiltonian term
    weights/commutators — never from shot count or sample count."""
    # tie_group == 0 is used, rather than aggregating over every step, only
    # because FR-013 already guarantees this fit's rows all share one
    # identical Trotter configuration (tau, r) -- so every tie_group (step)
    # is a structurally identical repetition of the same declared terms
    # (Constitution's own tie-group-uniformity requirement, enforced by
    # PauliEncodedCircuitIR._validate_tying). Step 0 is therefore fully
    # representative of every other step, not an arbitrary or partial
    # sample of the circuit's actual Trotter structure.
    step0_terms = [g for g in ir.gates if isinstance(g, PauliTerm) and g.tie_group == 0]
    weights = [-t.coefficient * math.pi * r / tau for t in step0_terms]
    paddeds = [Pauli(_pad_to_full_width_little_endian(t.pauli, t.qubits, ir.num_qubits)) for t in step0_terms]

    total = 0.0
    n = len(step0_terms)
    for i in range(n):
        for j in range(i + 1, n):
            if not paddeds[i].commutes(paddeds[j]):
                total += abs(weights[i]) * abs(weights[j]) * 2.0
    bound = (tau**2 / r) * total
    return TrotterBound(structural_approximation_bound=bound)


def error_bounding_report(
    model: LearnedModel,
    eval_points: Sequence[tuple[tuple[float, ...], float]] = (),
    delta: float = _DEFAULT_DELTA,
) -> ErrorBoundingReport:
    """FR-007..FR-011: generate the error-bounding report for a fitted
    model. `eval_points` are caller-supplied `(alpha, exact_value)` pairs —
    this function never computes "exact dynamics" itself (it may not import
    `fourierlearn.reference`, the only module allowed to do so); a caller
    wanting to check agreement against exact dynamics obtains those exact
    values from the oracle themselves and passes them in.
    """
    pac = _pac_bound(model.shots_per_row, delta)
    trotter = _trotter_bound(model.ir, model.tau, model.r)

    generalization_required = False
    suspect_input: tuple[float, ...] | None = None
    for alpha, exact in eval_points:
        predicted = predict(model, alpha)
        if abs(predicted - exact) < trotter.structural_approximation_bound:
            generalization_required = True
            suspect_input = alpha
            break

    return ErrorBoundingReport(
        pac_bound=pac,
        trotter_bound=trotter,
        noise_characterization=(
            f"shot noise across {len(model.shots_per_row)} measured row(s), "
            f"min shots={min(model.shots_per_row)}"
        ),
        scope_statement=(
            "This report bounds statistical measurement noise (per-row) and "
            "structural Trotterization error (per-fit) as two independent "
            "figures. It does not bound hardware noise, and its PAC figure "
            "does not itself bound the fitted model's weights — see "
            "weight_space_translation_status on the PAC bound."
        ),
        generalization_check_required=generalization_required,
        suspect_input=suspect_input,
    )
