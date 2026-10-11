# Pairwise review pack 02

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


## sense 35311, level 4

#### Pack A
### Level 4 (sense 35311, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "再生___エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "不可能",
      "可能性",
      "可能だ",
      "可能な"
    ],
    "accepted_normalized": [
      "可能",
      "不可能",
      "可能性",
      "可能だ",
      "可能な"
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
  "sentence_with_blank": "再生___エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "options": [
    "必要",
    "簡単",
    "重要",
    "可能"
  ],
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_typed** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "それは実現不___です。",
  "original_sentence": "それは実現不可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "不可能",
      "可能性",
      "可能だ",
      "可能な"
    ],
    "accepted_normalized": [
      "可能",
      "不可能",
      "可能性",
      "可能だ",
      "可能な"
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
  "sentence_with_blank": "それは実現不___です。",
  "original_sentence": "それは実現不可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "必要",
    "簡単",
    "重要",
    "可能"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 4 (sense 35311, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが___です。",
  "original_sentence": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
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
  "sentence_with_blank": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが___です。",
  "original_sentence": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
  "correct_answer": "可能です",
  "base_form": "可能",
  "form_label": "です形（丁寧）",
  "options": [
    "可能な",
    "可能です",
    "可能だ",
    "可能で"
  ],
  "explanation": "丁寧な文体（polite）の文末に接続する「です形」が適切です。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "彼が手伝うことは___です。",
  "original_sentence": "彼が手伝うことは可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
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
  "sentence_with_blank": "彼が手伝うことは___です。",
  "original_sentence": "彼が手伝うことは可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "可能",
    "簡単",
    "重要",
    "必要"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 6

#### Pack A
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この技術を使えば、新しいエネルギーを生み出すことを可能です。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。",
      "is_correct": true
    },
    {
      "text": "最新のAIにより、複雑な計算を可能しています。",
      "is_correct": false
    },
    {
      "text": "この計画により、一本の新しい工場を建設することが可能です。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「工場」の助数詞は「一本」ではなく「一軒」または「一つ」が適切です。 助詞の混同：「～ことを可能だ」とは言いません。「～ことが可能だ」とするのが正しいです。 活用・アスペクトの誤り：「可能」は形状詞なので「～している」のような動詞の活用はつきません。「可能にしています」や「可能となっています」が正しいです。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "不可能",
    "必須",
    "必然",
    "容易"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態を指し、目標語の対義語となる。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性がもたらしています。",
      "is_correct": false
    },
    {
      "text": "もたらしています可能性を新たな、小規模農家の経営に精密農業の導入が。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
      "is_correct": true
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしいます。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「もたらす」の対象は「を」で示す。「が」は誤り。 活用：「もたらして」が正しい活用で、「もたらしい」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "確実",
    "不可能",
    "容易",
    "有効"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行える状態の対義語であり、行うことができない性質を表す。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "連絡はメールで可能です。",
      "is_correct": true
    },
    {
      "text": "彼にはそれが可能で見える。",
      "is_correct": false
    },
    {
      "text": "彼にそれが可能に見える。",
      "is_correct": false
    },
    {
      "text": "見える可能にそれが、彼には。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：経験者を示す「には」を単なる「に」に置き換えると不自然。 活用：連用形は「可能に」であり、「可能で」は接続が誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "簡単",
    "複雑",
    "不便",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行える状態の対義語であり、行うことができない性質を表す"
    }
  }
}
```

---

## sense 35311, level 7

#### Pack A
### Level 7 (sense 35311, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能が体重になります。",
      "is_correct": false,
      "error_description": "活用：名詞の前では連体形「可能な」を使う。「可能が」は誤り。"
    },
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "今すぐ出発することが可能だ。",
      "is_correct": false,
      "error_description": "「も」を「が」に置き換えると、他の選択肢との並列を示す含意が失われる。"
    },
    {
      "text": "連絡はメールで可能です。",
      "is_correct": true
    },
    {
      "text": "明日なら参加が可能です。",
      "is_correct": true
    },
    {
      "text": "それは実現不可能です。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35311, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
      "is_correct": true
    },
    {
      "text": "近年の精密農業の導入により、小規模農家であっても効率的な経営を行うことが可能となりました。",
      "is_correct": true
    },
    {
      "text": "この新しいシステムを導入すれば、社内のデータ管理を可能となります。",
      "is_correct": false,
      "error_description": "「可能となります」は自動詞的な表現であり、その対象には主格を表す「が」を用います。「を」を用いる場合は「可能にします」とするのが正しい用法です。"
    }
  ]
}
```

