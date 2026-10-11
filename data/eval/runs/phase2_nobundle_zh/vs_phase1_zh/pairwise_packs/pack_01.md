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


## sense 10300, level 1

#### Pack A
### Level 1 (sense 10300, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "长",
  "options": [
    "chāng",
    "chàng",
    "cháng",
    "chǎng"
  ],
  "correct_answer": "cháng",
  "word": "长",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "長",
    "options": [
      "chāng",
      "chàng",
      "cháng",
      "chǎng"
    ],
    "correct_answer": "cháng",
    "word": "長",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "ipa": "[ʈʂʰɑŋ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "长",
    "昌",
    "唱",
    "厂"
  ],
  "correct_answer": "长",
  "explanation": "“长”读二声，指空间或时间上距离大，符合听力材料的语义。",
  "distractor_explanations": {
    "厂": "“厂”读三声，指工厂，声调不同导致意义完全改变。",
    "唱": "“唱”读四声，指唱歌，声调不同导致意义完全改变。",
    "昌": "“昌”读一声，指兴旺，声调不同导致意义完全改变。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[ʈʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "長",
      "昌",
      "唱",
      "廠"
    ],
    "correct_answer": "長",
    "explanation": "“長”讀二聲，指空間或時間上距離大，符合聽力材料的語義。",
    "distractor_explanations": {
      "厂": "“廠”讀三聲，指工廠，聲調不同導致意義完全改變。",
      "唱": "“唱”讀四聲，指唱歌，聲調不同導致意義完全改變。",
      "昌": "“昌”讀一聲，指興旺，聲調不同導致意義完全改變。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "cháng",
  "options": [
    "长",
    "事",
    "比",
    "高"
  ],
  "correct_answer": "长",
  "word": "长",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "比": "frequency",
    "高": "frequency",
    "事": "frequency"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "cháng",
    "options": [
      "長",
      "事",
      "比",
      "高"
    ],
    "correct_answer": "長",
    "word": "長",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "比": "frequency",
      "高": "frequency",
      "事": "frequency"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "长",
  "toneless_pinyin": "chang",
  "full_pinyin": "cháng",
  "options": [
    "4",
    "3",
    "2",
    "1"
  ],
  "correct_answer": "2",
  "option_labels": {
    "4": "falling (4)",
    "3": "dipping (3)",
    "2": "rising (2)",
    "1": "high level (1)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "長",
    "toneless_pinyin": "chang",
    "full_pinyin": "cháng",
    "options": [
      "4",
      "3",
      "2",
      "1"
    ],
    "correct_answer": "2",
    "option_labels": {
      "4": "falling (4)",
      "3": "dipping (3)",
      "2": "rising (2)",
      "1": "high level (1)"
    },
    "syllable_count": 1
  }
}
```

#### Pack B
### Level 1 (sense 10300, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "长",
  "options": [
    "chāng",
    "chàng",
    "cháng",
    "chǎng"
  ],
  "correct_answer": "cháng",
  "word": "长",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "長",
    "options": [
      "chāng",
      "chàng",
      "cháng",
      "chǎng"
    ],
    "correct_answer": "cháng",
    "word": "長",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "cháng",
  "options": [
    "长",
    "快",
    "比",
    "高"
  ],
  "correct_answer": "长",
  "word": "长",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "比": "frequency",
    "高": "frequency",
    "快": "frequency"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "cháng",
    "options": [
      "長",
      "快",
      "比",
      "高"
    ],
    "correct_answer": "長",
    "word": "長",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "比": "frequency",
      "高": "frequency",
      "快": "frequency"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "长",
  "toneless_pinyin": "chang",
  "full_pinyin": "cháng",
  "options": [
    "4",
    "3",
    "2",
    "1"
  ],
  "correct_answer": "2",
  "option_labels": {
    "4": "falling (4)",
    "3": "dipping (3)",
    "2": "rising (2)",
    "1": "high level (1)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "長",
    "toneless_pinyin": "chang",
    "full_pinyin": "cháng",
    "options": [
      "4",
      "3",
      "2",
      "1"
    ],
    "correct_answer": "2",
    "option_labels": {
      "4": "falling (4)",
      "3": "dipping (3)",
      "2": "rising (2)",
      "1": "high level (1)"
    },
    "syllable_count": 1
  }
}
```

