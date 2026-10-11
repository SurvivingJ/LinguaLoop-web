# Pairwise review pack 05

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


## sense 35111, level 4

#### Pack A
### Level 4 (sense 35111, difficulty None)
**morphology_slot** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "植物から色素が解放される現象は、熱と水という物理的作用に依るものである。",
  "original_sentence": "植物から色素が解放される現象は、熱と水という物理的作用に依るものである。",
  "correct_answer": "よっ",
  "base_form": "よる",
  "form_label": "連用形促音便",
  "options": [
    "よる",
    "よらない",
    "より",
    "よっ"
  ],
  "explanation": "「～に依るものである」の文脈では、連用形促音便の「よっ」が適切に接続する",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よっ"
}
```
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "植物から色素が解放される現象は、熱と水という物理的作用___依るものである。",
  "original_sentence": "植物から色素が解放される現象は、熱と水という物理的作用に依るものである。",
  "options": [
    "で",
    "を",
    "に",
    "と"
  ],
  "correct_answer": "に",
  "target_word": "よっ",
  "error_tags": {
    "を": "case_error",
    "で": "particle_meaning_mismatch",
    "と": "syntax_error"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。『〜に依る』は固定された格助詞の搭配です。"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "収量の安定化を通じて収益性が向上するのは、センサー等を用いた技術導入に依るものである。",
  "original_sentence": "収量の安定化を通じて収益性が向上するのは、センサー等を用いた技術導入に依るものである。",
  "correct_answer": "より",
  "base_form": "よる",
  "form_label": "連用形",
  "options": [
    "よる",
    "より",
    "よって",
    "よらない"
  ],
  "explanation": "連用形「より」は名詞的用法や副詞的用法として、「～によるものである」の構成要素として適切に機能する",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "より"
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "収量の安定化を通じて収益性が向上するのは、センサー等を用いた技術導入___依るものである。",
  "original_sentence": "収量の安定化を通じて収益性が向上するのは、センサー等を用いた技術導入に依るものである。",
  "options": [
    "と",
    "に",
    "を",
    "で"
  ],
  "correct_answer": "に",
  "target_word": "より",
  "error_tags": {
    "を": "case_error",
    "で": "particle_meaning_mismatch",
    "と": "syntax_error"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。『〜に依る』は固定された格助詞の搭配です。"
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

## sense 35111, level 6

#### Pack A
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "彼の成功は、若い頃からの不断の努力によります。",
      "is_correct": false
    },
    {
      "text": "彼の成功は、若い頃からの不断の努力によるものだ。",
      "is_correct": true
    },
    {
      "text": "彼の成功は、若い頃からの不断の努力によっていることだ。",
      "is_correct": false
    },
    {
      "text": "彼の成功は、若い頃からの不断の努力をよるものだ。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。『よる』は自動詞であり、直接目的語『を』を取ることはできません。 誤答。『〜ことだ』は勧誘や定義を表す表現であり、事実の説明である『〜ものだ』とは文脈が異なります。 誤答。文末が丁寧語『ます』で終わっており、説明的な文体『〜ものだ』と整合しません。",
  "target_word": "よる"
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "よる",
  "relation": "synonym",
  "options": [
    "依存する",
    "起因する",
    "無関係である",
    "結果する"
  ],
  "correct_answer": "起因する",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
      "explanation": "正解。『よる（依る）』と同様に、ある事柄が別の事柄の原因となることを表す類義語です。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "学習者の認知特性に最適化された教材提示が可能になるのは、人工知能アルゴリズムによるリアルタイム分析を依るものである。",
      "is_correct": false
    },
    {
      "text": "学習者の認知特性に最適化された教材提示が可能になるのは、人工知能アルゴリズムによるリアルタイム分析に依ることだ。",
      "is_correct": false
    },
    {
      "text": "学習者の認知特性に最適化された教材提示が可能になるのは、人工知能アルゴリズムによるリアルタイム分析に依るものである。",
      "is_correct": true
    },
    {
      "text": "学習者の認知特性に最適化された教材提示が可能になるのは、人工知能アルゴリズムによるリアルタイム分析に依ります。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。『依る』は自動詞であり、直接目的語『を』を取ることはできません。 誤答。『〜ことだ』は勧誘や定義を表す表現であり、事実の説明である『〜ものである』とは文脈が異なります。 誤答。文末が丁寧語『ます』で終わっており、説明的な文体『〜ものである』と整合しません。",
  "target_word": "よる"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "よる",
  "relation": "synonym",
  "options": [
    "結果する",
    "依存する",
    "起因する",
    "無関係である"
  ],
  "correct_answer": "起因する",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
      "explanation": "正解。『よる（依る）』と同様に、ある事柄が別の事柄の原因となることを表す類義語です。"
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
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "天然染料による染色の美しさは、素材との対話という儀礼的な過程に依るものである。",
      "is_correct": false,
      "error_description": "誤答。『依る』は自動詞であり、対象に『を』ではなく『に』を用いる必要があります。"
    },
    {
      "text": "天然染料による染色の美しさは、素材との対話という儀礼的な過程に依るものである。",
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

## sense 35111, level 9

#### Pack A
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

#### Pack B
### Level 9 (sense 35111, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "空間に深みを与える陰影の演出は、間接照明の配置に依るところが大きい。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "空間に深みを与える陰影の演出は、間接照明の配置に依るところが大きい。",
  "chunks": [
    "空間に深みを",
    "与える陰影の",
    "演出は間接照明の",
    "配置に",
    "依るところが",
    "大きい"
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
    "配置に",
    "大きい",
    "与える陰影の",
    "演出は間接照明の",
    "空間に深みを",
    "依るところが"
  ],
  "target_word": "よる",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "彼の成功は、若い頃からの不断の努力によるものだ。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "彼の成功は、若い頃からの不断の努力によるものだ。",
  "chunks": [
    "彼の",
    "成功は",
    "若い頃から",
    "の不断の",
    "努力に",
    "よるものだ"
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
    "努力に",
    "成功は",
    "よるものだ",
    "の不断の",
    "若い頃から",
    "彼の"
  ],
  "target_word": "よる",
  "chunk_count": 6
}
```

