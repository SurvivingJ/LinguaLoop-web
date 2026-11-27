---
title: Particle Drill (Japanese) — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./particle-drill.md
last_updated: 2026-11-27
dependencies:
  - "data/particle_drill/ja/ (catalog.json, guides/, items/, packs/, conjugation/, review/, manifest.json)"
  - "services/particle_drill/ (markup.py, content.py, progress.py, conjugation.py)"
  - "user_vocabulary_knowledge, dim_word_senses, dim_vocabulary (read only, conjugation pool); fugashi + unidic-lite"
  - "routes/particle_drill.py (blueprint particle_drill, /api/particle-drill)"
  - "templates/conjugation_drill.html (/conjugation-drill)"
  - "templates/particle_drill.html, static/js/pages/particle-drill.js, static/js/particles/*.js, static/css/redesign/particles.css"
  - "scripts/particle_drill_catalog.py, particle_drill_validate.py, particle_drill_build.py, particle_drill_swarm.py, particle_drill_kanji.py"
  - "migrations/particle_drill_progress.sql (table user_drill_progress, NOT APPLIED)"
  - "Claude Code CLI (`claude -p`) for authoring only; nothing at request time"
breaking_change_risk: low
---

# Particle Drill (Japanese) — Technical Specification

## Architecture Overview

```
Authoring (offline, repeatable)
  scripts/particle_drill_catalog.py --apply      -> data/particle_drill/ja/catalog.json
  scripts/particle_drill_swarm.py plan --apply   -> data/particle_drill/_run/plan/<job>.json   (not committed)
  scripts/particle_drill_swarm.py run --apply    -> per job: `claude -p` author, then `claude -p` reviewer
        items/<skill>[__part].jsonl, guides/<group>.json, packs/<skill>.json,
        conjugation/{verbs_n5,verbs_n4,verbs_n3,adjectives,guide}.json, review/<job>.json
  scripts/particle_drill_kanji.py --apply        -> compound particles rewritten in kanji with furigana
  scripts/particle_drill_validate.py             -> deterministic checks (read-only)
  scripts/particle_drill_build.py --apply        -> manifest.json (counts + content version)

Serving (no database content, no model)
  GET /particle-drill                    templates/particle_drill.html (task-mode shell)
  GET /api/particle-drill/catalog        services/particle_drill/content.py: catalog + counts
  GET /api/particle-drill/skill/<id>     guide section + every item + packs of one skill
  GET /api/particle-drill/conjugation    conjugation guides + verb and adjective lists
  GET /api/particle-drill/conjugation/words   services/particle_drill/conjugation.py: the learner's
                                         known verbs and adjectives (user_vocabulary_knowledge), classified
  GET|PUT /api/particle-drill/progress   services/particle_drill/progress.py: user_drill_progress
  GET /conjugation-drill                 templates/conjugation_drill.html (same script, data-home="conj")

Browser (static/js/pages/particle-drill.js + static/js/particles/)
  markup.js     parse 漢字[かな]{answer|skill}<var>, render ruby
  kana.js       romaji -> hiragana, typed-answer matching (は = wa)
  exercises.js  Deck (bank + packs), build(item, mode), grading
  mastery.js    the ladder: record(), promotion / demotion / reviews, planMix(), mergeProgress()
  conjugate.js  verb and adjective conjugation, accepted answers, wrong options
  store.js      localStorage copy + debounced PUT to the server
```

A drill round makes no request: the skill's whole bank is fetched once (30 to 60 KB), exercises
are built and judged in the browser, and the ladder state is written to `localStorage` after
every answer and to the server at most every 4 seconds and at the end of a round.

Content totals (manifest, {{DATE}}): {{SKILLS}} skills in {{GROUPS}} groups, {{ITEMS}} items,
{{PACKS}} pattern packs, {{GUIDES}} group guides, {{VERBS}} verbs, {{ADJECTIVES}} adjectives,
21 conjugation guides. Version `{{VERSION}}`.

