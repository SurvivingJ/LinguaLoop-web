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


## sense 38099, level 1

#### Pack A
### Level 1 (sense 38099, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "昇華",
  "prompt": "昇華",
  "options": [
    "しょうが",
    "じょうか",
    "しいょうか",
    "しょうか"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "しょうか",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "ɕoːka",
  "word": "昇華",
  "options": [
    "供花",
    "昇華",
    "教化",
    "中夏"
  ],
  "audio_url": null,
  "explanation": "正解です。「昇華」は「ある物事が、より高い段階や価値のある状態へと高まること。」という意味です。",
  "pronunciation": "しょうか",
  "correct_answer": "昇華",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "中夏": "「中夏」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「ちゅ」、一部の音の違い）。",
    "供花": "「供花」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「きょ」、一部の音の違い）。",
    "教化": "「教化」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「きょ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "昇華",
  "prompt": "しょうか",
  "options": [
    "上昇",
    "飛ぶ",
    "昇華",
    "飛行"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "昇華",
  "schema_version": 2,
  "distractor_sources": {
    "上昇": "component",
    "飛ぶ": "component",
    "飛行": "component"
  }
}
```

#### Pack B
### Level 1 (sense 38099, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "昇華",
  "options": [
    "しょうが",
    "じょうか",
    "しいょうか",
    "しょうか"
  ],
  "correct_answer": "しょうか",
  "word": "昇華",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "しょうか",
  "options": [
    "上昇",
    "飛躍",
    "昇華",
    "飛ぶ"
  ],
  "correct_answer": "昇華",
  "word": "昇華",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "上昇": "component",
    "飛ぶ": "component",
    "飛躍": "component"
  }
}
```

---

## sense 38099, level 2

#### Pack A
### Level 2 (sense 38099, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "correct_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "options": [
    "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
    "新しい事業や企業を始めること。特に、リスクが高いが大きな成長が期待される事業。",
    "「オート」は接頭語で、自動的な、または自己のという意味を表します。主に外来語の一部として使われます。",
    "構造物や建築物を作り上げる。柱や壁などを組み立てて完成させる。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "自分の手の届くあたり。",
        "数值",
        "心跳",
        "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
      ],
      "correct_answer": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 38099, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "昇華",
  "options": [
    "ある物事が、より高い段階や価値のある状態へと高まること。",
    "存在していた物が、使われたり、無くなったりして、もうない状態になること。",
    "物事の状態や場所が、時間がたつにつれて変わっていくこと。",
    "人々が共通の目的や感情によって強く結びつき、まとまること。"
  ],
  "pronunciation": "しょうか",
  "correct_definition": "ある物事が、より高い段階や価値のある状態へと高まること。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "an exit strategy — a method in business for stepping away from a venture to realize investment profit",
        "ある物事が、より高い段階や価値のある状態へと高まること。",
        "如果……那么",
        "强化 —— 把事物的力量变得更强、更牢固"
      ],
      "correct_answer": "ある物事が、より高い段階や価値のある状態へと高まること。"
    }
  },
  "tier": "T6",
  "word": "昇華",
  "pronunciation": "しょうか",
  "schema_version": 2
}
```

---

## sense 38099, level 4

#### Pack A
### Level 4 (sense 38099, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華点"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華点"
    ]
  },
  "input_mode": "ime",
  "target_word": "昇華",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
  "sentence_with_blank": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと___させるのである。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "昇華",
  "answer": {
    "accepted": [
      "昇華",
      "昇華する",
      "昇華点"
    ],
    "accepted_normalized": [
      "昇華",
      "昇華する",
      "昇華点"
    ]
  },
  "input_mode": "ime",
  "target_word": "昇華",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "悲しみが美しい歌へと昇華する。",
  "sentence_with_blank": "悲しみが美しい歌へと___する。"
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
### Level 6 (sense 38099, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
      "is_correct": true
    },
    {
      "text": "叶える食文化へと昇華される、生命の維持と豊かな食体験を同時に、穀物が。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華せれる。",
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

---

## sense 38099, level 7

#### Pack A
### Level 7 (sense 38099, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    },
    {
      "text": "この憧れの感情は、やがてグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
      "is_correct": true
    },
    {
      "text": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへが昇華させるのである。",
      "is_correct": false,
      "error_description": "助詞：結果を示す「へと」を「へが」に置き換えるのは誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "悲しみが美しい歌へと昇華する。",
      "is_correct": true
    },
    {
      "text": "苦労が喜びへと昇華した。",
      "is_correct": true
    },
    {
      "text": "この経験は自信が昇華する。",
      "is_correct": false,
      "error_description": "助詞：結果を示す「へと」を「が」に置き換えるのは誤り。"
    },
    {
      "text": "彼の努力は成功へと昇華した。",
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
### Level 9 (sense 38099, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営み。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "無機質な素材が",
    "自律的",
    "実体へと",
    "昇華する奇跡を",
    "自らの双手で",
    "紡ぎ出す営み"
  ],
  "chunk_count": 6,
  "target_word": "昇華",
  "schema_version": 2,
  "shuffled_chunks": [
    "昇華する奇跡を",
    "自律的",
    "実体へと",
    "自らの双手で",
    "紡ぎ出す営み",
    "無機質な素材が"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営み。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
    "生命の維持と",
    "豊かな食体験を同時に",
    "叶える食文化へ",
    "と昇華される"
  ],
  "chunk_count": 6,
  "target_word": "昇華",
  "schema_version": 2,
  "shuffled_chunks": [
    "叶える食文化へ",
    "生命の維持と",
    "豊かな食体験を同時に",
    "単なるエネルギー源に",
    "過ぎなかった穀物が",
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
  "original_sentence": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。"
}
```

#### Pack B
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

#### Pack B
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

---

## sense 39187, level 2

#### Pack A
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

---

## sense 39187, level 6

#### Pack A
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
