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


## sense 35111, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 35111, difficulty 8)
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "joɾɯ",
  "word": "よっ",
  "options": [
    "宵",
    "よっ",
    "酔う",
    "慾"
  ],
  "audio_url": null,
  "explanation": "正解です。「よっ」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "pronunciation": "よる",
  "correct_answer": "よっ",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "宵": "「宵」は「よっ」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「い」、一部の音の違い）。",
    "慾": "「慾」は「よっ」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「く」、一部の音の違い）。",
    "酔う": "「酔う」は「よっ」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「う」、一部の音の違い）。"
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
### Level 2 (sense 35111, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "improvement",
        "a task; an issue — a problem to be solved or a goal to be worked on",
        "载客（用）",
        "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
      ],
      "correct_answer": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
    }
  },
  "tier": "T6",
  "word": "よっ",
  "pronunciation": "よる",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "よっ",
  "options": [
    "人と関わること。特に、相手に対してある態度や行動をとること。",
    "ある土地の、自然や人工物を含めた全体的な見え方や眺め。",
    "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
    "物体が変形した後、元の形に戻ろうとする性質や力。弾性。"
  ],
  "pronunciation": "よる",
  "correct_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。"
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
### Level 3 (sense 35111, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "笑っ",
    "走っ",
    "行っ",
    "よっ"
  ],
  "explanation": "「によって」は原因・手段を表す固定表現。",
  "target_word": "よっ",
  "correct_answer": "よっ",
  "distractor_tags": {},
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "original_sentence": "デザイナーの直感に頼るのではなく、計算された論理によって、機能的かつ独創的な都市空間を創出することが目指されています。",
  "sentence_with_blank": "デザイナーの直感に頼るのではなく、計算された論理に___て、機能的かつ独創的な都市空間を創出することが目指されています。"
}
```

---

## sense 35111, level 4

#### Pack A
### Level 4 (sense 35111, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "よっ",
  "answer": {
    "accepted": [
      "より"
    ],
    "accepted_normalized": [
      "より"
    ]
  },
  "input_mode": "ime",
  "target_word": "より",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
  "sentence_with_blank": "これらに___、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "より",
    "よれば",
    "よって",
    "よった"
  ],
  "base_form": "因る",
  "form_label": "連用形（〜により）",
  "explanation": "「これにより」は連用形で後に文が続く接続的な形。",
  "target_word": "より",
  "correct_answer": "より",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
  "sentence_with_blank": "これらに___、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "よっ",
  "answer": {
    "accepted": [
      "よっ",
      "因った",
      "因って",
      "因れば"
    ],
    "accepted_normalized": [
      "よっ",
      "因った",
      "因って",
      "因れば"
    ]
  },
  "input_mode": "ime",
  "target_word": "よっ",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "高温のオーブンへ投入された瞬間、生地は熱エネルギーによって急激に膨張します。",
  "sentence_with_blank": "高温のオーブンへ投入された瞬間、生地は熱エネルギーに___て急激に膨張します。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "よっ",
    "よれば",
    "よった",
    "より"
  ],
  "base_form": "因る",
  "form_label": "連用形＋て形（〜によって）",
  "explanation": "「によって」は原因・手段を表す連用形＋て形の固定表現。",
  "target_word": "よっ",
  "correct_answer": "よっ",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "original_sentence": "高温のオーブンへ投入された瞬間、生地は熱エネルギーによって急激に膨張します。",
  "sentence_with_blank": "高温のオーブンへ投入された瞬間、生地は熱エネルギーに___て急激に膨張します。"
}
```

#### Pack B
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
### Level 6 (sense 35111, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "具体的には、無垢材の家具と白壁の組み合わせ、あるいは間接照明による陰影の演出などが効果的です。",
      "is_correct": true
    },
    {
      "text": "間接照明が陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "間接照明に因れば陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "効果的です陰影の演出などが、間接照明による組み合わせと家具の白壁無垢材。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：手段を表す「による」を省くと「が」が二重になり文が成立しない。 活用：仮定形「因れば」は条件の意味になり、手段を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
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
### Level 7 (sense 35111, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "デザイナーの直感に頼るのではなく、計算された論理によって、機能的かつ独創的な都市空間を創出することが目指されています。",
      "is_correct": true
    },
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "計算された論理がよって、機能的な都市空間を創出することが目指されています。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることができます。",
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
      "text": "結果として、建築は静的な物体ではなく、見る者によって絶えず意味が更新される開かれた場として再定義されるのです。",
      "is_correct": true
    },
    {
      "text": "高温のオーブンへ投入された瞬間、生地は熱エネルギーがよって急激に膨張します。",
      "is_correct": false,
      "error_description": "助詞：原因・手段を表す「による」は「に」を伴う。「が」は誤り。"
    },
    {
      "text": "高温のオーブンへ投入された瞬間、生地は熱エネルギーによって急激に膨張します。",
      "is_correct": true
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35111, level 9

#### Pack A
### Level 9 (sense 35111, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "制作は、絵師、彫師、摺師の役割分担によって進められます。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "制作は",
    "絵師",
    "彫師",
    "摺師の",
    "役割分担に",
    "よって進められます"
  ],
  "chunk_count": 6,
  "target_word": "よっ",
  "schema_version": 2,
  "shuffled_chunks": [
    "摺師の",
    "よって進められます",
    "絵師",
    "彫師",
    "制作は",
    "役割分担に"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "制作は、絵師、彫師、摺師の役割分担によって進められます。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "具体的には無垢材の",
    "家具と白壁の",
    "組み合わせ",
    "あるいは間接照明に",
    "よる陰影の演出など",
    "が効果的です"
  ],
  "chunk_count": 6,
  "target_word": "よる",
  "schema_version": 2,
  "shuffled_chunks": [
    "よる陰影の演出など",
    "家具と白壁の",
    "が効果的です",
    "あるいは間接照明に",
    "組み合わせ",
    "具体的には無垢材の"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "具体的には、無垢材の家具と白壁の組み合わせ、あるいは間接照明による陰影の演出などが効果的です。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "具体的には、無垢材の家具と白壁の組み合わせ、あるいは間接照明による陰影の演出などが効果的です。"
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
### Level 1 (sense 35293, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "きわめて",
  "schema_version": 2
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "極めて",
  "schema_version": 2,
  "distractor_sources": {
    "分厚い": "component",
    "大好き": "component",
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
### Level 2 (sense 35293, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "options": [
    "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
    "物の位置が、下よりも高い方にあること。また、その方向や場所。",
    "塩分を含まない、陸上の河川や湖沼などに存在する水。飲料水や農業・工業用水として利用される。",
    "劇場などで上映される、物語を映像と音声で表現した作品。"
  ],
  "pronunciation": "きわめて",
  "correct_definition": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "培育",
        "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
        "数量が多いこと。",
        "人や物の間で、情報や気持ちを送ったり受け取ったりすること。"
      ],
      "correct_answer": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
    }
  },
  "tier": "T6",
  "word": "極めて",
  "pronunciation": "きわめて",
  "schema_version": 2
}
```

---

## sense 35293, level 6

#### Pack A
### Level 6 (sense 35293, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "担う役割を重要な極めてCCUSは、領域において炭素発生をゼロ化し得ない。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割が担う。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担うう。",
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
