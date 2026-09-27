# Pairwise review pack 02

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


## sense 35001, level 9

#### Pack A
### Level 9 (sense 35001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "機械を使ってください。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "機械を使ってください。",
  "chunks": [
    "機械を",
    "使って",
    "ください"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "機械を",
    "ください",
    "使って"
  ],
  "target_word": "機械",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "機械を修理できます。"
}
```

#### Pack B
### Level 9 (sense 35001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "この機械は簡単に操作できます。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は機械を修理できます。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は機械を修理できます。",
  "chunks": [
    "彼は",
    "機械を",
    "修理できます"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "彼は",
    "修理できます",
    "機械を"
  ],
  "target_word": "機械",
  "chunk_count": 3
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "増え",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "correct_answer": "ふえる",
  "word": "増え",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "[ɸɯeɾɯ]",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "断える",
    "フリル",
    "増える",
    "越える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "越える": "「越える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「こ」、一部の音の違い）。",
    "フリル": "「フリル」は「増える」と一モーラだけ異なる実在語です（2モーラ目: 「え」→「り」、一部の音の違い）。",
    "断える": "「断える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "ふえる",
  "options": [
    "調理",
    "増え",
    "重量",
    "増える"
  ],
  "correct_answer": "増え",
  "word": "増え",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "増える": "homophone",
    "重量": "component",
    "調理": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "増え",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "correct_answer": "ふえる",
  "word": "増え",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "/ɸɯeɾɯ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "萌える",
    "デュエル",
    "返る",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "萌える": "「萌える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「も」、一部の音の違い）。",
    "返る": "「返る」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「か」、一部の音の違い）。",
    "デュエル": "「デュエル」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「でゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "ふえる",
  "options": [
    "調理",
    "増え",
    "重量",
    "増える"
  ],
  "correct_answer": "増え",
  "word": "増え",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "増える": "homophone",
    "重量": "component",
    "調理": "component"
  }
}
```

---

## sense 35017, level 2

#### Pack A
### Level 2 (sense 35017, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "数量や程度が多くなる。",
    "飛行機の主要な翼で、揚力を発生させて機体を支える重要な部分。",
    "問題や質問に対する答え。",
    "生物が成長して大きくなる。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to remain; to be left — something still being there, unused, in a place or state",
        "文化や習慣などの違いを理解する、または認識するという意味です。",
        "同じであること。",
        "数量や程度が多くなる。"
      ],
      "correct_answer": "数量や程度が多くなる。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35017, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "数量や回数が非常に多いこと。",
    "投資や仕事などで、複数の資産や作品を組み合わせた集まり。リスクを分散するために、異なる種類のものをバランスよく持つこと。",
    "数量や程度が多くなる。",
    "ある期間の中で、終わりに近い部分。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "小さくて丸い形をしたもの。また、そのような形をした一つ一つのもの。",
        "关注 —— 把注意力特别集中在某件事或某种现象上加以思考",
        "元素の一つ。原子番号6、記号C。すべての有機物の基本となる元素で、ダイヤモンドや黒鉛、二酸化炭素など様々な形で存在する。",
        "数量や程度が多くなる。"
      ],
      "correct_answer": "数量や程度が多くなる。"
    }
  }
}
```

---

## sense 35017, level 3

#### Pack A
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も___ています。",
  "original_sentence": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も増えています。",
  "correct_answer": "増え",
  "options": [
    "増え",
    "下がり",
    "変わり",
    "重なり"
  ],
  "explanation": "正解です。文脈に最も適しています。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "___た友達と遊びに行きます。",
  "original_sentence": "増えた友達と遊びに行きます。",
  "correct_answer": "増えた",
  "options": [
    "減った",
    "増えた",
    "降った",
    "壊れた"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "これ以上は負担が___ませんように。",
  "original_sentence": "これ以上は負担が増えませんように。",
  "correct_answer": "増え",
  "options": [
    "下がり",
    "重なり",
    "増やし",
    "増え"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

---

## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "最近、犬を飼う人が___ています。",
  "original_sentence": "最近、犬を飼う人が増えています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
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
**morphology_slot** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "最近、犬を飼う人が___ています。",
  "original_sentence": "最近、犬を飼う人が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形",
  "options": [
    "増えない",
    "増えた",
    "増え",
    "増える"
  ],
  "explanation": "「います」に接続するため連用形が必要",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___ない友達の数を心配しています。",
  "original_sentence": "増えない友達の数を心配しています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
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
**morphology_slot** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___ない友達の数を心配しています。",
  "original_sentence": "増えない友達の数を心配しています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "未然形",
  "options": [
    "増え",
    "増えた",
    "増える",
    "増えて"
  ],
  "explanation": "後ろの否定の助動詞「ない」に接続する未然形として正しい。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
### Level 4 (sense 35017, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "最近、ゴミの量が___ています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
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
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "最近、ゴミの量が___ています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "options": [
    "冷え",
    "増え",
    "枯れ",
    "晴れ"
  ],
  "explanation": "て形。「～てきた」の形に合う。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "最近、ゴミの量___増えています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "options": [
    "に",
    "で",
    "が",
    "を"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」が表す現象の主体を提示する主格助詞である"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "雨が降って水が___ました。",
  "original_sentence": "雨が降って水が増えました。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
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
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "雨が降って水が___ました。",
  "original_sentence": "雨が降って水が増えました。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "options": [
    "晴れ",
    "冷え",
    "枯れ",
    "増え"
  ],
  "explanation": "て形の語幹。「病気になる人が～いる」に合う。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "雨___降って水が増えました。",
  "original_sentence": "雨が降って水が増えました。",
  "options": [
    "を",
    "が",
    "に",
    "で"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語（主体）を標示する格助詞"
    }
  }
}
```

