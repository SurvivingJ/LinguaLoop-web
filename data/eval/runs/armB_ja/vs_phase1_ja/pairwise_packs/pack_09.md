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


## sense 53352, level 7

#### Pack A
### Level 7 (sense 53352, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "目に見えない菌の働きは、ただ食べ物を長持ちさせる方法を超え、私たちの食生活をより美味しく豊かにする素晴らしい技術です。",
      "is_correct": true
    },
    {
      "text": "この活動は、ただ植物を育てることを超え、自然環境を守りながら、人々の絆を深めることにもつながっています。",
      "is_correct": true
    },
    {
      "text": "気温が三十度が超えた。",
      "is_correct": false,
      "error_description": "助詞の混同：超える対象は「を」で示す。「三十度が」ではなく「三十度を」が正しい。"
    },
    {
      "text": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼女の能力は、私たちの予想を超えています。",
      "is_correct": true
    },
    {
      "text": "明日、参加者は百人を超えた。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り：未来の「明日」に過去形「超えた」は合わない。「超える」が正しい。"
    },
    {
      "text": "予想を超えて、とても嬉しかったです。",
      "is_correct": true
    },
    {
      "text": "予想を超え、そこには素晴らしい景色が広がっていました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 53352, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "山の高さは三千メートルを超えます。",
      "is_correct": true
    },
    {
      "text": "温度が基準を超えています。",
      "is_correct": true
    },
    {
      "text": "明日、参加者は百人を超えた。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り：未来の「明日」に過去形「超えた」は合わない。「超える」が正しい。"
    },
    {
      "text": "制限時間を超えてはいけません。",
      "is_correct": true
    }
  ]
}
```

---
