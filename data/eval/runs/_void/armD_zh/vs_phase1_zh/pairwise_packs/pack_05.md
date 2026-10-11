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
      "text": "我昨天听了一条很长的故事。",
      "is_correct": false,
      "error_description": "量词使用错误。名词“故事”的正确量词是“个”或“篇”，不能使用“条”。"
    },
    {
      "text": "很多故事和传说都流传了很长时间。",
      "is_correct": true
    },
    {
      "text": "这条马路很长，走过去需要很久。",
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
        "text": "我昨天聽了一條很長的故事。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。名詞“故事”的正確量詞是“個”或“篇”，不能使用“條”。"
      },
      {
        "text": "很多故事和傳說都流傳了很長時間。",
        "is_correct": true
      },
      {
        "text": "這條馬路很長，走過去需要很久。",
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
      "text": "这个故事很长，我们下次再讲吧。",
      "is_correct": true
    },
    {
      "text": "时间过得真快，长长的假期结束了。",
      "is_correct": true
    },
    {
      "text": "这条很长河，一直流向大海。",
      "is_correct": false,
      "error_description": "形容词“长”不能直接放在名词“河”前面且缺少结构助词“的”，正确的语序应为“这条河很长”或“这条很长的河”。"
    },
    {
      "text": "这条河很长，一直流向大海。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個故事很長，我們下次再講吧。",
        "is_correct": true
      },
      {
        "text": "時間過得真快，長長的假期結束了。",
        "is_correct": true
      },
      {
        "text": "這條很長河，一直流向大海。",
        "is_correct": false,
        "error_description": "形容詞“長”不能直接放在名詞“河”前面且缺少結構助詞“的”，正確的語序應為“這條河很長”或“這條很長的河”。"
      },
      {
        "text": "這條河很長，一直流向大海。",
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
  "ipa": "[t͡saɪ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "再",
    "宰",
    "崽",
    "灾"
  ],
  "correct_answer": "再",
  "explanation": "正确：'再'读第四声（zài），表示动作重复或继续，符合听到的语音。",
  "distractor_explanations": {
    "灾": "声调混淆：'灾'读第一声（zāi），指自然灾害；而目标词'再'读第四声（zài）。",
    "宰": "声调混淆：'宰'读第三声（zǎi），指杀牲畜或主管；而目标词'再'读第四声（zài）。",
    "崽": "声调混淆：'崽'读第三声（zǎi），指小孩子或动物幼崽；而目标词'再'读第四声（zài）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "再",
    "pronunciation": "zài",
    "ipa": "[t͡saɪ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "再",
      "宰",
      "崽",
      "災"
    ],
    "correct_answer": "再",
    "explanation": "正確：'再'讀第四聲（zài），表示動作重複或繼續，符合聽到的語音。",
    "distractor_explanations": {
      "灾": "聲調混淆：'災'讀第一聲（zāi），指自然災害；而目標詞'再'讀第四聲（zài）。",
      "宰": "聲調混淆：'宰'讀第三聲（zǎi），指殺牲畜或主管；而目標詞'再'讀第四聲（zài）。",
      "崽": "聲調混淆：'崽'讀第三聲（zǎi），指小孩子或動物幼崽；而目標詞'再'讀第四聲（zài）。"
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
      "text": "请你把这件事再想一次遍。",
      "is_correct": false
    },
    {
      "text": "请你把这件事想再一遍。",
      "is_correct": false
    },
    {
      "text": "请你把这件事再想一遍了。",
      "is_correct": false
    },
    {
      "text": "请你把这件事再想一遍。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：'再'表示未然或重复的动作，不能与表示已然的动态助词'了'在句末共现。 语序错误：副词'再'必须放在动词'想'之前作状语，不能放在动词和动量补语'一遍'之间。 量词使用错误：'次'和'遍'都是动量词，语义重复且不能连用，应保留其中一个。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "請你把這件事再想一次遍。",
        "is_correct": false
      },
      {
        "text": "請你把這件事想再一遍。",
        "is_correct": false
      },
      {
        "text": "請你把這件事再想一遍了。",
        "is_correct": false
      },
      {
        "text": "請你把這件事再想一遍。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：'再'表示未然或重複的動作，不能與表示已然的動態助詞'了'在句末共現。 語序錯誤：副詞'再'必須放在動詞'想'之前作狀語，不能放在動詞和動量補語'一遍'之間。 量詞使用錯誤：'次'和'遍'都是動量詞，語義重複且不能連用，應保留其中一個。",
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
    "还",
    "刚",
    "又"
  ],
  "correct_answer": "已",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或情况重复或继续。",
      "explanation": "反义：'已'表动作已完成、不再继续，与'再'表重复或继续构成反义"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "已",
      "還",
      "剛",
      "又"
    ],
    "correct_answer": "已",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或情況重複或繼續。",
        "explanation": "反義：'已'表動作已完成、不再繼續，與'再'表重複或繼續構成反義"
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
      "text": "别再生气了，开心一点吧。",
      "is_correct": true
    },
    {
      "text": "别生气再了，开心一点吧。",
      "is_correct": false
    },
    {
      "text": "别再生一次气了，开心一点吧。",
      "is_correct": false
    },
    {
      "text": "别再生气着了，开心一点吧。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：“着”表示状态持续，不能放在“再”和动词“生气”之间，应直接说“别再生气了”。 语序错误：副词“再”必须放在动词“生气”之前，不能放在动词之后。 搭配错误：“再”后面直接加动词表示重复，不需要加“一次”，“再生气”即可表达停止重复该动作。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "別再生氣了，開心一點吧。",
        "is_correct": true
      },
      {
        "text": "別生氣再了，開心一點吧。",
        "is_correct": false
      },
      {
        "text": "別再生一次氣了，開心一點吧。",
        "is_correct": false
      },
      {
        "text": "別再生氣著了，開心一點吧。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：“著”表示狀態持續，不能放在“再”和動詞“生氣”之間，應直接說“別再生氣了”。 語序錯誤：副詞“再”必須放在動詞“生氣”之前，不能放在動詞之後。 搭配錯誤：“再”後面直接加動詞表示重複，不需要加“一次”，“再生氣”即可表達停止重複該動作。",
    "target_word": "再"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "再",
  "relation": "antonym",
  "options": [
    "更",
    "还",
    "又",
    "不再"
  ],
  "correct_answer": "不再",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或情况重复或继续。",
      "explanation": "反义项：表示动作或情况停止、不继续或不重复，与目标词义项构成反义。"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "更",
      "還",
      "又",
      "不再"
    ],
    "correct_answer": "不再",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或情況重複或繼續。",
        "explanation": "反義項：表示動作或情況停止、不繼續或不重複，與目標詞義項構成反義。"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他们观察升力和阻力的变化，再测试一遍。",
      "is_correct": true
    },
    {
      "text": "他们把水用来灌溉农田，再重复利用。",
      "is_correct": true
    },
    {
      "text": "他们观察升力和阻力的变化，测试再一遍。",
      "is_correct": false,
      "error_description": "副词“再”表示动作的重复，应该放在动词“测试”的前面，而不能放在动词和动量补语“一遍”之间。"
    },
    {
      "text": "我们明天再去公园玩吧。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他們觀察升力和阻力的變化，再測試一遍。",
        "is_correct": true
      },
      {
        "text": "他們把水用來灌溉農田，再重複利用。",
        "is_correct": true
      },
      {
        "text": "他們觀察升力和阻力的變化，測試再一遍。",
        "is_correct": false,
        "error_description": "副詞“再”表示動作的重複，應該放在動詞“測試”的前面，而不能放在動詞和動量補語“一遍”之間。"
      },
      {
        "text": "我們明天再去公園玩吧。",
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
      "text": "请你把再这件事想一遍。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，副词“再”应该放在“把”字之前，或者放在“把”的宾语之后、动词之前，不能放在“把”和宾语之间。"
    },
    {
      "text": "他看着照片，再想起那些事。",
      "is_correct": true
    },
    {
      "text": "你能不能再帮我一个忙？",
      "is_correct": true
    },
    {
      "text": "别再生气了，开心一点吧。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "請你把再這件事想一遍。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，副詞“再”應該放在“把”字之前，或者放在“把”的賓語之後、動詞之前，不能放在“把”和賓語之間。"
      },
      {
        "text": "他看著照片，再想起那些事。",
        "is_correct": true
      },
      {
        "text": "你能不能再幫我一個忙？",
        "is_correct": true
      },
      {
        "text": "別再生氣了，開心一點吧。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10382, level 3

#### Pack A
### Level 3 (sense 10382, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这个过程连接了___国家的农民、公司和普通消费者。",
  "original_sentence": "这个过程连接了不同国家的农民、公司和普通消费者。",
  "correct_answer": "不同",
  "options": [
    "个别",
    "一致",
    "相反",
    "不同"
  ],
  "explanation": "正确。'不同'修饰'国家'，表示国家之间存在差异，符合语境。",
  "distractor_tags": {},
  "word_definition": "指事物之间没有共同点，有差别。",
  "target_word": "不同",
  "hant": {
    "sentence_with_blank": "這個過程連線了___國家的農民、公司和普通消費者。",
    "original_sentence": "這個過程連線了不同國家的農民、公司和普通消費者。",
    "correct_answer": "不同",
    "options": [
      "個別",
      "一致",
      "相反",
      "不同"
    ],
    "explanation": "正確。'不同'修飾'國家'，表示國家之間存在差異，符合語境。",
    "distractor_tags": {},
    "word_definition": "指事物之間沒有共同點，有差別。",
    "target_word": "不同"
  }
}
```

#### Pack B
### Level 3 (sense 10382, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这个过程连接了___国家的农民、公司和普通消费者。",
  "original_sentence": "这个过程连接了不同国家的农民、公司和普通消费者。",
  "correct_answer": "不同",
  "options": [
    "不同",
    "美丽",
    "遥远",
    "相同"
  ],
  "explanation": "正确选项。'不同'修饰'国家'，表示来自各个有差别的国家，符合全球化连接多元主体的语境。",
  "distractor_tags": {},
  "word_definition": "指事物之间没有共同点，有差别。",
  "target_word": "不同",
  "hant": {
    "sentence_with_blank": "這個過程連線了___國家的農民、公司和普通消費者。",
    "original_sentence": "這個過程連線了不同國家的農民、公司和普通消費者。",
    "correct_answer": "不同",
    "options": [
      "不同",
      "美麗",
      "遙遠",
      "相同"
    ],
    "explanation": "正確選項。'不同'修飾'國家'，表示來自各個有差別的國家，符合全球化連線多元主體的語境。",
    "distractor_tags": {},
    "word_definition": "指事物之間沒有共同點，有差別。",
    "target_word": "不同"
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
      "text": "全球化让不同文化的人常见面。",
      "is_correct": true
    },
    {
      "text": "全球化让的人不同文化常见面。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人见面常。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人常见面着。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“见面”是短暂性动作，不能与表示状态持续的“着”连用。 语序错误：定语“不同文化”错位，破坏了“让+宾语+动词”的正常兼语结构。 语序错误：副词“常”错放在动词“见面”之后，应放在动词前作状语。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "全球化讓不同文化的人常見面。",
        "is_correct": true
      },
      {
        "text": "全球化讓的人不同文化常見面。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人見面常。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人常見面著。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“見面”是短暫性動作，不能與表示狀態持續的“著”連用。 語序錯誤：定語“不同文化”錯位，破壞了“讓+賓語+動詞”的正常兼語結構。 語序錯誤：副詞“常”錯放在動詞“見面”之後，應放在動詞前作狀語。",
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
    "相近",
    "相似",
    "相同",
    "类似"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "反义项：表示事物之间完全一致、无差别，与「不同」构成反义"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相近",
      "相似",
      "相同",
      "類似"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "反義項：表示事物之間完全一致、無差別，與「不同」構成反義"
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
      "text": "地方不同的有不同的记谱法。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法起来。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法着。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：动态助词'着'表示动作持续或状态保持，不能放在名词性短语'记谱法'之后。 语序错误：'不同的'作为定语必须放在中心语'地方'之前，错位破坏了'主题—评论'结构。 方向补语误用：'起来'表示动作开始或向上，不能附加在表示客观存在的名词性成分'记谱法'之后。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "地方不同的有不同的記譜法。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法起來。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法著。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'著'表示動作持續或狀態保持，不能放在名詞性短語'記譜法'之後。 語序錯誤：'不同的'作為定語必須放在中心語'地方'之前，錯位破壞了'主題—評論'結構。 方向補語誤用：'起來'表示動作開始或向上，不能附加在表示客觀存在的名詞性成分'記譜法'之後。",
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
    "相似",
    "独立",
    "相同",
    "相关"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "反义项：事物之间没有差别，有共同点"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相似",
      "獨立",
      "相同",
      "相關"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "反義項：事物之間沒有差別，有共同點"
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

#### Pack B
### Level 7 (sense 10382, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "每个国家有了不同规定。",
      "is_correct": false,
      "error_description": "体标误用。形容词“不同”表示状态，不需要加动态助词“了”，应直接使用“有”或“是”。"
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
      "text": "每个国家有不同规定。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "每個國家有了不同規定。",
        "is_correct": false,
        "error_description": "體標誤用。形容詞“不同”表示狀態，不需要加動態助詞“了”，應直接使用“有”或“是”。"
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
      "text": "不同国家采取了不同的监管方法。",
      "is_correct": true
    },
    {
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    },
    {
      "text": "不同以前，他现在每天坚持早起锻炼。",
      "is_correct": false,
      "error_description": "语序错误。“不同”作为形容词，不能直接放在名词或代词前作状语。应改为“和……不同”或“不同于……”。"
    },
    {
      "text": "这个过程连接了不同国家的农民、公司和普通消费者。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "不同國家採取了不同的監管方法。",
        "is_correct": true
      },
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      },
      {
        "text": "不同以前，他現在每天堅持早起鍛鍊。",
        "is_correct": false,
        "error_description": "語序錯誤。“不同”作為形容詞，不能直接放在名詞或代詞前作狀語。應改為“和……不同”或“不同於……”。"
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
      "text": "随着时间推移，他愈发喜欢这只猫。",
      "is_correct": true
    },
    {
      "text": "听了这个故事，她愈发觉得感动。",
      "is_correct": true
    },
    {
      "text": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
      "is_correct": true
    },
    {
      "text": "随着时间推移，愈发他喜欢这只猫。",
      "is_correct": false,
      "error_description": "语序错误。副词“愈发”通常放在主语之后、谓语之前，不能放在主语前面。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "隨著時間推移，他愈發喜歡這隻貓。",
        "is_correct": true
      },
      {
        "text": "聽了這個故事，她愈發覺得感動。",
        "is_correct": true
      },
      {
        "text": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
        "is_correct": true
      },
      {
        "text": "隨著時間推移，愈發他喜歡這隻貓。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“愈發”通常放在主語之後、謂語之前，不能放在主語前面。"
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
      "text": "她把房间愈发收拾得干净了。",
      "is_correct": true
    },
    {
      "text": "大家愈发觉得这个主意不错。",
      "is_correct": true
    },
    {
      "text": "他把那本书愈发看得仔细了。",
      "is_correct": true
    },
    {
      "text": "他把那本书愈发看得仔细了。",
      "is_correct": false,
      "error_description": "语序错误。副词“愈发”修饰形容词“仔细”时，应紧跟在形容词之前，而不是放在动词“看”之前。正确的语序是“看得愈发仔细”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她把房間愈發收拾得乾淨了。",
        "is_correct": true
      },
      {
        "text": "大家愈發覺得這個主意不錯。",
        "is_correct": true
      },
      {
        "text": "他把那本書愈發看得仔細了。",
        "is_correct": true
      },
      {
        "text": "他把那本書愈發看得仔細了。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“愈發”修飾形容詞“仔細”時，應緊跟在形容詞之前，而不是放在動詞“看”之前。正確的語序是“看得愈發仔細”。"
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
      "text": "最近班里频发了感冒，大家都要注意保暖。",
      "is_correct": false
    },
    {
      "text": "最近班里频发着感冒，大家都要注意保暖。",
      "is_correct": false
    },
    {
      "text": "最近感冒频发在班里，大家都要注意保暖。",
      "is_correct": false
    },
    {
      "text": "最近班里感冒频发，大家都要注意保暖。",
      "is_correct": true
    }
  ],
  "explanation": "体标选用错误。频发表示一种高频发生的客观现象或状态，不能与表示动作持续的动态助词“着”连用。 语序错误。频发通常直接跟在主语之后作谓语，或者作为定语修饰名词，不能将处所补语“在班里”直接放在频发之后。 体标位置错误。频发本身已包含多次发生的语义，通常不加“了”表示完成。若强调已发生，应将“了”放在句末，如“频发了”不符合该词的习惯用法。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "最近班裡頻發了感冒，大家都要注意保暖。",
        "is_correct": false
      },
      {
        "text": "最近班裡頻發著感冒，大家都要注意保暖。",
        "is_correct": false
      },
      {
        "text": "最近感冒頻發在班裡，大家都要注意保暖。",
        "is_correct": false
      },
      {
        "text": "最近班裡感冒頻發，大家都要注意保暖。",
        "is_correct": true
      }
    ],
    "explanation": "體標選用錯誤。頻發表示一種高頻發生的客觀現象或狀態，不能與表示動作持續的動態助詞“著”連用。 語序錯誤。頻發通常直接跟在主語之後作謂語，或者作為定語修飾名詞，不能將處所補語“在班裡”直接放在頻發之後。 體標位置錯誤。頻發本身已包含多次發生的語義，通常不加“了”表示完成。若強調已發生，應將“了”放在句末，如“頻發了”不符合該詞的習慣用法。",
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
    "突发",
    "并发",
    "偶发",
    "蔓延"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短的时间内多次发生。",
      "explanation": "反义项：偶然发生，与频繁发生构成频率上的反义关系"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "突發",
      "併發",
      "偶發",
      "蔓延"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短的時間內多次發生。",
        "explanation": "反義項：偶然發生，與頻繁發生構成頻率上的反義關係"
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
      "text": "老师对频发起的违纪现象感到非常失望。",
      "is_correct": false
    },
    {
      "text": "老师对频发的违纪现象感到非常失望。",
      "is_correct": true
    },
    {
      "text": "老师对违纪现象频发地感到非常失望。",
      "is_correct": false
    },
    {
      "text": "老师对频发了的违纪现象感到非常失望。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'频发'本身已包含多次发生的动作意义，后面不能加动态助词'了'，应直接修饰名词。 语序错误。'频发'应作为定语直接修饰'违纪现象'，不能用结构助词'地'将其变为状语放在名词之后。 方向补语误用。'频发'表示动作多次发生，不能加趋向补语'起'，'频发起'不符合汉语语法和表达习惯。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "老師對頻發起的違紀現象感到非常失望。",
        "is_correct": false
      },
      {
        "text": "老師對頻發的違紀現象感到非常失望。",
        "is_correct": true
      },
      {
        "text": "老師對違紀現象頻發地感到非常失望。",
        "is_correct": false
      },
      {
        "text": "老師對頻發了的違紀現象感到非常失望。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'頻發'本身已包含多次發生的動作意義，後面不能加動態助詞'了'，應直接修飾名詞。 語序錯誤。'頻發'應作為定語直接修飾'違紀現象'，不能用結構助詞'地'將其變為狀語放在名詞之後。 方向補語誤用。'頻發'表示動作多次發生，不能加趨向補語'起'，'頻發起'不符合漢語語法和表達習慣。",
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
    "发生",
    "爆发",
    "偶发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短的时间内多次发生。",
      "explanation": "反义项：偶发指偶尔发生，与频发（短时间内多次发生）构成频率上的反义关系"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "突發",
      "發生",
      "爆發",
      "偶發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短的時間內多次發生。",
        "explanation": "反義項：偶發指偶爾發生，與頻發（短時間內多次發生）構成頻率上的反義關係"
      }
    }
  }
}
```

