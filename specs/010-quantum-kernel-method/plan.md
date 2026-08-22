# Implementation Plan: Quantum Kernel Method for FCE (PAC-Efficient Regime)

**Branch**: `010-quantum-kernel-method` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-quantum-kernel-method/spec.md`

## Summary

Implement the thesis's quantum-kernel construction (§5.7.7-§5.7.8) as three
pieces reusing existing pipeline machinery, not a parallel one: (a) a
kernel-overlap circuit (Figure 5.8) that reuses Spec 3's
`compile_frequency_circuit` verbatim as `A(U)` behind a Hadamard-test
selector qubit choosing between two classical inputs' fixed-gate
preparations; (b) kernel ridge regression on the resulting Gram matrix,
including the noisy variant (eq. 5.79-5.94); (c) the
`Rz(α_s)YRz(α_s)`-cancellation PAC-efficiency demonstration (§5.5.2). All
three grounding claims were already verified computationally at
specify-time (spec.md FR-012, Assumptions). This plan's own Phase 0 work
(Critical Mandate 1) additionally verified, at THIS project's actual
Hoeffding shot-noise scales (2,000/20,000/200,000 shots, δ=0.01), that the
noisy-KRR bound (eq. 5.94), while never violated, is loose-to-vacuous at
low-to-moderate shot counts and only becomes informative at high shot
counts with moderate-to-strong regularization — see
[research.md](./research.md) R1. Per that mandate, this is surfaced
structurally: every noisy-KRR prediction returns a `NoisyKRRBound` result
object (research.md R2) carrying a `tightness_status` field
(`"informative"` / `"loose"` / `"vacuous"`), mirroring Spec 5's
`PacBound.weight_space_translation_status` pattern in `learn.py` — a
caller can never receive a bare bound number without its own honesty
label attached.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `src/fourierlearn/`)

**Primary Dependencies**: Qiskit (`QuantumCircuit`, `Gate`, existing
`compile_frequency_circuit`/`FixedGate`/`PauliTerm` from Specs 1-3, 9),
NumPy (Gram-matrix linear algebra, KRR solve) — no new third-party
dependency introduced.

**Storage**: N/A (in-memory circuits, arrays, and dataclasses only, matching
every prior spec in this project).

**Testing**: pytest, split as `tests/unit/` (pure-Python KRR math,
`NoisyKRRBound` construction and thresholds) and `tests/oracle/` (circuit
construction verified against `reference.py`'s exact-statevector oracle),
matching this project's existing `tests/unit` vs `tests/oracle` split.

**Target Platform**: local CPU simulation (Aer `statevector` method, per
Constitution §3.2) — no hardware execution in this feature's scope.

**Project Type**: single Python library (`src/fourierlearn/`), no
frontend/mobile component — Option 1 (Single project) from the structure
template below.

**Performance Goals**: none stated or needed; this feature's own declared
scope is small-instance (`T` up to the low tens of training points per
spec.md's Key Entities), and Constitution §5.3 prohibits introducing any
optimisation without a recorded bottleneck profile, so none is proposed.

**Constraints**: Constitution §3 (measurement-only production path — the
kernel-overlap circuit is compiled and, when finite-shot extraction is
exercised, read out via Spec 4's existing shot-based estimator, never via
`Statevector`/`Operator` outside `reference.py`/tests); Constitution §5.3
(no unprofiled optimisation); Constitution §8.3 (every noisy-KRR result
states what its bound does and does not establish); Constitution §11.11
(kernel is over classical inputs `x`, never over encoded parameters `α` —
scope discipline, spec.md FR mapping below); Constitution §11.8 (no
kernel-advantage claim on the Z₂ validation platform — any Z₂-platform
fixture is pipeline-validation only, per spec.md FR-013's own scope note).

**Scale/Scope**: Gram matrix construction is `O(T²)` overlap-circuit
evaluations for `T` training points (spec.md FR-005) — declared and
accepted as the feature's own cost, not something this plan proposes to
reduce.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Gate | Requirement | How this feature satisfies it |
|------|-------------|-------------------------------|
| §3 Measurement-only production path | No production module inspects `Statevector`/`Operator`; `reference.py` is oracle-only | The kernel-overlap circuit is built with `compile_frequency_circuit` unmodified (already CI-guarded); a new `reference.py` function (mirroring `amplitude_coefficients`/`projector_coefficients` from Spec 9) supplies the oracle-side overlap for tests only; any finite-shot kernel-estimate path reuses Spec 4's existing shot-based extractor |
| §5.1-5.3 Optimisation discipline | No optimisation without a recorded bottleneck profile | None introduced; R4 (research.md) records this explicitly — `NoisyKRRBound` construction is `O(1)`, Gram-matrix cost is the feature's own declared `O(T²)` |
| §8.3 Honest results | Every result states what it does/doesn't establish | `NoisyKRRBound.tightness_status` (research.md R2) is a required, always-populated field on every noisy-KRR prediction — this plan's own Critical Mandate 1 response |
| §11.11 Scope discipline | Kernel is over classical `x`, never encoded `α` | Kernel-overlap circuit's selector qubit chooses between two `x`-dependent fixed-gate preparations, feeding the SAME `A(U)` compiled from one fixed `α`-encoding IR (spec.md FR-002/FR-003) — verified in spec.md's own pre-FR Finding 2 |
| §11.8 No advantage claim on Z₂ platform | Any Z₂-platform fixture is pipeline-validation only | spec.md FR-013 already states this; this plan introduces no new Z₂ fixture beyond what spec.md scoped |

**Result**: PASS — no violations requiring justification. Complexity Tracking table below is empty by design.

## Project Structure

### Documentation (this feature)

```text
specs/010-quantum-kernel-method/
├── plan.md              # This file
├── research.md          # Phase 0 output — realistic-noise verification, NoisyKRRBound design
├── data-model.md        # Phase 1 output (next)
├── quickstart.md        # Phase 1 output (next)
├── contracts/           # Phase 1 output (next)
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/fourierlearn/
├── circuits.py       # existing: compile_frequency_circuit (A(U), reused unmodified)
│                     #   + NEW: compile_kernel_overlap_circuit (Figure 5.8 selector-qubit wrapper)
├── reference.py       # existing: coefficients/amplitude_coefficients/projector_coefficients
│                     #   + NEW: kernel_overlap_oracle (exact b(x)·b(x') for test comparison only)
├── kernel.py          # NEW module: Gram-matrix assembly, noiseless + noisy KRR solve,
│                     #   NoisyKRRBound dataclass (mirrors learn.py's PacBound pattern)
├── learn.py           # existing PacBound/ErrorBoundingReport pattern — referenced, not modified
└── extract.py         # existing shot-based extraction, reused for any finite-shot kernel estimate

tests/
├── unit/
│   └── test_kernel_noisy_bound_tightness.py   # NEW: reproduces research.md R1's 3-shot-count sweep
├── oracle/
│   ├── test_circuits_kernel_overlap_circuit.py # NEW: circuit vs kernel_overlap_oracle, diff-based
│   └── test_kernel_cancellation_pac_efficiency.py # NEW: Rz(a)YRz(a) ambient/support demonstration
```

**Structure Decision**: Single project (Option 1) — this feature extends
the existing `src/fourierlearn/` library with one new module (`kernel.py`)
plus two small additions to `circuits.py`/`reference.py`, following the
exact same shape every prior spec in this project has used. No new
top-level directory, package, or service boundary is introduced.

## Complexity Tracking

*No violations — table intentionally empty.*
