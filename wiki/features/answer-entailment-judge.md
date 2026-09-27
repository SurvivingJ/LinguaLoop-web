---
title: Answer-Entailment Judge
type: feature
status: complete
tech_page: answer-entailment-judge.tech.md
last_updated: 2026-09-27
open_questions:
  - "OPEN: does jev hold up against human-adjudicated labels, not just structural ones?"
  - "OPEN: does a synthesised jev reject reason make regeneration worse than the LLM's explanation?"
---

# Answer-Entailment Judge

## Purpose
When LinguaLoop generates a comprehension question, an AI writes the passage-based question
and marks one choice as correct. Sometimes it invents an answer the passage never supports.
This judge checks each question's "correct" answer against the passage and stops those
questions reaching learners.

## User Story
A learner reading a passage and answering a question needs the marked answer to actually be
right. A question whose answer key is wrong teaches the wrong thing and erodes trust.

## How It Works
1. After a question is generated, the judge is given the passage, the question and the
   proposed correct answer.
2. It returns one of three verdicts: **accept** (the passage supports it), **flag** (unclear —
   keep the question but queue it for a human to look at), or **reject** (not supported —
   throw the question away and generate a replacement).
3. Two interchangeable engines can make the call. The original asks a chat model to rate
   support on a 1-5 scale. The newer one asks OpenRouter's jev decision model a single
   yes/no question and turns its probability into the same three verdicts. A setting picks
   the engine; **since 2026-09-27 the default is the newer one** (the original is the automatic
   fallback and the rollback). A third setting runs both and records
   both answers, but only the original's answer is used.
4. If the newer engine can't answer, the original runs instead.

## Constraints & Edge Cases
- The newer engine gives no explanation. On a reject, the replacement question is generated
  with a short generated note (a sentence plus the probability) rather than a reasoned one.
- A bulk generation run stops loudly if neither engine can run — it never ships unjudged
  questions. A learner waiting on a live session is never blocked by a judge outage.
- Questions whose correct answer is a definition of a word "in context" are the hardest
  for both engines; those land in the flag band more often, especially in Japanese.

## Business Rules
- Verdicts are always accept / flag / reject regardless of engine.
- A probability is never stored where a 1-5 rating belongs.
- The judge prompts are written in the passage's own language.

## Open Questions
- **OPEN** — Whether jev matches human judgement, not just the automatic "answer vs.
  distractor" labels used so far.
- **OPEN** — Whether the missing explanation makes regenerated questions worse.

## Related Pages
- [[features/answer-entailment-judge.tech]]
- [[decisions/ADR-030-jev-entailment-judge-backend]]
- [[evaluations/jev-entailment-calibration-2026-09-26]]
- [[evaluations/jev-judge-feasibility-2026-09-26]]
- [[evaluations/entailment-likert-v3-rollout-2026-08-19]]
- [[tasklist/jev-entailment-judge.tasks]]
