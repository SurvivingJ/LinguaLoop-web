# Pairwise review pack 04

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


## sense 35147, level 1

#### Pack A
### Level 1 (sense 35147, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "行きます",
  "options": [
    "いくう",
    "いぐ",
    "いいく",
    "いく"
  ],
  "correct_answer": "いく",
  "word": "行きます",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "いく",
  "options": [
    "行く",
    "幾",
    "行きます",
    "ポリマー"
  ],
  "correct_answer": "行きます",
  "word": "行きます",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "行く": "homophone",
    "幾": "homophone",
    "ポリマー": "frequency"
  }
}
```
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "ipa": "/iku/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "鋳る",
    "ズク",
    "行く",
    "遺址"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。また、物事が進む。」という意味です。",
  "distractor_explanations": {
    "ズク": "「ズク」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ず」、一部の音の違い）。",
    "鋳る": "「鋳る」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「る」、一部の音の違い）。",
    "遺址": "「遺址」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「し」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35147, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "行く",
  "options": [
    "いくう",
    "いぐ",
    "いいく",
    "いく"
  ],
  "correct_answer": "いく",
  "word": "行く",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "ipa": "/iku/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "意氣",
    "肉",
    "軸",
    "行く"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。また、物事が進む。」という意味です。",
  "distractor_explanations": {
    "意氣": "「意氣」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「き」、一部の音の違い）。",
    "肉": "「肉」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「に」、一部の音の違い）。",
    "軸": "「軸」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「じ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "いく",
  "options": [
    "幾",
    "履行",
    "行く",
    "技術"
  ],
  "correct_answer": "行く",
  "word": "行く",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "幾": "homophone",
    "履行": "component",
    "技術": "component"
  }
}
```

---

## sense 35147, level 2

#### Pack A
### Level 2 (sense 35147, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行きます",
  "pronunciation": "いく",
  "correct_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "options": [
    "複数の物や人が集まってできた、一つのまとまり。",
    "木版印刷に用いる、表面に文字や絵を彫った木の板。",
    "ある物事が持つ、良い結果や役に立つ性質。",
    "ある場所から別の場所へ移動する。また、物事が進む。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行きます",
  "pronunciation": "いく",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物事の外見や形式。また、世間に対する体面や見栄。",
        "あることが続かないで、短い間だけのこと。",
        "ある場所から別の場所へ移動する。また、物事が進む。",
        "他の会社。別の企業。"
      ],
      "correct_answer": "ある場所から別の場所へ移動する。また、物事が進む。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35147, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "correct_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "options": [
    "ある場所から別の場所へ移動する。また、物事が進む。",
    "物事の善悪や価値について、自分の考えを決めること。",
    "物事の動きや変化の方向性。特に、社会や時代の全体的な傾向や流れを指すことが多い。",
    "時間をかけて発酵や乾燥などの処理を行い、価値や品質が向上した状態にすること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "茁壮成长 —— 婴儿或孩子健康顺利地迅速长大的样子",
        "乐趣；期待的事；令人开心的事",
        "ある場所から別の場所へ移動する。また、物事が進む。",
        "English (language)"
      ],
      "correct_answer": "ある場所から別の場所へ移動する。また、物事が進む。"
    }
  }
}
```

---

## sense 35147, level 4

#### Pack A
### Level 4 (sense 35147, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "来月、海外へ___友達を祝いました。",
  "original_sentence": "来月、海外へ行く友達を祝いました。",
  "target_word": "行く",
  "word": "行く",
  "answer": {
    "accepted": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
    ],
    "accepted_normalized": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
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
  "sentence_with_blank": "来月、海外へ___友達を祝いました。",
  "original_sentence": "来月、海外へ行く友達を祝いました。",
  "correct_answer": "行く",
  "base_form": "行く",
  "form_label": "辞書形",
  "options": [
    "行きます",
    "行く",
    "行って",
    "行った"
  ],
  "explanation": "「来月」という未来の出来事を修飾するため、辞書形が適切である。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行く"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "私たちは選挙へ___べきです。",
  "original_sentence": "私たちは選挙へ行くべきです。",
  "target_word": "行く",
  "word": "行く",
  "answer": {
    "accepted": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
    ],
    "accepted_normalized": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
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
  "sentence_with_blank": "私たちは選挙へ___べきです。",
  "original_sentence": "私たちは選挙へ行くべきです。",
  "correct_answer": "行く",
  "base_form": "行く",
  "form_label": "辞書形（終止形）",
  "options": [
    "行く",
    "行った",
    "行かない",
    "行って"
  ],
  "explanation": "助動詞「べき」は動詞の辞書形（終止形）に接続する",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行く"
}
```

