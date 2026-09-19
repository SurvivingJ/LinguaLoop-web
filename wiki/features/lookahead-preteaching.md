---
title: Lookahead Pre-Teaching
type: feature
status: planned
tech_page: ./lookahead-preteaching.tech.md
last_updated: 2026-09-19
open_questions:
  - "ANSWERED 2026-09-19: rank by points per MINUTE (`c4_per_minute`), not per word. Which word that picks flips with the per-word cost model: least-known-first wins if unfamiliar words are cheap per point, frontier-first wins if they are expensive. `c4_per_minute` tracks the best arm at every setting, so the ranking is settled — but its `kappa` parameter is NOT yet measurable (15 exercise_attempts in total). Ship kappa = 0 and fit it from attempts-to-Ring-2 once traffic exists."
  - "ANSWERED 2026-09-19: the learner picks it. `words_per_week` becomes a user setting (casual ~20, serious ~100), replacing the derived `target_new_rate` of daily_minutes // 6 (5/week at 30 min/day) as the ladder intake ceiling. NEW CONSEQUENCE: a serious learner burns the entire 1,582-sense ja demand pool in ~16 weeks, so generation is continuous, not a one-off 500-sense backfill."
  - "ANSWERED 2026-09-19: the target test is hidden from the learner until they are ready for it. The cohort is framed as 'words for the week ahead'; naming a test would both promise something A2 deliberately does not commit to and remove the reveal."
---

# Lookahead Pre-Teaching

## Purpose

Make the practice engine the thing that *prepares* the day's test, instead of a
separate activity running beside it. Words the learner does not know are taught
through the vocabulary ladder first; the test that needs those words is served
afterwards, once they have been learned.

## User Story

> "I opened Japanese pitch accent and got 14%, then 18%. It just feels too hard,
> and nothing I do seems to make it easier."

That is the complaint behind [[features/vocabulary-aware-test-selection]], and
that feature's answer was to *search harder for an easier test*. It runs into a
wall: on live Japanese content the best available test is still 27% unknown for
this learner, so the target of 3–7% is unreachable and even 15% is a stretch.

Lookahead Pre-Teaching answers the same complaint the other way round. Rather
than hunting for a test the learner happens to be ready for, it **makes the
learner ready for the test.** Teaching roughly 15 words moves an average
Japanese test from 37% unknown to 19% — inside the band — and the simulation
puts 98% of the catalogue in reach that way.

## How It Works

1. **Look ahead.** Once per cycle the system takes the ten tests the recommender
   would plausibly serve next and reads their linked vocabulary.
2. **Find the shared blockers.** It collects the senses the learner does not
   know (`p_known < 0.5`) and ranks them by how many of those ten tests they
   block. Words shared across the pool are worth far more than words that
   unlock one test.
3. **Open a cohort.** The top words — sized against the learner's own
   words-per-week target, which they choose (casual ~20, serious ~100) —
   become the cycle's cohort and are subscribed to the vocabulary ladder
   ahead of every other intake source.
4. **Teach them.** For the next few days the Practice session's Acquisition mode
   anchors on those words and drills them to **Ring 2 cleared** — recognition,
   meaning recall and form production, not just "have you seen this before".
   Because a ring needs first-attempt successes on two distinct calendar days,
   a cohort cannot be rushed through in one sitting; three days is the floor.
5. **Release the test.** When enough of the cohort has landed, the tests it
   unblocks are released into the daily session. If the learner stalls, a
   deadline releases them anyway rather than holding the catalogue hostage.
6. **Reveal, don't promise.** The learner is never told which test the cohort is
   preparing them for. They see "words for the week ahead"; when the cohort
   lands, the test appears in their day already unlocked. Naming it up front
   would promise a specific test the pool design deliberately does not commit
   to, and would trade the reveal for an obligation.
7. **Measure honestly.** The test's unknown share is snapshotted at release and
   never recomputed, because the test result itself rewrites the vocabulary
   knowledge the measure is built from.

## What Blocks It Today

The algorithm works and the content does not. Of the ~17 words that block an
average Japanese test, **1.8 have enough exercises to drill**; in Chinese, using
only ladder exercises, **zero** do. Exercise generation has been
frequency-first, so it has covered exactly the words a learner at this level
already knows: the average sense with exercises is ~80% likely known.

