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
    "灶",
    "早",
    "凿"
  ],
  "correct_answer": "早",
  "explanation": "正确。'早'读第三声（zǎo），表示时间靠前。",
  "distractor_explanations": {
    "糟": "错误。'糟'读第一声（zāo），指事情变坏或指酒糟，声调不同。",
    "凿": "错误。'凿'读第二声（záo），指挖掘或打孔，声调不同。",
    "灶": "错误。'灶'读第四声（zào），指生火做饭的设备，声调不同。"
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
      "灶",
      "早",
      "鑿"
    ],
    "correct_answer": "早",
    "explanation": "正確。'早'讀第三聲（zǎo），表示時間靠前。",
    "distractor_explanations": {
      "糟": "錯誤。'糟'讀第一聲（zāo），指事情變壞或指酒糟，聲調不同。",
      "凿": "錯誤。'鑿'讀第二聲（záo），指挖掘或打孔，聲調不同。",
      "灶": "錯誤。'灶'讀第四聲（zào），指生火做飯的裝置，聲調不同。"
    },
    "distractor_source": "llm"
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

#### Pack B
### Level 6 (sense 10103, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "你来找我早一点吧。",
      "is_correct": false
    },
    {
      "text": "你早一点去找我来吧。",
      "is_correct": false
    },
    {
      "text": "你早一点来找我吧。",
      "is_correct": true
    },
    {
      "text": "你早了一点来找我吧。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：'了'表示动作已完成或状态改变，与表示建议或祈使的语气词'吧'冲突，应去掉'了'。 语序错误：时间或程度状语'早一点'应放在谓语动词'来找我'之前，放在句末不符合汉语常规语序。 方向补语误用：'去'表示离开说话人，'来'表示朝向说话人，两者连用导致方向冲突，应删去'去'或'来'。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "你來找我早一點吧。",
        "is_correct": false
      },
      {
        "text": "你早一點去找我來吧。",
        "is_correct": false
      },
      {
        "text": "你早一點來找我吧。",
        "is_correct": true
      },
      {
        "text": "你早了一點來找我吧。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：'了'表示動作已完成或狀態改變，與表示建議或祈使的語氣詞'吧'衝突，應去掉'了'。 語序錯誤：時間或程度狀語'早一點'應放在謂語動詞'來找我'之前，放在句末不符合漢語常規語序。 方向補語誤用：'去'表示離開說話人，'來'表示朝向說話人，兩者連用導致方向衝突，應刪去'去'或'來'。",
    "target_word": "早"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我觉得早一点出发更好，毕竟在于早一日之计。",
      "is_correct": false
    },
    {
      "text": "我觉得早一点出发更好。",
      "is_correct": true
    },
    {
      "text": "我觉得早一点出发更好，毕竟一日之计在于早了。",
      "is_correct": false
    },
    {
      "text": "我觉得早一点出发更好，毕竟一日之计在于一个条早。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“早”作为表示时段的名词，不能使用量词“条”，应改为“个”或直接省略。 体标选用错误：表示客观规律或固有属性时不应加动态助词“了”，破坏了句子的状态表达。 语序错误：时间名词“早”错误地修饰了“一日”，破坏了“一日之计”的固定偏正结构。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "我覺得早一點出發更好，畢竟在於早一日之計。",
        "is_correct": false
      },
      {
        "text": "我覺得早一點出發更好。",
        "is_correct": true
      },
      {
        "text": "我覺得早一點出發更好，畢竟一日之計在於早了。",
        "is_correct": false
      },
      {
        "text": "我覺得早一點出發更好，畢竟一日之計在於一個條早。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“早”作為表示時段的名詞，不能使用量詞“條”，應改為“個”或直接省略。 體標選用錯誤：表示客觀規律或固有屬性時不應加動態助詞“了”，破壞了句子的狀態表達。 語序錯誤：時間名詞“早”錯誤地修飾了“一日”，破壞了“一日之計”的固定偏正結構。",
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
      "text": "他每天起得很早。",
      "is_correct": true
    },
    {
      "text": "我们喜欢从早玩到晚。",
      "is_correct": true
    },
    {
      "text": "现在睡觉太早了。",
      "is_correct": true
    },
    {
      "text": "我们喜欢玩从早到晚。",
      "is_correct": false,
      "error_description": "时间状语“从早到晚”应放在动词“玩”之前作状语，不能放在动词之后。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他每天起得很早。",
        "is_correct": true
      },
      {
        "text": "我們喜歡從早玩到晚。",
        "is_correct": true
      },
      {
        "text": "現在睡覺太早了。",
        "is_correct": true
      },
      {
        "text": "我們喜歡玩從早到晚。",
        "is_correct": false,
        "error_description": "時間狀語“從早到晚”應放在動詞“玩”之前作狀語，不能放在動詞之後。"
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
      "text": "他把起床时间定得很早。",
      "is_correct": true
    },
    {
      "text": "早比晚好。",
      "is_correct": true
    },
    {
      "text": "我早昨天起床了。",
      "is_correct": false,
      "error_description": "时间状语“昨天”应放在“很早”之前，正确的语序为“昨天很早”。"
    },
    {
      "text": "我觉得早一点出发更好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把起床時間定得很早。",
        "is_correct": true
      },
      {
        "text": "早比晚好。",
        "is_correct": true
      },
      {
        "text": "我早昨天起床了。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”應放在“很早”之前，正確的語序為“昨天很早”。"
      },
      {
        "text": "我覺得早一點出發更好。",
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
    "边",
    "便",
    "贬"
  ],
  "correct_answer": "便",
  "explanation": "正确。读音为 biàn，表示做某事不费力气或时间很短。",
  "distractor_explanations": {
    "边": "错误。读音为 biān（第一声），指边缘或旁边，声调不同导致意义改变。",
    "扁": "错误。读音为 biǎn（第三声），指物体平而薄，声调不同导致意义改变。",
    "贬": "错误。读音为 biǎn（第三声），指降低或批评，声调不同导致意义改变。"
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
      "邊",
      "便",
      "貶"
    ],
    "correct_answer": "便",
    "explanation": "正確。讀音為 biàn，表示做某事不費力氣或時間很短。",
    "distractor_explanations": {
      "边": "錯誤。讀音為 biān（第一聲），指邊緣或旁邊，聲調不同導致意義改變。",
      "扁": "錯誤。讀音為 biǎn（第三聲），指物體平而薄，聲調不同導致意義改變。",
      "贬": "錯誤。讀音為 biǎn（第三聲），指降低或批評，聲調不同導致意義改變。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10104, level 3

#### Pack A
### Level 3 (sense 10104, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他一学___会了这道题。",
  "original_sentence": "他一学便会了这道题。",
  "correct_answer": "便",
  "options": [
    "却",
    "刚",
    "才",
    "便"
  ],
  "explanation": "正确选项。在“一……便……”结构中表示动作紧接着发生，符合语境。",
  "distractor_tags": {},
  "word_definition": "副词，表示做某事不费力气或时间很短。",
  "target_word": "便",
  "hant": {
    "sentence_with_blank": "他一學___會了這道題。",
    "original_sentence": "他一學便會了這道題。",
    "correct_answer": "便",
    "options": [
      "卻",
      "剛",
      "才",
      "便"
    ],
    "explanation": "正確選項。在“一……便……”結構中表示動作緊接著發生，符合語境。",
    "distractor_tags": {},
    "word_definition": "副詞，表示做某事不費力氣或時間很短。",
    "target_word": "便"
  }
}
```

#### Pack B
### Level 3 (sense 10104, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他一跑___到了终点。",
  "original_sentence": "他一跑便到了终点。",
  "correct_answer": "便",
  "options": [
    "正",
    "才",
    "又",
    "便"
  ],
  "explanation": "正确。“便”在这里表示动作完成得快，与“一跑”搭配，表示不费力气或时间很短。",
  "distractor_tags": {},
  "word_definition": "副词，表示做某事不费力气或时间很短。",
  "target_word": "便",
  "hant": {
    "sentence_with_blank": "他一跑___到了終點。",
    "original_sentence": "他一跑便到了終點。",
    "correct_answer": "便",
    "options": [
      "正",
      "才",
      "又",
      "便"
    ],
    "explanation": "正確。“便”在這裡表示動作完成得快，與“一跑”搭配，表示不費力氣或時間很短。",
    "distractor_tags": {},
    "word_definition": "副詞，表示做某事不費力氣或時間很短。",
    "target_word": "便"
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
      "text": "她刚坐下便睡起来了。",
      "is_correct": false
    },
    {
      "text": "她刚坐下便睡着过。",
      "is_correct": false
    },
    {
      "text": "她刚便坐下睡着了。",
      "is_correct": false
    },
    {
      "text": "她刚坐下便睡着了。",
      "is_correct": true
    }
  ],
  "explanation": "体标选用错误。“刚”表示最近发生的动作，应与动态助词“了”搭配，不能使用表示过去经历的“过”。 语序错误。副词“便”应连接前后两个动作，放在第一个动作“坐下”之后、第二个动作“睡着”之前。 方向/结果补语误用。“睡”后不能接“起来”表示动作完成或状态改变，应使用“着”或“了”。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "她剛坐下便睡起來了。",
        "is_correct": false
      },
      {
        "text": "她剛坐下便睡著過。",
        "is_correct": false
      },
      {
        "text": "她剛便坐下睡著了。",
        "is_correct": false
      },
      {
        "text": "她剛坐下便睡著了。",
        "is_correct": true
      }
    ],
    "explanation": "體標選用錯誤。“剛”表示最近發生的動作，應與動態助詞“了”搭配，不能使用表示過去經歷的“過”。 語序錯誤。副詞“便”應連線前後兩個動作，放在第一個動作“坐下”之後、第二個動作“睡著”之前。 方向/結果補語誤用。“睡”後不能接“起來”表示動作完成或狀態改變，應使用“著”或“了”。",
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
    "已",
    "才",
    "即",
    "就"
  ],
  "correct_answer": "才",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示做某事不费力气或时间很短。",
      "explanation": "反义：'才'表示事情发生得晚或耗时久，与'便'表示的轻易、快速构成反义"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "已",
      "才",
      "即",
      "就"
    ],
    "correct_answer": "才",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示做某事不費力氣或時間很短。",
        "explanation": "反義：'才'表示事情發生得晚或耗時久，與'便'表示的輕易、快速構成反義"
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
      "text": "这歌我听一遍便会唱起来。",
      "is_correct": false
    },
    {
      "text": "这歌我听一遍便会唱了。",
      "is_correct": true
    },
    {
      "text": "这歌我听一遍便会唱着了。",
      "is_correct": false
    },
    {
      "text": "这歌我一遍听便会唱了。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“着”表示动作持续，而“会唱”表示掌握技能，两者语义冲突；“便”强调短时间内掌握，应使用“了”表示完成。 语序错误：动量补语“一遍”应放在动词“听”之后作补语（即“听一遍”），不能放在动词之前。 趋向补语误用：“起来”表示动作开始，而“会唱”表示已经掌握，此处应使用“了”表示状态实现，使用“起来”导致语义不通。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "這歌我聽一遍便會唱起來。",
        "is_correct": false
      },
      {
        "text": "這歌我聽一遍便會唱了。",
        "is_correct": true
      },
      {
        "text": "這歌我聽一遍便會唱著了。",
        "is_correct": false
      },
      {
        "text": "這歌我一遍聽便會唱了。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“著”表示動作持續，而“會唱”表示掌握技能，兩者語義衝突；“便”強調短時間內掌握，應使用“了”表示完成。 語序錯誤：動量補語“一遍”應放在動詞“聽”之後作補語（即“聽一遍”），不能放在動詞之前。 趨向補語誤用：“起來”表示動作開始，而“會唱”表示已經掌握，此處應使用“了”表示狀態實現，使用“起來”導致語義不通。",
    "target_word": "便"
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
      "text": "这道题他一看便会做了。",
      "is_correct": true
    },
    {
      "text": "我把作业一写便去玩了。",
      "is_correct": true
    },
    {
      "text": "一跑他便到了终点。",
      "is_correct": false,
      "error_description": "在“一……便……”句式中，主语应放在“一”之前，不能放在“一”和“便”之间。"
    },
    {
      "text": "他一跑便到了终点。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這道題他一看便會做了。",
        "is_correct": true
      },
      {
        "text": "我把作業一寫便去玩了。",
        "is_correct": true
      },
      {
        "text": "一跑他便到了終點。",
        "is_correct": false,
        "error_description": "在“一……便……”句式中，主語應放在“一”之前，不能放在“一”和“便”之間。"
      },
      {
        "text": "他一跑便到了終點。",
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
      "text": "我刚出门便碰到了他。",
      "is_correct": true
    },
    {
      "text": "这歌我听一遍便会唱了。",
      "is_correct": true
    },
    {
      "text": "我刚出门碰到了他便。",
      "is_correct": false,
      "error_description": "“便”是副词，应放在动词“碰到”之前，不能放在句末。"
    },
    {
      "text": "只要多练，一学便会了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我剛出門便碰到了他。",
        "is_correct": true
      },
      {
        "text": "這歌我聽一遍便會唱了。",
        "is_correct": true
      },
      {
        "text": "我剛出門碰到了他便。",
        "is_correct": false,
        "error_description": "“便”是副詞，應放在動詞“碰到”之前，不能放在句末。"
      },
      {
        "text": "只要多練，一學便會了。",
        "is_correct": true
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
      "text": "广泛应用过新技术很重要。",
      "is_correct": false
    },
    {
      "text": "广泛应用新技术很重要。",
      "is_correct": true
    },
    {
      "text": "很重要广泛应用新技术。",
      "is_correct": false
    },
    {
      "text": "广泛应用着新技术很重要。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'过'表示经历，放在'应用'后使句子变成陈述过去经历，与句末'很重要'的评价语气冲突，应去掉'过'或改为'广泛应用新技术很重要'。 体标选用错误。'着'表示动作正在进行或状态持续，与句末'很重要'这种表示客观评价或一般性真理的语境不符，应去掉'着'。 语序错误。汉语中形容词谓语'很重要'通常放在句末作谓语，或者用'广泛应用新技术是很重要的'，将'很重要'放在句首破坏了正常的'主语—谓语'语序。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "廣泛應用過新技術很重要。",
        "is_correct": false
      },
      {
        "text": "廣泛應用新技術很重要。",
        "is_correct": true
      },
      {
        "text": "很重要廣泛應用新技術。",
        "is_correct": false
      },
      {
        "text": "廣泛應用著新技術很重要。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'過'表示經歷，放在'應用'後使句子變成陳述過去經歷，與句末'很重要'的評價語氣衝突，應去掉'過'或改為'廣泛應用新技術很重要'。 體標選用錯誤。'著'表示動作正在進行或狀態持續，與句末'很重要'這種表示客觀評價或一般性真理的語境不符，應去掉'著'。 語序錯誤。漢語中形容詞謂語'很重要'通常放在句末作謂語，或者用'廣泛應用新技術是很重要的'，將'很重要'放在句首破壞了正常的'主語—謂語'語序。",
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
    "局部使用",
    "严格管理",
    "深入研究",
    "大力推广"
  ],
  "correct_answer": "局部使用",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "广泛地使用或应用。",
      "explanation": "表示只在部分范围或特定方面使用，与在很大范围使用的广泛应用构成反义关系。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "區域性使用",
      "嚴格管理",
      "深入研究",
      "大力推廣"
    ],
    "correct_answer": "區域性使用",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "廣泛地使用或應用。",
        "explanation": "表示只在部分範圍或特定方面使用，與在很大範圍使用的廣泛應用構成反義關係。"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "借鉴",
    "采用",
    "推行",
    "弃用"
  ],
  "correct_answer": "弃用",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "广泛地使用或应用。",
      "explanation": "反义项：「弃用」指放弃、不再使用，与「广泛应用」（大范围使用）构成反义关系。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "借鑑",
      "採用",
      "推行",
      "棄用"
    ],
    "correct_answer": "棄用",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "廣泛地使用或應用。",
        "explanation": "反義項：「棄用」指放棄、不再使用，與「廣泛應用」（大範圍使用）構成反義關係。"
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
      "text": "大家把广泛应用这种方法。",
      "is_correct": false,
      "error_description": "在“把”字句中，“把”的宾语应紧跟在“把”字之后，即“把这种方法”，谓语动词“广泛应用”应放在宾语之后。"
    },
    {
      "text": "材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。",
      "is_correct": true
    },
    {
      "text": "我们在生活中广泛应用它。",
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
        "text": "大家把廣泛應用這種方法。",
        "is_correct": false,
        "error_description": "在“把”字句中，“把”的賓語應緊跟在“把”字之後，即“把這種方法”，謂語動詞“廣泛應用”應放在賓語之後。"
      },
      {
        "text": "材料科學的進步使得複合材料得以廣泛應用，不僅減輕了結構重量，還增強了疲勞耐久性；計算流體動力學（CFD）的發展則使工程師能夠在虛擬風洞中模擬極端工況下的氣動效能，從而在原型製造前完成多輪迭代。",
        "is_correct": true
      },
      {
        "text": "我們在生活中廣泛應用它。",
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
      "text": "大家正广泛应用着新技术。",
      "is_correct": true
    },
    {
      "text": "他广泛应用所学知识。",
      "is_correct": true
    },
    {
      "text": "大家把广泛应用这种方法。",
      "is_correct": false,
      "error_description": "在“把”字句中，受事宾语（这种方法）必须紧跟在“把”字之后，不能放在动词（广泛应用）之后。"
    },
    {
      "text": "学校广泛应用这种教学法。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "大家正廣泛應用著新技術。",
        "is_correct": true
      },
      {
        "text": "他廣泛應用所學知識。",
        "is_correct": true
      },
      {
        "text": "大家把廣泛應用這種方法。",
        "is_correct": false,
        "error_description": "在“把”字句中，受事賓語（這種方法）必須緊跟在“把”字之後，不能放在動詞（廣泛應用）之後。"
      },
      {
        "text": "學校廣泛應用這種教學法。",
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
    "逼",
    "笔",
    "毕",
    "鼻"
  ],
  "correct_answer": "毕",
  "explanation": "正确。读音为第四声（bì），意为完成或结束。",
  "distractor_explanations": {
    "逼": "声调为第一声（bī），意为强迫或接近，与第四声的“毕”意义不同。",
    "鼻": "声调为第二声（bí），指鼻子或物体突出带孔的部分，与第四声的“毕”意义不同。",
    "笔": "声调为第三声（bǐ），指写字画图的工具，与第四声的“毕”意义不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "畢",
    "pronunciation": "bì",
    "ipa": "[pi˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "逼",
      "筆",
      "畢",
      "鼻"
    ],
    "correct_answer": "畢",
    "explanation": "正確。讀音為第四聲（bì），意為完成或結束。",
    "distractor_explanations": {
      "逼": "聲調為第一聲（bī），意為強迫或接近，與第四聲的“畢”意義不同。",
      "鼻": "聲調為第二聲（bí），指鼻子或物體突出帶孔的部分，與第四聲的“畢”意義不同。",
      "笔": "聲調為第三聲（bǐ），指寫字畫圖的工具，與第四聲的“畢”意義不同。"
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