## Content Formats

Full authoring rules: `data/particle_drill/AUTHORING.md`. Summary:

**Markup** (shared by items, packs and guides; `services/particle_drill/markup.py`, twin
`static/js/particles/markup.js`, shared cases `tests/fixtures/particle_drill/markup_cases.json`):

```
私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に/へ|ni-time}起[お]きます。
```

- `漢字[かな]` furigana; every kanji run must carry a hiragana reading.
- `{answer|skill}` a particle slot. `/` separates accepted alternatives, the first is
  canonical. An answer is kana, or kanji with furigana (`{に対[たい]して|nitaishite}`); the
  parser returns the displayed text (`a`, `alt`), the marked text (`raw`) and the readings
  (`kana`).
- `<name>` a variable (pattern packs only).

**Catalog** (`catalog.json`, generated from `scripts/particle_drill_catalog.py`): `stages[] →
groups[] → skill ids` and `skills[]` with `id, group, stage, p, title, lv (JLPT 5..1), n
(target item count), conf (default confusions), packs (packs to author)`. The script's row
weights are scaled to exactly 10,000 items (multiples of 5, minimum 20 a skill).

**Item** (`items/<skill>.jsonl`, and part files `items/<skill>__<part>.jsonl`, one object per
line): `jp` (markup, one sentence, 6 to 70 characters, ends 。？！), `en`, `f` (index of the
focus slot), `d` (exactly 3 wrong answers for the focus slot; clinic files `x-…` 1 to 3), `why`
(15 to 200 characters), `lv` (1 to 5). The focus slot's skill equals the file's skill, except in
clinic files. Other slots carry their own skill id and alternatives and are used by Fill-all.
The served item gains `id` = first 10 hex of sha1(`jp`).

**Pattern pack** (`packs/<skill>.json`, array): `id, lv, tpl, en, f, d, why, vars`. `tpl` and
`en` contain `<name>`; `vars[name]` is a list of `[japanese, english]` pairs (at least 4 values;
at least 100 combinations; authors are asked for 6 to 12 values and 150 combinations). Values
may contain slots. The validator expands every value of every variable once and checks each
sentence as an item.

**Guide** (`guides/<group>.json`): `group, intro, skills[]`; each skill section has `id, rule,
explain, patterns[], examples[{jp,en}] (4+), contrast[{vs,note}], mistakes[{bad,good,note}],
tip`. `skills` lists exactly the group's skills in catalog order.

**Conjugation** (`conjugation/verbs*.json`, `adjectives*.json`): `{d, k, c, en, lv}` plus `t`
(`t`/`i`) for verbs; `c` is `godan | ichidan | suru | kuru` or `i | na`. `guide.json`: 21
topics `{id, title, rule, explain, table, examples, mistakes, tip}`; `conjugate.js` `FORMS[*].guide`
names the topic shown for each form.

**Review record** (`review/<job>.json`): `{batch, files[], checked, fixed, deleted, issues[]}`,
written by the reviewer of each authoring job. `tests/test_particle_drill.py` fails when a
content file is named by no review record.

## Database Impact

No content table. One optional table, **not applied**:

```sql
-- migrations/particle_drill_progress.sql
user_drill_progress (
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  drill text NOT NULL CHECK (drill ~ '^[a-z0-9_]{1,40}$'),     -- 'particles_ja'
  state jsonb NOT NULL DEFAULT '{}',                             -- CHECK pg_column_size(state) <= 300000
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, drill))
-- RLS enabled, no policy; REVOKE ALL from PUBLIC, anon, authenticated; service_role only.
```

One row per learner, a few KB. `services/particle_drill/progress.py` treats a missing table
(PostgREST `PGRST205` / `42P01`) as "not available": it answers `available: false`, remembers
that for 5 minutes, and the browser keeps using `localStorage` only. See [[database/schema.tech]].

## API / RPC Surface

