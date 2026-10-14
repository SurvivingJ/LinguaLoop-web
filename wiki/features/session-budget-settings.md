---
title: Session Budget Settings (daily session card)
type: feature
status: planned
tech_page: ./session-budget-settings.tech.md
last_updated: 2026-10-13
open_questions:
  - "OPEN: how the weekday shape scales new words. The shape is normalised to sum to 7, so a 5-day shape gives each active day a weight above 1. This spec scales new words by the same weight (rounded) so the weekly total and the daily amounts agree. The design text said 'words per active day, 0 on rest days'."
  - "ANSWERED 2026-10-13: a new word counts as started (and as completed for the week) on the day the learner makes their first attempt at it, whether it was admitted that day or earlier, in the main session or the extra round."
  - "ANSWERED 2026-10-13: with Vocabulary review switched off and new words above 0, the combination is allowed. All new words come in the optional extra round, and the settings page warns: Vocabulary review is off — words you learn won't be reviewed."
  - "ANSWERED 2026-10-13: the daily number counts words started, like Anki. Words admitted but not started carry over and are offered first; the app only tops up so that carried-over words plus words started today reach the day's quota."
  - "OPEN: tunables chosen without data: how far back 'recent tests' reach (28 days), how many reviews one new word causes in its first month (7), how long one review takes (20 s fallback), how big a review backlog is allowed (one day), how long one extra round is (20 min), how long a calibration miss stays usable (90 days)."
---

# Session Budget Settings (daily session card)

## Purpose

One **Daily session** card in Study Plan settings lets a learner decide what their daily time
target covers and how many new words they want to meet each day. It sits next to the module
on/off switches from [[features/session-modules]] and replaces the idea that new vocabulary is
just "whatever practice time is left".

## User Story

A learner sets 30 minutes a day for Chinese. Today that 30 minutes silently includes new-word
practice, so the number of new words depends on how the planner happens to split the time. They
want two things. First, to say exactly "teach me 5 new words a day". Second, to choose whether
their 30 minutes should cover tests and vocabulary review, or only tests, with review and new words
coming after the session if they feel like carrying on.

