---
title: "ADR-046: LLM call logs are archived to Supabase Storage; the database keeps a short window"
status: accepted
date: 2026-11-15
---

# ADR-046: LLM call logs are archived to Supabase Storage; the database keeps a short window

## Context
On 2026-11-15 the database was 526 MB, over the 500 MB limit. `llm_calls` was 54 MB
(20 MB of rows, 33 MB of indexes, 76,828 rows) and grows with every generation or judge
run: one ladder judge run on 2026-11-01..12 wrote ~52k rows. 75% of its rows (57,604)
were the verdict-only second row that `log_judge_verdict()` writes per judge call.
Nothing in the app reads `llm_calls`. Its readers are scripts: budget ceilings and
batch reports that read rows from the run in progress, and eval/measurement scripts.
The owner asked for the logs to be moved to a Supabase Storage bucket.

## Decision
- Old `llm_calls` rows are moved, not purged: `scripts/archive_llm_calls.py` exports
  every column of the rows older than a cutoff to gzipped JSON Lines, uploads them with a
  manifest to the private bucket `llm-logs-archive` (prefix `llm_calls/`), downloads the
  object back and checks sha256, row count and id set, and only then (with `--delete`)
  deletes exactly the exported ids. `VACUUM (FULL, ANALYZE) public.llm_calls` returns
  the space.
- The database keeps the current day's rows (default cutoff: 00:00 UTC on the day of
  the run), enough for in-flight budget ceilings and batch reports.
- First run 2026-11-15: 75,163 rows (2026-09-21 21:23 → 2026-11-14 14:46 UTC), 6.3 MB
  gzipped, object
  `llm_calls/llm_calls_20260921T212355_to_20261114T144607__cutoff_20261115T000000.jsonl.gz`,
  sha256 `10689fecdead5b61d5e567ada8a32479d653dfdee8dae790986fd1fd321dae6a`.
  `llm_calls` 54 MB → 1.5 MB; database 526 → 473 MB.

## Consequences
- The database stops paying for log history; Storage holds it at ~1/8 the size.
- Historical analysis (judge flag rates, cost over weeks) must read the archive files,
  not SQL. Scripts that query `llm_calls` across past runs (`measure_judge_flag_rate.py`,
  `run_exercise_gen_eval.py` over old runs, etc.) see only rows since the last archive.
- The table regrows until the script is run again. It is not scheduled; run it after
  large generation batches, or schedule it.
- Not changed: the verdict-only second row per judge call. Folding the verdict onto the
  raw-call row would cut new log volume by roughly three quarters; that is a code change
  in `services/exercise_generation/judges/base.py` and its readers, not done here.

## Alternatives Considered
- **`purge_old_log_rows()`** (`migrations/log_retention_purge.sql`, not applied): nulls
  `raw_response` by age. Rejected for this problem: `raw_response` was only 8 MB of the
  54 MB, and 68% of rows were under 7 days old, below its minimum age.
- **Dropping redundant `llm_calls` indexes only:** would save ~20 MB and keep the rows,
  but the rows keep growing; moving the rows also removes the index cost.
- **A file in the repo** (as on 2026-09-21, `archive/db_backups/*.zip`): rejected by the
  owner in favour of a Storage bucket; large binary logs do not belong in git.
