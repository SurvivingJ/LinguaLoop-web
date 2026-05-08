---
title: Model Arena — Technical Specification
type: feature-tech
status: complete
prose_page: ./model-arena.md
last_updated: 2026-05-07
dependencies:
  - "OpenRouter API (`OPENROUTER_API_KEY` env var)"
  - "services/llm_service.get_client (shared OpenAI-compatible client pool)"
  - "services/llm_output_cleaner (clean_text, clean_json_response)"
  - "services/conversation_generation/categorical_maps (DIFFICULTY_TO_TIER)"
  - "services/supabase_factory (admin client for topic queue reads)"
  - "services/task_runner (run_in_thread, is_task_stopped — cooperative-cancel runner)"
  - "dim_topics table (topic source for trial seeding)"
  - "data/arena_runs/ filesystem directory (persisted results)"
breaking_change_risk: low
---

# Model Arena — Technical Specification

## Architecture Overview

```
Admin UI (admin_dashboard.html)
    → POST /api/run/arena  { language_id, contestant_models[],
                              judge_model, generation_types[], num_trials }
        → routes/model_arena.py:run_arena()
            → ArenaConfig built from request body
            → task_runner.run_in_thread(arena_id, ArenaService(config).run)
                → ArenaService.run()                            ┐
                    → _load_topics()  (Supabase: dim_topics)    │
                    → _spread_difficulties()                    │
                    → for each trial:                           │  Background
                        → _run_prose_trial OR                   │  thread
                          _run_questions_trial                  │  (OpenRouter
                            → _call_contestant() × N             │   calls,
                              (call_model_with_usage)            │   judge
                            → _shuffle_for_judging() (blind)     │   calls,
                            → _invoke_judge()                    │   pricing
                              (call_model_with_usage)            │   compute)
                            → parse JudgeScores                 ┘
                    → _aggregate()  (per-dim mean, winners)
                    → write data/arena_runs/{arena_id}.json
                    → ARENA_RESULTS[arena_id] = results.to_dict()

Admin UI polls:
    GET /api/run/arena/{arena_id}/status   →  in-memory ARENA_RESULTS
    GET /api/run/arena/{arena_id}/results  →  same dict + completion flag
    POST /api/run/arena/{arena_id}/stop    →  task_runner.request_stop()
    GET /api/models                        →  cached OpenRouter catalogue
```

## Module Layout

| File | Lines | Responsibility |
|---|---|---|
| `services/model_arena/__init__.py` | 1 | Package marker |
| `services/model_arena/models.py` | 77 | Dataclasses: `ArenaConfig`, `ModelOutput`, `JudgeScores`, `TrialResult`, `ArenaResults` |
| `services/model_arena/pricing.py` | 68 | OpenRouter `/v1/models` fetcher (1h cache); `compute_cost(prompt, completion, pricing)` |
| `services/model_arena/llm_runner.py` | 54 | `call_model_with_usage(model, prompt) → (content, prompt_tok, completion_tok, latency)` — wraps the shared client to capture `response.usage` |
| `services/model_arena/judge_prompts.py` | 190 | `PROSE_DIMENSIONS`, `QUESTION_DIMENSIONS`, `build_prose_judge_prompt`, `build_questions_judge_prompt` — strict rubric prompt builders with truncation and JSON-schema enforcement |
| `services/model_arena/arena_service.py` | 487 | `ArenaService` orchestrator: topic loading, difficulty spread, trial execution, blind shuffle, judge invocation, aggregation, persistence |
| `routes/model_arena.py` | (HTTP) | Flask blueprint: `/api/models`, `/api/run/arena`, `/api/run/arena/<id>/status`, `/api/run/arena/<id>/stop`, `/api/run/arena/<id>/results` |

## Dataclasses

### `ArenaConfig`

