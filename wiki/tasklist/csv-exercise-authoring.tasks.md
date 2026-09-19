---
title: "CSV Exercise Authoring — Task Breakdown"
feature: csv-exercise-authoring
prose_page: ../features/csv-exercise-authoring.md
tech_page: ../features/csv-exercise-authoring.tech.md
total_tasks: 9
done: 8
---

# CSV Exercise Authoring — Task Breakdown

Infrastructure for the staged, in-session exercise chain that
[[features/lookahead-preteaching.tech]] §7 (TASK-784) needs. Scope agreed:
build and verify on 8 senses; **no bulk generation run without agreeing scope
with the user first.**

---

## TASK-795: Split `_fetch_corpus_sentences` into RPC + pure `mine_sentences`

**Status:** [x] Done 2026-09-19
**Feature:** csv-exercise-authoring
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
Mining was one method doing a per-sense RPC and then pure Python. Split it so
bulk-exported rows can be mined locally by the same code.

**Acceptance Criteria:**
- [x] `services/vocabulary_ladder/asset_pipeline.py::mine_sentences(rows, lemma, sense_id, language_id, tier=None)` is module-level and DB-free
- [x] `_fetch_corpus_sentences` = lemma lookup + RPC + `mine_sentences`; still degrades to `[]` on RPC / processor failure
- [x] Byte-identical old vs new on ≥8 ja senses

**Technical Notes:**
Signature takes `sense_id` (not only `tier`) because `_sense_surface_tokens`
needs it to read the token map. `tier` defaults to `tier_for_lemma`, as live.

**Files:** `services/vocabulary_ladder/asset_pipeline.py`, `scripts/verify_mining_split.py`, `tests/test_csv_exercise_authoring.py`

**Verification:** `python scripts/verify_mining_split.py --language ja --sense-ids 35053,35069,35215,35091,35127,35211,36633,38223,52958,41335,35943,38363`
→ **12/12 old==new and new==bulk** (2026-09-19), 4 of them at the 10-sentence
cap where row order matters.

---

## TASK-796: Stage 0 — `export_exercise_worklist.py --format csv`

**Status:** [x] Done 2026-09-19
**Feature:** csv-exercise-authoring
**Type:** feature
**Complexity:** M
**Depends On:** TASK-795

**Description:**
A CSV mode on the existing exporter (not a new script, not new SQL) writing
`senses.csv` + version-pinned `prompts.json` into a run directory.

**Acceptance Criteria:**
- [x] Columns per tech §2 (identity, zipf, level_tag, semantic_class, surface_tokens, corpus_sentences, n_mined, sentences_needed, pos_set, semantic_class_enum, prompt_version, p1_prompt, blocks_n_tests)
- [x] `tests_containing_sense` bulk-fetched once (`fetch_sense_test_rows`, chunked `overlaps` on `vocab_sense_ids`), rows fed to `mine_sentences`
- [x] `prompts.json` carries template text + version for P1/P2/P3/L4/L8, typed generators and all ladder judges (names read from the judge modules)
- [x] Same-language senses only (`definition_language_id = language_id`) in the pool and the vocab join
- [x] CSV `corpus_sentences`, `p1_prompt`, `pos_set` equal the JSON `--stage core` export for the same senses

**Technical Notes:**
`active_levels` / `p3_expected_levels` / `primary_collocate` are **not** stage-0
columns — see tech §2.2: they are functions of the P1 answer. They appear in
`plan.csv` at stage 2b. `ladder_word_family_generation`/`_judge` have no active
ja template (recorded as `error` in `prompts.json`; en-only).

**Files:** `scripts/export_exercise_worklist.py`

**Verification:** 8/8 ja senses matched the JSON export (2026-09-19); `pos_set` is UniDic.

---

## TASK-797: Stage runner (`scripts/exercise_stage_runner.py`)

**Status:** [x] Done 2026-09-19
**Feature:** csv-exercise-authoring
**Type:** feature
**Complexity:** L
**Depends On:** TASK-796

