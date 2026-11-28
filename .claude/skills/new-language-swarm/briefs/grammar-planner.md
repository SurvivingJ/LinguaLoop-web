# Grammar planner

You write `PACK/grammar/plan.json`: the full list of grammar drill topics for
this language. Read `GRAMMAR_SPEC.md` in this skill ("Plan file"),
`PACK/profile.json` (learner, levels, `unique_features`) and, as the model of
what a good plan looks like, `data/grammar_drills/zh/plan.json`.

- Choose topics from what learners of this language get wrong for years, in
  the profile's level range, not from a grammar book's contents page. A topic
  is one decision the learner must make fast (which auxiliary, which article,
  which mood after this conjunction).
- 25 to 45 topics in 5 to 8 categories. Every `unique_features` entry
  delivered by grammar is covered.
- `scope` spells out what is in and what is left to another topic, so two
  authors would write the same boundaries.
- `mix` fits the point: order and rewrite items for word-order and
  transformation points, cloze and judge for choice points.
- `batches`: the planned number of batches per topic at full scale (the
  profile's `targets.grammar_items` divided by `batch_size`, weighted toward
  the hardest points).
- `themes`: 20 everyday themes.

Run `validate-plan` until OK. Return the topic slugs in the order you would
build them: the points that matter most to a beginner first.
