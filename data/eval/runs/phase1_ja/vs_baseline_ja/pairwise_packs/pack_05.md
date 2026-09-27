# Pairwise review pack 05

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


## sense 35227, level 7

#### Pack A
### Level 7 (sense 35227, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
      "is_correct": true
    },
    {
      "text": "正しいプロセスに守ってください。",
      "is_correct": false,
      "error_description": "助詞の混同。「守る」の目的語を示すには「を」を使います。「に」は方向や着点を示す助詞であり、ここでは不適切です。"
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのです。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "プロセスを経て成長します。",
      "is_correct": true
    },
    {
      "text": "プロセスの結果が出ました。",
      "is_correct": true
    },
    {
      "text": "新しいプロセスが生まれました。",
      "is_correct": true
    },
    {
      "text": "プロセスに経て成長します。",
      "is_correct": false,
      "error_description": "動詞「経る」は経過する過程を表す名詞を受けて助詞「を」をとります。「に」を使うのは誤りです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35227, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのです。",
      "is_correct": true
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスこそが、指紋分析の真髄と言えるでしょう。",
      "is_correct": true
    },
    {
      "text": "この仕事のプロセスを複雑だ。",
      "is_correct": false,
      "error_description": "助詞の混同（を／は）。「複雑だ」は状態を述べる述語で目的語を取らないので、主題を表す「は」を使い、「プロセスは複雑だ」とするのが正しい。"
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
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
      "text": "プロセスが長くて疲れてしまいます。",
      "is_correct": true
    },
    {
      "text": "正しいプロセスで問題を解くことができます。",
      "is_correct": true
    },
    {
      "text": "このプロセスを踏むことで、成功することができます。",
      "is_correct": true
    },
    {
      "text": "彼女は仕事のプロセスに見直した。",
      "is_correct": false,
      "error_description": "助詞の混同（に／を）。「見直す」の対象は目的語なので、「に」ではなく「を」を使い、「プロセスを見直した」が正しい。"
    }
  ]
}
```

---

## sense 35227, level 9

#### Pack A
### Level 9 (sense 35227, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "正しいプロセスを守ってください。"
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "正しいプロセスを守ってください。",
  "chunks": [
    "正しいプロセスを",
    "守って",
    "ください"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "ください",
    "守って",
    "正しいプロセスを"
  ],
  "target_word": "プロセス",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えます。"
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えます。",
  "chunks": [
    "真実を",
    "解き明かすための",
    "静謐かつ論理的",
    "なプロセスそれこそが",
    "指紋分析の",
    "真髄と言えます"
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
    "なプロセスそれこそが",
    "解き明かすための",
    "静謐かつ論理的",
    "指紋分析の",
    "真実を",
    "真髄と言えます"
  ],
  "target_word": "プロセス",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35227, difficulty None)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "私たちは正しいプロセスを経ています。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "私たちは正しいプロセスを経ています。",
  "chunks": [
    "私たちは",
    "正しいプロセスを",
    "経て",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "います",
    "経て",
    "正しいプロセスを",
    "私たちは"
  ],
  "target_word": "プロセス",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "chunks": [
    "再生可能エネルギーの",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "ゼロ化し得ない領域に",
    "おいてCCUSは",
    "極めて重要な役割を担います"
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
    "ゼロ化し得ない領域に",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "おいてCCUSは",
    "再生可能エネルギーの",
    "極めて重要な役割を担います"
  ],
  "target_word": "プロセス",
  "chunk_count": 6
}
```

---

## sense 35293, level 1

#### Pack A
### Level 1 (sense 35293, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "word": "極めて",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "correct_answer": "極めて",
  "word": "極めて",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "大好き": "component",
    "分厚い": "component",
    "認める": "frequency"
  }
}
```

#### Pack B
### Level 1 (sense 35293, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "word": "極めて",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "correct_answer": "極めて",
  "word": "極めて",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "大好き": "component",
    "分厚い": "component",
    "認める": "frequency"
  }
}
```

---

## sense 35293, level 2

