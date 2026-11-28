# Chinese grammar drills: content contract

Learners drill one grammar point at a time until the right form is a reflex.
Each topic in `plan.json` has one guide (`guides/<slug>.json`) and a set of
drill items written in batches of 100 (`batches/<slug>-<NN>.jsonl`, reviewed
copy in `reviewed/<slug>-<NN>.jsonl`). `scripts/grammar_drills.py` checks both
and builds the static files the app serves. Run it from the repository root.

The learner is an English speaker at HSK 1 to 4. Everything is Simplified
Chinese, mainland standard usage. Explanations are in plain English.

## Rules for every Chinese sentence

- Natural sentences a native speaker would say; no textbook oddities, no
  proper names beyond common ones (小王, 李老师, 北京, 上海).
- Vocabulary: level 1 = HSK 1-2 words, short sentence; level 2 = HSK 3;
  level 3 = HSK 4, longer sentence or two clauses. The grammar point is the
  only hard thing in the sentence.
- No Latin letters and no Arabic digits: write 三点半, not 3点半.
- 3 to 34 characters.
- Pinyin (`py`): tone marks, **one syllable per character, separated by
  spaces**, no punctuation needed: `wǒ zuó tiān mǎi le sān běn shū`. Use the
  reading the character has in this sentence (了 le / liǎo, 得 de / děi / dé,
  地 de / dì, 着 zhe / zháo, 还 hái / huán, 长 cháng / zhǎng). Neutral tone is
  written without a mark (`de`, `le`, `ma`, `men`, `dōng xi`). 不 and 一 may be
  written with their citation tone (`bù`, `yī`). 儿 after a syllable is `r`
  (`yī diǎn r`).

## Item fields

One JSON object per line. Common fields:

| field | meaning |
|---|---|
| `id` | `<topic>-<batch NN>-<item NNN>`, e.g. `le-03-017` |
| `type` | `cloze`, `order`, `rewrite` or `judge` |
| `sub` | key of the sub-point drilled, from the topic guide's `subs` |
| `lvl` | 1, 2 or 3 |
| `zh` | the full correct sentence |
| `py` | pinyin of `zh` |
| `en` | natural English meaning of `zh` (shown to the learner as the cue) |
| `why` | 15 to 260 characters: the rule that decides this item, and why the tempting wrong answer fails. Specific to this sentence, not a generic slogan. |

### cloze: fill the blank

```json
{"id":"le-01-001","type":"cloze","sub":"completed-quantified","lvl":1,"q":"我昨天买___三本书。","opts":["了","过","着","的"],"a":0,"zh":"我昨天买了三本书。","py":"wǒ zuó tiān mǎi le sān běn shū","en":"I bought three books yesterday.","why":"A finished action with a counted object takes 了 right after the verb. 过 would mean 'have ever bought', which does not fit 昨天 with a specific purchase."}
```

- `q` has one blank written `___` (two blanks allowed for paired words).
- `opts`: 2 to 4 options, `a` is the index of the right one. For two blanks an
  option is `first|second`, e.g. `"因为|所以"`. Use `∅` for "nothing goes
  here", e.g. opts `["了","∅"]` when the point is that 了 must be left out.
- `zh` must be exactly `q` with the right option filled in.
- **Exactly one option may be acceptable** to a native speaker, given the
  sentence and the English cue. If two could work, change the sentence (add a
  time word, a result, a context clause) until one is forced. This is the most
  common defect: check every distractor by reading the sentence aloud with it.
- Distractors are the forms learners really confuse with the answer, not
  random words. Spread the correct answer across positions.

### order: build the sentence from tiles

```json
{"id":"word-order-01-020","type":"order","sub":"time-place","lvl":1,"tokens":["我","明天","在家","看","电影"],"alts":[["明天","我","在家","看","电影"]],"zh":"我明天在家看电影。","py":"wǒ míng tiān zài jiā kàn diàn yǐng","en":"I'm watching a film at home tomorrow.","why":"Time, then place, then the verb. 在家 cannot follow the verb phrase and 明天 cannot go at the end."}
```

