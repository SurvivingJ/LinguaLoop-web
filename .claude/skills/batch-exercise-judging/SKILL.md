---
name: batch-exercise-judging
description: Judge hand-authored vocabulary-ladder assets from a staged CSV authoring run — apply the live judge prompts to each item, rewrite what fails, and record {judged, verdict, changed} per item. Runs stage 2 (P1 core sentences), stage 6 (exercise items) or stage 8 (the exercise renderer's own judge requests, answered in their raw JSON so rendering needs no API) of scripts/exercise_stage_runner.py. Must run in a fresh context that has not seen the authoring. Use when asked to judge an exercise authoring run or when batch-exercise-authoring hands off a judge stage.
---

# Batch Exercise Judging

You are the judge for a run someone else authored. **You receive the run
directory and a stage number, and nothing else.** If this context contains the
authoring transcript — you wrote the items, or you can see why they were
written — stop and say so. A judge that can see the generation reasoning is
already committed to it, and its pass counts as not run (spec §3.2,
`wiki/features/csv-exercise-authoring.tech.md`).

The project has direct evidence that judging is not a formality: swapping only
the judge model moved the zh distractor reject rate 32% → 2%. You are the
judge model here. Be the strict one.

## What you read

Only these, in `RUN/stage<K>/round_NN/` (the highest-numbered round):

- `call_NNN.prompt.md` — a batch contract, then `### item_1 … item_k`. Each
  item holds:
  - **the judge prompt(s)**, captured from the real judge functions and the
    real exercise renderer with the LLM call intercepted, so each is the exact
    text the live judge model would get: `ladder_p1_sentence_judge` at stage 2;
    at stage 6 whichever of `ladder_l1_distractor_judge`,
    `ladder_collocation_judge`, `ladder_sentence_validity_judge`,
    `ladder_relation_judge`, `ladder_word_family_judge` and
    `ladder_particle_judge` the renderer actually fired for that sense
  - **the artifact** — the authored answer in its prompt's numeric contract
  - **the return contract**

Do not open `senses.csv`, the stage outputs (`0K_*.json`), `02b_plan.json`, the
`stage1/3/4/5` prompt files, or any conversation. The item is all you need.

## What you write

`call_NNN.response.json` beside each prompt file:

```json
{"item_1": {
   "judged": true,
   "verdict": "rewrite",
   "changed": true,
   "ratings": {"ladder_p1_sentence_judge": {"1": {"rating": 5, "reason": "…"},
                                            "4": {"rating": 2, "reason": "…"}}},
   "answer": { …the artifact, same keys and shape, sentence 4 rewritten… },
   "notes": "rewrote sentence 4: target used in its other sense"},
 "item_2": {"judged": true, "verdict": "accept", "changed": false,
            "ratings": {…}, "answer": { …the artifact, byte-for-byte… },
            "notes": "all sentences on-sense and on-register"}}
```

1. Apply **each judge prompt as written**: its criteria, its scale and its
   output JSON go into `ratings`. Do not apply a stricter or looser private
   standard. Where a prompt enumerates cases, remember that a closed list in a
   judge prompt is an allow-list: something not on it can still be wrong.
2. Anything rated **2 or below** gets rewritten in `answer` so that it would
   now pass. Rated 3 is kept and named in `notes`.
3. `verdict`: `accept` (nothing rewritten, `changed: false`), `rewrite`
   (something rewritten, `changed: true`), `reject` (unsalvageable: the sense
   is wrong, or fixing it means rewriting most of it. The sense is dropped).
4. `changed` is **checked against the actual diff**. Echo the artifact exactly
   when you accept; the runner fails an item whose flag and diff disagree.

## Rewriting without breaking the uploader

A rewrite must still pass the fail-closed validator. Keep the numeric keys,
list lengths, option counts, sentence count and order.

- **Stage 2 (P1 core).** The target word must appear verbatim in the rewritten
  sentence. Rewriting a mined corpus sentence makes it `generated`, so only do
  it when the rating really is 2 or below. POS stays in the item's `pos_set`
  (UniDic for ja).
- **Stage 6 (items).** Exactly 4 options with exactly one correct (L1 may have
  4–8), a non-empty explanation per option, L6 keeps 3 wrong sentences, L7's
  incorrect and corrected sentences differ. Replace a bad distractor. Do not
  delete it, and do not add or remove levels or typed types.

## A clean batch is suspicious, not a success

If you find nothing to change in the whole call, read it again. After collect,
a stage where **every** item is `changed: false` is treated as a rubber stamp
and fails the run. The fix is a real second reading. Do not manufacture an
edit to get past the gate: an invented change is worse than the stamp.

## Stage 8 — the renderer's judges (a different contract)

Stage 8 exists so building the exercise rows makes no API call. The runner ran
the real exercise renderer over the stored assets and recorded every request
its judges would have sent to a hosted model. Each item in
`stage8/round_NN/call_NNN.prompt.md` is **one such request, verbatim**. You
are that hosted model.

- Return, per item, **only the JSON the judge prompt asks for**: its own keys,
  its own scale. No `judged`/`verdict`/`changed` wrapper, and no rewriting.
  The renderer reads your answer exactly as it would read the model's, and
  drops what you reject.
- Judge the candidates as given, strictly and by the prompt's own criteria.
  You are not fixing anything here, only deciding what survives.
- Every item gets an answer. An unanswered request blocks that sense from
  being rendered at all.

## Hand back

Once every `call_NNN.response.json` exists, report back in a few lines: items
judged, verdict counts, what kind of fault you rewrote most. Do not run
`collect` or later stages. The authoring side does that.
