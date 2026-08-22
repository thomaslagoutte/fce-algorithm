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

**Spec 11 defect repair (Constitution §1.7)**: `_hadamard_test_circuit`
and `_v_l_dagger_circuit`'s controlled construction previously wrapped an
already-assembled, multi-gate block in a single `.control()` call,
forcing dense Quantum Shannon Decomposition synthesis over the block's
full qubit width — repaired to an inline, gate-by-gate controlled
assembly (`_append_controlled_block`, Constitution §5.7), proven
equivalent via the Two-Tiered Equivalence Proof (research.md R3/R4)
before being trusted.

**Speedup context, stated plainly (research.md R10)**: the resulting
**~6.0x speedup** (measured `1213.23s` mean → `201.85s` mean, each
reproduced across 2 trials) is for a SINGLE time-point, SINGLE `(n, r)`
instance, on a SINGLE laptop (Apple M1), with NO caching, NO batching, and
NO parametrized-template reuse anywhere in this module. Closing any
further gap to a different codebase's previously-reported multi-graph
performance figure is explicitly OUT OF SCOPE for this repair (Constitution
§5.3 — no optimisation without its own bottleneck profile) and is left to
a future profiling spec, not silently implied as already achieved here.

**Cost breakdown, stated plainly (research.md R9)**: `AerSimulator()`
reconstruction was measured at `0.0000s/call` in isolation — not a
meaningful cost, isolated or in context. The pre-repair baseline's
remaining, non-construction cost was `transpile()` re-optimizing the
densely-synthesized gate (`~1.02s/call` in isolation) and actual
finite-shot execution (`~1.32s/call` in isolation). Deliverable (c)'s
additive `simulator` parameter (below) is therefore a caller-configurable
backend seam, not a fix for a reconstruction-overhead bottleneck — no such
bottleneck was found to exist.
"""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator

from qiskit.circuit import Qubit

from fourierlearn import frequency
from fourierlearn.circuits import _increment_circuit, compile_observable_circuit
from fourierlearn.ir import PauliEncodedCircuitIR

_VALID_PARTS = ("real", "imag")

DEFAULT_SHOT_BUDGET = 10_000_000

# Spec 11 deliverable (b), FR-004/SC-005: explicit, named, benchmarked
# transpile() configuration -- never Qiskit's own silent default. Chosen
# by benchmarking optimization_level 0/1/2/3 against THIS repaired
# construction (research.md R5): level 1 was fastest on a 10-frequency
# sample of the documented baseline fixture (0.378s/freq, projected full
# 80.4s, vs 0.418s/89.0s for level 0, 0.563s/119.8s for level 2, and
# 0.506s/107.9s for level 3) -- a benchmarked choice, not an inherited
# default, even though it numerically matches Qiskit's own default.
_DEFAULT_OPTIMIZATION_LEVEL = 1

# `None` means "AerSimulator's own native target" -- research.md R5 found
# no explicit basis-gate override beneficial: the inline-assembled
# construction's own native gate set (`u`, `p`, `cx`, `ccx`, `mcx`) is
# already accepted by AerSimulator's default target without a forced
# re-basis step. Named explicitly here (rather than omitted from the
# transpile() call) so a reader finds a documented value, not an absence.
_DEFAULT_BASIS_GATES: list[str] | None = None


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


def _append_controlled_block(
    qc: QuantumCircuit, block: QuantumCircuit, control_qubit: Qubit, target_qubits: list[Qubit]
) -> None:
    """Spec 11 repair (Constitution §1.7/§5.7): `c-(U_K⋯U₁) = c-U_K⋯c-U₁`
    -- append `block`'s own gate sequence onto `qc`, each gate individually
    controlled by `control_qubit`, instead of wrapping the WHOLE assembled
    block in a single `.control()` call. One `.decompose()` is sufficient
    to reach only standard, natively-controllable gates (`u`, `p`, `cx`,
    `ccx`, `mcx`) for every block this module builds -- verified in-session
    (research.md R3) before this replaced the whole-block `.control()`
    calls below, not assumed from the algebraic identity alone. Used by
    BOTH the `A(U,O)`-block control and the `V_l^dagger`-block control in
    `_hadamard_test_circuit` -- neither reimplements this loop
    independently (Constitution §9.4).

    Constitution §5.3: no caching, batching, or memoization -- every call
    decomposes and re-appends its own block fresh."""
    flat = block.decompose()
    for instruction in flat.data:
        qubit_indices = [flat.find_bit(q).index for q in instruction.qubits]
        mapped_qubits = [target_qubits[i] for i in qubit_indices]
        controlled_gate = instruction.operation.control(1)
        qc.append(controlled_gate, [control_qubit] + mapped_qubits)


def _hadamard_test_circuit(circuit: QuantumCircuit, frequency: tuple[int, ...], part: str) -> QuantumCircuit:
    """The Hadamard-test circuit (research.md R2) for one target `frequency`
    tuple (one integer component per frequency register), wrapping the
    caller's already-compiled `A(U, O)` circuit (Spec 3's
    `compile_observable_circuit`, unmodified). No measurement is added here
    -- callers needing the exact (research/test-only) value evaluate this via
    `Statevector`; `estimate_coefficient` (production) adds measurement and
    executes with finite shots.

    `part` MUST be `'real'` or `'imag'`.

    Spec 11 repair (Constitution §1.7): both the `A(U,O)`-block control and
    the `V_l^dagger`-block control are appended via `_append_controlled_
    block`'s inline, gate-by-gate assembly -- NEVER a whole-block
    `.control()` call, which forces dense Quantum Shannon Decomposition
    synthesis over the block's full qubit width (the exact anti-pattern
    §1.7 names, and the measured root cause of a ~1213s, 2-trial-reproduced
    wall-clock baseline on a trivial 14-qubit instance -- research.md R1;
    repaired to a reproduced ~201.85s mean, research.md R6). Proven
    equivalent to the pre-repair construction via the Two-Tiered
    Equivalence Proof BEFORE this replacement was trusted (Constitution
    §4.1/§5.2): Tier 1 (`Operator.equiv` on small fixtures,
    `tests/unit/test_extract_hadamard_test.py`) and Tier 2 (`Statevector`
    equivalence at the actual 14-qubit baseline scale, on the all-zero and
    a Haar-random state, `tests/oracle/test_extract_hadamard_test_scale_
    equivalence.py`) -- research.md R3/R4."""
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
    target_qubits = qc.qubits[1 : 1 + circuit.num_qubits]
    _append_controlled_block(qc, circuit, had_anc[0], target_qubits)
    for component, freq_reg in zip(frequency, freq_registers):
        v_block = _v_l_dagger_circuit(component, len(freq_reg))
        _append_controlled_block(qc, v_block, had_anc[0], list(freq_reg))
    if part == "imag":
        qc.sdg(had_anc[0])
    qc.h(had_anc[0])
    return qc


def estimate_coefficient(
    circuit: QuantumCircuit,
    frequency: tuple[int, ...],
    shots: int,
    seed: int | None = None,
    simulator: AerSimulator | None = None,
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

    **`simulator` (Spec 11 deliverable c, additive)**: when `None` (the
    default), a fresh, bare `AerSimulator()` is constructed exactly as
    before this parameter existed — zero behavioral difference for any
    existing caller (FR-007). When supplied, that exact instance is used
    for execution instead, never silently replaced (FR-006/FR-007
    Acceptance Scenario 2). research.md R9 measured `AerSimulator()`
    construction at `0.0000s/call` in isolation — this parameter is a
    caller-configurable backend seam, not a fix for a reconstruction-
    overhead bottleneck, because no such bottleneck was found to exist.
    """
    if shots <= 0:
        raise ValueError(f"estimate_coefficient requires shots > 0, got {shots}")

    sim = simulator if simulator is not None else AerSimulator()
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
    # optimization_level/basis_gates are explicit, named, benchmarked
    # constants (Spec 11 deliverable b) -- never a silent default.
    real_qc = transpile(
        real_qc, sim, optimization_level=_DEFAULT_OPTIMIZATION_LEVEL, basis_gates=_DEFAULT_BASIS_GATES
    )
    imag_qc = transpile(
        imag_qc, sim, optimization_level=_DEFAULT_OPTIMIZATION_LEVEL, basis_gates=_DEFAULT_BASIS_GATES
    )

    real_kwargs = {} if seed is None else {"seed_simulator": seed}
    imag_kwargs = {} if seed is None else {"seed_simulator": seed + 1}
    real_counts = sim.run(real_qc, shots=shots, **real_kwargs).result().get_counts()
    imag_counts = sim.run(imag_qc, shots=shots, **imag_kwargs).result().get_counts()

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
    simulator: AerSimulator | None = None,
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

    **Opaque execution interface, with one additive seam (Spec 11
    deliverable c)**: this signature exposes no `transpile()`/`get_counts()`
    detail, and no per-circuit seed list — only the single, optional
    `simulator` parameter. When `None` (the default), behavior is
    IDENTICAL to before this parameter existed: each internal
    `estimate_coefficient` call constructs its own fresh, bare
    `AerSimulator()` (FR-007). When a caller supplies one instance, that
    SAME instance is passed to EVERY internal `estimate_coefficient` call
    across all canonical frequencies — never reconstructed fresh per
    frequency. This is a semantic-correctness requirement (a caller who
    configures a specific backend expects that configuration honored on
    every sub-circuit, research.md R9), not a performance optimisation:
    research.md R9 measured `AerSimulator()` construction at
    `0.0000s/call` in isolation, so there is no reconstruction-overhead
    cost this reuse is "saving." A future internal refactor introducing
    batched multi-circuit submission (an optimisation deliberately NOT
    implemented here, research.md R9/R11) could still be made without
    changing this function's calling contract at all.

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
        estimate, _ = estimate_coefficient(compiled, freq, shots, seed, simulator=simulator)
        result[freq] = estimate
        mirror = tuple(-component for component in freq)
        if mirror != freq:
            result[mirror] = estimate.conjugate()
    return result


