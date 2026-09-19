# Design 02 — Serving

Evidence: `recon-serving.md` (primary), plus direct reads of
`migrations/phase11_irt_selection.sql`, `migrations/phase12_practice_unified_score.sql`,
`services/irt/calibrator.py`, `wiki/algorithms/practice-unified-score.tech.md`,
`wiki/decisions/ADR-024-vocabulary-aware-test-selection.md`,
`wiki/decisions/ADR-007-merge-exercises-vocab-dojo.md`.

## 0. A correction that changes the framing of every S-design below

The thesis's S1-S4 are written as if `get_recommended_tests` /
`build_daily_session` (the **comprehension-test** selector recon-serving
traced in full) is the only selection surface in the app. It is not. A
second, separate, already-**live** selector exists for **ladder/vocabulary
exercises**: `get_practice_session` (`migrations/phase12_get_practice_session.sql`,
confirmed called from `routes/practice.py:65` and `routes/exercises.py:163,198`
via `get_practice_session_service()`), scoring candidates with a **unified
score that already combines IRT, BKT, and FSRS**:

```
score(item, user) = α·ladder_priority + β·irt_information(a,b,θ)
                   + γ·bkt_uncertainty(p_known) + δ·fsrs_urgency(due_date,stability)
```

(`migrations/phase12_practice_unified_score.sql:8-11`, matching
`wiki/algorithms/practice-unified-score.tech.md` exactly — despite that wiki
page's stale `status: planned` frontmatter, the SQL function and its callers
are live). Mode weights: acquisition `α=.40 β=.30 γ=.25 δ=.05`, maintenance
`α=.05 β=.15 γ=.30 δ=.50` (`practice-unified-score.tech.md` §"Mode weights").

**What this means for S1-S4**: they are not "should we add IRT/BKT/FSRS to
selection" proposals — a live implementation already exists, for a different
content type (ladder exercises) than the one recon-serving analyzed in depth
(comprehension tests). The real design question this document answers is
**which of S1-S4's ideas are (a) already solved by `get_practice_session` and
just need to be pointed at test selection too, (b) genuinely new for both
surfaces, or (c) specific to the comprehension-test selector's own
constraints** (fixed-content MC tests vs. individually-servable ladder
items). Each section below states which bucket it falls in. This is flagged
prominently because building any of S1-S4 from scratch, unaware of
`get_practice_session`, would duplicate a working system.

---

## S1 — Per-sense BKT/SRS scheduling

**Bucket: (a), already solved for ladder exercises; genuinely absent for
comprehension tests.**

`user_vocabulary_knowledge.p_known` (per-sense BKT) already drives
`bkt_uncertainty` in `get_practice_session`'s unified score
(`γ·(1−2·|p_known−0.5|)`, peaking at p_known=0.5 — i.e. already targeting
"senses near a 50% retrieval-strength threshold," which is a *stronger*
formulation of "near a threshold" than a raw FSRS forgetting-curve interval
would give, since it's threshold-agnostic to *which* 50% point and reacts
immediately to the latest BKT update rather than waiting for a scheduled
review date). `user_flashcards` already carries full FSRS state
(`stability, difficulty, due_date, reps, lapses, state` —
`recon-data-surface.md` §1) and feeds `fsrs_urgency` in the same score.

**What's genuinely missing**: `get_recommended_tests` (the comprehension-test
selector) has no equivalent. Its vocabulary term (`unknown(t)`) averages
`p_known` **across a whole test's linked senses** to compute a scalar
distance from a target unknown-rate (`u*=0.15`) — it never asks "is any
*individual* sense in this test near its own retrieval-strength threshold,"
because a test is a fixed bundle of ~15-40 senses and can't be scheduled
per-sense. **Recommendation**: do not build a parallel per-sense scheduler
for tests — extend `get_recommended_tests`'s existing vocabulary term with a
second, cheap statistic already computable from the same CTE:
`count(senses where 0.35 <= p_known <= 0.65) / count(senses)`, i.e. reward
tests whose *composition* concentrates senses near the BKT decision boundary,
not just tests whose *aggregate* unknown-rate matches a target. This is a
small, additive change to `recommended_tests_ranked`
(`migrations/task780_selection_combine_mode.sql:147-391`), not a new
subsystem.

