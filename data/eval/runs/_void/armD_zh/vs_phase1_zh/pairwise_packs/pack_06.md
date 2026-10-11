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


## sense 10803, level 3

#### Pack A
### Level 3 (sense 10803, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "然而，技术革新若无消费观念的同步转变，相关部门需___新技术纳入现有的市场准入规则中进行规范管理，以确保产业平稳发展。",
  "original_sentence": "然而，技术革新若无消费观念的同步转变，相关部门需将新技术纳入现有的市场准入规则中进行规范管理，以确保产业平稳发展。",
  "correct_answer": "将",
  "options": [
    "将",
    "被",
    "给",
    "对"
  ],
  "explanation": "正确。'将'作为介词，引出'纳入'的受事'新技术'，符合书面语表达习惯。",
  "distractor_tags": {},
  "word_definition": "把不同的事物统一纳入某种规则或系统中进行管理或安排",
  "target_word": "将",
  "hant": {
    "sentence_with_blank": "然而，技術革新若無消費觀念的同步轉變，相關部門需___新技術納入現有的市場準入規則中進行規範管理，以確保產業平穩發展。",
    "original_sentence": "然而，技術革新若無消費觀念的同步轉變，相關部門需將新技術納入現有的市場準入規則中進行規範管理，以確保產業平穩發展。",
    "correct_answer": "將",
    "options": [
      "將",
      "被",
      "給",
      "對"
    ],
    "explanation": "正確。'將'作為介詞，引出'納入'的受事'新技術'，符合書面語表達習慣。",
    "distractor_tags": {},
    "word_definition": "把不同的事物統一納入某種規則或系統中進行管理或安排",
    "target_word": "將"
  }
}
```

#### Pack B
### Level 3 (sense 10803, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "然而，技术革新若不能___消费观念的同步转变纳入其推广与应用的战略系统中进行统筹管理，最终往往会举步维艰。",
  "original_sentence": "然而，技术革新若不能将消费观念的同步转变纳入其推广与应用的战略系统中进行统筹管理，最终往往会举步维艰。",
  "correct_answer": "将",
  "options": [
    "将",
    "给",
    "替",
    "对"
  ],
  "explanation": "正确。'将'在此处作介词，引出动作'纳入'的受事'消费观念的同步转变'，符合书面语规范。",
  "distractor_tags": {},
  "word_definition": "把不同的事物统一纳入某种规则或系统中进行管理或安排",
  "target_word": "将",
  "hant": {
    "sentence_with_blank": "然而，技術革新若不能___消費觀念的同步轉變納入其推廣與應用的戰略系統中進行統籌管理，最終往往會舉步維艱。",
    "original_sentence": "然而，技術革新若不能將消費觀念的同步轉變納入其推廣與應用的戰略系統中進行統籌管理，最終往往會舉步維艱。",
    "correct_answer": "將",
    "options": [
      "將",
      "給",
      "替",
      "對"
    ],
    "explanation": "正確。'將'在此處作介詞，引出動作'納入'的受事'消費觀念的同步轉變'，符合書面語規範。",
    "distractor_tags": {},
    "word_definition": "把不同的事物統一納入某種規則或系統中進行管理或安排",
    "target_word": "將"
  }
}
```

---

## sense 10803, level 6

