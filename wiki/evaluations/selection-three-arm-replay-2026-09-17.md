---
title: "Selection arms replayed: weight 0 vs sum vs product (TASK-781)"
type: evaluation
status: complete
last_updated: 2026-09-17
---

# Selection arms replayed: weight 0 vs sum vs product

**Verdict: turn neither switch on on this evidence — and if one ever moves, it is
`vocab_weight`, not `combine_mode`.** The vocabulary term is worth a lot (share
of served tests inside the 5-25% unknown band goes **0.79 → 0.95**). The
multiplicative combination TASK-780 added is worth **nothing measurable, and is
slightly negative**: 0.952 → 0.938 on the same metric, better on **0** of 21
attempts, worse on 3. Both switches remain off.

## What was run

`scripts/measure_selection_quality.py --until 2026-09-08T23:59:59+00:00
--replay-language 3`, extended by TASK-781 from two arms to three:

| arm | `vocab_weight` | `combine_mode` | score |
|-----|---------------|----------------|-------|
| `w0` | 0 | — | `e` (the pre-TASK-748 ranking) |
| `sum` | 1 | `'sum'` | `e + v` |
| `product` | 1 | `'product'` | `(1+e)·(1+v)` |

with `e = elo_weight·|Δelo|/400` and `v = vocab_weight·|unknown − u*|/u_tol`.
`w0` runs in sum mode because at weight 0 the mode cannot matter — `(1+e)·1` is a
monotone transform of `e`.

**The product arm required a live write.** `combine_mode` is a `selection_tuning`
row, not an RPC argument ([[features/vocabulary-aware-test-selection.tech]]
§3.5), and the harness talks PostgREST, so it cannot use the transaction-local
`UPDATE … ROLLBACK` the SQL tests use. It sets the row, runs the arm, and
restores it in a `finally` — **and refuses to do so unless `vocab_weight = 0`**,
because at weight 0 `get_recommended_tests` never reaches the ranker, so the mode
cannot change what a live learner is served. The run ended with
`vocab_weight=0, combine_mode='sum'`, re-read from the database and printed.
(The restore write stamps `selection_tuning.combine_mode.updated_at` — it reads
`2026-09-16T21:47Z` because the page is dated local time; `vocab_weight` is
still untouched since 2026-09-10T11:34Z.)

## The four metrics (ja replay: 21 first attempts, 210 top-10 slots per arm)

| metric | `w0` | `sum` | `product` |
|--------|------|-------|-----------|
| **share of top-10 inside 5-25% unknown** | 0.786 | **0.952** | 0.938 |
| median top-10 unknown | 0.193 | 0.168 | 0.168 |
| p25 / p75 | 0.122 / 0.246 | 0.142 / 0.199 | 0.142 / 0.199 |
| **top-10 overlap with `w0`** (mean Jaccard) | — | 0.395 | 0.391 |
| **M5** min per-type pool delta vs `w0` | 0 | 0 | 0 |
| neutral slots | 0/210 | 0/210 | 0/210 |
| rank of the test actually taken (median) | 2 | 9 | 7 |

**Top-10 overlap `sum` vs `product`: 0.939.** The two arms pick the identical
top-10 *set* on **14 of 21** attempts, and the identical set *in the same order*
on 7.

**Spearman(unknown share of the test taken, the score the learner got) =
−0.584**, reproducing the −0.59 on record. It is **arm-independent** by
construction — `unknown_share` is a property of (user, test, as-of), not of the
ranking — so it is a check that the vocabulary signal is real, not a comparison
between arms. It remains the strongest single number in this workstream: more
unknown words, lower score, on live history.

## Why product does not help

Per attempt, product's in-band share is **better on 0, worse on 3, equal on 18**.
Not one attempt improved. The mechanism is visible in the rank correlation
between a candidate's unknown share and the score it is given:

| pair | `w0` | `sum` | `product` |
|------|------|-------|-----------|
| zh | 0.177 | **0.918** | 0.839 |
| ja | 0.552 | **0.961** | 0.913 |

Product's ranking is *less* driven by vocabulary than sum's, not more. Since
`product = sum + e·v`, every candidate is pushed down by `e·v` relative to sum —
which is the intended demotion of "wrong on both axes", but it lands hardest on
candidates whose vocabulary term is *large*, i.e. exactly the ones the
vocabulary term is trying to demote. It dilutes its own signal.

**The zh snapshot shows the sharper cost.** "What would be served now", per
(type, arm), counting how many of the ten have no vocabulary opinion at all:

