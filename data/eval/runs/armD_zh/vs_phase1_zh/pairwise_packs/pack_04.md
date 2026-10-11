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


## sense 10125, level 7

#### Pack A
### Level 7 (sense 10125, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这才是真正的快乐。",
      "is_correct": true
    },
    {
      "text": "我想去真正的森林里看看。",
      "is_correct": true
    },
    {
      "text": "我真正喜欢这首歌。",
      "is_correct": true
    },
    {
      "text": "我真正喜欢了这首歌。",
      "is_correct": false,
      "error_description": "体标位置错误。副词“真正”修饰心理动词“喜欢”时，表示一种真实的状态或程度，通常不与表示完成的动态助词“了”连用，应去掉“了”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這才是真正的快樂。",
        "is_correct": true
      },
      {
        "text": "我想去真正的森林裡看看。",
        "is_correct": true
      },
      {
        "text": "我真正喜歡這首歌。",
        "is_correct": true
      },
      {
        "text": "我真正喜歡了這首歌。",
        "is_correct": false,
        "error_description": "體標位置錯誤。副詞“真正”修飾心理動詞“喜歡”時，表示一種真實的狀態或程度，通常不與表示完成的動態助詞“了”連用，應去掉“了”。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10125, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "她真正关心你的感受。",
      "is_correct": true
    },
    {
      "text": "只有长期相处，两人才能真正建立感情。",
      "is_correct": true
    },
    {
      "text": "她关心真正你的感受。",
      "is_correct": false,
      "error_description": "语序错误。副词“真正”应该放在动词“关心”之前作状语，不能放在动词和宾语之间。"
    },
    {
      "text": "我真正喜欢听音乐。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她真正關心你的感受。",
        "is_correct": true
      },
      {
        "text": "只有長期相處，兩人才能真正建立感情。",
        "is_correct": true
      },
      {
        "text": "她關心真正你的感受。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“真正”應該放在動詞“關心”之前作狀語，不能放在動詞和賓語之間。"
      },
      {
        "text": "我真正喜歡聽音樂。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10131, level 6

#### Pack A
### Level 6 (sense 10131, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们计划去一条那个地区旅游。",
      "is_correct": false
    },
    {
      "text": "去那个地区我们计划旅游。",
      "is_correct": false
    },
    {
      "text": "我们计划去那个地区旅游。",
      "is_correct": true
    },
    {
      "text": "我们计划去那个地区着了旅游。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“地区”是表示范围的抽象/具体名词，不能用用于长条形事物的量词“一条”，应直接说“去那个地区”。 体标位置与选用错误：“着”表示动作进行或状态持续，不能放在宾语后表示旅游的目的或计划，应删去“着了”或改为“去那个地区旅游”。 语序错误：时间或地点状语“去那个地区”不应放在主语“我们”和谓语“计划”之前，破坏了正常的“主语—谓语—宾语”语序。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "我們計劃去一條那個地區旅遊。",
        "is_correct": false
      },
      {
        "text": "去那個地區我們計劃旅遊。",
        "is_correct": false
      },
      {
        "text": "我們計劃去那個地區旅遊。",
        "is_correct": true
      },
      {
        "text": "我們計劃去那個地區著了旅遊。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“地區”是表示範圍的抽象/具體名詞，不能用用於長條形事物的量詞“一條”，應直接說“去那個地區”。 體標位置與選用錯誤：“著”表示動作進行或狀態持續，不能放在賓語後表示旅遊的目的或計劃，應刪去“著了”或改為“去那個地區旅遊”。 語序錯誤：時間或地點狀語“去那個地區”不應放在主語“我們”和謂語“計劃”之前，破壞了正常的“主語—謂語—賓語”語序。",
    "target_word": "地區"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们把这个地区打扫干净了。",
      "is_correct": true
    },
    {
      "text": "我们把这个个地区打扫干净了。",
      "is_correct": false
    },
    {
      "text": "把这个地区我们打扫干净了。",
      "is_correct": false
    },
    {
      "text": "我们把这个地区打扫着干净了。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：名词“地区”前不应使用重叠量词“个个”，应直接使用指示代词“这个”。 体标位置错误：动态助词“着”表示动作持续，不能放在动词“打扫”和结果补语“干净”之间，应删去。 语序错误：介词结构“把这个地区”作为状语应放在主语“我们”之后，原句破坏了正常的“主—状—谓”语序。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "我們把這個地區打掃乾淨了。",
        "is_correct": true
      },
      {
        "text": "我們把這個個地區打掃乾淨了。",
        "is_correct": false
      },
      {
        "text": "把這個地區我們打掃乾淨了。",
        "is_correct": false
      },
      {
        "text": "我們把這個地區打掃著乾淨了。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：名詞“地區”前不應使用重疊量詞“個個”，應直接使用指示代詞“這個”。 體標位置錯誤：動態助詞“著”表示動作持續，不能放在動詞“打掃”和結果補語“乾淨”之間，應刪去。 語序錯誤：介詞結構“把這個地區”作為狀語應放在主語“我們”之後，原句破壞了正常的“主—狀—謂”語序。",
    "target_word": "地區"
  }
}
```

#### Pack B
### Level 6 (sense 10131, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那个地区很多游客吸引了。",
      "is_correct": false
    },
    {
      "text": "那个地区吸引了很多游客。",
      "is_correct": true
    },
    {
      "text": "那个地区吸引了着很多游客。",
      "is_correct": false
    },
    {
      "text": "一条地区吸引了很多游客。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'地区'是表示范围的名词，应使用'个'或'片'等量词，不能使用用于长条状物体的'条'。 体标选用错误：动态助词'了'表示动作完成，'着'表示状态持续，两者不能同时用在动词'吸引'后面。 语序错误：宾语'很多游客'被错误地放在了动词'吸引'之前，破坏了汉语正常的'主-谓-宾'语序。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "那個地區很多遊客吸引了。",
        "is_correct": false
      },
      {
        "text": "那個地區吸引了很多遊客。",
        "is_correct": true
      },
      {
        "text": "那個地區吸引了著很多遊客。",
        "is_correct": false
      },
      {
        "text": "一條地區吸引了很多遊客。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'地區'是表示範圍的名詞，應使用'個'或'片'等量詞，不能使用用於長條狀物體的'條'。 體標選用錯誤：動態助詞'了'表示動作完成，'著'表示狀態持續，兩者不能同時用在動詞'吸引'後面。 語序錯誤：賓語'很多遊客'被錯誤地放在了動詞'吸引'之前，破壞了漢語正常的'主-謂-賓'語序。",
    "target_word": "地區"
  }
}
```