#### Pack A
### Level 6 (sense 10803, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那些能将法律义务转化为治理创新的企业，在高度规制的AI时代将确立不可替代的制度性优势。",
      "is_correct": false
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立了不可替代的制度性优势。",
      "is_correct": false
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立不可替代的制度性优势。",
      "is_correct": true
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立着不可替代的制度性优势。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：第二个“将”作为介词，必须紧挨在其引出的受事“不可替代的制度性优势”之前，原句将其错置于主语“企业”之后、状语“在……”之前，导致介词悬空，破坏了“主题—评论”结构。 体标位置错误：介词“将”字句通常表示对事物的处置，具有完成或实现的意味，句末不应再加动态助词“了”。“了”应放在动词“确立”之后（即“确立了”），或者直接省略，原句将其错放在句末，导致体标记位置错误。 体标选用错误：“将”字句强调对受事的处置及结果的达成，通常与完成或实现体兼容；而“着”表示动作或状态的持续，与“确立”这一瞬间达成结果的动词及“将”字句的处置语义相冲突，属于体标记选用错误。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "那些能將法律義務轉化為治理創新的企業，在高度規制的AI時代將確立不可替代的制度性優勢。",
        "is_correct": false
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立了不可替代的制度性優勢。",
        "is_correct": false
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立不可替代的制度性優勢。",
        "is_correct": true
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立著不可替代的制度性優勢。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：第二個“將”作為介詞，必須緊挨在其引出的受事“不可替代的制度性優勢”之前，原句將其錯置於主語“企業”之後、狀語“在……”之前，導致介詞懸空，破壞了“主題—評論”結構。 體標位置錯誤：介詞“將”字句通常表示對事物的處置，具有完成或實現的意味，句末不應再加動態助詞“了”。“了”應放在動詞“確立”之後（即“確立了”），或者直接省略，原句將其錯放在句末，導致體標記位置錯誤。 體標選用錯誤：“將”字句強調對受事的處置及結果的達成，通常與完成或實現體相容；而“著”表示動作或狀態的持續，與“確立”這一瞬間達成結果的動詞及“將”字句的處置語義相沖突，屬於體標記選用錯誤。",
    "target_word": "將"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们心里将把这些规则记。",
      "is_correct": false
    },
    {
      "text": "我们将这些规则记在心。",
      "is_correct": false
    },
    {
      "text": "我们将这些规则记在心里。",
      "is_correct": true
    },
    {
      "text": "我们将着这些规则记在心里。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误。'记在心里'表示动作已完成或状态已达成，应使用表示完成的'了'，而不能使用表示动作持续或进行的'着'。 语序错误。'将'字句的基本结构为'主语+将+宾语+动词+其他成分'，此处将处所状语'心里'和宾语'这些规则'的位置颠倒，破坏了正常的句法结构。 方向/结果补语误用。'记'作为动词，后面需要接趋向补语'里'或结果补语'住'来完善语义，单用'在心'不符合现代汉语的表达习惯，语义不完整。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "我們心裡將把這些規則記。",
        "is_correct": false
      },
      {
        "text": "我們將這些規則記在心。",
        "is_correct": false
      },
      {
        "text": "我們將這些規則記在心裡。",
        "is_correct": true
      },
      {
        "text": "我們將著這些規則記在心裡。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤。'記在心裡'表示動作已完成或狀態已達成，應使用表示完成的'了'，而不能使用表示動作持續或進行的'著'。 語序錯誤。'將'字句的基本結構為'主語+將+賓語+動詞+其他成分'，此處將處所狀語'心裡'和賓語'這些規則'的位置顛倒，破壞了正常的句法結構。 方向/結果補語誤用。'記'作為動詞，後面需要接趨向補語'裡'或結果補語'住'來完善語義，單用'在心'不符合現代漢語的表達習慣，語義不完整。",
    "target_word": "將"
  }
}
```

#### Pack B
### Level 6 (sense 10803, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那些企业正将各项合规要求纳入着内部治理体系进行统筹管理。",
      "is_correct": false
    },
    {
      "text": "那些能将各项合规要求纳入内部治理体系进行统筹管理的企业，能够在高度规制的AI时代确立不可替代的制度性优势。",
      "is_correct": true
    },
    {
      "text": "那些企业将各项合规要求能纳入内部治理体系进行统筹管理。",
      "is_correct": false
    },
    {
      "text": "那些企业能将各项合规要求纳入起内部治理体系进行统筹管理。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：能愿动词“能”应放在介词“将”之前，即“能将”，原句将其置于“将”之后破坏了介词结构的完整性。 体标选用错误：“纳入”表示动作的完成与结果，不能与表示持续状态的动态助词“着”连用，应去掉“着”。 结果补语误用：“纳入”中的“入”已包含动作的结果与方向，不能再额外添加“起”等结果补语，造成语义重复与搭配不当。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "那些企業正將各項合規要求納入著內部治理體系進行統籌管理。",
        "is_correct": false
      },
      {
        "text": "那些能將各項合規要求納入內部治理體系進行統籌管理的企業，能夠在高度規制的AI時代確立不可替代的制度性優勢。",
        "is_correct": true
      },
      {
        "text": "那些企業將各項合規要求能納入內部治理體系進行統籌管理。",
        "is_correct": false
      },
      {
        "text": "那些企業能將各項合規要求納入起內部治理體系進行統籌管理。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：能願動詞“能”應放在介詞“將”之前，即“能將”，原句將其置於“將”之後破壞了介詞結構的完整性。 體標選用錯誤：“納入”表示動作的完成與結果，不能與表示持續狀態的動態助詞“著”連用，應去掉“著”。 結果補語誤用：“納入”中的“入”已包含動作的結果與方向，不能再額外新增“起”等結果補語，造成語義重複與搭配不當。",
    "target_word": "將"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我将你的建议纳入考虑范围。",
      "is_correct": true
    },
    {
      "text": "我将你的建议昨天纳入考虑范围。",
      "is_correct": false
    },
    {
      "text": "我将了你的建议纳入考虑范围。",
      "is_correct": false
    },
    {
      "text": "我将你的建议纳入出去考虑范围。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词'了'应放在动词'纳入'之后，即'将你的建议纳入了考虑范围'，不能放在介词'将'之后。 语序错误：时间状语'昨天'应放在介词'将'之前，即'我昨天将你的建议纳入考虑范围'，不能放在介词和宾语之间。 结果补语误用：'纳入'本身已包含'进入'的方向意义，添加表示向外方向的'出去'会导致语义矛盾且不符合语法。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "我將你的建議納入考慮範圍。",
        "is_correct": true
      },
      {
        "text": "我將你的建議昨天納入考慮範圍。",
        "is_correct": false
      },
      {
        "text": "我將了你的建議納入考慮範圍。",
        "is_correct": false
      },
      {
        "text": "我將你的建議納入出去考慮範圍。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'應放在動詞'納入'之後，即'將你的建議納入了考慮範圍'，不能放在介詞'將'之後。 語序錯誤：時間狀語'昨天'應放在介詞'將'之前，即'我昨天將你的建議納入考慮範圍'，不能放在介詞和賓語之間。 結果補語誤用：'納入'本身已包含'進入'的方向意義，新增表示向外方向的'出去'會導致語義矛盾且不符合語法。",
    "target_word": "將"
  }
}
```

