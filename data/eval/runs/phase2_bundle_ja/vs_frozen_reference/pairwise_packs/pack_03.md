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


## sense 35011, level 9

#### Pack A
### Level 9 (sense 35011, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "学校で",
    "発明に",
    "ついて学んだ"
  ],
  "chunk_count": 3,
  "target_word": "発明",
  "schema_version": 2,
  "shuffled_chunks": [
    "ついて学んだ",
    "学校で",
    "発明に"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "学校で発明について学んだ。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "学校で発明について学んだ。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "電球の発明は世界を変えた。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "電球の",
    "発明は",
    "世界を",
    "変えた"
  ],
  "chunk_count": 4,
  "target_word": "発明",
  "schema_version": 2,
  "shuffled_chunks": [
    "世界を",
    "発明は",
    "電球の",
    "変えた"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "電球の発明は世界を変えた。"
}
```

#### Pack B
### Level 9 (sense 35011, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "この機械は彼の発明です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "この機械は彼の発明です。",
  "chunks": [
    "この機械は",
    "彼の",
    "発明です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "発明です",
    "この機械は",
    "彼の"
  ],
  "target_word": "発明",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "発明には創造力が必要だ。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "発明には創造力が必要だ。",
  "chunks": [
    "発明に",
    "は",
    "創造力が",
    "必要だ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "創造力が",
    "は",
    "発明に",
    "必要だ"
  ],
  "target_word": "発明",
  "chunk_count": 4
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "増える",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "correct_answer": "ふえる",
  "word": "増える",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "ɸueɾu",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "添え",
    "変え",
    "据え",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "変え": "",
    "添え": "",
    "据え": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふえる",
  "options": [
    "異なる",
    "増える",
    "不思議",
    "増やす"
  ],
  "correct_answer": "増える",
  "word": "増える",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "増やす": "component",
    "不思議": "component",
    "異なる": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35017, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "増え",
  "prompt": "増え",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "ふえる",
  "schema_version": 2
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "増え",
  "prompt": "ふえる",
  "options": [
    "調理",
    "増え",
    "重量",
    "増える"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "増え",
  "schema_version": 2,
  "distractor_sources": {
    "調理": "component",
    "重量": "component",
    "増える": "homophone"
  }
}
```

---

## sense 35017, level 2

#### Pack A
### Level 2 (sense 35017, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "増え",
  "options": [
    "数や量が今より多くなること。",
    "食用として効率よく育てられるように改良されたにわとりの種類です。",
    "数量や程度が非常に大きいさま。",
    "「優しくする」の形で、思いやりを持って接する、親切に振る舞うという意味の動詞表現。"
  ],
  "pronunciation": "ふえる",
  "correct_definition": "数や量が今より多くなること。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "销售额；营业额；销售收入",
        "泥 —— 土和水混合而成的柔软物质",
        "sheepskin",
        "数や量が今より多くなること。"
      ],
      "correct_answer": "数や量が今より多くなること。"
    }
  },
  "tier": "T6",
  "word": "増え",
  "pronunciation": "ふえる",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 35017, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "ある目的を達成するために考え出された方法や手段。",
    "物事の内容や理由などを、相手によくわかるように述べること。",
    "数量や程度が多くなる。",
    "物事の進行や機能を妨げること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "「モンスターと戦う」で、ゲーム内の敵キャラクターに対して攻撃や防御などの行動をすること。実際の争いではなく、遊びの範囲での対決。",
        "the lower part",
        "文字を読んだり書いたりできること",
        "数量や程度が多くなる。"
      ],
      "correct_answer": "数量や程度が多くなる。"
    }
  }
}
```

---

## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられる"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられる"
    ]
  },
  "input_mode": "ime",
  "target_word": "増え",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "最近、体重が増えてきた。",
  "sentence_with_blank": "最近、体重が___てきた。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "枯れ",
    "冷え",
    "増え",
    "晴れ"
  ],
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "explanation": "て形。「～てきた」の形に合う。",
  "target_word": "増え",
  "correct_answer": "増え",
  "word_definition": "数や量が今より多くなること。",
  "original_sentence": "最近、体重が増えてきた。",
  "sentence_with_blank": "最近、体重が___てきた。"
}
```
**particle_selection** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語を標示する格助詞として正しい"
    }
  },
  "options": [
    "が",
    "に",
    "を",
    "で"
  ],
  "error_tags": {
    "で": "instrument",
    "に": "location_vs_target",
    "を": "object_marking"
  },
  "target_word": "増え",
  "correct_answer": "が",
  "schema_version": 2,
  "original_sentence": "最近、体重が増えてきた。",
  "sentence_with_blank": "最近、体重___増えてきた。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられる"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられる"
    ]
  },
  "input_mode": "ime",
  "target_word": "増え",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "病気になる人が増えている。",
  "sentence_with_blank": "病気になる人が___ている。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "冷え",
    "晴れ",
    "枯れ",
    "増え"
  ],
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "explanation": "て形の語幹。「病気になる人が～いる」に合う。",
  "target_word": "増え",
  "correct_answer": "増え",
  "word_definition": "数や量が今より多くなること。",
  "original_sentence": "病気になる人が増えている。",
  "sentence_with_blank": "病気になる人が___ている。"
}
```

#### Pack B
### Level 4 (sense 35017, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "公園で遊ぶ子供たちの数が___ました。",
  "original_sentence": "公園で遊ぶ子供たちの数が増えました。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えること"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えること"
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
  "sentence_with_blank": "公園で遊ぶ子供たちの数が___ました。",
  "original_sentence": "公園で遊ぶ子供たちの数が増えました。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "ます形語幹",
  "options": [
    "増える",
    "増えて",
    "増え",
    "増えない"
  ],
  "explanation": "「ました」に接続する連用形（ます形）の語幹として正しい",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "公園で遊ぶ子供たちの数___増えました。",
  "original_sentence": "公園で遊ぶ子供たちの数が増えました。",
  "options": [
    "が",
    "を",
    "に",
    "で"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "",
    "に": "",
    "で": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語を示す助詞として最も自然です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この町には新しいお店が___ています。",
  "original_sentence": "この町には新しいお店が増えています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えること"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えること"
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
  "sentence_with_blank": "この町には新しいお店が___ています。",
  "original_sentence": "この町には新しいお店が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（ます形語幹）",
  "options": [
    "増え",
    "増えて",
    "増える",
    "増えた"
  ],
  "explanation": "「ています」に接続する連用形（ます形の語幹）が正解です。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この町には新しいお店___増えています。",
  "original_sentence": "この町には新しいお店が増えています。",
  "options": [
    "を",
    "が",
    "に",
    "で"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "",
    "に": "",
    "で": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語を示す助詞として最も自然です。"
    }
  }
}
```

