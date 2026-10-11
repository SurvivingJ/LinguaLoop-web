# Pairwise review pack 03

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


## sense 35039, level 4

#### Pack A
### Level 4 (sense 35039, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "ミニマリストの思想に基づき、必要な要素だけを残すことで、居住者はより穏やかな日常を送ることが___ます。",
  "original_sentence": "ミニマリストの思想に基づき、必要な要素だけを残すことで、居住者はより穏やかな日常を送ることができます。",
  "correct_answer": "でき",
  "base_form": "できる",
  "form_label": "連用形（ます形の語幹）",
  "options": [
    "できない",
    "できて",
    "でき",
    "できた"
  ],
  "explanation": "「〜ことができます」の連用形（ます形の語幹）。",
  "word_definition": "「出来る」は動詞で、物事を行う能力がある、または実現可能であることを表します。",
  "target_word": "でき"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼は難しい問題を解くことが___ました。",
  "original_sentence": "彼は難しい問題を解くことができました。",
  "correct_answer": "でき",
  "base_form": "できる",
  "form_label": "連用形",
  "options": [
    "できる",
    "できた",
    "できない",
    "でき"
  ],
  "explanation": "「ます」に接続するための連用形「でき」が適切です。",
  "word_definition": "「出来る」は動詞で、物事を行う能力がある、または実現可能であることを表します。",
  "target_word": "でき"
}
```

#### Pack B
### Level 4 (sense 35039, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "必要な要素だけ___残すことで、より穏やかな日常を送れます。",
  "original_sentence": "必要な要素だけを残すことで、より穏やかな日常を送れます。",
  "options": [
    "で",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "でき",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「送る」の直接目的語（日常）を標示する格助詞です。"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "適切な言葉___発信することで、小さくても確実なファンを獲得できます。",
  "original_sentence": "適切な言葉で発信することで、小さくても確実なファンを獲得できます。",
  "options": [
    "が",
    "で",
    "を",
    "に"
  ],
  "correct_answer": "で",
  "target_word": "でき",
  "error_tags": {
    "に": "location_vs_target",
    "を": "object_marking",
    "が": "topic_vs_subject"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "手段・方法を示す格助詞であり、「適切な言葉で」は発信の手段を表す"
    }
  }
}
```

---

## sense 35039, level 6

