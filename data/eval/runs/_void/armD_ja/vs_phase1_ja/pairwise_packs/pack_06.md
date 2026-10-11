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


## sense 35341, level 7

#### Pack A
### Level 7 (sense 35341, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "そこに、発酵の不可欠な役割が凝縮されているのである。",
      "is_correct": true
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠の工程です。",
      "is_correct": false,
      "error_description": "形状詞「不可欠」が名詞を修飾する際は「不可欠な」の形を使います。「不可欠の」は誤りです。"
    },
    {
      "text": "特に多色印刷の場合、色ごとに異なる版木を使い分ける必要があり、職人たちの高度な技術と協力が不可欠です。",
      "is_correct": true
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
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
      "text": "信頼は友達で不可欠なものです。",
      "is_correct": false,
      "error_description": "「不可欠」の対象（誰にとって不可欠か）を示す場合は、助詞「に」または「にとって」を用います。場所や手段を表す「で」を用いるのは誤りです。"
    },
    {
      "text": "睡眠は不可欠な要素です。",
      "is_correct": true
    },
    {
      "text": "信頼は友達に不可欠なものです。",
      "is_correct": true
    },
    {
      "text": "協力も不可欠なものです。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35341, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "特に多色印刷の場合、色ごとに異なる版木を使い分ける必要があり、職人たちの高度な技術と協力が不可欠です。",
      "is_correct": true
    },
    {
      "text": "そこに、発酵の不可欠な役割が凝縮されているのである。",
      "is_correct": true
    },
    {
      "text": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
      "is_correct": true
    },
    {
      "text": "健康な生活には、バランスの良い食事を不可欠です。",
      "is_correct": false,
      "error_description": "「不可欠」は形状詞（ナ形容詞）であり、必要なものを示す主語には助詞「が」を使います。「を」を使うのは動詞（例：「必要とする」）の場合であり、形状詞の「不可欠」には不適切です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "良い関係を保つには、お互いの思いやりが不可欠です。",
      "is_correct": true
    },
    {
      "text": "外国語を学ぶとき、毎日の努力が不可欠になります。",
      "is_correct": true
    },
    {
      "text": "良い関係を保つには、お互いの思いやりに不可欠です。",
      "is_correct": false,
      "error_description": "助詞の混同。「不可欠」は性質を表す形状詞であり、その性質の主体（何が不可欠か）を示す場合は主格の助詞「が」を用います。「に」は対象や方向を表すことが多く、ここでは不適切です。"
    },
    {
      "text": "楽しい旅行には、事前の計画が不可欠な要素です。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35419, level 1

#### Pack A
### Level 1 (sense 35419, difficulty None)
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "ipa": "/jaɡate/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "約手",
    "山手",
    "軈て",
    "簳"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「時間が経過した後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、漢字で書く文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "約手": "「約手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「く」、一部の音の違い）。",
    "山手": "「山手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「ま」、一部の音の違い）。",
    "簳": "「簳」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「ら」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35419, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "ipa": "/jaɡate/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "遣り手",
    "軈て",
    "苦手",
    "野外"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "苦手": "「苦手」は「軈て」と一モーラだけ異なる実在語です（1モーラ目: 「や」→「に」、一部の音の違い）。",
    "野外": "「野外」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「い」、一部の音の違い）。",
    "遣り手": "「遣り手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35419, level 3

#### Pack A
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "水は瞬く間に闇色の大地へと吸い込まれ、___目に見えぬ根の網目へと伝わっていくだろう。",
  "original_sentence": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
  "correct_answer": "軈て",
  "options": [
    "突如",
    "決して",
    "軈て",
    "実に"
  ],
  "explanation": "正解です。水が大地に吸い込まれ、時間の経過を経て根の網目に広がるという自然なプロセスを表す「軈て」が適切です。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___彼らは故郷へ帰るだろう。",
  "original_sentence": "軈て彼らは故郷へ帰るだろう。",
  "correct_answer": "軈て",
  "options": [
    "すでに",
    "けっして",
    "軈て",
    "とくに"
  ],
  "explanation": "正解です。文脈に合う副詞「軈て」が入ります。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "水は瞬く間に闇色の大地へと吸い込まれ、___目に見えぬ根の網目へと伝わっていくだろう。",
  "original_sentence": "水は瞬く間に闇色の大地へと吸い込まれ、やがて目に見えぬ根の網目へと伝わっていくだろう。",
  "correct_answer": "やがて",
  "options": [
    "やがて",
    "すでに",
    "決して",
    "すぐに"
  ],
  "explanation": "正解です。文脈に合い、時間が経過した後の自然な成り行きを表します。",
  "distractor_tags": {},
  "word_definition": "時間が経過した後に何かが起こることを表す副詞です。「やがて」と同じ意味ですが、漢字で書く文語的な表現です。",
  "target_word": "やがて"
}
```

---

## sense 35419, level 6

#### Pack A
### Level 6 (sense 35419, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "彼は静かに眠りにつくやがて。",
      "is_correct": false
    },
    {
      "text": "やがて彼は静かに眠りにつくのだった。",
      "is_correct": false
    },
    {
      "text": "やがてに彼は静かに眠りにつく。",
      "is_correct": false
    },
    {
      "text": "やがて準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    }
  ],
  "explanation": "語順・係り受けの誤り：「やがて」は文末の「のだった」といった様相・回想の表現と直接結びつくことができません。文全体を包摂する位置に置く必要があります。 助詞の混同：「やがて」は副詞であり、格助詞「に」を伴うことはできません。副詞は単独で用言を修飾します。 語順・係り受けの誤り：「やがて」は修飾する動詞「眠りにつく」の前に配置されるべき副詞です。文末に置くことは統語的に誤りです。",
  "target_word": "やがて"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "やがて冷たい風が吹き始める。",
      "is_correct": false
    },
    {
      "text": "やがて夜空に星が輝き始める。",
      "is_correct": true
    },
    {
      "text": "やがて冷たい風が吹き始める。",
      "is_correct": false
    },
    {
      "text": "冷たい風がやがて吹き始める。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：副詞「やがて」の後に主語を示す「が」ではなく、誤って「を」が使われています。「風を」は目的語となり、自動詞「吹き始める」と結びつきません。 活用・アスペクトの誤り：「やがて」は未来や経過を表す副詞ですが、動詞が完了・結果の「てある」形式である「吹いてある」になっており、アスペクトが矛盾しています。 語順・係り受けの誤り：時の副詞「やがて」は通常、述語に近い位置か文頭に置かれますが、主語と述語の間に割り込むことで自然な係り受けが破壊されています。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 6 (sense 35419, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈て準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    },
    {
      "text": "準備が軈て整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備に整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備が整く、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「整う」は自動詞であり、主語を示す助詞は「が」が適切です。「準備に」という表現は、格助詞の取り違えです。 活用・アスペクトの誤り：自動詞「整う」の連用形は「整い」ですが、誤って「整く」と活用させています。 語順・係り受けの誤り：副詞「軈て」は通常、文頭や時間の経過を示す句の後に置かれます。「準備が」と「整い」の間に挿入されるのは不自然です。",
  "target_word": "軈て"
}
```