**Description:**
`prepare` / `collect` / `bridge` / `assemble` / `status` over a run directory.
Pure logic in `services/vocabulary_ladder/stage_runner.py`.

**Acceptance Criteria:**
- [x] item_N envelope reused from `services/batch_prompting` (always enveloped, even N=1)
- [x] Per-unit status; a failed unit does not stop the others; blocked units recorded, never silently absent
- [x] Stage 2b (`bridge`) = `upload_exercises.prepare_core` + `export_exercise_worklist.build_exercise_item(include_typed=True)`; refuses if a prompt version moved since export
- [x] Judge prompts captured from the real judge functions / `LadderExerciseRenderer.build_rows` with `call_llm` swapped for a recorder
- [x] Judge output `{judged, verdict, changed}`; `changed` checked against the diff; all-unchanged = rubber stamp → exit 1 and stage 7 refuses
- [x] Stage 7 writes the two batch/answers pairs + `dropped.json` accounting for every sense
- [x] Retries are new rounds (`--senses`), always max+1

**Files:** `scripts/exercise_stage_runner.py`, `services/vocabulary_ladder/stage_runner.py`, `tests/test_csv_exercise_authoring.py`

**Verification:** `PYTHONPATH=. python -m pytest tests/test_csv_exercise_authoring.py -q` → 21 passed.

---

## TASK-798: Two skills — authoring and judging

**Status:** [x] Done 2026-09-19
**Feature:** csv-exercise-authoring
**Type:** docs
**Complexity:** S
**Depends On:** TASK-797

**Acceptance Criteria:**
- [x] `.claude/skills/batch-exercise-authoring/SKILL.md` — stages 1, 3, 4, 5, 7; hand-off prompt is run dir + stage only
- [x] `.claude/skills/batch-exercise-judging/SKILL.md` — stages 2, 6; reads only the round's prompt files; refuses if it has the authoring context
- [x] Payload shapes deferred to `batch-exercise-generation` (not duplicated)

**Verification:** stage 2 of the e2e run judged by a fresh subagent given only
the run dir + stage: 3 accept / 5 rewrite, 9 sentences rewritten — it caught
every mined sentence with the target embedded in a compound (色彩, 赤色, 好循環)
or in a different sense (賭ける-sense かけ, 声をかける), plus a generated
鍵を掛ける the author had missed.

---

## TASK-799: Typed LLM levels through the uploader (`llm_types_A/B`)

**Status:** [x] Done 2026-09-19 (live: 16 particle_selection + 4 synonym_antonym_match rows, all linked)
**Feature:** csv-exercise-authoring
**Type:** feature
**Complexity:** S
**Depends On:** TASK-797

**Description:**
User decision 2026-09-19: extend the uploader rather than defer typed levels.
`TypedLLMGenerator.fragment_from_raw` is the post-call half of `generate`,
now shared with `upload_exercises._remap_typed` (schema gate against the
exported `prompt_version`, key-9 decline → `{}`).

**Acceptance Criteria:**
- [x] Variants exported with a `typed` block store `llm_types_<v>` (empty dict when no type applies, as the pipeline does)
- [x] Batches without `typed` behave exactly as before
- [x] `export_exercise_worklist --stage exercises --include-typed` for the JSON workflow
- [x] Live: rendered typed rows land with `word_asset_id` (TASK-800)

**Files:** `scripts/upload_exercises.py`, `services/vocabulary_ladder/asset_generators/typed_llm.py`, `scripts/export_exercise_worklist.py`

---

## TASK-800: End-to-end on 8 ja senses — no API calls anywhere

**Status:** [x] Done 2026-09-19
**Feature:** csv-exercise-authoring
**Type:** test
**Complexity:** M
**Depends On:** TASK-797, TASK-798, TASK-799

**Description:**
`data/exercise_seeding/ja/run_task798_e2e` — senses 53352 超える, 51794 色,
39097 工程, 39259 作業, 35201 齎す, 35241 掛ける, 36433 循環, 36179 文脈.
**User rule (2026-09-19): every model call is a Claude subagent or the session;
no hosted-model API call, including the renderer's judges.**