---

## sense 10131, level 7

#### Pack A
### Level 7 (sense 10131, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他住了三年在这个地区。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，表示地点的介词短语（如‘在这个地区’）应放在动词前作状语，不能放在动词之后。正确语序为‘主语+地点状语+动词+时量补语’。"
    },
    {
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    },
    {
      "text": "这个地区的气候非常温暖。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他住了三年在這個地區。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，表示地點的介詞短語（如‘在這個地區’）應放在動詞前作狀語，不能放在動詞之後。正確語序為‘主語+地點狀語+動詞+時量補語’。"
      },
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      },
      {
        "text": "這個地區的氣候非常溫暖。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
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
      "text": "那个地区吸引了很多游客。",
      "is_correct": true
    },
    {
      "text": "那个地区正下着大雨。",
      "is_correct": true
    },
    {
      "text": "他住了三年在这个地区。",
      "is_correct": false,
      "error_description": "语序错误。在汉语中，表示地点的介词短语（如‘在这个地区’）应放在动词（如‘住’）之前作状语，不能放在句末。"
    },
    {
      "text": "这个地区的发展一直很好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "那個地區吸引了很多遊客。",
        "is_correct": true
      },
      {
        "text": "那個地區正下著大雨。",
        "is_correct": true
      },
      {
        "text": "他住了三年在這個地區。",
        "is_correct": false,
        "error_description": "語序錯誤。在漢語中，表示地點的介詞短語（如‘在這個地區’）應放在動詞（如‘住’）之前作狀語，不能放在句末。"
      },
      {
        "text": "這個地區的發展一直很好。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10131, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个地区的气候很温暖。",
      "is_correct": true
    },
    {
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    },
    {
      "text": "在地区一些干旱的，人们很早就学会了如何节约用水。",
      "is_correct": false,
      "error_description": "语序错误。数量短语“一些”和形容词“干旱的”应该放在名词“地区”的前面作定语，正确的语序是“在一些干旱的地区”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這個地區的氣候很溫暖。",
        "is_correct": true
      },
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
        "is_correct": true
      },
      {
        "text": "在地區一些乾旱的，人們很早就學會了如何節約用水。",
        "is_correct": false,
        "error_description": "語序錯誤。數量短語“一些”和形容詞“乾旱的”應該放在名詞“地區”的前面作定語，正確的語序是“在一些乾旱的地區”。"
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
      "text": "我们把这个地区打扫干净了。",
      "is_correct": true
    },
    {
      "text": "这个地区发生过很大的变化。",
      "is_correct": true
    },
    {
      "text": "我从来没有去过那个地区。",
      "is_correct": true
    },
    {
      "text": "我从来没有去过那个个地区。",
      "is_correct": false,
      "error_description": "量词使用错误。“地区”的量词应为“个”，“那个”已经包含了量词“个”，不能重复使用“个个”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們把這個地區打掃乾淨了。",
        "is_correct": true
      },
      {
        "text": "這個地區發生過很大的變化。",
        "is_correct": true
      },
      {
        "text": "我從來沒有去過那個地區。",
        "is_correct": true
      },
      {
        "text": "我從來沒有去過那個個地區。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“地區”的量詞應為“個”，“那個”已經包含了量詞“個”，不能重複使用“個個”。"
      }
    ]
  }
}
```

---

## sense 10137, level 3

#### Pack A
### Level 3 (sense 10137, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他所改良的金属活字印刷系统，能够将文字直接___在纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "original_sentence": "他所改良的金属活字印刷系统，能够将文字直接压印在纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "correct_answer": "压印",
  "options": [
    "压印",
    "复印",
    "雕刻",
    "描绘"
  ],
  "explanation": "正确。“压印”指通过压力使表面留下图案，符合金属活字印刷的语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "他所改良的金屬活字印刷系統，能夠將文字直接___在紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "original_sentence": "他所改良的金屬活字印刷系統，能夠將文字直接壓印在紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "correct_answer": "壓印",
    "options": [
      "壓印",
      "影印",
      "雕刻",
      "描繪"
    ],
    "explanation": "正確。“壓印”指通過壓力使表面留下圖案，符合金屬活字印刷的語境。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "同学们很喜欢___这种手工。",
  "original_sentence": "同学们很喜欢压印这种手工。",
  "correct_answer": "压印",
  "options": [
    "描绘",
    "雕刻",
    "压印",
    "编织"
  ],
  "explanation": "正确。原句意为同学们喜欢这种通过施加压力留下图案的手工活动。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "同學們很喜歡___這種手工。",
    "original_sentence": "同學們很喜歡壓印這種手工。",
    "correct_answer": "壓印",
    "options": [
      "描繪",
      "雕刻",
      "壓印",
      "編織"
    ],
    "explanation": "正確。原句意為同學們喜歡這種通過施加壓力留下圖案的手工活動。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```

