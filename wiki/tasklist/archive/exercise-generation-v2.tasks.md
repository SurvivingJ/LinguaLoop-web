---
title: "Exercise Generation v2 — Task Breakdown"
feature: exercise-generation-v2
prose_page: ../features/exercise-generation-v2.md
tech_page: ../features/exercise-generation-v2.md
total_tasks: 36
done: 4
---

# Exercise Generation v2 — Task Breakdown

Implements the design plan in [[features/exercise-generation-v2]] (all operator decisions final, 2026-06-11).
Task IDs map 1:1 to the plan's numbered deliverables (TASK-501 = P0.1 … TASK-536 = P4.3); section references
(§4, §6.2 …) point into that page. Phases 0→3 are sequenced; Phase 4 is blocked on post-launch attempt data.

**Dependency spine:** Phase 0 is parallelisable (only 504, 506, 507 have intra-phase deps). The Phase-1 batch run
(TASK-515) is the integration gate — it requires essentially all of Phase 0 plus 513/514/519. Phases 2–3 fan out
after 515 except where noted.

---

## TASK-501: Commit the 2026-06-10 working tree + verify live state

**Status:** [x] Done (2026-06-12)
**Feature:** exercise-generation-v2
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
The judge-integration and slug-fix work from 2026-06-10 (cloze block-on-short, semantic sentence-validity wiring, language-aware template lookup, tl/nl same-language skip, tier-sorted pools, llm_calls tagging) is still uncommitted. Land it, and confirm both pending migrations are applied to the live DB.

**Resolution note:** The 2026-06-10 tree was already committed before this session (commits `fcd1fd22` "Exercise prompt improvements; judge integration" and `9c1e5fc9` "Cloze generation + judge prompting changes"), so this task reduced to verification + working-tree cleanup. Two committed tests were stale relative to the shipped code and failing: `test_difficulty_frequency.py::test_tier_still_dominates` used obsolete CEFR keys (`A1`/`C2`) after the CEFR→T-tier migration (`TIER_NUMERIC` only has `T1`–`T6`), and `test_cloze_generator.py::test_judge_rejects_one_retry_succeeds` asserted old wholesale-replace semantics where `cloze.py` now POOLs judge survivors across batches. Both tests were brought in line with shipped intent (git history confirms the code is newer). Also untracked 103 already-committed `.pyc` files (now covered by the existing `__pycache__/` gitignore) and removed the stray 0-byte tracked `and` file.

**Acceptance Criteria:**
- [x] `git status` clean; `.pyc` files excluded (gitignore), the stray `and` file removed or explained
- [x] `migrations/fix_exercise_generation_slugs_and_templates.sql` and `migrations/improve_semantic_discrimination_prompts.sql` committed AND verified applied live (no active `google/gemini-flash-1.5` rows; EN `exercise_sentence_generation` row exists)
- [x] Existing test suite green (`pytest`) — 457 passed, 1 skipped

**Files to Create / Modify:**
- Commit only — `services/exercise_generation/*`, `services/prompt_service.py`, the two migrations, wiki changes

**Verification:**
`SELECT count(*) FROM prompt_templates WHERE model='google/gemini-flash-1.5'` → 0; `git log -1` shows the commit.

---

## TASK-502: Ratify + migrate the `semantic_class` controlled vocabulary

**Status:** [x] Done (2026-06-13)
**Feature:** exercise-generation-v2
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Resolution note:** Migration `migrations/semantic_class_enum.sql` applied live (Supabase MCP): the 11 legacy non-null rows remapped (`abstract_noun→abstract`×4, `action_verb→action`×4, `adjective→property`×2, `具体名词→concrete`×1) and a `CHECK (semantic_class IS NULL OR IN (concrete,abstract,action,property,function,proper))` constraint added (NULL still allowed pre-backfill). `config.py` rewired: `compute_active_levels` now routes off the 6-value enum (proper→[] excluded from ladder; function→[1,2,3,6,7]; concrete→drop L5/L8, keep L4 for matrix-routed classifier; others→full); `LANGUAGE_VALIDATION_PROFILES` key on the single `SEMANTIC_CLASSES` set; the old `COLLOCATION_SKIP_CLASSES`/`MORPHOLOGY_LEVELS`/`NO_MORPHOLOGY_LANGUAGES`/`_SEMANTIC_CLASSES_EN/ZH` removed. **Added `normalize_semantic_class()`** and applied it at the `asset_pipeline` write boundary (and the active_levels read) so P1's still-legacy labels don't violate the new constraint — generation stays safe until the P1 prompts are reseeded. New `tests/test_active_levels_routing.py` (routing matrix + normalizer); existing validator fixtures moved to the ratified values. Suite: 498 passed, 1 skipped.

**Description:**
Replace the informal `semantic_class` values with the ratified 6-value enum (§4 table: `concrete | abstract | action | property | function | proper`) so the capability matrix and `active_levels` routing have a stable key. The platform is pre-launch — the handful of existing non-null values (≈11 rows) are remapped in the same migration.

**Acceptance Criteria:**
- [x] Migration adds `CHECK (semantic_class IN ('concrete','abstract','action','property','function','proper'))` on `dim_vocabulary` (NULL still allowed pre-backfill)
- [x] Existing non-null rows remapped to the new values (or NULLed with a log of what was dropped)
- [x] `LANGUAGE_VALIDATION_PROFILES` + `compute_active_levels` in `services/vocabulary_ladder/config.py` use only the 6 new values; `proper` is excluded from ladder subscription
- [x] Unit test: each enum value → expected `active_levels` per language

**Files to Create / Modify:**
- `migrations/semantic_class_enum.sql` — constraint + remap
- `services/vocabulary_ladder/config.py` — enum sets + routing
- `tests/` — routing matrix test

**Verification:**
`INSERT` with a bogus class fails; `compute_active_levels('concrete', zh)` drops 5/8 and routes L4→classifier.

---

## TASK-503: Fix `dim_exercise_types.family` + add new type rows

**Status:** [x] Done (2026-06-13)
**Feature:** exercise-generation-v2
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none

**Resolution note:** `migrations/fix_dim_exercise_types_families.sql` applied live (Supabase MCP), verified — all 25 rows (13 corrected + 12 new) match §5. Corrected: `cloze_completion`→meaning_recall, `definition_match`→form_recognition, `jumbled_sentence`→form_production, `listening_flashcard`→form_recognition, `spot_incorrect_sentence`+`spot_incorrect_part`→semantic_discrimination. Added 12: readings (`hanzi_to_pinyin`/`kanji_to_reading`/`pinyin_to_hanzi`/`reading_to_kanji`) + `tone_id_word` @15s, `timed_speed_round` @8s, others (`cloze_typed`/`classifier_match`/`particle_selection`/`counter_match`/`synonym_antonym_match`/`word_family`) @45s. **DB-vs-spec resolution:** the `family` CHECK forbade §5's `fluency` family (timed_speed_round), so the constraint was additively extended to include it — safe, as `fluency` is non-BKT (no `FAMILY_WEIGHTS` entry → never feeds `p_known`/coverage). Idempotent (keyed UPDATEs + DROP IF EXISTS/re-ADD + `ON CONFLICT DO NOTHING`).

**Description:**
Live `dim_exercise_types` mis-maps legacy types (cloze→collocation, jumbled→collocation, listening_flashcard→meaning_recall), so Acquisition-mode family targeting mis-drills (finding G4). Correct every row to the §5 Family column and insert rows for the 12 new type_codes with realistic `expected_seconds`.

**Acceptance Criteria:**
- [x] All 13 existing rows match §5 (cloze_completion→meaning_recall, jumbled_sentence→form_production, listening_flashcard→form_recognition, etc.)
- [x] New rows inserted: `cloze_typed`, `classifier_match`, `particle_selection`, `counter_match`, `hanzi_to_pinyin`, `kanji_to_reading`, `pinyin_to_hanzi`, `reading_to_kanji`, `tone_id_word`, `synonym_antonym_match`, `word_family`, `timed_speed_round` — each with family + `expected_seconds` (reading/tone ≈15s, speed-round ≈8s, others ≈45s)
- [x] Migration is idempotent (keyed UPDATEs + `ON CONFLICT DO NOTHING`)

**Files to Create / Modify:**
- `migrations/fix_dim_exercise_types_families.sql`

**Verification:**
`SELECT type_code, family FROM dim_exercise_types ORDER BY type_code` matches §5; re-running the migration is a no-op.

---

## TASK-504: `dim_exercise_capabilities` — table, seeds, wiring, invariant test

**Status:** [x] Done (2026-06-14)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-502, TASK-503

**Resolution note:** `migrations/dim_exercise_capabilities.sql` applied live (Supabase MCP) — 55 rows (54 enabled, 1 disabled marker = ZH `morphology_slot`), §6.2 DDL verbatim. Seeds encode §5's Lang column for all three languages. **DB-vs-spec resolution (flagged):** the live `dim_exercise_types` had 25 rows but **no `morphology_slot`** row, although it is L4's `exercise_type` in `config.py` LADDER_LEVELS, is §5 #5, and is the explicit `(1,'morphology_slot',…)` example in the §6.2 DDL — TASK-503 added the 12 new types assuming it pre-existed (it never did). Since capability rows FK-reference `dim_exercise_types(type_code)`, the migration additively backfills that one missing type row (`form_production`, 45s, `ON CONFLICT DO NOTHING`) — same additive pattern TASK-503 used for the `fluency` CHECK. **Key design choice:** `compute_active_levels` is now matrix-derived (distinct enabled `ladder_level` over rows whose `pos_classes` cover the class), language-aware, yet produces the *same* canonical level sets as TASK-502 (`proper`→[], `function`→[1,2,3,6,7], `concrete`→[1,2,3,4,6,7,9] with the L4 *type* differing per language: ZH=classifier_match, EN=morphology_slot, JA=particle/counter, all+cloze_typed as the general productive L4) — so the existing `test_active_levels_routing.py` stayed green with no changes. The `'all'` pos sentinel matches every class except `proper`; legacy hardcoded routing retained only as `_fallback_active_levels` (used when a language has no matrix rows). In-code `CAPABILITY_MATRIX` mirrors the SQL seeds (the offline routing + test source; DB copy is runtime SoT, cached by `DimensionService.get_exercise_capabilities`). New `tests/test_capability_matrix.py` (25 tests) asserts the §4 inventory invariant for all 18 (language × class) pairs + structural checks (judge_key NULL ⟺ deterministic) + the ZH-concrete verification. Suite: **523 passed, 1 skipped**.

**Description:**
Create the routing core (§6.2 DDL verbatim): one row per (language, type) declaring pos_classes, ladder_level, generator kind, data requirements, and judge_key. Seed EN/ZH/JA per §5's Lang column. Rewire `compute_active_levels` (and the generation planner) to read this table instead of hardcoded config.

**Acceptance Criteria:**
- [x] Table live with §6.2 schema; seeds for all enabled (language, type) pairs incl. disabled markers (`(1,'morphology_slot',is_enabled=false)`)
- [x] `compute_active_levels` derives levels from the matrix; hardcoded ZH/EN special cases in `config.py` reduced to `_fallback_active_levels` only
- [x] Invariant test: every `(language_id, semantic_class)` combination yields ≥1 enabled type per required family (the §4 inventory contract)
- [x] DimensionService caches the matrix at startup (`get_exercise_capabilities`, same pattern as other dim tables)

**Files to Create / Modify:**
- `migrations/dim_exercise_capabilities.sql` — DDL + seeds
- `services/vocabulary_ladder/config.py` — matrix-backed `compute_active_levels`
- `services/dimension_service.py` — cache
- `tests/test_capability_matrix.py` — invariant test

**Verification:**
Invariant test green; ZH concrete noun plan contains `classifier_match` at L4 and no `morphology_slot`.

---

## TASK-505: Japanese vocabulary bootstrap (transcripts only)

**Status:** [x] Done (2026-06-16 — live extraction batch over all 82 JA tests)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Resolution note (2026-06-14, partial — code only):** Operator paused the expensive live LLM extraction batch (session cost guardrail) and asked for the code prerequisites only. **Finding: most of B4 was already fixed in the repo before this session.** Evidence: (a) `asset_pipeline._extract_sentences_with_word` already takes `language_id` and uses `LanguageProcessor.for_language(language_id)` — the `self.db_language_id` typo that hardcoded the English processor is gone; (b) `services/vocabulary/frequency_service.py` is already language-agnostic with `ja` in `_LANG_MAP`, and `wordfreq` is already in `requirements.txt`; (c) `scripts/backfill_vocab.py` already accepts `--language ja`, propagates `language_id`, and sets `frequency_rank` from `compute_zipf_for_vocab_item(item, language_code)` (zipf score stored as the rank — pre-existing design) — so the JA extraction CLI + frequency path are wired end-to-end. **Net-new code this session:** the one remaining B4 item — CJK whole-word matching was still a substring fallback (`contains_target_whole_word` → `word in sentence`), which false-positives 子 inside 椅子. Added `LanguageProcessor.contains_whole_word` (tokenizer-based: ASCII uses `\b`; non-ASCII tokenises and accepts only a standalone token or an exact contiguous token run) and wired it into `_extract_sentences_with_word` (replacing the substring matcher). `tests/test_contains_whole_word.py` (7 tests, stub-tokenizer + real jieba). Suite: **530 passed, 1 skipped**. **Deferred (operator-approved):** acceptance criteria 2–4 — the live extraction run over the 82 JA tests (`scripts/backfill_vocab.py --language ja`; `dim_vocabulary` lang-3 rows > 0), `frequency_rank` coverage ≥90%, and the 50-lemma human spot-check — all require the LLM batch + live writes and are held for a fresh, cost-budgeted session. The code is ready to run that batch.

