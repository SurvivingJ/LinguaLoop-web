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


## sense 19859, level 1

#### Pack A
### Level 1 (sense 19859, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "要",
  "pronunciation": "yào",
  "ipa": "[jɑʊ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "要",
    "摇",
    "妖",
    "咬"
  ],
  "correct_answer": "要",
  "explanation": "正确。读 yào，表示希望、需要或请求。",
  "distractor_explanations": {
    "妖": "错误。读 yāo，指怪异的事物，声调为第一声。",
    "摇": "错误。读 yáo，指摆动、晃动，声调为第二声。",
    "咬": "错误。读 yǎo，指用牙齿夹住，声调为第三声。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "要",
    "pronunciation": "yào",
    "ipa": "[jɑʊ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "要",
      "搖",
      "妖",
      "咬"
    ],
    "correct_answer": "要",
    "explanation": "正確。讀 yào，表示希望、需要或請求。",
    "distractor_explanations": {
      "妖": "錯誤。讀 yāo，指怪異的事物，聲調為第一聲。",
      "摇": "錯誤。讀 yáo，指擺動、晃動，聲調為第二聲。",
      "咬": "錯誤。讀 yǎo，指用牙齒夾住，聲調為第三聲。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19859, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "要",
  "pronunciation": "yào",
  "ipa": "[jɑʊ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "摇",
    "腰",
    "咬",
    "要"
  ],
  "correct_answer": "要",
  "explanation": "正确。'要'读作 yào，表示希望、需要或打算做某事。",
  "distractor_explanations": {
    "腰": "错误。'腰'读作 yāo（第一声），指身体部位，声调与'要'不同。",
    "摇": "错误。'摇'读作 yáo（第二声），表示摆动，声调与'要'不同。",
    "咬": "错误。'咬'读作 yǎo（第三声），表示用牙齿夹住，声调与'要'不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "要",
    "pronunciation": "yào",
    "ipa": "[jɑʊ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "搖",
      "腰",
      "咬",
      "要"
    ],
    "correct_answer": "要",
    "explanation": "正確。'要'讀作 yào，表示希望、需要或打算做某事。",
    "distractor_explanations": {
      "腰": "錯誤。'腰'讀作 yāo（第一聲），指身體部位，聲調與'要'不同。",
      "摇": "錯誤。'搖'讀作 yáo（第二聲），表示擺動，聲調與'要'不同。",
      "咬": "錯誤。'咬'讀作 yǎo（第三聲），表示用牙齒夾住，聲調與'要'不同。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19859, level 3

#### Pack A
### Level 3 (sense 19859, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "我周末___去图书馆看新书。",
  "original_sentence": "我周末要去图书馆看新书。",
  "correct_answer": "要",
  "options": [
    "配",
    "肯",
    "要",
    "敢"
  ],
  "explanation": "正确。'要'在此处表示主语的主观意愿或打算，符合周末去图书馆的语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我週末___去圖書館看新書。",
    "original_sentence": "我週末要去圖書館看新書。",
    "correct_answer": "要",
    "options": [
      "配",
      "肯",
      "要",
      "敢"
    ],
    "explanation": "正確。'要'在此處表示主語的主觀意願或打算，符合週末去圖書館的語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```

#### Pack B
### Level 3 (sense 19859, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "我___去图书馆借本书。",
  "original_sentence": "我要去图书馆借本书。",
  "correct_answer": "要",
  "options": [
    "要",
    "善于",
    "忙于",
    "敢于"
  ],
  "explanation": "正确。表示主观意愿或计划，符合语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我___去圖書館借本書。",
    "original_sentence": "我要去圖書館借本書。",
    "correct_answer": "要",
    "options": [
      "要",
      "善於",
      "忙於",
      "敢於"
    ],
    "explanation": "正確。表示主觀意願或計劃，符合語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我___和你做朋友。",
  "original_sentence": "我要和你做朋友。",
  "correct_answer": "要",
  "options": [
    "许",
    "配",
    "敢",
    "要"
  ],
  "explanation": "正确选项。“要”在此处表示主观意愿，符合“和你做朋友”的积极语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我___和你做朋友。",
    "original_sentence": "我要和你做朋友。",
    "correct_answer": "要",
    "options": [
      "許",
      "配",
      "敢",
      "要"
    ],
    "explanation": "正確選項。“要”在此處表示主觀意願，符合“和你做朋友”的積極語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```

---

## sense 19859, level 7

#### Pack A
### Level 7 (sense 19859, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们要把明天教室打扫干净。",
      "is_correct": false,
      "error_description": "时间状语“明天”位置错误。在“把”字句中，时间状语应放在“把”字之前或主语之后、情态动词之前，正确语序为“我们明天要把教室打扫干净。”"
    },
    {
      "text": "弟弟哭着要妈妈给他买玩具。",
      "is_correct": true
    },
    {
      "text": "你刚才说要喝点什么饮料？",
      "is_correct": true
    },
    {
      "text": "这本书我要留着以后慢慢看。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們要把明天教室打掃乾淨。",
        "is_correct": false,
        "error_description": "時間狀語“明天”位置錯誤。在“把”字句中，時間狀語應放在“把”字之前或主語之後、情態動詞之前，正確語序為“我們明天要把教室打掃乾淨。”"
      },
      {
        "text": "弟弟哭著要媽媽給他買玩具。",
        "is_correct": true
      },
      {
        "text": "你剛才說要喝點什麼飲料？",
        "is_correct": true
      },
      {
        "text": "這本書我要留著以後慢慢看。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19859, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他想要一个红色的书包。",
      "is_correct": true
    },
    {
      "text": "我要把这本书看完。",
      "is_correct": true
    },
    {
      "text": "我要去图书馆借本书。",
      "is_correct": true
    },
    {
      "text": "他要买三本红色的书包。",
      "is_correct": false,
      "error_description": "量词使用错误。“书包”的量词应该是“个”，不能用“本”。“本”通常用来修饰书、杂志等。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他想要一個紅色的書包。",
        "is_correct": true
      },
      {
        "text": "我要把這本書看完。",
        "is_correct": true
      },
      {
        "text": "我要去圖書館借本書。",
        "is_correct": true
      },
      {
        "text": "他要買三本紅色的書包。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“書包”的量詞應該是“個”，不能用“本”。“本”通常用來修飾書、雜誌等。"
      }
    ]
  }
}
```

---

## sense 19860, level 1

#### Pack A
### Level 1 (sense 19860, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "pronunciation": "luàn",
  "ipa": "[luan˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "卵",
    "乱",
    "峦",
    "栾"
  ],
  "correct_answer": "乱",
  "explanation": "正确选项：“乱”读作 luàn（第四声），符合目标词的发音与字形。",
  "distractor_explanations": {
    "卵": "声调错误：“卵”读作 luǎn（第三声），指蛋或动物生殖细胞，与“乱”（luàn，第四声）声调不同，意义完全不同。",
    "峦": "声调错误：“峦”读作 luán（第二声），指连绵的山峰，与“乱”（luàn，第四声）声调不同，意义完全不同。",
    "栾": "声调错误：“栾”读作 luán（第二声），多用于姓氏或植物名，与“乱”（luàn，第四声）声调不同，意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "亂",
    "pronunciation": "luàn",
    "ipa": "[luan˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "卵",
      "亂",
      "巒",
      "欒"
    ],
    "correct_answer": "亂",
    "explanation": "正確選項：“亂”讀作 luàn（第四聲），符合目標詞的發音與字形。",
    "distractor_explanations": {
      "卵": "聲調錯誤：“卵”讀作 luǎn（第三聲），指蛋或動物生殖細胞，與“亂”（luàn，第四聲）聲調不同，意義完全不同。",
      "峦": "聲調錯誤：“巒”讀作 luán（第二聲），指連綿的山峰，與“亂”（luàn，第四聲）聲調不同，意義完全不同。",
      "栾": "聲調錯誤：“欒”讀作 luán（第二聲），多用於姓氏或植物名，與“亂”（luàn，第四聲）聲調不同，意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19860, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "pronunciation": "luàn",
  "ipa": "[luan˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "峦",
    "卵",
    "乱",
    "栾"
  ],
  "correct_answer": "乱",
  "explanation": "正确。'乱'读作 luàn，表示没有条理、秩序或混乱的状态。",
  "distractor_explanations": {
    "峦": "错误。'峦'读作 luán（第二声），指连绵的山，与'乱'声调不同，意义也不同。",
    "卵": "错误。'卵'读作 luǎn（第三声），指蛋或动物的卵，与'乱'声调不同，意义完全不同。",
    "栾": "错误。'栾'读作 luān（第一声），多用于树木名或姓氏，与'乱'声调不同，意义无关。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "亂",
    "pronunciation": "luàn",
    "ipa": "[luan˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "巒",
      "卵",
      "亂",
      "欒"
    ],
    "correct_answer": "亂",
    "explanation": "正確。'亂'讀作 luàn，表示沒有條理、秩序或混亂的狀態。",
    "distractor_explanations": {
      "峦": "錯誤。'巒'讀作 luán（第二聲），指連綿的山，與'亂'聲調不同，意義也不同。",
      "卵": "錯誤。'卵'讀作 luǎn（第三聲），指蛋或動物的卵，與'亂'聲調不同，意義完全不同。",
      "栾": "錯誤。'欒'讀作 luān（第一聲），多用於樹木名或姓氏，與'亂'聲調不同，意義無關。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19860, level 6

#### Pack A
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我不怕乱得，就怕没头绪。",
      "is_correct": false
    },
    {
      "text": "我不怕一乱，就怕没头绪。",
      "is_correct": false
    },
    {
      "text": "不怕没头绪，乱我。",
      "is_correct": false
    },
    {
      "text": "我不怕乱，就怕没头绪。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：形容词“乱”表示状态，后面不能直接加结构助词“得”来连接后续成分，此处“得”字多余且破坏了句法结构。 语序错误：破坏了“主题—评论”结构，“乱”作为形容词谓语，其主语（如“情况”或隐含的“它”）缺失且语序混乱，导致句意不通。 量词使用错误：“乱”是形容词，表示混乱的状态，不能受数量短语“一”的直接修饰，此处量词“一”误用。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "我不怕亂得，就怕沒頭緒。",
        "is_correct": false
      },
      {
        "text": "我不怕一亂，就怕沒頭緒。",
        "is_correct": false
      },
      {
        "text": "不怕沒頭緒，亂我。",
        "is_correct": false
      },
      {
        "text": "我不怕亂，就怕沒頭緒。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：形容詞“亂”表示狀態，後面不能直接加結構助詞“得”來連線後續成分，此處“得”字多餘且破壞了句法結構。 語序錯誤：破壞了“主題—評論”結構，“亂”作為形容詞謂語，其主語（如“情況”或隱含的“它”）缺失且語序混亂，導致句意不通。 量詞使用錯誤：“亂”是形容詞，表示混亂的狀態，不能受數量短語“一”的直接修飾，此處量詞“一”誤用。",
    "target_word": "亂"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "整齐",
    "繁杂",
    "凌乱",
    "拥挤"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义：指有条理、有秩序，与'没有条理、混乱'构成反义"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "整齊",
      "繁雜",
      "凌亂",
      "擁擠"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義：指有條理、有秩序，與'沒有條理、混亂'構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "复杂",
    "整齐",
    "稀疏",
    "干净"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义项：指事物有条理、有秩序，与“没有条理”构成反义"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "複雜",
      "整齊",
      "稀疏",
      "乾淨"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義項：指事物有條理、有秩序，與“沒有條理”構成反義"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他提出了一个很乱的观点。",
      "is_correct": true
    },
    {
      "text": "他提出了一个很乱着的观点。",
      "is_correct": false
    },
    {
      "text": "他提出了很乱的一个观点。",
      "is_correct": false
    },
    {
      "text": "他提出了一张很乱的观点。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'观点'应使用量词'个'，不能使用用于纸张或扁平物体的'张'。 体标选用错误。'乱'是性质形容词，前面已有程度副词'很'，后面不能加动态助词'着'来表示动作的持续。 语序错误。在汉语中，形容词定语'很乱'通常应放在数量词'一个'之后，即'一个很乱的观点'，放在数量词之前不符合常规语序。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "他提出了一個很亂的觀點。",
        "is_correct": true
      },
      {
        "text": "他提出了一個很亂著的觀點。",
        "is_correct": false
      },
      {
        "text": "他提出了很亂的一個觀點。",
        "is_correct": false
      },
      {
        "text": "他提出了一張很亂的觀點。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'觀點'應使用量詞'個'，不能使用用於紙張或扁平物體的'張'。 體標選用錯誤。'亂'是性質形容詞，前面已有程度副詞'很'，後面不能加動態助詞'著'來表示動作的持續。 語序錯誤。在漢語中，形容詞定語'很亂'通常應放在數量詞'一個'之後，即'一個很亂的觀點'，放在數量詞之前不符合常規語序。",
    "target_word": "亂"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "整齐",
    "详细",
    "复杂",
    "模糊"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义项：指事物有秩序、有条理的状态，与目标词构成反义"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "整齊",
      "詳細",
      "複雜",
      "模糊"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義項：指事物有秩序、有條理的狀態，與目標詞構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "单调",
    "安静",
    "整齐",
    "干净"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "同义项：指事物有秩序、有条理，与“乱”构成反义关系"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "單調",
      "安靜",
      "整齊",
      "乾淨"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "同義項：指事物有秩序、有條理，與“亂”構成反義關係"
      }
    }
  }
}
```

