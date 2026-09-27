# Pairwise review pack 04

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


## sense 35127, level 4

#### Pack A
### Level 4 (sense 35127, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "創造性を刺激する空間にしたいと考えたが、十分な予算が___、計画は頓挫してしまった。",
  "original_sentence": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
  "target_word": "なく",
  "word": "なく",
  "answer": {
    "accepted": [
      "なく",
      "なければ",
      "なかった",
      "無し"
    ],
    "accepted_normalized": [
      "なく",
      "なければ",
      "なかった",
      "無し"
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
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "創造性を刺激する空間にしたいと考えたが、十分な予算が___、計画は頓挫してしまった。",
  "original_sentence": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中頓）",
  "options": [
    "なく",
    "なければ",
    "ない",
    "なかった"
  ],
  "explanation": "中頓を表す連用形「なく」が後続の句に適切に接続する。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
  "original_sentence": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
  "correct_answer": "ない",
  "base_form": "無い",
  "form_label": "終止形（では〜の形）",
  "options": [
    "無ければ",
    "ない",
    "無かった",
    "無くて"
  ],
  "explanation": "「ではない」は存在の否定を表す終止形。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "ない"
}
```

#### Pack B
### Level 4 (sense 35127, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "なく",
  "answer": {
    "accepted": [
      "ない"
    ],
    "accepted_normalized": [
      "ない"
    ]
  },
  "input_mode": "ime",
  "target_word": "ない",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "これは幼い頃のような単なるお絵描きではない。",
  "sentence_with_blank": "これは幼い頃のような単なるお絵描きでは___。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "無くて",
    "ない",
    "無かった",
    "無ければ"
  ],
  "base_form": "無い",
  "form_label": "終止形（では〜の形）",
  "explanation": "「ではない」は存在の否定を表す終止形。",
  "target_word": "ない",
  "correct_answer": "ない",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "original_sentence": "これは幼い頃のような単なるお絵描きではない。",
  "sentence_with_blank": "これは幼い頃のような単なるお絵描きでは___。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "なく",
  "answer": {
    "accepted": [
      "ない"
    ],
    "accepted_normalized": [
      "ない"
    ]
  },
  "input_mode": "ime",
  "target_word": "ない",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動を意味するものではない。",
  "sentence_with_blank": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動を意味するものでは___。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "ない",
    "無ければ",
    "無くて",
    "無かった"
  ],
  "base_form": "無い",
  "form_label": "終止形（では〜の形）",
  "explanation": "「ではない」は存在の否定を表す終止形。",
  "target_word": "ない",
  "correct_answer": "ない",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "original_sentence": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動を意味するものではない。",
  "sentence_with_blank": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動を意味するものでは___。"
}
```

---

## sense 35127, level 6

#### Pack A
### Level 6 (sense 35127, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": true
    },
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択がなく、すべてが特定のメッセージを伝える記号として機能した。",
      "is_correct": false
    },
    {
      "text": "記号論の観点から色を分析すると、そこにはなく偶然の選択が、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": false
    },
    {
      "text": "記号論の観点から色を分析すると、そこには偶然の選択をなく、すべてが特定のメッセージを伝える記号として機能している。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同。「偶然の選択」は存在しないものの主語であるため、「を」ではなく「が」を使う必要があります。 活用・アスペクトの誤り。「分析すると」という条件・発見の表現に対して、結果の「機能した」という過去形は不自然です。 語順・係り受けの誤り。「そこには」の直後に「なく」を置くことで、「偶然の選択が」との主語との係り受けが破壊され、文構造が破綻しています。",
  "target_word": "なく"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えてある。",
      "is_correct": false
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えている。",
      "is_correct": true
    },
    {
      "text": "手元にはなく、参考になる資料や答えをみんなで知恵を出し合って考えている。",
      "is_correct": false
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合ってに考えている。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「出して」と「考えて」を繋ぐのに助詞「に」は不要であり、文法誤りです。 活用・アスペクトの誤り：「考える」は意志動詞であり、結果の状態を表す「てある」は不自然です。 語順・係り受けの誤り：「なく」は「資料や答え」にかかるべきですが、後続の節で「を」の目的語になっており係り受けが破綻しています。",
  "target_word": "ない"
}
```

#### Pack B
### Level 6 (sense 35127, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "答えが無いて困った。",
      "is_correct": false
    },
    {
      "text": "今日は時間を無い。",
      "is_correct": false
    },
    {
      "text": "無い今日は時間が。",
      "is_correct": false
    },
    {
      "text": "色は単なる装飾ではなく、記号論の観点から特定のメッセージを伝える記号として機能するのだ。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：存在を表す「ない」の主体は「が」で示す。「を」は誤り。 活用：て形は「無くて」であり、「無いて」は存在しない活用形。 語順：述語は文末に置く。文頭に置くのは日本語の語順に反する。",
  "target_word": "なく"
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "今日は時間に無い。",
      "is_correct": false
    },
    {
      "text": "答えが無くて困った。",
      "is_correct": true
    },
    {
      "text": "これは幼い頃のような単なるお絵描きでは無くだ。",
      "is_correct": false
    },
    {
      "text": "ではない、これは幼い頃のような単なるお絵描き。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：存在を表す「ない」の主体は「が」で示す。「に」は誤り。 活用：連用形「なく」に「だ」を続けるのは誤り。「ではない」を使う。 語順：述語を文頭に置くのは日本語の語順に反する。",
  "target_word": "無くて"
}
```

