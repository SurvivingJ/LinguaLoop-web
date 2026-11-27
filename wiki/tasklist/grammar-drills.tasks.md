---
title: "Chinese Grammar Drills — Task Breakdown"
feature: grammar-drills
prose_page: ../features/grammar-drills.md
tech_page: ../features/grammar-drills.tech.md
total_tasks: 15
done: 5
last_updated: 2026-11-27
---

# Chinese Grammar Drills — Task Breakdown

TASK-1234 to TASK-1248. TASK-1234 to 1238 record what was built on branch
`claude/happy-gates-qp9ifs` (2026-11-27, not deployed). TASK-1239 to 1248 are the follow-ups;
five of them are `[?]` because they wait on an owner decision, and each states the question.
TASK-1239 (progress tracking) was built the same day and is `[?]` Done (repo), awaiting the live
apply of its migration ([[decisions/ADR-065-grammar-drill-daily-tracking]]).
Specification: [[features/grammar-drills.tech]]. Decision record:
[[decisions/ADR-064-grammar-drills-static-content-local-progress]].

---

## TASK-1234: Content contract, topic plan and the `grammar_drills.py` script

**Status:** [x] Done (2026-11-27, repo)
**Feature:** grammar-drills
**Type:** infra
**Complexity:** L (1-2d)
**Depends On:** none

**Description:**
Define what a grammar drill item and a topic guide are, plan the topics, and write the one script
that validates authored content, supports blind review and builds the files the app serves. The
script works on local files only, so the whole content pipeline runs with no database and no
network.

**Acceptance Criteria:**
- [x] `data/grammar_drills/zh/SPEC.md` defines the four item types (cloze, order, rewrite, judge), the sentence and pinyin rules, the batch requirements and the guide format
- [x] `data/grammar_drills/zh/plan.json` lists 39 topics in 7 categories with a type mix and scope each; batches sum to 105
- [x] `scripts/grammar_drills.py` has the commands `validate`, `validate-guide`, `strip`, `compare`, `clean`, `build` (`--check`) and `stats`
- [x] `build` leaves out invalid lines and repeated sentences and writes `manifest.json` plus one file per topic with a content-hash version
- [x] `tests/test_grammar_drills_script.py` passes (19 cases), including a case that fails when shipped content is invalid or the static files are stale
- [x] `ruff check scripts/grammar_drills.py tests/test_grammar_drills_script.py` is clean

**Technical Notes:**
Commands and rules: [[features/grammar-drills.tech]] "Script" and "Data Contract". After the pilot
the validator was tightened (ASCII punctuation rejected; suffix `r` rejected on 儿子 / 女儿).
`clean` and the sentence-level de-duplication in `build` were added during the content run.

**Files to Create / Modify:**
- `data/grammar_drills/zh/SPEC.md` — content contract
- `data/grammar_drills/zh/plan.json` — topics, categories, mixes, themes
- `scripts/grammar_drills.py` — validator, blind-review helpers, build
- `tests/test_grammar_drills_script.py` — script tests

**Verification:**
`python -m pytest tests/test_grammar_drills_script.py -q` → 19 passed.
`python scripts/grammar_drills.py build --check` → "static files are up to date".

---

## TASK-1235: Topic guides (39) written, validated and reconciled with reviewer notes

**Status:** [x] Done (2026-11-27, repo)
**Feature:** grammar-drills
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1234

**Description:**
Write one guide per topic: a summary, the sub-points that items reference, rules with patterns and
examples, wrong/right contrasts and a cheat sheet. One Claude subagent per topic. After the
content review, a separate agent softened guides that claimed more than native usage supports.

**Acceptance Criteria:**
- [x] 39 files in `data/grammar_drills/zh/guides/`, one per plan topic
- [x] Every guide passes `python scripts/grammar_drills.py validate-guide`
- [x] 34 guides reconciled with `review_concerns.md` where they overclaimed (commit `439b5db`)
- [x] `tone-sandhi` has a guide although it has no written items

**Technical Notes:**
Guide format: SPEC.md "Guide file". The `subs` keys are the contract between a guide and its
items; changing a key invalidates items that use it.

**Files to Create / Modify:**
- `data/grammar_drills/zh/guides/*.json` — 39 guides

**Verification:**
`python scripts/grammar_drills.py validate-guide data/grammar_drills/zh/guides/*.json` exits 0;
`python scripts/grammar_drills.py stats` shows `yes` in the guide column for every topic.

---

