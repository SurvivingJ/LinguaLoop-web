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


## sense 10110, level 1

#### Pack A
### Level 1 (sense 10110, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "可",
  "options": [
    "kē",
    "kè",
    "kě",
    "ké"
  ],
  "correct_answer": "kě",
  "word": "可",
  "direction": "hanzi_to_pinyin",
  "context_sentence": "这种材料可回收利用，非常环保。",
  "context_target": "可",
  "is_polyphonic": true,
  "hant": {
    "schema_version": 2,
    "prompt": "可",
    "options": [
      "kē",
      "kè",
      "kě",
      "ké"
    ],
    "correct_answer": "kě",
    "word": "可",
    "direction": "hanzi_to_pinyin",
    "context_sentence": "這種材料可回收利用，非常環保。",
    "context_target": "可",
    "is_polyphonic": true
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "kě",
  "options": [
    "河",
    "可",
    "灯",
    "打"
  ],
  "correct_answer": "可",
  "word": "可",
  "direction": "pinyin_to_hanzi",
  "context_sentence": "这种材料可回收利用，非常环保。",
  "context_target": "可",
  "is_polyphonic": true,
  "distractor_sources": {
    "打": "component",
    "河": "component",
    "灯": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "kě",
    "options": [
      "河",
      "可",
      "燈",
      "打"
    ],
    "correct_answer": "可",
    "word": "可",
    "direction": "pinyin_to_hanzi",
    "context_sentence": "這種材料可回收利用，非常環保。",
    "context_target": "可",
    "is_polyphonic": true,
    "distractor_sources": {
      "打": "component",
      "河": "component",
      "灯": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "可",
  "toneless_pinyin": "ke",
  "full_pinyin": "kě",
  "options": [
    "3",
    "4",
    "2",
    "1"
  ],
  "correct_answer": "3",
  "option_labels": {
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)",
    "1": "high level (1)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "可",
    "toneless_pinyin": "ke",
    "full_pinyin": "kě",
    "options": [
      "3",
      "4",
      "2",
      "1"
    ],
    "correct_answer": "3",
    "option_labels": {
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)",
      "1": "high level (1)"
    },
    "syllable_count": 1
  }
}
```

#### Pack B
### Level 1 (sense 10110, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "可",
  "options": [
    "kē",
    "kè",
    "kě",
    "ké"
  ],
  "correct_answer": "kě",
  "word": "可",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "可",
    "options": [
      "kē",
      "kè",
      "kě",
      "ké"
    ],
    "correct_answer": "kě",
    "word": "可",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "ipa": "[kʰɤ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "科",
    "客",
    "壳",
    "可"
  ],
  "correct_answer": "可",
  "explanation": "正确：'可'读第三声（kě），表示许可或可能，符合听到的语音。",
  "distractor_explanations": {
    "科": "声调错误：'科'读第一声（kē），指学科或类别，与目标词'可'（kě）声调不同，意义完全不同。",
    "壳": "声调错误：'壳'读第二声（ké），指坚硬的外皮，与目标词'可'（kě）声调不同，意义完全不同。",
    "客": "声调错误：'客'读第四声（kè），指客人，与目标词'可'（kě）声调不同，意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "ipa": "[kʰɤ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "科",
      "客",
      "殼",
      "可"
    ],
    "correct_answer": "可",
    "explanation": "正確：'可'讀第三聲（kě），表示許可或可能，符合聽到的語音。",
    "distractor_explanations": {
      "科": "聲調錯誤：'科'讀第一聲（kē），指學科或類別，與目標詞'可'（kě）聲調不同，意義完全不同。",
      "壳": "聲調錯誤：'殼'讀第二聲（ké），指堅硬的外皮，與目標詞'可'（kě）聲調不同，意義完全不同。",
      "客": "聲調錯誤：'客'讀第四聲（kè），指客人，與目標詞'可'（kě）聲調不同，意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "kě",
  "options": [
    "河",
    "可",
    "灯",
    "打"
  ],
  "correct_answer": "可",
  "word": "可",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "打": "component",
    "河": "component",
    "灯": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "kě",
    "options": [
      "河",
      "可",
      "燈",
      "打"
    ],
    "correct_answer": "可",
    "word": "可",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "打": "component",
      "河": "component",
      "灯": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "可",
  "toneless_pinyin": "ke",
  "full_pinyin": "kě",
  "options": [
    "3",
    "4",
    "2",
    "1"
  ],
  "correct_answer": "3",
  "option_labels": {
    "3": "dipping (3)",
    "4": "falling (4)",
    "2": "rising (2)",
    "1": "high level (1)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "可",
    "toneless_pinyin": "ke",
    "full_pinyin": "kě",
    "options": [
      "3",
      "4",
      "2",
      "1"
    ],
    "correct_answer": "3",
    "option_labels": {
      "3": "dipping (3)",
      "4": "falling (4)",
      "2": "rising (2)",
      "1": "high level (1)"
    },
    "syllable_count": 1
  }
}
```