---

## sense 35127, level 7

#### Pack A
### Level 7 (sense 35127, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "単なる物置きではなく、創造性を刺激する空間にしたいと考えたのだ。",
      "is_correct": true
    },
    {
      "text": "単なる物置きでは無いく、創造性を刺激する空間にしたいと考えたのだ。",
      "is_correct": false,
      "error_description": "活用：形容詞の連用形は「なく」であり、「無いく」という形は存在しない。"
    },
    {
      "text": "これは幼い頃のような単なるお絵描きではない。",
      "is_correct": true
    },
    {
      "text": "このTシャツは、単なるグッズではなく、彼らのルーツへの敬意を形にしたものです。",
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
      "text": "企業は、単純な作業だけでなく、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
      "is_correct": true
    },
    {
      "text": "今日は時間を無い。",
      "is_correct": false,
      "error_description": "助詞：存在を表す「ない」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "答えが無くて困った。",
      "is_correct": true
    },
    {
      "text": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動を意味するものではない。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "創造性を刺激する空間にしたいと考えたが、十分な予算がなく、計画は頓挫してしまった。",
      "is_correct": true
    },
    {
      "text": "幼い頃のようなお絵描きとは異なり、この作品には特定のモデルがなく、純粋な感情表現となっている。",
      "is_correct": true
    },
    {
      "text": "彼らのルーツへの敬意を形にしたTシャツは、現在どこにも在庫になく、入手が困難となっている。",
      "is_correct": false,
      "error_description": "助詞の混同。存在しないものの主語を示すには『に』ではなく『が』を使います。正しくは『在庫がなく』です。"
    },
    {
      "text": "彼らのルーツへの敬意を形にしたTシャツは、現在どこにも在庫がなく、入手が困難となっている。",
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
      "text": "彼女の人生におけるこの学校の初日は、単なる物理的な場所の移動以上の意味を持ち、不安な気持ちはどこにもなく、充実していた。",
      "is_correct": true
    },
    {
      "text": "企業には単純な作業だけで済む余裕はなく、創造性や対人スキルを求められる役割へ従業員をシフトさせなければならない。",
      "is_correct": true
    },
    {
      "text": "今日は時間を無い。",
      "is_correct": false,
      "error_description": "助詞：存在を表す「ない」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "手元には参考になる資料や答えがなく、みんなで知恵を出し合って考えている。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35127, level 9

#### Pack A
### Level 9 (sense 35127, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "この事業の終了には悲観的な意味はなく、資本の循環と新たな創造への移行を意味する重要なプロセスなのだ。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "この事業の終了には悲観的な意味はなく、資本の循環と新たな創造への移行を意味する重要なプロセスなのだ。",
  "chunks": [
    "この事業の",
    "終了には悲観的な意味は",
    "なく資本の循環と",
    "新たな創造への移行を",
    "意味する重要なプロセスなの",
    "だ"
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
    "終了には悲観的な意味は",
    "新たな創造への移行を",
    "この事業の",
    "意味する重要なプロセスなの",
    "なく資本の循環と",
    "だ"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "記号論の観点から色を分析すると、そこには偶然の選択はなく、すべてが特定のメッセージを伝える記号として機能している。",
  "chunks": [
    "記号論の観点から色を",
    "分析するとそこには偶然の",
    "選択はなくすべてが特定の",
    "メッセージを",
    "伝える記号と",
    "して機能している"
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
    "伝える記号と",
    "選択はなくすべてが特定の",
    "メッセージを",
    "分析するとそこには偶然の",
    "記号論の観点から色を",
    "して機能している"
  ],
  "target_word": "なく",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35127, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "これは事業の",
    "終了では",
    "なく資本の循環と",
    "新たな創造へ",
    "の移行を",
    "意味する重要なプロセスだ"
  ],
  "chunk_count": 6,
  "target_word": "なく",
  "schema_version": 2,
  "shuffled_chunks": [
    "終了では",
    "新たな創造へ",
    "これは事業の",
    "の移行を",
    "なく資本の循環と",
    "意味する重要なプロセスだ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "色は単なる装飾では",
    "なく記号論の",
    "観点から特定の",
    "メッセージを",
    "伝える記号と",
    "して機能するのだ"
  ],
  "chunk_count": 6,
  "target_word": "なく",
  "schema_version": 2,
  "shuffled_chunks": [
    "伝える記号と",
    "観点から特定の",
    "メッセージを",
    "なく記号論の",
    "色は単なる装飾では",
    "して機能するのだ"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "色は単なる装飾ではなく、記号論の観点から特定のメッセージを伝える記号として機能するのだ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "色は単なる装飾ではなく、記号論の観点から特定のメッセージを伝える記号として機能するのだ。"
}
```

---

## sense 35147, level 1

#### Pack A
### Level 1 (sense 35147, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "prompt": "行く",
  "options": [
    "いくう",
    "いぐ",
    "いいく",
    "いく"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "いく",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "ikɯ",
  "word": "行く",
  "options": [
    "行く",
    "柵",
    "可く",
    "射る"
  ],
  "audio_url": null,
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。物事が進む。」という意味です。",
  "pronunciation": "いく",
  "correct_answer": "行く",
  "syllable_count": 2,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "柵": "「柵」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「さ」、一部の音の違い）。",
    "可く": "「可く」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「べ」、一部の音の違い）。",
    "射る": "「射る」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「る」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "prompt": "いく",
  "options": [
    "幾",
    "履行",
    "行く",
    "技術"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "行く",
  "schema_version": 2,
  "distractor_sources": {
    "幾": "homophone",
    "履行": "component",
    "技術": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35147, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "行く",
  "options": [
    "いくう",
    "いぐ",
    "いいく",
    "いく"
  ],
  "correct_answer": "いく",
  "word": "行く",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "ipa": "/iku/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "意氣",
    "肉",
    "軸",
    "行く"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。また、物事が進む。」という意味です。",
  "distractor_explanations": {
    "意氣": "「意氣」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「き」、一部の音の違い）。",
    "肉": "「肉」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「に」、一部の音の違い）。",
    "軸": "「軸」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「じ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "いく",
  "options": [
    "幾",
    "履行",
    "行く",
    "技術"
  ],
  "correct_answer": "行く",
  "word": "行く",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "幾": "homophone",
    "履行": "component",
    "技術": "component"
  }
}
```

---

## sense 35147, level 2

#### Pack A
### Level 2 (sense 35147, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "options": [
    "ある場所から別の場所へ移動する。物事が進む。",
    "内部に閉じ込められていたものを、外部に出すこと。",
    "生物の細胞や組織を包む薄い層。また、物の表面をおおう薄い皮。",
    "物事の勢いや速さが弱まって、遅くなること。"
  ],
  "pronunciation": "いく",
  "correct_definition": "ある場所から別の場所へ移動する。物事が進む。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "物事の本質や正体を隠し、別のもののように見せかけること。また、その行為。",
        "祈祷；祷告；祈愿",
        "ある場所から別の場所へ移動する。物事が進む。",
        "sandwich"
      ],
      "correct_answer": "ある場所から別の場所へ移動する。物事が進む。"
    }
  },
  "tier": "T3",
  "word": "行く",
  "pronunciation": "いく",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 35147, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "correct_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "options": [
    "ある場所から別の場所へ移動する。また、物事が進む。",
    "物事の善悪や価値について、自分の考えを決めること。",
    "物事の動きや変化の方向性。特に、社会や時代の全体的な傾向や流れを指すことが多い。",
    "時間をかけて発酵や乾燥などの処理を行い、価値や品質が向上した状態にすること。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "茁壮成长 —— 婴儿或孩子健康顺利地迅速长大的样子",
        "乐趣；期待的事；令人开心的事",
        "ある場所から別の場所へ移動する。また、物事が進む。",
        "English (language)"
      ],
      "correct_answer": "ある場所から別の場所へ移動する。また、物事が進む。"
    }
  }
}
```

---

## sense 35147, level 4

#### Pack A
### Level 4 (sense 35147, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "来月、海外へ___友達を祝いました。",
  "original_sentence": "来月、海外へ行く友達を祝いました。",
  "target_word": "行く",
  "word": "行く",
  "answer": {
    "accepted": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
    ],
    "accepted_normalized": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
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
  "sentence_with_blank": "来月、海外へ___友達を祝いました。",
  "original_sentence": "来月、海外へ行く友達を祝いました。",
  "correct_answer": "行く",
  "base_form": "行く",
  "form_label": "辞書形",
  "options": [
    "行きます",
    "行く",
    "行って",
    "行った"
  ],
  "explanation": "「来月」という未来の出来事を修飾するため、辞書形が適切である。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行く"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "私たちは選挙へ___べきです。",
  "original_sentence": "私たちは選挙へ行くべきです。",
  "target_word": "行く",
  "word": "行く",
  "answer": {
    "accepted": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
    ],
    "accepted_normalized": [
      "行く",
      "行った",
      "行って",
      "行ける",
      "行かない"
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
  "sentence_with_blank": "私たちは選挙へ___べきです。",
  "original_sentence": "私たちは選挙へ行くべきです。",
  "correct_answer": "行く",
  "base_form": "行く",
  "form_label": "辞書形（終止形）",
  "options": [
    "行く",
    "行った",
    "行かない",
    "行って"
  ],
  "explanation": "助動詞「べき」は動詞の辞書形（終止形）に接続する",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行く"
}
```

