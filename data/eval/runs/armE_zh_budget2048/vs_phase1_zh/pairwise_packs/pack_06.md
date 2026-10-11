# Pairwise review pack 06

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
    "亲自",
    "愈发",
    "互相",
    "偶尔"
  ],
  "explanation": "正确。'愈发'表示程度在原有基础上进一步加深，符合句中消费者关注度提升的语境。",
  "distractor_tags": {},
  "word_definition": "副词。表示程度在原有基础上进一步加深，相当于‘更加’。",
  "target_word": "愈发",
  "hant": {
    "sentence_with_blank": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者___關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "original_sentence": "一方面，大眾零售市場依賴規模化生產的速溶咖啡與連鎖咖啡店標準化產品；另一方面，精品咖啡運動的興起推動了“從種子到杯子”的溯源理念，消費者愈發關注產地故事、處理工藝與風味譜系，進而反向影響原產地的種植實踐與分級標準。",
    "correct_answer": "愈發",
    "options": [
      "親自",
      "愈發",
      "互相",
      "偶爾"
    ],
    "explanation": "正確。'愈發'表示程度在原有基礎上進一步加深，符合句中消費者關注度提升的語境。",
    "distractor_tags": {},
    "word_definition": "副詞。表示程度在原有基礎上進一步加深，相當於‘更加’。",
    "target_word": "愈發"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "弟弟___懂事了，不再乱发脾气。",
  "original_sentence": "弟弟愈发懂事了，不再乱发脾气。",
  "correct_answer": "愈发",
  "options": [
    "稍微",
    "互相",
    "愈发",
    "必定"
  ],
  "explanation": "正确。“愈发”表示程度进一步加深，符合弟弟变得“更加”懂事的语境。",
  "distractor_tags": {},
  "word_definition": "副词。表示程度在原有基础上进一步加深，相当于‘更加’。",
  "target_word": "愈发",
  "hant": {
    "sentence_with_blank": "弟弟___懂事了，不再亂髮脾氣。",
    "original_sentence": "弟弟愈發懂事了，不再亂髮脾氣。",
    "correct_answer": "愈發",
    "options": [
      "稍微",
      "互相",
      "愈發",
      "必定"
    ],
    "explanation": "正確。“愈發”表示程度進一步加深，符合弟弟變得“更加”懂事的語境。",
    "distractor_tags": {},
    "word_definition": "副詞。表示程度在原有基礎上進一步加深，相當於‘更加’。",
    "target_word": "愈發"
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
      "text": "听着这首歌，我愈发想念家乡了。",
      "is_correct": true
    },
    {
      "text": "他愈发把注意力放在学习上了。",
      "is_correct": true
    },
    {
      "text": "他把愈发注意力放在学习上了。",
      "is_correct": false,
      "error_description": "“愈发”是程度副词，应放在“把”字句的“把”字之前作状语，不能放在“把”和宾语之间。"
    },
    {
      "text": "一方面，大众零售市场依赖规模化生产的速溶咖啡与连锁咖啡店标准化产品；另一方面，精品咖啡运动的兴起推动了“从种子到杯子”的溯源理念，消费者愈发关注产地故事、处理工艺与风味谱系，进而反向影响原产地的种植实践与分级标准。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "聽著這首歌，我愈發想念家鄉了。",
        "is_correct": true
      },
      {
        "text": "他愈發把注意力放在學習上了。",
        "is_correct": true
      },
      {
        "text": "他把愈發注意力放在學習上了。",
        "is_correct": false,
        "error_description": "“愈發”是程度副詞，應放在“把”字句的“把”字之前作狀語，不能放在“把”和賓語之間。"
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
      "text": "他愈发把心思放在画画上了。",
      "is_correct": true
    },
    {
      "text": "雨愈发大了，我们赶紧回家吧。",
      "is_correct": true
    },
    {
      "text": "弟弟愈发懂事了，不再乱发脾气。",
      "is_correct": true
    },
    {
      "text": "他把愈发心思放在画画上了。",
      "is_correct": false,
      "error_description": "“愈发”是副词，应放在“把”字前修饰整个动词短语，不能放在“把”字后修饰名词“心思”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他愈發把心思放在畫畫上了。",
        "is_correct": true
      },
      {
        "text": "雨愈發大了，我們趕緊回家吧。",
        "is_correct": true
      },
      {
        "text": "弟弟愈發懂事了，不再亂髮脾氣。",
        "is_correct": true
      },
      {
        "text": "他把愈發心思放在畫畫上了。",
        "is_correct": false,
        "error_description": "“愈發”是副詞，應放在“把”字前修飾整個動詞短語，不能放在“把”字後修飾名詞“心思”。"
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

---

## sense 10553, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 10553, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "错误频发让他很伤心。",
      "is_correct": true
    },
    {
      "text": "让他很伤心错误频发。",
      "is_correct": false
    },
    {
      "text": "错误频发了让他很伤心。",
      "is_correct": false
    },
    {
      "text": "频发错误让他很伤心。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。“频发”表示一种持续或反复的状态，通常不加动态助词“了”，加“了”会破坏状态动词的自然体貌。 语序错误。“频发”是不及物状态动词，主语应为发生的事物（错误），不能带宾语，此处错误地将“错误”放在了宾语位置。 语序错误。因果复句中，原因分句“错误频发”应放在结果分句“让他很伤心”之前，当前语序破坏了正常的逻辑与主题评论结构。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "錯誤頻發讓他很傷心。",
        "is_correct": true
      },
      {
        "text": "讓他很傷心錯誤頻發。",
        "is_correct": false
      },
      {
        "text": "錯誤頻發了讓他很傷心。",
        "is_correct": false
      },
      {
        "text": "頻發錯誤讓他很傷心。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。“頻發”表示一種持續或反覆的狀態，通常不加動態助詞“了”，加“了”會破壞狀態動詞的自然體貌。 語序錯誤。“頻發”是不及物狀態動詞，主語應為發生的事物（錯誤），不能帶賓語，此處錯誤地將“錯誤”放在了賓語位置。 語序錯誤。因果複句中，原因分句“錯誤頻發”應放在結果分句“讓他很傷心”之前，當前語序破壞了正常的邏輯與主題評論結構。",
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
    "易发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短的时间内多次发生。",
      "explanation": "反义：频发指短时间内多次发生，偶发指偶尔发生，二者在发生频率上构成反义"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "突發",
      "併發",
      "偶發",
      "易發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短的時間內多次發生。",
        "explanation": "反義：頻髮指短時間內多次發生，偶發指偶爾發生，二者在發生頻率上構成反義"
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
      "text": "小错误频发着，说明你没用过心。",
      "is_correct": false
    },
    {
      "text": "频发小错误，说明你没用过心。",
      "is_correct": false
    },
    {
      "text": "小错误频发起来，说明你没用过心。",
      "is_correct": false
    },
    {
      "text": "小错误频发，说明你没用过心。",
      "is_correct": true
    }
  ],
  "explanation": "体标选用错误：'频发'表示多次发生的状态，不能加表示动作持续的动态助词'着'。 语序错误：'频发'在此处作谓语，主语'小错误'应置于谓语之前，构成'主语+谓语'的主谓结构。 结果补语误用：'起来'表示动作开始，但'频发'本身已包含反复多次的意义，两者连用导致语义重复且搭配不当。",
  "target_word": "频发",
  "hant": {
    "sentences": [
      {
        "text": "小錯誤頻發著，說明你沒用過心。",
        "is_correct": false
      },
      {
        "text": "頻發小錯誤，說明你沒用過心。",
        "is_correct": false
      },
      {
        "text": "小錯誤頻發起來，說明你沒用過心。",
        "is_correct": false
      },
      {
        "text": "小錯誤頻發，說明你沒用過心。",
        "is_correct": true
      }
    ],
    "explanation": "體標選用錯誤：'頻發'表示多次發生的狀態，不能加表示動作持續的動態助詞'著'。 語序錯誤：'頻發'在此處作謂語，主語'小錯誤'應置於謂語之前，構成'主語+謂語'的主謂結構。 結果補語誤用：'起來'表示動作開始，但'頻發'本身已包含反覆多次的意義，兩者連用導致語義重複且搭配不當。",
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
    "并发",
    "偶发"
  ],
  "correct_answer": "偶发",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指在较短的时间内多次发生。",
      "explanation": "反义项：指偶尔发生，与频发在发生频率上构成反义"
    }
  },
  "hant": {
    "word": "頻發",
    "relation": "antonym",
    "options": [
      "突發",
      "發生",
      "併發",
      "偶發"
    ],
    "correct_answer": "偶發",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指在較短的時間內多次發生。",
        "explanation": "反義項：指偶爾發生，與頻發在發生頻率上構成反義"
      }
    }
  }
}
```

---

## sense 10553, level 7

#### Pack A
### Level 7 (sense 10553, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "气候变化导致适宜种植区收缩，极端天气频发影响产量稳定性；全球航运成本波动、地缘政治紧张以及关税政策调整均可能扰乱贸易流向；同时，小农户在面对市场风险时普遍缺乏金融工具与信息支持。",
      "is_correct": true
    },
    {
      "text": "当极端气候频发导致主粮产区波动时，分布式的城市食品生产网络展现出显著的风险对冲能力，使地方政府将此类项目纳入关键基础设施的应急规划范畴。",
      "is_correct": true
    },
    {
      "text": "在某些干旱频发的地区，纺织工业甚至成为加剧水资源短缺的关键因素，挤占了农业、饮用水与生态系统所需的水量。",
      "is_correct": true
    },
    {
      "text": "频发极端天气影响了农作物的产量。",
      "is_correct": false,
      "error_description": "语序错误。“频发”的主语是发生的事件，应将“极端天气”放在“频发”前面作主语。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "氣候變化導致適宜種植區收縮，極端天氣頻發影響產量穩定性；全球航運成本波動、地緣政治緊張以及關稅政策調整均可能擾亂貿易流向；同時，小農戶在面對市場風險時普遍缺乏金融工具與資訊支援。",
        "is_correct": true
      },
      {
        "text": "當極端氣候頻發導致主糧產區波動時，分散式的城市食品生產網路展現出顯著的風險對沖能力，使地方政府將此類專案納入關鍵基礎設施的應急規劃範疇。",
        "is_correct": true
      },
      {
        "text": "在某些乾旱頻發的地區，紡織工業甚至成為加劇水資源短缺的關鍵因素，擠佔了農業、飲用水與生態系統所需的水量。",
        "is_correct": true
      },
      {
        "text": "頻發極端天氣影響了農作物的產量。",
        "is_correct": false,
        "error_description": "語序錯誤。“頻發”的主語是發生的事件，應將“極端天氣”放在“頻發”前面作主語。"
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
      "text": "小错误频发，说明你没用过心。",
      "is_correct": true
    },
    {
      "text": "最近误会频发，我们得聊聊。",
      "is_correct": true
    },
    {
      "text": "最近误会频发了，我们得聊聊。",
      "is_correct": false,
      "error_description": "“频发”表示频繁发生的状态，通常不与表示动作完成的动态助词“了”连用，应去掉“了”。"
    },
    {
      "text": "争吵频发，感情变淡了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "小錯誤頻發，說明你沒用過心。",
        "is_correct": true
      },
      {
        "text": "最近誤會頻發，我們得聊聊。",
        "is_correct": true
      },
      {
        "text": "最近誤會頻發了，我們得聊聊。",
        "is_correct": false,
        "error_description": "“頻發”表示頻繁發生的狀態，通常不與表示動作完成的動態助詞“了”連用，應去掉“了”。"
      },
      {
        "text": "爭吵頻發，感情變淡了。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
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

---

## sense 10803, level 6

#### Pack A
### Level 6 (sense 10803, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "那些企业正将各项合规要求纳入着内部治理体系进行统筹管理。",
      "is_correct": false
    },
    {
      "text": "那些能将各项合规要求纳入内部治理体系进行统筹管理的企业，能够在高度规制的AI时代确立不可替代的制度性优势。",
      "is_correct": true
    },
    {
      "text": "那些企业将各项合规要求能纳入内部治理体系进行统筹管理。",
      "is_correct": false
    },
    {
      "text": "那些企业能将各项合规要求纳入起内部治理体系进行统筹管理。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：能愿动词“能”应放在介词“将”之前，即“能将”，原句将其置于“将”之后破坏了介词结构的完整性。 体标选用错误：“纳入”表示动作的完成与结果，不能与表示持续状态的动态助词“着”连用，应去掉“着”。 结果补语误用：“纳入”中的“入”已包含动作的结果与方向，不能再额外添加“起”等结果补语，造成语义重复与搭配不当。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "那些企業正將各項合規要求納入著內部治理體系進行統籌管理。",
        "is_correct": false
      },
      {
        "text": "那些能將各項合規要求納入內部治理體系進行統籌管理的企業，能夠在高度規制的AI時代確立不可替代的制度性優勢。",
        "is_correct": true
      },
      {
        "text": "那些企業將各項合規要求能納入內部治理體系進行統籌管理。",
        "is_correct": false
      },
      {
        "text": "那些企業能將各項合規要求納入起內部治理體系進行統籌管理。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：能願動詞“能”應放在介詞“將”之前，即“能將”，原句將其置於“將”之後破壞了介詞結構的完整性。 體標選用錯誤：“納入”表示動作的完成與結果，不能與表示持續狀態的動態助詞“著”連用，應去掉“著”。 結果補語誤用：“納入”中的“入”已包含動作的結果與方向，不能再額外新增“起”等結果補語，造成語義重複與搭配不當。",
    "target_word": "將"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我将你的建议纳入考虑范围。",
      "is_correct": true
    },
    {
      "text": "我将你的建议昨天纳入考虑范围。",
      "is_correct": false
    },
    {
      "text": "我将了你的建议纳入考虑范围。",
      "is_correct": false
    },
    {
      "text": "我将你的建议纳入出去考虑范围。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词'了'应放在动词'纳入'之后，即'将你的建议纳入了考虑范围'，不能放在介词'将'之后。 语序错误：时间状语'昨天'应放在介词'将'之前，即'我昨天将你的建议纳入考虑范围'，不能放在介词和宾语之间。 结果补语误用：'纳入'本身已包含'进入'的方向意义，添加表示向外方向的'出去'会导致语义矛盾且不符合语法。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "我將你的建議納入考慮範圍。",
        "is_correct": true
      },
      {
        "text": "我將你的建議昨天納入考慮範圍。",
        "is_correct": false
      },
      {
        "text": "我將了你的建議納入考慮範圍。",
        "is_correct": false
      },
      {
        "text": "我將你的建議納入出去考慮範圍。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'應放在動詞'納入'之後，即'將你的建議納入了考慮範圍'，不能放在介詞'將'之後。 語序錯誤：時間狀語'昨天'應放在介詞'將'之前，即'我昨天將你的建議納入考慮範圍'，不能放在介詞和賓語之間。 結果補語誤用：'納入'本身已包含'進入'的方向意義，新增表示向外方向的'出去'會導致語義矛盾且不符合語法。",
    "target_word": "將"
  }
}
```

