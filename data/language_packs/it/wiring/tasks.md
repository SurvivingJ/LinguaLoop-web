---
title: "Italian (it, language id 4) — Wiring Task Breakdown"
feature: language-italian
source: data/language_packs/it/profile.json
total_tasks: 34
done: 0
---

# Italian (it, language id 4) — Wiring Task Breakdown

Written by the content team's wiring planner on 2026-11-28. **Nothing here has been
done.** The content team wrote local files only; no application code was edited and no
SQL was applied.

How to read this file

- Tasks are in dependency order. The numbers 1 to 34 are positions in this list, not
  task ids: the wiki owner assigns `TASK-NNN` ids when the list is taken into
  `wiki/tasklist/`. `wiring/pending_language.sql` refers to tasks by these positions.
- `PACK` is `data/language_packs/it/`. The profile (`PACK/profile.json`) is the
  specification for every ladder row and dictionary; each task quotes only what the
  engineer must not miss.
- File locations were confirmed by grep on 2026-11-28. Line numbers drift: grep for the
  quoted symbol before editing.
- The five checkpoints (each leaves the app in a testable state):
  1. tasks 1 to 6: the language exists and can be selected; nothing to study.
  2. tasks 7 to 9: vocabulary, senses, glosses and embeddings are in the database.
  3. tasks 10 to 28: the ladder runs for Italian (carried-over types first, then
     dictionaries, then the six new types, then the real fat-seed run).
  4. tasks 29 and 14: the grammar drill page and the Italian trainers.
  5. tasks 30 to 34: tests, dual translation, study plans, placement, go-live.

Open questions that block a task are marked **[?]** in its status, as the wiki rules
require (CLAUDE.md section 10).

---

## 1. Apply the language row and the capability matrix (inactive)

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Review `PACK/wiring/pending_language.sql`, move it into `migrations/` under its task id
and apply it. It inserts `dim_languages` id 4 (`it`, inactive), the six new
`dim_exercise_types` rows and 23 `dim_exercise_capabilities` rows for language 4. The
language stays inactive so that test generation and the nightly IRT calibration, which
iterate over active languages, do not pick it up before the code knows it.

**Acceptance Criteria:**
- [ ] The two Azure voices `it-IT-IsabellaNeural` and `it-IT-DiegoNeural` are confirmed
      against the live Azure voice list (the profile took them from memory) or replaced.
- [ ] The verification queries at the end of the file return the expected rows:
      23 capability rows, 15 enabled, 8 disabled; `is_active = false`.
- [ ] Running the file a second time changes nothing.
- [ ] `wiki/database/schema.tech.md` records the new language row and type codes.

**Technical Notes:**
The file was run twice against an empty local PostgreSQL 16 with stand-in tables (not
against any LinguaLoop database); it has not been run against the real schema. It writes
`id = 4` explicitly and then moves the id sequence. The collocation rows are inserted
disabled although the profile marks them `adapt`: see the file header and task 19.
`grammar_check_enabled` is false because no Italian grammar tooling is wired.

**Files to Create / Modify:**
- `migrations/<task>_italian_language.sql` — the reviewed copy of the pending file
- `wiki/database/schema.tech.md` — language row, six type codes (wiki owner)

**Verification:**
Run the verification block of the file. `SELECT is_active FROM dim_languages WHERE id = 4`
returns false; the production queue shows no Italian jobs after its next cycle.

---

## 2. Backend language set and the copies of the id-to-code map

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 1

**Description:**
Teach the backend that language 4 is `it`. `config.py` is the declared source, but about
twenty modules carry their own `{1: 'zh', 2: 'en', 3: 'ja'}`. Add Italian to every copy,
and where a copy has a second map keyed on script family, add `'it': 'latin'` (or the
English branch) deliberately rather than by fall-through.

**Acceptance Criteria:**
- [ ] `Config.LANGUAGES[4] == {'code': 'it', 'name': 'italian', 'display': 'Italian'}`
      and `Config.LANGUAGE_CODE_TO_ID['it'] == 4`.
- [ ] `grep -rnE "3: *'ja'|'ja': *3" services routes config.py` shows no map without an
      `it` entry (or a comment saying why Italian is excluded).
- [ ] A unit test asserts that every module-level id-to-code map equals the one derived
      from `Config.LANGUAGES`, so the next language is one edit.
- [ ] `routes/calibration.py` still rejects language 4 (placement is task 33).

**Technical Notes:**
Maps to edit: `services/vocabulary_ladder/asset_pipeline.py` `_LANG_ID_TO_CODE`;
`asset_generators/{_split_base,prompt1_core,prompt2_exercises,prompt3_transforms}.py`;
`services/vocabulary_ladder/config.py` `TIER_GATE_LANG_CODES`;
`services/vocabulary_ladder/definition_serving.py` `_LANG_CODE` and `_LANG_FAMILY`;
`services/exercise_explanations.py` `_LANG` and `_FAMILY`;
`services/exercise_content/store.py` `LANGUAGE_CODES`; `services/intro_drill.py`
`LANG_CODE`, `COLD_FORMAT` (Italian: `recall_typed`, as English) and the
`'cjk' if lang in ('ja','zh') else 'en'` branch of `STAGE_FORMATS`;
`services/corpus/ingestion.py`; `services/dual_translation/sentence_refs.py` `LANG_CODE`
(length-ratio table is task 31); `services/tier_classifier.py` `LANG_IDS` (thresholds are
task 30); `services/llm_service.py` `_LADDER_QWEN_REASONING_BUDGET_BY_LANG`;
`services/llm_output_cleaner.py` (language-code aliases); `services/categorical_maps.py`;
`services/vocabulary/sense_generator.py`; `services/vocabulary/gloss_generator.py`
`LANGUAGE_NAMES`. Do not touch `routes/calibration.py` `_SUPPORTED_LANGUAGE_IDS` or
`services/calibration_placement.py` yet.

**Files to Create / Modify:**
- `config.py` — `Config.LANGUAGES` entry 4
- the modules listed above — one map entry each
- `tests/test_language_maps.py` (new) — the equality test

**Verification:**
`pytest tests/test_language_maps.py tests/test_capability_matrix.py`; in a shell,
`Config.LANGUAGE_CODE_TO_ID['it']` is 4.

---

## 3. Italian text normaliser and the three NLP registries

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 2

**Description:**
Add an Italian processor to each of the three registries, all built on one shared
spaCy model and one shared normaliser. The profile's `nlp.notes` lists what the
normaliser must do; the points below are the ones that break exercises if missed.

**Acceptance Criteria:**
- [ ] Text is normalised to NFC and the curly apostrophe to the straight one before
      anything else.
- [ ] Tokens for exercises keep an elided form with the next word as one unit
      (`l'amico`, `un'idea`, `dell'acqua`, `c'è`, `quest'anno`): a test asserts the unit
      list for each of these five.
- [ ] A fused preposition + article (`del`, `nello`, `sugli`, `col`) is one token mapped
      to its preposition and is never returned as vocabulary.
- [ ] Enclitic pronouns are stripped by rule before lemmatising (`vederlo` -> `vedere`,
      `dammelo` -> `dare`, `alzandosi` -> `alzarsi` only when the lexicon lists the
      reflexive).
- [ ] `LanguageProcessor.for_language(4)`, `get_tokenizer(4)` and
      `_PROCESSOR_CLASSES['it']` all return an Italian class; `_NLP_METADATA['it']` exists.
- [ ] The model is pinned in `requirements.txt`.

**Technical Notes:**
The profile names `it_core_news_lg` (`it_core_news_md` where memory is tight). The
existing languages use the `sm` models and share them through
`services/vocabulary/model_cache.py`; decide the size against the host's memory and use
the same cache key from all three registries. The profile's notes on how spaCy splits
elisions and clitics were written from knowledge, not from a run (spaCy is not installed
where the profile was written): the first step of this task is to run the model on the
profile's examples and correct the notes. Homographs (`sono`, `stato`, `porto`, `ancora`,
`subito`, `legge`) need the tagger; irregular verb forms the lemmatiser gets wrong
(`vado`, `feci`, `tenga`) are corrected from the verb_conjugation dictionary once task 16
has loaded it.

