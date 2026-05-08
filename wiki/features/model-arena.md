---
title: Model Arena
type: feature
status: complete
tech_page: ./model-arena.tech.md
last_updated: 2026-05-07
open_questions: []
---

# Model Arena

## Purpose

The Model Arena is an **admin/operator tool** — not a learner-facing feature — that runs head-to-head blind comparisons of OpenRouter LLMs on the two most-expensive content-generation tasks in the system: prose passage generation and comprehension question generation. Its job is to answer "which model should we route this task to?" with measured evidence (judge scores, cost per call, latency) instead of vibes or vendor reputation.

It exists because LinguaDojo's content quality is bounded by model choice on a handful of `prompt_templates` rows, and the cost difference between the cheapest and most-expensive viable model is two orders of magnitude. Operating the system without measured comparisons would either over-spend or ship lower-quality content than necessary.

## User Story

A LinguaDojo operator suspects that a cheaper model could match the production prose model's quality at a fraction of the cost — or wants to verify that a newly-released model from OpenRouter is worth switching to. They open the admin Model Arena page, pick:

- a **language** (the trial language, since prose generation is language-specific)
- 2–5 **contestant models** from the live OpenRouter catalogue
- a **judge model** (typically a strong frontier model that is *not* one of the contestants)
- which **generation types** to test: prose, questions, or both
- a **trial count** (typically 5–20 trials per type)

They start the run. The arena fetches diverse topics + difficulties from the production topic queue, asks every contestant model to generate the same prompt for each trial, and feeds the outputs **blind** (relabelled A/B/C/D/E in random order) to the judge model with strict rubrics. Once all trials complete, the operator sees aggregate scores per dimension, total cost per model, and a recommended winner. The full per-trial results (prompts, raw outputs, judge reasoning, costs) are persisted to `data/arena_runs/` for later review.

## How It Works

1. **Setup** — operator picks language, contestants (2–5), judge, generation types, and trial count.
2. **Topic spread** — the arena pulls topics from `dim_topics` and spreads difficulties across 1–9 so trials sample the full skill range, not just one tier.
3. **Trial execution** — for each trial:
   - **Prose mode:** every contestant generates a passage on the same topic, tier, and word-count target. The judge then evaluates all of them blind on a 7-dimension prose rubric.
   - **Questions mode:** the *judge model* first generates a shared prose passage. Each contestant then generates a question set on that shared passage. The judge evaluates the question sets blind on a 5-dimension questions rubric.
4. **Blind judging** — contestants are relabelled A/B/C/D/E in random order before being sent to the judge. The judge sees only the labels, never the model IDs. Each trial uses a fresh random shuffle so the judge cannot anchor on label position.
5. **Cost + latency capture** — every contestant call records prompt tokens, completion tokens, latency, and computed USD cost from the live OpenRouter pricing table.
6. **Aggregation** — once trials complete, scores are averaged per dimension per model, a winner is computed per category, and an overall winner is selected. Results are written to a JSON file under `data/arena_runs/` and held in process memory so the admin dashboard can poll them.

## Constraints & Edge Cases

- **OpenRouter only** — the arena uses the OpenRouter unified API; non-OpenRouter providers (e.g. direct Anthropic, direct OpenAI) are not contestants.
- **Judge cannot also be contestant** — recommended but not enforced. If violated, the judge's blind-relabelling becomes self-judgement on at least one trial.
- **Per-call timeout 120s** — slow models simply error out and are flagged in the trial result rather than blocking the run.
- **Failed trials don't abort the run** — exceptions are logged; the trial record carries an `error` field; aggregation skips failed trials.
- **Cooperative cancellation** — the runner accepts a `stop_check` callback; the admin UI can cancel a long run mid-trial.
- **Trial count vs cost** — frontier models cost ~$0.01–0.10 per trial. Operators should plan: a 20-trial run with 4 contestants and a frontier judge can cost $5–15.
- **No persistence between runs** — the in-process `ARENA_RESULTS` dict is wiped on Flask restart. The JSON files in `data/arena_runs/` are the durable record.
- **No statistical significance testing** — small trial counts produce noisy winners. Operators must judge whether the gap is meaningful or sample noise.

## Business Rules

- Only operators with admin role can launch arena runs (gated by the admin blueprint auth).
- The OpenRouter API key is read from `OPENROUTER_API_KEY` env var; runs fail fast if missing.
- Pricing data is cached in-process for 1 hour to avoid hitting OpenRouter's `/models` endpoint on every dropdown render.
- Arena results never feed back into the production system automatically — picking a new production model is a manual operator decision after reviewing the run.
- Decisions resulting from arena runs that change a `prompt_templates.model` value should be recorded as an ADR or log entry (e.g. ADR-005-style) so the routing change has a paper trail.

## Open Questions

- Whether to add statistical significance estimation (paired t-test on per-trial scores) so small-sample noise is flagged.
- Whether to tie arena outcomes to automatic `prompt_templates.model` updates (currently manual; automation would reduce cycle time but remove the human checkpoint).
- Whether to add a third generation type for the vocab pipeline tasks (P1/P2/P3) — currently only prose + questions are tested.

## Related Pages

- [[features/model-arena.tech]] — Technical specification
- [[features/comprehension-tests]] — The downstream consumer of the prose + questions models
- [[features/exercise-generation-prompts]] — The prompt-template registry whose `model` column the arena informs
- [[features/conversations]] — Adjacent generation pipeline that could be added as a third arena type
