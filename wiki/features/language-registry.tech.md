---
title: Language Registry — Technical Specification
type: feature-tech
status: complete
prose_page: language-registry.md
last_updated: 2026-11-28
dependencies:
  - "module: services/language_registry.py (no application imports)"
  - "module: services/language_readiness.py"
  - "script: scripts/build_language_registry_js.py -> static/js/language-registry.js"
  - "script: scripts/check_language.py"
  - "table: dim_languages (ids and codes must match the registry)"
breaking_change_risk: medium
---

# Language Registry — Technical Specification

## Architecture Overview
```
services/language_registry.py   Language(id, code, name, display, native_name, locale, flag, glyph,
        │                                script, status, legacy_codes, wordfreq, langdetect,
        │                                web_font_sans, web_font_serif, features)
        ├─ config.py                 Config.LANGUAGES / VALID_LANGUAGE_IDS / LANGUAGE_CODE_TO_ID
        ├─ services/, routes/, utils/   module constants keep their names, values come from the registry
        ├─ scripts/, scratch_offline/, Corpuses/   maps and argparse choices
        ├─ app.py context processor  study_languages, native_language_choices -> templates
        └─ scripts/build_language_registry_js.py -> static/js/language-registry.js (window.LinguaLanguages)
services/language_readiness.py   CHECKS (plug-in points per language), DATABASE_STEPS
```
Registered: 1 `zh`, 2 `en`, 3 `ja` (active); 4 `it` (planned). The registry imports nothing from the application, so `config.py` and scripts that avoid the app can import it (`services/__init__.py` is empty).

## Database Impact
None. `dim_languages` stays the runtime source for TTS voices and display order; its ids and codes must equal the registry's. No migration.

## API / RPC Surface
No route. Python API (`from services import language_registry`), every lookup hides planned languages unless `include_planned=True`:

### `find(ref, include_planned=False) -> Language | None`
- **Purpose:** resolve an id, a code (current or legacy, any case), a digit string or a `Language`.
- **Returns:** `None` for unknown, for `bool`, and for a planned language without the flag.

### `get(ref, include_planned=False) -> Language`
- **Errors:** `KeyError` naming the registered languages.

### Maps and lists
`id_to_code()`, `code_to_id(legacy=False)`, `id_to_display()`, `code_to_display()`, `ids()`, `codes()`, `code_of(ref, default)`, `id_of(ref, default)`, `wordfreq_codes()`, `langdetect_to_code()`, `legacy_config()`, `native_language_choices(default_code)`. Each returns a fresh object.

### Script family
`is_cjk(ref)`, `cjk_ids()`, `cjk_codes()`, `token_joiner(ref)` (`''` for CJK, `' '` otherwise and for unknown), `script_family(ref)`, `needs_ime(ref)`. `Language.spaced`, `.token_joiner`, `.needs_ime`.

### Features
`has_feature(ref, feature)` (False for an unknown language, `KeyError` for an unknown feature), `ids_with(feature)`, `codes_with(feature)`. Features: `pinyin`, `tones`, `traditional_variants`, `furigana`, `pitch_accent`, `particles`, `classifier_drill`, `counter_drill`, `grammar_drills`, `pronunciation_calibration`, `translation_exercises`.

### `language_readiness.report(ref) -> list[Result]`, `blockers(ref)`
- **Purpose:** run every plug-in check for a language (planned included).
- **Required checks:** vocabulary processor (`services/vocabulary/pipeline.py` `_PROCESSOR_CLASSES`), NLP metadata (`services/vocabulary/config.py` `_NLP_METADATA`), exercise processor (`services/exercise_generation/language_processor.py` `PROCESSOR_CLASSES`), capability rows (`_CAPABILITY_SPEC`), validation profile (`LANGUAGE_VALIDATION_PROFILES`), wordfreq code, `lang_select.name_<code>` in every `static/i18n/*.json`, web fonts for a CJK script.
- **Optional checks:** corpus tokenizer (`TOKENIZER_CLASSES`), langdetect codes, script heuristic in `language_detection.py`, fitted tier thresholds, collocation grounding source, fat-seed cheat sheet.
- **CLI:** `python scripts/check_language.py` (one line per language) or `<code>` (full list, database steps, exit 1 when a required check fails, 2 when the code is not registered). On 2026-11-28: zh 8/8 required, en 8/8, ja 8/8, it 2/8.

