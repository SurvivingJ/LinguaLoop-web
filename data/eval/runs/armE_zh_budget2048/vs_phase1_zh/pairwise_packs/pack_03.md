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


## sense 10111, level 7

#### Pack A
### Level 7 (sense 10111, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个标志的三个箭头代表废物管理的三个步骤：减少使用、重复利用、回收处理。",
      "is_correct": true
    },
    {
      "text": "老师把重复了一遍重点。",
      "is_correct": false,
      "error_description": "在“把”字句中，“把”的宾语（重点）必须放在“把”之后、动词（重复）之前，不能放在动词之后。"
    },
    {
      "text": "这个过程会重复很多次，直到飞机飞得又快又稳又安全。",
      "is_correct": true
    },
    {
      "text": "它的设计像一个绿色的箭头圆圈，表示废物可以被重复利用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個標誌的三個箭頭代表廢物管理的三個步驟：減少使用、重複利用、回收處理。",
        "is_correct": true
      },
      {
        "text": "老師把重複了一遍重點。",
        "is_correct": false,
        "error_description": "在“把”字句中，“把”的賓語（重點）必須放在“把”之後、動詞（重複）之前，不能放在動詞之後。"
      },
      {
        "text": "這個過程會重複很多次，直到飛機飛得又快又穩又安全。",
        "is_correct": true
      },
      {
        "text": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被重複利用。",
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
      "text": "这个笑话他重复过了。",
      "is_correct": true
    },
    {
      "text": "请你把刚才的话重复起来。",
      "is_correct": false,
      "error_description": "“重复”不能与趋向补语“起来”搭配，表示动作的重复应使用动量补语“一次”或“一遍”。"
    },
    {
      "text": "请你把刚才的话重复一次。",
      "is_correct": true
    },
    {
      "text": "我不喜欢这种重复的游戏。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個笑話他重複過了。",
        "is_correct": true
      },
      {
        "text": "請你把剛才的話重複起來。",
        "is_correct": false,
        "error_description": "“重複”不能與趨向補語“起來”搭配，表示動作的重複應使用動量補語“一次”或“一遍”。"
      },
      {
        "text": "請你把剛才的話重複一次。",
        "is_correct": true
      },
      {
        "text": "我不喜歡這種重複的遊戲。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10111, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他重复了刚才的话昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”位置错误。在汉语中，时间状语通常放在主语之后、谓语动词之前，不能放在句末。"
    },
    {
      "text": "这个标志的三个箭头代表废物管理的三个步骤：减少使用、重复利用、回收处理。",
      "is_correct": true
    },
    {
      "text": "这个过程会重复很多次，直到飞机飞得又快又稳又安全。",
      "is_correct": true
    },
    {
      "text": "它的设计像一个绿色的箭头圆圈，表示废物可以被重复利用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他重複了剛才的話昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”位置錯誤。在漢語中，時間狀語通常放在主語之後、謂語動詞之前，不能放在句末。"
      },
      {
        "text": "這個標誌的三個箭頭代表廢物管理的三個步驟：減少使用、重複利用、回收處理。",
        "is_correct": true
      },
      {
        "text": "這個過程會重複很多次，直到飛機飛得又快又穩又安全。",
        "is_correct": true
      },
      {
        "text": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被重複利用。",
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
      "text": "请不要这句话重复。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，及物动词的宾语通常放在动词之后，‘这句话’应放在‘重复’之后。"
    },
    {
      "text": "老师重复着那个重要的观点。",
      "is_correct": true
    },
    {
      "text": "我们不要重复这个错误。",
      "is_correct": true
    },
    {
      "text": "请不要重复这句话。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "請不要這句話重複。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，及物動詞的賓語通常放在動詞之後，‘這句話’應放在‘重複’之後。"
      },
      {
        "text": "老師重複著那個重要的觀點。",
        "is_correct": true
      },
      {
        "text": "我們不要重複這個錯誤。",
        "is_correct": true
      },
      {
        "text": "請不要重複這句話。",
        "is_correct": true
      }
    ]
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
    "雕刻",
    "装订",
    "排版",
    "抄写"
  ],
  "explanation": "正确选项。泥活字的核心创新在于可以重复排列组合文字，即“排版”。",
  "distractor_tags": {},
  "word_definition": "将文字、图片等素材按一定规则或格式进行排列、组合，以便于阅读或展示。",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複___的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "排版",
    "options": [
      "雕刻",
      "裝訂",
      "排版",
      "抄寫"
    ],
    "explanation": "正確選項。泥活字的核心創新在於可以重複排列組合文字，即“排版”。",
    "distractor_tags": {},
    "word_definition": "將文字、圖片等素材按一定規則或格式進行排列、組合，以便於閱讀或展示。",
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

