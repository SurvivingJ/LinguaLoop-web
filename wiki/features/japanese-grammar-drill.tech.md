---
title: Grammar Drill and Reading Drill (Japanese) — Technical Specification
type: feature-tech
status: in-progress
prose_page: japanese-grammar-drill.md
last_updated: 2026-11-27
dependencies:
  - "everything in [[features/particle-drill.tech]] (markup, validator, runner, ladder, store, routes)"
  - "data/particle_drill/ja-grammar/ (catalog.json, items/, guides/, packs/, reading/katakana.json, review/, manifest.json)"
  - "data/particle_drill/AUTHORING_GRAMMAR.md"
  - "scripts/grammar_drill_catalog.py, scripts/grammar_drill_validate.py; PD_COURSE=ja-grammar for the shared scripts"
  - "static/js/particles/numbers.js; templates/grammar_drill.html, templates/reading_drill.html"
breaking_change_risk: low
---

# Grammar Drill and Reading Drill (Japanese) — Technical Specification

## Architecture Overview
A second *course* beside the particle course. Nothing was forked: the same markup, validator,
worker runner, content service, routes, page script, ladder and progress document serve both.

```
data/particle_drill/ja/           particle course (unchanged)
data/particle_drill/ja-grammar/   grammar course: catalog.json (182 skills, 48 groups, 12 stages),
                                  items/ (8,340), guides/ (48), packs/ (18), reading/katakana.json (609),
                                  review/ (187 records), manifest.json
PD_COURSE=ja-grammar              environment variable read by scripts/particle_drill_validate.py;
                                  particle_drill_swarm.py and particle_drill_build.py follow it
scripts/grammar_drill_catalog.py  source of the catalog (same row format, optional 8th field `ask`)
scripts/grammar_drill_validate.py the validator with PD_COURSE preset (what the workers run)
/grammar-drill                    templates/grammar_drill.html: the particle page script with data-course="grammar"
/reading-drill                    templates/reading_drill.html: the same script with data-home="read"
static/js/particles/numbers.js    rule engine: readNumber, numberReadings, counterReadings, hour/minute/month/day
                                  readings, CATS, generate(cat, rng, lists)
```

## Database Impact
None. No table is read or written beyond `user_drill_progress` (pending, [[features/particle-drill.tech]]).
Reading-drill progress is stored in the same document under `conj["read:<category>"]`.

## API / RPC Surface
### `GET /api/particle-drill/catalog?language_id=3&course=grammar`
### `GET /api/particle-drill/skill/<skill_id>?language_id=3&course=grammar`
- **Purpose:** as for the particle course; `course` is absent / `particles` or `grammar`.
- **Returns:** catalog rows now carry `conf` (the page picks interleaving companions from it)
  and, for kanji skills, `ask: "reading" | "kanji"`; the skill payload carries `ask` too.
- **Errors:** 400 for an unknown course; 404 for a skill of the other course.

### `GET /api/particle-drill/reading?language_id=3`
- **Purpose:** word lists of the reading drill.
- **Returns:** `{katakana: [{k, en, lv}]}` from `ja-grammar/reading/katakana.json`; cached by content version.
- **Auth:** login; Japanese only.

## Component Specification
### Item kinds (`ask`)
Set per skill in the catalog; the page copies it onto every item of the skill.
- **`reading`** (stage `yomi`): the slot is the word in kanji with its reading
  (`{今朝[けさ]|ym-n5-time}`); `d` is three wrong readings in hiragana. `exercises.build` sets
  `cue` (the kanji, drawn in the blank), `answer` / `accepted` / `typed` (the reading), `bare`
  (options drawn without ruby). Rungs: meet, choose, type, type, speed, speed.
- **`kanji`** (stage `nita`): the slot is the word with furigana; every distractor is the same
  word with a look-alike kanji or wrong okurigana **carrying the answer's reading**
  (`"d":["持[ま]って","特[ま]って","侍[ま]って"]`). `cue` is the reading, options are bare.
  Rungs: meet, choose, choose, choose, speed, speed.
- The validator enforces both (`check_item`): a kanji word in the focus slot; kana-only
  distractors for `reading`; kanji distractors with the answer's reading for `kanji`.

### Interleaving
`mastery.pickCompanions` treats the other skills of the focus skill's **group** as confusers
(in the particle course a group is one particle, so nothing changes there). A grammar skill
therefore has companions from its second round, before anything else is started.

### Reading drill (`numbers.js`)
- `generate(cat)` returns `{show, readings[], wrong[3], note}`; `readings[0]` is the standard
  reading, the rest are accepted variants. Categories: `num100`, `numbig`, `price`, `time`,
  `date`, `duration`, `age`, `kata` (`choiceOnly`: matched to its meaning).
- Sound changes are tables for 1 to 10 with the tens built in front (`counterReadings`): 分, 歳,
  か月, 週間, 年, 時, 月; days of the month are an explicit table.
- Wrong readings are built from wrong rules (no sound change; ふん for ぷん; よんがつ) and from the
  values next door, then filtered against the accepted readings.
- The page reuses the conjugation session (`kind: 'conj'`, `gen: 'read'`): three rungs, ids
  `read:<category>` in the `conj` map of the progress document.

## Key Architectural Decisions
1. **One more course directory, not one more feature.**
   - **Rationale:** eleven of the thirteen areas are "choose the right expression for this
     sentence", which is what the particle pipeline and ladder already do.
   - **Alternatives rejected:** a page and engine per area; putting the skills into the particle
     catalog (the hub would be 427 skills long and the two orders of study are independent).
2. **Numbers, times and dates are computed, not authored.**
   - **Rationale:** the readings are rules with a short list of exceptions; a hand-written table
     of about 100 cases checks the engine. Katakana cannot be computed, so it is a reviewed list.
3. **Keigo and transitive pairs are authored sentences, not conjugation rules.** お〜になる is not
   available for every verb and the special verbs replace it; a rule would produce wrong forms.
4. **Distractors of look-alike skills carry the answer's reading.** The learner sees the reading
   and chooses the writing; a different reading on a wrong option would give it away.
5. **Whole word in the slot when stems differ** (AUTHORING_GRAMMAR.md section 1), so every option
   is a well-formed word.

## Security Considerations
As [[features/particle-drill.tech]]: static content behind a login; the answer key is in the
browser, so nothing here may feed ELO.

## Testing Strategy
- `tests/test_grammar_drill.py` (pytest): the catalog equals what the source script builds; skill
  ids are disjoint from the particle course; the validator's two kanji kinds; the katakana list
  check; the course switch of the service and routes; `/reading`; and the shipped content:
  validates, manifest current, every skill at or over target with a guide, sets rotate their
  answers, every file named by a review record.
- `tests/unit/particle-drill-engine.test.js` (vitest): the two kanji kinds in `build` and
  `modeFor`; group companions; about 100 hand-written readings (numbers, hours, minutes, months,
  days, durations, ages, prices); 1,500 generated questions per category each with three wrong
  readings that are not accepted; generated times and dates against the tables.
- Walked in Chromium at 393×759: reading setup, 24 reading questions over all categories, the
  grammar hub, a reading skill, a look-alike skill, a pattern skill. No page errors.
