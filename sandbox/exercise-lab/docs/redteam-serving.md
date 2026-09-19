# Red team: S1-S5 vs the live vocabulary-aware/ELO serving stack

Adversarial review, 2026-09-17. Read-only against recon-serving.md and the
artefacts it cites, plus `wiki/decisions/ADR-002-bkt-per-sense.md`,
`migrations/phase11_irt_selection.sql`, `migrations/add_irt_calibration_metadata.sql`,
`services/irt/calibrator.py`, `scripts/measure_selection_quality.py:1-53`,
`migrations/word_upload_slot_scheduling.sql`. No writes outside this file, no
DB queries, no LLM calls.

## Headline finding recon did not have

**LinguaLoop already built and shipped S2, one level down, and it is evidence
against S2, not for it.** `migrations/phase11_irt_selection.sql` (2026-05-12,
"Phase 11 — IRT-aware selection", status "Live" per
`wiki/algorithms/ladder-implementation-analysis.tech.md:421`) is a nightly
2PL MLE IRT fit (`services/irt/calibrator.py`, scipy L-BFGS-B) over
`exercises.irt_difficulty`/`irt_discrimination`, feeding a Gaussian-weighted
term into `get_exercise_session`. Two facts from that code kill most of the
optimism in S2:

1. **It is 2PL, not 3PL — no guessing parameter exists in the live schema**
   (`create_all_tables.sql:509-510`, `exercise_generation_schema.sql:53-54`:
   only `irt_difficulty`, `irt_discrimination`). The team that built the only
   IRT system in this codebase looked at exactly S2's problem (MC items) and
   did not add `c`. That's not proof `c` is wrong, but it is a specific,
   documented precedent for "we tried IRT here and stopped short of 3PL,"
   and the proposal should say why this time is different.
2. **`DEFAULT_MIN_ATTEMPTS = 20` per item, hard-coded**
   (`services/irt/calibrator.py:47,271`), and item calibration is *skipped
   entirely* below it — `get_exercise_session` falls back to a flat weight of
   1.0 (`phase11_irt_selection.sql:166-172`), i.e. **no-op**, precisely to
   avoid corrupting selection with a garbage fit. This is the same team's own
   answer to "how much data does item-level IRT need here," on a *larger,
   less sparse* item pool (exercises are practiced repeatedly; tests are
   filtered to never-attempted). Given the exercise pool is orders of
   magnitude larger than 21-ish first attempts and this codebase still
   gates calibration at 20/item, the honest prior for test-level 3PL is
   that it fits **zero items** today, exactly like exercise-level IRT most
   likely does. This should be checked (`SELECT count(*) FROM exercises
   WHERE irt_calibrated_at IS NOT NULL`) before anyone treats S2 as buildable
   — a check this review could not run under its no-DB-query constraint, and
   which the proposal owes before estimating S2's cost.
3. **`wiki/algorithms/practice-unified-score.tech.md:53`** already carries the
   2PL Fisher information formula (`I(θ)=a²P(θ)(1−P(θ))`, max `0.25a²` at
   `b=θ`) in this wiki. Whoever writes S2 should extend that page, not start
   a parallel derivation — and should notice its own codebase already knows
   Fisher information saturates and never asks what happens with `c>0`.

This means S2 is not "introduce IRT to LinguaLoop" — it's "port a live,
already-gated, already-data-starved subsystem to a second, sparser domain,
and add the one axis (`c`) the original implementers declined to add." That
reframing should change how the proposal is scoped and reviewed.

---

## Verdicts by axis

| # | Axis | Verdict |
|---|------|---------|
| 1 | n=1 problem | **FATAL** (for S1/S2 as stated; S3/S4/S5 partially escape it) |
| 2 | IRT vs ELO maths | S2's specific claim ("c escapes the 191-pt cap") is **WRONG as stated**; the underlying idea (unbias the estimator) is **real but oversold** |
| 3 | Cold start | S1: **SERIOUS** (aggregation undefined); S2: **MANAGEABLE** (mirrors existing safe pattern); S4: **MANAGEABLE**; S5: **NOT A PROBLEM** on its own |
| 4 | BKT + forgetting coherence | **SERIOUS** — buildable only if scoped as two parallel signals, not one model; proposal doesn't say which |
| 5 | Gaming the objective (S3) | **SERIOUS** — at least three concrete degenerate policies, none of which the proposal text constrains |
| 6 | Regression risk of stacking | **SERIOUS** — a same-day, behaviourally-verified flip is not a base to build S1-S5 on; the parity-test pattern doesn't scale to any of them as stated |
| 7 | Measurement validity (M1-M5) | **SERIOUS** — M1-M5 are targeting/distributional, not learning-outcome, metrics; S1-S5 can improve all five while teaching less |
| 8 | Simulator trap | Real risk, not fatal, **if and only if** the report's constraints (below) are followed |
| 9 | What's right | S3's economic framing and S4's difficulty features are the strongest parts of the whole package |
| 10 | Strongest alternative | Fix the seeding defect (48/60 shared ja ELO) and the 17-22% unlinked-test gap before touching the model family |

