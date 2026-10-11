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


## sense 10156, level 7

#### Pack A
### Level 7 (sense 10156, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "随着出版物种类的丰富，除宗教文献外，科学论著、文学作品、法律文本乃至新闻小册子广泛流通，公众对知识的渴求被前所未有地激发。",
      "is_correct": true
    },
    {
      "text": "他带来了前所未有一个惊喜。",
      "is_correct": false,
      "error_description": "语序错误。数量词“一个”应放在形容词“前所未有”之前，正确语序为“一个前所未有的惊喜”。"
    },
    {
      "text": "这一突破不仅大幅降低了书籍的制作成本，更使《圣经》等文本得以以前所未有的速度和数量被复制，从而打破了教会对知识解释权的垄断。",
      "is_correct": true
    },
    {
      "text": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临前所未有的挑战。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "隨著出版物種類的豐富，除宗教文獻外，科學論著、文學作品、法律文本乃至新聞小冊子廣泛流通，公眾對知識的渴求被前所未有地激發。",
        "is_correct": true
      },
      {
        "text": "他帶來了前所未有一個驚喜。",
        "is_correct": false,
        "error_description": "語序錯誤。數量詞“一個”應放在形容詞“前所未有”之前，正確語序為“一個前所未有的驚喜”。"
      },
      {
        "text": "這一突破不僅大幅降低了書籍的製作成本，更使《聖經》等文本得以以前所未有的速度和數量被複制，從而打破了教會對知識解釋權的壟斷。",
        "is_correct": true
      },
      {
        "text": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨前所未有的挑戰。",
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
      "text": "她的热情达到了前所未有的高度。",
      "is_correct": true
    },
    {
      "text": "他带来了惊喜前所未有的。",
      "is_correct": false,
      "error_description": "“前所未有”是形容词，应放在名词“惊喜”前作定语。原句将其放在句末，造成语序错误，不符合汉语定语在前、中心语在后的基本语序规则。"
    },
    {
      "text": "他带来了前所未有的惊喜。",
      "is_correct": true
    },
    {
      "text": "这种友谊是前所未有的。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她的熱情達到了前所未有的高度。",
        "is_correct": true
      },
      {
        "text": "他帶來了驚喜前所未有的。",
        "is_correct": false,
        "error_description": "“前所未有”是形容詞，應放在名詞“驚喜”前作定語。原句將其放在句末，造成語序錯誤，不符合漢語定語在前、中心語在後的基本語序規則。"
      },
      {
        "text": "他帶來了前所未有的驚喜。",
        "is_correct": true
      },
      {
        "text": "這種友誼是前所未有的。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10156, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这次活动的规模是前所未有的。",
      "is_correct": true
    },
    {
      "text": "收到礼物时，我的开心是前所未有了。",
      "is_correct": false,
      "error_description": "体标选用错误。在‘是……的’结构中，句末应使用结构助词‘的’来强调状态，不能误用动态助词‘了’。"
    },
    {
      "text": "收到礼物时，我的开心是前所未有的。",
      "is_correct": true
    },
    {
      "text": "看到惊喜，我的感动是前所未有的。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這次活動的規模是前所未有的。",
        "is_correct": true
      },
      {
        "text": "收到禮物時，我的開心是前所未有了。",
        "is_correct": false,
        "error_description": "體標選用錯誤。在‘是……的’結構中，句末應使用結構助詞‘的’來強調狀態，不能誤用動態助詞‘了’。"
      },
      {
        "text": "收到禮物時，我的開心是前所未有的。",
        "is_correct": true
      },
      {
        "text": "看到驚喜，我的感動是前所未有的。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10300, level 1

#### Pack A
### Level 1 (sense 10300, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "长",
  "pronunciation": "cháng",
  "ipa": "[tʂʰɑŋ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "场",
    "长",
    "唱",
    "昌"
  ],
  "correct_answer": "长",
  "explanation": "正确。“长”读第二声（cháng），符合目标词的读音和“距离大”的释义。",
  "distractor_explanations": {
    "场": "声调错误。“场”读第三声（chǎng），指空地或聚会的地方；目标词“长”读第二声（cháng），指距离大。",
    "唱": "声调错误。“唱”读第四声（chàng），指发出声音或唱歌；目标词“长”读第二声（cháng），指距离大。",
    "昌": "声调错误。“昌”读第一声（chāng），指兴旺或美好；目标词“长”读第二声（cháng），指距离大。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[tʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "場",
      "長",
      "唱",
      "昌"
    ],
    "correct_answer": "長",
    "explanation": "正確。“長”讀第二聲（cháng），符合目標詞的讀音和“距離大”的釋義。",
    "distractor_explanations": {
      "场": "聲調錯誤。“場”讀第三聲（chǎng），指空地或聚會的地方；目標詞“長”讀第二聲（cháng），指距離大。",
      "唱": "聲調錯誤。“唱”讀第四聲（chàng），指發出聲音或唱歌；目標詞“長”讀第二聲（cháng），指距離大。",
      "昌": "聲調錯誤。“昌”讀第一聲（chāng），指興旺或美好；目標詞“長”讀第二聲（cháng），指距離大。"
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
    "重",
    "厚",
    "长",
    "远"
  ],
  "explanation": "正确。“长”准确描述了长城在空间上绵延不断的物理特征，符合语境。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "___城在中國北方，它很長很長。",
    "original_sentence": "長城在中國北方，它很長很長。",
    "correct_answer": "長",
    "options": [
      "重",
      "厚",
      "長",
      "遠"
    ],
    "explanation": "正確。“長”準確描述了長城在空間上綿延不斷的物理特徵，符合語境。",
    "distractor_tags": {},
    "word_definition": "指空間或時間上距離大，與‘短’相對。",
    "target_word": "長"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这部电影太___了，我看了两个小时。",
  "original_sentence": "这部电影太长了，我看了两个小时。",
  "correct_answer": "长",
  "options": [
    "大",
    "多",
    "高",
    "长"
  ],
  "explanation": "正确。符合语境，表示电影播放的时间距离大。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "這部電影太___了，我看了兩個小時。",
    "original_sentence": "這部電影太長了，我看了兩個小時。",
    "correct_answer": "長",
    "options": [
      "大",
      "多",
      "高",
      "長"
    ],
    "explanation": "正確。符合語境，表示電影播放的時間距離大。",
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

