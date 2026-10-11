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


## sense 35055, level 1

#### Pack A
### Level 1 (sense 35055, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "世界",
  "options": [
    "せいかい",
    "せがい",
    "せかい",
    "ぜかい"
  ],
  "correct_answer": "せかい",
  "word": "世界",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "せかい",
  "options": [
    "世界",
    "限界",
    "境界",
    "大量"
  ],
  "correct_answer": "世界",
  "word": "世界",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "限界": "component",
    "境界": "component",
    "大量": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35055, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "prompt": "世界",
  "options": [
    "せいかい",
    "せがい",
    "せかい",
    "ぜかい"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "せかい",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "sekai",
  "word": "世界",
  "options": [
    "樹海",
    "世界",
    "世代",
    "不快"
  ],
  "audio_url": null,
  "explanation": "正解です。「世界」は「地球全体。また、人間の活動の及ぶすべての範囲。社会全体。」という意味です。",
  "pronunciation": "せかい",
  "correct_answer": "世界",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "不快": "「不快」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「ふ」、一部の音の違い）。",
    "世代": "「世代」は「世界」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「だ」、一部の音の違い）。",
    "樹海": "「樹海」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「じゅ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "prompt": "せかい",
  "options": [
    "世界",
    "限界",
    "境界",
    "大量"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "世界",
  "schema_version": 2,
  "distractor_sources": {
    "境界": "component",
    "大量": "component",
    "限界": "component"
  }
}
```

---

## sense 35055, level 2

#### Pack A
### Level 2 (sense 35055, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "correct_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "options": [
    "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
    "二つのものが順番に現れたり、置かれたりすること。",
    "他の人のやり方や考え方、行動などをまねて、同じようにすること。",
    "ある目的のために、体や道具を使って物事を行うこと。特に、仕事や活動として取り組むこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "吃（了）—— 表示吃这个动作的持续、并列或理由等的连接形式",
        "结果实（结实）",
        "dependence; to depend on — not being able to function fully alone, relying on something else",
        "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
      ],
      "correct_answer": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35055, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "to leave behind",
        "appellation",
        "城墙 —— 为了保护城市或城堡而建造的高大石墙或砖墙",
        "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
      ],
      "correct_answer": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
    }
  },
  "tier": "T3",
  "word": "世界",
  "pronunciation": "せかい",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "options": [
    "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
    "国や地域の政治を行う組織。法律や税金、外交など、社会全体のルールを決めたり、公共のサービスを提供したりする仕組み。",
    "木版印刷に用いる、表面に文字や絵を彫った木の板。",
    "浮き世とは、はかない現世、または世の中のことを指します。特に江戸時代の文化では、遊びや楽しみを重視する世界観を表しました。"
  ],
  "pronunciation": "せかい",
  "correct_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。"
}
```

---

## sense 35055, level 3

#### Pack A
### Level 3 (sense 35055, difficulty 5)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "値段",
    "世界",
    "宿題",
    "机"
  ],
  "explanation": "「世界を旅する」で、地球上のさまざまな場所を旅する意味になり、文脈に合います。",
  "target_word": "世界",
  "correct_answer": "世界",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "original_sentence": "弟は世界を旅する仕事に興味があります。",
  "sentence_with_blank": "弟は___を旅する仕事に興味があります。"
}
```

#### Pack B
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼は___を旅して回りました。",
  "original_sentence": "彼は世界を旅して回りました。",
  "correct_answer": "世界",
  "options": [
    "環境",
    "宇宙",
    "世界",
    "地域"
  ],
  "explanation": "文脈に適合：地球全体や社会全体を指す。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "インターネットで___のニュースを見ます。",
  "original_sentence": "インターネットで世界のニュースを見ます。",
  "correct_answer": "世界",
  "options": [
    "天気",
    "世界",
    "机",
    "部屋"
  ],
  "explanation": "文脈に適合：多くの人々、グローバルな範囲を指す。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```

---

## sense 35055, level 4

