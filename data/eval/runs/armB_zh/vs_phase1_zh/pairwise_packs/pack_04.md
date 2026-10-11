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


## sense 10300, level 1

#### Pack A
### Level 1 (sense 10300, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "ipa": "[ʈʂʰɑŋ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "常",
    "场",
    "长",
    "唱"
  ],
  "correct_answer": "长",
  "explanation": "正确。读音为 cháng，第二声，表示空间或时间距离大。",
  "distractor_explanations": {
    "常": "错误。读音为 cháng，但意思是经常、平常，与长度无关。",
    "场": "错误。读音为 chǎng（第三声），指场地或场合，声调和意义均不同。",
    "唱": "错误。读音为 chàng（第四声），指唱歌，声调和意义均不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[ʈʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "常",
      "場",
      "長",
      "唱"
    ],
    "correct_answer": "長",
    "explanation": "正確。讀音為 cháng，第二聲，表示空間或時間距離大。",
    "distractor_explanations": {
      "常": "錯誤。讀音為 cháng，但意思是經常、平常，與長度無關。",
      "场": "錯誤。讀音為 chǎng（第三聲），指場地或場合，聲調和意義均不同。",
      "唱": "錯誤。讀音為 chàng（第四聲），指唱歌，聲調和意義均不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10300, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "ipa": "[ʈʂʰɑŋ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "长",
    "昌",
    "唱",
    "厂"
  ],
  "correct_answer": "长",
  "explanation": "“长”读二声，指空间或时间上距离大，符合听力材料的语义。",
  "distractor_explanations": {
    "厂": "“厂”读三声，指工厂，声调不同导致意义完全改变。",
    "唱": "“唱”读四声，指唱歌，声调不同导致意义完全改变。",
    "昌": "“昌”读一声，指兴旺，声调不同导致意义完全改变。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[ʈʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "長",
      "昌",
      "唱",
      "廠"
    ],
    "correct_answer": "長",
    "explanation": "“長”讀二聲，指空間或時間上距離大，符合聽力材料的語義。",
    "distractor_explanations": {
      "厂": "“廠”讀三聲，指工廠，聲調不同導致意義完全改變。",
      "唱": "“唱”讀四聲，指唱歌，聲調不同導致意義完全改變。",
      "昌": "“昌”讀一聲，指興旺，聲調不同導致意義完全改變。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10300, level 3

#### Pack A
### Level 3 (sense 10300, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___城在中国北方，它很长很长。",
  "original_sentence": "长城在中国北方，它很长很长。",
  "correct_answer": "长",
  "options": [
    "长",
    "大",
    "高",
    "宽"
  ],
  "explanation": "正确。形容长城在空间上的延伸距离很大。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "___城在中國北方，它很長很長。",
    "original_sentence": "長城在中國北方，它很長很長。",
    "correct_answer": "長",
    "options": [
      "長",
      "大",
      "高",
      "寬"
    ],
    "explanation": "正確。形容長城在空間上的延伸距離很大。",
    "distractor_tags": {},
    "word_definition": "指空間或時間上距離大，與‘短’相對。",
    "target_word": "長"
  }
}
```

#### Pack B
### Level 3 (sense 10300, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___城在中国北方，它很长很长。",
  "original_sentence": "长城在中国北方，它很长很长。",
  "correct_answer": "长",
  "options": [
    "久",
    "深",
    "远",
    "长"
  ],
  "explanation": "“长”指空间距离大，符合长城延伸的物理特征，且与后文“很长”呼应。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "___城在中國北方，它很長很長。",
    "original_sentence": "長城在中國北方，它很長很長。",
    "correct_answer": "長",
    "options": [
      "久",
      "深",
      "遠",
      "長"
    ],
    "explanation": "“長”指空間距離大，符合長城延伸的物理特徵，且與後文“很長”呼應。",
    "distractor_tags": {},
    "word_definition": "指空間或時間上距離大，與‘短’相對。",
    "target_word": "長"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "他把故事讲得很___，大家都听困了。",
  "original_sentence": "他把故事讲得很长，大家都听困了。",
  "correct_answer": "长",
  "options": [
    "大",
    "广",
    "长",
    "深"
  ],
  "explanation": "正确。‘长’指时间或篇幅大，符合后文‘大家都听困了’的语境。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "他把故事講得很___，大家都聽困了。",
    "original_sentence": "他把故事講得很長，大家都聽困了。",
    "correct_answer": "長",
    "options": [
      "大",
      "廣",
      "長",
      "深"
    ],
    "explanation": "正確。‘長’指時間或篇幅大，符合後文‘大家都聽困了’的語境。",
    "distractor_tags": {},
    "word_definition": "指空間或時間上距離大，與‘短’相對。",
    "target_word": "長"
  }
}
```

