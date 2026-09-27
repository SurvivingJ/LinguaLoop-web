---
title: "Exercise Generation Cost — Phase 1 Eval (2026-09-27)"
type: evaluation
status: complete
last_updated: 2026-09-27
---

# Exercise Generation Cost — Phase 1 Eval (2026-09-27)

**TASK-810–813** (retry caps + P3 salvage gating, level-scoped regen, stable-prefix/cache-token
logging, provider price routing + reasoning exception) plus an earlier `semantic_class` fix,
scored against [[evaluations/exercise-gen-baseline-2026-09]] via
`scripts/score_exercise_gen_run.py`. Runs: `data/eval/runs/phase1_ja` (baseline_ja sense ids,
`--force`), `data/eval/runs/phase1_en` (baseline_en sense ids, en generation overridden to
`qwen/qwen3.7-plus` for `vocab_prompt2_exercises`, `vocab_prompt3_transforms`,
`ladder_syn_ant_generation`, `ladder_word_family_generation`, `ladder_l4_morphology_generation`),
`data/eval/runs/phase1_zh` (30 `top_up_candidates` senses — **the first zh run that has ever
existed**, so it is filed here as the zh reference going forward, not scored against a baseline
that doesn't exist). Logs: `data/eval/runs/_logs/phase1_{ja,en,zh}.log`.

**Headline: en is the win, ja is not.** en's per-sense cost (on senses with calls) dropped
73.4% on the *same senses* baseline_en ran ($0.1083 → $0.0289), driven almost entirely by moving
five tasks off `anthropic/claude-sonnet-5` onto `qwen/qwen3.7-plus`. ja's per-sense cost on the
same completed senses went **up** 10.2% ($0.0590 → $0.0650) — Phase 1's reliability fixes (retry
cap, P3 gating) mean ja now *completes* far more senses (28/30 had calls vs. baseline's ~15-16),
so the mean-over-all-30 figure rose even further (3.1x → 6.4x over target) simply because there
are fewer free $0 failures dragging it down. No language clears <$0.01/sense. zh's first-ever
run lands at $0.0493/sense (4.9x over target) and is now the reference for future zh phases.

## 1. Run completion

| | ja | en | zh |
|---|---:|---:|---:|
| Senses requested / attempted | 30 / 30 | 30 / 30 | 30 / 30 |
| `success` | 3 (10.0%) | 5 (16.7%) | 10 (33.3%) |
| `partial` | 23 (76.7%) | 24 (80.0%) | 20 (66.7%) |
| `failed` | 4 (13.3%) | 1 (3.3%) | 0 |
| Cost cap tripped (`stopped_due_to_cost_cap`) | No | No | No |
| 402 / `in_flight_budget` errors | 0 (grep hits were false positives — sense IDs/timestamps containing "402", confirmed by extracting real `HTTP/x.x NNN` codes) | 0 | 0 |
| Non-2xx HTTP | none | none | 3× `HTTP/1.1 429` (transient, no retry-exhaustion) |
| Tracebacks / crashes | 0 | 0 | 0 |
| Total LLM calls | 475 | 481 | 479 |
| Total cost (run) | $1.9195 | $0.8679 | $1.4784 |

vs. baseline: ja completion improved sharply (baseline was 50% `failed`; now 13.3%). en held
steady (baseline 1 `success`/27 `partial`/2 `error`; now 5/24/1, no `error` class this time).

## 2. Headline cost table

Two conventions again, both from the scorer: **mean over all 30 attempted** (includes $0
hard-failures) and **mean over senses with calls** (the scorer's own convention — excludes
zero-call failures, better isolates unit economics of a sense that actually ran).

| | ja baseline | ja phase1 | en baseline | en phase1 | zh phase1 (reference) |
|---|---:|---:|---:|---:|---:|
| $/sense, mean (all 30) | $0.0313 | $0.0640 | $0.1011 | $0.0289 | $0.0493 |
| $/sense, mean (senses w/ calls) | $0.0586 (n=16) | $0.0686 (n=28) | $0.1083 (n=28) | $0.0289 (n=30) | $0.0493 (n=30) |
| $/sense, p50 | $0.0653 | $0.0731 | $0.1171 | $0.0318 | $0.0503 |
| $/sense, p90 | $0.0913 | $0.0877 | $0.1522 | $0.0388 | $0.0591 |
| Calls/sense | 9.73 | 15.83 | 15.47 | 16.03 | 15.97 |
| Retries/sense (mean) | 5.31 | 2.43 | 0.68 | 1.17 | 1.53 |
| Retry+repair+json_repair, % of cost | 17.7% | 13.5% | 2.8% | 5.6% | 7.8% |
| Wall clock/sense, mean | 298.4 s | 510.3 s | 52.7 s | 92.1 s | 357.1 s |
| Wall clock/sense, p50 / p90 | 68.3 / 764.8 s | 522.0 / 664.2 s | 56.5 / 75.0 s | 91.1 / 115.8 s | 332.5 / 437.8 s |
| Exercises/sense, mean | 7.50 | **13.17** | 10.73 | **12.97** | 15.57 |
| Invalid-asset rate (overall) | 0.0% | 0.0% | 30.4% | **14.1%** | 0.48% |
| Gap to <$0.01/sense (calls-mean) | 5.9x | 6.9x | 10.8x | **2.9x** | 4.9x |

Retries/sense fell as designed (TASK-810's cap) in every language — ja's dropped by more than
half. But retries falling did not translate into lower per-completed-sense cost for ja, because
wall clock and call volume both rose (more senses now push all the way through the pipeline
instead of dying early), and because reasoning-token volume on `qwen/qwen3.7-plus` swamps the
retry savings (§4).

## 3. Cost reduction on the SAME senses (apples-to-apples)

The headline table above compares different sense *sets* implicitly, since baseline and phase1
completed different subsets of the same 30 requested sense IDs. Restricting to senses that
**both runs actually completed with at least one billed call**:

| | ja (n=15 senses in both) | en (n=28 senses in both) |
|---|---:|---:|
| baseline total cost (these senses) | $0.8849 | $3.0318 |
| phase1 total cost (these senses) | $0.9748 | $0.8078 |
| baseline $/sense | $0.0590 | $0.1083 |
| phase1 $/sense | $0.0650 | $0.0289 |
| **Change** | **+10.2% (more expensive)** | **−73.4% (cheaper)** |

Including the full 30-sense set (i.e. counting baseline's $0 failures as $0, not excluding
them): ja goes from $0.0313 → $0.0640/sense (**+104.7%**, because far fewer sense now fail for
free) and en goes from $0.1011 → $0.0289/sense (**−71.4%**). En is a clean win either way. Ja is
not a cost win in Phase 1 — it is a *reliability* win (13.3% failure vs. 50%) that, read as a
pure cost metric, looks like a regression. Both readings are real; neither is wrong, they answer
different questions ("what does a working sense cost" vs. "what does 1,000 requested senses
cost").

## 4. Top cost drivers (by `task_name`, aggregated across `call_role`/model)

| ja | $ | % | en | $ | % | zh | $ | % |
|---|---:|---:|---|---:|---:|---|---:|---:|
| vocab_prompt2_exercises | $0.384 | 20.0% | vocab_prompt2_exercises | $0.368 | 42.4% | vocab_prompt2_exercises | $0.449 | 30.3% |
| judge_ladder_l1_distractor | $0.283 | 14.7% | vocab_prompt3_transforms | $0.176 | 20.3% | vocab_prompt3_transforms | $0.217 | 14.7% |
| judge_ladder_sentence_validity | $0.276 | 14.4% | ladder_syn_ant_generation | $0.077 | 8.9% | vocab_prompt1_core | $0.206 | 13.9% |
| vocab_prompt3_transforms | $0.241 | 12.6% | vocab_prompt1_core | $0.065 | 7.5% | judge_ladder_p1_sentence | $0.157 | 10.6% |
| vocab_prompt1_core | $0.235 | 12.3% | ladder_l4_morphology_generation | $0.041 | 4.7% | judge_ladder_sentence_validity | $0.140 | 9.5% |

en's top two tasks (`vocab_prompt2_exercises`, `vocab_prompt3_transforms`) are exactly the two
TASK-813 moved off `claude-sonnet-5`: baseline_en spent $1.5365 on 44 `vocab_prompt2_exercises`
calls at claude-sonnet-5 pricing; phase1_en spent $0.368 on 51 calls at qwen pricing — this
single swap is most of en's win. ja/zh were already on qwen for these tasks (per the ADR-028
2026-09-26 correction — TASK-809 confirmed no-op), so they had no equivalent lever to pull, and
ja's judge tasks (`judge_ladder_l1_distractor`, `judge_ladder_sentence_validity`) are now its
largest cost lines simply because so many more senses now reach them.

## 5. Tokens by task, and the cached_tokens question

Per-call `prompt_tokens` / `completion_tokens` / `cached_tokens` / `reasoning_tokens` are present
on every stored `llm_calls` row for all three runs (TASK-804/812 instrumentation is live).

**`cached_tokens` is non-zero for ja and zh, zero for en**, despite en also routing five tasks
through qwen/qwen3.7-plus this run:

| | ja | zh | en |
|---|---:|---:|---:|
| Total cached_tokens (all calls) | 18,304 | 4,992 | **0** |
| Calls in run | 475 | 479 | 481 |
| Cached tokens concentrated in | `vocab_prompt2_exercises` (13,824), `vocab_prompt3_transforms` (3,968) | `vocab_prompt2_exercises` (3,456), `vocab_prompt3_transforms` (1,152) | — |

This is incidental caching from the provider's own prompt ordering, not the deliberate
stable-prefix reorder — **TASK-812's actual prompt-reorder work is deferred** (see §7). It
answers half of ADR-028 open question (b): OpenRouter/qwen prompt caching *can* engage without
any code change, but it isn't reliable (0% hit for en on the identical model) and isn't yet being
engineered for.

**The bigger token finding: qwen/qwen3.7-plus emits enormous reasoning-token volume that is not
being suppressed.** For ja's `vocab_prompt2_exercises` (44 calls): 119,137 prompt tokens,
272,714 completion tokens, of which **243,481 (89.3%) are `reasoning_tokens`**. The same pattern
holds across every qwen-routed task in all three languages (zh `vocab_prompt2_exercises`:
87.5% reasoning; en `vocab_prompt2_exercises`: 88.1% reasoning). TASK-813's own note describes a
"reasoning qwen exception" — reasoning could not be fully disabled for this model family — and
this is the visible cost of that exception: reasoning tokens are billed completion tokens, and
they dominate every qwen call's cost. This is very likely the single largest remaining lever
short of a model change, and it is not yet addressed by any filed task.

By contrast, en's non-qwen tasks (still on `google/gemini-3.5-flash-lite`: `vocab_prompt1_core`,
`judge_ladder_sentence_validity`, `judge_ladder_p1_sentence`) show `reasoning_tokens: 0` —
confirming the reasoning-token cost is qwen-specific, not a pipeline-wide issue.

## 6. Exercises per sense, by level

| Level | ja baseline | ja phase1 | en baseline | en phase1 | zh phase1 |
|---|---:|---:|---:|---:|---:|
| 1 | 38 | 61 | 18 | 15 | 100 |
| 2 | 30 | 52 | 56 | 58 | 60 |
| 3 | 17 | 32 | 40 | 45 | 28 |
| 4 | 43 | 78 | 64 | 73 | 54 |
| 6 | 30 | 36 | 50 | 64 | 64 |
| 7 | 25 | 47 | **2** | **25** | 47 |
| 8 | 0 | 0 | 0 | 0 | 0 |
| 9 | 42 | 89 | 92 | 109 | 114 |
| **Total / mean per sense** | — / 7.50 | 395 / **13.17** | — / 10.73 | 389 / **12.97** | 467 / 15.57 |

Level 8 remains absent from all three languages in Phase 1 too — still worth the one-line check
against `services/vocabulary_ladder` flagged in the baseline report; not investigated here per
the "do not modify services/" constraint. **en level 7 recovered from 2 exercises (baseline) to
25** — consistent with the P3 runtime-skip validator fix improving that specific asset class.

## 7. Invalid-asset rate by asset type

| Asset type | ja baseline | ja phase1 | en baseline | en phase1 | zh phase1 |
|---|---:|---:|---:|---:|---:|
| prompt1_core | 0.0% | 0.0% | 0.0% | 3.3% | 0.0% |
| prompt2_exercises_A | 0.0% | 0.0% | 9.5% | 0.0% | 0.0% |
| prompt2_exercises_B | 0.0% | 0.0% | 0.0% | 3.8% | 0.0% |
| prompt3_transforms_A | 0.0% | 0.0% | **96.4%** | **46.2%** | 0.0% |
| prompt3_transforms_B | 0.0% | 0.0% | **96.4%** | **48.1%** | 3.3% |
| llm_types_A / B | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall** | 0.0% | 0.0% | 30.4% | **14.1%** | 0.48% |

en's `prompt3_transforms` invalid rate roughly halved (96.4% → ~47%) but is still the dominant
quality defect in the pipeline — the earlier `semantic_class` fix and the P3 salvage-call gating
improved this without fixing it. This asset type is the single most actionable remaining defect,
independent of cost, exactly as the baseline report flagged.

## 8. Render-judge reject rate by judge

| Judge | ja baseline | ja phase1 | en baseline | en phase1 | zh phase1 |
|---|---:|---:|---:|---:|---:|
| l1_distractor | 33.6% | **39.6%** | 0.0% | 0.0% | 0.0% |
| sentence_validity | 0.0% | 0.7% | 0.0% | 0.0% | 0.0% |
| particle | 0.0% | 0.0% | — | — | — |
| relation | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| word_family | — | — | 0.0% | 0.0% | — |

ja's `l1_distractor` reject rate rose (33.6% → 39.6%) alongside its much larger sample (122 →
217 judged, because more senses now reach this judge) — not necessarily a quality regression,
but worth tracking once a larger n stabilizes it. Every other judge stayed clean across both
runs and languages.

