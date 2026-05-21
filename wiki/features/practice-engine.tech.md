---
title: Practice Engine — Technical Specification
type: feature-tech
status: planned
prose_page: ./practice-engine.md
last_updated: 2026-05-21
dependencies:
  - "migrations/study_plans_v1/002_dim_practice_modes.sql — dim_practice_modes seed"
  - "migrations/study_plans_v1/007_alter_user_exercise_sessions_mode.sql — adds mode + target_minutes columns"
  - "migrations/study_plans_v1/001_dim_exercise_types.sql — adds expected_seconds per type"
  - "migrations/practice_merger/get_practice_session.sql — new RPC"
  - "services/practice_session_service.py (renamed from exercise_session_service.py)"
  - "routes/practice.py (new), routes/vocab_dojo.py, routes/exercises.py (now wrappers)"
  - "user_word_ladder table (Phase 8 + Phase 10 columns)"
  - "user_vocabulary_knowledge, user_flashcards tables"
  - "exercises table (sense_id, irt_difficulty, irt_discrimination, irt_n_attempts)"
  - "dim_practice_modes, dim_exercise_types (new dim tables)"
breaking_change_risk: medium
---

# Practice Engine — Technical Specification

## Architecture Overview

The Practice Engine is a single SQL-RPC-driven surface with mode dispatch. All scoring, candidate-pool composition, fall-through logic, and time accounting live in `get_practice_session`. Python orchestrates only:
- Mode resolution when `'auto'` is requested.
- Cold-ladder auto-subscription from selected packs.
- Gate / stress-test battery composition (delegated to existing `LadderService` methods).
- Reporting per-session minutes to `record_session_progress`.

```
GET /api/practice/session?mode=auto&minutes=15&language_id=cn
  → PracticeSessionService.get_session(user, language, mode, minutes, theta)
      ├─ If mode='auto': auto_mode_dispatch(user, language)  → 'maintenance' | 'acquisition'
      ├─ If mode='acquisition' and eligible_words is empty:
      │     auto_subscribe_from_packs(user, language, n=target_new_rate)
      │     If still empty: switch mode='maintenance'
      ├─ db.rpc('get_practice_session', user, language, resolved_mode, minutes, theta)
      │     → returns jsonb { session_id, mode_resolved, items[], elapsed_seconds, ... }
      ├─ For Acquisition: hydrate pending gate / stress batteries inline
      └─ Return jsonb (UI renders items[] sequentially)

POST /api/practice/attempt
  → record_attempt_with_updates(...)
  → ladder_record_attempt (if sense-linked) or exercise-only attempt log
  → bkt_update_* + fsrs update (existing)
  → record_session_progress(user, language, attempt_id, 'practice_'||mode,
                            NULL, minutes_for_this_item)
  → Return RPC jsonb
```

Old routes (`/api/exercises/session`, `/api/vocab-dojo/session`) wrap the same handler with default `mode='auto'` and `mode='acquisition'` respectively.

## RPC: `get_practice_session`

**Location:** `migrations/practice_merger/get_practice_session.sql`

```sql
CREATE OR REPLACE FUNCTION public.get_practice_session(
    p_user_id        uuid,
    p_language_id    smallint,
    p_mode           text     DEFAULT 'auto',     -- 'acquisition'|'maintenance'|'auto'
    p_target_minutes smallint DEFAULT 15,
    p_user_theta     numeric  DEFAULT NULL
) RETURNS jsonb
```

### Input validation

- `p_language_id` must exist in `dim_languages` with `is_active = true`. Else returns `{"error":"language_not_active","code":"E_LANG"}`.
- `p_mode IN ('acquisition','maintenance','auto')`. Else returns `{"error":"invalid_mode","code":"E_MODE"}`.
- `1 <= p_target_minutes <= 180`. Else `{"error":"target_minutes_out_of_range","code":"E_RANGE"}`.

### Mode resolution

If `p_mode = 'auto'`:

```sql
SELECT CASE
  WHEN (SELECT COUNT(*) FROM user_flashcards
        WHERE user_id=:u AND language_id=:l AND due_date <= CURRENT_DATE)
       + (SELECT COUNT(*) FROM user_vocabulary_knowledge uvk
          WHERE uvk.user_id=:u AND uvk.language_id=:l
            AND bkt_effective_p_known(uvk.p_known, uvk.last_evidence_at,
                  (SELECT stability FROM user_flashcards
                   WHERE user_id=:u AND sense_id=uvk.sense_id),
                  uvk.evidence_count) < uvk.p_known - 0.05)
       >=
       (SELECT COUNT(*) FROM user_word_ladder
        WHERE user_id=:u AND language_id=:l
          AND word_state IN ('active','gated','pre_mastery','relearning'))
  THEN 'maintenance'
  ELSE 'acquisition'
END;
```

