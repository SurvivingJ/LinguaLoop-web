# Results: serving-side simulation experiments

Read-only-repo sandbox work, 2026-09-17. All code lives under
`sandbox/exercise-lab/prototypes/serving/` (`formats.py`,
`exp1_estimable_range.py`, `bakeoff.py`, `exp4_attempts_floor.py`); raw JSON
outputs are in `sandbox/exercise-lab/reports/serving_exp*.json`. No
production code, migration, or Supabase/LLM call was touched — everything
here is closed-form math or a from-scratch Monte Carlo population, per
`docs/recon-serving.md` and `docs/redteam-serving.md`, which this session
read but did not re-derive.

---

## Experiment 1: multi-selection items as a chance-floor attack

### (a) Effective chance floor `c` and per-format single/multi-item information

| Format | c | ELO equilibrium reach | Estimable width @20 items | Estimable width @50 items |
|---|---|---|---|---|
| 4-option MC | 0.250 | −191 pts | none | none |
| 5-option MC | 0.200 | −241 pts | none | none |
| 6-option MC | 0.167 | −280 pts | none | none |
| Select-all-6 (all-or-nothing) | 0.0156 | −720 pts | none | 196 pts |
| 3-blank cloze (4-way each) | 0.0156 | −720 pts | none | 196 pts |
| 2-blank cloze (4-way each) | 0.0625 | −408 pts (not separately re-run; c between mc6 and matching) | — | — |
| Matching 4 pairs | 0.0417 | −545 pts | none | 124 pts |
| Ordering 4 tokens | 0.0417 | −545 pts | none | 124 pts |
| Ordering 5 tokens | 0.00833 | −830 pts | none | 216 pts |
| Ordering 6 tokens | 0.00139 | −1143 pts | none | 232 pts |

**"Estimable width"** = the ability range (in ELO points, relative to a single item's difficulty `b`) over which `SE(theta) ≤ 52.1 points` — the literal `SE(theta_logit) ≤ 0.3` criterion converted into this codebase's ELO-point parameterization (`1 logit = 400/ln(10) = 173.7 points`), assuming N items all administered at the same `b` (worst case; an adaptive test that re-aims each item does better, see (c)).

**The number that matters most in this table: at 20 items — the live IRT calibrator's own `DEFAULT_MIN_ATTEMPTS` floor — literally none of the nine formats clear `SE ≤ 0.3` anywhere.** This isn't a chance-floor artifact; it's a discrimination-scale artifact: max single-item Fisher information at `a = ln(10)/400` (this codebase's ELO-point discrimination unit) is `8.29×10⁻⁶`, giving a best-case single-item `SE_min = 347 points`. You need roughly 45 items at the *best possible* difficulty match (`c=0`) just to reach 52 points of precision; real formats need more. Only at 50 items do the lowest-`c` formats (select-all-6, cloze-3, the two orderings) begin to resolve a narrow band (124–232 points); standard 4/5/6-option MC never clears the bar even at 50. **Multi-selection formats don't just move the floor — they're the only formats that make the 20-attempt-and-beyond regime resolve at all**, but even they need more than 20 attempts to do it.

### (b) ELO equilibrium reach (`400·log₁₀(1/c − 1)`)

The −191pt cap (4-option MC) moves to: −241 (5-opt), −280 (6-opt), −408 to −545 (2-blank cloze / matching / ordering-4), −720 (select-all-6, 3-blank cloze), −830 (ordering-5), **−1143 points (ordering-6)**. Ordering-6 moves the cap over 5× farther than today's 4-option format.

### (c) HEADLINE — items-to-converge, 448-point true ability spread (ADR-024's real number)