---

## sense 10300, level 2

#### Pack A
### Level 2 (sense 10300, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "correct_definition": "指空间或时间上距离大，与‘短’相对。",
  "options": [
    "一种描述流体速度与压力关系的物理原理",
    "指空间或时间上距离大，与‘短’相对。",
    "观察或思考某个问题的特定角度。",
    "选择并实施（某种方法、策略、措施等）。"
  ],
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "correct_definition": "指空間或時間上距離大，與‘短’相對。",
    "options": [
      "一種描述流體速度與壓力關係的物理原理",
      "指空間或時間上距離大，與‘短’相對。",
      "觀察或思考某個問題的特定角度。",
      "選擇並實施（某種方法、策略、措施等）。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ethnic group; people who share a language and customs",
        "指空间或时间上距离大，与‘短’相对。",
        "計器；実験や測定のために使う道具",
        "表示承接关系，相当于‘于是’、‘便’，用于连接前后两个动作或情况。"
      ],
      "correct_answer": "指空间或时间上距离大，与‘短’相对。"
    }
  },
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "ethnic group; people who share a language and customs",
          "指空間或時間上距離大，與‘短’相對。",
          "計器；実験や測定のために使う道具",
          "表示承接關係，相當於‘於是’、‘便’，用於連線前後兩個動作或情況。"
        ],
        "correct_answer": "指空間或時間上距離大，與‘短’相對。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10300, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "correct_definition": "指空间或时间上距离大，与‘短’相对。",
  "options": [
    "指性格、态度、言语等不严厉、不粗暴，使人感到亲切。",
    "指空间或时间上距离大，与‘短’相对。",
    "精确而细致，没有误差。",
    "病原体从一个生物体转移到另一个生物体，使后者感染相同疾病的过程。"
  ],
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "correct_definition": "指空間或時間上距離大，與‘短’相對。",
    "options": [
      "指性格、態度、言語等不嚴厲、不粗暴，使人感到親切。",
      "指空間或時間上距離大，與‘短’相對。",
      "精確而細緻，沒有誤差。",
      "病原體從一個生物體轉移到另一個生物體，使後者感染相同疾病的過程。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "defensive; used to protect yourself, keeping others from harming you",
        "指空间或时间上距离大，与‘短’相对。",
        "to drive",
        "more and more"
      ],
      "correct_answer": "指空间或时间上距离大，与‘短’相对。"
    }
  },
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "defensive; used to protect yourself, keeping others from harming you",
          "指空間或時間上距離大，與‘短’相對。",
          "to drive",
          "more and more"
        ],
        "correct_answer": "指空間或時間上距離大，與‘短’相對。"
      }
    }
  }
}
```

---

## sense 10300, level 4

#### Pack A
### Level 4 (sense 10300, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "没有蜜蜂，庄稼___不好。",
  "original_sentence": "没有蜜蜂，庄稼长不好。",
  "target_word": "长",
  "word": "长",
  "answer": {
    "accepted": [
      "长",
      "很长",
      "长短",
      "长长"
    ],
    "accepted_normalized": [
      "长",
      "很长",
      "长短",
      "长长"
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
    "sentence_with_blank": "沒有蜜蜂，莊稼___不好。",
    "original_sentence": "沒有蜜蜂，莊稼長不好。",
    "target_word": "長",
    "word": "長",
    "answer": {
      "accepted": [
        "長",
        "很長",
        "長短",
        "長長"
      ],
      "accepted_normalized": [
        "長",
        "很長",
        "長短",
        "長長"
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
### Level 4 (sense 10300, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这条路很___，我们走了很久。",
  "original_sentence": "这条路很长，我们走了很久。",
  "target_word": "长",
  "word": "长",
  "answer": {
    "accepted": [
      "长",
      "长度",
      "长长",
      "长短"
    ],
    "accepted_normalized": [
      "长",
      "长度",
      "长长",
      "长短"
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
    "sentence_with_blank": "這條路很___，我們走了很久。",
    "original_sentence": "這條路很長，我們走了很久。",
    "target_word": "長",
    "word": "長",
    "answer": {
      "accepted": [
        "長",
        "長度",
        "長長",
        "長短"
      ],
      "accepted_normalized": [
        "長",
        "長度",
        "長長",
        "長短"
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
  "sentence_with_blank": "___不一定就是好，短也有短的优点。",
  "original_sentence": "长不一定就是好，短也有短的优点。",
  "target_word": "长",
  "word": "长",
  "answer": {
    "accepted": [
      "长",
      "长度",
      "长长",
      "长短"
    ],
    "accepted_normalized": [
      "长",
      "长度",
      "长长",
      "长短"
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
    "sentence_with_blank": "___不一定就是好，短也有短的優點。",
    "original_sentence": "長不一定就是好，短也有短的優點。",
    "target_word": "長",
    "word": "長",
    "answer": {
      "accepted": [
        "長",
        "長度",
        "長長",
        "長短"
      ],
      "accepted_normalized": [
        "長",
        "長度",
        "長長",
        "長短"
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

## sense 10300, level 9

#### Pack A
### Level 9 (sense 10300, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "我们把假期安排得长一些，去更多的地方。",
  "hant": {
    "original_sentence": "我們把假期安排得長一些，去更多的地方。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "我们把假期安排得长一些，去更多的地方。",
  "chunks": [
    "我们",
    "把假期",
    "安排得长一些",
    "去更多的地方"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "去更多的地方",
    "我们",
    "把假期",
    "安排得长一些"
  ],
  "target_word": "长",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "我們把假期安排得長一些，去更多的地方。",
    "chunks": [
      "我們",
      "把假期",
      "安排得長一些",
      "去更多的地方"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "去更多的地方",
      "我們",
      "把假期",
      "安排得長一些"
    ],
    "target_word": "長",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "她留着一头长长的黑发，看起来很精神。",
  "hant": {
    "original_sentence": "她留著一頭長長的黑髮，看起來很精神。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "她留着一头长长的黑发，看起来很精神。",
  "chunks": [
    "她",
    "留着一头",
    "长长的黑发",
    "看起来很精神"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "长长的黑发",
    "她",
    "看起来很精神",
    "留着一头"
  ],
  "target_word": "长",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "她留著一頭長長的黑髮，看起來很精神。",
    "chunks": [
      "她",
      "留著一頭",
      "長長的黑髮",
      "看起來很精神"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "長長的黑髮",
      "她",
      "看起來很精神",
      "留著一頭"
    ],
    "target_word": "長",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10300, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "请把这张纸剪得再长一点儿。",
  "hant": {
    "original_sentence": "請把這張紙剪得再長一點兒。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "请把这张纸剪得再长一点儿。",
  "chunks": [
    "请",
    "把这张纸",
    "剪得再长一点儿"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "剪得再长一点儿",
    "请",
    "把这张纸"
  ],
  "target_word": "长",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "請把這張紙剪得再長一點兒。",
    "chunks": [
      "請",
      "把這張紙",
      "剪得再長一點兒"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "剪得再長一點兒",
      "請",
      "把這張紙"
    ],
    "target_word": "長",
    "chunk_count": 3
  }
}
```

