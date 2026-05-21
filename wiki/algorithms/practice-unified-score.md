---
title: Practice Unified Score
type: algorithm
status: planned
tech_page: ./practice-unified-score.tech.md
last_updated: 2026-05-21
open_questions: []
---

# Practice Unified Score

## Purpose

The unified score ranks every candidate Practice item against every other, using a single formula that combines four orthogonal learning signals. It is the heart of the merged [[features/practice-engine|Practice Engine]] — see [[decisions/ADR-007-merge-exercises-vocab-dojo]].

## The Four Signals

Each signal tells us a different thing about a candidate item:

- **Ladder priority** — How urgently does the vocabulary ladder think this *word* should be drilled? Captures rings, families, gates, stress test, relapse — the pedagogical scaffolding from ADR-005.
- **IRT information** — How much would this *exact item* tell us about a learner at this ability level? Peaks for items whose difficulty matches the learner's theta.
- **BKT uncertainty** — How confident are we that the learner knows this *sense*? Peaks at p_known ≈ 0.5, where one more attempt resolves the most ambiguity.
- **FSRS urgency** — How overdue is this *flashcard*, relative to its stability? Peaks as items pass their due date.

Each is normalized to a `[0, 1]` range so they can be weighted and summed without one dominating by scale.

## The Formula

```
score = α · ladder_priority + β · irt_information + γ · bkt_uncertainty + δ · fsrs_urgency
```

The four weights `(α, β, γ, δ)` change by mode:

| Mode | α | β | γ | δ | Why these weights |
|---|---|---|---|---|---|
| Acquisition | 0.40 | 0.30 | 0.25 | 0.05 | Word-anchored learning. Ladder dominates (this *is* the ladder's session), IRT picks the best instance per family, BKT focuses on words that will move with one more attempt, FSRS is mostly irrelevant inside a brand-new word's drill. |
| Maintenance | 0.05 | 0.15 | 0.30 | 0.50 | Retention-focused. FSRS dominates (this *is* a flashcard-like session), BKT catches subtle decay, IRT picks instances that resolve ambiguity, ladder mostly irrelevant. |

The 0.05 floor for the "wrong-side" weight isn't zero by accident: even in Maintenance, a Maintenance item that happens to belong to a word currently in `relearning` ladder state *should* bubble up. Symmetrically, an Acquisition item that happens to be FSRS-due *should* preempt a non-due one.

## Why a Unified Score and Not Two Separate Algorithms?

Before the merger, Exercises used IRT to weight items and Vocab Dojo used ladder priority. The two surfaces would routinely pick the same word for different reasons, with no shared ranking. The unified score collapses that: any item ranked across any signal can be compared to any other. New signals (a novelty boost, a recency-of-exposure penalty) drop in as a fifth coefficient without architectural change.

It also closes the Priority-1 integration gap recorded in [[algorithms/ladder-implementation-analysis]] — a word the ladder thinks needs `collocation` practice can no longer receive a `meaning_recall` exercise from a mixed session, because in Acquisition mode the candidate pool is pre-filtered to the word's required families.

## What the Score Does Not Try to Capture

- **User preference** — handled at the orchestrator level via `skill_weight_overrides`, not at item ranking.
- **Content novelty / variety** — A separate anti-repetition filter excludes items seen today (existing behavior, preserved).
- **Token cost / tier access** — Practice items are free; tier filtering applies only to the Tests budget.
- **Streak preservation / motivation** — out of scope; motivational features layer above selection.

## See Also

- [[algorithms/practice-unified-score.tech]] — Exact normalization for each term, mode-dependent candidate pools, SQL helpers.
- [[features/practice-engine]] — Where the score is used.
- [[features/practice-engine.tech]] — Full RPC + candidate-pool spec.
- [[algorithms/vocabulary-ladder]] — Source of the ladder priority term.
- [[algorithms/vocabulary-knowledge]] — Source of the BKT term.
- [[features/flashcards]] — Source of the FSRS term.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — Why this score exists.
