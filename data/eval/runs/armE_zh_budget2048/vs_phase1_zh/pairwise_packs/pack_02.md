# Pairwise review pack 02

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


## sense 10106, level 6

#### Pack A
### Level 6 (sense 10106, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "等那本故事书看毕完，他便将其还给了图书馆。",
      "is_correct": false
    },
    {
      "text": "等那本故事书看毕了，他便将其还给了图书馆。",
      "is_correct": false
    },
    {
      "text": "等那本故事书毕看，他便将其还给了图书馆。",
      "is_correct": false
    },
    {
      "text": "等那本故事书看毕，他便将其还给了图书馆。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：“毕”本身已包含“完成”的体貌意义，后面不能再加动态助词“了”，应直接说“看毕”。 语序错误：“毕”作为结果补语，必须放在动词“看”的后面，不能放在动词前面。 语义重复/补语误用：“毕”已表示完成，后面再加“完”造成语义重复，且不符合汉语补语的使用习惯。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "等那本故事書看畢完，他便將其還給了圖書館。",
        "is_correct": false
      },
      {
        "text": "等那本故事書看畢了，他便將其還給了圖書館。",
        "is_correct": false
      },
      {
        "text": "等那本故事書畢看，他便將其還給了圖書館。",
        "is_correct": false
      },
      {
        "text": "等那本故事書看畢，他便將其還給了圖書館。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：“畢”本身已包含“完成”的體貌意義，後面不能再加動態助詞“了”，應直接說“看畢”。 語序錯誤：“畢”作為結果補語，必須放在動詞“看”的後面，不能放在動詞前面。 語義重複/補語誤用：“畢”已表示完成，後面再加“完”造成語義重複，且不符合漢語補語的使用習慣。",
    "target_word": "畢"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "毕",
  "relation": "antonym",
  "options": [
    "行",
    "终",
    "延",
    "始"
  ],
  "correct_answer": "始",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "完成；结束。",
      "explanation": "表示动作或事件的开始，与目标词“完成、结束”义构成反义关系。"
    }
  },
  "hant": {
    "word": "畢",
    "relation": "antonym",
    "options": [
      "行",
      "終",
      "延",
      "始"
    ],
    "correct_answer": "始",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "完成；結束。",
        "explanation": "表示動作或事件的開始，與目標詞“完成、結束”義構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10106, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "仪式终于结束，主持人宣布毕礼了。",
      "is_correct": false
    },
    {
      "text": "仪式终于结束，主持人宣布礼毕着了。",
      "is_correct": false
    },
    {
      "text": "仪式终于结束，主持人宣布礼毕了。",
      "is_correct": true
    },
    {
      "text": "仪式终于结束，主持人宣布礼毕下去了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“毕”表示动作完成，是瞬间动词，不能与表示状态持续的体标记“着”连用。 语序错误。“礼毕”是固定的主谓倒装结构，意为“礼仪完成”，颠倒为“毕礼”不符合汉语表达习惯。 方向/结果补语误用。“下去”表示动作继续，与“毕”所表达的“结束、完成”语义相反，造成逻辑冲突。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "儀式終於結束，主持人宣佈畢禮了。",
        "is_correct": false
      },
      {
        "text": "儀式終於結束，主持人宣佈禮畢著了。",
        "is_correct": false
      },
      {
        "text": "儀式終於結束，主持人宣佈禮畢了。",
        "is_correct": true
      },
      {
        "text": "儀式終於結束，主持人宣佈禮畢下去了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“畢”表示動作完成，是瞬間動詞，不能與表示狀態持續的體標記“著”連用。 語序錯誤。“禮畢”是固定的主謂倒裝結構，意為“禮儀完成”，顛倒為“畢禮”不符合漢語表達習慣。 方向/結果補語誤用。“下去”表示動作繼續，與“畢”所表達的“結束、完成”語義相反，造成邏輯衝突。",
    "target_word": "畢"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "relation": "antonym",
  "options": [
    "进行",
    "持续",
    "筹备",
    "开始"
  ],
  "correct_answer": "开始",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "完成；结束。",
      "explanation": "表示动作或事件从头做起，与目标词'完成、结束'构成反义关系。"
    }
  },
  "hant": {
    "word": "畢",
    "relation": "antonym",
    "options": [
      "進行",
      "持續",
      "籌備",
      "開始"
    ],
    "correct_answer": "開始",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "完成；結束。",
        "explanation": "表示動作或事件從頭做起，與目標詞'完成、結束'構成反義關係。"
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
      "text": "仪式终于毕下去了，大家开始鼓掌。",
      "is_correct": false
    },
    {
      "text": "他把书看完，合上书本，心想终于读毕。",
      "is_correct": true
    },
    {
      "text": "他正在读毕那本精彩的小说。",
      "is_correct": false
    },
    {
      "text": "他把书看完，合上书本，心想终于毕读。",
      "is_correct": false
    }
  ],
  "explanation": "体标/体貌错误。“毕”表示动作完成，不能与表示进行时的“正在”连用。 方向/结果补语误用。“毕”表示动作的结束和完成，不能与表示动作延续的趋向补语“下去”搭配。 语序错误。“毕”作为结果补语应紧跟在动词“读”之后，不能放在动词之前。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "儀式終於畢下去了，大家開始鼓掌。",
        "is_correct": false
      },
      {
        "text": "他把書看完，合上書本，心想終於讀畢。",
        "is_correct": true
      },
      {
        "text": "他正在讀畢那本精彩的小說。",
        "is_correct": false
      },
      {
        "text": "他把書看完，合上書本，心想終於畢讀。",
        "is_correct": false
      }
    ],
    "explanation": "體標/體貌錯誤。“畢”表示動作完成，不能與表示進行時的“正在”連用。 方向/結果補語誤用。“畢”表示動作的結束和完成，不能與表示動作延續的趨向補語“下去”搭配。 語序錯誤。“畢”作為結果補語應緊跟在動詞“讀”之後，不能放在動詞之前。",
    "target_word": "畢"
  }
}
```

---

## sense 10106, level 7

#### Pack A
### Level 7 (sense 10106, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他长舒一口气，心想这事总算毕了。",
      "is_correct": true
    },
    {
      "text": "他花了数日时间，终于完成了这幅画作，心里觉得一切总算完毕。",
      "is_correct": true
    },
    {
      "text": "他长舒一口气，心想这事总算毕着。",
      "is_correct": false,
      "error_description": "表示动作已经完成，应该使用完成体标记“了”，而不是表示动作持续的“着”。"
    },
    {
      "text": "经过四年的寒窗苦读，他终于完成了所有的学业，顺利从这所知名大学毕业。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他長舒一口氣，心想這事總算畢了。",
        "is_correct": true
      },
      {
        "text": "他花了數日時間，終於完成了這幅畫作，心裡覺得一切總算完畢。",
        "is_correct": true
      },
      {
        "text": "他長舒一口氣，心想這事總算畢著。",
        "is_correct": false,
        "error_description": "表示動作已經完成，應該使用完成體標記“了”，而不是表示動作持續的“著”。"
      },
      {
        "text": "經過四年的寒窗苦讀，他終於完成了所有的學業，順利從這所知名大學畢業。",
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
      "text": "他把书看完，合上书本，心想终于读毕。",
      "is_correct": true
    },
    {
      "text": "他把事情做完，心里觉得这事毕已。",
      "is_correct": false,
      "error_description": "副词“已”表示“已经”，应放在动词“毕”之前作状语。句中“毕已”属于语序错误，颠倒了状语和中心动词的位置。"
    },
    {
      "text": "他把事情做完，心里觉得这事已毕。",
      "is_correct": true
    },
    {
      "text": "考试终于结束，这场大战总算已毕。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把書看完，合上書本，心想終於讀畢。",
        "is_correct": true
      },
      {
        "text": "他把事情做完，心裡覺得這事畢已。",
        "is_correct": false,
        "error_description": "副詞“已”表示“已經”，應放在動詞“畢”之前作狀語。句中“畢已”屬於語序錯誤，顛倒了狀語和中心動詞的位置。"
      },
      {
        "text": "他把事情做完，心裡覺得這事已畢。",
        "is_correct": true
      },
      {
        "text": "考試終於結束，這場大戰總算已畢。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10106, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他毕了今天的功课，便去看电视。",
      "is_correct": false,
      "error_description": "“毕”在此处不能直接带宾语。应将宾语“功课”提前作主语，或改用及物动词“完成”。"
    },
    {
      "text": "运动会各项赛事毕，大家便有序地回到了教室。",
      "is_correct": true
    },
    {
      "text": "这项历时三年的研究工程终于告毕，团队成员们纷纷庆祝。",
      "is_correct": true
    },
    {
      "text": "开学典礼礼毕，同学们便开心地回到教室。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他畢了今天的功課，便去看電視。",
        "is_correct": false,
        "error_description": "“畢”在此處不能直接帶賓語。應將賓語“功課”提前作主語，或改用及物動詞“完成”。"
      },
      {
        "text": "運動會各項賽事畢，大家便有序地回到了教室。",
        "is_correct": true
      },
      {
        "text": "這項歷時三年的研究工程終於告畢，團隊成員們紛紛慶祝。",
        "is_correct": true
      },
      {
        "text": "開學典禮禮畢，同學們便開心地回到教室。",
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
      "text": "他毕了演讲环节，台下便响起了热烈的掌声。",
      "is_correct": false,
      "error_description": "“毕”表示结束，通常不直接带宾语，不能用于“主语+毕+宾语”结构。应将宾语提前，改为“演讲环节毕”或“演讲完毕”。"
    },
    {
      "text": "比赛终场毕，队员们便互相拥抱庆祝。",
      "is_correct": true
    },
    {
      "text": "考试终场毕，他便长长地舒了一口气。",
      "is_correct": true
    },
    {
      "text": "演讲环节毕，台下便响起了热烈的掌声。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他畢了演講環節，臺下便響起了熱烈的掌聲。",
        "is_correct": false,
        "error_description": "“畢”表示結束，通常不直接帶賓語，不能用於“主語+畢+賓語”結構。應將賓語提前，改為“演講環節畢”或“演講完畢”。"
      },
      {
        "text": "比賽終場畢，隊員們便互相擁抱慶祝。",
        "is_correct": true
      },
      {
        "text": "考試終場畢，他便長長地舒了一口氣。",
        "is_correct": true
      },
      {
        "text": "演講環節畢，臺下便響起了熱烈的掌聲。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10107, level 3

#### Pack A
### Level 3 (sense 10107, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更___泥活字，开启了可重复排版的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "首创",
  "options": [
    "仿造",
    "首创",
    "普及",
    "沿用"
  ],
  "explanation": "正确。'首创'指最先创造，与后文'开启了……先河'的语境完美契合。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，做别人没做过的事。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更___泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "首創",
    "options": [
      "仿造",
      "首創",
      "普及",
      "沿用"
    ],
    "explanation": "正確。'首創'指最先創造，與後文'開啟了……先河'的語境完美契合。",
    "distractor_tags": {},
    "word_definition": "最先創造或發明，做別人沒做過的事。",
    "target_word": "首創"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我们把这看作大家的___。",
  "original_sentence": "我们把这看作大家的首创。",
  "correct_answer": "首创",
  "options": [
    "创造",
    "制造",
    "首创",
    "发现"
  ],
  "explanation": "正确。在此句中作名词，指代大家最先创造的事物或行为。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，做别人没做过的事。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "我們把這看作大家的___。",
    "original_sentence": "我們把這看作大家的首創。",
    "correct_answer": "首創",
    "options": [
      "創造",
      "製造",
      "首創",
      "發現"
    ],
    "explanation": "正確。在此句中作名詞，指代大家最先創造的事物或行為。",
    "distractor_tags": {},
    "word_definition": "最先創造或發明，做別人沒做過的事。",
    "target_word": "首創"
  }
}
```

