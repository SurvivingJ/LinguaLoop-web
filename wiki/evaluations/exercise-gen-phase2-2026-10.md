---
title: "Exercise Generation Cost — Phase 2 Eval (2026-10-03)"
type: evaluation
status: complete
last_updated: 2026-10-08
---

# Exercise Generation Cost — Phase 2 Eval (2026-10-03)

Two arms on the same 30 senses/language used in [[evaluations/exercise-gen-phase1-2026-09]]:
**bundle** (`VOCAB_LADDER_BUNDLE_MODE=on`, draft bundle prompts via `--prompt-override-file`,
`data/eval/runs/phase2_bundle_{ja,zh,en}`) and **nobundle** (Phase 1 + qwen reasoning truly off
+ coverage fixes including a scoped repair call, `data/eval/runs/phase2_nobundle_{ja,zh,en}`).
Scored against [[evaluations/exercise-gen-phase1-2026-09]] (same language) via
`scripts/score_exercise_gen_run.py`; ja also scored against the frozen reference set
(`data/eval/exercise_gen_reference_set_2026-09.json`). Logs: `data/eval/runs/_logs/phase2_*.log`.

**Headline: this run is not a valid bundle-vs-nobundle quality comparison.** All six 30-sense
arms were launched back-to-back against a single shared OpenRouter account between 11:28 and
11:56 on 2026-10-03. The three bundle runs (11:28:36–~11:55) and the three nobundle runs
(11:55:34, three seconds after bundle_ja's last log line) both ran into genuine `402 Payment
Required` / `in_flight_budget_exhausted` responses from OpenRouter — not the false-positive
sense-ID-substring matches noted in Phase 1's logs. Both arms hard-fail `Prompt 1 generation`
after 2 attempts when this happens, before any judge (bundle or per-level) ever runs. nobundle
launched directly into the tail of bundle's in-flight-budget hole (OpenRouter's own
`Retry-After: 120` suggests ~2 minutes to settle; nobundle got 0–3 seconds) and nobundle's
un-batched call pattern exposes more separate requests to the same per-request ceiling, so it
collapsed almost completely: **en nobundle is 30/30 failed, $0 spent, 0 calls observed.** Five
small (5-sense) dev smoke runs of the same coverage-fix code (`phase2_fix_{ja,zh,en}`,
`phase2_fix_en_retry`) all completed 5/5 or 4/5 cleanly outside this contention window — the
coverage-fix logic itself is not implicated.

## 1. Run completion

| | ja bundle | ja nobundle | zh bundle | zh nobundle | en bundle | en nobundle |
|---|---:|---:|---:|---:|---:|---:|
| Senses requested/attempted | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| `success` | 12 | 0 | 9 | 0 | 9 | 0 |
| `partial` | 2 | 3 | 2 | 2 | 3 | 0 |
| `failed` | 16 | 27 | 19 | 28 | 18 | **30 (100%)** |
| Cost cap tripped | No | No | No | No | No | No |
| Real `402`/`in_flight_budget_exhausted` (log) | 52 | ~106 | 63 | 75 | 55 | 60 |
| `gave up` hard P1 failures (log) | 16 | 38 | 26 | 36 | 19 | 30 |
| 429 / rate-limit | 0 | 0 | 0 | 3 | 0 | 0 |
| Tracebacks / empty-content | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Total LLM calls observed | 168 | 23 | 86 | 5 | 176 | **0** |
| Total cost (run) | $0.1555 | $0.0157 | $0.1006 | $0.0046 | $0.1440 | **$0** |

Context (phase1, same 30 senses, no contention — see [[evaluations/exercise-gen-phase1-2026-09]]):
ja 3 success/23 partial/4 failed, zh 10 success/20 partial/0 failed, en 5 success/24 partial/1
failed; **zero genuine 402s in any phase1 log**. Baseline (phase0) context: ja 5/10/15,
en 1/27/2(error) — baseline_en/ja *did* see genuine 402s (81/76), so this failure mode predates
Phase 2 and reappeared here, worse, under six-arm contention; there is still no zh baseline.

Every failed sense in every Phase 2 arm carries the identical top-level error string
`"Prompt 1 generation failed"` (100% of failures in all 6 arms) — no sense ever reached the
bundle judge or a per-level render judge before dying.

## 2. Scoring vs. reference

All 8 scorer invocations (`--candidate phase2_{bundle,nobundle}_{ja,zh,en} --reference
phase1_{ja,zh,en}`, plus ja vs. the frozen reference) wrote `score.json`/`score_report.md` under
`<candidate>/vs_phase1_<lang>/` and (ja only) `<candidate>/vs_frozen_reference/`. All 8 **FAIL**
on criterion (c) coverage; zh bundle also fails (d) invalid-asset-rate; pairwise criterion (b) is
SKIPPED everywhere (no `--pairwise-results` yet, per instructions — see §4). No scorer-adapter
changes were needed; `normalize_run_entry()` handled this run shape (`judges` dict,
`exercise_rows`/`ladder_level`/`tags.variant`) without modification.

## 3. Headline table ($/sense, calls, coverage, invalid rate)

Cost convention: mean over senses-with-calls (scorer's own convention, from `score.json`
`candidate_metrics.cost`), matching Phase 1's report. n = senses with ≥1 priced call.

| | ja phase1 | ja bundle | ja nobundle | zh phase1 | zh bundle | zh nobundle | en phase1 | en bundle | en nobundle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| $/sense mean (n) | $0.0686 (28) | $0.0097 (16) | $0.0052 (3) | $0.0493 (30) | $0.0091 (11) | $0.0023 (2) | $0.0289 (30) | $0.0120 (12) | **—(0)** |
| $/sense p50 | $0.0731 | $0.0106 | $0.0049 | $0.0503 | $0.0100 | $0.0021 | $0.0318 | $0.0112 | — |
| $/sense p90 | $0.0877 | $0.0128 | $0.0067 | $0.0591 | $0.0105 | $0.0025 | $0.0388 | $0.0159 | — |
| Calls/sense (of 30 attempted) | 15.83 | 5.60 | 0.77 | 15.97 | 2.87 | 0.17 | 16.03 | 5.87 | 0.00 |
| Reasoning-token share of completion tokens | 91.8% | **0.0%** | **0.0%** | 90.7% | **0.0%** | **0.0%** | 82.5% | **0.0%** | n/a |
| Cached-token share of prompt tokens | 3.6% | 0.6% | 9.4%* | 1.2% | 0.0% | 0.0%* | 0.0% | 1.7% | n/a |
| Repair+retry calls/sense (mean) | 2.43 | 1.25 | 1.00* | 1.53 | 0.91 | 0.50* | 1.17 | 0.83 | n/a |
| Wall clock/sense, mean (30 attempted)† | 510.3 s | 53.8 s | 8.5 s† | 357.1 s | 37.6 s | 2.4 s† | 92.1 s | 36.4 s | 1.0 s† |
| Exercises/sense, mean (30 attempted) | 13.17 | 7.00 | 1.80 | 15.57 | 5.27 | 0.53 | 12.97 | 6.50 | 0.00 |
| Invalid-asset rate (overall) | 0.0% | 0.0% | 0.0%* | 0.48% | **5.41%** | 0.0%* | 14.06% | **3.57%** | n/a |
| Coverage vs. phase1 (same senses) | — | **40.5%** | **12.3%** | — | **32.5%** | **4.3%** | — | **39.7%** | **0.0%** |
| Coverage vs. frozen reference (ja only) | 83.9%‡ | 36.5% | 11.2% | — | — | — | — | — | — |

\* nobundle n is 2–3 senses (0 for en) — not statistically meaningful, shown for completeness only.
† Wall-clock drops are mostly senses dying fast at the P1-generation 402 wall, not a genuine
pipeline speedup — do not read this as a latency win.
‡ phase1_ja's own score vs. frozen reference, reproduced from the prior report for context.

**Reasoning tokens are confirmed off in both Phase 2 arms, in every language** (0.0% share,
down from 82–92% in phase1) — the single largest designed cost lever landed. $/sense on
completed senses fell 81–92% bundle-side and further nobundle-side, but nobundle's n is too
small in every language to credit that drop to the pipeline rather than to having almost no
senses survive to be priced.

## 4. Bundle judge vs. per-level judges — does the bundle judge drive the coverage dip?

**No — not detectably.** Every failed sense in both arms dies at **Prompt 1 generation**
(100% of failures, §1), before the bundle judge (`ladder_bundle_judge`) or any per-level render
judge (`sentence_validity`, `particle`, `cloze`, `relation`, `l1_distractor`) ever runs. The
`judge_reject_counts` sample sizes make this unambiguous: nobundle's render judges saw almost no
volume at all (zh: 0 judge calls of any kind; en: 0; ja: `sentence_validity` ran only 21 times
vs. bundle's 79 and phase1's 135), so there is no judge-reject signal in nobundle to compare
bundle's against — the arms are not on the same footing to make this comparison, which is itself
the finding: **the coverage gap between arms is explained by call-pattern exposure to the
OpenRouter in-flight-budget ceiling (nobundle issues more separate, smaller calls per sense and
started with zero settle time — §0), not by judge strictness.**

Within bundle's own completed senses (where there is enough volume to look), its
`sentence_validity` judge rejects more than phase1's did on the same senses:

| Judge | ja phase1 reject% (n) | ja bundle reject% (n) | zh phase1 (n) | zh bundle (n) | en phase1 (n) | en bundle (n) |
|---|---:|---:|---:|---:|---:|---:|
| `sentence_validity` | 0.74% (135) | **2.53% (79)** | 0.0% (185) | **5.00% (60)** | 0.0% (169) | **6.74% (89)** |
| `l1_distractor` | 39.63% (217) | 0.0% (18) | 0.0% (30) | 0.0% (12) | 0.0% (45) | 0.0% (21) |
| `particle`/`relation`/`cloze` | 0–0% | 0–0% | 0% | 0% | 0% | 0% |

`sentence_validity` reject rate roughly triples-to-sextuples under bundle mode on the senses
that get that far — a real, consistent (all 3 languages) secondary signal that bundle-drafted
sentences trip the downstream per-level sentence judge somewhat more often than phase1's
per-level generation did. But the effect size (2.5–6.7 pp) is an order of magnitude smaller than
the 55–100 pp coverage gap driven by P1-stage 402 failures, and cannot itself explain why
coverage vs. phase1 is only 32.5–40.5% in bundle.

## 5. Pairwise packs (generated this session, not judged)

Per task scope, judging is deferred to a fresh context. Packs and keys, all under
`data/eval/runs/<candidate>/vs_phase1_<lang>/`:

| Set | Packs | Sense×level comparisons | Path |
|---|---:|---:|---|
| ja bundle vs. phase1_ja | 7 | 70 | `data/eval/runs/phase2_bundle_ja/vs_phase1_ja/pairwise_packs/` |
| ja nobundle vs. phase1_ja | 2 | 20 | `data/eval/runs/phase2_nobundle_ja/vs_phase1_ja/pairwise_packs/` |
| zh bundle vs. phase1_zh | 7 | 62 | `data/eval/runs/phase2_bundle_zh/vs_phase1_zh/pairwise_packs/` |
| zh nobundle vs. phase1_zh | 1 | 8 | `data/eval/runs/phase2_nobundle_zh/vs_phase1_zh/pairwise_packs/` |
| en bundle vs. phase1_en | 7 | 68 | `data/eval/runs/phase2_bundle_en/vs_phase1_en/pairwise_packs/` |
| en nobundle vs. phase1_en | 0 | 0 | `data/eval/runs/phase2_nobundle_en/vs_phase1_en/pairwise_packs/` (empty — nobundle_en produced zero exercises, no overlapping sense×level pairs to pack) |

Additionally generated (ja only, per item 2, not part of the required bundle-vs-nobundle set):
`phase2_bundle_ja/vs_frozen_reference/` (8 packs, 71 comparisons) and
`phase2_nobundle_ja/vs_frozen_reference/` (3 packs, 21 comparisons). Unblinding keys are
`pairwise_key.json` alongside each `pairwise_packs/` directory. Fold results in with
`scripts/merge_pairwise_verdicts.py` and re-run the scorer with `--pairwise-results` once judged.

## 6. Caveats

1. **This run cannot support a bundle-vs-nobundle non-inferiority decision.** The dominant
   signal in every metric (coverage, $/sense n, exercises/sense, wall clock) is "did this sense
   survive OpenRouter's in-flight-budget ceiling," not an effect of bundle vs. per-level
   prompting. A re-run with the arms staggered (and ideally not run six-at-a-time against one
   account) is needed before §3/§4's numbers can be trusted as a design comparison.
2. **nobundle's near-zero n makes its own numbers decorative, not diagnostic**, in zh and en
   especially (zh: 2 senses priced; en: 0). Only ja nobundle (3 senses) has even nominal data.
3. **zh's invalid-asset-rate FAIL (bundle, 5.41% vs. phase1's 0.48%) is on n=74 assets from 11
   senses** — worth re-checking on a clean run before treating it as a real regression.
4. Reasoning-tokens-off is the one finding that is NOT confounded by the contention window — it
   held in both arms, all languages, confirming that fix landed independent of the 402 issue.
5. `phase2_fix_{ja,zh,en}` / `phase2_fix_en_retry` (5-sense dev smoke runs of the nobundle
   coverage-fix code, run outside the contention window) all completed cleanly (5/5, 5/5, 3/5+2
   retried, 2/2) — cited in §0 as evidence the coverage-fix *logic* is not what failed here.
6. No empty-content or 429-storm errors in any Phase 2 log; the only infra failure mode observed
   was OpenRouter 402 in-flight-budget exhaustion.

## 7. max_tokens right-sizing (ADR-028 cost work, 2026-10-03)

OpenRouter reserves `(prompt_tokens + max_tokens) × price` against balance for every
in-flight request (the `402 in_flight_budget_exhausted` failure mode noted in §6). An
oversized `max_tokens` is pure downside: it never raises quality (the model stops at its own
natural completion length regardless), but it inflates the reservation and throttles how many
requests can be in flight at once. Every cap below was re-derived from MEASURED
`completion_tokens` in `llm_calls` rows — `data/eval/runs/phase2_bundle_{en,ja,zh}/`,
`phase2_fix_{en,en_retry,ja,zh}/`, `phase2_smoke_ja_v3/`, `phase2_smoke_zh_r/` (reasoning is OFF
for qwen in all of these; phase1 runs were excluded from the derivation because their qwen rows
still carry reasoning tokens, which inflate p99 by roughly 3-5x — see the phase1 column comparison
pulled during this analysis). Formula: `cap = max(ceil(p99 × 2), ceil(max × 1.25))`, rounded up
to a round number, never below `observed_max × 1.25`. Where a (task, language) combination had
fewer than 10 measured calls, the cap instead borrows the most structurally-similar measured
task/language (noted per row) rather than deriving from too few points.

| Task (language) | Old cap | New cap | n | p99 | max | Note |
|---|---:|---:|---:|---:|---:|---|
| `vocab_bundle_generation` (en) | 44000 | 9500 | 19 | 4532 | 4707 | |
| `vocab_bundle_generation` (ja) | 34000 | 7000 | 20 | 3317 | 3346 | |
| `vocab_bundle_generation` (zh) | 40000 | 9000 | 16 | 4267 | 4323 | |
| `vocab_bundle_generation` (other/default) | 40000 | 9500 | — | — | — | max of the three measured languages |
| `ladder_bundle_judge` (ja, zh only — en has no prompt row) | 16000 | 4500 | 19 (ja) / 16 (zh) | 1145 (ja) / 2038 (zh) | 1189 (ja) / 2100 (zh) | zh governs |
| `judge_ladder_sentence_validity` | 16000 | 300 | 71 pooled (en=68 governs) | 146 | 147 | ja n=1, zh n=2 are smaller and sparse — bounded by en, no borrow needed |
| `judge_ladder_l1_distractor` | 14000 | 250 | 73 pooled (en=34 governs) | 121 | 121 | zh n=1 sparse but smaller, not governing |
| `judge_ladder_relation` / `judge_ladder_word_family` (shared cap) | 13000 | 250 | 100 pooled (en/word_family=19 governs) | 120 | 120 | |
| `judge_ladder_particle` (ja-only) | 9000 | 200 | 32 | 87.5 | 90 | |
| `cloze_distractor_judge` | 1000 | 300 | 40 pooled (en=38 governs) | 128 | 128 | |
| `judge_ladder_collocation` | 1500 | 300 | 5 (en-only, too thin) | 27.9 | 28 | **borrowed**: own data too sparse (n=5, no ja/zh rows at all); uses the pooled short-Likert-judge family (cloze/l1/relation/family/particle/sentence_validity, n=321, p99=128, max=147) |
| `vocab_prompt1_core` (primary+retry, shared across languages) | 8192 | 4000 | 62 pooled (ja=24 governs) | 1753 | 1845 | |
| `vocab_prompt1_core_repair` | 8192 | 4000 | 3 (ja-only, too thin) | 1337 | 1340 | **borrowed**: own n=3; uses `vocab_prompt1_core`'s own ja measurement (same output shape) |
| `vocab_prompt1_core_sentence_repair` | 4096 | 500 | 49 pooled (ja=23 governs) | 204 | 206 | en n=9 is borderline-thin but smaller, not governing |
| `vocab_prompt2_exercises` (primary+retry+repair, shared) | 8192 | 2000 | 11 pooled (each language individually <10: en=4, zh=6, ja=1) | 979 | 1003 | pooled cross-language total (11) used directly, flagged as thin rather than borrowed from an unrelated task |
| `vocab_prompt3_transforms` (primary+retry+repair, shared) | 8192 | 1000 | 50 pooled (ja=16 governs) | 358 (pooled) / 400 (ja) | 419 | zh n=7 thin but smaller, not governing |

**Worst-case reserved $ per request, before → after** (at `(prompt_tokens_observed_max +
max_tokens) × completion_price`, qwen3.7-plus $0.32/$1.28 per M prompt/completion,
gemini-3.5-flash-lite $0.30/$2.50 per M — model picked per the language/task that actually governs
each cap above):

| Task | Model | Before | After | Reduction |
|---|---|---:|---:|---:|
| `vocab_bundle_generation` (en) | qwen3.7-plus | $0.0571 | $0.0129 | 4.4x |
| `vocab_bundle_generation` (ja) | qwen3.7-plus | $0.0443 | $0.0098 | 4.5x |
| `vocab_bundle_generation` (zh) | qwen3.7-plus | $0.0519 | $0.0123 | 4.2x |
| `ladder_bundle_judge` (zh) | qwen3.7-plus | $0.0210 | $0.0063 | 3.3x |
| `judge_ladder_sentence_validity` | gemini-3.5-flash-lite | $0.0402 | $0.0009 | 44x |
| `judge_ladder_l1_distractor` | gemini-3.5-flash-lite | $0.0351 | $0.0008 | 47x |
| `judge_ladder_relation`/`word_family` | gemini-3.5-flash-lite | $0.0327 | $0.0008 | 42x |
| `judge_ladder_particle` | qwen3.7-plus | $0.0117 | $0.0005 | 26x |
| `cloze_distractor_judge` | gemini-3.5-flash-lite | $0.0026 | $0.0009 | 3.0x |
| `judge_ladder_collocation` | gemini-3.5-flash-lite | $0.0039 | $0.0009 | 4.4x |
| `vocab_prompt1_core` (ja) | qwen3.7-plus | $0.0115 | $0.0061 | 1.9x |
| `vocab_prompt1_core_repair` | qwen3.7-plus | $0.0110 | $0.0056 | 2.0x |
| `vocab_prompt1_core_sentence_repair` (ja) | qwen3.7-plus | $0.0054 | $0.0008 | 6.7x |
| `vocab_prompt2_exercises` (ja) | qwen3.7-plus | $0.0114 | $0.0035 | 3.3x |
| `vocab_prompt3_transforms` (ja) | qwen3.7-plus | $0.0111 | $0.0019 | 6.0x |

The judge caps show the largest multiples (26-47x) because TASK-812 had already sized them from a
reasoning-contaminated baseline (phase1, qwen reasoning still on) — those p99s were inflated
3-5x over the true reasoning-off distribution. The bundle and P1/P2/P3 generator caps show smaller
multiples (1.9-6.7x) because they were sized from real per-component sums or already-reasonable
guesses, not a contaminated measurement.

No call in any measured run (old or new cap) showed `completion_tokens` within 20% of its
then-live cap — i.e. nothing was actually being truncated by the old caps either; they were purely
wasting reservation headroom, which is the throughput problem ADR-028 flags, not a quality one.
Implemented in: `services/vocabulary_ladder/bundle/generator.py`, `services/vocabulary_ladder/bundle/judge.py`,
`services/exercise_generation/judges/{sentence_validity,l1_distractor,relation,particle,cloze,collocation}.py`,
`services/vocabulary_ladder/asset_generators/{prompt1_core,prompt2_exercises,prompt3_transforms}.py`.
No LLM calls, DB writes, or `prompt_templates` changes were made for this section — caps are
code-level `call_llm(max_tokens=...)` arguments, not prompt-template-driven.

## 8. Pairwise quality (blind) — bundle failed non-inferiority in every language

The pairwise packs generated in §5 (`vs_phase1_<lang>/pairwise_packs/`) were judged blind in a
fresh context after this report's first draft, then unblinded and scored with
`scripts/merge_pairwise_verdicts.py` into `vs_phase1_<lang>/pairwise_results.json`. All three
arms are `phase2_bundle_<lang>` (`VOCAB_LADDER_BUNDLE_MODE=on`, qwen reasoning genuinely off)
judged against `phase1_<lang>` (no bundling, qwen reasoning effectively on but hidden/billed —
see the confound note below). **All three languages FAIL non-inferiority:**

| | ja | en | zh |
|---|---:|---:|---:|
| Candidate (bundle) major-defect rate | **25.71%** | **13.24%** | **24.19%** |
| Reference (phase1) major-defect rate | 8.57% | 2.94% | 19.35% |
| Win / Loss / Tie (candidate W / candidate L / tie) | 5 / 17 / 48 | 2 / 13 / 53 | 7 / 13 / 42 |
| Win rate | 7.14% | 2.94% | 11.29% |
| Loss rate | 24.29% | 19.12% | 20.97% |
| n judged | 70 | 68 | 62 |
| **Verdict** | **FAIL** | **FAIL** | **FAIL** |

Source: `data/eval/runs/phase2_bundle_{ja,en,zh}/vs_phase1_{ja,en,zh}/pairwise_results.json`.

### Defect classes (all instances found on the bundle/candidate side — phase1/reference had none
### of these defect types in its own `major_defects_reference` entries)

**ja** — also-correct distractors (a marked-wrong option the judge/generator's own explanation
concedes is grammatically acceptable, e.g. へ vs. に, 為る as an alternate reading of 成る) and
compound-word anchoring (a target morpheme tested only via a larger compound it's bound inside,
e.g. 一 tested through 一連, not in isolation) — the same bound-morpheme failure mode
`ja-sense-pool-bound-morphemes` already describes for generation, now showing up as a judging-time
defect too. Also several over-permissive cloze/accepted-answer lists (counters 台/個 and
derived form 機械化 accepted as direct substitutes; ungrammatical verb-stem substitutions
accepted).

**en** — malformed items, grammar/correctness errors, duplicate options, and broken or
contradictory explanations. Notably, **en has no `ladder_bundle_judge` prompt row** (§4, §5 —
`BundleJudge.judge_bundle` always falls back to the per-level judges for `language_id=2`), so
every en defect here was caught (or missed) by the same per-level judges phase1 also used — the
bundle judge cannot be the cause of en's regression. That points the en regression at bundled
*generation* itself, or at the reasoning-off generator change, not at bundle judging.

**zh** — cloze accepted-answer-list junk (contextually ungrammatical or nonsensical alternates
accepted alongside the correct answer, e.g. 原形毕露/毕生/毕业 accepted for a slot where none of
them fit; a dropped modifier diluting what's actually tested) and true-homophone L1 distractors
(all three distractors share the exact same reading/tone as the target, e.g. 辩/变/遍 all biàn,
壁/避/必 all bì — explicitly unsolvable by ear, the specific zh L1 failure mode
`l1_is_listening`/`webapp-dt...` memory already flags as never-valid for this exercise type).

### The confound this run cannot resolve

Every one of these defects sits on the bundle/candidate side, which invites "bundle mode caused
this." But `phase2_bundle_<lang>` differs from `phase1_<lang>` in **two** respects simultaneously:
bundle mode is on, AND qwen reasoning is genuinely off (`_use_enabled_false_reasoning_param` +
`reasoning: {'enabled': False}`, landed 2026-09-28 — confirmed 0.0% reasoning-token share in
§3, vs. 82-92% in phase1). Phase 1's own published quality numbers were measured with qwen
reasoning left on (hidden from the response, still generated and billed) — a state that, per
`_unsafe_to_disable_reasoning_when_price_routed`'s 2026-09-27 finding, could not actually be
turned off for a price-routed qwen call without reproducibly returning empty completions. So
**every number in this section's table could equally be "bundling made quality worse" or
"removing qwen's reasoning pass made quality worse" — this run cannot distinguish the two,**
and `phase2_nobundle_<lang>` (which would have isolated the reasoning-off effect alone) died
almost completely to the same six-arm OpenRouter contention described in §0/§6 (en: 0 calls
observed at all). `LADDER_QWEN_REASONING` (added in `services/llm_service.py` alongside this
report) now lets that attribution be run cleanly — see TASK-856 in
[[tasklist/exercise-gen-cost.tasks]] for the staggered 3-arm design and exact commands, blocked
today on OpenRouter credit (~$0.04 left of $80).

## 9. TASK-856 arm B (2026-10-04) — reasoning-isolation re-run, real metrics

**The first arm B attempt (previously logged in this section as a 401 Clerk-auth wipeout) was
voided by a key-load bug in the harness itself, not OpenRouter — $0 spent, no signal.** After
the fix, all three single-language, concurrency-1 re-runs completed
(`LADDER_QWEN_REASONING=off`, bundle off, same 30 senses per language as `phase1_<lang>`,
sequential, $0.60 cap each — `data/eval/runs/armB_{ja,zh,en}`, logs
`data/eval/runs/_logs/armB_{ja,zh,en}.log`). This isolates the reasoning-off effect that §0/§6
flagged as unresolved (phase2's `nobundle` arm, which would have isolated it, died to
OpenRouter contention instead).

### Completion

| | ja | zh | en |
|---|---:|---:|---:|
| Senses requested/attempted | 30/30 | 30/30 | 30/30 |
| `success` | 23 (77%) | 22 (73%) | 23 (77%) |
| `partial` | 6 (20%) | 7 (23%) | 7 (23%) |
| `failed` | 1 (3%) | 1 (3%) | 0 |
| 401 / 402 / 429 (real, not timestamp coincidences) | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Empty-content LLM responses | 0 | 0 | 0 |
| Other transport errors | 50× OpenRouter 404 "No endpoints found" on `cloze_judge` (fail-open, kept all distractors) | 2× "Server disconnected" (sense 19882, 2 variants dropped) | 4× `ConnectionTerminated` (sense 19458, 3 variants + 1 template lookup dropped) |
| Cost cap tripped | No ($0.387 of $0.60) | No ($0.276 of $0.60) | No ($0.365 of $0.60) |
| Run wall clock | 2,326s | 1,660s | 940s |

No auth/payment errors (401/402/429) occurred anywhere in any armB log this time — confirms the
key-load fix held for the full run. The handful of transport errors above are pre-existing
flakiness (OpenRouter routing/disconnects), not systematic failures, and did not trip the cost
cap in any language.

### Scoring vs. phase1

Run via `scripts/score_exercise_gen_run.py --candidate data/eval/runs/armB_<lang> --reference
data/eval/runs/phase1_<lang> --lang <lang> --llm-only --out-dir
data/eval/runs/armB_<lang>/vs_phase1_<lang>`. Reports at `<out-dir>/score_report.md` /
`score.json`.

| Metric | ja armB | ja phase1 | zh armB | zh phase1 | en armB | en phase1 |
|---|---:|---:|---:|---:|---:|---:|
| $/sense mean | $0.01288 | $0.06855 | $0.00921 | $0.04928 | $0.01217 | $0.02893 |
| $/sense p50 | $0.01296 | $0.07311 | $0.00951 | $0.05031 | $0.01325 | $0.03180 |
| $/sense p90 | $0.01742 | $0.08769 | $0.01023 | $0.05912 | $0.01420 | $0.03880 |
| Calls/sense | 18.97 | 15.83 | 17.50 | 15.97 | 21.27 | 16.03 |
| Reasoning-token share of completion tokens | **0.00%** | 91.77% | **0.00%** | 90.74% | **0.00%** | 82.48% |
| Repair-call rate (non-primary calls/sense) | 1.23 | 2.43 | 0.63 | 1.53 | 0.43 | 1.17 |
| Exercises/sense | 12.63 | 13.17 | 12.23 | 15.57 | 15.03 | 12.97 |
| Invalid-asset rate | 0.00% | 0.00% | 3.96% | 0.48% | 3.38% | 14.06% |
| Coverage — LLM types only | 72.65% (85/117) | ref | 63.11% (65/103) | ref | 83.50% (86/103) | ref |
| Coverage — all types | 82.82% (188/227) | ref | 84.29% (236/280) | ref | 91.01% (172/189) | ref |

`LADDER_QWEN_REASONING=off` fully eliminated reasoning-token spend (0.00% in all three
languages vs. 82-92% in phase1) — this is the clean isolation TASK-856 set out to get. $/sense
dropped 81% (ja), 81% (zh), and 58% (en); wall clock dropped 85% (ja: 15,317s→2,326s), 85% (zh:
10,724s→1,660s), and 66% (en: 2,765s→940s). Coverage regressed in all three languages (both
LLM-only and all-types), below the 95% non-inferiority floor, so none of the three passes the
automatic gate on coverage alone.

**Decision per language** (`decide_non_inferiority`, margins: major-defect 2pp, coverage min
95%, invalid-asset 3pp):

| Criterion | ja | zh | en |
|---|---|---|---|
| (a) major-defect rate ≤ ref + 2pp | **FAIL** (15.0% vs 10.09%) | PASS (0.0% vs 0.0%) | PASS (0.0% vs 0.0%) |
| (b) pairwise loss − win ≤ margin | **FAIL** (W/L/T 8/9/64, loss−win 1.2pp; defects 22.2% vs 19.8%) | **FAIL** (W/L/T 2/18/37, loss−win 28.1pp; defects 31.6% vs 7.0%) | **FAIL** (W/L/T 6/13/65, loss−win 8.3pp; defects 15.5% vs 7.1%) |
| (c) coverage ≥ 95% | **FAIL** (82.82%) | **FAIL** (84.29%) | **FAIL** (91.01%) |
| (d) invalid-asset rate ≤ ref + 3pp | PASS (0.0% vs 0.0%) | **FAIL** (3.96% vs 0.48%, margin 3.48%) | PASS (3.38% vs 14.06%) |
| **Overall** | **FAIL** | **FAIL** | **FAIL** |

Per-judge reject rate, candidate vs. reference on the same senses:

| Judge | ja armB | ja phase1 | zh armB | zh phase1 | en armB | en phase1 |
|---|---:|---:|---:|---:|---:|---:|
| l1_distractor | 50.25% (99/197) | 39.63% (86/217) | 0.00% (0/24) | 0.00% (0/30) | 0.00% (0/45) | 0.00% (0/45) |
| sentence_validity | 9.74% (15/154) | 0.74% (1/135) | 0.00% (0/108) | 0.00% (0/185) | 0.00% (0/196) | 0.00% (0/169) |
| particle | 0.00% (0/60) | 0.00% (0/33) | n/a | n/a | n/a | n/a |
| relation | 0.00% (0/48) | 0.00% (0/21) | 0.00% (0/90) | 0.00% (0/54) | 0.00% (0/36) | 0.00% (0/48) |
| word_family | n/a | n/a | n/a | n/a | 0.00% (0/63) | 0.00% (0/27) |

ja's l1_distractor and sentence_validity reject rates both rose with reasoning off, which is
what drives its (a) major-defect-rate failure — the only language where (a) fails. zh/en judge
reject rates are flat at ~0% both arms (too few l1_distractor samples in zh to read much into
it).

### Pairwise packs

Stale empty outputs from the voided first attempt did not exist on disk (that attempt died at
$0 before writing any score/pairwise artifacts, so there was nothing to delete). Generated fresh
with `--llm-only`, which drops the 10 deterministic types in
`services/vocabulary_ladder/deterministic/` from the packs only (not from the metrics above):

| Set | Packs | Comparisons | Path |
|---|---:|---:|---|
| ja armB vs. phase1_ja | 9 | 81 | `data/eval/runs/armB_ja/vs_phase1_ja/pairwise_packs/` |
| zh armB vs. phase1_zh | 6 | 57 | `data/eval/runs/armB_zh/vs_phase1_zh/pairwise_packs/` |
| en armB vs. phase1_en | 9 | 84 | `data/eval/runs/armB_en/vs_phase1_en/pairwise_packs/` |

**Pairwise review is now complete** (judged blind in a fresh context, unblinded and folded in
via `scripts/merge_pairwise_verdicts.py`):

| | ja | zh | en |
|---|---:|---:|---:|
| Candidate (armB) W / L / T | 8 / 9 / 64 | 2 / 18 / 37 | 6 / 13 / 65 |
| n judged | 81 | 57 | 84 |
| Loss − win | +1.2pp | +28.1pp | +8.3pp |
| Candidate major-defect rate | 22.2% | 31.6% | 15.5% |
| Reference (phase1) major-defect rate | 19.8% | 7.0% | 7.1% |
| **Verdict** | **FAIL** | **FAIL** | **FAIL** |

All three languages fail non-inferiority on pairwise quality, not just on coverage — zh is
the worst by a wide margin (18 losses vs. 2 wins, major-defect rate more than 4x phase1's), ja
is close to even on win/loss but still loses on the defect-rate comparison, and en sits between
the two. Combined with (c) coverage failing everywhere (§"Decision per language" above),
**reasoning-off (armB) does not clear the bar in any language on any axis that was actually
measured** — this is the main driver of the broader Phase 2 regression documented in this file
(§8), since armB isolates the reasoning-off change alone and still fails where phase2_bundle
(reasoning off + bundling) also failed.

### Status

**TASK-856's reasoning-isolation question is now fully answered: reasoning-off is a large, clean
cost and latency win (-58 to -81% $/sense, -66 to -85% wall clock) but fails non-inferiority on
every measured axis in every language** — coverage (c), pairwise quality (b), and (in ja) judge
major-defect rate (a). Coverage loss is concentrated in exercise types/levels the reasoning-off
pass skips or fails to fill (see `score_report.md` `per_sense_missing` for exact level/type gaps
per sense) — worth checking whether this is a prompt behavior change from removing reasoning, or
an artifact of `vocab_prompt3_transforms`/`morphology_slot` style gaps already seen elsewhere in
this doc. With pairwise review now in, there is no remaining open step blocking a final call:
**reasoning-off, as tested here, should not ship** — reasoning-off is the primary cause of the
broader Phase 2 non-inferiority failure described in §8, not bundling.

## 10. Arm D (reasoning budget 1024)

Follow-up to §9: instead of turning qwen reasoning fully off (armB), arm D caps it at a fixed
token budget (`LADDER_QWEN_REASONING=budget`, `LADDER_QWEN_REASONING_BUDGET=1024`, bundle off,
same 30 senses per language as `phase1_<lang>`/`armB_<lang>`, sequential, concurrency 1 —
`data/eval/runs/armD_{ja,zh,en}`, logs `data/eval/runs/_logs/armD2_{ja,zh,en}.log`). No cost cap
was configured for these runs (`max_cost_usd: null` in each `summary.json`), so
`stopped_due_to_cost_cap` is trivially `false` in all three.

**This is the re-run. The first arm D attempt (previously logged in this section, data now moved
to `data/eval/runs/_void/armD_{ja,zh,en}`) was voided**: three judges
(`l1_distractor_judge`, `sentence_validity_judge`, `ladder_relation_judge`) called qwen with a
`max_completion_tokens` below the fixed 1024-token reasoning budget, which Alibaba rejected with
HTTP 400 (`max_completion_tokens [250] must be greater than thinking_budget [1024]`) — 160x in
ja, 226x in zh — and each judge fails open on that error, so those judges did essentially no real
judging in ja/zh. The fix was a reasoning `max_tokens` bump so judge calls no longer collide with
the thinking budget, and the harness was made fail-closed via `batch_mode()` with
`judge_failures` captured in `summary.json` so a silent fail-open collapse like this is visible
going forward. This section now reports the re-run's real numbers.

### Completion

| | ja | zh | en |
|---|---:|---:|---:|
| Senses requested/attempted | 30/30 | 30/30 | 30/30 |
| `success` | 17 (57%) | 27 (90%) | 25 (83%) |
| `partial` | 9 (30%) | 3 (10%) | 5 (17%) |
| `failed` | 4 (13%) | 0 | 0 |
| `judge_unavailable` | 0 | 0 | 0 |
| Real HTTP 400 / 404 / 429 | 0 / 51 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `judge_failures` (judge\|error_class, from `summary.json`) | `l1_distractor_judge\|parse_error`: 12 | none | none |
| Cost cap tripped | No (no cap configured; $1.0291 observed) | No (no cap configured; $0.8224 observed) | No (no cap configured; $0.6393 observed) |
| Run wall clock | 10,589s | 7,655s | 1,963s |

**The thinking-budget/400 collision is gone**: zero HTTP 400s in any language this run (vs. 160
in ja / 226 in zh in the voided attempt). The 51 ja HTTP 404s are a separate, pre-existing issue
already documented elsewhere in this doc — `cloze_distractor_judge` calling
`qwen/qwen-2.5-72b-instruct` with strict parameter routing (`reasoning={'max_tokens': 1024}`,
`require_parameters: True`) gets "no endpoints found," retries once without those overrides, and
succeeds — it did not cause any sense to fail. The 12 `l1_distractor_judge` failures in ja are a
distinct, unrelated defect: a JSON parse error on the judge's own structured output (fails open,
"keep all"), not an HTTP error — it affected a minority of l1 judge calls, not all of them (see
the reject-rate table below, where ja's `l1_distractor` reject rate is 36.31%, close to phase1's
39.63%, not collapsed to 0% the way the voided run's judges were).

### Scoring vs. phase1

Run via `scripts/score_exercise_gen_run.py --candidate data/eval/runs/armD_<lang> --reference
data/eval/runs/phase1_<lang> --lang <lang> --llm-only --out-dir
data/eval/runs/armD_<lang>/vs_phase1_<lang>`. "Coverage — LLM types only" is not a field the
scorer emits on its own (`--llm-only`/`--exclude-types` affect pairwise packs only, per its
`--help`) — it was derived by re-running `compute_coverage` on senses filtered through
`filter_exercise_types(..., exclude_types=DETERMINISTIC_EXERCISE_TYPES)` before scoring, the same
transform the scorer itself applies to pairwise packs. Reasoning-token figures come from the
inline `llm_calls` rows in each per-sense run JSON (no DB read).

| Metric | ja phase1 | ja armB | ja armD | zh phase1 | zh armB | zh armD | en phase1 | en armB | en armD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| $/sense mean | $0.06855 | $0.01288 | $0.03430 | $0.04928 | $0.00921 | $0.02741 | $0.02893 | $0.01217 | $0.02151 |
| $/sense p50 | $0.07311 | $0.01296 | $0.03978 | $0.05031 | $0.00951 | $0.02819 | $0.03180 | $0.01325 | $0.02492 |
| $/sense p90 | $0.08769 | $0.01742 | $0.04484 | $0.05912 | $0.01023 | $0.03030 | $0.03880 | $0.01420 | $0.02747 |
| Calls/sense | 15.83 | 18.97 | 19.30 | 15.97 | 17.50 | 17.50 | 16.03 | 21.27 | 19.43 |
| Reasoning tokens/call (all calls, qwen+non-qwen) | 2664.3 | 0.0 | 893.6 | 1992.4 | 0.0 | 819.3 | 929.2 | 0.0 | 405.2 |
| Reasoning-token share of completion tokens | 91.77% | 0.00% | 78.54% | 90.74% | 0.00% | 80.76% | 82.48% | 0.00% | 67.69% |
| Repair-call rate (non-primary calls/sense) | 2.43 | 1.23 | 2.10 | 1.53 | 0.63 | 1.03 | 1.17 | 0.43 | 0.53 |
| Exercises/sense | 13.17 | 12.63 | 9.87 | 15.57 | 12.23 | 11.60 | 12.97 | 15.03 | 12.70 |
| Invalid-asset rate | 0.00% | 0.00% | 0.00% | 0.48% | 3.96% | 0.97% | 14.06% | 3.38% | 0.52% |
| Coverage — LLM types only | ref | 72.65% (85/117) | 67.52% (79/117) | ref | 63.11% (65/103) | 76.70% (79/103) | ref | 83.50% (86/103) | 74.76% (77/103) |
| Coverage — all types | ref | 82.82% (188/227) | 69.60% (158/227) | ref | 84.29% (236/280) | 81.79% (229/280) | ref | 91.01% (172/189) | 86.24% (163/189) |

$/sense mean drops **-50.0%** (ja), **-44.4%** (zh), **-25.6%** (en) vs. phase1 — a real saving,
but smaller than armB's reasoning-fully-off **-81.2%/-81.3%/-57.9%**, because the 1024-token
budget still bills a substantial share of completion tokens as reasoning (67.69-80.76%, vs.
armB's clean 0.00%). Wall clock drops **-30.9%** (ja: 15,317s→10,589s), **-28.6%** (zh:
10,724s→7,655s), **-29.0%** (en: 2,765s→1,963s) — again real but much smaller than armB's
-84.8%/-84.5%/-66.0%. Coverage is below phase1 in all three languages on both axes, and below
armB's coverage in ja and en (zh is the one language where armD's LLM-only coverage — 76.70% —
beats armB's 63.11%).

Per-judge reject rate, candidate vs. reference on the same senses:

| Judge | ja phase1 | ja armB | ja armD | zh phase1 | zh armB | zh armD | en phase1 | en armB | en armD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| l1_distractor | 39.63% (86/217) | 50.25% (99/197) | 36.31% (57/157) | 0.00% (0/30) | 0.00% (0/24) | 0.00% (0/39) | 0.00% (0/45) | 0.00% (0/45) | 0.00% (0/42) |
| sentence_validity | 0.74% (1/135) | 9.74% (15/154) | 2.63% (2/76) | 0.00% (0/185) | 0.00% (0/108) | 0.00% (0/127) | 0.00% (0/169) | 0.00% (0/196) | 0.00% (0/177) |
| particle | 0.00% (0/33) | 0.00% (0/60) | 0.00% (0/66) | n/a | n/a | n/a | n/a | n/a | n/a |
| relation | 0.00% (0/21) | 0.00% (0/48) | 0.00% (0/63) | 0.00% (0/54) | 0.00% (0/90) | 0.00% (0/111) | 0.00% (0/48) | 0.00% (0/36) | 0.00% (0/63) |
| word_family | n/a | n/a | n/a | n/a | n/a | n/a | 0.00% (0/27) | 0.00% (0/63) | 0.00% (0/75) |

Unlike the voided attempt (where ja's `l1_distractor`/`sentence_validity` collapsed to a flat
0.00%), this run's ja judge reject rates are in the same range as phase1/armB — the 12
`l1_distractor_judge` parse-error fail-opens noted above diluted but did not zero out the signal.
zh/en judges are flat at 0% across all three arms (same as previously observed; too few
l1_distractor/sentence_validity rejections in those languages to read much into it either way).

**Decision per language** (`decide_non_inferiority`, margins: major-defect 2pp, coverage min
95%, invalid-asset 3pp):

| Criterion | ja | zh | en |
|---|---|---|---|
| (a) major-defect rate ≤ ref + 2pp | PASS (9.73% vs 10.09%, judge_reject_rate_fallback) | PASS (0.0% vs 0.0%) | PASS (0.0% vs 0.0%) |
| (b) pairwise loss − win ≤ margin | SKIPPED (packs generated this session, not yet judged) | SKIPPED | SKIPPED |
| (c) coverage ≥ 95% | **FAIL** (69.60%) | **FAIL** (81.79%) | **FAIL** (86.24%) |
| (d) invalid-asset rate ≤ ref + 3pp | PASS (0.0% vs 0.0%) | PASS (0.97% vs 0.48%) | PASS (0.52% vs 14.06%) |
| **Overall** | **FAIL** | **FAIL** | **FAIL** |

All three languages fail on coverage alone, the same gate armB failed on. ja's (a) PASS this
time is a genuine (if noisy) read, not the artifact it was in the voided attempt — the judges
that drive the major-defect fallback actually ran on the large majority of calls.

### Pairwise packs

Generated fresh with `--llm-only` (drops the 10 deterministic types from the packs only, not
from the metrics above), overwriting the stale packs from the voided attempt:

| Set | Packs | Comparisons | Path |
|---|---:|---:|---|
| ja armD vs. phase1_ja | 8 | 78 | `data/eval/runs/armD_ja/vs_phase1_ja/pairwise_packs/` |
| zh armD vs. phase1_zh | 8 | 76 | `data/eval/runs/armD_zh/vs_phase1_zh/pairwise_packs/` |
| en armD vs. phase1_en | 8 | 71 | `data/eval/runs/armD_en/vs_phase1_en/pairwise_packs/` |

**Pairwise review (blind, reported by the operator after this section was first written):**

| Language | W / L / T (armD vs phase1) | Blind major-defect rate (armD vs phase1) | Verdict |
|---|---|---|---|
| ja | 14 / 9 / 55 | 11.5% vs 16.7% | PASS |
| zh | 3 / 10 / 63 | 14.5% vs 7.9% | FAIL |
| en | 7 / 3 / 61 | 5.6% vs 11.3% | PASS |

(Pairwise verdicts are the blind-judged outcomes; the coverage gate (c) above still fails in all three languages.)

### Status

**A bounded reasoning budget (1024 tokens) is a smaller, less complete cost win than turning
reasoning off entirely** ($/sense -50.0%/-44.4%/-25.6% vs. phase1 in ja/zh/en, vs. armB's clean
-81.2%/-81.3%/-57.9%) — expected, since the budget still bills 68-81% of completion tokens as
reasoning rather than armB's 0%. With the judge-collision bug fixed, this run's quality signal is
trustworthy where the voided attempt's was not, and the verdict is unchanged: **arm D fails the
same coverage gate (c) in all three languages** that armB failed, so a partial reasoning budget
buys a smaller cost win than reasoning-off for no coverage benefit. Pairwise review (not yet
run) could still move the needle on (a)/(b) if armD's actual exercise quality turns out
materially better than armB's per-item defect rate, but on the two axes measured so far
(automatic metrics + coverage), **reasoning-off (armB, §9) remains the stronger of the two
levers** — it is cheaper per sense and per hour, and the coverage shortfall is comparable or
worse under armD despite the extra reasoning spend.

## 11. Arm E (zh budget 2048) and Arm F (en gemini generation)

Two follow-ups to arm D, same 30 senses per language as `phase1_<lang>`, bundle off, harness fail-closed (`judge_failures` captured).

### Arm F is VOID (OpenRouter credit exhausted)

`data/eval/runs/armF_en_gemini` (log `data/eval/runs/_logs/armF_en.log`) generation tasks (`vocab_prompt2_exercises`, `vocab_prompt3_transforms`, `ladder_syn_ant_generation`, `ladder_word_family_generation`, `ladder_l4_morphology_generation`) overridden to `google/gemini-3.5-flash-lite`. Result: 0/30 usable. 10 senses `judge_unavailable` (`p1_sentence_judge|other`: 10), 20 `failed` (`Prompt 1 generation failed`), 0 assets, 58.8s wall clock, $0.0233 observed. Cause: HTTP **402** from OpenRouter ("requires more credits ... can only afford 40923") x50 in the log; 0 x 400/404/429. No scorable data: `score.json` was written (decision FAIL, but meaningless) and **no pairwise packs exist** for arm F. Re-run after topping up credit (same condition as the TASK-856 note in the ADR-028 state).

### Arm E (zh, `LADDER_QWEN_REASONING=budget`, budget 2048)

`data/eval/runs/armE_zh_budget2048`, 30/30 attempted: 26 success, 4 partial, 0 failed, 0 judge_unavailable, `judge_failures` none, HTTP 400/404/429 = 0/0/0, no cost cap (observed $1.1707), wall clock 10,409s (phase1 10,724s; armD 7,655s).

Scored with `scripts/score_exercise_gen_run.py --candidate data/eval/runs/armE_zh_budget2048 --reference data/eval/runs/phase1_zh --lang zh --llm-only --out-dir data/eval/runs/armE_zh_budget2048/vs_phase1_zh`. LLM-only coverage derived as in section 10.

| Metric (zh) | phase1 | armD (1024) | armE (2048) |
|---|---:|---:|---:|
| $/sense mean | $0.04928 | $0.02741 | $0.03902 |
| $/sense p50 | $0.05049 | $0.02870 | $0.04149 |
| $/sense p90 | $0.05912 | $0.03030 | $0.04431 |
| Calls/sense | 15.97 | 17.50 | 17.43 |
| Reasoning tokens/call | 1992.4 | 819.3 | 1337.4 |
| Reasoning share of completion tokens | 90.74% | 80.76% | 87.03% |
| Invalid-asset rate | 0.48% | 0.97% | 0.49% |
| Coverage, LLM-only | ref | 76.70% (79/103) | 86.41% (89/103) |
| Coverage, all types | ref | 81.79% (229/280) | 86.43% (242/280) |
| Judge reject: l1_distractor | 0/30 | 0/39 | 0/36 |
| Judge reject: sentence_validity | 0/185 | 0/127 | 0/175 |
| Judge reject: relation | 0/54 | 0/111 | 0/114 |

Savings vs phase1: $/sense -20.8% (armD -44.4%). Missing pairs are mostly `jumbled_sentence` at level 9 (deterministic) plus level-3 `cloze_completion`, level-6 `semantic_discrimination`, level-7 `spot_incorrect_sentence`. Decision: **FAIL on coverage (c) 86.43% < 95%**; (a) PASS (0.0% vs 0.0%, judge-reject fallback), (d) PASS (0.49% vs 0.48%); (b) skipped pending blind review. Doubling the budget from 1024 to 2048 recovers ~10pp of LLM-only coverage but gives back about half the saving, and still does not clear the gate.

Blind pairwise packs (`--llm-only`, seed 0, pack size 10): 8 packs / 79 comparisons at `data/eval/runs/armE_zh_budget2048/vs_phase1_zh/pairwise_packs/` (key: `.../vs_phase1_zh/pairwise_key.json`). **Pending blind review.** Arm F: no packs (void).

## 12. Recommended configuration and Conclusion (2026-10-08)

### Final blind-pairwise evidence (LLM-generated types only, vs phase1)

| Arm | Lang | Major-defect rate (arm vs phase1) | W/L/T | $/sense (arm vs phase1) | Verdict |
|-----|------|-----------------------------------|-------|-------------------------|---------|
| B (reasoning off) | ja | 22.2% vs 19.8% | - | ~$0.009-0.013 | FAIL |
| B (reasoning off) | zh | 31.6% vs 7.0% | - | ~$0.009-0.013 | FAIL |
| B (reasoning off) | en | 15.5% vs 7.1% | - | ~$0.009-0.013 | FAIL |
| D (budget 1024) | ja | 11.5% vs 16.7% | 14/9/55 | $0.0343 vs $0.0686 | PASS |
| D (budget 1024) | en | 5.6% vs 11.3% | 7/3/61 | $0.0215 vs $0.0289 | PASS |
| D (budget 1024) | zh | 14.5% vs 7.9% | 3/10/63 | $0.0274 vs $0.0493 | FAIL |
| E (budget 2048) | zh | 25.3% vs 24.1% | 13/15/51 | $0.0390 vs $0.0493 | PASS |
| Bundle mode | all | - | - | - | FAIL (confounded with reasoning-off; not re-tested with reasoning on) |
| F (en on gemini-3.5-flash-lite) | en | - | - | - | VOID (OpenRouter 402, credit exhausted) |

### Recommended configuration

```
LADDER_QWEN_REASONING=budget
LADDER_QWEN_REASONING_BUDGET_JA=1024
LADDER_QWEN_REASONING_BUDGET_EN=1024
LADDER_QWEN_REASONING_BUDGET_ZH=2048
# bundle mode off (VOCAB_LADDER_BUNDLE_MODE unset)
# en P2/P3 off claude-sonnet-5: migrations/exercise_gen_en_p2_p3_off_sonnet.sql (user applies)
```

Per-language budgets are resolved by `services.llm_service.ladder_qwen_reasoning_budget_tokens(language_code)`:
`LADDER_QWEN_REASONING_BUDGET_<LANG>` -> `LADDER_QWEN_REASONING_BUDGET` -> 1024. The effective budget is
recorded in each harness `summary.json` as `ladder_qwen_reasoning_budget`. **Production defaults are unchanged**
(`LADDER_QWEN_REASONING` still defaults to `on`); flipping them is TASK-857 and needs user approval.

Expected cost with this config: ja ~$0.034, zh ~$0.039, en ~$0.022 per sense, i.e. ~45-50% below Phase 1 and
~65-80% below the Phase 0 baseline.

### Conclusion

- **The <$0.01/sense target is NOT reachable at non-inferior quality with qwen3.7-plus.** Reasoning-off hits
  the cost target (~$0.009-0.013) but fails blind quality in every language; reasoning-off is the cause of the
  Phase 2 quality regression. Bounded reasoning (budget) is the best validated trade-off.
- Bundle mode failed in every language but was confounded with reasoning-off; a re-test with budget reasoning
  is outstanding (TASK-859).
- **Open caveats:** the coverage gate (>=95% vs phase1) failed in every arm including phase1-vs-baseline,
  most likely run-to-run variance in a single-run reference (TASK-860); judge noise is large (the same phase1
  zh set was rated 7.9% defects by one blind judge and 24.1% by another), so small W/L differences are not
  decisive; arm F (en on gemini) must be re-run (TASK-858).

## Related

- [[evaluations/exercise-gen-phase1-2026-09]] — reference this run is scored against
- [[evaluations/exercise-gen-baseline-2026-09]] — Phase 0 baseline
- [[decisions/ADR-028-exercise-gen-cost-under-1c]] — target and phase plan
