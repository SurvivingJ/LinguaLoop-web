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


## sense 10106, level 7

#### Pack A
### Level 7 (sense 10106, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他看毕着那本书，心里十分感动。",
      "is_correct": false,
      "error_description": "体标选用错误。“毕”表示动作已经完成，而“着”表示动作正在进行或状态持续，两者在语义上相互矛盾，因此不能连用，应删去“着”。"
    },
    {
      "text": "经过四年的刻苦学习，他终于在今年夏天顺利从这所知名大学毕业，即将步入社会开启新的人生篇章。",
      "is_correct": true
    },
    {
      "text": "大家吃毕晚饭，一起去散步。",
      "is_correct": true
    },
    {
      "text": "他看毕那本书，心里十分感动。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他看畢著那本書，心裡十分感動。",
        "is_correct": false,
        "error_description": "體標選用錯誤。“畢”表示動作已經完成，而“著”表示動作正在進行或狀態持續，兩者在語義上相互矛盾，因此不能連用，應刪去“著”。"
      },
      {
        "text": "經過四年的刻苦學習，他終於在今年夏天順利從這所知名大學畢業，即將步入社會開啟新的人生篇章。",
        "is_correct": true
      },
      {
        "text": "大家吃畢晚飯，一起去散步。",
        "is_correct": true
      },
      {
        "text": "他看畢那本書，心裡十分感動。",
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
      "text": "他画毕最后一笔，满意地笑了。",
      "is_correct": true
    },
    {
      "text": "他毕画最后一笔，满意地笑了。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，结果补语“毕”必须放在动词“画”的后面，构成“动词+毕”的结构，不能放在动词前面。"
    },
    {
      "text": "我们听毕报告，开始分组讨论。",
      "is_correct": true
    },
    {
      "text": "我读毕这篇故事，深受启发。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他畫畢最後一筆，滿意地笑了。",
        "is_correct": true
      },
      {
        "text": "他畢畫最後一筆，滿意地笑了。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，結果補語“畢”必須放在動詞“畫”的後面，構成“動詞+畢”的結構，不能放在動詞前面。"
      },
      {
        "text": "我們聽畢報告，開始分組討論。",
        "is_correct": true
      },
      {
        "text": "我讀畢這篇故事，深受啟發。",
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

---

## sense 10107, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 10107, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "首创着需要很大的勇气。",
      "is_correct": false
    },
    {
      "text": "首创需要很大的勇气。",
      "is_correct": true
    },
    {
      "text": "需要很大的勇气首创。",
      "is_correct": false
    },
    {
      "text": "首创出来需要很大的勇气。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：'首创'是表示瞬间完成的动作动词，不能加表示状态持续的动态助词'着'。 语序错误：'首创'作为及物动词或核心动作，在此处作主语更符合汉语习惯，后置会导致句子结构松散、头重脚轻。 补语误用：'首创'本身已包含'最先创造'的完整结果意义，再加结果补语'出来'属于语义重复且搭配不当。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "首創著需要很大的勇氣。",
        "is_correct": false
      },
      {
        "text": "首創需要很大的勇氣。",
        "is_correct": true
      },
      {
        "text": "需要很大的勇氣首創。",
        "is_correct": false
      },
      {
        "text": "首創出來需要很大的勇氣。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：'首創'是表示瞬間完成的動作動詞，不能加表示狀態持續的動態助詞'著'。 語序錯誤：'首創'作為及物動詞或核心動作，在此處作主語更符合漢語習慣，後置會導致句子結構鬆散、頭重腳輕。 補語誤用：'首創'本身已包含'最先創造'的完整結果意義，再加結果補語'出來'屬於語義重複且搭配不當。",
    "target_word": "首創"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "首创",
  "relation": "antonym",
  "options": [
    "实践",
    "探索",
    "发现",
    "模仿"
  ],
  "correct_answer": "模仿",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "最先创造或发明，指做别人没有做过的事情。",
      "explanation": "反义项：照着现成的样子做，与最先创造相对"
    }
  },
  "hant": {
    "word": "首創",
    "relation": "antonym",
    "options": [
      "實踐",
      "探索",
      "發現",
      "模仿"
    ],
    "correct_answer": "模仿",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "最先創造或發明，指做別人沒有做過的事情。",
        "explanation": "反義項：照著現成的樣子做，與最先創造相對"
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
      "text": "首创精神值得着我们学习。",
      "is_correct": false
    },
    {
      "text": "首创精神值得学习得很。",
      "is_correct": false
    },
    {
      "text": "首创精神值得我们学习。",
      "is_correct": true
    },
    {
      "text": "值得学习首创精神我们。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：'着'表示动作正在进行或状态持续，不能放在'值得'和动词'学习'之间，应去掉'着'。 语序错误：宾语'首创精神'应紧跟在动词'学习'之后，主语'我们'应放在句首或'值得'之前。 搭配错误：'值得'后直接加动词即可，'得'用于动词后的程度补语，此处结构混乱，应去掉'得很'。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "首創精神值得著我們學習。",
        "is_correct": false
      },
      {
        "text": "首創精神值得學習得很。",
        "is_correct": false
      },
      {
        "text": "首創精神值得我們學習。",
        "is_correct": true
      },
      {
        "text": "值得學習首創精神我們。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：'著'表示動作正在進行或狀態持續，不能放在'值得'和動詞'學習'之間，應去掉'著'。 語序錯誤：賓語'首創精神'應緊跟在動詞'學習'之後，主語'我們'應放在句首或'值得'之前。 搭配錯誤：'值得'後直接加動詞即可，'得'用於動詞後的程度補語，此處結構混亂，應去掉'得很'。",
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
      "text": "他首创了昨天这种新玩法。",
      "is_correct": false,
      "error_description": "时间状语位置错误。在汉语中，表示时间的词语（如“昨天”）通常应放在主语之后、动词之前，不能放在动词和宾语之间。"
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "这是他们首创的品牌。",
      "is_correct": true
    },
    {
      "text": "他首创了这种新玩法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他首創了昨天這種新玩法。",
        "is_correct": false,
        "error_description": "時間狀語位置錯誤。在漢語中，表示時間的詞語（如“昨天”）通常應放在主語之後、動詞之前，不能放在動詞和賓語之間。"
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "這是他們首創的品牌。",
        "is_correct": true
      },
      {
        "text": "他首創了這種新玩法。",
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
      "text": "大家首创了这项新颖的活动。",
      "is_correct": true
    },
    {
      "text": "他首创着一种新的学习方法。",
      "is_correct": false,
      "error_description": "体标误用。'首创'表示一次性完成的动作，不能与表示持续状态的'着'连用，应改为表示完成的'了'。"
    },
    {
      "text": "这种首创让人很开心。",
      "is_correct": true
    },
    {
      "text": "首创精神值得我们学习。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "大家首創了這項新穎的活動。",
        "is_correct": true
      },
      {
        "text": "他首創著一種新的學習方法。",
        "is_correct": false,
        "error_description": "體標誤用。'首創'表示一次性完成的動作，不能與表示持續狀態的'著'連用，應改為表示完成的'了'。"
      },
      {
        "text": "這種首創讓人很開心。",
        "is_correct": true
      },
      {
        "text": "首創精神值得我們學習。",
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

---

## sense 10110, level 1

#### Pack A
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
    "克",
    "科",
    "可",
    "客"
  ],
  "correct_answer": "可",
  "explanation": "正确。'可'读第三声kě，在此表示许可或可能。",
  "distractor_explanations": {
    "克": "错误。'克'读第四声kè，意为克服或重量单位，声调不同导致意义改变。",
    "客": "错误。'客'读第四声kè，指客人或旅客，与目标词声调不同。",
    "科": "错误。'科'读第一声kē，指学科或类别，声调不同导致意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "ipa": "[kʰɤ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "克",
      "科",
      "可",
      "客"
    ],
    "correct_answer": "可",
    "explanation": "正確。'可'讀第三聲kě，在此表示許可或可能。",
    "distractor_explanations": {
      "克": "錯誤。'克'讀第四聲kè，意為克服或重量單位，聲調不同導致意義改變。",
      "客": "錯誤。'客'讀第四聲kè，指客人或旅客，與目標詞聲調不同。",
      "科": "錯誤。'科'讀第一聲kē，指學科或類別，聲調不同導致意義完全不同。"
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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "这片森林里的野生蘑菇有些___食用，有些则含有剧毒。",
  "original_sentence": "这片森林里的野生蘑菇有些可食用，有些则含有剧毒。",
  "correct_answer": "可",
  "options": [
    "愿",
    "须",
    "可",
    "应"
  ],
  "explanation": "正确。'可'在此处作情态动词，表示野生蘑菇具备被食用的可能性或许可。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這片森林裡的野生蘑菇有些___食用，有些則含有劇毒。",
    "original_sentence": "這片森林裡的野生蘑菇有些可食用，有些則含有劇毒。",
    "correct_answer": "可",
    "options": [
      "願",
      "須",
      "可",
      "應"
    ],
    "explanation": "正確。'可'在此處作情態動詞，表示野生蘑菇具備被食用的可能性或許可。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "现在的智能手机功能很多，除了打电话，还___用来拍照和上网。",
  "original_sentence": "现在的智能手机功能很多，除了打电话，还可用来拍照和上网。",
  "correct_answer": "可",
  "options": [
    "须",
    "敢",
    "欲",
    "可"
  ],
  "explanation": "正确。此处“可”表示客观条件允许或具备某种功能。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "現在的智慧手機功能很多，除了打電話，還___用來拍照和上網。",
    "original_sentence": "現在的智慧手機功能很多，除了打電話，還可用來拍照和上網。",
    "correct_answer": "可",
    "options": [
      "須",
      "敢",
      "欲",
      "可"
    ],
    "explanation": "正確。此處“可”表示客觀條件允許或具備某種功能。",
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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这扇窗户的锁坏了，从外面用手一拉就可以过打开，很不安全。",
      "is_correct": false
    },
    {
      "text": "这扇窗户的锁坏了，从外面用手一拉就可以得打开，很不安全。",
      "is_correct": false
    },
    {
      "text": "这扇窗户的锁坏了，从外面用手一拉就可以打开着，很不安全。",
      "is_correct": false
    },
    {
      "text": "这扇窗户的锁坏了，从外面用手一拉就可以打开，很不安全。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：“可以”后面不能加结构助词“得”，应直接接动词“打开”。 体标位置/选用错误：句末误用动态助词“着”，“打开”表示动作完成或结果，不能用“着”表示状态持续。 体标位置/选用错误：误用“过”表示经历，此处描述的是窗户当前具备的客观属性或结果，而非过去的经历。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "這扇窗戶的鎖壞了，從外面用手一拉就可以過開啟，很不安全。",
        "is_correct": false
      },
      {
        "text": "這扇窗戶的鎖壞了，從外面用手一拉就可以得開啟，很不安全。",
        "is_correct": false
      },
      {
        "text": "這扇窗戶的鎖壞了，從外面用手一拉就可以開啟著，很不安全。",
        "is_correct": false
      },
      {
        "text": "這扇窗戶的鎖壞了，從外面用手一拉就可以開啟，很不安全。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：“可以”後面不能加結構助詞“得”，應直接接動詞“開啟”。 體標位置/選用錯誤：句末誤用動態助詞“著”，“開啟”表示動作完成或結果，不能用“著”表示狀態持續。 體標位置/選用錯誤：誤用“過”表示經歷，此處描述的是窗戶當前具備的客觀屬性或結果，而非過去的經歷。",
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

#### Pack B
### Level 7 (sense 10110, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这意味着，同一代理可在不同计算平台间无缝迁移，其长期记忆与行为模式不受底层模型更迭的影响。",
      "is_correct": true
    },
    {
      "text": "这种“技术公地”的繁荣，暗示着一种可能的未来：个人AI代理不再由科技巨头垄断定义，而是成为可被公众共同塑造的认知基础设施。",
      "is_correct": true
    },
    {
      "text": "这片森林里的野生蘑菇有些可食用，有些则含有剧毒。",
      "is_correct": true
    },
    {
      "text": "他昨天把那份机密文件可不经过批准就带出了办公室。",
      "is_correct": false,
      "error_description": "语序错误。情态动词“可”应放在“把”字之前，即“可不经过批准就把……”，不能放在“把”字和宾语之间。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這意味著，同一代理可在不同計算平臺間無縫遷移，其長期記憶與行為模式不受底層模型更迭的影響。",
        "is_correct": true
      },
      {
        "text": "這種“技術公地”的繁榮，暗示著一種可能的未來：個人AI代理不再由科技巨頭壟斷定義，而是成為可被公眾共同塑造的認知基礎設施。",
        "is_correct": true
      },
      {
        "text": "這片森林裡的野生蘑菇有些可食用，有些則含有劇毒。",
        "is_correct": true
      },
      {
        "text": "他昨天把那份機密檔案可不經過批准就帶出了辦公室。",
        "is_correct": false,
        "error_description": "語序錯誤。情態動詞“可”應放在“把”字之前，即“可不經過批准就把……”，不能放在“把”字和賓語之間。"
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
      "text": "他可了去北京。",
      "is_correct": false,
      "error_description": "体标位置错误。情态动词“可”（可以）后面不能直接加动态助词“了”表示动作完成。如果要表示情况的变化或新情况的出现，语气助词“了”应该放在句末。"
    },
    {
      "text": "这个旧零件虽然生锈了，但清理一下后还可继续使用。",
      "is_correct": true
    },
    {
      "text": "现在的智能手机功能很多，除了打电话，还可用来拍照和上网。",
      "is_correct": true
    },
    {
      "text": "这扇窗户的锁坏了，从外面用手一拉就可以打开，很不安全。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他可了去北京。",
        "is_correct": false,
        "error_description": "體標位置錯誤。情態動詞“可”（可以）後面不能直接加動態助詞“了”表示動作完成。如果要表示情況的變化或新情況的出現，語氣助詞“了”應該放在句末。"
      },
      {
        "text": "這個舊零件雖然生鏽了，但清理一下後還可繼續使用。",
        "is_correct": true
      },
      {
        "text": "現在的智慧手機功能很多，除了打電話，還可用來拍照和上網。",
        "is_correct": true
      },
      {
        "text": "這扇窗戶的鎖壞了，從外面用手一拉就可以開啟，很不安全。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10111, level 3

#### Pack A
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这种错误我们不能再___了。",
  "original_sentence": "这种错误我们不能再重复了。",
  "correct_answer": "重复",
  "options": [
    "重演",
    "重现",
    "复制",
    "重复"
  ],
  "explanation": "正确。'重复'表示再次做同样的事，符合句中'不能再'的语境。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "這種錯誤我們不能再___了。",
    "original_sentence": "這種錯誤我們不能再重複了。",
    "correct_answer": "重複",
    "options": [
      "重演",
      "重現",
      "複製",
      "重複"
    ],
    "explanation": "正確。'重複'表示再次做同樣的事，符合句中'不能再'的語境。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```

#### Pack B
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "它的设计像一个绿色的箭头圆圈，表示废物可以被___利用。",
  "original_sentence": "它的设计像一个绿色的箭头圆圈，表示废物可以被重复利用。",
  "correct_answer": "重复",
  "options": [
    "破坏",
    "消耗",
    "施展",
    "重复"
  ],
  "explanation": "“重复”在此处表示再次利用，符合废物管理的环保语境与搭配习惯。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被___利用。",
    "original_sentence": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被重複利用。",
    "correct_answer": "重複",
    "options": [
      "破壞",
      "消耗",
      "施展",
      "重複"
    ],
    "explanation": "“重複”在此處表示再次利用，符合廢物管理的環保語境與搭配習慣。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我不喜欢这种___的游戏。",
  "original_sentence": "我不喜欢这种重复的游戏。",
  "correct_answer": "重复",
  "options": [
    "昂贵",
    "重复",
    "打破",
    "复杂"
  ],
  "explanation": "正确选项，表示动作或情况再次出现，符合句意。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "我不喜歡這種___的遊戲。",
    "original_sentence": "我不喜歡這種重複的遊戲。",
    "correct_answer": "重複",
    "options": [
      "昂貴",
      "重複",
      "打破",
      "複雜"
    ],
    "explanation": "正確選項，表示動作或情況再次出現，符合句意。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
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
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了重复可排版的技术先河。",
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
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河过。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'重复'作为动词，后面不能直接加动态助词'着'来表示技术特征，应去掉'着'。 语序错误。'重复'应放在助动词'可'之后修饰动词'排版'，放在'可'之前破坏了状语的正常语序。 体标选用错误。句中表示一种客观的技术能力或状态，句末加'过'表示曾经发生且已结束，与'开启了……先河'的语境和体貌不符。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了重複可排版的技術先河。",
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
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河過。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'重複'作為動詞，後面不能直接加動態助詞'著'來表示技術特徵，應去掉'著'。 語序錯誤。'重複'應放在助動詞'可'之後修飾動詞'排版'，放在'可'之前破壞了狀語的正常語序。 體標選用錯誤。句中表示一種客觀的技術能力或狀態，句末加'過'表示曾經發生且已結束，與'開啟了……先河'的語境和體貌不符。",
    "target_word": "重複"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "relation": "antonym",
  "options": [
    "首创",
    "延伸",
    "继续",
    "模仿"
  ],
  "correct_answer": "首创",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "反义：「首创」指第一次创造，与「重复」表再次进行构成反义"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "首創",
      "延伸",
      "繼續",
      "模仿"
    ],
    "correct_answer": "首創",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "反義：「首創」指第一次創造，與「重複」表再次進行構成反義"
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
      "text": "老师把重点内容重复了讲两次。",
      "is_correct": false
    },
    {
      "text": "老师把重点内容重复讲两次过。",
      "is_correct": false
    },
    {
      "text": "老师把重点内容重复讲过两次。",
      "is_correct": true
    },
    {
      "text": "老师把重点内容重复讲过两次了着。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词'了'应放在动词'重复'之后、补语'两次'之前，或者句末，不能插在动词和补语之间。 体标选用错误：表示过去经历应使用'过'，但'过'应紧跟在动词'重复'之后，即'重复过讲两次'，放在句末不符合语法。 体标选用错误：'了'和'着'不能同时连用作为句末语气词或动态助词，'着'表示动作持续，与表示完成的'过'和'两次'矛盾。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "老師把重點內容重複了講兩次。",
        "is_correct": false
      },
      {
        "text": "老師把重點內容重複講兩次過。",
        "is_correct": false
      },
      {
        "text": "老師把重點內容重複講過兩次。",
        "is_correct": true
      },
      {
        "text": "老師把重點內容重複講過兩次了著。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'應放在動詞'重複'之後、補語'兩次'之前，或者句末，不能插在動詞和補語之間。 體標選用錯誤：表示過去經歷應使用'過'，但'過'應緊跟在動詞'重複'之後，即'重複過講兩次'，放在句末不符合語法。 體標選用錯誤：'了'和'著'不能同時連用作為句末語氣詞或動態助詞，'著'表示動作持續，與表示完成的'過'和'兩次'矛盾。",
    "target_word": "重複"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "重复",
  "relation": "antonym",
  "options": [
    "创新",
    "省略",
    "强调",
    "模仿"
  ],
  "correct_answer": "创新",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "反义：创新指做出前所未有的新事物，与重复（再次做同样的事）构成反义"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "創新",
      "省略",
      "強調",
      "模仿"
    ],
    "correct_answer": "創新",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "反義：創新指做出前所未有的新事物，與重複（再次做同樣的事）構成反義"
      }
    }
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

---

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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "历史总是惊人地重复着。",
      "is_correct": true
    },
    {
      "text": "这种错误我们不能再重复了。",
      "is_correct": true
    },
    {
      "text": "老师把重点内容重复讲过两次。",
      "is_correct": true
    },
    {
      "text": "这种错误我们不能再重复着。",
      "is_correct": false,
      "error_description": "“不能再……”表示对动作的否定，强调动作的发生或完成，应使用表示完成的体标“了”，而不是表示状态持续的“着”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "歷史總是驚人地重複著。",
        "is_correct": true
      },
      {
        "text": "這種錯誤我們不能再重複了。",
        "is_correct": true
      },
      {
        "text": "老師把重點內容重複講過兩次。",
        "is_correct": true
      },
      {
        "text": "這種錯誤我們不能再重複著。",
        "is_correct": false,
        "error_description": "“不能再……”表示對動作的否定，強調動作的發生或完成，應使用表示完成的體標“了”，而不是表示狀態持續的“著”。"
      }
    ]
  }
}
```

---
