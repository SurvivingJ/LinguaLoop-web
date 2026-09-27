---
name: fat-seed-authoring
description: Cheap/fast path for building vocabulary-ladder exercises from a word list — spin up subagents that each write one named-field JSON document per word sense (core + every exercise block for variants A and B), validate them exactly as upload would, hand off to fat-seed-review in a fresh context, then assemble and upload. Use when asked to fat-seed words, build exercises quickly/cheaply from a word list, or author one JSON per word. The staged, live-prompt path is batch-exercise-authoring; this one trades the live prompt wording for one document per word.
---

# Fat-Seed Authoring

One JSON document per word sense, written by a subagent, reviewed by a
different subagent, then pushed through the **unchanged** upload path. You
orchestrate: you run the commands, spawn the authors, relay errors, and hand
off the review. You do not write the documents yourself, and you never review
them.

Runner: `PYTHONIOENCODING=utf-8 python scripts/fat_seed_runner.py <cmd> RUN`
(translation in `services/vocabulary_ladder/fat_seed.py`, tests in
`tests/test_fat_seed.py`). **No step calls a hosted model API.** Every model
call is a Claude subagent.

Compared with `batch-exercise-authoring` (the staged chain), this path answers
the rules of the live prompts, not the prompts themselves, in one document
instead of five stages. Whether that costs quality has not been measured yet.
Compare `review_summary.json` and the stage-8 reject rates against a staged
run of similar words before scaling past a first slice.

## Size first

Agree the slice with the user before exporting. **Default: 8 senses, one
language.** Anything larger is a scope conversation: each sense is roughly one
long subagent turn of writing plus a review.

## The chain

| # | step | who |
|---|---|---|
| 0 | `python scripts/export_exercise_worklist.py --language ja --format csv --limit 8 --out-dir data/exercise_seeding/ja/fatseed_NN` | you |
| 1 | `brief RUN` → `RUN/fat_seed/briefs/core_NN.md` + `rules_core.md` | you |
| 2 | author the cores, then the variants, one subagent per brief | **author subagents** |
| 3 | `check RUN`: fix loop until `failed: 0` | you + authors |
| 4 | `review-pack RUN`, then hand off | **fat-seed-review** (fresh subagent) |
| 5 | `check RUN --source reviewed`, then `assemble RUN` | you |
| 6 | `upload_exercises.py` core → exercises `--no-render`, dry run first | you |
| 7 | stage 8 + render via `exercise_stage_runner.py` | batch-exercise-judging + you |

`status RUN` shows where every sense stands.

## Step 2: spawning the authors

One subagent per brief file (6 senses each by default; `brief --width N`).
They are independent, so launch them together in the background. The prompt
is the brief's path plus this skill's block reference, nothing about other
briefs:

> You are authoring vocabulary-ladder exercises for LinguaLoop. Work only
> from files; make no API calls.
>
> Phase 1: read `RUN/fat_seed/briefs/core_NN.md` and the rules file it names.
> Write `RUN/fat_seed/words/<sense_id>.json` (the `core` only) for every
> sense in it.
>
> Phase 2: run `PYTHONIOENCODING=utf-8 python scripts/fat_seed_runner.py plan
> RUN --senses <your ids>`. For each sense, read
> `RUN/fat_seed/plans/<sid>.json` and `RUN/fat_seed/rules_exercises.md`.
> Add `variants` to the same document: every block the plan lists for A and
> for B, in the shapes in `.claude/skills/fat-seed-authoring/SKILL.md`
> ("Block reference"). A plan with `"ok": false` means your core failed
> validation. Fix the core and re-run `plan` for that sense.
>
> Phase 3: run `… fat_seed_runner.py check RUN --senses <your ids>` and fix
> until every sense is `ok`. Report the final check line.

If the subagent's Bash is denied, run `plan` / `check` yourself and send the
output back to **the same subagent** with SendMessage. Its context holds the
sense and the rules; a fresh agent would re-derive them.

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
| `level_1` phonetic | `{"options": [4–8 options]}`. The correct option is the plan's `correct` (the headword); the distractors must sound like it (L1 is a **listening** exercise). For ja, pairs that differ only in pitch accent are NOT valid. Over-generate: a judge filters distractors and the item dies below 3 survivors. |
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

## Step 3: check

`check RUN` runs every gate the uploader runs: the P1 remap and validator,
tier screen, collocate grounding, the P2/P3 validators and the L4/L8/typed
schema gates. Errors name the variant and block (`[B] level_3: missing`).
Send each sense's errors to its author subagent. Repeat until
`check (words): {'ok': N}`, with skips allowed.

## Step 4: the review hand-off

`review-pack RUN` writes `RUN/fat_seed/review_packs/review_NN.md`. For each
pack, launch a **new** subagent whose entire prompt is:

> Use the fat-seed-review skill on run directory `RUN`, pack `review_NN.md`.

Nothing else: not what the authors struggled with, not which items worry you.
A reviewer who knows the authoring reasoning is already committed to it.

## Step 5: assemble

`check RUN --source reviewed`, then `assemble RUN`. It refuses to assemble if:

- **RUBBER STAMP**: the review changed nothing in any document. Re-run the
  review in a fresh context. Do not edit a document to get past it.
- A `rewrite` verdict has an unchanged document, or a reviewed document fails
  validation. That sense is dropped, with the reason in `07_upload/dropped.json`.

`reject` verdicts are dropped by design. `RUN/fat_seed/review_summary.json`
records what the review changed per sense. Report it to the user; it is the
quality signal for this path.

## Steps 6–7: upload, then the renderer's judges

Exactly as the staged chain (see `batch-exercise-authoring` §7–8). `assemble`
prints the upload commands with `--source-model claude-code:fat-seed`, so
fat-seed assets are distinguishable in `word_assets`. Dry run first, core
before exercises, **always `--no-render`**. Then:

1. `python scripts/exercise_stage_runner.py prepare RUN --stage 8`: hand off
   to `batch-exercise-judging` (fresh subagent), then `collect RUN --stage 8`.
2. `render RUN --dry-run`; repeat step 1 until `0 sense(s) blocked`.
3. `render RUN`, then verify:
   `select count(*), count(word_asset_id) from exercises where word_sense_id in (…)`.
   The two counts must be equal.

## Hard rules

- **You never author and never review.** Authors and the reviewer are
  separate subagents, and the reviewer never sees the authoring conversation.
- Never hand-edit `plans/`, `senses.csv`, `prompts.json` or `07_upload/`.
  A wrong plan is fixed in the core (`semantic_class`, `primary_collocate`,
  `morphological_forms`), never in the plan file.
- Mined sentences stay byte-identical, or they silently become `generated`.
- Never insert into `exercises`; never render a sense that already has rows.
- One run directory per slice, and never mix this path and the staged chain
  in the same `RUN`.
