"""Extract layer — FR-001..FR-012.

Wraps Spec 3's compiled `A(U, O)` circuit with a Hadamard-test ancilla
(Barthe thesis Corollary 5.1/5.2) and executes it with finite shots only
(Constitution Article II/§3, §9.6): `estimate_coefficient()` is the
single-frequency primitive; `extract_coefficients()` builds the full
coefficient set from it, exploiting conjugate symmetry for a Hermitian
observable (Constitution §7.6) to avoid a redundant circuit execution for
every mirrored frequency pair.

No `Statevector`, `Operator`, or `expm` import anywhere in this module —
enforced mechanically by Spec 1's own CI import guard.
"""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

from fourierlearn import frequency
from fourierlearn.circuits import _increment_circuit, compile_observable_circuit
from fourierlearn.ir import PauliEncodedCircuitIR

_VALID_PARTS = ("real", "imag")

DEFAULT_SHOT_BUDGET = 10_000_000


class ShotBudgetExceeded(RuntimeError):
    """Raised when a full-coefficient-set extraction's predicted execution
    cost (circuits x shots) would exceed the configured budget without
    explicit confirmation (Constitution §10.3). Deliberately mirrors Spec 1's
    `CostBudgetExceeded`/`confirm=True` interface style (research.md R7) —
    defined locally here, never imported from `fourierlearn.reference`,
    which only `reference.py` itself may import (FR-001)."""


def _v_l_dagger_circuit(component: int, width: int) -> QuantumCircuit:
    """`V_l^\\dagger` for one frequency-register component: `|l|` repetitions
    of Circuits Layer's own cyclic-increment circuit (or its `.inverse()`
    for non-negative `l`) -- reused unchanged, not reimplemented
    (Constitution §9.4; research.md R2). `V_l := (V+)^l`, so
    `V_l^\\dagger = (V-)^l` for `l >= 0`, and `(V+)^{|l|}` for `l < 0`
    (since `(V-)^{-|l|} = (V+)^{|l|}`)."""
    qc = QuantumCircuit(width)
    step = _increment_circuit(width).inverse() if component >= 0 else _increment_circuit(width)
    for _ in range(abs(component)):
        qc.compose(step, inplace=True)
    return qc


def _hadamard_test_circuit(circuit: QuantumCircuit, frequency: tuple[int, ...], part: str) -> QuantumCircuit:
    """The Hadamard-test circuit (research.md R2) for one target `frequency`
    tuple (one integer component per frequency register), wrapping the
    caller's already-compiled `A(U, O)` circuit (Spec 3's
    `compile_observable_circuit`, unmodified). No measurement is added here
    -- callers needing the exact (research/test-only) value evaluate this via
    `Statevector`; `estimate_coefficient` (production) adds measurement and
    executes with finite shots.

    `part` MUST be `'real'` or `'imag'`."""
    if part not in _VALID_PARTS:
        raise ValueError(f"part must be one of {_VALID_PARTS}, got {part!r}")
    freq_registers = circuit.qregs[:-2]
    if len(frequency) != len(freq_registers):
        raise ValueError(
            f"frequency has {len(frequency)} components, but the compiled circuit has "
            f"{len(freq_registers)} frequency register(s)"
        )
    for component, freq_reg in zip(frequency, freq_registers):
        width = len(freq_reg)
        low, high = -(2 ** (width - 1)), 2 ** (width - 1) - 1
        if not (low <= component <= high):
            raise ValueError(
                f"frequency component {component} is not representable by a "
                f"{width}-qubit register (valid range [{low}, {high}])"
            )

    had_anc = QuantumRegister(1, "had_anc")
    qc = QuantumCircuit(had_anc, *circuit.qregs)
    qc.h(had_anc[0])
    qc.append(
        circuit.to_gate(label="A(U,O)").control(1),
        [had_anc[0]] + qc.qubits[1 : 1 + circuit.num_qubits],
    )
    for component, freq_reg in zip(frequency, freq_registers):
        v_gate = _v_l_dagger_circuit(component, len(freq_reg)).to_gate(label="Vl_dag").control(1)
        qc.append(v_gate, [had_anc[0]] + list(freq_reg))
    if part == "imag":
        qc.sdg(had_anc[0])
    qc.h(had_anc[0])
    return qc


def estimate_coefficient(
    circuit: QuantumCircuit,
    frequency: tuple[int, ...],
    shots: int,
    seed: int | None = None,
) -> tuple[complex, int]:
    """User Story 1 — the single-frequency Hadamard-test primitive (Barthe
    thesis Corollary 5.1/5.2): estimates one Fourier coefficient of the
    circuit's folded observable using only finite-shot measurement
    execution (`AerSimulator.run()` + `get_counts()`, Constitution §9.6) —
    never `Statevector`/`Operator` (Constitution Article II/§3.3-3.4).

    Returns `(estimate, shots)` — the exact shot count actually used is
    always returned alongside the estimate (Constitution §5.6).

    **Seed-determinism contract (part of this function's public interface,
    not an internal detail)**: when `seed` is supplied, the real-part
    circuit is run with `seed_simulator=seed` and the imaginary-part circuit
    with `seed_simulator=seed + 1`. These two seeds MUST differ so the real
    and imaginary parts' shot noise is statistically independent of each
    other -- reusing the same seed for both would spuriously correlate the
    two sampling errors. This exact offset-by-one convention is guaranteed
    and may be relied upon by callers; it is not free to change without a
    documented, deliberate contract change (research.md R5).
    """
    if shots <= 0:
        raise ValueError(f"estimate_coefficient requires shots > 0, got {shots}")

    simulator = AerSimulator()
    real_creg = ClassicalRegister(1, "c")
    imag_creg = ClassicalRegister(1, "c")

    real_qc = _hadamard_test_circuit(circuit, frequency, "real")
    real_qc.add_register(real_creg)
    real_qc.measure(real_qc.qregs[0][0], real_creg[0])

    imag_qc = _hadamard_test_circuit(circuit, frequency, "imag")
    imag_qc.add_register(imag_creg)
    imag_qc.measure(imag_qc.qregs[0][0], imag_creg[0])

    # transpile() is required, not optional: Aer rejects an un-transpiled
    # controlled custom-gate circuit (research.md R5's own recorded finding).
    real_qc = transpile(real_qc, simulator)
    imag_qc = transpile(imag_qc, simulator)

    real_kwargs = {} if seed is None else {"seed_simulator": seed}
    imag_kwargs = {} if seed is None else {"seed_simulator": seed + 1}
    real_counts = simulator.run(real_qc, shots=shots, **real_kwargs).result().get_counts()
    imag_counts = simulator.run(imag_qc, shots=shots, **imag_kwargs).result().get_counts()

    p0_re = real_counts.get("0", 0) / shots
    p1_re = real_counts.get("1", 0) / shots
    p0_im = imag_counts.get("0", 0) / shots
    p1_im = imag_counts.get("1", 0) / shots
    return complex(p0_re - p1_re, p0_im - p1_im), shots


