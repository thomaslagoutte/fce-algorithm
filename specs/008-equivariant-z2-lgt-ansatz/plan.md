# Implementation Plan: Equivariant Z2 LGT Ansatz and Containment Verification

**Branch**: `008-equivariant-z2-lgt-ansatz` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-equivariant-z2-lgt-ansatz/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Two new production modules and one narrowly-exempt companion module:

- **`src/fourierlearn/z2lgt.py`** (deliverables a+b): `Z2LGTEdge`, `Z2LGTGraph`,
  a mechanical `_gauss_law_generators(graph)` derivation, and
  `build_z2_lgt_model(...)`, which builds the full matter+gauge Hamiltonian's
  `CouplingGroup`s with **local** per-vertex/per-edge couplings
  (research.md R1: `d = |V| + 2|E|`, cited to the primary report's own
  §5.1–5.3/eq. 25–27 — **not** an extension beyond the source, despite eq.
  1–4 elsewhere in the same report using global scalars), ties `A_e`/`B_e`
  under one `CouplingGroup` per edge (reusing the existing tie-group
  mechanism unchanged, research.md R2), and **always** attaches a derived
  Gauss law `SymmetryDeclaration` — reusing Spec 7's existing
  `PhysicalModelDescription.__post_init__` enforcement completely
  unmodified (research.md R4/R5) to satisfy Critical Mandate 1.
- **`src/fourierlearn/containment.py`** (deliverable c, pure combinatorics,
  no new CI exemption): `compute_ambient_box(ir)`, `compute_lambda(ir, ...)`
  (Theorem 6.1 eq. 36/37 — additive charge on raw `l`, multiplicative Gauss
  on `l/2 mod 2` — executed and hand-verified in research.md R2).
