---
title: Pinyin Tone Trainer — Technical Specification
type: feature-tech
status: complete
prose_page: ./pinyin-trainer.md
last_updated: 2026-04-21
dependencies:
  - "tests table (pinyin_payload JSONB column)"
  - "dim_test_types (pinyin row)"
  - "test_skill_ratings (pinyin entries)"
  - "test_attempts table"
  - "process_test_submission() RPC"
  - "pypinyin library"
  - "jieba library"
  - "DeepSeek LLM (optional polyphone resolution)"
breaking_change_risk: low
---

# Pinyin Tone Trainer — Technical Specification

## Architecture Overview

```
Payload Generation (admin-triggered or automatic on test creation):
  Chinese transcript
    → jieba word segmentation
    → pypinyin tone extraction (per-character)
    → Token building (base_tone, pinyin_text, word context)
    → Deterministic sandhi rules (3rd tone, yi, bu)
    → Polyphone flagging (45+ watchlist chars)
    → [Optional] LLM polyphone resolution (DeepSeek)
    → pinyin_payload JSONB → tests.pinyin_payload column

Game Serving (user-facing):
  /test/{slug}/pinyin          → renders test_pinyin.html template
  GET /api/tests/test/{slug}   → returns test_data + pinyin_payload
  POST /api/tests/{slug}/submit-pinyin → grade + ELO update via process_test_submission()
```

## Database Impact

**Tables read:** `tests` (pinyin_payload, transcript), `questions` (first question_id for synthetic response), `dim_test_types` (pinyin type_id), `test_skill_ratings`, `user_skill_ratings`
**Tables written:** `tests` (pinyin_payload on generation), `test_attempts`, `test_skill_ratings`, `user_skill_ratings`

**Schema changes (migration: `add_pinyin_mode.sql`):**

1. New row in `dim_test_types`: `('pinyin', 'Pinyin Tones', false, true, 4)`
2. New column on `tests`: `pinyin_payload JSONB` (nullable, no default)
3. Backfill: `test_skill_ratings` entries for all Chinese tests (`language_id = 1`) with `elo_rating = 1400`

## Pinyin Token Schema

Each element in the `pinyin_payload` JSON array:

