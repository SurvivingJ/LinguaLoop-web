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


## sense 35341, level 1

#### Pack A
### Level 1 (sense 35341, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "不可欠",
  "prompt": "不可欠",
  "options": [
    "ふかげつ",
    "ふがけつ",
    "ふかけづ",
    "ふかけつ"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "ふかけつ",
  "schema_version": 2
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "不可欠",
  "prompt": "ふかけつ",
  "options": [
    "社内外",
    "大丈夫",
    "不可欠",
    "不可避"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "不可欠",
  "schema_version": 2,
  "distractor_sources": {
    "不可避": "component",
    "大丈夫": "component",
    "社内外": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35341, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "不可欠",
  "options": [
    "ふかげつ",
    "ふがけつ",
    "ふかけづ",
    "ふかけつ"
  ],
  "correct_answer": "ふかけつ",
  "word": "不可欠",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "ipa": "/fukaketsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "風穴",
    "負荷率",
    "不可欠",
    "付加刑"
  ],
  "correct_answer": "不可欠",
  "explanation": "正解です。「不可欠」は「ある物事をするために、どうしても必要であること。」という意味です。",
  "distractor_explanations": {
    "付加刑": "「付加刑」は「不可欠」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "負荷率": "「負荷率」は「不可欠」と一モーラだけ異なる実在語です（3モーラ目: 「け」→「り」、一部の音の違い）。",
    "風穴": "「風穴」は「不可欠」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「う」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "ふかけつ",
  "options": [
    "社内外",
    "大丈夫",
    "不可欠",
    "不可避"
  ],
  "correct_answer": "不可欠",
  "word": "不可欠",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "社内外": "component",
    "大丈夫": "component",
    "不可避": "component"
  }
}
```

---

## sense 35341, level 2

#### Pack A
### Level 2 (sense 35341, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "correct_definition": "ある物事をするために、どうしても必要であること。",
  "options": [
    "「ある」は存在を表す動詞で、物や事柄が存在することを示します。「ます」は丁寧な表現を作る助動詞です。",
    "ある物事をするために、どうしても必要であること。",
    "意見や利害の対立から起こる、言い合いやけんか。",
    "飛行機などの翼に働く、上向きの力。空気の流れの差によって生じ、機体を支える。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある物事が持つ、良い結果や役に立つ性質。",
        "「カーボン」は、石炭や木炭のもとになる、黒い色の物質のことです。",
        "ある物事をするために、どうしても必要であること。",
        "trust"
      ],
      "correct_answer": "ある物事をするために、どうしても必要であること。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35341, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "不可欠",
  "options": [
    "眠っている状態から目が覚めて、体を起こす。また、何かが新しく始まったり、発生したりする。",
    "地中や地表から採れる、無機質で天然の固体。多くの場合、結晶構造を持つ。",
    "右とは、方向の一つで、東を向いた時に南にあたる側、または体の中心から見て、心臓がある側と反対の側を指します。",
    "ある物事をするために、どうしても必要であること。"
  ],
  "pronunciation": "ふかけつ",
  "correct_definition": "ある物事をするために、どうしても必要であること。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "物の高さや順番を数えるときの言葉。例えば、棚の一つ一つの平らな場所を「だん」と言います。",
        "ある物事をするために、どうしても必要であること。",
        "to peck (at food)",
        "「裏腹」は、表面に現れている様子や期待とは反対の結果や状態を表す言葉です。例えば、美しい景色に反して大変な仕事をすることなどを指します。"
      ],
      "correct_answer": "ある物事をするために、どうしても必要であること。"
    }
  },
  "tier": "T6",
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "schema_version": 2
}
```

---

## sense 35341, level 4

#### Pack A
### Level 4 (sense 35341, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "target_word": "不可欠",
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠に",
      "不可欠な",
      "不可欠だ"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠に",
      "不可欠な",
      "不可欠だ"
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
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "correct_answer": "不可欠な",
  "base_form": "不可欠",
  "form_label": "連体形",
  "options": [
    "不可欠な",
    "不可欠に",
    "不可欠で",
    "不可欠だ"
  ],
  "explanation": "名詞「工程」を修飾するためには形状詞の連体形「な」が必要である。",
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "勉強には、集中力が___だと思う。",
  "original_sentence": "勉強には、集中力が不可欠だと思う。",
  "target_word": "不可欠",
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠に",
      "不可欠な",
      "不可欠だ"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠に",
      "不可欠な",
      "不可欠だ"
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
  "sentence_with_blank": "勉強には、集中力が___だと思う。",
  "original_sentence": "勉強には、集中力が不可欠だと思う。",
  "correct_answer": "不可欠",
  "base_form": "不可欠",
  "form_label": "語幹（だ／です に接続する形）",
  "options": [
    "重要",
    "必要",
    "不可欠",
    "十分"
  ],
  "explanation": "「だ」に接続する終止形の語幹。",
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```

#### Pack B
### Level 4 (sense 35341, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠な",
      "不可欠に"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠な",
      "不可欠に"
    ]
  },
  "input_mode": "ime",
  "target_word": "不可欠",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "重要",
    "不可欠",
    "十分",
    "必要"
  ],
  "base_form": "不可欠",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "target_word": "不可欠",
  "correct_answer": "不可欠",
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠な",
      "不可欠に"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠な",
      "不可欠に"
    ]
  },
  "input_mode": "ime",
  "target_word": "不可欠",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "睡眠は健康に不可欠だ。",
  "sentence_with_blank": "睡眠は健康に___だ。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "必要",
    "重要",
    "不可欠",
    "十分"
  ],
  "base_form": "不可欠",
  "form_label": "語幹（だ／です に接続する形）",
  "explanation": "「だ」に接続する終止形の語幹。",
  "target_word": "不可欠",
  "correct_answer": "不可欠",
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "original_sentence": "睡眠は健康に不可欠だ。",
  "sentence_with_blank": "睡眠は健康に___だ。"
}
```

---

## sense 35341, level 6

#### Pack A
### Level 6 (sense 35341, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "成功には、協力が不可欠にだ。",
      "is_correct": false
    },
    {
      "text": "成功には、協力が不可欠だと感じる。",
      "is_correct": true
    },
    {
      "text": "成功には、協力が不可欠なだ。",
      "is_correct": false
    },
    {
      "text": "成功には、協力が不可欠でだ。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：形状詞「不可欠」の連体形・終止形は「不可欠な」または「不可欠だ」ですが、「不可欠なだ」という活用は存在しません。 活用・アスペクトの誤り：形状詞「不可欠」に助動詞「だ」を接続する場合は「不可欠だ」となり、「不可欠にだ」とはなりません。 活用・アスペクトの誤り：形状詞「不可欠」の連用形「不可欠で」に「だ」を直接接続することはできません。「不可欠である」や「不可欠だ」とする必要があります。",
  "target_word": "不可欠"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "不可欠",
  "relation": "antonym",
  "options": [
    "有用",
    "不要",
    "重要",
    "必須"
  ],
  "correct_answer": "不要",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事をするために、どうしても必要であること。",
      "explanation": "「どうしても必要である」の対義語であり「必要ない」ことを表す"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35341, difficulty 8)
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "不可欠だ練習は上達に。",
      "is_correct": false
    },
    {
      "text": "練習は上達に不可欠だ。",
      "is_correct": true
    },
    {
      "text": "練習は上達を不可欠だ。",
      "is_correct": false
    },
    {
      "text": "練習は上達に不可欠にだ。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：形容動詞「不可欠」の対象は「に」で示す。「を」は誤り。 活用：終止形は「不可欠だ」であり、「不可欠にだ」は「に」を余計に挟んだ誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "不可欠"
}
```

---

## sense 35341, level 7

#### Pack A
### Level 7 (sense 35341, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠工程です。",
      "is_correct": false,
      "error_description": "形状詞「不可欠」が名詞を修飾する際は、連体形「不可欠な」を用いる必要があります。「不可欠工程」と助動詞「な」を省略することはできません。"
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
      "is_correct": true
    },
    {
      "text": "そこに、発酵の不可欠な役割が凝縮されているのです。",
      "is_correct": true
    },
    {
      "text": "特に多色印刷の場合、色ごとに異なる版木を使い分ける必要があり、職人たちの高度な技術と協力が不可欠です。",
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
      "text": "信頼は、友人との関係に不可欠な要素です。",
      "is_correct": true
    },
    {
      "text": "勉強には、集中力が不可欠だと思う。",
      "is_correct": true
    },
    {
      "text": "成功には、協力が不可欠だと感じる。",
      "is_correct": true
    },
    {
      "text": "これは計画に不可欠な要素が。",
      "is_correct": false,
      "error_description": "コピュラ「だ」を欠くと文が終止せず不完全になる。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35341, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理を不可欠な工程です。",
      "is_correct": false,
      "error_description": "助詞：形容動詞「不可欠」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "そこに、発酵の不可欠な役割が凝縮されているのである。",
      "is_correct": true
    },
    {
      "text": "特に多色印刷の場合、色ごとに異なる版木を使い分ける必要があり、職人たちの高度な技術と協力が不可欠です。",
      "is_correct": true
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
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
      "text": "これは計画に不可欠な要素が。",
      "is_correct": false,
      "error_description": "コピュラ「だ」を欠くと文が終止せず不完全になる。"
    },
    {
      "text": "練習は上達に不可欠だ。",
      "is_correct": true
    },
    {
      "text": "睡眠は健康に不可欠だ。",
      "is_correct": true
    },
    {
      "text": "彼の助けは不可欠だった。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35341, level 9

#### Pack A
### Level 9 (sense 35341, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "この道具は作業に不可欠だ。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "この道具は",
    "作業に",
    "不可欠だ"
  ],
  "chunk_count": 3,
  "target_word": "不可欠",
  "schema_version": 2,
  "shuffled_chunks": [
    "この道具は",
    "不可欠だ",
    "作業に"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "この道具は作業に不可欠だ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "テクノロジー産業の",
    "持続的発展に",
    "おいて",
    "ベンチャーキャピタルの",
    "存在は",
    "極めて不可欠である"
  ],
  "chunk_count": 6,
  "target_word": "不可欠",
  "schema_version": 2,
  "shuffled_chunks": [
    "テクノロジー産業の",
    "持続的発展に",
    "おいて",
    "極めて不可欠である",
    "存在は",
    "ベンチャーキャピタルの"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。"
}
```

