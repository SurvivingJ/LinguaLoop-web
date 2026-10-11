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


## sense 19860, level 6

#### Pack A
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "你把乱我的思路打。",
      "is_correct": false
    },
    {
      "text": "你把我的思路打乱出来。",
      "is_correct": false
    },
    {
      "text": "你把我的思路打乱了。",
      "is_correct": true
    },
    {
      "text": "你把我的思路打乱着。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：'着'表示动作持续或状态保持，但'打乱'是瞬间完成的结果，不能用'着'，应使用'了'。 语序错误：结果补语'乱'必须紧跟在动词'打'之后，不能放在宾语'我的思路'前面。 方向/结果补语误用：'出来'表示从内到外或显露，与'打乱'表示破坏条理的结果补语语义冲突，不能连用。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "你把亂我的思路打。",
        "is_correct": false
      },
      {
        "text": "你把我的思路打亂出來。",
        "is_correct": false
      },
      {
        "text": "你把我的思路打亂了。",
        "is_correct": true
      },
      {
        "text": "你把我的思路打亂著。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：'著'表示動作持續或狀態保持，但'打亂'是瞬間完成的結果，不能用'著'，應使用'了'。 語序錯誤：結果補語'亂'必須緊跟在動詞'打'之後，不能放在賓語'我的思路'前面。 方向/結果補語誤用：'出來'表示從內到外或顯露，與'打亂'表示破壞條理的結果補語語義衝突，不能連用。",
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
    "杂乱",
    "潦草",
    "整齐",
    "松散"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义：指事物有条理、有秩序，与「没有条理、混乱」正好相反"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "雜亂",
      "潦草",
      "整齊",
      "鬆散"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義：指事物有條理、有秩序，與「沒有條理、混亂」正好相反"
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
    "杂乱",
    "整齐",
    "模糊",
    "复杂"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指事物没有条理、秩序或混乱的状态。",
      "explanation": "反义：指事物有条理、有秩序，与'乱'的混乱义正好相反"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "雜亂",
      "整齊",
      "模糊",
      "複雜"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指事物沒有條理、秩序或混亂的狀態。",
        "explanation": "反義：指事物有條理、有秩序，與'亂'的混亂義正好相反"
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

---

## sense 19860, level 7

#### Pack A
### Level 7 (sense 19860, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他的心情最近很乱。",
      "is_correct": true
    },
    {
      "text": "别把我的心弄乱。",
      "is_correct": true
    },
    {
      "text": "他把房间弄了乱。",
      "is_correct": false,
      "error_description": "在“动词+结果补语”结构中，动态助词“了”应放在整个动补结构之后，不能插在动词和补语之间。"
    },
    {
      "text": "数据要干净，不能乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他的心情最近很亂。",
        "is_correct": true
      },
      {
        "text": "別把我的心弄亂。",
        "is_correct": true
      },
      {
        "text": "他把房間弄了亂。",
        "is_correct": false,
        "error_description": "在“動詞+結果補語”結構中，動態助詞“了”應放在整個動補結構之後，不能插在動詞和補語之間。"
      },
      {
        "text": "資料要乾淨，不能亂。",
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
      "text": "别把简单的计划弄乱。",
      "is_correct": true
    },
    {
      "text": "他把弄乱了房间。",
      "is_correct": false,
      "error_description": "“把”字句语序错误。宾语应该放在“把”和动词之间，正确结构为“把+宾语+动词+结果补语”。"
    },
    {
      "text": "她心里乱得像一团麻。",
      "is_correct": true
    },
    {
      "text": "我们不怕困难，也不怕乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "別把簡單的計劃弄亂。",
        "is_correct": true
      },
      {
        "text": "他把弄亂了房間。",
        "is_correct": false,
        "error_description": "“把”字句語序錯誤。賓語應該放在“把”和動詞之間，正確結構為“把+賓語+動詞+結果補語”。"
      },
      {
        "text": "她心裡亂得像一團麻。",
        "is_correct": true
      },
      {
        "text": "我們不怕困難，也不怕亂。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19860, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这篇文章的逻辑太乱了。",
      "is_correct": true
    },
    {
      "text": "大家七嘴八舌，把会场搞乱了。",
      "is_correct": true
    },
    {
      "text": "他把弄乱了房间，妈妈很生气。",
      "is_correct": false,
      "error_description": "“把”字句中，宾语应放在“把”字之后、动词之前，不能放在动补结构之后。"
    },
    {
      "text": "聚会结束后，现场变得很乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這篇文章的邏輯太亂了。",
        "is_correct": true
      },
      {
        "text": "大家七嘴八舌，把會場搞亂了。",
        "is_correct": true
      },
      {
        "text": "他把弄亂了房間，媽媽很生氣。",
        "is_correct": false,
        "error_description": "“把”字句中，賓語應放在“把”字之後、動詞之前，不能放在動補結構之後。"
      },
      {
        "text": "聚會結束後，現場變得很亂。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 19867, level 1

#### Pack A
### Level 1 (sense 19867, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "才",
  "pronunciation": "cái",
  "ipa": "[t͡sʰaɪ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "踩",
    "才",
    "猜",
    "菜"
  ],
  "correct_answer": "才",
  "explanation": "正确：“才”读第二声（cái），在此作副词，表示事情刚刚发生。",
  "distractor_explanations": {
    "猜": "声调错误：“猜”读第一声（cāi），意思是推测；而目标词“才”读第二声（cái）。",
    "踩": "声调错误：“踩”读第三声（cǎi），意思是用脚践踏；而目标词“才”读第二声（cái）。",
    "菜": "声调错误：“菜”读第四声（cài），意思是蔬菜或菜肴；而目标词“才”读第二声（cái）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "才",
    "pronunciation": "cái",
    "ipa": "[t͡sʰaɪ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "踩",
      "才",
      "猜",
      "菜"
    ],
    "correct_answer": "才",
    "explanation": "正確：“才”讀第二聲（cái），在此作副詞，表示事情剛剛發生。",
    "distractor_explanations": {
      "猜": "聲調錯誤：“猜”讀第一聲（cāi），意思是推測；而目標詞“才”讀第二聲（cái）。",
      "踩": "聲調錯誤：“踩”讀第三聲（cǎi），意思是用腳踐踏；而目標詞“才”讀第二聲（cái）。",
      "菜": "聲調錯誤：“菜”讀第四聲（cài），意思是蔬菜或菜餚；而目標詞“才”讀第二聲（cái）。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19867, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "才",
  "pronunciation": "cái",
  "ipa": "[t͡sʰai˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "菜",
    "才",
    "采",
    "猜"
  ],
  "correct_answer": "才",
  "explanation": "声调为阳平，副词，表示事情刚刚发生，为正确选项。",
  "distractor_explanations": {
    "猜": "声调为阴平，意为猜测，与目标词阳平声调不同。",
    "采": "声调为上声，意为采摘或采集，与目标词阳平声调不同。",
    "菜": "声调为去声，意为蔬菜，与目标词阳平声调不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "才",
    "pronunciation": "cái",
    "ipa": "[t͡sʰai˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "菜",
      "才",
      "採",
      "猜"
    ],
    "correct_answer": "才",
    "explanation": "聲調為陽平，副詞，表示事情剛剛發生，為正確選項。",
    "distractor_explanations": {
      "猜": "聲調為陰平，意為猜測，與目標詞陽平聲調不同。",
      "采": "聲調為上聲，意為採摘或採集，與目標詞陽平聲調不同。",
      "菜": "聲調為去聲，意為蔬菜，與目標詞陽平聲調不同。"
    },
    "distractor_source": "llm"
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

