# Pairwise review pack 03

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


## sense 35111, level 6

#### Pack A
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "雨に因る中止は残念です。",
      "is_correct": true
    },
    {
      "text": "雨に因った中止は残念です。",
      "is_correct": false
    },
    {
      "text": "雨で因る中止は残念です。",
      "is_correct": false
    },
    {
      "text": "中止は雨に因る残念です。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同。「因る」は「～に因る」の形をとります。「で」ではなく「に」を使う必要があります。 活用・アスペクトの誤り。「因る」の連用形は「より」であり、「よっ」とはなりません。「雨に因って」が正しい形です。 語順・係り受けの誤り。「雨に因る」は名詞「中止」を修飾する必要があります。「残念」を修飾しては文の意味が成立しません。",
  "target_word": "因る"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "選挙に因る変化を待つ。",
      "is_correct": true
    },
    {
      "text": "変化を選挙に因る待つ。",
      "is_correct": false
    },
    {
      "text": "選挙で因る変化を待つ。",
      "is_correct": false
    },
    {
      "text": "選挙に因っている変化を待つ。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：原因・理由を表す「因る」は、原因を示す名詞に「に」を伴います。 活用・アスペクトの誤り：「因る」は原因・理由を説明する動詞であり、進行や継続を表す「ている」形は不自然です。 語順・係り受けの誤り：「選挙に因る」は名詞「変化」を修飾する連体修飾語であり、動詞「待つ」の前に置くのは誤りです。",
  "target_word": "因る"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "因る",
  "relation": "antonym",
  "options": [
    "帰結する",
    "起因する",
    "発する",
    "由来する"
  ],
  "correct_answer": "帰結する",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
      "explanation": "ある結果として生じる。目標語義（原因となる）の対義語である。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "間接照明に因れば陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "効果的です陰影の演出などが、間接照明による組み合わせと家具の白壁無垢材。",
      "is_correct": false
    },
    {
      "text": "間接照明が陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "やがて企業が成熟すると、創業者や投資家は投資した対価を得るために、他社による買収や株式上場といったエグジット、すなわち出口戦略を選択する。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：手段を表す「による」を省くと「が」が二重になり文が成立しない。 活用：仮定形「因れば」は条件の意味になり、手段を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
  "target_word": "よる"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "収益性を向上させます、センサー等を用いた技術導入は収量の安定化により。",
      "is_correct": false
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化がより収益性を向上させます。",
      "is_correct": false
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化に因ったら収益性を向上させます。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：「により」の前に「が」を重ねるのは誤り。 活用：た系条件形「因ったら」は仮定の意味になり、原因を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
  "target_word": "よる"
}
```

---

## sense 35111, level 7

#### Pack A
### Level 7 (sense 35111, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "計算された論理がよって、機能的な都市空間を創出することが目指されています。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "天然染料による染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
      "is_correct": true
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    },
    {
      "text": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
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
      "text": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
      "is_correct": true
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "高温のオーブンへ投入された瞬間、生地は熱エネルギーがよって急激に膨張します。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "結果として、建築は静的な物体ではなく、見る者によって絶えず意味が更新される開かれた場として再定義されるのです。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35111, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "事故で因る被害は大きい。",
      "is_correct": false,
      "error_description": "助詞の混同。「因る」は原因や理由を表す名詞に接続する際、助詞「に」をとります。「で」は手段や直接的な原因の結果を表す際に使われるため、ここでは不適切です。"
    },
    {
      "text": "この結果は努力に因る。",
      "is_correct": true
    },
    {
      "text": "地震に因って家が壊れた。",
      "is_correct": true
    },
    {
      "text": "事故に因る被害は大きい。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35111, level 9

#### Pack A
### Level 9 (sense 35111, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "災害に因る被害の状況を伝えるニュースを見た。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "災害に因る被害の状況を伝えるニュースを見た。",
  "chunks": [
    "災害に",
    "因る被害の",
    "状況を",
    "伝えるニュースを",
    "見た"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "伝えるニュースを",
    "状況を",
    "因る被害の",
    "災害に",
    "見た"
  ],
  "target_word": "因る",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "雨に因る中止は残念です。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "雨に因る中止は残念です。",
  "chunks": [
    "雨に",
    "因る中止は",
    "残念です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "残念です",
    "因る中止は",
    "雨に"
  ],
  "target_word": "因る",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 35111, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "具体的には、無垢材の家具と白壁の組み合わせ、あるいは間接照明による陰影の演出などが効果的です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "具体的には、無垢材の家具と白壁の組み合わせ、あるいは間接照明による陰影の演出などが効果的です。",
  "chunks": [
    "具体的には無垢材の",
    "家具と白壁の",
    "組み合わせ",
    "あるいは間接照明に",
    "よる陰影の演出など",
    "が効果的です"
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
    "あるいは間接照明に",
    "が効果的です",
    "家具と白壁の",
    "組み合わせ",
    "具体的には無垢材の",
    "よる陰影の演出など"
  ],
  "target_word": "よる",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "やがて企業が成熟すると、創業者や投資家は投資した対価を得るために、他社による買収や株式上場といったエグジット、すなわち出口戦略を選択する。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "やがて企業が成熟すると、創業者や投資家は投資した対価を得るために、他社による買収や株式上場といったエグジット、すなわち出口戦略を選択する。",
  "chunks": [
    "やがて企業が成熟すると",
    "創業者や投資家は投資した対価を",
    "得るために他社に",
    "よる買収や株式上場と",
    "いったエグジット",
    "すなわち出口戦略を選択する"
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
    "いったエグジット",
    "創業者や投資家は投資した対価を",
    "すなわち出口戦略を選択する",
    "よる買収や株式上場と",
    "得るために他社に",
    "やがて企業が成熟すると"
  ],
  "target_word": "よる",
  "chunk_count": 6
}
```

