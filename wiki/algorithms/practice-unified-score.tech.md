---
title: Practice Unified Score — Technical Specification
type: algorithm-tech
status: planned
prose_page: ./practice-unified-score.md
last_updated: 2026-05-21
dependencies:
  - "exercises.irt_difficulty, irt_discrimination columns"
  - "user_vocabulary_knowledge.p_known"
  - "user_flashcards.due_date, stability"
  - "user_word_ladder (ladder_compute_priority)"
  - "dim_practice_modes.default_weights jsonb"
  - "dim_exercise_types (family + expected_seconds)"
breaking_change_risk: low
---

# Practice Unified Score — Technical Specification

## Formula

```
score(item, user) = α · ladder_priority(item.sense, user)
                  + β · irt_information(item, θ_user)
                  + γ · bkt_uncertainty(item.sense, user)
                  + δ · fsrs_urgency(item.sense, user)
```

All four terms normalize to `[0, 1]`.

## Normalization

### Ladder priority

Reuse the existing `get_ladder_session` priority formula:

```
ladder_priority = 0.35·overdue + 0.25·weakness + 0.20·gate_urgency
                + 0.10·novelty + 0.10·relapse
```

This is bounded `[0, ~1.05]` in practice. We defensively clamp:

```sql
norm_ladder = GREATEST(0, LEAST(1, ladder_priority))
```

The clamp's upper edge clips at most a handful of edge cases (gated + maximally overdue + relapsing); ordering of the top-K is unaffected.

If a candidate has no `user_word_ladder` row (e.g. unsubscribed sense), `ladder_priority = 0`.

### IRT information

For 2PL IRT: Fisher information at θ is `I(θ) = a² · P(θ) · (1 − P(θ))`, with maximum `0.25 · a²` at `b = θ`. Items with `a > 1` can saturate beyond `0.25`; cap at 1.0:

```sql
WITH p AS (SELECT 1.0 / (1.0 + exp(-a * (theta - b))) AS p_theta)
SELECT LEAST(1.0, (a*a) * p_theta * (1.0 - p_theta) / 0.25) AS norm_irt FROM p
```

| Scenario | Value |
|---|---|
| `a = 1.0`, `b = θ` (peak) | 1.00 |
| `a = 1.5`, `b = θ` (capped) | 1.00 |
| `a = 1.0`, `|b − θ| = 1` | 0.42 |
| `a = 1.0`, `|b − θ| = 2` | 0.07 |
| Uncalibrated (`irt_n_attempts < 20`) | Use defaults `a=1.0, b=0.0` |

### BKT uncertainty

```
norm_bkt = 1 − 2 · |p_known − 0.5|
```

Bounded `[0, 1]` for `p_known ∈ [0, 1]`. Peaks at `p_known = 0.5`. For senses with no `user_vocabulary_knowledge` row, treat `p_known = 0.5` (maximum uncertainty).

### FSRS urgency

```
days_overdue = (today − due_date)        -- integer, may be negative
x            = clamp(-2, days_overdue / max(stability, 1), +4)
norm_fsrs    = 1 / (1 + exp(-x))
```

| Days overdue, S=7 | x | norm_fsrs |
|---|---|---|
| −7 (one stability early) | −1.00 | 0.27 |
| 0 (due today) | 0.00 | 0.50 |
| 3 | 0.43 | 0.61 |
| 7 (one stability past) | 1.00 | 0.73 |
| 14 | 2.00 | 0.88 |
| 28 (clipped) | 4.00 | 0.98 |

For senses with no `user_flashcards` row, `norm_fsrs = 0`.

## SQL helper

```sql
CREATE OR REPLACE FUNCTION public.practice_unified_score(
    p_a numeric, p_b numeric, p_theta numeric,
    p_p_known numeric,
    p_due_date date, p_stability real, p_today date,
    p_ladder_priority numeric,
    p_alpha numeric, p_beta numeric, p_gamma numeric, p_delta numeric
) RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
  SELECT
      p_alpha * GREATEST(0, LEAST(1, COALESCE(p_ladder_priority, 0)))
    + p_beta  * LEAST(1.0,
                  (p_a * p_a)
                  * (1.0 / (1.0 + exp(-p_a * (p_theta - p_b))))
                  * (1.0 - 1.0 / (1.0 + exp(-p_a * (p_theta - p_b))))
                  / 0.25)
    + p_gamma * (1 - 2 * abs(COALESCE(p_p_known, 0.5) - 0.5))
    + p_delta * (
        CASE
          WHEN p_due_date IS NULL OR p_stability IS NULL THEN 0
          ELSE 1.0 / (1.0 + exp(-LEAST(4.0, GREATEST(-2.0,
            (p_today - p_due_date)::numeric / GREATEST(p_stability, 1)
          ))))
        END
      )
$$;
```

## Mode weights

```
dim_practice_modes rows:
  ('acquisition', {alpha:0.40, beta:0.30, gamma:0.25, delta:0.05})
  ('maintenance', {alpha:0.05, beta:0.15, gamma:0.30, delta:0.50})
  ('auto',        null)                            -- dispatcher only
```

