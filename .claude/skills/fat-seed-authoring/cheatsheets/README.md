# Cheat sheets

`nt_pipeline.py --lang <lang>` appends `<lang>.md` to the author's system
prompt, after a one-line role statement and before the skill's Block
reference. Every authoring call sees it: core, audits, variants and repairs.
It is the main lever on quality per language.

`ja.md` is the production sheet (v7 from the optimisation campaign,
`data/exercise_seeding/ja/opt/REPORT.md`). Use it as the template.

`zh.md` and `en.md` (v1) follow the same structure. They are aligned with the
live zh/en core and exercise prompts and their judges. They also cover
level_1, which zh and en still author because there is no phonetic trie for
them. **Neither has been run yet.** Validate each on a 100-sense gold set
before the full queue, as described below.

## What made the Japanese sheet work

- **Short and structural.** ~5 KB in five numbered sections. Every longer
  sheet tried (8–13 KB of rules) scored worse: Haiku follows a few concrete
  procedures and loses rule lists.
- **One section per defect class the judge counted**, in order of cost:
  1. Core sentences: whole word, the given reading, the given sense, natural
     collocations, one register.
  2. level_6 wrong sentences, built with two named moves (other sense / near-synonym
     swap), with worked examples and a never-list.
  3. level_7: one span, on the target.
  4. synonym_antonym_match: decline unless a dictionary lists the pair.
  5. Explanations and distractors: specific, true, never a generic template;
     distractors must not fit the slot; B shares nothing with A.
- **Worked examples in the target language**, including the wrong versions
  ("never 度を守る"). Examples change behaviour; abstract rules mostly do not.
- **No generic template phrases.** The earlier JA sheet suggested an
  explanation template; models copied it onto 72% of documents and the judge
  marked every copy as a defect.

## Writing `<lang>.md`

Keep sections 2–5 (they are language-independent in shape) and rewrite the
examples. Replace the Japanese-specific rules with the language's own:

| | ja | zh | en |
|---|---|---|---|
| reading / form | kana reading, morae, 清濁 | pinyin with tones, 多音字 (行 xíng/háng) | spelling variants, stress |
| inside a longer word | 習熟度 for 度 | 学生 for 学, 电脑 for 电 | "therapist" for "the rapist", compounds |
| function-word block | particle_selection (case particles) | measure words, 了/过/着 (if the plan asks) | prepositions in collocations |
| level_4 forms | conjugation (活用) | usually declined (`no_inflection`) | -s/-ed/-ing, irregulars |
| collocation traps | 節度を守る not 度を守る | 提高水平 not 增加水平 | make/do, heavy rain not strong rain |

## Before scaling

Run a 100-sense gold set for the language and compare against a baseline
arm, as described in the skill's "New language" section, before you launch
the full queue. Adjust the sheet where the defect classes cluster
(`nt_experiment.py --loss`); one example per class beats a new rule.
