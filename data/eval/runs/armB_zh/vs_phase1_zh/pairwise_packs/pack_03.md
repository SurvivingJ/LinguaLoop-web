# Pairwise review pack 03

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


## sense 10117, level 6

#### Pack A
### Level 6 (sense 10117, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个计划庞大地完成了。",
      "is_correct": false
    },
    {
      "text": "我们面对着计划庞大一个。",
      "is_correct": false
    },
    {
      "text": "我们面对着一个庞大的计划。",
      "is_correct": true
    },
    {
      "text": "我们面对着一个庞大了的计划。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。'庞大'是状态形容词，不能直接加动态助词'了'来表示动作的完成或状态的改变，应去掉'了'。 语序错误。在汉语中，数量短语和形容词定语修饰名词时，应放在名词之前，正确语序为'一个庞大的计划'。 句法功能错误。'庞大'是形容词，通常作定语或谓语，不能加'地'作状语来修饰动词'完成'。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "這個計劃龐大地完成了。",
        "is_correct": false
      },
      {
        "text": "我們面對著計劃龐大一個。",
        "is_correct": false
      },
      {
        "text": "我們面對著一個龐大的計劃。",
        "is_correct": true
      },
      {
        "text": "我們面對著一個龐大了的計劃。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。'龐大'是狀態形容詞，不能直接加動態助詞'了'來表示動作的完成或狀態的改變，應去掉'了'。 語序錯誤。在漢語中，數量短語和形容詞定語修飾名詞時，應放在名詞之前，正確語序為'一個龐大的計劃'。 句法功能錯誤。'龐大'是形容詞，通常作定語或謂語，不能加'地'作狀語來修飾動詞'完成'。",
    "target_word": "龐大"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "庞大",
  "relation": "antonym",
  "options": [
    "微小",
    "单薄",
    "复杂",
    "巨大"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量、力量等非常大，超过一般水平。",
      "explanation": "反义项：形容体积、规模或数量等非常小，与‘庞大’构成反义。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "微小",
      "單薄",
      "複雜",
      "巨大"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量、力量等非常大，超過一般水平。",
        "explanation": "反義項：形容體積、規模或數量等非常小，與‘龐大’構成反義。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10117, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这家公司的员工队伍被庞大了。",
      "is_correct": false
    },
    {
      "text": "这家公司的员工队伍非常庞大了着。",
      "is_correct": false
    },
    {
      "text": "这家公司的员工队伍非常庞大。",
      "is_correct": true
    },
    {
      "text": "庞大非常这家公司的员工队伍。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“庞大”是状态形容词，表示一种性质，不能直接加动态助词“着”来表示进行或持续状态。 语序错误：形容词谓语前应有主语，副词“非常”应紧贴形容词“庞大”，原句语序混乱，不符合汉语主谓结构习惯。 配价/语态错误：“庞大”是不及物性质的形容词，不能用于“被”字句构成被动语态，因为不存在一个施事者去“庞大”这个队伍。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "這家公司的員工隊伍被龐大了。",
        "is_correct": false
      },
      {
        "text": "這家公司的員工隊伍非常龐大了著。",
        "is_correct": false
      },
      {
        "text": "這家公司的員工隊伍非常龐大。",
        "is_correct": true
      },
      {
        "text": "龐大非常這家公司的員工隊伍。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“龐大”是狀態形容詞，表示一種性質，不能直接加動態助詞“著”來表示進行或持續狀態。 語序錯誤：形容詞謂語前應有主語，副詞“非常”應緊貼形容詞“龐大”，原句語序混亂，不符合漢語主謂結構習慣。 配價/語態錯誤：“龐大”是不及物性質的形容詞，不能用於“被”字句構成被動語態，因為不存在一個施事者去“龐大”這個隊伍。",
    "target_word": "龐大"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "庞大",
  "relation": "antonym",
  "options": [
    "微小",
    "繁杂",
    "宏伟",
    "巨大"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "形容体积、规模或数量极小，与“庞大”构成反义关系"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "微小",
      "繁雜",
      "宏偉",
      "巨大"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "形容體積、規模或數量極小，與“龐大”構成反義關係"
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
      "text": "这个工程被庞大得很困难。",
      "is_correct": false
    },
    {
      "text": "我们庞大了这个计划。",
      "is_correct": false
    },
    {
      "text": "这是一个庞大的工程，需要很多人。",
      "is_correct": true
    },
    {
      "text": "他正在庞大地工作着。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误：形容词“庞大”不能直接带补语“很困难”，且“被”字句使用不当，应改为“这个工程非常庞大，做起来很困难”。 搭配/语义错误：“庞大”是状态形容词，通常不修饰动态动词“工作”，也不能用“地”连接作状语表示工作方式。 词性错误：“庞大”是形容词，不能带宾语“这个计划”作谓语动词使用，应改为“我们扩大了这个计划的规模”或“这个计划很庞大”。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "這個工程被龐大得很困難。",
        "is_correct": false
      },
      {
        "text": "我們龐大了這個計劃。",
        "is_correct": false
      },
      {
        "text": "這是一個龐大的工程，需要很多人。",
        "is_correct": true
      },
      {
        "text": "他正在龐大地工作著。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤：形容詞“龐大”不能直接帶補語“很困難”，且“被”字句使用不當，應改為“這個工程非常龐大，做起來很困難”。 搭配/語義錯誤：“龐大”是狀態形容詞，通常不修飾動態動詞“工作”，也不能用“地”連線作狀語表示工作方式。 詞性錯誤：“龐大”是形容詞，不能帶賓語“這個計劃”作謂語動詞使用，應改為“我們擴大了這個計劃的規模”或“這個計劃很龐大”。",
    "target_word": "龐大"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "庞大",
  "relation": "antonym",
  "options": [
    "微小",
    "繁杂",
    "巨大",
    "宏伟"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "形容体积、规模或数量极小，与“庞大”构成反义关系"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "微小",
      "繁雜",
      "巨大",
      "宏偉"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "形容體積、規模或數量極小，與“龐大”構成反義關係"
      }
    }
  }
}
```

---

## sense 10119, level 3

#### Pack A
### Level 3 (sense 10119, difficulty None)
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "技术进步是好事，但如果管理不好，也可能带来新的___问题。",
  "original_sentence": "技术进步是好事，但如果管理不好，也可能带来新的社会问题。",
  "correct_answer": "社会",
  "options": [
    "人群",
    "社区",
    "社会",
    "集体"
  ],
  "explanation": "正确。'社会问题'是固定搭配，指涉及公众利益、结构或制度的问题。",
  "distractor_tags": {},
  "word_definition": "指由共同利益、文化或制度联系起来的人群整体。",
  "target_word": "社会",
  "hant": {
    "sentence_with_blank": "技術進步是好事，但如果管理不好，也可能帶來新的___問題。",
    "original_sentence": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
    "correct_answer": "社會",
    "options": [
      "人群",
      "社群",
      "社會",
      "集體"
    ],
    "explanation": "正確。'社會問題'是固定搭配，指涉及公眾利益、結構或制度的問題。",
    "distractor_tags": {},
    "word_definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
    "target_word": "社會"
  }
}
```