| zh type | `w0` neutral | `sum` neutral | `product` neutral | `sum` in band | `product` in band | overlap s\|p |
|---------|------------|-------------|-----------------|-------------|-----------------|------------|
| dictation | 9/10 | **0/10** | 5/10 | 1.00 | 0.80 | 0.25 |
| listening | 7/10 | **0/10** | 2/10 | 0.70 | 0.62 | 0.67 |
| pinyin | 7/10 | **0/10** | 0/10 | 1.00 | 1.00 | 1.00 |
| reading | 8/10 | **0/10** | 3/10 | 0.80 | 0.86 | 0.54 |

Chinese has 27 active tests with no `vocab_sense_ids`, and they sit close to the
learner's ELO, so `w0` serves them heavily. `sum` clears them out completely.
**`product` lets a third to a half of them back in.** A neutral candidate carries
the cohort *median* penalty; relative to sum, product charges every candidate an
extra `e·v`, which is smallest exactly where `e` is small — so a test the term
knows nothing about, sitting at the learner's ELO, is re-advantaged over a linked
test that is vocabulary-appropriate but further away in ELO. §3.4 chose the
median so that "no opinion" would be **neither** a reward nor a penalty; under
product it becomes a mild reward.

> **Read the in-band column with the neutral column.** `band_share` is computed
> over candidates that *have* an unknown share, so an arm serving more unlinked
> tests scores its band share over a smaller denominator. zh product's 0.80 is
> 4 of 5, not 8 of 10. The harness now prints the neutral count beside it; the ja
> replay figures are unaffected (0 neutral slots in every arm).

## What this does not settle

- **One learner — and that is not a window artefact.** Verified live
  2026-09-17: 14 users exist and exactly **one** (`de6fd05b…`) has *ever* taken a
  test. Every number here is that learner, in zh and ja. English has no attempts
  at all and therefore no served pair.
- **Ability is the uvk crossing, not calibration.** `ability_source` is
  `uvk_crossing` for both languages (ja 5.025, zh 5.152); `user_calibration_state`
  still has 0 rows, so the §4 tier ceiling never armed in any arm.
- **The replay is an approximation.** Test ELOs cannot be rewound
  (`test_skill_ratings` keeps no history) and `p_known` values updated after an
  attempt are read at today's value. Recorded in the TASK-748 migration header.
- **`u*` is still 0.15 on content that cannot reach it.** The ja median served
  unknown is 0.168 even in the best arm. The band metric is generous (5-25%)
  precisely because the catalogue cannot do better yet.
- **Nothing here tests product on a thick, fully-linked catalogue.** Its
  theoretical case — demoting the both-axes miss — is real and is pinned by
  fixtures; it simply does not pay on the pool that exists in 2026-09.

## Recommendation

1. **Leave `combine_mode = 'sum'`.** It costs nothing to keep the product branch
   live and inert, and the fixtures keep it honest, but on this evidence it is
   not a candidate for switching on. Revisit only if the catalogue grows enough
   that unlinked tests stop being a meaningful share of the pool — verified live
   2026-09-17: **zh 27 of 125 active tests and en 21 of 121 carry no
   `vocab_sense_ids`**; ja 0 of 59, which is why the ja replay sees no neutral
   slots and the zh snapshot sees many.
2. **ACTED ON 2026-09-17: `vocab_weight` raised to 1 — the term is live.** The
   operator took this recommendation directly rather than run the shadow window,
   on the grounds that rollback is one `UPDATE`. Verified from the recommender's
   output (0 unlinked zh tests served, `elo_diff` non-monotonic, 10 per type
   intact); latency 5-14 ms → 25-69 ms. See `wiki/log.md` 2026-09-17. The
   original recommendation follows.
   **`vocab_weight` is the switch worth arguing about** — 0.79 → 0.95 in-band,
   M5 intact, all neutral tests cleared from the zh top-10. It is still one
   learner's history, so the decision wants either the 7-day shadow window
   (`--shadow-out`) or a deliberate "n=1 is enough for a reversible flag".
3. If `vocab_weight` is ever raised, **re-run this replay first** — with the
   weight above 0 the harness will (correctly) refuse to switch `combine_mode`,
   and the product arm has to move to a SQL rollback-only transaction.

## Related

- [[features/vocabulary-aware-test-selection.tech]] §3.3, §3.4, §5.1
- [[tasklist/vocabulary-aware-test-selection.tasks]] TASK-780, TASK-781
- [[evaluations/selection-replay-2026-09-10]] — the two-arm predecessor
- [[decisions/ADR-024-vocabulary-aware-test-selection]]