**Files to Create / Modify:**
- `services/vocabulary/processors/italian.py` (new) — processor and shared normaliser
- `services/vocabulary/pipeline.py` — `_PROCESSOR_CLASSES['it']`
- `services/vocabulary/config.py` — `_NLP_METADATA['it']`
- `services/exercise_generation/language_processor.py` — `ItalianProcessor`, `for_language`
- `services/corpus/tokenizers.py` — `ItalianTokenizer`, `get_tokenizer`
- `requirements.txt` — the spaCy Italian model wheel
- `tests/test_italian_processor.py` (new)

**Verification:**
`pytest tests/test_italian_processor.py`; `LanguageProcessor.for_language(4)` chunks
"L'amico di Maria è andato al mercato." with `L'amico` and `al` as single units.

---

## 4. Frequency maps, language detection and input validators

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** 2

**Description:**
Several validators have no branch for an unknown language and pass silently. Give each an
Italian rule so that English or Spanish text cannot enter as Italian.

**Acceptance Criteria:**
- [ ] `services/vocabulary/frequency_service.py` and
      `services/test_generation/difficulty_scorer.py` map `it` (and `italian`) to
      wordfreq `it`; lemma frequency is summed over the forms of the lemma.
- [ ] `services/vocabulary/language_detection.py` `check_text_language(text, 'it')`
      rejects an English sentence and accepts an Italian one.
- [ ] `services/word_list_import/validation.py` `_SCRIPT_RULES['it']` accepts only the
      profile's letters (`a-z`, `à è é ì ò ù`, apostrophe) and rejects digits.
- [ ] `services/llm_output_cleaner.py` accepts `it` as an expected language.

**Technical Notes:**
The allowed character set is `text.allowed_regex` in the profile. Latin-script detection
cannot tell Italian from English by script, so use the detector the cleaner already uses
for `en` and require the detected code to be `it`.

**Files to Create / Modify:**
- the four modules named above
- `tests/test_language_detection.py` (new), `tests/test_word_list_validation.py` (new) — Italian cases

**Verification:**
`pytest tests/test_language_detection.py tests/test_word_list_validation.py`.

---

## 5. Frontend language set

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** 2

**Description:**
Add Italian to the frontend id-to-code maps and the language picker. The card is added
hidden behind the same flag that go-live (task 34) turns on.

**Acceptance Criteria:**
- [ ] `{ 1: 'zh', 2: 'en', 3: 'ja' }` gains `4: 'it'` in
      `static/js/pages/{language-selection,placement,knowledge,calibration}.js`,
      `static/js/prestudy/prestudy.js`, `static/js/session/players/prestudy.js`.
- [ ] Glyph maps (`{ 1: '词', 2: 'Aa', 3: '語' }` in `placement.js` and `knowledge.js`)
      gain an Italian glyph (`Aa` or `It`).
- [ ] `templates/language_selection.html` has a fourth card (`data-id="4"`, native name
      `Italiano`, `lang="it"`), not rendered until the language is active.
- [ ] `static/js/pages/study-plan.js` lists `{ id: 4, code: 'it', name: 'Italian' }`.
- [ ] Decision recorded: Italian is a study language only, not a native-language option
      in `static/js/pages/profile.js` (the profile's learner is an English speaker and
      `gloss_languages` is `["en"]`).

**Technical Notes:**
No font work is needed in `static/js/pages/base-head.js`: Italian uses the Latin stack.
Drive the card from the active-languages response rather than a fourth hard-coded
button if that is a small change.

**Files to Create / Modify:**
- the six JS files and `templates/language_selection.html`, `static/js/pages/study-plan.js`
- `tests/unit/` — extend the page tests that pin the maps

**Verification:**
`npm test`; with the language inactive the picker shows three cards; with a local row
set active it shows four and selecting Italian stores language id 4.

---

## 6. Scripts and offline tooling

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** 2

**Description:**
About 35 scripts carry their own `LANG_ID` map or `choices=['zh','en','ja']`. Open the
ones the content path needs; leave the evaluation scripts under `data/eval/` and
`sandbox/` alone.

**Acceptance Criteria:**
- [ ] `--lang it` (or language id 4) is accepted by `scripts/load_vocab_list.py`,
      `upload_senses.py`, `export_sense_seed_worklist.py`, `export_gloss_worklist.py`,
      `export_exercise_worklist.py`, `render_existing_assets.py`,
      `backfill_sense_embeddings.py`, `backfill_semantic_class.py`,
      `backfill_pronunciations.py`, `backfill_exercise_audio.py`,
      `sentence_ref_runner.py`, `run_content_build.py`, `fat_seed_runner.py`.
- [ ] `scratch_offline/nt_lang.py` `LANGUAGES` has `it`; `nt_pipeline.py --lang it` runs;
      `export_offline_worklist.py` reads the pack's `tl_standard` and `pronunciation`
      instead of `ja_standard` and `reading`.
- [ ] Each script imports the map from `config.py` instead of repeating it.

**Technical Notes:**
`scripts/grammar_drills.py` is Chinese-only by design (TASK-1266) and is not opened: the
Italian drills are built by `scripts/language_pack.py build it`.

**Files to Create / Modify:**
- the scripts named above

**Verification:**
`python scripts/export_sense_seed_worklist.py --lang it --help` exits 0; each listed
script's `--help` shows `it` among the choices.

---

## 7. Load the lexicon, senses, glosses and embeddings

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** 3, 4, 6

**Description:**
Load the pack's reviewed vocabulary through the existing write paths: lemmas into
`dim_vocabulary`, two-level senses and English glosses into `dim_word_senses`, then
embeddings. Only `PACK/senses/final.json` (reviewed batches) is loaded.

**Acceptance Criteria:**
- [ ] `python scripts/language_pack.py validate-lexicon it` and `validate-senses it` end
      with OK before anything is loaded.
- [ ] Every loaded sense has `pronunciation` in the profile's IPA format: slashes,
      primary stress mark, syllable dots (`/teˈlɛ.fo.no/`). A sense without the stress
      mark is reported, because `stress_position` (task 21) cannot use it.
- [ ] Sense counts in the database equal the count in `senses/final.json`.
- [ ] `scripts/backfill_sense_embeddings.py --lang it` leaves no Italian sense without an
      embedding.
- [ ] `scripts/backfill_semantic_class.py` has labelled every Italian sense (needs the
      `semantic_class_classification` row from task 9).

**Technical Notes:**
Loading goes through the sense write path (`scripts/upload_senses.py`), never direct
inserts, so the two-level definition checks and the embedding hook run. Frequency tiers
come from wordfreq summed over the forms of a lemma (profile `nlp.notes`).

**Files to Create / Modify:**
- none beyond task 6 (data load); record counts in the task log

**Verification:**
`SELECT count(*) FROM dim_word_senses WHERE word_language_id = 4 AND
definition_language_id = 4` equals the pack's sense count (English gloss rows are counted
separately, with `definition_language_id = 2`); the same query filtered on a missing
embedding or a NULL semantic class returns 0. Confirm the column names against
`wiki/database/schema.tech.md` before running.

---

## 8. SQL functions with per-language branches

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 1

**Description:**
Four migrations hold functions that branch on `p_word_language_id = 1` (Chinese) and
`= 3` (Japanese) and fall through to the English behaviour otherwise. Read each branch
and decide, in writing, that the English branch is right for Italian or add an Italian
one.

**Acceptance Criteria:**
- [ ] Each `CASE` in `migrations/calibration_placement_rpcs.sql`,
      `calibration_pronunciation_mode.sql`, `knowledge_calibration_inputs.sql` and
      `knowledge_report_words.sql` has a comment naming what language 4 gets.
- [ ] Italian has no reading or tone mode: word counting uses whitespace, and no
      pronunciation-mode calibration is offered.
- [ ] Changed functions are redefined in a new migration; the old definer is archived as
      `migrations/CLAUDE.md` requires.

**Technical Notes:**
The word-count branch for the default language splits on whitespace, which counts
`l'amico` as one word: that matches the profile (`length_unit: words`, apostrophe is not
punctuation). No change is expected there; the work is confirming each branch.

**Files to Create / Modify:**
- `migrations/<task>_language_branches_italian.sql` (new, only if a branch changes)
- `tests/sql/` — one fixture row per function for language 4

