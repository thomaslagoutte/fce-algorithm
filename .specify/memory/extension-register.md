# Extension Register — `fce`

**Constitution §2.3**: "Anything not in the source is marked `EXTENSION` with
what it adds and assumes, and is listed in one in-repo extension register
with its validation status." This file is that register. It is new as of
2026-08-21 — no prior extension register existed; this project's Constitution
§2.3 obligation had gone unfulfilled through Specs 1-5, whose own deferred
"weighted-sum/linear-combination-of-Paulis" TODO was recorded only inline,
redundantly, in each spec's own Assumptions section (`specs/003-circuits-layer/spec.md`,
carried forward by reference — not re-recorded — in Specs 4 and 5), rather
than in a shared, canonical location. This register is the canonical
location going forward; existing inline TODOs are not deleted (they remain
as historical record of when each spec deferred the item) but this file is
now the source of truth for status.

**Format**: one entry per `EXTENSION`, each stating what it adds beyond the
source, what it assumes, its exact source citation (per §2.5, verified
in-session against `docs/references/Barthe_thesis.pdf`, not assumed), its
current validation status, and which specs already reference it.

---

## EXT-001 — Linear Combination of Unitaries (weighted-Pauli-sum observables)

**Adds**: extends Barthe Corollary 5.1's Fourier-coefficient-extraction
algorithm — implemented in this codebase (Specs 3-5) for a single
Hermitian Pauli-string observable `P` only — to a general Hermitian
observable expressed as a weighted sum of polynomially many Pauli strings,
`O = Σ_h β_h P_h` (implemented: `circuits.compile_observable_circuit`'s
multi-term branch, `src/fourierlearn/circuits.py`). The extension reuses
the existing single-Pauli `A(U)`/`A(U†)` construction unchanged (run once,
shared across all terms — never once per term) and combines the terms via
a genuine Linear Combination of Unitaries (LCU) construction: an
additional selector register of `⌈log2(#terms)⌉` qubits, a diagonal sign
gate, a multiplexed controlled-`P_h` gate, and post-selection.

**Correction versus the thesis's own eq. 5.51 shorthand** (Spec 9
research.md R1, independently re-derived and numerically verified before
implementation): the selector register must be prepared into
`Σ_h √(|β_h|/S)|h⟩` with `S = Σ_h|β_h|` (the **L1** norm) — **not**
`Σ_h(β_h/‖β‖)|h⟩` (the L2 norm) as eq. 5.51 literally reads. The literal
reading gives a result quadratic in `β_h`, not the linear combination
`O` requires; it also cannot represent a negative `β_h` at all (an
invalid, imaginary `√` of a negative number). The sign of each `β_h` is
instead absorbed by a separate diagonal gate on the selector register.

**Assumes**: a polynomial number of terms `h` and polynomial `L1` norm
`S=Σ|β_h|` (the thesis's own stated precondition for this extension to
remain efficient) — an exponential-term or exponential-norm observable is
not covered by this extension and is not claimed to be.

**Source** (verified in-session against `docs/references/Barthe_thesis.pdf`,
249 pages, extracted via `pypdf`):
- Barthe thesis §5.7.3, subsection "Linear combination of Pauli observables"
  (page 144 of the PDF): "In this subsection, we extend the procedure above
  to a more generic observable, more specifically, a linear combination of
  polynomially many Pauli strings. This can be done using a Linear
  Combination of Unitaries approach." — with the explicit decomposition
  `O = Σ_h β_h P_h` (Eq. 5.49) and the register-size/post-selection
  requirement (Eq. 5.51 and surrounding text).
- Figure 5.5 (page 145), captioned "Illustration of the quantum function
  evaluation algorithm for arbitrary observables" — the circuit diagram for
  this exact construction.
- Forward-referenced from the main text at page 123 (§5.2.2): "Note that the
  theorem above is specific to observables that are Pauli strings `P`. In
  the Section 5.7.3, we prove that this result can efficiently be extended
  to a broader range of observables `O`, such as linear combinations of
  Pauli terms with a polynomial number of terms and polynomial spectral
  norm and local projectors."

