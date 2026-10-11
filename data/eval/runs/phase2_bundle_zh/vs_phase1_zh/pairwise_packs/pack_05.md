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


## sense 10112, level 1

#### Pack A
### Level 1 (sense 10112, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "排版",
  "options": [
    "pái bán",
    "pái bān",
    "pāi bǎn",
    "pái bǎn"
  ],
  "correct_answer": "pái bǎn",
  "word": "排版",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "排版",
    "options": [
      "pái bán",
      "pái bān",
      "pāi bǎn",
      "pái bǎn"
    ],
    "correct_answer": "pái bǎn",
    "word": "排版",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "pái bǎn",
  "options": [
    "排版",
    "抽排",
    "安排",
    "雕版"
  ],
  "correct_answer": "排版",
  "word": "排版",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "抽排": "component",
    "雕版": "component",
    "安排": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "pái bǎn",
    "options": [
      "排版",
      "抽排",
      "安排",
      "雕版"
    ],
    "correct_answer": "排版",
    "word": "排版",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "抽排": "component",
      "雕版": "component",
      "安排": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "排版",
  "toneless_pinyin": "pai ban",
  "full_pinyin": "pái bǎn",
  "options": [
    "22",
    "23",
    "24",
    "21"
  ],
  "correct_answer": "23",
  "option_labels": {
    "22": "rising (2) + rising (2)",
    "23": "rising (2) + dipping (3)",
    "24": "rising (2) + falling (4)",
    "21": "rising (2) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "排版",
    "toneless_pinyin": "pai ban",
    "full_pinyin": "pái bǎn",
    "options": [
      "22",
      "23",
      "24",
      "21"
    ],
    "correct_answer": "23",
    "option_labels": {
      "22": "rising (2) + rising (2)",
      "23": "rising (2) + dipping (3)",
      "24": "rising (2) + falling (4)",
      "21": "rising (2) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10112, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "排版",
  "options": [
    "pái bán",
    "pái bān",
    "pāi bǎn",
    "pái bǎn"
  ],
  "correct_answer": "pái bǎn",
  "word": "排版",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "排版",
    "options": [
      "pái bán",
      "pái bān",
      "pāi bǎn",
      "pái bǎn"
    ],
    "correct_answer": "pái bǎn",
    "word": "排版",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "pái bǎn",
  "options": [
    "排版",
    "抽排",
    "安排",
    "雕版"
  ],
  "correct_answer": "排版",
  "word": "排版",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "抽排": "component",
    "雕版": "component",
    "安排": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "pái bǎn",
    "options": [
      "排版",
      "抽排",
      "安排",
      "雕版"
    ],
    "correct_answer": "排版",
    "word": "排版",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "抽排": "component",
      "雕版": "component",
      "安排": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "排版",
  "toneless_pinyin": "pai ban",
  "full_pinyin": "pái bǎn",
  "options": [
    "22",
    "23",
    "24",
    "21"
  ],
  "correct_answer": "23",
  "option_labels": {
    "22": "rising (2) + rising (2)",
    "23": "rising (2) + dipping (3)",
    "24": "rising (2) + falling (4)",
    "21": "rising (2) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "排版",
    "toneless_pinyin": "pai ban",
    "full_pinyin": "pái bǎn",
    "options": [
      "22",
      "23",
      "24",
      "21"
    ],
    "correct_answer": "23",
    "option_labels": {
      "22": "rising (2) + rising (2)",
      "23": "rising (2) + dipping (3)",
      "24": "rising (2) + falling (4)",
      "21": "rising (2) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

---

## sense 10112, level 2

#### Pack A
### Level 2 (sense 10112, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "pronunciation": "pái bǎn",
  "correct_definition": "把文字或图片按规则排列好",
  "options": [
    "把文字或图片按规则排列好",
    "表示程度或范围超出所提到的，不仅限于。",
    "用手或工具使物体向自己前方或离开原位置移动。",
    "对财务账目、报表等进行审查和核实，以确认其真实性和合规性。"
  ],
  "hant": {
    "word": "排版",
    "pronunciation": "pái bǎn",
    "correct_definition": "把文字或圖片按規則排列好",
    "options": [
      "把文字或圖片按規則排列好",
      "表示程度或範圍超出所提到的，不僅限於。",
      "用手或工具使物體向自己前方或離開原位置移動。",
      "對財務賬目、報表等進行審查和核實，以確認其真實性和合規性。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "pronunciation": "pái bǎn",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "把文字或图片按规则排列好",
        "把分开的东西合在一起。",
        "觉得某件事是真的，在心里同意它。",
        "to take off; for a plane to fly up from the ground into the sky"
      ],
      "correct_answer": "把文字或图片按规则排列好"
    }
  },
  "hant": {
    "word": "排版",
    "pronunciation": "pái bǎn",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "把文字或圖片按規則排列好",
          "把分開的東西合在一起。",
          "覺得某件事是真的，在心裡同意它。",
          "to take off; for a plane to fly up from the ground into the sky"
        ],
        "correct_answer": "把文字或圖片按規則排列好"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10112, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "pronunciation": "pái bǎn",
  "correct_definition": "把文字、图片按规则排列组合，方便阅读。",
  "options": [
    "把家搬到别处去居住。",
    "把文字、图片按规则排列组合，方便阅读。",
    "粗糙度指物体表面或材料的不平整、不光滑的程度，通常用于描述表面质感或加工精度。",
    "指态度认真，完全按照规则或要求去做，不马虎。"
  ],
  "hant": {
    "word": "排版",
    "pronunciation": "pái bǎn",
    "correct_definition": "把文字、圖片按規則排列組合，方便閱讀。",
    "options": [
      "把家搬到別處去居住。",
      "把文字、圖片按規則排列組合，方便閱讀。",
      "粗糙度指物體表面或材料的不平整、不光滑的程度，通常用於描述表面質感或加工精度。",
      "指態度認真，完全按照規則或要求去做，不馬虎。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "pronunciation": "pái bǎn",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "把文字、图片按规则排列组合，方便阅读。",
        "非洲是一个很大的地方，那里有很多动物，比如大象和狮子。",
        "機能化する",
        "sound"
      ],
      "correct_answer": "把文字、图片按规则排列组合，方便阅读。"
    }
  },
  "hant": {
    "word": "排版",
    "pronunciation": "pái bǎn",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "把文字、圖片按規則排列組合，方便閱讀。",
          "非洲是一個很大的地方，那裡有很多動物，比如大象和獅子。",
          "機能化する",
          "sound"
        ],
        "correct_answer": "把文字、圖片按規則排列組合，方便閱讀。"
      }
    }
  }
}
```

---

## sense 10112, level 3

#### Pack A
### Level 3 (sense 10112, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复___的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "排版",
  "options": [
    "打印",
    "排版",
    "阅读",
    "书写"
  ],
  "explanation": "正确。语境为杂志的图文排列特色，符合“排版”语义。",
  "distractor_tags": {},
  "word_definition": "把文字或图片按规则排列好",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複___的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "排版",
    "options": [
      "列印",
      "排版",
      "閱讀",
      "書寫"
    ],
    "explanation": "正確。語境為雜誌的圖文排列特色，符合“排版”語義。",
    "distractor_tags": {},
    "word_definition": "把文字或圖片按規則排列好",
    "target_word": "排版"
  }
}
```

