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
    "印刷",
    "雕刻",
    "排版",
    "书写"
  ],
  "explanation": "正确。原句指宋代毕昇首创泥活字，开启了可重复排列文字和图像的技术先河。",
  "distractor_tags": {},
  "word_definition": "把文字和图片按规则排好，方便阅读。",
  "target_word": "排版",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複___的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "排版",
    "options": [
      "印刷",
      "雕刻",
      "排版",
      "書寫"
    ],
    "explanation": "正確。原句指宋代畢昇首創泥活字，開啟了可重複排列文字和影像的技術先河。",
    "distractor_tags": {},
    "word_definition": "把文字和圖片按規則排好，方便閱讀。",
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
      "text": "请把这篇文章排版一下着。",
      "is_correct": false
    },
    {
      "text": "请把这篇文章排版出来漂亮。",
      "is_correct": false
    },
    {
      "text": "排版请把这篇文章一下。",
      "is_correct": false
    },
    {
      "text": "请把这篇文章排版一下。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误。'一下'表示短时尝试，'着'表示动作持续，两者不能连用。应删去'着'或改为'排着版'。 语序错误。'排版'是及物动词，宾语'这篇文章'应紧跟在动词之后，动量补语'一下'应放在宾语之后。 方向/结果补语误用。'出来'表示从无到有，不能直接接形容词'漂亮'作状态补语。应改为'排版得漂亮'或'排版出漂亮的效果'。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "請把這篇文章排版一下著。",
        "is_correct": false
      },
      {
        "text": "請把這篇文章排版出來漂亮。",
        "is_correct": false
      },
      {
        "text": "排版請把這篇文章一下。",
        "is_correct": false
      },
      {
        "text": "請把這篇文章排版一下。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤。'一下'表示短時嘗試，'著'表示動作持續，兩者不能連用。應刪去'著'或改為'排著版'。 語序錯誤。'排版'是及物動詞，賓語'這篇文章'應緊跟在動詞之後，動量補語'一下'應放在賓語之後。 方向/結果補語誤用。'出來'表示從無到有，不能直接接形容詞'漂亮'作狀態補語。應改為'排版得漂亮'或'排版出漂亮的效果'。",
    "target_word": "排版"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "打乱",
    "印刷",
    "校对",
    "编辑"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字和图片按规则排好，方便阅读。",
      "explanation": "反义：排版是按规则整理，打乱是破坏原有顺序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "打亂",
      "印刷",
      "校對",
      "編輯"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字和圖片按規則排好，方便閱讀。",
        "explanation": "反義：排版是按規則整理，打亂是破壞原有順序"
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
      "text": "排版一件有趣的事是。",
      "is_correct": false
    },
    {
      "text": "排版是一件有趣的事。",
      "is_correct": true
    },
    {
      "text": "排版一件有趣的事。",
      "is_correct": false
    },
    {
      "text": "排版着是一件有趣的事。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。动态助词“着”不能放在动词和“是”之间，此处表示一般事实，应去掉“着”。 语序错误。判断动词“是”及其宾语应紧跟在主语之后，不能放在句末。 配价错误。动词“排版”是动作动词，不能直接带名词性短语作宾语，缺少判断动词“是”。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "排版一件有趣的事是。",
        "is_correct": false
      },
      {
        "text": "排版是一件有趣的事。",
        "is_correct": true
      },
      {
        "text": "排版一件有趣的事。",
        "is_correct": false
      },
      {
        "text": "排版著是一件有趣的事。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。動態助詞“著”不能放在動詞和“是”之間，此處表示一般事實，應去掉“著”。 語序錯誤。判斷動詞“是”及其賓語應緊跟在主語之後，不能放在句末。 配價錯誤。動詞“排版”是動作動詞，不能直接帶名詞性短語作賓語，缺少判斷動詞“是”。",
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
    "校对",
    "打乱",
    "编辑",
    "印刷"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字和图片按规则排好，方便阅读。",
      "explanation": "反义：排版是按规则整理有序，打乱是使有序变为无序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "校對",
      "打亂",
      "編輯",
      "印刷"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字和圖片按規則排好，方便閱讀。",
        "explanation": "反義：排版是按規則整理有序，打亂是使有序變為無序"
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
      "text": "他正在电脑前认真排版。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "他排版着正在电脑前认真。",
      "is_correct": false,
      "error_description": "语序与体标错误。表示动作正在进行的副词“正在”和处所状语“在电脑前”应放在动词“排版”及体标记“着”之前。"
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他正在電腦前認真排版。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "他排版著正在電腦前認真。",
        "is_correct": false,
        "error_description": "語序與體標錯誤。表示動作正在進行的副詞“正在”和處所狀語“在電腦前”應放在動詞“排版”及體標記“著”之前。"
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
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
      "text": "他排版了明天的校报。",
      "is_correct": false,
      "error_description": "体标选用错误。'着'表示动作正在进行或状态的持续，而'了'表示动作已完成。'明天'是将来的时间，校报还未排版，因此不能用表示完成的'了'，应使用表示持续或进行的'着'（或改为'正在排版'）。"
    },
    {
      "text": "排版是一件有趣的事。",
      "is_correct": true
    },
    {
      "text": "他排版着明天的校报。",
      "is_correct": true
    },
    {
      "text": "排版需要很多耐心。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他排版了明天的校報。",
        "is_correct": false,
        "error_description": "體標選用錯誤。'著'表示動作正在進行或狀態的持續，而'了'表示動作已完成。'明天'是將來的時間，校報還未排版，因此不能用表示完成的'了'，應使用表示持續或進行的'著'（或改為'正在排版'）。"
      },
      {
        "text": "排版是一件有趣的事。",
        "is_correct": true
      },
      {
        "text": "他排版著明天的校報。",
        "is_correct": true
      },
      {
        "text": "排版需要很多耐心。",
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "把这种游戏老师引入了课堂，开了先河。",
      "is_correct": false
    },
    {
      "text": "老师把这种游戏引入了课堂，开着了先河。",
      "is_correct": false
    },
    {
      "text": "老师把这种游戏引入了课堂，开了先河。",
      "is_correct": true
    },
    {
      "text": "老师把这种游戏引入了课堂，开了一个先河。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'先河'是抽象名词，比喻开创的做法，不能用个体量词'一个'来修饰，通常搭配'开……先河'或'首开先河'。 体标位置错误。'开先河'是一个动宾结构的固定搭配，表示完成某种开创，动态助词'了'应放在动词'开'之后、宾语'先河'之前，不能放在'开'和'着'之后。 语序错误。'把'字句中，主语'老师'必须放在'把'字之前，原句将主语放在了'把'字和宾语之后，破坏了基本的句法结构。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "把這種遊戲老師引入了課堂，開了先河。",
        "is_correct": false
      },
      {
        "text": "老師把這種遊戲引入了課堂，開著了先河。",
        "is_correct": false
      },
      {
        "text": "老師把這種遊戲引入了課堂，開了先河。",
        "is_correct": true
      },
      {
        "text": "老師把這種遊戲引入了課堂，開了一個先河。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'先河'是抽象名詞，比喻開創的做法，不能用個體量詞'一個'來修飾，通常搭配'開……先河'或'首開先河'。 體標位置錯誤。'開先河'是一個動賓結構的固定搭配，表示完成某種開創，動態助詞'了'應放在動詞'開'之後、賓語'先河'之前，不能放在'開'和'著'之後。 語序錯誤。'把'字句中，主語'老師'必須放在'把'字之前，原句將主語放在了'把'字和賓語之後，破壞了基本的句法結構。",
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
    "尾声",
    "开端",
    "陈规",
    "末节"
  ],
  "correct_answer": "尾声",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某一事业或行动的开创者或最早的做法。",
      "explanation": "反义关系：指事情结束的阶段，与表开端的‘先河’构成始与终的反义"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "尾聲",
      "開端",
      "陳規",
      "末節"
    ],
    "correct_answer": "尾聲",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某一事業或行動的開創者或最早的做法。",
        "explanation": "反義關係：指事情結束的階段，與表開端的‘先河’構成始與終的反義"
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
      "text": "这个活动开创了着交友的先河。",
      "is_correct": false
    },
    {
      "text": "这个活动开创了一个交友的先河。",
      "is_correct": false
    },
    {
      "text": "交友的先河被这个活动开创了。",
      "is_correct": false
    },
    {
      "text": "这个活动开创了交友的新先河。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：'先河'作为抽象名词，通常不与个体量词'一个'搭配，应直接说'开创了交友的先河'。 体标位置错误：'开创'是瞬间完成动词，不能加表示持续的体标记'着'，应使用'了'或直接使用动词。 语序错误：'先河'作为受事宾语，在主动句中应置于动词后，使用被动句破坏了自然的'主题—评论'结构。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "這個活動開創了著交友的先河。",
        "is_correct": false
      },
      {
        "text": "這個活動開創了一個交友的先河。",
        "is_correct": false
      },
      {
        "text": "交友的先河被這個活動開創了。",
        "is_correct": false
      },
      {
        "text": "這個活動開創了交友的新先河。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：'先河'作為抽象名詞，通常不與個體量詞'一個'搭配，應直接說'開創了交友的先河'。 體標位置錯誤：'開創'是瞬間完成動詞，不能加表示持續的體標記'著'，應使用'了'或直接使用動詞。 語序錯誤：'先河'作為受事賓語，在主動句中應置於動詞後，使用被動句破壞了自然的'主題—評論'結構。",
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
    "惯例",
    "滥觞",
    "末流",
    "创举"
  ],
  "correct_answer": "末流",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某一事业或行动的开创者或最早的做法。",
      "explanation": "反义：先河指事物的开创与起源，末流指事物发展到后期的衰变形态，二者构成起源与末端的反义关系"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "antonym",
    "options": [
      "慣例",
      "濫觴",
      "末流",
      "創舉"
    ],
    "correct_answer": "末流",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某一事業或行動的開創者或最早的做法。",
        "explanation": "反義：先河指事物的開創與起源，末流指事物發展到後期的衰變形態，二者構成起源與末端的反義關係"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这次比赛开创了学校社交的新先河。",
      "is_correct": true
    },
    {
      "text": "他的新想法开创了班级活动的先河。",
      "is_correct": true
    },
    {
      "text": "他的新想法开创先河了班级活动。",
      "is_correct": false,
      "error_description": "语序错误。动态助词“了”应放在动词“开创”之后，宾语“班级活动的先河”之前，不能放在动宾短语的中间。"
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這次比賽開創了學校社交的新先河。",
        "is_correct": true
      },
      {
        "text": "他的新想法開創了班級活動的先河。",
        "is_correct": true
      },
      {
        "text": "他的新想法開創先河了班級活動。",
        "is_correct": false,
        "error_description": "語序錯誤。動態助詞“了”應放在動詞“開創”之後，賓語“班級活動的先河”之前，不能放在動賓短語的中間。"
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
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
      "text": "他开创了环保社团的先河。",
      "is_correct": true
    },
    {
      "text": "他开创了先河在环保社团方面。",
      "is_correct": false,
      "error_description": "语序错误。表示范围或方面的介词短语（如“在……方面”）通常应放在动词之前作状语，不能放在宾语之后。"
    },
    {
      "text": "她的演讲开创了表达观点的先河。",
      "is_correct": true
    },
    {
      "text": "这个活动开创了交友的新先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他開創了環保社團的先河。",
        "is_correct": true
      },
      {
        "text": "他開創了先河在環保社團方面。",
        "is_correct": false,
        "error_description": "語序錯誤。表示範圍或方面的介詞短語（如“在……方面”）通常應放在動詞之前作狀語，不能放在賓語之後。"
      },
      {
        "text": "她的演講開創了表達觀點的先河。",
        "is_correct": true
      },
      {
        "text": "這個活動開創了交友的新先河。",
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
      "text": "这个庞大的机器看着很吓人了。",
      "is_correct": false
    },
    {
      "text": "这个庞大的机器看着很吓人。",
      "is_correct": true
    },
    {
      "text": "看着很庞大这个机器。",
      "is_correct": false
    },
    {
      "text": "这个机器看着很庞大起来。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：形容词“庞大”表示一种静态的属性，后面不能直接加动态助词“了”来表示状态的变化或完成。 语序错误：汉语中形容词作谓语时，通常主语在前，谓语在后。将主语“这个机器”放在句末破坏了基本的“主—谓”语序。 方向补语误用：“起来”通常接在动词或形容词后表示动作或状态的开始，但“庞大”是表示既定客观属性的形容词，不能与“起来”搭配表示状态的起始。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "這個龐大的機器看著很嚇人了。",
        "is_correct": false
      },
      {
        "text": "這個龐大的機器看著很嚇人。",
        "is_correct": true
      },
      {
        "text": "看著很龐大這個機器。",
        "is_correct": false
      },
      {
        "text": "這個機器看著很龐大起來。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：形容詞“龐大”表示一種靜態的屬性，後面不能直接加動態助詞“了”來表示狀態的變化或完成。 語序錯誤：漢語中形容詞作謂語時，通常主語在前，謂語在後。將主語“這個機器”放在句末破壞了基本的“主—謂”語序。 方向補語誤用：“起來”通常接在動詞或形容詞後表示動作或狀態的開始，但“龐大”是表示既定客觀屬性的形容詞，不能與“起來”搭配表示狀態的起始。",
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
    "微小",
    "沉重",
    "复杂"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "反义项：形容体积、规模或数量等非常小，与目标词构成反义关系。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "巨大",
      "微小",
      "沉重",
      "複雜"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "反義項：形容體積、規模或數量等非常小，與目標詞構成反義關係。"
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
      "text": "我觉得这个计划太庞大了。",
      "is_correct": true
    },
    {
      "text": "我觉得这个计划庞大了太。",
      "is_correct": false
    },
    {
      "text": "我觉得这个计划太庞大着。",
      "is_correct": false
    },
    {
      "text": "我觉得这个计划太庞大了得。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：形容词'庞大'后面不能直接加结构助词'得'来引出补语，这种语法结构在此处不成立。 语序错误：程度副词'太'必须放在形容词'庞大'的前面进行修饰，不能放在后面。 体标错误：动态助词'着'表示动作或状态的持续，不能用在表示性质评价的形容词'庞大'之后。",
  "target_word": "庞大",
  "hant": {
    "sentences": [
      {
        "text": "我覺得這個計劃太龐大了。",
        "is_correct": true
      },
      {
        "text": "我覺得這個計劃龐大了太。",
        "is_correct": false
      },
      {
        "text": "我覺得這個計劃太龐大著。",
        "is_correct": false
      },
      {
        "text": "我覺得這個計劃太龐大了得。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：形容詞'龐大'後面不能直接加結構助詞'得'來引出補語，這種語法結構在此處不成立。 語序錯誤：程度副詞'太'必須放在形容詞'龐大'的前面進行修飾，不能放在後面。 體標錯誤：動態助詞'著'表示動作或狀態的持續，不能用在表示性質評價的形容詞'龐大'之後。",
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
    "复杂",
    "微小",
    "臃肿",
    "巨大"
  ],
  "correct_answer": "微小",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容体积、规模、数量等非常大，超过一般水平。",
      "explanation": "形容体积、规模或数量等非常小，与目标词“庞大”构成反义关系。"
    }
  },
  "hant": {
    "word": "龐大",
    "relation": "antonym",
    "options": [
      "複雜",
      "微小",
      "臃腫",
      "巨大"
    ],
    "correct_answer": "微小",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容體積、規模、數量等非常大，超過一般水平。",
        "explanation": "形容體積、規模或數量等非常小，與目標詞“龐大”構成反義關係。"
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
      "text": "他把庞大的行李箱搬上了车。",
      "is_correct": true
    },
    {
      "text": "他把庞大的行李箱搬了上车。",
      "is_correct": false,
      "error_description": "“了”作为动态助词，应紧跟在动词“搬”之后，并与趋向补语“上”结合为“上了”，不能放在动词和补语之间。"
    },
    {
      "text": "学校组织了庞大的队伍去春游。",
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
        "text": "他把龐大的行李箱搬上了車。",
        "is_correct": true
      },
      {
        "text": "他把龐大的行李箱搬了上車。",
        "is_correct": false,
        "error_description": "“了”作為動態助詞，應緊跟在動詞“搬”之後，並與趨向補語“上”結合為“上了”，不能放在動詞和補語之間。"
      },
      {
        "text": "學校組織了龐大的隊伍去春遊。",
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我觉得这个计划太庞大了。",
      "is_correct": true
    },
    {
      "text": "她有一件庞大的梦想。",
      "is_correct": false,
      "error_description": "量词使用错误。修饰抽象名词“梦想”时，应使用量词“个”，而不能使用用于具体物品的量词“件”。"
    },
    {
      "text": "她有一个庞大的梦想。",
      "is_correct": true
    },
    {
      "text": "庞大的恐龙曾经生活在地球上。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我覺得這個計劃太龐大了。",
        "is_correct": true
      },
      {
        "text": "她有一件龐大的夢想。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。修飾抽象名詞“夢想”時，應使用量詞“個”，而不能使用用於具體物品的量詞“件”。"
      },
      {
        "text": "她有一個龐大的夢想。",
        "is_correct": true
      },
      {
        "text": "龐大的恐龍曾經生活在地球上。",
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种对水资源的社会调控机制，本质上是一种非市场化的治理模式，其合法性源于共同体内部的文化共识，而非现代法律条文。",
      "is_correct": true
    },
    {
      "text": "这种对调控机制的社会水资源，本质上是一种非市场化的治理模式。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的一只社会调控机制，本质上是一种非市场化的治理模式。",
      "is_correct": false
    },
    {
      "text": "这种对水资源的社会了调控机制，本质上是一种非市场化的治理模式。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'社会'是抽象名词，不能用个体量词'一只'来修饰，此处属于量词误用。 体标位置错误。'社会'在此处作定语修饰'调控机制'，不能直接加动态助词'了'表示动作完成。 语序错误。'社会'应修饰'调控机制'，原句语序错乱导致'社会水资源'语义不通，破坏了原有的偏正结构。",
  "target_word": "社会",
  "hant": {
    "sentences": [
      {
        "text": "這種對水資源的社會調控機制，本質上是一種非市場化的治理模式，其合法性源於共同體內部的文化共識，而非現代法律條文。",
        "is_correct": true
      },
      {
        "text": "這種對調控機制的社會水資源，本質上是一種非市場化的治理模式。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的一隻社會調控機制，本質上是一種非市場化的治理模式。",
        "is_correct": false
      },
      {
        "text": "這種對水資源的社會了調控機制，本質上是一種非市場化的治理模式。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'社會'是抽象名詞，不能用個體量詞'一隻'來修飾，此處屬於量詞誤用。 體標位置錯誤。'社會'在此處作定語修飾'調控機制'，不能直接加動態助詞'了'表示動作完成。 語序錯誤。'社會'應修飾'調控機制'，原句語序錯亂導致'社會水資源'語義不通，破壞了原有的偏正結構。",
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
    "群体",
    "国家",
    "个人"
  ],
  "correct_answer": "个人",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指由共同利益或文化联系起来的人群整体。",
      "explanation": "反义关系：社会指人群整体，个人指单独的个体，二者构成集体与个体的对立"
    }
  },
  "hant": {
    "word": "社會",
    "relation": "antonym",
    "options": [
      "集體",
      "群體",
      "國家",
      "個人"
    ],
    "correct_answer": "個人",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指由共同利益或文化聯絡起來的人群整體。",
        "explanation": "反義關係：社會指人群整體，個人指單獨的個體，二者構成集體與個體的對立"
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
      "text": "每一次突破都非孤立发明，而是社会需求与基础科学、工程实践共振的产物。",
      "is_correct": false
    },
    {
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与社会需求共振的产物。",
      "is_correct": true
    },
    {
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与社会需求了共振的产物。",
      "is_correct": false
    },
    {
      "text": "每一次突破都非孤立发明，而是基础科学、工程实践与一个社会需求共振的产物。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'社会需求'作为抽象概念，通常不加个体量词'一个'，直接使用'社会需求'即可。 体标位置错误：动态助词'了'应放在动词'共振'之后（即'共振了'），或放在句末，不能直接插在名词'社会需求'和动词'共振'之间。 语序错误：原句遵循从微观到宏观、从具体到抽象的逻辑顺序（基础科学->工程实践->社会需求），调换后破坏了原有的递进语势和逻辑连贯性。",
  "target_word": "社会",
  "hant": {
    "sentences": [
      {
        "text": "每一次突破都非孤立發明，而是社會需求與基礎科學、工程實踐共振的產物。",
        "is_correct": false
      },
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與社會需求共振的產物。",
        "is_correct": true
      },
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與社會需求了共振的產物。",
        "is_correct": false
      },
      {
        "text": "每一次突破都非孤立發明，而是基礎科學、工程實踐與一個社會需求共振的產物。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'社會需求'作為抽象概念，通常不加個體量詞'一個'，直接使用'社會需求'即可。 體標位置錯誤：動態助詞'了'應放在動詞'共振'之後（即'共振了'），或放在句末，不能直接插在名詞'社會需求'和動詞'共振'之間。 語序錯誤：原句遵循從微觀到宏觀、從具體到抽象的邏輯順序（基礎科學->工程實踐->社會需求），調換後破壞了原有的遞進語勢和邏輯連貫性。",
    "target_word": "社會"
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
      "text": "这表明，基层环保实践正逐步演进为公民参与社会治理的有效路径。",
      "is_correct": true
    },
    {
      "text": "专家提醒，必须提前准备社会，否则贫富差距可能会变得更大。",
      "is_correct": false,
      "error_description": "语序错误。'社会'是'准备'的主语，而不是宾语。将'社会'放在'准备'之后会导致动宾搭配不当，应将其移至句首或'必须'之前作主语。"
    },
    {
      "text": "这种基于绩效的认可机制，与现实社会的成就导向形成镜像。",
      "is_correct": true
    },
    {
      "text": "这些水利系统背后所蕴藏的，是一整套关于水权、劳动组织与社会协作的文化制度。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這表明，基層環保實踐正逐步演進為公民參與社會治理的有效路徑。",
        "is_correct": true
      },
      {
        "text": "專家提醒，必須提前準備社會，否則貧富差距可能會變得更大。",
        "is_correct": false,
        "error_description": "語序錯誤。'社會'是'準備'的主語，而不是賓語。將'社會'放在'準備'之後會導致動賓搭配不當，應將其移至句首或'必須'之前作主語。"
      },
      {
        "text": "這種基於績效的認可機制，與現實社會的成就導向形成映象。",
        "is_correct": true
      },
      {
        "text": "這些水利系統背後所蘊藏的，是一整套關於水權、勞動組織與社會協作的文化制度。",
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
      "text": "未来可能会有更严格的法律出台，推动向更可持续的方向社会发展。",
      "is_correct": false,
      "error_description": "语序错误。'向更可持续的方向' 是介词短语作状语，修饰动词 '发展'，应紧跟在动词之前，或者放在宾语 '社会' 之后、动词 '发展' 之前，即 '推动社会向更可持续的方向发展'。"
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
        "text": "未來可能會有更嚴格的法律出臺，推動向更可持續的方向社會發展。",
        "is_correct": false,
        "error_description": "語序錯誤。'向更可持續的方向' 是介詞短語作狀語，修飾動詞 '發展'，應緊跟在動詞之前，或者放在賓語 '社會' 之後、動詞 '發展' 之前，即 '推動社會向更可持續的方向發展'。"
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
      "text": "你真正理解了他的意思吗？",
      "is_correct": false
    },
    {
      "text": "真正你理解他的意思吗？",
      "is_correct": false
    },
    {
      "text": "你真正理解他的意思吗？",
      "is_correct": true
    },
    {
      "text": "你真正理解他的意思过吗？",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：副词“真正”修饰心理动词“理解”时，通常表示一种持续的状态或能力，不应与表示完成的动态助词“了”连用，去掉“了”更自然。 语序错误：副词“真正”作为状语，必须放在主语“你”之后、谓语动词“理解”之前，不能放在主语前面。 体标选用错误：经验体标记“过”表示过去的经历，而“理解”在此处询问的是当前的认知状态，使用“过”会导致语义和语用上的不自然。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "你真正理解了他的意思嗎？",
        "is_correct": false
      },
      {
        "text": "真正你理解他的意思嗎？",
        "is_correct": false
      },
      {
        "text": "你真正理解他的意思嗎？",
        "is_correct": true
      },
      {
        "text": "你真正理解他的意思過嗎？",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：副詞“真正”修飾心理動詞“理解”時，通常表示一種持續的狀態或能力，不應與表示完成的動態助詞“了”連用，去掉“了”更自然。 語序錯誤：副詞“真正”作為狀語，必須放在主語“你”之後、謂語動詞“理解”之前，不能放在主語前面。 體標選用錯誤：經驗體標記“過”表示過去的經歷，而“理解”在此處詢問的是當前的認知狀態，使用“過”會導致語義和語用上的不自然。",
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
    "假装",
    "偶尔",
    "确实",
    "大概"
  ],
  "correct_answer": "假装",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（常用来强调所说的话是真实的）。",
      "explanation": "反义项：表示故意做出某种姿态，与‘真实地、确实地’构成反义。"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "假裝",
      "偶爾",
      "確實",
      "大概"
    ],
    "correct_answer": "假裝",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（常用來強調所說的話是真實的）。",
        "explanation": "反義項：表示故意做出某種姿態，與‘真實地、確實地’構成反義。"
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
      "text": "大家真正享受了过假期。",
      "is_correct": false
    },
    {
      "text": "大家正真正着享受着假期。",
      "is_correct": false
    },
    {
      "text": "正大家真正享受着假期。",
      "is_correct": false
    },
    {
      "text": "大家正真正享受着假期。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：副词'真正'不能直接带动态助词'着'，'着'应紧跟在主要动词'享受'之后。 语序错误：时间/状态副词'正'应该放在主语'大家'之后、副词'真正'之前，不能放在句首。 体标选用错误：动态助词'了'和'过'不能连用，表示经历应单用'过'，即'享受过'。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "大家真正享受了過假期。",
        "is_correct": false
      },
      {
        "text": "大家正真正著享受著假期。",
        "is_correct": false
      },
      {
        "text": "正大家真正享受著假期。",
        "is_correct": false
      },
      {
        "text": "大家正真正享受著假期。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：副詞'真正'不能直接帶動態助詞'著'，'著'應緊跟在主要動詞'享受'之後。 語序錯誤：時間/狀態副詞'正'應該放在主語'大家'之後、副詞'真正'之前，不能放在句首。 體標選用錯誤：動態助詞'了'和'過'不能連用，表示經歷應單用'過'，即'享受過'。",
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
    "完全",
    "大概",
    "确实",
    "假装"
  ],
  "correct_answer": "假装",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（常用来强调所说的话是真实的）。",
      "explanation": "反义项：表示故意做出某种姿态，与“真实地、确实地”相对"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "完全",
      "大概",
      "確實",
      "假裝"
    ],
    "correct_answer": "假裝",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（常用來強調所說的話是真實的）。",
        "explanation": "反義項：表示故意做出某種姿態，與“真實地、確實地”相對"
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
