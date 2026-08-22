# Implementation Plan: Execution Configuration and Controlled-Circuit Defect Repair

**Branch**: `011-execution-config-repair` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-execution-config-repair/spec.md`

## Summary

Repair a genuine Constitution §1.7 violation in `extract.py`'s
`_hadamard_test_circuit` and `_v_l_dagger_circuit` (each wraps an
already-assembled, multi-gate block in a single `.control()` call, forcing
dense Quantum Shannon Decomposition synthesis over the block's full qubit
width), replace it with an inline, gate-by-gate controlled assembly per
Constitution §5.7, make `transpile()`'s configuration explicit, and add an
additive `simulator` parameter to the three affected functions. Phase 0
research (research.md) executed all of this feature's own proof and
benchmark obligations before this plan was finalized: a fresh, 2-trial
re-baseline of the OLD code (mean `1213.23s`, matching the documented
`1108.00s` within expected variance) run strictly BEFORE any correctness
work (Critical Mandate 1); the Two-Tiered Equivalence Proof (Tier 1: 20/20
small-fixture `Operator.equiv` checks passed; Tier 2: 4/4 actual-14-qubit-
scale `Statevector` checks passed, on both the all-zero and a Haar-random
state); an `optimization_level` sweep (`0,1,2,3`) on the repaired
construction, numerically selecting `1`; and a fresh, 2-trial "after"
benchmark (mean `201.85s`) — a reproduced **~6.0x speedup**, entirely from
the construction-pattern fix and the now-deliberate `transpile()`
configuration, with zero new optimisation techniques introduced (Critical
Mandate 4).

**Plainly stated (research.md R9/R10)**: the remaining ~58-72% of the old
baseline not attributable to construction cost is `transpile()`
(`~1.02s/call` in isolation, re-optimizing the dense-synthesized gate)
plus actual finite-shot execution (`~1.32s/call`) — `AerSimulator()`
reconstruction itself measured at `0.0000s/call`, i.e. not a real cost at
all, so deliverable (c) does not "resolve" it because nothing there needs
resolving; deliverable (c)'s own value is a caller-configurable backend
seam, not a fix for a bottleneck that does not exist. And the measured
~6.0x speedup is for ONE time-point, ONE `(n,r)` instance, on ONE laptop,
with no caching/batching/template-reuse on either side of the comparison —
closing any further gap to a different codebase's previously-reported
multi-graph performance figure is explicitly out of this spec's scope
(Critical Mandate 4) and left to a future profiling spec.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `src/fourierlearn/`).

**Primary Dependencies**: Qiskit / Qiskit Aer (`AerSimulator`, `transpile`,
`Gate.control()`) — no new third-party dependency introduced.

**Storage**: N/A (in-memory circuits and arrays, matching every prior
spec).

**Testing**: pytest, `tests/unit/` and `tests/oracle/` — this feature adds
its Tier 1 proof to `tests/unit/test_extract_hadamard_test.py` (already
the home of this exact obligation) and its Tier 2 proof as a NEW,
permanent test in `tests/oracle/` (see Constitution Check and Project
Structure below — Critical Research Mandate 3 requires this to run in the
DEFAULT suite, never an optional or "slow" one, and this project has no
such optional-suite mechanism to begin with: no `pytest.ini`/marker
convention exists in this repo today).

**Target Platform**: local CPU simulation (Aer, Constitution §3.2) —
matches every prior spec; this feature's own benchmark hardware was a
single Apple M1 (research.md's own "ordinary consumer hardware" scope,
Assumptions).

**Project Type**: single Python library (`src/fourierlearn/`) — repairs
existing `extract.py`, no new module.

**Performance Goals**: none newly imposed by this plan beyond what
research.md already measured and reported (§5.5) — the repaired
construction's own ~6.0x speedup is a RESULT, not a target this plan
commits to exceeding further (Critical Mandate 4: no additional
optimisation without its own bottleneck profile).

**Constraints**: Constitution §1.7 (no `.control()` on a block beyond a
few qubits — the defect this plan repairs); §5.7 (gate-by-gate controlled
assembly, `c-(U_K⋯U₁)=c-U_K⋯c-U₁`); §5.2 (every circuit change ships with
an equivalence proof — satisfied by the Two-Tiered Equivalence Proof,
research.md R3/R4); §5.3 (no optimisation without its own profile — R2's
executed profile IS this fix's own bottleneck evidence; nothing beyond
FR-001/002/004/006 is introduced); §5.4/§5.5 (every default cites its own,
fresh benchmark — R5/R7); §4.1 (validate against ground truth — R8).

**Scale/Scope**: the documented baseline (`n=3, r=2, shots=20000, t=1.09`
→ 14 qubits, 425 frequencies, 850 circuits) is this feature's own declared
benchmark scale; no larger scale is targeted or claimed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Gate | Requirement | How this feature satisfies it |
|------|-------------|-------------------------------|
| §1.7 | Never wrap a circuit block beyond a few qubits in `.control()` | FR-001/FR-002 replace both violation sites with inline, gate-by-gate controlled assembly (research.md R3) — the defect this entire feature exists to repair |
| §5.7 | Controlled constructions assembled gate-by-gate, `c-(U_K⋯U₁)=c-U_K⋯c-U₁` | Literal implementation basis for FR-001/FR-002 (research.md R3: one `.decompose()` reaches only natively-controllable gates for every block this module builds) |
| §5.2 | Every circuit optimisation ships with an equivalence proof | Two-Tiered Equivalence Proof (FR-003/FR-012/FR-013) — Tier 1 `Operator.equiv` (20/20 passed) + Tier 2 `Statevector` at actual scale (4/4 passed), executed BEFORE this plan finalized (research.md R3/R4) |
| §5.3 | No optimisation without a recorded profile of the live bottleneck | research.md R2 profiles the ACTUAL live path (`extract_coefficients`'s own repeated `_hadamard_test_circuit` construction), not an alternative/abandoned one; R9 confirms no optimisation beyond FR-001/002/004/006 was introduced |
| §5.4/§5.5 | Device/parallelism/timing defaults benchmarked on target hardware, reported with hardware/qubits/depth/circuits/shots, reproduced ≥2 trials | R1 (before, 2 trials), R6 (after, 2 trials), R5 (optimization_level sweep) — all on this codebase's own post-repair circuit shapes, on the actual benchmark hardware (Apple M1); R7 explicitly declines to promote any device/parallelism default absent its own fresh benchmark, rather than inheriting one |
| §4.1 | Validate against exact ground truth before composing | R8: the repaired pipeline's output matches `reference.coefficients` within shot-noise tolerance on the existing mandated fixture |
| §8.3 | State what is and is not established | research.md R6's own "Honest caveat" reports the sample-based projection's gap from the actual full-scale result; R9 reports its own isolated-profiling-vs-measured-total mismatch (~1.9x) directly rather than smoothing it over; R10 plainly scopes the ~6.0x speedup to a single time-point/instance/laptop and explicitly excludes closing the gap to a different codebase's multi-graph figure |

**Result**: PASS — no violations requiring justification. Complexity Tracking table below is empty by design.

## Project Structure

### Documentation (this feature)

```text
specs/011-execution-config-repair/
├── plan.md              # This file
├── research.md          # Phase 0 output — re-baseline, Two-Tiered Equivalence Proof, opt-level sweep, after-benchmark
├── data-model.md        # Phase 1 output (next, if warranted — see note below)
├── quickstart.md        # Phase 1 output (next)
├── contracts/           # Phase 1 output (next, if warranted)
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

