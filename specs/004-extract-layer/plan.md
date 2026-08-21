# Implementation Plan: Extract Layer

**Branch**: `004-extract-layer` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-extract-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A single new module (`src/fourierlearn/extract.py`) that wraps Spec 3's
compiled `A(U,O)` circuit with a Hadamard-test ancilla per target frequency
`l` (Barthe thesis Corollary 5.1/5.2), executes it with **finite shots only**
via `AerSimulator.run()` + `get_counts()` (Constitution §9.6), and converts
the resulting counts into a Fourier-coefficient estimate via
`P(\text{ancilla}=0) - P(\text{ancilla}=1)`. `V_l` (the frequency-register
state-preparation unitary Corollary 5.1's formula requires) is built by
reusing Circuits Layer's own cyclic-shift primitive (`_increment_circuit`)
`|l|` times — no new shift logic is introduced. A second entry point,
`extract_coefficients`, builds the full coefficient set from this primitive,
directly estimating only the non-mirrored half of the frequencies (plus the
always-direct DC term) and deriving the rest by complex conjugation, since
the folded observable's Hermiticity forces the underlying function real.

Every formula in this plan — the Hadamard-test circuit, the `V_l`
construction, and the counts-to-amplitude conversion — was verified
computationally in research.md using the **exact production construction**,
not a simplified stand-in: matched the Foundation Layer's exact oracle to
~1e-14 at the infinite-shot limit, confirmed the conjugate-symmetry identity
holds exactly on the estimator's own raw output (not merely on the oracle),
and then re-confirmed with a real, finite-shot `AerSimulator` run (200,000
shots) landing within the shot count's own expected statistical noise, plus
a four-point convergence trend (1e3 to 1e6 shots) shrinking at the expected
`1/\sqrt{\text{shots}}` rate.

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-3; same pinned
interpreter, no change).