#### Pack A
### Level 4 (sense 35055, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この問題は___中で議論されています。",
  "original_sentence": "この問題は世界中で議論されています。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
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
  "sentence_with_blank": "この問題は世界中___議論されています。",
  "original_sentence": "この問題は世界中で議論されています。",
  "options": [
    "と",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "で",
  "target_word": "世界",
  "error_tags": {
    "を": "",
    "に": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "動作が行われる範囲・場所を示す助詞として自然。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "平和な___を作るのは難しいことです。",
  "original_sentence": "平和な世界を作るのは難しいことです。",
  "target_word": "世界",
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界一",
      "世界観"
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
### Level 4 (sense 35055, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界的",
      "世界観",
      "世界地図"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界的",
      "世界観",
      "世界地図"
    ]
  },
  "input_mode": "ime",
  "target_word": "世界",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "現実的な設計図とは異なるが、その絵には彼が求める理想の世界が詰まっている。",
  "sentence_with_blank": "現実的な設計図とは異なるが、その絵には彼が求める理想の___が詰まっている。"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "「理想」が後ろの名詞「世界」を修飾する連体修飾の「の」である"
    }
  },
  "options": [
    "に",
    "を",
    "へ",
    "の"
  ],
  "error_tags": {
    "に": "location_vs_target",
    "へ": "direction",
    "を": "object_marking"
  },
  "target_word": "世界",
  "correct_answer": "の",
  "schema_version": 2,
  "original_sentence": "現実的な設計図とは異なるが、その絵には彼が求める理想の世界が詰まっている。",
  "sentence_with_blank": "現実的な設計図とは異なるが、その絵には彼が求める理想___世界が詰まっている。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "世界",
  "answer": {
    "accepted": [
      "世界",
      "世界中",
      "世界的",
      "世界観",
      "世界地図"
    ],
    "accepted_normalized": [
      "世界",
      "世界中",
      "世界的",
      "世界観",
      "世界地図"
    ]
  },
  "input_mode": "ime",
  "target_word": "世界",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "平和な世界をつくるために、勉強します。",
  "sentence_with_blank": "平和な___をつくるために、勉強します。"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "他動詞「つくる」の直接目的語「平和な世界」を標示する"
    }
  },
  "options": [
    "と",
    "へ",
    "を",
    "に"
  ],
  "error_tags": {
    "と": "listing",
    "に": "location_vs_target",
    "へ": "direction"
  },
  "target_word": "世界",
  "correct_answer": "を",
  "schema_version": 2,
  "original_sentence": "平和な世界をつくるために、勉強します。",
  "sentence_with_blank": "平和な世界___つくるために、勉強します。"
}
```

---

## sense 35055, level 6

#### Pack A
### Level 6 (sense 35055, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界には、国が三匹あります。",
      "is_correct": false
    },
    {
      "text": "世界には、たくさんの国があります。",
      "is_correct": true
    },
    {
      "text": "世界を、たくさんの国があります。",
      "is_correct": false
    },
    {
      "text": "世界には、たくさんのがあります国。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：国を数えるときは「三匹」ではなく「三つ」や「三か国」を使います。「匹」は小さな動物に使う助数詞です。 助詞の混同：存在を表す「ある」の場所は「に」で示すので、「世界を」は誤りです。正しくは「世界には」です。 語順・係り受けの誤り：「たくさんの」が修飾する名詞を失い、「国」が述語の後に取り残されて係り受けが壊れています。",
  "target_word": "世界"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "テレビで様子を世界の知ることができます。",
      "is_correct": false
    },
    {
      "text": "テレビで世界の様子を知ったことができます。",
      "is_correct": false
    },
    {
      "text": "テレビで世界の様子を知ることができます。",
      "is_correct": true
    },
    {
      "text": "テレビに世界の様子を知ることができます。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：手段を表す「で」を「に」に取り違えています。正しくは「テレビで」です。 活用・アスペクトの誤り：「ことができる」の前は辞書形にするので、「知った」ではなく「知る」が正しい形です。 語順・係り受けの誤り：「世界の」が「様子」から切り離され、修飾する名詞を失って係り受けが壊れています。",
  "target_word": "世界"
}
```

