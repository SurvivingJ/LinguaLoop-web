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


## sense 10119, level 6

#### Pack A
### Level 6 (sense 10119, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "集体",
    "国家",
    "群体",
    "自然"
  ],
  "correct_answer": "自然",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：社会指人类基于共同利益与文化制度形成的群体整体，自然指独立于人类组织之外的物质世界，二者构成人文与天然的经典对立。"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "集體",
      "國家",
      "群體",
      "自然"
    ],
    "correct_answer": "自然",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：社會指人類基於共同利益與文化制度形成的群體整體，自然指獨立於人類組織之外的物質世界，二者構成人文與天然的經典對立。"
      }
    }
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
    "国家",
    "集体",
    "群体"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：社会指人群整体，个人指单个的人，二者构成集体与个体的对立"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "個人",
      "國家",
      "集體",
      "群體"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：社會指人群整體，個人指單個的人，二者構成集體與個體的對立"
      }
    }
  }
}
```

#### Pack B
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

---

## sense 10119, level 7

#### Pack A
### Level 7 (sense 10119, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们要努力构建一条公平、正义的社会。",
      "is_correct": false,
      "error_description": "“社会”是抽象名词，不能使用用于长条形事物的量词“条”，应使用“个”。"
    },
    {
      "text": "这表明，基层环保实践正逐步演进为公民参与社会治理的有效路径。",
      "is_correct": true
    },
    {
      "text": "这些水利系统背后所蕴藏的，是一整套关于水权、劳动组织与社会协作的文化制度。",
      "is_correct": true
    },
    {
      "text": "这种基于绩效的认可机制，与现实社会的成就导向形成镜像。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們要努力構建一條公平、正義的社會。",
        "is_correct": false,
        "error_description": "“社會”是抽象名詞，不能使用用於長條形事物的量詞“條”，應使用“個”。"
      },
      {
        "text": "這表明，基層環保實踐正逐步演進為公民參與社會治理的有效路徑。",
        "is_correct": true
      },
      {
        "text": "這些水利系統背後所蘊藏的，是一整套關於水權、勞動組織與社會協作的文化制度。",
        "is_correct": true
      },
      {
        "text": "這種基於績效的認可機制，與現實社會的成就導向形成映象。",
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
      "text": "未来可能会有更严格的法律出台，推动社会向更可持续的方向发展。",
      "is_correct": true
    },
    {
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与社会需求共振的产物。",
      "is_correct": true
    },
    {
      "text": "社会向更可持续的方向在法律出台后发展。",
      "is_correct": false,
      "error_description": "语序错误。表示时间或条件的状语（如“在法律出台后”）通常应放在句首或主语之后、谓语动词之前，不能放在介词短语和动词之间。"
    },
    {
      "text": "技术进步是好事，但如果管理不好，也可能带来新的社会问题。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "未來可能會有更嚴格的法律出臺，推動社會向更可持續的方向發展。",
        "is_correct": true
      },
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與社會需求共振的產物。",
        "is_correct": true
      },
      {
        "text": "社會向更可持續的方向在法律出臺後發展。",
        "is_correct": false,
        "error_description": "語序錯誤。表示時間或條件的狀語（如“在法律出臺後”）通常應放在句首或主語之後、謂語動詞之前，不能放在介詞短語和動詞之間。"
      },
      {
        "text": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10119, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这些水利系统背后所蕴藏的，是一整套关于水权、劳动组织与社会协作的文化制度。",
      "is_correct": true
    },
    {
      "text": "这表明，基层环保实践正逐步演进为公民参与社会治理的有效路径。",
      "is_correct": true
    },
    {
      "text": "这种基于绩效的认可机制，与现实社会的成就导向形成镜像。",
      "is_correct": true
    },
    {
      "text": "社会正在发生了巨大的变化，我们需要适应这种变化。",
      "is_correct": false,
      "error_description": "“正在”表示动作正在进行，不能与表示完成的动态助词“了”连用。应删去“了”或改为“已经”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這些水利系統背後所蘊藏的，是一整套關於水權、勞動組織與社會協作的文化制度。",
        "is_correct": true
      },
      {
        "text": "這表明，基層環保實踐正逐步演進為公民參與社會治理的有效路徑。",
        "is_correct": true
      },
      {
        "text": "這種基於績效的認可機制，與現實社會的成就導向形成映象。",
        "is_correct": true
      },
      {
        "text": "社會正在發生了巨大的變化，我們需要適應這種變化。",
        "is_correct": false,
        "error_description": "“正在”表示動作正在進行，不能與表示完成的動態助詞“了”連用。應刪去“了”或改為“已經”。"
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
      "text": "技术进步是好事，但如果管理不好，也可能带来新的社会问题。",
      "is_correct": true
    },
    {
      "text": "未来可能会有更严格的法律出台，推动社会向更可持续的方向发展。",
      "is_correct": true
    },
    {
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与社会需求共振的产物。",
      "is_correct": true
    },
    {
      "text": "社会已经发展了向更可持续的方向。",
      "is_correct": false,
      "error_description": "语序与体标位置错误。介词短语“向更可持续的方向”应放在动词“发展”之前作状语，动态助词“了”应紧跟在动词之后或放在句末。正确写法为“社会已经向更可持续的方向发展了”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
        "is_correct": true
      },
      {
        "text": "未來可能會有更嚴格的法律出臺，推動社會向更可持續的方向發展。",
        "is_correct": true
      },
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與社會需求共振的產物。",
        "is_correct": true
      },
      {
        "text": "社會已經發展了向更可持續的方向。",
        "is_correct": false,
        "error_description": "語序與體標位置錯誤。介詞短語“向更可持續的方向”應放在動詞“發展”之前作狀語，動態助詞“了”應緊跟在動詞之後或放在句末。正確寫法為“社會已經向更可持續的方向發展了”。"
      }
    ]
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
      "text": "我真正明白过了你的意思。",
      "is_correct": false
    },
    {
      "text": "我真正明白了你的意思。",
      "is_correct": true
    },
    {
      "text": "真正我明白了你的意思。",
      "is_correct": false
    },
    {
      "text": "我真正明白了意思你的。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：宾语“你的意思”语序混乱，代词“你的”应放在名词“意思”之前。 体标错误：“明白”是心理动词，通常不与表示经历的“过”连用，且“过”的位置应在“明白”之后、“了”之前，此处用法不自然。 语序错误：副词“真正”通常放在主语之后、谓语动词之前，不能放在主语“我”之前。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "我真正明白過了你的意思。",
        "is_correct": false
      },
      {
        "text": "我真正明白了你的意思。",
        "is_correct": true
      },
      {
        "text": "真正我明白了你的意思。",
        "is_correct": false
      },
      {
        "text": "我真正明白了意思你的。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：賓語“你的意思”語序混亂，代詞“你的”應放在名詞“意思”之前。 體標錯誤：“明白”是心理動詞，通常不與表示經歷的“過”連用，且“過”的位置應在“明白”之後、“了”之前，此處用法不自然。 語序錯誤：副詞“真正”通常放在主語之後、謂語動詞之前，不能放在主語“我”之前。",
    "target_word": "真正"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "真正",
  "relation": "antonym",
  "options": [
    "其实",
    "大概",
    "假装",
    "非常"
  ],
  "correct_answer": "假装",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（常用来强调所说的话是真实的）",
      "explanation": "反义项：作情态副词时表示故意做出某种姿态，与强调事实的“真正”相对。"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "其實",
      "大概",
      "假裝",
      "非常"
    ],
    "correct_answer": "假裝",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（常用來強調所說的話是真實的）",
        "explanation": "反義項：作情態副詞時表示故意做出某種姿態，與強調事實的“真正”相對。"
      }
    }
  }
}
```

