# Pairwise review pack 06

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


## sense 10803, level 7

#### Pack A
### Level 7 (sense 10803, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "联合国环境规划署在1972年斯德哥尔摩人类环境会议后，将此类标准化符号纳入全球环境治理的技术建议之中。",
      "is_correct": true
    },
    {
      "text": "首先，训练数据的采集与使用需满足“知情—同意”框架的实质要求，这意味着企业不能仅依赖用户协议中的概括性条款，而应通过分层披露机制，将涉及个人敏感信息或生成式内容的数据纳入可验证的用户授权路径进行严格管理，清晰说明其用于模型训练的具体场景、类别及潜在影响。",
      "is_correct": true
    },
    {
      "text": "我将纳入管理系统这些资料。",
      "is_correct": false,
      "error_description": "语序错误。在“将”字句中，受事宾语必须放在“将”之后、动词之前，不能放在动词之后。"
    },
    {
      "text": "可以预见，未来立法将原料提取、产品设计至废弃物回收等各个环节纳入全生命周期管理体系，以形成闭环控制机制。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "聯合國環境規劃署在1972年斯德哥爾摩人類環境會議後，將此類標準化符號納入全球環境治理的技術建議之中。",
        "is_correct": true
      },
      {
        "text": "首先，訓練資料的採集與使用需滿足“知情—同意”框架的實質要求，這意味著企業不能僅依賴使用者協議中的概括性條款，而應通過分層披露機制，將涉及個人敏感資訊或生成式內容的資料納入可驗證的使用者授權路徑進行嚴格管理，清晰說明其用於模型訓練的具體場景、類別及潛在影響。",
        "is_correct": true
      },
      {
        "text": "我將納入管理系統這些資料。",
        "is_correct": false,
        "error_description": "語序錯誤。在“將”字句中，受事賓語必須放在“將”之後、動詞之前，不能放在動詞之後。"
      },
      {
        "text": "可以預見，未來立法將原料提取、產品設計至廢棄物回收等各個環節納入全生命週期管理體系，以形成閉環控制機制。",
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
      "text": "然而，技术革新若无消费观念的同步转变，相关部门需将新技术纳入现有的市场准入规则中进行规范管理，以确保产业平稳发展。",
      "is_correct": true
    },
    {
      "text": "我将你的建议纳入考虑范围。",
      "is_correct": true
    },
    {
      "text": "我将这些资料纳入管理系统。",
      "is_correct": true
    },
    {
      "text": "我将纳入管理系统这些资料。",
      "is_correct": false,
      "error_description": "“将”字句要求受事宾语紧跟在“将”之后、谓语动词之前。原句将宾语放在了动词之后，属于语序错误。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "然而，技術革新若無消費觀念的同步轉變，相關部門需將新技術納入現有的市場準入規則中進行規範管理，以確保產業平穩發展。",
        "is_correct": true
      },
      {
        "text": "我將你的建議納入考慮範圍。",
        "is_correct": true
      },
      {
        "text": "我將這些資料納入管理系統。",
        "is_correct": true
      },
      {
        "text": "我將納入管理系統這些資料。",
        "is_correct": false,
        "error_description": "“將”字句要求受事賓語緊跟在“將”之後、謂語動詞之前。原句將賓語放在了動詞之後，屬於語序錯誤。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10803, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师将我们分成几个小组来讨论。",
      "is_correct": true
    },
    {
      "text": "管理者应将大家用严格的规则约束起来，以确保整体秩序。",
      "is_correct": true
    },
    {
      "text": "然而，若无消费观念的同步转变，这种脱节会将技术革新的进程拖入举步维艰的境地。",
      "is_correct": true
    },
    {
      "text": "老师将几个小组分成我们来讨论。",
      "is_correct": false,
      "error_description": "“将”字句的宾语应该是被处置的对象。在这个句子中，被分成小组的对象是“我们”，而不是“几个小组”，因此“我们”应该放在“将”的后面。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師將我們分成幾個小組來討論。",
        "is_correct": true
      },
      {
        "text": "管理者應將大家用嚴格的規則約束起來，以確保整體秩序。",
        "is_correct": true
      },
      {
        "text": "然而，若無消費觀念的同步轉變，這種脫節會將技術革新的程序拖入舉步維艱的境地。",
        "is_correct": true
      },
      {
        "text": "老師將幾個小組分成我們來討論。",
        "is_correct": false,
        "error_description": "“將”字句的賓語應該是被處置的物件。在這個句子中，被分成小組的物件是“我們”，而不是“幾個小組”，因此“我們”應該放在“將”的後面。"
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
      "text": "他正把拮抗剂着放进医疗箱里。",
      "is_correct": false
    },
    {
      "text": "他把一袋拮抗剂放进了医疗箱里。",
      "is_correct": false
    },
    {
      "text": "他把拮抗剂放进了医疗箱里。",
      "is_correct": true
    },
    {
      "text": "拮抗剂他把放进了医疗箱里。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“拮抗剂”作为具体药物名词，应使用“支”、“瓶”或“盒”，不能用“袋”。 体标位置错误：动态助词“着”应紧跟在动词“放”之后，即“放着”，不能放在宾语“拮抗剂”之后。 语序错误：在“把”字句中，宾语“拮抗剂”必须紧跟在介词“把”之后，不能置于主语和“把”之前。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "他正把拮抗劑著放進醫療箱裡。",
        "is_correct": false
      },
      {
        "text": "他把一袋拮抗劑放進了醫療箱裡。",
        "is_correct": false
      },
      {
        "text": "他把拮抗劑放進了醫療箱裡。",
        "is_correct": true
      },
      {
        "text": "拮抗劑他把放進了醫療箱裡。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“拮抗劑”作為具體藥物名詞，應使用“支”、“瓶”或“盒”，不能用“袋”。 體標位置錯誤：動態助詞“著”應緊跟在動詞“放”之後，即“放著”，不能放在賓語“拮抗劑”之後。 語序錯誤：在“把”字句中，賓語“拮抗劑”必須緊跟在介詞“把”之後，不能置於主語和“把”之前。",
    "target_word": "拮抗劑"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种拮抗剂正通过了测试。",
      "is_correct": false
    },
    {
      "text": "已经通过了测试这种拮抗剂。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂们已经通过了测试。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂已经通过了测试。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：'拮抗剂'作为物质名词或专业术语，通常不加复数后缀'们'，且此处未使用合适的量词。 体标选用错误：'正'表示动作正在进行，而'通过测试'是一个完成性事件，应使用'已经'或'了'。 语序错误：宾语'这种拮抗剂'被错误地放在了动补短语'通过了测试'之后，破坏了正常的'主-谓-宾'语序。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "這種拮抗劑正通過了測試。",
        "is_correct": false
      },
      {
        "text": "已經通過了測試這種拮抗劑。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑們已經通過了測試。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑已經通過了測試。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：'拮抗劑'作為物質名詞或專業術語，通常不加複數字尾'們'，且此處未使用合適的量詞。 體標選用錯誤：'正'表示動作正在進行，而'通過測試'是一個完成性事件，應使用'已經'或'了'。 語序錯誤：賓語'這種拮抗劑'被錯誤地放在了動補短語'通過了測試'之後，破壞了正常的'主-謂-賓'語序。",
    "target_word": "拮抗劑"
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

## sense 11315, level 7

#### Pack A
### Level 7 (sense 11315, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种拮抗剂能阻断神经信号。",
      "is_correct": true
    },
    {
      "text": "医生给病人注射了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "例如，多巴胺水平的升高可显著增加哈欠频率，而其拮抗剂则能抑制该行为。",
      "is_correct": true
    },
    {
      "text": "医生给病人注射了一个拮抗剂。",
      "is_correct": false,
      "error_description": "量词使用错误。“拮抗剂”是药物或化学物质，应使用“支”、“种”等量词，不能使用泛用量词“个”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種拮抗劑能阻斷神經訊號。",
        "is_correct": true
      },
      {
        "text": "醫生給病人注射了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "例如，多巴胺水平的升高可顯著增加哈欠頻率，而其拮抗劑則能抑制該行為。",
        "is_correct": true
      },
      {
        "text": "醫生給病人注射了一個拮抗劑。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“拮抗劑”是藥物或化學物質，應使用“支”、“種”等量詞，不能使用泛用量詞“個”。"
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
      "text": "研究人员发现了一件新型拮抗剂。",
      "is_correct": false,
      "error_description": "量词使用错误。‘拮抗剂’是药物或化学物质，表示种类时应用量词‘种’，表示具体包装时可用‘支’或‘瓶’，不能用用于衣物或普通事物的量词‘件’。"
    },
    {
      "text": "该拮抗剂着实降低了毒素的影响。",
      "is_correct": true
    },
    {
      "text": "这种拮抗剂的疗效非常显著。",
      "is_correct": true
    },
    {
      "text": "研究人员发现了一种新型拮抗剂。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "研究人員發現了一件新型拮抗劑。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。‘拮抗劑’是藥物或化學物質，表示種類時應用量詞‘種’，表示具體包裝時可用‘支’或‘瓶’，不能用用於衣物或普通事物的量詞‘件’。"
      },
      {
        "text": "該拮抗劑著實降低了毒素的影響。",
        "is_correct": true
      },
      {
        "text": "這種拮抗劑的療效非常顯著。",
        "is_correct": true
      },
      {
        "text": "研究人員發現了一種新型拮抗劑。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 11315, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "医生给病人注射着这种拮抗剂。",
      "is_correct": false,
      "error_description": "体标选用错误。'注射'在这里表示一个已经完成的动作，应该使用动态助词'了'来表示动作的完成，而不能使用表示动作持续的'着'。"
    },
    {
      "text": "这种拮抗剂能缓解过敏症状。",
      "is_correct": true
    },
    {
      "text": "医生给病人注射了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "例如，多巴胺水平的升高可显著增加哈欠频率，而其拮抗剂则能抑制该行为。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "醫生給病人注射著這種拮抗劑。",
        "is_correct": false,
        "error_description": "體標選用錯誤。'注射'在這裡表示一個已經完成的動作，應該使用動態助詞'了'來表示動作的完成，而不能使用表示動作持續的'著'。"
      },
      {
        "text": "這種拮抗劑能緩解過敏症狀。",
        "is_correct": true
      },
      {
        "text": "醫生給病人注射了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "例如，多巴胺水平的升高可顯著增加哈欠頻率，而其拮抗劑則能抑制該行為。",
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
      "text": "这种拮抗剂已经通过了测试。",
      "is_correct": true
    },
    {
      "text": "护士正在配置了新的拮抗剂。",
      "is_correct": false,
      "error_description": "“正在”表示动作正在进行，后面不能加表示完成的动态助词“了”，应删去“了”。"
    },
    {
      "text": "护士正在配置新的拮抗剂。",
      "is_correct": true
    },
    {
      "text": "这种拮抗剂的作用非常显著。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種拮抗劑已經通過了測試。",
        "is_correct": true
      },
      {
        "text": "護士正在配置了新的拮抗劑。",
        "is_correct": false,
        "error_description": "“正在”表示動作正在進行，後面不能加表示完成的動態助詞“了”，應刪去“了”。"
      },
      {
        "text": "護士正在配置新的拮抗劑。",
        "is_correct": true
      },
      {
        "text": "這種拮抗劑的作用非常顯著。",
        "is_correct": true
      }
    ]
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
    "强效",
    "昂贵",
    "微弱",
    "迅速"
  ],
  "explanation": "正确。'强效'修饰'抗精神病药物'，表示药物具有很强的效力，符合语境。",
  "distractor_tags": {},
  "word_definition": "指药物或方法等有很强的效力或作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "更引人深思的是，某些___抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "original_sentence": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "correct_answer": "強效",
    "options": [
      "強效",
      "昂貴",
      "微弱",
      "迅速"
    ],
    "explanation": "正確。'強效'修飾'抗精神病藥物'，表示藥物具有很強的效力，符合語境。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法等有很強的效力或作用。",
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
      "text": "他正在使用强效着清洁剂。",
      "is_correct": false
    },
    {
      "text": "强效的他正在使用清洁剂。",
      "is_correct": false
    },
    {
      "text": "他正在使用强效清洁剂。",
      "is_correct": true
    },
    {
      "text": "他正在使用强效得清洁剂。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'强效'是形容词，不能直接加动态助词'着'来表示动作的持续。 语序错误。'强效'作为定语应紧跟中心语'清洁剂'，放在主语'他'之前破坏了句子的语法结构。 搭配错误。'得'通常用于动词或形容词后引出补语，不能用于形容词和名词之间作结构助词。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "他正在使用強效著清潔劑。",
        "is_correct": false
      },
      {
        "text": "強效的他正在使用清潔劑。",
        "is_correct": false
      },
      {
        "text": "他正在使用強效清潔劑。",
        "is_correct": true
      },
      {
        "text": "他正在使用強效得清潔劑。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'強效'是形容詞，不能直接加動態助詞'著'來表示動作的持續。 語序錯誤。'強效'作為定語應緊跟中心語'清潔劑'，放在主語'他'之前破壞了句子的語法結構。 搭配錯誤。'得'通常用於動詞或形容詞後引出補語，不能用於形容詞和名詞之間作結構助詞。",
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
    "长效",
    "高效",
    "弱效",
    "速效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法等有很强的效力或作用。",
      "explanation": "反义项：指药物或方法效力微弱，与'强效'效力强大构成反义"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "長效",
      "高效",
      "弱效",
      "速效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法等有很強的效力或作用。",
        "explanation": "反義項：指藥物或方法效力微弱，與'強效'效力強大構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "速效",
    "长效",
    "缓效",
    "弱效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法等有很强的效力或作用。",
      "explanation": "反义项：指药物或方法等效力微弱，与目标词“强效”构成反义关系。"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "速效",
      "長效",
      "緩效",
      "弱效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法等有很強的效力或作用。",
        "explanation": "反義項：指藥物或方法等效力微弱，與目標詞“強效”構成反義關係。"
      }
    }
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