Weights are loaded once per session call and passed as constants to the SQL helper — no per-row jsonb lookup.

## Candidate pools per mode

See [[features/practice-engine.tech]] for the full pool SQL.

| Mode | Pool definition | Pre-rank | Final rank |
|---|---|---|---|
| Acquisition | Items whose `sense_id` matches an ladder-active word (`word_state IN ('active','gated','pre_mastery','relearning')`) AND whose `exercise_type → family` matches the word's current ring's required families | Word picked by `ladder_priority DESC`, top 50 words | Per family, top item by unified score |
| Maintenance | Items whose `sense_id` is FSRS-due (`due_date ≤ today + 7d`) OR BKT-decayed (`effective_p_known < raw − 0.05`); ALL must have `sense_id IS NOT NULL` (per [[decisions/ADR-012-grammar-items-excluded-v1]]) | `urgency_proxy = days_overdue / stability`, top 200 senses | Unified score across all candidates |

## Mode dispatch (auto)

```
due_today    = COUNT(user_flashcards WHERE due_date ≤ today)
decayed      = COUNT(senses with effective_p_known < raw − 0.05)
active_ladder = COUNT(user_word_ladder WHERE word_state IN
                  ('active','gated','pre_mastery','relearning'))

mode = 'maintenance' if (due_today + decayed) ≥ active_ladder
     else 'acquisition'
```

When the Study Plan is active, `daily_session_targets` carries explicit `practice_maintenance_min` and `practice_acquisition_min`. The session handler picks the mode whose minutes are positive (or whichever the caller explicitly requests); auto-dispatch is the fallback when neither caller nor plan specify a mode.

## Mid-session fall-through

If `mode='maintenance'` and the pool empties before `target_minutes·60` seconds of `expected_seconds` accumulate, the session continues in Acquisition for the remaining minutes. Each item carries its `mode` in the response so the UI can render a section break.

```python
if mode == 'maintenance':
    items, elapsed = drain_maintenance_pool(target_seconds)
    if elapsed < target_seconds:
        remaining_min = (target_seconds - elapsed) / 60
        more_items, _ = acquisition_session(user, language, remaining_min, theta)
        items.extend(more_items)
return items
```

Acquisition does *not* fall through to Maintenance (a learner who asked for Acquisition gets either Acquisition items or an `no_content_reason` flag).

## Cold-start handling

- **Cold IRT (`irt_n_attempts < 20`):** Use defaults `a = 1.0, b = 0.0` from the existing IRT calibration default. The IRT term still computes but is less informative — that's correct behavior pre-calibration.
- **Cold BKT (no `user_vocabulary_knowledge` row):** Treat `p_known = 0.5` → `norm_bkt = 1.0`. Newly-encountered senses score high on uncertainty.
- **Cold FSRS (no `user_flashcards` row):** `norm_fsrs = 0`. The sense can't be in the Maintenance pool by definition; in Acquisition the term is just zero-weighted.
- **Cold ladder (no `user_word_ladder` row):** `norm_ladder = 0`. Used only as a defensive default; the candidate pool already filters to ladder-active words in Acquisition mode.

## Performance

- `practice_unified_score` is `IMMUTABLE` — the planner can hoist constants and inline.
- Hard cap of 200 candidates in Maintenance and ~50 words × ≤6 families ≈ 300 evaluations in Acquisition → < 500 score evals per session.
- Indices required: `user_flashcards (user_id, language_id, due_date)`, `user_vocabulary_knowledge (user_id, language_id)`, `user_word_ladder (user_id, language_id, word_state)`, `exercises (sense_id, language_id) WHERE sense_id IS NOT NULL`. Verify with `EXPLAIN ANALYZE` in staging.

## Verification

- **Unit:** Hand-computed values for the four corner cases (peak IRT, peak BKT, far-overdue FSRS, gated ladder word) match the SQL helper output to 4 decimals.
- **Property:** For any inputs, `practice_unified_score ∈ [0, α + β + γ + δ]`. Since `α + β + γ + δ = 1.0` in both seeded modes, score ∈ `[0, 1]`.
- **Integration:** Run `get_practice_session('acquisition', 12)` with seeded inputs; verify top item's score matches manual computation.

## Related Pages

- [[algorithms/practice-unified-score]] — Prose counterpart.
- [[features/practice-engine.tech]] — Where the score is invoked.
- [[algorithms/vocabulary-ladder.tech]] — Source of ladder_priority subscores.
- [[features/vocabulary-knowledge.tech]] — BKT formula.
- [[features/flashcards.tech]] — FSRS state.
- [[features/exercises.tech]] — IRT calibration (deprecated for the prose redirect; the `exercises` table itself is still canonical).
- [[decisions/ADR-007-merge-exercises-vocab-dojo]], [[decisions/ADR-012-grammar-items-excluded-v1]].