## sense 10112, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 10112, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "打乱",
    "校对",
    "编辑",
    "打印"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "将文字、图片等素材按一定规则或格式进行排列、组合，以便于阅读或展示。",
      "explanation": "反义：排版指按规则排列组合，打乱指破坏原有排列与秩序，二者构成动作反义。"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "打亂",
      "校對",
      "編輯",
      "列印"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "將文字、圖片等素材按一定規則或格式進行排列、組合，以便於閱讀或展示。",
        "explanation": "反義：排版指按規則排列組合，打亂指破壞原有排列與秩序，二者構成動作反義。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "设计",
    "印刷",
    "编辑",
    "打乱"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "将文字、图片等素材按一定规则或格式进行排列、组合，以便于阅读或展示。",
      "explanation": "反义：排版指按规则排列组合素材，打乱指破坏已有的排列秩序，二者动作方向相反"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "設計",
      "印刷",
      "編輯",
      "打亂"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "將文字、圖片等素材按一定規則或格式進行排列、組合，以便於閱讀或展示。",
        "explanation": "反義：排版指按規則排列組合素材，打亂指破壞已有的排列秩序，二者動作方向相反"
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他排版了杂志在办公室。",
      "is_correct": false,
      "error_description": "地点状语“在办公室”应放在动词“排版”之前，不能放在句末。"
    },
    {
      "text": "他学会了电脑排版。",
      "is_correct": true
    },
    {
      "text": "他排版印出了这本杂志。",
      "is_correct": true
    },
    {
      "text": "排版格式必须整齐。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他排版了雜誌在辦公室。",
        "is_correct": false,
        "error_description": "地點狀語“在辦公室”應放在動詞“排版”之前，不能放在句末。"
      },
      {
        "text": "他學會了電腦排版。",
        "is_correct": true
      },
      {
        "text": "他排版印出了這本雜誌。",
        "is_correct": true
      },
      {
        "text": "排版格式必須整齊。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10113, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 10113, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "他的做法堪称社交___。",
  "original_sentence": "他的做法堪称社交先河。",
  "correct_answer": "先河",
  "options": [
    "常规",
    "先锋",
    "风气",
    "先河"
  ],
  "explanation": "正确。符合语境，指代首创的做法。",
  "distractor_tags": {},
  "word_definition": "比喻某一事业或行动的开创者或最早的做法。",
  "target_word": "先河",
  "hant": {
    "sentence_with_blank": "他的做法堪稱社交___。",
    "original_sentence": "他的做法堪稱社交先河。",
    "correct_answer": "先河",
    "options": [
      "常規",
      "先鋒",
      "風氣",
      "先河"
    ],
    "explanation": "正確。符合語境，指代首創的做法。",
    "distractor_tags": {},
    "word_definition": "比喻某一事業或行動的開創者或最早的做法。",
    "target_word": "先河"
  }
}
```

---

## sense 10113, level 6

#### Pack A
### Level 6 (sense 10113, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他为了帮助贫困学生，开创了一只先河。",
      "is_correct": false
    },
    {
      "text": "这位科学家正在开创着该领域的先河。",
      "is_correct": false
    },
    {
      "text": "先河总是由勇敢的人开创。",
      "is_correct": true
    },
    {
      "text": "先河由勇敢的人总是去开创。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“先河”为抽象名词，不能使用具体事物的量词“只”，应使用“个”或省略量词。 体标选用错误：“开创”表示已经完成的动作，不能与表示动作持续的“着”连用，应改为“开创了”。 语序错误：副词“总是”应放在介词“由”之前，以修饰整个被动句式，原句破坏了正常的状语位置。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "他為了幫助貧困學生，開創了一隻先河。",
        "is_correct": false
      },
      {
        "text": "這位科學家正在開創著該領域的先河。",
        "is_correct": false
      },
      {
        "text": "先河總是由勇敢的人開創。",
        "is_correct": true
      },
      {
        "text": "先河由勇敢的人總是去開創。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“先河”為抽象名詞，不能使用具體事物的量詞“只”，應使用“個”或省略量詞。 體標選用錯誤：“開創”表示已經完成的動作，不能與表示動作持續的“著”連用，應改為“開創了”。 語序錯誤：副詞“總是”應放在介詞“由”之前，以修飾整個被動句式，原句破壞了正常的狀語位置。",
    "target_word": "先河"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "先河",
  "relation": "antonym",
  "options": [
    "渊源",
    "流派",
    "末流",
    "源流"
  ],
  "correct_answer": "末流",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某一事业或行动的开创者或最早的做法。",
      "explanation": "先河喻事业之开创与起源，末流指传统之末端与衰落，二者在事物发展的起止两端构成反义。"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "淵源",
      "流派",
      "末流",
      "源流"
    ],
    "correct_answer": "末流",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某一事業或行動的開創者或最早的做法。",
        "explanation": "先河喻事業之開創與起源，末流指傳統之末端與衰落，二者在事物發展的起止兩端構成反義。"
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
      "text": "她开创了帮助同学的先河。",
      "is_correct": true
    },
    {
      "text": "她开创帮助同学的先河着。",
      "is_correct": false
    },
    {
      "text": "她开创了帮助同学的一条先河。",
      "is_correct": false
    },
    {
      "text": "先河她开创了帮助同学的。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“先河”是抽象名词，不能用具体名词的量词“条”。 体标选用错误：“先河”是名词，不能直接加动态助词“着”表示动作持续。 语序错误：宾语“先河”被错误地提前至句首，破坏了正常的“主谓宾”语序。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "她開創了幫助同學的先河。",
        "is_correct": true
      },
      {
        "text": "她開創幫助同學的先河著。",
        "is_correct": false
      },
      {
        "text": "她開創了幫助同學的一條先河。",
        "is_correct": false
      },
      {
        "text": "先河她開創了幫助同學的。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“先河”是抽象名詞，不能用具體名詞的量詞“條”。 體標選用錯誤：“先河”是名詞，不能直接加動態助詞“著”表示動作持續。 語序錯誤：賓語“先河”被錯誤地提前至句首，破壞了正常的“主謂賓”語序。",
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
    "末流",
    "肇始",
    "滥觞",
    "发端"
  ],
  "correct_answer": "末流",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某一事业或行动的开创者或最早的做法。",
      "explanation": "反义：先河喻事物的开创与起源，末流喻事物的衰落与末端，二者构成反义关系。"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "末流",
      "肇始",
      "濫觴",
      "發端"
    ],
    "correct_answer": "末流",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某一事業或行動的開創者或最早的做法。",
        "explanation": "反義：先河喻事物的開創與起源，末流喻事物的衰落與末端，二者構成反義關係。"
      }
    }
  }
}
```

