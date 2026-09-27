---
title: "Exercise Generation Cost Baseline (2026-09-26)"
type: evaluation
status: complete
last_updated: 2026-09-26
---

# Exercise Generation Cost Baseline (2026-09-26)

**TASK-808.** Phase 0 baseline for [[decisions/ADR-028-exercise-gen-cost-under-1c]]: run the
current, unmodified vocabulary-ladder pipeline on 30 senses/language with `llm_calls`
instrumentation (TASK-804) live, and measure $/sense, call volume, retry/repair share, wall
clock, and quality (invalid-asset rate, judge reject rate, coverage vs the frozen reference
set) before any model swap or call-collapse change (TASK-809+) is allowed to ship.

**Headline: neither language is close to the <$0.01/sense target, the two languages fail for
opposite reasons, and the zh baseline never ran — it is not filed here.** ja is cheap per call
but the pipeline half-fails (50% of senses did not complete); en completes but a validator gap
makes ~30% of its assets invalid and burns most of its budget on a claude-sonnet-5 call that is
worth relatively little of that spend. See [Run failures](#0-run-failures-read-this-first)
below before reading the cost tables as if they described a healthy run.

## 0. Run failures (read this first)

| | ja | en | zh |
|---|---|---|---|
| Senses requested | 30 | 30 | 30 (planned) |
| Senses attempted | 30 | 30 | **0 — run never executed** |
| `success` | 5 (16.7%) | 1 (3.3%) | — |
| `partial` | 10 (33.3%) | 27 (90%) | — |
| `failed` | 15 (50.0%) | 0 | — |
| `error` | 0 | 2 (6.7%) | — |
| Cost cap tripped | No | No | — |

**zh has no baseline.** `data/eval/runs/baseline_zh/` does not exist on disk, no
`_logs/baseline_zh.log` was ever written, and no zh process was found running at the time of
this write-up. Only `data/eval/runs/pilot_zh/` exists (a 2-sense smoke test from an earlier
session, both `success`, not a 30-sense run). Whatever produced `baseline_ja` and `baseline_en`
was not run for zh, or its output was lost before this session started. **zh has no cost, call,
or quality numbers in this document and no gate can be scored against it** — TASK-809 (move zh
generation to qwen) cannot be scored against a Phase 0 zh baseline because one was never
produced; it must be re-run before TASK-809 is evaluated for non-inferiority. Given ADR-028's
2026-09-26 correction (below), this is lower-urgency than it looks: zh generation is already on
qwen, so TASK-809 is largely a no-op migration, but the *measurement* gap is real and should be
closed before any other zh-facing change in this workstream ships.

**ja: 50% hard failure, all at generation, not judging.** 15 of 30 senses produced zero assets.
The dominant single error is **`Prompt 1 generation failed` (14 occurrences)** — P1 core
generation (the first call in the pipeline; everything downstream depends on it) failed outright
for essentially half the failed senses, with no fallback. Secondary errors are all downstream of
a missing P1 or a missing variant: `[A]/[B] synonym_antonym_match generation failed` (6),
`Prompt 3 (L4) variant A/B generation failed` (5), `[A]/[B] particle_selection generation
failed` (5), `Prompt 2/3 variant A/B generation failed` (12). No exceptions/tracebacks were
attached to these — they are handled failures inside the generators, not crashes, so the
specific upstream cause (timeout, malformed output, template load, provider error) is not
visible from the run artifacts alone and needs a follow-up log read if it recurs.

**en: near-universal partial completion, driven by one missing exercise level.** 27 of 30
senses are `partial` (only 1 fully `success`). The single largest error class is **`[A]
Missing level_8` / `[B] Missing level_8`, 26 occurrences each (52 total across 30 senses)** —
level 8 is missing from essentially every en sense, both variants. `exercises_per_sense.by_level`
confirms this at the aggregate level: level 8 has **zero** exercises across all 30 en senses,
vs. level 7 having only 2 (also a near-total gap) while levels 1/2/3/4/6/9 are populated
normally. ja does not show this gap (level 7 has 25 exercises, no level 8 in either language's
by_level table — level 8 may not be a defined ladder level in the current schema; if so the
error message itself, not just the count, is a scorer-adapter-shaped question worth checking
against `services/vocabulary_ladder` before assuming this is new). Two en senses (`13898`,
`14544`) hard-`error`ed with `httpx.RemoteProtocolError: Server disconnected` while loading the
`vocab_prompt1_core` prompt template from Supabase — a transient network/infra fault, not a
pipeline defect; both occurred before any billed call, so they cost $0 and are excluded from
the cost-per-sense-with-calls figures below (but included in the "mean over all 30" figures).

## 1. Run configuration

| | |
|---|---|
| Pipeline | `scripts/run_exercise_gen_eval.py`, current/unmodified, TASK-804 `llm_calls` instrumentation live |
| Senses/language | 30 |
| ja source | frozen benchmark set (`data/eval/exercise_gen_reference_set_2026-09.json`, run with `--force`) |
| zh/en source | `top_up_candidates` from the same reference file |
| ja batch_id | `b546df83-eb6e-4cb8-ab49-29ed2d47b4ab` |
| en batch_id | `9350a943-c5a2-42c0-98b2-6505f710f4a7` |
| ja run wall clock (total) | 5,189.2 s (86.5 min) |
| en run wall clock (total) | 929.8 s (15.5 min) |
| Logs | `data/eval/runs/_logs/baseline_ja.log` (325 KB), `baseline_en.log` (480 KB) |
| **Validator fix applied just before this run** | semantic_class normalisation in the P1 validator, removing a wasted repair round. **This baseline is current pipeline + that fix**, not the pre-fix pipeline — it is not a clean "before" snapshot for that specific change. |

## 2. Headline table

Two cost/sense conventions are both reported because they answer different questions: **"mean
over all 30"** is the real cost of attempting a sense including senses that failed for $0
(the number that matters for "what would 1,000 senses cost"); **"mean over senses with calls"**
(the scorer's convention, from `scripts/score_exercise_gen_run.py`) excludes zero-call
hard-errors and better isolates per-call unit economics.

| | ja | en | zh |
|---|---:|---:|---:|
| $/sense, mean (all 30 attempted) | $0.0313 | $0.1011 | — |
| $/sense, mean (senses with calls) | $0.0586 | $0.1083 | — |
| $/sense, p50 (all 30) | $0.0084 | $0.1153 | — |
| $/sense, p90 (all 30) | $0.0780 | $0.1515 | — |
| Calls/sense, mean | 9.73 | 15.47 | — |
| Retry+repair+json_repair share of cost | 17.7% | 2.8% | — |
| Wall clock/sense, mean | 298.4 s | 52.7 s | — |
| Wall clock/sense, p50 / p90 | 68.3 s / 764.8 s | 56.5 s / 75.0 s | — |
| Exercises/sense, mean | 7.50 | 10.73 | — |
| Invalid-asset rate (overall) | 0.0% | 30.4% | — |
| Total run cost | $0.9376 | $3.0318 | — |
| Total LLM calls | 292 | 464 | — |

**Gap to the <$0.01/sense target:** ja is **3.1-5.9×** over target (mean-over-all-30 vs
mean-over-calls); en is **10.1-10.8×** over target. Neither clears the bar, and they fail in
different registers — ja's mean is dragged *down* by cheap, near-zero-cost hard failures (a
sense that fails at P1 costs ~$0.03 in repair attempts before giving up, not the ~$0.06+ a
completed sense costs), so the "mean over calls" figure is the fairer read of what a *working*
ja sense costs today. en has almost no failures dragging its mean down, so its $0.10-0.11 is a
more honest picture of what today's en pipeline actually costs per sense.

## 3. Cost breakdown by task and call role

### By call_role (cost share)

| call_role | ja cost | ja share | en cost | en share |
|---|---:|---:|---:|---:|
| primary | $0.7717 | 82.3% | $2.9461 | 97.2% |
| json_repair | $0.1076 | 11.5% | $0.0766 | 2.5% |
| repair | $0.0483 | 5.2% | $0.0029 | 0.1% |
| retry | $0.0101 | 1.1% | $0.0062 | 0.2% |

ja spends **17.7%** of its budget on non-primary calls (retry+repair+json_repair); en spends
**2.8%**. This is the inverse of what the failure-rate numbers above might suggest — ja's
generators retry hard before giving up (12 `vocab_prompt1_core_sentence_repair` calls, 15
`ladder_syn_ant_generation__json_repair` calls, etc.), which is real spend on senses that often
still end up `failed` or `partial`.

### Top cost drivers by (language, task, model) — combined run

| Rank | Language | task_name | Model | Cost | Share of $3.9694 combined |
|---|---|---|---|---:|---:|
| 1 | en | vocab_prompt2_exercises | anthropic/claude-sonnet-5 | $1.5365 | 38.7% |
| 2 | en | ladder_syn_ant_generation | anthropic/claude-sonnet-5 | $0.3818 | 9.6% |
| 3 | en | vocab_prompt3_transforms | anthropic/claude-sonnet-5 | $0.3495 | 8.8% |
| 4 | en | ladder_word_family_generation | anthropic/claude-sonnet-5 | $0.3310 | 8.3% |
| 5 | en | ladder_l4_morphology_generation | anthropic/claude-sonnet-5 | $0.1918 | 4.8% |
| 6 | ja | vocab_prompt2_exercises | qwen/qwen3.7-plus | $0.1911 | 4.8% |
| 7 | ja | judge_ladder_sentence_validity | qwen/qwen3.7-plus | $0.1364 | 3.4% |
| 8 | ja | vocab_prompt1_core | qwen/qwen3.7-plus | $0.1151 | 2.9% |

**The top 5 cost drivers overall are all en/claude-sonnet-5 calls, 70.2% of combined spend.**
`vocab_prompt2_exercises` alone is 38.7% of everything spent in this baseline. Rank 3
(`vocab_prompt3_transforms`, $0.3495) is a specific waste flag: **96.4% of this task's output
was invalid** (below), so almost all of that $0.35 bought nothing usable.

### Per-task cost, calls, and token mix (ja, qwen/qwen3.7-plus unless noted)

| task_name | call_role | cost | calls | prompt tok | completion tok | reasoning tok | cached tok |
|---|---|---:|---:|---:|---:|---:|---:|
| vocab_prompt2_exercises | primary | $0.1911 | 23 | 61,670 | 133,868 | 118,712 | 0 |
| judge_ladder_sentence_validity | primary | $0.1364 | 50 | 29,573 | 99,162 | 96,210 | 0 |
| vocab_prompt1_core | primary | $0.1151 | 15 | 39,842 | 79,979 | 67,366 | 0 |
| vocab_prompt3_transforms | primary | $0.1080 | 24 | 39,540 | 74,499 | 70,849 | 0 |
| judge_ladder_p1_sentence | primary | $0.0898 | 25 | 18,055 | 65,659 | 60,931 | 0 |
| judge_ladder_l1_distractor | primary | $0.0530 | 13 | 10,477 | 38,777 | 36,037 | 0 |
| judge_ladder_l1_distractor | json_repair | $0.0481 | 13 | 10,531 | 34,934 | 31,569 | 0 |
| vocab_prompt1_core_sentence_repair | repair | $0.0343 | 12 | 3,473 | 25,906 | 24,797 | 0 |

`reasoning_tokens` is 71-96% of completion tokens on essentially every qwen3.7-plus call in
this table — this is a reasoning model, and reasoning tokens are billed. **`cached_tokens` is 0
on every ja primary call** — prompt caching is not engaging for ja today, which is exactly
ADR-028 open question (b) and TASK-812's target.

### Per-task cost, calls, and token mix (en; model noted per row)

| task_name | model | cost | calls | prompt tok | completion tok | reasoning tok |
|---|---|---:|---:|---:|---:|---:|
| vocab_prompt2_exercises | claude-sonnet-5 | $1.5365 | 44 | 99,290 | 133,790 | 102,299 |
| ladder_syn_ant_generation | claude-sonnet-5 | $0.3818 | 45 | 41,532 | 29,876 | 22,678 |
| vocab_prompt3_transforms | claude-sonnet-5 | $0.3495 | 44 | 70,928 | 20,765 | 15,113 |
| ladder_word_family_generation | claude-sonnet-5 | $0.3310 | 29 | 31,714 | 26,754 | 20,934 |
| ladder_l4_morphology_generation | claude-sonnet-5 | $0.1918 | 31 | 37,151 | 11,746 | 7,131 |
| vocab_prompt1_core | gemini-3.5-flash-lite | $0.0660 | 28 | 51,754 | 20,180 | 0 |
| judge_ladder_p1_sentence | gemini-3.5-flash-lite | $0.0257 | 38 | 24,222 | 7,380 | 0 |
| judge_ladder_sentence_validity | gemini-3.5-flash-lite | $0.0168 | 44 | 20,515 | 4,243 | 0 |

en's judges (all gemini-3.5-flash-lite) are cheap — none exceeds $0.026 total across 30 senses.
**All five of en's expensive tasks are on claude-sonnet-5**, which also shows reasoning tokens
despite Sonnet not being priced as a dedicated reasoning-tier model here — worth checking
whether extended thinking is enabled for these calls when TASK-813 (reasoning disabled) lands.

## 4. Quality: invalid-asset rate

| asset_type | ja valid/invalid | ja rate | en valid/invalid | en rate |
|---|---:|---:|---:|---:|
| prompt1_core | 15/0 | 0.0% | 26/0 | 0.0% |
| prompt2_exercises_A | 12/0 | 0.0% | 19/2 | 9.5% |
| prompt2_exercises_B | 11/0 | 0.0% | 23/0 | 0.0% |
| prompt3_transforms_A | 12/0 | 0.0% | **1/27** | **96.4%** |
| prompt3_transforms_B | 9/0 | 0.0% | **1/27** | **96.4%** |
| llm_types_A | 15/0 | 0.0% | 28/0 | 0.0% |
| llm_types_B | 15/0 | 0.0% | 28/0 | 0.0% |
| **Overall** | **89/0** | **0.0%** | **128/56** | **30.4%** |

**en `prompt3_transforms` is producing near-total garbage — 96.4% invalid on both variants.**
This one asset type accounts for effectively all of en's 30.4% overall invalid rate (56 of 56
invalid assets are `prompt3_transforms`). ja's `prompt3_transforms` on the same conceptual task
(different prompt/model — qwen) is 0% invalid. This is the single most actionable finding in
this baseline: whatever validator or schema `prompt3_transforms` enforces for en is rejecting
almost everything claude-sonnet-5 produces for it, and $0.35 (8.8% of combined spend, see §3) is
being spent to produce output that is thrown away. This predates and is independent of the
semantic_class validator fix noted in §1 — worth its own investigation before TASK-814/815
touch this call site.