#### Pack B
### Level 9 (sense 35341, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "水は、生きるために不可欠な条件です。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "水は、生きるために不可欠な条件です。",
  "chunks": [
    "水は",
    "生きるため",
    "に",
    "不可欠な条件です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "不可欠な条件です",
    "水は",
    "生きるため",
    "に"
  ],
  "target_word": "不可欠",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠です。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠です。",
  "chunks": [
    "テクノロジー産業の",
    "持続的発展に",
    "おいて",
    "ベンチャーキャピタルの",
    "存在は",
    "極めて不可欠です"
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
    "テクノロジー産業の",
    "持続的発展に",
    "おいて",
    "極めて不可欠です",
    "存在は",
    "ベンチャーキャピタルの"
  ],
  "target_word": "不可欠",
  "chunk_count": 6
}
```

---

## sense 35419, level 1

#### Pack A
### Level 1 (sense 35419, difficulty 8)
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "jagate",
  "word": "やがて",
  "options": [
    "苦手",
    "やり手",
    "矢盾",
    "やがて"
  ],
  "audio_url": null,
  "explanation": "正解です。「やがて」は「時間が経過した後に何かが起こることを表す。「やがて」の意味。」という意味です。",
  "pronunciation": "やがて",
  "correct_answer": "やがて",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "矢盾": "「矢盾」は「やがて」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「た」、一部の音の違い）。",
    "苦手": "「苦手」は「やがて」と一モーラだけ異なる実在語です（1モーラ目: 「や」→「に」、一部の音の違い）。",
    "やり手": "「やり手」は「やがて」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。"
  }
}
```

