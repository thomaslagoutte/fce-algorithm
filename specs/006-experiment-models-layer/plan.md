# Implementation Plan: Experiment and Models Layer

**Branch**: `006-experiment-models-layer` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-experiment-models-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Three new modules. First, `src/fourierlearn/_exact_dynamics.py` — a
single, minimal function (`exact_dynamics`) that is the **only** code in
this project outside `reference.py` itself authorized to import
`fourierlearn.reference` (FR-011), granted via a narrowly-scoped,
explicitly-documented CI-guard exception (FR-012, research.md R3,
executed against synthetic modules — not merely described). Second,
`src/fourierlearn/experiment.py` — the generalization-check mechanism
(FR-001/FR-002): given a Spec 5 `ErrorBoundingReport`, select a classical
input shifted away from every training input, obtain the exact
ground-truth value there via `_exact_dynamics.exact_dynamics` alone, and
compare it against the fitted model's (deterministic) prediction using an
absolute, inclusive threshold (`abs(predicted - exact) <= trotter_bound`,
research.md R2 — no noise-based hedging, since neither side of the
comparison carries randomness) to return `generalizes` or `refuted`,
without ever mutating the consumed report (FR-003) or its
`PacBound.weight_space_translation_status` (FR-004). Third,
`src/fourierlearn/models.py` — the TFIM model-construction capability
(FR-005/FR-006), translating a graph-and-field description into Spec 2's
existing `CouplingGroup` input shape, plus the two additive, always-`None`
Constitution §11 attach points (FR-007/FR-008, research.md R6) that
implement nothing of §11 itself.

The refutation guard (research.md R1) was executed, not merely described:
a genuine overfitting artifact (a null-space-injected, under-determined
least-squares fit that interpolates its own training data to `2.3e-15`
while being unconstrained elsewhere) was constructed on a real fixture with
a nonzero Trotter bound, and the generalization check correctly returned
`refuted` at a genuinely unseen point (`gap=4.07` vs. `bound=0.5`), while a
positive control (the true oracle-matching model) correctly returned
`generalizes` (`gap=1.1e-16`). The threshold's absolute, inclusive nature
was executed at the exact boundary (99.9% / exactly 100% / 100.1% of the
Trotter bound), each returning its definitive expected verdict with no
ambiguous middle case. The CI guard's exact code change was prototyped and
executed against synthetic modules, confirming the exemption is scoped to
exactly one module and exactly one forbidden name.

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-5; unchanged).

**Primary Dependencies**: `qiskit` 2.3.1, `qiskit-aer` 0.17.2, `numpy`
1.26.4, `scikit-learn` 1.8.0 (all already pinned, unchanged). No new
third-party dependency. This feature's only new *internal* dependency
pattern is `_exact_dynamics.py`'s narrowly-scoped import of
`fourierlearn.reference` (research.md R3/R4) — the second and last module
in this project ever permitted to do so.

**Storage**: N/A — pure in-memory computation; a generalization-check
result and a constructed model are both plain, immutable data objects.

**Testing**: `pytest`. research.md R1's refutation guard (negative +
positive control) and R2's threshold-boundary cases become permanent,
named tests, kept separate per this project's established discipline of
never merging an exact-plumbing-style check with a different claim. R3's
CI-guard prototype's two new test functions are applied directly to
`tests/ci/test_no_forbidden_imports.py` (not left as a separate
prototype file).

**Target Platform**: Developer workstation and CI runner — unchanged.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding three new modules.

**Performance Goals**: None (§5.3 — research.md R7: no caching, batching,
or memoization anywhere in this design; nothing here runs in a hot loop
this spec's own scope would need to profile).

**Constraints**: `_exact_dynamics.py` MUST be the only module (besides
`reference.py`) importing `fourierlearn.reference`, and MUST NOT itself
import `Statevector`/`Operator`/`expm` directly (research.md R3's guard
prototype enforces this exact boundary). `experiment.py` MUST NOT import
`fourierlearn.reference` — only `_exact_dynamics.exact_dynamics`. The
generalization check MUST NOT mutate the consumed `ErrorBoundingReport` or
its `PacBound.weight_space_translation_status` (FR-003/FR-004). The
threshold comparison MUST use `<=` (inclusive), never a noise-derived
tolerance (research.md R2). `models.py`'s coupling-group construction MUST
reject a zero coupling strength explicitly (FR-006).

**Scale/Scope**: Small validation fixtures only — the two-coupling-group
`X`/`Z` fixture (research.md R1/R2) for the generalization-check tests, and
a small (e.g. 3-node path graph) TFIM instance for the model-construction
tests. No production-scale physical model is targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Measurement-only production path (general rule) | Article II, §1.1, §9.6 | **PASS** | `experiment.py` and `models.py` import neither `Statevector`/`Operator`/`expm` nor `fourierlearn.reference` — confirmed by research.md R3's guard prototype, which still rejects "some other module" importing `reference`. |
| Measurement-only production path (narrow exception) | §1.1, §2.3 (`EXTENSION`) | **PASS, WITH DOCUMENTED EXCEPTION** | See Complexity Tracking below — `_exact_dynamics.py` is a deliberate, narrow, explicitly-justified deviation from the blanket rule, not a silent one. |
| Honest results: suspected artifact requires a generalization test | §8.2 | **PASS** | This entire feature exists to implement exactly this requirement; research.md R1 executes the actual negative/positive control, not merely a formula. |
| Negative/inconclusive results documented | §8.4 | **PASS** | The zero-Trotter-bound boundary tie (spec.md Edge Cases) is stated explicitly as a tie, per the `<=` rule (research.md R2), never silently resolved either way. |
| Immutable Reports | Clarifications 2026-08-20/21 (FR-003) | **PASS** | `experiment.py` only reads `ErrorBoundingReport` fields; research.md's own test plan asserts before/after field equality directly, not merely relying on the dataclass being frozen. |
| PAC-Bound Rigidity | Clarifications 2026-08-21 (FR-004) | **PASS** | Nothing in `experiment.py` constructs or returns a new `PacBound`; `weight_space_translation_status` is never read for the purpose of being rewritten. |
| Architecture / pipeline order, no duplicated call paths | §9.1, §9.4 | **PASS** | `experiment.py` calls Spec 5's own `predict()` unchanged; `models.py` calls Spec 2's own `CouplingGroup`/`trotter_frontend` unchanged; neither reimplements circuit or fitting logic. |
| One code path regardless of dimensionality | §9.3 | **PASS** | `models.py`'s group-per-label construction (research.md R5) is data-driven (the caller's label choice), not a branch on graph size or edge count. |
| Optimisation discipline | §5.3 | **PASS** | research.md R7. |
| Research programme attach points | §11.0-§11.11 | **PASS, SCOPED** | research.md R6's two additive, always-`None` fields implement nothing of §11 — verified by construction (no code path sets them), not merely asserted. |

### Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| `_exact_dynamics.py` imports `fourierlearn.reference` (Article II's blanket "only `reference.py` itself" rule) | Constitution §8.2's generalization check requires a genuinely *exact* comparison target. research.md's Clarifications (2026-08-21) proved every finite-shot or finer-Trotter-approximation alternative is scientifically invalid for this specific purpose: both a real capability and an overfitting artifact would "pass" against an approximate target, so the check would prove nothing. | A finite-shot re-measurement of the same Trotterized circuit — rejected: it is *still* only Trotter-approximate, so it cannot distinguish the two cases §8.2 requires distinguishing (Clarifications, 2026-08-21). A finer Trotter step as a "closer" reference — rejected for the identical reason, however small the step. Both alternatives were the original (incorrect) design and are recorded as a corrected mistake, not a rejected-but-plausible option (spec.md Clarifications). |

No other Constitution Check items require justification.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's executed verification work. The
narrow exception itself was verified from three angles, not merely
declared: (1) it correctly enables the refutation guard to work at all —
research.md R1's negative control would have been unfalsifiable without a
genuinely exact comparison target; (2) the guard prototype (R3) proves the
exemption doesn't widen to any other module; (3) the guard prototype also
proves the exempt module itself isn't given a blanket pass — it is still
rejected for `Statevector`/`Operator`/`expm`. No open items remain before
`/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/006-experiment-models-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2-5's own precedent.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py          # Spec 1 — unchanged
    ├── ir.py                  # Spec 1 — unchanged
    ├── reference.py            # Spec 1 — unchanged; gains exactly one new
    │                            # authorized caller, `_exact_dynamics.py`
    ├── contracts.py             # Spec 1/5 — unchanged
    ├── encodings/                # Spec 2 — unchanged; `CouplingGroup`/
    │                              # `trotter_frontend` reused by models.py
    ├── circuits.py                # Spec 3 — unchanged
    ├── extract.py                  # Spec 4 — unchanged
    ├── learn.py                     # Spec 5 — unchanged; `predict()`,
    │                                 # `ErrorBoundingReport`, `PacBound`
    │                                 # reused unchanged by experiment.py
    ├── _exact_dynamics.py             # NEW — FR-011: the ONE narrowly
    │                                   # exempt module (research.md R3/R4)
    ├── experiment.py                   # NEW — FR-001..FR-004, FR-008..010:
    │                                    # the generalization-check mechanism
    └── models.py                        # NEW — FR-005..FR-008: TFIM model
                                           # construction + §11 attach points

tests/
├── ci/
│   └── test_no_forbidden_imports.py     # MODIFIED (not new) — research.md
│                                          # R3's exact diff applied; two new
│                                          # test functions added
├── unit/
│   ├── test_experiment_refutation_guard.py  # research.md R1: negative +
│   │                                          # positive control, promoted
│   ├── test_experiment_threshold.py          # research.md R2: the three
│   │                                          # boundary cases (99.9% /
│   │                                          # exactly 100% / 100.1%)
│   ├── test_experiment_immutability.py        # FR-003: before/after field
│   │                                            # equality on the consumed
│   │                                            # ErrorBoundingReport
│   ├── test_experiment_pac_rigidity.py         # FR-004:
│   │                                            # weight_space_translation_status
│   │                                            # never changes
│   ├── test_models_tfim_construction.py         # US2: uniform + heterogeneous
│   │                                              # coupling-group construction,
│   │                                              # zero-coupling rejection
│   │                                              # (FR-005, FR-006)
│   └── test_models_symmetry_attach_point.py      # US3: optional, additive,
│                                                   # never-evaluated symmetry
│                                                   # declaration (FR-007)
└── oracle/
    └── test_experiment_shift_leakage.py            # FR-009: shifted input
                                                       # never coincides with a
                                                       # training input
```

**Structure Decision**: Three new modules, matching the constitution's own
pipeline-layer names (§9.1: `... → learn → models → experiment`). The
narrow oracle-access exception (FR-011) is isolated to the smallest
possible module (`_exact_dynamics.py`, one function) rather than granted to
`experiment.py` as a whole, minimizing the CI-guard-exempted surface
(research.md R4). No existing Spec 1-5 file's behavior changes; the only
modification to previously-shipped code is the documented, tested addition
to `tests/ci/test_no_forbidden_imports.py` itself (research.md R3).

## Complexity Tracking

*See the Constitution Check section above — one documented, justified
violation (the narrow oracle-access exception), not repeated here.*
