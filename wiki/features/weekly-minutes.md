---
title: Weekly Minutes (accurate "studied this week")
type: feature
status: planned
tech_page: ./weekly-minutes.tech.md
last_updated: 2026-10-14
open_questions:
  - "OPEN: should minutes studied on a second language also appear in a cross-language total? (v1 shows one language at a time.)"
  - "ANSWERED: activity outside planned sessions counts (developer decision 2026-10-14)."
  - "ANSWERED: tests count measured time, flashcards and dual translation count measured active time, all clamped server-side."
---

# Weekly Minutes

## Purpose
The Study Plan page tells the learner how many minutes they studied this week against their weekly target. Today that number is wrong: it only counts vocabulary practice exercises, so a learner who does tests, flashcards or dual translation sees "0 minutes" for real work. This feature makes the number honest.

## User Story
As a learner, I do a reading test, ten minutes of flashcards and a dual-translation passage. I open the Study Plan page and see "Studied this week: 34 / 210 min", with a breakdown showing where the time went. It does not matter whether I did these inside the planned daily session or on my own from the Tests page.

## How It Works
1. Every time the learner finishes a unit of study (a test, a vocabulary exercise, a flashcard, a dual-translation submission, a classifier or counter drill), the server records how long it took and files it under the right kind and the learner's current local week.
2. Time is measured, not guessed: tests use the start and finish times of the attempt, vocabulary exercises use the time the exercise took, and flashcards and dual translation use the active time the page measured (time the tab was visible and the learner was interacting).
3. The server caps every single credit so one forgotten open tab cannot inflate the week.
4. Each unit of study is counted exactly once, even if the browser retries.
5. The Study Plan page shows one progress line "Studied this week: X / Y min" (Y is the weekly target) and a breakdown by kind: tests, vocabulary practice, flashcards, dual translation, other drills. The per-skill counts table stays.
6. The week is the learner's own local Monday-to-Sunday week, the same week the planner uses, so the page and the planner agree around midnight and across timezones.

## Constraints & Edge Cases
- Time the learner spent outside a finished unit (reading the page, an abandoned test) is not counted.
- A test submitted without start/finish times (very old client) earns no minutes; counts are unaffected.
- If the learner has no plan row for the week yet, minutes are still recorded; the page shows the total without a target.
- Time is attributed to the week in which the activity is submitted (learner local date).
- Existing weeks: the current week is backfilled once from stored attempt durations. Flashcard and dual-translation time before this feature shipped was never measured and is not backfilled.

## Business Rules
- One source row (attempt, review, submission) is credited at most once per kind.
- Per-credit caps: test and drill 20 min, vocabulary exercise 5 min, flashcard 2 min, dual-translation submission 15 min, dual-translation card review 2 min.
- Minutes shown are seconds / 60, rounded to whole minutes for display only.
- This "studied" figure is for display and motivation; planner logic (counts, practice seconds, shares) is unchanged.

## Open Questions
- OPEN: cross-language total (see frontmatter).

## Related Pages
- [[features/weekly-minutes.tech]]
- [[decisions/ADR-035-study-time-ledger]]
- [[features/study-plans]]
- [[pages/study-session]]
- [[tasklist/weekly-minutes.tasks]]
