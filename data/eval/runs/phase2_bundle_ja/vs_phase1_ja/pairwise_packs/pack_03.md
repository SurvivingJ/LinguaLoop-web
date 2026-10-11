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


## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "最近、ゴミの量が___ています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
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
**cloze_typed** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "雨が降って水が___ました。",
  "original_sentence": "雨が降って水が増えました。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えています"
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
### Level 9 (sense 35017, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "増えたゴミを自分で減らします。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "増えたゴミを自分で減らします。",
  "chunks": [
    "増えたゴミを",
    "自分で",
    "減らします"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "減らします",
    "自分で",
    "増えたゴミを"
  ],
  "target_word": "増え",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "最近、この町の人口が増えています。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "最近、この町の人口が増えています。",
  "chunks": [
    "最近",
    "この町の",
    "人口が",
    "増えて",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "います",
    "人口が",
    "最近",
    "この町の",
    "増えて"
  ],
  "target_word": "増え",
  "chunk_count": 5
}
```

---

## sense 35033, level 1

#### Pack A
### Level 1 (sense 35033, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "成る",
  "pronunciation": "なる",
  "ipa": "naɾɯ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "成る",
    "洩る",
    "選る",
    "居る"
  ],
  "correct_answer": "成る",
  "explanation": "正解です。「成る」は「物事や状態が変化して、ある結果・状態になる。」という意味です。",
  "distractor_explanations": {
    "居る": "「居る」は「成る」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「お」、一部の音の違い）。",
    "洩る": "「洩る」は「成る」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「も」、一部の音の違い）。",
    "選る": "「選る」は「成る」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「え」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
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
### Level 2 (sense 35033, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "なれる",
  "pronunciation": "なる",
  "correct_definition": "物事や状態が変化して、ある結果・状態になる。",
  "options": [
    "物事の状態や、行動のありさま。",
    "木の葉のすきまから太陽の光が差し込むこと。または、その光。",
    "攻撃や危険から守ること。また、そのための手段や行為。",
    "物事や状態が変化して、ある結果・状態になる。"
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
        "recycling",
        "「本来」は、あるものが初めからそうであること、または当然そうあるべき状態を表す語です。",
        "尺寸（大小）",
        "物事や状態が変化して、ある結果・状態になる。"
      ],
      "correct_answer": "物事や状態が変化して、ある結果・状態になる。"
    }
  }
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
### Level 4 (sense 35033, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "これらは視覚的な雑音を減らし、理想の自分になれるよう心の豊かさを追求する手段と___ています。",
  "original_sentence": "これらは視覚的な雑音を減らし、理想の自分になれるよう心の豊かさを追求する手段となっています。",
  "target_word": "なっ",
  "word": "なれる",
  "answer": {
    "accepted": [
      "なっ"
    ],
    "accepted_normalized": [
      "なっ"
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
  "sentence_with_blank": "これらは視覚的な雑音を減らし、理想の自分になれるよう心の豊かさを追求する手段と___ています。",
  "original_sentence": "これらは視覚的な雑音を減らし、理想の自分になれるよう心の豊かさを追求する手段となっています。",
  "correct_answer": "なれる",
  "base_form": "なる",
  "form_label": "可能形",
  "options": [
    "なる",
    "なった",
    "なれる",
    "なって"
  ],
  "explanation": "可能形は疑問文「〜でしょうか」に自然に接続する。",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "target_word": "なっ"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "これらは視覚的な雑音を減らし、理想の自分___なれるよう心の豊かさを追求する手段となっています。",
  "original_sentence": "これらは視覚的な雑音を減らし、理想の自分になれるよう心の豊かさを追求する手段となっています。",
  "options": [
    "へ",
    "に",
    "で",
    "が"
  ],
  "correct_answer": "に",
  "target_word": "なっ",
  "error_tags": {
    "が": "topic_vs_subject",
    "へ": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "動詞「なる」が表す変化の結果や到達点を示す"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "人生においては多くの困難や挫折がありますが、それらに立ち向かいながら経験を積むことで、やがては誰もが望むような立派な大人になれるはずです。",
  "original_sentence": "人生においては多くの困難や挫折がありますが、それらに立ち向かいながら経験を積むことで、やがては誰もが望むような立派な大人になれるはずです。",
  "correct_answer": "なっ",
  "base_form": "なる",
  "form_label": "て形（〜ている の前）",
  "options": [
    "なっ",
    "なり",
    "なる",
    "なれ"
  ],
  "explanation": "「なっている」は現在の状態を表す標準の活用（て形＋いる）。",
  "word_definition": "物事や状態が変化して、ある結果・状態になる。",
  "target_word": "なら"
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

## sense 35033, level 6

#### Pack A
### Level 6 (sense 35033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "AIがホワイトカラーの雇用を代替する時代がなれました。",
      "is_correct": false
    },
    {
      "text": "AIがホワイトカラーの雇用を代替する時代になれました。",
      "is_correct": true
    },
    {
      "text": "AIがホワイトカラーの雇用を代替する時代をなれました。",
      "is_correct": false
    },
    {
      "text": "AIがホワイトカラーの雇用を代替する時代となれました。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。変化の結果には助詞「に」を使うべきで、「を」は不適切です。 誤答。主語が「時代」自身になってしまうため、文脈として不自然です。 誤答。変化の結果を表す場合は「に」が標準的であり、「と」は引用や同定の意味になりがちです。",
  "target_word": "なっ"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "なれる",
  "relation": "synonym",
  "options": [
    "作る",
    "保つ",
    "止まる",
    "変化する"
  ],
  "correct_answer": "変化する",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事や状態が変化して、ある結果・状態になる。",
      "explanation": "類義語。状態が変わって別のものになるという意味で近いです。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "このシステムは、私たちの食生活を支える基盤がなれます。",
      "is_correct": false
    },
    {
      "text": "このシステムは、私たちの食生活を支える基盤になれます。",
      "is_correct": true
    },
    {
      "text": "このシステムは、私たちの食生活を支える基盤となれます。",
      "is_correct": false
    },
    {
      "text": "このシステムは、私たちの食生活を支える基盤をなれます。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。変化の結果には助詞「に」を使うべきで、「を」は不適切です。 誤答。主語が「基盤」自身になってしまうため、文脈として不自然です。 誤答。変化の結果を表す場合は「に」が標準的であり、「と」は引用や同定の意味になりがちです。",
  "target_word": "なっ"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "なれる",
  "relation": "synonym",
  "options": [
    "作る",
    "止まる",
    "変化する",
    "保つ"
  ],
  "correct_answer": "変化する",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事や状態が変化して、ある結果・状態になる。",
      "explanation": "類義語。状態が変わって別のものになるという意味で近いです。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用を代替する時代へなれるかどうか、議論されている。",
      "is_correct": false
    },
    {
      "text": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用をなれる時代を代替するかどうか、議論されている。",
      "is_correct": false
    },
    {
      "text": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用を代替する時代になれるかどうか、議論されている。",
      "is_correct": true
    },
    {
      "text": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用を代替する時代になれているかどうか、議論されている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「なる」の到達点・結果を示す助詞は「に」であり、「へ」は不自然です。 活用・アスペクトの誤り：「なれている」は状態の継続を表しますが、ここでは可能性についての議論であるため、可能態の「なれる」が適切です。 語順・係り受けの誤り：「なれる」の位置が誤っており、「雇用をなれる時代」という不自然な係り受けになっています。「時代になれる」が正しい語順です。",
  "target_word": "なっ"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この効率的な生産システムは、私たちの食生活を支える基盤となり、誰もが安心して食を楽しめる生活になれるよう支えています。",
      "is_correct": true
    },
    {
      "text": "この効率的な生産システムは、私たちの食生活を支える基盤となり、誰もが安心して食を楽しめる生活になれたよう支えています。",
      "is_correct": false
    },
    {
      "text": "この効率的な生産システムは、私たちの食生活を支える基盤となり、生活になれるよう誰もが安心して食を楽しめる支えています。",
      "is_correct": false
    },
    {
      "text": "この効率的な生産システムは、私たちの食生活を支える基盤となり、誰もが安心して食を楽しめる生活でなれるよう支えています。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同。「なる」は到達する目標状態を示す際に格助詞「に」を取ります。「で」は手段や場所を表すため、ここでは不適切です。 活用・アスペクトの誤り。「なれた」は過去・完了の助動詞「た」が付いた形ですが、「～よう」と接続する場合は可能態や意志を表す「なれる」が適切です。 語順・係り受けの誤り。「生活になれるよう」の後に「誰もが安心して食を楽しめる」が置かれたため、「食を楽しめる」が「支えています」を修飾する形になり、文の係り受けが破壊されています。",
  "target_word": "なっ"
}
```

