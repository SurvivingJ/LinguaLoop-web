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


## sense 35001, level 7

#### Pack A
### Level 7 (sense 35001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私たちは機械の音を聞いています。",
      "is_correct": true
    },
    {
      "text": "私たちは機械の音を聞きます。",
      "is_correct": false,
      "error_description": "原文は進行形・状態を表す「ています」ですが、誤文では習慣や未来を表す「ます」になっており、文脈（現在進行中の行為）と一致しません。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "大きな機械が部屋へ入ります。",
      "is_correct": false,
      "error_description": "原文は存在や移動の結果としての状態変化を含む文脈で「に」が使われていますが、誤文の「へ」は方向性を強調し、室内に入るという結果よりも過程や方向を示唆するため、文脈的にやや不自然、または原文との厳密な一致から外れます。（※注：実際には「へ」も文法的に許容され得ますが、L7の誤文発見として「原文との差異」および「入室という結果焦点」の観点から誤りと設定します）"
    },
    {
      "text": "大きな機械が部屋に入ります。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35001, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "工場には大きな機械がたくさんある。",
      "is_correct": true
    },
    {
      "text": "この機械は自動で動いている。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "新しい機械が工場に入れた。",
      "is_correct": false,
      "error_description": "他動詞「入れた」の対象を表す「を」を使うべきところを「が」にしている誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "機械を止めてから掃除をする。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械が操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": false,
      "error_description": "「機械を操作する」（機械を対象とする）を「機械が操作する」（機械が主体になる）に誤って変えている。"
    },
    {
      "text": "農業でも機械が使われている。",
      "is_correct": true
    },
    {
      "text": "機械のおかげで作業が早くなった。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35001, level 9

#### Pack A
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

#### Pack B
### Level 9 (sense 35001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "私たちは機械の音を聞いています。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "私たちは機械の音を聞いています。",
  "chunks": [
    "私たちは",
    "機械の",
    "音を",
    "聞いて",
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
    "機械の",
    "私たちは",
    "音を",
    "聞いて"
  ],
  "target_word": "機械",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "その機械はとても静かです。"
}
```

---

## sense 35009, level 1

#### Pack A
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
  "context_sentence": "ご来店のお客様は、皆様に心より感謝申し上げます。",
  "context_target": "よう",
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
  "context_sentence": "ご来店のお客様は、皆様に心より感謝申し上げます。",
  "context_target": "よう",
  "is_polyphonic": true,
  "distractor_sources": {
    "線": "component",
    "美": "component",
    "差": "component"
  }
}
```

#### Pack B
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

---

## sense 35009, level 2

#### Pack A
### Level 2 (sense 35009, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "よう",
  "pronunciation": "さま",
  "correct_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "options": [
    "物や知識などを少しずつ集めて、たくさんにすること。また、その集まったもの。",
    "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
    "物事が起こったり、存在するようになったりするもと。",
    "食べ物をはさんで口に運ぶための細長い道具。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "よう",
  "pronunciation": "さま",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "もうけ。お金が増えること。",
        "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
        "位置や程度が、高い状態から低い状態に変わること。",
        "saltiness"
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

#### Pack B
### Level 3 (sense 35009, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "ご来店のお客様は、皆様に心より感謝申し上げます。",
  "original_sentence": "ご来店のお客様は、皆様に心より感謝申し上げます。",
  "correct_answer": "様",
  "options": [
    "君",
    "氏",
    "殿",
    "様"
  ],
  "explanation": "正解。相手を敬って呼ぶ接尾語です。",
  "distractor_tags": {},
  "word_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "target_word": "よう"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "鈴木___からの荷物が届いています。",
  "original_sentence": "鈴木様からの荷物が届いています。",
  "correct_answer": "様",
  "options": [
    "君",
    "殿",
    "様",
    "氏"
  ],
  "explanation": "正解。相手を敬って呼ぶ接尾語です。",
  "distractor_tags": {},
  "word_definition": "「様（さま）」は、相手を敬って呼ぶときの接尾語です。「お客様」のように使います。",
  "target_word": "様"
}
```

---

## sense 35011, level 1

#### Pack A
### Level 1 (sense 35011, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "発明",
  "options": [
    "ばつめい",
    "ぱつめい",
    "はづめい",
    "はつめい"
  ],
  "correct_answer": "はつめい",
  "word": "発明",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "はつめい",
  "options": [
    "発見",
    "発明",
    "発生",
    "開発"
  ],
  "correct_answer": "発明",
  "word": "発明",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "開発": "component",
    "発見": "component",
    "発生": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35011, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "prompt": "発明",
  "options": [
    "ばつめい",
    "ぱつめい",
    "はづめい",
    "はつめい"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "はつめい",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "/hatsɯmeː/",
  "word": "発明",
  "options": [
    "初恋",
    "説明",
    "物名",
    "発明"
  ],
  "audio_url": null,
  "explanation": "正解です。「発明」は「新しい物や方法を考え出すこと。」という意味です。",
  "pronunciation": "はつめい",
  "correct_answer": "発明",
  "syllable_count": 4,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "初恋": "「初恋」は「発明」と一モーラだけ異なる実在語です（3モーラ目: 「め」→「こ」、一部の音の違い）。",
    "物名": "「物名」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「ぶ」、一部の音の違い）。",
    "説明": "「説明」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「せ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "prompt": "はつめい",
  "options": [
    "発見",
    "発明",
    "発生",
    "開発"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "発明",
  "schema_version": 2,
  "distractor_sources": {
    "発生": "component",
    "発見": "component",
    "開発": "component"
  }
}
```