#### Pack B
### Level 3 (sense 10107, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这是他们___的活动。",
  "original_sentence": "这是他们首创的活动。",
  "correct_answer": "首创",
  "options": [
    "首创",
    "解散",
    "复制",
    "捏造"
  ],
  "explanation": "正确。'首创'指最先创造，符合语境中强调该活动是他们第一次举办的创新之意。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，指做别人没有做过的事情。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "這是他們___的活動。",
    "original_sentence": "這是他們首創的活動。",
    "correct_answer": "首創",
    "options": [
      "首創",
      "解散",
      "複製",
      "捏造"
    ],
    "explanation": "正確。'首創'指最先創造，符合語境中強調該活動是他們第一次舉辦的創新之意。",
    "distractor_tags": {},
    "word_definition": "最先創造或發明，指做別人沒有做過的事情。",
    "target_word": "首創"
  }
}
```

---

## sense 10107, level 6

#### Pack A
### Level 6 (sense 10107, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这是她首创出去的独特生日庆祝法。",
      "is_correct": false
    },
    {
      "text": "这是她首创了独特生日庆祝法。",
      "is_correct": false
    },
    {
      "text": "这是她首创的独特生日庆祝法。",
      "is_correct": true
    },
    {
      "text": "这是她首创着的独特生日庆祝法。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：'首创'作为及物动词，其后应直接跟宾语'独特生日庆祝法'，句中多用了结构助词'了'导致'的'字结构被破坏，应改为'她首创的独特生日庆祝法'。 体标选用错误：'首创'表示一次性的完成动作（最先创造），不能使用表示动作持续或状态持续的动态助词'着'，应改为'首创的'。 方向补语误用：'首创'本身已包含'创造出新事物'的完整结果意义，不能与表示向外方向的趋向补语'出去'搭配，应直接使用'首创的'。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "這是她首創出去的獨特生日慶祝法。",
        "is_correct": false
      },
      {
        "text": "這是她首創了獨特生日慶祝法。",
        "is_correct": false
      },
      {
        "text": "這是她首創的獨特生日慶祝法。",
        "is_correct": true
      },
      {
        "text": "這是她首創著的獨特生日慶祝法。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：'首創'作為及物動詞，其後應直接跟賓語'獨特生日慶祝法'，句中多用了結構助詞'了'導致'的'字結構被破壞，應改為'她首創的獨特生日慶祝法'。 體標選用錯誤：'首創'表示一次性的完成動作（最先創造），不能使用表示動作持續或狀態持續的動態助詞'著'，應改為'首創的'。 方向補語誤用：'首創'本身已包含'創造出新事物'的完整結果意義，不能與表示向外方向的趨向補語'出去'搭配，應直接使用'首創的'。",
    "target_word": "首創"
  }
}
```

