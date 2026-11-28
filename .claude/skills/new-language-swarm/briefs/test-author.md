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

## Questions that need the passage (from the pilot)

In the pilot a solver who never saw the passages answered 85 to 100 percent
of the questions. The reasons, and what to do about each:

1. **The passage said what anyone would expect.** A question about a detail
   is only as good as the detail. Give every passage particulars that could
   have been otherwise and that nobody could predict: the character goes on
   Tuesday and not at the weekend, likes the cheap one better, the delay was
   caused by a lost key and not by traffic, the second step is done before
   the first. Then ask about those. If the true answer is the stereotype or
   the famous fact, change the passage or drop the question.
2. **Other questions leaked the answer.** Read your questions as a set: a
   word in one question's stem or choices must not settle another. Do not
   name in a stem something a different question asks for.
3. **The key looked different.** Every choice has the same form, length and
   degree of detail, and every wrong choice is something that could be true
   of a text with this title. For `main_idea` and `author_purpose` that means
   four summaries of the same scope and tone (not one balanced sentence
   against three narrow ones): the wrong ones describe a slightly different
   text on the same subject, or get the passage's emphasis or conclusion
   wrong.
4. **General knowledge.** On real subjects (a food, a monument, an inventor)
   do not ask what the world already knows about them; ask what this passage
   adds: the narrator's case, an order, a reason, a comparison it draws.

Before you keep a question, hide the passage and ask: which choice would a
clever stranger pick? If it is the key, the question is not finished.
