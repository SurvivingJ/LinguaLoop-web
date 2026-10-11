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
  "ipa": "[tsɑʊ̯˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "凿",
    "糟",
    "灶",
    "早"
  ],
  "correct_answer": "早",
  "explanation": "“早”读作 zǎo（第三声），表示时间靠前。",
  "distractor_explanations": {
    "糟": "“糟”读作 zāo（第一声），声调不同，意思为坏或糟糕。",
    "凿": "“凿”读作 záo（第二声），声调不同，指挖掘或打孔的工具/动作。",
    "灶": "“灶”读作 zào（第四声），声调不同，指生火做饭的设备。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsɑʊ̯˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "鑿",
      "糟",
      "灶",
      "早"
    ],
    "correct_answer": "早",
    "explanation": "“早”讀作 zǎo（第三聲），表示時間靠前。",
    "distractor_explanations": {
      "糟": "“糟”讀作 zāo（第一聲），聲調不同，意思為壞或糟糕。",
      "凿": "“鑿”讀作 záo（第二聲），聲調不同，指挖掘或打孔的工具/動作。",
      "灶": "“灶”讀作 zào（第四聲），聲調不同，指生火做飯的裝置。"
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
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "别着急，离上课时间还___着呢。",
  "original_sentence": "别着急，离上课时间还早着呢。",
  "correct_answer": "早",
  "options": [
    "近",
    "早",
    "短",
    "晚"
  ],
  "explanation": "正确。'早'表示时间靠前，符合'别着急'的语境。",
  "distractor_tags": {},
  "word_definition": "指太阳刚升起或时间靠前的时段。",
  "target_word": "早",
  "hant": {
    "sentence_with_blank": "彆著急，離上課時間還___著呢。",
    "original_sentence": "彆著急，離上課時間還早著呢。",
    "correct_answer": "早",
    "options": [
      "近",
      "早",
      "短",
      "晚"
    ],
    "explanation": "正確。'早'表示時間靠前，符合'彆著急'的語境。",
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
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "早",
  "relation": "antonym",
  "options": [
    "久",
    "快",
    "慢",
    "晚"
  ],
  "correct_answer": "晚",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指太阳刚升起或时间靠前的时段。",
      "explanation": "反义：「晚」指太阳落山后或时间靠后的时段，与「早」的时间靠前义构成反义"
    }
  },
  "hant": {
    "word": "早",
    "relation": "antonym",
    "options": [
      "久",
      "快",
      "慢",
      "晚"
    ],
    "correct_answer": "晚",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指太陽剛升起或時間靠前的時段。",
        "explanation": "反義：「晚」指太陽落山後或時間靠後的時段，與「早」的時間靠前義構成反義"
      }
    }
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他每天早晨都起得很早，学习非常努力。",
      "is_correct": true
    },
    {
      "text": "别着急，离上课时间还早着呢。",
      "is_correct": true
    },
    {
      "text": "他早每天起床去公园跑步。",
      "is_correct": false,
      "error_description": "语序错误。表示时间的状语“每天”应放在表示时间的形容词“很早”之前，即“每天很早”。"
    },
    {
      "text": "我们约的时间早，可以慢慢走。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他每天早晨都起得很早，學習非常努力。",
        "is_correct": true
      },
      {
        "text": "彆著急，離上課時間還早著呢。",
        "is_correct": true
      },
      {
        "text": "他早每天起床去公園跑步。",
        "is_correct": false,
        "error_description": "語序錯誤。表示時間的狀語“每天”應放在表示時間的形容詞“很早”之前，即“每天很早”。"
      },
      {
        "text": "我們約的時間早，可以慢慢走。",
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
  "ipa": "[piɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "扁",
    "便",
    "编",
    "边"
  ],
  "correct_answer": "便",
  "explanation": "正确。发音为第四声（biàn），在此处作副词，表示动作紧接着发生或很容易完成。",
  "distractor_explanations": {
    "边": "声调为第一声（biān），指边缘或旁边，与目标词第四声（biàn）不同，意义完全改变。",
    "扁": "声调为第三声（biǎn），指物体平而薄，与目标词第四声（biàn）不同，意义完全改变。",
    "编": "声调为第一声（biān），指把条状物交叉组织起来，与目标词第四声（biàn）不同，意义完全改变。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[piɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "扁",
      "便",
      "編",
      "邊"
    ],
    "correct_answer": "便",
    "explanation": "正確。發音為第四聲（biàn），在此處作副詞，表示動作緊接著發生或很容易完成。",
    "distractor_explanations": {
      "边": "聲調為第一聲（biān），指邊緣或旁邊，與目標詞第四聲（biàn）不同，意義完全改變。",
      "扁": "聲調為第三聲（biǎn），指物體平而薄，與目標詞第四聲（biàn）不同，意義完全改變。",
      "编": "聲調為第一聲（biān），指把條狀物交叉組織起來，與目標詞第四聲（biàn）不同，意義完全改變。"
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
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "马上",
    "赶紧",
    "立刻",
    "迟迟"
  ],
  "correct_answer": "迟迟",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示做某事不费力气或时间很短。",
      "explanation": "反义：'迟迟'表示拖延、耗时久，与'便'表时间极短构成反义"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "馬上",
      "趕緊",
      "立刻",
      "遲遲"
    ],
    "correct_answer": "遲遲",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示做某事不費力氣或時間很短。",
        "explanation": "反義：'遲遲'表示拖延、耗時久，與'便'表時間極短構成反義"
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
      "text": "我随叫便到，因为我们是好朋友。",
      "is_correct": true
    },
    {
      "text": "他把衣服便一洗晾在了阳台上。",
      "is_correct": false,
      "error_description": "语序错误。在“一……便……”结构中，“便”作为副词应放在第二个动作（动词）之前，不能放在“一+动词”之前。"
    },
    {
      "text": "他把课文一读便背过了。",
      "is_correct": true
    },
    {
      "text": "他一学便会了这道数学题。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我隨叫便到，因為我們是好朋友。",
        "is_correct": true
      },
      {
        "text": "他把衣服便一洗晾在了陽臺上。",
        "is_correct": false,
        "error_description": "語序錯誤。在“一……便……”結構中，“便”作為副詞應放在第二個動作（動詞）之前，不能放在“一+動詞”之前。"
      },
      {
        "text": "他把課文一讀便背過了。",
        "is_correct": true
      },
      {
        "text": "他一學便會了這道數學題。",
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
      "text": "老师一讲我便听懂了这个知识点。",
      "is_correct": true
    },
    {
      "text": "他一洗便把晾在了阳台上。",
      "is_correct": false,
      "error_description": "“把”字句中“把”后面必须有明确的宾语，原句缺失了宾语“衣服”，应将其放在“把”之后。"
    },
    {
      "text": "他把衣服一洗便晾在了阳台上。",
      "is_correct": true
    },
    {
      "text": "这道菜很简单，一炒便熟了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師一講我便聽懂了這個知識點。",
        "is_correct": true
      },
      {
        "text": "他一洗便把晾在了陽臺上。",
        "is_correct": false,
        "error_description": "“把”字句中“把”後面必須有明確的賓語，原句缺失了賓語“衣服”，應將其放在“把”之後。"
      },
      {
        "text": "他把衣服一洗便晾在了陽臺上。",
        "is_correct": true
      },
      {
        "text": "這道菜很簡單，一炒便熟了。",
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
    "毕",
    "鼻",
    "逼"
  ],
  "correct_answer": "毕",
  "explanation": "“毕”读第四声（bì），意为完成、结束，符合听到的发音和词义。",
  "distractor_explanations": {
    "逼": "“逼”读第一声（bī），意为强迫或逼近，与第四声的“毕”声调不同，意义也完全不同。",
    "鼻": "“鼻”读第二声（bí），指鼻子或物体的突出部分，声调与“毕”不同，属于名词而非动作。",
    "笔": "“笔”读第三声（bǐ），指写字画图的工具，声调与“毕”不同，词义和词性均不符。"
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
      "畢",
      "鼻",
      "逼"
    ],
    "correct_answer": "畢",
    "explanation": "“畢”讀第四聲（bì），意為完成、結束，符合聽到的發音和詞義。",
    "distractor_explanations": {
      "逼": "“逼”讀第一聲（bī），意為強迫或逼近，與第四聲的“畢”聲調不同，意義也完全不同。",
      "鼻": "“鼻”讀第二聲（bí），指鼻子或物體的突出部分，聲調與“畢”不同，屬於名詞而非動作。",
      "笔": "“筆”讀第三聲（bǐ），指寫字畫圖的工具，聲調與“畢”不同，詞義和詞性均不符。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10106, level 3

#### Pack A
### Level 3 (sense 10106, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "考试终于结束，这场大战总算已___。",
  "original_sentence": "考试终于结束，这场大战总算已毕。",
  "correct_answer": "毕",
  "options": [
    "停",
    "断",
    "散",
    "毕"
  ],
  "explanation": "正确选项。“毕”意为完成、结束，与“已”搭配表示事情已经完结，符合语境。",
  "distractor_tags": {},
  "word_definition": "完成；结束。",
  "target_word": "毕",
  "hant": {
    "sentence_with_blank": "考試終於結束，這場大戰總算已___。",
    "original_sentence": "考試終於結束，這場大戰總算已畢。",
    "correct_answer": "畢",
    "options": [
      "停",
      "斷",
      "散",
      "畢"
    ],
    "explanation": "正確選項。“畢”意為完成、結束，與“已”搭配表示事情已經完結，符合語境。",
    "distractor_tags": {},
    "word_definition": "完成；結束。",
    "target_word": "畢"
  }
}
```

#### Pack B
### Level 3 (sense 10106, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "经过四年的刻苦学习，他终于在今年夏天顺利从这所知名大学___业，即将步入社会开启新的人生篇章。",
  "original_sentence": "经过四年的刻苦学习，他终于在今年夏天顺利从这所知名大学毕业，即将步入社会开启新的人生篇章。",
  "correct_answer": "毕",
  "options": [
    "毕",
    "成",
    "了",
    "结"
  ],
  "explanation": "“毕”意为完成，“毕业”是完成学业的固定搭配，完美契合句中完成大学四年学习的语境。",
  "distractor_tags": {},
  "word_definition": "完成；结束。",
  "target_word": "毕",
  "hant": {
    "sentence_with_blank": "經過四年的刻苦學習，他終於在今年夏天順利從這所知名大學___業，即將步入社會開啟新的人生篇章。",
    "original_sentence": "經過四年的刻苦學習，他終於在今年夏天順利從這所知名大學畢業，即將步入社會開啟新的人生篇章。",
    "correct_answer": "畢",
    "options": [
      "畢",
      "成",
      "了",
      "結"
    ],
    "explanation": "“畢”意為完成，“畢業”是完成學業的固定搭配，完美契合句中完成大學四年學習的語境。",
    "distractor_tags": {},
    "word_definition": "完成；結束。",
    "target_word": "畢"
  }
}
```

