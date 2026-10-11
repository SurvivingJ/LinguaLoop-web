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


## sense 34999, level 1

#### Pack A
### Level 1 (sense 34999, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "一",
  "options": [
    "いち",
    "いいち",
    "いちい",
    "いぢ"
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
  "ipa": "/iti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "無知",
    "一",
    "貴地",
    "逝く"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「数や順番の最初。一つだけ。」という意味です。",
  "distractor_explanations": {
    "貴地": "「貴地」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「き」、一部の音の違い）。",
    "逝く": "「逝く」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「く」、一部の音の違い）。",
    "無知": "「無知」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「む」、一部の音の違い）。"
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
    "位置",
    "方",
    "4",
    "一"
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

#### Pack B
### Level 1 (sense 34999, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "一",
  "options": [
    "いち",
    "いいち",
    "いちい",
    "いぢ"
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
  "ipa": "itɕi",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "四",
    "三",
    "一",
    "二"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「数や順番の最初。一つだけ。」という意味です。",
  "distractor_explanations": {
    "二": "",
    "三": "",
    "四": ""
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
    "位置",
    "方",
    "4",
    "一"
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

## sense 34999, level 2

#### Pack A
### Level 2 (sense 34999, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "correct_definition": "数や順番の最初。一つだけ。",
  "options": [
    "数や順番の最初。一つだけ。",
    "小さくて丸い形をしたもの。また、そのような形をした一つ一つのもの。",
    "電気を動力に変えて回転や直線運動を生み出す装置。モーターは家電製品や機械に広く使われている。",
    "都市以外の、農業を主な産業とする地域。田舎。"
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
        "数や順番の最初。一つだけ。",
        "灌溉 —— 为了培育农作物，人工向土地供水",
        "terroir; the land's climate and soil that shape a wine's character",
        "実際に自分が経験すること。また、その経験によって得られた知識や感じ方。"
      ],
      "correct_answer": "数や順番の最初。一つだけ。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 34999, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "correct_definition": "数や順番の最初。一つだけ。",
  "options": [
    "ある場所や状態の中に、使い切らずにまだある。",
    "数や順番の最初。一つだけ。",
    "物が中心の軸をぐるぐる回ること。また、回すこと。頭をしっかり働かせることのたとえ。",
    "羊の毛を除いた皮。なめして紙や布などの材料に使う。"
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
        "数や順番の最初。一つだけ。",
        "户外",
        "本当にあったことや本当にあることを、実際のものにすること。",
        "擅长 —— 做某事的技术或能力很出色"
      ],
      "correct_answer": "数や順番の最初。一つだけ。"
    }
  }
}
```

---

## sense 34999, level 4

#### Pack A
### Level 4 (sense 34999, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "その___連の動作が、彼女の認知能力と社会性を育む養分となる。",
  "original_sentence": "その一連の動作が、彼女の認知能力と社会性を育む養分となる。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "個",
      "回",
      "番",
      "つ"
    ],
    "accepted_normalized": [
      "一",
      "個",
      "回",
      "番",
      "つ"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "その一連の動作___、彼女の認知能力と社会性を育む養分となる。",
  "original_sentence": "その一連の動作が、彼女の認知能力と社会性を育む養分となる。",
  "options": [
    "で",
    "を",
    "に",
    "が"
  ],
  "correct_answer": "が",
  "target_word": "一",
  "error_tags": {
    "を": "case_error",
    "に": "case_error",
    "で": "case_error"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "主語を示す格助詞として自然です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___人で行くのは少し心配です。",
  "original_sentence": "一人で行くのは少し心配です。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "個",
      "回",
      "番",
      "つ"
    ],
    "accepted_normalized": [
      "一",
      "個",
      "回",
      "番",
      "つ"
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

#### Pack B
### Level 4 (sense 34999, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "その___つひとつの動作が、彼女の認知能力と社会性を育む養分となります。",
  "original_sentence": "その一つひとつの動作が、彼女の認知能力と社会性を育む養分となります。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
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
  "sentence_with_blank": "___つずつ順番に並んでいます。",
  "original_sentence": "一つずつ順番に並んでいます。",
  "target_word": "一",
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
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

---

## sense 34999, level 6

#### Pack A
### Level 6 (sense 34999, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は一冊の意見を持っています。",
      "is_correct": false
    },
    {
      "text": "私は一つに意見を持っています。",
      "is_correct": false
    },
    {
      "text": "一つ私はの意見を持っています。",
      "is_correct": false
    },
    {
      "text": "私は一つの意見を持っています。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「意見」に使う助数詞は「冊」ではなく「つ」や「個」です。「一つの」が正しいです。 助詞の混同：所有や付帯状況を表す場合は「に」ではなく「の」を使います。「一つの意見」が正しいです。 語順・係り受けの誤り：連体修飾語「一つの」は被修飾語「意見」の直前に置く必要があります。語順が誤っています。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一まで十から覚えてきました。",
      "is_correct": false
    },
    {
      "text": "一から十までが覚えてきました。",
      "is_correct": false
    },
    {
      "text": "一から十まで覚えてあります。",
      "is_correct": false
    },
    {
      "text": "一から十まで覚えてきました。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：「一から十まで」は範囲を表す副詞的用法であり、主格助詞「が」は不適切です。 語順・係り受けの誤り：「一から十まで」は固定した語順の慣用表現であり、入れ替えると意味が破綻します。 活用・アスペクトの誤り：「てある」は他動詞の結果の残存を表すため、経験を表すこの文脈では「てきた」が適切です。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34999, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は毎日一時間勉強していますか。",
      "is_correct": false
    },
    {
      "text": "私は毎日一時間勉強しているます。",
      "is_correct": false
    },
    {
      "text": "私は毎日一時間勉強しています。",
      "is_correct": true
    },
    {
      "text": "私一毎日一時間勉強しています。",
      "is_correct": false
    }
  ],
  "explanation": "平叙文であるべき文を疑問形にしており、文脈的に不自然な統語誤りです。 動詞の活用（ています）が誤っており、文法的に不正です。 主語と副詞の間に助詞がなく、文法的に接続が誤っています。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私たちは一つの目標を持っているです。",
      "is_correct": false
    },
    {
      "text": "私たち一つ目標を持っています。",
      "is_correct": false
    },
    {
      "text": "私たちは一つの目標を持っていますか。",
      "is_correct": false
    },
    {
      "text": "私たちは一つの目標を持っています。",
      "is_correct": true
    }
  ],
  "explanation": "平叙文であるべき文を疑問形にしており、文脈的に不自然な統語誤りです。 数量詞と名詞の間に助詞「の」または適切な接続がなく、不自然です。 丁寧語の構成（持っています）が誤っており、文法的に不正です。",
  "target_word": "一"
}
```

---

## sense 34999, level 7

#### Pack A
### Level 7 (sense 34999, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "親である私にできるのは、その勇気ある第一歩を、ただ静かに、そして確かな祈りを込めて見守ることだけです。",
      "is_correct": true
    },
    {
      "text": "その一つひとつの動作が、彼女の認知能力と社会性を育む養分となります。",
      "is_correct": true
    },
    {
      "text": "この絵画は、一から丁寧に描き上げました。",
      "is_correct": true
    },
    {
      "text": "この絵画は、一を丁寧に描き上げました。",
      "is_correct": false,
      "error_description": "助詞の混同。「一から」は「何もない状態から」という意味の慣用表現であり、「一を」とは言いません。正しくは「一から」となります。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一つずつ順番に並んでいます。",
      "is_correct": true
    },
    {
      "text": "一から十まで覚えてきました。",
      "is_correct": true
    },
    {
      "text": "一つの目標に向かって頑張っています。",
      "is_correct": true
    },
    {
      "text": "一つの目標は向かって頑張っています。",
      "is_correct": false,
      "error_description": "助詞の混同。「目標」は「向かう」の方向・対象を表すため、助詞「は」ではなく「に」または「へ」を使うのが正しいです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 34999, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "昨日は一匹の猫を見つけました。",
      "is_correct": true
    },
    {
      "text": "昨日は一匹猫を見つけました。",
      "is_correct": false,
      "error_description": "数量詞が名詞を修飾する場合、通常助詞「の」が必要です（または直結も可能ですが、学習レベルT3では「の」のある形を正解とし、欠落を誤りとします）。"
    }
  ]
}
```

---

## sense 34999, level 9

#### Pack A
### Level 9 (sense 34999, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "一人の友達が手伝ってくれました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "一人の友達が手伝ってくれました。",
  "chunks": [
    "一人の",
    "友達が",
    "手伝って",
    "くれました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "友達が",
    "手伝って",
    "くれました",
    "一人の"
  ],
  "target_word": "一",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "私は一つの意見を持っています。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "私は一つの意見を持っています。",
  "chunks": [
    "私は",
    "一つの",
    "意見を",
    "持って",
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
    "意見を",
    "一つの",
    "持って",
    "います",
    "私は"
  ],
  "target_word": "一",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 34999, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼はクラスで一番背が高いです。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼はクラスで一番背が高いです。",
  "chunks": [
    "彼は",
    "クラスで",
    "一番背が",
    "高いです"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "クラスで",
    "一番背が",
    "高いです",
    "彼は"
  ],
  "target_word": "一",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "私は毎日一時間勉強しています。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "私は毎日一時間勉強しています。",
  "chunks": [
    "私は",
    "毎日一時間勉強して",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "毎日一時間勉強して",
    "います",
    "私は"
  ],
  "target_word": "一",
  "chunk_count": 3
}
```

