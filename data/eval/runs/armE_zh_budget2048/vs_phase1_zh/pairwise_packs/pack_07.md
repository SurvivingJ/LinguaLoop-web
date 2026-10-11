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


## sense 11319, level 7

#### Pack A
### Level 7 (sense 11319, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种强效感冒药效果好。",
      "is_correct": true
    },
    {
      "text": "医生给我开了一只强效止痛药。",
      "is_correct": false,
      "error_description": "量词“只”使用错误，修饰药物应使用“盒”、“瓶”或“粒”等合适的量词。"
    },
    {
      "text": "我们采用了强效疗法。",
      "is_correct": true
    },
    {
      "text": "这药以前用过，很强效。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種強效感冒藥效果好。",
        "is_correct": true
      },
      {
        "text": "醫生給我開了一隻強效止痛藥。",
        "is_correct": false,
        "error_description": "量詞“只”使用錯誤，修飾藥物應使用“盒”、“瓶”或“粒”等合適的量詞。"
      },
      {
        "text": "我們採用了強效療法。",
        "is_correct": true
      },
      {
        "text": "這藥以前用過，很強效。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 11319, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
      "is_correct": true
    },
    {
      "text": "该复方制剂具有强效的解热镇痛作用。",
      "is_correct": true
    },
    {
      "text": "强效的这种感冒药效果很好。",
      "is_correct": false,
      "error_description": "语序错误。指示代词“这种”应放在形容词“强效的”之前，正确语序为“这种强效的感冒药”。"
    },
    {
      "text": "该新型抗菌药物具有强效的抑菌作用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
        "is_correct": true
      },
      {
        "text": "該複方製劑具有強效的解熱鎮痛作用。",
        "is_correct": true
      },
      {
        "text": "強效的這種感冒藥效果很好。",
        "is_correct": false,
        "error_description": "語序錯誤。指示代詞“這種”應放在形容詞“強效的”之前，正確語序為“這種強效的感冒藥”。"
      },
      {
        "text": "該新型抗菌藥物具有強效的抑菌作用。",
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
      "text": "医生给病人开了强效的一种新药。",
      "is_correct": false,
      "error_description": "数量短语“一种”应放在形容词“强效”之前，正确的语序为“一种强效的新药”。"
    },
    {
      "text": "药理实验证实该提取物具有强效的抗炎活性。",
      "is_correct": true
    },
    {
      "text": "研发团队致力于开发具有强效靶向作用的创新药物。",
      "is_correct": true
    },
    {
      "text": "该新型抗真菌药物具有强效的抑菌作用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "醫生給病人開了強效的一種新藥。",
        "is_correct": false,
        "error_description": "數量短語“一種”應放在形容詞“強效”之前，正確的語序為“一種強效的新藥”。"
      },
      {
        "text": "藥理實驗證實該提取物具有強效的抗炎活性。",
        "is_correct": true
      },
      {
        "text": "研發團隊致力於開發具有強效靶向作用的創新藥物。",
        "is_correct": true
      },
      {
        "text": "該新型抗真菌藥物具有強效的抑菌作用。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 11531, level 3

#### Pack A
### Level 3 (sense 11531, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解___厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
  "original_sentence": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
  "correct_answer": "细碎",
  "options": [
    "完整",
    "庞大",
    "昂贵",
    "细碎"
  ],
  "explanation": "正确。'细碎'修饰'厨余'，准确表达了厨余垃圾细小且零散的状态，符合语境。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解___廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "original_sentence": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "correct_answer": "細碎",
    "options": [
      "完整",
      "龐大",
      "昂貴",
      "細碎"
    ],
    "explanation": "正確。'細碎'修飾'廚餘'，準確表達了廚餘垃圾細小且零散的狀態，符合語境。",
    "distractor_tags": {},
    "word_definition": "細小而零碎。",
    "target_word": "細碎"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "他的话语___而温柔。",
  "original_sentence": "他的话语细碎而温柔。",
  "correct_answer": "细碎",
  "options": [
    "粘稠",
    "粗糙",
    "细碎",
    "庞大"
  ],
  "explanation": "正确。'细碎'形容话语细小而零散，与'温柔'搭配自然。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "他的話語___而溫柔。",
    "original_sentence": "他的話語細碎而溫柔。",
    "correct_answer": "細碎",
    "options": [
      "粘稠",
      "粗糙",
      "細碎",
      "龐大"
    ],
    "explanation": "正確。'細碎'形容話語細小而零散，與'溫柔'搭配自然。",
    "distractor_tags": {},
    "word_definition": "細小而零碎。",
    "target_word": "細碎"
  }
}
```

#### Pack B
### Level 3 (sense 11531, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解___厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
  "original_sentence": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
  "correct_answer": "细碎",
  "options": [
    "巨大",
    "华丽",
    "漫长",
    "细碎"
  ],
  "explanation": "正确选项。形容厨余颗粒细小零碎，符合微生物高效降解的物理条件。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解___廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "original_sentence": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "correct_answer": "細碎",
    "options": [
      "巨大",
      "華麗",
      "漫長",
      "細碎"
    ],
    "explanation": "正確選項。形容廚餘顆粒細小零碎，符合微生物高效降解的物理條件。",
    "distractor_tags": {},
    "word_definition": "細小而零碎。",
    "target_word": "細碎"
  }
}
```

