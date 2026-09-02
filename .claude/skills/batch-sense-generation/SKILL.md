---
name: batch-sense-generation
description: Seed the word-sense dictionary in batches. Export the lemmas that have no definition, write two-level definitions for them yourself in this session, upload through the real sense write path, then embed. Use when asked to backfill senses, seed the dictionary, define missing vocabulary, or fix words with no definitions.
---

# Batch Sense Generation

**You write the definitions.** Not a subprocess, not a hosted model — you, in
this session. Python handles the database on both sides: one script exports the
lemmas that need defining, another writes your answers back through the real
sense write path.

Every lemma in `dim_vocabulary` is supposed to carry a *two-level* sense: a
`simple` row a young child could read, and a `standard` row that reads like a
dictionary. This workflow fills in the ones that don't have both.

This is the bulk dictionary path. Per-transcript work — deciding which sense of a
word a particular test passage uses — is `test-sense-linking`.

## Size the job first

Do this before exporting anything.

```sql
select l.language_code, count(*) as needs_seeding
from dim_vocabulary v join dim_languages l on l.id = v.language_id
where not exists (
  select 1 from dim_word_senses s
  where s.vocab_id = v.id and s.definition_level = 'simple'
    and s.definition_language_id = l.id)
group by l.language_code;
```

A few dozen lemmas is one sitting. A few thousand is not — say so and agree a
scope before starting, rather than discovering it at batch 40. The backlog grows
by every vocabulary row that test linking creates, so it will not be the same
number next week.

## Stage 1 — export

```bash
python scripts/export_sense_seed_worklist.py --language ja
python scripts/export_sense_seed_worklist.py --language ja --batch-size 25 --limit 100
```

Writes `data/sense_seeding/<lang>/batch_001.json`, `batch_002.json`, … Default 50
lemmas per file; 25–50 is comfortable to answer in one pass without truncating.

Each batch carries what you need and nothing else:

- `items[]` — `vocab_id`, `lemma`, `part_of_speech` (often null), and
  `existing_standard`
- `simple_register` — the child register the `simple` row must be written to,
  read live from `dim_complexity_tiers`
- `pos_legend` — the integer POS codes legal for this language

Lemmas whose primary sense is `source='manual'` are excluded at export. Someone
wrote those by hand; they are not yours to replace.

## Stage 2 — write the definitions (this is you)

Read one batch file. Write `batch_NNN.senses.json` beside it: one entry per item,
in any order, but **every `vocab_id` in the batch must get exactly one answer.**

```json
[
  {"vocab_id": 24791, "lemma": "すき", "part_of_speech": 3, "confidence": 0.95,
   "simple": "すきは、そのものやひとを、いいなとおもうきもちです。",
   "standard": "好き。ある物事や人に心が引かれ、快く感じること。",
   "example": "わたしはいちごがすきです。"},

  {"vocab_id": 24798, "lemma": "ローマ", "skip": true, "reason": "proper noun (place name)"}
]
```

### The two levels

`simple` and `standard` are not a short version and a long version of the same
sentence. They are written for different readers:

- **`simple`** — the register named in `simple_register` (roughly ages 4–9):
  everyday vocabulary, one idea per sentence, no term the definition itself would
  need to explain. A child should finish it knowing what the word means.
- **`standard`** — an ordinary dictionary definition. Precise, complete, names
  the genus and the distinguishing property. May use vocabulary a learner would
  look up.

Both are written **in the target language** — Japanese definitions for Japanese
words, Chinese for Chinese. Not English. Preserve kana, kanji and diacritics
exactly.

`example` is one short natural sentence that actually uses the word, at the
`simple` register. Keep it under about 60 characters.

`part_of_speech` is an **integer from that batch's `pos_legend`**, never a string.
Omit it rather than guess; a wrong POS is written back to `dim_vocabulary`.

`confidence` is 0–1 and is not decoration: below the validation threshold the row
is written with `is_validated = false`. Lower it honestly for a word you are
unsure of — that is the signal a reviewer filters on.

### When `existing_standard` is present

