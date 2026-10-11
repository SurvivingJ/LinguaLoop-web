# Pairwise review pack 01

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


## sense 10103, level 1

#### Pack A
### Level 1 (sense 10103, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "早",
  "options": [
    "zǎo",
    "zāo",
    "záo",
    "zào"
  ],
  "correct_answer": "zǎo",
  "word": "早",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "早",
    "options": [
      "zǎo",
      "zāo",
      "záo",
      "zào"
    ],
    "correct_answer": "zǎo",
    "word": "早",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "ipa": "[tsaʊ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "早",
    "灶",
    "凿",
    "糟"
  ],
  "correct_answer": "早",
  "explanation": "正确：“早”读第三声（zǎo），指太阳刚升起或时间靠前的时段，符合目标词的语音和语义。",
  "distractor_explanations": {
    "糟": "声调错误：“糟”读第一声（zāo），意思是坏、糟糕，与目标词“早”的第三声不同，声调改变导致意义完全不同。",
    "凿": "声调错误：“凿”读第二声（záo），意思是打孔或挖掘工具，与目标词“早”的第三声不同，声调改变导致意义完全不同。",
    "灶": "声调错误：“灶”读第四声（zào），意思是生火做饭的设备，与目标词“早”的第三声不同，声调改变导致意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsaʊ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "早",
      "灶",
      "鑿",
      "糟"
    ],
    "correct_answer": "早",
    "explanation": "正確：“早”讀第三聲（zǎo），指太陽剛升起或時間靠前的時段，符合目標詞的語音和語義。",
    "distractor_explanations": {
      "糟": "聲調錯誤：“糟”讀第一聲（zāo），意思是壞、糟糕，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。",
      "凿": "聲調錯誤：“鑿”讀第二聲（záo），意思是打孔或挖掘工具，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。",
      "灶": "聲調錯誤：“灶”讀第四聲（zào），意思是生火做飯的裝置，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "zǎo",
  "options": [
    "花",
    "早",
    "相",
    "卖"
  ],
  "correct_answer": "早",
  "word": "早",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "相": "frequency",
    "花": "frequency",
    "卖": "frequency"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "zǎo",
    "options": [
      "花",
      "早",
      "相",
      "賣"
    ],
    "correct_answer": "早",
    "word": "早",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "相": "frequency",
      "花": "frequency",
      "卖": "frequency"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "早",
  "toneless_pinyin": "zao",
  "full_pinyin": "zǎo",
  "options": [
    "1",
    "3",
    "4",
    "2"
  ],
  "correct_answer": "3",
  "option_labels": {
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "早",
    "toneless_pinyin": "zao",
    "full_pinyin": "zǎo",
    "options": [
      "1",
      "3",
      "4",
      "2"
    ],
    "correct_answer": "3",
    "option_labels": {
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)"
    },
    "syllable_count": 1
  }
}
```

#### Pack B
### Level 1 (sense 10103, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "早",
  "options": [
    "zǎo",
    "zāo",
    "záo",
    "zào"
  ],
  "correct_answer": "zǎo",
  "word": "早",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "早",
    "options": [
      "zǎo",
      "zāo",
      "záo",
      "zào"
    ],
    "correct_answer": "zǎo",
    "word": "早",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "ipa": "[tsɑu˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "早",
    "造",
    "枣",
    "糟"
  ],
  "correct_answer": "早",
  "explanation": "正确。目标词，读音 zǎo，第三声，意为时间靠前。",
  "distractor_explanations": {
    "糟": "干扰项。读音 zāo，第一声，意为坏、糟糕，声调不同且语义无关。",
    "枣": "干扰项。读音 zǎo，第三声，虽同音但为名词（水果），词性与语义均不符。",
    "造": "干扰项。读音 zào，第四声，意为制造，声调不同且语义无关。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsɑu˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "早",
      "造",
      "棗",
      "糟"
    ],
    "correct_answer": "早",
    "explanation": "正確。目標詞，讀音 zǎo，第三聲，意為時間靠前。",
    "distractor_explanations": {
      "糟": "干擾項。讀音 zāo，第一聲，意為壞、糟糕，聲調不同且語義無關。",
      "枣": "干擾項。讀音 zǎo，第三聲，雖同音但為名詞（水果），詞性與語義均不符。",
      "造": "干擾項。讀音 zào，第四聲，意為製造，聲調不同且語義無關。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "zǎo",
  "options": [
    "花",
    "早",
    "相",
    "子"
  ],
  "correct_answer": "早",
  "word": "早",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "相": "frequency",
    "花": "frequency",
    "子": "frequency"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "zǎo",
    "options": [
      "花",
      "早",
      "相",
      "子"
    ],
    "correct_answer": "早",
    "word": "早",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "相": "frequency",
      "花": "frequency",
      "子": "frequency"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "早",
  "toneless_pinyin": "zao",
  "full_pinyin": "zǎo",
  "options": [
    "1",
    "3",
    "4",
    "2"
  ],
  "correct_answer": "3",
  "option_labels": {
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "早",
    "toneless_pinyin": "zao",
    "full_pinyin": "zǎo",
    "options": [
      "1",
      "3",
      "4",
      "2"
    ],
    "correct_answer": "3",
    "option_labels": {
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)"
    },
    "syllable_count": 1
  }
}
```

