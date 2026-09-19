---
title: "Lookahead pre-teaching: variant simulation (TASK-782)"
type: evaluation
status: complete
last_updated: 2026-09-19
---

# Lookahead pre-teaching: variant simulation

**Verdict: the algorithm is solved and the content is not.** Under today's
exercise inventory the best possible pre-teaching variant moves Japanese from
11.9% to 11.9% of the catalogue in band — **zero** — because only 1.8 of the
17.5 words that block an average test can actually be drilled. Lift the supply
gate and the same algorithm reaches **98.3%**. Every variant question below is
worth answering, and none of them is the reason this does not work today.

The recommended configuration is **A2 cohort + B2 working depth + C3
least-known-first**, and the work that unblocks it is generating ladder
exercises for ~500 demand-ranked senses per language, not tuning the ranker.

---

## 1. What was run

`scripts/simulate_preteach_variants.py`, read-only against live, for the one
learner with vocabulary history (`de6fd05b…`, ja `ability_zipf` 5.0251, zh
5.1525 — both from `selection_vocab_ability()`, the `uvk_crossing` fallback,
since `user_calibration_state` is still empty).

`P_known(s)` is [[features/vocabulary-aware-test-selection.tech]] §3.2
verbatim: the `user_vocabulary_knowledge` row when one exists, else
`σ(1.5·(zipf − ability_zipf) + ln(0.85/0.15))`. A test resolves if ≥5 of its
`vocab_sense_ids` carry a Zipf (§3.4). Target `u* = 0.15`, band 5–25%, matching
`selection_tuning` and the metric in
[[evaluations/selection-three-arm-replay-2026-09-17]].

Catalogue: **ja 59 tests / 1,589 distinct senses**, **zh 98 tests / 4,029**.

### The three axes

| axis | variants |
|---|---|
| **A — what to target** | `a1_commit` one pinned test · `a2_cohort` the shared vocabulary of the top-10 pool · `a3_demand` catalogue-wide ranking, no target |
| **B — how deep before the test** | `b1_preview` Ring 1 only (p_known→0.65, 4 items) · `b2_working` Ring 2 cleared (→0.85, 12 items) · `b3_mastery` Gate A (→0.92, 20 items) |
| **C — which words first** | `c1_frequency` most test occurrences · `c2_frontier` nearest the frontier · `c3_greedy` least-known first |

Item counts per depth come from the ladder's ring requirements
([[algorithms/vocabulary-ladder]]: R1 = 1 family, R2 = 3 families), doubled
because each family needs first-attempt successes on **2 distinct calendar
days**. Minutes use `DEFAULT_EXPECTED_SECONDS = 45`.

### The ceiling arm

Every table is reported twice: **gated**, which applies the live supply gate
(`LADDER_MIN_EXERCISES_PER_SENSE = 3`), and **ceiling** (`--ignore-supply`),
which assumes every blocking sense has exercises. The ceiling arm is not a
proposal. The gap between the two *is* the content debt, in the units that
matter.

---

## 2. The finding that dominates every other finding

Per average test, under the live inventory:

| | ja | zh |
|---|---|---|
| words blocking the test (`p_known < 0.5`) | 17.4 | 26.4 |
| words needed to reach `u* = 0.15` | **17.5** | **26.4** |
| of those, drillable today (any exercise) | **1.8** | **0.6** |
| of those, drillable today (ladder levels only) | **1.8** | **0.0** |
| starved — nominated, no exercises | 15.7 | 25.8 |

Chinese has **zero** ladder-drillable blocking words per test. Not few: zero.

The mechanism is that exercise generation has been frequency-first while the
blocking words are, by definition, the rare ones:

| | senses total | with exercises | mean Zipf *with* | mean Zipf *without* |
|---|---|---|---|---|
| ja | 19,668 | 74 (0.4%) | 4.77 | 3.87 |
| zh | 22,475 | 180 (0.8%) | 4.97 | 4.09 |
| en | 9,889 | 166 (1.7%) | 5.09 | 4.19 |

