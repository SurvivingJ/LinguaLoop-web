# Recon: How Exercises Are Generated From Word Lists / Senses

Read-only recon, 2026-09-17. All claims carry `file:line`; anything not directly
read in the repo is flagged **UNVERIFIED**.

---

## 1. Entry points

There are **two separate content systems** that both start from vocabulary and
both call LLMs, plus a **third, human-in-the-loop system** that replaces the
LLM with Claude Code itself. They write to different tables.

| # | Entry point | file:line | Produces | Automated / manual |
|---|---|---|---|---|
| A | `VocabAssetPipeline.generate_for_sense` / `.generate_batch` | `services/vocabulary_ladder/asset_pipeline.py:58,85,451` | `word_assets` rows (P1/P2/P3/L4/L8/typed) | Automated, hosted LLM |
| B | `LadderExerciseRenderer.render_all` / `.build_rows` | `services/vocabulary_ladder/exercise_renderer.py:42,63` | `exercises` rows (ladder levels 1-9 + typed types) | Deterministic + per-render judges |
| C | `scripts/run_generation_batch.py` (CLI, TASK-515 runner) | `scripts/run_generation_batch.py:1-620` | Drives A then B over a chunk of senses, per language | Automated batch driver, resumable, cost-ceilinged |
| D | `scripts/run_content_build.py` | `services/vocabulary_ladder` + `test_generation` glue, uses `BatchModeThreadPoolExecutor` at `scripts/run_content_build.py:488` | Multi-stage nightly/on-demand content build (canary + ladder + test-gen phases) | Automated |
| E | `.claude/skills/batch-exercise-generation/SKILL.md` + `scripts/export_exercise_worklist.py` + `scripts/upload_exercises.py` | skill file (full text read) | Same `word_assets` → `exercises` chain as A/B, but **Claude Code writes the prompt answers in-session** instead of calling a hosted model | Manual (agentic), no LLM API spend |
| F | `.claude/skills/batch-sense-generation/SKILL.md` + `scripts/export_sense_seed_worklist.py` + `scripts/upload_senses.py` | skill file (full text read) | `dim_word_senses` two-level (`simple`/`standard`) definitions | Manual (agentic) |
| G | `services/vocabulary/sense_generator.py: SenseGenerator._call_llm` (`:277`), `.generate_sense` (`:658`), `.seed_words_batch` (`:726`) | — | `dim_word_senses` rows, called **inline during test generation** (vocabulary enrichment) | Automated, hosted LLM (`vocab_definition_generation` task) |
| H | `services/exercise_generation/orchestrator.py: ExerciseGenerationOrchestrator.run` (`:72`) | — | `exercises` rows for `grammar`/`collocation`/`conversation`/`style` source types only | **Frozen legacy path** — `source_type='vocabulary'` raises `_VOCAB_RETIRED_MSG` (`orchestrator.py:38-47,195-203,259-260`); no new vocab work lands here since TASK-512 |
| I | `services/test_generation/orchestrator.py` (84 KB, `run()`/`_run_impl` split, thread pools at `:1061`, `:1739`) | — | `tests` + `questions` rows (reading/listening comprehension), triggers G once per unresolved lemma | Automated, hosted LLM |
| J | `.claude/skills/cross-language-glosses/SKILL.md` | referenced from `services/vocabulary/gloss_generator.py:1-40` | `dim_word_senses` cross-language gloss rows | Manual (agentic) — **replaces a retired hosted path**, see §7 |
| K | `.claude/skills/test-sense-linking/SKILL.md` | — | Links a test transcript's vocabulary to `dim_word_senses` | Manual (agentic) |

**Practical reading:** for *vocabulary* content specifically, entry points A+B
(automated) and E (manual/Claude-authored) are the **only** live vocab-exercise
generators — H is explicitly retired for vocab. C and D are batch drivers over
A+B. G+I are a *different* content type (reading-comprehension tests, not
ladder exercises) that happens to also mint new `dim_word_senses` rows as a
side effect.

---

