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


## sense 35615, level 1

#### Pack A
### Level 1 (sense 35615, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "複雑",
  "options": [
    "ふくさつ",
    "ふくざづ",
    "ふぐざつ",
    "ふくざつ"
  ],
  "correct_answer": "ふくざつ",
  "word": "複雑",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/fukuzatsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複舌",
    "錯雑",
    "複雑",
    "複座機"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "錯雑": "「錯雑」は「複雑」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「さ」、一部の音の違い）。",
    "複座機": "「複座機」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「き」、一部の音の違い）。",
    "複舌": "「複舌」は「複雑」と一モーラだけ異なる実在語です（3モーラ目: 「ざ」→「ぜ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふくざつ",
  "options": [
    "複雑",
    "混雑",
    "複合",
    "雑誌"
  ],
  "correct_answer": "複雑",
  "word": "複雑",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "雑誌": "component",
    "複合": "component",
    "混雑": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35615, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "prompt": "複雑",
  "options": [
    "ふくさつ",
    "ふくざづ",
    "ふぐざつ",
    "ふくざつ"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "ふくざつ",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "ɸɯkɯzat͡sɯ",
  "word": "複雑",
  "options": [
    "福笹",
    "伏罪",
    "複雑",
    "服罪"
  ],
  "audio_url": null,
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単には理解できない様子。」という意味です。",
  "pronunciation": "ふくざつ",
  "correct_answer": "複雑",
  "syllable_count": 4,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "伏罪": "「伏罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "服罪": "「服罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "prompt": "ふくざつ",
  "options": [
    "複雑",
    "複合",
    "雑誌",
    "複数"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "複雑",
  "schema_version": 2,
  "distractor_sources": {
    "複合": "component",
    "複数": "component",
    "雑誌": "component"
  }
}
```

---

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

#### Pack B
### Level 2 (sense 35615, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "同じくらいの程度や価値があること。",
        "何かを一生懸命にやってみること。",
        "多くの要素がからみ合って、簡単には理解できない様子。",
        "何かをやってみたことがあること。"
      ],
      "correct_answer": "多くの要素がからみ合って、簡単には理解できない様子。"
    }
  },
  "tier": "T3",
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "options": [
    "他と違いがなく、一致していること。",
    "バロックとは、1600年から1750年頃のヨーロッパで栄えた芸術様式の一つです。音楽では、教会旋法から長調・短調の調性音楽へと移行し、バッハやヘンデルのような作曲家が活躍しました。特徴として、装飾音の多用、対位法の重視、通奏低音の使用などが挙げられます。",
    "多くの要素がからみ合って、簡単には理解できない様子。",
    "人が身に着ける衣服の総称。特に、学校や仕事などで着る制服や、日常的に着る衣類を指すことが多い。"
  ],
  "pronunciation": "ふくざつ",
  "correct_definition": "多くの要素がからみ合って、簡単には理解できない様子。"
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

#### Pack B
### Level 3 (sense 35615, difficulty 5)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "複雑",
    "元気",
    "丈夫",
    "親切"
  ],
  "explanation": "「複雑すぎて説明できない」は、要素が多くからみ合っていて説明しきれないという意味で自然である。",
  "target_word": "複雑",
  "correct_answer": "複雑",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単には理解できない様子。",
  "original_sentence": "複雑すぎて、説明できない。",
  "sentence_with_blank": "___すぎて、説明できない。"
}
```

---

## sense 35615, level 4

#### Pack A
### Level 4 (sense 35615, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑さ",
      "複雑化"
    ],
    "accepted_normalized": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑さ",
      "複雑化"
    ]
  },
  "input_mode": "ime",
  "target_word": "複雑",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "駅の中は通路が複雑で、迷いやすい。",
  "sentence_with_blank": "駅の中は通路が___で、迷いやすい。"
}
```
**morphology_slot** variant `A`, tier `T3`
```json
{
  "options": [
    "複雑",
    "複雑に",
    "複雑な",
    "複雑さ"
  ],
  "base_form": "複雑",
  "form_label": "語幹（「で」に続く形）",
  "explanation": "形状詞の語幹で、後ろの「で」（だ・で）に直接つながり、「通路が複雑で」と述語になる",
  "target_word": "複雑",
  "correct_answer": "複雑",
  "word_definition": "多くの要素がからみ合って、簡単には理解できない様子。",
  "original_sentence": "駅の中は通路が複雑で、迷いやすい。",
  "sentence_with_blank": "駅の中は通路が___で、迷いやすい。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "複雑",
  "answer": {
    "accepted": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑さ",
      "複雑化"
    ],
    "accepted_normalized": [
      "複雑",
      "複雑な",
      "複雑に",
      "複雑さ",
      "複雑化"
    ]
  },
  "input_mode": "ime",
  "target_word": "複雑",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "複雑な話は苦手だ。",
  "sentence_with_blank": "___な話は苦手だ。"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "options": [
    "複雑に",
    "複雑な",
    "複雑さ",
    "複雑"
  ],
  "base_form": "複雑",
  "form_label": "語幹（「な」に続く形）",
  "explanation": "形状詞の語幹に「な」が付いて「複雑な話」と連体修飾になる",
  "target_word": "複雑",
  "correct_answer": "複雑",
  "word_definition": "多くの要素がからみ合って、簡単には理解できない様子。",
  "original_sentence": "複雑な話は苦手だ。",
  "sentence_with_blank": "___な話は苦手だ。"
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

