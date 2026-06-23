---
title: Translation Grading Cascade — Technical Specification
type: algorithm-tech
status: planned
prose_page: ./translation-grading-cascade.md
last_updated: 2026-06-23
dependencies:
  - "service: services.dictation.grader (Levenshtein WordDiff)"
  - "table: prompt_templates (OpenRouter slugs per language+stage)"
  - "service: services.model_arena.pricing (OpenRouter /v1/models pricing fetcher) — pattern reused"
  - "service: services.model_arena.llm_runner.call_model_with_usage — OpenRouter call + token usage"
  - "service: services.llm_output_cleaner.clean_json_response — strips fences before json.loads"
  - "table: dt_rubric_version, dt_taxonomy_version — shapes now defined by services/dual_translation/grader_cascade.py + prompts.py (see Implementation contracts below)"
breaking_change_risk: low
---

# Translation Grading Cascade — Technical Specification

Objective function (from the brief): **minimize (calls × tokens × model-price)** while
protecting quality on the two high-weight dimensions (`accuracy`, `understandability`).
Because grading is **reference-based**, most of this is achievable deterministically.

> Model access is **OpenRouter** (per user note), not the brief's Anthropic-tier names. Use
> **flash-style models** to keep cost down, **language-dependent by L2 content**: Gemini-flash
> for English, Qwen for Chinese and Japanese. The brief's Haiku/Sonnet/Opus tiers map to *named
> router tiers* whose slugs live in `prompt_templates` (keyed by L2 language). Re-verify slugs at
> runtime (OpenRouter delists models — see memory `prompt-template-model-slug-rot`); the cascade
> fails open to the previous tier on 404.
>
> **Prompt/output business rule (same as exercise-gen):** grading prompts are **target-language
> (L2) only — no English**, and the grader **returns numerical indices** (score integers,
> subtype/severity/source enum indices, character span offsets) — **never prose**. Human-readable
> output is produced separately by templates (see "eager explanations" below).

## Tier 0 — deterministic pre-pass (free, always first)
1. **Normalize** — whitespace, punctuation, full/half-width, kana (critical for JA/ZH).
2. **Diff / align** — reuse `services.dictation.grader` Levenshtein → opcode array
   (equal/replace/insert/delete) with character spans.
3. **Exact / trivially-close → full marks, zero errors, no model call.** Awards `scores`=all-4,
   empty `errors[]`, `grader_trace.tier='tier0'`, `tokens=0`.
4. **Embedding-similarity gate** — cheap semantic-closeness estimate to route: high similarity +
   small diff → cheap path; large divergence → escalate. (Embedding provider OPEN.)
5. **Result cache** — key `hash(passage_id, normalized_reproduction)`; identical/near resubmits
   return the cached grade for free.

## Tier 1 — cheap OpenRouter slug
- Only for reproductions that differ from the gold.
- Detect + tag **`accuracy`** errors (grammatical/lexical) where the reference makes the call
  near-deterministic; first pass at `range`.
- Emits the compact §2.2 JSON only (no prose).

## Tier 2 — mid OpenRouter slug
- The **nuanced dimensions**: `understandability`, `fidelity`/register, `naturalness`.
- Called **only** for dimensions unresolved at Tier 0/1, or when Tier 1 `confidence` is low or
  the diff is large.

## Tier 3 — expensive slug (default OFF)
- Reserved for rare low-confidence/disputed cases or one-time calibration-content generation.
- Never in the per-submission hot path.

## The biggest lever: prompt caching
The rubric, band descriptors (per age tier), few-shot calibration examples, and per-language
instruction block are **large, static, identical across submissions** → cached prefix; only the
learner's reference + reproduction go in the uncached suffix.
- Keep the prefix **byte-stable**; version it via `dt_rubric_version` / `dt_taxonomy_version`.
- A prefix change is the *only* thing allowed to bust the cache, and it must bump the version.
- Pre-warm per active language. (OpenRouter prompt-caching support varies by model — confirm the
  chosen slug supports it; if not, the lever degrades to "keep the prompt small".)

## Minimize output tokens + eager explanations (repo override)
- Grading output is **numerical indices only** (scores, subtype/severity/source enum indices,
  span offsets) — no prose, no English, L2-only prompt. This is the cheapest possible grader output
  and satisfies the business rule.
- **Explanations are eager but template-rendered, not model prose** (override of brief §4.4 —
  [[decisions/ADR-015-eager-error-explanations]]): each error's `explanation` is rendered from a
  **versioned per-subtype × per-L1 template** keyed by the grader's numerical subtype index, with
  `corrected_form`/`learner_form` slotted in. "Which rule + why" for every error, in the learner's
  L1, at ~zero marginal model cost. Templates live with the taxonomy
  ([[business-rules/translation-error-taxonomy]] / `dt_taxonomy_version`).

## Batch the async work (OpenRouter has no 50% batch tier — plan accordingly)
The brief's Anthropic Batch API discount does not exist on OpenRouter. So "batch" here means
**off-hot-path scheduling**, not a discount. Run async (nightly): L1-reference generation for new
passages, error clustering (embeddings, not LLM), card generation, bulk re-scores after a rubric
change. The cost win comes from prompt caching + Tier 0, not a batch discount.

## Budget guardrails
- Per-user/day token budget is a **required tunable config value** in `Config` (not hardcoded —
  operators must be able to adjust it). On breach: **degrade to Tier 0 + Tier 1 only**; never
  hard-fail the session.
- Log `grader_trace` (tier, cache hit/miss, tokens, slugs) on every submission; expose a cost
  dashboard. A prompt edit that busts the cache must be observable as a cost regression.
