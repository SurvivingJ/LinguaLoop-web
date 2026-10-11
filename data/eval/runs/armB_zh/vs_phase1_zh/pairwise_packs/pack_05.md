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


## sense 10553, level 7

#### Pack A
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "气候变化导致适宜种植区收缩，极端天气频发影响产量稳定性；全球航运成本波动、地缘政治紧张以及关税政策调整均可能扰乱贸易流向；同时，小农户在面对市场风险时普遍缺乏金融工具与信息支持。",
      "is_correct": true
    },
    {
      "text": "当极端气候频发导致主粮产区波动时，分布式的城市食品生产网络展现出显著的风险对冲能力，使地方政府将此类项目纳入关键基础设施的应急规划范畴。",
      "is_correct": true
    },
    {
      "text": "在某些干旱频发的地区，纺织工业甚至成为加剧水资源短缺的关键因素，挤占了农业、饮用水与生态系统所需的水量。",
      "is_correct": true
    },
    {
      "text": "最近班里感冒的同学很多，这种病正在频发着。",
      "is_correct": false,
      "error_description": "错误类型：体标误用。'频发'表示某种现象频繁发生，本身已包含持续性或重复性的语义，且在此语境中作为谓语描述一种状态或趋势，通常不与进行体标记'着'连用。正确的表达应直接使用'频发'或根据语境使用'频发中'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "氣候變化導致適宜種植區收縮，極端天氣頻發影響產量穩定性；全球航運成本波動、地緣政治緊張以及關稅政策調整均可能擾亂貿易流向；同時，小農戶在面對市場風險時普遍缺乏金融工具與資訊支援。",
        "is_correct": true
      },
      {
        "text": "當極端氣候頻發導致主糧產區波動時，分散式的城市食品生產網路展現出顯著的風險對沖能力，使地方政府將此類專案納入關鍵基礎設施的應急規劃範疇。",
        "is_correct": true
      },
      {
        "text": "在某些乾旱頻發的地區，紡織工業甚至成為加劇水資源短缺的關鍵因素，擠佔了農業、飲用水與生態系統所需的水量。",
        "is_correct": true
      },
      {
        "text": "最近班裡感冒的同學很多，這種病正在頻發著。",
        "is_correct": false,
        "error_description": "錯誤型別：體標誤用。'頻發'表示某種現象頻繁發生，本身已包含持續性或重複性的語義，且在此語境中作為謂語描述一種狀態或趨勢，通常不與進行體標記'著'連用。正確的表達應直接使用'頻發'或根據語境使用'頻發中'。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "最近矛盾频发，他们把关系搞僵了。",
      "is_correct": true
    },
    {
      "text": "最近频发了很多事故，把大家吓坏了。",
      "is_correct": false,
      "error_description": "“频发”是不及物动词，不能直接带宾语。应将“事故”放在“频发”前面作主语，改为“最近事故频发”。"
    },
    {
      "text": "大家害怕事故频发。",
      "is_correct": true
    },
    {
      "text": "频发的错误让她心里很难过。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "最近矛盾頻發，他們把關係搞僵了。",
        "is_correct": true
      },
      {
        "text": "最近頻發了很多事故，把大家嚇壞了。",
        "is_correct": false,
        "error_description": "“頻發”是不及物動詞，不能直接帶賓語。應將“事故”放在“頻發”前面作主語，改為“最近事故頻發”。"
      },
      {
        "text": "大家害怕事故頻發。",
        "is_correct": true
      },
      {
        "text": "頻發的錯誤讓她心裡很難過。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 11315, level 6

#### Pack A
### Level 6 (sense 11315, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "拮抗剂可以阻止毒素起作用。",
      "is_correct": true
    },
    {
      "text": "拮抗剂可以阻止毒素起作用了。",
      "is_correct": false
    },
    {
      "text": "一个拮抗剂可以阻止毒素起作用。",
      "is_correct": false
    },
    {
      "text": "可以阻止毒素起作用拮抗剂。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：句尾的'了'表示变化或完成，而原句陈述的是一般性科学事实或能力，不应使用完成体标记。 量词/指称错误：在陈述一般性功能时，'拮抗剂'作为不可数或类指名词，通常不加个体量词'一个'，直接作主语更自然。 语序错误：汉语基本语序为主谓宾，'拮抗剂'是主语，应置于句首，而非句尾。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "拮抗劑可以阻止毒素起作用。",
        "is_correct": true
      },
      {
        "text": "拮抗劑可以阻止毒素起作用了。",
        "is_correct": false
      },
      {
        "text": "一個拮抗劑可以阻止毒素起作用。",
        "is_correct": false
      },
      {
        "text": "可以阻止毒素起作用拮抗劑。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：句尾的'了'表示變化或完成，而原句陳述的是一般性科學事實或能力，不應使用完成體標記。 量詞/指稱錯誤：在陳述一般性功能時，'拮抗劑'作為不可數或類指名詞，通常不加個體量詞'一個'，直接作主語更自然。 語序錯誤：漢語基本語序為主謂賓，'拮抗劑'是主語，應置於句首，而非句尾。",
    "target_word": "拮抗劑"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "拮抗剂",
  "relation": "antonym",
  "options": [
    "激动剂",
    "阻断剂",
    "催化剂",
    "抑制剂"
  ],
  "correct_answer": "激动剂",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "能抵消另一种物质作用的药物或成分。",
      "explanation": "在药理学中，激动剂能激活受体产生效应，与能抵消作用的拮抗剂构成反义关系。"
    }
  },
  "hant": {
    "word": "拮抗劑",
    "relation": "antonym",
    "options": [
      "激動劑",
      "阻斷劑",
      "催化劑",
      "抑制劑"
    ],
    "correct_answer": "激動劑",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "能抵消另一種物質作用的藥物或成分。",
        "explanation": "在藥理學中，激動劑能啟用受體產生效應，與能抵消作用的拮抗劑構成反義關係。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "拮抗剂",
  "relation": "antonym",
  "options": [
    "抑制剂",
    "阻滞剂",
    "激动剂",
    "催化剂"
  ],
  "correct_answer": "激动剂",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "能抵消另一种物质作用的药物或成分。",
      "explanation": "药理学反义词：指能与受体结合并产生生物效应的物质，作用与拮抗剂相反。"
    }
  },
  "hant": {
    "word": "拮抗劑",
    "relation": "antonym",
    "options": [
      "抑制劑",
      "阻滯劑",
      "激動劑",
      "催化劑"
    ],
    "correct_answer": "激動劑",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "能抵消另一種物質作用的藥物或成分。",
        "explanation": "藥理學反義詞：指能與受體結合併產生生物效應的物質，作用與拮抗劑相反。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 11315, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "需要密切观察副作用拮抗剂的。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂已经抑制着了毒素的影响。",
      "is_correct": false
    },
    {
      "text": "医生给病人开了一张拮抗剂。",
      "is_correct": false
    },
    {
      "text": "拮抗剂的副作用需要密切观察。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误。'拮抗剂'作为药物种类或具体药剂，应使用'种'、'类'或'支'，不能使用用于纸张的'张'。 体标选用错误。'已经'表示动作完成，而'着'表示状态持续，两者在体貌上相互冲突，不能连用。 语序错误。定语'拮抗剂的'应该放在中心语'副作用'之前，正确的语序应为'拮抗剂的副作用'。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "需要密切觀察副作用拮抗劑的。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑已經抑制著了毒素的影響。",
        "is_correct": false
      },
      {
        "text": "醫生給病人開了一張拮抗劑。",
        "is_correct": false
      },
      {
        "text": "拮抗劑的副作用需要密切觀察。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤。'拮抗劑'作為藥物種類或具體藥劑，應使用'種'、'類'或'支'，不能使用用於紙張的'張'。 體標選用錯誤。'已經'表示動作完成，而'著'表示狀態持續，兩者在體貌上相互衝突，不能連用。 語序錯誤。定語'拮抗劑的'應該放在中心語'副作用'之前，正確的語序應為'拮抗劑的副作用'。",
    "target_word": "拮抗劑"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "医生为病人开了一项拮抗剂来缓解症状。",
      "is_correct": false
    },
    {
      "text": "该拮抗剂着实降低了毒素的影响。",
      "is_correct": true
    },
    {
      "text": "医生给病人拮抗剂昨天注射以阻断神经信号。",
      "is_correct": false
    },
    {
      "text": "护士把拮抗剂了注射到病人的静脉里。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“拮抗剂”作为具体药物或物质，应使用“种”、“支”或“瓶”等量词，而“项”通常用于修饰项目、任务等抽象事物。 体标位置错误：动态助词“了”应放在动词“注射”之后或句末，不能放在介词“把”的宾语和动词之间，导致语法结构破裂。 语序错误：时间状语“昨天”应放在主语“医生”之后或句首，不能放在间接宾语和动词之间，破坏了正常的句法语序。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "醫生為病人開了一項拮抗劑來緩解症狀。",
        "is_correct": false
      },
      {
        "text": "該拮抗劑著實降低了毒素的影響。",
        "is_correct": true
      },
      {
        "text": "醫生給病人拮抗劑昨天注射以阻斷神經訊號。",
        "is_correct": false
      },
      {
        "text": "護士把拮抗劑了注射到病人的靜脈裡。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“拮抗劑”作為具體藥物或物質，應使用“種”、“支”或“瓶”等量詞，而“項”通常用於修飾專案、任務等抽象事物。 體標位置錯誤：動態助詞“了”應放在動詞“注射”之後或句末，不能放在介詞“把”的賓語和動詞之間，導致語法結構破裂。 語序錯誤：時間狀語“昨天”應放在主語“醫生”之後或句首，不能放在間接賓語和動詞之間，破壞了正常的句法語序。",
    "target_word": "拮抗劑"
  }
}
```

---

## sense 11319, level 3

#### Pack A
### Level 3 (sense 11319, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "更引人深思的是，某些___抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "original_sentence": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "correct_answer": "强效",
  "options": [
    "昂贵",
    "新鲜",
    "快速",
    "强效"
  ],
  "explanation": "正确。'强效'形容药物作用强大，符合句中抗精神病药物的语境。",
  "distractor_tags": {},
  "word_definition": "指药物或方法有非常强大的作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "更引人深思的是，某些___抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "original_sentence": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "correct_answer": "強效",
    "options": [
      "昂貴",
      "新鮮",
      "快速",
      "強效"
    ],
    "explanation": "正確。'強效'形容藥物作用強大，符合句中抗精神病藥物的語境。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法有非常強大的作用。",
    "target_word": "強效"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这种___肥料让花开得更好了。",
  "original_sentence": "这种强效肥料让花开得更好了。",
  "correct_answer": "强效",
  "options": [
    "昂贵",
    "强效",
    "新鲜",
    "快速"
  ],
  "explanation": "正确。'强效'形容作用非常强大，常修饰肥料、药物等，符合句意。",
  "distractor_tags": {},
  "word_definition": "指药物或方法有非常强大的作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "這種___肥料讓花開得更好了。",
    "original_sentence": "這種強效肥料讓花開得更好了。",
    "correct_answer": "強效",
    "options": [
      "昂貴",
      "強效",
      "新鮮",
      "快速"
    ],
    "explanation": "正確。'強效'形容作用非常強大，常修飾肥料、藥物等，符合句意。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法有非常強大的作用。",
    "target_word": "強效"
  }
}
```

