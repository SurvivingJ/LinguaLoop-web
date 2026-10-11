# Pairwise review pack 05

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


## sense 10300, level 7

#### Pack A
### Level 7 (sense 10300, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "长城在中国北方，它很长很长。",
      "is_correct": true
    },
    {
      "text": "她的头发很长着，看起来很有艺术感。",
      "is_correct": false,
      "error_description": "形容词“长”表示事物的固有属性或状态，不能与表示动作持续的动态助词“着”连用，应直接去掉“着”。"
    },
    {
      "text": "他的头发很长，看起来很有艺术感。",
      "is_correct": true
    },
    {
      "text": "这条裙子太长了，我需要去改短。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "長城在中國北方，它很長很長。",
        "is_correct": true
      },
      {
        "text": "她的頭髮很長著，看起來很有藝術感。",
        "is_correct": false,
        "error_description": "形容詞“長”表示事物的固有屬性或狀態，不能與表示動作持續的動態助詞“著”連用，應直接去掉“著”。"
      },
      {
        "text": "他的頭髮很長，看起來很有藝術感。",
        "is_correct": true
      },
      {
        "text": "這條裙子太長了，我需要去改短。",
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
      "text": "这条马路很长，我们走了很久昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”位置错误。在汉语中，表示过去的时间状语通常放在主语之后、谓语动词之前，不能放在句末。"
    },
    {
      "text": "冬天夜长，大家要注意保暖。",
      "is_correct": true
    },
    {
      "text": "这条河很长，流过很多个城市。",
      "is_correct": true
    },
    {
      "text": "这条路很长，我们要走很久。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這條馬路很長，我們走了很久昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”位置錯誤。在漢語中，表示過去的時間狀語通常放在主語之後、謂語動詞之前，不能放在句末。"
      },
      {
        "text": "冬天夜長，大家要注意保暖。",
        "is_correct": true
      },
      {
        "text": "這條河很長，流過很多個城市。",
        "is_correct": true
      },
      {
        "text": "這條路很長，我們要走很久。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10300, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这条路长很，我们走了很久。",
      "is_correct": false,
      "error_description": "程度副词“很”应该放在形容词“长”的前面，不能放在后面。正确语序为“很长”。"
    },
    {
      "text": "长城在中国北方，它很长很长。",
      "is_correct": true
    },
    {
      "text": "这条河流很长，流经了许多的省份。",
      "is_correct": true
    },
    {
      "text": "这条路很长，我们走了很久。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這條路長很，我們走了很久。",
        "is_correct": false,
        "error_description": "程度副詞“很”應該放在形容詞“長”的前面，不能放在後面。正確語序為“很長”。"
      },
      {
        "text": "長城在中國北方，它很長很長。",
        "is_correct": true
      },
      {
        "text": "這條河流很長，流經了許多的省份。",
        "is_correct": true
      },
      {
        "text": "這條路很長，我們走了很久。",
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
      "text": "我们有一段很长的回忆，永远忘不了。",
      "is_correct": true
    },
    {
      "text": "长不一定就是好，短也有短的优点。",
      "is_correct": true
    },
    {
      "text": "这条裙子长太了，你去换一条短的吧。",
      "is_correct": false,
      "error_description": "‘太……了’是固定搭配，程度副词‘太’必须放在形容词‘长’的前面，且句末需要有语气词‘了’。不能说‘长太了’。"
    },
    {
      "text": "他把故事讲得很长，大家都听困了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們有一段很長的回憶，永遠忘不了。",
        "is_correct": true
      },
      {
        "text": "長不一定就是好，短也有短的優點。",
        "is_correct": true
      },
      {
        "text": "這條裙子長太了，你去換一條短的吧。",
        "is_correct": false,
        "error_description": "‘太……了’是固定搭配，程度副詞‘太’必須放在形容詞‘長’的前面，且句末需要有語氣詞‘了’。不能說‘長太了’。"
      },
      {
        "text": "他把故事講得很長，大家都聽困了。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10353, level 1

#### Pack A
### Level 1 (sense 10353, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "再",
  "pronunciation": "zài",
  "ipa": "[tsaɪ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "栽",
    "灾",
    "再",
    "宰"
  ],
  "correct_answer": "再",
  "explanation": "正确选项。读音为第四声（zài），表示动作或状态的重复或继续。",
  "distractor_explanations": {
    "栽": "声调为第一声（zāi），意为种植或跌倒，与目标词第四声（zài）声调不同，意义完全不同。",
    "宰": "声调为第三声（zǎi），意为杀牲畜或主管，与目标词第四声（zài）声调不同，意义完全不同。",
    "灾": "声调为第一声（zāi），意为祸害或自然灾害，与目标词第四声（zài）声调不同，意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "再",
    "pronunciation": "zài",
    "ipa": "[tsaɪ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "栽",
      "災",
      "再",
      "宰"
    ],
    "correct_answer": "再",
    "explanation": "正確選項。讀音為第四聲（zài），表示動作或狀態的重複或繼續。",
    "distractor_explanations": {
      "栽": "聲調為第一聲（zāi），意為種植或跌倒，與目標詞第四聲（zài）聲調不同，意義完全不同。",
      "宰": "聲調為第三聲（zǎi），意為殺牲畜或主管，與目標詞第四聲（zài）聲調不同，意義完全不同。",
      "灾": "聲調為第一聲（zāi），意為禍害或自然災害，與目標詞第四聲（zài）聲調不同，意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10353, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "再",
  "pronunciation": "zài",
  "ipa": "[t͡sai˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "栽",
    "宰",
    "崽",
    "再"
  ],
  "correct_answer": "再",
  "explanation": "正确。'再'读第四声（zài），表示动作或状态的重复或继续。",
  "distractor_explanations": {
    "栽": "声调混淆。'栽'读第一声（zāi），意为种植，声调不同导致意义改变。",
    "宰": "声调混淆。'宰'读第三声（zǎi），意为杀牲畜或主管，声调不同导致意义改变。",
    "崽": "声调混淆。'崽'读第三声（zǎi），意为小孩或动物幼崽，声调不同导致意义改变。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "再",
    "pronunciation": "zài",
    "ipa": "[t͡sai˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "栽",
      "宰",
      "崽",
      "再"
    ],
    "correct_answer": "再",
    "explanation": "正確。'再'讀第四聲（zài），表示動作或狀態的重複或繼續。",
    "distractor_explanations": {
      "栽": "聲調混淆。'栽'讀第一聲（zāi），意為種植，聲調不同導致意義改變。",
      "宰": "聲調混淆。'宰'讀第三聲（zǎi），意為殺牲畜或主管，聲調不同導致意義改變。",
      "崽": "聲調混淆。'崽'讀第三聲（zǎi），意為小孩或動物幼崽，聲調不同導致意義改變。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10353, level 6

#### Pack A
### Level 6 (sense 10353, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "你把作业写完，再去着玩手机游戏。",
      "is_correct": false
    },
    {
      "text": "你把作业写完，再着去玩手机游戏。",
      "is_correct": false
    },
    {
      "text": "你把作业写完，再去玩手机游戏。",
      "is_correct": true
    },
    {
      "text": "再你把作业写完，去玩手机游戏。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：'着'表示动作正在进行或状态持续，不能用在表示顺承关系的副词'再'之后，此处应直接接动词'玩'。 语序错误：副词'再'及其引导的顺承动作应放在条件分句之后，不能放在句首修饰整个条件句。 体标位置/选用错误：'去'和'玩'之间不需要加'着'，'去玩'表示目的或连续动作，加'着'会破坏动作的连贯性和未然状态。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "你把作業寫完，再去著玩手機遊戲。",
        "is_correct": false
      },
      {
        "text": "你把作業寫完，再著去玩手機遊戲。",
        "is_correct": false
      },
      {
        "text": "你把作業寫完，再去玩手機遊戲。",
        "is_correct": true
      },
      {
        "text": "再你把作業寫完，去玩手機遊戲。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：'著'表示動作正在進行或狀態持續，不能用在表示順承關係的副詞'再'之後，此處應直接接動詞'玩'。 語序錯誤：副詞'再'及其引導的順承動作應放在條件分句之後，不能放在句首修飾整個條件句。 體標位置/選用錯誤：'去'和'玩'之間不需要加'著'，'去玩'表示目的或連續動作，加'著'會破壞動作的連貫性和未然狀態。",
    "target_word": "再"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "再",
  "relation": "antonym",
  "options": [
    "已",
    "刚",
    "又",
    "还"
  ],
  "correct_answer": "已",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或状态的重复或继续。",
      "explanation": "反义项：「已」表动作已完成，「再」表动作重复或继续，二者在时间指向上相反"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "已",
      "剛",
      "又",
      "還"
    ],
    "correct_answer": "已",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或狀態的重複或繼續。",
        "explanation": "反義項：「已」表動作已完成，「再」表動作重複或繼續，二者在時間指向上相反"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "再",
  "relation": "antonym",
  "options": [
    "刚",
    "更",
    "已",
    "不再"
  ],
  "correct_answer": "不再",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或状态的重复或继续。",
      "explanation": "反义：表示动作停止或不继续，与表重复继续的“再”相对"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "剛",
      "更",
      "已",
      "不再"
    ],
    "correct_answer": "不再",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或狀態的重複或繼續。",
        "explanation": "反義：表示動作停止或不繼續，與表重複繼續的“再”相對"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10353, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这句话我没听清，请你再说说一遍好吗？",
      "is_correct": false
    },
    {
      "text": "这句话我没听清，请你再说了遍好吗？",
      "is_correct": false
    },
    {
      "text": "这句话我没听清，请你再说一遍好吗？",
      "is_correct": true
    },
    {
      "text": "这句话我没听清，请你一遍再说好吗？",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：'再'表示动作的重复或继续，通常用于未然语境，后面不能直接跟表示完成的动态助词'了'，应去掉'了'。 语序错误：数量短语'一遍'作为动量补语，应该紧跟在动词'说'之后，不能放在'再'和'说'之间，破坏了固定语序。 搭配错误：动词重叠'说说'表示动作短暂或尝试，不能再与表示完整次数的动量补语'一遍'连用，两者在体貌上相互冲突。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "這句話我沒聽清，請你再說說一遍好嗎？",
        "is_correct": false
      },
      {
        "text": "這句話我沒聽清，請你再說了遍好嗎？",
        "is_correct": false
      },
      {
        "text": "這句話我沒聽清，請你再說一遍好嗎？",
        "is_correct": true
      },
      {
        "text": "這句話我沒聽清，請你一遍再說好嗎？",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：'再'表示動作的重複或繼續，通常用於未然語境，後面不能直接跟表示完成的動態助詞'了'，應去掉'了'。 語序錯誤：數量短語'一遍'作為動量補語，應該緊跟在動詞'說'之後，不能放在'再'和'說'之間，破壞了固定語序。 搭配錯誤：動詞重疊'說說'表示動作短暫或嘗試，不能再與表示完整次數的動量補語'一遍'連用，兩者在體貌上相互衝突。",
    "target_word": "再"
  }
}
```

---

## sense 10353, level 7

#### Pack A
### Level 7 (sense 10353, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这篇课文我没背熟，老师让我背再一遍。",
      "is_correct": false,
      "error_description": "“再”作为副词修饰动词时，应放在动词之前，不能放在动词与动量补语之间。正确语序为“再背一遍”。"
    },
    {
      "text": "如果明天不下雨，我们再去爬山吧。",
      "is_correct": true
    },
    {
      "text": "他把那封信再看了一遍，心里很难过。",
      "is_correct": true
    },
    {
      "text": "这个问题很重要，我们需要再想想。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這篇課文我沒背熟，老師讓我背再一遍。",
        "is_correct": false,
        "error_description": "“再”作為副詞修飾動詞時，應放在動詞之前，不能放在動詞與動量補語之間。正確語序為“再背一遍”。"
      },
      {
        "text": "如果明天不下雨，我們再去爬山吧。",
        "is_correct": true
      },
      {
        "text": "他把那封信再看了一遍，心裡很難過。",
        "is_correct": true
      },
      {
        "text": "這個問題很重要，我們需要再想想。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10353, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "请把桌子收拾干净，再开始写作业。",
      "is_correct": true
    },
    {
      "text": "等心情平静下来，再和他好好谈一谈。",
      "is_correct": true
    },
    {
      "text": "大家讨论完这个问题，再决定下一步再。",
      "is_correct": false,
      "error_description": "语序错误。副词“再”应放在动词“决定”之前作状语，不能放在句末。"
    },
    {
      "text": "大家讨论完这个问题，再决定下一步。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "請把桌子收拾乾淨，再開始寫作業。",
        "is_correct": true
      },
      {
        "text": "等心情平靜下來，再和他好好談一談。",
        "is_correct": true
      },
      {
        "text": "大家討論完這個問題，再決定下一步再。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“再”應放在動詞“決定”之前作狀語，不能放在句末。"
      },
      {
        "text": "大家討論完這個問題，再決定下一步。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10382, level 6

#### Pack A
### Level 6 (sense 10382, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "全球化让不同文化的人常见过面。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人面常见。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人常见面。",
      "is_correct": true
    },
    {
      "text": "全球化让不同文化的人常见了面。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：'见面'是离合词，表示经常性或习惯性的动作时，中间不能加动态助词'了'。 语序错误：'见面'作为离合词，宾语'面'不能提前到动词'见'之前，破坏了正常的动宾结构。 体标错误：'过'表示过去的经历，而句中的'让'和'常见'表示一种普遍的现象或现在的状态，时态冲突。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "全球化讓不同文化的人常見過面。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人面常見。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人常見面。",
        "is_correct": true
      },
      {
        "text": "全球化讓不同文化的人常見了面。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：'見面'是離合詞，表示經常性或習慣性的動作時，中間不能加動態助詞'了'。 語序錯誤：'見面'作為離合詞，賓語'面'不能提前到動詞'見'之前，破壞了正常的動賓結構。 體標錯誤：'過'表示過去的經歷，而句中的'讓'和'常見'表示一種普遍的現象或現在的狀態，時態衝突。",
    "target_word": "不同"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "不同",
  "relation": "antonym",
  "options": [
    "相似",
    "相同",
    "相近",
    "迥异"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "反义项：表示事物之间有共同点，没有差别"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相似",
      "相同",
      "相近",
      "迥異"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "反義項：表示事物之間有共同點，沒有差別"
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
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    },
    {
      "text": "不同的地方有记谱法不同。",
      "is_correct": false
    },
    {
      "text": "不同记谱法的地方有不同的。",
      "is_correct": false
    },
    {
      "text": "地方不同着有不同的记谱法。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：'不同记谱法的地方'语序混乱，且句末'有不同的'缺少宾语中心语，导致句子结构不完整、语义不通。 体标位置错误：动态助词'着'误用在形容词'不同'之后，'不同'表示静态属性，不能加'着'表示持续。 语序错误：'有记谱法不同'不符合汉语'有+定语+中心语'或'中心语+不同'的句法结构，应改为'有不同的记谱法'。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      },
      {
        "text": "不同的地方有記譜法不同。",
        "is_correct": false
      },
      {
        "text": "不同記譜法的地方有不同的。",
        "is_correct": false
      },
      {
        "text": "地方不同著有不同的記譜法。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：'不同記譜法的地方'語序混亂，且句末'有不同的'缺少賓語中心語，導致句子結構不完整、語義不通。 體標位置錯誤：動態助詞'著'誤用在形容詞'不同'之後，'不同'表示靜態屬性，不能加'著'表示持續。 語序錯誤：'有記譜法不同'不符合漢語'有+定語+中心語'或'中心語+不同'的句法結構，應改為'有不同的記譜法'。",
    "target_word": "不同"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "不同",
  "relation": "antonym",
  "options": [
    "相近",
    "相似",
    "相同",
    "特殊"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "反义项：指事物之间没有差异，与“不同”构成反义关系"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相近",
      "相似",
      "相同",
      "特殊"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "反義項：指事物之間沒有差異，與“不同”構成反義關係"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10382, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "不同的地方有不同的记谱法，因此各地的乐谱完全相同。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    },
    {
      "text": "有不同的记谱法不同的地方。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法，因为不同的石头有不同的思想。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。形容词'不同'作定语修饰'地方'时，应放在中心语之前，句中将其放在后面，破坏了正常的定中结构语序。 语义/搭配错误。'石头'与'思想'搭配不当，石头没有思想，导致句子语义荒谬，不符合客观逻辑。 语用/逻辑错误。前半句说明记谱法存在差别，后半句却得出乐谱完全相同的结论，前后逻辑矛盾，语用上极不自然。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "不同的地方有不同的記譜法，因此各地的樂譜完全相同。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      },
      {
        "text": "有不同的記譜法不同的地方。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法，因為不同的石頭有不同的思想。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。形容詞'不同'作定語修飾'地方'時，應放在中心語之前，句中將其放在後面，破壞了正常的定中結構語序。 語義/搭配錯誤。'石頭'與'思想'搭配不當，石頭沒有思想，導致句子語義荒謬，不符合客觀邏輯。 語用/邏輯錯誤。前半句說明記譜法存在差別，後半句卻得出樂譜完全相同的結論，前後邏輯矛盾，語用上極不自然。",
    "target_word": "不同"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "不同",
  "relation": "antonym",
  "options": [
    "相同",
    "相似",
    "相近",
    "类似"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "「相同」指事物之间没有差别、完全一致，与「不同」构成直接反义关系。"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相同",
      "相似",
      "相近",
      "類似"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "「相同」指事物之間沒有差別、完全一致，與「不同」構成直接反義關係。"
      }
    }
  }
}
```