All routes need a JWT (`middleware.auth.jwt_required`) and `language_id=3`; any other language
is 400 "The particle drill is Japanese-only".

### `GET /api/particle-drill/catalog?language_id=3`
- **Returns:** `{version, stages[], skills[{id, group, stage, p, title, lv, items, packs}]}`.
  `items` / `packs` are counts from `manifest.json` (counted from the files when it is absent).
- **Caching:** `ETag: "pd-<version>"`, `Cache-Control: private, max-age=3600`; `If-None-Match` → 304.

### `GET /api/particle-drill/skill/<skill_id>?language_id=3`
- **Returns:** `{skill{id,group,stage,p,title,lv,conf}, group{id,p,name,skills[]}, guide{…section, intro} | null, items[], packs[]}`.
- **Errors:** 404 unknown skill.
- **Caching:** as above, ETag `"pd-<version>-<skill>"`.

### `GET /api/particle-drill/conjugation?language_id=3`
- **Returns:** `{guide[], verbs[], adjectives[]}` (the `verbs*.json` / `adjectives*.json` parts merged, repeats dropped).

### `GET /api/particle-drill/conjugation/words?language_id=3`
- **Purpose:** the learner's own pool for the conjugation drill.
- **Returns:** `{words[{d, k, c, en, lv, known: true}], verbs, adjectives, skipped}`, most confidently known first.
- **Reads (service role, no write):** `user_vocabulary_knowledge` (the caller's rows, `language_id = 3`,
  `status IN ('known','probably_known','learning')`, up to 6,000) → `dim_word_senses` (`vocab_id`) →
  `dim_vocabulary` (`part_of_speech IN ('verb','adjective')`; `lemma`, `reading`, `part_of_speech_raw`,
  `level_tag`) → `dim_word_senses` again for a gloss in `users.native_language_id` (English when unset or Japanese).
- **Class of each word** (`conjugation.classify`): the reviewed word list when the word is in it;
  otherwise the UniDic conjugation type of the dictionary form through `fugashi` (五段 → `godan`,
  上一段 / 下一段 → `ichidan`, サ行変格 → `suru`, カ行変格 → `kuru`; `part_of_speech_raw` 形容詞 → `i`,
  形状詞 → `na`). Skipped (counted in `skipped`): the honorific ～ます verbs, 問う / 請う, single-kanji
  する verbs, ～ずる verbs, anything that is not one token (or noun + する), and any word whose
  lemma and reading fail the ending rules of the word-list validator.
- **Not cached:** the pool follows the learner's vocabulary on every load of the page.

### `GET /api/particle-drill/progress?language_id=3`
- **Returns:** `{available: bool, state: object|null, updated_at}`.

### `PUT /api/particle-drill/progress`
- **Body:** `{language_id: 3, state: {v, skills{}, conj{}, settings{}}}`.
- **Errors:** 400 when `state` is not an object, `skills` / `conj` are not objects, or the JSON is over 256 KB.
- **Returns:** `{available: bool, saved: bool}`. **Side effects:** upsert of the caller's row.

### Page
`/particle-drill` → `particle_drill_page` → `templates/particle_drill.html` (task mode, Back
pill with `task_back = 'history'`; the import map covers `static/js/particles`). Linked from the
wide-screen nav, the Practice chips and the Me page, each gated to Japanese (`lang-gate`).

## Component Specification (UI)

`static/js/pages/particle-drill.js` mounts into `#particleDrillRoot` and switches views on the
URL hash, so the Back pill and the browser's back button step drill → guide → ladder:

| Hash | View |
|------|------|
| `#/` | Hub: next skill, four counters, Daily mix, Conjugation gym, furigana switch, stages (`<details>`) → group cards → skill rows with level pips |
| `#/skill/<id>` | Guide of the skill; dock: exercise-type control (Auto, Choose, Type, Fill all, Fix, Speed) and Start |
| `#/drill/<id>` | Rounds of 10 over one skill |
| `#/mix` | Rounds of 20 over `planMix()` (up to 6 skills) |
| `/conjugation-drill` `#/`, `#/drill` | Conjugation setup (word pools first: "Words I know" + N5 / N4 / N3+, then forms and guides); rounds of 20. On `/particle-drill`, `#/conj` redirects here |

