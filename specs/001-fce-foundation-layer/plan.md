# Implementation Plan: FCE Foundation Layer

**Branch**: `001-fce-foundation-layer` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-fce-foundation-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Establish the four foundation components every later FCE layer depends on: (1) a
typed contracts module scoped to the two boundaries this spec crosses (`Encoding ->
IR`, `IR -> Oracle`) plus a documented extension point for later layers' Protocols;
(2) an intermediate representation (IR) for Pauli-encoded parameterised circuits that
carries, per parameter, its upload count, its real per-upload coefficients, and its
tied multiplicity `r_j`, as an ordered gate sequence over fixed and parameterised
gates; (3) a single frequency-convention module fixing sign (`l = Λ - Λ'`), the
canonical pre-parity representation, the explicit post-parity relabeling, two's-
complement decoding, coordinate ordering, and the `register_width(uploads, r_j)`
formula; (4) an exact reference oracle, quarantined to `reference.py`, that maps an
IR instance to its Fourier coefficients via a Nyquist-sufficient grid (`4 r_j L + 1`
points per coordinate, pre-parity) and a d-dimensional FFT; and (5) a CI check —
implemented as an AST-based import scanner run as a pytest test inside CI — that
fails the build if any production module imports `Statevector`, `Operator`, `expm`,
or the reference oracle. Validated against hand-derived analytic coefficients for a
single-upload case and a two-upload case that includes a fixed symmetry-breaking gate
so its coefficients are genuinely complex (spec FR-018).

**Revision note (post-planning correction, verified against `docs/references/`)**:
(1) the rotation-angle period question left open in the first plan revision is now
resolved — period 2 in native `α` units, not `2π` — cited to Barthe's Definition 2.4
and the Z2LGT report §3.1-3.2 (research.md R8); (2) the oracle's evaluation strategy
uses `Statevector` only, over a circuit built from real Qiskit gates — `expm` and
dense-Hamiltonian construction are not used here at all, and are forward-referenced
to Spec 6 (Experiment) for continuous-time dynamics (research.md R6); (3) the IR
holds real Qiskit `Gate` objects (e.g. `FixedGate.gate: Gate`) rather than a parallel
gate ontology (research.md R3); (4) the numpy/Qiskit dependency floor was re-checked
via `importlib.metadata` in this session — no numpy 2.x floor is forced, `1.26.4`
stands (research.md R2) — and the run-manifest scaffold is scoped down to a
dependency-version check only, with full manifest scaffolding deferred to Spec 6
(research.md R11); (5) the package is renamed `fce` → `fourierlearn` throughout, to
avoid a `sys.path` collision with an unrelated legacy repository of the same name.

**Second revision note (plan-design review)**: two further corrections, both adding
new falsifiable requirements rather than just fixing wording: (6) the oracle's grid
samples the *full* period-2 domain per parameter, not the period-1 half-domain the
parity result would, in principle, justify — sampling the half-domain would make
"every odd-`l` coefficient is zero" an assumption baked into the grid rather than a
checked claim, so FR-020/SC-008 now require asserting it explicitly, at double the
(still cheap, at this scale) evaluation cost (research.md R7); (7) `PauliTerm.to_gate()`'s
mapping to `PauliEvolutionGate` was verified in-session to need a `-π` factor
(`time = -π c α`, not `c α`), since `PauliEvolutionGate(P, time=t)` implements
`e^{-itP}` while this layer's encoding convention is `e^{+iπcαP}` — a sign error here
silently conjugates every coefficient (`l ↔ -l`) invisibly on real-valued tests, so
FR-021/SC-009 now require a dedicated `Operator`-equivalence test independent of the
oracle's own coefficient checks (research.md R6). Both were verified computationally
in-session (§9.7) before being written up, not asserted from the general Qiskit
documentation.

## Technical Context

**Language/Version**: Python 3.12 (verified installed: 3.12.2; constitution §9.7
requires pinning, not assuming, the interpreter and library versions actually used).