---

## sense 10382, level 7

#### Pack A
### Level 7 (sense 10382, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "每个国家有不同规定。",
      "is_correct": true
    },
    {
      "text": "不同地方的人看时间不一样。",
      "is_correct": true
    },
    {
      "text": "不同地方的人对时间的看法不一样。",
      "is_correct": true
    },
    {
      "text": "每个国家有不同本规定。",
      "is_correct": false,
      "error_description": "量词使用错误。'规定'是抽象名词，不能用量词'本'来修饰，此处应直接省略量词或根据具体语境使用合适的量词（如'项'），但在'有不同规定'中通常无需加量词。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "每個國家有不同規定。",
        "is_correct": true
      },
      {
        "text": "不同地方的人看時間不一樣。",
        "is_correct": true
      },
      {
        "text": "不同地方的人對時間的看法不一樣。",
        "is_correct": true
      },
      {
        "text": "每個國家有不同本規定。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。'規定'是抽象名詞，不能用量詞'本'來修飾，此處應直接省略量詞或根據具體語境使用合適的量詞（如'項'），但在'有不同規定'中通常無需加量詞。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10382, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "不同地方的人对时间的看法不一样。",
      "is_correct": true
    },
    {
      "text": "不同每个国家有规定。",
      "is_correct": false,
      "error_description": "语序错误。“不同”作为形容词应修饰名词“规定”作定语，放在“每个国家”前会导致修饰对象错误且语序不当。正确写法为“每个国家有不同规定”。"
    },
    {
      "text": "不同地方的人看时间不一样。",
      "is_correct": true
    },
    {
      "text": "每个国家有不同规定。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "不同地方的人對時間的看法不一樣。",
        "is_correct": true
      },
      {
        "text": "不同每個國家有規定。",
        "is_correct": false,
        "error_description": "語序錯誤。“不同”作為形容詞應修飾名詞“規定”作定語，放在“每個國家”前會導致修飾物件錯誤且語序不當。正確寫法為“每個國家有不同規定”。"
      },
      {
        "text": "不同地方的人看時間不一樣。",
        "is_correct": true
      },
      {
        "text": "每個國家有不同規定。",
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
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    },
    {
      "text": "他买了不同的三本书。",
      "is_correct": false,
      "error_description": "数量词“三本”应该放在形容词“不同的”前面，修饰名词“书”，正确语序是“三本不同的书”。"
    },
    {
      "text": "不同国家采取了不同的监管方法。",
      "is_correct": true
    },
    {
      "text": "这个过程连接了不同国家的农民、公司和普通消费者。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      },
      {
        "text": "他買了不同的三本書。",
        "is_correct": false,
        "error_description": "數量詞“三本”應該放在形容詞“不同的”前面，修飾名詞“書”，正確語序是“三本不同的書”。"
      },
      {
        "text": "不同國家採取了不同的監管方法。",
        "is_correct": true
      },
      {
        "text": "這個過程連線了不同國家的農民、公司和普通消費者。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10525, level 7

#### Pack A
### Level 7 (sense 10525, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我愈发喜欢这里的同学了。",
      "is_correct": true
    },
    {
      "text": "他把那本书愈发握得紧了。",
      "is_correct": false,
      "error_description": "“愈发”是程度副词，应放在状态补语“紧”的前面，即结构助词“得”之后，不能放在动词“握”之前。"
    },
    {
      "text": "听了这个消息，她愈发高兴了。",
      "is_correct": true
    },
    {
      "text": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我愈發喜歡這裡的同學了。",
        "is_correct": true
      },
      {
        "text": "他把那本書愈發握得緊了。",
        "is_correct": false,
        "error_description": "“愈發”是程度副詞，應放在狀態補語“緊”的前面，即結構助詞“得”之後，不能放在動詞“握”之前。"
      },
      {
        "text": "聽了這個訊息，她愈發高興了。",
        "is_correct": true
      },
      {
        "text": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
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
      "text": "听了这个消息，愈发她高兴了。",
      "is_correct": false,
      "error_description": "“愈发”是副词，应该放在主语之后、谓语之前，不能放在主语之前。"
    },
    {
      "text": "大家愈发觉得这个主意好。",
      "is_correct": true
    },
    {
      "text": "经过这件事，我们愈发信任彼此。",
      "is_correct": true
    },
    {
      "text": "她的笑容愈发灿烂了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "聽了這個訊息，愈發她高興了。",
        "is_correct": false,
        "error_description": "“愈發”是副詞，應該放在主語之後、謂語之前，不能放在主語之前。"
      },
      {
        "text": "大家愈發覺得這個主意好。",
        "is_correct": true
      },
      {
        "text": "經過這件事，我們愈發信任彼此。",
        "is_correct": true
      },
      {
        "text": "她的笑容愈發燦爛了。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10525, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "雨下得愈发大了，我们只好回家。",
      "is_correct": true
    },
    {
      "text": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
      "is_correct": true
    },
    {
      "text": "听了这个故事，我愈发喜欢了他。",
      "is_correct": false,
      "error_description": "体标位置错误。'愈发'表示程度随时间加深，句末的'了'表示状态变化，应放在句末，不能紧跟在动词'喜欢'之后。"
    },
    {
      "text": "听了这个故事，我愈发喜欢他了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "雨下得愈發大了，我們只好回家。",
        "is_correct": true
      },
      {
        "text": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
        "is_correct": true
      },
      {
        "text": "聽了這個故事，我愈發喜歡了他。",
        "is_correct": false,
        "error_description": "體標位置錯誤。'愈發'表示程度隨時間加深，句末的'了'表示狀態變化，應放在句末，不能緊跟在動詞'喜歡'之後。"
      },
      {
        "text": "聽了這個故事，我愈發喜歡他了。",
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
      "text": "经过讨论，我们愈发同意他的观点。",
      "is_correct": true
    },
    {
      "text": "他的成绩愈发优秀，老师很高兴。",
      "is_correct": true
    },
    {
      "text": "我把房间打扫得愈发干净了。",
      "is_correct": true
    },
    {
      "text": "他把房间愈发打扫得干净了。",
      "is_correct": false,
      "error_description": "语序错误。程度副词“愈发”应该放在状态补语“干净”之前，而不是动词“打扫”之前。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "經過討論，我們愈發同意他的觀點。",
        "is_correct": true
      },
      {
        "text": "他的成績愈發優秀，老師很高興。",
        "is_correct": true
      },
      {
        "text": "我把房間打掃得愈發乾淨了。",
        "is_correct": true
      },
      {
        "text": "他把房間愈發打掃得乾淨了。",
        "is_correct": false,
        "error_description": "語序錯誤。程度副詞“愈發”應該放在狀態補語“乾淨”之前，而不是動詞“打掃”之前。"
      }
    ]
  }
}
```

---

## sense 10553, level 6

#### Pack A
### Level 6 (sense 10553, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "频发错误最近，她心里很难过。",
      "is_correct": false
    },
    {
      "text": "最近错误频发掉，她心里很难过。",
      "is_correct": false
    },
    {
      "text": "最近错误正频发，她心里很难过。",
      "is_correct": false
    },
    {
      "text": "最近错误频发，她心里很难过。",
      "is_correct": true
    }
  ],
  "explanation": "体标选用错误。“正”表示动作正在进行，而“频发”表示在一段时间内多次发生，两者在体貌上冲突。 语序错误。谓语“频发”放在了主语“错误”和状语“最近”之前，破坏了汉语正常的主谓语序。 结果补语误用。“掉”作为结果补语表示消除或失去，而“频发”表示多次发生，两者语义矛盾，不能搭配。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "頻發錯誤最近，她心裡很難過。",
        "is_correct": false
      },
      {
        "text": "最近錯誤頻發掉，她心裡很難過。",
        "is_correct": false
      },
      {
        "text": "最近錯誤正頻發，她心裡很難過。",
        "is_correct": false
      },
      {
        "text": "最近錯誤頻發，她心裡很難過。",
        "is_correct": true
      }
    ],
    "explanation": "體標選用錯誤。“正”表示動作正在進行，而“頻發”表示在一段時間內多次發生，兩者在體貌上衝突。 語序錯誤。謂語“頻發”放在了主語“錯誤”和狀語“最近”之前，破壞了漢語正常的主謂語序。 結果補語誤用。“掉”作為結果補語表示消除或失去，而“頻發”表示多次發生，兩者語義矛盾，不能搭配。",
    "target_word": "頻發"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "频发",
  "relation": "antonym",
  "options": [
    "并发",
    "发生",
    "偶发",
    "突发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短时间内多次发生。",
      "explanation": "反义：偶尔发生，与'频发'（短时间内多次发生）在频率维度上构成反义关系"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "併發",
      "發生",
      "偶發",
      "突發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短時間內多次發生。",
        "explanation": "反義：偶爾發生，與'頻發'（短時間內多次發生）在頻率維度上構成反義關係"
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
      "text": "频发的错误让她心里很难过最近。",
      "is_correct": false
    },
    {
      "text": "频发的错误让她心里很难过。",
      "is_correct": true
    },
    {
      "text": "最近错误正在频发着，让她心里很难过。",
      "is_correct": false
    },
    {
      "text": "她不小心把错误频发出来了，心里很难过。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。'频发'表示多次发生，本身已包含反复的体貌意义，不能与表示进行或持续的'正在……着'连用。 语序错误。时间状语'最近'应该放在句首或主语之后，不能放在句末。 趋向补语误用。'频发'表示事件多次发生，不能带趋向补语'出来'表示动作的方向或结果。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "頻發的錯誤讓她心裡很難過最近。",
        "is_correct": false
      },
      {
        "text": "頻發的錯誤讓她心裡很難過。",
        "is_correct": true
      },
      {
        "text": "最近錯誤正在頻發著，讓她心裡很難過。",
        "is_correct": false
      },
      {
        "text": "她不小心把錯誤頻發出來了，心裡很難過。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。'頻發'表示多次發生，本身已包含反覆的體貌意義，不能與表示進行或持續的'正在……著'連用。 語序錯誤。時間狀語'最近'應該放在句首或主語之後，不能放在句末。 趨向補語誤用。'頻發'表示事件多次發生，不能帶趨向補語'出來'表示動作的方向或結果。",
    "target_word": "頻發"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "频发",
  "relation": "antonym",
  "options": [
    "突发",
    "偶发",
    "发生",
    "爆发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短时间内多次发生。",
      "explanation": "反义关系：偶发指偶尔发生，与频发（短时间内多次发生）在频率维度上构成反义"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "突發",
      "偶發",
      "發生",
      "爆發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短時間內多次發生。",
        "explanation": "反義關係：偶發指偶爾發生，與頻發（短時間內多次發生）在頻率維度上構成反義"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10553, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种故障频发，我们得赶紧修理。",
      "is_correct": true
    },
    {
      "text": "频发这种故障，我们得赶紧修理。",
      "is_correct": false
    },
    {
      "text": "这种故障频发了起来，我们得赶紧修理。",
      "is_correct": false
    },
    {
      "text": "这种故障频发着，我们得赶紧修理。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：'频发'本身已包含多次发生的频率意义，不能加表示持续状态的动态助词'着'。 语序错误：'频发'在此处作谓语，主语'这种故障'应放在动词前，原句破坏了'主题—评论'的主谓结构。 方向/结果补语误用：'起来'表示动作开始并继续，而'频发'强调已经多次发生的事实，两者结合导致语义冲突。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "這種故障頻發，我們得趕緊修理。",
        "is_correct": true
      },
      {
        "text": "頻發這種故障，我們得趕緊修理。",
        "is_correct": false
      },
      {
        "text": "這種故障頻發了起來，我們得趕緊修理。",
        "is_correct": false
      },
      {
        "text": "這種故障頻發著，我們得趕緊修理。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：'頻發'本身已包含多次發生的頻率意義，不能加表示持續狀態的動態助詞'著'。 語序錯誤：'頻發'在此處作謂語，主語'這種故障'應放在動詞前，原句破壞了'主題—評論'的主謂結構。 方向/結果補語誤用：'起來'表示動作開始並繼續，而'頻發'強調已經多次發生的事實，兩者結合導致語義衝突。",
    "target_word": "頻發"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "频发",
  "relation": "antonym",
  "options": [
    "偶发",
    "并发",
    "突发",
    "连发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短的时间内多次发生。",
      "explanation": "反义项：偶尔发生，与'频发'（多次发生）在频率上构成反义"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "偶發",
      "併發",
      "突發",
      "連發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短的時間內多次發生。",
        "explanation": "反義項：偶爾發生，與'頻發'（多次發生）在頻率上構成反義"
      }
    }
  }
}
```

