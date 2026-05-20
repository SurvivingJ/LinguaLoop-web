---
title: Furigana Overlay — Technical Specification
type: feature-tech
status: in-progress
prose_page: furigana-overlay.md
last_updated: 2026-05-20
dependencies:
  - "fugashi (MeCab wrapper, already used by services/vocabulary/processors/japanese.py)"
  - "unidic-lite (UniDic dictionary, ships with fugashi[unidic-lite])"
  - "jaconv (katakana→hiragana conversion)"
  - "tests.furigana_payload, test_attempts.furigana_used columns"
  - "users.exercise_preferences JSONB (existing)"
breaking_change_risk: low
---

# Furigana Overlay — Technical Specification

## Architecture Overview

```
test creation
   │
   ▼
services/test_service.py::save_test()
   ├── (Chinese) process_pinyin_passage     → tests.pinyin_payload
   ├── (Japanese) process_pitch_passage     → tests.pitch_payload
   └── (Japanese) process_furigana_payload  → tests.furigana_payload    [NEW]

GET /api/tests/test/<slug>
   └── returns furigana_payload alongside pitch_payload

test page
   ├── /api/users/preferences GET       → toggle initial state
   ├── checkbox flip                    → /api/users/preferences PATCH
   └── render passage / question / choice → renderJpText(plain, tokens)

submit
   └── POST /api/tests/<slug>/submit { furigana_used }
       └── process_test_submission RPC
           └── if furigana_used: user K *= 0.5
```

The shape mirrors the existing pinyin/pitch-accent payload pattern exactly —
pre-compute at creation, ship with the test fetch, render client-side.

## Database Impact

New migration: `migrations/add_furigana_mode.sql`.

```sql
ALTER TABLE tests
    ADD COLUMN IF NOT EXISTS furigana_payload JSONB;

ALTER TABLE test_attempts
    ADD COLUMN IF NOT EXISTS furigana_used BOOLEAN NOT NULL DEFAULT FALSE;
```

Per-user opt-in lives in the existing `users.exercise_preferences` JSONB
(key: `furigana_enabled`), so no new users column is required.

Existing Japanese tests get `furigana_payload = NULL` until they're either
edited (re-saved) or processed by a backfill script.

## Payload Shape

```jsonc
{
  "transcript": [
    {"kind": "plain", "text": "私は"},
    {"kind": "ruby",  "base": "東京",
     "rt": "とうきょう",
     "segments": [{"base": "東京", "rt": "とうきょう"}]},
    {"kind": "plain", "text": "に"},
    {"kind": "ruby",  "base": "行きます",
     "rt": "いきます",
     "segments": [{"base": "行", "rt": "い"}, {"base": "きます", "rt": ""}]}
  ],
  "questions": [
    {
      "text":    [ /* tokens for question_text */ ],
      "choices": [ [ /* tokens choice 0 */ ], [ /* choice 1 */ ], … ]
    }
  ]
}
```

Questions are indexed positionally — the DB-assigned UUIDs aren't available
at creation time, but the frontend renders questions in insertion order, so
index alignment is safe.

## Furigana Generation

`services/furigana_service.py`:

### `process_passage(text: str) -> list[FuriganaToken]`
- **Purpose:** tokenize a string and emit ordered ruby/plain descriptors.
- **Algorithm:**
  1. `fugashi.Tagger()(text)` → token stream.
  2. For each token: read `feature.kana` (fallback `feature.pron`); convert
     katakana → hiragana with `jaconv.kata2hira`.
  3. If surface has no kanji → emit `{"kind": "plain", "text": surface}`.
  4. Otherwise, `_split_kanji_kana_runs(surface)` splits into maximal runs.
  5. `_align_okurigana(surface, reading)`:
     - Strip kana runs from both ends of the reading where the surface kana
       matches (handles okurigana: 食べる→食/た + べる).
     - The remaining middle becomes ruby segments. If there's exactly one
       kanji-run in the middle, the entire remaining reading attaches to it
       (group ruby for jukujikun like 今日→きょう).
- **Determinism:** UniDic readings + jaconv conversion are pure functions.
  Same input → same output.
- **Errors:** tokenizer exceptions degrade to a single plain token containing
  the original input; logged at WARN.