---

## sense 35017, level 6

#### Pack A
### Level 6 (sense 35017, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "仕事が増えて忙しくなった。",
      "is_correct": true
    },
    {
      "text": "音が増えることを切った。",
      "is_correct": false
    },
    {
      "text": "星が増えることを着た。",
      "is_correct": false
    },
    {
      "text": "机が増えることを飲んだ。",
      "is_correct": false
    }
  ],
  "explanation": "「机が増えること」という事実を飲むことはできない。 事実を着ることはできない。 事実を切ることはできない。",
  "target_word": "増え"
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "光が増えることを切った。",
      "is_correct": false
    },
    {
      "text": "雲が増えることを食べた。",
      "is_correct": false
    },
    {
      "text": "雨で川の水が増えた。",
      "is_correct": true
    },
    {
      "text": "夢が増えることを着た。",
      "is_correct": false
    }
  ],
  "explanation": "事実を食べることはできない。 事実を着ることはできない。 事実を切ることはできない。",
  "target_word": "増え"
}
```
**synonym_antonym_match** variant `B`, tier `T6`
```json
{
  "nl": {
    "en": {
      "definition": "数や量が今より多くなること。",
      "explanation": "数量や程度が少なくなるという点で、目標語の語義と対義関係にある"
    }
  },
  "word": "増え",
  "options": [
    "変わり",
    "続き",
    "減り",
    "止まり"
  ],
  "relation": "antonym",
  "correct_answer": "減り",
  "schema_version": 2
}
```

#### Pack B
### Level 6 (sense 35017, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "最近、自転車に乗る人が増えられていますようです。",
      "is_correct": false
    },
    {
      "text": "最近、自転車に乗る人を増えているようです。",
      "is_correct": false
    },
    {
      "text": "最近、自転車に乗る人が増やしているようです。",
      "is_correct": false
    },
    {
      "text": "最近、自転車に乗る人が増えているようです。",
      "is_correct": true
    }
  ],
  "explanation": "「増える」は自動詞なので、人を目的語（〜を）にとることはできません。 文脈的に人が自発的に増やす行為をしているわけではなく、自然現象や傾向として増えているため、他動詞「増やす」の進行形は不自然です。 「増える」に受身や可能の助動詞を直接つけるのは文法的に誤りです。",
  "target_word": "増え"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "増え",
  "relation": "synonym",
  "options": [
    "下がる",
    "続く",
    "少なくなる",
    "多くなる"
  ],
  "correct_answer": "多くなる",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "数量や程度が多くなる。",
      "explanation": "「増える」の類義語です。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "勉強時間が増やしますと、成績が良くなります。",
      "is_correct": false
    },
    {
      "text": "勉強時間を増えると、成績が良くなります。",
      "is_correct": false
    },
    {
      "text": "勉強時間が増えると、成績が良くなります。",
      "is_correct": true
    },
    {
      "text": "勉強時間が増えられますと、成績が良くなります。",
      "is_correct": false
    }
  ],
  "explanation": "「増える」は自動詞なので、時間を目的語（〜を）にとることはできません。 文脈的に勉強時間が自発的に増やす行為をするわけではないため、他動詞「増やす」は不自然です。 「増える」に受身や可能の助動詞を直接つけるのは文法的に誤りです。",
  "target_word": "増え"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "増え",
  "relation": "synonym",
  "options": [
    "続く",
    "多くなる",
    "下がる",
    "少なくなる"
  ],
  "correct_answer": "多くなる",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "数量や程度が多くなる。",
      "explanation": "「増える」の類義語です。"
    }
  }
}
```