**Migration path**: add a third term `f(t) = w_focus · (1 − focus_share(t))`
to the existing `score(t) = e(t) + v(t)` sum (or the same algebraic
`sum`/`product` choice already tunable via `selection_tuning.combine_mode`).
`w_focus = 0` reproduces today's behavior exactly, matching the project's own
established rollback pattern (`vocab_weight=0` reproduces pre-TASK-748
behavior byte-for-byte, per `tests/sql/test_task748_parity.sql`).

**Cold start**: `p_known` defaults to 0.10 with no BKT row
(`user_vocabulary_knowledge` schema, `recon-data-surface.md` §1) — this
already exists and needs no new handling; `focus_share` for a brand-new
learner will read "everything is far from 0.5" until enough attempts land,
which is the same cold-start shape the existing `unknown()` term already has.

**n=1 validation problem**: with `n_learners=1` (`design-00` §4), any A/B on
`w_focus` has a sample size of one person's history. The existing
`scripts/measure_selection_quality.py` replay mode (M1-M5, §7 of
recon-serving) is the only honest validation instrument available — it
replays *historical* attempts under alternate scoring arms, which at least
uses real behavioral data rather than synthetic fixtures, but it is still one
learner's idiosyncratic history. **Kill metric**: `M1 on-target rate`
(60-85% first-attempt band) under the `w_focus`-enabled replay arm vs. the
current `sum` arm — if it does not improve M1 relative to `sum` on the same
replay, `w_focus` adds ranking complexity for no measured benefit and should
not ship. **Negative result looks like**: M1 unchanged or worse, and/or M5
(pool health, candidate count per type) shrinking — the latter would violate
the project's own standing invariant (`recon-serving.md` §2, "pool never
shrinks").

---

## S2 — Item-level IRT with a guessing parameter (3PL, c=1/k)

**Bucket: (a) partially — 2PL IRT is live (`services/irt/calibrator.py`,
`exercises.irt_difficulty/irt_discrimination`), but for ladder exercises via
`get_practice_session`, not for comprehension tests via
`get_recommended_tests`; and it is **2PL, not 3PL** — no guessing parameter
exists anywhere in the live schema or calibrator.**

### Why ELO cannot be rescued by raising K (precise restatement)

ADR-024 already derives this exactly, and it is worth restating in full
because it is the strongest, most quantitative piece of reasoning in either
recon: a multiple-choice test has a chance floor `s_floor` (e.g. 0.25 for
4-option MC). At equilibrium, a learner who truly knows nothing still scores
`s_floor`, not 0, so the ELO expectation function
`expected = 1/(1+10^((test_elo-user_elo)/400))` settles at
`expected = s_floor`, which inverts to a **fixed gap**:

```
gap = 400 · log10(1/s_floor − 1)
    = 400 · log10(1/0.25 − 1)
    = 400 · log10(3)
    ≈ −191 points
```

This gap depends only on `s_floor`, not on K. **K controls how fast a rating
*approaches* its equilibrium, not *where* the equilibrium is.** Raising K
makes a learner's rating swing further per attempt (more variance) around a
fixed point that is already wrong by construction — it cannot move the fixed
point itself, because the fixed point is a property of the scoring function
(percent-correct against a chance-inflated floor), not of the update
rule. This is precisely ADR-024's own rejection of "raise K"
(`ADR-024:136-138`, quoted verbatim in recon-serving §4) and the arithmetic
above is the same formula the live audit used to derive the observed
88-point assigned band against a 448-point true ability spread for one
real ja learner (ADR-024 §Context point 2).

### Why IRT's guessing parameter `c` can fix what K cannot