---

## sense 35311, level 9

#### Pack A
### Level 9 (sense 35311, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "この問題は解決可能です。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "chunks": [
    "彼らは",
    "驚くべきスピードで",
    "成長し",
    "わずか数週間で",
    "出荷可能な体重に",
    "なります"
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
    "彼らは",
    "なります",
    "出荷可能な体重に",
    "驚くべきスピードで",
    "わずか数週間で",
    "成長し"
  ],
  "target_word": "可能",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35311, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "明日の会議はオンラインで可能です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "明日の会議はオンラインで可能です。",
  "chunks": [
    "明日の",
    "会議は",
    "オンラインで",
    "可能です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "可能です",
    "明日の",
    "オンラインで",
    "会議は"
  ],
  "target_word": "可能",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。",
  "chunks": [
    "彼らは",
    "驚くべきスピードで",
    "成長しわずか数週間で",
    "市場に出荷することが",
    "可能な体重に",
    "まで達します"
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
    "彼らは",
    "まで達します",
    "可能な体重に",
    "驚くべきスピードで",
    "市場に出荷することが",
    "成長しわずか数週間で"
  ],
  "target_word": "可能",
  "chunk_count": 6
}
```

---

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "correct_answer": "みずから",
  "word": "自ら",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "水カビ",
    "蹼",
    "自ら",
    "ミズカビ"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "ミズカビ": "「ミズカビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "蹼": "「蹼」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「き」、一部の音の違い）。",
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "みずから",
  "options": [
    "視覚",
    "購買",
    "自分",
    "自ら"
  ],
  "correct_answer": "自ら",
  "word": "自ら",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "視覚": "component",
    "購買": "component",
    "自分": "component"
  }
}
```

#### Pack B
### Level 1 (sense 39187, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "correct_answer": "みずから",
  "word": "自ら",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "みずから",
  "options": [
    "購買",
    "自分",
    "見る",
    "自ら"
  ],
  "correct_answer": "自ら",
  "word": "自ら",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "購買": "component",
    "自分": "component",
    "見る": "component"
  }
}
```

---

## sense 39187, level 2

#### Pack A
### Level 2 (sense 39187, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "correct_definition": "自分自身のこと。",
  "options": [
    "病気やけがなどを治療して、健康な状態にすること。",
    "機械や乗り物など、一人で使ったり動かしたりするものを数える語。",
    "限りある資源やお金、時間などを、無駄なく効率的に使うこと。また、その考え方。",
    "自分自身のこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "dissipation (radiation)",
        "trade — the buying and selling of goods between countries",
        "自分自身のこと。",
        "an object; a target — the person or thing toward which an action or thought is directed"
      ],
      "correct_answer": "自分自身のこと。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 39187, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。",
  "options": [
    "自分自身を指す言葉。",
    "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
    "資本。元手となるお金。また、首都。",
    "何かを包み込んだり、中に含めたりすることを表す動詞。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "irrigation",
        "消化管の一部で、栄養の吸収や便の形成に関わる器官。食物の消化と吸収、免疫機能にも重要な役割を果たす。",
        "自分自身を指す言葉。",
        "特別でなく、広く一般的なさま。多くの人や物事に共通していること。"
      ],
      "correct_answer": "自分自身を指す言葉。"
    }
  }
}
```

---

## sense 39187, level 4

#### Pack A
### Level 4 (sense 39187, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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
  "sentence_with_blank": "___が進む道です。",
  "original_sentence": "自らが進む道です。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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
### Level 4 (sense 39187, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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
  "sentence_with_blank": "先生は___説明してくれました。",
  "original_sentence": "先生は自ら説明してくれました。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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

