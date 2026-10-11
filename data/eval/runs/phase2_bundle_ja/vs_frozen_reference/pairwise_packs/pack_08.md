# Pairwise review pack 08

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


## sense 53352, level 9

#### Pack A
### Level 9 (sense 53352, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "予想以上の人数が集まり、定員を超えてしまいました。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "予想以上の人数が集まり、定員を超えてしまいました。",
  "chunks": [
    "予想以上の",
    "人数が",
    "集まり",
    "定員を",
    "超えて",
    "しまいました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "予想以上の",
    "集まり",
    "超えて",
    "しまいました",
    "人数が",
    "定員を"
  ],
  "target_word": "超え",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ている。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ている。",
  "chunks": [
    "その行為は",
    "単なるガーデニングの",
    "域を超え",
    "自然の摂理に",
    "対する静かなる祈りに",
    "も似ている"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "自然の摂理に",
    "域を超え",
    "その行為は",
    "単なるガーデニングの",
    "対する静かなる祈りに",
    "も似ている"
  ],
  "target_word": "超え",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 53352, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "参加者は",
    "百人を",
    "超えて",
    "いる"
  ],
  "chunk_count": 4,
  "target_word": "超え",
  "schema_version": 2,
  "shuffled_chunks": [
    "百人を",
    "参加者は",
    "超えて",
    "いる"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "参加者は百人を超えている。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "参加者は百人を超えている。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "学校イベントと",
    "いう儀礼的空間において",
    "Tシャツデザインは",
    "単なる装飾を超え集団内の",
    "微細な階層や個性の顕現と",
    "して機能し得る"
  ],
  "chunk_count": 6,
  "target_word": "超え",
  "schema_version": 2,
  "shuffled_chunks": [
    "単なる装飾を超え集団内の",
    "Tシャツデザインは",
    "学校イベントと",
    "いう儀礼的空間において",
    "微細な階層や個性の顕現と",
    "して機能し得る"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "学校イベントという儀礼的空間において、Tシャツデザインは単なる装飾を超え、集団内の微細な階層や個性の顕現として機能し得る。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "学校イベントという儀礼的空間において、Tシャツデザインは単なる装飾を超え、集団内の微細な階層や個性の顕現として機能し得る。"
}
```

---