## TASK-1236: Drill content authored, blind-reviewed and built (105 batches, 10,209 items)

**Status:** [x] Done (2026-11-27, repo)
**Feature:** grammar-drills
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1234, TASK-1235

**Description:**
Author the drill items in batches of 100 and review each batch independently. Claude subagents
only (no OpenRouter, no Anthropic API key): per batch one author agent (Sonnet), then a reviewer
agent (Sonnet) in a fresh context that solves a stripped copy blind, compares with the keys,
reviews every item, fixes and re-validates. A pilot on 了 and word order came first.

**Acceptance Criteria:**
- [x] 105 files in each of `batches/`, `reviewed/` and `verdicts/`; 210 files in `blind/`
- [x] Every reviewed batch passes `validate`; 10,521 reviewed items in total
- [x] Reviewer notes per batch recorded in `data/grammar_drills/zh/review_concerns.md`
- [x] Five top-up batches (了, result-complement, coverbs, final-particles, bu-mei) added so the built total passes 10,000
- [x] `build` writes 10,209 items in 39 topics (312 repeated sentences and 0 invalid lines left out): cloze 5,471, order 1,616, rewrite 1,027, judge 2,095; 5.54 MB

**Technical Notes:**
Verdict files: `{ flagged, fixed, dropped, added, items }`; summed over all batches 145 flagged by
the blind compare, 1,091 fixed, 3 dropped, 3 added. No native speaker has checked the result
(TASK-1241).

**Files to Create / Modify:**
- `data/grammar_drills/zh/batches/*.jsonl` — authored batches
- `data/grammar_drills/zh/blind/*` — stripped copies and blind answers
- `data/grammar_drills/zh/reviewed/*.jsonl` — reviewed batches (the build source)
- `data/grammar_drills/zh/verdicts/*.json`, `review_concerns.md` — review records
- `static/data/grammar/zh/*.json` — built output (40 files)

**Verification:**
`python scripts/grammar_drills.py stats` → TOTAL 105 / 105 files 10521 / 105 files 10521.
`python scripts/grammar_drills.py build --check` → "10209 items in 39 topics; 312 duplicates and
0 invalid lines left out", "static files are up to date".

---

## TASK-1237: `/grammar-drill` page: engine, four-stage ladder, local progress, i18n, profile link

**Status:** [x] Done (2026-11-27, repo)
**Feature:** grammar-drills
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1234

**Description:**
Build the page that serves the drills: hub, topic guide, drill round, results, Mixed review and
Endless mode, with the rules in DOM-free modules and progress in `localStorage`. Pinyin is shown
on demand as ruby text.

**Acceptance Criteria:**
- [x] Route `/grammar-drill` (`grammar_drill_page`) renders `templates/grammar_drill.html`; 117 URL rules
- [x] Four stages (Recognise, Build, Recall, Speed); next stage opens at 85% over the last 30 answers; "Instant" at stage 4 with 90% and a median recall time under 3 s
- [x] A missed item returns in the same round until answered right; scores count first answers
- [x] Recall hides a cloze item's options until "Show choices", or takes a typed answer
- [x] Progress under `localStorage['ld.grammar.zh.v1']`; the page works when storage is blocked
- [x] 82 `grammar_drill.*` keys in each of the four bundles; zh-gated link on the profile page
- [x] vitest 1,088 passed in 53 files; `npm run check` 0 errors

**Technical Notes:**
Module table, ladder, selection and store format: [[features/grammar-drills.tech]]. The es / ja /
zh strings are unreviewed machine translations (TASK-1243).

**Files to Create / Modify:**
- `templates/grammar_drill.html`, `web/pages.py`, `templates/profile.html`
- `static/js/pages/grammar-drill.js`, `static/js/grammar/{text,check,ladder,select,round,store,data,render,app}.js`
- `static/css/redesign/grammar.css`
- `static/i18n/{en,es,ja,zh}.json`
- `tests/unit/grammar-{text-check,ladder-store,select-round,app}.test.js`

**Verification:**
`npx vitest run` → 53 files, 1,088 passed. Open `/grammar-drill` with Chinese as the study
language, start 了 at stage 1, miss an item and see it return three items later.

---

## TASK-1238: Infinite-practice generators (22 generators, 13 topics) and Endless mode

**Status:** [x] Done (2026-11-27, repo)
**Feature:** grammar-drills
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1237

**Description:**
Add browser-side generators that build drill items from curated word lists, so topics with a
regular pattern can be practised without end. Endless mode mixes generated items with the topic's
written items.

