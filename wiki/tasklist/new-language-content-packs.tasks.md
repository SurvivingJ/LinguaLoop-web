---
title: "New-Language Content Packs — Task Breakdown"
feature: new-language-content-packs
prose_page: ../features/new-language-content-packs.md
tech_page: ../features/new-language-content-packs.tech.md
total_tasks: 6
done: 0
last_updated: 2026-11-28
---

# New-Language Content Packs — Task Breakdown

The skill, the tool and the Italian pilot were built on 2026-11-28 ([[evaluations/italian-pack-pilot-2026-11-28]]). The engineering work to make Italian live is listed, without task ids, in `data/language_packs/it/wiring/tasks.md` (34 entries); ids are assigned when the owner accepts the profile (TASK-1269).

---

## TASK-1269: Owner decisions on the Italian profile

**Status:** [?] Awaiting the owner (NQ1, NQ4)
**Feature:** new-language-content-packs
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The profile proposes six new exercise types, five lookup dictionaries and several teaching rules. Each one costs engineering work and decides what the content team writes next, so the owner accepts, changes or rejects them before any larger run.

**Acceptance Criteria:**
- [ ] Each item under "Decisions for the owner" in the evaluation page is marked accepted, changed or rejected
- [ ] `data/language_packs/it/profile.json` is updated to match and `validate-profile it` passes
- [ ] NQ1 and NQ4 are marked ANSWERED in the feature page

**Technical Notes:**
A changed dictionary field spec means every file of that dictionary is re-validated.

**Files to Create / Modify:**
- `data/language_packs/it/profile.json` — the accepted decisions
- `wiki/features/new-language-content-packs.md` — open questions

**Verification:**
`python scripts/language_pack.py validate-profile it` prints OK; `status it` shows no profile problems.

---

## TASK-1270: Native-speaker check of the Italian pilot

**Status:** [?] Awaiting the owner (NQ2: who)
**Feature:** new-language-content-packs
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
All Italian content was written and reviewed by AI agents. A native speaker reads a fixed sample and marks each item right, wrong or unnatural, which gives the first real error rate and tells us which reviewer changes were themselves wrong.

**Acceptance Criteria:**
- [ ] The 151 built drill items, the 49 collocation rows, the 57 government rows and the 6 exercise documents are each marked
- [ ] Error rate per content type is added to the evaluation page
- [ ] Every error class found is added to the matching brief in `.claude/skills/new-language-swarm/briefs/`

**Technical Notes:**
Collocations and exercise documents had the highest reviewer change rates; start there.

**Files to Create / Modify:**
- `data/language_packs/it/reports/native_check.md` — the marks
- `wiki/evaluations/italian-pack-pilot-2026-11-28.md` — the rates

**Verification:**
The evaluation page states a native-checked error rate for each of the four content types.

---

## TASK-1271: Second Italian pilot with the amended briefs

**Status:** [ ] Not Started
**Feature:** new-language-content-packs
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1269

**Description:**
The briefs for senses, the judgement dictionaries, drills and exercise documents were amended after the first run and not re-tested. Run the swarm again on new material at pilot size and compare reviewer change rates with the first run before any scale-up.

**Acceptance Criteria:**
- [ ] A run with `skip: ["profile", "wiring"]` on the next lexicon rows, three further grammar topics and a second file of each dictionary completes with every file passing the tool
- [ ] Reviewer change rates per stage are tabled beside the first run's
- [ ] A 100-sense fat-seed slice of content words is judged, and the cheat sheet trimmed where defects do not cluster

**Technical Notes:**
Pass `dictionaries` and `topics` in the workflow arguments when the profile and plan stages are skipped. The dictionary briefs write file `_01`; give the second run file numbers in the task text or extend the script.

**Files to Create / Modify:**
- `data/language_packs/it/**` — new batches
- `.claude/skills/new-language-swarm/workflow.js` — a `fileNumber` argument for dictionaries and lexicon chunks
- `wiki/evaluations/` — a second evaluation page

**Verification:**
`python scripts/language_pack.py status it` shows the added counts; the evaluation page shows both runs' rates.

---

## TASK-1272: Scale the Italian pack to the profile's targets

**Status:** [?] Blocked on TASK-1270 and TASK-1271, and on NQ3 (where the content is stored)
**Feature:** new-language-content-packs
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1270, TASK-1271

**Description:**
Build the full pack: about 5,000 lemmas and senses, the five dictionaries at target size, 37 guides and 90 drill batches. Run in workflows of a few dozen batches so each result is sampled before the next.

**Acceptance Criteria:**
- [ ] `status it` reaches the profile's targets for lexicon, senses, dictionaries and grammar items
- [ ] Reviewer change rates stay under 15% per stage, or the stage is stopped and its brief fixed
- [ ] `build it --check` reports the static files up to date

**Technical Notes:**
Budget on the session login from the pilot: about 110 K subagent tokens per agent; a drill batch of 100 is one author and one reviewer.

**Files to Create / Modify:**
- `data/language_packs/it/**`, `static/data/grammar/it/**`

**Verification:**
`python scripts/language_pack.py status it` and every `validate-*` command pass.

---

## TASK-1273: Drill page reads a pack's built files

**Status:** [ ] Not Started
**Feature:** new-language-content-packs
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
`static/js/grammar/*.js` and `templates/grammar_drill.html` read `item.zh`, `item.py`, join tiles without spaces and load `static/data/grammar/zh/`. Make the page take the language from the route, read the sentence field named in `manifest.fields.sentence`, join tiles with `manifest.token_joiner`, and hide pinyin controls when there is no romanisation. Related to TASK-1266.

**Acceptance Criteria:**
- [ ] The Italian manifest loads and the three built topics can be drilled in all four stages
- [ ] Chinese behaviour is unchanged (existing vitest suite passes)
- [ ] Progress is stored per language (`ld.grammar.<lang>.v1`)

**Technical Notes:**
See [[features/grammar-drills.tech]]. The browser generators are Chinese-only and stay behind a language check.

**Files to Create / Modify:**
- `templates/grammar_drill.html`, `static/js/grammar/{app,data,render,text,check,store,sync}.js`
- `routes/` — language parameter on `/grammar-drill`

**Verification:**
`npm run check`, vitest, and a Playwright walk of one Italian topic at phone width.

---

## TASK-1274: Cross-field checks for pack dictionaries

**Status:** [ ] Not Started
**Feature:** new-language-content-packs
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1269

**Description:**
`validate-dict` checks one field at a time. Rules that tie fields together (the article against the noun's first sound and gender; a plural required unless the plural type is "none"; a calque being one of the wrong collocates) are only prose in the profile. Add a `rules` list to a dictionary spec and evaluate it per row.

**Acceptance Criteria:**
- [ ] A dictionary spec may carry rules of the forms "field A required when field B is X", "field A is one of list field B" and "field A matches a regex chosen by field B"
- [ ] The Italian profile states its numbered author-note rules as such rules and all reviewed rows pass
- [ ] Tests cover each rule form

**Technical Notes:**
Keep the rule forms declarative (JSON); no expression evaluation.

**Files to Create / Modify:**
- `scripts/language_pack.py` — `check_row` rules
- `tests/test_language_pack_script.py`
- `.claude/skills/new-language-swarm/briefs/profiler.md` — how to write rules

**Verification:**
`python scripts/language_pack.py validate-dict it noun_gender --reviewed` passes and fails on a row with `lo` before a plain consonant.
