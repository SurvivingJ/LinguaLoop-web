---
title: "ADR-052: Retire dt_card review cards in favour of repair daily practice, and select the /next window in SQL"
status: proposed
date: 2026-11-23
---

# ADR-052: Retire dt_card review cards in favour of repair daily practice, and select the /next window in SQL

**Proposal. Not decided. This needs the owner's decision; nothing described under "Decision" has been built.** Two related simplifications are bundled because both remove code from `GET /api/dual-translation/next`; the owner may accept one and not the other.

## Context

**Two remediation systems run side by side.**

- The FSRS card system ([[features/dual-translation-remediation.tech]]): `dt_error_profile_entry` (14 rows live on 2026-11-23: 1 queued, 4 drilling), `dt_card` (**4 cards**), `dt_card_review` (**0 reviews**).
- Guided self-repair ([[features/dt-guided-self-repair.tech]], [[decisions/ADR-045-dt-guided-self-repair]]): `dt_repair_session` / `dt_repair_item` (**22 sessions, 26 items**, live since 2026-11-16), with its own daily practice block. ADR-045 deliberately left `dt_card` alone.

Nobody has reviewed a `dt_card` yet. The card path also costs code and risk: card generation runs on `GET /api/dual-translation/next`, so **`/next` writes on a GET** when it materialises cards for queued entries; it needed its own batching (TASK-1003) and an own-language fix (a Chinese entry was once carded from a Japanese error: live cards 11 and 12).

**`/next` has two input paths.** The normal path calls the RPC `dt_next_inputs`; if it fails, a per-table fallback (`_TableInputs`, roughly 15 to 30 round trips) takes over for 10 minutes. The fallback duplicates the RPC path's logic by hand, so the two must be kept in sync. And the RPC returns the sentence rows of **every** candidate test (about 176 KB of JSON for zh, 274 tests, measured 2026-11-23) although `_choose_next` uses only the first eligible window; Python then builds materials for all of them on each call.

## Decision (proposed)

1. **Retire the `dt_card` review system** in favour of the repair daily practice. Remediation is then one queue keyed by sentence and language. Remove: the error-card branch of `/next` (and with it card generation on a GET), `cards.py` database wiring, the `/cards/due` and `/cards/<id>/review` routes, `metrics.compute_recurrence_metrics` (no caller outside tests), and the interleaving of error cards into practice sessions. Behaviour change for learners: error cards stop appearing in `/next` and in practice sessions. The existing 4 cards and the profile entries are exported or dropped by a migration chosen at implementation time; `dt_error_profile_entry` and the nightly synthesis can stay if the dashboard still uses them.
2. **Choose the `/next` window in SQL.** `dt_next_inputs` returns the chosen window (or only the first K candidate tests in serving order) instead of all tests' sentence rows, and the per-table fallback path is deleted. The serving order (resume, new window from an attempted test, new window from an untaken test nearest the learner's level, skipped, re-serve) must stay identical; the hash-based rotation key currently computed in Python has to be reproduced in SQL (for example with `pgcrypto`) or replaced by a stable SQL order with the same semantics.

## Consequences

- Easier: one remediation system to explain and maintain; `/next` becomes read-mostly (it still opens or creates a `dt_submission` row); a smaller payload (the order of 176 KB down to a few KB) and less Python work per call; no second input path to keep in sync.
- Harder: the SQL function grows in complexity and needs SQL tests; the sentence-reference review rules (tightness floor, reviewer agreement, [[decisions/ADR-050-reviewer-agreement-overrides-tightness-floor]]) must be reproduced exactly in SQL; the repair daily practice becomes the only spaced practice for DT errors, so its untuned thresholds matter more, and any future retention evidence for FSRS cards on DT errors is given up.
- Constrained: the Practice Engine's error-exercise stream and the dual-translation profile page lose their card source; the `dt_card` tables and `TASK-1003` follow-up disappear with it.

## Alternatives Considered

- **Keep both systems** (status quo). No migration or behaviour change; keeps unused code, a write on a GET and the duplicated `/next` path.
- **Retire the repair daily practice instead and keep FSRS cards.** FSRS is the better-studied scheduler, but ADR-045 rejected cards as the daily practice because FSRS ratings do not express the hint-level rules and the `card_type` CHECK would need a destructive change; guided repair is where the learner's actual usage is.
- **Retire the cards only; keep `/next` as is.** Smallest behaviour-relevant step; leaves the 176 KB payload and the duplicated path.
- **Fix `/next` by trimming the RPC without moving selection into SQL** (return the first K tests in a stable order). Cuts the payload but keeps the hash rotation in Python, so the RPC would have to return enough tests to cover the rotation.

## Related Pages
- [[features/dual-translation.tech]] — `GET /next`, error cards, input paths
- [[features/dual-translation-remediation.tech]] — the card system proposed for retirement
- [[features/dt-guided-self-repair.tech]] — the system that would remain
- [[decisions/ADR-045-dt-guided-self-repair]]
- [[decisions/ADR-051-one-transactional-write-per-dt-submission]] — the companion proposal
- [[api/rpcs.tech]] — `dt_next_inputs`
