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


## sense 35011, level 7

#### Pack A
### Level 7 (sense 35011, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この発明によって人々の生活は豊かになった。",
      "is_correct": true
    },
    {
      "text": "彼の発明は世界中に使われています。",
      "is_correct": false,
      "error_description": "動作が行われる場所や範囲を表す場合は助詞「で」を使います。「に」は存在場所や到着点を表すため、この文脈では不適切です。"
    },
    {
      "text": "彼の発明は世界中で使われています。",
      "is_correct": true
    },
    {
      "text": "私は将来、便利な機械を発明したいです。",
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
      "text": "彼の発明した道具は多くの人の役に立っている。",
      "is_correct": true
    },
    {
      "text": "小さな気づきがやがて大きな発明につながる。",
      "is_correct": true
    },
    {
      "text": "私たちは環境を守るための発明を学んでいます。",
      "is_correct": false,
      "error_description": "「ための」の後に続く名詞「発明」を修飾する形になっていますが、「環境を守る」という目的に対して「発明を学ぶ」という行為が直接結びつくため、「ために」を用いて目的と行為を明確に接続するのが自然です。"
    },
    {
      "text": "私たちは環境を守るための発明を学んでいます。",
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
**phonetic_recognition** variant `A`, tier `T4+`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "/ɸɯeɾɯ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "冷える",
    "増える",
    "萌える",
    "植える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "植える": "「植える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「う」、一部の音の違い）。",
    "冷える": "「冷える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「ひ」、一部の音の違い）。",
    "萌える": "「萌える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「も」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35017, level 4

#### Pack A
### Level 4 (sense 35017, difficulty None)
**particle_selection** variant `A`, tier `T4+`
```json
{
  "sentence_with_blank": "最近、この町で外国人___増えています。",
  "original_sentence": "最近、この町で外国人が増えています。",
  "options": [
    "を",
    "に",
    "が",
    "で"
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
      "explanation": "自動詞「増える」の主語（主体）を標示する"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T4+`
```json
{
  "sentence_with_blank": "冬になると風邪をひく人が___ます。",
  "original_sentence": "冬になると風邪をひく人が増えます。",
  "correct_answer": "増え",
  "base_form": "増える",
  "form_label": "連用形（ます形）",
  "options": [
    "増えた",
    "増える",
    "増えて",
    "増え"
  ],
  "explanation": "「ます」に接続する連用形（ます形）として正しい",
  "word_definition": "数量や程度が多くなる。",
  "target_word": "増え"
}
```
**particle_selection** variant `B`, tier `T4+`
```json
{
  "sentence_with_blank": "冬になると風邪をひく人___増えます。",
  "original_sentence": "冬になると風邪をひく人が増えます。",
  "options": [
    "で",
    "に",
    "を",
    "が"
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
      "explanation": "自動詞「増える」の主語を標示する格助詞として正しい"
    }
  }
}
```

#### Pack B
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

---

## sense 35017, level 7

#### Pack A
### Level 7 (sense 35017, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4+`
```json
{
  "sentences": [
    {
      "text": "最近、この町で外国人を増えています。",
      "is_correct": false,
      "error_description": "「増える」は自動詞なので、目的語をとる他動詞の用法「を増える」は誤りです。また、場所を示す助詞は「で」ではなく、存在や変化の着地点を表す「に」を使うのが自然です。"
    },
    {
      "text": "テストの点が前より増えました。",
      "is_correct": true
    },
    {
      "text": "最近、この町で外国人が増えています。",
      "is_correct": true
    },
    {
      "text": "しかし、その古めかしい見た目や管理の難しさから、現在ではその価値が見直される一方で、壊されるケースも増えています。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4+`
```json
{
  "sentences": [
    {
      "text": "冬になると風邪をひく人が増えっています。",
      "is_correct": false,
      "error_description": "「増えっています」は存在しない活用形です。正しくは「増えます」または「増えています」とします。"
    },
    {
      "text": "最近、増えている問題について話します。",
      "is_correct": true
    },
    {
      "text": "冬になると風邪をひく人が増えます。",
      "is_correct": true
    },
    {
      "text": "友達の数はこれから増えます。",
      "is_correct": true
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

## sense 35055, level 1

#### Pack A
### Level 1 (sense 35055, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "ipa": "/sekai/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "デカイ",
    "世界",
    "戦意",
    "市会"
  ],
  "correct_answer": "世界",
  "explanation": "正解です。「世界」は「地球全体や、社会全体のこと。」という意味です。",
  "distractor_explanations": {
    "市会": "「市会」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「し」、一部の音の違い）。",
    "戦意": "「戦意」は「世界」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「ん」、撥音「ん」の有無）。",
    "デカイ": "「デカイ」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「で」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35055, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "pronunciation": "せかい",
  "ipa": "/seꜜkai/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "不快",
    "死海",
    "歯科医",
    "世界"
  ],
  "correct_answer": "世界",
  "explanation": "正解です。「世界」は「地球全体。また、社会全体や、人の活動の範囲。」という意味です。",
  "distractor_explanations": {
    "不快": "「不快」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「ふ」、一部の音の違い）。",
    "死海": "「死海」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「し」、一部の音の違い）。",
    "歯科医": "「歯科医」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「し」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35055, level 3

#### Pack A
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "私は___の人々と交流するために、毎日英語の勉強を頑張っています。",
  "original_sentence": "私は世界の人々と交流するために、毎日英語の勉強を頑張っています。",
  "correct_answer": "世界",
  "options": [
    "時代",
    "世界",
    "個人",
    "地域"
  ],
  "explanation": "正解です。文脈から、交流の範囲が日本だけでなく地球全体（世界）に及んでいることがわかります。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、社会全体や、人の活動の範囲。",
  "target_word": "世界"
}
```

#### Pack B
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "私はいつか___一周の旅に出かけたいです。",
  "original_sentence": "私はいつか世界一周の旅に出かけたいです。",
  "correct_answer": "世界",
  "options": [
    "世間",
    "世界",
    "グローブ",
    "机"
  ],
  "explanation": "正解です。「世界一周」は決まった表現として自然です。",
  "distractor_tags": {},
  "word_definition": "地球全体や、社会全体のこと。",
  "target_word": "世界"
}
```

---

## sense 35055, level 6

#### Pack A
### Level 6 (sense 35055, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界で広くて、とても面白いです。",
      "is_correct": false
    },
    {
      "text": "世界は広くて、とても面白いです。",
      "is_correct": true
    },
    {
      "text": "世界は広くて、とても面白いでした。",
      "is_correct": false
    },
    {
      "text": "私は一匹の世界を旅しました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「世界」に「一匹」は使えません。「一つ」などを用います。 助詞の混同：文の主題を示すには「は」を使い、「世界は広くて」とするのが正しいです。 活用・アスペクトの誤り：形容詞「面白い」の過去形や状態を表す際は「面白かった」を用います。",
  "target_word": "世界"
}
```

