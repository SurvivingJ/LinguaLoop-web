---
name: fat-seed-review
description: Review fat-seed exercise documents (one named-field JSON per word sense) written by another subagent — check the core and every exercise block against the live judge rules, fix what fails, and write a reviewed copy plus a verdict record per sense. Must run in a fresh context that has not seen the authoring. Use when handed a fat-seed review pack (RUN/fat_seed/review_packs/review_NN.md) or asked to review fat-seed JSON files.
---

# Fat-Seed Review

You are the quality step for documents someone else wrote. **You receive a
run directory and a pack name, and nothing else.** If this context contains
the authoring (you wrote the documents, or can see why they were written),
stop and say so. A reviewer that knows the generation reasoning is already
committed to it.

Be the strict one. This project found that swapping only the judge model
moved the zh distractor reject rate from 32% to 2%: the judge, not the
generator, decides quality. A pass that changes nothing is refused at
assemble as a rubber stamp. That does not mean "change something". It means
a review that finds no problems in N documents almost certainly did not look.

## What you read

- `RUN/fat_seed/review_packs/review_NN.md`: your senses and the output paths
- `RUN/fat_seed/rules_judges.md`: the live judge prompts. Their standards
  are yours; ignore their output formats.
- per sense: `RUN/fat_seed/words/<sid>.json` (the document) and
  `RUN/fat_seed/plans/<sid>.json` (the required blocks and each block's
  anchor sentence; `sentences` rows are `[index, text, target_word, source]`)

Do not open `briefs/`, `rules_core.md`, `rules_exercises.md`, any other pack,
or any conversation.

## What to check

**Core**
- Every sentence uses the word in **one** sense, the one `definition` and
  `sense_fingerprint` describe. A homograph, a compound that embeds the word,
  or a drifted sense fails.
- The `target_word` is the word as it actually appears in the text.
- Sentences fit the learner tier (length, grammar, abstraction) and `register`.
- `mined` sentences are corpus-attested: **never edit one.** If one is
  unusable, say so in `notes`; it cannot be fixed here.
- `primary_collocate` is a genuine fixed collocation (swapping in a synonym
  sounds wrong), or null. A topical co-occurrence is not a collocation.
- `pos` / `semantic_class` are right. If you change `semantic_class`,
  `primary_collocate` or `morphological_forms`, the required blocks may
  change. Run `PYTHONIOENCODING=utf-8 python scripts/fat_seed_runner.py plan
  RUN --source reviewed --senses <sid>` after writing the reviewed document,
  read `plans_reviewed/<sid>.json`, and add or remove blocks to match.

**Every option block**: exactly one option is correct and is the answer the
plan names. Every explanation is true. No distractor is also defensibly
correct in the anchor sentence. That last one is the most common real defect.

| block | the failure to hunt for |
|---|---|
| `level_1` | Distractors that don't sound like the headword, aren't real words, or (ja) differ only in pitch accent. L1 is a listening exercise. |
| `level_3` | A distractor that also fits the blank grammatically and in meaning. |
| `level_5` / `level_8` | A "non-collocate" that is actually idiomatic with the word; an `error_collocate` that isn't clearly wrong. |
| `level_6` | A "wrong" sentence that is actually acceptable, or wrong for a reason unrelated to the word. |
| `level_7` | More than one error; an error not involving the target; a "corrected" sentence that is still wrong. |
| `level_4` | A distractor form that is also grammatical there; `form_label` not matching the correct form. |
| `synonym_antonym_match` | The correct option not in the stated `relation` to **this sense**; a distractor that is in it (the polysemy trap). |
| `word_family` | A "non-word" distractor that is a real word; a wrong `part_of_speech`. |
| `particle_selection` | A second particle that also works; `blanked_particle` ≠ the correct option; missing or wrong `error_tags`. |

Also check that A and B are not copies of each other. If one is, rewrite B.

## What you write

For **every** sense in the pack, both files:

1. `RUN/fat_seed/reviewed/<sid>.json`: the full document with your fixes,
   same shape. If nothing needs fixing, copy it unchanged.
2. `RUN/fat_seed/review/<sid>.json`:

```json
{"sense_id": 53352,
 "verdict": "rewrite",
 "issues": [{"path": "variants.A.level_3.options[2]",
             "problem": "越す also fits: 限界を越す is grammatical and means the same",
             "fix": "replaced with 渡る"}],
 "notes": ""}
```

- `accept`: no changes (the reviewed file equals the original)
- `rewrite`: you changed something, and every change has an `issues` entry
- `reject`: the core is unusable (wrong sense throughout, broken
  sentences); the sense is dropped. Do not reject for a fixable block.

Then run `PYTHONIOENCODING=utf-8 python scripts/fat_seed_runner.py check RUN
--source reviewed --senses <your ids>` and fix until every sense is `ok`.
Finish by reporting: the verdict counts, the check line, and the one or two
most common defect types you found.

## Hard rules

- Never edit `words/`, `plans/` or anything outside `reviewed/` and `review/`.
- Never edit a `mined` sentence.
- Every sense in the pack gets both files.
- Do not soften a finding to avoid a rewrite.
