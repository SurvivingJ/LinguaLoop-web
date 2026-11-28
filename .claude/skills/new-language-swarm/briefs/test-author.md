# Test author

You write one batch of comprehension tests:
`PACK/tests/batches/t<tier>-<NN>.jsonl`, one test per line, for the entries of
that batch in `PACK/tests/plan/t<tier>.json`. Read `TEST_SPEC.md` in this
skill in full, and `PACK/profile.json` (variety, text rules).

For each test:

1. Write the passage first, as a native writer would for that reader: a text
   someone could have published, with something specific in every sentence.
   Count the words; stay inside the tier's range. Vary the kind of text
   across the batch (description, small story, report, explanation, letter,
   notice, dialogue where the plan says conversational).
2. Translate each sentence faithfully for `en`.
3. Write the questions from the passage, then test each one twice: cover the
   passage and try to answer (if you can, the question is too easy: rewrite
   it); then read each wrong choice against the passage (if the passage
   supports it, replace it).
4. Shuffle so the key is not always in the same position.

Write the file in parts if it is long. Run `validate-tests <lang> <file>`
until OK.

**Facts.** The plan's topics were written from memory and some carry figures
and dates that were never checked. A learner will remember what a passage
says, so state as fact only what you are certain of. Where you are not, write
the passage so that it does not depend on the figure: leave the number out,
make it a character's own case ("my grandfather's workshop made two violins
a year"), or frame a tradition as a tradition ("the story goes that …").
Never build a question on a figure you could not confirm. List in your report
every factual claim about the real world you kept and were not sure of.

Keep each passage distinct from the other tiers' tests on neighbouring
subjects: follow your topic's angle, not the general subject.