A 3PL item response function is `P(correct|θ) = c + (1-c)/(1+exp(-a(θ-b)))`.
Setting `c = 1/k` (k = number of MC options, so `c=0.25` for 4-option MC)
makes the *model itself* account for the chance floor as a per-item
parameter rather than letting it distort the *ability estimate*. Where ELO's
percent-correct is chance-inflated and that inflation leaks into the rating
(the −191 gap above), 3PL's likelihood function explicitly subtracts the
guessing contribution when inferring θ: a correct answer on a 4-option item
by someone with low θ is explained as "guessed correctly" (probability mass
assigned to `c`) rather than as evidence of higher ability. **This is a
structural fix, not a tuning fix** — it changes what an "equilibrium" score
of `s_floor` *means* to the estimator (chance, not ability) rather than
changing how fast the estimator moves.

**What already exists**: the live 2PL calibrator
(`services/irt/calibrator.py:9-13,72-110`) fits `(a, b)` per exercise from
`user_exercise_history` via `sigmoid(a(θ-b))`, with a Bayesian shrinkage
prior toward a tier-seeded `b_seed` (`PRIOR_PSEUDOCOUNT=10`) and clamps
`a∈[0.3,3.0]`, `b∈[-3,3]`. **Extending to 3PL** means: (1) add a `c` column
(`irt_guessing`, defaulting to `1/k` per item's actual option count — a
one-line migration, not a new subsystem, since `exercises.content.options`
already carries option count for every MC type); (2) change
`_neg_log_likelihood`/`_neg_log_likelihood_grad`
(`calibrator.py:55-69`) to the 3PL form; (3) either fix `c` at `1/k` (simpler,
avoids the well-known 3PL identifiability problem where `a`, `b`, and `c` can
trade off against each other with too little data) or fit it with a tight
prior centered on `1/k` (more correct, needs more data per item to be
stable). **Recommend fixing `c=1/k`** given the data volume constraint below
— this is the practical, low-risk version of "3PL," not full unconstrained
3PL fitting.

### Cold start and the n=1 problem, sharpened

The calibrator's own default `DEFAULT_MIN_ATTEMPTS = 20`
(`calibrator.py:47`) means **no exercise item calibrates (2PL or 3PL) until
20 first-attempts accumulate on it**. With `n_learners=1`
(`design-00` §4), **zero exercise items can reach 20 attempts from organic
traffic in any realistic timeframe** — this is not a future risk, it is the
present state: the practice-unified-score doc's own cold-start table
(`practice-unified-score.tech.md` §"Cold-start handling") already documents
that uncalibrated items fall back to `a=1.0, b=0.0` and states this is
"correct behavior pre-calibration" — which today means **all behavior**, for
every item, since n=1 cannot produce 20-attempt-per-item calibration. **This
is the sharpest instance of the n=1 validation problem in this whole
document**: 3PL-vs-2PL is a real, well-motivated theoretical improvement that
**cannot be empirically validated at all against live LinguaLoop traffic
today**, only against synthetic/simulated response data or against the
existing 20-attempt-ja-type replay data ADR-024 mentions elsewhere
("no (language, type) has more than 8 first attempts,"
`recon-serving.md` §6.2) — which is itself below the calibrator's own
20-attempt floor.

**Kill metric**: this cannot be `M1`-style live A/B at current traffic.
The honest metric is a **simulation study**: generate synthetic response
data from a known 3PL ground truth (θ, a, b, c all specified), fit both 2PL
and 3PL calibrators against it, and measure `|b_fit − b_true|` and the
downstream ability-estimate bias each model produces under a chance floor —
this reproduces the ADR-024 −191-point calculation as an *empirical*
recovery test rather than a closed-form one. **Negative result**: if 3PL's
fitted `b` is *not* measurably closer to `b_true` than 2PL's under a
simulated chance floor (i.e. the identifiability problem dominates even with
`c` fixed at `1/k`), the added parameter and migration complexity isn't
earning its keep, and the simpler fix — using `c=1/k` as a **closed-form
post-hoc correction to already-fitted 2PL difficulty** (subtract the known
chance-floor bias analytically, no new likelihood function) — should be
tried first, since it requires zero new calibration code.

---

## S3 — Expected-learning-gain knapsack

**Bucket: (b), genuinely new for both surfaces**, though `build_daily_session`'s
existing greedy knapsack (`migrations/word_upload_slot_scheduling.sql:140-158,
344-408`) is real infrastructure to extend, not replace.