---

## sense 35127, level 1

#### Pack A
### Level 1 (sense 35127, difficulty None)
**phonetic_recognition** variant `B`, tier `T4`
```json
{
  "word": "無い",
  "pronunciation": "ない",
  "ipa": "/nai/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "無い",
    "礼",
    "女医",
    "薙ぐ"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "distractor_explanations": {
    "女医": "「女医」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「じょ」、一部の音の違い）。",
    "礼": "「礼」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「れ」、一部の音の違い）。",
    "薙ぐ": "「薙ぐ」は「無い」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「ぐ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35127, difficulty None)
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "無い",
  "pronunciation": "ない",
  "ipa": "/nai/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "泰",
    "会",
    "無い",
    "姓"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "distractor_explanations": {
    "会": "「会」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「か」、一部の音の違い）。",
    "姓": "「姓」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「せ」、一部の音の違い）。",
    "泰": "「泰」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35127, level 2

#### Pack A
### Level 2 (sense 35127, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "pronunciation": "ない",
  "correct_definition": "存在しないこと。何かがそこにないこと。",
  "options": [
    "物事が循環する仕組みや、繰り返される過程。特に、始まりと終わりがつながっている状態。",
    "一般の店で売られていること。また、その商品。",
    "太陽の光が直接当たって、温かく感じられる場所。",
    "存在しないこと。何かがそこにないこと。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "pronunciation": "ない",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to drag",
        "拉",
        "存在しないこと。何かがそこにないこと。",
        "家や部屋の入り口にある、開け閉めできるもの"
      ],
      "correct_answer": "存在しないこと。何かがそこにないこと。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35127, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "pronunciation": "ない",
  "correct_definition": "存在しないこと。何かがそこにないこと。",
  "options": [
    "存在しないこと。何かがそこにないこと。",
    "強調の副詞。述べた内容が疑いなく事実であることを示す。",
    "物事の大きさや量を測る基準となる、一定の大きさや量。また、その区切り。",
    "ある物が、折れ曲がること。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "pronunciation": "ない",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to make sound",
        "自分にとって不利な存在。戦いや競争の相手。",
        "存在しないこと。何かがそこにないこと。",
        "to receive — getting something, such as an object or information, from someone"
      ],
      "correct_answer": "存在しないこと。何かがそこにないこと。"
    }
  }
}
```

---

## sense 35127, level 3

