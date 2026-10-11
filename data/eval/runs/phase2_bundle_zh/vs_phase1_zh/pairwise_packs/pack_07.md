# Pairwise review pack 07

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


## sense 11315, level 4

#### Pack A
### Level 4 (sense 11315, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "医生给病人注射了这种___。",
  "original_sentence": "医生给病人注射了这种拮抗剂。",
  "target_word": "拮抗剂",
  "word": "拮抗剂",
  "answer": {
    "accepted": [
      "拮抗剂",
      "种",
      "受体拮抗剂"
    ],
    "accepted_normalized": [
      "拮抗剂",
      "种",
      "受体拮抗剂"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "醫生給病人注射了這種___。",
    "original_sentence": "醫生給病人注射了這種拮抗劑。",
    "target_word": "拮抗劑",
    "word": "拮抗劑",
    "answer": {
      "accepted": [
        "拮抗劑",
        "種",
        "受體拮抗劑"
      ],
      "accepted_normalized": [
        "拮抗劑",
        "種",
        "受體拮抗劑"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这种___的疗效非常显著。",
  "original_sentence": "这种拮抗剂的疗效非常显著。",
  "target_word": "拮抗剂",
  "word": "拮抗剂",
  "answer": {
    "accepted": [
      "拮抗剂",
      "种",
      "受体拮抗剂"
    ],
    "accepted_normalized": [
      "拮抗剂",
      "种",
      "受体拮抗剂"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這種___的療效非常顯著。",
    "original_sentence": "這種拮抗劑的療效非常顯著。",
    "target_word": "拮抗劑",
    "word": "拮抗劑",
    "answer": {
      "accepted": [
        "拮抗劑",
        "種",
        "受體拮抗劑"
      ],
      "accepted_normalized": [
        "拮抗劑",
        "種",
        "受體拮抗劑"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

#### Pack B
### Level 4 (sense 11315, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这种___可以阻止病毒进入细胞。",
  "original_sentence": "这种拮抗剂可以阻止病毒进入细胞。",
  "target_word": "拮抗剂",
  "word": "拮抗剂",
  "answer": {
    "accepted": [
      "拮抗剂",
      "种",
      "瓶",
      "受体拮抗剂"
    ],
    "accepted_normalized": [
      "拮抗剂",
      "种",
      "瓶",
      "受体拮抗剂"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這種___可以阻止病毒進入細胞。",
    "original_sentence": "這種拮抗劑可以阻止病毒進入細胞。",
    "target_word": "拮抗劑",
    "word": "拮抗劑",
    "answer": {
      "accepted": [
        "拮抗劑",
        "種",
        "瓶",
        "受體拮抗劑"
      ],
      "accepted_normalized": [
        "拮抗劑",
        "種",
        "瓶",
        "受體拮抗劑"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

---

## sense 11315, level 9

#### Pack A
### Level 9 (sense 11315, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "我们需要研究这种拮抗剂的副作用。",
  "hant": {
    "original_sentence": "我們需要研究這種拮抗劑的副作用。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "我们需要研究这种拮抗剂的副作用。",
  "chunks": [
    "我们需要",
    "研究这种",
    "拮抗剂的副作用"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "我们需要",
    "拮抗剂的副作用",
    "研究这种"
  ],
  "target_word": "拮抗剂",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "我們需要研究這種拮抗劑的副作用。",
    "chunks": [
      "我們需要",
      "研究這種",
      "拮抗劑的副作用"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "我們需要",
      "拮抗劑的副作用",
      "研究這種"
    ],
    "target_word": "拮抗劑",
    "chunk_count": 3
  }
}
```

#### Pack B
### Level 9 (sense 11315, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "新的拮抗剂正在实验室里测试。",
  "hant": {
    "original_sentence": "新的拮抗劑正在實驗室裡測試。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "新的拮抗剂正在实验室里测试。",
  "chunks": [
    "新的",
    "拮抗剂正在",
    "实验室里测试"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "新的",
    "实验室里测试",
    "拮抗剂正在"
  ],
  "target_word": "拮抗剂",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "新的拮抗劑正在實驗室裡測試。",
    "chunks": [
      "新的",
      "拮抗劑正在",
      "實驗室裡測試"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "新的",
      "實驗室裡測試",
      "拮抗劑正在"
    ],
    "target_word": "拮抗劑",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "拮抗剂的副作用需要密切观察。",
  "hant": {
    "original_sentence": "拮抗劑的副作用需要密切觀察。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "拮抗剂的副作用需要密切观察。",
  "chunks": [
    "拮抗剂的",
    "副作用需要",
    "密切观察"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "副作用需要",
    "密切观察",
    "拮抗剂的"
  ],
  "target_word": "拮抗剂",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "拮抗劑的副作用需要密切觀察。",
    "chunks": [
      "拮抗劑的",
      "副作用需要",
      "密切觀察"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "副作用需要",
      "密切觀察",
      "拮抗劑的"
    ],
    "target_word": "拮抗劑",
    "chunk_count": 3
  }
}
```

---