#### Pack B
### Level 3 (sense 10137, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面___出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
  "original_sentence": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面压印出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
  "correct_answer": "压印",
  "options": [
    "压印",
    "烙印",
    "盖",
    "描绘"
  ],
  "explanation": "正确选项。符合句中通过机械装置施加压力在纸张上留下文字痕迹的语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面___出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
    "original_sentence": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面壓印出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
    "correct_answer": "壓印",
    "options": [
      "壓印",
      "烙印",
      "蓋",
      "描繪"
    ],
    "explanation": "正確選項。符合句中通過機械裝置施加壓力在紙張上留下文字痕跡的語境。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "你___的图案真好看，我很喜欢。",
  "original_sentence": "你压印的图案真好看，我很喜欢。",
  "correct_answer": "压印",
  "options": [
    "压印",
    "测量",
    "撕裂",
    "销毁"
  ],
  "explanation": "正确。压印指通过压力留下痕迹，符合语境中制作出好看图案的动作。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "你___的圖案真好看，我很喜歡。",
    "original_sentence": "你壓印的圖案真好看，我很喜歡。",
    "correct_answer": "壓印",
    "options": [
      "壓印",
      "測量",
      "撕裂",
      "銷燬"
    ],
    "explanation": "正確。壓印指通過壓力留下痕跡，符合語境中製作出好看圖案的動作。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```