#### Pack B
### Level 3 (sense 11319, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "更引人深思的是，某些___抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "original_sentence": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "correct_answer": "强效",
  "options": [
    "强固",
    "昂贵",
    "强效",
    "剧烈"
  ],
  "explanation": "正确。",
  "distractor_tags": {},
  "word_definition": "指药物或方法有很强的作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "更引人深思的是，某些___抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "original_sentence": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "correct_answer": "強效",
    "options": [
      "強固",
      "昂貴",
      "強效",
      "劇烈"
    ],
    "explanation": "正確。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法有很強的作用。",
    "target_word": "強效"
  }
}
```

---

## sense 11319, level 6

#### Pack A
### Level 6 (sense 11319, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "不需要这么强效治病。",
      "is_correct": false
    },
    {
      "text": "这药强效下去了。",
      "is_correct": false
    },
    {
      "text": "治病不需要这么强效。",
      "is_correct": true
    },
    {
      "text": "这种感冒药正强效着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“强效”为性质形容词，表示药物作用强的固有属性，不能加动态助词“着”表示状态的持续进行。 语序错误。“这么强效”在句中应作谓语或补语，说明治疗的程度或方法，不能直接放在动词“治病”前作状语。 方向/结果补语误用。“强效”表示药物作用强的属性，不能与趋向补语“下去”连用表示动作或状态的延续。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "不需要這麼強效治病。",
        "is_correct": false
      },
      {
        "text": "這藥強效下去了。",
        "is_correct": false
      },
      {
        "text": "治病不需要這麼強效。",
        "is_correct": true
      },
      {
        "text": "這種感冒藥正強效著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“強效”為性質形容詞，表示藥物作用強的固有屬性，不能加動態助詞“著”表示狀態的持續進行。 語序錯誤。“這麼強效”在句中應作謂語或補語，說明治療的程度或方法，不能直接放在動詞“治病”前作狀語。 方向/結果補語誤用。“強效”表示藥物作用強的屬性，不能與趨向補語“下去”連用表示動作或狀態的延續。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "高效",
    "弱效",
    "速效",
    "长效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法有很强的作用。",
      "explanation": "反义项：弱效指药物或方法作用微弱，与强效（作用很强）构成反义关系"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "高效",
      "弱效",
      "速效",
      "長效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法有很強的作用。",
        "explanation": "反義項：弱效指藥物或方法作用微弱，與強效（作用很強）構成反義關係"
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
      "text": "这种强效感冒药效果好。",
      "is_correct": true
    },
    {
      "text": "这种感冒药强效出来效果好。",
      "is_correct": false
    },
    {
      "text": "强效的这种感冒药效果好。",
      "is_correct": false
    },
    {
      "text": "这感冒药以前强效过。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“强效”是性质形容词，表示药物固有属性，不能加动态助词“过”表示经历。 语序错误。多层定语语序不当，指示代词“这种”应放在形容词“强效的”之前。 方向补语误用。“强效”是形容词，不能带趋向补语“出来”，应直接作定语或谓语。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "這種強效感冒藥效果好。",
        "is_correct": true
      },
      {
        "text": "這種感冒藥強效出來效果好。",
        "is_correct": false
      },
      {
        "text": "強效的這種感冒藥效果好。",
        "is_correct": false
      },
      {
        "text": "這感冒藥以前強效過。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“強效”是性質形容詞，表示藥物固有屬性，不能加動態助詞“過”表示經歷。 語序錯誤。多層定語語序不當，指示代詞“這種”應放在形容詞“強效的”之前。 方向補語誤用。“強效”是形容詞，不能帶趨向補語“出來”，應直接作定語或謂語。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "特效",
    "弱效",
    "速效",
    "长效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法有很强的作用。",
      "explanation": "反义项：指药物或方法的作用很弱，与“强效”构成反义关系。"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "特效",
      "弱效",
      "速效",
      "長效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法有很強的作用。",
        "explanation": "反義項：指藥物或方法的作用很弱，與“強效”構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 11319, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这款清洁剂具有强效去污能力得。",
      "is_correct": false
    },
    {
      "text": "这款清洁剂正在具有强效去污能力。",
      "is_correct": false
    },
    {
      "text": "这款清洁剂把强效去污能力具有。",
      "is_correct": false
    },
    {
      "text": "这款清洁剂具有强效去污能力。",
      "is_correct": true
    }
  ],
  "explanation": "语法错误：句末误用了结构助词'得'。'具有……能力'是动宾结构，不需要补语标记，应删除'得'。 语序错误：'把'字句使用不当。'具有'是状态动词，通常不用于'把'字句将宾语提前，且语序不符合汉语习惯。 体貌错误：'具有'表示一种固有的属性或状态，不能与表示进行时的'正在'连用。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "這款清潔劑具有強效去汙能力得。",
        "is_correct": false
      },
      {
        "text": "這款清潔劑正在具有強效去汙能力。",
        "is_correct": false
      },
      {
        "text": "這款清潔劑把強效去汙能力具有。",
        "is_correct": false
      },
      {
        "text": "這款清潔劑具有強效去汙能力。",
        "is_correct": true
      }
    ],
    "explanation": "語法錯誤：句末誤用了結構助詞'得'。'具有……能力'是動賓結構，不需要補語標記，應刪除'得'。 語序錯誤：'把'字句使用不當。'具有'是狀態動詞，通常不用於'把'字句將賓語提前，且語序不符合漢語習慣。 體貌錯誤：'具有'表示一種固有的屬性或狀態，不能與表示進行時的'正在'連用。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "劣质",
    "高效",
    "快速",
    "微弱"
  ],
  "correct_answer": "微弱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法有非常强大的作用。",
      "explanation": "反义词：指作用或力量很小，与“强效”的“强大作用”构成反义关系"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "劣質",
      "高效",
      "快速",
      "微弱"
    ],
    "correct_answer": "微弱",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法有非常強大的作用。",
        "explanation": "反義詞：指作用或力量很小，與“強效”的“強大作用”構成反義關係"
      }
    }
  }
}
```