#### Pack A
### Level 3 (sense 35127, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "この古い町には近代的なビルが___、昔ながらの静かな風景が残っています。",
  "original_sentence": "この古い町には近代的なビルがなく、昔ながらの静かな風景が残っています。",
  "correct_answer": "なく",
  "options": [
    "麗しく",
    "なく",
    "淡く",
    "古く"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この地域には大きなスーパーが___、日々の買い物をするのにとても不便です。",
  "original_sentence": "この地域には大きなスーパーがなく、日々の買い物をするのにとても不便です。",
  "correct_answer": "なく",
  "options": [
    "忙しく",
    "甘く",
    "なく",
    "多く"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```

#### Pack B
### Level 3 (sense 35127, difficulty None)
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "企業には単純な作業だけで済む余裕は___、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
  "original_sentence": "企業には単純な作業だけで済む余裕はなく、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
  "correct_answer": "なく",
  "options": [
    "悪く",
    "狭く",
    "なく",
    "大きく"
  ],
  "explanation": "正解です。文脈に適切です。",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```

---

## sense 35127, level 4

#### Pack A
### Level 4 (sense 35127, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "創造性を刺激する空間にしたいと考えたが、十分な予算が___、計画は頓挫してしまった。",
  "original_sentence": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
  "target_word": "なく",
  "word": "なく",
  "answer": {
    "accepted": [
      "なく",
      "なければ",
      "なかった",
      "無し"
    ],
    "accepted_normalized": [
      "なく",
      "なければ",
      "なかった",
      "無し"
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
  "sentence_with_blank": "創造性を刺激する空間にしたいと考えたが、十分な予算が___、計画は頓挫してしまった。",
  "original_sentence": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中頓）",
  "options": [
    "なく",
    "なければ",
    "ない",
    "なかった"
  ],
  "explanation": "中頓を表す連用形「なく」が後続の句に適切に接続する。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
  "original_sentence": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
  "correct_answer": "ない",
  "base_form": "無い",
  "form_label": "終止形（では〜の形）",
  "options": [
    "無ければ",
    "ない",
    "無かった",
    "無くて"
  ],
  "explanation": "「ではない」は存在の否定を表す終止形。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "ない"
}
```

#### Pack B
### Level 4 (sense 35127, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "このプロジェクトには十分な資金が___、計画通りに進めるのは難しい状況です。",
  "original_sentence": "このプロジェクトには十分な資金がなく、計画通りに進めるのは難しい状況です。",
  "target_word": "なく",
  "word": "なく",
  "answer": {
    "accepted": [
      "なく",
      "ない",
      "なければ",
      "なかった"
    ],
    "accepted_normalized": [
      "なく",
      "ない",
      "なければ",
      "なかった"
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
  "sentence_with_blank": "このプロジェクトには十分な資金が___、計画通りに進めるのは難しい状況です。",
  "original_sentence": "このプロジェクトには十分な資金がなく、計画通りに進めるのは難しい状況です。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中頓）",
  "options": [
    "なければ",
    "なく",
    "ない",
    "なかった"
  ],
  "explanation": "形容詞の連用形「なく」は、文を中頓して後ろの句に接続する際に用いられます。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
  "original_sentence": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
  "correct_answer": "ない",
  "base_form": "ない",
  "form_label": "辞書形",
  "options": [
    "なければ",
    "なかった",
    "なく",
    "ない"
  ],
  "explanation": "現在の状態を表す形容詞の辞書形が文脈に合致する",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "ない"
}
```

---

## sense 35127, level 6

#### Pack A
### Level 6 (sense 35127, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": true
    },
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択がなく、すべてが特定のメッセージを伝える記号として機能した。",
      "is_correct": false
    },
    {
      "text": "記号論の観点から色を分析すると、そこにはなく偶然の選択が、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": false
    },
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択をなく、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同。「偶然の選択」は存在しないものの主語であるため、「を」ではなく「が」を使う必要があります。 活用・アスペクトの誤り。「分析すると」という条件・発見の表現に対して、結果の「機能した」という過去形は不自然です。 語順・係り受けの誤り。「そこには」の直後に「なく」を置くことで、「偶然の選択が」との主語との係り受けが破壊され、文構造が破綻しています。",
  "target_word": "なく"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えてある。",
      "is_correct": false
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えている。",
      "is_correct": true
    },
    {
      "text": "手元にはなく、参考になる資料や答えをみんなで知恵を出し合って考えている。",
      "is_correct": false
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合ってに考えている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「出して」と「考えて」を繋ぐのに助詞「に」は不要であり、文法誤りです。 活用・アスペクトの誤り：「考える」は意志動詞であり、結果の状態を表す「てある」は不自然です。 語順・係り受けの誤り：「なく」は「資料や答え」にかかるべきですが、後続の節で「を」の目的語になっており係り受けが破綻しています。",
  "target_word": "ない"
}
```

#### Pack B
### Level 6 (sense 35127, difficulty None)
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "少ない",
    "ある",
    "空しい",
    "乏しい"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "「存在しない」の対義語であり、物やことがそこに存在することを表す"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "机の上に消しゴムが1冊なく、友達に借りなければなりません。",
      "is_correct": false
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りなければなりません。",
      "is_correct": true
    },
    {
      "text": "机の上に消しゴムがなく、友達で借りなければなりません。",
      "is_correct": false
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りてあるなければなりません。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「消しゴム」の助数詞は「個」や「つ」であり、「冊」は本などに使います。 助詞の混同：「友達に」が正しく、「友達で」は動作の相手ではなく手段や共同動作を表す助詞です。 活用・アスペクトの誤り：「借りてあるなければ」は文法的に誤りです。",
  "target_word": "ない"
}
```

