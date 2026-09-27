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


## sense 35001, level 9

#### Pack A
### Level 9 (sense 35001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "この機械は簡単に操作できます。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は機械を修理できます。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は機械を修理できます。",
  "chunks": [
    "彼は",
    "機械を",
    "修理できます"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "彼は",
    "修理できます",
    "機械を"
  ],
  "target_word": "機械",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 35001, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "機械の",
    "使い方を",
    "教えて",
    "もらった"
  ],
  "chunk_count": 4,
  "target_word": "機械",
  "schema_version": 2,
  "shuffled_chunks": [
    "機械の",
    "もらった",
    "教えて",
    "使い方を"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "機械の使い方を教えてもらった。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "機械の使い方を教えてもらった。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "機械が",
    "壊れたの",
    "で修理を",
    "頼んだ"
  ],
  "chunk_count": 4,
  "target_word": "機械",
  "schema_version": 2,
  "shuffled_chunks": [
    "で修理を",
    "機械が",
    "壊れたの",
    "頼んだ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "機械が壊れたので修理を頼んだ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "機械が壊れたので修理を頼んだ。"
}
```

---

## sense 35009, level 1

#### Pack A
### Level 1 (sense 35009, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "様",
  "prompt": "様",
  "options": [
    "さま",
    "さまあ",
    "ざま",
    "さあま"
  ],
  "direction": "kanji_to_reading",
  "is_polyphonic": true,
  "context_target": "様",
  "correct_answer": "さま",
  "schema_version": 2,
  "context_sentence": "田中様、お電話です。"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "様",
  "prompt": "さま",
  "options": [
    "差",
    "美",
    "線",
    "様"
  ],
  "direction": "reading_to_kanji",
  "is_polyphonic": true,
  "context_target": "様",
  "correct_answer": "様",
  "schema_version": 2,
  "context_sentence": "田中様、お電話です。",
  "distractor_sources": {
    "差": "component",
    "線": "component",
    "美": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "ipa": "/sama/",
  "word": "様",
  "options": [
    "小夜",
    "様",
    "ハマ",
    "坂"
  ],
  "audio_url": null,
  "explanation": "正解です。「様」は「相手を敬って名前などに付ける敬称。」という意味です。",
  "pronunciation": "さま",
  "correct_answer": "様",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "坂": "「坂」は「様」と一モーラだけ異なる実在語です（2モーラ目: 「ま」→「か」、一部の音の違い）。",
    "ハマ": "「ハマ」は「様」と一モーラだけ異なる実在語です（1モーラ目: 「さ」→「は」、一部の音の違い）。",
    "小夜": "「小夜」は「様」と一モーラだけ異なる実在語です（2モーラ目: 「ま」→「よ」、一部の音の違い）。"
  }
}
```

#### Pack B
### Level 1 (sense 35009, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "様",
  "options": [
    "さま",
    "さまあ",
    "ざま",
    "さあま"
  ],
  "correct_answer": "さま",
  "word": "様",
  "direction": "kanji_to_reading",
  "context_sentence": "お客様が待っています。",
  "context_target": "様",
  "is_polyphonic": true
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "さま",
  "options": [
    "差",
    "美",
    "線",
    "様"
  ],
  "correct_answer": "様",
  "word": "様",
  "direction": "reading_to_kanji",
  "context_sentence": "お客様が待っています。",
  "context_target": "様",
  "is_polyphonic": true,
  "distractor_sources": {
    "線": "component",
    "美": "component",
    "差": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "様",
  "pronunciation": "さま",
  "ipa": "[sama]",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "様",
    "坂",
    "三",
    "里"
  ],
  "correct_answer": "様",
  "explanation": "正解です。「様」は「「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。」という意味です。",
  "distractor_explanations": {
    "坂": "「坂」は「様」と一モーラだけ異なる実在語です（2モーラ目: 「ま」→「か」、一部の音の違い）。",
    "里": "「里」は「様」と一モーラだけ異なる実在語です（2モーラ目: 「ま」→「と」、一部の音の違い）。",
    "三": "「三」は「様」と一モーラだけ異なる実在語です（2モーラ目: 「ま」→「ん」、撥音「ん」の有無）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35009, level 2

#### Pack A
### Level 2 (sense 35009, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "様",
  "pronunciation": "さま",
  "correct_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "options": [
    "14世紀から16世紀にかけてヨーロッパで起こった、古代ギリシャ・ローマの文化を復興し、新しい学問や芸術が発展した時代。",
    "ある程度の時間が経過すること。行動や出来事の間に少し間があることを表す副詞。",
    "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
    "複数の人や組織が互いに協力して、目的を達成するために行動を合わせること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "様",
  "pronunciation": "さま",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "周囲より高く盛り上がった地形。多くの場合、頂上や斜面がある。",
        "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
        "何かができるようになること。",
        "to manifest"
      ],
      "correct_answer": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35009, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "様",
  "options": [
    "物や人を、ある場所にどのように置いたり、並べたりするかという、そのときの位置や並べ方の計画。",
    "普通とは違う、不快なにおい。",
    "相手を敬って名前などに付ける敬称。",
    "仮定の条件を示す接続詞。現実とは異なる事柄を仮定したり、可能性が低いことを想定したりする際に用いる。"
  ],
  "pronunciation": "さま",
  "correct_definition": "相手を敬って名前などに付ける敬称。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "コンピュータやテレビなどで遊ぶ、楽しい活動です。",
        "ある目的のために、積極的に行動する。また、仕事をする。",
        "とても、という意味。",
        "相手を敬って名前などに付ける敬称。"
      ],
      "correct_answer": "相手を敬って名前などに付ける敬称。"
    }
  },
  "tier": "T3",
  "word": "様",
  "pronunciation": "さま",
  "schema_version": 2
}
```

---

## sense 35009, level 3

#### Pack A
### Level 3 (sense 35009, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "お客___が待っています。",
  "original_sentence": "お客様が待っています。",
  "correct_answer": "お客様",
  "options": [
    "方",
    "お客様",
    "さん",
    "殿"
  ],
  "explanation": "正解です。「様」は相手を敬って呼ぶ接尾辞として自然です。",
  "distractor_tags": {},
  "word_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "target_word": "様"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "お母___が作ってくれました。",
  "original_sentence": "お母様が作ってくれました。",
  "correct_answer": "様",
  "options": [
    "様",
    "ちゃん",
    "殿",
    "氏"
  ],
  "explanation": "正解です。「様」は相手を敬って呼ぶ接尾辞で、「お母様」として自然な尊敬表現になります。",
  "distractor_tags": {},
  "word_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "target_word": "様"
}
```