**Validation status**: **validated**. Implemented and tested in
`specs/009-lcu-projector-extension/` (deliverable a) —
`src/fourierlearn/circuits.py`'s `compile_observable_circuit` multi-term
branch, `_insert_observable_lcu`, `_lcu_magnitude_amplitudes`,
`_lcu_sign_diagonal`, `_append_multiplexed_fold`. Verified end to end
against the exact reference oracle on a 3-term, mixed-sign fixture
(`β=+1,-2,+3`, `tests/oracle/test_circuits_lcu_three_term_mixed_sign.py`,
diff `<1e-9` across every frequency, including a genuinely complex
non-DC coefficient), on a 2-term negative-weight fixture with an
isolating sign-gate-removal control
(`tests/unit/test_circuits_lcu_negative_weight.py`), and confirmed a
single-term observable's compiled circuit is unchanged from Spec 3's own
pre-existing output (`tests/unit/test_circuits_lcu_single_term_unchanged.py`).

**Already referenced (not yet re-pointed at this register) by**:
`specs/003-circuits-layer/spec.md` (first recorded, ~line 448-453),
`specs/003-circuits-layer/plan.md` (~line 78-79),
`specs/003-circuits-layer/checklists/requirements.md` (~line 51-58),
`specs/004-extract-layer/spec.md` (~line 369-373, reference only),
`specs/005-learning-backend-layer/spec.md` (~line 526-530, 558-560,
reference only), `specs/009-lcu-projector-extension/spec.md` (deliverable a,
activating implementation).

---

## EXT-002 — Quantum Kernel method (heuristic, classical-input kernel)

