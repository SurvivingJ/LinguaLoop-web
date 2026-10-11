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
### Level 7 (sense 35001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "機械が動いています。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "新しい機械を一個買いました。",
      "is_correct": false,
      "error_description": "機械を数える助数詞は「台」です。「個」は小さめの物に使う助数詞で、機械には不適切です。"
    },
    {
      "text": "この機械は便利です。",
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
      "text": "機械を作る人はすごいです。",
      "is_correct": true
    },
    {
      "text": "機械を壊れてしまいました。",
      "is_correct": false,
      "error_description": "自動詞の「壊れる」の主語には助詞「が」を使います。「を」は他動詞の目的語に使う助詞です。"
    },
    {
      "text": "機械の音を聞きました。",
      "is_correct": true
    },
    {
      "text": "機械が壊れてしまいました。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35001, level 9

#### Pack A
### Level 9 (sense 35001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "機械を使ってください。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "機械を使ってください。",
  "chunks": [
    "機械を",
    "使って",
    "ください"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "機械を",
    "ください",
    "使って"
  ],
  "target_word": "機械",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "機械を修理できます。"
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
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "ipa": "/hatsumei/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "発明",
    "絶命",
    "血盟",
    "説明"
  ],
  "correct_answer": "発明",
  "explanation": "正解です。「発明」は「新しい物や方法を考え出し、実際に作ること。」という意味です。",
  "distractor_explanations": {
    "絶命": "「絶命」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「ぜ」、一部の音の違い）。",
    "血盟": "「血盟」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「け」、一部の音の違い）。",
    "説明": "「説明」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「せ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
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

---

## sense 35011, level 2

#### Pack A
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

#### Pack B
### Level 2 (sense 35011, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "correct_definition": "新しい物や方法を考え出し、実際に作ること。",
  "options": [
    "生物が生きていくこと。特に、厳しい状況の中で命や活動を保ち続けること。",
    "自分の願いがかなったり、よいことがあったりしたときに感じる、楽しくて満足な気持ち。",
    "値段が低く、買いやすいこと。",
    "新しい物や方法を考え出し、実際に作ること。"
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
        "今、実際にある状態や事情。",
        "新しい物や方法を考え出し、実際に作ること。",
        "「問う」は、人に質問することです。",
        "barrier; a protective shield or partition"
      ],
      "correct_answer": "新しい物や方法を考え出し、実際に作ること。"
    }
  }
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
  "sentence_with_blank": "彼の___はすごく便利です。",
  "original_sentence": "彼の発明はすごく便利です。",
  "target_word": "発明",
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明品",
      "発明家"
    ],
    "accepted_normalized": [
      "発明",
      "発明品",
      "発明家"
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
  "sentence_with_blank": "学校で___の発表をしました。",
  "original_sentence": "学校で発明の発表をしました。",
  "target_word": "発明",
  "word": "発明",
  "answer": {
    "accepted": [
      "発明",
      "発明品",
      "発明家"
    ],
    "accepted_normalized": [
      "発明",
      "発明品",
      "発明家"
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

---

## sense 35011, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35011, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "創造",
    "開発",
    "考案",
    "発見"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しい物や方法を考え出し、実際に作ること。",
      "explanation": "すでに存在するものを見出すことで、新たなものを創り出す目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "発明を切った。",
      "is_correct": false
    },
    {
      "text": "発明は難しいが楽しいです。",
      "is_correct": true
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
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "発見",
    "創造",
    "応用",
    "開発"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しい物や方法を考え出し、実際に作ること。",
      "explanation": "すでに存在するものや法則などを明らかにすることで、目標語の対義語となる"
    }
  }
}
```

---

## sense 35011, level 9

#### Pack A
### Level 9 (sense 35011, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "こんな発明ができるんです。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "こんな発明ができるんです。",
  "chunks": [
    "こんな発明が",
    "できるん",
    "です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "です",
    "こんな発明が",
    "できるん"
  ],
  "target_word": "発明",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "発明をして特許を取りました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "発明をして特許を取りました。",
  "chunks": [
    "発明を",
    "して",
    "特許を",
    "取りました"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "特許を",
    "して",
    "発明を",
    "取りました"
  ],
  "target_word": "発明",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 35011, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "この機械は彼の発明です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "この機械は彼の発明です。",
  "chunks": [
    "この機械は",
    "彼の",
    "発明です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "発明です",
    "この機械は",
    "彼の"
  ],
  "target_word": "発明",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "発明には創造力が必要だ。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "発明には創造力が必要だ。",
  "chunks": [
    "発明に",
    "は",
    "創造力が",
    "必要だ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "創造力が",
    "は",
    "発明に",
    "必要だ"
  ],
  "target_word": "発明",
  "chunk_count": 4
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "増える",
  "options": [
    "ふうえる",
    "ふえる",
    "ぶえる",
    "ぷえる"
  ],
  "correct_answer": "ふえる",
  "word": "増える",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "ɸueɾu",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "添え",
    "変え",
    "据え",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "変え": "",
    "添え": "",
    "据え": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふえる",
  "options": [
    "異なる",
    "増える",
    "不思議",
    "増やす"
  ],
  "correct_answer": "増える",
  "word": "増える",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "増やす": "component",
    "不思議": "component",
    "異なる": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35017, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
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
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "/ɸɯeɾɯ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "萌える",
    "デュエル",
    "返る",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "萌える": "「萌える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「も」、一部の音の違い）。",
    "返る": "「返る」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「か」、一部の音の違い）。",
    "デュエル": "「デュエル」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「でゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T4`
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

