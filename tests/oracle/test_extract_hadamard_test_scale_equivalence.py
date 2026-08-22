"""Spec 11 T002 — the Two-Tiered Equivalence Proof's Tier 2 (Scale
Correctness, FR-013). Runs UNCONDITIONALLY as part of the default test
suite: no `@pytest.mark.skip`, `@pytest.mark.slow`, or any other
conditional marker bypasses it during a standard `pytest tests/` run
(this round's own Critical Implementation Mandate 1 — this repository has
no slow/optional-suite marker mechanism to begin with, and this test is
not the first to accept a genuinely slow, unmarked cost directly in this
tree: `tests/oracle/test_containment_omega_subset_lambda.py`'s own
deliberately-slower `r=2` fixture is the established precedent, research.md
verified against Spec 3's own research.md R5.7 for the specific
`Statevector`-at-intractable-scale substitution used here).

At the documented 14-qubit baseline scale (`n=3` TFIM, `r=2` Trotter
steps, `t=1.09`), a full `Operator()` reconstruction is intractable (a
`2^14 x 2^14` dense matrix, per Spec 3's research.md R5.7 and this spec's
own Clarifications) -- so this compares the pre-repair (`.control()`-
based) construction against the current, repaired `_hadamard_test_circuit`
via `Statevector` instead, on the all-zero state and a Haar-random state,
for both `real` and `imag` parts. Expected to be extremely slow to
evaluate on the OLD side specifically (research.md R4 measured up to
~875s for one such evaluation) -- an accepted, one-time verification cost
paid in full here, not avoided by substituting a smaller, unrepresentative
fixture (spec.md Assumptions).
"""

from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import SparsePauliOp, Statevector, random_statevector

from fourierlearn.circuits import _increment_circuit, compile_observable_circuit
from fourierlearn.extract import _hadamard_test_circuit

_VALID_PARTS = ("real", "imag")
_HAAR_RANDOM_SEED = 11


def _pre_repair_v_l_dagger_circuit(component: int, width: int) -> QuantumCircuit:
    """Frozen, byte-for-byte copy of `extract._v_l_dagger_circuit` as it
    existed before Spec 11's repair (permanent Tier 2 reference, mirrors
    `tests/unit/test_extract_hadamard_test.py`'s own frozen copy)."""
    qc = QuantumCircuit(width)
    step = _increment_circuit(width).inverse() if component >= 0 else _increment_circuit(width)
    for _ in range(abs(component)):
        qc.compose(step, inplace=True)
    return qc


def _pre_repair_hadamard_test_circuit(circuit: QuantumCircuit, frequency: tuple[int, ...], part: str) -> QuantumCircuit:
    """Frozen, byte-for-byte copy of `extract._hadamard_test_circuit` as it
    existed before Spec 11's repair -- the Constitution §1.7 violation this
    whole spec exists to repair, permanently retained here as Tier 2's own
    reference construction."""
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
        v_gate = _pre_repair_v_l_dagger_circuit(component, len(freq_reg)).to_gate(label="Vl_dag").control(1)
        qc.append(v_gate, [had_anc[0]] + list(freq_reg))
    if part == "imag":
        qc.sdg(had_anc[0])
    qc.h(had_anc[0])
    return qc


def _documented_baseline_ir():
    """The exact documented baseline fixture (`n=3` TFIM, `r=2` Trotter
    steps, `t=1.09`), reusing `tfim_dynamics_sweep_profile.py`'s own
    fixture-construction functions unmodified (repo root, "BASELINE
    PROFILING ONLY") -- not re-derived for this test."""
    import pathlib
    import sys

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    from tfim_dynamics_sweep_profile import N_SITES, OBSERVABLE_LABEL, R_STEPS, get_tfim_ir

    observable = SparsePauliOp(OBSERVABLE_LABEL)
    ir = get_tfim_ir(n=N_SITES, tau=1.09, r=R_STEPS, obs=observable)
    return ir, observable


def test_tier2_statevector_equivalence_at_actual_baseline_scale() -> None:
    """FR-013 (Tier 2, Scale Correctness): the pre-repair and repaired
    `_hadamard_test_circuit` constructions produce equivalent statevectors
    at the ACTUAL documented 14-qubit baseline scale, on the all-zero
    state and a Haar-random state, for both real and imaginary parts --
    4 checks total, reproducing research.md R4's 4/4 result against the
    real, shipped construction (not only the scratch prototype it was
    first proven on)."""
    ir, observable = _documented_baseline_ir()
    compiled = compile_observable_circuit(ir, observable)
    freq_registers = compiled.qregs[:-2]
    frequency = tuple(0 for _ in freq_registers)

    checked = 0
    for part in _VALID_PARTS:
        old_qc = _pre_repair_hadamard_test_circuit(compiled, frequency, part)
        new_qc = _hadamard_test_circuit(compiled, frequency, part)
        assert old_qc.num_qubits == new_qc.num_qubits

        n = old_qc.num_qubits
        zero_state = Statevector.from_label("0" * n)
        old_sv_zero = zero_state.evolve(old_qc)
        new_sv_zero = zero_state.evolve(new_qc)
        assert old_sv_zero.equiv(new_sv_zero), f"all-zero state mismatch, part={part}"
        checked += 1

        random_init = random_statevector(2**n, seed=_HAAR_RANDOM_SEED)
        old_sv_rand = random_init.evolve(old_qc)
        new_sv_rand = random_init.evolve(new_qc)
        assert old_sv_rand.equiv(new_sv_rand), f"Haar-random state mismatch, part={part}"
        checked += 1

    assert checked == 4