## 5. Quality: render-judge reject rate

| judge | ja ran (calls) | ja reject rate (items) | en ran (calls) | en reject rate (items) |
|---|---:|---:|---:|---:|
| l1_distractor | 13 | **33.6%** (41/122) | 18 | 0.0% (0/54) |
| sentence_validity | 44 | 0.0% (0/82) | 38 | 0.0% (0/110) |
| relation | 9 | 0.0% (0/33) | 14 | 0.0% (0/42) |
| particle | 6 | 0.0% (0/24) | — (n/a for en) | — |
| word_family | — (n/a for ja) | — | 20 | 0.0% (0/60) |
| cloze | 17 (calls) | not tallied (0 kept, 0 rejected recorded) | 40 (calls) | not tallied (0 kept, 0 rejected recorded) |

**ja's l1_distractor judge is the only judge with a non-trivial reject rate in this baseline,
at 33.6%** — a third of L1 phonetic-recognition distractor candidates are being rejected and
regenerated, which is consistent with L1's known all-or-nothing render gate (see
[[features/exercise-generation-prompts]]: L1 is an audio-confusable-only listening exercise,
and pitch-accent-only distractor pairs are invalid because TTS renders one form). Every other
judge in both languages rejected effectively nothing
in this sample (0 of several hundred items) — either those judges are healthy, or (per the
long-standing `distractor-judge-language-divergence` finding) they are not calibrated to catch
what they should; this baseline cannot distinguish those two explanations on its own.

