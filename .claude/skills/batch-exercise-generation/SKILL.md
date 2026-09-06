---
name: batch-exercise-generation
description: Build vocabulary-ladder exercises in batches for senses that have none. Export the senses with no exercises together with the live generation prompts, answer those prompts yourself in this session, upload through the real word_assets write path, then render the exercise rows. Use when asked to backfill exercises, seed the ladder, build practice items for words, or fix senses with no exercises.
---

# Batch Exercise Generation

**You write the exercises.** Not a subprocess, not a hosted model — you, in
this session. Python handles the database on both sides and hands you the
*actual production prompt*: `scripts/export_exercise_worklist.py` renders the
live `prompt_templates` row through the real generator object, so what you
answer is byte-identical to what the hosted model would be sent, at the same
template version. `scripts/upload_exercises.py` then does the same remapping,
the same deterministic post-processing and the same validation the pipeline
does, and writes the result back.

Do **not** route this through `claude -p`, `--provider claude-cli`, or
`run_content_build.py` — those are the automated path, and at ~5.5 min/sense
the automated path is the reason the backlog exists.

This is the bulk ladder path. Per-word admin work and anything needing the
LLM judges is still the automated pipeline's job.

## You are authoring assets, not exercise rows

Never insert into `exercises` directly. TASK-512 made the vocabulary ladder
the sole vocab generator precisely because its items carry `word_asset_id`,
which legacy vocab exercises never did. The chain is:

    word_assets.prompt1_core          <- you write this (stage: core)
      └─ prompt2_exercises_A / _B     <- you write these (stage: exercises)
      └─ prompt3_transforms_A / _B    <- you write these (stage: exercises)
           └─ LadderExerciseRenderer  <- deterministic, run by the uploader
                └─ exercises rows

`LadderExerciseRenderer` also produces the levels no prompt owns — L2
definition_match from the database, L9 jumbled locally — so a correct asset
set yields more exercises than you wrote answers for. That is expected.

## Two stages, because the prompts chain

Prompt 2 and Prompt 3 are both rendered *from* Prompt 1's output. A sense
therefore needs a valid `prompt1_core` before its exercise prompts can be
built at all. The export enforces this: `--stage core` selects senses with no
exercises **and** no valid core; `--stage exercises` selects senses that now
have a valid core but still no exercises. Run core → upload → exercises →
upload, per batch.

## Size the job first

```sql
select l.language_code,
       count(*) filter (where ex.word_sense_id is null) as no_exercises
from dim_word_senses s
join dim_vocabulary v on v.id = s.vocab_id
join dim_languages l on l.id = v.language_id
left join (select distinct word_sense_id from exercises
           where word_sense_id is not null) ex on ex.word_sense_id = s.id
where s.definition_language_id = v.language_id
group by 1 order by 1;
```

As of 2026-09-04: **en 10,578 · zh 8,031 · ja 7,118 — 25,727 senses with no
exercises**, against 57 senses that have assets at all. That is not one
sitting, and it is not a hundred sittings either.

What makes it tractable is the ranking. The export orders by how many *active
tests* reference the sense, and only test-referenced senses are in the pool by
default. For `ja` that pool is **665 senses**, not 7,118 — the words learners
actually meet. The export logs both numbers every run; read them before
committing to a scope, and **agree the scope with the user** before going past
a first `--limit` slice.

`--include-unreferenced` extends the pool to senses no test uses. Reach for it
only when the ranked pool is exhausted — a sense no test references earns
assets last.

## Stage 1 — export the core worklist

```bash
python scripts/export_exercise_worklist.py --language ja --stage core --limit 24
python scripts/export_exercise_worklist.py --language ja --stage core --batch-size 8
```

Writes `data/exercise_seeding/<lang>/batch_001.json`, … Default 8 senses per
file — one ladder sense is roughly ten gloss items of writing, so 8 is what
fits in a pass without truncating.

Each item carries what you need and nothing else:

- `prompt` — the live `vocab_prompt1_core` template, already filled with the
  lemma, tier, existing definition and the mined corpus sentences
- `corpus_sentences` — what transcript mining found, kept so the uploader can
  derive `sentence_source` the way the generator does
- `sentences_needed` — how many you must write beyond the mined ones
- the batch header's `validation` block — the POS and semantic-class enums the
  validator will actually hold you to, and `sentences_required`

## Stage 2 — answer the core prompt (this is you)

Read one batch file. Answer each item's `prompt` exactly as it asks — **the
raw numeric-keyed JSON, in that prompt's own contract**. Do not translate the
keys to descriptive names; the uploader runs `PROMPT1_KEY_MAP` over your
answer, the same remap the generator runs, and descriptive keys would pass
through unmapped.

Write `batch_NNN.core.json` beside the batch file: one entry per item, in any
order, but **every `sense_id` in the batch must get exactly one answer.**

