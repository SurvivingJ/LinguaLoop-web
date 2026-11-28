# Grammar drills for a language pack: content contract

Learners drill one grammar point at a time until the right form is a reflex.
Each topic in `grammar/plan.json` has one guide (`grammar/guides/<slug>.json`)
and drill items written in batches (`grammar/batches/<slug>-<NN>.jsonl`,
reviewed copy in `grammar/reviewed/<slug>-<NN>.jsonl`). All paths are under
`data/language_packs/<lang>/`. `python scripts/language_pack.py` checks every
file and builds the static files; run it from the repository root.

This is the Chinese contract (`data/grammar_drills/zh/SPEC.md`) with the
sentence field named `tl` and the script rules taken from the language's
`profile.json` (`text`, `levels`, `learner`). Read the profile first: it says
who the learner is, which characters are allowed, how long a sentence may be
and what the three item levels mean.

## Rules for every target-language sentence

- Natural sentences a native speaker would say, in the profile's variety. No
  textbook oddities. Only very common proper names.
- The grammar point is the only hard thing in the sentence: vocabulary and
  length follow the item's level (`levels.drill_levels`).
- Only the characters the profile allows (digits are normally forbidden: write
  numbers as words). NFC-normalised accents, straight apostrophes.
- Length within `text.sentence_min` to `text.sentence_max`.
- If the profile names a romanisation, every sentence field has one
  (`rom`, `s_rom`, `src_rom`).

## Item fields

One JSON object per line.

| field | meaning |
|---|---|
| `id` | `<topic>-<batch NN>-<item NNN>` |
| `type` | `cloze`, `order`, `rewrite` or `judge` |
| `sub` | key of the sub-point drilled, from the topic guide's `subs` |
| `lvl` | 1, 2 or 3 |
| `tl` | the full correct sentence |
| `en` | natural English meaning of `tl` (the cue the learner sees) |
| `why` | 15 to 260 characters, in English: the rule that decides this item and why the tempting wrong answer fails. Specific to this sentence. |

### cloze: fill the blank

```json
{"id":"x-01-001","type":"cloze","sub":"…","lvl":1,"q":"Ieri ___ andata al mare.","opts":["sono","ho","è","sto"],"a":0,"tl":"Ieri sono andata al mare.","en":"Yesterday I went to the seaside.","why":"…"}
```

- `q` has one blank written `___` (two allowed for paired words; an option is
  then `first|second`). `∅` means "nothing goes here".
- `opts`: 2 to 4, `a` is the index of the right one. `tl` is exactly `q` with
  the right option filled in.
- **Exactly one option may be acceptable** to a native speaker given the
  sentence and the English cue. If two could work, change the sentence until
  one is forced. This is the most common defect.
- Distractors are the forms learners really confuse with the answer. Spread
  the correct answer across positions.

### order: build the sentence from tiles

- `tokens`: 3 to 10 tiles in the correct order, no punctuation; joined with the
  profile's `token_joiner` they equal `tl` without punctuation (case is
  ignored when the profile says so: write tiles in lower case except proper
  nouns, so the capital does not give the first tile away).
- Cut tiles at word or phrase boundaries so that the grammar point is what the
  learner decides. A tile may hold several words.
- `alts`: every other order of the same tiles that is also correct and means
  the same. A missing alt marks a right answer wrong. More than two: cut the
  tiles differently.
- `extra` (optional): up to 2 distractor tiles that must not be used.

### rewrite: transform a sentence

Same fields as `order`, plus `src` (the starting sentence) and `task` (a short
English instruction: "Make it negative.", "Replace the object with a pronoun.").

### judge: is this sentence correct?

- `s` is the sentence shown, `ok` true or false.
- `ok: true`: `s` equals `tl`. `ok: false`: `s` has exactly one error on this
  topic and `tl` is the corrected sentence.
- A wrong sentence is clearly wrong to every native speaker, not merely
  unusual or regional. A correct sentence should look like a trap. Keep 30 to
  60 percent of judge items correct.

## Batch requirements

- `plan.json` `batch_size` items (up to 10 more), ids numbered 001 upward.
- Type mix: the topic's `mix`, within the tolerance the validator reports.
- Levels: at least 25% level 1 and 10% level 3; aim for 40 / 40 / 20.
- Spread items over the guide's sub-points, weighted toward what learners get
  wrong most. No two items in a batch share a sentence.
- Vary subjects, verbs and situations; stay on the themes in the brief so
  parallel batches do not collide.

`python scripts/language_pack.py validate-batch <lang> <file>` until OK.

## Guide file

```json
{"topic": "<slug>",
 "summary": "60 to 420 characters: what this point does and the one idea that makes it click.",
 "subs": [{"key": "lowercase-key", "label": "short label", "focus": "what items must test, including the typical learner error"}],
 "rules": [{"sub": "lowercase-key", "rule": "one statement the learner can apply", "pattern": "optional schema", "examples": [{"tl": "…", "en": "…"}], "note": "optional caveat"}],
 "contrasts": [{"wrong": "…", "right": {"tl": "…", "en": "…"}, "why": "…"}],
 "cheat": ["one-line reflex rule"]}
```

- `subs`: 3 to 10, together covering the topic's `scope` in the plan.
- `rules`: 3 to 12, every sub-point covered, 2 to 4 examples each.
- `contrasts`: 3 to 10 wrong/right pairs showing the classic mistakes.
- `cheat`: 3 to 7 one-line rules for the moment of answering.

`python scripts/language_pack.py validate-guide <lang> <file>` until OK.

## Plan file

```json
{"language": "<lang>", "batch_size": 100,
 "categories": [{"key": "…", "title": "…"}],
 "themes": ["food and restaurants", "… at least 10"],
 "topics": [{"slug": "…", "title": "…", "cat": "<category key>", "batches": 3,
             "mix": {"cloze": 55, "order": 15, "rewrite": 10, "judge": 20},
             "scope": "exactly what the topic covers and what it leaves to other topics"}]}
```

`mix` sums to `batch_size`. `batches` is how many batches the topic deserves:
more for the points learners take longest to automate.