#### Pack B
### Level 4 (sense 35147, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "友達と映画を見に___。",
  "original_sentence": "友達と映画を見に行っています。",
  "target_word": "行っています",
  "word": "行きます",
  "answer": {
    "accepted": [
      "行っています"
    ],
    "accepted_normalized": [
      "行っています"
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
  "sentence_with_blank": "友達と映画を見に___。",
  "original_sentence": "友達と映画を見に行っています。",
  "correct_answer": "いった",
  "base_form": "行く",
  "form_label": "た形（過去）",
  "options": [
    "いく",
    "いった",
    "いって",
    "いかない"
  ],
  "explanation": "「昨日」があるので過去のた形が必要。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行っています"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この道は狭くて、車で___。",
  "original_sentence": "この道は狭くて、車で行けません。",
  "target_word": "行けません",
  "word": "行きます",
  "answer": {
    "accepted": [
      "行けません"
    ],
    "accepted_normalized": [
      "行けません"
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
  "sentence_with_blank": "この道は狭くて、車で___。",
  "original_sentence": "この道は狭くて、車で行けません。",
  "correct_answer": "行けません",
  "base_form": "行く",
  "form_label": "可能＋ない形（丁寧）",
  "options": [
    "行きません",
    "行ける",
    "行きます",
    "行けません"
  ],
  "explanation": "「狭くて」により不可能な状況なので、可能の否定形が適切です。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行けません"
}
```

---

## sense 35147, level 6

#### Pack A
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "来週、私は東京を行けます。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けています。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けます。",
      "is_correct": true
    },
    {
      "text": "行けます私は来週、東京に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：目的地を表す場合は「に」を使います。「を」は通過点を表します。 活用・アスペクトの誤り：未来の事柄「来週」に対して、状態継続の「ています」は使えません。 語順の誤り：日本語の動詞は文末に置きます。また、主題「私は」は文の初めに置くのが自然です。",
  "target_word": "行けます"
}
```

#### Pack B
### Level 6 (sense 35147, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "relation": "antonym",
  "options": [
    "来る",
    "走る",
    "通る",
    "入る"
  ],
  "correct_answer": "来る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "話し手の方へ移動する意であり、目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は今、京都へ行くています。",
      "is_correct": false
    },
    {
      "text": "私が行く時は一緒にどうですか。",
      "is_correct": true
    },
    {
      "text": "行く私が時は京都へ一緒にどうですか。",
      "is_correct": false
    },
    {
      "text": "私は来週、京都へ行くにしました。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「行く」の後ろには名詞化するための「こと」が必要で、「に」を直接続けることはできません。正しくは「行くことにしました」です。 活用・アスペクトの誤り：「行く」の連用形は「行き」であり、「行くている」は誤りです。正しくは「行っている」または「行っています」です。 語順・係り受けの誤り：「私が行く時は」という節の語順が壊れており、文として成立していません。",
  "target_word": "行く"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "行く",
  "relation": "antonym",
  "options": [
    "渡る",
    "走る",
    "来る",
    "入る"
  ],
  "correct_answer": "来る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "目標語と同じく場所の移動を表すが、方向が逆であるため対義語となる"
    }
  }
}
```

---

## sense 35147, level 7

#### Pack A
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "来月、海外へ行く友達を祝いました。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都で行く予定です。",
      "is_correct": false,
      "error_description": "移動の目的地を表す助詞は「へ」または「に」を使います。「で」は動作の行われる場所を表すため、この文脈では不適切です。"
    },
    {
      "text": "ボランティア活動へ行って、多くのことを学びました。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都へ行く予定です。",
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
      "text": "駅まで歩いて行ってください。",
      "is_correct": true
    },
    {
      "text": "私が行く時は一緒にどうですか。",
      "is_correct": true
    },
    {
      "text": "私たちは選挙へ行くべきです。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都へ行くです。",
      "is_correct": false,
      "error_description": "動詞の辞書形「行く」の後に直接「です」を続けることはできません。「行く予定です」や「行くつもりです」のように形式名詞を挟む必要があります。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は毎日学校に行きます。",
      "is_correct": true
    },
    {
      "text": "昨日行った公園は広かったです。",
      "is_correct": true
    },
    {
      "text": "友達と映画を見に行っています。",
      "is_correct": true
    },
    {
      "text": "彼と一緒に行くには楽しい。",
      "is_correct": false,
      "error_description": "助詞：名詞化の「の」を「に」に置き換えるのは誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "雨が降っているけど、傘を持たずに行きます。",
      "is_correct": true
    },
    {
      "text": "この道は狭くて、車で行けません。",
      "is_correct": true
    },
    {
      "text": "私は毎日電車を使って学校を行きます。",
      "is_correct": false,
      "error_description": "目的地を表す助詞は「に」または「へ」を使います。「を」は移動の経路や通過点に使います。"
    },
    {
      "text": "電車に乗って、町に行って、買い物しました。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35147, level 9

#### Pack A
### Level 9 (sense 35147, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "これから行く場所が楽しみです。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "これから行く場所が楽しみです。",
  "chunks": [
    "これから",
    "行く場所が",
    "楽しみです"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "行く場所が",
    "楽しみです",
    "これから"
  ],
  "target_word": "行く",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "この電車では学校へ行くことができません。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "この電車では学校へ行くことができません。",
  "chunks": [
    "この電車で",
    "は",
    "学校へ",
    "行くことが",
    "できません"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "この電車で",
    "できません",
    "行くことが",
    "は",
    "学校へ"
  ],
  "target_word": "行けない",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 35147, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "公園に行って、いい運動になります。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "公園に行って、いい運動になります。",
  "chunks": [
    "公園に",
    "行って",
    "いい運動に",
    "なります"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "いい運動に",
    "なります",
    "公園に",
    "行って"
  ],
  "target_word": "行って",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "来週、私は東京に行けます。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "来週、私は東京に行けます。",
  "chunks": [
    "来週",
    "私は",
    "東京に",
    "行けます"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "行けます",
    "私は",
    "来週",
    "東京に"
  ],
  "target_word": "行けます",
  "chunk_count": 4
}
```