#### Pack B
### Level 6 (sense 35055, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この本は世界の人々に走られています。",
      "is_correct": false
    },
    {
      "text": "この本は世界の人々に泳がれています。",
      "is_correct": false
    },
    {
      "text": "この本は世界の人々に読まれています。",
      "is_correct": true
    },
    {
      "text": "この本は世界の人々に飲まれています。",
      "is_correct": false
    }
  ],
  "explanation": "本は「走る」という動作を行わない。 本は「飲む」という動作の対象にはなり得ない。 本は「泳ぐ」という動作を行わない。",
  "target_word": "世界"
}
```

---

## sense 35055, level 9

#### Pack A
### Level 9 (sense 35055, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "世界で",
    "一番高い山に",
    "登りたいです"
  ],
  "chunk_count": 3,
  "target_word": "世界",
  "schema_version": 2,
  "shuffled_chunks": [
    "一番高い山に",
    "世界で",
    "登りたいです"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "世界で一番高い山に登りたいです。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "世界で一番高い山に登りたいです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "世界に",
    "は",
    "たくさんの",
    "国が",
    "あります"
  ],
  "chunk_count": 5,
  "target_word": "世界",
  "schema_version": 2,
  "shuffled_chunks": [
    "は",
    "世界に",
    "国が",
    "たくさんの",
    "あります"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "original_sentence": "世界には、たくさんの国があります。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "世界には、たくさんの国があります。"
}
```

#### Pack B
### Level 9 (sense 35055, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "世界は私たちのものであり、未来です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "世界は私たちのものであり、未来です。",
  "chunks": [
    "世界は",
    "私たちの",
    "ものであり",
    "未来です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "ものであり",
    "未来です",
    "世界は",
    "私たちの"
  ],
  "target_word": "世界",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "広い世界を見てみたいですね。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "広い世界を見てみたいですね。",
  "chunks": [
    "広い世界を",
    "見て",
    "みたいですね"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "見て",
    "広い世界を",
    "みたいですね"
  ],
  "target_word": "世界",
  "chunk_count": 3
}
```

---

## sense 35093, level 1

#### Pack A
### Level 1 (sense 35093, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "技術",
  "options": [
    "ぎじゅづ",
    "ぎしゅつ",
    "ぎじゅつ",
    "きじゅつ"
  ],
  "correct_answer": "ぎじゅつ",
  "word": "技術",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ぎじゅつ",
  "options": [
    "技術",
    "衝撃",
    "芸術",
    "美術"
  ],
  "correct_answer": "技術",
  "word": "技術",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "衝撃": "component",
    "芸術": "component",
    "美術": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35093, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "技術",
  "prompt": "技術",
  "options": [
    "ぎじゅづ",
    "ぎしゅつ",
    "ぎじゅつ",
    "きじゅつ"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "ぎじゅつ",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "gidʑɯtsɯ",
  "word": "技術",
  "options": [
    "美術",
    "話術",
    "技術",
    "魔術"
  ],
  "audio_url": null,
  "explanation": "正解です。「技術」は「ある分野で使われる、専門的な方法や手順。それを応用して作ったり処理したりする能力や体系。」という意味です。",
  "pronunciation": "ぎじゅつ",
  "correct_answer": "技術",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "美術": "「美術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「び」、一部の音の違い）。",
    "話術": "「話術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「わ」、一部の音の違い）。",
    "魔術": "「魔術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ま」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "技術",
  "prompt": "ぎじゅつ",
  "options": [
    "技術",
    "衝撃",
    "芸術",
    "美術"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "技術",
  "schema_version": 2,
  "distractor_sources": {
    "美術": "component",
    "芸術": "component",
    "衝撃": "component"
  }
}
```

---

## sense 35093, level 2