---

## sense 35001, level 1

#### Pack A
### Level 1 (sense 35001, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "機械",
  "options": [
    "きいかい",
    "きかい",
    "ぎかい",
    "きがい"
  ],
  "correct_answer": "きかい",
  "word": "機械",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "/kikai/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "機械",
    "規程",
    "自壊",
    "嫌い"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「動力や電気で動き、人間の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "嫌い": "「嫌い」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「ら」、一部の音の違い）。",
    "自壊": "「自壊」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「じ」、一部の音の違い）。",
    "規程": "「規程」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「て」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きかい",
  "options": [
    "機能",
    "機会",
    "契機",
    "機械"
  ],
  "correct_answer": "機械",
  "word": "機械",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機会": "homophone",
    "契機": "component",
    "機能": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35001, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "機械",
  "options": [
    "きいかい",
    "きかい",
    "ぎかい",
    "きがい"
  ],
  "correct_answer": "きかい",
  "word": "機械",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きかい",
  "options": [
    "機能",
    "機会",
    "契機",
    "機械"
  ],
  "correct_answer": "機械",
  "word": "機械",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機会": "homophone",
    "契機": "component",
    "機能": "component"
  }
}
```

---

## sense 35001, level 2

#### Pack A
### Level 2 (sense 35001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "correct_definition": "動力や電気で動き、人間の代わりに仕事をする装置。",
  "options": [
    "ある出来事や物事が実現するのを、期待しながら待つこと。",
    "動力や電気で動き、人間の代わりに仕事をする装置。",
    "人から物や情報などを自分の方にいただくこと。",
    "物の一番端の部分。また、行き着く所や相手。例：行き先、受け入れ先。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "比喻；打比方 —— 用别的事物来说明，使内容更容易理解",
        "動力や電気で動き、人間の代わりに仕事をする装置。",
        "色の名前。黒と白をまぜたような色。また、つまらなくて、かわりのないようす。",
        "grassroots"
      ],
      "correct_answer": "動力や電気で動き、人間の代わりに仕事をする装置。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "correct_definition": "動力や電気で動き、人間の代わりに仕事をする装置。",
  "options": [
    "ある場所に定期的に行き来すること。",
    "動力や電気で動き、人間の代わりに仕事をする装置。",
    "牛乳などを原料として作られた食品。チーズやバター、ヨーグルトなど。",
    "「幾」は、数量や程度が不確定であることを表す語で、「いくつかの」「どれほどの」という意味を持ちます。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "雨",
        "動力や電気で動き、人間の代わりに仕事をする装置。",
        "morality",
        "a decade of age; an era — a noun for an age range (like the teens or twenties) or a historical period"
      ],
      "correct_answer": "動力や電気で動き、人間の代わりに仕事をする装置。"
    }
  }
}
```