- `tokens`: 3 to 10 tiles in the correct order, no punctuation; joined they
  equal `zh` without punctuation. Cut tiles at word or phrase boundaries so
  the grammar point is what the learner has to decide.
- `alts`: every other order of the same tiles that is also correct and means
  the same. Think hard about these: a missing alt marks a right answer wrong.
  If there are more than two, cut the tiles differently.
- `extra` (optional): up to 2 distractor tiles that must not be used.
- The learner sees `en` and the shuffled tiles.

### rewrite: transform a sentence

```json
{"id":"ba-02-061","type":"rewrite","sub":"ba-result","lvl":2,"src":"我喝完了那杯咖啡。","src_py":"wǒ hē wán le nà bēi kā fēi","task":"Rewrite with 把.","tokens":["我","把","那杯咖啡","喝完","了"],"zh":"我把那杯咖啡喝完了。","py":"wǒ bǎ nà bēi kā fēi hē wán le","en":"I finished that cup of coffee.","why":"把 moves the definite object in front of the verb, and the verb keeps its result 完 and 了."}
```

Same fields as `order`, plus `src` (the starting sentence), `src_py` and
`task` (a short English instruction: "Make it negative.", "Rewrite with 被.",
"Say it is still going on.", "Turn it into an A-not-A question.").

### judge: is this sentence correct?

```json
{"id":"bu-mei-01-090","type":"judge","sub":"mei-you","lvl":1,"s":"我不有哥哥。","s_py":"wǒ bù yǒu gē ge","ok":false,"zh":"我没有哥哥。","py":"wǒ méi yǒu gē ge","en":"I don't have an older brother.","why":"有 is only ever negated with 没; 不有 does not exist."}
```

- `ok: true`: `s` is correct and equals `zh`.
- `ok: false`: `s` contains exactly one error on this topic, `zh` is the
  corrected sentence, and `s_py` is the pinyin of `s`.
- A wrong sentence must be clearly wrong to every native speaker, not merely
  unusual. A correct sentence should look like a trap (it uses the pattern in
  a way learners doubt). Keep 30 to 60 percent of judge items correct.

## Batch requirements

- 100 items (up to 110 allowed), ids numbered 001 upward.
- Type mix: the topic's `mix` in `plan.json`, within 8 either way.
- Levels: at least 25% level 1 and 10% level 3; aim for 40 / 40 / 20.
- Spread items over the guide's sub-points, weighted toward the ones
  learners get wrong most. No two items in a batch may share a sentence.
- Vary subjects, verbs and situations. The batch brief gives themes; stay on
  them so that parallel batches do not collide.

Check a batch with `python scripts/grammar_drills.py validate <file>` and fix
every reported problem.

## Guide file

`guides/<slug>.json`, one object:

```json
{
  "topic": "le",
  "summary": "60 to 420 characters: what this point does and the one idea that makes it click.",
  "subs": [
    {"key": "completed-quantified", "label": "了 after the verb", "focus": "What items on this sub-point must test, including the typical learner error."}
  ],
  "rules": [
    {"sub": "completed-quantified", "rule": "One short statement the learner can apply.", "pattern": "Subject + Verb + 了 + number + measure + Object", "examples": [{"zh": "我买了三本书。", "py": "wǒ mǎi le sān běn shū", "en": "I bought three books."}], "note": "optional caveat"}
  ],
  "contrasts": [
    {"wrong": "我昨天没去了。", "right": {"zh": "我昨天没去。", "py": "wǒ zuó tiān méi qù", "en": "I didn't go yesterday."}, "why": "没 already says it did not happen; 了 cannot be added."}
  ],
  "cheat": ["Counted object? 了 goes right after the verb."]
}
```

- `subs`: 3 to 10 sub-points with short lowercase keys. Together they cover
  the topic's `scope` in `plan.json`. These keys are what items reference.
- `rules`: 3 to 12, each tied to a sub-point, each with 2 to 4 examples.
- `contrasts`: 3 to 10 wrong/right pairs showing the classic mistakes.
- `cheat`: 3 to 7 one-line reflex rules for the moment of answering.

Check with `python scripts/grammar_drills.py validate-guide <file>`.
