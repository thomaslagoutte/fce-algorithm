# Implementation Plan: Encodings Layer

**Branch**: `002-encodings-layer` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-encodings-layer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Two frontends that lower a domain-familiar circuit description into the Foundation
Layer's `PauliEncodedCircuitIR`, plus validation proving both against Spec 1's
reference oracle: (1) a Pauli-PQC frontend (`build_ir`) taking an ordered list of
Pauli-string uploads (parameter label, tie group, real coefficient) and delegating
all structural validation to `PauliEncodedCircuitIR`'s own constructor; (2) a
Trotter frontend (`trotter_frontend`) taking one or more **coupling groups** (Pauli
terms sharing one unknown coupling, each with a known weight), a fixed evolution
time `τ`, and a fixed Trotter step count `r`, computing each term's coefficient as
`c = -h·τ/(π·r)` — re-derived and verified in-session against the actual target
unitary, not assumed from the user-supplied formula, which omitted a load-bearing
sign — and delegating to the Pauli-PQC frontend rather than duplicating its logic
(Constitution §9.4). The encoded (unknown, extracted) parameters are the
Hamiltonian's own coupling constants; evolution time and Trotter step count are
fixed classical arguments, never swept.

Both frontends validate their own inputs explicitly (non-empty uploads/groups,
uniform per-group weight, pairwise-commuting tied terms — a check Spec 1's IR does
not perform and this layer must, per Constitution §9.5/§11.2) rather than relying
solely on Spec 1's downstream rejections, which — per explicit instruction — is
verified with a dedicated test (`trotter_frontend(groups, tau=0, r=5, ...)` must
raise), not assumed from Spec 1's separately-scoped coefficient-zero rejection.

No optimisation of any kind is introduced (Constitution §5.3): no caching, no
batching, no parameterised-template reuse — each call does one pass of validation
and construction, independent of input size (§9.3).

## Technical Context

**Language/Version**: Python 3.12 (inherited from Spec 1; same pinned interpreter,
no change).

**Primary Dependencies**: `qiskit` 2.3.1 (already pinned by Spec 1) —
`qiskit.quantum_info.Pauli`/`SparsePauliOp` for tie-group commutativity checking and
observable/IR construction; no new third-party dependency is introduced. This layer
does not execute or simulate any circuit itself (that remains Spec 1's oracle, used
only for this spec's own validation tests, and later the `circuits`/`extract`
layers) — `qiskit-aer` is not imported here.

**Storage**: N/A — pure computation over in-memory data structures, same as Spec 1.

**Testing**: `pytest`, reusing Spec 1's `fourierlearn.reference.coefficients` oracle
directly for this spec's own validation tests (FR-011–FR-013) — no new ground-truth
mechanism is introduced; ground truth for the "genuinely complex" validation cases
was derived and independently cross-checked numerically in this session
(research.md R8), not asserted from memory.

