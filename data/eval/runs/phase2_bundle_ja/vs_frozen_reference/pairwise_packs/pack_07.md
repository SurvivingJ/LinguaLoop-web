# Pairwise review pack 07

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


## sense 39187, level 9

#### Pack A
### Level 9 (sense 39187, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "自らの意見を持つ。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "自らの",
    "意見を",
    "持つ"
  ],
  "chunk_count": 3,
  "target_word": "自ら",
  "schema_version": 2,
  "shuffled_chunks": [
    "持つ",
    "意見を",
    "自らの"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "自らの意見を持つ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "自らを",
    "信じることが",
    "大切だ"
  ],
  "chunk_count": 3,
  "target_word": "自ら",
  "schema_version": 2,
  "shuffled_chunks": [
    "信じることが",
    "大切だ",
    "自らを"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "自らを信じることが大切だ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "自らを信じることが大切だ。"
}
```

#### Pack B
### Level 9 (sense 39187, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼女は自ら行動できる人です。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼は自らその問題を解決した。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は自らその問題を解決した。",
  "chunks": [
    "彼は",
    "自らその問題を",
    "解決した"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "自らその問題を",
    "解決した",
    "彼は"
  ],
  "target_word": "自ら",
  "chunk_count": 3
}
```

---

## sense 39661, level 1

#### Pack A
### Level 1 (sense 39661, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "営み",
  "options": [
    "いとうなみ",
    "いいとなみ",
    "いとなみ",
    "いどなみ"
  ],
  "correct_answer": "いとなみ",
  "word": "営み",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "itonami",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "営み",
    "住み",
    "悩み",
    "試み"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。」という意味です。",
  "distractor_explanations": {
    "試み": "",
    "悩み": "",
    "住み": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "いとなみ",
  "options": [
    "宇宙",
    "経営",
    "運営",
    "営み"
  ],
  "correct_answer": "営み",
  "word": "営み",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "運営": "component",
    "宇宙": "component",
    "経営": "component"
  }
}
```

#### Pack B
### Level 1 (sense 39661, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "prompt": "営み",
  "options": [
    "いとうなみ",
    "いいとなみ",
    "いとなみ",
    "いどなみ"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "いとなみ",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "itanami",
  "word": "営み",
  "options": [
    "伊弉冉",
    "人波",
    "営む",
    "営み"
  ],
  "audio_url": null,
  "explanation": "正解です。「営み」は「生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。」という意味です。",
  "pronunciation": "いとなみ",
  "correct_answer": "営み",
  "syllable_count": 4,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "人波": "「人波」は「営み」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ひ」、一部の音の違い）。",
    "営む": "「営む」は「営み」と一モーラだけ異なる実在語です（4モーラ目: 「み」→「む」、一部の音の違い）。",
    "伊弉冉": "「伊弉冉」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "prompt": "いとなみ",
  "options": [
    "宇宙",
    "経営",
    "運営",
    "営み"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "営み",
  "schema_version": 2,
  "distractor_sources": {
    "宇宙": "component",
    "経営": "component",
    "運営": "component"
  }
}
```

---

## sense 39661, level 2

