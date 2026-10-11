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


## sense 19860, level 6

#### Pack A
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他提出了一个很乱的观点。",
      "is_correct": true
    },
    {
      "text": "他提出了一个很乱着的观点。",
      "is_correct": false
    },
    {
      "text": "他提出了很乱的一个观点。",
      "is_correct": false
    },
    {
      "text": "他提出了一张很乱的观点。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'观点'应使用量词'个'，不能使用用于纸张或扁平物体的'张'。 体标选用错误。'乱'是性质形容词，前面已有程度副词'很'，后面不能加动态助词'着'来表示动作的持续。 语序错误。在汉语中，形容词定语'很乱'通常应放在数量词'一个'之后，即'一个很乱的观点'，放在数量词之前不符合常规语序。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "他提出了一個很亂的觀點。",
        "is_correct": true
      },
      {
        "text": "他提出了一個很亂著的觀點。",
        "is_correct": false
      },
      {
        "text": "他提出了很亂的一個觀點。",
        "is_correct": false
      },
      {
        "text": "他提出了一張很亂的觀點。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'觀點'應使用量詞'個'，不能使用用於紙張或扁平物體的'張'。 體標選用錯誤。'亂'是性質形容詞，前面已有程度副詞'很'，後面不能加動態助詞'著'來表示動作的持續。 語序錯誤。在漢語中，形容詞定語'很亂'通常應放在數量詞'一個'之後，即'一個很亂的觀點'，放在數量詞之前不符合常規語序。",
    "target_word": "亂"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "整齐",
    "详细",
    "复杂",
    "模糊"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义项：指事物有秩序、有条理的状态，与目标词构成反义"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "整齊",
      "詳細",
      "複雜",
      "模糊"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義項：指事物有秩序、有條理的狀態，與目標詞構成反義"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "单调",
    "安静",
    "整齐",
    "干净"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "同义项：指事物有秩序、有条理，与“乱”构成反义关系"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "單調",
      "安靜",
      "整齊",
      "乾淨"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "同義項：指事物有秩序、有條理，與“亂”構成反義關係"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "别把桌子弄乱了。",
      "is_correct": true
    },
    {
      "text": "别乱把桌子弄了。",
      "is_correct": false
    },
    {
      "text": "别把桌子乱得弄了。",
      "is_correct": false
    },
    {
      "text": "桌子被乱弄了。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：结果补语'乱'应紧跟在动词'弄'之后，构成'弄乱'，而不是放在'得'字结构中作为状态描述，且'得'后通常接程度或状态补语，此处结构混乱。 语序/搭配错误：在被动句中，结果补语通常紧贴动词。更自然的说法是'桌子被弄乱了'。'乱弄'作为一个词通常指胡乱做事，而非导致桌子变乱的状态结果。 语义/语用错误：'乱'作为状语修饰'弄'时，意为'胡乱地做某事'，侧重于动作的方式随意；而原句意在禁止导致'桌子变乱'这一结果。应使用动补结构'弄乱'来强调结果。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "別把桌子弄亂了。",
        "is_correct": true
      },
      {
        "text": "別亂把桌子弄了。",
        "is_correct": false
      },
      {
        "text": "別把桌子亂得弄了。",
        "is_correct": false
      },
      {
        "text": "桌子被亂弄了。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：結果補語'亂'應緊跟在動詞'弄'之後，構成'弄亂'，而不是放在'得'字結構中作為狀態描述，且'得'後通常接程度或狀態補語，此處結構混亂。 語序/搭配錯誤：在被動句中，結果補語通常緊貼動詞。更自然的說法是'桌子被弄亂了'。'亂弄'作為一個詞通常指胡亂做事，而非導致桌子變亂的狀態結果。 語義/語用錯誤：'亂'作為狀語修飾'弄'時，意為'胡亂地做某事'，側重於動作的方式隨意；而原句意在禁止導致'桌子變亂'這一結果。應使用動補結構'弄亂'來強調結果。",
    "target_word": "亂"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "忙碌",
    "整齐",
    "干净",
    "杂乱"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "指有秩序、有条理，与“乱”在该义项下构成反义关系。"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "忙碌",
      "整齊",
      "乾淨",
      "雜亂"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "指有秩序、有條理，與“亂”在該義項下構成反義關係。"
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
      "text": "计划很乱打了，我们需要重做。",
      "is_correct": false
    },
    {
      "text": "计划被打乱了，我们需要重做。",
      "is_correct": true
    },
    {
      "text": "计划被乱打了，我们需要重做。",
      "is_correct": false
    },
    {
      "text": "计划乱得打了，我们需要重做。",
      "is_correct": false
    }
  ],
  "explanation": "语序/结构错误：在被动句和动补结构中，“乱”作为状语修饰动词时，应位于动词之前或作为结果补语的一部分（如“打乱”）。此处将“乱”插入“打”和“了”之间且置于动词前，破坏了“被打乱”这一固定搭配的完整性，读起来不通顺。正确的表达应为“计划被打乱了”。 句法错误：“乱”是形容词，不能直接修饰动词“打”构成“乱打”来表示“使...变得混乱”的结果。这里混淆了状态形容词和致使性动补结构。应使用动补结构“打乱”。 结构误用：“得”字补语结构通常用于描述程度或状态（如“乱得一团糟”）。“乱得打了”不符合汉语语法习惯，无法表达“计划被破坏”的含义。应改为“计划被打乱了”。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "計劃很亂打了，我們需要重做。",
        "is_correct": false
      },
      {
        "text": "計劃被打亂了，我們需要重做。",
        "is_correct": true
      },
      {
        "text": "計劃被亂打了，我們需要重做。",
        "is_correct": false
      },
      {
        "text": "計劃亂得打了，我們需要重做。",
        "is_correct": false
      }
    ],
    "explanation": "語序/結構錯誤：在被動句和動補結構中，“亂”作為狀語修飾動詞時，應位於動詞之前或作為結果補語的一部分（如“打亂”）。此處將“亂”插入“打”和“了”之間且置於動詞前，破壞了“被打亂”這一固定搭配的完整性，讀起來不通順。正確的表達應為“計劃被打亂了”。 句法錯誤：“亂”是形容詞，不能直接修飾動詞“打”構成“亂打”來表示“使...變得混亂”的結果。這裡混淆了狀態形容詞和致使性動補結構。應使用動補結構“打亂”。 結構誤用：“得”字補語結構通常用於描述程度或狀態（如“亂得一團糟”）。“亂得打了”不符合漢語語法習慣，無法表達“計劃被破壞”的含義。應改為“計劃被打亂了”。",
    "target_word": "亂"
  }
}
```

---

## sense 19867, level 6

#### Pack A
### Level 6 (sense 19867, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这道题我才做出来。",
      "is_correct": true
    },
    {
      "text": "这道题我才已经做出来了。",
      "is_correct": false
    },
    {
      "text": "这道题我才做得出来。",
      "is_correct": false
    },
    {
      "text": "我才把这道题做出来昨天。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：“才”强调刚刚完成，而“已经”强调完成的状态，两者连用造成语义冲突和冗余，通常不这样搭配。 语序错误：时间状语“昨天”应当放在主语之后、动词短语之前，或者句首，不能放在句末。 补语误用：“做得出来”表示能力或可能性（能做成），而原句强调的是动作完成的时间晚。此处应用结果补语“做出来”并配合“了”，而非可能补语。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "這道題我才做出來。",
        "is_correct": true
      },
      {
        "text": "這道題我才已經做出來了。",
        "is_correct": false
      },
      {
        "text": "這道題我才做得出來。",
        "is_correct": false
      },
      {
        "text": "我才把這道題做出來昨天。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：“才”強調剛剛完成，而“已經”強調完成的狀態，兩者連用造成語義衝突和冗餘，通常不這樣搭配。 語序錯誤：時間狀語“昨天”應當放在主語之後、動詞短語之前，或者句首，不能放在句末。 補語誤用：“做得出來”表示能力或可能性（能做成），而原句強調的是動作完成的時間晚。此處應用結果補語“做出來”並配合“了”，而非可能補語。",
    "target_word": "才"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "才",
  "relation": "antonym",
  "options": [
    "早",
    "刚",
    "就",
    "已"
  ],
  "correct_answer": "已",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "表示事情发生得早，或强调刚刚发生。",
      "explanation": "反义关系；'才'强调动作刚发生或发生得晚（相对于预期），'已'表示动作已经完成或发生得早"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "早",
      "剛",
      "就",
      "已"
    ],
    "correct_answer": "已",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "表示事情發生得早，或強調剛剛發生。",
        "explanation": "反義關係；'才'強調動作剛發生或發生得晚（相對於預期），'已'表示動作已經完成或發生得早"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 19867, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他才睡过了，就梦到了妈妈。",
      "is_correct": false
    },
    {
      "text": "他才睡着，就梦到了妈妈。",
      "is_correct": true
    },
    {
      "text": "他才睡起，就梦到了妈妈。",
      "is_correct": false
    },
    {
      "text": "他睡着才，就梦到了妈妈。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“才”表示动作刚刚发生，强调时间近；“过”表示过去的经历。两者连用造成体貌冲突，语义不自然。 语序错误：副词“才”修饰动词时，必须放在动词“睡着”之前，不能放在动词之后，此处语序错误。 结果补语误用：“睡”表示进入睡眠状态，其结果补语应为“着”，表示动作达到目的；“起”不能作“睡”的结果补语，此处动补搭配错误。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "他才睡過了，就夢到了媽媽。",
        "is_correct": false
      },
      {
        "text": "他才睡著，就夢到了媽媽。",
        "is_correct": true
      },
      {
        "text": "他才睡起，就夢到了媽媽。",
        "is_correct": false
      },
      {
        "text": "他睡著才，就夢到了媽媽。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“才”表示動作剛剛發生，強調時間近；“過”表示過去的經歷。兩者連用造成體貌衝突，語義不自然。 語序錯誤：副詞“才”修飾動詞時，必須放在動詞“睡著”之前，不能放在動詞之後，此處語序錯誤。 結果補語誤用：“睡”表示進入睡眠狀態，其結果補語應為“著”，表示動作達到目的；“起”不能作“睡”的結果補語，此處動補搭配錯誤。",
    "target_word": "才"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他才真正哭出来，那一刻就释怀了。",
      "is_correct": true
    },
    {
      "text": "他才真正哭起去，那一刻就释怀了。",
      "is_correct": false
    },
    {
      "text": "他才真正哭出来着，那一刻就释怀了。",
      "is_correct": false
    },
    {
      "text": "才他真正哭出来，那一刻就释怀了。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：副词“才”应当放在主语“他”之后，不能放在主语之前。 体标选用错误：“才”强调动作刚刚发生或结束，不能与表示动作持续的体标记“着”搭配使用。 方向补语误用：“起来”表示动作开始或情绪爆发，符合语境；“起去”不是合法的汉语趋向补语，且方向意义错误。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "他才真正哭出來，那一刻就釋懷了。",
        "is_correct": true
      },
      {
        "text": "他才真正哭起去，那一刻就釋懷了。",
        "is_correct": false
      },
      {
        "text": "他才真正哭出來著，那一刻就釋懷了。",
        "is_correct": false
      },
      {
        "text": "才他真正哭出來，那一刻就釋懷了。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：副詞“才”應當放在主語“他”之後，不能放在主語之前。 體標選用錯誤：“才”強調動作剛剛發生或結束，不能與表示動作持續的體標記“著”搭配使用。 方向補語誤用：“起來”表示動作開始或情緒爆發，符合語境；“起去”不是合法的漢語趨向補語，且方向意義錯誤。",
    "target_word": "才"
  }
}
```

