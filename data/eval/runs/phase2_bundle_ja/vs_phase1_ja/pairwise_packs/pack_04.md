# Pairwise review pack 04

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


## sense 35055, level 4

#### Pack A
### Level 4 (sense 35055, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この問題は___中で議論されています。",
  "original_sentence": "この問題は世界中で議論されています。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題は世界中___議論されています。",
  "original_sentence": "この問題は世界中で議論されています。",
  "options": [
    "と",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "で",
  "target_word": "世界",
  "error_tags": {
    "を": "",
    "に": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "動作が行われる範囲・場所を示す助詞として自然。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "平和な___を作るのは難しいことです。",
  "original_sentence": "平和な世界を作るのは難しいことです。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
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

#### Pack B
### Level 4 (sense 35055, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "私たちの会社は、___の人々に喜んでもらえるような商品を開発しています。",
  "original_sentence": "私たちの会社は、世界の人々に喜んでもらえるような商品を開発しています。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界観",
      "世界地図",
      "世界一"
    ],
    "accepted_normalized": [
      "世界",
      "世界観",
      "世界地図",
      "世界一"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___の人々と友達になりたいです。",
  "original_sentence": "世界の人々と友達になりたいです。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界観",
      "世界地図",
      "世界一"
    ],
    "accepted_normalized": [
      "世界",
      "世界観",
      "世界地図",
      "世界一"
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

## sense 35055, level 6

#### Pack A
### Level 6 (sense 35055, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この本は世界の人々に走られています。",
      "is_correct": false
    },
    {
      "text": "この本は世界の人々に泳がれています。",
      "is_correct": false
    },
    {
      "text": "この本は世界の人々に読まれています。",
      "is_correct": true
    },
    {
      "text": "この本は世界の人々に飲まれています。",
      "is_correct": false
    }
  ],
  "explanation": "本は「走る」という動作を行わない。 本は「飲む」という動作の対象にはなり得ない。 本は「泳ぐ」という動作を行わない。",
  "target_word": "世界"
}
```

#### Pack B
### Level 6 (sense 35055, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界で広くて、とても面白いです。",
      "is_correct": false
    },
    {
      "text": "世界は広くて、とても面白いです。",
      "is_correct": true
    },
    {
      "text": "世界は広くて、とても面白いでした。",
      "is_correct": false
    },
    {
      "text": "私は一匹の世界を旅しました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「世界」に「一匹」は使えません。「一つ」などを用います。 助詞の混同：文の主題を示すには「は」を使い、「世界は広くて」とするのが正しいです。 活用・アスペクトの誤り：形容詞「面白い」の過去形や状態を表す際は「面白かった」を用います。",
  "target_word": "世界"
}
```

---

## sense 35055, level 9