---

## sense 11531, level 6

#### Pack A
### Level 6 (sense 11531, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "细碎",
  "relation": "antonym",
  "options": [
    "微小",
    "繁杂",
    "完整",
    "粗糙"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎。",
      "explanation": "指事物具有整体性、不零散，与目标词“细小而零碎”的义项构成反义"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "微小",
      "繁雜",
      "完整",
      "粗糙"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎。",
        "explanation": "指事物具有整體性、不零散，與目標詞“細小而零碎”的義項構成反義"
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
      "text": "她整理着细碎的头发。",
      "is_correct": true
    },
    {
      "text": "她整理着条细碎的头发。",
      "is_correct": false
    },
    {
      "text": "细碎的她整理着头发。",
      "is_correct": false
    },
    {
      "text": "她整理着细碎了的头发。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'头发'作为整体或散乱状态时，不能用个体量词'条'来修饰'细碎的头发'，应使用'缕'或直接省略量词。 体标选用错误：'细碎'是状态形容词，表示事物本身的属性，不能加动态助词'了'表示动作完成或状态变化。 语序错误：形容词'细碎'作定语应紧挨着中心语'头发'，放在主语'她'之前会导致修饰关系错乱，语义不通。",
  "target_word": "细碎",
  "hant": {
    "sentences": [
      {
        "text": "她整理著細碎的頭髮。",
        "is_correct": true
      },
      {
        "text": "她整理著條細碎的頭髮。",
        "is_correct": false
      },
      {
        "text": "細碎的她整理著頭髮。",
        "is_correct": false
      },
      {
        "text": "她整理著細碎了的頭髮。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'頭髮'作為整體或散亂狀態時，不能用個體量詞'條'來修飾'細碎的頭髮'，應使用'縷'或直接省略量詞。 體標選用錯誤：'細碎'是狀態形容詞，表示事物本身的屬性，不能加動態助詞'了'表示動作完成或狀態變化。 語序錯誤：形容詞'細碎'作定語應緊挨著中心語'頭髮'，放在主語'她'之前會導致修飾關係錯亂，語義不通。",
    "target_word": "細碎"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "细碎",
  "relation": "antonym",
  "options": [
    "粗糙",
    "密集",
    "完整",
    "繁杂"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎。",
      "explanation": "目标词指细小且零散，「完整」指具有整体而不零碎，二者构成反义关系。"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "粗糙",
      "密集",
      "完整",
      "繁雜"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎。",
        "explanation": "目標詞指細小且零散，「完整」指具有整體而不零碎，二者構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 11531, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "记忆里的画面总是细碎了。",
      "is_correct": false
    },
    {
      "text": "记忆里的画面总是很细碎地。",
      "is_correct": false
    },
    {
      "text": "记忆里的画面总是很细碎。",
      "is_correct": true
    },
    {
      "text": "记忆里的画面总是很细碎着。",
      "is_correct": false
    }
  ],
  "explanation": "语序/结构错误：'细碎'是形容词，不能直接加'地'作状语修饰名词'画面'，应去掉'地'，或改为'细碎的画面'。 体标错误：'细碎'表示一种状态，通常不与动态助词'了'连用表示完成，应去掉'了'，保持状态形容词的用法。 体标错误：'细碎'是性质形容词，不能加'着'表示动作或状态的持续，应去掉'着'。",
  "target_word": "细碎",
  "hant": {
    "sentences": [
      {
        "text": "記憶裡的畫面總是細碎了。",
        "is_correct": false
      },
      {
        "text": "記憶裡的畫面總是很細碎地。",
        "is_correct": false
      },
      {
        "text": "記憶裡的畫面總是很細碎。",
        "is_correct": true
      },
      {
        "text": "記憶裡的畫面總是很細碎著。",
        "is_correct": false
      }
    ],
    "explanation": "語序/結構錯誤：'細碎'是形容詞，不能直接加'地'作狀語修飾名詞'畫面'，應去掉'地'，或改為'細碎的畫面'。 體標錯誤：'細碎'表示一種狀態，通常不與動態助詞'了'連用表示完成，應去掉'了'，保持狀態形容詞的用法。 體標錯誤：'細碎'是性質形容詞，不能加'著'表示動作或狀態的持續，應去掉'著'。",
    "target_word": "細碎"
  }
}
```

---

## sense 11531, level 7

#### Pack A
### Level 7 (sense 11531, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "她整理着细碎的头发。",
      "is_correct": true
    },
    {
      "text": "他的话语细碎而温柔。",
      "is_correct": true
    },
    {
      "text": "她把细碎的头发整理。",
      "is_correct": false,
      "error_description": "“把”字句中的谓语动词不能是光杆动词，必须在动词后添加结果补语（如“好”）或动态助词（如“了”）以表示动作的结果或完成。"
    },
    {
      "text": "我想起那些细碎的时光。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她整理著細碎的頭髮。",
        "is_correct": true
      },
      {
        "text": "他的話語細碎而溫柔。",
        "is_correct": true
      },
      {
        "text": "她把細碎的頭髮整理。",
        "is_correct": false,
        "error_description": "“把”字句中的謂語動詞不能是光桿動詞，必須在動詞後新增結果補語（如“好”）或動態助詞（如“了”）以表示動作的結果或完成。"
      },
      {
        "text": "我想起那些細碎的時光。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 11531, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "树下的阳光显得很细碎。",
      "is_correct": true
    },
    {
      "text": "我听着窗外一条细碎的脚步声。",
      "is_correct": false,
      "error_description": "量词使用错误。量词“条”不能用来修饰“脚步声”，此处不需要加量词，或者可以改为“一阵”。"
    },
    {
      "text": "我听着窗外细碎的脚步声。",
      "is_correct": true
    },
    {
      "text": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "樹下的陽光顯得很細碎。",
        "is_correct": true
      },
      {
        "text": "我聽著窗外一條細碎的腳步聲。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。量詞“條”不能用來修飾“腳步聲”，此處不需要加量詞，或者可以改為“一陣”。"
      },
      {
        "text": "我聽著窗外細碎的腳步聲。",
        "is_correct": true
      },
      {
        "text": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 12012, level 6

#### Pack A
### Level 6 (sense 12012, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他们把关系弄得剑拔弩张着。",
      "is_correct": false
    },
    {
      "text": "他们把关系弄得剑拔弩张起来。",
      "is_correct": false
    },
    {
      "text": "他们把关系弄得剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "剑拔弩张他们把关系弄得。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。“剑拔弩张”是状态形容词，不能加动态助词“着”来表示动作的持续。 语序错误。“剑拔弩张”作为补语或谓语，不能脱离其主语和宾语前置到句首，破坏了“把”字句的基本结构。 体标选用错误。“起来”表示动作或状态的开始，而“弄得”后面通常接结果补语，表示状态达到的程度，两者搭配不当。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "他們把關係弄得劍拔弩張著。",
        "is_correct": false
      },
      {
        "text": "他們把關係弄得劍拔弩張起來。",
        "is_correct": false
      },
      {
        "text": "他們把關係弄得劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "劍拔弩張他們把關係弄得。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。“劍拔弩張”是狀態形容詞，不能加動態助詞“著”來表示動作的持續。 語序錯誤。“劍拔弩張”作為補語或謂語，不能脫離其主語和賓語前置到句首，破壞了“把”字句的基本結構。 體標選用錯誤。“起來”表示動作或狀態的開始，而“弄得”後面通常接結果補語，表示狀態達到的程度，兩者搭配不當。",
    "target_word": "劍拔弩張"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "剑拔弩张",
  "relation": "antonym",
  "options": [
    "错综复杂",
    "热火朝天",
    "千钧一发",
    "风平浪静"
  ],
  "correct_answer": "风平浪静",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方争吵或对立，气氛非常紧张。",
      "explanation": "反义项：比喻平静无事，与目标词形容双方对立、气氛紧张构成反义。"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "錯綜複雜",
      "熱火朝天",
      "千鈞一髮",
      "風平浪靜"
    ],
    "correct_answer": "風平浪靜",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方爭吵或對立，氣氛非常緊張。",
        "explanation": "反義項：比喻平靜無事，與目標詞形容雙方對立、氣氛緊張構成反義。"
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
      "text": "谈判双方剑拔弩张得很，互不相让。",
      "is_correct": false
    },
    {
      "text": "剑拔弩张着谈判双方，互不相让。",
      "is_correct": false
    },
    {
      "text": "谈判双方把关系剑拔弩张起来，互不相让。",
      "is_correct": false
    },
    {
      "text": "谈判双方剑拔弩张，互不相让。",
      "is_correct": true
    }
  ],
  "explanation": "体标误用：“剑拔弩张”本身已包含极度紧张的状态，不能加程度补语“得很”，造成语义重复与体貌错误。 语序错误：“剑拔弩张”是不及物状态的形容词，不能带动态助词“着”并前置作及物动词使用，破坏了主题-评论结构。 配价与补语误用：“剑拔弩张”不能用于“把”字句中作结果补语，也不能与趋向补语“起来”搭配表示状态起始。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "談判雙方劍拔弩張得很，互不相讓。",
        "is_correct": false
      },
      {
        "text": "劍拔弩張著談判雙方，互不相讓。",
        "is_correct": false
      },
      {
        "text": "談判雙方把關係劍拔弩張起來，互不相讓。",
        "is_correct": false
      },
      {
        "text": "談判雙方劍拔弩張，互不相讓。",
        "is_correct": true
      }
    ],
    "explanation": "體標誤用：“劍拔弩張”本身已包含極度緊張的狀態，不能加程度補語“得很”，造成語義重複與體貌錯誤。 語序錯誤：“劍拔弩張”是不及物狀態的形容詞，不能帶動態助詞“著”並前置作及物動詞使用，破壞了主題-評論結構。 配價與補語誤用：“劍拔弩張”不能用於“把”字句中作結果補語，也不能與趨向補語“起來”搭配表示狀態起始。",
    "target_word": "劍拔弩張"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "剑拔弩张",
  "relation": "antonym",
  "options": [
    "势均力敌",
    "死气沉沉",
    "如火如荼",
    "一团和气"
  ],
  "correct_answer": "一团和气",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方争吵或对立，气氛非常紧张。",
      "explanation": "形容气氛融洽、态度温和，与目标词“气氛非常紧张、对立”构成反义。"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "勢均力敵",
      "死氣沉沉",
      "如火如荼",
      "一團和氣"
    ],
    "correct_answer": "一團和氣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方爭吵或對立，氣氛非常緊張。",
        "explanation": "形容氣氛融洽、態度溫和，與目標詞“氣氛非常緊張、對立”構成反義。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 12012, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "两人关系剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "两人关系剑拔弩张出来。",
      "is_correct": false
    },
    {
      "text": "关系两人剑拔弩张。",
      "is_correct": false
    },
    {
      "text": "两人关系剑拔弩张着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“剑拔弩张”是状态形容词，不能加动态助词“着”来表示状态的持续。 语序错误。汉语中主语“两人关系”应放在谓语“剑拔弩张”之前，不能颠倒为“关系两人”。 方向/结果补语误用。“剑拔弩张”不能带趋向补语“出来”，“出来”通常用于表示动作使某事物显露，不能用于修饰状态形容词。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "兩人關係劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "兩人關係劍拔弩張出來。",
        "is_correct": false
      },
      {
        "text": "關係兩人劍拔弩張。",
        "is_correct": false
      },
      {
        "text": "兩人關係劍拔弩張著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“劍拔弩張”是狀態形容詞，不能加動態助詞“著”來表示狀態的持續。 語序錯誤。漢語中主語“兩人關係”應放在謂語“劍拔弩張”之前，不能顛倒為“關係兩人”。 方向/結果補語誤用。“劍拔弩張”不能帶趨向補語“出來”，“出來”通常用於表示動作使某事物顯露，不能用於修飾狀態形容詞。",
    "target_word": "劍拔弩張"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在竞技场剑拔弩张的对峙让人害怕。",
      "is_correct": false
    },
    {
      "text": "一个剑拔弩张的对峙让人害怕。",
      "is_correct": false
    },
    {
      "text": "剑拔弩张的对峙让人害怕。",
      "is_correct": true
    },
    {
      "text": "剑拔弩张着的对峙让人害怕。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。介词短语“在竞技场”作定语时，应放在形容词“剑拔弩张”之前，改为“竞技场里剑拔弩张的对峙”才自然。 体标选用错误。“剑拔弩张”本身已表示完整的状态，通常不加动态助词“着”直接修饰名词，加“着”显得生硬且不自然。 量词使用错误。“对峙”作为事件或状态，通常用量词“场”或“次”修饰，使用“个”不自然。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "在競技場劍拔弩張的對峙讓人害怕。",
        "is_correct": false
      },
      {
        "text": "一個劍拔弩張的對峙讓人害怕。",
        "is_correct": false
      },
      {
        "text": "劍拔弩張的對峙讓人害怕。",
        "is_correct": true
      },
      {
        "text": "劍拔弩張著的對峙讓人害怕。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。介詞短語“在競技場”作定語時，應放在形容詞“劍拔弩張”之前，改為“競技場裡劍拔弩張的對峙”才自然。 體標選用錯誤。“劍拔弩張”本身已表示完整的狀態，通常不加動態助詞“著”直接修飾名詞，加“著”顯得生硬且不自然。 量詞使用錯誤。“對峙”作為事件或狀態，通常用量詞“場”或“次”修飾，使用“個”不自然。",
    "target_word": "劍拔弩張"
  }
}
```

---

## sense 12012, level 7

#### Pack A
### Level 7 (sense 12012, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "经理把会议室的气氛剑拔弩张。",
      "is_correct": false,
      "error_description": "“把”字句的谓语不能是形容词，“剑拔弩张”不能直接作“把”字句的谓语。应去掉“经理把”，或改为“经理把会议室的气氛搞得剑拔弩张”。"
    },
    {
      "text": "他打破了剑拔弩张的局面。",
      "is_correct": true
    },
    {
      "text": "剑拔弩张的对峙让人害怕。",
      "is_correct": true
    },
    {
      "text": "竞争态势剑拔弩张。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "經理把會議室的氣氛劍拔弩張。",
        "is_correct": false,
        "error_description": "“把”字句的謂語不能是形容詞，“劍拔弩張”不能直接作“把”字句的謂語。應去掉“經理把”，或改為“經理把會議室的氣氛搞得劍拔弩張”。"
      },
      {
        "text": "他打破了劍拔弩張的局面。",
        "is_correct": true
      },
      {
        "text": "劍拔弩張的對峙讓人害怕。",
        "is_correct": true
      },
      {
        "text": "競爭態勢劍拔弩張。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 12012, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "玩家在“敌对公会”的竞技场厮杀后，可能在同一资源区合作采矿；竞争对手在排行榜上剑拔弩张，却又在社区论坛共享战术心得。",
      "is_correct": true
    },
    {
      "text": "这是一场剑拔弩张的比赛。",
      "is_correct": true
    },
    {
      "text": "几句话把气氛剑拔弩张。",
      "is_correct": false,
      "error_description": "在“把”字句中，“把”的宾语后不能直接接形容词“剑拔弩张”，必须使用“动词+得+形容词”的结构，例如改为“搞得剑拔弩张”。"
    },
    {
      "text": "两边的气氛剑拔弩张。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "玩家在“敵對公會”的競技場廝殺後，可能在同一資源區合作採礦；競爭對手在排行榜上劍拔弩張，卻又在社群論壇共享戰術心得。",
        "is_correct": true
      },
      {
        "text": "這是一場劍拔弩張的比賽。",
        "is_correct": true
      },
      {
        "text": "幾句話把氣氛劍拔弩張。",
        "is_correct": false,
        "error_description": "在“把”字句中，“把”的賓語後不能直接接形容詞“劍拔弩張”，必須使用“動詞+得+形容詞”的結構，例如改為“搞得劍拔弩張”。"
      },
      {
        "text": "兩邊的氣氛劍拔弩張。",
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
      "text": "双方剑拔弩张地争吵着。",
      "is_correct": true
    },
    {
      "text": "几句话把搞得气氛剑拔弩张。",
      "is_correct": false,
      "error_description": "“把”字句的宾语“气氛”必须紧跟在“把”之后，不能放在动词“搞”之后。"
    },
    {
      "text": "谈判双方剑拔弩张，互不相让。",
      "is_correct": true
    },
    {
      "text": "两国关系曾经剑拔弩张。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "雙方劍拔弩張地爭吵著。",
        "is_correct": true
      },
      {
        "text": "幾句話把搞得氣氛劍拔弩張。",
        "is_correct": false,
        "error_description": "“把”字句的賓語“氣氛”必須緊跟在“把”之後，不能放在動詞“搞”之後。"
      },
      {
        "text": "談判雙方劍拔弩張，互不相讓。",
        "is_correct": true
      },
      {
        "text": "兩國關係曾經劍拔弩張。",
        "is_correct": true
      }
    ]
  }
}
```

---

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
  "explanation": "正确。发音为第四声（yào），表示希望、需要或请求。",
  "distractor_explanations": {
    "腰": "声调混淆：“腰”读第一声（yāo），指身体的一部分；而目标词“要”读第四声（yào）。",
    "摇": "声调混淆：“摇”读第二声（yáo），表示摆动；而目标词“要”读第四声（yào）。",
    "咬": "声调混淆：“咬”读第三声（yǎo），表示用牙齿夹住或切断；而目标词“要”读第四声（yào）。"
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
    "explanation": "正確。發音為第四聲（yào），表示希望、需要或請求。",
    "distractor_explanations": {
      "腰": "聲調混淆：“腰”讀第一聲（yāo），指身體的一部分；而目標詞“要”讀第四聲（yào）。",
      "摇": "聲調混淆：“搖”讀第二聲（yáo），表示擺動；而目標詞“要”讀第四聲（yào）。",
      "咬": "聲調混淆：“咬”讀第三聲（yǎo），表示用牙齒夾住或切斷；而目標詞“要”讀第四聲（yào）。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19859, level 6

#### Pack A
### Level 6 (sense 19859, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我要把这本故事书送给小明。",
      "is_correct": true
    },
    {
      "text": "我要把这本故事书送起给小明。",
      "is_correct": false
    },
    {
      "text": "我要把这本故事书送了给小明。",
      "is_correct": false
    },
    {
      "text": "我把这本故事书要送给小明。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：情态动词“要”必须放在“把”字短语之前，正确语序应为“我要把这本故事书送给小明”。 体标位置错误：在“把”字句中，动态助词“了”应放在动补结构“送给”之后，即“送给了小明”，不能插入动词和补语之间。 方向/结果补语误用：“起”不能作“送”的补语来表示给予对象的方向，此处应使用“给”或“出去”等合适的补语。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "我要把這本故事書送給小明。",
        "is_correct": true
      },
      {
        "text": "我要把這本故事書送起給小明。",
        "is_correct": false
      },
      {
        "text": "我要把這本故事書送了給小明。",
        "is_correct": false
      },
      {
        "text": "我把這本故事書要送給小明。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：情態動詞“要”必須放在“把”字短語之前，正確語序應為“我要把這本故事書送給小明”。 體標位置錯誤：在“把”字句中，動態助詞“了”應放在動補結構“送給”之後，即“送給了小明”，不能插入動詞和補語之間。 方向/結果補語誤用：“起”不能作“送”的補語來表示給予物件的方向，此處應使用“給”或“出去”等合適的補語。",
    "target_word": "要"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "你要不要试着把这道题解开了？",
      "is_correct": false
    },
    {
      "text": "要不要你试着把这道题解开？",
      "is_correct": false
    },
    {
      "text": "你要不要试着把这道题解开？",
      "is_correct": true
    },
    {
      "text": "你要不要试着把这只题解开？",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“题”的量词应为“道”，不能使用修饰动物或某些成对物品的“只”。 体标选用错误：句末的“了”表示动作完成，但“试着”表示尝试，两者在语义和体貌上冲突，应去掉“了”。 语序错误：情态动词“要”的主语“你”被错放在了“要不要”之后，破坏了正常的“主语+情态动词”语序。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "你要不要試著把這道題解開了？",
        "is_correct": false
      },
      {
        "text": "要不要你試著把這道題解開？",
        "is_correct": false
      },
      {
        "text": "你要不要試著把這道題解開？",
        "is_correct": true
      },
      {
        "text": "你要不要試著把這隻題解開？",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“題”的量詞應為“道”，不能使用修飾動物或某些成對物品的“只”。 體標選用錯誤：句末的“了”表示動作完成，但“試著”表示嘗試，兩者在語義和體貌上衝突，應去掉“了”。 語序錯誤：情態動詞“要”的主語“你”被錯放在了“要不要”之後，破壞了正常的“主語+情態動詞”語序。",
    "target_word": "要"
  }
}
```