- **State:** `app.session` (decks, round counters, current question `q`), `app.store`
  (progress document), `app.bundles` (fetched skills, by id).
- **Question flow:** `nextQuestion → renderQuestion → ask<Mode> → settle → advance`. `settle`
  records the answer (`mastery.record`), saves, shows feedback; a right answer advances after
  750 ms (1.4 s at Meet, 1.3 s after a rung change), a wrong one waits for Continue / Enter and
  re-queues the item three questions later (and before the round ends). Re-asked items are not
  recorded again.
- **Keys:** 1–4 choose, 1–9 place a chip, Backspace removes the last chip, Enter checks or
  continues, Escape closes the guide sheet.
- **Typed input:** IME-safe (composition events and keyCode 229), romaji converted on input.
- **Speed:** `mastery.SPEED_LIMIT_MS` (6000) via `requestAnimationFrame`; timeout settles as wrong.
- **Styles:** `static/css/redesign/particles.css`, scoped to `.pd-host` / `.pd-sheet`, design
  tokens only. Loaded by this template only.
- **Strings:** `particle_drill.*` (78 keys), `common.nav.particle_drill`,
  `me.particle_drill_sub` in all four locale files. Guides and `why` lines are English content.

### Ladder (`static/js/particles/mastery.js`)

State per skill: `{l, la, e, n, c, rt, due, iv, last, miss[]}` = level, answers at this level,
accuracy EWMA (α 0.3), answers, correct, response-time EWMA (ms, right answers), review due
(ms epoch), review interval index, last answer, ids of missed bank items (newest first, 20 kept).

| Rule | Value |
|------|-------|
| Promote | answer right, `la ≥ 5`, `e ≥ 0.80` (Speed: `la ≥ 8`, `e ≥ 0.85` and `rt ≤ 4000` ms) → `l + 1`, `la = 0` |
| Demote | answer wrong, `la ≥ 4`, `e < 0.45`, `l > 1` → `l − 1`, `la = 0`, `e = 0.6` |
| Mastered | `l = 7`; `due = now + 1 day` |
| Review | at `l = 7`, 3 right answers once due → next of 1, 3, 7, 14, 30, 60, 120 days |
| Lapse | at `l = 7`, wrong and `e < 0.6` → `l = 5`, no due date |
| Not counted | answers in a manually chosen type (`counts: false`) or drawn at a level other than `l` |

`modeFor(level, item)` lowers the type to what the item supports (Fill all needs two slots).
The conjugation gym uses the same functions with `maxLevel = 3` (Choose, Type, Speed) and one
state per form id under `conj`.

## Key Architectural Decisions

1. **Content is files in the repository, not database rows** ([[decisions/ADR-064-particle-drill-static-content-client-engine]]).
   - **Rationale:** the database is at its size line (473 MB of a 475 MB working limit, [[tasklist/report-and-placement-apply-runbook]]); 10,000 items with guides are about 5 MB of JSON, read-only and versioned with the code.
   - **Alternatives rejected:** `dim_particle_*` tables with a session RPC like the measure-word drill (needs space and a live apply before anything works); static files under `static/` (no login check).
2. **Exercises are built and judged in the browser.**
   - **Rationale:** the goal is answer speed; a round trip per answer (about 270 ms p50 on this stack) would dominate a one-second answer. The key is not secret: the drill is practice, not a scored test.
   - **Alternatives rejected:** a server session RPC per round (the measure-word design) — kept open for a later ELO hook.
