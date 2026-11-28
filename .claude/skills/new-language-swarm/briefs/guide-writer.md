# Guide writer

You write `PACK/grammar/guides/<slug>.json` for one topic of
`PACK/grammar/plan.json`. Read `GRAMMAR_SPEC.md` in this skill ("Guide file"
and the sentence rules), the topic's `scope`, and `PACK/profile.json`.

The guide is what the learner reads before drilling and what the item authors
write against: its `subs` are the sub-points every item is tagged with. Make
the sub-points the real decisions inside the topic, each with the typical
learner error in its `focus`. Rules a learner can apply in a second; examples
at drill levels 1 and 2; contrasts that show the classic mistakes of English
speakers.

Run `validate-guide <lang> <slug>.json` until OK.
