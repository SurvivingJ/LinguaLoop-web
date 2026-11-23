---
title: "ADR-053: Growth comes from daily per-learner, per-language snapshots that store the estimator's inputs"
status: proposed
date: 2026-11-17
---

# ADR-053: Growth comes from daily per-learner, per-language snapshots that store the estimator's inputs

## Context
The owner wants growth over 30 and 90 days. No table stores `p_known` or status over time, and replay
is impossible: five of the seven writers log nothing per word, only 203 of 906 exercise attempts
carry `p_known_after`, and question→sense links have changed since attempts were taken. The database
is at 513,526,931 B against a 500 MB Free cap; a per-sense daily snapshot would cost ~37 MB a year
at today's size.

The challenge stage found three traps in a plain "estimate then vs now" design
([[features/knowledge-report.tech]] Appendix A, S6 and P9):
- The windowed estimate is a lagging average: for de6fd05b, 177 of 178 answers in today's 180-day
  window were already in the window 30 days ago, so a difference mostly reflects window composition.
- The denominator moves without learning: zh banded lemmas went from 3,952 to 12,790 in a month,
  and the check's pool is refreshed by hand.
- "Words practised" based on `last_evidence_at` counts words that only appeared in a text, and the
  "rated known" count moves with reading tests.

## Decision
1. New table `user_knowledge_snapshots`, PK `(user_id, language_id, snapshot_date)`, ~25 fixed columns:
   measured counts (tracked, rated known, checked, missed recently, not seen 60+ days, practised and
   direct checks in 30 days), the estimator **inputs** (definition language, per-band n/s/c as
   `smallint[21]`, frame sizes as `int[7]`, answer count, first and last answer time) and outputs
   (kind, lo, hi, label), `method_version`; ~300 B a row (measured composite 256 B); RLS on, service
   role only.
2. A nightly APScheduler job at 04:25 UTC writes one row per active pair, every day, by idempotent
   upsert, using the same summary RPC and estimator as the page; then prunes to daily for 120 days and
   Mondays after that. The job ships **before** the page.
3. History-free figures come from timestamped logs: words practised and direct checks (first-try
   exercise and word-quiz outcomes) and, separately, words met in texts (no direct check).
4. From snapshots: the **change in words rated known after a direct check**, always shown with the
   number of direct checks in the period ("No direct checks in this period. Any change comes from your
   reading tests." when it is 0); never "learned" or "forgot".
5. An **estimate comparison** is shown only when "then" (recomputed from the stored inputs on today's
   frame) and "now" (answers after the anchor's last answer — disjoint by construction) each pass the
   estimate gates; "No clear change" when |Δ| < 1.96·sqrt(SD_then² + SD_now²). A pool change of more
   than 5% is announced.
6. `snapshot_date` is the UTC date; no back-fill; deltas need an anchor at least 14 days old and the
   same `method_version`.

## Consequences
- Easier: growth is cheap to read, consistent with the live page, and honest about what moved it.
  Size ≈ 0.23 MB in year one at today's 5 pairs, ≈ 2.3 MB at 50 pairs, ≈ 46 MB at 1,000 pairs (ESTIMATE).
- Harder: nothing before the first run; estimate comparisons need a learner to retake the check;
  rule changes need a `method_version` bump that suppresses deltas across versions.
- Constrained: no per-word "learned on" dates; a future evidence log (TASK-1065) would be needed.

## Alternatives Considered
- **Replay from logs:** impossible (above).
- **Per-sense daily snapshots:** ~37 MB a year now; unaffordable under the cap.
- **Store only lo/hi/total:** cannot recompute "then" on today's pool or test disjointness.
- **pg_cron:** available but not installed; needs `CREATE EXTENSION` and its run log must be purged.
- **Weekly snapshots only:** 7× smaller but 30-day deltas would rest on 4 points.
- **One-time back-fill of D-30/D-90 anchors:** helps one human learner and guesses 112 rows.