#### Pack A
### Level 6 (sense 35039, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "ムダを省きながら収量の最適化を図れます。",
      "is_correct": true
    },
    {
      "text": "ムダを省きながら収量の最適化ができると。",
      "is_correct": false
    },
    {
      "text": "ムダを省きながら収量の最適化をでき。",
      "is_correct": false
    },
    {
      "text": "ムダを省きながら収量の最適化ができります。",
      "is_correct": false
    }
  ],
  "explanation": "活用の誤り：「できる」の可能形は「できる」そのもの、または丁寧語で「できます」です。「できります」という活用形は存在しません。 文法・終止形の誤り：「でき」は連用形であり、文を終えるためには「ます」や「る」などの終止形が必要です。単独で文末に置くことはできません。 係り受け・文の完結性の誤り：「と」で終わっており、引用や条件節の一部となっていますが、独立した文として完結していません。文脈として不適切です。",
  "target_word": "でき"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "でき",
  "relation": "antonym",
  "options": [
    "簡単",
    "上手",
    "得意",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行う能力がある、または実現可能であることを表します。",
      "explanation": "目標語の『できる（可能である）』という語義に対する直接的な対義語です。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "でき",
  "relation": "antonym",
  "options": [
    "ある",
    "わかる",
    "しない",
    "できない"
  ],
  "correct_answer": "できない",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行う能力がある、または実現可能であることを表します。",
      "explanation": "能力や可能性の欠如を表す、直接的な対義語です。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35039, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることができます。",
      "is_correct": true
    },
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることをできます。",
      "is_correct": false
    },
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることができってしまいます。",
      "is_correct": false
    },
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図る、ことができます。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「できる」は可能を表す場合、前の動詞を「〜ことが」で受けるのが規範的であり、「〜ことをできます」とするのは格助詞の誤用です。 活用・アスペクトの誤り：「でき」の後に「て」を接続する際、促音便（っ）は生じません。「できてしまいます」が正しい形です。 語順・係り受けの誤り：「図る」で一度区切られているため、「ことができます」との係り受けが破壊され、文法的に誤った構造になっています。",
  "target_word": "でき"
}
```

---

## sense 35039, level 7

#### Pack A
### Level 7 (sense 35039, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることが出来ります。",
      "is_correct": false,
      "error_description": "活用：「できます」を漢字の語幹「出来」に「ります」を続けた誤った混成形。"
    },
    {
      "text": "ミニマリストの思想に基づき、必要な要素だけを残すことで、居住者はより穏やかな日常を送ることができます。",
      "is_correct": true
    },
    {
      "text": "一方で、農村経済全体を見ると、労働需要の質が変化するという社会経済的影響も無視できません。",
      "is_correct": true
    },
    {
      "text": "誰に何を求めているか分析し、適切な言葉で発信することで、小さくても確実なファンを獲得できます。",
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
      "text": "彼は努力してついに目標を達成できました。",
      "is_correct": true
    },
    {
      "text": "友達と協力すれば成功できます。",
      "is_correct": true
    },
    {
      "text": "彼は難しい問題を解くことができました。",
      "is_correct": true
    },
    {
      "text": "私は日本語に挨拶ができます。",
      "is_correct": false,
      "error_description": "手段や方法を表す助詞は「で」が適切ですが、「に」が誤って使われています。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35039, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "必要な要素だけを残すことで、より穏やかな日常を送れます。",
      "is_correct": true
    },
    {
      "text": "これにより、ムダを省きながら収量の「最適化」を図ることが出来ります。",
      "is_correct": false,
      "error_description": "活用：「できます」を漢字の語幹「出来」に「ります」を続けた誤った混成形。"
    },
    {
      "text": "適切な言葉で発信することで、小さくても確実なファンを獲得できます。",
      "is_correct": true
    },
    {
      "text": "農村経済全体を見ると、労働需要の質の変化という影響も無視できません。",
      "is_correct": true
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
  "ipa": "sekaɪ",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "耳介",
    "市会",
    "世界",
    "地界"
  ],
  "correct_answer": "世界",
  "explanation": "正解です。「世界」は「地球全体。また、人間の活動の及ぶすべての範囲。社会全体。」という意味です。",
  "distractor_explanations": {
    "市会": "「市会」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「し」、一部の音の違い）。",
    "耳介": "「耳介」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「じ」、一部の音の違い）。",
    "地界": "「地界」は「世界」と一モーラだけ異なる実在語です（1モーラ目: 「せ」→「ち」、一部の音の違い）。"
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

#### Pack B
### Level 3 (sense 35055, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼は___中を旅して回りました。",
  "original_sentence": "彼は世界中を旅して回りました。",
  "correct_answer": "世界",
  "options": [
    "国家",
    "宇宙",
    "世界",
    "地域"
  ],
  "explanation": "正解です。文脈「彼は～中を旅して回りました」に最も適しており、地球全体という意味で使われています。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
  "target_word": "世界"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼は___で一番速く走れます。",
  "original_sentence": "彼は世界で一番速く走れます。",
  "correct_answer": "世界",
  "options": [
    "世界",
    "地域",
    "時間",
    "方法"
  ],
  "explanation": "正解です。文脈「彼は～で一番速く走れます」において、比較の範囲として「地球全体・全人類」を指す「世界」が適切です。",
  "distractor_tags": {},
  "word_definition": "地球全体。また、人間の活動の及ぶすべての範囲。社会全体。",
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
      "text": "広い世界を三つ見てみたいですね。",
      "is_correct": false
    },
    {
      "text": "世界は広いです見てみたいですね。",
      "is_correct": false
    },
    {
      "text": "広い世界を見てみたいですね。",
      "is_correct": true
    },
    {
      "text": "世界へ広いを見てみたいですね。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「世界」のような抽象的な広がりや集合概念には、個数を数える助数詞「三つ」は不適切です。 語順・係り受けの誤り：形容詞「広い」が名詞「世界」を修飾する関係が崩れており、文法的に不自然な語順です。正しくは「広い世界を」です。 文構造の誤り：二つの節「世界は広いです」と「見てみたいですね」が接続詞なしで不適切に結合されており、文として成立していません。",
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

---

## sense 35093, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 35093, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "技術",
  "pronunciation": "ぎじゅつ",
  "ipa": "gidʑɯtsɯ",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "美術",
    "武術",
    "義塾",
    "技術"
  ],
  "correct_answer": "技術",
  "explanation": "正解です。「技術」は「物を作ったり処理したりするための、専門的な方法や能力。」という意味です。",
  "distractor_explanations": {
    "美術": "「美術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「び」、一部の音の違い）。",
    "武術": "「武術」は「技術」と一モーラだけ異なる実在語です（1モーラ目: 「ぎ」→「ぶ」、一部の音の違い）。",
    "義塾": "「義塾」は「技術」と一モーラだけ異なる実在語です（3モーラ目: 「つ」→「く」、一部の音の違い）。"
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
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "センサー等を用いた___導入は、収量の安定化により収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
  "correct_answer": "技術",
  "options": [
    "天気",
    "技術",
    "習慣",
    "感情"
  ],
  "explanation": "正解です。文脈「センサー等を用いた____導入」において、専門的な方法や手段を導入するという意味で「技術」が最も適切です。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "target_word": "技術"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "私たちは___を勉強しています。",
  "original_sentence": "私たちは技術を勉強しています。",
  "correct_answer": "技術",
  "options": [
    "技術",
    "運命",
    "天気",
    "感情"
  ],
  "explanation": "正解です。文脈「勉強しています」に対して、習得可能な専門的な方法や能力である「技術」が最も自然に適合します。",
  "distractor_tags": {},
  "word_definition": "物を作ったり処理したりするための、専門的な方法や能力。",
  "target_word": "技術"
}
```