---

## sense 10103, level 2

#### Pack A
### Level 2 (sense 10103, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "correct_definition": "指太阳刚升起或时间靠前的时段。",
  "options": [
    "降低行动或进程的速度，使节奏放缓。",
    "指事物最初就有的、非人工加工或移植的本来状态。",
    "具有代表性或象征性的人或事物。",
    "指太阳刚升起或时间靠前的时段。"
  ],
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "correct_definition": "指太陽剛升起或時間靠前的時段。",
    "options": [
      "降低行動或程序的速度，使節奏放緩。",
      "指事物最初就有的、非人工加工或移植的本來狀態。",
      "具有代表性或象徵性的人或事物。",
      "指太陽剛升起或時間靠前的時段。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "一个国家就是一个地方，有很多很多人住在一起，有一个政府来管理。",
        "群落；同じ場所で一緒に生きる生き物の集まり",
        "指太阳刚升起或时间靠前的时段。",
        "呼応する"
      ],
      "correct_answer": "指太阳刚升起或时间靠前的时段。"
    }
  },
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "一個國家就是一個地方，有很多很多人住在一起，有一個政府來管理。",
          "群落；同じ場所で一緒に生きる生き物の集まり",
          "指太陽剛升起或時間靠前的時段。",
          "呼応する"
        ],
        "correct_answer": "指太陽剛升起或時間靠前的時段。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10103, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "correct_definition": "时间靠前的；比规定或合适的时间提前",
  "options": [
    "指事物发展所能达到的最高程度或最大范围。",
    "在赤道以南的纬度，从0°到90°S。",
    "指在会议或讨论中提出供大家审议、讨论或表决的建议或方案。",
    "时间靠前的；比规定或合适的时间提前"
  ],
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "correct_definition": "時間靠前的；比規定或合適的時間提前",
    "options": [
      "指事物發展所能達到的最高程度或最大範圍。",
      "在赤道以南的緯度，從0°到90°S。",
      "指在會議或討論中提出供大家審議、討論或表決的建議或方案。",
      "時間靠前的；比規定或合適的時間提前"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "十分；量や程度が満足できるところまで達していること",
        "尊厳",
        "时间靠前的；比规定或合适的时间提前",
        "人類学者"
      ],
      "correct_answer": "时间靠前的；比规定或合适的时间提前"
    }
  },
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "十分；量や程度が満足できるところまで達していること",
          "尊厳",
          "時間靠前的；比規定或合適的時間提前",
          "人類學者"
        ],
        "correct_answer": "時間靠前的；比規定或合適的時間提前"
      }
    }
  }
}
```

---

## sense 10103, level 4

#### Pack A
### Level 4 (sense 10103, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "他今天来得很___。",
  "original_sentence": "他今天来得很早。",
  "target_word": "早",
  "word": "早",
  "answer": {
    "accepted": [
      "早",
      "早晚",
      "早上",
      "提早",
      "早早"
    ],
    "accepted_normalized": [
      "早",
      "早晚",
      "早上",
      "提早",
      "早早"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "他今天來得很___。",
    "original_sentence": "他今天來得很早。",
    "target_word": "早",
    "word": "早",
    "answer": {
      "accepted": [
        "早",
        "早晚",
        "早上",
        "提早",
        "早早"
      ],
      "accepted_normalized": [
        "早",
        "早晚",
        "早上",
        "提早",
        "早早"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这趟火车发车时间有点___。",
  "original_sentence": "这趟火车发车时间有点早。",
  "target_word": "早",
  "word": "早",
  "answer": {
    "accepted": [
      "早",
      "早晚",
      "早上",
      "提早",
      "早早"
    ],
    "accepted_normalized": [
      "早",
      "早晚",
      "早上",
      "提早",
      "早早"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這趟火車發車時間有點___。",
    "original_sentence": "這趟火車發車時間有點早。",
    "target_word": "早",
    "word": "早",
    "answer": {
      "accepted": [
        "早",
        "早晚",
        "早上",
        "提早",
        "早早"
      ],
      "accepted_normalized": [
        "早",
        "早晚",
        "早上",
        "提早",
        "早早"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

#### Pack B
### Level 4 (sense 10103, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "我们___点出发，免得错过精彩的表演。",
  "original_sentence": "我们早点出发，免得错过精彩的表演。",
  "target_word": "早",
  "word": "早",
  "answer": {
    "accepted": [
      "早",
      "早晨",
      "早上",
      "早餐",
      "早早"
    ],
    "accepted_normalized": [
      "早",
      "早晨",
      "早上",
      "早餐",
      "早早"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "我們___點出發，免得錯過精彩的表演。",
    "original_sentence": "我們早點出發，免得錯過精彩的表演。",
    "target_word": "早",
    "word": "早",
    "answer": {
      "accepted": [
        "早",
        "早晨",
        "早上",
        "早餐",
        "早早"
      ],
      "accepted_normalized": [
        "早",
        "早晨",
        "早上",
        "早餐",
        "早早"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "虽然起得___，但他上课还是听着听着睡着了。",
  "original_sentence": "虽然起得早，但他上课还是听着听着睡着了。",
  "target_word": "早",
  "word": "早",
  "answer": {
    "accepted": [
      "早",
      "早晨",
      "早上",
      "早餐",
      "早早"
    ],
    "accepted_normalized": [
      "早",
      "早晨",
      "早上",
      "早餐",
      "早早"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "雖然起得___，但他上課還是聽著聽著睡著了。",
    "original_sentence": "雖然起得早，但他上課還是聽著聽著睡著了。",
    "target_word": "早",
    "word": "早",
    "answer": {
      "accepted": [
        "早",
        "早晨",
        "早上",
        "早餐",
        "早早"
      ],
      "accepted_normalized": [
        "早",
        "早晨",
        "早上",
        "早餐",
        "早早"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

---

## sense 10103, level 6

#### Pack A
### Level 6 (sense 10103, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "今年的春天很早，公园里的花儿都开着。",
      "is_correct": true
    },
    {
      "text": "今年的春天早了着，公园里的花儿都开着。",
      "is_correct": false
    },
    {
      "text": "今年的春天早出来，公园里的花儿都开着。",
      "is_correct": false
    },
    {
      "text": "很早今年的春天，公园里的花儿都开着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“早”是性质形容词，不能直接加动态助词“了”和“着”来表示动作的持续或完成。 语序错误：“很早”作为形容词短语，不能直接放在主语“今年的春天”之前作定语或状语，应放在主语之后作谓语。 结果补语误用：“早”表示时间靠前，不能带结果补语“出来”表示空间或状态的显现。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "今年的春天很早，公園裡的花兒都開著。",
        "is_correct": true
      },
      {
        "text": "今年的春天早了著，公園裡的花兒都開著。",
        "is_correct": false
      },
      {
        "text": "今年的春天早出來，公園裡的花兒都開著。",
        "is_correct": false
      },
      {
        "text": "很早今年的春天，公園裡的花兒都開著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“早”是性質形容詞，不能直接加動態助詞“了”和“著”來表示動作的持續或完成。 語序錯誤：“很早”作為形容詞短語，不能直接放在主語“今年的春天”之前作定語或狀語，應放在主語之後作謂語。 結果補語誤用：“早”表示時間靠前，不能帶結果補語“出來”表示空間或狀態的顯現。",
    "target_word": "早"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "早点你把心情调整好，别再生气了。",
      "is_correct": false
    },
    {
      "text": "你早点把心情调整早，别再生气了。",
      "is_correct": false
    },
    {
      "text": "你早点把心情调整好，别再生气了。",
      "is_correct": true
    },
    {
      "text": "你早着把心情调整好，别再生气了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“早”表示时间靠前的状态，不是持续性的动作，不能加动态助词“着”。 语序错误：时间状语“早点”应放在主语“你”之后、谓语之前，不能置于句首。 结果补语误用：“调整”的结果补语应为表示状态改变的词（如“好”），不能用表示时间的“早”作补语。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "早點你把心情調整好，別再生氣了。",
        "is_correct": false
      },
      {
        "text": "你早點把心情調整早，別再生氣了。",
        "is_correct": false
      },
      {
        "text": "你早點把心情調整好，別再生氣了。",
        "is_correct": true
      },
      {
        "text": "你早著把心情調整好，別再生氣了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“早”表示時間靠前的狀態，不是持續性的動作，不能加動態助詞“著”。 語序錯誤：時間狀語“早點”應放在主語“你”之後、謂語之前，不能置於句首。 結果補語誤用：“調整”的結果補語應為表示狀態改變的詞（如“好”），不能用表示時間的“早”作補語。",
    "target_word": "早"
  }
}
```