#### Pack B
### Level 3 (sense 10112, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复___的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "排版",
  "options": [
    "描绘",
    "雕刻",
    "排版",
    "装订"
  ],
  "explanation": "正确选项。毕昇首创泥活字，其核心创新在于可以重复排列组合活字进行印刷。",
  "distractor_tags": {},
  "word_definition": "把文字、图片按规则排列组合，方便阅读。",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複___的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "排版",
    "options": [
      "描繪",
      "雕刻",
      "排版",
      "裝訂"
    ],
    "explanation": "正確選項。畢昇首創泥活字，其核心創新在於可以重複排列組合活字進行印刷。",
    "distractor_tags": {},
    "word_definition": "把文字、圖片按規則排列組合，方便閱讀。",
    "target_word": "排版"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "他正___着校刊封面。",
  "original_sentence": "他正排版着校刊封面。",
  "correct_answer": "排版",
  "options": [
    "撰写",
    "出版",
    "排版",
    "装订"
  ],
  "explanation": "正确，符合语境，指对校刊封面进行文字和图片的排列组合。",
  "distractor_tags": {},
  "word_definition": "把文字、图片按规则排列组合，方便阅读。",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "他正___著校刊封面。",
    "original_sentence": "他正排版著校刊封面。",
    "correct_answer": "排版",
    "options": [
      "撰寫",
      "出版",
      "排版",
      "裝訂"
    ],
    "explanation": "正確，符合語境，指對校刊封面進行文字和圖片的排列組合。",
    "distractor_tags": {},
    "word_definition": "把文字、圖片按規則排列組合，方便閱讀。",
    "target_word": "排版"
  }
}
```

---

## sense 10112, level 4

#### Pack A
### Level 4 (sense 10112, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "然而，受制于汉字数量庞大、___复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
  "original_sentence": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
  "target_word": "排版",
  "word": "排版",
  "answer": {
    "accepted": [
      "排版",
      "排版了",
      "排版着",
      "排版过",
      "排版机"
    ],
    "accepted_normalized": [
      "排版",
      "排版了",
      "排版着",
      "排版过",
      "排版机"
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
    "sentence_with_blank": "然而，受制於漢字數量龐大、___複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
    "original_sentence": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
    "target_word": "排版",
    "word": "排版",
    "answer": {
      "accepted": [
        "排版",
        "排版了",
        "排版著",
        "排版過",
        "排版機"
      ],
      "accepted_normalized": [
        "排版",
        "排版了",
        "排版著",
        "排版過",
        "排版機"
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
  "sentence_with_blank": "我学过给杂志___。",
  "original_sentence": "我学过给杂志排版。",
  "target_word": "排版",
  "word": "排版",
  "answer": {
    "accepted": [
      "排版",
      "排版了",
      "排版着",
      "排版过",
      "排版机"
    ],
    "accepted_normalized": [
      "排版",
      "排版了",
      "排版着",
      "排版过",
      "排版机"
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
    "sentence_with_blank": "我學過給雜誌___。",
    "original_sentence": "我學過給雜誌排版。",
    "target_word": "排版",
    "word": "排版",
    "answer": {
      "accepted": [
        "排版",
        "排版了",
        "排版著",
        "排版過",
        "排版機"
      ],
      "accepted_normalized": [
        "排版",
        "排版了",
        "排版著",
        "排版過",
        "排版機"
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
### Level 4 (sense 10112, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "然而，受制于汉字数量庞大、___复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
  "original_sentence": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
  "target_word": "排版",
  "word": "排版",
  "answer": {
    "accepted": [
      "排版",
      "排了版",
      "排着版",
      "排过版",
      "排版员"
    ],
    "accepted_normalized": [
      "排版",
      "排了版",
      "排着版",
      "排过版",
      "排版员"
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
    "sentence_with_blank": "然而，受制於漢字數量龐大、___複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
    "original_sentence": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
    "target_word": "排版",
    "word": "排版",
    "answer": {
      "accepted": [
        "排版",
        "排了版",
        "排著版",
        "排過版",
        "排版員"
      ],
      "accepted_normalized": [
        "排版",
        "排了版",
        "排著版",
        "排過版",
        "排版員"
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
  "sentence_with_blank": "我学过怎么给文章___。",
  "original_sentence": "我学过怎么给文章排版。",
  "target_word": "排版",
  "word": "排版",
  "answer": {
    "accepted": [
      "排版",
      "排了版",
      "排着版",
      "排过版",
      "排版员"
    ],
    "accepted_normalized": [
      "排版",
      "排了版",
      "排着版",
      "排过版",
      "排版员"
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
    "sentence_with_blank": "我學過怎麼給文章___。",
    "original_sentence": "我學過怎麼給文章排版。",
    "target_word": "排版",
    "word": "排版",
    "answer": {
      "accepted": [
        "排版",
        "排了版",
        "排著版",
        "排過版",
        "排版員"
      ],
      "accepted_normalized": [
        "排版",
        "排了版",
        "排著版",
        "排過版",
        "排版員"
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

## sense 10112, level 6

#### Pack A
### Level 6 (sense 10112, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这本书的一个排版看起来很舒服。",
      "is_correct": false
    },
    {
      "text": "这本书的排版看起来很舒服。",
      "is_correct": true
    },
    {
      "text": "这本书的排版看起来很舒服地。",
      "is_correct": false
    },
    {
      "text": "这本书的排版看起很舒服来。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误。形容词“舒服”作谓语或补语时，不应加“地”，“地”通常用于状语修饰动词。 语序错误。趋向补语“起来”被错误拆分插入形容词中间，正确应为“看起来”。 量词/名词化错误。“排版”在此处作为抽象的设计效果，通常不加个体量词“一个”，或直接说“这种排版”。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "這本書的一個排版看起來很舒服。",
        "is_correct": false
      },
      {
        "text": "這本書的排版看起來很舒服。",
        "is_correct": true
      },
      {
        "text": "這本書的排版看起來很舒服地。",
        "is_correct": false
      },
      {
        "text": "這本書的排版看起很舒服來。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤。形容詞“舒服”作謂語或補語時，不應加“地”，“地”通常用於狀語修飾動詞。 語序錯誤。趨向補語“起來”被錯誤拆分插入形容詞中間，正確應為“看起來”。 量詞/名詞化錯誤。“排版”在此處作為抽象的設計效果，通常不加個體量詞“一個”，或直接說“這種排版”。",
    "target_word": "排版"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "relation": "synonym",
  "options": [
    "编排",
    "混乱",
    "删除",
    "写作"
  ],
  "correct_answer": "编排",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字或图片按规则排列好",
      "explanation": "近义。“编排”也包含排列、组织的意思，在图文处理语境下与“排版”意义相近。"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "synonym",
    "options": [
      "編排",
      "混亂",
      "刪除",
      "寫作"
    ],
    "correct_answer": "編排",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字或圖片按規則排列好",
        "explanation": "近義。“編排”也包含排列、組織的意思，在圖文處理語境下與“排版”意義相近。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "排版",
  "relation": "synonym",
  "options": [
    "破坏",
    "整理",
    "编排",
    "杂乱"
  ],
  "correct_answer": "编排",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字或图片按规则排列好",
      "explanation": "近义。“编排”也包含排列、组织的意思，在图文处理语境下与“排版”意义相近。"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "synonym",
    "options": [
      "破壞",
      "整理",
      "編排",
      "雜亂"
    ],
    "correct_answer": "編排",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字或圖片按規則排列好",
        "explanation": "近義。“編排”也包含排列、組織的意思，在圖文處理語境下與“排版”意義相近。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10112, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正在排版着那本杂志的封面。",
      "is_correct": false
    },
    {
      "text": "哥哥在大学学排版。",
      "is_correct": true
    },
    {
      "text": "他排版每天在公司里。",
      "is_correct": false
    },
    {
      "text": "他把那篇文章排版出来了。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。“排版”是动宾式离合词，动态助词“着”应插在动词和宾语之间，说成“排着版”，不能直接加在词后。 语序错误。时间状语“每天”应放在动词“排版”之前或句首，不能放在动宾结构之后。 结果补语误用。“排版”是离合词，结果补语“出来”应插在“排”和“版”之间，说成“排出（了）版来”，不能直接放在词后。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "他正在排版著那本雜誌的封面。",
        "is_correct": false
      },
      {
        "text": "哥哥在大學學排版。",
        "is_correct": true
      },
      {
        "text": "他排版每天在公司裡。",
        "is_correct": false
      },
      {
        "text": "他把那篇文章排版出來了。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。“排版”是動賓式離合詞，動態助詞“著”應插在動詞和賓語之間，說成“排著版”，不能直接加在詞後。 語序錯誤。時間狀語“每天”應放在動詞“排版”之前或句首，不能放在動賓結構之後。 結果補語誤用。“排版”是離合詞，結果補語“出來”應插在“排”和“版”之間，說成“排出（了）版來”，不能直接放在詞後。",
    "target_word": "排版"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他排版校刊正在。",
      "is_correct": false
    },
    {
      "text": "他把文章排版进去。",
      "is_correct": false
    },
    {
      "text": "他排版了着校刊封面。",
      "is_correct": false
    },
    {
      "text": "排版工作非常辛苦。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：“了”和“着”不能连用表示完成和进行，应去掉“了”或改为“正在排版”。 语序错误：副词“正在”应放在动词“排版”之前作状语，不能放在句末。 方向/结果补语误用：“进去”表示由外到内的方向，与“排版”的语义不搭配，应改为“排版好”或“排版完”。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "他排版校刊正在。",
        "is_correct": false
      },
      {
        "text": "他把文章排版進去。",
        "is_correct": false
      },
      {
        "text": "他排版了著校刊封面。",
        "is_correct": false
      },
      {
        "text": "排版工作非常辛苦。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：“了”和“著”不能連用表示完成和進行，應去掉“了”或改為“正在排版”。 語序錯誤：副詞“正在”應放在動詞“排版”之前作狀語，不能放在句末。 方向/結果補語誤用：“進去”表示由外到內的方向，與“排版”的語義不搭配，應改為“排版好”或“排版完”。",
    "target_word": "排版"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "打乱",
    "印刷",
    "编辑",
    "校对"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字、图片按规则排列组合，方便阅读。",
      "explanation": "反义：排版是按规则有序排列，打乱是破坏秩序使之无序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "打亂",
      "印刷",
      "編輯",
      "校對"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字、圖片按規則排列組合，方便閱讀。",
        "explanation": "反義：排版是按規則有序排列，打亂是破壞秩序使之無序"
      }
    }
  }
}
```

