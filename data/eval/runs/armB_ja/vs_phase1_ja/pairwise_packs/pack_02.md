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
      "text": "新しい機械を買いました。",
      "is_correct": true
    },
    {
      "text": "この機械はとても静かです。",
      "is_correct": true
    },
    {
      "text": "機械を三匹買いました。",
      "is_correct": false,
      "error_description": "助数詞の誤りです。「機械」のような大型の機器や車両を数える場合は「台」を使います。「匹」は動物を数える際に用いる助数詞です。"
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
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

## sense 35011, level 1

#### Pack A
### Level 1 (sense 35011, difficulty None)
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

#### Pack B
### Level 1 (sense 35011, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "ipa": "hat͡ɕimeː",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "筆名",
    "発令",
    "発明",
    "節名"
  ],
  "correct_answer": "発明",
  "explanation": "正解です。「発明」は「新しいものや方法を考え出して、実際に作ること。」という意味です。",
  "distractor_explanations": {
    "筆名": "「筆名」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「ひ」、一部の音の違い）。",
    "節名": "「節名」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「せ」、一部の音の違い）。",
    "発令": "「発令」は「発明」と一モーラだけ異なる実在語です（3モーラ目: 「め」→「れ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
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
      "text": "この発明はとても便利です。",
      "is_correct": true
    },
    {
      "text": "発明はこのとても便利です。",
      "is_correct": false
    },
    {
      "text": "この発明はとても便利だです。",
      "is_correct": false
    },
    {
      "text": "この発明はとても便利にです。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：形容動詞「便利だ」の後に丁寧語の「です」を直接続けることはできません。「便利です」または「便利なのです」とする必要があります。 語順・係り受けの誤り：指示詞「この」は名詞「発明」を修飾すべきですが、文中の位置が不自然で、意味が通りません。「この発明はとても便利です」が正しい語順です。 助詞の混同：状態を表す形容動詞の語幹「便利」に接続助詞「に」をつけて「です」につなげるのは誤りです。「便利です」が正しい形です。",
  "target_word": "発明"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "発明は人を助けたいです。",
      "is_correct": false
    },
    {
      "text": "発明で人を助けたいです。",
      "is_correct": true
    },
    {
      "text": "発明で人を助けるのは一冊です。",
      "is_correct": false
    },
    {
      "text": "私は発明に人を助けたいです。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「発明」のような抽象的な概念や行為には「一冊」は使いません。「一冊」は本やノートなど物理的に綴じられた物に用います。 助詞の混同：「人を助ける」という動作の対象を示すためには「を」を使う必要があります。「に」を使うと方向や対象が変わってしまい、文意が不自然になります。 語順・係り受けの誤り：「助けたい」という意志を持つ主体は人間であり、「発明」そのものではありません。主題と述語の論理関係が破綻しています。",
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

## sense 35011, level 7

#### Pack A
### Level 7 (sense 35011, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その発明は世界を変えました。",
      "is_correct": true
    },
    {
      "text": "発明は世界を変えりました。",
      "is_correct": false,
      "error_description": "動詞「変える」の過去形は不規則変化であり、「変えりました」ではなく「変えました」が正しい形です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "大きな発明が生まれました。",
      "is_correct": true
    },
    {
      "text": "発明について調べています。",
      "is_correct": true
    },
    {
      "text": "発明について調べていります。",
      "is_correct": false,
      "error_description": "進行・継続を表す補助動詞「いる」の活用が誤っています。正しくは「ています」です。「いります」は存在動詞「入る」や「要る」の形であり、文脈に合いません。"
    },
    {
      "text": "発明で人を助けたいです。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35011, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "学校に発明の発表をしました。",
      "is_correct": false,
      "error_description": "動作が行われる場所を表す場合は助詞『で』を使います。『に』は存在場所や到着点を表すため、この文脈では不適切です。"
    },
    {
      "text": "私は新しい発明をしたいです。",
      "is_correct": true
    },
    {
      "text": "彼の発明はすごく便利です。",
      "is_correct": true
    },
    {
      "text": "この発明は世界を変えます。",
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
      "text": "学校で発明の発表をしました。",
      "is_correct": true
    },
    {
      "text": "発明は難しいが楽しいです。",
      "is_correct": true
    },
    {
      "text": "その発明には驚きました。",
      "is_correct": true
    },
    {
      "text": "発明を学校で発表をしました。",
      "is_correct": false,
      "error_description": "「発明を」と「発表をしました」で助詞「を」が重複しています。「発明の発表をしました」または「発明を学校で発表しました」とするのが正しいです。"
    }
  ]
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
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

