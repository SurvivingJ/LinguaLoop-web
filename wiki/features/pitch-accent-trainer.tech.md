---
title: Pitch Accent Trainer — Technical Specification
type: feature-tech
status: complete
prose_page: ./pitch-accent-trainer.md
last_updated: 2026-05-17
dependencies:
  - "pyopenjtalk (Python NLP, MIT — provides NJD per-word accent extraction)"
  - "Migration: add_pitch_accent_mode.sql (dim_test_types + tests.pitch_payload + skill rating backfill)"
  - "Migration: process_pitch_accent_submission.sql (accuracy-based RPC)"
  - "Existing: test_skill_ratings, user_skill_ratings, test_attempts, user_languages"
breaking_change_risk: low
---

# Pitch Accent Trainer — Technical Specification

## Architecture Overview

The Pitch Accent Trainer mirrors the Pinyin Trainer architecture one-to-one, swapping the Chinese-specific preprocessor (pypinyin + jieba + sandhi rules) for a Japanese one (pyopenjtalk + mora segmentation). Same shape: pre-compute a structured JSON payload at test save time, serve it as part of the test data fetch, replay it client-side as a per-word guessing game, and submit pre-counted accuracy to a dedicated RPC that updates ELO with the same K=32 formula.

```
Test creation (services/test_service.py)
  → if language_id == 3:
       pitch_accent_service.process_passage(transcript)
       UPDATE tests SET pitch_payload = <json> WHERE id = test_id
  → _create_skill_ratings inserts a pitch_accent row at ELO 1400

Test load (routes/tests.py:get_test_with_ratings)
  → SELECT ... pitch_payload ... FROM tests
  → returns response_data["pitch_payload"] for JA tests

Game (templates/test_pitch_accent.html)
  → state machine with two renderers (Quick / Contour) sharing a single payload
  → per-token correctness check
  → on completion: POST /api/tests/<slug>/submit-pitch-accent

Submit (routes/tests.py:submit_pitch_accent_attempt)
  → RPC process_pitch_accent_submission(p_correct_units, p_total_units, ...)
  → JSONB response: { attempt_id, user_elo_before/after, test_elo_before/after, ... }
```

## Database Impact

### New row in `dim_test_types`

| field | value |
|---|---|
| `type_code` | `pitch_accent` |
| `type_name` | `Pitch Accent` |
| `requires_audio` | `false` |
| `is_active` | `true` |
| `display_order` | `5` |

### New column on `tests`

```sql
ALTER TABLE tests ADD COLUMN pitch_payload JSONB;
```

Stores the per-word accent payload for Japanese tests (analogous to `pinyin_payload` for Chinese tests). NULL for non-Japanese tests.

### Backfill on `test_skill_ratings`

For every existing `language_id = 3` test, one row at `elo_rating = 1400, total_attempts = 0` keyed by the new `pitch_accent` `test_type_id`. Verified in production: 80/80 JA tests have a pitch_accent skill rating row.

### Tables read/written by `process_pitch_accent_submission`

| Table | Operation | Notes |
|---|---|---|
| `test_attempts` | INSERT | One row per submission. `score`/`total_questions` are the correct/total accent phrases. `idempotency_key` dedupes replays. |
| `user_skill_ratings` | UPSERT | New user gets `elo_rating=1200`; first attempt updates by `K=32 × (accuracy − expected)`. |
| `test_skill_ratings` | UPSERT | New test (defensive) gets `elo_rating=1400`; first attempt updates by `K=32 × ((1−accuracy) − (1−expected))`. |
| `user_languages` | UPSERT | Bumps `total_tests_taken` and `last_test_date`. |

## API / RPC Surface

### `POST /api/tests/<slug>/submit-pitch-accent`

Implemented at [routes/tests.py:submit_pitch_accent_attempt](../../routes/tests.py).

- **Auth:** JWT required (`@supabase_jwt_required`).
- **Request body:**
  ```json
  {
    "correct_units": 47,
    "total_units": 50,
    "time_taken": 92,
    "errors": [ ... ]
  }
  ```
  `correct_units = max(0, total − errorCount)`; `errors` is capped client-side at 50 and currently logged only (no DB storage).
- **Server-side path:**
  1. Loads `tests` by slug, asserts `language_id == 3`.
  2. Resolves the `pitch_accent` test_type_id via `DimensionService.get_test_type_id('pitch_accent')`.
  3. Calls `process_pitch_accent_submission` via Supabase RPC.
  4. Builds the response payload from the RPC JSONB.
- **Response:**
  ```json
  {
    "status": "success",
    "result": {
      "accuracy": 94.0,
      "correct_units": 47,
      "total_units": 50,
      "time_taken": 92,
      "user_elo_change": { "before": 1200, "after": 1228, "change": 28 },
      "test_elo_change": { "before": 1400, "after": 1393, "change": -7 },
      "test_mode": "pitch_accent",
      "attempt_id": "uuid"
    }
  }
  ```