---

## sense 35011, level 2

#### Pack A
### Level 2 (sense 35011, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "物や人に何かを加えたり、取り付けたりすること。",
        "independence; to be self-reliant — doing things by one's own strength, without depending on others",
        "新しい物や方法を考え出すこと。",
        "东南"
      ],
      "correct_answer": "新しい物や方法を考え出すこと。"
    }
  },
  "tier": "T3",
  "word": "発明",
  "pronunciation": "はつめい",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "options": [
    "「作る」という動詞に、可能や受け身の意味を持つ「れる」と、丁寧な過去を表す「ます」と「た」が組み合わさった形です。主に「作られる」という可能や受け身の意味で使われます。",
    "空気中などに存在する微生物のうち、特に衛生上問題となるものを指す。食べ物を腐らせたり、病気の原因になることがある。",
    "目的を達成するために用いる具体的な方法や、そのための設備や道具。",
    "新しい物や方法を考え出すこと。"
  ],
  "pronunciation": "はつめい",
  "correct_definition": "新しい物や方法を考え出すこと。"
}
```

#### Pack B
### Level 2 (sense 35011, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "correct_definition": "新しいものや方法を考え出して、実際に作ること。",
  "options": [
    "新しいものや方法を考え出して、実際に作ること。",
    "他の人に言われなくても、自分の意志で行動すること。",
    "庭やプランターで植物を育て、お手入れをする趣味や仕事のことです。",
    "ある物事を基礎や根拠として、それに従って行動する、または成り立つこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "分析",
        "新しいものや方法を考え出して、実際に作ること。",
        "神经",
        "今后 —— 从现在开始往后的时间或事情，即将来"
      ],
      "correct_answer": "新しいものや方法を考え出して、実際に作ること。"
    }
  }
}
```

---

## sense 35011, level 3

#### Pack A
### Level 3 (sense 35011, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼は新しい電池を___した。",
  "original_sentence": "彼は新しい電池を発明した。",
  "correct_answer": "発明",
  "options": [
    "開発",
    "発明",
    "発見",
    "創造"
  ],
  "explanation": "正解。「新しいものや方法を考え出して作ること」であり、文脈に適合します。",
  "distractor_tags": {},
  "word_definition": "新しいものや方法を考え出して、実際に作ること。",
  "target_word": "発明"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "私たちは未来の技術を___できる。",
  "original_sentence": "私たちは未来の技術を発明できる。",
  "correct_answer": "発明",
  "options": [
    "発見",
    "輸入",
    "学習",
    "発明"
  ],
  "explanation": "正解。「未来の技術を考え出して作ること」であり、文脈に適合します。",
  "distractor_tags": {},
  "word_definition": "新しいものや方法を考え出して、実際に作ること。",
  "target_word": "発明"
}
```

#### Pack B
### Level 3 (sense 35011, difficulty 5)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "options": [
    "見学",
    "発明",
    "予約",
    "発言"
  ],
  "explanation": "文脈（新しい機械を～する）に合う正しい語。",
  "target_word": "発明",
  "correct_answer": "発明",
  "distractor_tags": {},
  "word_definition": "新しい物や方法を考え出すこと。",
  "original_sentence": "彼は新しい機械を発明した。",
  "sentence_with_blank": "彼は新しい機械を___した。"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "発言",
    "見学",
    "予約",
    "発明"
  ],
  "explanation": "文脈に合う正しい語。",
  "target_word": "発明",
  "correct_answer": "発明",
  "distractor_tags": {},
  "word_definition": "新しい物や方法を考え出すこと。",
  "original_sentence": "昔の人々もいろいろな発明をした。",
  "sentence_with_blank": "昔の人々もいろいろな___をした。"
}
```