On the card they pick a scope, switch modules on or off, and type a number of new words. The card
tells them how that plays out ("about 2 of these fit inside your 30 minutes; the rest come in an optional
extra round") and what it will cost later ("about +12 min a day of reviews in a month").

## How It Works

### The three settings

1. **Which modules are in the session.** Reading, listening, dictation and the others, exactly as in
   [[features/session-modules]]. One change: the *Vocabulary practice* module is renamed
   **Vocabulary review**. It now means only keeping known words fresh (flashcard-style reviews
   and the speed-round tail). It no longer controls new words.
2. **What the daily time covers** (the budget scope). Two choices:
   - **Tests and review** (default, today's behaviour). The daily target covers tests,
     flashcards, dual translation and vocabulary work: due reviews first, then new words.
   - **Tests only.** The daily target covers only tests, flashcards and dual translation. Vocabulary
     review and new words are not part of the daily target; they come in the optional extra round
     after the session.
3. **New words per day** (0 to 50). A number of words, not minutes. 0 turns new-word teaching off.
   It works like a daily quota in a flashcard app: it is the number of new words you are offered
   each day, and it is not extra time added to your target.

### How a day is built

A daily session has a **main session** and an **optional extra round**.

- **The main session** is the learner's minutes for the day, shaped by the weekday multipliers. It holds
  tests, flashcards and dual translation. Under *Tests and review* it also holds a vocabulary share:
  the app puts the **due reviews first**, then as many of today's new words as still fit. Any vocabulary
  time that is not needed (for example, nothing is due and no new words are available) goes back to tests.
  The day never ends up empty or short.
- **The optional extra round** comes after the main session and is never required. It holds the due reviews
  that did not fit (most overdue first), and then the rest of today's new words. At the end of the main
  session the learner sees, for example, "Session done — 0 reviews and 4 new words left today. Keep going?".
  Work done in the extra round still counts toward the week's targets. Under *Tests only*, all review and all
  new words are in the extra round.

Flashcards and dual translation count as "tests" for the scope choice. They are inside the daily target under
both scopes.

### Where new words come from

The daily number counts words you **start**, as in Anki. Words the app admitted earlier but you never started are
kept and offered first; the app only adds enough new ones so that those plus the words you have started today reach the
day's number. Candidates come from these sources, in this order:

1. **Words from your recent tests that you missed or don't know yet**, including words from the
   quick word quiz after a test. Tests taken in the last four weeks (a tunable window) count. The most
   recently missed words come first.
2. **Words you got wrong in calibration.** A single wrong answer in a (definition-mode) calibration
   run is enough to nominate a word. These come after the test-based words, because a one-off calibration
   guess is weaker evidence than repeated test results. A word you later show you know is skipped.
3. **Lookahead cohorts** ([[features/lookahead-preteaching]]), once that feature exists. Until
   then this source is empty.

A word is only admitted if it already has enough practice exercises behind it. At present few
words do, so most days the quota will **not be fully met**. The app records how many words short it
fell, asks for more exercises to be generated for the words it could not use, and shows the
shortfall on the settings page ("New words: 9 / 35, 26 short because exercises are still being
prepared"). The practice time those missing words would have used goes back to tests inside the daily target.

### Keeping reviews under control

Reviews are always scheduled before new words, and the app watches the review backlog (reviews that were
due before today and are still not done):

- backlog up to one day's worth of review time: the full quota is offered;
- up to two days' worth: **half** the quota (rounded down);
- more than that: **no new words** until the backlog is cleared.

The learner sees "New words paused — catching up on 45 reviews" (or "reduced"). The backlog is re-checked
every time the session loads, so new words come back as soon as the reviews are done.

On the settings page, next to the new-words box, the card shows a forecast such as "≈ +12 min/day of
reviews in a month": every new word comes back for reviews over the following weeks, so a higher daily
number means a bigger daily review load about a month later.

### When a change takes effect

Immediately, as for modules: the current week's plan is recomputed and the not-yet-done part of
today's session is rebuilt. Anything already completed today stays completed.

## Constraints & Edge Cases

- **Always at least one module.** The number of new words counts as a module. A learner may turn
  every other module off if new words per day is above 0. The save is refused only when every
  module is off *and* new words is 0.
- **Tests only needs a test module.** Choosing *Tests only* while every test and surface module is
  off is refused, because the daily target would then cover nothing.
- **Rest days.** A weekday with multiplier 0 gets no new words.
- **Vocabulary review off.** There is no review time to share, so new words are offered only in the
  optional extra round, and no reviews are scheduled or counted in the backlog. This combination is allowed, and
  the settings page shows "Vocabulary review is off — words you learn won't be reviewed." under the new-words box.
- **Brand-new learner (cold start).** New learners do calibration mode and some introductory tests.
  Calibration (definition mode) measures ability and picks the first tests, and now also records what the
  learner got wrong (including "I don't know" answers) as vocabulary evidence; questions left unanswered are ignored. The introductory tests supply the recent-test unknowns (first
  source), calibration misses are the second source, and the upcoming tests supply pre-teaching words
  (third source). Pronunciation-mode calibration records no vocabulary evidence.
- **Shortfall is normal for now.** Few words have exercises. The day still fills its daily target (the unused
  vocabulary minutes go to tests) and the shortfall is shown.
- **Existing learners.** Everyone keeps *Tests and review* and gets a starting new-words number
  derived from their daily minutes (30 min a day gives 5 **per day**). This is about seven times the old
  effective rate (the old formula was a per-week figure); it is accepted on purpose, and the review forecast and the
  review governor exist to keep it manageable.
- **Speed round.** Hidden from the session when Vocabulary review is off.
- **Excluded is not deleted.** Turning Vocabulary review off does not remove any word from the
  learner's ladder or review schedule. It only stops the daily session from scheduling review.

## Business Rules

- `daily_minutes` is the length of the main session. The optional extra round is never part of it and is
  never needed to finish the session.
- New words per day is a whole number from 0 to 50 and is a daily quota, not a time budget.
- The budget scope is exactly one of *Tests and review* or *Tests only*.
- Flashcards and dual translation are "tests" for scope purposes.
- Due reviews are scheduled before new words, in the main session and in the extra round.
- Rest days (multiplier 0) receive no new words.
- A new word is admitted only if it already has at least the minimum number of exercises.
- The quota is counted per learner-local day (from local midnight). Admission is never undone.
- A single wrong calibration answer can nominate a word, but never ahead of test and word-quiz evidence.
- The weekly module rules in [[features/session-modules]] still apply, with the amendment that new
  words per day above 0 counts as an included module.

## Open Questions

- ANSWERED 2026-10-13: layout of the card. Option A, one card with stacked sections (scope, modules, new words with
  forecast, typical day).
- ANSWERED 2026-10-13: starter words for brand-new learners. Calibration plus introductory tests give the sources:
  introductory-test evidence, and calibration misses recorded as vocabulary evidence.
- ANSWERED 2026-10-13: the default of 5 words a day at 30 minutes is intended, although it is about 7x the old per-week rate.
- ANSWERED 2026-10-13: freed minutes are not filled by scaling tests up; new words are a quota inside the main session, with the
  remainder in an optional extra round, and unused vocabulary minutes return to tests.
- OPEN: weekday multipliers and new words.
- ANSWERED 2026-10-13: a "completed" new word is one the learner has started: their first attempt at it falls on that day.
- ANSWERED 2026-10-13: new words when Vocabulary review is off (allowed, extra round only, with a warning); unstarted admitted
  words (carried over and offered first; they count toward the day's quota only once started).
- ANSWERED 2026-10-13: the review forecast uses the learner's typical time per vocabulary exercise (all vocabulary exercises, not
  review-only) and is shown as an estimate.
- ANSWERED 2026-10-13: in calibration, "I don't know" counts as a wrong answer; questions never answered because the learner quit are ignored.
- OPEN: the tunables listed in the frontmatter.
- ANSWERED 2026-10-13: new words are a word count, not minutes.
- ANSWERED 2026-10-13: flashcards and dual translation count as tests for scope.
- ANSWERED 2026-10-13: "Exercises" means only the vocabulary ladder practice; the module is renamed
  Vocabulary review.
- ANSWERED 2026-10-13: nominate from recent tests first, then calibration misses, then lookahead cohorts; no frequency list.
- ANSWERED 2026-10-13: under *Tests only* the planner still sizes a weekly review target from how much review is due (with a cap),
  but review is served in the extra round, not inside the daily target.

## Related Pages

- [[features/session-budget-settings.tech]] — Technical specification
- [[features/session-modules]] — Module on/off switches this card absorbs
- [[features/study-plans]] — The planner that builds the weekly and daily plan
- [[features/calibration]] — Calibration (cold-start evidence)
- [[features/lookahead-preteaching]] — Third source of new words (not yet built)
- [[pages/study-session]] — The `/session` runner that shows the result
- [[decisions/ADR-033-budget-scope-and-new-word-budget]] — Why scope and new words work this way
- [[decisions/ADR-009-two-budget-tests-vs-practice]] — The budget model this amends
- [[decisions/ADR-032-session-module-exclusion]] — Module exclusion
- [[decisions/ADR-011-per-language-independent-budgets]] — Per-language settings
- [[tasklist/session-budget-settings.tasks]] — Task breakdown
- [[tasklist/session-modules.tasks]] — Module tasks this feature amends