#### Pack B
### Level 6 (sense 10103, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这里的春天来得很早。",
      "is_correct": true
    },
    {
      "text": "这里的春天来得一个早。",
      "is_correct": false
    },
    {
      "text": "这里的春天来得很早早。",
      "is_correct": false
    },
    {
      "text": "这里的春天来得早已。",
      "is_correct": false
    }
  ],
  "explanation": "错误。形容词‘早’重叠形式‘早早’通常作状语（如‘早早地来了’），不作‘来得’后的补语，且‘很’不能修饰重叠式形容词。 错误。量词误用。形容词‘早’作补语时，前面不能加数量短语‘一个’。 错误。词性误用。‘早已’是副词，意为‘早就’，不能作‘来得’后的补语。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "這裡的春天來得很早。",
        "is_correct": true
      },
      {
        "text": "這裡的春天來得一個早。",
        "is_correct": false
      },
      {
        "text": "這裡的春天來得很早早。",
        "is_correct": false
      },
      {
        "text": "這裡的春天來得早已。",
        "is_correct": false
      }
    ],
    "explanation": "錯誤。形容詞‘早’重疊形式‘早早’通常作狀語（如‘早早地來了’），不作‘來得’後的補語，且‘很’不能修飾重疊式形容詞。 錯誤。量詞誤用。形容詞‘早’作補語時，前面不能加數量短語‘一個’。 錯誤。詞性誤用。‘早已’是副詞，意為‘早就’，不能作‘來得’後的補語。",
    "target_word": "早"
  }
}
```

---

## sense 10103, level 9

#### Pack A
### Level 9 (sense 10103, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他习惯了起早，每天五点就起床锻炼。",
  "hant": {
    "original_sentence": "他習慣了起早，每天五點就起床鍛鍊。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他习惯了起早，每天五点就起床锻炼。",
  "chunks": [
    "他习惯",
    "了起早",
    "每天五点",
    "就起床锻炼"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "了起早",
    "就起床锻炼",
    "他习惯",
    "每天五点"
  ],
  "target_word": "早",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他習慣了起早，每天五點就起床鍛鍊。",
    "chunks": [
      "他習慣",
      "了起早",
      "每天五點",
      "就起床鍛鍊"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "了起早",
      "就起床鍛鍊",
      "他習慣",
      "每天五點"
    ],
    "target_word": "早",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "今年的春天很早，公园里的花儿都开着。",
  "hant": {
    "original_sentence": "今年的春天很早，公園裡的花兒都開著。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "今年的春天很早，公园里的花儿都开着。",
  "chunks": [
    "今年的春天",
    "很早",
    "公园里的花儿",
    "都开着"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "今年的春天",
    "都开着",
    "很早",
    "公园里的花儿"
  ],
  "target_word": "早",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "今年的春天很早，公園裡的花兒都開著。",
    "chunks": [
      "今年的春天",
      "很早",
      "公園裡的花兒",
      "都開著"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "今年的春天",
      "都開著",
      "很早",
      "公園裡的花兒"
    ],
    "target_word": "早",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10103, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "为了赶车，他起得很早。",
  "hant": {
    "original_sentence": "為了趕車，他起得很早。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "为了赶车，他起得很早。",
  "chunks": [
    "为了赶车",
    "他",
    "起得很早"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "他",
    "起得很早",
    "为了赶车"
  ],
  "target_word": "早",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "為了趕車，他起得很早。",
    "chunks": [
      "為了趕車",
      "他",
      "起得很早"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "他",
      "起得很早",
      "為了趕車"
    ],
    "target_word": "早",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这里的春天来得很早。",
  "hant": {
    "original_sentence": "這裡的春天來得很早。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这里的春天来得很早。",
  "chunks": [
    "这里",
    "的",
    "春天来得很早"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "这里",
    "春天来得很早",
    "的"
  ],
  "target_word": "早",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這裡的春天來得很早。",
    "chunks": [
      "這裡",
      "的",
      "春天來得很早"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "這裡",
      "春天來得很早",
      "的"
    ],
    "target_word": "早",
    "chunk_count": 3
  }
}
```