**Target Platform**: Developer workstation and CI runner — unchanged from Spec 1.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`), adding an `encodings` subpackage.

**Performance Goals**: None (Constitution §5.3 — no optimisation without a recorded
profile and a bottleneck it targets; this layer performs no circuit execution at
all, only IR construction).

**Constraints**: Must reuse, not duplicate, IR-construction logic between the two
frontends (§9.4). Must not introduce fixed-gate support beyond spec FR-001's literal
scope (parameterised Pauli-string uploads only) — verified unnecessary even for the
"genuinely complex" validation requirement (research.md R8). Must not perform any
caching, batching, or parameterised-template optimisation (§5.3).

**Scale/Scope**: Small validation circuits only for this spec's own tests (1–2
qubits, 1–2 coupling groups) — no production circuit sizes are targeted here, same
scope discipline as Spec 1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Architecture / no duplicated call paths | §9.1, §9.2, §9.4 | **PASS** | `encodings/` sits between `ir` and `circuits` per the pipeline order; the Trotter frontend imports and calls the Pauli-PQC frontend's `build_ir` rather than reimplementing IR construction (research.md R1, R3). |
| One code path regardless of size | §9.3 | **PASS** | Neither frontend branches on the number of uploads/groups/terms; per-item structure is data (a `Sequence[PauliUpload]`/`Sequence[CouplingGroup]`), not control flow (research.md R2, R3, R9). |
| Physics decisions live in the model layer | §9.5, §11.2 | **PASS** | Tied-term commutativity — required for "sum of commuting Pauli strings" (§11.2) to mean what it claims — is validated here, in the encodings layer, precisely because it is a physics decision the generic Foundation IR correctly does not make (research.md R6, verified Spec 1's IR does not check this). |
| Per-parameter scaling never enters the frequency register | §6.4 | **PASS** | `h`, `τ`, `r` are combined into each `PauliTerm.coefficient` (`c = -h·τ/(π·r)`, research.md R4); Spec 1's IR already keeps `coefficient` out of the register itself (its own FR-007). |
| Classical input vs. encoded parameter | §7.1 | **PASS** | Per-term weights, `τ`, and `r` are known classical inputs selecting fixed structure; the coupling constants are the unknown, encoded parameters — the entire point of this spec's paradigm-shift revision. |
| Validation protocol, non-trivial tests | §4.1, §4.3 | **PASS** | Both frontends are validated against Spec 1's oracle (FR-011–FR-013); each frontend's own validation case is independently verified to produce a genuinely complex (not merely nonzero) non-DC coefficient (research.md R8), not a shared or degenerate one. |
| Failure behaviour | §10.1 | **PASS** | `r<=0`, `tau==0`, empty groups/uploads, non-uniform per-group weight, and non-commuting tied terms all raise explicitly with a message naming the actual problem (research.md R7), rather than silently proceeding or relying solely on a downstream, less-specific rejection. |
| Optimisation discipline | §5.3 | **PASS** | No caching, batching, or template reuse anywhere in this design (research.md R9) — nothing here has a recorded profile or bottleneck to justify any. |

No violations requiring Complexity Tracking.

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's verification work, not merely at the
outline stage. Two items were only confirmed correct *during* research, not assumed
beforehand: the commutativity requirement (§11.2/§9.5 — Spec 1's IR was checked and
confirmed not to enforce this, making it this layer's responsibility) and the
sign of the coefficient formula (§2.2/§9.7-style verification discipline — the
user-supplied formula was checked against the target unitary and corrected). No
open items remain before `/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/002-encodings-layer/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to exactly what was requested this round — `plan.md` and `research.md`
only. `data-model.md`/`contracts/`/`quickstart.md` are not generated here; the data
shapes and contracts are fully specified in research.md R2/R3 instead. Say the word
if you want the standard Phase 1 artifact set added before `/speckit-tasks`.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py        # Spec 1 — unchanged, imported for coordinate_order
    ├── ir.py                # Spec 1 — unchanged, imported for PauliEncodedCircuitIR/PauliTerm
    ├── contracts.py         # Spec 1 — unchanged; both frontends satisfy the Encoding Protocol
    ├── reference.py         # Spec 1 — unchanged; used only by this spec's own validation tests
    └── encodings/
        ├── __init__.py
        ├── pauli_pqc.py      # FR-001..FR-005: PauliUpload, build_ir()
        └── trotter.py        # FR-006..FR-010: CouplingGroupTerm, CouplingGroup,
                                # trotter_frontend() — imports build_ir from pauli_pqc.py

tests/
├── unit/
│   ├── test_pauli_pqc.py     # US1 acceptance scenarios, FR-001..FR-005
│   └── test_trotter.py       # US2 acceptance scenarios, FR-006..FR-010 — INCLUDES
│                               # test_trotter_frontend_rejects_zero_evolution_time,
│                               # asserting trotter_frontend(groups, tau=0, r=5, ...)
│                               # raises: verified directly, per explicit instruction,
│                               # not inferred from Spec 1's separate coefficient-zero test
└── oracle/
    └── test_encodings_validation.py  # US3, FR-011..FR-013: both frontends' lowered
                                        # IR executed through fourierlearn.reference
                                        # .coefficients(), each with its own genuinely
                                        # complex non-DC coefficient (research.md R8)
```

**Structure Decision**: A new `encodings/` subpackage under the existing
`src/fourierlearn/` library, matching the constitution's own pipeline-layer name
(§9.1) rather than a generic name. No existing Spec 1 file is modified — this
feature only imports from `frequency.py`, `ir.py`, `contracts.py`, and (for tests
only) `reference.py`. `trotter.py` imports from `pauli_pqc.py` within the same
package (Constitution §9.4 — reuse, not a duplicated call path); no other coupling
between the two frontend modules exists.

## Complexity Tracking

*No Constitution Check violations — table intentionally omitted.*