The learner's `ability_zipf` is **5.03 (ja) / 5.15 (zh)**. The mean sense that
has exercises sits *below* that threshold — `σ(1.5·(4.77−5.03)+1.73) = 0.80`.
**The average word the practice engine can drill is one the learner is already
80% likely to know.** Across the whole test catalogue, 702 ja senses and 1,773
zh senses are unknown and appear in a test; **16** of the ja set and **0** of
the zh set have ladder exercises.

This is visible in learner behaviour without any modelling: **15 exercise
attempts have ever been recorded**, against 54 test attempts; all 47
`user_word_ladder` rows are still `word_state = 'new'`, subscribed between
2026-08-31 and 2026-09-08, and **5 of the 47** clear the supply gate. The
practice engine is starved, not declined.

---

## 3. Axis B — how deep. Preview is not enough; mastery is waste.

ja, ceiling arm, `a1_commit`, unbounded budget:

| depth | in band | mean unknown after | words | minutes |
|---|---|---|---|---|
| `b1_preview` (R1, p→0.65) | 0.356 | 0.249 | 17.5 | 52 |
| **`b2_working` (R2, p→0.85)** | **0.983** | **0.187** | 17.5 | 157 |
| `b3_mastery` (Gate A, p→0.92) | 0.983 | 0.166 | 17.4 | 261 |

zh reproduces it exactly: 0.704 → **1.000** → 1.000, at 79 / 238 / 395 minutes.

Two clean results:

- **Recognition-only preview fails.** Lifting a word to `p_known = 0.65` leaves
  the arithmetic short — 35% of ja tests reach the band, against 98%. A
  flashcard-style "here are tomorrow's words" screen is not a cheaper version
  of this feature; it is a version that does not work.
- **Mastery buys nothing.** `b3` costs 66% more time than `b2` for **identical**
  in-band share in both languages. Pre-teaching should stop at Ring 2 cleared
  and hand the word to FSRS.

---

## 4. Axis C — which words. Inert until a budget binds, then least-known-first wins.

Unbounded, all three rankings score identically (0.983 / 0.983 / 0.983) — the
loop teaches until the target is hit regardless of order. Order only matters
when the budget binds, which is the real regime:
`target_new_rate = daily_minutes // 6` per **week** (5 words/week at 30 min/day)
against a demand of 17.5 words per test.

ja, ceiling arm, `b2_working`:

| budget | `c1_frequency` | `c2_frontier` | **`c3_greedy`** |
|---|---|---|---|
| 5 words | 0.288 | 0.271 | **0.339** |
| 10 words | 0.458 | 0.424 | **0.492** |

`c3_greedy` (least-known first) wins at every budget and every depth;
`c2_frontier` (teach the words you nearly know) is consistently **worst**.
Mechanically that is forced: the objective is mean `p_known`, so the lift per
word is largest for the word with the lowest `p_known`.

> **Caveat, and it is a real one.** The simulation charges the same 12 items to
> every word regardless of starting `p_known`. If a word at `p_known = 0.45`
> genuinely takes fewer attempts to clear Ring 2 than one at 0.05 — which is
> what BKT assumes — then `c2_frontier` is being unfairly charged and the true
> ordering could invert. **Nothing in the available data settles this**, and it
> is the one axis that must be decided by a live A/B rather than by arithmetic.
> Ship `c3_greedy` as the default and keep `c2_frontier` as the contrast arm.

---

## 5. Axis A — what to target. The cohort is an order of magnitude cheaper.

ja, ceiling arm, `b2_working`:

| variant | scope | words taught | in band | minutes | **words per test brought in band** |
|---|---|---|---|---|---|
| `a1_commit` | per test | 17.5 *each* | 0.983 | 157 *each* | 17.8 |
| **`a2_cohort10`** | top-10 pool | **15 total** | 0.900 | 135 total | **1.7** |
| `a3_demand500` | catalogue | 500 total | 0.678 | 4,500 | 12.5 |
| `a3_demand` (all 705) | catalogue | 705 total | 0.983 | 6,345 | 12.2 |

zh: `a2_cohort10` reaches **1.000** in band on **9 words / 81 minutes**.

`a1_commit` pins one test and pays its full vocabulary bill alone.
`a2_cohort` teaches the words *shared* across the ten tests the ranker would
plausibly serve next, so each word is amortised over the whole pool — **~10×
fewer words per test unlocked**, and it never has to commit to a test before
the learner has earned it. `a3_demand` ignores what is about to be served and
wastes most of its budget.

