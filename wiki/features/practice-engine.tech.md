---
title: Practice Engine — Technical Specification
type: feature-tech
status: complete
prose_page: ./practice-engine.md
last_updated: 2026-11-23
dependencies:
  - "migrations/phase12_dim_practice_modes.sql — dim_practice_modes seed"
  - "migrations/phase12_user_exercise_sessions_columns.sql — adds mode + target_minutes columns"
  - "migrations/phase12_dim_exercise_types.sql — dim_exercise_types, expected_seconds per type"
  - "migrations/phase12_get_practice_session.sql and migrations/phase12_practice_unified_score.sql — original RPC bodies (historical; the live body is exercise_content_drop_column.sql)"
  - "services/practice_session_service.py — composes the three mixins in services/practice/ (see [[features/practice-package.tech]])"
  - "routes/practice.py (GET /api/practice/session, /extra, /speed-round; POST /attempt, /intro/complete), routes/vocab_dojo.py (gate / stress-test endpoints)"
  - "migrations/record_exercise_attempt.sql — the only attempt-recording path (2026-11-23)"
  - "user_word_ladder table (Phase 8 + Phase 10 columns)"
  - "user_vocabulary_knowledge, user_flashcards tables"
  - "exercises table (sense_id, irt_difficulty, irt_discrimination, irt_n_attempts)"
  - "dim_practice_modes, dim_exercise_types (new dim tables)"
  - "services/exercise_content/store.py (ADR-049: rpc_content_args, select_columns, hydrate)"
  - "migrations/exercise_content_drop_column.sql (ADR-049 step 3e: canonical get_practice_session / get_review_ahead_items, live since 2026-11-19; the TASK-1017 pre-drop file is in migrations/archive/)"
breaking_change_risk: medium
open_questions:
  - "The SQL in 'Mode resolution', 'Acquisition mode', 'Maintenance mode' and the Return shape below is the 2026-05 design pseudo-code; it was not re-diffed against the live get_practice_session body (md5 e2f6089f... checked 2026-11-23) in this pass. Treat migrations/exercise_content_drop_column.sql as canonical."
---

# Practice Engine — Technical Specification

## Architecture Overview

The Practice Engine is a single SQL-RPC-driven surface with mode dispatch. All scoring, candidate-pool composition, fall-through logic, and time accounting live in `get_practice_session`. Python (`services/practice/`, composed by `services/practice_session_service.py`; module map in [[features/practice-package.tech]]) orchestrates:
- Ladder intake from learner evidence before the RPC (two nomination queues behind one supply gate; see [[features/new-word-drill.tech]] and [[features/practice-package.tech]]). Pack-based cold-start intake was removed 2026-09-21 with the language-packs archive; the pack pseudo-code below is historical.
- Post-RPC steps: session-size floor, prestudy follow-ups, new-word drill block, ordering, content hydration, script variant, jumbled preparation, DT error cards.
- Gate / stress-test battery composition (delegated to existing `LadderService` methods).
- Attempt recording: one RPC, `record_exercise_attempt`, plus FSRS in Python.

Current request flow (verified against code at commit 0d345e98, 2026-11-23):

```
GET /api/practice/session?mode=auto&minutes=15&language_id=L          (routes/practice.py)
  -> PracticeSessionService.get_session(user, language, mode, minutes, debug, tail)   (services/practice/session_assembly.py)
      1. validate mode / minutes (E_MODE, E_RANGE)
      2. acquisition|auto: _maybe_top_up_ladder -> admit_daily_new_words
      3. in parallel: get_practice_session RPC | due prestudy follow-ups | intro sense ids | exercise_preferences
      4. _apply_session_floor (acquisition|auto), _inject_prestudy_followups (maintenance|auto, not tail)
      5. intro_drill: route_untaught, drop intro senses from items, block_for_session
      6. _order_items; strip score_breakdown unless debug; hydrate content (ADR-049)
      7. _apply_script_variant, _prepare_jumbled_items, DT error cards interleaved

POST /api/practice/attempt                                             (routes/practice.py)
  -> typed re-grade (cloze_typed only) -> record_attempt_with_updates   (services/practice/attempt_recording.py)
      -> db.rpc('record_exercise_attempt')   one transaction, see "Attempt recording" below
      -> FSRS review in Python (+ bkt_apply_lapse_penalty on a lapse)
```

