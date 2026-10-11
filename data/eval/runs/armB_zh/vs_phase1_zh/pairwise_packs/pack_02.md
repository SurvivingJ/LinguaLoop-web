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


## sense 10107, level 7

#### Pack A
### Level 7 (sense 10107, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "这家店首创了这种新口味的冰淇淋在昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”通常放在主语之后、谓语动词之前，或者句首，不能放在句末。"
    },
    {
      "text": "他首创了这个有趣的游戏。",
      "is_correct": true
    },
    {
      "text": "这家店首创了这种新口味的冰淇淋。",
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
        "text": "這家店首創了這種新口味的冰淇淋在昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”通常放在主語之後、謂語動詞之前，或者句首，不能放在句末。"
      },
      {
        "text": "他首創了這個有趣的遊戲。",
        "is_correct": true
      },
      {
        "text": "這家店首創了這種新口味的冰淇淋。",
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

---

## sense 10110, level 1

#### Pack A
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
    "可",
    "渴",
    "刻",
    "科"
  ],
  "correct_answer": "可",
  "explanation": "正确。读音为 kě，第三声，表示许可或可能。",
  "distractor_explanations": {
    "科": "错误。读音为 kē，第一声，通常指学科或科学。",
    "渴": "错误。读音为 kě，但意为口渴，与情态动词无关。",
    "刻": "错误。读音为 kè，第四声，通常指时间或雕刻。"
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
      "渴",
      "刻",
      "科"
    ],
    "correct_answer": "可",
    "explanation": "正確。讀音為 kě，第三聲，表示許可或可能。",
    "distractor_explanations": {
      "科": "錯誤。讀音為 kē，第一聲，通常指學科或科學。",
      "渴": "錯誤。讀音為 kě，但意為口渴，與情態動詞無關。",
      "刻": "錯誤。讀音為 kè，第四聲，通常指時間或雕刻。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 10110, level 3

#### Pack A
### Level 3 (sense 10110, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "你___以直接利用自然力来转化能量。",
  "original_sentence": "你可以直接利用自然力来转化能量。",
  "correct_answer": "可",
  "options": [
    "敢",
    "爱",
    "须",
    "可"
  ],
  "explanation": "正确。在此句中表示“可以”，指具备利用自然力的可能性或许可。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "你___以直接利用自然力來轉化能量。",
    "original_sentence": "你可以直接利用自然力來轉化能量。",
    "correct_answer": "可",
    "options": [
      "敢",
      "愛",
      "須",
      "可"
    ],
    "explanation": "正確。在此句中表示“可以”，指具備利用自然力的可能性或許可。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这道题其实___做出来。",
  "original_sentence": "这道题其实可做出来。",
  "correct_answer": "可",
  "options": [
    "敢",
    "须",
    "应",
    "可"
  ],
  "explanation": "正确。在此句中表示‘可能’或‘能够’，语气较口语化，符合语境。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這道題其實___做出來。",
    "original_sentence": "這道題其實可做出來。",
    "correct_answer": "可",
    "options": [
      "敢",
      "須",
      "應",
      "可"
    ],
    "explanation": "正確。在此句中表示‘可能’或‘能夠’，語氣較口語化，符合語境。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```

#### Pack B
### Level 3 (sense 10110, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "去不去公园这事儿___去可不去，反正周末我在家待着也没别的事儿干。",
  "original_sentence": "去不去公园这事儿可去可不去，反正周末我在家待着也没别的事儿干。",
  "correct_answer": "可",
  "options": [
    "可",
    "能",
    "须",
    "该"
  ],
  "explanation": "正确：'可'在'可V可不V'结构中表示许可或选择，符合句意。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "去不去公園這事兒___去可不去，反正週末我在家待著也沒別的事兒幹。",
    "original_sentence": "去不去公園這事兒可去可不去，反正週末我在家待著也沒別的事兒幹。",
    "correct_answer": "可",
    "options": [
      "可",
      "能",
      "須",
      "該"
    ],
    "explanation": "正確：'可'在'可V可不V'結構中表示許可或選擇，符合句意。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这旧纸___把桌子擦干净。",
  "original_sentence": "这旧纸可把桌子擦干净。",
  "correct_answer": "可",
  "options": [
    "敢",
    "配",
    "可",
    "得"
  ],
  "explanation": "正确选项，“可”表示“可以用来”，符合旧纸擦桌子的语境。",
  "distractor_tags": {},
  "word_definition": "表示许可或可能，常用于口语。",
  "target_word": "可",
  "hant": {
    "sentence_with_blank": "這舊紙___把桌子擦乾淨。",
    "original_sentence": "這舊紙可把桌子擦乾淨。",
    "correct_answer": "可",
    "options": [
      "敢",
      "配",
      "可",
      "得"
    ],
    "explanation": "正確選項，“可”表示“可以用來”，符合舊紙擦桌子的語境。",
    "distractor_tags": {},
    "word_definition": "表示許可或可能，常用於口語。",
    "target_word": "可"
  }
}
```

---

## sense 10110, level 7

#### Pack A
### Level 7 (sense 10110, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这件事你可别告诉别人。",
      "is_correct": true
    },
    {
      "text": "如果你愿意，我可帮你复习。",
      "is_correct": true
    },
    {
      "text": "这道题其实可做出来。",
      "is_correct": true
    },
    {
      "text": "这道题其实可做出来。",
      "is_correct": false,
      "error_description": "错误类型：体标/结构不完整。在表示能力或可能性的语境中，单音节情态动词“可”通常不单独作谓语核心来修饰动补结构，且句末缺乏必要的语气助词或动态助词来完句。更自然的表达是使用双音节“可以”，并配合“的”字结构或补语标记，如“可以做出来的”或“可以做出来”。原句“可做出来”口语中极不自然，显得生硬且语法成分残缺。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這件事你可別告訴別人。",
        "is_correct": true
      },
      {
        "text": "如果你願意，我可幫你複習。",
        "is_correct": true
      },
      {
        "text": "這道題其實可做出來。",
        "is_correct": true
      },
      {
        "text": "這道題其實可做出來。",
        "is_correct": false,
        "error_description": "錯誤型別：體標/結構不完整。在表示能力或可能性的語境中，單音節情態動詞“可”通常不單獨作謂語核心來修飾動補結構，且句末缺乏必要的語氣助詞或動態助詞來完句。更自然的表達是使用雙音節“可以”，並配合“的”字結構或補語標記，如“可以做出來的”或“可以做出來”。原句“可做出來”口語中極不自然，顯得生硬且語法成分殘缺。"
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

## sense 10111, level 3

#### Pack A
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "它的设计像一个绿色的箭头圆圈，表示废物可以被___利用。",
  "original_sentence": "它的设计像一个绿色的箭头圆圈，表示废物可以被重复利用。",
  "correct_answer": "重复",
  "options": [
    "破坏",
    "消耗",
    "施展",
    "重复"
  ],
  "explanation": "“重复”在此处表示再次利用，符合废物管理的环保语境与搭配习惯。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被___利用。",
    "original_sentence": "它的設計像一個綠色的箭頭圓圈，表示廢物可以被重複利用。",
    "correct_answer": "重複",
    "options": [
      "破壞",
      "消耗",
      "施展",
      "重複"
    ],
    "explanation": "“重複”在此處表示再次利用，符合廢物管理的環保語境與搭配習慣。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我不喜欢这种___的游戏。",
  "original_sentence": "我不喜欢这种重复的游戏。",
  "correct_answer": "重复",
  "options": [
    "昂贵",
    "重复",
    "打破",
    "复杂"
  ],
  "explanation": "正确选项，表示动作或情况再次出现，符合句意。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "我不喜歡這種___的遊戲。",
    "original_sentence": "我不喜歡這種重複的遊戲。",
    "correct_answer": "重複",
    "options": [
      "昂貴",
      "重複",
      "打破",
      "複雜"
    ],
    "explanation": "正確選項，表示動作或情況再次出現，符合句意。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```