#### Pack B
### Level 3 (sense 10119, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "技术进步是好事，但如果管理不好，也可能带来新的___问题。",
  "original_sentence": "技术进步是好事，但如果管理不好，也可能带来新的社会问题。",
  "correct_answer": "社会",
  "options": [
    "规模",
    "家庭",
    "社会",
    "朝廷"
  ],
  "explanation": "正确选项，指人群整体，符合技术进步影响宏观层面的语境。",
  "distractor_tags": {},
  "word_definition": "指由共同利益、文化或制度联系起来的人群整体。",
  "target_word": "社会",
  "hant": {
    "sentence_with_blank": "技術進步是好事，但如果管理不好，也可能帶來新的___問題。",
    "original_sentence": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
    "correct_answer": "社會",
    "options": [
      "規模",
      "家庭",
      "社會",
      "朝廷"
    ],
    "explanation": "正確選項，指人群整體，符合技術進步影響宏觀層面的語境。",
    "distractor_tags": {},
    "word_definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
    "target_word": "社會"
  }
}
```

---

## sense 10119, level 6

#### Pack A
### Level 6 (sense 10119, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种对水资源的社会调控机制，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文，需要全社会成员的共同维护，而不是仅靠一条社会。",
      "is_correct": false
    },
    {
      "text": "这种对水资源调控机制的社会，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的社会调控机制了，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的社会调控机制，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误。“社会”作为抽象集合名词，不能使用个体量词“条”，应使用“个”或直接使用“全社会”。 体标位置错误。动态助词“了”不能直接附着在名词性短语“社会调控机制”之后，应放在谓语动词之后或句末。 语序错误。“社会”与“调控机制”位置颠倒，导致“社会”成为“治理模式”的中心语，语义不通；应为“社会调控机制”。",
  "target_word": "社会",
  "hant": {
    "sentences": [
      {
        "text": "這種對水資源的社會調控機制，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文，需要全社會成員的共同維護，而不是僅靠一條社會。",
        "is_correct": false
      },
      {
        "text": "這種對水資源調控機制的社會，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的社會調控機制了，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的社會調控機制，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤。“社會”作為抽象集合名詞，不能使用個體量詞“條”，應使用“個”或直接使用“全社會”。 體標位置錯誤。動態助詞“了”不能直接附著在名詞性短語“社會調控機制”之後，應放在謂語動詞之後或句末。 語序錯誤。“社會”與“調控機制”位置顛倒，導致“社會”成為“治理模式”的中心語，語義不通；應為“社會調控機制”。",
    "target_word": "社會"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "集体",
    "个人",
    "国家",
    "群体"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：社会指由共同利益联系的人群整体，个人指单独的个体，构成集体与个体的对立关系"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "集體",
      "個人",
      "國家",
      "群體"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：社會指由共同利益聯絡的人群整體，個人指單獨的個體，構成集體與個體的對立關係"
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
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与社会需求共振的产物。",
      "is_correct": true
    },
    {
      "text": "他研究了社会了三年，终于写出了这本著作。",
      "is_correct": false
    },
    {
      "text": "为了解决这件社会的问题，政府出台了新规定。",
      "is_correct": false
    },
    {
      "text": "社会未来，将会面临更多未知的挑战。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。“社会”是抽象名词，不能用指代具体事物的量词“件”，应改为“个”或直接省略。 语序错误。时间名词“未来”作定语时应加“的”，或作状语时应放在主语后，不能直接构成“社会未来”。 体标位置错误。动态助词“了”表示动作完成，应放在动词“研究”之后，不能放在宾语“社会”之后。",
  "target_word": "社会",
  "hant": {
    "sentences": [
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與社會需求共振的產物。",
        "is_correct": true
      },
      {
        "text": "他研究了社會了三年，終於寫出了這本著作。",
        "is_correct": false
      },
      {
        "text": "為了解決這件社會的問題，政府出臺了新規定。",
        "is_correct": false
      },
      {
        "text": "社會未來，將會面臨更多未知的挑戰。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。“社會”是抽象名詞，不能用指代具體事物的量詞“件”，應改為“個”或直接省略。 語序錯誤。時間名詞“未來”作定語時應加“的”，或作狀語時應放在主語後，不能直接構成“社會未來”。 體標位置錯誤。動態助詞“了”表示動作完成，應放在動詞“研究”之後，不能放在賓語“社會”之後。",
    "target_word": "社會"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "个人",
    "群体",
    "国家",
    "集体"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义项：社会指人群整体，个人指单独的个体，二者构成集体与个体的对立"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "個人",
      "群體",
      "國家",
      "集體"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義項：社會指人群整體，個人指單獨的個體，二者構成集體與個體的對立"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10119, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "这种对水资源的调控社会机制，本质上是一种非市场化的治理模式。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的社会了调控机制，本质上是一种非市场化的治理模式。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的社会调控机制，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文。",
      "is_correct": true
    },
    {
      "text": "这种对水资源的一个社会治理机制，本质上是一种非市场化的治理模式。",
      "is_correct": false
    }
  ],
  "explanation": "量词错误：'社会'是抽象名词，表示一种宏观结构或状态，不能用个体量词'一个'来修饰具体的'机制'，应直接说'社会治理机制'或'一种社会治理机制'。 体标位置错误：动态助词'了'不能插入在定语'社会'和中心语'调控'之间，破坏了名词性短语的结构完整性。 语序错误：多层定语中，表示性质的'社会'应紧贴中心语'机制'或作为整体概念'社会治理'的一部分，'调控社会机制'易被误解为'调控'是动词，导致句法结构混乱。",
  "target_word": "社会",
  "hant": {
    "sentences": [
      {
        "text": "這種對水資源的調控社會機制，本質上是一種非市場化的治理模式。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的社會了調控機制，本質上是一種非市場化的治理模式。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的社會調控機制，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文。",
        "is_correct": true
      },
      {
        "text": "這種對水資源的一個社會治理機制，本質上是一種非市場化的治理模式。",
        "is_correct": false
      }
    ],
    "explanation": "量詞錯誤：'社會'是抽象名詞，表示一種宏觀結構或狀態，不能用個體量詞'一個'來修飾具體的'機制'，應直接說'社會治理機制'或'一種社會治理機制'。 體標位置錯誤：動態助詞'了'不能插入在定語'社會'和中心語'調控'之間，破壞了名詞性短語的結構完整性。 語序錯誤：多層定語中，表示性質的'社會'應緊貼中心語'機制'或作為整體概念'社會治理'的一部分，'調控社會機制'易被誤解為'調控'是動詞，導致句法結構混亂。",
    "target_word": "社會"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "公众",
    "社区",
    "群体",
    "个人"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：指单个的个体，与指人群整体的“社会”构成个体与集体的对立关系。"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "公眾",
      "社群",
      "群體",
      "個人"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：指單個的個體，與指人群整體的“社會”構成個體與集體的對立關係。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "公众",
    "群体",
    "社区",
    "个人"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：指单个的人，与指人群整体的‘社会’构成个体与集体的对立关系。"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "公眾",
      "群體",
      "社群",
      "個人"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：指單個的人，與指人群整體的‘社會’構成個體與集體的對立關係。"
      }
    }
  }
}
```

