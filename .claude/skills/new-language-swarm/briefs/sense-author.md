# Sense author

Input: `PACK/senses/write_<NNN>.in.json` (lemma, pos, level, zipf, hint).
Output: `PACK/senses/write_<NNN>.out.json`: a JSON array, one object per input
word, same order.

```json
{"lemma": "…", "pos": "…", "confidence": 0.95, "pronunciation": "IPA, or the profile's reading",
 "tl_simple": "…", "tl_standard": "…", "example": "…",
 "glosses": {"en": {"simple": "…", "standard": "…"}},
 "lexical": {}}
```
or `{"lemma": "…", "skip": true, "reason": "…"}` only if it is not a word.

- **One sense only**: the one the hint names. A definition that joins two
  meanings ("; also …") is rejected downstream.
- `tl_simple`: in the target language, for a child of about eight: everyday
  words, one idea per sentence, one or two short sentences. It must not use
  the word itself or a grammar term.
- `tl_standard`: an ordinary monolingual dictionary definition (genus and
  distinguishing property), one sentence.
- `example`: one short natural sentence that uses the word, simple register.
- `glosses.<lang>.simple`: the single best equivalent (60 characters at most).
  `standard`: the equivalent set separated by "; ", with a clarifier after
  " — " only where the mapping is lossy; 120 at most and longer than simple.
  Never a sentence, never the target-language word itself unless it is the
  English word too.
- `lexical`: the facts this language's learners need with the word, as the
  profile's `nlp` and `dictionaries` suggest (for a noun its gender, for a
  verb its auxiliary or class). Leave `{}` when there is nothing.
- `confidence` is honest; lower it when unsure.

Run `validate-senses` on your file until OK.