**`cloze` shows `ran` > 0 but `kept`/`rejected` both 0 in both languages** — the run harness's
summary counts the calls but does not tally per-item verdicts for this judge, so its true
reject rate is unknown from this artifact, not necessarily zero. Flagged rather than reported
as "0%" to avoid implying a clean judge when the truth is "not measured."

## 6. Exercises per sense, by level

| Level | ja count | en count |
|---|---:|---:|
| 1 | 38 | 18 |
| 2 | 30 | 56 |
| 3 | 17 | 40 |
| 4 | 43 | 64 |
| 6 | 30 | 50 |
| 7 | 25 | **2** |
| 8 | 0 | **0** |
| 9 | 42 | 92 |

Level 8 is absent from both languages' output entirely (see §0 — for en this drove the dominant
error class; for ja no "Missing level_8" error was logged, so either level 8 is not expected to
exist in the current schema for ja, or it fails silently there without an error string — worth
a one-line check against `services/vocabulary_ladder` before assuming parity). en level 7 is
also nearly empty (2 exercises across 30 senses, vs ja's 25) and correlates with the "Missing
level_7" error class in §0.

## 7. Coverage vs. the frozen reference set (ja only)

Scored with `scripts/score_exercise_gen_run.py --candidate data/eval/runs/baseline_ja
--reference data/eval/exercise_gen_reference_set_2026-09.json --lang ja`. **Result: FAIL on
coverage (c); PASS on invalid-asset rate (d); (a) major-defect-rate and (b) pairwise both
SKIPPED** (no judge-verdict rows in the reference and no pairwise verdicts folded in yet — see
§8).

| Metric | Value |
|---|---|
| Senses compared (candidate ∩ reference) | 30 of 30 candidate senses matched a reference sense |
| Senses in reference not attempted by candidate | 20 (reference set has 50 senses total; this run only covered 30) |
| Expected (level, exercise_type) pairs | 249 |
| Present pairs | 114 |
| **Coverage** | **45.8%** (threshold: 95%) |
| Invalid-asset rate, candidate vs. reference | 0.0% vs 0.0% (PASS, margin 3pp) |
| L1 variants, candidate vs. reference | 13 vs. 43 |

The 45.8% coverage failure is not a new/separate defect — it is the direct downstream
consequence of the 50% sense-failure rate in §0: a sense that fails at P1 contributes 0 of its
~10 expected (level, type) pairs to the numerator. This is one number, not two independent
findings.

### Scorer adapter fixes made in this session

`scripts/score_exercise_gen_run.py`'s `normalize_run_entry()` did not correctly read the real
`exercise_rows` shape written by `run_exercise_gen_eval.py`, which silently zeroed coverage to
0% (a scorer bug, not a pipeline defect) before these fixes:

1. **Level field.** Real exercise rows carry `ladder_level` at the row's top level (or inside
   `tags.ladder_level`); the scorer only read `level`. Every candidate exercise was normalizing
   to `level=None`, so no (level, type) pair could ever match the reference's real level
   numbers — this alone was the entire cause of the first run showing 0.0% coverage.