---

## sense 35017, level 9

#### Pack A
### Level 9 (sense 35017, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "間違いが減って、正解が増えました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "間違いが減って、正解が増えました。",
  "chunks": [
    "間違いが",
    "減って",
    "正解が",
    "増えました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "増えました",
    "正解が",
    "減って",
    "間違いが"
  ],
  "target_word": "増え",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "最近、自転車に乗る人が増えているようです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "最近、自転車に乗る人が増えているようです。",
  "chunks": [
    "最近",
    "自転車に",
    "乗る人が",
    "増えて",
    "いるようです"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "いるようです",
    "乗る人が",
    "最近",
    "自転車に",
    "増えて"
  ],
  "target_word": "増え",
  "chunk_count": 5
}
```

#### Pack B
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

---

## sense 35033, level 1

#### Pack A
### Level 1 (sense 35033, difficulty 8)
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "naɾɯ",
  "word": "なり",
  "options": [
    "綯う",
    "奈良",
    "切る",
    "なり"
  ],
  "audio_url": null,
  "explanation": "正解です。「なり」は「物事や状態が変化して、ある結果・状態になる。」という意味です。",
  "pronunciation": "なる",
  "correct_answer": "なり",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "切る": "「切る」は「なり」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「き」、一部の音の違い）。",
    "奈良": "「奈良」は「なり」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「ら」、一部の音の違い）。",
    "綯う": "「綯う」は「なり」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「う」、一部の音の違い）。"
  }
}
```

#### Pack B
### Level 1 (sense 35033, difficulty None)
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "なる",
  "options": [
    "為る",
    "成功",
    "完成",
    "成る"
  ],
  "correct_answer": "成る",
  "word": "成る",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "為る": "homophone",
    "成功": "component",
    "完成": "component"
  }
}
```

---

## sense 35033, level 2

#### Pack A
### Level 2 (sense 35033, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "なり",
  "options": [
    "人や物事に強く惹かれる性質や、価値があると感じさせる要素。",
    "物事や状態が変化して、ある結果・状態になる。",
    "電気エネルギーを化学エネルギーとして蓄え、必要なときに電気として取り出せる装置。",
    "思春期とは、心と体が大人へと変化していく時期を指します。"
  ],
  "pronunciation": "なる",
  "correct_definition": "物事や状態が変化して、ある結果・状態になる。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "作者",
        "盒子",
        "提高 —— 事物的程度或状态上升到更高的水平",
        "物事や状態が変化して、ある結果・状態になる。"
      ],
      "correct_answer": "物事や状態が変化して、ある結果・状態になる。"
    }
  },
  "tier": "T6",
  "word": "なり",
  "pronunciation": "なる",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 35033, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "なれる",
  "pronunciation": "なる",
  "correct_definition": "物事や状態が変化して、ある結果・状態になる。",
  "options": [
    "病気やけがを治療するための方法や手段。薬を使ったり、手術をしたりすることなど。",
    "酸素が少なく、物が腐りやすい状態のこと。",
    "物事や状態が変化して、ある結果・状態になる。",
    "有機物を微生物の働きで分解・発酵させて作られる、肥料として使える土のようなもの。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "なれる",
  "pronunciation": "なる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "作用 —— 一事物对另一事物产生的影响或效果，也指功能与活动",
        "整体",
        "位置や程度が、高い状態から低い状態に変わること。",
        "物事や状態が変化して、ある結果・状態になる。"
      ],
      "correct_answer": "物事や状態が変化して、ある結果・状態になる。"
    }
  }
}
```

---

## sense 35033, level 4

