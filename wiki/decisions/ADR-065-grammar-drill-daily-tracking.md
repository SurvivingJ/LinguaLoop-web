---
title: "ADR-065: Grammar drill progress on the server as daily summaries plus one state row"
status: accepted
date: 2026-11-27
---

# ADR-065: Grammar drill progress on the server as daily summaries plus one state row

## Context

[[decisions/ADR-064-grammar-drills-static-content-local-progress]] kept grammar-drill progress in
one browser's `localStorage`, explicitly as a provisional choice, because the database was at
473.15 MB against the owner's 475 MB stop line. Two things follow from that choice: the server
knows nothing about a learner's practice, and progress does not follow the learner to another
device.

On 2026-11-27 the owner asked: "do you think we could add tracking in? so we can know the user's
improvement over time?" and, given the options (per answer, per round, per day), decided:
"Do daily with the current space limit raised to 480mb".

## Decision

1. **The database stop line is 480 MB** (was 475 MB). The plan's cap of 500 MB is unchanged.
2. **One summary row per learner, topic and practice day** (`grammar_drill_daily`): first-answer
   counts (`answers`, `correct`), recall time (`timed`, `ms_sum`: right first answers and the sum
   of their recall times, each capped at 30 s), the highest stage unlocked, whether the topic was
   instant, and misses per sub-point. **No row per answer and no row per item.**
3. **One state row per learner and topic** (`grammar_drill_state`): the highest unlocked stage,
   the last 30 results per stage, and totals, so progress follows the learner. The per-item review
   boxes stay in the browser.
4. **One function writes both** (`record_grammar_drill_round`), idempotent on a round key the
   browser generates. The browser queues finished rounds in `localStorage` and resends them until
   the server has taken them (at least once from the browser, once in the database).
5. **The practice day is the app's review day** (`services/day_boundary.review_today`, zone
   Australia/Sydney, [[decisions/ADR-022-local-day-boundary]] and TASK-1211), computed in Python
   and passed to the function.
6. **The browser stays the working copy.** `localStorage` is still read and written on every
   answer; the server is written once per finished session and read once per page load. When the
   server is unreachable, the learner is signed out, or the migration is not applied, the page
   behaves exactly as under ADR-064 and shows no error.
7. Point 3 of ADR-064 ("learner progress is kept in `localStorage`", provisional) is superseded
   by this record. Its other points (static content, browser-side generators, answers checked in
   the browser) stand.

Specification: [[features/grammar-drills.tech]] "Progress tracking". Apply steps and owner
queries: [[tasklist/grammar-drill-tracking-runbook]].

## Consequences

**Easier**

- Improvement over time can be read per learner and topic (accuracy and recall time by day),
  stalled topics and hard sub-points can be found across learners, and the learner sees the same
  on the topic screen and the hub.
- Stages and totals follow the account to another device or a cleared browser.
- Writes are one small call per finished round, not one per answer.

**Harder or now constrained**

- **Space.** Measured about 246 bytes per daily row with its index (167 heap + 79 index) and 665
  to 1,250 bytes per state row. The 6.85 MB of headroom on 2026-11-24 is about 29,000 daily rows.
  The table sizes must be watched against the 480 MB line (first query of the runbook). The
  budget of about 150 bytes per daily row was not met: 150 is the floor for this primary key
  with no sub-point data.
- **Resolution is one day.** Within-day order, per-item history and single answers are not kept
  and cannot be reconstructed.
- **A new migration must be applied live** before anything is recorded (pending:
  `migrations/PENDING-2026-11-27.md`).
- **The counts are the browser's.** The server checks ranges and that topics and sub-points
  exist; it cannot check that the answers were given. Acceptable for self-study drills with no
  stakes (same reasoning as ADR-064); it would not be for anything scored or ranked.
- **Idempotency remembers one key per state row.** A resend that arrives after another device
  wrote the same topic in between is counted twice. Accepted for a summary.
- **History starts at apply time.** Progress made before is uploaded once as state only; no daily
  rows are invented for it.
- The item review boxes are still per browser: a new device knows the stage but treats every item
  as unseen.

## Alternatives Considered

1. **One row per answer.** The most detail; rejected on space (a 20-item round would write 20
   rows of about 100 bytes plus index, against 1 here).
2. **One row per round.** Keeps within-day order; rejected by the owner's choice of daily: several
   times the rows of the daily design for a learner who plays several rounds a day.
3. **One JSON value per user and language holding everything** (the earlier TASK-1239 sketch).
   Gives sync but no history over time, which is what the owner asked for.
4. **Per-item boxes on the server too.** Up to 10,209 entries per learner; rejected on space.
5. **Sub-point misses keyed by position instead of key.** Would save about 30 bytes a row but
   breaks when a guide's sub-points are reordered; rejected, noted as the first thing to revisit
   if space gets tight.
6. **Computing the day in SQL with `review_today()`.** That function is itself in a pending
   migration; the day is computed in Python so this file does not depend on it.

## Related

- [[decisions/ADR-064-grammar-drills-static-content-local-progress]] — point 3 superseded here
- [[features/grammar-drills]], [[features/grammar-drills.tech]]
- [[tasklist/grammar-drills.tasks]] — TASK-1239
- [[tasklist/grammar-drill-tracking-runbook]]
- [[database/schema.tech]], [[api/rpcs.tech]]