---

## sense 11319, level 7

#### Pack A
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
      "text": "医生给我开了一种强效止痛药。",
      "is_correct": true
    },
    {
      "text": "这种强效药非常地很有效。",
      "is_correct": false,
      "error_description": "程度副词“非常”和“很”语义重复，不能同时修饰形容词，应删去其中一个。"
    },
    {
      "text": "这种药是强效的，吃一片就够了。",
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
        "text": "醫生給我開了一種強效止痛藥。",
        "is_correct": true
      },
      {
        "text": "這種強效藥非常地很有效。",
        "is_correct": false,
        "error_description": "程度副詞“非常”和“很”語義重複，不能同時修飾形容詞，應刪去其中一個。"
      },
      {
        "text": "這種藥是強效的，吃一片就夠了。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
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
    "细碎",
    "巨大",
    "昂贵",
    "完整"
  ],
  "explanation": "正确。'细碎'形容物体细小而零散，符合'厨余'被降解前的物理状态。",
  "distractor_tags": {},
  "word_definition": "细小而零碎",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解___廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "original_sentence": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "correct_answer": "細碎",
    "options": [
      "細碎",
      "巨大",
      "昂貴",
      "完整"
    ],
    "explanation": "正確。'細碎'形容物體細小而零散，符合'廚餘'被降解前的物理狀態。",
    "distractor_tags": {},
    "word_definition": "細小而零碎",
    "target_word": "細碎"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "请不要把___的垃圾扔在草地上。",
  "original_sentence": "请不要把细碎的垃圾扔在草地上。",
  "correct_answer": "细碎",
  "options": [
    "巨大",
    "昂贵",
    "细碎",
    "完整"
  ],
  "explanation": "正确。形容垃圾体积小且分散，符合语境。",
  "distractor_tags": {},
  "word_definition": "细小而零碎",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "請不要把___的垃圾扔在草地上。",
    "original_sentence": "請不要把細碎的垃圾扔在草地上。",
    "correct_answer": "細碎",
    "options": [
      "巨大",
      "昂貴",
      "細碎",
      "完整"
    ],
    "explanation": "正確。形容垃圾體積小且分散，符合語境。",
    "distractor_tags": {},
    "word_definition": "細小而零碎",
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