### θ resolution

If `p_user_theta IS NULL`: compute via existing `irt_compute_user_theta(:u, :l)`. Cache for the duration of the call.

### Unified score formula (in-RPC SQL helper)

```sql
CREATE OR REPLACE FUNCTION public.practice_unified_score(
    p_a numeric, p_b numeric, p_theta numeric,         -- IRT params
    p_p_known numeric,                                  -- BKT
    p_due_date date, p_stability real, p_today date,   -- FSRS
    p_ladder_priority numeric,                          -- ladder
    p_alpha numeric, p_beta numeric, p_gamma numeric, p_delta numeric
) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
  WITH terms AS (
    SELECT
      -- ladder term
      GREATEST(0, LEAST(1, COALESCE(p_ladder_priority, 0))) AS lad,
      -- IRT term: I(θ) = a² · P(θ)(1-P(θ)); norm by 0.25
      LEAST(1.0,
        (p_a * p_a) *
        (1.0 / (1.0 + exp(-p_a * (p_theta - p_b)))) *
        (1.0 - 1.0 / (1.0 + exp(-p_a * (p_theta - p_b))))
        / 0.25
      ) AS irt,
      -- BKT term
      1 - 2 * abs(COALESCE(p_p_known, 0.5) - 0.5) AS bkt,
      -- FSRS term: sigmoid(clamp(-2, days_overdue/stability, +4))
      CASE
        WHEN p_due_date IS NULL OR p_stability IS NULL THEN 0
        ELSE 1.0 / (1.0 + exp(-LEAST(4.0, GREATEST(-2.0,
              (p_today - p_due_date)::numeric / GREATEST(p_stability, 1)
            ))))
      END AS fsrs
  )
  SELECT p_alpha*lad + p_beta*irt + p_gamma*bkt + p_delta*fsrs FROM terms
$$;
```

### Acquisition mode (SQL + iteration)

Candidate selection (eligible words):

```sql
SELECT
  uwl.sense_id, uwl.current_ring, uwl.word_state, uwl.family_confidence,
  -- ladder priority is already produced by get_ladder_session; reuse its CTE
  -- or inline the same priority formula
  ladder_compute_priority(uwl.*) AS ladder_priority
FROM user_word_ladder uwl
WHERE uwl.user_id = :u
  AND uwl.language_id = :l
  AND uwl.word_state IN ('active','gated','pre_mastery','relearning')
ORDER BY ladder_priority DESC
LIMIT 50;            -- top 50 candidate words; over-fetch for the inner loop
```

For each picked word, enumerate `ring_families(current_ring)`. For each family, pick the top exercise by unified score within that family:

```sql
WITH fams AS (SELECT unnest(ladder_ring_families(:ring,
                                                 :active_levels)) AS family)
SELECT DISTINCT ON (det.family)
  e.id, e.exercise_type, det.family,
  practice_unified_score(
    e.irt_discrimination, e.irt_difficulty, :theta,
    uvk.p_known,
    fc.due_date, fc.stability, CURRENT_DATE,
    :ladder_priority,
    :alpha, :beta, :gamma, :delta
  ) AS score
FROM fams det
JOIN dim_exercise_types det2 ON det2.family = det.family AND det2.is_active
JOIN exercises e ON e.exercise_type = det2.type_code
                AND e.sense_id = :sense_id
                AND e.language_id = :l
LEFT JOIN user_vocabulary_knowledge uvk
   ON uvk.user_id = :u AND uvk.sense_id = e.sense_id
LEFT JOIN user_flashcards fc
   ON fc.user_id = :u AND fc.sense_id = e.sense_id
WHERE e.id NOT IN (SELECT id FROM seen_today)
ORDER BY det.family, score DESC;
```

Iteration loop (in Python or PL/pgSQL):

