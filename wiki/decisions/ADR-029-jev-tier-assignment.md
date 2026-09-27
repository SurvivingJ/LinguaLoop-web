---
title: "ADR-029: jev assigns every test's age tier"
status: accepted
date: 2026-09-26
---

# ADR-029: jev assigns every test's age tier

## Context

A test's tier (`tests.target_age_tier`, 1–6, `dim_complexity_tiers.id`) was never measured. It
was the tier of the *topic* the passage was written for: the per-tier Explorer prompt stamped
the topic ([[decisions/ADR-003-age-tiers]] and TASK-740), and test generation copied it. A
prompt aimed at "T1" is not a T1 passage, and the labels showed it. On the live 305 active
tests, children's stories carried T6 and 神经学-level vocabulary carried T1.

The only LLM tier judge, `TierFitJudge` in topic generation, walked up to six sequential
yes/no chat calls per topic, judged the topic's vocabulary rather than any passage, and failed
open (an outage passed the topic unjudged).

`typesafe/jev-1.13` on OpenRouter is a typed decision model, not a chat model
(`POST /api/alpha/decisions`). The feasibility study
([[evaluations/jev-judge-feasibility-2026-09-26]] §3.4) found that it separates unambiguous
texts by tier cleanly and monotonically in zh, en and ja (89–100% exact on 54 hand-written
texts, ρ≥0.989 between its choice and score modes), repeats almost deterministically in score
mode, and costs ≈$0.00004 per call. On the 305-test re-tier the whole library cost $0.013.

## Decision

1. **jev assigns the tier.** One jev *score* question places a passage on the six-step tier
   scale. The probability-weighted score (0–5) becomes the tier by an ordered per-language
   threshold table (`SCORE_THRESHOLDS` in `services/tier_classifier.py`); the default is round
   half up, `floor(score + 0.5) + 1`. **ja uses fitted cut points** (0.95, 2.65, 3.25, 4.2,
   4.4) and **zh a uniform shift** (cut points 0.75 / 1.75 / 2.75 / 3.75 / 4.75, i.e.
   score − 0.25); **en stays on the default** (see *Recalibration* below). Score mode, not choice mode: it is an ordinal scale, and
   the two agreed at ρ≥0.989. The raw score is always stored, so a tier can be re-derived
   under a new table with no further call (`scripts/rederive_tiers.py`).
2. **The tier is measured on the finished passage, not inherited.** Test generation writes the
   passage for the topic's target tier (word budget, prose prompt), then asks jev. The
   *assigned* tier drives everything that is stored or seeded: `target_age_tier`, the legacy
   `difficulty`, the ELO seed (tier midpoint + `difficulty_scorer` adjustment), the question
   mix, the judges gate, the dedup scope `(topic_id, target_age_tier)`, the slug.
3. **Prompts are entirely in the content language** (zh in Chinese, ja in Japanese, en in
   English) and reuse `TIER_DISPLAY_NAMES` / `TIER_CONSTRAINTS` from
   `services/categorical_maps.py` verbatim. Topics are English, so the topic prompt is English.
4. **Difficulty is derived one-way from the tier**, to the bottom of its band
   (`TIER_ID_TO_DIFFICULTY` = 1, 3, 5, 6, 7, 8, computed from `DIFFICULTY_TO_TIER` so there is
   no fourth copy of the bands; `tests/test_difficulty_to_tier_matches_db.py` still pins the
   three that exist). `tests.difficulty` is still read by `dictation_max_words`,
   `get_recommended_tests`, `build_daily_session` and `tests_containing_sense`.
5. **No fallback.** On a jev error the client retries with backoff (network, 429, transient
   402, 5xx). If it still fails, that test's generation fails: nothing is written and the
   queue item is marked *failed* (retryable), not completed. There is no flag and no
   chat-model path; the old `TierFitJudge` internals (`TIER_READERS`, `best_tier`, the
   fail-open verdict) are deleted.
6. **The topic tier-fit judge uses jev too.** One score call on `concept + distinctive
   vocabulary`; a topic fits its stamped tier when it assesses **at or below** it (tier is a
   floor on reader capability), which preserves the old judge's one-sided meaning.
   `scripts/backfill_topic_tiers.py --stamp-tiers` stamps the assessed tier.
7. **The answer is stored, not just the tier.** `tests.age_tier_score` (raw), `age_tier_confidence`,
   `age_tier_probabilities` (`{"T1": p, …}`), `age_tier_model`, `age_tier_calibration` (which
   threshold table produced the tier: `default`, `ja-2026-09-27` or `zh-2026-09-27`),
   `age_tier_assessed_at`, so a
   tier can be audited, thresholded on confidence, or re-derived under a different mapping
   without another call.
8. **Every call is logged to `llm_calls`** (`pipeline='tier_assignment'`, task names
   `jev_tier_passage` / `jev_tier_topic`, `cost_usd` from `usage.cost`, token counts,
   `judge_verdict='T3'`, `judge_confidence`).
