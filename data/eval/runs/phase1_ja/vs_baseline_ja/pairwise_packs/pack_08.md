# Pairwise review pack 08

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


## sense 35615, level 2

#### Pack A
### Level 2 (sense 35615, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "correct_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "options": [
    "ある物が、折れ曲がること。",
    "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
    "物事の程度や勢いが、次第に強くなったり大きくなったりすること。",
    "音楽や芸術で、強い感情や想像力を大切にする、19世紀ごろのヨーロッパの芸術の流れや、そのような雰囲気のこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to win",
        "大好きは、何かをとても好きなことです。",
        "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
        "ある目標や問題に対して、積極的にかかわって努力すること。"
      ],
      "correct_answer": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35615, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "correct_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "options": [
    "人間が目的を持って意識的に身体や知能を使って行う活動。特に、経済的な価値を生み出すための仕事。",
    "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
    "位置や状態を変える。動作をする。",
    "同じ動作や言葉を、もう一度行うこと。または、同じことを何度も言うこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ものを はさんで もつ どうぐです。",
        "打磨 —— 摩擦刀具或工具的表面，使其更锋利或更有光泽",
        "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
        "发电 —— 产生电能这一行为或过程"
      ],
      "correct_answer": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。"
    }
  }
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
    "静か",
    "複雑",
    "親切",
    "元気"
  ],
  "explanation": "「この問題は複雑だ」は、問題が多くの要素からみ合って理解しにくいという意味で自然に成り立つ。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この地図は___て道がわかりません。",
  "original_sentence": "この地図は複雑すぎて道がわかりません。",
  "correct_answer": "複雑",
  "options": [
    "親切",
    "元気",
    "複雑",
    "丈夫"
  ],
  "explanation": "「複雑すぎて説明できない」は、要素が多くからみ合っていて説明しきれないという意味で自然である。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑すぎ"
}
```

---

## sense 35615, level 4

#### Pack A
### Level 4 (sense 35615, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "人間の気持ちは___ですね。",
  "original_sentence": "人間の気持ちは複雑ですね。",
  "target_word": "複雑",
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑だ",
      "複雑さ"
    ],
    "accepted_normalized": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑だ",
      "複雑さ"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "物語の筋が___になっています。",
  "original_sentence": "物語の筋が複雑になっています。",
  "target_word": "複雑",
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑だ",
      "複雑さ"
    ],
    "accepted_normalized": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑だ",
      "複雑さ"
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
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___気持ちで学校に行きました。",
  "original_sentence": "複雑な気持ちで学校に行きました。",
  "target_word": "複雑な",
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑な"
    ],
    "accepted_normalized": [
      "複雑な"
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
  "sentence_with_blank": "___気持ちで学校に行きました。",
  "original_sentence": "複雑な気持ちで学校に行きました。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹（「で」に続く形）",
  "options": [
    "複雑",
    "複雑さ",
    "複雑な",
    "複雑に"
  ],
  "explanation": "形状詞の語幹で、後ろの「で」（だ・で）に直接つながり、「通路が複雑で」と述語になる",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑な"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___ルールを覚えるのは大変です。",
  "original_sentence": "複雑なルールを覚えるのは大変です。",
  "target_word": "複雑な",
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑な"
    ],
    "accepted_normalized": [
      "複雑な"
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
  "sentence_with_blank": "___ルールを覚えるのは大変です。",
  "original_sentence": "複雑なルールを覚えるのは大変です。",
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
  "target_word": "複雑な"
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
      "text": "複雑な気持ちで学校に行きました。",
      "is_correct": true
    },
    {
      "text": "この問題はとても複雑です。",
      "is_correct": true
    },
    {
      "text": "機械の構造は複雑すぎてわかりません。",
      "is_correct": true
    },
    {
      "text": "複雑の話は苦手だ。",
      "is_correct": false,
      "error_description": "助詞・活用の誤り。形状詞「複雑」が名詞を修飾するときは「の」ではなく「な」を使い、「複雑な話」が正しい形です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "複雑な計算は電卓を使ってください。",
      "is_correct": true
    },
    {
      "text": "複雑なルールを覚えるのは大変です。",
      "is_correct": true
    },
    {
      "text": "この地図は複雑すぎて道がわかりません。",
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

#### Pack B
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

---

## sense 35615, level 9

#### Pack A
### Level 9 (sense 35615, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "複雑にからみ合った糸をほどきました。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "複雑な問題を解くのは大変です。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "複雑な問題を解くのは大変です。",
  "chunks": [
    "複雑な問題を",
    "解くの",
    "は",
    "大変です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "大変です",
    "解くの",
    "は",
    "複雑な問題を"
  ],
  "target_word": "複雑な",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 35615, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼の行動は少し複雑です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼の行動は少し複雑です。",
  "chunks": [
    "彼の",
    "行動は",
    "少し複雑です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "少し複雑です",
    "行動は",
    "彼の"
  ],
  "target_word": "複雑",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "社会の仕組みは複雑です。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "社会の仕組みは複雑です。",
  "chunks": [
    "社会の",
    "仕組みは",
    "複雑です"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "仕組みは",
    "社会の",
    "複雑です"
  ],
  "target_word": "複雑",
  "chunk_count": 3
}
```