2. **Variant/payload fields.** `variant` lives in `tags.variant`, not at the row's top level;
   rendered content lives under `content`, not `payload`. Both are now tried as fallbacks. This
   fixed `l1_drop_rate` reporting 0 ja L1 variants (real count: 13) and empty pairwise-pack
   rendering.
3. **Own-output re-ingestion.** `load_candidate_run` globs every `*.json` in the run directory;
   after a first scoring pass writes `score.json`/`pairwise_key.json` into that same directory
   (the default `--out-dir`), a second run tried to parse its own prior output as a per-sense
   record and crashed with `RunShapeError` on `pairwise_key.json`. Fixed by excluding the
   scorer's own output filenames.
4. **Wall clock undercounting.** `stage_seconds` in the real per-sense JSON only covers a subset
   of pipeline stages (`fetch_corpus`, `p1_generate`, `p1_repair`, `tier_gate`, `p1_judge`,
   `fan_out`) and summed to roughly half of the sense's actual `wall_clock_s` (e.g. sense 35127:
   388s summed vs. 772s actual). The scorer now prefers the authoritative top-level
   `wall_clock_s` field when present, falling back to the stage-timing sum otherwise.

All 4 fixes are confined to `normalize_run_entry`/`compute_wall_clock`/`load_candidate_run` per
the module's own "Adapter contract" docstring. `tests/test_score_exercise_gen_run.py` (21 cases)
passes unchanged after the fixes — the synthetic fixtures already used the aliased field names,
which is why the bug was invisible to the test suite and only surfaced against a real run.