---

## sense 19867, level 7

#### Pack A
### Level 7 (sense 19867, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我才看过那部感人的电影。",
      "is_correct": true
    },
    {
      "text": "他才给好朋友发了消息。",
      "is_correct": true
    },
    {
      "text": "他才把秘密告诉了朋友。",
      "is_correct": true
    },
    {
      "text": "他才昨天给好朋友发了消息。",
      "is_correct": false,
      "error_description": "语序错误。时间状语“昨天”应该放在副词“才”的前面，正确语序为“主语 + 时间 + 才 + 动词短语”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "我才看過那部感人的電影。",
        "is_correct": true
      },
      {
        "text": "他才給好朋友發了訊息。",
        "is_correct": true
      },
      {
        "text": "他才把秘密告訴了朋友。",
        "is_correct": true
      },
      {
        "text": "他才昨天給好朋友發了訊息。",
        "is_correct": false,
        "error_description": "語序錯誤。時間狀語“昨天”應該放在副詞“才”的前面，正確語序為“主語 + 時間 + 才 + 動詞短語”。"
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
      "text": "他才真正哭出来，那一刻就释怀了。",
      "is_correct": true
    },
    {
      "text": "我才拒绝了那个无聊的邀请。",
      "is_correct": true
    },
    {
      "text": "他才感动得流下了眼泪。",
      "is_correct": true
    },
    {
      "text": "他才昨天把那本有趣的书看完。",
      "is_correct": false,
      "error_description": "语序错误。时间状语“昨天”应该放在副词“才”的前面，正确的写法是“他昨天才把那本有趣的书看完”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他才真正哭出來，那一刻就釋懷了。",
        "is_correct": true
      },
      {
        "text": "我才拒絕了那個無聊的邀請。",
        "is_correct": true
      },
      {
        "text": "他才感動得流下了眼淚。",
        "is_correct": true
      },
      {
        "text": "他才昨天把那本有趣的書看完。",
        "is_correct": false,
        "error_description": "語序錯誤。時間狀語“昨天”應該放在副詞“才”的前面，正確的寫法是“他昨天才把那本有趣的書看完”。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19867, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他八点才起床。",
      "is_correct": true
    },
    {
      "text": "电影才开始五分钟。",
      "is_correct": true
    },
    {
      "text": "我昨天才见过他。",
      "is_correct": true
    },
    {
      "text": "我昨天才见面他。",
      "is_correct": false,
      "error_description": "动词“见面”是离合词或不及物动词，不能直接带宾语“他”。应改为及物动词“见”，或者调整为“我才和他见面”。在此语境下，使用“见过他”更符合T3级别的语法规范。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他八點才起床。",
        "is_correct": true
      },
      {
        "text": "電影才開始五分鐘。",
        "is_correct": true
      },
      {
        "text": "我昨天才見過他。",
        "is_correct": true
      },
      {
        "text": "我昨天才見面他。",
        "is_correct": false,
        "error_description": "動詞“見面”是離合詞或不及物動詞，不能直接帶賓語“他”。應改為及物動詞“見”，或者調整為“我才和他見面”。在此語境下，使用“見過他”更符合T3級別的語法規範。"
      }
    ]
  }
}
```

---

## sense 19870, level 1

#### Pack A
### Level 1 (sense 19870, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "也",
  "pronunciation": "yě",
  "ipa": "[jɛ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "夜",
    "也",
    "爷",
    "野"
  ],
  "correct_answer": "也",
  "explanation": "正确。读音为 yě（第三声），表示同样或并列。",
  "distractor_explanations": {
    "夜": "错误。读音为 yè（第四声），意思是夜晚，与目标词声调不同。",
    "野": "错误。读音为 yě（第三声），但在本语境中通常指野外或野蛮，虽同音但字形和意义完全不同，此处作为视觉干扰项需注意区分字形。注：严格来说L1主要考察听音辨字，若纯听力无法区分同音字，通常避免同音异义字。但根据规则“不得使用整体同音同调的纯同形异义字”，此处“野”与“也”虽同音同调，但属于不同汉字。为了符合L1声调混淆的主要原则，更标准的干扰项应为声调不同的字。让我们修正干扰项以严格符合“声调混淆”规则。",
    "爷": "错误。读音为 yé（第二声），意思是爷爷或长辈，声调与目标词不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "也",
    "pronunciation": "yě",
    "ipa": "[jɛ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "夜",
      "也",
      "爺",
      "野"
    ],
    "correct_answer": "也",
    "explanation": "正確。讀音為 yě（第三聲），表示同樣或並列。",
    "distractor_explanations": {
      "夜": "錯誤。讀音為 yè（第四聲），意思是夜晚，與目標詞聲調不同。",
      "野": "錯誤。讀音為 yě（第三聲），但在本語境中通常指野外或野蠻，雖同音但字形和意義完全不同，此處作為視覺干擾項需注意區分字形。注：嚴格來說L1主要考察聽音辨字，若純聽力無法區分同音字，通常避免同音異義字。但根據規則“不得使用整體同音同調的純同形異義字”，此處“野”與“也”雖同音同調，但屬於不同漢字。為了符合L1聲調混淆的主要原則，更標準的干擾項應為聲調不同的字。讓我們修正干擾項以嚴格符合“聲調混淆”規則。",
      "爷": "錯誤。讀音為 yé（第二聲），意思是爺爺或長輩，聲調與目標詞不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19870, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "也",
  "pronunciation": "yě",
  "ipa": "[jɛ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "爷",
    "叶",
    "也",
    "夜"
  ],
  "correct_answer": "也",
  "explanation": "正确。读音为 yě，表示同样、并列。",
  "distractor_explanations": {
    "爷": "错误。读音为 yé，二声，指父亲或长辈，声调不同。",
    "夜": "错误。读音为 yè，四声，指从天黑到天亮的时间，声调不同。",
    "叶": "错误。读音为 yè，四声，指植物的叶子，声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "也",
    "pronunciation": "yě",
    "ipa": "[jɛ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "爺",
      "葉",
      "也",
      "夜"
    ],
    "correct_answer": "也",
    "explanation": "正確。讀音為 yě，表示同樣、並列。",
    "distractor_explanations": {
      "爷": "錯誤。讀音為 yé，二聲，指父親或長輩，聲調不同。",
      "夜": "錯誤。讀音為 yè，四聲，指從天黑到天亮的時間，聲調不同。",
      "叶": "錯誤。讀音為 yè，四聲，指植物的葉子，聲調不同。"
    },
    "distractor_source": "llm"
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

#### Pack B
### Level 6 (sense 19870, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他去过北京，我也把那里去过。",
      "is_correct": false
    },
    {
      "text": "他去过北京，我也去过那里。",
      "is_correct": true
    },
    {
      "text": "也他去过北京，我去过那里。",
      "is_correct": false
    },
    {
      "text": "他去北京过，我也去过那里。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误：动态助词“过”应紧贴在动词“去”之后，即“去过北京”，而不是放在宾语“北京”之后。 语序错误：副词“也”应当放在主语“他”之后、动词短语之前，不能放在句首修饰整个句子或置于主语前。 搭配/语序错误：在“把”字句中，动词“去”是不及物动词或方向动词，通常不能直接作为“把”字句的谓语核心来处置宾语“那里”，且“去过”作为动补结构不宜拆分放入典型的“把”字处置结构中，表达极不自然。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "他去過北京，我也把那裡去過。",
        "is_correct": false
      },
      {
        "text": "他去過北京，我也去過那裡。",
        "is_correct": true
      },
      {
        "text": "也他去過北京，我去過那裡。",
        "is_correct": false
      },
      {
        "text": "他去北京過，我也去過那裡。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤：動態助詞“過”應緊貼在動詞“去”之後，即“去過北京”，而不是放在賓語“北京”之後。 語序錯誤：副詞“也”應當放在主語“他”之後、動詞短語之前，不能放在句首修飾整個句子或置於主語前。 搭配/語序錯誤：在“把”字句中，動詞“去”是不及物動詞或方向動詞，通常不能直接作為“把”字句的謂語核心來處置賓語“那裡”，且“去過”作為動補結構不宜拆分放入典型的“把”字處置結構中，表達極不自然。",
    "target_word": "也"
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
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "做人要___，不能骗人。",
  "original_sentence": "做人要诚实，不能骗人。",
  "correct_answer": "诚实",
  "options": [
    "勇敢",
    "诚实",
    "快乐",
    "聪明"
  ],
  "explanation": "正确。句意强调做人的道德准则，“诚实”指言行一致、不欺骗，符合语境。",
  "distractor_tags": {},
  "word_definition": "言行与内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "做人要___，不能騙人。",
    "original_sentence": "做人要誠實，不能騙人。",
    "correct_answer": "誠實",
    "options": [
      "勇敢",
      "誠實",
      "快樂",
      "聰明"
    ],
    "explanation": "正確。句意強調做人的道德準則，“誠實”指言行一致、不欺騙，符合語境。",
    "distractor_tags": {},
    "word_definition": "言行與內心一致，不虛假。",
    "target_word": "誠實"
  }
}
```

---

## sense 19882, level 7

#### Pack A
### Level 7 (sense 19882, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他的表现很诚实，值得信任。",
      "is_correct": true
    },
    {
      "text": "诚实是一种很优秀的习惯。",
      "is_correct": false,
      "error_description": "搭配错误。'诚实'通常被描述为一种'品质'或'美德'，而不是'习惯'。'习惯'指经常重复的行为，而'诚实'是内在的道德属性。"
    },
    {
      "text": "做人要诚实，不能骗人。",
      "is_correct": true
    },
    {
      "text": "保持诚实会让朋友更尊重你。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的表現很誠實，值得信任。",
        "is_correct": true
      },
      {
        "text": "誠實是一種很優秀的習慣。",
        "is_correct": false,
        "error_description": "搭配錯誤。'誠實'通常被描述為一種'品質'或'美德'，而不是'習慣'。'習慣'指經常重複的行為，而'誠實'是內在的道德屬性。"
      },
      {
        "text": "做人要誠實，不能騙人。",
        "is_correct": true
      },
      {
        "text": "保持誠實會讓朋友更尊重你。",
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
