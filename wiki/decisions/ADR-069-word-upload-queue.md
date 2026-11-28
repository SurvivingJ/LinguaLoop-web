---
title: "ADR-069: Word-list uploads go to a queue, built offline"
status: accepted
date: 2026-11-28
---

# ADR-069: Word-list uploads go to a queue, built offline

## Context

`POST /api/word-list/submit` ([[features/word-upload-queue]]) used to resolve each uploaded
word and run the whole ladder LLM pipeline (sense generation, `VocabAssetPipeline`,
`LadderExerciseRenderer`) inside the web process, on an in-memory worker pool, about
5.5 minutes per new word, through OpenRouter/OpenAI keys. Nothing recorded a word before
it was processed, so a restart mid-batch lost the rest. The content the app actually
serves is authored by the operator with the in-session skills (batch-sense-generation,
cross-language-glosses, batch-exercise-generation, fat-seed-authoring), not by hosted
calls, and the inline path skipped glosses and audio altogether.

Owner, 2026-11-28: "Ideally they get put into a queue db table and then I can run ai LLM
over them to build the assets etc." Then: keep the inline path as an option you can switch
on; build everything; ignore credits for now.

## Decision

1. Submitted words are inserted into a new table `word_upload_queue`, one row per
   (learner, language, raw word), and the route answers 202. No LLM call in the web process.
2. The asset set a word needs before it reaches the learner's watchlist is: dictionary row,
   two-level native sense, embedding, pronunciation (zh, ja), a gloss in the learner's native
   language (English when unset), a valid ladder core, active exercises, and audio on every
   audio-bearing exercise.
3. The operator builds missing assets offline with the existing skills;
   `scripts/word_upload_queue.py export` writes their worklists scoped to the queued words
   (new `--vocab-ids` filters on the sense and gloss exporters; the exercise exporter already
   had `--sense-ids`) and a `plan.md` of what to run next.
4. A word is finished by `advance` (no LLM): when its checklist is empty it becomes `done`
   and its `user_word_watchlist` row is written, followed by the immediate test-match sweep.
   `advance` runs after each submit (that batch, lookup only), hourly from the scheduler
   (lookup only), and from the script (which may also create the dictionary row).
5. The web process never creates a `dim_vocabulary` row from learner input in queue mode;
   only the operator's `export` / `advance --create-vocab` does, after the operator has seen
   the words.
6. The inline path stays, behind `WORD_LIST_INLINE_GENERATION=true` (default false).
7. Credits are not charged in either mode for now (the pricing plan's `sense_import` spend
   is left for billing, TASK-1060).

## Consequences

- Uploaded words survive restarts and deploys, and the operator sees every word before it
  enters the shared dictionary.
- Words already fully built reach the watchlist within seconds (the post-submit advance) or
  within the hour; brand-new words wait for the operator's next run. The page says so.
- The daily cap now counts queued batches from the table, so it holds across workers.
- The finish step is a conditional `building -> done` update, so concurrent schedulers in
  several gunicorn workers cannot write a watchlist row twice.
- The audio check duplicates the two-entry type -> URL field map of
  `scripts/backfill_exercise_audio.py`; the two must change together.
- `migrations/word_upload_queue.sql` must be applied before queue mode works; until then a
  submit answers 503 `WORD_QUEUE_UNAVAILABLE` (the watchlist page still loads).

## Alternatives Considered

- **Reuse `generation_queue`.** Its `sense_id` is NOT NULL with an FK, and a raw word often
  has no sense yet; it is also keyed (sense, reason), not per learner. Rejected.
- **Resolve and create the dictionary row at submit.** Puts learner text into the shared
  dictionary unreviewed. Rejected; lookup only at submit.
- **A hosted-model worker draining the queue.** Contradicts how content is authored in this
  project (in-session skills, not hosted calls) and is what the owner asked to move away from.
