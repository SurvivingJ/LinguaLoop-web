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
      "text": "这场精彩的演讲终于言毕了，台下顿时响起了经久不息的热烈掌声。",
      "is_correct": false
    },
    {
      "text": "这场精彩的演讲终于言毕，台下顿时响起了经久不息的热烈掌声。",
      "is_correct": true
    },
    {
      "text": "终于言毕这场精彩的演讲，台下顿时响起了经久不息的热烈掌声。",
      "is_correct": false
    },
    {
      "text": "这场精彩的演讲终于言毕出，台下顿时响起了经久不息的热烈掌声。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：“毕”本身已包含“完成、结束”的完成体意义，后面不能再加动态助词“了”，造成语义重复和语法冗余。 语序错误：“言毕”是不及物用法或后接宾语时结构不同，此处将宾语“这场精彩的演讲”前置导致动宾结构破坏，应改为“这场精彩的演讲终于言毕”。 方向/结果补语误用：“毕”表示动作完成，不能与趋向补语“出”连用构成“毕出”，属于生造词或补语误用。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "這場精彩的演講終於言畢了，臺下頓時響起了經久不息的熱烈掌聲。",
        "is_correct": false
      },
      {
        "text": "這場精彩的演講終於言畢，臺下頓時響起了經久不息的熱烈掌聲。",
        "is_correct": true
      },
      {
        "text": "終於言畢這場精彩的演講，臺下頓時響起了經久不息的熱烈掌聲。",
        "is_correct": false
      },
      {
        "text": "這場精彩的演講終於言畢出，臺下頓時響起了經久不息的熱烈掌聲。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：“畢”本身已包含“完成、結束”的完成體意義，後面不能再加動態助詞“了”，造成語義重複和語法冗餘。 語序錯誤：“言畢”是不及物用法或後接賓語時結構不同，此處將賓語“這場精彩的演講”前置導致動賓結構破壞，應改為“這場精彩的演講終於言畢”。 方向/結果補語誤用：“畢”表示動作完成，不能與趨向補語“出”連用構成“畢出”，屬於生造詞或補語誤用。",
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
    "持续",
    "中止",
    "进行",
    "开始"
  ],
  "correct_answer": "开始",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "完成；结束。",
      "explanation": "反义：「毕」表完成、结束，「开始」表起始，二者构成反义关系"
    }
  },
  "hant": {
    "word": "畢",
    "relation": "antonym",
    "options": [
      "持續",
      "中止",
      "進行",
      "開始"
    ],
    "correct_answer": "開始",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "完成；結束。",
        "explanation": "反義：「畢」表完成、結束，「開始」表起始，二者構成反義關係"
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
      "text": "一天的学习被毕，他整理好书本，感到十分充实和满足。",
      "is_correct": false
    },
    {
      "text": "一天的学习毕起来，他整理好书本，感到十分充实和满足。",
      "is_correct": false
    },
    {
      "text": "一天的学习告毕，他整理好书本，感到十分充实和满足。",
      "is_correct": true
    },
    {
      "text": "毕一天的学习，他整理好书本，感到十分充实和满足。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“毕”本身已包含完成的语义，不能与表示被动的“被”字连用。 语序错误：“毕”作为动词应位于宾语“一天的学习”之后，不能前置。 方向补语误用：“起来”表示动作开始或向上，与“毕”表示完成的语义相冲突。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "一天的學習被畢，他整理好書本，感到十分充實和滿足。",
        "is_correct": false
      },
      {
        "text": "一天的學習畢起來，他整理好書本，感到十分充實和滿足。",
        "is_correct": false
      },
      {
        "text": "一天的學習告畢，他整理好書本，感到十分充實和滿足。",
        "is_correct": true
      },
      {
        "text": "畢一天的學習，他整理好書本，感到十分充實和滿足。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“畢”本身已包含完成的語義，不能與表示被動的“被”字連用。 語序錯誤：“畢”作為動詞應位於賓語“一天的學習”之後，不能前置。 方向補語誤用：“起來”表示動作開始或向上，與“畢”表示完成的語義相沖突。",
    "target_word": "畢"
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
      "text": "随着最后一门专业课考核结束，他大学四年的学业也终于圆满礼毕。",
      "is_correct": true
    },
    {
      "text": "这项浩大的古籍修复工程历时三年，如今各项工序均已告毕，专家们无不感到欣慰。",
      "is_correct": true
    },
    {
      "text": "老师讲完课，说：“下课！”同学们齐声回应，言毕便走出了教室。",
      "is_correct": true
    },
    {
      "text": "他把作业写毕了，长舒了一口气，准备去休息。",
      "is_correct": false,
      "error_description": "“毕”本身已包含“完成、结束”的结果意义，作结果补语时后面不能再加动态助词“了”，否则会造成语义重复和语法冗余。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "隨著最後一門專業課考核結束，他大學四年的學業也終於圓滿禮畢。",
        "is_correct": true
      },
      {
        "text": "這項浩大的古籍修復工程歷時三年，如今各項工序均已告畢，專家們無不感到欣慰。",
        "is_correct": true
      },
      {
        "text": "老師講完課，說：“下課！”同學們齊聲回應，言畢便走出了教室。",
        "is_correct": true
      },
      {
        "text": "他把作業寫畢了，長舒了一口氣，準備去休息。",
        "is_correct": false,
        "error_description": "“畢”本身已包含“完成、結束”的結果意義，作結果補語時後面不能再加動態助詞“了”，否則會造成語義重複和語法冗餘。"
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
      "text": "一天的学习告毕，他整理好书本，感到十分充实和满足。",
      "is_correct": true
    },
    {
      "text": "会议各项议程均已告毕，大家纷纷交流了各自的观点和看法。",
      "is_correct": true
    },
    {
      "text": "昨天的会议各项议程均已告毕了，大家纷纷交流了各自的观点和看法。",
      "is_correct": false,
      "error_description": "体标误用：'告毕' 本身已包含动作完成、结束的语义，其后不能再添加表示完成的动态助词 '了'，否则会造成语义重复与语法冗余。"
    },
    {
      "text": "演出礼毕，演员们纷纷走到台前，向台下热情的观众鞠躬致谢。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "一天的學習告畢，他整理好書本，感到十分充實和滿足。",
        "is_correct": true
      },
      {
        "text": "會議各項議程均已告畢，大家紛紛交流了各自的觀點和看法。",
        "is_correct": true
      },
      {
        "text": "昨天的會議各項議程均已告畢了，大家紛紛交流了各自的觀點和看法。",
        "is_correct": false,
        "error_description": "體標誤用：'告畢' 本身已包含動作完成、結束的語義，其後不能再新增表示完成的動態助詞 '了'，否則會造成語義重複與語法冗餘。"
      },
      {
        "text": "演出禮畢，演員們紛紛走到臺前，向臺下熱情的觀眾鞠躬致謝。",
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
    "发现",
    "首创",
    "制造",
    "开启"
  ],
  "explanation": "正确。'首创'指最先创造或发明，符合毕昇发明泥活字的语境。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，指做别人没有做过的事情。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更___泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "首創",
    "options": [
      "發現",
      "首創",
      "製造",
      "開啟"
    ],
    "explanation": "正確。'首創'指最先創造或發明，符合畢昇發明泥活字的語境。",
    "distractor_tags": {},
    "word_definition": "最先創造或發明，指做別人沒有做過的事情。",
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
      "text": "方法的首创她是。",
      "is_correct": false
    },
    {
      "text": "这是她首创的方法。",
      "is_correct": true
    },
    {
      "text": "这是她首创出来的方法。",
      "is_correct": false
    },
    {
      "text": "这是她首创了的方法。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：'首创'本身已包含'最先'的完成意味，其后不应再加动态助词'了'，且'了'放在'首创'和'的'之间破坏了'是……的'强调句型结构。 语序错误：汉语的基本语序为主谓宾，将宾语'方法'提前至句首且谓语'是'置于句末，破坏了正常的'主题—评论'结构，导致句子不通顺。 结果补语误用：'首创'意为最先创造，其动作结果已内含在词义中，不能再附加'出来'作为结果补语，否则会造成语义冗余和搭配不当。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "方法的首創她是。",
        "is_correct": false
      },
      {
        "text": "這是她首創的方法。",
        "is_correct": true
      },
      {
        "text": "這是她首創出來的方法。",
        "is_correct": false
      },
      {
        "text": "這是她首創了的方法。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：'首創'本身已包含'最先'的完成意味，其後不應再加動態助詞'了'，且'了'放在'首創'和'的'之間破壞了'是……的'強調句型結構。 語序錯誤：漢語的基本語序為主謂賓，將賓語'方法'提前至句首且謂語'是'置於句末，破壞了正常的'主題—評論'結構，導致句子不通順。 結果補語誤用：'首創'意為最先創造，其動作結果已內含在詞義中，不能再附加'出來'作為結果補語，否則會造成語義冗餘和搭配不當。",
    "target_word": "首創"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "同学们均支持他首创出来此法。",
      "is_correct": false
    },
    {
      "text": "同学们均支持他首创此法。",
      "is_correct": true
    },
    {
      "text": "同学们均支持他首创着此法。",
      "is_correct": false
    },
    {
      "text": "同学们均支持首创他此法。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。'首创'表示一次性的完成动作（最先创造），不能与表示动作持续或状态保持的体标记'着'连用。 结果补语误用。'首创'本身已包含'创造'的动作及'首次'的结果意义，后面再加'出来'属于语义重复且搭配不当，通常直接接宾语。 语序错误。'首创'是及物动词，其宾语'此法'应紧跟在动词之后，而施事者'他'应作为主语或定语放在动词前，原句破坏了正常的动宾语序。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "同學們均支援他首創出來此法。",
        "is_correct": false
      },
      {
        "text": "同學們均支援他首創此法。",
        "is_correct": true
      },
      {
        "text": "同學們均支援他首創著此法。",
        "is_correct": false
      },
      {
        "text": "同學們均支援首創他此法。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。'首創'表示一次性的完成動作（最先創造），不能與表示動作持續或狀態保持的體標記'著'連用。 結果補語誤用。'首創'本身已包含'創造'的動作及'首次'的結果意義，後面再加'出來'屬於語義重複且搭配不當，通常直接接賓語。 語序錯誤。'首創'是及物動詞，其賓語'此法'應緊跟在動詞之後，而施事者'他'應作為主語或定語放在動詞前，原句破壞了正常的動賓語序。",
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
      "text": "他首创着一种新玩法。",
      "is_correct": false,
      "error_description": "“首创”表示最先创造，是一个瞬间完成的动作，不能与表示动作持续的体标记“着”连用，应改为表示完成的“了”。"
    },
    {
      "text": "这项活动由他首创。",
      "is_correct": true
    },
    {
      "text": "他首创了一种新玩法。",
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
        "text": "他首創著一種新玩法。",
        "is_correct": false,
        "error_description": "“首創”表示最先創造，是一個瞬間完成的動作，不能與表示動作持續的體標記“著”連用，應改為表示完成的“了”。"
      },
      {
        "text": "這項活動由他首創。",
        "is_correct": true
      },
      {
        "text": "他首創了一種新玩法。",
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师表扬他首创该教学法。",
      "is_correct": true
    },
    {
      "text": "他首创了昨天一种新玩法。",
      "is_correct": false,
      "error_description": "时间状语“昨天”位置错误。在汉语中，表示时间的词语通常应放在主语之后、动词之前，不能放在动词和宾语之间。"
    },
    {
      "text": "他向大家宣布他首创此法。",
      "is_correct": true
    },
    {
      "text": "同学们均支持他首创此法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師表揚他首創該教學法。",
        "is_correct": true
      },
      {
        "text": "他首創了昨天一種新玩法。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”位置錯誤。在漢語中，表示時間的詞語通常應放在主語之後、動詞之前，不能放在動詞和賓語之間。"
      },
      {
        "text": "他向大家宣佈他首創此法。",
        "is_correct": true
      },
      {
        "text": "同學們均支援他首創此法。",
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
    "可",
    "咳",
    "科",
    "客"
  ],
  "correct_answer": "可",
  "explanation": "“可”读第三声（kě），在此表示许可或可能，常用于口语商量或征求意见。",
  "distractor_explanations": {
    "科": "“科”读第一声（kē），指学科、类别或行政单位，与目标词声调及意义均不同。",
    "咳": "“咳”读第二声（ké），指咳嗽或叹气声，声调不同且词义完全无关。",
    "客": "“客”读第四声（kè），指客人或旅客，声调不同且无法在此语境中表达许可或可能。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "可",
    "pronunciation": "kě",
    "ipa": "[kʰɤ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "可",
      "咳",
      "科",
      "客"
    ],
    "correct_answer": "可",
    "explanation": "“可”讀第三聲（kě），在此表示許可或可能，常用於口語商量或徵求意見。",
    "distractor_explanations": {
      "科": "“科”讀第一聲（kē），指學科、類別或行政單位，與目標詞聲調及意義均不同。",
      "咳": "“咳”讀第二聲（ké），指咳嗽或嘆氣聲，聲調不同且詞義完全無關。",
      "客": "“客”讀第四聲（kè），指客人或旅客，聲調不同且無法在此語境中表達許可或可能。"
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

## sense 10110, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 10110, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "周末我们可去公园玩着。",
      "is_correct": false
    },
    {
      "text": "周末我们可去公园玩。",
      "is_correct": true
    },
    {
      "text": "周末我们可去公园玩得。",
      "is_correct": false
    },
    {
      "text": "周末我们公园可去玩。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：情态动词“可”后接动作时，不应使用表示状态持续的体标记“着”，应直接说“可去公园玩”。 语序错误：地点状语“公园”应放在动词“去”之后作为宾语，或放在“可”之前作状语，当前语序破坏了正常的句法结构。 体标位置/选用错误：结构助词“得”通常用于引出程度或结果补语，此处无补语成分，放在句末属于语法和体标记误用。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "週末我們可去公園玩著。",
        "is_correct": false
      },
      {
        "text": "週末我們可去公園玩。",
        "is_correct": true
      },
      {
        "text": "週末我們可去公園玩得。",
        "is_correct": false
      },
      {
        "text": "週末我們公園可去玩。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：情態動詞“可”後接動作時，不應使用表示狀態持續的體標記“著”，應直接說“可去公園玩”。 語序錯誤：地點狀語“公園”應放在動詞“去”之後作為賓語，或放在“可”之前作狀語，當前語序破壞了正常的句法結構。 體標位置/選用錯誤：結構助詞“得”通常用於引出程度或結果補語，此處無補語成分，放在句末屬於語法和體標記誤用。",
    "target_word": "可"
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "他今天没来上课，可是生病了没。",
      "is_correct": false
    },
    {
      "text": "他今天没来上课，可是生病了过。",
      "is_correct": false
    },
    {
      "text": "可是生病了，他今天没来上课。",
      "is_correct": false
    },
    {
      "text": "他今天没来上课，可是生病了？",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误。句末的“没”不能与表示猜测的“可是”搭配，应改为疑问语气词“吗”或“呢”。 语序错误。表示猜测的“可是”引导的分句应放在结果或现象之后，原句因果/推测逻辑颠倒。 体标位置/选用错误。句末的“过”表示经历，不能用于表示对当前情况的猜测，应改为“了吗”。",
  "target_word": "可",
  "hant": {
    "sentences": [
      {
        "text": "他今天沒來上課，可是生病了沒。",
        "is_correct": false
      },
      {
        "text": "他今天沒來上課，可是生病了過。",
        "is_correct": false
      },
      {
        "text": "可是生病了，他今天沒來上課。",
        "is_correct": false
      },
      {
        "text": "他今天沒來上課，可是生病了？",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤。句末的“沒”不能與表示猜測的“可是”搭配，應改為疑問語氣詞“嗎”或“呢”。 語序錯誤。表示猜測的“可是”引導的分句應放在結果或現象之後，原句因果/推測邏輯顛倒。 體標位置/選用錯誤。句末的“過”表示經歷，不能用於表示對當前情況的猜測，應改為“了嗎”。",
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
      "text": "这意味着，同一代理可在不同计算平台间无缝迁移，其长期记忆与行为模式不受底层模型更迭的影响。",
      "is_correct": true
    },
    {
      "text": "可在不同计算平台间同一代理无缝迁移。",
      "is_correct": false,
      "error_description": "语序错误。情态动词“可”及其引导的谓语部分应紧跟在主语“同一代理”之后，地点状语“在不同计算平台间”之前，不能将主语置于状语和情态动词之后。"
    },
    {
      "text": "这周末天气不错，咱们去爬山可好？",
      "is_correct": true
    },
    {
      "text": "这种“技术公地”的繁荣，暗示着一种可能的未来：个人AI代理不再由科技巨头垄断定义，而是成为可被公众共同塑造的认知基础设施。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這意味著，同一代理可在不同計算平臺間無縫遷移，其長期記憶與行為模式不受底層模型更迭的影響。",
        "is_correct": true
      },
      {
        "text": "可在不同計算平臺間同一代理無縫遷移。",
        "is_correct": false,
        "error_description": "語序錯誤。情態動詞“可”及其引導的謂語部分應緊跟在主語“同一代理”之後，地點狀語“在不同計算平臺間”之前，不能將主語置於狀語和情態動詞之後。"
      },
      {
        "text": "這週末天氣不錯，咱們去爬山可好？",
        "is_correct": true
      },
      {
        "text": "這種“技術公地”的繁榮，暗示著一種可能的未來：個人AI代理不再由科技巨頭壟斷定義，而是成為可被公眾共同塑造的認知基礎設施。",
        "is_correct": true
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
      "text": "他今天没来上班，可是生病了？",
      "is_correct": true
    },
    {
      "text": "他今天没来上班，可是生病了？",
      "is_correct": false,
      "error_description": "错误类型：疑问语气词缺失。句中的“可是”表示“是不是”或“难道是”，用于提出疑问，句末必须加上疑问语气词“吗”才能构成完整的疑问句，否则句子结构不完整。"
    },
    {
      "text": "他今天没来上课，可是生病了？",
      "is_correct": true
    },
    {
      "text": "你到了那边，可要记得给家里打个电话。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他今天沒來上班，可是生病了？",
        "is_correct": true
      },
      {
        "text": "他今天沒來上班，可是生病了？",
        "is_correct": false,
        "error_description": "錯誤型別：疑問語氣詞缺失。句中的“可是”表示“是不是”或“難道是”，用於提出疑問，句末必須加上疑問語氣詞“嗎”才能構成完整的疑問句，否則句子結構不完整。"
      },
      {
        "text": "他今天沒來上課，可是生病了？",
        "is_correct": true
      },
      {
        "text": "你到了那邊，可要記得給家裡打個電話。",
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
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复着排版的技术先河。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的先河技术。",
      "is_correct": false
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了重复可排版的技术先河。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'重复'作为动词，后面不能直接加动态助词'着'来表示技术特征，应去掉'着'或改为'可重复的'。 语序错误。'可'作为能愿动词，必须放在动词'重复'之前，正确语序应为'可重复排版'。 语序错误。'技术'是'先河'的中心语，'技术先河'为固定搭配，不能颠倒为'先河技术'，破坏了名词短语的内部结构。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複著排版的技術先河。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的先河技術。",
        "is_correct": false
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了重複可排版的技術先河。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'重複'作為動詞，後面不能直接加動態助詞'著'來表示技術特徵，應去掉'著'或改為'可重複的'。 語序錯誤。'可'作為能願動詞，必須放在動詞'重複'之前，正確語序應為'可重複排版'。 語序錯誤。'技術'是'先河'的中心語，'技術先河'為固定搭配，不能顛倒為'先河技術'，破壞了名詞短語的內部結構。",
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
    "停止",
    "创新",
    "模仿",
    "继续"
  ],
  "correct_answer": "创新",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "反义：创新指创造新事物，与重复（再次进行）构成反义"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "停止",
      "創新",
      "模仿",
      "繼續"
    ],
    "correct_answer": "創新",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "反義：創新指創造新事物，與重複（再次進行）構成反義"
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
      "text": "我们不想重复这种错误。",
      "is_correct": true
    },
    {
      "text": "我们不想把这种错误重复。",
      "is_correct": false
    },
    {
      "text": "我们不想重复了这种错误。",
      "is_correct": false
    },
    {
      "text": "我们不想重复出来这种错误。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：'重复'作为及物动词带宾语时，动态助词'了'应放在句末或宾语之后，不能直接插在动词和宾语之间。 语序错误：使用'把'字句时，动词后通常需要有补语或动态助词（如'重复一遍'），单用'重复'导致句子结构不完整、不自然。 结果补语误用：'重复'本身已包含'再次'的语义，不需要加趋向/结果补语'出来'，且'重复出来'搭配不当。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "我們不想重複這種錯誤。",
        "is_correct": true
      },
      {
        "text": "我們不想把這種錯誤重複。",
        "is_correct": false
      },
      {
        "text": "我們不想重複了這種錯誤。",
        "is_correct": false
      },
      {
        "text": "我們不想重複出來這種錯誤。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：'重複'作為及物動詞帶賓語時，動態助詞'了'應放在句末或賓語之後，不能直接插在動詞和賓語之間。 語序錯誤：使用'把'字句時，動詞後通常需要有補語或動態助詞（如'重複一遍'），單用'重複'導致句子結構不完整、不自然。 結果補語誤用：'重複'本身已包含'再次'的語義，不需要加趨向/結果補語'出來'，且'重複出來'搭配不當。",
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
    "继续",
    "停止",
    "取消",
    "创新"
  ],
  "correct_answer": "停止",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "反义：目标词表示动作再次进行，而该词表示动作不再进行"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "繼續",
      "停止",
      "取消",
      "創新"
    ],
    "correct_answer": "停止",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "反義：目標詞表示動作再次進行，而該詞表示動作不再進行"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "它的设计像一个绿色的箭头圆圈，表示这个步骤可以重复。",
      "is_correct": true
    },
    {
      "text": "这个过程会重复很多次，直到飞机飞得又快又稳又安全。",
      "is_correct": true
    },
    {
      "text": "它的设计像一个绿色的箭头圆圈，表示这个步骤可以重复着。",
      "is_correct": false,
      "error_description": "错误类型：体标选用错误。'可以'后面表示能力或可能性，应直接加动词原形，不需要加表示动作持续的体标'着'。"
    },
    {
      "text": "这个标志的三个箭头代表实验的三个步骤：初步测试、重复实验、得出结论。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "它的設計像一個綠色的箭頭圓圈，表示這個步驟可以重複。",
        "is_correct": true
      },
      {
        "text": "這個過程會重複很多次，直到飛機飛得又快又穩又安全。",
        "is_correct": true
      },
      {
        "text": "它的設計像一個綠色的箭頭圓圈，表示這個步驟可以重複著。",
        "is_correct": false,
        "error_description": "錯誤型別：體標選用錯誤。'可以'後面表示能力或可能性，應直接加動詞原形，不需要加表示動作持續的體標'著'。"
      },
      {
        "text": "這個標誌的三個箭頭代表實驗的三個步驟：初步測試、重複實驗、得出結論。",
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
      "text": "他重复了说着同样的话。",
      "is_correct": false,
      "error_description": "体标位置错误。在表示动作持续或状态保持的“重复+动词”结构中，动态助词“了”不能插在“重复”和后面的动词之间，应直接去掉“了”，或者将“着”改为“了”并调整语序（如“他重复说了同样的话”）。"
    },
    {
      "text": "这个故事他重复讲过。",
      "is_correct": true
    },
    {
      "text": "我们不想重复这种错误。",
      "is_correct": true
    },
    {
      "text": "请不要重复别人的观点。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他重複了說著同樣的話。",
        "is_correct": false,
        "error_description": "體標位置錯誤。在表示動作持續或狀態保持的“重複+動詞”結構中，動態助詞“了”不能插在“重複”和後面的動詞之間，應直接去掉“了”，或者將“著”改為“了”並調整語序（如“他重複說了同樣的話”）。"
      },
      {
        "text": "這個故事他重複講過。",
        "is_correct": true
      },
      {
        "text": "我們不想重複這種錯誤。",
        "is_correct": true
      },
      {
        "text": "請不要重複別人的觀點。",
        "is_correct": true
      }
    ]
  }
}
```

---