#### Pack B
### Level 6 (sense 10107, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们首创了昨天班级新规矩。",
      "is_correct": false
    },
    {
      "text": "我们首创出来班级新规矩。",
      "is_correct": false
    },
    {
      "text": "我们首创了班级新规矩。",
      "is_correct": true
    },
    {
      "text": "我们一直在首创班级新规矩。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“首创”是瞬间动词，表示动作已完成，不能与表示动作持续的“一直在”连用。 语序错误：时间状语“昨天”位置不当，应放在主语之后、动词之前，改为“我们昨天首创了班级新规矩”。 结果补语误用：“首创”本身已包含“创造”的结果义，不能再附加结果补语“出来”。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "我們首創了昨天班級新規矩。",
        "is_correct": false
      },
      {
        "text": "我們首創出來班級新規矩。",
        "is_correct": false
      },
      {
        "text": "我們首創了班級新規矩。",
        "is_correct": true
      },
      {
        "text": "我們一直在首創班級新規矩。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“首創”是瞬間動詞，表示動作已完成，不能與表示動作持續的“一直在”連用。 語序錯誤：時間狀語“昨天”位置不當，應放在主語之後、動詞之前，改為“我們昨天首創了班級新規矩”。 結果補語誤用：“首創”本身已包含“創造”的結果義，不能再附加結果補語“出來”。",
    "target_word": "首創"
  }
}
```

---

## sense 10107, level 7

#### Pack A
### Level 7 (sense 10107, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "她首创着这种新舞蹈。",
      "is_correct": false,
      "error_description": "“首创”表示第一次创造，是已经完成的动作，不能与表示动作持续的“着”连用，应改为表示完成的“了”。"
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "她首创了这种新舞蹈。",
      "is_correct": true
    },
    {
      "text": "同学们首创了这个节目。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她首創著這種新舞蹈。",
        "is_correct": false,
        "error_description": "“首創”表示第一次創造，是已經完成的動作，不能與表示動作持續的“著”連用，應改為表示完成的“了”。"
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "她首創了這種新舞蹈。",
        "is_correct": true
      },
      {
        "text": "同學們首創了這個節目。",
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
      "text": "他首创了这种新模式昨天。",
      "is_correct": false,
      "error_description": "时间状语‘昨天’应放在主语之后、动词之前，不能放在句末。"
    },
    {
      "text": "这是他们首创的活动。",
      "is_correct": true
    },
    {
      "text": "我们支持他首创这种新模式。",
      "is_correct": true
    },
    {
      "text": "首创这种新玩法能带来很多快乐。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他首創了這種新模式昨天。",
        "is_correct": false,
        "error_description": "時間狀語‘昨天’應放在主語之後、動詞之前，不能放在句末。"
      },
      {
        "text": "這是他們首創的活動。",
        "is_correct": true
      },
      {
        "text": "我們支援他首創這種新模式。",
        "is_correct": true
      },
      {
        "text": "首創這種新玩法能帶來很多快樂。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10107, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他首创了这个有趣的班级游戏。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "他首创了这个有趣的班级游戏在昨天。",
      "is_correct": false,
      "error_description": "时间状语位置错误。在汉语中，时间状语通常放在主语之后、谓语动词之前，或者句首，不能放在句末。"
    },
    {
      "text": "我们曾首创这种环保的交友方式。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他首創了這個有趣的班級遊戲。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "他首創了這個有趣的班級遊戲在昨天。",
        "is_correct": false,
        "error_description": "時間狀語位置錯誤。在漢語中，時間狀語通常放在主語之後、謂語動詞之前，或者句首，不能放在句末。"
      },
      {
        "text": "我們曾首創這種環保的交友方式。",
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
      "text": "小明首创了这种分享心情的方法。",
      "is_correct": true
    },
    {
      "text": "小明首创了这种分享心情的方法昨天。",
      "is_correct": false,
      "error_description": "时间状语位置错误。在汉语中，表示时间的词语（如“昨天”）通常应放在主语之后、谓语动词之前，不能放在句末。"
    },
    {
      "text": "我们把这看作大家的首创。",
      "is_correct": true
    },
    {
      "text": "这种表达情感的方式是他的首创。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "小明首創了這種分享心情的方法。",
        "is_correct": true
      },
      {
        "text": "小明首創了這種分享心情的方法昨天。",
        "is_correct": false,
        "error_description": "時間狀語位置錯誤。在漢語中，表示時間的詞語（如“昨天”）通常應放在主語之後、謂語動詞之前，不能放在句末。"
      },
      {
        "text": "我們把這看作大家的首創。",
        "is_correct": true
      },
      {
        "text": "這種表達情感的方式是他的首創。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10110, level 1

#### Pack A
### Level 1 (sense 10110, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "ipa": "[kʰɤ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "科",
    "克",
    "可",
    "课"
  ],
  "correct_answer": "可",
  "explanation": "“可”读作 kě（第三声），表示许可或可能。",
  "distractor_explanations": {
    "科": "“科”读作 kē（第一声），声调不同，通常指学科或类别，如“科学”。",
    "克": "“克”读作 kè（第四声），声调不同，通常指克服或重量单位，如“克服”。",
    "课": "“课”读作 kè（第四声），声调不同，通常指教学科目，如“上课”。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "ipa": "[kʰɤ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "科",
      "克",
      "可",
      "課"
    ],
    "correct_answer": "可",
    "explanation": "“可”讀作 kě（第三聲），表示許可或可能。",
    "distractor_explanations": {
      "科": "“科”讀作 kē（第一聲），聲調不同，通常指學科或類別，如“科學”。",
      "克": "“克”讀作 kè（第四聲），聲調不同，通常指克服或重量單位，如“克服”。",
      "课": "“課”讀作 kè（第四聲），聲調不同，通常指教學科目，如“上課”。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10110, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "可",
  "pronunciation": "kě",
  "ipa": "[kʰɤ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "科",
    "客",
    "壳",
    "可"
  ],
  "correct_answer": "可",
  "explanation": "正确：'可'读第三声（kě），表示许可或可能，符合听到的语音。",
  "distractor_explanations": {
    "科": "声调错误：'科'读第一声（kē），指学科或类别，与目标词'可'（kě）声调不同，意义完全不同。",
    "壳": "声调错误：'壳'读第二声（ké），指坚硬的外皮，与目标词'可'（kě）声调不同，意义完全不同。",
    "客": "声调错误：'客'读第四声（kè），指客人，与目标词'可'（kě）声调不同，意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "ipa": "[kʰɤ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "科",
      "客",
      "殼",
      "可"
    ],
    "correct_answer": "可",
    "explanation": "正確：'可'讀第三聲（kě），表示許可或可能，符合聽到的語音。",
    "distractor_explanations": {
      "科": "聲調錯誤：'科'讀第一聲（kē），指學科或類別，與目標詞'可'（kě）聲調不同，意義完全不同。",
      "壳": "聲調錯誤：'殼'讀第二聲（ké），指堅硬的外皮，與目標詞'可'（kě）聲調不同，意義完全不同。",
      "客": "聲調錯誤：'客'讀第四聲（kè），指客人，與目標詞'可'（kě）聲調不同，意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10110, level 3

#### Pack A
### Level 3 (sense 10110, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "去不去公园这事儿___去可不去，反正周末我在家待着也没别的事儿干。",
  "original_sentence": "去不去公园这事儿可去可不去，反正周末我在家待着也没别的事儿干。",
  "correct_answer": "可",
  "options": [
    "可",
    "能",
    "须",
    "该"
  ],
  "explanation": "正确：'可'在'可V可不V'结构中表示许可或选择，符合句意。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "去不去公園這事兒___去可不去，反正週末我在家待著也沒別的事兒幹。",
    "original_sentence": "去不去公園這事兒可去可不去，反正週末我在家待著也沒別的事兒幹。",
    "correct_answer": "可",
    "options": [
      "可",
      "能",
      "須",
      "該"
    ],
    "explanation": "正確：'可'在'可V可不V'結構中表示許可或選擇，符合句意。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这旧纸___把桌子擦干净。",
  "original_sentence": "这旧纸可把桌子擦干净。",
  "correct_answer": "可",
  "options": [
    "敢",
    "配",
    "可",
    "得"
  ],
  "explanation": "正确选项，“可”表示“可以用来”，符合旧纸擦桌子的语境。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這舊紙___把桌子擦乾淨。",
    "original_sentence": "這舊紙可把桌子擦乾淨。",
    "correct_answer": "可",
    "options": [
      "敢",
      "配",
      "可",
      "得"
    ],
    "explanation": "正確選項，“可”表示“可以用來”，符合舊紙擦桌子的語境。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```