```python
def acquisition_session(user, language, target_minutes, theta):
    items = []
    elapsed_s = 0
    target_s = target_minutes * 60
    eligible = load_eligible_words(user, language, limit=50)
    if not eligible:
        seeded = auto_subscribe_from_packs(user, language,
                                           n=target_new_rate(user, language))
        if seeded:
            eligible = seeded
        else:
            return maintenance_session(user, language, target_minutes, theta)

    weights = dim_practice_modes['acquisition'].default_weights

    while elapsed_s < target_s and eligible:
        word = eligible[0]  # highest ladder_priority
        families = ladder_ring_families(word.current_ring, active_levels)
        for fam in families:
            item = pick_top_by_score(word.sense_id, fam, theta, weights)
            if item is None:
                continue
            items.append({**item, 'family': fam, 'mode': 'acquisition'})
            elapsed_s += expected_seconds(item.exercise_type)
            if elapsed_s >= target_s:
                break
        # gate / stress test if pending and time remains
        if word.gate_pending and elapsed_s < target_s:
            items.extend(assemble_gate_battery(word))
            elapsed_s += 180
        if word.stress_test_pending and elapsed_s < target_s:
            items.extend(assemble_stress_test(word))
            elapsed_s += 420
        eligible = eligible[1:]

    return items, elapsed_s
```

### Maintenance mode (SQL)

```sql
WITH due_or_decayed AS (
  SELECT DISTINCT sense_id, stability, due_date,
         NULL::numeric AS p_known_override
  FROM user_flashcards
  WHERE user_id = :u AND language_id = :l
    AND due_date <= CURRENT_DATE + INTERVAL '7 days'
  UNION
  SELECT DISTINCT uvk.sense_id, NULL::real, NULL::date, uvk.p_known
  FROM user_vocabulary_knowledge uvk
  LEFT JOIN user_flashcards fc
    ON fc.user_id = uvk.user_id AND fc.sense_id = uvk.sense_id
  WHERE uvk.user_id = :u AND uvk.language_id = :l
    AND bkt_effective_p_known(uvk.p_known, uvk.last_evidence_at,
                              fc.stability, uvk.evidence_count)
        < uvk.p_known - 0.05
),
ranked AS (
  SELECT *,
    GREATEST(0, (CURRENT_DATE - due_date)::numeric
                / NULLIF(stability, 0))::numeric AS urg_proxy
  FROM due_or_decayed
  ORDER BY urg_proxy DESC NULLS LAST, sense_id
  LIMIT 200                                -- R4.10 hard cap
),
candidates AS (
  SELECT e.id, e.exercise_type, r.sense_id,
    practice_unified_score(
      e.irt_discrimination, e.irt_difficulty, :theta,
      COALESCE(uvk.p_known, r.p_known_override),
      r.due_date, r.stability, CURRENT_DATE,
      ladder_compute_priority(uwl.*),
      :alpha, :beta, :gamma, :delta
    ) AS score
  FROM ranked r
  JOIN exercises e ON e.sense_id = r.sense_id
                  AND e.language_id = :l
                  AND e.sense_id IS NOT NULL                -- ADR-012
  LEFT JOIN user_vocabulary_knowledge uvk
       ON uvk.user_id = :u AND uvk.sense_id = e.sense_id
  LEFT JOIN user_word_ladder uwl
       ON uwl.user_id = :u AND uwl.sense_id = e.sense_id
)
SELECT * FROM candidates ORDER BY score DESC;
```

Python wraps this and accumulates items until `elapsed_seconds >= target_minutes * 60`. If exhausted earlier, falls through to `acquisition_session` for remaining minutes (R4.5).

### Return shape

```jsonc
{
  "session_id": "11111111-2222-3333-4444-555555555555",
  "mode_requested": "auto",
  "mode_resolved":  "acquisition",
  "target_minutes": 15,
  "elapsed_seconds": 920,
  "items": [
    {
      "exercise_id": "uuid",
      "sense_id": 1234,
      "exercise_type": "mcq_meaning",
      "family": "form_recognition",
      "content": { "...": "..." },
      "ladder_level": 3,
      "p_known": 0.42,
      "expected_seconds": 40,
      "mode": "acquisition",
      "is_gate": false,
      "is_stress_test": false,
      "score_breakdown": {        // included when ?debug=1
        "ladder": 0.62, "irt": 0.81, "bkt": 0.93, "fsrs": 0.18,
        "alpha": 0.40, "beta": 0.30, "gamma": 0.25, "delta": 0.05,
        "unified": 0.671
      }
    }
  ],
  "no_content_reason": null   // 'no_packs_selected' | 'all_complete' | null
}
```

### Error cases