**Acceptance Criteria:**
- [x] Stages 0–7 run; stage 2 (incl. a retry round) and stage 6 judged by fresh subagents
- [x] Assets uploaded with `--no-render`; rows built by **stage 8**: the real renderer's
  judge requests captured, answered by subagents (83 + 14 + 2 requests over 3 rounds),
  replayed at render time — `render` refuses to insert a sense with any unanswered request
- [x] **153 rows, `count(word_asset_id) = count(*) = 153`, 8/8 senses, 12 exercise types**
- [x] 0 learner-facing rows came from an API judge (the first attempt's 74 API-rendered
  rows for 4 senses, 0 attempts, were deleted and rebuilt through stage 8)

**Findings:**
- `upload_exercises.py` without `--no-render` calls hosted judges (~6 min/sense, and the
  cloze judge's `qwen/qwen-2.5-72b-instruct` slug is failing open: rate-limited + endpoint
  unsupported). The authoring skill now mandates `--no-render` + stage 8.
- The ja L1 phonetic trie `random.shuffle`s its candidates, so unseeded capture/render ask
  about different words and replay never converges. The runner seeds `random` per sense.
- 超える and 掛ける got **no L1 row**: see TASK-803.

---

## TASK-801: ja suru-nouns labelled `action` get an unsatisfiable L4 plan

**Status:** [x] Done 2026-09-20 (option (a), POS-aware gate)
**Feature:** csv-exercise-authoring (affects the live pipeline equally)
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
For ja, `semantic_class = action` plans `morphology_slot` (L4) whenever P1
records ≥2 morphological forms. A suru-noun (作業, 循環 — both `action` in
`dim_vocabulary`) has no conjugation of its own, so the L4 prompt correctly
declines (`{"9": "no_inflection"}`), the fragment is `{}`, and
`validate_prompt3` rejects the P3 asset with "Missing level_4". The live
pipeline takes the same path and would store an invalid P3.

**Acceptance Criteria:**
- [x] Decide (operator chose (a), 形状詞 keeps L4): P1 guidance (`action` = 動作動詞 only, as the ja prompt already says) vs a POS-aware L4 gate (名詞 ⇒ no morphology_slot) vs validator tolerance of an L4 decline
- [x] Count live ja senses with `pos = 名詞 ∧ semantic_class = action`: `dim_vocabulary` 461 名詞 (+6 `noun`) rows = 2,766 senses labelled `action` (of 821 `action` rows; 351 are 動詞). In `word_assets` `prompt1_core` (ja): **0 of 84** are 名詞 ∧ action (21 are `action`, all non-noun). Invalid `prompt3_transforms` with "Missing level_4": **0** (no invalid ja P3 rows are stored; all 168 are valid). So today the defect is latent: it bites when P1 copies the `dim_vocabulary` label onto a noun
- [x] Regression test: `tests/test_ja_suru_noun_l4_gate.py` (16 tests; 10 fail with the token removed)

**Implementation:** new requirement token `inflecting_pos` on the ja `morphology_slot` row of `_CAPABILITY_SPEC`
(`services/vocabulary_ladder/config.py`), set by `capability_context_from_core` from P1's `pos`
against `JA_NON_INFLECTING_POS` (名詞, 代名詞, 副詞, 連体詞, 接続詞, 感動詞, 助詞). 動詞, 形容詞
and 形状詞 keep L4. No `pos` in the asset leaves the token unset, which `requirements_met`
treats as satisfied, so a sparse asset is planned as before. The pipeline, `build_exercise_item`
and the renderer all call that one function, so the plan and the validator's expected-level list
agree and "Missing level_4" cannot arise for a gated word. L4 itself stays in the plan
(`cloze_typed`, `particle_selection` still serve nouns); only the model's morphology request is dropped.
No `prompt_templates` row was edited. The mirror `migrations/dim_exercise_capabilities.sql` row was
updated to match but **not applied live**: no gate reads the live table, and applying it is a separate step.

