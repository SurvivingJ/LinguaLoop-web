# Test planner

You write `PACK/tests/plan/t<tier>.json`: the topics of the comprehension
tests of one tier. Read `TEST_SPEC.md` in this skill ("Tiers", "Plan file")
and `PACK/profile.json` (learner, variety).

- Spread the tests over the 17 categories as evenly as the tier allows.
- Topics belong to the world of the language's speakers as well as to
  everyday life anywhere: places, habits, institutions, food, work and
  history a learner of this language should meet. No test about the language
  itself, no politics of the day, nothing that dates within a year.
- Fit the topic to the tier's reader: tier 1 and 2 topics are concrete and
  close to a child's world; tier 5 and 6 topics carry an argument or a
  tension a passage can develop.
- Each topic gives the author an angle and something specific to say (a
  contrast, a sequence, a reason, a surprise): generic topics produce
  questions anyone can answer without reading.
- No two topics of your tier may produce the same passage. Read the other
  tiers' plan files if they exist and avoid repeating their angles.

Run `validate-test-plan <lang> t<tier>.json` until OK. Return the number of
tests and batches.
