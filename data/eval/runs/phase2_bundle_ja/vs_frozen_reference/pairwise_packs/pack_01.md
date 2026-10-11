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
### Level 1 (sense 34999, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "一",
  "prompt": "一",
  "options": [
    "いち",
    "いいち",
    "いちい",
    "いぢ"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "いち",
  "schema_version": 2
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "一",
  "prompt": "いち",
  "options": [
    "位置",
    "今",
    "4",
    "一"
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
**phonetic_recognition** variant `B`, tier `T6`
```json
{
  "ipa": "/it͡ɕi/",
  "word": "一",
  "options": [
    "居間",
    "一",
    "フチ",
    "維持"
  ],
  "audio_url": null,
  "explanation": "正解です。「一」は「数や順序で最初であること。また、ひとつだけであること。」という意味です。",
  "pronunciation": "いち",
  "correct_answer": "一",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "フチ": "「フチ」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ふ」、一部の音の違い）。",
    "居間": "「居間」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「ま」、一部の音の違い）。",
    "維持": "「維持」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「じ」、一部の音の違い）。"
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
### Level 2 (sense 34999, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "零；零点；基准起点",
        "数や順序で最初であること。また、ひとつだけであること。",
        "rest (relaxation)",
        "收获 —— 采摘成熟的农作物"
      ],
      "correct_answer": "数や順序で最初であること。また、ひとつだけであること。"
    }
  },
  "tier": "T6",
  "word": "一",
  "pronunciation": "いち",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "一",
  "options": [
    "過去に経験したことや学んだことを、頭の中にしまっておき、あとで思い出せるようにすること。",
    "数や順序で最初であること。また、ひとつだけであること。",
    "特定の立場や意見に偏らず、公平で中立的な状態や性質を表す語。",
    "人が栄養を取るために食べるものの総称。特に、毎日の食事に使われる材料や製品を指すことが多い。"
  ],
  "pronunciation": "いち",
  "correct_definition": "数や順序で最初であること。また、ひとつだけであること。"
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
### Level 4 (sense 34999, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "一つ",
      "一番",
      "第一",
      "一歩"
    ],
    "accepted_normalized": [
      "一",
      "一つ",
      "一番",
      "第一",
      "一歩"
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
  "original_sentence": "その一つひとつの動作が、彼女の認知能力と社会性を育む養分となる。",
  "sentence_with_blank": "その___つひとつの動作が、彼女の認知能力と社会性を育む養分となる。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一",
      "一つ",
      "一番",
      "第一",
      "一歩"
    ],
    "accepted_normalized": [
      "一",
      "一つ",
      "一番",
      "第一",
      "一歩"
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
  "original_sentence": "一歩ずつ前に進んでいく。",
  "sentence_with_blank": "___歩ずつ前に進んでいく。"
}
```

---

## sense 34999, level 6

#### Pack A
### Level 6 (sense 34999, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "一番が泳いでいる。",
      "is_correct": false
    },
    {
      "text": "一番を折った。",
      "is_correct": false
    },
    {
      "text": "一番が笑った。",
      "is_correct": false
    },
    {
      "text": "一番好きな食べ物はカレーだ。",
      "is_correct": true
    }
  ],
  "explanation": "順位が泳ぐことはない。 順位を物理的に折ることはできない。 順位が笑うことはない。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "一からが赤い。",
      "is_correct": false
    },
    {
      "text": "一からが眠っている。",
      "is_correct": false
    },
    {
      "text": "一からを食べた。",
      "is_correct": false
    },
    {
      "text": "一からやり直すことにした。",
      "is_correct": true
    }
  ],
  "explanation": "「一から」というフレーズに色はない。 フレーズを食べることはできない。 フレーズが眠ることはない。",
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
### Level 7 (sense 34999, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "親である私にできるのは、その勇気ある第一歩を、ただ静かに、そして確かな祈りを込めて見守ることだけだ。",
      "is_correct": true
    },
    {
      "text": "こうして、一枚の絵画が完成します。",
      "is_correct": true
    },
    {
      "text": "彼女はクラスに一位になった。",
      "is_correct": false,
      "error_description": "範囲を表す「で」を使うべきところを「に」にしている誤り。"
    },
    {
      "text": "その一つひとつの動作が、彼女の認知能力と社会性を育む養分となる。",
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
      "text": "一からやり直すことにした。",
      "is_correct": true
    },
    {
      "text": "一歩ずつ前に進んでいく。",
      "is_correct": true
    },
    {
      "text": "これが私の一番大切なものだ。",
      "is_correct": true
    },
    {
      "text": "こうして、一枚絵画が完成します。",
      "is_correct": false,
      "error_description": "助数詞と名詞の間には「の」が必要。「一枚絵画」は誤り。"
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
### Level 9 (sense 34999, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "一つだけ",
    "質問が",
    "あります"
  ],
  "chunk_count": 3,
  "target_word": "一",
  "schema_version": 2,
  "shuffled_chunks": [
    "質問が",
    "あります",
    "一つだけ"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "一つだけ質問があります。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "一つだけ質問があります。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "一番好きな食べ物はカレーだ。"
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
### Level 1 (sense 35001, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "機械",
  "prompt": "機械",
  "options": [
    "きいかい",
    "きかい",
    "ぎかい",
    "きがい"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "きかい",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "/kikai/",
  "word": "機械",
  "options": [
    "規格",
    "初回",
    "瓦解",
    "機械"
  ],
  "audio_url": null,
  "explanation": "正解です。「機械」は「動力で動き、人の代わりに働く装置。」という意味です。",
  "pronunciation": "きかい",
  "correct_answer": "機械",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "初回": "「初回」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「しょ」、一部の音の違い）。",
    "瓦解": "「瓦解」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「が」、一部の音の違い）。",
    "規格": "「規格」は「機械」と一モーラだけ異なる実在語です（3モーラ目: 「い」→「く」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "機械",
  "prompt": "きかい",
  "options": [
    "機能",
    "機会",
    "契機",
    "機械"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "機械",
  "schema_version": 2,
  "distractor_sources": {
    "契機": "component",
    "機会": "homophone",
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
### Level 2 (sense 35001, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "機械",
  "options": [
    "数の一つ。百に十をかけた数。",
    "直接言わずに、別の物事にたとえて表現する修辞法。例えば、「人生は旅」のように、似ているところを使って意味を伝える。",
    "動力で動き、人の代わりに働く装置。",
    "人や物が存在する、特定の空間や状況。"
  ],
  "pronunciation": "きかい",
  "correct_definition": "動力で動き、人の代わりに働く装置。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "a decision; to decide — clearly settling on something, and the content settled on",
        "紧握",
        "the edge (seam)",
        "動力で動き、人の代わりに働く装置。"
      ],
      "correct_answer": "動力で動き、人の代わりに働く装置。"
    }
  },
  "tier": "T6",
  "word": "機械",
  "pronunciation": "きかい",
  "schema_version": 2
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
### Level 4 (sense 35001, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "機械化",
      "機械的"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "機械化",
      "機械的"
    ]
  },
  "input_mode": "ime",
  "target_word": "機械",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "工場には大きな機械がたくさんある。",
  "sentence_with_blank": "工場には大きな___がたくさんある。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "機械化",
      "機械的"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "機械化",
      "機械的"
    ]
  },
  "input_mode": "ime",
  "target_word": "機械",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "機械のおかげで作業が早くなった。",
  "sentence_with_blank": "___のおかげで作業が早くなった。"
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
### Level 6 (sense 35001, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "機械が壊れたので修理を頼んだ。",
      "is_correct": true
    },
    {
      "text": "機械が歌を歌いだした。",
      "is_correct": false
    },
    {
      "text": "機械が恋をした。",
      "is_correct": false
    },
    {
      "text": "機械が悲しんでいる。",
      "is_correct": false
    }
  ],
  "explanation": "機械には感情がなく、悲しむことはない。 機械が恋をすることはない。 この文脈の機械が自発的に歌うことはない。",
  "target_word": "機械"
}
```

---
