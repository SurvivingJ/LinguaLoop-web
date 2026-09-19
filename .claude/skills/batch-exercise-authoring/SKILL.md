---
name: batch-exercise-authoring
description: Author vocabulary-ladder exercise assets through the staged CSV chain — answer the live generation prompts stage by stage (core, exercises, transforms, split/typed levels) across a whole sense list, N items per call, then assemble the upload files. Use when asked to author exercises from a CSV, run the staged exercise chain, or seed ladder assets in bulk with the judges in the loop. Judging is NOT done here — that is batch-exercise-judging, in a separate context.
---

# Batch Exercise Authoring (staged CSV chain)

You write the ladder assets. The live prompts come from `prompt_templates`,
rendered by the real generator objects; `scripts/exercise_stage_runner.py`
chunks them into `item_N` envelopes, you answer each call, and the runner
validates and chains the stages. Spec:
`wiki/features/csv-exercise-authoring.tech.md`.

**This skill runs stages 1, 3, 4, 5 and 7. It never runs stages 2 or 6.**
Those are `batch-exercise-judging`, and they must run in a context that has
never seen this one — a subagent given only the run directory, or a separate
session. If you judge your own work here, the pass is recorded as not run and
the run cannot assemble. Do not read the judge prompts in `stage2/` or
`stage6/` while authoring.

Reference for every numeric-key payload shape, the validator's
non-negotiables and the POS / semantic_class enums:
`.claude/skills/batch-exercise-generation/SKILL.md`. The shapes are the same.
Read its "The things that actually fail" and stage-5 sections before starting.

## The chain

| # | stage | who | command |
|---|---|---|---|
| 0 | export | runner | `python scripts/export_exercise_worklist.py --language ja --format csv --limit 8 --out-dir RUN` |
| 1 | core (P1) | **you** | `prepare RUN --stage 1` → answer → `collect RUN --stage 1` |
| 2 | judge core | *judging skill* | `prepare RUN --stage 2` → **hand off** → `collect RUN --stage 2` |
| 2b | bridge | runner | `bridge RUN` |
| 3 | exercises (P2) A/B | **you** | `prepare`/answer/`collect --stage 3` |
| 4 | transforms (P3) A/B | **you** | `prepare`/answer/`collect --stage 4` |
| 5 | split L4/L8 + typed | **you** | `prepare`/answer/`collect --stage 5` |
| 6 | judge items | *judging skill* | `prepare RUN --stage 6` → **hand off** → `collect RUN --stage 6` |
| 7 | assemble + upload assets | runner | `assemble RUN`, then `upload_exercises.py … --no-render` |
| 8 | renderer judges → render | *judging skill*, then runner | `prepare/collect --stage 8` (repeat until dry run is clean) → `render RUN` |

**Every model call in this chain is a Claude subagent or this session. No step
calls a hosted model API.**

All runner commands are `PYTHONIOENCODING=utf-8 python scripts/exercise_stage_runner.py <cmd> …`.
`status RUN` shows where every stage stands.

Stage 0 reads the database; 2-prepare, 2b and 6-prepare read it; nothing but
`upload_exercises.py` writes it. The level plan (`active_levels`,
`p3_expected_levels`, the collocate grade) cannot be known before P1 is
answered — it is a function of P1's semantic_class, morphology and collocate —
so it appears at 2b, in `RUN/plan.csv`, not in `senses.csv`.

Size the job with the user before stage 0. A first slice of 8 is the default;
anything past it is a scope conversation (see the generation skill).

## Answering a call

`prepare` writes `RUN/stageK/round_NN/call_NNN.prompt.md`. Each is a batch
contract followed by `### item_1 … ### item_k`, and each item body is the
**unchanged production prompt**. Write `call_NNN.response.json` beside it:

```json
{"item_1": { …that item's numeric-keyed answer… },
 "item_2": {"skip": true, "reason": "proper noun"},
 "item_3": { … }}
```

- Every item key, every time. A missing or null item is marked failed.
- Answer each item in its own prompt's numeric contract. Descriptive keys pass
  through the remap unmapped and fail validation downstream.
- `{"skip": true, "reason": …}` is a real answer for stage 1 only (proper
  nouns, symbols, fragments). The sense is dropped at 2b with the reason.
- Then `collect`. It prints failures per unit; fix them by re-preparing just
  those senses: `prepare RUN --stage K --senses 123,456` (a new round), answer,
  `collect` again. Later rounds overwrite only the units they re-ran.

### Stage 1 — core

The item is `vocab_prompt1_core`, already seeded with the mined corpus
sentences. `senses.csv` has `n_mined`, `sentences_needed`, `surface_tokens`
and `pos_set` per sense if you need them.

- **Keep mined sentences verbatim.** A sentence is tagged `mined` only on an
  exact match after whitespace/case normalisation; any edit silently makes it
  `generated`. `plan.csv` reports `n_mined_kept` after 2b — compare it with
  `n_mined`.
