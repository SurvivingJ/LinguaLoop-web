---
title: Word-Upload Queue — Technical Specification
type: feature-tech
status: in-progress
prose_page: word-upload-queue.md
last_updated: 2026-11-28
dependencies:
  - "NEW table: word_upload_queue (migrations/word_upload_queue.sql — PENDING live apply)"
  - "NEW code: services/word_list_import/queue.py, scripts/word_upload_queue.py, .claude/skills/word-upload-queue/SKILL.md"
  - "CHANGED: routes/word_list_import.py (queue mode default), config.py (WORD_LIST_INLINE_GENERATION), web/scheduler.py (hourly job), static/js/word_list.js, templates/word_list.html, static/i18n/*.json, scripts/export_sense_seed_worklist.py and scripts/export_gloss_worklist.py (--vocab-ids)"
  - "EXISTING: user_word_watchlist, services/word_list_import/match_sweep.py, services/vocabulary/word_resolver.py, services/exercise_content/store.py"
breaking_change_risk: medium
---

# Word-Upload Queue — Technical Specification

Decision: [[decisions/ADR-069-word-upload-queue]]. Original feature (watchlist, sweeps,
slot scheduling): [[tasklist/word-list-import.plan]].

## Architecture Overview

```
POST /api/word-list/submit                      (Config.WORD_LIST_INLINE_GENERATION false: default)
  validate (clean_words) -> daily cap (max(watchlist batches, queue batches) in 24 h)
  -> queue.enqueue_words  (upsert ignore-duplicates on user_id,language_id,raw_word)
  -> 202 {upload_batch_id, mode:'queue', queued, already_queued}
  -> pool job: queue.advance(upload_batch_id=…)  lookup only

web/scheduler.py  word_upload_queue_advance_hourly  (:35 every hour)
  -> queue.run_scheduled_advance()  -> queue.advance(all open rows)  lookup only

operator: scripts/word_upload_queue.py export --language L --apply   (dry run without --apply)
  -> queue.advance(create_vocab=True)
  -> stage_groups(open rows) -> exporters scoped by --vocab-ids / --sense-ids
  -> RUN/plan.md, RUN/queue.json        (RUN = data/word_upload_queue/<lang>-<stamp>, git-ignored)
  operator answers worklists with the skills, uploads, re-runs export … then advance

queue.advance(rows):
  resolve_rows    pending -> building (vocab_id)  | pending + missing=['vocab'] | failed
  check_assets    batched reads -> {sense_id, missing[]} per row
  _finish         missing == [] : UPDATE … SET status='done' WHERE id=? AND status='building'
                  -> INSERT user_word_watchlist (unless the learner already watches the sense)
                  -> match_sweep.sweep_immediate_matches(new rows)   (when a db_client is given)
```

Inline mode (`WORD_LIST_INLINE_GENERATION=true`) is unchanged:
`process_word_list_upload` on the worker pool, as documented in `routes/word_list_import.py`.

## Database Impact

New table `word_upload_queue` ([[database/schema.tech]]):

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | bigint | NN | identity (ALWAYS) | PK |
| `user_id` | uuid | NN | | FK `users(id)` ON DELETE CASCADE |
| `upload_batch_id` | uuid | NN | | the 202's id |
| `language_id` | smallint | NN | | FK `dim_languages(id)` |
| `raw_word` | text | NN | | CHECK length 1..40 (cleaned: NFC, whitespace collapsed) |
| `gloss_language_id` | smallint | | | FK `dim_languages(id)`; CHECK ≠ `language_id` |
| `vocab_id` | integer | | | FK `dim_vocabulary(id)`; set on resolve |
| `sense_id` | integer | | | FK `dim_word_senses(id)`; primary native standard sense |
| `status` | text | NN | `'pending'` | CHECK pending, building, done, failed, cancelled |
| `missing` | text[] | NN | `'{}'` | asset keys still to build |
| `detail` | jsonb | | | `lemma`, `reason` (failed) |
| `requested_at` / `updated_at` | timestamptz | NN | `now()` | |
| `completed_at` | timestamptz | | | set on done |

UNIQUE `(user_id, language_id, raw_word)`; indexes `(status, language_id, requested_at)` and
`(user_id, requested_at DESC)`. RLS on, no policy, `REVOKE ALL … FROM PUBLIC, anon,
authenticated`; service role only.

Reads for the checklist (all batched, ≤ 200 ids per `.in_()`): `dim_vocabulary`,
`dim_word_senses` (native standard + simple, gloss rows, `embedding IS NOT NULL`),
`word_assets` (`asset_type='prompt1_core' AND is_valid`), `exercises` (`is_active`), and the
exercise content store for audio URLs. Writes: `word_upload_queue`, `user_word_watchlist`
(insert, `ladder_exercises_generated=true`), `dim_vocabulary` (only with `create_vocab`), and
the sweep's match columns.

### Asset checklist (`queue.ASSET_KEYS`, build order)

| Key | Present when | Built by |
|---|---|---|
| `vocab` | a `dim_vocabulary` row for the lemma (or the raw word) | `export` / `advance --create-vocab` (`get_or_create_vocab_id`) |
| `sense` | primary native `standard` row and a `simple` row at the same `sense_rank` | batch-sense-generation → `upload_senses.py` |
| `embedding` | that standard row's `embedding` not null | `backfill_sense_embeddings --apply` (also done by `upload_senses.py`) |
| `pronunciation` | zh/ja only: standard row `pronunciation` not null | `backfill_pronunciations.py --apply` |
| `gloss` | if `gloss_language_id`: `simple` + `standard` rows in it at the same rank | cross-language-glosses → `upload_glosses.py` |
| `core` | valid `prompt1_core` `word_assets` row for the sense | batch-exercise-generation stage 1–3 |
| `exercises` | ≥ 1 active `exercises` row | batch-exercise-generation stage 4–6 |
| `audio` | every active `phonetic_recognition` / `listening_flashcard` item has its URL (`audio_url` / `front_audio_url`); unreadable content counts as missing | `backfill_exercise_audio.py` |

