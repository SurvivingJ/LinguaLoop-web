# LinguaLoop Judge Inventory & jev-1.13 Experiment Design Notes

Compiled 2026-09-26. Read-only research; no repo files modified.

---

## 1. Every LLM judge found

### 1a. Ladder/exercise-generation judges — `services/exercise_generation/judges/*.py`

All share infrastructure in `services/exercise_generation/judges/base.py`:
- `JudgeOutcome(verdict, confidence, reason, ...)`, `Verdict = 'accept'|'flag'|'reject'`.
- `classify(confidence: float) -> Verdict` — **legacy** raw 0.0–1.0 confidence mapper (0.8 accept threshold). Only `cloze_distractor_judge` still uses this.
- `schemas.likert_to_verdict` (in `services/test_generation/schemas.py`) — **current** convention: 5-point Likert, 5/4→accept, 3→flag, 2/1→reject. Nearly every judge below has been migrated to this ("v3 Likert contract").
- `log_judge_verdict(task_name, model, verdict, confidence, pipeline)` — writes a **second** `llm_calls` row carrying the classified verdict (the row `call_llm` itself writes always has `judge_verdict=NULL`). Query ground truth via `WHERE task_name LIKE 'judge_%' AND judge_verdict IS NOT NULL`.
- `guard_fail_open`, `accept_item`, `safe_accept` — every judge fails open (accepts) on missing/unparseable/errored output; a judge outage never blocks generation.
- `BatchModeThreadPoolExecutor` — judges run concurrently; contextvars (`sense_id`, `generation_batch_id`) propagate into worker threads.

