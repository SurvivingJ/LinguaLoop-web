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


## sense 35093, level 7

#### Pack A
### Level 7 (sense 35093, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は新しい技術を学んでいます。",
      "is_correct": true
    },
    {
      "text": "近年、センサーやデータ解析の技術を活用した「精密農業」が注目されています。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた技術は、収量の安定化により収益性を向上させます。",
      "is_correct": true
    },
    {
      "text": "私は新しい技術が学んでいます。",
      "is_correct": false,
      "error_description": "助詞の混同（を／が）：他動詞『学ぶ』の目的語には助詞『を』を使います。『が』を使うと『技術』が動作主として解釈され、文脈に合いません。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "料理の技術を磨くことに楽しいです。",
      "is_correct": false,
      "error_description": "助詞の混同の誤りです。名詞節を主題として提示し、それについて述述する場合は「ことは」を使います。「ことに」は方向や結果などを表す際に使われます。"
    },
    {
      "text": "料理の技術を磨くことは楽しいです。",
      "is_correct": true
    },
    {
      "text": "日本はロボットを作る技術が高いです。",
      "is_correct": true
    },
    {
      "text": "最新の技術を使ってロボットを作りました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35093, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "私は新しい技術に学びたい。",
      "is_correct": false,
      "error_description": "「学ぶ」のような他動詞の目的語を示すには、対格助詞「を」を使用する必要があります。「に」は方向や対象の帰着点を表すため、この文脈では不適切です。"
    },
    {
      "text": "近年、センサーやデータ解析などの技術を活用した「精密農業」が注目されています。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた技術は、収量の安定化により収益性を向上させます。",
      "is_correct": true
    },
    {
      "text": "私は新しい技術を学びたい。",
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
      "text": "彼女はその技術が詳しい。",
      "is_correct": false,
      "error_description": "助詞：「詳しい」の対象は「に」で示す。「が」は誤り。"
    },
    {
      "text": "この技術は世界を変えられる。",
      "is_correct": true
    },
    {
      "text": "私たちは技術を大切にすべきだ。",
      "is_correct": true
    },
    {
      "text": "技術が進歩して生活が楽になる。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35111, level 3

#### Pack A
### Level 3 (sense 35111, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "天然染料に___ところの多いこの染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "original_sentence": "天然染料によるところの多いこの染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "correct_answer": "よっ",
  "options": [
    "笑っ",
    "走っ",
    "よっ",
    "行っ"
  ],
  "explanation": "「によって」は原因・手段を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。「～に因る」の形で使われ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よる"
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

## sense 35111, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "間接照明に因れば陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "会社が成長して安定すると、創業者や投資家は自分たちの利益を得るために、他の会社によってもたらされる買収や株式の上場といった方法を選んで会社を売ることがある。",
      "is_correct": true
    },
    {
      "text": "効果的です陰影の演出などが、間接照明による組み合わせと家具の白壁無垢材。",
      "is_correct": false
    },
    {
      "text": "間接照明が陰影の演出などが効果的です。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：手段を表す「による」を省くと「が」が二重になり文が成立しない。 活用：仮定形「因れば」は条件の意味になり、手段を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
  "target_word": "よる"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "収益性を向上させます、センサー等を用いた技術導入は収量の安定化により。",
      "is_correct": false
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるところの大きいリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化に因ったら収益性を向上させます。",
      "is_correct": false
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化がより収益性を向上させます。",
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
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "天然染料によるところの多いこの染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
      "is_correct": true
    },
    {
      "text": "まず、季節の移ろいと共に採取された植物から色素が抽出されるのは、熱と水によるところが大きい。",
      "is_correct": true
    },
    {
      "text": "計算された論理がよって、機能的な都市空間を創出することが目指されています。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "自然の素材は時間とともに色や形が変わってしまうが、職人の技術による丁寧な作業によって、長く楽しめる美しい工芸品が作られるのである。",
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
      "text": "こうした文脈下、人工知能アルゴリズムによるところの大きいリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "高温のオーブンへ投入された瞬間、生地は熱エネルギーがよって急激に膨張します。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "結果として、建築は静的な物体ではなく、見る者によってもたらされる意味の更新によって絶えず再定義される開かれた場となるのです。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化によるところの大きい収益性の向上を実現します。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35127, level 1

#### Pack A
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
    "２位",
    "地位",
    "無い",
    "余意"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "distractor_explanations": {
    "２位": "「２位」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「に」、一部の音の違い）。",
    "地位": "「地位」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「ち」、一部の音の違い）。",
    "余意": "「余意」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「よ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35127, level 3

#### Pack A
### Level 3 (sense 35127, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "この店には彼らのルーツへの敬意を形にしたグッズが___、代わりに伝統的なTシャツが売られています。",
  "original_sentence": "この店には彼らのルーツへの敬意を形にしたグッズがなく、代わりに伝統的なTシャツが売られています。",
  "correct_answer": "なく",
  "options": [
    "あら",
    "たり",
    "なく",
    "まで"
  ],
  "explanation": "正解です。文脈から「敬意を形にしたグッズが存在しない」という意味になり、形容詞「ない」の連用形「なく」が適切です。",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```

#### Pack B
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

---

## sense 35127, level 4

#### Pack A
### Level 4 (sense 35127, difficulty None)
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

#### Pack B
### Level 4 (sense 35127, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "この国には資本の循環と新たな創造への移行を意味する重要なプロセスが___、事業は終了へと向かっています。",
  "original_sentence": "この国には資本の循環と新たな創造への移行を意味する重要なプロセスがなく、事業は終了へと向かっています。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中頓）",
  "options": [
    "なければ",
    "なかった",
    "ない",
    "なく"
  ],
  "explanation": "形容詞の連用形による中頓で、前後の文を自然に接続しています",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```

---

## sense 35127, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35127, difficulty None)
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "とぼしい",
    "あやふや",
    "すくない",
    "あり"
  ],
  "correct_answer": "あり",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "「存在する」ことを表し、目標語の「存在しない」という語義と対義関係にある。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "めずらしい",
    "あふれる",
    "おおい",
    "ある"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "同一語義：存在すること。何かがそこに存在していること。"
    }
  }
}
```

---

## sense 35147, level 4

#### Pack A
### Level 4 (sense 35147, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "友達と映画を見に___。",
  "original_sentence": "友達と映画を見に行っています。",
  "correct_answer": "いった",
  "base_form": "行く",
  "form_label": "た形（過去）",
  "options": [
    "いく",
    "いった",
    "いって",
    "いかない"
  ],
  "explanation": "「昨日」があるので過去のた形が必要。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行っています"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この道は狭くて、車で___。",
  "original_sentence": "この道は狭くて、車で行けません。",
  "correct_answer": "行けません",
  "base_form": "行く",
  "form_label": "可能＋ない形（丁寧）",
  "options": [
    "行きません",
    "行ける",
    "行きます",
    "行けません"
  ],
  "explanation": "「狭くて」により不可能な状況なので、可能の否定形が適切です。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行けません"
}
```

