# Pairwise review pack 01

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


## sense 10103, level 1

#### Pack A
### Level 1 (sense 10103, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "ipa": "[tsaʊ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "早",
    "灶",
    "凿",
    "糟"
  ],
  "correct_answer": "早",
  "explanation": "正确：“早”读第三声（zǎo），指太阳刚升起或时间靠前的时段，符合目标词的语音和语义。",
  "distractor_explanations": {
    "糟": "声调错误：“糟”读第一声（zāo），意思是坏、糟糕，与目标词“早”的第三声不同，声调改变导致意义完全不同。",
    "凿": "声调错误：“凿”读第二声（záo），意思是打孔或挖掘工具，与目标词“早”的第三声不同，声调改变导致意义完全不同。",
    "灶": "声调错误：“灶”读第四声（zào），意思是生火做饭的设备，与目标词“早”的第三声不同，声调改变导致意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsaʊ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "早",
      "灶",
      "鑿",
      "糟"
    ],
    "correct_answer": "早",
    "explanation": "正確：“早”讀第三聲（zǎo），指太陽剛升起或時間靠前的時段，符合目標詞的語音和語義。",
    "distractor_explanations": {
      "糟": "聲調錯誤：“糟”讀第一聲（zāo），意思是壞、糟糕，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。",
      "凿": "聲調錯誤：“鑿”讀第二聲（záo），意思是打孔或挖掘工具，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。",
      "灶": "聲調錯誤：“灶”讀第四聲（zào），意思是生火做飯的裝置，與目標詞“早”的第三聲不同，聲調改變導致意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10103, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "ipa": "[tsɑʊ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "糟",
    "皂",
    "凿",
    "早"
  ],
  "correct_answer": "早",
  "explanation": "正确：'早'读第三声（zǎo），指太阳刚升起或时间靠前的时段，符合听到的语音。",
  "distractor_explanations": {
    "糟": "声调混淆：'糟'读第一声（zāo），意思是坏、糟糕，与表示时间靠前的'早'（zǎo）声调不同，意义也不同。",
    "凿": "声调混淆：'凿'读第二声（záo），意思是挖掘或打孔，与'早'（zǎo）声调不同，意义完全不同。",
    "皂": "声调混淆：'皂'读第四声（zào），指肥皂或黑色，与'早'（zǎo）声调不同，意义无关。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsɑʊ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "糟",
      "皂",
      "鑿",
      "早"
    ],
    "correct_answer": "早",
    "explanation": "正確：'早'讀第三聲（zǎo），指太陽剛升起或時間靠前的時段，符合聽到的語音。",
    "distractor_explanations": {
      "糟": "聲調混淆：'糟'讀第一聲（zāo），意思是壞、糟糕，與表示時間靠前的'早'（zǎo）聲調不同，意義也不同。",
      "凿": "聲調混淆：'鑿'讀第二聲（záo），意思是挖掘或打孔，與'早'（zǎo）聲調不同，意義完全不同。",
      "皂": "聲調混淆：'皂'讀第四聲（zào），指肥皂或黑色，與'早'（zǎo）聲調不同，意義無關。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10103, level 3

#### Pack A
### Level 3 (sense 10103, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他今天来得很___，我们一起去吃饭。",
  "original_sentence": "他今天来得很早，我们一起去吃饭。",
  "correct_answer": "早",
  "options": [
    "晚",
    "早",
    "远",
    "多"
  ],
  "explanation": "正确：“早”表示时间靠前，符合句中提前到达以便一起吃饭的语境。",
  "distractor_tags": {},
  "word_definition": "指太阳刚升起或时间靠前的时段。",
  "target_word": "早",
  "hant": {
    "sentence_with_blank": "他今天來得很___，我們一起去吃飯。",
    "original_sentence": "他今天來得很早，我們一起去吃飯。",
    "correct_answer": "早",
    "options": [
      "晚",
      "早",
      "遠",
      "多"
    ],
    "explanation": "正確：“早”表示時間靠前，符合句中提前到達以便一起吃飯的語境。",
    "distractor_tags": {},
    "word_definition": "指太陽剛升起或時間靠前的時段。",
    "target_word": "早"
  }
}
```

#### Pack B
### Level 3 (sense 10103, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "现在讨论这个问题太___了。",
  "original_sentence": "现在讨论这个问题太早了。",
  "correct_answer": "早",
  "options": [
    "先",
    "早",
    "远",
    "完"
  ],
  "explanation": "正确：'早'表示时间靠前，填入句中表示现在讨论这个问题的时机还未到，符合语境。",
  "distractor_tags": {},
  "word_definition": "指太阳刚升起或时间靠前的时段。",
  "target_word": "早",
  "hant": {
    "sentence_with_blank": "現在討論這個問題太___了。",
    "original_sentence": "現在討論這個問題太早了。",
    "correct_answer": "早",
    "options": [
      "先",
      "早",
      "遠",
      "完"
    ],
    "explanation": "正確：'早'表示時間靠前，填入句中表示現在討論這個問題的時機還未到，符合語境。",
    "distractor_tags": {},
    "word_definition": "指太陽剛升起或時間靠前的時段。",
    "target_word": "早"
  }
}
```

---

## sense 10103, level 6

#### Pack A
### Level 6 (sense 10103, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们出发早得，没遇到堵车。",
      "is_correct": false
    },
    {
      "text": "早我们出发得，没遇到堵车。",
      "is_correct": false
    },
    {
      "text": "我们出发得早，没遇到堵车。",
      "is_correct": true
    },
    {
      "text": "我们出发得早着，没遇到堵车。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：时间/状态状语'早'和补语标记'得'的位置颠倒。正确的语序应为'出发得早'，'早'应放在'得'之后作程度/状态补语。 体标选用错误：'着'表示动作或状态的持续，而'出发'是一个瞬间动作，且此处强调出发的时间属性而非持续状态，应使用结构助词'得'引出补语'早'。 语序错误：结构助词'得'的位置错误。在动补结构中，'得'必须紧跟在动词之后，引出后面的补语，正确语序为'出发得早'。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "我們出發早得，沒遇到堵車。",
        "is_correct": false
      },
      {
        "text": "早我們出發得，沒遇到堵車。",
        "is_correct": false
      },
      {
        "text": "我們出發得早，沒遇到堵車。",
        "is_correct": true
      },
      {
        "text": "我們出發得早著，沒遇到堵車。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：時間/狀態狀語'早'和補語標記'得'的位置顛倒。正確的語序應為'出發得早'，'早'應放在'得'之後作程度/狀態補語。 體標選用錯誤：'著'表示動作或狀態的持續，而'出發'是一個瞬間動作，且此處強調出發的時間屬性而非持續狀態，應使用結構助詞'得'引出補語'早'。 語序錯誤：結構助詞'得'的位置錯誤。在動補結構中，'得'必須緊跟在動詞之後，引出後面的補語，正確語序為'出發得早'。",
    "target_word": "早"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "早",
  "relation": "antonym",
  "options": [
    "晚",
    "迟",
    "快",
    "久"
  ],
  "correct_answer": "晚",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指太阳刚升起或时间靠前的时段。",
      "explanation": "反义项：「晚」指太阳已落或时间靠后的时段，与「早」的时间靠前义构成反义"
    }
  },
  "hant": {
    "word": "早",
    "relation": "antonym",
    "options": [
      "晚",
      "遲",
      "快",
      "久"
    ],
    "correct_answer": "晚",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指太陽剛升起或時間靠前的時段。",
        "explanation": "反義項：「晚」指太陽已落或時間靠後的時段，與「早」的時間靠前義構成反義"
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
      "text": "早去了能占到好座位。",
      "is_correct": false
    },
    {
      "text": "早去能占到好座位。",
      "is_correct": true
    },
    {
      "text": "早去能占到好座位们。",
      "is_correct": false
    },
    {
      "text": "能早去占到好座位。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“座位”是普通名词，不能使用表示复数的后缀“们”，应直接说“好座位”。 体标位置错误：句中的“能”表示一种可能性或条件结果，前面不应加表示完成的“了”，否则会破坏条件句的语感。 语序错误：表示条件的“早去”应该放在能愿动词“能”的前面，以突出“早去”是“占到好座位”的前提条件。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "早去了能佔到好座位。",
        "is_correct": false
      },
      {
        "text": "早去能佔到好座位。",
        "is_correct": true
      },
      {
        "text": "早去能佔到好座位們。",
        "is_correct": false
      },
      {
        "text": "能早去佔到好座位。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“座位”是普通名詞，不能使用表示複數的字尾“們”，應直接說“好座位”。 體標位置錯誤：句中的“能”表示一種可能性或條件結果，前面不應加表示完成的“了”，否則會破壞條件句的語感。 語序錯誤：表示條件的“早去”應該放在能願動詞“能”的前面，以突出“早去”是“佔到好座位”的前提條件。",
    "target_word": "早"
  }
}
```

#### Pack B
### Level 6 (sense 10103, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "今年的春天很早，公园里的花儿都开着。",
      "is_correct": true
    },
    {
      "text": "今年的春天早了着，公园里的花儿都开着。",
      "is_correct": false
    },
    {
      "text": "今年的春天早出来，公园里的花儿都开着。",
      "is_correct": false
    },
    {
      "text": "很早今年的春天，公园里的花儿都开着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“早”是性质形容词，不能直接加动态助词“了”和“着”来表示动作的持续或完成。 语序错误：“很早”作为形容词短语，不能直接放在主语“今年的春天”之前作定语或状语，应放在主语之后作谓语。 结果补语误用：“早”表示时间靠前，不能带结果补语“出来”表示空间或状态的显现。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "今年的春天很早，公園裡的花兒都開著。",
        "is_correct": true
      },
      {
        "text": "今年的春天早了著，公園裡的花兒都開著。",
        "is_correct": false
      },
      {
        "text": "今年的春天早出來，公園裡的花兒都開著。",
        "is_correct": false
      },
      {
        "text": "很早今年的春天，公園裡的花兒都開著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“早”是性質形容詞，不能直接加動態助詞“了”和“著”來表示動作的持續或完成。 語序錯誤：“很早”作為形容詞短語，不能直接放在主語“今年的春天”之前作定語或狀語，應放在主語之後作謂語。 結果補語誤用：“早”表示時間靠前，不能帶結果補語“出來”表示空間或狀態的顯現。",
    "target_word": "早"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "早点你把心情调整好，别再生气了。",
      "is_correct": false
    },
    {
      "text": "你早点把心情调整早，别再生气了。",
      "is_correct": false
    },
    {
      "text": "你早点把心情调整好，别再生气了。",
      "is_correct": true
    },
    {
      "text": "你早着把心情调整好，别再生气了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“早”表示时间靠前的状态，不是持续性的动作，不能加动态助词“着”。 语序错误：时间状语“早点”应放在主语“你”之后、谓语之前，不能置于句首。 结果补语误用：“调整”的结果补语应为表示状态改变的词（如“好”），不能用表示时间的“早”作补语。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "早點你把心情調整好，別再生氣了。",
        "is_correct": false
      },
      {
        "text": "你早點把心情調整早，別再生氣了。",
        "is_correct": false
      },
      {
        "text": "你早點把心情調整好，別再生氣了。",
        "is_correct": true
      },
      {
        "text": "你早著把心情調整好，別再生氣了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“早”表示時間靠前的狀態，不是持續性的動作，不能加動態助詞“著”。 語序錯誤：時間狀語“早點”應放在主語“你”之後、謂語之前，不能置於句首。 結果補語誤用：“調整”的結果補語應為表示狀態改變的詞（如“好”），不能用表示時間的“早”作補語。",
    "target_word": "早"
  }
}
```