**Acceptance Criteria:**
- [x] `generatorsFor(slug)` returns `[{ key, label, make(rng) }]`; `GENERATOR_TOPICS` lists 13 slugs
- [x] 22 generators: numbers-time 4, er-liang 1, tone-sandhi 3, measure-words 1, de-three 1, bu-mei 1, potential-complement 1, word-order 1, ba 2, bei 2, comparison 2, duration-frequency 1, separable-verbs 2
- [x] Every random choice goes through `rng`, so a seeded `rng` reproduces the output
- [x] Generated items (`id` starting `gen:`) are never written to the progress store
- [x] The generators module is optional: the page works when it is absent
- [x] `tests/unit/grammar-generators.test.js` passes

**Technical Notes:**
Interface and table: [[features/grammar-drills.tech]] "Generators". `tone-sandhi` is served by
generators only. Sentence meaning is sometimes flat (TASK-1245).

**Files to Create / Modify:**
- `static/js/grammar/generators/{index,util,numbers-time,er-liang,tone-sandhi,measure-words,de-three,bu-mei,potential-complement,word-order,ba-bei,comparison,duration-frequency,separable-verbs}.js`
- `tests/unit/grammar-generators.test.js`

**Verification:**
`npx vitest run tests/unit/grammar-generators.test.js` passes. On the page, open 把 and tap
"Endless".

---

## TASK-1239: Track grammar-drill progress on the server (daily summaries + state)

**Status:** [?] Done (repo, 2026-11-27), awaiting live apply of `migrations/grammar_drill_tracking.sql`
**Feature:** grammar-drills
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** none (the live migration needs the owner to apply it; the database must be under 480 MB)

**Description:**
Progress lived in one browser's `localStorage`, so the server knew nothing about practice and a
second device started again. The owner asked for tracking of improvement over time and chose
daily rows with the stop line raised to 480 MB
([[decisions/ADR-065-grammar-drill-daily-tracking]]). Built: one summary row per learner, topic
and practice day, one state row per learner and topic, one idempotent function that writes both,
two API routes, a browser queue that resends unsent rounds, a merge on load, and progress views
on the topic screen and the hub. This replaces the first sketch of this task (one JSON value per
user, GET/PUT, debounced writes), which gave sync but no history.

**Acceptance Criteria:**
- [x] `grammar_drill_daily` (PK user, language, topic, practice day) and `grammar_drill_state` (PK user, language, topic) are defined with CHECK constraints, RLS on, an own-row SELECT policy, and no client privilege; no per-answer or per-item rows
- [x] `record_grammar_drill_round` writes both in one transaction and does not double count a repeated `round_key`; SECURITY DEFINER with pinned `search_path`, EXECUTE service_role only; `tests/test_migration_security_lint.py` passes
- [x] `POST /api/grammar-drill/round` validates language, round key, mode, topic slugs and sub-point keys against the manifest, and all bounds; `GET /api/grammar-drill/progress` returns only the caller's rows, `days` capped at 365
- [x] The practice day is the app review day, computed in Python and passed in
- [x] With the tables or function missing both routes answer a logged 503 and the page carries on locally with no message
- [x] After every finished round, Mixed review and Endless stop the page sends per-topic first-try totals; unsent rounds wait in `localStorage` and are resent with the same key
- [x] On load the page merges the server state (higher unlocked stage, fresher rolling results) and never loses local progress; local-only progress is uploaded once as state, without daily history
- [x] Topic "Progress" card (accuracy and recall time over the last 30 practised days, change since the first week, "needs work" sub-points of the last 14 days) and hub summary (days practised in 30, answers, instant topics, activity strip), pure SVG; empty and one-day states handled; nothing drawn without server history
- [x] i18n keys in all four bundles (21 new, 103 `grammar_drill.*` in total)
- [x] Row size measured: about 246 bytes per daily row with index; 665 to 1,250 per state row (the 150-byte budget was not met, see GQ11)
- [x] pytest (15 route tests), vitest (25 + 7 cases) and a Playwright check with stubbed routes pass
- [ ] `migrations/grammar_drill_tracking.sql` applied live and its VERIFY AFTER checks pass
- [ ] One real round recorded and read back on the deployed app (second browser shows the same stage)

