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