---

## sense 10104, level 1

#### Pack A
### Level 1 (sense 10104, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "便",
  "options": [
    "biǎn",
    "biàn",
    "bián",
    "biān"
  ],
  "correct_answer": "biàn",
  "word": "便",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "便",
    "options": [
      "biǎn",
      "biàn",
      "bián",
      "biān"
    ],
    "correct_answer": "biàn",
    "word": "便",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "ipa": "[piɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "便",
    "边",
    "编",
    "扁"
  ],
  "correct_answer": "便",
  "explanation": "正确选项。读作第四声（biàn），表示就、立刻或容易，符合听力发音。",
  "distractor_explanations": {
    "边": "声调为第一声（biān），指边缘或旁边，与目标词第四声（biàn）声调不同。",
    "扁": "声调为第三声（biǎn），指物体平而薄，与目标词第四声（biàn）声调不同。",
    "编": "声调为第一声（biān），指把细长条的东西交叉组织起来，与目标词第四声（biàn）声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[piɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "便",
      "邊",
      "編",
      "扁"
    ],
    "correct_answer": "便",
    "explanation": "正確選項。讀作第四聲（biàn），表示就、立刻或容易，符合聽力發音。",
    "distractor_explanations": {
      "边": "聲調為第一聲（biān），指邊緣或旁邊，與目標詞第四聲（biàn）聲調不同。",
      "扁": "聲調為第三聲（biǎn），指物體平而薄，與目標詞第四聲（biàn）聲調不同。",
      "编": "聲調為第一聲（biān），指把細長條的東西交叉組織起來，與目標詞第四聲（biàn）聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "biàn",
  "options": [
    "更",
    "便",
    "做",
    "使"
  ],
  "correct_answer": "便",
  "word": "便",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "做": "component",
    "更": "component",
    "使": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "biàn",
    "options": [
      "更",
      "便",
      "做",
      "使"
    ],
    "correct_answer": "便",
    "word": "便",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "做": "component",
      "更": "component",
      "使": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "便",
  "toneless_pinyin": "bian",
  "full_pinyin": "biàn",
  "options": [
    "1",
    "3",
    "4",
    "2"
  ],
  "correct_answer": "4",
  "option_labels": {
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "便",
    "toneless_pinyin": "bian",
    "full_pinyin": "biàn",
    "options": [
      "1",
      "3",
      "4",
      "2"
    ],
    "correct_answer": "4",
    "option_labels": {
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)"
    },
    "syllable_count": 1
  }
}
```

#### Pack B
### Level 1 (sense 10104, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "便",
  "options": [
    "biǎn",
    "biàn",
    "bián",
    "biān"
  ],
  "correct_answer": "biàn",
  "word": "便",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "便",
    "options": [
      "biǎn",
      "biàn",
      "bián",
      "biān"
    ],
    "correct_answer": "biàn",
    "word": "便",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "ipa": "[piɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "辩",
    "变",
    "便",
    "遍"
  ],
  "correct_answer": "便",
  "explanation": "正确。目标词，读作 biàn，在此处作副词，表示动作轻易或快速发生。",
  "distractor_explanations": {
    "变": "错误。读音为 biàn，但意为改变、变化，与语境中“轻易/快速”的副词用法不符。",
    "遍": "错误。读音为 biàn，意为全面、到处或量词，无法充当表示“随即/轻易”的副词。",
    "辩": "错误。读音为 biàn，意为辩论、辩解，词性与语义均不符合句法要求。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[piɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "辯",
      "變",
      "便",
      "遍"
    ],
    "correct_answer": "便",
    "explanation": "正確。目標詞，讀作 biàn，在此處作副詞，表示動作輕易或快速發生。",
    "distractor_explanations": {
      "变": "錯誤。讀音為 biàn，但意為改變、變化，與語境中“輕易/快速”的副詞用法不符。",
      "遍": "錯誤。讀音為 biàn，意為全面、到處或量詞，無法充當表示“隨即/輕易”的副詞。",
      "辩": "錯誤。讀音為 biàn，意為辯論、辯解，詞性與語義均不符合句法要求。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "biàn",
  "options": [
    "更",
    "便",
    "做",
    "使"
  ],
  "correct_answer": "便",
  "word": "便",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "做": "component",
    "更": "component",
    "使": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "biàn",
    "options": [
      "更",
      "便",
      "做",
      "使"
    ],
    "correct_answer": "便",
    "word": "便",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "做": "component",
      "更": "component",
      "使": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "便",
  "toneless_pinyin": "bian",
  "full_pinyin": "biàn",
  "options": [
    "1",
    "3",
    "4",
    "2"
  ],
  "correct_answer": "4",
  "option_labels": {
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "便",
    "toneless_pinyin": "bian",
    "full_pinyin": "biàn",
    "options": [
      "1",
      "3",
      "4",
      "2"
    ],
    "correct_answer": "4",
    "option_labels": {
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)"
    },
    "syllable_count": 1
  }
}
```

