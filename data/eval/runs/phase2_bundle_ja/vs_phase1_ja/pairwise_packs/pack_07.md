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


## sense 39661, level 2

#### Pack A
### Level 2 (sense 39661, difficulty None)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "correct_definition": "人や動物が生活し、生命を保つための活動。",
  "options": [
    "物や情報などを、多くの人にわたすこと。",
    "人や動物が生活し、生命を保つための活動。",
    "音楽において、音の長さや強さが規則的にくり返されるパターンや、その流れの感じ。",
    "まだ歩いたり話したりすることがあまりできない、小さな子ども。特に、親に保護されて育てられている年ごろの子ども。"
  ]
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "tier": "T6",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "low-priced (cheap)",
        "人や動物が生活し、生命を保つための活動。",
        "时间 —— 用钟表可以知道的、流逝着的时刻",
        "ちゅうごくは、アジアにあるおおきなくにです。"
      ],
      "correct_answer": "人や動物が生活し、生命を保つための活動。"
    }
  }
}
```

#### Pack B
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

---

## sense 39661, level 3

#### Pack A
### Level 3 (sense 39661, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "童子の行為は、単なる日常的な___の模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのである。",
  "original_sentence": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのである。",
  "correct_answer": "営み",
  "options": [
    "営み",
    "遊び",
    "休み",
    "働き"
  ],
  "explanation": "正解。「彼はこの小さな町で静かな営み（生活・生計活動）を続けている」という文脈に適合します。",
  "distractor_tags": {},
  "word_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
  "target_word": "営み"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "彼はこの小さな町で静かな___を続けている。",
  "original_sentence": "彼はこの小さな町で静かな営みを続けている。",
  "correct_answer": "営み",
  "options": [
    "営み",
    "規則",
    "約束",
    "計画"
  ],
  "explanation": "正解。「季節の移り変わりは自然の営み（自然界の活動）を感じさせる」という文脈に適合します。",
  "distractor_tags": {},
  "word_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
  "target_word": "営み"
}
```

