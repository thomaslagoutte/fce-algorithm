"""Cross-Topology Regression Layer — Spec 12, FR-001..FR-014.

Restores the pipeline Spec 5 was originally meant to build, after Spec 5's
own, already-documented drift (`specs/005-learning-backend-layer/spec.md`
Clarifications; research.md R1) into the thesis's "flipped concept" `C̄`
(Barthe thesis §5.7.10): a training row here is `(x_t, y_t)` — a classical-
input/topology declaration and its label — NEVER `(alpha_j, y_j)` for one
fixed circuit with a bound numeric parameter value. Each row's feature
vector `b(x_t)` is obtained via a genuinely SEPARATE call to Spec 4's own
`extract.extract_coefficients` (Spec-11-execution-repaired) on that
topology's own compiled circuit.

**Non-reuse boundary (FR-003, Critical Mandate)**: this module MUST NOT
import `fourierlearn.learn`'s `estimate_y`, `TrainingRow`, `build_sensing_
matrix`, `LassoRegressionBackend`, or `fit_model` — enforced by a
dedicated, automated AST-scan test
(`tests/unit/test_cross_topology_no_learn_reuse.py`), not by this
docstring alone. `learn.py` itself is not modified or deprecated by this
module: it remains a correct answer to a different (flipped, classically-
easy) question.

**Relationship to Spec 10 (research.md R2/R3, FR-013)**: this feature and
Spec 10 (Quantum Kernel Method) solve the SAME underlying linear model
(thesis §5.7.8 eq. 5.79: `y = x^⊤w`) via two different routes — Spec 10's
kernel ridge regression is the implicit/dual route; this feature's LASSO
fit is the explicit/primal/sparse route. They are complementary, not
duplicates. Executed cross-check (research.md R3): on a shared fixture,
the two routes do NOT produce identical predictions (mean divergence
`2.8e-4` at `T=5` under-determined, `6e-5` at `T=12` well-determined) —
this is an expected, legitimate consequence of L1 vs. L2 regularization,
never asserted as floating-point equality. Both track the true, noiseless
dynamics to within `<1e-3` in that check. This is also WHY the shared-
fixture cross-check (`tests/oracle/test_cross_topology_krr_crosscheck.py`)
reuses Spec 10's generic, feature-agnostic `kernel.py` machinery
(`build_gram_matrix`/`krr_fit_predict`) applied to THIS module's own
`extract_feature_vector` output — never Spec 10's own amplitude-based
circuit/oracle, which research.md R2 found computes a numerically
DIFFERENT `b(x)` object for the same circuit (different frequency support,
different values — an honest, executed finding, not a defect in either
spec).

Constitution §5.3: no caching, batching, or memoization anywhere in this
module — every function recomputes fresh per call, unprofiled and by
design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import numpy.typing as npt
from sklearn.linear_model import LassoCV
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

from fourierlearn import frequency as _frequency
from fourierlearn.extract import extract_coefficients
from fourierlearn.ir import PauliEncodedCircuitIR


@dataclass(frozen=True)
class CrossTopologyRow:
    """One training row: `(x_t, y_t)` (FR-001) — `x_t` is a classical-
    input/topology declaration (an `ir` selecting its own fixed gates
    within an otherwise-shared encoded-parameter structure, Constitution
    §7.1), `y_t` is its real-valued label. There is no field here whose
    semantics is "a bound encoded-parameter assignment" — that is
    precisely `learn.py`'s own, already-drifted row model (FR-001's own
    negative example), not this one."""

    ir: PauliEncodedCircuitIR
    label: float


# --- FR-014: frequency-lattice alignment -----------------------------------


class FrequencyLatticeMismatchError(ValueError):
    """Raised when two training rows' IRs do not share an identical
    frequency lattice (FR-014) — the general, directly-checkable mechanism
    FR-008's Trotter-configuration check is one instance of. The message
    ALWAYS names the exact `parameter_index` and the exact field
    (`upload_count`, `multiplicity`, or `coefficients`) that mismatched —
    never a generic "lattices differ" message (this round's Critical
    Mandate 1)."""


def _frequency_lattice_signature(ir: PauliEncodedCircuitIR) -> tuple[object, ...]:
    """A hashable signature of an IR's own frequency-lattice structure
    (research.md R4): everything `extract_coefficients`'s own frequency-
    domain construction (`frequency.pre_parity_range` per parameter,
    `_is_canonical_representative`) depends on. Two IRs sharing this
    signature produce an IDENTICAL canonical frequency list by
    construction — this signature IS that list's own generator input, not
    a separate, possibly-drifting duplicate check."""
    params = ir.parameters()  # Spec 1's own coordinate_order, order is significant
    return tuple(
        (p.index, p.upload_count, p.multiplicity, p.coefficients) for p in params
    ) + (ir.num_qubits,)


def validate_lattice_alignment(rows: Sequence[CrossTopologyRow]) -> None:
    """FR-014: validate, before any design matrix is assembled, that
    EVERY row's IR shares the exact same frequency lattice as the first
    row's. Raises `FrequencyLatticeMismatchError` naming the exact
    `parameter_index` and field that mismatched on the first disagreement
    found — never proceeds silently.

    Constitution §5.3: no caching — every call recomputes every row's own
    signature fresh."""
    if not rows:
        raise ValueError("validate_lattice_alignment requires at least one row")

    reference_ir = rows[0].ir
    reference_signature = _frequency_lattice_signature(reference_ir)
    reference_params = reference_ir.parameters()
    reference_num_qubits = reference_ir.num_qubits

    for row_index, row in enumerate(rows[1:], start=1):
        if _frequency_lattice_signature(row.ir) == reference_signature:
            continue  # fast path: identical lattice, no mismatch to diagnose
        params = row.ir.parameters()
        if row.ir.num_qubits != reference_num_qubits:
            raise FrequencyLatticeMismatchError(
                f"frequency lattice mismatch between row 0 and row {row_index}: "
                f"field='num_qubits' row[0]={reference_num_qubits!r} "
                f"row[{row_index}]={row.ir.num_qubits!r}"
            )
        if len(params) != len(reference_params):
            raise FrequencyLatticeMismatchError(
                f"frequency lattice mismatch between row 0 and row {row_index}: "
                f"field='num_parameters' row[0]={len(reference_params)!r} "
                f"row[{row_index}]={len(params)!r}"
            )
        for ref_p, p in zip(reference_params, params):
            if ref_p.index != p.index:
                raise FrequencyLatticeMismatchError(
                    f"frequency lattice mismatch between row 0 and row {row_index}: "
                    f"field='index' row[0]={ref_p.index!r} row[{row_index}]={p.index!r}"
                )
            for field in ("upload_count", "multiplicity", "coefficients"):
                ref_value = getattr(ref_p, field)
                value = getattr(p, field)
                if ref_value != value:
                    raise FrequencyLatticeMismatchError(
                        f"frequency lattice mismatch between row 0 and row {row_index} "
                        f"at parameter_index={ref_p.index}: field={field!r} "
                        f"row[0]={ref_value!r} row[{row_index}]={value!r}"
                    )


# --- FR-002: per-row feature extraction (Spec 4, unmodified) --------------


def extract_feature_vector(
    ir: PauliEncodedCircuitIR,
    observable: SparsePauliOp,
    shots: int,
    seed: int | None = None,
    simulator: AerSimulator | None = None,
) -> dict[tuple[int, ...], complex]:
    """FR-002: one row's `b(x_t)` — a genuinely SEPARATE call to Spec 4's
    `extract_coefficients` on `ir`'s own compiled circuit. Never a bound-
    parameter read of a shared circuit (that is `learn.py`'s own `estimate_
    y`, which this module does not import and does not call).

    Constitution §5.3: no caching — every call compiles and measures its
    own circuit fresh."""
    return extract_coefficients(ir, observable, shots, seed=seed, simulator=simulator)


# --- FR-006: conjugate-symmetric real stacking -----------------------------


def canonical_frequencies(ir: PauliEncodedCircuitIR) -> list[tuple[int, ...]]:
    """The same canonical (non-mirrored, plus always-direct DC) frequency
    list `extract_coefficients` itself targets directly, reused via the
    same `frequency.pre_parity_range` domain construction (Spec 1) and the
    same canonical-representative rule `extract.py` already defines --
    not a second, independently-derived list."""
    from fourierlearn.extract import _is_canonical_representative

    domain_per_axis = [
        list(_frequency.pre_parity_range(p.multiplicity, p.upload_count)) for p in ir.parameters()
    ]
    all_frequencies: list[tuple[int, ...]] = [()]
    for axis_values in domain_per_axis:
        all_frequencies = [prefix + (value,) for prefix in all_frequencies for value in axis_values]
    return [f for f in all_frequencies if _is_canonical_representative(f)]


def stack_real(coeffs: dict[tuple[int, ...], complex], canonical: Sequence[tuple[int, ...]]) -> npt.NDArray[np.float64]:
    """FR-006: stack the real and imaginary parts of each canonical
    (non-DC) frequency's coefficient as two real columns, plus one real
    column for the always-real DC term (`(0,)*d`) — this module's OWN
    implementation (original code, not imported from `learn.py`'s
    `_stack_real`), even though it reuses the same underlying conjugate-
    symmetry identity Constitution §7.6 already establishes."""
    out: list[float] = []
    for freq in canonical:
        value = coeffs.get(freq, 0j)
        if all(component == 0 for component in freq):
            out.append(value.real)
        else:
            out.append(value.real)
            out.append(value.imag)
    return np.array(out, dtype=np.float64)


def reconstruct_complex(
    stacked: npt.NDArray[np.float64], canonical: Sequence[tuple[int, ...]]
) -> dict[tuple[int, ...], complex]:
    """The inverse of `stack_real`: reconstruct one complex coefficient
    per canonical frequency (plus its mirror, via conjugate symmetry) from
    a real-stacked vector of the same layout `stack_real` produces."""
    result: dict[tuple[int, ...], complex] = {}
    position = 0
    for freq in canonical:
        if all(component == 0 for component in freq):
            value = complex(stacked[position], 0.0)
            position += 1
        else:
            value = complex(stacked[position], stacked[position + 1])
            position += 2
        result[freq] = value
        mirror = tuple(-component for component in freq)
        if mirror != freq:
            result[mirror] = value.conjugate()
    return result


# --- FR-004/FR-009: LASSO fit across topologies, honestly under-determined -

# Constitution §7.4/§7.7 (the "t^2-penalty bug" guardrail, generalized here
# from Spec 5's Trotter-evolution-time framing to this pipeline's own
# shot-noise axis, per FR-009): an explicit, version-pinned candidate grid
# and a fixed CV fold count -- NEVER a function of shot count, label noise,
# or any other quantity belonging to a different error source. Deliberately
# original code (not imported from `learn.py`'s own, differently-named
# `_ALPHA_GRID`/`_K_DEFAULT_FOLDS`), mirroring the SAME data-driven-grid
# design pattern, per FR-003's non-reuse boundary.
_ALPHA_GRID: npt.NDArray[np.float64] = np.geomspace(1e-4, 1.0, 30)
_K_DEFAULT_FOLDS = 5


@dataclass(frozen=True)
class CrossTopologyModel:
    """FR-004's fitted output: a sparse real-stacked weight vector `ŵ`
    over the shared canonical frequency basis, plus the metadata
    `predict` needs to extract a held-out topology's own `b(x*)` via the
    identical path (FR-005).

    **Structural enforcement (mirrors Spec 6's `PhysicalModelDescription`
    precedent)**: `__post_init__` re-asserts the Hermitian-observable
    invariant `fit_cross_topology_lasso` already checks at fit time — this
    makes the guarantee hold for *every* code path that could ever produce
    a `CrossTopologyModel`, including direct construction in a test or a
    future caller, not only the one factory function that happens to
    check it today."""

    weights: npt.NDArray[np.float64]
    canonical: tuple[tuple[int, ...], ...]
    observable: SparsePauliOp
    training_topologies: tuple[PauliEncodedCircuitIR, ...]

    def __post_init__(self) -> None:
        if self.observable != self.observable.adjoint():
            raise ValueError(
                "CrossTopologyModel requires a Hermitian observable — the "
                "real/imaginary stacking convention (FR-006) only holds for "
                "a Hermitian observable's real-valued expectation function"
            )


def fit_cross_topology_lasso(
    rows: Sequence[CrossTopologyRow],
    observable: SparsePauliOp,
    shots: int,
    seed: int | None = None,
    simulator: AerSimulator | None = None,
) -> CrossTopologyModel:
    """FR-004: fit a sparse weight vector `w(α*)` via LASSO across the
    collected `{(b(x_t), y_t)}` pairs, honestly supporting `T` topologies
    strictly fewer than the number of representable frequencies as the
    intended operating mode (Constitution §7.3) -- never raising, warning,
    or otherwise guarding against "too few" training topologies.

    FR-014: validates every row's frequency-lattice alignment BEFORE
    assembling the design matrix -- a mismatched row is rejected with a
    surgical `FrequencyLatticeMismatchError`, never silently included.

    Constitution §5.3: no caching -- every call re-extracts every row's
    own feature vector and re-fits from scratch."""
    if observable != observable.adjoint():
        raise ValueError(
            "fit_cross_topology_lasso requires a Hermitian observable — the "
            "conjugate-symmetry stacking convention (FR-006) only holds for "
            "a Hermitian observable's real-valued expectation function"
        )
    if not rows:
        raise ValueError("fit_cross_topology_lasso requires at least one training row")

    validate_lattice_alignment(rows)

    canonical = canonical_frequencies(rows[0].ir)
    design_rows = []
    labels = []
    for row in rows:
        coeffs = extract_feature_vector(row.ir, observable, shots, seed=seed, simulator=simulator)
        design_rows.append(stack_real(coeffs, canonical))
        labels.append(row.label)

    design_matrix = np.array(design_rows, dtype=np.float64)
    y = np.array(labels, dtype=np.float64)

    cv = min(_K_DEFAULT_FOLDS, design_matrix.shape[0])
    model = LassoCV(alphas=_ALPHA_GRID, cv=cv, fit_intercept=False, random_state=seed, selection="cyclic", max_iter=10_000)
    model.fit(design_matrix, y)

    return CrossTopologyModel(
        weights=model.coef_,
        canonical=tuple(canonical),
        observable=observable,
        training_topologies=tuple(row.ir for row in rows),
    )


# --- FR-005/FR-010/FR-011: held-out prediction ------------------------------


def assert_held_out_disjoint(training_topologies: Sequence[PauliEncodedCircuitIR], x_star: PauliEncodedCircuitIR) -> None:
    """FR-010: assert, after any training/held-out split is generated,
    that `x_star` does not appear in the training set — checked
    explicitly, never assumed (Constitution §7.8)."""
    for topology in training_topologies:
        if topology == x_star:
            raise ValueError(
                "held-out topology x_star appears in the training set — "
                "Constitution §7.8 requires this be checked explicitly, "
                "never assumed"
            )


def predict(
    model: CrossTopologyModel,
    x_star: PauliEncodedCircuitIR,
    shots: int,
    seed: int | None = None,
    simulator: AerSimulator | None = None,
) -> float:
    """FR-005: `ŷ* = b(x*)^⊤ŵ`, extracting `b(x*)` via the IDENTICAL
    `extract_feature_vector` call path every training row uses (never a
    distinct prediction-time extraction mechanism). FR-011: the model's
    own observable must be Hermitian (already checked at fit time,
    FR-006's stacking convention depends on it) — this function does not
    re-derive the model, so it trusts that check rather than repeating it
    wastefully; a model built from a non-Hermitian observable could not
    exist in the first place (`fit_cross_topology_lasso` rejects it)."""
    assert_held_out_disjoint(model.training_topologies, x_star)
    coeffs = extract_feature_vector(x_star, model.observable, shots, seed=seed, simulator=simulator)
    x_star_stacked = stack_real(coeffs, model.canonical)
    return float(x_star_stacked @ model.weights)