---

## sense 19860, level 7

#### Pack A
### Level 7 (sense 19860, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这篇文章的逻辑太乱了。",
      "is_correct": true
    },
    {
      "text": "大家七嘴八舌，把会场搞乱了。",
      "is_correct": true
    },
    {
      "text": "他把弄乱了房间，妈妈很生气。",
      "is_correct": false,
      "error_description": "“把”字句中，宾语应放在“把”字之后、动词之前，不能放在动补结构之后。"
    },
    {
      "text": "聚会结束后，现场变得很乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這篇文章的邏輯太亂了。",
        "is_correct": true
      },
      {
        "text": "大家七嘴八舌，把會場搞亂了。",
        "is_correct": true
      },
      {
        "text": "他把弄亂了房間，媽媽很生氣。",
        "is_correct": false,
        "error_description": "“把”字句中，賓語應放在“把”字之後、動詞之前，不能放在動補結構之後。"
      },
      {
        "text": "聚會結束後，現場變得很亂。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19860, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他把房间弄乱得很。",
      "is_correct": false,
      "error_description": "程度副词“非常”应放在形容词“乱”的前面作状语，不能放在句末用“得很”来修饰“把”字句的结果补语。"
    },
    {
      "text": "心里很乱，不想说话。",
      "is_correct": true
    },
    {
      "text": "数据要干净，不能乱。",
      "is_correct": true
    },
    {
      "text": "他把房间弄得非常乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把房間弄亂得很。",
        "is_correct": false,
        "error_description": "程度副詞“非常”應放在形容詞“亂”的前面作狀語，不能放在句末用“得很”來修飾“把”字句的結果補語。"
      },
      {
        "text": "心裡很亂，不想說話。",
        "is_correct": true
      },
      {
        "text": "資料要乾淨，不能亂。",
        "is_correct": true
      },
      {
        "text": "他把房間弄得非常亂。",
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
      "text": "他把房间乱弄了。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，形容词“乱”作结果补语时，必须紧跟在动词“弄”之后，不能放在动词前面。"
    },
    {
      "text": "别把现场弄乱。",
      "is_correct": true
    },
    {
      "text": "他正看着很乱的线。",
      "is_correct": true
    },
    {
      "text": "她看着很乱的桌面。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把房間亂弄了。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，形容詞“亂”作結果補語時，必須緊跟在動詞“弄”之後，不能放在動詞前面。"
      },
      {
        "text": "別把現場弄亂。",
        "is_correct": true
      },
      {
        "text": "他正看著很亂的線。",
        "is_correct": true
      },
      {
        "text": "她看著很亂的桌面。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 19867, level 1

#### Pack A
### Level 1 (sense 19867, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "才",
  "pronunciation": "cái",
  "ipa": "[t͡sʰai˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "菜",
    "才",
    "采",
    "猜"
  ],
  "correct_answer": "才",
  "explanation": "声调为阳平，副词，表示事情刚刚发生，为正确选项。",
  "distractor_explanations": {
    "猜": "声调为阴平，意为猜测，与目标词阳平声调不同。",
    "采": "声调为上声，意为采摘或采集，与目标词阳平声调不同。",
    "菜": "声调为去声，意为蔬菜，与目标词阳平声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "才",
    "pronunciation": "cái",
    "ipa": "[t͡sʰai˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "菜",
      "才",
      "採",
      "猜"
    ],
    "correct_answer": "才",
    "explanation": "聲調為陽平，副詞，表示事情剛剛發生，為正確選項。",
    "distractor_explanations": {
      "猜": "聲調為陰平，意為猜測，與目標詞陽平聲調不同。",
      "采": "聲調為上聲，意為採摘或採集，與目標詞陽平聲調不同。",
      "菜": "聲調為去聲，意為蔬菜，與目標詞陽平聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19867, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "才",
  "pronunciation": "cái",
  "ipa": "[t͡sʰaɪ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "菜",
    "才",
    "采",
    "猜"
  ],
  "correct_answer": "才",
  "explanation": "正确。“才”读第二声（cái），在此处作副词，表示事情刚刚发生。",
  "distractor_explanations": {
    "猜": "声调错误。“猜”读第一声（cāi），意思是推测；而目标词“才”读第二声（cái）。",
    "采": "声调错误。“采”读第三声（cǎi），意思是摘取或收集；而目标词“才”读第二声（cái）。",
    "菜": "声调错误。“菜”读第四声（cài），意思是蔬菜或菜肴；而目标词“才”读第二声（cái）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "才",
    "pronunciation": "cái",
    "ipa": "[t͡sʰaɪ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "菜",
      "才",
      "採",
      "猜"
    ],
    "correct_answer": "才",
    "explanation": "正確。“才”讀第二聲（cái），在此處作副詞，表示事情剛剛發生。",
    "distractor_explanations": {
      "猜": "聲調錯誤。“猜”讀第一聲（cāi），意思是推測；而目標詞“才”讀第二聲（cái）。",
      "采": "聲調錯誤。“採”讀第三聲（cǎi），意思是摘取或收集；而目標詞“才”讀第二聲（cái）。",
      "菜": "聲調錯誤。“菜”讀第四聲（cài），意思是蔬菜或菜餚；而目標詞“才”讀第二聲（cái）。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19867, level 6

#### Pack A
### Level 6 (sense 19867, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "才",
  "relation": "antonym",
  "options": [
    "正",
    "就",
    "常",
    "将"
  ],
  "correct_answer": "就",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示事情刚刚发生，或强调事情发生、结束得很早。",
      "explanation": "反义项：强调事情发生得早或快，与“才”表示刚刚或发生得晚构成反义"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "正",
      "就",
      "常",
      "將"
    ],
    "correct_answer": "就",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示事情剛剛發生，或強調事情發生、結束得很早。",
        "explanation": "反義項：強調事情發生得早或快，與“才”表示剛剛或發生得晚構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "才",
  "relation": "antonym",
  "options": [
    "总是",
    "刚刚",
    "已经",
    "马上"
  ],
  "correct_answer": "已经",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示事情刚刚发生，或强调事情发生、结束得很早。",
      "explanation": "反义项：'已经'表示事情早已完成，与'才'表示事情刚刚发生构成反义关系。"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "總是",
      "剛剛",
      "已經",
      "馬上"
    ],
    "correct_answer": "已經",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示事情剛剛發生，或強調事情發生、結束得很早。",
        "explanation": "反義項：'已經'表示事情早已完成，與'才'表示事情剛剛發生構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19867, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他才睡过了，就梦到了妈妈。",
      "is_correct": false
    },
    {
      "text": "他才睡着，就梦到了妈妈。",
      "is_correct": true
    },
    {
      "text": "他才睡起，就梦到了妈妈。",
      "is_correct": false
    },
    {
      "text": "他睡着才，就梦到了妈妈。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“才”表示动作刚刚发生，强调时间近；“过”表示过去的经历。两者连用造成体貌冲突，语义不自然。 语序错误：副词“才”修饰动词时，必须放在动词“睡着”之前，不能放在动词之后，此处语序错误。 结果补语误用：“睡”表示进入睡眠状态，其结果补语应为“着”，表示动作达到目的；“起”不能作“睡”的结果补语，此处动补搭配错误。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "他才睡過了，就夢到了媽媽。",
        "is_correct": false
      },
      {
        "text": "他才睡著，就夢到了媽媽。",
        "is_correct": true
      },
      {
        "text": "他才睡起，就夢到了媽媽。",
        "is_correct": false
      },
      {
        "text": "他睡著才，就夢到了媽媽。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“才”表示動作剛剛發生，強調時間近；“過”表示過去的經歷。兩者連用造成體貌衝突，語義不自然。 語序錯誤：副詞“才”修飾動詞時，必須放在動詞“睡著”之前，不能放在動詞之後，此處語序錯誤。 結果補語誤用：“睡”表示進入睡眠狀態，其結果補語應為“著”，表示動作達到目的；“起”不能作“睡”的結果補語，此處動補搭配錯誤。",
    "target_word": "才"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他才真正哭出来，那一刻就释怀了。",
      "is_correct": true
    },
    {
      "text": "他才真正哭起去，那一刻就释怀了。",
      "is_correct": false
    },
    {
      "text": "他才真正哭出来着，那一刻就释怀了。",
      "is_correct": false
    },
    {
      "text": "才他真正哭出来，那一刻就释怀了。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：副词“才”应当放在主语“他”之后，不能放在主语之前。 体标选用错误：“才”强调动作刚刚发生或结束，不能与表示动作持续的体标记“着”搭配使用。 方向补语误用：“起来”表示动作开始或情绪爆发，符合语境；“起去”不是合法的汉语趋向补语，且方向意义错误。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "他才真正哭出來，那一刻就釋懷了。",
        "is_correct": true
      },
      {
        "text": "他才真正哭起去，那一刻就釋懷了。",
        "is_correct": false
      },
      {
        "text": "他才真正哭出來著，那一刻就釋懷了。",
        "is_correct": false
      },
      {
        "text": "才他真正哭出來，那一刻就釋懷了。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：副詞“才”應當放在主語“他”之後，不能放在主語之前。 體標選用錯誤：“才”強調動作剛剛發生或結束，不能與表示動作持續的體標記“著”搭配使用。 方向補語誤用：“起來”表示動作開始或情緒爆發，符合語境；“起去”不是合法的漢語趨向補語，且方向意義錯誤。",
    "target_word": "才"
  }
}
```

---

## sense 19867, level 7

#### Pack A
### Level 7 (sense 19867, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "现在才八点，他就出门了。",
      "is_correct": true
    },
    {
      "text": "他才昨天告诉我这个好消息。",
      "is_correct": false,
      "error_description": "副词“才”表示事情发生得晚或慢时，应放在时间状语之后。正确语序为“他昨天才告诉我这个好消息”。"
    },
    {
      "text": "你才看过这部电影吗？",
      "is_correct": true
    },
    {
      "text": "他昨天才告诉我这个好消息。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "現在才八點，他就出門了。",
        "is_correct": true
      },
      {
        "text": "他才昨天告訴我這個好訊息。",
        "is_correct": false,
        "error_description": "副詞“才”表示事情發生得晚或慢時，應放在時間狀語之後。正確語序為“他昨天才告訴我這個好訊息”。"
      },
      {
        "text": "你才看過這部電影嗎？",
        "is_correct": true
      },
      {
        "text": "他昨天才告訴我這個好訊息。",
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
      "text": "他才来不久，还在熟悉环境。",
      "is_correct": true
    },
    {
      "text": "才下课，同学们就跑去玩了。",
      "is_correct": true
    },
    {
      "text": "他才不久来，还在熟悉环境。",
      "is_correct": false,
      "error_description": "语序错误。'不久'作为时间补语，应该放在动词'来'的后面，不能放在'才'和动词之间。"
    },
    {
      "text": "才刚开学，你就想家了吗？",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他才來不久，還在熟悉環境。",
        "is_correct": true
      },
      {
        "text": "才下課，同學們就跑去玩了。",
        "is_correct": true
      },
      {
        "text": "他才不久來，還在熟悉環境。",
        "is_correct": false,
        "error_description": "語序錯誤。'不久'作為時間補語，應該放在動詞'來'的後面，不能放在'才'和動詞之間。"
      },
      {
        "text": "才剛開學，你就想家了嗎？",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19867, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我才看过那部感人的电影。",
      "is_correct": true
    },
    {
      "text": "他才给好朋友发了消息。",
      "is_correct": true
    },
    {
      "text": "他才把秘密告诉了朋友。",
      "is_correct": true
    },
    {
      "text": "他才昨天给好朋友发了消息。",
      "is_correct": false,
      "error_description": "语序错误。时间状语“昨天”应该放在副词“才”的前面，正确语序为“主语 + 时间 + 才 + 动词短语”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我才看過那部感人的電影。",
        "is_correct": true
      },
      {
        "text": "他才給好朋友發了訊息。",
        "is_correct": true
      },
      {
        "text": "他才把秘密告訴了朋友。",
        "is_correct": true
      },
      {
        "text": "他才昨天給好朋友發了訊息。",
        "is_correct": false,
        "error_description": "語序錯誤。時間狀語“昨天”應該放在副詞“才”的前面，正確語序為“主語 + 時間 + 才 + 動詞短語”。"
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
      "text": "他才真正哭出来，那一刻就释怀了。",
      "is_correct": true
    },
    {
      "text": "我才拒绝了那个无聊的邀请。",
      "is_correct": true
    },
    {
      "text": "他才感动得流下了眼泪。",
      "is_correct": true
    },
    {
      "text": "他才昨天把那本有趣的书看完。",
      "is_correct": false,
      "error_description": "语序错误。时间状语“昨天”应该放在副词“才”的前面，正确的写法是“他昨天才把那本有趣的书看完”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他才真正哭出來，那一刻就釋懷了。",
        "is_correct": true
      },
      {
        "text": "我才拒絕了那個無聊的邀請。",
        "is_correct": true
      },
      {
        "text": "他才感動得流下了眼淚。",
        "is_correct": true
      },
      {
        "text": "他才昨天把那本有趣的書看完。",
        "is_correct": false,
        "error_description": "語序錯誤。時間狀語“昨天”應該放在副詞“才”的前面，正確的寫法是“他昨天才把那本有趣的書看完”。"
      }
    ]
  }
}
```