## sense 10300, level 7

#### Pack A
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

#### Pack B
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
      "text": "这条田埂比那条田埂很长。",
      "is_correct": false,
      "error_description": "在“比”字比较句中，形容词前不能使用“很”等程度副词，应直接使用形容词“长”，或使用“更”、“得多”等。"
    },
    {
      "text": "这条田埂很长，一眼望不到尽头。",
      "is_correct": true
    },
    {
      "text": "这种豆角很长，在菜市场很受欢迎。",
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
        "text": "這條田埂比那條田埂很長。",
        "is_correct": false,
        "error_description": "在“比”字比較句中，形容詞前不能使用“很”等程度副詞，應直接使用形容詞“長”，或使用“更”、“得多”等。"
      },
      {
        "text": "這條田埂很長，一眼望不到盡頭。",
        "is_correct": true
      },
      {
        "text": "這種豆角很長，在菜市場很受歡迎。",
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
      "text": "这条长长的公路一直走到海边。",
      "is_correct": true
    },
    {
      "text": "他的故事很长，我们坐着慢慢听。",
      "is_correct": true
    },
    {
      "text": "这部电影太长了，我看了两个小时。",
      "is_correct": true
    },
    {
      "text": "这部电影长太了，我看了两个小时。",
      "is_correct": false,
      "error_description": "“太……了”结构中，程度副词“太”应放在形容词“长”之前，且“了”放在句末。错误句子将“长”放在了“太”之前，导致语序错误。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這條長長的公路一直走到海邊。",
        "is_correct": true
      },
      {
        "text": "他的故事很長，我們坐著慢慢聽。",
        "is_correct": true
      },
      {
        "text": "這部電影太長了，我看了兩個小時。",
        "is_correct": true
      },
      {
        "text": "這部電影長太了，我看了兩個小時。",
        "is_correct": false,
        "error_description": "“太……了”結構中，程度副詞“太”應放在形容詞“長”之前，且“了”放在句末。錯誤句子將“長”放在了“太”之前，導致語序錯誤。"
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
    "再",
    "灾",
    "宰"
  ],
  "correct_answer": "再",
  "explanation": "正确。'再'读作 zài，表示动作或状态的重复或继续。",
  "distractor_explanations": {
    "栽": "错误。'栽'读作 zāi（第一声），声调不同，意为种植或跌倒，如'栽树'。",
    "宰": "错误。'宰'读作 zǎi（第三声），声调不同，意为杀牲畜或主管，如'宰羊'。",
    "灾": "错误。'灾'读作 zāi（第一声），声调不同，意为自然界或人为的损害，如'灾难'。"
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
      "再",
      "災",
      "宰"
    ],
    "correct_answer": "再",
    "explanation": "正確。'再'讀作 zài，表示動作或狀態的重複或繼續。",
    "distractor_explanations": {
      "栽": "錯誤。'栽'讀作 zāi（第一聲），聲調不同，意為種植或跌倒，如'栽樹'。",
      "宰": "錯誤。'宰'讀作 zǎi（第三聲），聲調不同，意為殺牲畜或主管，如'宰羊'。",
      "灾": "錯誤。'災'讀作 zāi（第一聲），聲調不同，意為自然界或人為的損害，如'災難'。"
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
      "text": "请把这本书看再一遍，你会喜欢的。",
      "is_correct": false
    },
    {
      "text": "他正在再写那篇没有完成的报告。",
      "is_correct": false
    },
    {
      "text": "他昨天没听清楚，再又问了老师一次。",
      "is_correct": false
    },
    {
      "text": "请把这本书再看一遍，你会喜欢的。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误。副词'再'应放在动词'看'之前，修饰整个动补结构'看一遍'，不能放在动词和数量补语之间。 体标选用错误。'再'表示未然或假设的重复，表示过去已经发生的动作重复应使用'又'，两者不能连用。 体貌冲突。'再'表示动作的重复或继续，通常不与表示动作正在进行的'正在'连用，两者在体貌上相互矛盾。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "請把這本書看再一遍，你會喜歡的。",
        "is_correct": false
      },
      {
        "text": "他正在再寫那篇沒有完成的報告。",
        "is_correct": false
      },
      {
        "text": "他昨天沒聽清楚，再又問了老師一次。",
        "is_correct": false
      },
      {
        "text": "請把這本書再看一遍，你會喜歡的。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤。副詞'再'應放在動詞'看'之前，修飾整個動補結構'看一遍'，不能放在動詞和數量補語之間。 體標選用錯誤。'再'表示未然或假設的重複，表示過去已經發生的動作重複應使用'又'，兩者不能連用。 體貌衝突。'再'表示動作的重複或繼續，通常不與表示動作正在進行的'正在'連用，兩者在體貌上相互矛盾。",
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
    "常",
    "初",
    "更",
    "全"
  ],
  "correct_answer": "初",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或状态的重复或继续。",
      "explanation": "反义项：作副词表第一次，与“再”表重复或继续构成反义"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "常",
      "初",
      "更",
      "全"
    ],
    "correct_answer": "初",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或狀態的重複或繼續。",
        "explanation": "反義項：作副詞表第一次，與“再”表重複或繼續構成反義"
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
      "text": "想清楚再决定着，不要让自己后悔。",
      "is_correct": false
    },
    {
      "text": "想清楚再决定了，不要让自己后悔。",
      "is_correct": false
    },
    {
      "text": "再想清楚决定，不要让自己后悔。",
      "is_correct": false
    },
    {
      "text": "想清楚再决定，不要让自己后悔。",
      "is_correct": true
    }
  ],
  "explanation": "体标选用错误：“再”表示动作尚未发生或即将重复，其后动词通常不与表示完成的动态助词“了”连用。 语序错误：副词“再”应紧挨在其修饰的动词“决定”之前，放在“想清楚”前会破坏条件与动作的顺承逻辑。 体标位置与选用错误：“着”表示动作或状态的持续，而“决定”是瞬间动词，不能与“着”搭配表示持续。",
  "target_word": "再",
  "hant": {
    "sentences": [
      {
        "text": "想清楚再決定著，不要讓自己後悔。",
        "is_correct": false
      },
      {
        "text": "想清楚再決定了，不要讓自己後悔。",
        "is_correct": false
      },
      {
        "text": "再想清楚決定，不要讓自己後悔。",
        "is_correct": false
      },
      {
        "text": "想清楚再決定，不要讓自己後悔。",
        "is_correct": true
      }
    ],
    "explanation": "體標選用錯誤：“再”表示動作尚未發生或即將重複，其後動詞通常不與表示完成的動態助詞“了”連用。 語序錯誤：副詞“再”應緊挨在其修飾的動詞“決定”之前，放在“想清楚”前會破壞條件與動作的順承邏輯。 體標位置與選用錯誤：“著”表示動作或狀態的持續，而“決定”是瞬間動詞，不能與“著”搭配表示持續。",
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
    "还",
    "刚",
    "又",
    "不再"
  ],
  "correct_answer": "不再",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示动作或状态的重复或继续。",
      "explanation": "副词，表示动作不重复或状态不继续，与目标词的“重复或继续”义项构成反义关系。"
    }
  },
  "hant": {
    "word": "再",
    "relation": "antonym",
    "options": [
      "還",
      "剛",
      "又",
      "不再"
    ],
    "correct_answer": "不再",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示動作或狀態的重複或繼續。",
        "explanation": "副詞，表示動作不重複或狀態不繼續，與目標詞的“重複或繼續”義項構成反義關係。"
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
      "text": "他们观察升力和阻力的变化，再改进设计。",
      "is_correct": true
    },
    {
      "text": "我们先吃完晚饭，再去公园散步吧。",
      "is_correct": true
    },
    {
      "text": "等到干旱时，再把这些水用来灌溉农田。",
      "is_correct": true
    },
    {
      "text": "请你再一遍说。",
      "is_correct": false,
      "error_description": "副词“再”应放在动词前，动量补语“一遍”应放在动词后。正确语序为“再+动词+动量补语”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他們觀察升力和阻力的變化，再改進設計。",
        "is_correct": true
      },
      {
        "text": "我們先吃完晚飯，再去公園散步吧。",
        "is_correct": true
      },
      {
        "text": "等到乾旱時，再把這些水用來灌溉農田。",
        "is_correct": true
      },
      {
        "text": "請你再一遍說。",
        "is_correct": false,
        "error_description": "副詞“再”應放在動詞前，動量補語“一遍”應放在動詞後。正確語序為“再+動詞+動量補語”。"
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
      "text": "想清楚再决定，不要让自己后悔。",
      "is_correct": true
    },
    {
      "text": "你把心事再跟她说一遍吧。",
      "is_correct": true
    },
    {
      "text": "他再想问一次老师，因为昨天没听清楚。",
      "is_correct": false,
      "error_description": "副词“再”应该放在能愿动词“想”之后、主要动词“问”之前，不能放在能愿动词之前。"
    },
    {
      "text": "大家休息一会儿，再继续讨论这个问题。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "想清楚再決定，不要讓自己後悔。",
        "is_correct": true
      },
      {
        "text": "你把心事再跟她說一遍吧。",
        "is_correct": true
      },
      {
        "text": "他再想問一次老師，因為昨天沒聽清楚。",
        "is_correct": false,
        "error_description": "副詞“再”應該放在能願動詞“想”之後、主要動詞“問”之前，不能放在能願動詞之前。"
      },
      {
        "text": "大家休息一會兒，再繼續討論這個問題。",
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

#### Pack B
### Level 3 (sense 10382, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "每个国家有___规定。",
  "original_sentence": "每个国家有不同规定。",
  "correct_answer": "不同",
  "options": [
    "相等",
    "不同",
    "一致",
    "相同"
  ],
  "explanation": "正确。'不同'修饰'规定'，准确表达了各个国家规定之间的差异。",
  "distractor_tags": {},
  "word_definition": "指事物之间没有共同点，有差别。",
  "target_word": "不同",
  "hant": {
    "sentence_with_blank": "每個國家有___規定。",
    "original_sentence": "每個國家有不同規定。",
    "correct_answer": "不同",
    "options": [
      "相等",
      "不同",
      "一致",
      "相同"
    ],
    "explanation": "正確。'不同'修飾'規定'，準確表達了各個國家規定之間的差異。",
    "distractor_tags": {},
    "word_definition": "指事物之間沒有共同點，有差別。",
    "target_word": "不同"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这个过程连接了___国家的农民、公司和普通消费者。",
  "original_sentence": "这个过程连接了不同国家的农民、公司和普通消费者。",
  "correct_answer": "不同",
  "options": [
    "相似",
    "相同",
    "不同",
    "一致"
  ],
  "explanation": "正确。",
  "distractor_tags": {},
  "word_definition": "指事物之间没有共同点，有差别。",
  "target_word": "不同",
  "hant": {
    "sentence_with_blank": "這個過程連線了___國家的農民、公司和普通消費者。",
    "original_sentence": "這個過程連線了不同國家的農民、公司和普通消費者。",
    "correct_answer": "不同",
    "options": [
      "相似",
      "相同",
      "不同",
      "一致"
    ],
    "explanation": "正確。",
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
      "text": "不同让全球化文化的人常见面。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人见面了常见。",
      "is_correct": false
    },
    {
      "text": "全球化让不同文化的人常见面。",
      "is_correct": true
    },
    {
      "text": "全球化让不同文化的人常见面着。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：'着'表示动作正在进行或状态持续，不能放在句末作为'见面'的补语，应去掉'着'或改为'经常见面'。 语序错误：'不同'是形容词，不能直接作主语放在句首，应修饰'文化'，保持'不同文化'的结构。 语序错误：'常见'是副词+形容词，不能放在动词'见面'之后作补语，应调整为'经常见面'或'常见面'。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "不同讓全球化文化的人常見面。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人見面了常見。",
        "is_correct": false
      },
      {
        "text": "全球化讓不同文化的人常見面。",
        "is_correct": true
      },
      {
        "text": "全球化讓不同文化的人常見面著。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：'著'表示動作正在進行或狀態持續，不能放在句末作為'見面'的補語，應去掉'著'或改為'經常見面'。 語序錯誤：'不同'是形容詞，不能直接作主語放在句首，應修飾'文化'，保持'不同文化'的結構。 語序錯誤：'常見'是副詞+形容詞，不能放在動詞'見面'之後作補語，應調整為'經常見面'或'常見面'。",
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
    "相反",
    "相关"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "「相同」表示事物之间没有差别，与「不同」（有差别）构成直接反义关系。"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相似",
      "相同",
      "相反",
      "相關"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "「相同」表示事物之間沒有差別，與「不同」（有差別）構成直接反義關係。"
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
      "text": "不同的地方有不同的记谱法着。",
      "is_correct": false
    },
    {
      "text": "地方不同的有不同的记谱法。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法起来。",
      "is_correct": false
    },
    {
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：动态助词“着”表示动作持续或状态保持，不能放在名词性短语“记谱法”之后。 语序错误：定语“不同”应紧贴中心语“地方”，原句语序破坏了“主题—评论”结构，导致句子不通顺。 方向补语误用：“起来”通常作趋向补语跟在动词后表示动作开始，不能直接放在名词“记谱法”后作句末成分。",
  "target_word": "不同",
  "hant": {
    "sentences": [
      {
        "text": "不同的地方有不同的記譜法著。",
        "is_correct": false
      },
      {
        "text": "地方不同的有不同的記譜法。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法起來。",
        "is_correct": false
      },
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：動態助詞“著”表示動作持續或狀態保持，不能放在名詞性短語“記譜法”之後。 語序錯誤：定語“不同”應緊貼中心語“地方”，原句語序破壞了“主題—評論”結構，導致句子不通順。 方向補語誤用：“起來”通常作趨向補語跟在動詞後表示動作開始，不能直接放在名詞“記譜法”後作句末成分。",
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
    "相仿",
    "悬殊",
    "相似"
  ],
  "correct_answer": "相同",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物之间没有共同点，有差别。",
      "explanation": "表示事物之间没有差别，与目标词“不同”构成反义关系"
    }
  },
  "hant": {
    "word": "不同",
    "relation": "antonym",
    "options": [
      "相同",
      "相仿",
      "懸殊",
      "相似"
    ],
    "correct_answer": "相同",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物之間沒有共同點，有差別。",
        "explanation": "表示事物之間沒有差別，與目標詞“不同”構成反義關係"
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
      "text": "不同地方的人看时间不一样。",
      "is_correct": true
    },
    {
      "text": "每个国家有不同规定。",
      "is_correct": true
    },
    {
      "text": "不同地方的人对时间的看法不一样。",
      "is_correct": true
    },
    {
      "text": "每个国家有了不同规定。",
      "is_correct": false,
      "error_description": "体标误用。动词“有”表示客观存在或领属时，其后通常不加动态助词“了”；此处描述客观事实，直接使用“有”即可。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "不同地方的人看時間不一樣。",
        "is_correct": true
      },
      {
        "text": "每個國家有不同規定。",
        "is_correct": true
      },
      {
        "text": "不同地方的人對時間的看法不一樣。",
        "is_correct": true
      },
      {
        "text": "每個國家有了不同規定。",
        "is_correct": false,
        "error_description": "體標誤用。動詞“有”表示客觀存在或領屬時，其後通常不加動態助詞“了”；此處描述客觀事實，直接使用“有”即可。"
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
      "text": "他的意见不同我的意见。",
      "is_correct": false,
      "error_description": "“不同”是形容词，不能直接带宾语。表示两者比较时，应使用“和/跟/与……不同”的句型。"
    },
    {
      "text": "不同国家采取了不同的监管方法。",
      "is_correct": true
    },
    {
      "text": "这个过程连接了不同国家的农民、公司和普通消费者。",
      "is_correct": true
    },
    {
      "text": "不同的地方有不同的记谱法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的意見不同我的意見。",
        "is_correct": false,
        "error_description": "“不同”是形容詞，不能直接帶賓語。表示兩者比較時，應使用“和/跟/與……不同”的句型。"
      },
      {
        "text": "不同國家採取了不同的監管方法。",
        "is_correct": true
      },
      {
        "text": "這個過程連線了不同國家的農民、公司和普通消費者。",
        "is_correct": true
      },
      {
        "text": "不同的地方有不同的記譜法。",
        "is_correct": true
      }
    ]
  }
}
```

---