---

## sense 35293, level 1

#### Pack A
### Level 1 (sense 35293, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "word": "極めて",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "きわめて",
  "pronunciation": "きわめて",
  "ipa": "kiwamete",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "きめて",
    "たしかめて",
    "きよめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "explanation": "「きわめて」が対象語の正しい表記です。",
  "distractor_explanations": {
    "きよめて": "「きよめて」＝清めて。2番目のモーラが「わ→よ」で異なる別語。",
    "きめて": "「きめて」＝決めて。促音位置が異なる短い対比語。",
    "たしかめて": "「たしかめて」＝確かめて。末尾の音形が近い対比語。"
  },
  "distractor_source": "llm"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "correct_answer": "極めて",
  "word": "極めて",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "大好き": "component",
    "分厚い": "component",
    "認める": "frequency"
  }
}
```

#### Pack B
### Level 1 (sense 35293, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "word": "極めて",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "correct_answer": "極めて",
  "word": "極めて",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "大好き": "component",
    "分厚い": "component",
    "認める": "frequency"
  }
}
```

---

## sense 35293, level 2

#### Pack A
### Level 2 (sense 35293, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "correct_definition": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
  "options": [
    "ビジネスなどで、投資した利益を得るために事業から離れる方法や戦略。",
    "非常に速いさま。速やかなさま。",
    "ある期間ごとにくり返し行われること。また、そのさま。",
    "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ペットとしてよく飼われる、四本足の動物です。",
        "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
        "a picture (drawing)",
        "天気の状態を予測して知らせること。特に気象庁などが発表するもの。"
      ],
      "correct_answer": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35293, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "correct_definition": "状態や動作の度合いが、とても高いことを表す副詞。",
  "options": [
    "数量や程度が非常に大きいこと。",
    "状態や動作の度合いが、とても高いことを表す副詞。",
    "「本来」は、あるものが初めからそうであること、または当然そうあるべき状態を表す語です。",
    "本物ではないこと。実際には存在しないことや、うそであること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "polyester — a fiber chemically synthesized from petroleum, resistant to wrinkling and quick-drying, used in clothing",
        "状態や動作の度合いが、とても高いことを表す副詞。",
        "指や道具で、ものをこすってまぜること。",
        "轮次 —— 表示顺序的词，尤指做某事的次序，或按顺序分配的角色"
      ],
      "correct_answer": "状態や動作の度合いが、とても高いことを表す副詞。"
    }
  }
}
```

---

## sense 35293, level 6

#### Pack A
### Level 6 (sense 35293, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難な局面を迎えている。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担うう。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割が担う。",
      "is_correct": false
    },
    {
      "text": "担う役割を重要な極めてCCUSは、領域において炭素発生をゼロ化し得ない。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「担う」の対象は「を」で示す。「が」は誤り。 活用：辞書形は「担う」であり、「担うう」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "極めて"
}
```