## sense 35615, level 6

#### Pack A
### Level 6 (sense 35615, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "複雑な道を迷ってしまった。",
      "is_correct": false
    },
    {
      "text": "道で迷ってしまった複雑な。",
      "is_correct": false
    },
    {
      "text": "複雑な道で迷ってしまった。",
      "is_correct": true
    },
    {
      "text": "昨日、複雑な道で迷ってしまう。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「道に迷う」が正しい結びつきで、「道を迷う」は不自然である。「に」を「を」に取り違えている。 活用・アスペクトの誤り：「昨日」という過去の時を表す語があるのに、述語が非過去の「迷ってしまう」になっていて時制が合わない。 語順・係り受けの誤り：修飾する「複雑な」が文末に残り、かかる名詞がないため係り受けが壊れている。",
  "target_word": "複雑"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "definition": "多くの要素がからみ合って、簡単には理解できない様子。",
      "explanation": "要素が少なく分かりやすい様子で、「複雑」と反対の意味になる"
    }
  },
  "word": "複雑",
  "options": [
    "曖昧",
    "単純",
    "面倒",
    "精密"
  ],
  "relation": "antonym",
  "correct_answer": "単純",
  "schema_version": 2
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼の話を複雑で、よく分からなかった。",
      "is_correct": false
    },
    {
      "text": "彼の複雑は話で、よく分からなかった。",
      "is_correct": false
    },
    {
      "text": "彼の話は複雑だったで、よく分からなかった。",
      "is_correct": false
    },
    {
      "text": "彼の話は複雑で、よく分からなかった。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：形状詞「複雑」の主語を示すのは「が」または「は」で、「を」は使えない。「彼の話が複雑で」が正しい。 活用・アスペクトの誤り：理由をつなぐ「で」の前に過去形「だった」を置くことはできない。「複雑で」または「複雑だったので」が正しい。 語順・係り受けの誤り：「複雑」と「話」の位置が入れ替わり、「彼の話は複雑で」というまとまりが壊れている。",
  "target_word": "複雑"
}
```

#### Pack B
### Level 6 (sense 35615, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "道で迷ってしまった複雑な。",
      "is_correct": false
    },
    {
      "text": "複雑な問題を解くのは大変です。",
      "is_correct": true
    },
    {
      "text": "複雑な道を迷ってしまった。",
      "is_correct": false
    },
    {
      "text": "昨日、複雑な道で迷ってしまう。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「道に迷う」が正しい結びつきで、「道を迷う」は不自然である。「に」を「を」に取り違えている。 活用・アスペクトの誤り：「昨日」という過去の時を表す語があるのに、述語が非過去の「迷ってしまう」になっていて時制が合わない。 語順・係り受けの誤り：修飾する「複雑な」が文末に残り、かかる名詞がないため係り受けが壊れている。",
  "target_word": "複雑な"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼の複雑は話で、よく分からなかった。",
      "is_correct": false
    },
    {
      "text": "彼の話は複雑だったで、よく分からなかった。",
      "is_correct": false
    },
    {
      "text": "複雑な計算は電卓を使ってください。",
      "is_correct": true
    },
    {
      "text": "彼の話を複雑で、よく分からなかった。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：形状詞「複雑」の主語を示すのは「が」または「は」で、「を」は使えない。「彼の話が複雑で」が正しい。 活用・アスペクトの誤り：理由をつなぐ「で」の前に過去形「だった」を置くことはできない。「複雑で」または「複雑だったので」が正しい。 語順・係り受けの誤り：「複雑」と「話」の位置が入れ替わり、「彼の話は複雑で」というまとまりが壊れている。",
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
### Level 7 (sense 35615, difficulty 5)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "複雑の話は苦手だ。",
      "is_correct": false,
      "error_description": "助詞・活用の誤り。形状詞「複雑」が名詞を修飾するときは「の」ではなく「な」を使い、「複雑な話」が正しい形です。"
    },
    {
      "text": "ルールが複雑で、覚えられない。",
      "is_correct": true
    },
    {
      "text": "駅の中は通路が複雑で、迷いやすい。",
      "is_correct": true
    },
    {
      "text": "この問題は複雑だ。",
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
      "text": "複雑すぎて、説明できない。",
      "is_correct": true
    },
    {
      "text": "この規則は複雑くて、覚えにくい。",
      "is_correct": false,
      "error_description": "活用の誤り。「複雑」は形状詞（ナ形容詞）なので、い形容詞のように「くて」とは言わず、「複雑で」と接続します。"
    },
    {
      "text": "彼の話は複雑で、よく分からなかった。",
      "is_correct": true
    },
    {
      "text": "複雑な話は苦手だ。",
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
### Level 9 (sense 35615, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "この機械は仕組みが複雑だ。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "この機械は",
    "仕組みが",
    "複雑だ"
  ],
  "chunk_count": 3,
  "target_word": "複雑",
  "schema_version": 2,
  "shuffled_chunks": [
    "複雑だ",
    "仕組みが",
    "この機械は"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "この機械は仕組みが複雑だ。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "複雑な道で迷ってしまった。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "chunks": [
    "複雑な道で",
    "迷って",
    "しまった"
  ],
  "chunk_count": 3,
  "target_word": "複雑",
  "schema_version": 2,
  "shuffled_chunks": [
    "迷って",
    "複雑な道で",
    "しまった"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "複雑な道で迷ってしまった。"
}
```

