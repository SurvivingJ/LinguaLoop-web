---
title: Dictation — Technical Specification
type: feature-tech
status: complete
prose_page: ./dictation.md
last_updated: 2026-05-17
dependencies:
  - "table: tests (audio_url, transcript, vocab_token_map, vocab_sense_ids)"
  - "table: test_attempts (+ 4 new columns)"
  - "table: test_skill_ratings (backfilled for test_type_id=3)"
  - "table: dim_test_types (id=3 dictation, activated)"
  - "RPC: process_dictation_submission (new)"
  - "RPC: get_recommended_tests (modified)"
  - "RPC: calculate_elo_rating, calculate_volatility_multiplier (reused)"
  - "RPC: update_vocabulary_from_word_test (via VocabularyKnowledgeService)"
  - "Service: services.dictation.grader, services.dictation.tokenizer (new)"
  - "Service: services.vocabulary.knowledge_service (reused)"
  - "Frontend: templates/test_dictation.html (new)"
breaking_change_risk: low
---

# Dictation — Technical Specification

## Architecture Overview

```
Browser                          Flask                          Postgres
────────                         ─────                          ────────
GET /test/<slug>/dictation  ──►  test_dictation.html render
                                  ↓
GET /api/tests/test/<slug>       get_test_with_ratings()
   ?mode=dictation          ──►  pops 'transcript' + 'vocab_token_map'  ──►  SELECT tests.*
                            ◄──  audio_url + skill_ratings              ◄──

[user plays audio + types + submits]

POST /api/tests/<slug>/submit-dictation
{user_transcript,                submit_dictation_attempt()
 replay_count,                    ↓
 idempotency_key}           ──►  SELECT id, language_id, transcript,
                                       vocab_sense_ids, vocab_token_map
                                  ↓
                                 grader.grade_dictation(canonical, user, lang)
                                  → GradingResult{word_correct, word_total,
                                                  diff[WordDiff]}
                                  ↓
                                 Map canonical tokens → sense_id via
                                   vocab_token_map surface lookup
                                  ↓
                                 RPC process_dictation_submission(
                                   word_correct, word_total, replay_count,
                                   diff_payload, idempotency_key)
                                                              ↓
                                                              composed_K = vol × replay_factor
                                                              ELO update (user + test)
                                                              INSERT test_attempts
                                                              RETURN jsonb envelope
                                  ↓
                                 for each diff.sense_id where op ∈ {equal,replace,delete}:
                                     VocabularyKnowledgeService
                                       .update_from_word_test(sense_id, is_correct)
                                                              ↓
                                                              RPC update_vocabulary_from_word_test
                                                              BKT update + flashcard auto-create
                                  ↓
                            ◄──  {accuracy, word_correct/total, diff[],
                                  user_elo_change, replay_factor, ...}

[client renders inline diff overlay]
```

## Database Impact

### `dim_test_types` (modified)

Row id=3 (`type_code='dictation'`, `type_name='Dictation'`, `requires_audio=true`) was seeded inactive at project bootstrap. Migration [add_dictation_mode.sql](../../migrations/add_dictation_mode.sql) flipped `is_active=true`.

### `test_attempts` (new columns, all nullable)

| Column | Type | Notes |
|---|---|---|
| `replay_count` | `smallint` | NULL for non-dictation rows. ≥ 1 for dictation; `1` = no replay penalty. |
| `dictation_word_correct` | `integer` | Words marked correct after Levenshtein fuzzy tolerance. |
| `dictation_word_total` | `integer` | Canonical tokens after punctuation removal. |
| `dictation_diff` | `jsonb` | Per-token opcode array for the result-screen diff. Capped at 200 entries server-side. |

The existing `score`, `total_questions`, and `percentage` (generated) columns are also populated (`score = dictation_word_correct`, `total_questions = dictation_word_total`) so history queries that key on those work unchanged.

The existing `elo_reduction_factor` column carries the composed K-multiplier (replay penalty × any retry-slot factor), letting the existing "Review · 0.45× ELO" badge renderer in [profile.html](../../templates/profile.html) work without code changes.

### `test_skill_ratings` (backfill)

The migration inserts one row per existing listening-tier test under `test_type_id=3` with `elo_rating=1400, total_attempts=0`. As of 2026-05-17 this added 243 rows. Backfill pattern matches `add_pinyin_mode.sql`.

## API / RPC Surface

### `process_dictation_submission(...)` — new

```
process_dictation_submission(
  p_user_id          uuid,
  p_test_id          uuid,
  p_language_id      smallint,
  p_test_type_id     smallint,  -- always 3
  p_word_correct     integer,
  p_word_total       integer,
  p_replay_count     smallint,
  p_diff_payload     jsonb,
  p_was_free_test    boolean DEFAULT true,
  p_idempotency_key  uuid    DEFAULT NULL
) RETURNS jsonb
```