#### Pack B
### Level 3 (sense 10111, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这种错误不应该在作业里___出现。",
  "original_sentence": "这种错误不应该在作业里重复出现。",
  "correct_answer": "重复",
  "options": [
    "继续",
    "坚持",
    "保持",
    "重复"
  ],
  "explanation": "正确。'重复出现'指同样的错误再次发生，符合语境。",
  "distractor_tags": {},
  "word_definition": "表示某个动作或情况再次出现或进行第二次。",
  "target_word": "重复",
  "hant": {
    "sentence_with_blank": "這種錯誤不應該在作業裡___出現。",
    "original_sentence": "這種錯誤不應該在作業裡重複出現。",
    "correct_answer": "重複",
    "options": [
      "繼續",
      "堅持",
      "保持",
      "重複"
    ],
    "explanation": "正確。'重複出現'指同樣的錯誤再次發生，符合語境。",
    "distractor_tags": {},
    "word_definition": "表示某個動作或情況再次出現或進行第二次。",
    "target_word": "重複"
  }
}
```

---

## sense 10111, level 6

#### Pack A
### Level 6 (sense 10111, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "重复",
  "relation": "antonym",
  "options": [
    "继续",
    "练习",
    "模仿",
    "创新"
  ],
  "correct_answer": "创新",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "“重复”指照原样再次进行，“创新”指创造新的事物或方法，二者在动作性质上构成反义关系。"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "繼續",
      "練習",
      "模仿",
      "創新"
    ],
    "correct_answer": "創新",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "“重複”指照原樣再次進行，“創新”指創造新的事物或方法，二者在動作性質上構成反義關係。"
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
      "text": "不要总是对别人的观点重复去。",
      "is_correct": false
    },
    {
      "text": "不要总是重复着别人的观点已经。",
      "is_correct": false
    },
    {
      "text": "不要总是重复别人的观点，要有自己的想法。",
      "is_correct": true
    },
    {
      "text": "不要总是把别人的观点重复有。",
      "is_correct": false
    }
  ],
  "explanation": "语法错误：'有'不能作为结果补语与'重复'搭配，应改为'重复别人的观点'或'重复出...'（视具体语境），此处结构混乱。 语序错误：时间副词或完成态标记'已经'位置错误，不应置于句末，且与'着'（进行态）冲突。 补语误用：'去'作为趋向补语表示离开说话人方向，与'重复'这一抽象认知行为搭配不当，语义不通。",
  "target_word": "重复",
  "hant": {
    "sentences": [
      {
        "text": "不要總是對別人的觀點重複去。",
        "is_correct": false
      },
      {
        "text": "不要總是重複著別人的觀點已經。",
        "is_correct": false
      },
      {
        "text": "不要總是重複別人的觀點，要有自己的想法。",
        "is_correct": true
      },
      {
        "text": "不要總是把別人的觀點重複有。",
        "is_correct": false
      }
    ],
    "explanation": "語法錯誤：'有'不能作為結果補語與'重複'搭配，應改為'重複別人的觀點'或'重複出...'（視具體語境），此處結構混亂。 語序錯誤：時間副詞或完成態標記'已經'位置錯誤，不應置於句末，且與'著'（進行態）衝突。 補語誤用：'去'作為趨向補語表示離開說話人方向，與'重複'這一抽象認知行為搭配不當，語義不通。",
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
    "创新",
    "继续",
    "模仿",
    "练习"
  ],
  "correct_answer": "创新",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示某个动作或情况再次出现或进行第二次。",
      "explanation": "反义词：指创造新的事物或方法，与‘再次出现’的重复义相对。"
    }
  },
  "hant": {
    "word": "重複",
    "relation": "antonym",
    "options": [
      "創新",
      "繼續",
      "模仿",
      "練習"
    ],
    "correct_answer": "創新",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示某個動作或情況再次出現或進行第二次。",
        "explanation": "反義詞：指創造新的事物或方法，與‘再次出現’的重複義相對。"
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

## sense 10112, level 6

#### Pack A
### Level 6 (sense 10112, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正在排版着那本杂志的封面。",
      "is_correct": false
    },
    {
      "text": "哥哥在大学学排版。",
      "is_correct": true
    },
    {
      "text": "他排版每天在公司里。",
      "is_correct": false
    },
    {
      "text": "他把那篇文章排版出来了。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。“排版”是动宾式离合词，动态助词“着”应插在动词和宾语之间，说成“排着版”，不能直接加在词后。 语序错误。时间状语“每天”应放在动词“排版”之前或句首，不能放在动宾结构之后。 结果补语误用。“排版”是离合词，结果补语“出来”应插在“排”和“版”之间，说成“排出（了）版来”，不能直接放在词后。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "他正在排版著那本雜誌的封面。",
        "is_correct": false
      },
      {
        "text": "哥哥在大學學排版。",
        "is_correct": true
      },
      {
        "text": "他排版每天在公司裡。",
        "is_correct": false
      },
      {
        "text": "他把那篇文章排版出來了。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。“排版”是動賓式離合詞，動態助詞“著”應插在動詞和賓語之間，說成“排著版”，不能直接加在詞後。 語序錯誤。時間狀語“每天”應放在動詞“排版”之前或句首，不能放在動賓結構之後。 結果補語誤用。“排版”是離合詞，結果補語“出來”應插在“排”和“版”之間，說成“排出（了）版來”，不能直接放在詞後。",
    "target_word": "排版"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他排版校刊正在。",
      "is_correct": false
    },
    {
      "text": "他把文章排版进去。",
      "is_correct": false
    },
    {
      "text": "他排版了着校刊封面。",
      "is_correct": false
    },
    {
      "text": "排版工作非常辛苦。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误：“了”和“着”不能连用表示完成和进行，应去掉“了”或改为“正在排版”。 语序错误：副词“正在”应放在动词“排版”之前作状语，不能放在句末。 方向/结果补语误用：“进去”表示由外到内的方向，与“排版”的语义不搭配，应改为“排版好”或“排版完”。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "他排版校刊正在。",
        "is_correct": false
      },
      {
        "text": "他把文章排版進去。",
        "is_correct": false
      },
      {
        "text": "他排版了著校刊封面。",
        "is_correct": false
      },
      {
        "text": "排版工作非常辛苦。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤：“了”和“著”不能連用表示完成和進行，應去掉“了”或改為“正在排版”。 語序錯誤：副詞“正在”應放在動詞“排版”之前作狀語，不能放在句末。 方向/結果補語誤用：“進去”表示由外到內的方向，與“排版”的語義不搭配，應改為“排版好”或“排版完”。",
    "target_word": "排版"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "打乱",
    "印刷",
    "编辑",
    "校对"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字、图片按规则排列组合，方便阅读。",
      "explanation": "反义：排版是按规则有序排列，打乱是破坏秩序使之无序"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "打亂",
      "印刷",
      "編輯",
      "校對"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字、圖片按規則排列組合，方便閱讀。",
        "explanation": "反義：排版是按規則有序排列，打亂是破壞秩序使之無序"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10112, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他排版得正在电脑前认真。",
      "is_correct": false
    },
    {
      "text": "他把电脑前认真地排版了。",
      "is_correct": false
    },
    {
      "text": "他正在电脑前认真地排版。",
      "is_correct": true
    },
    {
      "text": "他正在电脑前认真地排版着。",
      "is_correct": false
    }
  ],
  "explanation": "体标误用：‘正在’表示进行时，通常不与持续体标记‘着’连用用于此类动态动词，显得冗余且不自然。一般说‘正在排版’或‘排着版’（若强调状态），但‘正在...排版着’结构杂糅。 语序错误：状语‘正在电脑前认真’位置错误，不应放在补语标记‘得’之后。正确的语序应为‘他正在电脑前认真地排版’。 配价/论元错误：‘把’字句要求宾语是受事者（如‘文章’、‘海报’），而‘电脑前’是地点状语，不能作为‘排版’的直接处置对象。",
  "target_word": "排版",
  "hant": {
    "sentences": [
      {
        "text": "他排版得正在電腦前認真。",
        "is_correct": false
      },
      {
        "text": "他把電腦前認真地排版了。",
        "is_correct": false
      },
      {
        "text": "他正在電腦前認真地排版。",
        "is_correct": true
      },
      {
        "text": "他正在電腦前認真地排版著。",
        "is_correct": false
      }
    ],
    "explanation": "體標誤用：‘正在’表示進行時，通常不與持續體標記‘著’連用用於此類動態動詞，顯得冗餘且不自然。一般說‘正在排版’或‘排著版’（若強調狀態），但‘正在...排版著’結構雜糅。 語序錯誤：狀語‘正在電腦前認真’位置錯誤，不應放在補語標記‘得’之後。正確的語序應為‘他正在電腦前認真地排版’。 配價/論元錯誤：‘把’字句要求賓語是受事者（如‘文章’、‘海報’），而‘電腦前’是地點狀語，不能作為‘排版’的直接處置物件。",
    "target_word": "排版"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "打印",
    "校对",
    "打乱",
    "编辑"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字或图片按规则排列好",
      "explanation": "反义词：指使原本有序排列的图文变得混乱无序，与“按规则排列好”构成反义关系"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "列印",
      "校對",
      "打亂",
      "編輯"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字或圖片按規則排列好",
        "explanation": "反義詞：指使原本有序排列的圖文變得混亂無序，與“按規則排列好”構成反義關係"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "排版",
  "relation": "antonym",
  "options": [
    "编辑",
    "校对",
    "整理",
    "打乱"
  ],
  "correct_answer": "打乱",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "把文字或图片按规则排列好",
      "explanation": "反义词：指使原本有序排列的图文变得混乱无序，与“按规则排列”构成反义关系。"
    }
  },
  "hant": {
    "word": "排版",
    "relation": "antonym",
    "options": [
      "編輯",
      "校對",
      "整理",
      "打亂"
    ],
    "correct_answer": "打亂",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "把文字或圖片按規則排列好",
        "explanation": "反義詞：指使原本有序排列的圖文變得混亂無序，與“按規則排列”構成反義關係。"
      }
    }
  }
}
```

