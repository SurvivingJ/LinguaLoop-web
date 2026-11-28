---
title: Language Registry
type: feature
status: complete
tech_page: language-registry.tech.md
last_updated: 2026-11-28
open_questions:
  - "RQ1: Should the three single-language trainers (measure words, counters, grammar drills) become one configurable trainer per language, or stay separate services?"
  - "RQ2: Should the exercise-type matrix in code be derived from the registry's features, or stay a hand-written mirror of the database table?"
---

# Language Registry

## Purpose
One place that says which languages LinguaLoop has and what each one is like, so adding a language starts with a single entry instead of edits in about a hundred files.

## User Story
As the owner, when I decide to add a language I want to declare it once, run one command that tells me exactly what is still missing for it, and work down that list — without hunting for every place the three current languages were typed out by hand.

## How It Works
1. Each language is declared once: its number, code, names, flag, the kind of script it uses, and which special features it has (pinyin, tones, furigana, pitch accent, measure-word trainer and so on).
2. A language is either **active** (learners can choose it) or **planned** (content is being prepared; the app does not accept it yet). Italian is planned.
3. Everything that used to carry its own copy of the language list — the server, the maintenance scripts, the pages in the browser, the language cards on the selection and onboarding pages — now reads the declaration.
4. A readiness check lists, for any language, the pieces that have to be written specifically for it (how its text is split into words, which exercise types it has, its name in each interface language) and marks each as present or missing. It also prints the database rows a person has to add.
5. A test fails if someone types a new copy of the language list anywhere, so the single declaration stays single.

## Constraints & Edge Cases
- Declaring a language does not make it work: the pieces on the readiness list still have to be built. The registry removes the bookkeeping, not the linguistics.
- A planned language is invisible in the app and rejected by every route, but offline content tools can name it.
- Old codes that still arrive from stored data (`cn`, `jp`) are understood and mapped to the current ones.
- Some behaviour is still tied to one language by name and was left alone on purpose (see the technical page): the three single-language trainers, word-splitting rules, prompt wording, fitted thresholds.
- Per-language seal glyphs in six page scripts still use their own small tables.

## Business Rules
- The registry is the only place a language's number and code are paired.
- A language becomes active only when it passes every required readiness check and its database rows exist.
- The browser's copy is generated from the server's declaration, never edited by hand.

## Open Questions
- RQ1 OPEN — one configurable trainer or three services.
- RQ2 OPEN — derive the exercise-type matrix from features or keep the mirror.

## Related Pages
- [[features/language-registry.tech]]
- [[decisions/ADR-068-language-registry]]
- [[features/new-language-content-packs]] — how a new language's content is prepared
- [[tasklist/new-language-content-packs.tasks]] — TASK-1275 (registry follow-ups)
- [[database/schema.tech]] — `dim_languages`, `dim_exercise_capabilities`
