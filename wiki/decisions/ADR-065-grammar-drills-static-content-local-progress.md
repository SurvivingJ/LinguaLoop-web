---
title: "ADR-065: Grammar drills as static files, client-side generators and localStorage progress"
status: accepted
date: 2026-11-27
---

# ADR-065: Grammar drills as static files, client-side generators and localStorage progress

> **Partly superseded 2026-11-27:** Decision point 3 (progress kept in `localStorage` only) and
> the first two points under "Harder or now constrained" are superseded by
> [[decisions/ADR-066-grammar-drill-daily-tracking]]: progress is also written to the server as
> daily summaries plus one state row per topic, and the database stop line is 480 MB (was
> 475 MB). Points 1, 2 and 4 stand. The text below is unchanged.

## Context

The owner asked (2026-11-27) for particle-style drilling: "a drill drill drill thing. Build out a
complete set of 10000 exercises and the associated guides… Make it infinite practice where
possible. Do not use openrouter or anthropic api, just Claude headless subagents… drill them so it
becomes instantaneous", then "do the above but for Chinese", and after the proposal: "Japanese is
wip, so just build a Chinese one", "Pinyin on demand", and on storage: "At the moment we haven't
got the space so maybe static?".

The constraint behind the last answer: the database was at 473.15 MB against the owner's 475 MB
stop line (the plan's cap is 500 MB; see [[log]] 2026-11-24). Exercise content for the vocabulary
ladder that did not fit is already being held offline for the same reason. About 10,000 drill
items with pinyin, English and an explanation each come to 5.54 MB as compact JSON, before any
index or row overhead.

The content is read-only, identical for every learner and changes only when the repository
changes. Learner progress, in contrast, is per user and written on every answer.

## Decision

1. **Content is static files.** Guides and drill items are authored as files under
   `data/grammar_drills/zh/`, validated and built by `scripts/grammar_drills.py` into
   `static/data/grammar/zh/` (one manifest plus one JSON file per topic, each versioned by a
   content hash), and fetched by the page as ordinary static files. No table, RPC or migration.
2. **Infinite practice is generated in the browser.** Generators in
   `static/js/grammar/generators/` build items from curated word lists. No model is called at
   run time.
3. **Learner progress is kept in `localStorage`** (key `ld.grammar.zh.v1`) for now, behind a
   single module (`static/js/grammar/store.js`) with a `dump()` method, so that a server sync can
   be added later without changing the drill engine.
4. **Answers are checked in the browser.** The page calls no API.

The owner's wording on storage was tentative ("maybe static?"); the feature was built this way
and this record is filed as accepted on that basis. Point 3 is explicitly provisional.

Specification: [[features/grammar-drills.tech]].

## Consequences

**Easier**

- No database growth: 0 rows, 0 MB. The feature could be built while the database is at its line.
- No migration, no live apply step, no API cost per answer, no server latency per answer.
- Content is reviewed and versioned in git; `build --check` and a pytest case fail when the
  served files are out of date or invalid.
- Topic files are cached by content hash; the hub loads only the 42 KB manifest.

**Harder or now constrained**

- **Progress is per browser.** It is not tied to the account, is lost when site data is cleared,
  and does not follow the learner to another device (TASK-1259).
- **The server knows nothing about grammar practice.** No Study Plan or daily-session
  integration, no ELO, no Knowledge Report input, no usage analytics (TASK-1260).
- **Answers ship to the client.** Acceptable for self-study drills with no stakes; it would not
  be for anything scored or ranked.
- **Content changes need a deploy.** A wrong item cannot be fixed with a database update.
- **The repository grows**: 5.54 MB of built JSON plus the authoring files (batches, blind packs,
  reviewed copies, verdicts) are committed.
- **Generated sentences are limited by the word lists**; they are grammatical but sometimes
  semantically flat (TASK-1265).
- The stored progress format (`v: 1`) becomes a compatibility surface: a later sync must read it
  or migrate it.

## Alternatives Considered

1. **Database tables for topics, guides and items** (the pattern of
   [[features/measure-word-trainer]], which is database-backed). Rejected for now: no space
   (473.15 MB against 475 MB), and the content does not need per-row queries. Would allow fixes
   without a deploy and server-side selection.
2. **Content files in Supabase Storage** (the pattern of
   [[decisions/ADR-049-exercise-content-in-storage]]). Rejected: adds a storage dependency and a
   read path through the API for content that the application's own static file serving handles;
   nothing here is per-user or access-controlled.
3. **A progress table now** (one row per user and language, or one row per answer). Rejected for
   the first build: needs a migration applied live and write traffic on every answer, at a time
   when the database is at its line. Deferred, not ruled out (TASK-1259). A single JSON row per
   user would be small.
4. **Generating items with a hosted model at request time.** Rejected: cost and latency per item,
   unreviewed output shown to learners, and the owner excluded OpenRouter and the Anthropic API
   for this feature.
5. **One large content file.** Rejected: 5.5 MB on first load for a learner who opens one topic.

## Related

- [[features/grammar-drills]], [[features/grammar-drills.tech]]
- [[tasklist/grammar-drills.tasks]]
- [[decisions/ADR-066-grammar-drill-daily-tracking]] — supersedes point 3