- **Purpose:** persist a graded dictation attempt and update ELO. Scoring is pre-computed in Python; this function trusts the count inputs and performs only validation, idempotency, ELO arithmetic, and writes.
- **Validation:** `p_word_total > 0`, `0 ≤ p_word_correct ≤ p_word_total`, `p_replay_count ≥ 1`. Raises `Unauthorized` if `p_user_id != auth.uid()`.
- **Returns:** JSONB envelope with `{success, attempt_id, score, total_questions, percentage, user_elo_change, test_elo_change, replay_count, replay_factor, elo_reduction_factor, diff, ...}`.
- **Errors:** any DB exception is caught and returned as `{success: false, error, error_detail}`.
- **Auth:** `SECURITY DEFINER`, `GRANT EXECUTE TO authenticated`.
- **Side effects:** INSERT `test_attempts`, UPDATE `user_skill_ratings` and `test_skill_ratings` (first attempt + retry-slot path), UPSERT `user_languages`, token charge (when `was_free_test=false`).

ELO formula (first attempt branch):
```
v_replay_factor := GREATEST(0.5, 1.0 - 0.10 * GREATEST(0, p_replay_count - 1))
v_user_K := 32 * volatility * v_replay_factor
v_test_K := 16 * v_replay_factor
elo_reduction_factor := CASE WHEN v_replay_factor < 1.0 THEN v_replay_factor ELSE NULL END
```

Retry-slot branch composes multiplicatively with the existing daily-retry decay factor (per [ADR-006](../decisions/ADR-006-retry-slot-reduced-elo.md)).

### `get_recommended_tests` — modified

[migrations/update_get_recommended_tests_for_dictation.sql](../../migrations/update_get_recommended_tests_for_dictation.sql). Two changes vs the prior `fix_get_recommended_tests_signature.sql`:

1. **Per-test-type exclusion** — the `NOT EXISTS test_attempts` subquery key changed from `(user_id, test_id)` to `(user_id, test_id, test_type_id)`. A user who took the listening version of a test still sees the dictation version surfaced.
2. **Dictation length cap** — the dictation lane filters to transcripts where `array_length(string_to_array(trim(transcript), ' '), 1) <= 80`. Other lanes unaffected.

Signature unchanged (`uuid, smallint`).

### Reused unchanged

- `calculate_elo_rating(current_rating, opposing_rating, actual_score, k_factor, volatility) → integer`
- `calculate_volatility_multiplier(tests_taken, last_test_date, base) → numeric`
- `update_vocabulary_from_word_test(p_user_id, p_sense_id, p_is_correct, p_language_id, p_exercise_type?) → table`

## Backend Scoring Service

### `services/dictation/grader.py`

```python
def grade_dictation(
    correct_transcript: str,
    user_transcript: str,
    language_code: str,
) -> GradingResult
```

Returns `GradingResult(word_correct, word_total, accuracy, diff: list[WordDiff], canonical_tokens, user_tokens)` where each `WordDiff` has `(op, correct, user, is_correct, sense_id?)`.

**Algorithm:**
1. Normalize both transcripts via `tokenizer.normalize()` — lowercase, NFKD strip combining marks, strip punctuation (keep word-internal `'`/`-`), collapse whitespace.
2. Tokenize via `tokenizer.tokenize(text, language_code)`.
3. Walk `difflib.SequenceMatcher(canonical, user).get_opcodes()`:
   - `equal` → emit `WordDiff(op='equal', is_correct=True)` per token, counted toward total.
   - `replace` → zip-aligned pairs run through `_fuzzy_equal`; leftover tokens become `insert`/`delete`.
   - `delete` → canonical-side token user missed; counted against total.
   - `insert` → extra user-side token; recorded for UI, never counted.
4. `_fuzzy_equal(a, b)`: exact match → True; both `len ≥ 4` AND `_levenshtein(a, b) ≤ 1` → True; else False.

`_levenshtein` is a bounded pure-Python implementation that early-exits when the row minimum exceeds the budget. No `python-Levenshtein` dependency needed.

### `services/dictation/tokenizer.py`

- `normalize(text) → str` — language-agnostic.
- `tokenize(text, language_code) → list[str]`:
  - `cn` / `zh*` → `jieba.lcut` (lazily imported; falls back to char-level if missing)
  - `jp` / `ja` → character-level (no MeCab dependency)
  - otherwise → `text.split()`
- Trailing/leading apostrophes and hyphens are trimmed from each token via `_EDGE_TRIM_RE`.

### Sense-id mapping

Done in [routes/tests.py](../../routes/tests.py) `submit_dictation_attempt`, not the grader. We build a `surface_to_sense` map by normalizing each `vocab_token_map` entry's surface form, then look up each canonical-side diff token. Lemma-based lookup is a future improvement; current surface-form lookup is fine for most languages because normalization handles inflection-free comparison.

## Flask Endpoints

### `POST /api/tests/<slug>/submit-dictation`

[routes/tests.py](../../routes/tests.py) `submit_dictation_attempt()`. JWT-required. Body: `{user_transcript, replay_count, time_taken, idempotency_key}`. Server-side: fetches canonical transcript + vocab token map, runs grader, calls RPC, fires per-word BKT updates (fire-and-log; non-fatal), returns response envelope.

### `GET /api/tests/test/<slug>?mode=dictation` — modified

