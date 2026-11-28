---
title: "Idiom Trainer (Chinese and Japanese) — Task Breakdown"
feature: idiom-trainer
prose_page: ../features/idiom-trainer.md
tech_page: ../features/idiom-trainer.tech.md
total_tasks: 4
done: 2
---

# Idiom Trainer (Chinese and Japanese) — Task Breakdown

Owner, 2026-11-28: "Chinese and Japanese need idiom trainers … We need to learn in context", then
"Do core first", "run on opus for authoring", "It would also be good to get the story behind
idioms if they exist".

---

## TASK-1287: Idiom trainer: contract, engine, pages, tracking

**Status:** [x] Done (2026-11-28; repo, not deployed)
**Feature:** idiom-trainer
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1282

**Description:**
The card and list formats and their validator, the build to static files, the per-idiom ladder,
the question builder, the store, the page for each language, and idioms as topics of the shared
tracking.

**Acceptance Criteria:**
- [x] `python scripts/idiom_trainer.py validate` rejects the 22 defective variants in the tests
- [x] `/idiom-trainer/zh` and `/idiom-trainer/ja` render; `/idiom-trainer` goes to the study language
- [x] five steps and reviews as specified (vitest); wrong options never share a theme or a listed look-alike
- [x] a round posted by the page is accepted by `validate_round` for both languages

**Technical Notes:**
[[features/idiom-trainer.tech]].

**Files to Create / Modify:**
- `data/idioms/AUTHORING.md`, `scripts/idiom_trainer.py`, `scripts/idiom_trainer_swarm.py`
- `static/js/idioms/*.js`, `static/js/pages/idiom-trainer.js`, `static/css/redesign/idioms.css`
- `templates/idiom_trainer*.html`, `web/pages.py`, nav templates, `static/i18n/*.json`
- `services/grammar_drill_tracking.py`

**Verification:**
`pytest tests/test_idiom_trainer.py -q` and `npx vitest run tests/unit/idiom-trainer.test.js`.

---

## TASK-1288: Author and review the core tier

**Status:** [x] Done (2026-11-28)
**Feature:** idiom-trainer
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1287

**Description:**
Six ranked lists and 652 cards (zh 320, ja 332), each with six contexts and two misuses, and a
story where one is certain.

**Acceptance Criteria:**
- [x] every listed idiom has a card; every file has a review record (test)
- [x] all lists and cards validate; static files match a build (tests)
- [x] every story names its source (test)

**Technical Notes:**
Run record: 72 jobs (6 lists, 66 card files), writer and reviewer both headless Claude Code
workers on Opus, signed in with the session login; none failed. List reviewers changed 33
entries and swapped 7; card reviewers recorded 255 fixes over 652 cards and kept all 99 stories
the writers had included (98 remain after de-duplication of the count by card). Notional cost
from the worker logs: about $120.

**Files to Create / Modify:**
- `data/idioms/zh/`, `data/idioms/ja/`, `static/data/idioms/`

**Verification:**
`python scripts/idiom_trainer.py stats` and `python scripts/idiom_trainer.py build --check`.

---

## TASK-1289: Native-speaker check of the lists, cards and stories

**Status:** [?] Awaiting owner
**Feature:** idiom-trainer
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1288

**Description:**
No human has seen this content. Idioms are where a model is most likely to choose something
dated, misjudge a register, or tell an origin slightly wrong. Check: the six lists (does each
entry belong in a core list), a sample of 100 cards, and all 98 stories against their sources.

**Acceptance Criteria:**
- [ ] lists pruned; findings in `wiki/evaluations/`
- [ ] every story confirmed, corrected or removed

**Technical Notes:**
`data/idioms/<lang>/review/*.json` lists what the reviewers changed.

**Files to Create / Modify:**
- `wiki/evaluations/idiom-trainer-check-<date>.md`

**Verification:**
The evaluation page exists and its fixes are merged.

---

## TASK-1290: The full tier

**Status:** [?] Awaiting owner decision
**Feature:** idiom-trainer
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1288

**Description:**
Grow the sets to the full tier proposed on 2026-11-28: Chinese about 850 (chengyu 600,
colloquial 150, sayings 100), Japanese about 770 (idioms 450, four-character 200, proverbs 120).
The owner asked for the core first, to judge the format.

**Acceptance Criteria:**
- [ ] owner decision after trying the core
- [ ] `SETS` sizes raised in `scripts/idiom_trainer.py`; the list jobs extend the lists; cards follow

**Technical Notes:**
The runner plans card jobs from the list length, so extending a reviewed list is enough; a
"tier" field in the list would let the page offer the core first.

**Files to Create / Modify:**
- `scripts/idiom_trainer.py`, `data/idioms/`

**Verification:**
`python scripts/idiom_trainer.py stats`.