**Verification:**
The SQL tests under `tests/sql/` pass with the language-4 fixtures.

---

## 9. Prompt rows: sense dictionary and vocabulary extraction

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 1

**Description:**
Write and seed the Italian `prompt_templates` rows for the vocabulary pipeline:
`vocab_phrase_detection`, `vocab_definition_generation`, `vocab_sense_selection`,
`semantic_class_classification` (`PACK/wiring/prompt_tasks.txt`, fourth group). Without
`vocab_phrase_detection` the extraction pipeline raises on an Italian test.

**Acceptance Criteria:**
- [ ] One row per task name with `language_id = 4`, model columns filled, written in the
      style of `migrations/rewrite_sense_prompts_two_level.sql`.
- [ ] The definition prompt produces the two-level definition the pack's senses use and
      English glosses; examples are Italian.
- [ ] `scripts/audit_prompt_conventions.py` passes for language 4.

**Technical Notes:**
Start from the English rows (Latin script, inflecting language), not the Chinese or
Japanese ones. The pack's reviewed senses are the reference for tone and length.

**Files to Create / Modify:**
- `migrations/<task>_it_vocab_prompts.sql` (new)

**Verification:**
`get_template_config(db, 'vocab_phrase_detection', 4)` returns a row; running the
extraction pipeline on one Italian paragraph returns lemmas with definitions.

---

## 10. Prompt rows: ladder generation and judges

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 1, 7

**Description:**
Write and seed the Italian rows for the ladder generators and judges
(`prompt_tasks.txt`, first three groups: 15 names). `get_template_config` has no
fallback, so a missing row stops generation for that type. The adaptations the profile
asks for live in these prompts; the `note` of each ladder row is the requirement.

**Acceptance Criteria:**
- [ ] Rows exist for `vocab_prompt1_core`, `vocab_prompt2_exercises`,
      `vocab_prompt3_transforms`, `ladder_l4_morphology_generation`,
      `ladder_syn_ant_generation`, `ladder_word_family_generation`,
      `ladder_l8_collocation_repair_generation` and the judges
      `ladder_p1_sentence_judge`, `ladder_l1_distractor_judge`, `cloze_distractor_judge`,
      `ladder_sentence_validity_judge`, `ladder_relation_judge`,
      `ladder_word_family_judge`, `ladder_collocation_judge`,
      `translation_uniqueness_judge`, all with `language_id = 4`.
- [ ] P1 core asks for IPA with stress mark and syllable dots, and for sentences inside
      the profile's limits (3 to 22 words, no digits, the allowed character set).
- [ ] L1 distractors differ from the headword in spelling (single/double consonant,
      gl/l, gn/n, c/g, one vowel); stress-only and open/closed-vowel pairs are forbidden;
      the prompt may decline with `no_minimal_pairs`.
- [ ] L3 distractors share gender, number and kind of first sound with the answer; an
      elided or truncated word is never blanked.
- [ ] L4 morphology: one fitting form; declines with `no_inflection` for invariables.
- [ ] L7: one error on the target of the kinds the profile lists; no accent-only error.
- [ ] `scripts/audit_prompt_conventions.py` and `audit_prompt_latin.py` pass.

**Technical Notes:**
`PACK/fat_seed/` holds the cheat sheet and the reviewed exercise documents: they are the
worked examples for these prompts. Follow `migrations/ja_prompt_seeds.sql` for the file
shape and `seed_ladder_judge_prompts.sql` for the judges.

**Files to Create / Modify:**
- `migrations/<task>_it_ladder_prompts.sql` (new)

**Verification:**
`scripts/fat_seed_runner.py` (opened in task 6) prints an Italian brief for one sense
without a missing-template error.

---

## 11. P1 validation profile and the inflecting-part-of-speech gate

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** 2

**Description:**
`services/vocabulary_ladder/config.py` validates a P1 core asset per language and derives
the `inflecting_pos` requirement from a Japanese list. Add the Italian profile and make
the gate language-aware, or morphology is planned for Italian adverbs and loanwords.

**Acceptance Criteria:**
- [ ] `LANGUAGE_VALIDATION_PROFILES[4]` exists: `ipa_required=True`,
      `min_morphological_forms=2`, an Italian part-of-speech set.
- [ ] `capability_context_from_core` takes the language and computes `inflecting_pos`
      from a per-language set; for Italian, adverbs, prepositions, conjunctions and
      interjections are non-inflecting.
- [ ] P1 validation warns when the IPA has no primary stress mark.

**Technical Notes:**
Today `context['inflecting_pos'] = pos not in JA_NON_INFLECTING_POS` for every language;
only the Japanese capability row asked for the token, and the Italian morphology row now
asks for it too. Invariable nouns and adjectives (`bar`, `film`, `blu`) cannot be gated by
part of speech: the prompt declines them (`no_inflection`).

**Files to Create / Modify:**
- `services/vocabulary_ladder/config.py`
- `tests/test_capability_matrix.py`, `tests/test_ja_suru_noun_l4_gate.py` — Italian cases

**Verification:**
`pytest tests/test_capability_matrix.py tests/test_ja_suru_noun_l4_gate.py`.

---

## 12. Adapted deterministic types: typed answers and sentence tiles

**Status:** [?] Blocked on a design answer (jumbled alternative orders, below)
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 3

**Description:**
Two carried-over deterministic generators need Italian behaviour. `cloze_typed`: accents
are part of the spelling, and a wrong or missing accent is reported as an accent error
with the right spelling, not as a plain wrong answer and not as correct.
`jumbled_sentence`: tiles are split on spaces only, so `l'amico` and `dammelo` are one
tile each.

**Acceptance Criteria:**
- [ ] `utils/answer_normalization.py`: for language 4 the comparison is
      case-insensitive, maps the curly apostrophe to the straight one and keeps accents
      significant; `normalization_spec(4)` records an `accents: 'significant'` entry.
- [ ] `cloze_typed.grade` returns `is_correct: false` plus `error_kind: 'accent'` and the
      correct spelling when the answer differs only in accents (`perche`, `perchè` for
      `perché`; `citta` for `città`; `e'` for `è`). A single/double consonant slip is a
      plain wrong answer.
- [ ] The renderer shows the accent message; the attempt is recorded as incorrect.
- [ ] `jumbled.py` for language 4: tiles from the Italian processor's units, joined with
      a space, lower-cased except proper names, only sentences of at most eight tiles.
- [ ] `input_mode` is `text` for Italian.

**Technical Notes:**
Open question the profile leaves unresolved: it asks the item to "accept every order a
reviewer listed as valid, not just the stored one" (Oggi piove / Piove oggi). Neither the
P1 sentence asset nor the jumbled content has a field for alternative orders, and the
fat-seed documents do not carry one. Either add `accepted_orderings` to the P1 sentence
and to the item, or restrict Italian to sentences with one valid order. Until that is
decided the jumbled part is blocked; the cloze part is not.

**Files to Create / Modify:**
- `utils/answer_normalization.py`, `services/vocabulary_ladder/deterministic/cloze_typed.py`
- `services/vocabulary_ladder/deterministic/jumbled.py`
- `static/js/exercise-renderers.js` — accent message for typed cloze
- `tests/test_answer_normalization.py`, `tests/test_deterministic_generators.py`,
  `tests/unit/exercise-renderers.test.js`

**Verification:**
`pytest tests/test_answer_normalization.py tests/test_deterministic_generators.py`;
typing `perche` in a served Italian typed cloze shows the accent message and counts as
incorrect.

---

## 13. Capability matrix in code and the type registrations

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 1, 11

**Description:**
Mirror sections 2 and 3 of the applied SQL in code, and register the six new type codes
everywhere a type must be known, with every new row disabled. After this task the ladder
planner computes the right levels for an Italian sense.

**Acceptance Criteria:**
- [ ] `_CAPABILITY_SPEC` in `services/vocabulary_ladder/config.py` has the 23 Italian
      rows with the same columns and `is_enabled` as the database;
      `tests/test_capability_matrix.py` pins them.
- [ ] `compute_active_levels(4, cls)` returns `[1,2,3,4,6,7,9]` for concrete, abstract,
      action and property, and `[1,2,3,6,7]` for function.