**Primary Dependencies**: `qiskit` 2.3.1 and `qiskit-aer` 0.17.2 (verified installed
versions; `reference.py` uses `qiskit.quantum_info.Statevector` — and only
`Statevector` — over a circuit built from real Qiskit gates (`PauliEvolutionGate`,
`SGate`, etc.); `Operator` and `expm` are not needed by this spec's oracle at all and
are forward-referenced to Spec 6 for continuous-time dynamics, research.md R6),
`numpy` 1.26.4 (`numpy.fft.fftn` for the d-dimensional FFT — re-verified this session
via `importlib.metadata` to have no unmet version floor against either Qiskit package,
research.md R2), `pytest` (test runner, including the CI import-guard test), `mypy`
(verifies the contracts module's Protocols are actually typed, per spec SC-001).

**Storage**: N/A — this layer is pure computation over in-memory data structures; no
persistence.

**Testing**: `pytest` for all unit and oracle-validation tests; `mypy` in CI for
static type checking of the contracts module and IR. Oracle validation is exact
(floating-point precision assertions), not statistical — there is no shot noise at
this layer (§4.2's "encodings vs. analytic coefficients" and "circuits vs. oracle
coefficients" rungs; no sampled extractor exists yet to apply §4.4's tolerance rule
to).

**Target Platform**: Developer workstation (macOS/Linux) and CI runner (GitHub
Actions) — no target execution hardware beyond what runs `pytest`.

**Project Type**: Single Python library package (`src/fourierlearn/`), consistent
with the constitution's framing as "a shot-based Qiskit package." (Renamed from the
original `src/fce/` to avoid a `sys.path` namespace collision with an unrelated
legacy repository also named `fce`.)

**Performance Goals**: None beyond the cost-budget guard on the oracle's grid
evaluation (spec FR-013, §10.3) — this layer's purpose is a correct, stable interface,
not throughput (spec Assumptions).

**Constraints**: No production module (i.e. anything outside `reference.py` and test
helpers) may import `Statevector`, `Operator`, `expm`, or `reference` (§3.3-3.4,
enforced mechanically by the CI import guard). The IR must handle any parameter count
through one code path — no branching on dimensionality (§9.3).

**Scale/Scope**: Foundation layer only — two validation circuits (one-upload,
two-upload-with-symmetry-breaking-gate) plus the register-width unit-test table; no
production circuit sizes are targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Measurement-only production path | §3.3, §3.4 | **PASS** | This spec's own deliverables (d) and (e) *are* the quarantine and the CI guard; `reference.py` is the only module permitted to import the four forbidden symbols — this spec's own oracle only actually uses `Statevector`; `Operator`/`expm` remain available there for Spec 6's continuous-time dynamics without needing a second quarantine module (research.md R6). |
| Scientific fidelity / source verification | §2.1, §2.5 | **PASS** | The rotation-angle period, the grid-size formula, and the register-width formula are cited to `docs/references/Barthe_thesis.pdf` and `docs/references/equivariant FCE Z2LGT report.pdf` by file, page, and definition/equation number (research.md R8, R12), not left as unverified markers. |
| Validation protocol | §4.1, §4.2, §4.3, §4.5 | **PASS** | Contracts, IR, frequency convention, and oracle each get an isolated ground-truth/consistency test (spec SC-005) before any dependent layer's spec is written. The two-upload case is required to be genuinely complex (§4.3), not degenerate; the oracle's grid additionally samples the full (not parity-halved) domain so the parity claim itself is a live, failable check (FR-020/SC-008); the IR's gate-convention sign is checked by a dedicated equivalence test independent of coefficient comparisons (FR-021/SC-009). |
| Conventions | §6.1, §6.2, §6.3, §6.4 | **PASS** | One frequency-convention module is the sole source of sign/indexing/decoding/ordering; pre-/post-parity counts stay separately annotated; `register_width` is one named function; per-parameter scaling never enters the frequency register. |
| Architecture | §9.1, §9.2, §9.3 | **PASS** | Contracts module is scoped to the boundaries this spec actually crosses (`Encoding -> IR`, `IR -> Oracle`), per the spec's own narrowing (FR-001/FR-002) — it does not pre-define Protocols for layers that do not exist, avoiding a premature/undesigned contract. IR represents per-parameter structure as data, not control flow. |
| Failure behaviour | §10.1, §10.3 | **PASS** | The oracle predicts/logs grid cost and refuses to exceed a configured budget without confirmation (spec FR-013); a multiplicity/tie mismatch in the IR is a detectable invalid state, not a silent guess. |
| Optimisation discipline | §5.* | **N/A** | No circuit optimisation exists at this layer — nothing to profile or prove equivalent yet. |
| Research programme (§11.*) | §11.1-§11.11 | **N/A** | This spec defines the general tied-parameter IR primitive (§11.2, §11.3) that the symmetry-restricted programme will later reuse, but performs no `Λ`-restriction, sector assertion, or separation claim itself — those are later specs' concern. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 1, then re-verified after source review)