---

## sense 35017, level 2

#### Pack A
### Level 2 (sense 35017, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "ある目的を達成するために考え出された方法や手段。",
    "物事の内容や理由などを、相手によくわかるように述べること。",
    "数量や程度が多くなる。",
    "物事の進行や機能を妨げること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "「モンスターと戦う」で、ゲーム内の敵キャラクターに対して攻撃や防御などの行動をすること。実際の争いではなく、遊びの範囲での対決。",
        "the lower part",
        "文字を読んだり書いたりできること",
        "数量や程度が多くなる。"
      ],
      "correct_answer": "数量や程度が多くなる。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35017, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "correct_definition": "数量や程度が多くなる。",
  "options": [
    "数量や程度が多くなる。",
    "飛行機の主要な翼で、揚力を発生させて機体を支える重要な部分。",
    "問題や質問に対する答え。",
    "生物が成長して大きくなる。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "増え",
  "pronunciation": "ふえる",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to remain; to be left — something still being there, unused, in a place or state",
        "文化や習慣などの違いを理解する、または認識するという意味です。",
        "同じであること。",
        "数量や程度が多くなる。"
      ],
      "correct_answer": "数量や程度が多くなる。"
    }
  }
}
```

---

## sense 35017, level 3

#### Pack A
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も___ています。",
  "original_sentence": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も増えています。",
  "correct_answer": "増え",
  "options": [
    "増え",
    "下がり",
    "変わり",
    "重なり"
  ],
  "explanation": "正解です。文脈に最も適しています。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "___た友達と遊びに行きます。",
  "original_sentence": "増えた友達と遊びに行きます。",
  "correct_answer": "増えた",
  "options": [
    "減った",
    "増えた",
    "降った",
    "壊れた"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "しかし、古い建物であることや管理の難しさから、壊されるケースも___ています。",
  "original_sentence": "しかし、古い建物であることや管理の難しさから、壊されるケースも増えています。",
  "correct_answer": "増え",
  "options": [
    "止まり",
    "増え",
    "変わり",
    "減り"
  ],
  "explanation": "文脈に合致する正しい語です。「壊されるケースも増えています」は自然な表現です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "友達の意見を取り入れて、参加者が___ました。",
  "original_sentence": "友達の意見を取り入れて、参加者が増えました。",
  "correct_answer": "増え",
  "options": [
    "変わり",
    "減り",
    "増え",
    "止まり"
  ],
  "explanation": "文脈に合致する正しい語です。「友達の意見を取り入れて、参加者が増えました」は自然な表現です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

---
