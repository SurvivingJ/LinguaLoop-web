# Pairwise review pack 06

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


## sense 38099, level 4

#### Pack A
### Level 4 (sense 38099, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと___されるのである。",
  "original_sentence": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
  "target_word": "昇華",
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華させる",
      "昇華される"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華させる",
      "昇華される"
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
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "怒りを、正義へと___できる。",
  "original_sentence": "怒りを、正義へと昇華できる。",
  "target_word": "昇華",
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華させる",
      "昇華される"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華させる",
      "昇華される"
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
### Level 4 (sense 38099, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと___されるのである。",
  "original_sentence": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
  "target_word": "昇華",
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華した",
      "昇華させる"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華した",
      "昇華させる"
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
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "努力が成功への道へと___する。",
  "original_sentence": "努力が成功への道へと昇華する。",
  "target_word": "昇華",
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華した",
      "昇華させる"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華した",
      "昇華させる"
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

## sense 38099, level 6

#### Pack A
### Level 6 (sense 38099, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華だ。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
      "is_correct": true
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華っぽい。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華いる。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。動詞の活用形が誤っています。「昇華される」または「昇華する」であるべきです。 誤答。名詞「昇華」に断定の助動詞「だ」を直接付けることはできず、文法的に不自然です。 誤答。「昇華」は名詞であり、様態を表す「っぽい」を直接付けることはできません。",
  "target_word": "昇華"
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "synonym",
  "options": [
    "高揚",
    "停滞",
    "低下",
    "堕落"
  ],
  "correct_answer": "高揚",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
      "explanation": "類義語。精神や気分が高まることを指し、文脈的に近いです。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "経験が知恵へと昇華いる。",
      "is_correct": false
    },
    {
      "text": "経験が知恵へと昇華していく。",
      "is_correct": true
    },
    {
      "text": "経験が知恵へと昇華っぽい。",
      "is_correct": false
    },
    {
      "text": "経験が知恵へと昇華だ。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。動詞の活用形が誤っています。「昇華していく」または「昇華する」であるべきです。 誤答。名詞「昇華」に断定の助動詞「だ」を直接付けることはできず、文法的に不自然です。 誤答。「昇華」は名詞であり、様態を表す「っぽい」を直接付けることはできません。",
  "target_word": "昇華"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "synonym",
  "options": [
    "高揚",
    "停滞",
    "低下",
    "堕落"
  ],
  "correct_answer": "高揚",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
      "explanation": "類義語。精神や気分が高まることを指し、文脈的に近いです。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 38099, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華せれる。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
      "is_correct": true
    },
    {
      "text": "叶える食文化へと昇華される、生命の維持と豊かな食体験を同時に、穀物が。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化が昇華される。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：結果を示す「へと」を「が」に置き換えるのは誤り。 活用：受身形は「される」であり、「せれる」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "昇華"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "想いは、歌へと昇華している。",
      "is_correct": true
    },
    {
      "text": "想いは、歌へと昇華したことがある。",
      "is_correct": false
    },
    {
      "text": "想いは、昇華している歌へと。",
      "is_correct": false
    },
    {
      "text": "想いは、歌で昇華している。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「で」は場所や手段を表します。変化の到達点を表すには「へと」や「に」を使う必要があります。 活用・アスペクトの誤り：「たことがある」は過去の経験を表します。現在の状態や継続的な変化には「ている」が適切です。 語順・係り受けの誤り：「昇華している」が直後の「歌」を修飾する形になり、「想い」が昇華するという本来の意味が壊れています。",
  "target_word": "昇華"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "antonym",
  "options": [
    "転換",
    "停滞",
    "堕落",
    "進化"
  ],
  "correct_answer": "堕落",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
      "explanation": "価値や精神が低い状態へ落ちることを表し、高まることの対義となる"
    }
  }
}
```

---

## sense 38099, level 7

#### Pack A
### Level 7 (sense 38099, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへが昇華させるのである。",
      "is_correct": false,
      "error_description": "助詞：結果を示す「へと」を「へが」に置き換えるのは誤り。"
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 38099, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "努力が成功への道へと昇華する。",
      "is_correct": true
    },
    {
      "text": "この経験は自信が昇華する。",
      "is_correct": false,
      "error_description": "助詞：結果を示す「へと」を「が」に置き換えるのは誤り。"
    },
    {
      "text": "悲しみが芸術作品へと昇華した。",
      "is_correct": true
    },
    {
      "text": "経験が知恵へと昇華していく。",
      "is_correct": true
    }
  ]
}
```

