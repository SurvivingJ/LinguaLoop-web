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

#### Pack B
### Level 3 (sense 10112, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复___的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "排版",
  "options": [
    "雕刻",
    "书写",
    "印刷",
    "排版"
  ],
  "explanation": "正确。'排版'指将文字和图片按规则排列，符合印刷技术发展的语境。",
  "distractor_tags": {},
  "word_definition": "把文字和图片按规则排列组合，方便阅读。",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複___的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "排版",
    "options": [
      "雕刻",
      "書寫",
      "印刷",
      "排版"
    ],
    "explanation": "正確。'排版'指將文字和圖片按規則排列，符合印刷技術發展的語境。",
    "distractor_tags": {},
    "word_definition": "把文字和圖片按規則排列組合，方便閱讀。",
    "target_word": "排版"
  }
}
```

---

## sense 10112, level 6

#### Pack A
### Level 6 (sense 10112, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "设计",
    "打乱",
    "印刷",
    "编辑"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字和图片按规则排列组合，方便阅读。",
      "explanation": "反义项：排版是按规则排列组合使之有序，打乱是破坏既有秩序使之无序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "設計",
      "打亂",
      "印刷",
      "編輯"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字和圖片按規則排列組合，方便閱讀。",
        "explanation": "反義項：排版是按規則排列組合使之有序，打亂是破壞既有秩序使之無序"
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
      "text": "很快他排版的速度。",
      "is_correct": false
    },
    {
      "text": "他排版的速度很快。",
      "is_correct": true
    },
    {
      "text": "他排版的速度很块。",
      "is_correct": false
    },
    {
      "text": "他排版的速度很快了。",
      "is_correct": false
    }
  ],
  "explanation": "错别字/词汇错误：“块”应为“快”。“块”是名词或量词，不能用来形容速度的高低。 体标错误：句末误加了动态助词“了”。形容主语具备的固有属性或能力（速度快）时，不需要加表示状态变化或完成的“了”。 语序错误：程度副词“很快”不能直接放在主语“他排版的速度”之前作谓语，应改为“他排版的速度很快”。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "很快他排版的速度。",
        "is_correct": false
      },
      {
        "text": "他排版的速度很快。",
        "is_correct": true
      },
      {
        "text": "他排版的速度很塊。",
        "is_correct": false
      },
      {
        "text": "他排版的速度很快了。",
        "is_correct": false
      }
    ],
    "explanation": "錯別字/詞彙錯誤：“塊”應為“快”。“塊”是名詞或量詞，不能用來形容速度的高低。 體標錯誤：句末誤加了動態助詞“了”。形容主語具備的固有屬性或能力（速度快）時，不需要加表示狀態變化或完成的“了”。 語序錯誤：程度副詞“很快”不能直接放在主語“他排版的速度”之前作謂語，應改為“他排版的速度很快”。",
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
    "编辑",
    "打乱",
    "印刷",
    "校对"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字和图片按规则排列组合，方便阅读。",
      "explanation": "反义：排版是使图文按规则有序组合，打乱则是破坏其排列组合使之无序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "編輯",
      "打亂",
      "印刷",
      "校對"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字和圖片按規則排列組合，方便閱讀。",
        "explanation": "反義：排版是使圖文按規則有序組合，打亂則是破壞其排列組合使之無序"
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

## sense 10112, level 7

#### Pack A
### Level 7 (sense 10112, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我正在为校刊排版。",
      "is_correct": true
    },
    {
      "text": "请把这篇文章排版下来。",
      "is_correct": false,
      "error_description": "错误类型为结果补语误用。“排版”表示使文章格式整齐，达到预期效果应使用结果补语“好”，正确写法为“排版好”，不能用“下来”。"
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我正在為校刊排版。",
        "is_correct": true
      },
      {
        "text": "請把這篇文章排版下來。",
        "is_correct": false,
        "error_description": "錯誤型別為結果補語誤用。“排版”表示使文章格式整齊，達到預期效果應使用結果補語“好”，正確寫法為“排版好”，不能用“下來”。"
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10112, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这本书的排版非常漂亮。",
      "is_correct": true
    },
    {
      "text": "他正在排版了那本杂志。",
      "is_correct": false,
      "error_description": "体标“了”表示动作完成，与表示动作进行的“正在”在语义上冲突。应删去“了”，或将“正在”改为“已经”。"
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這本書的排版非常漂亮。",
        "is_correct": true
      },
      {
        "text": "他正在排版了那本雜誌。",
        "is_correct": false,
        "error_description": "體標“了”表示動作完成，與表示動作進行的“正在”在語義上衝突。應刪去“了”，或將“正在”改為“已經”。"
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10113, level 6

#### Pack A
### Level 6 (sense 10113, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正开着先河，后面的事就好办了。",
      "is_correct": false
    },
    {
      "text": "他先河开了，后面的事就好办了。",
      "is_correct": false
    },
    {
      "text": "这是一条先河，大家都很喜欢。",
      "is_correct": false
    },
    {
      "text": "先河之作的销量非常好。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：“先河”是抽象名词，指代开创的做法，不能使用具体名词的量词“条”。 体标选用错误：“开先河”表示开创的完成动作，具有瞬间性，不能使用表示动作持续的体标“着”。 语序错误：宾语“先河”错误地放在了动词“开”之前，破坏了正常的“主—谓—宾”语序。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "他正開著先河，後面的事就好辦了。",
        "is_correct": false
      },
      {
        "text": "他先河開了，後面的事就好辦了。",
        "is_correct": false
      },
      {
        "text": "這是一條先河，大家都很喜歡。",
        "is_correct": false
      },
      {
        "text": "先河之作的銷量非常好。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：“先河”是抽象名詞，指代開創的做法，不能使用具體名詞的量詞“條”。 體標選用錯誤：“開先河”表示開創的完成動作，具有瞬間性，不能使用表示動作持續的體標“著”。 語序錯誤：賓語“先河”錯誤地放在了動詞“開”之前，破壞了正常的“主—謂—賓”語序。",
    "target_word": "先河"
  }
}
```

