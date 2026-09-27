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


## sense 35017, level 9

#### Pack A
### Level 9 (sense 35017, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "友達が",
    "増えて",
    "うれしい"
  ],
  "chunk_count": 3,
  "target_word": "増え",
  "schema_version": 2,
  "shuffled_chunks": [
    "うれしい",
    "増えて",
    "友達が"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "友達が増えてうれしい。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "友達が増えてうれしい。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "仕事が増えて忙しくなった。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "仕事が",
    "増えて",
    "忙しくなった"
  ],
  "chunk_count": 3,
  "target_word": "増え",
  "schema_version": 2,
  "shuffled_chunks": [
    "忙しくなった",
    "仕事が",
    "増えて"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "仕事が増えて忙しくなった。"
}
```

#### Pack B
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

---

## sense 35111, level 6

#### Pack A
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

#### Pack B
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

---

## sense 35111, level 7

#### Pack A
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

---

## sense 35127, level 1

#### Pack A
### Level 1 (sense 35127, difficulty 8)
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "nai",
  "word": "なく",
  "options": [
    "何",
    "夏",
    "ナチ",
    "なく"
  ],
  "audio_url": null,
  "explanation": "正解です。「なく」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "pronunciation": "ない",
  "correct_answer": "なく",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "何": "「何」は「なく」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「ん」、撥音「ん」の有無）。",
    "夏": "「夏」は「なく」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「つ」、一部の音の違い）。",
    "ナチ": "「ナチ」は「なく」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「ち」、一部の音の違い）。"
  }
}
```

#### Pack B
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

---

## sense 35127, level 2

#### Pack A
### Level 2 (sense 35127, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "rapid; swift — happening at a very high speed",
        "打磨（磨快）",
        "动作",
        "存在しないこと。何かがそこにないこと。"
      ],
      "correct_answer": "存在しないこと。何かがそこにないこと。"
    }
  },
  "tier": "T6",
  "word": "なく",
  "pronunciation": "ない",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "なく",
  "options": [
    "存在しないこと。何かがそこにないこと。",
    "文字の読み書きができる能力",
    "動物や植物の体をおおっている、外側の薄い部分。",
    "人に何かをさせようと働きかけること。"
  ],
  "pronunciation": "ない",
  "correct_definition": "存在しないこと。何かがそこにないこと。"
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

---

## sense 35127, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 35127, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "なく",
    "よく",
    "少なく",
    "悪く"
  ],
  "explanation": "「ではなく」は存在の否定を表す固定表現。",
  "target_word": "なく",
  "correct_answer": "なく",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "original_sentence": "単なる物置きではなく、創造性を刺激する空間にしたいと考えたのだ。",
  "sentence_with_blank": "単なる物置きでは___、創造性を刺激する空間にしたいと考えたのだ。"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "options": [
    "悪く",
    "なく",
    "多く",
    "早く"
  ],
  "explanation": "「だけでなく」は存在の否定を表す固定表現。",
  "target_word": "なく",
  "correct_answer": "なく",
  "distractor_tags": {},
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "original_sentence": "企業は、単純な作業だけでなく、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
  "sentence_with_blank": "企業は、単純な作業だけで___、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。"
}
```

---