#### Pack A
### Level 9 (sense 35055, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "世界のいろいろな国を知っています。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "世界のいろいろな国を知っています。",
  "chunks": [
    "世界の",
    "いろいろな国を",
    "知って",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "知って",
    "います",
    "世界の",
    "いろいろな国を"
  ],
  "target_word": "世界",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "世界は広くて、とても面白いです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "世界は広くて、とても面白いです。",
  "chunks": [
    "世界は",
    "広くて",
    "とても面白いです"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "広くて",
    "世界は",
    "とても面白いです"
  ],
  "target_word": "世界",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 35055, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "世界は私たちのものであり、未来です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "世界は私たちのものであり、未来です。",
  "chunks": [
    "世界は",
    "私たちの",
    "ものであり",
    "未来です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "ものであり",
    "未来です",
    "世界は",
    "私たちの"
  ],
  "target_word": "世界",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "広い世界を見てみたいですね。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "広い世界を見てみたいですね。",
  "chunks": [
    "広い世界を",
    "見て",
    "みたいですね"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "見て",
    "広い世界を",
    "みたいですね"
  ],
  "target_word": "世界",
  "chunk_count": 3
}
```

---

## sense 35093, level 1

#### Pack A
### Level 1 (sense 35093, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "技術",
  "options": [
    "ぎじゅづ",
    "ぎしゅつ",
    "ぎじゅつ",
    "きじゅつ"
  ],
  "correct_answer": "ぎじゅつ",
  "word": "技術",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ぎじゅつ",
  "options": [
    "技術",
    "衝撃",
    "芸術",
    "美術"
  ],
  "correct_answer": "技術",
  "word": "技術",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "衝撃": "component",
    "芸術": "component",
    "美術": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35093, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "技術",
  "options": [
    "ぎじゅづ",
    "ぎしゅつ",
    "ぎじゅつ",
    "きじゅつ"
  ],
  "correct_answer": "ぎじゅつ",
  "word": "技術",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "ipa": "[gʲidʑutsɯ]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "武術",
    "技術",
    "著述",
    "邪術"
  ],
  "correct_answer": "技術",
  "explanation": "正解です。「技術」は「物を作ったり処理したりする、専門的な方法や能力。」という意味です。",
  "distractor_explanations": {
    "武術": "「武術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ぶ」、一部の音の違い）。",
    "邪術": "「邪術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「じゃ」、一部の音の違い）。",
    "著述": "「著述」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ちょ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ぎじゅつ",
  "options": [
    "技術",
    "衝撃",
    "芸術",
    "美術"
  ],
  "correct_answer": "技術",
  "word": "技術",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "衝撃": "component",
    "芸術": "component",
    "美術": "component"
  }
}
```

---

## sense 35093, level 2

#### Pack A
### Level 2 (sense 35093, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "correct_definition": "物を作ったり処理したりする、専門的な方法や能力。",
  "options": [
    "人間と一緒に暮らすことが多い、哺乳類の動物。吠える声やしっぽを振る行動が特徴。",
    "物を作ったり処理したりする、専門的な方法や能力。",
    "物事を引っ張って進めること。特に、先頭に立って全体を動かすこと。",
    "物事の内容や意味を、わかるように述べること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物を作ったり処理したりする、専門的な方法や能力。",
        "points",
        "あるものをこえて、もっと上にいくこと。",
        "periodic; regular — happening repeatedly at set intervals, and that state"
      ],
      "correct_answer": "物を作ったり処理したりする、専門的な方法や能力。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35093, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "correct_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "options": [
    "物事の数量や程度が、以前より少なくなること。",
    "本。書物。文字や絵が印刷された、綴じた紙の集まり。",
    "広く行き渡っていること。どこにでもあること。",
    "物を作ったり処理したりするための、専門的な方法や能力。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物を作ったり処理したりするための、専門的な方法や能力。",
        "病気やけがを治すために、薬を使ったり、手術をしたりすること。",
        "pursuit; to pursue — actively and persistently seeking to achieve a goal or ideal",
        "to put in (include)"
      ],
      "correct_answer": "物を作ったり処理したりするための、専門的な方法や能力。"
    }
  }
}
```

---

## sense 35093, level 4

#### Pack A
### Level 4 (sense 35093, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "近年、センサーやデータ解析の___を活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析の技術を活用した「精密農業」が注目されています。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析の技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析の技術を活用した「精密農業」が注目されています。",
  "options": [
    "を",
    "が",
    "で",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「活用する」の直接目的語を標示する。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "最新の___を使ってロボットを作りました。",
  "original_sentence": "最新の技術を使ってロボットを作りました。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的"
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
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "最新の技術___使ってロボットを作りました。",
  "original_sentence": "最新の技術を使ってロボットを作りました。",
  "options": [
    "が",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "が": "topic_vs_subject",
    "で": "instrument",
    "に": "location_vs_target"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「使う」の直接目的語を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35093, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "近年、センサーやデータ解析___を活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析技術を活用した「精密農業」が注目されています。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析技術を活用した「精密農業」が注目されています。",
  "options": [
    "に",
    "と",
    "を",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「技術を活用した」が正しい目的語のマーカーです。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "医療___の進歩は人々を助けます。",
  "original_sentence": "医療技術の進歩は人々を助けます。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
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
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "医療技術___進歩は人々を助けます。",
  "original_sentence": "医療技術の進歩は人々を助けます。",
  "options": [
    "で",
    "に",
    "を",
    "の"
  ],
  "correct_answer": "の",
  "target_word": "技術",
  "error_tags": {
    "を": "",
    "に": "",
    "で": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「医療技術の進歩」のように、名詞を修飾する場合は「の」が適切です。"
    }
  }
}
```

