# Implementation Plan: Cross-Topology Regression Layer

**Branch**: `012-cross-topology-regression` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-cross-topology-regression/spec.md`

## Summary

Build the pipeline Spec 5 was originally meant to build, restoring the
thesis's own advantage-relevant learning direction after Spec 5's own,
already-documented drift into the "flipped concept" `C̄` (thesis §5.7.10):
a training-row abstraction of `(x_t, y_t)` pairs (classical topology +
label, never a bound encoded-parameter value); per-row feature extraction
via Spec 4's real `extract_coefficients` (one full circuit per topology);
an honestly under-determined LASSO fit for a sparse weight vector `w(α*)`
(thesis eq. 5.79); and held-out prediction via the identical extraction
path. Phase 0 research executed all three of this round's critical
mandates before this plan was finalized: (1) a real, executed shared-
fixture cross-check between this feature's LASSO route and Spec 10's KRR
route, which — as expected — do NOT produce identical predictions (mean
divergence `2.8e-4` at `T=5` under-determined, shrinking to `6e-5` at
`T=12` well-determined) but both track the true, noiseless dynamics to
within `<1e-3`, giving SC-006 a concrete, non-equality tolerance definition
instead of an assumed one; along the way, research.md R2 found and
resolved a real ambiguity — Spec 10's amplitude-based `b(x)` and Spec 4's
observable-based `b(x)` are DIFFERENT objects for the same circuit, so the
cross-check reuses Spec 10's generic KRR machinery on THIS feature's own
feature vectors, not Spec 10's own circuit; (2) FR-014's frequency-
lattice-alignment check mapped out concretely, as a signature over Spec
1's own `Parameter` fields, with FR-008 identified as one instance of it,
not a separate mechanism; (3) Spec 5's own two-round architectural drift
documented with its exact failure mechanism, citing Spec 5's own spec.md
history and the verified thesis sections.

## Technical Context

**Language/Version**: Python 3.12 (matches the rest of `src/fourierlearn/`).

**Primary Dependencies**: Qiskit (circuit compilation, reused unchanged
from Specs 1-4/11), `scikit-learn`'s `LassoCV` (matching `learn.py`'s own
already-established library convention — no new dependency), NumPy.

**Storage**: N/A (in-memory circuits and arrays, matching every prior spec).

**Testing**: pytest, `tests/unit/` and `tests/oracle/` — this feature's
own module gets a dedicated, NEW CI-style import-guard test (FR-003/SC-002),
using the same AST-based scanning technique `tests/ci/test_no_forbidden_
imports.py` already established, but as its own file: that file's own
scope (`Statevector`/`Operator`/`expm`/`reference`) is a project-wide
invariant unrelated to this feature's narrow, one-module-vs-one-module
non-reuse boundary against `learn.py`.

**Target Platform**: local CPU simulation (Aer, Constitution §3.2) —
matches every prior spec.

**Project Type**: single Python library (`src/fourierlearn/`) — one new
module, no new top-level directory.

**Performance Goals**: none newly imposed; per-topology extraction cost
is Spec 4's own (now Spec-11-repaired) cost, unchanged by this feature.

**Constraints**: Constitution §7.3 (under-determined regression is
intended, never guarded against); §7.4/§7.7 (penalty selection data-
driven, never anchored to shot noise); §7.6/§7.8 (conjugate symmetry,
held-out-input assertion); §8.4 (Spec 5's drift documented, not erased);
§11.11 analog (FR-007 — classical-input scope discipline, never drifting
into a fidelity regression over `α`).

**Scale/Scope**: small, hand-constructed validation fixtures (single-digit
to low-double-digit topology counts, 1-2 encoded parameters) — matching
every prior spec's own declared validation scale; no production-scale
topology sweep is targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Gate | Requirement | How this feature satisfies it |
|------|-------------|-------------------------------|
| §7.1 | Encoded parameters unknown/carry frequencies; classical input known, selects fixed gates | FR-001/FR-002: training rows are `(x_t, y_t)`, `x_t` selecting fixed gates within a shared encoded-parameter structure — never a bound `α_j` |
| §7.3 | Under-determined regression intended; never guard against "too few" samples | FR-004; research.md R3 executes exactly this regime (`T=5 < d=7`) and reports it as the intended case, not an edge case |
| §7.4/§7.7 | Penalty selection data-driven only, never anchored to noise/evolution-time | FR-009 |
| §7.6/§7.8 | Conjugate symmetry for real predictions; held-out input asserted absent from training | FR-006, FR-010, FR-011 |
| §8.4 | Negative results documented with failure mechanism, never erased | research.md R1 — Spec 5's two-round drift, cited from its own spec.md history |
| §11.11 analog | Never drift into a fidelity kernel/regression over `α` | FR-007 |
| §5.2/§4.1 (verify before asserting) | Every equivalence/relationship claim backed by an executed check | research.md R2 (the `b(x)` object-identity check) and R3 (the executed LASSO-vs-KRR cross-check) — both run before this plan was finalized, per this round's own Critical Research Mandates |

**Result**: PASS — no violations requiring justification. Complexity Tracking table below is empty by design.

## Project Structure

### Documentation (this feature)

```text
specs/012-cross-topology-regression/
├── plan.md              # This file
├── research.md          # Phase 0 output — Spec 5 drift history, b(x) object-identity
│                         #   finding, executed LASSO-vs-KRR cross-check, FR-014 mapping
├── data-model.md         # Phase 1 output (next)
├── quickstart.md         # Phase 1 output (next)
├── contracts/            # Phase 1 output (next, if warranted)
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/fourierlearn/
├── cross_topology.py    # NEW module (this feature) -- deliberately NOT learn.py,
│                         #   since FR-003 forbids importing learn.py's flipped-
│                         #   direction symbols and this is new code added
│                         #   alongside it, not a modification of it:
│                         #   - CrossTopologyRow: (x_t, y_t) training-row dataclass
│                         #     (FR-001)
│                         #   - extract_feature_vector(ir_x, observable, shots, ...):
│                         #     thin wrapper around extract.extract_coefficients
│                         #     (Spec 4) + the conjugate-symmetric real-stacking
│                         #     convention (FR-006, verified research.md-style
│                         #     before /speckit-tasks relies on it)
│                         #   - FrequencyLatticeMismatchError,
│                         #     _frequency_lattice_signature,
│                         #     validate_lattice_alignment(rows) -- FR-014
│                         #     (research.md R4), FR-008 implemented as one
│                         #     instance of this general check
│                         #   - fit_cross_topology_lasso(rows, ...) -- FR-004/FR-009
│                         #   - predict(model, x_star, ...) -- FR-005/FR-010/FR-011

