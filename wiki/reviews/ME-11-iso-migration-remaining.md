# ME-11 — ISO Language Code Migration: Remaining Patch

**Goal:** Replace app-convention `'jp'` → ISO `'ja'`, `'cn'` → ISO `'zh'` across all remaining call sites.

**Already done in this session (verified):**
- `config.py` — `LANGUAGES` dict + docstrings
- `services/test_generation/difficulty_scorer.py` — `_LANG_MAP`
- `services/vocabulary/frequency_service.py` — `_LANG_MAP` + docstring
- `services/vocabulary/config.py` — `_NLP_METADATA` keys + docstring
- `services/vocabulary/pipeline.py` — `_PROCESSOR_CLASSES` keys + 3 docstrings
- `services/vocabulary/sense_generator.py` — `LINGUISTIC_NOTES`, `LANGUAGE_NAMES` keys + docstring
- `services/vocabulary/language_detection.py` — branch checks (`'cn'` → `'zh'`, `'jp'` → `'ja'`) + docstring

---

## Remaining file edits

For each file below: simple find-and-replace. All instances of `'jp'` → `'ja'` and `'cn'` → `'zh'` *as language-code string literals only* — do NOT touch HTML-class names, voice IDs like `ja-JP-Nanami`, or wordfreq `'zh-cn'` variants in `dictation/tokenizer.py`.

### 1. `services/dictation/tokenizer.py`

| Line | Before | After |
|---|---|---|
| 11 | `- Chinese ('cn'): jieba.lcut for word-segmented matching` | `- Chinese ('zh'): jieba.lcut for word-segmented matching` |
| 12 | `- Japanese ('jp'): char-level fallback (no MeCab dependency)` | `- Japanese ('ja'): char-level fallback (no MeCab dependency)` |
| 60 | `return language_code in {"cn", "zh", "zh-cn", "zh-hans", "zh-hant"}` | `return language_code in {"zh", "zh-cn", "zh-hans", "zh-hant"}` |
| 64 | `return language_code in {"jp", "ja"}` | `return language_code in {"ja"}` |
| 92 | `language_code: e.g. 'cn', 'en', 'es', 'jp'.` | `language_code: ISO 639-1, e.g. 'zh', 'en', 'es', 'ja'.` |

### 2. `services/dictation/grader.py`

| Line | Before | After |
|---|---|---|
| 128 | `language_code:      'cn', 'en', 'es', 'jp', etc. Controls tokenization.` | `language_code:      ISO 639-1: 'zh', 'en', 'es', 'ja', etc. Controls tokenization.` |

### 3. `services/exercise_generation/difficulty.py`

| Line | Before | After |
|---|---|---|
| 11 | `_LANG_ID_TO_CODE: dict[int, str] = {1: 'cn', 2: 'en', 3: 'jp'}` | `_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}` |

### 4. `services/corpus/ingestion.py`

| Line | Before | After |
|---|---|---|
| 18 | `_LANG_ID_TO_CODE = {1: 'cn', 2: 'en', 3: 'jp'}` | `_LANG_ID_TO_CODE = {1: 'zh', 2: 'en', 3: 'ja'}` |

### 5. `services/corpus/style_analyzer.py`

| Line | Before | After |
|---|---|---|
| 24 | `_LANG_ID_TO_WF = {1: 'cn', 2: 'en', 3: 'jp'}` | `_LANG_ID_TO_WF = {1: 'zh', 2: 'en', 3: 'ja'}` |

### 6. `services/llm_output_cleaner.py`

This file has a normalization map that converts external lang codes → app codes.
After ISO migration the normalization is essentially identity for ISO inputs; keep
the legacy aliases for resilience to upstream callers that still send `'zh-cn'` etc.

| Line | Before | After |
|---|---|---|
| 40 | `'zh-cn': 'cn',` | `'zh-cn': 'zh',` |
| 41 | `'zh-tw': 'cn',` | `'zh-tw': 'zh',` |
| 42 | `'zh':    'cn',` | `'zh':    'zh',` |
| 43 | `'ja':    'jp',` | `'ja':    'ja',` |
| 158 | `'cn', 'en', or 'jp').` | `'zh', 'en', or 'ja').` |
| 224 | `expected_lang:      App language code ('cn', 'en', 'jp'). If given,` | `expected_lang:      App language code ISO 639-1 ('zh', 'en', 'ja'). If given,` |