---

## sense 10110, level 2

#### Pack A
### Level 2 (sense 10110, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "correct_definition": "表示许可或可能，常用于口语。",
  "options": [
    "有价值的物品和金钱的总和。",
    "表示许可或可能，常用于口语。",
    "人和动物体内负责传递信息和指令的组织，由许多神经细胞组成；也指精神状态不正常。",
    "指完成某项活动或任务所具备的才能、本领。"
  ],
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "correct_definition": "表示許可或可能，常用於口語。",
    "options": [
      "有價值的物品和金錢的總和。",
      "表示許可或可能，常用於口語。",
      "人和動物體內負責傳遞資訊和指令的組織，由許多神經細胞組成；也指精神狀態不正常。",
      "指完成某項活動或任務所具備的才能、本領。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "崩壊する",
        "競争相手；あなたと競い合う人",
        "水从一处流向另一处。",
        "表示许可或可能，常用于口语。"
      ],
      "correct_answer": "表示许可或可能，常用于口语。"
    }
  },
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "崩壊する",
          "競爭相手；あなたと競い合う人",
          "水從一處流向另一處。",
          "表示許可或可能，常用於口語。"
        ],
        "correct_answer": "表示許可或可能，常用於口語。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10110, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "correct_definition": "表示许可或可能，常用于口语。",
  "options": [
    "土壤中水分的含量，通常用百分比表示。",
    "仔细地看，检查评估。",
    "明确承认或肯定某事，表示同意或认定。",
    "表示许可或可能，常用于口语。"
  ],
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "correct_definition": "表示許可或可能，常用於口語。",
    "options": [
      "土壤中水分的含量，通常用百分比表示。",
      "仔細地看，檢查評估。",
      "明確承認或肯定某事，表示同意或認定。",
      "表示許可或可能，常用於口語。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "decarbonization; reducing the amount of carbon something releases",
        "指一个团队或组织的负责人，负责指挥和协调。",
        "一个人或一件事限制住另一个人或事，不让它随便动。",
        "表示许可或可能，常用于口语。"
      ],
      "correct_answer": "表示许可或可能，常用于口语。"
    }
  },
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "decarbonization; reducing the amount of carbon something releases",
          "指一個團隊或組織的負責人，負責指揮和協調。",
          "一個人或一件事限制住另一個人或事，不讓它隨便動。",
          "表示許可或可能，常用於口語。"
        ],
        "correct_answer": "表示許可或可能，常用於口語。"
      }
    }
  }
}
```

---

## sense 10110, level 6

#### Pack A
### Level 6 (sense 10110, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这水烧开着可直接喝。",
      "is_correct": false
    },
    {
      "text": "这水烧开后可直接喝出来。",
      "is_correct": false
    },
    {
      "text": "这水烧开后可直接喝。",
      "is_correct": true
    },
    {
      "text": "这水可直接喝烧开后。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：条件状语'烧开后'应放在情态动词'可'之前，说明在什么条件下可以喝，不能放在句末。 体标选用错误：'烧开'是瞬间完成动词，不能用表示状态持续的'着'，应改为'烧开后'或'烧开了'。 方向补语误用：'喝'的动作方向是进入体内，应使用'喝下去'或直接说'喝'，不能使用表示由内向外的'出来'。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "這水燒開著可直接喝。",
        "is_correct": false
      },
      {
        "text": "這水燒開後可直接喝出來。",
        "is_correct": false
      },
      {
        "text": "這水燒開後可直接喝。",
        "is_correct": true
      },
      {
        "text": "這水可直接喝燒開後。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：條件狀語'燒開後'應放在情態動詞'可'之前，說明在什麼條件下可以喝，不能放在句末。 體標選用錯誤：'燒開'是瞬間完成動詞，不能用表示狀態持續的'著'，應改為'燒開後'或'燒開了'。 方向補語誤用：'喝'的動作方向是進入體內，應使用'喝下去'或直接說'喝'，不能使用表示由內向外的'出來'。",
    "target_word": "可"
  }
}
```