### `process_test_payload(transcript, questions) -> dict`
- Builds the full payload shape above. Choices may be a list or a JSON string;
  both are accepted.

## API / RPC Surface

### `GET /api/tests/test/<identifier>` (modified)
- New field in response: `furigana_payload` (only present for Japanese tests
  with a populated column).

### `POST /api/tests/<slug>/submit` (modified)
- New optional body field: `furigana_used` (bool, default false).
- Threaded into `_call_submission_rpc` → `process_test_submission` RPC.

### `POST /api/tests/<slug>/submit-pitch-accent` (modified)
- Same new field, same plumbing into `process_pitch_accent_submission`.

### `GET /api/users/preferences` (new)
- Returns `{ exercise_preferences: { ... } }`.

### `PATCH /api/users/preferences` (modified)
- Accepts `furigana_enabled: bool` alongside `session_size`.

### `process_test_submission` RPC (modified)
- Signature gains `p_furigana_used BOOLEAN DEFAULT FALSE`.
- User-side K-factor multiplied by constant `c_furigana_dampener = 0.5` when
  the flag is true. Test K is unchanged.
- The flag is persisted into `test_attempts.furigana_used` on the new attempt
  row.

### `process_pitch_accent_submission` RPC (modified)
- Same change as above.

## Component Specification

### `test.html` (modified)
- New state on `testState`: `furiganaPayload`, `furiganaEnabled`,
  `furiganaUsedThisAttempt`.
- New helpers: `renderFuriganaTokens(tokens)`, `renderJpText(text, tokens)`,
  `setupFuriganaToggle()`.
- `transcriptText`, `createQuestionCard` question text + choice labels now
  use `renderJpText`.
- Submission body includes `furigana_used: testState.furiganaUsedThisAttempt`
  (sticky — once on, stays on for the attempt).

### `test_pitch_accent.html` (modified)
- New state on `state`: `furiganaPayload`, `furiganaBySurface` (lookup map),
  `furiganaEnabled`, `furiganaUsedThisAttempt`.
- Each `.word-token .word-surface` renders via `renderSurfaceHtml(surface)`
  which substitutes the ruby form when the toggle is on.
- Toggle change rewrites only the surface spans in place to preserve
  mid-drill state (current/completed/cls-*).

## Key Architectural Decisions

1. **Pre-compute at test creation, not on the fly.**
   - **Rationale:** matches the existing pinyin/pitch pattern; avoids paying
     tokenizer cost on every test load; lets us cache stable JSONB.
   - **Alternatives rejected:** server-side render-time tokenization (slow,
     repeated work), client-side tokenization (would require shipping
     UniDic to the browser).

2. **Group ruby per kanji-run, not per-character alignment.**
   - **Rationale:** per-character is wrong for jukujikun (e.g. 今日 → きょう
     cannot be split as 今/きょ + 日/う). Group ruby is deterministic and
     correct in every case.
   - **Alternatives rejected:** alignment heuristics on common-reading
     dictionaries (still wrong on jukujikun, adds a giant data dependency).

3. **Dampener on user K only.**
   - **Rationale:** a learner's display choice shouldn't move the test's
     published rating; that rating belongs to the test, not the attempt.
   - **Alternatives rejected:** dampening both sides (corrupts test rating),
     dampening only on certain modes (over-engineering).

4. **Sticky `furigana_used` flag for the attempt.**
   - **Rationale:** prevents the peek-then-hide loophole.
   - **Alternatives rejected:** point-in-time check at submit (gameable).

## Security Considerations
- Furigana payload is generated server-side from the test's own transcript —
  no user input. No injection vector.
- The submit-time flag is purely advisory (it affects the learner's *own*
  ELO and is stored on their own attempt row). No privilege escalation.

## Testing Strategy
- Unit test `process_passage` with the canonical cases listed in the plan:
  pure kana, pure kanji compound, kanji + okurigana, jukujikun, mixed sentence.
- Integration test: create a Japanese test, fetch it, confirm payload present
  and well-shaped.
- E2E manual test: take a test toggle-off then toggle-on; confirm ELO delta
  is ~half on the second attempt and `test_attempts.furigana_used` is true.
