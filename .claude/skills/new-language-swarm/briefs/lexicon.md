# Lexicon curator

Input: rows `FROM` to `TO` of `PACK/lexicon/candidates.tsv` (rank, lemma,
summed Zipf, surface forms): a frequency list grouped by an automatic
lemmatiser, with its mistakes. Output: `PACK/lexicon/lexicon_<NN>.jsonl`, one
line per candidate row, in order.

For each row decide whether it is a word worth teaching:

- Keep: `{"lemma", "pos", "level", "zipf", "hint", "rank"}`. `lemma` is the
  dictionary form (fix the lemmatiser: wrong lemma, inflected form, missing
  accent). `pos` is one of the tool's list. `level` is a band of the profile's
  scheme, judged as a teacher would, not computed from frequency. `hint` is a
  short English meaning that says WHICH word and sense this row is (the most
  frequent sense). `zipf` is copied.
- A form that is two different words (noun and verb, or homographs) gets one
  line each, most frequent first, with distinct hints.
- Drop: `{"lemma", "drop": true, "reason"}` for proper names, foreign words
  not used as loans, abbreviations, chat spellings, fragments, inflected forms
  whose lemma is already in your range (say which).
- Function words are kept (they are taught), with their real part of speech.

Run `validate-lexicon` until OK. Return how many you kept and dropped.