---

## 1. The n=1 problem — quantified, and it is worse than "unfittable," it's structurally self-defeating

**Numbers, from the artefacts themselves (no DB query needed):**
- 14 users total, exactly 1 (`de6fd05b…`) has ever completed a test
  (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md:112-115`).
- That learner: 21 first ja attempts (`ADR-024:16`, matching the replay's
  "21 first attempts, 210 top-10 slots" at `evaluations/...:44`), plus some
  zh attempts (Spearman is computed over a zh+ja pool). En: **zero** attempts.
- Test catalogue: ja 59, en 121, zh 125 active tests (`ADR-024:44-45`,
  `recon-serving.md:185`). So even generously assuming 21 ja attempts spread
  across 59 ja tests, **the maximum possible attempts on any single ja test
  is 1**, because `get_recommended_tests` filters out already-attempted
  tests unconditionally (`recon-serving.md:106`, "never-attempted by this
  user+type") and the only repeat paths — `retry` (≤1/day, only for sub-70%
  scores) and `replay` (only fills shortfalls, ≥7 days old) — are capped and
  rare by design (`recon-serving.md §3`).

**This is the structurally self-defeating part, and it's the strongest
version of the objection:** IRT/BKT calibration needs *repeated observations
per item*. The serving policy under attack (never re-serve an attempted
test) exists specifically to maximize content coverage and avoid staleness
— and it guarantees that no test will ever accumulate more than a handful of
observations from any one user, and there is exactly one user. You cannot
fix this by "waiting for more data" under the current serving policy,
because the policy itself is the reason exposure per item stays at n≈1
forever, for every user, individually — it's not solved by 100 more users
either, unless many of them independently attempt the *same* items, which
never-repeat-by-design actively works against per learner (each learner
still gets ≤1 exposure per item; only pooling *across* users helps, and that
requires the population to grow, not just time). This is the same
data-starvation the codebase already lives with for the exercise ladder,
and it's why `services/irt/calibrator.py` gates at n≥20/item and reports
`fitted=0` rather than fitting garbage.

**BKT per-sense (S1):** `user_vocabulary_knowledge` already exists and
already updates (`migrations/bkt_vocabulary_tracking.sql`,
`phase7_bkt_improvements.sql`, `phase8_momentum_bands.sql`,
`phase10_ladder_advancement_demotion.sql` all touch it) — so S1 is not
"introduce BKT," it's "add per-sense *scheduling* on top of an
already-running per-sense tracker." That's a meaningfully smaller ask than
S2, and the honest minimum-data path for S1 is close to already met:
p_known already exists per sense for the one active learner. The FSRS-lite
forgetting-curve half of S1 is a separate ask with its own data requirement
(inter-exposure intervals per sense, which barely exist yet given one
learner's short history) — **S1 should be split**: the scheduling-on-p_known
half is buildable now; the forgetting-curve half is not, for the same
reason IRT isn't.

**Honest minimum-data path, in priority order:**
1. Ship the scheduling half of S1 alone (rank by distance from a p_known
   threshold, no forgetting curve) — data exists today.
2. Do not attempt S2 or the forgetting half of S1 until either (a) the user
   base grows enough that *some* items cross a 15-20 response threshold — the
   number this codebase already uses for exercise IRT — or (b) the serving
   policy itself changes to deliberately allow bounded re-exposure for
   calibration purposes, which is a direct trade against the "never stale,
   maximize coverage" design intent and should be named as a real cost, not
   waved through.
3. Track `exercises.irt_calibrated_at IS NOT NULL` count monthly as the
   go/no-go gate for ever starting S2 — it is the one number that would
   falsify "this is unfittable" if it turned out to be large.

**Verdict: FATAL for S2 and the forgetting-curve half of S1, as proposed,
today. Not fatal for the scheduling half of S1, S4 (item features, not
population data), or S5 (a sequencing rule, not a fitted model).**

---

## 2. IRT vs ELO — the maths, and why S2's crux claim is wrong as stated

**3PL model:** `P(θ) = c + (1-c)·Ψ(a(θ-b))`, `Ψ` = logistic, `c` = guessing
floor (`1/k` for k-option MC).

**Fisher information for 3PL** (standard result, e.g. Lord 1980; reduces to
the 2PL formula already in `practice-unified-score.tech.md:53` at `c=0`):

```
I(θ) = a² · [(P(θ) − c) / (1 − c)]² · [(1 − P(θ)) / P(θ)]
```

Check: at `c=0`, `(P-c)/(1-c) = P`, giving `I(θ) = a²·P·(1-P)` — matches the
wiki's own 2PL formula. Good.

**What this formula says as `θ → -∞` (learner far below item difficulty):**
`Ψ(a(θ-b)) → 0`, so `P(θ) → c` and `(P(θ)-c) → 0`. Both factors in the
bracketed term vanish, so **`I(θ) → 0`** — item information collapses to
zero for any learner sufficiently below the item's difficulty, guessing
parameter or not. This is the crux, and it is not a subtle point: **3PL does
not create information where none exists in the response.** A multiple-choice
item literally cannot distinguish "knows nothing, guessed right" from "knows
a little, guessed right" once you're deep enough below threshold, no matter
what curve you fit to the guess rate — because the *data itself* (right/wrong
against a k-way guess) carries almost no bits about θ down there. This is
computer science, not modeling choice: you can't extract information a
binary-with-a-floor response never contained.

**So what does `c` actually buy you, and is it real?** Yes, real, but it is
a **bias fix, not a range fix**. ELO's implicit expected-score model
(`1/(1+10^(Δ/400))`) has *no floor at all* — it assumes `P→0` as `Δ→-∞`.
Real MC score data can't go below `~c` on average. So whenever a learner's
true ability sits far enough below an item that ELO expects near-0% but the
data floors at `c` (25% for 4-option), ELO's update treats the observed
25% as *better than expected* and pushes the rating **up**, toward the point
where ELO's own un-floored formula predicts exactly 25% — which is precisely
the `400·log₁₀(1/s-1)` equilibrium at `s=c` that ADR-024 already derives as
"-191 points" (`ADR-024:31-36`). **That number is not a coincidence — it is
the point where ELO's model finally agrees with the floor it doesn't know
exists.** A correctly-specified 3PL avoids this specific bias, because `c`
is a term in the model, not an artifact the fit has to explain away by
distorting `θ` and `b`. That's a legitimate, useful property: 3PL should
produce *less biased* difficulty and ability point estimates near the floor
than ELO does.

**But "less biased" is not "more resolving."** A learner scoring exactly at
`c` on an item still produces an MLE for `θ` with enormous standard error
under 3PL — the likelihood is nearly flat below `b`, so the *estimate* is
honest about not knowing, whereas ELO's random-walk update silently commits
to a specific number and keeps it there. **The honest framing of S2's payoff
is: 3PL replaces a confidently-wrong number with an honestly-wide interval.
It does not let you tell two low-ability learners apart.** If the actual
complaint is "the ~191-point compression makes the system think everyone
below the floor is the same," 3PL does not fix that complaint; it just stops
pretending otherwise.

**Are ELO and 3PL "equivalent up to reparameterization" here?** No — and
it's worth being precise about why not, since the prompt asks for a blunt
answer either way. Un-floored ELO and floored 3PL are different models of
the *same latent construct*; the population of θ values consistent with a
given ELO rating and the population consistent with a given 3PL θ estimate
are not the same distribution once any data sits near/below the floor,
because ELO has silently smeared floor-driven variance into the ability
estimate itself while 3PL keeps it in the standard error. So: **not
equivalent — genuinely different, and 3PL's version is more honest** — but
the practical payoff is a calibration-quality improvement (less bias,
correct uncertainty), not the range-extension the proposal claims.

**The real fix, and the codebase already contains evidence for it:**
ADR-024's own data shows dictation — a **free-response, non-MC format with
no chance floor** — is the type where this learner's *true* ability is
highest and least compressed (dictation ~1539 vs pitch accent ~1091, inside
ADR-024's own 448-point true-spread claim, `ADR-024:24-26`). That's not a
coincidence either: the format without a guessing floor is the one format
where ELO already expresses more of the real spread, with **zero model
changes**. If the actual goal is "stop losing ability information to the MC
floor," the evidence in this repo's own decision record points at **format
diversity** (more constructed-response/production items, an item type S5's
recognition→production ladder would also push toward) ahead of any change
to the scoring model. This is the single strongest piece of evidence in this
review, and it comes from a document (ADR-024) already cited by the
proposal's own author.

---

## 3. Cold start

**Current system's documented safety property:** neutral degradation —
unlinked/uncalibratable candidates get the **median raw penalty of their
cohort**, never 0 (would always-win) or +∞ (would empty the pool)
(`recon-serving.md:103`, `ADR-024:59-62`). This is explicitly a "no
opinion" default, and the tier-ceiling rail demotes rather than excludes for
the same reason — the pool must never shrink (M5).

- **S2 (3PL):** the existing Phase-11 pattern already answers this
  correctly — cold items get flat weight (no-op), calibrated items get the
  Gaussian/3PL term (`phase11_irt_selection.sql:166-172`,
  `exercise-generation-v2.md:351`: "defaults a=1.0, b=0.0 until n≥20"). If
  S2 copies this pattern for tests, cold start is **MANAGEABLE** — it's a
  known-good shape in this codebase. Risk is only if S2's authors don't
  reuse it and instead build a second, divergent cold-start convention.
- **S1 (BKT+FSRS scheduling):** a brand-new sense has no retrieval-strength
  history. FSRS conventionally treats first exposure as "due now," which is
  fine at the *flashcard* grain (one card, one state). At the *test* grain,
  a test links many senses in mixed states (new, due, mastered,
  decayed) — the proposal never specifies how a multi-sense test's schedule
  value aggregates those states into one rankable number. `unknown(t)` in
  the current system solves the analogous problem for the *knowledge* axis
  with a defined mean over `S'`; S1 has no equivalent aggregation rule
  stated. **SERIOUS**, not fatal — it's a real design gap, not a proof of
  impossibility, but it must be resolved before implementation, and until it
  is, it's not clear the "pool never shrinks" invariant survives (a
  fresh-sense-heavy test could look maximally "due" under one aggregation
  and maximally "not due" under another).