tests/
├── unit/
│   ├── test_cross_topology_no_learn_reuse.py   # NEW, dedicated file (FR-003/SC-002)
│   │                                    #   -- mirrors tests/ci/test_no_forbidden_
│   │                                    #   imports.py's own AST-based scanning
│   │                                    #   TECHNIQUE, but lives in tests/unit/, not
│   │                                    #   tests/ci/: that file's own scope
│   │                                    #   (Statevector/Operator/expm/reference) is a
│   │                                    #   project-wide invariant every module is
│   │                                    #   subject to, unrelated to this feature's own
│   │                                    #   narrow, one-module-vs-one-module non-reuse
│   │                                    #   boundary against learn.py's estimate_y/
│   │                                    #   TrainingRow/build_sensing_matrix/
│   │                                    #   LassoRegressionBackend/fit_model
│   └── test_cross_topology_*.py        # NEW: FR-006 stacking round trip, FR-008/FR-014
│                                        #   lattice-alignment rejection, FR-009 penalty
│                                        #   discipline, FR-010 held-out assertion
└── oracle/
    ├── test_cross_topology_lasso_recovery.py   # NEW: SC-001, known-sparse recovery
    └── test_cross_topology_krr_crosscheck.py   # NEW: SC-006, reproducing research.md
                                                  #   R3's executed cross-check as a
                                                  #   permanent regression test
```

**Structure Decision**: Single project (Option 1) — one new module
(`cross_topology.py`), no new top-level directory, matching every prior
spec's own shape. Placed alongside, not inside, `learn.py` — FR-003's
non-reuse boundary is a MODULE-level separation, not merely a
within-file discipline.

## Complexity Tracking

*No violations — table intentionally empty.*