#### Pack B
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
    "细碎",
    "昂贵"
  ],
  "explanation": "正确。填入“细碎”表示厨余垃圾细小零碎，符合语境。",
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
      "細碎",
      "昂貴"
    ],
    "explanation": "正確。填入“細碎”表示廚餘垃圾細小零碎，符合語境。",
    "distractor_tags": {},
    "word_definition": "細小而零碎。",
    "target_word": "細碎"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "奶奶正在缝补那些___的布条。",
  "original_sentence": "奶奶正在缝补那些细碎的布条。",
  "correct_answer": "细碎",
  "options": [
    "光滑",
    "沉重",
    "庞大",
    "细碎"
  ],
  "explanation": "正确。'细碎'形容布条细小零散，符合缝补的语境。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "奶奶正在縫補那些___的布條。",
    "original_sentence": "奶奶正在縫補那些細碎的布條。",
    "correct_answer": "細碎",
    "options": [
      "光滑",
      "沉重",
      "龐大",
      "細碎"
    ],
    "explanation": "正確。'細碎'形容布條細小零散，符合縫補的語境。",
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
      "text": "从隔壁房间细碎的笑声传了过来。",
      "is_correct": false
    },
    {
      "text": "细碎的笑声从隔壁房间传了过来。",
      "is_correct": true
    },
    {
      "text": "细碎的一阵笑声从隔壁房间传了过来。",
      "is_correct": false
    },
    {
      "text": "细碎着的笑声从隔壁房间传了过来。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：数量短语'一阵'应放在形容词'细碎的'之前，正确语序为'一阵细碎的笑声'。 体标错误：'细碎'是状态形容词，不能直接加动态助词'着'来表示动作的持续。 语序错误：处所状语'从隔壁房间'应放在主语'细碎的笑声'之后或句首，不能割裂主语和谓语。",
  "target_word": "细碎",
  "hant": {
    "sentences": [
      {
        "text": "從隔壁房間細碎的笑聲傳了過來。",
        "is_correct": false
      },
      {
        "text": "細碎的笑聲從隔壁房間傳了過來。",
        "is_correct": true
      },
      {
        "text": "細碎的一陣笑聲從隔壁房間傳了過來。",
        "is_correct": false
      },
      {
        "text": "細碎著的笑聲從隔壁房間傳了過來。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：數量短語'一陣'應放在形容詞'細碎的'之前，正確語序為'一陣細碎的笑聲'。 體標錯誤：'細碎'是狀態形容詞，不能直接加動態助詞'著'來表示動作的持續。 語序錯誤：處所狀語'從隔壁房間'應放在主語'細碎的笑聲'之後或句首，不能割裂主語和謂語。",
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
    "完整",
    "细微",
    "密集",
    "琐碎"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎。",
      "explanation": "反义项：指事物具有应有的部分，没有残缺或零散，与“细碎”的零散不集中构成反义"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "完整",
      "細微",
      "密集",
      "瑣碎"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎。",
        "explanation": "反義項：指事物具有應有的部分，沒有殘缺或零散，與“細碎”的零散不集中構成反義"
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

#### Pack B
### Level 7 (sense 11531, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我听到了一件细碎的脚步声，心里有些害怕。",
      "is_correct": false,
      "error_description": "量词使用错误。'脚步声'不能用'件'来修饰，应使用'阵'或'阵'等合适的量词。"
    },
    {
      "text": "细碎的笑声从隔壁房间传了过来。",
      "is_correct": true
    },
    {
      "text": "他说话的声音细碎，让人听不清。",
      "is_correct": true
    },
    {
      "text": "奶奶正在缝补那些细碎的布条。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我聽到了一件細碎的腳步聲，心裡有些害怕。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。'腳步聲'不能用'件'來修飾，應使用'陣'或'陣'等合適的量詞。"
      },
      {
        "text": "細碎的笑聲從隔壁房間傳了過來。",
        "is_correct": true
      },
      {
        "text": "他說話的聲音細碎，讓人聽不清。",
        "is_correct": true
      },
      {
        "text": "奶奶正在縫補那些細碎的布條。",
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
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "剑拔弩张",
  "relation": "antonym",
  "options": [
    "千钧一发",
    "错综复杂",
    "风平浪静",
    "热火朝天"
  ],
  "correct_answer": "风平浪静",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方冲突紧张，一触即发的状态。",
      "explanation": "反义项：比喻平静无事，没有冲突，与紧张冲突一触即发构成反义"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "千鈞一髮",
      "錯綜複雜",
      "風平浪靜",
      "熱火朝天"
    ],
    "correct_answer": "風平浪靜",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方衝突緊張，一觸即發的狀態。",
        "explanation": "反義項：比喻平靜無事，沒有衝突，與緊張衝突一觸即發構成反義"
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
      "text": "谈判桌上双方剑拔弩张得不肯退让一步。",
      "is_correct": false
    },
    {
      "text": "谈判桌上剑拔弩张，双方都不肯退让一步。",
      "is_correct": true
    },
    {
      "text": "双方都不肯退让一步，谈判桌上剑拔弩张。",
      "is_correct": false
    },
    {
      "text": "谈判桌上剑拔弩张着，双方都不肯退让一步。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'剑拔弩张'是状态形容词，不能加动态助词'着'来表示动作的持续。 配价错误。'剑拔弩张'不能带程度或结果补语，不能用'得'连接后续的动作状态。 语序错误。汉语通常先交代背景或场景（谈判桌上），再描述状态（剑拔弩张），最后说明具体表现（不肯退让），原句语序破坏了自然的叙事逻辑。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "談判桌上雙方劍拔弩張得不肯退讓一步。",
        "is_correct": false
      },
      {
        "text": "談判桌上劍拔弩張，雙方都不肯退讓一步。",
        "is_correct": true
      },
      {
        "text": "雙方都不肯退讓一步，談判桌上劍拔弩張。",
        "is_correct": false
      },
      {
        "text": "談判桌上劍拔弩張著，雙方都不肯退讓一步。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'劍拔弩張'是狀態形容詞，不能加動態助詞'著'來表示動作的持續。 配價錯誤。'劍拔弩張'不能帶程度或結果補語，不能用'得'連線後續的動作狀態。 語序錯誤。漢語通常先交代背景或場景（談判桌上），再描述狀態（劍拔弩張），最後說明具體表現（不肯退讓），原句語序破壞了自然的敘事邏輯。",
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
    "暗流涌动",
    "一触即发",
    "势均力敌",
    "相安无事"
  ],
  "correct_answer": "相安无事",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方冲突紧张，一触即发的状态。",
      "explanation": "反义项：指彼此相处平安和睦，没有冲突与争执，与冲突紧张相对"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "暗流湧動",
      "一觸即發",
      "勢均力敵",
      "相安無事"
    ],
    "correct_answer": "相安無事",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方衝突緊張，一觸即發的狀態。",
        "explanation": "反義項：指彼此相處平安和睦，沒有衝突與爭執，與衝突緊張相對"
      }
    }
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
      "text": "他们俩为了这点小事，弄得剑拔弩张的。",
      "is_correct": true
    },
    {
      "text": "比赛前，双方队员剑拔弩张，气氛非常紧张。",
      "is_correct": true
    },
    {
      "text": "比赛前，双方队员剑拔弩张着，气氛非常紧张。",
      "is_correct": false,
      "error_description": "体标误用。“剑拔弩张”本身已包含状态义，作谓语时不需要加动态助词“着”，直接说“剑拔弩张”即可。"
    },
    {
      "text": "玩家在“敌对公会”的竞技场厮杀后，可能在同一资源区合作采矿；竞争对手在排行榜上剑拔弩张，却又在社区论坛共享战术心得。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他們倆為了這點小事，弄得劍拔弩張的。",
        "is_correct": true
      },
      {
        "text": "比賽前，雙方隊員劍拔弩張，氣氛非常緊張。",
        "is_correct": true
      },
      {
        "text": "比賽前，雙方隊員劍拔弩張著，氣氛非常緊張。",
        "is_correct": false,
        "error_description": "體標誤用。“劍拔弩張”本身已包含狀態義，作謂語時不需要加動態助詞“著”，直接說“劍拔弩張”即可。"
      },
      {
        "text": "玩家在“敵對公會”的競技場廝殺後，可能在同一資源區合作採礦；競爭對手在排行榜上劍拔弩張，卻又在社群論壇共享戰術心得。",
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
      "text": "双方剑拔弩张在谈判桌上，都不肯退让一步。",
      "is_correct": false,
      "error_description": "语序错误。表示处所的词语“谈判桌上”应放在主语“双方”之前或谓语“剑拔弩张”之前作状语，不能放在形容词谓语之后。"
    },
    {
      "text": "谈判桌上剑拔弩张，双方都不肯退让一步。",
      "is_correct": true
    },
    {
      "text": "刚才还剑拔弩张的他们，现在又一起笑了。",
      "is_correct": true
    },
    {
      "text": "会议室里剑拔弩张，大家都在争论这个问题。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "雙方劍拔弩張在談判桌上，都不肯退讓一步。",
        "is_correct": false,
        "error_description": "語序錯誤。表示處所的詞語“談判桌上”應放在主語“雙方”之前或謂語“劍拔弩張”之前作狀語，不能放在形容詞謂語之後。"
      },
      {
        "text": "談判桌上劍拔弩張，雙方都不肯退讓一步。",
        "is_correct": true
      },
      {
        "text": "剛才還劍拔弩張的他們，現在又一起笑了。",
        "is_correct": true
      },
      {
        "text": "會議室裡劍拔弩張，大家都在爭論這個問題。",
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