---

## sense 10112, level 7

#### Pack A
### Level 7 (sense 10112, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我学过怎么给书排版。",
      "is_correct": true
    },
    {
      "text": "他负责给网站排版。",
      "is_correct": true
    },
    {
      "text": "他负责给网站排版了昨天。",
      "is_correct": false,
      "error_description": "时间状语“昨天”通常放在主语之后、谓语动词之前，或者句首，不能放在句末。"
    },
    {
      "text": "这本书的排版有些乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我學過怎麼給書排版。",
        "is_correct": true
      },
      {
        "text": "他負責給網站排版。",
        "is_correct": true
      },
      {
        "text": "他負責給網站排版了昨天。",
        "is_correct": false,
        "error_description": "時間狀語“昨天”通常放在主語之後、謂語動詞之前，或者句首，不能放在句末。"
      },
      {
        "text": "這本書的排版有些亂。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10112, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我正在为校刊排版。",
      "is_correct": true
    },
    {
      "text": "请把这篇文章排版下来。",
      "is_correct": false,
      "error_description": "错误类型为结果补语误用。“排版”表示使文章格式整齐，达到预期效果应使用结果补语“好”，正确写法为“排版好”，不能用“下来”。"
    },
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "然而，受制于汉字数量庞大、排版复杂以及社会结构的限制，这一技术未能引发大规模的知识普及浪潮。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我正在為校刊排版。",
        "is_correct": true
      },
      {
        "text": "請把這篇文章排版下來。",
        "is_correct": false,
        "error_description": "錯誤型別為結果補語誤用。“排版”表示使文章格式整齊，達到預期效果應使用結果補語“好”，正確寫法為“排版好”，不能用“下來”。"
      },
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "然而，受制於漢字數量龐大、排版複雜以及社會結構的限制，這一技術未能引發大規模的知識普及浪潮。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10113, level 3