#### Pack B
### Level 6 (sense 19859, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们要买些新鲜水果。",
      "is_correct": true
    },
    {
      "text": "我们要买新鲜些水果。",
      "is_correct": false
    },
    {
      "text": "我们要买着些新鲜水果。",
      "is_correct": false
    },
    {
      "text": "我们要买一条新鲜水果。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'水果'不能用'条'来修饰，应使用'些'或具体的量词如'个'。 体标选用错误。'着'表示动作持续，'买'是瞬间动词，且'要'表示意愿或将来，与'着'冲突。 语序错误。数量词'些'应放在形容词'新鲜'之前，正确语序为'些新鲜水果'。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "我們要買些新鮮水果。",
        "is_correct": true
      },
      {
        "text": "我們要買新鮮些水果。",
        "is_correct": false
      },
      {
        "text": "我們要買著些新鮮水果。",
        "is_correct": false
      },
      {
        "text": "我們要買一條新鮮水果。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'水果'不能用'條'來修飾，應使用'些'或具體的量詞如'個'。 體標選用錯誤。'著'表示動作持續，'買'是瞬間動詞，且'要'表示意願或將來，與'著'衝突。 語序錯誤。數量詞'些'應放在形容詞'新鮮'之前，正確語序為'些新鮮水果'。",
    "target_word": "要"
  }
}
```

---

## sense 19859, level 7

#### Pack A
### Level 7 (sense 19859, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我把这本故事书要送给小明。",
      "is_correct": false,
      "error_description": "在把字句中，情态动词要应该放在把字之前，而不是之后。"
    },
    {
      "text": "请把你要说的话大声讲出来。",
      "is_correct": true
    },
    {
      "text": "我明天需要去图书馆，所以我要去。",
      "is_correct": true
    },
    {
      "text": "她明天需要买礼物，所以她要买。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我把這本故事書要送給小明。",
        "is_correct": false,
        "error_description": "在把字句中，情態動詞要應該放在把字之前，而不是之後。"
      },
      {
        "text": "請把你要說的話大聲講出來。",
        "is_correct": true
      },
      {
        "text": "我明天需要去圖書館，所以我要去。",
        "is_correct": true
      },
      {
        "text": "她明天需要買禮物，所以她要買。",
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
    "挛",
    "卵",
    "峦",
    "乱"
  ],
  "correct_answer": "乱",
  "explanation": "正确。'乱'读作 luàn，表示没有条理或秩序。",
  "distractor_explanations": {
    "峦": "错误。'峦'读作 luán（二声），指连绵的山峰，声调不同导致意义改变。",
    "卵": "错误。'卵'读作 luǎn（三声），指蛋或动物的生殖细胞，声调不同导致意义改变。",
    "挛": "错误。'挛'读作 luán（二声），指肌肉收缩不能伸直，声调不同导致意义改变。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "亂",
    "pronunciation": "luàn",
    "ipa": "[luan˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "攣",
      "卵",
      "巒",
      "亂"
    ],
    "correct_answer": "亂",
    "explanation": "正確。'亂'讀作 luàn，表示沒有條理或秩序。",
    "distractor_explanations": {
      "峦": "錯誤。'巒'讀作 luán（二聲），指連綿的山峰，聲調不同導致意義改變。",
      "卵": "錯誤。'卵'讀作 luǎn（三聲），指蛋或動物的生殖細胞，聲調不同導致意義改變。",
      "挛": "錯誤。'攣'讀作 luán（二聲），指肌肉收縮不能伸直，聲調不同導致意義改變。"
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
