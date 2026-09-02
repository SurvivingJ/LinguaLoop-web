---
name: test-sense-linking
description: Link a test transcript to the word-sense dictionary. For each test with no vocab_sense_ids, extract the teachable vocabulary, resolve it against dim_vocabulary, decide per term whether an existing sense fits or a new one must be written, and apply the result. Use when asked to backfill senses for tests, fix tests whose words are unclickable, or process data/sense_linking/*.csv.
---

# Test Sense Linking

You are stage 3 of a four-stage pipeline. Three Python scripts do the database
work; you make the judgement calls between them. Your job per transcript is two
decisions and nothing else:

1. **Which words in this transcript are worth teaching?**
2. **For each of those, does an existing sense fit this usage — or does a new one
   have to be written?**

Everything else is a script. Do not query Supabase yourself, do not write SQL,
and do not edit `dim_word_senses` through any other tool. The scripts hold
invariants you cannot see from here.

## The loop

Work **one test at a time**, start to finish, before touching the next. A batch
half-applied across fifty tests is far worse than a queue of forty-nine untouched
ones.

### Stage 1 — the worklist (once per session)

```bash
python scripts/export_tests_missing_senses.py --language zh
```

Writes `data/sense_linking/tests_missing_senses.csv`. Read it and note two things:

- Any row where `token_map_linked_tokens` > 0 **does not need you at all**. Its
  sense ids are already inside its token map. Recover those first, with no LLM
  work, and remove them from your queue:
  ```bash
  python scripts/upload_test_senses.py --from-token-map --language en --dry-run
  ```
- The `transcript` column is the text you extract from. Read it from the CSV;
  do not re-fetch it.

### Stage 2 — extract, then resolve

Read one row's transcript. Produce the list of terms worth teaching (rules
below), write it to `data/sense_linking/<slug>.terms.json`:

```json
["机械", "昔", "働く"]
```

Then resolve it (`--test-id` takes the slug or the uuid; the slug is what the CSV
gives you and what keeps the filenames readable):

```bash
python scripts/sense_candidates.py --test-id zh-d6-my-favorite-t-shirt-20260607025702 \
  --terms-file data/sense_linking/zh-d6-my-favorite-t-shirt-20260607025702.terms.json
```

Read the candidates file. Per item it gives you `vocab_id`, `match`,
`in_transcript`, the containing `sentence`, and every existing `candidates[]`
sense with its definition and rank. It also carries `pos_legend` and
`simple_register` — the legal POS codes and the register a `simple` definition
must be written in. Both come from the database; use them, don't invent your own.

### Stage 3 — decide (this is you)

Write `data/sense_linking/<slug>.decisions.json`. One decision per item in the
candidates file, no more and no fewer.

```json
{
  "test_id": "03f1ba3e-316b-45f2-b0c2-4bec27bc38ed",
  "decisions": [
    {"term": "机械", "vocab_id": 4412, "action": "select", "sense_id": 8812},

    {"term": "新词", "vocab_id": null, "lemma": "新词", "action": "create",
     "part_of_speech": 1, "confidence": 0.9,
     "simple": "<child-register definition>",
     "standard": "<standard definition>",
     "example": "<one short sentence using the word>"},

    {"term": "小明", "action": "skip", "reason": "personal name"}
  ]
}
```

### Stage 4 — apply

```bash
python scripts/upload_test_senses.py --decisions-file data/sense_linking/<slug>.decisions.json --dry-run
python scripts/upload_test_senses.py --decisions-file data/sense_linking/<slug>.decisions.json
```

Always dry-run first. Read the output: it reports how many tokens the transcript
ended up linking and which content lemmas stayed unmatched. If linked tokens look
implausibly low for the transcript's length, your term list was too thin — go
back to stage 2 for that test rather than moving on.

## What to extract

Include content words a learner at this test's difficulty would plausibly not
know: nouns, verbs, adjectives, adverbs, and multi-word items with
non-compositional meaning (`throw up`, `成语`, idiomatic 〜ておく).

Exclude:

- proper nouns — people, places, brands, titles
- numbers, dates, units, symbols
- function words: particles, auxiliaries, determiners, pure grammar
- words that appear only inside a quoted foreign phrase

Write the term **exactly as the transcript spells it**. Do not romanise, do not
normalise CJK variants, do not expand contractions. Stage 2 handles lemmatisation
and reports which tier of matching it used; your job is fidelity to the text.

Twenty to sixty terms is normal for a 400–1800 character transcript. If you have
five, you have under-extracted. If you have two hundred, you are including
function words.

## How to decide select vs create

**Select** when one of the existing `candidates` means what the word means *in
this sentence*. Read the `sentence` field, not just the term.

Expect to select less often than you'd think. The dictionary looks complete in
aggregate — nearly every lemma in `dim_vocabulary` has a sense — but that is
survivorship: those lemmas are there *because* an earlier test was processed. The
tests in this backlog are the ones that never ran, so their vocabulary is largely
absent. On the first zh test measured, 9 of 30 terms existed and 21 needed
creating. **A create-heavy sheet is the normal case here, not a smell.** Which
means the quality of your definitions is the main thing this workflow produces —
treat each one as a dictionary entry someone will read, not a form field.

**Create** only when the word is genuinely absent (`candidates` is empty) or when
every existing sense is a different meaning of the same form — 行 as "go" when
this transcript uses it as "line", not merely a candidate you'd have worded
differently. A definition you'd phrase better is **not** grounds for a new sense;
that fragments the word and splits its review history.

**Skip** proper nouns, numerals, symbols, and anything that slipped through your
extraction filter.

Two flags in the candidates file need attention before you decide:

- `"match"` other than `"exact"` means the resolver *guessed* which vocabulary
  row your term refers to. Check that the `lemma` it settled on is really your
  word. If it is not, treat the item as `create` with the correct `lemma`, or
  `skip` it.
- `"in_transcript": false` means the term does not appear in the text. Usually
  you paraphrased. Fix the term and re-run stage 2 rather than deciding on it.

## Hard rules

- **Never invent a `sense_id`.** Only ever use an id printed in that item's
  `candidates` array. Stage 4 verifies every id against the database and aborts
  the whole test if one is wrong — but a *plausible* wrong id that happens to
  exist is the failure mode nothing catches, and it puts a wrong definition in
  front of a learner.
- **Every `create` needs both `simple` and `standard`.** A standard-only sense is
  exactly the drift the two-level treatment exists to prevent, and stage 4 rejects
  it. `simple` is written to the register in `simple_register`; `standard` is the
  ordinary dictionary definition.
- **Definitions are written in the target language**, not English — Chinese
  definitions for Chinese words, Japanese for Japanese. Preserve CJK, kana, and
  diacritics verbatim.
- **`part_of_speech` is an integer from that file's `pos_legend`.** Not a string.
- **One decision per candidate item.** Stage 4 counts skips against the item
  list; dropping items silently makes its coverage report lie.
- Do not edit `services/vocabulary/sense_generator.py` or any migration to make a
  decision fit. If a decision cannot be expressed in this format, stop and say so.

## When to stop and ask

- A transcript is empty, truncated, or not in the language its row claims.
- Stage 4 reports a validation error you don't understand — do not reach for
  `--skip-invalid` to move past it. That flag drops decisions; it does not fix
  them.
- Most items come back with `"in_transcript": false`, or with a `match` tier
  below `exact`. Both mean your extraction and the tokenizer disagree about what
  this text contains, and deciding on top of that disagreement writes senses for
  words the transcript does not use.
- Stage 4's dry run reports far fewer linked tokens than the transcript's length
  implies, twice in a row on the same test.
