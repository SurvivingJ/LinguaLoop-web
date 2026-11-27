---
title: Chinese Grammar Drills — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./grammar-drills.md
last_updated: 2026-11-27
dependencies:
  - "data/grammar_drills/zh/ (SPEC.md, plan.json, guides/, batches/, blind/, reviewed/, verdicts/, review_concerns.md)"
  - "scripts/grammar_drills.py (local files only; no database, no network)"
  - "static/data/grammar/zh/ (manifest.json + one JSON per topic, built output)"
  - "static/js/grammar/*.js, static/js/grammar/generators/*.js, static/js/pages/grammar-drill.js"
  - "static/js/session/dom.js (escapeHtml, applyI18n, nowMs)"
  - "templates/grammar_drill.html, web/pages.py, templates/profile.html"
  - "static/css/redesign/grammar.css"
  - "static/i18n/{en,es,ja,zh}.json (82 `grammar_drill.*` keys each, plus `common.nav.grammar_drill` and `me.grammar_drill_sub`)"
  - "window.localStorage key `ld.grammar.zh.v1`"
breaking_change_risk: low
---

# Chinese Grammar Drills — Technical Specification

Verified against the code on branch `claude/happy-gates-qp9ifs` on 2026-11-27. Not deployed.
Prose page: [[features/grammar-drills]]. Decision record:
[[decisions/ADR-064-grammar-drills-static-content-local-progress]].

## Architecture Overview

```
data/grammar_drills/zh/            authoring (in the repo, not served)
  SPEC.md  plan.json  guides/*.json
  batches/<slug>-<NN>.jsonl   --strip-->  blind/<name>.blind.jsonl (+ .answers.jsonl from the reviewer)
  reviewed/<slug>-<NN>.jsonl  verdicts/<slug>-<NN>.json  review_concerns.md
        |
        |  python scripts/grammar_drills.py build      (validates, de-duplicates, compacts)
        v
static/data/grammar/zh/            served as static files
  manifest.json   <slug>.json  (39 topic files)
        |
        |  fetch (same-origin, no API)
        v
/grammar-drill  templates/grammar_drill.html  ->  static/js/pages/grammar-drill.js
  -> static/js/grammar/app.js (screens)
       data.js  store.js(localStorage)  ladder.js  select.js  round.js  check.js  text.js  render.js
       generators/index.js  (optional, dynamic import)
```

There is no server-side logic beyond serving the template and the static files. The page makes no
`/api/*` call. No table, RPC, migration or environment variable was added.

Sizes (verified): 39 topics in 7 categories, 105 batches planned and reviewed (10,521 reviewed
items), 10,209 items built after 312 repeated sentences were left out and 0 invalid lines; by type
cloze 5,471, order 1,616, rewrite 1,027, judge 2,095. Built output 40 files, 5.54 MB
(`manifest.json` 42,554 bytes; largest topic file `le.json` 351,562 bytes). `tone-sandhi` has a
guide and generators and 0 items.

## Database Impact

None. No table is read or written. See [[database/schema.tech]] for the unrelated
`dim_classifiers` tables used by [[features/measure-word-trainer.tech]], which this feature does
not touch.

## Data Contract (summary of `data/grammar_drills/zh/SPEC.md`)

The SPEC is the authority; this is a summary.

**Plan** (`plan.json`): `{ language: "zh", batch_size: 100, categories: [{key, title}] (7),
themes: [..] (20), topics: [{ slug, title, zh, cat, batches, mix: {cloze, order, rewrite, judge},
scope }] (39) }`. `batches` sums to 105.

**Sentence rules:** Simplified Chinese; 3 to 34 characters; no Latin letters or Arabic digits;
full-width punctuation; pinyin with tone marks, one syllable per character separated by spaces,
neutral tone unmarked, erhua 儿 written `r`. Levels: 1 = HSK 1–2, 2 = HSK 3, 3 = HSK 4.

