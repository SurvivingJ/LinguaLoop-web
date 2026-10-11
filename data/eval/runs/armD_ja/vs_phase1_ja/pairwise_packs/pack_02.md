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


## sense 35017, level 3

#### Pack A
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___ていくゴミをどうすればよいのでしょうか。",
  "original_sentence": "増えていくゴミをどうすればよいのでしょうか。",
  "correct_answer": "増え",
  "options": [
    "増え",
    "増やし",
    "増えて",
    "増える"
  ],
  "explanation": "正解です。補助動詞「いる」の連用形「います」に接続するため、動詞「増える」の連用形である「増え」が適切です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
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

---

## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty None)
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

#### Pack B
### Level 4 (sense 35017, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "最近、この町に外国人が___ています。",
  "original_sentence": "最近、この町に外国人が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形",
  "options": [
    "増えない",
    "増え",
    "増える",
    "増えた"
  ],
  "explanation": "「います」に接続するため、連用形の「増え」が正しい。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "最近、この町に外国人___増えています。",
  "original_sentence": "最近、この町に外国人が増えています。",
  "options": [
    "に",
    "を",
    "で",
    "が"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語（現象の主体）を標示する格助詞"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "最近、私の友達が___たと思います。",
  "original_sentence": "最近、私の友達が増えたと思います。",
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

---

## sense 35017, level 7

#### Pack A
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "しかし、見た目の古さや手入れの難しさから、今はその良さが認められていても、壊される家も増えています。",
      "is_correct": true
    },
    {
      "text": "最近、この町に外国人が増えています。",
      "is_correct": true
    },
    {
      "text": "テストの点数が前回より増えました。",
      "is_correct": true
    },
    {
      "text": "テストの点数が前回より増えりました。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り。「増える」は一段動詞なので、過去形は「増えりました」ではなく「増えました」が正しいです。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この頃、コンビニの数がどんどん増えています。",
      "is_correct": true
    },
    {
      "text": "しかし、その無骨な外観や維持管理の難しさから、現在ではその価値が再評価される一方で、取り壊されるケースも増えいます。",
      "is_correct": false,
      "error_description": "「～ています」の「て」が抜けている誤り。"
    },
    {
      "text": "増えていくゴミをどうすればよいのでしょうか。",
      "is_correct": true
    },
    {
      "text": "最近、私の友達が増えたと思います。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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

---

## sense 35055, level 1

#### Pack A
### Level 1 (sense 35055, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "ipa": "[se̞ka̠i]",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "附会",
    "世界",
    "打開",
    "器械"
  ],
  "correct_answer": "世界",
  "explanation": "正解です。「世界」は「地球全体。また、人間の活動の及ぶすべての範囲。社会全体。」という意味です。",
  "distractor_explanations": {
    "器械": "「器械」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「き」、一部の音の違い）。",
    "附会": "「附会」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「ふ」、一部の音の違い）。",
    "打開": "「打開」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「だ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35055, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "ipa": "/sekai/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "デカイ",
    "世界",
    "戦意",
    "市会"
  ],
  "correct_answer": "世界",
  "explanation": "正解です。「世界」は「地球全体や、社会全体のこと。」という意味です。",
  "distractor_explanations": {
    "市会": "「市会」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「し」、一部の音の違い）。",
    "戦意": "「戦意」は「世界」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「ん」、撥音「ん」の有無）。",
    "デカイ": "「デカイ」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「で」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35055, level 3

#### Pack A
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "私はいつか___一周の旅に出かけたいです。",
  "original_sentence": "私はいつか世界一周の旅に出かけたいです。",
  "correct_answer": "世界",
  "options": [
    "世間",
    "世界",
    "グローブ",
    "机"
  ],
  "explanation": "正解です。「世界一周」は決まった表現として自然です。",
  "distractor_tags": {},
  "word_definition": "地球全体や、社会全体のこと。",
  "target_word": "世界"
}
```

#### Pack B
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "私は___の国々を旅してみたいと思います。",
  "original_sentence": "私は世界の国々を旅してみたいと思います。",
  "correct_answer": "世界",
  "options": [
    "部屋",
    "世界",
    "地域",
    "家庭"
  ],
  "explanation": "正解です。「世界の国々」は、地球上に存在するすべての国々を指す自然な表現です。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___には、まだ解決されていない多くの問題があります。",
  "original_sentence": "世界には、まだ解決されていない多くの問題があります。",
  "correct_answer": "世界",
  "options": [
    "家庭",
    "部屋",
    "世界",
    "個人"
  ],
  "explanation": "正解です。文脈に合致する適切な名詞です。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
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
      "text": "世界は一つ冊です。",
      "is_correct": false
    },
    {
      "text": "世界で平和が守る。",
      "is_correct": false
    },
    {
      "text": "世界は明日回った。",
      "is_correct": false
    },
    {
      "text": "私は世界の国々を旅してみたいと思います。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「世界」のような抽象的・広域的な概念には「冊」は使えず、通常は数えません。 項構造の誤り：「平和」は守られる対象であるため、自動詞の「守る」ではなく他動詞の受身形「守られる」を使う必要があります。 活用・アスペクトの誤り：地球が回転することは継続的な事実・習慣であるため、完了・過去の「回った」ではなく「回っている」が適切です。",
  "target_word": "世界"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "世界",
  "relation": "antonym",
  "options": [
    "地球",
    "国内",
    "宇宙",
    "社会"
  ],
  "correct_answer": "国内",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
      "explanation": "地球全体や社会全体を指す「世界」に対し、特定の国家の内部を指す「国内」は範囲の対義関係にある。"
    }
  }
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

## sense 35055, level 7

#### Pack A
### Level 7 (sense 35055, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "日本の伝統的な工芸品は、現在では世界から高い評価を受けています。",
      "is_correct": true
    },
    {
      "text": "私はいつか世界一周の旅に出かけたいです。",
      "is_correct": true
    },
    {
      "text": "私たちの会社は、世界の人々が喜んでもらえるような商品を開発しています。",
      "is_correct": false,
      "error_description": "助詞の混同。「喜んでもらう」の動作の受け手を示す助詞は「に」であり、「が」は誤りです。"
    },
    {
      "text": "私たちの会社は、世界の人々に喜んでもらえるような商品を開発しています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35055, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は世界の国々を旅してみたいと思います。",
      "is_correct": true
    },
    {
      "text": "この伝統的な工芸品は、世界中の多くの人々を愛されています。",
      "is_correct": false,
      "error_description": "受身形の動作主（〜される）を示す助詞には「に」や「から」を使います。「を」は目的語を示す助詞であるため、ここでは誤りです。"
    },
    {
      "text": "この美しい自然は、世界の人々によって守られるべきものです。",
      "is_correct": true
    },
    {
      "text": "この伝統的な工芸品は、世界中の多くの人々から愛されています。",
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
      "text": "世界がもっと良くなってほしい。",
      "is_correct": true
    },
    {
      "text": "世界をもっと良くなってほしい。",
      "is_correct": false,
      "error_description": "「良くなる」は自動詞なので、その主体を表す助詞は「が」を使います。「を」は他動詞の目的語に使う助詞です。"
    },
    {
      "text": "世界は広い。",
      "is_correct": true
    },
    {
      "text": "世界には、まだ解決されていない多くの問題があります。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35093, level 1

#### Pack A
### Level 1 (sense 35093, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "ipa": "[ɡʲidʑɯtɕɯ]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "武術",
    "奇術",
    "技術",
    "話術"
  ],
  "correct_answer": "技術",
  "explanation": "正解です。「技術」は「ある分野で使われる、専門的な方法や手順。また、それを応用して物を作ったり、処理したりする能力や体系。」という意味です。",
  "distractor_explanations": {
    "話術": "「話術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「わ」、一部の音の違い）。",
    "奇術": "「奇術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「き」、清濁・半濁音の対立）。",
    "武術": "「武術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ぶ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35093, difficulty None)
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

---

## sense 35093, level 3

#### Pack A
### Level 3 (sense 35093, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "センサー等を用いた___は、収量の安定化により収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術は、収量の安定化により収益性を向上させます。",
  "correct_answer": "技術",
  "options": [
    "知識",
    "芸術",
    "意識",
    "技術"
  ],
  "explanation": "正解です。文脈に最も適切に当てはまります。",
  "distractor_tags": {},
  "word_definition": "ある分野で使われる、専門的な方法や手順。また、それを応用して物を作ったり、処理したりする能力や体系。",
  "target_word": "技術"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___が進歩して生活が楽になる。",
  "original_sentence": "技術が進歩して生活が楽になる。",
  "correct_answer": "技術",
  "options": [
    "趣味",
    "芸術",
    "思想",
    "技術"
  ],
  "explanation": "正解です。文脈は技術の進歩による生活の向上を表しており、「技術」が最も適切です。",
  "distractor_tags": {},
  "word_definition": "ある分野で使われる、専門的な方法や手順。また、それを応用して物を作ったり、処理したりする能力や体系。",
  "target_word": "技術"
}
```