---

## sense 10553, level 7

#### Pack A
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "最近这里频发着很多火灾，居民们都很担心。",
      "is_correct": false,
      "error_description": "“频发”表示频繁发生，通常以“名词+频发”的主谓结构出现，不能加动态助词“着”表示动作持续，也不能在句末加“很多”作补语。"
    },
    {
      "text": "气候变化导致适宜种植区收缩，极端天气频发影响产量稳定性；全球航运成本波动、地缘政治紧张以及关税政策调整均可能扰乱贸易流向；同时，小农户在面对市场风险时普遍缺乏金融工具与信息支持。",
      "is_correct": true
    },
    {
      "text": "当极端气候频发导致主粮产区波动时，分布式的城市食品生产网络展现出显著的风险对冲能力，使地方政府将此类项目纳入关键基础设施的应急规划范畴。",
      "is_correct": true
    },
    {
      "text": "在某些干旱频发的地区，纺织工业甚至成为加剧水资源短缺的关键因素，挤占了农业、饮用水与生态系统所需的水量。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "最近這裡頻發著很多火災，居民們都很擔心。",
        "is_correct": false,
        "error_description": "“頻發”表示頻繁發生，通常以“名詞+頻發”的主謂結構出現，不能加動態助詞“著”表示動作持續，也不能在句末加“很多”作補語。"
      },
      {
        "text": "氣候變化導致適宜種植區收縮，極端天氣頻發影響產量穩定性；全球航運成本波動、地緣政治緊張以及關稅政策調整均可能擾亂貿易流向；同時，小農戶在面對市場風險時普遍缺乏金融工具與資訊支援。",
        "is_correct": true
      },
      {
        "text": "當極端氣候頻發導致主糧產區波動時，分散式的城市食品生產網路展現出顯著的風險對沖能力，使地方政府將此類專案納入關鍵基礎設施的應急規劃範疇。",
        "is_correct": true
      },
      {
        "text": "在某些乾旱頻發的地區，紡織工業甚至成為加劇水資源短缺的關鍵因素，擠佔了農業、飲用水與生態系統所需的水量。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "最近矛盾频发，他们把关系搞僵了。",
      "is_correct": true
    },
    {
      "text": "最近频发了很多事故，把大家吓坏了。",
      "is_correct": false,
      "error_description": "“频发”是不及物动词，不能直接带宾语。应将“事故”放在“频发”前面作主语，改为“最近事故频发”。"
    },
    {
      "text": "大家害怕事故频发。",
      "is_correct": true
    },
    {
      "text": "频发的错误让她心里很难过。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "最近矛盾頻發，他們把關係搞僵了。",
        "is_correct": true
      },
      {
        "text": "最近頻發了很多事故，把大家嚇壞了。",
        "is_correct": false,
        "error_description": "“頻發”是不及物動詞，不能直接帶賓語。應將“事故”放在“頻發”前面作主語，改為“最近事故頻發”。"
      },
      {
        "text": "大家害怕事故頻發。",
        "is_correct": true
      },
      {
        "text": "頻發的錯誤讓她心裡很難過。",
        "is_correct": true
      }
    ]
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