#### Pack A
### Level 2 (sense 39661, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "correct_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
  "options": [
    "人の口の中にある、食べ物をかんだり噛み切ったりするための固い器官。",
    "空中に浮かび上がるように、軽やかに上昇すること。ほこりや花びら、紙くずなどが風に乗って舞い上がる様子を表す。",
    "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
    "昼の食事。昼ごはん。ランチ。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物を入れて持ち歩くための袋や箱。",
        "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
        "病気やけがをよくするために、お医者さんがすることです。",
        "物や状態を、元の場所や元の形、元の状態に変えること。"
      ],
      "correct_answer": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 39661, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "何かを中心にして、自分たちで進めていくこと。",
        "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
        "an ideal",
        "何かをするときの、特別なやり方や方法のことです。"
      ],
      "correct_answer": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。"
    }
  },
  "tier": "T6",
  "word": "営み",
  "pronunciation": "いとなみ",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "options": [
    "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
    "動力や電気で動き、人間の代わりに仕事をする装置。",
    "あるものと別のものが、状態ややり方において同じであることを示す言葉。",
    "心に情景やイメージを浮かべること。想像すること。"
  ],
  "pronunciation": "いとなみ",
  "correct_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。"
}
```

---

## sense 39661, level 4

#### Pack A
### Level 4 (sense 39661, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "しかし、微生物の___を経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。",
  "original_sentence": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。",
  "target_word": "営み",
  "word": "営み",
  "answer": {
    "accepted": [
      "営み",
      "営む"
    ],
    "accepted_normalized": [
      "営み",
      "営む"
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
**particle_selection** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "しかし、微生物___営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。",
  "original_sentence": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。",
  "options": [
    "に",
    "の",
    "が",
    "を"
  ],
  "correct_answer": "の",
  "target_word": "営み",
  "error_tags": {
    "を": "",
    "に": "",
    "が": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。「微生物の営み」と所有・属性を表す格助詞「の」が自然です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "森の中の生き物の___は神秘的だ。",
  "original_sentence": "森の中の生き物の営みは神秘的だ。",
  "target_word": "営み",
  "word": "営み",
  "answer": {
    "accepted": [
      "営み",
      "営む"
    ],
    "accepted_normalized": [
      "営み",
      "営む"
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
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "森___中の生き物の営みは神秘的だ。",
  "original_sentence": "森の中の生き物の営みは神秘的だ。",
  "options": [
    "の",
    "に",
    "を",
    "が"
  ],
  "correct_answer": "の",
  "target_word": "営み",
  "error_tags": {
    "を": "",
    "に": "",
    "が": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "正解。「生き物の営み」と所有・属性を表す格助詞「の」が自然です。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 39661, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "answer": {
    "accepted": [
      "営み",
      "営む"
    ],
    "accepted_normalized": [
      "営み",
      "営む"
    ]
  },
  "input_mode": "ime",
  "target_word": "営み",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "それはまさに、自然の営みと時間が凝縮したかような深紅を纏うリンゴであった。",
  "sentence_with_blank": "それはまさに、自然の___と時間が凝縮したかような深紅を纏うリンゴであった。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "営み",
  "answer": {
    "accepted": [
      "営み",
      "営む"
    ],
    "accepted_normalized": [
      "営み",
      "営む"
    ]
  },
  "input_mode": "ime",
  "target_word": "営み",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "小さな営みが積み重なる。",
  "sentence_with_blank": "小さな___が積み重なる。"
}
```

---

## sense 39661, level 9