- **Errors:**
  - `400` — `Invalid total_units` (≤ 0) or wrong-language test.
  - `404` — Test slug not found.
  - `500` — RPC failure (includes propagated `error` and `error_detail` from the RPC's exception envelope).

### `process_pitch_accent_submission(...)` RPC

```
process_pitch_accent_submission(
  p_user_id        UUID,
  p_test_id        UUID,
  p_language_id    SMALLINT,
  p_test_type_id   SMALLINT,
  p_correct_units  INTEGER,
  p_total_units    INTEGER,
  p_was_free_test  BOOLEAN DEFAULT TRUE,
  p_idempotency_key UUID DEFAULT NULL
) RETURNS JSONB
```

Source: [migrations/process_pitch_accent_submission.sql](../../migrations/process_pitch_accent_submission.sql). SECURITY DEFINER; `GRANT EXECUTE TO authenticated`. Behaviour-identical to `process_pinyin_submission` with parameter renames (`p_correct_chars`/`p_total_chars` → `p_correct_units`/`p_total_units`).

Key invariants:
- Auth check: `p_user_id != auth.uid()` raises `Unauthorized`.
- Input validation: `0 <= correct_units <= total_units`, `total_units > 0`.
- Idempotency: short-circuit return for matching `(user_id, idempotency_key)`.
- ELO update **only on first attempt**: K=32, bounds [400, 3000]. Retries record an attempt row but don't move ELO.
- Returns a JSONB envelope with `success`, `attempt_id`, ELO before/after/change, score, total, percentage, and a human-readable `message`.

### `GET /api/tests/test/<identifier>` enhancement

For Japanese tests, the response includes a `pitch_payload` key alongside the existing `pinyin_payload` (for Chinese tests). The select column list was extended to include both. No new endpoint; just an additive field.

## Service Specification

### `services/pitch_accent_service.py`

#### `process_passage(text: str) -> list[dict]`

Main entry point. Pipeline:

1. `pyopenjtalk.run_frontend(text)` returns a list of NJD per-word feature dicts (works with both modern list-returning and legacy tuple-returning versions of the library).
2. For each NJD entry:
   - If POS = `記号` or surface is all-punctuation → emit `is_punctuation: true` token (preserves rendering layout).
   - If POS = `助詞` (particle) or `助動詞` (aux verb) → **skip** as own token (these are attached to the previous content word as `trailing_particle`).
   - Else → segment the katakana pronunciation into mora, derive `pattern_class` and `contour` from `(accent, mora_size)`, lookahead for a trailing particle, emit token.
3. Return list of dicts. Empty list on transcript-empty or pyopenjtalk failure (logged warning).

#### Token schema

```json
{
  "phrase_index": 0,
  "surface": "東京",
  "kana": "トーキョー",
  "mora": ["ト", "ー", "キョ", "ー"],
  "mora_count": 4,
  "accent": 0,
  "pattern_class": "heiban",
  "contour": ["L", "H", "H", "H"],
  "trailing_particle": "ワ",
  "trailing_particle_pitch": "H",
  "pos": "名詞",
  "is_punctuation": false,
  "requires_review": false
}
```

| Field | Type | Notes |
|---|---|---|
| `phrase_index` | int | Sequential counter over content tokens (skips punctuation, particles, aux verbs). |
| `surface` | string | Original orthography (may contain kanji). |
| `kana` | string | Pyopenjtalk's `pron` field — katakana with `ー` for long vowels. |
| `mora` | string[] | Mora-segmented kana. Small kana fuse with preceding character; `ー`/`ッ`/`ン` are each one mora. |
| `mora_count` | int | Trusted from pyopenjtalk's `mora_size`; the `mora` array is padded/truncated to match. |
| `accent` | int 0..N | Pyopenjtalk's `acc`. 0 = heiban (no drop); N = odaka (drop on boundary). |
| `pattern_class` | string | `heiban` \| `atamadaka` \| `nakadaka` \| `odaka` \| `unknown` (only if `mora_count <= 0`). |
| `contour` | string[] | Derived `H`/`L` per mora. Heiban → `L H H...`, Atamadaka → `H L L...`, else → `L H ...H L L...` with drop after `accent`. |
| `trailing_particle` | string \| null | First mora of the next NJD entry if it's POS=助詞; else null. |
| `trailing_particle_pitch` | `"H"` \| `"L"` \| null | Heiban → `H` (particle stays high); any drop → `L`. |
| `pos` | string | NJD POS tag, kept for debugging. |
| `is_punctuation` | bool | True for symbol tokens; skipped in gameplay. |
| `requires_review` | bool | True when classifier couldn't assign a class; reserved for a future admin override path. |

#### Helpers

- `_segment_kana_to_mora(kana)` — implements the small-kana-fusion rule for Japanese mora.
- `_derive_pattern_class(accent, mora_count)` — pure-function mapping.
- `_derive_contour(accent, mora_count)` — pure-function contour derivation.
- `_derive_particle_pitch(accent, mora_count)` — H if heiban, else L.

#### Failure mode

If pyopenjtalk raises (e.g., for a malformed input) the service logs a warning and returns `[]`. The caller in [test_service.py:save_test](../../services/test_service.py) wraps the call in its own try/except so a payload-generation failure does not block the test save (mirrors pinyin's graceful-degradation pattern).

## Component Specification (UI)

### `templates/test_pitch_accent.html`

A single-file Jinja template containing CSS, markup, and a self-contained IIFE. State machine has nine fields:

| field | meaning |
|---|---|
| `slug` | Test slug parsed from URL. |
| `testData` | The full `test_data` object from `/api/tests/test/<slug>`. |
| `allTokens` | Full `pitch_payload` including punctuation. |
| `playableTokens` | `allTokens` filtered to non-punctuation, non-unknown. |
| `playableIndices` | Parallel index into `allTokens` for DOM lookups. |
| `currentIndex`, `correctCount`, `errorCount`, `errors` | Game progress. |
| `mode` | `'quick'` \| `'contour'`, persisted in `localStorage` as `pa_mode`. |
| `contourInput` | Per-mora `'H' / 'L' / null` working array for contour mode. |
| `contourCursor` | Current mora being edited in contour mode. |

### Renderers

#### Quick mode (`handleClassInput`)

Keyboard map: `ArrowLeft` → `heiban`, `ArrowUp` → `atamadaka`, `ArrowRight` → `nakadaka`, `ArrowDown` → `odaka`. Match the `pattern_class` field exactly. Correct → `acceptToken`; wrong → `rejectToken({ mode: 'quick', guessedClass })`.

#### Contour mode (`renderScratchpad` / `submitContour`)

A two-track grid (HIGH row / LOW row / mora-label row) where every mora has two clickable dots. The trailing particle, if any, is rendered as a reference-only column (lighter dots, not selectable). Keyboard: `1`/`L` = LOW, `2`/`H` = HIGH for current mora; `←`/`→` advance/retreat cursor; `Enter` submits.

`analyzeContour(input)` validates the submission against the two universal rules:
1. `contour[0] !== contour[1]` (mora 1 and mora 2 must differ).
2. At most one H→L transition; no L→H transition after a drop.

If invalid, returns a reason code (`mora1_eq_mora2`, `multiple_drops`, `rise_after_drop`, `empty`) and the error modal explains it. If valid, the derived accent nucleus (`dropAt`, or `0` if no drop) is compared against `token.accent`. Mismatch → "drop is in the wrong place" modal.

### Mode toggle

Top-right segmented control: `[ ⚡ Quick | 🎯 Contour ]`. Saved to `localStorage.pa_mode`. Toggling mid-token resets only the current contour input (no score impact).

### Shared chrome

Progress bar, timer (MM:SS), error count, error modal with full canonical contour (SVG with H/L dashed reference lines, polyline through the drop, dots, mora labels, particle label in muted color), results screen.

### Scoring

```javascript
const accuracy = Math.max(0, totalUnits - errorCount) / totalUnits;
```

One mistake per token regardless of retries. Posted to the submit endpoint as `correct_units` and `total_units`.

## Key Architectural Decisions

1. **Pre-computed pitch_payload JSONB on `tests`.**
   - **Rationale:** Same as pinyin — payload generation requires pyopenjtalk's dictionary, ~3–8 KB per test, deterministic. Pre-computing avoids per-request latency and removes the runtime dependency from the request path.
   - **Alternative rejected:** On-the-fly extraction. Pyopenjtalk is fast (~50 ms per paragraph) but the dictionary load is non-trivial and would tax cold-start latency.

2. **Dedicated `process_pitch_accent_submission` RPC (parameter rename of pinyin's).**
   - **Rationale:** Pitch accent produces a pre-counted accuracy with no MC questions to grade. Reusing `process_test_submission` would force a synthetic question/response shape and break the BKT path. The dedicated RPC accepts `(correct_units, total_units)` directly.
   - **Alternative rejected:** Extending the generic RPC with a "mode" flag — mixes concerns and complicates the function used by every other test type.

3. **One token per content word, particles attached as `trailing_particle`.**
   - **Rationale:** Odaka and heiban are indistinguishable inside a word; the difference shows up on a following particle. Bundling the particle's pitch with the host word lets the contour visualization display the full disambiguating shape without needing a separate "particle token" in the gameplay loop.
   - **Alternative rejected:** Emit particles as their own tokens. They'd need their own input UI, double-counting accent decisions and breaking the "one word, one accent" mental model.

4. **Hybrid Quick/Contour UI with mode toggle.**
   - **Rationale:** Quick mode matches the pinyin trainer's muscle memory and ships the fastest drill loop. Contour mode trains exact-mora accuracy (the actual linguistic representation) and exposes the universal rules to the learner. Same backend payload powers both; learners can ramp from Quick → Contour as their model deepens.
   - **Alternative rejected:** Picking one. Quick alone undertrains the position knowledge; Contour alone is too slow for many short words.

5. **Visual recall only in v1 (no audio).**
   - **Rationale:** Matches the pinyin trainer. Avoids new TTS infrastructure (JP voice seeding into `dim_languages.tts_voice_ids`, per-word audio rendering and R2 caching). Audio is documented as Phase 2 if learner feedback shows perception drills are needed.
   - **Alternative rejected:** Per-word TTS in v1. Adds 1–2 minutes to test creation, requires JP voice config, and is the longest pole in the tent for shipping the feature.

6. **Error-penalised accuracy with retry-in-place.**
   - **Rationale:** Same fix the pinyin trainer landed on 2026-05-06. Wrong answers retry until correct, so `correctCount` always equals `totalUnits` at game end. The informative metric is the error count, which feeds the ELO update consistently across modes.

## Security Considerations

- Submit endpoint is JWT-gated (`@supabase_jwt_required`).
- RPC enforces `p_user_id == auth.uid()` server-side, preventing cross-user submission spoofing.
- Idempotency key path prevents double-credit on retries / network replays.
- Input validation rejects pathological inputs (`total_units <= 0`, `correct_units > total_units`).
- Language gate on the route (`language_id == 3`) prevents the JA-only RPC from being called against non-Japanese tests.

## Testing Strategy

### Service unit tests

Confirmed working in repo via manual probe — `process_passage` correctly classifies:
- 東京 (heiban, 4 mora, L-H-H-H)
- 男 (odaka, 3 mora, L-H-H, particle drops)
- 命 (atamadaka, 3 mora, H-L-L)
- 日本 (nakadaka, 4 mora, L-H-H-L)
- 首都 (atamadaka, 2 mora, H-L)
- さくら (heiban, 3 mora, L-H-H, particle stays H)

### Backfill verification

```
SELECT COUNT(*) FILTER (WHERE pitch_payload IS NOT NULL),
       COUNT(*) FILTER (WHERE jsonb_array_length(pitch_payload) > 0)
FROM tests WHERE language_id = 3 AND is_active = TRUE;
```

Expected: both equal to total JA test count (80 at time of writing).

### End-to-end smoke (in browser)

1. Log in as a JA learner, open a JA test preview → confirm "Pitch Accent" button visible.
2. Click → lands on `/test/<slug>/pitch-accent`. Confirm the kana grid renders and the first token is highlighted.
3. Quick mode loop: play through a short test using arrow keys. Make at least one deliberate mistake; confirm the error modal pops with the canonical contour and class explanation. Complete → confirm results screen shows accuracy = `(total − errors) / total`.
4. Toggle to Contour mode mid-game. Build a contour; submit an invalid one (e.g., L-H-L-H-L) → confirm the rule-violation error fires. Submit a valid-but-wrong contour → confirm the position-mismatch error fires.
5. Verify in DB: `test_attempts` row has `user_elo_before/after` populated; `user_skill_ratings` and `test_skill_ratings` for `test_type_id = pitch_accent` moved by `K=32 × (actual − expected)`.
6. Submit the same test a second time → confirm `is_first_attempt = false` and ELO is unchanged (matches pinyin behavior).
7. Switch UI locale to ja/zh/es and confirm no dotted i18n keys appear on the preview or trainer page.

## Out of Scope (Phase 2 candidates)

- **Audio playback** — per-phrase TTS with `は`/`が` appended, R2 caching, JP voice seeding into `dim_languages.tts_voice_ids` for `language_id=3`. Adds *perception* training on top of v1's *recall* training.
- **Admin override / LLM disambiguation** — mirror of `resolve_polyphones_llm` for ambiguous compounds and proper nouns where pyopenjtalk's accent is noisy. Backfill shows 0/80 tests flagged for review on current corpus, so the need is not urgent.
- **Compound rule engine** — proper morphophonological reassignment for compound nouns. v1 accepts pyopenjtalk's output verbatim.
- **Word-sense disambiguation** — same-spelling-different-accent (端/雨/橋/箸). Would require linking accent to `dim_word_senses`.
- **Curated word-list standalone mode** — a non-test path (like Listening Lab) for learners with no Japanese tests. Test-mode primary surface is enough for v1.
