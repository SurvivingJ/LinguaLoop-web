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


## sense 34998, level 1

#### Pack A
### Level 1 (sense 34998, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "一",
  "prompt": "一",
  "options": [
    "いぢ",
    "いち",
    "いいち",
    "いちい"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "いち",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "/it͡ɕi/",
  "word": "一",
  "options": [
    "遺事",
    "入",
    "書痴",
    "一"
  ],
  "audio_url": null,
  "explanation": "正解です。「一」は「数の中で最も小さい、1という数を表す語。」という意味です。",
  "pronunciation": "いち",
  "correct_answer": "一",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "入": "「入」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「り」、一部の音の違い）。",
    "書痴": "「書痴」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「しょ」、一部の音の違い）。",
    "遺事": "「遺事」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「じ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "一",
  "prompt": "いち",
  "options": [
    "今",
    "4",
    "一",
    "位置"
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

#### Pack B
### Level 1 (sense 34998, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "一",
  "options": [
    "いぢ",
    "いち",
    "いいち",
    "いちい"
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
  "ipa": "/i.ti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "一",
    "池",
    "既知",
    "淵"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "池": "「池」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「け」、一部の音の違い）。",
    "淵": "「淵」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ふ」、一部の音の違い）。",
    "既知": "「既知」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「き」、一部の音の違い）。"
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
    "今",
    "4",
    "一",
    "位置"
  ],
  "correct_answer": "一",
  "word": "一",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "位置": "homophone",
    "4": "frequency",
    "今": "frequency"
  }
}
```

---

## sense 34998, level 2

#### Pack A
### Level 2 (sense 34998, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "options": [
    "レモン果汁に水と砂糖を加えて作った、すっぱくてさわやかな飲み物。",
    "人と人の関係が近く、心が通じ合っている様子。仲が良い。",
    "数の中で最も小さい、1という数を表す語。",
    "空気中などに存在する微生物のうち、特に衛生上問題となるものを指す。食べ物を腐らせたり、病気の原因になることがある。"
  ],
  "pronunciation": "いち",
  "correct_definition": "数の中で最も小さい、1という数を表す語。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "自分の能力や才能を発揮して、社会や集団の中で積極的に活動すること。",
        "数の中で最も小さい、1という数を表す語。",
        "studio",
        "curve"
      ],
      "correct_answer": "数の中で最も小さい、1という数を表す語。"
    }
  },
  "tier": "T3",
  "word": "一",
  "pronunciation": "いち",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 34998, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "correct_definition": "ひとつだけの数。",
  "options": [
    "自然の力ではなく、人間の技術や手によって作られたこと。",
    "ひとつだけの数。",
    "敵や相手と戦うこと。また、その行動。",
    "粉や粒状のものを、広く散らすようにして置くこと。"
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
        "ひとつだけの数。",
        "送达",
        "消除（熄灭）",
        "改善 —— 把事物变成更好的状态"
      ],
      "correct_answer": "ひとつだけの数。"
    }
  }
}
```

---

## sense 34998, level 3

#### Pack A
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "答えは___です。",
  "original_sentence": "答えは一です。",
  "correct_answer": "一",
  "options": [
    "一冊",
    "一",
    "犬",
    "参"
  ],
  "explanation": "正解です。文脈に合う数値を表します。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

#### Pack B
### Level 3 (sense 34998, difficulty 5)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "options": [
    "百",
    "一",
    "二",
    "十"
  ],
  "explanation": "文脈に合う正しい数字。",
  "target_word": "一",
  "correct_answer": "一",
  "distractor_tags": {},
  "word_definition": "数の中で最も小さい、1という数を表す語。",
  "original_sentence": "一に一を足すと二になる。",
  "sentence_with_blank": "___に一を足すと二になる。"
}
```

---

## sense 34998, level 4

#### Pack A
### Level 4 (sense 34998, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
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
  "original_sentence": "彼は一から十まで数えた。",
  "sentence_with_blank": "彼は___から十まで数えた。"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "起点を表す格助詞「から」が「十まで」との呼応で自然な範囲の始点を示す"
    }
  },
  "options": [
    "で",
    "を",
    "から",
    "に"
  ],
  "error_tags": {
    "で": "source_vs_goal",
    "に": "source_vs_goal",
    "を": "source_vs_goal"
  },
  "target_word": "一",
  "correct_answer": "から",
  "schema_version": 2,
  "original_sentence": "彼は一から十まで数えた。",
  "sentence_with_blank": "彼は一___十まで数えた。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "一",
  "answer": {
    "accepted": [
      "一"
    ],
    "accepted_normalized": [
      "一"
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
  "original_sentence": "一は最も小さい自然数だ。",
  "sentence_with_blank": "___は最も小さい自然数だ。"
}
```