### Exact current objective, restated

```
per_min_value(skill) = skill_value(skill) / test_time_estimate(skill)
spacing_cost(skill)  = γ(=0.15) · (count of skill in last 3 chosen) / 3
objective += per_min_value·mins − spacing_cost      -- test/surface side
objective += per_min_value·mins                     -- maint/acq side, no spacing cost
```

(`recon-serving.md` §2, `word_upload_slot_scheduling.sql:140-158`).
`skill_value` is not shown in recon as an explicit formula distinct from the
per-candidate `score()` used in `recommended_tests_ranked` — treat
`skill_value(skill)` as the aggregate desirability of a skill's currently
available candidates, separate from `score(t)`'s per-candidate ranking within
a skill.

### Proposed replacement term: expected Δp_known per minute

```
expected_gain(candidate) = P(correct | θ_user, item) · learn_rate
                          + (1 − P(correct | θ_user, item)) · slip_rate
```

using the **existing** per-family BKT rates already defined in
`config.py:186-190` (`FAMILY_BKT_RATES`, e.g. `standard: {learn:0.15,
slip:0.12}`) — this is not new data, it's an existing constant currently used
only for post-attempt BKT updates, repurposed here as a **pre-attempt
expected-value estimate**. `P(correct|θ_user, item)` is exactly the IRT term
S2 already computes (`practice-unified-score.tech.md`'s `norm_irt`
Fisher-information calculation reuses the same sigmoid). Then:

```
per_min_value(candidate) = expected_gain(candidate) / test_time_estimate(candidate)
```