---

## sense 35227, level 2

#### Pack A
### Level 2 (sense 35227, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "correct_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "options": [
    "ポリエステルは、石油を原料として化学的に合成される繊維で、シワになりにくく、乾きやすい性質を持ちます。衣料品や様々な工業製品に広く用いられています。",
    "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
    "視覚的に表現された図形や画像、またはコンピュータで扱われる画像全般を指す語。",
    "人が座るための場所。座席。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
        "何かを、中に取り込むこと。",
        "学校の建物。校舎は、授業や活動が行われる建物です。",
        "伙伴 —— 一起做同一件事、同属一个团体的人"
      ],
      "correct_answer": "ある目的を達成するために、順序立てて行われる一連の動作や操作。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35227, difficulty None)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "correct_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "options": [
    "相手に物や情報などを渡すこと。",
    "本。書物。文字や絵が印刷された、綴じた紙の集まり。",
    "人や物を車や電車などの上にのせること。",
    "ある目的を達成するために、順序立てて行われる一連の動作や操作。"
  ]
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "tier": "T6",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
        "官民",
        "use; to utilize — using an item or service for a certain purpose",
        "病気や悪いことが、どんどん広がること。"
      ],
      "correct_answer": "ある目的を達成するために、順序立てて行われる一連の動作や操作。"
    }
  }
}
```

---

## sense 35227, level 3

#### Pack A
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "真実を解き明かすための静謐かつ論理的な___こそが、指紋分析の真髄と言えるでしょう。",
  "original_sentence": "真実を解き明かすための静謐かつ論理的なプロセスこそが、指紋分析の真髄と言えるでしょう。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "お祭り騒ぎ",
    "パーティー",
    "ジャケット"
  ],
  "explanation": "「静謐かつ論理的な」に続き、真実を解き明かすための一連の手順を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "sentence_with_blank": "この___を踏むことで、成功することができます。",
  "original_sentence": "このプロセスを踏むことで、成功することができます。",
  "correct_answer": "プロセス",
  "options": [
    "消しゴム",
    "スプーン",
    "台風",
    "プロセス"
  ],
  "explanation": "「学ぶ」に続き、学習が進む一連の過程を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

#### Pack B
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___です。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "シンボル",
    "アイデア",
    "ルール"
  ],
  "explanation": "正解です。文脈に合う適切な名詞です。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___の結果が出ました。",
  "original_sentence": "プロセスの結果が出ました。",
  "correct_answer": "プロセス",
  "options": [
    "消しゴム",
    "プロセス",
    "スプーン",
    "台風"
  ],
  "explanation": "「学ぶ」に続き、学習が進む一連の過程を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

---

## sense 35227, level 4

#### Pack A
### Level 4 (sense 35227, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "再生可能エネルギーの導入加速にもかかわらず、製造___の性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
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
  "sentence_with_blank": "___を経て成長します。",
  "original_sentence": "プロセスを経て成長します。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
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
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "プロセス___経て成長します。",
  "original_sentence": "プロセスを経て成長します。",
  "options": [
    "を",
    "が",
    "で",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "プロセス",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「経る」の直接目的語を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35227, difficulty None)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___です。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
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
**particle_selection** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行___意味する重要なプロセスです。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "options": [
    "で",
    "に",
    "が",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "プロセス",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「意味する」の直接目的語を標示する"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___が長くて疲れてしまいます。",
  "original_sentence": "プロセスが長くて疲れてしまいます。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
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
**particle_selection** variant `B`, tier `T6`
```json
{
  "sentence_with_blank": "プロセス___長くて疲れてしまいます。",
  "original_sentence": "プロセスが長くて疲れてしまいます。",
  "options": [
    "を",
    "で",
    "が",
    "に"
  ],
  "correct_answer": "が",
  "target_word": "プロセス",
  "error_tags": {
    "を": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "形容詞「長い」の対象を主格で標示する"
    }
  }
}
```

---

## sense 35227, level 6

#### Pack A
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスをだ。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えます。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": false
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスについてだ。",
      "is_correct": false
    }
  ],
  "explanation": "語域：基礎例文は「意味する重要なプロセスです」という丁寧な表現（語域）ですが、この文は「だ」という常体（だ・である調）になっており、文体の丁寧度が一致していません。 語順・係り受けの誤り：「〜を意味する重要なプロセスについてだ」とすると、文全体が「〜について（説明・言及する）」という主題提示の構造になり、「これは〜プロセスです」というイコールの関係が崩れて意味が通りません。 助詞の混同：「重要なプロセスをだ」とはなりません。名詞を提示して断定する場合は「が」または「は」を使い、「を」は目的語を作る格助詞なのでここでは誤りです。",
  "target_word": "プロセス"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "この作業は、二羽のプロセスに分けられる。",
      "is_correct": false
    },
    {
      "text": "新しいプロセスが生まれました。",
      "is_correct": true
    },
    {
      "text": "このプロセスは、もう完成してある。",
      "is_correct": false
    },
    {
      "text": "プロセスが見直せば、時間を減らせる。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：作業の段階を数えるのに鳥用の「羽」は使えない。正しくは「二つのプロセス」や「二段階のプロセス」である。 助詞の混同：「見直す」の対象は「を」で示すべきで、「が」では対象が主語扱いになり不自然になる。正しくは「プロセスを見直せば」である。 活用・アスペクトの誤り：「〜てある」は他動詞にしか接続できず、自動詞「完成する」には使えない。正しくは「完成している」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "手法",
    "結果",
    "手順",
    "作業"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "「過程」である目標語の語義に対し、その行き着く先である「結果」は対義関係にある。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "工場は新しい技術でプロセスが導入した。",
      "is_correct": false
    },
    {
      "text": "明日、私はそのプロセスを見直した。",
      "is_correct": false
    },
    {
      "text": "この製品は、三匹のプロセスを経て完成する。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：手順や段階を数えるのに動物用の「匹」は使えない。正しくは「三つのプロセス」や「三段階のプロセス」である。 助詞の混同：「導入する」の対象は「を」で示すべきで、「が」では主語になってしまい文が成り立たない。正しくは「プロセスを導入した」である。 活用・テンスの誤り：未来を表す「明日」と過去形の「た」が矛盾し、文として成立しない。正しくは「見直す」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "方法",
    "経過",
    "結果",
    "手順"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "過程に対する帰結を指し、目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "このプロセスは、もう完成してある。",
      "is_correct": false
    },
    {
      "text": "この作業は、二羽のプロセスに分けられる。",
      "is_correct": false
    },
    {
      "text": "プロセスが見直せば、時間を減らせる。",
      "is_correct": false
    },
    {
      "text": "正しいプロセスで問題を解くことができます。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：作業の段階を数えるのに鳥用の「羽」は使えない。正しくは「二つのプロセス」や「二段階のプロセス」である。 助詞の混同：「見直す」の対象は「を」で示すべきで、「が」では対象が主語扱いになり不自然になる。正しくは「プロセスを見直せば」である。 活用・アスペクトの誤り：「〜てある」は他動詞にしか接続できず、自動詞「完成する」には使えない。正しくは「完成している」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T6`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "経過",
    "結果",
    "手法",
    "手順"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "ある作用によって生じた事柄。順序立った動作そのものを指す「プロセス」の対義語となる。"
    }
  }
}
```

---