- [ ] `EXERCISE_TYPE_FAMILY` and `EXERCISE_TYPE_CONTEXT_CLASS` contain the six new codes
      with the values of the SQL.
- [ ] Decision implemented for the context-free caps: `stress_position` and
      `auxiliary_choice` have one question per word (default cap 1; add them to
      `_CONTEXT_FREE_UNIQUE_TYPES` in `exercise_renderer.py`, to `c_context_free` in
      `migrations/exercise_content_storage.sql` and to the v2 unique index in
      `exercise_content_drop_column.sql`, all three together). `article_match` (4 modes),
      `conjugation_form` (many cells) and `government_match` (one per government row)
      get an explicit entry in `CONTEXT_FREE_TYPE_CAPS` and are NOT added to the index.
- [ ] `services/exercise_generation/schemas/envelope.py` lists the native-language
      fields of the six types (`explanation` for all six).

**Technical Notes:**
The `requires` tokens `noun_gender_dict`, `verb_conjugation_dict`, `verb_government_dict`,
`collocations_dict` and `false_friends_dict` are new. Follow the `classifier_dict`
convention: do not put them in `capability_context_from_core`; the builder skips with a
reason. If one is ever supplied, `false_friends_dict` must mean "loaded for the
language", never "this word is in it" (see the SQL header). Four ladder types now share
level 4 for an Italian verb (`cloze_typed`, `morphology_slot`, `auxiliary_choice`,
`conjugation_form`, plus `government_match` and `preposition_selection`): check that
level-4 selection rotates over types rather than always serving the first.

**Files to Create / Modify:**
- `services/vocabulary_ladder/config.py`, `services/vocabulary_ladder/exercise_renderer.py`
- `services/exercise_generation/schemas/envelope.py`
- `migrations/<task>_context_free_types_italian.sql` (new)
- `tests/test_capability_matrix.py`, `tests/test_context_free_exercise_caps.py`

**Verification:**
`pytest tests/test_capability_matrix.py tests/test_context_free_exercise_caps.py`.

---

## 14. Dictionary trainer shell (shared drill page and service)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 2, 5

**Description:**
The classifier and counter drills are two single-language pages over one service
(`services/drill_service.py`). Italian has five dictionaries; build one trainer shell
that a dictionary plugs into with a small descriptor (table, prompt builder, options,
explanation), so that tasks 15 to 19 each add a drill without a new page.

**Acceptance Criteria:**
- [ ] One route and template render a recall drill for a named dictionary of the current
      study language; unknown dictionary or language answers 404.
- [ ] A drill round is recorded with the mechanism the counter drill uses (sentinel test
      and ELO) or a per-item mastery table: the choice is written down in the tech page.
- [ ] `templates/profile.html` shows the Italian trainer links behind
      `data-lang-gate="it"`.
- [ ] The existing classifier and counter drills are unchanged.

**Technical Notes:**
`static/js/pages/classifier-drill.js` and `counter-drill.js` are the models for the page;
`migrations/counter_drill.sql` and `task530_counter_drill_test_type.sql` for the test
type. Whether a trainer is a session module is task 32.

**Files to Create / Modify:**
- `services/drill_service.py` — descriptor registry
- `routes/` and `templates/` — the shared drill page
- `static/js/pages/dictionary-drill.js` (new), `templates/profile.html`
- `tests/unit/drill-config.test.js` and a service test

**Verification:**
With a stub descriptor and three fixture rows the page serves a round and records it.

---

## 15. Dictionary: noun_gender (table, build script, drill)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 7, 14

**Description:**
Nouns with gender, articles and plural (target 2,000 rows): the data behind
`article_match`, the plural check of `morphology_slot` and the article shown in
`nl_tl_translation`.

**Acceptance Criteria:**
- [ ] Table (proposed `dim_noun_gender`, with `language_id` so the next gendered
      language reuses it): the profile's fields `lemma`, `gender`, `art_def_sg`,
      `art_indef_sg`, `gender_cue`, `plural`, `art_def_pl`, `plural_type`, `en`, `level`,
      a nullable link to `dim_vocabulary`, UNIQUE (`language_id`, `lemma`, `gender`),
      RLS on, no client write grant.
- [ ] `scripts/build_noun_gender_dictionary.py` loads only
      `PACK/dictionaries/reviewed/noun_gender*.jsonl`, is idempotent, and refuses rows
      that break the cross-field rules the pack validator cannot check: article against
      gender and first sound (lo / uno before s + consonant, z, gn, ps, pn, x, y,
      i + vowel; l' / un' before a vowel or silent h), plural article against the singular
      one, `plural` and `art_def_pl` present unless `plural_type` is `none`.
- [ ] `services/vocabulary_ladder/deterministic/dictionaries.py` exposes a lookup by
      lemma for language 4, cached like `get_index`, empty (not raising) when the table
      is missing.
- [ ] Drill "article": show the noun, choose the article; registered in the shell of
      task 14.

**Technical Notes:**
The profile's review asks for the cross-field rules to be enforced by a build step
because `validate-dict` checks fields one at a time. A noun with two genders has two
rows. The only exception to the plural-article rule is `il dio / gli dei`.

**Files to Create / Modify:**
- `migrations/<task>_dim_noun_gender.sql` (new)
- `scripts/build_noun_gender_dictionary.py` (new)
- `services/vocabulary_ladder/deterministic/dictionaries.py`
- `services/drill_service.py` — article drill descriptor
- `tests/test_noun_gender_dictionary.py` (new)

**Verification:**
`python scripts/language_pack.py validate-dict it noun_gender --reviewed` ends with OK;
the build script reports rows loaded and 0 refused; the lookup returns `lo` / `uno` /
`gli` for `zaino`.

---

## 16. Dictionary: verb_conjugation (table, build script, drill)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 7, 14

**Description:**
Verbs with auxiliary, participle and the forms that cannot be computed (target 600):
the data behind `auxiliary_choice`, `conjugation_form` and the form check of
`morphology_slot`.

**Acceptance Criteria:**
- [ ] Table (proposed `dim_verb_conjugations`): the profile's fields, `present` as a
      six-element text array, `irregular_in` as a text array, UNIQUE
      (`language_id`, `lemma`).
- [ ] `scripts/build_verb_conjugation_dictionary.py` loads the reviewed files only and
      refuses a row whose stored forms contradict the regular pattern of its class
      without the part being listed in `irregular_in` (and the reverse).
- [ ] A pure function `paradigm(row)` returns every cell the profile says is computable:
      the other persons of the imperfect, future and conditional from the stored io form,
      and the present subjunctive (io / tu / lui = stored form, noi = present noi, voi =
      that form with -iate, loro = stored form + no). Unit-tested on `essere`, `andare`,
      `venire`, `finire`, `fare`, `alzarsi`.
- [ ] Drill "conjugation": infinitive + tense + person, typed or chosen.

**Technical Notes:**
Forms are stored bare (no subject or reflexive pronoun). `imperative_tu` is optional;
when `imperative_tu_short` exists both are correct (`vai`, `va'`). The passato remoto is
not stored. Task 3's lemmatiser corrections read this table.

**Files to Create / Modify:**
- `migrations/<task>_dim_verb_conjugations.sql` (new)
- `scripts/build_verb_conjugation_dictionary.py` (new)
- `services/vocabulary_ladder/deterministic/italian_verbs.py` (new) — `paradigm`
- `services/vocabulary_ladder/deterministic/dictionaries.py`, `services/drill_service.py`
- `tests/test_italian_paradigm.py` (new)

**Verification:**
`validate-dict it verb_conjugation --reviewed` ends with OK; `pytest
tests/test_italian_paradigm.py`; `paradigm(andare)['subjunctive']` is
`vada, vada, vada, andiamo, andiate, vadano`.

---

## 17. Dictionary: verb_government (table, build script, drill)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 7, 14

**Description:**
The preposition a verb, adjective or noun takes before its complement (target 350): the
data behind `government_match`, and a check for `preposition_selection`.

**Acceptance Criteria:**
- [ ] Table (proposed `dim_government_patterns`): the profile's fields, UNIQUE
      (`language_id`, `head`, `complement`, `preposition`).
- [ ] Build script loads reviewed files only and refuses: `english_calque` present when
      `differs_from_english` is false; `english_calque` equal to `preposition`; two rows
      of one head and complement with the same `en_pattern`.