- **S4 (per-type computed difficulty):** cold-starts the same way
  authoring-time difficulty already does (a formula over Zipf/length/cosine
  margin/confusability computed at generation time, no learner history
  needed) — this is **strictly better** cold-start behaviour than either
  ELO or S1/S2, because it needs zero response data at all. Degrades
  gracefully to "same as today" if any input feature is missing.
- **S5 (sequencing ladder):** doesn't estimate anything from data; it's a
  fixed policy (recognition before production per sense). No cold-start
  failure mode of its own — inherits whatever S1/S2's cold-start behaviour
  is for the underlying targeting, but the sequencing rule itself is
  **NOT A PROBLEM**.

---

## 4. BKT validity under an added forgetting curve

ADR-002 states current BKT is the textbook two-state model: **no forgetting
(mastery is absorbing), one latent skill per item, fixed slip/guess per
evidence type** (`ADR-002:15,23`). p_known is live and actively written
(`bkt_vocabulary_tracking.sql`, `phase7_bkt_improvements.sql`,
`phase8_momentum_bands.sql`, `phase10_ladder_advancement_demotion.sql`), so
this is a real, running signal, not a stub — good foundation.

**The incoherence risk is specific:** in vanilla BKT, once `p_known` crosses
into "known," the model's own transition matrix says it stays known — there
is no state for "known, but faded." If S1 makes `p_known` itself decay with
elapsed time, that directly contradicts the absorbing-mastery assumption the
same number is defined under, and every other consumer of `p_known`
(distractor-quality calibration, the vocabulary-aware ranker's `unknown(t)`
term) would start seeing a *different meaning* of the same column without
being told. That's a correctness bug waiting to happen across the whole
ranker, not just S1.

