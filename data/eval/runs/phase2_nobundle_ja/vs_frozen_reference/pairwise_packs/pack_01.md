# Pairwise review pack 01

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


## sense 34998, level 1

#### Pack A
### Level 1 (sense 34998, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "一",
  "prompt": "一",
  "options": [
    "いぢ",
    "いち",
    "いいち",
    "いちい"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "いち",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "/it͡ɕi/",
  "word": "一",
  "options": [
    "遺事",
    "入",
    "書痴",
    "一"
  ],
  "audio_url": null,
  "explanation": "正解です。「一」は「数の中で最も小さい、1という数を表す語。」という意味です。",
  "pronunciation": "いち",
  "correct_answer": "一",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "入": "「入」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「り」、一部の音の違い）。",
    "書痴": "「書痴」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「しょ」、一部の音の違い）。",
    "遺事": "「遺事」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「じ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "一",
  "prompt": "いち",
  "options": [
    "今",
    "4",
    "一",
    "位置"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "一",
  "schema_version": 2,
  "distractor_sources": {
    "4": "frequency",
    "今": "frequency",
    "位置": "homophone"
  }
}
```

#### Pack B
### Level 1 (sense 34998, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "一",
  "options": [
    "いぢ",
    "いち",
    "いいち",
    "いちい"
  ],
  "correct_answer": "いち",
  "word": "一",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "ipa": "/itɕi/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "位次",
    "依估",
    "一",
    "殷"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "殷": "「殷」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「ん」、撥音「ん」の有無）。",
    "依估": "「依估」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「こ」、一部の音の違い）。",
    "位次": "「位次」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「じ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "いち",
  "options": [
    "方",
    "4",
    "一",
    "位置"
  ],
  "correct_answer": "一",
  "word": "一",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "位置": "homophone",
    "4": "frequency",
    "方": "frequency"
  }
}
```

---

## sense 34998, level 2

#### Pack A
### Level 2 (sense 34998, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "options": [
    "レモン果汁に水と砂糖を加えて作った、すっぱくてさわやかな飲み物。",
    "人と人の関係が近く、心が通じ合っている様子。仲が良い。",
    "数の中で最も小さい、1という数を表す語。",
    "空気中などに存在する微生物のうち、特に衛生上問題となるものを指す。食べ物を腐らせたり、病気の原因になることがある。"
  ],
  "pronunciation": "いち",
  "correct_definition": "数の中で最も小さい、1という数を表す語。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "自分の能力や才能を発揮して、社会や集団の中で積極的に活動すること。",
        "数の中で最も小さい、1という数を表す語。",
        "studio",
        "curve"
      ],
      "correct_answer": "数の中で最も小さい、1という数を表す語。"
    }
  },
  "tier": "T3",
  "word": "一",
  "pronunciation": "いち",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 34998, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "correct_definition": "ひとつだけの数。",
  "options": [
    "水や液体が満ちてあふれそうになること。また、感情や力などが満ちあふれること。",
    "文字を読み書きする基本的な能力。また、専門的な知識や情報を正確に理解し、適切に処理・活用する能力を指します。",
    "一つのみで、他にないこと。",
    "ひとつだけの数。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ひとつだけの数。",
        "an occurrence",
        "洗衣 —— 用水和洗涤剂把衣物或布制品的污渍洗掉，使其干净",
        "blessing"
      ],
      "correct_answer": "ひとつだけの数。"
    }
  }
}
```

---

## sense 34998, level 3

#### Pack A
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___は数字の始まりです。",
  "original_sentence": "一は数字の始まりです。",
  "correct_answer": "一",
  "options": [
    "百",
    "一",
    "十",
    "二"
  ],
  "explanation": "文脈に合う正しい数字。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___列に並んでください。",
  "original_sentence": "一列に並んでください。",
  "correct_answer": "一",
  "options": [
    "無",
    "三",
    "一",
    "二"
  ],
  "explanation": "文脈に合う正しい数字。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

#### Pack B
### Level 3 (sense 34998, difficulty 5)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "options": [
    "百",
    "一",
    "二",
    "十"
  ],
  "explanation": "文脈に合う正しい数字。",
  "target_word": "一",
  "correct_answer": "一",
  "distractor_tags": {},
  "word_definition": "数の中で最も小さい、1という数を表す語。",
  "original_sentence": "一に一を足すと二になる。",
  "sentence_with_blank": "___に一を足すと二になる。"
}
```

---

## sense 34998, level 4