#### Pack B
### Level 1 (sense 35017, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "ɸɯeɾɯ",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "絶える",
    "増える",
    "栄える",
    "餓える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "餓える": "「餓える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「う」、一部の音の違い）。",
    "栄える": "「栄える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「は」、一部の音の違い）。",
    "絶える": "「絶える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35017, level 3

#### Pack A
### Level 3 (sense 35017, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "しかし、その古い建物や管理の難しさから、現在では壊されるケースも___ています。",
  "original_sentence": "しかし、その古い建物や管理の難しさから、現在では壊されるケースも増えています。",
  "correct_answer": "増え",
  "options": [
    "変わり",
    "起こり",
    "続き",
    "増え"
  ],
  "explanation": "正解です。文脈「壊されるケースも＿＿ています」において、事例の数量が多くなっている状況を表すのに適切です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "友だちが___ると楽しいです。",
  "original_sentence": "友だちが増えると楽しいです。",
  "correct_answer": "増え",
  "options": [
    "増え",
    "終わり",
    "働き",
    "変わり"
  ],
  "explanation": "正解です。文脈「友だちが＿＿＿と楽しいです」において、人数が多くなることを表す「増え」が適切です。",
  "distractor_tags": {},
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```

#### Pack B
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

---

## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "最近、ゴミの量が___ています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "options": [
    "冷え",
    "増え",
    "枯れ",
    "晴れ"
  ],
  "explanation": "て形。「～てきた」の形に合う。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "最近、ゴミの量___増えています。",
  "original_sentence": "最近、ゴミの量が増えています。",
  "options": [
    "に",
    "で",
    "が",
    "を"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」が表す現象の主体を提示する主格助詞である"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "雨が降って水が___ました。",
  "original_sentence": "雨が降って水が増えました。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（て形の語幹）",
  "options": [
    "晴れ",
    "冷え",
    "枯れ",
    "増え"
  ],
  "explanation": "て形の語幹。「病気になる人が～いる」に合う。",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "雨___降って水が増えました。",
  "original_sentence": "雨が降って水が増えました。",
  "options": [
    "を",
    "が",
    "に",
    "で"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語（主体）を標示する格助詞"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35017, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "公園に来る人が___ました。",
  "original_sentence": "公園に来る人が増えました。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "ます形（連用形）",
  "options": [
    "増える",
    "増えて",
    "増えない",
    "増え"
  ],
  "explanation": "「ました」に接続する連用形（ます形）の語幹として正しい",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "公園に来る人___増えました。",
  "original_sentence": "公園に来る人が増えました。",
  "options": [
    "で",
    "が",
    "に",
    "を"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語（現象の主体）を標示する"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "ゴミの量が___ています。",
  "original_sentence": "ゴミの量が増えています。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（ます形）",
  "options": [
    "増えて",
    "増えた",
    "増え",
    "増える"
  ],
  "explanation": "「います」に接続する連用形（ます形）の語幹として正しい",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "ゴミの量___増えています。",
  "original_sentence": "ゴミの量が増えています。",
  "options": [
    "で",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "が",
  "target_word": "増え",
  "error_tags": {
    "を": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "自動詞「増える」の主語（変化の対象）を示す格助詞として正しい。"
    }
  }
}
```

---

## sense 35017, level 7