---

## sense 38099, level 9

#### Pack A
### Level 9 (sense 38099, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "この憧れの感情は、やがて芸術的な表現へと昇華され、人々の精神を深く揺さぶる存在となるのだ。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "この憧れの感情は、やがて芸術的な表現へと昇華され、人々の精神を深く揺さぶる存在となるのだ。",
  "chunks": [
    "この憧れの感情は",
    "やがて芸術的",
    "な表現へと昇華され",
    "人々の精神を",
    "深く揺さぶる存在と",
    "なるのだ"
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
    "人々の精神を",
    "やがて芸術的",
    "な表現へと昇華され",
    "深く揺さぶる存在と",
    "なるのだ",
    "この憧れの感情は"
  ],
  "target_word": "昇華",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
  "chunks": [
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
    "生命の維持と",
    "豊かな食体験を同時に",
    "叶える食文化へ",
    "と昇華される"
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
    "叶える食文化へ",
    "生命の維持と",
    "豊かな食体験を同時に",
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
    "と昇華される"
  ],
  "target_word": "昇華",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 38099, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "個人の内に秘めた深い悲しみは、やがて普遍的な芸術作品へと昇華を遂げ、多くの人々の心に静かな感動を呼び起こすことになるのだ。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "個人の内に秘めた深い悲しみは、やがて普遍的な芸術作品へと昇華を遂げ、多くの人々の心に静かな感動を呼び起こすことになるのだ。",
  "chunks": [
    "個人の内に",
    "秘めた深い悲しみは",
    "やがて普遍的な芸術作品へ",
    "と昇華を遂げ多くの",
    "人々の心に静かな感動を",
    "呼び起こすことになるのだ"
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
    "と昇華を遂げ多くの",
    "秘めた深い悲しみは",
    "やがて普遍的な芸術作品へ",
    "人々の心に静かな感動を",
    "呼び起こすことになるのだ",
    "個人の内に"
  ],
  "target_word": "昇華",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
  "chunks": [
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
    "生命の維持と",
    "豊かな食体験を同時に",
    "叶える食文化へ",
    "と昇華される"
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
    "叶える食文化へ",
    "生命の維持と",
    "豊かな食体験を同時に",
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
    "と昇華される"
  ],
  "target_word": "昇華",
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

