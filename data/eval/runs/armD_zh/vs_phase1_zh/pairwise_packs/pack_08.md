# Pairwise review pack 08

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


## sense 19870, level 3

#### Pack A
### Level 3 (sense 19870, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "周末我___想去公园散步。",
  "original_sentence": "周末我也想去公园散步。",
  "correct_answer": "也",
  "options": [
    "也",
    "都",
    "刚",
    "竟"
  ],
  "explanation": "正确。“也”表示同样，说明除了别人之外，“我”同样有去公园散步的愿望。",
  "distractor_tags": {},
  "word_definition": "副词。表示同样、并列或加强语气。",
  "target_word": "也",
  "hant": {
    "sentence_with_blank": "週末我___想去公園散步。",
    "original_sentence": "週末我也想去公園散步。",
    "correct_answer": "也",
    "options": [
      "也",
      "都",
      "剛",
      "竟"
    ],
    "explanation": "正確。“也”表示同樣，說明除了別人之外，“我”同樣有去公園散步的願望。",
    "distractor_tags": {},
    "word_definition": "副詞。表示同樣、並列或加強語氣。",
    "target_word": "也"
  }
}
```

#### Pack B
### Level 3 (sense 19870, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "他___一直等着你的回复呢。",
  "original_sentence": "他也一直等着你的回复呢。",
  "correct_answer": "也",
  "options": [
    "且",
    "也",
    "才",
    "正"
  ],
  "explanation": "正确选项：表示同样或加强语气，符合语境。",
  "distractor_tags": {},
  "word_definition": "副词。表示同样、并列或加强语气。",
  "target_word": "也",
  "hant": {
    "sentence_with_blank": "他___一直等著你的回覆呢。",
    "original_sentence": "他也一直等著你的回覆呢。",
    "correct_answer": "也",
    "options": [
      "且",
      "也",
      "才",
      "正"
    ],
    "explanation": "正確選項：表示同樣或加強語氣，符合語境。",
    "distractor_tags": {},
    "word_definition": "副詞。表示同樣、並列或加強語氣。",
    "target_word": "也"
  }
}
```

---

## sense 19870, level 6

