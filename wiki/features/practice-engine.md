---
title: Practice Engine
type: feature
status: planned
tech_page: ./practice-engine.tech.md
last_updated: 2026-05-21
open_questions:
  - "Should grammar/style items (sense_id IS NULL) be reachable in V1 via a 'Browse drills' surface, or only via the language-pack flow?"
---

# Practice Engine

## Purpose

The Practice Engine is LinguaLoop's single surface for non-test vocabulary work. It replaces the split between Daily Mixed Session (`/api/exercises/session`) and Vocab Dojo (`/api/vocab-dojo/session`) — see [[decisions/ADR-007-merge-exercises-vocab-dojo]] — and exposes one route, one RPC, and one philosophy: every candidate item ranked by a unified score, served in one of two complementary modes.

## User Story

A learner taps "Practice." The system asks itself: *does this learner need to retain what they already know, or build new knowledge?* If the FSRS-due queue plus the BKT-decay-flagged mastered words outnumber the active ladder words, the answer is retention — and the session opens with the most urgent flashcard or decayed sense, ranked across many words. Otherwise the session anchors on one ladder-active word at a time, drilling the cognitive families that word's current ring needs, then moving to the next word, until the learner's time is up.

Either way, the learner sees one continuous flow. Gate batteries and stress tests appear inline when a ladder word reaches them. If a Maintenance session runs out of due items, it quietly continues with Acquisition — the budget is never wasted on an empty queue.

## How It Works

1. The learner has a per-day target_minutes for Practice (set by the [[features/study-plans|Study Plan]] orchestrator, or defaulted by the legacy /api/exercises path).
2. The system picks a mode:
   - **Acquisition** if the learner has more active ladder words than FSRS-due-plus-decayed items.
   - **Maintenance** otherwise.
   - The Study Plan can override this by passing explicit `practice_maintenance_min` and `practice_acquisition_min` for the day.
3. **Acquisition mode** picks one ladder-active word by priority, drills the families its current ring requires (one item per family, top-ranked by unified score), handles any pending gate or stress test, then re-ranks and picks the next word. Continues until accumulated expected time fills `target_minutes`.
4. **Maintenance mode** ranks every FSRS-due-within-7-days or BKT-decay-flagged sense, picks the top items directly by unified score, drains the queue. If the queue empties before time is up, the session falls through to Acquisition for the remainder.
5. Every item the learner submits updates BKT, FSRS, and ladder state via the existing per-attempt RPCs — no logic changes there.
6. The session also reports its time consumption to `record_session_progress` so the weekly plan's Maintenance/Acquisition counters stay live.

## The Unified Score

Every item is ranked by a single formula:

```
score = α · ladder_priority + β · irt_information + γ · bkt_uncertainty + δ · fsrs_urgency
```

The four terms each measure something different:

- **ladder_priority** — how urgently the ladder thinks this sense should be drilled right now (rings, families, gates, stress test, relapse).
- **irt_information** — how much this *specific item* tells us about a learner at this ability level (peaks when the item's difficulty matches the learner's theta).
- **bkt_uncertainty** — how unsure we are whether the learner knows this sense (peaks at p_known = 0.5).
- **fsrs_urgency** — how overdue the FSRS review is, relative to the card's stability.

The four weights `(α, β, γ, δ)` differ by mode:

| Mode | α (ladder) | β (IRT) | γ (BKT) | δ (FSRS) | Best for |
|---|---|---|---|---|---|
| Acquisition | 0.40 | 0.30 | 0.25 | 0.05 | Building new knowledge anchored on words. |
| Maintenance | 0.05 | 0.15 | 0.30 | 0.50 | Retaining known knowledge — FSRS dominates. |

See [[algorithms/practice-unified-score]] for the plain-English version and [[algorithms/practice-unified-score.tech]] for the exact normalization of each term.

## Modes in Detail

### Acquisition (word-and-deep)

For each ladder-active word, the engine drills as many items as the current ring requires (K = number of required families: Ring 1 = 1, Ring 2 = 3, Ring 3 = 1, Ring 4 = 2). It always picks the highest-unified-score item *within each required family*, so the family-targeted philosophy of ADR-005 momentum bands is preserved. If a word reaches Gate A or B, the 3-item gate battery runs inline; if a word in pre-mastery reaches the stress test, the 8-item battery runs inline; both still gate ring advancement and graduation. Then the word is popped from the eligible pool and the next word is picked by re-evaluating ladder priority.