#### Pack B
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "我们把他的做法看作先河。",
      "is_correct": true
    },
    {
      "text": "他开创了一条班级活动的先河。",
      "is_correct": false,
      "error_description": "“先河”是抽象名词，比喻某种风气或做法的开端，不能与具体事物的量词“一条”搭配，此处不需要加量词，或可改用“一种”。"
    },
    {
      "text": "他开创了班级活动的先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "我們把他的做法看作先河。",
        "is_correct": true
      },
      {
        "text": "他開創了一條班級活動的先河。",
        "is_correct": false,
        "error_description": "“先河”是抽象名詞，比喻某種風氣或做法的開端，不能與具體事物的量詞“一條”搭配，此處不需要加量詞，或可改用“一種”。"
      },
      {
        "text": "他開創了班級活動的先河。",
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
      "text": "没人想过要开创这个先河。",
      "is_correct": true
    },
    {
      "text": "她开创了帮助同学的先河昨天。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，时间状语通常放在主语之后、谓语动词之前，不能放在句末。应将“昨天”放在“开创”之前。"
    },
    {
      "text": "她开创了帮助同学的先河。",
      "is_correct": true
    },
    {
      "text": "他的做法堪称社交先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "沒人想過要開創這個先河。",
        "is_correct": true
      },
      {
        "text": "她開創了幫助同學的先河昨天。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，時間狀語通常放在主語之後、謂語動詞之前，不能放在句末。應將“昨天”放在“開創”之前。"
      },
      {
        "text": "她開創了幫助同學的先河。",
        "is_correct": true
      },
      {
        "text": "他的做法堪稱社交先河。",
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
      "text": "他的作业量庞大得很多。",
      "is_correct": false
    },
    {
      "text": "他的作业量非常庞大。",
      "is_correct": true
    },
    {
      "text": "非常他的作业量庞大。",
      "is_correct": false
    },
    {
      "text": "他的作业量非常庞大了。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：'庞大'是表示性质的状态形容词，通常不受动态助词'了'的修饰，此处加'了'破坏了状态形容词的语法特征。 语序错误：程度副词'非常'必须放在形容词'庞大'之前作状语，不能放在主语'他的作业量'之前，破坏了正常的修饰语序。 方向/结果补语误用：'庞大'本身已包含'大'的语义，后面不能再用'得很多'来补充说明，造成语义重复和补语结构误用。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "他的作業量龐大得很多。",
        "is_correct": false
      },
      {
        "text": "他的作業量非常龐大。",
        "is_correct": true
      },
      {
        "text": "非常他的作業量龐大。",
        "is_correct": false
      },
      {
        "text": "他的作業量非常龐大了。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：'龐大'是表示性質的狀態形容詞，通常不受動態助詞'了'的修飾，此處加'了'破壞了狀態形容詞的語法特徵。 語序錯誤：程度副詞'非常'必須放在形容詞'龐大'之前作狀語，不能放在主語'他的作業量'之前，破壞了正常的修飾語序。 方向/結果補語誤用：'龐大'本身已包含'大'的語義，後面不能再用'得很多'來補充說明，造成語義重複和補語結構誤用。",
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
    "巨大",
    "粗大",
    "宏伟",
    "微小"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大。",
      "explanation": "反义关系：「微小」形容体积、规模等非常小，与「庞大」形容非常大构成反义。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "巨大",
      "粗大",
      "宏偉",
      "微小"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大。",
        "explanation": "反義關係：「微小」形容體積、規模等非常小，與「龐大」形容非常大構成反義。"
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
      "text": "很庞大变得他的身躯。",
      "is_correct": false
    },
    {
      "text": "他的身躯变得很庞大。",
      "is_correct": true
    },
    {
      "text": "他的身躯庞大了很多。",
      "is_correct": false
    },
    {
      "text": "他的身躯庞大上去了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“庞大”表示状态，通常不直接加动态助词“了”来表示变化，应使用“变得庞大”或“庞大起来”。 语序错误。程度副词“很”和动词“变得”的位置颠倒，且主语“他的身躯”应放在句首，正确语序为“他的身躯变得很庞大”。 结果补语误用。“庞大”作为形容词，不能直接带趋向补语“上去”，表示状态变化应使用“变得庞大起来”或“庞大起来”。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "很龐大變得他的身軀。",
        "is_correct": false
      },
      {
        "text": "他的身軀變得很龐大。",
        "is_correct": true
      },
      {
        "text": "他的身軀龐大了很多。",
        "is_correct": false
      },
      {
        "text": "他的身軀龐大上去了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“龐大”表示狀態，通常不直接加動態助詞“了”來表示變化，應使用“變得龐大”或“龐大起來”。 語序錯誤。程度副詞“很”和動詞“變得”的位置顛倒，且主語“他的身軀”應放在句首，正確語序為“他的身軀變得很龐大”。 結果補語誤用。“龐大”作為形容詞，不能直接帶趨向補語“上去”，表示狀態變化應使用“變得龐大起來”或“龐大起來”。",
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
    "宏伟",
    "巨大",
    "微弱",
    "微小"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大。",
      "explanation": "反义项：形容体积、规模等非常小，与“庞大”构成反义关系。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "宏偉",
      "巨大",
      "微弱",
      "微小"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大。",
        "explanation": "反義項：形容體積、規模等非常小，與“龐大”構成反義關係。"
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
      "text": "他的身躯非常庞大，像一座小山。",
      "is_correct": true
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    },
    {
      "text": "庞大的这个家族聚会让我很开心。",
      "is_correct": false,
      "error_description": "指示代词“这个”应该放在形容词“庞大”的前面，正确的定语语序是“这个庞大的家族聚会”。"
    },
    {
      "text": "这个庞大的家族聚会让我很开心。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的身軀非常龐大，像一座小山。",
        "is_correct": true
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
        "is_correct": true
      },
      {
        "text": "龐大的這個家族聚會讓我很開心。",
        "is_correct": false,
        "error_description": "指示代詞“這個”應該放在形容詞“龐大”的前面，正確的定語語序是“這個龐大的家族聚會”。"
      },
      {
        "text": "這個龐大的家族聚會讓我很開心。",
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
      "text": "他的身躯变得很庞大。",
      "is_correct": true
    },
    {
      "text": "他的胃口很庞大，一顿能吃三碗饭。",
      "is_correct": true
    },
    {
      "text": "她花了很多钱买庞大的家具。",
      "is_correct": true
    },
    {
      "text": "这个学校的规模庞大十分。",
      "is_correct": false,
      "error_description": "程度副词位置错误。‘十分’作为程度副词，应该放在形容词‘庞大’的前面作状语，不能放在形容词后面。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的身軀變得很龐大。",
        "is_correct": true
      },
      {
        "text": "他的胃口很龐大，一頓能吃三碗飯。",
        "is_correct": true
      },
      {
        "text": "她花了很多錢買龐大的傢俱。",
        "is_correct": true
      },
      {
        "text": "這個學校的規模龐大十分。",
        "is_correct": false,
        "error_description": "程度副詞位置錯誤。‘十分’作為程度副詞，應該放在形容詞‘龐大’的前面作狀語，不能放在形容詞後面。"
      }
    ]
  }
}
```

---

## sense 10119, level 3

#### Pack A
### Level 3 (sense 10119, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "技术进步是好事，但如果管理不好，也可能带来新的___问题。",
  "original_sentence": "技术进步是好事，但如果管理不好，也可能带来新的社会问题。",
  "correct_answer": "社会",
  "options": [
    "私人",
    "历史",
    "生理",
    "社会"
  ],
  "explanation": "正确选项。“社会问题”指与社会整体运行、公共秩序相关的宏观问题，符合技术进步带来的广泛影响。",
  "distractor_tags": {},
  "word_definition": "指由共同利益、文化或制度联系起来的人群整体。",
  "target_word": "社会",
  "hant": {
    "sentence_with_blank": "技術進步是好事，但如果管理不好，也可能帶來新的___問題。",
    "original_sentence": "技術進步是好事，但如果管理不好，也可能帶來新的社會問題。",
    "correct_answer": "社會",
    "options": [
      "私人",
      "歷史",
      "生理",
      "社會"
    ],
    "explanation": "正確選項。“社會問題”指與社會整體執行、公共秩序相關的宏觀問題，符合技術進步帶來的廣泛影響。",
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