---

## sense 19870, level 1

#### Pack A
### Level 1 (sense 19870, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "也",
  "pronunciation": "yě",
  "ipa": "[jɛ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "耶",
    "也",
    "爷",
    "夜"
  ],
  "correct_answer": "也",
  "explanation": "正确。“也”读第三声（yě），是表示同样、并列的副词。",
  "distractor_explanations": {
    "耶": "声调错误。“耶”读第一声（yē），常用于音译词或句末语气词，而目标词“也”读第三声（yě）。",
    "爷": "声调错误。“爷”读第二声（yé），指长辈或尊称，而目标词“也”读第三声（yě）。",
    "夜": "声调错误。“夜”读第四声（yè），指从天黑到天亮的时间，而目标词“也”读第三声（yě）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "也",
    "pronunciation": "yě",
    "ipa": "[jɛ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "耶",
      "也",
      "爺",
      "夜"
    ],
    "correct_answer": "也",
    "explanation": "正確。“也”讀第三聲（yě），是表示同樣、並列的副詞。",
    "distractor_explanations": {
      "耶": "聲調錯誤。“耶”讀第一聲（yē），常用於音譯詞或句末語氣詞，而目標詞“也”讀第三聲（yě）。",
      "爷": "聲調錯誤。“爺”讀第二聲（yé），指長輩或尊稱，而目標詞“也”讀第三聲（yě）。",
      "夜": "聲調錯誤。“夜”讀第四聲（yè），指從天黑到天亮的時間，而目標詞“也”讀第三聲（yě）。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19870, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "也",
  "pronunciation": "yě",
  "ipa": "[jɛ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "爷",
    "叶",
    "也",
    "夜"
  ],
  "correct_answer": "也",
  "explanation": "正确。读音为 yě，表示同样、并列。",
  "distractor_explanations": {
    "爷": "错误。读音为 yé，二声，指父亲或长辈，声调不同。",
    "夜": "错误。读音为 yè，四声，指从天黑到天亮的时间，声调不同。",
    "叶": "错误。读音为 yè，四声，指植物的叶子，声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "也",
    "pronunciation": "yě",
    "ipa": "[jɛ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "爺",
      "葉",
      "也",
      "夜"
    ],
    "correct_answer": "也",
    "explanation": "正確。讀音為 yě，表示同樣、並列。",
    "distractor_explanations": {
      "爷": "錯誤。讀音為 yé，二聲，指父親或長輩，聲調不同。",
      "夜": "錯誤。讀音為 yè，四聲，指從天黑到天亮的時間，聲調不同。",
      "叶": "錯誤。讀音為 yè，四聲，指植物的葉子，聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```

---
