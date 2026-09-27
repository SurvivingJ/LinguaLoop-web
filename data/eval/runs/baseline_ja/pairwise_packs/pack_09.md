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


## sense 39187, level 4

#### Pack A
### Level 4 (sense 39187, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
    ]
  },
  "input_mode": "ime",
  "target_word": "自ら",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "sentence_with_blank": "変化に適応し、___の価値を高め続ける姿勢が、これからの職場では強く求められる。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
    ]
  },
  "input_mode": "ime",
  "target_word": "自ら",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "自らの過ちを認めた。",
  "sentence_with_blank": "___の過ちを認めた。"
}
```

#### Pack B
### Level 4 (sense 39187, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "変化に適応し、___の価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "original_sentence": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ],
    "accepted_normalized": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": null
  },
  "input_mode": "ime"
}
```
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___の意思で毎日勉強しています。",
  "original_sentence": "自らの意思で毎日勉強しています。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ],
    "accepted_normalized": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": null
  },
  "input_mode": "ime"
}
```

---

## sense 39187, level 6

#### Pack A
### Level 6 (sense 39187, difficulty 8)
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "高めている彼女は自らを。",
      "is_correct": false
    },
    {
      "text": "彼女は自らを高めている。",
      "is_correct": true
    },
    {
      "text": "彼女は自らが高めている。",
      "is_correct": false
    },
    {
      "text": "彼女は自らを高まっている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「高める」の対象は「を」で示す。「が」は誤り。 活用：他動詞は「高める」であり、自動詞「高まる」との混同は誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "自ら"
}
```

#### Pack B
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "高めている彼女は自らを。",
      "is_correct": false
    },
    {
      "text": "自らを信じています。",
      "is_correct": true
    },
    {
      "text": "彼女は自らを高まっている。",
      "is_correct": false
    },
    {
      "text": "彼女は自らが高めている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「高める」の対象は「を」で示す。「が」は誤り。 活用：他動詞は「高める」であり、自動詞「高まる」との混同は誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "自ら"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "自ら",
  "relation": "antonym",
  "options": [
    "他人",
    "自分",
    "彼",
    "我々"
  ],
  "correct_answer": "他人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "自分自身を指す言葉。",
      "explanation": "自分以外の人を指し、「自ら」の対義語となる"
    }
  }
}
```

---

## sense 39187, level 7

#### Pack A
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らに肌で実感していくことになります。",
      "is_correct": false,
      "error_description": "「自ら」が名詞を修飾する場合は助詞「の」を用いて「自らの肌」とするのが正しい用法です。「に」は誤りです。"
    },
    {
      "text": "自らの手で丁寧に掃除をしています。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "自らの手で花を育てています。",
      "is_correct": true
    },
    {
      "text": "自らを信じています。",
      "is_correct": true
    },
    {
      "text": "自ら意思で毎日勉強しています。",
      "is_correct": false,
      "error_description": "「自ら」が名詞を修飾する場合は、「自らの」と助詞「の」を伴うのが正しい用法です。"
    },
    {
      "text": "自らの意思で毎日勉強しています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 39187, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らを価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": false,
      "error_description": "助詞：連体修飾の「の」を「を」に置き換えるのは誤り。"
    },
    {
      "text": "彼は自らの力で成功した。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "彼女は自らを高めている。",
      "is_correct": true
    },
    {
      "text": "彼は自ら行動する。",
      "is_correct": true
    },
    {
      "text": "自らの過ちが認めた。",
      "is_correct": false,
      "error_description": "助詞：他動詞「認める」の対象は「を」で示す。「が」は誤り。"
    },
    {
      "text": "自らの過ちを認めた。",
      "is_correct": true
    }
  ]
}
```

---

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

---