- **Preserve the pedagogy/cost synergy:** the high-weight dimensions are the cheapest (Tier 0 /
  Tier 1 / reference-anchored); the de-emphasized `naturalness` is the expensive fuzzy one. Don't
  "fix" quality by spending more on nativeness grading.

## Implementation contracts (TASK-606, `services/dual_translation/grader_cascade.py` + `prompts.py`)

TASK-606 had to define several JSON shapes the wiki described only in prose. These are now the
canonical contracts — TASK-604 (rubric seed) and TASK-616 (taxonomy localisation) must conform to
them, not the other way around.

**`dt_rubric_version.config`** (consumed by `grader_cascade.compute_overall_band` + `prompts.build_system_prompt`):
```json
{
  "weights": {
    "default": {"accuracy": 0.3, "understandability": 0.3, "fidelity": 0.15, "range": 0.15, "naturalness": 0.1},
    "by_language": {"ja": {"fidelity": 0.25}, "zh": {"accuracy": 0.35}}
  },
  "band_descriptors": {
    "<age_tier 1-6>": {"<dimension>": {"<l2_code>": {"1": "band-1 text", "2": "...", "3": "...", "4": "..."}}}
  }
}
```
Missing `band_descriptors` entries degrade gracefully (the calibration line is omitted from the
prompt, never a crash) — only a missing **row** (`get_active_rubric` finds no active
`dt_rubric_version`) is a hard `RuntimeError`, mirroring `prompt_service.get_template_config`'s
"no silent fallback" contract.

**`dt_taxonomy_version.taxonomy`** (consumed by `_resolve_subtypes`/`_resolve_subtype_labels`/`render_explanation`):
```json
{
  "pairs": {
    "<l1_code>-<l2_code>": {"subtypes": ["particle", "keigo_register", "..."]},
    "<l2_code>": {"subtypes": ["..."]}
  },
  "subtype_glosses": {"<subtype>": {"<l2_code>": "human-readable gloss shown to the grading model, in l2_code"}},
  "templates": {"<subtype>": {"<l1_code>": "explanation template with {learner_form}/{corrected_form} placeholders"}}
}
```
`category`/`source`/`severity` are **not** in this config — they're already hardcoded as CHECK
constraints on the live `dt_error_instance` table (TASK-602), so `prompts.CATEGORY_ENUM` /
`SOURCE_ENUM` / `SEVERITY_ENUM` mirror those exact values as code constants; only `subtype` is the
open-ended, versioned axis. `pairs` falls back from the exact `<l1>-<l2>` key to an `<l2>`-only
baseline when no per-pair table exists yet (true today, pre-TASK-616) — every L1 shares one
baseline subtype list, which also maximizes the prompt-cache prefix's reuse until per-pair data
genuinely diverges it. `subtype_glosses` is new: the model must never see a bare English subtype
slug inside an L2-only ZH/JA prompt, so each subtype needs a short gloss *in the L2 being graded*
(distinct from `templates`, which is keyed by the learner's **L1** and used only for the
post-grading explanation render, never shown to the model). A missing gloss falls back to the bare
slug and logs an authoring flag — same non-blocking pattern as a missing explanation template.

**Raw per-tier model JSON** (L2-only prompt, `prompts.validate_raw_response` checks the outer
shape; `grader_cascade._decode_error` validates each error and drops malformed entries individually
rather than discarding the whole response):
```json
{
  "confidence": 0.0,
  "scores": {"<dimension>": 1},
  "errors": [{
    "span_repro": [0, 0], "span_ref": [0, 0],
    "category": 0, "source": 0, "severity": 0, "subtype": 0,
    "learner_form": "...", "corrected_form": "...",
    "confidence": 0.0, "is_mistake": false
  }]
}
```
JSON field names stay in English in every L2 (protocol tokens, like an XML tag name — not prose);
everything else in the prompt (instructions, enum glosses, subtype glosses, band descriptors) is
authored in the L2 being graded. The three instructional templates (EN/ZH/JA) in `prompts.py` are
AI-authored first drafts, not native-reviewed — functionally complete, flagged for linguistic QA
alongside TASK-616.

**Escalation thresholds actually implemented** (`grader_cascade.py` module constants):
`CONFIDENCE_ESCALATION_THRESHOLD = 0.6` and `LARGE_DIFF_RATIO = 0.3` — Tier 2 always runs once
Tier 0 hasn't resolved (`understandability`/`fidelity`/`naturalness` are Tier-2-exclusive); it
*additionally* re-grades `accuracy`/`range` (overriding Tier 1's values) only when Tier 1's
self-reported `confidence` is below the threshold or Tier 0's `mismatch_ratio` (now a field on
`tier0.Tier0Result`, reused rather than re-diffed) exceeds the ratio.

**Fail-open, precisely:** a tier with no usable slug (router exhausted to `tier0`/`slug=None`) or
a response that fails JSON parsing/shape validation contributes nothing — that tier's owned
dimensions default to `MAX_BAND` (4) and add no errors, rather than hard-failing the submission.
`grader_trace.fell_open`/`reason` record which tier(s) and why. In the worst case (every tier
unusable) every dimension defaults to 4 — the submission ends up identical to a Tier 0 full-marks
grade despite a real, non-trivial diff. This is a deliberate, generous reading of "fail-open to
Tier 0 marks on malformed grader JSON" for total-outage: never block the learner, even at the cost
of an occasionally too-generous grade during an outage.

## Related Pages
- [[features/dual-translation.tech]] — where the cascade is invoked
- [[features/dictation.tech]] — Tier 0 diff grader
- [[features/model-arena.tech]] — OpenRouter pricing fetcher + runner pattern
- [[decisions/ADR-014-reference-first-grading]], [[decisions/ADR-015-eager-error-explanations]]