#### Pack B
### Level 6 (sense 10110, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "你可以把这本书借给看我吗？",
      "is_correct": false
    },
    {
      "text": "你可把这本书借给我看吗？以",
      "is_correct": false
    },
    {
      "text": "你可以把这本书借给我看吗？",
      "is_correct": true
    },
    {
      "text": "你可以把这本书我看借给吗？",
      "is_correct": false
    }
  ],
  "explanation": "语序/结构错误。‘以’字多余且位置错误，破坏了‘可以’的完整性或句法结构。 语序错误。双宾语结构中，间接宾语‘我’应紧跟动词‘借给’或直接宾语前，通常说‘借给我’，‘借给看我’语序混乱。 语序严重错误。动词短语内部成分完全乱序。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "你可以把這本書借給看我嗎？",
        "is_correct": false
      },
      {
        "text": "你可把這本書借給我看嗎？以",
        "is_correct": false
      },
      {
        "text": "你可以把這本書借給我看嗎？",
        "is_correct": true
      },
      {
        "text": "你可以把這本書我看借給嗎？",
        "is_correct": false
      }
    ],
    "explanation": "語序/結構錯誤。‘以’字多餘且位置錯誤，破壞了‘可以’的完整性或句法結構。 語序錯誤。雙賓語結構中，間接賓語‘我’應緊跟動詞‘借給’或直接賓語前，通常說‘借給我’，‘借給看我’語序混亂。 語序嚴重錯誤。動詞短語內部成分完全亂序。",
    "target_word": "可"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这件事你可别告诉别人。",
      "is_correct": true
    },
    {
      "text": "这件事你可告诉别人别。",
      "is_correct": false
    },
    {
      "text": "这件事你可告诉别别人。",
      "is_correct": false
    },
    {
      "text": "这件事你别可告诉别人。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。否定词‘别’不应放在强调标记‘可’之前，应为‘可别’。 量词/重叠错误。‘别人’不应重叠为‘别别人’，且语意不通。 语序错误。否定副词‘别’置于句末不符合汉语语法规范。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "這件事你可別告訴別人。",
        "is_correct": true
      },
      {
        "text": "這件事你可告訴別人別。",
        "is_correct": false
      },
      {
        "text": "這件事你可告訴別別人。",
        "is_correct": false
      },
      {
        "text": "這件事你別可告訴別人。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。否定詞‘別’不應放在強調標記‘可’之前，應為‘可別’。 量詞/重疊錯誤。‘別人’不應重疊為‘別別人’，且語意不通。 語序錯誤。否定副詞‘別’置於句末不符合漢語語法規範。",
    "target_word": "可"
  }
}
```

---

## sense 10110, level 9

#### Pack A
### Level 9 (sense 10110, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "你可得小心点，别摔着了。",
  "hant": {
    "original_sentence": "你可得小心點，別摔著了。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "你可以把这本书借给我看吗？",
  "hant": {
    "original_sentence": "你可以把這本書借給我看嗎？"
  }
}
```