#### Pack A
### Level 9 (sense 39661, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "家族の営みは、毎日少しずつ積み重なっている。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "家族の営みは、毎日少しずつ積み重なっている。",
  "chunks": [
    "家族の",
    "営みは",
    "毎日少しずつ",
    "積み重なって",
    "いる"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "毎日少しずつ",
    "営みは",
    "積み重なって",
    "いる",
    "家族の"
  ],
  "target_word": "営み",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営み。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営み。",
  "chunks": [
    "無機質な素材が",
    "自律的",
    "実体へと",
    "昇華する奇跡を",
    "自らの双手で",
    "紡ぎ出す営み"
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
    "紡ぎ出す営み",
    "昇華する奇跡を",
    "実体へと",
    "自らの双手で",
    "無機質な素材が",
    "自律的"
  ],
  "target_word": "営み",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 39661, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "毎日の営みを大切にする。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "毎日の",
    "営みを",
    "大切にする"
  ],
  "chunk_count": 3,
  "target_word": "営み",
  "schema_version": 2,
  "shuffled_chunks": [
    "営みを",
    "毎日の",
    "大切にする"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "original_sentence": "毎日の営みを大切にする。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "しかし微生物の営みを経ることで",
    "難消化性の成分は",
    "低分子化され栄養価が",
    "劇的に向上するのみ",
    "ならずフィチン酸など",
    "の抗栄養因子も分解される"
  ],
  "chunk_count": 6,
  "target_word": "営み",
  "schema_version": 2,
  "shuffled_chunks": [
    "の抗栄養因子も分解される",
    "劇的に向上するのみ",
    "低分子化され栄養価が",
    "ならずフィチン酸など",
    "しかし微生物の営みを経ることで",
    "難消化性の成分は"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解される。"
}
```

---

## sense 53352, level 1

#### Pack A
### Level 1 (sense 53352, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "prompt": "超え",
  "options": [
    "こえいる",
    "ごえる",
    "こうえる",
    "こえる"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "こえる",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "/ko̞eɾɯ/",
  "word": "超える",
  "options": [
    "還る",
    "超える",
    "生える",
    "返る"
  ],
  "audio_url": null,
  "explanation": "正解です。「超える」は「限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。」という意味です。",
  "pronunciation": "こえる",
  "correct_answer": "超える",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "返る": "「返る」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「か」、一部の音の違い）。",
    "還る": "「還る」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「か」、一部の音の違い）。",
    "生える": "「生える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「は」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "prompt": "こえる",
  "options": [
    "超える",
    "超越",
    "超え",
    "越える"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "超え",
  "schema_version": 2,
  "distractor_sources": {
    "超越": "component",
    "超える": "homophone",
    "越える": "homophone"
  }
}
```

#### Pack B
### Level 1 (sense 53352, difficulty None)
**kanji_to_reading** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "超える",
  "options": [
    "こえいる",
    "ごえる",
    "こうえる",
    "こえる"
  ],
  "correct_answer": "こえる",
  "word": "超える",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "超える",
  "pronunciation": "こえる",
  "ipa": "ko.e.ru",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "変え",
    "据え",
    "超える",
    "添え"
  ],
  "correct_answer": "超える",
  "explanation": "正解です。「超える」は「きまった数や範囲よりも多くなること。また、その先へ進むこと。」という意味です。",
  "distractor_explanations": {
    "添え": "",
    "据え": "",
    "変え": ""
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "prompt": "こえる",
  "options": [
    "起こし",
    "起きる",
    "超える",
    "越える"
  ],
  "correct_answer": "超える",
  "word": "超える",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "越える": "homophone",
    "起こし": "component",
    "起きる": "component"
  }
}
```

---

## sense 53352, level 2

#### Pack A
### Level 2 (sense 53352, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "options": [
    "外部から内部へ、人や物が流れ込むこと。特に、人の移動やお金などの資源が他地域から入ってくる場合に使う。",
    "物事が進んでいくこと。",
    "自分自身を指す言葉。",
    "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。"
  ],
  "pronunciation": "こえる",
  "correct_definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "早餐",
        "purchasing; acquiring — paying money to make a good or asset one's own",
        "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
        "colony collapse disorder — worker honeybees suddenly vanishing until the colony collapses"
      ],
      "correct_answer": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。"
    }
  },
  "tier": "T3",
  "word": "超え",
  "pronunciation": "こえる",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 53352, difficulty None)
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "超え",
  "pronunciation": "こえる",
  "correct_definition": "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
  "options": [
    "位置が低いところから高いところへ移る。",
    "数字の2。",
    "仕事や活動をして得るお金や利益のこと。",
    "きまった数や範囲よりも多くなること。また、その先へ進むこと。"
  ]
}
```
**definition_match** variant `A`, tier `T4`
```json
{
  "word": "超え",
  "pronunciation": "こえる",
  "tier": "T4",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "複数の人や物が集まって一つのまとまりになったもの。特に、共同で何かをするための組織や団体。",
        "ある物事が他の物事に対して及ぼす作用や効果。また、機能や活動。",
        "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
        "to export — selling goods produced at home to other countries"
      ],
      "correct_answer": "きまった数や範囲よりも多くなること。また、その先へ進むこと。"
    }
  }
}
```

