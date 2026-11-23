---
title: Practice Package (the code behind Practice)
type: feature
status: complete
tech_page: ./practice-package.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN 2026-11-23: should repeated recent test misses override a word the system believes is known when choosing new words? The code lets them (recent-test list has no check); the decision record ADR-047 says known words are skipped. The owner wants misses to win and the record to be amended."
  - "OPEN: flashcard due dates are dated in UTC by the server while some readers use the learner's local day. No effect today (all three live plans are UTC); a fix must change every reader and writer together."
---

# Practice Package (the code behind Practice)

## Purpose

When a learner taps Practice, a small group of code files (the `services/practice/` package) decides which new words to start, assembles the day's exercises and records every answer. This page explains what that group does and how it is divided, for someone who has not read the code. The exact function-by-function version is [[features/practice-package.tech]].

## User Story

A learner opens Practice and expects three things to just work: today's exercises appear quickly and are the right ones, a few new words are introduced at a sensible pace, and when they answer, the answer is saved once, correctly, even if their phone double-sends it.

## How It Works

The package has five parts, each in its own file:

1. **Session assembly.** Builds the list of exercises. It first admits today's new words, then asks the database for the best exercises for the chosen mode (learn new words, or review), then tidies the list: tops up a very short session with reviews, adds the "study these again tomorrow" words from test prestudy, puts the new-word drill first, orders new words oldest-first and reviews most-overdue-first, fills in each exercise's actual text and applies the learner's Traditional-Chinese preference. Due Dual-Translation error cards are mixed in last. It also builds the optional "keep practising" rounds.
2. **New-word admission.** Decides which words become "new words today". The number is the learner's daily quota, reduced when too many reviews are overdue. Candidate words come in order from: words missed in tests and word quizzes in the last four weeks; words missed in calibration or the placement check; and (not built yet) words planned by look-ahead teaching. Each candidate must have enough exercises to teach it, or, with the new-word drill on, is admitted and sent to be generated.
3. **Attempt recording.** Saves each answer with one database call that either fully succeeds or leaves nothing behind. It records the attempt, counts it on the exercise, updates what we think the learner knows, moves the word along its ladder and credits study time. Two quick duplicate submissions can no longer both count as the first attempt. The review schedule (spaced repetition) is then updated by the server.
4. **Constants.** The tunable numbers: the minimum session length (20 items), the largest daily intake per call (12), the extra-round sizes (10 new words, 10 reviews) and so on.
5. **The service entrance.** A thin file, `practice_session_service.py`, joins the three working parts and is the single place the rest of the app calls.

## Constraints & Edge Cases

- If the learner has no study plan, no new words are admitted automatically; extra rounds still serve words already admitted and not started.
- A failed answer save fails the whole request and the app shows its normal error; nothing is half-saved.
- Admission failures never stop a session being served.
- Words that do not yet have enough exercises are queued for exercise generation (at most 5 per request); with the new-word drill on they are still admitted, because the drill's first session needs only a definition and an example sentence.

## Business Rules

- Only a learner's first attempt at an exercise changes what we believe they know; repeated attempts still update the review schedule.
- A single wrong answer is not enough to start a word from test evidence: it takes two, or a low confidence that the word is known. A single wrong answer in calibration is enough.
- Words already on the learner's ladder are never admitted twice.

## Open Questions

- **OPEN:** repeated recent misses versus "known" words (see frontmatter).
- **OPEN:** flashcard dates in UTC versus local day (see frontmatter).

## Related Pages

- [[features/practice-package.tech]] — technical counterpart with the module map
- [[features/practice-engine]] — what Practice is and how it ranks exercises
- [[features/new-word-drill]] — the first-days drill new words go through
- [[features/study-session-package]] — the package that builds the daily queue and calls this one
- [[features/session-budget-settings]] — the daily quota and the review governor
- [[features/practice-extra-rounds]] — the "keep practising" rounds
- [[features/test-prestudy]] — prestudy follow-ups
- [[decisions/ADR-047-basic-word-knowledge-prior]] — the knowledge-status rule the admission lists are meant to follow