#### Pack B
### Level 6 (sense 11531, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "细碎",
  "relation": "antonym",
  "options": [
    "完整",
    "微小",
    "粗糙",
    "零乱"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎",
      "explanation": "“细碎”指细小零散、不完整，“完整”指具有整体性、未分裂，二者在物体形态的完整性上构成反义关系。"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "完整",
      "微小",
      "粗糙",
      "零亂"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎",
        "explanation": "“細碎”指細小零散、不完整，“完整”指具有整體性、未分裂，二者在物體形態的完整性上構成反義關係。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "细碎",
  "relation": "antonym",
  "options": [
    "微小",
    "琐碎",
    "完整",
    "凌乱"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎",
      "explanation": "“细碎”指细小零散、不完整，与表示整体、完备的“完整”构成反义关系。"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "微小",
      "瑣碎",
      "完整",
      "凌亂"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎",
        "explanation": "“細碎”指細小零散、不完整，與表示整體、完備的“完整”構成反義關係。"
      }
    }
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

#### Pack B
### Level 6 (sense 12012, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "比赛开始前，两队队员显得剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "比赛开始前，两队队员把气氛剑拔弩张了。",
      "is_correct": false
    },
    {
      "text": "比赛开始前，两队队员显得剑拔弩张着。",
      "is_correct": false
    },
    {
      "text": "比赛开始前，剑拔弩张的两队队员显得。",
      "is_correct": false
    }
  ],
  "explanation": "体标误用：'剑拔弩张'是形容词性成语，描述一种状态，通常不与表示持续进行的动态助词'着'连用。 语序错误：汉语中形容词作定语修饰名词时，应置于名词之前，且句子主干'队员显得……'后缺少补语或宾语，导致结构残缺且语序混乱。 配价/句法错误：'剑拔弩张'是不及物状态词，不能直接作为'把'字句的结果补语使用，也不能带宾语'气氛'。应改为'使气氛变得剑拔弩张'。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "比賽開始前，兩隊隊員顯得劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "比賽開始前，兩隊隊員把氣氛劍拔弩張了。",
        "is_correct": false
      },
      {
        "text": "比賽開始前，兩隊隊員顯得劍拔弩張著。",
        "is_correct": false
      },
      {
        "text": "比賽開始前，劍拔弩張的兩隊隊員顯得。",
        "is_correct": false
      }
    ],
    "explanation": "體標誤用：'劍拔弩張'是形容詞性成語，描述一種狀態，通常不與表示持續進行的動態助詞'著'連用。 語序錯誤：漢語中形容詞作定語修飾名詞時，應置於名詞之前，且句子主幹'隊員顯得……'後缺少補語或賓語，導致結構殘缺且語序混亂。 配價/句法錯誤：'劍拔弩張'是不及物狀態詞，不能直接作為'把'字句的結果補語使用，也不能帶賓語'氣氛'。應改為'使氣氛變得劍拔弩張'。",
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
    "针锋相对",
    "一触即发",
    "和平共处",
    "严阵以待"
  ],
  "correct_answer": "和平共处",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方冲突或紧张对峙，一触即发的状态。",
      "explanation": "反义词：形容双方关系融洽、没有冲突，与“剑拔弩张”的紧张对峙状态相反。"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "針鋒相對",
      "一觸即發",
      "和平共處",
      "嚴陣以待"
    ],
    "correct_answer": "和平共處",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方衝突或緊張對峙，一觸即發的狀態。",
        "explanation": "反義詞：形容雙方關係融洽、沒有衝突，與“劍拔弩張”的緊張對峙狀態相反。"
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
      "text": "别把简单的讨论弄得剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "别把简单的讨论弄得剑拔弩张过。",
      "is_correct": false
    },
    {
      "text": "别把简单的讨论弄得剑拔弩张起来很。",
      "is_correct": false
    },
    {
      "text": "别把简单的讨论弄得正在剑拔弩张。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：'剑拔弩张'是形容词性成语，表示一种状态，不能与进行体标记'正在'连用。应去掉'正在'。 语序错误：程度副词'很'不能放在趋向补语'起来'之后。正确的语序应是'变得很剑拔弩张'或去掉'很'，且'弄得...起来'搭配略显冗余，通常直接用'变得'。 体标选用错误：'过'表示经历体，通常用于动词后。'剑拔弩张'在此处作结果补语或状态描写，不能直接加'过'来表示'曾经紧张'。若要表达经历，需重构句子，如'讨论曾经剑拔弩张过'。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "別把簡單的討論弄得劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "別把簡單的討論弄得劍拔弩張過。",
        "is_correct": false
      },
      {
        "text": "別把簡單的討論弄得劍拔弩張起來很。",
        "is_correct": false
      },
      {
        "text": "別把簡單的討論弄得正在劍拔弩張。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：'劍拔弩張'是形容詞性成語，表示一種狀態，不能與進行體標記'正在'連用。應去掉'正在'。 語序錯誤：程度副詞'很'不能放在趨向補語'起來'之後。正確的語序應是'變得很劍拔弩張'或去掉'很'，且'弄得...起來'搭配略顯冗餘，通常直接用'變得'。 體標選用錯誤：'過'表示經歷體，通常用於動詞後。'劍拔弩張'在此處作結果補語或狀態描寫，不能直接加'過'來表示'曾經緊張'。若要表達經歷，需重構句子，如'討論曾經劍拔弩張過'。",
    "target_word": "劍拔弩張"
  }
}
```

---

## sense 12012, level 7

#### Pack A
### Level 7 (sense 12012, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "谈判桌上的气氛变得很剑拔弩张。",
      "is_correct": false,
      "error_description": "错误类型：冗余修饰。'剑拔弩张'本身已包含程度深、状态紧张的语义，通常不与程度副词'很'连用，直接作谓语或补语即可。"
    },
    {
      "text": "他们俩因为小事吵得剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "谈判桌上的气氛变得剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "玩家在“敌对公会”的竞技场厮杀后，可能在同一资源区合作采矿；竞争对手在排行榜上剑拔弩张，却又在社区论坛共享战术心得。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "談判桌上的氣氛變得很劍拔弩張。",
        "is_correct": false,
        "error_description": "錯誤型別：冗餘修飾。'劍拔弩張'本身已包含程度深、狀態緊張的語義，通常不與程度副詞'很'連用，直接作謂語或補語即可。"
      },
      {
        "text": "他們倆因為小事吵得劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "談判桌上的氣氛變得劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "玩家在“敵對公會”的競技場廝殺後，可能在同一資源區合作採礦；競爭對手在排行榜上劍拔弩張，卻又在社群論壇共享戰術心得。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
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
    "要",
    "耀",
    "药",
    "咬"
  ],
  "correct_answer": "要",
  "explanation": "正确。读音为 yào（第四声），表示希望或需要。",
  "distractor_explanations": {
    "药": "错误。读音为 yào，但意思是“药物”，与句意不符。",
    "咬": "错误。读音为 yǎo（第三声），意思是“用牙齿夹住或切断”。",
    "耀": "错误。读音为 yào，但意思是“光线强烈”或“炫耀”，不表示需要。"
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
      "耀",
      "藥",
      "咬"
    ],
    "correct_answer": "要",
    "explanation": "正確。讀音為 yào（第四聲），表示希望或需要。",
    "distractor_explanations": {
      "药": "錯誤。讀音為 yào，但意思是“藥物”，與句意不符。",
      "咬": "錯誤。讀音為 yǎo（第三聲），意思是“用牙齒夾住或切斷”。",
      "耀": "錯誤。讀音為 yào，但意思是“光線強烈”或“炫耀”，不表示需要。"
    },
    "distractor_source": "llm"
  }
}
```

---