#### Pack B
### Level 6 (sense 10803, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们将这些旧书整理好送给山区的孩子。",
      "is_correct": true
    },
    {
      "text": "我们将这些旧书整理送给山区的孩子。",
      "is_correct": false
    },
    {
      "text": "我们将整理好这些旧书送给山区的孩子。",
      "is_correct": false
    },
    {
      "text": "我们将了这些旧书整理好送给山区的孩子。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词'了'不能放在介词'将'之后，应放在主要动词后（如'整理好了'）或句末。 语序错误：'将'的宾语必须紧跟在介词之后，不能将宾语'这些旧书'错放到动词'整理好'之后。 体貌错误：在'将'字句中，主要动词不能是光杆动词，必须带有补语、动态助词或重叠等形式（如'整理好'）。",
  "target_word": "将",
  "hant": {
    "sentences": [
      {
        "text": "我們將這些舊書整理好送給山區的孩子。",
        "is_correct": true
      },
      {
        "text": "我們將這些舊書整理送給山區的孩子。",
        "is_correct": false
      },
      {
        "text": "我們將整理好這些舊書送給山區的孩子。",
        "is_correct": false
      },
      {
        "text": "我們將了這些舊書整理好送給山區的孩子。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'不能放在介詞'將'之後，應放在主要動詞後（如'整理好了'）或句末。 語序錯誤：'將'的賓語必須緊跟在介詞之後，不能將賓語'這些舊書'錯放到動詞'整理好'之後。 體貌錯誤：在'將'字句中，主要動詞不能是光桿動詞，必須帶有補語、動態助詞或重疊等形式（如'整理好'）。",
    "target_word": "將"
  }
}
```

---

## sense 10803, level 7

#### Pack A
### Level 7 (sense 10803, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "联合国环境规划署在1972年斯德哥尔摩人类环境会议后，将此类标准化符号纳入全球环境治理的技术建议之中。",
      "is_correct": true
    },
    {
      "text": "首先，训练数据的采集与使用需满足“知情—同意”框架的实质要求，这意味着企业不能仅依赖用户协议中的概括性条款，而应通过分层披露机制，将涉及个人敏感信息或生成式内容的数据纳入可验证的用户授权路径进行严格管理，清晰说明其用于模型训练的具体场景、类别及潜在影响。",
      "is_correct": true
    },
    {
      "text": "我将纳入管理系统这些资料。",
      "is_correct": false,
      "error_description": "语序错误。在“将”字句中，受事宾语必须放在“将”之后、动词之前，不能放在动词之后。"
    },
    {
      "text": "可以预见，未来立法将原料提取、产品设计至废弃物回收等各个环节纳入全生命周期管理体系，以形成闭环控制机制。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "聯合國環境規劃署在1972年斯德哥爾摩人類環境會議後，將此類標準化符號納入全球環境治理的技術建議之中。",
        "is_correct": true
      },
      {
        "text": "首先，訓練資料的採集與使用需滿足“知情—同意”框架的實質要求，這意味著企業不能僅依賴使用者協議中的概括性條款，而應通過分層披露機制，將涉及個人敏感資訊或生成式內容的資料納入可驗證的使用者授權路徑進行嚴格管理，清晰說明其用於模型訓練的具體場景、類別及潛在影響。",
        "is_correct": true
      },
      {
        "text": "我將納入管理系統這些資料。",
        "is_correct": false,
        "error_description": "語序錯誤。在“將”字句中，受事賓語必須放在“將”之後、動詞之前，不能放在動詞之後。"
      },
      {
        "text": "可以預見，未來立法將原料提取、產品設計至廢棄物回收等各個環節納入全生命週期管理體系，以形成閉環控制機制。",
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
      "text": "然而，技术革新若无消费观念的同步转变，相关部门需将新技术纳入现有的市场准入规则中进行规范管理，以确保产业平稳发展。",
      "is_correct": true
    },
    {
      "text": "我将你的建议纳入考虑范围。",
      "is_correct": true
    },
    {
      "text": "我将这些资料纳入管理系统。",
      "is_correct": true
    },
    {
      "text": "我将纳入管理系统这些资料。",
      "is_correct": false,
      "error_description": "“将”字句要求受事宾语紧跟在“将”之后、谓语动词之前。原句将宾语放在了动词之后，属于语序错误。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "然而，技術革新若無消費觀念的同步轉變，相關部門需將新技術納入現有的市場準入規則中進行規範管理，以確保產業平穩發展。",
        "is_correct": true
      },
      {
        "text": "我將你的建議納入考慮範圍。",
        "is_correct": true
      },
      {
        "text": "我將這些資料納入管理系統。",
        "is_correct": true
      },
      {
        "text": "我將納入管理系統這些資料。",
        "is_correct": false,
        "error_description": "“將”字句要求受事賓語緊跟在“將”之後、謂語動詞之前。原句將賓語放在了動詞之後，屬於語序錯誤。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10803, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "可以预见，未来立法将全生命周期管理纳入核心框架，涵盖从原料提取、产品设计到废弃物回收的各个环节，以形成闭环控制体系。",
      "is_correct": true
    },
    {
      "text": "班长将大家的意见没有收集起来。",
      "is_correct": false,
      "error_description": "语序错误。在“将”字句中，否定词（如“没有”“不”）必须放在介词“将”的前面，而不能放在“将”和动词之间。"
    },
    {
      "text": "联合国环境规划署在1972年斯德哥尔摩人类环境会议后，将此类标准化符号纳入全球环境治理的技术建议之中。",
      "is_correct": true
    },
    {
      "text": "首先，训练数据的采集与使用需满足“知情—同意”框架的实质要求，这意味着企业不能仅依赖用户协议中的概括性条款，而应通过分层披露机制，清晰说明将数据纳入模型训练系统的具体场景、类别及潜在影响，尤其在涉及个人敏感信息或生成式内容时，须实现可验证的用户授权路径。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "可以預見，未來立法將全生命週期管理納入核心框架，涵蓋從原料提取、產品設計到廢棄物回收的各個環節，以形成閉環控制體系。",
        "is_correct": true
      },
      {
        "text": "班長將大家的意見沒有收集起來。",
        "is_correct": false,
        "error_description": "語序錯誤。在“將”字句中，否定詞（如“沒有”“不”）必須放在介詞“將”的前面，而不能放在“將”和動詞之間。"
      },
      {
        "text": "聯合國環境規劃署在1972年斯德哥爾摩人類環境會議後，將此類標準化符號納入全球環境治理的技術建議之中。",
        "is_correct": true
      },
      {
        "text": "首先，訓練資料的採集與使用需滿足“知情—同意”框架的實質要求，這意味著企業不能僅依賴使用者協議中的概括性條款，而應通過分層披露機制，清晰說明將資料納入模型訓練系統的具體場景、類別及潛在影響，尤其在涉及個人敏感資訊或生成式內容時，須實現可驗證的使用者授權路徑。",
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
      "text": "然而，技术革新若无消费观念的同步转变，便难以将各项前沿成果纳入实际应用的轨道，最终只能举步维艰。",
      "is_correct": true
    },
    {
      "text": "我们将送给山区的孩子这些旧书整理好。",
      "is_correct": false,
      "error_description": "在“将”字句中，“将”的宾语必须紧跟在“将”字之后，不能将其他动词短语插在“将”和宾语之间。正确的语序应为“将+宾语+动词短语”。"
    },
    {
      "text": "老师将同学们的座位重新安排了一下。",
      "is_correct": true
    },
    {
      "text": "我们将这些旧书整理好送给山区的孩子。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "然而，技術革新若無消費觀念的同步轉變，便難以將各項前沿成果納入實際應用的軌道，最終只能舉步維艱。",
        "is_correct": true
      },
      {
        "text": "我們將送給山區的孩子這些舊書整理好。",
        "is_correct": false,
        "error_description": "在“將”字句中，“將”的賓語必須緊跟在“將”字之後，不能將其他動詞短語插在“將”和賓語之間。正確的語序應為“將+賓語+動詞短語”。"
      },
      {
        "text": "老師將同學們的座位重新安排了一下。",
        "is_correct": true
      },
      {
        "text": "我們將這些舊書整理好送給山區的孩子。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 11315, level 6

#### Pack A
### Level 6 (sense 11315, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们研究了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "我们研究拮抗剂起来。",
      "is_correct": false
    },
    {
      "text": "拮抗剂我们了研究。",
      "is_correct": false
    },
    {
      "text": "我们研究了一个拮抗剂。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'拮抗剂'作为专业医学名词，通常使用集合量词'种'或'类'，使用个体量词'个'不符合专业语体习惯。 语序错误。动态助词'了'应紧跟在动词'研究'之后，或者放在句末表示动作完成，放在主语和动词之间破坏了正常的句法结构。 体标位置错误。趋向补语'起来'表示动作的开始或继续，应紧跟在动词'研究'之后（研究起来），放在宾语'拮抗剂'之后导致语法结构错误。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "我們研究了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "我們研究拮抗劑起來。",
        "is_correct": false
      },
      {
        "text": "拮抗劑我們了研究。",
        "is_correct": false
      },
      {
        "text": "我們研究了一個拮抗劑。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'拮抗劑'作為專業醫學名詞，通常使用集合量詞'種'或'類'，使用個體量詞'個'不符合專業語體習慣。 語序錯誤。動態助詞'了'應緊跟在動詞'研究'之後，或者放在句末表示動作完成，放在主語和動詞之間破壞了正常的句法結構。 體標位置錯誤。趨向補語'起來'表示動作的開始或繼續，應緊跟在動詞'研究'之後（研究起來），放在賓語'拮抗劑'之後導致語法結構錯誤。",
    "target_word": "拮抗劑"
  }
}
```

#### Pack B
### Level 6 (sense 11315, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "需要密切观察副作用拮抗剂的。",
      "is_correct": false
    },
    {
      "text": "这种拮抗剂已经抑制着了毒素的影响。",
      "is_correct": false
    },
    {
      "text": "医生给病人开了一张拮抗剂。",
      "is_correct": false
    },
    {
      "text": "拮抗剂的副作用需要密切观察。",
      "is_correct": true
    }
  ],
  "explanation": "量词使用错误。'拮抗剂'作为药物种类或具体药剂，应使用'种'、'类'或'支'，不能使用用于纸张的'张'。 体标选用错误。'已经'表示动作完成，而'着'表示状态持续，两者在体貌上相互冲突，不能连用。 语序错误。定语'拮抗剂的'应该放在中心语'副作用'之前，正确的语序应为'拮抗剂的副作用'。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "需要密切觀察副作用拮抗劑的。",
        "is_correct": false
      },
      {
        "text": "這種拮抗劑已經抑制著了毒素的影響。",
        "is_correct": false
      },
      {
        "text": "醫生給病人開了一張拮抗劑。",
        "is_correct": false
      },
      {
        "text": "拮抗劑的副作用需要密切觀察。",
        "is_correct": true
      }
    ],
    "explanation": "量詞使用錯誤。'拮抗劑'作為藥物種類或具體藥劑，應使用'種'、'類'或'支'，不能使用用於紙張的'張'。 體標選用錯誤。'已經'表示動作完成，而'著'表示狀態持續，兩者在體貌上相互衝突，不能連用。 語序錯誤。定語'拮抗劑的'應該放在中心語'副作用'之前，正確的語序應為'拮抗劑的副作用'。",
    "target_word": "拮抗劑"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "医生为病人开了一项拮抗剂来缓解症状。",
      "is_correct": false
    },
    {
      "text": "该拮抗剂着实降低了毒素的影响。",
      "is_correct": true
    },
    {
      "text": "医生给病人拮抗剂昨天注射以阻断神经信号。",
      "is_correct": false
    },
    {
      "text": "护士把拮抗剂了注射到病人的静脉里。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“拮抗剂”作为具体药物或物质，应使用“种”、“支”或“瓶”等量词，而“项”通常用于修饰项目、任务等抽象事物。 体标位置错误：动态助词“了”应放在动词“注射”之后或句末，不能放在介词“把”的宾语和动词之间，导致语法结构破裂。 语序错误：时间状语“昨天”应放在主语“医生”之后或句首，不能放在间接宾语和动词之间，破坏了正常的句法语序。",
  "target_word": "拮抗剂",
  "hant": {
    "sentences": [
      {
        "text": "醫生為病人開了一項拮抗劑來緩解症狀。",
        "is_correct": false
      },
      {
        "text": "該拮抗劑著實降低了毒素的影響。",
        "is_correct": true
      },
      {
        "text": "醫生給病人拮抗劑昨天注射以阻斷神經訊號。",
        "is_correct": false
      },
      {
        "text": "護士把拮抗劑了注射到病人的靜脈裡。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“拮抗劑”作為具體藥物或物質，應使用“種”、“支”或“瓶”等量詞，而“項”通常用於修飾專案、任務等抽象事物。 體標位置錯誤：動態助詞“了”應放在動詞“注射”之後或句末，不能放在介詞“把”的賓語和動詞之間，導致語法結構破裂。 語序錯誤：時間狀語“昨天”應放在主語“醫生”之後或句首，不能放在間接賓語和動詞之間，破壞了正常的句法語序。",
    "target_word": "拮抗劑"
  }
}
```

---

## sense 11315, level 7

#### Pack A
### Level 7 (sense 11315, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这种拮抗剂能阻断神经信号。",
      "is_correct": true
    },
    {
      "text": "医生给病人注射了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "例如，多巴胺水平的升高可显著增加哈欠频率，而其拮抗剂则能抑制该行为。",
      "is_correct": true
    },
    {
      "text": "医生给病人注射了一个拮抗剂。",
      "is_correct": false,
      "error_description": "量词使用错误。“拮抗剂”是药物或化学物质，应使用“支”、“种”等量词，不能使用泛用量词“个”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種拮抗劑能阻斷神經訊號。",
        "is_correct": true
      },
      {
        "text": "醫生給病人注射了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "例如，多巴胺水平的升高可顯著增加哈欠頻率，而其拮抗劑則能抑制該行為。",
        "is_correct": true
      },
      {
        "text": "醫生給病人注射了一個拮抗劑。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“拮抗劑”是藥物或化學物質，應使用“支”、“種”等量詞，不能使用泛用量詞“個”。"
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
      "text": "研究人员发现了一件新型拮抗剂。",
      "is_correct": false,
      "error_description": "量词使用错误。‘拮抗剂’是药物或化学物质，表示种类时应用量词‘种’，表示具体包装时可用‘支’或‘瓶’，不能用用于衣物或普通事物的量词‘件’。"
    },
    {
      "text": "该拮抗剂着实降低了毒素的影响。",
      "is_correct": true
    },
    {
      "text": "这种拮抗剂的疗效非常显著。",
      "is_correct": true
    },
    {
      "text": "研究人员发现了一种新型拮抗剂。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "研究人員發現了一件新型拮抗劑。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。‘拮抗劑’是藥物或化學物質，表示種類時應用量詞‘種’，表示具體包裝時可用‘支’或‘瓶’，不能用用於衣物或普通事物的量詞‘件’。"
      },
      {
        "text": "該拮抗劑著實降低了毒素的影響。",
        "is_correct": true
      },
      {
        "text": "這種拮抗劑的療效非常顯著。",
        "is_correct": true
      },
      {
        "text": "研究人員發現了一種新型拮抗劑。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 11315, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "医生使用了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "医生使用了一只拮抗剂。",
      "is_correct": false,
      "error_description": "量词“只”通常用于动物或某些成对的事物，不能用于药物或化学物质。此处应使用“种”来修饰“拮抗剂”。"
    },
    {
      "text": "例如，多巴胺水平的升高可显著增加哈欠频率，而其拮抗剂则能抑制该行为。",
      "is_correct": true
    },
    {
      "text": "这种拮抗剂能缓解疼痛。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "醫生使用了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "醫生使用了一隻拮抗劑。",
        "is_correct": false,
        "error_description": "量詞“只”通常用於動物或某些成對的事物，不能用於藥物或化學物質。此處應使用“種”來修飾“拮抗劑”。"
      },
      {
        "text": "例如，多巴胺水平的升高可顯著增加哈欠頻率，而其拮抗劑則能抑制該行為。",
        "is_correct": true
      },
      {
        "text": "這種拮抗劑能緩解疼痛。",
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
      "text": "我们研究了这种拮抗剂。",
      "is_correct": true
    },
    {
      "text": "该拮抗剂临床效果很好。",
      "is_correct": true
    },
    {
      "text": "医生把使用了这种拮抗剂。",
      "is_correct": false,
      "error_description": "“把”字句结构错误。“把”字后面必须接名词性宾语，不能直接跟动词。此处应删去“把”字。"
    },
    {
      "text": "这种药是种拮抗剂。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們研究了這種拮抗劑。",
        "is_correct": true
      },
      {
        "text": "該拮抗劑臨床效果很好。",
        "is_correct": true
      },
      {
        "text": "醫生把使用了這種拮抗劑。",
        "is_correct": false,
        "error_description": "“把”字句結構錯誤。“把”字後面必須接名詞性賓語，不能直接跟動詞。此處應刪去“把”字。"
      },
      {
        "text": "這種藥是種拮抗劑。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 11319, level 3

#### Pack A
### Level 3 (sense 11319, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "更引人深思的是，某些___抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "original_sentence": "更引人深思的是，某些强效抗精神病药物因影响多巴胺通路，常以“病理性哈欠”作为副作用，每日可达数十次之多，这反而为研究其神经机制提供了临床窗口。",
  "correct_answer": "强效",
  "options": [
    "强固",
    "昂贵",
    "强效",
    "剧烈"
  ],
  "explanation": "正确。",
  "distractor_tags": {},
  "word_definition": "指药物或方法有很强的作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "更引人深思的是，某些___抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "original_sentence": "更引人深思的是，某些強效抗精神病藥物因影響多巴胺通路，常以“病理性哈欠”作為副作用，每日可達數十次之多，這反而為研究其神經機制提供了臨床視窗。",
    "correct_answer": "強效",
    "options": [
      "強固",
      "昂貴",
      "強效",
      "劇烈"
    ],
    "explanation": "正確。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法有很強的作用。",
    "target_word": "強效"
  }
}
```

#### Pack B
### Level 3 (sense 11319, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "药理实验证实该提取物具有___的抗炎活性。",
  "original_sentence": "药理实验证实该提取物具有强效的抗炎活性。",
  "correct_answer": "强效",
  "options": [
    "微弱",
    "昂贵",
    "迅速",
    "强效"
  ],
  "explanation": "正确。强效指具有非常强大的效力，与“抗炎活性”搭配恰当。",
  "distractor_tags": {},
  "word_definition": "指药物或方法等具有非常强大的效力或作用。",
  "target_word": "强效",
  "hant": {
    "sentence_with_blank": "藥理實驗證實該提取物具有___的抗炎活性。",
    "original_sentence": "藥理實驗證實該提取物具有強效的抗炎活性。",
    "correct_answer": "強效",
    "options": [
      "微弱",
      "昂貴",
      "迅速",
      "強效"
    ],
    "explanation": "正確。強效指具有非常強大的效力，與“抗炎活性”搭配恰當。",
    "distractor_tags": {},
    "word_definition": "指藥物或方法等具有非常強大的效力或作用。",
    "target_word": "強效"
  }
}
```

---

## sense 11319, level 6

#### Pack A
### Level 6 (sense 11319, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "该靶向药物具有强效的抗肿瘤活性。",
      "is_correct": true
    },
    {
      "text": "该靶向药物具有强效得抗肿瘤活性。",
      "is_correct": false
    },
    {
      "text": "强效的该靶向药物具有抗肿瘤活性。",
      "is_correct": false
    },
    {
      "text": "该靶向药物具有强效着抗肿瘤活性。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。'强效'是形容词，表示状态和属性，后面不能直接加动态助词'着'来表示动作的持续。 语序错误。定语'强效的'应紧跟在指示代词'该'之后，正确语序应为'该强效的靶向药物'。 结构助词误用。'强效'作为定语修饰名词'抗肿瘤活性'时，应使用'的'，而不能使用补语标记'得'。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "該靶向藥物具有強效的抗腫瘤活性。",
        "is_correct": true
      },
      {
        "text": "該靶向藥物具有強效得抗腫瘤活性。",
        "is_correct": false
      },
      {
        "text": "強效的該靶向藥物具有抗腫瘤活性。",
        "is_correct": false
      },
      {
        "text": "該靶向藥物具有強效著抗腫瘤活性。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。'強效'是形容詞，表示狀態和屬性，後面不能直接加動態助詞'著'來表示動作的持續。 語序錯誤。定語'強效的'應緊跟在指示代詞'該'之後，正確語序應為'該強效的靶向藥物'。 結構助詞誤用。'強效'作為定語修飾名詞'抗腫瘤活性'時，應使用'的'，而不能使用補語標記'得'。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "高效",
    "速效",
    "弱效",
    "长效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法等具有非常强大的效力或作用。",
      "explanation": "反义项：指药物或方法效力微弱，与"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "高效",
      "速效",
      "弱效",
      "長效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法等具有非常強大的效力或作用。",
        "explanation": "反義項：指藥物或方法效力微弱，與"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "缓效",
    "长效",
    "弱效",
    "速效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法等具有非常强大的效力或作用。",
      "explanation": "指药物或方法效力微弱，与目标词在效力强度上构成反义关系。"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "緩效",
      "長效",
      "弱效",
      "速效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法等具有非常強大的效力或作用。",
        "explanation": "指藥物或方法效力微弱，與目標詞在效力強度上構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 11319, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "不需要这么强效治病。",
      "is_correct": false
    },
    {
      "text": "这药强效下去了。",
      "is_correct": false
    },
    {
      "text": "治病不需要这么强效。",
      "is_correct": true
    },
    {
      "text": "这种感冒药正强效着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“强效”为性质形容词，表示药物作用强的固有属性，不能加动态助词“着”表示状态的持续进行。 语序错误。“这么强效”在句中应作谓语或补语，说明治疗的程度或方法，不能直接放在动词“治病”前作状语。 方向/结果补语误用。“强效”表示药物作用强的属性，不能与趋向补语“下去”连用表示动作或状态的延续。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "不需要這麼強效治病。",
        "is_correct": false
      },
      {
        "text": "這藥強效下去了。",
        "is_correct": false
      },
      {
        "text": "治病不需要這麼強效。",
        "is_correct": true
      },
      {
        "text": "這種感冒藥正強效著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“強效”為性質形容詞，表示藥物作用強的固有屬性，不能加動態助詞“著”表示狀態的持續進行。 語序錯誤。“這麼強效”在句中應作謂語或補語，說明治療的程度或方法，不能直接放在動詞“治病”前作狀語。 方向/結果補語誤用。“強效”表示藥物作用強的屬性，不能與趨向補語“下去”連用表示動作或狀態的延續。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "高效",
    "弱效",
    "速效",
    "长效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法有很强的作用。",
      "explanation": "反义项：弱效指药物或方法作用微弱，与强效（作用很强）构成反义关系"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "高效",
      "弱效",
      "速效",
      "長效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法有很強的作用。",
        "explanation": "反義項：弱效指藥物或方法作用微弱，與強效（作用很強）構成反義關係"
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
      "text": "这种强效感冒药效果好。",
      "is_correct": true
    },
    {
      "text": "这种感冒药强效出来效果好。",
      "is_correct": false
    },
    {
      "text": "强效的这种感冒药效果好。",
      "is_correct": false
    },
    {
      "text": "这感冒药以前强效过。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“强效”是性质形容词，表示药物固有属性，不能加动态助词“过”表示经历。 语序错误。多层定语语序不当，指示代词“这种”应放在形容词“强效的”之前。 方向补语误用。“强效”是形容词，不能带趋向补语“出来”，应直接作定语或谓语。",
  "target_word": "强效",
  "hant": {
    "sentences": [
      {
        "text": "這種強效感冒藥效果好。",
        "is_correct": true
      },
      {
        "text": "這種感冒藥強效出來效果好。",
        "is_correct": false
      },
      {
        "text": "強效的這種感冒藥效果好。",
        "is_correct": false
      },
      {
        "text": "這感冒藥以前強效過。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“強效”是性質形容詞，表示藥物固有屬性，不能加動態助詞“過”表示經歷。 語序錯誤。多層定語語序不當，指示代詞“這種”應放在形容詞“強效的”之前。 方向補語誤用。“強效”是形容詞，不能帶趨向補語“出來”，應直接作定語或謂語。",
    "target_word": "強效"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "强效",
  "relation": "antonym",
  "options": [
    "特效",
    "弱效",
    "速效",
    "长效"
  ],
  "correct_answer": "弱效",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指药物或方法有很强的作用。",
      "explanation": "反义项：指药物或方法的作用很弱，与“强效”构成反义关系。"
    }
  },
  "hant": {
    "word": "強效",
    "relation": "antonym",
    "options": [
      "特效",
      "弱效",
      "速效",
      "長效"
    ],
    "correct_answer": "弱效",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指藥物或方法有很強的作用。",
        "explanation": "反義項：指藥物或方法的作用很弱，與“強效”構成反義關係。"
      }
    }
  }
}
```

---
