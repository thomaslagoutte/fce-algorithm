# Specification Quality Checklist: LCU and Projector-Observable Extension for FCE

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-21
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

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- As with Spec 8, this feature is inherently physics/mathematics-heavy
  (Pauli-sum observables, LCU registers, complex-conjugate circuits)
  because it directly implements a cited algorithm (Barthe thesis
  Appendix 5.7.3) — the "implementation details" excluded here are
  software/tooling choices, not the mathematical objects the feature
  exists to construct.
- Two corrections were made during drafting (not left as
  [NEEDS CLARIFICATION] markers, since both were resolved by direct,
  in-session verification against the cited source): (1) the LCU
  construction runs the frequency-counting forward/inverse pass exactly
  once, shared across all terms, not once per term; (2) the projector
  `|0><0|` construction (deliverable b) is a genuinely separate
  capability from the weighted-Pauli-sum construction (deliverable a),
  not a special case of it, since the projector's own Pauli decomposition
  has exponentially many terms. Both are documented in spec.md's
  Clarifications section.
- **Session 2026-08-21 (`/speckit-clarify`)**: a critical mathematical
  error in FR-003 ("the Square Root Trap") was caught, independently
  re-derived from first principles, and numerically confirmed (diff
  ~1e-16 for the corrected formula vs. ~0.2 for the original) before being
  applied — the LCU preparation amplitude must be `c_h = sqrt(beta_h/S)`
  with `S` the L1 norm, never `c_h = beta_h/S` as a literal reading of
  eq. 5.51 would suggest, or the recovered combination is quadratic in
  `beta_h` instead of linear. FR-003 corrected; a non-degenerate
  (asymmetric-weight) verification mandate added to Assumptions; FR-008
  corrected to require two independent frequency-counting registers for
  the `U⊗U*` construction (register-doubling cost), predicted and logged
  per Constitution §10.3. All 16 checklist items remained passing before
  and after — no regressions.