#### Pack B
### Level 9 (sense 10110, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "周末我们可去公园，也可在家。",
  "hant": {
    "original_sentence": "週末我們可去公園，也可在家。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这水烧开后可直接喝。",
  "hant": {
    "original_sentence": "這水燒開後可直接喝。"
  }
}
```

---

## sense 10111, level 1

#### Pack A
### Level 1 (sense 10111, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "重复",
  "options": [
    "chóng fù",
    "chóng fū",
    "chōng fù",
    "chóng fú"
  ],
  "correct_answer": "chóng fù",
  "word": "重复",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "重複",
    "options": [
      "chóng fù",
      "chóng fū",
      "chōng fù",
      "chóng fú"
    ],
    "correct_answer": "chóng fù",
    "word": "重複",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "chóng fù",
  "options": [
    "重量",
    "重复",
    "处理",
    "设备"
  ],
  "correct_answer": "重复",
  "word": "重复",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "重量": "component",
    "处理": "component",
    "设备": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "chóng fù",
    "options": [
      "重量",
      "重複",
      "處理",
      "裝置"
    ],
    "correct_answer": "重複",
    "word": "重複",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "重量": "component",
      "处理": "component",
      "设备": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "重复",
  "toneless_pinyin": "chong fu",
  "full_pinyin": "chóng fù",
  "options": [
    "24",
    "22",
    "23",
    "21"
  ],
  "correct_answer": "24",
  "option_labels": {
    "24": "rising (2) + falling (4)",
    "22": "rising (2) + rising (2)",
    "23": "rising (2) + dipping (3)",
    "21": "rising (2) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "重複",
    "toneless_pinyin": "chong fu",
    "full_pinyin": "chóng fù",
    "options": [
      "24",
      "22",
      "23",
      "21"
    ],
    "correct_answer": "24",
    "option_labels": {
      "24": "rising (2) + falling (4)",
      "22": "rising (2) + rising (2)",
      "23": "rising (2) + dipping (3)",
      "21": "rising (2) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10111, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "重复",
  "options": [
    "chóng fù",
    "chóng fū",
    "chōng fù",
    "chóng fú"
  ],
  "correct_answer": "chóng fù",
  "word": "重复",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "重複",
    "options": [
      "chóng fù",
      "chóng fū",
      "chōng fù",
      "chóng fú"
    ],
    "correct_answer": "chóng fù",
    "word": "重複",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "chóng fù",
  "options": [
    "重量",
    "重复",
    "处理",
    "设备"
  ],
  "correct_answer": "重复",
  "word": "重复",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "重量": "component",
    "处理": "component",
    "设备": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "chóng fù",
    "options": [
      "重量",
      "重複",
      "處理",
      "裝置"
    ],
    "correct_answer": "重複",
    "word": "重複",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "重量": "component",
      "处理": "component",
      "设备": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "重复",
  "toneless_pinyin": "chong fu",
  "full_pinyin": "chóng fù",
  "options": [
    "24",
    "22",
    "23",
    "21"
  ],
  "correct_answer": "24",
  "option_labels": {
    "24": "rising (2) + falling (4)",
    "22": "rising (2) + rising (2)",
    "23": "rising (2) + dipping (3)",
    "21": "rising (2) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "重複",
    "toneless_pinyin": "chong fu",
    "full_pinyin": "chóng fù",
    "options": [
      "24",
      "22",
      "23",
      "21"
    ],
    "correct_answer": "24",
    "option_labels": {
      "24": "rising (2) + falling (4)",
      "22": "rising (2) + rising (2)",
      "23": "rising (2) + dipping (3)",
      "21": "rising (2) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

---

## sense 10111, level 2

#### Pack A
### Level 2 (sense 10111, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "pronunciation": "chóng fù",
  "correct_definition": "表示某个动作或情况再次出现或进行第二次。",
  "options": [
    "得到好处；获得利益。",
    "将信息、意见或结果等传递回来。",
    "时间表是用来规划和记录各项活动或任务在特定时间进行的表格或清单。",
    "表示某个动作或情况再次出现或进行第二次。"
  ],
  "hant": {
    "word": "重複",
    "pronunciation": "chóng fù",
    "correct_definition": "表示某個動作或情況再次出現或進行第二次。",
    "options": [
      "得到好處；獲得利益。",
      "將資訊、意見或結果等傳遞回來。",
      "時間表是用來規劃和記錄各項活動或任務在特定時間進行的表格或清單。",
      "表示某個動作或情況再次出現或進行第二次。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "pronunciation": "chóng fù",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "指程度浅、不严重。",
        "ライダー；レーザー光で距離を測り、車の目のように周りを見えるようにする機械",
        "表示某个动作或情况再次出现或进行第二次。",
        "doll; a toy shaped like a little person"
      ],
      "correct_answer": "表示某个动作或情况再次出现或进行第二次。"
    }
  },
  "hant": {
    "word": "重複",
    "pronunciation": "chóng fù",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "指程度淺、不嚴重。",
          "ライダー；レーザー光で距離を測り、車の目のように周りを見えるようにする機械",
          "表示某個動作或情況再次出現或進行第二次。",
          "doll; a toy shaped like a little person"
        ],
        "correct_answer": "表示某個動作或情況再次出現或進行第二次。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10111, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "pronunciation": "chóng fù",
  "correct_definition": "表示某个动作或情况再次出现或进行第二次。",
  "options": [
    "一种由脑垂体分泌的激素，能促进子宫收缩、帮助分娩，并促进亲子关系。",
    "为了了解某事物的效果或性能而进行尝试或操作。",
    "指有血缘关系或婚姻关系的一群人，通常包括父母、子女和其他亲属。",
    "表示某个动作或情况再次出现或进行第二次。"
  ],
  "hant": {
    "word": "重複",
    "pronunciation": "chóng fù",
    "correct_definition": "表示某個動作或情況再次出現或進行第二次。",
    "options": [
      "一種由腦垂體分泌的激素，能促進子宮收縮、幫助分娩，並促進親子關係。",
      "為了瞭解某事物的效果或效能而進行嘗試或操作。",
      "指有血緣關係或婚姻關係的一群人，通常包括父母、子女和其他親屬。",
      "表示某個動作或情況再次出現或進行第二次。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "pronunciation": "chóng fù",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "把要做的事情想好顺序，一件一件做好。",
        "to let go",
        "表示某个动作或情况再次出现或进行第二次。",
        "符号学是研究记号怎么表达意思的学问。"
      ],
      "correct_answer": "表示某个动作或情况再次出现或进行第二次。"
    }
  },
  "hant": {
    "word": "重複",
    "pronunciation": "chóng fù",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "把要做的事情想好順序，一件一件做好。",
          "to let go",
          "表示某個動作或情況再次出現或進行第二次。",
          "符號學是研究記號怎麼表達意思的學問。"
        ],
        "correct_answer": "表示某個動作或情況再次出現或進行第二次。"
      }
    }
  }
}
```