---

## sense 35033, level 9

#### Pack A
### Level 9 (sense 35033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、誰もが心地よく過ごせる空間になれるよう設計されました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、誰もが心地よく過ごせる空間になれるよう設計されました。",
  "chunks": [
    "これらにより壁を",
    "薄くして大きな窓を",
    "設けることが",
    "可能となり誰もが",
    "心地よく過ごせる空間に",
    "なれるよう設計されました"
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
    "可能となり誰もが",
    "これらにより壁を",
    "薄くして大きな窓を",
    "心地よく過ごせる空間に",
    "なれるよう設計されました",
    "設けることが"
  ],
  "target_word": "なり",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用を代替する時代になれるかどうか、議論されている。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "現在、オフィスでの定型業務の自動化が進み、AIがホワイトカラーの雇用を代替する時代になれるかどうか、議論されている。",
  "chunks": [
    "現在オフィスでの",
    "定型業務の自動化が",
    "進みAIがホワイトカラーの",
    "雇用を代替する時代に",
    "なれるかどうか",
    "議論されている"
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
    "議論されている",
    "なれるかどうか",
    "現在オフィスでの",
    "雇用を代替する時代に",
    "定型業務の自動化が",
    "進みAIがホワイトカラーの"
  ],
  "target_word": "なっ",
  "chunk_count": 6
}
```

#### Pack B
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

---

## sense 35055, level 1

#### Pack A
### Level 1 (sense 35055, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "世界",
  "options": [
    "せいかい",
    "せがい",
    "せかい",
    "ぜかい"
  ],
  "correct_answer": "せかい",
  "word": "世界",
  "direction": "kanji_to_reading"
}
```
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
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "せかい",
  "options": [
    "世界",
    "限界",
    "境界",
    "大量"
  ],
  "correct_answer": "世界",
  "word": "世界",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "限界": "component",
    "境界": "component",
    "大量": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35055, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "世界",
  "options": [
    "せいかい",
    "せがい",
    "せかい",
    "ぜかい"
  ],
  "correct_answer": "せかい",
  "word": "世界",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "せかい",
  "options": [
    "世界",
    "限界",
    "境界",
    "大量"
  ],
  "correct_answer": "世界",
  "word": "世界",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "限界": "component",
    "境界": "component",
    "大量": "component"
  }
}
```

---

## sense 35055, level 2

#### Pack A
### Level 2 (sense 35055, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "correct_definition": "地球全体や、社会全体のこと。",
  "options": [
    "地球全体や、社会全体のこと。",
    "農作物を育てるために、田や畑に水を供給すること。特に、人工的に水を引いて土地を潤すこと。",
    "生分解性プラスチックの一種で、トウモロコシなどから作られるポリ乳酸の略称。",
    "色の名前で、空や海の色を表す形容詞。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "豆",
        "神聖は、とても大事で、だれも壊してはいけないことです。",
        "主轴（核心）",
        "地球全体や、社会全体のこと。"
      ],
      "correct_answer": "地球全体や、社会全体のこと。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35055, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "correct_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "options": [
    "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
    "二つのものが順番に現れたり、置かれたりすること。",
    "他の人のやり方や考え方、行動などをまねて、同じようにすること。",
    "ある目的のために、体や道具を使って物事を行うこと。特に、仕事や活動として取り組むこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "吃（了）—— 表示吃这个动作的持续、并列或理由等的连接形式",
        "结果实（结实）",
        "dependence; to depend on — not being able to function fully alone, relying on something else",
        "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
      ],
      "correct_answer": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
    }
  }
}
```

---

## sense 35055, level 3

#### Pack A
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼は___を旅して回りました。",
  "original_sentence": "彼は世界を旅して回りました。",
  "correct_answer": "世界",
  "options": [
    "環境",
    "宇宙",
    "世界",
    "地域"
  ],
  "explanation": "文脈に適合：地球全体や社会全体を指す。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "インターネットで___のニュースを見ます。",
  "original_sentence": "インターネットで世界のニュースを見ます。",
  "correct_answer": "世界",
  "options": [
    "天気",
    "世界",
    "机",
    "部屋"
  ],
  "explanation": "文脈に適合：多くの人々、グローバルな範囲を指す。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```

#### Pack B
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

---