- [ ] Lookup returns all rows of a head, so the generator can exclude a preposition that
      another row of the same head and complement makes correct.
- [ ] Drill "preposition after": head + complement kind + `en_pattern`, choose the
      preposition.

**Technical Notes:**
`∅` is a value of `preposition` (direct complement). Heads can be two words
(`avere bisogno`). The dictionary's `source_pos` is `verb`, but authors add adjectives and
nouns: link rows to `dim_vocabulary` by lemma, not by part of speech.

**Files to Create / Modify:**
- `migrations/<task>_dim_government_patterns.sql` (new)
- `scripts/build_verb_government_dictionary.py` (new)
- `services/vocabulary_ladder/deterministic/dictionaries.py`, `services/drill_service.py`
- `tests/test_government_dictionary.py` (new)

**Verification:**
`validate-dict it verb_government --reviewed` ends with OK; the lookup for `pensare`
returns the `a` and the `di` row with different `en_pattern`.

---

## 18. Dictionary: false_friends (table, build script, drill)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 7, 14

**Description:**
Italian words whose form suggests a wrong English meaning (target 200): forced in as
distractors of the translation types and used as the error of `spot_incorrect_sentence`.

**Acceptance Criteria:**
- [ ] Table (proposed `dim_false_friends`): `lemma`, `pos`, `en_lookalike`, `en_meaning`,
      `it_for_lookalike`, `kind`, `level`, with the study language and the learner's
      language as columns (the trap exists for a language pair), UNIQUE on the pair plus
      (`lemma`, `en_lookalike`).
- [ ] Build script loads reviewed files only; warns on a lemma missing from
      `dim_vocabulary`.
- [ ] Lookup by lemma and by English lookalike (both directions are needed: `attualmente`
      -> `actually`; `factory` -> `fattoria`).
- [ ] Drill "false friends": Italian word, choose the real meaning with the lookalike as
      an option.

**Technical Notes:**
Rows are specific to English-speaking learners. Do not serve them to a learner with
another native language; the profile's only gloss language is English, so this is a guard
for later.

**Files to Create / Modify:**
- `migrations/<task>_dim_false_friends.sql` (new)
- `scripts/build_false_friends_dictionary.py` (new)
- `services/vocabulary_ladder/deterministic/dictionaries.py`, `services/drill_service.py`
- `tests/test_false_friends_dictionary.py` (new)

**Verification:**
`validate-dict it false_friends --reviewed` ends with OK; lookup of `libreria` returns
`library` / `bookshop` / `biblioteca`.

---

## 19. Dictionary: collocations (table, build script, drill) and the collocation levels

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 7, 10, 14

**Description:**
Fixed pairs with the wrong partners learners choose (target 500). This dictionary is the
grounding source Italian needs before levels 5 and 8 can be enabled; without one the
collocation family is unsatisfiable and every sense is re-enqueued nightly (audit B1).

**Acceptance Criteria:**
- [ ] Table (proposed `dim_collocation_pairs`): `node`, `node_pos`, `collocate`,
      `pattern`, `phrase`, `wrong_collocates` (text array, 3 or 4), `calque`, `en`,
      `level`, UNIQUE (`language_id`, `phrase`).
- [ ] Build script loads reviewed files only; refuses a `phrase` that does not contain
      `node` and `collocate`, a `calque` that is not the first wrong collocate, and a
      wrong collocate equal to the collocate.
- [ ] `services/vocabulary_ladder/collocation_grounding.py`: `GROUNDING_SOURCES[4]` names
      the dictionary; a pair in it counts as validated. Either export the dictionary to
      `data/collocations/it_collocations.tsv` and add it to `LIST_FILENAMES`, or add a
      dictionary source; a pair absent from it is not validated.
- [ ] Level 5 for a grounded pair uses the row's first three `wrong_collocates` as the
      distractors (none invented); level 8 breaks the sentence with the row's calque or
      another wrong collocate and repairs to the row's phrase.
- [ ] Concrete nouns get levels 5 and 8 only when the dictionary has a pair for them.
- [ ] Only then: section 4b of the SQL is applied and the two rows are enabled in
      `_CAPABILITY_SPEC`.
- [ ] Drill "collocations": phrase with the collocate blanked.

**Technical Notes:**
The profile adds `concrete` to the collocation rows' `pos_classes`, against the app-wide
rule in `config.py` ("concrete nouns skip L5/L8"). With the row enabled, level 5 is
planned for every concrete noun and dropped for those without a grounded pair; confirm
that an ungrounded concrete noun does not then count as missing the collocation family in
`v_sense_family_coverage` (that is exactly the B1 loop). If it does, the family
requirement must be computed per sense from the dictionary, and this task is blocked on
that change. `wrong_collocates` means unacceptable, not rarer: a reviewer must have
confirmed each one.

**Files to Create / Modify:**
- `migrations/<task>_dim_collocation_pairs.sql` (new)
- `scripts/build_collocations_dictionary.py` (new)
- `services/vocabulary_ladder/collocation_grounding.py`, `data/collocations/`
- `services/vocabulary_ladder/asset_pipeline.py` — grounded distractors for language 4
- `services/vocabulary_ladder/config.py` — enable the two rows
- `tests/test_collocation_grounding.py`, `tests/test_capability_matrix.py`

**Verification:**
`validate-dict it collocations --reviewed` ends with OK; for `domanda` level 5 offers
`fare` against `chiedere` and two more row values; after one nightly coverage run no
Italian sense is re-enqueued for the collocation family.

---

## 20. Translation types for Italian (tl_nl_translation, nl_tl_translation)

**Status:** [?] Blocked: no ladder generator exists for these types
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 10, 15, 18

**Description:**
The profile marks both translation types `adapt` ("same type", with false friends forced
in as distractors and nouns answered with their article). In the repository the two
types exist as capability rows for Chinese and Japanese, in the family and context maps,
in `envelope.py` and in the prestudy and intro-drill field maps, with a judge
(`translation_uniqueness`), but no generator under `services/vocabulary_ladder/` produces
them, and the only prompt rows (`tl_nl_translation_generation`,
`nl_tl_translation_generation`) were seeded for Chinese by the archived
exercise-generation schema. So there is nothing to adapt: the generator has to be built,
for all languages or for Italian first.

**Acceptance Criteria:**
- [ ] Decision recorded: build a typed LLM generator for the two types (registered in
      `asset_generators/typed_llm.py`) or leave the Italian rows inert like the Chinese
      and Japanese ones.
- [ ] If built: for a word in `false_friends`, the English lookalike is one of the
      distractors of `tl_nl_translation`, with an explanation naming the Italian word for
      it; for `nl_tl_translation` a noun is shown and answered with its definite article
      from `noun_gender` (`the book: il libro`), and an Italian lookalike of the English
      prompt is a distractor (`factory: fattoria`).
- [ ] Items pass `translation_uniqueness_judge`.

**Technical Notes:**
The capability rows are inserted enabled (as for Chinese and Japanese); with no generator
they produce nothing and cost nothing. If the decision is "inert", say so in the feature
page so that the missing family is not read as a defect.

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/translation.py` (new, if built)
- `services/exercise_generation/schemas/ladder_typed.py`
- `migrations/<task>_translation_generation_prompts.sql` (new, if built)
- `tests/test_typed_llm_generators.py`

**Verification:**
For `attualmente`, the rendered `tl_nl_translation` item has `actually` among its wrong
options and `currently` as the answer.

---

## 21. New type: stress_position (generator, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 7, 13

**Description:**
The Italian analogue of `tone_id_word`: the word is shown split into written syllables
(`te-le-fo-no`), the learner taps the stressed one and then hears the word. Deterministic,
built from the sense's IPA.

**Acceptance Criteria:**
- [ ] `services/vocabulary_ladder/deterministic/stress_position.py`, registered with
      `@register('stress_position')`, added to the import sweep in
      `deterministic/__init__.py`.
- [ ] A rule-based syllabifier for Italian spelling (digraphs gl, gn, sc, ch, gh;
      diphthongs and hiatus; double consonants split) with a unit test of at least 60
      words including `telefono`, `zucchero`, `abitano`, `famiglia`, `aiuola`, `farmacia`,
      `poesia`.
- [ ] The stressed index comes from the IPA's primary stress mark; if the number of
      written syllables and of IPA syllables differ, the builder skips with a reason.
- [ ] Skips, each with a `Skip` reason: fewer than three syllables; a written final
      accent (`città`); a homograph with two stresses (`ancora`, `subito`, `principi`);
      no stress mark in the IPA.
- [ ] Content: `word`, `syllables`, `correct_index`, `pronunciation`, audio reference;
      schema added to the content validator.
- [ ] `static/js/exercise-renderers.js`: `renderStressPosition` (tap a syllable, then
      play audio), an entry in the dispatch map and the instruction string
      `exercises.instruction.stress_position`.
- [ ] Section 4a of the SQL applied for this type and the row enabled in
      `_CAPABILITY_SPEC`.

**Technical Notes:**
The homograph list has no source in the pack: the builder needs a small bundled list of
stress homographs or a flag on the sense. Priority order from the profile (stress on the
third-last syllable or earlier first) is a serving concern, not a build filter. Cap is one
item per word (task 13).

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/stress_position.py` (new),
  `deterministic/__init__.py`