#### Pack A
### Level 3 (sense 10113, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术___。",
  "original_sentence": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
  "correct_answer": "先河",
  "options": [
    "局面",
    "先河",
    "前景",
    "先锋"
  ],
  "explanation": "正确。'开...先河'是固定搭配，比喻开创某种事业或做法。",
  "distractor_tags": {},
  "word_definition": "比喻某一事业或行动的开创者或最早的做法。",
  "target_word": "先河",
  "hant": {
    "sentence_with_blank": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術___。",
    "original_sentence": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
    "correct_answer": "先河",
    "options": [
      "局面",
      "先河",
      "前景",
      "先鋒"
    ],
    "explanation": "正確。'開...先河'是固定搭配，比喻開創某種事業或做法。",
    "distractor_tags": {},
    "word_definition": "比喻某一事業或行動的開創者或最早的做法。",
    "target_word": "先河"
  }
}
```

#### Pack B
### Level 3 (sense 10113, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "老师表扬了他，说他开了___。",
  "original_sentence": "老师表扬了他，说他开了先河。",
  "correct_answer": "先河",
  "options": [
    "先鞭",
    "先锋",
    "先声",
    "先河"
  ],
  "explanation": "正确选项。“开先河”为固定搭配，意为开创某种事业或做法，符合老师表扬的语境。",
  "distractor_tags": {},
  "word_definition": "先河比喻某一事业或行动的开创者或最早的做法。",
  "target_word": "先河",
  "hant": {
    "sentence_with_blank": "老師表揚了他，說他開了___。",
    "original_sentence": "老師表揚了他，說他開了先河。",
    "correct_answer": "先河",
    "options": [
      "先鞭",
      "先鋒",
      "先聲",
      "先河"
    ],
    "explanation": "正確選項。“開先河”為固定搭配，意為開創某種事業或做法，符合老師表揚的語境。",
    "distractor_tags": {},
    "word_definition": "先河比喻某一事業或行動的開創者或最早的做法。",
    "target_word": "先河"
  }
}
```

