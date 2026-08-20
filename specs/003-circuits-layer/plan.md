# Implementation Plan: Circuits Layer

**Branch**: `003-circuits-layer` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-circuits-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A single new module (`src/fourierlearn/circuits.py`) compiling a Foundation-Layer
`PauliEncodedCircuitIR` into two circuits: (1) `compile_frequency_circuit` — the
unconditional "parity-fold" circuit `A(U)` (Barthe thesis Theorem 5.1) that
appends one frequency-counter register per encoded parameter (reusing Spec 1's
`register_width`), computes each encoding gate's qubit parity onto one single,
shared, serially-reused ancilla, and applies a controlled increment (even
parity) or decrement (odd parity) to that parameter's register; and (2)
`compile_observable_circuit` — the observable-folded circuit `A(U, O)` (Barthe
thesis Corollary 5.1, Figure 5.4) that combines a forward pass, a direct
insertion of the (single Pauli-string) observable, and the literal inverse of
the assembled forward circuit as the reversed pass, all sharing the identical
frequency registers. Non-`Z` encoding gates are compiled via a single shared
basis-change helper (`W_X=H`, `W_Y=S·H`, both derived and verified in-session,
not assumed) rather than a native per-letter fold rule.

Every sign, parity convention, gate ordering, and basis-change identity in this
plan was verified computationally before being written down — culminating in a
3-parameter, two-tied-multiplicity, fully-interleaved stress case (research.md
R5.4) confirming the reversed-pass construction holds under genuine
multi-parameter contention on the shared ancilla, not only in a simplified
case. See research.md for the full verification trail, including two
verification-code bugs it caught and fixed along the way (R3, R5.5).

## Technical Context

**Language/Version**: Python 3.12 (inherited from Spec 1/2; same pinned
interpreter, no change).

**Primary Dependencies**: `qiskit` 2.3.1 (already pinned) —
`qiskit.circuit.library.UnitaryGate`/`.control()` for the ancilla-controlled
frequency-register shift (`V+`/`V-`), `qiskit.circuit.QuantumCircuit.inverse()`
for the reversed pass (research.md R5), `qiskit.quantum_info.Operator`/`.equiv()`
for the dedicated sign/ordering equivalence tests (FR-011). No new third-party
dependency is introduced. This layer constructs circuits; it does not execute
them (`qiskit-aer` is not imported here) — that remains Spec 1's oracle for
this spec's own validation tests, and later a `circuits`-consuming `extract`
layer spec.

**Storage**: N/A — pure computation over in-memory circuit objects, same as
Spec 1/2.

**Testing**: `pytest`, reusing Spec 1's `fourierlearn.reference.coefficients`
oracle directly for this spec's own validation tests (FR-012) — no new
ground-truth mechanism is introduced. Dedicated sign/ordering equivalence
tests (FR-011) compare against hand-built target matrices via
`qiskit.quantum_info.Operator`/`.equiv()`, following Spec 1's own
`test_ir_gate_convention.py` precedent exactly.

**Target Platform**: Developer workstation and CI runner — unchanged from
Spec 1/2.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding one new module.

**Performance Goals**: None (Constitution §5.3 — no optimisation without a
recorded profile and a bottleneck it targets; this layer performs no circuit
*execution* at all, only circuit *construction*).

**Constraints**: Must reuse, not duplicate, Spec 1's `register_width` and
frequency-sign convention (§6.1, §6.3, §9.4). Must use exactly one shared
ancilla, reused serially across every encoding gate regardless of parameter
(research.md R4) — verified under contention, not merely asserted (research.md
R5.4). Must implement the reversed pass as a literal circuit inverse, not a
second hand-maintained construction (research.md R5, all three stress levels).
Must use one single shared basis-change helper for both encoding-gate
compilation (User Story 1) and observable folding (User Story 2/3) (FR-014,
research.md R6/R7). Scoped to a single Hermitian Pauli-string observable per
compilation — the weighted-sum/LCU extension (Barthe thesis Figure 5.5) is an
explicit, named `TODO` deferred to a later spec (spec.md Assumptions).

