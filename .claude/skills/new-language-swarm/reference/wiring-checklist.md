# Wiring checklist: making a new study language live

The content team does not do this; the wiring agent turns it into
`wiring/tasks.md` and pending SQL for the language. Line numbers are from
2026-11-28 and drift: grep before editing.

## Database (pending SQL only, never applied by the team)

- `dim_languages`: one row (id, `language_code`, names, `tts_voice_ids` with two
  Azure neural voices, `tts_speed`, `grammar_check_enabled`).
- `dim_exercise_capabilities`: one row per type the profile's `ladder` keeps
  (PK `language_id, type_code`). Without rows the language gets the legacy full
  ladder, including collocation levels with no grounding source.
- `prompt_templates`: rows per `(task_name, language_id)`. Ladder generators and
  judges fail without them (`services/prompt_service.py` `get_template_config`);
  test and topic generation fall back to the English rows.
- `dim_study_plan_templates` (3 per language), `dt_taxonomy` seed, session
  module exclusions, new dictionary tables for the language's own lookups.
- SQL functions with `CASE WHEN p_word_language_id = 1 / 3`:
  `calibration_placement_rpcs.sql`, `calibration_pronunciation_mode.sql`,
  `knowledge_calibration_inputs.sql`, `knowledge_report_words.sql`.

## Backend

- Language set: `config.py` (`Config.LANGUAGES`, `VALID_LANGUAGE_IDS`,
  `LANGUAGE_CODE_TO_ID`), `routes/calibration.py` `_SUPPORTED_LANGUAGE_IDS`,
  `services/calibration_placement.py`.
- Copies of the id-to-code map: `services/vocabulary_ladder/asset_pipeline.py`,
  `asset_generators/{_split_base,prompt1_core,prompt2_exercises,prompt3_transforms}.py`,
  `vocabulary_ladder/config.py` (`TIER_GATE_LANG_CODES`, `_CAPABILITY_SPEC`,
  `LANGUAGE_VALIDATION_PROFILES`), `definition_serving.py`,
  `services/exercise_explanations.py`, `services/exercise_content/store.py`,
  `services/intro_drill.py`, `services/corpus/ingestion.py`,
  `services/dual_translation/sentence_refs.py`, `services/tier_classifier.py`,
  `services/categorical_maps.py`, `services/llm_service.py`,
  `services/llm_output_cleaner.py`, `services/vocabulary/sense_generator.py`.
- wordfreq maps: `services/vocabulary/frequency_service.py`,
  `services/test_generation/difficulty_scorer.py`.
- NLP processors (three registries): `services/vocabulary/pipeline.py`
  `_PROCESSOR_CLASSES` + `services/vocabulary/config.py` `_NLP_METADATA`;
  `services/exercise_generation/language_processor.py` `for_language`;
  `services/corpus/tokenizers.py` `get_tokenizer`. Add the model to
  `requirements.txt`.
- Validators with no branch for the language (they pass silently):
  `services/vocabulary/language_detection.py`,
  `services/word_list_import/validation.py`.
- Collocation grounding: `services/vocabulary_ladder/collocation_grounding.py`
  (`GROUNDING_SOURCES`, `LIST_FILENAMES`), `data/collocations/`.
- Dual translation L1/L2 branches: `services/dual_translation/prompts.py`,
  `single_call_grader.py`.
- Single-language features to open or copy: `services/drill_service.py`
  (classifier / counter drills), `services/grammar_drill_tracking.py`.

## Scripts and offline tooling

- About 35 scripts carry their own `LANG_ID` map or `choices=['zh','en','ja']`;
  the ones the content path needs first: `export_exercise_worklist.py`,
  `export_sense_seed_worklist.py`, `export_gloss_worklist.py`,
  `upload_senses.py`, `load_vocab_list.py`, `render_existing_assets.py`,
  `sentence_ref_runner.py`, `backfill_sense_embeddings.py`.
- `scratch_offline/nt_lang.py` `LANGUAGES`, `nt_pipeline.py` `--lang`,
  `export_offline_worklist.py` (reads `ja_standard` / `reading`; needs the
  pack's `tl_standard` / `pronunciation`).
- `scripts/grammar_drills.py` is Chinese-only (TASK-1266); the pack's drills
  are built by `scripts/language_pack.py build`.

## Frontend

- Id-to-code maps: `static/js/pages/{language-selection,placement,knowledge,calibration}.js`,
  `static/js/prestudy/prestudy.js`, `static/js/session/players/prestudy.js`.
- `templates/language_selection.html` (three hard-coded cards),
  `static/js/pages/study-plan.js` (flags), `pages/profile.js` (native-language
  picker), `pages/base-head.js` (fonts).
- Grammar drill page: `templates/grammar_drill.html` (`lang="zh"`,
  manifest path), `static/js/grammar/*.js` read `item.zh` / `item.py` and
  join tiles without spaces; store key `ld.grammar.zh.v1`;
  `data-lang-gate="zh"` in `templates/profile.html`. The pack's build writes
  `fields.sentence` and `token_joiner` into the manifest for this.
- New renderers for every ladder row the profile marks `new`.

## Order that keeps each step testable

1. `dim_languages` row + config maps + NLP processors (the language can be
   selected; nothing to study yet).
2. Vocabulary and senses through the sense write path, glosses, embeddings.
3. Prompt rows + capability rows, then the real fat-seed runner replaces the
   shape check (gold set of 100 senses first).
4. Drill page for the language, then the language's own trainers.
5. Tests: prompt rows, tier thresholds, sentence references, placement pool.
