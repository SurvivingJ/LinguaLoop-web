---
title: Exercise Explanations in the Learner's Language
type: feature
status: in-progress
tech_page: exercise-explanations.tech.md
last_updated: 2026-11-26
open_questions:
  - "Which other exercise types should get per-option explanations next (cloze, semantic discrimination)? (TASK-1242)"
---

# Exercise Explanations in the Learner's Language

## Purpose
After answering, a learner sees why every option was right or wrong, written in their own
language, and multiple-choice options that are definitions are always shown in their own language.

## User Story
As an English speaker studying Japanese, when I answer "Which sentence contains an error?", I want
to see for each sentence what it means and why it is correct or wrong (and how to fix the wrong
one) in English, so I learn from every option and not only from the one I picked. When I am asked
to pick a word's meaning, I want the four meanings in English, not in Japanese.

## How It Works
1. **Spot the error.** Once the learner taps a sentence, each sentence shows a line underneath:
   "Correct" or "Error", what it means in the learner's language, and one or two sentences on why.
   The wrong sentence also shows "Correct form: …". The first time anyone sees an item, the
   explanation is written by a model (a few seconds, usually while the learner is still reading)
   and saved; everyone after reads the saved one. If none can be written, the item still works and
   shows the short note it always had.
2. **Pick the meaning (definition match).** The four options are the word's meanings in the
   learner's language: the right one and three meanings of other words that are about as common,
   about as long, and the same part of speech (so a verb is never the only "to …" option). Two
   options never share a listed equivalent ("merely" in both). If the word has no meaning written
   in the learner's language yet, the question is skipped for that learner rather than shown in
   the language being studied.

## Constraints & Edge Cases
- Explanations follow the item's own answer; the model is never asked which sentence is wrong.
- An item that is regenerated gets a new explanation; the old one is not shown against new
  sentences.
- Chinese: only 3,914 of 12,802 words have an English meaning yet, so about a third of Chinese
  definition questions are skipped for English speakers until those are written (TASK-1238).
- Test prestudy renders spot-the-error with its own page script and does not show explanations yet
  (TASK-1241).

## Business Rules
- Options and explanations a learner reads are in their native language (`users.native_language_id`,
  English when unset), never in the language being studied, unless no such text exists for an
  explanation (then the old note is shown).
- Explanations are written once per item and language and reused for every learner.

## Open Questions
- OPEN: other types with target-language notes (TASK-1242).

## Related Pages
- [[features/exercise-explanations.tech]]
- [[decisions/ADR-064-exercise-explanations-generated-once-and-cached]]
- [[features/practice-engine]]
- [[features/new-word-drill]]
- [[features/test-prestudy]]
- [[tasklist/fixes-2026-11-26.tasks]]
