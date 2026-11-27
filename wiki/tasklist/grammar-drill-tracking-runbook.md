---
title: "Grammar Drill Tracking — Apply Runbook and Owner Queries"
type: overview
status: in-progress
last_updated: 2026-11-27
---

# Grammar Drill Tracking — Apply Runbook and Owner Queries

For the owner. Covers the one pending migration that turns on progress tracking for the Chinese
grammar drills ([[features/grammar-drills]], [[decisions/ADR-066-grammar-drill-daily-tracking]],
TASK-1259) and the SQL to read the collected history. Nothing here has been applied.

## The space line

**The database stop line is 480 MB** (owner decision 2026-11-27: "Do daily with the current space
limit raised to 480mb"; it was 475 MB). The plan's cap is 500 MB. The database was 473.15 MB on
2026-11-24, so the headroom is 6.85 MB.

Measured cost (scratch PostgreSQL 16, 472,680 rows): **about 246 bytes per daily row** including
its primary key index (167 heap + 79 index), and 665 to 1,250 bytes per state row (one per
learner and topic, at most 39 per learner). 6.85 MB is about 29,000 daily rows: for example 10
learners practising 4 topics every day for two years. The original target of about 150 bytes per
row is the floor for this key with no sub-point data; the sub-point keys are the difference.

## Apply

1. Read the header of `migrations/grammar_drill_tracking.sql` and run its VERIFY BEFORE queries:
   the three objects are absent and the database is under 480 MB.
2. Apply `migrations/grammar_drill_tracking.sql` (one transaction; creates two empty tables and
   one function; changes nothing that exists).
3. Run its VERIFY AFTER queries and `tests/sql/check_function_acls.sql` (every result set empty).
4. No restart is needed. The application remembers "not deployed" for at most 10 minutes per
   worker; after that the two routes work. The code can be deployed before or after this step:
   until both are in place the page keeps progress in the browser and shows no charts.
5. Check: play one round at `/grammar-drill` while signed in, then run query 1 below
   (`daily_rows` at least 1) and reload the page (the hub shows "Your progress").

Rollback: `migrations/grammar_drill_tracking_rollback.sql` (drops the three objects; the
history is lost, the browsers keep their own progress).

## If the line gets close

In order of how much they free: delete daily rows older than a chosen date
(`DELETE FROM public.grammar_drill_daily WHERE practice_day < DATE '...'` then
`VACUUM public.grammar_drill_daily`; the page reads only the last 180 days); or roll back. Ask
before either: both are destructive.

## Owner queries

Read-only. Run them in the Supabase SQL editor. Day boundaries are the app's review day
(Australia/Sydney), as written by the route.

### 1. Table sizes against the 480 MB line

Run this first, and again after any busy week. `mb_left_to_480` must stay positive; `daily_size / daily_rows` should stay near 246 bytes.

```sql
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size,
       round(pg_database_size(current_database()) / 1048576.0, 2) AS database_mb,
       round(480 - pg_database_size(current_database()) / 1048576.0, 2) AS mb_left_to_480,
       pg_size_pretty(pg_total_relation_size('public.grammar_drill_daily')) AS daily_size,
       (SELECT count(*) FROM public.grammar_drill_daily) AS daily_rows,
       pg_size_pretty(pg_total_relation_size('public.grammar_drill_state')) AS state_size,
       (SELECT count(*) FROM public.grammar_drill_state) AS state_rows;
```

### 2. Accuracy and recall time by week, per learner and topic

Improvement over time: one row per learner, topic and week (weeks start on Monday). `avg_recall_s` is over right first answers only and is NULL for a week with none.

```sql
SELECT user_id, topic, date_trunc('week', practice_day)::date AS week,
       count(*) AS days_practised,
       sum(answers) AS answers,
       round(100.0 * sum(correct) / sum(answers), 1) AS accuracy_pct,
       round(sum(ms_sum) / NULLIF(sum(timed), 0) / 1000.0, 2) AS avg_recall_s,
       max(stage) AS stage
  FROM public.grammar_drill_daily
 WHERE language_id = 1
 GROUP BY user_id, topic, week
 ORDER BY user_id, topic, week;
```

### 3. Topics that stall

Learners who gave at least 200 answers on a topic in the last 30 days without opening a further stage and without being instant. Raise or lower the 200 as needed.

```sql
SELECT user_id, topic,
       sum(answers) AS answers_30d,
       count(*) AS days_30d,
       min(stage) AS stage_at_start, max(stage) AS stage_now,
       round(100.0 * sum(correct) / sum(answers), 1) AS accuracy_pct
  FROM public.grammar_drill_daily
 WHERE language_id = 1
   AND practice_day >= (now() AT TIME ZONE 'Australia/Sydney')::date - 29
 GROUP BY user_id, topic
HAVING sum(answers) >= 200 AND max(stage) = min(stage) AND NOT bool_or(instant)
 ORDER BY answers_30d DESC;
```

### 4. Time from first practice to instant

Per topic: how many learners reached instant, and how many days and answers it took from their first recorded day. Days before tracking was applied are not in the history, so early figures are a lower bound.

```sql
SELECT topic,
       count(*) AS learners_instant,
       round(avg(first_instant - first_day), 1) AS avg_days_to_instant,
       min(first_instant - first_day) AS fastest_days,
       max(first_instant - first_day) AS slowest_days,
       round(avg(answers_to_instant)) AS avg_answers_to_instant
  FROM (SELECT d.user_id, d.topic,
               min(d.practice_day) AS first_day,
               min(d.practice_day) FILTER (WHERE d.instant) AS first_instant,
               (SELECT sum(x.answers) FROM public.grammar_drill_daily x
                 WHERE x.user_id = d.user_id AND x.language_id = d.language_id
                   AND x.topic = d.topic
                   AND x.practice_day <= min(d.practice_day) FILTER (WHERE d.instant)
               ) AS answers_to_instant
          FROM public.grammar_drill_daily d
         WHERE d.language_id = 1
         GROUP BY d.user_id, d.language_id, d.topic) t
 WHERE first_instant IS NOT NULL
 GROUP BY topic
 ORDER BY avg_days_to_instant DESC;
```

### 5. Most-missed sub-points across learners

Last 90 days. Sub-point keys are the `subs[].key` values of the topic guide (`static/data/grammar/zh/manifest.json`). A sub-point that dominates its topic's misses is a candidate for more items or a clearer guide rule.

```sql
SELECT d.topic, m.key AS sub_point,
       sum(m.value::integer) AS misses,
       count(DISTINCT d.user_id) AS learners,
       round(100.0 * sum(m.value::integer) / sum(sum(m.value::integer)) OVER (PARTITION BY d.topic), 1)
         AS pct_of_topic_misses
  FROM public.grammar_drill_daily d
 CROSS JOIN LATERAL jsonb_each_text(d.sub_misses) AS m(key, value)
 WHERE d.language_id = 1
   AND d.practice_day >= (now() AT TIME ZONE 'Australia/Sydney')::date - 89
 GROUP BY d.topic, m.key
 ORDER BY misses DESC
;
```

## Related Pages

- [[features/grammar-drills]], [[features/grammar-drills.tech]]
- [[decisions/ADR-066-grammar-drill-daily-tracking]]
- [[tasklist/grammar-drills.tasks]] — TASK-1259
- [[tasklist/report-and-placement-apply-runbook]] — the earlier apply runbook and the database-size history
- [[database/schema.tech]] — the two tables