All gates above still **PASS** after `data-model.md` and `contracts/` were written.
The one item flagged as open in the previous revision — R8's rotation-angle period —
has since been resolved in-session against `docs/references/Barthe_thesis.pdf` and
`docs/references/equivariant FCE Z2LGT report.pdf` per the newly-added Constitution
§2.5 (source verification against `docs/references/` rather than an "unverified"
marker). The period is 2 (native `α` units), not `2π`; this no longer blocks writing
`tests/oracle/test_reference_oracle.py`'s hand-derived expected values during
`/speckit-implement`. No open items remain before implementation.

## Project Structure

### Documentation (this feature)

```text
specs/001-fce-foundation-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── ir_types.py
│   ├── encoding_to_ir.py
│   ├── ir_to_oracle.py
│   └── frequency_convention.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
pyproject.toml           # package metadata; pins qiskit==2.3.1, qiskit-aer==0.17.2,
                          # numpy==1.26.4 (FR-019, verified compatible: research.md R2)

src/
└── fourierlearn/
    ├── __init__.py
    ├── frequency.py       # FR-008..FR-010: sign, parity, two's-complement, ordering,
    │                       # dft_frequencies, register_width — built FIRST (see below)
    ├── ir.py              # FR-004..FR-007, FR-021: PauliEncodedCircuitIR and its parts
    │                       # (real Qiskit Gate/PauliEvolutionGate objects, research.md R3);
    │                       # imports frequency.py
    ├── contracts.py      # FR-001, FR-002: Encoding/Oracle Protocols + extension point;
    │                       # imports ir.py's PauliEncodedCircuitIR
    └── reference.py       # FR-011..FR-013: quarantined Statevector-only oracle (research.md R6);
                            # imports ir.py, frequency.py, and contracts.py's Oracle Protocol

tests/
├── conftest.py
├── unit/
│   ├── test_frequency.py      # sign/parity/decoding/ordering + register_width unit tests (FR-010)
│   ├── test_ir.py             # tied-parameter representation, per-parameter data
│   ├── test_ir_gate_convention.py  # FR-021/SC-009: to_gate() Operator-equivalence to a
│   │                                # hand-built RZ-style gate at the expected angle (research.md R6)
│   ├── test_contracts.py     # SC-001: Protocol type-checking, extension point
│   └── test_dependency_versions.py  # FR-019 (scoped): pinned versions match installed env;
│                                     # full manifest scaffolding deferred to Spec 6 (research.md R11)
├── oracle/
│   ├── test_reference_oracle.py   # FR-016, FR-017, FR-018: single-upload + complex two-upload
│   │                                # validation, PLUS FR-020/SC-008's odd-l vanishing assertion
│   └── test_cost_budget.py        # FR-013: the cost-budget guard's own dedicated test
└── ci/
    └── test_no_forbidden_imports.py  # FR-014, FR-015: the CI import guard itself

.github/
└── workflows/
    └── ci.yml             # runs mypy + pytest (including the import-guard test) on every push/PR
```

**Structure Decision**: Single Python library, `src/`-layout (`src/fourierlearn/`),
matching the constitution's later layers (`encodings`, `circuits`, `extract`,
`backends`, `learn`, `models`, `experiment` will each become their own module under
`src/fourierlearn/` in later specs). Renamed from the original `src/fce/` to avoid a
`sys.path` collision with an unrelated legacy repository of the same name. **The
module listing above is ordered to match the strict build/dependency order** —
`frequency.py` first, then `ir.py`, then `contracts.py`, then `reference.py` — not
alphabetically and not by FR number; see tasks.md's "Phase Ordering Deviation"
section for the full rationale (`ir.py` imports `frequency.coordinate_order`/
`register_width`, so `frequency.py` must exist first, contrary to the priority
numbering US1 > US2 might otherwise suggest). The CI import guard is implemented as a
plain pytest test rather than a bespoke CI-vendor script, so "the build fails" simply
because `pytest` fails — this keeps FR-014's enforcement independent of which CI
provider ends up running it (spec Assumptions), while `.github/workflows/ci.yml` is
still scaffolded now since this spec's deliverable (e) is explicitly a CI check and no
CI configuration exists yet in this repository.

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
