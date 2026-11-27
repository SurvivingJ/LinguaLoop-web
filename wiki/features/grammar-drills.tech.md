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
  - "static/i18n/{en,es,ja,zh}.json (103 `grammar_drill.*` keys each, plus `common.nav.grammar_drill` and `me.grammar_drill_sub`)"
  - "window.localStorage keys `ld.grammar.zh.v1` (progress) and `ld.grammar.zh.sync.v1` (unsent rounds)"
  - "routes/grammar_drill.py, services/grammar_drill_tracking.py, services/day_boundary.py (`review_today`), web/rate_limits.py"
  - "migrations/grammar_drill_tracking.sql (PENDING): tables `grammar_drill_daily`, `grammar_drill_state`; function `record_grammar_drill_round`"
  - "window.authFetch (static/js/pages/base.js)"
open_questions:
  - "GQ11 (OPEN): a daily row measures about 246 bytes with its index against a budget of about 150; accept, or store sub-point misses more compactly?"
  - "GQ12 (OPEN): retention of `grammar_drill_daily` rows; the page reads 180 days and nothing deletes older rows."
breaking_change_risk: medium
---

# Chinese Grammar Drills — Technical Specification

Verified against the code on branch `claude/happy-gates-qp9ifs` on 2026-11-27. Not deployed.
Progress tracking (ADR-065) was added the same day in the working tree; its migration is not applied.
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

Content and answer checking involve no server-side logic beyond serving the template and the
static files. **Progress tracking (added 2026-11-27, ADR-065)** is the one server part: two API
routes, two tables and one function, described under "Progress tracking" below. The migration is
pending; until it is applied the routes answer 503 and the page works from `localStorage` alone.

```
finished round / Mixed review / Endless stop / session left part-way
  app.js  session.tally (sync.createTally)  --sendTally-->  sync.queueRound(mode, counts)
     -> localStorage['ld.grammar.zh.sync.v1']  (queue of { k: round key, m, at, t: [topic entries] })
     -> POST /api/grammar-drill/round  (window.authFetch)        routes/grammar_drill.py
          -> services/grammar_drill_tracking.validate_round / record_round
          -> RPC record_grammar_drill_round(user, language, round key, practice day, topics)
               -> grammar_drill_daily (+counts)   grammar_drill_state (merge, last_round_key)
page load
  sync.pull(): flush queue -> GET /api/grammar-drill/progress?language_id=1&days=180
     -> store.mergeRemote(slug, state) per topic; first upload of local-only topics (mode 'sync')
     -> trends.js (shaping) -> trendview.js (SVG) -> hub "Your progress", topic "Progress" card
```

Sizes (verified): 39 topics in 7 categories, 105 batches planned and reviewed (10,521 reviewed
items), 10,209 items built after 312 repeated sentences were left out and 0 invalid lines; by type
cloze 5,471, order 1,616, rewrite 1,027, judge 2,095. Built output 40 files, 5.54 MB
(`manifest.json` 42,554 bytes; largest topic file `le.json` 351,562 bytes). `tone-sandhi` has a
guide and generators and 0 items.

## Database Impact

Content: none. Tracking (ADR-065): two new tables and one new function, defined in
`migrations/grammar_drill_tracking.sql` (**pending, not applied**; rollback
`migrations/grammar_drill_tracking_rollback.sql`; apply entry `migrations/PENDING-2026-11-27.md`).
Full definitions: [[database/schema.tech]] "Grammar drill tracking". Nothing existing is changed.