replaces `skill_value(skill)/test_time_estimate(skill)` as the ranking
statistic feeding the same greedy loop — **the knapsack structure itself
(TASK-710's single consolidated greedy pass, per project memory) does not
change**, only what "value" means per candidate.

### Why this is better-motivated than `|elo diff| + |unknown diff|`

The current objective (`e(t) + v(t)`, ADR-024) rewards candidates *near* the
learner on two axes but has no notion of *how much the learner would learn*
from attempting it — a test at the perfect ELO/vocab match could still teach
almost nothing if its senses are all things the learner already knows at
p_known=0.95 (BKT ceiling — `slip_rate` still applies, so *some* gain exists,
but `expected_gain` correctly scores it near-zero, whereas the current
`v(t)` term treats "matches the target unknown rate" as an end in itself
even when the match is achieved by senses that are individually
uninformative). This is the standard "expected information gain" framing IRT
selection theory already uses for `irt_information` (Fisher information
peaks where `P(θ)=0.5`, i.e. maximal uncertainty) — S3 generalizes the same
idea from "informative for calibration" to "informative for learning,"
which are related but not identical objectives (Fisher information is about
*measuring* ability precisely; `expected_gain` is about *changing* p_known
efficiently — a subtle but real distinction worth keeping separate in any
implementation, since they can disagree, e.g. a very easy item is
uninformative for calibration but can still deliver real spaced-repetition
consolidation value that a pure Fisher-information objective would
undervalue).

**Migration path**: `w_expected_gain=0` should reproduce
today's `per_min_value` exactly by falling back to `skill_value` unchanged —
same rollback discipline as `vocab_weight`/`combine_mode`.

**Cold start**: `expected_gain` needs `θ_user` (from IRT — itself cold at
`a=1,b=0` per S2) and `p_known` (defaults to 0.10). Cold-start behavior
degrades gracefully to whatever S2's cold IRT defaults produce, which is
already specified and already the live behavior for `get_practice_session`.

**n=1 validation**: same instrument as S1 — `measure_selection_quality.py`
replay mode, extended with a new metric `M6: realized_gain` = observed
Δp_known per minute of the *actually chosen* items vs. a counterfactual
uniform-random selection over the same candidate pool, computed from
historical attempt data. **Kill metric**: `M6` under the expected-gain arm
must exceed `M6` under the current arm on the same replayed history.
**Negative result**: if `M6` is statistically indistinguishable (n=1's history
is short enough that this is plausible), the added complexity is unproven and
should stay behind a weight-0 flag rather than becoming the default.

---

## S4 — Computed per-type difficulty

**Bucket: (b)/(c) — genuinely new, and specifically targets the
comprehension-test defect (#2 in recon-serving §6), which is a **content
seeding** problem, not a selection problem, per ADR-024's own "known limit"
section.**

### The defect, precisely

`build_daily_session`/test generation seeded `test_skill_ratings` from prose
complexity at generation time (TASK-732), which has no way to know whether a
test's *task* is reading, dictation, or pitch-accent recognition — so 48 of
60 live ja tests carry **one ELO value across all 8 test types**
(ADR-024 §Context, quoted in `recon-serving.md` §4). The measured
consequence: one learner's *true* ability spans 448 points (pitch accent
~1091, dictation ~1539) compressed into an 88-point assigned band
(1182-1270), with reading/listening/dictation under-rated and only pitch
accent over-rated — net effect, "ja is mostly too easy," despite pitch accent
*feeling* broken because 6/7 attempts scored under 50%.

### Proposed fix: derive per-type difficulty from features, not from a single seeded prose score

```
difficulty(test, type) = f(zipf_percentile(test.vocab_sense_ids),
                            sentence_length_percentile(test),
                            distractor_cosine_margin(test, type),   -- G1's
                                                                     -- embedding
                                                                     -- band, reused
                            phonetic_confusability(test, type))     -- ja pitch/
                                                                     -- mora
                                                                     -- specific
```

This is explicitly a place where **G1's generation-time infrastructure
(embedding-band distances, phonetic-trie confusability scores) becomes a
serving-time input** — the two halves of this document set share a real data
dependency here, not just a thematic one. A pitch-accent test's difficulty
should be driven by *mora-level confusability* (already computed
deterministically by `services/pitch_accent_service.py`, `recon-data-surface.md`
§1), which a prose-complexity score structurally cannot see — this is
exactly ADR-024's own diagnosis of the root cause, restated as a concrete
feature-engineering fix rather than left as a "needs a per-type ELO reseed"
TODO (ADR-024's own text: "Better selection cannot fix pitch accent on its
own, because the type-blind test ELO is a *content seeding* defect").

**Migration path**: this is a **content re-seeding job**, not a selection
migration — re-derive `test_skill_ratings` per (test, test_type) from the
feature formula above, backfilled once, then feed forward at generation time
for new tests. Existing selection (`get_recommended_tests`,
`build_daily_session`) needs no formula change once `test_skill_ratings` is
correctly per-type — this is the one S-design that fixes its target defect
by improving the *input data* rather than the *ranking formula*, and should
be sequenced accordingly (see `design-04`): it does not compete with S1-S3
for the same code path.

**Kill metric**: re-run `measure_selection_quality.py`'s M3 (compression
metric — spread of implied ability vs. spread of live per-type rating) after
the reseed. **Target**: M3's gap should shrink materially from the documented
448-vs-88 ratio. **Negative result**: if M3 does not close, either the
feature set is missing the actual driver of difficulty (plausible for pitch
accent specifically — mora confusability might not be the dominant factor;
audio quality, speech rate, or unfamiliar vocabulary co-occurring with the
tested mora could dominate instead) or per-type ELO genuinely needs the
"per-type reseed" TASK-751 already proposed and currently blocked on the
same n=1 data sparsity ("no (language,type) has more than 8 first attempts,"
`recon-serving.md` §6.2) — in which case S4's feature-based approach is
strictly better *because* it does not require live attempt data to seed
correctly, unlike a reseed-from-attempts approach.

---

## S5 — Ladder/transfer-ordered progression

**Bucket: (a), already substantially implemented, though not exactly as
S5 frames it.**

The ladder already sequences levels through 4 rings from
`form_recognition` (R1) through `meaning_recall`/`form_production`/
`collocation` (R2) to `semantic_discrimination` (R3) and back to
`collocation`/`form_production` at higher difficulty (R4) — this **is**
recognition→production sequencing, gated by explicit thresholds
(`GATES`, `config.py:132-151`: gate_a requires `min_p_known=0.72` AND
`require_production=True` before unlocking R3; gate_b similarly before R4).
`get_practice_session`'s Acquisition mode is explicitly **word-anchored, one
ring's required families at a time** (`ADR-007` §Decision), which is
precisely "sequence exercise types per sense along recognition→production,"
already shipped.

**What's genuinely open**: the thesis's framing — "rather than treating
types as interchangeable" — is a real critique of a *different* surface: the
**Maintenance mode** pool in `get_practice_session` ranks candidates by the
unified score **across all due/decayed senses and all their available
types**, with no ring/family sequencing constraint (`practice-unified-score.tech.md`
§"Candidate pools per mode," Maintenance row) — post-mastery review
genuinely does treat types as interchangeable, by design (`MAINTENANCE_FAMILY_WEIGHTS`,
`config.py:273-280`, is a flat weighting, not a sequence). Whether that's a
defect or a correct design choice depends on the pedagogical claim being
made: for **acquisition**, transfer-appropriate-processing theory supports
strict sequencing (a learner who hasn't yet demonstrated recognition
shouldn't be drilled on production of the same item — the current gates
already enforce this). For **maintenance**, once mastery is reached, the
learning-science case for continued strict sequencing is weaker — the
relevant literature here is closer to "interleaved practice" (Rohrer &
Taylor 2007), which argues *for* mixing item/skill types during review
precisely because interleaving (vs. blocking by type) improves long-term
retention and discrimination, i.e. the current flat-weighted Maintenance
pool may already be closer to the pedagogically correct answer than a
S5-style enforced sequence would be for that mode specifically.

**Recommendation**: do not add sequencing constraints to Maintenance mode —
the interleaving literature argues against it. Do audit whether Acquisition
mode's existing gate/ring sequencing is being *bypassed* anywhere (e.g. by
`get_recommended_tests`-sourced comprehension tests serving a
`ladder_level`-agnostic mix of question types that happen to touch a sense
mid-ladder — this cross-surface interaction between the two selectors named
in §0 was not traced in either recon and is a genuine gap: **UNVERIFIED**
whether a comprehension test's vocabulary-context questions can expose a
learner to production-level use of a sense still gated below gate_a in the
ladder).