#### Pack B
### Level 6 (sense 35055, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界はとても広く、まだ私たちが知らないことがたくさんあります。",
      "is_correct": true
    },
    {
      "text": "世界はとても広く、まだ私たちが知らないことが三冊あります。",
      "is_correct": false
    },
    {
      "text": "世界はとても広く、まだ私たちが知らないことがたくさんあります。",
      "is_correct": false
    },
    {
      "text": "世界はとても広く、まだ私たちが知らないことがたくさんあります。",
      "is_correct": false
    }
  ],
  "explanation": "正しい文です。「世界」を空間的な広がりとして捉え、自然な表現になっています。 助数詞の誤り：「世界」や「こと」のような抽象的な名詞に、本や雑誌を数える「三冊」を使うことはできません。 助詞の混同：主題を提示する「は」を使うべきところで、主語を強調する「が」を使っており、文脈との繋がりが不自然です。",
  "target_word": "世界"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "世界",
  "relation": "antonym",
  "options": [
    "宇宙",
    "地域",
    "国内",
    "海外"
  ],
  "correct_answer": "国内",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "地球全体。また、社会全体や、人の活動の範囲。",
      "explanation": "地球全体や社会全体に対する、自国の範囲を指す対義語です。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界には、まだ私たちが訪れていない美しい場所がたくさんあります。",
      "is_correct": false
    },
    {
      "text": "世界に、まだ私たちが訪れていない美しい場所がたくさんあるている。",
      "is_correct": false
    },
    {
      "text": "私は世界の人々と交流するために、毎日英語の勉強を頑張っています。",
      "is_correct": true
    },
    {
      "text": "世界を、まだ私たちが訪れていない美しい場所がたくさんあります。",
      "is_correct": false
    }
  ],
  "explanation": "「世界は」の「は」は主題を示しますが、存在文の構文では場所を示す「に」に対して「が」を使うか、あるいは「世界には」とするのが自然です。ここでは「世界が」が適切です。 「世界を」の「を」は移動の経路などを表しますが、存在する場所を示す場合は「に」を使います。 「ある」の進行形・状態を表す場合は「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「あるている」ではなく「ある......",
  "target_word": "世界"
}
```

---

## sense 35055, level 7

#### Pack A
### Level 7 (sense 35055, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼の活動は、もはや日本だけでなく、世界全体に影響を及ぼしています。",
      "is_correct": true
    },
    {
      "text": "私は世界の人々と交流するために、毎日英語の勉強を頑張っています。",
      "is_correct": true
    },
    {
      "text": "この製品は、現在世界の数多くの国で販売されています。",
      "is_correct": true
    },
    {
      "text": "世界に一番大きい動物はクジラです。",
      "is_correct": false,
      "error_description": "助詞の混同（に／で）：範囲を示して「その中で一番」と言うときは「世界で一番」が正しい。「世界に一番」は誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "世界を旅してみたい。",
      "is_correct": true
    },
    {
      "text": "世界には色々な国がある。",
      "is_correct": false,
      "error_description": "「ある」は無生物の主語に使えますが、この文では存在を丁寧に述べる「あります」が適切です。"
    },
    {
      "text": "世界には、まだ私たちが訪れていない美しい場所がたくさんあります。",
      "is_correct": true
    },
    {
      "text": "世界には色々な国がある。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35055, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "日本の伝統的な工芸品は、現在では世界から高い評価を受けています。",
      "is_correct": true
    },
    {
      "text": "私はいつか世界一周の旅に出かけたいです。",
      "is_correct": true
    },
    {
      "text": "私たちの会社は、世界の人々が喜んでもらえるような商品を開発しています。",
      "is_correct": false,
      "error_description": "助詞の混同。「喜んでもらう」の動作の受け手を示す助詞は「に」であり、「が」は誤りです。"
    },
    {
      "text": "私たちの会社は、世界の人々に喜んでもらえるような商品を開発しています。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35093, level 1

#### Pack A
### Level 1 (sense 35093, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "ipa": "[ɡʲidʑɯᵝtsɯᵝ]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "技術",
    "既述",
    "叙述",
    "莪朮"
  ],
  "correct_answer": "技術",
  "explanation": "正解です。「技術」は「物を作ったり処理したりするための、専門的な方法や能力。」という意味です。",
  "distractor_explanations": {
    "既述": "「既述」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「き」、清濁・半濁音の対立）。",
    "叙述": "「叙述」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「じょ」、一部の音の違い）。",
    "莪朮": "「莪朮」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「が」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35093, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "ipa": "[gʲidʑutsɯ]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "武術",
    "技術",
    "著述",
    "邪術"
  ],
  "correct_answer": "技術",
  "explanation": "正解です。「技術」は「物を作ったり処理したりする、専門的な方法や能力。」という意味です。",
  "distractor_explanations": {
    "武術": "「武術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ぶ」、一部の音の違い）。",
    "邪術": "「邪術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「じゃ」、一部の音の違い）。",
    "著述": "「著述」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ちょ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35093, level 3

#### Pack A
### Level 3 (sense 35093, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "センサー等を用いた___は、収量の安定化により収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術は、収量の安定化により収益性を向上させます。",
  "correct_answer": "技術",
  "options": [
    "資格",
    "技術",
    "知識",
    "経験"
  ],
  "explanation": "「解析技術」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりする、専門的な方法や能力。",
  "target_word": "技術"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "料理の___を磨くことは楽しいです。",
  "original_sentence": "料理の技術を磨くことは楽しいです。",
  "correct_answer": "技術",
  "options": [
    "経験",
    "技術",
    "知識",
    "資格"
  ],
  "explanation": "「技術を研究する」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりする、専門的な方法や能力。",
  "target_word": "技術"
}
```

#### Pack B
### Level 3 (sense 35093, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "センサー等を用いた新しい___を導入すれば、収量の安定化により収益性を向上させます。",
  "original_sentence": "センサー等を用いた新しい技術を導入すれば、収量の安定化により収益性を向上させます。",
  "correct_answer": "技術",
  "options": [
    "経験",
    "資格",
    "知識",
    "技術"
  ],
  "explanation": "「解析技術」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "target_word": "技術"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___が進んで生活が便利になりました。",
  "original_sentence": "技術が進んで生活が便利になりました。",
  "correct_answer": "技術",
  "options": [
    "経験",
    "知識",
    "資格",
    "技術"
  ],
  "explanation": "「技術を研究する」は専門的な方法を表す固定表現。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "target_word": "技術"
}
```

---