## sense 39187, level 6

#### Pack A
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "弟は自ら片付けました。",
      "is_correct": true
    },
    {
      "text": "弟は自ら片付けていますでした。",
      "is_correct": false
    },
    {
      "text": "弟は自らを片付けました。",
      "is_correct": false
    },
    {
      "text": "弟は自らが片付けました。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「自ら」は副詞的に用いられ、「自分で」という意味を表します。目的語をとる名詞ではないため、助詞「を」を取ることはできません。正しくは「弟は自ら片付けました」または「弟は自分の部屋を自ら片付けました」などとなります。 係り受けの誤り：「が」を用いると「自らが」が主語として強調されますが、文末の「片付けました」の主語は既に「弟は」として提示されています。二重主語となり不自然です。通常、「自ら」は動詞を修飾する副詞的用法で用いられます。 活用・アスペクトの誤り：「ています」は進行・状態、「でした」は過去の丁寧語尾です。これらを直接結合させることは文法的に誤りです。正しくは「片付けていました」または「片付けました」となります。",
  "target_word": "自ら"
}
```

#### Pack B
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "自ら守るがルールです。",
      "is_correct": false
    },
    {
      "text": "自らをルールが守る。",
      "is_correct": false
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
      "is_correct": true
    },
    {
      "text": "自らが守るルールだ。",
      "is_correct": false
    }
  ],
  "explanation": "項構造：「自ら」は「守る」動作の主体（主語）ではなく、対象（目的語）です。正しくは「自らが守るルール」です。 語域：「だ」は口語的な断定表現であり、基礎例文の「自らが守るルールです」という丁寧な表現と語域が一致しません。 語順：「自ら守るが」の「が」の位置が誤りです。名詞を修飾する場合は「自ら守るルール」となるべきです。",
  "target_word": "自ら"
}
```

---

## sense 39187, level 7

#### Pack A
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    },
    {
      "text": "私は自ら勉強しています。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らを価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": false,
      "error_description": "助詞：連体修飾の「の」を「を」に置き換えるのは誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "弟は自ら片付けました。",
      "is_correct": true
    },
    {
      "text": "君は自ら選ぶべきです。",
      "is_correct": true
    },
    {
      "text": "先生は自ら説明してくれました。",
      "is_correct": true
    },
    {
      "text": "自らの過ちが認めた。",
      "is_correct": false,
      "error_description": "助詞：他動詞「認める」の対象は「を」で示す。「が」は誤り。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼は自らでそのプロジェクトを成功させた。",
      "is_correct": false,
      "error_description": "「自ら」は副詞的・名詞的に「自分自身」を指しますが、「自分で」とは異なり、助詞「で」を伴って動作の主体を表す用法はありません。「自分で」との混同による助詞の誤用です。正しくは「自ら」または「自らが」とします。"
    },
    {
      "text": "自らを責めて、泣きました。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
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
      "text": "自らが守るルールです。",
      "is_correct": true
    },
    {
      "text": "自らが進む道です。",
      "is_correct": true
    },
    {
      "text": "自らを進む道です。",
      "is_correct": false,
      "error_description": "助詞の混同。「自ら」は動詞「進む」の主語であるため、格助詞「が」を使うのが適切です。「を」は動作の目的語を示す際に使います。"
    },
    {
      "text": "自らが考えたアイデアです。",
      "is_correct": true
    }
  ]
}
```

---

## sense 39187, level 9

#### Pack A
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "自らの気持ちを大切にします。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "自らの気持ちを大切にします。",
  "chunks": [
    "自らの",
    "気持ちを",
    "大切にします"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "大切にします",
    "気持ちを",
    "自らの"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "自らが決めた道です。"
}
```

#### Pack B
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼女は自ら行動しています。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼女は自ら行動しています。",
  "chunks": [
    "彼女は",
    "自ら行動して",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "います",
    "自ら行動して",
    "彼女は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は自らその問題を解決しました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は自らその問題を解決しました。",
  "chunks": [
    "彼は",
    "自らその問題を",
    "解決しました"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "自らその問題を",
    "解決しました",
    "彼は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```

---