| File | Function | `llm_calls.task_name` | `prompt_templates.task_name` | Output format | Notes |
|---|---|---|---|---|---|
| `judges/answer_entailment.py` | `judge_answer_entailment()` | `judge_answer_entailment` | `test_answer_entailment` | Likert 1-5 (`response_format='json_object'`, `schema=AnswerEntailmentVerdict`) | v3 (TASK-723); refuses to run against a pre-v3 prompt row (`_is_pre_likert`) because legacy 1.0 == "max confidence accept" collides with Likert 1 == reject. Bands: 5=explicit,4=inferable→accept; 3=partial→flag; 2/1→reject. Pipeline `test_gen`. |
| `judges/l1_distractor.py` | `judge_l1_distractors()` | `judge_ladder_l1_distractor` | `ladder_l1_distractor_judge` | Binary `keep`/`reject` JSON dict per distractor (`response_format='json'`) | Downstream filter for the ja mora-trie L1 renderer per memory notes. |
| `judges/distractor_plausibility.py` | `judge_distractor_plausibility()` | `judge_distractor_plausibility` | `test_distractor_plausibility` | **v7 two-axis** Likert: `fit` + `confusability`, each 1-5, `response_format='json_object'`, `schema=DistractorPlausibilityVerdict`; verdict derived by `schemas.axes_to_verdict` | Two-axis code path exists and is live-safe but **inactive per memory** (`distractor-judge-v7-two-axis`) — old scalar verdict still shipped until TASK-719 activates it. `confidence` carries the *binding* axis's rating. Model: zh/ja on `google/gemini-3.1-flash-lite` (was `qwen/qwen3.6-flash`, was `deepseek/deepseek-v4-flash`) — see migrations below. |
| `judges/particle.py` | `judge_particle()` | `judge_ladder_particle` | `ladder_particle_judge` | Likert 1-5, `response_format='json_object'` | |
| `judges/sentence_validity.py` | `judge_wrong_sentences()` | `judge_ladder_sentence_validity` | `ladder_sentence_validity_judge` | Likert 1-5, `response_format='json'` | Per-sentence verdicts, batch call; logs the *worst* verdict in the batch. |
| `judges/relation.py` | `judge_derivation()` + numbered-candidate helper | `judge_ladder_relation` (`_RELATION_TASK`) and `judge_ladder_word_family` (`_FAMILY_TASK`) | (two prompt rows, name pattern `ladder_*_judge`) | Likert via numbered-candidate prompt, `response_format='json_object'` | |
| `judges/collocation.py` | `judge_collocation_repair()` | `judge_ladder_collocation` | `ladder_collocation_judge` | Likert 1-5 | |
| `judges/translation_uniqueness.py` | `judge_translation_item()` | `judge_translation_uniqueness` | `translation_uniqueness_judge` | Likert 1-5, `response_format='json'` | Likert direction runs toward *keep* (inverse of others) — flagged explicitly in the docstring. |
| `judges/cloze.py` | `judge_distractors()` | `cloze_distractor_judge` (**no `judge_` prefix** — legacy naming) | `cloze_distractor_judge` | Binary `keep`/`reject` dict, `response_format='json'` | Still on the **old 0.0-1.0 float scale** via `base.classify` — the one judge not yet converted to Likert (per `answer_entailment.py`'s own docstring: "until it converts, `judge_confidence` is consistent per task_name but not globally"). |
| `judges/p1_sentences.py` | `judge_p1_sentences()` | `judge_ladder_p1_sentence` | `ladder_p1_sentence_judge` | Likert 1-5, `response_format='json'` | Folds 3 checks per sentence into one rating. |

There is also `services/exercise_generation/cloze_judge.py` (separate from `judges/cloze.py`) — not fully inspected; flag for follow-up if the two are duplicates/predecessors.

### 1b. Topic-generation judge
- `services/topic_generation/agents/tier_fit_judge.py` → `TierFitJudge.judge()` / `.best_tier()`.
  `task_name='judge_topic_tier_fit'`. **Pure binary yes/no**: `{"fits": true|false, "reason": "..."}` — a single reachability question per (topic, tier). `.best_tier()` walks tiers ascending and stops at the first fit (so it's really N independent yes/no calls, not one multi-choice call). Fails open (`fits=True, judged=False`) on any error/timeout/unparseable output. Uses `TIER_READERS` — English prose reader-profiles per tier (see §2) — as the judge's evidence anchor, deliberately not a number, "so the judge is reasoning about a person, not an ordinal."
  **This is the single best candidate in the repo for jev's yes/no (`noul`) mode as a drop-in**, and `.best_tier()`'s ascending-walk shape is exactly what jev's `score`/ordered-scale mode (with a `legend` per tier) could collapse into one call instead of up to six.

### 1c. Vocabulary-curation judges (not exercise-facing, but same call_llm pattern)
- `services/classifier_curation/judge.py` → `judge_nouns()`, task_name `judge_nouns`. Likert 1-5 ("is 个 the only natural classifier → 1"), `response_format='json_object'`, `schema=JudgeRatings`. Model from `config.JUDGE_MODEL`. Fail-open returns all-5.
- `services/counter_curation/judge.py` → mirror of the above for counter words (same task_name `judge_nouns` — **task_name collision between the two pipelines**, distinguishable only by `pipeline`).
- Ground truth exists: `data/classifier_curation/*.json` + `data/classifier_curation/approved_curation.json` are human-reviewed outputs of this judge — usable as accept/reject gold for a classifier-judge comparison.

### 1d. Dual Translation (DT) grading — not file-per-judge, but IS an LLM-judge system
Core files: `services/dual_translation/{grader_cascade.py, scoring.py, tier0.py, prompts.py, router.py, explainer.py}`.

- **Tier 0** (`tier0.py`): deterministic, no LLM — normalizes and diffs; short-circuits to full marks on a normalization-only diff.
- **v1 flow** (legacy, still the flag default off-path): Tier 1 model call scores `accuracy`+`range` directly (1-4 band each); Tier 2 scores `understandability`+`fidelity`+`naturalness` (and re-checks accuracy/range when Tier 1 confidence < 0.6 or Tier 0's diff ratio > 0.3 — those two calls run concurrently in that case).
- **v2 flow** (`Config.DT_FRAMEWORK_V2`, **default ON since 2026-07-19** per memory) = Detector/Verifier cascade:
  - **Detector** (tier1 slug): proposes `errors[]` + `highlights[]`, **no scores**.
  - **Verifier** (tier2 slug): per-error verdict (confirm=0/reject=1/adjust=2) **plus** `naturalness`/`range` judgments — each judgment requires a mandatory evidence span (`_has_valid_evidence`) or it's discarded (never silently defaults to a full mark).
  - **Merge** (pure Python): confirmed+adjusted+added errors.
  - **Derived scoring** (`services/dual_translation/scoring.py`, pure functions, TASK-627 rubric v5/v6): `accuracy`/`fidelity`/`understandability` bands come from **severity-weighted penalty sums** over the merged errors (`severity_weights`/`understandability_weights`/`band_thresholds` live in the active `dt_rubric_version.config` row) — NOT directly model-judged. Only `naturalness` and `range` are still model-judged bands (1-4, `MAX_BAND=4`).
  - Optional **Tier-3 arbiter** (`Config.DT_TIER3_ARBITER_ENABLED`, default OFF) re-adjudicates the whole proposed list when the Verifier rejected ≥50% of items or its confidence < 0.5.
- **Output format**: JSON, numeric-index enums (`CATEGORY_ENUM`/`SOURCE_ENUM`/`SEVERITY_ENUM`/per-pair `subtypes` list) rather than free text — deliberately numeric so the L2-only prompt never has to spell an enum name in the target language.
- **Language-specificity**: prompts are L2-only / numeric-index by design (`prompts.build_system_prompt` etc.) — the model is given the L2 text and answers in numbered indices, not prose, so "native-language prompt" doesn't quite apply the way it does to ladder judges; explanations are rendered from **template tables** per (subtype, L1), never model prose (ADR-015).
- **Model routing**: `services/dual_translation/router.py:resolve_tier(db, tier, l2_language_id)` resolves a per-tier, per-language model slug from a routing table (seeded by `migrations/dual_translation_router_seed.sql`) — not `prompt_templates`.
- **IMPORTANT — logging gap**: DT grading calls go through `services.model_arena.llm_runner.call_model_with_usage(slug, prompt, system_prompt=, temperature=0.0)`, which reuses `services.llm_service.get_client()`'s shared OpenAI-compatible client pool **but does NOT call `_log_llm_call`** — confirmed by grep (`llm_calls`, `task_name`, `log_judge_verdict` all absent from `services/model_arena/llm_runner.py`). **DT grading calls are not represented in the `llm_calls` table at all** — no `task_name`, no `cost_usd`, no `judge_verdict` row. Cost/latency for DT grading must come from elsewhere (the DT eval harness's own token counting — see §3) — this is a real gap for a cost comparison unless a jev-in-DT experiment adds its own logging.
- **Rubric**: v6 is active live (per memory `dt-rubric-v5-derived-scoring` — v6 applied 2026-08-10); `band_thresholds` is flat, not nested as an older tech-spec draft implied.

### 1e. Judge-eval / cost-instrumentation shared plumbing
- `services/llm_service.py` (see §5) — every `call_llm()` invocation writes one `llm_calls` row via `_log_llm_call`, tagged by `pipeline` + `task_name` + `template_version` + `model` + `language_code`, plus `cost_usd`/token counts when the provider (OpenRouter) reports them.
- `services/prompt_service.get_template_config(db, task_name, language_id)` — the per-(task_name, language) lookup every ladder/test-gen judge above calls to get `{template, model, version}` from `prompt_templates`. This is the DB-driven, per-language, per-judge model slug — **this is where a jev arm would be registered** if judges are to keep the same routing convention (a new `prompt_templates` row per judge/language with `model='typesafe/jev-1.13'`, though jev's Decisions API doesn't take a chat prompt template the same way — see §6/§8).

---

## 2. Difficulty / tier system

Six age-anchored tiers **T1–T6** replaced CEFR (A1-C2) system-wide (`migrations/replace_cefr_with_age_tiers.sql`, ADR-003). Canonical Python source: `services/categorical_maps.py`; canonical DB source: `dim_complexity_tiers` (columns include `difficulty_min`/`difficulty_max`, `description`; referenced by `migrations/task740_collapse_difficulty_to_tier_schema.sql`, `add_topic_age_tier.sql`).

| Tier | Reader profile (English, from `topic_generation/agents/tier_fit_judge.py:TIER_READERS`, ADR-003) | `TIER_NUMERIC` | `TIER_TO_IRT` | `TIER_TO_PHASE` |
|---|---|---|---|---|
| T1 | a 4-5 year old (~500 words; basic verbs/nouns; one idea per sentence) | 1.0 | -2.0 | A |
| T2 | an 8-9 year old (~2,000 words; compound sentences; literal/concrete) | 2.0 | -1.0 | A |
| T3 | a 13-14 year old (~5,000 words; colloquialisms, mild idiom, conditionals) | 3.0 | 0.0 | B |
| T4 | a 16-17 year old (~10,000 words; standard adult grammar, moderate jargon) | 3.5 | 0.5 | C |
| T5 | a university student 19-21 (15,000+ words; full breadth, complex clauses) | 4.0 | 1.0 | D |
| T6 | an educated professional 30+ (25,000+ words; high register, domain jargon, rhetoric) | 5.0 | 2.0 | D |

`services/categorical_maps.py` also carries, **per tier per language (1=zh, 2=en, 3=ja)**:
- `TIER_DISPLAY_NAMES` — short native-language labels, e.g. T1 = `幼儿（4-5岁）` / `The Toddler (Age 4-5)` / `幼児（4-5歳）`.
- `TIER_CONSTRAINTS` — a full paragraph per (tier, language) of **native-language** prose describing vocabulary/grammar constraints, injected directly into generation prompts (e.g. T1 zh: `只使用最常见的基本动词和具体名词。不使用抽象概念。每句话只表达一个意思。`). This is the single richest ready-made set of "choice descriptions" in the repo — could seed jev multiple-choice-mode `legend`/option text directly, in all three languages.
- `get_tier_constraint(tier, language_id)` / `get_tier_display(tier, language_id)` helper functions.

Difficulty→tier bridges:
- `DIFFICULTY_TO_TIER: {1:'T1',2:'T1',3:'T2',4:'T2',5:'T3',6:'T4',7:'T5',8:'T6',9:'T6'}` in `categorical_maps.py` — the **legacy** integer-difficulty reader used by dual translation / model arena / mystery generation (test-gen itself no longer resolves a tier this way since TASK-740; it uses `target_age_tier` directly via `TestGenDatabaseClient.get_tier_config(tier_id)`). Per memory (`two-difficulty-to-tier-maps`), this map and the DB `dim_complexity_tiers` ranges were reconciled 2026-08-22 (d4→T2 everywhere in both copies now); `tests/test_difficulty_to_tier_matches_db.py` pins the two in sync.
- `services/exercise_generation/difficulty.py:DifficultyCalibrator.attach_difficulty()` — `difficulty_static = 0.40×tier_numeric + 0.30×sentence_length_score(1-5) + 0.30×word_frequency_score(1-5, inverse Zipf)`; `irt_difficulty = TIER_TO_IRT[tier]`.

**`tier_fit_judge.py` is a binary judge over this exact tier system** (see §1b) — worth building the jev pilot on it first, since its inputs (a short vocabulary list + a fixed reader description) are cheap and its current cost/latency/label distribution can be measured against the live judge trivially.

---

## 3. Labelled / reference data usable as ground truth

| Data | Location | Nature | Harness |
|---|---|---|---|
| **DT grading gold set** | `tests/fixtures/dt_gold/{en,zh,ja}.json` + `README.md` | 30 items/language (10 clean, 15 single-error, 5 multi-error), **fully human-adjudicated** by the developer (2026-07-05), with exact char-offset spans (scripted, never hand-counted, via `scripts/dt_gold_seed_helper.py`), taxonomy v5 subtypes, and `expected_bands` **derived** (not hand-set) from the seeded errors by `derive_bands()` using the same rubric-v5/v6 formula the live grader uses. | `python scripts/run_dt_grading_eval.py --l2 {en|zh|ja} --out report.md [--live] [--limit N] [--framework-v2] [--rubric-file ...] [--resume ...]` — reports per-dimension **QWK**, exact-match rate, adjacent-match rate. `--live` makes real paid OpenRouter calls (required to actually grade; omit for a dry structural check). |
| **Distractor-plausibility gold set** | `data/eval/distractor_gold_frame_2026-08.json` (unlabelled frame), adjudicated file referenced as `data/eval/distractor_gold_2026-08.json`; pure statistics logic in `scripts/distractor_gold.py`; builder `scripts/build_distractor_gold_frame.py` | Stratified by (language × question type_code), **disagreement-enriched then reweighted** (`frame_weight`/`selection_prob` correct for the enrichment bias — an unweighted rate off this set would read as a false regression). Two **separate, never-collapsed** gold axes: `TOPICAL_DISTANCE ∈ {on-topic, related, unrelated}` and `CONFUSABLE ∈ {yes, borderline, no}`; a labelled overlap slice supports Cohen's kappa. | `python scripts/measure_judge_flag_rate.py --sample <frozen.json> --arms "name=version:model,..." [--gold data/eval/distractor_gold_2026-08.json] [--out results.json] [--report-only results.json]` — this is the exact harness that found the TASK-718 zh "qwen artefact" result (same content, swap only the judge model). |
| **Entailment AB data** | `data/eval/entailment_sample_150.json`, `entailment_ab_2026-08-17.json`, `entailment_ab_g37f_2026-08-17.json`, `entailment_v3_2026-08-19.json`, `entailment_v3_ja_models_2026-08-19.json` | Labels are **structural, not human-adjudicated**: the stated correct answer = positive class, its 3 distractors = negative class. Explicitly called out as a lower-bound-only AUC in the judge-eval-campaign tech spec (a distractor is a proxy for "hallucinated answer," not the real production negative class). | `scripts/measure_entailment_ab.py` — AUC (Mann-Whitney), Wilson CI, false-reject/false-accept at live thresholds, score-distribution collapse detection, pairwise agreement. This is the harness the (unbuilt) judge-eval-campaign plans to generalize. |
| **Classifier/counter curation approvals** | `data/classifier_curation/*.json`, `data/classifier_curation/approved_curation.json` | Human-reviewed accept/reject decisions over `judge_nouns()` output — direct gold for that judge. | No dedicated CLI found; would need a small ad hoc script. |
| **`llm_calls` judge-verdict history** | Supabase table `llm_calls` | Every judge above writes `judge_verdict`/`judge_confidence` via `log_judge_verdict` (task_name prefixed `judge_`), **in addition to** the raw-call row `call_llm` always writes (verdict NULL there). Query `task_name LIKE 'judge_%' AND judge_verdict IS NOT NULL` for live accept/flag/reject distributions per judge/model/language — not human-labelled, but useful as a live-traffic baseline distribution to match a jev arm against. | Ad hoc SQL via Supabase MCP or `python`+`supabase-py`. |
| **Full (unbuilt) campaign design** | `wiki/features/judge-eval-campaign.md` + `.tech.md` | **Deferred 2026-08-17, nothing built** — a complete blueprint for exactly this kind of model bake-off: 3-tier funnel (Tier 0 gate ~200 models × 6 calls → Tier 1 screen ~150 × 90 items → Tier 2 full ~20 × 1000 items against `data/eval/entailment_gold_v1.json`, a **not-yet-built** gold set with a locked 20% holdout split), pre-flight gate (JSON-mode support, empty-content rate, schema-parse rate, degenerate-response detection — catches models that silently always return the `safe_accept()` sentinel), `--budget-ceiling`/`--dry-run` guardrails, and an HTML report spec. Nothing here has been implemented; treat it as a design reference, not working code. | N/A (design doc) |

**How to query Supabase**: `DATABASE_URL` in `.env` is **local dev only, not Supabase** (memory note) — use the Supabase MCP tools or `python`'s `supabase-py` client against the live project for `llm_calls`/`prompt_templates`/`dim_complexity_tiers` reads. Local pytest needs `PYTHONPATH=.` **and** an explicit `tests/` path (`PYTHONIOENCODING=utf-8 PYTHONPATH=. python -m pytest tests/ -q` — omitting `tests/` silently collects nothing, confirmed again in the judge-eval-campaign tech spec's own Testing Strategy section).

---

## 4. Costs / latency currently recorded

- `llm_calls.cost_usd` — populated only when the provider is `openrouter` (code sends `extra_body={'usage':{'include': True}}`) and the provider actually reports `usage.cost`; **no fabricated per-token estimate** is used when it's missing (explicit design choice in `llm_service._extract_cost`). Per wiki index (2026-09-24), this column has gone 100% NULL more than once (a defect class closed 2026-08-12, recurring by 2026-09-24) — **verify it's populated before trusting any llm_calls-derived cost figure**.
- `migrations/llm_calls_cost_instrumentation.sql` added `prompt_tokens`/`completion_tokens`/`cached_tokens`/`reasoning_tokens`/`sense_id`/`call_role`/`generation_batch_id` — but the judge-eval-campaign tech spec (2026-08-17) still says `llm_calls` has **no token columns** for its purposes, i.e. that migration may postdate or be independent of what that doc assumed; check the live schema before relying on token columns for a jev comparison.
- **DT grading has NO `llm_calls` rows at all** (see §1d) — its cost must come from the DT eval harness's own token accounting (`run_dt_grading_eval.py` reports `cost=$X` per run) or from adding logging.
- Known unit economics from memory / migrations:
  - Test generation: **$0.0088/test, 2.9 min/test** (wall-clock bound, 82% vocab enrichment).
  - Sense generation batch (TASK-515): **~$0.024/sense, ~5.5 min/sense**.
  - Fat-seed gloss generation: **$0.000026/call**.
  - Judge-eval-campaign's own measured throughput (2026-08-17): **46 calls/min at 8 workers**; a full 200-model × 3-tier funnel projects to **~35,000 calls, ~$13, ~4.5h wall clock** (vs. a naive flat 200×1000 sweep at ~200,000 calls / ~35h — not executable). List price mispredicted real cost by **up to 4.8×** in that exercise (`gemini-3.7-flash` was the single most expensive arm despite mid-range list pricing) — a reason to always measure, never predict, per-call cost.
- Distractor-judge model history (zh/ja), from migrations:
  - `migrations/distractor_judge_model_zh_ja_gemini.sql`: `SET model = 'google/gemini-3.1-flash-lite'` (current/live per memory, 6.7× cheaper than the prior qwen slug and restores a middle rating band).
  - `migrations/swap_distractor_judge_zhja_to_qwen.sql`: `SET model = 'qwen/qwen3.6-flash'` (an earlier swap; reversible back to `deepseek/deepseek-v4-flash`).
  - Memory confirms: the earlier zh 32%→2% reject-rate swing on a qwen→gemini model change was a **qwen artefact**, not a real content-quality difference — a caution that any jev-vs-incumbent comparison must hold prompt content and version constant (exactly what `measure_judge_flag_rate.py --arms` is built to do).

---

## 5. How OpenRouter is called today (for an experiment script to reuse)

`services/llm_service.py` — single entry point `call_llm(...)`:
- Client pool: `get_client(provider='openrouter')` → cached `openai.OpenAI(api_key=OPENROUTER_API_KEY, base_url='https://openrouter.ai/api/v1')` (an OpenAI-SDK-compatible client hitting **`/chat/completions`**, not a raw HTTP call).
- **`OPENROUTER_API_KEY` freezes at import time** (module-level `os.getenv` at line 64) — any standalone script outside the Flask app **must call `load_dotenv(<repo>/.env)` before importing any `services.*` module**, or the key resolves empty and the OpenAI SDK silently falls back to `OPENAI_API_KEY`, producing 401s that read like a revoked key (cost the team "several tool calls to diagnose" on 2026-08-17 per the judge-eval-campaign doc).
- Every call auto-logs to `llm_calls` (DB, best-effort) and a daily CSV (`logs/llm_usage/llm_calls_YYYY-MM-DD.csv`, always-available, never silently NULL on cost). `subscribe_llm_cost_hook(callback)` gives an in-process observer independent of whether the DB write succeeds — the pattern `scripts/run_exercise_gen_eval.py`'s `InterceptingClient` harness uses to total spend even when it injects its own DB client.
- Retries: 3 attempts, exponential backoff, on connection/timeout/rate-limit errors; one deterministic temperature-0 repair turn on malformed JSON or schema-validation failure (each repair logs its own `llm_calls` row with `call_role='json_repair'|'repair'`).
- A second, simpler client wrapper exists at `services/model_arena/llm_runner.call_model_with_usage(model, prompt, system_prompt=, temperature=0.9, timeout=120)` — reuses the same client pool, returns `(content, prompt_tokens, completion_tokens, latency_seconds)`, but **does not log to `llm_calls`**. This is what DT grading uses, and would be a lighter-weight template for a standalone jev arm than reworking `call_llm`.

### Critical mismatch for a jev experiment
Both paths above call the **`/chat/completions`**-shaped OpenAI SDK method (`client.chat.completions.create(...)`). **`typesafe/jev-1.13` does not use that endpoint.** Per OpenRouter's own docs (fetched live, see §6), Jev is served through a **separate Decisions API**: `POST https://openrouter.ai/api/alpha/decisions` with body `{model, state: {...}, questions: {...}}`, returning typed `{answers: {key: {type: 'noul'|'choice'|'score', ...}}, usage: {input_tokens, output_tokens, cost}}`. **Neither `call_llm` nor `call_model_with_usage` can invoke jev as-is** — a jev experiment script needs its own thin HTTP client (reusing only `OPENROUTER_API_KEY`), and a decision on whether to bolt its results into `llm_calls`/`log_judge_verdict` for comparability with the other judges' history, or keep it in a separate `pipeline='diag'` lane (the convention the (unbuilt) judge-eval-campaign design already recommends, specifically so diagnostic spend never contaminates per-pipeline production cost reporting).

---

## 6. jev-1.13 mechanics (from OpenRouter's live docs, for experiment design)

- **Not a chat/generator model** — a "System One" decision model: typed probabilistic answers, no reasoning trace, **no output-token charge**.
- Endpoint: `POST https://openrouter.ai/api/alpha/decisions`, body `{model: "typesafe/jev-1.13", state: {...arbitrary context...}, questions: {...}}`. Multiple independent questions can be asked in **one request** (answered in parallel, no cross-visibility between answers).
- Answer types relevant here:
  - **`noul`** (yes/no probability mode) → `{type:"noul", noul: 0.0-1.0}` = P(yes). **Direct fit for `judge_topic_tier_fit`** (currently a hand-parsed `{"fits": bool}` JSON call) and for any binary keep/reject ladder judge (`l1_distractor`, `cloze` distractor judges).
  - **`choice`** (multiple-choice mode) → `{type:"choice", choice: "<option>", confidence, probabilities: {option: prob, ...}}`. Fits a closed enumeration like the DT `subtype`/`severity` enums, or `TierFitJudge.best_tier()`'s "which tier does this fit" walk collapsed into one call.
  - **`score`** (ordered-scale mode) → `{type:"score", score: float, confidence, probabilities: {band: prob}, legend: {band: "description"}}`. **This is the closest existing shape to both the Likert-1-5 judges (particle/collocation/p1_sentences/sentence_validity/translation_uniqueness/answer_entailment/distractor_plausibility) and the DT naturalness/range 1-4 bands** — `legend` can carry the exact prose already in `TIER_CONSTRAINTS`/rubric band descriptors.
- Pricing: **$0.042/M input tokens, $0.00/M output tokens**; `usage.cost` in the response is authoritative (OpenRouter's own worked example: ~$0.0000256/item, 609.9 input tokens/item, on a 550-item batch costing $0.014 total).
- Versioning: sending `typesafe/jev-1.13` resolves to the current 1.13 release (response `model` names the exact dated snapshot served, e.g. `typesafe/jev-1.13-20260917`); `~typesafe/jev-latest` tracks the newest release for those who don't need a pinned version.
- Same OpenRouter API key as everything else in this repo — no separate signup.
- Rate/spend errors: a `402` with `limit_source: "openrouter_in_flight_budget"` is transient (retry after `Retry-After`); any other `402` means real credits/key-limit exhaustion.

---

## Summary for experiment design (see final chat message for the <500-word version)

Best first pilot: **`services/topic_generation/agents/tier_fit_judge.py`** — already binary yes/no, already fails open, small/cheap prompt, and its "walk tiers ascending" shape maps cleanly onto jev's `score`/`choice` mode as a single-call replacement for up to six sequential calls. No gold set exists for it yet, but it's cheap to hand-label a few hundred (topic, tier) pairs.

Best-instrumented existing comparison harness to extend: **`scripts/measure_judge_flag_rate.py`** (holds content byte-identical across arms, already supports `--arms "name=version:model,..."` and `--gold`) — adding a jev arm requires only a thin non-chat-completions client, since the harness's arm concept is model-agnostic at the results layer.

Richest gold set: **`tests/fixtures/dt_gold/{en,zh,ja}.json`** (human-adjudicated, spans verified programmatically, expected_bands derived from the live scoring formula) — but DT grading is NOT wired into `llm_calls` for cost tracking, and its enum-index/evidence-span contract is the most complex to replicate in jev's typed-answer shape.