#### Pack A
### Level 2 (sense 35293, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "correct_definition": "状態や動作の度合いが、とても高いことを表す副詞。",
  "options": [
    "物体が地球などに引かれる力。重さの原因となる。",
    "人が乗ってペダルをこぎ、車輪を回して進む乗り物。",
    "物事をより完全な状態にするために、手を加えて美しくしたり、技術を高めたりすること。",
    "状態や動作の度合いが、とても高いことを表す副詞。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "不要になったもの、捨てるもの、または材料の切れ端や残りの部分。",
        "状態や動作の度合いが、とても高いことを表す副詞。",
        "existence (viability)",
        "実際に経験して、確かにそうだと感じること。"
      ],
      "correct_answer": "状態や動作の度合いが、とても高いことを表す副詞。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35293, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "correct_definition": "状態や動作の度合いが、とても高いことを表す副詞。",
  "options": [
    "数量や程度が非常に大きいこと。",
    "状態や動作の度合いが、とても高いことを表す副詞。",
    "「本来」は、あるものが初めからそうであること、または当然そうあるべき状態を表す語です。",
    "本物ではないこと。実際には存在しないことや、うそであること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "polyester — a fiber chemically synthesized from petroleum, resistant to wrinkling and quick-drying, used in clothing",
        "状態や動作の度合いが、とても高いことを表す副詞。",
        "指や道具で、ものをこすってまぜること。",
        "轮次 —— 表示顺序的词，尤指做某事的次序，或按顺序分配的角色"
      ],
      "correct_answer": "状態や動作の度合いが、とても高いことを表す副詞。"
    }
  }
}
```

---

## sense 35293, level 7

#### Pack A
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入は、現代社会において極めてに重要な課題である。",
      "is_correct": false,
      "error_description": "副詞「極めて」の後に助詞「に」を付けるのは誤りです。副詞は助詞を介さずに直接形容詞や動詞を修飾します。"
    },
    {
      "text": "その社会的意義は極めて大きい。",
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
      "text": "この問題は極めてに難しい。",
      "is_correct": false,
      "error_description": "助詞の混同。副詞「極めて」の後に格助詞「に」を誤って付加している。副詞は助詞を伴わずに直接形容詞を修飾する。"
    },
    {
      "text": "極めて珍しい花が咲いている。",
      "is_correct": true
    },
    {
      "text": "極めて大切な友達です。",
      "is_correct": true
    },
    {
      "text": "この問題は極めて難しい。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "解決策を見つけるのは極めて難しいです。",
      "is_correct": true
    },
    {
      "text": "彼は極めて慎重に行動しています。",
      "is_correct": true
    },
    {
      "text": "この問題は極めて重要です。",
      "is_correct": true
    },
    {
      "text": "この問題は極めてに重要です。",
      "is_correct": false,
      "error_description": "副詞「極めて」の後に格助詞「に」を付けるのは誤りです。副詞は助詞を伴わず、直接形容詞や動詞を修飾します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "極めて静かな環境に勉強しています。",
      "is_correct": false,
      "error_description": "動作が行われる場所や環境を示す場合は助詞「で」を使います。「に」は存在場所や目的地に使います。"
    },
    {
      "text": "この仕事は極めて責任が重いです。",
      "is_correct": true
    },
    {
      "text": "極めて短い時間で準備を終えました。",
      "is_correct": true
    },
    {
      "text": "極めて静かな環境で勉強しています。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35311, level 1

#### Pack A
### Level 1 (sense 35311, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "correct_answer": "かのう",
  "word": "可能",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "/ka.noː/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "仮寓",
    "可能",
    "稼働",
    "架橋"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "架橋": "「架橋」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「きょ」、一部の音の違い）。",
    "仮寓": "「仮寓」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ぐ」、一部の音の違い）。",
    "稼働": "「稼働」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "correct_answer": "可能",
  "word": "可能",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機能": "component",
    "能力": "component",
    "知能": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35311, difficulty None)
**kanji_to_reading** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "correct_answer": "かのう",
  "word": "可能",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "/kanou/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "歌唱",
    "加号",
    "苦悩",
    "可能"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "苦悩": "「苦悩」は「可能」と一モーラだけ異なる実在語です（1モーラ目: 「か」→「く」、一部の音の違い）。",
    "歌唱": "「歌唱」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「しょ」、一部の音の違い）。",
    "加号": "「加号」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ご」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "correct_answer": "可能",
  "word": "可能",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機能": "component",
    "能力": "component",
    "知能": "component"
  }
}
```

---

## sense 35311, level 2