# --- Spec 10 deliverable (a): finite-shot kernel-overlap estimation --------


def estimate_kernel_overlap(
    circuit: QuantumCircuit,
    selector_qubit: Qubit,
    circuit_reg: QuantumRegister,
    shots: int,
    seed: int | None = None,
    simulator: AerSimulator | None = None,
) -> tuple[float, int]:
    """Finite-shot estimate of `⟨Z_selector⊗I⊗|0⟩⟨0|_circuit⟩` on
    `circuits.compile_kernel_overlap_circuit`'s output — `Re(⟨b(x)|b(x')⟩)`
    (FR-002). Unlike `estimate_coefficient`'s Hadamard-test-with-`V_l^dagger`
    machinery (built for a DIFFERENT purpose — extracting one targeted
    Fourier coefficient from an observable-folded `A(U,O)` circuit), this
    observable needs no extra ancilla or controlled-`V_l^dagger` gate at
    all: a direct computational-basis measurement of every qubit already
    gives, per shot, both the selector's own outcome and whether the
    circuit register measured all-zero, from which the observable's
    expectation is the plain classical average `(+1` for `selector=0,
    circuit=0`, `-1` for `selector=1, circuit=0`, `0` otherwise`)` — reused
    directly, not derived through `estimate_coefficient`'s per-frequency
    machinery, which does not apply here (verified in-session against the
    exact `Statevector` value before this function was written: 200,000-shot
    estimate `0.46042` vs exact `0.4605304970`, well within the shot count's
    own Hoeffding tolerance).

    Returns `(estimate, shots)`, matching `estimate_coefficient`'s own
    `(estimate, shots)` return-shape convention (Constitution §5.6).

    **`simulator` (Spec 11 deliverable c, additive)**: when `None` (the
    default), a fresh, bare `AerSimulator()` is constructed exactly as
    before this parameter existed (FR-007). When supplied, that exact
    instance is used instead, never silently replaced (FR-006/FR-007
    Acceptance Scenario 2).

    Constitution §5.3: no caching, batching, or memoization — every call
    transpiles and executes its own fresh circuit."""
    if shots <= 0:
        raise ValueError(f"estimate_kernel_overlap requires shots > 0, got {shots}")

    sim = simulator if simulator is not None else AerSimulator()
    qubit_order = list(circuit.qubits)
    n = len(qubit_order)
    selector_position = qubit_order.index(selector_qubit)
    circuit_positions = [qubit_order.index(q) for q in circuit_reg]

    creg = ClassicalRegister(n, "c")
    meas_qc = circuit.copy()
    meas_qc.add_register(creg)
    meas_qc.measure(meas_qc.qubits, creg)
    meas_qc = transpile(meas_qc, sim)

    kwargs = {} if seed is None else {"seed_simulator": seed}
    counts = sim.run(meas_qc, shots=shots, **kwargs).result().get_counts()

    total = 0
    for bitstring, count in counts.items():
        # `get_counts()` keys are big-endian over the classical register: bit
        # i (measured from qubit_order[i]) is character (n-1-i) from the left
        # -- verified in-session against the exact Statevector value above,
        # not assumed from the docstring alone.
        bits = [int(bitstring[n - 1 - i]) for i in range(n)]
        if any(bits[p] != 0 for p in circuit_positions):
            continue
        total += count if bits[selector_position] == 0 else -count
    return total / shots, shots
