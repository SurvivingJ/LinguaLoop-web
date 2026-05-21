---
title: "ADR-007: Merge Exercises and Vocab Dojo into a Unified Practice Engine"
status: accepted
date: 2026-05-21
---

# ADR-007: Merge Exercises and Vocab Dojo into a Unified Practice Engine

## Context

LinguaLoop currently exposes two practice surfaces — `/api/exercises/session` (Daily Mixed Session) and `/api/vocab-dojo/session` (Vocab Dojo) — over the same underlying data. Both write to `exercise_attempts` and `user_vocabulary_knowledge`. They differ in scheduling philosophy:

- **Daily Mixed** is *batch-and-broad*: 20-item mixed session driven by IRT-weighted exercise selection across many words and types.
- **Vocab Dojo** is *word-and-deep*: per-word ladder priority, 6 cognitive families × 4 rings, gate batteries, stress tests.

The split is structurally incoherent. The current Daily Mixed builder ignores ladder family targeting; a ladder-active word in Ring 2 (needing form_production + collocation work) can be served a meaning_recall exercise in the mixed session, then that same word's family confidence is updated without crediting the family the ladder thought was being worked on. This is recorded as a Priority-1 integration gap in [[algorithms/ladder-implementation-analysis]].

The learner sees two CTAs ("Practice" vs "Vocab Dojo") that do similar-sounding things with no clear distinction. Onboarding has no way to direct a new user toward one over the other.

The Study Plan orchestration layer ([[decisions/ADR-008-study-plan-orchestration-layer]]) needs *one* Practice budget to allocate against, not two competing surfaces.

## Decision

Collapse both surfaces into a single Practice Engine service exposing one canonical RPC:

```sql
get_practice_session(p_user_id, p_language_id, p_mode text, p_target_minutes smallint, p_user_theta numeric)
RETURNS jsonb
```

Where `p_mode ∈ {'acquisition', 'maintenance', 'auto'}`:

- **Acquisition mode** is word-anchored — picks one word by ladder priority, drills the current ring's required families (K items, one per family, ranked by unified score), runs any pending gate/stress batteries, pops the word, re-ranks, anchors the next word. Full ladder mechanics (rings, families, gates A/B, stress test, cross-session advancement gating, ring demotion) preserved verbatim from ADR-005.
- **Maintenance mode** is batch-anchored across many words — ranks candidates (FSRS due ≤ +7d OR BKT-decay-flagged) directly by unified score. If the pool empties before `target_minutes` is reached, the session falls through to Acquisition for the remaining time.
- **Auto mode** dispatches by `(FSRS-due-today + decayed) ≥ active-ladder-words → maintenance else acquisition`.

A single **unified score** ranks every candidate item in either mode:

```
score(item, user) = α · ladder_priority + β · irt_information + γ · bkt_uncertainty + δ · fsrs_urgency
```

with mode-dependent weights stored in `dim_practice_modes.default_weights jsonb` (Acquisition `α=0.40, β=0.30, γ=0.25, δ=0.05`; Maintenance `α=0.05, β=0.15, γ=0.30, δ=0.50`). See [[algorithms/practice-unified-score.tech]] for normalization and the candidate-pool SQL per mode.

Old RPCs `get_exercise_session` and `get_ladder_session` are kept for one release as thin wrappers delegating to `get_practice_session`. Old routes `/api/exercises/session` and `/api/vocab-dojo/session` likewise wrap. A new canonical route `/api/practice/session?mode=...&minutes=...` is introduced for the consolidated UI.

V1 candidate pools require `exercises.sense_id IS NOT NULL`; grammar/style items without a sense link are excluded — see [[decisions/ADR-012-grammar-items-excluded-v1]].

## Consequences

- **Easier:** One Practice budget for the orchestrator to allocate. One mental model for the learner ("Practice"). The Priority-1 ladder/exercise integration gap is closed by construction — Acquisition mode is word-anchored, so family targeting and family-confidence updates always agree.
- **Easier:** Adding a new signal (e.g. spaced-out exposure, novelty boost) is a single coefficient change in the unified score, applied to both modes.
- **Easier:** The mid-session fall-through (Maintenance dry → Acquisition) honors the user's time budget without forcing them to manually switch surfaces.
- **Harder:** The merged RPC is more complex than either predecessor — four normalized terms, mode dispatch, candidate-pool composition, fall-through logic. Mitigated by [[algorithms/practice-unified-score.tech]] specifying every formula and constant.
- **Harder:** Parity testing is required to verify the merged service approximates the legacy services. Defined as top-K Jaccard ≥ 0.70 median with no user < 0.50 across 50 seeded staging users covering new/mid-ladder/mastered/lapsed cohorts.
- **Constrained:** Acquisition K (items per word per session leg) is fixed to the current ring's required-family count (1, 2, 3, or 6 depending on ring). A simpler fixed K (e.g. 3) was considered and rejected because it would either over-drill R1 words or under-drill R2 words.

## Alternatives Considered

1. **Extend each surface independently.** Add IRT to Vocab Dojo, add ladder targeting to Daily Mixed, leave the two surfaces split. Rejected: the dual code paths would diverge again; learners still see two CTAs; the orchestrator still has two budgets to manage.

2. **Merge into one surface but keep two pool definitions** (no unified score). Rank Acquisition purely by ladder priority, Maintenance purely by FSRS urgency. Rejected: loses the cross-signal benefit (e.g. a high-IRT-info Maintenance item ranks above a less-informative one) and re-introduces the integration gap whenever an item is eligible for both pools.

3. **Replace ladder mechanics entirely with FSRS-only retention.** Rejected: ADR-005 momentum bands (6 families × 4 rings × gates × stress test) are pedagogically central and locally tuned. Discarding them would lose the productive-skill targeting that distinguishes LinguaLoop from a flashcard app.

4. **Different K per mode rather than per ring** (e.g. Maintenance K=1, Acquisition K=5). Rejected: K-per-ring naturally encodes Ring 1's single required family vs Ring 2's three; a fixed K wastes drill time on lower rings and shortchanges higher rings.

## Related Pages

- [[features/practice-engine]] — Plain-English description of the merged surface.
- [[features/practice-engine.tech]] — Full technical specification.
- [[algorithms/practice-unified-score]] — Scoring philosophy.
- [[algorithms/practice-unified-score.tech]] — Normalization, weights, candidate pools.
- [[decisions/ADR-005-momentum-bands]] — Ladder mechanics preserved by the merger.
- [[decisions/ADR-008-study-plan-orchestration-layer]] — Why one Practice budget matters.
- [[decisions/ADR-012-grammar-items-excluded-v1]] — V1 candidate-pool limitation.
- [[algorithms/ladder-implementation-analysis]] — Priority-1 integration gap resolved here.
