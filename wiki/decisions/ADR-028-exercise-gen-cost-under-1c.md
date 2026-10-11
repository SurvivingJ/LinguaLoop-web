---
title: "ADR-028: Exercise generation cost target <$0.01/sense via call collapse, qwen for zh/ja generation"
status: accepted
date: 2026-09-24
---

# ADR-028: Exercise generation cost target <$0.01/sense via call collapse, qwen for zh/ja generation

## Context

A 2026-09-24 four-agent analysis of the vocabulary-ladder generation pipeline found the following:

**Call volume.** Ladder generation (`services/vocabulary_ladder/asset_pipeline.py`,
`VocabAssetPipeline._generate_for_sense_impl`) makes ~26 LLM calls/sense in en, ~14-16 in
zh/ja (L5/L8 disabled there), and 55-65+ in worst-case retry paths. Drivers:

- Variant A/B doubling on ~13 of 18 call sites — the same generator is invoked twice per
  sense for no structural reason.
- Stacked retries: `llm_service.py:519-535` runs a JSON-repair turn *under* each generator's
  own retry loop, so a single bad completion can cost 2-3 calls before the generator gives up.
- The P3 text-mode salvage call (`prompt3_transforms.py:205-247`) has no schema gate and fires
  speculatively.
- Regen re-runs the *entire* `build_rows()` with all 7 render judges (`queue_drain.py:279-293`)
  even when only one level needs to change.
- Each generator re-sends the same word context from scratch — no shared prefix, no prompt
  caching.
- No provider routing, no reasoning-effort control, no Batch API, no `json_schema` structured
  outputs anywhere in the pipeline.

**Cost is unmeasured.** `llm_calls` has 138 rows total (all from one 48-minute window on
2026-09-21); `cost_usd` is 100% NULL; there are no token columns; `artifact_id` is always NULL.
OpenRouter's `usage.cost` is requested (`llm_service.py` ~line 660) but never persisted. The
Aug 11-23 OpenRouter batch (~61 senses) spent an unlogged amount; generation since Sep 6 has
run via Claude Code subagents (`claude-code:batch-exercise-generation`, 604 valid assets across
108 senses), which is not billed through `llm_calls` at all. Any budget ceiling that reads
`cost_usd` is therefore very likely inert again — the same defect class closed in the
2026-08-12 exercise-gen-v2 batch recurred. The last real measurement is TASK-515's
~$0.024/sense, 5.5 min/sense, and it is stale.

**Current model assignment.** zh `prompt2`/`prompt3` run on `anthropic/claude-sonnet-5`
(69% invalid on `prompt3_transforms`, 9/13, by `word_assets.is_valid`); zh `prompt1_core` runs
on `gemini-3.5-flash-lite`; en/ja run on `qwen/qwen3.7-plus`.

**Only measured sub-cent path.** The fat-seed subagent path on `gemini-3.5-flash-lite` measures
~$0.004/sense, but only at n=6 and not at real scale; a blind comparison against the staged
chain found 4 major defects vs 0, all compound-word anchoring — the exact failure class the P1
sentence judge exists to catch.

**Prices (OpenRouter, 2026-09-24, $/M tokens, in/out):** `gemini-3.5-flash-lite` 0.30/2.50
(cached read 0.03); `gemini-3.1-flash-lite` 0.25/1.50; `qwen3.7-plus` 0.32/1.28;
`qwen3.6-flash` 0.1875/1.125; `gpt-5-nano` 0.05/0.40; `deepseek-v4-flash` dated snapshots
~0.03/0.08. OpenRouter's Batch API runs ~50% off list price on a 24h SLA.

> **Correction (2026-09-26), per the TASK-808 baseline run's live `llm_calls` rows
> (see [[evaluations/exercise-gen-baseline-2026-09]]):** the "Current model assignment"
> paragraph above is stale. **zh generation is already 100% on `qwen/qwen3.7-plus`**
> (`prompt1_core`, `prompt2`, `prompt3`, and every `ladder_*_generation` row) — this
> matches TASK-809's 2026-09-26 verification finding that an untracked flip on
> 2026-08-17 already moved zh off gemini/claude-sonnet-5, ahead of and independent of
> this ADR. It is **en**, not zh, that is still split across providers: en
> `vocab_prompt2_exercises` and `vocab_prompt3_transforms` (plus `ladder_syn_ant_generation`,
> `ladder_word_family_generation`, and `ladder_l4_morphology_generation`) run on
> `anthropic/claude-sonnet-5`; en `vocab_prompt1_core` and all en judges run on
> `google/gemini-3.5-flash-lite`. This is permitted under Decision §2 (en generation may use
> any model) but it is the reason en's baseline cost/sense ($0.10-0.11) is an order of
> magnitude above zh/ja's, not a violation needing correction. The ja baseline run in the same
> session confirms ja generation is fully on `qwen/qwen3.7-plus` as this ADR intended.

