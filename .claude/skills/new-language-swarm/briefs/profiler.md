# Profiler

You decide what the content pack for this language contains. Everything
downstream is built from your `PACK/profile.json`.

Read first: `reference/ja-zh-inventory.md` in this skill (what Japanese and
Chinese have and why), then the template the tool created at
`PACK/profile.json`.

Fill in every field:

- `proposed_language_id`: given in your task.
- `variety`, `learner`: the standard variety, and the learner (L1 English
  unless told otherwise, with the level range the content targets).
- `text`: the characters a sentence may contain (`allowed_regex` must match a
  whole sentence and each single allowed character), what is forbidden
  (digits, normally), `punctuation` (every punctuation character sentences
  use, including the space when words are spaced), `token_joiner` (`" "` for
  spaced scripts, `""` otherwise), `length_unit` and sentence bounds,
  `romanisation` (null unless learners need one).
- `levels`: the level scheme teachers of this language use, and what drill
  levels 1 to 3 mean in vocabulary and sentence shape.
- `gloss_languages`: given in your task.
- `tts_voices`: two Azure neural voice names for the language if you know them
  for certain, else `[]` with a note in your report.
- `nlp`: the tokeniser and lemmatiser you recommend (a spaCy model name where
  one exists) and anything that needs care (clitics, elision, contractions).
- `ladder`: one row for **every** type code in the inventory's exercise table,
  and one for every new type this language needs:
  `{"type_code", "ladder_level", "generator": "llm"|"deterministic", "status": "reuse"|"adapt"|"new"|"not_applicable", "pos_classes": [...], "requires": [...], "note"}`.
  `reuse` = works as it is; `adapt` = same type, different rules for this
  language (say which); `new` = does not exist yet; `not_applicable` = say why.
  A `new` row with generator `llm` becomes a block the fat-seed authors write,
  so its note must give the block's shape.
- `unique_features`: what this language has that a learner must automate and
  the others do not have in this form. For each:
  `{"key", "title", "why", "analogue": {"zh": "…", "ja": "…"}, "delivered_by": "ladder"|"dictionary"|"grammar"|"generator", "dictionary": "<key>" (when delivered by a dictionary), "exercise_types": [...]}`.
  Use the four patterns at the end of section 2 of the inventory. Aim for the
  features that cost learners the most errors, not a complete grammar.
- `dictionaries`: the reviewed lookup tables that make exercises deterministic
  (the analogue of measure words and counters). For each:
  `{"key", "title", "unit" (what one row is), "target" (rows needed), "unique": [field names], "source_pos" (which lexicon part of speech feeds it), "fields": {…}, "exercises": [type codes it feeds], "author_notes"}`.
  A field spec is `"str"`, `"int"`, `"bool"`, a list of allowed values,
  `{"regex": "…"}`, `{"list": <spec>, "min": n}` or `{"object": {…fields…}}`;
  a field name ending in `?` is optional. Make the fields strict enough that a
  wrong row fails: enumerate closed sets, give regexes for forms.
- `targets`: realistic full-scale counts.

Then run `validate-profile` until OK. Also write `PACK/reports/profile.md`
(under 500 words): the decisions a teacher of this language would question,
and why you made them.

Return the dictionary keys and the list of ladder rows marked `new`.