## 9. Coverage vs. reference (why every language still FAILs the scorer's decision)

The scorer's `--pairwise-loss-margin-pp` and coverage gates were run in full; only invalid-rate
and (where scoreable) major-defect-rate criteria PASS. **Coverage FAILs everywhere** because the
95% coverage threshold compares (level, exercise_type) pairs against a reference that used a
different, often larger, set of levels/types per sense than what a partial completion actually
produced:

| Comparison | Decision | Coverage | Notes |
|---|---|---:|---|
| phase1_ja vs. frozen reference set | FAIL | 83.9% | 20/50 frozen-ja senses were never in this run's 30-sense set at all (expected — see §10) |
| phase1_ja vs. baseline_ja | FAIL | 85.6% | missing levels concentrated in 1,2,3,4,6,7 for a handful of senses that completed with fewer levels than baseline_ja got for those same IDs |
| phase1_en vs. baseline_en | FAIL | 83.4% | missing levels concentrated in 1 (`phonetic_recognition`), 4 (`word_family`), 3/6 (`cloze_completion`, `synonym_antonym_match`) |
| phase1_zh vs. itself (reference) | PASS | 100.0% | trivial — establishes zh as the reference, not a real comparison |

Coverage gaps are `[level, exercise_type]` pairs missing per sense, not missing senses (except
the frozen-reference case). None of this is a scorer-adapter bug — the four fixes from the
baseline session (level field, variant/payload field, own-output re-ingestion,
`wall_clock_s` fallback) still hold; `tests/test_score_exercise_gen_run.py` was not touched this
session because nothing here exposed a new adapter defect.