---

## sense 35127, level 7

#### Pack A
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
      "is_correct": true
    },
    {
      "text": "幼い頃のようなお絵描きとは異なり、この作品には特定のモデルがなく、純粋な感情表現となっている。",
      "is_correct": true
    },
    {
      "text": "彼らのルーツへの敬意を形にしたTシャツは、現在どこにも在庫になく、入手が困難となっている。",
      "is_correct": false,
      "error_description": "助詞の混同。存在しないものの主語を示すには『に』ではなく『が』を使います。正しくは『在庫がなく』です。"
    },
    {
      "text": "彼らのルーツへの敬意を形にしたTシャツは、現在どこにも在庫がなく、入手が困難となっている。",
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
      "text": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
      "is_correct": true
    },
    {
      "text": "企業には単純な作業だけで済む余裕はなく、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
      "is_correct": true
    },
    {
      "text": "今日は時間を無い。",
      "is_correct": false,
      "error_description": "助詞：存在を表す「ない」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えている。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
      "is_correct": true
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りなければなりません。",
      "is_correct": true
    },
    {
      "text": "机の上で消しゴムがなく、友達に借りなければなりません。",
      "is_correct": false,
      "error_description": "助詞の混同（に／で）。物が存在する場所を表す場合は助詞「に」を使います。「で」は動作が行われる場所を表すため、この文脈では誤りです。"
    },
    {
      "text": "この地域には大きなスーパーがなく、日々の買い物をするのにとても不便です。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35127, level 9

#### Pack A
### Level 9 (sense 35127, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "この古い建物にはエレベーターがなく、足腰の弱い方には大変な負担となります。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "この古い建物にはエレベーターがなく、足腰の弱い方には大変な負担となります。",
  "chunks": [
    "この古い建物には",
    "エレベーターが",
    "なく足腰の",
    "弱い方には",
    "大変な負担と",
    "なります"
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
    "エレベーターが",
    "弱い方には",
    "この古い建物には",
    "大変な負担と",
    "なく足腰の",
    "なります"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "この島には十分な医療施設がなく、住民の皆様は不便な生活を強いられています。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "この島には十分な医療施設がなく、住民の皆様は不便な生活を強いられています。",
  "chunks": [
    "この島には",
    "十分な医療施設が",
    "なく住民の皆様は",
    "不便な生活を",
    "強いられて",
    "います"
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
    "強いられて",
    "なく住民の皆様は",
    "不便な生活を",
    "十分な医療施設が",
    "この島には",
    "います"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35127, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "この事業の終了には悲観的な意味はなく、資本の循環と新たな創造への移行を意味する重要なプロセスなのだ。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "この事業の終了には悲観的な意味はなく、資本の循環と新たな創造への移行を意味する重要なプロセスなのだ。",
  "chunks": [
    "この事業の",
    "終了には悲観的な意味は",
    "なく資本の循環と",
    "新たな創造への移行を",
    "意味する重要なプロセスなの",
    "だ"
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
    "終了には悲観的な意味は",
    "新たな創造への移行を",
    "この事業の",
    "意味する重要なプロセスなの",
    "なく資本の循環と",
    "だ"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。",
  "chunks": [
    "記号論の観点から色を",
    "分析するとそこには偶然の",
    "選択はなくすべてが特定の",
    "メッセージを",
    "伝える記号と",
    "して機能している"
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
    "伝える記号と",
    "選択はなくすべてが特定の",
    "メッセージを",
    "分析するとそこには偶然の",
    "記号論の観点から色を",
    "して機能している"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```

---