- Exactly `sentences_required` (10) sentences, target word verbatim in each.
- ja POS is **UniDic** (`名詞`, `動詞`, `形状詞` …), never `名词`/`动词`.
  `dim_vocabulary.part_of_speech` may say `verb` — ignore it; the enum wins.
- `semantic_class` is a closed enum and decides the level plan.
- `primary_collocate` null unless there is a real fixed partner.

### Stages 3–5 — exercises, transforms, split + typed

Units are per sense × variant (A/B) × part: `p2`, `p3`, `l4`, `l8`,
`typed:<type_code>`. A and B differ only in which core sentences they draw
on — **answer them independently**; a copied B is worse than none.

- P2/P3 are 1-based; L4/L8 and the typed prompts are 0-based with key 9 the
  error escape. Do not unify the numberings.
- Option levels: exactly 4 options, exactly one correct, every option
  explained — except L1, which may carry 4–8. L6 needs 3 wrong sentences.
  L7's incorrect and corrected sentences must differ.
- Typed prompts (`synonym_antonym_match`, `word_family`,
  `particle_selection`) have their own schemas, gated on upload against their
  prompt version. If the word genuinely cannot carry the type, use the key-9
  escape — that is a clean skip, not a failure.

Validation for 3–5 runs when stage 6 is prepared (it calls
`upload_exercises.prepare_exercises`). A sense that fails is listed as
blocked with the validator's own message — fix the answer, re-prepare that
stage for those senses, collect, and re-prepare stage 6.

## Handing off to the judge (stages 2 and 6)

After `prepare RUN --stage 2` (or 6), launch the judging skill in a fresh
context. With the Agent tool, the prompt is only:

> Use the batch-exercise-judging skill on run directory `RUN`, stage 2.

Nothing else — not what you wrote, not why, not which items worried you. Then
`collect RUN --stage 2`. If collect reports **RUBBER STAMP** (every item
`changed: false`), the run stops there: re-run the judge, do not override it.

## Stage 7 — assemble and upload

`assemble RUN` writes `RUN/07_upload/`:

- `batch_001.core.batch.json` + `batch_001.core.json`
- `batch_001.exercises.batch.json` + `batch_001.exercises.json`
- `dropped.json` — every sense not carried forward, with the stage and reason

Then the existing uploader, dry-run first, core before exercises. **Always
`--no-render` on the exercises upload.** Rendering inside the uploader calls
the hosted judge models over the API; this workflow makes no API calls.

```bash
python scripts/upload_exercises.py --stage core \
  --batch-file RUN/07_upload/batch_001.core.batch.json \
  --answers-file RUN/07_upload/batch_001.core.json --dry-run
python scripts/upload_exercises.py --stage core  …(same, no --dry-run)
python scripts/upload_exercises.py --stage exercises --no-render \
  --batch-file RUN/07_upload/batch_001.exercises.batch.json \
  --answers-file RUN/07_upload/batch_001.exercises.json --dry-run
python scripts/upload_exercises.py --stage exercises --no-render  …(same, no --dry-run)
```

## Stage 8 — the renderer's judges, then render (no API)

`LadderExerciseRenderer` filters items through judges as it builds rows. Here
those judges are answered by a subagent and replayed:

1. `prepare RUN --stage 8`: runs the real renderer over the stored assets,
   records every judge request it would send (nothing is sent), and writes them
   as calls. It is **the judging skill's job**. Hand off exactly as for stages 2
   and 6, then `collect RUN --stage 8`.
2. `render RUN --dry-run`: builds the rows with the stored answers replayed.
   A sense that makes a request with no stored answer is not inserted. That is
   normal for a first pass, since some requests only appear once an earlier
   verdict is known. Repeat step 1 (it asks only the new requests) until the
   dry run reports `0 sense(s) blocked`.
3. `render RUN`: inserts the rows. It refuses any sense that already has
   exercise rows.

The runner seeds Python's `random` per sense for both capture and render,
because the ja L1 phonetic-trie lookup shuffles its candidates. Without the
seed, every run asks about different words and the loop never converges.

Verify linkage:

```sql
select count(*), count(word_asset_id) from exercises
where word_sense_id in (…the run's senses…);
```

The two counts must be equal.

## Hard rules

- **Never insert into `exercises`.** Only `upload_exercises.py` writes, and it
  writes `word_assets`; the renderer makes the rows and attaches
  `word_asset_id` (TASK-512).
- **Never re-render a sense that already has rows.** `render_all` has no
  de-duplication. Clear the old rows first or pass `--no-render`.
- **Never re-express a gate.** If the level plan looks wrong, the fix is in
  the pipeline (`build_exercise_item`, the capability matrix), not a
  hand-edited `02b_plan.json`.
- **Never edit `senses.csv`, `prompts.json` or `02b_plan.json` by hand.** The
  bridge refuses to run if a prompt version moved since export — re-export.
- **Never judge in this context.**
- Never invent a sense_id; every item gets an answer or a skip.
- One run at a time, through stage 7 and the upload, before starting another.