#### Pack B
### Level 3 (sense 10110, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "这些自然力经过简单转化，___变成直接利用的动力。",
  "original_sentence": "这些自然力经过简单转化，可变成直接利用的动力。",
  "correct_answer": "可",
  "options": [
    "敢",
    "须",
    "准",
    "可"
  ],
  "explanation": "正确。在此句中表示客观可能性，符合科学说明的语境。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這些自然力經過簡單轉化，___變成直接利用的動力。",
    "original_sentence": "這些自然力經過簡單轉化，可變成直接利用的動力。",
    "correct_answer": "可",
    "options": [
      "敢",
      "須",
      "準",
      "可"
    ],
    "explanation": "正確。在此句中表示客觀可能性，符合科學說明的語境。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "这件衣服___放进洗衣机里洗吗？",
  "original_sentence": "这件衣服可放进洗衣机里洗吗？",
  "correct_answer": "可",
  "options": [
    "可",
    "须",
    "配",
    "敢"
  ],
  "explanation": "正确。在此句中表示客观可能性或许可，符合语境。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這件衣服___放進洗衣機裡洗嗎？",
    "original_sentence": "這件衣服可放進洗衣機裡洗嗎？",
    "correct_answer": "可",
    "options": [
      "可",
      "須",
      "配",
      "敢"
    ],
    "explanation": "正確。在此句中表示客觀可能性或許可，符合語境。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```