---

## sense 10106, level 6

#### Pack A
### Level 6 (sense 10106, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们毕听报告，开始分组讨论。",
      "is_correct": false
    },
    {
      "text": "我们听毕报告，开始分组讨论。",
      "is_correct": true
    },
    {
      "text": "我们听毕起报告，开始分组讨论。",
      "is_correct": false
    },
    {
      "text": "我们听毕了报告，开始分组讨论。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：“毕”本身已包含完成的语义，其后不应再加动态助词“了”，造成语义重复和语法冗余。 语序错误：“毕”作为表示完成的动词，应放在主要动作“听”之后作结果补语或连动后项，不能置于动词前。 方向补语误用：“毕”已表示动作完成，后面不能再接趋向补语“起”，两者在语义和语法上均不兼容。",
  "target_word": "毕",
  "hant": {
    "sentences": [
      {
        "text": "我們畢聽報告，開始分組討論。",
        "is_correct": false
      },
      {
        "text": "我們聽畢報告，開始分組討論。",
        "is_correct": true
      },
      {
        "text": "我們聽畢起報告，開始分組討論。",
        "is_correct": false
      },
      {
        "text": "我們聽畢了報告，開始分組討論。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：“畢”本身已包含完成的語義，其後不應再加動態助詞“了”，造成語義重複和語法冗餘。 語序錯誤：“畢”作為表示完成的動詞，應放在主要動作“聽”之後作結果補語或連動後項，不能置於動詞前。 方向補語誤用：“畢”已表示動作完成，後面不能再接趨向補語“起”，兩者在語義和語法上均不相容。",
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
