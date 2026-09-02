---
name: cross-language-glosses
description: Write cross-language gloss definitions for the sense dictionary — a definition of a word rendered in a DIFFERENT language than the word's own, for a learner reading their L1. Export the senses that need one, write the glosses yourself in this session, upload through dim_word_senses, then re-embed. Use when asked to gloss vocabulary into another language, fix cross-language definitions, or generate L1 equivalents for existing senses.
---

# Cross-Language Glosses

**You write the glosses.** Not a subprocess, not a hosted model — you, in this
session. `services/vocabulary/gloss_generator.py`'s old hosted "translate this
definition" prompt is retired: it produced sentence-length prose for what
should be a short equivalent set (緊張 → a 145-character English paragraph
instead of "tension; nervousness"). Do **not** route this through `claude -p`,
`--provider claude-cli`, or any other automated call — that is the same
mistake in a different wrapper.

A gloss is a `dim_word_senses` row whose `definition_language_id` differs from
the word's own `dim_vocabulary.language_id` — e.g. an English definition of a
Japanese word, for a learner whose L1 is English. This is separate from
[[batch-sense-generation]], which writes a word's definition in its OWN
language. It is also separate from [[test-sense-linking]], which links
transcript words to existing senses.

## Parse the arguments first

Invoked as:

    /cross-language-glosses source=en target=zh,ja

`source` is the word's own language — the words being glossed. `target` is one
or more languages to write the definitions **in**. Both are required, and both
must be one of `zh`, `en`, `ja`. **If either is missing, stop and ask** — do
not guess a pairing from conversation context. `target` must not include
`source` (you cannot gloss English words into English).

## The target format

Two levels, selected by the learner's tier at serve time (see
`services/vocabulary/gloss_lookup.py` — not your concern here, it just
substitutes level-for-level once the rows exist):

- **`simple`** — the single best equivalent. One word or short phrase.
  緊張 → `"tension"`. 場所 → `"place"`.
