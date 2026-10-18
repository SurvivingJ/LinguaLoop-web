---
title: "ADR-036: Open-ended practice beyond the daily budget"
status: accepted
date: 2026-10-18
---

# ADR-036: Open-ended practice beyond the daily budget

## Context
Practice mode ended when the daily budget and the optional extra round ran out. The extra round
was also hidden in Practice mode until today's tests were done, because its gate checked the full
queue. The developer wants unlimited reviews and/or new words in Practice mode.

## Decision
- Practice mode gets a "Keep practising" panel with repeatable rounds: reviews (≤10 per round:
  due first, then review-ahead) and/or new words (≤10 per round, admitted past the quota).
- Early reviews update FSRS/BKT normally. Extra new words join the ladder and its schedule.
  Extra work counts toward the weekly targets (attempts carry `is_tail`).
- No daily cap, only a warning when the new words go beyond today's goal.
- The Practice-mode tail gate ignores test items (`scope=practice`).

## Consequences
- Learners can over-admit; the review governor reduces later quotas automatically when the
  backlog grows.
- No complete-block ids for extra rounds; they are not daily blocks.
- One new RPC, no schema changes.

## Alternatives Considered
- Practice-only extra reviews that leave the schedule unchanged: rejected; it wastes evidence.
- A hard daily cap on extra words: rejected in favour of a warning.
- An `is_extra` attempt column to keep extra reviews out of the governor: dropped; early reviews
  only push due dates out and add no backlog.