---

## sense 10125, level 6

#### Pack A
### Level 6 (sense 10125, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "真正他关心我，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心着了，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心起我去，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心我，是我值得信赖的知己。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误：“真正”作为副词，通常放在主语之后、谓语动词之前。放在主语“他”之前修饰整个句子不符合汉语语法习惯。 体标选用错误：“关心”是心理动词，通常不与表示完成的“了”和表示持续的“着”直接连用，此处体标叠加使用导致语法错误。 补语误用：“起……去”不是合法的趋向补语结构。表示动作开始并继续应使用“起……来”，此处误用了“去”。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "真正他關心我，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心著了，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心起我去，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心我，是我值得信賴的知己。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤：“真正”作為副詞，通常放在主語之後、謂語動詞之前。放在主語“他”之前修飾整個句子不符合漢語語法習慣。 體標選用錯誤：“關心”是心理動詞，通常不與表示完成的“了”和表示持續的“著”直接連用，此處體標疊加使用導致語法錯誤。 補語誤用：“起……去”不是合法的趨向補語結構。表示動作開始並繼續應使用“起……來”，此處誤用了“去”。",
    "target_word": "真正"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "只有长期相处，两人才能真正建立感情。",
      "is_correct": true
    },
    {
      "text": "只有长期相处，两人建立感情真正。",
      "is_correct": false
    },
    {
      "text": "只有长期相处，两人真正了建立感情。",
      "is_correct": false
    },
    {
      "text": "只有长期相处，两人真正能建立感情。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：能愿动词'能'应放在副词'真正'之前，正确语序为'能真正建立'。 体标位置错误：动态助词'了'表示完成，不能放在副词'真正'和动词'建立'之间，应放在句末或动词后。 语序错误：副词'真正'必须放在它所修饰的动词'建立'之前，不能放在句末。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "只有長期相處，兩人才能真正建立感情。",
        "is_correct": true
      },
      {
        "text": "只有長期相處，兩人建立感情真正。",
        "is_correct": false
      },
      {
        "text": "只有長期相處，兩人真正了建立感情。",
        "is_correct": false
      },
      {
        "text": "只有長期相處，兩人真正能建立感情。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：能願動詞'能'應放在副詞'真正'之前，正確語序為'能真正建立'。 體標位置錯誤：動態助詞'了'表示完成，不能放在副詞'真正'和動詞'建立'之間，應放在句末或動詞後。 語序錯誤：副詞'真正'必須放在它所修飾的動詞'建立'之前，不能放在句末。",
    "target_word": "真正"
  }
}
```

#### Pack B
### Level 6 (sense 10125, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "真正他喜欢的是画画。",
      "is_correct": false
    },
    {
      "text": "他真正喜欢得是画画，不是打游戏。",
      "is_correct": false
    },
    {
      "text": "他正在真正喜欢画画。",
      "is_correct": false
    },
    {
      "text": "他真正喜欢的是画画，不是打游戏。",
      "is_correct": true
    }
  ],
  "explanation": "语序/结构错误：'是……的'结构中，'的'应紧跟在动词或形容词后，或者放在句末强调。此处'得'字误用，且语序混乱，应为'他真正喜欢的是画画'。 体貌错误：'喜欢'是心理状态动词，通常不与进行体标记'正在'连用。'真正'修饰状态，但不能改变动词本身的体貌限制。 语序错误：副词'真正'通常修饰谓语动词或形容词，不应置于主语'他'之前。正确语序应为'他真正喜欢的是画画'。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "真正他喜歡的是畫畫。",
        "is_correct": false
      },
      {
        "text": "他真正喜歡得是畫畫，不是打遊戲。",
        "is_correct": false
      },
      {
        "text": "他正在真正喜歡畫畫。",
        "is_correct": false
      },
      {
        "text": "他真正喜歡的是畫畫，不是打遊戲。",
        "is_correct": true
      }
    ],
    "explanation": "語序/結構錯誤：'是……的'結構中，'的'應緊跟在動詞或形容詞後，或者放在句末強調。此處'得'字誤用，且語序混亂，應為'他真正喜歡的是畫畫'。 體貌錯誤：'喜歡'是心理狀態動詞，通常不與進行體標記'正在'連用。'真正'修飾狀態，但不能改變動詞本身的體貌限制。 語序錯誤：副詞'真正'通常修飾謂語動詞或形容詞，不應置於主語'他'之前。正確語序應為'他真正喜歡的是畫畫'。",
    "target_word": "真正"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "真正",
  "relation": "antonym",
  "options": [
    "大概",
    "确实",
    "实在",
    "虚假"
  ],
  "correct_answer": "虚假",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（强调事实）",
      "explanation": "反义关系：'真正'强调事实的真实性，'虚假'指不真实、伪造，二者在'是否属实'这一语义维度上构成直接对立。"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "大概",
      "確實",
      "實在",
      "虛假"
    ],
    "correct_answer": "虛假",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（強調事實）",
        "explanation": "反義關係：'真正'強調事實的真實性，'虛假'指不真實、偽造，二者在'是否屬實'這一語義維度上構成直接對立。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "真正",
  "relation": "antonym",
  "options": [
    "确实",
    "虚假",
    "大概",
    "实在"
  ],
  "correct_answer": "虚假",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（强调事实）",
      "explanation": "反义：'真正'强调事实的真实性，'虚假'指不真实、伪造，二者在真实性维度上构成反义关系。"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "確實",
      "虛假",
      "大概",
      "實在"
    ],
    "correct_answer": "虛假",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（強調事實）",
        "explanation": "反義：'真正'強調事實的真實性，'虛假'指不真實、偽造，二者在真實性維度上構成反義關係。"
      }
    }
  }
}
```