#### Pack B
### Level 4 (sense 35147, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "answer": {
    "accepted": [
      "行った"
    ],
    "accepted_normalized": [
      "行った"
    ]
  },
  "input_mode": "ime",
  "target_word": "行った",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "昨日、公園へ行った。",
  "sentence_with_blank": "昨日、公園へ___。"
}
```
**morphology_slot** variant `A`, tier `T3`
```json
{
  "options": [
    "いって",
    "いった",
    "いかない",
    "いく"
  ],
  "base_form": "行く",
  "form_label": "た形（過去）",
  "explanation": "「昨日」があるので過去のた形が必要。",
  "target_word": "行った",
  "correct_answer": "いった",
  "word_definition": "ある場所から別の場所へ移動する。物事が進む。",
  "original_sentence": "昨日、公園へ行った。",
  "sentence_with_blank": "昨日、公園へ___。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "行く",
  "answer": {
    "accepted": [
      "行く",
      "行った",
      "行って",
      "行かない",
      "行き方"
    ],
    "accepted_normalized": [
      "行く",
      "行った",
      "行って",
      "行かない",
      "行き方"
    ]
  },
  "input_mode": "ime",
  "target_word": "行く",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼は毎日会社に行く。",
  "sentence_with_blank": "彼は毎日会社に___。"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "options": [
    "いく",
    "いって",
    "いった",
    "いきたい"
  ],
  "base_form": "行く",
  "form_label": "辞書形（習慣）",
  "explanation": "習慣的な行為を表す辞書形。",
  "target_word": "行く",
  "correct_answer": "いく",
  "word_definition": "ある場所から別の場所へ移動する。物事が進む。",
  "original_sentence": "彼は毎日会社に行く。",
  "sentence_with_blank": "彼は毎日会社に___。"
}
```

---

## sense 35147, level 6

#### Pack A
### Level 6 (sense 35147, difficulty 5)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼が一緒に行くのは楽しい。",
      "is_correct": false
    },
    {
      "text": "彼と一緒に行くのを楽しい。",
      "is_correct": false
    },
    {
      "text": "楽しい彼と一緒に行くのは。",
      "is_correct": false
    },
    {
      "text": "彼と一緒に行くのは楽しい。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：一般的な話者の相手は「と」で示す。「が」は不自然。 助詞：形容詞述語の対象は「は」で示す。「を」は誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "行く"
}
```