---

## sense 10137, level 6

#### Pack A
### Level 6 (sense 10137, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们把花瓣压印起在画布上呢。",
      "is_correct": false
    },
    {
      "text": "我们正把花瓣压印了画布上呢。",
      "is_correct": false
    },
    {
      "text": "我们正把花瓣压印在画布上呢。",
      "is_correct": true
    },
    {
      "text": "我们正压印把花瓣在画布上呢。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误。进行体标记“正……呢”与完成体标记“了”冲突，且“了”后直接接处所名词不符合语法，应为“压印在”。 语序错误。“把”字及其宾语“花瓣”被错误放置于动词之后，破坏了“把+宾语+动词+补语”的正确句法结构。 方向/结果补语误用。结果补语“起”表示动作开始或物体向上，与处所补语“在画布上”表示的附着状态语义冲突，应直接使用“压印在”。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "我們把花瓣壓印起在畫布上呢。",
        "is_correct": false
      },
      {
        "text": "我們正把花瓣壓印了畫布上呢。",
        "is_correct": false
      },
      {
        "text": "我們正把花瓣壓印在畫布上呢。",
        "is_correct": true
      },
      {
        "text": "我們正壓印把花瓣在畫布上呢。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤。進行體標記“正……呢”與完成體標記“了”衝突，且“了”後直接接處所名詞不符合語法，應為“壓印在”。 語序錯誤。“把”字及其賓語“花瓣”被錯誤放置於動詞之後，破壞了“把+賓語+動詞+補語”的正確句法結構。 方向/結果補語誤用。結果補語“起”表示動作開始或物體向上，與處所補語“在畫布上”表示的附著狀態語義衝突，應直接使用“壓印在”。",
    "target_word": "壓印"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在手工纸上干花压印真美。",
      "is_correct": false
    },
    {
      "text": "干花压印在手工纸上真美。",
      "is_correct": true
    },
    {
      "text": "干花压印起在手工纸上真美。",
      "is_correct": false
    },
    {
      "text": "干花压印过在手工纸上真美。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用与语序错误。“过”表示过去的经历，与当前欣赏的语境不符，且“过”应放在“在手工纸上”之后。 语序错误。处所状语“在手工纸上”放在句首时，主语“干花”应紧跟其后，原句破坏了正常的语序结构。 方向/结果补语误用。“起”表示向上或开始，而此处表示施加压力使痕迹附着于纸面，应使用表示附着的补语，且“起在”搭配不当。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "在手工紙上乾花壓印真美。",
        "is_correct": false
      },
      {
        "text": "乾花壓印在手工紙上真美。",
        "is_correct": true
      },
      {
        "text": "乾花壓印起在手工紙上真美。",
        "is_correct": false
      },
      {
        "text": "乾花壓印過在手工紙上真美。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用與語序錯誤。“過”表示過去的經歷，與當前欣賞的語境不符，且“過”應放在“在手工紙上”之後。 語序錯誤。處所狀語“在手工紙上”放在句首時，主語“乾花”應緊跟其後，原句破壞了正常的語序結構。 方向/結果補語誤用。“起”表示向上或開始，而此處表示施加壓力使痕跡附著於紙面，應使用表示附著的補語，且“起在”搭配不當。",
    "target_word": "壓印"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "压制",
    "抹平",
    "雕刻",
    "拓印"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义：压印是施压留下痕迹，抹平是消除痕迹使表面恢复平坦"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "壓制",
      "抹平",
      "雕刻",
      "拓印"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義：壓印是施壓留下痕跡，抹平是消除痕跡使表面恢復平坦"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10137, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "印刷",
    "雕刻",
    "擦除",
    "描绘"
  ],
  "correct_answer": "擦除",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义项：擦除指去除物体表面痕迹，与压印（施加压力留下痕迹）构成反义关系"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "印刷",
      "雕刻",
      "擦除",
      "描繪"
    ],
    "correct_answer": "擦除",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義項：擦除指去除物體表面痕跡，與壓印（施加壓力留下痕跡）構成反義關係"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "拓印",
    "抹平",
    "雕刻",
    "按压"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "抹平指消除痕迹或使表面平整，与压印（留下痕迹）构成反义。"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "拓印",
      "抹平",
      "雕刻",
      "按壓"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "抹平指消除痕跡或使表面平整，與壓印（留下痕跡）構成反義。"
      }
    }
  }
}
```

---

## sense 10137, level 7

#### Pack A
### Level 7 (sense 10137, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我把树叶压印在纸上，送给好朋友。",
      "is_correct": true
    },
    {
      "text": "他所改良的金属活字印刷系统，通过螺旋装置在纸张表面压印出清晰的文字，结合油性墨水与精确铸造技术，实现了复制的标准化与高效率生产。",
      "is_correct": true
    },
    {
      "text": "她在书签上压印过很多漂亮的图案。",
      "is_correct": true
    },
    {
      "text": "我把树叶压印了纸上，送给好朋友。",
      "is_correct": false,
      "error_description": "在“把”字句中，动词后接处所补语时，必须使用介词“在”引出地点，不能省略“在”。正确写法是“压印在纸上”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我把樹葉壓印在紙上，送給好朋友。",
        "is_correct": true
      },
      {
        "text": "他所改良的金屬活字印刷系統，通過螺旋裝置在紙張表面壓印出清晰的文字，結合油性墨水與精確鑄造技術，實現了複製的標準化與高效率生產。",
        "is_correct": true
      },
      {
        "text": "她在書籤上壓印過很多漂亮的圖案。",
        "is_correct": true
      },
      {
        "text": "我把樹葉壓印了紙上，送給好朋友。",
        "is_correct": false,
        "error_description": "在“把”字句中，動詞後接處所補語時，必須使用介詞“在”引出地點，不能省略“在”。正確寫法是“壓印在紙上”。"
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
      "text": "他压印名字在信封上了。",
      "is_correct": false,
      "error_description": "语序错误。动词后接“在+处所”作补语时，宾语需借助“把”字提前，或将处所状语置于动词前，不能直接采用“动词+宾语+在+处所”的结构。"
    },
    {
      "text": "你压印的图案真好看，我很喜欢。",
      "is_correct": true
    },
    {
      "text": "干花压印在手工纸上真美。",
      "is_correct": true
    },
    {
      "text": "他把名字压印在信封上了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他壓印名字在信封上了。",
        "is_correct": false,
        "error_description": "語序錯誤。動詞後接“在+處所”作補語時，賓語需藉助“把”字提前，或將處所狀語置於動詞前，不能直接採用“動詞+賓語+在+處所”的結構。"
      },
      {
        "text": "你壓印的圖案真好看，我很喜歡。",
        "is_correct": true
      },
      {
        "text": "乾花壓印在手工紙上真美。",
        "is_correct": true
      },
      {
        "text": "他把名字壓印在信封上了。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10137, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "工人把图案压印在木板上。",
      "is_correct": true
    },
    {
      "text": "他正在压印一张漂亮的贺卡。",
      "is_correct": true
    },
    {
      "text": "他所改良的金属活字印刷系统，能够将文字直接压印在纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
      "is_correct": true
    },
    {
      "text": "工人把压印在木板上图案。",
      "is_correct": false,
      "error_description": "“把”字句中，宾语（图案）必须紧跟在“把”之后，动词（压印）之前。原句语序错误。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "工人把圖案壓印在木板上。",
        "is_correct": true
      },
      {
        "text": "他正在壓印一張漂亮的賀卡。",
        "is_correct": true
      },
      {
        "text": "他所改良的金屬活字印刷系統，能夠將文字直接壓印在紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
        "is_correct": true
      },
      {
        "text": "工人把壓印在木板上圖案。",
        "is_correct": false,
        "error_description": "“把”字句中，賓語（圖案）必須緊跟在“把”之後，動詞（壓印）之前。原句語序錯誤。"
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
      "text": "我们压印了一些纪念章。",
      "is_correct": true
    },
    {
      "text": "同学们很喜欢压印这种手工。",
      "is_correct": true
    },
    {
      "text": "机器把花纹压印在皮革上。",
      "is_correct": true
    },
    {
      "text": "他压印了一本漂亮的贺卡。",
      "is_correct": false,
      "error_description": "量词使用错误。'贺卡'是扁平的纸质物品，应该使用量词'张'，而不是用于书本等装订成册物品的'本'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們壓印了一些紀念章。",
        "is_correct": true
      },
      {
        "text": "同學們很喜歡壓印這種手工。",
        "is_correct": true
      },
      {
        "text": "機器把花紋壓印在皮革上。",
        "is_correct": true
      },
      {
        "text": "他壓印了一本漂亮的賀卡。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。'賀卡'是扁平的紙質物品，應該使用量詞'張'，而不是用於書本等裝訂成冊物品的'本'。"
      }
    ]
  }
}
```

