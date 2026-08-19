---
title: Judge Evaluation Campaign System — Technical Specification
type: feature-tech
status: planned
prose_page: judge-eval-campaign.md
last_updated: 2026-08-17
dependencies:
  - "scripts/measure_entailment_ab.py — the working 7-arm harness this generalises"
  - "services/model_arena/pricing.py:fetch_model_list — existing OpenRouter /models discovery + cache"
  - "services/exercise_generation/judges/base.py — THRESHOLD_ACCEPT/REJECT, classify(), safe_accept()"
  - "services/test_generation/schemas.py:AnswerEntailmentVerdict"
  - "llm_calls table — measured cost_usd read-back"
  - "dim_question_types — question_type_id -> type_code mapping"
  - "TASK-723 (Likert unification) — sequencing dependency, would invalidate 2 of 6 metric modules"
breaking_change_risk: low
---

# Judge Evaluation Campaign System — Technical Specification

**Deferred 2026-08-17. Nothing built.** This records the design so it is
recoverable. See [[features/judge-eval-campaign]] for rationale.

## Scope note

"200 A/B tests" is specified here as **one campaign screening ~200 candidate
models against shared gold labels**, not 200 independent pairwise A/Bs. Because
every arm is scored against gold rather than against another arm, pairwise
framing doubles the call budget for no additional information.

## Architecture Overview

Refactor, not rewrite. [scripts/measure_entailment_ab.py](../../scripts/measure_entailment_ab.py)
already implements correct metrics; extract them into a library and add
discovery, gating, tiering and reporting on top.

```
scripts/run_judge_ab_campaign.py      (orchestrator CLI)
scripts/build_entailment_gold_set.py  (dataset builder)
scripts/measure_entailment_ab.py      (existing CLI, becomes thin wrapper — behaviour preserved)
        |
        v
services/judge_eval/
    items.py       dataset load, item expansion, stratification
    discovery.py   wraps pricing.fetch_model_list; price/context/modality filters; denylist
    preflight.py   Tier-0 gate
    arms.py        execution, per-model semaphore, checkpoint/resume
    metrics.py     AUC, Wilson CI, FR/FA, collapse detection, best threshold, pairwise agreement
    cost.py        paginated llm_calls read-back
    report_html.py self-contained HTML
```

`services/judge_eval/` follows the placement convention set by
`services/model_arena/` and `services/dual_translation/eval_metrics.py` — eval
logic lives under `services/<domain>/`, not in `scripts/`.

## The tiered funnel

A flat 200 × 1000 sweep is 200,000 calls ≈ 35 h at the current 8 workers
(measured throughput 2026-08-17: 46 calls/min). Not executable.

| Tier | Purpose | Arms | Items/arm | Calls | Est. cost | Est. wall clock |
|---|---|---|---|---|---|---|
| 0 — gate | reachability, JSON mode, schema, non-degenerate | ~200 | 6 | 1,200 | ~$0.50 | ~15 min |
| 1 — screen | reject duds | ~150 | 90 | 13,500 | ~$4 | ~1.5 h |
| 2 — full | separate finalists | ~20 | 1,000 | 20,000 | ~$8 | ~2.5 h |
| | | | **total** | **~35k** | **~$13** | **~4.5 h** |

**Sizing rationale (the load-bearing part).** n=90 reliably separates AUC 0.95
from 0.80 — which is all Tier 1 must do. It *cannot* separate 0.995 from 0.985;
that requires n≈1000, which is precisely what Tier 2 spends its budget on. Each
tier is sized to the discrimination it actually has to make, and no finer.

Concurrency: raise global workers 8 → ~32, but impose a **per-model semaphore of
~6**. A real 429 was observed on `bytedance-seed/seed-2.0-mini` on 2026-08-17; a
single global pool trips per-provider limits.

## Database Impact

Reads only; no schema change required.