#### Pack B
### Level 3 (sense 35009, difficulty 5)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "options": [
    "石",
    "犬",
    "机",
    "様"
  ],
  "explanation": "敬称として自然に使う語。",
  "target_word": "様",
  "correct_answer": "様",
  "distractor_tags": {},
  "word_definition": "相手を敬って名前などに付ける敬称。",
  "original_sentence": "田中様、お電話です。",
  "sentence_with_blank": "田中___、お電話です。"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "石",
    "犬",
    "様",
    "机"
  ],
  "explanation": "敬称として自然に使う語。",
  "target_word": "様",
  "correct_answer": "様",
  "distractor_tags": {},
  "word_definition": "相手を敬って名前などに付ける敬称。",
  "original_sentence": "ご来場の皆様、ありがとうございます。",
  "sentence_with_blank": "ご来場の皆___、ありがとうございます。"
}
```

---

## sense 35009, level 7

#### Pack A
### Level 7 (sense 35009, difficulty 5)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "山田様からお手紙が届いた。",
      "is_correct": true
    },
    {
      "text": "田中様、お電話です。",
      "is_correct": true
    },
    {
      "text": "お客様、少々お待ちください。",
      "is_correct": true
    },
    {
      "text": "佐藤様はもうお帰りにになった。",
      "is_correct": false,
      "error_description": "尊敬語「お帰りになる」の形が誤っている（「に」が重複している）。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "田中様は、お電話です。",
      "is_correct": false,
      "error_description": "呼びかけの後に助詞「は」を入れる必要はない。直接呼びかける形が自然。"
    },
    {
      "text": "木村様にご案内します。",
      "is_correct": true
    },
    {
      "text": "ご来場の皆様、ありがとうございます。",
      "is_correct": true
    },
    {
      "text": "王様が城に住んでいる。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35009, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "お母様が作ってくれました。",
      "is_correct": true
    },
    {
      "text": "お客様のお話を聞いています。",
      "is_correct": true
    },
    {
      "text": "お客様をお茶を出して。",
      "is_correct": false,
      "error_description": "「お客様」は動作の受け手（対象）であるため、助詞「に」を使う必要があります。「を」を使うと、「お客様」が「お茶」を出す動作の主語になってしまい、文法的に誤りです。"
    },
    {
      "text": "皆様、少し休んでください。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "増え",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "correct_answer": "ふえる",
  "word": "増え",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "[ɸɯeɾɯ]",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "断える",
    "フリル",
    "増える",
    "越える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "越える": "「越える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「こ」、一部の音の違い）。",
    "フリル": "「フリル」は「増える」と一モーラだけ異なる実在語です（2モーラ目: 「え」→「り」、一部の音の違い）。",
    "断える": "「断える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "ふえる",
  "options": [
    "調理",
    "増え",
    "重量",
    "増える"
  ],
  "correct_answer": "増え",
  "word": "増え",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "増える": "homophone",
    "重量": "component",
    "調理": "component"
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
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "数量や回数が非常に多いこと。",
    "投資や仕事などで、複数の資産や作品を組み合わせた集まり。リスクを分散するために、異なる種類のものをバランスよく持つこと。",
    "数量や程度が多くなる。",
    "ある期間の中で、終わりに近い部分。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "小さくて丸い形をしたもの。また、そのような形をした一つ一つのもの。",
        "关注 —— 把注意力特别集中在某件事或某种现象上加以思考",
        "元素の一つ。原子番号6、記号C。すべての有機物の基本となる元素で、ダイヤモンドや黒鉛、二酸化炭素など様々な形で存在する。",
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
### Level 4 (sense 35017, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "最近、犬を飼う人が___ています。",
  "original_sentence": "最近、犬を飼う人が増えています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
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
**morphology_slot** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "最近、犬を飼う人が___ています。",
  "original_sentence": "最近、犬を飼う人が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形",
  "options": [
    "増えない",
    "増えた",
    "増え",
    "増える"
  ],
  "explanation": "「います」に接続するため連用形が必要",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___ない友達の数を心配しています。",
  "original_sentence": "増えない友達の数を心配しています。",
  "target_word": "増え",
  "word": "増え",
  "answer": {
    "accepted": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
    ],
    "accepted_normalized": [
      "増え",
      "増えた",
      "増えて",
      "増えない",
      "増えられない"
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
**morphology_slot** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___ない友達の数を心配しています。",
  "original_sentence": "増えない友達の数を心配しています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "未然形",
  "options": [
    "増え",
    "増えた",
    "増える",
    "増えて"
  ],
  "explanation": "後ろの否定の助動詞「ない」に接続する未然形として正しい。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
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

---

## sense 35017, level 6

#### Pack A
### Level 6 (sense 35017, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースが増えたあります。",
      "is_correct": false
    },
    {
      "text": "古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースに増えています。",
      "is_correct": false
    },
    {
      "text": "しかし、古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースも増えています。",
      "is_correct": true
    },
    {
      "text": "増えている古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースもあります。",
      "is_correct": false
    }
  ],
  "explanation": "語順・係り受けの誤り：「増えている」が「古い建物」にかかってしまい、建物の数が増えているという不自然な意味になっています。 助詞の混同：「ケースに増えています」は誤りです。数量の増加の対象を示す場合は「ケースが」を使います。 活用・アスペクトの誤り：「増えたあります」は文法的に誤りです。状態の継続を表すなら「増えています」が適切です。",
  "target_word": "増え"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "ゴミが一本増えました。",
      "is_correct": false
    },
    {
      "text": "良い点が取れて、自信が増えてきました。",
      "is_correct": true
    },
    {
      "text": "自信が増えてある。",
      "is_correct": false
    },
    {
      "text": "私は自信を増えました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「ゴミ」は「本」で数えない。 助詞の混同：「増える」は自動詞なので、対象を示すのに「を」ではなく「が」を使う。 活用・アスペクトの誤り：「てある」は他動詞の動作の結果の状態に使うため、自動詞の「増える」には使えない。",
  "target_word": "増え"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "増え",
  "relation": "antonym",
  "options": [
    "保ち",
    "変わり",
    "減り",
    "伸び"
  ],
  "correct_answer": "減り",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "数量や程度が多くなる。",
      "explanation": "数量や程度が少なくなることを表す対義語である"
    }
  }
}
```