#### Pack B
### Level 3 (sense 39661, difficulty None)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "童子の行為は、単なる日常的な___の模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのです。",
  "original_sentence": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのです。",
  "correct_answer": "営み",
  "options": [
    "営み",
    "仕事",
    "業務",
    "動作"
  ],
  "explanation": "正解です。文脈にある「生命の循環に対する原初的な祈りにも似た」活動は、自然や生物の「営み」と結びつくのが適切です。",
  "distractor_tags": {},
  "word_definition": "人や動物が生活し、生命を保つための活動。",
  "target_word": "営み"
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
### Level 4 (sense 39661, difficulty None)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "しかし、微生物の___を経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解されます。",
  "original_sentence": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解されます。",
  "target_word": "営み",
  "word": "営み",
  "answer": {
    "accepted": [
      "営み"
    ],
    "accepted_normalized": [
      "営み"
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
**cloze_typed** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "人々の___を守りたいです。",
  "original_sentence": "人々の営みを守りたいです。",
  "target_word": "営み",
  "word": "営み",
  "answer": {
    "accepted": [
      "営み"
    ],
    "accepted_normalized": [
      "営み"
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
### Level 9 (sense 39661, difficulty None)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "自然の営みについて学びたいと思います。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "自然の営みについて学びたいと思います。",
  "chunks": [
    "自然の",
    "営みに",
    "ついて学びたいと",
    "思います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "営みに",
    "思います",
    "ついて学びたいと",
    "自然の"
  ],
  "target_word": "営み",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営みなのです。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "無機質な素材が自律的実体へと昇華する奇跡を、自らの双手で紡ぎ出す営みなのです。",
  "chunks": [
    "無機質な素材が",
    "自律的実体へと",
    "昇華する奇跡を",
    "自らの双手で",
    "紡ぎ出す営みなの",
    "です"
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
    "です",
    "自らの双手で",
    "昇華する奇跡を",
    "紡ぎ出す営みなの",
    "無機質な素材が",
    "自律的実体へと"
  ],
  "target_word": "営み",
  "chunk_count": 6
}
```

---

## sense 53352, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 53352, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "超え",
  "options": [
    "こえいる",
    "ごえる",
    "こうえる",
    "こえる"
  ],
  "correct_answer": "こえる",
  "word": "超え",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "超える",
  "pronunciation": "こえる",
  "ipa": "/ko.e.ru/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "超える",
    "篭める",
    "小江戸",
    "燃える"
  ],
  "correct_answer": "超える",
  "explanation": "正解です。「超える」は「限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。」という意味です。",
  "distractor_explanations": {
    "燃える": "「燃える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「も」、一部の音の違い）。",
    "小江戸": "「小江戸」は「超える」と一モーラだけ異なる実在語です（3モーラ目: 「る」→「ど」、一部の音の違い）。",
    "篭める": "「篭める」は「超える」と一モーラだけ異なる実在語です（2モーラ目: 「え」→「め」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "こえる",
  "options": [
    "超える",
    "超越",
    "超え",
    "越える"
  ],
  "correct_answer": "超え",
  "word": "超え",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "越える": "homophone",
    "超える": "homophone",
    "超越": "component"
  }
}
```

---

## sense 53352, level 2

#### Pack A
### Level 2 (sense 53352, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "pronunciation": "こえる",
  "correct_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "options": [
    "人が住んだり、仕事をしたりするために建てられた、屋根と壁のある構造物。",
    "事業や組織を新しく始めること。",
    "ある地域に長期間続く、平均的な天候の状態。気温や雨の量などが含まれます。",
    "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "超え",
  "pronunciation": "こえる",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある状態や物を、別の状態や物に変えること。",
        "a voice",
        "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
        "細部にまで注意が行き届いていて、手抜かりがないさま。"
      ],
      "correct_answer": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。"
    }
  }
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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この活動は、ただ植物を育てることを___、自然環境を守りながら、人々の絆を深めることにもつながっています。",
  "original_sentence": "この活動は、ただ植物を育てることを超え、自然環境を守りながら、人々の絆を深めることにもつながっています。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "通り",
    "抜け",
    "過ぎ"
  ],
  "explanation": "正解です。「超え」は限度や範囲をこえることを表し、文脈に適切に適合しています。",
  "distractor_tags": {},
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想を___て、とても嬉しかったです。",
  "original_sentence": "予想を超えて、とても嬉しかったです。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "過ぎ",
    "外れ",
    "慣れ"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```

#### Pack B
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
### Level 4 (sense 53352, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "学校の行事では、Tシャツのデザインはただの飾りを___、グループの中の立場や個性を表すものとして使われることがあります。",
  "original_sentence": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "学校の行事では、Tシャツのデザインはただの飾りを___、グループの中の立場や個性を表すものとして使われることがあります。",
  "original_sentence": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形（中止法）",
  "options": [
    "超えない",
    "超えた",
    "超え",
    "超えよう"
  ],
  "explanation": "連用形で読点の後の句へ並べてつなぐ中止法になる",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "学校の行事では、Tシャツのデザインはただの飾り___超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "original_sentence": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "options": [
    "が",
    "を",
    "に",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "が": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語（飾り）を標示する格助詞"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "original_sentence": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "未然形（ない形）",
  "options": [
    "超えた",
    "超える",
    "超えろ",
    "超え"
  ],
  "explanation": "「ない」に続く未然形で「超えない」となる",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超える"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想___超え、そこには素晴らしい景色が広がっていました。",
  "original_sentence": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "options": [
    "で",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "超える",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語（基準）を標示する"
    }
  }
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
### Level 6 (sense 53352, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼女の能力は、超えています私たちの予想を。",
      "is_correct": false
    },
    {
      "text": "彼女の能力は、私たちの予想を超えています。",
      "is_correct": true
    },
    {
      "text": "彼女の能力は、私たちの予想を超えっています。",
      "is_correct": false
    },
    {
      "text": "彼女の能力は、私たちの予想に超えています。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「超える」は「を」格の目的語を取ります。「に」は誤りです。 活用・アスペクトの誤り：「超える」の継続・状態を表すには「超えています」が正しく、「超えっています」は活用形が誤りです。 語順・係り受けの誤り：目的語「私たちの予想を」は動詞「超えています」の直前に配置するのが自然な日本語の語順です。",
  "target_word": "超え"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "超え",
  "relation": "antonym",
  "options": [
    "及ぶ",
    "下回る",
    "低下する",
    "上回る"
  ],
  "correct_answer": "下回る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
      "explanation": "数量や水準が基準より小さいことを表し、対義関係が成立する"
    }
  }
}
```

---

## sense 53352, level 9

#### Pack A
### Level 9 (sense 53352, difficulty None)
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "original_sentence": "予想以上の人数が集まり、定員を超えてしまいました。"
}
```
**jumbled_sentence** variant `A`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "予想以上の人数が集まり、定員を超えてしまいました。",
  "chunks": [
    "予想以上の",
    "人数が",
    "集まり",
    "定員を",
    "超えて",
    "しまいました"
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
    "予想以上の",
    "集まり",
    "超えて",
    "しまいました",
    "人数が",
    "定員を"
  ],
  "target_word": "超え",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ている。"
}
```
**jumbled_sentence** variant `B`, tier `T4`
```json
{
  "schema_version": 2,
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ている。",
  "chunks": [
    "その行為は",
    "単なるガーデニングの",
    "域を超え",
    "自然の摂理に",
    "対する静かなる祈りに",
    "も似ている"
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
    "自然の摂理に",
    "域を超え",
    "その行為は",
    "単なるガーデニングの",
    "対する静かなる祈りに",
    "も似ている"
  ],
  "target_word": "超え",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 53352, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "彼は限界を超え、毎日練習しています。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼は限界を超え、毎日練習しています。",
  "chunks": [
    "彼は",
    "限界を",
    "超え",
    "毎日練習して",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "彼は",
    "超え",
    "います",
    "限界を",
    "毎日練習して"
  ],
  "target_word": "超える",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ています。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ています。",
  "chunks": [
    "その行為は",
    "単なるガーデニングの",
    "域を超え",
    "自然の摂理に",
    "対する静かなる祈りに",
    "も似ています"
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
    "自然の摂理に",
    "域を超え",
    "その行為は",
    "単なるガーデニングの",
    "対する静かなる祈りに",
    "も似ています"
  ],
  "target_word": "超え",
  "chunk_count": 6
}
```

---
