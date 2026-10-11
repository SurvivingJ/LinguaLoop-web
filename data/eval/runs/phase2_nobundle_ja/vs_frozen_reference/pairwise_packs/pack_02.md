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
### Level 4 (sense 35311, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ]
  },
  "input_mode": "ime",
  "target_word": "可能",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "簡単",
    "必要",
    "重要",
    "可能"
  ],
  "base_form": "可能",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "target_word": "可能",
  "correct_answer": "可能",
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ]
  },
  "input_mode": "ime",
  "target_word": "可能",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "それは十分に可能だ。",
  "sentence_with_blank": "それは十分に___だ。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "必要",
    "重要",
    "簡単",
    "可能"
  ],
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "target_word": "可能",
  "correct_answer": "可能",
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "それは十分に可能だ。",
  "sentence_with_blank": "それは十分に___だ。"
}
```

---

## sense 35311, level 6

#### Pack A
### Level 6 (sense 35311, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "もたらしています可能性を新たな、小規模農家の経営に精密農業の導入が。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしいます。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性がもたらしています。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：他動詞「もたらす」の対象は「を」で示す。「が」は誤り。 活用：「もたらして」が正しい活用で、「もたらしい」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "可能"
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "彼にはそれが可能で見える。",
      "is_correct": false
    },
    {
      "text": "彼にはそれが可能に見える。",
      "is_correct": true
    },
    {
      "text": "見える可能にそれが、彼には。",
      "is_correct": false
    },
    {
      "text": "彼にそれが可能に見える。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：経験者を示す「には」を単なる「に」に置き換えると不自然。 活用：連用形は「可能に」であり、「可能で」は接続が誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "可能"
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
### Level 7 (sense 35311, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "また、限られた環境で効率的に生産を行う「資源管理」の観点からも、持続可能な食料供給の実現において重要な役割を果たしています。",
      "is_correct": true
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能が体重になります。",
      "is_correct": false,
      "error_description": "活用：名詞の前では連体形「可能な」を使う。「可能が」は誤り。"
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
      "is_correct": true
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
### Level 9 (sense 35311, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "これは可能な計画だ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "近年精密農業の",
    "導入が",
    "小規模農家の",
    "経営に",
    "新たな可能性を",
    "もたらしています"
  ],
  "chunk_count": 6,
  "target_word": "可能",
  "schema_version": 2,
  "shuffled_chunks": [
    "近年精密農業の",
    "もたらしています",
    "新たな可能性を",
    "導入が",
    "経営に",
    "小規模農家の"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。"
}
```

---

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "みずから",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "mizɯkaɾa",
  "word": "自ら",
  "options": [
    "水換え",
    "見るから",
    "自ら",
    "水カビ"
  ],
  "audio_url": null,
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "pronunciation": "みずから",
  "correct_answer": "自ら",
  "syllable_count": 4,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "水換え": "「水換え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。",
    "見るから": "「見るから」は「自ら」と一モーラだけ異なる実在語です（2モーラ目: 「ず」→「る」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "prompt": "みずから",
  "options": [
    "視覚",
    "購買",
    "自分",
    "自ら"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "自ら",
  "schema_version": 2,
  "distractor_sources": {
    "自分": "component",
    "視覚": "component",
    "購買": "component"
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
### Level 2 (sense 39187, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "こなのように、とても細かいものです。",
        "a (coffee) bean",
        "vertical",
        "自分自身を指す言葉。"
      ],
      "correct_answer": "自分自身を指す言葉。"
    }
  },
  "tier": "T6",
  "word": "自ら",
  "pronunciation": "みずから",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "options": [
    "ある物事や現象が一時的に非常に人気になり、多くの人々が熱中する状態。",
    "自分自身を指す言葉。",
    "ある製品や資源を、多く消費したり使用したりする国",
    "実際に物事を行ったり、その場に立ち会ったりして得た知識や技能。"
  ],
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。"
}
```

---

## sense 39187, level 3

#### Pack A
### Level 3 (sense 39187, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "自分",
    "自ら",
    "他人",
    "彼"
  ],
  "explanation": "「自らの肌で実感する」は自分自身を指す固定表現。",
  "target_word": "自ら",
  "correct_answer": "自ら",
  "distractor_tags": {},
  "word_definition": "自分自身を指す言葉。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。"
}
```

#### Pack B
### Level 3 (sense 39187, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "変化に適応し、___の価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "original_sentence": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "correct_answer": "自ら",
  "options": [
    "自ら",
    "自分",
    "彼",
    "他人"
  ],
  "explanation": "「自らの肌で実感する」は自分自身を指す固定表現。",
  "distractor_tags": {},
  "word_definition": "自分自身のこと。",
  "target_word": "自ら"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "君は___選ぶべきです。",
  "original_sentence": "君は自ら選ぶべきです。",
  "correct_answer": "自ら",
  "options": [
    "直ぐ",
    "彼ら",
    "自ら",
    "共に"
  ],
  "explanation": "正解です。文脈「君は＿＿選ぶべきです」において、他人に頼らず自分自身で決定するという意味で「自ら」が適切です。",
  "distractor_tags": {},
  "word_definition": "自分自身のこと。",
  "target_word": "自ら"
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

#### Pack B
### Level 4 (sense 39187, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
    ]
  },
  "input_mode": "ime",
  "target_word": "自ら",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "sentence_with_blank": "変化に適応し、___の価値を高め続ける姿勢が、これからの職場では強く求められる。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
    ]
  },
  "input_mode": "ime",
  "target_word": "自ら",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "自らの過ちを認めた。",
  "sentence_with_blank": "___の過ちを認めた。"
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
### Level 6 (sense 39187, difficulty 8)
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "高めている彼女は自らを。",
      "is_correct": false
    },
    {
      "text": "彼女は自らを高めている。",
      "is_correct": true
    },
    {
      "text": "彼女は自らが高めている。",
      "is_correct": false
    },
    {
      "text": "彼女は自らを高まっている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「高める」の対象は「を」で示す。「が」は誤り。 活用：他動詞は「高める」であり、自動詞「高まる」との混同は誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "自ら"
}
```

---

## sense 39187, level 7

#### Pack A
### Level 7 (sense 39187, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らを価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": false,
      "error_description": "助詞：連体修飾の「の」を「を」に置き換えるのは誤り。"
    },
    {
      "text": "彼は自らの力で成功した。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
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
      "text": "彼女は自らを高めている。",
      "is_correct": true
    },
    {
      "text": "彼は自ら行動する。",
      "is_correct": true
    },
    {
      "text": "自らの過ちが認めた。",
      "is_correct": false,
      "error_description": "助詞：他動詞「認める」の対象は「を」で示す。「が」は誤り。"
    },
    {
      "text": "自らの過ちを認めた。",
      "is_correct": true
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

---
