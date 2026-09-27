# Pairwise review pack 09

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
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "自らの頭で考えて行動できる人です。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "自らの頭で考えて行動できる人です。",
  "chunks": [
    "自らの",
    "頭で",
    "考えて",
    "行動できる人です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "行動できる人です",
    "頭で",
    "自らの",
    "考えて"
  ],
  "target_word": "自ら",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "自らの意見を堂々と言えます。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "自らの意見を堂々と言えます。",
  "chunks": [
    "自らの",
    "意見を",
    "堂々と",
    "言えます"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "堂々と",
    "意見を",
    "言えます",
    "自らの"
  ],
  "target_word": "自ら",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "自らの気持ちを大切にします。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "自らの気持ちを大切にします。",
  "chunks": [
    "自らの",
    "気持ちを",
    "大切にします"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "大切にします",
    "気持ちを",
    "自らの"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "自らが決めた道です。"
}
```

---
