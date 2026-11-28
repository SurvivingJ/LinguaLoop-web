---
name: new-language-swarm
description: Build the whole content pack for a NEW study language with an agent team — language profile (which exercise types carry over from Japanese / Chinese / English and which unique ones the language needs), lexicon, two-level senses and glosses, the language's own lookup dictionaries, grammar drills (plan, guides, author + blind-reviewer batches), fat-seed cheat sheet and exercise documents, and the wiring plan. Everything is written as validated local files under data/language_packs/<lang>/; nothing is uploaded. Use when asked to add a language (Italian, Spanish, Korean …), build or extend a language pack, or run the content swarm for a language.
---

# New-language swarm

Japanese and Chinese content was built over months by separate pipelines.
This skill runs the same work for a new language as one team: a script
(`workflow.js`) decides who works on what and in which order, agents write
files, and `scripts/language_pack.py` says whether each file is acceptable.
You orchestrate, check the numbers, sample the quality and report. You do
not write content yourself.

Invoking this skill is the owner's opt-in to multi-agent orchestration: call
the Workflow tool with `scriptPath` set to this skill's `workflow.js`.

## What a pack is

`data/language_packs/<lang>/`:

| path | written by | checked by |
|---|---|---|
| `profile.json`, `reports/profile.md` | profiler, then a reviewer | `validate-profile` |
| `lexicon/candidates.tsv` | `lexicon-candidates` (wordfreq) | — |
| `lexicon/lexicon_NN.jsonl` | lexicon curators | `validate-lexicon` |
| `senses/write_NNN.{in,out,reviewed,verdict}.json`, `final.json` | sense author, sense reviewer | `validate-senses`, `merge-senses` |
| `dictionaries/<key>_NN.jsonl`, `dictionaries/reviewed/` | dictionary author, reviewer | `validate-dict [--reviewed]` |
| `grammar/plan.json`, `guides/`, `batches/`, `blind/`, `reviewed/`, `verdicts/` | planner, guide writers, drill authors, blind reviewers | `validate-plan`, `validate-guide`, `validate-batch`, `strip`, `compare` |
| `fat_seed/words/`, `fat_seed/reviewed/` | fat-seed author, reviewer | `validate-fatseed` (shape only, see below) |
| `wiring/pending_language.sql`, `tasks.md`, `prompt_tasks.txt` | wiring planner | you |
| `.claude/skills/fat-seed-authoring/cheatsheets/<lang>.md` | cheat-sheet writer | the gold-set run, once wired |
| `static/data/grammar/<lang>/` | `build` (reviewed batches only) | `build --check` |

Role instructions are in `briefs/` (every agent reads `COMMON.md` and its own
brief). `GRAMMAR_SPEC.md` is the drill contract. `reference/ja-zh-inventory.md`
is the survey of what Japanese and Chinese have, which the profiler answers
row by row; `reference/wiring-checklist.md` lists the code that knows about
languages.

## Before you start

1. Read `wiki/index.md` and the last entries of `wiki/log.md` (CLAUDE.md).
2. Check the database size and the stop line in the latest log entries. This
   skill writes no rows, but the report must say what uploading would cost
   (about 30 KB per sense for dictionary + assets).
3. Agree the scale with the owner if they did not state it: **pilot** (the
   defaults below, about 30 agents) or a named larger scale. Never go from
   nothing to full scale: the pilot's defects decide the briefs.
4. Register the language as `PLANNED` in `services/language_registry.py` (next free id, checked
   against `dim_languages` with a read-only query), run `python scripts/build_language_registry_js.py`,
   and use that id as `languageId`. `python scripts/check_language.py <code>` lists what the
   app still needs for it; the wiring planner starts from that list.

## Run

```bash
python scripts/language_pack.py init <lang> --name <Name> --native <Native name>
python scripts/language_pack.py lexicon-candidates <lang> --top 8000   # needs wordfreq (+ simplemma if it has the language)
```

Then the Workflow tool, `scriptPath: .claude/skills/new-language-swarm/workflow.js`, with

```json
{"lang": "it", "name": "Italian", "languageId": 4, "repo": "<absolute repository root>",
 "glossLanguages": ["en"],
 "scale": {"lexiconRows": 300, "lexiconChunk": 300, "senseWords": 50, "senseBatch": 25,
           "dictRows": 60, "guideTopics": 3, "batchesPerTopic": 1, "batchItems": 50,
           "fatseedSenses": 6, "fatseedGroup": 3},
 "models": {"author": "sonnet"}}
```