### 7. `services/conversation_generation/quality_checker.py`

| Line | Before | After |
|---|---|---|
| 87 | `# over the DB language_code which may use non-langdetect codes (e.g. 'cn')` | `# over the DB language_code which is ISO 639-1 (e.g. 'zh')` |

### 8. `services/dimension_service.py`

| Line | Before | After |
|---|---|---|
| 145 | `"""Reverse lookup: language_id → language_code (e.g. 1 → 'cn')."""` | `"""Reverse lookup: language_id → language_code (e.g. 1 → 'zh')."""` |

### 9. `services/test_generation/orchestrator.py`

| Line | Before | After |
|---|---|---|
| 54 | `language_code: str                                # 'cn', 'en', 'jp'` | `language_code: str                                # ISO 639-1: 'zh', 'en', 'ja'` |

### 10. `services/test_generation/database_client.py`

| Line | Before | After |
|---|---|---|
| 378 | `Fetch language configuration by language code (e.g., 'en', 'cn', 'jp').` | `Fetch language configuration by language code (ISO 639-1: 'en', 'zh', 'ja').` |

### 11. `scripts/validate_sense_languages.py`

| Line | Before | After |
|---|---|---|
| 41 | `    'cn': 'Chinese',` | `    'zh': 'Chinese',` |
| 43 | `    'jp': 'Japanese',` | `    'ja': 'Japanese',` |
| 322 | `parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],` | `parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],` |

### 12. `scripts/run_test_generation_cli.py`

| Line | Before | After |
|---|---|---|
| 58 | `'--language', required=True, choices=['cn', 'en', 'jp'],` | `'--language', required=True, choices=['zh', 'en', 'ja'],` |
| 91 | `language_names = {'cn': 'Chinese', 'en': 'English', 'jp': 'Japanese'}` | `language_names = {'zh': 'Chinese', 'en': 'English', 'ja': 'Japanese'}` |

### 13. `scripts/backfill_zipf_scores.py`

| Line | Before | After |
|---|---|---|
| 161 | `group.add_argument('--language', choices=['cn', 'en', 'jp'],` | `group.add_argument('--language', choices=['zh', 'en', 'ja'],` |
| 180 | `languages = ['cn', 'en', 'jp'] if args.all else [args.language]` | `languages = ['zh', 'en', 'ja'] if args.all else [args.language]` |

### 14. `scripts/backfill_vocab.py`

| Line | Before | After |
|---|---|---|
| 435 | `parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],` | `parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],` |

### 15. `scripts/backfill_token_maps.py`

| Line | Before | After |
|---|---|---|
| 374 | `parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],` | `parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],` |

### 16. `scripts/backfill_exercises.py`

| Line | Before | After |
|---|---|---|
| 375 | `parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],` | `parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],` |

### 17. `scripts/backfill_question_sense_ids.py`

| Line | Before | After |
|---|---|---|
| 215 | `parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],` | `parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],` |

### 18. `tests/test_dictation_grader.py`

| Line | Before | After |
|---|---|---|
| 220 | `r = grade_dictation("我喜欢学习", "我喜欢学习", "cn")` | `r = grade_dictation("我喜欢学习", "我喜欢学习", "zh")` |

### 19. `templates/study_plan.html`

| Line | Before | After |
|---|---|---|
| 234 | `                { id: 1, code: 'cn', name: 'Chinese' },` | `                { id: 1, code: 'zh', name: 'Chinese' },` |
| 236 | `                { id: 3, code: 'jp', name: 'Japanese' },` | `                { id: 3, code: 'ja', name: 'Japanese' },` |

### 20. `templates/profile.html`

| Line | Before | After |
|---|---|---|
| 523 | `            'cn': '🇨🇳', 'chinese': '🇨🇳',` | `            'zh': '🇨🇳', 'chinese': '🇨🇳',` |
| 525 | `            'jp': '🇯🇵', 'japanese': '🇯🇵',` | `            'ja': '🇯🇵', 'japanese': '🇯🇵',` |