#### Pack A
### Level 4 (sense 35033, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "なり",
  "answer": {
    "accepted": [
      "なれる"
    ],
    "accepted_normalized": [
      "なれる"
    ]
  },
  "input_mode": "ime",
  "target_word": "なれる",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "これからのともだちになれるでしょうか。",
  "sentence_with_blank": "これからのともだちに___でしょうか。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "なって",
    "なった",
    "なれる",
    "なる"
  ],
  "base_form": "なる",
  "form_label": "可能形",
  "explanation": "可能形は疑問文「〜でしょうか」に自然に接続する。",
  "target_word": "なれる",
  "correct_answer": "なれる",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "original_sentence": "これからのともだちになれるでしょうか。",
  "sentence_with_blank": "これからのともだちに___でしょうか。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "なり",
  "answer": {
    "accepted": [
      "なっ"
    ],
    "accepted_normalized": [
      "なっ"
    ]
  },
  "input_mode": "ime",
  "target_word": "なっ",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "この効率的な生産システムは、私たちの食生活を支える基盤となっているのです。",
  "sentence_with_blank": "この効率的な生産システムは、私たちの食生活を支える基盤と___ているのです。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "なっ",
    "なる",
    "なり",
    "なれ"
  ],
  "base_form": "なる",
  "form_label": "て形（〜ている の前）",
  "explanation": "「なっている」は現在の状態を表す標準の活用（て形＋いる）。",
  "target_word": "なっ",
  "correct_answer": "なっ",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "original_sentence": "この効率的な生産システムは、私たちの食生活を支える基盤となっているのです。",
  "sentence_with_blank": "この効率的な生産システムは、私たちの食生活を支える基盤と___ているのです。"
}
```

#### Pack B
### Level 4 (sense 35033, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "これらの手段は、心の豊かさを追求するものになれます。",
  "original_sentence": "これらの手段は、心の豊かさを追求するものになれます。",
  "correct_answer": "なっ",
  "base_form": "なれる",
  "form_label": "連用形",
  "options": [
    "なれない",
    "なって",
    "なる",
    "なっ"
  ],
  "explanation": "「ます」に接続する連用形（音便形）が正解です。",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "target_word": "なっ"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "これらの手段は、心の豊かさを追求するもの___なれます。",
  "original_sentence": "これらの手段は、心の豊かさを追求するものになれます。",
  "options": [
    "に",
    "で",
    "と",
    "を"
  ],
  "correct_answer": "に",
  "target_word": "なっ",
  "error_tags": {
    "を": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。変化の結果を表す助詞「に」が適切です。"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予期しない変化や問題が起きる状態になれます。",
  "original_sentence": "予期しない変化や問題が起きる状態になれます。",
  "correct_answer": "なら",
  "base_form": "なれる",
  "form_label": "ます形（連用形）",
  "options": [
    "なり",
    "なら",
    "なっ",
    "なれ"
  ],
  "explanation": "可能動詞「なれる」の未然形（連用形）であり、文末の助動詞「ます」と接続して丁寧な可能表現を作る",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "target_word": "なら"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予期しない変化や問題が起きる状態___なれます。",
  "original_sentence": "予期しない変化や問題が起きる状態になれます。",
  "options": [
    "と",
    "で",
    "を",
    "に"
  ],
  "correct_answer": "に",
  "target_word": "なら",
  "error_tags": {
    "を": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。変化の結果を表す助詞「に」が適切です。"
    }
  }
}
```

---

## sense 35033, level 9

#### Pack A
### Level 9 (sense 35033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "内部は、光に満ちあふれた空間になれました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "内部は、光に満ちあふれた空間になれました。",
  "chunks": [
    "内部は",
    "光に",
    "満ちあふれた空間に",
    "なれました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "内部は",
    "なれました",
    "光に",
    "満ちあふれた空間に"
  ],
  "target_word": "なり",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "AIがホワイトカラーの雇用を代替する時代になれました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "AIがホワイトカラーの雇用を代替する時代になれました。",
  "chunks": [
    "AIが",
    "ホワイトカラーの",
    "雇用を",
    "代替する時代に",
    "なれました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "なれました",
    "AIが",
    "代替する時代に",
    "ホワイトカラーの",
    "雇用を"
  ],
  "target_word": "なっ",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 35033, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "しかし農薬を使わずに野菜を",
    "育てるという仕事を",
    "通じて彼は自然の厳しさ",
    "と土が命を育むという壮大な仕組みを",
    "自らの肌で実感して",
    "いくことになります"
  ],
  "chunk_count": 6,
  "target_word": "なり",
  "schema_version": 2,
  "shuffled_chunks": [
    "と土が命を育むという壮大な仕組みを",
    "しかし農薬を使わずに野菜を",
    "育てるという仕事を",
    "自らの肌で実感して",
    "いくことになります",
    "通じて彼は自然の厳しさ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "これらにより壁を",
    "薄くして大きな窓を",
    "設けることが",
    "可能となり",
    "内部は光に",
    "満ちあふれました"
  ],
  "chunk_count": 6,
  "target_word": "なり",
  "schema_version": 2,
  "shuffled_chunks": [
    "満ちあふれました",
    "内部は光に",
    "これらにより壁を",
    "可能となり",
    "薄くして大きな窓を",
    "設けることが"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。"
}
```

---