**Item** (one JSON object per line). Common fields: `id` (`<topic>-<batch NN>-<item NNN>`),
`type`, `sub` (a key from the topic guide's `subs`), `lvl` (1–3), `zh`, `py`, `en`, `why`
(15 to 260 characters).

| type | extra fields | rule |
|------|--------------|------|
| `cloze` | `q` (one or two `___` blanks), `opts` (2–4 strings; two blanks as `first\|second`; `∅` = nothing), `a` (index) | `zh` equals `q` with option `a` filled in; exactly one option acceptable |
| `order` | `tokens` (3–10 tiles in the correct order, no punctuation), `alts` (other correct orders), `extra` (0–2 distractor tiles) | tiles joined equal `zh` without punctuation |
| `rewrite` | as `order`, plus `src`, `src_py`, `task` (5–80 characters) | `src` differs from the answer |
| `judge` | `s`, `ok`, `s_py` (when `ok` is false) | `ok: true` → `s == zh`; `ok: false` → `zh` is the corrected sentence |

**Batch:** 100 items (up to 110); type mix within 8 of the topic's `mix`; at least 25% level 1
and 10% level 3; no more than half the sub-points unused; 30–60% of judge items correct (checked
from 6 judge items); the correct cloze index may not sit at one position in over half the items
(checked from 20 cloze items); no duplicate id or content.

**Guide** (`guides/<slug>.json`): `{ topic, summary (60–420 chars), subs: [{key, label, focus}]
(3–10), rules: [{sub, rule, pattern, examples: [{zh, py, en}] (2–4), note?}] (3–12), contrasts:
[{wrong, right: {zh, py, en}, why}] (3–10), cheat: [..] (3–7) }`.

## Script: `scripts/grammar_drills.py`

787 lines. Run from the repository root. Every command works on local files only; nothing reads
or writes the database, so the `--apply` convention for writing scripts does not apply to it.
`LANG = 'zh'` is a module constant (see TASK-1246).

| Command | Effect | Exit code |
|---------|--------|-----------|
| `validate FILE.jsonl [...] [--min-items N]` | Checks each item and the batch rules above against the plan and the topic guide | 1 if any file has a problem |
| `validate-guide FILE.json [...]` | Checks a guide against the guide rules | 1 if any file has a problem |
| `strip FILE.jsonl` | Writes `blind/<name>.blind.jsonl`: the batch without answers (`cloze`: `q`, `opts`, `en`; `order`/`rewrite`: tiles in an md5-fixed order, `en`, and `src`/`task`; `judge`: `s` only) | 0 |
| `compare FILE.jsonl` | Compares the reviewer's `blind/<name>.answers.jsonl` with the keys and prints flags: `KEY REJECTED`, `AMBIGUOUS` (cloze, the solver's `ok` list), `DIFFERENT ORDER` (order/rewrite), `JUDGEMENT DIFFERS`, `no blind answer` | 0 (2 if there is no answers file) |
| `clean` | Mechanical fixes to every file in `reviewed/`, in place: stray punctuation, erhua `ér` → `r` (not in 儿子, 女儿 and similar), 都 `dū` → `dōu` (not in 首都, 成都), a missing full stop on order/rewrite sentences | 0 |
| `build [--check]` | Reads `reviewed/`, drops invalid lines and repeated sentences, writes `static/data/grammar/zh/`. `--check` writes nothing and exits 1 when the static files are out of date | 0 / 1 |
| `stats` | Per topic: planned batches, guide present, authored and reviewed files and item counts | 0 |

**De-duplication in `build`:** one sentence is drilled once, whatever the item type. The key is
`zh` with punctuation removed; for a judge item the shown sentence `s` is a key as well. An item
whose `zh`, shown sentence or `id` has already been seen is left out. Files are read in sorted
name order, so the earlier batch wins.

## Static File Shapes

`static/data/grammar/zh/manifest.json` (compact JSON):