3. **One authored sentence, six exercise types.** Every particle of a sentence is marked, so the same item serves Meet, Choose, Type, Fill all, Fix and Speed; only the focus slot has authored wrong answers, so wrong options are never invented at run time.
4. **Pattern packs for unbounded practice** rather than a model call at request time. A pack is authored and reviewed once; the browser expands it. The validator exercises every value.
5. **Ladder rules mirror `update_classifier_mastery`** (5 answers at the level, EWMA 0.80) so the trainers behave alike, with two additions: a timed top rung and spaced reviews after mastery.
6. **Authoring by headless Claude Code workers** (`claude -p`), author and reviewer in separate contexts, no hosted model API (owner instruction 2026-11-27). The Workflow tool was tried first and stopped: on this 4-CPU container it runs two agents at a time.
7. **The conjugation drill reads the learner's vocabulary and stores no exercise rows.**
   - **Rationale:** the owner asked for "we know they know xyz verbs, so serve them infinite
     practice conjugating them", with a dedicated page and possibly the `exercises` table. Every
     form is a function of (dictionary form, reading, class), so a row per verb and form (about
     20,000 for the 1,131 Japanese verbs in `dim_vocabulary`) would add database size at the
     475 MB line and nothing the rule engine does not already produce; the engine is checked
     against a hand-written table instead. What the database does supply is the part only it
     knows: which verbs this learner knows.
   - **Alternatives rejected:** rows in `exercises` / `word_assets` per verb and form; a
     `dim_conjugation_class` table (the class is derived in milliseconds and cross-checked
     against the reviewed lists by a test).
8. **Progress is a client document with an optional server copy.** The page works before the migration is applied and offline; the merge rule is per skill, most answers wins.

## Security Considerations

- Every route requires a login; content routes are cacheable `private` only.
- `PUT /progress` stores caller-supplied JSON for the caller only (the user id comes from the
  token), capped at 256 KB by the route and 300 KB by a table constraint. The state is never
  executed or rendered as HTML.
- The table has RLS on, no policy, and no client-role grants (lint: `tests/test_migration_security_lint.py`).
- All content rendered into the page goes through `esc()`; the markup renderer emits only
  `<ruby>`, `<rt>` and the slot markup the page supplies.
- Authoring workers run with `--allowedTools Read,Write,Edit,Glob,Grep,Bash(python…)` and the
  API-key variables removed from their environment.

## Testing Strategy

- `tests/unit/particle-drill-engine.test.js` (vitest): markup (shared cases with Python),
  romaji and answer matching, every ladder rule, exercise building for the six types, pack
  expansion, the deck, and conjugation against a hand-written table of 303 forms
  (`tests/fixtures/particle_drill/conjugation_cases.json`: 14 verbs × 18 forms, exceptions,
  6 adjectives × 7 forms).
- `tests/test_particle_drill.py` also covers the conjugation pool: 21 classification cases
  (godan verbs in -iru / -eru, the left-out irregulars), a missing or katakana reading, the
  known-words query over an in-memory database, the route, and **agreement between the UniDic
  class and the reviewed word list for every listed verb**.
- `tests/test_particle_drill.py` (pytest, offline): markup, validator accept / reject cases,
  pack and lexicon checks, catalog = source script and sums to 10,000, **shipped content
  validates with 0 errors**, **manifest is current**, **every skill meets its item target and
  has a guide**, **every content file has a review record**, content service, progress store
  (including the missing-table path), all routes.
- Manual / browser: `tests/e2e/redesign/serve.py` serves the real app with a fake login; the
  page was walked in Chromium at 393×759 through every exercise type and a full round
  (see [[tasklist/particle-drill.tasks]] TASK-1236).

## Related Pages

- [[features/particle-drill]] — prose description
- [[decisions/ADR-064-particle-drill-static-content-client-engine]]
- [[tasklist/particle-drill.tasks]]
- [[features/measure-word-trainer.tech]] — sibling trainers and the mastery rule this ladder mirrors
- [[api/rpcs.tech]] — route table
- [[database/schema.tech]] — `user_drill_progress` (pending)