#### Pack B
### Level 4 (sense 35147, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "友達の家に遊びに___ました。",
  "original_sentence": "友達の家に遊びに行きました。",
  "correct_answer": "行き",
  "base_form": "行く",
  "form_label": "ます形（連用形）",
  "options": [
    "行かない",
    "行く",
    "行った",
    "行き"
  ],
  "explanation": "「ます」に接続するには連用形（ます形）の「行き」が必要です",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行き"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "友達の家___遊びに行きました。",
  "original_sentence": "友達の家に遊びに行きました。",
  "options": [
    "が",
    "を",
    "に",
    "で"
  ],
  "correct_answer": "に",
  "target_word": "行き",
  "error_tags": {
    "で": "location_vs_target",
    "を": "object_marking",
    "が": "topic_vs_subject"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "移動の着点を示す格助詞「に」が「家」に付き、目的地を正しく標示する"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "バスで___ばすぐに着きます。",
  "original_sentence": "バスで行けばすぐに着きます。",
  "correct_answer": "行け",
  "base_form": "行く",
  "form_label": "仮定形",
  "options": [
    "行き",
    "行く",
    "行か",
    "行け"
  ],
  "explanation": "仮定形「行け」は条件を表す「ば」に正しく接続する。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行け"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "バス___行けばすぐに着きます。",
  "original_sentence": "バスで行けばすぐに着きます。",
  "options": [
    "に",
    "を",
    "で",
    "へ"
  ],
  "correct_answer": "で",
  "target_word": "行け",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "へ": "direction"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "移動の手段を標示する格助詞「で」が適切である"
    }
  }
}
```

---

## sense 35147, level 6

#### Pack A
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は毎日電車で行くます。",
      "is_correct": false
    },
    {
      "text": "私は毎日に行きます電車。",
      "is_correct": false
    },
    {
      "text": "私は毎日電車に行きます。",
      "is_correct": false
    },
    {
      "text": "駅へはどの道で行きますか。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：移動の手段を表すには「で」を使い、「に」は目的地を表すために使います。 活用の誤り：動詞「行く」のます形は「行きます」であり、「行くます」という活用形は存在しません。 語順の誤り：日本語では動詞（行きます）が文末に来る必要があり、頻度を表す副詞句（毎日）の後に助詞「に」をつけるのも不自然です。",
  "target_word": "行く"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "行き",
  "relation": "antonym",
  "options": [
    "来",
    "戻り",
    "出",
    "止まり"
  ],
  "correct_answer": "来",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "話者や基準点へ移動する「来る」の連用形であり、目標語の対義語となる"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "来週、私は東京を行けます。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けています。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けます。",
      "is_correct": true
    },
    {
      "text": "行けます私は来週、東京に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：目的地を表す場合は「に」を使います。「を」は通過点を表します。 活用・アスペクトの誤り：未来の事柄「来週」に対して、状態継続の「ています」は使えません。 語順の誤り：日本語の動詞は文末に置きます。また、主題「私は」は文の初めに置くのが自然です。",
  "target_word": "行けます"
}
```

---