---

## sense 10104, level 2

#### Pack A
### Level 2 (sense 10104, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "correct_definition": "副词，表示做某事不费力气或时间很短。",
  "options": [
    "副词，表示做某事不费力气或时间很短。",
    "指在工厂、企业等单位中从事体力或技术劳动、以工资收入为主要生活来源的人。",
    "指流动的空气，即气流。",
    "风的大小或强度，通常用等级表示。"
  ],
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "correct_definition": "副詞，表示做某事不費力氣或時間很短。",
    "options": [
      "副詞，表示做某事不費力氣或時間很短。",
      "指在工廠、企業等單位中從事體力或技術勞動、以工資收入為主要生活來源的人。",
      "指流動的空氣，即氣流。",
      "風的大小或強度，通常用等級表示。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "direct trade",
        "to lighten",
        "副词，表示做某事不费力气或时间很短。",
        "歌う"
      ],
      "correct_answer": "副词，表示做某事不费力气或时间很短。"
    }
  },
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "direct trade",
          "to lighten",
          "副詞，表示做某事不費力氣或時間很短。",
          "歌う"
        ],
        "correct_answer": "副詞，表示做某事不費力氣或時間很短。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10104, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "correct_definition": "表示做某事不费力气或时间很短",
  "options": [
    "指具有历史价值或学术价值的文字资料，如书籍、文章、档案等。",
    "表示做某事不费力气或时间很短",
    "朝着前方行进。",
    "瓶子是口小腹大的容器，通常用于盛放液体。"
  ],
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "correct_definition": "表示做某事不費力氣或時間很短",
    "options": [
      "指具有歷史價值或學術價值的文字資料，如書籍、文章、檔案等。",
      "表示做某事不費力氣或時間很短",
      "朝著前方行進。",
      "瓶子是口小腹大的容器，通常用於盛放液體。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "粘性；のりのように指にくっつく度合い",
        "希少資源；みんなに行き渡らないほど少ない有用なもの",
        "表示做某事不费力气或时间很短",
        "hometown"
      ],
      "correct_answer": "表示做某事不费力气或时间很短"
    }
  },
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "粘性；のりのように指にくっつく度合い",
          "希少資源；みんなに行き渡らないほど少ない有用なもの",
          "表示做某事不費力氣或時間很短",
          "hometown"
        ],
        "correct_answer": "表示做某事不費力氣或時間很短"
      }
    }
  }
}
```

---

## sense 10104, level 4

#### Pack A
### Level 4 (sense 10104, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "我一看___知道他的心情。",
  "original_sentence": "我一看便知道他的心情。",
  "target_word": "便",
  "word": "便",
  "answer": {
    "accepted": [
      "便",
      "方便",
      "随便",
      "便捷",
      "便利"
    ],
    "accepted_normalized": [
      "便",
      "方便",
      "随便",
      "便捷",
      "便利"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "我一看___知道他的心情。",
    "original_sentence": "我一看便知道他的心情。",
    "target_word": "便",
    "word": "便",
    "answer": {
      "accepted": [
        "便",
        "方便",
        "隨便",
        "便捷",
        "便利"
      ],
      "accepted_normalized": [
        "便",
        "方便",
        "隨便",
        "便捷",
        "便利"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这首古诗他读两遍___会。",
  "original_sentence": "这首古诗他读两遍便会。",
  "target_word": "便",
  "word": "便",
  "answer": {
    "accepted": [
      "便",
      "方便",
      "随便",
      "便捷",
      "便利"
    ],
    "accepted_normalized": [
      "便",
      "方便",
      "随便",
      "便捷",
      "便利"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這首古詩他讀兩遍___會。",
    "original_sentence": "這首古詩他讀兩遍便會。",
    "target_word": "便",
    "word": "便",
    "answer": {
      "accepted": [
        "便",
        "方便",
        "隨便",
        "便捷",
        "便利"
      ],
      "accepted_normalized": [
        "便",
        "方便",
        "隨便",
        "便捷",
        "便利"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

#### Pack B
### Level 4 (sense 10104, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "他轻轻一跳，___过了那条小河。",
  "original_sentence": "他轻轻一跳，便过了那条小河。",
  "target_word": "便",
  "word": "便",
  "answer": {
    "accepted": [
      "便",
      "就",
      "即"
    ],
    "accepted_normalized": [
      "便",
      "就",
      "即"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "他輕輕一跳，___過了那條小河。",
    "original_sentence": "他輕輕一跳，便過了那條小河。",
    "target_word": "便",
    "word": "便",
    "answer": {
      "accepted": [
        "便",
        "就",
        "即"
      ],
      "accepted_normalized": [
        "便",
        "就",
        "即"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "听到这个消息，她脸上___露出了笑容。",
  "original_sentence": "听到这个消息，她脸上便露出了笑容。",
  "target_word": "便",
  "word": "便",
  "answer": {
    "accepted": [
      "便",
      "就",
      "即"
    ],
    "accepted_normalized": [
      "便",
      "就",
      "即"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "聽到這個訊息，她臉上___露出了笑容。",
    "original_sentence": "聽到這個訊息，她臉上便露出了笑容。",
    "target_word": "便",
    "word": "便",
    "answer": {
      "accepted": [
        "便",
        "就",
        "即"
      ],
      "accepted_normalized": [
        "便",
        "就",
        "即"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

---

## sense 10104, level 6

#### Pack A
### Level 6 (sense 10104, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师一讲我便明白下去了。",
      "is_correct": false
    },
    {
      "text": "老师一讲我便明白了。",
      "is_correct": true
    },
    {
      "text": "老师一讲我便明白着。",
      "is_correct": false
    },
    {
      "text": "昨天我便老师一讲明白了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“明白”表示认知状态的达成，不能用“着”表示动作持续，应使用“了”表示状态实现。 语序错误：副词“便”不能放在主语“老师”之前，且时间状语与主语位置错乱，破坏了句子的基本语序。 方向/结果补语误用：“下去”表示动作或状态的继续，而“一……便……”结构强调动作的即时达成，两者在语义上矛盾。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "老師一講我便明白下去了。",
        "is_correct": false
      },
      {
        "text": "老師一講我便明白了。",
        "is_correct": true
      },
      {
        "text": "老師一講我便明白著。",
        "is_correct": false
      },
      {
        "text": "昨天我便老師一講明白了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“明白”表示認知狀態的達成，不能用“著”表示動作持續，應使用“了”表示狀態實現。 語序錯誤：副詞“便”不能放在主語“老師”之前，且時間狀語與主語位置錯亂，破壞了句子的基本語序。 方向/結果補語誤用：“下去”表示動作或狀態的繼續，而“一……便……”結構強調動作的即時達成，兩者在語義上矛盾。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "才",
    "即",
    "就",
    "还"
  ],
  "correct_answer": "才",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示做某事不费力气或时间很短。",
      "explanation": "副词，表示事情发生得晚或经过较长时间，与目标词表示时间短、不费力构成反义"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "才",
      "即",
      "就",
      "還"
    ],
    "correct_answer": "才",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示做某事不費力氣或時間很短。",
        "explanation": "副詞，表示事情發生得晚或經過較長時間，與目標詞表示時間短、不費力構成反義"
      }
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "便大家讨论完有了好观点。",
      "is_correct": false
    },
    {
      "text": "大家讨论完便有了好观点。",
      "is_correct": true
    },
    {
      "text": "大家讨论完便有着好观点。",
      "is_correct": false
    },
    {
      "text": "大家讨论完便有了过好观点。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：副词“便”不能放在主语“大家”之前，应放在主语之后、谓语之前。 体标位置错误：动态助词“过”应放在动词“有”之后，不能放在“了”之后，此处直接用“了”表示完成即可。 体标选用错误：“着”表示动作持续或状态保持，与前面的“完”及结果“有”相矛盾，应使用“了”。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "便大家討論完有了好觀點。",
        "is_correct": false
      },
      {
        "text": "大家討論完便有了好觀點。",
        "is_correct": true
      },
      {
        "text": "大家討論完便有著好觀點。",
        "is_correct": false
      },
      {
        "text": "大家討論完便有了過好觀點。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：副詞“便”不能放在主語“大家”之前，應放在主語之後、謂語之前。 體標位置錯誤：動態助詞“過”應放在動詞“有”之後，不能放在“了”之後，此處直接用“了”表示完成即可。 體標選用錯誤：“著”表示動作持續或狀態保持，與前面的“完”及結果“有”相矛盾，應使用“了”。",
    "target_word": "便"
  }
}
```