---

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "correct_answer": "みずから",
  "word": "自ら",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "水カビ",
    "蹼",
    "自ら",
    "ミズカビ"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "ミズカビ": "「ミズカビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "蹼": "「蹼」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「き」、一部の音の違い）。",
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "みずから",
  "options": [
    "視覚",
    "購買",
    "自分",
    "自ら"
  ],
  "correct_answer": "自ら",
  "word": "自ら",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "視覚": "component",
    "購買": "component",
    "自分": "component"
  }
}
```

#### Pack B
### Level 1 (sense 39187, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "correct_answer": "みずから",
  "word": "自ら",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "みずから",
  "options": [
    "購買",
    "自分",
    "見る",
    "自ら"
  ],
  "correct_answer": "自ら",
  "word": "自ら",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "購買": "component",
    "自分": "component",
    "見る": "component"
  }
}
```
**phonetic_recognition** variant `B`, tier `T5`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "水換え",
    "自ら",
    "水替え",
    "ミズカビ"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "ミズカビ": "「ミズカビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "水替え": "「水替え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。",
    "水換え": "「水換え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 39187, level 2

#### Pack A
### Level 2 (sense 39187, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。",
  "options": [
    "自分自身を指す言葉。",
    "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
    "資本。元手となるお金。また、首都。",
    "何かを包み込んだり、中に含めたりすることを表す動詞。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "irrigation",
        "消化管の一部で、栄養の吸収や便の形成に関わる器官。食物の消化と吸収、免疫機能にも重要な役割を果たす。",
        "自分自身を指す言葉。",
        "特別でなく、広く一般的なさま。多くの人や物事に共通していること。"
      ],
      "correct_answer": "自分自身を指す言葉。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 39187, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。",
  "options": [
    "物事を考えるときの、特定の立場や視点。",
    "バロックとは、1600年から1750年頃のヨーロッパで栄えた芸術様式の一つです。音楽では、教会旋法から長調・短調の調性音楽へと移行し、バッハやヘンデルのような作曲家が活躍しました。特徴として、装飾音の多用、対位法の重視、通奏低音の使用などが挙げられます。",
    "競争や試合などで、他の人やチームよりも優れた結果を出すこと。",
    "自分自身を指す言葉。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "しろ。しろい いろ。",
        "废弃 —— 把不再需要的东西丢弃处理掉",
        "自分自身を指す言葉。",
        "a part (component)"
      ],
      "correct_answer": "自分自身を指す言葉。"
    }
  }
}
```

---

## sense 39187, level 4

#### Pack A
### Level 4 (sense 39187, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "変化に適応し、___の価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "original_sentence": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ],
    "accepted_normalized": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
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
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___の意思で毎日勉強しています。",
  "original_sentence": "自らの意思で毎日勉強しています。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
    ],
    "accepted_normalized": [
      "自ら",
      "自らも",
      "自らが",
      "自らの"
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
### Level 4 (sense 39187, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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
  "sentence_with_blank": "___が進む道です。",
  "original_sentence": "自らが進む道です。",
  "target_word": "自ら",
  "word": "自ら",
  "answer": {
    "accepted": [
      "自ら"
    ],
    "accepted_normalized": [
      "自ら"
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

---

## sense 39187, level 6

#### Pack A
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "高めている彼女は自らを。",
      "is_correct": false
    },
    {
      "text": "自らを信じています。",
      "is_correct": true
    },
    {
      "text": "彼女は自らを高まっている。",
      "is_correct": false
    },
    {
      "text": "彼女は自らが高めている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「高める」の対象は「を」で示す。「が」は誤り。 活用：他動詞は「高める」であり、自動詞「高まる」との混同は誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "自ら"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "自ら",
  "relation": "antonym",
  "options": [
    "他人",
    "自分",
    "彼",
    "我々"
  ],
  "correct_answer": "他人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "自分自身を指す言葉。",
      "explanation": "自分以外の人を指し、「自ら」の対義語となる"
    }
  }
}
```