#### Pack B
### Level 6 (sense 10113, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "relation": "antonym",
  "options": [
    "末流",
    "圭臬",
    "窠臼",
    "滥觞"
  ],
  "correct_answer": "末流",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某个事业或行动的最早做法或开创者。",
      "explanation": "反义：指事物的末尾或流派的末流，与表发端开创的先河相对"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "末流",
      "圭臬",
      "窠臼",
      "濫觴"
    ],
    "correct_answer": "末流",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某個事業或行動的最早做法或開創者。",
        "explanation": "反義：指事物的末尾或流派的末流，與表發端開創的先河相對"
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
      "text": "他的发明先河开启了新技术。",
      "is_correct": false
    },
    {
      "text": "他的发明开启了新技术的先河着。",
      "is_correct": false
    },
    {
      "text": "他的发明开启了新技术的一个先河。",
      "is_correct": false
    },
    {
      "text": "他的发明开启了新技术的先河。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：'先河'作为抽象名词，通常受'个'修饰或直接与动词搭配，不能用量词'一个'来修饰。 体标位置错误：动态助词'着'表示动作持续，不能直接放在宾语'先河'之后，应放在动词'开启'之后或省略。 语序错误：'先河'是动词'开启'的宾语，被错误地提前到了主语'他的发明'和谓语'开启'之间，破坏了正常的动宾结构。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "他的發明先河開啟了新技術。",
        "is_correct": false
      },
      {
        "text": "他的發明開啟了新技術的先河著。",
        "is_correct": false
      },
      {
        "text": "他的發明開啟了新技術的一個先河。",
        "is_correct": false
      },
      {
        "text": "他的發明開啟了新技術的先河。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：'先河'作為抽象名詞，通常受'個'修飾或直接與動詞搭配，不能用量詞'一個'來修飾。 體標位置錯誤：動態助詞'著'表示動作持續，不能直接放在賓語'先河'之後，應放在動詞'開啟'之後或省略。 語序錯誤：'先河'是動詞'開啟'的賓語，被錯誤地提前到了主語'他的發明'和謂語'開啟'之間，破壞了正常的動賓結構。",
    "target_word": "先河"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "先河",
  "relation": "antonym",
  "options": [
    "圭臬",
    "滥觞",
    "末流",
    "余绪"
  ],
  "correct_answer": "末流",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某个事业或行动的最早做法或开创者。",
      "explanation": "反义项：先河喻指事物的开端与创始，末流喻指事物的末端与衰落阶段，二者在源流脉络上构成反义。"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "圭臬",
      "濫觴",
      "末流",
      "餘緒"
    ],
    "correct_answer": "末流",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某個事業或行動的最早做法或開創者。",
        "explanation": "反義項：先河喻指事物的開端與創始，末流喻指事物的末端與衰落階段，二者在源流脈絡上構成反義。"
      }
    }
  }
}
```

---

## sense 10113, level 7

#### Pack A
### Level 7 (sense 10113, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "先河已开，同学们都跟着做。",
      "is_correct": true
    },
    {
      "text": "这本先河之作非常受欢迎。",
      "is_correct": true
    },
    {
      "text": "他昨天开着先河，大家都跟着学。",
      "is_correct": false,
      "error_description": "体标选用错误。“开先河”表示开创先例，是已经完成的动作，应使用表示完成的体标“了”，而不是表示动作持续的“着”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "先河已開，同學們都跟著做。",
        "is_correct": true
      },
      {
        "text": "這本先河之作非常受歡迎。",
        "is_correct": true
      },
      {
        "text": "他昨天開著先河，大家都跟著學。",
        "is_correct": false,
        "error_description": "體標選用錯誤。“開先河”表示開創先例，是已經完成的動作，應使用表示完成的體標“了”，而不是表示動作持續的“著”。"
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
      "text": "老师表扬了他，说他开了先河。",
      "is_correct": true
    },
    {
      "text": "先河一开，后面的事就好办了。",
      "is_correct": true
    },
    {
      "text": "他开先河了，大家都跟着做。",
      "is_correct": false,
      "error_description": "“开先河”是动宾结构，表示动作完成的动态助词“了”应放在动词“开”和宾语“先河”之间，即“开了先河”，不能放在句末。"
    },
    {
      "text": "先河之作的销量非常好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師表揚了他，說他開了先河。",
        "is_correct": true
      },
      {
        "text": "先河一開，後面的事就好辦了。",
        "is_correct": true
      },
      {
        "text": "他開先河了，大家都跟著做。",
        "is_correct": false,
        "error_description": "“開先河”是動賓結構，表示動作完成的動態助詞“了”應放在動詞“開”和賓語“先河”之間，即“開了先河”，不能放在句末。"
      },
      {
        "text": "先河之作的銷量非常好。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10113, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他的发明开启了新技术的先河。",
      "is_correct": true
    },
    {
      "text": "他的设计开启了先河在时尚界。",
      "is_correct": false,
      "error_description": "语序错误。表示范围或领域的介词短语（如“在时尚界”）不能放在动词和宾语之后，应作为定语修饰“先河”，改为“时尚界的先河”。"
    },
    {
      "text": "这项活动开启了校园文化的先河。",
      "is_correct": true
    },
    {
      "text": "他的设计开启了时尚界的先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的發明開啟了新技術的先河。",
        "is_correct": true
      },
      {
        "text": "他的設計開啟了先河在時尚界。",
        "is_correct": false,
        "error_description": "語序錯誤。表示範圍或領域的介詞短語（如“在時尚界”）不能放在動詞和賓語之後，應作為定語修飾“先河”，改為“時尚界的先河”。"
      },
      {
        "text": "這項活動開啟了校園文化的先河。",
        "is_correct": true
      },
      {
        "text": "他的設計開啟了時尚界的先河。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10117, level 6

#### Pack A
### Level 6 (sense 10117, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "庞大",
  "relation": "antonym",
  "options": [
    "微小",
    "巨大",
    "单薄",
    "复杂"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "反义项：形容体积、规模或数量等非常小，与目标词构成反义"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "微小",
      "巨大",
      "單薄",
      "複雜"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "反義項：形容體積、規模或數量等非常小，與目標詞構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "庞大",
  "relation": "antonym",
  "options": [
    "巨大",
    "平整",
    "纤细",
    "微小"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "反义项：形容体积、规模或数量等非常小，与目标词构成反义。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "巨大",
      "平整",
      "纖細",
      "微小"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "反義項：形容體積、規模或數量等非常小，與目標詞構成反義。"
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

---

## sense 10117, level 7

#### Pack A
### Level 7 (sense 10117, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个项目的规模十分庞大。",
      "is_correct": true
    },
    {
      "text": "这个计划看起来太庞大了。",
      "is_correct": true
    },
    {
      "text": "这个组织的结构非常庞大。",
      "is_correct": true
    },
    {
      "text": "这个项目的规模庞大十分。",
      "is_correct": false,
      "error_description": "程度副词“十分”应放在形容词“庞大”之前作状语，不能放在形容词之后。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個專案的規模十分龐大。",
        "is_correct": true
      },
      {
        "text": "這個計劃看起來太龐大了。",
        "is_correct": true
      },
      {
        "text": "這個組織的結構非常龐大。",
        "is_correct": true
      },
      {
        "text": "這個專案的規模龐大十分。",
        "is_correct": false,
        "error_description": "程度副詞“十分”應放在形容詞“龐大”之前作狀語，不能放在形容詞之後。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10117, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个庞大的计划让我们感到压力。",
      "is_correct": true
    },
    {
      "text": "他的身躯庞大十分。",
      "is_correct": false,
      "error_description": "程度副词“十分”应放在形容词“庞大”之前作状语，不能放在形容词之后。"
    },
    {
      "text": "他的身躯看起来十分庞大。",
      "is_correct": true
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個龐大的計劃讓我們感到壓力。",
        "is_correct": true
      },
      {
        "text": "他的身軀龐大十分。",
        "is_correct": false,
        "error_description": "程度副詞“十分”應放在形容詞“龐大”之前作狀語，不能放在形容詞之後。"
      },
      {
        "text": "他的身軀看起來十分龐大。",
        "is_correct": true
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
        "is_correct": true
      }
    ]
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
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "社会",
  "relation": "antonym",
  "options": [
    "国家",
    "群体",
    "世界",
    "自然"
  ],
  "correct_answer": "自然",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益、文化或制度联系起来的人群整体。",
      "explanation": "反义：指与人类社会相对的自然界"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "國家",
      "群體",
      "世界",
      "自然"
    ],
    "correct_answer": "自然",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益、文化或制度聯絡起來的人群整體。",
        "explanation": "反義：指與人類社會相對的自然界"
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

#### Pack B
### Level 7 (sense 10119, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他大学毕业后，终于成功地走进入社会了。",
      "is_correct": false,
      "error_description": "方向补语误用。“进入”本身已包含“入”的方向意义，不能再叠加“入”构成“走进入”，应改为“走入”或“走进”。"
    },
    {
      "text": "这些水利系统背后所蕴藏的，是一整套关于水权、劳动组织与社会协作的文化制度。",
      "is_correct": true
    },
    {
      "text": "这种基于绩效的认可机制，与现实社会的成就导向形成镜像。",
      "is_correct": true
    },
    {
      "text": "这表明，基层环保实践正逐步演进为公民参与社会治理的有效路径。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他大學畢業後，終於成功地走進入社會了。",
        "is_correct": false,
        "error_description": "方向補語誤用。“進入”本身已包含“入”的方向意義，不能再疊加“入”構成“走進入”，應改為“走入”或“走進”。"
      },
      {
        "text": "這些水利系統背後所蘊藏的，是一整套關於水權、勞動組織與社會協作的文化制度。",
        "is_correct": true
      },
      {
        "text": "這種基於績效的認可機制，與現實社會的成就導向形成映象。",
        "is_correct": true
      },
      {
        "text": "這表明，基層環保實踐正逐步演進為公民參與社會治理的有效路徑。",
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
      "text": "大学毕业生在离开学校后，需要尽快融入一条新的社会。",
      "is_correct": false,
      "error_description": "量词使用错误。“社会”是抽象名词，不能用修饰长条形事物的量词“条”，应使用“个”或直接省略量词说“融入社会”。"
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
        "text": "大學畢業生在離開學校後，需要儘快融入一條新的社會。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“社會”是抽象名詞，不能用修飾長條形事物的量詞“條”，應使用“個”或直接省略量詞說“融入社會”。"
      },
      {
        "text": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10125, level 6

#### Pack A
### Level 6 (sense 10125, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "真正",
  "relation": "antonym",
  "options": [
    "果然",
    "确实",
    "虚假",
    "其实"
  ],
  "correct_answer": "虚假",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "确实；表示所说的话是真实的",
      "explanation": "反义：「真正」表确实真实，「虚假」表不真实、伪造，二者在「真/假」义上构成反义"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "果然",
      "確實",
      "虛假",
      "其實"
    ],
    "correct_answer": "虛假",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "確實；表示所說的話是真實的",
        "explanation": "反義：「真正」表確實真實，「虛假」表不真實、偽造，二者在「真/假」義上構成反義"
      }
    }
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

---
