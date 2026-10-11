# Pairwise review pack 02

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


## sense 10104, level 9

#### Pack A
### Level 9 (sense 10104, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他把书打开，便找到了需要的内容。",
  "hant": {
    "original_sentence": "他把書開啟，便找到了需要的內容。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他把书打开，便找到了需要的内容。",
  "chunks": [
    "他",
    "把书",
    "打开",
    "便找到了需要的内容"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "把书",
    "他",
    "打开",
    "便找到了需要的内容"
  ],
  "target_word": "便",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他把書開啟，便找到了需要的內容。",
    "chunks": [
      "他",
      "把書",
      "開啟",
      "便找到了需要的內容"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "把書",
      "他",
      "開啟",
      "便找到了需要的內容"
    ],
    "target_word": "便",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "老师一解释，大家便明白了意思。",
  "hant": {
    "original_sentence": "老師一解釋，大家便明白了意思。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "老师一解释，大家便明白了意思。",
  "chunks": [
    "老师一",
    "解释",
    "大家",
    "便明白了意思"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "解释",
    "便明白了意思",
    "老师一",
    "大家"
  ],
  "target_word": "便",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "老師一解釋，大家便明白了意思。",
    "chunks": [
      "老師一",
      "解釋",
      "大家",
      "便明白了意思"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "解釋",
      "便明白了意思",
      "老師一",
      "大家"
    ],
    "target_word": "便",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10104, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他把作业一写便去打球了。",
  "hant": {
    "original_sentence": "他把作業一寫便去打球了。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他把作业一写便去打球了。",
  "chunks": [
    "他",
    "把作业一",
    "写便去打球了"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "写便去打球了",
    "他",
    "把作业一"
  ],
  "target_word": "便",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他把作業一寫便去打球了。",
    "chunks": [
      "他",
      "把作業一",
      "寫便去打球了"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "寫便去打球了",
      "他",
      "把作業一"
    ],
    "target_word": "便",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "老师一讲我便明白了。",
  "hant": {
    "original_sentence": "老師一講我便明白了。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "老师一讲我便明白了。",
  "chunks": [
    "老师一",
    "讲我",
    "便明白了"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "讲我",
    "便明白了",
    "老师一"
  ],
  "target_word": "便",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "老師一講我便明白了。",
    "chunks": [
      "老師一",
      "講我",
      "便明白了"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "講我",
      "便明白了",
      "老師一"
    ],
    "target_word": "便",
    "chunk_count": 3
  }
}
```

---

## sense 10105, level 1

#### Pack A
### Level 1 (sense 10105, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "广泛应用",
  "options": [
    "guǎng fān yìng yòng",
    "guǎng fàn yìng yōng",
    "guǎng fàn yìng yòng",
    "guāng fàn yìng yòng"
  ],
  "correct_answer": "guǎng fàn yìng yòng",
  "word": "广泛应用",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "廣泛應用",
    "options": [
      "guǎng fān yìng yòng",
      "guǎng fàn yìng yōng",
      "guǎng fàn yìng yòng",
      "guāng fàn yìng yòng"
    ],
    "correct_answer": "guǎng fàn yìng yòng",
    "word": "廣泛應用",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "guǎng fàn yìng yòng",
  "options": [
    "当地政府",
    "广泛应用",
    "应运而生",
    "归根结底"
  ],
  "correct_answer": "广泛应用",
  "word": "广泛应用",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "当地政府": "component",
    "归根结底": "component",
    "应运而生": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "guǎng fàn yìng yòng",
    "options": [
      "當地政府",
      "廣泛應用",
      "應運而生",
      "歸根結底"
    ],
    "correct_answer": "廣泛應用",
    "word": "廣泛應用",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "当地政府": "component",
      "归根结底": "component",
      "应运而生": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "广泛应用",
  "toneless_pinyin": "guang fan ying yong",
  "full_pinyin": "guǎng fàn yìng yòng",
  "options": [
    "3444",
    "3443",
    "3442",
    "3441"
  ],
  "correct_answer": "3444",
  "option_labels": {
    "3444": "dipping (3) + falling (4) + falling (4) + falling (4)",
    "3443": "dipping (3) + falling (4) + falling (4) + dipping (3)",
    "3442": "dipping (3) + falling (4) + falling (4) + rising (2)",
    "3441": "dipping (3) + falling (4) + falling (4) + high level (1)"
  },
  "syllable_count": 4,
  "hant": {
    "schema_version": 2,
    "word": "廣泛應用",
    "toneless_pinyin": "guang fan ying yong",
    "full_pinyin": "guǎng fàn yìng yòng",
    "options": [
      "3444",
      "3443",
      "3442",
      "3441"
    ],
    "correct_answer": "3444",
    "option_labels": {
      "3444": "dipping (3) + falling (4) + falling (4) + falling (4)",
      "3443": "dipping (3) + falling (4) + falling (4) + dipping (3)",
      "3442": "dipping (3) + falling (4) + falling (4) + rising (2)",
      "3441": "dipping (3) + falling (4) + falling (4) + high level (1)"
    },
    "syllable_count": 4
  }
}
```

#### Pack B
### Level 1 (sense 10105, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "广泛应用",
  "options": [
    "guǎng fān yìng yòng",
    "guǎng fàn yìng yōng",
    "guǎng fàn yìng yòng",
    "guāng fàn yìng yòng"
  ],
  "correct_answer": "guǎng fàn yìng yòng",
  "word": "广泛应用",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "廣泛應用",
    "options": [
      "guǎng fān yìng yòng",
      "guǎng fàn yìng yōng",
      "guǎng fàn yìng yòng",
      "guāng fàn yìng yòng"
    ],
    "correct_answer": "guǎng fàn yìng yòng",
    "word": "廣泛應用",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "guǎng fàn yìng yòng",
  "options": [
    "当地政府",
    "广泛应用",
    "应运而生",
    "归根结底"
  ],
  "correct_answer": "广泛应用",
  "word": "广泛应用",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "当地政府": "component",
    "归根结底": "component",
    "应运而生": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "guǎng fàn yìng yòng",
    "options": [
      "當地政府",
      "廣泛應用",
      "應運而生",
      "歸根結底"
    ],
    "correct_answer": "廣泛應用",
    "word": "廣泛應用",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "当地政府": "component",
      "归根结底": "component",
      "应运而生": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "word": "广泛应用",
  "toneless_pinyin": "guang fan ying yong",
  "full_pinyin": "guǎng fàn yìng yòng",
  "options": [
    "3444",
    "3443",
    "3442",
    "3441"
  ],
  "correct_answer": "3444",
  "option_labels": {
    "3444": "dipping (3) + falling (4) + falling (4) + falling (4)",
    "3443": "dipping (3) + falling (4) + falling (4) + dipping (3)",
    "3442": "dipping (3) + falling (4) + falling (4) + rising (2)",
    "3441": "dipping (3) + falling (4) + falling (4) + high level (1)"
  },
  "syllable_count": 4,
  "hant": {
    "schema_version": 2,
    "word": "廣泛應用",
    "toneless_pinyin": "guang fan ying yong",
    "full_pinyin": "guǎng fàn yìng yòng",
    "options": [
      "3444",
      "3443",
      "3442",
      "3441"
    ],
    "correct_answer": "3444",
    "option_labels": {
      "3444": "dipping (3) + falling (4) + falling (4) + falling (4)",
      "3443": "dipping (3) + falling (4) + falling (4) + dipping (3)",
      "3442": "dipping (3) + falling (4) + falling (4) + rising (2)",
      "3441": "dipping (3) + falling (4) + falling (4) + high level (1)"
    },
    "syllable_count": 4
  }
}
```

---

## sense 10105, level 2

#### Pack A
### Level 2 (sense 10105, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "广泛应用",
  "pronunciation": "guǎng fàn yìng yòng",
  "correct_definition": "在很多地方或领域里使用。",
  "options": [
    "在很多地方或领域里使用。",
    "沙漠是指降水极少、植被稀疏、地表以沙或岩石为主的地带。",
    "指一定时期内运输旅客的数量。",
    "从树上飘落下来的叶子。"
  ],
  "hant": {
    "word": "廣泛應用",
    "pronunciation": "guǎng fàn yìng yòng",
    "correct_definition": "在很多地方或領域裡使用。",
    "options": [
      "在很多地方或領域裡使用。",
      "沙漠是指降水極少、植被稀疏、地表以沙或岩石為主的地帶。",
      "指一定時期內運輸旅客的數量。",
      "從樹上飄落下來的葉子。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "广泛应用",
  "pronunciation": "guǎng fàn yìng yòng",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "一种硬纸片，上面可以写字、画画。",
        "to knit",
        "在很多地方或领域里使用。",
        "実は；本当のことを伝えるときに使う言葉"
      ],
      "correct_answer": "在很多地方或领域里使用。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "pronunciation": "guǎng fàn yìng yòng",
    "tier": "T5",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "一種硬紙片，上面可以寫字、畫畫。",
          "to knit",
          "在很多地方或領域裡使用。",
          "実は；本當のことを伝えるときに使う言葉"
        ],
        "correct_answer": "在很多地方或領域裡使用。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10105, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "广泛应用",
  "pronunciation": "guǎng fàn yìng yòng",
  "correct_definition": "广泛地使用或应用。",
  "options": [
    "指体育锻炼或身体活动，如跑步、游泳等。",
    "比喻崩溃、分裂或完全失败。",
    "广泛地使用或应用。",
    "指中国农村按行政划分的村级单位，通常包含若干自然村，设有村委会等管理机构。"
  ],
  "hant": {
    "word": "廣泛應用",
    "pronunciation": "guǎng fàn yìng yòng",
    "correct_definition": "廣泛地使用或應用。",
    "options": [
      "指體育鍛煉或身體活動，如跑步、游泳等。",
      "比喻崩潰、分裂或完全失敗。",
      "廣泛地使用或應用。",
      "指中國農村按行政劃分的村級單位，通常包含若干自然村，設有村委會等管理機構。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "广泛应用",
  "pronunciation": "guǎng fàn yìng yòng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "electric power system; everything that gets electricity from where it's made to our homes",
        "備える；ある能力や条件を持っていること",
        "广泛地使用或应用。",
        "模範"
      ],
      "correct_answer": "广泛地使用或应用。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "pronunciation": "guǎng fàn yìng yòng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "electric power system; everything that gets electricity from where it's made to our homes",
          "備える；ある能力や條件を持っていること",
          "廣泛地使用或應用。",
          "模範"
        ],
        "correct_answer": "廣泛地使用或應用。"
      }
    }
  }
}
```

---

## sense 10105, level 4

#### Pack A
### Level 4 (sense 10105, difficulty None)
**cloze_typed** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "中国早在唐代便已___雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "target_word": "广泛应用",
  "word": "广泛应用",
  "answer": {
    "accepted": [
      "广泛应用",
      "应用了",
      "应用过",
      "应用着",
      "應用"
    ],
    "accepted_normalized": [
      "广泛应用",
      "应用了",
      "应用过",
      "应用着",
      "应用"
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
    "sentence_with_blank": "中國早在唐代便已___雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "target_word": "廣泛應用",
    "word": "廣泛應用",
    "answer": {
      "accepted": [
        "廣泛應用",
        "應用了",
        "應用過",
        "應用著",
        "應用"
      ],
      "accepted_normalized": [
        "廣泛應用",
        "應用了",
        "應用過",
        "應用著",
        "應用"
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
**cloze_typed** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这种环保材料正在各个行业中得到___。",
  "original_sentence": "这种环保材料正在各个行业中得到广泛应用。",
  "target_word": "广泛应用",
  "word": "广泛应用",
  "answer": {
    "accepted": [
      "广泛应用",
      "应用了",
      "应用过",
      "应用着",
      "應用"
    ],
    "accepted_normalized": [
      "广泛应用",
      "应用了",
      "应用过",
      "应用着",
      "应用"
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
    "sentence_with_blank": "這種環保材料正在各個行業中得到___。",
    "original_sentence": "這種環保材料正在各個行業中得到廣泛應用。",
    "target_word": "廣泛應用",
    "word": "廣泛應用",
    "answer": {
      "accepted": [
        "廣泛應用",
        "應用了",
        "應用過",
        "應用著",
        "應用"
      ],
      "accepted_normalized": [
        "廣泛應用",
        "應用了",
        "應用過",
        "應用著",
        "應用"
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
### Level 4 (sense 10105, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "中国早在唐代便已___雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "target_word": "广泛应用",
  "word": "广泛应用",
  "answer": {
    "accepted": [
      "广泛应用",
      "广泛应用着",
      "广泛应用过",
      "广泛应用了"
    ],
    "accepted_normalized": [
      "广泛应用",
      "广泛应用着",
      "广泛应用过",
      "广泛应用了"
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
    "sentence_with_blank": "中國早在唐代便已___雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "target_word": "廣泛應用",
    "word": "廣泛應用",
    "answer": {
      "accepted": [
        "廣泛應用",
        "廣泛應用著",
        "廣泛應用過",
        "廣泛應用了"
      ],
      "accepted_normalized": [
        "廣泛應用",
        "廣泛應用著",
        "廣泛應用過",
        "廣泛應用了"
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
  "sentence_with_blank": "这种理论模型在相关学术研究中___。",
  "original_sentence": "这种理论模型在相关学术研究中广泛应用。",
  "target_word": "广泛应用",
  "word": "广泛应用",
  "answer": {
    "accepted": [
      "广泛应用",
      "广泛应用着",
      "广泛应用过",
      "广泛应用了"
    ],
    "accepted_normalized": [
      "广泛应用",
      "广泛应用着",
      "广泛应用过",
      "广泛应用了"
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
    "sentence_with_blank": "這種理論模型在相關學術研究中___。",
    "original_sentence": "這種理論模型在相關學術研究中廣泛應用。",
    "target_word": "廣泛應用",
    "word": "廣泛應用",
    "answer": {
      "accepted": [
        "廣泛應用",
        "廣泛應用著",
        "廣泛應用過",
        "廣泛應用了"
      ],
      "accepted_normalized": [
        "廣泛應用",
        "廣泛應用著",
        "廣泛應用過",
        "廣泛應用了"
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

## sense 10105, level 6

#### Pack A
### Level 6 (sense 10105, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种科学方法广泛应用已在生产实践中。",
      "is_correct": false
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用着。",
      "is_correct": false
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用出去。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。句中有“已”表示动作完成，而“着”表示动作持续，两者在时态上冲突，应删去“着”。 语序错误。介词结构“在生产实践中”作为状语，应放在谓语动词“广泛应用”之前，不能放在句末。 方向/结果补语误用。“应用”表示使用，不能与趋向补语“出去”搭配，语义不通，应删去“出去”。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "這種科學方法廣泛應用已在生產實踐中。",
        "is_correct": false
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用著。",
        "is_correct": false
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用出去。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。句中有“已”表示動作完成，而“著”表示動作持續，兩者在時態上衝突，應刪去“著”。 語序錯誤。介詞結構“在生產實踐中”作為狀語，應放在謂語動詞“廣泛應用”之前，不能放在句末。 方向/結果補語誤用。“應用”表示使用，不能與趨向補語“出去”搭配，語義不通，應刪去“出去”。",
    "target_word": "廣泛應用"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种创新方案已在各大企业中广泛应用出来。",
      "is_correct": false
    },
    {
      "text": "这种创新方案广泛应用已在各大企业中。",
      "is_correct": false
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“已”表示动作完成，而“着”表示动作持续或状态保持，两者时态矛盾，且“应用”后直接加“着”不符合汉语习惯。 语序错误。介词短语“在各大企业中”作地点状语，应放在谓语动词“广泛应用”之前，不能放在其后。 结果补语误用。“出来”表示从无到有或从隐蔽到显露，不能作“应用”的结果补语，此处属于动补搭配不当。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "這種創新方案已在各大企業中廣泛應用出來。",
        "is_correct": false
      },
      {
        "text": "這種創新方案廣泛應用已在各大企業中。",
        "is_correct": false
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“已”表示動作完成，而“著”表示動作持續或狀態保持，兩者時態矛盾，且“應用”後直接加“著”不符合漢語習慣。 語序錯誤。介詞短語“在各大企業中”作地點狀語，應放在謂語動詞“廣泛應用”之前，不能放在其後。 結果補語誤用。“出來”表示從無到有或從隱蔽到顯露，不能作“應用”的結果補語，此處屬於動補搭配不當。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "积极探索",
    "深入研究",
    "大力推广",
    "束之高阁"
  ],
  "correct_answer": "束之高阁",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "广泛地使用或应用。",
      "explanation": "反义项：将事物搁置起来不予使用，与「广泛应用」构成反义"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "積極探索",
      "深入研究",
      "大力推廣",
      "束之高閣"
    ],
    "correct_answer": "束之高閣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "廣泛地使用或應用。",
        "explanation": "反義項：將事物擱置起來不予使用，與「廣泛應用」構成反義"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10105, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "老师把新技术广泛应用得课堂教学中。",
      "is_correct": false
    },
    {
      "text": "老师把新技术广泛应用到了课堂教学中。",
      "is_correct": true
    },
    {
      "text": "老师把新技术广泛应用在到了课堂教学中。",
      "is_correct": false
    },
    {
      "text": "老师把新技术广泛应用去课堂教学中。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误。介词“在”和趋向补语“到”连用冗余且语序混乱，应为“应用到”或“应用在”。 语法错误。“得”后应接程度或结果补语，不能直接接地点宾语“课堂教学中”，应改为“到”。 语法错误。“去”表示离开说话人方向，不能用于引出动作涉及的处所或范围，此处应用“到”。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "老師把新技術廣泛應用得課堂教學中。",
        "is_correct": false
      },
      {
        "text": "老師把新技術廣泛應用到了課堂教學中。",
        "is_correct": true
      },
      {
        "text": "老師把新技術廣泛應用在到了課堂教學中。",
        "is_correct": false
      },
      {
        "text": "老師把新技術廣泛應用去課堂教學中。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤。介詞“在”和趨向補語“到”連用冗餘且語序混亂，應為“應用到”或“應用在”。 語法錯誤。“得”後應接程度或結果補語，不能直接接地點賓語“課堂教學中”，應改為“到”。 語法錯誤。“去”表示離開說話人方向，不能用於引出動作涉及的處所或範圍，此處應用“到”。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "广泛应用",
  "relation": "synonym",
  "options": [
    "偶尔一用",
    "普遍使用",
    "弃置不用",
    "束之高阁"
  ],
  "correct_answer": "普遍使用",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很多地方或领域里使用。",
      "explanation": "近义。意为在许多地方使用，与“广泛应用”语义相近。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "synonym",
    "options": [
      "偶爾一用",
      "普遍使用",
      "棄置不用",
      "束之高閣"
    ],
    "correct_answer": "普遍使用",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很多地方或領域裡使用。",
        "explanation": "近義。意為在許多地方使用，與“廣泛應用”語義相近。"
      }
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法。",
      "is_correct": true
    },
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法起来。",
      "is_correct": false
    },
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法进去。",
      "is_correct": false
    },
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法得过。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误。“起来”表示开始并持续，通常用于不及物动词或特定及物动词结构，此处“应用”带宾语“新疗法”，且语境强调已完成或常态，用“起来”语序和语义均不妥，应为“应用了”。 语法错误。“进去”表示进入内部，不能用于抽象的“疗法”实施过程，趋向补语误用。 语法错误。“得过”不是标准的体标记组合，经验体应为“过”，完成体为“了”，二者混用且位置错误。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法。",
        "is_correct": true
      },
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法起來。",
        "is_correct": false
      },
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法進去。",
        "is_correct": false
      },
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法得過。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤。“起來”表示開始並持續，通常用於不及物動詞或特定及物動詞結構，此處“應用”帶賓語“新療法”，且語境強調已完成或常態，用“起來”語序和語義均不妥，應為“應用了”。 語法錯誤。“進去”表示進入內部，不能用於抽象的“療法”實施過程，趨向補語誤用。 語法錯誤。“得過”不是標準的體標記組合，經驗體應為“過”，完成體為“了”，二者混用且位置錯誤。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "广泛应用",
  "relation": "synonym",
  "options": [
    "偶尔一用",
    "普遍使用",
    "弃置不用",
    "束之高阁"
  ],
  "correct_answer": "普遍使用",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很多地方或领域里使用。",
      "explanation": "近义。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "synonym",
    "options": [
      "偶爾一用",
      "普遍使用",
      "棄置不用",
      "束之高閣"
    ],
    "correct_answer": "普遍使用",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很多地方或領域裡使用。",
        "explanation": "近義。"
      }
    }
  }
}
```

---

## sense 10105, level 7

#### Pack A
### Level 7 (sense 10105, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法着。",
      "is_correct": false,
      "error_description": "错误句中“了”和“着”同时出现，体标记冲突。“了”表示完成，“着”表示持续，二者不能同时附着在同一个动词后表示同一动作状态。"
    },
    {
      "text": "为了帮助更多人，医生们广泛应用了新疗法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法著。",
        "is_correct": false,
        "error_description": "錯誤句中“了”和“著”同時出現，體標記衝突。“了”表示完成，“著”表示持續，二者不能同時附著在同一個動詞後表示同一動作狀態。"
      },
      {
        "text": "為了幫助更多人，醫生們廣泛應用了新療法。",
        "is_correct": true
      }
    ]
  }
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "同学们讨论过这种软件在绘画中的广泛应用。",
      "is_correct": true
    },
    {
      "text": "同学们讨论过这种软件在绘画中的广泛应用地。",
      "is_correct": false,
      "error_description": "错误句末尾多加了“地”，导致句子结构残缺或词性误用。“应用”在此处作名词性成分（讨论的对象），不需要副词后缀“地”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "同學們討論過這種軟體在繪畫中的廣泛應用。",
        "is_correct": true
      },
      {
        "text": "同學們討論過這種軟體在繪畫中的廣泛應用地。",
        "is_correct": false,
        "error_description": "錯誤句末尾多加了“地”，導致句子結構殘缺或詞性誤用。“應用”在此處作名詞性成分（討論的物件），不需要副詞字尾“地”。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10105, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种新型教学模式广泛应用了在各级学校。",
      "is_correct": false,
      "error_description": "体标位置错误。动态助词“了”不能放在动词和地点状语之间，应放在句末，或者使用“已”来表示动作的完成。"
    },
    {
      "text": "材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "这种方法在同学中广泛应用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種新型教學模式廣泛應用了在各級學校。",
        "is_correct": false,
        "error_description": "體標位置錯誤。動態助詞“了”不能放在動詞和地點狀語之間，應放在句末，或者使用“已”來表示動作的完成。"
      },
      {
        "text": "材料科學的進步使得複合材料得以廣泛應用，不僅減輕了結構重量，還增強了疲勞耐久性；計算流體動力學（CFD）的發展則使工程師能夠在虛擬風洞中模擬極端工況下的氣動效能，從而在原型製造前完成多輪迭代。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "這種方法在同學中廣泛應用。",
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
      "text": "这种模拟训练系统在专业学生中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案广泛应用已在各大企业中。",
      "is_correct": false,
      "error_description": "语序错误。副词“已”和介词短语“在各大企业中”应作为状语放在动词“广泛应用”之前，不能放在动词之后。"
    },
    {
      "text": "这种理论模型在相关学术研究中广泛应用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種模擬訓練系統在專業學生中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案廣泛應用已在各大企業中。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“已”和介詞短語“在各大企業中”應作為狀語放在動詞“廣泛應用”之前，不能放在動詞之後。"
      },
      {
        "text": "這種理論模型在相關學術研究中廣泛應用。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10105, level 9

#### Pack A
### Level 9 (sense 10105, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "这种新型社交软件在青年群体中广泛应用。",
  "hant": {
    "original_sentence": "這種新型社交軟體在青年群體中廣泛應用。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这种新型社交软件在青年群体中广泛应用。",
  "chunks": [
    "这种新型",
    "社交软件",
    "在青年",
    "群体中广泛应用"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "群体中广泛应用",
    "社交软件",
    "在青年",
    "这种新型"
  ],
  "target_word": "广泛应用",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這種新型社交軟體在青年群體中廣泛應用。",
    "chunks": [
      "這種新型",
      "社交軟體",
      "在青年",
      "群體中廣泛應用"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "群體中廣泛應用",
      "社交軟體",
      "在青年",
      "這種新型"
    ],
    "target_word": "廣泛應用",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这种科学方法已在生产实践中广泛应用。",
  "hant": {
    "original_sentence": "這種科學方法已在生產實踐中廣泛應用。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这种科学方法已在生产实践中广泛应用。",
  "chunks": [
    "这种科学方法",
    "已",
    "在生产实践中广泛应用"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "在生产实践中广泛应用",
    "已",
    "这种科学方法"
  ],
  "target_word": "广泛应用",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這種科學方法已在生產實踐中廣泛應用。",
    "chunks": [
      "這種科學方法",
      "已",
      "在生產實踐中廣泛應用"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "在生產實踐中廣泛應用",
      "已",
      "這種科學方法"
    ],
    "target_word": "廣泛應用",
    "chunk_count": 3
  }
}
```

#### Pack B
### Level 9 (sense 10105, difficulty None)
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "original_sentence": "太阳能技术已经在很多农村得到广泛应用。",
  "hant": {
    "original_sentence": "太陽能技術已經在很多農村得到廣泛應用。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "太阳能技术已经在很多农村得到广泛应用。",
  "chunks": [
    "太阳能技术",
    "已经",
    "在很多农村",
    "得到广泛应用"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "得到广泛应用",
    "已经",
    "在很多农村",
    "太阳能技术"
  ],
  "target_word": "广泛应用",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "太陽能技術已經在很多農村得到廣泛應用。",
    "chunks": [
      "太陽能技術",
      "已經",
      "在很多農村",
      "得到廣泛應用"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "得到廣泛應用",
      "已經",
      "在很多農村",
      "太陽能技術"
    ],
    "target_word": "廣泛應用",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "original_sentence": "老师把新技术广泛应用到了课堂教学中。",
  "hant": {
    "original_sentence": "老師把新技術廣泛應用到了課堂教學中。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T5`
```json
{
  "schema_version": 2,
  "original_sentence": "老师把新技术广泛应用到了课堂教学中。",
  "chunks": [
    "老师把",
    "新技术",
    "广泛应用到",
    "了课堂教学中"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "了课堂教学中",
    "新技术",
    "广泛应用到",
    "老师把"
  ],
  "target_word": "广泛应用",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "老師把新技術廣泛應用到了課堂教學中。",
    "chunks": [
      "老師把",
      "新技術",
      "廣泛應用到",
      "了課堂教學中"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "了課堂教學中",
      "新技術",
      "廣泛應用到",
      "老師把"
    ],
    "target_word": "廣泛應用",
    "chunk_count": 4
  }
}
```

---

## sense 10106, level 1

#### Pack A
### Level 1 (sense 10106, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "毕",
  "options": [
    "bī",
    "bì",
    "bí",
    "bǐ"
  ],
  "correct_answer": "bì",
  "word": "毕",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "畢",
    "options": [
      "bī",
      "bì",
      "bí",
      "bǐ"
    ],
    "correct_answer": "bì",
    "word": "畢",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "ipa": "[pi˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "毕",
    "壁",
    "避",
    "必"
  ],
  "correct_answer": "毕",
  "explanation": "正确。目标词，读音 bì，意为完成、结束。",
  "distractor_explanations": {
    "必": "干扰项。读音 bì（同音同调），意为一定、必须，与“结束”义无关。",
    "避": "干扰项。读音 bì（同音同调），意为躲避、避免，与“结束”义无关。",
    "壁": "干扰项。读音 bì（同音同调），意为墙壁，名词，与动词义无关。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "ipa": "[pi˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "畢",
      "壁",
      "避",
      "必"
    ],
    "correct_answer": "畢",
    "explanation": "正確。目標詞，讀音 bì，意為完成、結束。",
    "distractor_explanations": {
      "必": "干擾項。讀音 bì（同音同調），意為一定、必須，與“結束”義無關。",
      "避": "干擾項。讀音 bì（同音同調），意為躲避、避免，與“結束”義無關。",
      "壁": "干擾項。讀音 bì（同音同調），意為牆壁，名詞，與動詞義無關。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "bì",
  "options": [
    "皆",
    "能",
    "比",
    "毕"
  ],
  "correct_answer": "毕",
  "word": "毕",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "皆": "component",
    "能": "component",
    "比": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "bì",
    "options": [
      "皆",
      "能",
      "比",
      "畢"
    ],
    "correct_answer": "畢",
    "word": "畢",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "皆": "component",
      "能": "component",
      "比": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "毕",
  "toneless_pinyin": "bi",
  "full_pinyin": "bì",
  "options": [
    "2",
    "1",
    "3",
    "4"
  ],
  "correct_answer": "4",
  "option_labels": {
    "2": "rising (2)",
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "畢",
    "toneless_pinyin": "bi",
    "full_pinyin": "bì",
    "options": [
      "2",
      "1",
      "3",
      "4"
    ],
    "correct_answer": "4",
    "option_labels": {
      "2": "rising (2)",
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)"
    },
    "syllable_count": 1
  }
}
```

#### Pack B
### Level 1 (sense 10106, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "毕",
  "options": [
    "bī",
    "bì",
    "bí",
    "bǐ"
  ],
  "correct_answer": "bì",
  "word": "毕",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "畢",
    "options": [
      "bī",
      "bì",
      "bí",
      "bǐ"
    ],
    "correct_answer": "bì",
    "word": "畢",
    "direction": "hanzi_to_pinyin"
  }
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "ipa": "[pi˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "笔",
    "鼻",
    "逼",
    "毕"
  ],
  "correct_answer": "毕",
  "explanation": "正确。“毕”读作 bì，意为完成、结束。",
  "distractor_explanations": {
    "逼": "错误。“逼”读作 bī，第一声，意为强迫、接近，声调不同。",
    "鼻": "错误。“鼻”读作 bí，第二声，指鼻子，声调不同。",
    "笔": "错误。“笔”读作 bǐ，第三声，指写字工具，声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "ipa": "[pi˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "筆",
      "鼻",
      "逼",
      "畢"
    ],
    "correct_answer": "畢",
    "explanation": "正確。“畢”讀作 bì，意為完成、結束。",
    "distractor_explanations": {
      "逼": "錯誤。“逼”讀作 bī，第一聲，意為強迫、接近，聲調不同。",
      "鼻": "錯誤。“鼻”讀作 bí，第二聲，指鼻子，聲調不同。",
      "笔": "錯誤。“筆”讀作 bǐ，第三聲，指寫字工具，聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "bì",
  "options": [
    "皆",
    "能",
    "比",
    "毕"
  ],
  "correct_answer": "毕",
  "word": "毕",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "皆": "component",
    "能": "component",
    "比": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "bì",
    "options": [
      "皆",
      "能",
      "比",
      "畢"
    ],
    "correct_answer": "畢",
    "word": "畢",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "皆": "component",
      "能": "component",
      "比": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "毕",
  "toneless_pinyin": "bi",
  "full_pinyin": "bì",
  "options": [
    "2",
    "1",
    "3",
    "4"
  ],
  "correct_answer": "4",
  "option_labels": {
    "2": "rising (2)",
    "1": "high level (1)",
    "3": "dipping (3)",
    "4": "falling (4)"
  },
  "syllable_count": 1,
  "hant": {
    "schema_version": 2,
    "word": "畢",
    "toneless_pinyin": "bi",
    "full_pinyin": "bì",
    "options": [
      "2",
      "1",
      "3",
      "4"
    ],
    "correct_answer": "4",
    "option_labels": {
      "2": "rising (2)",
      "1": "high level (1)",
      "3": "dipping (3)",
      "4": "falling (4)"
    },
    "syllable_count": 1
  }
}
```

---

## sense 10106, level 2

#### Pack A
### Level 2 (sense 10106, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "correct_definition": "完成；结束",
  "options": [
    "形容程度非常高，超过一般水平。",
    "指故乡，家乡的土地，也泛指地方特色。",
    "指事物周围或区域的大小界限。",
    "完成；结束"
  ],
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "correct_definition": "完成；結束",
    "options": [
      "形容程度非常高，超過一般水平。",
      "指故鄉，家鄉的土地，也泛指地方特色。",
      "指事物周圍或區域的大小界限。",
      "完成；結束"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "完成；结束",
        "to send a signal",
        "说话或做事时所依据的法则或标准。",
        "complementarity"
      ],
      "correct_answer": "完成；结束"
    }
  },
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "完成；結束",
          "to send a signal",
          "說話或做事時所依據的法則或標準。",
          "complementarity"
        ],
        "correct_answer": "完成；結束"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10106, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "correct_definition": "完成；结束。",
  "options": [
    "指地表长期积水、生长湿生植物的低洼地带。",
    "完成；结束。",
    "指最终归结到最根本的、最核心的问题或原因上。",
    "指液体或气体等物质连续地移动、变化。"
  ],
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "correct_definition": "完成；結束。",
    "options": [
      "指地表長期積水、生長溼生植物的低窪地帶。",
      "完成；結束。",
      "指最終歸結到最根本的、最核心的問題或原因上。",
      "指液體或氣體等物質連續地移動、變化。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "完成；结束。",
        "terraced field; farmland on a mountainside that looks like stairs",
        "teaching; a teacher instructing and students learning",
        "築く；何かを組み立てて作ること"
      ],
      "correct_answer": "完成；结束。"
    }
  },
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "完成；結束。",
          "terraced field; farmland on a mountainside that looks like stairs",
          "teaching; a teacher instructing and students learning",
          "築く；何かを組み立てて作ること"
        ],
        "correct_answer": "完成；結束。"
      }
    }
  }
}
```

---

## sense 10106, level 4

#### Pack A
### Level 4 (sense 10106, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "他长舒一口气，心想这事总算___了。",
  "original_sentence": "他长舒一口气，心想这事总算毕了。",
  "target_word": "毕",
  "word": "毕",
  "answer": {
    "accepted": [
      "毕",
      "完毕",
      "毕业"
    ],
    "accepted_normalized": [
      "毕",
      "完毕",
      "毕业"
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
    "sentence_with_blank": "他長舒一口氣，心想這事總算___了。",
    "original_sentence": "他長舒一口氣，心想這事總算畢了。",
    "target_word": "畢",
    "word": "畢",
    "answer": {
      "accepted": [
        "畢",
        "完畢",
        "畢業"
      ],
      "accepted_normalized": [
        "畢",
        "完畢",
        "畢業"
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
  "sentence_with_blank": "他把事情做完，心里觉得这事已___。",
  "original_sentence": "他把事情做完，心里觉得这事已毕。",
  "target_word": "毕",
  "word": "毕",
  "answer": {
    "accepted": [
      "毕",
      "完毕",
      "毕业"
    ],
    "accepted_normalized": [
      "毕",
      "完毕",
      "毕业"
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
    "sentence_with_blank": "他把事情做完，心裡覺得這事已___。",
    "original_sentence": "他把事情做完，心裡覺得這事已畢。",
    "target_word": "畢",
    "word": "畢",
    "answer": {
      "accepted": [
        "畢",
        "完畢",
        "畢業"
      ],
      "accepted_normalized": [
        "畢",
        "完畢",
        "畢業"
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
### Level 4 (sense 10106, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "经过数年的艰苦钻研，这项科研课题终于圆满告___。",
  "original_sentence": "经过数年的艰苦钻研，这项科研课题终于圆满告毕。",
  "target_word": "毕",
  "word": "毕",
  "answer": {
    "accepted": [
      "毕",
      "毕业",
      "完毕",
      "毕生",
      "原形毕露"
    ],
    "accepted_normalized": [
      "毕",
      "毕业",
      "完毕",
      "毕生",
      "原形毕露"
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
    "sentence_with_blank": "經過數年的艱苦鑽研，這項科研課題終於圓滿告___。",
    "original_sentence": "經過數年的艱苦鑽研，這項科研課題終於圓滿告畢。",
    "target_word": "畢",
    "word": "畢",
    "answer": {
      "accepted": [
        "畢",
        "畢業",
        "完畢",
        "畢生",
        "原形畢露"
      ],
      "accepted_normalized": [
        "畢",
        "畢業",
        "完畢",
        "畢生",
        "原形畢露"
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
  "sentence_with_blank": "演讲说完了，发言完___。",
  "original_sentence": "演讲说完了，发言完毕。",
  "target_word": "毕",
  "word": "毕",
  "answer": {
    "accepted": [
      "毕",
      "毕业",
      "完毕",
      "毕生",
      "原形毕露"
    ],
    "accepted_normalized": [
      "毕",
      "毕业",
      "完毕",
      "毕生",
      "原形毕露"
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
    "sentence_with_blank": "演講說完了，發言完___。",
    "original_sentence": "演講說完了，發言完畢。",
    "target_word": "畢",
    "word": "畢",
    "answer": {
      "accepted": [
        "畢",
        "畢業",
        "完畢",
        "畢生",
        "原形畢露"
      ],
      "accepted_normalized": [
        "畢",
        "畢業",
        "完畢",
        "畢生",
        "原形畢露"
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