**Technical Notes:**
Specification: [[features/grammar-drills.tech]] "API / RPC Surface" and "Progress tracking";
tables: [[database/schema.tech]] "Grammar drill tracking"; apply steps and owner queries:
[[tasklist/grammar-drill-tracking-runbook]]; pending entry `migrations/PENDING-2026-11-27.md`.
The migration was run on a scratch PostgreSQL 16 only, never against Supabase. Known limits:
one remembered round key per state row (a resend after another device wrote the same topic is
counted twice); item review boxes stay per browser; history starts at apply time. Open: GQ11
(row size against the budget) and GQ12 (retention) in [[features/grammar-drills]].

**Files to Create / Modify:**
- `migrations/grammar_drill_tracking.sql`, `migrations/grammar_drill_tracking_rollback.sql`, `migrations/PENDING-2026-11-27.md` — tables, RLS, function, rollback, apply entry
- `services/grammar_drill_tracking.py`, `routes/grammar_drill.py`, `app.py`, `web/rate_limits.py` — validation, storage calls, the two routes, registration, limits
- `static/js/grammar/sync.js`, `trends.js`, `trendview.js` (new); `store.js`, `app.js`; `static/css/redesign/grammar.css`; `templates/grammar_drill.html`; `static/i18n/{en,es,ja,zh}.json`
- `tests/test_grammar_drill_tracking_routes.py`, `tests/unit/grammar-sync-trends.test.js`, `tests/unit/grammar-app.test.js`

**Verification:**
`python -m pytest tests/test_grammar_drill_tracking_routes.py tests/test_migration_security_lint.py -q`
and `npx vitest run tests/unit/grammar-sync-trends.test.js tests/unit/grammar-app.test.js`. After
the live apply: practise a topic signed in, run query 1 of
[[tasklist/grammar-drill-tracking-runbook]] (`daily_rows` at least 1), reload and see "Your
progress" on the hub; sign in from a second browser and see the same stage.

---

## TASK-1240: Decide whether grammar drills join the Study Plan / daily session and feed ELO

**Status:** [?] Awaiting owner decision
**Feature:** grammar-drills
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1239

**Description:**
Grammar drills are a separate page: not a daily-session block, not counted by the Study Plan, no
ELO and no Knowledge Report input. **Question for the owner:** should a grammar block appear in
the daily session (and count toward plan minutes), and should results feed any learner model? If
yes, which topic does the session pick, and how long is a block?

**Acceptance Criteria:**
- [ ] The owner's answer is recorded in [[features/grammar-drills]] (GQ2) and, if it changes the architecture, in an ADR
- [ ] If yes: this task is replaced by concrete tasks for the session block, the plan accounting and the model input

**Technical Notes:**
Any integration needs server-side knowledge of progress, hence the dependency on TASK-1239. See
[[features/study-plans.tech]] and [[pages/study-session.tech]] for the block model.

**Files to Create / Modify:**
- `wiki/features/grammar-drills.md` — record the decision

**Verification:**
GQ2 is marked ANSWERED with the owner's words.

---

## TASK-1241: Native-speaker audit of the drill content

**Status:** [ ] Not Started
**Feature:** grammar-drills
**Type:** test
**Complexity:** XL (>2d)
**Depends On:** none (needs a native speaker of Mandarin)

**Description:**
All 10,209 items and 39 guides were written and reviewed by Claude agents. The reviewers fixed
1,091 items and left some borderline ones in, naming them in `review_concerns.md`. A native
speaker should check the listed items first, then a random sample, and the result should be fed
back as edits to `reviewed/` and a rebuild.

**Acceptance Criteria:**
- [ ] Every item named as a residual risk or judgement call in `data/grammar_drills/zh/review_concerns.md` is marked keep, fix or drop by a native speaker
- [ ] A random sample of at least 300 items not named there (stratified by item type) is checked and the defect rate reported per type
- [ ] Fixes are made in `data/grammar_drills/zh/reviewed/`, every touched batch passes `validate` (with `--min-items` where items were dropped), and the static files are rebuilt
- [ ] If the sample defect rate is above an agreed level, the task result proposes how much more to audit
- [ ] The result is filed as a page under `wiki/evaluations/`

**Technical Notes:**
The defects most likely to remain, from the reviewer notes: a cloze distractor that is also
acceptable; a missing `alts` order; a judge item marked wrong that natives accept colloquially; a
`why` text that overclaims. `python scripts/grammar_drills.py build --check` must pass at the end.

**Files to Create / Modify:**
- `data/grammar_drills/zh/reviewed/*.jsonl` — fixes
- `static/data/grammar/zh/*.json` — rebuilt
- `wiki/evaluations/grammar-drills-native-audit-[date].md` — result