---

## sense 35093, level 9

#### Pack A
### Level 9 (sense 35093, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "プログラミングの技術が上達しました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "プログラミングの技術が上達しました。",
  "chunks": [
    "プログラミングの",
    "技術が",
    "上達しました"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "技術が",
    "上達しました",
    "プログラミングの"
  ],
  "target_word": "技術",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼の料理の技術は素晴らしいです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼の料理の技術は素晴らしいです。",
  "chunks": [
    "彼の",
    "料理の",
    "技術は",
    "素晴らしいです"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "素晴らしいです",
    "彼の",
    "料理の",
    "技術は"
  ],
  "target_word": "技術",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 35093, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "技術が進歩して生活が便利になりました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "技術が進歩して生活が便利になりました。",
  "chunks": [
    "技術が",
    "進歩して",
    "生活が",
    "便利になりました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "便利になりました",
    "技術が",
    "生活が",
    "進歩して"
  ],
  "target_word": "技術",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼の技術は本当に素晴らしいです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼の技術は本当に素晴らしいです。",
  "chunks": [
    "彼の",
    "技術は",
    "本当に",
    "素晴らしいです"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "素晴らしいです",
    "彼の",
    "技術は",
    "本当に"
  ],
  "target_word": "技術",
  "chunk_count": 4
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
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "ipa": "joɾu",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "より",
    "因る",
    "よる",
    "よる"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "より": "",
    "よる": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
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
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "よる",
  "pronunciation": "よる",
  "correct_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "options": [
    "必要なものや情報が不足している状態。欠けていること。",
    "ある物や人が、場所を高い方から低い方へと移動することを言います。",
    "図書館や博物館などが、本や作品などを収集して保管していること。また、そのもの。",
    "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "よる",
  "pronunciation": "よる",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "一しゅうかんごとに。",
        "the best; number one — the highest in degree among many things, or the most outstanding",
        "礼貌语尾（ます）",
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

---

## sense 35111, level 3

#### Pack A
### Level 3 (sense 35111, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "天然染料に___染色の美しさは、素材との対話という儀礼的な過程に依るものである。",
  "original_sentence": "天然染料による染色の美しさは、素材との対話という儀礼的な過程に依るものである。",
  "correct_answer": "依る",
  "options": [
    "拠る",
    "寄る",
    "依る",
    "因る"
  ],
  "explanation": "正解。文脈「〜に依るものである」に適合する原因・理由を表す動詞です。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よる"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "建築の意味が絶えず更新されるのは、見る者の主観的な解釈に依る部分が大きいためである。",
  "original_sentence": "建築の意味が絶えず更新されるのは、見る者の主観的な解釈に依る部分が大きいためである。",
  "correct_answer": "依る",
  "options": [
    "因る",
    "依る",
    "拠る",
    "寄る"
  ],
  "explanation": "正解。文脈「〜に依るものである」に適合する原因・理由を表す動詞です。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よっ"
}
```

#### Pack B
### Level 3 (sense 35111, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "天然染料に___染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "original_sentence": "天然染料による染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "correct_answer": "よっ",
  "options": [
    "笑っ",
    "行っ",
    "走っ",
    "よっ"
  ],
  "explanation": "「によって」は原因・手段を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よる"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "結果として、建築は静的な物体ではなく、見る者に___て絶えず意味が更新される開かれた場として再定義されるのです。",
  "original_sentence": "結果として、建築は静的な物体ではなく、見る者によって絶えず意味が更新される開かれた場として再定義されるのです。",
  "correct_answer": "よっ",
  "options": [
    "笑っ",
    "行っ",
    "限っ",
    "よっ"
  ],
  "explanation": "「によって」は原因・手段を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よっ"
}
```

---
