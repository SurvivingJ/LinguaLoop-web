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
([[decisions/ADR-049-exercise-content-in-storage]]). Regenerating the corpus is a large offline
authoring run and would still leave every future native language unserved.

## Decision

1. **Generate on first serve, once per (exercise, learner language), and cache.** A model is
   given the sentences, which one is wrong (decided by the item, never re-judged) and the stored
   note as a hint, and returns for every sentence its meaning, why it is right or wrong and the
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
- The same mechanism can carry other types whose notes are in the target language (cloze
  `explanation`, semantic discrimination): TASK-1242.

## Alternatives Considered

- **Regenerate the corpus with per-option nl explanations** (new prompt + judge, offline run):
  the right long-term shape for new items, but hours of authoring for ~24k items, a migration of
  content versions, and still one language only. Not chosen for the fix; the cache serves either.
- **Machine-translate the stored note**: explains only the wrong sentence, and the note is often
  terse; the owner asked for every option.
- **Generate on every view without a cache**: repeated cost and latency for every learner.
