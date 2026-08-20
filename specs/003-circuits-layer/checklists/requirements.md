# Specification Quality Checklist: Circuits Layer

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

- As with Spec 1 (Foundation Layer) and Spec 2 (Encodings Layer), this feature's
  "stakeholders" are the developers building the next pipeline layer (`extract`) on
  top of it, not an external end user — User Scenarios are framed accordingly per
  Constitution §9.
- A small number of FRs and SCs name a verification *method* (operator equivalence,
  matrix-exponential comparison, a numeric tolerance) rather than a specific tool or
  library. This is consistent with Spec 1's FR-021/SC-009 and Spec 2's FR-007/FR-013,
  which do the same — the project's own Constitution (§2.1, §9.7) requires every
  algorithmic decision to be verified in-session and every plan to state how, so this
  is a project-wide documentation requirement, not an implementation-detail leak.
  Nothing here names a specific library, language construct, or API signature.
- No [NEEDS CLARIFICATION] markers were needed: the one genuinely scope-determining
  ambiguity found while drafting — whether the observable-folded compiler (User
  Story 2) should support a single Pauli-string observable (Barthe thesis Figure 5.4,
  literally what the request describes) or a weighted sum of several (Figure 5.5's
  separate Linear-Combination-of-Unitaries extension) — was resolved with a
  documented default (single Pauli string in scope; the sum-of-Paulis extension
  deferred with a named `TODO`, Constitution §4.7) rather than a blocking question,
  since Barthe's own paper treats the sum case as a distinct, later extension and
  this project has repeatedly deferred similarly-scoped follow-on work the same way
  (see Spec 1's checklist, revisions 2 and 4).
- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- 2026-08-20 `/speckit-clarify` session: resolved three architect-flagged ambiguities.
  (1) Parity-ancilla concurrency — confirmed, by direct citation (Barthe thesis
  §5.7.3), to be one single ancilla shared across the whole circuit, never one per
  parameter; FR-003, Key Entities, and a new Edge Case updated accordingly. (2) The
  `A(U,P)` reversed-pass construction — computationally verified in-session (not
  assumed) that a literal full-circuit inverse of the assembled forward circuit and
  a separately constructed reverse-order pass with role-swapped shift primitives are
  provably the same operation (exact match, both algebraically and end-to-end
  against an independent brute-force ground truth on a genuinely non-DC toy case);
  FR-006 now mandates the single, simpler implementation (literal circuit inverse)
  rather than a second, independently maintained construction. This same toy
  verification also caught and fixed two unrelated modeling bugs (a reversed
  CNOT control/target direction; a frequency register sized one bit too small,
  aliasing `l=+4` and `l=-4`) — carried forward as explicit findings for
  `/speckit-plan`'s research.md, not discarded. (3) Basis-change duplication —
  added FR-014 mandating one single shared basis-change helper for both the
  encoding-gate case (User Story 1) and the observable case (User Story 3);
  FR-005/FR-008 and the Basis-change sandwich Key Entity updated to reference it.
- 2026-08-20 follow-up (same day): the reversed-pass verification above was
  challenged as insufficient — a d=1, single-tie toy case does not stress the
  shared ancilla under real multi-parameter contention. Re-verified on a 2-parameter
  circuit (Parameter A tied with multiplicity 2, its two tied terms deliberately
  non-adjacent in the gate list; Parameter B untied; gates interleaved
  A-term1/B/A-term2; both frequency registers independently and correctly sized),
  with every primitive built programmatically from its own definition rather than
  hand-typed, to avoid repeating the earlier manual-indexing bug class. Result:
  `R1`/`R2` matched to `max|R1-R2| = 0.0`, and the full `A(U,P)` construction
  matched an independent 2-D brute-force ground truth exactly across the whole
  sampled grid. FR-006's mandate holds under contention, not only in the simple
  case. Checklist items re-verified and still pass.
  Checklist items re-verified against the revised spec and still pass.