#### Pack B
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "自ら守るがルールです。",
      "is_correct": false
    },
    {
      "text": "自らをルールが守る。",
      "is_correct": false
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
      "is_correct": true
    },
    {
      "text": "自らが守るルールだ。",
      "is_correct": false
    }
  ],
  "explanation": "項構造：「自ら」は「守る」動作の主体（主語）ではなく、対象（目的語）です。正しくは「自らが守るルール」です。 語域：「だ」は口語的な断定表現であり、基礎例文の「自らが守るルールです」という丁寧な表現と語域が一致しません。 語順：「自ら守るが」の「が」の位置が誤りです。名詞を修飾する場合は「自ら守るルール」となるべきです。",
  "target_word": "自ら"
}
```

---

## sense 39187, level 7

#### Pack A
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らに肌で実感していくことになります。",
      "is_correct": false,
      "error_description": "「自ら」が名詞を修飾する場合は助詞「の」を用いて「自らの肌」とするのが正しい用法です。「に」は誤りです。"
    },
    {
      "text": "自らの手で丁寧に掃除をしています。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
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
      "text": "自らの手で花を育てています。",
      "is_correct": true
    },
    {
      "text": "自らを信じています。",
      "is_correct": true
    },
    {
      "text": "自ら意思で毎日勉強しています。",
      "is_correct": false,
      "error_description": "「自ら」が名詞を修飾する場合は、「自らの」と助詞「の」を伴うのが正しい用法です。"
    },
    {
      "text": "自らの意思で毎日勉強しています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼は自らでそのプロジェクトを成功させた。",
      "is_correct": false,
      "error_description": "「自ら」は副詞的・名詞的に「自分自身」を指しますが、「自分で」とは異なり、助詞「で」を伴って動作の主体を表す用法はありません。「自分で」との混同による助詞の誤用です。正しくは「自ら」または「自らが」とします。"
    },
    {
      "text": "自らを責めて、泣きました。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
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
      "text": "自らが守るルールです。",
      "is_correct": true
    },
    {
      "text": "自らが進む道です。",
      "is_correct": true
    },
    {
      "text": "自らを進む道です。",
      "is_correct": false,
      "error_description": "助詞の混同。「自ら」は動詞「進む」の主語であるため、格助詞「が」を使うのが適切です。「を」は動作の目的語を示す際に使います。"
    },
    {
      "text": "自らが考えたアイデアです。",
      "is_correct": true
    }
  ]
}
```

---