---

## sense 10353, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 10353, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "再",
  "pronunciation": "zài",
  "ipa": "[t͡saɪ̯˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "在",
    "宰",
    "再",
    "载"
  ],
  "correct_answer": "再",
  "explanation": "正确。读音为 zài，第四声，表示重复或继续。",
  "distractor_explanations": {
    "在": "错误。读音为 zài，但意为“正在”或“位于”，不表示重复。",
    "载": "错误。多音字（zǎi/zài），意为“装载”或“记录”，语义不符。",
    "宰": "错误。读音为 zǎi，第三声，意为“屠宰”或“主宰”，声调和意义均不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "再",
    "pronunciation": "zài",
    "ipa": "[t͡saɪ̯˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "在",
      "宰",
      "再",
      "載"
    ],
    "correct_answer": "再",
    "explanation": "正確。讀音為 zài，第四聲，表示重複或繼續。",
    "distractor_explanations": {
      "在": "錯誤。讀音為 zài，但意為“正在”或“位於”，不表示重複。",
      "载": "錯誤。多音字（zǎi/zài），意為“裝載”或“記錄”，語義不符。",
      "宰": "錯誤。讀音為 zǎi，第三聲，意為“屠宰”或“主宰”，聲調和意義均不同。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10353, level 3

#### Pack A
### Level 3 (sense 10353, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他们观察升力和阻力的变化，___改进设计。",
  "original_sentence": "他们观察升力和阻力的变化，再改进设计。",
  "correct_answer": "再",
  "options": [
    "再",
    "才",
    "还",
    "又"
  ],
  "explanation": "正确。表示在前一个动作（观察）之后，进行下一个动作（改进），体现顺序和继续。",
  "distractor_tags": {},
  "word_definition": "表示动作或状态的重复或继续",
  "target_word": "再",
  "hant": {
    "sentence_with_blank": "他們觀察升力和阻力的變化，___改進設計。",
    "original_sentence": "他們觀察升力和阻力的變化，再改進設計。",
    "correct_answer": "再",
    "options": [
      "再",
      "才",
      "還",
      "又"
    ],
    "explanation": "正確。表示在前一個動作（觀察）之後，進行下一個動作（改進），體現順序和繼續。",
    "distractor_tags": {},
    "word_definition": "表示動作或狀態的重複或繼續",
    "target_word": "再"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "看完这本书，___去看那部电影。",
  "original_sentence": "看完这本书，再去看那部电影。",
  "correct_answer": "再",
  "options": [
    "又",
    "还",
    "再",
    "才"
  ],
  "explanation": "正确。表示动作的先后顺序，看完书之后接着看电影。",
  "distractor_tags": {},
  "word_definition": "表示动作或状态的重复或继续",
  "target_word": "再",
  "hant": {
    "sentence_with_blank": "看完這本書，___去看那部電影。",
    "original_sentence": "看完這本書，再去看那部電影。",
    "correct_answer": "再",
    "options": [
      "又",
      "還",
      "再",
      "才"
    ],
    "explanation": "正確。表示動作的先後順序，看完書之後接著看電影。",
    "distractor_tags": {},
    "word_definition": "表示動作或狀態的重複或繼續",
    "target_word": "再"
  }
}
```

#### Pack B
### Level 3 (sense 10353, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "如果明天不下雨，我们___去爬山吧。",
  "original_sentence": "如果明天不下雨，我们再去爬山吧。",
  "correct_answer": "再",
  "options": [
    "再",
    "却",
    "且",
    "已"
  ],
  "explanation": "正确。'再'表示在条件满足后接着做某事，符合句意。",
  "distractor_tags": {},
  "word_definition": "副词，表示动作或状态的重复或继续。",
  "target_word": "再",
  "hant": {
    "sentence_with_blank": "如果明天不下雨，我們___去爬山吧。",
    "original_sentence": "如果明天不下雨，我們再去爬山吧。",
    "correct_answer": "再",
    "options": [
      "再",
      "卻",
      "且",
      "已"
    ],
    "explanation": "正確。'再'表示在條件滿足後接著做某事，符合句意。",
    "distractor_tags": {},
    "word_definition": "副詞，表示動作或狀態的重複或繼續。",
    "target_word": "再"
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

#### Pack B
### Level 6 (sense 10353, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "再",
  "relation": "antonym",
  "options": [
    "仍",
    "还",
    "初",
    "又"
  ],
  "correct_answer": "初",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示动作或状态的重复或继续",
      "explanation": "表示第一次或开始，与表示重复或继续的“再”构成反义关系"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "仍",
      "還",
      "初",
      "又"
    ],
    "correct_answer": "初",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示動作或狀態的重複或繼續",
        "explanation": "表示第一次或開始，與表示重複或繼續的“再”構成反義關係"
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
      "text": "这个问题很重要，我们需要再讨论了。",
      "is_correct": false
    },
    {
      "text": "这个问题很重要，我们需要讨论一下再。",
      "is_correct": false
    },
    {
      "text": "这个问题很重要，我们需要再讨论得一下。",
      "is_correct": false
    },
    {
      "text": "这个问题很重要，我们需要再讨论一下。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误：副词'再'必须放在动词'讨论'之前，不能放在句末。 体貌错误：'再'表示未然或将来进行的重复，与表示完成或变化的句尾'了'搭配不当，应去掉'了'或改为'再讨论一次'。 结构错误：'一下'作为动量补语直接跟在动词后，中间不能插入结构助词'得'。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "這個問題很重要，我們需要再討論了。",
        "is_correct": false
      },
      {
        "text": "這個問題很重要，我們需要討論一下再。",
        "is_correct": false
      },
      {
        "text": "這個問題很重要，我們需要再討論得一下。",
        "is_correct": false
      },
      {
        "text": "這個問題很重要，我們需要再討論一下。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤：副詞'再'必須放在動詞'討論'之前，不能放在句末。 體貌錯誤：'再'表示未然或將來進行的重複，與表示完成或變化的句尾'了'搭配不當，應去掉'了'或改為'再討論一次'。 結構錯誤：'一下'作為動量補語直接跟在動詞後，中間不能插入結構助詞'得'。",
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
    "初",
    "还",
    "又",
    "仍"
  ],
  "correct_answer": "初",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示动作或状态的重复或继续",
      "explanation": "反义：表示动作或状态的第一次发生，与“再”表示的重复或继续相对。"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "初",
      "還",
      "又",
      "仍"
    ],
    "correct_answer": "初",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示動作或狀態的重複或繼續",
        "explanation": "反義：表示動作或狀態的第一次發生，與“再”表示的重複或繼續相對。"
      }
    }
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
      "text": "他们观察升力和阻力的变化，再改进设计。",
      "is_correct": true
    },
    {
      "text": "这道题很难，请你再做一次。",
      "is_correct": true
    },
    {
      "text": "我们昨天再去了那家餐厅吃饭。",
      "is_correct": false,
      "error_description": "错误类型：体标/时间副词误用。解释：'再'通常用于将来时或未然动作，表示'接着做'或'重复做（将来）'；对于已经发生的过去重复动作，应使用'又'。"
    },
    {
      "text": "等到干旱时，再把这些水用来灌溉农田。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他們觀察升力和阻力的變化，再改進設計。",
        "is_correct": true
      },
      {
        "text": "這道題很難，請你再做一次。",
        "is_correct": true
      },
      {
        "text": "我們昨天再去了那家餐廳吃飯。",
        "is_correct": false,
        "error_description": "錯誤型別：體標/時間副詞誤用。解釋：'再'通常用於將來時或未然動作，表示'接著做'或'重複做（將來）'；對於已經發生的過去重複動作，應使用'又'。"
      },
      {
        "text": "等到乾旱時，再把這些水用來灌溉農田。",
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
      "text": "全球化让不同文化的人正在常见面。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人见面常见。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人常见面。",
      "is_correct": true
    },
    {
      "text": "全球化让不同文化的人常见面了。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：频率副词'常'应放在动词'见面'之前作状语，即'常见面'，而非放在句末作补语。 体貌错误：'常'表示习惯性动作，而'正在'表示进行时，两者在语义上冲突，不能同时修饰同一个动词。 体标误用：句子描述的是一种普遍现象或常态，不宜使用表示完成或变化的动态助词'了'，这会破坏陈述一般事实的语用功能。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "全球化讓不同文化的人正在常見面。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人見面常見。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人常見面。",
        "is_correct": true
      },
      {
        "text": "全球化讓不同文化的人常見面了。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：頻率副詞'常'應放在動詞'見面'之前作狀語，即'常見面'，而非放在句末作補語。 體貌錯誤：'常'表示習慣性動作，而'正在'表示進行時，兩者在語義上衝突，不能同時修飾同一個動詞。 體標誤用：句子描述的是一種普遍現象或常態，不宜使用表示完成或變化的動態助詞'了'，這會破壞陳述一般事實的語用功能。",
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
    "类似",
    "相似",
    "相同",
    "差异"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "反义词：指事物之间没有差别，完全一致"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "類似",
      "相似",
      "相同",
      "差異"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "反義詞：指事物之間沒有差別，完全一致"
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

## sense 10525, level 3

#### Pack A
### Level 3 (sense 10525, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者___关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
  "original_sentence": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
  "correct_answer": "愈发",
  "options": [
    "一概",
    "断然",
    "大肆",
    "愈发"
  ],
  "explanation": "正确。'愈发'表示程度比原来更深，符合语境中消费者关注程度的加深。",
  "distractor_tags": {},
  "word_definition": "副词。表示程度比原来更加深，相当于‘更加’。",
  "target_word": "愈发",
  "hant": {
    "sentence_with_blank": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者___關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "original_sentence": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "correct_answer": "愈發",
    "options": [
      "一概",
      "斷然",
      "大肆",
      "愈發"
    ],
    "explanation": "正確。'愈發'表示程度比原來更深，符合語境中消費者關注程度的加深。",
    "distractor_tags": {},
    "word_definition": "副詞。表示程度比原來更加深，相當於‘更加’。",
    "target_word": "愈發"
  }
}
```

#### Pack B
### Level 3 (sense 10525, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者___关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
  "original_sentence": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
  "correct_answer": "愈发",
  "options": [
    "愈发",
    "刚刚",
    "偶尔",
    "忽然"
  ],
  "explanation": "正确。语境中消费者关注度随时间推移而加深，“愈发”准确表达了这种渐进的程度变化。",
  "distractor_tags": {},
  "word_definition": "表示程度比原来更深，相当于“更加”。",
  "target_word": "愈发",
  "hant": {
    "sentence_with_blank": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者___關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "original_sentence": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "correct_answer": "愈發",
    "options": [
      "愈發",
      "剛剛",
      "偶爾",
      "忽然"
    ],
    "explanation": "正確。語境中消費者關注度隨時間推移而加深，“愈發”準確表達了這種漸進的程度變化。",
    "distractor_tags": {},
    "word_definition": "表示程度比原來更深，相當於“更加”。",
    "target_word": "愈發"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这本书很有趣，我___喜欢读了。",
  "original_sentence": "这本书很有趣，我愈发喜欢读了。",
  "correct_answer": "愈发",
  "options": [
    "愈发",
    "忽然",
    "偶尔",
    "刚刚"
  ],
  "explanation": "正确。“愈发”表示程度比原来更深，符合句意“因为书有趣，所以喜欢的程度加深了”。",
  "distractor_tags": {},
  "word_definition": "表示程度比原来更深，相当于“更加”。",
  "target_word": "愈发",
  "hant": {
    "sentence_with_blank": "這本書很有趣，我___喜歡讀了。",
    "original_sentence": "這本書很有趣，我愈發喜歡讀了。",
    "correct_answer": "愈發",
    "options": [
      "愈發",
      "忽然",
      "偶爾",
      "剛剛"
    ],
    "explanation": "正確。“愈發”表示程度比原來更深，符合句意“因為書有趣，所以喜歡的程度加深了”。",
    "distractor_tags": {},
    "word_definition": "表示程度比原來更深，相當於“更加”。",
    "target_word": "愈發"
  }
}
```

---

## sense 10553, level 3

#### Pack A
### Level 3 (sense 10553, difficulty None)
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "近期暴雨___，导致多地出现内涝。",
  "original_sentence": "近期暴雨频发，导致多地出现内涝。",
  "correct_answer": "频发",
  "options": [
    "偶发",
    "初发",
    "频发",
    "激发"
  ],
  "explanation": "正确。语境指暴雨在短时间内多次发生，符合“频发”的语义。",
  "distractor_tags": {},
  "word_definition": "在短时间里多次发生",
  "target_word": "频发",
  "hant": {
    "sentence_with_blank": "近期暴雨___，導致多地出現內澇。",
    "original_sentence": "近期暴雨頻發，導致多地出現內澇。",
    "correct_answer": "頻發",
    "options": [
      "偶發",
      "初發",
      "頻發",
      "激發"
    ],
    "explanation": "正確。語境指暴雨在短時間內多次發生，符合“頻發”的語義。",
    "distractor_tags": {},
    "word_definition": "在短時間裡多次發生",
    "target_word": "頻發"
  }
}
```

#### Pack B
### Level 3 (sense 10553, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "最近这一带交通事故___，让很多市民对日常出行的安全感到十分担忧，大家希望相关部门能尽快改善路况并加强管理，以保障居民的安全。",
  "original_sentence": "最近这一带交通事故频发，让很多市民对日常出行的安全感到十分担忧，大家希望相关部门能尽快改善路况并加强管理，以保障居民的安全。",
  "correct_answer": "频发",
  "options": [
    "爆发",
    "延续",
    "频发",
    "制造"
  ],
  "explanation": "正确选项。“频发”指在较短时间内多次发生，符合交通事故多次出现导致市民担忧的语境。",
  "distractor_tags": {},
  "word_definition": "指在较短时间内多次发生。",
  "target_word": "频发",
  "hant": {
    "sentence_with_blank": "最近這一帶交通事故___，讓很多市民對日常出行的安全感到十分擔憂，大家希望相關部門能儘快改善路況並加強管理，以保障居民的安全。",
    "original_sentence": "最近這一帶交通事故頻發，讓很多市民對日常出行的安全感到十分擔憂，大家希望相關部門能儘快改善路況並加強管理，以保障居民的安全。",
    "correct_answer": "頻發",
    "options": [
      "爆發",
      "延續",
      "頻發",
      "製造"
    ],
    "explanation": "正確選項。“頻發”指在較短時間內多次發生，符合交通事故多次出現導致市民擔憂的語境。",
    "distractor_tags": {},
    "word_definition": "指在較短時間內多次發生。",
    "target_word": "頻發"
  }
}
```

---

## sense 10553, level 6

#### Pack A
### Level 6 (sense 10553, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "最近班里感冒的同学很多，这种病正在频发。",
      "is_correct": true
    },
    {
      "text": "最近班里感冒的同学很多，这种病频发在。",
      "is_correct": false
    },
    {
      "text": "最近班里感冒的同学很多，这种病被频发。",
      "is_correct": false
    },
    {
      "text": "最近班里感冒的同学很多，这种病正在频发了。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：'频发'本身已包含多次发生的动态含义，通常不与表示完成或状态改变的'了'直接连用构成'正在...了'结构，语感冗余且不自然。 语序错误：汉语中处所或状态补语不能简单以'在'结尾悬空，'频发'是不及物动词用法，此处句法结构破碎。 语态错误：'频发'描述的是事件发生的频率和状态，通常作为不及物动词使用，不能用于被动语态'被'字句。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "最近班裡感冒的同學很多，這種病正在頻發。",
        "is_correct": true
      },
      {
        "text": "最近班裡感冒的同學很多，這種病頻發在。",
        "is_correct": false
      },
      {
        "text": "最近班裡感冒的同學很多，這種病被頻發。",
        "is_correct": false
      },
      {
        "text": "最近班裡感冒的同學很多，這種病正在頻發了。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：'頻發'本身已包含多次發生的動態含義，通常不與表示完成或狀態改變的'了'直接連用構成'正在...了'結構，語感冗餘且不自然。 語序錯誤：漢語中處所或狀態補語不能簡單以'在'結尾懸空，'頻發'是不及物動詞用法，此處句法結構破碎。 語態錯誤：'頻發'描述的是事件發生的頻率和狀態，通常作為不及物動詞使用，不能用於被動語態'被'字句。",
    "target_word": "頻發"
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "这里火灾正在频发着，消防员工作很辛苦。",
      "is_correct": false
    },
    {
      "text": "这里火灾频发，消防员工作很辛苦。",
      "is_correct": true
    },
    {
      "text": "消防员在这里火灾频发地工作很辛苦。",
      "is_correct": false
    },
    {
      "text": "这里火灾频发过，消防员工作很辛苦。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“频发”本身已包含“多次发生”的频率意义，通常不与表示持续状态的动态助词“着”连用，语感冗余且不自然。 语序错误：状语位置不当。“火灾频发”应作为背景或原因独立成句或作定语，直接修饰“工作”造成句法结构混乱，语义重心偏移。 体标错误：“过”表示经历或完成，暗示该现象已不再持续。这与后半句描述的消防员当前持续辛苦的工作状态在逻辑连贯性上较弱，通常此类语境强调现状而非过往经历。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "這裡火災正在頻發著，消防員工作很辛苦。",
        "is_correct": false
      },
      {
        "text": "這裡火災頻發，消防員工作很辛苦。",
        "is_correct": true
      },
      {
        "text": "消防員在這裡火災頻發地工作很辛苦。",
        "is_correct": false
      },
      {
        "text": "這裡火災頻發過，消防員工作很辛苦。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“頻發”本身已包含“多次發生”的頻率意義，通常不與表示持續狀態的動態助詞“著”連用，語感冗餘且不自然。 語序錯誤：狀語位置不當。“火災頻發”應作為背景或原因獨立成句或作定語，直接修飾“工作”造成句法結構混亂，語義重心偏移。 體標錯誤：“過”表示經歷或完成，暗示該現象已不再持續。這與後半句描述的消防員當前持續辛苦的工作狀態在邏輯連貫性上較弱，通常此類語境強調現狀而非過往經歷。",
    "target_word": "頻發"
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