- `services/vocabulary_ladder/deterministic/italian_syllables.py` (new)
- `static/js/exercise-renderers.js`, `services/exercise_explanations.py`
- `tests/test_deterministic_generators.py`, `tests/test_italian_syllables.py` (new),
  `tests/unit/exercise-renderers.test.js`

**Verification:**
`pytest tests/test_italian_syllables.py tests/test_deterministic_generators.py`;
`npm test`; a served item for `telefono` marks the second syllable.

---

## 22. New type: article_match (generator, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 13, 15

**Description:**
The analogue of `classifier_match`, for nouns. From one `noun_gender` row the generator
builds four modes in rising difficulty: definite article singular, indefinite article,
definite article with the plural form shown, preposition + article.

**Acceptance Criteria:**
- [ ] `deterministic/article_match.py`, registered; skips with a reason when the noun is
      not in the dictionary.
- [ ] Mode (a) `___ zaino`: options `il, lo, la, l'`; (b) options `un, uno, una, un'`;
      (c) `___ uova`: options `i, gli, le`, skipped when the row has no plural; (d) one of
      a, di, da, in, su fused with the article (`nello zaino`, `dell'acqua`,
      `sugli alberi`), options are the forms of that one preposition.
- [ ] A pure function builds the 35 fused forms from preposition + article and is tested
      on all of them.
- [ ] The explanation is generated from the row: gender, `gender_cue` and the first-sound
      rule, in English.
- [ ] Each mode is a separate item with a `mode` field; the cap in
      `CONTEXT_FREE_TYPE_CAPS` is 4.
- [ ] Renderer: `renderMeasureWord` reused or a variant that shows the elided form
      attached to the noun (`l'amico`, not `l' amico`); instruction string added.
- [ ] Section 4a applied for this type; row enabled in `_CAPABILITY_SPEC`.

**Technical Notes:**
The profile's review notes a reviewer may want the fused prepositions (mode d) as their
own type; it is one type with a `mode` field so that the split stays cheap. With `l'` and
`un'` the blank and the noun are written together: the stem must not show a space.

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/article_match.py` (new), `__init__.py`
- `services/vocabulary_ladder/config.py` — cap
- `static/js/exercise-renderers.js`, `services/exercise_explanations.py`
- `tests/test_deterministic_generators.py`, `tests/unit/exercise-renderers.test.js`

**Verification:**
For `zaino` the four items have answers `lo`, `uno`, `gli`, and (for `in`) `nello`.

---

## 23. New type: auxiliary_choice (generator, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 13, 16

**Description:**
For verbs: the infinitive, a subject and passato prossimo; the learner chooses between the
avere and the essere form, with and without the right participle agreement
(`Maria + andare`: `è andata`, `ha andato`, `è andato`, `ha andata`).

**Acceptance Criteria:**
- [ ] `deterministic/auxiliary_choice.py`, registered; built from the row's `auxiliary`
      and `past_participle`.
- [ ] For essere verbs the subject is feminine or plural so that the agreement shows; for
      a reflexive the pronoun precedes the auxiliary (`si è alzata`).
- [ ] Verbs with `auxiliary = both` are skipped with a reason; `auxiliary_note` is used
      only as explanation text and never parsed.
- [ ] Exactly one option is correct; the four options are distinct strings.
- [ ] Renderer: a four-option choice (the generic choice renderer if it shows the prompt
      line `Maria — andare — passato prossimo`); instruction string added.
- [ ] Section 4a applied; row enabled in `_CAPABILITY_SPEC`.

**Technical Notes:**
A small closed list of subjects (`Maria`, `Le ragazze`, `Io (Paolo)`, `Noi`) with gender
and number is enough; participle agreement is `-o / -a / -i / -e` on the stored masculine
singular. For an avere verb the agreeing form (`ha andata`-style) is always a distractor.

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/auxiliary_choice.py` (new), `__init__.py`
- `static/js/exercise-renderers.js`, `services/exercise_explanations.py`
- `tests/test_deterministic_generators.py`, `tests/unit/exercise-renderers.test.js`

**Verification:**
`andare` with `Maria` gives the answer `è andata`; `finire` yields no item and a Skip
"auxiliary is both".

---

## 24. New type: conjugation_form (generator, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 13, 16

**Description:**
One cell of a verb's paradigm, without a sentence: infinitive + tense + person
(`venire, presente, loro`); the learner chooses, and at higher mastery types, the form
(`vengono`). `morphology_slot` stays the in-sentence version.

**Acceptance Criteria:**
- [ ] `deterministic/conjugation_form.py`, registered; cells come from `paradigm(row)`
      (task 16); a row without `imperative_tu` gets no imperative cell.
- [ ] Distractors are generated: the regular form the verb would have (`venono`), another
      person, another tense; none equals a correct form.
- [ ] When the row has `imperative_tu_short` both imperatives are accepted and neither is
      a distractor.
- [ ] Cells listed in `irregular_in` are built first; the per-word cap is explicit in
      `CONTEXT_FREE_TYPE_CAPS`.
- [ ] Typed mode grades with the Italian normalisation of task 12 (accents significant:
      `andrò`, not `andro`).
- [ ] Renderer shows infinitive, tense name and person; choice and typed input;
      instruction string added.
- [ ] Section 4a applied; row enabled in `_CAPABILITY_SPEC`.

