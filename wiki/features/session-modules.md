---
title: Daily Session Modules (include / exclude)
type: feature
status: planned
tech_page: ./session-modules.tech.md
last_updated: 2026-10-13
open_questions: []
---

# Daily Session Modules (include / exclude)

## Purpose

Learners can switch individual **modules** of their daily session on or off in their settings,
per language. Examples are listening, reading, dictation, pinyin (Chinese) and pitch accent
(Japanese). An excluded module is left out of the planned daily session (`/session`) only. It
stays fully available everywhere else in the app.

## User Story

A Chinese learner commutes by train and can't play audio, so they never want listening in their
daily session. They also already know pinyin well. In **Study Plan → Daily session modules** they
untick *Listening* and *Pinyin* and save. That same day, the not-yet-started part of today's
session is rebuilt without them. The session is still about the same length, because the time
those two modules used is shared out among the modules they kept. When they're at home and want
a listening test, they can still pick one from the Tests page as before.

A Japanese learner who only wants tests and no vocabulary drilling can untick *Vocabulary
review* and set *New words per day* to 0. Their session then has no vocabulary chunks, and the
tests fill the whole day's time. (Unticking only *Vocabulary review* still leaves the daily
new words, which are set separately — see below.)

## How It Works

### The modules

Each language offers the modules in its study-plan template, plus vocabulary practice:

| Module | Chinese | Japanese | English |
|---|---|---|---|
| Reading | ✓ | ✓ | ✓ |
| Listening | ✓ | ✓ | ✓ |
| Dictation | ✓ | ✓ | ✓ |
| Pinyin | ✓ | | |
| Measure words | ✓ | | |
| Pitch accent | | ✓ | |
| Flashcard review | ✓ | ✓ | ✓ |
| Dual translation | ✓ | ✓ | ✓ |
| Vocabulary review (spaced-repetition / maintenance review, and the speed-round tail) | ✓ | ✓ | ✓ |

All modules are on by default. Any of them can be turned off, but **at least one must stay on**.
The save button refuses to save a plan with every module off.

**Vocabulary review is only the review part.** Since 2026-10-13 the *Vocabulary review* module
means reviewing words the learner already knows (spaced-repetition and decay maintenance) plus the
speed-round tail. It no longer covers learning new words. How many **new words** to introduce each
day is its own setting, *New words per day* (0 turns new words off), described in
[[features/session-budget-settings]]. Because new words are their own setting, a learner can drop
review but keep new words, or the reverse.

**What counts as "on" for the at-least-one rule.** A plan with *New words per day* above 0 counts
that as an included part of the session. So a learner may untick every module in the list as long
as they still ask for new words each day.

### Where the setting lives

The setting is **per language**, stored with that language's study plan. Turning off listening for
Chinese has no effect on Japanese. This matches the rule that every language has its own
independent plan ([[decisions/ADR-011-per-language-independent-budgets]]).

### What "excluded" means

- **Left out of the daily session.** The weekly plan gives the module no slots, and the daily
  resolver never schedules it. Special one-off slots don't either: the "retry a test you did
  badly on" slot and the "test that uses a word you uploaded" slot both skip excluded modules.
- **Still available everywhere else.** The Tests page, the flashcards page, dual translation,
  practice, calibration and so on all work as before. Tests the learner takes manually still
  update their ratings in the normal way.
- **Excluded is not deleted.** Ratings, history, per-skill weight overrides and flashcard decks
  are all kept. Turning a module back on picks up where it left off.

### Time is kept, not lost

The learner set a daily time target, so excluding a module does **not** shorten the session.
The minutes the excluded module would have used are shared among the modules that remain, in
proportion to how much time each already had. If a learner drops listening, their reading,
dictation, dual translation and practice time all grow a little. The mix among those modules
stays the same.

Flashcard review is the exception. It is one review block a day, sized by how many cards are due,
so it neither shrinks nor grows when other modules change. Freed time goes to the other modules.

### When a change takes effect

Immediately, including today:

1. The current week's plan is recomputed with the new set of modules.
2. If today's session has already been built, the parts the learner has **not done yet** are
   rebuilt. Anything already completed today stays completed and keeps counting.

The learner returns to `/session` and sees the updated queue.

## Constraints & Edge Cases

- **Last module.** If only one module remains on, its toggle is disabled in the UI, unless
  *New words per day* is above 0, which counts as included. The API also rejects a request that
  would exclude every module while *New words per day* is 0.
- **Only flashcards left on.** Flashcard review isn't scaled, so there is nowhere to put the freed
  time and the session is short (one review block). The settings page shows a hint saying so.
- **Mid-test change.** If the learner changes settings in one tab while a test of an
  about-to-be-excluded module is open in another tab, the test still submits and is scored and
  rated normally. It just no longer counts as a session slot.
- **Completed today, then excluded.** A test slot of that module that was finished earlier today
  stays in today's queue as completed. A completed practice or flashcard block of an excluded
  module disappears from the queue, but its minutes still count toward the week.
- **Template change.** Exclusions survive a template switch (30 → 45 minutes, for example). A
  module the new template doesn't offer is ignored.
- **Legacy fallback.** If the plan can't be resolved for some reason and the app falls back to
  the old three-test daily load, that fallback also skips excluded test types.
- **Coverage floor.** The planner normally guarantees every skill at least one slot a week.
  Exclusion overrides that guarantee for the excluded modules only.

## Business Rules

- `excluded_modules` must name only modules offered for that language. At least one module stays
  included, where `new_words_per_day > 0` counts as included.
- The `practice` module (shown as *Vocabulary review*) governs review only. New-word volume is
  governed solely by `new_words_per_day` (0 = off), never by the module list.
- Exclusion affects **only** daily-session planning (Tier B weekly allocation and Tier C daily
  resolution). It never hides content, blocks manual use, or changes how scoring works.
- Excluding a module never lowers the day's time budget, except in the "only flashcards left" case
  above.
- Changes apply to the current week and the not-yet-completed part of today. Completed work is
  never discarded.

## Open Questions

None. These were decided with the developer on 2026-10-12:

- ANSWERED: Freed time is redistributed so the daily length stays the same, rather than the
  session getting shorter.
- ANSWERED: The setting is per language, not global.
- ANSWERED: Every module can be toggled, including practice, flashcards and dual translation, but
  at least one must stay on.
- ANSWERED: Changes take effect immediately, including today's unfinished slots.

## Related Pages

- [[features/session-modules.tech]] — Technical specification
- [[decisions/ADR-032-session-module-exclusion]] — Why exclusion lives in Tier B with a Tier C guard
- [[features/session-budget-settings]] — Budget scope and the new-words-per-day setting
- [[decisions/ADR-033-budget-scope-and-new-word-budget]] — Why new words are a daily quota inside the session, with an optional extra round
- [[features/study-plans]] — The planner this feature constrains
- [[pages/study-session]] — The `/session` runner that shows the result
- [[tasklist/session-modules.tasks]] — Task breakdown (TASK-863–869)
