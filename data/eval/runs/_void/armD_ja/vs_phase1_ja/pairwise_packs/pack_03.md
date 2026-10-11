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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析などの高度な技術___駆使した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析などの高度な技術を駆使した「精密農業」が注目されています。",
  "options": [
    "に",
    "を",
    "が",
    "で"
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
      "explanation": "他動詞「駆使する」の直接目的語を標示する"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "技術___応用して新しい物を作りました。",
  "original_sentence": "技術を応用して新しい物を作りました。",
  "options": [
    "に",
    "で",
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
      "explanation": "他動詞「応用する」の直接目的語を標示する"
    }
  }
}
```

---

## sense 35093, level 7

#### Pack A
### Level 7 (sense 35093, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼らはその技術が研究している。",
      "is_correct": false,
      "error_description": "助詞：他動詞「研究する」の対象は「を」で示す。「が」は誤り。"
    },
    {
      "text": "新しい技術を学ぶことは楽しいです。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた新しい技術を導入すれば、収量の安定化により収益性を向上させます。",
      "is_correct": true
    },
    {
      "text": "近年、センサーやデータ解析などの高度な技術を駆使した「精密農業」が注目されています。",
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
      "text": "技術を磨くために毎日努力を払っています。",
      "is_correct": false,
      "error_description": "「努力」は「する」と結びつく名詞であり、「払う」とは共起しません。「努力する」が正しい表現です。"
    },
    {
      "text": "技術を応用して新しい物を作りました。",
      "is_correct": true
    },
    {
      "text": "技術が進んで生活が便利になりました。",
      "is_correct": true
    },
    {
      "text": "その技術は社会に役立っています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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
  "ipa": "/joɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "鑄る",
    "因る",
    "釬",
    "猟る"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "鑄る": "「鑄る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「い」、一部の音の違い）。",
    "釬": "「釬」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「み」、一部の音の違い）。",
    "猟る": "「猟る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「か」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35111, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 35111, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "天然染料に___染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "original_sentence": "天然染料による染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
  "correct_answer": "よっ",
  "options": [
    "よっ",
    "笑っ",
    "走っ",
    "行っ"
  ],
  "explanation": "「によって」は原因・手段を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よる"
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
      "text": "社長による会社の買収は、投資家にとって大きな利益を得るための重要な出口戦略である。",
      "is_correct": true
    },
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
      "text": "こうした文脈下、人工知能アルゴリズムによってリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": false
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": false
    },
    {
      "text": "天然染料による染色は、単なる化学的操作の連鎖ではなく、素材と対話する儀礼にも等しい。",
      "is_correct": true
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによったリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": false
    }
  ],
  "explanation": "正しい文です。「～による」が「原因・手段」を表し、その結果として「教材提示を可能にする」という機能・結果が導かれる自然な文です。 助詞の混同：「～によって」の後ろに名詞（リアルタイムの習熟度分析）を続けることはできません。「による」＋名詞の形にする必要があります。 活用・アスペクトの誤り：「よった」は過去の確定・完了を表すため、まだ実現していない「教材提示を可能にする」という将来的・一般的な機能説明の修飾語としては不適切です。",
  "target_word": "よる"
}
```

---

## sense 35111, level 7

#### Pack A
### Level 7 (sense 35111, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "地震による建物の倒壊は、多くの命を奪い、街の機能を完全に失わせた。",
      "is_correct": true
    },
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
      "text": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
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
      "text": "結果として、建築は静的な物体ではなく、見る者によって絶えず意味が更新される開かれた場として再定義されるのです。",
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
      "text": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
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
    "無い",
    "鳴る",
    "肢位",
    "ヤイ"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「物やことが存在しない。そこにそれがない状態。」という意味です。",
  "distractor_explanations": {
    "肢位": "「肢位」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「し」、一部の音の違い）。",
    "ヤイ": "「ヤイ」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「や」、一部の音の違い）。",
    "鳴る": "「鳴る」は「無い」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「る」、一部の音の違い）。"
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
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "この地域には総合病院が___、住民たちは毎回遠くまで通院しなければならない状況です。",
  "original_sentence": "この地域には総合病院がなく、住民たちは毎回遠くまで通院しなければならない状況です。",
  "correct_answer": "なく",
  "options": [
    "いそがしく",
    "おおく",
    "たのしく",
    "なく"
  ],
  "explanation": "正解です。文脈に合致する「ない」の連用形です。",
  "distractor_tags": {},
  "word_definition": "物やことが存在しない。そこにそれがない状態。",
  "target_word": "なく"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この部屋には収納するためのクローゼットが___、家具の配置にとても頭を悩ませています。",
  "original_sentence": "この部屋には収納するためのクローゼットがなく、家具の配置にとても頭を悩ませています。",
  "correct_answer": "なく",
  "options": [
    "余り",
    "遠く",
    "なく",
    "高く"
  ],
  "explanation": "正解です。文脈から「存在しない」という意味が適切です。",
  "distractor_tags": {},
  "word_definition": "物やことが存在しない。そこにそれがない状態。",
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
  "sentence_with_blank": "現在のプロジェクトには十分な資金が___、新たな投資家を探すのが急務となっています。",
  "original_sentence": "現在のプロジェクトには十分な資金がなく、新たな投資家を探すのが急務となっています。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中止法）",
  "options": [
    "なく",
    "なければ",
    "なかった",
    "ない"
  ],
  "explanation": "形容詞の連用形「く」による中止法で、後続の文へ自然に接続します。",
  "word_definition": "物やことが存在しない。そこにそれがない状態。",
  "target_word": "なく"
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
      "text": "この町には大きなスーパーマーケットがなかく、買い物をするのに毎回車で移動しなければなりません。",
      "is_correct": false
    },
    {
      "text": "この町には大きなスーパーマーケットがなくて、買い物をするのに毎回車で移動しなければなりません。",
      "is_correct": false
    },
    {
      "text": "この町には大きなスーパーマーケットがなく、買い物をするのに毎回車で移動しなければなりません。",
      "is_correct": false
    },
    {
      "text": "この古い工場には最新の安全設備がなく、従業員たちの作業環境の改善が求められています。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：「には～が」の対比構造において、存在の否定には「は」ではなく「が」を使うのが自然です。 活用・アスペクトの誤り：形容詞「ない」の連用形は「なく」であり、「なかく」という活用形は存在しません。 語順・係り受けの誤り：「なく」の直後に読点（、）を置くと、後続の文との係り受けが不自然になり、文のまとまりが損なわれます。",
  "target_word": "なく"
}
```
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "少ない",
    "多い",
    "ある",
    "広い"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物やことが存在しない。そこにそれがない状態。",
      "explanation": "物やことが存在する状態を表し、目標語の対義語となる。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "大切な書類がなくことに気づいて、慌てて探した。",
      "is_correct": false
    },
    {
      "text": "大切な書類がないことに気づいて、慌てて探した。",
      "is_correct": true
    },
    {
      "text": "なく大切な書類に気づいて、慌てて探した。",
      "is_correct": false
    },
    {
      "text": "大切な書類がなくてに気づいて、慌てて探した。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「が」の後に「なくてに」と続けるのは文法的に誤りです。「ないことに」とするのが正しい形です。 活用・アスペクトの誤り：「なく」の後に直接「こと」を続けることはできません。「ないこと」と活用させる必要があります。 語順・係り受けの誤り：「なく」が修飾するべき「書類」から離れすぎており、文の構造が破綻しています。",
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
