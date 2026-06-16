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

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-502, TASK-505

**Description:**
Classify every lemma (EN + ZH + JA, ~10k after JA bootstrap) into the ratified 6-value enum with a cheap LLM batch (flash-tier, batched ~50 lemmas/call, prompt includes POS + definition as context). Record `gen_confidence`; low-confidence rows default to `abstract` and are flagged. This unlocks `active_levels` routing — without it every word gets all 9 levels (the eval's "bean" failure).

**Acceptance Criteria:**
- [ ] ≥95% of lemmas classified; `proper` correctly catches proper nouns (excluded from ladder)
- [ ] 200-row stratified human spot-check ≥90% agreement; disagreements corrected and fed back into the prompt before the full run
- [ ] Cost logged to `llm_calls` (task_name=`semantic_class_classification`)
- [ ] Idempotent (skips classified rows)

**Files to Create / Modify:**
- `scripts/backfill_semantic_class.py` — new
- `prompt_templates` seed row for the classification task

**Verification:**
`SELECT semantic_class, count(*) FROM dim_vocabulary GROUP BY 1` shows a plausible distribution; spot-check sheet attached.

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

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Operator decision: dual-store both scripts at generation (§6.7). Add the `opencc` dependency (config `s2twp`); add `dim_vocabulary.lemma_traditional` (filled by enrichment with jieba context for ambiguous 发→發/髮-class lemmas); create `script_conversion_overrides(simplified PK, traditional, note)`; add a renderer step that persists a `content.hant` mirror (stem, option texts, reasoning) on every ZH exercise after validation; write the idempotent mirror-backfill script for existing/corrected rows. Document the `users.exercise_preferences.script_variant` convention.

**Acceptance Criteria:**
- [ ] `lemma_traditional` populated for ≥99% of ZH lemmas; ambiguous conversions resolved and spot-checked (50-row sample incl. 发/干/后/面 class)
- [ ] Renderer writes `content.hant` covering every learner-visible TL string for all newly generated ZH exercises
- [ ] Overrides table consulted at mirror render; correcting an override + re-running backfill updates only `hant`
- [ ] Mirror-backfill script converts existing ZH exercises (~2,393 rows) idempotently

**Files to Create / Modify:**
- `migrations/traditional_chinese_groundwork.sql` — column + overrides table
- `requirements.txt` — `opencc`
- `services/vocabulary_ladder/exercise_renderer.py` — `_render_hant_mirror` step
- `scripts/backfill_hant_mirrors.py` — new

**Verification:**
Random 20 generated ZH exercises each contain `content.hant` with option-count parity; backfill re-run is a no-op.

---

## TASK-510: Model-slug health cron + fail-closed batch judges

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

---

## TASK-513: Transcript mining as a P1 sentence source

**Status:** [ ] Not Started
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

---

## TASK-514: Pipeline robustness — non-destructive regen, P1 retry, matrix-gated L4

**Status:** [ ] Not Started
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

---

## TASK-515: Batch run — top 1,000 senses × EN/ZH/JA

**Status:** [ ] Not Started
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

## TASK-516: Deterministic generators — definition_match, jumbled, readings, tone

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

---

## TASK-520: Per-exercise-type prompt split (L4 + L8 first)

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-501

**Description:**
Add `dim_word_senses.embedding vector` (pgvector, existing OpenAI embedding service; embed `lemma + definition`). Backfill all senses; embed new senses at creation. Powers distractor nearness windows (mid-cosine band), `definition_match` distractor upgrade, and syn/ant sanity checks.

**Acceptance Criteria:**
- [ ] Column + vector index; ≥99% senses embedded; idempotent backfill
- [ ] Helper `nearest_senses(sense_id, lang, pos, k, cos_min, cos_max)` SQL function
- [ ] Embedding cost logged; new-sense hook in the sense creation path

**Files to Create / Modify:**
- `migrations/dim_word_senses_embedding.sql`
- `scripts/backfill_sense_embeddings.py`
- `services/vocabulary/sense_generator.py` — embed-on-create

**Verification:**
`nearest_senses` for "precision" returns accuracy/exactness-class neighbours in the mid band.

---

## TASK-522: `synonym_antonym_match` + `word_family` generators

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

---

## TASK-525: tl_nl uniqueness judge

**Status:** [ ] Not Started
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

---

## TASK-526: Traditional-script serve toggle

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-509, TASK-515

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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-504

**Description:**
Clone the classifier-drill architecture for Japanese counters (operator-confirmed): curated counter dictionary (本/枚/匹/台/冊/杯 + semantic groups) built by a seed script + the LLM curation pipeline (`services/classifier_curation` pattern), deterministic session RPC with semantic-group distractors, sentinel-test ELO (`__counter_drill_ja`), Choose/Type modes. Then `counter_match` as L4-JA for concrete nouns in the ladder (same pattern as TASK-528).

**Acceptance Criteria:**
- [ ] Counter dictionary ≥40 counters with ≥10 nouns each for the common set; curation JSON human-reviewed before merge
- [ ] Drill RPC mirrors `get_classifier_drill_session` semantics (multi-acceptable, always 3 distractors, group-based)
- [ ] ELO via sentinel test, K=32 first-attempt-only; route rejects non-JA
- [ ] `counter_match` ladder items for dict-covered concrete nouns; capability fallback to `particle_selection` otherwise (§6.10)

**Files to Create / Modify:**
- `scripts/build_counter_dictionary.py`, `scripts/generate_counter_curation.py`
- `migrations/counter_drill.sql` (tables + RPC + sentinel)
- counter drill route + template (clone classifier drill)
- `services/vocabulary_ladder/deterministic/counter_match.py`

**Verification:**
300-item sample: 0 missing distractors, group-plausible foils; ladder attempt round-trip green.

---

## TASK-531: Audio at scale (L1 + listening variants)

**Status:** [ ] Not Started
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515

**Description:**
Synthesise TTS for all batch senses' L1 phonetic items and listening flashcards (Azure, `audio_voice.pick_voice`, deterministic R2 slugs), extending the existing L1 audio backfill tab to the full batch + JA voices. TTS failures ship the text variant and queue a backfill (§6.10).

**Acceptance Criteria:**
- [ ] ≥95% of batch L1/listening items have `audio_url`; failures queued with reason
- [ ] JA voices selected from `dim_languages.tts_voice_ids`; spot-listen 10 per language
- [ ] Cost/quota throttling (configurable per-night cap)

**Files to Create / Modify:**
- `scripts/backfill_exercise_audio.py` (extend existing backfill runner)

**Verification:**
Coverage query ≥95%; sampled URLs play.

---

## TASK-532: `cloze_typed` free-input exercises

**Status:** [ ] Not Started
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

**Status:** [ ] Not Started
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

## TASK-534: Exercise-type effectiveness view *(Phase 4 — data-gated)*

**Status:** [?] Blocked — requires post-launch attempt volume
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-515 + launch data

**Description:**
Per-`(p_known bucket, exercise_type)` Δp_known-per-minute view from `exercise_attempts` (+ Part F outcome capture), powering Phase-4 adaptivity and content QA (which types actually move knowledge at which stage).

**Acceptance Criteria:**
- [ ] View + admin page; validated against synthetic attempt fixtures

---

## TASK-535: Thompson-sampling type tie-breaker *(Phase 4 — data-gated)*

**Status:** [?] Blocked — requires ~50k attempts
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-534

**Description:**
Bandit over exercise *type* as a tie-breaker among same-family candidates inside the unified-score shortlist (composes with, never replaces, the unified score). Reuses the Study-Plan Thompson pattern.

**Acceptance Criteria:**
- [ ] Offline replay evaluation before flag-on; per-arm posteriors inspectable

---

## TASK-536: Per-user format preferences + item retirement *(Phase 4 — data-gated)*

**Status:** [?] Blocked — requires launch data
**Feature:** exercise-generation-v2
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-534

**Description:**
Soft per-user format weighting (e.g. audio-first) and an item-retirement policy driven by IRT drift + `vw_distractor_error_analysis` pick-rates (deactivate items whose distractors never attract or whose difficulty drifts implausibly).

**Acceptance Criteria:**
- [ ] Retirement runs as a reviewed batch (flag → human confirm → deactivate); preference weight bounded so it cannot override family targeting

---
