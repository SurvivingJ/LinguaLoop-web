---
title: "ADR-068: One language registry in code, with a generated browser copy and a guard test"
status: accepted
date: 2026-11-28
---

# ADR-068: One language registry in code, with a generated browser copy and a guard test

## Context
The owner asked for "a language registry so it is easy to add new languages". The pairing of language ids and codes was typed out in 36 backend files, 52 scripts and 18 page scripts, plus four templates; `config.py` called itself the single source of truth but most code did not read it. Checks such as `language_id in (1, 3)` mixed up "uses a CJK script" with "has a reading to quiz".

## Decision
`services/language_registry.py` declares each language once (identity, script family, named features, status active or planned). All other code reads it; existing constants keep their names. `static/js/language-registry.js` is generated from it and loaded on every page. `services/language_readiness.py` lists the per-language plug-in points and `scripts/check_language.py` reports them. A test fails on any new literal language map.

## Consequences
- Adding a language is one entry plus the items the readiness check names.
- A planned language can be named by offline content tools while the app rejects it.
- The registry and `dim_languages` must agree; nothing enforces that at runtime yet (TASK-1275).
- Behaviour that is truly per language (word splitting, prompts, thresholds, the single-language trainers) is still found by name, not by registry attribute.

## Alternatives Considered
- **Read `dim_languages` everywhere.** Scripts and import-time constants would need a database connection; features and script family are not columns.
- **A shared JSON file.** Two parsers and no place for derived properties; the generated file gives the browser the same data.
- **Convention only.** Already tried: the comment in `config.py`.