---

## sense 10156, level 6

#### Pack A
### Level 6 (sense 10156, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "史无前例",
    "惊天动地",
    "闻所未闻",
    "屡见不鲜"
  ],
  "correct_answer": "屡见不鲜",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指以前从来没有发生过。",
      "explanation": "反义项：经常见到，并不新奇，与'以前从未发生过'相反"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "史無前例",
      "驚天動地",
      "聞所未聞",
      "屢見不鮮"
    ],
    "correct_answer": "屢見不鮮",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指以前從來沒有發生過。",
        "explanation": "反義項：經常見到，並不新奇，與'以前從未發生過'相反"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "绝无仅有",
    "史无前例",
    "司空见惯",
    "昙花一现"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指以前从来没有发生过。",
      "explanation": "反义项：指某事常见，不足为奇，与以前从未发生过构成反义"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "絕無僅有",
      "史無前例",
      "司空見慣",
      "曇花一現"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指以前從來沒有發生過。",
        "explanation": "反義項：指某事常見，不足為奇，與以前從未發生過構成反義"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10156, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了压力前所未有的。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更前所未有的对地球脆弱的水资源系统施加了压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的压力。",
      "is_correct": true
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加前所未有的了压力。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误。动态助词“了”应放在动词“施加”之后或句末，不能插入在定语“前所未有”和中心语“压力”之间，破坏了定中结构。 语序错误。“前所未有”作为定语修饰“压力”时，必须放在中心语“压力”之前。放在句末导致动宾结构“施加了压力”被割裂，语序混乱。 语序错误。“前所未有”是形容词，不能直接放在介词结构或动词前作状语。应改为副词性结构“前所未有地”，或将其作为定语修饰“压力”。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了壓力前所未有的。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更前所未有的對地球脆弱的水資源系統施加了壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的壓力。",
        "is_correct": true
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加前所未有的了壓力。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤。動態助詞“了”應放在動詞“施加”之後或句末，不能插入在定語“前所未有”和中心語“壓力”之間，破壞了定中結構。 語序錯誤。“前所未有”作為定語修飾“壓力”時，必須放在中心語“壓力”之前。放在句末導致動賓結構“施加了壓力”被割裂，語序混亂。 語序錯誤。“前所未有”是形容詞，不能直接放在介詞結構或動詞前作狀語。應改為副詞性結構“前所未有地”，或將其作為定語修飾“壓力”。",
    "target_word": "前所未有"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "昙花一现",
    "平淡无奇",
    "史无前例",
    "司空见惯"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从来没有发生过或出现过的。",
      "explanation": "反义项：指某事常见，不足为奇，与“前所未有”（以前从未有过）构成反义。"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "曇花一現",
      "平淡無奇",
      "史無前例",
      "司空見慣"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從來沒有發生過或出現過的。",
        "explanation": "反義項：指某事常見，不足為奇，與“前所未有”（以前從未有過）構成反義。"
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
      "text": "这次活动的规模是前所未有的。",
      "is_correct": true
    },
    {
      "text": "这次活动的规模前所未有起来。",
      "is_correct": false
    },
    {
      "text": "这次活动的规模是前所未有过了。",
      "is_correct": false
    },
    {
      "text": "前所未有的这次活动的规模让我们震惊。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：“前所未有”本身已包含完成和过去的语义（“未有”），再叠加体标“过”和“了”导致体标冗余且位置不当。 语序错误：“前所未有”作定语时应紧挨着被修饰的中心语“规模”，即“这次活动前所未有的规模”，当前语序破坏了定中结构的紧密性。 方向/结果补语误用：“起来”表示动作或状态的开始与向上发展，而“前所未有”表示一种已经存在的极致状态，两者在体貌和语义上冲突，不能搭配。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "這次活動的規模是前所未有的。",
        "is_correct": true
      },
      {
        "text": "這次活動的規模前所未有起來。",
        "is_correct": false
      },
      {
        "text": "這次活動的規模是前所未有過了。",
        "is_correct": false
      },
      {
        "text": "前所未有的這次活動的規模讓我們震驚。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：“前所未有”本身已包含完成和過去的語義（“未有”），再疊加體標“過”和“了”導致體標冗餘且位置不當。 語序錯誤：“前所未有”作定語時應緊挨著被修飾的中心語“規模”，即“這次活動前所未有的規模”，當前語序破壞了定中結構的緊密性。 方向/結果補語誤用：“起來”表示動作或狀態的開始與向上發展，而“前所未有”表示一種已經存在的極致狀態，兩者在體貌和語義上衝突，不能搭配。",
    "target_word": "前所未有"
  }
}
```

---

## sense 10156, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 10156, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他正经历着前所未有的困难。",
      "is_correct": true
    },
    {
      "text": "这种前所未有的现象，值得我们关注。",
      "is_correct": true
    },
    {
      "text": "他正经历着前所未有地困难。",
      "is_correct": false,
      "error_description": "结构助词误用。'前所未有'在此处作定语修饰名词'困难'，应使用定语标志'的'，而不能使用状语标志'地'。"
    },
    {
      "text": "前所未有的变化，让大家感到惊讶。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他正經歷著前所未有的困難。",
        "is_correct": true
      },
      {
        "text": "這種前所未有的現象，值得我們關注。",
        "is_correct": true
      },
      {
        "text": "他正經歷著前所未有地困難。",
        "is_correct": false,
        "error_description": "結構助詞誤用。'前所未有'在此處作定語修飾名詞'困難'，應使用定語標誌'的'，而不能使用狀語標誌'地'。"
      },
      {
        "text": "前所未有的變化，讓大家感到驚訝。",
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
  "ipa": "[ʈʂʰɑŋ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "厂",
    "昌",
    "长",
    "唱"
  ],
  "correct_answer": "长",
  "explanation": "正确。读音为 cháng，表示空间或时间上的距离大。",
  "distractor_explanations": {
    "厂": "错误。读音为 chǎng，第三声，通常指工厂或开阔的场地，与目标词声调不同。",
    "唱": "错误。读音为 chàng，第四声，意为发声唱歌，与目标词声调不同。",
    "昌": "错误。读音为 chāng，第一声，意为兴盛或美好，与目标词声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[ʈʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "廠",
      "昌",
      "長",
      "唱"
    ],
    "correct_answer": "長",
    "explanation": "正確。讀音為 cháng，表示空間或時間上的距離大。",
    "distractor_explanations": {
      "厂": "錯誤。讀音為 chǎng，第三聲，通常指工廠或開闊的場地，與目標詞聲調不同。",
      "唱": "錯誤。讀音為 chàng，第四聲，意為發聲唱歌，與目標詞聲調不同。",
      "昌": "錯誤。讀音為 chāng，第一聲，意為興盛或美好，與目標詞聲調不同。"
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
    "长",
    "高",
    "大"
  ],
  "explanation": "正确。填入“长”准确描述了长城在空间上延伸距离大的核心特征。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "___城在中國北方，它很長很長。",
    "original_sentence": "長城在中國北方，它很長很長。",
    "correct_answer": "長",
    "options": [
      "重",
      "長",
      "高",
      "大"
    ],
    "explanation": "正確。填入“長”準確描述了長城在空間上延伸距離大的核心特徵。",
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
