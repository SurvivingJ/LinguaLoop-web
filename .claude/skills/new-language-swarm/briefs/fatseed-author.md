# Fat-seed author

You write one exercise document per sense in `PACK/fat_seed/worklist.json`
(your task says which entries), to `PACK/fat_seed/words/<doc>`.

Read, in this order: `.claude/skills/fat-seed-authoring/SKILL.md` section
"Block reference" (the shapes), the language's cheat sheet
`.claude/skills/fat-seed-authoring/cheatsheets/<lang>.md`, and the `ladder`
of `PACK/profile.json`.

The real pipeline has a planner that fixes each block's anchor sentence and
answer; the language is not wired yet, so here you choose them, and record
your choice: every block carries `"sentence_index"` (which core sentence it is
built on) in addition to the Block reference fields.

```json
{"lemma": "…", "pos": "…", "sense_hint": "<the worklist hint>",
 "core": {"definition": "<tl_standard from the worklist>", "pos": "…", "register": "neutral|formal|informal",
          "pronunciation": "…", "forms": ["3 to 5 real forms"], "primary_collocate": "… or null",
          "sentences": [{"text": "…", "target_word": "<the form as it stands in the sentence>"} × 10]},
 "variants": {"A": {…blocks…}, "B": {…blocks…}}}
```

Blocks per variant: `level_1`, `level_3`, `level_6`, `level_7` for every word;
`level_4` when the word inflects; `synonym_antonym_match` only when a
dictionary would list the pair (else decline); every ladder row marked `new`
with generator `llm` whose `pos_classes` include this word, in the shape its
note gives. `level_5` and `level_8` are not written (no collocation list yet).
Decline with the Block reference's tokens, never by leaving a block out.

B is written independently of A: different anchor sentences, different
distractors. Run `validate-fatseed <lang> <doc>` on each document until OK.

Notes from the Italian pilot: every index is 0-based. level_7
`correct_sentence_indices` are the indices of the core sentences shown beside
the wrong one. Reviewers found a defect that would break an item in four of
six documents, most often a "wrong" level_6 sentence that is acceptable and a
level_3 distractor that also fits: test each one in the sentence before you
keep it.

From the Opus check: one document in six was unusable because its level_6
"wrong" sentences used the word correctly in another sense or part of speech,
or did not contain the word at all (a homograph). A level_6 wrong sentence
contains the target word, in the taught part of speech, used where a native
speaker would use a different word. Articles and other determiners get no
exercise document (the worklist leaves function words out): every
meaning-based cloze alternative fits their blank.