**Verification:**
`python -m pytest tests/test_grammar_drills_script.py -q` passes after the rebuild; the
evaluation page states items checked, defects found and the rate per type.

---

## TASK-1242: Decide the languages for guide and explanation text

**Status:** [?] Awaiting owner decision
**Feature:** grammar-drills
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** none

**Description:**
Guides, the English meaning of each sentence and each item's `why` are English only, whatever the
interface language. **Question for the owner:** which other languages are wanted (es, ja, zh are
the other interface bundles), and does that cover the guides only (39 files) or also the 10,209
`en` cues and `why` texts? The second option multiplies the static content per language.

**Acceptance Criteria:**
- [ ] The owner's answer is recorded in [[features/grammar-drills]] (GQ4)
- [ ] If yes: the SPEC gains a rule for localised fields, and concrete authoring and build tasks replace this one

**Technical Notes:**
The SPEC states "Explanations are in plain English" and "The learner is an English speaker". A
localised build would need per-language topic files so that a learner does not download every
language.

**Files to Create / Modify:**
- `wiki/features/grammar-drills.md` — record the decision

**Verification:**
GQ4 is marked ANSWERED with the owner's words.

---

## TASK-1243: Review the es / ja / zh interface strings for the grammar-drill page

**Status:** [ ] Not Started
**Feature:** grammar-drills
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The Spanish, Japanese and Chinese strings for this page were machine-translated and nobody has
reviewed them. Have each bundle checked by someone who reads the language and correct what is
wrong or unnatural.

**Acceptance Criteria:**
- [ ] All 82 `grammar_drill.*` keys plus `common.nav.grammar_drill` and `me.grammar_drill_sub` are reviewed in `es.json`, `ja.json` and `zh.json`
- [ ] Placeholders (`{n}`, `{count}`, `{pct}`, `{next}`, `{need}`, `{have}`, `{stage}`) are unchanged in every corrected string
- [ ] Stage names are consistent wherever they appear in a bundle
- [ ] The existing i18n key-parity test still passes

**Technical Notes:**
English is the source. The keys are flat (`"grammar_drill.<key>"`) in `static/i18n/*.json`.

**Files to Create / Modify:**
- `static/i18n/es.json`, `static/i18n/ja.json`, `static/i18n/zh.json` — corrected strings

**Verification:**
`python -m pytest -q -k i18n` and `npx vitest run` pass; open `/grammar-drill` in each interface
language and read the hub, a drill item and the results screen.

---

## TASK-1244: Decide how Recall time is measured

**Status:** [?] Awaiting owner decision
**Feature:** grammar-drills
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
At the Recall and Speed stages a cloze item's time is the time until the learner taps "Show
choices". The learner can tap at once and then think with the options visible, so the "Instant"
badge (median under 3 s) rests on a self-reported time. **Question for the owner:** keep it as is,
judge "Instant" on the whole answer time (already stored), or require typed answers at the Speed
stage?

**Acceptance Criteria:**
- [ ] The owner's answer is recorded in [[features/grammar-drills]] (GQ6)
- [ ] If the rule changes: `ladder.isInstant` and the results screen use the chosen time, and `tests/unit/grammar-ladder-store.test.js` covers it

**Technical Notes:**
Both times are stored per answer: `r` (recall time, signed) and `w` (total time) in
`store.js`, so judging on the total time needs no change to stored data. With typed answers there
is no "Show choices" step and the recorded time is already the whole answer.

**Files to Create / Modify:**
- `static/js/grammar/ladder.js` — `isInstant` (if changed)
- `static/js/grammar/app.js` — results text (if changed)

**Verification:**
GQ6 is marked ANSWERED; if changed, the unit tests state the new rule.

---

## TASK-1245: Improve the meaning of generated sentences

**Status:** [ ] Not Started
**Feature:** grammar-drills
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Generators combine subjects, verbs and objects from word lists. The output is grammatical but
sometimes flat or slightly odd in meaning. Sample each generator, list the combinations that read
badly and restrict the lists (pair verbs with the objects they take, drop poor entries) so that
samples read like sentences a person would say.

**Acceptance Criteria:**
- [ ] For each of the 22 generators, 200 items from a seeded `rng` are read and the odd ones listed in the task result
- [ ] Word lists are changed so that a fresh 200-item sample per generator has no item judged semantically odd by the reviewer
- [ ] Every generated item still satisfies the item shape (`tests/unit/grammar-generators.test.js` passes)
- [ ] No generator's number of distinct outputs over 2,000 draws falls below half its value before the change (stated per generator)