`gloss_language_id` = `users.native_language_id`, else English (2); NULL when equal to the
word's language. Fixed at submit.

### Resolution (no LLM)

`_Tokenizer.lemma_item` uses the language processor (`VocabularyExtractionPipeline
.get_processor`). For ja, trailing `助動詞` tokens are dropped first (食べた → 食べる,
走ります → 走る). A CJK word the tokeniser still splits (お茶 → 御 + 茶) is stored and
looked up under the raw word. Lookup order: lemma, then raw word. The shared
`_tokenize_single_word` (inline path) still has the old behaviour (TASK-1277).

## API / RPC Surface

### `POST /api/word-list/submit`
- **Arguments:** `{words: string[] (≤ 50), language: 'zh'|'en'|'ja'}` — unchanged.
- **Returns (queue mode):** 202 `{status:'success', upload_batch_id, mode:'queue', queued,
  already_queued}`. Inline mode: 202 `{upload_batch_id, mode:'inline'}`.
- **Errors:** 400 (validation), 401, 429 `RATE_LIMITED` (daily cap; in-flight only in inline
  mode), 503 `WORD_QUEUE_UNAVAILABLE` (queue insert failed; the daily slot is refunded).
- **Auth:** JWT. **Side effects:** queue rows; background lookup-only advance of the batch.

### `GET /api/word-list/watchlist`
- **Returns:** `{watchlist: [...as before], queue: [{id, raw_word, language_id,
  upload_batch_id, status, missing, requested_at, updated_at}]}` — the learner's
  pending/building/failed rows, newest first, ≤ 500. A failed queue read returns `queue: []`.

### `services.word_list_import.queue`
- `enqueue_words(db, user_id, language_id, words, upload_batch_id, gloss_language_id) -> int`
- `gloss_language_for(db, user_id, language_id) -> int | None`
- `count_recent_queue_batches(db, user_id, since_iso) -> int`
- `open_rows_for_user(db, user_id) -> list[dict]`
- `load_open_rows(db, *, language_id=None, upload_batch_id=None, ids=None, statuses=None)`
- `resolve_rows(db, rows, *, create_vocab=False)`; `check_assets(db, rows) -> {id: {sense_id, missing}}`
- `advance(db, *, language_id=None, upload_batch_id=None, create_vocab=False, db_client=None, sweep=True) -> summary`
- `run_scheduled_advance()` — scheduler target.

### `scripts/word_upload_queue.py`
`status`, `list [--status]`, `advance [--create-vocab] [--no-sweep]`, `export --language L
[--out-dir] [--no-create-vocab]`, `requeue --ids`, `fail --ids --reason`. The four writing
sub-commands are dry runs unless `--apply` (`_common.add_apply_flags`, TASK-1218); a dry run
reads the queue and prints, writing neither the database nor `RUN/`.
`export` hands a word a later stage only when the earlier ones are in
(sense → {embedding, pronunciation, gloss, core} → exercises → audio).

## Component Specification (UI)

`static/js/word_list.js`: queue rows render above watchlist rows with the raw word, a badge
(`word_list.queued` / `.building` / `.failed`) and "Not yet" in the match column. A queue-mode
submit shows `word_list.queued_message` and keeps it shown. New i18n keys in all four locale
files; `word_list.intro` reworded (no longer "right away").

## Key Architectural Decisions
1. **Own table, not `generation_queue`** — see ADR-069 (sense_id NOT NULL; not per learner).
2. **Lookup only in the web process** — learner text enters `dim_vocabulary` only via the
   operator run.
3. **Claim by conditional update** — `building -> done` with `.eq('status','building')`; the
   watchlist insert only follows a successful claim, so concurrent workers are safe without an
   advisory lock.
4. **One row per learner** — the learner-facing state and the watchlist insert are per learner;
   the operator script de-duplicates by vocab/sense id when exporting.

## Security Considerations
- Service role only; no client grant. Learner text is validated (`clean_words`) and stored
  as data; the skill tells the operator to read and `fail` junk or injection attempts before
  exporting. Worklists are local files under a git-ignored directory.
- The 503 path refunds the daily slot so a database outage does not burn a learner's quota.

## Testing Strategy
- `tests/test_word_upload_queue.py` (27): enqueue de-dup, gloss language, resolve
  lookup-only / create, ja tail, CJK raw-word fallback, every checklist key, audio URL field
  per type, finish + watchlist, no double finish, batch scoping, sweep call.
- `tests/test_word_upload_queue_routes.py` (9): queue-mode submit, background advance scope,
  re-submit, daily cap from the table, 503 + refund, watchlist `queue` field and fail-soft.
- `tests/test_word_upload_queue_script.py` (7): stage routing, exporter arguments, plan text,
  fail/requeue, dry runs write nothing, `--apply` export runs exporters and writes the plan.
- Inline-path tests pinned to `WORD_LIST_INLINE_GENERATION=true`.
- After the live apply: submit two words (one already fully built, one new); the built one
  appears on the watchlist within seconds; `python scripts/word_upload_queue.py status`
  shows the other as building.