---

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "prompt": "自ら",
  "options": [
    "みいずから",
    "みずから",
    "みすから",
    "みずがら"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "みずから",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "mizɯkaɾa",
  "word": "自ら",
  "options": [
    "水換え",
    "見るから",
    "自ら",
    "水カビ"
  ],
  "audio_url": null,
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "pronunciation": "みずから",
  "correct_answer": "自ら",
  "syllable_count": 4,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "水換え": "「水換え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。",
    "見るから": "「見るから」は「自ら」と一モーラだけ異なる実在語です（2モーラ目: 「ず」→「る」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "prompt": "みずから",
  "options": [
    "視覚",
    "購買",
    "自分",
    "自ら"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "自ら",
  "schema_version": 2,
  "distractor_sources": {
    "自分": "component",
    "視覚": "component",
    "購買": "component"
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
### Level 2 (sense 39187, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "こなのように、とても細かいものです。",
        "a (coffee) bean",
        "vertical",
        "自分自身を指す言葉。"
      ],
      "correct_answer": "自分自身を指す言葉。"
    }
  },
  "tier": "T6",
  "word": "自ら",
  "pronunciation": "みずから",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "自ら",
  "options": [
    "ある物事や現象が一時的に非常に人気になり、多くの人々が熱中する状態。",
    "自分自身を指す言葉。",
    "ある製品や資源を、多く消費したり使用したりする国",
    "実際に物事を行ったり、その場に立ち会ったりして得た知識や技能。"
  ],
  "pronunciation": "みずから",
  "correct_definition": "自分自身を指す言葉。"
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

## sense 39187, level 3

#### Pack A
### Level 3 (sense 39187, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "自分",
    "自ら",
    "他人",
    "彼"
  ],
  "explanation": "「自らの肌で実感する」は自分自身を指す固定表現。",
  "target_word": "自ら",
  "correct_answer": "自ら",
  "distractor_tags": {},
  "word_definition": "自分自身を指す言葉。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。"
}
```

#### Pack B
### Level 3 (sense 39187, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、___の肌で実感していくことになります。",
  "original_sentence": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
  "correct_answer": "自ら",
  "options": [
    "自動的に",
    "自ら",
    "他人",
    "受動的に"
  ],
  "explanation": "文脈に合っており、自分自身で体験するという意味で適切です。",
  "distractor_tags": {},
  "word_definition": "自分自身を指す言葉。",
  "target_word": "自ら"
}
```

---