**Technical Notes:**
"The regular form the verb would have" needs a regular-conjugation function per class
(`are`, `ere`, `ire`, `ire_isc`, `rre`): the same one the build script of task 16 uses to
check `irregular_in`. The switch from choosing to typing "at higher mastery" has no
existing mechanism for a deterministic type; decide whether it is two items with a `mode`
field or a serve-time switch.

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/conjugation_form.py` (new), `__init__.py`
- `services/vocabulary_ladder/config.py` — cap
- `static/js/exercise-renderers.js`, `services/exercise_explanations.py`
- `tests/test_deterministic_generators.py`, `tests/unit/exercise-renderers.test.js`

**Verification:**
`venire / presente / loro` has the answer `vengono` and the distractor `venono`.

---

## 25. New type: government_match (generator, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 13, 17

**Description:**
For verbs, adjectives and nouns that fix the preposition of their complement: the head
with a gap and the kind of complement (`cominciare ___ + infinitive`), with the row's
English pattern shown; the learner chooses among four of ∅, a, di, da, in, con, su, per.

**Acceptance Criteria:**
- [ ] `deterministic/government_match.py`, registered; one item per government row of the
      head.
- [ ] The English calque is always an option when the row has `differs_from_english`.
- [ ] A preposition that another row gives for the same head and complement is never a
      distractor (pensare a / di; chiedere a qualcuno / chiedere qualcosa).
- [ ] Answer, example and explanation come from the row; `en_pattern` is shown in the
      prompt.
- [ ] Renderer shows `∅` as "no preposition" with its own label; instruction string
      added.
- [ ] Section 4a applied; row enabled in `_CAPABILITY_SPEC`.

**Technical Notes:**
The capability row's classes are action, property and abstract; a head is matched by
lemma, so an adjective or noun head is served for the adjective's or noun's sense.

**Files to Create / Modify:**
- `services/vocabulary_ladder/deterministic/government_match.py` (new), `__init__.py`
- `static/js/exercise-renderers.js`, `services/exercise_explanations.py`
- `tests/test_deterministic_generators.py`, `tests/unit/exercise-renderers.test.js`

**Verification:**
`dipendere + noun` has the answer `da` and the option `su`; the item for `pensare a` never
offers `di`.

---

## 26. New type: preposition_selection (generator, judge, renderer, tests)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 3, 10, 13, 17

**Description:**
The analogue of `particle_selection` and the only new authored block: one preposition of
a core sentence is blanked and the learner picks it from four. Block shape (profile):
`{"sentence_index": n, "sentence": "<sentence with ___>", "options": [4 x {"text",
"is_correct", "explanation"}]}`; declines with `{"declined": "no_preposition"}`.

**Acceptance Criteria:**
- [ ] `asset_generators/preposition_selection.py`: a `TypedLLMGenerator` registered for
      `preposition_selection`, added to `_load_generators`, with
      `TASK_NAME = 'ladder_preposition_selection_generation'`.
- [ ] The tokeniser offers the candidate slots: simple prepositions (di, a, da, in, con,
      su, per, tra, fra) and fused forms (al, della, nello, sugli); the model chooses
      among them. A blank inside a content word is impossible.
- [ ] All four options have the same shape (all simple, or all fused with the same
      article form), checked in code.
- [ ] A judge (`judges/preposition.py`, key `preposition`, prompt row
      `ladder_preposition_judge`) rejects an item where a second option also gives a
      natural sentence. Reusing `judges/particle.py` with an Italian row is acceptable if
      the capability row's `judge_key` is changed to `particle` in the SQL and the spec.
- [ ] Schema in `schemas/ladder_typed.py` (`TYPED_SCHEMAS`); `fat_seed.py` knows the
      block (`ESCAPE_TOKENS['preposition_selection'] = 'no_preposition'`, `_TYPED_FIELDS`,
      the slot check that exists for particles); `scripts/fat_seed_runner.py` and
      `scripts/run_content_build.py` list the two task names.
- [ ] The two prompt rows are seeded for language 4.
- [ ] `renderParticleSelection` reused or copied; instruction string
      "Choose the correct preposition:"; prestudy and intro-drill field maps
      (`services/prestudy.py`, `services/intro_drill.py`, `static/js/prestudy/prestudy.js`)
      list the type next to `particle_selection`.
- [ ] Section 4a applied; row enabled in `_CAPABILITY_SPEC`.

**Technical Notes:**
The pack's fat-seed documents author this block per sentence in the named-field shape
above; the live typed blocks use a numeric contract (key 0 is the option array). Decide
which the generator stores and convert in one place. When the government dictionary has a
row for the target word and the blanked preposition, the answer must agree with it.

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/preposition_selection.py` (new),
  `typed_llm.py`
- `services/exercise_generation/judges/preposition.py` (new)
- `services/exercise_generation/schemas/ladder_typed.py`, `schemas/envelope.py`
- `services/vocabulary_ladder/fat_seed.py`, `scripts/fat_seed_runner.py`,
  `scripts/run_content_build.py`
- `migrations/<task>_preposition_selection_prompts.sql` (new)
- `static/js/exercise-renderers.js`, `static/js/prestudy/prestudy.js`,
  `services/prestudy.py`, `services/intro_drill.py`
- `tests/test_typed_llm_generators.py`, `tests/test_fat_seed.py`,
  `tests/unit/exercise-renderers.test.js`

**Verification:**
`pytest tests/test_typed_llm_generators.py tests/test_fat_seed.py`; an item on "Abito ___
Italia da tre anni." has the answer `in` and the judge rejects a variant offering both
`in` and a second acceptable option.

---

## 27. Adapted LLM types checked against the dictionaries (morphology_slot, word_family)

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 10, 15, 16

**Description:**
`morphology_slot` now covers nouns (plural formation has no type of its own) and must
agree with the dictionaries; `word_family` carries over from English, where its generator
has only ever run for language 2.

**Acceptance Criteria:**
- [ ] After generation, every form offered as correct in a `morphology_slot` item is
      checked against `verb_conjugation` (via `paradigm`) or `noun_gender` when the word
      is there; a disagreement rejects the item with a logged reason.
- [ ] `word_family` generation runs for language 4: any English-only assumption in
      `asset_generators/word_family.py` and `judges/relation.py` is removed; the prompt
      declines with `no_family`.
- [ ] `fat_seed.py` validation applies the same dictionary check to reviewed documents.