#### Pack B
### Level 2 (sense 39187, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。",
  "options": [
    "弓や楽器などに張る、細くて丈夫な糸。また、三味線などの楽器の糸。",
    "情報や考え、文化などが、人から人へと広まっていくこと。また、広めること。",
    "複数の要素や事柄を組み合わせて、一つのまとまりのあるものを作り出すこと。",
    "自分自身を指す言葉。"
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
        "まなぶこと。",
        "桥梁",
        "自分自身を指す言葉。",
        "to be commonly used; valid — being widely and generally used, or effective"
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌___実感していくことになります。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "options": [
    "を",
    "で",
    "と",
    "に"
  ],
  "correct_answer": "で",
  "target_word": "自ら",
  "error_tags": {
    "に": "",
    "を": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "手段・様態を表す助詞として自然です。「自らの肌で実感する」は慣用的な表現です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "彼は___その責任を引き受けました。",
  "original_sentence": "彼は自らその責任を引き受けました。",
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
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼は自らその責任___引き受けました。",
  "original_sentence": "彼は自らその責任を引き受けました。",
  "options": [
    "に",
    "で",
    "と",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "自ら",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。「責任を引き受ける」の対象を示す格助詞として「を」が自然です。"
    }
  }
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

---

## sense 39187, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼は自らをその問題を解決した。",
      "is_correct": false
    },
    {
      "text": "彼は自らその問題を解決した。",
      "is_correct": true
    },
    {
      "text": "彼は自らにその問題を解決した。",
      "is_correct": false
    },
    {
      "text": "彼は自らがその問題を解決した。",
      "is_correct": false
    }
  ],
  "explanation": "誤り。「自ら」は代名詞であり、動作の主体を示すため、後に助詞「に」をつけて対象とするのは不自然です。 誤り。「自ら」の後に主格の「が」を重ねると冗長かつ不自然な強調になり、通常の文法では避けられます。 誤り。「自ら」を目的語「を」で受ける構造は、再帰動詞（例：自らを律する）以外では一般的ではありません。",
  "target_word": "自ら"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "relation": "synonym",
  "options": [
    "自分",
    "他人",
    "誰",
    "彼"
  ],
  "correct_answer": "自分",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "自分自身を指す言葉。",
      "explanation": "類義語。「自ら」と「自分」はどちらも自分自身を指します。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "子供たちは自ら片付けました。",
      "is_correct": true
    },
    {
      "text": "子供たちは自らが片付けました。",
      "is_correct": false
    },
    {
      "text": "子供たちは自らに片付けました。",
      "is_correct": false
    },
    {
      "text": "子供たちは自らを片付けました。",
      "is_correct": false
    }
  ],
  "explanation": "誤り。「自ら」の後に主格の「が」を入れると、二重主語のような不自然な構造になります。 誤り。「自ら」に助詞「に」をつけると、動作の方向や対象が変わってしまい、意味が通じなくなります。 誤り。「片付ける」の目的語として「自ら（自分自身）」をとると、物理的な意味になってしまい不自然です。",
  "target_word": "自ら"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "自ら",
  "relation": "synonym",
  "options": [
    "誰",
    "自分",
    "彼",
    "他人"
  ],
  "correct_answer": "自分",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "自分自身を指す言葉。",
      "explanation": "類義語。「自ら」と「自分」はどちらも自分自身を指します。"
    }
  }
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
  "original_sentence": "彼女は自ら行動できる人です。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は自らその問題を解決した。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は自らその問題を解決した。",
  "chunks": [
    "彼は",
    "自らその問題を",
    "解決した"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "自らその問題を",
    "解決した",
    "彼は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```

---

## sense 39661, level 1

#### Pack A
### Level 1 (sense 39661, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "営み",
  "options": [
    "いとうなみ",
    "いいとなみ",
    "いとなみ",
    "いどなみ"
  ],
  "correct_answer": "いとなみ",
  "word": "営み",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "itonami",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "営み",
    "住み",
    "悩み",
    "試み"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。」という意味です。",
  "distractor_explanations": {
    "試み": "",
    "悩み": "",
    "住み": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "いとなみ",
  "options": [
    "宇宙",
    "経営",
    "運営",
    "営み"
  ],
  "correct_answer": "営み",
  "word": "営み",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "運営": "component",
    "宇宙": "component",
    "経営": "component"
  }
}
```

#### Pack B
### Level 1 (sense 39661, difficulty None)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "prompt": "営み",
  "options": [
    "いとうなみ",
    "いいとなみ",
    "いとなみ",
    "いどなみ"
  ],
  "correct_answer": "いとなみ",
  "word": "営み",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "/itonami/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "伊奘冉",
    "営み",
    "人並み",
    "岩波"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「人や動物が生活し、生命を保つための活動。」という意味です。",
  "distractor_explanations": {
    "岩波": "「岩波」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「わ」、一部の音の違い）。",
    "伊奘冉": "「伊奘冉」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。",
    "人並み": "「人並み」は「営み」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ひ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "prompt": "いとなみ",
  "options": [
    "宇宙",
    "経営",
    "運営",
    "営み"
  ],
  "correct_answer": "営み",
  "word": "営み",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "運営": "component",
    "宇宙": "component",
    "経営": "component"
  }
}
```

---