Old routes (`/api/exercises/session`, `/api/vocab-dojo/session`) were removed (see "Deprecation wrappers"); the former exercises route module and exercise-session service module were deleted on 2026-11-14 and their code lives in `services/practice/` and `services/study_session/`.

## RPC: `get_practice_session`

**Location:** original body `migrations/phase12_get_practice_session.sql` (historical); canonical live body `migrations/exercise_content_drop_column.sql` step 3e.

```sql
CREATE OR REPLACE FUNCTION public.get_practice_session(
    p_user_id        uuid,
    p_language_id    smallint,
    p_mode           text     DEFAULT 'auto',     -- 'acquisition'|'maintenance'|'auto'
    p_target_minutes smallint DEFAULT 15,
    p_user_theta     numeric  DEFAULT NULL
) RETURNS jsonb
```

> **ADR-049 (TASK-1017 / TASK-1030 / TASK-1031).** The live function is
> `get_practice_session(p_user_id uuid, p_language_id smallint, p_mode text DEFAULT 'auto',
> p_target_minutes smallint DEFAULT 15, p_user_theta numeric DEFAULT NULL, p_include_content
> boolean DEFAULT true) RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = public, pg_temp`,
> service_role only. Since the cut-over (2026-11-19) it never returns `content`:
> `p_include_content` is accepted and ignored, and every exercise item carries `content_version`
> instead (gate / stress markers are unchanged). Python always passes `p_include_content = false`
> and fills the content from the files. Canonical body: `migrations/exercise_content_drop_column.sql`
> step 3e (live md5 `e2f6089f…` = that body, checked 2026-11-19). The 5-argument
> `migrations/archive/get_practice_session_language_scope.sql` and the pre-drop 6-argument
> `migrations/archive/exercise_content_session_rpcs.sql` are archived (TASK-1031). The
> canonical-file location above is historical.

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
      "content": { "...": "..." },   // never from the RPC (ADR-049); filled in Python from the content file
      "content_version": 0,          // ADR-049: the version of the sense's content file
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
-- migrations/phase12_dim_practice_modes.sql
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

> **REMOVED 2026-07-14 (TASK-220).** Both wrappers were dropped by
> `migrations/archive/phase17_drop_deprecation_wrappers.sql` (archived in TASK-1031) after the one-release
> deprecation window elapsed. `/api/exercises/session` and
> `/api/vocab-dojo/session` now 302 to `/api/practice/session`, and the two
> standalone pages were retired. The SQL below is kept as historical record of
> the wrapper bodies (see `migrations/archive/phase12_deprecation_wrappers.sql`).
>
> **Drift found 2026-11-17 (ADR-049 Context finding 6):** the drop never took effect live.
> `get_exercise_session(uuid,smallint,integer)`, `get_exercise_session(uuid,smallint,integer,numeric)`
> and `get_ladder_session(uuid,smallint,integer)` existed live (service_role only, no Python
> caller) until `migrations/archive/exercise_content_session_rpcs.sql` (TASK-1017) dropped all three on 2026-11-17; checked absent live 2026-11-19.

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

## Service-layer file map