---

## sense 10111, level 3

#### Pack A
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "这个实验步骤需要___三次，以确保数据的准确性。",
  "original_sentence": "这个实验步骤需要重复三次，以确保数据的准确性。",
  "correct_answer": "重复",
  "options": [
    "模仿",
    "继续",
    "复习",
    "重复"
  ],
  "explanation": "正确。语境为实验步骤再次进行，符合‘动作再次出现’的释义。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "這個實驗步驟需要___三次，以確保資料的準確性。",
    "original_sentence": "這個實驗步驟需要重複三次，以確保資料的準確性。",
    "correct_answer": "重複",
    "options": [
      "模仿",
      "繼續",
      "複習",
      "重複"
    ],
    "explanation": "正確。語境為實驗步驟再次進行，符合‘動作再次出現’的釋義。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```

#### Pack B
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "它的设计像一个绿色的箭头圆圈，表示废物可以被___利用。",
  "original_sentence": "它的设计像一个绿色的箭头圆圈，表示废物可以被重复利用。",
  "correct_answer": "重复",
  "options": [
    "破坏",
    "消耗",
    "施展",
    "重复"
  ],
  "explanation": "“重复”在此处表示再次利用，符合废物管理的环保语境与搭配习惯。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被___利用。",
    "original_sentence": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被重複利用。",
    "correct_answer": "重複",
    "options": [
      "破壞",
      "消耗",
      "施展",
      "重複"
    ],
    "explanation": "“重複”在此處表示再次利用，符合廢物管理的環保語境與搭配習慣。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我不喜欢这种___的游戏。",
  "original_sentence": "我不喜欢这种重复的游戏。",
  "correct_answer": "重复",
  "options": [
    "昂贵",
    "重复",
    "打破",
    "复杂"
  ],
  "explanation": "正确选项，表示动作或情况再次出现，符合句意。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "我不喜歡這種___的遊戲。",
    "original_sentence": "我不喜歡這種重複的遊戲。",
    "correct_answer": "重複",
    "options": [
      "昂貴",
      "重複",
      "打破",
      "複雜"
    ],
    "explanation": "正確選項，表示動作或情況再次出現，符合句意。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```