---

## sense 10131, level 6

#### Pack A
### Level 6 (sense 10131, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那个地区很多游客吸引了。",
      "is_correct": false
    },
    {
      "text": "那个地区吸引了很多游客。",
      "is_correct": true
    },
    {
      "text": "那个地区吸引了着很多游客。",
      "is_correct": false
    },
    {
      "text": "一条地区吸引了很多游客。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'地区'是表示范围的名词，应使用'个'或'片'等量词，不能使用用于长条状物体的'条'。 体标选用错误：动态助词'了'表示动作完成，'着'表示状态持续，两者不能同时用在动词'吸引'后面。 语序错误：宾语'很多游客'被错误地放在了动词'吸引'之前，破坏了汉语正常的'主-谓-宾'语序。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "那個地區很多遊客吸引了。",
        "is_correct": false
      },
      {
        "text": "那個地區吸引了很多遊客。",
        "is_correct": true
      },
      {
        "text": "那個地區吸引了著很多遊客。",
        "is_correct": false
      },
      {
        "text": "一條地區吸引了很多遊客。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'地區'是表示範圍的名詞，應使用'個'或'片'等量詞，不能使用用於長條狀物體的'條'。 體標選用錯誤：動態助詞'了'表示動作完成，'著'表示狀態持續，兩者不能同時用在動詞'吸引'後面。 語序錯誤：賓語'很多遊客'被錯誤地放在了動詞'吸引'之前，破壞了漢語正常的'主-謂-賓'語序。",
    "target_word": "地區"
  }
}
```

#### Pack B
### Level 6 (sense 10131, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们计划去个地区旅行。",
      "is_correct": false
    },
    {
      "text": "我们计划去那个地区了旅行。",
      "is_correct": false
    },
    {
      "text": "我们计划去那个地区旅行。",
      "is_correct": true
    },
    {
      "text": "地区那个我们去计划旅行。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词'了'不应插入在动词'去'和宾语'那个地区'之间，也不应放在连动结构的中间破坏语流，应改为'去那个地区旅行'或'去了那个地区旅行'（视具体时态而定，但原句结构不通）。 量词使用错误：'地区'作为可数名词，前面需要特定的数量词或指示代词修饰，单独使用泛指量词'个'显得非常不自然且缺乏指代性，通常说'某个地区'或'一个地区'，但在'去...旅行'的具体计划中，通常需要更明确的指代如'那个'。 语序错误：汉语基本语序为主谓宾。此句将宾语'地区'前置且结构混乱，破坏了'我们计划去那个地区旅行'的正常逻辑顺序。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "我們計劃去個地區旅行。",
        "is_correct": false
      },
      {
        "text": "我們計劃去那個地區了旅行。",
        "is_correct": false
      },
      {
        "text": "我們計劃去那個地區旅行。",
        "is_correct": true
      },
      {
        "text": "地區那個我們去計劃旅行。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'不應插入在動詞'去'和賓語'那個地區'之間，也不應放在連動結構的中間破壞語流，應改為'去那個地區旅行'或'去了那個地區旅行'（視具體時態而定，但原句結構不通）。 量詞使用錯誤：'地區'作為可數名詞，前面需要特定的數量詞或指示代詞修飾，單獨使用泛指量詞'個'顯得非常不自然且缺乏指代性，通常說'某個地區'或'一個地區'，但在'去...旅行'的具體計劃中，通常需要更明確的指代如'那個'。 語序錯誤：漢語基本語序為主謂賓。此句將賓語'地區'前置且結構混亂，破壞了'我們計劃去那個地區旅行'的正常邏輯順序。",
    "target_word": "地區"
  }
}
```