#### Pack B
### Level 1 (sense 35419, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "軈て",
  "options": [
    "やがて",
    "やがで",
    "やかて",
    "やあがて"
  ],
  "correct_answer": "やがて",
  "word": "軈て",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "ipa": "/jaɡate/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "山手",
    "苦手",
    "矢盾",
    "軈て"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。」という意味です。",
  "distractor_explanations": {
    "山手": "「山手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「ま」、一部の音の違い）。",
    "苦手": "「苦手」は「軈て」と一モーラだけ異なる実在語です（1モーラ目: 「や」→「に」、一部の音の違い）。",
    "矢盾": "「矢盾」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "やがて",
  "options": [
    "意思",
    "思想",
    "軈て",
    "意志"
  ],
  "correct_answer": "軈て",
  "word": "軈て",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "思想": "component",
    "意思": "component",
    "意志": "component"
  }
}
```

---

## sense 35419, level 2

#### Pack A
### Level 2 (sense 35419, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "correct_definition": "時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。",
  "options": [
    "時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。",
    "二つのものが激しくぶつかること。また、意見や利害が対立すること。",
    "特定の任務や責任を負い、それを取り扱うこと。また、その役割を果たす人。",
    "一度起こった変化が、再び元の状態に戻ることが可能な性質"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "本を読むこと。読書という行為。",
        "時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。",
        "物が動く速さのことです。",
        "物事の端の方、または場所の隅の部分。"
      ],
      "correct_answer": "時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35419, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "やがて",
  "options": [
    "人や動物などを殺すこと。また、何かを終わらせること。",
    "上下の方向。垂直。",
    "時間が経過した後に何かが起こることを表す。「やがて」の意味。",
    "手や道具などを使って、物体をおしやるのではなく手前へ動かすこと。"
  ],
  "pronunciation": "やがて",
  "correct_definition": "時間が経過した後に何かが起こることを表す。「やがて」の意味。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "時間が経過した後に何かが起こることを表す。「やがて」の意味。",
        "ことがらの、あるときのようすのこと。",
        "周",
        "amicably (on good terms)"
      ],
      "correct_answer": "時間が経過した後に何かが起こることを表す。「やがて」の意味。"
    }
  },
  "tier": "T6",
  "word": "やがて",
  "pronunciation": "やがて",
  "schema_version": 2
}
```