---

## sense 53352, level 3

#### Pack A
### Level 3 (sense 53352, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "この活動は、ただ植物を育てることを___、環境を守り仲間と協力する点に意味があります。",
  "original_sentence": "この活動は、ただ植物を育てることを超え、環境を守り仲間と協力する点に意味があります。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "過ぎ",
    "抜け",
    "離れ"
  ],
  "explanation": "文脈：「植物を育てる」という行為の範囲・限界を出て、さらに高い次元（環境保護など）に進むことを表すため、「超え」が適切です。",
  "distractor_tags": {},
  "word_definition": "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
  "target_word": "超え"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "山を___ると、きれいな湖が見えます。",
  "original_sentence": "山を越えると、きれいな湖が見えます。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "抜け",
    "過ぎ",
    "離れ"
  ],
  "explanation": "文脈：「山」という物理的・概念的な障害や境界を向こう側へ進むことを表すため、「越え」または「超え」の文脈ですが、ここでは標高や困難さという「限度」を意味的に含むため「超え」が正解となります（※問題文のターゲット指定に従う）。ただし、一般的な物理的移動は「越え」ですが、本問の定義「きまった数や範囲よりも多くなること、またその先へ進むこと」に基づき、選択肢の中から文脈に合うものを選びます。実際の変体Bの文6は「山を越えると」でありターゲットが「越え」ですが、L3の指示通り文インデックス0/6を使用します。文0の文脈（概念的超越）に合わせて「超え」を正解とします。",
  "distractor_tags": {},
  "word_definition": "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
  "target_word": "越え"
}
```

#### Pack B
### Level 3 (sense 53352, difficulty 5)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "options": [
    "覚え",
    "守り",
    "超え",
    "閉じ"
  ],
  "explanation": "正解。「保存技法の域を超え」で、その範囲の外へ出る意味になる。",
  "target_word": "超え",
  "correct_answer": "超え",
  "distractor_tags": {},
  "word_definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
  "original_sentence": "微生物の代謝作用である発酵は、単なる保存技法の域を超え、主食の持つ潜在能力を飛躍的に拡張する化学的芸術である。",
  "sentence_with_blank": "微生物の代謝作用である発酵は、単なる保存技法の域を___、主食の持つ潜在能力を飛躍的に拡張する化学的芸術である。"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "超える",
    "貸す",
    "下げる",
    "洗う"
  ],
  "explanation": "正解。「限界を超える」で、今の力の先へいく意味になる。",
  "target_word": "超える",
  "correct_answer": "超える",
  "distractor_tags": {},
  "word_definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
  "original_sentence": "限界を超える練習はつらい。",
  "sentence_with_blank": "限界を___練習はつらい。"
}
```

---

## sense 53352, level 4