Existing `get_test_with_ratings` handler. When `mode=dictation` is present in the query string, the response strips `transcript` and `vocab_token_map` before returning, so the learner never sees the canonical transcript pre-submit.

### `GET /test/<slug>/dictation` — page route

[app.py](../../app.py) `dictation_test_page()`. Renders [templates/test_dictation.html](../../templates/test_dictation.html).

## Frontend

### `templates/test_dictation.html` (new)

Self-contained client-side page with audio player, replay counter, speed toggle (1.0x / 0.75x / 0.5x via `HTMLAudioElement.playbackRate`), textarea, submit footer, and results overlay with inline diff renderer.

**State:**
```
state = { slug, audioUrl, replayCount, playbackRate, hasPlayed,
          isSubmitting, submitted, idempotencyKey, startTime }
```

**Submit flow:** generates `idempotencyKey = crypto.randomUUID()` on init; pauses audio + disables textarea on submit; renders diff overlay on success.

**Diff renderer:** iterates `diff: WordDiff[]` from response, emits `<span class="dict-word dict-word-{equal|replace|delete|insert}">{token}</span>`. Fuzzy-matched replaces (where `is_correct=true` despite token diff) render as `dict-word-equal` with the user's typed version in a `title` tooltip.

### `templates/test_preview.html` (modified)

The Dictation radio button was already present (lines 276-287). Only the `startTest()` routing was updated to navigate to `/test/<slug>/dictation` instead of `/test/<slug>?type=dictation`.

### i18n

22 new `dictation.*` keys added to [static/i18n/en.json](../../static/i18n/en.json), [zh.json](../../static/i18n/zh.json), [es.json](../../static/i18n/es.json), [ja.json](../../static/i18n/ja.json).

## Key Architectural Decisions

1. **Python-side scoring, not SQL.** Pure-SQL Levenshtein over tokenized JSONB arrays requires `fuzzystrmatch` and a custom array-align loop; fragile, slower, harder to test. We grade in Python and ship integer counts + the diff JSONB to a thin RPC.
   - **Alternatives rejected:** all-in-SQL grading (fragility); LLM grading (cost, latency, determinism).
2. **Reuse listening tests verbatim.** Zero new content generation. Listening transcripts already have R2-hosted audio.
   - **Alternative rejected:** dedicated short dictation tests with their own pipeline (higher pack-build cost; deferred until real-user data warrants it).
3. **Per-word BKT signal.** Every transcript word that maps to `dim_word_senses` triggers `update_vocabulary_from_word_test`. One dictation = 50-100 BKT updates vs ~5 from a comprehension test. This is the dominant learning-value upside.
   - **Alternative rejected:** test-level ELO only (loses the upside).
4. **Replay penalty curve `max(0.5, 1.0 - 0.10 * (n - 1))`.** One free replay; -10% K per additional play; 0.50 floor.
   - **Rationale:** typical learner plays once; the curve makes power-replayers honest without zeroing them out.
   - **Mirrors:** ADR-006 retry-slot factor philosophy (always award *some* signal).
5. **No new ADR for the replay multiplier** — references ADR-006 inline. Promote later if contentious.
6. **Pure-Python Levenshtein.** No `python-Levenshtein` C extension dependency; word-level distance over short tokens is O(n*m) in the tens of operations — negligible.

## Security Considerations

- `process_dictation_submission` is `SECURITY DEFINER` with `p_user_id = auth.uid()` check identical to `process_test_submission` and `process_pinyin_submission`.
- Server-side length guard: `len(user_transcript) <= 10 * len(canonical_transcript)` rejects pathological submissions.
- `GET ?mode=dictation` strips the transcript server-side. Defense-in-depth: even if a client tampers with the request, the canonical transcript is never returned in dictation mode.
- Per-word BKT updates wrapped in try/except; one bad sense_id never aborts an attempt.
- Idempotency key prevents double-credit on network retries.

## Testing Strategy

### Unit ([tests/test_dictation_grader.py](../../tests/test_dictation_grader.py))

34 tests covering: Levenshtein bounded distance, fuzzy equality thresholds, normalization (case, diacritics, punctuation, apostrophes, hyphens, whitespace), tokenization, perfect/zero match, typo tolerance, short-word strictness, extra/missing word handling, empty transcript, Chinese round-trip, diff payload serialization.

### Manual E2E

1. Navigate to a Chinese listening test preview → click Dictation → verify routing to `/test/<slug>/dictation`.
2. Play audio once, type approximation, submit → verify color-coded inline diff renders.
3. Replay audio 5× and submit → verify `elo_reduction_factor ≈ 0.6` on the `test_attempts` row.
4. Resubmit with same `idempotency_key` → verify cached response returned, no double ELO.
5. Verify `user_vocabulary_knowledge` updated for words in the transcript with sense_id mappings.
6. Verify recommendation `get_recommended_tests` returns dictation candidates capped at ≤ 80 words.

### Verification SQL

```sql
SELECT test_type, COUNT(*) AS candidates
FROM public.get_recommended_tests(user_uuid, 1::smallint)
GROUP BY test_type;
-- Expected: dictation, listening, reading each appearing
```