**Adds**: a heuristic learning algorithm for the regime beyond Constitution
§11's log-many-parameters restriction, where provable PAC bounds for the
efficient quantum learner (Barthe §5.3.2 / this project's own extraction
pipeline) do not apply. Defines a kernel over **classical inputs** `x`,
`k(x, x') = b(x)·b(x')`, where `b(x)` is the Fourier-coefficient vector
extracted (via this project's own FCE subroutine, §5.2) at input `x`, and
builds a `T×T` Gram matrix with `O(T²)` quantum evaluations, on which
ordinary classical kernel methods (e.g. kernel ridge regression) then run.

**Assumes**: the resulting kernel's feature-map dimension is exponentially
large in general, so its generalization performance carries **no
guarantee** unless an exponential number of training samples is available
— quantum kernels are noted (citing thesis ref. [160]) to suffer from
exponential concentration in general. This extension's use is therefore
conditioned on the "rank collapse" regime already named and bounded by
Constitution §11.11: *"The thesis kernel is over classical inputs,
`k(x,x')=b(x)·b(x')`. ... The kernel route is reserved for the regime where
rank collapse makes the support polynomial; invoking it where the support
stays exponential is prohibited, as its guarantee does not hold there."*
This register entry does not introduce a new constraint — §11.11 already
governs this extension's applicability; this entry only records that the
method itself is not yet implemented.

**Source** (verified in-session against `docs/references/Barthe_thesis.pdf`):
- Barthe thesis §5.5.2, "Kernel approach" (page 131): "We propose a kernel
  method approach as a heuristic... We define the kernel as `k(x,x') =
  b(x)·b(x')`... we build the `T×T` Gram matrix with `O(T²)` evaluations on
  a quantum computer."
- §5.5.1, "Exponentially large spectrum" (page 130), the framing section
  establishing why this heuristic is needed once the parameter count grows
  beyond log-many (matching Constitution §11.11's "rank collapse"/"support
  polynomial vs. exponential" language).
- §5.7.7, "PAC efficient Kernel-based algorithm" and §5.7.8, "Noisy Kernel
  Ridge Regression" (per the thesis's own table of contents, page 8) — the
  detailed circuit/complexity treatment this heuristic's implementation
  would need to follow.
- Figure 5.8 (page 150), the kernel-overlap evaluation circuit.

**Validation status**: **implemented**. Originally deferred pending Z₂ LGT
validation; that validation is complete (Spec 8) and the LCU extension it
depends on for weighted-sum observables is also complete (Spec 9,
EXT-001). `specs/010-quantum-kernel-method/` is this extension's
implementation: `circuits.compile_kernel_overlap_circuit` (deliverable a),
`kernel.py` — `build_gram_matrix`, `krr_fit_predict`, `noisy_krr_predict`,
`NoisyKRRBound` (deliverable b) — and the cancellation/PAC-efficiency
demonstration fixture (deliverable c, `tests/oracle/test_kernel_
cancellation_pac_efficiency.py`). Its three core claims, verified
computationally in-session before that spec's own FRs were written
(Constitution §2.2/§4.1), are now permanent regression tests, not only
ad hoc session findings: (1) the thesis's own `Rz(α_s)YRz(α_s)` cancellation
identity (§5.5.2, p.121-122) holds exactly (diff `0`-`2.2e-16`) independent
of `α_s`, and a fixture with two independent cancelling parameters shows
the ambient frequency box growing multiplicatively (`45→405`) while the
extracted support stays fixed at `2` elements (`tests/oracle/test_kernel_
cancellation_pac_efficiency.py`); (2) the Figure 5.8 kernel-overlap
circuit, built with Spec 3's `compile_frequency_circuit` reused completely
unmodified, reproduces `Re(⟨b(x)|b(x')⟩)` to machine precision on both a
1-qubit/1-parameter fixture and a richer 2-qubit/2-tied-parameter fixture
(`tests/oracle/test_circuits_kernel_overlap_circuit.py`); (3) the noisy-KRR
error bound (eq. 5.94) held with zero violations across `500` random Monte
Carlo trials at both generic-magnitude noise (`tests/unit/test_kernel_
noisy_bound_formula.py`) and realistic, Spec-4-derived Hoeffding shot-noise
scales (`specs/010-quantum-kernel-method/research.md` R1).

**Labeling guardrail (FR-011/Acceptance Scenario 4, Constitution §11.8)**:
this implementation introduces NO fixture on the Z₂ LGT validation
platform (Specs 6-8) of its own — the cancellation demonstration (claim 1
above) is a purpose-built, platform-independent fixture (FR-013), not a Z₂
model. There is therefore nothing in this implementation that could be
mislabeled as a demonstrated Z₂ learning advantage; this is recorded
explicitly rather than left unstated.

**Structural honesty note (Constitution §8.3)**: `noisy_krr_predict`
NEVER returns a bare prediction number — every call returns
`(prediction, NoisyKRRBound)`, where `NoisyKRRBound.tightness_status`
(`"informative"`/`"loose"`/`"vacuous"`, computed fresh from each call's
own live signal magnitude, never a frozen constant) flags whenever eq.
5.94's bound is too loose to be a practically useful constraint at the
noise scale actually supplied — mirroring `learn.py`'s
`PacBound.weight_space_translation_status` pattern.

**Already referenced by**: Constitution §11.11 (governs this method's
applicability), `specs/010-quantum-kernel-method/spec.md` (implementation
record), `specs/010-quantum-kernel-method/research.md` (realistic-noise
verification and the `NoisyKRRBound` design).

---

## EXT-003 — Projector/probability observable via the `U⊗U*` construction

**Adds**: extends the Fourier-coefficient-extraction pipeline (currently
implemented, Specs 3-4, for a Hermitian Pauli-string or — pending EXT-001 —
weighted Pauli-sum observable only) to extract the Fourier coefficients of
`P(0) = |⟨0|U(α)|0⟩|²`, the probability that the *original*, unmodified
circuit `U` returns the all-zeros outcome. This is the observable
`|0⟩⟨0|` — not expressible as a polynomial-size Pauli-string sum (its own
decomposition, `(1/2^n) Σ_{P∈{I,Z}^n} P`, has `2^n` terms), so EXT-001's
LCU machinery is the wrong tool for it. The extension instead runs the
existing frequency-counting construction jointly on `U` and an
independently-constructed complex-conjugate circuit `U*`, via
`(U⊗U*)(|0⟩⊗|0⟩) = Σ_{k,l} ϕ_k ϕ*_l |k⟩⊗|l⟩`, and reads off the joint
amplitude.

**Assumes**: `U*` is built gate-by-gate, IN THE SAME ORDER as `U` (complex
conjugation of a matrix product does not reverse it, unlike the Hermitian
adjoint: `(AB)*=A*B*`, verified in-session on a 3-gate mixed sequence,
`tests/unit/test_circuits_conjugate_gate_order.py`). Per-gate rule for a
Pauli-rotation `e^{iπcαP}` (verified against `Operator(gate).conjugate()`
for both parities, `tests/unit/test_circuits_conjugate_gate_rule.py`):
an EVEN number of `Y` factors in `P` (`P` real, `P*=P`) negates the
angle; an ODD number (`P*=-P`) leaves the angle UNCHANGED — the opposite
of the naive "always negate" guess. **Explicit scope boundary**: a
`FixedGate` with a complex matrix (e.g. `S`) is out of scope — `conjugate_ir`
raises `ComplexFixedGateConjugationError` rather than mishandling it
silently; only real-matrix `FixedGate`s (e.g. `X`, `H`, as already used by
Spec 8's state-prep flips) are supported.

**Source** (verified in-session against `docs/references/Barthe_thesis.pdf`,
249 pages, extracted via `pypdf`):
- Barthe thesis p.135-136, "Probabilities, or projectors observables":
  "Consider a circuit `U` yielding a pure state `U|0⟩ = |ϕ⟩ = Σ_k ϕ_k|k⟩`.
  Its density matrix is `ρ = Σ_{k,l} ϕ_k ϕ*_l |k⟩⟨l|`. Defining the
  conjugate circuit as `U*`, we have `(U⊗U*)(|0⟩⊗|0⟩) = Σ_{k,l} ϕ_k ϕ*_l
  |k⟩⊗|l⟩`... This yields the procedure illustrated in Figure 5.6 to
  retrieve the coefficients for the observable `|0⟩⟨0|`" (eq. 5.52).
- Figure 5.6 (p.136), captioned "Illustration of the quantum function
  evaluation algorithm for a projector" — the circuit diagram running
  `A(U)` and `A(U*)` on parallel registers.

**Validation status**: **validated, for the scope actually built** —
implemented in `specs/009-lcu-projector-extension/` (deliverable b) as
`src/fourierlearn/circuits.py`'s `compile_projector_circuit`,
`conjugate_ir`, `predict_projector_register_cost`, and (added after an
architect-caught gap) `src/fourierlearn/reference.py`'s
`amplitude_coefficients`/`projector_coefficients` — the standard oracle
for this deliverable's own target quantity, `f(α)=|⟨0|U(α)|0⟩|²`.

**Correction (architect-caught, verified in-session before being
implemented)**: `compile_projector_circuit`'s output has TWO independent
frequency registers (one per copy, `A(U)` and `A(U*)`) — there is no
single register to read a combined frequency from. Combining the two
registers' decoded integers by SUMMING them (`Ω=ω_1+ω_2`) was tried and
found WRONG (numerically verified: max error `0.25` against an
independent grid+DFT of `f(α)` on a concrete fixture). The correct
combination is the per-axis DIFFERENCE, `Ω=ω_1-ω_2` (verified to match
that same ground truth to machine precision, `1.1e-16`) — matching the
underlying math directly: `⟨0|U(α)|0⟩=Σ_l a_l e^{ilα}`, so its complex
conjugate contributes `e^{-ilα}`, and the product's `e^{imα}` coefficient
sits at `m=l_1-l_2`, never `l_1+l_2`. `reference.projector_coefficients`
implements the verified (difference) rule.

Verified end to end (`tests/oracle/test_circuits_projector_end_to_end.py`):
`projector_coefficients` matches a fully independent classical grid+DFT
of `|⟨0|U(α)|0⟩|²` exactly, AND the actually-compiled
`compile_projector_circuit` output — decoding both of its frequency
registers and combining them via the difference rule — matches
`projector_coefficients` exactly, closing the gap between the oracle's
claim and what the compiled circuit's two disjoint registers actually
produce. The register-doubling cost formula
(`n_total=2·n_circuit+2·Σ_j⌈log2(4r_jL_j+1)⌉+2`) is verified against a
worked example (`tests/unit/test_circuits_projector_register_cost.py`).

**Scope boundary, not yet covered**: a circuit containing a complex-matrix
`FixedGate` (e.g. `S`, `T`) is explicitly out of scope (raises
`ComplexFixedGateConjugationError`) — extending `conjugate_ir` to handle
this case is left for a future spec, if ever needed.

**TODO, deferred (Constitution §4.7 — named, with its own blocking
condition, not a silent gap)**: the **finite-shot extraction wrapper** for
`compile_projector_circuit`'s output is not implemented. What exists today
is the compiler (`compile_projector_circuit`) and the exact oracle
(`reference.projector_coefficients`) — both validated end to end against
each other. What does NOT exist is a shot-based counterpart to Spec 4's
`extract.estimate_coefficient`/`extract_coefficients` for this
construction. Spec 4's existing Hadamard-test wrapper
(`extract._hadamard_test_circuit`) assumes a single-frequency-register
layout (`circuit.qregs[:-2]` = frequency registers, the last two = ancilla
and circuit) — it cannot be pointed at `compile_projector_circuit`'s own
six-register layout (`freq0, ancilla, circuit, freq0_star, ancilla_star,
circuit_star`) without a genuinely new wrapper. That wrapper must (a)
correlate BOTH frequency registers' measurement outcomes from the SAME
shot (never treat them as independently samplable, since the joint
amplitude — not a product of marginals — is the physically meaningful
quantity, per eq. 5.52), and (b) combine their decoded integers via the
verified DIFFERENCE rule (`Ω=ω_1-ω_2`, not `ω_1+ω_2` — see the correction
above) to construct the reported frequency. **Blocking condition**: this
wrapper is needed before this extension can be used for any finite-shot
(hardware- or noisy-simulator-facing) result — it is not needed for, and
does not block, the exact-oracle validation already completed above.

**Already referenced by**: `specs/009-lcu-projector-extension/spec.md`
(first record).

---

## Spec 8 (Equivariant Z2 LGT Ansatz) — determination: no new EXTENSION entry

Spec 8's `build_z2_lgt_model` targets the full matter+gauge Hamiltonian
with local, per-vertex/per-edge couplings (`d = |V| + 2|E|`). This was
checked in-session against `docs/references/equivariant FCE Z2LGT
report.pdf` (research.md R1, `specs/008-equivariant-z2-lgt-ansatz/`): the
report's own §5.1–5.3 (eq. 25–27), not only its earlier §2.3 (eq. 1–4,
global scalars `J, m, f`), already specifies this exact local-coupling
ansatz verbatim — `alpha^(m)_v, alpha^(g)_e, alpha^(h)_e` and
`d = |V| + 2|E|` (eq. 27) appear directly in the source. **This is
therefore a citation to a different part of the same source, not a
Constitution §2.3 `EXTENSION`** — no register entry is warranted for the
Hamiltonian itself. The remaining implementation choices specific to this
codebase (`Z2LGTGraph`/`build_z2_lgt_model`/`compute_lambda`'s concrete
function signatures, the `initial_occupation` state-prep-flip parameter)
are this project's own API design, not physics content, and likewise
require no register entry.

---

## Known gap: not yet backfilled into this register

Two further Spec-1-recorded deferred items exist only inline
(`specs/001-fce-foundation-layer/spec.md:434` and `:441`: an aliasing
regression test deferred to Spec 3, and run-manifest scaffolding deferred
to a later spec) and have not been given register entries here — this
register's first pass is scoped to the two extensions the user asked for
(EXT-001, EXT-002). Backfilling the rest remains open.
