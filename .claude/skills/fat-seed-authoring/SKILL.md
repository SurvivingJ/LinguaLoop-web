---
name: fat-seed-authoring
description: Production path for building vocabulary-ladder exercise assets for every sense of a language — one named-field JSON document per word sense (core + every exercise block for variants A and B), written and reviewed by headless `claude -p` calls with no tools (Sonnet core, Haiku audits/variants/patch review), validated exactly as upload would, assembled into SQL upload packages. Use when asked to fat-seed words, build or backfill exercise assets for a language (ja, zh, en), author one JSON per word, or run the authoring pipeline on a new language. The staged, live-prompt path is batch-exercise-authoring.
---

# Fat-Seed Authoring

One JSON document per word sense, pushed through the **unchanged** upload
path. Since October 2026 the documents are written by a script-driven,
tool-free pipeline: each model call gets a prompt and returns JSON, the
scripts write the files and run the validators. You orchestrate: export,
build runs, launch the pipeline, watch it, sample its quality, package the
SQL. You do not write or review documents yourself.

Measured on Japanese (`data/exercise_seeding/ja/opt/REPORT.md`, 6,111 senses
produced): **$0.045/sense** against $0.19 for the earlier Sonnet + Opus
subagent path. A frozen Opus judge scored a 104-sense production sample at
7.05/10, with 22% of senses carrying at least one item-breaking defect. The
earlier path scored 7.67 and 14% on the 100-sense test set. Read the report
before changing the configuration: most "obvious" improvements were measured
and rejected.

## The chain

| # | step | command |
|---|---|---|
| 0 | cheat sheet for the language exists | `.claude/skills/fat-seed-authoring/cheatsheets/<lang>.md` (see "New language") |
| 1 | export the worklist | `python scripts/export_exercise_worklist.py --language <lang> --stage core --format csv --include-unreferenced --out-dir data/exercise_seeding/<lang>/fatseed_all` |
| 2 | build runs (≤12 senses, a lemma's senses together) | `python3 scratch_offline/nt_make_runs.py data/exercise_seeding/<lang>/fatseed_all data/exercise_seeding/<lang>/wf2` |
| 3 | author + review every run | `python3 scratch_offline/nt_pipeline.py --lang <lang> --workers 20` |
| 4 | quality sample | `python3 scratch_offline/nt_judge.py RUN --source reviewed --model opus --effort medium --rubric 3` on ~10% of runs |
| 5 | assemble + capture the uploader's writes | `python3 scratch_offline/assemble_all.py --lang <lang>` |
| 6 | package the SQL | `python3 scratch_offline/package_upload.py data/exercise_seeding/<lang>/payload_wf/writes.jsonl data/exercise_seeding/<lang>/upload --lang <lang>` |
| 7 | apply, verify, render | `psql … -f upload/apply_all.sql`, `verify.sql`, then stage 8 + render (below) |

Steps 2–6 resume: re-running a step skips finished work and never re-pays.

## Prerequisites

- **Models:** the `claude` CLI on PATH; every call is `claude -p --tools ""`
  with a system prompt. Usage limits are handled: `call_model` waits 10 min
  and retries. A malformed JSON reply is retried once.
- **Database:** the runner (`scripts/fat_seed_runner.py`: `brief`, `plan`,
  `check`, `assemble`) reads `dim_word_senses`, `prompt_templates` etc.
  - With network access to Supabase, set `NT_ONLINE=1` plus `SUPABASE_URL` /
    `SUPABASE_KEY`, and the scripts call it directly. Exports and uploads use
    the same credentials.
  - Without it, as in a Claude Code cloud container, everything goes through
    the offline shim `scratch_offline/run.py`. The shim serves reads from
    `scratch_offline/snap/<table>.json` (gitignored: they hold table rows)
    and records writes to `writes.jsonl` instead of executing them.
  - To snapshot a language through the Supabase MCP, run one
    `SELECT json_agg(t) AS <table> FROM (…rows for that language…) t` per
    table. Then run `python3 scratch_offline/spill.py <saved tool result> <table>`.
  - Tables to snapshot: `dim_languages`, `dim_vocabulary`, `dim_word_senses`,
    `prompt_templates`, `tests`, `exercises`, `word_assets`,
    `corpus_collocations`, `calibration_anchor_blocklist`. Check
    `snap/_queries.log` for `MISSING` tables after a dry run.
- **Lints:** `nt_pipeline.py` sets `FAT_SEED_LINT_ALL_BLOCKS=1` with
  `FAT_SEED_LINT_SKIP=l3_generic_expl,l6_shared_expl,l6_copied_expl,l7_edit_far`.
  It keeps only the rules that paid for themselves: A/B overlap, level_7
  twin, particle slot, level_7 error on the target.

## What one run does (`nt_pipeline.py` → `nt_author.py` → `nt_review.py`)

1. `brief`, then **core**: Sonnet/low writes each sense's core (definition,
   10 sentences with the mined ones byte-for-byte, POS, register, forms).
   The core anchors every block, and Haiku confuses sibling senses of the
   same lemma here; that was 0.26 vs 0.06 fatal share in production. Do not
   move the core to Haiku.