---

## sense 10131, level 7

#### Pack A
### Level 7 (sense 10131, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个地区很美丽风景。",
      "is_correct": false,
      "error_description": "语序错误。形容词“美丽”应该修饰名词“风景”，构成偏正短语“美丽的风景”或“风景非常美丽”，而不是放在句尾直接修饰主语。"
    },
    {
      "text": "这个地区的风景非常美丽。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    },
    {
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個地區很美麗風景。",
        "is_correct": false,
        "error_description": "語序錯誤。形容詞“美麗”應該修飾名詞“風景”，構成偏正短語“美麗的風景”或“風景非常美麗”，而不是放在句尾直接修飾主語。"
      },
      {
        "text": "這個地區的風景非常美麗。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
        "is_correct": true
      },
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10131, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他住了三年在这个地区。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，表示地点的介词短语（如‘在这个地区’）应放在动词前作状语，不能放在动词之后。正确语序为‘主语+地点状语+动词+时量补语’。"
    },
    {
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    },
    {
      "text": "这个地区的气候非常温暖。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他住了三年在這個地區。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，表示地點的介詞短語（如‘在這個地區’）應放在動詞前作狀語，不能放在動詞之後。正確語序為‘主語+地點狀語+動詞+時量補語’。"
      },
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      },
      {
        "text": "這個地區的氣候非常溫暖。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
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
      "text": "那个地区吸引了很多游客。",
      "is_correct": true
    },
    {
      "text": "那个地区正下着大雨。",
      "is_correct": true
    },
    {
      "text": "他住了三年在这个地区。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，表示地点的介词短语（如‘在这个地区’）应放在动词（如‘住’）之前作状语，不能放在句末。"
    },
    {
      "text": "这个地区的发展一直很好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "那個地區吸引了很多遊客。",
        "is_correct": true
      },
      {
        "text": "那個地區正下著大雨。",
        "is_correct": true
      },
      {
        "text": "他住了三年在這個地區。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，表示地點的介詞短語（如‘在這個地區’）應放在動詞（如‘住’）之前作狀語，不能放在句末。"
      },
      {
        "text": "這個地區的發展一直很好。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10137, level 6

#### Pack A
### Level 6 (sense 10137, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们把花瓣压印起在画布上呢。",
      "is_correct": false
    },
    {
      "text": "我们正把花瓣压印了画布上呢。",
      "is_correct": false
    },
    {
      "text": "我们正把花瓣压印在画布上呢。",
      "is_correct": true
    },
    {
      "text": "我们正压印把花瓣在画布上呢。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误。进行体标记“正……呢”与完成体标记“了”冲突，且“了”后直接接处所名词不符合语法，应为“压印在”。 语序错误。“把”字及其宾语“花瓣”被错误放置于动词之后，破坏了“把+宾语+动词+补语”的正确句法结构。 方向/结果补语误用。结果补语“起”表示动作开始或物体向上，与处所补语“在画布上”表示的附着状态语义冲突，应直接使用“压印在”。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "我們把花瓣壓印起在畫布上呢。",
        "is_correct": false
      },
      {
        "text": "我們正把花瓣壓印了畫布上呢。",
        "is_correct": false
      },
      {
        "text": "我們正把花瓣壓印在畫布上呢。",
        "is_correct": true
      },
      {
        "text": "我們正壓印把花瓣在畫布上呢。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤。進行體標記“正……呢”與完成體標記“了”衝突，且“了”後直接接處所名詞不符合語法，應為“壓印在”。 語序錯誤。“把”字及其賓語“花瓣”被錯誤放置於動詞之後，破壞了“把+賓語+動詞+補語”的正確句法結構。 方向/結果補語誤用。結果補語“起”表示動作開始或物體向上，與處所補語“在畫布上”表示的附著狀態語義衝突，應直接使用“壓印在”。",
    "target_word": "壓印"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在手工纸上干花压印真美。",
      "is_correct": false
    },
    {
      "text": "干花压印在手工纸上真美。",
      "is_correct": true
    },
    {
      "text": "干花压印起在手工纸上真美。",
      "is_correct": false
    },
    {
      "text": "干花压印过在手工纸上真美。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用与语序错误。“过”表示过去的经历，与当前欣赏的语境不符，且“过”应放在“在手工纸上”之后。 语序错误。处所状语“在手工纸上”放在句首时，主语“干花”应紧跟其后，原句破坏了正常的语序结构。 方向/结果补语误用。“起”表示向上或开始，而此处表示施加压力使痕迹附着于纸面，应使用表示附着的补语，且“起在”搭配不当。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "在手工紙上乾花壓印真美。",
        "is_correct": false
      },
      {
        "text": "乾花壓印在手工紙上真美。",
        "is_correct": true
      },
      {
        "text": "乾花壓印起在手工紙上真美。",
        "is_correct": false
      },
      {
        "text": "乾花壓印過在手工紙上真美。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用與語序錯誤。“過”表示過去的經歷，與當前欣賞的語境不符，且“過”應放在“在手工紙上”之後。 語序錯誤。處所狀語“在手工紙上”放在句首時，主語“乾花”應緊跟其後，原句破壞了正常的語序結構。 方向/結果補語誤用。“起”表示向上或開始，而此處表示施加壓力使痕跡附著於紙面，應使用表示附著的補語，且“起在”搭配不當。",
    "target_word": "壓印"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "压制",
    "抹平",
    "雕刻",
    "拓印"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义：压印是施压留下痕迹，抹平是消除痕迹使表面恢复平坦"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "壓制",
      "抹平",
      "雕刻",
      "拓印"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義：壓印是施壓留下痕跡，抹平是消除痕跡使表面恢復平坦"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10137, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "覆盖",
    "描绘",
    "雕刻",
    "擦除"
  ],
  "correct_answer": "擦除",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "用力在物体表面留下痕迹或图案",
      "explanation": "反义：压印是留下痕迹，擦除是去除痕迹，二者动作结果相反。"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "覆蓋",
      "描繪",
      "雕刻",
      "擦除"
    ],
    "correct_answer": "擦除",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "用力在物體表面留下痕跡或圖案",
        "explanation": "反義：壓印是留下痕跡，擦除是去除痕跡，二者動作結果相反。"
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
      "text": "我们要学习图片如何正确压印。",
      "is_correct": false
    },
    {
      "text": "我们要学习如何压印起来图片。",
      "is_correct": false
    },
    {
      "text": "我们要学习如何正确压印了图片。",
      "is_correct": false
    },
    {
      "text": "我们要学习如何正确压印图片。",
      "is_correct": true
    }
  ],
  "explanation": "体标错误：'要学习如何'表示将来或一般性的技能习得，不应与表示完成体的'了'连用，应去掉'了'。 补语误用：'压印'是及物动词，直接带宾语'图片'。'起来'作为趋向补语在此处语义不通，且破坏了动宾结构的紧密性。 语序错误：虽然口语中偶有主题化结构，但在'学习如何...'的句式中，'如何'应紧接动词短语，'图片'作为宾语应置于'压印'之后，即'如何正确压印图片'。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "我們要學習圖片如何正確壓印。",
        "is_correct": false
      },
      {
        "text": "我們要學習如何壓印起來圖片。",
        "is_correct": false
      },
      {
        "text": "我們要學習如何正確壓印了圖片。",
        "is_correct": false
      },
      {
        "text": "我們要學習如何正確壓印圖片。",
        "is_correct": true
      }
    ],
    "explanation": "體標錯誤：'要學習如何'表示將來或一般性的技能習得，不應與表示完成體的'了'連用，應去掉'了'。 補語誤用：'壓印'是及物動詞，直接帶賓語'圖片'。'起來'作為趨向補語在此處語義不通，且破壞了動賓結構的緊密性。 語序錯誤：雖然口語中偶有主題化結構，但在'學習如何...'的句式中，'如何'應緊接動詞短語，'圖片'作為賓語應置於'壓印'之後，即'如何正確壓印圖片'。",
    "target_word": "壓印"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "描绘",
    "雕刻",
    "擦除",
    "印刷"
  ],
  "correct_answer": "擦除",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "用力在物体表面留下痕迹或图案",
      "explanation": "反义：压印是留下痕迹，擦除是去除痕迹"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "描繪",
      "雕刻",
      "擦除",
      "印刷"
    ],
    "correct_answer": "擦除",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "用力在物體表面留下痕跡或圖案",
        "explanation": "反義：壓印是留下痕跡，擦除是去除痕跡"
      }
    }
  }
}
```

---

## sense 10137, level 7

#### Pack A
### Level 7 (sense 10137, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我把树叶压印在纸上，送给好朋友。",
      "is_correct": true
    },
    {
      "text": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面压印出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
      "is_correct": true
    },
    {
      "text": "她在书签上压印过很多漂亮的图案。",
      "is_correct": true
    },
    {
      "text": "我把树叶压印了纸上，送给好朋友。",
      "is_correct": false,
      "error_description": "在“把”字句中，动词后接处所补语时，必须使用介词“在”引出地点，不能省略“在”。正确写法是“压印在纸上”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我把樹葉壓印在紙上，送給好朋友。",
        "is_correct": true
      },
      {
        "text": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面壓印出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
        "is_correct": true
      },
      {
        "text": "她在書籤上壓印過很多漂亮的圖案。",
        "is_correct": true
      },
      {
        "text": "我把樹葉壓印了紙上，送給好朋友。",
        "is_correct": false,
        "error_description": "在“把”字句中，動詞後接處所補語時，必須使用介詞“在”引出地點，不能省略“在”。正確寫法是“壓印在紙上”。"
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
      "text": "他压印名字在信封上了。",
      "is_correct": false,
      "error_description": "语序错误。动词后接“在+处所”作补语时，宾语需借助“把”字提前，或将处所状语置于动词前，不能直接采用“动词+宾语+在+处所”的结构。"
    },
    {
      "text": "你压印的图案真好看，我很喜欢。",
      "is_correct": true
    },
    {
      "text": "干花压印在手工纸上真美。",
      "is_correct": true
    },
    {
      "text": "他把名字压印在信封上了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他壓印名字在信封上了。",
        "is_correct": false,
        "error_description": "語序錯誤。動詞後接“在+處所”作補語時，賓語需藉助“把”字提前，或將處所狀語置於動詞前，不能直接採用“動詞+賓語+在+處所”的結構。"
      },
      {
        "text": "你壓印的圖案真好看，我很喜歡。",
        "is_correct": true
      },
      {
        "text": "乾花壓印在手工紙上真美。",
        "is_correct": true
      },
      {
        "text": "他把名字壓印在信封上了。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10137, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这张卡片上压印着金色的字母。",
      "is_correct": true
    },
    {
      "text": "工人正在把花纹压印在皮革上。",
      "is_correct": true
    },
    {
      "text": "工人正在把花纹压印在皮革上了。",
      "is_correct": false,
      "error_description": "错误类型：体标误用。句中已有“正在”表示动作正在进行，不应再使用表示完成或变化的“了”，应去掉“了”。"
    },
    {
      "text": "他所改良的金属活字印刷系统，结合了螺旋压印机、油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這張卡片上壓印著金色的字母。",
        "is_correct": true
      },
      {
        "text": "工人正在把花紋壓印在皮革上。",
        "is_correct": true
      },
      {
        "text": "工人正在把花紋壓印在皮革上了。",
        "is_correct": false,
        "error_description": "錯誤型別：體標誤用。句中已有“正在”表示動作正在進行，不應再使用表示完成或變化的“了”，應去掉“了”。"
      },
      {
        "text": "他所改良的金屬活字印刷系統，結合了螺旋壓印機、油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10156, level 3

#### Pack A
### Level 3 (sense 10156, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临___的挑战。",
  "original_sentence": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临前所未有的挑战。",
  "correct_answer": "前所未有",
  "options": [
    "空前绝后",
    "闻所未闻",
    "绝无仅有",
    "前所未有"
  ],
  "explanation": "正确。“前所未有”指过去从来没有发生过，修饰“挑战”表示挑战的程度和性质是过去没有的，完全符合语境。",
  "distractor_tags": {},
  "word_definition": "指过去从来没有发生过或出现过的。",
  "target_word": "前所未有",
  "hant": {
    "sentence_with_blank": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨___的挑戰。",
    "original_sentence": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨前所未有的挑戰。",
    "correct_answer": "前所未有",
    "options": [
      "空前絕後",
      "聞所未聞",
      "絕無僅有",
      "前所未有"
    ],
    "explanation": "正確。“前所未有”指過去從來沒有發生過，修飾“挑戰”表示挑戰的程度和性質是過去沒有的，完全符合語境。",
    "distractor_tags": {},
    "word_definition": "指過去從來沒有發生過或出現過的。",
    "target_word": "前所未有"
  }
}
```