## 2. Pipeline stages, one word/sense, lemma → renderable exercise row

Concrete trace for the **ladder** path (A→B), which is the sole vocab-exercise
generator today (`services/exercise_generation/orchestrator.py:33-47`):

```
0. Lemma exists in dim_vocabulary (from VocabularyExtractionPipeline,
   services/vocabulary/pipeline.py:43 — lemmatize → phrase-detect (LLM,
   vocab_phrase_detection, only if nlp_meta.phrase_detection_enabled) →
   merge → filter → dedupe. Runs during test-transcript ingestion.)
        │
1. dim_word_senses row (definition) — via G (hosted, vocab_definition_generation)
   or F (Claude-authored, batch-sense-generation skill).
        │
2. fetch_corpus_sentences() — mine real transcript sentences that use THIS
   sense (asset_pipeline.py:668-700, tests.vocab_sense_ids GIN index). No LLM.
        │
3. Prompt 1 (CoreAssetGenerator.generate, asset_pipeline.py:136-138) — ONE
   hosted call, task vocab_prompt1_core (prompt1_core.py:28). Produces POS,
   semantic_class, definition, pronunciation, 10 sentences, primary_collocate,
   morphological_forms.
        │  ├─ structural validation (VocabAssetValidator.validate_prompt1)
        │  │    → on failure: ONE repair call (task vocab_prompt1_core_repair,
        │  │      prompt1_core.py:285) then re-validate; still-invalid → stored
        │  │      is_valid=false, pipeline stops for this sense.
        │  ├─ tier_gate_sentences() (asset_pipeline.py:503-579) — DETERMINISTIC
        │  │    frequency-table screen; misfits get a repair call
        │  │    (vocab_prompt1_core_sentence_repair, prompt1_core.py:365).
        │  ├─ judge_p1_sentences() (asset_pipeline.py:585-662) — LLM judge
        │  │    (judges/p1_sentences.py, task judge_ladder_p1_sentence),
        │  │    per-sentence accept/flag/reject, one repair pass, blocks the
        │  │    whole asset if < P1_MIN_ACCEPTABLE_SENTENCES survive.
        │  └─ collocate grounding (ground_core_asset, collocation_grounding.py)
        │       — DETERMINISTIC corpus-PMI check, tags but never blocks.
        │
4. Level planning — compute_active_levels / active_levels_for_context /
   prompt3_levels_for_context (config.py) — pure function of semantic_class +
   language + capability_context (morph_forms count, has primary_collocate,
   etc). Decides which of L1-L9 + typed types this sense can even attempt.
        │
5. Fan-out (ThreadPoolExecutor max_workers=12, asset_pipeline.py:311-346),
   TWO variants (A/B, different sentence assignments) x:
     - Prompt 2 (ExerciseAssetGenerator, task vocab_prompt2_exercises) — L1/L3/
       L5/L6 option content.
     - Prompt 3 (TransformAssetGenerator, task vocab_prompt3_transforms) — L7.
     - L4 (MorphologySlotGenerator, task ladder_l4_morphology_generation) —
       own model/retries since TASK-520.
     - L8 (CollocationRepairGenerator, task ladder_l8_collocation_repair_generation).
     - typed_llm.generate_all — synonym_antonym_match (ladder_syn_ant_generation),
       word_family (ladder_word_family_generation), particle_selection
       (ladder_particle_selection_generation, JA only).
   = up to 10 hosted calls in flight per sense, all through
   BatchModeThreadPoolExecutor (fail-closed judge contract carried across
   threads, judges/base.py:1-60).
        │
6. Validate + store each variant's asset into word_assets
   (_store_asset, asset_pipeline.py:939) — immutable, versioned by batch_id.
        │
7. LadderExerciseRenderer.build_rows (exercise_renderer.py:63) — reads the
   stored word_assets, RE-derives active_levels + per-type gates (so a stale
   asset never renders a level it shouldn't), then per level:
     - L1 phonetic: JA → deterministic phonetic-trie lookup
       (l1_lookup.py, phonetic_trie/), ZH/EN → LLM asset unchanged. Either
       source still passes through ladder_l1_distractor_judge
       (judges/l1_distractor.py) for synonymy/register, and JA gets a real
       Azure TTS audio clip (_generate_l1_audio, exercise_renderer.py:610).
     - L2 definition_match: 100% deterministic, same-tier sense lookup
       (deterministic/definition_match.py).
     - L3 cloze: LLM asset content, distractors routed through cloze_judge.
     - L4 morphology_slot: LLM asset, judged by sentence_validity.
     - L5 collocation_gap_fill: LLM asset, judged by collocation judge,
       already PMI-gated at generation time.
     - L6 semantic_discrimination: LLM asset, sentence_validity judge.
     - L7 spot_incorrect_sentence: LLM asset, sentence_validity judge.
     - L8 collocation_repair: LLM asset, collocation judge.
     - L9 jumbled_sentence: 100% deterministic (language chunkers:
       jieba/fugashi/spaCy).
     - typed types (synonym_antonym_match/word_family/particle_selection):
       relation / word_family / particle judges respectively.
     - Traditional-Chinese mirror (_render_hant_mirror, :1072) generated
       deterministically for every ZH row.
        │
8. exercises.insert(rows) (exercise_renderer.py:56) — final renderable rows,
   ~2 per active level (variant A+B) plus dedupe on context-free types
   (uq_exercises_context_free_variant).
```