---

## sense 10113, level 6

#### Pack A
### Level 6 (sense 10113, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正开着先河，后面的事就好办了。",
      "is_correct": false
    },
    {
      "text": "他先河开了，后面的事就好办了。",
      "is_correct": false
    },
    {
      "text": "这是一条先河，大家都很喜欢。",
      "is_correct": false
    },
    {
      "text": "先河之作的销量非常好。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：“先河”是抽象名词，指代开创的做法，不能使用具体名词的量词“条”。 体标选用错误：“开先河”表示开创的完成动作，具有瞬间性，不能使用表示动作持续的体标“着”。 语序错误：宾语“先河”错误地放在了动词“开”之前，破坏了正常的“主—谓—宾”语序。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "他正開著先河，後面的事就好辦了。",
        "is_correct": false
      },
      {
        "text": "他先河開了，後面的事就好辦了。",
        "is_correct": false
      },
      {
        "text": "這是一條先河，大家都很喜歡。",
        "is_correct": false
      },
      {
        "text": "先河之作的銷量非常好。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：“先河”是抽象名詞，指代開創的做法，不能使用具體名詞的量詞“條”。 體標選用錯誤：“開先河”表示開創的完成動作，具有瞬間性，不能使用表示動作持續的體標“著”。 語序錯誤：賓語“先河”錯誤地放在了動詞“開”之前，破壞了正常的“主—謂—賓”語序。",
    "target_word": "先河"
  }
}
```

#### Pack B
### Level 6 (sense 10113, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师鼓励我们勇于开创了先河。",
      "is_correct": false
    },
    {
      "text": "我们要学习这种敢开先河的精神。",
      "is_correct": true
    },
    {
      "text": "我们要学习这种敢开一条先河的精神。",
      "is_correct": false
    },
    {
      "text": "先河被我们勇于开创。",
      "is_correct": false
    }
  ],
  "explanation": "量词错误：'先河'是抽象名词，比喻开创性的行为或源头，不能用量词'条'修饰。 体貌错误：句中表达的是鼓励一种普遍的精神或态度，应用一般现在时或动词原形概念，加'了'表示动作已完成，与'鼓励我们勇于...'的语境冲突。 语用/语序错误：'开先河'常作为主动语态下的惯用表达，强调主体的主动性；被动句式在此处显得生硬且不自然，破坏了成语性搭配的流畅度。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "老師鼓勵我們勇於開創了先河。",
        "is_correct": false
      },
      {
        "text": "我們要學習這種敢開先河的精神。",
        "is_correct": true
      },
      {
        "text": "我們要學習這種敢開一條先河的精神。",
        "is_correct": false
      },
      {
        "text": "先河被我們勇於開創。",
        "is_correct": false
      }
    ],
    "explanation": "量詞錯誤：'先河'是抽象名詞，比喻開創性的行為或源頭，不能用量詞'條'修飾。 體貌錯誤：句中表達的是鼓勵一種普遍的精神或態度，應用一般現在時或動詞原形概念，加'了'表示動作已完成，與'鼓勵我們勇於...'的語境衝突。 語用/語序錯誤：'開先河'常作為主動語態下的慣用表達，強調主體的主動性；被動句式在此處顯得生硬且不自然，破壞了成語性搭配的流暢度。",
    "target_word": "先河"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "老师鼓励我们勇于开创一条先河。",
      "is_correct": false
    },
    {
      "text": "老师鼓励我们勇于开创先河。",
      "is_correct": true
    },
    {
      "text": "老师鼓励我们勇于开创了先河。",
      "is_correct": false
    },
    {
      "text": "老师鼓励先河我们勇于开创。",
      "is_correct": false
    }
  ],
  "explanation": "量词错误：'先河'是抽象名词，比喻开创性的行为或事业，通常不与个体量词'一条'搭配，直接使用'开创先河'即可。 体貌错误：句中'鼓励'表示建议或期望，后面的动作尚未发生或作为一种精神提倡，不应使用表示完成的动态助词'了'。 语序错误：'先河'是'开创'的宾语，被错误地前置到了主语位置，破坏了'主-谓-宾'的基本句法结构，导致语义不通。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "老師鼓勵我們勇於開創一條先河。",
        "is_correct": false
      },
      {
        "text": "老師鼓勵我們勇於開創先河。",
        "is_correct": true
      },
      {
        "text": "老師鼓勵我們勇於開創了先河。",
        "is_correct": false
      },
      {
        "text": "老師鼓勵先河我們勇於開創。",
        "is_correct": false
      }
    ],
    "explanation": "量詞錯誤：'先河'是抽象名詞，比喻開創性的行為或事業，通常不與個體量詞'一條'搭配，直接使用'開創先河'即可。 體貌錯誤：句中'鼓勵'表示建議或期望，後面的動作尚未發生或作為一種精神提倡，不應使用表示完成的動態助詞'了'。 語序錯誤：'先河'是'開創'的賓語，被錯誤地前置到了主語位置，破壞了'主-謂-賓'的基本句法結構，導致語義不通。",
    "target_word": "先河"
  }
}
```

---