---

## sense 10103, level 7

#### Pack A
### Level 7 (sense 10103, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们早点出发，免得错过精彩的表演。",
      "is_correct": true
    },
    {
      "text": "你昨晚睡得很早，今天上课没有犯困。",
      "is_correct": true
    },
    {
      "text": "他来得很早昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”位置错误，不能放在句末，应放在主语之后、谓语之前。"
    },
    {
      "text": "他今天来得很早，我们一起去吃饭。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們早點出發，免得錯過精彩的表演。",
        "is_correct": true
      },
      {
        "text": "你昨晚睡得很早，今天上課沒有犯困。",
        "is_correct": true
      },
      {
        "text": "他來得很早昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”位置錯誤，不能放在句末，應放在主語之後、謂語之前。"
      },
      {
        "text": "他今天來得很早，我們一起去吃飯。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10103, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他每天早起床去跑步。",
      "is_correct": false,
      "error_description": "语序错误。形容词“早”不能直接放在动词前作状语，应放在动词后作补语，并用“得”连接，即“起得很早”。"
    },
    {
      "text": "他每天醒得很早。",
      "is_correct": true
    },
    {
      "text": "请你早点把作业写完吧。",
      "is_correct": true
    },
    {
      "text": "现在讨论这个问题太早了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他每天早起床去跑步。",
        "is_correct": false,
        "error_description": "語序錯誤。形容詞“早”不能直接放在動詞前作狀語，應放在動詞後作補語，並用“得”連線，即“起得很早”。"
      },
      {
        "text": "他每天醒得很早。",
        "is_correct": true
      },
      {
        "text": "請你早點把作業寫完吧。",
        "is_correct": true
      },
      {
        "text": "現在討論這個問題太早了。",
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
      "text": "你早来一点，就能见到他了。",
      "is_correct": false,
      "error_description": "语序错误。当“早”与表示时间量或程度的“一点”连用时，正确的语序应为“早一点 + 动词”，而不是“早 + 一点 + 动词”。"
    },
    {
      "text": "现在说放弃还太早。",
      "is_correct": true
    },
    {
      "text": "大家早点把教室打扫干净。",
      "is_correct": true
    },
    {
      "text": "早去能占到好座位。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "你早來一點，就能見到他了。",
        "is_correct": false,
        "error_description": "語序錯誤。當“早”與表示時間量或程度的“一點”連用時，正確的語序應為“早一點 + 動詞”，而不是“早 + 一點 + 動詞”。"
      },
      {
        "text": "現在說放棄還太早。",
        "is_correct": true
      },
      {
        "text": "大家早點把教室打掃乾淨。",
        "is_correct": true
      },
      {
        "text": "早去能佔到好座位。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10104, level 1

#### Pack A
### Level 1 (sense 10104, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "ipa": "[piɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "便",
    "边",
    "编",
    "扁"
  ],
  "correct_answer": "便",
  "explanation": "正确选项。读作第四声（biàn），表示就、立刻或容易，符合听力发音。",
  "distractor_explanations": {
    "边": "声调为第一声（biān），指边缘或旁边，与目标词第四声（biàn）声调不同。",
    "扁": "声调为第三声（biǎn），指物体平而薄，与目标词第四声（biàn）声调不同。",
    "编": "声调为第一声（biān），指把细长条的东西交叉组织起来，与目标词第四声（biàn）声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[piɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "便",
      "邊",
      "編",
      "扁"
    ],
    "correct_answer": "便",
    "explanation": "正確選項。讀作第四聲（biàn），表示就、立刻或容易，符合聽力發音。",
    "distractor_explanations": {
      "边": "聲調為第一聲（biān），指邊緣或旁邊，與目標詞第四聲（biàn）聲調不同。",
      "扁": "聲調為第三聲（biǎn），指物體平而薄，與目標詞第四聲（biàn）聲調不同。",
      "编": "聲調為第一聲（biān），指把細長條的東西交叉組織起來，與目標詞第四聲（biàn）聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10104, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "便",
  "pronunciation": "biàn",
  "ipa": "[pi̯ɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "便",
    "边",
    "扁",
    "变"
  ],
  "correct_answer": "便",
  "explanation": "正确：“便”读第四声（biàn），符合听到的发音。",
  "distractor_explanations": {
    "边": "声调错误：“边”读第一声（biān），而目标词“便”在此处读第四声（biàn）。",
    "扁": "声调错误：“扁”读第三声（biǎn），而目标词“便”在此处读第四声（biàn）。",
    "变": "同音字混淆：“变”与“便”同音同调（biàn），但字形和意义不同，此处需选表示“就”的副词“便”。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[pi̯ɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "便",
      "邊",
      "扁",
      "變"
    ],
    "correct_answer": "便",
    "explanation": "正確：“便”讀第四聲（biàn），符合聽到的發音。",
    "distractor_explanations": {
      "边": "聲調錯誤：“邊”讀第一聲（biān），而目標詞“便”在此處讀第四聲（biàn）。",
      "扁": "聲調錯誤：“扁”讀第三聲（biǎn），而目標詞“便”在此處讀第四聲（biàn）。",
      "变": "同音字混淆：“變”與“便”同音同調（biàn），但字形和意義不同，此處需選表示“就”的副詞“便”。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10104, level 6

#### Pack A
### Level 6 (sense 10104, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师一讲我便明白下去了。",
      "is_correct": false
    },
    {
      "text": "老师一讲我便明白了。",
      "is_correct": true
    },
    {
      "text": "老师一讲我便明白着。",
      "is_correct": false
    },
    {
      "text": "昨天我便老师一讲明白了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“明白”表示认知状态的达成，不能用“着”表示动作持续，应使用“了”表示状态实现。 语序错误：副词“便”不能放在主语“老师”之前，且时间状语与主语位置错乱，破坏了句子的基本语序。 方向/结果补语误用：“下去”表示动作或状态的继续，而“一……便……”结构强调动作的即时达成，两者在语义上矛盾。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "老師一講我便明白下去了。",
        "is_correct": false
      },
      {
        "text": "老師一講我便明白了。",
        "is_correct": true
      },
      {
        "text": "老師一講我便明白著。",
        "is_correct": false
      },
      {
        "text": "昨天我便老師一講明白了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“明白”表示認知狀態的達成，不能用“著”表示動作持續，應使用“了”表示狀態實現。 語序錯誤：副詞“便”不能放在主語“老師”之前，且時間狀語與主語位置錯亂，破壞了句子的基本語序。 方向/結果補語誤用：“下去”表示動作或狀態的繼續，而“一……便……”結構強調動作的即時達成，兩者在語義上矛盾。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "才",
    "即",
    "就",
    "还"
  ],
  "correct_answer": "才",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示做某事不费力气或时间很短。",
      "explanation": "副词，表示事情发生得晚或经过较长时间，与目标词表示时间短、不费力构成反义"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "才",
      "即",
      "就",
      "還"
    ],
    "correct_answer": "才",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示做某事不費力氣或時間很短。",
        "explanation": "副詞，表示事情發生得晚或經過較長時間，與目標詞表示時間短、不費力構成反義"
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
      "text": "便大家讨论完有了好观点。",
      "is_correct": false
    },
    {
      "text": "大家讨论完便有了好观点。",
      "is_correct": true
    },
    {
      "text": "大家讨论完便有着好观点。",
      "is_correct": false
    },
    {
      "text": "大家讨论完便有了过好观点。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：副词“便”不能放在主语“大家”之前，应放在主语之后、谓语之前。 体标位置错误：动态助词“过”应放在动词“有”之后，不能放在“了”之后，此处直接用“了”表示完成即可。 体标选用错误：“着”表示动作持续或状态保持，与前面的“完”及结果“有”相矛盾，应使用“了”。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "便大家討論完有了好觀點。",
        "is_correct": false
      },
      {
        "text": "大家討論完便有了好觀點。",
        "is_correct": true
      },
      {
        "text": "大家討論完便有著好觀點。",
        "is_correct": false
      },
      {
        "text": "大家討論完便有了過好觀點。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：副詞“便”不能放在主語“大家”之前，應放在主語之後、謂語之前。 體標位置錯誤：動態助詞“過”應放在動詞“有”之後，不能放在“了”之後，此處直接用“了”表示完成即可。 體標選用錯誤：“著”表示動作持續或狀態保持，與前面的“完”及結果“有”相矛盾，應使用“了”。",
    "target_word": "便"
  }
}
```

#### Pack B
### Level 6 (sense 10104, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "听一遍这首歌她便唱会了。",
      "is_correct": false
    },
    {
      "text": "这首歌她听一遍便会唱了。",
      "is_correct": true
    },
    {
      "text": "这首歌她听一遍便唱着了。",
      "is_correct": false
    },
    {
      "text": "这首歌她听一遍便会了唱。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：能愿动词或结果补语“会”与动词“唱”的语序不当，应直接说“便会唱”，加“了”破坏了“一……便……”后接简单动词短语的紧凑结构。 体标选用错误：“着”表示动作持续或状态保持，而原句强调动作瞬间完成并掌握，“便”后应接表示完成的“了”或直接接动词，用“着”导致体貌冲突。 语序错误：条件状语“听一遍”被拆分且位置错乱，破坏了“主语 + 一 + 动词 + 宾语 + 便 + 结果”的自然语序，导致句子结构松散、不自然。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "聽一遍這首歌她便唱會了。",
        "is_correct": false
      },
      {
        "text": "這首歌她聽一遍便會唱了。",
        "is_correct": true
      },
      {
        "text": "這首歌她聽一遍便唱著了。",
        "is_correct": false
      },
      {
        "text": "這首歌她聽一遍便會了唱。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：能願動詞或結果補語“會”與動詞“唱”的語序不當，應直接說“便會唱”，加“了”破壞了“一……便……”後接簡單動詞短語的緊湊結構。 體標選用錯誤：“著”表示動作持續或狀態保持，而原句強調動作瞬間完成並掌握，“便”後應接表示完成的“了”或直接接動詞，用“著”導致體貌衝突。 語序錯誤：條件狀語“聽一遍”被拆分且位置錯亂，破壞了“主語 + 一 + 動詞 + 賓語 + 便 + 結果”的自然語序，導致句子結構鬆散、不自然。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "才",
    "难",
    "快",
    "就"
  ],
  "correct_answer": "难",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短，常与“一”连用。",
      "explanation": "反义：目标词表'不费力气、很快就能'，'难'表'费力气、不容易'，如'听一遍便会'与'听多遍也难'相对"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "才",
      "難",
      "快",
      "就"
    ],
    "correct_answer": "難",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短，常與“一”連用。",
        "explanation": "反義：目標詞表'不費力氣、很快就能'，'難'表'費力氣、不容易'，如'聽一遍便會'與'聽多遍也難'相對"
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
      "text": "他一试便了成功。",
      "is_correct": false
    },
    {
      "text": "试一他便成功了。",
      "is_correct": false
    },
    {
      "text": "他一试便成功了。",
      "is_correct": true
    },
    {
      "text": "他一试便成功去。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：“了”作为完成体标记，应放在动词“成功”之后（便成功了），放在“便”后破坏了副词修饰动词的结构。 语序错误：条件状语“一试”应放在主语“他”之后或句首，放在主语前导致“主题—评论”结构破坏，句子不通顺。 方向/结果补语误用：“去”表示动作远离说话人，而“成功”是内在结果状态，不能与趋向补语“去”搭配，应使用“了”。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "他一試便了成功。",
        "is_correct": false
      },
      {
        "text": "試一他便成功了。",
        "is_correct": false
      },
      {
        "text": "他一試便成功了。",
        "is_correct": true
      },
      {
        "text": "他一試便成功去。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：“了”作為完成體標記，應放在動詞“成功”之後（便成功了），放在“便”後破壞了副詞修飾動詞的結構。 語序錯誤：條件狀語“一試”應放在主語“他”之後或句首，放在主語前導致“主題—評論”結構破壞，句子不通順。 方向/結果補語誤用：“去”表示動作遠離說話人，而“成功”是內在結果狀態，不能與趨向補語“去”搭配，應使用“了”。",
    "target_word": "便"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "易",
    "快",
    "难",
    "正"
  ],
  "correct_answer": "难",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短，常与“一”连用。",
      "explanation": "反义项：表示做某事费力气或不容易，与目标词的不费力气构成反义"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "易",
      "快",
      "難",
      "正"
    ],
    "correct_answer": "難",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短，常與“一”連用。",
        "explanation": "反義項：表示做某事費力氣或不容易，與目標詞的不費力氣構成反義"
      }
    }
  }
}
```