#### Pack B
### Level 6 (sense 35147, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "relation": "antonym",
  "options": [
    "来る",
    "走る",
    "通る",
    "入る"
  ],
  "correct_answer": "来る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "話し手の方へ移動する意であり、目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は今、京都へ行くています。",
      "is_correct": false
    },
    {
      "text": "私が行く時は一緒にどうですか。",
      "is_correct": true
    },
    {
      "text": "行く私が時は京都へ一緒にどうですか。",
      "is_correct": false
    },
    {
      "text": "私は来週、京都へ行くにしました。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「行く」の後ろには名詞化するための「こと」が必要で、「に」を直接続けることはできません。正しくは「行くことにしました」です。 活用・アスペクトの誤り：「行く」の連用形は「行き」であり、「行くている」は誤りです。正しくは「行っている」または「行っています」です。 語順・係り受けの誤り：「私が行く時は」という節の語順が壊れており、文として成立していません。",
  "target_word": "行く"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "行く",
  "relation": "antonym",
  "options": [
    "渡る",
    "走る",
    "来る",
    "入る"
  ],
  "correct_answer": "来る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "目標語と同じく場所の移動を表すが、方向が逆であるため対義語となる"
    }
  }
}
```

---

## sense 35147, level 7

#### Pack A
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "来月、海外へ行く友達を祝いました。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都で行く予定です。",
      "is_correct": false,
      "error_description": "移動の目的地を表す助詞は「へ」または「に」を使います。「で」は動作の行われる場所を表すため、この文脈では不適切です。"
    },
    {
      "text": "ボランティア活動へ行って、多くのことを学びました。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都へ行く予定です。",
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
      "text": "駅まで歩いて行ってください。",
      "is_correct": true
    },
    {
      "text": "私が行く時は一緒にどうですか。",
      "is_correct": true
    },
    {
      "text": "私たちは選挙へ行くべきです。",
      "is_correct": true
    },
    {
      "text": "私は来週、京都へ行くです。",
      "is_correct": false,
      "error_description": "動詞の辞書形「行く」の後に直接「です」を続けることはできません。「行く予定です」や「行くつもりです」のように形式名詞を挟む必要があります。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35147, difficulty 5)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "昨日、公園へ行った。",
      "is_correct": true
    },
    {
      "text": "彼と一緒に行くには楽しい。",
      "is_correct": false,
      "error_description": "助詞：名詞化の「の」を「に」に置き換えるのは誤り。"
    },
    {
      "text": "彼は今、駅へ行っている。",
      "is_correct": true
    },
    {
      "text": "学校へ行く。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35147, level 9

#### Pack A
### Level 9 (sense 35147, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "これから行く場所が楽しみです。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "これから行く場所が楽しみです。",
  "chunks": [
    "これから",
    "行く場所が",
    "楽しみです"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "行く場所が",
    "楽しみです",
    "これから"
  ],
  "target_word": "行く",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "この電車では学校へ行くことができません。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "この電車では学校へ行くことができません。",
  "chunks": [
    "この電車で",
    "は",
    "学校へ",
    "行くことが",
    "できません"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "この電車で",
    "できません",
    "行くことが",
    "は",
    "学校へ"
  ],
  "target_word": "行けない",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 35147, difficulty 5)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "明日、友達と一緒に行く。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "chunks": [
    "明日",
    "友達と",
    "一緒に",
    "行く"
  ],
  "chunk_count": 4,
  "target_word": "行く",
  "schema_version": 2,
  "shuffled_chunks": [
    "一緒に",
    "行く",
    "明日",
    "友達と"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "明日、友達と一緒に行く。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "一人で行くことができる。"
}
```

---