| Code | Returned shape |
|---|---|
| `E_LANG` | `{ "error": "language_not_active", "code": "E_LANG" }` |
| `E_MODE` | `{ "error": "invalid_mode", "code": "E_MODE" }` |
| `E_RANGE` | `{ "error": "target_minutes_out_of_range", "code": "E_RANGE" }` |

## Mode weights (table-driven)

```sql
-- migrations/study_plans_v1/002_dim_practice_modes.sql
CREATE TABLE dim_practice_modes (
  mode_id         smallint PRIMARY KEY,
  name            text NOT NULL UNIQUE,
  default_weights jsonb,
  is_active       boolean NOT NULL DEFAULT true
);

INSERT INTO dim_practice_modes VALUES
  (1, 'acquisition', '{"alpha":0.40,"beta":0.30,"gamma":0.25,"delta":0.05}', true),
  (2, 'maintenance', '{"alpha":0.05,"beta":0.15,"gamma":0.30,"delta":0.50}', true),
  (3, 'auto',        null,                                                    true);
```

Weights are loaded once per RPC call and passed to `practice_unified_score` as constants — no per-row lookup overhead.

## Time accounting

New table `dim_exercise_types` carries the canonical per-type expected duration:

```sql
CREATE TABLE dim_exercise_types (
  type_code             text PRIMARY KEY,
  family                text NOT NULL,         -- one of the 6 cognitive families
  expected_seconds      smallint NOT NULL DEFAULT 45,
  expected_seconds_p50  numeric(5,1),          -- nullable, refreshed nightly
  is_active             boolean NOT NULL DEFAULT true
);
```

Seed via:

```sql
INSERT INTO dim_exercise_types (type_code, family, expected_seconds)
SELECT DISTINCT exercise_type,
       map_exercise_type_to_family(exercise_type),
       45
FROM exercises
WHERE exercise_type IS NOT NULL
ON CONFLICT DO NOTHING;
```

Nightly refresh (in `_refresh_exercise_time_estimates`, runs at 04:05 UTC after IRT):

```sql
UPDATE dim_exercise_types det
SET expected_seconds_p50 = src.p50
FROM (
  SELECT exercise_type,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY time_taken_ms) / 1000.0 AS p50
  FROM exercise_attempts
  WHERE time_taken_ms IS NOT NULL
    AND created_at > NOW() - INTERVAL '30 days'
  GROUP BY exercise_type
  HAVING COUNT(*) >= 30
) src
WHERE det.type_code = src.exercise_type;
```

Service-layer `expected_seconds(exercise_type)` returns `det.expected_seconds_p50` when not NULL, else `det.expected_seconds`.

## Deprecation wrappers

```sql
-- get_exercise_session — wraps get_practice_session('auto', ...)
CREATE OR REPLACE FUNCTION public.get_exercise_session(
  p_user_id uuid, p_language_id smallint,
  p_session_size integer DEFAULT 20,
  p_user_theta numeric DEFAULT 0.0
) RETURNS TABLE (
  out_exercise_id   uuid,
  out_sense_id      integer,
  out_exercise_type text,
  out_content       jsonb,
  out_complexity_tier text,
  out_phase         text,
  out_slot_type     text,
  out_priority      numeric
) AS $$
  -- Approximate minutes from legacy session_size
  WITH res AS (
    SELECT get_practice_session(p_user_id, p_language_id, 'auto',
                                GREATEST(1, (p_session_size * 0.6)::smallint),
                                p_user_theta) AS payload
  ),
  items AS (
    SELECT jsonb_array_elements(payload->'items') AS item FROM res
  )
  SELECT
    (item->>'exercise_id')::uuid,
    (item->>'sense_id')::integer,
    item->>'exercise_type',
    item->'content',
    NULL::text, NULL::text, NULL::text,
    (item->>'score_breakdown')::jsonb->>'unified'::text::numeric
  FROM items;
$$ LANGUAGE sql;
```

Equivalent wrapper for `get_ladder_session` calls `get_practice_session('acquisition', count * 0.5)`. Both wrappers log `RAISE WARNING 'DEPRECATED: use get_practice_session'` once per session.

## Service-layer file changes