---

## sense 10112, level 9

#### Pack A
### Level 9 (sense 10112, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "请把这张海报排版得漂亮些。",
  "hant": {
    "original_sentence": "請把這張海報排版得漂亮些。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "请把这张海报排版得漂亮些。",
  "chunks": [
    "请",
    "把这张海报",
    "排版得漂亮些"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "把这张海报",
    "请",
    "排版得漂亮些"
  ],
  "target_word": "排版",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "請把這張海報排版得漂亮些。",
    "chunks": [
      "請",
      "把這張海報",
      "排版得漂亮些"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "把這張海報",
      "請",
      "排版得漂亮些"
    ],
    "target_word": "排版",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这本书的排版看起来很舒服。",
  "hant": {
    "original_sentence": "這本書的排版看起來很舒服。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这本书的排版看起来很舒服。",
  "chunks": [
    "这本书",
    "的排版",
    "看起来很舒服"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "这本书",
    "看起来很舒服",
    "的排版"
  ],
  "target_word": "排版",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這本書的排版看起來很舒服。",
    "chunks": [
      "這本書",
      "的排版",
      "看起來很舒服"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "這本書",
      "看起來很舒服",
      "的排版"
    ],
    "target_word": "排版",
    "chunk_count": 3
  }
}
```

#### Pack B
### Level 9 (sense 10112, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "排版需要很多耐心。",
  "hant": {
    "original_sentence": "排版需要很多耐心。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "排版需要很多耐心。",
  "chunks": [
    "排版",
    "需要",
    "很多耐心"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "需要",
    "排版",
    "很多耐心"
  ],
  "target_word": "排版",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "排版需要很多耐心。",
    "chunks": [
      "排版",
      "需要",
      "很多耐心"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "需要",
      "排版",
      "很多耐心"
    ],
    "target_word": "排版",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "哥哥在大学学排版。",
  "hant": {
    "original_sentence": "哥哥在大學學排版。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "哥哥在大学学排版。",
  "chunks": [
    "哥哥",
    "在大学学",
    "排版"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "哥哥",
    "排版",
    "在大学学"
  ],
  "target_word": "排版",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "哥哥在大學學排版。",
    "chunks": [
      "哥哥",
      "在大學學",
      "排版"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "哥哥",
      "排版",
      "在大學學"
    ],
    "target_word": "排版",
    "chunk_count": 3
  }
}
```