---

## sense 35419, level 7

#### Pack A
### Level 7 (sense 35419, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈て成長の過程において、植物は時折厳しい気候に晒されながらも、力強く茎を伸ばしていく。",
      "is_correct": true
    },
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
      "is_correct": true
    },
    {
      "text": "悲しみは軈てに喜びに変わる。",
      "is_correct": false,
      "error_description": "副詞「軈て」の後に不要な助詞「に」が付いています。「軈て」はそれ単独で副詞として機能するため、助詞は必要ありません。"
    },
    {
      "text": "この憧れの感情は、軈てグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
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
      "text": "悲しみは軈て喜びに変わる。",
      "is_correct": true
    },
    {
      "text": "軈ての悲しみは喜びに変わる。",
      "is_correct": false,
      "error_description": "副詞の誤用。「軈て」は副詞なので「の」を付けて名詞を直接修飾することはできません。"
    },
    {
      "text": "軈て彼らは故郷へ帰るだろう。",
      "is_correct": true
    },
    {
      "text": "努力は軈て大きな力となる。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35419, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、やがて目に見えぬ根の網目へと伝わっていくだろう。",
      "is_correct": true
    },
    {
      "text": "やがてに春が訪れ、花が咲き誇る。",
      "is_correct": false,
      "error_description": "「やがて」は副詞であるため、後に助詞「に」を伴うことはできません。副詞はそのまま用言や節を修飾します。"
    },
    {
      "text": "やがて成長の過程において、植物は時折厳しい気候に晒されながらも、力強く茎を伸ばしていく。",
      "is_correct": true
    },
    {
      "text": "この憧れの感情は、やがてグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
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
      "text": "やがて彼は静かに眠りにつくに。",
      "is_correct": false,
      "error_description": "終止形「つく」の後に余計な助詞「に」が付いており、文が不完全になっています。副詞「やがて」は動詞を修飾しますが、動詞の終止形の後ろに格助詞を付けることはできません。"
    },
    {
      "text": "やがて彼は静かに眠りにつく。",
      "is_correct": true
    },
    {
      "text": "やがて夜空に星が輝き始める。",
      "is_correct": true
    },
    {
      "text": "やがて空が赤く染まり、夕暮れとなる。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35615, level 1

#### Pack A
### Level 1 (sense 35615, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/ɸɯkɯzatsɯ/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複雑",
    "錯雑",
    "福笹",
    "覆没"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "錯雑": "「錯雑」は「複雑」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「さ」、一部の音の違い）。",
    "覆没": "「覆没」は「複雑」と一モーラだけ異なる実在語です（3モーラ目: 「ざ」→「ぼ」、一部の音の違い）。",
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35615, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/ɸukuzatsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複座機",
    "福笹",
    "伏罪",
    "複雑"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "複座機": "「複座機」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「き」、一部の音の違い）。",
    "伏罪": "「伏罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35615, level 3

#### Pack A
### Level 3 (sense 35615, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題はとても___です。",
  "original_sentence": "この問題はとても複雑です。",
  "correct_answer": "複雑",
  "options": [
    "簡単",
    "複雑",
    "単調",
    "明確"
  ],
  "explanation": "正解です。文脈に最も適切です。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

#### Pack B
### Level 3 (sense 35615, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題はとても___です。",
  "original_sentence": "この問題はとても複雑です。",
  "correct_answer": "複雑",
  "options": [
    "複雑",
    "簡単",
    "明確",
    "単純"
  ],
  "explanation": "正解です。文脈にある「多くの要素がからみ合って簡単には理解できない」という意味に合致します。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

---

## sense 35615, level 4

#### Pack A
### Level 4 (sense 35615, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "人間の気持ちは___ですね。",
  "original_sentence": "人間の気持ちは複雑ですね。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹（「で」に続く形）",
  "options": [
    "複雑に",
    "複雑な",
    "複雑",
    "複雑さ"
  ],
  "explanation": "形状詞の語幹で、後ろの「で」（だ・で）に直接つながり、「通路が複雑で」と述語になる",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "物語の筋が___になっています。",
  "original_sentence": "物語の筋が複雑になっています。",
  "correct_answer": "複雑に",
  "base_form": "複雑",
  "form_label": "連用形（に）",
  "options": [
    "複雑さ",
    "複雑に",
    "複雑な",
    "複雑だ"
  ],
  "explanation": "「～になる」に接続するため、形状詞の連用形「に」が必要",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

#### Pack B
### Level 4 (sense 35615, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___な問題を解いています。",
  "original_sentence": "複雑な問題を解いています。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹（「な」に続く形）",
  "options": [
    "複雑",
    "複雑な",
    "複雑さ",
    "複雑に"
  ],
  "explanation": "形状詞の語幹に「な」が付いて「複雑な話」と連体修飾になる",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

---

## sense 35615, level 7

#### Pack A
### Level 7 (sense 35615, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "人間の気持ちは複雑ですね。",
      "is_correct": true
    },
    {
      "text": "複雑の話は苦手だ。",
      "is_correct": false,
      "error_description": "助詞・活用の誤り。形状詞「複雑」が名詞を修飾するときは「の」ではなく「な」を使い、「複雑な話」が正しい形です。"
    },
    {
      "text": "複雑なルールで困っています。",
      "is_correct": true
    },
    {
      "text": "この問題はとても複雑です。",
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
      "text": "複雑な問題を解くのは大変です。",
      "is_correct": true
    },
    {
      "text": "物語の筋が複雑だになっています。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り。形状詞「複雑」の連用形は「複雑に」であり、「複雑だに」とはなりません。"
    },
    {
      "text": "物語の筋が複雑になっています。",
      "is_correct": true
    },
    {
      "text": "複雑な人間関係に疲れています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35615, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この問題はとても複雑です。",
      "is_correct": true
    },
    {
      "text": "社会の仕組みは複雑でですね。",
      "is_correct": false,
      "error_description": "形状詞「複雑」の語幹に直接接続助詞「で」を付けることはできません。「複雑ですね」が正しい形です。"
    },
    {
      "text": "社会の仕組みは複雑ですね。",
      "is_correct": true
    },
    {
      "text": "この機械の構造は非常に複雑です。",
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
      "text": "複雑な問題を解いています。",
      "is_correct": true
    },
    {
      "text": "複雑な計算はできないです。",
      "is_correct": true
    },
    {
      "text": "この機械の構造は複雑です。",
      "is_correct": true
    },
    {
      "text": "この規則は複雑くて、覚えにくい。",
      "is_correct": false,
      "error_description": "活用の誤り。「複雑」は形状詞（ナ形容詞）なので、い形容詞のように「くて」とは言わず、「複雑で」と接続します。"
    }
  ]
}
```

---

## sense 36181, level 1

#### Pack A
### Level 1 (sense 36181, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "新た",
  "pronunciation": "あらた",
  "ipa": "/aɾata/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "新た",
    "わらた",
    "荒らす",
    "アラブ"
  ],
  "correct_answer": "新た",
  "explanation": "正解です。「新た」は「「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。」という意味です。",
  "distractor_explanations": {
    "わらた": "「わらた」は「新た」と一モーラだけ異なる実在語です（1モーラ目: 「あ」→「わ」、一部の音の違い）。",
    "荒らす": "「荒らす」は「新た」と一モーラだけ異なる実在語です（3モーラ目: 「た」→「す」、一部の音の違い）。",
    "アラブ": "「アラブ」は「新た」と一モーラだけ異なる実在語です（3モーラ目: 「た」→「ぶ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 36181, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "新た",
  "pronunciation": "あらた",
  "ipa": "/aɾata/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "荒木",
    "新た",
    "アラブ",
    "粗砥"
  ],
  "correct_answer": "新た",
  "explanation": "正解です。「新た」は「今までと違う、新しい状態になることです。」という意味です。",
  "distractor_explanations": {
    "荒木": "「荒木」は「新た」と一モーラだけ異なる実在語です（3モーラ目: 「た」→「き」、一部の音の違い）。",
    "粗砥": "「粗砥」は「新た」と一モーラだけ異なる実在語です（3モーラ目: 「た」→「と」、一部の音の違い）。",
    "アラブ": "「アラブ」は「新た」と一モーラだけ異なる実在語です（3モーラ目: 「た」→「ぶ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