**Technical Notes:**
Builders: `cloze` and `order` in `static/js/grammar/generators/util.js`. A reviewer agent in a
fresh context is acceptable for the reading; a native speaker is better (TASK-1241).

**Files to Create / Modify:**
- `static/js/grammar/generators/*.js` — word lists and pairings
- `tests/unit/grammar-generators.test.js` — any new shape or variety checks

**Verification:**
`npx vitest run tests/unit/grammar-generators.test.js` passes; the task result lists the
before/after variety per generator.

---

## TASK-1246: Make the contract and script reusable for Japanese particles

**Status:** [ ] Not Started
**Feature:** grammar-drills
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
A Japanese particle counterpart is work in progress elsewhere and should reuse this contract
rather than define its own. Today `scripts/grammar_drills.py` has `LANG = 'zh'` as a constant and
its sentence and reading checks are Chinese-specific; the page, the store key and the static path
are also `zh`. Make the language a parameter and isolate the language-specific checks.

**Acceptance Criteria:**
- [ ] Every script command takes `--lang` (default `zh`) and reads `data/grammar_drills/<lang>/`, writes `static/data/grammar/<lang>/`
- [ ] Sentence and reading validation is behind a per-language function; the zh behaviour and all 19 existing test cases are unchanged
- [ ] The item types, guide format, batch rules, blind-review commands and build output shape are shared and documented once
- [ ] The frontend store key and manifest URL are derived from the language, with existing `ld.grammar.zh.v1` data still read
- [ ] The Japanese work's owner confirms the shared contract covers particles, or the gaps are listed

**Technical Notes:**
The ja reading field needs kana or furigana rather than one pinyin syllable per character, so
`check_py` and the frontend's `rubyPairs` alignment are the main language-specific parts. Do not
start the Japanese content here; this task only removes the `zh` hard-wiring.

**Files to Create / Modify:**
- `scripts/grammar_drills.py` — `--lang`, per-language validators
- `data/grammar_drills/zh/SPEC.md` — split shared and zh-specific rules
- `static/js/grammar/store.js`, `templates/grammar_drill.html`, `web/pages.py` — language parameter
- `tests/test_grammar_drills_script.py` — a second-language fixture

**Verification:**
`python scripts/grammar_drills.py build --check --lang zh` reports up to date with byte-identical
output; the full test suites pass.

---

## TASK-1247: Decide whether grammar drills get audio

**Status:** [?] Awaiting owner decision
**Feature:** grammar-drills
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** none

**Description:**
No drill has audio; the tone-change topic in particular is answered by reading pinyin. **Question
for the owner:** is audio wanted, for which part (the correct sentence after an answer, or
listening items), and from what source: the browser's speech synthesis (no storage, quality
varies by device) or generated audio files (10,209 files to produce and store)?

**Acceptance Criteria:**
- [ ] The owner's answer is recorded in [[features/grammar-drills]] (GQ9)
- [ ] If yes: concrete tasks replace this one, naming the source and where files are stored

**Technical Notes:**
Generated sentences have no fixed text, so stored audio files cannot cover Endless mode.

**Files to Create / Modify:**
- `wiki/features/grammar-drills.md` — record the decision

**Verification:**
GQ9 is marked ANSWERED with the owner's words.

---

## TASK-1248: Decide the relation between the measure-words topic and the Measure Word Trainer

**Status:** [?] Awaiting owner decision
**Feature:** grammar-drills
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The `measure-words` topic (4 batches plus one generator) overlaps
[[features/measure-word-trainer]] (`/classifier-drill`), which is database-backed, has a curated
classifier dictionary and updates ELO. The two links sit next to each other on the profile page.
**Question for the owner:** keep both as they are, cross-link them, or fold one into the other?

**Acceptance Criteria:**
- [ ] The owner's answer is recorded in [[features/grammar-drills]] (GQ10) and in [[features/measure-word-trainer]]
- [ ] If the answer is to cross-link or merge: a concrete task replaces this one

**Technical Notes:**
The trainer never trains 个 and draws from `dim_classifiers`; the grammar topic's items are fixed
sentences with explanations. They share no code or data.

**Files to Create / Modify:**
- `wiki/features/grammar-drills.md`, `wiki/features/measure-word-trainer.md` — record the decision

**Verification:**
GQ10 is marked ANSWERED with the owner's words.

---