#### Pack A
### Level 6 (sense 19870, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "今天的天气也冷特别。",
      "is_correct": false
    },
    {
      "text": "也今天的天气特别冷。",
      "is_correct": false
    },
    {
      "text": "今天的天气也特别冷。",
      "is_correct": true
    },
    {
      "text": "今天的天气也了特别冷。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。程度副词“特别”必须放在形容词“冷”的前面作状语，不能放在后面作补语。 体标位置错误。动态助词“了”通常放在动词后或句末表示变化或完成，不能直接放在副词“也”和形容词“冷”之间。 语序错误。副词“也”在句中作状语时，通常必须放在主语（今天的天气）之后、谓语（特别冷）之前，不能放在句首。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "今天的天氣也冷特別。",
        "is_correct": false
      },
      {
        "text": "也今天的天氣特別冷。",
        "is_correct": false
      },
      {
        "text": "今天的天氣也特別冷。",
        "is_correct": true
      },
      {
        "text": "今天的天氣也了特別冷。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。程度副詞“特別”必須放在形容詞“冷”的前面作狀語，不能放在後面作補語。 體標位置錯誤。動態助詞“了”通常放在動詞後或句末表示變化或完成，不能直接放在副詞“也”和形容詞“冷”之間。 語序錯誤。副詞“也”在句中作狀語時，通常必須放在主語（今天的天氣）之後、謂語（特別冷）之前，不能放在句首。",
    "target_word": "也"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "弟弟连也看懂了这部电影。",
      "is_correct": false
    },
    {
      "text": "连弟弟也看懂了这部电影。",
      "is_correct": true
    },
    {
      "text": "连弟弟也看懂过这部电影。",
      "is_correct": false
    },
    {
      "text": "连弟弟看懂了也这部电影。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：副词“也”应放在主要动词“看懂”之前，不能放在动词和宾语之间，破坏了正常的“状语—动词—宾语”语序。 体标选用错误：“连……也……”句型通常用于强调某种极端情况下的结果或能力，常与“了”连用表示实现，用“过”表示过去经历会削弱强调当前结果的语用效果，搭配不自然。 语序错误：在“连……也……”结构中，“连”必须直接放在被强调的名词（弟弟）之前，不能将“也”插入到“连”和名词之间，导致句法结构破坏。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "弟弟連也看懂了這部電影。",
        "is_correct": false
      },
      {
        "text": "連弟弟也看懂了這部電影。",
        "is_correct": true
      },
      {
        "text": "連弟弟也看懂過這部電影。",
        "is_correct": false
      },
      {
        "text": "連弟弟看懂了也這部電影。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：副詞“也”應放在主要動詞“看懂”之前，不能放在動詞和賓語之間，破壞了正常的“狀語—動詞—賓語”語序。 體標選用錯誤：“連……也……”句型通常用於強調某種極端情況下的結果或能力，常與“了”連用表示實現，用“過”表示過去經歷會削弱強調當前結果的語用效果，搭配不自然。 語序錯誤：在“連……也……”結構中，“連”必須直接放在被強調的名詞（弟弟）之前，不能將“也”插入到“連”和名詞之間，導致句法結構破壞。",
    "target_word": "也"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "也",
  "relation": "antonym",
  "options": [
    "又",
    "还",
    "只",
    "都"
  ],
  "correct_answer": "只",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词。表示同样、并列或加强语气。",
      "explanation": "反义：「也」表同样、并列（包括），「只」表仅限于某范围（排除），二者在范围指向上相反"
    }
  },
  "hant": {
    "word": "也",
    "relation": "antonym",
    "options": [
      "又",
      "還",
      "只",
      "都"
    ],
    "correct_answer": "只",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞。表示同樣、並列或加強語氣。",
        "explanation": "反義：「也」表同樣、並列（包括），「只」表僅限於某範圍（排除），二者在範圍指向上相反"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19870, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我也把这件事告诉了我的好朋友昨天。",
      "is_correct": false
    },
    {
      "text": "我也把这件事了告诉我的好朋友。",
      "is_correct": false
    },
    {
      "text": "我也把这件事告诉了我的好朋友。",
      "is_correct": true
    },
    {
      "text": "我也把这件事告诉给我的好朋友。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。时间状语“昨天”应放在句首或主语“我”之后，不能放在句末。 体标位置错误。动态助词“了”应紧跟在动词“告诉”之后，不能放在“把”字短语和动词之间。 方向补语误用。动词“告诉”本身已包含传递方向，后面不能再加方向补语“给”，应直接使用“告诉”或改用“说给”。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "我也把這件事告訴了我的好朋友昨天。",
        "is_correct": false
      },
      {
        "text": "我也把這件事了告訴我的好朋友。",
        "is_correct": false
      },
      {
        "text": "我也把這件事告訴了我的好朋友。",
        "is_correct": true
      },
      {
        "text": "我也把這件事告訴給我的好朋友。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。時間狀語“昨天”應放在句首或主語“我”之後，不能放在句末。 體標位置錯誤。動態助詞“了”應緊跟在動詞“告訴”之後，不能放在“把”字短語和動詞之間。 方向補語誤用。動詞“告訴”本身已包含傳遞方向，後面不能再加方向補語“給”，應直接使用“告訴”或改用“說給”。",
    "target_word": "也"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "连这么简单的问题他也不知道。",
      "is_correct": true
    },
    {
      "text": "连这么简单的问题他也猜不进去。",
      "is_correct": false
    },
    {
      "text": "连这么简单的问题他也不知道着。",
      "is_correct": false
    },
    {
      "text": "连这么简单的问题也不知道他。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误：“知道”是表示认知状态的动词，不能与表示动作持续的体标“着”连用。 语序错误：主语“他”被错误地放在了句末，破坏了“连……也……”句式中正常的“主题—评论”结构。 方向/结果补语误用：“猜”的结果补语应为“出”或“到”，表示得出结果，而“进去”表示方向向内，不能与“猜”搭配。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "連這麼簡單的問題他也不知道。",
        "is_correct": true
      },
      {
        "text": "連這麼簡單的問題他也猜不進去。",
        "is_correct": false
      },
      {
        "text": "連這麼簡單的問題他也不知道著。",
        "is_correct": false
      },
      {
        "text": "連這麼簡單的問題也不知道他。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤：“知道”是表示認知狀態的動詞，不能與表示動作持續的體標“著”連用。 語序錯誤：主語“他”被錯誤地放在了句末，破壞了“連……也……”句式中正常的“主題—評論”結構。 方向/結果補語誤用：“猜”的結果補語應為“出”或“到”，表示得出結果，而“進去”表示方向向內，不能與“猜”搭配。",
    "target_word": "也"
  }
}
```

---

## sense 19870, level 7

#### Pack A
### Level 7 (sense 19870, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "周末我也想去公园散步。",
      "is_correct": true
    },
    {
      "text": "他昨天也去过那家书店。",
      "is_correct": true
    },
    {
      "text": "他昨天去过那家书店也。",
      "is_correct": false,
      "error_description": "语序错误。副词“也”不能像英语的“too”一样放在句末，而应该放在主语之后、谓语动词之前。"
    },
    {
      "text": "这件衣服也很适合你。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "週末我也想去公園散步。",
        "is_correct": true
      },
      {
        "text": "他昨天也去過那家書店。",
        "is_correct": true
      },
      {
        "text": "他昨天去過那家書店也。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“也”不能像英語的“too”一樣放在句末，而應該放在主語之後、謂語動詞之前。"
      },
      {
        "text": "這件衣服也很適合你。",
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
      "text": "连弟弟也看懂了这部电影。",
      "is_correct": true
    },
    {
      "text": "他也没有按时完成作业。",
      "is_correct": true
    },
    {
      "text": "也他昨天去过那家书店。",
      "is_correct": false,
      "error_description": "语序错误。副词“也”通常应放在主语之后、谓语动词之前，不能直接放在主语前面。"
    },
    {
      "text": "我也不想参加这个活动。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "連弟弟也看懂了這部電影。",
        "is_correct": true
      },
      {
        "text": "他也沒有按時完成作業。",
        "is_correct": true
      },
      {
        "text": "也他昨天去過那家書店。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“也”通常應放在主語之後、謂語動詞之前，不能直接放在主語前面。"
      },
      {
        "text": "我也不想參加這個活動。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19870, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我昨天去了图书馆，也他去了。",
      "is_correct": false,
      "error_description": "副词“也”应该放在主语之后、谓语之前。句中“也”放在了主语“他”的前面，属于语序错误，应将其移至主语“他”之后。"
    },
    {
      "text": "我也很喜欢看这本漫画书。",
      "is_correct": true
    },
    {
      "text": "他去过北京，我也去过那里。",
      "is_correct": true
    },
    {
      "text": "今天天气很好，我的心情也很好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我昨天去了圖書館，也他去了。",
        "is_correct": false,
        "error_description": "副詞“也”應該放在主語之後、謂語之前。句中“也”放在了主語“他”的前面，屬於語序錯誤，應將其移至主語“他”之後。"
      },
      {
        "text": "我也很喜歡看這本漫畫書。",
        "is_correct": true
      },
      {
        "text": "他去過北京，我也去過那裡。",
        "is_correct": true
      },
      {
        "text": "今天天氣很好，我的心情也很好。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 19882, level 3

#### Pack A
### Level 3 (sense 19882, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我们都要学习___。",
  "original_sentence": "我们都要学习诚实。",
  "correct_answer": "诚实",
  "options": [
    "虚伪",
    "诚实",
    "帅",
    "高大"
  ],
  "explanation": "正确。‘诚实’在此处作名词化形容词，表示一种不虚假的品质，符合‘学习’的宾语要求。",
  "distractor_tags": {},
  "word_definition": "指言行与内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "我們都要學習___。",
    "original_sentence": "我們都要學習誠實。",
    "correct_answer": "誠實",
    "options": [
      "虛偽",
      "誠實",
      "帥",
      "高大"
    ],
    "explanation": "正確。‘誠實’在此處作名詞化形容詞，表示一種不虛假的品質，符合‘學習’的賓語要求。",
    "distractor_tags": {},
    "word_definition": "指言行與內心一致，不虛假。",
    "target_word": "誠實"
  }
}
```