Everything from step 3 onward runs **once per sense**, not once per exercise —
the 8-14 hosted calls above are the entire generation cost for that sense's
whole ladder (confirms the "$0.024/sense, ~5.5 min/sense, well over a dozen
LLM calls" figure in §5).

---

## 3. Exercise / test-type taxonomy

### 3a. Vocabulary ladder (`exercises` table, `source_type='vocabulary'`)

Level map is the literal source of truth: `services/vocabulary_ladder/config.py:32-48` and the capability matrix at `config.py:476-508`.

| Level | `exercise_type` | Asks the learner | Answer format | Generator | Judge |
|---|---|---|---|---|---|
| L1 | `phonetic_recognition` | Pick the word you heard (audio-confusable distractors) | MC, audio | LLM (ZH/EN) or deterministic phonetic-trie (JA) | `l1_distractor` |
| L2 | `definition_match` | Match word to its definition | MC | deterministic (same-tier sense) | none |
| L3 | `cloze_completion` | Fill the blank in a sentence | MC | LLM | `cloze` |
| L4 | `morphology_slot` | Choose the correct inflected/derived form | MC | LLM (own prompt since TASK-520) | `sentence_validity` |
| L5 | `collocation_gap_fill` | Fill the blank with the word that collocates | MC | LLM, gated on corpus-PMI fixed collocation | `collocation` |
| L6 | `semantic_discrimination` | Pick which sentence uses the word correctly | MC (3 wrong + 1 right) | LLM | `sentence_validity` |
| L7 | `spot_incorrect_sentence` | Identify + correct the wrong word usage | MC + correction text | LLM | `sentence_validity` |
| L8 | `collocation_repair` | Fix a broken collocation | MC | LLM (own prompt since TASK-520) | `collocation` |
| L9 | `jumbled_sentence` | Reorder scrambled words into the sentence | Ordering | deterministic (language chunkers) | none |
| typed | `synonym_antonym_match` | Match synonym/antonym | MC | LLM | `relation` |
| typed | `word_family` | Pick the correct derived form (noun/verb/adj) | MC | LLM | `word_family` |
| typed | `particle_selection` (JA only) | Choose the correct particle | MC | LLM | `particle` |
| ZH-only | `classifier_match`, `counter_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`, `tone_id_word` | pinyin/measure-word drills | MC | deterministic (`deterministic/` package) | none |
| JA-only | `kanji_to_reading`, `reading_to_kanji`, `cloze_typed` | reading/typed drills | MC / typed | deterministic | none |

Column source: `exercises` row shape read directly from
`exercise_renderer.py:237-249` — `id, language_id, exercise_type, source_type,
content (jsonb), tags (jsonb), complexity_tier, is_active, word_sense_id,
word_asset_id, ladder_level`.

### 3b. Legacy/frozen non-vocab exercise types (`exercises`, still served, no new generation)

From `services/exercise_generation/orchestrator.py:211-257`: `cloze_completion`,
`jumbled_sentence`, `tl_nl_translation`, `nl_tl_translation`, `text_flashcard`,
`listening_flashcard`, `semantic_discrimination`, `spot_incorrect_sentence`,
`odd_one_out`, `context_spectrum`, `timed_speed_round`, `collocation_gap_fill`,
`collocation_repair`, `odd_collocation_out`, `verb_noun_match`,
`style_sentence_completion`, `style_pattern_match`, `style_voice_transform`,
`style_transition_fill`, `style_imitation`. These share type *names* with
ladder types but are a different `source_type` and generator family, frozen
since TASK-512.

### 3c. Reading/listening comprehension (`tests` + `questions` tables)

Confirmed via `services/test_generation/database_client.py` (`.table('tests')`
:344, `.table('questions')` :847, `.table('dim_question_types')` :570).
Question types observed live in the cost table (§5):
`question_literal_detail`, `question_inference`, `question_main_idea`,
`question_author_purpose`, `question_supporting_detail`,
`question_vocabulary_context` — all MC, answer format and options embedded per
question row, `question_type_id` FK to `dim_question_types`. ZH tests
additionally carry a pinyin payload (`orchestrator.py:832`). Audio synthesis
(Azure TTS) + R2 upload for `listening` type tests.

---

## 4. LLM call graph — prompt template / model / batching

All model resolution for the ladder goes through
`services/prompt_service.get_template_config(db, task_name, language_id)` —
**no hardcoded model slugs** in any `asset_generators/*.py` file (verified by
grep: every generator reads `cfg['model']` from a `get_template_config` call).

| Stage | `prompt_templates.task_name` | Model (as measured live, §5) | Batching | Sync/async |
|---|---|---|---|---|
| P1 core | `vocab_prompt1_core` | not measured in the sampled run | 1 call/sense | sync HTTP, called from worker thread |
| P1 repair | `vocab_prompt1_core_repair` | same as P1 | 0-1 call/sense | sync |
| P1 sentence repair | `vocab_prompt1_core_sentence_repair` | same as P1 | 0-N calls/sense (per off-tier sentence) | sync |
| P1 sentence judge | `judge_ladder_p1_sentence` (verdict logging), billed under its own task | — | 1 call/sense (all 10 sentences at once) | sync |
| P2 exercises | `vocab_prompt2_exercises` | — | 1 call/variant (2/sense) | sync, in thread pool |
| P3 transforms | `vocab_prompt3_transforms` | — | 1 call/variant (2/sense) | sync, in thread pool |
| P3 salvage | `vocab_prompt3_transforms_salvage` | — | 0-1/variant | sync |
| L4 morphology | `ladder_l4_morphology_generation` | own model, split out in TASK-520 specifically so a bad model choice doesn't retry L7 too | 1/variant | sync, in thread pool |
| L8 collocation repair | `ladder_l8_collocation_repair_generation` | own model | 1/variant | sync, in thread pool |
| synonym/antonym | `ladder_syn_ant_generation` | — | 1/variant | sync, in thread pool |
| word family | `ladder_word_family_generation` | — | 1/variant | sync, in thread pool |
| particle selection (JA) | `ladder_particle_selection_generation` | — | 1/variant | sync, in thread pool |
| Vocab phrase detection | `vocab_phrase_detection` | — | 1 call/text during ingestion | sync |
| Sense definitions (automated) | `vocab_definition_generation` | **`deepseek/deepseek-v4-flash`** (measured, §5) | 1 call/lemma (`prefer_existing=True` reuses across tests) | sync |
| Test-gen questions | `question_literal_detail`/`question_inference`/etc | **`google/gemini-3.5-flash-lite`** (measured, §5 — "every model in this run was gemini-3.5-flash-lite except vocab senses") | 1/question, thread-pooled (`BatchModeThreadPoolExecutor`, `test_generation/orchestrator.py:1061,1739`) | sync, threaded |
| Test-gen judges | `judge_distractor_plausibility`, `judge_answer_entailment` | gemini-3.5-flash-lite (measured run) | 1/question judged | sync, threaded |
| Test-gen prose/title | `prose_generation`, `title_generation` | gemini-3.5-flash-lite | 1/test | sync |

Non-DB / hardcoded models: **none found** in the current ladder or test-gen
generators — this is a deliberate, commented design choice (`orchestrator.py`
docstring: "No 'en' literal here by design (TASK-519)... that literal is how
the v1 corpus became English-only"). A **prior** incident is on record where
OpenRouter delisted a model slug and zh silently rotted onto a different one
(`prompt-template-model-slug-rot` memory note) — the DB-driven design doesn't
prevent slug rot, it just centralizes where it's fixed.

Batching envelope: a separate "batch prompting" mechanism exists
(`services/batch_prompting.py`, memory: "N rows per call, position keys not
vocab_ids") but per the memory note **only sense-gen is wired to it** — the
ladder P1/P2/P3 calls above are one-call-per-item, not N-per-call.

---

## 5. Cost + latency — verified numbers

### Test generation (fully re-verified against `wiki/evaluations/test-gen-20-run-2026-08-21.md`)

- **$0.00875/test, 176.6 s/test mean (2.9 min), 118 s median**, from a live
  20-test EN run (`wiki/evaluations/test-gen-20-run-2026-08-21.md:14,33,87`).
- Stage wall-clock share: **vocabulary enrichment 82.1%** (145.0 s/test mean),
  questions+judges 10.7%, audio (TTS+upload) 5.3%, setup/prose/title 1.6%
  (`test-gen-20-run-2026-08-21.md:90-95`).
- Stage cost share: judges **38.2%** of spend ($0.00446/judged test), vocab
  enrichment **16.2%** of spend despite 82% of wall clock — i.e. vocab
  enrichment is *slow* (network round trips / cold corpus lookups) not
  *expensive* (`test-gen-20-run-2026-08-21.md:52-56,92`).
- Difficulty scales latency hard: d1 mean 49 s vs d9 mean 358 s (7.3x) because
  longer passages need more unique-lemma sense lookups
  (`test-gen-20-run-2026-08-21.md:97-104`).
- Extrapolation given in-doc: 1,000 tests ≈ $8.75 / ~49 h, **sequential, one
  process one language at a time** (`test-gen-20-run-2026-08-21.md:112-123`).

### Vocabulary ladder generation (TASK-515, `wiki/tasklist/archive/exercise-generation-v2.tasks.md:790-812`)

- Measured from only **7 ZH senses** (small sample, explicitly flagged as such
  in-doc: "7 senses is far too small a sample to judge [the 90% valid-rate
  bar]"): **$0.1645 / 65 calls → ~$0.024/sense**, **~5.5 min/sense**.
- Extrapolated in the same doc: ~$2.40 + ~9h per 100-sense chunk,
  ~$7.20 + ~27h for all three languages at 1,000 senses/language.
- **A newer, larger estimate lives in the current runner's own docstring**
  (`scripts/run_generation_batch.py:390-401`): "a sense needs well over a
  dozen LLM calls plus judges and measures ~5.5 minutes... the 9,075-sense
  pool is ~35 days run serially and ~9 [days] at `--workers 4`, for the same
  **$305**" → implies ~$0.0336/sense at that larger, more-current scope
  (9,075 senses is bigger than the 1,000/language original target, so this
  figure supersedes the $0.024 one but the two are not directly comparable —
  different sample sizes, possibly different mix of already-mined vs
  fully-generated sentences).
- **Status: TASK-515 (the "batch run — top 1,000 senses × EN/ZH/JA" task) is
  marked `[~]` (in progress / partial) in `wiki/tasklist/master.md:570`**, not
  done. The skill's own "size the job" query (`.claude/skills/batch-exercise-
  generation/SKILL.md:63-65`) states, as of 2026-09-04: **en 10,578 · zh 8,031
  · ja 7,118 = 25,727 senses with no exercises, against only 57 senses that
  have assets at all.** The automated batch path has not materially chewed
  through the backlog; bulk fill today happens through skill E
  (Claude-authored, no LLM API cost, but bounded by session/attention time
  rather than wall clock).

### Sense generation via the batch-sense-generation skill (F)

No hosted LLM cost (Claude writes definitions in-session). Embedding backfill
is measured at "~$0.02 per million tokens"
(`.claude/skills/batch-sense-generation/SKILL.md:150`).

### Not found / UNVERIFIED

- No per-stage cost/latency breakdown specific to L1-L9 individually (only
  whole-sense P1/P2/P3/L4/L8/typed aggregate numbers exist).
- No measured number for the legacy (frozen) grammar/collocation/conversation/
  style pipeline (`orchestrator.py`, entry point H) — it predates the
  measurement harness and is frozen, so this is plausibly permanently
  unmeasured.
- Azure TTS / R2 cost: explicitly flagged in the eval doc as **not included**
  in the `llm_calls` cost table ("Azure Speech TTS and R2 storage... are a
  separate bill", `test-gen-20-run-2026-08-21.md:80-83`).

---

## 6. Concurrency

**Within one sense (ladder):** `BatchModeThreadPoolExecutor(max_workers=12)`
fans P2 + P3 + (0-2 split levels) + typed, x2 variants = up to 10 futures,
`asset_pipeline.py:311-346`. This is genuine IO-bound concurrency (each future
is "independently CPU/IO light on this thread, the wait is all downstream LLM
latency" — comment at `asset_pipeline.py:308-310`).

**Across senses (ladder batch):** `scripts/run_generation_batch.py:run_chunk`
(`:379-492`) puts `--workers N` senses in flight via a second
`ThreadPoolExecutor`. Default `workers=1` (fully serial). The docstring is
explicit about the multiplier and the external rate-limit risk:

> "Each sense already fans its P2/P3/split/typed generators across an 8-wide
> pool of its own, so `workers=N` means up to N x 8 concurrent provider calls.
> Check that against the OpenRouter rate limit before raising it; 4 is 32."
> — `run_generation_batch.py:398-401`

**Across languages:** `main()` iterates `for language_id in languages:` and
calls `run_language` synchronously per language even under `--all-languages`
(`run_generation_batch.py:601-604`) — **languages are never generated in
parallel** by this script. An earlier finding (`exercise-generation-v2.tasks.md:800-805`)
explains why this was made a hard rule: `spend_since()` sums *all* `llm_calls`
rows since the chunk began, so "three concurrent runs trip each other's
ceilings on each other's spend" if run in parallel.

**Cross-process safety:** a Postgres advisory lock RPC,
`pg_try_advisory_lock_for_queue_drain` (`services/vocabulary_ladder/queue_drain.py:315`),
serializes the queue-drain coverage-gap step so two batch runs (or a batch run
and a cron) can't double-enqueue.

**Test generation:** same pattern — `BatchModeThreadPoolExecutor` at
`services/test_generation/orchestrator.py:1061` and `:1739` fans out
per-question generation within one test; the eval doc's extrapolation
explicitly calls the overall run "sequential — one process, one language at a
time" (`test-gen-20-run-2026-08-21.md:123`).

**Serialization points, summarized:**
1. Budget ceiling check reads *global* `llm_calls.cost_usd` since a start
   timestamp → cross-run/cross-language parallelism corrupts the ceiling.
2. `run_generation_batch.py` and `run_test_generation_cli.py` are both plain
   sequential-language CLI loops.
3. OpenRouter's own rate limit (not quoted numerically anywhere in-repo —
   **UNVERIFIED** exact QPS/RPM) is the reason `--workers` is capped low in
   practice.
4. `LadderExerciseRenderer` keeps per-thread state (`last_skips` via
   `threading.local()`, `run_generation_batch.py:426-431`) specifically so
   `--workers>1` doesn't race two senses' deterministic-skip tallies.

---

## 7. Failure modes / fail-closed behaviour

Two different contracts, deliberately switched by call site
(`services/exercise_generation/judges/base.py:1-60`, read in full):

- **Serve-time (a learner mid-session):** fail-**open**. Any judge error
  (missing template, LLM failure, malformed response) returns `safe_accept()`
  — "act as if the judge wasn't there." A dead judge must never break a live
  session.
- **Batch-generation time:** fail-**closed**, via a thread-local `batch_mode()`
  flag. A judge that can't resolve its template/model raises
  `JudgeUnavailable`, which propagates up through `as_completed()` and aborts
  the *whole batch* rather than shipping unjudged content
  (`asset_pipeline.py:353-358`, `353: except JudgeUnavailable: raise`).
  `BatchModeThreadPoolExecutor` exists specifically to carry that flag across
  the thread-pool boundary — a bare `ThreadPoolExecutor` would silently fall
  back to fail-open on worker threads (documented as "the original TASK-510
  bug wearing a different hat," `judges/base.py:49-52`).

**Verdict bands** (same file): confidence `<0.6` → reject (sync block),
`0.6-0.8` → flag (persisted, kept, enqueued for review), `≥0.8` → accept.

**What gets thrown away, with numbers:**
- Test-gen 20-run: **17 validator rejections vs 2 judge rejections** — "the
  validator, not the judges, is what rejects questions here"
  (`test-gen-20-run-2026-08-21.md:145`). 6 question slots lost to
  `Exhausted N attempts` retries; 5/94 saved questions (5.3%) flagged for
  review, not rejected (`:132-136`).
- Distractor-plausibility judge reject rate: **~0.9% production-weighted**
  (`wiki/evaluations/distractor-gold-frame-2026-08-19.md`, cross-referenced at
  `test-gen-20-run-2026-08-21.md:142-143`) — zero rejects in the 81-call
  sampled run is consistent with that base rate, not evidence the judge is
  inert.
- Ladder P1 sentence judge on the 7-sense sample: **33% reject**
  (`exercise-generation-v2.tasks.md:797`) — flagged in-doc as too small a
  sample to trust.
- **`_MIN_VALID_RATE = 0.90`** (`run_generation_batch.py:71`) — a chunk whose
  valid-rate falls below 90% (once ≥20 senses attempted) **stops the whole
  run** rather than continuing to generate low-quality content
  (`run_generation_batch.py:524-529`).
- Failed senses are queued as `generation_queue(reason='regen')` rather than
  retried inline (`run_generation_batch.py` module docstring, "Resumability").
- Repairs are capped at exactly one attempt per failure class (P1 structural
  repair, tier-gate repair, judge-reject repair) — a still-failing asset after
  that one repair is stored `is_valid=false` and generation stops for that
  sense (`asset_pipeline.py:144-162`).
- `_existing_cap_counts` in the legacy orchestrator is explicitly documented
  as **fail-open**: a DB lookup failure lets a batch insert uncapped rather
  than dropping work, relying on a partial unique index as the real backstop
  (`services/exercise_generation/orchestrator.py:286-313`).

---

## 8. Determinism — what needs an LLM vs what's already computed from data

| Deterministic today (no LLM) | file | Still LLM-dependent today |
|---|---|---|
| ZH pinyin + tone sandhi | `services/pinyin_service.py`, `scripts/backfill_pronunciations.py:9-11,90` (pypinyin + jieba) | ZH L1 phonetic distractor generation/verification (no ZH phonetic trie yet) |
| JA kana reading | `scripts/backfill_pronunciations.py:15,130,186-187` (fugashi + unidic-lite) | EN L1 phonetic distractor generation/verification (no ARPAbet/cmudict integration found anywhere in the repo — **UNVERIFIED / not yet built**, matches memory note "en ARPAbet, en lowest priority") |
| JA furigana ruby annotation | `services/furigana_service.py:1-30` (fugashi + jaconv) | P1 core classification (POS, semantic_class, definition, 10 example sentences, primary_collocate, morphological_forms) — inherently generative, no deterministic substitute claimed anywhere |
| JA pitch accent | `services/pitch_accent_service.py:1-40` (pyopenjtalk) | L3 cloze, L4 morphology, L5/L8 collocation, L6 semantic discrimination, L7 spot-incorrect — all still full LLM generation + judge |
| JA L1 phonetic distractors | `services/vocabulary_ladder/l1_lookup.py` + `phonetic_trie/ja_mora.py`,`trie.py` — build-once mora trie, registered per-language in `_TRIE_REGISTRY` (`l1_lookup.py:42-45`, currently only `language_id: 3`) | typed types: synonym_antonym_match (needs `sense_embedding` capability — embeddings ARE precomputed via pgvector, but the *match selection/explanation* is still an LLM call), word_family, particle_selection |
| L2 definition_match | `deterministic/definition_match.py` — same-tier sense lookup | Sense definitions when no existing sense/manual entry exists (inherently generative) |
| L9 jumbled_sentence | `deterministic/jumbled.py` — language chunkers (jieba/fugashi/spaCy) | Cross-language glosses were an LLM path but are **now retired** in favor of Claude-in-session (`services/vocabulary/gloss_generator.py:1-40`) — i.e. moved from "automated LLM" to "manual LLM", not to "deterministic" |
| ZH classifier_match, counter_match, hanzi_to_pinyin, pinyin_to_hanzi, tone_id_word | `deterministic/` package (classifier_match.py, counter_match.py, tone.py, readings.py) | Collocate grounding is deterministic (corpus PMI) but the *primary_collocate assertion itself* still comes from the P1 LLM call — grounding only grades it after the fact |
| Sentence-tier hard gate | `services/vocabulary_ladder/tier_gate.py` (frequency table) — runs *before* the LLM judge specifically to save judge spend on sentences a deterministic check would already reject (`asset_pipeline.py:170-175`) | Phrase detection (`vocab_phrase_detection` task) during vocabulary extraction — LLM, though only when `nlp_meta.phrase_detection_enabled` for the language |
| Traditional-Chinese script mirror | `exercise_renderer.py:1065-1085`, `script_converter.py` | P1 sentence judge and all downstream per-level judges (cloze, collocation, sentence_validity, particle, relation, l1_distractor) are LLM calls by construction — a judge is defined as "a second model's opinion," so none of these have a deterministic substitute in scope |
| Azure TTS audio synthesis | not an LLM (neural TTS API), deterministic given the text | — |

**Architectural note (from `.claude/reviews/l1-phonetic-trie-architecture.md`,
referenced but not fully read — cited via `l1_lookup.py:5-9`):** the stated
roadmap is ZH phonetic trie next, EN lowest priority, because "zh is
best-resourced [and] ja is the actual defect" per the project's own prior
review (also corroborated by the MEMORY.md note
`l1-phonetic-trie-architecture.md`). This recon did not re-read that review
file directly — flagging as **secondary source, not independently verified**.

---

## Answers not fully found (explicitly flagged rather than guessed)

- Exact OpenRouter rate limit numbers (QPS/RPM) that bound `--workers` — not
  quoted anywhere in the repo, only referenced qualitatively.
- A verified, non-stale count of exercises rendered to date broken out by
  ladder level (L1...L9) — only the aggregate "57 senses have assets at all"
  and per-language "no_exercises" counts were found (skill SKILL.md:63-65,
  2026-09-04 snapshot).
- Per-stage $ and time cost for the *ladder* pipeline (analogous to the
  test-gen per-stage table in §5) — the TASK-515 note gives one aggregate
  $/sense and min/sense figure from a 7-sense sample, not a stage breakdown.
- Confirmation of the ZH-phonetic-trie / EN-ARPAbet roadmap timeline —
  referenced only secondhand via a doc this recon didn't open.