#### Pack B
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

---

## sense 10553, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "当极端气候频发导致主粮产区波动时，分布式的城市食品生产网络展现出显著的风险对冲能力，使地方政府将此类项目纳入关键基础设施的应急规划范畴。",
      "is_correct": true
    },
    {
      "text": "最近班里感冒频发着，大家都要注意保暖。",
      "is_correct": false,
      "error_description": "体标选用错误。“频发”表示频繁发生的状态或动作，本身已包含持续或反复的语义，后面不能加表示动作持续的体标“着”，应直接删去“着”。"
    },
    {
      "text": "在某些干旱频发的地区，纺织工业甚至成为加剧水资源短缺的关键因素，挤占了农业、饮用水与生态系统所需的水量。",
      "is_correct": true
    },
    {
      "text": "气候变化导致适宜种植区收缩，极端天气频发影响产量稳定性；全球航运成本波动、地缘政治紧张以及关税政策调整均可能扰乱贸易流向；同时，小农户在面对市场风险时普遍缺乏金融工具与信息支持。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "當極端氣候頻發導致主糧產區波動時，分散式的城市食品生產網路展現出顯著的風險對沖能力，使地方政府將此類專案納入關鍵基礎設施的應急規劃範疇。",
        "is_correct": true
      },
      {
        "text": "最近班裡感冒頻發著，大家都要注意保暖。",
        "is_correct": false,
        "error_description": "體標選用錯誤。“頻發”表示頻繁發生的狀態或動作，本身已包含持續或反覆的語義，後面不能加表示動作持續的體標“著”，應直接刪去“著”。"
      },
      {
        "text": "在某些乾旱頻發的地區，紡織工業甚至成為加劇水資源短缺的關鍵因素，擠佔了農業、飲用水與生態系統所需的水量。",
        "is_correct": true
      },
      {
        "text": "氣候變化導致適宜種植區收縮，極端天氣頻發影響產量穩定性；全球航運成本波動、地緣政治緊張以及關稅政策調整均可能擾亂貿易流向；同時，小農戶在面對市場風險時普遍缺乏金融工具與資訊支援。",
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
      "text": "最近班里感冒频发着，大家都要注意保暖。",
      "is_correct": false,
      "error_description": "体标选用错误。'频发'表示频繁发生，本身已包含频率和动态意味，后面不能加表示动作持续的体标'着'。应直接去掉'着'。"
    },
    {
      "text": "矛盾频发让这段友谊走到了尽头。",
      "is_correct": true
    },
    {
      "text": "老师对频发的违纪现象感到非常失望。",
      "is_correct": true
    },
    {
      "text": "他把频发的问题记录在了本子上。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "最近班裡感冒頻發著，大家都要注意保暖。",
        "is_correct": false,
        "error_description": "體標選用錯誤。'頻發'表示頻繁發生，本身已包含頻率和動態意味，後面不能加表示動作持續的體標'著'。應直接去掉'著'。"
      },
      {
        "text": "矛盾頻發讓這段友誼走到了盡頭。",
        "is_correct": true
      },
      {
        "text": "老師對頻發的違紀現象感到非常失望。",
        "is_correct": true
      },
      {
        "text": "他把頻發的問題記錄在了本子上。",
        "is_correct": true
      }
    ]
  }
}
```

---
