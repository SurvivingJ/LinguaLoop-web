---
title: CSV Exercise Authoring — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./csv-exercise-authoring.md
last_updated: 2026-09-20
dependencies:
  - "script: scripts/upload_exercises.py (extended by TASK-799 with an llm_types_<v> path; otherwise unchanged)"
  - "script: scripts/exercise_stage_runner.py + services/vocabulary_ladder/stage_runner.py (TASK-797)"
  - "renderer: LadderExerciseRenderer.render_all"
  - "table: word_assets, exercises, dim_word_senses, dim_exercise_capabilities"
  - "prompt_templates: vocab_prompt1_core, vocab_prompt2_exercises, vocab_prompt3_transforms, ladder_* generators and judges"
breaking_change_risk: low
---

# CSV Exercise Authoring — Technical Specification

> **Built 2026-09-19 (TASK-795–799), with two corrections to this spec, both
> agreed with the user before building:**
>
> 1. **The level plan is not a stage-0 column.** `active_levels`,
>    `p3_expected_levels` and the collocate grade are functions of the *P1
>    answer*: `active_levels_for_context(semantic_class, lang,
>    capability_context_from_core(core))` reads P1's semantic_class, morph-form
>    count and pronunciation, and the L5 gate grades P1's own
>    `primary_collocate`. None of them exist before stage 1. They are computed
>    at a new deterministic **stage 2b (`bridge`)**, after the core judge, by
>    the same functions (`upload_exercises.prepare_core` →
>    `export_exercise_worklist.build_exercise_item`), and written to
>    `plan.csv`. Consequence for §5: 2b also reads the DB (grounding, template
>    configs). Nothing but the upload writes.
> 2. **Typed levels needed an upload path.** `upload_exercises.py` had no
>    `llm_types_*` writer, so stage 5's syn/ant / particle / word-family answers
>    had nowhere to land. The user chose to extend the uploader (TASK-799)
>    rather than defer them; "nothing downstream changes" is therefore true of
>    the renderer and the tables, not of the uploader.
>
> 3. **No API calls anywhere (user rule, 2026-09-19).** The uploader's render
>    step calls the hosted judge models. Assets are therefore uploaded with
>    `--no-render`, and a **stage 8** answers the renderer's own judge requests
>    by subagent: `prepare --stage 8` runs the real renderer over the stored
>    assets and records every request, and `render` rebuilds the rows with
>    `replay_llm_calls` returning the stored answers. A sense with any
>    unanswered request is not inserted (repeat stage 8 until the dry run is
>    clean), and `random` is seeded per sense because the ja L1 trie shuffles.
>    Verified on 8 ja senses: 153 rows, all linked (TASK-800).
>
> Also: `ladder_sentence_validity_judge` judges the L6/L7 *wrong* sentences,
> which do not exist at stage 2 — it fires at stage 6, from the renderer. Stage
> 2 is `ladder_p1_sentence_judge` alone.
>
> Operator docs: `.claude/skills/batch-exercise-authoring` and
> `.claude/skills/batch-exercise-judging`. Tasks:
> [[tasklist/csv-exercise-authoring.tasks]].

> **Revised 2026-09-19.** The first draft of this page specified a single fat
> pass per sense and accepted three quality losses for it (no mined sentences,
> no L5, no judges). That was wrong on the second point and unnecessary on all
> three. **Anything the database knows can be a column in the export.** The
> boundary is not "offline means degraded"; it is "one rich export up front,
> then everything runs locally". This page now specifies the staged chain.

Run the existing prompt chain locally, stage by stage, across the whole sense
list at once — `vocab_prompt1` over every sense, judge, `vocab_prompt2` over
every sense, judge, and so on — then emit the asset payloads for upload.

---

## 1. Why staged beats one fat pass

| | fat pass (per sense) | **staged (per prompt, all senses)** |
|---|---|---|
| prompt chain | collapsed — prompt 2 inlined after prompt 1 | **preserved verbatim** |
| judges | dropped | **all of them run** |
| prompt fidelity | a merged prompt nobody has validated | the live `prompt_templates` text, version-pinned |
| context cost | prompt re-read once per sense | **one instruction + N items per call** ([[batch-prompting-item-envelope]]) |
| failure isolation | one bad sense can derail its own whole chain | a stage fails for a sense; other stages and senses are unaffected |

The staged shape is also the one the codebase already trusts: it is the live
pipeline's own ordering, executed by a model in-session instead of by ~13
serial API calls ([[evaluations/preteach-variants-2026-09-19]] §8).

---

## 2. Stage 0 — one rich export (the only DB step)

Everything the prompts need that the database knows is exported **once**, up
front. This is what makes the rest genuinely local, and it is what the previous
draft missed.

