---
title: Exercise Explanations in the Learner's Language — Technical Specification
type: feature-tech
status: in-progress
prose_page: exercise-explanations.md
last_updated: 2026-11-26
dependencies:
  - "services/exercise_explanations.py (new)"
  - "services/vocabulary_ladder/definition_serving.py (new)"
  - "table exercise_explanations (migrations/exercise_explanations.sql, NOT applied)"
  - "dim_word_senses cross-language gloss rows (definition_language_id = learner's language)"
  - "OpenRouter (deepseek/deepseek-v4.1-flash, fallback google/gemini-3.5-flash)"
breaking_change_risk: low
---

# Exercise Explanations in the Learner's Language — Technical Specification

Two serve-time fixes for content stored in the target language (TL) but read by the learner in
their native language (NL = `users.native_language_id`, via
`gloss_lookup.get_user_definition_language_id`, English when unset; memoised per GET request
since 2026-11-26).

## 1. `definition_match` options in the NL — `services/vocabulary_ladder/definition_serving.py`

**Cause.** `deterministic/definition_match.py` takes key and distractors from the word's
own-language senses (`lexicon._load_entries` filters `definition_language_id == language_id`) and
stores them under `content.nl.<DEFAULT_NATIVE_LANGUAGE>` (`en`). For ja/zh that is TL text filed
as `en` (~11.9k active ja items). The client's `flattenNl` picks `nl.en`, so English speakers saw
Japanese definitions. v1 rows (`correct_definition` + flat `options`) are the same.

**Fix (serve time).** When NL ≠ TL, every `definition_match` item is rebuilt:

- *Key*: the NL gloss row of the same `(vocab_id, sense_rank)`, at the item sense's
  `definition_level`, else `standard`, else `simple`, else any.
- *Distractors*: `Lexicon.definitions_near` (the generator's own frequency ±1/±2 Zipf and length
  0.6–1.6 / 0.4–2.5 staging) over rank-1 NL glosses at the key's level **and part of speech**
  (falling back to the level, then everything, when a slice has < 40 entries), oversampled to 12,
  then any candidate sharing a normalised gloss term with the key (`gloss_terms`: the `;`-separated
  equivalents before " — ", articles and "to" stripped) is dropped; 3 kept. The key word's own
  gloss rows are excluded. Seeded `random.Random(f'definition_match:l1:{sense_id}:{nl}')`.
- *Output*: flat content — `options`, `correct_answer`, `correct_definition` (both the key),
  `definition_language_id`, `nl_language`; `nl` and `schema_version` removed. Read unchanged by
  `ExRenderers.renderDefinitionMatch` (flat content passes `flattenNl`) and by prestudy's
  `trim_exercise`.
- *Not rebuildable* (no NL gloss for the meaning, < 3 distractors, pool unavailable): dropped
  when the stored options' script family (`definition_match.script_family`) differs from the NL's,
  else kept. Content declaring `definition_language_id == NL` is left alone.

**Gloss pool.** All gloss rows for `(word_language_id, definition_language_id)` (ja→en 13,434
rows, 6,717 meanings) plus the language's `dim_vocabulary` (lemma, Zipf, POS), fetched as flat
pages concurrently on the module's own `gloss-pool` executor (16 + 8 pages) and joined in Python;
cached per process for 6 h (a failed load for 60 s). Measured 1.6 s cold from the dev container;
an embedded `dim_vocabulary(...)` per row made 16 concurrent pages hit the 8 s statement timeout.
`warm()` starts the load early; `get_pool(timeout=5)` waits for it. The same pool now serves the
new-word drill's option pool (`intro_drill._distractor_pool` → `GlossPool.rows_from`), replacing
an uncached query measured at up to 2.7 s.

**Call sites.** `SessionAssemblyMixin._hydrate_items(payload, language_id, nl_language_id)`
(`prepare` runs beside `store.hydrate`, `apply` after); `intro_drill._block_exercises`;
`prestudy._load_exercises(..., nl_language_id)` (payload and on-demand route).

## 2. Per-option spot-the-error explanations — `services/exercise_explanations.py` (ADR-064)

