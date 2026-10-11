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
      "text": "新しいプロジェクトを成功させるには、チーム全員の協力が必要不可欠です。",
      "is_correct": false,
      "error_description": "「必要不可欠」は同義語を重ねた冗長な表現（重言）であり、T4レベルでは「不可欠」のみを用いるのが適切です。"
    },
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
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "外国語を学ぶとき、毎日少しずつ練習することが不可欠です。",
      "is_correct": true
    },
    {
      "text": "新しいアイデアを生み出すには、さまざまな視点を持つことが不可欠です。",
      "is_correct": true
    },
    {
      "text": "この実験を成功させるには、正確なデータ測定が不可欠になります。",
      "is_correct": true
    },
    {
      "text": "新しいアイデアを生み出すには、さまざまな視点を持つこと不可欠です。",
      "is_correct": false,
      "error_description": "「不可欠」は形状詞（ナ形容詞）であり、その主語を示すためには主格助詞「が」が必要です。「こと」の直後に「が」を省略することはできません。"
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
    "矢がら",
    "やり手",
    "夜学",
    "軈て"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "矢がら": "「矢がら」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「ら」、一部の音の違い）。",
    "やり手": "「やり手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。",
    "夜学": "「夜学」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「く」、一部の音の違い）。"
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
    "わざと",
    "すでに",
    "決して"
  ],
  "explanation": "正解です。水が大地に吸い込まれ、時間が経過した後に根の網目に伝わっていくという自然な時間の経過を表しています。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "やがて"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "___彼は自分の道を見つける。",
  "original_sentence": "軈て彼は自分の道を見つける。",
  "correct_answer": "やがて",
  "options": [
    "すぐに",
    "すでに",
    "やがて",
    "決して"
  ],
  "explanation": "文脈に最も適しています。「やがて」は時間の経過を経て結果が生じることを自然に表現します。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```

---

## sense 35419, level 7

#### Pack A
### Level 7 (sense 35419, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "やがて成長の過程において、植物は時折厳しい気候に晒されながらも、力強く茎を伸ばしていく。",
      "is_correct": true
    },
    {
      "text": "この憧れの感情は、やがてグローバルな大衆向けブランドによって巧妙に咀嚼され、誰もが手が届く価格帯へと昇華されるのだ。",
      "is_correct": true
    },
    {
      "text": "水は瞬く間に闇色の大地へと吸い込まれ、やがて目に見えぬ根の網目へと伝わっていくだろう。",
      "is_correct": true
    },
    {
      "text": "やがてに、その答えが分かる時が来る。",
      "is_correct": false,
      "error_description": "「やがて」は副詞であるため、格助詞「に」を直接結びつけて「やがてに」とすることはできません。副詞は単独で用言や文全体を修飾します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "軈てすべては良い方向へ向かう。",
      "is_correct": true
    },
    {
      "text": "軈て彼は自分の道に見つける。",
      "is_correct": false,
      "error_description": "「見つける」は他動詞であり、目的語を示す助詞「を」を使う必要があります。「に」は方向や存在場所を表すため、この文脈では不適切です。"
    },
    {
      "text": "軈て真実が明らかになるだろう。",
      "is_correct": true
    },
    {
      "text": "軈て彼は自分の道を見つける。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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
  "ipa": "/fukuzatsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "福笹",
    "服罪",
    "伏罪",
    "複雑"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「物事の仕組みや内容がからみ合って、簡単に理解できない様子。」という意味です。",
  "distractor_explanations": {
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。",
    "伏罪": "「伏罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "服罪": "「服罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。"
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

#### Pack B
### Level 3 (sense 35615, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題はとても___です。",
  "original_sentence": "この問題はとても複雑です。",
  "correct_answer": "複雑",
  "options": [
    "明確",
    "複雑",
    "簡単",
    "単純"
  ],
  "explanation": "正解です。文脈に最も適切です。",
  "distractor_tags": {},
  "word_definition": "物事の仕組みや内容がからみ合って、簡単に理解できない様子。",
  "target_word": "複雑"
}
```

---

## sense 35615, level 4

#### Pack A
### Level 4 (sense 35615, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___な手順で作業を進めています。",
  "original_sentence": "複雑な手順で作業を進めています。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹（「な」に続く形）",
  "options": [
    "複雑に",
    "複雑さ",
    "複雑な",
    "複雑"
  ],
  "explanation": "形状詞の語幹に「な」が付いて「複雑な話」と連体修飾になる",
  "word_definition": "物事の仕組みや内容がからみ合って、簡単に理解できない様子。",
  "target_word": "複雑"
}
```

#### Pack B
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "複雑な手順で作業を進めています。",
      "is_correct": true
    },
    {
      "text": "複雑な機械を分解しています。",
      "is_correct": true
    },
    {
      "text": "複雑な形をしている石です。",
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

## sense 36181, level 4

#### Pack A
### Level 4 (sense 36181, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と___な創造への移行を意味する重要なプロセスだ。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "correct_answer": "新た",
  "base_form": "新た",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "options": [
    "新た",
    "新たに",
    "新ただ",
    "新たなら"
  ],
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "word_definition": "今までと違う、新しい状態になることです。",
  "target_word": "新た"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "戦後の都市計画において、ブルータリズムは機能性を重視した___な住宅様式として普及しました。",
  "original_sentence": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及しました。",
  "correct_answer": "新たな",
  "base_form": "新た",
  "form_label": "連体形",
  "options": [
    "新たに",
    "新たで",
    "新たな",
    "新ただ"
  ],
  "explanation": "名詞「住宅様式」を修飾するためには連体形の「新たな」が必要です。",
  "word_definition": "今までと違う、新しい状態になることです。",
  "target_word": "新た"
}
```

#### Pack B
### Level 4 (sense 36181, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "戦後の都市計画において、ブルータリズムは機能性を重視した___な住宅様式として普及しました。",
  "original_sentence": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及しました。",
  "correct_answer": "新た",
  "base_form": "新た",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "options": [
    "新たに",
    "新た",
    "新ただ",
    "新たなら"
  ],
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "word_definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
  "target_word": "新た"
}
```

---

## sense 36181, level 6

#### Pack A
### Level 6 (sense 36181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題に浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなに課題として浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなを課題として浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    }
  ],
  "explanation": "助詞・活用の誤り：「新た」を副詞的に使う場合は「新たに」とするのが正しい活用・連語の形であり、「新たなに」という形は文法的に誤りです。 助詞の混同：「新たな」は連体詞として機能し、直後の名詞「課題」を修飾すべきです。間に目的語を示す「を」を入れると、項構造が破壊され文法的に誤りとなります。 連語・助詞の誤り：「浮上する」は表面に現れることを意味し、通常「〜として」や「が」を伴います。「課題に浮上する」という表現は、対象語の連語および助詞の取り方が不自然です。",
  "target_word": "新た"
}
```

#### Pack B
### Level 6 (sense 36181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなを課題として浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題に浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなに課題として浮上しているのです。",
      "is_correct": false
    }
  ],
  "explanation": "助詞・活用の誤り：形状詞「新た」に副詞的な誤った接尾辞「に」が直接付いています。「新たな」として名詞を修飾するのが正しい用法です。 助詞の混同：形状詞「新た」の後に格助詞「を」が誤って配置されています。名詞「課題」を修飾する連体修飾語としては機能せず、文構造が破綻しています。 連語・格の誤り：「浮上する」は「〜として」や「〜が」といった格助詞を伴って、何かが表面化することを表します。「課題に浮上する」という結びつきは不自然です。",
  "target_word": "新た"
}
```

---
