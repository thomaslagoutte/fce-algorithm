# Specification Quality Checklist: Encodings Layer

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-20
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

- As with Spec 1 (Foundation Layer), this feature's "stakeholders" are the
  developers building on top of it (the `circuits`/`extract` layers and beyond),
  not an external end user — User Scenarios are framed accordingly per Constitution
  §9.
- The user's explicit "critical requirement" (genuinely complex coefficients per
  frontend, guarding against a hidden `coeff_per_param` scaling error) is encoded as
  its own user story (US3) plus FR-011/FR-012/FR-013 and SC-003/SC-004, rather than
  left as a note — it is load-bearing, not advisory, mirroring how Spec 1's own
  FR-018/FR-020 were structured.
- No [NEEDS CLARIFICATION] markers were needed at initial drafting: the request
  specified enough detail to resolve every open point with a documented default
  (see Assumptions) rather than a question.
- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- 2026-08-20 `/speckit-clarify` session: a pre-planning audit of Spec 1's `ir.py`,
  requested before this spec proceeded, found two latent Foundation Layer defects
  (tie-group/parameter coefficient uniformity was unvalidated; the oracle's grid
  domain didn't rescale for non-unit coefficients) — both fixed in Spec 1 with
  regression tests (see Spec 1's checklist, revision 4). That fix revealed FR-006 as
  originally drafted ("tie every Hamiltonian term to one parameter") is
  structurally incompatible with any Hamiltonian whose terms have different
  coupling constants — i.e., the realistic case. FR-006/FR-007 were rewritten
  (renumbered FR-007) to require one encoded parameter per distinct coupling
  constant, with the exact `c_k = -h_k/(πL)` formula now pinned; US2, Edge Cases,
  Key Entities, Success Criteria, and Assumptions were updated to match, and FR
  numbers 5-11 shifted to 6-12 accordingly. Checklist items re-verified against the
  revised spec and still pass.
- 2026-08-20 second `/speckit-clarify` session (paradigm shift): a deeper
  architectural review determined evolution time was the wrong quantity to encode
  at all — the encoded parameters are the Hamiltonian's own coupling constants;
  evolution time `τ` and Trotter step count `r` are both fixed classical
  constructor arguments. The formula was re-derived and re-verified in-session
  (not assumed from the user's stated version, which omitted a sign that turned
  out to be load-bearing — confirmed against the actual target unitary): pinned as
  `c = -h·τ/(π·r)`. This reframing is a strict simplification versus the prior
  revision: because grouping is by shared coupling with equal per-term weight, the
  Foundation Layer's tie-group uniformity invariant is satisfied by construction
  (backstopped by a new FR-008 validation), and the "reconstruct a 1-D time series
  from a multi-dimensional output" concern from the previous revision is eliminated
  entirely — each encoded parameter now directly is a physical coupling. Also
  found and fixed, independent of this reframing: the Spec 1 audit's three
  non-unit-coefficient regression tests used `0.5, 3.0, -0.5` — one of them an
  integer, the others simple fractions of the period-2 domain — replaced with
  `0.37, 4.13, -1.79` to rule out masking via a rational relationship to the
  domain (see Spec 1's checklist). User Story 2, Edge Cases, FR-006 through
  FR-013, Key Entities, Success Criteria, and Assumptions were rewritten
  accordingly. Checklist items re-verified against the revised spec and still
  pass.