**Types**: `spot_incorrect_sentence` (`SPOT`) and `semantic_discrimination` (`PICK`, "pick the
sentence that uses the word correctly"). Explainable shape: ≥ 2 sentences with text, ≥ 1 right and
≥ 1 wrong.

**Stored notes first (`stored_entries`)**: when every sentence already has an `explanation` in
Latin script and the learner reads English, those notes are attached as they are (`meaning` empty)
and no model is called. Measured 2026-11-26: ja pick items 87/200 qualify; 113/200 lack a note on
the correct sentence; zh 47/150 have only a joined Chinese note — those are generated.

**Prompt (v1)**: system "experienced {TL} teacher … learner whose native language is {NL}".
SPOT: user lists `n. [CORRECT|ERROR] text` (+ the stored `error_description` as a hint), "do not
change that judgement", asks per sentence `meaning`, `explanation` (1–2 sentences), `correction`
(error only). PICK: names the word (`target_word`), lists `n. [CORRECT|WRONG] text` with each
sentence's stored `explanation` as a teacher's note ("keep its point"), asks `meaning` and
`explanation` (correct: what the word means here and why it fits; wrong: why not, and which word
would). `call_llm(..., response_format='json', temperature=0.2, max_tokens=2000, timeout=30,
pipeline='exercise_explanations', task_name='spot_error_explanation' | 'pick_sentence_explanation',
template_version=1)`.

**Prompt v2 (2026-11-26, owner-approved after reviewing an example)**: a wrong sentence's
`meaning` is its LITERAL translation, mistake included ("I boiled the fragments on the floor with a
broom", not the intended "I swept them up"), shown as "Literally: …"; explanations must not open
with a verdict word (the app shows it). Spot items: the reviewed `corrected_sentence` of the item's
`prompt3_transforms_A|B.level_7` asset (matched on `incorrect_sentence`, `stored_correction`) is
given to the model and replaces its correction. Payloads carry `prompt_version`; `_aligned` serves
only the current version, so v1 explanations are written again.

**Validation (`parse`)**: exactly one entry per sentence (re-ordered by `index` when valid);
non-empty explanation; English NL → explanation must be Latin-majority; caps 400/600/300 chars;
corrections dropped on correct sentences. Primary then fallback model; none usable → no row.

**Storage**: `exercise_explanations(exercise_id uuid FK exercises ON DELETE CASCADE,
nl_language_id smallint FK dim_languages, content_version int, payload jsonb, model text,
prompt_version smallint, created_at)`, PK `(exercise_id, nl_language_id)`, RLS on, service role
only. Payload `{"sentences":[{"text","is_correct","meaning","explanation","correction"}]}`; a row
is used only when `content_version` matches and its texts equal the item's sentences. Process LRU
(2,000) in front; a failed table read disables table use for 300 s (memory only).

**Serving.**
- `prefetch(db, items, …)` reads cached rows from ids alone (runs beside `store.hydrate`);
  `prepare_items(…, prefetched=…)` attaches `content.option_explanations`
  (`[{meaning, explanation, correction}]` aligned with `content.sentences`) and
  `content.explanation_language`, and starts background generation (4-worker `explain` pool,
  in-flight futures de-duplicated per key) for up to `EXERCISE_EXPLANATION_WARM_PER_REQUEST`
  items. Called from `_hydrate_items` and `intro_drill._block_exercises`.
- `GET /api/practice/explanations/<exercise_id>` (`@jwt_required`, 30/min + 600/day per user):
  `get_or_generate` → `{status:'success', state, exercise_id, option_explanations?,
  explanation_language?}`; `state` ∈ `ready` | `pending` (waited 25 s) | `unsupported` |
  `unavailable`. 400 on a non-UUID.

**Client** (`static/js/exercise-renderers.js` `renderSpotSentence`, `renderSemDiscrim` via
`explanationRequest`; `mcq` gained an `onAnswered` hook): uses attached
`option_explanations`, else `fetchExplanations(exercise_id)` at display (`window.authFetch`,
memoised per id, one retry after 2.5 s on `pending`). After the answer, each option button gets
`.has-expl` and a `.ex-opt-expl` line (verdict — "Error" / "Wrong" for pick items —, “meaning”,
why, "Correct form: …" on the wrong spot sentence; matched to options by text because pick items
are shuffled; styles in `static/css/redesign/session.css`). While waiting: `.ex-opt-expl-loading` only
(pick items also show their stored per-sentence notes, replaced on arrival). If the fetch brings
nothing, the item's own note is shown under the wrong sentence; the feedback bar carries the old
spot note only when explanations could not be asked for at all (no id / no `authFetch`). i18n keys `exercises.spot.*` in all four bundles.

## 3. Pre-written explanations in Storage (2026-11-27)

`services/explanation_files.py`: `file_path(lang, sense, nl, v)` →
`explanations/{lang}/{sense}.{nl}.p{v}.json`; `encode`/`decode` (format 1: `{format, language_id,
sense_id, nl_language_id, prompt_version, exercises: {exercise_id: {content_version, model,
payload}}}`); `write_file` (immutable: `'written'` or `'exists'`); `read_for_senses` (own
`explain-file` pool, 8 MB byte LRU, 600 s negative cache, deadline; never raises). The sweep
script lists only `{lang}/` folders and never touches `explanations/`.

Serving (`exercise_explanations`): memory → `stored_entries` → file entry (content_version and
`_aligned` must match) → table row → generate. `prefetch()` returns `Prefetched(files, rows)`,
reading files (8-worker pool, `EXERCISE_CONTENT_DEADLINE_S`, 3 s) and table concurrently beside
content hydration. `_job` re-reads the sense's file (10 s) before calling a model.

Batch writers (dry run unless `--apply`; run directories under the git-ignored
`data/exercise_explanations/`):
- `scripts/prewrite_explanations_anthropic_batch.py` — the owner's Anthropic key (`CLAUDE_API`,
  `https://api.anthropic.com` explicitly; every call in `~/.claude_api_ledger.jsonl`), Message
  Batches of 5,000: prepare (senses without a file; a sense with unreadable content held back;
  corrections in chunks of 100 senses) → submit (pending marker, no SDK retry, adoption on
  resume) → collect (one retry batch for failures; a sense written only when complete and
  current; parallel writes) → report.json. Answers are parsed with
  `explanations_anthropic.payload_from_message`, which takes the last valid JSON object (the
  model sometimes appends a corrected JSON).
- `scripts/prewrite_exercise_explanations.py` — the same over OpenRouter, synchronous, with a
  cost cap; sets `LLM_CALLS_DB_LOGGING=false` so 17k calls don't write ~24 MB of `llm_calls`.

State 2026-11-27: every ja spot/pick sense has a file (5,956; Sonnet 5.5; TASK-1244); zh has
none (TASK-1246). Cold file GETs from the US take ~1–1.8 s; with 6 readers a request over ~8+
distinct senses can pass the 3 s budget, and those items are then served by the job's re-read,
not a model ([[evaluations/explanation-storage-2026-11-27]] "Serving check").

## Configuration
`EXERCISE_EXPLANATIONS_ENABLED` (True), `EXERCISE_EXPLANATION_MODEL`
(`deepseek/deepseek-v4.1-flash`), `EXERCISE_EXPLANATION_FALLBACK_MODEL`
(`google/gemini-3.5-flash`), `EXERCISE_EXPLANATION_WARM_PER_REQUEST` (8).

## Key Architectural Decisions
1. **Decision:** rebuild definition options at serve time from gloss rows.
   - **Rationale:** content is immutable per version (ADR-049); the gloss rows already exist
     (98.6% of ja meanings have an English gloss); works for any future NL.
   - **Alternatives rejected:** regenerate the corpus (large, one NL only); drop the type for
     non-native learners (loses the L2 form-recognition family).
2. **Decision:** explanations cached per (exercise, NL), generated on first serve — ADR-064.

## Security Considerations
Explanations and options are rendered with `escHtml`. The endpoint is authenticated, UUID-checked
and rate-limited; it reads only active exercises. The table has RLS on with no client grant.
The model never sees user input (only stored sentences).

## Testing Strategy
`tests/test_definition_serving.py` (rebuild, POS/overlap/own-word exclusion, determinism, drops,
pool paging/caching, intro pool from cache, prestudy and practice wiring);
`tests/test_exercise_explanations.py` (prompt, validation, fallback model, attach/warm/stale
version/cap, memory-only without the table, in-flight de-duplication, pending/unsupported/
unavailable, route); `tests/unit/exercise-renderers.test.js` "renderSpotSentence explanations".
Live checks 2026-11-26: 251/251 ja and 106/160 zh sampled definition items rebuilt in English
(no key-term overlap); 人間 spot item explained end to end in 7.8 s, 0.6 s from memory.