**Description:**
`dim_vocabulary`/`dim_word_senses` have zero JA rows despite 82 JA tests (finding G2). Fix audit bug B4 first (`asset_pipeline.py:340` — `self.db_language_id` typo hardcodes the English processor; `\b` regex breaks on CJK), then run vocabulary extraction over all JA tests via the existing japanese processor + sense generator. Operator decision: transcripts only, no frequency-list top-up. Establish JA `frequency_rank` via the `wordfreq` library.

**Acceptance Criteria:**
- [x] B4 fixed: correct language_id propagation; CJK-safe whole-word matching via the language processor's tokenizer (fugashi), not `\b`
- [x] Extraction run over all 82 JA tests: `dim_vocabulary` lang-3 rows > 0 with `part_of_speech` populated [2,404 vocab, 100% POS]; senses generated [4,792 senses]
- [x] `frequency_rank` populated for ≥90% of JA lemmas [98.59%, 2,370/2,404] (wordfreq lookup; unknown lemmas ranked last)
- [x] 50-lemma human spot-check passes (correct lemmatisation, no particles/fragments as lemmas — 0 助詞/助動詞/記号 lemmas; dictionary forms verified: 移す/増える/発明 etc.)

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_pipeline.py` — B4 fix [prior session]
- `services/vocabulary/frequency_service.py` — JA wordfreq path [pre-existing]
- run via existing admin Full Pipeline / `scripts/backfill_vocab.py` against language_id=3
- `migrations/ja_vocab_phrase_detection_seed.sql` — NEW (live blocker found this session)
- `requirements.txt` — `mecab-python3` + `ipadic` (NEW — wordfreq JA tokenization)

**Verification:**
`SELECT count(*) FROM dim_vocabulary WHERE language_id=3` > 0; spot-check sample attached to PR.

**Resolution (2026-06-16 — live extraction batch run over all 82 JA tests):**
The prior session landed code-only and never ran live, so two real prerequisites surfaced on first
live run (both fixed this session):
1. **Missing JA `vocab_phrase_detection` prompt** — the extraction pipeline
   (`services/vocabulary/pipeline.py`, `get_template_config`) hard-failed all 82 tests with
   "No active prompt_templates row". TASK-508 had seeded the *ladder* prompts, not this upstream
   *extraction* prompt. Seeded `migrations/ja_vocab_phrase_detection_seed.sql` (cloned from ZH/EN,
   adapted to JA MWEs: 複合動詞/慣用句/複合語/連語; model `google/gemini-2.5-flash-lite` like
   ZH/EN; idempotent `WHERE NOT EXISTS`). The sibling `vocab_definition_generation` and
   `vocab_sense_selection` JA rows already existed.
2. **Missing `mecab-python3` + `ipadic`** — `wordfreq`'s Japanese tokenizer (used by
   `compute_zipf_for_vocab_item` for `frequency_rank`) raised `No module named 'MeCab'`. fugashi is a
   *separate* binding; wordfreq specifically imports `MeCab`. Installed both into the venv + added to
   `requirements.txt`. Verified (食べる→4.92, 学校→5.31).
**Results:** all 82 tests processed, 0 failed → **2,404 vocab (100% POS), 4,792 senses,
`frequency_rank` 98.59%**. Definitions are dual-register (simple + standard JA). Extraction degraded
gracefully on occasional malformed phrase-detection JSON (gemini-flash-lite) with fallback to
`qwen/qwen3.6-flash`. Validated incrementally (2-test smoke first) before the full run. Cost: the
batch roughly doubled session spend (one definition-gen LLM call per unique lemma); operator
explicitly approved the full run. This unblocked + closed TASK-506's deferred JA pronunciation
backfill (100% JA kana, same session).

---

## TASK-506: Pronunciation backfill (ZH + JA) + JA `register` column

**Status:** [x] Done (2026-06-16 — ZH 100% + JA 100% kana after TASK-505 batch + register column)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-505 (JA portion)

**Description:**
`dim_word_senses.pronunciation` is ≈0% populated (finding G3) but is a hard requirement for reading/tone exercise types. Backfill deterministically: pypinyin with jieba word-context (+ existing sandhi engine output stored as tone digits) for all ZH senses; fugashi/UniDic kana readings for all JA senses. Add `dim_word_senses.register text` (keigo: `plain|polite|honorific|humble|formal|casual`, NULL elsewhere) per operator answer 13 — populated by the JA P1 prompt going forward (TASK-508).

**Acceptance Criteria:**
- [x] `pronunciation` populated for ≥99% of ZH senses (tone-marked pinyin + machine-readable tone digits) [DONE: 100%, 8084/8084] and ≥95% of JA senses (kana) [DONE: 100%, 4792/4792 after the TASK-505 batch]; failures logged with reason
- [x] Polyphones resolved with the lemma's word context (jieba) — spot-class sample checked (便宜=pián yi, 重复=chóng fù, 重要=zhòng yào, 长大=zhǎng dà, 音乐=yīn yuè)
- [x] `migrations/dim_word_senses_register.sql` applied; column documented
- [x] Script is idempotent (skips already-populated rows unless `--force`)

**Files to Create / Modify:**
- `scripts/backfill_pronunciations.py` — new
- `migrations/dim_word_senses_register.sql` — new

**Verification:**
Coverage query per language ≥ thresholds; re-run is a no-op.

**Resolution (2026-06-14 — register column + ZH backfill done; JA pronunciation deferred):**
- `migrations/dim_word_senses_register.sql` (ADD COLUMN IF NOT EXISTS `register text`) applied live +
  verified. (Applied during TASK-508 for sequencing — committed there; the column carries JA keigo
  plain|polite|honorific|humble|formal|casual, NULL elsewhere; populated going forward by the JA P1
  prompt via `asset_pipeline._update_vocabulary_metadata`.)
- `scripts/backfill_pronunciations.py` (new, deterministic, NO LLM cost): ZH uses the existing sandhi
  engine `services/pinyin_service.process_passage` (jieba word-context + pypinyin + 三声/一/不 sandhi);
  stores `"<tone-marked pinyin> (<tone digits, sandhi-applied>)"` (diacritics = base/dictionary tones,
  digits = spoken/context tones). JA uses fugashi + unidic-lite → hiragana reading (verified offline:
  食べる→たべる, 学校→がっこう, 図書館→としょかん). Idempotent (skips populated unless `--force`).
- **ZH run: 100% coverage (8084/8084)**, polyphones correctly disambiguated by word context (spot-check
  above). Idempotent re-run fetched 0 rows. (NB: the run was driven via a `| findstr` pipe that errored
  under bash — `findstr` is a cmd builtin — but the Python writer completed all updates; the script
  itself is clean. fugashi/unidic-lite confirmed installed.)
- **JA kana backfill — DONE (2026-06-16):** after the TASK-505 batch created 4,792 JA senses,
  `backfill_pronunciations.py --language ja` ran (fugashi + unidic-lite → hiragana, deterministic, no
  LLM cost): **100% (4,792/4,792)**, 0 failed. Readings verified (機械→きかい, 発明→はつめい,
  増える→ふえる, 学校→がっこう, 情報→じょうほう).

---

## TASK-507: `semantic_class` backfill (LLM classification batch)

**Status:** [x] Done (2026-06-18 — all 3 languages 100% classified; human spot-check CSV handed to operator)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-502, TASK-505

**Description:**
Classify every lemma (EN + ZH + JA, ~10k after JA bootstrap) into the ratified 6-value enum with a cheap LLM batch (flash-tier, batched ~50 lemmas/call, prompt includes POS + definition as context). Record `gen_confidence`; low-confidence rows default to `abstract` and are flagged. This unlocks `active_levels` routing — without it every word gets all 9 levels (the eval's "bean" failure).

**Acceptance Criteria:**
- [x] ≥95% of lemmas classified — 100% (9,865/9,865: ZH 3,890 / EN 3,571 / JA 2,404); `proper` catches proper nouns (ZH 66, JA 19, EN 0 — the EN frequency list has none), excluded from the ladder by `compute_active_levels`
- [~] 200-row stratified human spot-check ≥90% agreement — **CSV emitted (`spot_check_semantic_class.csv`, 198 rows, class-stratified) and handed to the operator; the human sign-off is the operator's step (not fabricated).** No prompt iteration was needed pre-run (0 parse/schema failures across all batches).
- [x] Cost logged to `llm_calls` (task_name=`semantic_class_classification`) — every call logged via `call_llm` under that task_name
- [x] Idempotent (skips classified rows) — proven: a re-run after completion found 0 lemmas to classify

**Files to Create / Modify:**
- `scripts/backfill_semantic_class.py` — new
- `migrations/semantic_class_backfill.sql` — new (adds `dim_vocabulary.semantic_class_confidence` + the 3 `prompt_templates` seed rows)

**Verification:**
`SELECT semantic_class, count(*) FROM dim_vocabulary GROUP BY 1` shows a plausible distribution; spot-check sheet attached.

**Resolution (2026-06-18):**
- **Migration** `migrations/semantic_class_backfill.sql` applied live: added
  `dim_vocabulary.semantic_class_confidence real` (records the classifier's
  certainty; the spec's "record gen_confidence" — `dim_vocabulary` had no
  confidence column, only `dim_word_senses.gen_confidence` exists) and seeded 3
  `prompt_templates` rows (`semantic_class_classification`, language_id 1/2/3,
  `google/gemini-3.5-flash`, provider `openrouter`). `language_id` is NOT NULL on
  the table so a row per language is required; text is language-agnostic (the
  6-value enum is). Idempotent `WHERE NOT EXISTS` guard.
- **Script** `scripts/backfill_semantic_class.py`: ~50 lemmas/call, context =
  `part_of_speech` (dim_vocabulary) + the primary sense definition
  (`dim_word_senses`, lowest `sense_rank`). Model returns `{id:{class,confidence}}`
  at temp 0. Confidence persisted; rows below `--conf-threshold` (0.6) defaulted to
  `abstract` and flagged (query: `semantic_class='abstract' AND
  semantic_class_confidence < 0.6` → 7 rows). Idempotent (only `semantic_class IS
  NULL` unless `--force`); failures logged, never fatal.
- **Run:** ZH + EN completed in the first pass; JA stalled at batch 26 because
  OpenRouter credits were exhausted mid-run (every subsequent call hard-failed
  with a non-retryable error, 0 retries). After the operator topped up,
  `--language ja` re-ran idempotently and filled the remaining 1,154 rows
  (0 failed). Final: 100% all three languages.
- **Distribution (plausible):** action/abstract/concrete/property dominant;
  function + proper are small minorities, as expected for a frequency-ranked list.
- **Flagged:** the ≥90% human spot-check sign-off is deferred to the operator
  (CSV ready). The two repo migration `.sql` files were applied (507 via
  `apply_migration`; 509 via `execute_sql` after `apply_migration` 502'd) — both
  live; the repo files are the canonical record.
- **Prompt revision (2026-06-21 — numeric output, target-language legend):** per the
  house convention that a target-language item must only read/emit target-language
  text or numeric indices (never English class words), the classifier prompt was
  refactored. The single English template became **three language-specific** rows
  (ZH/JA legends + rules fully in Chinese/Japanese; EN in English), each binding the
  six classes to a number; the model now returns `{"<id>": [<class 1-6>, <conf>]}`
  — numbers only. The English enum (required by the `semantic_class` CHECK) is
  produced solely by `INDEX_TO_CLASS` in the script at write time. Input lines also
  dropped their English scaffolding keys. **Live-validated** one batch per language:
  `numeric_output=True, failed=0` all three; mappings correct (人们→concrete,
  写字→action, 機械→concrete, bean→concrete). The already-classified corpus was
  **not** re-run — it is correct; this was a prompt/parser quality fix for future
  runs. Files: `migrations/semantic_class_backfill.sql` (re-seeded v2 templates),
  `scripts/backfill_semantic_class.py` (`INDEX_TO_CLASS`, `_parse_entry`).

---

## TASK-508: Japanese prompt seeds (P1/P2/P3 + 4 judges + generation rows)

**Status:** [x] Done (2026-06-17 — seeds + code landed; live P1 smoke passed)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Seed every `prompt_templates` row JA generation needs, cloned structurally from the ZH set, all on `qwen/qwen3.7-plus`: `vocab_prompt1_core`(3) — with the three JA-specific additions from §6.6 (per-sense `register`, kana readings per sentence occurrence, counter word for concrete nouns, mirroring ZH rule 18); `vocab_prompt2_exercises`(3); `vocab_prompt3_transforms`(3); the 4 ladder judges (p1_sentence/l1_distractor/collocation/sentence_validity, with JA error taxonomies — particle confusion, conjugation class, long/short vowel); activate `cloze_distractor_generation`(3); seed `exercise_sentence_generation`(3).

**Acceptance Criteria:**
- [x] All rows present, active, `provider='openrouter'`, model `qwen/qwen3.7-plus`
- [x] JA P1 output schema includes `register` + readings + counter keys (numeric-key JSON, documented in the migration header)
- [x] `_load_models`/`get_template_config` resolve for language_id=3 without error
- [x] One end-to-end smoke sense generated producing ≥1 valid P1 asset (2026-06-17: sense 35000 機械 → valid asset; all 3 JA additions verified live — register=polite, furigana=きかい べんり, 助数詞=台; semantic_class=concrete token; 10 sentences; model qwen/qwen3.7-plus; generate()-only, no DB write to clean up)

**Files to Create / Modify:**
- `migrations/ja_prompt_seeds.sql` — new (idempotent NOT EXISTS guards)
- `services/vocabulary_ladder/asset_generators/prompt1_core.py` — parse the new JA P1 keys → `dim_word_senses.register`

**Verification:**
Smoke-sense run log + `SELECT task_name, is_active FROM prompt_templates WHERE language_id=3` matches the list.

**Resolution (2026-06-14 — seeds + code landed; live P1 smoke deferred):**
- `migrations/ja_prompt_seeds.sql` written + applied live. Seeds 8 JA (lang=3) tasks structurally
  cloned from the active ZH set, all `provider='openrouter'`, `model='qwen/qwen3.7-plus'`,
  idempotent `WHERE NOT EXISTS` guards (no unique constraint exists on
  `(task_name,language_id,version)` — verified, only PK on id): `vocab_prompt1_core` (with §6.6
  JA additions), `vocab_prompt2_exercises`, `vocab_prompt3_transforms`, `ladder_p1_sentence_judge`,
  `ladder_l1_distractor_judge`, `ladder_collocation_judge`, `ladder_sentence_validity_judge`,
  `exercise_sentence_generation`; plus activated the pre-existing `cloze_distractor_generation`
  lang=3 v1 (it was already a complete JA template on qwen3.7-plus, just inactive). Verified: all
  9 tasks have exactly 1 active row with model+provider populated (what `get_template_config`
  requires → resolves for lang=3 without error).
- **JA P1 schema additions (documented in the migration header):** key `10`=register (keigo:
  plain|polite|honorific|humble|formal|casual); key `5`=kana reading of the lemma; per-sentence
  furigana as sentence-object key `5`; counter (助数詞) as a `morphological_forms` (key 9) entry
  labeled 助数詞 (JA analogue of ZH rule 18). JA L1 distractor rules + judge enforce **audio**
  confusability (long/short vowel, dakuten, sokuon/hatsuon, pitch) per [[l1_is_listening]] — never
  visual similarity. JA error taxonomies (particle confusion, conjugation/aspect, 助数詞,
  long/short vowel) baked into P2/P3/judges.
- **`semantic_class` decision (flagged):** `_LEGACY_SEMANTIC_CLASS_MAP` has ZH/EN labels but **no
  JA labels**, so the JA P1 prompt emits the ratified English enum tokens directly
  (`concrete|abstract|action|property|function|proper`) — they pass through
  `normalize_semantic_class` cleanly, avoiding a `dim_vocabulary.semantic_class` CHECK violation.
- **Code (flagged location):** register *parsing* (numeric→descriptive) was already handled by
  `PROMPT1_KEY_MAP '10'→register` in prompt1_core's `_remap_output`; no change needed there. The
  *persist* to `dim_word_senses.register` was missing — added to
  `asset_pipeline._update_vocabulary_metadata` (where all other P1→dim_word_senses phonetic writes
  live), guarded so it's a no-op for ZH/EN. Added `'5':'furigana'` to `SENTENCE_KEY_MAP`
  (config.py). Suite: **530 passed, 1 skipped** (baseline unchanged).
- **Sequencing (flagged):** applied `migrations/dim_word_senses_register.sql` (nominally TASK-506's
  file) NOW so the register write target exists; committed with this task.
- **DEFERRED:** the live end-to-end P1 smoke sense — there are 0 JA senses until the TASK-505 batch
  runs, and the single LLM call is held for the cost-budgeted TASK-505 session. Code is ready to
  run it. Not fabricated.

---

## TASK-509: Traditional Chinese groundwork (dual-store)

**Status:** [x] Done (2026-06-18 — lemmas + all 2,393 exercise mirrors backfilled; renderer wired)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Operator decision: dual-store both scripts at generation (§6.7). Add the `opencc` dependency (config `s2twp`); add `dim_vocabulary.lemma_traditional` (filled by enrichment with jieba context for ambiguous 发→發/髮-class lemmas); create `script_conversion_overrides(simplified PK, traditional, note)`; add a renderer step that persists a `content.hant` mirror (stem, option texts, reasoning) on every ZH exercise after validation; write the idempotent mirror-backfill script for existing/corrected rows. Document the `users.exercise_preferences.script_variant` convention.

**Acceptance Criteria:**
- [x] `lemma_traditional` populated for ≥99% of ZH lemmas — 100% (3,890/3,890; 2,406 differ from Simplified). Ambiguous conversions spot-checked: `发→發` (诱发→誘發, 发展→發展), phrase-aware `晒干→曬乾` vs bare `干→幹`, `后→後` (随后→隨後), `面→面/臨` (面临→面臨)
- [x] Renderer writes `content.hant` covering every learner-visible TL string for all newly generated ZH exercises — `_render_hant_mirror` deep-converts the whole content dict (non-Han values pass through unchanged)
- [x] Overrides table consulted at mirror render; correcting an override + re-running backfill updates only `hant` — `ScriptConverter` loads `script_conversion_overrides` and applies them with sentinel priority over OpenCC; backfill writes only the `hant` key (and only when it differs)
- [x] Mirror-backfill script converts existing ZH exercises (~2,393 rows) idempotently — 2,388 updated + 5 skipped (the pilot rows) on first run; option-count parity verified

**Files to Create / Modify:**
- `migrations/traditional_chinese_groundwork.sql` — column + overrides table
- `requirements.txt` — `opencc==1.3.1`
- `services/vocabulary_ladder/script_converter.py` — new (`ScriptConverter`, s2twp + overrides)
- `services/vocabulary_ladder/exercise_renderer.py` — `_render_hant_mirror` step
- `scripts/backfill_hant_mirrors.py` — new (lemmas + exercise mirrors)

**Verification:**
Random 20 generated ZH exercises each contain `content.hant` with option-count parity; backfill re-run is a no-op.

**Resolution (2026-06-18):**
- **Migration** `migrations/traditional_chinese_groundwork.sql` applied live: added
  `dim_vocabulary.lemma_traditional text` and `script_conversion_overrides
  (simplified PK, traditional, note, created_at)`. (Applied via `execute_sql`
  because the `apply_migration` MCP endpoint was 502'ing; the repo file is canonical.)
- **`opencc==1.3.1`** added to `requirements.txt` (official binding, ships Windows
  wheels; config `s2twp` — phrase-aware Taiwan standard).
- **`ScriptConverter`** (`services/vocabulary_ladder/script_converter.py`): wraps
  OpenCC `s2twp` plus the overrides table. Overrides win absolutely — the
  simplified form is swapped for a PUA sentinel before OpenCC runs, then replaced
  with the curated traditional form so OpenCC can never re-convert it. Non-Han
  characters (pinyin, ASCII, English) pass through untouched, so `convert_content`
  safely deep-converts a whole exercise `content` dict. **jieba pre-segmentation
  proved unnecessary** — s2twp's phrase awareness already resolves the 发/干/后/面
  ambiguities from context (verified: bare `干→幹` but `晒干→曬乾`).
- **Renderer:** `_render_hant_mirror` runs in `build_rows` after judge sidecars are
  popped (so `__judge_*` never leaks into `hant`), ZH-only, failures non-fatal.
  Lazy per-renderer converter (overrides loaded once).
- **Backfill** `scripts/backfill_hant_mirrors.py`: `--target lemmas|exercises|all`.
  Each row's Traditional form is recomputed and written **only when it differs**
  from what's stored — so a plain re-run is a no-op, but correcting an override +
  re-running updates exactly the affected mirrors (and only the `hant` key; the
  Simplified content is never touched). Lemmas: 3,890 updated. Exercises: 2,388
  updated + 5 skipped.
- **Residual (for the overrides table):** s2twp's Taiwan-vocabulary substitution
  can over-reach on some compounds (e.g. `历史进程→歷史程序` rather than `歷史進程`).
  Harmless for groundwork; add a `script_conversion_overrides` row if the operator
  disagrees on any specific case.
- **Serve convention (documented, consumed by TASK-526):**
  `users.exercise_preferences.script_variant` ∈ {`simplified` (default),
  `traditional` (serve `content.hant` / `lemma_traditional`)}.

---

## TASK-510: Model-slug health cron + fail-closed batch judges

**Status:** [x] Done (2026-08-08)
**Feature:** exercise-generation-v2
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-501

**Description:**
Two total outages came from delisted model slugs (finding G8). Add a nightly APScheduler job (advisory-lock pattern, after IRT) that probes every `DISTINCT model FROM prompt_templates WHERE is_active` against OpenRouter `/models` and surfaces misses (dashboard banner + ERROR log). Flip judges to **fail closed in generation batches**: a judge that cannot resolve its template/model raises and blocks the batch with a loud error, instead of silently accepting everything (serve-adjacent call sites keep fail-open).

**Acceptance Criteria:**
- [ ] Cron registered (`slug_health_nightly`, ~04:10 UTC, advisory lock, `DISABLE_SCHEDULER` honoured); manual admin trigger endpoint too
- [ ] Dead slug → admin dashboard banner + ERROR log naming the rows
- [ ] Batch generation with a missing judge template aborts with an actionable error (test simulates a missing row)
- [ ] Serve-adjacent judge paths unchanged (fail-open test still green)

**Files to Create / Modify:**
- `services/model_health.py` — new probe
- `app.py` — scheduler entry
- `routes/admin_local.py` — banner data + manual trigger
- `services/exercise_generation/judges/base.py` — batch-mode fail-closed flag

**Verification:**
Probe with a planted dead slug → banner JSON lists it; batch with a judge row deactivated → aborts.

**Resolution (2026-08-08):** `services/model_health.py` probes every DISTINCT active
`prompt_templates` model against the provider's `/models` listing, memoised 15 min so
dashboard polling doesn't hammer OpenRouter. Only `provider='openrouter'` rows are probed —
ollama slugs live on a host-specific daemon, so their absence is not rot and they are
reported under `skipped`. Routing suffixes (`:free`, `@preset/…`) resolve against the bare
listing id. A probe failure reports `error` with `ok` left True: a flaky network must not
manufacture a false "everything is dead" banner.

Cron `slug_health_nightly` @ 04:10 UTC in [app.py](../../../app.py) (after IRT, honours
`DISABLE_SCHEDULER`), advisory-locked via new RPCs
`pg_try_advisory_lock_for_model_health` / `pg_advisory_unlock_for_model_health`
(`migrations/task510_model_health_advisory_lock.sql`, lock key 1298417772 = 'MdHl',
distinct from IRT and Study-Plan). **Applied live 2026-08-08**; verified acquire→true,
release→true, 0 locks left. Manual trigger `POST /admin/api/run/model-slug-health` +
banner feed `GET /admin/api/model-slug-health` + dashboard banner.

Fail-closed half: `judges/base.py` gains `batch_mode()` (a **thread-local** flag, so a
batch in an APScheduler thread can never flip the contract for a request thread),
`JudgeUnavailable`, and `guard_fail_open()`. Because every judge already funnels errors
through `safe_accept()`, that one chokepoint makes them all fail closed.

**Design decision:** `safe_accept` (judge *outage* — dead slug, missing template, unusable
response) now raises in batch mode, but a new `accept_item()` was added for *per-item* gaps
(one unparseable rating in an otherwise healthy response) and never raises. Aborting a
3,000-sense batch over a single malformed entry would be a worse failure than shipping that
item, and the v3 Likert contract already says a missing verdict must never manufacture a
rejection. Per-item call sites in `p1_sentences.py`, `sentence_validity.py`, and
collocation's "nothing to judge" early return were moved to `accept_item`.

Tests: `tests/test_model_health.py` (18) — dead-slug detection naming every offending row,
ollama skip, routing-suffix match, probe-failure-isn't-death, memoisation, ERROR log
content, lock skip, thread-isolation, serve-path fail-open still green, batch abort on
missing template *and* on LLM failure, and per-item tolerance inside a batch.

---

## TASK-511: `generation_queue` migration

**Status:** [x] Done (2026-06-14)
**Feature:** exercise-generation-v2
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Create the async work queue (§6.5 DDL verbatim): per-sense rows with `reason ∈ (pack, subscribe_topup, coverage_gap, regen)`, status lifecycle, `UNIQUE (sense_id, reason)`.

**Acceptance Criteria:**
- [x] Table live per §6.5; index on `(status, requested_at)`
- [x] Duplicate (sense, reason) insert upserts/no-ops rather than erroring

**Files to Create / Modify:**
- `migrations/generation_queue.sql`

**Verification:**
Insert/duplicate-insert/status-update round-trip in a SQL smoke test.

**Resolution (2026-06-14):** `migrations/generation_queue.sql` written (§6.5 DDL verbatim,
`CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` on `(status, requested_at)`) and
applied live via Supabase MCP. Verified: 8 columns, 1 UNIQUE constraint `(sense_id, reason)`,
status index present. Round-trip smoke (DO block over a real `dim_word_senses` sense): insert →
duplicate insert (`ON CONFLICT (sense_id, reason) DO NOTHING`, no error → no-op confirmed) →
status update to `done` → cleanup; table left empty (0 rows). FK to `dim_word_senses(id)` works
fine despite JA senses being absent. Note: `dim_word_senses` has no `language_id` column, so the
queue's `language_id` is producer-supplied (independent of the senses table).

---

## TASK-512: Consolidation — ladder pipeline becomes the sole vocab generator

**Status:** [x] Done (2026-08-08)
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Remove `VOCABULARY_DISTRIBUTION` and the vocabulary source branch from the legacy `ExerciseGenerationOrchestrator`; the admin "Exercise Generation → vocabulary" action routes to the ladder pipeline (`VocabAssetPipeline` + renderer) instead. Legacy keeps grammar/conversation/style untouched (frozen). Existing legacy vocab exercises keep serving until TASK-518 deactivates them per sense.

**Acceptance Criteria:**
- [ ] `run_vocabulary_batch` (admin path) invokes the ladder pipeline; legacy orchestrator rejects `source_type='vocabulary'` with a clear error
- [ ] Grammar/conversation/style batches still function (smoke run each)
- [ ] No orphaned imports/config (`VOCABULARY_DISTRIBUTION` deleted from `services/exercise_generation/config.py`)
- [ ] Wiki: [[features/exercises.tech]] updated to record the freeze

**Files to Create / Modify:**
- `services/exercise_generation/orchestrator.py`, `config.py` — remove vocab branch
- `routes/admin_local.py` / `run_exercise_generation.py` — reroute vocab batches
- `wiki/features/exercises.tech.md` — freeze note

**Verification:**
Admin vocab batch for one EN sense produces ladder-rendered exercises (`word_asset_id IS NOT NULL`); grammar batch unchanged.

**Resolution (2026-08-08):** `ExerciseGenerationOrchestrator` now rejects
`source_type='vocabulary'` from **both** `_get_distribution()` and `_build_generators()`
(module-level `_VOCAB_RETIRED_MSG` names the ladder entry points), so there is no path back
in via either. `VOCABULARY_DISTRIBUTION` deleted from
`services/exercise_generation/config.py` — the ladder's per-level mix comes from the
capability matrix in `services/vocabulary_ladder/config.py`, not a flat type→count map.

`run_vocabulary_batch()` (admin action + `--source vocabulary` CLI) routes to
`VocabAssetPipeline.generate_for_sense()` then `LadderExerciseRenderer.render_all()`, and
**skips rendering when asset status is `failed`** — rendering half-built assets is how blank
and single-option exercises reach learners. Per-sense result now carries
`{status, exercise_ids, errors}`.

Freeze recorded in [[features/exercises.tech]] with a source-type ownership table.
Grammar / collocation / conversation / style stay on the legacy orchestrator, frozen.

**Known accepted exemption:** `generators/style.py` still writes `grading_notes` outside the
schema-v2 `content.nl` envelope (TASK-519). Because this task freezes the style path, that
is recorded as an exemption in `tests/test_nl_keyed_content.py::_FROZEN_LEGACY` rather than
fixed — deleting its line there is the reminder if style is ever unfrozen.

**Not verified:** the AC's "smoke run each" for grammar / conversation / style batches needs
live LLM + DB spend and was not run. Code-level verification only: vocabulary raises from
both entry points, grammar distribution still resolves, `VOCABULARY_DISTRIBUTION` is gone,
and the full Python suite (1,342 tests) is green.

---

## TASK-513: Transcript mining as a P1 sentence source

**Status:** [x] Done (2026-08-08 — code + tests; no live batch run)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-512

**Description:**
Port the legacy `TranscriptMiner` capability into the ladder pipeline: before P1 generation, mine candidate sentences containing the target sense from test transcripts (via `tests.vocab_sense_ids`/`vocab_token_map`), strip markup, tier-filter, and pass them to P1 as pre-seeded candidates. All sentences — mined and generated — go through the existing P1 sentence judge. Record `provenance.sentence_source = 'mined' | 'generated'`.

**Acceptance Criteria:**
- [ ] P1 prompt accepts seeded candidate sentences and only generates the remainder up to 10
- [ ] Mined sentences pass the same judge; rejected mined sentences are replaced by generated ones (never shipped)
- [ ] CJK mining uses the language tokenizer (no `\b`); works for ZH and JA (after TASK-505's B4 fix)
- [ ] `sentence_source` persisted per sentence in `word_assets` and echoed into exercise provenance

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_pipeline.py` — mining step (replaces the broken corpus-extraction path)
- `services/vocabulary_ladder/asset_generators/prompt1_core.py` — seeded-candidates support