- **`standard`** — the full equivalent set, plus a clarifier **only where the
  mapping is lossy**. 緊張 → `"tension; nervousness; strain — being keyed up
  or on edge"`. 場所 → `"place; location; spot"` (no clarifier needed — the
  mapping isn't lossy).

**Gloss first, clarifier only where it earns its place.** This is not
"translations only" — 気 has no clean English equivalent, and a bare
one-word answer would be actively misleading:

- 気 → simple: `"spirit"`. standard: `"spirit; mind; feeling — no single
  English equivalent; covers mood, attention and intention"`.

The failure mode in both directions is real: a clarifier on every word
(気's problem, generalized) drowns the equivalents in prose; no clarifier ever
(the opposite mistake) quietly lies about words like 気. Decide per word.

Other rules, non-negotiable:

- Written **in the target language**, not a mix.
- **Never include the source word itself** in the gloss (this is what stops a
  Chinese gloss of 気 coming back as "気").
- The source `simple`/`standard` definitions in the batch item are context to
  disambiguate *which sense* you're glossing — not text to translate
  word-for-word. The `example_sentence` is there for the same reason; don't
  translate it either.
- `standard` must read longer than `simple` for the same target language, and
  neither should read like a dictionary-entry sentence. `scripts/upload_glosses.py`
  enforces length bounds on both (see `check_gloss_shape`) — if your answer gets
  rejected for shape, you wrote a mini-definition, not a gloss.

## Size the job first

```sql
select l.language_code as target, count(*) as already_glossed
from dim_word_senses s join dim_languages l on l.id = s.definition_language_id
where s.source = 'llm_gloss'
group by l.language_code;

-- complete source pairs available for a given --source-language (both levels present):
select count(*) from (
  select vocab_id, sense_rank
  from dim_word_senses s join dim_vocabulary v on v.id = s.vocab_id
  where s.definition_language_id = v.language_id  -- native rows only
    and v.language_id = (select id from dim_languages where language_code = 'en')
  group by vocab_id, sense_rank
  having count(*) filter (where definition_level = 'simple') > 0
     and count(*) filter (where definition_level = 'standard') > 0
) pairs;
```

`source=en target=zh,ja` is **4,219 items → 16,876 rows** at full scale — about
105 batches of 40. That is not one sitting. **Agree a scope with the user
before running anything beyond a first `--limit` slice.** The export script
reports the real numbers (complete pairs, standard-only exclusions, already-done
count) — read them before committing to a size.

## Stage 1 — export

```bash
python scripts/export_gloss_worklist.py --source-language en --target-languages zh,ja --limit 40
python scripts/export_gloss_worklist.py --source-language en --target-languages zh,ja
python scripts/export_gloss_worklist.py --source-language ja --target-languages en --overwrite
```

Writes `data/gloss_seeding/<source>_to_<targets>/batch_001.json`, … Default 40
senses per file. **One item per (vocab_id, sense_rank), carrying every target
language it still needs** — so you write zh and ja for a sense in the same
pass and they stay consistent with each other, instead of drifting across two
separate runs.

Selection is on **complete source pairs only** — a sense needs both `simple`
and `standard` in the source language to be glossed. A standard-only sense
(real for a slice of `en` — 6,555 standard senses but only 4,219 with a simple
counterpart) is excluded and counted in the log output, not silently
half-glossed. If the excluded count is large, tell the user and let them
decide whether those senses should be seeded with a `simple` row first
([[batch-sense-generation]]) rather than skipped forever.

Without `--overwrite`, a sense already fully glossed in every requested target
is skipped — that's what makes re-running the same command safe. A sense with
only *some* targets done (an interrupted run) still comes back, but its
`target_languages` field lists only what's missing, so you don't re-answer a
language that's already good.

## Stage 2 — write the glosses (this is you)

Read one batch file. Write `batch_NNN.glosses.json` beside it: one entry per
item, in any order, but **every item in the batch must get exactly one
answer.**

```json
[
  {"vocab_id": 4412, "sense_rank": 1,
   "glosses": {
     "zh": {"simple": "紧张", "standard": "紧张；不安 —— 心里绷得很紧、坐立不安的感觉"},
     "ja": {"simple": "緊張", "standard": "緊張；不安 —— 気持ちが張り詰めて落ち着かない状態"}
   }},

  {"vocab_id": 4413, "sense_rank": 1, "skip": true, "reason": "proper noun"}
]
```

`glosses` must have an entry for every language listed in that item's
`target_languages`. Only answer the languages actually requested for that
item — the uploader rejects a language nobody asked for.

### When to skip

Emit `{"vocab_id": …, "sense_rank": …, "skip": true, "reason": "…"}` for proper
nouns and anything else a cross-language equivalent doesn't meaningfully apply
to. A skip is a real answer — it satisfies the every-item rule.

## Stage 3 — upload

```bash
python scripts/upload_glosses.py --batch-file data/gloss_seeding/en_to_zh-ja/batch_001.json \
  --glosses-file data/gloss_seeding/en_to_zh-ja/batch_001.glosses.json --dry-run
python scripts/upload_glosses.py --batch-file data/gloss_seeding/en_to_zh-ja/batch_001.json \
  --glosses-file data/gloss_seeding/en_to_zh-ja/batch_001.glosses.json
```

Dry-run first, every time. Read what prints — it's your last chance to catch a
gloss that leaked into the wrong language, kept the source word, or turned
into a sentence.

Writes go directly to `dim_word_senses`, upserted on
`vocab_id,definition_language_id,definition_level,sense_rank` with
`source='llm_gloss'`. This is additive: it never touches the source sense's
own row or id, so `word_assets`, `exercises`, and `user_word_ladder`
references are unaffected.

Validation is fail-closed and aborts the batch before writing anything on: a
`(vocab_id, sense_rank)` not in the batch, a duplicate, a target language not
requested for that item, a missing `simple` or `standard`, a gloss that fails
the target-language heuristic check, a gloss shaped like a sentence instead of
an equivalent, a gloss that still contains the source word, or any item left
unanswered. Fix the file and re-run. `--skip-invalid` drops the offending
items and continues — reach for it only when you've decided those items
should be abandoned, never to get past an error you haven't read.

## Stage 4 — re-embed

A gloss row is a new `dim_word_senses` row, so it needs its own embedding.
There is no embed-on-write here (unlike `SenseGenerator._write_two_levels`) —
null the rows you just wrote, then run the ordinary embed backfill, which only
picks up NULLs:

```sql
update dim_word_senses set embedding = null
where source = 'llm_gloss' and definition_language_id in (1, 2);  -- the target languages you just wrote, by id
```

```bash
python -m scripts.backfill_sense_embeddings --language 3   # the SOURCE word's language, not the target
```

`--language` here filters on the word's own language (`dim_vocabulary.language_id`),
not `definition_language_id` — so glossing `ja` words into `en`/`zh` still
means `--language 3`. Language ids: zh 1, en 2, ja 3. **Never pass `--force`**
— that re-embeds every sense in the language, not just the ones you touched.

## Verify

```bash
python scripts/export_gloss_worklist.py --source-language en --target-languages zh,ja --limit 20
# write batch_001.glosses.json, then:
python scripts/upload_glosses.py --batch-file ... --glosses-file ... --dry-run
```

Read the dry-run output. 場所 should come back as `"place"`, not a sentence.
Then, after a real upload:

```sql
select v.lemma, s.definition_level, s.definition, length(s.definition) as len
from dim_word_senses s join dim_vocabulary v on v.id = s.vocab_id
where s.source = 'llm_gloss' and s.definition_language_id = 2  -- en
order by len desc limit 20;
```

- Average length for `ja → en` should drop toward the `ja → ja` range (target:
  low tens of characters for `simple`, not the 57/94-char averages the old
  prompt produced).
- `simple` must be shorter than `standard` for the same word — the uploader
  already enforces this, but eyeball a handful anyway.
- Spot-check 気 and 甘える specifically: they should still carry a clarifier,
  not a misleadingly crisp one-word answer. If the shape gate is rejecting a
  legitimate long clarifier, that's a signal to look at the actual text, not
  to loosen the gate blindly.

## Hard rules

- **Never invent a `vocab_id` or `sense_rank`.** Only keys from the batch
  file.
- **Every item gets an answer** — glosses for every requested target, or an
  explicit `skip`.
- **Both levels, every requested target language.** A standard-only gloss is
  the same drift the two-level treatment exists to prevent everywhere else.
- **Target language, not English** (unless English is the actual target).
- **One batch at a time**, through stage 2 and 3, before opening the next.
- **Do not edit `gloss_generator.py`'s retired prompt back to life, and do not
  edit `upload_glosses.py`'s shape gate to fit a bad batch.** If a real gloss
  keeps getting rejected, look at whether it's actually shaped wrong before
  touching the gate.
- **No migration.** `llm_gloss` is already an allowed `source` value and the
  unique key already covers this; if you find yourself reaching for one,
  stop.

## When to stop and ask

- The worklist is far bigger than the conversation expected — agree scope
  first (see "Size the job" above).
- A large fraction of the source language is standard-only (no `simple`
  counterpart) — that's an upstream gap in [[batch-sense-generation]], not
  something to route around silently here.
- Many words in a batch have no clean equivalent at all (not just the
  occasional 気) — that may mean the source and target languages are too
  distant for this format to fit, and is worth surfacing rather than forcing.
- The shape gate rejects something you're confident is correct — read the
  actual numbers in the error before deciding whether the text or the gate is
  wrong.