---

## sense 10125, level 7

#### Pack A
### Level 7 (sense 10125, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "朋友聚会可能说“晚上七点”，但真正开始可能是八点甚至更晚。",
      "is_correct": true
    },
    {
      "text": "可持续发展真正需要依赖的，不仅是材料本身的创新，更是配套的分类回收基础设施、政策法规与公众认知的协同演进。",
      "is_correct": true
    },
    {
      "text": "只有大家合作，才能真正解决塑料污染问题。",
      "is_correct": true
    },
    {
      "text": "真正我理解了你的意思。",
      "is_correct": false,
      "error_description": "副词“真正”不能放在主语之前作句首状语，应放在主语之后、谓语动词之前。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "朋友聚會可能說“晚上七點”，但真正開始可能是八點甚至更晚。",
        "is_correct": true
      },
      {
        "text": "可持續發展真正需要依賴的，不僅是材料本身的創新，更是配套的分類回收基礎設施、政策法規與公眾認知的協同演進。",
        "is_correct": true
      },
      {
        "text": "只有大家合作，才能真正解決塑膠汙染問題。",
        "is_correct": true
      },
      {
        "text": "真正我理解了你的意思。",
        "is_correct": false,
        "error_description": "副詞“真正”不能放在主語之前作句首狀語，應放在主語之後、謂語動詞之前。"
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
      "text": "只有内心充实，才能真正感受到快乐。",
      "is_correct": true
    },
    {
      "text": "我把那本书真正看完了。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，副词“真正”应当放在“把”字及其宾语构成的介词短语之前，不能放在“把”字之后。"
    },
    {
      "text": "她真正热爱这份工作，每天都充满了热情。",
      "is_correct": true
    },
    {
      "text": "他真正关心大家，表达的心意十分诚恳。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "只有內心充實，才能真正感受到快樂。",
        "is_correct": true
      },
      {
        "text": "我把那本書真正看完了。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，副詞“真正”應當放在“把”字及其賓語構成的介詞短語之前，不能放在“把”字之後。"
      },
      {
        "text": "她真正熱愛這份工作，每天都充滿了熱情。",
        "is_correct": true
      },
      {
        "text": "他真正關心大家，表達的心意十分誠懇。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10125, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "她真正关心你的感受。",
      "is_correct": true
    },
    {
      "text": "只有长期相处，两人才能真正建立感情。",
      "is_correct": true
    },
    {
      "text": "她关心真正你的感受。",
      "is_correct": false,
      "error_description": "语序错误。副词“真正”应该放在动词“关心”之前作状语，不能放在动词和宾语之间。"
    },
    {
      "text": "我真正喜欢听音乐。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她真正關心你的感受。",
        "is_correct": true
      },
      {
        "text": "只有長期相處，兩人才能真正建立感情。",
        "is_correct": true
      },
      {
        "text": "她關心真正你的感受。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“真正”應該放在動詞“關心”之前作狀語，不能放在動詞和賓語之間。"
      },
      {
        "text": "我真正喜歡聽音樂。",
        "is_correct": true
      }
    ]
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
      "text": "这个地区了的人们都很热情好客。",
      "is_correct": false
    },
    {
      "text": "人们这个地区都很热情好客。",
      "is_correct": false
    },
    {
      "text": "这个地区的人们都很热情好客。",
      "is_correct": true
    },
    {
      "text": "一条地区的人们都很热情好客。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'地区'是表示广阔范围的名词，不能使用用于细长物体的量词'条'，应使用'个'。 语序错误：破坏了'主题—评论'结构，表示范围的'这个地区'应放在主语'人们'之前作为定语或主题。 体标选用错误：'地区'是具体名词，不能直接附加动态助词'了'来表示动作或状态的完成。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "這個地區了的人們都很熱情好客。",
        "is_correct": false
      },
      {
        "text": "人們這個地區都很熱情好客。",
        "is_correct": false
      },
      {
        "text": "這個地區的人們都很熱情好客。",
        "is_correct": true
      },
      {
        "text": "一條地區的人們都很熱情好客。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'地區'是表示廣闊範圍的名詞，不能使用用於細長物體的量詞'條'，應使用'個'。 語序錯誤：破壞了'主題—評論'結構，表示範圍的'這個地區'應放在主語'人們'之前作為定語或主題。 體標選用錯誤：'地區'是具體名詞，不能直接附加動態助詞'了'來表示動作或狀態的完成。",
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

#### Pack B
### Level 7 (sense 10131, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们探索过这个神秘的地区。",
      "is_correct": true
    },
    {
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    },
    {
      "text": "我在这个地区生活着三年。",
      "is_correct": false,
      "error_description": "动态助词“着”表示动作或状态的持续，不能与表示时间段的“三年”连用。表示动作完成或过去的经历，应使用“了”或“过”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們探索過這個神秘的地區。",
        "is_correct": true
      },
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
        "is_correct": true
      },
      {
        "text": "我在這個地區生活著三年。",
        "is_correct": false,
        "error_description": "動態助詞“著”表示動作或狀態的持續，不能與表示時間段的“三年”連用。表示動作完成或過去的經歷，應使用“了”或“過”。"
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
      "text": "他旅游去过很多不同的地区。",
      "is_correct": false,
      "error_description": "在连动句中，表示目的的动词应放在主要动词及地点宾语之后，正确语序为“去+地点+旅游”。"
    },
    {
      "text": "他去过很多不同的地区旅游。",
      "is_correct": true
    },
    {
      "text": "我们要保护好这个地区的生态环境。",
      "is_correct": true
    },
    {
      "text": "偏远地区的教育问题引起了关注。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他旅遊去過很多不同的地區。",
        "is_correct": false,
        "error_description": "在連動句中，表示目的的動詞應放在主要動詞及地點賓語之後，正確語序為“去+地點+旅遊”。"
      },
      {
        "text": "他去過很多不同的地區旅遊。",
        "is_correct": true
      },
      {
        "text": "我們要保護好這個地區的生態環境。",
        "is_correct": true
      },
      {
        "text": "偏遠地區的教育問題引起了關注。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10137, level 3

#### Pack A
### Level 3 (sense 10137, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他所改良的金属活字印刷系统，通过滚筒均匀___纸张，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "original_sentence": "他所改良的金属活字印刷系统，通过滚筒均匀压印纸张，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "correct_answer": "压印",
  "options": [
    "裁剪",
    "压印",
    "涂抹",
    "翻阅"
  ],
  "explanation": "“压印”准确表达了滚筒对纸张施加压力以复制文字的动作，符合印刷系统的专业语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "他所改良的金屬活字印刷系統，通過滾筒均勻___紙張，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "original_sentence": "他所改良的金屬活字印刷系統，通過滾筒均勻壓印紙張，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "correct_answer": "壓印",
    "options": [
      "裁剪",
      "壓印",
      "塗抹",
      "翻閱"
    ],
    "explanation": "“壓印”準確表達了滾筒對紙張施加壓力以複製文字的動作，符合印刷系統的專業語境。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```

#### Pack B
### Level 3 (sense 10137, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面___出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
  "original_sentence": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面压印出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
  "correct_answer": "压印",
  "options": [
    "压印",
    "烙印",
    "盖",
    "描绘"
  ],
  "explanation": "正确选项。符合句中通过机械装置施加压力在纸张上留下文字痕迹的语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面___出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
    "original_sentence": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面壓印出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
    "correct_answer": "壓印",
    "options": [
      "壓印",
      "烙印",
      "蓋",
      "描繪"
    ],
    "explanation": "正確選項。符合句中通過機械裝置施加壓力在紙張上留下文字痕跡的語境。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "你___的图案真好看，我很喜欢。",
  "original_sentence": "你压印的图案真好看，我很喜欢。",
  "correct_answer": "压印",
  "options": [
    "压印",
    "测量",
    "撕裂",
    "销毁"
  ],
  "explanation": "正确。压印指通过压力留下痕迹，符合语境中制作出好看图案的动作。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "你___的圖案真好看，我很喜歡。",
    "original_sentence": "你壓印的圖案真好看，我很喜歡。",
    "correct_answer": "壓印",
    "options": [
      "壓印",
      "測量",
      "撕裂",
      "銷燬"
    ],
    "explanation": "正確。壓印指通過壓力留下痕跡，符合語境中製作出好看圖案的動作。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他压印着过一张明信片。",
      "is_correct": false
    },
    {
      "text": "他正在压印出来一张明信片。",
      "is_correct": false
    },
    {
      "text": "正在他压印一张明信片。",
      "is_correct": false
    },
    {
      "text": "他正在压印一张明信片。",
      "is_correct": true
    }
  ],
  "explanation": "结果补语误用：“压印”本身已包含动作与结果，不能与“出来”连用造成语义重复与结构冗余。 语序错误：时间副词“正在”应放在主语“他”之后、动词“压印”之前，原句破坏了基本的“主—状—谓”语序。 体标选用错误：动态助词“着”表持续，“过”表经历，两者不能同时紧跟在动词后，造成体貌结构冲突。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "他壓印著過一張明信片。",
        "is_correct": false
      },
      {
        "text": "他正在壓印出來一張明信片。",
        "is_correct": false
      },
      {
        "text": "正在他壓印一張明信片。",
        "is_correct": false
      },
      {
        "text": "他正在壓印一張明信片。",
        "is_correct": true
      }
    ],
    "explanation": "結果補語誤用：“壓印”本身已包含動作與結果，不能與“出來”連用造成語義重複與結構冗餘。 語序錯誤：時間副詞“正在”應放在主語“他”之後、動詞“壓印”之前，原句破壞了基本的“主—狀—謂”語序。 體標選用錯誤：動態助詞“著”表持續，“過”表經歷，兩者不能同時緊跟在動詞後，造成體貌結構衝突。",
    "target_word": "壓印"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "拓印",
    "抹平",
    "压制",
    "雕刻"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "抹平指将物体表面的痕迹或凸起弄平，与压印（留下痕迹或图案）在动作结果上构成反义关系。"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "拓印",
      "抹平",
      "壓制",
      "雕刻"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "抹平指將物體表面的痕跡或凸起弄平，與壓印（留下痕跡或圖案）在動作結果上構成反義關係。"
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
      "text": "他正在压印了那张明信片。",
      "is_correct": false
    },
    {
      "text": "请用模具把花纹压印上去。",
      "is_correct": true
    },
    {
      "text": "请用模具把花纹压印下去。",
      "is_correct": false
    },
    {
      "text": "他压印在卡片上名字。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。体标“了”表示动作完成，与表示进行的“正在”在语义上冲突，应删去“了”或改为“压印了”。 语序错误。宾语“名字”和处所补语“在卡片上”位置颠倒，应改为“把名字压印在卡片上”或“在卡片上压印名字”。 方向/结果补语误用。“下去”表示动作继续或向下离开，此处表示花纹附着在物体表面，应使用“上去”或“出来”。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "他正在壓印了那張明信片。",
        "is_correct": false
      },
      {
        "text": "請用模具把花紋壓印上去。",
        "is_correct": true
      },
      {
        "text": "請用模具把花紋壓印下去。",
        "is_correct": false
      },
      {
        "text": "他壓印在卡片上名字。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。體標“了”表示動作完成，與表示進行的“正在”在語義上衝突，應刪去“了”或改為“壓印了”。 語序錯誤。賓語“名字”和處所補語“在卡片上”位置顛倒，應改為“把名字壓印在卡片上”或“在卡片上壓印名字”。 方向/結果補語誤用。“下去”表示動作繼續或向下離開，此處表示花紋附著在物體表面，應使用“上去”或“出來”。",
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
    "拓印",
    "雕刻"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义项：“压印”指施加压力制造痕迹，“抹平”指消除痕迹使表面恢复平整"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "壓制",
      "抹平",
      "拓印",
      "雕刻"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義項：“壓印”指施加壓力製造痕跡，“抹平”指消除痕跡使表面恢復平整"
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
      "text": "他压印在卡片上把名字。",
      "is_correct": false,
      "error_description": "语序错误。“把”字句的基本结构为“主语+把+宾语+动词+补语”，宾语“名字”必须紧跟在“把”字之后，而处所补语“在卡片上”应放在动词“压印”之后。"
    },
    {
      "text": "我们在纸上压印美丽的图案。",
      "is_correct": true
    },
    {
      "text": "他所改良的金属活字印刷系统，通过滚筒均匀压印纸张，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
      "is_correct": true
    },
    {
      "text": "他把名字压印在卡片上。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他壓印在卡片上把名字。",
        "is_correct": false,
        "error_description": "語序錯誤。“把”字句的基本結構為“主語+把+賓語+動詞+補語”，賓語“名字”必須緊跟在“把”字之後，而處所補語“在卡片上”應放在動詞“壓印”之後。"
      },
      {
        "text": "我們在紙上壓印美麗的圖案。",
        "is_correct": true
      },
      {
        "text": "他所改良的金屬活字印刷系統，通過滾筒均勻壓印紙張，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
        "is_correct": true
      },
      {
        "text": "他把名字壓印在卡片上。",
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
      "text": "请用模具把花纹压印上去。",
      "is_correct": true
    },
    {
      "text": "他压印过很多漂亮的书签。",
      "is_correct": true
    },
    {
      "text": "这枚硬币是机器压印的。",
      "is_correct": true
    },
    {
      "text": "他压印了昨天一张明信片。",
      "is_correct": false,
      "error_description": "时间状语“昨天”应放在动词“压印”之前，体标记“了”应紧跟在动词之后。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "請用模具把花紋壓印上去。",
        "is_correct": true
      },
      {
        "text": "他壓印過很多漂亮的書籤。",
        "is_correct": true
      },
      {
        "text": "這枚硬幣是機器壓印的。",
        "is_correct": true
      },
      {
        "text": "他壓印了昨天一張明信片。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”應放在動詞“壓印”之前，體標記“了”應緊跟在動詞之後。"
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

---

## sense 10156, level 6

#### Pack A
### Level 6 (sense 10156, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的压力。",
      "is_correct": true
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的着压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的过压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更前所未有的对地球脆弱的水资源系统施加了压力。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：“施加压力”是一个瞬间或持续的动作行为，不能用表示状态持续的体标记“着”，应直接说“施加了前所未有的压力”。 语序错误：“前所未有”作为形容词性短语，应紧贴其修饰的中心语“压力”作定语，不能直接放在介词短语“对……”之前作状语。 体标位置/选用错误：“过”表示过去的经历或完结，而句中“施加了……压力”强调的是当前已经造成并持续存在的客观结果，使用“过”会导致体貌冲突。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的壓力。",
        "is_correct": true
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的著壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的過壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更前所未有的對地球脆弱的水資源系統施加了壓力。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：“施加壓力”是一個瞬間或持續的動作行為，不能用表示狀態持續的體標記“著”，應直接說“施加了前所未有的壓力”。 語序錯誤：“前所未有”作為形容詞性短語，應緊貼其修飾的中心語“壓力”作定語，不能直接放在介詞短語“對……”之前作狀語。 體標位置/選用錯誤：“過”表示過去的經歷或完結，而句中“施加了……壓力”強調的是當前已經造成並持續存在的客觀結果，使用“過”會導致體貌衝突。",
    "target_word": "前所未有"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "微不足道",
    "平淡无奇",
    "司空见惯",
    "史无前例"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从未出现过或发生过。",
      "explanation": "反义项：指某事常见，不足为奇，与“前所未有”构成反义"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "微不足道",
      "平淡無奇",
      "司空見慣",
      "史無前例"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從未出現過或發生過。",
        "explanation": "反義項：指某事常見，不足為奇，與“前所未有”構成反義"
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
      "text": "她的热情达到了前所未有着高度。",
      "is_correct": false
    },
    {
      "text": "她的热情达到了前所未有的高度。",
      "is_correct": true
    },
    {
      "text": "她的热情达到了前所未有的高。",
      "is_correct": false
    },
    {
      "text": "前所未有她的热情达到了高度。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。动态助词“着”表示动作或状态的持续，不能直接放在形容词“前所未有”和结构助词“的”之间，应改为“的”。 语序错误。“前所未有”作为定语修饰“高度”时，必须紧跟在中心语之前，不能脱离名词短语提前至句首作状语。 搭配错误。“达到”后面通常接名词性宾语（如“高度”、“水平”），而“高”是形容词，不能直接作“达到”的宾语。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "她的熱情達到了前所未有著高度。",
        "is_correct": false
      },
      {
        "text": "她的熱情達到了前所未有的高度。",
        "is_correct": true
      },
      {
        "text": "她的熱情達到了前所未有的高。",
        "is_correct": false
      },
      {
        "text": "前所未有她的熱情達到了高度。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。動態助詞“著”表示動作或狀態的持續，不能直接放在形容詞“前所未有”和結構助詞“的”之間，應改為“的”。 語序錯誤。“前所未有”作為定語修飾“高度”時，必須緊跟在中心語之前，不能脫離名詞短語提前至句首作狀語。 搭配錯誤。“達到”後面通常接名詞性賓語（如“高度”、“水平”），而“高”是形容詞，不能直接作“達到”的賓語。",
    "target_word": "前所未有"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "平淡无奇",
    "绝无仅有",
    "司空见惯",
    "史无前例"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从未出现过或发生过。",
      "explanation": "指某事常见，不足为奇，与“前所未有”（从未发生过）构成反义关系。"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "平淡無奇",
      "絕無僅有",
      "司空見慣",
      "史無前例"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從未出現過或發生過。",
        "explanation": "指某事常見，不足為奇，與“前所未有”（從未發生過）構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10156, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了压力前所未有的。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更前所未有的对地球脆弱的水资源系统施加了压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的压力。",
      "is_correct": true
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加前所未有的了压力。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误。动态助词“了”应放在动词“施加”之后或句末，不能插入在定语“前所未有”和中心语“压力”之间，破坏了定中结构。 语序错误。“前所未有”作为定语修饰“压力”时，必须放在中心语“压力”之前。放在句末导致动宾结构“施加了压力”被割裂，语序混乱。 语序错误。“前所未有”是形容词，不能直接放在介词结构或动词前作状语。应改为副词性结构“前所未有地”，或将其作为定语修饰“压力”。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了壓力前所未有的。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更前所未有的對地球脆弱的水資源系統施加了壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的壓力。",
        "is_correct": true
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加前所未有的了壓力。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤。動態助詞“了”應放在動詞“施加”之後或句末，不能插入在定語“前所未有”和中心語“壓力”之間，破壞了定中結構。 語序錯誤。“前所未有”作為定語修飾“壓力”時，必須放在中心語“壓力”之前。放在句末導致動賓結構“施加了壓力”被割裂，語序混亂。 語序錯誤。“前所未有”是形容詞，不能直接放在介詞結構或動詞前作狀語。應改為副詞性結構“前所未有地”，或將其作為定語修飾“壓力”。",
    "target_word": "前所未有"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "昙花一现",
    "平淡无奇",
    "史无前例",
    "司空见惯"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从来没有发生过或出现过的。",
      "explanation": "反义项：指某事常见，不足为奇，与“前所未有”（以前从未有过）构成反义。"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "曇花一現",
      "平淡無奇",
      "史無前例",
      "司空見慣"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從來沒有發生過或出現過的。",
        "explanation": "反義項：指某事常見，不足為奇，與“前所未有”（以前從未有過）構成反義。"
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
      "text": "这次活动的规模是前所未有的。",
      "is_correct": true
    },
    {
      "text": "这次活动的规模前所未有起来。",
      "is_correct": false
    },
    {
      "text": "这次活动的规模是前所未有过了。",
      "is_correct": false
    },
    {
      "text": "前所未有的这次活动的规模让我们震惊。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：“前所未有”本身已包含完成和过去的语义（“未有”），再叠加体标“过”和“了”导致体标冗余且位置不当。 语序错误：“前所未有”作定语时应紧挨着被修饰的中心语“规模”，即“这次活动前所未有的规模”，当前语序破坏了定中结构的紧密性。 方向/结果补语误用：“起来”表示动作或状态的开始与向上发展，而“前所未有”表示一种已经存在的极致状态，两者在体貌和语义上冲突，不能搭配。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "這次活動的規模是前所未有的。",
        "is_correct": true
      },
      {
        "text": "這次活動的規模前所未有起來。",
        "is_correct": false
      },
      {
        "text": "這次活動的規模是前所未有過了。",
        "is_correct": false
      },
      {
        "text": "前所未有的這次活動的規模讓我們震驚。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：“前所未有”本身已包含完成和過去的語義（“未有”），再疊加體標“過”和“了”導致體標冗餘且位置不當。 語序錯誤：“前所未有”作定語時應緊挨著被修飾的中心語“規模”，即“這次活動前所未有的規模”，當前語序破壞了定中結構的緊密性。 方向/結果補語誤用：“起來”表示動作或狀態的開始與向上發展，而“前所未有”表示一種已經存在的極致狀態，兩者在體貌和語義上衝突，不能搭配。",
    "target_word": "前所未有"
  }
}
```

---
