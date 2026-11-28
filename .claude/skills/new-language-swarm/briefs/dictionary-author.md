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

Notes from the Italian pilot:

- `source_pos` may name several parts of speech; take words from all of them.
  Where the lexicon is too thin for the table (collocations, false friends),
  common words of the profile's level range are the right source.
- A field that lists **wrong** alternatives (wrong collocates, a calque, a
  wrong preposition) is the riskiest in the table: each one must be
  unacceptable in every reading and register. If it forms an established
  phrase with another meaning, or is merely rarer, it is not wrong. Six in ten
  collocation rows failed on this in the pilot.
- Apply the profile's criteria for flags (irregular, spelling change, cue) the
  same way to every row; where the criterion does not decide a case, say so in
  your report instead of deciding silently.

From the Opus check of the Italian pilot (15 of 49 collocation rows, 7 of 57
government rows and 8 of 56 false-friend rows were still wrong after review):

- Before listing a wrong partner, search your memory for the phrase with a
  small change of construction (an added preposition or article, an impersonal
  form). If that is everyday usage with the same meaning, the partner is not
  wrong.
- A calque field holds what a speaker of the learner's language would really
  produce. Where their language maps straight onto the correct form there is
  no trap: leave the row out. Regional variants of the target language are not
  calques.
- A head that accepts two prepositions for the same complement and meaning is
  left out, not listed with one of them.
- A false friend is "full" only when no current sense is shared, on either
  side; otherwise "partial".
