# Implementation Plan: Learning Backend Layer

**Branch**: `005-learning-backend-layer` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-learning-backend-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

**Note on this revision**: This plan replaces the version written before the
2026-08-21 clarify-session correction (an external review correctly
identified that the previous row model — training row = one
directly-measured Fourier coefficient — makes the sensing matrix an
identity, on which LASSO cannot perform genuine sparse recovery). See
research.md's own "Note on this revision" and R1-R5 for the corrected
design and its executed verification. The Constitution Check table below
explicitly marks which gates were re-derived because of this pivot and
which were unaffected (planning mandate #5).

## Summary

One new module (`src/fourierlearn/learn.py`) with two responsibilities.
First, a **new** finite-shot measurement primitive (FR-014) that estimates
the real-valued expectation `y(alpha) = <0|U^dagger(alpha) P U(alpha)|0>` at
a concrete numeric parameter assignment — an ancilla-Hadamard-test wrapping
a genuinely simpler circuit than Spec 4's (no frequency register, no
controlled-shift gates at all: 1 qubit vs. 6 on the mandated fixture,
research.md R2) built from `ir.gates` directly plus Circuits Layer's shared
`_insert_observable` helper. Second, the regression engine: `M` measured
`(alpha_j, y_j)` rows build a real Fourier sensing matrix `A_{j,l} =
exp(i*pi*l*alpha_j)` (FR-015, derived from — not reinvented independently
of — `fourierlearn.reference`'s own DFT/grid convention, research.md R3),
and `sklearn.linear_model.LassoCV` over an explicit, version-pinned penalty
grid solves the resulting genuinely under-determined linear system `y = A
b` for the sparse Fourier-coefficient vector `b` (FR-003/FR-004, the
"$t^2$-penalty bug" guardrail unaffected by the row-model pivot). A third
responsibility, the error-bounding framework, reports a PAC-style
statistical bound and a first-order Lie-Trotter structural bound as two
permanently separate numbers (FR-007/FR-008), plus a third, independent
noise axis (FR-010) and a policy-only "generalization check required" flag
(FR-009) whose mechanism is out of scope (Spec 6).

Per this round's planning mandates, four things were *executed*, not
promised, and kept in four separate scripts/sections so the exact-plumbing
claim is never conflated with the statistical-recovery claim (mandate #1):

1. **research.md R2**: FR-014's circuit has 5 fewer qubits than Spec 4's
   `V_l`-based circuit and zero `cx`/controlled-shift instructions — a
   structural simplification, not an identity-shift `V_l` (mandate #2) —
   and its Hadamard-test-wrapped value matches an independent direct
   computation to `1.44e-15` at 5 concrete `alpha` values.
2. **research.md R4**: the FR-006 stacking/reconstruction round trip,
   executed **end to end** (bind `alpha` → measure exact `y` → build the
   real sensing matrix → ordinary-least-squares solve → reconstruct complex
   `b`) on an exactly-determined system (`M=25 >= P=13`), matching the
   oracle to `2.08e-15`, with a negative control (flipped `Im`-column sign)
   confirmed detected (mandate #3).
3. **research.md R5**: SC-001's statistical sparse-recovery claim, on a
   *different* fixture (`L=25`, only 2 nonzero canonical frequencies),
   `M=9 << P=25`, `LassoCV` recovering the one active frequency to `0.0017`
   with zero spurious weight on the 12 inactive ones — deliberately kept
   separate from item 2 (mandate #1).
4. **research.md R6**: the FR-013 `tau` tolerance
   (`rel_tol=1e-9, abs_tol=1e-12` + exact `r` equality), carried over
   unaffected by the pivot and re-confirmed (mandate #4).

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-4; same pinned
interpreter, no change).

**Primary Dependencies**: `qiskit` 2.3.1, `qiskit-aer` 0.17.2, `numpy`
1.26.4 (all already pinned, unchanged). `scikit-learn==1.8.0` (new,
research.md R7/R12, already applied to `pyproject.toml`). **Pivot impact**:
this feature now owns its own first production circuit-execution path
(FR-014) rather than calling only Spec 4's already-shipped
`estimate_coefficient()` — `qiskit-aer`'s `AerSimulator.run()` +
`get_counts()` + `transpile()` is required for FR-014's shipped
implementation (Constitution Article II/§9.6), the same pattern Spec 4
already established, not a new execution style.

**Storage**: N/A — pure in-memory computation; a run manifest (config,
versions, hardware, timings, §8.5) is written beside outputs.

**Testing**: `pytest`. research.md R4's exact end-to-end round trip and R5's
statistical sparse-recovery scenario are promoted to two separate,
permanent named tests (never merged into one "does the fit work" test,
per this round's mandate #1). research.md R2's circuit-simplification and
exact-cross-check assertions become their own permanent test. `pytest`
reuses Spec 1's `fourierlearn.reference.coefficients` oracle and
`fourierlearn.reference._build_circuit` (already an existing, shared
research/oracle-only helper) directly, as research.md's own scripts do —
no new ground-truth mechanism is introduced.

**Target Platform**: Developer workstation and CI runner — unchanged from
Specs 1-4.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding one new module plus one new `Protocol` in the
existing `contracts.py` (§9.2's own extension point).

**Performance Goals**: None (§5.3 — no optimisation without a recorded
profile; research.md R11 confirms nothing was added beyond `LassoCV`'s own
unmodified internal defaults).

**Constraints**: FR-014's circuit MUST have no frequency register and no
controlled-shift gate at all (research.md R2 — not an identity-shift `V_l`).
FR-015's sensing matrix MUST use the exact Fourier basis convention
`fourierlearn.reference`'s own oracle already reconstructs against
(research.md R3), not an independently-invented one. The regularization
penalty grid and CV selection MUST NOT read the shot-noise bound or
Trotter evolution time (FR-003/FR-004). PAC bound and Trotter bound
computations MUST NOT read each other's inputs (FR-007) and MUST NEVER be
combined (FR-008). A single fit MUST reject a training set whose rows do
not share one identical `(tau, r)` (FR-013, research.md R6). Every
training/evaluation split MUST be checked for zero overlap (FR-005). A
non-Hermitian observable MUST be rejected before any prediction (FR-006).

**Scale/Scope**: Small validation cases only — the mandated single-qubit
conjugate-symmetric fixture (research.md R2/R4) for the exact-plumbing
checks, and a separate, deliberately wider/sparser single-qubit fixture
(research.md R5) for the statistical sparse-recovery check. No
production-scale frequency lattice is targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Blast-radius legend** (planning mandate #5): **RE-DERIVED** = this gate's
justification changed because of the 2026-08-21 row-model correction, and
was re-verified against the corrected design. **UNCHANGED** = this gate
concerns something the row-model correction does not touch; carried over
from the prior planning pass without new verification work.

| Gate | Rule | Status | Blast radius | Notes |
|------|------|--------|--------------|-------|
| Measurement-only production path | Article II, §3.1-3.4, §1.1-1.3 | **PASS** | **RE-DERIVED (new gate)** | Before the pivot, this feature added no new circuit-execution path (only called Spec 4's `estimate_coefficient()`). FR-014 is now this feature's *own* first production measurement primitive — verified in research.md R2 to be structurally simpler than Spec 4's circuit, with its exact value cross-checked; the shipped implementation MUST use `AerSimulator.run()`/`get_counts()`/`transpile()`, never `Statevector`, outside test/research code. |
| Learner input/label semantics | §7.1 | **PASS** | **RE-DERIVED** | The entire row model changed: a row is now `(alpha_j, y_j)` from FR-014, not a directly-measured `b_l` (research.md R1). |
| Trotterisation as label noise | §7.2 | **PASS** | UNCHANGED | Trotter error still enters only through the feature map (the compiled circuit itself), regardless of how a row's label is obtained. |
| Under-determined regression is intended | §7.3 | **PASS** | **RE-VERIFIED** | Now backed by an actually-executed sparse-recovery demonstration (research.md R5: `M=9 << P=25`) rather than an assumption; `cv = min(K_DEFAULT, M)` remains the only sample-count-sensitive line, a CV-fold mechanic, not a refusal to fit. |
| Penalty not anchored to shot-noise bound ("$t^2$-penalty bug") | §7.4 | **PASS** | UNCHANGED | The penalty grid/CV selection logic does not depend on what a row measures, only on the training data matrix — unaffected by the row-model fix. |
| Constants computed globally, not per input | §7.5 | **PASS** | UNCHANGED | The PAC bound remains one value per fit; only its internal union-bound count changed (research.md R8: `M` rows, not `2M` real components, since a row is now one real `y_j`, not a complex `b_l`) — RE-DERIVED at the formula-detail level, but the "compute once globally" requirement itself is untouched. |
| Conjugate symmetry for real predictions | §7.6 | **PASS** | **RE-DERIVED** | Re-verified end to end through the corrected pipeline (research.md R4: bind → measure → build `A` → solve → reconstruct), not merely re-asserting the previously-verified stacking sub-piece still applies. |
| Penalty selection uses only training data | §7.7 | **PASS** | UNCHANGED | `LassoCV(cv=k)` cross-validates over training rows only, regardless of what a row is. |
| No evaluation-input leakage | §7.8 | **PASS** | UNCHANGED | The split is still over concrete classical inputs (`alpha_j` values) either way — arguably a cleaner fit post-pivot, since `alpha_j` is now unambiguously "the classical input," but the check itself is unaffected. |
| Two error sources reported separately | §8.1 | **PASS** | UNCHANGED (formula detail RE-DERIVED) | PAC bound (research.md R8) and Trotter bound (research.md R9) remain computed from disjoint inputs and never combined; only the PAC formula's internal row-count detail changed. |
| Suspiciously-good fit is an artifact | §8.2 | **PASS** | UNCHANGED | FR-009's policy-flag behavior does not depend on the row model. |
| Every report states its own scope | §8.3 | **PASS** | UNCHANGED | — |
| Negative/inconclusive results documented | §8.4 | **PASS** | UNCHANGED | — |
| Seeded, versioned, manifested runs | §8.5 | **PASS** | UNCHANGED | `LassoCV(random_state=seed, selection="cyclic")` determinism is orthogonal to the row model. |
| Noise as a third independent axis | §8.6 | **PASS** | UNCHANGED | — |
| Architecture / pipeline order, no duplicated call paths | §9.1, §9.4 | **PASS** | **RE-DERIVED** | FR-014 reuses `reference.py`'s plain-circuit-construction pattern and Circuits Layer's shared `_insert_observable`/`basis_change_gates` helpers (research.md R2) rather than reimplementing observable-folding or building a third parallel circuit-construction path alongside `compile_frequency_circuit`/`compile_observable_circuit`. |
| Typed cross-layer Protocol | §9.2 | **PASS** | UNCHANGED | The `RegressionBackend` Protocol addition to `contracts.py` is orthogonal to the row model. |
| One code path regardless of dimensionality | §9.3 | **PASS** | UNCHANGED | — |
| Optimisation discipline | §5.3 | **PASS** | UNCHANGED | research.md R11 re-confirms nothing new was added. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's executed verification work. The
two mandates most central to this round were both executed, not promised:
(1) FR-014's circuit was checked to have strictly fewer qubits and zero
controlled-shift instructions compared to Spec 4's `V_l`-based circuit —
proving it is a structurally simpler construction, not an identity-shift
`V_l` masquerading as one (research.md R2); (2) FR-006's round trip was
verified **twice**, deliberately kept apart: once as an exactly-determined
linear-algebra plumbing check with `M >= P` and no LASSO (research.md R4,
`max error = 2.08e-15`), and once as a genuinely under-determined
statistical sparse-recovery check with `M << P` and real `LassoCV` fitting
on a different, deliberately sparser fixture (research.md R5, active-term
error `0.0017`, zero spurious weight on inactive terms). Neither check
stands in for the other. The FR-013 `tau` tolerance
(`rel_tol=1e-9, abs_tol=1e-12`) was re-confirmed unaffected by the pivot and
still executes cleanly (research.md R6). No open items remain before
`/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/005-learning-backend-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2-4's own precedent.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py         # Spec 1 — unchanged
    ├── ir.py                 # Spec 1 — unchanged
    ├── reference.py           # Spec 1 — unchanged; `_build_circuit` and
    │                           # `coefficients` reused by this spec's own
    │                           # tests/verification, same as research.md
    ├── contracts.py            # Spec 1 — ONE addition: RegressionBackend
    │                            # Protocol (§9.2's extension point)
    ├── encodings/               # Spec 2 — unchanged; trotter.py's tau/r
    │                            # feed the Trotter bound (research.md R9)
    ├── circuits.py               # Spec 3 — unchanged; `_insert_observable`
    │                              # and `basis_change_gates` reused by
    │                              # FR-014 (research.md R2); NOT
    │                              # `compile_frequency_circuit`/
    │                              # `compile_observable_circuit`
    ├── extract.py                 # Spec 4 — unchanged; no longer called
    │                               # by this feature after the pivot
    │                               # (FR-014 is this feature's own primitive)
    └── learn.py                    # NEW — FR-001..FR-015: estimate_y()
                                      # (FR-014), fit_model(), predict(),
                                      # error_bounding_report(),
                                      # LassoRegressionBackend

tests/
├── unit/
│   ├── test_learn_y_primitive.py       # FR-014: circuit-simplification
│   │                                     # assertion (fewer qubits, zero
│   │                                     # controlled-shift instructions
│   │                                     # vs. compile_observable_circuit)
│   │                                     # and the exact cross-check
│   │                                     # (research.md R2), promoted
│   ├── test_learn_design_matrix.py      # FR-006/FR-015: the executed
│   │                                     # END-TO-END exact round trip
│   │                                     # (research.md R4) — bind alpha,
│   │                                     # measure, build A, solve,
│   │                                     # reconstruct, plus its negative
│   │                                     # control — kept SEPARATE from:
│   ├── test_learn_sparse_recovery.py     # SC-001: the statistical M<<P
│   │                                      # LassoCV recovery scenario
│   │                                      # (research.md R5) — its own
│   │                                      # named test, never merged with
│   │                                      # test_learn_design_matrix.py
│   ├── test_learn_trotter_config.py       # FR-013: tau/r tolerance cases
│   │                                       # (research.md R6)
│   ├── test_learn_fit.py                   # US1: determinism, conjugate-
│   │                                        # symmetry prediction, leakage
│   │                                        # assertion (FR-002, FR-005,
│   │                                        # FR-006, FR-012)
│   ├── test_learn_penalty_integrity.py      # US3: the "$t^2$-penalty bug"
│   │                                         # guardrail (FR-003, FR-004)
│   └── test_learn_error_report.py            # US2: PAC/Trotter separation,
│                                               # no blended figure,
│                                               # generalization-check flag
│                                               # is policy-only (FR-007..010)
└── oracle/
    └── test_learn_pac_vs_trotter.py            # US2: PAC bound and Trotter
                                                  # bound validated against
                                                  # their own closed-form
                                                  # inputs, with a
                                                  # deliberately-coarse
                                                  # Trotter case showing the
                                                  # two bounds diverge
```

**Structure Decision**: One new module (`learn.py`), matching the
constitution's own pipeline-layer name (§9.1). One new `Protocol`
(`RegressionBackend`) appended to the existing `contracts.py`. No existing
Spec 1-4 file's behavior changes; `learn.py` reuses `reference.py`'s
`_build_circuit` and `circuits.py`'s `_insert_observable`/
`basis_change_gates` for FR-014, and no longer imports `extract.py` at all
after the pivot. The CI import guard (Spec 1) already recursively scans the
full source tree; `learn.py` imports only `qiskit`, `qiskit_aer`, `numpy`,
`sklearn`, and the two named Spec 1/Spec 3 helpers above — no `Statevector`,
`Operator`, or `expm` in its production path.

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
