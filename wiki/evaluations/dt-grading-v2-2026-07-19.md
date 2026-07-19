---
title: "DT Grading Eval — Evidence-First v2 Final (2026-07-19)"
type: evaluation
status: complete
date: 2026-07-19
harness: scripts/run_dt_grading_eval.py (--framework-v2 --rubric-file, both new this pass)
metrics_module: services/dual_translation/eval_metrics.py
gold_sets: tests/fixtures/dt_gold/{en,zh,ja}.json (TASK-621, frozen)
---

# DT Grading Eval — Evidence-First v2 Final (2026-07-19)

TASK-632's full harness run on the **completed v2 stack**: Detector → Verifier → Python verdict
merge → derived severity-weighted scoring ([[algorithms/evidence-first-grading.tech]] §2/§4/§6),
with the TASK-630 Explainer live on every error-bearing item. This is the run that flipped
`Config.DT_FRAMEWORK_V2` to **default ON** — v2 is now the live grading flow;
[[algorithms/translation-grading-cascade]] (v1) is the `DT_FRAMEWORK_V2=false` rollback path.

- **Grader:** `grade_submission(framework_v2=True)` — framework passed EXPLICITLY by the new
  `--framework-v2` flag (the ambient env var is ignored; runs are self-documenting).
- **Rubric:** the **v6 candidate** config, loaded from `migrations/dt_rubric_v6_seed.sql` via the
  new `--rubric-file` flag (evaluate-before-activate: the config cache is pre-seeded, the live DB
  is untouched). So these numbers correspond to the **v2 + rubric v6** stack. ⚠️ v6 is **not yet
  applied live** (this session's permission classifier denied every DB-write wire); live grading
  uses v5 descriptors — identical scoring keys, only descriptor text differs — until
  `dt_rubric_v6_seed.sql` is applied manually (TASK-629 carry).
- **Taxonomy:** live v5. **Slugs (router-resolved):** EN `google/gemini-2.5-flash-lite` (Detector)
  + `google/gemini-3.5-flash` (Verifier); JA/ZH `qwen/qwen3.6-flash` + `qwen/qwen3.7-plus`.
  Explainer rides the tier-1 (cheap) slug.
- **Cost:** EN **$0.74 measured** (54 calls, 80K in / 74K out, single invocation). JA/ZH ran
  across several resumed invocations; the checkpoint does not persist per-item token usage, so
  their report meta under-counts (a known harness gap — see Findings). Whole-pass estimate
  **≈ $2.5–3.5**, dominated by `qwen/qwen3.7-plus` output tokens (one JA verifier+explainer pair
  emitted 33K output tokens).

## Headline

**The Detector/Verifier split + derived scoring recovers the band-agreement QWK that Phase 1 gave
back, while pushing detection precision to ceiling on EN.** EN: span precision 1.000 (zero false
spans), clean-FP 0.000, overall QWK **.824** (v1 never exceeded .516). JA holds its detection
gains (span F1 .880) with severity exact at its best-ever (.818). The two model-judged dimensions
(naturalness/range) remain the weak signal on all L2s — QWK ≈ 0 against a gold set that barely
varies them (see Findings §3).

## Per-L2 summary (v2, this run)

| L2 | span P | span R | span F1 | TP/FP/FN | subtype acc | sev exact | sev w/in-1 | clean FP | overall QWK (exact/adj) |
|----|--------|--------|---------|----------|-------------|-----------|------------|----------|--------------------------|
| EN | 1.000 | 0.889 | **0.941** | 24/0/3 | **1.000** (24/24) | 0.625 | 1.000 | **0.000** | **0.824** (.90/1.00) |
| JA | 0.957 | 0.815 | **0.880** | 22/1/5 | 0.864 (19/22) | **0.818** | 1.000 | 0.100 (1 item) | 0.419 (.83/1.00) |
| ZH | 0.917 | 0.846 | **0.880** | 22/2/4 | 0.818 (18/22) | 0.727 | 1.000 | 0.200 (2 items) | 0.245 (.83/.97) |

Per-dimension QWK (EN / JA / ZH): accuracy .778 / .412 / .570; understandability .746 / .332 /
.577; fidelity .487 / .371 / **.891**; range .000 / .000 / 1.000 (degenerate — constant rater);
naturalness .099 / .053 / .020.

## Per-phase metric progression (622 → 632)

Values from [[evaluations/dt-grading-baseline-2026-07-05]] per-task updates; **632 = this run**
(v2 flow + v6 candidate rubric; all earlier phases are the v1 flow).

**Span F1**

| L2 | 622 baseline | 623 tier-0 fix | 624 prompts | 625 triad | 626 taxonomy v5 | **632 v2** |
|----|--------------|----------------|-------------|-----------|------------------|------------|
| EN | .293 | .494 | .553 | .553 | .543 | **.941** |
| JA | .194 | .554 | .725 | (deferred) | .696 | **.880** |
| ZH | .000 | .597 | .658 | .686 | .639 | **.880** |

**Clean-passage FP rate** (622's 0.000 was a Tier-0 short-circuit artifact — clean items never
reached the grader)

| L2 | 622 | 623 | 624 | 625 | 626 | **632 v2** |
|----|-----|-----|-----|-----|-----|------------|
| EN | (.000) | .300 | .200 | .200 | .200 | **.000** |
| JA | (.000) | .700 | .000 | — | .000 | **.100** |
| ZH | (.000) | .400 | .100 | .100 | .100 | **.200** |

**Overall-band QWK**

| L2 | 622 | 623 | 624 | 625 | 626 | **632 v2** |
|----|-----|-----|-----|-----|-----|------------|
| EN | .516 | .512 | .467 | .512 | .512 | **.824** |
| JA | .186 | .571 | .430 | — | .429 | **.419** |
| ZH | .000 | .216 | .255 | .412 | .322 | **.245** |

**Subtype accuracy** (626 onward is the finer v5 17-way tagset for JA/ZH)

| L2 | 622 | 623 | 624 | 625 | 626 | **632 v2** |
|----|-----|-----|-----|-----|-----|------------|
| EN | .333 | .684 | .714 | .714 | .727 | **1.000** |
| JA | 1.000 (n=3) | .913 | .760 | — | .875 | **.864** |
| ZH | n/a | .826 | .792 | .833 | .739 | **.818** |

## Gate assessment (TASK-628 AC)

- ⚠️ **FP rate (verifier rejection): decisively met on EN only.** EN .200 → **.000** with span
  precision 1.000 — the Verifier's reject/adjust pass eliminated every spurious EN span. JA
  regressed .000 → **.100** (one clean passage, one error) and ZH .100 → **.200** (two clean
  passages, two errors). Not blockers — span precision stays ≥ .917 everywhere and the extra
  flags are single-item effects on n=10 clean sets — but JA/ZH clean-FP is the metric to watch in
  production traces; the arbiter escalation (`DT_TIER3_ARBITER_ENABLED`, default OFF) is the
  designed lever if it recurs.
- ✅ **Span F1 not regressed — strongly up on all three** (EN +.398, JA +.184, ZH +.241 vs 626).
- ✅ **QWK not regressed (within variance):** EN +.312 (the Phase-1 give-back fully recovered and
  exceeded — derived scoring is doing what ADR-019 predicted); JA −.010 (flat); ZH −.077
  (.322→.245, inside ZH's documented ±.1 identical-code run variance — 625→626 swung −.090 with
  grading logic untouched; adjacent agreement .967). ZH fidelity QWK hit **.891**, its best ever.
- ✅ Severity within-one 1.000 everywhere; JA severity exact best-ever (.818).
- ✅ Failure modes: zero items skipped, zero `provisional` grades, zero fell-open silent
  full-marks (the v2 both-fail path never triggered on 90 items).

## Findings & recommended improvements (TASK-632 code/harness review)

Condensed; the full report was delivered with the TASK-632 session summary.

1. **Harness — checkpoint must persist per-item usage.** Resumed runs under-report cost/tokens
   (records carry no `tokens`/`cost`), so JA/ZH spend here is estimated. Add
   `{"tokens_in","tokens_out","model_slugs"}` to each checkpoint record and sum on load.
2. **Harness — wall-clock latency is now the JA bottleneck, and it is unmeasured.** JA v2 items
   took ~2–3 min each (sequential Detector→Verifier + Explainer on `qwen/qwen3.7-plus`, which
   emits huge outputs — likely reasoning tokens). Record per-item latency; consider a
   `max_tokens` cap or a non-reasoning verifier slug for JA/ZH; consider grading items
   concurrently (bounded pool) — the retry wrapper already isolates failures.
3. **Evals — naturalness/range carry no signal** (QWK ≈ 0 on all L2s): the gold set's expected
   bands barely vary on those dims, so agreement is base-rate. Extend the gold sets with
   naturalness/range-varied items (unidiomatic-but-correct reproductions; flattened-register
   reproductions) and seed the missing `exemplars.verifier` few-shots the Verifier prompt already
   knows how to render.
4. **Evals — n=30/L2 makes QWK swing ±.1 between identical-code runs** (see ZH 625→626). Report
   bootstrap CIs next to point metrics; treat ±.1 as noise in gates.
5. **Engine — `_fetch_active_scalar` caches `None` forever** on a transient read failure
   (`grader_cascade.get_active_rubric_version`), pinning `prompt_version: null` into every trace
   for the process lifetime. Don't cache the failure.
6. **Engine — highlights are not reconciled against the Verifier merge:** a "what worked"
   highlight can overlap a span the Verifier's `added_errors` marks wrong. Filter highlights that
   overlap final error spans at merge time.
7. **EN severity exact (.625) is now the weakest EN metric** — severity anchors are exactly what
   rubric v6's parenthetical error profiles supply; **apply v6 live** (the one owed step).

## Reproduce

```
python scripts/run_dt_grading_eval.py --l2 {en|zh|ja} --out report.md --live \
    --framework-v2 --rubric-file migrations/dt_rubric_v6_seed.sql --resume ckpt.jsonl
```

`--framework-v2` selects the v2 flow explicitly; `--rubric-file` evaluates a candidate rubric
without activating it; `--resume` reuses already-paid items across interrupted invocations.

## Related Pages
- [[evaluations/dt-grading-baseline-2026-07-05]] — v1 baseline + phase updates (622–626)
- [[algorithms/evidence-first-grading]] / [[algorithms/evidence-first-grading.tech]] — the v2 framework (now complete)
- [[algorithms/translation-grading-cascade]] — v1, deprecated (rollback path)
- [[tasklist/archive/evidence-first-grading.tasks]] — TASK-621..632
- [[decisions/ADR-019-evidence-first-scoring]]