80 simulated learners, true ability drawn uniformly across a 448-point spread centered on the live cold-start default (1200), adaptive test (each item's difficulty = current MLE estimate — mirrors nearest-ELO), convergence = MLE stays within ±50 points for every remaining item, capped at 40 items:

| Format | Median items to converge | Non-convergence rate (≤40 items) | Median minutes (stated time/item) |
|---|---|---|---|
| 4-option MC | 34 | **51%** | 8.5 |
| 5-option MC | 35 | 49% | 9.3 |
| 6-option MC | 33 | 45% | 9.4 |
| Ordering-6 (c=0.0014) | 28.5 | 35% | 20.0 |
| Ordering-5 (c=0.0083) | 29.5 | 35% | 17.2 |
| Select-all-6 / cloze-3 (c=0.0156) | 26.5 | 35% | 13.3 / 17.7 |
| Matching-4 / ordering-4 (c=0.0417) | 33.5 | 37.5% | 19.5 / 15.6 |

**Every format has a non-convergence rate between 35% and 51% at a 40-item cap.** Lower-`c` formats do converge in fewer items (26.5–29.5 median vs. 33–35 for MC), a real and consistent effect, but the improvement is modest (≈15–22% fewer items) and none of them get non-convergence anywhere near zero. This is the honest, quantitative version of the redteam's SS2 point: a guessing floor produces a *biased* equilibrium, and multi-selection formats reduce that bias's magnitude and mildly speed convergence — but convergence remains slow and unreliable in absolute terms because single-item information is intrinsically tiny at this discrimination scale, independent of `c`.

### (d) Information-per-minute — the honest tradeoff

Median wall-clock time to converge, using the stated seconds-per-item assumptions: mc4 8.5 min, mc5 9.3 min, mc6 9.4 min, select-all-6 13.3 min, cloze-3 17.7 min, ordering-4 15.6 min, matching-4 19.5 min, ordering-5 17.2 min, ordering-6 20.0 min.

**Standard 4-option MC is cheapest in raw wall-clock minutes (8.5) precisely because it's cheap per item (15s assumed), even though it needs the most items (34 median) and converges least reliably (51% non-convergence at the 40-item cap).** The multi-selection formats need fewer items (26.5–33.5 median, a 15–22% reduction) but each item costs roughly 2× as long, so **every multi-selection format tested costs MORE total minutes than mc4, not less** — the item-count win never overcomes the per-item time cost at these assumptions. The honest tradeoff is therefore: **multi-selection formats buy a moderately lower non-convergence rate (35% vs. 51%) at a real wall-clock cost (1.6–2.4× mc4's minutes), not a time saving.** No format tested "halves items-to-converge but triples time-per-item" as a clean loss-making example, but none is a clean win either — this is a reliability-vs-speed tradeoff, and which side wins depends entirely on whether the product cares more about not stalling out (favor multi-selection) or about total session time (favor plain MC).

---

## Experiment 2 + 3: selector bake-off, race under four response models

Five selectors (A = live elo+vocab objective, B = A + BKT/FSRS "due" scheduling term, C = expected-BKT-gain-per-minute knapsack using `FAMILY_BKT_RATES['standard']` verbatim from `services/vocabulary_ladder/config.py:186` [learn=0.15, slip=0.12], D = nearest-ELO on content-computed difficulty instead of type-blind seeded difficulty, E = random-in-tier control), raced under four response/learning models (discrete BKT; continuous FSRS-style retrievability; pure IRT with **no learning at all**; and a deliberately misspecified model with learn/slip swapped and forgetting half-life anti-correlated with ability). 24 simulated learners, 60 senses, 45 items, 30 days, 5 seeds per (model, selector) cell, retention measured on 10 senses held out from serving during the final 7 days.

### Retention ranking (mean over 5 seeds), best → worst