#### Pack B
### Level 6 (sense 35293, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難な局面を迎えている。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担うう。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割が担う。",
      "is_correct": false
    },
    {
      "text": "担う役割を重要な極めてCCUSは、領域において炭素発生をゼロ化し得ない。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「担う」の対象は「を」で示す。「が」は誤り。 活用：辞書形は「担う」であり、「担うう」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "極めて"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その判断は極めて危険だ。",
      "is_correct": true
    },
    {
      "text": "その判断は極めて三つ危険だ。",
      "is_correct": false
    },
    {
      "text": "その判断は極めて危険だ。",
      "is_correct": false
    },
    {
      "text": "その判断は極めて危険をだ。",
      "is_correct": false
    }
  ],
  "explanation": "これは正しい文です。対象語「極めて」が形容動詞「危険だ」の程度を適切に修飾しています。 助数詞の誤り：「極めて」は程度を表す副詞であり、数量や個数を表す助数詞「三つ」と直接結びついて名詞を修飾する構造にはなりません。また、「三つ危険だ」という表現自体も不自然です。 助詞の混同：「危険だ」は形容動詞の終止形です。「危険を」とすると名詞扱いになり、文末の「だ」と接続できず、文法的に破綻します。",
  "target_word": "極めて"
}
```

---

## sense 35293, level 7

#### Pack A
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入は、現代社会において極めてに重要な課題である。",
      "is_correct": false,
      "error_description": "副詞「極めて」の後に助詞「に」を付けるのは誤りです。副詞は助詞を介さずに直接形容詞や動詞を修飾します。"
    },
    {
      "text": "その社会的意義は極めて大きい。",
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
      "text": "この問題は極めてに難しい。",
      "is_correct": false,
      "error_description": "助詞の混同。副詞「極めて」の後に格助詞「に」を誤って付加している。副詞は助詞を伴わずに直接形容詞を修飾する。"
    },
    {
      "text": "極めて珍しい花が咲いている。",
      "is_correct": true
    },
    {
      "text": "極めて大切な友達です。",
      "is_correct": true
    },
    {
      "text": "この問題は極めて難しい。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その社会的意義は極めて大きいだ。",
      "is_correct": false,
      "error_description": "形容詞「大きい」の後に断定の助動詞「だ」を直接付けることはできません。形容詞述語文では、そのまま終止形として用いるか、丁寧語の場合は「です」を用います。"
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "その社会的意義は極めて大きい。",
      "is_correct": true
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
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
      "text": "その問題が極めて難しい。",
      "is_correct": false,
      "error_description": "「は」を「が」に置き換えると、主題として提示する働きが失われる。"
    },
    {
      "text": "この問題は極めて複雑です。",
      "is_correct": true
    },
    {
      "text": "その判断は極めて危険だ。",
      "is_correct": true
    },
    {
      "text": "彼の意見は極めて正しい。",
      "is_correct": true
    }
  ]
}
```

---

## sense 38099, level 1

#### Pack A
### Level 1 (sense 38099, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "昇華",
  "options": [
    "しょうが",
    "じょうか",
    "しいょうか",
    "しょうか"
  ],
  "correct_answer": "しょうか",
  "word": "昇華",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "しょうか",
  "options": [
    "上昇",
    "飛躍",
    "昇華",
    "飛ぶ"
  ],
  "correct_answer": "昇華",
  "word": "昇華",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "上昇": "component",
    "飛ぶ": "component",
    "飛躍": "component"
  }
}
```

#### Pack B
### Level 1 (sense 38099, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "昇華",
  "options": [
    "しょうが",
    "じょうか",
    "しいょうか",
    "しょうか"
  ],
  "correct_answer": "しょうか",
  "word": "昇華",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "しょうか",
  "options": [
    "上昇",
    "飛躍",
    "昇華",
    "飛ぶ"
  ],
  "correct_answer": "昇華",
  "word": "昇華",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "上昇": "component",
    "飛ぶ": "component",
    "飛躍": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "ipa": "/ɕoːka/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "焦土",
    "老化",
    "象戯",
    "昇華"
  ],
  "correct_answer": "昇華",
  "explanation": "正解です。「昇華」は「ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。」という意味です。",
  "distractor_explanations": {
    "老化": "「老化」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「ろ」、一部の音の違い）。",
    "象戯": "「象戯」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ぎ」、一部の音の違い）。",
    "焦土": "「焦土」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 38099, level 2

#### Pack A
### Level 2 (sense 38099, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "correct_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "options": [
    "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
    "物事を最後までやり遂げて、完全な状態にすること。",
    "周囲よりも温度が低い状態。特に、冷蔵庫や冷凍庫の中のような冷たい温度を指すことが多い。",
    "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "fresh",
        "細かいところまで気を配り、丁寧で思いやりのある様子。",
        "何人 —— 询问一个人的身份、性质或立场的词，多用于「…是何人」的疑问句",
        "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
      ],
      "correct_answer": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 38099, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "correct_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "options": [
    "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
    "新しい事業や企業を始めること。特に、リスクが高いが大きな成長が期待される事業。",
    "「オート」は接頭語で、自動的な、または自己のという意味を表します。主に外来語の一部として使われます。",
    "構造物や建築物を作り上げる。柱や壁などを組み立てて完成させる。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "自分の手の届くあたり。",
        "数值",
        "心跳",
        "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
      ],
      "correct_answer": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
    }
  }
}
```

---
