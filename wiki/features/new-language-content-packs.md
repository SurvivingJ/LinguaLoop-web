---
title: New-Language Content Packs
type: feature
status: in-progress
tech_page: new-language-content-packs.tech.md
last_updated: 2026-11-28
open_questions: []
---

# New-Language Content Packs

## Purpose
A repeatable way to prepare everything a new study language needs — its word list, definitions, exercises, grammar drills and the exercises only that language has — before any of it touches the live app. Italian is the first language prepared this way, at pilot size.

## User Story
As the owner, I want to add a language without months of one-off pipelines: I name the language, a team of AI agents builds and cross-checks the content, and I get files I can inspect, a list of what is still unverified, and a plan of the engineering work needed to switch the language on.

## How It Works
1. A profile is written for the language: who the learner is, which exercise types carry over from Japanese, Chinese and English, which do not apply, and which new ones the language needs. A second agent who did not write it reviews it as a teacher would.
2. From the profile the team works in parallel:
   - a frequency list is turned into a curated word list with levels;
   - each word gets a child-level and a dictionary-level definition in the language itself, plus an English gloss;
   - the language's own lookup tables are written (for Italian: noun gender and articles, verb conjugation, which preposition a word takes, collocations, false friends), the way measure words were for Chinese;
   - a grammar plan is drawn up from what learners get wrong, each topic gets a guide, and drill items are written in batches;
   - a short writing guide for exercise authors is produced and tried on a few words;
   - the engineering work to make the language live is listed.
3. Every piece is written by one agent and checked by another that starts from nothing but the file. Drill reviewers first solve a copy with the answers removed; where their answer differs from the key, the item is ambiguous or wrong.
4. A script, not an agent, decides whether each file is acceptable, and only reviewed drill batches are built into the files the app would serve.

## Constraints & Edge Cases
- Nothing is uploaded. The pack is files in the repository until the owner decides.
- No human native speaker checks the content. By the owner's decision the final language check is an Opus reviewer; that is a stronger reader than the authors, not a guarantee.
- The exercise documents are checked for shape only: the real exercise pipeline cannot run for a language that has no prompt and capability rows yet.
- The drill page reads Chinese field names today, so built Italian drills are not served.
- A pilot comes before any larger run; the pilot's reviewer fix rates decide whether the author instructions need changing first.

## Business Rules
- Author and reviewer are never the same agent.
- Unreviewed content is never built or merged.
- Content is not edited to pass a check, and the profile is not loosened to admit a file.
- Paid model APIs are used only when the owner says so for that run.

## Open Questions
- NQ1 ANSWERED 2026-11-28 — owner: "Accept". The six new exercise types, five dictionaries and the profile's teaching rules stand as proposed.
- NQ2 ANSWERED 2026-11-28 — owner: "Opus". The language check is done by Opus reviewers that mark every item; no human native speaker is planned. First check run the same day ([[evaluations/italian-pack-pilot-2026-11-28]]).
- NQ3 ANSWERED 2026-11-28 — owner: "We will just store it in the repo for now". Packs stay in `data/language_packs/<lang>/`; nothing is uploaded.
- NQ4 ANSWERED 2026-11-28 — covered by NQ1: preposition choice is its own type.

## Related Pages
- [[features/new-language-content-packs.tech]]
- [[decisions/ADR-067-new-language-content-as-file-packs]]
- [[evaluations/italian-pack-pilot-2026-11-28]]
- [[tasklist/new-language-content-packs.tasks]]
- [[features/language-registry]] — where a language is declared and what it still needs
- [[features/grammar-drills]] — the Chinese drills the grammar contract is taken from
- [[features/exercise-generation-v2]] — the exercise ladder and capability matrix the profile maps onto
