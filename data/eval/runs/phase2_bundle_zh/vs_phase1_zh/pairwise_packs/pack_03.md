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


## sense 10106, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 10106, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "会议开完了，议程完毕。",
      "is_correct": true
    },
    {
      "text": "会议开完了，议程毕了。",
      "is_correct": false
    },
    {
      "text": "会议开完了，议程正毕。",
      "is_correct": false
    },
    {
      "text": "会议开完了，毕议程。",
      "is_correct": false
    }
  ],
  "explanation": "体貌错误。'毕'作为文言色彩较浓的动词，通常不单独带动态助词'了'，而多以'完毕'或'礼毕'等双音节形式出现，或在固定短语中使用。单用'毕了'口语感太强，与'毕'的正式语域冲突。 语序错误。'毕'在此处是不及物用法或使动用法的残留，但在现代汉语'议程完毕'结构中，'毕'位于名词后表示状态完成。'毕议程'不符合现代汉语常规语序，应为'结束议程'。 体标错误。'毕'表示动作已经完成，具有终结性，不能与表示进行体的'正'连用。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "會議開完了，議程完畢。",
        "is_correct": true
      },
      {
        "text": "會議開完了，議程畢了。",
        "is_correct": false
      },
      {
        "text": "會議開完了，議程正畢。",
        "is_correct": false
      },
      {
        "text": "會議開完了，畢議程。",
        "is_correct": false
      }
    ],
    "explanation": "體貌錯誤。'畢'作為文言色彩較濃的動詞，通常不單獨帶動態助詞'了'，而多以'完畢'或'禮畢'等雙音節形式出現，或在固定短語中使用。單用'畢了'口語感太強，與'畢'的正式語域衝突。 語序錯誤。'畢'在此處是不及物用法或使動用法的殘留，但在現代漢語'議程完畢'結構中，'畢'位於名詞後表示狀態完成。'畢議程'不符合現代漢語常規語序，應為'結束議程'。 體標錯誤。'畢'表示動作已經完成，具有終結性，不能與表示進行體的'正'連用。",
    "target_word": "畢"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "relation": "synonym",
  "options": [
    "开始",
    "结束",
    "继续",
    "进行"
  ],
  "correct_answer": "结束",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "完成；结束",
      "explanation": "近义词。'结束'与'毕'在表示动作完成、终止时意义相近。"
    }
  },
  "hant": {
    "word": "畢",
    "relation": "synonym",
    "options": [
      "開始",
      "結束",
      "繼續",
      "進行"
    ],
    "correct_answer": "結束",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "完成；結束",
        "explanation": "近義詞。'結束'與'畢'在表示動作完成、終止時意義相近。"
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
      "text": "信写完了，毕书写。",
      "is_correct": false
    },
    {
      "text": "信写完了，书写毕过。",
      "is_correct": false
    },
    {
      "text": "信写完了，书写毕着。",
      "is_correct": false
    },
    {
      "text": "信写完了，书写完毕。",
      "is_correct": true
    }
  ],
  "explanation": "体标错误。'毕'表示完成，是瞬间动词或结果状态，不能与表示持续状态的'着'连用。 语序错误。'毕'在此处应后置表示状态，或作为动词'完毕'的一部分。'毕书写'不符合现代汉语动宾或主谓习惯。 体貌错误。'毕'本身已包含完成义，通常不与经验体标记'过'连用，或者说'书写毕过'极其别扭，应为'书写完毕'或'曾书写完毕'。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "信寫完了，畢書寫。",
        "is_correct": false
      },
      {
        "text": "信寫完了，書寫畢過。",
        "is_correct": false
      },
      {
        "text": "信寫完了，書寫畢著。",
        "is_correct": false
      },
      {
        "text": "信寫完了，書寫完畢。",
        "is_correct": true
      }
    ],
    "explanation": "體標錯誤。'畢'表示完成，是瞬間動詞或結果狀態，不能與表示持續狀態的'著'連用。 語序錯誤。'畢'在此處應後置表示狀態，或作為動詞'完畢'的一部分。'畢書寫'不符合現代漢語動賓或主謂習慣。 體貌錯誤。'畢'本身已包含完成義，通常不與經驗體標記'過'連用，或者說'書寫畢過'極其彆扭，應為'書寫完畢'或'曾書寫完畢'。",
    "target_word": "畢"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "毕",
  "relation": "synonym",
  "options": [
    "发起",
    "开幕",
    "起始",
    "告终"
  ],
  "correct_answer": "告终",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "完成；结束",
      "explanation": "近义词。'告终'与'毕'都含有结束、完成的意思，尤其在正式语境下。"
    }
  },
  "hant": {
    "word": "畢",
    "relation": "synonym",
    "options": [
      "發起",
      "開幕",
      "起始",
      "告終"
    ],
    "correct_answer": "告終",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "完成；結束",
        "explanation": "近義詞。'告終'與'畢'都含有結束、完成的意思，尤其在正式語境下。"
      }
    }
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
      "text": "信写完了，书写毕。",
      "is_correct": false,
      "error_description": "错误句中'书写毕'不符合双音节韵律习惯，且在句末单独使用单音节文言动词'毕'显得突兀，通常需构成双音节词'完毕'或使用'礼毕'等固定搭配。正确句使用了标准的'完毕'。"
    },
    {
      "text": "信写完了，书写完毕。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "信寫完了，書寫畢。",
        "is_correct": false,
        "error_description": "錯誤句中'書寫畢'不符合雙音節韻律習慣，且在句末單獨使用單音節文言動詞'畢'顯得突兀，通常需構成雙音節詞'完畢'或使用'禮畢'等固定搭配。正確句使用了標準的'完畢'。"
      },
      {
        "text": "信寫完了，書寫完畢。",
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
      "text": "饭吃完了，用餐完毕。",
      "is_correct": true
    },
    {
      "text": "饭吃完了，用餐毕。",
      "is_correct": false,
      "error_description": "错误句中'用餐毕'同样面临单音节文言动词在句末独立使用的韵律和语域问题，不如双音节词'完毕'自然完整。正确句使用了标准的'完毕'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "飯吃完了，用餐完畢。",
        "is_correct": true
      },
      {
        "text": "飯吃完了，用餐畢。",
        "is_correct": false,
        "error_description": "錯誤句中'用餐畢'同樣面臨單音節文言動詞在句末獨立使用的韻律和語域問題，不如雙音節詞'完畢'自然完整。正確句使用了標準的'完畢'。"
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

## sense 10106, level 9

#### Pack A
### Level 9 (sense 10106, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "礼毕之后，同学们开始开心地聊天。",
  "hant": {
    "original_sentence": "禮畢之後，同學們開始開心地聊天。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "礼毕之后，同学们开始开心地聊天。",
  "chunks": [
    "礼毕之后",
    "同学们",
    "开始开心",
    "地聊天"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "开始开心",
    "地聊天",
    "同学们",
    "礼毕之后"
  ],
  "target_word": "毕",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "禮畢之後，同學們開始開心地聊天。",
    "chunks": [
      "禮畢之後",
      "同學們",
      "開始開心",
      "地聊天"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "開始開心",
      "地聊天",
      "同學們",
      "禮畢之後"
    ],
    "target_word": "畢",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "仪式终于结束，主持人宣布礼毕了。",
  "hant": {
    "original_sentence": "儀式終於結束，主持人宣佈禮畢了。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "仪式终于结束，主持人宣布礼毕了。",
  "chunks": [
    "仪式",
    "终于结束",
    "主持人",
    "宣布礼毕了"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "终于结束",
    "主持人",
    "仪式",
    "宣布礼毕了"
  ],
  "target_word": "毕",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "儀式終於結束，主持人宣佈禮畢了。",
    "chunks": [
      "儀式",
      "終於結束",
      "主持人",
      "宣佈禮畢了"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "終於結束",
      "主持人",
      "儀式",
      "宣佈禮畢了"
    ],
    "target_word": "畢",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10106, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "比赛结束了，竞赛完毕。",
  "hant": {
    "original_sentence": "比賽結束了，競賽完畢。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "比赛结束了，竞赛完毕。",
  "chunks": [
    "比赛",
    "结束",
    "了竞赛完毕"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "了竞赛完毕",
    "结束",
    "比赛"
  ],
  "target_word": "毕",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "比賽結束了，競賽完畢。",
    "chunks": [
      "比賽",
      "結束",
      "了競賽完畢"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "了競賽完畢",
      "結束",
      "比賽"
    ],
    "target_word": "畢",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "会议开完了，议程完毕。",
  "hant": {
    "original_sentence": "會議開完了，議程完畢。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "会议开完了，议程完毕。",
  "chunks": [
    "会议",
    "开完了",
    "议程",
    "完毕"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "开完了",
    "议程",
    "会议",
    "完毕"
  ],
  "target_word": "毕",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "會議開完了，議程完畢。",
    "chunks": [
      "會議",
      "開完了",
      "議程",
      "完畢"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "開完了",
      "議程",
      "會議",
      "完畢"
    ],
    "target_word": "畢",
    "chunk_count": 4
  }
}
```

---

## sense 10107, level 1

#### Pack A
### Level 1 (sense 10107, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "首创",
  "options": [
    "shǒu chuáng",
    "shǒu chuāng",
    "shǒu chuàng",
    "shōu chuàng"
  ],
  "correct_answer": "shǒu chuàng",
  "word": "首创",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "首創",
    "options": [
      "shǒu chuáng",
      "shǒu chuāng",
      "shǒu chuàng",
      "shōu chuàng"
    ],
    "correct_answer": "shǒu chuàng",
    "word": "首創",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "shǒu chuàng",
  "options": [
    "创新",
    "创造",
    "首创",
    "创作"
  ],
  "correct_answer": "首创",
  "word": "首创",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "创新": "component",
    "创造": "component",
    "创作": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "shǒu chuàng",
    "options": [
      "創新",
      "創造",
      "首創",
      "創作"
    ],
    "correct_answer": "首創",
    "word": "首創",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "创新": "component",
      "创造": "component",
      "创作": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "首创",
  "toneless_pinyin": "shou chuang",
  "full_pinyin": "shǒu chuàng",
  "options": [
    "34",
    "33",
    "32",
    "31"
  ],
  "correct_answer": "34",
  "option_labels": {
    "34": "dipping (3) + falling (4)",
    "33": "dipping (3) + dipping (3)",
    "32": "dipping (3) + rising (2)",
    "31": "dipping (3) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "首創",
    "toneless_pinyin": "shou chuang",
    "full_pinyin": "shǒu chuàng",
    "options": [
      "34",
      "33",
      "32",
      "31"
    ],
    "correct_answer": "34",
    "option_labels": {
      "34": "dipping (3) + falling (4)",
      "33": "dipping (3) + dipping (3)",
      "32": "dipping (3) + rising (2)",
      "31": "dipping (3) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10107, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "首创",
  "options": [
    "shǒu chuáng",
    "shǒu chuāng",
    "shǒu chuàng",
    "shōu chuàng"
  ],
  "correct_answer": "shǒu chuàng",
  "word": "首创",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "首創",
    "options": [
      "shǒu chuáng",
      "shǒu chuāng",
      "shǒu chuàng",
      "shōu chuàng"
    ],
    "correct_answer": "shǒu chuàng",
    "word": "首創",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "shǒu chuàng",
  "options": [
    "创造",
    "创新",
    "首创",
    "创作"
  ],
  "correct_answer": "首创",
  "word": "首创",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "创造": "component",
    "创新": "component",
    "创作": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "shǒu chuàng",
    "options": [
      "創造",
      "創新",
      "首創",
      "創作"
    ],
    "correct_answer": "首創",
    "word": "首創",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "创造": "component",
      "创新": "component",
      "创作": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "首创",
  "toneless_pinyin": "shou chuang",
  "full_pinyin": "shǒu chuàng",
  "options": [
    "34",
    "33",
    "32",
    "31"
  ],
  "correct_answer": "34",
  "option_labels": {
    "34": "dipping (3) + falling (4)",
    "33": "dipping (3) + dipping (3)",
    "32": "dipping (3) + rising (2)",
    "31": "dipping (3) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "首創",
    "toneless_pinyin": "shou chuang",
    "full_pinyin": "shǒu chuàng",
    "options": [
      "34",
      "33",
      "32",
      "31"
    ],
    "correct_answer": "34",
    "option_labels": {
      "34": "dipping (3) + falling (4)",
      "33": "dipping (3) + dipping (3)",
      "32": "dipping (3) + rising (2)",
      "31": "dipping (3) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

---

## sense 10107, level 2

#### Pack A
### Level 2 (sense 10107, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "首创",
  "pronunciation": "shǒu chuàng",
  "correct_definition": "最先创造或发明，指做别人没有做过的事情。",
  "options": [
    "形容体积、规模、数量、力量等非常大，超过一般水平。",
    "最先创造或发明，指做别人没有做过的事情。",
    "副词，表示做某事不费力气或时间很短。",
    "形容只能使用一次，不能重复使用的物品或行为。"
  ],
  "hant": {
    "word": "首創",
    "pronunciation": "shǒu chuàng",
    "correct_definition": "最先創造或發明，指做別人沒有做過的事情。",
    "options": [
      "形容體積、規模、數量、力量等非常大，超過一般水平。",
      "最先創造或發明，指做別人沒有做過的事情。",
      "副詞，表示做某事不費力氣或時間很短。",
      "形容只能使用一次，不能重複使用的物品或行為。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "首创",
  "pronunciation": "shǒu chuàng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "最先创造或发明，指做别人没有做过的事情。",
        "to collect; to bring things back, like picking flowers or fruit on a mountain",
        "供人、车、马等行走的狭长地面。",
        "把一只脚抬起来，迈过一样东西。"
      ],
      "correct_answer": "最先创造或发明，指做别人没有做过的事情。"
    }
  },
  "hant": {
    "word": "首創",
    "pronunciation": "shǒu chuàng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "最先創造或發明，指做別人沒有做過的事情。",
          "to collect; to bring things back, like picking flowers or fruit on a mountain",
          "供人、車、馬等行走的狹長地面。",
          "把一隻腳抬起來，邁過一樣東西。"
        ],
        "correct_answer": "最先創造或發明，指做別人沒有做過的事情。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10107, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "首创",
  "pronunciation": "shǒu chuàng",
  "correct_definition": "最先创造或发明，指做别人没有做过的事情。",
  "options": [
    "持续地创造新事物或提出新想法。",
    "指一个人能力范围内能够做到的最大限度；常用于‘尽自己所能’等固定搭配。",
    "最先创造或发明，指做别人没有做过的事情。",
    "绿洲是沙漠中水草丰美、适合居住的小块地区。"
  ],
  "hant": {
    "word": "首創",
    "pronunciation": "shǒu chuàng",
    "correct_definition": "最先創造或發明，指做別人沒有做過的事情。",
    "options": [
      "持續地創造新事物或提出新想法。",
      "指一個人能力範圍內能夠做到的最大限度；常用於‘儘自己所能’等固定搭配。",
      "最先創造或發明，指做別人沒有做過的事情。",
      "綠洲是沙漠中水草豐美、適合居住的小塊地區。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "首创",
  "pronunciation": "shǒu chuàng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "最先创造或发明，指做别人没有做过的事情。",
        "进入一个较大的空间或范围。",
        "最有钱的意思。",
        "cool"
      ],
      "correct_answer": "最先创造或发明，指做别人没有做过的事情。"
    }
  },
  "hant": {
    "word": "首創",
    "pronunciation": "shǒu chuàng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "最先創造或發明，指做別人沒有做過的事情。",
          "進入一個較大的空間或範圍。",
          "最有錢的意思。",
          "cool"
        ],
        "correct_answer": "最先創造或發明，指做別人沒有做過的事情。"
      }
    }
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
    "制造",
    "首创",
    "使用",
    "改进"
  ],
  "explanation": "正确。句意：宋代毕昇最先发明了泥活字。符合'最先创造'的语义。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，指做别人没有做过的事情。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更___泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "首創",
    "options": [
      "製造",
      "首創",
      "使用",
      "改進"
    ],
    "explanation": "正確。句意：宋代畢昇最先發明瞭泥活字。符合'最先創造'的語義。",
    "distractor_tags": {},
    "word_definition": "最先創造或發明，指做別人沒有做過的事情。",
    "target_word": "首創"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "谁___了这个有趣的规则？",
  "original_sentence": "谁首创了这个有趣的规则？",
  "correct_answer": "首创",
  "options": [
    "首创",
    "修改",
    "遵守",
    "制造"
  ],
  "explanation": "正确。'首创'指最先创造，符合句中询问谁制定了新规则的语境。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，指做别人没有做过的事情。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "誰___了這個有趣的規則？",
    "original_sentence": "誰首創了這個有趣的規則？",
    "correct_answer": "首創",
    "options": [
      "首創",
      "修改",
      "遵守",
      "製造"
    ],
    "explanation": "正確。'首創'指最先創造，符合句中詢問誰制定了新規則的語境。",
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

## sense 10107, level 4

#### Pack A
### Level 4 (sense 10107, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "她___了这种新舞蹈。",
  "original_sentence": "她首创了这种新舞蹈。",
  "target_word": "首创",
  "word": "首创",
  "answer": {
    "accepted": [
      "首创",
      "首创了",
      "首创过",
      "首创精神"
    ],
    "accepted_normalized": [
      "首创",
      "首创了",
      "首创过",
      "首创精神"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "她___了這種新舞蹈。",
    "original_sentence": "她首創了這種新舞蹈。",
    "target_word": "首創",
    "word": "首創",
    "answer": {
      "accepted": [
        "首創",
        "首創了",
        "首創過",
        "首創精神"
      ],
      "accepted_normalized": [
        "首創",
        "首創了",
        "首創過",
        "首創精神"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "我们支持他___这种新模式。",
  "original_sentence": "我们支持他首创这种新模式。",
  "target_word": "首创",
  "word": "首创",
  "answer": {
    "accepted": [
      "首创",
      "首创了",
      "首创过",
      "首创精神"
    ],
    "accepted_normalized": [
      "首创",
      "首创了",
      "首创过",
      "首创精神"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "我們支援他___這種新模式。",
    "original_sentence": "我們支援他首創這種新模式。",
    "target_word": "首創",
    "word": "首創",
    "answer": {
      "accepted": [
        "首創",
        "首創了",
        "首創過",
        "首創精神"
      ],
      "accepted_normalized": [
        "首創",
        "首創了",
        "首創過",
        "首創精神"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

#### Pack B
### Level 4 (sense 10107, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这家公司___了新的服务模式。",
  "original_sentence": "这家公司首创了新的服务模式。",
  "target_word": "首创",
  "word": "首创",
  "answer": {
    "accepted": [
      "首创",
      "首创了",
      "首创过",
      "首创者"
    ],
    "accepted_normalized": [
      "首创",
      "首创了",
      "首创过",
      "首创者"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這家公司___了新的服務模式。",
    "original_sentence": "這家公司首創了新的服務模式。",
    "target_word": "首創",
    "word": "首創",
    "answer": {
      "accepted": [
        "首創",
        "首創了",
        "首創過",
        "首創者"
      ],
      "accepted_normalized": [
        "首創",
        "首創了",
        "首創過",
        "首創者"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "这家店___了外卖送餐服务。",
  "original_sentence": "这家店首创了外卖送餐服务。",
  "target_word": "首创",
  "word": "首创",
  "answer": {
    "accepted": [
      "首创",
      "首创了",
      "首创过",
      "首创者"
    ],
    "accepted_normalized": [
      "首创",
      "首创了",
      "首创过",
      "首创者"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "這家店___了外賣送餐服務。",
    "original_sentence": "這家店首創了外賣送餐服務。",
    "target_word": "首創",
    "word": "首創",
    "answer": {
      "accepted": [
        "首創",
        "首創了",
        "首創過",
        "首創者"
      ],
      "accepted_normalized": [
        "首創",
        "首創了",
        "首創過",
        "首創者"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
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
      "text": "这家公司首创着这种新型环保材料。",
      "is_correct": false
    },
    {
      "text": "这家公司首创了这种新型环保材料。",
      "is_correct": true
    },
    {
      "text": "这家公司把这种新型环保材料首创了。",
      "is_correct": false
    },
    {
      "text": "这家公司正在首创这种新型环保材料。",
      "is_correct": false
    }
  ],
  "explanation": "体貌错误。'首创'是一个瞬间完成的成就动词，表示'最先发明'这一事实，通常不与表示进行时的'正在'连用，因为'发明'的过程是研发，而'首创'是结果状态。 体标错误。'首创'不能加持续体标记'着'，因为它不是持续性动作动词。 语序/句式不当。虽然语法上勉强可通，但'首创'作为谓语核心，通常直接带宾语或使用'是...首创的'强调句，'把'字句在此处显得生硬且不自然，通常用于处置性更强的动作。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "這家公司首創著這種新型環保材料。",
        "is_correct": false
      },
      {
        "text": "這家公司首創了這種新型環保材料。",
        "is_correct": true
      },
      {
        "text": "這家公司把這種新型環保材料首創了。",
        "is_correct": false
      },
      {
        "text": "這家公司正在首創這種新型環保材料。",
        "is_correct": false
      }
    ],
    "explanation": "體貌錯誤。'首創'是一個瞬間完成的成就動詞，表示'最先發明'這一事實，通常不與表示進行時的'正在'連用，因為'發明'的過程是研發，而'首創'是結果狀態。 體標錯誤。'首創'不能加持續體標記'著'，因為它不是持續性動作動詞。 語序/句式不當。雖然語法上勉強可通，但'首創'作為謂語核心，通常直接帶賓語或使用'是...首創的'強調句，'把'字句在此處顯得生硬且不自然，通常用於處置性更強的動作。",
    "target_word": "首創"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正在首创这套独特的教学方法。",
      "is_correct": false
    },
    {
      "text": "他首创了这套独特的教学方法。",
      "is_correct": true
    },
    {
      "text": "他首创得这套独特的教学方法很好。",
      "is_correct": false
    },
    {
      "text": "这套独特的教学方法被他首创了。",
      "is_correct": false
    }
  ],
  "explanation": "体貌错误：'首创'是一个瞬间完成的动作或既成事实，表示'最先创造'的状态或结果，通常不与表示进行时的'正在'连用。 语域/搭配不当：虽然语法上被动句成立，但'首创'多用于主动语态以强调主体的创新行为，被动语态在此处显得生硬且不自然，通常说'是由他首创的'。 句法错误：'首创'后直接接宾语'这套独特的教学方法'，中间不能插入结构助词'得'来连接补语，这种结构破坏了动宾关系的完整性。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "他正在首創這套獨特的教學方法。",
        "is_correct": false
      },
      {
        "text": "他首創了這套獨特的教學方法。",
        "is_correct": true
      },
      {
        "text": "他首創得這套獨特的教學方法很好。",
        "is_correct": false
      },
      {
        "text": "這套獨特的教學方法被他首創了。",
        "is_correct": false
      }
    ],
    "explanation": "體貌錯誤：'首創'是一個瞬間完成的動作或既成事實，表示'最先創造'的狀態或結果，通常不與表示進行時的'正在'連用。 語域/搭配不當：雖然語法上被動句成立，但'首創'多用於主動語態以強調主體的創新行為，被動語態在此處顯得生硬且不自然，通常說'是由他首創的'。 句法錯誤：'首創'後直接接賓語'這套獨特的教學方法'，中間不能插入結構助詞'得'來連線補語，這種結構破壞了動賓關係的完整性。",
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
      "text": "他首创过这套独特的教学方法很多次。",
      "is_correct": false,
      "error_description": "逻辑/体貌错误。'首创'意味着'第一次创造'，具有唯一性和不可重复性，不能说'很多次'。"
    },
    {
      "text": "他首创了这套独特的教学方法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他首創過這套獨特的教學方法很多次。",
        "is_correct": false,
        "error_description": "邏輯/體貌錯誤。'首創'意味著'第一次創造'，具有唯一性和不可重複性，不能說'很多次'。"
      },
      {
        "text": "他首創了這套獨特的教學方法。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10107, level 9

#### Pack A
### Level 9 (sense 10107, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "这种游戏玩法是孩子们首创的。",
  "hant": {
    "original_sentence": "這種遊戲玩法是孩子們首創的。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这种游戏玩法是孩子们首创的。",
  "chunks": [
    "这种游戏",
    "玩法是",
    "孩子们",
    "首创的"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "玩法是",
    "孩子们",
    "首创的",
    "这种游戏"
  ],
  "target_word": "首创",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這種遊戲玩法是孩子們首創的。",
    "chunks": [
      "這種遊戲",
      "玩法是",
      "孩子們",
      "首創的"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "玩法是",
      "孩子們",
      "首創的",
      "這種遊戲"
    ],
    "target_word": "首創",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这家公司首创了这种新型环保材料。",
  "hant": {
    "original_sentence": "這家公司首創了這種新型環保材料。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这家公司首创了这种新型环保材料。",
  "chunks": [
    "这家公司",
    "首创了",
    "这种新型",
    "环保材料"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "环保材料",
    "首创了",
    "这家公司",
    "这种新型"
  ],
  "target_word": "首创",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這家公司首創了這種新型環保材料。",
    "chunks": [
      "這家公司",
      "首創了",
      "這種新型",
      "環保材料"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "環保材料",
      "首創了",
      "這家公司",
      "這種新型"
    ],
    "target_word": "首創",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10107, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他首创的新玩法很有趣。",
  "hant": {
    "original_sentence": "他首創的新玩法很有趣。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他首创的新玩法很有趣。",
  "chunks": [
    "他首创",
    "的新",
    "玩法很有趣"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "的新",
    "玩法很有趣",
    "他首创"
  ],
  "target_word": "首创",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他首創的新玩法很有趣。",
    "chunks": [
      "他首創",
      "的新",
      "玩法很有趣"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "的新",
      "玩法很有趣",
      "他首創"
    ],
    "target_word": "首創",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "我们首创了班级新规矩。",
  "hant": {
    "original_sentence": "我們首創了班級新規矩。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "我们首创了班级新规矩。",
  "chunks": [
    "我们首创",
    "了班级",
    "新规矩"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "我们首创",
    "新规矩",
    "了班级"
  ],
  "target_word": "首创",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "我們首創了班級新規矩。",
    "chunks": [
      "我們首創",
      "了班級",
      "新規矩"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "我們首創",
      "新規矩",
      "了班級"
    ],
    "target_word": "首創",
    "chunk_count": 3
  }
}
```

---