| Model | Ranking | A vs. E gap vs. seed noise (stdev) |
|---|---|---|
| BKT (discrete) | B(.0886) > A(.0880) > E(.0848) > C(.0833) > D(.0746) | gap .0032, **smaller than stdev (~.007–.008) — not distinguishable from noise** |
| FSRS (continuous) | B(.0419) > A(.0417) > C(.0278) > E(.0223) > D(.0199) | gap .0194, **larger than stdev (~.003–.01) — a real, robust separation** |
| Pure IRT (no learning) | **C(.0382) > D(.0349) > E(.0329) > B(.0328) > A(.0325)** | ranking **inverts**: A/B fall to last, gap A-vs-E is .0004 (noise) |
| Misspecified | B(.0831) > A(.0816) > E(.0806) > C(.0787) > D(.0718) | gap A/B-vs-E ~.001–.003, **not distinguishable from noise** |

### What's stable, what flips

**Stable across BKT / FSRS / misspecified (3 of 4 models, including the adversarial one):** the live objective (A) and its scheduling-augmented variant (B) occupy the top two ranks; D (elo-only, no vocabulary term) occupies last place in all three. This is the one genuinely robust conclusion this simulation supports: **dropping the vocabulary/knowledge-targeting term entirely (D's whole value proposition — clean, response-data-free difficulty) costs retention, consistently, whenever there is any learning dynamic to target.**

**Flips completely under pure IRT (no learning at all):** C jumps to first, A and B collapse to last, and — this is the headline the task asked to look for — **random-in-tier (E) beats both the live objective (A) and the scheduling variant (B)** when there is no actual learning process for A/B's targeting logic to exploit. Mechanically this makes sense (A/B's vocabulary term assumes exposure changes knowledge; when it structurally can't, that targeting buys nothing and the elo-matching noise it adds becomes pure cost), but it is exactly the falsifiable prediction a trustworthy simulator has to expose, not paper over.

**Is "sophisticated selectors clearly beat random" actually true here? Only sometimes, and only by a specific mechanism.** Under FSRS the separation is large and real (stdev-robust). Under discrete BKT and the misspecified model, the apparent A/B-over-E edge is smaller than seed-to-seed noise at this sample size (24 learners × 5 seeds) — **not a demonstrated win, an unresolved tie.** Under pure IRT, random wins outright. **The single most important finding from this bake-off: no selector beats random robustly across all four models — the win is real in exactly one of four tested worlds (FSRS) and is a tie-or-loss in the other three.** This is stated per the task's explicit instruction to report this prominently if found, not bury it.

**Teaching less while improving M1-type metrics:** in the single-seed BKT run, D achieved the highest on-target rate (M1 = 0.166) of all five selectors while its cumulative mastery at day 29 (0.107) was *lower* than C's and E's (0.108, 0.109) — a candidate "improves targeting while teaching less" result. But the gaps (M1: ~0.01–0.015 out of ~720 samples, binomial SE ≈ 0.0137; mastery: ~0.001–0.002) are within one standard error of each other. **This is suggestive, not demonstrated** — flagged, not claimed.

**Nobody reached mastery.** `frac_target_mastered` was 0.0 in every one of the 20 (model × selector) cells at a 30-day horizon with a 0.8 `p_known` threshold — the mastery curve crept from ~0.05 to ~0.10 over 30 days under BKT/misspec, and even lower/flatter under FSRS/pure-IRT. Time-to-proficiency is therefore **uninformative in this parameterization** (fully censored) — a limitation of the simulation's chosen learn-rate/exposure-rate combination, not a claim about real learners.

---

## The simulator trap: what survives, what must not be claimed

Following the redteam's own SS8 warning (a simulator can only confirm the model family it was built to represent), here is the accounting:

**Survives across ≥3 of 4 response models (treated as a stable simulated-mechanism finding):**
- Dropping the vocabulary-knowledge term (selector D) costs retention whenever any learning dynamic exists.
- The live objective (A) and a BKT/FSRS-scheduling augmentation of it (B) are never the *worst* selector under any model with real learning.

**Flips depending on the response model (must NOT be stated as a general finding):**
- Whether A/B "beat random" at all — true and robust only under the FSRS model; a statistical tie under discrete BKT and the misspecified model; **false** (random wins) under pure IRT.
- The absolute retention numbers themselves vary 2–4× across models (e.g., A's retention ranges from .0325 to .0880 across the four models) — no absolute magnitude claim survives model choice.

**Claims that must NOT be made from this simulation alone** (per the task's mandate and consistent with `docs/redteam-serving.md` SS8):
- That any selector (A–D) "improves real LinguaLoop learner outcomes" — the simulator's response model is authored by this session, not fit to real behavioral data (no calibration against the one real learner's 21 ja + zh attempts was performed here, for the stated economy reason: n=1 cannot constrain 4+ free response-model parameters).
- Any specific numeric percentage-improvement figure carried into a product decision.
- Anything about **English at all** — the simulation used one abstract "skill," not per-language parameters, and even if it had, en has zero real attempts to calibrate against (per established findings).
- That multi-selection formats (Experiment 1) "solve" ability estimation — Experiment 1's own numbers show non-convergence rates of 35–51% even in the best case at a 40-item cap.
- That the "teaching less while improving M1" result for selector D is real — it is a single-seed, within-noise observation, explicitly flagged above as unconfirmed.

---

## Experiment 4: attempts-per-item structural blocker

**Quoted, verbatim (`migrations/task748_get_recommended_tests_vocab_aware.sql:349-353`), the never-re-served filter inside `get_recommended_tests`'s candidate CTE:**

```sql
AND NOT EXISTS (
    SELECT 1 FROM test_attempts ta
     WHERE ta.user_id = p_user_id
       AND ta.test_id = t.id
       AND ta.test_type_id = us.type_id
       AND (p_as_of IS NULL OR ta.created_at < p_as_of)
)
```

This is an unconditional, hard filter (not the neutral-degradation soft penalty used elsewhere in the same query) — once a user has attempted a `(test_id, test_type_id)` pair, that pair is permanently excluded from ever being served to them again via this RPC. Reaching the live IRT calibrator's `DEFAULT_MIN_ATTEMPTS=20` therefore requires **20 distinct users**, not 20 attempts from any population.

**Order-of-magnitude time-to-floor** (pool size ≈15 tests per (language, type) — derived from recon's ~121–125 tests/language over 8 types for en/zh, ~59/8 for ja; optimistic uniform-routing assumption, i.e. best case):

| Daily active users | Days for ANY single item to reach 20 attempts |
|---|---|
| 10 | ~30 days |
| 100 | ~3 days |
| 1,000 | ~0.3 days |

**This is the optimistic floor, not a realistic estimate.** Real routing ranks candidates by `|elo_diff|` — only the sub-population near an item's specific difficulty band is ever routed to it — so the true time-to-floor is a multiple of these numbers (unquantified here; would require the real ability distribution production doesn't have). **And at today's actual traffic — one user has ever taken a test, ever — the honest answer is not "slow," it's "unreached": the 20-attempt floor has never been approached for a single item and will not be approached at anything like current usage.**

**Minimum viable change, if item-level IRT calibration on the test path is wanted at all:** the established findings already point at the answer — either (1) relax the hard exclusion to a *controlled* re-serve policy (deliberately reintroducing some repeat exposure purely for calibration, a real invariant change to the "never re-serve" guarantee), (2) pool calibration across item families instead of per-item (aggregate attempts across items sharing type+difficulty-band so the 20-attempt requirement is met by the family, not the individual test), or (3) sidestep the need for response-fitted difficulty entirely via S4's computed-difficulty approach (Zipf/length/confusability features, zero response data required — this is the option Experiment 2's bake-off already shows is the *worst* on retention when used ALONE without a vocabulary term, so it is a cold-start/seeding fix, not a substitute for the vocabulary signal). **Per-item IRT on the test-serving path is not reachable without one of these three structural changes — "wait for more traffic" is not a plan, given the pool-size/traffic-rate math above.**