---

## sense 35093, level 4

#### Pack A
### Level 4 (sense 35093, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析の技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析の技術を活用した「精密農業」が注目されています。",
  "options": [
    "を",
    "が",
    "で",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「活用する」の直接目的語を標示する。"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "最新の技術___使ってロボットを作りました。",
  "original_sentence": "最新の技術を使ってロボットを作りました。",
  "options": [
    "が",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "が": "topic_vs_subject",
    "で": "instrument",
    "に": "location_vs_target"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「使う」の直接目的語を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35093, difficulty None)
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "近年、センサーやデータ解析技術___活用した「精密農業」が注目されています。",
  "original_sentence": "近年、センサーやデータ解析技術を活用した「精密農業」が注目されています。",
  "options": [
    "が",
    "で",
    "に",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "技術",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「活用する」の直接目的語（対象）を示す格助詞です。"
    }
  }
}
```

---

## sense 35111, level 1

#### Pack A
### Level 1 (sense 35111, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "ipa": "joɾu",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "去る",
    "因る",
    "剪る",
    "狩る"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "狩る": "「狩る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「か」、一部の音の違い）。",
    "去る": "「去る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「さ」、一部の音の違い）。",
    "剪る": "「剪る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「き」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35111, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "因る",
  "pronunciation": "よる",
  "ipa": "/joɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "ネル",
    "世々",
    "彫る",
    "因る"
  ],
  "correct_answer": "因る",
  "explanation": "正解です。「因る」は「物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。」という意味です。",
  "distractor_explanations": {
    "世々": "「世々」は「因る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「よ」、一部の音の違い）。",
    "ネル": "「ネル」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「ね」、一部の音の違い）。",
    "彫る": "「彫る」は「因る」と一モーラだけ異なる実在語です（1モーラ目: 「よ」→「え」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