#### Pack B
### Level 6 (sense 10104, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师一解释，大家便明白意思了得。",
      "is_correct": false
    },
    {
      "text": "老师一解释，大家便正在明白意思。",
      "is_correct": false
    },
    {
      "text": "老师一解释，大家便往明白意思。",
      "is_correct": false
    },
    {
      "text": "老师一解释，大家便明白了意思。",
      "is_correct": true
    }
  ],
  "explanation": "语法错误。'了得'通常用于否定句或疑问句末尾表示程度深（如'非同小可'），或作为动词短语，不能直接跟在'明白'后作补语来表示完成，应改为'明白了'。 体貌错误。'便'表示动作迅速完成或紧接着发生，具有瞬时性或完成性，与表示进行体的'正在'矛盾。 语序/介词错误。'往'是介词，指向方向，不能直接修饰心理动词'明白'，且破坏了'便+动词'的副词结构。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "老師一解釋，大家便明白意思了得。",
        "is_correct": false
      },
      {
        "text": "老師一解釋，大家便正在明白意思。",
        "is_correct": false
      },
      {
        "text": "老師一解釋，大家便往明白意思。",
        "is_correct": false
      },
      {
        "text": "老師一解釋，大家便明白了意思。",
        "is_correct": true
      }
    ],
    "explanation": "語法錯誤。'了得'通常用於否定句或疑問句末尾表示程度深（如'非同小可'），或作為動詞短語，不能直接跟在'明白'後作補語來表示完成，應改為'明白了'。 體貌錯誤。'便'表示動作迅速完成或緊接著發生，具有瞬時性或完成性，與表示進行體的'正在'矛盾。 語序/介詞錯誤。'往'是介詞，指向方向，不能直接修飾心理動詞'明白'，且破壞了'便+動詞'的副詞結構。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "synonym",
  "options": [
    "才",
    "就",
    "难",
    "慢"
  ],
  "correct_answer": "就",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短",
      "explanation": "正确。'就'是该义项下最常见的近义词，都表示动作发生得快或容易。"
    }
  },
  "hant": {
    "word": "便",
    "relation": "synonym",
    "options": [
      "才",
      "就",
      "難",
      "慢"
    ],
    "correct_answer": "就",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短",
        "explanation": "正確。'就'是該義項下最常見的近義詞，都表示動作發生得快或容易。"
      }
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "门没锁，推一下便进去得过。",
      "is_correct": false
    },
    {
      "text": "门没锁，推一下便向进去。",
      "is_correct": false
    },
    {
      "text": "门没锁，推一下便进去了。",
      "is_correct": true
    },
    {
      "text": "门没锁，推一下便着进去。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误。'得过'不是标准的完成体标记，且'进去'后不应接'得过'，应直接用'了'。 体貌/语序错误。'着'表示进行或状态持续，不能放在趋向动词'进去'之前修饰'便'后的瞬间动作，且语序混乱。 介词错误。'向'是介词，不能直接作状语修饰'进去'而不带宾语，且破坏了副词'便'直接修饰动词的结构。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "門沒鎖，推一下便進去得過。",
        "is_correct": false
      },
      {
        "text": "門沒鎖，推一下便向進去。",
        "is_correct": false
      },
      {
        "text": "門沒鎖，推一下便進去了。",
        "is_correct": true
      },
      {
        "text": "門沒鎖，推一下便著進去。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤。'得過'不是標準的完成體標記，且'進去'後不應接'得過'，應直接用'了'。 體貌/語序錯誤。'著'表示進行或狀態持續，不能放在趨向動詞'進去'之前修飾'便'後的瞬間動作，且語序混亂。 介詞錯誤。'向'是介詞，不能直接作狀語修飾'進去'而不帶賓語，且破壞了副詞'便'直接修飾動詞的結構。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "便",
  "relation": "synonym",
  "options": [
    "就",
    "慢",
    "才",
    "难"
  ],
  "correct_answer": "就",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短",
      "explanation": "正确。'就'是该义项下最常见的近义词。"
    }
  },
  "hant": {
    "word": "便",
    "relation": "synonym",
    "options": [
      "就",
      "慢",
      "才",
      "難"
    ],
    "correct_answer": "就",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短",
        "explanation": "正確。'就'是該義項下最常見的近義詞。"
      }
    }
  }
}
```

---

## sense 10104, level 7

#### Pack A
### Level 7 (sense 10104, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "门没锁，推一下便进去了。",
      "is_correct": true
    },
    {
      "text": "门没锁，推一下便进去里了。",
      "is_correct": false,
      "error_description": "错误句中'进去里了'结构混乱。'进去'是趋向补语，后面直接加'了'表示完成。'里'是方位词，不能插在趋向动词和时态助词之间，也不能说'进去里'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "門沒鎖，推一下便進去了。",
        "is_correct": true
      },
      {
        "text": "門沒鎖，推一下便進去裡了。",
        "is_correct": false,
        "error_description": "錯誤句中'進去裡了'結構混亂。'進去'是趨向補語，後面直接加'了'表示完成。'裡'是方位詞，不能插在趨向動詞和時態助詞之間，也不能說'進去裡'。"
      }
    ]
  }
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "雨刚停，太阳便从云里出来了。",
      "is_correct": true
    },
    {
      "text": "雨刚停，太阳便从云里出来上去。",
      "is_correct": false,
      "error_description": "错误句中'出来上去'趋向补语堆砌且逻辑矛盾。'出来'已包含方向，'上去'指向上移动，两者连用不符合汉语习惯，且原句仅需'出来了'表示出现。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "雨剛停，太陽便從雲裡出來了。",
        "is_correct": true
      },
      {
        "text": "雨剛停，太陽便從雲裡出來上去。",
        "is_correct": false,
        "error_description": "錯誤句中'出來上去'趨向補語堆砌且邏輯矛盾。'出來'已包含方向，'上去'指向上移動，兩者連用不符合漢語習慣，且原句僅需'出來了'表示出現。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10104, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他一学便了会这道题。",
      "is_correct": false,
      "error_description": "“便”是副词，修饰动词“会”，“了”是动态助词，应放在动词或结果补语之后。此处“了”误放在“便”和“会”之间，正确写法为“便会了”。"
    },
    {
      "text": "我一看便知道他的心情。",
      "is_correct": true
    },
    {
      "text": "他一学便会了这道题。",
      "is_correct": true
    },
    {
      "text": "我们一见面便聊得很开心。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他一學便了會這道題。",
        "is_correct": false,
        "error_description": "“便”是副詞，修飾動詞“會”，“了”是動態助詞，應放在動詞或結果補語之後。此處“了”誤放在“便”和“會”之間，正確寫法為“便會了”。"
      },
      {
        "text": "我一看便知道他的心情。",
        "is_correct": true
      },
      {
        "text": "他一學便會了這道題。",
        "is_correct": true
      },
      {
        "text": "我們一見面便聊得很開心。",
        "is_correct": true
      }
    ]
  }
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这首古诗他读两遍便会。",
      "is_correct": true
    },
    {
      "text": "我把心事一说便轻松了。",
      "is_correct": true
    },
    {
      "text": "把作业一写他便去打球了。",
      "is_correct": false,
      "error_description": "“把”字句语序错误。“把”字及其宾语必须放在主语之后、谓语动词之前，不能放在主语之前。"
    },
    {
      "text": "大家讨论完便有了好观点。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這首古詩他讀兩遍便會。",
        "is_correct": true
      },
      {
        "text": "我把心事一說便輕鬆了。",
        "is_correct": true
      },
      {
        "text": "把作業一寫他便去打球了。",
        "is_correct": false,
        "error_description": "“把”字句語序錯誤。“把”字及其賓語必須放在主語之後、謂語動詞之前，不能放在主語之前。"
      },
      {
        "text": "大家討論完便有了好觀點。",
        "is_correct": true
      }
    ]
  }
}
```

---
