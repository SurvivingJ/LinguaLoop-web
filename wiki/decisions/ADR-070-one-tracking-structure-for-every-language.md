---
title: "ADR-070: One tracking structure for the grammar drills of every language"
status: accepted
date: 2026-11-28
---

# ADR-070: One tracking structure for the grammar drills of every language

## Context
Two branches built grammar drills on the same two days. `main` got the Chinese grammar drills
with server-side tracking (two tables and one function, pending,
[[decisions/ADR-066-grammar-drill-daily-tracking]]). The other branch got the Japanese drills
(particles, grammar, conjugation, reading) with a different store: one JSON document per learner
in a separate pending table, `user_drill_progress`. Both used the address `/grammar-drill`.
Neither migration was applied (checked on the live database on 2026-11-28: none of the objects
exists; the database was 431 MB).

Owner, 2026-11-28: "I think each language should have their own grammar drill routes" and "can
you resolve a shared db structure for tracking grammar drill progress and implement it".

## Decision
1. **One structure.** `grammar_drill_daily`, `grammar_drill_state` and
   `record_grammar_drill_round` (ADR-066) are the tracking structure for the drills of every
   language. `user_drill_progress`, its service and its two routes are removed; they were never
   applied.
2. **The database stays generic; the rules are per language in Python.** A row is keyed by
   (learner, language, topic). The database knows only: `stage` 1 to 7, and `state` is a JSON
   object with `u` (highest stage reached; never lowered) and `l` (epoch seconds of the last
   answer; the later side wins the merge). Which topics exist, how many stages a topic has and
   the rest of `state` are a `Profile` per language in `services/grammar_drill_tracking.py`:
   - Chinese (1): the topics of `static/data/grammar/zh`, four stages, sub-point misses,
     `state = {u, r, q, e, l}` (unchanged).
   - Japanese (3): every skill of the particle course and the grammar course (seven stages: six
     rungs and Instant), `conj-<form>` and `read-<category>` (four stages),
     `state = {u, l, s}` where `s` is the ladder state the browser keeps for the skill.
3. **The only schema change to ADR-066:** the stage limit goes from 4 to 7 (the table's CHECK
   and the two `LEAST(...)` in the function).
4. **One API.** `POST /api/grammar-drill/round` and `GET /api/grammar-drill/progress` take
   `language_id` 1 or 3. The Japanese page sends one request when a round ends.
5. **One page per language.** `/grammar-drill/zh` and `/grammar-drill/ja`. `/grammar-drill`
   sends the browser to the page of its study language.

## Consequences
- One migration to apply, one runbook, one place to read a learner's improvement over time, for
  both languages. A third language needs a `Profile`, no migration.
- Japanese gains daily summaries (answers, right first time, recall time, stage per day), which
  the JSON document did not have. Trend charts for Japanese are not built yet (TASK-1290).
- The Japanese ladder can demote, the Chinese one cannot. `u` therefore means "highest stage
  reached" for Japanese and the current rung is `state.s.l`.
- A Japanese learner can have several hundred state rows (one per skill started; about 330 bytes
  each with the index), where the JSON document was one row. At 431 MB against the 480 MB line
  this is affordable: 460 topics is about 150 kB per learner who starts everything.
- Interface settings of the Japanese page (furigana, chosen forms) no longer leave the browser.
- Progress made in a browser before the tables exist is uploaded once they do (`mode: sync`),
  and rounds played meanwhile wait in the browser (at most 60).

## Alternatives Considered
- **Keep both structures.** Two migrations and two ways to answer "how is this learner doing".
- **Move Chinese onto the JSON document.** Loses the daily history the owner asked for.
- **A `drill` column beside `language_id`** (particles, grammar, conjugation, reading as separate
  drills). Not needed: topic ids are unique within a language, and a family prefix
  (`conj-`, `read-`) already says which drill a topic belongs to.
- **Per-language stage limits in the database.** The limit that matters is per topic (a
  Japanese conjugation topic has four stages, a particle skill seven); that is content
  knowledge, which lives in Python with the catalogs.