```json
{
  "char": "语",
  "word": "语言",
  "pinyin_text": "yu",
  "base_tone": 3,
  "context_tone": 2,
  "is_sandhi": true,
  "sandhi_rule": "Third tone sandhi: when two 3rd tones appear together, the first changes to a 2nd tone.",
  "is_punctuation": false,
  "requires_review": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `char` | string | Single Chinese character |
| `word` | string | The jieba-segmented word containing this character |
| `pinyin_text` | string | Romanisation without tone number |
| `base_tone` | int (1-5) | Dictionary tone (5 = neutral) |
| `context_tone` | int (1-5) | Tone after sandhi rules applied — this is what the user must guess |
| `is_sandhi` | bool | Whether a sandhi rule changed the tone |
| `sandhi_rule` | string\|null | Human-readable explanation of which sandhi rule applied |
| `is_punctuation` | bool | If true, rendered but not interactive |
| `requires_review` | bool | Flagged for LLM polyphone resolution |

## API / RPC Surface

### `GET /test/{slug}/pinyin` (page route)

- **Purpose:** Render the pinyin trainer game page
- **Handler:** `app.py:303-306` → `pinyin_test_page()`
- **Auth:** JWT required (checked client-side)
- **Returns:** Rendered `test_pinyin.html` template

### `GET /api/tests/test/{slug}` (existing, enhanced)

- **Purpose:** Fetch test content including pinyin payload
- **Handler:** `routes/tests.py:960-1041`
- **Enhancement:** For Chinese tests, includes `pinyin_payload` in response if present
- **Returns:** `{test_data, questions_data, skill_ratings, pinyin_payload?}`

### `POST /api/tests/{slug}/submit-pinyin`

- **Purpose:** Submit pinyin game results and update ELO
- **Handler:** `routes/tests.py:847-948`
- **Auth:** JWT required
- **Arguments:**
  - `correct_chars: int` — characters answered correctly
  - `total_chars: int` — total playable characters
  - `time_taken: int` — seconds elapsed
  - `errors: array` — (optional) error log objects
- **Processing:**
  1. Calculate accuracy: `correct_chars / total_chars`
  2. Look up test by slug, verify `language_id == 1`
  3. Get pinyin `test_type_id` via `DimensionService.get_test_type_id('pinyin')`
  4. Build synthetic response: `[{question_id: first_question_id, selected_answer: "pinyin_accuracy_{accuracy:.2f}"}]`
  5. Call `process_test_submission` RPC with pinyin type_id — RPC handles ELO calc and attempt recording
  6. Parse ELO changes from RPC response
- **Returns:**
  ```json
  {
    "status": "success",
    "result": {
      "accuracy": 87.5,
      "correct_chars": 7,
      "total_chars": 8,
      "time_taken": 45,
      "test_mode": "pinyin",
      "attempt_id": "uuid",
      "user_elo_change": {"before": 1400, "after": 1420, "change": 20},
      "test_elo_change": {"before": 1400, "after": 1395, "change": -5}
    }
  }
  ```
- **Errors:** 400 (missing fields, non-Chinese test), 404 (test not found), 401 (no auth)

## Pinyin Processing Pipeline (`services/pinyin_service.py`)

### `process_passage(text: str) -> list[dict]`

1. **Segment:** `jieba.lcut(text)` → word list
2. **Extract:** For each word, `pypinyin.pinyin(word, style=Style.TONE3, v_to_u=True, neutral_tone_with_five=True)` → per-character pinyin with tone numbers
3. **Tokenise:** Build token dicts with `char`, `word`, `pinyin_text`, `base_tone`, `context_tone` (initially = base_tone), `is_punctuation`
4. **Sandhi:** `_apply_sandhi(tokens)` — mutates `context_tone`, sets `is_sandhi` and `sandhi_rule`
5. **Flag polyphones:** Check single-character tokens against `POLYPHONE_WATCHLIST` → set `requires_review = true`
6. **Return:** Token list ready for JSON serialisation

### Sandhi Rules (`_apply_sandhi`)

Applied in order, each rule checks consecutive token pairs:

| Rule | Condition | Result | Exception |
|------|-----------|--------|-----------|
| Third tone sandhi | Two consecutive base_tone=3 | First → context_tone=2 | Not yi or bu chars |
| Yi before 4th | yi + next base_tone=4 | yi → context_tone=2 | — |
| Yi before 1st/2nd/3rd | yi + next base_tone=1/2/3 | yi → context_tone=4 | — |
| Yi in A-yi-A | Repeated verb pattern | yi → context_tone=5 (neutral) | — |
| Bu before 4th | bu + next base_tone=4 | bu → context_tone=2 | — |
| Bu in A-bu-A | Repeated verb pattern | bu → context_tone=5 (neutral) | — |

### `resolve_polyphones_llm(tokens: list, text: str) -> list[dict]`

- **Trigger:** Only via `--resolve-polyphones` flag in batch script
- **Model:** DeepSeek (via `llm_service.call_llm()`)
- **Prompt:** Asks LLM to analyse grammatical context and return `{"pinyin_text": str, "tone": int}`
- **Post-processing:** Re-applies sandhi rules after LLM corrections
- **Rate limit:** 0.5s delay between calls

## Component Specification (UI)

### `test_pinyin.html` (Jinja2 template with inline JS)

**State:**

| Variable | Type | Description |
|----------|------|-------------|
| `slug` | string | Test identifier from URL |
| `testData` | object | Full test metadata |
| `allTokens` | array | All tokens including punctuation (for rendering) |
| `playableTokens` | array | Non-punctuation tokens only (for gameplay) |
| `playableIndices` | array | Map from playable index → allTokens index |
| `currentIndex` | int | Current playable token being guessed |
| `correctCount` | int | Successful guesses |
| `errorCount` | int | Wrong guesses |
| `errors` | array | Error log for submission |
| `startTime` | timestamp | Game start |
| `isComplete` | bool | All characters answered |
| `isPaused` | bool | Error modal active |

**Input handling:**

- Keyboard: `ArrowRight`=T1, `ArrowUp`=T2, `ArrowLeft`=T3, `ArrowDown`=T4, `Space`=Neutral(T5)
- Touch: Swipe direction detection with distance threshold; tap (<300ms, small movement) = Neutral

**Rendering:**

- Characters in flex-wrap grid at 2rem font size
- Current character scaled 1.25x with underline
- Completed characters coloured by tone (CSS variables `--tone-1` through `--tone-5`)
- Pinyin romanisation revealed below each character on correct answer
- Error modal overlays game with character, word context, tones, and sandhi explanation

**Grading thresholds:**

| Grade | Accuracy |
|-------|----------|
| Excellent | >= 95% |
| Good | >= 80% |
| Fair | >= 60% |
| Poor | < 60% |

## Batch Generation Script (`scripts/batch_generate_pinyin.py`)

Backfills `pinyin_payload` for existing Chinese tests.

```
Usage:
  python scripts/batch_generate_pinyin.py              # All Chinese tests
  python scripts/batch_generate_pinyin.py --limit 100  # First 100
  python scripts/batch_generate_pinyin.py --resolve-polyphones  # With LLM
  python scripts/batch_generate_pinyin.py --dry-run    # Preview only