#### Pack B
### Level 3 (sense 19882, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "说清楚，才能让别人觉得你很___。",
  "original_sentence": "说清楚，才能让别人觉得你很诚实。",
  "correct_answer": "诚实",
  "options": [
    "诚实",
    "勇敢",
    "活泼",
    "聪明"
  ],
  "explanation": "正确。填入“诚实”表示把话说清楚，展现出不虚假的品质，符合语境。",
  "distractor_tags": {},
  "word_definition": "指言行与内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "說清楚，才能讓別人覺得你很___。",
    "original_sentence": "說清楚，才能讓別人覺得你很誠實。",
    "correct_answer": "誠實",
    "options": [
      "誠實",
      "勇敢",
      "活潑",
      "聰明"
    ],
    "explanation": "正確。填入“誠實”表示把話說清楚，展現出不虛假的品質，符合語境。",
    "distractor_tags": {},
    "word_definition": "指言行與內心一致，不虛假。",
    "target_word": "誠實"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "做人要___，不能撒谎。",
  "original_sentence": "做人要诚实，不能撒谎。",
  "correct_answer": "诚实",
  "options": [
    "活泼",
    "勇敢",
    "聪明",
    "诚实"
  ],
  "explanation": "正确。填入“诚实”表示做人要言行一致、不撒谎，符合句意。",
  "distractor_tags": {},
  "word_definition": "指言行与内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "做人要___，不能撒謊。",
    "original_sentence": "做人要誠實，不能撒謊。",
    "correct_answer": "誠實",
    "options": [
      "活潑",
      "勇敢",
      "聰明",
      "誠實"
    ],
    "explanation": "正確。填入“誠實”表示做人要言行一致、不撒謊，符合句意。",
    "distractor_tags": {},
    "word_definition": "指言行與內心一致，不虛假。",
    "target_word": "誠實"
  }
}
```

---

## sense 19882, level 6

#### Pack A
### Level 6 (sense 19882, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "诚实应该朋友之间，不能撒谎。",
      "is_correct": false
    },
    {
      "text": "朋友之间应该诚实着，不能撒谎。",
      "is_correct": false
    },
    {
      "text": "朋友之间应该诚实，不能撒谎。",
      "is_correct": true
    },
    {
      "text": "朋友之间应该诚实出来，不能撒谎。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。'诚实'是性质形容词，表示稳定的内在品质，不能加动态助词'着'来表示动作或状态的持续。 语序错误。主语'朋友之间'应位于句首，能愿动词'应该'必须放在形容词'诚实'之前，原句主谓及能愿动词位置颠倒。 结果补语误用。'诚实'是表示内在品质的形容词，不能与趋向补语'出来'搭配表示显露，应使用'表现得诚实'等表达。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "誠實應該朋友之間，不能撒謊。",
        "is_correct": false
      },
      {
        "text": "朋友之間應該誠實著，不能撒謊。",
        "is_correct": false
      },
      {
        "text": "朋友之間應該誠實，不能撒謊。",
        "is_correct": true
      },
      {
        "text": "朋友之間應該誠實出來，不能撒謊。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。'誠實'是性質形容詞，表示穩定的內在品質，不能加動態助詞'著'來表示動作或狀態的持續。 語序錯誤。主語'朋友之間'應位於句首，能願動詞'應該'必須放在形容詞'誠實'之前，原句主謂及能願動詞位置顛倒。 結果補語誤用。'誠實'是表示內在品質的形容詞，不能與趨向補語'出來'搭配表示顯露，應使用'表現得誠實'等表達。",
    "target_word": "誠實"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "诚实",
  "relation": "antonym",
  "options": [
    "固执",
    "骄傲",
    "虚伪",
    "狡猾"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指言行与内心一致，不虚假。",
      "explanation": "反义项：指言行与内心不一致，虚假不真实，与目标词构成反义关系"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "固執",
      "驕傲",
      "虛偽",
      "狡猾"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指言行與內心一致，不虛假。",
        "explanation": "反義項：指言行與內心不一致，虛假不真實，與目標詞構成反義關係"
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
      "text": "他诚实出来了，大家才相信你。",
      "is_correct": false
    },
    {
      "text": "做一个诚实的人，大家才会相信你。",
      "is_correct": true
    },
    {
      "text": "大家才会相信诚实做一个的人。",
      "is_correct": false
    },
    {
      "text": "他诚实着承认了错误。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。‘诚实’是性质形容词，不能加动态助词‘着’来表示动作的持续或状态的进行。 语序错误。定语‘诚实’和中心语‘人’的位置颠倒，破坏了‘形容词+的+名词’的正常偏正结构。 方向/结果补语误用。‘诚实’是静态的性质形容词，不能带趋向补语‘出来’表示状态的变化或显露。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "他誠實出來了，大家才相信你。",
        "is_correct": false
      },
      {
        "text": "做一個誠實的人，大家才會相信你。",
        "is_correct": true
      },
      {
        "text": "大家才會相信誠實做一個的人。",
        "is_correct": false
      },
      {
        "text": "他誠實著承認了錯誤。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。‘誠實’是性質形容詞，不能加動態助詞‘著’來表示動作的持續或狀態的進行。 語序錯誤。定語‘誠實’和中心語‘人’的位置顛倒，破壞了‘形容詞+的+名詞’的正常偏正結構。 方向/結果補語誤用。‘誠實’是靜態的性質形容詞，不能帶趨向補語‘出來’表示狀態的變化或顯露。",
    "target_word": "誠實"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "诚实",
  "relation": "antonym",
  "options": [
    "虚伪",
    "善良",
    "勇敢",
    "宽容"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指言行与内心一致，不虚假。",
      "explanation": "指表里不一、不真实，与“言行与内心一致”正好相反，构成反义关系。"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "虛偽",
      "善良",
      "勇敢",
      "寬容"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指言行與內心一致，不虛假。",
        "explanation": "指表裡不一、不真實，與“言行與內心一致”正好相反，構成反義關係。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19882, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "朋友之间最重要的是很诚实。",
      "is_correct": false
    },
    {
      "text": "朋友之间最重要的是诚实。",
      "is_correct": true
    },
    {
      "text": "朋友之间最重要的是诚实地。",
      "is_correct": false
    },
    {
      "text": "朋友之间诚实的是最重要。",
      "is_correct": false
    }
  ],
  "explanation": "语序/搭配错误：“诚实”本身已包含性质状态，前面加程度副词“很”虽语法可行，但在“最重要的是……”这种强调本质属性的句式中，直接使用“诚实”更自然，加“很”显得累赘且语用不自然。 语序错误：将形容词“诚实”提前作主语，破坏了“是……的”强调句型或判断句的正常语序，导致句子结构混乱，不符合汉语表达习惯。 词性/句法错误：“诚实”在此处作名词性成分（宾语），后面不能加结构助词“地”，“地”通常用于连接状语和中心语，此处属于虚词误用。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "朋友之間最重要的是很誠實。",
        "is_correct": false
      },
      {
        "text": "朋友之間最重要的是誠實。",
        "is_correct": true
      },
      {
        "text": "朋友之間最重要的是誠實地。",
        "is_correct": false
      },
      {
        "text": "朋友之間誠實的是最重要。",
        "is_correct": false
      }
    ],
    "explanation": "語序/搭配錯誤：“誠實”本身已包含性質狀態，前面加程度副詞“很”雖語法可行，但在“最重要的是……”這種強調本質屬性的句式中，直接使用“誠實”更自然，加“很”顯得累贅且語用不自然。 語序錯誤：將形容詞“誠實”提前作主語，破壞了“是……的”強調句型或判斷句的正常語序，導致句子結構混亂，不符合漢語表達習慣。 詞性/句法錯誤：“誠實”在此處作名詞性成分（賓語），後面不能加結構助詞“地”，“地”通常用於連線狀語和中心語，此處屬於虛詞誤用。",
    "target_word": "誠實"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他诚实了地承认了自己的错误。",
      "is_correct": false
    },
    {
      "text": "他诚实地很承认了自己的错误。",
      "is_correct": false
    },
    {
      "text": "他承认了自己的错误诚实地。",
      "is_correct": false
    },
    {
      "text": "他诚实地承认了自己的错误。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误。程度副词“很”不能放在形容词“诚实”和动词“承认”之间，应改为“他很诚实地承认了……”。 体标位置错误。动态助词“了”不能插入在形容词“诚实”和结构助词“地”之间，应放在句末或动词后。 语序错误。状语“诚实地”必须放在中心语“承认”之前，不能放在句末。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "他誠實了地承認了自己的錯誤。",
        "is_correct": false
      },
      {
        "text": "他誠實地很承認了自己的錯誤。",
        "is_correct": false
      },
      {
        "text": "他承認了自己的錯誤誠實地。",
        "is_correct": false
      },
      {
        "text": "他誠實地承認了自己的錯誤。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤。程度副詞“很”不能放在形容詞“誠實”和動詞“承認”之間，應改為“他很誠實地承認了……”。 體標位置錯誤。動態助詞“了”不能插入在形容詞“誠實”和結構助詞“地”之間，應放在句末或動詞後。 語序錯誤。狀語“誠實地”必須放在中心語“承認”之前，不能放在句末。",
    "target_word": "誠實"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "诚实",
  "relation": "antonym",
  "options": [
    "勇敢",
    "虚伪",
    "善良",
    "谦虚"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指言行与内心一致，不虚假。",
      "explanation": "反义：指内心与言行不一致、做作不真实，与「言行与内心一致」恰好相反"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "勇敢",
      "虛偽",
      "善良",
      "謙虛"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指言行與內心一致，不虛假。",
        "explanation": "反義：指內心與言行不一致、做作不真實，與「言行與內心一致」恰好相反"
      }
    }
  }
}
```

