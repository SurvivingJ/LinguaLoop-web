---
title: "ADR-009: Two Budgets — Tests vs Practice — with Maintenance/Acquisition Split Within Practice"
status: accepted
date: 2026-05-21
---

# ADR-009: Two Budgets — Tests vs Practice — with Maintenance/Acquisition Split Within Practice

## Context

The Study Plan orchestrator ([[decisions/ADR-008-study-plan-orchestration-layer]]) needs a budget structure to allocate time against. Several decompositions were viable:

- **One budget** (just "study time"). Too coarse; loses the ELO/skill-targeted structure tests provide.
- **Per-surface budgets** (Reading time, Listening time, Pinyin time, Vocab Dojo time, Daily Mixed time, ...). Too granular; surfaces are an implementation detail and N + 1 budget creep when we add a surface.
- **Per-skill-category budgets** (Comprehension time, Production time, Vocabulary time). Plausible but cuts across surfaces in awkward ways — Vocab Dojo is comprehension *and* production; dictation tests comprehension *via* production.

We also need an internal split inside the vocabulary-acquisition budget so retention (FSRS-due flashcards, BKT-decayed mastered words) doesn't starve new learning, and vice versa.

## Decision

Two top-level budgets per `(user, language)`:

1. **Tests budget** — comprehension test types (reading, listening, dictation) plus language-specific sentinel-test trainers (pinyin, measure-word, pitch-accent). ELO-scored. Allocated as *counts per skill per week* by Tier B.
2. **Practice budget** — everything else in the vocabulary-acquisition path: ladder exercises, FSRS-due flashcards, mastered-word maintenance. Allocated as *minutes per week*. Internally split:
   - **Maintenance** sub-budget — minutes for FSRS-due / BKT-decay-flagged items (retention).
   - **Acquisition** sub-budget — minutes for ladder-active words (new learning).

Bounds:
- Maintenance share ∈ `[0.15, 0.50]` (never below 15%: retention risk; never above 50%: starves new learning).
- Acquisition share ∈ `[0.50, 0.85]`.
- Base split at template creation: `30 : 70` (beginner-skewed). Adapter pushes toward `50 : 50` as the mastered-word pool grows and retention pressure rises.

Flashcards explicitly do **not** get their own budget — they are a sub-type of Maintenance practice (FSRS-due items). Sentinel-test trainers (pinyin, measure-word, pitch-accent) are **Tests** (they update ELO via `process_pinyin_submission` / `process_measure_word_submission` / `process_pitch_accent_submission`), not Practice.

## Consequences

- **Easier:** Two budgets is the smallest decomposition that respects the real architectural split (ELO-scored vs unified-score-ranked) and gives Practice room to self-balance retention vs learning.
- **Easier:** Adding a new test type (e.g. a future grammar quiz) drops into the Tests budget with a template entry; no new top-level budget.
- **Easier:** Flashcards-as-Maintenance closes a long-standing UX confusion ("why are there two places that show me FSRS reviews?"). The merged Practice surface is the only entry point.
- **Harder:** The Maintenance/Acquisition split needs its own adapter logic (`rebalance_practice` in [[algorithms/study-plan-adaptation.tech]]) driven by `maintenance_pressure` and `acquisition_pressure` formulas. Adds spec surface but is contained to one function.
- **Constrained:** A learner who wants "more flashcards, fewer ladder words" has only one knob — the per-skill weight overrides — and it acts on the test side, not within Practice. V2 may expose explicit Maint/Acq overrides if telemetry shows demand.

## Alternatives Considered

1. **One unified time budget.** Adapter divides freely across all surfaces. Rejected: loses the ELO-targeted structure of tests; allocation becomes harder to interpret and explain.

2. **Three budgets (Tests / Acquisition / Maintenance) at the top level.** Rejected: Maintenance and Acquisition share the same surface (merged Practice), the same scoring formula (unified score), and the same time-tracking column (`exercise_attempts.time_taken_ms`). Splitting them at the budget level but unifying them at the surface level adds plumbing without conceptual gain. The current structure (Practice budget + internal Maint/Acq split) is the right level of decomposition.

3. **Per-skill Practice budgets** (Practice-for-reading, Practice-for-listening, ...). Rejected: senses don't map cleanly to skills, and the V1 weakness signal uses global-per-language `ladder_stagnation` and `fsrs_lapse_rate` precisely because the per-skill attribution is fragile. Per-skill Practice would force the fragile mapping.

4. **Flashcards as a third budget.** Rejected: flashcards are functionally identical to FSRS-due items inside the Maintenance pool. Two surfaces for the same data is exactly the problem ADR-007 solves.

## Related Pages

- [[features/study-plans.tech]] — Tier B + C with both budgets in scope.
- [[algorithms/study-plan-adaptation.tech]] — `rebalance_practice` formula.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — Practice surface unification.
- [[decisions/ADR-008-study-plan-orchestration-layer]] — Layer that allocates these budgets.
- [[features/flashcards]] — Status as a Maintenance sub-type clarified here.