#### Pack A
### Level 2 (sense 35093, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "a generation — a group born in the same era and raised in a similar environment, or the lineage from parent to child",
        "ある分野で使われる、専門的な方法や手順。それを応用して作ったり処理したりする能力や体系。",
        "an atmosphere (mood)",
        "not allowed"
      ],
      "correct_answer": "ある分野で使われる、専門的な方法や手順。それを応用して作ったり処理したりする能力や体系。"
    }
  },
  "tier": "T6",
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "技術",
  "options": [
    "自分の好きなことやしたいことをして、気持ちよく過ごすこと。",
    "ある分野で使われる、専門的な方法や手順。それを応用して作ったり処理したりする能力や体系。",
    "ある動作や状態が完了せず、現在も続いていることを表す副詞。",
    "特定の目的のために企画・開催される、集まりや催し物。"
  ],
  "pronunciation": "ぎじゅつ",
  "correct_definition": "ある分野で使われる、専門的な方法や手順。それを応用して作ったり処理したりする能力や体系。"
}
```

#### Pack B
### Level 2 (sense 35093, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "correct_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "options": [
    "物事の数量や程度が、以前より少なくなること。",
    "本。書物。文字や絵が印刷された、綴じた紙の集まり。",
    "広く行き渡っていること。どこにでもあること。",
    "物を作ったり処理したりするための、専門的な方法や能力。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物を作ったり処理したりするための、専門的な方法や能力。",
        "病気やけがを治すために、薬を使ったり、手術をしたりすること。",
        "pursuit; to pursue — actively and persistently seeking to achieve a goal or ideal",
        "to put in (include)"
      ],
      "correct_answer": "物を作ったり処理したりするための、専門的な方法や能力。"
    }
  }
}
```

---

## sense 35093, level 4

#### Pack A
### Level 4 (sense 35093, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "近年、センサーやデータ解析___を活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析技術を活用した「精密農業」が注目されています。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
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
  "sentence_with_blank": "近年、センサーやデータ解析技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析技術を活用した「精密農業」が注目されています。",
  "options": [
    "に",
    "と",
    "を",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「技術を活用した」が正しい目的語のマーカーです。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "医療___の進歩は人々を助けます。",
  "original_sentence": "医療技術の進歩は人々を助けます。",
  "target_word": "技術",
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
    ],
    "accepted_normalized": [
      "技術",
      "技術者",
      "技術的",
      "新技術"
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
  "sentence_with_blank": "医療技術___進歩は人々を助けます。",
  "original_sentence": "医療技術の進歩は人々を助けます。",
  "options": [
    "で",
    "に",
    "を",
    "の"
  ],
  "correct_answer": "の",
  "target_word": "技術",
  "error_tags": {
    "を": "",
    "に": "",
    "で": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「医療技術の進歩」のように、名詞を修飾する場合は「の」が適切です。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35093, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術的",
      "技術者",
      "技術力"
    ],
    "accepted_normalized": [
      "技術",
      "技術的",
      "技術者",
      "技術力"
    ]
  },
  "input_mode": "ime",
  "target_word": "技術",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
  "sentence_with_blank": "センサー等を用いた___導入は、収量の安定化により収益性を向上させます。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "技術",
  "answer": {
    "accepted": [
      "技術",
      "技術的",
      "技術者",
      "技術力"
    ],
    "accepted_normalized": [
      "技術",
      "技術的",
      "技術者",
      "技術力"
    ]
  },
  "input_mode": "ime",
  "target_word": "技術",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼女はその技術に詳しい。",
  "sentence_with_blank": "彼女はその___に詳しい。"
}
```

---

## sense 35093, level 9

#### Pack A
### Level 9 (sense 35093, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "プログラミングの技術が上達しました。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "プログラミングの技術が上達しました。",
  "chunks": [
    "プログラミングの",
    "技術が",
    "上達しました"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "技術が",
    "上達しました",
    "プログラミングの"
  ],
  "target_word": "技術",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼の料理の技術は素晴らしいです。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼の料理の技術は素晴らしいです。",
  "chunks": [
    "彼の",
    "料理の",
    "技術は",
    "素晴らしいです"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "素晴らしいです",
    "彼の",
    "料理の",
    "技術は"
  ],
  "target_word": "技術",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 35093, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "その技術は",
    "まだ完成して",
    "いない"
  ],
  "chunk_count": 3,
  "target_word": "技術",
  "schema_version": 2,
  "shuffled_chunks": [
    "まだ完成して",
    "いない",
    "その技術は"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "その技術はまだ完成していない。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "その技術はまだ完成していない。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "この技術は生活を便利にする。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "この技術は",
    "生活を",
    "便利にする"
  ],
  "chunk_count": 3,
  "target_word": "技術",
  "schema_version": 2,
  "shuffled_chunks": [
    "この技術は",
    "便利にする",
    "生活を"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "この技術は生活を便利にする。"
}
```

---