#### Pack A
### Level 4 (sense 53352, difficulty None)
**cloze_typed** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "学校の行事という特別な場では、Tシャツのデザインは単なる飾りを___、グループの中での役割や個性を表すものになります。",
  "original_sentence": "学校の行事という特別な場では、Tシャツのデザインは単なる飾りを超え、グループの中での役割や個性を表すものになります。",
  "target_word": "超え",
  "word": "超え",
  "answer": {
    "accepted": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ],
    "accepted_normalized": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
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
  "sentence_with_blank": "学校の行事という特別な場では、Tシャツのデザインは単なる飾りを___、グループの中での役割や個性を表すものになります。",
  "original_sentence": "学校の行事という特別な場では、Tシャツのデザインは単なる飾りを超え、グループの中での役割や個性を表すものになります。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形",
  "options": [
    "超えて",
    "超える",
    "超えた",
    "超え"
  ],
  "explanation": "文脈上の接続関係から、連用形（マス形去掉）が適切です。",
  "word_definition": "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "学校の行事という特別な場では、Tシャツのデザインは単なる飾り___超え、グループの中での役割や個性を表すものになります。",
  "original_sentence": "学校の行事という特別な場では、Tシャツのデザインは単なる飾りを超え、グループの中での役割や個性を表すものになります。",
  "options": [
    "と",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「飾り」は「超える」という動作の対象（限界となるもの）であるため、対格助詞「を」が必要です。"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "この橋は川を___て両岸をつないでいます。",
  "original_sentence": "この橋は川を超えて両岸をつないでいます。",
  "target_word": "超え",
  "word": "超え",
  "answer": {
    "accepted": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ],
    "accepted_normalized": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
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
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この橋は川を___て両岸をつないでいます。",
  "original_sentence": "この橋は川を超えて両岸をつないでいます。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形",
  "options": [
    "超えない",
    "超える",
    "超えた",
    "超え"
  ],
  "explanation": "文脈から接続助詞「て」に続く連用形（ます形の語幹）が正解です",
  "word_definition": "きまった数や範囲よりも多くなること。また、その先へ進むこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この橋は川___超えて両岸をつないでいます。",
  "original_sentence": "この橋は川を超えて両岸をつないでいます。",
  "options": [
    "に",
    "と",
    "を",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "に": "",
    "で": "",
    "と": ""
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「川」は「超える（渡る）」という動作の対象となる空間的範囲であるため、対格助詞「を」が必要です。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 53352, difficulty 5)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "answer": {
    "accepted": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ],
    "accepted_normalized": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ]
  },
  "input_mode": "ime",
  "target_word": "超え",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "この取り組みは、単なる植物の栽培を超え、環境再生と社会的結束の醸成を同時に企図する点に特徴がある。",
  "sentence_with_blank": "この取り組みは、単なる植物の栽培を___、環境再生と社会的結束の醸成を同時に企図する点に特徴がある。"
}
```
**morphology_slot** variant `A`, tier `T3`
```json
{
  "options": [
    "超え",
    "超えた",
    "超えない",
    "超えよう"
  ],
  "base_form": "超える",
  "form_label": "連用形（中止法）",
  "explanation": "連用形で読点の後の句へ並べてつなぐ中止法になる",
  "target_word": "超え",
  "correct_answer": "超え",
  "word_definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
  "original_sentence": "この取り組みは、単なる植物の栽培を超え、環境再生と社会的結束の醸成を同時に企図する点に特徴がある。",
  "sentence_with_blank": "この取り組みは、単なる植物の栽培を___、環境再生と社会的結束の醸成を同時に企図する点に特徴がある。"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "「ある」の主体「特徴」を主格で示す"
    }
  },
  "options": [
    "が",
    "に",
    "へ",
    "を"
  ],
  "error_tags": {
    "に": "location_vs_target",
    "へ": "direction",
    "を": "object_marking"
  },
  "target_word": "超え",
  "correct_answer": "が",
  "schema_version": 2,
  "original_sentence": "この取り組みは、単なる植物の栽培を超え、環境再生と社会的結束の醸成を同時に企図する点に特徴がある。",
  "sentence_with_blank": "この取り組みは、単なる植物の栽培を超え、環境再生と社会的結束の醸成を同時に企図する点に特徴___ある。"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "word": "超え",
  "answer": {
    "accepted": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ],
    "accepted_normalized": [
      "超え",
      "超えた",
      "超えて",
      "超えない",
      "超えられる"
    ]
  },
  "input_mode": "ime",
  "target_word": "超え",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "予算を超えないように買い物をした。",
  "sentence_with_blank": "予算を___ないように買い物をした。"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "options": [
    "超える",
    "超え",
    "超えた",
    "超えろ"
  ],
  "base_form": "超える",
  "form_label": "未然形（ない形）",
  "explanation": "「ない」に続く未然形で「超えない」となる",
  "target_word": "超え",
  "correct_answer": "超え",
  "word_definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
  "original_sentence": "予算を超えないように買い物をした。",
  "sentence_with_blank": "予算を___ないように買い物をした。"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "nl": {
    "en": {
      "explanation": "「超える」の対象「予算」を示す"
    }
  },
  "options": [
    "を",
    "で",
    "に",
    "と"
  ],
  "error_tags": {
    "で": "instrument",
    "と": "other",
    "に": "location_vs_target"
  },
  "target_word": "超え",
  "correct_answer": "を",
  "schema_version": 2,
  "original_sentence": "予算を超えないように買い物をした。",
  "sentence_with_blank": "予算___超えないように買い物をした。"
}
```

---

## sense 53352, level 6

#### Pack A
### Level 6 (sense 53352, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "その行為は単なるガーデニングの域を超えられ、自然の摂理に対する静かなる祈りにも似ている。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ている。",
      "is_correct": true
    },
    {
      "text": "その行為は単なるガーデニングの域を超えつつ、自然の摂理に対する静かなる祈りにも似ている。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超えたり、自然の摂理に対する静かなる祈りにも似ている。",
      "is_correct": false
    }
  ],
  "explanation": "「超えられ」は可能・受動態ですが、ここでは事実としてその域を出ていることを述べる必要があり、単純な接続形「超え」が自然です。また、文脈的に能力の話ではありません。 「〜しつつ」は同時進行を表しますが、「域を出す」という状態変化と「似ている」という性質の記述は同時進行ではなく、論理的な飛躍・包含関係にあるため不適切です。 「〜たり」は例示や並列を表しますが、後半の文が例示ではなく本質的な比喩であるため、文法的・意味的に接続が不自然です。",
  "target_word": "超え"
}
```