*Note on Phase 1*: this feature repairs existing functions' internal
construction and adds three narrow, additive parameters — it introduces no
new entity, no new public interface surface beyond `simulator: AerSimulator
| None = None`, and no new external contract. `data-model.md`/`contracts/`
are therefore expected to be thin-to-empty at `/speckit-tasks` time; this
is a property of the feature's own small, well-bounded scope, not an
omission.

### Source Code (repository root)

```text
src/fourierlearn/
├── extract.py       # REPAIRED: _hadamard_test_circuit, _v_l_dagger_circuit's
│                     #   .control() call sites replaced by inline, gate-by-gate
│                     #   controlled assembly (a new shared helper, e.g.
│                     #   _append_controlled_block, per Constitution §9.4 --
│                     #   used by both repair sites, not duplicated);
│                     #   explicit optimization_level/basis_gates constants
│                     #   on transpile(); additive `simulator` parameter on
│                     #   estimate_coefficient and extract_coefficients.
│                     #   estimate_kernel_overlap (Spec 10, ALSO defined in
│                     #   extract.py, not circuits.py -- corrected during
│                     #   implementation, this file originally mis-stated
│                     #   its location) -- this function does not use
│                     #   _hadamard_test_circuit at all, so FR-001/002/003/012/
│                     #   013 do not apply to it; only FR-006/FR-007 (deliverable c) do.

tests/
├── unit/
│   └── test_extract_hadamard_test.py   # EXTENDED: Tier 1 proof (FR-012) added
│                                        #   alongside its existing equivalence tests
├── oracle/
│   ├── test_extract_hadamard_test_scale_equivalence.py  # NEW, PERMANENT, in the
│   │     DEFAULT suite (Critical Research Mandate 3 -- explicitly NOT marked
│   │     slow/optional; this repo has no such marker mechanism to begin with):
│   │     Tier 2 proof (FR-013) at the actual 14-qubit baseline scale, citing
│   │     Spec 3's own research.md R5.7 (verified in-session: "full
│   │     Operator() reconstruction... costs minutes" at 14 qubits,
│   │     "Statevector evolution of the same circuit costs ~2-3s" -- the
│   │     established substitution this repair's Tier 2 reuses) and Spec
│   │     8's own precedent (test_containment_omega_subset_lambda.py's
│   │     deliberately slower r=2 fixture, "accepted as the one-time cost
│   │     of a genuinely richer proof, not deferred" per its own
│   │     docstring, with no slow/optional marker used -- though this plan
│   │     does not independently verify the specific "~4 minute" duration
│   │     sometimes cited for that test, since no wall-clock figure is
│   │     recorded in that file itself).
│   └── test_extract_convergence.py     # UNCHANGED — must still pass unmodified (FR-008)
```

**Structure Decision**: Single project (Option 1) — this feature repairs
two functions and adds parameters within the EXISTING `extract.py`/
`circuits.py` files; no new module, no new top-level directory. The one
new file is a permanent oracle-suite test (Tier 2), placed in `tests/oracle/`
(the tree already reserved for exact-ground-truth/scale-sensitive checks)
rather than any new "slow tests" location, since this repository has never
had one and Critical Research Mandate 3 forbids inventing one now to hide
this specific test.

## Complexity Tracking

*No violations — table intentionally empty.*