| File | Change |
|---|---|
| `services/exercise_session_service.py` → `services/practice_session_service.py` | Rename. Split into `_acquisition.py`, `_maintenance.py`, `_scoring.py`. |
| `routes/exercises.py` | `/api/exercises/session` becomes thin wrapper calling `get_practice_session('auto', ...)`. |
| `routes/vocab_dojo.py` | `/api/vocab-dojo/session` wraps `get_practice_session('acquisition', ...)`. Gate / stress-test endpoints unchanged. |
| `routes/practice.py` (NEW) | Canonical `/api/practice/session?mode=...&minutes=...`. Also `POST /api/practice/attempt`. |
| `services/irt/calibrator.py` | Nightly `_refresh_exercise_time_estimates` step added (04:05 UTC). |
| `app.py:227-251` | Add `exercise_time_estimate_refresh` cron entry. |

## Parity test (R4.7)

`tests/integration/test_practice_merger_parity.py`:

1. Seed 50 staging users across 4 cohorts (≥10 each):
   - **new**: < 5 ladder rows, < 5 test attempts.
   - **mid_ladder**: 30–80 ladder-active words, mixed rings.
   - **mostly_mastered**: > 200 mastered words, < 20 active.
   - **lapsed**: idle ≥ 30 days, FSRS-due > 50.
2. For each user, call both `get_ladder_session(20)` and `get_practice_session('acquisition', target_minutes = 12)`. Extract item ID sets.
3. Compute Jaccard = `|A ∩ B| / |A ∪ B|`.
4. Pass iff: `median(jaccards) >= 0.70` AND `min(jaccards) >= 0.50`.
5. Repeat for `get_exercise_session` vs `get_practice_session('auto', minutes = session_size * 0.6)`.

A run report (CSV of per-user Jaccard + cohort + size) is written to `wiki/raw/parity_reports/<date>.csv` for human review.

## Key Architectural Decisions

1. **Mode-dependent weights with the same unified score across modes** rather than two separate scoring formulas. Lets us add new signals (e.g. novelty boost) by editing one formula instead of two.
2. **Per-mode candidate pools** rather than one pool with mode-dependent filtering. The pool definitions differ enough (ladder-active set vs FSRS-due-set) that splitting them keeps the SQL readable.
3. **Maintenance → Acquisition fall-through** rather than ending early on dry. Honors learner time intent; UI handles the mid-session mode flip via per-item `mode` field.
4. **Hard LIMIT 200 candidates** at the cheap-rank stage. Caps unified-score compute at ≤ 200 evaluations per session; covers ≥ 3× typical 30-min Maintenance volume.
5. **Wrapper RPCs for backwards compatibility** rather than hard cutover. One release of overlap protects against ranking regressions discovered post-flip.
6. **`exercises.sense_id IS NOT NULL` filter at the candidate-pool SQL** rather than at item assembly. Cleanest place to enforce ADR-012; one filter, both modes.

## Security Considerations

- All RPCs are `SECURITY INVOKER`; rely on Supabase RLS for `exercises`, `user_word_ladder`, `user_vocabulary_knowledge`, `user_flashcards` access (existing).
- `p_user_id` is server-supplied from the session; never accepted from the client. The route layer pulls it from `flask.g.user_id`.
- No PII in `score_breakdown` debug payload; safe to log.

## Testing Strategy

- **Unit**: `practice_unified_score()` SQL helper tested with hand-computed values for: peak-IRT-info, peak-BKT-uncertainty, far-overdue FSRS, gated ladder word.
- **Unit**: Python `auto_mode_dispatch` with seeded counts on either side of the threshold.
- **Integration**: Parity tests above (R4.7).
- **Integration**: Cold-ladder flow — new user, no packs → empty session with `no_content_reason='no_packs_selected'`.
- **Integration**: Maintenance fall-through — seed user with 1 FSRS-due item + 50 ladder-active. Request `mode='maintenance', minutes=20`. Assert items include both modes; first item has `mode='maintenance'`; later items have `mode='acquisition'`.
- **Performance**: P95 < 500ms for `get_practice_session` over 200-candidate pool; benchmark in staging with `EXPLAIN ANALYZE`.

## Related Pages

- [[features/practice-engine]] — Plain-English counterpart.
- [[algorithms/practice-unified-score.tech]] — Per-term math in depth.
- [[algorithms/vocabulary-ladder.tech]] — Ring/family/gate mechanics (preserved).
- [[features/vocabulary-knowledge.tech]] — BKT formula source.
- [[features/flashcards.tech]] — FSRS source.
- [[features/study-plans.tech]] — How `target_minutes` and mode are determined.
- [[database/schema.tech]] — Schema changes.
- [[database/rpcs.tech]] — Full RPC signatures.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]], [[decisions/ADR-012-grammar-items-excluded-v1]].