```json
[
  {"sense_id": 35053, "answer": {
     "1": "动词", "2": "action", "3": "ある動作や行為を行うこと。", "4": null,
     "5": "する", "6": "/sɯɾɯ/", "7": 2,
     "8": [{"1": "…", "2": "し", "3": "corpus", "4": "T3", "5": ""}],
     "9": [{"1": "する", "2": "辞書形"}],
     "10": "plain", "11": "动词 | 動作・行為を行う"}},

  {"sense_id": 35069, "skip": true, "reason": "proper noun"}
]
```

### The things that actually fail

- **`sentences` must be exactly `sentences_required` long** (10). Mining often
  supplies all 10 — then `sentences_needed` is 0 and you keep them unchanged.
  Keep mined sentences *verbatim*: the uploader tags a sentence `mined` only
  on an exact match after whitespace/case normalisation, and a light rewrite
  silently downgrades it to `generated`.
- **Every sentence's target word must actually appear in its text.** The
  validator does a whole-word check (a contiguous-substring check for CJK).
  This is the most common rejection.
- **POS must come from the batch's `pos_set`** — the header prints the exact
  set the validator will hold you to, so read it rather than assuming. For
  `ja` it is the **UniDic tagset**: `名詞`, `動詞`, `形容詞`, `形状詞`, `副詞`,
  `助詞`, … Note `形状詞` for na-adjectives, which has no EN or ZH counterpart.
  Do not write Simplified Chinese labels (`名词`, `动词`) — they are a
  different language's tagset and are rejected. A handful of ja assets
  generated before 2026-09-04 carry the Simplified forms; they are the bug
  this enum closed, not the standard.
- **`semantic_class` is a closed enum**: `concrete`, `abstract`, `action`,
  `property`, `function`, `proper`. It decides which ladder levels the sense
  gets, so a careless label silently changes the exercise set.
- **`primary_collocate` defaults to `null`.** Assert one only when the word
  really has a fixed partner. An unattested collocate is graded
  `llm_asserted` by the grounder, warns on upload, and gets L5 dropped anyway.

### When to skip

Emit `{"sense_id": …, "skip": true, "reason": "…"}` for proper nouns, symbols,
and fragments that are not words. A skip is a real answer — it satisfies the
every-item rule.

## Stage 3 — upload the core

```bash
python scripts/upload_exercises.py --stage core \
  --batch-file data/exercise_seeding/ja/batch_001.json \
  --answers-file data/exercise_seeding/ja/batch_001.core.json --dry-run
python scripts/upload_exercises.py --stage core \
  --batch-file data/exercise_seeding/ja/batch_001.json \
  --answers-file data/exercise_seeding/ja/batch_001.core.json
```

Dry-run first, every time. It prints POS, semantic class, sentence count and
every warning — the tier-gate screen and the collocate grounding both run here
and report, and reading them back is the last chance to catch a register slip.

The upload remaps, derives `sentence_source`, screens each sentence against
the lemma's tier band, grades the collocate, validates with
`VocabAssetValidator`, upserts `prompt1_core`, then writes POS /
`semantic_class` / phonetics back to `dim_vocabulary` and `dim_word_senses` —
the same side effects `VocabAssetPipeline` has.

Validation is fail-closed for the whole batch: nothing is written if any sense
fails, so a batch is never half-applied. `--skip-invalid` drops the offending
senses and continues — reach for it only when you have decided those senses
should be abandoned, never to get past an error you have not read.

## Stage 4 — export the exercise worklist

```bash
python scripts/export_exercise_worklist.py --language ja --stage exercises
```

Only senses whose core you just landed will appear. Each item carries the
derived level plan and, per variant **A** and **B**, the filled prompts:

- `p2.prompt` — `vocab_prompt2_exercises`, covering the active levels among
  L1 phonetic / L3 cloze / L5 collocation gap / L6 semantic discrimination
- `p3.prompt` — `vocab_prompt3_transforms`, L7 spot-incorrect
- `l4.prompt` / `l8.prompt` — the split morphology / collocation-repair
  prompts, present only where their capability rows fire

A and B differ only in which of the core's 10 sentences each level draws on
(`sentence_assignments`), which is what makes two distinct exercises per level.
**Answer them independently.** Copying A's answer into B produces two identical
items about different sentences, which is worse than one item.

`active_levels` and `p3_expected_levels` in the item are the level lists the
validator will hold you to. They are often narrower than the full ladder and
that is correct: L5 is dropped unless the collocation passes a corpus PMI
gate, and L4 is dropped for a sense whose type gate has no enabled row — a ja
abstract noun keeps L4 in `active_levels` but not in `p3_expected_levels`,
because ja morphology is served elsewhere. Answer what the variant actually
contains, nothing more.

## Stage 5 — answer the exercise prompts (this is you)

Write `batch_NNN.exercises.json`. Same numeric-key rule, one entry per sense,
both variants:

```json
[
  {"sense_id": 35005,
   "A": {"p2": {"1": [{"1": "たくさん", "2": true,  "3": "正解の説明。"},
                      {"1": "たくざん", "2": false, "3": "誤答の説明。"}],
                "3": [],
                "6": {"1": 3, "2": [{"1": "…", "2": "…"}]}},
         "p3": {"7": {"1": "誤文", "2": "正文", "3": "誤りの説明", "4": [0, 1, 2]}}},
   "B": {"p2": {}, "p3": {}}}
]
```

