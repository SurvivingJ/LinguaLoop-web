---
title: Idiom Trainer (Chinese and Japanese) — Technical Specification
type: feature-tech
status: in-progress
prose_page: idiom-trainer.md
last_updated: 2026-11-28
dependencies:
  - "data/idioms/AUTHORING.md; data/idioms/<lang>/{lists,cards,review}/"
  - "scripts/idiom_trainer.py (validate, build, stats), scripts/idiom_trainer_swarm.py (workers)"
  - "static/data/idioms/<lang>/ (manifest.json + one file per set, built)"
  - "static/js/idioms/{ladder,questions,store}.js, static/js/pages/idiom-trainer.js, static/css/redesign/idioms.css"
  - "static/js/particles/markup.js (furigana markup), static/css/redesign/particles.css"
  - "templates/idiom_trainer{,_zh,_ja}.html, web/pages.py"
  - "services/grammar_drill_tracking.py (topics idiom-<id>), routes/grammar_drill.py"
  - "pypinyin (reading check of Chinese idioms), scripts/grammar_drills.py (check_py)"
breaking_change_risk: low
---

# Idiom Trainer (Chinese and Japanese) — Technical Specification

## Architecture Overview
```
data/idioms/<lang>/lists/<set>.json      ranked list: {id, t, r, mean, lvl, tag}
data/idioms/<lang>/cards/<set>-NN.json   ten cards per file, in list order
data/idioms/<lang>/review/<job>.json     what the reviewer changed
        |  python scripts/idiom_trainer.py build
        v
static/data/idioms/<lang>/manifest.json  {language, language_id, sets[{key,title,en,count,v}], total,
                                          idioms[{id,t,r,mean,lvl,tag,set,parts,story:bool}]}
static/data/idioms/<lang>/<set>.json     {set, cards[...]}
        |  fetch (static files, no API)
        v
/idiom-trainer/zh, /idiom-trainer/ja     templates/idiom_trainer_<lang>.html -> js/pages/idiom-trainer.js
   js/idioms/ladder.js     the ladder of one idiom, the round plan
   js/idioms/questions.js  one question for a card at a step
   js/idioms/store.js      localStorage + POST /api/grammar-drill/round, GET /progress
/idiom-trainer                           sends the browser to its study language's page
```
Sets: zh `chengyu` (code `cy`), `guanyong` (`gy`), `suyu` (`sy`); ja `kanyo` (`ky`), `yoji`
(`yj`), `kotowaza` (`kw`). Built totals: zh 320, ja 332; 3,912 contexts and 1,304 misuses.

## Database Impact
No table of its own. Progress uses the shared grammar-drill tracking (pending migration,
[[database/schema.tech]]): topic `idiom-<id>`, language 1 or 3, six stages. `state = {u, l,
s: {l, k, n, c, due, iv, last}}`.

## API / RPC Surface
No new route. `services/grammar_drill_tracking.py` accepts `idiom-<id>` for a language when `<id>`
is in that language's built manifest (`idiom_ids`, cached by file time); `IDIOM_STAGES = 6`;
`_idiom_state` validates the state. `Profile.state` now receives the topic so one language can
hold topics of different shapes.

## Component Specification
### Card (`cards/<set>-NN.json`)
`id, t, r, mean, lvl, tag` (copied from the list) and: `lit`; `story: null | {text, source}`;
`use: {reg: spoken|written|formal|neutral, tone: praise|criticism|humorous|neutral, how}`;
`near: [{t, diff}]` (0 to 2); `parts: [a, b]` (join to `t`); `cue`; `ctx: [{s, en}]` (exactly
6); `bad: [{s, en, why}]` (exactly 2). The idiom appears once in braces in every sentence.
Chinese sentences: simplified, full-width punctuation, 8 to 60 characters; chengyu and suyu
unchanged in the braces, a colloquial expression may be split (`{炒了他的鱿鱼}`). Japanese
sentences: the furigana markup of the particle drill, also inside the braces. Readings of
Chinese idioms are checked character by character against pypinyin.

### Ladder (`ladder.js`)
`record(state, correct, now)`: two right in a row → next step (`up`); step 5 passed → level 6,
due in 1 day (`mastered`); a right review lengthens the interval over `[1,3,7,14,30,60,120]`
days (`kept`); a wrong review → level 4 (`down`). `planRound(idioms, states, {size: 12, active:
5, sets})`: idioms in progress (oldest answer first) and new ones in list order up to `active`,
due reviews once each (at most half the round), then the in-progress idioms a second time in
rotated order. `modeFor(level)`: meet, recognise, complete, judge, recall, review.

### Questions (`questions.js`)
`build(card, mode, pool, rng, seen)`; `pool` is the manifest's idiom rows. Wrong options come
from `distractors`: same set first, never a listed look-alike, never the same `tag`, never the
same text; a small pool relaxes the tag rule. `complete` offers other idioms' second halves,
never one that would form another real idiom with this first half. `judge` is a good context
(from the third on) or a misuse, half each. `seen` holds the contexts this idiom was shown in
during the round, so the next one is new where one is left.

## Key Architectural Decisions
1. **A trainer of its own, not a stage of the grammar course.** The unit is one idiom with its
   card, and the questions are about meaning and situation, not about filling a slot.
2. **Stories are optional data with a named source, and the reviewer's first check.**
   - **Rationale:** the owner asked for "the story behind idioms if they exist … helpful for
     memory". A model will supply a plausible origin for anything; the contract therefore makes
     `null` the safe answer, and the reviewer cuts any story it cannot stand behind.
   - **Result:** 98 stories in 652 cards; reviewers kept 99, removed 0, added 0.
   - **Alternatives rejected:** a story for every idiom (invites invention); a separate
     "etymology" job (two passes disagreeing about facts).
3. **The list is written and reviewed before any card**, and is the authority for id, text,
   reading and meaning line, so two card jobs cannot disagree about an idiom.
4. **A theme tag on every idiom** keeps near-synonyms out of each other's options.
5. **Two right answers per step, not the particle ladder's rolling accuracy.** An idiom is one
   fact; ten right answers master it and reviews carry the rest.
6. **Static files and the shared tracking**, as the other drills
   ([[decisions/ADR-068-one-tracking-structure-for-every-language]]).

## Security Considerations
Static content behind the login page; the answer key is in the browser, so nothing here may
feed ELO. Tracking validation as for the other drills.

## Testing Strategy
- `tests/test_idiom_trainer.py` (pytest): good and bad list entries and cards (22 rejected
  variants), split colloquial expressions, Japanese furigana, paths and set sizes; shipped lists
  and cards validate; every listed idiom has a card and a review record; static files match a
  build; stories are sourced; the three pages; idioms as tracking topics of their own language.
- `tests/unit/idiom-trainer.test.js` (vitest): the ladder (promotion, mastery, review intervals,
  failed review), the round plan, every question kind, the distractor rules, fresh contexts, the
  store (one request per round, languages apart, queue while unavailable, merge and sync).
- Walked in Chromium at 393×759 for both languages: chooser redirect, hub, a new idiom's card,
  a round to its result screen, the set list, a card with a story. No page errors; the rounds the
  page posted were accepted by the server's validator.