---

## sense 10113, level 1

#### Pack A
### Level 1 (sense 10113, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "先河",
  "options": [
    "xiān hé",
    "xiān hě",
    "xiān hē",
    "xián hé"
  ],
  "correct_answer": "xiān hé",
  "word": "先河",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "先河",
    "options": [
      "xiān hé",
      "xiān hě",
      "xiān hē",
      "xián hé"
    ],
    "correct_answer": "xiān hé",
    "word": "先河",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "xiān hé",
  "options": [
    "先河",
    "河流",
    "选择",
    "制造"
  ],
  "correct_answer": "先河",
  "word": "先河",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "河流": "component",
    "选择": "component",
    "制造": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "xiān hé",
    "options": [
      "先河",
      "河流",
      "選擇",
      "製造"
    ],
    "correct_answer": "先河",
    "word": "先河",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "河流": "component",
      "选择": "component",
      "制造": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "先河",
  "toneless_pinyin": "xian he",
  "full_pinyin": "xiān hé",
  "options": [
    "11",
    "13",
    "14",
    "12"
  ],
  "correct_answer": "12",
  "option_labels": {
    "11": "high level (1) + high level (1)",
    "13": "high level (1) + dipping (3)",
    "14": "high level (1) + falling (4)",
    "12": "high level (1) + rising (2)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "先河",
    "toneless_pinyin": "xian he",
    "full_pinyin": "xiān hé",
    "options": [
      "11",
      "13",
      "14",
      "12"
    ],
    "correct_answer": "12",
    "option_labels": {
      "11": "high level (1) + high level (1)",
      "13": "high level (1) + dipping (3)",
      "14": "high level (1) + falling (4)",
      "12": "high level (1) + rising (2)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10113, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "先河",
  "options": [
    "xiān hé",
    "xiān hě",
    "xiān hē",
    "xián hé"
  ],
  "correct_answer": "xiān hé",
  "word": "先河",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "先河",
    "options": [
      "xiān hé",
      "xiān hě",
      "xiān hē",
      "xián hé"
    ],
    "correct_answer": "xiān hé",
    "word": "先河",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "xiān hé",
  "options": [
    "先河",
    "河流",
    "选择",
    "制造"
  ],
  "correct_answer": "先河",
  "word": "先河",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "河流": "component",
    "选择": "component",
    "制造": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "xiān hé",
    "options": [
      "先河",
      "河流",
      "選擇",
      "製造"
    ],
    "correct_answer": "先河",
    "word": "先河",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "河流": "component",
      "选择": "component",
      "制造": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "先河",
  "toneless_pinyin": "xian he",
  "full_pinyin": "xiān hé",
  "options": [
    "11",
    "13",
    "14",
    "12"
  ],
  "correct_answer": "12",
  "option_labels": {
    "11": "high level (1) + high level (1)",
    "13": "high level (1) + dipping (3)",
    "14": "high level (1) + falling (4)",
    "12": "high level (1) + rising (2)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "先河",
    "toneless_pinyin": "xian he",
    "full_pinyin": "xiān hé",
    "options": [
      "11",
      "13",
      "14",
      "12"
    ],
    "correct_answer": "12",
    "option_labels": {
      "11": "high level (1) + high level (1)",
      "13": "high level (1) + dipping (3)",
      "14": "high level (1) + falling (4)",
      "12": "high level (1) + rising (2)"
    },
    "syllable_count": 2
  }
}
```
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "先河",
  "pronunciation": "xiān hé",
  "ipa": "[ɕjɛn˥ xɤ˧˥]",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "鲜合",
    "先河",
    "险壑",
    "现核"
  ],
  "correct_answer": "先河",
  "explanation": "正确。目标词，读音 xiān hé。",
  "distractor_explanations": {
    "鲜合": "干扰项。读音 xiān hé，同音但非真实常用词，或为生造词，用于混淆视听。",
    "险壑": "干扰项。读音 xiǎn hè，声调不同，意为危险的沟壑，语义无关。",
    "现核": "干扰项。读音 xiàn hé，声调不同，语义不通。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "先河",
    "pronunciation": "xiān hé",
    "ipa": "[ɕjɛn˥ xɤ˧˥]",
    "syllable_count": 2,
    "audio_url": null,
    "options": [
      "鮮合",
      "先河",
      "險壑",
      "現核"
    ],
    "correct_answer": "先河",
    "explanation": "正確。目標詞，讀音 xiān hé。",
    "distractor_explanations": {
      "鲜合": "干擾項。讀音 xiān hé，同音但非真實常用詞，或為生造詞，用於混淆視聽。",
      "险壑": "干擾項。讀音 xiǎn hè，聲調不同，意為危險的溝壑，語義無關。",
      "现核": "干擾項。讀音 xiàn hé，聲調不同，語義不通。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10113, level 2

#### Pack A
### Level 2 (sense 10113, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "pronunciation": "xiān hé",
  "correct_definition": "先河比喻某一事业或行动的开创者或最早的做法。",
  "options": [
    "指对原有的技术或方法进行改进，使其更高效、更先进。",
    "先河比喻某一事业或行动的开创者或最早的做法。",
    "建造、建立，通常指有系统地搭建或形成某种结构。",
    "事物发展过程中方向或性质的改变，也指文章或话语中从一个话题转到另一个话题。"
  ],
  "hant": {
    "word": "先河",
    "pronunciation": "xiān hé",
    "correct_definition": "先河比喻某一事業或行動的開創者或最早的做法。",
    "options": [
      "指對原有的技術或方法進行改進，使其更高效、更先進。",
      "先河比喻某一事業或行動的開創者或最早的做法。",
      "建造、建立，通常指有系統地搭建或形成某種結構。",
      "事物發展過程中方向或性質的改變，也指文章或話語中從一個話題轉到另一個話題。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "pronunciation": "xiān hé",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "先河比喻某一事业或行动的开创者或最早的做法。",
        "to catalyze",
        "weather; how the sky is, like windy or rainy",
        "きちんと管理する"
      ],
      "correct_answer": "先河比喻某一事业或行动的开创者或最早的做法。"
    }
  },
  "hant": {
    "word": "先河",
    "pronunciation": "xiān hé",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "先河比喻某一事業或行動的開創者或最早的做法。",
          "to catalyze",
          "weather; how the sky is, like windy or rainy",
          "きちんと管理する"
        ],
        "correct_answer": "先河比喻某一事業或行動的開創者或最早的做法。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10113, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "pronunciation": "xiān hé",
  "correct_definition": "比喻某项事业或行动的开创者或最早的做法",
  "options": [
    "对事物或情况做出肯定或否定的认识、断定。",
    "比喻某项事业或行动的开创者或最早的做法",
    "言语动作谦虚、恭敬、友好的表现。",
    "禁止和限制，指不允许或加以约束。"
  ],
  "hant": {
    "word": "先河",
    "pronunciation": "xiān hé",
    "correct_definition": "比喻某項事業或行動的開創者或最早的做法",
    "options": [
      "對事物或情況做出肯定或否定的認識、斷定。",
      "比喻某項事業或行動的開創者或最早的做法",
      "言語動作謙虛、恭敬、友好的表現。",
      "禁止和限制，指不允許或加以約束。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "pronunciation": "xiān hé",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "比喻某项事业或行动的开创者或最早的做法",
        "織物",
        "入れる；手にある物を別の場所に移すこと",
        "一群共享文化、历史和价值观的人所组成的群体"
      ],
      "correct_answer": "比喻某项事业或行动的开创者或最早的做法"
    }
  },
  "hant": {
    "word": "先河",
    "pronunciation": "xiān hé",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "比喻某項事業或行動的開創者或最早的做法",
          "織物",
          "入れる；手にある物を別の場所に移すこと",
          "一群共享文化、歷史和價值觀的人所組成的群體"
        ],
        "correct_answer": "比喻某項事業或行動的開創者或最早的做法"
      }
    }
  }
}
```

---

## sense 10113, level 3

#### Pack A
### Level 3 (sense 10113, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术___。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "先河",
  "options": [
    "局面",
    "前景",
    "先河",
    "先锋"
  ],
  "explanation": "正确。符合语境，比喻开创性的做法。",
  "distractor_tags": {},
  "word_definition": "比喻某项事业或行动的开创者或最早的做法",
  "target_word": "先河",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術___。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "先河",
    "options": [
      "局面",
      "前景",
      "先河",
      "先鋒"
    ],
    "explanation": "正確。符合語境，比喻開創性的做法。",
    "distractor_tags": {},
    "word_definition": "比喻某項事業或行動的開創者或最早的做法",
    "target_word": "先河"
  }
}
```

#### Pack B
### Level 3 (sense 10113, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "老师表扬了他，说他开了___。",
  "original_sentence": "老师表扬了他，说他开了先河。",
  "correct_answer": "先河",
  "options": [
    "先鞭",
    "先锋",
    "先声",
    "先河"
  ],
  "explanation": "正确选项。“开先河”为固定搭配，意为开创某种事业或做法，符合老师表扬的语境。",
  "distractor_tags": {},
  "word_definition": "先河比喻某一事业或行动的开创者或最早的做法。",
  "target_word": "先河",
  "hant": {
    "sentence_with_blank": "老師表揚了他，說他開了___。",
    "original_sentence": "老師表揚了他，說他開了先河。",
    "correct_answer": "先河",
    "options": [
      "先鞭",
      "先鋒",
      "先聲",
      "先河"
    ],
    "explanation": "正確選項。“開先河”為固定搭配，意為開創某種事業或做法，符合老師表揚的語境。",
    "distractor_tags": {},
    "word_definition": "先河比喻某一事業或行動的開創者或最早的做法。",
    "target_word": "先河"
  }
}
```