* `llm_calls` — cost read-back, filtered `pipeline='diag'`, `task_name LIKE 'entail_%'`.
  **Must paginate**: PostgREST caps a select at 1000 rows and returns exactly 1000
  silently, which produced a wrong volume figure during the 2026-08-17 session.
  Use `count='exact'` for counts; `.range(off, off+999)` loops for rows.
  Note `llm_calls` has **no token columns** — `cost_usd` (populated from
  OpenRouter's `extra_body: {usage: {include: true}}`) is the only cost source.
* `dim_question_types` — `id` → `type_code`, mirroring
  [scripts/measure_judge_flag_rate.py:114-131](../../scripts/measure_judge_flag_rate.py#L114-L131).
* `prompt_templates` — read the active judge row per language.

Optional future addition: a `judge_eval_runs` table to persist manifests. Not
required for v1; a JSON manifest on disk is sufficient and simpler.

## Dataset specification

`data/eval/entailment_gold_v1.json` + `entailment_gold_v1.meta.json`.

Item schema extends the existing 150-item sample
(`data/eval/entailment_sample_150.json`) so the current harness can read either:

| field | type | notes |
|---|---|---|
| `qid` | str | source question id — provenance for later adjudication |
| `lang` | int | 1=zh, 2=en, 3=ja |
| `passage` | str | |
| `question` | str | |
| `answer` | str | the correct answer → label 1 |
| `distractors` | list[str] | length 3 → label 0 |
| `type_code` | str | **string**, not `question_type_id` — see gotcha below |
| `gold_source` | str | `"structural"` \| `"human"` — future-proofs adjudication |
| `split` | str | `"screen"` \| `"holdout"` |

* Stratified by **language × `type_code`**. The flag-rate harness showed reject
  behaviour varies by question type, so an unstratified sample confounds the two.
* Deterministic and seeded; `--verify` recomputes the SHA256 and fails on drift.
* `.meta.json` records: content hash, version, build date, seed, source question
  ids, generating model, per-stratum counts.
* **20% `holdout`**, untouched during screening.

**Size — unresolved.** (a) 1000 labelled items ≈ 334 questions (111/lang) → 1,002
items/arm. (b) 1000 questions → 3,002 items/arm, 3× the Tier-2 budget.
Recommendation: (a); ~334 positives supports a ±2% CI on false-reject, which is
the production-relevant metric, and the saved budget buys human adjudication.

## Tier-0 pre-flight gate

Mandatory before any spend. 2 calls × 3 languages per candidate. Asserts:

1. Slug resolves, HTTP 200.
2. `response_format='json_object'` accepted — catches `stepfun/step-3.5-flash`
   (SiliconFlow: `"Json mode is not supported for this model"`).
3. Content non-empty — catches `z-ai/glm-4.7-flash` (empty content on **210/450 =
   47%** of calls on 2026-08-17).
4. Parses to `AnswerEntailmentVerdict` — catches `qwen/qwen3.5-flash-02-23`
   (returns a bare float, not an object, on zh/ja).
5. **Non-degenerate**: reject any model whose confidence equals `THRESHOLD_ACCEPT`
   (0.8) exactly on every probe. That is the `safe_accept()` signature — the
   fail-open path at
   [answer_entailment.py:88-91](../../services/exercise_generation/judges/answer_entailment.py#L88-L91)
   returns exactly this on *any* exception, so a fully-broken model is
   indistinguishable from a permissive one unless checked for explicitly.
6. Record serving `provider_name`. The same OpenRouter slug routes to different
   upstreams with different JSON-mode support, so the real unit of comparison is
   **slug + provider**, not slug.

Persist to `data/eval/model_preflight_cache.json` keyed by slug, with a timestamp
so entries can expire. Repeat campaigns skip known-broken models.

## CLI Surface

### `scripts/run_judge_ab_campaign.py`

- **Purpose:** run a tiered campaign, explicit or autonomous.
- **Arguments:**
  - `--arms "name=slug,..."` — explicit models.
  - `--discover` with `--max-price`, `--min-context`, `--limit` — autonomous selection.
  - `--dataset` (default `data/eval/entailment_gold_v1.json`), `--langs`, `--negatives`.
  - `--tiers 0,1,2`, `--workers 32`, `--per-model-concurrency 6`.
  - `--dry-run` — print planned call counts and projected cost, spend nothing.
  - `--budget-ceiling USD` — abort on breach. **Must treat NULL `cost_usd` as
    fatal, not zero**: a NULL silently disarmed every budget ceiling in this repo
    prior to 2026-08-12.
  - `--resume RUN_ID`.
  - `--out`, `--report`.
- **Returns:** results JSON + run manifest + HTML report.
- **Errors:** aborts before spend on dataset hash mismatch, empty candidate set
  after gating, or projected cost over ceiling.
- **Side effects:** writes `llm_calls` rows under `pipeline='diag'` so diagnostic
  spend never contaminates per-pipeline production cost reporting.

### `scripts/build_entailment_gold_set.py`

- `--size`, `--seed`, `--langs`, `--holdout-frac`, `--out`, `--verify`.
- `--verify` recomputes the content hash and exits non-zero on drift.

## Metrics (lift from the working harness)

`metrics.py` takes these unchanged from
[measure_entailment_ab.py](../../scripts/measure_entailment_ab.py): `auc`
(Mann-Whitney identity, ties = 0.5), `wilson`, false-reject/false-accept at live
thresholds, distinct-value collapse count, best-achievable balanced-accuracy
threshold, pairwise agreement with who-was-right.

**Two are Likert-fragile.** The live-threshold error rates and the
score-distribution collapse check both assume a continuous 0–1 confidence. TASK-723
replaces that with a 1–5 integer scale, which retires both. This is the sequencing
dependency.

## Report Specification

`report_html.py` → one self-contained file. **No precedent exists in this repo**
(no `<html>`-emitting Python in `scripts/` or `services/`), so this is new code,
not a mirrored pattern.

* Inline CSS and inline SVG only. No CDN, no external fonts — required so the page
  is publishable as an artifact and readable offline.
* Theme-aware light/dark; horizontal scroll contained to wide tables.
* Sections: leaderboard; per-language AUC/FR/FA with Wilson CIs;
  score-distribution collapse; measured cost per call and projected monthly;
  funnel attrition (what died at which tier, with the reason string).
* **Caveats render at the top of the page, not in a footnote:**
  1. labels are structural → every AUC is a lower bound;
  2. false-reject maps to production but **false-accept is a proxy** — production
     never sends this judge a distractor, so the negative class stands in for
     answer hallucination rather than reproducing it;
  3. the selection effect from screening N models (below).
* Regenerable offline from results JSON + manifest, mirroring the existing
  `--report-only` convention.

## Key Architectural Decisions

1. **Tiered funnel over flat sweep.**
   - *Rationale:* 82% fewer calls; 35 h → 4.5 h. Makes the feature executable at all.
   - *Rejected:* flat sweep (not executable); adaptive bandit allocation (better
     sample efficiency, far more complexity, and harder to explain to a human
     reading the report).
2. **Measured `cost_usd`, never list price.**
   - *Rationale:* list prices mispredicted actual cost by up to 4.8× on
     2026-08-17, because output-token volume dominates. `gemini-3.7-flash` was the
     single most expensive arm despite mid-range list pricing.
   - *Rejected:* `pricing.compute_cost()` from list prices — accurate only given
     real token counts, which `llm_calls` does not store.
3. **Refactor the existing harness rather than replace it.**
   - *Rationale:* its metrics are correct and its results are already cited in a
     published evaluation. Behaviour-compatible refactor keeps those reproducible.
   - *Rejected:* greenfield harness (discards working, reviewed metric code).
4. **Persisted pre-flight denylist.**
   - *Rationale:* the three broken models found on 2026-08-17 were discovered by
     spending money. That knowledge belongs in the repo, not a transcript.
5. **Lock-box holdout split.**
   - *Rationale:* see Security/Validity below. Without it, screening 200 models
     against one fixed set produces a winner whose margin is partly selection noise.

## Security Considerations

Not user-facing; no auth surface. The relevant risks are spend and validity.

* **Autonomous model selection spends money without a human naming the target.**
  `--dry-run` plus a fail-closed `--budget-ceiling` are the required guardrails,
  not optional conveniences.
* API key handling: `services/llm_service.py:57` freezes `OPENROUTER_API_KEY` at
  **import time**. Any script living outside the repo root must call
  `load_dotenv(<repo>/.env)` explicitly *before* importing any service, or the key
  resolves empty and the OpenAI SDK falls back to `OPENAI_API_KEY`, producing 401s
  that read like a revoked key. Cost several tool calls to diagnose on 2026-08-17.
* **Validity risk — multiple comparisons.** The best of ~200 arms is optimistically
  biased by construction. Mitigation: pre-register the primary metric; report CIs
  not point estimates; confirm only the final 2–3 candidates on the untouched
  holdout; state the selection effect in the report.

## Testing Strategy

Mirror `tests/test_dt_eval_metrics.py` and `tests/test_dt_eval_harness_retry.py`:
pure functions and mocked failure paths, **no live API calls in the test suite**.

| Test file | Covers |
|---|---|
| `test_judge_eval_metrics.py` | AUC against hand-computed fixtures; perfect/inverted/all-tied separation; Wilson at k=0 and k=n; collapse detection |
| `test_judge_eval_preflight.py` | each of the 6 gate conditions via mocked responses, **including the degenerate `safe_accept` case** |
| `test_judge_eval_items.py` | determinism under a fixed seed; stratification proportions; holdout disjoint from screen |
| `test_judge_eval_cost.py` | pagination past 1000 rows; **NULL `cost_usd` fails closed** |
| `test_judge_eval_report.py` | renders with zero external references; wide tables wrapped |

Run: `PYTHONIOENCODING=utf-8 PYTHONPATH=. python -m pytest tests/ -q`
(the explicit `tests/` path is required — omitting it collects nothing).

Regression gate: `python scripts/measure_entailment_ab.py --report-only
data/eval/entailment_ab_2026-08-17.json` must produce byte-identical tables
after the refactor.

## Environment gotchas

* Prefix every invocation with `PYTHONIOENCODING=utf-8` — CJK output raises
  `UnicodeEncodeError` on the Windows console otherwise.
* `.env` overrides code defaults everywhere; verify effective values, not source.
* Runtime model routing lives in the `prompt_templates` DB table, not in code.
* `llm_calls.created_at` is UTC; a local-date filter can silently match nothing.

## Related Pages

- [[features/judge-eval-campaign]] — prose counterpart
- [[evaluations/entailment-judge-model-ab-2026-08-17]] — source results and caveats
- [[tasklist/distractor-judge-calibration.tasks]] — TASK-723 sequencing dependency
- [[database/schema.tech]] — `llm_calls`, `prompt_templates`, `dim_question_types`