## 8. Blind pairwise packs (ja vs. frozen reference)

Generated at `data/eval/runs/baseline_ja/pairwise_packs/pack_01.md` through `pack_09.md` (9
packs, 84 sense×level comparisons, seed 0), with the unblinding key at
`data/eval/runs/baseline_ja/pairwise_key.json`. **These have not been judged** — per the task
scope, judging blind pairwise packs is a separate, fresh-context step (a subagent or human
reviewer with no visibility into which side is baseline vs. reference), not something to do
inside this write-up. Once judged, fold the result in with
`scripts/merge_pairwise_verdicts.py --candidate data/eval/runs/baseline_ja --verdicts <file>`
and re-run the scorer with `--pairwise-results` to fill in criteria (a) and (b) above, which are
currently SKIPPED for lack of this data.

zh and en have no pairwise packs in this baseline: en was scored against itself (trivially
100% "coverage", not a meaningful pairwise comparison), and zh has no run to pack at all (§0).

## 9. Caveats

- **Validator fix landed just before this run.** A semantic_class normalisation fix in the P1
  validator (removing a wasted repair round) shipped immediately before this baseline was run.
  Every number in this document is **current pipeline + that fix**, not a pre-fix snapshot — if
  a future comparison needs the pre-fix cost, it is not recoverable from this run.