| File | Role (at commit 0d345e98, 2026-11-23) |
|---|---|
| `services/practice_session_service.py` | Import point. `PracticeSessionService(SessionAssemblyMixin, AttemptRecordingMixin, NewWordAdmissionMixin)`; `get_practice_session_service()` singleton; re-exports `services/practice/constants.py`. Renamed from the former exercise-session service module (TASK-106); that file is deleted. |
| `services/practice/session_assembly.py` | `get_session`, `get_extra_round`, floor, follow-ups, ordering, hydration. |
| `services/practice/attempt_recording.py` | `record_attempt_with_updates`, `record_prestudy_exercise_attempt`, `record_speed_round_attempt`, FSRS. |
| `services/practice/new_word_admission.py` | Daily quota state, nomination queues, supply gate, ladder subscription. |
| `services/practice/constants.py` | Tunables. |
| `routes/practice.py` | `GET /api/practice/session`, `GET /api/practice/extra`, `POST /api/practice/attempt`, `GET /api/practice/speed-round`, `POST /api/practice/intro/complete`. Mounted at `/api/practice` in `app.py::_register_blueprints`. |
| `routes/vocab_dojo.py` | Gate / stress-test endpoints (unchanged). |
| `services/study_plan_service.py` | `_refresh_exercise_time_estimates` (nightly job `exercise_time_estimate_refresh`, 04:05 UTC, registered in `web/scheduler.py`). |

The planned split into separate acquisition, maintenance and scoring modules was never made: acquisition, maintenance and scoring are all inside the `get_practice_session` RPC. The old thin wrapper route module for `/api/exercises/session` is deleted.

## Attempt recording (`record_exercise_attempt`, 2026-11-23)

`record_exercise_attempt` (`migrations/record_exercise_attempt.sql`, live, service_role only) is the **only** way a Practice attempt is recorded. The per-step Python path, the `PRACTICE_ATTEMPT_RPC_ENABLED` flag, its "not deployed" probe and the counter-retry code were deleted from `services/practice/attempt_recording.py` (709 -> 436 lines) and `services/practice/constants.py`.

`PracticeSessionService.record_attempt_with_updates(user_id, exercise_id, is_correct, user_response, time_taken_ms, session_mode, language_id, expected_seconds, is_tail, exercise_context)`:

1. `plan_kind` = `'practice_acq'` / `'practice_maint'` when `Config.STUDY_PLAN_ENABLED` and `session_mode` is acquisition / maintenance, else NULL.
2. `p_credit_seconds` = `_effective_practice_seconds(time_taken_ms, expected_seconds)`: missing/zero ms or elapsed over `PRACTICE_ATTEMPT_MAX_SECONDS` (300) credits the item's `expected_seconds` (default `DEFAULT_EXPECTED_SECONDS` = 45, clamped to 300); else the measured seconds rounded, minimum 1.
3. One call: `db.rpc('record_exercise_attempt', {p_user_id, p_exercise_id, p_is_correct, p_user_response, p_time_taken_ms, p_language_id, p_credit_seconds, p_plan_kind, p_is_tail, p_exercise_context})`.
4. Result `{'error': 'exercise_not_found'}` from SQL becomes `{'error': 'Exercise not found'}` (the route answers 500 via `server_error`). Any RPC exception propagates and the route's `api_errors` returns the normal error envelope; because it is one transaction, **nothing is half-written**.
5. FSRS (Python, `services/vocabulary/fsrs.py`): the RPC returns the learner's `user_flashcards` row as `flashcard`; Python rates it (wrong -> AGAIN; correct and under 5000 ms -> EASY; else GOOD), updates the row (`due_date` and `last_review` from one `day_boundary.review_today()` value: the app-wide Sydney review day, see "FSRS review day" below), and on a lapse calls `bkt_apply_lapse_penalty(p_user_id, p_sense_id)` after the BKT write the RPC committed.
6. The ladder summary is copied to `result['ladder']`; after a ring-2 demotion `intro_drill.restart_if_demoted(...)` may set `result['ladder']['intro_restart'] = True`.

Inside the RPC, in order (all in one transaction):