9. **Existing tests were re-tiered once**, all 305 active, through one atomic RPC
   (`apply_jev_retier`) that raises unless every row updates. `difficulty` was rewritten only
   where the tier changed. **ELO was left alone** for existing tests: live ELOs are not
   anchored to tier midpoints (T1 seeds range 1054–1430 against a midpoint of 875) and 54
   tests carry real attempts. New tests seed from the jev tier.

## Consequences

**Easier.** Tier now means something measurable and per-passage. One call replaces up to six.
Re-tiering the library is 26 seconds and ~$0.013, so a future prompt or model change is
cheap to re-run.

**Harder / constrained.**

- **Single provider, alpha endpoint.** jev is served only by TypeSafe through
  `/api/alpha/decisions`; there is no failover. An outage stops test generation (by design,
  no fallback) rather than degrading it.
- **Undocumented zh/ja support.** Evidence is empirical (600+ calls, coherent), not a
  vendor guarantee.
- **A test's tier can differ from its topic's.** 141 of 305 changed. Downstream code that
  assumed `tests.target_age_tier == topics.target_age_tier` is wrong. Dedup, the per-topic cap
  and `match_test_passages_by_topic_tier` all read the *test's* tier.
- **Dictation eligibility can change.** A test that moves down a tier may now exceed that
  tier's dictation length cap and drop out of dictation (only).
- **Legacy T6 difficulty is 9, new T6 rows are 8.** Both are in band and behave identically;
  unchanged T6 rows kept 9.
- **`tests` is created only by `TestGenerationOrchestrator`.** The legacy
  `TestService.save_test` path and its `/api/tests/generate_test` and `/custom_test`
  endpoints could not have worked (they inserted a non-existent `topic` column) and were
  removed on 2026-09-26.

**Known weakness, measured after the fact.** *(ja and zh recalibrated 2026-09-27, en measured and left
as is; see Recalibration.)* Fifteen tests per language were sampled
(7 largest tier moves, 6 lowest confidence, 2 unmoved controls) and read by a separate
subagent per language against the native tier descriptions:

| | agree | borderline | disagree |
|---|---|---|---|
| ja | 5 | 10 | 0 |
| en | 8 | 5 | 2 |
| zh | 10 | 4 | 1 |

- **ja is shifted up one tier.** All 10 ja borderlines were "new tier one too high"; 13 of 24
  ja tests labelled T4 became T5 or T6. The reviewer's reading: jev credits jargon density
  where the rubric's T5 markers are subordinate clauses, cultural idiom and descriptive
  richness. Adult expository prose full of loanword jargon reads as T5.
- **en has a milder version** (about 6 of 15: simple text with glossed jargon lifted one
  tier). **zh compresses toward T3** (13 of 15 sampled got T3, mostly at low confidence).
- Against the old labels, the reviewers found the new tier closer on most items where the two
  differ in zh and en; the old T1 and T6 labels were often plainly wrong. The sample is
  weighted to extremes, so these rates understate overall agreement. This is not a claim that
  jev is right, only that the previous labels were not better.

## Recalibration (2026-09-27)

Same procedure for each language: label blind (rubric only, no labels or jev output) with two
independent readers (LLM subagents), then fit and cross-validate the score → tier mapping
(`scripts/build_tier_gold_sample.py`, `scripts/fit_tier_thresholds.py`). A prediction hits
when it equals either reader's tier. ja used all 59 active tests; zh and en a 60-test sample
spread evenly over the jev score range.

| | readers agree exactly / within 1 | round-half-up | uniform offset (CV) | fitted 5 cuts (CV) | **applied** | original pre-jev labels |
|---|---|---|---|---|---|---|
| ja | 41 / 59 · 59 / 59 | 38 | 42 | **52.5** | fitted cuts (57 in-sample) | 48 |
| zh | 52 / 60 · 60 / 60 | 44 | **52.0** | 51.5 | uniform −0.25 (53 in-sample) | 33 |
| en | 54 / 60 · 60 / 60 | 46 | 44.2 | 47.0 | **default, no change** | 42 |

- **zh:** the offset and the five-cut fit tie under cross-validation, so the one-parameter
  model was kept. Live: 19 zh tests moved from the first jev pass (11 T3→T2, 7 T4→T3, 1 T6→T5).
- **en:** nothing beat round-half-up by more than noise (+1/60 for the fit, −2 for an offset),
  so en is untouched. jev already matches the readers on 46/60 (the pre-jev labels 42/60); the
  spot check's "mild upward bias" was a property of the extreme-weighted sample.
- **Pre-recalibration state** (all languages): `tests_tier_backup_20260927_v1`.
- **Guards:** `tests/fixtures/{ja,zh}_tier_calibration_gold.json` fail an edit that loses the
  fit.

### ja detail