`scripts/export_exercise_csv.py --language ja --limit N --out data/exercise_seeding/ja/senses.csv`

### 2.0 Mining: bulk-export the tests, mine locally, reuse the miner

`_fetch_corpus_sentences` ([`asset_pipeline.py:668`](../../services/vocabulary_ladder/asset_pipeline.py#L668))
is **already** two separable halves, which is what makes bulk local mining a
refactor rather than a rewrite:

| half | what it is | where it belongs |
|---|---|---|
| `tests_containing_sense(sense_id, language_id)` RPC | GIN lookup on `tests.vocab_sense_ids` plus the surface tokens in `tests.vocab_token_map` | **deterministic SQL — bulk export it once for all senses** |
| `TranscriptMiner` + `LanguageProcessor` + `screen_sentence` / `tier_for_lemma` | markup-strip, tier-screen against the sense's own band, dedupe, tag `sentence_source='mined'` | **already pure Python — import it, run it locally** |

Today they are called one sense at a time, so 500 senses is 500 round trips.
Split them:

```
tests_containing_sense(...)          -> export once, all senses   (SQL)
mine_sentences(rows, lemma, tier)    -> pure, local, unchanged    (Python)
```

**Nothing is reimplemented.** The local miner calls the same
`TranscriptMiner` and the same `screen_sentence` against exported rows instead
of RPC results, so a mined sentence is byte-identical to what the live pipeline
would produce — which matters, because the uploader tags a sentence `mined`
only on an exact match after normalisation, and any drift silently downgrades it
to `generated`.

The `vocab_token_map` is load-bearing here: it supplies the *surface tokens*
that realise a sense, which is how an inflected or segmented occurrence is
matched without the `\b` regex CJK cannot support. Export it, do not try to
re-derive matching from the lemma. (It is jsonb with no FK and has been
orphaned before — see [[sense-deletions-must-check-token-maps]].)

Mining already degrades to `[]` on any failure, and P1 then writes all ten
sentences. That fallback is correct and must be preserved locally.

### 2.1 Call the pipeline functions; do not re-express the gates in SQL

Stage 0 is a Python script, and most of it already exists. Three of its columns
are **not** table reads — they are pipeline logic:

- `corpus_sentences` ← `pipeline._fetch_corpus_sentences(sense_id, language_id)`
- `active_levels` / `p3_expected_levels` ← the `dim_exercise_capabilities` gates
  plus the L5 corpus PMI gate
- `primary_collocate` / `collocate_grade` ← the PMI grounder

`export_exercise_worklist.py` already calls all of them
([`export_exercise_worklist.py:226`](../../scripts/export_exercise_worklist.py#L226)).
**Stage 0 should be a `--format csv` output mode on that script, not a new set
of SQL queries.** Hand-writing SQL that reproduces a capability gate creates a
second copy of a rule that already moved once — the same drift the previous
draft's static level table introduced, re-entering by a different door.

Plain SQL is right for the *sense selection* half (which senses, in what demand
order — [`export_ja_senses_no_exercises.sql`](../../scripts/sql/export_ja_senses_no_exercises.sql));
it is wrong for the derived columns.

| column | source | why it must be exported |
|---|---|---|
| `sense_id`, `lemma`, `reading`, `part_of_speech`, `definition` | `dim_word_senses` ⋈ `dim_vocabulary` | identity; `definition` disambiguates a polysemous headword |
| `zipf`, `level_tag`, `semantic_class` | `dim_vocabulary` | tier and level plan |
| **`corpus_sentences`** (JSON array) | `pipeline._fetch_corpus_sentences(sense_id, language_id)` | **mined, attested usage.** A DB query, therefore exportable — so nothing is given up. Without this column every sentence would be `generated` |
| **`active_levels`, `p3_expected_levels`** (JSON) | live `dim_exercise_capabilities` + the L5 corpus PMI gate | the level plan the validator will hold the author to. Computed by the *live* gates, not a static table copy |
| `primary_collocate`, `collocate_grade` | the PMI grounder | lets L5 survive when it is genuinely attested |
| `pos_set`, `semantic_class_enum`, `sentences_required` | per-language validation block | the enums the uploader enforces |
| `prompt_version` | `prompt_templates` | pins what the author answered against |
| `blocks_n_tests` | demand ranking | ordering only |

Because `active_levels` and the collocate come from the live gates rather than
a hand-maintained table, **§3.2 of the previous draft is deleted** along with
the drift risk it carried. L5 is dropped per-sense when the PMI gate says so,
not categorically.

The prompt texts are exported alongside as `prompts.json`, version-pinned. No
hand-copied prompt goes in the skill.

---

## 3. Stages 1..N — the local chain

Each stage reads the previous stage's output file and writes its own. Every
stage is `N` items per call via the `item_N` envelope — position keys, not
sense ids ([[batch-prompting-item-envelope]]).

| # | stage | prompt | writes |
|---|---|---|---|
| 1 | core | `vocab_prompt1_core` | `01_core.json` |
| 2 | **judge core** | `ladder_p1_sentence_judge` | `02_core.judged.json` |
| 2b | **bridge** (deterministic, DB read) | — `prepare_core` + `build_exercise_item(include_typed=True)` | `02b_plan.json`, `plan.csv` |
| 3 | exercises A/B | `vocab_prompt2_exercises` | `03_exercises.json` |
| 4 | transforms A/B | `vocab_prompt3_transforms` | `04_transforms.json` |
| 5 | split levels | `ladder_l4_morphology_generation`, `ladder_l8_collocation_repair_generation`, `ladder_syn_ant_generation`, `ladder_particle_selection_generation` (ja), `ladder_word_family_generation` (en) | `05_split.json` |
| 6 | **judge items** | whatever `LadderExerciseRenderer.build_rows` fires: `ladder_l1_distractor_judge`, `ladder_collocation_judge`, `ladder_sentence_validity_judge`, `ladder_relation_judge`, `ladder_word_family_judge`, `ladder_particle_judge` | `06_items.judged.json` |
| 7 | assemble | — (deterministic) | `07_upload/batch_NNN.{core,exercises}.batch.json` + `batch_NNN.{core,exercises}.json` (answers) + `dropped.json` |

**How the prompts are produced (as built).** Stage 1's prompt is the CSV's
`p1_prompt`. Stages 3–5 are the prompts `build_exercise_item` renders at 2b.
The judge prompts at stages 2 and 6 are **captured**, not rebuilt:
`stage_runner.capture_llm_calls()` swaps `call_llm` in every loaded
`services.*` module for a recorder that raises, then the runner calls
`VocabAssetPipeline._judge_p1_sentences` (stage 2) or runs
`LadderExerciseRenderer.build_rows` over the not-yet-stored assets (stage 6).
Every judge fails open outside batch mode, so the calling code completes, and
the recorded prompts are exactly what the live judge models would get. No
judge prompt construction is copied.

**Units, rounds, retries.** A unit is a sense (stages 1, 2, 6) or a
`sense:variant:part` (3–5; part ∈ `p2 p3 l4 l8 typed:<code>`). `prepare`
writes `stageK/round_NN/call_NNN.prompt.md` (item_N envelope from
`services.batch_prompting`); answers go in `call_NNN.response.json`;
`collect` validates per unit and merges into `0K_*.json`. A retry is
`prepare --senses …` → a new round (always max+1); later rounds overwrite only
their own units. Stage 3–5 answers are validated by
`upload_exercises.prepare_exercises` when stage 6 is prepared; a failing sense
is recorded as blocked with the validator's message.

A stage that fails for one sense marks that sense and continues. Senses missing
a required upstream answer are dropped at stage 7 with a reason, not carried
forward half-built.

### 3.1 Two skills, not one — the split is structural

- **`batch-exercise-authoring`** runs stages 1, 3, 4, 5 and 7. It writes.
- **`batch-exercise-judging`** runs stages 2 and 6. It reviews and rewrites.

They are separate skills rather than separate stages of one skill because the
separation has to survive a tired operator. A single skill that *says* "now
judge your own work in a fresh context" is one shortcut away from being a
rubber stamp; two skills cannot share a context by construction.

The judging skill takes the authoring skill's output files and the judge
prompts, and nothing else — no access to the authoring transcript.

### 3.2 The judge passes must not run in the generating context

This is the one place the design can quietly fail.

A model that has just written an item, and can see why it wrote it, is not an
independent judge of that item — it is already committed. The project has
direct evidence that judging is not a formality: swapping only the judge model
moved the zh distractor reject rate **32% → 2%**
([[distractor-judge-v3-likert]]), and a closed enumeration inside a judge
prompt silently acts as an allow-list ([[ja-l1-judge-and-generator-doctrine]]).

**Requirement:** stages 2 and 6 run in a **fresh context** — a subagent, or a
separate skill invocation — given only the artifacts and the judge prompt,
never the generation reasoning. A judge pass in the authoring context is
recorded as *not run*.

**The judge's verdict is applied, not narrated.** Stage 2/6 output carries the
rewritten item plus `{judged: true, verdict, changed: bool}` per item, so the
rework is auditable and a rubber-stamp pass (all `changed: false`) is visible
as the anomaly it would be.

---

## 4. The final artifact — one correction worth making

> **The DB's "correct structure" is `word_assets`, not `exercises`.**

`exercises` rows are not authored. They are **rendered deterministically** by
`LadderExerciseRenderer.render_all` from the assets — and the render is what
attaches `word_asset_id`. Emitting exercise rows directly and inserting them
produces exactly the class of item TASK-512 removed: vocabulary exercises with
no asset linkage, invisible to the ladder's provenance and regeneration paths.

So stage 7 emits the two files the **existing** uploader already reads, and
nothing downstream changes:

```bash
python scripts/upload_exercises.py --stage core \
  --batch-file  data/exercise_seeding/ja/batch_001.json \
  --answers-file data/exercise_seeding/ja/batch_001.core.json --dry-run
# then without --dry-run, then the same pair for --stage exercises
```

The uploader performs the same `PROMPT1_KEY_MAP` remap, the same schema gate on
the split L4/L8 fragments, the same fail-closed validation, the same upsert, and
then calls the renderer. **No new write path.**

If a flat CSV of the rendered exercises is wanted for review, produce it *after*
the render, as an export — never as the input.

> `render_all` is a plain insert with **no de-duplication**. Re-rendering a
> sense that already has rows duplicates them. Clear the old rows first or pass
> `--no-render`.

---

## 5. What is actually given up

Only one thing, and it is procedural rather than qualitative:

- **Stage 0 needs database access.** Everything after it is local. A sense
  cannot be authored from a lemma and a definition alone, because
  `active_levels`, the PMI gate and the mined sentences are all facts about the
  corpus, not about the word.

The three losses the previous draft accepted are all recovered: mined sentences
become a column (§2), L5 survives where the gate allows it (§2), and the judges
run (§3).

---

## 6. Testing Strategy

- Stage 0's CSV round-trips: for 8 senses, the exported `active_levels`,
  `corpus_sentences` and `pos_set` match what `export_exercise_worklist.py`
  produces for the same senses. Assert on a captured pair so export-format drift
  fails loudly here.
- Stage 7's output validates byte-identically in shape to a hand-run
  `batch-exercise-generation` answers file.
- A judge stage whose output has `changed: false` on **every** item fails the
  run — that is the rubber-stamp signature, not a clean batch.
- A sentence not containing its target word is rejected at `--dry-run`, before
  any write. Validation is already fail-closed per batch.
- End-to-end on 8 ja senses: CSV → stages → `--dry-run` → real → confirm
  `count(word_asset_id) = count(*)` on the new `exercises` rows.
- POS is UniDic for ja (`形状詞`, never Simplified `名词`); assert the enum.

## 7. Open Questions

- **OPEN.** Batch width `N` per call, per stage. Stage 1 (10 sentences/sense) is
  far heavier than stage 6 (judge a few options). `N` should be per-stage, and
  the live skill's 8-senses default was chosen for stage 1 only. Measure before
  scaling a run. *Built defaults:* `DEFAULT_WIDTH = {1: 8, 2: 8, 3: 8, 4: 8,
  5: 12, 6: 4}`; the 8-sense e2e produced 83 KB (stage 1) and ~87 KB (stage 3)
  call files at those widths.
- **ANSWERED 2026-09-19 — gate.** A judge `reject` drops the sense at 2b / 7; a
  sense stage 6 never judged cannot be assembled; an all-unchanged judge pass
  exits 1 and `require_judged` refuses it. `changed` is checked against the
  diff, so a judge cannot claim a rewrite it did not make.
- **ANSWERED 2026-09-19 — stage 1 assigns it.** The P1 answer's
  `semantic_class` is authoritative, and it is also why the level plan moved to
  2b (correction 1 above). `dim_vocabulary.semantic_class` is exported only as
  a hint. It can be wrong in a way that matters: 作業/循環 carry `action` there,
  which planned an L4 conjugation a noun cannot have. **Fixed 2026-09-20 (TASK-801):**
  the ja `morphology_slot` capability row also requires `inflecting_pos`, derived from
  P1's `pos` (名詞 and other non-inflecting POS fail it; 動詞/形容詞/形状詞 pass). The
  gate lives in `capability_context_from_core`, shared by pipeline, exporter and renderer.
- **ANSWERED 2026-09-20 — L1 target (TASK-803).** L1 keys its candidates on P1's
  `pronunciation` and names its answer with `LadderExerciseRenderer._headword`
  (`dim_vocabulary.lemma`), not `_lemma` (a sentence's target, an inflected stem
  for ja verbs). `_lemma` still feeds the deterministic types unchanged.

## Related Pages

- [[features/lookahead-preteaching.tech]] — §7, the demand this content serves
- [[evaluations/preteach-variants-2026-09-19]] — the sizing behind it
- [[features/exercises.tech]] — the asset → renderer → `exercises` chain
- [[algorithms/vocabulary-ladder]] — rings, levels, families