**Technical Notes:**
Neither `word_family` nor the collocation blocks are in the first fat-seed slice (profile
notes), so the gold set of task 28 does not exercise `word_family`: test it on live
generation for 20 senses.

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/l4_morphology.py`, `word_family.py`
- `services/vocabulary_ladder/fat_seed.py`
- `tests/test_typed_llm_generators.py`, `tests/test_prompt_split_l4_l8.py`

**Verification:**
A `morphology_slot` item offering `uomi` as the correct plural of `uomo` is rejected; a
`word_family` item for `decidere` offers `decisione`.

---

## 28. Fat-seed run for Italian: gold set of 100, then the full pack

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** L (1-2d)
**Depends On:** 10, 12, 13, 26, 27

**Description:**
Replace the pack's shape check with the real fat-seed validation and upload. The pack's
`validate-fatseed` checks only the document shape; `services/vocabulary_ladder/fat_seed.py`
validates exactly as upload would. Run a gold set of 100 senses first, read the rejects,
then run the rest.

**Acceptance Criteria:**
- [ ] `scripts/fat_seed_runner.py` validates the pack's reviewed documents
      (`PACK/fat_seed/reviewed/`) for language 4 with every Italian check on: character
      set, sentence length, IPA stress mark, elision units, the dictionary checks of
      task 27 and the preposition slot check of task 26.
- [ ] 100 senses spread over parts of speech and levels are uploaded and rendered; each
      enabled type has at least one served item checked by hand in the browser.
- [ ] Reject reasons are tabulated; a reason above 5 % goes back to the content team as
      a brief change, not as a code workaround.
- [ ] Exercise audio is generated with the Italian voices
      (`scripts/backfill_exercise_audio.py`).
- [ ] Only then the remaining reviewed documents are uploaded.

**Technical Notes:**
The documents are one named-field JSON per sense with variants A and B. Collocation
blocks and `word_family` are not in the first slice; `v_sense_family_coverage` must not
treat their absence as a gap while the collocation rows are disabled.

**Files to Create / Modify:**
- `scripts/fat_seed_runner.py`, `services/vocabulary_ladder/fat_seed.py` — Italian checks
- `tests/test_fat_seed.py` — Italian fixtures

**Verification:**
The runner's report shows 100 senses uploaded; `SELECT exercise_type, count(*) FROM
exercises WHERE language_id = 4 GROUP BY 1` lists every enabled type; a practice session
in Italian serves and grades items of each.

---

## 29. Grammar drill page for the language

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 2, 5

**Description:**
The grammar drill page is Chinese-only: the template has `lang="zh"` and a fixed manifest
path, the scripts read `item.zh` and `item.py` and join tiles without spaces, and the
store key is `ld.grammar.zh.v1`. The pack's `build` writes `static/data/grammar/it/` with
a manifest that declares `fields.sentence` and `token_joiner`; make the page read those.

**Acceptance Criteria:**
- [ ] `templates/grammar_drill.html` takes the language from the user's study language:
      `lang`, `data-language-id` and the manifest path `static/data/grammar/<code>/`.
- [ ] `static/js/grammar/*.js` read the sentence through the manifest's `fields.sentence`
      (`tl` for Italian, `zh` for Chinese) and the romanisation only when
      `fields.romanisation` is set; tiles are joined with the manifest's `token_joiner`.
- [ ] The store key is `ld.grammar.<code>.v1`; a Chinese learner's stored progress is
      still read from `ld.grammar.zh.v1`.
- [ ] Typed answers on the Italian page use the Italian rule (case-insensitive, accents
      significant, apostrophes straightened).
- [ ] `templates/profile.html`: the grammar link is shown for `zh` and `it`.
- [ ] `services/grammar_drill_tracking.py` and `routes/grammar_drill.py` accept language
      id 4.
- [ ] `python scripts/language_pack.py build it --check` passes before the files are
      served.

**Technical Notes:**
The page's contract is `data/grammar_drills/zh/SPEC.md`; the pack's is
`.claude/skills/new-language-swarm/GRAMMAR_SPEC.md`. `build` reads `grammar/reviewed/`
only. About a dozen places in `static/js/grammar/` read `item.zh` / `item.py`.

**Files to Create / Modify:**
- `templates/grammar_drill.html`, `templates/profile.html`
- `static/js/grammar/{app,data,render,text,check,store,select,round}.js`
- `services/grammar_drill_tracking.py`, `routes/grammar_drill.py`
- `tests/unit/grammar-*.test.js` — an Italian manifest fixture

**Verification:**
`npm test`; with study language Italian the page loads the Italian manifest, a jumbled
item shows space-separated tiles with `l'amico` as one tile, and a finished round is
recorded for language 4. With Chinese the page behaves as before.

---

## 30. Test generation for Italian: prompt rows, voices, tier thresholds

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 3, 4, 7

**Description:**
Make reading and listening tests generable in Italian. Prose and question texts fall back
to the English rows, which steers Italian output with English instructions; the model
lookup does not fall back and raises.

**Acceptance Criteria:**
- [ ] Rows with `language_id = 4` for `prose_generation`, `title_generation`, the six
      `question_*` tasks, `test_answer_entailment` and `test_distractor_plausibility`.
- [ ] `services/tier_classifier.py`: thresholds, calibration label and the prompt strings
      for `it`; until a calibration set exists the label says uncalibrated.
- [ ] `services/test_generation/difficulty_scorer.py` scores Italian with wordfreq `it`.
- [ ] Listening audio uses the two Italian voices; a sample is listened to by an Italian
      speaker.
- [ ] Dictation: accents are significant; the word count uses whitespace.

**Technical Notes:**
The profile's levels are CEFR bands A1 to C1; map them to the app's tiers the way the
English tiers are mapped. `grammar_check_enabled` stays false unless a tool is wired.

**Files to Create / Modify:**
- `migrations/<task>_it_test_prompts.sql` (new)
- `services/tier_classifier.py`, `services/test_generation/difficulty_scorer.py`
- `services/dictation/tokenizer.py` (confirm; change only if needed)

**Verification:**
One reading and one listening test are generated for Italian in a staging run, pass both
judges, and play audio in an Italian voice.

---

## 31. Dual translation and sentence references

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 2, 30

**Description:**
Open dual translation for the pair English (L1) and Italian (L2).

**Acceptance Criteria:**
- [ ] Rows with `language_id = 4` for `dual_translation_tier1`, `_tier2`, `_tier3`.
- [ ] `services/dual_translation/prompts.py` and `single_call_grader.py` have an Italian
      L2 branch.
- [ ] `services/dual_translation/sentence_refs.py`: length-ratio bounds for (`it`, `en`)
      and (`en`, `it`); Italian is not in `_CJK_CODES`.
- [ ] `dt_taxonomy` gains the pairs `it` and `en-it` in a new cumulative version, with
      subtypes that include the profile's grammar features: gender and article, agreement,
      auxiliary choice, preposition, clitic pronoun, tense and aspect (passato prossimo /
      imperfetto), mood (congiuntivo), false friend, register (tu / Lei).
- [ ] `scripts/sentence_ref_runner.py --lang it` produces references for Italian tests.

**Technical Notes:**
Each taxonomy version row is a complete taxonomy (see `migrations/dt_taxonomy_ja_seed.sql`):
copy the active version and add the two pairs.

**Files to Create / Modify:**
- `migrations/<task>_it_dual_translation_prompts.sql`, `<task>_dt_taxonomy_it_seed.sql` (new)
- `services/dual_translation/{prompts,single_call_grader,sentence_refs}.py`

**Verification:**
A translation of one Italian test sentence is graded and returns error cards with the new
subtypes.

---

## 32. Study plan templates and session modules

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** 1, 14, 29

**Description:**
A study plan cannot be created for a language without templates. Seed three (30, 45, 60
minutes a day) and decide which Italian trainers are session modules.

**Acceptance Criteria:**
- [ ] Three `dim_study_plan_templates` rows for Italian (ids 401 to 403, by
      `language_code = 'it'`), modelled on the English ones: reading, listening,
      dictation; no pinyin, classifier or pitch-accent module.
- [ ] Decision recorded: whether the grammar drill and the dictionary trainers become
      modules. If yes, the module names are added to `ALL_MODULES` in
      `services/study_plan_service.py` and to the CHECK
      `user_study_plans_excluded_modules_known` together (`test_session_modules.py` pins
      both).

**Technical Notes:**
The existing seeds use template ids 101 to 103 (Chinese) and 201 to 203 (English); follow
the pattern. `dim_languages.new_word_minutes_est` is filled by the nightly job once
Italian words are introduced; until then the default of 3.0 minutes applies.

**Files to Create / Modify:**
- `migrations/<task>_it_study_plan_templates.sql` (new)
- `services/study_plan_service.py`, `migrations/session_module_exclusions.sql` successor
  (only if modules are added)

**Verification:**
Creating a study plan for Italian with 30 minutes a day succeeds and the daily session
lists reading, listening, dictation, flashcards and practice.

---

## 33. Placement and calibration pool

**Status:** [ ] Not Started
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** 7, 8, 28

**Description:**
Open the placement test and knowledge calibration for Italian once vocabulary and
exercises exist.

**Acceptance Criteria:**
- [ ] `routes/calibration.py` `_SUPPORTED_LANGUAGE_IDS` and
      `services/calibration_placement.py` (`SUPPORTED_LANGUAGE_IDS`,
      `PLACEMENT_LANGUAGES`, the per-language branches near `pd.LANG_EN` / `pd.LANG_JA`)
      include language 4; `services/placement_design.py` has `LANG_IT`, and its
      script-family helper (`'en' if language_id == LANG_EN else 'cjk'`) returns the
      Latin branch for Italian instead of falling through to `cjk`.
- [ ] The calibration pool and distractor cache are built for (4, English definitions)
      (`scripts/build_calibration_distractor_cache.py`).
- [ ] Italian has no pronunciation mode in placement; the frame for `4:2` exists.

**Technical Notes:**
Depends on the decisions of task 8. Placement frames are keyed
`<word language>:<definition language>`.

**Files to Create / Modify:**
- `routes/calibration.py`, `services/calibration_placement.py`, `services/placement_design.py`
- `static/js/pages/placement.js`, `calibration.js` (maps from task 5)

**Verification:**
A placement session in Italian starts, serves 20 items and writes a result.

---

## 34. Go-live

**Status:** [ ] Not Started
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** 5, 28, 29, 30, 32, 33

**Description:**
Activate the language: apply section 4c of the SQL, show the language card, and run the
end-to-end check as a new user.

**Acceptance Criteria:**
- [ ] `UPDATE dim_languages SET is_active = true WHERE id = 4` applied.
- [ ] A new user can choose Italian, take placement, get a study plan, complete a daily
      session with a test, a practice block of ladder exercises, the grammar drill and one
      dictionary trainer.
- [ ] The nightly jobs (coverage, IRT calibration, new-word minutes) complete with Italian
      present; no Italian sense is re-enqueued repeatedly.
- [ ] `wiki/` pages for the language are written by the wiki owner (overview, the six
      new types, the five dictionaries, an ADR for the collocation grounding and for the
      accent rule).

**Technical Notes:**
Everything before this task is invisible to users. If a nightly job fails on language 4,
set `is_active = false` again: nothing else needs to be undone.

**Files to Create / Modify:**
- `migrations/<task>_italian_go_live.sql` (new) — section 4c
- `wiki/` (wiki owner)

**Verification:**
The acceptance walk-through above, on staging and then on production.

---

## Not attempted and why

- No prompt text was written. `prompt_tasks.txt` lists the task names; the prompts are
  tasks 9, 10, 26, 30 and 31.
- No table DDL was written for the five dictionaries: the table names above are
  proposals, and the columns are the profile's `dictionaries[].fields`.
- The live database was not read. Everything said about existing rows comes from the
  files in `migrations/` and from `wiki/database/schema.tech.md`.
