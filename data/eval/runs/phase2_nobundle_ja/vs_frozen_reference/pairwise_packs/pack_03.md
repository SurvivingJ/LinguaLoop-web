# Pairwise review pack 03

## Rubric

For each level shown, compare Pack A and Pack B for the SAME sense and level and
judge which set of exercises is better, or call it a tie. Score on:

1. **Correctness** -- is the correct answer actually correct for the sentence/prompt shown?
2. **Single defensible answer** -- is exactly one option defensible as correct, with no
   distractor that a reasonable native speaker could also accept?
3. **Distractor plausibility** -- are distractors plausible confusions (not random noise),
   and none of them *also correct* ("also-correct" is a major defect, not a style nit)?
4. **Naturalness** -- does the sentence/prompt read as something a native speaker would
   actually write or say?
5. **Target-word anchoring** -- does the exercise actually test the target word/sense, not
   some other word in the sentence? **Known defect class: the target word appears only
   inside a compound word**, so the exercise is really testing the compound, not the
   target sense. Flag this explicitly as a major defect when you see it.
6. **L1 (`phonetic_recognition`) validity, if shown** -- L1 is an audio-confusable-only,
   listening exercise: pitch-accent-only distractor pairs are NOT valid, because TTS only
   renders one form. A pitch-accent-only distractor is a major defect, not a style nit.

Return one JSON line per (sense_id, level) you evaluated:
`{"sense_id": ..., "level": ..., "preferred": "A" | "B" | "tie", "major_defects_A": [...], "major_defects_B": [...], "notes": "..."}`
`major_defects_A` / `major_defects_B` are short strings from the checklist above (e.g.
"also-correct distractor", "compound-word anchoring", "pitch-accent-only L1 pair"), empty
list if none found. Do not guess which side is the candidate or reference -- you are not
told, and should not try to infer it from formatting.


## sense 39187, level 9

#### Pack A
### Level 9 (sense 39187, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "自らの意見を持つ。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "自らの",
    "意見を",
    "持つ"
  ],
  "chunk_count": 3,
  "target_word": "自ら",
  "schema_version": 2,
  "shuffled_chunks": [
    "持つ",
    "意見を",
    "自らの"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "自らの意見を持つ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "自らを",
    "信じることが",
    "大切だ"
  ],
  "chunk_count": 3,
  "target_word": "自ら",
  "schema_version": 2,
  "shuffled_chunks": [
    "信じることが",
    "大切だ",
    "自らを"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "自らを信じることが大切だ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "自らを信じることが大切だ。"
}
```

#### Pack B
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼女は自ら行動しています。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼女は自ら行動しています。",
  "chunks": [
    "彼女は",
    "自ら行動して",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "います",
    "自ら行動して",
    "彼女は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は自らその問題を解決しました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は自らその問題を解決しました。",
  "chunks": [
    "彼は",
    "自らその問題を",
    "解決しました"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "自らその問題を",
    "解決しました",
    "彼は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```

---