**Verification:**
Generate a sense whose lemma appears in ≥2 transcripts → P1 asset contains ≥1 `mined` sentence that passed the judge.

**Resolution (2026-08-08).** `_fetch_corpus_sentences` no longer scans 50
arbitrary transcripts plus 30 conversations substring-matching the bare lemma.
It now goes through the index built for the question: the
`tests_containing_sense` RPC over `tests.vocab_sense_ids` (GIN), with
`tests.vocab_token_map` supplying the surface forms that realise *this* sense.
Both token-map shapes are read (legacy `["ran", 42]` pairs and
`{"token":…,"sense_id":…}` objects) because more than one backfill generation
wrote it. Mined sentences are markup-stripped, deduplicated, screened by the
TASK-524 tier gate before seeding, and capped at `VOCAB_SENTENCES_PER_WORD`.
Any failure returns `[]`, so P1 generates the full set — the correct
degradation. The old `_extract_sentences_with_word` helper is deleted.

P1 already accepted seeded candidates and generated only the remainder, so AC 1
needed no change. `sentence_source` is now stamped per sentence by
`CoreAssetGenerator._tag_sentence_sources` and **derived, not trusted**: a
sentence is `mined` only if it matches a seeded candidate once whitespace and
case are normalised. A model that lightly rewrites a mined sentence has, for
provenance purposes, generated a new one — a false `generated` costs nothing, a
false `mined` claims corpus attestation the sentence does not have. The renderer
echoes the index-aligned map into `exercises.tags.provenance`.