**The coherent way to do this** — which the proposal doesn't state but
should be required to before approval — is to keep `p_known` as BKT's static
mastery estimate and compute a **separate derived quantity** (retrievability,
à la FSRS) as a function of `p_known` and time-since-last-exposure, used only
for *scheduling*, never overwriting `p_known` itself. That keeps BKT's
semantics intact and treats FSRS as a second, independent signal layered on
top — two models running in parallel, not one hybrid model. Whether the
slip/guess parameters ADR-002 mentions were ever empirically fit (versus
hand-set constants) isn't verifiable read-only here, but with n=1 users it
is very unlikely they were fit from data — which matters, because a
retrievability layer built on an unfit BKT is compounding one
under-validated estimate with a second one.

**Verdict: SERIOUS, not FATAL.** Buildable, but only if scoped explicitly as
"two parallel signals" and the proposal currently reads as one hybrid model.
Ship the scheduling half of S1 (rank by `p_known` distance from a target
band, no decay) first — it's a smaller, coherent change that doesn't touch
BKT's semantics at all.

---

## 5. Gaming the objective (S3: greedy knapsack over expected Δp_known/min)

Three concrete degenerate policies, each with a required constraint the
proposal text does not currently include:

1. **Thrash on the cheapest almost-known item.** An item near `p_known≈0.5`
   scored quickly (short MC item) produces a bigger `Δp_known/min` than a
   genuinely hard, slow, valuable item (a long dictation on new vocabulary),
   *especially* if BKT's guess/slip parameters make small `p_known` moves
   easy to trigger on easy items. Left unconstrained, the greedy pass
   converges on serving lots of short easy items with fast probability
   churn. **Constraint needed:** a diversity/coverage floor per session (cap
   repeats of the same sense/type per session — the existing
   `spacing_cost` term in `build_daily_session` already does exactly this
   for skill mix, `word_upload_slot_scheduling.sql:115` — S3 needs the
   sense-level analogue, which doesn't exist yet).
2. **Avoid hard-but-important vocabulary.** Low-frequency, high-value senses
   (technical terms, low-Zipf) have low `p_known` and probably a *low*
   `Δp_known` per exposure too (harder to move), so a pure Δ-per-minute
   greedy pass systematically under-serves exactly the vocabulary a curriculum
   should prioritize. **Constraint needed:** a minimum-exposure guarantee per
   curriculum-priority sense, independent of measured Δ — i.e. the objective
   needs a value term that isn't purely "learnability," or it optimizes away
   from anything hard to learn.
3. **Optimizing the proxy, not the skill.** `Δp_known` is BKT's *model's*
   belief update, not ground truth — a system that maximizes its own belief
   update is, by construction, maximizing confidence in its own model, which
   is trivially gameable by serving items whose slip/guess parameters make
   `p_known` swing hardest (e.g., very easy items with low guess rate move
   `p_known` up fast on a correct answer) rather than items that produce
   durable knowledge. This is Goodhart's law applied directly to the
   selection objective. **Constraint needed:** validate `Δp_known`
   predictions against **held-out delayed re-tests**, not just against the
   next attempt on the same item — without that, the objective is
   unfalsifiable by construction (see axis 7).

**Verdict: SERIOUS.** None of these are exotic edge cases; they're the
default behaviour of a greedy per-minute-value objective without the
constraints above, and the current `build_daily_session` knapsack already
demonstrates the team knows to add anti-degeneracy terms (`spacing_cost`,
`γ=0.15`) — S3 needs the equivalent, not a bare Δ/min objective.

---

## 6. Regression risk of stacking on `vocab_weight`

**What actually happened today (2026-09-17):** `vocab_weight` was flipped
0→1 live, by an operator running a manual `UPDATE` because the agent's own
permission guard blocked it, verified **only behaviourally** (unlinked-test
count, non-monotonic `elo_diff`, pool size, latency) — not against a
pre-registered acceptance threshold, not over a shadow window despite the
evaluation doc explicitly recommending one
(`selection-three-arm-replay-2026-09-17.md:144-147`: "It is still one
learner's history, so the decision wants either the 7-day shadow window...
or a deliberate 'n=1 is enough'"). `wiki/tasklist/master.md` is a full day
stale relative to this (`recon-serving.md:192`). **This is a live change
resting on a decision the evaluation itself flagged as premature**, on a
population of one.

**What the parity test actually proves, precisely:** `test_task748_parity.sql`
proves that `vocab_weight=0` **byte-for-byte reproduces** the pre-TASK-748
function (`_grt_pre748`) for every user × language, and that `vocab_weight=1`
never shrinks per-type pool count (M5) — i.e., it proves **the rollback path
is safe and the new code doesn't break the old invariant**, for exactly the
two axes it was designed to check (`recon-serving.md:208-212`). It says
**nothing about whether the new ranking is *better*** — that's the
evaluation doc's job, and the evaluation doc itself says the decision is
premature.

**Can S1-S5 produce an equivalent parity proof?** Only partially, and it
gets structurally harder up the list:
- **S4** (computed per-type difficulty) is the *easiest* to parity-test: it
  changes `test_elo` seeding, not the ranker, so a parity test analogous to
  `test_task748_parity.sql` (does the new seed match some frozen baseline
  under a null hypothesis) is straightforward to write.
- **S1's scheduling half** could get a similar parity test (weight=0
  reproduces today's ranker) if built the same way ADR-024 built vocab_weight
  — as an additive term behind a tunable, defaulted to inert.
- **S2 and S3 cannot get an equivalent proof**, because there is no
  "byte-identical to the old function at weight 0" baseline to fall back
  to — they *replace* the scoring model, not add a term to it. The parity
  pattern this team relies on (`vocab_weight=0 ⟺ old behaviour exactly`)
  only works for **additive, switchable terms**, and S2/S3 as stated are not
  that shape. If S2/S3 are pursued, they should be reframed as one more
  additive, defaulted-to-0 term (the way ADR-024 did it) specifically so
  this team's own regression-safety pattern still applies — not as a
  wholesale replacement of the objective function.

**Verdict: SERIOUS.** Not "don't do it," but: no change should land on top
of today's unshadowed flip without (a) the shadow window the eval doc itself
asked for finally running, and (b) every subsequent change shaped as an
additive, defaulted-off term with its own parity test, exactly like
`vocab_weight` — never a wholesale objective-function swap, given the parity
tooling this team already trusts can't check a swap.

---

## 7. Measurement validity — M1-M5 measure targeting, not learning

Per `scripts/measure_selection_quality.py:9-24` (the docstring is
authoritative):
- M1 on-target rate: `60 < pct ≤ 85` on first attempts.
- M2 below-floor: `pct < 50`.
- M3 compression: spread of *implied* ability (inverted from `pct`) vs
  spread of the live rating.
- M4 served unknown: median `unknown(t)` over top-10.
- M5 pool health: candidate count.

**Every one of these is a function of (a) the score distribution on served
items and/or (b) the vocabulary-coverage distribution of served items.**
None measures retention, delayed recall, transfer, or any outcome measured
*after* the serving decision that isn't itself the next immediate score.
**A selector can trivially improve all five while teaching nothing more**:
serve items that produce scores in the 60-85 band and unknown-shares near
15% by construction (which is close to *definitionally* what S1-S4 all
optimize for), and M1/M2/M4 improve automatically, regardless of whether the
learner retains anything a week later. This is the textbook Goodhart failure
for an "on-target difficulty" metric: hitting the target band is the
selection *mechanism*, so measuring how often the band is hit measures
whether the mechanism ran, not whether it worked.

**The metric that would catch it, and doesn't exist yet:** a **delayed
outcome check** — re-test the same sense/skill after a fixed interval (e.g.
7-14 days) *without* it being freshly practiced in between, and compare
delayed accuracy against a pre-registered baseline (or against the
population that received a different serving policy). This is exactly the
kind of check `get_replay_tests`' `min_age_days=7` window already has the
raw data shape for (it looks at *previously-attempted* tests older than a
window) — the infrastructure to compute a delayed-recall metric largely
exists; it's just never been pointed at "did the earlier serving decision
predict later recall," only at "should this be re-served."

**Verdict: SERIOUS.** Any go/no-go decision for S1-S5 that cites M1-M5
improving is not evidence of a learning improvement. This applies with equal
force to the `vocab_weight` flip already live today — the 0.79→0.95
in-band number is a targeting metric, not a learning metric, a caveat the
evaluation doc itself does not make explicit.

---

## 8. The simulator trap

A synthetic-learner simulator is the right instinct given n=1, but it fails
in one specific, well-known way here: **the response model the simulator
author writes IS the conclusion.** If the simulated learner's probability of
a correct answer is generated from, say, a BKT+forgetting process, then a
selector built to target BKT+forgetting state will *necessarily* look best
in that simulation — the evaluation and the thing being evaluated share an
assumption, so the simulator can only confirm the model family it was built
to represent, never falsify it. Concretely here: if S1's simulator generates
responses via an FSRS-consistent decay process, S1 (which schedules against
FSRS-modeled decay) will "win" against the ELO/vocab-share baseline (which
doesn't model decay at all) *by construction*, independent of whether real
LinguaLoop learners forget the way the simulator assumes.

**What would make simulator results trustworthy:**
1. **Multiple, disagreeing response models**, at minimum one that matches
   each proposal's assumption and at least one adversarial one that
   deliberately violates it (e.g., a learner whose forgetting is
   context-dependent rather than a clean exponential, or one whose slip rate
   varies by fatigue rather than being fixed) — a selector that only wins
   under its own model's simulator is not evidence of anything.
2. **Calibrate the simulator's parameters against the one real learner's 21
   ja + zh attempts** before trusting any relative ranking between arms —
   otherwise the simulator's absolute numbers (and possibly its qualitative
   ranking) are unconstrained by the one dataset this system actually has.
3. **Report simulator results as "these selectors were compared under
   assumption X," never as "selector A improves learning."**

**Claims that must never be made from simulation alone:** any claim of the
form "S1/S2/S3 improves real learner outcomes," any specific numeric
improvement percentage carried into a product decision, and any claim that a
simulator result generalizes across languages the simulator wasn't
separately calibrated for (en has zero real attempts to calibrate against at
all — a simulator for en is unconstrained by any real data whatsoever, which
should be stated loudly, not buried).

**Verdict: real risk, not fatal**, contingent on the three constraints above
being followed rather than treated as caveats to mention once and ignore.

---

## 9. What the proposal gets right

Being fair, in priority order:

1. **S3's economic framing (value per minute) is the correct generalization
   of what `build_daily_session` already does.** `per_min_value = skill_value
   / test_time_estimate` already exists as a greedy knapsack objective
   (`word_upload_slot_scheduling.sql:140-158,289-298`) — S3's idea is
   "replace the static per-skill `skill_value` constant (default 0.10,
   `word_upload_slot_scheduling.sql:293`) with a computed, per-item learning
   value." That's a real improvement in kind, not a new architecture — it
   slots into infrastructure already proven stable (TASK-710's fixture-matrix
   proof that the greedy pass is deterministic and correct).
2. **S4 (computed per-type difficulty) is the lowest-risk, highest-leverage
   item in the whole package.** It needs no learner-response data at all
   (Zipf, sentence length, distractor cosine margin, phonetic confusability
   are all computable at authoring time), it directly attacks documented
   defect #2 (48/60 ja tests share one ELO because seeding used prose
   complexity, not task type — `ADR-024:19-21`, `recon-serving.md:183`), and
   it has a trivial parity/regression story (compare new seed distribution
   to old, offline, before touching the live ranker).