---

## sense 10104, level 7

#### Pack A
### Level 7 (sense 10104, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他一学便了会这道题。",
      "is_correct": false,
      "error_description": "“便”是副词，修饰动词“会”，“了”是动态助词，应放在动词或结果补语之后。此处“了”误放在“便”和“会”之间，正确写法为“便会了”。"
    },
    {
      "text": "我一看便知道他的心情。",
      "is_correct": true
    },
    {
      "text": "他一学便会了这道题。",
      "is_correct": true
    },
    {
      "text": "我们一见面便聊得很开心。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他一學便了會這道題。",
        "is_correct": false,
        "error_description": "“便”是副詞，修飾動詞“會”，“了”是動態助詞，應放在動詞或結果補語之後。此處“了”誤放在“便”和“會”之間，正確寫法為“便會了”。"
      },
      {
        "text": "我一看便知道他的心情。",
        "is_correct": true
      },
      {
        "text": "他一學便會了這道題。",
        "is_correct": true
      },
      {
        "text": "我們一見面便聊得很開心。",
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
      "text": "这首古诗他读两遍便会。",
      "is_correct": true
    },
    {
      "text": "我把心事一说便轻松了。",
      "is_correct": true
    },
    {
      "text": "把作业一写他便去打球了。",
      "is_correct": false,
      "error_description": "“把”字句语序错误。“把”字及其宾语必须放在主语之后、谓语动词之前，不能放在主语之前。"
    },
    {
      "text": "大家讨论完便有了好观点。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這首古詩他讀兩遍便會。",
        "is_correct": true
      },
      {
        "text": "我把心事一說便輕鬆了。",
        "is_correct": true
      },
      {
        "text": "把作業一寫他便去打球了。",
        "is_correct": false,
        "error_description": "“把”字句語序錯誤。“把”字及其賓語必須放在主語之後、謂語動詞之前，不能放在主語之前。"
      },
      {
        "text": "大家討論完便有了好觀點。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10104, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "她把作业一写便交上去了。",
      "is_correct": true
    },
    {
      "text": "他一学便会了这道数学题。",
      "is_correct": true
    },
    {
      "text": "我一看便知道他在撒谎。",
      "is_correct": true
    },
    {
      "text": "他一学便了会这道数学题。",
      "is_correct": false,
      "error_description": "体标位置错误。动态助词“了”表示动作完成，应放在动词“会”之后，而不是副词“便”之后。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她把作業一寫便交上去了。",
        "is_correct": true
      },
      {
        "text": "他一學便會了這道數學題。",
        "is_correct": true
      },
      {
        "text": "我一看便知道他在撒謊。",
        "is_correct": true
      },
      {
        "text": "他一學便了會這道數學題。",
        "is_correct": false,
        "error_description": "體標位置錯誤。動態助詞“了”表示動作完成，應放在動詞“會”之後，而不是副詞“便”之後。"
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
      "text": "他一试便成功了。",
      "is_correct": true
    },
    {
      "text": "老师一讲我便明白了。",
      "is_correct": true
    },
    {
      "text": "他把球一扔便进了篮筐。",
      "is_correct": true
    },
    {
      "text": "他把球一扔便于进了篮筐。",
      "is_correct": false,
      "error_description": "语序与成分多余错误：副词“便”直接修饰动词“进”，后面不能加介词“于”。应删去“于”，保持“便+动词”的正确结构。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他一試便成功了。",
        "is_correct": true
      },
      {
        "text": "老師一講我便明白了。",
        "is_correct": true
      },
      {
        "text": "他把球一扔便進了籃筐。",
        "is_correct": true
      },
      {
        "text": "他把球一扔便於進了籃筐。",
        "is_correct": false,
        "error_description": "語序與成分多餘錯誤：副詞“便”直接修飾動詞“進”，後面不能加介詞“於”。應刪去“於”，保持“便+動詞”的正確結構。"
      }
    ]
  }
}
```

---

## sense 10105, level 6

#### Pack A
### Level 6 (sense 10105, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种科学方法广泛应用已在生产实践中。",
      "is_correct": false
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用着。",
      "is_correct": false
    },
    {
      "text": "这种科学方法已在生产实践中广泛应用出去。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。句中有“已”表示动作完成，而“着”表示动作持续，两者在时态上冲突，应删去“着”。 语序错误。介词结构“在生产实践中”作为状语，应放在谓语动词“广泛应用”之前，不能放在句末。 方向/结果补语误用。“应用”表示使用，不能与趋向补语“出去”搭配，语义不通，应删去“出去”。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "這種科學方法廣泛應用已在生產實踐中。",
        "is_correct": false
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用著。",
        "is_correct": false
      },
      {
        "text": "這種科學方法已在生產實踐中廣泛應用出去。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。句中有“已”表示動作完成，而“著”表示動作持續，兩者在時態上衝突，應刪去“著”。 語序錯誤。介詞結構“在生產實踐中”作為狀語，應放在謂語動詞“廣泛應用”之前，不能放在句末。 方向/結果補語誤用。“應用”表示使用，不能與趨向補語“出去”搭配，語義不通，應刪去“出去”。",
    "target_word": "廣泛應用"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种创新方案已在各大企业中广泛应用出来。",
      "is_correct": false
    },
    {
      "text": "这种创新方案广泛应用已在各大企业中。",
      "is_correct": false
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“已”表示动作完成，而“着”表示动作持续或状态保持，两者时态矛盾，且“应用”后直接加“着”不符合汉语习惯。 语序错误。介词短语“在各大企业中”作地点状语，应放在谓语动词“广泛应用”之前，不能放在其后。 结果补语误用。“出来”表示从无到有或从隐蔽到显露，不能作“应用”的结果补语，此处属于动补搭配不当。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "這種創新方案已在各大企業中廣泛應用出來。",
        "is_correct": false
      },
      {
        "text": "這種創新方案廣泛應用已在各大企業中。",
        "is_correct": false
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“已”表示動作完成，而“著”表示動作持續或狀態保持，兩者時態矛盾，且“應用”後直接加“著”不符合漢語習慣。 語序錯誤。介詞短語“在各大企業中”作地點狀語，應放在謂語動詞“廣泛應用”之前，不能放在其後。 結果補語誤用。“出來”表示從無到有或從隱蔽到顯露，不能作“應用”的結果補語，此處屬於動補搭配不當。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "积极探索",
    "深入研究",
    "大力推广",
    "束之高阁"
  ],
  "correct_answer": "束之高阁",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "广泛地使用或应用。",
      "explanation": "反义项：将事物搁置起来不予使用，与「广泛应用」构成反义"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "積極探索",
      "深入研究",
      "大力推廣",
      "束之高閣"
    ],
    "correct_answer": "束之高閣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "廣泛地使用或應用。",
        "explanation": "反義項：將事物擱置起來不予使用，與「廣泛應用」構成反義"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10105, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "同学们广泛应用把这种学习方法。",
      "is_correct": false
    },
    {
      "text": "同学们把这种学习方法广泛应用。",
      "is_correct": true
    },
    {
      "text": "同学们把这种学习方法广泛应用去。",
      "is_correct": false
    },
    {
      "text": "同学们把这种学习方法广泛应用了着。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：'了'表示完成，'着'表示持续，两者不能同时连用在动词后表示同一个体貌，属于语法结构错误。 方向补语误用：'应用'通常不与趋向补语'去'搭配，'去'表示动作离开说话人，此处语义不通。 语序错误：在'把'字句中，'把'及其宾语必须放在动词'应用'之前，不能放在动词之后。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "同學們廣泛應用把這種學習方法。",
        "is_correct": false
      },
      {
        "text": "同學們把這種學習方法廣泛應用。",
        "is_correct": true
      },
      {
        "text": "同學們把這種學習方法廣泛應用去。",
        "is_correct": false
      },
      {
        "text": "同學們把這種學習方法廣泛應用了著。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：'了'表示完成，'著'表示持續，兩者不能同時連用在動詞後表示同一個體貌，屬於語法結構錯誤。 方向補語誤用：'應用'通常不與趨向補語'去'搭配，'去'表示動作離開說話人，此處語義不通。 語序錯誤：在'把'字句中，'把'及其賓語必須放在動詞'應用'之前，不能放在動詞之後。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "重点开发",
    "全面普及",
    "局部使用",
    "大力推广"
  ],
  "correct_answer": "局部使用",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很大范围内普遍使用",
      "explanation": "反义项：使用范围局限于小部分，与“在很大范围内普遍使用”构成反义"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "重點開發",
      "全面普及",
      "區域性使用",
      "大力推廣"
    ],
    "correct_answer": "區域性使用",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很大範圍內普遍使用",
        "explanation": "反義項：使用範圍侷限於小部分，與“在很大範圍內普遍使用”構成反義"
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
      "text": "这种好方法已经被大家广泛应用了过。",
      "is_correct": false
    },
    {
      "text": "这种好方法已经被大家广泛应用。",
      "is_correct": true
    },
    {
      "text": "已经被大家广泛应用这种好方法。",
      "is_correct": false
    },
    {
      "text": "这种好方法已经被大家广泛应用起来。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：动态助词'了'和'过'不能同时连用在动词后表示完成和经历，应删去'了'，改为'应用过'，或删去'过'保留'应用了'。 语序错误：在'被'字句中，受事主语（这种好方法）必须放在'被'字之前，不能放在动词之后，导致句子结构混乱。 方向/结果补语误用：'起来'表示动作的开始或向上，而'广泛应用'强调动作的完成和普遍状态，此处使用'起来'与句意及'已经'所表达的完成体相冲突。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "這種好方法已經被大家廣泛應用了過。",
        "is_correct": false
      },
      {
        "text": "這種好方法已經被大家廣泛應用。",
        "is_correct": true
      },
      {
        "text": "已經被大家廣泛應用這種好方法。",
        "is_correct": false
      },
      {
        "text": "這種好方法已經被大家廣泛應用起來。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：動態助詞'了'和'過'不能同時連用在動詞後表示完成和經歷，應刪去'了'，改為'應用過'，或刪去'過'保留'應用了'。 語序錯誤：在'被'字句中，受事主語（這種好方法）必須放在'被'字之前，不能放在動詞之後，導致句子結構混亂。 方向/結果補語誤用：'起來'表示動作的開始或向上，而'廣泛應用'強調動作的完成和普遍狀態，此處使用'起來'與句意及'已經'所表達的完成體相沖突。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "深入研究",
    "大力推广",
    "束之高阁",
    "逐步完善"
  ],
  "correct_answer": "束之高阁",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很大范围内普遍使用",
      "explanation": "反义：将事物搁置不用，与「广泛应用」构成反义"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "深入研究",
      "大力推廣",
      "束之高閣",
      "逐步完善"
    ],
    "correct_answer": "束之高閣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很大範圍內普遍使用",
        "explanation": "反義：將事物擱置不用，與「廣泛應用」構成反義"
      }
    }
  }
}
```