**Primary Dependencies**: `qiskit` 2.3.1 and `qiskit-aer` 0.17.2 (both
already pinned) — `qiskit_aer.AerSimulator.run()` + `.result().get_counts()`
for finite-shot execution (Constitution §9.6's Aer-native batched path;
`SamplerV2` remains an equally compliant alternative not adopted here, per
spec.md's own Assumption deferring that choice to this plan — `AerSimulator`
is chosen for its direct, minimal-abstraction counts interface, matching
§5.9's "prefer the simple correct construction"); `qiskit.transpile()`
before every `.run()` call (research.md R5 — required, not optional: a
controlled custom-gate circuit is rejected by Aer otherwise). No new
third-party dependency is introduced.

**Storage**: N/A — pure computation over in-memory circuit objects and
in-process `AerSimulator` execution, same as Specs 1-3.

**Testing**: `pytest`, reusing Spec 1's `fourierlearn.reference.coefficients`
oracle directly for this spec's own validation tests (FR-009) — no new
ground-truth mechanism is introduced. The dedicated statistical convergence
test uses research.md's own Hoeffding-derived tolerance formula
(`eps(N, delta) = sqrt(2*ln(2/delta)/N)`), applied independently to the real
and imaginary parts of the mandated reused fixture (Spec 3 research.md R8),
at more than one shot count, and passes for any seed (Constitution §4.4).

**Target Platform**: Developer workstation and CI runner — unchanged from
Specs 1-3.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding one new module.

**Performance Goals**: None (Constitution §5.3 — no optimisation without a
recorded profile and a bottleneck it targets; research.md R9 explicitly
considered and rejected batching multiple circuits into one `sim.run()` call
absent such a profile).

**Constraints**: MUST NOT import or invoke `Statevector`, `Operator`, or
`expm` anywhere in this module (Constitution Article II/§3.3-3.4) — enforced
mechanically by Spec 1's existing, already-recursive CI import guard, which
requires no changes for this feature (confirmed in spec.md's own
Assumptions). MUST NOT provide any exact/`shots=None` execution mode
(§1.2). MUST NOT synthesize shot noise around an exactly-computed value
(§1.3) — every estimate must come from real `get_counts()` output. The new
cost-budget guard (`ShotBudgetExceeded`) MUST mirror Spec 1's
`CostBudgetExceeded`/`confirm=True` interface style exactly, defined locally
(research.md R7).

**Scale/Scope**: Small validation circuits only for this spec's own tests
(1-2 qubits, the single mandated Spec 3 R8 fixture for the convergence test)
— no production circuit sizes are targeted here, same scope discipline as
Specs 1-3.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Measurement-only production path | Article II, §3.1-3.4, §1.1-1.3 | **PASS** | Every estimate in this design comes from `AerSimulator.run()` + `get_counts()`, converted via `P(0)-P(1)` — verified directly with a real 200,000-shot run (research.md R5); no `Statevector`/`Operator` anywhere outside the research-only verification scripts themselves, which are not part of the shipped module. |
| Execution primitive | §9.6 | **PASS** | `AerSimulator.run()`/`get_counts()` — the Aer-native batched path explicitly permitted; `qiskit.execute()`, V1 primitives, and `EstimatorV2` are not used anywhere (research.md R2, R5). |
| No exact/infinite-shot mode | §1.2 | **PASS** | Every entry point requires an explicit, finite, positive shot count (FR-002/FR-008); no `shots=None` path exists. |
| No synthesized shot noise | §1.3 | **PASS** | research.md R5's estimates come from real `get_counts()` output on an actually-executed circuit, not sampling around the exact value R3/R4 separately (and only in research) computed. |
| Architecture / no duplicated call paths | §9.1, §9.4 | **PASS** | `extract.py` sits directly after `circuits` per the pipeline order; it calls Spec 3's `compile_observable_circuit` and Circuits Layer's own `_increment_circuit` rather than rebuilding either (research.md R1, R2). |
| Conjugate symmetry shortcut | §7.6 | **PASS** | Verified, not assumed, on the estimator's own exact raw output (research.md R4) — the specific check `/speckit-clarify` mandated before this shortcut could be accepted; Hermiticity is asserted before use (FR-006), and the DC term's realness is a permanent, load-bearing per-run test assertion (FR-012, research.md R8), not a one-time design note. |
| Validation protocol, non-trivial tests | §4.1, §4.3, §4.4 | **PASS** | Validated against Spec 1's own oracle at the exact limit (research.md R3) and at real finite shots with a derived, non-arbitrary Hoeffding tolerance (research.md R6) on a genuinely complex, mandated-reuse fixture (FR-010) — not a fixture that happens to be real-valued. |
| Failure behaviour | §10.1, §10.3 | **PASS** | Degenerate shot counts and out-of-range frequencies raise (FR-008); predicted execution cost is checked against a budget before running, refusing without confirmation (FR-007). |
| Optimisation discipline | §5.3 | **PASS** | No caching, batching, or template reuse anywhere in this design (research.md R9) — batching multiple circuits into one `sim.run()` call was explicitly considered and rejected absent a recorded profile. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's verification work, not merely at
the outline stage. Two items were only confirmed correct *during* research,
not assumed beforehand: (1) `V_l = (V+)^l` is not an arbitrary choice among
unitaries satisfying `V_l|0\rangle=|l\rangle` — it was specifically checked
that this construction sends every *other* basis state to something
orthogonal to `|0\rangle`, which is what makes Corollary 5.1's overlap
formula correctly isolate only the `l`-th term rather than an uncontrolled
mixture (research.md R2-R3); (2) the conjugate-symmetry shortcut holds
exactly for the *estimator's own* raw output, not only for the oracle it is
being compared against (research.md R4) — the specific gap
`/speckit-clarify` flagged as unverified. A real bug (Aer rejecting an
un-transpiled controlled custom gate) was found and fixed during this same
verification pass, not discovered later during implementation (research.md
R5). No open items remain before `/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/004-extract-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2/3's own precedent —
`data-model.md`/`contracts/`/`quickstart.md` are not generated here; the one
new module's data shapes and verified decisions are fully specified in
research.md instead.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py        # Spec 1 — unchanged
    ├── ir.py                # Spec 1 — unchanged
    ├── contracts.py         # Spec 1 — unchanged
    ├── reference.py         # Spec 1 — unchanged; used only by this spec's own validation tests
    ├── encodings/            # Spec 2 — unchanged; used only by this spec's own test fixtures
    ├── circuits.py           # Spec 3 — unchanged; compile_observable_circuit and
    │                          # _increment_circuit reused unchanged
    └── extract.py             # NEW — FR-001..FR-012: estimate_coefficient(),
                                 # extract_coefficients(), ShotBudgetExceeded

tests/
├── unit/
│   ├── test_extract_hadamard_test.py    # US1, FR-001..FR-004, FR-008: dedicated
│   │                                      # equivalence tests for the Hadamard-test
│   │                                      # circuit and the V_l construction against
│   │                                      # the exact oracle (research.md R2-R4)
│   └── test_extract_full_coefficients.py # US2, FR-005..FR-007, FR-012: full-set
│                                           # extraction, conjugate-symmetry shortcut,
│                                           # DC-is-real load-bearing assertion,
│                                           # cost-budget guard
└── oracle/
    └── test_extract_convergence.py        # US3, FR-009..FR-010: the statistical
                                             # convergence test, using the mandated
                                             # Spec 3 research.md R8 fixture at
                                             # multiple increasing shot counts,
                                             # any-seed tolerance from research.md R6
```

**Structure Decision**: One new module (`extract.py`) directly under the
existing `src/fourierlearn/` library, matching the constitution's own
pipeline-layer name (§9.1). No existing Spec 1-3 file is modified — this
feature only imports from `circuits.py` (`compile_observable_circuit`,
`_increment_circuit`) and, for tests only, `reference.py`. The CI import
guard (Spec 1) already recursively scans the full source tree and requires
no changes.

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