Those are the pilot defaults. The team:

1. **Profile** — one profiler, then a reviewer who did not write it. Nothing
   else starts before this.
2. In parallel:
   - **Lexicon** curators → sense batches cut by the tool → per batch a
     **sense author** and a **sense reviewer** → `merge-senses`.
   - **Dictionaries** (after the lexicon): per lookup table an author and a
     reviewer who re-derives every form before reading the author's.
   - **Grammar**: planner → per topic a guide writer → per batch a drill
     author and a reviewer who solves a blind copy first.
   - **Cheat sheet**, then (with the senses) **fat-seed** authors and reviewers.
   - **Wiring** planner.

Authors run on Sonnet (the repository's measured practice); leads and
reviewers inherit the session model. Override with `models`
(`lead`, `author`, `reviewer`, `clerk`).

Larger runs: raise `scale`, pass `"skip": ["profile", "lexicon", …]` for
stages that are finished (with `"dictionaries": [...]` and `"topics": [...]`
when the profile and plan are skipped), and keep one workflow to a few dozen
batches so its result can be read and sampled before the next. `guideTopics: 0`
and `batchesPerTopic: 0` are not "everything": the plan's batch counts are
launched by naming topics and counts per run. Files that exist are overwritten
by a re-run of the same batch number, so start the next batch numbers by
running the remaining topics, not the same ones.

## After the workflow returns

Do these yourself, in order:

1. `python scripts/language_pack.py status <lang>` and every `validate-*` on
   what was written. An agent's "validator_ok" is a claim; the tool is the fact.
2. Read the workflow's `not_ok` and `doubts`. A doubt that says a rule is
   wrong for the language is a brief or tool change, not something to drop.
3. **Sample the content.** Read at least 15 drill items, 10 senses, 10
   dictionary rows and 2 exercise documents, and the verdict files' totals.
   Report the reviewers' fix rates per stage: a stage where reviewers changed
   more than about 15% needs its author brief fixed before scaling.
4. **Language check by Opus** (owner's decision, 2026-11-28: the final checker is Opus, not a
   person). Spawn Opus reviewers that mark every built drill item, every guide, every reviewed
   dictionary row and every exercise document as ok / wrong / unnatural, without the earlier
   verdict files, into `reports/native_check/`; then one agent applies the certain marks
   (fix, delete the row, or move the document to `fat_seed/rejected/`) and lists the rest in
   `applied.json`. Report the rates per content type.
5. `python scripts/language_pack.py build <lang>` then `build --check`.
6. Wiki, as CLAUDE.md requires: the evaluation page with the run's numbers,
   the feature pages if the pack format changed, tasks from `wiring/tasks.md`
   (the wiki owner assigns TASK ids), index and log.
7. Tell the owner what exists, the Opus check's rates and what it left uncertain, and that
   no human native speaker has read it.

## Hard rules

- **No database writes and no paid API.** The team writes files. Agents run
  on the session login through the Workflow tool; the owner's API key
  (`CLAUDE_API`) and OpenRouter are used only when the owner says so for that run.
- **Author and reviewer are never the same agent**, and a reviewer never sees
  the author's reasoning: only the file.
- **Unreviewed content is never built.** `build` reads `grammar/reviewed/` only;
  `merge-senses` leaves out batches with no reviewed file.
- **Do not edit content to make a validator pass.** Send it back (re-run that
  batch) or drop it. Do not loosen the profile to admit a file either: the
  profile changes only when the language needs it, and then every file is
  re-validated.
- **The fat-seed documents are shape-checked only.** The real runner
  (`scripts/fat_seed_runner.py`, the `nt_*` pipeline) needs the language's
  prompt rows and capability rows; until the wiring tasks are done the
  documents are a pilot of the cheat sheet, not upload packages. Once wired,
  the path is the `fat-seed-authoring` skill, starting with its 100-sense
  gold set.
- **The Opus check is the last reader, not a guarantee.** In the Italian pilot it still found
  one judgement-table row in five wrong after the first review. Say in every report that no
  human native speaker has read the content.

## Known limits

- `lexicon-candidates` groups forms with an automatic lemmatiser and includes
  names and fragments; the curators exist to fix that.
- The drill page (`static/js/grammar/`) reads the Chinese field names; the
  built manifest carries `fields.sentence` and `token_joiner` for the
  frontend task in the wiring list. Until then the built files are not served.
- Chinese drills stay with `scripts/grammar_drills.py` and
  `data/grammar_drills/zh/`; do not move them into a pack.