| Object | Key | Written by | Read by |
|--------|-----|-----------|---------|
| `grammar_drill_daily` | PK `(user_id, language_id, topic, practice_day)` | `record_grammar_drill_round` only | `GET /api/grammar-drill/progress` (service role, filtered on the caller's id) |
| `grammar_drill_state` | PK `(user_id, language_id, topic)` | `record_grammar_drill_round` only | the same route |
| `record_grammar_drill_round(uuid, smallint, uuid, date, jsonb) RETURNS jsonb` | — | — | called by `POST /api/grammar-drill/round` |

No index beyond the two primary keys: every read is by `(user_id, language_id)` plus a
`practice_day` range, which the daily primary key's leading columns serve for the user filter.
Measured size: about 246 bytes per daily row with index, 665 to 1,250 per state row (see the
migration header and [[tasklist/grammar-drill-tracking-runbook]]). The database stop line is
480 MB (ADR-065).

The unrelated `dim_classifiers` tables used by [[features/measure-word-trainer.tech]] are not
touched.

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

Page route in `web/pages.py`: `('/grammar-drill', 'grammar_drill_page', 'grammar_drill.html')`;
like every entry in `PAGES` it only renders its template. Tracking adds blueprint `grammar_drill`
(`routes/grammar_drill.py`, registered in `app.py` at `/api/grammar-drill`) with two routes; the
application has 119 URL rules (117 before). Logic and validation are in
`services/grammar_drill_tracking.py`. Listed in [[api/rpcs.tech]] "Drills".

### `POST /api/grammar-drill/round`: `record_round(): { recorded, replayed, practice_day }`
- **Purpose:** record the first-answer totals of one finished session and the learner's current
  state per topic, once per `round_key`.
- **Arguments (JSON body):**
  - `language_id` — integer, must be 1 (Chinese, `services.drill_service.ZH_LANGUAGE_ID`).
  - `round_key` — UUID string generated by the browser; stored lower-case.
  - `mode` — `'round' | 'mixed' | 'endless' | 'sync'`. `sync` is the one-time upload of progress
    that existed before tracking: every topic must have `answers = 0` and a `state`. The other
    modes need `answers >= 1` per topic. The mode is validated and not stored.
  - `played_at` — optional integer, epoch seconds when the session was queued. Used for the
    practice day when it is not in the future (5 minutes of clock skew allowed) and at most 7
    days old; otherwise the request time is used.
  - `topics` — list of 1 to 10 objects, each topic at most once, no unknown fields:
    `topic` (a slug in `static/data/grammar/zh/manifest.json`, loaded and cached server-side,
    re-read when the file's mtime changes); `answers` (integer 0–500); `correct`
    (0–`answers`); `timed` (0–`answers`; the browser sends the right first answers);
    `ms_sum` (0–`timed` × 30000); `stage` (1–4, the highest unlocked stage); `instant`
    (boolean, only with `stage` 4); `sub_misses` (object: sub-point key of that topic → integer
    1–`answers`, sum at most `answers − correct`); `state` (null or exactly
    `{ u: 1–4, r: [4 strings], q: 0–10,000,000, e: [answers, correct, best], l: epoch seconds }`
    where each `r` string matches `^(-?[1-9]\d{0,5}(,-?[1-9]\d{0,5}){0,29})?$` and the JSON
    text is at most 1,500 characters).
  - Booleans are not accepted as integers. Any other top-level field (for example `user_id`) is
    ignored; the user is always the token's.
- **Returns:** `200 { status: "success", recorded: n, replayed: n, practice_day: "YYYY-MM-DD" }`.
  `recorded` topics were written; `replayed` topics already carried this `round_key`.
- **Errors:** `400 BAD_REQUEST` with a one-line reason for any validation failure (nothing is
  written); `401` without a valid token; `429` over the rate limit; `503
  GRAMMAR_TRACKING_UNAVAILABLE` when the function or tables are missing (PostgREST `PGRST202` /
  `PGRST205`, Postgres `42883` / `42P01`): logged as a warning naming the migration, and
  remembered for 600 s per process so later requests do not pay a failing round trip; `500` for
  any other database error (message not exposed).
- **Auth:** `@jwt_required`; any signed-in user, own data only.
- **Rate limit:** `30 per minute; 600 per hour` per user (`web/rate_limits.py`).
- **Side effects:** one RPC `record_grammar_drill_round(p_user_id, p_language_id, p_round_key,
  p_practice_day, p_topics)`. The practice day is `services.day_boundary.review_today` (zone
  Australia/Sydney), computed in Python.

### `GET /api/grammar-drill/progress?language_id=1&days=180`: `get_progress(): { today, days, states, daily }`
- **Purpose:** the caller's own state per topic and daily summaries.
- **Arguments:** `language_id` (required, must be 1); `days` (optional, default 180, values
  above 365 are cut to 365, below 1 is a 400).
- **Returns:** `200 { status: "success", today: "YYYY-MM-DD" (the review day), days,
  states: { <topic>: <state> }, daily: [{ topic, day, answers, correct, timed, ms_sum, stage,
  instant, sub_misses }] }`, `daily` ordered by day then topic, days from `today − (days − 1)`.
- **Errors:** `400` (language, days), `401`, `429`, `503 GRAMMAR_TRACKING_UNAVAILABLE`, `500`
  as above.
- **Auth:** `@jwt_required`; rows are selected with `user_id = <token user>` by the service
  role. A `user_id` query parameter is ignored.
- **Rate limit:** `30 per minute` per user.
- **Side effects:** none. Reads `grammar_drill_state` once and `grammar_drill_daily` through
  `services.pagination.fetch_all` (pages of 1,000).

### `record_grammar_drill_round(p_user_id uuid, p_language_id smallint, p_round_key uuid, p_practice_day date, p_topics jsonb): jsonb`
- **Purpose:** the one writer of both tables; one transaction per round.
- **Arguments:** as named; `p_topics` is the validated `topics` list (1 to 10 entries).
- **Returns:** `{ success: true, recorded, replayed }`, or `{ success: false, error:
  'bad_arguments' }` for a NULL argument or a `p_topics` that is not an array of 1 to 10.
- **Errors:** raises `22023` for a topic entry whose counts are out of range (the route rejects
  those first); table CHECK violations.
- **Auth:** SECURITY DEFINER, `search_path = public, pg_temp`, EXECUTE for `service_role` only.
  Trusts `p_user_id`.
- **Side effects, per topic in slug order:** insert-or-lock the state row; if its
  `last_round_key` equals `p_round_key`, skip the topic (replay); else, when `answers > 0`,
  upsert the daily row (add `answers`, `correct`, `timed`, `ms_sum`; `stage = GREATEST`;
  `instant` = the new value; `sub_misses` merged by adding per key; no change once the day would
  pass 50,000 answers); then set the state to the side whose `l` is later (the old state when
  the entry has no state), with `u = GREATEST(old u, new u, stage)`, and store `p_round_key`.
- **Known limit:** one key per state row. A resend that arrives after another device has
  written the same topic in between is counted twice (ADR-065).

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
| `app.js` | 1,733 | `mountGrammar(root, opts) -> { destroy() }`. Screens: hub, topic (guide), drill, results. Routing by `location.hash`: `''` hub, `#<slug>` topic, `#<slug>/drill`, `#<slug>/endless`, `#mixed`. Sessions are not restored on reload. `opts.store`, `opts.rng`, `opts.generators`, `opts.manifest`, `opts.sync` (a sync object, or `false` for none) and `opts.syncStorage` can be injected by tests. Keeps a tally per session and hands it to `sync.queueRound`; fills `[data-gd-progress]` on the hub and topic screen (`fillProgress`). |
| `data.js` | 72 | `loadManifest(url)`, `topicUrl(manifestUrl, topic)`, `loadTopic(manifestUrl, topic)` (each file fetched once, failures not cached), `loadGenerators(url)` (dynamic `import()`; a missing or failing module means no generators). |
| `store.js` | 273 | `createStore(storage, key, now)`: the only module that knows where progress lives. `KEY = 'ld.grammar.zh.v1'`. `syncState(slug)` and `mergeRemote(slug, state)` are the server copy's two ends; `encodeResults` / `decodeResults`. |
| `ladder.js` | 128 | Stage definitions, unlock, instant, level cap, speed countdown. No DOM. |
| `select.js` | 154 | `pickRound`, `pickMixed`, `mixedTopics`, `recommendTopic`, `itemClass`. No DOM; randomness passed in as `rng`. |
| `round.js` | 98 | `createRound(entries, { gap, more })`: the queue of one round, retry of missed items, summary. |
| `check.js` | 51 | `checkCloze`, `checkTyped`, `typedToOption`, `checkOrder`, `checkJudge`, `rightOption`, `correctSentence`. |
| `text.js` | 162 | Blanks, options, pinyin-to-character alignment (`rubyPairs`, `clozeSegments`, `tokenPinyin`, `readingMap`, `guessPinyin`), `median`, `seconds`. |
| `render.js` | 155 | HTML strings for sentences with `<ruby>` pinyin, cloze, options, tiles and the guide. `t(key)` reads `grammar_drill.<key>`. |
| `sync.js` | 262 | `createSync({ store, storage, request, languageId, now, instant, known })`: the unsent-round queue (`QUEUE_KEY = 'ld.grammar.zh.sync.v1'`, at most 60 jobs, 10 topics per job), `queueRound`, `flush`, `pull`, `progress`, `pending`; `createTally()`: first-answer counts per topic. No DOM. |
| `trends.js` | 205 | Pure shaping of the daily rows: `topicSeries`, `trendOf`, `needsWork`, `hubSummary`, `linePoints`, `applyRound`, `dayDiff`, `addDays`. No DOM, no network. |
| `trendview.js` | 250 | HTML strings with inline SVG: `topicProgressHtml(progress, slug, subs)`, `hubProgressHtml(progress, instantCount)`, `dayLabel`. |

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
nothing throws. `dump()` returns the whole value.

### Progress tracking (ADR-065; client side)

**What is sent.** `app.js` `record()` adds every FIRST answer to `session.tally`
(`sync.createTally`): per topic `answers`, `correct`, `timed` and `ms_sum` (right first answers
only, each time capped at 30,000 ms; the time is the recall time the store records), and
`sub_misses[item.sub]` for a miss whose `sub` is one of the topic's `subs` in the manifest
(generated items and unknown subs count as a miss without a sub-point). `sendTally()` runs in
`finish()` (round end, Mixed review end, Endless "Stop"), in `endSession()` (a session left
part-way, `destroy()`), and whenever one topic's tally reaches 200 answers (`TALLY_FLUSH`, so an
Endless sitting never exceeds the route's 500). It calls `sync.queueRound(session.kind, counts)`.

**Queue.** `queueRound` drops topics with no answers or unknown to the manifest, adds per topic
`stage` (`u`), `instant` (`ladder.isInstant`) and `state` (`store.syncState`), stores the job
`{ k: crypto.randomUUID(), m: mode, at: epoch seconds, t: [entries] }` under
`localStorage['ld.grammar.zh.sync.v1']` and calls `flush()`. `flush()` sends jobs oldest first,
one at a time: `2xx` removes the job (and adds it to the cached progress with `applyRound`);
`400` removes it (it can never be accepted); anything else (offline, `401`, `429`, `5xx`, `503`
not deployed) stops sending for the rest of the visit and keeps the job. The queue holds at most
60 jobs (`MAX_QUEUE`); the oldest are dropped beyond that.

**Request helper.** `window.authFetch` (the app's API helper, `static/js/pages/base.js`). No
call is made without a `jwt_token` in `localStorage`, so a signed-out visitor is never sent to
`/login` by this feature.

**Load.** `boot()` calls `sync.pull()` after the first screen is drawn: `flush()`, then
`GET /progress`; each returned state goes through `store.mergeRemote`; then every locally
practised topic the server has no state for, and that is not already queued, is queued once as a
`sync` job (`answers = 0`, state only: no daily history is invented). If the merge changed the
store the screen is redrawn, otherwise only the progress slot is filled.

**Merge (`store.mergeRemote`).** `u = max(local, remote)`; `q` and each of `e` = max; when the
remote `l` (last answer, epoch seconds) is later than the local one, the four result lists `r`
are replaced by the remote ones (and `w` by their absolute values) and `l` is taken; a topic the
browser has never drilled starts at stage `u`. `i` (item boxes), `s` (chosen stage, otherwise)
and `sp` are local only.

**State sent (`store.syncState`).** `{ u, r: [4 strings], q, e: [answers, correct, best], l }`;
each `r` string is the stage's last 30 results as comma-separated signed ms (`'1200,-800'`).

**Views (`trends.js`, `trendview.js`).** Drawn only when `sync.progress()` is non-null.
- Topic "Progress" card (`topicProgressHtml`): `topicSeries` = the topic's last 30 practised
  days; two charts, never one chart with two axes: accuracy (scale 50–100%, lower if a day fell
  below 50) and average recall time (scale from 0), each a 2 px line in `--brand` with a dot on
  the latest day, the latest value in text, and `trendOf`'s change in words: latest day minus the
  first week (the seven days from the first practised day, weighted by answers), or minus the
  first day while the latest day is inside that week; no change text for one day. "Needs work":
  `needsWork`, the three sub-points with the most misses in the 14 days ending `today`.
  Each SVG has `role="img"` and an `aria-label` naming the range; each point has a `<title>`.
- Hub "Your progress" (`hubProgressHtml`): `hubSummary` = practised days among the last 30,
  all answers in the returned history, and a 30-cell strip in one hue (four opacity levels
  relative to the busiest day); the instant count comes from the store. Not drawn when the
  history has no answers.
- CSS: `.gd-trend*` in `static/css/redesign/grammar.css`, existing tokens only (`--brand`,
  `--line`, `--surface`, `--ink`, `--ink-2`, `--brand-wash`).

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
2. **Decision:** progress in `localStorage` behind one module (`store.js`) as the working copy,
   copied to the server as daily summaries plus one state row per topic
   ([[decisions/ADR-065-grammar-drill-daily-tracking]], which supersedes the
   `localStorage`-only choice of ADR-064).
   - **Rationale:** the owner wants improvement over time and chose daily rows with the stop
     line raised to 480 MB; one write per finished session keeps the drill free of server
     latency and working offline.
   - **Alternatives rejected:** a row per answer or per round (space); one JSON value per user
     (no history); item boxes on the server (space).
6. **Decision:** at-least-once sending from a `localStorage` queue with a browser-made round
   key, and one remembered key per state row on the server.
   - **Rationale:** no extra table for seen keys; a browser resends in order, so the last key is
     the one a retry carries.
   - **Alternatives rejected:** a table of round keys (space); no idempotency (double counts on
     every lost response).
7. **Decision:** the practice day is computed in Python (`review_today`) and passed to SQL.
   - **Rationale:** `public.review_today()` is in a pending migration; this file must not depend
     on it. A queued round keeps its own day through `played_at` (at most 7 days back).
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

- Content is static; the page route renders a template like every other entry in
  `web/pages.py`. Typed answers are compared locally and never leave the browser.
- **Tracking routes:** both need a valid token (`@jwt_required`) and act only on the token's
  user id; no request field can name another user. The body is validated field by field before
  any write (types, ranges, topic and sub-point keys against the manifest, state shape and size);
  unknown fields in a topic entry are rejected. Rate limited per user.
- **Tables:** RLS enabled; one SELECT policy each (own rows, role `authenticated`); no table
  privilege for `PUBLIC`, `anon` or `authenticated`, so the policy is inert and only the service
  role reads or writes. **Function:** SECURITY DEFINER with pinned `search_path`, EXECUTE revoked
  from `PUBLIC`, `anon`, `authenticated`, granted to `service_role`. The migration passes
  `tests/test_migration_security_lint.py`.
- **The counts are self-reported.** The server cannot verify that answers were given; a signed-in
  user can only distort their own summaries. Bounds: 500 answers per topic per call, 10 topics
  per call, 30 calls a minute, 50,000 answers per topic and day, state at most 1,500 characters
  (CHECK: 4,096 stored bytes).
- **Data kept:** counts, times and sub-point keys per day; no text the learner typed, no item
  ids. Rows are deleted with the user (`ON DELETE CASCADE` on `users.id`).
- The 503 path exposes only a fixed message; database error text is never returned.
- All content and interface text is inserted through `escapeHtml` (`static/js/session/dom.js`).
  The content files are trusted repository data, validated by the script before the build.
- The static files are public, like everything under `static/`. They hold no user data and no
  secrets; the answers are in the files by design.
- `localStorage` holds drill progress (stages, timings, item boxes) and the unsent-round queue
  (the same counts and state); no account data.

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
- **Tracking routes (pytest):** `tests/test_grammar_drill_tracking_routes.py` (15 tests) over an
  in-memory stand-in for the two tables and the function: happy path and read-back, replay of a
  round key, `sync` upload without a daily row, state merge rules, `played_at`, 40 invalid
  bodies rejected before any write, 401, isolation from another user's rows, the days window,
  missing tables / function (503, logged, remembered), other database errors (500), rate-limit
  and URL-rule registration, and the migration's parameter names.
- **Tracking SQL:** `tests/test_migration_security_lint.py` passes with the new files. The
  migration was applied to a scratch PostgreSQL 16 (stub `users`, `dim_languages`, roles): record,
  replay, second round on the same day, `sync` entry, grants, and the size measurement. Not run
  against Supabase.
- **Tracking frontend (vitest):** `tests/unit/grammar-sync-trends.test.js` (25 tests: state
  encode / merge, tally, queue, resend with the same key, 400 dropped, 503 kept, queue cap,
  broken storage, pull and merge, first upload, trend shaping) and 7 new cases in
  `grammar-app.test.js` (what a round, a part-played round and an Endless stop hand over; no view
  without history; hub and topic views; one-day and empty states; redraw after a merge).
- **Browser (Playwright, Chromium, local preview server, both API routes stubbed), 2026-11-27:**
  a 20-item round at 393×759 sent one POST with the expected body; the views rendered from a
  stubbed 27-day history at 393×759 and 1280×800 with no horizontal scroll; with both routes
  answering 503 the page worked, showed no message, kept the round queued and sent it with the
  same key on the next load.
- **Gates after tracking, 2026-11-27 (uncommitted working tree):** full pytest 6,534 passed, 16
  skipped, 0 failed; `ruff check` clean on the touched Python files; vitest 1,120 passed in 54
  files; `npm run check` 0 errors and the same 2 warnings.
- **Gates on 2026-11-27 before tracking** (all re-run by the wiki session at commit `fcf23e2`): full pytest 6,519
  passed, 16 skipped, 0 failed; `ruff check scripts/grammar_drills.py tests/test_grammar_drills_script.py`
  clean; `python scripts/grammar_drills.py build --check` reports the static files up to date;
  vitest 1,088 passed in 53 files; `npm run check` 0 errors and 2 warnings (both in files this
  feature does not touch: `static/js/pages/login.js`, `static/js/utils.js`); 117 URL rules.
- **Not tested:** correctness of the Chinese itself beyond the validator and the agent review
  (TASK-1241); the page on a deployed host; the migration and the two routes against the live
  Supabase project (PostgREST error codes for the missing-object path are taken from the other
  services' handling, not observed for these objects).

## Related Pages

- [[features/grammar-drills]] — prose page
- [[decisions/ADR-064-grammar-drills-static-content-local-progress]]
- [[decisions/ADR-065-grammar-drill-daily-tracking]] — tracking; the 480 MB line
- [[tasklist/grammar-drill-tracking-runbook]] — apply steps, owner queries
- [[tasklist/grammar-drills.tasks]]
- [[features/measure-word-trainer.tech]] — database-backed drill overlapping the `measure-words` topic
- [[pages/pages-overview]] — route table
- [[database/schema.tech]] — "Grammar drill tracking" (two tables, one function; pending)
- [[api/rpcs.tech]] — "Drills" (the two tracking routes)