#### Pack A
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "公園に来る人が増えました。",
      "is_correct": true
    },
    {
      "text": "公園に来る人が増えりました。",
      "is_correct": false,
      "error_description": "動詞『増える』の過去形は『増えました』です。『増えりました』という活用形は存在しません。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "しかし、見た目が古かったり直すのが大変だったりするため、現在ではその価値が認められている一方で、壊される建物の数も増えています。",
      "is_correct": true
    },
    {
      "text": "車の数が年々増えいる。",
      "is_correct": false,
      "error_description": "「～ている」の形で「て」が抜けている誤り。"
    },
    {
      "text": "最近、ゴミの量が増えています。",
      "is_correct": true
    },
    {
      "text": "私の町で外国人が増えています。",
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
      "text": "増えた友達と遊びに行きます。",
      "is_correct": true
    },
    {
      "text": "雨が降って水が増えました。",
      "is_correct": true
    },
    {
      "text": "増えることを期待しています。",
      "is_correct": true
    },
    {
      "text": "しかし、その無骨な外観や維持管理の難しさから、現在ではその価値が再評価される一方で、取り壊されるケースも増えいます。",
      "is_correct": false,
      "error_description": "「～ています」の「て」が抜けている誤り。"
    }
  ]
}
```

---

## sense 35039, level 1

#### Pack A
### Level 1 (sense 35039, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "出来る",
  "pronunciation": "できる",
  "ipa": "dekɪɾu",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "デレる",
    "出禁",
    "出来る",
    "煮切る"
  ],
  "correct_answer": "出来る",
  "explanation": "正解です。「出来る」は「物事を行う能力がある、または実現可能であることを表します。」という意味です。",
  "distractor_explanations": {
    "出禁": "「出禁」は「出来る」と一モーラだけ異なる実在語です（3モーラ目: 「る」→「ん」、撥音「ん」の有無）。",
    "デレる": "「デレる」は「出来る」と一モーラだけ異なる実在語です（2モーラ目: 「き」→「れ」、一部の音の違い）。",
    "煮切る": "「煮切る」は「出来る」と一モーラだけ異なる実在語です（1モーラ目: 「で」→「に」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35039, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "出来る",
  "pronunciation": "できる",
  "ipa": "/dekiru/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "尽きる",
    "出来る",
    "厭きる",
    "飽きる"
  ],
  "correct_answer": "出来る",
  "explanation": "正解です。「出来る」は「「出来る」は動詞で、物事を行う能力がある、または実現可能であることを表します。」という意味です。",
  "distractor_explanations": {
    "尽きる": "「尽きる」は「出来る」と一モーラだけ異なる実在語です（1モーラ目: 「で」→「つ」、一部の音の違い）。",
    "厭きる": "「厭きる」は「出来る」と一モーラだけ異なる実在語です（1モーラ目: 「で」→「あ」、一部の音の違い）。",
    "飽きる": "「飽きる」は「出来る」と一モーラだけ異なる実在語です（1モーラ目: 「で」→「あ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35039, level 3

#### Pack A
### Level 3 (sense 35039, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "誰に何を求めているか分析し、適切な言葉で発信することで、小さくても確実なファンを獲得___ます。",
  "original_sentence": "誰に何を求めているか分析し、適切な言葉で発信することで、小さくても確実なファンを獲得できます。",
  "correct_answer": "でき",
  "options": [
    "いたし",
    "でき",
    "し",
    "おき"
  ],
  "explanation": "正解です。文脈に適切に合致します。",
  "distractor_tags": {},
  "word_definition": "「出来る」は動詞で、物事を行う能力がある、または実現可能であることを表します。",
  "target_word": "でき"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "友達と協力すれば成功___ます。",
  "original_sentence": "友達と協力すれば成功できます。",
  "correct_answer": "でき",
  "options": [
    "わかり",
    "叶い",
    "し",
    "でき"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "「出来る」は動詞で、物事を行う能力がある、または実現可能であることを表します。",
  "target_word": "でき"
}
```

#### Pack B
### Level 3 (sense 35039, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "適切な言葉で発信することで、小さくても確実なファンを獲得___ます。",
  "original_sentence": "適切な言葉で発信することで、小さくても確実なファンを獲得できます。",
  "correct_answer": "でき",
  "options": [
    "でき",
    "あり",
    "なり",
    "し"
  ],
  "explanation": "正解です。文脈「発信することで～獲得できます」において、可能・能力を表す「でき」が適切です。",
  "distractor_tags": {},
  "word_definition": "物事を行う能力がある、または実現可能であることを表します。",
  "target_word": "でき"
}
```

---