#### Pack B
### Level 4 (sense 34998, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___から始めましょう。",
  "original_sentence": "一から始めましょう。",
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
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一___十まで丁寧に説明しています。",
  "original_sentence": "一から十まで丁寧に説明しています。",
  "options": [
    "に",
    "から",
    "を",
    "で"
  ],
  "correct_answer": "から",
  "target_word": "一",
  "error_tags": {
    "に": "direction",
    "で": "instrument",
    "を": "object_marking"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "数詞の起点を表し、「十まで」と呼応して範囲を示す"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___を足すと二になります。",
  "original_sentence": "一を足すと二になります。",
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
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "一___足すと二になります。",
  "original_sentence": "一を足すと二になります。",
  "options": [
    "に",
    "が",
    "を",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "一",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「足す」の直接目的語を標示する"
    }
  }
}
```

---

## sense 34998, level 6

#### Pack A
### Level 6 (sense 34998, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一という数字を漢字で書く。",
      "is_correct": true
    },
    {
      "text": "一が空を飛ぶ。",
      "is_correct": false
    },
    {
      "text": "一を食べました。",
      "is_correct": false
    },
    {
      "text": "一が笑っている。",
      "is_correct": false
    }
  ],
  "explanation": "数字が笑うことはない。 数字は食べる対象にならない。 数字が空を飛ぶことはない。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一を二倍すると二になる。",
      "is_correct": true
    },
    {
      "text": "一を洗った。",
      "is_correct": false
    },
    {
      "text": "一は幸せそうだ。",
      "is_correct": false
    },
    {
      "text": "一が走ってきた。",
      "is_correct": false
    }
  ],
  "explanation": "数字が感情を持つことはない。 数字は洗う対象にならない。 数字が走ることはない。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一から十まで説明してあります。",
      "is_correct": false
    },
    {
      "text": "一から十までで丁寧に説明します。",
      "is_correct": false
    },
    {
      "text": "一、二、三と声を合わせて数えています。",
      "is_correct": true
    },
    {
      "text": "一羽の犬が公園で遊んでいる。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り。「犬」に対しては「羽」ではなく「匹」を用いるのが正しい。 助詞の混同。起点と終点による範囲を示す「一から十まで」に対して、動作の手段や状態を表す「で」は不適切。 活用・アスペクトの誤り。「説明する」のような動作動詞に対し、準備や状態の残留を表す「てある」を用いるのは不自然。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "数字の一は奇数で、二は偶数です。",
      "is_correct": true
    },
    {
      "text": "一に足すと二を三になります。",
      "is_correct": false
    },
    {
      "text": "一は二を足すと三になります。",
      "is_correct": false
    },
    {
      "text": "一羽の本が机の上に置いてある。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：本を数える場合は「冊」を使い、「羽」は鳥やウサギなどに使います。 助詞の混同：足し算の構文では「AにBを足すと」という形になります。「は」は不適切です。 語順・係り受けの誤り：「一に二を足すと三になります」という正しい語順になっていません。",
  "target_word": "一"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "二",
    "多",
    "単",
    "全"
  ],
  "correct_answer": "多",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "目標語の語義（ひとつだけの数）に対して、数が多いことを表す名詞として対義関係にある"
    }
  }
}
```

---

## sense 34998, level 9

