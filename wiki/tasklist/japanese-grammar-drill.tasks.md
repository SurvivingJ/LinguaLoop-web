---
title: "Grammar Drill and Reading Drill (Japanese) — Task Breakdown"
feature: japanese-grammar-drill
prose_page: ../features/japanese-grammar-drill.md
tech_page: ../features/japanese-grammar-drill.tech.md
total_tasks: 4
done: 3
---

# Grammar Drill and Reading Drill (Japanese) — Task Breakdown

Built on 2026-11-27 (owner, after the particle drill: "build all of them, the same way").

---

## TASK-1278: Second course in the pipeline, service, routes and page

**Status:** [x] Done (2026-11-27)
**Feature:** japanese-grammar-drill
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1271

**Description:**
Make the particle pipeline and page serve a second course: `PD_COURSE`, the grammar catalog and
its authoring rules, the `course` parameter of the content routes, `/grammar-drill`, the two
kanji question kinds (`ask: reading | kanji`), group companions for interleaving.

**Acceptance Criteria:**
- [x] `scripts/grammar_drill_catalog.py --apply` writes 182 skills summing to 8,000 target items; ids disjoint from the particle course (test)
- [x] the validator enforces the two kanji kinds (tests)
- [x] `?course=grammar` selects the content; unknown course is 400 (test)
- [x] reading and look-alike questions do not reveal the answer through furigana (vitest, browser walk)

**Technical Notes:**
See [[features/japanese-grammar-drill.tech]]. Catalog rows now send `conf` to the browser; before this
the listed confusers of a particle skill were never used for interleaving.

**Files to Create / Modify:**
- `scripts/grammar_drill_catalog.py`, `grammar_drill_validate.py`, `particle_drill_{catalog,validate,swarm,build}.py`
- `data/particle_drill/AUTHORING_GRAMMAR.md`
- `services/particle_drill/content.py`, `routes/particle_drill.py`, `web/pages.py`, `templates/grammar_drill.html`
- `static/js/particles/{exercises,mastery}.js`, `static/js/pages/particle-drill.js`, nav templates, `static/i18n/*.json`

**Verification:**
`pytest tests/test_grammar_drill.py -q` passes; open `/grammar-drill` and drill 熟字訓.

---

## TASK-1279: Author and review the grammar content

**Status:** [x] Done (2026-11-27)
**Feature:** japanese-grammar-drill
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1278

**Description:**
Run the pipeline for the grammar course: 8,340 items over 182 skills, 48 guides, 18 pattern
packs and the katakana list (609 words).

**Acceptance Criteria:**
- [x] every skill at or over its target, with a guide section (test)
- [x] every content file named by a review record (test)
- [x] 0 validation errors; `manifest.json` current (tests)

**Technical Notes:**
Run record: 187 jobs (145 item batches including one top-up, 37 guide batches, 4 pack batches,
the katakana list), each written by one headless Claude Code worker (Sonnet for items and the
list, Opus for guides and packs) and reviewed by an Opus worker in a separate context, signed in
with the session login. No job failed. Reviewers checked 9,160 entries, corrected 1,659 and
deleted 32. Notional cost from the worker logs: about $225. Twice during the run a worker edited
`data/particle_drill/ja/conjugation/verbs_n3.json` (the other course, outside its assignment);
both edits were reverted from git before committing. A seven-job pilot was read before the full run.

**Files to Create / Modify:**
- `data/particle_drill/ja-grammar/`

**Verification:**
`python scripts/grammar_drill_validate.py --summary` prints `0 errors` and no skill under target.

---

## TASK-1280: Reading drill (numbers, prices, times, dates, durations, ages, katakana)

**Status:** [x] Done (2026-11-27)
**Feature:** japanese-grammar-drill
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1277

**Description:**
`static/js/particles/numbers.js` generates and reads the questions by rule; `/reading-drill`
runs them on the conjugation drill's three rungs; `GET /api/particle-drill/reading` serves the
katakana list.

**Acceptance Criteria:**
- [x] about 100 hand-written readings pass (vitest)
- [x] every generated question has three wrong readings, none of them accepted (vitest, 1,500 per category)
- [x] accepted variants (しちじ / ななじ, じっぷん, よんえん, はたち) are accepted when typed
- [x] the page is linked from the nav, the Practice chips, the Me page and both hubs

**Technical Notes:**
Progress ids are `read:<category>` in the `conj` map of the progress document.

**Files to Create / Modify:**
- `static/js/particles/numbers.js`, `static/js/pages/particle-drill.js`, `templates/reading_drill.html`
- `routes/particle_drill.py`, `services/particle_drill/content.py`

**Verification:**
Open `/reading-drill`, start: a price, a time and a date come up; type `sanbyakuen` for 300円.

---

## TASK-1281: Native-speaker spot check of the grammar answer keys

**Status:** [?] Awaiting owner
**Feature:** japanese-grammar-drill
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1279

**Description:**
As TASK-1272 for the particle course: no human has checked a sample. Draw about 300 items
stratified by stage; keigo, the conditionals and the conjecture patterns (そう / よう / らしい) carry
the most risk of a distractor that a native speaker would accept.

**Acceptance Criteria:**
- [ ] sample judged; error rate per stage reported in `wiki/evaluations/`
- [ ] wrong items fixed or removed; manifest rebuilt

**Technical Notes:**
`data/particle_drill/ja-grammar/review/*.json` lists what the reviewers changed.

**Files to Create / Modify:**
- `wiki/evaluations/grammar-drill-spot-check-<date>.md`

**Verification:**
The evaluation page exists and its fixes are merged.