---

## TASK-802: ESLint parses `static/js/session/**` as script, `npm run check` fails

**Status:** [ ] Not Started
**Feature:** tooling
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:**
`npm run check` exits 1 on 11 ESLint *parse* errors ("'import' and 'export'
may appear only with 'sourceType: module'"), not only on the CRLF prettier
baseline. All 11 are the ES-module files under `static/js/session/`;
`eslint.config.js` sets `sourceType: 'script'` for all of `static/js`.
Pre-existing (config unchanged since May). The fix is a config block
`{ files: ['static/js/session/**/*.js'], languageOptions: { sourceType: 'module' } }` —
the ECC config-protection hook blocks agent edits to `eslint.config.js`, so it
needs the operator.

**Status update 2026-09-20:** re-checked, `npx eslint static/js` reports the same 11
parse errors, all in `static/js/session/` (controller, player_registry and 9
players). Append this object to the array in `eslint.config.js` (after the
`static/js/**/*.js` block, so it overrides `sourceType`):

```js
  {
    files: ['static/js/session/**/*.js'],
    languageOptions: { sourceType: 'module' },
  },
```

Awaiting that edit; then confirm `npm run check` fails only on the CRLF prettier baseline.

---

## TASK-803: ja L1 judge and trie are given the stem, not the dictionary form

**Status:** [x] Done 2026-09-20
**Feature:** csv-exercise-authoring (affects the live renderer equally)
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
`LadderExerciseRenderer._render_phonetic` takes `target_word = self._lemma(core, sense_id)`,
which for ja verbs resolves to the sentence surface/stem (超え, かけ), not the headword
(超える, 掛ける). The trie builds neighbours of the stem and the L1 judge judges against the
stem, so a 2-mora "target" meets 3-mora candidates and every distractor fails: in TASK-800
超え kept 0–1 of 10 per request, かけ 0–1, and both senses lost L1 entirely. Every ja verb
rendered live is exposed.

**Acceptance Criteria:**
- [x] `_render_phonetic` uses the dictionary form: new `LadderExerciseRenderer._headword` (`dim_vocabulary.lemma`, falling back to the sentence target). `_lemma` is unchanged
- [x] Count live ja verb senses with no `phonetic_recognition` row: **10 of 22** verbs/adjectives with exercises before; **8 of 22** after (超える, 掛ける fixed)
- [x] Regression test on 超える / 掛ける: `tests/test_l1_headword.py` (5 tests; 4 fail with the fix reverted)
- [x] Verified on the TASK-800 run: 53352 and 35241 re-rendered through stage 8 (round 4, 4 requests) to 23 and 21 rows, all linked; both now have an L1 row keyed on 超える / 掛ける with `distractor_source = phonetic_trie`

**Findings (correcting the description above):**
- The trie was never given the stem. It is keyed on P1's `pronunciation` (こえる), which is already the dictionary reading, so its candidates were always right. The stem (超え) reached only the **judge** and the **learner** as `correct_answer`, so the judge compared candidates against a form that was not the answer. Candidate counts are identical before and after (10 per verb offline).
- `_lemma` stays as it was. `ctx.lemma` feeds the deterministic types, and `cloze_typed._interchangeable_variants` compares the sentence target against it, so switching it globally would change those.
- Not fixed here, needs a re-render through stage 8: 7 live L1 rows still carry a stem as the correct answer (取る→取っ, 因る→よっ, 居る→い, 成る→なり, 於く→おい, 限る→限ら, 無い→なく), and 8 verbs have no L1 (出来る, 増える, 担う, 持つ, 有る, 為る, 留まる, 通ずる). All have 0 attempts except 持つ (1).
- Related, not touched: the lexicon-keyed deterministic types (`kanji_to_reading`, `reading_to_kanji`) also read `ctx.lemma`, so for inflected verbs they look up the stem.