---

## sense 35001, level 4

#### Pack A
### Level 4 (sense 35001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___が動いています。",
  "original_sentence": "機械が動いています。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "機械式"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "機械式"
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
  "sentence_with_blank": "___の音を聞きました。",
  "original_sentence": "機械の音を聞きました。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "機械式"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "機械式"
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

#### Pack B
### Level 4 (sense 35001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この工場では新しい___を使っています。",
  "original_sentence": "この工場では新しい機械を使っています。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "個",
      "機械化",
      "機械的"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "個",
      "機械化",
      "機械的"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この工場では新しい機械___使っています。",
  "original_sentence": "この工場では新しい機械を使っています。",
  "options": [
    "を",
    "に",
    "で",
    "と"
  ],
  "correct_answer": "を",
  "target_word": "機械",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「使う」の目的語を示す格助詞として適切です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___を修理できる人はいますか。",
  "original_sentence": "機械を修理できる人はいますか。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "個",
      "機械化",
      "機械的"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "個",
      "機械化",
      "機械的"
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
  "sentence_with_blank": "機械___修理できる人はいますか。",
  "original_sentence": "機械を修理できる人はいますか。",
  "options": [
    "に",
    "で",
    "と",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "機械",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「修理できる」の目的語を示す格助詞として適切です。"
    }
  }
}
```

---

## sense 35001, level 6

#### Pack A
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その機械はとても静かあります。",
      "is_correct": false
    },
    {
      "text": "その機械はとても静かです。",
      "is_correct": true
    },
    {
      "text": "その機械はとても静かなです。",
      "is_correct": false
    },
    {
      "text": "その機械はとても静かだ。",
      "is_correct": false
    }
  ],
  "explanation": "文末が「だ」となっており、指定された丁寧語（polite）の文体と一致しません。 形容詞「静かだ」の接続が誤っています。「静かです」が正解です。 形容詞に直接「あります」をつけることはできません。",
  "target_word": "機械"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この機械で紙を切れる。",
      "is_correct": false
    },
    {
      "text": "この機械で紙を切れます。",
      "is_correct": true
    },
    {
      "text": "この機械で紙を切るできます。",
      "is_correct": false
    },
    {
      "text": "この機械で紙を切れられます。",
      "is_correct": false
    }
  ],
  "explanation": "文末が「切れる」となっており、指定された丁寧語（polite）の文体と一致しません。 可能動詞「切れる」にさらに受身・可能の「られる」をつけるのは二重表現で誤りです。 動詞の辞書形に直接「できます」をつけることはできません。",
  "target_word": "機械"
}
```

#### Pack B
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この機械は昨日壊れてある。",
      "is_correct": false
    },
    {
      "text": "工場には新しい機械が三冊導入された。",
      "is_correct": false
    },
    {
      "text": "機械を作る人はすごいです。",
      "is_correct": true
    },
    {
      "text": "機械を人間の代わりに仕事をする。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：機械の助数詞は「台」や「個」であり、本や雑誌などに使う「冊」は誤りです。 助詞の混同：動作の主体である機械を示すには「が」が必要であり、「を」は誤りです。 アスペクトの誤り：「壊れる」は自動詞であり、他動詞の結果状態を表す「てある」は結びつきません。「壊れている」が適切です。",
  "target_word": "機械"
}
```

---