```
{ "language": "zh",
  "categories": [{ "key", "title" }],
  "topics": [{ "slug", "title", "zh", "cat", "summary",
               "subs": [{ "key", "label" }],
               "count": <items in the topic file>,
               "types": { "cloze": n, "order": n, "rewrite": n, "judge": n },
               "v": "<first 10 hex of sha1 of the topic file body>" }],
  "total": 10209 }
```

`static/data/grammar/zh/<slug>.json`: `{ "topic": "<slug>", "guide": <guide object>, "items":
[<item>, ...] }`. Items are the reviewed items with empty fields removed. The manifest URL is
versioned by the template (`url_for('static', ...)`); each topic file is requested as
`<slug>.json?v=<v>` (`data.topicUrl`).

## API / RPC Surface

None. One page route was added to `web/pages.py`:
`('/grammar-drill', 'grammar_drill_page', 'grammar_drill.html')`. Like every entry in `PAGES` it
only renders its template. The application now has 117 URL rules (116 before). See
[[api/rpcs.tech]] for the API surface, which is unchanged.

## Component Specification

### Template `templates/grammar_drill.html`

Extends `base.html` in task mode (`task_mode = true`, `task_back = 'history'`, Back falls back to
the profile page). Emits an import map that joins `module_assets('js/session')` and
`module_assets('js/grammar')`, module-preloads the entry, and renders
`<div id="grammarRoot" lang="zh" data-manifest="..." data-generators="...">`. `data-generators`
is the URL of `js/grammar/generators/index.js` only when the file exists (the URL carries `?v=`);
otherwise it is empty and nothing is imported.

### Entry `static/js/pages/grammar-drill.js`

Calls `mountGrammar(root, { manifestUrl: root.dataset.manifest })` on DOM ready.

### Modules in `static/js/grammar/`

| Module | Lines | Role |
|--------|-------|------|
| `app.js` | 1,649 | `mountGrammar(root, opts) -> { destroy() }`. Screens: hub, topic (guide), drill, results. Routing by `location.hash`: `''` hub, `#<slug>` topic, `#<slug>/drill`, `#<slug>/endless`, `#mixed`. Sessions are not restored on reload. `opts.store`, `opts.rng`, `opts.generators`, `opts.manifest` can be injected by tests. |
| `data.js` | 72 | `loadManifest(url)`, `topicUrl(manifestUrl, topic)`, `loadTopic(manifestUrl, topic)` (each file fetched once, failures not cached), `loadGenerators(url)` (dynamic `import()`; a missing or failing module means no generators). |
| `store.js` | 203 | `createStore(storage, key, now)`: the only module that knows where progress lives. `KEY = 'ld.grammar.zh.v1'`. |
| `ladder.js` | 128 | Stage definitions, unlock, instant, level cap, speed countdown. No DOM. |
| `select.js` | 154 | `pickRound`, `pickMixed`, `mixedTopics`, `recommendTopic`, `itemClass`. No DOM; randomness passed in as `rng`. |
| `round.js` | 98 | `createRound(entries, { gap, more })`: the queue of one round, retry of missed items, summary. |
| `check.js` | 51 | `checkCloze`, `checkTyped`, `typedToOption`, `checkOrder`, `checkJudge`, `rightOption`, `correctSentence`. |
| `text.js` | 162 | Blanks, options, pinyin-to-character alignment (`rubyPairs`, `clozeSegments`, `tokenPinyin`, `readingMap`, `guessPinyin`), `median`, `seconds`. |
| `render.js` | 155 | HTML strings for sentences with `<ruby>` pinyin, cloze, options, tiles and the guide. `t(key)` reads `grammar_drill.<key>`. |

Pinyin is always in the markup as `<rt>`; the class `.gd.is-py` shows it (`grammar.css`).

### Ladder rules (`ladder.js`)

| Stage | Key | Item types | Focus | Flags |
|-------|-----|-----------|-------|-------|
| 1 | `recognise` | cloze, judge | — | — |
| 2 | `build` | cloze, judge, order, rewrite | order + rewrite, 50% of the round | — |
| 3 | `recall` | all four | cloze, 60% of the round | `recall` |
| 4 | `speed` | all four | — | `recall`, `timed` |