| Field | Type | Notes |
|---|---|---|
| `language_id` | int | FK to `dim_languages.id` (1=Chinese, 2=English, 3=Japanese) |
| `language_name` | str | Display name passed to judge prompts |
| `language_code` | str | ISO short code |
| `judge_model` | str | OpenRouter model ID (e.g. `'anthropic/claude-opus-4-7'`) |
| `contestant_models` | list[str] | 2–5 OpenRouter model IDs |
| `generation_types` | list[str] | Subset of `['prose', 'questions']` |
| `num_trials` | int | Total trials; spread across types in round-robin |
| `model_pricing` | dict[str, dict] | `{model_id: {prompt: $/tok, completion: $/tok}}` |

### `JudgeScores` (1–10 integer per dimension)

**Prose rubric:** `naturalness`, `vocabulary_appropriateness`, `grammar_accuracy`, `topic_adherence`, `engagement`, `length_compliance`, `difficulty_calibration`.

**Questions rubric:** `question_quality`, `distractor_quality`, `cognitive_level_match`, `answer_correctness`, `language_accuracy`.

Plus a free-form `judge_reasoning: str` (2–4 sentence justification per response).

### `TrialResult`

| Field | Type | Notes |
|---|---|---|
| `trial_num` | int | 1-indexed |
| `difficulty` | int | 1–9 |
| `tier` | str | T1–T6 derived via `DIFFICULTY_TO_TIER` |
| `topic_concept` | str | From `dim_topics` |
| `generation_type` | str | `'prose'` or `'questions'` |
| `shared_prose` | str\|None | Set only for question-mode trials (judge-generated source passage) |
| `label_to_model` | dict[str,str] | `'A' → 'anthropic/claude-...'` (the blind mapping for this trial) |
| `model_outputs` | dict[str, ModelOutput] | One per contestant — keyed by model_id |
| `judge_scores` | dict[str, JudgeScores] | Keyed by model_id (post-decoding, not by label) |
| `judge_output` | ModelOutput | The raw judge response with cost/latency |

### `ArenaResults`

Top-level run record persisted to `data/arena_runs/{arena_id}.json`. Contains:

- The `ArenaConfig` used
- All `TrialResult`s
- `started_at`, `completed_at` ISO timestamps
- `total_cost_by_model: {model_id: usd}`
- `judge_cost: float` (total across all judge invocations + judge-as-prose-author for questions trials)
- `aggregate_scores: {model_id: {dimension: mean_score}}`
- `winner_by_category: {dimension: model_id}`
- `overall_winner: str` — model_id with highest mean across all rated dimensions

## API / RPC Surface

### `GET /api/models`

- **Purpose:** Admin UI dropdown population — list all OpenRouter models with pricing.
- **Handler:** `routes/model_arena.py:list_openrouter_models`
- **Query params:** `refresh=1` to force-bypass the 1h pricing cache.
- **Returns:**
  ```json
  {
    "models": [
      { "id": "anthropic/claude-opus-4-7", "name": "Claude Opus 4.7",
        "context_length": 200000,
        "prompt_cost": "0.000015", "completion_cost": "0.000075" }
    ]
  }
  ```
- **Errors:** 500 on OpenRouter network/auth failure.
- **Auth:** Inherits from blueprint guard (admin-only).

### `POST /api/run/arena`

- **Purpose:** Launch an arena run.
- **Handler:** `routes/model_arena.py:run_arena`
- **Body:**
  ```json
  {
    "language_id": 2,
    "contestant_models": ["openai/gpt-4.1", "anthropic/claude-sonnet-4-6", "google/gemini-2.5-pro"],
    "judge_model": "anthropic/claude-opus-4-7",
    "generation_types": ["prose", "questions"],
    "num_trials": 10
  }
  ```
- **Validation:**
  - `2 ≤ len(contestant_models) ≤ 5`
  - `judge_model` non-empty
  - `language_id` non-empty
  - `generation_types` ⊆ `{'prose', 'questions'}`
- **Returns:** `{ "arena_id": "uuid-string" }` immediately; the run executes in a background thread via `task_runner.run_in_thread`.
- **Side effects:** Creates `data/arena_runs/{arena_id}.json` on completion. Holds in-memory `ARENA_RESULTS[arena_id]` for the dashboard.

