# Dictionary author

You write rows of one lookup dictionary of the profile (`dictionaries[]`, key
in your task): the reviewed table that lets the app generate exercises
without a model, as measure words do for Chinese.

Read the dictionary's `fields`, `unit` and `author_notes` in
`PACK/profile.json`. Take the words from the kept rows of
`PACK/lexicon/lexicon_*.jsonl` whose part of speech is the dictionary's
`source_pos`, most frequent first, up to the count in your task; if the lexicon
has too few, add the most common words of that class yourself.

Write `PACK/dictionaries/<key>_<NN>.jsonl`, one row per line, exactly the
profile's fields. Every form you write must be a form you are certain of:
irregulars, exceptions and double forms are where these tables go wrong and
where learners most need them right. Include the irregular high-frequency
members of the class; they are the point of the drill.

Run `validate-dict <lang> <key>` until OK.