- `recall` (stages 3 and 4): a cloze item's options are hidden until the learner taps "Show
  choices" (`reveal()`), or, with the typed-answers setting, replaced by a text field checked by
  `checkTyped` (exact match with the right option; parts split on spaces, commas, `|` or `…`;
  the "nothing" chip stands for `∅`). Generated items show their options at once.
- **Recorded time:** for a recall cloze the time is the time to "Show choices" (`revealMs`); for
  everything else it is the whole answer time. Both are stored (`r` and `w` below). The clock and
  the countdown pause while the guide sheet is open over a drill.
- **Unlock:** `WINDOW = 30`, `UNLOCK_ACC = 0.85`. `unlocksNext(results)` is true when the last 30
  results at the stage number at least 30 and are at least 85% correct. Checked only when the
  answer is at the highest unlocked stage and that stage is below 4. Unlocking raises `u`; the
  current stage `s` changes only when the learner chooses a stage.
- **Instant:** `unlocked == 4` and the last 30 stage-4 results: `n >= 30`, accuracy `>= 0.9`
  (`INSTANT_ACC`), median of the recorded times `< 3000` ms (`INSTANT_MS`).
- **Level cap** (`levelCap`): judged on the highest stage with at least 10 results (else all
  results). Level 1 until 10 answers at 75%; level 2 until 30 answers in total at 80%; then 3.
- **Speed countdown** (rounds only, not Mixed review or Endless): base 8,000 ms
  (`SPEED_START_MS`), one 500 ms step tighter after every 5 right in a row (`SPEED_STREAK`), floor
  4,000 ms, one step looser after a miss (ceiling 8,000 ms); `+1,200` ms per tile for order and
  rewrite items (tokens plus extra). A timeout is submitted as a wrong answer with the limit as
  its time. After a right answer the page moves on by itself after 800 ms. The base is stored per
  topic (`sp`).

### Selection rules (`select.js`)

- `ROUND_SIZE = 20`, `MISSED_SHARE = 0.3`.
- Item class, lower first: 0 never seen; 1 missed last time (box 0); 2 seen and due; 3 seen and
  not due. Items above the level cap rank after every item within it (class + 4).
- Due: a Leitner box 1–5 per item; an item is due when the topic's answer count since it was last
  seen is at least `[15, 40, 100, 250, 600]` for boxes 1 to 5. A right answer moves the item up
  one box (maximum 5); a wrong answer sets box 0.
- `pickRound`: only the stage's types; first up to `ceil(20 × 0.3) = 6` class-1 items; then, when
  the stage has `focus` types, enough focus items to reach `focusShare` of the round; then the
  rest by class. Inside a class the sub-points take turns, each giving its least recently seen
  item. The result is shuffled.
- `recommendTopic`: the most recently practised topic that is not instant, else the first topic
  in manifest order with items that is not instant, else the first topic.
- `mixedTopics`: practised topics with items, most recent first, at most 5. `pickMixed` spreads 20
  items evenly over them, each drawn as that topic's round at its current stage.

### Round rules (`round.js`)

`RETRY_GAP = 3`: a missed item is re-inserted three items later and returns until answered right.
`summary()` scores first answers only (`answers`, `correct`, `accuracy`, `medianMs`, `missed`,
`best` streak). With `more` (Endless) the queue never runs dry.

### Sessions (`app.js`)

| Kind | Source of items | What is recorded |
|------|-----------------|------------------|
| `round` | `pickRound` at the topic's current stage | `store.record` with the stage: box, rolling results, possible unlock; speed base at stage 4 |
| `mixed` | `pickMixed` | `store.record` with `stage: null`: box only |
| `endless` | 50% static items (drawn 10 at a time with `pickRound`) when the topic has any, else a random generator of the topic (up to 5 tries) | `store.recordEndless` (answers, correct, best streak); static items also move their box; generated items are never stored |

Endless is offered only for a topic with at least one generator.

### Progress store (`store.js`)