#### Pack A
### Level 2 (sense 35311, difficulty None)
**definition_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。",
  "options": [
    "歴史や物事の流れの中で、特徴的な出来事や変化が起こった、特別な時期や時代。",
    "「かげつ」と読み、月を数える単位です。特に「一箇月」「二箇月」のように使います。",
    "複数の要素や人を集めて、一つのまとまりを作ること。",
    "物事を行うことができる性質や状態。"
  ]
}
```
**definition_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "tier": "advanced",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物事を行うことができる性質や状態。",
        "原初",
        "模糊 —— 事物的区别或状态不清楚，无法明确判断",
        "a tomato — a red, round vegetable eaten raw or used in cooking"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35311, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。",
  "options": [
    "水が流れるための細長い通路や、人が通るための細長い場所。",
    "物事を行うことができる性質や状態。",
    "国境を越えて商品やサービスを売買すること。特に国際的な商取引を指す。",
    "時間のかかることなく、すぐに終わること。また、移動や作業のスピードが高いこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物事を行うことができる性質や状態。",
        "difficulty",
        "「遣る」は「する」という意味の動詞で、特に何かの仕事や作業を実行することを表します。また、誰かに物を与える意味もあります。",
        "an advantage — a quality something has that brings a good result or is helpful"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  }
}
```

---

## sense 35311, level 3

#### Pack A
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "解決___な方法を、みんなで考えました。",
  "original_sentence": "解決可能な方法を、みんなで考えました。",
  "correct_answer": "可能",
  "options": [
    "完全",
    "可能",
    "必要",
    "容易"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "頂戴したデータにつきましては、専門家の分析を経た上で、来週中に詳細な回答をお返しすることが___です。",
  "original_sentence": "頂戴したデータにつきましては、専門家の分析を経た上で、来週中に詳細な回答をお返しすることが可能です。",
  "correct_answer": "可能",
  "options": [
    "可能",
    "実現",
    "成功",
    "許可"
  ],
  "explanation": "正解です。文脈に合致します。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 4

#### Pack A
### Level 4 (sense 35311, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが___です。",
  "original_sentence": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが___です。",
  "original_sentence": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
  "correct_answer": "可能です",
  "base_form": "可能",
  "form_label": "です形（丁寧）",
  "options": [
    "可能な",
    "可能です",
    "可能だ",
    "可能で"
  ],
  "explanation": "丁寧な文体（polite）の文末に接続する「です形」が適切です。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "彼が手伝うことは___です。",
  "original_sentence": "彼が手伝うことは可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能で",
      "可能性"
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼が手伝うことは___です。",
  "original_sentence": "彼が手伝うことは可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "可能",
    "簡単",
    "重要",
    "必要"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 4 (sense 35311, difficulty None)
**cloze_typed** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
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
**morphology_slot** variant `A`, tier `advanced`
```json
{
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "correct_answer": "可能な",
  "base_form": "可能",
  "form_label": "連体形（な）",
  "options": [
    "可能で",
    "可能な",
    "可能に",
    "可能だ"
  ],
  "explanation": "名詞「体重」を修飾するためには、形状詞の連体形「な」を用いる必要がある",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_typed** variant `B`, tier `advanced`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "早く終われば、間に合うことも___です。",
  "original_sentence": "早く終われば、間に合うことも可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
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
**morphology_slot** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "早く終われば、間に合うことも___です。",
  "original_sentence": "早く終われば、間に合うことも可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "簡単",
    "可能",
    "重要",
    "必要"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 6

#### Pack A
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことを可能となっています。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となっています。",
      "is_correct": true
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも可能となっています、効率的な経営を行うことが。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となってあります。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「ことが」を「ことを」と誤用しています。 活用・アスペクトの誤り：状態変化を表す「可能となる」に「てある」は不自然です。 語順・係り受けの誤り：述語と主語の語順が逆転しており不自然です。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "至難",
    "困難",
    "容易",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態。目標語「可能」の対義語。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `advanced`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "容易",
    "必然",
    "不可能",
    "困難"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態を表し、目標語の対義語となる。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この技術を使えば、新しいエネルギーを生み出すことを可能です。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。",
      "is_correct": true
    },
    {
      "text": "最新のAIにより、複雑な計算を可能しています。",
      "is_correct": false
    },
    {
      "text": "この計画により、一本の新しい工場を建設することが可能です。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「工場」の助数詞は「一本」ではなく「一軒」または「一つ」が適切です。 助詞の混同：「～ことを可能だ」とは言いません。「～ことが可能だ」とするのが正しいです。 活用・アスペクトの誤り：「可能」は形状詞なので「～している」のような動詞の活用はつきません。「可能にしています」や「可能となっています」が正しいです。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "不可能",
    "必須",
    "必然",
    "容易"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態を指し、目標語の対義語となる。"
    }
  }
}
```

---