---

## sense 10110, level 6

#### Pack A
### Level 6 (sense 10110, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "这苹果可吃吗？",
      "is_correct": true
    },
    {
      "text": "这苹果可吃着吗？",
      "is_correct": false
    },
    {
      "text": "这只苹果可吃吗？",
      "is_correct": false
    },
    {
      "text": "可这苹果吃吗？",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“苹果”的规范量词应为“个”，不能使用用于动物或某些特定物品的“只”。 体标选用错误：情态动词“可”后通常接动词原形表示可能性或许可，不能接表示动作持续的体标记“着”。 语序错误：情态动词“可”应放在主语“这苹果”之后、谓语动词“吃”之前，不能置于句首破坏“主题—评论”结构。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "這蘋果可吃嗎？",
        "is_correct": true
      },
      {
        "text": "這蘋果可吃著嗎？",
        "is_correct": false
      },
      {
        "text": "這隻蘋果可吃嗎？",
        "is_correct": false
      },
      {
        "text": "可這蘋果吃嗎？",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“蘋果”的規範量詞應為“個”，不能使用用於動物或某些特定物品的“只”。 體標選用錯誤：情態動詞“可”後通常接動詞原形表示可能性或許可，不能接表示動作持續的體標記“著”。 語序錯誤：情態動詞“可”應放在主語“這蘋果”之後、謂語動詞“吃”之前，不能置於句首破壞“主題—評論”結構。",
    "target_word": "可"
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "你可通过网络联系上远方的朋友吗？",
      "is_correct": true
    },
    {
      "text": "你可通过网络联系着远方的朋友吗？",
      "is_correct": false
    },
    {
      "text": "你可通过网络联系上远方的朋友吗昨天？",
      "is_correct": false
    },
    {
      "text": "你可通过网络联系下远方的朋友吗？",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“着”表示动作持续，与“可……吗”表示可能性的疑问句式冲突，应去掉“着”。 语序错误。时间状语“昨天”不能放在句末，应放在主语“你”之后或句首。 结果补语误用。“下”不能与“联系”搭配表示建立连接的结果，应改为“上”或“到”。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "你可通過網路聯絡上遠方的朋友嗎？",
        "is_correct": true
      },
      {
        "text": "你可通過網路聯絡著遠方的朋友嗎？",
        "is_correct": false
      },
      {
        "text": "你可通過網路聯絡上遠方的朋友嗎昨天？",
        "is_correct": false
      },
      {
        "text": "你可通過網路聯絡下遠方的朋友嗎？",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“著”表示動作持續，與“可……嗎”表示可能性的疑問句式衝突，應去掉“著”。 語序錯誤。時間狀語“昨天”不能放在句末，應放在主語“你”之後或句首。 結果補語誤用。“下”不能與“聯絡”搭配表示建立連線的結果，應改為“上”或“到”。",
    "target_word": "可"
  }
}
```

#### Pack B
### Level 6 (sense 10110, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这水烧开着可直接喝。",
      "is_correct": false
    },
    {
      "text": "这水烧开后可直接喝出来。",
      "is_correct": false
    },
    {
      "text": "这水烧开后可直接喝。",
      "is_correct": true
    },
    {
      "text": "这水可直接喝烧开后。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：条件状语'烧开后'应放在情态动词'可'之前，说明在什么条件下可以喝，不能放在句末。 体标选用错误：'烧开'是瞬间完成动词，不能用表示状态持续的'着'，应改为'烧开后'或'烧开了'。 方向补语误用：'喝'的动作方向是进入体内，应使用'喝下去'或直接说'喝'，不能使用表示由内向外的'出来'。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "這水燒開著可直接喝。",
        "is_correct": false
      },
      {
        "text": "這水燒開後可直接喝出來。",
        "is_correct": false
      },
      {
        "text": "這水燒開後可直接喝。",
        "is_correct": true
      },
      {
        "text": "這水可直接喝燒開後。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：條件狀語'燒開後'應放在情態動詞'可'之前，說明在什麼條件下可以喝，不能放在句末。 體標選用錯誤：'燒開'是瞬間完成動詞，不能用表示狀態持續的'著'，應改為'燒開後'或'燒開了'。 方向補語誤用：'喝'的動作方向是進入體內，應使用'喝下去'或直接說'喝'，不能使用表示由內向外的'出來'。",
    "target_word": "可"
  }
}
```