2. **core audit** (Haiku): reading / whole-word / sense / natural per sentence,
   regenerating failures. This takes core fatals below the earlier pipeline.
3. `plan`: code fixes each block's anchor sentence, answer and `given` values.
4. **variants** (Haiku/medium, 4 senses per call): every block the plan lists
   for A and B, in the Block reference shapes below. For ja, level_1 is
   declined in code (`--skip-l1`), because the renderer builds it from the ja
   phonetic trie. zh and en have no trie, so their level_1 is authored and the
   cheat sheet must cover it.
5. **variant audit + level_6 audit** (Haiku): level_6 "wrong" sentences must
   be natural-sounding sense misuses, and level_7 must have one span on the
   target. This is the largest quality gain per dollar.
6. `check` and up to 2 repair rounds for validator failures only.
7. **patch review** (Haiku/medium, no tools): it returns RFC 6902 JSON-Patch
   operations, never whole documents. Patched blocks are shape-validated and
   declines preserved. `check --source reviewed` follows, with one repair round.

Configuration lives in `scratch_offline/nt_pipeline.py` (`AUTHOR_ARGS`,
`REVIEW_ARGS`, `LINT_ENV`). Each call is logged with its cost in
`RUN/fat_seed/nt_usage.jsonl`.

## Running it

- Launch detached so a session restart does not kill it:
  `setsid nohup python3 scratch_offline/nt_pipeline.py --lang ja --workers 20 >> LOG 2>&1 < /dev/null & disown`.
  It prints `RUN <dir>: final reviewed check {...}` per run and `PIPELINE DONE`.
- **Workers:** each run is ~35 min of serial model calls; 20–32 workers gives
  ~50 runs/hour. The account's 5-hour usage limit, not the machine, is the
  ceiling. More workers only reach it sooner.
- **Restarting:** stop the pipeline and its children (`nt_pipeline`,
  `nt_author`, `nt_review`, `claude -p`), delete any truncated JSON written in
  the last minutes, relaunch the same command. Authoring resumes from
  `words/`, review resumes with `--resume`, and audits keep their state in
  `audit_*.json`.
- **QA:** judge ~4 random finished runs at a time (~45 senses, ~$3). Steer by
  the share of senses with ≥1 fatal. It is the stable metric; minors are noise.
  Judge records carry a document hash, so re-running the judge after a
  re-review re-judges only changed senses.

## Afterwards

- `assemble` drops a sense when the reviewer said `rewrite` but changed nothing.
  Re-review those senses: move their `review/` and `reviewed/` files aside,
  run `nt_review.py RUN RUN --model haiku --effort medium --resume`, then
  delete `RUN/07_upload/` and `RUN/upload_writes.jsonl` and re-assemble.
  This recovered 179 of 209 senses on ja.
- Senses that still fail: retry the model-omission failures once in a fresh
  run (`nt_make_runs.py` picks them up). `plan: no LLM-authored level is
  active` cannot be fixed by authoring.
- **Rejected cores** are dictionary-data problems (duplicate sibling senses,
  wrong headword/POS, definition ≠ usage). List them in
  `data/exercise_seeding/<lang>/issues/` for the user; regenerating does not
  fix them.
- **Packages:** `package_upload.py` writes `apply_all.sql` (one transaction),
  ~1 MB `chunks/` (each its own transaction, for the Supabase SQL editor),
  `word_assets.csv`, `verify.sql` and a README. Use `--exclude-csv
  <earlier>/word_assets.csv` for a delta. Files over 50 MB do not belong in
  git: commit the chunks, or `gzip -9` the SQL (≈7× smaller). Archive the
  JSON records (`words/`, `reviewed/`, `review/`, `senses.csv`) as a tar.gz.
- **Upload and render** stay exactly as the staged chain: `--source-model
  claude-code:fat-seed`, core before exercises, `--no-render`. Then
  `python scripts/exercise_stage_runner.py prepare RUN --stage 8`, hand off
  to `batch-exercise-judging`, then `collect`, `render --dry-run`, `render`.
  Verify `count(*) = count(word_asset_id)` on `exercises`.

## New language

1. **Cheat sheet:** write `cheatsheets/<lang>.md` following
   `cheatsheets/README.md`. Copy the five-section structure of `ja.md` and
   replace the Japanese examples and rules with the language's own.
   `nt_pipeline.py` refuses to start without one.
2. **Prompts:** set `--lang` (or `NT_LANG`). The system prompts name the
   language automatically: they say "Japanese" and are localised, while
   Japanese stays byte-identical.
3. **Blocks differ:** `particle_selection` is ja-only and `word_family`
   en-only. The plan decides which blocks a sense gets, so nothing to configure.
   level_1 is authored unless the language has a phonetic trie
   (`TRIE_LANGS` in `nt_pipeline.py`; ja only today).