- **ja senses are the frozen benchmark set, run with `--force`**, i.e. deliberately re-run
  against senses the reference set was built from, to make the coverage/pairwise comparison in
  §7-8 meaningful. zh/en senses are `top_up_candidates` — sense IDs the reference file lists as
  needing exercises, not senses with existing reference exercises to compare against.
- **zh and en have no independent benchmark.** Per the frozen reference file, only ja has
  authored reference exercises. For zh and en, **this baseline run is the reference** any later
  candidate (TASK-809/814/815 etc.) must be scored against with `--reference
  data/eval/runs/baseline_{zh,en}` — except zh has no baseline to point at (§0).
- **en's $/sense is not comparable to ja's on a "which language costs more" basis** without
  correcting for the model split: en's expensive tasks are on claude-sonnet-5 (permitted by
  ADR-028 §2 for en), ja's are on qwen3.7-plus. The gap mostly reflects that model choice, not
  an en-specific structural problem — except for the `prompt3_transforms` invalid-rate finding
  in §4, which is a real en-specific defect independent of model cost.
- **No paid LLM calls, DB writes, or `services/` changes were made in this session.** All
  numbers are read from the run artifacts already on disk (`data/eval/runs/baseline_{ja,en}/`)
  and `data/eval/runs/_logs/`. The only code change made was the scorer-adapter fix in §7.
- **Coverage/pairwise scoring only exists for ja.** en was scored against itself as its own
  reference (trivial PASS, informative only for confirming the scorer's cost/invalid-rate
  metrics are correct, not for a real non-inferiority judgment) since there is no independent en
  benchmark to score against yet.

## 10. Gap to target, summarized

| | Target | ja | en | zh |
|---|---:|---:|---:|---:|
| $/sense | <$0.01 | $0.031-0.059 (**3.1-5.9×**) | $0.101-0.108 (**10.1-10.8×**) | not measured |
| Non-inferior to reference | required | FAIL (coverage 45.8% vs 95% min; driven by 50% sense failure, not exercise quality) | n/a (self-referential) | not measured |

Neither language clears the cost target, and ja additionally fails the coverage gate for
reasons unrelated to cost (a generation-reliability problem, not a pricing problem). No
Phase 1/2/3 change (TASK-809+) should be scored as "shipped" against this baseline until (a)
the ja P1 failure mode is understood well enough to not be conflated with a future model-swap's
own failure rate, and (b) a real zh baseline exists.

## Related

- [[decisions/ADR-028-exercise-gen-cost-under-1c]] — the ADR this baseline gates, with a
  2026-09-26 correction to its "current model assignment" paragraph
- [[tasklist/exercise-gen-cost.tasks]] — TASK-804-818
- `data/eval/runs/baseline_ja/score_report.md`, `data/eval/runs/baseline_en/score_report.md` —
  full scorer output
- `data/eval/runs/baseline_ja/pairwise_packs/` — unjudged blind pairwise packs (§8)
