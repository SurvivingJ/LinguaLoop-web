---
title: "ADR-017: Dual Translation as a Standalone Surface, L1→L2-only MVP"
status: accepted
date: 2026-06-22
---

# ADR-017: Dual Translation as a Standalone Surface, L1→L2-only MVP

## Context
Dual Translation overlaps existing surfaces (Dictation's diff grader, Flashcards' FSRS, the
Practice Engine, Study Plans' two-budget model). We must decide where it lives and how much of the
bidirectional loop to build first. The research report recommends an L1→L2-only MVP (the full loop
doubles grading surface and cost).

## Decision
Build Dual Translation as a **fully standalone feature surface** — its own `dt_*` tables, routes,
and pages — that **reuses existing services** (the dictation diff grader for Tier 0, FSRS-4 code
for remediation scheduling, the OpenRouter client/pricing pattern) without coupling to their
schemas. The MVP grades **L1→L2 back-translation only**. Integration with Study Plans budgets and
the bidirectional (L2→L1) step are explicitly deferred.

## Consequences
- **Easier:** maximum design freedom; no risk of destabilising Practice Engine / Study Plans
  during build; clean `dt_*` schema.
- **Easier:** still reuses the expensive-to-build parts (diff, FSRS, model router) as code.
- **Partial integration is in scope from day one (revised 2026-06-23):** error exercises
  (cloze / isolate-and-re-translate) are **interleaved into the Practice Engine exercise sessions**
  as well as the dual-translation queue. They ride a **separate, non-sense-linked** stream, so this
  is a lightweight injection point, not full Study-Plan orchestration.
- **Harder/later:** a second integration pass is still needed to slot Dual Translation *passages*
  into Study Plans orchestration and the Tests-vs-Practice budgets.
- **Constrained:** the L2→L1 comprehension step and its extra grading path are out of MVP scope.

## Alternatives Considered
1. **New test_type (like dictation id=3).** Maximises reuse of test_attempts/ELO, slots into the
   Tests budget — but forces the feature into the comprehension-test data shape, which fits poorly
   (rubric scores, error instances, spans). Rejected for MVP; revisit at integration.
2. **Practice Engine sub-mode.** Ties to the Practice budget and unified-score, but grading is far
   heavier than current practice items and would distort the unified-score model. Rejected.
3. **Full bidirectional loop now.** ~2× grading cost and surface for marginal MVP learning gain.
   Deferred.
