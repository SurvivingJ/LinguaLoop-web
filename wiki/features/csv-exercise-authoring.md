---
title: CSV Exercise Authoring
type: feature
status: in-progress
tech_page: ./csv-exercise-authoring.tech.md
last_updated: 2026-09-19
open_questions:
  - "Batch width per stage (items per call). Defaults are 8/8/8/8/12/4 for stages 1-6; not yet measured."
  - "ja suru-nouns (作業, 循環) labelled semantic_class 'action' get an L4 conjugation plan they cannot satisfy — fix the label, the gate, or the prompt? (TASK-801)"
---

# CSV Exercise Authoring

## Purpose
A way to build vocabulary-ladder exercises for many words at once, by running
the same prompts the automatic pipeline uses, one prompt at a time across the
whole word list, with an independent reviewer checking the work at two points.
It exists because the automatic pipeline takes about 5.5 minutes per word, and
[[features/lookahead-preteaching]] needs exercises for about 500 words per
language before it can do anything.

## User Story
As the operator, I want to hand a list of words to the tool and get back
exercises that went through the same steps and checks as the live pipeline,
without waiting minutes per word, and without a single person both writing
and approving the same items.

## How It Works
1. **Export.** One command pulls everything the database knows about each word
   into a spreadsheet: the word, its meaning, how hard it is, real example
   sentences found in the test transcripts, and the exact text of every prompt
   that will be used, pinned to its current version.
2. **Write the core.** The author answers the first prompt for every word:
   part of speech, meaning, reading, and ten example sentences. The real
   example sentences are kept word-for-word.
3. **Review the core.** A separate reviewer, who has never seen the author's
   work in progress, reads each word's sentences against the live review
   prompt and rewrites the bad ones. For each word it records whether it
   accepted, rewrote or rejected it.
4. **Plan.** The tool works out which exercise levels each word gets. This
   depends on what the author decided in step 2 (a verb gets conjugation
   practice; a noun does not), so it cannot happen earlier.
5. **Write the exercises.** The author answers the remaining prompts: listening,
   fill-in-the-blank, spot-the-mistake, conjugation, particles, and
   opposites. Each is written twice, over different sentences.
6. **Review the exercises.** The separate reviewer checks each word's items
   against the exact prompts the live review models would get, and rewrites
   the weak options.
7. **Assemble and upload.** The tool packages what survived into the files the
   existing uploader reads. The uploader validates everything again, stores
   it, and builds the exercise rows.

Every word that falls out along the way is listed with the step and the reason.

## Constraints & Edge Cases
- Only the export, the planning step and the upload talk to the database.
  Nothing but the upload writes to it.
- A reviewer that changes nothing at all across a whole batch is treated as a
  failure. That pattern means nobody actually read the items.
- The reviewer must say truthfully whether it changed something. The tool
  compares the before and after and rejects any item whose claim does not
  match.
- If any prompt changes version between the export and the planning step, the
  run stops and must be re-exported.
- Re-uploading words that already have exercise rows duplicates them. Clear
  the old rows first.
- Some words have no real one-sound-apart neighbours for the listening
  exercise (もたらす, 文脈). The author is told never to invent words; those
  items may be dropped when the exercises are built.

## Business Rules
- Exercise rows are never written directly. They are always built from stored
  word assets, which is what links each exercise to its source (TASK-512).
- The author and the reviewer never share a working context.
- A rewritten real example sentence stops counting as a real example.
- Japanese parts of speech use the UniDic labels (e.g. 形状詞), never Chinese
  ones.

## Open Questions
- **OPEN.** How many items per call each stage should carry. Measure it on the
  first real batch.
- **OPEN.** Whether nouns like 作業 ("work") should ever be labelled as actions.
  Today that label schedules conjugation practice the word cannot have
  (TASK-801).
- **ANSWERED (2026-09-19).** Do the reviews block or only annotate? They block:
  a rejected word is dropped, and a word the reviewer never saw cannot be
  uploaded.
- **ANSWERED (2026-09-19).** Can the level plan be exported up front? No. It
  depends on the author's answer to the first prompt, so it is computed in a
  planning step after the first review.

## Related Pages
- [[features/csv-exercise-authoring.tech]]
- [[features/lookahead-preteaching]]
- [[features/exercises.tech]]
- [[algorithms/vocabulary-ladder]]
- [[tasklist/csv-exercise-authoring.tasks]]