#### Pack B
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

---

## sense 35017, level 7

#### Pack A
### Level 7 (sense 35017, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "最近、体重が増えてきた。",
      "is_correct": true
    },
    {
      "text": "車の数が年々増えいる。",
      "is_correct": false,
      "error_description": "「～ている」の形で「て」が抜けている誤り。"
    },
    {
      "text": "人口がどんどん増えている。",
      "is_correct": true
    },
    {
      "text": "しかし、その無骨な外観や維持管理の難しさから、現在ではその価値が再評価される一方で、取り壊されるケースも増えています。",
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
      "text": "病気になる人が増えている。",
      "is_correct": true
    },
    {
      "text": "しかし、その無骨な外観や維持管理の難しさから、現在ではその価値が再評価される一方で、取り壊されるケースも増えいます。",
      "is_correct": false,
      "error_description": "「～ています」の「て」が抜けている誤り。"
    },
    {
      "text": "雨で川の水が増えた。",
      "is_correct": true
    },
    {
      "text": "貯金が少しずつ増えてきた。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "最近、犬を飼う人が増えています。",
      "is_correct": true
    },
    {
      "text": "しかし、古い建物は直すのが難しいため、現在ではその価値が見直される一方で、壊されるケースも増えています。",
      "is_correct": true
    },
    {
      "text": "テストの点が少し増えました。",
      "is_correct": true
    },
    {
      "text": "最近、犬を飼う人に増えています。",
      "is_correct": false,
      "error_description": "「増える」は自動詞であり、変化する主体を示す助詞は「が」を使います。「に」を使うのは誤りです。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "増えない友達の数を心配しています。",
      "is_correct": true
    },
    {
      "text": "良い点が取れて、自信が増えてきました。",
      "is_correct": true
    },
    {
      "text": "日本の人口を増えています。",
      "is_correct": false,
      "error_description": "「増える」は自動詞であり、増加する主体を示す助詞は「を」ではなく「が」です。「を」を使う場合は他動詞の「増やす」を用います。"
    },
    {
      "text": "これ以上は負担が増えませんように。",
      "is_correct": true
    }
  ]
}
```

---