| Step | Failure behaviour |
|---|---|
| exercise lookup (`exercise_type`, `word_sense_id`, `language_id`); `p_language_id` overrides the language | not found: returns `{error:'exercise_not_found'}` |
| `pg_advisory_xact_lock(hashtextextended(user_id || ':' || exercise_id, 0))` then first-attempt check (no earlier `exercise_attempts` row for user + exercise) | fails the call |
| insert `exercise_attempts` with `is_first_attempt` | fails the call |
| `exercises.attempt_count` / `correct_count` incremented atomically | fails the call |
| complete `prestudy_followups` for the sense (`completed_at = now()`) | best effort (`undefined_table` ignored; other errors in `warnings`) |
| first attempts only: `update_vocabulary_from_word_test` (BKT), `bkt_infer_from_frequency` when p_known crosses 0.90 upward, p_known before/after captured on the attempt row | best effort, warnings `bkt`, `frequency_inference`, `p_known_capture` |
| `ladder_apply_progress(..., context)` where context is `standard`, `gate` or `stress_test` (anything else becomes `standard`) | best effort, warning `ladder` |
| `credit_study_time(user, lang, 'practice', secs, 'exercise_attempts', attempt_id)` when secs > 0 | best effort, warning `study_time` |
| `record_session_progress` (kind = `p_plan_kind`, delta seconds, sense id for acquisition, `p_is_tail`) | best effort, warning `session_progress` |
| read the learner's flashcard row | returned as `flashcard` |

Return jsonb: `attempt_id, is_first_attempt, exercise_type, sense_id, language_id, bkt_update, ladder, flashcard, warnings`. Python logs each warning (`prestudy_followups` at INFO, others WARNING). Because the lock serialises per user and exercise, two simultaneous submissions can no longer both count as first attempts.

Database calls per answer (Python side, excluding the lapse penalty and the intro-restart check): **2** when the sense has a flashcard (RPC + card update), **1** with no card, **1** for an exercise with no sense. Before 2026-11-23 the same answer cost 12 (tracked word, first attempt, has a flashcard, planned session), 10 (later attempt), 9 (no card, unplanned) or 5 (no sense).

Live check 2026-11-23: `record_exercise_attempt` exists with the 10-argument signature and its source contains `pg_advisory_xact_lock`. The md5 of the live body was not compared with the file.

Other writers: `record_prestudy_exercise_attempt` (prestudy prime: direct insert tagged `source='prestudy'`, BKT on first attempt only, no ladder / FSRS / plan counters; see [[features/test-prestudy.tech]]) and `record_speed_round_attempt` (FSRS only, never the ladder) are unchanged and do not use the RPC.

### FSRS review day: one app-wide review time zone (Australia/Sydney) (TASK-1211)

Owner decision 2026-11-23: no per-learner local day for flashcards. Every FSRS date (`user_flashcards.due_date` and `last_review` written, and "due today" read) uses **one app-wide review calendar whose day rolls over at midnight Sydney time** (`Australia/Sydney`; owner decision "Use Sydney time"; UTC+11 in daylight saving, first Sunday in October to first Sunday in April, otherwise UTC+10; midnight = 13:00 UTC in daylight saving, 14:00 UTC otherwise). The study plan's own `timezone` (ADR-022) keeps governing only plan / day-slot accounting (load date, week, "reviews done today" window, intro-drill dates). The per-learner local-day design is recorded as not pursued (see TASK-1211).

The zone is configured in exactly two places; change both together (a test, `tests/test_review_day_boundary.py`, fails if they differ):
- **Python:** `services/day_boundary.py` `REVIEW_TIMEZONE`; helpers `review_today()` / `review_today_iso()` (no database round trip).
- **SQL:** the string literal in `public.review_today(p_at timestamptz DEFAULT now())`, `migrations/fsrs_review_day_aest.sql`.

| Side | Writers (stamp the review date) | Readers (decide what is due) |
|---|---|---|
| Python (code done) | `fsrs.schedule_review` default, `attempt_recording._apply_fsrs_review`, `POST /api/flashcards/review` | `GET /api/flashcards/due`, `/stats` |
| SQL (**pending apply**, PENDING-2026-11-23 group 10) | `ladder_graduate`, `ladder_record_attempt` (FSRS lapse path only) | `get_practice_session` (new `v_review_today`), `get_session_senses`, `compute_weekly_plan_load_signals`, `review_governor_state` and `build_daily_session` (their `user_flashcards` comparisons use `review_today()` instead of the plan-local `p_date`; `new_word_state_inputs` reaches them through `review_governor_state`) |