#### Pack B
### Level 3 (sense 35093, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "センサー等を用いた___は、収量の安定化により収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術は、収量の安定化により収益性を向上させます。",
  "correct_answer": "技術",
  "options": [
    "資格",
    "技術",
    "知識",
    "経験"
  ],
  "explanation": "「解析技術」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりする、専門的な方法や能力。",
  "target_word": "技術"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "料理の___を磨くことは楽しいです。",
  "original_sentence": "料理の技術を磨くことは楽しいです。",
  "correct_answer": "技術",
  "options": [
    "経験",
    "技術",
    "知識",
    "資格"
  ],
  "explanation": "「技術を研究する」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりする、専門的な方法や能力。",
  "target_word": "技術"
}
```

---

## sense 35093, level 4

#### Pack A
### Level 4 (sense 35093, difficulty None)
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
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析などの技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析などの技術を活用した「精密農業」が注目されています。",
  "options": [
    "で",
    "に",
    "が",
    "を"
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
      "explanation": "他動詞「活用する」の直接目的語を標示する"
    }
  }
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "私たちは技術___大切にすべきだ。",
  "original_sentence": "私たちは技術を大切にすべきだ。",
  "options": [
    "が",
    "で",
    "に",
    "を"
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
      "explanation": "他動詞「する」の直接目的語を標示する"
    }
  }
}
```

---