---

## sense 10111, level 4

#### Pack A
### Level 4 (sense 10111, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这个标志的三个箭头代表废物管理的三个步骤：减少使用、___利用、回收处理。",
  "original_sentence": "这个标志的三个箭头代表废物管理的三个步骤：减少使用、重复利用、回收处理。",
  "target_word": "重复",
  "word": "重复",
  "answer": {
    "accepted": [
      "重复",
      "重复了",
      "重复过",
      "重复率"
    ],
    "accepted_normalized": [
      "重复",
      "重复了",
      "重复过",
      "重复率"
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
    "sentence_with_blank": "這個標誌的三個箭頭代表廢物管理的三個步驟：減少使用、___利用、回收處理。",
    "original_sentence": "這個標誌的三個箭頭代表廢物管理的三個步驟：減少使用、重複利用、回收處理。",
    "target_word": "重複",
    "word": "重複",
    "answer": {
      "accepted": [
        "重複",
        "重複了",
        "重複過",
        "重複率"
      ],
      "accepted_normalized": [
        "重複",
        "重複了",
        "重複過",
        "重複率"
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
  "sentence_with_blank": "这个笑话他___过了。",
  "original_sentence": "这个笑话他重复过了。",
  "target_word": "重复",
  "word": "重复",
  "answer": {
    "accepted": [
      "重复",
      "重复了",
      "重复过",
      "重复率"
    ],
    "accepted_normalized": [
      "重复",
      "重复了",
      "重复过",
      "重复率"
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
    "sentence_with_blank": "這個笑話他___過了。",
    "original_sentence": "這個笑話他重複過了。",
    "target_word": "重複",
    "word": "重複",
    "answer": {
      "accepted": [
        "重複",
        "重複了",
        "重複過",
        "重複率"
      ],
      "accepted_normalized": [
        "重複",
        "重複了",
        "重複過",
        "重複率"
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
### Level 4 (sense 10111, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "为了避免遗漏重要信息，他决定把刚才的话再___一遍。",
  "original_sentence": "为了避免遗漏重要信息，他决定把刚才的话再重复一遍。",
  "target_word": "重复",
  "word": "重复",
  "answer": {
    "accepted": [
      "重复",
      "重复了",
      "重复过",
      "重复着",
      "複復"
    ],
    "accepted_normalized": [
      "重复",
      "重复了",
      "重复过",
      "重复着",
      "复复"
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
    "sentence_with_blank": "為了避免遺漏重要資訊，他決定把剛才的話再___一遍。",
    "original_sentence": "為了避免遺漏重要資訊，他決定把剛才的話再重複一遍。",
    "target_word": "重複",
    "word": "重複",
    "answer": {
      "accepted": [
        "重複",
        "重複了",
        "重複過",
        "重複著",
        "複復"
      ],
      "accepted_normalized": [
        "重複",
        "重複了",
        "重複過",
        "重複著",
        "複復"
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
  "sentence_with_blank": "为了记住单词，我___写了好几遍。",
  "original_sentence": "为了记住单词，我重复写了好几遍。",
  "target_word": "重复",
  "word": "重复",
  "answer": {
    "accepted": [
      "重复",
      "重复了",
      "重复过",
      "重复着",
      "複復"
    ],
    "accepted_normalized": [
      "重复",
      "重复了",
      "重复过",
      "重复着",
      "复复"
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
    "sentence_with_blank": "為了記住單詞，我___寫了好幾遍。",
    "original_sentence": "為了記住單詞，我重複寫了好幾遍。",
    "target_word": "重複",
    "word": "重複",
    "answer": {
      "accepted": [
        "重複",
        "重複了",
        "重複過",
        "重複著",
        "複復"
      ],
      "accepted_normalized": [
        "重複",
        "重複了",
        "重複過",
        "重複著",
        "複復"
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

## sense 10111, level 6

#### Pack A
### Level 6 (sense 10111, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "relation": "synonym",
  "options": [
    "首次",
    "创新",
    "停止",
    "再次"
  ],
  "correct_answer": "再次",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "近义词。‘再次’也表示第二次或又一次，与‘重复’在表示动作再现时语义相近。"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "synonym",
    "options": [
      "首次",
      "創新",
      "停止",
      "再次"
    ],
    "correct_answer": "再次",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "近義詞。‘再次’也表示第二次或又一次，與‘重複’在表示動作再現時語義相近。"
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
      "text": "历史有时候会重复过，我们要吸取教训。",
      "is_correct": false
    },
    {
      "text": "历史有时候会重复，我们要吸取教训。",
      "is_correct": true
    },
    {
      "text": "历史有时候重复在三十年前，我们要吸取教训。",
      "is_correct": false
    },
    {
      "text": "历史有时候会向上重复，我们要吸取教训。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误。‘会’表示将来或惯常，‘过’表示经历，二者在表示普遍真理或预测时搭配不当，应去掉‘过’或改为‘曾经重复过’。 趋向补语误用。‘重复’一般不带方向性趋向补语‘向上’，语义不通。 介词结构/语序错误。‘重复’后不能直接接‘在+时间’来表示发生时间，应说‘三十年前重复过’。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "歷史有時候會重複過，我們要吸取教訓。",
        "is_correct": false
      },
      {
        "text": "歷史有時候會重複，我們要吸取教訓。",
        "is_correct": true
      },
      {
        "text": "歷史有時候重複在三十年前，我們要吸取教訓。",
        "is_correct": false
      },
      {
        "text": "歷史有時候會向上重複，我們要吸取教訓。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤。‘會’表示將來或慣常，‘過’表示經歷，二者在表示普遍真理或預測時搭配不當，應去掉‘過’或改為‘曾經重複過’。 趨向補語誤用。‘重複’一般不帶方向性趨向補語‘向上’，語義不通。 介詞結構/語序錯誤。‘重複’後不能直接接‘在+時間’來表示發生時間，應說‘三十年前重複過’。",
    "target_word": "重複"
  }
}
```

#### Pack B
### Level 6 (sense 10111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复出排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了重复着排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了排版可重复的技术先河。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：此处需表示动作可再次发生的属性，应使用“可重复”，误用体标“着”表示动作持续，不符合语境。 语序错误：修饰语“可重复”应放在中心语“排版”之前，构成“可重复排版”，放在其后不符合汉语修饰习惯。 结果补语误用：“出”表示从无到有产生，与“重复”表示再次进行的语义冲突，不能搭配使用。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複出排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了重複著排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了排版可重複的技術先河。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：此處需表示動作可再次發生的屬性，應使用“可重複”，誤用體標“著”表示動作持續，不符合語境。 語序錯誤：修飾語“可重複”應放在中心語“排版”之前，構成“可重複排版”，放在其後不符合漢語修飾習慣。 結果補語誤用：“出”表示從無到有產生，與“重複”表示再次進行的語義衝突，不能搭配使用。",
    "target_word": "重複"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "请你把刚才的话重复起来一次。",
      "is_correct": false
    },
    {
      "text": "请你把刚才的话重复着了。",
      "is_correct": false
    },
    {
      "text": "请你把刚才的话重复一次。",
      "is_correct": true
    },
    {
      "text": "重复一次请你把刚才的话。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“重复”表示动作再次发生，不能用“着”表示动作持续，且“着了”连用不符合汉语体标记的语法规则。 语序错误。动词短语“重复一次”被放在了祈使词“请你”之前，破坏了正常的语序和“把”字句的基本结构。 方向/结果补语误用。“起来”表示动作开始或向上，而“重复”表示再次进行，两者语义不兼容，不能搭配使用。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "請你把剛才的話重複起來一次。",
        "is_correct": false
      },
      {
        "text": "請你把剛才的話重複著了。",
        "is_correct": false
      },
      {
        "text": "請你把剛才的話重複一次。",
        "is_correct": true
      },
      {
        "text": "重複一次請你把剛才的話。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“重複”表示動作再次發生，不能用“著”表示動作持續，且“著了”連用不符合漢語體標記的語法規則。 語序錯誤。動詞短語“重複一次”被放在了祈使詞“請你”之前，破壞了正常的語序和“把”字句的基本結構。 方向/結果補語誤用。“起來”表示動作開始或向上，而“重複”表示再次進行，兩者語義不相容，不能搭配使用。",
    "target_word": "重複"
  }
}
```

---

## sense 10111, level 9

#### Pack A
### Level 9 (sense 10111, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他重复着刚才说过的话，希望我们能听懂。",
  "hant": {
    "original_sentence": "他重複著剛才說過的話，希望我們能聽懂。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他重复着刚才说过的话，希望我们能听懂。",
  "chunks": [
    "他",
    "重复着刚才",
    "说过的话",
    "希望我们",
    "能听懂"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "能听懂",
    "希望我们",
    "重复着刚才",
    "说过的话",
    "他"
  ],
  "target_word": "重复",
  "chunk_count": 5,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他重複著剛才說過的話，希望我們能聽懂。",
    "chunks": [
      "他",
      "重複著剛才",
      "說過的話",
      "希望我們",
      "能聽懂"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3,
      4
    ],
    "shuffled_chunks": [
      "能聽懂",
      "希望我們",
      "重複著剛才",
      "說過的話",
      "他"
    ],
    "target_word": "重複",
    "chunk_count": 5
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这种错误的操作模式如果不断重复，最终会导致系统崩溃。",
  "hant": {
    "original_sentence": "這種錯誤的操作模式如果不斷重複，最終會導致系統崩潰。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这种错误的操作模式如果不断重复，最终会导致系统崩溃。",
  "chunks": [
    "这种错误的操作模式",
    "如果不断重复",
    "最终会导致系统",
    "崩溃"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "崩溃",
    "最终会导致系统",
    "如果不断重复",
    "这种错误的操作模式"
  ],
  "target_word": "重复",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這種錯誤的操作模式如果不斷重複，最終會導致系統崩潰。",
    "chunks": [
      "這種錯誤的操作模式",
      "如果不斷重複",
      "最終會導致系統",
      "崩潰"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "崩潰",
      "最終會導致系統",
      "如果不斷重複",
      "這種錯誤的操作模式"
    ],
    "target_word": "重複",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10111, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "她重复着那句感人的话。",
  "hant": {
    "original_sentence": "她重複著那句感人的話。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "她重复着那句感人的话。",
  "chunks": [
    "她重复",
    "着那句",
    "感人的话"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "着那句",
    "她重复",
    "感人的话"
  ],
  "target_word": "重复",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "她重複著那句感人的話。",
    "chunks": [
      "她重複",
      "著那句",
      "感人的話"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "著那句",
      "她重複",
      "感人的話"
    ],
    "target_word": "重複",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "hant": {
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "chunks": [
    "中国早",
    "在唐代",
    "便已广泛应用雕版印刷",
    "宋代",
    "毕昇更首创泥活字",
    "开启了可重复排版的技术先河"
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
    "在唐代",
    "毕昇更首创泥活字",
    "开启了可重复排版的技术先河",
    "便已广泛应用雕版印刷",
    "宋代",
    "中国早"
  ],
  "target_word": "重复",
  "chunk_count": 6,
  "hant": {
    "schema_version": 2,
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "chunks": [
      "中國早",
      "在唐代",
      "便已廣泛應用雕版印刷",
      "宋代",
      "畢昇更首創泥活字",
      "開啟了可重複排版的技術先河"
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
      "在唐代",
      "畢昇更首創泥活字",
      "開啟了可重複排版的技術先河",
      "便已廣泛應用雕版印刷",
      "宋代",
      "中國早"
    ],
    "target_word": "重複",
    "chunk_count": 6
  }
}
```

---