### 21. `templates/test_preview.html`

| Line | Before | After |
|---|---|---|
| 479 | `if (test.language === 'cn' \|\| test.language_id === 1) {` | `if (test.language === 'zh' \|\| test.language_id === 1) {` |
| 484 | `if (test.language === 'jp' \|\| test.language === 'ja' \|\| test.language_id === 3) {` | `if (test.language === 'ja' \|\| test.language_id === 3) {` |

### 22. `static/js/utils.js`

| Line | Before | After |
|---|---|---|
| 24 | `    'zh': '🇨🇳', 'cn': '🇨🇳', 'chinese': '🇨🇳', 'Chinese': '🇨🇳',` | `    'zh': '🇨🇳', 'chinese': '🇨🇳', 'Chinese': '🇨🇳',` |
| 25 | `    'ja': '🇯🇵', 'jp': '🇯🇵', 'japanese': '🇯🇵', 'Japanese': '🇯🇵',` | `    'ja': '🇯🇵', 'japanese': '🇯🇵', 'Japanese': '🇯🇵',` |
| 302 | `     * @param {string} langNameOrCode - e.g. "chinese", "cn", "Chinese"` | `     * @param {string} langNameOrCode - e.g. "chinese", "zh", "Chinese"` |

---

## Database Migration

Create a new file: `migrations/phase15_iso_language_codes.sql`

```sql
-- ME-11: Switch dim_languages.language_code from app-convention to ISO 639-1.
-- 'jp' -> 'ja', 'cn' -> 'zh'. Idempotent.
--
-- All FK references in the DB are to dim_languages.language_id (the integer
-- PK), so this only touches the human-readable code column. Verify before
-- running: SELECT language_id, language_code FROM public.dim_languages;

BEGIN;

UPDATE public.dim_languages
   SET language_code = 'zh'
 WHERE language_code = 'cn';

UPDATE public.dim_languages
   SET language_code = 'ja'
 WHERE language_code = 'jp';

-- Verify
DO $$
DECLARE
    bad_count int;
BEGIN
    SELECT count(*) INTO bad_count
      FROM public.dim_languages
     WHERE language_code IN ('cn', 'jp');
    IF bad_count > 0 THEN
        RAISE EXCEPTION 'Migration incomplete: % rows still have legacy codes', bad_count;
    END IF;
END $$;

COMMIT;
```

**Verification query (run before AND after):**

```sql
SELECT language_id, language_code, native_name
  FROM public.dim_languages
 ORDER BY language_id;
```

Expected after migration:
```
 1 | zh | Chinese
 2 | en | English
 3 | ja | Japanese
```

---

## Caveats / Out of Scope

- **`migrations/phase13_dim_study_plan_templates.sql`** (existing migration): leave as-is. It runs once historically; the new phase15 migration corrects the codes afterwards.
- **`wiki/raw/*`**: per CLAUDE.md, never modify raw source documents.
- **`Project Knowledge/*`** docs: contain example values. Update separately as a docs pass.
- **`data/arena_runs/*.json`**: historical run artifacts; leave alone.
- **`wiki/reviews/code-review-2026-05-24.md`**: historical review pointing at this very issue.

## Final Verification

After applying all edits, run:
```powershell
# Should return zero matches in code paths (excludes wiki/raw and Project Knowledge)
rg "['\"]jp['\"]" --type py --type js --type html --type sql -g '!wiki/raw/**' -g '!Project Knowledge/**' -g '!data/arena_runs/**'
rg "['\"]cn['\"]" --type py --type js --type html --type sql -g '!wiki/raw/**' -g '!Project Knowledge/**' -g '!data/arena_runs/**'
```

Then:
```powershell
# Smoke test imports still work
python -c "from config import Config; print(Config.LANGUAGES)"
python -c "from services.vocabulary.frequency_service import get_zipf_score; print(get_zipf_score('日本', 'ja'))"
python -c "from services.test_generation.difficulty_scorer import score_passage; print(score_passage('Hello world.', 'en'))"
```