#### Pack B
### Level 6 (sense 10803, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立不可替代的制度性优势。",
      "is_correct": true
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立不可替代的制度性优势起。",
      "is_correct": false
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将在高度规制的AI时代确立着不可替代的制度性优势。",
      "is_correct": false
    },
    {
      "text": "那些能将法律义务转化为治理创新的企业，将高度规制的AI时代在确立不可替代的制度性优势。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：“将”字句表示对事物进行处置并产生结果，通常不与表示状态持续的“着”连用，此处应去掉“着”。 语序错误：“将”的宾语应是受事“制度性优势”，原句错将“AI时代”放在“将”后，破坏了“将+受事+动词+补语”的正确语序。 方向/结果补语误用：句末误加了趋向补语“起”，导致句子结构残缺且语义不通，“确立”后无需也不能加“起”。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立不可替代的制度性優勢。",
        "is_correct": true
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立不可替代的制度性優勢起。",
        "is_correct": false
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將在高度規制的AI時代確立著不可替代的制度性優勢。",
        "is_correct": false
      },
      {
        "text": "那些能將法律義務轉化為治理創新的企業，將高度規制的AI時代在確立不可替代的制度性優勢。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：“將”字句表示對事物進行處置併產生結果，通常不與表示狀態持續的“著”連用，此處應去掉“著”。 語序錯誤：“將”的賓語應是受事“制度性優勢”，原句錯將“AI時代”放在“將”後，破壞了“將+受事+動詞+補語”的正確語序。 方向/結果補語誤用：句末誤加了趨向補語“起”，導致句子結構殘缺且語義不通，“確立”後無需也不能加“起”。",
    "target_word": "將"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "管理者应将大家用严格的规则约束起来着，以确保整体秩序。",
      "is_correct": false
    },
    {
      "text": "管理者应将大家用严格的规则约束起来，以确保整体秩序。",
      "is_correct": true
    },
    {
      "text": "管理者应将大家用严格的规则约束起，以确保整体秩序。",
      "is_correct": false
    },
    {
      "text": "管理者应大家将用严格的规则约束起来，以确保整体秩序。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：介词“将”及其宾语“大家”应放在状语“用严格的规则”之前，原句语序破坏了“主题—评论”结构。 体标位置/选用错误：趋向补语“起来”表示动作的开始或状态的持续，不能省略“来”字单用“起”。 体标位置/选用错误：动态助词“着”表示动作进行或状态持续，不能与表示趋向和起始的“起来”连用。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "管理者應將大家用嚴格的規則約束起來著，以確保整體秩序。",
        "is_correct": false
      },
      {
        "text": "管理者應將大家用嚴格的規則約束起來，以確保整體秩序。",
        "is_correct": true
      },
      {
        "text": "管理者應將大家用嚴格的規則約束起，以確保整體秩序。",
        "is_correct": false
      },
      {
        "text": "管理者應大家將用嚴格的規則約束起來，以確保整體秩序。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：介詞“將”及其賓語“大家”應放在狀語“用嚴格的規則”之前，原句語序破壞了“主題—評論”結構。 體標位置/選用錯誤：趨向補語“起來”表示動作的開始或狀態的持續，不能省略“來”字單用“起”。 體標位置/選用錯誤：動態助詞“著”表示動作進行或狀態持續，不能與表示趨向和起始的“起來”連用。",
    "target_word": "將"
  }
}
```

---