The first pass rounded jev's expected tier half-up and left ja one tier high. To fix it rather
than guess, all 59 active ja transcripts were labelled **blind** (rubric only, no labels or jev
output) by two independent readers (LLM subagents; exact agreement 41/59, within one tier
59/59, Spearman 0.947). Findings:

- **jev's ordering is right; its scale is not.** Sorted by jev score the gold tiers ascend
  cleanly, but the tiers sit at expected-tier ≈ 1.3 / 2.4–3.6 / 4.0–4.2 / 4.3–5.2 / 5.5 / 5.9,
  so bands land at 1.97 / 3.63 / 4.25 / 5.22 / 5.39 rather than 1.5 / 2.5 / 3.5 / 4.5 / 5.5.
  The error is tier-dependent (gold T2–T3 +1.0, T4 +0.6, T6 0.0), so a uniform offset
  (best case 41/59) would have shifted the T6 items that were already right.
- **A prompt fix was not needed.** Adding a "judge by sentence structure, not jargon"
  instruction moved the bias only from +0.41 to +0.26 and lowered the rank correlation, so the
  production prompt stays unchanged (native rubric verbatim, one prompt across languages).
- **Fitted cut points fix it.** Matches to either reader: round-half-up 39/59 →
  fitted **57/59** (MAE vs the two-reader mean 0.51 → 0.19, bias +0.47 → +0.07);
  **52.3/59 under 5-fold cross-validation** (leave-one-out 52/59), which is the honest
  generalisation figure. The pre-jev labels matched 48/59 and could not express T2/T3 at all
  (ja content had only ever been generated at T1/T4/T6).
- **Applied live:** 59 ja tests re-derived from their stored raw scores (no new jev calls);
  26 moved from the first jev pass, 16 differ from the original labels; `difficulty` follows
  only where the tier moved; ELO untouched. Pre-recalibration state:
  `tests_tier_backup_20260927_v1`. The guard is `tests/fixtures/ja_tier_calibration_gold.json`
  (fails if an edit to the ja table drops it below 55/59).

Caveats: the gold is two model readers, not humans, and a 60-item sample per language is
small. T5 (and T3 in en) is barely represented, so cuts around those tiers are the least
certain; ja passages are short (mean 203 characters), which is itself noise; and the zh and en
samples are spread over the score range rather than random, so the hit rates describe that
sample, not the library's tier mix.

## Alternatives Considered

- **Choice mode (argmax tier).** 8–17 points higher exact match than rounded score in the
  experiment, but the task called for an ordinal, probability-weighted tier; kept the
  probabilities so choice can be recomputed as `argmax`.
- **Keep the target tier as the stored tier.** Zero cost, but it is the source of the bad
  labels above.
- **Keep a chat-model tier judge as fallback.** Rejected: two tier authorities that can
  disagree, and a fallback would silently reintroduce the guessing this replaces.
- **Fail open on jev errors** (as the old judge did). Rejected: a tier guessed under an
  outage is indistinguishable from a measured one.
- **Re-seed ELO for re-tiered tests.** Rejected for existing tests (see Decision 9); new
  tests do seed from the assigned tier.
- **A uniform per-language offset.** Tested on the ja gold: best 41/59, worse than the fitted
  table (57/59) because the error is not constant across tiers.
- **Average two calls with reversed option order.** The experiment showed 5% order
  sensitivity; not needed for routine use, and score mode takes an ordered array, so there
  is no order to reverse.

## Reversal

Two backups. `tests_tier_backup_20260927_v1` holds the state after the first jev pass and before
the ja recalibration (UPDATE in `migrations/task821_tier_calibration.sql`).
`tests_tier_backup_20260926` holds every test's pre-change `target_age_tier`, `difficulty` and
`seeded_elo` (307 rows). The `UPDATE … FROM tests_tier_backup_20260926` to restore them is in
`migrations/task819_jev_tier_assignment.sql`. Restoring a single language is the same
statement with `AND t.language_id = <id>`.

## Open questions

- **Human check of the gold sets** (the readers were models), particularly around T5 (and T3 in
  en).
- **Larger gold sets** would tighten the ja and zh tables; the scripts make a re-fit cheap.
- **Does jev on `concept + distinctive vocabulary` (topics) behave like jev on passages?** The
  feasibility study validated passages only.
- **Should the assigned tier gate anything** (for example, flag a test whose assessed tier is
  ≥2 from its target for review)?

## Related Pages

- [[evaluations/jev-judge-feasibility-2026-09-26]] — the feasibility study this rests on
- [[evaluations/jev-tier-calibration-2026-09-27]] — the blind gold sets and fits behind the score→tier tables
- [[features/test-tier-assignment]] / [[features/test-tier-assignment.tech]] — how it works and how to operate it
- [[tasklist/jev-tier-assignment.tasks]] — TASK-819–823
- [[database/schema.tech]] — `tests.age_tier_*` columns
- [[algorithms/elo-ranking]] — how test ELO is seeded and updated