---

## sense 10382, level 1

#### Pack A
### Level 1 (sense 10382, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "不同",
  "options": [
    "bù tōng",
    "bū tóng",
    "bù tóng",
    "bú tóng"
  ],
  "correct_answer": "bù tóng",
  "word": "不同",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "不同",
    "options": [
      "bù tōng",
      "bū tóng",
      "bù tóng",
      "bú tóng"
    ],
    "correct_answer": "bù tóng",
    "word": "不同",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "bù tóng",
  "options": [
    "社会",
    "不能",
    "不同",
    "福祉"
  ],
  "correct_answer": "不同",
  "word": "不同",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "福祉": "component",
    "社会": "component",
    "不能": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "bù tóng",
    "options": [
      "社會",
      "不能",
      "不同",
      "福祉"
    ],
    "correct_answer": "不同",
    "word": "不同",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "福祉": "component",
      "社会": "component",
      "不能": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "不同",
  "toneless_pinyin": "bu tong",
  "full_pinyin": "bù tóng",
  "options": [
    "43",
    "42",
    "44",
    "41"
  ],
  "correct_answer": "42",
  "option_labels": {
    "43": "falling (4) + dipping (3)",
    "42": "falling (4) + rising (2)",
    "44": "falling (4) + falling (4)",
    "41": "falling (4) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "不同",
    "toneless_pinyin": "bu tong",
    "full_pinyin": "bù tóng",
    "options": [
      "43",
      "42",
      "44",
      "41"
    ],
    "correct_answer": "42",
    "option_labels": {
      "43": "falling (4) + dipping (3)",
      "42": "falling (4) + rising (2)",
      "44": "falling (4) + falling (4)",
      "41": "falling (4) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10382, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "不同",
  "options": [
    "bù tōng",
    "bū tóng",
    "bù tóng",
    "bú tóng"
  ],
  "correct_answer": "bù tóng",
  "word": "不同",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "不同",
    "options": [
      "bù tōng",
      "bū tóng",
      "bù tóng",
      "bú tóng"
    ],
    "correct_answer": "bù tóng",
    "word": "不同",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "bù tóng",
  "options": [
    "社会",
    "不能",
    "不同",
    "福祉"
  ],
  "correct_answer": "不同",
  "word": "不同",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "福祉": "component",
    "社会": "component",
    "不能": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "bù tóng",
    "options": [
      "社會",
      "不能",
      "不同",
      "福祉"
    ],
    "correct_answer": "不同",
    "word": "不同",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "福祉": "component",
      "社会": "component",
      "不能": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "不同",
  "toneless_pinyin": "bu tong",
  "full_pinyin": "bù tóng",
  "options": [
    "43",
    "42",
    "44",
    "41"
  ],
  "correct_answer": "42",
  "option_labels": {
    "43": "falling (4) + dipping (3)",
    "42": "falling (4) + rising (2)",
    "44": "falling (4) + falling (4)",
    "41": "falling (4) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "不同",
    "toneless_pinyin": "bu tong",
    "full_pinyin": "bù tóng",
    "options": [
      "43",
      "42",
      "44",
      "41"
    ],
    "correct_answer": "42",
    "option_labels": {
      "43": "falling (4) + dipping (3)",
      "42": "falling (4) + rising (2)",
      "44": "falling (4) + falling (4)",
      "41": "falling (4) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

---

## sense 10382, level 2

#### Pack A
### Level 2 (sense 10382, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不同",
  "pronunciation": "bù tóng",
  "correct_definition": "指事物之间没有共同点，有差别。",
  "options": [
    "形容物体坚固、耐用，不易损坏。",
    "指事物之间没有共同点，有差别。",
    "指生物群落中一个群落被另一个群落取代的过程。",
    "指事物或系统的复杂程度。"
  ],
  "hant": {
    "word": "不同",
    "pronunciation": "bù tóng",
    "correct_definition": "指事物之間沒有共同點，有差別。",
    "options": [
      "形容物體堅固、耐用，不易損壞。",
      "指事物之間沒有共同點，有差別。",
      "指生物群落中一個群落被另一個群落取代的過程。",
      "指事物或系統的複雜程度。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不同",
  "pronunciation": "bù tóng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "转矩是让东西转起来的力量。",
        "ball; a round object you can bounce and play with",
        "像水一样快速喷出的一股东西。",
        "指事物之间没有共同点，有差别。"
      ],
      "correct_answer": "指事物之间没有共同点，有差别。"
    }
  },
  "hant": {
    "word": "不同",
    "pronunciation": "bù tóng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "轉矩是讓東西轉起來的力量。",
          "ball; a round object you can bounce and play with",
          "像水一樣快速噴出的一股東西。",
          "指事物之間沒有共同點，有差別。"
        ],
        "correct_answer": "指事物之間沒有共同點，有差別。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10382, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不同",
  "pronunciation": "bù tóng",
  "correct_definition": "指事物之间没有共同点，有差别。",
  "options": [
    "指事物之间没有共同点，有差别。",
    "表示恰好、正好；用于确认或肯定。",
    "收集、拾取或采摘，例如采集植物、数据或样本。",
    "用石磨或机器将小麦等谷物磨成面粉。"
  ],
  "hant": {
    "word": "不同",
    "pronunciation": "bù tóng",
    "correct_definition": "指事物之間沒有共同點，有差別。",
    "options": [
      "指事物之間沒有共同點，有差別。",
      "表示恰好、正好；用於確認或肯定。",
      "收集、拾取或採摘，例如採集植物、資料或樣本。",
      "用石磨或機器將小麥等穀物磨成麵粉。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不同",
  "pronunciation": "bù tóng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "纤维素是一种由葡萄糖单元组成的多糖，是植物细胞壁的主要成分，不溶于水，是膳食纤维的重要来源。",
        "排出削減；汚れたものを空気中に出す量を減らすこと",
        "宿題",
        "指事物之间没有共同点，有差别。"
      ],
      "correct_answer": "指事物之间没有共同点，有差别。"
    }
  },
  "hant": {
    "word": "不同",
    "pronunciation": "bù tóng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "纖維素是一種由葡萄糖單元組成的多糖，是植物細胞壁的主要成分，不溶於水，是膳食纖維的重要來源。",
          "排出削減；汚れたものを空気中に出す量を減らすこと",
          "宿題",
          "指事物之間沒有共同點，有差別。"
        ],
        "correct_answer": "指事物之間沒有共同點，有差別。"
      }
    }
  }
}
```

---

## sense 10382, level 4

#### Pack A
### Level 4 (sense 10382, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___地方的人对时间的看法不一样。",
  "original_sentence": "不同地方的人对时间的看法不一样。",
  "target_word": "不同",
  "word": "不同",
  "answer": {
    "accepted": [
      "不同",
      "不同点",
      "不同处",
      "不同意见"
    ],
    "accepted_normalized": [
      "不同",
      "不同点",
      "不同处",
      "不同意见"
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
    "sentence_with_blank": "___地方的人對時間的看法不一樣。",
    "original_sentence": "不同地方的人對時間的看法不一樣。",
    "target_word": "不同",
    "word": "不同",
    "answer": {
      "accepted": [
        "不同",
        "不同點",
        "不同處",
        "不同意見"
      ],
      "accepted_normalized": [
        "不同",
        "不同點",
        "不同處",
        "不同意見"
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
  "sentence_with_blank": "___国家采取了不同的监管方法。",
  "original_sentence": "不同国家采取了不同的监管方法。",
  "target_word": "不同",
  "word": "不同",
  "answer": {
    "accepted": [
      "不同",
      "不同点",
      "不同处",
      "不同意见"
    ],
    "accepted_normalized": [
      "不同",
      "不同点",
      "不同处",
      "不同意见"
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
    "sentence_with_blank": "___國家採取了不同的監管方法。",
    "original_sentence": "不同國家採取了不同的監管方法。",
    "target_word": "不同",
    "word": "不同",
    "answer": {
      "accepted": [
        "不同",
        "不同點",
        "不同處",
        "不同意見"
      ],
      "accepted_normalized": [
        "不同",
        "不同點",
        "不同處",
        "不同意見"
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
### Level 4 (sense 10382, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___地方的人对时间的看法不一样。",
  "original_sentence": "不同地方的人对时间的看法不一样。",
  "target_word": "不同",
  "word": "不同",
  "answer": {
    "accepted": [
      "不同",
      "不一样",
      "差异",
      "区别"
    ],
    "accepted_normalized": [
      "不同",
      "不一样",
      "差异",
      "区别"
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
    "sentence_with_blank": "___地方的人對時間的看法不一樣。",
    "original_sentence": "不同地方的人對時間的看法不一樣。",
    "target_word": "不同",
    "word": "不同",
    "answer": {
      "accepted": [
        "不同",
        "不一樣",
        "差異",
        "區別"
      ],
      "accepted_normalized": [
        "不同",
        "不一樣",
        "差異",
        "區別"
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

## sense 10382, level 9

#### Pack A
### Level 9 (sense 10382, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "”她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。",
  "hant": {
    "original_sentence": "”她的意思是，不同種類的植物和動物可以一起生活，大自然才會健康。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "”她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。",
  "chunks": [
    "”她的意思是",
    "不同种类的植物",
    "和动物",
    "可以一起",
    "生活",
    "大自然才会健康"
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
    "可以一起",
    "”她的意思是",
    "大自然才会健康",
    "和动物",
    "生活",
    "不同种类的植物"
  ],
  "target_word": "不同",
  "chunk_count": 6,
  "hant": {
    "schema_version": 2,
    "original_sentence": "”她的意思是，不同種類的植物和動物可以一起生活，大自然才會健康。",
    "chunks": [
      "”她的意思是",
      "不同種類的植物",
      "和動物",
      "可以一起",
      "生活",
      "大自然才會健康"
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
      "可以一起",
      "”她的意思是",
      "大自然才會健康",
      "和動物",
      "生活",
      "不同種類的植物"
    ],
    "target_word": "不同",
    "chunk_count": 6
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "全球化让不同文化的人常见面。",
  "hant": {
    "original_sentence": "全球化讓不同文化的人常見面。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "全球化让不同文化的人常见面。",
  "chunks": [
    "全球化",
    "让不同文化的人",
    "常见面"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "常见面",
    "让不同文化的人",
    "全球化"
  ],
  "target_word": "不同",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "全球化讓不同文化的人常見面。",
    "chunks": [
      "全球化",
      "讓不同文化的人",
      "常見面"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "常見面",
      "讓不同文化的人",
      "全球化"
    ],
    "target_word": "不同",
    "chunk_count": 3
  }
}
```

#### Pack B
### Level 9 (sense 10382, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "”她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。",
  "hant": {
    "original_sentence": "”她的意思是，不同種類的植物和動物可以一起生活，大自然才會健康。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "”她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。",
  "chunks": [
    "”她的意思是",
    "不同种类的植物",
    "和动物",
    "可以一起",
    "生活",
    "大自然才会健康"
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
    "可以一起",
    "”她的意思是",
    "大自然才会健康",
    "和动物",
    "生活",
    "不同种类的植物"
  ],
  "target_word": "不同",
  "chunk_count": 6,
  "hant": {
    "schema_version": 2,
    "original_sentence": "”她的意思是，不同種類的植物和動物可以一起生活，大自然才會健康。",
    "chunks": [
      "”她的意思是",
      "不同種類的植物",
      "和動物",
      "可以一起",
      "生活",
      "大自然才會健康"
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
      "可以一起",
      "”她的意思是",
      "大自然才會健康",
      "和動物",
      "生活",
      "不同種類的植物"
    ],
    "target_word": "不同",
    "chunk_count": 6
  }
}
```

---