3. **Fixing `c=1/k` as a known constant rather than fitting it (S2)** is the
   statistically correct call given the data volume — 3PL guessing
   parameters are notoriously unidentifiable when fit freely from small
   samples, and the proposal doesn't try to fit it. Credit for getting this
   one detail right even though the surrounding claim (axis 2) is oversold.
4. **S5's recognition→production sequencing** is a genuinely orthogonal,
   low-risk idea — it's a fixed pedagogical policy, not a fitted model, so it
   inherits none of the n=1 problems above and could ship independent of
   S1-S4 entirely.
5. **The instinct to target BKT's existing `p_known` more directly** (S1) is
   sound in spirit — ADR-024 itself already flags that `user_vocabulary_
   knowledge` is read only in aggregate (`unknown(t)`'s mean), never as a
   standalone per-sense targeting signal (`recon-serving.md:171`). Using an
   existing, live, working signal more precisely is the right direction even
   though the forgetting-curve half over-reaches.

---

## 10. The strongest alternative — neither this proposal nor the status quo

**Fix the seeding defect, not the model.** The single highest-leverage,
lowest-risk change available today is **TASK-751** (per-type ELO reseed for
the 48/60 ja tests sharing one rating across all 8 test types) — already
identified, already scoped, currently blocked only on "no (language, type)
has more than 8 first attempts" (`recon-serving.md:183`, `wiki/log.md`
2026-09-10). This is smaller than any of S1-S5, needs no new model family,
directly targets the *documented, root-caused* defect (content seeding, not
scoring algorithm — ADR-024 says this explicitly: "Better selection cannot
fix pitch accent on its own, because the type-blind test ELO is a *content
seeding* defect," `ADR-024:118-119`), and has an existing regression pattern
to reuse (parity-test the reseed against the byte-identical old ratings
where per-type data doesn't yet exist, same shape as `test_task748_parity.sql`).

**Second-highest leverage: close the 17-22% unlinked-test gap** (zh 27/125,
en 21/121 tests with no `vocab_sense_ids`, `recon-serving.md:185`,
`ADR-024:44-45`). Every proposal in S1-S5 that depends on vocabulary
linkage inherits this hole for a fifth of the en/zh catalogue — no
scheduling or IRT sophistication changes anything for a test the system has
zero vocabulary opinion about. This is a content-authoring/linking task
(the `test-sense-linking` skill already exists in this repo for exactly
this), not a serving-algorithm task, and it multiplies the value of
everything downstream of it, including any future S1-S5 work.

**Third: get more, and more diverse, real usage before any of S1/S2/S3.**
n=1, en=0. No amount of selector sophistication survives contact with "there
is one real learner and zero attempts in one of three languages." The
highest-expected-value move for the *serving* workstream specifically is not
a better algorithm — it's whatever gets a second and third real user
attempting tests in all three languages, because every metric in this
review (M1-M5, the eval doc's headline numbers, ADR-024's ability-spread
figures) is a single case study wearing the clothes of a population result.

**Framed directly against S1-S5:** the proposal treats "the model is wrong"
as the bottleneck. The evidence in this repo — the phase11 IRT precedent
sitting mostly idle at min_attempts=20, the n=1/en=0 population, the
documented seeding defect with a known fix already blocked purely on data
volume, the unlinked-test gap — says the bottleneck is **data volume and
content linkage**, not model sophistication. Shipping S1-S5 now would be
building a more sophisticated engine for a car that doesn't have gas yet.

---

## Claims in recon-serving.md worth flagging

None found to be **wrong**. Recon's central technical claims (the objective
function formulas, the neutral-degradation and tier-ceiling mechanics, the
n=1/en=0 figures, the 191-point equilibrium derivation, the 48/60 ja
seeding defect) were checked directly against `ADR-024`, `ADR-006`, and the
2026-09-17 evaluation doc and match. One thing recon does not mention that
materially changes the risk picture for this specific proposal: **the
Phase-11 exercise-level IRT precedent** (`migrations/phase11_irt_selection.sql`,
`services/irt/calibrator.py`) — a live, running, already-gated,
already-2PL-not-3PL IRT system in a sibling part of the same serving stack.
It isn't a recon error (recon was scoped to test/comprehension serving, and
Phase 11 governs exercise/ladder serving, a genuinely different RPC path),
but anyone deciding on S2 needs it in view, because it is the closest thing
this codebase has to a controlled experiment on exactly S2's question, and
the honest reading of it is cautionary, not encouraging.