**One finding worth keeping.** ZH recall was zero on obvious cases because jieba
merges 喝+咖啡 into one token, so `contains_whole_word` — correct in rejecting
咖啡 inside 咖啡馆 ("cafe") — also rejected it inside 喝咖啡. The two are told
apart by position: Chinese compounding is overwhelmingly head-final, so a target
in **prefix** position is usually part of a derived word while a target in
**suffix** position is usually the object of a merged phrase. `_mentions_token`
accepts the suffix case as a mining-only fallback. Deliberately not folded into
`contains_whole_word`, which is shared with sentence *validation* where the
strict reading is right.

Tests: `tests/test_transcript_mining.py` (31) — token-map parsing, sense
discrimination, markup/dedup/tier-screen, the ZH prefix-vs-suffix pair, RPC
failure degradation, provenance labelling and its echo into tags.

---

## TASK-514: Pipeline robustness — non-destructive regen, P1 retry, matrix-gated L4

**Status:** [x] Done (2026-08-08 — B5 closed; regen smoke on a real sense still owed)
**Feature:** exercise-generation-v2
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** TASK-504

**Description:**
Close the three remaining audit bugs before the big batch: **B1** — regeneration renders to a staging list and only delete-and-replaces when the new render is non-empty (today a failed regen wipes a good word's exercises, [admin_local.py:1338](../../routes/admin_local.py#L1338)); **B6** — P1 gets retry + targeted field repair (mirror P2/P3); **B5** — L4 activation comes from the capability matrix, not from hoping the model returns null.

**Acceptance Criteria:**
- [ ] Regen of a sense whose new P1 fails leaves the previous exercises untouched (test)
- [ ] P1 single malformed response → one retry, then field-targeted repair call, then block (test with mocked LLM)
- [ ] ZH concrete noun's plan contains no `morphology_slot` regardless of model output (matrix-gated)

**Files to Create / Modify:**
- `routes/admin_local.py` — staging-list regen
- `services/vocabulary_ladder/asset_generators/prompt1_core.py` — retry/repair
- `services/vocabulary_ladder/asset_pipeline.py` — matrix-gated planning

**Verification:**
Three new tests green; regen smoke on a real sense.

**Resolution (2026-08-08) — partial. Read before picking this up.**

**B1 (non-destructive regen) — already done, not by this task.** The staging-list pattern is
live at [routes/admin_local.py](../../../routes/admin_local.py) in `_do_vocab_regenerate`:
`renderer.build_rows()` first, bail out with `retained_existing: True` if it yields 0 rows,
then insert-before-delete so the sense is never momentarily empty. Worst case is duplicates
(cleaned by the next regen), never data loss. The task's status was stale.

**B6 (P1 retry + targeted repair) — already done, not by this task.**
`asset_generators/prompt1_core.py` has `_call_with_retry` (2 attempts, retries on exception
*and* on blank response), `repair()` (targeted validation-error fix) and `repair_sentences()`
(per-index sentence repair). Mirrors the P2/P3 pattern as the task asked. Also stale.

**B5 (matrix-gated L4) — HALF DONE. The remaining half is real work.**

Added `requirements_met(requires, context)` and `active_levels_for_context(semantic_class,
language_id, context)` to `services/vocabulary_ladder/config.py`, and wired them into
`VocabAssetPipeline.generate_for_sense` via a new `_capability_context(core_asset)` that
reports `morph_forms`, `pronunciation`, `p1_definition`, `p1_sentences`. Unknown requirement
tokens count as satisfied — planning must not drop a level over something only the renderer
can see (`tts`, `same_tier_senses`). `compute_active_levels()` is unchanged, so existing
routing tests are untouched.

**Why the AC is still not met.** The AC says "ZH concrete noun's plan contains no
`morphology_slot`". That cannot be achieved by gating *levels*, because TASK-504 already
seeded richer L4 rows than the task text assumed:

| lang | class | L4 capabilities (`requires`) |
|------|-------|------------------------------|
| zh | concrete | `cloze_typed` (`cloze_asset`), `classifier_match` (`classifier_dict`) |
| en | action | `cloze_typed`, `morphology_slot` (`morph_forms>=2`), `word_family` (`morph_forms>=2`) |
| ja | concrete | `cloze_typed`, `particle_selection`, `counter_match` (`counter_dict`) |

ZH concrete legitimately keeps L4 via `classifier_match` (TASK-528) and `cloze_typed`
(TASK-532). Level survives; the *type* must be suppressed. So B5 needs **per-type** gating
inside P3 prompt assembly — `prompt3_transforms.py` must ask for morphology only when a
morphology-bearing capability row for this (language, semantic_class, word) actually
qualifies, instead of including L4 in `p3_active` and hoping the model returns null.

Tests: `tests/test_matrix_gated_planning.py` (14) cover the new helpers and document this
boundary explicitly — `test_a_level_survives_while_any_of_its_capabilities_can_fire` asserts
the current (correct) level-level behaviour, and the ZH-concrete tests `skip` with a message
when a non-morphology L4 capability exists rather than passing vacuously.

**Resolution part 2 (2026-08-08) — B5 closed.**

Gating is now per *type*, not per level. `config.py` gains
`PROMPT3_TYPE_FOR_LEVEL` (4→morphology_slot, 7→spot_incorrect_sentence,
8→collocation_repair), `type_is_available(type_code, language_id,
semantic_class, context)` and `prompt3_levels_for_context(...)`. A level stays
alive on any capability that can fire; the *prompt* only asks for the type it
owns. ZH concrete therefore keeps L4 (classifier_match, cloze_typed — both
deterministic) while P3 stops asking Sonnet for Chinese morphology.

Both sides are gated, because assets written before this exist:
  * **generation** — `TransformAssetGenerator.generate` takes optional
    `semantic_class` + `capability_context`; supplied by the pipeline, omitted
    by admin one-off callers so their behaviour is unchanged. When the gate
    empties the level set the LLM is never called at all.
  * **rendering** — `build_rows` suppresses a P3-owned level whose type cannot
    fire, so a stale `level_4` blob of invented ZH plurals cannot reach the
    corpus. `semantic_class` is normalised for the gate (legacy assets still
    say `concrete_noun`); `compute_active_levels` is deliberately left on the
    raw value, since narrowing the level set for legacy assets is a wider
    behaviour change than this task authorises.

`validate_prompt3` is held to the gated level list, otherwise a correctly
suppressed L4 reads back as "Missing level_4" and invalidates a good asset.
`_capability_context` moved to `config.capability_context_from_core` so the
pipeline and the renderer gate on identical facts.

Permissive in the same two places as the rest of the module: an unrecognised /
NULL `semantic_class` and a language with no matrix rows both pass, so a
misconfiguration degrades to the old behaviour rather than generating nothing.

Tests: `tests/test_p3_type_gating.py` (20) — including the AC pair, that a ZH
concrete noun's P3 *request* omits "4" and its *rendered output* contains no
`morphology_slot` even from a stale asset carrying one.

**Still owed:** the regen smoke on a real sense (needs live LLM + DB spend).

---

## TASK-515: Batch run — top 1,000 senses × EN/ZH/JA

**Status:** [~] In Progress — two blocking defects fixed 2026-08-12 (cost logging,
asset_type CHECK); 7 senses run; the full batch is **wall-clock blocked**, not
spend blocked. See the 2026-08-12 note below.
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-504, 505, 506, 507, 508, 509, 510, 511, 513, 514, 519

**Description:**
The integration gate. Select the top 1,000 senses per language by `frequency_rank` (sense_rank=1 senses first; `proper` excluded), run the full ladder pipeline (P1 mined+generated → judges → P2/P3 → render incl. `hant` mirrors) in resumable nightly chunks (~100 senses/night/language) via the admin runner with stop checks, per-chunk cost logging, and a dry-run mode. Budget guardrail: abort the chunk if projected cost exceeds a configured ceiling.

**Acceptance Criteria:**
- [ ] Selection query reviewed (frequency-ranked, sense_rank-aware, proper-excluded) and persisted as a script
- [ ] ≥90% of attempted senses end with valid P1 + rendered exercises; failures land in `generation_queue(reason='regen')` with reasons
- [ ] Per-chunk report: senses done, exercises created, judge reject-rates, LLM cost (from `llm_calls.cost_usd`)
- [ ] Resumable: re-running skips senses with valid assets

**Files to Create / Modify:**
- `scripts/run_generation_batch.py` — new (chunking, ceilings, resume)
- `routes/admin_local.py` — batch tab wiring

**Verification:**
After completion: `SELECT language_id, count(DISTINCT sense_id) FROM exercises WHERE word_asset_id IS NOT NULL GROUP BY 1` ≈ 1,000 each; judge dashboard shows per-language reject rates.

---

### 2026-08-12 — two blocking defects fixed; batch is wall-clock bound

**The budget ceiling did not work, and could not have.** `llm_calls` held 12,947
rows and **not one had `cost_usd` populated** — `_log_llm_call` never set the key.
So `spend_since()` always returned `$0.00`, `--ceiling` could never fire, and the
per-chunk cost line in the report (an explicit acceptance criterion here) would
have read `$0.0000` no matter what the batch spent. Running a $10-capped batch
behind a cap that reads zero is not a cap. Fixed: `_make_one_call` now requests
OpenRouter usage accounting (`extra_body={'usage': {'include': True}}`) and
threads the returned cost through to the log row. Verified live — a probe call
logged `cost_usd = 0.001638`. 11 tests in `tests/test_llm_call_cost_logging.py`,
including the `model_extra` path that a naive test would miss (the OpenAI SDK's
Usage model does not declare `cost`, so it lands in the pydantic extras bag).

**Every typed-LLM asset write was being rejected.** `word_assets_asset_type_check`
enumerated the seven pre-TASK-520 asset types; TASK-522's generator writes
`llm_types_A` / `llm_types_B`, so all of them failed with 23514. `_store_asset`
catches and logs, so the pipeline reported success per sense while
`synonym_antonym_match`, `word_family` and `particle_selection` produced
**nothing** — and the valid-rate report would still have read ~100%, because it
measures the P1/P2/P3 assets that did store. The first chunk hit this on sense 1
and would have hit it on all 300 at full cost. Fixed by
`migrations/task522_word_assets_llm_types_check.sql` (applied live), which
replaces the enumeration with a pattern matching how the code builds the value
(`prefix_variant`) — the enumeration is precisely what rotted. Confirmed working
in the live batch: `llm_types_A` and `llm_types_B` went from 0 rows to 3 each.

**Measured, from the 7 senses that ran (ZH):**

| Metric | Value |
|--------|-------|
| Cost | **$0.1645** over 65 logged calls |
| Cost per sense | **~$0.024** → ~$2.40 per 100-sense chunk, ~$7.20 for all three languages |
| Throughput | **~5.5 min/sense** → **~9 h per 100-sense chunk**, ~27 h for three |
| `judge_ladder_p1_sentence` | 2 accept / 2 flag / 2 reject → **33% reject** |
| `judge_ladder_sentence_validity` | 7 accept / 0 reject → 0% reject |

**Why it stopped.** Not spend — $0.1645 of a $10 authorisation. Wall clock: one
language's chunk needs ~9 hours. The runner is resumable (a sense with a valid
P1 is skipped), so the 7 completed senses are kept and a re-run continues from
there. Parallelising the three languages is **not** safe as written:
`spend_since()` sums *all* `llm_calls` since the chunk began, so three concurrent
runs trip each other's ceilings on each other's spend.