```

**Flow:**
1. Query Supabase for Chinese tests (`language_id=1`) where `pinyin_payload IS NULL`
2. For each test: `process_passage(transcript)` → tokens
3. If `--resolve-polyphones`: call LLM for flagged tokens (0.5s rate limit)
4. If not `--dry-run`: update test record with `pinyin_payload` JSONB
5. Log per-test stats: playable chars, sandhi count, unresolved polyphones

## Integration Points

1. **Test creation** (`test_service.py:283-294`, `orchestrator.py:438-448`) — automatically generates `pinyin_payload` for Chinese tests on save. Fails gracefully (non-blocking).
2. **Skill ratings** (`test_service.py:311-315`, `database_client.py:737`) — includes pinyin test_type in initial `test_skill_ratings` for Chinese tests.
3. **Test retrieval** (`routes/tests.py:960-1041`) — includes `pinyin_payload` in API response for Chinese tests when present.
4. **Test preview** (`test_preview.html:497-498`) — shows pinyin mode button when `language === 'cn' OR language_id === 1`.

## Key Architectural Decisions

1. **Pre-computed payload stored on test record**
   - **Rationale:** Pinyin extraction + sandhi rules are deterministic for a given transcript. Computing once and storing as JSONB avoids repeated processing per user session. Payload is ~1-3KB per test.
   - **Alternatives rejected:** On-the-fly computation — adds latency and requires pypinyin/jieba on the serving path.

2. **Reuse `process_test_submission` RPC with synthetic response**
   - **Rationale:** The existing RPC already handles ELO updates, attempt recording, and skill ratings atomically. A synthetic response (`pinyin_accuracy_0.87`) maps accuracy to the existing grading mechanism.
   - **Alternatives rejected:** Separate pinyin submission RPC — would duplicate ELO logic.

3. **Deterministic sandhi rules with optional LLM fallback**
   - **Rationale:** The three main sandhi rules cover the vast majority of cases. LLM resolution is expensive and only needed for ambiguous polyphones, so it runs as a batch job, not per-request.
   - **Alternatives rejected:** Full LLM tone annotation — too slow, too expensive, unnecessary for ~95% of characters.

4. **Keyboard arrows + touch swipes for tone input**
   - **Rationale:** Maps spatial direction to tone contour (right=flat T1, up=rising T2, left=dipping T3, down=falling T4). Intuitive for learners who know tone contours. Works on both desktop and mobile.
   - **Alternatives rejected:** Number keys — less intuitive spatial mapping. Dropdown selectors — too slow for game flow.

## Security Considerations

- JWT auth required for all endpoints
- Language check: backend verifies `language_id == 1` before processing pinyin submissions
- No user-supplied text processed — only pre-computed payloads from admin-generated tests
- LLM calls only in batch script (admin-only), not in user-facing request path

## Testing Strategy

- Unit test: sandhi rule application with known character sequences
- Unit test: token generation from sample Chinese passages
- Integration test: submit-pinyin endpoint with mock accuracy data, verify ELO changes
- Edge cases: empty transcript, all-punctuation text, polyphone-heavy passages, 100% and 0% accuracy submissions

## Related Pages

- [[features/pinyin-trainer]] — Prose description
- [[features/comprehension-tests.tech]] — Parent test engine
- [[algorithms/elo-ranking.tech]] — ELO formula shared by pinyin mode
- [[database/schema.tech]] — `tests.pinyin_payload`, `dim_test_types`, `test_skill_ratings`
- [[database/rpcs.tech]] — `process_test_submission` RPC
