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


## sense 19867, level 1

#### Pack A
### Level 1 (sense 19867, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "才",
  "pronunciation": "cái",
  "ipa": "[t͡sʰaɪ˧˥]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "才",
    "采",
    "猜",
    "菜"
  ],
  "correct_answer": "才",
  "explanation": "正确：“才”读第二声（cái），符合听到的语音。",
  "distractor_explanations": {
    "猜": "声调错误：“猜”读第一声（cāi），意为推测；而目标词“才”读第二声（cái）。",
    "采": "声调错误：“采”读第三声（cǎi），意为摘取或收集；而目标词“才”读第二声（cái）。",
    "菜": "声调错误：“菜”读第四声（cài），指蔬菜或菜肴；而目标词“才”读第二声（cái）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "才",
    "pronunciation": "cái",
    "ipa": "[t͡sʰaɪ˧˥]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "才",
      "採",
      "猜",
      "菜"
    ],
    "correct_answer": "才",
    "explanation": "正確：“才”讀第二聲（cái），符合聽到的語音。",
    "distractor_explanations": {
      "猜": "聲調錯誤：“猜”讀第一聲（cāi），意為推測；而目標詞“才”讀第二聲（cái）。",
      "采": "聲調錯誤：“採”讀第三聲（cǎi），意為摘取或收集；而目標詞“才”讀第二聲（cái）。",
      "菜": "聲調錯誤：“菜”讀第四聲（cài），指蔬菜或菜餚；而目標詞“才”讀第二聲（cái）。"
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
      "text": "天刚亮，他才起床去跑步。",
      "is_correct": true
    },
    {
      "text": "才他天刚亮起床去跑步。",
      "is_correct": false
    },
    {
      "text": "他才刚亮天起床去跑步。",
      "is_correct": false
    },
    {
      "text": "他才着起床去跑步。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：时间状语“天刚亮”被错误地拆分并放在了副词“才”和动词“起床”之间，破坏了正常的句法结构。 体标选用错误：动态助词“着”表示动作持续，不能用在表示瞬间动作的“起床”前，且与“才”强调刚发生的语义冲突。 语序错误：副词“才”被错误地放置在主语“他”之前，违反了汉语副词通常位于主语之后、谓语之前的语序规则。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "天剛亮，他才起床去跑步。",
        "is_correct": true
      },
      {
        "text": "才他天剛亮起床去跑步。",
        "is_correct": false
      },
      {
        "text": "他才剛亮天起床去跑步。",
        "is_correct": false
      },
      {
        "text": "他才著起床去跑步。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：時間狀語“天剛亮”被錯誤地拆分並放在了副詞“才”和動詞“起床”之間，破壞了正常的句法結構。 體標選用錯誤：動態助詞“著”表示動作持續，不能用在表示瞬間動作的“起床”前，且與“才”強調剛發生的語義衝突。 語序錯誤：副詞“才”被錯誤地放置在主語“他”之前，違反了漢語副詞通常位於主語之後、謂語之前的語序規則。",
    "target_word": "才"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "才",
  "relation": "antonym",
  "options": [
    "已",
    "将",
    "常",
    "正"
  ],
  "correct_answer": "已",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示事情发生或结束得早，或强调事情刚刚发生。",
      "explanation": "反义项：表示动作已完成，与表刚刚发生的“才”相对"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "已",
      "將",
      "常",
      "正"
    ],
    "correct_answer": "已",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示事情發生或結束得早，或強調事情剛剛發生。",
        "explanation": "反義項：表示動作已完成，與表剛剛發生的“才”相對"
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
      "text": "他才五岁，就喜欢看着小动物。",
      "is_correct": true
    },
    {
      "text": "他才五岁，就喜欢看着小动物了过。",
      "is_correct": false
    },
    {
      "text": "才他五岁，就喜欢看着小动物。",
      "is_correct": false
    },
    {
      "text": "他才五岁，就喜欢看着只小动物。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：“只”通常用于动物，但“小动物”是一个泛指名词短语，前面不应加个体量词“只”，应直接说“看着小动物”或“看着一只小动物”。 体标位置/选用错误：句末的“了过”是错误的体标记连用。表示过去的经历应使用“过”，且“喜欢”后接动作时不需要在句末加“了过”，应改为“就喜欢看小动物了”或直接去掉“了过”。 语序错误：副词“才”修饰数量词“五岁”时，必须放在主语“他”之后、数量词之前，不能放在主语前面，正确语序应为“他才五岁”。",
  "target_word": "才",
  "hant": {
    "sentences": [
      {
        "text": "他才五歲，就喜歡看著小動物。",
        "is_correct": true
      },
      {
        "text": "他才五歲，就喜歡看著小動物了過。",
        "is_correct": false
      },
      {
        "text": "才他五歲，就喜歡看著小動物。",
        "is_correct": false
      },
      {
        "text": "他才五歲，就喜歡看著只小動物。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：“只”通常用於動物，但“小動物”是一個泛指名詞短語，前面不應加個體量詞“只”，應直接說“看著小動物”或“看著一隻小動物”。 體標位置/選用錯誤：句末的“了過”是錯誤的體標記連用。表示過去的經歷應使用“過”，且“喜歡”後接動作時不需要在句末加“了過”，應改為“就喜歡看小動物了”或直接去掉“了過”。 語序錯誤：副詞“才”修飾數量詞“五歲”時，必須放在主語“他”之後、數量詞之前，不能放在主語前面，正確語序應為“他才五歲”。",
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
    "再",
    "已经",
    "刚",
    "还"
  ],
  "correct_answer": "已经",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词，表示事情发生或结束得早，或强调事情刚刚发生。",
      "explanation": "反义：「才」表刚刚发生，「已经」表动作已完成，二者在时间早晚上相对"
    }
  },
  "hant": {
    "word": "才",
    "relation": "antonym",
    "options": [
      "再",
      "已經",
      "剛",
      "還"
    ],
    "correct_answer": "已經",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞，表示事情發生或結束得早，或強調事情剛剛發生。",
        "explanation": "反義：「才」表剛剛發生，「已經」表動作已完成，二者在時間早晚上相對"
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
      "text": "他把房间才打扫完，还没弄完呢。",
      "is_correct": false,
      "error_description": "语序错误。副词“才”应该放在“把”字之前，即主语之后、“把”字句结构之前，不能放在“把”和宾语之后。"
    },
    {
      "text": "我才吃过饭，现在还不饿。",
      "is_correct": true
    },
    {
      "text": "他才八岁，就已经学过钢琴了。",
      "is_correct": true
    },
    {
      "text": "他才把作业写完，正看着电视呢。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他把房間才打掃完，還沒弄完呢。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“才”應該放在“把”字之前，即主語之後、“把”字句結構之前，不能放在“把”和賓語之後。"
      },
      {
        "text": "我才吃過飯，現在還不餓。",
        "is_correct": true
      },
      {
        "text": "他才八歲，就已經學過鋼琴了。",
        "is_correct": true
      },
      {
        "text": "他才把作業寫完，正看著電視呢。",
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
      "text": "他才到，衣服上还淋着雨呢。",
      "is_correct": true
    },
    {
      "text": "他才五岁，就喜欢看着小动物。",
      "is_correct": true
    },
    {
      "text": "他才把房间打扫了完。",
      "is_correct": false,
      "error_description": "体标位置错误。在“把”字句中，结果补语“完”前面不能加动态助词“了”，“了”应放在句末或直接省略。"
    },
    {
      "text": "他才十岁，就把这本书读过了。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他才到，衣服上還淋著雨呢。",
        "is_correct": true
      },
      {
        "text": "他才五歲，就喜歡看著小動物。",
        "is_correct": true
      },
      {
        "text": "他才把房間打掃了完。",
        "is_correct": false,
        "error_description": "體標位置錯誤。在“把”字句中，結果補語“完”前面不能加動態助詞“了”，“了”應放在句末或直接省略。"
      },
      {
        "text": "他才十歲，就把這本書讀過了。",
        "is_correct": true
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
**phonetic_recognition** variant `A`, tier `T3`
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
    "椰",
    "夜"
  ],
  "correct_answer": "也",
  "explanation": "正确。读音为第三声（yě），表示同样或并列。",
  "distractor_explanations": {
    "椰": "声调错误。“椰”读第一声（yē），常用于“椰子”等词，而目标词“也”读第三声（yě）。",
    "爷": "声调错误。“爷”读第二声（yé），常用于“爷爷”等词，而目标词“也”读第三声（yě）。",
    "夜": "声调错误。“夜”读第四声（yè），常用于“夜晚”等词，而目标词“也”读第三声（yě）。"
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
      "椰",
      "夜"
    ],
    "correct_answer": "也",
    "explanation": "正確。讀音為第三聲（yě），表示同樣或並列。",
    "distractor_explanations": {
      "椰": "聲調錯誤。“椰”讀第一聲（yē），常用於“椰子”等詞，而目標詞“也”讀第三聲（yě）。",
      "爷": "聲調錯誤。“爺”讀第二聲（yé），常用於“爺爺”等詞，而目標詞“也”讀第三聲（yě）。",
      "夜": "聲調錯誤。“夜”讀第四聲（yè），常用於“夜晚”等詞，而目標詞“也”讀第三聲（yě）。"
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

#### Pack B
### Level 3 (sense 19870, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "我___很喜欢参加学校的社交活动。",
  "original_sentence": "我也很喜欢参加学校的社交活动。",
  "correct_answer": "也",
  "options": [
    "都",
    "也",
    "才",
    "就"
  ],
  "explanation": "正确。“也”表示同样，说明说话人与他人一样喜欢参加社交活动。",
  "distractor_tags": {},
  "word_definition": "副词。表示同样、并列或加强语气。",
  "target_word": "也",
  "hant": {
    "sentence_with_blank": "我___很喜歡參加學校的社交活動。",
    "original_sentence": "我也很喜歡參加學校的社交活動。",
    "correct_answer": "也",
    "options": [
      "都",
      "也",
      "才",
      "就"
    ],
    "explanation": "正確。“也”表示同樣，說明說話人與他人一樣喜歡參加社交活動。",
    "distractor_tags": {},
    "word_definition": "副詞。表示同樣、並列或加強語氣。",
    "target_word": "也"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我把这个有趣的观点___告诉了他。",
  "original_sentence": "我把这个有趣的观点也告诉了他。",
  "correct_answer": "也",
  "options": [
    "正",
    "瞎",
    "也",
    "白"
  ],
  "explanation": "正确。'也'表示同样，说明除了别人之外，'我'同样把这个观点告诉了他。",
  "distractor_tags": {},
  "word_definition": "副词。表示同样、并列或加强语气。",
  "target_word": "也",
  "hant": {
    "sentence_with_blank": "我把這個有趣的觀點___告訴了他。",
    "original_sentence": "我把這個有趣的觀點也告訴了他。",
    "correct_answer": "也",
    "options": [
      "正",
      "瞎",
      "也",
      "白"
    ],
    "explanation": "正確。'也'表示同樣，說明除了別人之外，'我'同樣把這個觀點告訴了他。",
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
      "text": "妹妹也参加了同学的生日聚会想。",
      "is_correct": false
    },
    {
      "text": "妹妹去也参加同学的生日聚会想。",
      "is_correct": false
    },
    {
      "text": "也妹妹想去参加同学的生日聚会。",
      "is_correct": false
    },
    {
      "text": "妹妹也想去参加同学的生日聚会。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误：副词“也”应放在主要动词“想”之前，不能放在连动结构的第一个动词后，且句末助动词“想”位置错误。 语序错误：助动词“想”表示意愿，应放在动词“参加”之前，原句将“想”置于句末导致语法结构破坏。 语序错误：副词“也”不能放在主语“妹妹”之前，必须放在主语之后、谓语动词或助动词之前。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "妹妹也參加了同學的生日聚會想。",
        "is_correct": false
      },
      {
        "text": "妹妹去也參加同學的生日聚會想。",
        "is_correct": false
      },
      {
        "text": "也妹妹想去參加同學的生日聚會。",
        "is_correct": false
      },
      {
        "text": "妹妹也想去參加同學的生日聚會。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤：副詞“也”應放在主要動詞“想”之前，不能放在連動結構的第一個動詞後，且句末助動詞“想”位置錯誤。 語序錯誤：助動詞“想”表示意願，應放在動詞“參加”之前，原句將“想”置於句末導致語法結構破壞。 語序錯誤：副詞“也”不能放在主語“妹妹”之前，必須放在主語之後、謂語動詞或助動詞之前。",
    "target_word": "也"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "也",
  "relation": "antonym",
  "options": [
    "才",
    "就",
    "只",
    "都"
  ],
  "correct_answer": "只",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词。表示同样、并列或加强语气。",
      "explanation": "反义：'也'表同样并列，'只'表限定排除，二者在范围上构成反义"
    }
  },
  "hant": {
    "word": "也",
    "relation": "antonym",
    "options": [
      "才",
      "就",
      "只",
      "都"
    ],
    "correct_answer": "只",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞。表示同樣、並列或加強語氣。",
        "explanation": "反義：'也'表同樣並列，'只'表限定排除，二者在範圍上構成反義"
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
      "text": "她也连最难的数学题做出来了。",
      "is_correct": false
    },
    {
      "text": "连最难的数学题她也做出来了过。",
      "is_correct": false
    },
    {
      "text": "连最难的数学题做出来她也了。",
      "is_correct": false
    },
    {
      "text": "连最难的数学题她也做出来了。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：动态助词'了'应紧跟在动词'做'或动补结构'做出来'之后，不能放在主语'她'之后。 语序错误：'连'字句用于强调极端情况，'连+宾语'必须放在副词'也'之前，以突出强调的对象。 体标选用错误：句末的'了'表示动作完成或状态实现，而'过'表示过去的经历，两者连用导致体貌标记冲突。",
  "target_word": "也",
  "hant": {
    "sentences": [
      {
        "text": "她也連最難的數學題做出來了。",
        "is_correct": false
      },
      {
        "text": "連最難的數學題她也做出來了過。",
        "is_correct": false
      },
      {
        "text": "連最難的數學題做出來她也了。",
        "is_correct": false
      },
      {
        "text": "連最難的數學題她也做出來了。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：動態助詞'了'應緊跟在動詞'做'或動補結構'做出來'之後，不能放在主語'她'之後。 語序錯誤：'連'字句用於強調極端情況，'連+賓語'必須放在副詞'也'之前，以突出強調的物件。 體標選用錯誤：句末的'了'表示動作完成或狀態實現，而'過'表示過去的經歷，兩者連用導致體貌標記衝突。",
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
    "都",
    "只",
    "就",
    "又"
  ],
  "correct_answer": "只",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "副词。表示同样、并列或加强语气。",
      "explanation": "反义项：表示限制范围，与“也”表示的同样、并列相对"
    }
  },
  "hant": {
    "word": "也",
    "relation": "antonym",
    "options": [
      "都",
      "只",
      "就",
      "又"
    ],
    "correct_answer": "只",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "副詞。表示同樣、並列或加強語氣。",
        "explanation": "反義項：表示限制範圍，與“也”表示的同樣、並列相對"
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
      "text": "他也觉得这个观点非常有道理。",
      "is_correct": true
    },
    {
      "text": "我昨天去图书馆也借了两本书。",
      "is_correct": false,
      "error_description": "语序错误。副词“也”通常应放在主语之后、主要动词之前。当句中有时间状语时，“也”应放在时间状语之后、动词之前，不能放在动词之后。"
    },
    {
      "text": "周末我们也去公园散步了。",
      "is_correct": true
    },
    {
      "text": "我也很喜欢参加学校的社交活动。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他也覺得這個觀點非常有道理。",
        "is_correct": true
      },
      {
        "text": "我昨天去圖書館也借了兩本書。",
        "is_correct": false,
        "error_description": "語序錯誤。副詞“也”通常應放在主語之後、主要動詞之前。當句中有時間狀語時，“也”應放在時間狀語之後、動詞之前，不能放在動詞之後。"
      },
      {
        "text": "週末我們也去公園散步了。",
        "is_correct": true
      },
      {
        "text": "我也很喜歡參加學校的社交活動。",
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
      "text": "连最难的数学题她也做出来了。",
      "is_correct": true
    },
    {
      "text": "他把那本感人的小说也看完了。",
      "is_correct": true
    },
    {
      "text": "我把也那本感人的小说看完了。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，副词“也”不能放在“把”字和宾语之间，而应该放在“把”字之前（如“我也把……”）或主要动词之前（如“把……也看完了”）。"
    },
    {
      "text": "我把这个有趣的观点也告诉了他。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "連最難的數學題她也做出來了。",
        "is_correct": true
      },
      {
        "text": "他把那本感人的小說也看完了。",
        "is_correct": true
      },
      {
        "text": "我把也那本感人的小說看完了。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，副詞“也”不能放在“把”字和賓語之間，而應該放在“把”字之前（如“我也把……”）或主要動詞之前（如“把……也看完了”）。"
      },
      {
        "text": "我把這個有趣的觀點也告訴了他。",
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
    "聪明",
    "活泼",
    "诚实",
    "勇敢"
  ],
  "explanation": "正确。句意是表达清楚事实，体现不虚假的品质。",
  "distractor_tags": {},
  "word_definition": "言行和内心一致，不虚假。",
  "target_word": "诚实",
  "hant": {
    "sentence_with_blank": "說清楚，才能讓別人覺得你很___。",
    "original_sentence": "說清楚，才能讓別人覺得你很誠實。",
    "correct_answer": "誠實",
    "options": [
      "聰明",
      "活潑",
      "誠實",
      "勇敢"
    ],
    "explanation": "正確。句意是表達清楚事實，體現不虛假的品質。",
    "distractor_tags": {},
    "word_definition": "言行和內心一致，不虛假。",
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
      "text": "他为人很诚实，从不骗人。",
      "is_correct": true
    },
    {
      "text": "很为人他诚实，从不骗人。",
      "is_correct": false
    },
    {
      "text": "他为人很诚实，从不骗人过。",
      "is_correct": false
    },
    {
      "text": "他为人诚实得很，从不骗人起。",
      "is_correct": false
    }
  ],
  "explanation": "体标错误：“诚实”是表示持久属性的状态形容词，不能与表示过去经历的动态助词“过”连用。 语序错误：程度副词“很”不能放在介词短语“为人”之前，应放在形容词“诚实”之前作状语。 补语误用：状态形容词“诚实”后不能接趋向补语“起”，“起”通常用于动作动词之后。",
  "target_word": "诚实",
  "hant": {
    "sentences": [
      {
        "text": "他為人很誠實，從不騙人。",
        "is_correct": true
      },
      {
        "text": "很為人他誠實，從不騙人。",
        "is_correct": false
      },
      {
        "text": "他為人很誠實，從不騙人過。",
        "is_correct": false
      },
      {
        "text": "他為人誠實得很，從不騙人起。",
        "is_correct": false
      }
    ],
    "explanation": "體標錯誤：“誠實”是表示持久屬性的狀態形容詞，不能與表示過去經歷的動態助詞“過”連用。 語序錯誤：程度副詞“很”不能放在介詞短語“為人”之前，應放在形容詞“誠實”之前作狀語。 補語誤用：狀態形容詞“誠實”後不能接趨向補語“起”，“起”通常用於動作動詞之後。",
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
    "虚伪",
    "善良",
    "狡猾"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "言行和内心一致，不虚假。",
      "explanation": "反义项：表里不一、做作不真实，与「言行和内心一致」相反"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "謙虛",
      "虛偽",
      "善良",
      "狡猾"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "言行和內心一致，不虛假。",
        "explanation": "反義項：表裡不一、做作不真實，與「言行和內心一致」相反"
      }
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "诚实",
  "relation": "antonym",
  "options": [
    "懒惰",
    "虚伪",
    "傲慢",
    "狡猾"
  ],
  "correct_answer": "虚伪",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "言行和内心一致，不虚假。",
      "explanation": "反义项：指言行与内心不一致，不真实，与“诚实”构成反义"
    }
  },
  "hant": {
    "word": "誠實",
    "relation": "antonym",
    "options": [
      "懶惰",
      "虛偽",
      "傲慢",
      "狡猾"
    ],
    "correct_answer": "虛偽",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "言行和內心一致，不虛假。",
        "explanation": "反義項：指言行與內心不一致，不真實，與“誠實”構成反義"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他是一个非常诚实的好孩子。",
      "is_correct": true
    },
    {
      "text": "我们要做一个诚实的人。",
      "is_correct": true
    },
    {
      "text": "说清楚，才能让别人觉得你很诚实。",
      "is_correct": true
    },
    {
      "text": "他诚实昨天说出了事情的经过。",
      "is_correct": false,
      "error_description": "语序错误。时间状语“昨天”应该放在主语之后、谓语之前，且修饰动词的形容词后应加“地”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他是一個非常誠實的好孩子。",
        "is_correct": true
      },
      {
        "text": "我們要做一個誠實的人。",
        "is_correct": true
      },
      {
        "text": "說清楚，才能讓別人覺得你很誠實。",
        "is_correct": true
      },
      {
        "text": "他誠實昨天說出了事情的經過。",
        "is_correct": false,
        "error_description": "語序錯誤。時間狀語“昨天”應該放在主語之後、謂語之前，且修飾動詞的形容詞後應加“地”。"
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
      "text": "诚实比聪明更重要。",
      "is_correct": true
    },
    {
      "text": "朋友之间保持应该诚实。",
      "is_correct": false,
      "error_description": "语序错误。能愿动词“应该”必须放在主要动词“保持”的前面，不能放在动词之后。"
    },
    {
      "text": "朋友之间应该保持诚实。",
      "is_correct": true
    },
    {
      "text": "诚实的孩子总是受人喜欢。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "誠實比聰明更重要。",
        "is_correct": true
      },
      {
        "text": "朋友之間保持應該誠實。",
        "is_correct": false,
        "error_description": "語序錯誤。能願動詞“應該”必須放在主要動詞“保持”的前面，不能放在動詞之後。"
      },
      {
        "text": "朋友之間應該保持誠實。",
        "is_correct": true
      },
      {
        "text": "誠實的孩子總是受人喜歡。",
        "is_correct": true
      }
    ]
  }
}
```

---