---

## sense 10105, level 7

#### Pack A
### Level 7 (sense 10105, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种新型教学模式广泛应用了在各级学校。",
      "is_correct": false,
      "error_description": "体标位置错误。动态助词“了”不能放在动词和地点状语之间，应放在句末，或者使用“已”来表示动作的完成。"
    },
    {
      "text": "材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。",
      "is_correct": true
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "这种方法在同学中广泛应用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種新型教學模式廣泛應用了在各級學校。",
        "is_correct": false,
        "error_description": "體標位置錯誤。動態助詞“了”不能放在動詞和地點狀語之間，應放在句末，或者使用“已”來表示動作的完成。"
      },
      {
        "text": "材料科學的進步使得複合材料得以廣泛應用，不僅減輕了結構重量，還增強了疲勞耐久性；計算流體動力學（CFD）的發展則使工程師能夠在虛擬風洞中模擬極端工況下的氣動效能，從而在原型製造前完成多輪迭代。",
        "is_correct": true
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "這種方法在同學中廣泛應用。",
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
      "text": "这种模拟训练系统在专业学生中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案已在各大企业中广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种创新方案广泛应用已在各大企业中。",
      "is_correct": false,
      "error_description": "语序错误。副词“已”和介词短语“在各大企业中”应作为状语放在动词“广泛应用”之前，不能放在动词之后。"
    },
    {
      "text": "这种理论模型在相关学术研究中广泛应用。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種模擬訓練系統在專業學生中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案已在各大企業中廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種創新方案廣泛應用已在各大企業中。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“已”和介詞短語“在各大企業中”應作為狀語放在動詞“廣泛應用”之前，不能放在動詞之後。"
      },
      {
        "text": "這種理論模型在相關學術研究中廣泛應用。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10105, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "大家把广泛应用这种新方法。",
      "is_correct": false,
      "error_description": "“把”字句中，“把”的宾语必须是动作的受事（即“这种新方法”），动词“广泛应用”应放在“把”字结构之后。"
    },
    {
      "text": "这种新方法在班里得到了广泛应用。",
      "is_correct": true
    },
    {
      "text": "材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。",
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
        "text": "大家把廣泛應用這種新方法。",
        "is_correct": false,
        "error_description": "“把”字句中，“把”的賓語必須是動作的受事（即“這種新方法”），動詞“廣泛應用”應放在“把”字結構之後。"
      },
      {
        "text": "這種新方法在班裡得到了廣泛應用。",
        "is_correct": true
      },
      {
        "text": "材料科學的進步使得複合材料得以廣泛應用，不僅減輕了結構重量，還增強了疲勞耐久性；計算流體動力學（CFD）的發展則使工程師能夠在虛擬風洞中模擬極端工況下的氣動效能，從而在原型製造前完成多輪迭代。",
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
      "text": "大家把这种社交技巧广泛应用着。",
      "is_correct": false,
      "error_description": "“把”字句中的谓语动词通常不能直接带体标记“着”来表示动作的持续或状态的保留，应使用“了”表示动作的完成或结果。"
    },
    {
      "text": "这种好方法已经被大家广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种观点在朋友间被广泛应用着。",
      "is_correct": true
    },
    {
      "text": "他曾经把这种技巧广泛应用过。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "大家把這種社交技巧廣泛應用著。",
        "is_correct": false,
        "error_description": "“把”字句中的謂語動詞通常不能直接帶體標記“著”來表示動作的持續或狀態的保留，應使用“了”表示動作的完成或結果。"
      },
      {
        "text": "這種好方法已經被大家廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種觀點在朋友間被廣泛應用著。",
        "is_correct": true
      },
      {
        "text": "他曾經把這種技巧廣泛應用過。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10106, level 1

#### Pack A
### Level 1 (sense 10106, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "ipa": "[pi˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "鼻",
    "逼",
    "笔",
    "毕"
  ],
  "correct_answer": "毕",
  "explanation": "“毕”读作 bì（第四声），意思是完成、结束。",
  "distractor_explanations": {
    "逼": "“逼”读作 bī（第一声），意思是强迫或接近，声调不同导致意义完全不同。",
    "鼻": "“鼻”读作 bí（第二声），指鼻子或物体的突出部分，声调不同导致意义完全不同。",
    "笔": "“笔”读作 bǐ（第三声），指写字画图的工具，声调不同导致意义完全不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "ipa": "[pi˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "鼻",
      "逼",
      "筆",
      "畢"
    ],
    "correct_answer": "畢",
    "explanation": "“畢”讀作 bì（第四聲），意思是完成、結束。",
    "distractor_explanations": {
      "逼": "“逼”讀作 bī（第一聲），意思是強迫或接近，聲調不同導致意義完全不同。",
      "鼻": "“鼻”讀作 bí（第二聲），指鼻子或物體的突出部分，聲調不同導致意義完全不同。",
      "笔": "“筆”讀作 bǐ（第三聲），指寫字畫圖的工具，聲調不同導致意義完全不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 10106, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "毕",
  "pronunciation": "bì",
  "ipa": "[pi˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "笔",
    "鼻",
    "逼",
    "毕"
  ],
  "correct_answer": "毕",
  "explanation": "正确。“毕”读作 bì，意为完成、结束。",
  "distractor_explanations": {
    "逼": "错误。“逼”读作 bī，第一声，意为强迫、接近，声调不同。",
    "鼻": "错误。“鼻”读作 bí，第二声，指鼻子，声调不同。",
    "笔": "错误。“笔”读作 bǐ，第三声，指写字工具，声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "ipa": "[pi˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "筆",
      "鼻",
      "逼",
      "畢"
    ],
    "correct_answer": "畢",
    "explanation": "正確。“畢”讀作 bì，意為完成、結束。",
    "distractor_explanations": {
      "逼": "錯誤。“逼”讀作 bī，第一聲，意為強迫、接近，聲調不同。",
      "鼻": "錯誤。“鼻”讀作 bí，第二聲，指鼻子，聲調不同。",
      "笔": "錯誤。“筆”讀作 bǐ，第三聲，指寫字工具，聲調不同。"
    },
    "distractor_source": "llm"
  }
}
```

---