#### Pack B
### Level 6 (sense 19867, difficulty None)
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "才",
  "relation": "antonym",
  "options": [
    "已经",
    "还",
    "正",
    "刚"
  ],
  "correct_answer": "已经",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示事情发生或结束得早，或强调事情刚刚发生。",
      "explanation": "反义项：「已经」表示动作已完成或早已发生，与「才」表刚刚发生构成反义"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "已經",
      "還",
      "正",
      "剛"
    ],
    "correct_answer": "已經",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示事情發生或結束得早，或強調事情剛剛發生。",
        "explanation": "反義項：「已經」表示動作已完成或早已發生，與「才」表剛剛發生構成反義"
      }
    }
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

#### Pack B
### Level 1 (sense 19870, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "也",
  "pronunciation": "yě",
  "ipa": "[jɛ˨˩˦]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "也",
    "爷",
    "夜",
    "椰"
  ],
  "correct_answer": "也",
  "explanation": "正确。读音为第三声（yě），表示同样或并列。",
  "distractor_explanations": {
    "椰": "声调不同。“椰”读第一声（yē），指椰子；“也”读第三声（yě）。",
    "爷": "声调不同。“爷”读第二声（yé），指爷爷或长辈；“也”读第三声（yě）。",
    "夜": "声调不同。“夜”读第四声（yè），指夜晚；“也”读第三声（yě）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "也",
    "pronunciation": "yě",
    "ipa": "[jɛ˨˩˦]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "也",
      "爺",
      "夜",
      "椰"
    ],
    "correct_answer": "也",
    "explanation": "正確。讀音為第三聲（yě），表示同樣或並列。",
    "distractor_explanations": {
      "椰": "聲調不同。“椰”讀第一聲（yē），指椰子；“也”讀第三聲（yě）。",
      "爷": "聲調不同。“爺”讀第二聲（yé），指爺爺或長輩；“也”讀第三聲（yě）。",
      "夜": "聲調不同。“夜”讀第四聲（yè），指夜晚；“也”讀第三聲（yě）。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19870, level 3

#### Pack A
### Level 3 (sense 19870, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "这么简单的问题，连他___不会。",
  "original_sentence": "这么简单的问题，连他也不会。",
  "correct_answer": "也",
  "options": [
    "未",
    "也",
    "刚",
    "又"
  ],
  "explanation": "正确。“连……也……”是固定句式，表示强调，此处填入“也”表示同样不会。",
  "distractor_tags": {},
  "word_definition": "副词。表示同样、并列或加强语气。",
  "target_word": "也",
  "hant": {
    "sentence_with_blank": "這麼簡單的問題，連他___不會。",
    "original_sentence": "這麼簡單的問題，連他也不會。",
    "correct_answer": "也",
    "options": [
      "未",
      "也",
      "剛",
      "又"
    ],
    "explanation": "正確。“連……也……”是固定句式，表示強調，此處填入“也”表示同樣不會。",
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

## sense 19882, level 3

#### Pack A
### Level 3 (sense 19882, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "说清楚，才能让别人觉得你很___。",
  "original_sentence": "说清楚，才能让别人觉得你很诚实。",
  "correct_answer": "诚实",
  "options": [
    "伟大",
    "虚伪",
    "聪明",
    "诚实"
  ],
  "explanation": "正确。“说清楚”体现了不隐瞒、不欺骗的品质，与“诚实”的语义完美契合。",
  "distractor_tags": {},
  "word_definition": "指言行与内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "說清楚，才能讓別人覺得你很___。",
    "original_sentence": "說清楚，才能讓別人覺得你很誠實。",
    "correct_answer": "誠實",
    "options": [
      "偉大",
      "虛偽",
      "聰明",
      "誠實"
    ],
    "explanation": "正確。“說清楚”體現了不隱瞞、不欺騙的品質，與“誠實”的語義完美契合。",
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
      "text": "老师表扬了他的诚实和勇敢。",
      "is_correct": true
    },
    {
      "text": "老师表扬了他的诚实的勇敢。",
      "is_correct": false
    },
    {
      "text": "老师表扬了他的诚实和勇敢过。",
      "is_correct": false
    },
    {
      "text": "老师表扬了他的诚实得很勇敢。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置错误。动态助词“过”不能放在名词性短语“诚实和勇敢”之后，应放在动词“表扬”之后，如“表扬过”。 语序与结构错误。连用两个“的”破坏了并列结构，应使用连词“和”连接“诚实”与“勇敢”。 句法结构错误。“得很”用于形容词后作程度补语，不能连接两个并列的形容词，导致句子结构混乱。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "老師表揚了他的誠實和勇敢。",
        "is_correct": true
      },
      {
        "text": "老師表揚了他的誠實的勇敢。",
        "is_correct": false
      },
      {
        "text": "老師表揚了他的誠實和勇敢過。",
        "is_correct": false
      },
      {
        "text": "老師表揚了他的誠實得很勇敢。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置錯誤。動態助詞“過”不能放在名詞性短語“誠實和勇敢”之後，應放在動詞“表揚”之後，如“表揚過”。 語序與結構錯誤。連用兩個“的”破壞了並列結構，應使用連詞“和”連線“誠實”與“勇敢”。 句法結構錯誤。“得很”用於形容詞後作程度補語，不能連線兩個並列的形容詞，導致句子結構混亂。",
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
    "谦虚",
    "善良",
    "勇敢",
    "虚伪"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指言行与内心一致，不虚假。",
      "explanation": "成立：指不真实、做作，与目标词言行一致不虚假构成反义关系。"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "謙虛",
      "善良",
      "勇敢",
      "虛偽"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指言行與內心一致，不虛假。",
        "explanation": "成立：指不真實、做作，與目標詞言行一致不虛假構成反義關係。"
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
      "text": "她诚实地说出了事情的真相了。",
      "is_correct": false
    },
    {
      "text": "她诚实地说出了事情的真相。",
      "is_correct": true
    },
    {
      "text": "诚实地她说出了事情的真相。",
      "is_correct": false
    },
    {
      "text": "她诚实说出了事情的真相。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误：'了'表示动作完成，但'说出'本身已包含结果补语'出'，句末再加'了'显得冗余且不符合表达习惯，应去掉句末的'了'。 语序/结构错误：'诚实'是形容词，修饰动词'说出'时，必须加上结构助词'地'作状语，即'诚实地说出'，直接修饰不符合语法规范。 语序错误：状语'诚实地'应该放在主语'她'之后、谓语动词'说出'之前，放在主语之前破坏了正常的'主—状—谓'语序。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "她誠實地說出了事情的真相了。",
        "is_correct": false
      },
      {
        "text": "她誠實地說出了事情的真相。",
        "is_correct": true
      },
      {
        "text": "誠實地她說出了事情的真相。",
        "is_correct": false
      },
      {
        "text": "她誠實說出了事情的真相。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤：'了'表示動作完成，但'說出'本身已包含結果補語'出'，句末再加'了'顯得冗餘且不符合表達習慣，應去掉句末的'了'。 語序/結構錯誤：'誠實'是形容詞，修飾動詞'說出'時，必須加上結構助詞'地'作狀語，即'誠實地說出'，直接修飾不符合語法規範。 語序錯誤：狀語'誠實地'應該放在主語'她'之後、謂語動詞'說出'之前，放在主語之前破壞了正常的'主—狀—謂'語序。",
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
    "固执",
    "虚伪",
    "善良",
    "勇敢"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "指言行与内心一致，不虚假。",
      "explanation": "反义项：指表里不一、不真实，与“言行与内心一致”构成反义。"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "固執",
      "虛偽",
      "善良",
      "勇敢"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "指言行與內心一致，不虛假。",
        "explanation": "反義項：指表裡不一、不真實，與“言行與內心一致”構成反義。"
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

#### Pack B
### Level 7 (sense 19882, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "诚实是人际交往中最重要的品质。",
      "is_correct": true
    },
    {
      "text": "我们要把诚实放在第一位。",
      "is_correct": true
    },
    {
      "text": "我们要把第一位放在诚实。",
      "is_correct": false,
      "error_description": "“把”字句的宾语应为被处置的对象“诚实”，而不是位置“第一位”。正确语序为“把+宾语+动词+在+位置”。"
    },
    {
      "text": "她诚实地说出了事情的真相。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "誠實是人際交往中最重要的品質。",
        "is_correct": true
      },
      {
        "text": "我們要把誠實放在第一位。",
        "is_correct": true
      },
      {
        "text": "我們要把第一位放在誠實。",
        "is_correct": false,
        "error_description": "“把”字句的賓語應為被處置的物件“誠實”，而不是位置“第一位”。正確語序為“把+賓語+動詞+在+位置”。"
      },
      {
        "text": "她誠實地說出了事情的真相。",
        "is_correct": true
      }
    ]
  }
}
```

---
