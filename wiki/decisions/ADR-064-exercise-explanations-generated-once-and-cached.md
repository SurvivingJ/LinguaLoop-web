---
title: "ADR-064: Per-option exercise explanations are generated once per item and learner language, and cached"
status: proposed
date: 2026-11-26
---

# ADR-064: Per-option exercise explanations are generated once per item and learner language, and cached

## Context

The owner, studying Japanese with English as their native language, reported on 2026-11-26 that
"spot the error" questions (`spot_incorrect_sentence`) need an explanation for **each option**,
saying why it is right or wrong, **in the learner's native language**.

What the corpus holds for such an item is four target-language sentences, which one is wrong, and
at most a one-line note on the wrong one written in the target language
(`助詞：他動詞「使う」の対象は「を」で示す。「が」は誤り。`). Correct sentences carry nothing. About
11,700 Japanese items (and the Chinese ones) are stored this way in immutable content files
([[decisions/ADR-049-exercise-content-in-storage]]).

Asked next "what about … pick the correct sentence" (`semantic_discrimination`, ~11,000 ja items):
a 200-item ja sample had English notes on every wrong sentence, but **113/200 had none on the
correct sentence**; a zh sample had **47/150 with only one joined note in Chinese**. No item
shows what the sentences mean. Regenerating the corpus is a large offline
authoring run and would still leave every future native language unserved.

## Decision

Applies to `spot_incorrect_sentence` and `semantic_discrimination` (same shape: sentences, each
right or wrong).

0. **Use the item's own notes when they already explain every sentence in the learner's
   language** (decidable for English learners: every sentence has a Latin-script note). No model
   call; they are attached as they are.
1. **Otherwise generate on first serve, once per (exercise, learner language), and cache.** A model is
   given the sentences, which one is wrong (decided by the item, never re-judged) and the stored
   notes as hints (pick-the-sentence: "keep its point"), and returns for every sentence its meaning, why it is right or wrong and the
   correction for the wrong one, all in the learner's language. The answer is validated (one entry
   per sentence; non-empty; English prose checked to be English) and stored in the new table
   `exercise_explanations` keyed `(exercise_id, nl_language_id)` with the item's
   `content_version`, so a regenerated item is explained afresh.
2. **Warm ahead, ask late.** The session request attaches cached explanations to the items it
   serves and starts generation in the background for up to
   `EXERCISE_EXPLANATION_WARM_PER_REQUEST` (8) items that have none. The renderer asks
   `GET /api/practice/explanations/<id>` only for an item served without them, at display time,
   and shows the result once the learner has answered. A generation already in flight is
   awaited, not repeated.
3. **Model**: `deepseek/deepseek-v4.1-flash`, fallback `google/gemini-3.5-flash`, via OpenRouter,
   both settable by env (`EXERCISE_EXPLANATION_MODEL`, `_FALLBACK_MODEL`). Chosen on live ja items
   on 2026-11-26: ~4 s and ~10 s, both accurate; `qwen/qwen3.7-plus` (the ladder authoring model)
   was as accurate but took 41 s, too slow for a learner waiting.
4. The table is service-role only (RLS on, no policy). Until the owner applies
   `migrations/exercise_explanations.sql`, explanations are generated and kept in process memory
   only.

## Consequences

- Every spot-the-error item explains every option in the learner's language, and a new native
  language needs no regeneration.
- A first viewer waits on one model call (usually hidden by the warm-up and by the time spent
  reading four sentences); every later viewer reads a row.
- Explanations are model-written and only structurally validated: a wrong explanation of a
  correct key is possible. The key itself cannot change. Spot checks of the first rows are owed
  (TASK-1236 follow-up).
- Cost is one small call per item and language actually served (~$0.0005); a per-user rate
  limit (30/min, 600/day) bounds a script hitting the endpoint.
- The same mechanism can carry the word-option types whose single note is often in the target
  language (ja sample 2026-11-26: fill-the-blank 40/80, particle choice 53/80, word form 44/80,
  word relations 47/80 in Japanese): TASK-1242.

## Alternatives Considered

- **Regenerate the corpus with per-option nl explanations** (new prompt + judge, offline run):
  the right long-term shape for new items, but hours of authoring for ~24k items, a migration of
  content versions, and still one language only. Not chosen for the fix; the cache serves either.
- **Machine-translate the stored note**: explains only the wrong sentence, and the note is often
  terse; the owner asked for every option.
- **Generate on every view without a cache**: repeated cost and latency for every learner.

## Amendment 2026-11-27: written ahead into Storage files, on the owner's Anthropic key

Owner: "pre write all explanations" (after the storage estimate,
[[evaluations/explanation-storage-2026-11-27]]), then "run agent swarm to write the storage file
version and run the Japanese batch"; billing: "Use my Anthropic API key"; model: Claude Sonnet 5.5.

- **Where:** pre-written explanations are immutable per-sense files in the Storage bucket
  `exercise-content` (`explanations/{lang}/{sense}.{nl}.p{prompt_version}.json`,
  `services/explanation_files.py`), not the table: the database is 473 MB of the Free plan's
  500 MB, and Japanese alone would be ~35 MB in the table (~27 MB as files).
- **Serving order:** process memory → the item's own complete English notes → Storage file →
  table → model. The file read runs beside content hydration with the same 3 s budget; a
  background job re-reads the file before paying for a model. The table and live generation
  stay for items with no file (new items, held-back senses).
- **Writing:** `scripts/prewrite_explanations_anthropic_batch.py`, Message Batches API (50% of
  standard price) on the owner's key (`CLAUDE_API`, `services/explanations_anthropic.py`, the
  live prompt and validation). The OpenRouter key had $0.22 of its $11.25 limit left.
- **Model:** measured on 20 live ja items at effort medium, all answers valid: Opus 5.5
  $0.0174/item, Sonnet 5.5 $0.0061, Haiku 5.5 $0.0006 (standard price); quality looked
  equivalent on the 10 items all three wrote. Owner chose Sonnet 5.5 (~$52 batched for 17,256
  items).
- **Immutability rules** (independent review): a sense's file is written only when every item of
  it has a usable answer (after one retry batch) at its current content version; otherwise the
  sense is held back for a later run. Reviewed corrected sentences are read in URL-sized chunks.
  Batch creation is never retried blindly (no idempotency key); an unconfirmed create is matched
  to the server's batch list on resume.