#### Pack A
### Level 9 (sense 34998, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "一の位を先に計算する。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "一の",
    "位を",
    "先に",
    "計算する"
  ],
  "chunk_count": 4,
  "target_word": "一",
  "schema_version": 2,
  "shuffled_chunks": [
    "一の",
    "先に",
    "位を",
    "計算する"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "一の位を先に計算する。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "一と",
    "いう数字を",
    "漢字で",
    "書く"
  ],
  "chunk_count": 4,
  "target_word": "一",
  "schema_version": 2,
  "shuffled_chunks": [
    "漢字で",
    "書く",
    "一と",
    "いう数字を"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "一という数字を漢字で書く。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "一という数字を漢字で書く。"
}
```

#### Pack B
### Level 9 (sense 34998, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "一から順番に名前を呼んでいます。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "一から順番に名前を呼んでいます。",
  "chunks": [
    "一から",
    "順番に",
    "名前を",
    "呼んで",
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
    "一から",
    "名前を",
    "順番に",
    "呼んで",
    "います"
  ],
  "target_word": "一",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "一、二、三と声を合わせて数えています。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "一、二、三と声を合わせて数えています。",
  "chunks": [
    "一二",
    "三と",
    "声を",
    "合わせて",
    "数えて",
    "います"
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
    "数えて",
    "合わせて",
    "います",
    "声を",
    "一二",
    "三と"
  ],
  "target_word": "一",
  "chunk_count": 6
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
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "[kikai]",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "機内",
    "向かい",
    "機械",
    "魚介"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「動力や電気で動き、人間の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "機内": "「機内」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「な」、一部の音の違い）。",
    "向かい": "「向かい」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「む」、一部の音の違い）。",
    "魚介": "「魚介」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「ぎょ」、一部の音の違い）。"
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
    "不要になったもの、捨てるもの、または材料の切れ端や残りの部分。",
    "動力や電気で動き、人間の代わりに仕事をする装置。",
    "学校の中で、先生と生徒が勉強するための部屋。",
    "複数の点を結ぶ、細くて長いもの。また、通信や交通のための経路。"
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
        "束缚",
        "動力や電気で動き、人間の代わりに仕事をする装置。",
        "an arrow (symbol)",
        "a sparrow's snack — a snack sparrows eat, once used as an old-fashioned nickname for electricity"
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
  "sentence_with_blank": "私は新しい___を使っています。",
  "original_sentence": "私は新しい機械を使っています。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "個",
      "機械化"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "個",
      "機械化"
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
  "sentence_with_blank": "私は新しい機械___使っています。",
  "original_sentence": "私は新しい機械を使っています。",
  "options": [
    "に",
    "で",
    "を",
    "が"
  ],
  "correct_answer": "を",
  "target_word": "機械",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「使う」の直接目的語を標示する"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___が音をたてています。",
  "original_sentence": "機械が音をたてています。",
  "target_word": "機械",
  "word": "機械",
  "answer": {
    "accepted": [
      "機械",
      "台",
      "個",
      "機械化"
    ],
    "accepted_normalized": [
      "機械",
      "台",
      "個",
      "機械化"
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
  "sentence_with_blank": "機械が音___たてています。",
  "original_sentence": "機械が音をたてています。",
  "options": [
    "は",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "機械",
  "error_tags": {
    "が": "object_marking",
    "は": "topic_vs_subject",
    "に": "other"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「たてる」の直接目的語を標示する"
    }
  }
}
```

---

## sense 35001, level 7

#### Pack A
### Level 7 (sense 35001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は新しい機械を使っています。",
      "is_correct": true
    },
    {
      "text": "私は新しい機械で使っています。",
      "is_correct": false,
      "error_description": "「機械」は「使う」動作の直接の対象であるため、助詞「を」を使います。「で」は手段や場所を表す助詞なので、ここでは不適切です。"
    },
    {
      "text": "機械が急に止まりました。",
      "is_correct": true
    },
    {
      "text": "この機械はとてもよく動きます。",
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
      "text": "機械について調べています。",
      "is_correct": true
    },
    {
      "text": "機械に音をたてています。",
      "is_correct": false,
      "error_description": "助詞の混同です。動作の主体には「が」を使い、「に」は動作の方向や対象に使います。正しい文は「機械が音をたてています。」です。"
    },
    {
      "text": "機械が音をたてています。",
      "is_correct": true
    },
    {
      "text": "壊れた機械を捨てましょう。",
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