The word already has a standard definition and is missing only the simple one.
Your `standard` **overwrites** the existing wording at the same rank. Read what
is there first. Improve it if it is wrong or vague; otherwise stay close to it.
Rewriting a correct definition into your own phrasing churns the corpus for
nothing.

### When to skip

Emit `{"vocab_id": …, "skip": true, "reason": "…"}` for proper nouns, numerals,
symbols, and fragments that are not words. A skip is a real answer — it satisfies
the every-lemma rule and costs nothing.

## Stage 3 — upload

```bash
python scripts/upload_senses.py --batch-file data/sense_seeding/ja/batch_001.json \
  --senses-file data/sense_seeding/ja/batch_001.senses.json --dry-run
python scripts/upload_senses.py --batch-file data/sense_seeding/ja/batch_001.json \
  --senses-file data/sense_seeding/ja/batch_001.senses.json
```

Dry-run first, every time — it prints each definition as it will be written, and
reading them back is the last chance to catch a register or language slip.

Writes go through `SenseGenerator._write_two_levels`, which pairs the two rows at
one `sense_rank`, writes POS back to `dim_vocabulary`, runs the language check,
records `source_ref`, and embeds both levels.

Validation is fail-closed and aborts the batch before writing anything on: a
`vocab_id` not in the batch, a missing `simple` or `standard`, a `part_of_speech`
outside the legend, a duplicate, or **any lemma left unanswered**. Fix the file
and re-run. `--skip-invalid` drops the offending items and continues — reach for
it only when you have decided those items should be abandoned, never to get past
an error you have not read.

## Stage 4 — embed anything left without a vector

```bash
python -m scripts.backfill_sense_embeddings --language 3 --dry-run
python -m scripts.backfill_sense_embeddings --language 3
```

Language ids: zh 1, en 2, ja 3. Stage 3 embeds on create, so this is a net for
rows whose embedding call failed and for senses written before embed-on-create
existed. A sense without a vector is usable but silently degrades the distractor
mid-cosine band and `definition_match` — nothing errors, those features just get
worse. Idempotent, and cheap (~$0.02 per million tokens).

## Stage 5 — reattach, if tests were waiting on these words

```bash
python scripts/relink_deferred_vocab.py --language ja --dry-run
python scripts/relink_deferred_vocab.py --language ja
```

When inline enrichment was capped during test generation, the tail of a test's
vocabulary was recorded in `vocab_sense_stats.deferred_lemmas` with rows but no
senses. If you just gave those words senses, this attaches them to their tests.
No LLM calls. Skipping it leaves the deferral permanent.

## Verify

```sql
select definition_level, count(*), count(*) filter (where is_validated) as validated
from dim_word_senses s join dim_vocabulary v on v.id = s.vocab_id
where v.language_id = 3 and s.source_ref like 'claude-code:%'
group by definition_level;
```

The two levels must have equal counts. They are written as a pair, so any gap
means a batch went in half-applied.

## Hard rules

- **Never invent a `vocab_id`.** Only ids from the batch file. The uploader
  rejects anything else, but the reason it must is that a plausible wrong id
  writes a definition onto an unrelated word.
- **Every lemma gets an answer** — a definition or an explicit `skip`. Silence is
  rejected, because a dropped lemma looks identical to a lemma you decided
  against.
- **Both levels, always.** A standard-only row is exactly the drift the two-level
  treatment exists to prevent.
- **Target language, not English.**
- **One batch at a time**, through all of stage 2 and 3, before opening the next.
  Ten written batches and zero uploaded is ten batches of work with nothing to
  show and no way to tell which were reviewed.
- **Do not edit `prompt_templates` or `sense_generator.py`** to make a batch fit.
  If something cannot be expressed in the senses format, stop and say so.

## When to stop and ask

- The worklist is far bigger than the conversation expected — agree scope first.
- A batch is full of fragments, particles, or strings that are not words. That is
  an upstream extraction problem; defining them makes it permanent.
- Stage 3 reports a validation error you do not understand. `--skip-invalid` is
  not the answer to a message you have not read.
- Many lemmas arrive with an `existing_standard` that looks wrong. Two different
  problems — bad definitions and missing simple rows — and the second one is the
  only one this workflow is scoped to fix.
