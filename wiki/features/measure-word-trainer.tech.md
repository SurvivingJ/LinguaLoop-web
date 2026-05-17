---
title: Measure Word Trainer — Technical Specification
type: feature-tech
status: complete
prose_page: ./measure-word-trainer.md
last_updated: 2026-05-17
dependencies:
  - "dim_classifiers, dim_classifier_distractor_groups, dim_classifier_noun_pairs (new tables)"
  - "dim_test_types row classifier_drill (id=14)"
  - "tests sentinel row slug='__classifier_drill_zh'"
  - "test_attempts / user_skill_ratings / test_skill_ratings"
  - "get_classifier_drill_session() RPC"
  - "process_classifier_drill_submission() RPC"
breaking_change_risk: low
---

# Measure Word Trainer — Technical Specification

## Architecture Overview

```
Dictionary build (one-time, idempotent):
  scripts/build_classifier_dictionary.py
    embedded CLASSIFIERS list + NOUN_CLASSIFIERS mapping
    → dim_classifier_distractor_groups  (12 rows, seeded by migration)
    → dim_classifiers                   (40 rows, language_id=1)
    → dim_classifier_noun_pairs         (269 rows, multi-valid per noun)

Session serving:
  GET /api/classifier-drill/session?language_id=1&count=20
    → routes/classifier_drill.py: get_drill_session
    → services/classifier_drill_service.py: get_session
    → db.rpc('get_classifier_drill_session', {user_id, language_id, count})
    → returns 20 items, each:
        {pair_id, noun_lemma, noun_sense_id, noun_gloss, noun_pronunciation,
         correct_classifier_ids[], correct_classifier_hanzi[],
         distractor_ids[], distractor_hanzi[], distractor_pinyin[],
         semantic_label, distractor_group_label}

Gameplay (templates/classifier_drill.html):
  Single-page SPA. State: {mode, items, cursor, correct, errors,
                            startTime, currentOptions, isLocked, currentItem}.
  Toggle [Choose | Type] persisted to localStorage.cd_mode.
  MC mode: 4 shuffled buttons, keys 1-4. Type mode: <input> accepts any
  hanzi in correct_classifier_ids.
  Wrong → feedback modal (canonical 一<correct><noun>, group label,
  also-acceptable list).

Submission:
  POST /api/classifier-drill/submit  body:{language_id,correct_items,total_items,
                                            time_taken,idempotency_key?}
    → routes/classifier_drill.py: submit_drill
    → services/classifier_drill_service.py: submit_session
        (looks up sentinel test_id once, caches)
    → db.rpc('process_classifier_drill_submission', ...)
    → K=32 ELO update on user_skill_ratings + test_skill_ratings
    → INSERT INTO test_attempts (percentage column is GENERATED ALWAYS)
```

## Database Impact

### New tables (migration: `add_classifier_drill_mode.sql`)

```sql
dim_classifier_distractor_groups (12 rows for language_id=1):
  id smallserial PK, language_id smallint FK→dim_languages,
  label text, description text, created_at timestamptz,
  UNIQUE(language_id, label)

dim_classifiers (40 rows for language_id=1):
  id smallserial PK, language_id smallint FK→dim_languages,
  hanzi text, pinyin text, pinyin_display text,
  semantic_label text, example_nouns text[] DEFAULT '{}',
  frequency_rank integer, distractor_group_id smallint FK,
  UNIQUE(language_id, hanzi)
  INDEX on distractor_group_id

dim_classifier_noun_pairs (269 rows for language_id=1):
  id serial PK, language_id smallint FK, noun_sense_id integer FK→dim_word_senses (nullable),
  lemma_text text, classifier_id smallint FK→dim_classifiers ON DELETE CASCADE,
  is_primary boolean, frequency_score numeric, source text DEFAULT 'curated',
  UNIQUE(language_id, lemma_text, classifier_id)
  INDEX on (language_id, lemma_text)
  INDEX on classifier_id
```