**Kill metric**: `cross_surface_gate_violation_rate` — the fraction of
comprehension-test exposures to a sense that involve a cognitive demand
(e.g. active recall/production, per `question_type_id`) exceeding what the
learner's ladder `gates_passed` state for that sense would currently permit
if it were a ladder item. This metric does not exist today and would need to
be built from `dim_question_types` + `user_word_ladder` joined against
`tests.vocab_sense_ids` — flagged as the actual open work item under S5,
rather than "add sequencing," which is largely already done.

---

## Summary: what's live, what's new, per S-design

| | Live today (where) | New work required |
|---|---|---|
| S1 | BKT/FSRS in `get_practice_session` unified score | Add a focus-share term to the **test** selector only |
| S2 | 2PL IRT (`calibrator.py`, `get_practice_session`) | Extend to fixed-`c` 3PL; validate via simulation (n=1 blocks live validation) |
| S3 | Greedy knapsack structure (`build_daily_session`) | New `expected_gain` value function replacing `skill_value` |
| S4 | Nothing — genuinely new | Feature-based per-type difficulty re-seed, reusing G1's embedding/phonetic infra |
| S5 | Ring/gate sequencing (Acquisition mode) | Audit cross-surface gate bypass; do NOT add sequencing to Maintenance (interleaving literature argues against it) |

The n=1 learner problem (`design-00` §4) is the binding constraint across
S1-S4: every kill metric above either falls back to the existing
replay-based `measure_selection_quality.py` instrument (real but
single-history) or, for S2 specifically, requires a synthetic simulation
study because the live data cannot reach the calibrator's own 20-attempt
floor. No S-design in this document should be presented as "validated" on
the strength of live-traffic numbers until `n_learners` grows well past 1 —
this is stated once here as the governing caveat for the entire document
rather than repeated in every section's kill-metric.
