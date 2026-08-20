# Specification Quality Checklist: FCE Foundation Layer

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- This foundation layer is inherently infrastructure for other developers rather than an
  end-user-facing feature, per Constitution §9 (Architecture). "Stakeholders" and "users"
  in this checklist's sense are the developers who build the downstream pipeline layers
  against these contracts — the spec frames its User Scenarios accordingly rather than
  around an external end user, since none exists for this layer.
- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- 2026-08-19 revision: corrected six derivation defects — decoupled the FFT dimension
  `d` from parity indexing, split the register-width formula (tested here) from its
  aliasing regression test (deferred to Spec 3, per §4.7), pinned the frequency
  convention's canonical representation and sign, narrowed the contracts module to the
  boundaries this spec actually crosses (`Encoding -> IR`, `IR -> Oracle`) plus a
  documented extension point, added the required symmetry-breaking gate to the
  complex-coefficient validation case, and added version-pinning/manifest requirements
  (§9.7, §8.5). All checklist items re-verified against the revised spec and still pass.
- 2026-08-19 revision 2 (plan-phase correction): scoped FR-019/SC-007 down to
  dependency-version verification only; full run-manifest scaffolding is deferred to
  Spec 6 (Experiment) per a new TODO in Assumptions, since this layer produces no
  experimental output to attach a manifest to. Checklist items re-verified and still
  pass.
- 2026-08-20 revision 3 (plan-phase review): added FR-020/SC-008 (oracle MUST sample
  the full pre-parity domain, not the half-domain the parity result would seem to
  justify, so that result stays an independently falsifiable check per §4.3) and
  FR-021/SC-009 (the IR's Qiskit-gate sign mapping, `t = -π c α` for
  `PauliEvolutionGate`, verified in-session per §9.7, MUST be covered by a direct
  gate-equivalence test — a sign error here is invisible on any real-coefficient
  test). Both trace to a review of plan.md's design, not the spec's own gaps, but are
  recorded here since they add falsifiable requirements a complete spec needs.
  Checklist items re-verified and still pass.
- 2026-08-20 revision 4 (post-implementation audit, ahead of Spec 2): a rigorous
  architectural audit — prompted by a question about whether tied Pauli terms may
  have heterogeneous coefficients — found two related, previously-unvalidated
  defects, both already implemented and tested: (1) `PauliEncodedCircuitIR` did not
  require `coefficient` uniformity across a parameter's terms (FR-007 amended,
  SC-010 added); (2) the oracle sampled a fixed length-2 domain regardless of
  `coefficient`, silently aliasing any non-unit value — confirmed against an
  independent, finer-grid ground truth (FR-022 added, SC-011 added). Every prior
  test case used `coefficient=1.0`, so both gaps were latent, not merely
  undocumented. Both are now enforced/fixed in code, with regression tests for the
  rejection and the fix. Checklist items re-verified and still pass.
- 2026-08-20 revision 5 (test-design hardening, prompted during Spec 2's second
  clarification session): the three non-unit-coefficient regression values added in
  revision 4 (`0.5, 3.0, -0.5`) included an integer (`3.0`) and two simple fractions
  of the period-2 domain — checked computationally and confirmed they do catch the
  specific pre-fix bug, but replaced with `0.37, 4.13, -1.79` anyway as the more
  robust test design: incommensurate values rule out masking via *any* coincidental
  rational relationship to the domain, not just the one bug already found. SC-011's
  wording updated to state this explicitly. Checklist items re-verified and still
  pass.
