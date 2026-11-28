---
title: New-Language Content Packs — Technical Specification
type: feature-tech
status: in-progress
prose_page: new-language-content-packs.md
last_updated: 2026-11-28
dependencies:
  - "skill: .claude/skills/new-language-swarm (SKILL.md, briefs/, GRAMMAR_SPEC.md, reference/, workflow.js)"
  - "script: scripts/language_pack.py"
  - "package: wordfreq (lexicon-candidates), simplemma (optional, not in requirements.txt)"
  - "skill: fat-seed-authoring (cheat sheets, Block reference)"
breaking_change_risk: low
---

# New-Language Content Packs — Technical Specification

## Architecture Overview
```
language_pack.py init / lexicon-candidates
        │
Workflow (workflow.js) ── profiler ── profile reviewer
        ├─ lexicon curators ─ sense-batches ─ sense author → sense reviewer ─ merge-senses ─┐
        │                └─ dictionary author → dictionary reviewer (per table)              │
        ├─ grammar planner ─ guide writer (per topic) ─ drill author → blind reviewer        │
        ├─ cheat-sheet writer ───────────────────────────────── fat-seed author → reviewer ◄─┘
        └─ wiring planner
        │
orchestrator: status, every validate-*, sample, build, wiki
```
Agents are spawned by the Workflow tool on the session login. Authors run on Sonnet; leads and reviewers inherit the session model (`models` argument). The script has no file access: work lists come back from agents as structured output, and two mechanical steps (`sense-batches`, `merge-senses` + `fatseed-worklist`) are run by a low-effort agent.

Pack layout `data/language_packs/<lang>/`: `profile.json`, `reports/profile.md`, `lexicon/{candidates.tsv, lexicon_NN.jsonl}`, `senses/write_NNN.{in,out,reviewed,verdict}.json` + `final.json`, `dictionaries/<key>_NN.jsonl` + `dictionaries/reviewed/`, `grammar/{plan.json, guides/, batches/, blind/, reviewed/, verdicts/}`, `fat_seed/{worklist.json, words/, reviewed/}`, `wiring/{pending_language.sql, tasks.md, prompt_tasks.txt}`. Built output: `static/data/grammar/<lang>/` (`manifest.json` + one file per topic).

## Database Impact
None. No table is read or written by the tool. `wiring/pending_language.sql` (a `dim_languages` row and `dim_exercise_capabilities` rows) is written NOT APPLIED. See [[database/schema.tech]] for those tables.

## API / RPC Surface
No route or RPC. Command line, `python scripts/language_pack.py <command> <lang>`; every `validate-*` exits 0 when clean, 1 otherwise.

| command | does |
|---|---|
| `init --name --native` | creates the pack skeleton and a profile template |
| `validate-profile` | required keys; regexes compile; `ladder` ≥ 8 rows with status `reuse` / `adapt` / `new` / `not_applicable` and a note for all but `reuse`; ≥ 3 `unique_features`; dictionary field specs |
| `lexicon-candidates --top N` | wordfreq top list grouped by lemma (simplemma when it has the language) → `lexicon/candidates.tsv` |
| `validate-lexicon` | kept rows: lemma, pos (fixed list), level (profile band), zipf, hint; dropped rows need a reason; no duplicate lemma + pos |
| `sense-batches --size --limit` | cuts kept lexicon rows not yet in a `write_NNN.in.json` into input batches; prints JSON |
| `validate-senses <file>` | order matches the `.in.json`; pos, confidence, pronunciation; `tl_simple` must not use the word; gloss lengths (60 / 120, standard longer); profile characters |
| `merge-senses` | `final.json` from `*.reviewed.json` only |
| `validate-dict <key> [--reviewed]` | rows against the profile's field specs (`str`, `int`, `bool`, enumerations, `{"regex"}`, `{"list"}`, `{"object"}`, optional `name?`), unknown fields, `unique` |
| `validate-plan`, `validate-guide`, `validate-batch [--min-items]` | the Chinese drill contract with `zh` → `tl`, script rules from the profile, optional romanisation, tiles joined with `text.token_joiner` and compared case-insensitively when `casefold_tokens` |
| `strip`, `compare` | blind copy for the reviewer; flags `KEY REJECTED`, `AMBIGUOUS`, `DIFFERENT ORDER`, `JUDGEMENT DIFFERS` |
| `fatseed-worklist --n [--function-words]` | picks reviewed senses, content words first |
| `validate-fatseed <doc>` | shape only: 10 core sentences each containing `target_word` as a whole word; option blocks 4 options (level_1 4–8), one correct, explanations; level_6 three wrong sentences; level_7 two differing sentences; legal decline tokens; blocks named by `new` llm ladder rows accepted; A and B may share at most 25% of distractors |
| `build [--check]` | reviewed batches only; drops invalid lines and repeated sentences; manifest carries `fields.sentence = "tl"` and `token_joiner` |
| `status [--json]` | counts per content type against the profile's targets |

Workflow arguments: `{lang, name, languageId, repo, glossLanguages, scale{lexiconRows, lexiconChunk, senseWords, senseBatch, dictRows, guideTopics, batchesPerTopic, batchItems, fatseedSenses, fatseedGroup}, models{lead, author, reviewer, clerk}, skip[], dictionaries[], topics[]}`.

## Component Specification (if UI)
None. The drill page is Chinese-only ([[features/grammar-drills.tech]]); reading `manifest.fields.sentence` and `token_joiner` is TASK-1273.

## Key Architectural Decisions
1. **Decision:** a pack of local files per language, with a profile that drives the checks. See [[decisions/ADR-067-new-language-content-as-file-packs]].
   - **Rationale:** the database has no room and the live pipelines fail for an unknown language id.
   - **Alternatives rejected:** wiring the language first; generalising `scripts/grammar_drills.py` in place.
2. **Decision:** a separate script, leaving `scripts/grammar_drills.py` and `data/grammar_drills/zh/` untouched.
   - **Rationale:** 10,209 live Chinese items depend on pinyin checks and field names; TASK-1266 can later merge the two.
   - **Alternatives rejected:** adding `--lang` to the Chinese script now.
3. **Decision:** fat-seed documents are shape-checked only until the language is wired.
   - **Rationale:** `scripts/fat_seed_runner.py` needs prompt and capability rows; `get_template_config` has no cross-language fallback.
   - **Alternatives rejected:** faking Italian rows in the offline snapshot.

## Security Considerations
The tool reads and writes only under the pack and `static/data/grammar/<lang>/`. Agents are told to write no database rows, call no hosted API, and not to commit. The run did not use `CLAUDE_API` or OpenRouter.

## Testing Strategy
`tests/test_language_pack_script.py` (25 cases): profile rules, each item type, empty and paired cloze options, forbidden characters, sentence bounds, tile joining for spaced and unspaced scripts, romanisation, plan / guide / batch on disk, strip and compare flags, build from reviewed only and `--check`, sense rules, batch cutting and merge, dictionary field specs, exercise-document shape, status. Run here with `--noconftest` (the project requirements are not installed in the cloud container).
