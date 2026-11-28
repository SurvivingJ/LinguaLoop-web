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

Notes from the Italian pilot: reviewers changed about one item in five. The
recurring faults were a `why` that states a rule more strongly than the
language does, an English cue that does not match the verb, a distractor that
is also a normal sentence (a first-person plural, a polite request), and too
few `alts` when an adverb can move. Check those four on every item.

From the Opus check: do not repeat a guide's rule in `why` more strongly
than the guide states it, and if the guide's rule looks too absolute, say so in
your report. Level 1 means one clause; two clauses is level 2 at least. A
distractor tile is useless when the form it competes with sits inside a larger
tile: cut the tiles so the choice is real.
