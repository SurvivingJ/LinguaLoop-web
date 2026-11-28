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

Notes from the Opus check of the Italian pilot: both guides checked stated
rules as absolutes that are false at the edges ("only X is possible", "used
only with A, B and C", a pattern that the very next verb breaks). Write a rule
as an absolute only when it has no exception; otherwise say "mainly", list the
members with "such as", or name the exception. Test every rule against five
more words of the class before you keep it. Item authors copy the guide's
claims into their `why` texts, so one false rule becomes many false items.