- **`src/fourierlearn/_containment_oracle_check.py`** (deliverable c, the
  ONE function needing a narrow, explicitly-justified CI-guard exception,
  mirroring Spec 6's `_exact_dynamics.py` isolation pattern exactly):
  extracts `Ω` via `reference.coefficients` for the empirical
  `Ω ⊆ Λ` check Constitution §11.6 requires — never used for training or
  feature construction.

All five planning mandates were executed, not promised (research.md
R1–R6):

1. **R1**: eq. 1–4 does use global scalars `J,m,f` (the architect's factual
   premise, confirmed) — but the same report's own §5.1–5.3/eq. 25–27
   already specifies the local, `d=|V|+2|E|` ansatz Spec 8 targets. The
   local-coupling Hamiltonian is therefore a direct citation to a
   different part of the same source, not a Constitution §2.3 EXTENSION —
   flagged transparently below and in the Completion Report.
2. **R2**: a real 2-matter-site/1-edge/3-qubit instance built end to end;
   `Ω ⊆ Λ ⊊ ambient` verified with concrete numbers (`|ambient|=1125`,
   `|Λ|=25`, `45x` reduction), `Λ`'s own predicate independently confirmed
   against seven hand-derived positive/negative controls before trusting
   it against the real circuit's `Ω`. A genuine, checked degeneracy (the
   default all-zero initial state sits in `h_e`'s exact zero-eigenspace)
   was found and fixed with a `FixedGate` state-prep flip, not hidden.
3. **R3**: tied `A_e`/`B_e` proven exactly equal to the combined
   generator's evolution (`diff=3.3e-16`, machine precision) via a
   dedicated `Operator`-equivalence test, independent of the coefficient-
   level construction (this project's own standing rule); untied proven to
   break `[U,Q]=0` (`max|[U,Q]|=3.8`) at distinct angles, with an
   equal-angle sanity check recovering exact commutation (`~1e-15`) to
   isolate that independence, specifically, is the failure mode.
4. **R4**: the derived Gauss law generators pass Spec 7's `verify_symmetry`
   unmodified against the **full** matter+gauge Hamiltonian (including
   hopping — stronger than Spec 7's own original fixture), and a corrupted
   generator is correctly rejected (non-vacuous negative control).
5. **R6**: no optimisation anywhere in this design (§5.3).

## Technical Context

**Language/Version**: Python 3.12 (inherited from Specs 1-7; unchanged).

**Primary Dependencies**: `qiskit` 2.3.1, `numpy`, `scipy` (`scipy.linalg.expm`,
test/research-only, matching this project's existing convention of
verifying gate-construction claims via direct `Operator`/`expm` comparison
in tests, never in production code). No new dependency.

**Storage**: N/A — pure in-memory computation over `SparsePauliOp`,
`CouplingGroup`, and `PauliEncodedCircuitIR` objects, exactly as Specs 1-7.

**Testing**: `pytest`. research.md's R2 (containment fixture + hand-derived
`Λ` controls), R3 (tied-exactness / untied-breaks-`Q` proofs), and R4
(Gauss law positive + negative control against the full Hamiltonian) all
become permanent, named tests — kept as separate test functions per this
project's established discipline (distinct claims, distinct tests).

**Target Platform**: Developer workstation and CI runner — unchanged.

**Project Type**: Continuation of the same single Python library
(`src/fourierlearn/`): two new modules plus one new, narrowly-exempt
companion module; no modification to any existing Spec 1-7 module's public
behavior (Spec 7's `PhysicalModelDescription`/`verify_symmetry`,
Spec 2/6's `CouplingGroup` tie-group mechanism, and Spec 4's
`reference.coefficients`/`predict_grid_cost` are all reused completely
unchanged).

**Performance Goals**: None (§5.3 — research.md R6: no caching, batching,
or memoization; this spec's own declared scope is small, hand-sized
instances only).

**Constraints**: `z2lgt.py` and `containment.py` MUST NOT import
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` — enforced
by the existing CI import guard with no exemption needed for either.
`_containment_oracle_check.py` is narrowly exempt for `reference` ONLY
(never `Statevector`/`Operator`/`expm` directly) — mirroring
`_exact_dynamics.py`'s exact exemption shape. Every `A_e`/`B_e` tie MUST
use the existing `CouplingGroup` mechanism (Constitution §11.2); no new
tying primitive is introduced. `build_z2_lgt_model` MUST always attach a
non-empty Gauss law `SymmetryDeclaration` (never optional) so Spec 7's
existing `__post_init__` enforcement runs unconditionally (Critical
Mandate 1).

**Scale/Scope**: Small, explicit, hand-constructed lattice instances only
(research.md R2's 2-vertex/1-edge/3-qubit fixture for the executed
containment proof) — no production-scale lattice is targeted, matching
spec.md's own Assumptions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Rule | Status | Notes |
|------|------|--------|-------|
| Measurement-only production path | Article II, §1.1, §3.3/§3.4, §9.6 | **PASS** | `z2lgt.py`/`containment.py` import nothing execution-related. `_containment_oracle_check.py` imports only `reference.coefficients`, mirroring the one existing precedent exactly. |
| Symmetry declared and verified before the ansatz is trusted | Critical Mandate 1; Constitution §11.1 | **PASS** | research.md R4: executed, including a discriminating negative control, against the FULL matter+gauge Hamiltonian. Enforcement reused from Spec 7 `__post_init__`, unmodified. |
| Target Hamiltonian is full matter+gauge, local couplings | Critical Mandate 3; FR-002 | **PASS** | research.md R1/R2: `d=|V|+2|E|` cited to report §5.1-5.3/eq.25-27, executed end to end on a real instance. |
| Parameter tying (A_e, B_e) | Constitution §11.2; FR-006/FR-007/FR-008 | **PASS** | research.md R3: tied exactness and untied `U(1)_Q` breakage both executed, with a sanity-isolating equal-angle control. |
| Containment: `Ω ⊆ Λ ⊊ ambient`, verified empirically | Constitution §11.4/§11.5/§11.6; FR-009..FR-012 | **PASS** | research.md R2: executed on a real instance with a concrete reduction factor; `Λ`'s own predicate independently validated against 7 hand-derived controls before trusting it against `Ω`. |
| Honest measurement-advantage claim, no separation on Z₂ | Constitution §11.7/§11.8; Critical Mandate 2; FR-013/FR-014 | **PASS** | research.md R2's explicit honest-scope note: the `45x` reduction is this instance's own exact number, not fitted to or presented as confirming the asymptotic `2^{-(d+|V|)}` formula, and no separation claim is made. |
| Gate contiguity for the commuting family `F` | Constitution §11.9/§11.10; FR-005 | **PASS** | research.md R5: `build_z2_lgt_model` declares mass/electric/hopping groups in fixed order; `circuits.py` preserves IR gate order exactly (unmodified, no reordering stage exists to violate contiguity). Asserted directly on the IR's own gate tuple in tests, not merely commented. |
| CI import guard, narrow exemption | Constitution §3.4; Article II | **PASS, with a required, explicit, backward-compatible widening** | See Complexity Tracking below — this is not a violation, it is the same narrow-exception pattern Spec 6 already established, applied a second time. |
| Optimisation discipline | §5.3 | **PASS** | research.md R6. |
| Architecture / no duplicated call paths | §9.1, §9.4 | **PASS** | `build_z2_lgt_model` constructs a `PhysicalModelDescription` through the same constructor `build_tfim_model` uses; no parallel validation or compilation path. |

No violations requiring justification beyond the CI-guard widening, which
is fully specified in Complexity Tracking (a mechanical, precedented
change, not an open design question).

### Post-design re-check (after Phase 0 research)

All gates above hold after research.md's executed work. The central risks
this round's mandates targeted — whether the local-coupling Hamiltonian is
actually grounded in the source (R1: yes, §5.1-5.3, not an extension),
whether the containment claim actually holds on a real instance rather
than only in the abstract (R2: yes, with concrete numbers and independent
predicate validation), whether tying is provably exact and untying
provably breaks the symmetry (R3: yes, to machine precision both ways),
and whether the Gauss law genuinely passes the *existing*, unmodified
verification engine against the *full* Hamiltonian (R4: yes, plus a
discriminating negative control) — were all resolved by execution, not
argument. The one open, explicitly-scoped item is the CI-guard widening
(mechanical, fully specified, not a design risk) and the honest note that
R2's fixture, while genuinely non-trivial, exercises the hopping
coordinate more directly than the cross-coupled mass/electric Gauss
relation within `Ω` itself (mitigated by the independent hand-derived
`Λ`-predicate controls). No other open items remain before `/speckit-tasks`.

## Project Structure

### Documentation (this feature)

```text
specs/008-equivariant-z2-lgt-ansatz/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

*(Scoped to plan.md + research.md only, matching Specs 2-7's own precedent
— no data-model.md/contracts/quickstart.md: this feature's "data model" is
fully captured by the dataclasses listed below, and its "contract" is the
same Python function-signature contract style Specs 5-7 used inline.)*

### Source Code (repository root)

```text
src/
└── fourierlearn/
    ├── frequency.py                # Spec 1 — unchanged; register_width/
    │                                  pre_parity_range reused verbatim
    ├── ir.py                        # Spec 1 — unchanged; FixedGate reused
    │                                  for the containment fixture's
    │                                  initial-state flip
    ├── reference.py                 # Spec 1 — unchanged; imported ONLY by
    │                                  the new _containment_oracle_check.py
    ├── contracts.py                 # Spec 1/5 — unchanged
    ├── encodings/
    │   ├── pauli_pqc.py             # Spec 2 — unchanged; build_ir and the
    │   │                              shared little-endian padding helper
    │   │                              reused for the Gauss law generators
    │   └── trotter.py               # Spec 2 — unchanged; CouplingGroup's
    │                                  existing tie-group mechanism reused
    │                                  unmodified for A_e/B_e tying
    ├── circuits.py                  # Spec 3 — unchanged; gate order
    │                                  preserved exactly (no reordering
    │                                  stage exists to break contiguity)
    ├── extract.py                   # Spec 4 — unchanged
    ├── learn.py                     # Spec 5 — unchanged
    ├── _exact_dynamics.py           # Spec 6 — unchanged
    ├── experiment.py                # Spec 6 — unchanged
    ├── models.py                    # Spec 6/7 — unchanged; PhysicalModelDescription's
    │                                  existing __post_init__ enforcement
    │                                  reused unmodified (Critical Mandate 1)
    ├── symmetry.py                  # Spec 7 — unchanged; verify_symmetry
    │                                  reused unmodified
    ├── z2lgt.py                     # NEW — Z2LGTEdge, Z2LGTGraph,
    │                                  _gauss_law_generators, build_z2_lgt_model
    ├── containment.py               # NEW — compute_ambient_box, compute_lambda,
    │                                  ContainmentVerificationResult (the
    │                                  reduction factor + honest
    │                                  no-separation caveat as a structural field)
    └── _containment_oracle_check.py # NEW — the ONE function extracting
                                        Omega via reference.coefficients;
                                        narrowly CI-guard exempt for
                                        `reference` only

tests/
├── unit/
│   ├── test_z2lgt_hamiltonian_construction.py   # FR-001/FR-002: term
│   │                                               library restriction,
│   │                                               local couplings, d=|V|+2|E|
│   ├── test_z2lgt_gauss_law_hook.py              # FR-003/FR-004: Gauss law
│   │                                               declared and verified;
│   │                                               corrupted generator rejected
│   ├── test_z2lgt_gate_contiguity.py             # FR-005: commuting block
│   │                                               F stays contiguous
│   ├── test_z2lgt_tying_exactness.py             # FR-006/FR-007: tied ==
│   │                                               combined generator's
│   │                                               evolution, Operator-exact
│   ├── test_z2lgt_untying_breaks_charge.py       # FR-008: untied breaks
│   │                                               [U,Q]=0; equal-angle
│   │                                               sanity control
│   └── test_containment_lambda_predicate.py      # FR-009: the 7 hand-derived
│                                                    positive/negative controls
└── oracle/
    └── test_containment_omega_subset_lambda.py   # FR-010/FR-011/FR-012/FR-013/FR-014:
                                                     the full, executed
                                                     Omega subset-of Lambda
                                                     subset-of ambient proof
                                                     on the real instance,
                                                     plus the mandatory
                                                     no-separation caveat

tests/ci/
└── test_no_forbidden_imports.py     # MODIFIED — _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY
                                        widened from a str to a tuple
                                        (adds "_containment_oracle_check.py");
                                        find_violations' internal check
                                        changes `==` to `in`; the 3 existing
                                        Spec 6 tests indexing the bare
                                        constant as a path segment are
                                        updated to index element [0]
```

**Structure Decision**: two new, unexempt modules (`z2lgt.py`,
`containment.py`) plus one new, narrowly-exempt single-function module
(`_containment_oracle_check.py`), matching Spec 6's own precedent for
isolating oracle access. No existing Spec 1-7 module's public behavior
changes — `PhysicalModelDescription`, `verify_symmetry`, `CouplingGroup`,
and `reference.coefficients`/`predict_grid_cost` are all reused completely
unmodified, confirmed by direct execution in research.md, not merely
assumed compatible.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| A second narrow CI-guard exemption (`_containment_oracle_check.py`, widening `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` from a `str` to a `tuple`) | Constitution §11.6 *requires* verifying `Ω ⊆ Λ` "by brute-force support extraction against the oracle" before any `Λ`-restricted extraction is trusted — the oracle is `reference.coefficients`, importable in production only from `reference.py` itself absent an exception. This is not optional polish; §1's Hard Prohibition #6 makes an *unverified* `Λ`-restriction a forbidden state, so the verification path must exist somewhere reachable in production, not only in a one-off test script. | Running the oracle check only inside `tests/` (never in `src/`) was considered and rejected: spec.md's FR-009..FR-012 phrase this as a system capability ("the system MUST compute Λ... MUST extract Ω... MUST assert Ω⊆Λ"), matching Constitution §11.4's own requirement that Λ be "a named pre-processing stage with its own module" — a capability a future spec (or a report script) needs to invoke on a *new* instance, not only ever re-derivable by hand in a test. Isolating it into its own single-function module (rather than adding the import to a larger module) exactly mirrors Spec 6's own already-accepted `_exact_dynamics.py` precedent, keeping the exemption's blast radius minimal and independently justified. |