### Modified tables (existing)

- `dim_test_types` — one new row: `(id=14, type_code='classifier_drill', type_name='Measure Words', requires_audio=false, is_active=true, display_order=6)`
- `tests` — one new sentinel row: `slug='__classifier_drill_zh'`, `is_active=false`, language_id=1.
- `test_skill_ratings` — one new row anchoring `(sentinel_test_id, classifier_drill_type_id)` at ELO 1400.
- `user_skill_ratings` — rows created lazily by the submission RPC on first attempt.
- `test_attempts` — rows written by the submission RPC. `percentage` is GENERATED ALWAYS — the INSERT omits it.

### Reads / writes

- Session RPC reads `dim_classifier_noun_pairs`, `dim_classifiers`, `dim_classifier_distractor_groups`, `dim_word_senses`.
- Submission RPC reads/writes `test_attempts`, `user_skill_ratings`, `test_skill_ratings`, `user_languages`.

## API / RPC Surface

### `GET /api/classifier-drill/session`
- **Auth:** JWT required.
- **Query:** `language_id` (required, only `1` accepted in v1); `count` (default 20, max 40).
- **Returns:**
  ```json
  {"data": {"items": [{...}, ...], "count": 20, "language_id": 1}}
  ```
- **Errors:** 400 if `language_id` missing or != 1.

### `POST /api/classifier-drill/submit`
- **Auth:** JWT required.
- **Body:** `language_id`, `correct_items`, `total_items`, optional `time_taken`, `idempotency_key`.
- **Side effects:** Inserts `test_attempts` row, mutates `user_skill_ratings` + `test_skill_ratings`, increments `user_languages.total_tests_taken`.
- **Returns:**
  ```json
  {"data": {"accuracy": 80.0, "correct_items": 16, "total_items": 20,
            "user_elo_change": {"before": 1200, "after": 1218, "change": 18},
            "test_elo_change": {"before": 1400, "after": 1382, "change": -18},
            "attempt_id": "...", "is_first_attempt": true,
            "test_mode": "classifier_drill"}}
  ```
- **Errors:** 400 on invalid body fields, 500 on RPC failure.

### RPC `get_classifier_drill_session(p_user_id uuid, p_language_id smallint, p_count integer)`
- `SECURITY DEFINER`, `STABLE`. GRANTed to `authenticated`.
- Returns 12 columns (see file `migrations/get_classifier_drill_session.sql`).
- Sampling: `DISTINCT ON (lemma_text)` over `is_primary=true` rows, weighted by `random()*frequency_score`, then `LIMIT count`.
- Per item: pulls *all* acceptable classifier IDs via secondary subquery (multi-valid CC-CEDICT semantics).
- Distractors: 3 from the primary classifier's group, excluding all acceptable IDs; top up from `general` group if the primary group has < 3 alternatives.

### RPC `process_classifier_drill_submission(p_user_id, p_test_id, p_language_id, p_test_type_id, p_correct_items, p_total_items, p_was_free_test, p_idempotency_key)`
- `SECURITY DEFINER`. GRANTed to `authenticated`.
- Same K=32 ELO formula as `process_pinyin_submission`. First-attempt-only motion; repeats increment `tests_taken` but do not move ELO.
- Idempotency: returns `{cached: true, ...}` if `(user_id, idempotency_key)` matches an existing row.
- Returns JSONB envelope `{success, attempt_id, user_elo_*, test_elo_*, percentage, ...}`.

## Component Specification (UI)

### `templates/classifier_drill.html`
- Extends `base.html`.
- All inline JS; no external module. Loads `LinguaI18n` at init.
- State machine in IIFE closure. `loadBatch()` fetches and renders; `renderCurrent()` either calls `renderMcOptions()` or shows the typed input form.
- Keyboard: 1–4 in MC mode; Enter on typed-mode form submit; Enter/Space dismisses feedback.
- Touch + click for mobile.
- Submits on `finishBatch()` and renders ELO delta from response.