---

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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "联合国环境规划署在1972年斯德哥尔摩人类环境会议后，将纳入此类标准化符号全球环境治理的技术建议之中。",
      "is_correct": false,
      "error_description": "语序错误。'将'字句中，介词'将'的宾语（此类标准化符号）必须紧跟在'将'之后，动词（纳入）之前。原句将宾语放在了动词之后，导致句子结构混乱。"
    },
    {
      "text": "联合国环境规划署在1972年斯德哥尔摩人类环境会议后，将此类标准化符号纳入全球环境治理的技术建议之中。",
      "is_correct": true
    },
    {
      "text": "首先，训练数据的采集与使用需满足“知情—同意”框架的实质要求，这意味着企业不能仅依赖用户协议中的概括性条款，而应通过分层披露机制，清晰说明如何将数据纳入模型训练的具体场景与类别管理系统中，尤其在涉及个人敏感信息或生成式内容时，须实现可验证的用户授权路径。",
      "is_correct": true
    },
    {
      "text": "可以预见，未来立法会将全生命周期管理纳入法治轨道，从原料提取、产品设计到废弃物回收，形成统一的闭环控制体系。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "聯合國環境規劃署在1972年斯德哥爾摩人類環境會議後，將納入此類標準化符號全球環境治理的技術建議之中。",
        "is_correct": false,
        "error_description": "語序錯誤。'將'字句中，介詞'將'的賓語（此類標準化符號）必須緊跟在'將'之後，動詞（納入）之前。原句將賓語放在了動詞之後，導致句子結構混亂。"
      },
      {
        "text": "聯合國環境規劃署在1972年斯德哥爾摩人類環境會議後，將此類標準化符號納入全球環境治理的技術建議之中。",
        "is_correct": true
      },
      {
        "text": "首先，訓練資料的採集與使用需滿足“知情—同意”框架的實質要求，這意味著企業不能僅依賴使用者協議中的概括性條款，而應通過分層披露機制，清晰說明如何將資料納入模型訓練的具體場景與類別管理系統中，尤其在涉及個人敏感資訊或生成式內容時，須實現可驗證的使用者授權路徑。",
        "is_correct": true
      },
      {
        "text": "可以預見，未來立法會將全生命週期管理納入法治軌道，從原料提取、產品設計到廢棄物回收，形成統一的閉環控制體系。",
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
      "text": "老师将分成了我们几个小组来讨论。",
      "is_correct": false,
      "error_description": "在“将”字句中，“将”的宾语（动作的承受者）必须紧跟在“将”之后、动词之前。原句中宾语“我们”错放在了动词“分成”之后，造成了语序错误。"
    },
    {
      "text": "老师将我们分成了几个小组来讨论。",
      "is_correct": true
    },
    {
      "text": "我们将这些规则记在心里。",
      "is_correct": true
    },
    {
      "text": "然而，技术革新若不能将消费观念的同步转变纳入其推广与应用的战略系统中进行统筹管理，最终往往会举步维艰。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師將分成了我們幾個小組來討論。",
        "is_correct": false,
        "error_description": "在“將”字句中，“將”的賓語（動作的承受者）必須緊跟在“將”之後、動詞之前。原句中賓語“我們”錯放在了動詞“分成”之後，造成了語序錯誤。"
      },
      {
        "text": "老師將我們分成了幾個小組來討論。",
        "is_correct": true
      },
      {
        "text": "我們將這些規則記在心裡。",
        "is_correct": true
      },
      {
        "text": "然而，技術革新若不能將消費觀念的同步轉變納入其推廣與應用的戰略系統中進行統籌管理，最終往往會舉步維艱。",
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
      "text": "拮抗剂着了药效比原来的药更好。",
      "is_correct": false
    },
    {
      "text": "拮抗剂的药效比原来的药更好。",
      "is_correct": true
    },
    {
      "text": "药效比原来的药拮抗剂更好。",
      "is_correct": false
    },
    {
      "text": "拮抗剂们的药效比原来的药更好。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'拮抗剂'作为专业物质名词，通常不可数，不能直接加复数后缀'们'。 体标位置错误：'着'表示动作进行或状态持续，不能直接放在名词'拮抗剂'后表示其具有药效。 语序错误：主语'拮抗剂的药效'被错误拆分，导致'拮抗剂'与'药效'的所属关系混乱，句子结构破裂。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "拮抗劑著了藥效比原來的藥更好。",
        "is_correct": false
      },
      {
        "text": "拮抗劑的藥效比原來的藥更好。",
        "is_correct": true
      },
      {
        "text": "藥效比原來的藥拮抗劑更好。",
        "is_correct": false
      },
      {
        "text": "拮抗劑們的藥效比原來的藥更好。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'拮抗劑'作為專業物質名詞，通常不可數，不能直接加複數字尾'們'。 體標位置錯誤：'著'表示動作進行或狀態持續，不能直接放在名詞'拮抗劑'後表示其具有藥效。 語序錯誤：主語'拮抗劑的藥效'被錯誤拆分，導致'拮抗劑'與'藥效'的所屬關係混亂，句子結構破裂。",
    "target_word": "拮抗劑"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "很有效对治疗该病这种拮抗剂。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂对治疗该病很有效了。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂对治疗该病很有效过。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂对治疗该病很有效。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：句末误加动态助词“了”，陈述药物客观疗效时不应使用表示状态改变的“了”。 语序错误：状语“对治疗该病”和主语“这种拮抗剂”位置错乱，破坏了正常的“主语+状语+谓语”结构。 体标位置/选用错误：误用经历体标记“过”，药物的客观有效性属于属性状态，不能用表示过去经历的“过”。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "很有效對治療該病這種拮抗劑。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑對治療該病很有效了。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑對治療該病很有效過。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑對治療該病很有效。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：句末誤加動態助詞“了”，陳述藥物客觀療效時不應使用表示狀態改變的“了”。 語序錯誤：狀語“對治療該病”和主語“這種拮抗劑”位置錯亂，破壞了正常的“主語+狀語+謂語”結構。 體標位置/選用錯誤：誤用經歷體標記“過”，藥物的客觀有效性屬於屬性狀態，不能用表示過去經歷的“過”。",
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
      "text": "医生给病人使用了一种新拮抗剂。",
      "is_correct": true
    },
    {
      "text": "医生给病人使用了一只新拮抗剂。",
      "is_correct": false,
      "error_description": "量词使用错误。'拮抗剂'作为药物或化学物质，应使用量词'种'，不能使用用于动物的量词'只'。"
    },
    {
      "text": "这种拮抗剂能阻止毒素发挥作用。",
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
        "text": "醫生給病人使用了一種新拮抗劑。",
        "is_correct": true
      },
      {
        "text": "醫生給病人使用了一隻新拮抗劑。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。'拮抗劑'作為藥物或化學物質，應使用量詞'種'，不能使用用於動物的量詞'只'。"
      },
      {
        "text": "這種拮抗劑能阻止毒素髮揮作用。",
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
      "text": "他昨天在书上关于拮抗剂看过图。",
      "is_correct": false,
      "error_description": "语序错误。介词短语“关于拮抗剂”应作为定语修饰“图”，放在“图”的前面，而不是放在动词“看过”的前面。"
    },
    {
      "text": "我们学过关于受体拮抗剂的知识。",
      "is_correct": true
    },
    {
      "text": "他昨天在书上看过关于拮抗剂的图。",
      "is_correct": true
    },
    {
      "text": "这种拮抗剂对治疗该病很有效。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他昨天在書上關於拮抗劑看過圖。",
        "is_correct": false,
        "error_description": "語序錯誤。介詞短語“關於拮抗劑”應作為定語修飾“圖”，放在“圖”的前面，而不是放在動詞“看過”的前面。"
      },
      {
        "text": "我們學過關於受體拮抗劑的知識。",
        "is_correct": true
      },
      {
        "text": "他昨天在書上看過關於拮抗劑的圖。",
        "is_correct": true
      },
      {
        "text": "這種拮抗劑對治療該病很有效。",
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

#### Pack B
### Level 3 (sense 11319, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "更引人深思的是，某些___抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "original_sentence": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "correct_answer": "强效",
  "options": [
    "长效",
    "强效",
    "特效",
    "速效"
  ],
  "explanation": "正确。强效修饰抗精神病药物，表示其具有非常强大的药理作用，符合语境。",
  "distractor_tags": {},
  "word_definition": "指药物或清洁用品等具有非常强大的作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "更引人深思的是，某些___抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "original_sentence": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "correct_answer": "強效",
    "options": [
      "長效",
      "強效",
      "特效",
      "速效"
    ],
    "explanation": "正確。強效修飾抗精神病藥物，表示其具有非常強大的藥理作用，符合語境。",
    "distractor_tags": {},
    "word_definition": "指藥物或清潔用品等具有非常強大的作用。",
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
      "text": "医生给他开了止痛的强效药。",
      "is_correct": false
    },
    {
      "text": "医生给他开了强效得很的止痛药。",
      "is_correct": false
    },
    {
      "text": "医生给他开了一副强效的止痛药。",
      "is_correct": false
    },
    {
      "text": "医生给他开了强效的止痛药。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：“强效”本身已包含程度意味，不能像普通性质形容词那样直接加“得很”作补语，应使用“非常强效”或“强效的”。 语序错误：在汉语中，表示性质或状态的形容词（强效）通常应放在表示用途或类别的定语（止痛）之前，正确语序应为“强效的止痛药”。 量词使用错误：“药”作为西药或一般药物时，通常用量词“种”、“瓶”或“片”，而“副”通常用于中药（如一副中药）或眼镜等，此处量词搭配不当。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "醫生給他開了止痛的強效藥。",
        "is_correct": false
      },
      {
        "text": "醫生給他開了強效得很的止痛藥。",
        "is_correct": false
      },
      {
        "text": "醫生給他開了一副強效的止痛藥。",
        "is_correct": false
      },
      {
        "text": "醫生給他開了強效的止痛藥。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：“強效”本身已包含程度意味，不能像普通性質形容詞那樣直接加“得很”作補語，應使用“非常強效”或“強效的”。 語序錯誤：在漢語中，表示性質或狀態的形容詞（強效）通常應放在表示用途或類別的定語（止痛）之前，正確語序應為“強效的止痛藥”。 量詞使用錯誤：“藥”作為西藥或一般藥物時，通常用量詞“種”、“瓶”或“片”，而“副”通常用於中藥（如一副中藥）或眼鏡等，此處量詞搭配不當。",
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
    "弱效",
    "速效",
    "特效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或清洁用品等具有非常强大的作用。",
      "explanation": "反义项：指药物或清洁用品等效力微弱，与目标词构成反义关系"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "長效",
      "弱效",
      "速效",
      "特效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或清潔用品等具有非常強大的作用。",
        "explanation": "反義項：指藥物或清潔用品等效力微弱，與目標詞構成反義關係"
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
      "text": "买药时我们都很看重强效。",
      "is_correct": true
    },
    {
      "text": "买药时我们都很强效看重。",
      "is_correct": false
    },
    {
      "text": "买药时我们都很看重强效了。",
      "is_correct": false
    },
    {
      "text": "买药时我们都很看重强效着。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'强效'是形容词，不能直接加动态助词'着'来表示动作的持续。 体标选用错误。'强效'表示事物的属性状态，不能加'了'表示状态的变化或完成。 语序错误。'强效'不能作状语修饰动词'看重'，它只能作定语修饰名词或作谓语/补语。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "買藥時我們都很看重強效。",
        "is_correct": true
      },
      {
        "text": "買藥時我們都很強效看重。",
        "is_correct": false
      },
      {
        "text": "買藥時我們都很看重強效了。",
        "is_correct": false
      },
      {
        "text": "買藥時我們都很看重強效著。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'強效'是形容詞，不能直接加動態助詞'著'來表示動作的持續。 體標選用錯誤。'強效'表示事物的屬性狀態，不能加'了'表示狀態的變化或完成。 語序錯誤。'強效'不能作狀語修飾動詞'看重'，它只能作定語修飾名詞或作謂語/補語。",
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
      "definition": "指药物或清洁用品等具有非常强大的作用。",
      "explanation": "反义项：指药物或清洁用品等效力微弱，与「强效」的「强大效力」义直接相反"
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
        "definition": "指藥物或清潔用品等具有非常強大的作用。",
        "explanation": "反義項：指藥物或清潔用品等效力微弱，與「強效」的「強大效力」義直接相反"
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

---

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
      "text": "妈妈把强效的清洁剂昨天在超市买了。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，时间状语（昨天）和地点状语（在超市）应该放在“把”字之前，而不是“把”字之后。"
    },
    {
      "text": "这种强效的洗衣液去污很快。",
      "is_correct": true
    },
    {
      "text": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
      "is_correct": true
    },
    {
      "text": "妈妈买了一些强效的清洁剂。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "媽媽把強效的清潔劑昨天在超市買了。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，時間狀語（昨天）和地點狀語（在超市）應該放在“把”字之前，而不是“把”字之後。"
      },
      {
        "text": "這種強效的洗衣液去汙很快。",
        "is_correct": true
      },
      {
        "text": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
        "is_correct": true
      },
      {
        "text": "媽媽買了一些強效的清潔劑。",
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
      "text": "这种除菌喷雾的效果很强效。",
      "is_correct": true
    },
    {
      "text": "他买了感冒药强效的。",
      "is_correct": false,
      "error_description": "语序错误。形容词“强效”作定语修饰名词“感冒药”时，应该放在名词前面，并使用“的”连接，不能放在名词后面。"
    },
    {
      "text": "买药时我们都很看重强效。",
      "is_correct": true
    },
    {
      "text": "他把强效的感冒药喝了下去。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種除菌噴霧的效果很強效。",
        "is_correct": true
      },
      {
        "text": "他買了感冒藥強效的。",
        "is_correct": false,
        "error_description": "語序錯誤。形容詞“強效”作定語修飾名詞“感冒藥”時，應該放在名詞前面，並使用“的”連線，不能放在名詞後面。"
      },
      {
        "text": "買藥時我們都很看重強效。",
        "is_correct": true
      },
      {
        "text": "他把強效的感冒藥喝了下去。",
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
    "昂贵",
    "完整",
    "细碎",
    "庞大"
  ],
  "explanation": "正确。'细碎'形容厨余垃圾细小而零碎，符合语境。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解___廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "original_sentence": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
    "correct_answer": "細碎",
    "options": [
      "昂貴",
      "完整",
      "細碎",
      "龐大"
    ],
    "explanation": "正確。'細碎'形容廚餘垃圾細小而零碎，符合語境。",
    "distractor_tags": {},
    "word_definition": "細小而零碎。",
    "target_word": "細碎"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我喜欢收集那些___的小物件。",
  "original_sentence": "我喜欢收集那些细碎的小物件。",
  "correct_answer": "细碎",
  "options": [
    "昂贵",
    "庞大",
    "光滑",
    "细碎"
  ],
  "explanation": "正确。“细碎”形容小物件细小而零散，符合收集小物件的语境。",
  "distractor_tags": {},
  "word_definition": "细小而零碎。",
  "target_word": "细碎",
  "hant": {
    "sentence_with_blank": "我喜歡收集那些___的小物件。",
    "original_sentence": "我喜歡收集那些細碎的小物件。",
    "correct_answer": "細碎",
    "options": [
      "昂貴",
      "龐大",
      "光滑",
      "細碎"
    ],
    "explanation": "正確。“細碎”形容小物件細小而零散，符合收集小物件的語境。",
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他把细碎进簸箕里的石头扫了。",
      "is_correct": false
    },
    {
      "text": "石头细碎了他扫进簸箕里。",
      "is_correct": false
    },
    {
      "text": "他把细碎的石头扫进了簸箕里。",
      "is_correct": true
    },
    {
      "text": "他把很细碎石头扫进了簸箕里。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误：'细碎'是双音节形容词，修饰名词时不能直接加程度副词'很'而不加'的'，应改为'很细碎的石头'或'细碎的石头'。 语序错误：'细碎'是形容词，不能像动词那样带动态助词'了'并放在主语后作谓语，导致句子结构混乱，应改为'他把细碎的石头扫进了簸箕里'。 搭配与句法错误：'细碎'是形容词，不能带趋向补语'进'，也不能直接修饰动词短语，此处误将其当作动词使用。",
  "target_word": "细碎",
  "hant": {
    "sentences": [
      {
        "text": "他把細碎進簸箕裡的石頭掃了。",
        "is_correct": false
      },
      {
        "text": "石頭細碎了他掃進簸箕裡。",
        "is_correct": false
      },
      {
        "text": "他把細碎的石頭掃進了簸箕裡。",
        "is_correct": true
      },
      {
        "text": "他把很細碎石頭掃進了簸箕裡。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤：'細碎'是雙音節形容詞，修飾名詞時不能直接加程度副詞'很'而不加'的'，應改為'很細碎的石頭'或'細碎的石頭'。 語序錯誤：'細碎'是形容詞，不能像動詞那樣帶動態助詞'了'並放在主語後作謂語，導致句子結構混亂，應改為'他把細碎的石頭掃進了簸箕裡'。 搭配與句法錯誤：'細碎'是形容詞，不能帶趨向補語'進'，也不能直接修飾動詞短語，此處誤將其當作動詞使用。",
    "target_word": "細碎"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "细碎",
  "relation": "antonym",
  "options": [
    "零散",
    "粗糙",
    "完整",
    "光滑"
  ],
  "correct_answer": "完整",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "细小而零碎。",
      "explanation": "反义：细碎指细小零碎，完整指整体无缺，构成反义"
    }
  },
  "hant": {
    "word": "細碎",
    "relation": "antonym",
    "options": [
      "零散",
      "粗糙",
      "完整",
      "光滑"
    ],
    "correct_answer": "完整",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "細小而零碎。",
        "explanation": "反義：細碎指細小零碎，完整指整體無缺，構成反義"
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
      "text": "那些细碎了的往事，我都记得。",
      "is_correct": false
    },
    {
      "text": "往事那些细碎的，我都记得。",
      "is_correct": false
    },
    {
      "text": "那些件细碎的往事，我都记得。",
      "is_correct": false
    },
    {
      "text": "那些细碎的往事，我都记得。",
      "is_correct": true
    }
  ],
  "explanation": "体标错误：“细碎”是状态形容词，不能加动态助词“了”来表示动作的完成或状态的改变。 语序错误：定语“细碎的”必须放在中心语“往事”之前，不能后置，破坏了正常的偏正结构。 量词错误：“往事”是抽象名词，不能用用于具体物品的个体量词“件”来修饰，属于量词搭配不当。",
  "target_word": "细碎",
  "hant": {
    "sentences": [
      {
        "text": "那些細碎了的往事，我都記得。",
        "is_correct": false
      },
      {
        "text": "往事那些細碎的，我都記得。",
        "is_correct": false
      },
      {
        "text": "那些件細碎的往事，我都記得。",
        "is_correct": false
      },
      {
        "text": "那些細碎的往事，我都記得。",
        "is_correct": true
      }
    ],
    "explanation": "體標錯誤：“細碎”是狀態形容詞，不能加動態助詞“了”來表示動作的完成或狀態的改變。 語序錯誤：定語“細碎的”必須放在中心語“往事”之前，不能後置，破壞了正常的偏正結構。 量詞錯誤：“往事”是抽象名詞，不能用用於具體物品的個體量詞“件”來修飾，屬於量詞搭配不當。",
    "target_word": "細碎"
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