---

## sense 35011, level 4

#### Pack A
### Level 4 (sense 35011, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "その___は世界を変えた。",
  "original_sentence": "その発明は世界を変えた。",
  "target_word": "発明",
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明する",
      "発明家",
      "発明品"
    ],
    "accepted_normalized": [
      "発明",
      "発明する",
      "発明家",
      "発明品"
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
  "sentence_with_blank": "その発明___世界を変えた。",
  "original_sentence": "その発明は世界を変えた。",
  "options": [
    "と",
    "は",
    "を",
    "に"
  ],
  "correct_answer": "は",
  "target_word": "発明",
  "error_tags": {
    "を": "",
    "に": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。主題を示す助詞として自然です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "その___は多くの人を助けた。",
  "original_sentence": "その発明は多くの人を助けた。",
  "target_word": "発明",
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明する",
      "発明家",
      "発明品"
    ],
    "accepted_normalized": [
      "発明",
      "発明する",
      "発明家",
      "発明品"
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
  "sentence_with_blank": "その発明___多くの人を助けた。",
  "original_sentence": "その発明は多くの人を助けた。",
  "options": [
    "に",
    "は",
    "と",
    "を"
  ],
  "correct_answer": "は",
  "target_word": "発明",
  "error_tags": {
    "を": "",
    "に": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。主題を示す助詞として自然です。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35011, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明品",
      "発明者",
      "発明家",
      "発明する"
    ],
    "accepted_normalized": [
      "発明",
      "発明品",
      "発明者",
      "発明家",
      "発明する"
    ]
  },
  "input_mode": "ime",
  "target_word": "発明",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "この発明のおかげで生活が便利になった。",
  "sentence_with_blank": "この___のおかげで生活が便利になった。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明品",
      "発明者",
      "発明家",
      "発明する"
    ],
    "accepted_normalized": [
      "発明",
      "発明品",
      "発明者",
      "発明家",
      "発明する"
    ]
  },
  "input_mode": "ime",
  "target_word": "発明",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "その発明はまだ広まっていない。",
  "sentence_with_blank": "その___はまだ広まっていない。"
}
```

---

## sense 35011, level 6

#### Pack A
### Level 6 (sense 35011, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "発明が笑った。",
      "is_correct": false
    },
    {
      "text": "発明を食べた。",
      "is_correct": false
    },
    {
      "text": "電球の発明は世界を変えた。",
      "is_correct": true
    },
    {
      "text": "発明が泳いでいる。",
      "is_correct": false
    }
  ],
  "explanation": "抽象的な概念である「発明」が泳ぐことはない。 「発明」というアイデアを食べることはできない。 「発明」が笑うことはない。",
  "target_word": "発明"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "新しい発明が次々と生まれている。",
      "is_correct": true
    },
    {
      "text": "発明を切った。",
      "is_correct": false
    },
    {
      "text": "発明が赤く光った。",
      "is_correct": false
    },
    {
      "text": "発明を三個買った。",
      "is_correct": false
    }
  ],
  "explanation": "抽象的なアイデアを個数で買うことはできない。 「発明」自体が光ることはない。 アイデアを物理的に切ることはできない。",
  "target_word": "発明"
}
```

#### Pack B
### Level 6 (sense 35011, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "発明から創造力が必要だ。",
      "is_correct": false
    },
    {
      "text": "発明には創造力がいるだ。",
      "is_correct": false
    },
    {
      "text": "発明へは創造力が必要だ。",
      "is_correct": false
    },
    {
      "text": "発明には創造力が必要だ。",
      "is_correct": true
    }
  ],
  "explanation": "誤答。形容動詞や名詞述語の否定・断定ではなく、存在を表す文型として不自然です。また『いる』の主語は通常生物です。 誤答。対象や方向を示す『へ』は、必要性の対象である『発明』には不適切で、『に』または『には』が適切です。 誤答。起点を示す『から』は、必要性の根拠としては不自然です。",
  "target_word": "発明"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼女は優れた発明がいる。",
      "is_correct": false
    },
    {
      "text": "彼女は優れた発明をしました。",
      "is_correct": true
    },
    {
      "text": "彼女は優れた発明からした。",
      "is_correct": false
    },
    {
      "text": "彼女は優れた発明へした。",
      "is_correct": false
    }
  ],
  "explanation": "誤答。所有や属性を表す文で「いる」を使うのは不自然です。 誤答。動作の結果や対象を示すのに「へ」は不適切です。 誤答。動作の起点を示す「から」は、この文脈では意味をなしません。",
  "target_word": "発明"
}
```

---