> One honest adjustment: `a2`'s pool is chosen by nearness to the band, so it
> starts from a higher baseline (ja 0.168 mean unknown vs 0.369 catalogue-wide).
> Its advantage is real but the headline number flatters it; the load-bearing
> comparison is words-per-test-unlocked, where it wins by ~10×.

---

## 6. What this projects to in score, and why no number is given

The recorded relationship on live history is **Spearman(unknown share of the
test taken, score) = −0.584** ([[evaluations/selection-three-arm-replay-2026-09-17]]),
computed **as of** each attempt.

Recomputing it naively from *current* `p_known` gives **r = +0.107** on the same
21 ja attempts — the opposite sign. That is not a contradiction, it is
contamination: `update_vocabulary_from_test` writes `p_known` *from* those very
attempts, so a test the learner did well on has its words marked known
**because** they did well.

**Consequence for this feature: the outcome measure is endogenous to the
intervention.** Any live evaluation of pre-teaching must snapshot `unknown(t)`
at the moment the test is released and never recompute it afterwards, or it
will score itself. No score-uplift projection is offered here; the direction is
supported by the −0.584, the magnitude is not identified at n=21.

---

## 7. Sizing the content debt

Tests reachable by pre-teaching after generating the top-N demand-ranked senses
(demand = how many tests the sense blocks):

| senses generated | ja (of 59 tests) | zh (of 98) |
|---|---|---|
| 0 — today | 4 (7%) | 10 (10%) |
| +50 | 6 | 12 |
| +200 | 12 (20%) | 31 (32%) |
| **+500** | **45 (76%)** | **54 (55%)** |
| +1,500 | 57 (97%) | 87 (89%) |

Total addressable demand is 702 ja / 1,773 zh unknown senses across the
catalogue. At the recorded batch economics (~$0.024 and ~5.5 min wall clock per
sense, [[task515-batch-economics]] — the binding cost is wall clock, and the
languages cannot run in parallel), **500 senses is ~$12 and ~46 hours per
language**. The spend is irrelevant; the two days of wall clock are the plan.

---

## 8. Two defects found while measuring

1. **`generation_queue` has 7 rows stuck in `status = 'running'` for 29 days**
   (claimed 2026-08-21, never finished). There is no lease expiry, and
   `_open_queue_sense_ids` de-duplicates against `pending`/`running`, so those
   7 senses can never be re-queued. 11 further rows are `failed`, 4 `done`.
   The demand-driven path exists and has effectively never run — **0 rows carry
   `reason = 'subscribe_topup'`.**
2. **The supply gate is doing its job and nobody is watching the output.**
   `_request_generation` already logs and enqueues starved nominations, capped
   at `DEMAND_GENERATION_MAX_PER_CALL = 5`. At a starvation rate of 15.7 words
   per test that cap is two orders of magnitude below demand, and the queue it
   writes into is jammed per (1).

---

## 9. Reproducing

```bash
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
  python scripts/simulate_preteach_variants.py --language 3            # gated
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
  python scripts/simulate_preteach_variants.py --language 3 --ignore-supply
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
  python scripts/simulate_preteach_variants.py --language 3 \
      --ignore-supply --budget 10                                      # axis C
PYTHONPATH=. PYTHONIOENCODING=utf-8 \
  python scripts/simulate_preteach_variants.py --language 1 --ladder-only
```

`--ladder-only` counts only `ladder_level IS NOT NULL` exercises, which is what
Acquisition mode actually serves. It is how the zh "0.0 drillable" figure above
was obtained.

## Related Pages

- [[features/lookahead-preteaching]] — the feature this evaluates
- [[features/lookahead-preteaching.tech]] — the design spec it feeds
- [[decisions/ADR-026-lookahead-preteaching]] — the decisions taken from it
- [[features/vocabulary-aware-test-selection.tech]] — `P_known`, `u*`, the band
- [[evaluations/selection-three-arm-replay-2026-09-17]] — the −0.584 and the arm harness
- [[features/practice-engine]] — the engine being made central
- [[algorithms/vocabulary-ladder]] — rings, families, the 2-distinct-day gate
