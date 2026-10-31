# Rules for authoring sentence references (ja -> en, arm `aligned`)

You translate the sentences of a test transcript into the learner's native
language (English). The translations are **references for back-translation**:
a learner will read your English and try to write the original Japanese.
So every sentence must be faithful and tight, not pretty.

1. One entry per sentence, in order, same count as the transcript. Never merge
   or split, even when English would naturally do so.
2. Keep every piece of information: numbers, names, lists, negation, tense or
   aspect markers, politeness markers, and the sentence's own focus. Add
   nothing. Explain nothing. No parentheses, no translator's notes in `l1`.
3. Prefer the wording that most directly maps back to the original structure
   while still being natural English. When two phrasings are equally natural,
   choose the one whose word order follows the original.
4. No Japanese script in `l1` (no kanji, kana or hanzi in English; no romaji
   either). Loanwords go back to their source form (カタログ -> catalogue).
5. Proper nouns: use the standard English form if one exists, else a
   transliteration. Keep digits as digits.
6. Terminators: end each `l1` with the punctuation the sentence type needs in
   English. Question stays a question.
7. Arm `sentencewise`: translate one sentence at a time, re-reading the whole
   passage before each. Arm `aligned`: translate the whole passage first, then
   split it into the aligned array and adjust each entry so it stands alone.
   Either way the output shape is identical.
8. Write `author_notes` only for things the reviewer must know (an ambiguous
   gold, a possible transcript error). They are stripped before review.
9. Do not touch `l2`. Do not reorder `idx`.

Document shape (one file per test, `docs/<test_id>.en.json`):

```json
{"test_id": "...", "l2": "ja", "l1": "en", "arm": "aligned", "prompt_version": "sr-1.0",
 "sentences": [{"idx": 0, "l2": "<copied exactly>", "l1": "<your translation>"}, ...],
 "author_notes": ""}
```