def _is_canonical_representative(freq: tuple[int, ...]) -> bool:
    """Picks, for each mirrored pair `{f, -f}`, exactly one of the two to
    estimate directly: the one whose first nonzero component is positive.
    The all-zero (DC) tuple is its own mirror and is always treated as
    canonical (estimated directly, never derived)."""
    for component in freq:
        if component > 0:
            return True
        if component < 0:
            return False
    return True


def extract_coefficients(
    ir: PauliEncodedCircuitIR,
    observable: SparsePauliOp,
    shots: int,
    seed: int | None = None,
    budget: int = DEFAULT_SHOT_BUDGET,
    confirm: bool = False,
) -> dict[tuple[int, ...], complex]:
    """User Story 2 — the full Fourier-coefficient-set extraction, built
    entirely from `estimate_coefficient()` (User Story 1): compiles the
    circuit once (Spec 3's `compile_observable_circuit`, reused unchanged),
    determines every representable frequency from the IR's own parameter
    structure (`frequency.pre_parity_range`, Spec 1, reused not redefined),
    and directly estimates only the non-mirrored half of them plus the
    always-direct DC term — the remaining half is derived by complex
    conjugation, exploiting the conjugate-symmetry identity a Hermitian
    observable's real-valued expectation function guarantees (Constitution
    §7.6; research.md R4).

    **Hermiticity precondition — checked here, not merely asserted
    elsewhere**: `observable` is this function's own direct parameter,
    independent of whatever `ir.observable` may separately be (matching
    Circuits Layer's own `compile_observable_circuit(ir, observable)`
    signature) — nothing upstream forces a caller to route it through Spec
    1's Hermiticity-validating IR constructor first. This check is therefore
    genuinely reachable via the public API, not unreachable defense-in-depth:
    a caller can construct and pass an arbitrary non-Hermitian
    `SparsePauliOp` directly, with no IR involved in building it at all.

    **Opaque execution interface**: this signature exposes no
    `AerSimulator`/`transpile()`/`get_counts()` detail whatsoever — no
    backend object, no raw counts, no per-circuit seed list. A future
    internal refactor introducing batched multi-circuit submission (an
    optimisation deliberately NOT implemented here, research.md R9) could
    be made without changing this function's calling contract at all.

    Raises `ValueError` if `observable` is not Hermitian, or `shots` is not
    a positive integer. Raises `ShotBudgetExceeded` if the predicted total
    execution cost (number of directly-estimated frequencies x 2 sub-circuits
    x shots) exceeds `budget`, unless `confirm=True` (Constitution §10.3;
    research.md R7 — mirrors Spec 1's `CostBudgetExceeded`/`confirm=True`
    interface style).
    """
    if observable != observable.adjoint():
        raise ValueError(
            "extract_coefficients requires a Hermitian observable — the "
            "conjugate-symmetry shortcut (b_{-l} = conj(b_l)) only holds "
            "because a Hermitian observable's expectation function is real "
            "(Constitution §7.6); a non-Hermitian observable was supplied"
        )
    if shots <= 0:
        raise ValueError(f"extract_coefficients requires shots > 0, got {shots}")

    domain_per_axis = [
        list(frequency.pre_parity_range(p.multiplicity, p.upload_count)) for p in ir.parameters()
    ]
    all_frequencies: list[tuple[int, ...]] = [()]
    for axis_values in domain_per_axis:
        all_frequencies = [prefix + (value,) for prefix in all_frequencies for value in axis_values]

    canonical = [f for f in all_frequencies if _is_canonical_representative(f)]
    predicted_cost = len(canonical) * 2 * shots
    if predicted_cost > budget and not confirm:
        raise ShotBudgetExceeded(
            f"Extracting {len(canonical)} independent frequencies at {shots} shots each "
            f"(2 sub-circuits per frequency) would require {predicted_cost} total shots, "
            f"exceeding budget {budget}. Pass confirm=True to proceed anyway (§10.3)."
        )

    compiled = compile_observable_circuit(ir, observable)

    result: dict[tuple[int, ...], complex] = {}
    for freq in canonical:
        estimate, _ = estimate_coefficient(compiled, freq, shots, seed)
        result[freq] = estimate
        mirror = tuple(-component for component in freq)
        if mirror != freq:
            result[mirror] = estimate.conjugate()
    return result