---

## sense 35017, level 7

#### Pack A
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も増えています。",
      "is_correct": true
    },
    {
      "text": "車の数が年々増えいる。",
      "is_correct": false,
      "error_description": "「～ている」の形で「て」が抜けている誤り。"
    },
    {
      "text": "最近、ゴミの量が増えています。",
      "is_correct": true
    },
    {
      "text": "私の町で外国人が増えています。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "増えた友達と遊びに行きます。",
      "is_correct": true
    },
    {
      "text": "雨が降って水が増えました。",
      "is_correct": true
    },
    {
      "text": "増えることを期待しています。",
      "is_correct": true
    },
    {
      "text": "しかし、その無骨な外観や維持管理の難しさから、現在ではその価値が再評価される一方で、取り壊されるケースも増えいます。",
      "is_correct": false,
      "error_description": "「～ています」の「て」が抜けている誤り。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "最近、犬を飼う人が増えています。",
      "is_correct": true
    },
    {
      "text": "しかし、古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースも増えています。",
      "is_correct": true
    },
    {
      "text": "テストの点が少し増えました。",
      "is_correct": true
    },
    {
      "text": "最近、犬を飼う人に増えています。",
      "is_correct": false,
      "error_description": "「増える」は自動詞であり、変化する主体を示す助詞は「が」を使います。「に」を使うのは誤りです。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "増えない友達の数を心配しています。",
      "is_correct": true
    },
    {
      "text": "良い点が取れて、自信が増えてきました。",
      "is_correct": true
    },
    {
      "text": "日本の人口を増えています。",
      "is_correct": false,
      "error_description": "「増える」は自動詞であり、増加する主体を示す助詞は「を」ではなく「が」です。「を」を使う場合は他動詞の「増やす」を用います。"
    },
    {
      "text": "これ以上は負担が増えませんように。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35017, level 9

#### Pack A
### Level 9 (sense 35017, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "増える税金について意見を言いたいです。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "増える税金について意見を言いたいです。",
  "chunks": [
    "増える税金に",
    "ついて意見を",
    "言いたいです"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "言いたいです",
    "ついて意見を",
    "増える税金に"
  ],
  "target_word": "増える",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "増えるゴミの問題について考えます。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "増えるゴミの問題について考えます。",
  "chunks": [
    "増えるゴミの",
    "問題に",
    "ついて考えます"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "ついて考えます",
    "増えるゴミの",
    "問題に"
  ],
  "target_word": "増える",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 35017, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "増えたゴミを自分で減らします。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "増えたゴミを自分で減らします。",
  "chunks": [
    "増えたゴミを",
    "自分で",
    "減らします"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "減らします",
    "自分で",
    "増えたゴミを"
  ],
  "target_word": "増え",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "最近、この町の人口が増えています。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "最近、この町の人口が増えています。",
  "chunks": [
    "最近",
    "この町の",
    "人口が",
    "増えて",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "います",
    "人口が",
    "最近",
    "この町の",
    "増えて"
  ],
  "target_word": "増え",
  "chunk_count": 5
}
```

---

## sense 35111, level 1

#### Pack A
### Level 1 (sense 35111, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "ipa": "/joɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "ネル",
    "世々",
    "彫る",
    "因る"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "世々": "「世々」は「因る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「よ」、一部の音の違い）。",
    "ネル": "「ネル」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「ね」、一部の音の違い）。",
    "彫る": "「彫る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「え」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35111, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "ipa": "/joɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "降る",
    "因る",
    "余儀",
    "酔い"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "酔い": "「酔い」は「因る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「い」、一部の音の違い）。",
    "降る": "「降る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「ふ」、一部の音の違い）。",
    "余儀": "「余儀」は「因る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「ぎ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "よる",
  "options": [
    "契機",
    "太谿",
    "天候",
    "因る"
  ],
  "correct_answer": "因る",
  "word": "因る",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "太谿": "component",
    "天候": "component",
    "契機": "component"
  }
}
```

---

## sense 35111, level 2