4. **Validate before scaling:** export a 100-sense gold set with one sense
   per lemma, but keep siblings together the way production runs do. Run it
   with `NT_LANG=<lang> python3 scratch_offline/nt_experiment.py <arm>
   --gold gold100 --chunks 8 --judge-model opus --judge-effort medium
   --judge-rubric 3 …`, and compare against an arm using the earlier
   configuration on the same senses. Differences under ~0.55 points on 100
   senses are noise. Fix the cheat sheet where the defect classes cluster
   (`nt_experiment.py --loss <arm> --against <baseline>`).
5. Then run the chain from step 1.

## Block reference

The document, after phase 2:

```json
{"sense_id": 53352, "lemma": "超える",
 "core": { …phase 1… },
 "variants": {"A": { …blocks… }, "B": { …blocks… }}}
```

Write exactly the blocks `plans/<sid>.json` lists under `blocks.A` / `blocks.B`.
The plan also fixes each block's anchor sentence (`sentence_index`,
`sentence`), its answer (`correct`) and anything code decides (`given`:
the syn/ant `relation`, the particle spans). **Do not choose these yourself.**
Surplus blocks are dropped with a warning; missing ones fail `check`.

An option is `{"text": "…", "is_correct": true|false, "explanation": "…"}`.
Every option gets an explanation. Exactly one is correct.

| block | shape |
|---|---|
| `level_1` phonetic | `{"options": [4–8 options]}`. The correct option is the plan's `correct` (the headword); the distractors must sound like it (L1 is a **listening** exercise). For ja, pairs that differ only in pitch accent are NOT valid. Over-generate: a judge filters distractors and the item dies below 3 survivors. Or `{"declined": "no_minimal_pairs"}` when the word has too few real one-mora neighbours for that variant. |
| `level_3` cloze | `{"options": [4]}`. The correct option is the plan's `correct`, the form in the anchor sentence. Only it may fit the blank. |
| `level_5` collocation gap | `{"options": [4]}`. The correct option is the plan's collocate; the distractors are genuine non-collocates. |
| `level_6` semantic discrimination | `{"correct_sentence_index": <plan value>, "wrong_sentences": [{"text", "explanation"} ×3]}`. Each wrong sentence misuses the word (wrong sense or wrong usage), and is clearly wrong. |
| `level_7` spot incorrect | `{"incorrect_sentence", "corrected_sentence", "error_description", "correct_sentence_indices": <plan value>}`. One error involving the target; the two sentences must differ. |
| `level_4` morphology | `{"options": [4], "base_form": "…", "form_label": "…"}`. The correct option is the form in the anchor sentence; distractors are real forms of the same lemma. Or `{"declined": "no_inflection"}`. |
| `level_8` collocation repair | `{"options": [4], "error_collocate": "…"}`. The correct option is the collocate; `error_collocate` is the wrong word planted in the sentence. Or `{"declined": "no_collocation"}`. |
| `synonym_antonym_match` | `{"relation": <given.relation>, "options": [4]}`. Distractors are real words NOT in that relation to *this sense*. Or `{"declined": "no_relation"}`. |
| `word_family` (en) | `{"stem": "…", "options": [4, each also with "part_of_speech"]}`. Distractors are invented, well-formed non-words. Or `{"declined": "no_family"}`. |
| `particle_selection` (ja) | `{"blanked_particle": "に", "options": [4 particles], "error_tags": {"へ": "direction", …}}`. `blanked_particle` must be the correct option and must occur in the anchor sentence. Or `{"declined": "no_particle_slot"}`. |

A and B must be written independently. A B that copies A is worse than none.
Only the blocks with a `may_decline_with` in the plan can be declined, and
only with that token.

## Hard rules

- Never hand-edit `plans/`, `senses.csv`, `prompts.json` or `07_upload/`.
  A wrong plan is fixed in the core (`semantic_class`, `primary_collocate`,
  `morphological_forms`), never in the plan file.
- Mined sentences stay byte-identical, or they silently become `generated`.
- Launch a run directory exactly once at a time: two writers corrupt it.
- Never insert into `exercises`; never render a sense that already has rows.
- Never write to the live database from this pipeline; it produces SQL
  packages that the user applies.
- Do not change models, effort or prompts in the production configuration
  without a gold-set comparison under the frozen judge. Long rule lists, higher
  effort, split A/B calls, extra repair rounds and second review passes were
  all measured and made things worse or cost more for nothing (`opt/REPORT.md`).

## Small slices: the subagent path

For a handful of senses without the CLI pipeline, the runner still supports
the original flow: `brief RUN` → author subagents write
`RUN/fat_seed/words/<sid>.json` (core, then `plan RUN`, then variants) →
`check RUN` until `ok` → `review-pack RUN` → a fresh subagent runs the
fat-seed-review skill per pack → `check RUN --source reviewed` → `assemble RUN`.
`status RUN` shows where every sense stands. Authors and reviewers must be
separate subagents.