### `GET /api/run/arena/<arena_id>/status` and `/results`

- **Purpose:** Polling endpoints for the admin UI to render progress and final aggregates.
- **Returns:** Current `ArenaResults` dict (partial during execution, complete after).

### `POST /api/run/arena/<arena_id>/stop`

- **Purpose:** Request cooperative cancellation — the next `stop_check()` call inside the runner returns `True` and the loop exits cleanly. In-flight LLM calls run to completion (no client-side abort).

## Trial Execution Detail

### Prose trial — `_run_prose_trial`

1. Compute word-count window from `WORD_COUNT_BY_TIER[tier]` (T1: 40–80 → T6: 260–400).
2. Build prose prompt via `_build_prose_prompt(topic, difficulty, tier, word_min, word_max)`.
3. For each contestant: `_call_contestant(model_id, prompt, temperature=0.9)` → `ModelOutput(content, tokens, cost, latency)`.
4. `_shuffle_for_judging(trial)` → returns `[(label, model_id), ...]` with labels assigned uniformly at random.
5. `build_prose_judge_prompt(...)` builds a strict-rubric prompt that:
   - Truncates each response to 2,500 chars (`_truncate`) to keep the judge prompt within context.
   - Includes the tier reference (T1–T6 difficulty descriptions verbatim).
   - Demands a JSON object with one entry per label, scoring all 7 dimensions as 1–10 integers plus reasoning.
6. `_invoke_judge` calls the judge model and parses the JSON response. Decoded scores are mapped back from labels to model_ids via `trial.label_to_model`.

### Questions trial — `_run_questions_trial`

Differs in that **the judge model first writes the shared source prose**, then contestants each generate a question set on that prose. This isolates question-generation skill from prose-generation skill.

1. Generate shared prose with the judge model (using the same prose prompt). The cost is added to `results.judge_cost` rather than to any contestant's tally.
2. For each contestant: build a questions prompt with the shared prose; call with `temperature=0.7` (lower than prose).
3. Parse each contestant's question JSON via `_parse_question_set` (lenient JSON cleanup via `clean_json_response`).
4. Build the questions judge prompt with the parsed question sets and the shared prose. Same blind-labelling logic.
5. Score on the 5-dimension questions rubric.

### Aggregation — `_aggregate`

After all trials:

1. For each model_id and each dimension that received scores: compute mean across trials, write into `aggregate_scores[model_id][dimension]`.
2. For each dimension: pick the model with the highest mean, write into `winner_by_category[dimension]`.
3. Compute `overall_winner` as the model with the highest mean across all dimensions on which it was scored.
4. Write the full `ArenaResults` dict (via `to_dict()` → `dataclasses.asdict`) to `data/arena_runs/{arena_id}.json` with pretty-print indent.

## Pricing Model

`services/model_arena/pricing.py` exposes:

- `fetch_model_list(api_key, force_refresh) -> list[dict]` — calls `https://openrouter.ai/api/v1/models`. In-process cache with `CACHE_TTL_SECONDS = 3600`.
- `get_pricing_map() -> {model_id: {prompt: $/tok, completion: $/tok}}` — the values come from OpenRouter's `pricing.prompt` and `pricing.completion` fields, parsed as floats with safe defaults of 0.0.
- `compute_cost(prompt_tokens, completion_tokens, pricing) -> float` — straightforward `p_tok * pricing['prompt'] + c_tok * pricing['completion']`.

If `pricing` is empty or the API returned 0/null pricing, costs are reported as $0.00 — operators should sanity-check costs against their OpenRouter dashboard rather than treating arena costs as authoritative.

## Persistence

