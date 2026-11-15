---
title: "ADR-046: A never-taught word the practice engine picks starts the new-word drill"
status: accepted
date: 2026-11-15
---

# ADR-046: A never-taught word the practice engine picks starts the new-word drill

## Context

[[decisions/ADR-040-criterion-based-new-word-drill]] drills every word *admitted to the ladder*
through four intro sessions. But the practice engine (`get_practice_session`) also serves
BKT/FSRS candidates from `user_vocabulary_knowledge`, and those need no ladder row. A word the
learner met once in a comprehension test (status `encountered`/`unknown`, low `p_known`) was
served as an ordinary ladder exercise at any level, with no teaching first.

Observed 2026-11-15 (developer's account, Japanese): 雰囲気 and 開放, first met in a reading
test on 2026-09-08 and never taught, came up in the daily Practice block with two exercises each
(spot the incorrect sentence, semantic discrimination, definition match, typed cloze), and three of
the four were answered wrong. The developer's rule: **"if we see them, we should drill them from
the beginning."**

## Decision

When a practice payload is built (`PracticeSessionService.get_session`, every mode including tail
rounds, and the review half of `get_extra_round`), every served word that is **never taught** is
taken out of the ordinary items and starts the drill at intro session 1, today:

- **Never taught** = no `user_word_ladder` row in any state, **and** no correct exercise answer
  (`user_vocabulary_knowledge.word_test_correct = 0`), **and** `p_known < 0.5` (or no knowledge row).
  Words known from tests or placement (`p_known ≥ 0.5`, about 65 of the developer's Japanese
  words) are not pulled back to session 1.
- The ladder row is inserted with `word_state='intro'`, `intro_stage=1`, `intro_due_date=today`,
  and `intro_history=[{event:'overload', source:'practice', date, at}]`. The `overload` event
  already means "serve now, in every mode, past the new-word quota" to `bypasses_quota` and to the
  review governor SQL, so **no migration** is needed.
- At most **5** never-taught words per practice request (`UNTAUGHT_MAX_PER_SESSION`). More than
  that are removed from the request and **not** served plain; they start the drill when the engine
  picks them again.
- Words the drill cannot build (no gloss in the learner's definition language) stay as ordinary
  items. Prestudy follow-up items and DT error cards are never touched.
- Once session 1 is finished the word counts as started today in `ladder_new_word_state`, so it
  takes one of today's new-word slots in acquisition (later brand-new words wait).

## Consequences

- No word reaches the learner as a hard exercise before it has been taught.
- A Practice-mode (maintenance) session can now contain session-1 drill words. The start card
  already counts them as "new words to learn".
- A practice request that served many never-taught words gets shorter (over-cap words are held
  back) and longer (≈7 drill items per routed word). The cap bounds this.
- One extra pair of reads per practice request (`user_word_ladder`, `user_vocabulary_knowledge`
  for the served sense ids), plus one sense read when something is routed.
- Words already answered right once (e.g. 雰囲気's definition match on 2026-11-15) count as taught
  and are not routed. The bar is deliberately low: one correct answer is evidence of some teaching.

## Alternatives Considered

- **Exclude never-taught words from practice and leave them for normal new-word intake.** Rejected
  by the developer: a word the engine considers worth practising should be taught now, not hidden.
- **Route only within the new-word quota.** Rejected: in Practice mode the quota is 0, so the
  words would still be served plain or dropped.
- **A new history event (`seen`).** Rejected for now: the governor SQL matches events by name, so
  it would need a live migration for no behavioural difference. `source: 'practice'` tells the
  two kinds of overload apart.
