# Implementation Plan: Symmetry Verification Layer

**Branch**: `007-symmetry-verification-layer` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-symmetry-verification-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

One new module, `src/fourierlearn/symmetry.py`, exposing
`verify_symmetry(generators, hamiltonian_terms) -> SymmetryVerificationResult`
— a purely algebraic check (`qiskit.quantum_info.SparsePauliOp`
commutator/anticommutator relations only, no `QuantumCircuit`,
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` import, and
no CI-guard exception needed) of Constitution §11.1's three conditions:
**internal** (classical-input independence — research.md R1's executed
Vacuous Truth Test found this is a genuine, non-trivial runtime check, not
a type-level guarantee, since `SparsePauliOp` legitimately accepts a
symbolic coefficient), **non-annihilating** (every generator commutes with
every Hamiltonian term), and **Abelian** (every pair of generators
commutes). Spec 6's `SymmetryDeclaration` (`src/fourierlearn/models.py`)
gains one new, defaulted field (`generators`) so every existing call site
is unaffected. `build_tfim_model` becomes the classical validation hook:
when a declaration with generators is attached, it calls
`verify_symmetry` against the model's own Hamiltonian terms and rejects
construction — before any circuit-compilation module is ever reached —
if any condition fails.

All four planning mandates were executed, not promised:

1. **research.md R1**: the Vacuous Truth Test found the *opposite* of
   what was hypothesized — `SparsePauliOp` legitimately accepts a symbolic
   `Parameter` coefficient, so "internal" is not vacuously true and needed
   (and got) a real runtime check, executed against both a concrete and a
   symbolic generator.
2. **research.md R2**: a concrete Z₂ Gauss law (three genuinely different,
   site-indexed generators on a 3-vertex path lattice) executed and
   confirmed to pass all three §11.1 conditions — directly resolving the
   2026-08-21 clarify session's correction.
3. **research.md R3**: a Z-twirl candidate executed against the lattice's
   own gauge-field kinetic term `H_g`, confirmed to fail non-annihilating
   specifically (anticommutes with `H_g`'s `IX` term) while still passing
   internal and Abelian — an isolated, unconfounded negative control. A
   real `numpy.bool_` vs. Python `bool` identity pitfall was found and
   fixed during this same execution.
4. **research.md R5**: no optimisation anywhere in this design.

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-6; unchanged).

**Primary Dependencies**: `qiskit` 2.3.1 (`qiskit.quantum_info.SparsePauliOp`,
`qiskit.circuit.ParameterExpression`), already pinned — no new dependency.
This is the first feature in this project whose production code touches
**no** other `fourierlearn` execution module at all (no `qiskit-aer`,
`numpy`, or `scikit-learn` import) — it is pure Pauli-string algebra.

**Storage**: N/A — pure in-memory computation over immutable
`SparsePauliOp` objects.

**Testing**: `pytest`. research.md R1's Vacuous Truth Test, R2's Gauss law
positive control, and R3's Z-twirl negative control all become permanent,
named tests — kept as separate test functions (the project's established
discipline: distinct claims, distinct tests, never merged).

**Target Platform**: Developer workstation and CI runner — unchanged.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding one new module and one additive field to an
existing Spec 6 dataclass.

**Performance Goals**: None (§5.3 — research.md R5: no caching, batching,
or memoization; all inputs are small and fixed-size for this spec's own
scope).

**Constraints**: `symmetry.py` MUST NOT import `QuantumCircuit`,
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` — enforced
by the existing, unmodified CI import guard (no new exemption). The
"internal" check MUST be a real runtime check
(`is_classical_input_independent`, research.md R1) — never documented as
an always-true type-level guarantee. Every `.commutes()` result MUST be
compared with `==`/`bool(...)`, never `is True`/`is False` (research.md
R3's own pitfall). `SymmetryDeclaration`'s new `generators` field MUST
default to `()` so every existing Spec 6 call site is unaffected.

**Scale/Scope**: Small, explicit, hand-constructed generator/Hamiltonian
fixtures only — the 3-vertex path lattice (research.md R2/R3) for the
Gauss-law/Z-twirl cases, plus the small TFIM instance Spec 6 already uses.
No production-scale lattice is targeted here.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Measurement-only production path | Article II, §1.1, §9.6 | **PASS** | `symmetry.py` imports nothing execution-related at all — confirmed by the unmodified CI guard (no exemption needed, unlike Spec 6's `_exact_dynamics.py`). |
| Pure Algebra, No Quantum Execution | Clarifications 2026-08-21 (FR-004) | **PASS** | research.md R1-R3 executed every check via `SparsePauliOp`/`Pauli.commutes()` only — no circuit ever built. |
| Symmetry legality checked before implementation | §11.1 | **PASS** | This entire feature exists to implement exactly this; research.md R2 proves the check gives the theoretically correct verdict on the actual Z₂ Gauss law, not merely a formula that looks right. |
| "Internal" correctly distinguished from "site-uniform" | Clarifications 2026-08-21 | **PASS** | research.md R1/R2: the check is classical-input independence; R2's three Gauss law generators are confirmed genuinely different per site and still pass. |
| Non-annihilating grounded in the named theory case | Clarifications 2026-08-21 (FR-002) | **PASS** | research.md R3: the `Z`-twirl-vs-`H_g` case executed and confirmed to fail, isolated from the other two conditions. |
| Rejections recorded with failure mode | §8.4 | **PASS** | `SymmetryVerificationResult` reports every condition's individual pass/fail and the specific offending term/generator pair (FR-006/FR-007). |
| Generic architecture, no model-specific branch | Clarifications 2026-08-21 (FR-005) | **PASS** | `verify_symmetry` takes only `(generators, hamiltonian_terms)` — no model-identifying argument exists for a branch to key on. |
| Architecture / no duplicated call paths | §9.1, §9.4 | **PASS** | `SymmetryDeclaration`'s extension is additive; `build_tfim_model`'s hook calls `verify_symmetry` directly, no parallel validation path. |
| Optimisation discipline | §5.3 | **PASS** | research.md R5. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's executed verification work. The
central risk this round's mandates targeted — that the "internal" check
might either be vacuous (mandate #1) or might reproduce the exact physics
error the clarify session caught (mandates #2/#3) — was resolved by
execution, not argument: R1 found the check is genuinely non-vacuous (the
opposite of the initial hypothesis), and R2/R3 together prove the engine
gives the *theoretically correct* verdict on both the real Gauss law
(accept) and the naive, wrong `Z`-twirl alternative (reject, for the
specific §11.1(b) reason). No open items remain before `/speckit-tasks`,
except the citation-verification flag research.md R2 and spec.md's own
Assumptions already name (the exact Pauli-letter convention for the
Gauss law/`H_g` should be checked against a specific cited reference
before implementation treats it as more than a structural example).

## Project Structure

### Documentation (this feature)

```text
specs/007-symmetry-verification-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2-6's own precedent.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py           # Spec 1 — unchanged
    ├── ir.py                   # Spec 1 — unchanged
    ├── reference.py             # Spec 1 — unchanged; not imported by this feature at all
    ├── contracts.py              # Spec 1/5 — unchanged
    ├── encodings/                 # Spec 2 — unchanged
    ├── circuits.py                 # Spec 3 — unchanged; never invoked by this feature
    ├── extract.py                   # Spec 4 — unchanged
    ├── learn.py                      # Spec 5 — unchanged
    ├── _exact_dynamics.py             # Spec 6 — unchanged
    ├── experiment.py                   # Spec 6 — unchanged
    ├── models.py                        # Spec 6 — MODIFIED: `SymmetryDeclaration`
    │                                      # gains a new, defaulted `generators` field
    │                                      # (FR-012); `build_tfim_model` gains the
    │                                      # classical validation hook (FR-010)
    └── symmetry.py                        # NEW — FR-001..FR-009: verify_symmetry(),
                                             # SymmetryVerificationResult,
                                             # is_classical_input_independent()

tests/
└── unit/
    ├── test_symmetry_vacuous_truth.py       # research.md R1: both attempts, promoted
    ├── test_symmetry_gauss_law_positive.py   # research.md R2: the Gauss law positive
    │                                          # control, promoted
    ├── test_symmetry_ztwirl_negative.py       # research.md R3: the Z-twirl negative
    │                                          # control (+ its isolation sanity check),
    │                                          # promoted, kept separate from R2's file
    ├── test_symmetry_abelian_failure.py        # a simple non-commuting-pair negative
    │                                            # control for "Abelian" specifically
    │                                            # (not covered by R2/R3, both of which
    │                                            # are all-X or all-Z and trivially
    │                                            # Abelian either way)
    ├── test_symmetry_degenerate_declarations.py # FR-008/FR-009: zero generators,
    │                                              # identity generator, qubit-count
    │                                              # mismatch
    └── test_models_symmetry_validation_hook.py    # FR-010/FR-011: build_tfim_model
                                                      # rejects before compilation;
                                                      # unchanged behavior without a
                                                      # declaration or with a valid one
```

**Structure Decision**: One new module (`symmetry.py`), matching the
constitution's own pipeline positioning (a classical, pre-compilation
validation stage feeding into `models.py`, per §9.1's `... → models →
experiment` — this feature sits structurally alongside `models.py`, not
after `circuits.py`). One additive field on an existing Spec 6 dataclass;
no other Spec 1-6 file's behavior changes. The CI import guard requires no
modification at all for this feature — the first feature since Spec 4
(inclusive) for which that is true.

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
