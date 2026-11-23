---
title: Study Session Package (the code behind the daily session)
type: feature
status: complete
tech_page: ./study-session-package.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: flashcard due dates are compared in UTC by some readers while the session itself runs on the learner's local day. No effect today (all three live study plans are UTC); a fix must change all readers and writers together."
---

# Study Session Package (the code behind the daily session)

## Purpose

When a learner opens the `/session` page, the `services/study_session/` package turns the day's plan into one ordered to-do list (tests, practice chunks, flashcards, translation passages, and a few conditional extras) and remembers what has been done. This page explains it for someone who has not read the code; the exact version is [[features/study-session-package.tech]].

## User Story

A learner opens the session and sees today's work in a sensible order with a progress bar. If they close the app and come back, the list is the same and they resume where they left off. When they finish, the app offers to keep going if there is still work left.

## How It Works

The package has two files:

1. **The queue builder** decides the order. It only works on information it is handed and never touches the database, so it is easy to test. Flashcards go first as a warm-up. Tests are shuffled so that two of the same kind are never next to each other, and the same learner gets the same order all day. Practice chunks of at most ten minutes are spread evenly through the tests; translation passages go in among the practice. A timed "speed round" of well-known words is added at the end as an optional bonus. It then adds the conditional pieces: a short "study these words first" block before hard tests, a small review chunk for new-word drill reviews and next-day prestudy reviews, and a repair block for the learner's own translation mistakes. If everything is done, it works out what optional extra work remains (due reviews, then leftover new words, at most 20 minutes at a time).
2. **The session loader** gathers what the queue builder needs. It loads today's tests and minute targets, admits today's new words, reads several counts at once (so one slow count does not slow the page), asks the queue builder for the list, and adds a short message about the review backlog. It also marks a block as done, rejecting anything that is not part of today's list, and credits weekly progress for flashcard and translation blocks.

The `/session` page is a single screen that asks the server for this list and plays each item in turn with the right player (reading, listening, practice, flashcards and so on).

## Constraints & Edge Cases

- If the learner has no study plan, the list is built from the older rule set and has no practice chunks; the review chunk can still appear so due reviews are not hidden.
- If any optional part fails (prestudy planning, speed-round check, counts), only that part is left out; the session still loads.
- Marking a block done twice changes nothing.
- "Today" is the learner's own local day from their plan's timezone (UTC when none is set).

## Business Rules

- Optional extras (tail, speed round, tests moved aside to make room for prestudy) never count towards completing the day.
- A block can only be marked done if it is in today's list.
- The speed round and the translation-repair block do not add to the weekly targets.

## Open Questions

- **OPEN:** flashcard dates in UTC versus local day (see frontmatter).

## Related Pages

- [[features/study-session-package.tech]] — technical counterpart
- [[pages/study-session]] — the page learners see
- [[features/study-plans]] — where the minute targets come from
- [[features/practice-package]] — the package that supplies new words and practice
- [[features/session-modules]] — which modules the learner switched off
- [[features/session-budget-settings]] — the optional tail and the review backlog message
- [[features/test-prestudy]] — the "study first" blocks