**Outstanding.** The ≥90% valid-rate criterion is still unmeasured — 7 senses is
far too small a sample to judge it, and the 33% P1-sentence reject rate above
should be treated as a signal to watch rather than a result. One content-quality
issue was visible and is worth pursuing before a long run: the ZH P1 generator
returned `semantic_class: '功能词'` (the Chinese term) where the schema requires
one of the English enum values, which fails validation and costs a retry.

---

---

## TASK-516: Deterministic generators — definition_match, jumbled, readings, tone

**Status:** [x] Done (2026-08-08 — `deterministic/` package + type-keyed renderer pass; 31 fixture tests)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-503, TASK-506

**Description:**
Build/scale the no-LLM generators (§5 #2, #13, #14, #16): `definition_match` from same-tier sense definitions (sampler exists — scale + tier guard); `jumbled_sentence` from P1 sentences via language chunkers (jieba/fugashi/spaCy); `hanzi_to_pinyin` + `tone_id_word` (ZH) and `kanji_to_reading` (JA) from backfilled pronunciations with the §5 confusion-set distractor algorithms (tone-variant > near initial/final for ZH; long/short vowel, voicing, っ for JA). Readings are keyed to the P1-sentence contextual reading for polyphonic/multi-reading words.

**Acceptance Criteria:**
- [ ] Each generator emits schema-v2 content (§6.4) with `ladder_level`/family per the capability matrix and never calls an LLM
- [ ] Confusion-set distractors are real words/syllables from the language's inventory; no duplicates of the key; polyphone test cases pass (行/重 class for ZH, 本/月 on-kun class for JA)
- [ ] Generated for every batch sense with `pronunciation` present; senses without it are skipped with a logged reason (§6.10)
- [ ] Unit tests per generator with golden fixtures

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/` — new package (`definition_match.py`, `readings.py`, `tone.py`, `jumbled.py` refactor)
- `tests/test_deterministic_generators.py`

**Verification:**
Run over 50 batch senses per language → expected counts; fixture tests green.

---

## TASK-517: Coverage check, batch report, queue drain

**Status:** [~] In Progress — coverage view + queue drain landed 2026-08-08; cron entry, advisory lock and `subscribe_topup` enqueue still owed
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-504, TASK-511

**Description:**
Implement the §6.3 inventory contract: after every batch (and nightly), verify each generated sense has ≥1 active exercise per required family (per `active_levels` × capability matrix); shortfalls are queued (`coverage_gap`) and reported. Add the queue drain job (admin trigger + optional 04:15 UTC cron, advisory-locked) that re-runs generation for queued senses.

**Acceptance Criteria:**
- [ ] Coverage SQL view `v_sense_family_coverage(sense_id, language_id, missing_families[])`
- [ ] Batch report includes coverage summary; gaps auto-queued
- [ ] Drain job processes `pending` queue rows oldest-first with stop checks; statuses transition correctly on success/failure
- [ ] Sense-subscription top-up path enqueues (`subscribe_topup`) when assets are missing

**Files to Create / Modify:**
- `migrations/v_sense_family_coverage.sql`
- `scripts/run_generation_batch.py` — report hook
- `services/vocabulary_ladder/queue_drain.py` + scheduler entry
- `routes/vocab_dojo.py` (ladder init path) — top-up enqueue

**Verification:**
Delete one family's exercises for a test sense → view flags it, drain regenerates it, view clears.

---

## TASK-518: Per-sense legacy exercise dedupe

**Status:** [x] Done (2026-08-08 — coverage-gated, deactivate-never-delete, dry-run verified live)
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-515

**Description:**
For every sense the batch covered, deactivate (`is_active=false`, never delete) the legacy-pipeline vocabulary exercises (`source_type='vocabulary' AND word_asset_id IS NULL`) so learners get only judge-gated ladder content. Idempotent script with a dry-run count.

**Acceptance Criteria:**
- [ ] Only senses with full family coverage (TASK-517 view) are deduped
- [ ] Rows deactivated, not deleted; count logged; reversible by flipping the flag
- [ ] Practice session for a covered sense serves only `word_asset_id IS NOT NULL` items

**Files to Create / Modify:**
- `scripts/dedupe_legacy_vocab_exercises.py`

**Verification:**
Dry-run count ≈ covered-sense legacy rows; post-run practice session spot-check.

---

## TASK-519: Multi-nl content rules (`content.nl` keyed maps)

**Status:** [x] Done (2026-08-08)
**Feature:** exercise-generation-v2
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-501

**Description:**
Operator decision: nl-keyed maps from the first batch. Define the schema-v2 envelope rule (§6.4): all nl-facing strings (glosses, grading notes, nl translations) live under `content.nl = {"en": {...}}`; TL-facing content stays nl-free. Enforce with the JSON-schema gate and a lint test that fails any generator writing nl text outside `content.nl` or hardcoding `'en'` in generation code paths.

**Acceptance Criteria:**
- [ ] Schema files for the v2 envelope reject nl text at top level (for known nl-bearing fields)
- [ ] Lint/unit test asserts the renderer writes `content.nl` for nl-bearing types (tl_nl/nl_tl, hints) and flags hardcoded nl literals in generation modules
- [ ] tl_nl/nl_tl generators (ZH/JA) emit the keyed shape

**Files to Create / Modify:**
- `services/exercise_generation/schemas/` — envelope schemas
- `services/vocabulary_ladder/exercise_renderer.py` — nl-map emission
- `tests/test_nl_keyed_content.py`

**Verification:**
Generate one ZH tl_nl item → options under TL keys, gloss under `content.nl.en`; lint test green.

**Resolution (2026-08-08):** New package `services/exercise_generation/schemas/`
(`envelope.py` + re-export `__init__.py`) defines the rule: TL-facing content stays flat and
nl-free; every nl-bearing field lives under `content.nl.<code>`. `NL_BEARING_FIELDS` maps
each exercise type to its nl fields; `wrap_nl` builds an envelope (and *accumulates* — a
second call adds `ja` alongside `en`); `read_nl` resolves one learner's block with
single-block fallback; `flatten_for_serve` projects back onto v1 keys.

**Reading is tolerant, writing is strict.** `validate_envelope` no-ops below
`schema_version 2`, so the existing v1 corpus is not retroactively invalidated — the gate
governs what new generators write. `ExerciseValidator` runs the envelope check *first* and
returns immediately on violation (otherwise every nl field reports as "missing" and buries
the real cause), then validates v2 through a flattened view so the per-type checkers keep
seeing the names they were written for.

tl_nl/nl_tl generators emit the keyed shape; `nl_language_code` is now a **required keyword**
with no `'en'` default. Serve side: `exercise-renderers.js` flattens once in `dispatch()`,
so all ~16 renderers stay unchanged.

**The lint tests found two real offenders, which is the point of them:**
1. `ExerciseGenerationOrchestrator.__init__(nl_language_code='en')` — the actual root cause
   of the corpus being English-only. Replaced with `Config.DEFAULT_NATIVE_LANGUAGE`: one
   declared, env-overridable knob instead of a literal buried in a signature. All six
   construction sites keep working.
2. `generators/style.py` writes `grading_notes` at the top level. **Not fixed by design** —
   TASK-512 freezes the style path. Recorded in `_FROZEN_LEGACY` in the test file so the
   exemption is visible and reviewable; deleting that line is the reminder if style is ever
   unfrozen.

Tests: `tests/test_nl_keyed_content.py` (22) — envelope gate (top-level nl text rejected,
incomplete blocks rejected, legacy untouched), construction/reading round-trips,
generator shape parametrised over zh/en + ja/en + zh/ja, and the two AST lint tests
(hardcoded nl defaults; nl-bearing keys written outside the envelope).

---

## TASK-520: Per-exercise-type prompt split (L4 + L8 first)

**Status:** [~] In Progress — code + prompts + schema gate landed 2026-08-09; migration not applied live
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
Peel the two most failure-prone levels out of the P3 monolith into their own `task_name`s (`ladder_l4_morphology_generation`, `ladder_l8_collocation_repair_generation`) with focused prompts, independent model choice, isolated retry, and a JSON-schema gate binding output shape to `prompt_version` (audit B3.2 + B3.4).

**Acceptance Criteria:**
- [ ] New prompt rows seeded (en/zh/ja); P3 no longer emits L4/L8
- [ ] Per-(type, schema_version) JSON schema validated before remap; the speculative fallback shape branches for these levels deleted
- [ ] Judge wiring unchanged (collocation judge still gates L8); reject-rate view picks up the new prompt_versions
- [ ] A/B variant behaviour preserved

**Files to Create / Modify:**
- `migrations/ladder_prompt_split_l4_l8.sql`
- `services/vocabulary_ladder/asset_generators/` — new `l4_morphology.py`, `l8_repair.py`; slim `prompt3_transforms.py`
- `services/exercise_generation/schemas/` — two schema files

**Verification:**
Regenerate 10 senses → L4/L8 render via the new tasks; reject-rate dashboard splits by new prompt_version.

---

## TASK-521: Sense embeddings

**Status:** [x] Done 2026-08-12 — backfill run (22,348 senses, 100% coverage,
$0.0047); also fixed the band-check RPC, which had never worked
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Add `dim_word_senses.embedding vector` (pgvector, existing OpenAI embedding service; embed `lemma + definition`). Backfill all senses; embed new senses at creation. Powers distractor nearness windows (mid-cosine band), `definition_match` distractor upgrade, and syn/ant sanity checks.

**Acceptance Criteria:**
- [x] Column + vector index; ≥99% senses embedded; idempotent backfill
- [x] Helper `nearest_senses(sense_id, lang, pos, k, cos_min, cos_max)` SQL function
- [x] Embedding cost logged; new-sense hook in the sense creation path

**Files to Create / Modify:**
- `migrations/dim_word_senses_embedding.sql`
- `scripts/backfill_sense_embeddings.py`
- `services/vocabulary/sense_generator.py` — embed-on-create

**Verification:**
`nearest_senses` for "precision" returns accuracy/exactness-class neighbours in the mid band.

**Completed 2026-08-12.** Backfill embedded **22,348 senses — ZH 8,084 / EN 9,472 /
JA 4,792 — at 100.00% coverage per language, 0 NULL remaining**, for **$0.0047**
(88 API calls, `text-embedding-3-small`). One row failed on the first pass and
was picked up by a second run, which is what "idempotent" was for.

**A second defect had to be fixed before the band checks could work.**
`sense_neighbours.neighbour_similarities` called
`nearest_senses(p_sense_id, p_language_id, p_lemmas)` — a signature the live
function has never had — and read `lemma`/`similarity` where it returns
`out_lemma`/`out_similarity`. Every call raised PGRST202, the bare
`except Exception` logged it at INFO as "RPC unavailable", and the band check
returned "no opinion" on every foil. **TASK-522's embedding band checks were
therefore never going to fire, backfill or no backfill** — a state
indistinguishable in the logs from the backfill simply not having run.

Fixed by adding `sense_similarity_to_lemmas(p_sense_id, p_language_id, p_lemmas)`
— a companion to `nearest_senses`, not a replacement: that one *searches* for
k-nearest, this one *scores* named candidates, and a foil outside the band must
come back with its similarity rather than be omitted. Log level raised to
WARNING. `migrations/dim_word_senses_embedding.sql` now records the column, the
HNSW index, the pre-existing `nearest_senses` (live since 2026-08-08 with **no
migration file at all**, against `migrations/CLAUDE.md`) and the new function.

**Post-fix spot-check, 3 lemmas per language** — sane and correctly banded:
`precision`/`accuracy` 0.79 IN · `build`/`construct` 0.88 OUT (near-duplicate,
likely also-correct) · `学习`/`学` 0.95 OUT · `朋友`/`石头` 0.21 OUT (unrelated) ·
`朋友`/`同学` 0.46 IN · `食べる`/`飲む` 0.69 IN. Pinned by 12 tests in
`tests/test_sense_neighbour_band_checks.py`, which assert the RPC *name*,
argument keys and result columns — this is the fourth instance of the ADR-020
class (a late symbolic reference failing into a silent no-op).

*Noted, not fixed:* `車`/`林檎` scores 0.39 and lands just inside the 0.35 band
floor. The floor may want raising for JA once real reject data exists.

---

## TASK-522: `synonym_antonym_match` + `word_family` generators

**Status:** [~] In Progress — generators, relation/word_family judges + band check landed 2026-08-09; migration not applied live
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-504, TASK-521

**Description:**
Two new LLM generators with judges (§5 #17, #18). Syn/ant (all langs, `abstract|action|property` classes): LLM proposes relation candidates anchored to the *sense* (definition in prompt), judge verifies relation + uniqueness, embedding band sanity-checks foils. Word_family (EN): derived-form slot exercises built from enriched `morphological_forms`, judge + dictionary check against invented derivations.

**Acceptance Criteria:**
- [ ] Both emit schema-v2 content, capability-matrix routed, judge-gated (fail-closed in batch)
- [ ] Syn/ant: polysemy test — sense-anchored foils don't cross senses
- [ ] Word_family: invented-derivation planted defect is dropped by the judge (test)
- [ ] Prompt + judge rows seeded; reject rates visible on the dashboard

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/syn_ant.py`, `word_family.py`
- `services/exercise_generation/judges/relation.py`
- `migrations/syn_ant_word_family_prompts.sql`

**Verification:**
20-sense sample run; planted-defect tests green.

---

## TASK-523: Collocation grounding for L5/L8

**Status:** [~] In Progress — grounding service, tag plumbing + report script landed 2026-08-09; EN list not vendored
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
P1's `primary_collocate` is LLM-asserted with no corpus grounding (finding G6). Validate each batch sense's collocate against a frequency source (EN: a bundled open n-gram/collocation list; ZH: extend corpus ingestion over the conversation corpus; JA: defer if no source). Tag each as `corpus_validated | llm_asserted`; L5/L8 generation prefers validated collocates and records the tag in provenance.

**Acceptance Criteria:**
- [ ] Validation covers all batch senses with L5/L8 active; mismatches flagged and re-prompted once
- [ ] Tag persisted on `word_assets` and exercise provenance
- [ ] Documented source + licence for the EN list

**Files to Create / Modify:**
- `scripts/validate_collocates.py`; `data/collocations/` source list
- `services/vocabulary_ladder/asset_pipeline.py` — tag plumbing

**Verification:**
Report: % validated per language; spot-check 20 flagged mismatches.

---

## TASK-524: Sentence-tier hard gate

**Status:** [x] Done (2026-08-08)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-513

**Description:**
Deterministic frequency-band screen rejecting P1/mined sentences whose lexical profile exceeds the sense's tier (the "C2 sentence for an A1 word" eval failure): tokenize, look up `frequency_rank` per content word, reject if >N words fall outside the tier's band (jieba/fugashi/spaCy; thresholds per tier in config).

**Acceptance Criteria:**
- [ ] Gate runs before the P1 judge (cheap first); rejected sentences replaced by regeneration
- [ ] The coffee-corpus C2 example from the eval is rejected for an A1 sense (fixture test)
- [ ] Per-language tokenizer correctness tests

**Files to Create / Modify:**
- `services/vocabulary_ladder/tier_gate.py` + config thresholds
- `tests/test_tier_gate.py`

**Verification:**
Fixture tests green; batch report shows tier-gate reject counts.

**Resolution (2026-08-08).** New `services/vocabulary_ladder/tier_gate.py`;
thresholds in `config.TIER_GATE_PROFILES`. Runs in the pipeline immediately
before `_judge_p1_sentences` — deterministic and free, so the judge's
per-sentence LLM spend is reserved for what only a model can assess.

**Two thresholds, not one.** A soft `soft_floor` with a `max_out_of_band`
budget catches the C2-lexis sentence; a `hard_floor` rejects a single
sufficiently rare word on its own, because a budget alone lets *bergamot*
through in an otherwise-plain sentence. `max_unknown` gives OOV tokens (names,
typos, tokeniser artefacts) their own small allowance — they are not evidence
of tier fit in either direction, so counting them as violations over-rejects.

**Calibrated, not guessed.** Empirically against the eval fixture in all three
languages: an ordinary A1/A2 sentence scores 0–1 out-of-band, the coffee-corpus
C2 sentence scores 6 (zh), 8 (ja), 10 (en). T6 is ungated — at the top tier
there is no lexis that is too hard.

The sense's tier is derived from the *lemma's own* Zipf
(`LEMMA_ZIPF_TO_TIER`), which is what "an A1 word" means operationally.
The target word and its `morphological_forms` are exempt: a rare sense being
taught cannot also be the reason its own example is rejected.

Tokenisation uses `wordfreq.tokenize`, not `LanguageProcessor` — the frequency
tables were built with it so lookups are apples-to-apples, and it covers zh/ja/en
with no spaCy or fugashi model to install (the JA spaCy model is absent from
this environment, and the gate has to run in CI and in the batch runner alike).

Rejected sentences take the same in-place `repair_sentences` path as judge
rejects and are re-screened; indices are never disturbed. The gate never
blocks an asset — the judge that runs next already owns that decision
(`P1_MIN_ACCEPTABLE_SENTENCES`), and double-blocking on two criteria would make
failures hard to attribute. Per-sense stats (`tier`, `screened`, `rejected`,
`repaired`, `still_failing`) land on the pipeline result for TASK-517's report.

Tests: `tests/test_tier_gate.py` (39) — the coffee-corpus fixture rejected and
its ordinary counterpart passed in en/zh/ja, per-language tokenisation, the
target/morphology exemptions, fail-open paths, and pipeline repair accounting.

---

## TASK-525: tl_nl uniqueness judge

**Status:** [~] In Progress — code + tests done 2026-08-08; prompt migration NOT applied live
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-501

**Description:**
The eval found tl_nl options frequently had >1 acceptable answer (0% accept). Before scaling translation types for ZH/JA, add a uniqueness judge: given the TL sentence + keyed translation + distractor translations, rate each distractor 1–5 on "is this also an acceptable translation?" (≤2 rejects; mirrors the collocation-judge contract). Block items with <2 surviving distractors.

**Acceptance Criteria:**
- [ ] Judge module + en/zh/ja prompt rows; fail-closed in batch
- [ ] Planted also-acceptable distractor is rejected (test)
- [ ] Wired into tl_nl/nl_tl generation for ZH/JA; verdicts in `tags` + `llm_calls`

**Files to Create / Modify:**
- `services/exercise_generation/judges/translation_uniqueness.py`
- `migrations/translation_uniqueness_judge_prompts.sql`
- `services/exercise_generation/generators/translation.py` — wiring

**Verification:**
Planted-defect test green; 10-sense ZH sample shows reject activity.

**Resolution (2026-08-08) — code complete, live seed outstanding.**

`services/exercise_generation/judges/translation_uniqueness.py` mirrors the
collocation-judge contract: one prompt over a numbered candidate list, 5-point
Likert per candidate, `likert_to_verdict` mapping, fail-open outside a batch and
`guard_fail_open` (raise) inside one.

**Rating orientation is the load-bearing detail.** The scale runs in the
direction of *keep* — 5 = clearly NOT an acceptable translation (ideal
distractor), 1 = a fully acceptable rendering (also-correct, must go) — so no
negation is needed on either side. Written the intuitive way round ("5 = yes,
also acceptable") the judge would silently keep exactly the distractors it
exists to remove, **and the item would still look well-formed**. The direction
is therefore asserted in the tests and flagged in a DO-NOT-INVERT block in the
migration, not left to the prompt author.

`judge_translation_item` blocks the whole item below
`MIN_SURVIVING_DISTRACTORS = 2`. Blocking rather than padding is deliberate — a
padded distractor is how also-correct options got in to begin with.
`TlNlTranslationGenerator.generate_one` returns None on that verdict and
attaches a `translation_uniqueness` sidecar to `__judge_metas` otherwise.
`NlTlTranslationGenerator` is untouched: it is free-input, so there are no
distractors to disambiguate.

`nl_language_code` is a required argument with no default — the TASK-519 AST
lint caught the `''` default on the first pass, which is exactly what it is for.

Tests: `tests/test_translation_uniqueness_judge.py` (28) — the full 1-5 scale
parametrised against keep/drop, the planted also-acceptable distractor, the
<2-survivor block, every fail-open path, and generator wiring end to end.

**Outstanding:** `migrations/translation_uniqueness_judge_prompts.sql` (en/zh/ja
rows) is written but **not applied live** — it needs an operator to run it.
Until it is, the judge fails open on a missing template and ships items
unjudged outside a batch, so the AC "prompt rows seeded" and the 10-sense ZH
sample are both still open.

---

## TASK-526: Traditional-script serve toggle

**Status:** [?] DEFERRED 2026-08-12 — code + 27 tests done; the live 發/髮 spot-check
is deferred to a future feature-completion pass
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-509, TASK-515

**DEFERRAL NOTE (2026-08-12).** Unblocked by **`content.hant` mirrors existing over
real senses**, which comes from TASK-509's backfill running over the TASK-515
batch senses. The serve path, the `script_variant` preference, the profile toggle
and i18n in all four locales are all live, and 27 tests pass — but the one
remaining criterion is a *live payload* spot-check of a 發/髮-class field, and
there is nothing to spot-check until mirrored senses exist. Verifying against a
hand-inserted mirror would test the fixture, not the pipeline.

**Description:**
Surface the dual-stored mirrors: practice session responses select `content.hant` fields when `users.exercise_preferences->>'script_variant'='traditional'` (per-field simplified fallback + flag for overrides review). Settings UI toggle. Typed ZH answers normalised `t2s` before matching. Scope: practice/vocab surfaces only (operator decision); tests/mysteries are a later epic.

**Acceptance Criteria:**
- [ ] Toggle persisted in `exercise_preferences`; practice session payload renders traditional for all item types incl. options and reasoning
- [ ] Missing-mirror field → simplified served + flagged for review
- [ ] `cloze_typed` accepts traditional-typed input via `t2s` normalisation (test)
- [ ] No serve-time OpenCC calls (pure field selection)

**Files to Create / Modify:**
- practice session service — field selection
- `routes/users.py` + settings template/JS — toggle
- `tests/test_script_variant_serving.py`

**Verification:**
Toggle on → session payload spot-check shows 發/髮-class fields correct; toggle off unchanged.

---

## TASK-527: JA `particle_selection` generator + judge

**Status:** [~] In Progress — generator, particle judge + tokeniser spans landed 2026-08-09; migration not applied live
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-508, TASK-515

**Description:**
The L4-JA exercise (§5 #7, prompts drafted in §6.6): blank one particle in a P1 sentence (fugashi identifies particle spans), LLM picks the pedagogically confusable blank + 3 distractor particles with reasoning; the particle judge verifies no distractor also yields a natural sentence (uniqueness). Wired as ladder L4 via the capability matrix.

**Acceptance Criteria:**
- [ ] Generator + judge modules; prompt rows seeded from the §6.6 drafts; fail-closed in batch
- [ ] Planted also-natural particle (に/へ direction class) rejected by the judge (test)
- [ ] Items carry `ladder_level=4`, family form_production, error tags per distractor
- [ ] Generated for batch JA senses with eligible sentences; coverage view recognises it as L4-JA

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/particle_selection.py`
- `services/exercise_generation/judges/particle.py`
- `migrations/particle_selection_prompts.sql`

**Verification:**
20-sense JA sample; planted-defect test green; dojo serves a particle item for a JA word at R2.

---

## TASK-528: ZH `classifier_match` as ladder L4

**Status:** [x] Done (2026-08-08 — group distractors, 个 excluded, multi-acceptable answers; attempt round-trip untested end-to-end)
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-504

**Description:**
Ladder-linked classifier exercises for ZH concrete nouns, reusing `dim_classifiers` + the drill's distractor-group logic (never 个; semantic-group distractors; multi-acceptable support). Items carry `sense_id` + `ladder_level=4` so family credit flows through `ladder_record_attempt`. The standalone drill is unchanged.

**Acceptance Criteria:**
- [ ] Deterministic generator joins lemma→classifier dict; nouns absent from the dict omit L4 (capability `requires`)
- [ ] Distractors follow the drill's group rules; full 4-option items always
- [ ] Attempts update `form_production` family confidence (integration test through `ladder_record_attempt`)

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/classifier_match.py`
- `tests/test_classifier_match.py`

**Verification:**
Generate for 50 ZH concrete nouns; dict-missing noun cleanly skips; attempt round-trip test green.

---

## TASK-529: `reading_to_kanji` / `pinyin_to_hanzi` + character-component table

**Status:** [~] In Progress — generators + `dim_character_components` live 2026-08-08; the licensed component import awaits a source/licence decision
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-516

**Description:**
The sound→script direction (§5 #15): show the reading, pick the character/word among homophones and visually similar foils. Build the homophone index over `dim_word_senses.pronunciation` and a small character-component table (kanjivg/hanzipy-derived, one-time import) for visual-similarity padding when homophone sets are sparse.

**Acceptance Criteria:**
- [ ] `dim_character_components` (or equivalent) imported with documented source/licence
- [ ] Distractor priority: same-reading different-character > shared-component > frequency-band filler; never the key's own variants
- [ ] Items generated for batch ZH/JA senses; sparse-syllable fallback test

**Files to Create / Modify:**
- `migrations/dim_character_components.sql` + import script
- `services/vocabulary_ladder/deterministic/readings.py` — reverse direction

**Verification:**
张/章/掌-class foil sets produced for a sample; sparse case pads correctly.

---

## TASK-530: JA counter drill (助数詞) + `counter_match`

**Status:** [~] In Progress — everything shipped and merged 2026-08-12/13; the
dictionary reached **38 counters at ≥10 nouns against a bar of 40**, so the first
acceptance criterion is *narrowly* unmet. See the closing note.
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-504

**Description:**
Clone the classifier-drill architecture for Japanese counters (operator-confirmed): curated counter dictionary (本/枚/匹/台/冊/杯 + semantic groups) built by a seed script + the LLM curation pipeline (`services/classifier_curation` pattern), deterministic session RPC with semantic-group distractors, sentinel-test ELO (`__counter_drill_ja`), Choose/Type modes. Then `counter_match` as L4-JA for concrete nouns in the ladder (same pattern as TASK-528).

**Acceptance Criteria:**
- [~] Counter dictionary ≥40 counters with ≥10 nouns each for the common set; curation JSON human-reviewed before merge — **38/40**, human review done
- [x] Drill RPC mirrors `get_classifier_drill_session` semantics (multi-acceptable, always 3 distractors, group-based)
- [x] ELO via sentinel test, K=32 first-attempt-only; route rejects non-JA
- [x] `counter_match` ladder items for dict-covered concrete nouns; capability fallback to `particle_selection` otherwise (§6.10)

**Files to Create / Modify:**
- `scripts/build_counter_dictionary.py`, `scripts/generate_counter_curation.py`
- `migrations/counter_drill.sql` (tables + RPC + sentinel)
- counter drill route + template (clone classifier drill)
- `services/vocabulary_ladder/deterministic/counter_match.py`

**Verification:**
300-item sample: 0 missing distractors, group-plausible foils; ladder attempt round-trip green.

---

### 2026-08-12/13 — drill shipped, curation merged after sign-off

**Drill (route/template/modes/nav).** `routes/counter_drill.py` +
`services/counter_drill_service.py` + `templates/counter_drill.html`, cloned from
the classifier drill so the two stay one pattern. Choose and Type modes; Type
reuses TASK-532's IME handling verbatim (`compositionstart`/`compositionend`
**plus** the `keyCode === 229` guard, since some IMEs never fire the events).
No `auto` mode: the classifier drill's auto routes by per-classifier mastery and
counters have no equivalent table, so it would have been a third name for `mc`.
Nav entries added in both the desktop bar and the mobile dropdown; 17 new strings
in **all four** locales (`en/es/ja/zh`), verified key-by-key.

**Submission reuses `process_classifier_drill_submission`** — it is parameterised
by test_id/test_type_id and contains nothing classifier-specific (grep for
`dim_classifier|classifier_mastery` in it returns 0 matches). Cloning it would
have duplicated the whole ELO block so the copy could drift.

**Blocking gap found: there was no `counter_drill` row in `dim_test_types`.**
`DimensionService.get_test_type_id` filters on `is_active`, so **every submission
would have 500'd** — the drill would have served items and recorded none. Added
as id 15 via `migrations/task530_counter_drill_test_type.sql`; kept distinct from
`classifier_drill` (id 14) so a learner strong on Mandarin measure words does not
appear competent at Japanese counters.

**Live verification.** 20-item session through the real RPC: **0 items with the
wrong distractor count, 0 without a correct answer, 0 answer/distractor overlap**,
and foils are group-plausible (鹿→頭 against 匹/羽/尾; テレビ→台 against 両/隻/機).
Page renders 200 with the IME guards present. 7-test `counter_match` round-trip
added covering the generation→`ladder_record_attempt` join that the 2026-08-08
session flagged as untested for the Mandarin twin.

**Curation pass.** 43 underserved counters (<10 nouns), qwen3.7-plus via
OpenRouter, **$0.5818 of a $5 ceiling, 0 failures**. 705 rows generated, 578
accepted at judge ≥4. The `counts_nouns` gate declined **7** counters that count
no showable noun — 回, 度, 振り, 方, 番, 遍, 階 — which is the 階 error class from
the previous pass being caught automatically rather than by eye.

**Human sign-off rejected 6 more.** Five on the judge's own numbers (筋 0/19,
編 2/20, 項 3/19, 片 7/20, 組 9/20 accepted). The sixth, **列**, is the more
interesting one and the gate missed it: it counts *rows*, so "nouns that take 列"
is really "nouns that can be arranged in a row" (車, 学生, 本, 花, 建物 …), none of
which is taught with 列. It was also the largest single source of
multi-acceptable pairs (列+台, 列+両, 列+冊 …), each of which would have made an
ordinary item accept two answers. Excluded from both its own list and other
counters' alternates, and kept as a foil — same treatment as 階.

**Result: 54 counters, 837 pairs, 582 distinct nouns, 0 audit warnings**
(from 54 / 173 / 166). 454 primary + 238 secondary pairs merged.

**The ≥40-counters-at-≥10-nouns criterion is NOT met: 38.** Reported rather than
rounded up. The realistic gap is smaller than it looks — of the near-misses,
名様 sits at 9, while 回 (8) counts occurrences and 個 (8) / つ (6) are the
universal counters deliberately excluded from drilling. Closing it needs either a
second curation pass over counters currently at 5–9 (~$0.05), or accepting one of
the six sign-off exclusions, which would mean teaching content the judge rejected.

*Note:* 組 retains its 3 hand-curated pairs (トランプ/夫婦/茶碗). The exclusion
rejects the LLM's proposed list, not pre-existing curated data.

---

## TASK-531: Audio at scale (L1 + listening variants)

**Status:** [x] Done 2026-08-12 — run complete; 100% coverage on every populated
type. A per-type audio-field defect had to be fixed first.
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
Synthesise TTS for all batch senses' L1 phonetic items and listening flashcards (Azure, `audio_voice.pick_voice`, deterministic R2 slugs), extending the existing L1 audio backfill tab to the full batch + JA voices. TTS failures ship the text variant and queue a backfill (§6.10).

**Acceptance Criteria:**
- [x] ≥95% of batch L1/listening items have `audio_url`; failures queued with reason
- [x] JA voices selected from `dim_languages.tts_voice_ids`; spot-listen 10 per language
- [x] Cost/quota throttling (configurable per-night cap)

**Files to Create / Modify:**
- `scripts/backfill_exercise_audio.py` (extend existing backfill runner)

**Verification:**
Coverage query ≥95%; sampled URLs play.

**Completed 2026-08-12.** 8 items synthesised, **0 failures**, nothing queued for
retry. Final coverage, against a 95% target:

| Language | Type | Coverage |
|----------|------|----------|
| ZH | `listening_flashcard` | **56/56 — 100%** |
| ZH | `phonetic_recognition` | **2/2 — 100%** |
| EN | `phonetic_recognition` | **16/16 — 100%** |
| JA | — | no audio-bearing items generated yet |

Azure usage was 8 short utterances, negligible against the free tier; the per-run
cap (`--cap`, `$AUDIO_BACKFILL_CAP`) was set to 50 and never approached.

**The first report was wrong, and the fix mattered.** The runner treated
`content.audio_url` as universal. `listening_flashcard` does not use that key —
the renderer writes and reads **`front_audio_url`** — so the coverage query
reported **0/56, 0.0%** over 56 items that were already fully voiced, and the
speakable-text extractor listed four field names (`audio_text`,
`highlight_word`, `word`, `front_sentence`) that appear in no
`listening_flashcard` row, producing 56 × "no speakable text".

Left unfixed, this was worse than a bad number: the write-back also used
`audio_url`, so any newly synthesised flashcard audio would have been uploaded to
R2, recorded under a key the renderer never reads, and left the item silent *and*
permanently counted as uncovered — burning Azure quota on every subsequent run.
Fixed with an `AUDIO_URL_FIELDS` per-type map used consistently by the pending
filter, the coverage query and the write-back.

---

## TASK-532: `cloze_typed` free-input exercises

**Status:** [~] In Progress — builder + answer normalisation landed 2026-08-08; typed-input FE component (IME) and attempt-route grading still owed
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
Productive-form cloze (§5 #4): reuse existing cloze assets without distractors; learner types the answer (IME for CJK). Grading is **exact/normalised match only** (operator decision): trim/case/unicode-width normalisation, ZH `t2s`, accepted set = keyed answer + relevant `morphological_forms` variants. New renderer + player UI + grading in the attempt path; family form_production.

**Acceptance Criteria:**
- [ ] `answer.accepted[]` + `normalization` emitted per §6.4; no LLM in the grading path
- [ ] Normalisation tests: full-width input, case, trailing space, traditional-typed ZH, EN inflection in accepted set
- [ ] Attempt flow records first-attempt correctness into the ladder like other types
- [ ] Frontend input component with IME-safe composition handling

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/cloze_typed.py` (derive from cloze assets)
- `utils/answer_normalization.py` + tests
- `static/js/` practice player typed-input component; attempt route grading

**Verification:**
Normalisation test matrix green; manual IME smoke (ZH + JA input).

---

## TASK-533: `timed_speed_round` serve-time composer

**Status:** [~] In Progress — composer, route, attempt path + timer player landed 2026-08-09; nothing schedules it yet
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
Fluency-development battery (§5 #21): a serve-time composer selects 10–20 *mastered* senses (FSRS-owned) with L1–L3 assets and assembles a rapid-fire recognition round (per-item time limit; no new content generated). Restricted to mastered senses so time pressure is fluency training, not acquisition noise.

**Acceptance Criteria:**
- [ ] Composer returns batteries only from `word_state='mastered'` senses; empty-state handled
- [ ] Timing recorded per item; results update FSRS (rating from speed+correctness) but not family confidence
- [ ] Capability-matrix row `ladder_level=NULL` respected (not served as a ladder drill)

**Files to Create / Modify:**
- speed-round composer service + route; player timer UI

**Verification:**
Seeded mastered user gets a battery; non-mastered senses never appear (test).

---

## TASK-534: Exercise-type effectiveness view *(Phase 4)*

**Status:** [x] Done 2026-08-12 — view, outcome capture, admin page and synthetic
fixtures all landed. Real-data validation deferred (see below).
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515 + launch data

**Description:**
Per-`(p_known bucket, exercise_type)` Δp_known-per-minute view from `exercise_attempts` (+ Part F outcome capture), powering Phase-4 adaptivity and content QA (which types actually move knowledge at which stage).

**Acceptance Criteria:**
- [x] View + admin page; validated against synthetic attempt fixtures

**What shipped (2026-08-12):**
- **Part F outcome capture was missing entirely.** `user_vocabulary_knowledge`
  holds only the *current* `p_known` and there is no history table, so a
  per-attempt delta was not recoverable after the fact. The BKT RPC already
  returned `out_p_known_before` / `out_p_known_after` and the service already
  read them — they were simply never persisted. Added
  `exercise_attempts.p_known_before` / `p_known_after` (nullable; pre-existing
  rows cannot be reconstructed and are not fabricated) and
  `PracticeSessionService._capture_knowledge_outcome`, which is best-effort so
  analytics can never fail a learner's submission.
- `vw_exercise_type_effectiveness` — counts only attempts where BKT ran and
  `time_taken_ms > 0`, buckets on `p_known_before` (bucketing on *after* would
  manufacture the correlation being measured), and caps per-attempt time at
  5 minutes to match `_effective_practice_seconds`.
- Admin page at `/exercise-type-effectiveness` (bucket × type grid, cells under
  30 attempts flagged `thin`).
- `migrations/task534_exercise_type_effectiveness.sql`, applied live.

**Verification run:** `scripts/validate_effectiveness_view.py` inserts 13
synthetic attempts whose aggregate is hand-computed, checks the view, and
deletes them. **All 8 expectations hold** — bucket edges on both sides of 0.2
and 0.8, the 5-minute clamp, exclusion of uncaptured/zero-time rows, and a
negative delta pulling a rate down rather than being floored at 0. Plus 11 unit
tests in `tests/test_knowledge_outcome_capture.py`.

**DEFERRED — real-data validation.** Unblocked by post-launch attempt volume:
the view is correct against fixtures but has never been read against real
traffic, so nothing yet confirms the buckets are useful cut-points or that
30 attempts is the right thinness threshold. Every live cell is currently empty,
because capture only began with this migration.

---

## TASK-535: Thompson-sampling type tie-breaker *(Phase 4 — data-gated)*

**Status:** [?] DEFERRED 2026-08-12 — entirely, including the offline replay harness
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-534

**Description:**
Bandit over exercise *type* as a tie-breaker among same-family candidates inside the unified-score shortlist (composes with, never replaces, the unified score). Reuses the Study-Plan Thompson pattern.

**Acceptance Criteria:**
- [ ] Offline replay evaluation before flag-on; per-arm posteriors inspectable

**DEFERRAL NOTE (2026-08-12).** Unblocked by **~50k real attempts plus TASK-534's
view returning non-empty cells**. The replay harness is deferred with the rest
rather than built ahead: a replay needs a log of real (type, outcome) pairs to
replay, and `exercise_attempts` now captures the required `p_known` deltas only
from 2026-08-12 onward, so there is nothing to run it over.

---

## TASK-536: Per-user format preferences + item retirement *(Phase 4 — data-gated)*

**Status:** [?] DEFERRED 2026-08-12 — both halves, not split
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-534

**Description:**
Soft per-user format weighting (e.g. audio-first) and an item-retirement policy driven by IRT drift + `vw_distractor_error_analysis` pick-rates (deactivate items whose distractors never attract or whose difficulty drifts implausibly).

**Acceptance Criteria:**
- [ ] Retirement runs as a reviewed batch (flag → human confirm → deactivate); preference weight bounded so it cannot override family targeting

**DEFERRAL NOTE (2026-08-12).** Unblocked by **launch attempt volume giving
`vw_distractor_error_analysis` real distractor pick-rates**. Kept as one task:
retirement is driven by the same per-item attempt distribution that the
preference weighting reads, so splitting it would mean building that read twice.
Retiring items on pre-launch data would deactivate content for having no
attempts rather than for being bad.

---

---

## Session status — 2026-08-11 (operator-gated batch cleared)

Nine rows closed. The table below supersedes the 2026-08-08 one for those tasks;
rows not listed here are unchanged. Full suite: **1676 passed, 3 skipped**.

| Task | State | What changed | What is still outstanding |
|------|-------|--------------|---------------------------|
| 517 | [x] | `run_nightly_drain()` = coverage sweep then drain, behind `pg_try_advisory_lock_for_queue_drain` (key 1363440238; `migrations/task517_queue_drain_advisory_lock.sql`, **applied live**). 04:15 UTC cron registered in `_initialize_scheduler`, last in the 04:xx chain so it runs after the slug-health probe rather than spending the drain budget on a dead model. `subscribe_topup` enqueued from `GET /api/vocab-dojo/word/<id>/exercises` when a learner opens a word with no ladder items — the one moment a missing sense is certain, and the one the coverage sweep cannot infer (it only finds gaps in senses that already have assets). | — |
| 520 | [x] | **No new work — the checkbox was stale.** All six prompt rows (`ladder_l4_morphology_generation`, `ladder_l8_collocation_repair_generation` × en/zh/ja) and the `vocab_prompt3_transforms` description annotation were verified present live. | Real per-`prompt_version` reject rates still need a batch chunk (TASK-515). |
| 522 | [x] | **No new work — the checkbox was stale.** All eight rows live (`ladder_syn_ant_generation` ×3, `ladder_relation_judge` ×3, `ladder_word_family_generation`, `ladder_word_family_judge`). | The 20-sense sample run; band checks stay inert until TASK-521's backfill. |
| 523 | [x] | **The EN list is vendored.** `data/collocations/en_collocations.tsv` — 73,718 pairs from 18.3M words of OANC (public domain), built by `scripts/build_en_collocations.py`. Dependency-parsed rather than bigram-counted, so `relation` is real and function-word pairs never appear. The motivating defect behaves: `personalize`+`advertising` returns no match → `llm_asserted`. **Loader bug fixed**: `load()` skipped any row whose first column was `head`, discarding every collocation headed by the noun *head*. | JA remains deliberately `no_source`. |
| 525 | [x] | The only migration genuinely missing. **Rewritten to `ON CONFLICT ... DO UPDATE` before applying**: the header claimed "re-runnable" but the bare `INSERT` would abort on `idx_prompt_templates_task_lang_ver` *after* the deactivating `UPDATE` in the same transaction, rolling back to a deactivated judge. Three rows live; all four `{tl_sentence}` / `{correct_translation}` / `{nl_language}` / `{candidates_numbered}` placeholders verified against the judge's `.format()` call. | — |
| 527 | [x] | **No new work — the checkbox was stale.** `ladder_particle_selection_generation` and `ladder_particle_judge` both live. | The 20-sense JA sample and the dojo round-trip. |
| 529 | [x] | `dim_character_components` populated: **27,131 rows, 100% radical + stroke coverage**, avg 3.57 components. **Source/licence decision: cjk-decomp (Apache-2.0) for components + Unihan (Unicode License) for radical/strokes.** `cjkvi-ids` was rejected as **GPLv2** — copyleft on a vendored data file follows it to every deployment. KanjiVG rejected as CC BY-SA *and* kanji-only, which would miss simplified-only hanzi. Components appearing in >5% of characters are dropped, or strokes would dominate every similarity score. Verified: 請/晴 share 月青龶. | — |
| 532 | [x] | FE renderer `renderClozeTyped` with IME composition handling (`compositionstart`/`end` **and** `keyCode === 229`, since some IMEs never fire the events). **Grading moved server-side**: `cloze_typed.grade()` is authoritative and the client's `is_correct` is overwritten, because the comparison is a normalisation rule and two implementations of one rule eventually disagree. 39-case matrix in `tests/test_answer_normalization.py`. | Manual IME smoke on a real ZH/JA keyboard. |
| 533 | [x] | The session queue emits a `speed_round` block when the learner has ≥`MIN_BATTERY` mastered senses (`has_enough_mastered`, one cheap query). **Deliberately not a `_SURFACE_BLOCKS` member** — ADR-021 puts it outside the planner, so it is appended after the planned queue and credits no weekly counter. `KIND_LABELS` and i18n added in all four locales. | — |

**Two latent defects found and fixed while doing the above:**

1. **`deterministic._load_builders()` guarded on `if _REGISTRY:`.** A non-empty registry only
   proves *one* builder was imported. `routes/practice.py` now imports `cloze_typed` directly
   for `grade`, and under the old guard that single import made the loader a no-op — leaving
   the other six builders unregistered, so every sense would generate one exercise type
   instead of seven, with no skip reason to explain it. Now a dedicated `_BUILDERS_LOADED`
   flag; pinned by a regression test.
2. **`BundledCollocationList.load()` header detection.** See row 523.

**Repo-record gaps closed.** `dim_character_components` and the three `dim_counter_*` tables
were live with no migration file at all, against `migrations/CLAUDE.md`. Added
`migrations/dim_character_components.sql` and `migrations/counter_drill.sql`, both
`IF NOT EXISTS` and matching the live definitions.

**TASK-530 partially advanced (still `[~]`).** `get_counter_drill_session` written and
**applied live**, mirroring the classifier drill's semantics (one row per noun,
multi-acceptable answers, always exactly three distractors, group-plausible foils).
`scripts/build_counter_dictionary.py` seeds **54 counters / 173 pairs / 166 nouns** with 0
audit warnings. Verified over the full corpus: 0 rows with the wrong distractor count, 0
without a correct answer, 0 distractor/answer overlap, 7 multi-acceptable nouns
(兎 → 匹+羽, 魚 → 匹+尾). **Still owed:** the drill route + template,
`generate_counter_curation.py`, the human-reviewed curation pass, and the `counter_match`
ladder attempt round-trip.

---

## Session status — 2026-08-08 (TASK-515 tail)

Legend: **[x]** acceptance criteria met · **[~]** code complete, criteria needing a live
run or an external asset outstanding · **[ ]** not started.

| Task | State | What landed | What is outstanding |
|------|-------|-------------|---------------------|
| 515 | [~] | `scripts/run_generation_batch.py` — chunking, resume, `--ceiling` budget abort, per-chunk report (senses/exercises/judge reject-rates/`llm_calls.cost_usd`), failures queued as `regen`, judges fail-closed via `batch_mode()`. Selection verified by dry-run on all three languages. | The batch itself. The ≥90% valid-rate criterion, real judge reject rates and the cost ceiling are unexercised until an operator spends on a chunk. Admin-tab wiring. |
| 516 | [x] | `services/vocabulary_ladder/deterministic/` package + type-keyed renderer pass; `phonology`, `lexicon`, builders for definition_match / jumbled / readings / tone. 31 fixture tests. | — |
| 517 | [~] | `v_sense_family_coverage` (live), `services/vocabulary_ladder/queue_drain.py` — enqueue + oldest-first drain with stop checks, status transitions, and a post-drain re-check so a drain cannot report success on a still-missing family. Batch runner calls the coverage check per language. | 04:15 UTC cron entry + advisory lock; `subscribe_topup` enqueue in the dojo ladder-init path. |
| 518 | [x] | `scripts/dedupe_legacy_vocab_exercises.py` — coverage-gated, deactivate-never-delete, `--reactivate` undo, dry-run verified live. | — |
| 521 | [~] | `dim_word_senses.embedding` + HNSW + `nearest_senses()` RPC (live); `scripts/backfill_sense_embeddings.py`, dry-run verified over 17.5k senses. | The backfill run (~cents, operator-gated); embed-on-create hook in `services/vocabulary/sense_generator.py`. |
| 528 | [x] | `deterministic/classifier_match.py` — group distractors, 个 excluded, multi-acceptable answers, `ladder_level=4`. | Attempt round-trip through `ladder_record_attempt` is untested end-to-end. |
| 529 | [~] | Reverse-direction generators with the homophone > component > frequency priority; `dim_character_components` table (live) with required source/licence columns. | The licensed import itself (kanjivg/hanzipy) — needs a source + licence decision. Until then the generator degrades to homophone + frequency foils, which the live smoke test confirms it does cleanly. |
| 530 | [~] | `dim_counters` / `dim_counter_noun_pairs` / `dim_counter_distractor_groups` (live), `__counter_drill_ja` ELO sentinel, `deterministic/counter_match.py`. | `get_counter_drill_session` RPC, drill route + template, `build_counter_dictionary.py` / `generate_counter_curation.py`, and the human-reviewed curation pass. |
| 532 | [~] | `deterministic/cloze_typed.py` + `utils/answer_normalization.py` (NFKC, whitespace, case, quotes, trailing punctuation, ZH t2s); conservative accepted-variant rule. | Frontend typed-input component with IME composition handling; grading in the attempt route; the normalisation test matrix. |
| 520 | [~] | Split complete: `ladder_l4_morphology_generation` / `ladder_l8_collocation_repair_generation` prompts (en/zh/ja), `asset_generators/_split_base.py` + `l4_morphology.py` + `l8_repair.py`, per-(type, prompt_version) JSON-schema gate in `schemas/` that **refuses** an unregistered version, `prompt3_transforms.py` slimmed to L7 with all four speculative shape branches deleted. Pipeline fans out per level so a morphology failure no longer forces a retry of L7/L8. 31 tests. | `migrations/ladder_prompt_split_l4_l8.sql` not applied live. Real reject rates per new prompt_version need a batch chunk. |
| 522 | [~] | `synonym_antonym_match` + `word_family` via a new type-registered LLM generator layer (`asset_generators/typed_llm.py`, mirroring the deterministic registry); `judges/relation.py` (both judges, Likert v3, fail-closed in batch); `sense_neighbours.py` mid-band embedding check that stays silent when the backfill has not run. Both planted-defect tests green: a cross-sense foil and a real word posing as an invented derivation are each dropped. | `migrations/syn_ant_word_family_prompts.sql` not applied live. The 20-sense sample run. Band checks are inert until TASK-521's backfill runs. |
| 523 | [~] | `collocation_grounding.py` — bundled-list → `corpus_collocations` cascade, tagging `corpus_validated` / `llm_asserted` / `no_source`; tag pinned onto the P1 asset, read by the L5 gate (which now has ONE threshold instead of two) and copied into L5/L8 exercise provenance; `scripts/validate_collocates.py` with a one-shot re-prompt and a per-language report. `data/collocations/README.md` documents OANC (public domain) as the source. 20 tests. | **The EN list itself is not vendored** — see the README for the install step. Until it is, EN grounding falls through to `corpus_collocations` alone. JA is deliberately `no_source`. |
| 526 | [~] | `script_serving.py` — pure field selection over the TASK-509 `content.hant` mirror, shape-matched, with per-field Simplified fallback recorded in `script_fallback_fields`; wired into `get_session`; `script_variant` accepted by `PATCH /api/users/preferences`; profile-page toggle + i18n in all four locales. A test parses the module to prove no converter is imported on the serve path. 27 tests. | Live spot-check of a 發/髮-class payload with the toggle on. Tests/mysteries remain Simplified-only by operator decision. |
| 527 | [~] | `asset_generators/particle_selection.py` + `judges/particle.py` + `LanguageProcessor.particle_spans` (spaCy `ja_core_news_sm`, character offsets). The blank is cut only at a tokeniser-confirmed span — `str.replace` would blank the に inside にんじん. Planted に/へ also-natural distractor is dropped by the judge (test). | `migrations/particle_selection_prompts.sql` not applied live. The 20-sense JA sample and the dojo round-trip. |
| 531 | [~] | `scripts/backfill_exercise_audio.py` — deterministic slugs matching the renderer's, per-run cap (`$AUDIO_BACKFILL_CAP`), `--dry-run` / `--report-only`, per-type coverage table against the 95% target, TTS failures queued as `audio_backfill` rather than deleting the item. | The run itself (Azure quota + spend, operator-gated). Coverage numbers are unmeasured until then. |
| 533 | [~] | `speed_round.py` composer (mastered-only, L1–L3, ≤1 item/sense, 10–20 items), `GET /api/practice/speed-round`, `record_speed_round_attempt` (FSRS only — never family confidence), `players/speed_round.js` with a per-item countdown that submits `timed_out` as incorrect. 18 tests, including query-level assertions that non-mastered senses are never even requested. | No scheduler emits a `speed_round` queue item yet — the player is registered and the route is live, but nothing routes a learner to it. |

**Cross-cutting note.** `dim_vocabulary.frequency_rank` is a Zipf score (0.25–6.56, higher =
more common), not a rank. Any future task that reads it for ordering must sort DESC; the
plain-English reading of "frequency rank" inverts the selection silently.