## Component Specification (if UI)
### `window.LinguaLanguages` (`static/js/language-registry.js`, generated)
- Loaded synchronously in `templates/base.html` before `js/pages/base-head.js`; every template extends `base.html`. Unit tests evaluate the real file in `tests/unit/setup.js`.
- **API:** `list(includePlanned)`, `find(ref, includePlanned)`, `idToCode()`, `codeToId(includePlanned, legacy)`, `codeOf(ref, fallback)`, `idOf(ref, fallback)`, `hasFeature(ref, feature)`, `isCjk(ref)`, `flagOf(ref, fallback)`. Language objects: `id, code, name, nativeName, locale, flag, glyph, script, spaced, active, legacyCodes, fontSans, fontSerif, features`.
- Excluded from prettier (`.prettierignore`); declared a readonly global in `eslint.config.js`.

### Templates
`language_selection.html`, `onboarding.html`, `word_list.html` and the native-language prompt in `base.html` loop over `study_languages` / `native_language_choices` (context processor in `app.py`).

## Adding a language
1. Add a `Language(...)` with `status=PLANNED`; run `python scripts/build_language_registry_js.py`.
2. `python scripts/check_language.py <code>` and build each missing required item.
3. Apply the database steps it prints (the content pack's `wiring/pending_language.sql` holds the first two for Italian).
4. Set `status=ACTIVE`, rebuild the browser copy, run the full test suite: `tests/test_language_readiness.py` then requires the language to pass every required check.

## Key Architectural Decisions
1. **Decision:** a Python module is the source of truth; the browser copy is generated. See [[decisions/ADR-068-language-registry]].
   - **Rationale:** scripts and `config.py` need it without a database or a request.
   - **Alternatives rejected:** reading `dim_languages` everywhere; a JSON file read by both sides.
2. **Decision:** existing module-level constants keep their names and are assigned from the registry.
   - **Rationale:** tests and callers import them; behaviour for ids 1 to 3 is unchanged.
   - **Alternatives rejected:** replacing every use with a registry call in one pass.
3. **Decision:** features are named flags; script family is separate.
   - **Rationale:** "CJK" decided joining and input, while pinyin or furigana are per language; conflating them is what made `in (1, 3)` checks wrong for a third CJK language.
4. **Decision:** a guard test instead of a convention.
   - **Rationale:** the previous "single source of truth" comment in `config.py` did not stop about 100 copies.

## Not migrated (per-language logic the registry does not describe)
- Single-language trainers: `services/drill_service.py`, `services/grammar_drill_tracking.py`, `routes/grammar_drill.py` (RQ1).
- `_CAPABILITY_SPEC` in `services/vocabulary_ladder/config.py` (RQ2).
- NLP plug-ins and word-splitting branches: `services/corpus/classifier.py`, `corpus/verifier.py`, `test_generation/agents/prose_writer.py`, `dictation/tokenizer.py`, `vocabulary/language_detection.py`, `vocabulary_ladder/deterministic/definition_match.py`.
- Prompt wording, labels and fitted thresholds: `services/tier_classifier.py`, `categorical_maps.py`, `dual_translation/prompts.py`, `single_call_grader.py`, `repair/hints.py` `TEMPLATE_L1S`.
- Frontend: seal glyph tables (six files), default study language when none is stored, `data-lang-gate` attributes asserted by `tests/test_redesign_shell.py`.
- SQL functions with `CASE WHEN p_word_language_id = 1 / 3`.

## Security Considerations
No new input surface. Planned languages are rejected wherever the app validates a language id, because every set of valid ids is built without them.

## Testing Strategy
`tests/test_language_registry.py` (14): lookups, legacy codes, planned visibility, script and feature helpers, `Config` values, duplicate refusal, browser copy freshness, and two guards that scan Python and JavaScript for literal language maps and `choices=[... 'zh' ...]`. `tests/test_language_readiness.py` (5): active languages pass every required check, no check errors, Italian's missing set, processor registries match the registry codes, CLI exit codes. Full runs on 2026-11-28: pytest 6,735 passed, 16 skipped (`tests/test_prewrite_explanations_anthropic_batch.py` not collected: `anthropic` is not in the requirements); vitest 1,140 passed in 55 files; `npm run check` 0 errors, 2 known warnings.