Stays on the UTC date on purpose (not FSRS): `get_practice_session`'s anti-repetition `v_today` (compared with `user_exercise_history.session_date`, whose default is `CURRENT_DATE`), and the ladder's own `family_success_dates`, `review_due_at` and `last_success_session_date` in `ladder_record_attempt`. `last_review` is `timestamptz`; both old and new rows store the calendar date at 00:00 UTC.

**Until the SQL file is applied the system is mixed** once the Python is deployed: deploy the Python and apply the file in one window in which the Sydney and UTC dates are equal, so old and new code agree: 00:00 to 13:00 UTC during daylight saving (11:00 to midnight Sydney time; the window on 2026-11-23) and 00:00 to 14:00 UTC otherwise (10:00 to midnight Sydney time). If the halves straddle the end of the window (13:00-24:00 UTC in daylight saving, 14:00-24:00 UTC otherwise), for up to 11 hours the flashcard page and the practice / daily session disagree by one day about which cards are due. Existing rows are not backfilled: cards now come due up to 11 hours earlier in daylight saving, 10 otherwise (at most one review day early), never later. The 9 live cards with `due_date = last_review` are all `relearning`: AGAIN on a review card schedules `review_date + 1 minute`, which on a `date` is the same day (intended same-day relearning).

## Exercise content hydration (ADR-049, TASK-1019; modes removed in TASK-1031)

Exercise content lives only in one immutable file per sense and version in the private Storage
bucket `exercise-content` ([[decisions/ADR-049-exercise-content-in-storage]]); `exercises.content`
was dropped on 2026-11-19. The session code reads it through `services/exercise_content/store.py`.
There are no read or write modes any more (TASK-1031 removed the `db` / `shadow` paths, the DB
fallback and the `EXERCISE_CONTENT_SOURCE` / `_WRITE` / `_DB_FALLBACK` / `_SHADOW_SAMPLE` flags).

- `_practice_session_rpc` and the `get_review_ahead_items` call pass `**store.rpc_content_args()`,
  which is always `{'p_include_content': False}`.
- `_inject_prestudy_followups` selects `store.select_columns('id, word_sense_id, exercise_type,
  {content}, ladder_level')` (`{content}` becomes `content_version`) and copies
  `content_version` onto the follow-up item.
- `SessionAssemblyMixin._hydrate_items(payload, language_id)` makes **one**
  `store.hydrate(payload['items'], language_id=…, id_key='exercise_id', sense_key='sense_id')`
  call per request, in `get_session` and in `get_extra_round` (`hydrate` takes no `db` since
  2026-11-19): after the floor, follow-ups, intro routing/filtering, `_order_items` and the
  `score_breakdown` strip, and immediately before `_apply_script_variant` and
  `_prepare_jumbled_items` (which rewrite content in place; hydrate hands every item a fresh
  object). DT error cards are injected afterwards and never hydrated; gate / stress markers have
  no `exercise_id` and pass through.
- An item whose content cannot be found (no file, a corrupt file, past the per-call cap or
  deadline) is dropped, order kept. When that empties a non-empty list:
  `no_content_reason = 'content_unavailable'` and one ERROR log. One INFO line
  `exercise content hydrated (lang=..): items= groups= cache_hits= fetched= over_cap= dropped=
  elapsed_ms=` when anything was fetched or dropped. An unexpected exception from `hydrate` (a
  contract breach) is logged and the items without content are dropped. Without
  `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` every item needing content is missing (one ERROR
  per process).
- The intro-drill block hydrates its own rows in `intro_drill.build_block` (≤ 40 senses), so a
  session request makes at most two hydrate calls. The speed round picks its ≤ 20 rows first and
  hydrates only those; gate/stress batteries (`LadderService._fetch_exercises_for_levels`) hydrate
  the sense's rows before picking by `tags.variant`.
- `POST /api/practice/attempt`: the server-side `cloze_typed` re-grade (`_grade_typed_if_needed`)
  selects `'exercise_type, {content}, language_id, word_sense_id'` and hydrates with
  `drop_missing=False`; missing content keeps the client's verdict (fails open, as a failed
  lookup did).