If the learner has no eligible ladder words (e.g. brand-new account, or all words mastered), the engine auto-subscribes up to `target_new_rate` senses from the learner's selected packs (highest-frequency unsubscribed first). If they have no packs either, the session falls through to Maintenance. If even Maintenance has nothing, the engine returns an empty session with a `no_content` flag for the UI to surface a "select a pack" nudge.

### Maintenance (batch-and-broad)

Candidate pool: any sense with an FSRS card due within the next 7 days, OR any sense flagged as BKT-decayed (effective p_known has fallen more than 0.05 below the raw value). At most 200 candidates are pre-ranked by a cheap urgency proxy (`days_overdue / stability`), then the full unified score ranks those 200. The engine picks the top item, drills it, picks the next, and so on until time is up.

If the pool empties before `target_minutes` is reached, the engine falls through to Acquisition for the remaining time — see [[decisions/ADR-007-merge-exercises-vocab-dojo|ADR-007]].

## Constraints & Edge Cases

- **V1 excludes exercises with `sense_id IS NULL`** (grammar / style / non-sense-linked collocation items) from both candidate pools. See [[decisions/ADR-012-grammar-items-excluded-v1]]. V2 will recover them via a sense bridge table.
- **Cold ladder** (new user, 0 subscribed senses) — auto-subscribe from selected packs; if no packs, fall through to Maintenance; if still empty, return empty session with `no_content` reason.
- **Cold IRT** — exercises with `irt_n_attempts < 20` use the calibrated default `irt_discrimination = 1.0, irt_difficulty = 0.0`; the IRT term still computes, just with the default parameters.
- **Cold FSRS** — senses with no `user_flashcards` row contribute `fsrs_urgency = 0` (and aren't in the Maintenance pool anyway). Acquisition draws them from the ladder.
- **Time-budget overshoot** — the engine stops at the first item whose accumulated `expected_seconds` would exceed `target_minutes · 60`. It will not pad a partially-completed gate battery; the next session continues from the same word.
- **Item time variability** — the per-type `expected_seconds` (column on `dim_exercise_types`) is a P50 estimate; actual learner times will vary. The Study Plan handles drift on a weekly cadence.

## Business Rules

- Practice sessions are free (no token cost), consistent with current Vocab Dojo and Exercises behavior.
- Only first attempts update family confidence and BKT. Retries update FSRS scheduling but not confidence (unchanged from current).
- All gate / stress-test mechanics from [[decisions/ADR-005-momentum-bands]] are preserved verbatim: ring clears, cross-session advancement, ring demotion on ≥ 3 consecutive failures, FSRS graduation.
- A graduated word is owned by FSRS for scheduling. Mastered words appear in Maintenance via their FSRS due date; they appear in Acquisition only if they re-enter the `relearning` state.

## Backwards Compatibility

For one release after launch, the legacy RPCs and routes are kept as thin wrappers:

- `get_exercise_session(user, language, session_size, theta)` → `get_practice_session(user, language, 'auto', minutes ≈ session_size · 0.6, theta)`.
- `get_ladder_session(user, language, count)` → `get_practice_session(user, language, 'acquisition', minutes ≈ count · 0.5)`.
- `/api/exercises/session` and `/api/vocab-dojo/session` continue to function (with a deprecation log line).

The new canonical route is `/api/practice/session?mode=...&minutes=...`. UI consolidation happens incrementally; the legacy routes are scheduled for removal in the next release after launch.

## Related Pages

- [[features/practice-engine.tech]] — Full technical specification (RPC contract, candidate-pool SQL, session-loop pseudocode).
- [[algorithms/practice-unified-score]] — Plain-English description of the scoring.
- [[algorithms/practice-unified-score.tech]] — Exact normalization, weights, candidate pools.
- [[features/study-plans]] — The orchestrator that drives `target_minutes` and mode targets.
- [[algorithms/vocabulary-ladder]] — Ring/family/gate/stress-test progression (preserved verbatim).
- [[features/flashcards]] — FSRS mechanics; flashcards are now a sub-type of Maintenance items.
- [[features/vocabulary-knowledge]] — BKT formula and decay (unchanged).
- [[decisions/ADR-007-merge-exercises-vocab-dojo]] — Why the merger.
- [[decisions/ADR-012-grammar-items-excluded-v1]] — Why grammar items wait until V2.
- [[features/exercises]] — Deprecated (redirected here).
- [[features/vocab-dojo]] — Deprecated (redirected here).