#### Pack A
### Level 4 (sense 34998, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
    ]
  },
  "input_mode": "ime",
  "target_word": "一",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼は一から十まで数えた。",
  "sentence_with_blank": "彼は___から十まで数えた。"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "起点を表す格助詞「から」が「十まで」との呼応で自然な範囲の始点を示す"
    }
  },
  "options": [
    "で",
    "を",
    "から",
    "に"
  ],
  "error_tags": {
    "で": "source_vs_goal",
    "に": "source_vs_goal",
    "を": "source_vs_goal"
  },
  "target_word": "一",
  "correct_answer": "から",
  "schema_version": 2,
  "original_sentence": "彼は一から十まで数えた。",
  "sentence_with_blank": "彼は一___十まで数えた。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
    ]
  },
  "input_mode": "ime",
  "target_word": "一",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "一は最も小さい自然数だ。",
  "sentence_with_blank": "___は最も小さい自然数だ。"
}
```

#### Pack B
### Level 4 (sense 34998, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "私は___ページだけ読んだ。",
  "original_sentence": "私は一ページだけ読んだ。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "一つ",
      "一番",
      "一度"
    ],
    "accepted_normalized": [
      "一",
      "一つ",
      "一番",
      "一度"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___歩ずつ進みましょう。",
  "original_sentence": "一歩ずつ進みましょう。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "一つ",
      "一番",
      "一度"
    ],
    "accepted_normalized": [
      "一",
      "一つ",
      "一番",
      "一度"
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
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "一___数字の始まりです。",
  "original_sentence": "一は数字の始まりです。",
  "options": [
    "を",
    "が",
    "は",
    "に"
  ],
  "correct_answer": "は",
  "target_word": "一",
  "error_tags": {
    "が": "topic_vs_subject",
    "を": "object_marking",
    "に": "location_vs_target"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "主題を示す係助詞であり、文のテーマとして「一」を提示する"
    }
  }
}
```

---

## sense 34998, level 6

#### Pack A
### Level 6 (sense 34998, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一という数字を漢字で書く。",
      "is_correct": true
    },
    {
      "text": "一が空を飛ぶ。",
      "is_correct": false
    },
    {
      "text": "一を食べました。",
      "is_correct": false
    },
    {
      "text": "一が笑っている。",
      "is_correct": false
    }
  ],
  "explanation": "数字が笑うことはない。 数字は食べる対象にならない。 数字が空を飛ぶことはない。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一を二倍すると二になる。",
      "is_correct": true
    },
    {
      "text": "一を洗った。",
      "is_correct": false
    },
    {
      "text": "一は幸せそうだ。",
      "is_correct": false
    },
    {
      "text": "一が走ってきた。",
      "is_correct": false
    }
  ],
  "explanation": "数字が感情を持つことはない。 数字は洗う対象にならない。 数字が走ることはない。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一が笑っている。",
      "is_correct": false
    },
    {
      "text": "一が空を飛ぶ。",
      "is_correct": false
    },
    {
      "text": "彼は一等賞を取りました。",
      "is_correct": true
    },
    {
      "text": "一を食べました。",
      "is_correct": false
    }
  ],
  "explanation": "数字が笑うことはない。 数字は食べる対象にならない。 数字が空を飛ぶことはない。",
  "target_word": "一"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "複数",
    "最大",
    "全体",
    "平均"
  ],
  "correct_answer": "複数",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "「一つ」の対義語であり、二つ以上であることを表す"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一は幸せそうだ。",
      "is_correct": false
    },
    {
      "text": "一昨日会いましたか。",
      "is_correct": true
    },
    {
      "text": "一が走ってきた。",
      "is_correct": false
    },
    {
      "text": "一を洗った。",
      "is_correct": false
    }
  ],
  "explanation": "数字が感情を持つことはない。 数字は洗う対象にならない。 数字が走ることはない。",
  "target_word": "一"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "単",
    "全",
    "始",
    "多"
  ],
  "correct_answer": "多",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "「一（ひとつ）」という少数・単数の概念に対し、数が多くあることを表す対義語です。"
    }
  }
}
```

---

## sense 34998, level 7

#### Pack A
### Level 7 (sense 34998, difficulty 5)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一に一が足すと二になる。",
      "is_correct": false,
      "error_description": "動作の対象を表す「を」を使うべきところを「が」にしている誤り。"
    },
    {
      "text": "彼は一から十まで数えた。",
      "is_correct": true
    },
    {
      "text": "一に一を足すと二になる。",
      "is_correct": true
    },
    {
      "text": "サイコロで一が出た。",
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
      "text": "一を英語でワンに言う。",
      "is_correct": false,
      "error_description": "言い換えを表す「と」を使うべきところを「に」にしている誤り。"
    },
    {
      "text": "この問題の答えは一だ。",
      "is_correct": true
    },
    {
      "text": "一を二倍すると二になる。",
      "is_correct": true
    },
    {
      "text": "一は最も小さい自然数だ。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 34998, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一は数字の始まりです。",
      "is_correct": true
    },
    {
      "text": "一の位はここにあります。",
      "is_correct": true
    },
    {
      "text": "私は一ページだけ読んだ。",
      "is_correct": true
    },
    {
      "text": "一に一が足すと二になる。",
      "is_correct": false,
      "error_description": "動作の対象を表す「を」を使うべきところを「が」にしている誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一歩ずつ進みましょう。",
      "is_correct": true
    },
    {
      "text": "一昨日会いましたか。",
      "is_correct": true
    },
    {
      "text": "一を英語でワンに言う。",
      "is_correct": false,
      "error_description": "言い換えを表す「と」を使うべきところを「に」にしている誤り。"
    },
    {
      "text": "一列に並んでください。",
      "is_correct": true
    }
  ]
}
```