## Post-RPC error-card injection (Dual Translation, TASK-618)

After `get_practice_session` returns, `PracticeSessionService.get_session` interleaves due
Dual-Translation error-remediation cards into `payload['items']` as a **separate, non-sense-linked
stream** — they never pass through the RPC's sense-keyed candidate pools or the `sense_id IS NOT
NULL` filter (decision 6 above). This keeps remediation in the flow of normal practice without
Study-Plan orchestration.

- **Selector:** `services/dual_translation/cards.py::select_error_exercises_for_practice(db,
  user_id, *, language_id, normal_item_count, max_cards=None, fraction=None)`. Materialises due
  cards first (idempotent `generate_cards_for_queued_entries`), fetches due `dt_card` rows
  (`due_date ≤ today OR state='new'`) **scoped to the session L2** (`dt_card` has no language
  column → scope via `profile_entry_id → dt_error_profile_entry.l2_language_id`), and round-robins
  them through the existing `interleave_by_subtype`.
- **Cap (does not crowd out normal practice):** `min(available_due, max_cards,
  ceil(fraction × normal_item_count))`. Env knobs `DT_PRACTICE_ERROR_CARD_MAX` (default 3) and
  `DT_PRACTICE_ERROR_CARD_FRACTION` (default 0.34), read straight from the environment to match
  `DT_ERROR_CARD_INTERLEAVE_EVERY`. With `normal_item_count = 0` the fraction cap is 0, so an empty
  practice session stays empty — `GET /api/dual-translation/next` remains the surface for a due
  queue with no accompanying practice.
- **Placement:** `PracticeSessionService._interleave_extras` spreads the capped items evenly
  through the normal items (never clumped at the tail; the session still opens on a normal item).
- **Item shape:** `{ id: "dt-error-<card_id>", exercise_type: "dt_error_card", type: "error_card",
  is_error_exercise: true, word_sense_id: null, card_id, card_type, subtype, prompt_payload,
  state, due_date }`. Graded via the existing `POST /api/dual-translation/cards/<id>/review`
  (FSRS state lives on `dt_card`), **not** `POST /api/practice/attempt`. The payload also gains
  `error_cards_injected: <n>` when any were injected.
- **Best-effort:** the whole injection is wrapped so a remediation failure is logged and never
  breaks the practice session.
- **FE (deferred):** the v1 practice player (`static/js/session/players/practice.js`) and the
  legacy `get_or_create_daily_session` shape both **skip** `is_error_exercise` items exactly as
  they skip gate / stress-test markers, so nothing renders broken. Wiring the cloze /
  isolate-retranslate renderer into the practice player is the tracked follow-up; the cards ride
  in the payload regardless.

## Parity test (R4.7) — historical

The merger's one-off parity test (an integration test file named for the practice merger parity check, which compared the Jaccard overlap of `get_ladder_session` / `get_exercise_session` with `get_practice_session` over 50 staging users in four cohorts) was run once at the merge. The test file and both legacy RPCs no longer exist (the RPCs were dropped live 2026-11-17), so the check cannot be re-run. Pass rule used: median Jaccard >= 0.70 and minimum >= 0.50. The CSV reports, if kept, are under `wiki/raw/parity_reports/`.

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
- **Unit**: auto-mode dispatch lives inside the RPC (see "Mode resolution"); there is no Python `auto_mode_dispatch`.
- **Integration**: the one-off parity test is historical (see above).
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
- [[features/practice-package]] and [[features/practice-package.tech]] — Module map of `services/practice/`.
- [[features/study-session-package.tech]] — How the daily session calls the engine.
- [[features/new-word-drill.tech]] — Admission queues and the drill.
- [[database/schema.tech]] — Schema changes.
- [[database/rpcs.tech]] — Full RPC signatures.
- [[decisions/ADR-007-merge-exercises-vocab-dojo]], [[decisions/ADR-012-grammar-items-excluded-v1]].
