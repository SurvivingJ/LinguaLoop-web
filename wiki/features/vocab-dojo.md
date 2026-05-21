---
title: Vocab Dojo
type: feature
status: deprecated
tech_page: ./vocab-dojo.tech.md
last_updated: 2026-05-21
open_questions: []
---

# Vocab Dojo

> **DEPRECATED — see [[features/practice-engine]].** As of 2026-05-21, Vocab Dojo is folded into the merged Practice Engine alongside [[features/exercises|Exercises]]. The `/api/vocab-dojo/session` route remains as a thin wrapper around `get_practice_session('acquisition', ...)` for one release; the canonical surface is `/api/practice/session?mode=acquisition&minutes=...`. Gate and stress-test endpoints (`/api/vocab-dojo/gate`, `.../gate/result`, `.../stress-test`, `.../stress-test/result`) are unchanged — they still call `ladder_pass_gate` / stress logic directly. Decision rationale in [[decisions/ADR-007-merge-exercises-vocab-dojo]].
>
> The open-question about whether the daily mixed session should surface ladder content is resolved by the merger: there is no longer a separate daily mixed session.
>
> Content below describes the legacy single-surface design and is preserved for historical context until the deprecation wrapper is removed.

## Purpose

Vocab Dojo is an adaptive exercise serving system that eliminates decision fatigue from vocabulary practice. It automatically selects which words to practice and which exercise type to serve, based on the learner's per-family confidence on each word and where the word sits in the ladder's four-ring progression. The goal is to build both passive recognition and active production of vocabulary.

## User Story

A learner navigates to `/vocab-dojo` and hits "Play." The system pulls a session of up to 20 exercises, each chosen because the underlying word needs that *specific cognitive skill* worked on right now. A word in Ring 2 that's strong on meaning but weak on collocation gets a Collocation Gap exercise. A word that has cleared every threshold and is at `pre_mastery` triggers the 8-exercise stress test. A word in the lapse path (recently mastered, recently missed) gets pulled to the front and worked back up.

The learner never chooses — the system handles family selection, exercise selection, gate batteries, and stress-test orchestration. If they get an exercise wrong, they see why and must keep trying until correct. But only the first attempt updates their family confidence.

## How It Works

1. The system calls the `get_ladder_session` SQL function with the user's id, the language id, and a target count.
2. It scores every candidate word in `user_word_ladder` whose `review_due_at` has arrived. Each word gets a priority from five subscores: how overdue it is, how far the weakest family is below its ring threshold, whether it's stalled at a gate, whether the previous-exercise family is repeating (novelty), and whether the word is in a relapse state.
3. The top words by priority go through. For each one, it picks one exercise — preferring the family the word's current ring most needs, preferring the variant the learner hasn't seen today, breaking ties at random.
4. Exercises seen earlier today are filtered out.
5. The frontend marks any word in `gated` state as needing a gate battery, and any word in `pre_mastery` as needing the stress test. The learner sees one button-press flow into either branch.
6. After each attempt, family confidence is updated, the ring is re-evaluated for clearing, and the next `review_due_at` is set from the momentum band (low/medium/high p_known).

## Priority Scoring

Every candidate word gets one number:

```
priority = 0.35 · overdue
         + 0.25 · weakness
         + 0.20 · gate_urgency
         + 0.10 · novelty
         + 0.10 · relapse
```

- **Overdue**: days past `review_due_at`, capped at 7 then normalised to [0, 1].
- **Weakness**: the gap between the ring's required confidence threshold and the weakest active family. A word that needs 0.65 in `semantic_discrimination` but only has 0.40 scores 0.25 here.
- **Gate urgency**: 1 if the word is `gated`, 0 otherwise.
- **Novelty**: 0.5 if the word has never been exercised before (last_exercised_family is null), 0 otherwise.
- **Relapse**: 1 if the word is `relearning` (a mastered word that recently failed), 0 otherwise.

A word's overall priority can exceed 1.0, so this is a ranking score, not a probability.

## Family Targeting

Within a word, the chosen exercise prefers the *weakest* required family in the current ring. A word in R2 (which requires meaning_recall, form_production, collocation) with confidences `{meaning: 0.72, production: 0.48, collocation: 0.55}` will pull a Level-4 morphology exercise first because form_production is the lagging family.

## Gates and Stress Test

The dojo handles three exercise modes:

- **Standard exercise** — one-by-one, individually scheduled by momentum band.
- **Gate battery** — 3 exercises drawn from the ring about to be unlocked. The learner needs at least 2/3 correct. Triggered automatically when a word in `gated` state surfaces in the session.
- **Stress test battery** — 8 exercises spread across all six cognitive families. The learner needs 6/8. Triggered when a word in `pre_mastery` surfaces. Pass → graduate to `mastered` and hand off to FSRS-4.5 maintenance scheduling.

If a gate or stress test is failed, the family confidences degrade and the learner is invited to try again next time the ring re-clears.

## Anti-Repetition

- Exercises served earlier today (via `user_exercise_history`) are filtered out of the session pick.
- A/B variants alternate — for exercise types with two variants, the picker prefers the one the learner hasn't seen most recently.
- Words skipped for active_levels (e.g. concrete nouns at level 5/8) are skipped at the ring-family check, not at the exercise pick — they don't get stuck waiting on a family they can't exercise.

## Constraints & Edge Cases

- A word becomes a stress-test candidate only when *every active family* has confidence ≥ 0.72, not just the families required for R4. This guards against a learner blitzing one ring while another family quietly lags.
- The 6th family `contextual_use` has no exercise type yet — it's reserved for a future Level 10 Capstone. Its 0.10 default confidence caps a word's overall p_known at ≈ 0.92 until the capstone ships.
- Post-mastery scheduling is FSRS-driven (see [[features/flashcards]]). Mastered words have `review_due_at = NULL`; their next maintenance review lives in `user_flashcards.due_date`.
- If a mastered word fails an exercise — the lapse path — it drops to `relearning`, takes a 30% extra family-confidence penalty, and FSRS gets a "AGAIN" rating.

## Business Rules

- Sessions are free (no token cost for Vocab Dojo exercises).
- Only first attempts update family confidence and BKT. Retries update FSRS scheduling but not confidence.
- A graduated word is owned by FSRS for scheduling — the ladder service stops touching `review_due_at` on mastered rows.
- Exercise history is logged to `user_exercise_history` via a database trigger; analytics and the anti-repetition CTE both read from there.

## Daily Mixed Session vs Dojo

Two distinct surfaces:

- **Vocab Dojo** (`/api/vocab-dojo/session`) — *Only ladder content.* Uses `get_ladder_session` directly. Per-word, ring-aware, family-targeted.
- **Daily Mixed Session** (`/api/exercises/session`) — Mixed across FSRS due reviews, BKT uncertainty-zone words, new words, and supplementary grammar/collocation. A separate Python builder. *Currently does not serve ladder content* due to a broken integration with the ladder service — see [[algorithms/ladder-implementation-analysis]] Priority 1.

## Related Pages

- [[features/vocab-dojo.tech]] — Technical specification with RPC details
- [[algorithms/vocabulary-ladder]] — Ring/family/gate/stress-test progression
- [[algorithms/vocabulary-ladder.tech]] — Full ladder spec
- [[algorithms/ladder-implementation-analysis]] — Audit and improvement priorities
- [[features/exercises]] — Exercise type inventory
- [[features/vocabulary-knowledge]] — BKT (overall p_known)
- [[features/flashcards]] — FSRS handoff on graduation
- [[decisions/ADR-005-momentum-bands]] — Why the dojo schedules this way