#### Pack B
### Level 6 (sense 53352, difficulty 5)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "気温が三十度超えたを。",
      "is_correct": false
    },
    {
      "text": "気温が三十度が超えた。",
      "is_correct": false
    },
    {
      "text": "明日、気温は三十度を超えた。",
      "is_correct": false
    },
    {
      "text": "学校イベントという儀礼的空間において、Tシャツデザインは単なる装飾を超え、集団内の微細な階層や個性の顕現として機能し得る。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：超える対象には「を」を使い、「三十度を超えた」が正しい。 活用・アスペクトの誤り：未来の「明日」に過去形「超えた」は合わない。 語順の誤り：助詞「を」は目的語「三十度」の直後に置き、「三十度を超えた」とする。",
  "target_word": "超え"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
      "explanation": "基準より上へ出る「超える」に対し、基準より下になる"
    }
  },
  "word": "超え",
  "options": [
    "下回る",
    "増える",
    "達する",
    "上回る"
  ],
  "relation": "antonym",
  "correct_answer": "下回る",
  "schema_version": 2
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "点数が目標を取れた超える。",
      "is_correct": false
    },
    {
      "text": "目標を超える点数が取れた。",
      "is_correct": true
    },
    {
      "text": "目標に超える点数が取れた。",
      "is_correct": false
    },
    {
      "text": "昨日、目標を超える点数が取れる。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「目標を超える」が正しい。 活用・アスペクトの誤り：過去の「昨日」に非過去「取れる」は合わない。 語順の誤り：連体修飾「目標を超える」は名詞「点数」の前に置く。",
  "target_word": "超える"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "nl": {
    "en": {
      "definition": "限度や基準をこえて、その先へいくこと。数や量が基準より多くなること。",
      "explanation": "目標より上になる「超える」に対し、目標より下になる"
    }
  },
  "word": "超え",
  "options": [
    "目指す",
    "上回る",
    "下回る",
    "達する"
  ],
  "relation": "antonym",
  "correct_answer": "下回る",
  "schema_version": 2
}
```

---
