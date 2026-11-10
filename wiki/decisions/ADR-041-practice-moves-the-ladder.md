---
title: "ADR-041: Practice attempts move the ladder; checkpoints run in the Practice player"
status: accepted
date: 2026-11-10
---

# ADR-041: Practice attempts move the ladder; checkpoints run in the Practice player

## Context

[[features/practice-engine.tech]] says a sense-linked Practice attempt calls
`ladder_record_attempt`. It never did: since Vocab Dojo was retired (TASK-220, 2026-07-14) the
only caller of `ladder_record_attempt` was the unused `/api/vocab-dojo/attempt` route, and the
Practice player dropped gate and stress-test markers. Live on 2026-11-10: all 120 ladder words
of all learners were on ring 1; no word had ever moved a ring, passed a gate or been mastered.
The new-word drill ([[decisions/ADR-040-criterion-based-new-word-drill]]) hands graduates to
ring 2, so they would have stayed there forever.

`ladder_record_attempt` also inserts the attempt row, updates overall BKT and rates FSRS, all
of which the Practice attempt path already does, so calling it as-is would double-count.

## Decision

1. New SQL function `ladder_apply_progress` (`migrations/ladder_apply_progress.sql`):
   `ladder_record_attempt` minus the attempt insert, the overall BKT update and the lapse-path
   FSRS rating; it never creates a ladder row, skips words not on the ladder and words in the
   drill, and acts on first attempts only. Family confidence, the cross-session gate, ring
   clearing, gates, demotion, lapse → relearning and the lapse BKT penalty are unchanged.
2. `PracticeSessionService.record_attempt_with_updates` calls it for every sense-linked
   attempt, after BKT and FSRS. `POST /api/practice/attempt` accepts `exercise_context`
   (`standard` | `gate` | `stress_test`).
3. The Practice player keeps gate and stress-test markers and runs their battery in place
   (`POST /api/vocab-dojo/gate` | `/stress-test`, answers posted with the battery context,
   first try only, then `/gate/result` | `/stress-test/result`). Those endpoints are unchanged.
4. A ring-2 demotion of a word that came through the drill restarts the drill (ADR-040).

## Consequences

- Rings, gates, stress tests and mastery work again. The 120 existing ring-1 words start moving
  from their current family confidences; nothing is backfilled from past attempts.
- Practice attempts cost one more RPC.
- `ladder_record_attempt` stays as-is (Vocab Dojo API) and is now unused by the app.

## Alternatives Considered

- **Call `ladder_record_attempt` instead of the Practice path's own writes:** it updates BKT on
  retries and creates ladder rows for any reviewed word (bypassing the new-word quota).
- **Drop gates and stress tests:** a design change to ADR-005, not a fix.