---

## Bottom line

**What would change the decision:** a real count of
`exercises.irt_calibrated_at IS NOT NULL` (tests whether Phase-11 IRT has
ever actually fired) and a real count of attempts-per-test-item for the one
active learner. Both are cheap DB queries this review could not run. If
either comes back meaningfully non-zero/non-trivial, axis 1's FATAL verdict
softens to SERIOUS and S2 becomes worth prototyping. Absent that, the
n=1/never-repeat structural argument in axis 1, combined with the Phase-11
precedent, is enough to block S2 and the forgetting-curve half of S1 today.

**Priority-ordered action list:**
1. (Fatal, blocks S2/S1-forgetting) Confirm data volume before scoping
   further work on either — likely answer is "not enough," per the Phase-11
   precedent and the never-repeat serving policy.
2. (Serious, blocks any go/no-go) Run the 7-day shadow window the evaluation
   doc already asked for on `vocab_weight` before stacking anything on top
   of it; update `wiki/tasklist/master.md` to match the live state.
3. (Serious) Build the delayed-outcome metric before trusting M1-M5 (or the
   0.79→0.95 in-band number) as evidence of learning improvement, for this
   proposal or for the change already live.
4. (Do this instead, first) TASK-751 per-type ELO reseed, and the 17-22%
   unlinked-test content-linking gap — both smaller, better-evidenced, and
   already scoped.
5. (Worth doing now, low risk) S4 per-type computed difficulty, S5
   recognition→production sequencing, and the scheduling half of S1 (rank by
   `p_known` distance, no decay) — the three pieces of S1-S5 that don't
   depend on population size to be safe to ship.
