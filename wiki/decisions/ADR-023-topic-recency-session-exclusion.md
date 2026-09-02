---
title: "ADR-023: Per-user topic-recency exclusion in get_recommended_tests"
status: accepted
date: 2026-08-30
---

# ADR-023: Per-user topic-recency exclusion in get_recommended_tests

## Context

TASK-740 Phase 5 (finding #3, 2026-08-29 review): a learner can be served
multiple tests that are all built on the same or a near-duplicate topic
within a short span, because the session-hydration path only excludes tests
the user has already **attempted** (`get_recommended_tests`'s
`NOT EXISTS ... test_attempts` clause) — it has no concept of "topic seen
recently." Phase 5's generation-time dedup (`services/test_generation/dedup.py`,
`migrations/task740_phase5_question_passage_dedup.sql`) stops near-duplicate
*passages* from being generated in the first place, but does nothing about a
learner being served two *different, legitimately distinct* tests on the same
topic close together (e.g. a topic that has fanned out to its
`max_tests_per_topic` cap over time, per Phase 4).

Confirmed decision Q5: dedup covers both generation-time AND per-user
recency. This ADR is the per-user recency half.

`build_daily_session` (the live session builder, `phase13_build_daily_session.sql`)
sources its "new" test slots from `get_recommended_tests`
(`migrations/task715_get_recommended_tests_tier_cap.sql`, called via
`services/test_service.py:712` for the legacy daily-load path, and
internally by the `build_daily_session` SQL for the Study Plan resolver
path). **Both are live functions already serving production traffic.**

## Decision

Add a topic-recency exclusion to `get_recommended_tests`: a candidate test is
excluded if the user has attempted *any* test on the same `topic_id` within a
configurable recency window (proposed default 14 days — half the
`topic_recency_window_days` generation-side cap, since this window governs
how repetitive a session *feels*, not how fast content is allowed to be
regenerated).

Concretely: add `p_topic_recency_days smallint DEFAULT 14` to
`get_recommended_tests`'s signature (backward compatible — existing callers
that don't pass it keep working unchanged) and extend the `all_candidates`
CTE's `WHERE` with:

```sql
AND NOT EXISTS (
    SELECT 1 FROM test_attempts ta2
    JOIN tests t2 ON t2.id = ta2.test_id
    WHERE ta2.user_id = p_user_id
      AND t2.topic_id = t.topic_id
      AND ta2.created_at >= now() - (p_topic_recency_days || ' days')::interval
)
```

Applied in `migrations/task740_phase5b_topic_recency_exclusion.sql`, with
explicit operator sign-off, 2026-08-30. Verified live in a rollback-only
transaction (`tests/sql/test_task740_phase5b_topic_recency.sql`) before and
after applying: a test sharing a topic with a just-attempted test is
excluded; an unrelated-topic test is retained. The superseded prior
definition was archived per `migrations/CLAUDE.md` to
`migrations/archive/task715_get_recommended_tests_tier_cap.sql`.

## Consequences

- What becomes easier: sessions stop repeating the same topic across
  consecutive days even after `test_attempts`-based dedup is exhausted for a
  topic's current test pool.
- What becomes harder / risk: a topic with very few tests at a tier (thin
  content, see `webapp-content-inventory-2026-08` memory — ja has 0
  exercises/word_assets in some areas) could see its whole pool excluded for
  the recency window, worsening an existing hydration-shortfall class
  (`resolver-hydration-skill-gap`). The shortfall-surfacing machinery
  (TASK-702) already logs this as `hydrated < requested`, so a regression
  would be visible, not silent — but it is a real cost worth weighing before
  applying.
- The window (14 days) is a starting guess, not a measured value — no gold
  data exists yet on how repetitive a topic has to feel before it hurts
  retention. Treat it as adjustable.

## Alternatives Considered

- **Filter in Python after the RPC call** (`services/test_service.py`,
  post-processing `recommended` before building `load_items`): avoids
  touching a live RPC's body. Rejected as the primary mechanism because
  `build_daily_session`'s Study Plan resolver path — the actually-live path
  per `STUDY_PLAN_ENABLED` — does its own hydration entirely in SQL and never
  round-trips through this Python function; a Python-side filter would only
  cover the legacy `_compute_daily_load` fallback path, leaving the primary
  path unfixed.
- **New, additive RPC** (`get_recommended_tests_v2` or similar) that both
  callers switch to: avoids a `CREATE OR REPLACE` on the live function, but
  leaves two near-identical candidate-selection queries to keep in sync
  indefinitely, which is the exact drift `migrations/CLAUDE.md` warns about.
  Rejected in favor of one function, redefined, once approved.
- **Exclude by test_id repetition only** (already the status quo): rejected
  — it is precisely the gap this ADR closes.