---

## sense 35419, level 6

#### Pack A
### Level 6 (sense 35419, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈て準備が整いて、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    },
    {
      "text": "軈て準備に整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "彼は勢いよく扉を押し開ける、軈て準備が整い。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「準備」の格助詞は主格を表す「が」が適切であり、「に」は不自然です。 活用・アスペクトの誤り：「整う」の連用形は「整い」または「整って」であり、「整いて」は誤った活用です。 語順・係り受けの誤り：副詞「軈て」は修飾する節「準備が整い」の直前に置くべきであり、文末に置くと係り受けが破綻します。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 6 (sense 35419, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "やがて準備を整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "扉を押し開ける勢いよく彼は、やがて準備が整い。",
      "is_correct": false
    },
    {
      "text": "やがて準備が整いる、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "やがて準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：自動詞「整う」の主体は「が」で示す。「を」は誤り。 活用：連用形「整い」に「る」を続けるのは存在しない形。「整って」が正しい。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "やがて"
}
```

---

## sense 35419, level 7

#### Pack A
### Level 7 (sense 35419, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈てに真実が明らかになる。",
      "is_correct": false,
      "error_description": "助詞の混同。副詞である「軈て」に助詞「に」を過剰に付加しています。正しくは助詞なしで「軈て真実が」とします。"
    },
    {
      "text": "厳しい気候に晒されながらも力強く茎を伸ばしてきた植物は、軈て暖かな春の陽射しを浴びて花を咲かせるだろう。",
      "is_correct": true
    },
    {
      "text": "この憧れの感情は、軈てグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
      "is_correct": true
    },
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
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
      "text": "軈てにこの町も発展していく。",
      "is_correct": false,
      "error_description": "「軈て」は副詞であるため、格助詞「に」を付けて「軈てに」とすることはできません。「すぐ」のように名詞的に扱って「に」を付けてしまう助詞の過剰付加の誤りです。正しい形は「軈て」として直接用言を修飾します。"
    },
    {
      "text": "軈てこの町も発展していく。",
      "is_correct": true
    },
    {
      "text": "軈て真実が明らかになる。",
      "is_correct": true
    },
    {
      "text": "練習して、軈て試合に勝つ。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35419, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "この憧れの感情は、やがてグローバルな大衆向けブランドが巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
      "is_correct": false,
      "error_description": "助詞：動作主を示す「によって」を「が」に置き換えるのは誤り。"
    },
    {
      "text": "やがて成長の過程において、植物は時折厳しい気候に晒されながらも、力強く茎を伸ばしていく。",
      "is_correct": true
    },
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、やがて目に見えぬ根の網目へと伝わっていくだろう。",
      "is_correct": true
    },
    {
      "text": "この憧れの感情は、やがてグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
      "is_correct": true
    }
  ]
}
```

---
