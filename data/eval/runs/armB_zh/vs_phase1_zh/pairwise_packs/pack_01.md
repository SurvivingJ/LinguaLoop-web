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
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "早",
  "pronunciation": "zǎo",
  "ipa": "[tsɑu˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "早",
    "造",
    "枣",
    "糟"
  ],
  "correct_answer": "早",
  "explanation": "正确。读音为 zǎo（第三声），意为时间靠前。",
  "distractor_explanations": {
    "造": "错误。读音为 zào（第四声），意为制造或建造，声调不同。",
    "枣": "错误。读音为 zǎo（第三声），但指一种水果（红枣），意义完全不同。注意：虽然声调相同，但在听音辨字初级练习中，通常考察形近或音近混淆。此处修正为更符合L1规则的声调混淆项。",
    "糟": "错误。读音为 zāo（第一声），意为糟糕或酒糟，声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "早",
    "pronunciation": "zǎo",
    "ipa": "[tsɑu˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "早",
      "造",
      "棗",
      "糟"
    ],
    "correct_answer": "早",
    "explanation": "正確。讀音為 zǎo（第三聲），意為時間靠前。",
    "distractor_explanations": {
      "造": "錯誤。讀音為 zào（第四聲），意為製造或建造，聲調不同。",
      "枣": "錯誤。讀音為 zǎo（第三聲），但指一種水果（紅棗），意義完全不同。注意：雖然聲調相同，但在聽音辨字初級練習中，通常考察形近或音近混淆。此處修正為更符合L1規則的聲調混淆項。",
      "糟": "錯誤。讀音為 zāo（第一聲），意為糟糕或酒糟，聲調不同。"
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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这花开得早早。",
      "is_correct": false
    },
    {
      "text": "这花早开过真。",
      "is_correct": false
    },
    {
      "text": "这花开得真早。",
      "is_correct": true
    },
    {
      "text": "这花被早开了。",
      "is_correct": false
    }
  ],
  "explanation": "体貌/形态错误：形容词'早'重叠形式通常为'早早地'作状语，或单用。在补语位置'开得...'后直接加重叠式'早早'不符合汉语习惯，应说'开得真早'或'早早地开了'。 语序错误：程度副词'真'应该放在动词/形容词之前或作为补语标记的一部分，不能放在句末。正确语序应为'这花真开得早'或'这花开得真早'。 配价/语态错误：'开'在此处是不及物动词（花朵开放），不能使用被动句'被...'。此外，'早'作为时间状语，位置应在'被'字前或动词前，但核心错误在于不及物动词误用被动语态。",
  "target_word": "早",
  "hant": {
    "sentences": [
      {
        "text": "這花開得早早。",
        "is_correct": false
      },
      {
        "text": "這花早開過真。",
        "is_correct": false
      },
      {
        "text": "這花開得真早。",
        "is_correct": true
      },
      {
        "text": "這花被早開了。",
        "is_correct": false
      }
    ],
    "explanation": "體貌/形態錯誤：形容詞'早'重疊形式通常為'早早地'作狀語，或單用。在補語位置'開得...'後直接加重疊式'早早'不符合漢語習慣，應說'開得真早'或'早早地開了'。 語序錯誤：程度副詞'真'應該放在動詞/形容詞之前或作為補語標記的一部分，不能放在句末。正確語序應為'這花真開得早'或'這花開得真早'。 配價/語態錯誤：'開'在此處是不及物動詞（花朵開放），不能使用被動句'被...'。此外，'早'作為時間狀語，位置應在'被'字前或動詞前，但核心錯誤在於不及物動詞誤用被動語態。",
    "target_word": "早"
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
  "ipa": "[pjɛn˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "便",
    "辩",
    "遍",
    "变"
  ],
  "correct_answer": "便",
  "explanation": "正确。读音为 biàn，第四声。",
  "distractor_explanations": {
    "变": "错误。读音为 biàn，但意思是“改变”，与目标词意义不同。",
    "辩": "错误。读音为 biàn，但意思是“辩论”，与目标词意义不同。",
    "遍": "错误。读音为 biàn，但意思是“次/回”或“全面”，与目标词意义不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "便",
    "pronunciation": "biàn",
    "ipa": "[pjɛn˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "便",
      "辯",
      "遍",
      "變"
    ],
    "correct_answer": "便",
    "explanation": "正確。讀音為 biàn，第四聲。",
    "distractor_explanations": {
      "变": "錯誤。讀音為 biàn，但意思是“改變”，與目標詞意義不同。",
      "辩": "錯誤。讀音為 biàn，但意思是“辯論”，與目標詞意義不同。",
      "遍": "錯誤。讀音為 biàn，但意思是“次/回”或“全面”，與目標詞意義不同。"
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
  "sentence_with_blank": "这道题很简单，我一会儿___做完了。",
  "original_sentence": "这道题很简单，我一会儿便做完了。",
  "correct_answer": "便",
  "options": [
    "便",
    "却",
    "竟",
    "才"
  ],
  "explanation": "正确。“便”在此处作副词，表示动作发生得快或容易，符合“一会儿就做完了”的语境。",
  "distractor_tags": {},
  "word_definition": "表示做某事不费力气或时间很短",
  "target_word": "便",
  "hant": {
    "sentence_with_blank": "這道題很簡單，我一會兒___做完了。",
    "original_sentence": "這道題很簡單，我一會兒便做完了。",
    "correct_answer": "便",
    "options": [
      "便",
      "卻",
      "竟",
      "才"
    ],
    "explanation": "正確。“便”在此處作副詞，表示動作發生得快或容易，符合“一會兒就做完了”的語境。",
    "distractor_tags": {},
    "word_definition": "表示做某事不費力氣或時間很短",
    "target_word": "便"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这软件操作简___，新手很快便能上手。",
  "original_sentence": "这软件操作简便，新手很快便能上手。",
  "correct_answer": "便",
  "options": [
    "才",
    "却",
    "已",
    "便"
  ],
  "explanation": "正确。表示动作发生得快或容易，符合语境中“很快能上手”的意思。",
  "distractor_tags": {},
  "word_definition": "表示做某事不费力气或时间很短",
  "target_word": "便",
  "hant": {
    "sentence_with_blank": "這軟體操作簡___，新手很快便能上手。",
    "original_sentence": "這軟體操作簡便，新手很快便能上手。",
    "correct_answer": "便",
    "options": [
      "才",
      "卻",
      "已",
      "便"
    ],
    "explanation": "正確。表示動作發生得快或容易，符合語境中“很快能上手”的意思。",
    "distractor_tags": {},
    "word_definition": "表示做某事不費力氣或時間很短",
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
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "便",
  "relation": "antonym",
  "options": [
    "即",
    "就",
    "才",
    "已"
  ],
  "correct_answer": "才",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短",
      "explanation": "反义关系：表示动作发生得晚、慢或费力，与“便”表示的轻易、快速相对"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "即",
      "就",
      "才",
      "已"
    ],
    "correct_answer": "才",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短",
        "explanation": "反義關係：表示動作發生得晚、慢或費力，與“便”表示的輕易、快速相對"
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
      "text": "这个问题不难，想一想便出知道答案。",
      "is_correct": false
    },
    {
      "text": "这个问题不难，想一想便知道答案了过。",
      "is_correct": false
    },
    {
      "text": "这个问题不难，便想一想知道答案。",
      "is_correct": false
    },
    {
      "text": "这个问题不难，想一想便知道答案。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：动态助词'了'和'过'不能同时堆叠在句尾，且'过'表示经历，与此处陈述事实的语境不符。 语序错误：副词'便'应紧贴谓语动词'知道'之前，放在状语'想一想'之前会导致逻辑断裂，读起来不自然。 结果补语误用：'出'作为结果补语通常紧跟动词（如'看出'），不能插入在副词'便'和动词'知道'之间，结构混乱。",
  "target_word": "便",
  "hant": {
    "sentences": [
      {
        "text": "這個問題不難，想一想便出知道答案。",
        "is_correct": false
      },
      {
        "text": "這個問題不難，想一想便知道答案了過。",
        "is_correct": false
      },
      {
        "text": "這個問題不難，便想一想知道答案。",
        "is_correct": false
      },
      {
        "text": "這個問題不難，想一想便知道答案。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'和'過'不能同時堆疊在句尾，且'過'表示經歷，與此處陳述事實的語境不符。 語序錯誤：副詞'便'應緊貼謂語動詞'知道'之前，放在狀語'想一想'之前會導致邏輯斷裂，讀起來不自然。 結果補語誤用：'出'作為結果補語通常緊跟動詞（如'看出'），不能插入在副詞'便'和動詞'知道'之間，結構混亂。",
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
    "已",
    "才",
    "就",
    "即"
  ],
  "correct_answer": "才",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示做某事不费力气或时间很短",
      "explanation": "反义：表示动作发生得晚、慢或困难，与“便”表示的轻易、快速相对。"
    }
  },
  "hant": {
    "word": "便",
    "relation": "antonym",
    "options": [
      "已",
      "才",
      "就",
      "即"
    ],
    "correct_answer": "才",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示做某事不費力氣或時間很短",
        "explanation": "反義：表示動作發生得晚、慢或困難，與“便”表示的輕易、快速相對。"
      }
    }
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
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "老师广泛应用这种方法过在教学。",
      "is_correct": false
    },
    {
      "text": "老师把这种方法广泛应用在教学中。",
      "is_correct": true
    },
    {
      "text": "老师正在广泛应用着这种方法在教学。",
      "is_correct": false
    },
    {
      "text": "老师把这种方法广泛应用了在教学。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：介词短语'在教学中'应作为状语修饰动词，或紧跟动词后作补语，但不能将'在'置于宾语'教学'之前并断开动词。正确应为'广泛应用在教学中'或'在教学里广泛应用'。 体标误用：'广泛应用'通常表示一种普遍的状态或已完成的事实，不宜与进行体标记'正在...着'连用，且句式杂糅。 语序/体标错误：动态助词'过'应紧贴动词之后，即'应用过'，且'在教学'的位置不当，导致句子结构混乱。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "老師廣泛應用這種方法過在教學。",
        "is_correct": false
      },
      {
        "text": "老師把這種方法廣泛應用在教學中。",
        "is_correct": true
      },
      {
        "text": "老師正在廣泛應用著這種方法在教學。",
        "is_correct": false
      },
      {
        "text": "老師把這種方法廣泛應用了在教學。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：介詞短語'在教學中'應作為狀語修飾動詞，或緊跟動詞後作補語，但不能將'在'置於賓語'教學'之前並斷開動詞。正確應為'廣泛應用在教學中'或'在教學裡廣泛應用'。 體標誤用：'廣泛應用'通常表示一種普遍的狀態或已完成的事實，不宜與進行體標記'正在...著'連用，且句式雜糅。 語序/體標錯誤：動態助詞'過'應緊貼動詞之後，即'應用過'，且'在教學'的位置不當，導致句子結構混亂。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "重点试点",
    "束之高阁",
    "普遍采用",
    "大力推广"
  ],
  "correct_answer": "束之高阁",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很多地方或领域里使用。",
      "explanation": "反义：指把东西捆起来放在高架上，比喻弃置不用，与‘广泛应用’构成反义关系。"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "重點試點",
      "束之高閣",
      "普遍採用",
      "大力推廣"
    ],
    "correct_answer": "束之高閣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很多地方或領域裡使用。",
        "explanation": "反義：指把東西捆起來放在高架上，比喻棄置不用，與‘廣泛應用’構成反義關係。"
      }
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "我们要把新技术广泛应用着在实验室里。",
      "is_correct": false
    },
    {
      "text": "我们要把新技术广泛应用得在多个领域。",
      "is_correct": false
    },
    {
      "text": "我们要把新技术广泛应用起来。",
      "is_correct": true
    },
    {
      "text": "我们要把新技术广泛应用在起来。",
      "is_correct": false
    }
  ],
  "explanation": "语序/结构错误：趋向补语'起来'应紧跟动词'应用'之后，构成'应用起来'，介词短语'在...'不能插入动词和补语之间。 结构错误：'得'后通常接程度或状态补语（如'很广泛'），不能直接接介词短语'在多个领域'来引出地点。 体貌错误：'着'表示持续状态，通常不与表示起始或展开动作的'起来'或此类祈使句中的动态过程自然搭配，且'应用着在...'结构生硬，不符合汉语习惯。",
  "target_word": "广泛应用",
  "hant": {
    "sentences": [
      {
        "text": "我們要把新技術廣泛應用著在實驗室裡。",
        "is_correct": false
      },
      {
        "text": "我們要把新技術廣泛應用得在多個領域。",
        "is_correct": false
      },
      {
        "text": "我們要把新技術廣泛應用起來。",
        "is_correct": true
      },
      {
        "text": "我們要把新技術廣泛應用在起來。",
        "is_correct": false
      }
    ],
    "explanation": "語序/結構錯誤：趨向補語'起來'應緊跟動詞'應用'之後，構成'應用起來'，介詞短語'在...'不能插入動詞和補語之間。 結構錯誤：'得'後通常接程度或狀態補語（如'很廣泛'），不能直接接介詞短語'在多個領域'來引出地點。 體貌錯誤：'著'表示持續狀態，通常不與表示起始或展開動作的'起來'或此類祈使句中的動態過程自然搭配，且'應用著在...'結構生硬，不符合漢語習慣。",
    "target_word": "廣泛應用"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "广泛应用",
  "relation": "antonym",
  "options": [
    "束之高阁",
    "普遍使用",
    "大力推广",
    "重点试点"
  ],
  "correct_answer": "束之高阁",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "在很多地方或领域里使用。",
      "explanation": "指把东西捆起来放在高架上，比喻弃置不用，与‘广泛应用’构成反义关系"
    }
  },
  "hant": {
    "word": "廣泛應用",
    "relation": "antonym",
    "options": [
      "束之高閣",
      "普遍使用",
      "大力推廣",
      "重點試點"
    ],
    "correct_answer": "束之高閣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "在很多地方或領域裡使用。",
        "explanation": "指把東西捆起來放在高架上，比喻棄置不用，與‘廣泛應用’構成反義關係"
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
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "这种新软件在学校里被广泛应用。",
      "is_correct": true
    },
    {
      "text": "这种新软件在学校里被广泛应用了昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”位置错误。在汉语中，时间状语通常放在主语之后、谓语动词之前，或者句首，不能放在句末。"
    },
    {
      "text": "材料科学的进步使得复合材料得以广泛应用，不仅减轻了结构重量，还增强了疲劳耐久性；计算流体动力学（CFD）的发展则使工程师能够在虚拟风洞中模拟极端工况下的气动性能，从而在原型制造前完成多轮迭代。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "這種新軟體在學校裡被廣泛應用。",
        "is_correct": true
      },
      {
        "text": "這種新軟體在學校裡被廣泛應用了昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”位置錯誤。在漢語中，時間狀語通常放在主語之後、謂語動詞之前，或者句首，不能放在句末。"
      },
      {
        "text": "材料科學的進步使得複合材料得以廣泛應用，不僅減輕了結構重量，還增強了疲勞耐久性；計算流體動力學（CFD）的發展則使工程師能夠在虛擬風洞中模擬極端工況下的氣動效能，從而在原型製造前完成多輪迭代。",
        "is_correct": true
      }
    ]
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
      "text": "随着最后一项议程完毕，今天的会议正式结束。",
      "is_correct": true
    },
    {
      "text": "他昨天把作业写毕了。",
      "is_correct": false,
      "error_description": "错误类型：语体风格与搭配不当。'毕'作为单字动词表示'结束/完成'时，多用于书面语或固定复合词（如'完毕'、'毕业'）。在口语或一般叙述中，单独使用'写毕'显得生硬且不自然，通常使用'写完'或'写好'。若要用'毕'，应使用双音节词'完毕'，但'写完毕'也不符合习惯，通常说'作业完毕'或'写作完毕'。对于T3级别学习者，最自然的表达是'写完'。"
    },
    {
      "text": "他把作业写毕了，现在可以出去玩。",
      "is_correct": true
    },
    {
      "text": "这项艰巨的科研任务终于圆满完毕，团队成员们如释重负。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "隨著最後一項議程完畢，今天的會議正式結束。",
        "is_correct": true
      },
      {
        "text": "他昨天把作業寫畢了。",
        "is_correct": false,
        "error_description": "錯誤型別：語體風格與搭配不當。'畢'作為單字動詞表示'結束/完成'時，多用於書面語或固定複合詞（如'完畢'、'畢業'）。在口語或一般敘述中，單獨使用'寫畢'顯得生硬且不自然，通常使用'寫完'或'寫好'。若要用'畢'，應使用雙音節詞'完畢'，但'寫完畢'也不符合習慣，通常說'作業完畢'或'寫作完畢'。對於T3級別學習者，最自然的表達是'寫完'。"
      },
      {
        "text": "他把作業寫畢了，現在可以出去玩。",
        "is_correct": true
      },
      {
        "text": "這項艱鉅的科研任務終於圓滿完畢，團隊成員們如釋重負。",
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

#### Pack B
### Level 3 (sense 10107, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更___泥活字，开启了可重复排版的技术先河。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "首创",
  "options": [
    "模仿",
    "制造",
    "首创",
    "发现"
  ],
  "explanation": "正确。'首创'意为最先创造或发明，符合毕昇发明泥活字的历史事实。",
  "distractor_tags": {},
  "word_definition": "最先创造或发明，指做别人没有做过的事情。",
  "target_word": "首创",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更___泥活字，開啟了可重複排版的技術先河。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "首創",
    "options": [
      "模仿",
      "製造",
      "首創",
      "發現"
    ],
    "explanation": "正確。'首創'意為最先創造或發明，符合畢昇發明泥活字的歷史事實。",
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
      "text": "我们学校正在首创周末读书活动。",
      "is_correct": false
    },
    {
      "text": "周末读书活动被我们学校首创在图书馆。",
      "is_correct": false
    },
    {
      "text": "我们学校首创了周末读书活动给学生们。",
      "is_correct": false
    },
    {
      "text": "我们学校首创了周末读书活动。",
      "is_correct": true
    }
  ],
  "explanation": "体貌错误：'首创'是一个瞬间完成的动作动词，表示从无到有的突破，不能与表示持续进行的'正在'连用。 配价错误：'首创'是及物动词，直接接宾语（被创造的事物），不能像'送'或'给'那样带双宾语或通过介词引出接受者。 语序/搭配错误：被动句式中，'首创'通常不直接跟地点状语'在图书馆'作为补语，这种表达不符合汉语习惯，应改为'由我们学校在图书馆首创'或调整句式。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "我們學校正在首創週末讀書活動。",
        "is_correct": false
      },
      {
        "text": "週末讀書活動被我們學校首創在圖書館。",
        "is_correct": false
      },
      {
        "text": "我們學校首創了週末讀書活動給學生們。",
        "is_correct": false
      },
      {
        "text": "我們學校首創了週末讀書活動。",
        "is_correct": true
      }
    ],
    "explanation": "體貌錯誤：'首創'是一個瞬間完成的動作動詞，表示從無到有的突破，不能與表示持續進行的'正在'連用。 配價錯誤：'首創'是及物動詞，直接接賓語（被創造的事物），不能像'送'或'給'那樣帶雙賓語或通過介詞引出接受者。 語序/搭配錯誤：被動句式中，'首創'通常不直接跟地點狀語'在圖書館'作為補語，這種表達不符合漢語習慣，應改為'由我們學校在圖書館首創'或調整句式。",
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
    "发明",
    "建立",
    "创造",
    "模仿"
  ],
  "correct_answer": "模仿",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "最先创造或发明，指做别人没有做过的事情。",
      "explanation": "反义关系：首创指最先创造，模仿指照样子做，二者在创新性与原创性上构成对立。"
    }
  },
  "hant": {
    "word": "首創",
    "relation": "antonym",
    "options": [
      "發明",
      "建立",
      "創造",
      "模仿"
    ],
    "correct_answer": "模仿",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "最先創造或發明，指做別人沒有做過的事情。",
        "explanation": "反義關係：首創指最先創造，模仿指照樣子做，二者在創新性與原創性上構成對立。"
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
      "text": "这种玩具的设计是他正在首创的吗？",
      "is_correct": false
    },
    {
      "text": "这种玩具的设计被他首创得非常好。",
      "is_correct": false
    },
    {
      "text": "他首创了这种玩具的设计在昨天。",
      "is_correct": false
    },
    {
      "text": "这种玩具的设计是他首创的吗？",
      "is_correct": true
    }
  ],
  "explanation": "体貌错误：'首创'是一个瞬间完成的成就动词，表示动作的完成和结果，不能与表示持续进行的'正在'连用。 语序错误：汉语中时间状语'在昨天'通常放在动词之前或句首，不能像英语一样放在句末。 搭配/补语误用：'首创'强调的是'从无到有'的开创性事实，而不是动作的质量或程度，因此不能用'得非常好'来修饰。",
  "target_word": "首创",
  "hant": {
    "sentences": [
      {
        "text": "這種玩具的設計是他正在首創的嗎？",
        "is_correct": false
      },
      {
        "text": "這種玩具的設計被他首創得非常好。",
        "is_correct": false
      },
      {
        "text": "他首創了這種玩具的設計在昨天。",
        "is_correct": false
      },
      {
        "text": "這種玩具的設計是他首創的嗎？",
        "is_correct": true
      }
    ],
    "explanation": "體貌錯誤：'首創'是一個瞬間完成的成就動詞，表示動作的完成和結果，不能與表示持續進行的'正在'連用。 語序錯誤：漢語中時間狀語'在昨天'通常放在動詞之前或句首，不能像英語一樣放在句末。 搭配/補語誤用：'首創'強調的是'從無到有'的開創性事實，而不是動作的質量或程度，因此不能用'得非常好'來修飾。",
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
