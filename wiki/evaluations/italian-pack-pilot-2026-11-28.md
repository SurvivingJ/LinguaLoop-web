---
title: Italian content pack — pilot run of the new-language swarm
type: evaluation
status: complete
last_updated: 2026-11-28
---

# Italian content pack — pilot run (2026-11-28)

Owner: "Analyse our resources and content for Japanese and Chinese and create a skill to run an agent swarm team to build all of the unique exercises and content for a new language, and test it with Italian."

One run of `.claude/skills/new-language-swarm/workflow.js` at pilot scale: 35 agents, 48 minutes, 3.93 M subagent tokens on the session login. No paid API, no database write (451 MB before and after), no application code changed. Files: `data/language_packs/it/` (1.3 MB), `static/data/grammar/it/` (0.12 MB, not served), `.claude/skills/fat-seed-authoring/cheatsheets/it.md`. Method and tool: [[features/new-language-content-packs.tech]]. The survey of Japanese and Chinese it starts from is `.claude/skills/new-language-swarm/reference/ja-zh-inventory.md`.

**No native speaker has checked any of this.** Every reviewer was an AI agent. The orchestrator's own sample (18 drill items, 15 dictionary rows, 6 senses) found no error, which is not a measure of quality.

## What was produced

| content | pilot | full-scale target in the profile | all files pass the tool |
|---|---|---|---|
| profile: exercise-type decisions | 31 types decided | — | yes |
| lexicon (candidate ranks 1–300) | 317 lemmas kept, 19 dropped (A1 174, A2 86, B1 48, B2 9) | 5,000 | yes |
| senses (two definitions in Italian, example, IPA, English gloss) | 50 | 5,000 | yes |
| dictionaries, reviewed rows | noun_gender 60, verb_conjugation 60, verb_government 57, collocations 49, false_friends 56 | 2,000 / 600 / 350 / 500 / 200 | yes |
| grammar plan | 37 topics, 7 categories, 90 batches planned | 9,000 items | yes |
| grammar guides | 3 (present-tense-forms, ce-or-e, adjective-agreement) | 37 | yes |
| drill items, reviewed and built | 151 (cloze 99, judge 32, order 13, rewrite 7) | 9,000 | yes |
| exercise documents (shape-checked only) | 6 | one per sense | yes |
| fat-seed cheat sheet | 8.2 KB, untested on a gold set | — | no check exists |
| wiring plan | 34 tasks, pending SQL (not applied), 93 prompt task names | — | no check exists |

## What the profile decided for Italian

- **Not applicable (8):** the pinyin, tone and kanji-reading types, measure words, counters, Japanese particles.
- **Reused as they are (6):** definition match, semantic discrimination, synonym / antonym, both flashcards, speed round.
- **Adapted (11):** listening recognition (double consonants and stress instead of tones or morae), cloze (the gender frame must not give the answer away), typed cloze (accents count), word forms, spot-the-error, sentence tiles, word family, both translation types; collocation gap-fill and repair stay disabled until the collocation dictionary is complete.
- **New (6):** `stress_position` (which syllable is stressed, from the IPA), `article_match` (il / lo / l' / la, un / uno, plural and fused prepositions, from the noun dictionary), `auxiliary_choice` (essere or avere), `conjugation_form` (a paradigm cell), `government_match` (which preposition a word takes) — all generated from the dictionaries without a model — and `preposition_selection` (authored per sentence, the analogue of Japanese particles).
- **Fifteen features learners must automate:** nine delivered by dictionaries, the ladder or a generator; six by grammar topics (clitic pronouns, passato prossimo against imperfetto, the subjunctive, agreement, piacere-type verbs, tu against Lei).

## How much the reviewers changed

| stage | reviewed | changed | dropped | share touched |
|---|---|---|---|---|
| senses | 50 | 16 | 0 | 32% |
| noun_gender | 60 | 1 | 0 | 2% |
| verb_conjugation | 60 | 1 (no form changed) | 0 | 2% |
| verb_government | 60 | 8 | 3 | 18% |
| false_friends | 60 | 8 | 4 | 20% |
| collocations | 60 | 25 | 11 | 60% |
| drill items | 151 | 30 | 0 | 20% |
| exercise documents | 6 | 6 | 0 | 4 of 6 had a defect that would break an item (9 in all) |

The blind solve flagged 2 of 151 drill items (both ambiguous cloze items in the verb batch); the other 28 changes came from the read-through.

Reading: the two form tables (gender, conjugation) are reliable from a Sonnet author. Everything that needs a judgement of acceptability is not: wrong collocates that are valid Italian in another sense, a preposition "calque" that is also standard, a "wrong" sentence that is acceptable. Definitions of function words joined two senses. By the skill's own rule (over about 15% changed means the author brief is fixed before scaling), senses, the three judgement dictionaries, drills and exercise documents were not ready to scale; their briefs were amended after the run and **have not been re-tested**.

Exercise documents: the worklist picked the most frequent words, which are function words (il, di, non). Those are taught by dictionaries and drills, and made the weakest documents. The picker now takes content words first.

## Decisions for the owner

1. The six new exercise types and five dictionaries (NQ1). Each is engineering work listed in `data/language_packs/it/wiring/tasks.md`.
2. `preposition_selection`: a new type, or the Japanese particle renderer under another name (NQ4).
3. Typed answers treat a wrong or missing accent (perchè for perché) as an error from A1.
4. Open against closed e / o is not drilled; passato remoto is left out of the conjugation table; plural-only nouns are left out of the gender table.
5. Vulgar words are dropped from the lexicon (one in the first 300).
6. Azure voices `it-IT-IsabellaNeural` / `it-IT-DiegoNeural` are from memory, not checked.
7. Language id 4 is free today (`dim_languages` max id 3, read-only query).

## Limits of this test

- 3 of 37 grammar topics, 50 of about 5,000 senses, 60 rows per dictionary, 6 exercise documents.
- Cross-field dictionary rules (article against first sound and gender, a calque being one of the wrong collocates) are in the profile's author notes only; the tool checks one field at a time (TASK-1274).
- The cheat sheet is 8.2 KB against the roughly 5 KB that worked for Japanese, and has not met a gold set.
- The full pytest suite was not run: the project requirements are not installed in this container. `tests/test_language_pack_script.py` (25 cases) passes with `--noconftest`; ruff is clean on the new files.

## Related Pages
- [[features/new-language-content-packs]]
- [[decisions/ADR-067-new-language-content-as-file-packs]]
- [[tasklist/new-language-content-packs.tasks]]