---

## sense 10110, level 7

#### Pack A
### Level 7 (sense 10110, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "这意味着，同一个程序可在不同电脑间无缝切换，记忆和习惯都不受影响。",
      "is_correct": true
    },
    {
      "text": "这种技术的繁荣暗示着一种未来：个人AI不再由大公司垄断，而是大家可共同塑造的。",
      "is_correct": true
    },
    {
      "text": "这些自然力经过简单转化，可变成直接利用的动力。",
      "is_correct": true
    },
    {
      "text": "这些自然力经过简单转化，可变成了直接利用的动力。",
      "is_correct": false,
      "error_description": "情态动词“可”表示能力或可能性，其后的动词“变成”不能加表示完成的动态助词“了”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這意味著，同一個程式可在不同電腦間無縫切換，記憶和習慣都不受影響。",
        "is_correct": true
      },
      {
        "text": "這種技術的繁榮暗示著一種未來：個人AI不再由大公司壟斷，而是大家可共同塑造的。",
        "is_correct": true
      },
      {
        "text": "這些自然力經過簡單轉化，可變成直接利用的動力。",
        "is_correct": true
      },
      {
        "text": "這些自然力經過簡單轉化，可變成了直接利用的動力。",
        "is_correct": false,
        "error_description": "情態動詞“可”表示能力或可能性，其後的動詞“變成”不能加表示完成的動態助詞“了”。"
      }
    ]
  }
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "这件衣服可放进洗衣机里洗吗？",
      "is_correct": true
    },
    {
      "text": "他的心事可跟最信任的朋友说。",
      "is_correct": true
    },
    {
      "text": "这件衣服可放了进洗衣机里洗吗？",
      "is_correct": false,
      "error_description": "情态动词“可”表示可能性或允许时，其后的动词短语不能带表示动作完成的体标记“了”。此处“了”位置与选用均错误，应直接删除。"
    },
    {
      "text": "你可通过网络联系上远方的朋友吗？",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這件衣服可放進洗衣機裡洗嗎？",
        "is_correct": true
      },
      {
        "text": "他的心事可跟最信任的朋友說。",
        "is_correct": true
      },
      {
        "text": "這件衣服可放了進洗衣機裡洗嗎？",
        "is_correct": false,
        "error_description": "情態動詞“可”表示可能性或允許時，其後的動詞短語不能帶表示動作完成的體標記“了”。此處“了”位置與選用均錯誤，應直接刪除。"
      },
      {
        "text": "你可通過網路聯絡上遠方的朋友嗎？",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10110, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这周末的同学聚会你可去可不去，反正大家也就是随便吃个饭聊聊天，没那么多讲究，你要是觉得累就在家好好歇着。",
      "is_correct": true
    },
    {
      "text": "去不去公园这事儿可去可不去，反正周末我在家待着也没别的事儿干。",
      "is_correct": true
    },
    {
      "text": "这台旧电脑你修可不修，反正平时你也就上上网、看看视频，真要是彻底坏了直接换新的就行。",
      "is_correct": false,
      "error_description": "“可修可不修”是固定结构，表示“可以修也可以不修”，情态动词“可”必须放在动词“修”之前，不能放在动词之后。"
    },
    {
      "text": "这台旧电脑你可修可不修，反正平时你也就上上网、看看视频，真要是彻底坏了直接换新的就行。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這週末的同學聚會你可去可不去，反正大家也就是隨便吃個飯聊聊天，沒那麼多講究，你要是覺得累就在家好好歇著。",
        "is_correct": true
      },
      {
        "text": "去不去公園這事兒可去可不去，反正週末我在家待著也沒別的事兒幹。",
        "is_correct": true
      },
      {
        "text": "這臺舊電腦你修可不修，反正平時你也就上上網、看看影片，真要是徹底壞了直接換新的就行。",
        "is_correct": false,
        "error_description": "“可修可不修”是固定結構，表示“可以修也可以不修”，情態動詞“可”必須放在動詞“修”之前，不能放在動詞之後。"
      },
      {
        "text": "這臺舊電腦你可修可不修，反正平時你也就上上網、看看影片，真要是徹底壞了直接換新的就行。",
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
      "text": "这旧纸可把桌子擦干净。",
      "is_correct": true
    },
    {
      "text": "这礼物送给可小明。",
      "is_correct": false,
      "error_description": "情态动词“可”应该放在主要动词“送”之前，不能放在动词和宾语之间，属于语序错误。"
    },
    {
      "text": "这件外套可穿着去爬山。",
      "is_correct": true
    },
    {
      "text": "这礼物可送给小明。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這舊紙可把桌子擦乾淨。",
        "is_correct": true
      },
      {
        "text": "這禮物送給可小明。",
        "is_correct": false,
        "error_description": "情態動詞“可”應該放在主要動詞“送”之前，不能放在動詞和賓語之間，屬於語序錯誤。"
      },
      {
        "text": "這件外套可穿著去爬山。",
        "is_correct": true
      },
      {
        "text": "這禮物可送給小明。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10111, level 6

#### Pack A
### Level 6 (sense 10111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复出排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了重复着排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了排版可重复的技术先河。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：此处需表示动作可再次发生的属性，应使用“可重复”，误用体标“着”表示动作持续，不符合语境。 语序错误：修饰语“可重复”应放在中心语“排版”之前，构成“可重复排版”，放在其后不符合汉语修饰习惯。 结果补语误用：“出”表示从无到有产生，与“重复”表示再次进行的语义冲突，不能搭配使用。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複出排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了重複著排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了排版可重複的技術先河。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：此處需表示動作可再次發生的屬性，應使用“可重複”，誤用體標“著”表示動作持續，不符合語境。 語序錯誤：修飾語“可重複”應放在中心語“排版”之前，構成“可重複排版”，放在其後不符合漢語修飾習慣。 結果補語誤用：“出”表示從無到有產生，與“重複”表示再次進行的語義衝突，不能搭配使用。",
    "target_word": "重複"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "请你把刚才的话重复起来一次。",
      "is_correct": false
    },
    {
      "text": "请你把刚才的话重复着了。",
      "is_correct": false
    },
    {
      "text": "请你把刚才的话重复一次。",
      "is_correct": true
    },
    {
      "text": "重复一次请你把刚才的话。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“重复”表示动作再次发生，不能用“着”表示动作持续，且“着了”连用不符合汉语体标记的语法规则。 语序错误。动词短语“重复一次”被放在了祈使词“请你”之前，破坏了正常的语序和“把”字句的基本结构。 方向/结果补语误用。“起来”表示动作开始或向上，而“重复”表示再次进行，两者语义不兼容，不能搭配使用。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "請你把剛才的話重複起來一次。",
        "is_correct": false
      },
      {
        "text": "請你把剛才的話重複著了。",
        "is_correct": false
      },
      {
        "text": "請你把剛才的話重複一次。",
        "is_correct": true
      },
      {
        "text": "重複一次請你把剛才的話。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“重複”表示動作再次發生，不能用“著”表示動作持續，且“著了”連用不符合漢語體標記的語法規則。 語序錯誤。動詞短語“重複一次”被放在了祈使詞“請你”之前，破壞了正常的語序和“把”字句的基本結構。 方向/結果補語誤用。“起來”表示動作開始或向上，而“重複”表示再次進行，兩者語義不相容，不能搭配使用。",
    "target_word": "重複"
  }
}
```

#### Pack B
### Level 6 (sense 10111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版起的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复着排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了重复可排版的技术先河。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。动态助词“着”不能插在“可”和“重复”之间，且“重复”在此处表示可能性，不应使用表示持续的“着”。 语序错误。能愿动词“可”必须放在动词“重复”之前，原句语序破坏了“可+动词”的合法句法结构。 方向补语误用。动词“重复”后不能接趋向补语“起”，且“排版起”不符合汉语表达习惯，属于生造搭配。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版起的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複著排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了重複可排版的技術先河。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。動態助詞“著”不能插在“可”和“重複”之間，且“重複”在此處表示可能性，不應使用表示持續的“著”。 語序錯誤。能願動詞“可”必須放在動詞“重複”之前，原句語序破壞了“可+動詞”的合法句法結構。 方向補語誤用。動詞“重複”後不能接趨向補語“起”，且“排版起”不符合漢語表達習慣，屬於生造搭配。",
    "target_word": "重複"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "请不要重复了这句话。",
      "is_correct": false
    },
    {
      "text": "请不要重复这句话。",
      "is_correct": true
    },
    {
      "text": "请不要重复出这句话。",
      "is_correct": false
    },
    {
      "text": "请不要重复这句话起来。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。动态助词“了”应放在动补结构之后，正确语序为“重复这句话了”或直接省略“了”。 结果补语误用。“出”表示从无到有或显露，而“重复”本身已包含再次进行的意义，不能加“出”作补语。 趋向补语误用。“起来”表示动作开始或向上，不能接在“重复”后表示禁止或停止，此处属于补语冗余且语义不通。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "請不要重複了這句話。",
        "is_correct": false
      },
      {
        "text": "請不要重複這句話。",
        "is_correct": true
      },
      {
        "text": "請不要重複出這句話。",
        "is_correct": false
      },
      {
        "text": "請不要重複這句話起來。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。動態助詞“了”應放在動補結構之後，正確語序為“重複這句話了”或直接省略“了”。 結果補語誤用。“出”表示從無到有或顯露，而“重複”本身已包含再次進行的意義，不能加“出”作補語。 趨向補語誤用。“起來”表示動作開始或向上，不能接在“重複”後表示禁止或停止，此處屬於補語冗餘且語義不通。",
    "target_word": "重複"
  }
}
```

---