---

## sense 10113, level 4

#### Pack A
### Level 4 (sense 10113, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___已开，同学们都跟着做。",
  "original_sentence": "先河已开，同学们都跟着做。",
  "target_word": "先河",
  "word": "先河",
  "answer": {
    "accepted": [
      "先河"
    ],
    "accepted_normalized": [
      "先河"
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
    "sentence_with_blank": "___已開，同學們都跟著做。",
    "original_sentence": "先河已開，同學們都跟著做。",
    "target_word": "先河",
    "word": "先河",
    "answer": {
      "accepted": [
        "先河"
      ],
      "accepted_normalized": [
        "先河"
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
  "sentence_with_blank": "___一开，后面的事就好办了。",
  "original_sentence": "先河一开，后面的事就好办了。",
  "target_word": "先河",
  "word": "先河",
  "answer": {
    "accepted": [
      "先河"
    ],
    "accepted_normalized": [
      "先河"
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
    "sentence_with_blank": "___一開，後面的事就好辦了。",
    "original_sentence": "先河一開，後面的事就好辦了。",
    "target_word": "先河",
    "word": "先河",
    "answer": {
      "accepted": [
        "先河"
      ],
      "accepted_normalized": [
        "先河"
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
### Level 4 (sense 10113, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "他率先尝试新方法，开创了这一领域的___。",
  "original_sentence": "他率先尝试新方法，开创了这一领域的先河。",
  "target_word": "先河",
  "word": "先河",
  "answer": {
    "accepted": [
      "先河",
      "开创先河",
      "开启先河",
      "敢为先河"
    ],
    "accepted_normalized": [
      "先河",
      "开创先河",
      "开启先河",
      "敢为先河"
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
    "sentence_with_blank": "他率先嚐試新方法，開創了這一領域的___。",
    "original_sentence": "他率先嚐試新方法，開創了這一領域的先河。",
    "target_word": "先河",
    "word": "先河",
    "answer": {
      "accepted": [
        "先河",
        "開創先河",
        "開啟先河",
        "敢為先河"
      ],
      "accepted_normalized": [
        "先河",
        "開創先河",
        "開啟先河",
        "敢為先河"
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
  "sentence_with_blank": "这家店的服务方式开了行业___。",
  "original_sentence": "这家店的服务方式开了行业先河。",
  "target_word": "先河",
  "word": "先河",
  "answer": {
    "accepted": [
      "先河",
      "开创先河",
      "开启先河",
      "敢为先河"
    ],
    "accepted_normalized": [
      "先河",
      "开创先河",
      "开启先河",
      "敢为先河"
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
    "sentence_with_blank": "這家店的服務方式開了行業___。",
    "original_sentence": "這家店的服務方式開了行業先河。",
    "target_word": "先河",
    "word": "先河",
    "answer": {
      "accepted": [
        "先河",
        "開創先河",
        "開啟先河",
        "敢為先河"
      ],
      "accepted_normalized": [
        "先河",
        "開創先河",
        "開啟先河",
        "敢為先河"
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