---

## sense 19882, level 7

#### Pack A
### Level 7 (sense 19882, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "诚实他是一个好孩子。",
      "is_correct": false,
      "error_description": "语序错误。‘诚实’是形容词，应作定语修饰名词‘好孩子’，放在数量词‘一个’之后，不能放在句首。"
    },
    {
      "text": "他是一个诚实的好孩子。",
      "is_correct": true
    },
    {
      "text": "我们应该做一个诚实的人。",
      "is_correct": true
    },
    {
      "text": "说清楚，才能让别人觉得你很诚实。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "誠實他是一個好孩子。",
        "is_correct": false,
        "error_description": "語序錯誤。‘誠實’是形容詞，應作定語修飾名詞‘好孩子’，放在數量詞‘一個’之後，不能放在句首。"
      },
      {
        "text": "他是一個誠實的好孩子。",
        "is_correct": true
      },
      {
        "text": "我們應該做一個誠實的人。",
        "is_correct": true
      },
      {
        "text": "說清楚，才能讓別人覺得你很誠實。",
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
      "text": "他诚实地承认了自己的错误。",
      "is_correct": true
    },
    {
      "text": "他诚实了承认自己的错误。",
      "is_correct": false,
      "error_description": "体标选用错误。'诚实'是形容词，作状语修饰动词时应使用结构助词'地'，而不能使用动态助词'了'。"
    },
    {
      "text": "做人要诚实，不能撒谎。",
      "is_correct": true
    },
    {
      "text": "他的诚实赢得了大家的信任。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他誠實地承認了自己的錯誤。",
        "is_correct": true
      },
      {
        "text": "他誠實了承認自己的錯誤。",
        "is_correct": false,
        "error_description": "體標選用錯誤。'誠實'是形容詞，作狀語修飾動詞時應使用結構助詞'地'，而不能使用動態助詞'了'。"
      },
      {
        "text": "做人要誠實，不能撒謊。",
        "is_correct": true
      },
      {
        "text": "他的誠實贏得了大家的信任。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19882, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他说话诚实了，大家都很喜欢他。",
      "is_correct": false,
      "error_description": "“诚实”是形容词，表示人的品质，不能直接加动态助词“了”表示动作完成或状态变化。应去掉“了”。"
    },
    {
      "text": "他说话诚实，大家都很喜欢他。",
      "is_correct": true
    },
    {
      "text": "那个诚实的孩子把钱包交给了警察。",
      "is_correct": true
    },
    {
      "text": "说清楚，才能让别人觉得你很诚实。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他說話誠實了，大家都很喜歡他。",
        "is_correct": false,
        "error_description": "“誠實”是形容詞，表示人的品質，不能直接加動態助詞“了”表示動作完成或狀態變化。應去掉“了”。"
      },
      {
        "text": "他說話誠實，大家都很喜歡他。",
        "is_correct": true
      },
      {
        "text": "那個誠實的孩子把錢包交給了警察。",
        "is_correct": true
      },
      {
        "text": "說清楚，才能讓別人覺得你很誠實。",
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
      "text": "我们都要学习了诚实。",
      "is_correct": false,
      "error_description": "错误类型为体标误用。动词“学习”后接表示抽象概念的词语作宾语时，不能使用动态助词“了”，正确写法应去掉“了”。"
    },
    {
      "text": "我们都要学习诚实。",
      "is_correct": true
    },
    {
      "text": "老师教导我们要诚实。",
      "is_correct": true
    },
    {
      "text": "做一个诚实的人，大家才会相信你。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我們都要學習了誠實。",
        "is_correct": false,
        "error_description": "錯誤型別為體標誤用。動詞“學習”後接表示抽象概念的詞語作賓語時，不能使用動態助詞“了”，正確寫法應去掉“了”。"
      },
      {
        "text": "我們都要學習誠實。",
        "is_correct": true
      },
      {
        "text": "老師教導我們要誠實。",
        "is_correct": true
      },
      {
        "text": "做一個誠實的人，大家才會相信你。",
        "is_correct": true
      }
    ]
  }
}
```

---