One JSON value under `localStorage['ld.grammar.zh.v1']`:

```
{ v: 1,
  s: { py: 0|1, ty: 0|1 },              // settings: pinyin shown, typed answers
  t: { <slug>: {
    s: stage, u: highest unlocked stage,
    r: [[..],[..],[..],[..]],           // last 30 results per stage: +ms right, -ms wrong (recall time)
    w: [[..],[..],[..],[..]],           // the same answers' total times (ms)
    i: { <id without the slug prefix>: [box 0-5, seq when last seen] },
    q: answers recorded for the topic,
    l: epoch seconds of the last answer,
    sp: speed-stage base countdown (ms),
    e: [answers, correct, best streak]  // Endless totals
  } } }
```

Every storage call is guarded: a blocked or full `localStorage` means progress is not kept and
nothing throws. `dump()` returns the whole value "for a later server sync" (TASK-1239).

### Generators (`static/js/grammar/generators/`)

Interface (`index.js`): `generatorsFor(slug) -> [{ key, label, make(rng) }]` and
`GENERATOR_TOPICS` (slugs with at least one generator). `make(rng)` returns one item shaped like a
static item, with `id: "gen:<key>"` and an optional `cue` (a question shown instead of the English
meaning). `rng` returns a float in `[0, 1)` and defaults to `Math.random`; every random choice
goes through it, so a seeded `rng` reproduces a session. Items are built from curated word lists
with the `cloze` and `order` builders in `util.js`.

22 generators for 13 topics (verified by calling each one):

| Topic | Generators (key: item type) |
|-------|-----------------------------|
| `numbers-time` | `number-reading`: cloze, `clock-time`: cloze, `date-order`: order, `money`: cloze |
| `er-liang` | `er-liang`: cloze |
| `tone-sandhi` | `bu-tone`: cloze, `yi-tone`: cloze, `third-tones`: cloze |
| `measure-words` | `measure-words`: cloze |
| `de-three` | `de-three`: cloze |
| `bu-mei` | `bu-mei`: cloze |
| `potential-complement` | `potential-form`: cloze |
| `word-order` | `word-order`: order |
| `ba` | `ba-order`: order, `ba-or-bei`: cloze |
| `bei` | `bei-order`: order, `bei-or-ba`: cloze |
| `comparison` | `comparison-order`: order, `comparison-cloze`: cloze |
| `duration-frequency` | `duration-order`: order |
| `separable-verbs` | `separable-cloze`: cloze, `separable-order`: order |

### Entry point in the app

`templates/profile.html` has a link to `url_for('grammar_drill_page')` with
`class="ld-set lang-gate d-none" data-lang-gate="zh"`, directly below the Measure Words link. It
is the only link to the page.

## How the Content Was Produced

Claude subagents only; no OpenRouter and no Anthropic API key.

1. Contract, plan and validator first. A pilot on 了 and word order was authored and reviewed; its
   lessons went back into the prompts and the validator (ASCII punctuation rejected; suffix `r`
   rejected on 儿子 / 女儿).
2. One guide agent per topic (39 guides, each passing `validate-guide`).
3. Per 100-item batch: one author agent (Sonnet), then an independent reviewer agent (Sonnet) in
   a fresh context that (a) solves the stripped copy blind (`strip`), (b) compares its answers
   with the keys (`compare`), (c) reviews every item, fixes what fails and re-validates. The
   reviewer writes `reviewed/<slug>-<NN>.jsonl` and `verdicts/<slug>-<NN>.json`
   (`{ flagged, fixed, dropped, added, items: { <id>: { v, note } } }`). Summed over the 105
   verdict files: 145 flagged by the blind compare, 1,091 fixed, 3 dropped, 3 added.
4. Reviewer notes per batch are in `review_concerns.md` (65 KB), including judgement calls left in.
5. A separate agent reconciled 34 guides with those notes where a guide overclaimed against
   native usage.