## Key Architectural Decisions

1. **Infinite session via sentinel test row**
   - **Rationale:** Reuses the `test_attempts` schema, RLS, ELO formula, and profile dashboard rendering without inventing a parallel "session" table.
   - **Alternatives rejected:** New `classifier_drill_sessions` table — duplicates ELO infrastructure and breaks the profile history rendering pipeline.

2. **Curated dictionary, no LLM**
   - **Rationale:** The user's stated requirement was "a complete dictionary without LLMs". A curated seed gives full determinism, auditable provenance, and zero per-request cost.
   - **Alternatives rejected:** LLM seeding (drifts between batches, costs); pure on-demand LLM (latency, cost); corpus mining (coverage too sparse against the existing test catalog).

3. **Semantic distractor groups, hand-curated (12 groups, 40 classifiers)**
   - **Rationale:** Plausibility of distractors is the single most important quality lever for an MC drill. Random distractors trivialise the task. Grouping classifiers by semantic class lets the system always serve confusable alternatives.
   - **Alternatives rejected:** Embedding similarity between classifiers (no embeddings available offline, would need a model); random sampling (too easy); fixed pairs (too few combinations).

4. **MC + Typed runtime toggle**
   - **Rationale:** MC is the productive scaffolded mode for early learners; Typed forces recall. Locking the user to either mode is unnecessary friction. Persists in `localStorage.cd_mode`.
   - **Alternatives rejected:** Two separate pages; ladder-based progression from MC to Typed (Phase 2 candidate).

5. **First-attempt-only ELO motion**
   - **Rationale:** Matches the pinyin/pitch-accent convention. Without this an infinite trainer would farm ELO trivially.
   - **Alternatives rejected:** Time-decay ELO ([[decisions/ADR-006-retry-slot-reduced-elo]]) — adds complexity without clear product gain for an infinite trainer.

## Security Considerations

- Both endpoints require JWT auth via `@supabase_jwt_required`.
- Backend rejects any `language_id != 1` in v1.
- Submission RPC validates `0 ≤ correct_items ≤ total_items`. Negative or oversized values raise an exception which is captured into the JSONB envelope as `success: false`.
- `auth.uid() != p_user_id` exception is the standard guard; service-role calls bypass via `NULL != p_user_id` semantics (matches pinyin/pitch-accent).
- Idempotency key recommended for client-side retry safety; falls back to a server-generated UUID when omitted.

## Testing Strategy

- **Data quality (one-shot):** `SELECT COUNT(*)` on the three new dim tables; spot-check ~10 high-frequency lemmas against the expected classifier (`猫→只`, `车→辆`, `书→本`, etc.).
- **Session RPC:** `SELECT * FROM get_classifier_drill_session(<uuid>, 1::smallint, 5)` — assert 5 rows, each with `array_length(correct_classifier_ids,1) ≥ 1` and `array_length(distractor_ids,1)` between 2 and 3.
- **Submission RPC:** Call with `correct=16, total=20` → assert `user_elo_change.change` is non-zero on first attempt; replay with same `idempotency_key` → assert `cached=true` and ELO unchanged.
- **Frontend:** No automated tests in v1; covered by the owner walk-through in the log entry.

## Verification History

- 2026-05-17 — Initial dictionary build returned 40 classifiers, 269 pairs, 78 with sense_id linkage. Session RPC + submission RPC both green; idempotency replay verified.

## Related Pages

- [[features/measure-word-trainer]] — Prose description
- [[features/pinyin-trainer.tech]] — Sibling RPC layout (clone target)
- [[features/pitch-accent-trainer.tech]] — Sibling RPC layout
- [[features/exercise-generation-prompts]] — The L6/L7 cloze prompt section that originated the "wrong measure word" error category (left untouched by this work)
- [[algorithms/elo-ranking.tech]] — K=32 formula shared by trainer
- [[database/schema.tech]] — Schema diffs for the three new tables