**Scale/Scope**: Small validation circuits only for this spec's own tests
(1–3 qubits, 1–3 encoded parameters) — no production circuit sizes are
targeted here, same scope discipline as Spec 1/2.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Architecture / no duplicated call paths | §9.1, §9.2, §9.4 | **PASS** | `circuits.py` sits between `encodings` and (a future) `extract` per the pipeline order; `compile_observable_circuit` calls `compile_frequency_circuit` and the one shared basis-change helper rather than reimplementing either (research.md R1, R6, R7). |
| One code path regardless of size | §9.3 | **PASS** | Neither compiler branches on parameter count, tie multiplicity, or which Pauli letter an encoding gate uses (the basis-change helper is called uniformly, per-letter, never with a special-cased "already Z" branch — research.md R7); per-parameter/per-gate structure is data (the IR's own `gates` tuple), not control flow. |
| Physics decisions live in the model layer | §9.5, §11.2 | **PASS** | This layer performs no new physics decisions beyond what Spec 1's IR already encodes (tie-group commutativity, coefficient uniformity); it purely compiles the IR's existing structure into a circuit. |
| Per-parameter scaling never enters the frequency register | §6.4 | **PASS** | The frequency register holds only the integer pre-parity value `l`; `PauliTerm.coefficient` (already folded into the gate's rotation angle by Spec 1's `to_gate()`) never appears in the register itself — unchanged from Spec 1's own guarantee. |
| Classical input vs. encoded parameter | §7.1 | **PASS** (N/A) | This layer has no classical-input/encoded-parameter distinction of its own to make — it compiles whatever `PauliEncodedCircuitIR` it is given, which already embodies that distinction (Spec 1/2). |
| Validation protocol, non-trivial tests | §4.1, §4.3 | **PASS** | Both compiled constructions are validated against Spec 1's own oracle (FR-012) with a genuinely complex, non-degenerate case for each (FR-013) — verified in research.md R8 (a three-upload construction found by exhaustive search after the originally-assumed R6 fixture turned out, when actually computed, to be purely real, not complex) and R5.2–R5.4 (non-DC, non-degenerate coefficients at every stress level), not a case that happens to be purely real. |
| Failure behaviour | §10.1 | **PASS** | A zero-parameter `PauliEncodedCircuitIR` raises (FR-009) rather than silently compiling a meaningless circuit. |
| Optimisation discipline | §5.3 | **PASS** | No caching, batching, or template reuse anywhere in this design (research.md R10) — nothing here has a recorded profile or bottleneck to justify any. |
| Verification discipline (this spec's own mandate) | §2.1, §9.7 | **PASS** | Every sign/coefficient/ordering claim in this plan was computationally verified in research.md before being written down — including a final, deliberately harder 3-parameter/2-tied-multiplicity stress test (R5.4) run specifically because the plan's author correctly judged a simpler case insufficient to earn the mandate. Two verification-code bugs were caught and fixed along the way (R3, R5.5), not silently corrected. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's verification work, not merely at the
outline stage. Three items were only confirmed correct *during* research, not
assumed beforehand: (1) the parity-to-increment/decrement sign convention
(research.md R3 — the first candidate assignment tried was wrong and was
caught against ground truth, not assumed correct from the thesis's informal
description); (2) the reversed-pass identity holding under genuine
multi-parameter, tied-multiplicity, interleaved, shared-ancilla contention,
not only in a minimal case (research.md R5.2–R5.4); (3) that a single
Pauli-string observable needs no basis-change wrapping to be inserted directly
at the `A(U,P)` observable point — a real architectural finding, not assumed
from the thesis's "WLOG" remark, which turned out to describe the derivation's
proof strategy rather than a strict implementation requirement for the
single-observable case this spec is scoped to (research.md R7). No open items
remain before `/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/003-circuits-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Spec 2's own precedent —
`data-model.md`/`contracts/`/`quickstart.md` are not generated here; the one
new module's data shapes are fully specified in research.md R1/R6/R7 instead.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py        # Spec 1 — unchanged, imported for register_width
    ├── ir.py                # Spec 1 — unchanged, imported for PauliEncodedCircuitIR/PauliTerm
    ├── contracts.py         # Spec 1 — unchanged
    ├── reference.py         # Spec 1 — unchanged; used only by this spec's own validation tests
    ├── encodings/            # Spec 2 — unchanged; used only by this spec's own test fixtures
    │   ├── pauli_pqc.py
    │   └── trotter.py
    └── circuits.py           # NEW — FR-001..FR-014: compile_frequency_circuit(),
                                # compile_observable_circuit(), the shared
                                # basis-change helper

tests/
├── unit/
│   ├── test_circuits_parity_fold.py     # US1, FR-002..FR-005, FR-009..FR-010
│   ├── test_circuits_gate_convention.py # FR-011: dedicated Operator-equivalence
│   │                                     # tests for the parity sign, the
│   │                                     # reversed-pass identity (at the
│   │                                     # multi-parameter/tied/interleaved
│   │                                     # stress level from research.md R5.4,
│   │                                     # not only the minimal case), and the
│   │                                     # X/Y basis-change gates
│   └── test_circuits_observable_fold.py # US2/US3, FR-006..FR-008, FR-014
└── oracle/
    └── test_circuits_validation.py       # US-level validation, FR-012..FR-013:
                                            # both compiled constructions run
                                            # through fourierlearn.reference
                                            # .coefficients(), each with a
                                            # genuinely complex non-DC
                                            # coefficient (research.md R8)
```

**Structure Decision**: One new module (`circuits.py`) directly under the
existing `src/fourierlearn/` library, matching the constitution's own
pipeline-layer name (§9.1). No existing Spec 1/2 file is modified — this
feature only imports from `frequency.py`, `ir.py`, `contracts.py`, and (for
tests only) `reference.py` and `encodings/`. `compile_observable_circuit`
imports from `compile_frequency_circuit` within the same module (Constitution
§9.4 — reuse, not a duplicated call path); the basis-change helper is called
by both, never independently reimplemented (FR-014).

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