#### Pack B
### Level 3 (sense 10156, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临___的挑战。",
  "original_sentence": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临前所未有的挑战。",
  "correct_answer": "前所未有",
  "options": [
    "琳琅满目",
    "前所未有",
    "微不足道",
    "井井有条"
  ],
  "explanation": "正确。'前所未有'形容挑战的严重程度是以前从未出现过的，符合语境中全球变暖加剧的背景。",
  "distractor_tags": {},
  "word_definition": "以前从来没有过的",
  "target_word": "前所未有",
  "hant": {
    "sentence_with_blank": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨___的挑戰。",
    "original_sentence": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨前所未有的挑戰。",
    "correct_answer": "前所未有",
    "options": [
      "琳琅滿目",
      "前所未有",
      "微不足道",
      "井井有條"
    ],
    "explanation": "正確。'前所未有'形容挑戰的嚴重程度是以前從未出現過的，符合語境中全球變暖加劇的背景。",
    "distractor_tags": {},
    "word_definition": "以前從來沒有過的",
    "target_word": "前所未有"
  }
}
```

---

## sense 10156, level 7

#### Pack A
### Level 7 (sense 10156, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临前所未有的挑战。",
      "is_correct": true
    },
    {
      "text": "这一突破不仅大幅降低了书籍的制作成本，更使《圣经》等文本得以以前所未有的速度和数量被复制，从而打破了教会对知识解释权的垄断。",
      "is_correct": true
    },
    {
      "text": "随着出版物种类的丰富，除宗教文献外，科学论著、文学作品、法律文本乃至新闻小册子广泛流通，公众对知识的渴求被前所未有地激发。",
      "is_correct": true
    },
    {
      "text": "我们遇到了前所未有困难。",
      "is_correct": false,
      "error_description": "错误类型：结构助词缺失。在定语“前所未有”和中心语“困难”之间，通常需要加结构助词“的”来连接，使修饰关系更清晰自然。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨前所未有的挑戰。",
        "is_correct": true
      },
      {
        "text": "這一突破不僅大幅降低了書籍的製作成本，更使《聖經》等文本得以以前所未有的速度和數量被複制，從而打破了教會對知識解釋權的壟斷。",
        "is_correct": true
      },
      {
        "text": "隨著出版物種類的豐富，除宗教文獻外，科學論著、文學作品、法律文本乃至新聞小冊子廣泛流通，公眾對知識的渴求被前所未有地激發。",
        "is_correct": true
      },
      {
        "text": "我們遇到了前所未有困難。",
        "is_correct": false,
        "error_description": "錯誤型別：結構助詞缺失。在定語“前所未有”和中心語“困難”之間，通常需要加結構助詞“的”來連線，使修飾關係更清晰自然。"
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
      "text": "这种热闹场面真是前所未有。",
      "is_correct": true
    },
    {
      "text": "大家的热情达到了前所未有的高度。",
      "is_correct": true
    },
    {
      "text": "这种热闹场面真是前所未有地。",
      "is_correct": false,
      "error_description": "错误类型：成分赘余/词性误用。'前所未有'在此处作谓语，形容'场面'，后面不需要加结构助词'地'。'地'通常用于连接状语和中心语（动词或形容词），而此处句子已结束。"
    },
    {
      "text": "他的进步速度是前所未有的。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種熱鬧場面真是前所未有。",
        "is_correct": true
      },
      {
        "text": "大家的熱情達到了前所未有的高度。",
        "is_correct": true
      },
      {
        "text": "這種熱鬧場面真是前所未有地。",
        "is_correct": false,
        "error_description": "錯誤型別：成分贅餘/詞性誤用。'前所未有'在此處作謂語，形容'場面'，後面不需要加結構助詞'地'。'地'通常用於連線狀語和中心語（動詞或形容詞），而此處句子已結束。"
      },
      {
        "text": "他的進步速度是前所未有的。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10156, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这次活动的规模是前所未有的。",
      "is_correct": true
    },
    {
      "text": "收到礼物时，我的开心是前所未有了。",
      "is_correct": false,
      "error_description": "体标选用错误。在‘是……的’结构中，句末应使用结构助词‘的’来强调状态，不能误用动态助词‘了’。"
    },
    {
      "text": "收到礼物时，我的开心是前所未有的。",
      "is_correct": true
    },
    {
      "text": "看到惊喜，我的感动是前所未有的。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這次活動的規模是前所未有的。",
        "is_correct": true
      },
      {
        "text": "收到禮物時，我的開心是前所未有了。",
        "is_correct": false,
        "error_description": "體標選用錯誤。在‘是……的’結構中，句末應使用結構助詞‘的’來強調狀態，不能誤用動態助詞‘了’。"
      },
      {
        "text": "收到禮物時，我的開心是前所未有的。",
        "is_correct": true
      },
      {
        "text": "看到驚喜，我的感動是前所未有的。",
        "is_correct": true
      }
    ]
  }
}
```

---