6. Five top-up batches (了, result-complement, coverbs, final-particles, bu-mei) took the plan
   from 100 to 105 batches so that the total stays above 10,000 after de-duplication (9,725
   before the top-up, 10,209 after).

## Key Architectural Decisions

1. **Decision:** content as static JSON built from files in the repository; no database rows.
   - **Rationale:** the database was at 473.15 MB against the owner's 475 MB line (500 MB plan
     cap); the content is read-only and the same for every learner.
   - **Alternatives rejected:** tables for topics and items; exercise content files in Storage.
     See [[decisions/ADR-064-grammar-drills-static-content-local-progress]].
2. **Decision:** progress in `localStorage` behind one module (`store.js`).
   - **Rationale:** no table needed now; the store has one interface and a `dump()` so that a
     server sync can replace it without touching the engine.
   - **Alternatives rejected:** a per-user progress table now (needs a live migration and writes
     on every answer).
3. **Decision:** generators run in the browser.
   - **Rationale:** infinite practice with no API cost, no network and no stored rows.
   - **Alternatives rejected:** generating items with a hosted model at request time (cost,
     latency, and the owner ruled out OpenRouter and the Anthropic API for this feature).
4. **Decision:** one topic file per topic, versioned by content hash in the manifest.
   - **Rationale:** the hub needs only the 42 KB manifest; a topic's items load when it is opened
     and cache until the content changes.
   - **Alternatives rejected:** one 5.5 MB file.
5. **Decision:** sentence-level de-duplication at build time, not at authoring time.
   - **Rationale:** parallel author agents cannot see each other's batches; the build is the one
     place that sees all of them.

## Security Considerations

- Static content only; no new API route, no database access, no authentication change. The page
  route renders a template like every other entry in `web/pages.py`.
- Nothing the learner types leaves the browser; typed answers are compared locally.
- All content and interface text is inserted through `escapeHtml` (`static/js/session/dom.js`).
  The content files are trusted repository data, validated by the script before the build.
- The static files are public, like everything under `static/`. They hold no user data and no
  secrets; the answers are in the files by design.
- `localStorage` holds drill progress only (stages, timings, item boxes); no account data.

## Testing Strategy

- **Script:** `tests/test_grammar_drills_script.py` (9 test functions, 19 cases): the SPEC
  examples validate; two blanks and `∅`; cloze, order and judge defects are reported; pinyin
  rules; `compare` flags; plan sums; and `test_shipped_content_is_valid_and_built`, which fails
  when shipped content is invalid or the static files are out of date.
- **Frontend (vitest):** `tests/unit/grammar-text-check.test.js`, `grammar-ladder-store.test.js`,
  `grammar-select-round.test.js`, `grammar-app.test.js` (hub, topic guide, a full round with a
  retried miss, `∅` and number keys, pinyin on P, settings, Endless never storing generated
  items, Recall reveal and typed answers, the Speed countdown and its pause under the guide) and
  `grammar-generators.test.js`.
- **Gates on 2026-11-27** (all re-run by the wiki session at commit `fcf23e2`): full pytest 6,519
  passed, 16 skipped, 0 failed; `ruff check scripts/grammar_drills.py tests/test_grammar_drills_script.py`
  clean; `python scripts/grammar_drills.py build --check` reports the static files up to date;
  vitest 1,088 passed in 53 files; `npm run check` 0 errors and 2 warnings (both in files this
  feature does not touch: `static/js/pages/login.js`, `static/js/utils.js`); 117 URL rules.
- **Not tested:** correctness of the Chinese itself beyond the validator and the agent review
  (TASK-1241); the page in a real browser on a deployed host.

## Related Pages

- [[features/grammar-drills]] — prose page
- [[decisions/ADR-064-grammar-drills-static-content-local-progress]]
- [[tasklist/grammar-drills.tasks]]
- [[features/measure-word-trainer.tech]] — database-backed drill overlapping the `measure-words` topic
- [[pages/pages-overview]] — route table
- [[database/schema.tech]] — unchanged by this feature
- [[api/rpcs.tech]] — unchanged by this feature
