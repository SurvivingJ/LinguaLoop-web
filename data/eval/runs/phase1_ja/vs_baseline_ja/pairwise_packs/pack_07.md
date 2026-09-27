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
### Level 4 (sense 35341, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "そこに、発酵の___な役割が凝縮されているのである。",
  "original_sentence": "そこに、発酵の不可欠な役割が凝縮されているのである。",
  "target_word": "不可欠",
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠な",
      "不可欠に",
      "不可欠さ"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠な",
      "不可欠に",
      "不可欠さ"
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
  "sentence_with_blank": "そこに、発酵の___な役割が凝縮されているのである。",
  "original_sentence": "そこに、発酵の不可欠な役割が凝縮されているのである。",
  "correct_answer": "不可欠な",
  "base_form": "不可欠",
  "form_label": "連体形",
  "options": [
    "不可欠に",
    "不可欠だ",
    "不可欠な",
    "不可欠で"
  ],
  "explanation": "名詞「役割」を修飾するには形状詞の連体形「な」が必要である。",
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "睡眠は___な要素です。",
  "original_sentence": "睡眠は不可欠な要素です。",
  "target_word": "不可欠",
  "word": "不可欠",
  "answer": {
    "accepted": [
      "不可欠",
      "不可欠な",
      "不可欠に",
      "不可欠さ"
    ],
    "accepted_normalized": [
      "不可欠",
      "不可欠な",
      "不可欠に",
      "不可欠さ"
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
  "sentence_with_blank": "睡眠は___な要素です。",
  "original_sentence": "睡眠は不可欠な要素です。",
  "correct_answer": "不可欠な",
  "base_form": "不可欠",
  "form_label": "連体形",
  "options": [
    "不可欠だ",
    "不可欠さ",
    "不可欠な",
    "不可欠に"
  ],
  "explanation": "名詞「要素」を修飾するため、形状詞の連体形「な」が必要である。",
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

---

## sense 35341, level 6

#### Pack A
### Level 6 (sense 35341, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "協力も不可欠なものです。",
      "is_correct": true
    },
    {
      "text": "練習は上達に不可欠にだ。",
      "is_correct": false
    },
    {
      "text": "練習は上達を不可欠だ。",
      "is_correct": false
    },
    {
      "text": "不可欠だ練習は上達に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：形容動詞「不可欠」の対象は「に」で示す。「を」は誤り。 活用：終止形は「不可欠だ」であり、「不可欠にだ」は「に」を余計に挟んだ誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "不可欠"
}
```

#### Pack B
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

---

## sense 35341, level 7

#### Pack A
### Level 7 (sense 35341, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "そこに、発酵の不可欠な役割が凝縮されているのである。",
      "is_correct": true
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠の工程です。",
      "is_correct": false,
      "error_description": "形状詞「不可欠」が名詞を修飾する際は「不可欠な」の形を使います。「不可欠の」は誤りです。"
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "信頼は友達で不可欠なものです。",
      "is_correct": false,
      "error_description": "「不可欠」の対象（誰にとって不可欠か）を示す場合は、助詞「に」または「にとって」を用います。場所や手段を表す「で」を用いるのは誤りです。"
    },
    {
      "text": "睡眠は不可欠な要素です。",
      "is_correct": true
    },
    {
      "text": "信頼は友達に不可欠なものです。",
      "is_correct": true
    },
    {
      "text": "協力も不可欠なものです。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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

---

## sense 35341, level 9

#### Pack A
### Level 9 (sense 35341, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "水は生き物に不可欠です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "水は生き物に不可欠です。",
  "chunks": [
    "水は",
    "生き物に",
    "不可欠です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "水は",
    "不可欠です",
    "生き物に"
  ],
  "target_word": "不可欠",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。",
  "chunks": [
    "テクノロジー産業の",
    "持続的発展に",
    "おいて",
    "ベンチャーキャピタルの",
    "存在は",
    "極めて不可欠である"
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
    "極めて不可欠である",
    "存在は",
    "ベンチャーキャピタルの"
  ],
  "target_word": "不可欠",
  "chunk_count": 6
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
    "遣り手",
    "軈て",
    "苦手",
    "野外"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "苦手": "「苦手」は「軈て」と一モーラだけ異なる実在語です（1モーラ目: 「や」→「に」、一部の音の違い）。",
    "野外": "「野外」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「い」、一部の音の違い）。",
    "遣り手": "「遣り手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。"
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
### Level 2 (sense 35419, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "correct_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "options": [
    "二つの方向のうち、右と左。また、物事の二つの側面や立場。",
    "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
    "線や糸などが横と縦に交わり、格子状になった構造。また、その模様。",
    "ある土地の、自然や人工物を含めた全体的な見え方や眺め。"
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
        "增加",
        "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
        "迈步",
        "弯曲 —— 不是笔直的，而是呈缓和的曲线状"
      ],
      "correct_answer": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。"
    }
  }
}
```

---

## sense 35419, level 3

#### Pack A
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この憧れの感情は、___グローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
  "original_sentence": "この憧れの感情は、軈てグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
  "correct_answer": "軈て",
  "options": [
    "決して",
    "いきなり",
    "軈て",
    "すでに"
  ],
  "explanation": "正解です。時間の経過を経て何かが起こることを表し、文脈に適合します。",
  "distractor_tags": {},
  "word_definition": "時間がたった後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、少し古い言い方です。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "水は瞬く間に闇色の大地へと吸い込まれ、___目に見えぬ根の網目へと伝わっていくだろう。",
  "original_sentence": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
  "correct_answer": "軈て",
  "options": [
    "突如",
    "決して",
    "軈て",
    "実に"
  ],
  "explanation": "正解です。水が大地に吸い込まれ、時間の経過を経て根の網目に広がるという自然なプロセスを表す「軈て」が適切です。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___彼らは故郷へ帰るだろう。",
  "original_sentence": "軈て彼らは故郷へ帰るだろう。",
  "correct_answer": "軈て",
  "options": [
    "すでに",
    "けっして",
    "軈て",
    "とくに"
  ],
  "explanation": "正解です。文脈に合う副詞「軈て」が入ります。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
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
      "text": "軈て準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    },
    {
      "text": "準備が軈て整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備に整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備が整く、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「整う」は自動詞であり、主語を示す助詞は「が」が適切です。「準備に」という表現は、格助詞の取り違えです。 活用・アスペクトの誤り：自動詞「整う」の連用形は「整い」ですが、誤って「整く」と活用させています。 語順・係り受けの誤り：副詞「軈て」は通常、文頭や時間の経過を示す句の後に置かれます。「準備が」と「整い」の間に挿入されるのは不自然です。",
  "target_word": "軈て"
}
```

#### Pack B
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

---

## sense 35419, level 7

#### Pack A
### Level 7 (sense 35419, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈て成長の過程において、植物は時折厳しい気候に晒されながらも、力強く茎を伸ばしていく。",
      "is_correct": true
    },
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
      "is_correct": true
    },
    {
      "text": "悲しみは軈てに喜びに変わる。",
      "is_correct": false,
      "error_description": "副詞「軈て」の後に不要な助詞「に」が付いています。「軈て」はそれ単独で副詞として機能するため、助詞は必要ありません。"
    },
    {
      "text": "この憧れの感情は、軈てグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
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
      "text": "悲しみは軈て喜びに変わる。",
      "is_correct": true
    },
    {
      "text": "軈ての悲しみは喜びに変わる。",
      "is_correct": false,
      "error_description": "副詞の誤用。「軈て」は副詞なので「の」を付けて名詞を直接修飾することはできません。"
    },
    {
      "text": "軈て彼らは故郷へ帰るだろう。",
      "is_correct": true
    },
    {
      "text": "努力は軈て大きな力となる。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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

---

## sense 35615, level 1

#### Pack A
### Level 1 (sense 35615, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "複雑",
  "options": [
    "ふくさつ",
    "ふくざづ",
    "ふぐざつ",
    "ふくざつ"
  ],
  "correct_answer": "ふくざつ",
  "word": "複雑",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふくざつ",
  "options": [
    "複雑",
    "複合",
    "雑誌",
    "複数"
  ],
  "correct_answer": "複雑",
  "word": "複雑",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "複数": "component",
    "雑誌": "component",
    "複合": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/ɸɯkɯzatsɯ/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複雑",
    "錯雑",
    "福笹",
    "覆没"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "錯雑": "「錯雑」は「複雑」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「さ」、一部の音の違い）。",
    "覆没": "「覆没」は「複雑」と一モーラだけ異なる実在語です（3モーラ目: 「ざ」→「ぼ」、一部の音の違い）。",
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35615, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "複雑",
  "options": [
    "ふくさつ",
    "ふくざづ",
    "ふぐざつ",
    "ふくざつ"
  ],
  "correct_answer": "ふくざつ",
  "word": "複雑",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/fukuzatsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複舌",
    "錯雑",
    "複雑",
    "複座機"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "錯雑": "「錯雑」は「複雑」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「さ」、一部の音の違い）。",
    "複座機": "「複座機」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「き」、一部の音の違い）。",
    "複舌": "「複舌」は「複雑」と一モーラだけ異なる実在語です（3モーラ目: 「ざ」→「ぜ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふくざつ",
  "options": [
    "複雑",
    "混雑",
    "複合",
    "雑誌"
  ],
  "correct_answer": "複雑",
  "word": "複雑",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "雑誌": "component",
    "複合": "component",
    "混雑": "component"
  }
}
```

---
