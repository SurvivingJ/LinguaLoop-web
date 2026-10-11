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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "真正他喜欢打篮球。",
      "is_correct": false,
      "error_description": "语序错误。副词“真正”不能放在主语前面，应该放在主语之后、谓语动词之前。"
    },
    {
      "text": "朋友聚会可能说“晚上七点”，但真正开始可能是八点甚至更晚。",
      "is_correct": true
    },
    {
      "text": "要真正实现可持续性，不仅依赖材料本身的创新，更需配套的分类回收基础设施、政策法规与公众认知协同演进。",
      "is_correct": true
    },
    {
      "text": "只有大家合作，才能真正解决塑料污染问题。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "真正他喜歡打籃球。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“真正”不能放在主語前面，應該放在主語之後、謂語動詞之前。"
      },
      {
        "text": "朋友聚會可能說“晚上七點”，但真正開始可能是八點甚至更晚。",
        "is_correct": true
      },
      {
        "text": "要真正實現可持續性，不僅依賴材料本身的創新，更需配套的分類回收基礎設施、政策法規與公眾認知協同演進。",
        "is_correct": true
      },
      {
        "text": "只有大家合作，才能真正解決塑膠汙染問題。",
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
      "text": "真正他喜欢打篮球。",
      "is_correct": false,
      "error_description": "语序错误。副词“真正”应放在主语之后、谓语动词之前，不能放在主语之前。"
    },
    {
      "text": "我真正去过那个地方。",
      "is_correct": true
    },
    {
      "text": "他真正喜欢打篮球。",
      "is_correct": true
    },
    {
      "text": "大家正真正享受着假期。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "真正他喜歡打籃球。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“真正”應放在主語之後、謂語動詞之前，不能放在主語之前。"
      },
      {
        "text": "我真正去過那個地方。",
        "is_correct": true
      },
      {
        "text": "他真正喜歡打籃球。",
        "is_correct": true
      },
      {
        "text": "大家正真正享受著假期。",
        "is_correct": true
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
      "text": "冬天这个地区的总是下着大雪。",
      "is_correct": false
    },
    {
      "text": "这个地区们的冬天总是下着大雪。",
      "is_correct": false
    },
    {
      "text": "这个地区的冬天总是下着大雪。",
      "is_correct": true
    },
    {
      "text": "这个地区了冬天总是下着大雪。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“地区”是表示范围的名词，不能用复数后缀“们”来修饰。 体标位置错误：动态助词“了”不能直接加在表示空间范围的名词“地区”后面。 语序错误：时间状语“冬天”应放在句首或主语之后，且“的”字结构破坏了“这个地区的冬天”这一主语的整体性。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "冬天這個地區的總是下著大雪。",
        "is_correct": false
      },
      {
        "text": "這個地區們的冬天總是下著大雪。",
        "is_correct": false
      },
      {
        "text": "這個地區的冬天總是下著大雪。",
        "is_correct": true
      },
      {
        "text": "這個地區了冬天總是下著大雪。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“地區”是表示範圍的名詞，不能用複數字尾“們”來修飾。 體標位置錯誤：動態助詞“了”不能直接加在表示空間範圍的名詞“地區”後面。 語序錯誤：時間狀語“冬天”應放在句首或主語之後，且“的”字結構破壞了“這個地區的冬天”這一主語的整體性。",
    "target_word": "地區"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那个地区们的发展速度让人惊讶。",
      "is_correct": false
    },
    {
      "text": "发展速度那个地区的让人惊讶。",
      "is_correct": false
    },
    {
      "text": "那个地区着了的发展速度让人惊讶。",
      "is_correct": false
    },
    {
      "text": "那个地区的发展速度让人惊讶。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误：'地区'是表示地理范围的具体名词，不能加表示人的复数后缀'们'。 体标位置/选用错误：'着'表示动作进行或状态持续，不能用在名词'地区'之后，且不符合表达发展速度的语境。 语序错误：定语'那个地区'应该放在中心语'发展速度'之前，原句语序错乱导致结构破坏。",
  "target_word": "地区",
  "hant": {
    "sentences": [
      {
        "text": "那個地區們的發展速度讓人驚訝。",
        "is_correct": false
      },
      {
        "text": "發展速度那個地區的讓人驚訝。",
        "is_correct": false
      },
      {
        "text": "那個地區著了的發展速度讓人驚訝。",
        "is_correct": false
      },
      {
        "text": "那個地區的發展速度讓人驚訝。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤：'地區'是表示地理範圍的具體名詞，不能加表示人的複數字尾'們'。 體標位置/選用錯誤：'著'表示動作進行或狀態持續，不能用在名詞'地區'之後，且不符合表達發展速度的語境。 語序錯誤：定語'那個地區'應該放在中心語'發展速度'之前，原句語序錯亂導致結構破壞。",
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
      "text": "这种记谱法被很多作曲家使用，也传到了其他地区。",
      "is_correct": true
    },
    {
      "text": "我们把这个地区的风景都拍下来了。",
      "is_correct": true
    },
    {
      "text": "在一些干旱的地区，人们很早就学会了如何节约用水。",
      "is_correct": true
    },
    {
      "text": "他曾经去过那座偏远的地区旅游。",
      "is_correct": false,
      "error_description": "量词使用错误。'地区'表示一定的空间或区域，不能用'座'（通常用于山、城市或大型建筑）来修饰，应使用量词'个'或'片'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種記譜法被很多作曲家使用，也傳到了其他地區。",
        "is_correct": true
      },
      {
        "text": "我們把這個地區的風景都拍下來了。",
        "is_correct": true
      },
      {
        "text": "在一些乾旱的地區，人們很早就學會了如何節約用水。",
        "is_correct": true
      },
      {
        "text": "他曾經去過那座偏遠的地區旅遊。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。'地區'表示一定的空間或區域，不能用'座'（通常用於山、城市或大型建築）來修飾，應使用量詞'個'或'片'。"
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
      "text": "那个地区的发展速度让人惊讶。",
      "is_correct": true
    },
    {
      "text": "那个地区的人们一直保持着热情。",
      "is_correct": true
    },
    {
      "text": "我在这个地区交到了很多好朋友。",
      "is_correct": true
    },
    {
      "text": "我交到了很多好朋友在这个地区。",
      "is_correct": false,
      "error_description": "语序错误。表示地点的状语“在这个地区”应该放在动词“交到”之前，而不是句末。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "那個地區的發展速度讓人驚訝。",
        "is_correct": true
      },
      {
        "text": "那個地區的人們一直保持著熱情。",
        "is_correct": true
      },
      {
        "text": "我在這個地區交到了很多好朋友。",
        "is_correct": true
      },
      {
        "text": "我交到了很多好朋友在這個地區。",
        "is_correct": false,
        "error_description": "語序錯誤。表示地點的狀語“在這個地區”應該放在動詞“交到”之前，而不是句末。"
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
  "sentence_with_blank": "他所改良的金属活字印刷系统，利用金属字模___纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "original_sentence": "他所改良的金属活字印刷系统，利用金属字模压印纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
  "correct_answer": "压印",
  "options": [
    "雕刻",
    "绘制",
    "复印",
    "压印"
  ],
  "explanation": "正确。“压印”指通过压力使物体表面留下图案，符合金属活字印刷的语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "他所改良的金屬活字印刷系統，利用金屬字模___紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "original_sentence": "他所改良的金屬活字印刷系統，利用金屬字模壓印紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
    "correct_answer": "壓印",
    "options": [
      "雕刻",
      "繪製",
      "影印",
      "壓印"
    ],
    "explanation": "正確。“壓印”指通過壓力使物體表面留下圖案，符合金屬活字印刷的語境。",
    "distractor_tags": {},
    "word_definition": "通過施加壓力使物體表面留下痕跡或圖案。",
    "target_word": "壓印"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "手工___需要很大的力气。",
  "original_sentence": "手工压印需要很大的力气。",
  "correct_answer": "压印",
  "options": [
    "抚摸",
    "描绘",
    "雕刻",
    "压印"
  ],
  "explanation": "正确。'压印'指通过压力留下痕迹，符合手工操作需要力气的语境。",
  "distractor_tags": {},
  "word_definition": "通过施加压力使物体表面留下痕迹或图案。",
  "target_word": "压印",
  "hant": {
    "sentence_with_blank": "手工___需要很大的力氣。",
    "original_sentence": "手工壓印需要很大的力氣。",
    "correct_answer": "壓印",
    "options": [
      "撫摸",
      "描繪",
      "雕刻",
      "壓印"
    ],
    "explanation": "正確。'壓印'指通過壓力留下痕跡，符合手工操作需要力氣的語境。",
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这张卡片压印着过美丽的花纹。",
      "is_correct": false
    },
    {
      "text": "这张卡片压印出来美丽的花纹。",
      "is_correct": false
    },
    {
      "text": "美丽的花纹这张卡片压印过。",
      "is_correct": false
    },
    {
      "text": "这张卡片压印过美丽的花纹。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：“着”表示状态持续，“过”表示经历，两者不能连用在动词后，应删去“着”或“过”。 语序错误：将宾语“美丽的花纹”提前至句首作主题，破坏了正常的“主语+谓语+宾语”结构，导致句子不自然。 结果补语误用：“出来”强调从无到有的产生，而“压印”本身已包含使图案显现的结果，此处使用“了”或直接接宾语更自然。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "這張卡片壓印著過美麗的花紋。",
        "is_correct": false
      },
      {
        "text": "這張卡片壓印出來美麗的花紋。",
        "is_correct": false
      },
      {
        "text": "美麗的花紋這張卡片壓印過。",
        "is_correct": false
      },
      {
        "text": "這張卡片壓印過美麗的花紋。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：“著”表示狀態持續，“過”表示經歷，兩者不能連用在動詞後，應刪去“著”或“過”。 語序錯誤：將賓語“美麗的花紋”提前至句首作主題，破壞了正常的“主語+謂語+賓語”結構，導致句子不自然。 結果補語誤用：“出來”強調從無到有的產生，而“壓印”本身已包含使圖案顯現的結果，此處使用“了”或直接接賓語更自然。",
    "target_word": "壓印"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "压印",
  "relation": "antonym",
  "options": [
    "压制",
    "抹平",
    "拓印",
    "雕刻"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义：压印是施加压力留下痕迹，抹平是使痕迹消失恢复平整"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "壓制",
      "抹平",
      "拓印",
      "雕刻"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義：壓印是施加壓力留下痕跡，抹平是使痕跡消失恢復平整"
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
      "text": "机器很快压印着速度。",
      "is_correct": false
    },
    {
      "text": "机器压印了速度很快。",
      "is_correct": false
    },
    {
      "text": "机器压印的速度很快。",
      "is_correct": true
    },
    {
      "text": "机器压印得很快速度。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：'速度很快'是主谓短语作谓语，前面不应加动态助词'了'，应改为'机器压印的速度很快'。 语序错误：'速度'是名词，不能放在补语'很快'之后作宾语，应直接说'机器压印的速度很快'。 体标选用错误：'着'表示动作持续，而'速度很快'描述的是属性或状态，两者搭配不当，应去掉'着'。",
  "target_word": "压印",
  "hant": {
    "sentences": [
      {
        "text": "機器很快壓印著速度。",
        "is_correct": false
      },
      {
        "text": "機器壓印了速度很快。",
        "is_correct": false
      },
      {
        "text": "機器壓印的速度很快。",
        "is_correct": true
      },
      {
        "text": "機器壓印得很快速度。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：'速度很快'是主謂短語作謂語，前面不應加動態助詞'了'，應改為'機器壓印的速度很快'。 語序錯誤：'速度'是名詞，不能放在補語'很快'之後作賓語，應直接說'機器壓印的速度很快'。 體標選用錯誤：'著'表示動作持續，而'速度很快'描述的是屬性或狀態，兩者搭配不當，應去掉'著'。",
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
    "抹平",
    "雕刻",
    "压制",
    "印刷"
  ],
  "correct_answer": "抹平",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "通过施加压力使物体表面留下痕迹或图案。",
      "explanation": "反义：压印是施压使表面留下痕迹，抹平是使表面痕迹消失变平滑"
    }
  },
  "hant": {
    "word": "壓印",
    "relation": "antonym",
    "options": [
      "抹平",
      "雕刻",
      "壓制",
      "印刷"
    ],
    "correct_answer": "抹平",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "通過施加壓力使物體表面留下痕跡或圖案。",
        "explanation": "反義：壓印是施壓使表面留下痕跡，抹平是使表面痕跡消失變平滑"
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
      "text": "他把树叶压印在画纸上。",
      "is_correct": true
    },
    {
      "text": "工人们正在压印精美的图案。",
      "is_correct": true
    },
    {
      "text": "他所改良的金属活字印刷系统，利用金属字模压印纸张表面，结合油性墨水与精确铸造技术，实现了文字复制的标准化与高效率生产。",
      "is_correct": true
    },
    {
      "text": "他把树叶压印了画纸上。",
      "is_correct": false,
      "error_description": "“把”字句中，动词“压印”后接地点宾语时，必须使用介词“在”来引出地点，不能省略“在”直接加地点名词。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把樹葉壓印在畫紙上。",
        "is_correct": true
      },
      {
        "text": "工人們正在壓印精美的圖案。",
        "is_correct": true
      },
      {
        "text": "他所改良的金屬活字印刷系統，利用金屬字模壓印紙張表面，結合油性墨水與精確鑄造技術，實現了文字複製的標準化與高效率生產。",
        "is_correct": true
      },
      {
        "text": "他把樹葉壓印了畫紙上。",
        "is_correct": false,
        "error_description": "“把”字句中，動詞“壓印”後接地點賓語時，必須使用介詞“在”來引出地點，不能省略“在”直接加地點名詞。"
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
      "text": "他正在压印了美丽的图案。",
      "is_correct": false,
      "error_description": "“正在”表示动作正在进行，不能与表示动作完成的体标“了”同时使用。应删去“了”，或将“正在”改为“已经”。"
    },
    {
      "text": "机器压印的速度很快。",
      "is_correct": true
    },
    {
      "text": "手工压印需要很大的力气。",
      "is_correct": true
    },
    {
      "text": "我们学会了如何压印。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他正在壓印了美麗的圖案。",
        "is_correct": false,
        "error_description": "“正在”表示動作正在進行，不能與表示動作完成的體標“了”同時使用。應刪去“了”，或將“正在”改為“已經”。"
      },
      {
        "text": "機器壓印的速度很快。",
        "is_correct": true
      },
      {
        "text": "手工壓印需要很大的力氣。",
        "is_correct": true
      },
      {
        "text": "我們學會了如何壓印。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10156, level 6

#### Pack A
### Level 6 (sense 10156, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的着压力。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了压力前所未有的。",
      "is_correct": false
    },
    {
      "text": "在当代全球化经济图景中，快时尚产业的崛起不仅重塑了消费者的穿衣模式，更对地球脆弱的水资源系统施加了前所未有的压力。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误。'前所未有'是形容词，后面不能直接加动态助词'着'来表示动作的持续，应直接修饰名词'压力'。 语序错误。'前所未有'作为定语修饰'压力'时，应放在中心语之前，即'前所未有的压力'，放在句末破坏了定中结构。 搭配错误。'前所未有'修饰名词时，通常需要加上结构助词'的'来连接定语和中心语，即'前所未有的压力'，缺少'的'会导致语法不自然。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的著壓力。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了壓力前所未有的。",
        "is_correct": false
      },
      {
        "text": "在當代全球化經濟圖景中，快時尚產業的崛起不僅重塑了消費者的穿衣模式，更對地球脆弱的水資源系統施加了前所未有的壓力。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤。'前所未有'是形容詞，後面不能直接加動態助詞'著'來表示動作的持續，應直接修飾名詞'壓力'。 語序錯誤。'前所未有'作為定語修飾'壓力'時，應放在中心語之前，即'前所未有的壓力'，放在句末破壞了定中結構。 搭配錯誤。'前所未有'修飾名詞時，通常需要加上結構助詞'的'來連線定語和中心語，即'前所未有的壓力'，缺少'的'會導致語法不自然。",
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
    "史无前例",
    "闻所未闻",
    "惊天动地",
    "司空见惯"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从未出现过或发生过。",
      "explanation": "反义：指某事常见、不足为奇，与「从未出现过」构成反义"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "史無前例",
      "聞所未聞",
      "驚天動地",
      "司空見慣"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從未出現過或發生過。",
        "explanation": "反義：指某事常見、不足為奇，與「從未出現過」構成反義"
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
      "text": "此次经历让我前所未有的感受到了震撼。",
      "is_correct": false
    },
    {
      "text": "此次经历让我感受到了前所未有过的震撼。",
      "is_correct": false
    },
    {
      "text": "此次经历让我感受到了震撼的前所未有。",
      "is_correct": false
    },
    {
      "text": "此次经历让我感受到了前所未有的震撼。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误。'前所未有'本身已包含'未'（没有）的否定与完成意味，后面不能再加动态助词'过'，造成体标记冗余和冲突。 语序错误。'前所未有'是形容词，在句中应作定语修饰名词'震撼'，不能放在动词'感受'前作状语。 语序错误。将形容词'前所未有'置于中心语'震撼'之后作后置定语，不符合现代汉语常规的'定语+的+中心语'语序规则。",
  "target_word": "前所未有",
  "hant": {
    "sentences": [
      {
        "text": "此次經歷讓我前所未有的感受到了震撼。",
        "is_correct": false
      },
      {
        "text": "此次經歷讓我感受到了前所未有過的震撼。",
        "is_correct": false
      },
      {
        "text": "此次經歷讓我感受到了震撼的前所未有。",
        "is_correct": false
      },
      {
        "text": "此次經歷讓我感受到了前所未有的震撼。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤。'前所未有'本身已包含'未'（沒有）的否定與完成意味，後面不能再加動態助詞'過'，造成體標記冗餘和衝突。 語序錯誤。'前所未有'是形容詞，在句中應作定語修飾名詞'震撼'，不能放在動詞'感受'前作狀語。 語序錯誤。將形容詞'前所未有'置於中心語'震撼'之後作後置定語，不符合現代漢語常規的'定語+的+中心語'語序規則。",
    "target_word": "前所未有"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "前所未有",
  "relation": "antonym",
  "options": [
    "昙花一现",
    "司空见惯",
    "闻所未闻",
    "史无前例"
  ],
  "correct_answer": "司空见惯",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指过去从未出现过或发生过。",
      "explanation": "反义项：指某事常见，与“从未出现过”构成反义"
    }
  },
  "hant": {
    "word": "前所未有",
    "relation": "antonym",
    "options": [
      "曇花一現",
      "司空見慣",
      "聞所未聞",
      "史無前例"
    ],
    "correct_answer": "司空見慣",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指過去從未出現過或發生過。",
        "explanation": "反義項：指某事常見，與“從未出現過”構成反義"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "随着出版物种类的丰富，除宗教文献外，科学论著、文学作品、法律文本乃至新闻小册子广泛流通，公众对知识的渴求被前所未有地激发。",
      "is_correct": true
    },
    {
      "text": "这一突破不仅大幅降低了书籍的制作成本，更使《圣经》等文本得以以前所未有的速度和数量被复制，从而打破了教会对知识解释权的垄断。",
      "is_correct": true
    },
    {
      "text": "面对全球变暖加剧、降水模式日益不稳定的现实，现代水资源管理正面临前所未有的挑战。",
      "is_correct": true
    },
    {
      "text": "面对前所未有的了挑战，我们必须保持高度的战略定力。",
      "is_correct": false,
      "error_description": "“前所未有”本身已包含“以前没有”的完整语义，直接修饰名词作定语即可，后面不能加动态助词“了”，属于体标误用。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "隨著出版物種類的豐富，除宗教文獻外，科學論著、文學作品、法律文本乃至新聞小冊子廣泛流通，公眾對知識的渴求被前所未有地激發。",
        "is_correct": true
      },
      {
        "text": "這一突破不僅大幅降低了書籍的製作成本，更使《聖經》等文本得以以前所未有的速度和數量被複制，從而打破了教會對知識解釋權的壟斷。",
        "is_correct": true
      },
      {
        "text": "面對全球變暖加劇、降水模式日益不穩定的現實，現代水資源管理正面臨前所未有的挑戰。",
        "is_correct": true
      },
      {
        "text": "面對前所未有的了挑戰，我們必須保持高度的戰略定力。",
        "is_correct": false,
        "error_description": "“前所未有”本身已包含“以前沒有”的完整語義，直接修飾名詞作定語即可，後面不能加動態助詞“了”，屬於體標誤用。"
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
      "text": "他把前所未有的热情给了大家。",
      "is_correct": true
    },
    {
      "text": "此次经历让我感受到了前所未有的震撼。",
      "is_correct": true
    },
    {
      "text": "我们正经历着前所未有的开心。",
      "is_correct": true
    },
    {
      "text": "他前所未有的把热情给了大家。",
      "is_correct": false,
      "error_description": "语序错误。形容词“前所未有”修饰名词“热情”时，应放在名词前面作定语，即“前所未有的热情”，而不是放在主语和“把”之间。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把前所未有的熱情給了大家。",
        "is_correct": true
      },
      {
        "text": "此次經歷讓我感受到了前所未有的震撼。",
        "is_correct": true
      },
      {
        "text": "我們正經歷著前所未有的開心。",
        "is_correct": true
      },
      {
        "text": "他前所未有的把熱情給了大家。",
        "is_correct": false,
        "error_description": "語序錯誤。形容詞“前所未有”修飾名詞“熱情”時，應放在名詞前面作定語，即“前所未有的熱情”，而不是放在主語和“把”之間。"
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
    "唱",
    "昌",
    "厂",
    "长"
  ],
  "correct_answer": "长",
  "explanation": "“长”读二声（cháng），表示空间或时间上的距离大。",
  "distractor_explanations": {
    "厂": "“厂”读三声（chǎng），指工厂或场地，与长度无关。",
    "唱": "“唱”读四声（chàng），表示歌唱，声调不同且意义完全不同。",
    "昌": "“昌”读一声（chāng），表示兴旺、美好，声调不同且意义不符。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "長",
    "pronunciation": "cháng",
    "ipa": "[ʈʂʰɑŋ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "唱",
      "昌",
      "廠",
      "長"
    ],
    "correct_answer": "長",
    "explanation": "“長”讀二聲（cháng），表示空間或時間上的距離大。",
    "distractor_explanations": {
      "厂": "“廠”讀三聲（chǎng），指工廠或場地，與長度無關。",
      "唱": "“唱”讀四聲（chàng），表示歌唱，聲調不同且意義完全不同。",
      "昌": "“昌”讀一聲（chāng），表示興旺、美好，聲調不同且意義不符。"
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
    "远"
  ],
  "explanation": "正确。“长”形容长城在空间上的距离大，符合语境。",
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
      "遠"
    ],
    "explanation": "正確。“長”形容長城在空間上的距離大，符合語境。",
    "distractor_tags": {},
    "word_definition": "指空間或時間上距離大，與‘短’相對。",
    "target_word": "長"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这个故事很___，我们下次再讲吧。",
  "original_sentence": "这个故事很长，我们下次再讲吧。",
  "correct_answer": "长",
  "options": [
    "长",
    "深",
    "宽",
    "多"
  ],
  "explanation": "正确。指故事篇幅大、讲述所需的时间久，符合语境。",
  "distractor_tags": {},
  "word_definition": "指空间或时间上距离大，与‘短’相对。",
  "target_word": "长",
  "hant": {
    "sentence_with_blank": "這個故事很___，我們下次再講吧。",
    "original_sentence": "這個故事很長，我們下次再講吧。",
    "correct_answer": "長",
    "options": [
      "長",
      "深",
      "寬",
      "多"
    ],
    "explanation": "正確。指故事篇幅大、講述所需的時間久，符合語境。",
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