#### Pack A
### Level 2 (sense 35111, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "よる",
  "pronunciation": "よる",
  "correct_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "options": [
    "朝に食べる食事。",
    "前に話したことや、これから話すことを指し示すときに使う言葉。状況や物事を具体的に示す。",
    "目標や目的地に向けて進むこと。また、ある方向へ動くこと。",
    "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "よる",
  "pronunciation": "よる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "business — an activity or organization buying and selling goods or services for profit",
        "to devour (indulge greedily)",
        "活発に活動する状態になること。または、その状態。",
        "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
      ],
      "correct_answer": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35111, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "correct_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "options": [
    "人々が共通の目的や感情によって強く結びつき、まとまること。",
    "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
    "物価が上昇するインフレと、経済活動が停滞する不況が同時に発生する状態。",
    "物事の端の方、または場所の隅の部分。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "車や機械から、いらない空気やけむりを出すこと。",
        "hundreds",
        "做 —— 「する」的礼貌说法，用来礼貌地表达动作或状态",
        "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
      ],
      "correct_answer": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
    }
  }
}
```

---

## sense 35111, level 4

#### Pack A
### Level 4 (sense 35111, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "地震に___家が壊れた。",
  "original_sentence": "地震に因って家が壊れた。",
  "target_word": "因って",
  "word": "因る",
  "answer": {
    "accepted": [
      "因って"
    ],
    "accepted_normalized": [
      "因って"
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "地震に___家が壊れた。",
  "original_sentence": "地震に因って家が壊れた。",
  "correct_answer": "因って",
  "base_form": "因る",
  "form_label": "て形",
  "options": [
    "因る",
    "因ります",
    "因って",
    "因らない"
  ],
  "explanation": "「に」に呼応して原因・理由を表し後続の文へ接続するには、て形が適切である",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "因って"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "地震___因って家が壊れた。",
  "original_sentence": "地震に因って家が壊れた。",
  "options": [
    "へ",
    "に",
    "から",
    "で"
  ],
  "correct_answer": "に",
  "target_word": "因って",
  "error_tags": {
    "で": "instrument",
    "から": "source_vs_goal",
    "へ": "direction"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "原因・理由を表す格助詞「に」が「因る」と呼応して用いられる"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "運に___結果が変わる。",
  "original_sentence": "運に因って結果が変わる。",
  "target_word": "因って",
  "word": "因る",
  "answer": {
    "accepted": [
      "因って"
    ],
    "accepted_normalized": [
      "因って"
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "運に___結果が変わる。",
  "original_sentence": "運に因って結果が変わる。",
  "correct_answer": "因って",
  "base_form": "因る",
  "form_label": "て形",
  "options": [
    "因って",
    "因れる",
    "因ります",
    "因らない"
  ],
  "explanation": "「て形」は原因・理由を表し、後続の句に自然に接続する",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "因って"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "運___因って結果が変わる。",
  "original_sentence": "運に因って結果が変わる。",
  "options": [
    "に",
    "で",
    "へ",
    "を"
  ],
  "correct_answer": "に",
  "target_word": "因って",
  "error_tags": {
    "で": "instrument",
    "を": "object_marking",
    "へ": "direction"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「因る」は原因・理由を表す名詞に助詞「に」を伴って用いられる。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35111, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "まず、季節の移ろいと共に採取された植物は、熱と水に___てその奥底に秘められた色素を解放される。",
  "original_sentence": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "target_word": "よっ",
  "word": "よる",
  "answer": {
    "accepted": [
      "よっ"
    ],
    "accepted_normalized": [
      "よっ"
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "まず、季節の移ろいと共に採取された植物は、熱と水に___てその奥底に秘められた色素を解放される。",
  "original_sentence": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "correct_answer": "より",
  "base_form": "因る",
  "form_label": "連用形（〜により）",
  "options": [
    "より",
    "よった",
    "よれば",
    "よって"
  ],
  "explanation": "「これにより」は連用形で後に文が続く接続的な形。",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よっ"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "まず、季節の移ろいと共___採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "original_sentence": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "options": [
    "で",
    "が",
    "を",
    "に"
  ],
  "correct_answer": "に",
  "target_word": "よっ",
  "error_tags": {
    "で": "instrument",
    "が": "other",
    "を": "object_marking"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "原因・理由を表す動詞「よる」は格助詞「に」をとる"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "センサー等を用いた技術導入は、収量の安定化に___収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
  "target_word": "より",
  "word": "よる",
  "answer": {
    "accepted": [
      "より"
    ],
    "accepted_normalized": [
      "より"
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "センサー等を用いた技術導入は、収量の安定化に___収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
  "correct_answer": "よっ",
  "base_form": "因る",
  "form_label": "連用形＋て形（〜によって）",
  "options": [
    "よっ",
    "よった",
    "より",
    "よれば"
  ],
  "explanation": "「によって」は原因・手段を表す連用形＋て形の固定表現。",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "より"
}
```

---