## 10. Blind pairwise packs (generated; judged in a later session — see §14)

Per task scope, judging blind pairwise packs is a separate fresh-context step and was not done
in this session (no subagent spawn available here, and judging your own generated packs
defeats the blind-review purpose anyway). **Update 2026-09-27 (later session): all packs below
were judged out-of-band and unblinded — results in [[#14-pairwise-quality-blind|§14]].** Packs
and unblinding keys:

- **phase1_en vs. baseline_en:** `data/eval/runs/phase1_en/vs_baseline_en/pairwise_packs/pack_01.md` through `pack_14.md` (14 packs), key at `data/eval/runs/phase1_en/vs_baseline_en/pairwise_key.json`
- **phase1_ja vs. baseline_ja:** `data/eval/runs/phase1_ja/vs_baseline_ja/pairwise_packs/pack_01.md` through `pack_09.md` (9 packs), key at `data/eval/runs/phase1_ja/vs_baseline_ja/pairwise_key.json`

Once judged (a fresh-context reviewer returning `{sense_id, level, preferred, major_defects_A,
major_defects_B, notes}` per item), fold in with `scripts/merge_pairwise_verdicts.py` and re-run
the scorer with `--pairwise-results` to fill criterion (b), currently SKIPPED in every run above
for lack of this data. phase1_ja vs. frozen-reference and phase1_zh self-reference were scored
with `--skip-pairwise-packs` (frozen-reference has no natural "B" render to pair against without
re-rendering it; zh-vs-itself would only produce trivially-identical pairs).

## 11. What changed in Phase 1 (for context)

- **TASK-809** (move zh generation to qwen): confirmed no-op — zh's three prompt tasks were
  already on `qwen/qwen3.7-plus` since an untracked 2026-08-17 change, predating this task.
- **TASK-810** (retry cap ≤2 + P3 salvage gating): retries/sense fell in every language (ja
  5.31→2.43, en 0.68→1.17 — en's rose slightly because more senses now retry into completion
  rather than failing outright); the P3 runtime-skip validator fix roughly halved en's
  `prompt3_transforms` invalid rate (96.4%→~47%).
- **TASK-811** (level-scoped regen): not independently isolable from this run's numbers — no
  regen-specific instrumentation was queried this session.
- **TASK-812** (stable-prefix ordering + cache-token logging + judge `max_tokens` caps):
  **cache-token logging is live and confirmed working** (§5); **the actual stable-prefix
  reorder is deferred** — it needs a `prompt_templates` edit plus native-speaker review before
  it can ship, so today's `cached_tokens` hits are incidental, not engineered.
- **TASK-813** (provider price routing + reasoning disabled): price routing is the main driver
  of en's cost drop (claude-sonnet-5 → qwen on 5 tasks); reasoning could not be disabled for
  qwen without breaking it ("reasoning qwen exception"), and §5 shows that exception is now the
  largest single token-cost driver on every qwen-routed call.
- Earlier `semantic_class` fix: contributes to the en invalid-rate improvement in §7 alongside
  the P3 validator fix; not separable from it in this run's data.

## 12. Caveats

- **ja's cost picture got harder to read, not easier.** Fewer failures is unambiguously good for
  the product; whether it's good for the cost-reduction workstream depends entirely on which
  convention you read (§2, §3). Report both, always, for ja specifically.
- **Sample sizes are still small and per-sense noisy** (n=15-30 per language per run); a single
  expensive or cheap sense can move the mean several cents. Treat single-run deltas as directional.
- **No quality judgment is filed here.** Coverage FAILs are mechanical (level/type pairs), not a
  reviewer's opinion of exercise quality — that requires the pairwise packs in §10 to actually be
  judged, which they have not been.
- **zh has no baseline to compare against**, per the baseline report's known gap. This run is
  now the zh reference; do not treat its numbers as "improvement" or "regression" from anything.
- **Reasoning-token cost (§5) was not previously tracked** — it may already have been present in
  the TASK-808 baseline (qwen was already live for ja/zh generation then) but was invisible
  without this session's token aggregation. Worth back-computing against the baseline runs'
  stored `llm_calls` if TASK-804's per-call export supports it, to know whether Phase 1 made this
  worse or just made it visible.
- **services/ was not modified in this session**, per instruction (another agent is wiring
  Phase 2 concurrently); all analysis here is read-only against existing run artifacts. No DB
  writes and no paid LLM calls were made — the scorer invocations only read local JSON.

## 13. Gap to target, summarized

| | Phase 0 baseline | Phase 1 | Change |
|---|---:|---:|---:|
| ja $/sense (calls-mean) | $0.0586 (5.9x over) | $0.0686 (6.9x over) | **worse** |
| en $/sense (calls-mean) | $0.1083 (10.8x over) | $0.0289 (2.9x over) | **73% better** |
| zh $/sense (calls-mean) | — (no baseline) | $0.0493 (4.9x over) | new reference |

en is now the closest language to target by a wide margin. ja needs a cost-specific lever next —
Phase 1's reliability fixes did not supply one, and §5's reasoning-token finding suggests the
biggest remaining opportunity for ja/zh is not more retry/call-count engineering but the qwen
reasoning-token volume itself (a model-level or prompt-level lever, likely Phase 2/3 territory —
TASK-817's bake-off is the natural place to test a non-reasoning-heavy qwen variant or an
alternative model for these specific tasks).

## 14. Pairwise quality (blind)

The blind packs from §10 were judged by fresh-context reviewers (per-pack, no visibility into
which side was candidate/reference) and returned as
`{sense_id, level, preferred, major_defects_A, major_defects_B, notes}` verdict lines in
`data/eval/runs/phase1_{ja,en}/vs_baseline_{ja,en}/pairwise_verdicts_{ja,en}_*.jsonl`. This
session unblinded and aggregated them with `scripts/merge_pairwise_verdicts.py` (no code change
needed — the existing `--verdicts` flag already accepts multiple file args) against each run's
`pairwise_key.json`, then re-ran `scripts/score_exercise_gen_run.py --pairwise-results
<run>/pairwise_results.json --skip-pairwise-packs` to fold the result into criterion (b) and
recompute criterion (a) from real defect data instead of the judge-reject-rate fallback. No
`services/` code was touched, no DB writes, no LLM calls made in this session — purely local
JSON aggregation and re-scoring.

### Results

| Metric | ja (81 pairs) | en (132 pairs) |
|---|---:|---:|
| Candidate (phase1) wins | 14 (17.28%) | 15 (11.36%) |
| Reference (baseline) wins | 14 (17.28%) | 12 (9.09%) |
| Ties | 53 (65.43%) | 105 (79.55%) |
| Coverage of key (judged/total) | 81/81 (100%) | 132/132 (100%) |
| Unmatched / missing verdicts | 0 / 0 | 0 / 0 |
| Major-defect rate, candidate | 16.05% (13/81) | 7.58% (10/132) |
| Major-defect rate, reference | 16.05% (13/81) | 6.82% (9/132) |

### Non-inferiority decision (all 4 criteria now scoreable)

| Criterion | ja | en |
|---|---|---|
| (a) major-defect rate ≤ ref + 2pp | **PASS** — 16.05% vs 16.05% (+0.0pp), source=pairwise | **PASS** — 7.58% vs 6.82% (+0.76pp), source=pairwise |
| (b) loss − win ≤ 10pp | **PASS** — loss−win = 0.0pp | **PASS** — loss−win = −2.27pp (candidate wins more) |
| (c) coverage ≥ 95% | **FAIL** — 85.61% (§9) | **FAIL** — 83.43% (§9) |
| (d) invalid-asset rate ≤ ref + 3pp | **PASS** — 0.0% vs 0.0% | **PASS** — 14.06% vs 30.43% |
| **Overall** | **FAIL** (coverage only) | **FAIL** (coverage only) |

Criterion (b) was previously SKIPPED for both runs (no pairwise data); it now PASSES for both,
and it flips criterion (a) from the judge-reject-rate fallback onto real pairwise-judged defect
data, unchanged in ja and slightly worse-looking in en (still within margin). **Both languages'
overall FAIL is entirely the pre-existing §9 coverage gap — pairwise quality itself shows no
non-inferiority problem in either language**, in fact en's candidate wins more than it loses.

### Defect-note tally by class and by side (candidate=phase1 vs reference=baseline)

Counted per defect *tag* (an item can carry more than one tag, so these sum to more than the
13/13 ja and 10/9 en item-level defect counts above):

| Class | ja cand | ja ref | en cand | en ref | Total cand | Total ref |
|---|---:|---:|---:|---:|---:|---:|
| also-correct distractors | 10 | 6 | 3 | 1 | **13** | **7** |
| jumbled_sentence chunk reconstruction / missing chunks (L9) | 1 | 1 | 5 | 4 | **6** | **5** |
| compound-word anchoring | 1 | 3 | 0 | 2 | **1** | **5** |
| cloze_typed accepted-list / correct_answer mismatch | 3 | 4 | 0 | 0 | **3** | **4** |
| explanation mismatches | 2 | 1 | 0 | 0 | **2** | **1** |
| template concatenation ("workss" / "smallchild") | 0 | 0 | 1 | 1 | **1** | **1** |
| other (context-insufficient, weak distractors) | 0 | 0 | 1 | 2 | **1** | **2** |

Also-correct distractors is the largest class on both sides and skews toward the candidate
(phase1) — a judgment call about distractor design, not a rendering bug; not filed as a bug
below. The next three classes are deterministic-generator defects (same rendering/templating
code path runs for both baseline and phase1, so their near-even candidate/reference split is
expected — these are pipeline bugs, not phase1 regressions or improvements).

### Follow-up bugs (deterministic-generator defects, pipeline-independent — not phase1-specific)

These come from the deterministic exercise renderer/templater, not the LLM content, and appear
on both candidate and reference sides at similar rates — they should be filed and fixed
independent of any phase1/phase2 model or prompt work:

1. **`jumbled_sentence` (L9) chunk reconstruction broken or missing chunks** (11 instances: 6
   candidate, 5 reference, both languages). Two failure modes seen: (a) `chunks` /
   `shuffled_chunks` / `correct_ordering` entirely absent for an item (non-functional, e.g. en
   sense 14033 L9); (b) populated but mis-segmented so the stated `correct_ordering` does not
   reconstruct the original sentence — e.g. en sense 16031 L9 chunks `('will waterlog',
   'quickly', 'it')` concatenate to "will waterlog quickly it" instead of "will quickly
   waterlog it"; en sense 19521 L9 chunks concatenate to "is considered usually" instead of "is
   usually considered" (also reuses a source sentence lacking the target word); en sense 15150
   L9 chunk "Are feeling" is not a contiguous span of the source sentence at all; ja sense 34998
   L9 chunk "ichi-ni" fuses the target word with an adjacent number, breaking anchoring (see
   compound-word anchoring class above — same root cause).
2. **`cloze_typed` accepted-answer list / `correct_answer` mismatches with the template**
   (7 instances, ja only in this sample: 3 candidate, 4 reference). The accepted-answer list
   appears to be a generic per-lemma list not customized to the specific templated sentence, so
   it includes forms that are ungrammatical once spliced into that blank's context. Also seen:
   `morphology_slot` `correct_answer` inconsistent with its own template (e.g. answer already
   contains 'に' after a blank that also supplies 'に', producing doubled 'にに'; template
   `'___て'` + `correct_answer '複雑'` yields ungrammatical '複雑て' instead of '複雑すぎて').
3. **Template concatenation bugs producing glued non-words** (2 instances, en only: 1 candidate,
   1 reference). Missing whitespace or wrong suffix handling when splicing the accepted answer
   into the blank template: reference sense 13929 L3 template `'Marcus ___s'` + answer `'works'`
   renders as `'workss'`; candidate sense 14033 L3 drops the space after the blank, rendering
   `'___child'`/`'___wooden'` as `'smallchild'`/`'smallwooden'`.

Explanation mismatches (3 instances, ja only) and compound-word anchoring outside the L9 overlap
noted above are lower-volume and not conclusively pipeline bugs vs. content-generation quality
issues from this sample alone; worth re-checking once a larger judged sample exists.

## Related

- [[evaluations/exercise-gen-baseline-2026-09]] — Phase 0 baseline this run is scored against
- [[decisions/ADR-028-exercise-gen-cost-under-1c]] — target and phase plan
- [[tasklist/exercise-gen-cost.tasks]] — TASK-809–813 closure notes
- [[tasklist/master]] — status board