Option levels (L1/L3/L5/L8) take a **list** of `{"1": text, "2": is_correct,
"3": explanation}`. L6 takes `{"1": correct_sentence_index, "2": [{"1": text,
"2": explanation}]}`. L7 takes `{"1": incorrect, "2": corrected, "3":
description, "4": correct_indices}`.

Non-negotiable, because the validator enforces them:

- **Exactly 4 options**, exactly one correct, every option with a non-empty
  explanation — for every option level except L1.
- **L1 may carry 4–8 options.** It is the one level whose distractors are
  individually judged downstream, and the renderer drops the whole variant if
  fewer than 3 distractors survive. Write extras; the learner still sees 4.
- **L6 needs 3 wrong sentences.**
- **L7's incorrect and corrected sentences must differ.**

## Stage 6 — upload and render

```bash
python scripts/upload_exercises.py --stage exercises \
  --batch-file data/exercise_seeding/ja/batch_001.json \
  --answers-file data/exercise_seeding/ja/batch_001.exercises.json --dry-run
python scripts/upload_exercises.py --stage exercises \
  --batch-file data/exercise_seeding/ja/batch_001.json \
  --answers-file data/exercise_seeding/ja/batch_001.exercises.json
```

The uploader remaps P2 and P3, schema-gates the split L4/L8 fragments against
their own prompt version, merges the whole P3 family into one
`prompt3_transforms_<variant>` asset (the shape the renderer reads), validates
each, upserts them, then calls `LadderExerciseRenderer.render_all` and reports
how many exercise rows landed. `--no-render` stores assets without rendering.

`render_all` is a plain insert with no de-duplication. Re-rendering a sense
that already has rows duplicates them — clear the old rows first, or use
`--no-render`.

## Verify

```sql
select e.exercise_type, count(*), count(e.word_asset_id) as linked
from exercises e
join dim_word_senses s on s.id = e.word_sense_id
join dim_vocabulary v on v.id = s.vocab_id
where v.language_id = 3 and e.created_at > now() - interval '1 day'
group by 1 order by 2 desc;
```

- Every rendered vocab exercise must carry a `word_asset_id`. A null one means
  something wrote to `exercises` outside the ladder.
- Expect ~2 rows per active level per sense (variants A and B), plus the
  deterministic L2 and L9 the renderer adds for free.
- `rendered 0 exercises` on an upload that reported stored assets means the
  core asset is missing or invalid for that sense — check `word_assets`, do not
  re-answer the exercise prompts.

## Scope limit — the typed LLM levels

`llm_types_A` / `llm_types_B` (synonym-antonym match, word family, particle
selection) are **not** authored here. They are per-type prompts with their own
registry, and the renderer treats a missing typed asset as "no applicable
types for this word" — those levels simply do not render. Everything else
does. If a language needs them, that is the automated pipeline's job; say so
rather than hand-rolling them into a `prompt3_transforms` asset, where the
validator does not expect them.

## Hard rules

- **Never invent a `sense_id`.** Only ids from the batch file. The uploader
  rejects anything else, but the reason it must is that a plausible wrong id
  writes assets onto an unrelated word.
- **Every sense gets an answer** — a full answer or an explicit `skip`.
  Silence is rejected, because a dropped sense looks identical to a sense you
  decided against.
- **Answer in the prompt's numeric contract**, not in descriptive keys. P1/P2/P3
  are 1-based; the split L4/L8 prompts are 0-based with 9 reserved as the error
  escape. They are deliberately different numberings — do not unify them.
- **Both variants, every active level.** A one-variant sense halves the
  learner's item pool for that word.
- **Target language, not English** — for definitions, sentences and
  explanations alike.
- **One batch at a time**, through the whole core → exercises cycle, before
  opening the next.
- **Never insert into `exercises` directly**, and never edit `prompt_templates`,
  the generators, or `VocabAssetValidator` to make a batch fit. If something
  cannot be expressed in the prompt's contract, stop and say so.

## When to stop and ask

- The worklist is far bigger than the conversation expected — agree scope
  first (see "Size the job" above).
- The ranked pool is empty and only `--include-unreferenced` would find work.
  That is a scope decision, not a default.
- A batch is full of senses whose definitions look wrong. Bad definitions and
  missing exercises are two different problems, and this workflow only fixes
  the second — [[batch-sense-generation]] owns the first.
- The validator rejects something you are confident is right. Read the actual
  enum or count in the error before deciding whether the answer or the gate is
  wrong. If a ja batch rejects every POS, check that
  `migrations/ja_p1_pos_enum_unidic.sql` has been applied — the prompt and the
  validator are a matched pair, and ja P1 fails 100% if only one of them has
  landed.
- Mining returned few or no corpus sentences for most of a batch. The ladder
  will still build, but the sentences will be entirely yours — worth surfacing
  rather than quietly generating a corpus.