- **Per-run JSON:** `data/arena_runs/{arena_id}.json` written on `_aggregate()` completion. Contains the entire `ArenaResults` including raw model outputs (not just scores), so post-hoc analysis can re-judge with a different judge model.
- **In-memory:** `ARENA_RESULTS: dict[str, dict]` survives only as long as the Flask process. On restart, only the JSON files remain; the dashboard loses live polling state for any in-flight runs.
- **No DB persistence** — arena runs are intentionally not stored in Supabase. The cost and the operator-facing nature of the results don't justify the row volume in `prompt_templates`-adjacent tables.

## Key Architectural Decisions

1. **Blind-relabelled judging via per-trial random shuffle**
   - **Rationale:** Prevents the judge from anchoring on label position or model name. The shuffle is per-trial, so even position-based bias averages out.
   - **Alternatives rejected:** Sending model names directly to the judge (vendor-name bias). Using a fixed label assignment across trials (positional bias).

2. **Judge model writes the shared prose for questions trials**
   - **Rationale:** Isolates question-generation skill from prose-generation skill. Otherwise contestants with weaker prose would also generate worse-grounded questions, conflating two dimensions.
   - **Alternatives rejected:** Each contestant writes its own prose then questions (conflated). Use a production-stored prose passage (introduces the production prose model as an unmeasured confound).

3. **OpenRouter as the unified provider**
   - **Rationale:** Allows comparing across vendors (Anthropic, OpenAI, Google, Mistral, Qwen, etc.) through one API and one cost-accounting source. The arena's job is comparison; using each vendor's native API would add code per vendor without changing the judging.
   - **Alternatives rejected:** Native APIs per vendor (more code; inconsistent usage reporting). LiteLLM (similar tradeoffs to OpenRouter; OpenRouter chosen for its catalogue UI).

4. **Cooperative-cancellation via `stop_check` callback**
   - **Rationale:** A frontier-model 20-trial run can take 10–20 minutes. The operator must be able to abort if results are obviously skewed early. A `stop_check()` polled at trial boundaries gives clean cancellation without aborting in-flight HTTP requests.
   - **Alternatives rejected:** Hard kill of the worker thread (leaves OpenRouter calls dangling, may strand cost). No cancellation (wastes operator time and money).

5. **Fixed temperatures (prose=0.9, questions=0.7)**
   - **Rationale:** Mirrors the production generation temperature for prose (creative) and questions (structured/JSON). Comparing models at *their* production temperature is what the operator cares about.
   - **Alternatives rejected:** Per-model temperature tuning (turns the arena into a hyperparam search and dilutes the model-vs-model comparison).

## Security Considerations

- Admin-only blueprint — no learner can launch a run.
- `OPENROUTER_API_KEY` read from env, never logged. The `pricing.fetch_model_list` Authorization header is constructed inline and not echoed.
- Arena runs can be expensive; the trial-count and contestant-count caps (`num_trials` is operator-supplied; contestant count clamped to 2–5) are the only cost guard. Operators should not give admin role to untrusted accounts.
- Persisted JSONs in `data/arena_runs/` contain raw model outputs which may include test prose passages. Treat the directory as the same sensitivity tier as the prompt-template registry.

## Testing Strategy

- **Unit:** `compute_cost` with edge cases (zero pricing, missing keys).
- **Unit:** `_truncate` boundary at exactly 2500 chars.
- **Unit:** `build_prose_judge_prompt` with 2/3/5 contestants — verify schema includes one entry per label.
- **Unit:** `_shuffle_for_judging` over many runs — verify uniform label distribution.
- **Integration:** mock OpenRouter responses through `call_model_with_usage` and run a 2-trial arena end-to-end; assert `aggregate_scores`, `overall_winner`, and the JSON file all exist.
- **Edge cases:** all contestants error on a trial; judge JSON malformed; trial cancelled mid-run; OpenRouter pricing API down.

## Related Pages

- [[features/model-arena]] — Prose description
- [[features/comprehension-tests.tech]] — Downstream prose-generation consumer
- [[features/exercise-generation-prompts]] — `prompt_templates.model` rows the arena informs
- [[database/rpcs.tech]] — `prompt_templates` table (the routing destination)