The consequence is measurable — 15 exercise attempts have ever been recorded
against 54 test attempts, and all 47 subscribed ladder words are still in state
`new`.

So this feature ships in two halves, and the second half is the one that
matters: **re-point exercise generation from frequency-first to demand-first.**
Generating ~500 demand-ranked senses per language takes Japanese from 7% to 76%
of the catalogue pre-teachable. That is about two days of wall clock and twelve
dollars per language.

## Constraints & Edge Cases

- **A cohort cannot be learned in a day.** The ladder's cross-session gate
  requires successes on two distinct calendar days per family, so the minimum
  useful lead time is three days — and no words-per-week setting can shorten
  it. A learner who studies once a week gets one cohort per visit-pair.
- **A fast learner outruns the content.** At 100 words/week the ja demand
  pool (1,582 test-referenced senses with no exercises) lasts ~16 weeks.
  Generation has to become a standing process, not a one-off backfill.
- **Recognition-only preview does not work.** Stopping at Ring 1 leaves only 36%
  of tests in band against 98% for Ring 2. A "tomorrow's words" flashcard screen
  is not a cheap version of this feature.
- **Mastery is waste.** Drilling past Ring 2 to Gate A costs 66% more time for
  no additional tests in band. Pre-taught words hand off to FSRS at Ring 2.
- **No target test is promised.** The cohort is chosen from a *pool*, so the
  learner is never blocked waiting on one specific test, and a test that becomes
  unsuitable for other reasons costs nothing.
- **Starved words are not silently dropped.** A blocking word with no exercises
  is the strongest possible generation signal — it is queued, with the cohort as
  its reason, and the queue is drained ahead of speculative generation.
- **Unlinked tests are unaffected.** 17% of English and 22% of Chinese tests have
  no linked vocabulary; they keep their neutral treatment and are never
  penalised for being unteachable.

## Business Rules

- Pre-teaching never *blocks* a learner from taking a test they ask for. It
  orders the daily session; it is not a lock.
- A cohort expires. An unfinished cohort does not accumulate indefinitely —
  it closes at its deadline and its unlearned words fall back to the ordinary
  evidence queue.
- Practice remains free of token cost, unchanged.
- The supply gate is absolute: a word with fewer than 3 active exercises is
  never subscribed, whatever its demand rank. Subscribing unservable words is
  the live failure this rule exists to prevent.

## Open Questions

- **ANSWERED 2026-09-19** — which words first? Rank by **points of knowledge
  gained per minute of practice**, not per word. One parameter of that
  ranking — whether unfamiliar words cost more or less per point than
  half-familiar ones — is still unmeasured, and it is what decides whether
  the ranking behaves like least-known-first or frontier-first.
- **ANSWERED 2026-09-19** — the learner sets their own words-per-week target
  (casual ~20, serious ~100). This replaces the derived 5/week and removes
  the conflict with cohort size entirely.
- **ANSWERED 2026-09-19** — does the UI name the target test? **No.** The target
  is hidden until the cohort is ready; then the test surfaces as unlocked. The
  learner sees "words for the week ahead" while learning, never "this is for
  Thursday's reading test".
- **ANSWERED 2026-09-19** — how deep before the test? Ring 2 cleared. Preview is
  insufficient, mastery is waste.
- **ANSWERED 2026-09-19** — pin one test or work from a pool? A pool: ~10× fewer
  words per test brought into band.

## Related Pages

- [[features/lookahead-preteaching.tech]] — full technical specification
- [[evaluations/preteach-variants-2026-09-19]] — the variant simulation behind every number here
- [[decisions/ADR-026-lookahead-preteaching]] — the decisions and what was rejected
- [[features/practice-engine]] — the engine this makes central to the day
- [[features/vocabulary-aware-test-selection]] — the selection-side answer to the same problem
- [[features/study-plans]] — the orchestrator that owns the daily budget
- [[algorithms/vocabulary-ladder]] — rings, families, the cross-session gate
- [[features/exercises]] — where the missing content has to come from