## Decision

1. **Target:** every exercise generated for one sense costs < $0.01, measured from `llm_calls`,
   at quality non-inferior to a frozen reference set.

2. **Model-family rule (operator decision, 2026-09-24, optimizing for quality, not just cost):**
   zh and ja **generation** uses the qwen family only. en generation may use any model. Model
   choice *within* a family is decided by bake-off against the reference set, not by ADR fiat.
   Consequence: zh `prompt1_core` (currently gemini) and zh `prompt2`/`prompt3` (currently
   claude-sonnet-5) must move to a qwen model.

3. **Measure before optimising.** A Phase 0 (instrumentation, guardrail verification, reference
   set, baseline run) gates every later phase. No model swap or call-collapse change ships
   without a baseline to compare against — this is the same lesson as the 2026-08-12 silently-
   inert-guardrail incident, applied prospectively.

4. **Primary lever is call collapse, to roughly 4-5 calls/sense:**
   P1 core → P1 sentence judge (kept as its own call — it is the thing that catches
   compound-word anchoring, the fat-seed path's defect class) → one bundle generation call
   (P2+P3+L4+typed, both variants together) → one bundle judge call → at most one targeted
   repair call. Layered on top, in priority order: prompt caching (stable prefix first), capped
   retries (≤2 real calls per step, not per generator × per repair), level-scoped regen instead
   of full `build_rows()`, `max_tokens` caps, provider price routing, reasoning disabled, and
   OpenRouter Batch API for backfill/bulk runs.

## Consequences

- Fewer calls also cuts wall clock, which has historically been the binding constraint (TASK-515:
  5.5 min/sense; test-gen: 82% of wall clock in one non-dominant-cost stage) — collapsing calls
  attacks both axes at once.
- Larger bundle prompts (P2+P3+L4+typed in one call, one judge call over everything) risk
  quality loss on long outputs and long judge contexts. This must be validated against the
  reference set before it ships, not assumed safe by analogy to the per-call version.
- Batch API adds up to 24h of latency per stage round — acceptable for backfill, not for
  interactive/on-demand generation.
- Moving zh off claude-sonnet-5 and gemini onto qwen is a quality bet that must clear the
  bake-off; if no qwen model matches current output quality, this ADR's model-family rule, not
  the cost target, is what has to be revisited.

**2026-10-03 note:** the bundle-call risk flagged two lines above was realized — Phase 2's blind
pairwise review failed non-inferiority vs. Phase 1 in all three languages (ja major-defect 25.7%
vs. 8.6%, en 13.2% vs. 2.9%, zh 24.2% vs. 19.4%; see
[[evaluations/exercise-gen-phase2-2026-10]] §8). But Phase 2 also landed the reasoning-disable fix
(qwen reasoning genuinely off, not just hidden) at the same time as bundle mode, so this result
cannot yet be pinned on bundling specifically — it could equally be the reasoning-off change. A
new flag, `LADDER_QWEN_REASONING` (`services/llm_service.py`), lets a follow-up eval hold qwen's
reasoning state fixed while bundle mode varies independently; see TASK-856 in
[[tasklist/exercise-gen-cost.tasks]], blocked on OpenRouter credit. TASK-814/815/816 (the bundle
rollout tasks) are blocked pending that attribution.

**Constraints that stand, unchanged by this decision:**
- L1 is listening-only: pitch-accent-only distractor pairs are invalid (TTS renders one form
  only), the render gate is all-or-nothing, and at least 3 distractors must survive it.
- The ja mora-trie generation path for L1 stays as-is.
- Judges skip items at difficulty ≤2, so any quality comparison here is implicitly a d≥3
  comparison — a reference set skewed toward d≥3 is representative, not a bias to correct for.
- Verify every guardrail actually fires before trusting it (2026-08-12 precedent: NULL
  `cost_usd`, a nonexistent RPC signature, a CHECK constraint rejecting all typed-LLM assets,
  and a per-type audio-field mismatch were all silently inert for months).
- `generation_queue` has been jammed since 2026-08-21 with no lease expiry; do not assume it
  drains on its own during this work.
- Qwen3.x + `response_format: json_object` 400s if the prompt text does not literally contain
  the word "JSON" — a latent landmine that becomes live risk the moment zh generation moves onto
  qwen.
- Prompt migrations need `DO UPDATE` / an explicit version bump, not `ON CONFLICT DO NOTHING`
  (a bare insert silently no-ops on a corrected re-run).
- `llm_calls.task_name` is written under a `judge_` prefix for judges, not under their
  `prompt_templates` key — querying the wrong namespace shows zero rows for a healthy judge.

## Open Questions

- **(a) Does the qwen-only rule also apply to zh/ja judges, not just generation?** Current
  evidence points the other way: qwen has repeatedly been the *outlier* judge model —
  [[evaluations/distractor-judge-language-divergence-2026-08-16]] found the zh distractor
  judge's reject rate went 32% → 2% when moved off qwen onto gemini, and
  [[evaluations/entailment-judge-model-ab-2026-08-17]] found the ja entailment judge's
  false-accept rate went 18% → 2% when moved off qwen. Judges stay on their current models
  pending an explicit operator decision — this ADR's model-family rule is scoped to
  **generation** only.
- **(b) Does OpenRouter's implicit prompt caching, and its Batch API, actually cover the qwen
  models?** Unverified as of this writing; the cost model in Decision §4 assumes yes.
- **(c) How should Claude-Code-subagent generation cost be attributed?** It is currently
  subscription-billed and logged in `llm_calls` as $0, which understates true cost for any
  path-vs-path comparison that includes the fat-seed/subagent route.

## Outcome 2026-10-08

**Target not met.** <$0.01/sense is not reachable at non-inferior quality with qwen3.7-plus. Reasoning off
(~$0.009-0.013/sense) hits the cost target but fails blind quality in all languages (major-defect: ja 22.2% vs
19.8%, zh 31.6% vs 7.0%, en 15.5% vs 7.1%); bundle mode also failed (confounded with reasoning-off, not
re-tested). Bounded reasoning passes: ja budget 1024 ($0.0343 vs $0.0686), en budget 1024 ($0.0215 vs $0.0289),
zh budget 2048 ($0.0390 vs $0.0493; 1024 failed for zh). Best validated cost is ~45-50% below Phase 1 and
~65-80% below baseline. Attribution (TASK-856): reasoning-off is the cause of the regression.

**Recommended (pending user approval, TASK-857):** `LADDER_QWEN_REASONING=budget`,
`LADDER_QWEN_REASONING_BUDGET_JA=1024`, `_EN=1024`, `_ZH=2048`, bundle off, and en P2/P3 off claude-sonnet-5 via
`migrations/exercise_gen_en_p2_p3_off_sonnet.sql`. Production defaults are unchanged. Caveats: coverage gate
failed in every arm (likely reference variance, TASK-860); judge noise is large; arm F (en on gemini) void,
needs re-run (TASK-858). Details: [[evaluations/exercise-gen-phase2-2026-10]] section 12.

## Alternatives Considered

- **Model swap alone, no call collapse.** Rejected as insufficient: output tokens × ~26 calls
  dominate the per-sense cost; a cheaper model on the same call count does not reach <$0.01.
- **Fat-seed subagent path as the sole generation method.** Rejected for now: unmeasured at real
  scale (n=6), and the one comparison run found a defect class (compound-word anchoring) that
  the staged chain's separate P1 sentence judge catches and the fat-seed path does not.
- **Provider batch APIs directly (bypassing OpenRouter).** Rejected: OpenRouter's own Batch API
  now matches provider-direct batch pricing to within ~0-5%, so the extra integration is not
  worth it.
- **Dropping judges to cut calls.** Rejected selectively: the entailment judge is validated
  (AUC 0.957-0.99 across the 2026-08-19 rollout) and stays. The distractor judge is *not*
  validated (gold labels are still pending per TASK-726) — it is a candidate for the bundle-judge
  collapse in Decision §4, not for removal, since removing an unvalidated judge is not the same
  claim as removing a validated one.

## Update 2026-10-09: production flipped (TASK-857)

User approved the recommended config. Code defaults in `services/llm_service.py` now are `LADDER_QWEN_REASONING=budget` with per-language budgets ja 1024 / en 1024 / zh 2048 (env `LADDER_QWEN_REASONING_BUDGET_<LANG>` > `LADDER_QWEN_REASONING_BUDGET` > per-language default > 1024). Bundle mode stays off. Calls without a `language_code` (legacy `services/exercise_generation/generators/*`) fall back to 1024. Rollback: set `LADDER_QWEN_REASONING=on` (pre-flip unbounded reasoning). The en P2/P3 sonnet migration is separate. A post-flip `llm_calls` sample is still owed to close the TASK-857 cost criterion.
