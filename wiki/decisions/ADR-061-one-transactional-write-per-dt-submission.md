---
title: "ADR-061: One transactional write per Dual Translation submission"
status: proposed
date: 2026-11-23
---

# ADR-061: One transactional write per Dual Translation submission

**Proposal. Not decided. This needs the owner's decision; nothing described under "Decision" has been built.**

## Context

A graded Dual Translation (DT) submission is saved by several separate statements with no transaction
([[features/dual-translation.tech]], "Submit flow and duplicate submits"):

1. update `dt_submission` (the reproduction);
2. insert the `dt_error_instance` rows;
3. insert `dt_grade` (UNIQUE `submission_id`), deliberately **last** so that a failed error insert leaves no grade and the retry re-grades (ADR-019, TASK-633);
4. insert the `dt_grading_call` rows (best-effort);
5. create the repair session (`dt_repair_session`, UNIQUE `submission_id`), then insert its items (`dt_repair_item`) in a second statement.

Correctness therefore depends on statement order, on the browser's double-click guard and, since 2026-11-23, on two pieces of application code:

- a per-submission lock held **inside one process** (`_SubmissionLock`, 90 s wait);
- cleanup-on-conflict: when the `dt_grade` insert loses a race, the loser deletes only the error rows it inserted (`_discard_error_rows`) and returns the stored grade.

Known gaps that remain:

- `Procfile` runs `gunicorn ... --workers 2 --worker-class gthread --threads 8`. A double submit that lands on the other worker is not covered by the in-process lock: both grade, and the grader (a paid or rate-limited model call) is paid twice. The loser's rows are cleaned up afterwards.
- A failed items insert leaves a repair session with no items. This needs self-healing: the next cached submit rebuilds the items (`hooks._recreate_items`, re-planned with the current planner under the old session's status), or serves the full grade.
- A losing duplicate submit overwrites `dt_submission.reproduction` and `idempotency_key` before its grade insert fails (pre-existing), leaving the row with the loser's text beside the winner's grade.
- `dt_repair_item` has no unique constraint (checked live 2026-11-23: primary key only), so two cached re-submits on a session with no items, on different workers, could insert the items twice.
- Failure modes are handled in several places (persist order, the lock, the cleanup, the rebuild), each with its own tests; a new write added later has to remember all of them.

## Decision (proposed)

Write a graded submission with **one SQL function** (a Postgres RPC, for example `dt_save_graded_submission`), called once by `submit()` after grading:

- it takes a **per-submission advisory lock** (`pg_advisory_xact_lock` on the submission id), so concurrent submits of the same submission serialise across all workers and hosts;
- inside that lock and one transaction it checks whether a `dt_grade` already exists and, if so, returns the stored grade (and its repair payload inputs) without writing;
- otherwise it writes the reproduction, the `dt_error_instance` rows, the `dt_grade`, the repair session and its items atomically, and returns what `_cached_grade` returns today;
- `dt_grading_call` rows may stay a separate best-effort write (they are an audit log, also written when no grade is saved).

Afterwards remove the in-process lock, `_discard_error_rows`, the loser-handling branch in `submit()` and the item-less-session rebuild, and keep the existing tests as characterisation tests of the function.

The grader call stays outside the transaction (it is slow); the second worker still waits at the lock **after** its own grading call, so a cross-worker duplicate still pays the grader twice unless the lock is taken (or a "grading in progress" mark is written) before grading. Whether to take it before grading (and hold a database connection for the length of a model call) or accept the duplicate cost is part of the owner's decision.

## Consequences

- Easier: a half-written submission cannot exist (no orphan error rows, no session without items); duplicate handling is one rule in one place and works across workers; the nightly synthesis, which reads `dt_error_instance` directly, cannot see rows of a grade that was not stored.
- Harder: a migration and an RPC with a large JSON argument to maintain in SQL, outside the Python test suite's reach unless a SQL test is added; the function has to reproduce the column handling of `_error_columns` (the optional asset columns and their 10-minute fallback), so the logic of "missing migration tolerance" moves or is dropped.
- Constrained: the grade-last ordering rule (ADR-019) becomes the transaction's job; any new table written per submission must be added to the function.

## Alternatives Considered

- **Keep as is** (in-process lock, cleanup-on-conflict, rebuild of item-less sessions). Cheapest, already written; leaves the cross-worker double grade and the possible duplicate items, and keeps the failure handling spread over several modules.
- **Unique constraints only** (for example a unique key on `dt_repair_item` by session and sentence, plus `ON CONFLICT DO NOTHING` inserts). Fixes the duplicate items but not orphan error rows or the double grading; the error rows would need their own key.
- **Single worker or sticky routing per submission.** Removes the cross-worker case without SQL, but constrains deployment and does not fix the partial-write cases.

## Related Pages
- [[features/dual-translation.tech]] — submit flow and the known limit
- [[features/dt-guided-self-repair.tech]] — session and item inserts, known issues
- [[decisions/ADR-045-dt-guided-self-repair]]
- [[decisions/ADR-062-retire-dt-card-and-select-next-window-in-sql]] — the companion proposal
- [[database/schema.tech]]
