# Drill author

You write one batch of drill items: `PACK/grammar/batches/<slug>-<NN>.jsonl`.
Read `GRAMMAR_SPEC.md` in this skill in full, `PACK/profile.json` (`text`,
`levels`, `learner`), the topic in `PACK/grammar/plan.json` and its guide
`PACK/grammar/guides/<slug>.json`. Your task gives the batch number, the
number of items and the themes to stay on.

- Before you write a cloze, say the sentence with each distractor. If any
  distractor could be accepted by some native speaker, change the sentence.
- For order and rewrite items, try the tiles in other orders and list every
  correct one in `alts`.
- A wrong judge sentence has one error, on this topic, that every native
  speaker rejects.
- `why` names the rule and the tempting error for this sentence.

Write the file in parts if it is long. Run `validate-batch <lang> <file>
--min-items <n>` until OK.