---

## sense 34998, level 9

#### Pack A
### Level 9 (sense 34998, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "一の位を先に計算する。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "一の",
    "位を",
    "先に",
    "計算する"
  ],
  "chunk_count": 4,
  "target_word": "一",
  "schema_version": 2,
  "shuffled_chunks": [
    "一の",
    "先に",
    "位を",
    "計算する"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "一の位を先に計算する。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "一と",
    "いう数字を",
    "漢字で",
    "書く"
  ],
  "chunk_count": 4,
  "target_word": "一",
  "schema_version": 2,
  "shuffled_chunks": [
    "漢字で",
    "書く",
    "一と",
    "いう数字を"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "一という数字を漢字で書く。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "一という数字を漢字で書く。"
}
```

#### Pack B
### Level 9 (sense 34998, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "一時間待ってください。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は一等賞を取りました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は一等賞を取りました。",
  "chunks": [
    "彼は",
    "一等賞を",
    "取りました"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "一等賞を",
    "取りました",
    "彼は"
  ],
  "target_word": "一",
  "chunk_count": 3
}
```

---

## sense 35311, level 1

#### Pack A
### Level 1 (sense 35311, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "かのう",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "kanoː",
  "word": "可能",
  "options": [
    "下葉",
    "過少",
    "川鵜",
    "可能"
  ],
  "audio_url": null,
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "pronunciation": "かのう",
  "correct_answer": "可能",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "下葉": "「下葉」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「よ」、一部の音の違い）。",
    "川鵜": "「川鵜」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「わ」、一部の音の違い）。",
    "過少": "「過少」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「しょ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "可能",
  "schema_version": 2,
  "distractor_sources": {
    "機能": "component",
    "知能": "component",
    "能力": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35311, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "correct_answer": "かのう",
  "word": "可能",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "correct_answer": "可能",
  "word": "可能",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機能": "component",
    "能力": "component",
    "知能": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T4`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "kanoː",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "河道",
    "可能",
    "か流",
    "嘉賞"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "河道": "「河道」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ど」、一部の音の違い）。",
    "嘉賞": "「嘉賞」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「しょ」、一部の音の違い）。",
    "か流": "「か流」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「りゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35311, level 2

#### Pack A
### Level 2 (sense 35311, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "breathing — the process by which a living thing draws air into the body and lets it out again",
        "物事を行うことができる性質や状態。",
        "换句话说",
        "prosperity"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  },
  "tier": "T6",
  "word": "可能",
  "pronunciation": "かのう",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "options": [
    "物事のはずれやまちがいがなく、ぴったりあっているさま。",
    "火をつけて燃やすことで熱やエネルギーを生み出す物質。車や飛行機を動かすためのガソリンや軽油、灯油などの総称。",
    "物事を行うことができる性質や状態。",
    "生物の体を構成する最小の単位。植物や動物の体は多くの細胞からできている。"
  ],
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。"
}
```

#### Pack B
### Level 2 (sense 35311, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。",
  "options": [
    "物事を行うことができる性質や状態。",
    "他の人や国などから提供されたものを受け取ること。",
    "契約や約束などの内容を実際に行うこと。",
    "年齢が低い、まだ成長途中の人間。特に、親に養われる年齢の者。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物事を行うことができる性質や状態。",
        "permanent",
        "specific; particular — a clear feature or condition that sets something apart from others",
        "ものや体が、長い間こわれずに使えること。"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  }
}
```

---

## sense 35311, level 3

#### Pack A
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "近年、精密農業の導入が小規模農家の経営に新たな___性をもたらしています。",
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
  "correct_answer": "可能",
  "options": [
    "必要",
    "簡単",
    "重要",
    "可能"
  ],
  "explanation": "「可能となり」は実現できる性質を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "明日なら参加が___です。",
  "original_sentence": "明日なら参加が可能です。",
  "correct_answer": "可能",
  "options": [
    "可能",
    "必要",
    "簡単",
    "重要"
  ],
  "explanation": "「可能に見える」は実現できる性質を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 3 (sense 35311, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "可能",
    "重要",
    "簡単",
    "必要"
  ],
  "explanation": "「可能となり」は実現できる性質を表す固定表現。",
  "target_word": "可能",
  "correct_answer": "可能",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
  "sentence_with_blank": "これらにより、壁を薄くして大きな窓を設けることが___となり、内部は光に満ちあふれました。"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "options": [
    "簡単",
    "必要",
    "重要",
    "可能"
  ],
  "explanation": "「可能に見える」は実現できる性質を表す固定表現。",
  "target_word": "可能",
  "correct_answer": "可能",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "参加は可能ですか。",
  "sentence_with_blank": "参加は___ですか。"
}
```

---
