---
title: The Tests Route Package
type: feature
status: complete
tech_page: ./routes-tests-package.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN: Submitting a test with an unknown address may answer a server error instead of 'test not found' (the lookup raises when no row matches). Not tried against the running site; see [[features/routes-tests-package.tech]]."
  - "OPEN: The tests list endpoint (`GET /api/tests/`) has no caller in the repository. Keep it, or remove it?"
---

# The Tests Route Package

## Purpose

Everything the website does with comprehension tests over HTTP lives in the `routes/tests/` package: finding tests, opening one, submitting answers, studying a test's words beforehand, and fetching a test's sentences with translations. It used to be one 1,361-line file; on 2026-11-14 it was split by topic with no change to any address or behaviour.

## User Story

As a learner I want to be offered tests at my level, open one and read or listen, answer the questions, and immediately see my score, how my rating moved, the explanations and a short quiz on the words I was unsure about. If I want, I study the test's key words first, and afterwards I can translate part of the passage from my own language.

## How It Works

1. **Finding tests.** The site offers recommended tests (up to nine, matched to the learner's rating), one random matching test, today's planned load, a filterable list and the learner's history.
2. **Opening a test.** Anyone can open a test by its address; if the learner is signed in, the transcript stays hidden when today's plan asks for dictation, and the definitions of the words are shown in the learner's preferred language.
3. **Submitting.** The learner sends their answers (or, for the pinyin and pitch-accent games, how many items they got right; for dictation, what they typed). The database grades and records the attempt and moves the ratings in one step. Afterwards the server updates what it believes the learner knows about each word, schedules flashcards, builds a five-word quiz and returns everything in one answer. Timing and plan bookkeeping run alongside, and a failure there never costs the learner their result.
4. **Studying beforehand (prestudy).** The learner can open a study sheet for a test: the passage's key words with meanings, exercises for the words they mark as unknown, and a way to start a translation of the most relevant sentences. After the test, a follow-up sheet covers the words behind the questions they got wrong.
5. **Sentences.** The server can hand out a test's sentences with reference translations in the learner's language; for the translation stage the original sentences stay hidden until the learner has taken the test today.

## Constraints & Edge Cases

- Pinyin submissions only for Chinese tests, pitch-accent only for Japanese; the reported totals may not exceed what the test really contains.
- A time window sent with a submission is validated and capped at 20 minutes; a forged window is rejected before anything is recorded.
- The same submission sent twice (same idempotency key) records one attempt.
- If the post-submission steps fail, the learner still gets the score; if the grading step fails, they get a generic "submission failed" message with no database detail.

## Business Rules

- The correct answers are never sent before submission; explanations appear only in the submission result.
- Only active tests can be opened or submitted.
- A test taken within six hours of a completed prestudy session counts as "prestudied" and moves the rating less (the server checks this itself).
- Dictation is always graded on the server.

## Open Questions

- OPEN: unknown test on submit (see frontmatter).
- OPEN: the unused list endpoint (see frontmatter).

## Related Pages

- [[features/routes-tests-package.tech]] — Technical specification (module map, submit flow)
- [[features/comprehension-tests]] — The test engine
- [[features/test-prestudy]] — Prestudy
- [[features/dictation]], [[features/pinyin-trainer]], [[features/pitch-accent-trainer]] — The other submit modes
- [[algorithms/elo-ranking]] — How ratings move
- [[api/rpcs.tech]] — Route table
