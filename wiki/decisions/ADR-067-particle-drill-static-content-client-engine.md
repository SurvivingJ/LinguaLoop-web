---
title: "ADR-067: Particle drill content ships as files and is drilled in the browser"
status: accepted
date: 2026-11-27
---

# ADR-067: Particle drill content ships as files and is drilled in the browser

## Context

The owner asked for a Japanese particle drill "akin to our ladder": guides for every particle,
10,000 exercises, endless practice where possible, conjugation rules, and drilling until the
answer is instantaneous; content to be written by Claude headless subagents, with no OpenRouter
or Anthropic API call (2026-11-27).

Three facts shaped the design:

1. **Database size.** The live database stood at 473.15 MB against the owner's 475 MB stop line
   (2026-11-24, [[tasklist/report-and-placement-apply-runbook]]); 2,452 authored word senses are
   already held offline for that reason. There is no room for a new content table.
2. **Speed is the product.** The existing trainers ([[features/measure-word-trainer.tech]]) fetch
   a round from a session RPC and post the result; a measured API round trip on this stack is
   about 270 ms at the median. For answers that should take about a second, any per-answer
   request would be a large part of the experience.
3. **The existing vocabulary ladder is per word sense** (`word_assets`, `exercises`,
   `user_word_ladder`). A particle skill is not a word sense: one particle has many functions,
   and one sentence exercises several particles at once.

## Decision

1. **Content is static files** under `data/particle_drill/ja/`, committed with the code:
   a catalog of skills, one guide file per particle group, one exercise file per skill (JSON
   lines), pattern packs, and the conjugation word lists. A manifest holds the counts and a
   content hash. No content table is created.
2. **A small Flask service reads the files** (`services/particle_drill/content.py`) and four
   authenticated, cacheable GET routes serve the catalog, one skill, and the conjugation data.
3. **The drill engine runs in the browser** (`static/js/particles/`): it builds each exercise
   from an item and the learner's rung, judges the answer, and moves the ladder. A round makes
   no request.
4. **A skill is one function of one particle**, with its own six-rung ladder (Meet, Choose,
   Type, Fill all, Fix, Speed) and spaced reviews after mastery. One authored sentence serves
   all six exercise types because every particle in it is marked.
5. **Endless practice comes from authored pattern packs** expanded in the browser, and from a
   rule-based conjugation engine; never from a model call at request time.
6. **Progress is a JSON document kept in the browser**, mirrored to one row per learner in a
   new table `user_drill_progress` once `migrations/particle_drill_progress.sql` is applied.
   The page works without the table. **Superseded on 2026-11-28 by
   [[decisions/ADR-068-one-tracking-structure-for-every-language]]:** the mirror is the shared
   grammar-drill tracking (one state row per skill, daily summaries); `user_drill_progress` was
   withdrawn before it was applied.
7. **Authoring is done by `claude -p` workers**, each file written by one worker and reviewed
   by another in a separate context, then checked by a deterministic validator
   (`scripts/particle_drill_swarm.py`, `particle_drill_validate.py`).

## Consequences

**Easier**

- Nothing has to be applied to the live database for the drill to work; the content adds no
  database bytes.
- Content changes are reviewed as diffs and roll back with the code.
- Answering is instant, works on a poor connection once a skill is loaded, and the server does
  no work per answer.
- The same content can later feed a server-side session (the files are the source of truth).

**Harder / constrained**

- The answer key is sent to the browser. Acceptable for practice; **this drill must not become
  a scored or ELO-bearing test without a server-judged path.**
- Ladder state is not trustworthy server-side (it is client-written). It must not be used for
  entitlements, placement or the knowledge report without re-validation.
- The drill does not yet write `test_attempts`, study time or ELO, so it is invisible to the
  weekly-minutes total and the daily session ([[tasklist/particle-drill.tasks]] TASK-1273, 1239).
- The repository grows by about 5.8 MB of JSON, and every web worker holds the loaded
  skills in memory (at most that much).
- Content fixes need a deploy.
- A content error reported by a learner cannot be patched in place; it needs an edit to a
  file and `scripts/particle_drill_build.py --apply`.

**2026-11-27, later the same day:** the decision was reused unchanged for a second course
(`data/particle_drill/ja-grammar/`, [[features/japanese-grammar-drill]]): 8,340 more items as files, no table.

## Alternatives Considered

- **Database tables and a session RPC, like the measure-word drill** (`dim_classifiers` …,
  `get_classifier_drill_session_v2`). Consistent with the siblings and gives server-side
  mastery and ELO for free, but needs about 6 to 10 MB of table and index space the database
  does not have, a live apply before anything works, and a round trip per round.
- **Reuse the vocabulary ladder** (`word_assets` / `exercises` rows per particle sense). The
  ladder's promotion machinery is per word sense and its exercise types assume a headword; a
  sentence with four particles does not fit one row, and it would again be database content.
- **Generate sentences with a model at request time.** Unbounded variety, but latency, cost,
  and an unreviewed answer key in a drill whose whole value is a correct key.
- **Static files under `static/`.** Simplest, but served without a login and outside the
  paywall model ([[business/pricing-plan]]).
- **Server-side ladder with a per-answer API.** Trustworthy state, at the cost of the speed
  that is the point of the drill.
- **The Workflow tool for authoring.** Tried first; on the 4-CPU session container it runs two
  agents at a time (about a day for 272 jobs). Replaced by a pool of ten `claude -p` workers.
