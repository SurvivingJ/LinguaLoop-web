---
title: "ADR-067: A new language's content is built as a file pack before the language is wired"
status: proposed
date: 2026-11-28
---

# ADR-067: A new language's content is built as a file pack before the language is wired

## Context
The owner asked for a skill that runs an agent team to build all the content of a new language, tested on Italian. Japanese and Chinese content was built by pipelines that read and write the live database. On 2026-11-28 the database was 451 MB (stop line 480 MB, plan 500 MB); a language costs about 30 KB per word sense. The set of languages is hard-coded in about 60 places, and exercise generation fails for a language with no prompt rows.

## Decision
Content for a new language is written to `data/language_packs/<lang>/` as validated files by the `new-language-swarm` skill. A `profile.json` per language states the script rules, levels, which exercise types are reused, adapted, new or not applicable, and the language's lookup dictionaries; `scripts/language_pack.py` checks every file against it. Nothing is uploaded and no application code changes during a content run. Wiring is a separate task list written into the pack.

## Consequences
- A language can be prepared and inspected without database room or code changes.
- Exercise documents cannot go through the real planner and validators until wiring, so they are a trial of the cheat sheet only.
- Two drill tools exist (Chinese and packs) until TASK-1266 merges them.
- Uploading later needs an id remap, as the offline JLPT N1 work does.

## Alternatives Considered
- **Wire the language first, then use the existing skills.** Needs room in the database and several weeks of code before any content can be judged.
- **Generalise `scripts/grammar_drills.py` in place.** Risks the 10,209 served Chinese items for no gain to the pilot.
- **Hosted model APIs for bulk authoring.** Costs money on the owner's key; not asked for.
