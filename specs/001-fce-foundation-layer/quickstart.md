# Quickstart: Validating the FCE Foundation Layer

This guide proves the foundation layer works end-to-end, once implemented per
[plan.md](./plan.md), [data-model.md](./data-model.md), and [contracts/](./contracts/).
It is a validation/run guide only — implementation lives in `tasks.md` and the
`/speckit-implement` phase, not here.

## Prerequisites

- Python 3.12 (matching research.md R2's verified interpreter).
- `pip install -e ".[dev]"` from the repo root, installing the pinned `qiskit==2.3.1`,
  `qiskit-aer==0.17.2`, `numpy==1.26.4`, plus `pytest` and `mypy` (dev extras).

## Setup

```bash
cd fce-algorithm
pip install -e ".[dev]"
```

## Run the full validation suite

```bash
pytest tests/ -v
mypy src/fourierlearn/
```

**Expected outcome**: all tests pass, `mypy` reports no errors. In particular:

- `tests/unit/test_frequency.py` passes — confirms the pinned sign/parity/decoding/
  ordering functions and the `register_width` unit-test table
  (contracts/frequency_convention.md) match hand-computed values.
- `tests/unit/test_ir.py` passes — confirms a `PauliEncodedCircuitIR` with a tied,
  `r_j = 2` parameter reports upload count, multiplicity, and coefficients correctly,
  and rejects a construction where multiplicity does not evenly divide the tied term
  count (data-model.md's "Parameter" validation rules).
- `tests/oracle/test_reference_oracle.py` passes — the two required scenarios below,
  **including** the required odd-`l` vanishing assertion (spec FR-020/SC-008) in both.
- `tests/unit/test_ir_gate_convention.py` passes — `PauliTerm.to_gate()` for a
  `Z`-upload is `Operator`-equivalent to a hand-built rotation gate at the angle the
  encoding convention implies (spec FR-021/SC-009); this is required, not optional —
  see "Sign convention" below for why.
- `tests/ci/test_no_forbidden_imports.py` passes — no production module (anything
  outside `src/fourierlearn/reference.py`) imports `Statevector`, `Operator`, `expm`, or
  `fourierlearn.reference`.
- `tests/unit/test_dependency_versions.py` passes — the installed `qiskit`,
  `qiskit_aer`, and `numpy` versions match this layer's pin (research.md R2, R11).
  Full run-manifest scaffolding is a Spec 6 concern, not tested here.

## Manually exercising the two required oracle scenarios

These correspond to spec FR-016/FR-017/FR-018 and are worth running by hand once to
build intuition before relying on the automated tests.

### Scenario 1 — single-upload, real coefficients

1. Build a `PauliEncodedCircuitIR` (contracts/ir_types.py) with one qubit, one
   `PauliTerm("Z", qubits=(0,), parameter_index=0, coefficient=1.0, tie_group=0)`, and
   an observable of `SparsePauliOp("Z")`.
2. Call the reference oracle's `coefficients()` (contracts/ir_to_oracle.py) on it.
3. **Expected**: coefficients matching the analytically known single-qubit `Z`-
   rotation expectation-value spectrum — real-valued, symmetric in `l`.

### Scenario 2 — two-upload, genuinely complex coefficients

1. Build a `PauliEncodedCircuitIR` with one qubit and three gates in order: a
   `PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0)`, a
   `FixedGate(SGate(), (0,))` (a real Qiskit gate instance — research.md R3), and a
   second `PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=1)` —
   the `S` gate is the FR-018 symmetry-breaking gate between the two `Z`-rotation
   uploads of the same parameter.
2. Call the reference oracle's `coefficients()` on it.
3. **Expected**: at least one non-DC coefficient has both nonzero real and nonzero
   imaginary parts, matching the hand-derived analytic value to floating-point
   precision (spec SC-002, relative error ≤ 1e-9). A result where every coefficient is
   real (i.e. the `S` gate had no effect) indicates the symmetry-breaking construction
   is wrong, not that the test may be loosened (spec FR-018/§4.3).

## Rotation-angle period, and why the grid is *not* halved (research.md R7, R8)

Both scenarios' analytic values use `α ∈ [0,1]` (Barthe's own native units) with
rotation angle `π·α`, giving `f(α)` period **2**, not `2π` — confirmed in-session
against `docs/references/Barthe_thesis.pdf` (Definition 2.4, eq. 2.29-2.30) and
`docs/references/equivariant FCE Z2LGT report.pdf` (§3.1-3.2, eq. 7-13). The oracle's
grid samples the **full** period-2 domain per parameter, `4 r_j L_j + 1` points, per
R7/R12 — deliberately *not* the period-1 half-domain the parity result (every
admissible `l` is even) would, in principle, make sufficient. Sampling the half-domain
would be half the cost, but would make every odd-`l` coefficient structurally
unmeasurable — turning "every odd-`l` coefficient is zero" into a premise baked into
the grid, rather than a claim the grid can check. This is why FR-020/SC-008 make it a
**required** assertion, not a bonus: `tests/oracle/test_reference_oracle.py` must
assert every odd pre-parity coefficient is zero to floating-point precision in *both*
scenarios. A violation would indicate a period, indexing, or parity-derivation bug —
distinct from, and checked independently of, FR-018's complex-coefficient assertion.

## Sign convention: `PauliTerm.to_gate()` versus `PauliEvolutionGate` (research.md R6)

This layer's encoding convention is `e^{iπcαP}`; Qiskit's `PauliEvolutionGate(P,
time=t)` implements `e^{-itP}` — confirmed in-session by comparing `Operator(qc)` for
a one-qubit `PauliEvolutionGate(SparsePauliOp('Z'), time=0.37)` against
`scipy.linalg.expm(-1j*0.37*Z)` (matches) and `expm(+1j*0.37*Z)` (does not). The
correct mapping is therefore `time = -math.pi * c * α`, not `c * α`. **Do not trust
this by inspection alone**: a flipped sign silently conjugates every returned
coefficient (`l ↔ -l`), which looks identical to a correct result on Scenario 1 (real
coefficients are unchanged by conjugation) and only shows up as a swapped real/
imaginary relationship on Scenario 2 — exactly the kind of error that is easy to ship
unnoticed. `tests/unit/test_ir_gate_convention.py` closes this independent of the
oracle's coefficient tests: build `PauliTerm("Z", (0,), 0, 1.0, 0).to_gate(Parameter("a"))`,
bind `a` to a concrete value, and assert `Operator`-equivalence against a hand-built
`e^{iπ·1.0·a·Z}` matrix directly. This is the same sign-convention failure mode that
previously broke the "template_binding" work in the predecessor repository — treat
this test as standing infrastructure, not a one-off fix, since any later spec that
constructs a similar parameterised gate from an encoding convention re-introduces the
same risk unless it re-verifies the sign against the installed Qiskit version itself.

## Success Criteria → test mapping (T029, recorded post-implementation)

| Success Criterion | Test(s) |
|---|---|
| SC-001 | `tests/unit/test_contracts.py` (all 4 tests) + `mypy src/fourierlearn/` clean |
| SC-002 | `tests/oracle/test_reference_oracle.py::test_single_upload_reproduces_analytic_coefficients`, `::test_two_upload_reproduces_analytic_complex_coefficients` |
| SC-003 | Structural audit (T028): grep confirms no sign/parity/`fftfreq`/`fftshift`/two's-complement logic outside `frequency.py`; `reference.py`/`ir.py` call `frequency.dft_frequencies`/`coordinate_order` rather than reimplementing |
| SC-004 | `tests/ci/test_no_forbidden_imports.py` (all 4 tests, including the `tmp_path` guard-validation regression) |
| SC-005 | Full suite: `pytest tests/ -v` — 53 passed |
| SC-006 | `tests/unit/test_frequency.py::test_register_width_matches_hand_computed_table` (4 cases) + the two degenerate-input rejection tests. **Behavioral aliasing-regression clause is explicitly deferred to Spec 3** per the TODO in spec.md's Assumptions — not tested here by design, not an omission |
| SC-007 | `tests/unit/test_dependency_versions.py` (all 3 tests) |
| SC-008 | `test_single_upload_odd_l_vanish`, `test_two_upload_odd_l_vanish` |
| SC-009 | `tests/unit/test_ir_gate_convention.py::test_to_gate_z_upload_is_operator_equivalent_to_hand_built_rotation` |

All nine Success Criteria have a corresponding passing check as of this implementation.
