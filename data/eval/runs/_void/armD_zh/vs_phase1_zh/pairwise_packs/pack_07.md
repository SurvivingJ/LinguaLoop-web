# Pairwise review pack 07

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


## sense 11531, level 7

#### Pack A
### Level 7 (sense 11531, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "树下的阳光显得很细碎。",
      "is_correct": true
    },
    {
      "text": "我听着窗外一条细碎的脚步声。",
      "is_correct": false,
      "error_description": "量词使用错误。量词“条”不能用来修饰“脚步声”，此处不需要加量词，或者可以改为“一阵”。"
    },
    {
      "text": "我听着窗外细碎的脚步声。",
      "is_correct": true
    },
    {
      "text": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "樹下的陽光顯得很細碎。",
        "is_correct": true
      },
      {
        "text": "我聽著窗外一條細碎的腳步聲。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。量詞“條”不能用來修飾“腳步聲”，此處不需要加量詞，或者可以改為“一陣”。"
      },
      {
        "text": "我聽著窗外細碎的腳步聲。",
        "is_correct": true
      },
      {
        "text": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 11531, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "阳光透过树叶，洒下了光斑细碎。",
      "is_correct": false,
      "error_description": "语序错误。形容词“细碎”作定语修饰名词“光斑”时，应放在名词前面，即“细碎的光斑”，不能放在名词后面。"
    },
    {
      "text": "阳光透过树叶，洒下细碎的光斑。",
      "is_correct": true
    },
    {
      "text": "她听着细碎的脚步声，心里有些害怕。",
      "is_correct": true
    },
    {
      "text": "城市公寓可采用密闭式蠕虫堆肥箱（vermicomposter），利用红蚯蚓（Eisenia fetida）的肠道微生物高效降解细碎厨余，产出富含植物生长激素的“黑色金子”——腐殖质浓缩液。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "陽光透過樹葉，灑下了光斑細碎。",
        "is_correct": false,
        "error_description": "語序錯誤。形容詞“細碎”作定語修飾名詞“光斑”時，應放在名詞前面，即“細碎的光斑”，不能放在名詞後面。"
      },
      {
        "text": "陽光透過樹葉，灑下細碎的光斑。",
        "is_correct": true
      },
      {
        "text": "她聽著細碎的腳步聲，心裡有些害怕。",
        "is_correct": true
      },
      {
        "text": "城市公寓可採用密閉式蠕蟲堆肥箱（vermicomposter），利用紅蚯蚓（Eisenia fetida）的腸道微生物高效降解細碎廚餘，產出富含植物生長激素的“黑色金子”——腐殖質濃縮液。",
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
      "text": "她听着细碎的脚步声，心里有些害怕了。",
      "is_correct": false,
      "error_description": "体标位置/选用错误。形容词“害怕”表示心理状态，在此处不需要加动态助词“了”来表示动作完成或状态改变，直接说“有些害怕”即可。"
    },
    {
      "text": "这些声音听起来很细碎。",
      "is_correct": true
    },
    {
      "text": "我喜欢收集那些细碎的小物件。",
      "is_correct": true
    },
    {
      "text": "那些细碎的往事，我都记得。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "她聽著細碎的腳步聲，心裡有些害怕了。",
        "is_correct": false,
        "error_description": "體標位置/選用錯誤。形容詞“害怕”表示心理狀態，在此處不需要加動態助詞“了”來表示動作完成或狀態改變，直接說“有些害怕”即可。"
      },
      {
        "text": "這些聲音聽起來很細碎。",
        "is_correct": true
      },
      {
        "text": "我喜歡收集那些細碎的小物件。",
        "is_correct": true
      },
      {
        "text": "那些細碎的往事，我都記得。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 12012, level 6

#### Pack A
### Level 6 (sense 12012, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "大家都不敢说话，气氛剑拔弩张。",
      "is_correct": false
    },
    {
      "text": "气氛剑拔弩张，大家都不敢说话。",
      "is_correct": true
    },
    {
      "text": "气氛剑拔弩张着，大家都不敢说话。",
      "is_correct": false
    },
    {
      "text": "剑拔弩张气氛，大家都不敢说话。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“剑拔弩张”是状态形容词，表示一种静态的紧张局势，不能加动态助词“着”来表示动作或状态的持续。 语序错误。状态形容词“剑拔弩张”作定语修饰名词“气氛”时，必须加结构助词“的”，不能直接前置组合。 语序错误。原句“气氛”是主题，“剑拔弩张”是评论。将评论前置、主题后置破坏了汉语“主题—评论”的自然语序和逻辑连贯性。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "大家都不敢說話，氣氛劍拔弩張。",
        "is_correct": false
      },
      {
        "text": "氣氛劍拔弩張，大家都不敢說話。",
        "is_correct": true
      },
      {
        "text": "氣氛劍拔弩張著，大家都不敢說話。",
        "is_correct": false
      },
      {
        "text": "劍拔弩張氣氛，大家都不敢說話。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“劍拔弩張”是狀態形容詞，表示一種靜態的緊張局勢，不能加動態助詞“著”來表示動作或狀態的持續。 語序錯誤。狀態形容詞“劍拔弩張”作定語修飾名詞“氣氛”時，必須加結構助詞“的”，不能直接前置組合。 語序錯誤。原句“氣氛”是主題，“劍拔弩張”是評論。將評論前置、主題後置破壞了漢語“主題—評論”的自然語序和邏輯連貫性。",
    "target_word": "劍拔弩張"
  }
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "剑拔弩张",
  "relation": "antonym",
  "options": [
    "暗流涌动",
    "针锋相对",
    "势均力敌",
    "风平浪静"
  ],
  "correct_answer": "风平浪静",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方冲突或紧张对峙，一触即发的状态。",
      "explanation": "反义：形容平静无事，毫无紧张对峙之感"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "暗流湧動",
      "針鋒相對",
      "勢均力敵",
      "風平浪靜"
    ],
    "correct_answer": "風平浪靜",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方衝突或緊張對峙，一觸即發的狀態。",
        "explanation": "反義：形容平靜無事，毫無緊張對峙之感"
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
      "text": "他们剑拔弩张得瞪着对方。",
      "is_correct": false
    },
    {
      "text": "他们剑拔弩张着了对方。",
      "is_correct": false
    },
    {
      "text": "他们剑拔弩张地瞪着对方。",
      "is_correct": true
    },
    {
      "text": "对方剑拔弩张他们瞪着。",
      "is_correct": false
    }
  ],
  "explanation": "体标误用：'剑拔弩张'是表示状态的形容词，不能带动态助词'着'，也不能直接接宾语'对方'。 语序错误：破坏了'主题—评论'结构，'对方'作为主语应放在句首，或者使用'他们剑拔弩张地瞪着对方'。 结构助词误用：修饰动词'瞪着'应使用状语标志'地'，而不是补语标志'得'。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "他們劍拔弩張得瞪著對方。",
        "is_correct": false
      },
      {
        "text": "他們劍拔弩張著了對方。",
        "is_correct": false
      },
      {
        "text": "他們劍拔弩張地瞪著對方。",
        "is_correct": true
      },
      {
        "text": "對方劍拔弩張他們瞪著。",
        "is_correct": false
      }
    ],
    "explanation": "體標誤用：'劍拔弩張'是表示狀態的形容詞，不能帶動態助詞'著'，也不能直接接賓語'對方'。 語序錯誤：破壞了'主題—評論'結構，'對方'作為主語應放在句首，或者使用'他們劍拔弩張地瞪著對方'。 結構助詞誤用：修飾動詞'瞪著'應使用狀語標誌'地'，而不是補語標誌'得'。",
    "target_word": "劍拔弩張"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "剑拔弩张",
  "relation": "antonym",
  "options": [
    "针锋相对",
    "暗流涌动",
    "风平浪静",
    "一触即发"
  ],
  "correct_answer": "风平浪静",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容双方冲突或紧张对峙，一触即发的状态。",
      "explanation": "反义：指没有风浪，比喻平静无事，与紧张对峙的状态相反"
    }
  },
  "hant": {
    "word": "劍拔弩張",
    "relation": "antonym",
    "options": [
      "針鋒相對",
      "暗流湧動",
      "風平浪靜",
      "一觸即發"
    ],
    "correct_answer": "風平浪靜",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容雙方衝突或緊張對峙，一觸即發的狀態。",
        "explanation": "反義：指沒有風浪，比喻平靜無事，與緊張對峙的狀態相反"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 12012, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "两人关系剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "两人关系剑拔弩张出来。",
      "is_correct": false
    },
    {
      "text": "关系两人剑拔弩张。",
      "is_correct": false
    },
    {
      "text": "两人关系剑拔弩张着。",
      "is_correct": false
    }
  ],
  "explanation": "体标选用错误。“剑拔弩张”是状态形容词，不能加动态助词“着”来表示状态的持续。 语序错误。汉语中主语“两人关系”应放在谓语“剑拔弩张”之前，不能颠倒为“关系两人”。 方向/结果补语误用。“剑拔弩张”不能带趋向补语“出来”，“出来”通常用于表示动作使某事物显露，不能用于修饰状态形容词。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "兩人關係劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "兩人關係劍拔弩張出來。",
        "is_correct": false
      },
      {
        "text": "關係兩人劍拔弩張。",
        "is_correct": false
      },
      {
        "text": "兩人關係劍拔弩張著。",
        "is_correct": false
      }
    ],
    "explanation": "體標選用錯誤。“劍拔弩張”是狀態形容詞，不能加動態助詞“著”來表示狀態的持續。 語序錯誤。漢語中主語“兩人關係”應放在謂語“劍拔弩張”之前，不能顛倒為“關係兩人”。 方向/結果補語誤用。“劍拔弩張”不能帶趨向補語“出來”，“出來”通常用於表示動作使某事物顯露，不能用於修飾狀態形容詞。",
    "target_word": "劍拔弩張"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "在竞技场剑拔弩张的对峙让人害怕。",
      "is_correct": false
    },
    {
      "text": "一个剑拔弩张的对峙让人害怕。",
      "is_correct": false
    },
    {
      "text": "剑拔弩张的对峙让人害怕。",
      "is_correct": true
    },
    {
      "text": "剑拔弩张着的对峙让人害怕。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误。介词短语“在竞技场”作定语时，应放在形容词“剑拔弩张”之前，改为“竞技场里剑拔弩张的对峙”才自然。 体标选用错误。“剑拔弩张”本身已表示完整的状态，通常不加动态助词“着”直接修饰名词，加“着”显得生硬且不自然。 量词使用错误。“对峙”作为事件或状态，通常用量词“场”或“次”修饰，使用“个”不自然。",
  "target_word": "剑拔弩张",
  "hant": {
    "sentences": [
      {
        "text": "在競技場劍拔弩張的對峙讓人害怕。",
        "is_correct": false
      },
      {
        "text": "一個劍拔弩張的對峙讓人害怕。",
        "is_correct": false
      },
      {
        "text": "劍拔弩張的對峙讓人害怕。",
        "is_correct": true
      },
      {
        "text": "劍拔弩張著的對峙讓人害怕。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤。介詞短語“在競技場”作定語時，應放在形容詞“劍拔弩張”之前，改為“競技場裡劍拔弩張的對峙”才自然。 體標選用錯誤。“劍拔弩張”本身已表示完整的狀態，通常不加動態助詞“著”直接修飾名詞，加“著”顯得生硬且不自然。 量詞使用錯誤。“對峙”作為事件或狀態，通常用量詞“場”或“次”修飾，使用“個”不自然。",
    "target_word": "劍拔弩張"
  }
}
```

---

## sense 12012, level 7

#### Pack A
### Level 7 (sense 12012, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "比赛前，双方队员把剑拔弩张。",
      "is_correct": false,
      "error_description": "“剑拔弩张”是形容词，不能直接用在“把”字句中作谓语，应去掉“把”字，直接作谓语描述主语的状态。"
    },
    {
      "text": "比赛前，双方队员剑拔弩张。",
      "is_correct": true
    },
    {
      "text": "玩家在“敌对公会”的竞技场厮杀后，可能在同一资源区合作采矿；竞争对手在排行榜上剑拔弩张，却又在社区论坛共享战术心得。",
      "is_correct": true
    },
    {
      "text": "他们剑拔弩张地争吵着。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "比賽前，雙方隊員把劍拔弩張。",
        "is_correct": false,
        "error_description": "“劍拔弩張”是形容詞，不能直接用在“把”字句中作謂語，應去掉“把”字，直接作謂語描述主語的狀態。"
      },
      {
        "text": "比賽前，雙方隊員劍拔弩張。",
        "is_correct": true
      },
      {
        "text": "玩家在“敵對公會”的競技場廝殺後，可能在同一資源區合作採礦；競爭對手在排行榜上劍拔弩張，卻又在社群論壇共享戰術心得。",
        "is_correct": true
      },
      {
        "text": "他們劍拔弩張地爭吵著。",
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
      "text": "他们争吵着剑拔弩张。",
      "is_correct": false,
      "error_description": "语序错误。'剑拔弩张' 在此处作状语修饰动词 '争吵'，应放在动词前，并使用结构助词 '地' 连接，不能放在动词之后。"
    },
    {
      "text": "局势剑拔弩张，让人紧张。",
      "is_correct": true
    },
    {
      "text": "他们剑拔弩张地瞪着对方。",
      "is_correct": true
    },
    {
      "text": "谈判桌上剑拔弩张。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他們爭吵著劍拔弩張。",
        "is_correct": false,
        "error_description": "語序錯誤。'劍拔弩張' 在此處作狀語修飾動詞 '爭吵'，應放在動詞前，並使用結構助詞 '地' 連線，不能放在動詞之後。"
      },
      {
        "text": "局勢劍拔弩張，讓人緊張。",
        "is_correct": true
      },
      {
        "text": "他們劍拔弩張地瞪著對方。",
        "is_correct": true
      },
      {
        "text": "談判桌上劍拔弩張。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 12012, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "经理把会议室的气氛剑拔弩张。",
      "is_correct": false,
      "error_description": "“把”字句的谓语不能是形容词，“剑拔弩张”不能直接作“把”字句的谓语。应去掉“经理把”，或改为“经理把会议室的气氛搞得剑拔弩张”。"
    },
    {
      "text": "他打破了剑拔弩张的局面。",
      "is_correct": true
    },
    {
      "text": "剑拔弩张的对峙让人害怕。",
      "is_correct": true
    },
    {
      "text": "竞争态势剑拔弩张。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "經理把會議室的氣氛劍拔弩張。",
        "is_correct": false,
        "error_description": "“把”字句的謂語不能是形容詞，“劍拔弩張”不能直接作“把”字句的謂語。應去掉“經理把”，或改為“經理把會議室的氣氛搞得劍拔弩張”。"
      },
      {
        "text": "他打破了劍拔弩張的局面。",
        "is_correct": true
      },
      {
        "text": "劍拔弩張的對峙讓人害怕。",
        "is_correct": true
      },
      {
        "text": "競爭態勢劍拔弩張。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 19859, level 1

#### Pack A
### Level 1 (sense 19859, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "要",
  "pronunciation": "yào",
  "ipa": "[jɑʊ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "咬",
    "要",
    "摇",
    "腰"
  ],
  "correct_answer": "要",
  "explanation": "正确。读音为第四声（yào），表示希望、需要或打算做某事。",
  "distractor_explanations": {
    "腰": "声调错误。“腰”读第一声（yāo），指身体的一部分；而目标词“要”读第四声（yào）。",
    "摇": "声调错误。“摇”读第二声（yáo），表示摆动；而目标词“要”读第四声（yào）。",
    "咬": "声调错误。“咬”读第三声（yǎo），指用牙齿夹住或切断；而目标词“要”读第四声（yào）。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "要",
    "pronunciation": "yào",
    "ipa": "[jɑʊ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "咬",
      "要",
      "搖",
      "腰"
    ],
    "correct_answer": "要",
    "explanation": "正確。讀音為第四聲（yào），表示希望、需要或打算做某事。",
    "distractor_explanations": {
      "腰": "聲調錯誤。“腰”讀第一聲（yāo），指身體的一部分；而目標詞“要”讀第四聲（yào）。",
      "摇": "聲調錯誤。“搖”讀第二聲（yáo），表示擺動；而目標詞“要”讀第四聲（yào）。",
      "咬": "聲調錯誤。“咬”讀第三聲（yǎo），指用牙齒夾住或切斷；而目標詞“要”讀第四聲（yào）。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19859, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "要",
  "pronunciation": "yào",
  "ipa": "[jɑʊ˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "要",
    "摇",
    "妖",
    "咬"
  ],
  "correct_answer": "要",
  "explanation": "正确。读 yào，表示希望、需要或请求。",
  "distractor_explanations": {
    "妖": "错误。读 yāo，指怪异的事物，声调为第一声。",
    "摇": "错误。读 yáo，指摆动、晃动，声调为第二声。",
    "咬": "错误。读 yǎo，指用牙齿夹住，声调为第三声。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "要",
    "pronunciation": "yào",
    "ipa": "[jɑʊ˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "要",
      "搖",
      "妖",
      "咬"
    ],
    "correct_answer": "要",
    "explanation": "正確。讀 yào，表示希望、需要或請求。",
    "distractor_explanations": {
      "妖": "錯誤。讀 yāo，指怪異的事物，聲調為第一聲。",
      "摇": "錯誤。讀 yáo，指擺動、晃動，聲調為第二聲。",
      "咬": "錯誤。讀 yǎo，指用牙齒夾住，聲調為第三聲。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19859, level 3

#### Pack A
### Level 3 (sense 19859, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "我周末___去图书馆看书。",
  "original_sentence": "我周末要去图书馆看书。",
  "correct_answer": "要",
  "options": [
    "敢",
    "配",
    "要",
    "必须"
  ],
  "explanation": "正确。在此句中表示主语的主观意愿或打算，符合“周末去图书馆”的语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我週末___去圖書館看書。",
    "original_sentence": "我週末要去圖書館看書。",
    "correct_answer": "要",
    "options": [
      "敢",
      "配",
      "要",
      "必須"
    ],
    "explanation": "正確。在此句中表示主語的主觀意願或打算，符合“週末去圖書館”的語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```

#### Pack B
### Level 3 (sense 19859, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "我___去图书馆借本书。",
  "original_sentence": "我要去图书馆借本书。",
  "correct_answer": "要",
  "options": [
    "要",
    "善于",
    "忙于",
    "敢于"
  ],
  "explanation": "正确。表示主观意愿或计划，符合语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我___去圖書館借本書。",
    "original_sentence": "我要去圖書館借本書。",
    "correct_answer": "要",
    "options": [
      "要",
      "善於",
      "忙於",
      "敢於"
    ],
    "explanation": "正確。表示主觀意願或計劃，符合語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "我___和你做朋友。",
  "original_sentence": "我要和你做朋友。",
  "correct_answer": "要",
  "options": [
    "许",
    "配",
    "敢",
    "要"
  ],
  "explanation": "正确选项。“要”在此处表示主观意愿，符合“和你做朋友”的积极语境。",
  "distractor_tags": {},
  "word_definition": "表示希望、需要或请求得到某物，或做某事。",
  "target_word": "要",
  "hant": {
    "sentence_with_blank": "我___和你做朋友。",
    "original_sentence": "我要和你做朋友。",
    "correct_answer": "要",
    "options": [
      "許",
      "配",
      "敢",
      "要"
    ],
    "explanation": "正確選項。“要”在此處表示主觀意願，符合“和你做朋友”的積極語境。",
    "distractor_tags": {},
    "word_definition": "表示希望、需要或請求得到某物，或做某事。",
    "target_word": "要"
  }
}
```

---

## sense 19859, level 6

#### Pack A
### Level 6 (sense 19859, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我们要买些新鲜水果。",
      "is_correct": true
    },
    {
      "text": "我们要买新鲜些水果。",
      "is_correct": false
    },
    {
      "text": "我们要买着些新鲜水果。",
      "is_correct": false
    },
    {
      "text": "我们要买一条新鲜水果。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误。'水果'不能用'条'来修饰，应使用'些'或具体的量词如'个'。 体标选用错误。'着'表示动作持续，'买'是瞬间动词，且'要'表示意愿或将来，与'着'冲突。 语序错误。数量词'些'应放在形容词'新鲜'之前，正确语序为'些新鲜水果'。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "我們要買些新鮮水果。",
        "is_correct": true
      },
      {
        "text": "我們要買新鮮些水果。",
        "is_correct": false
      },
      {
        "text": "我們要買著些新鮮水果。",
        "is_correct": false
      },
      {
        "text": "我們要買一條新鮮水果。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤。'水果'不能用'條'來修飾，應使用'些'或具體的量詞如'個'。 體標選用錯誤。'著'表示動作持續，'買'是瞬間動詞，且'要'表示意願或將來，與'著'衝突。 語序錯誤。數量詞'些'應放在形容詞'新鮮'之前，正確語序為'些新鮮水果'。",
    "target_word": "要"
  }
}
```

#### Pack B
### Level 6 (sense 19859, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "我要把礼物送给好朋友了。",
      "is_correct": false
    },
    {
      "text": "把我要礼物送给好朋友。",
      "is_correct": false
    },
    {
      "text": "我要把礼物送给好朋友。",
      "is_correct": true
    },
    {
      "text": "我要送给好朋友把礼物。",
      "is_correct": false
    }
  ],
  "explanation": "体标位置/选用错误。句中的“把”字句表示对宾语的处置，通常不与表示完成或实现的动态助词“了”直接连用在句末，应去掉“了”或改为“我已经把礼物送给好朋友了”。 语序错误。“把”字句的正确结构是“主语+把+宾语+动词+其他”，情态动词“要”必须放在“把”字之前，不能放在“把”和宾语之间。 语序错误。“把”字句的宾语必须紧跟在“把”字之后，即“把+礼物”，不能将宾语“礼物”放在动词“送给”之后。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "我要把禮物送給好朋友了。",
        "is_correct": false
      },
      {
        "text": "把我要禮物送給好朋友。",
        "is_correct": false
      },
      {
        "text": "我要把禮物送給好朋友。",
        "is_correct": true
      },
      {
        "text": "我要送給好朋友把禮物。",
        "is_correct": false
      }
    ],
    "explanation": "體標位置/選用錯誤。句中的“把”字句表示對賓語的處置，通常不與表示完成或實現的動態助詞“了”直接連用在句末，應去掉“了”或改為“我已經把禮物送給好朋友了”。 語序錯誤。“把”字句的正確結構是“主語+把+賓語+動詞+其他”，情態動詞“要”必須放在“把”字之前，不能放在“把”和賓語之間。 語序錯誤。“把”字句的賓語必須緊跟在“把”字之後，即“把+禮物”，不能將賓語“禮物”放在動詞“送給”之後。",
    "target_word": "要"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "爸爸要买一台新电脑。",
      "is_correct": true
    },
    {
      "text": "爸爸要买一匹新电脑。",
      "is_correct": false
    },
    {
      "text": "要爸爸买一台新电脑。",
      "is_correct": false
    },
    {
      "text": "爸爸买要一台新电脑。",
      "is_correct": false
    }
  ],
  "explanation": "量词使用错误：'电脑'的量词应为'台'，'匹'通常用于马、骡等动物。 语序错误：主语'爸爸'应放在情态动词'要'的前面，原句破坏了基本的主谓结构。 语序错误：情态动词'要'必须放在主要动词'买'的前面，不能放在动词之后。",
  "target_word": "要",
  "hant": {
    "sentences": [
      {
        "text": "爸爸要買一臺新電腦。",
        "is_correct": true
      },
      {
        "text": "爸爸要買一匹新電腦。",
        "is_correct": false
      },
      {
        "text": "要爸爸買一臺新電腦。",
        "is_correct": false
      },
      {
        "text": "爸爸買要一臺新電腦。",
        "is_correct": false
      }
    ],
    "explanation": "量詞使用錯誤：'電腦'的量詞應為'臺'，'匹'通常用於馬、騾等動物。 語序錯誤：主語'爸爸'應放在情態動詞'要'的前面，原句破壞了基本的主謂結構。 語序錯誤：情態動詞'要'必須放在主要動詞'買'的前面，不能放在動詞之後。",
    "target_word": "要"
  }
}
```

---

## sense 19859, level 7

#### Pack A
### Level 7 (sense 19859, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "他想要一个红色的书包。",
      "is_correct": true
    },
    {
      "text": "我要把这本书看完。",
      "is_correct": true
    },
    {
      "text": "我要去图书馆借本书。",
      "is_correct": true
    },
    {
      "text": "他要买三本红色的书包。",
      "is_correct": false,
      "error_description": "量词使用错误。“书包”的量词应该是“个”，不能用“本”。“本”通常用来修饰书、杂志等。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "他想要一個紅色的書包。",
        "is_correct": true
      },
      {
        "text": "我要把這本書看完。",
        "is_correct": true
      },
      {
        "text": "我要去圖書館借本書。",
        "is_correct": true
      },
      {
        "text": "他要買三本紅色的書包。",
        "is_correct": false,
        "error_description": "量詞使用錯誤。“書包”的量詞應該是“個”，不能用“本”。“本”通常用來修飾書、雜誌等。"
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 19859, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "弟弟要一个红色的气球。",
      "is_correct": true
    },
    {
      "text": "我周末要去图书馆看书了昨天。",
      "is_correct": false,
      "error_description": "体标位置错误。表示过去发生的动作，时间状语“昨天”应放在动词“去”之前，或者将“了”放在句末表示事态变化，不能将“了”直接放在时间状语“昨天”之前。"
    },
    {
      "text": "我周末要去图书馆看书。",
      "is_correct": true
    },
    {
      "text": "妈妈要我每天练习钢琴。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "弟弟要一個紅色的氣球。",
        "is_correct": true
      },
      {
        "text": "我週末要去圖書館看書了昨天。",
        "is_correct": false,
        "error_description": "體標位置錯誤。表示過去發生的動作，時間狀語“昨天”應放在動詞“去”之前，或者將“了”放在句末表示事態變化，不能將“了”直接放在時間狀語“昨天”之前。"
      },
      {
        "text": "我週末要去圖書館看書。",
        "is_correct": true
      },
      {
        "text": "媽媽要我每天練習鋼琴。",
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
      "text": "爸爸要买一台新电脑。",
      "is_correct": true
    },
    {
      "text": "我们要把房间打扫一下。",
      "is_correct": true
    },
    {
      "text": "老师要我们保持教室干净。",
      "is_correct": true
    },
    {
      "text": "我们要把打扫一下房间。",
      "is_correct": false,
      "error_description": "语序错误。在“把”字句中，“把”后面必须紧跟动作的受事宾语。正确的语序应该是“把 + 宾语 + 动词 + 其他成分”，因此“房间”必须放在“把”和“打扫”之间。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "爸爸要買一臺新電腦。",
        "is_correct": true
      },
      {
        "text": "我們要把房間打掃一下。",
        "is_correct": true
      },
      {
        "text": "老師要我們保持教室乾淨。",
        "is_correct": true
      },
      {
        "text": "我們要把打掃一下房間。",
        "is_correct": false,
        "error_description": "語序錯誤。在“把”字句中，“把”後面必須緊跟動作的受事賓語。正確的語序應該是“把 + 賓語 + 動詞 + 其他成分”，因此“房間”必須放在“把”和“打掃”之間。"
      }
    ]
  }
}
```

---

## sense 19860, level 1

#### Pack A
### Level 1 (sense 19860, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "pronunciation": "luàn",
  "ipa": "[luan˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "峦",
    "乱",
    "栾",
    "卵"
  ],
  "correct_answer": "乱",
  "explanation": "正确。乱（luàn）读第四声，表示没有条理或秩序。",
  "distractor_explanations": {
    "卵": "错误。卵（luǎn）读第三声，指蛋或动物的生殖细胞，声调与意义均不同。",
    "峦": "错误。峦（luán）读第二声，指连绵的山峰，声调与意义均不同。",
    "栾": "错误。栾（luán）读第二声，多用于姓氏或植物名，声调与意义均不同。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "亂",
    "pronunciation": "luàn",
    "ipa": "[luan˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "巒",
      "亂",
      "欒",
      "卵"
    ],
    "correct_answer": "亂",
    "explanation": "正確。亂（luàn）讀第四聲，表示沒有條理或秩序。",
    "distractor_explanations": {
      "卵": "錯誤。卵（luǎn）讀第三聲，指蛋或動物的生殖細胞，聲調與意義均不同。",
      "峦": "錯誤。巒（luán）讀第二聲，指連綿的山峰，聲調與意義均不同。",
      "栾": "錯誤。欒（luán）讀第二聲，多用於姓氏或植物名，聲調與意義均不同。"
    },
    "distractor_source": "llm"
  }
}
```

#### Pack B
### Level 1 (sense 19860, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "乱",
  "pronunciation": "luàn",
  "ipa": "[luan˥˩]",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "峦",
    "卵",
    "乱",
    "栾"
  ],
  "correct_answer": "乱",
  "explanation": "正确。'乱'读作 luàn，表示没有条理、秩序或混乱的状态。",
  "distractor_explanations": {
    "峦": "错误。'峦'读作 luán（第二声），指连绵的山，与'乱'声调不同，意义也不同。",
    "卵": "错误。'卵'读作 luǎn（第三声），指蛋或动物的卵，与'乱'声调不同，意义完全不同。",
    "栾": "错误。'栾'读作 luān（第一声），多用于树木名或姓氏，与'乱'声调不同，意义无关。"
  },
  "distractor_source": "llm",
  "hant": {
    "word": "亂",
    "pronunciation": "luàn",
    "ipa": "[luan˥˩]",
    "syllable_count": 1,
    "audio_url": null,
    "options": [
      "巒",
      "卵",
      "亂",
      "欒"
    ],
    "correct_answer": "亂",
    "explanation": "正確。'亂'讀作 luàn，表示沒有條理、秩序或混亂的狀態。",
    "distractor_explanations": {
      "峦": "錯誤。'巒'讀作 luán（第二聲），指連綿的山，與'亂'聲調不同，意義也不同。",
      "卵": "錯誤。'卵'讀作 luǎn（第三聲），指蛋或動物的卵，與'亂'聲調不同，意義完全不同。",
      "栾": "錯誤。'欒'讀作 luān（第一聲），多用於樹木名或姓氏，與'亂'聲調不同，意義無關。"
    },
    "distractor_source": "llm"
  }
}
```

---

## sense 19860, level 6

#### Pack A
### Level 6 (sense 19860, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "房间正乱起来，不想让人进去参观。",
      "is_correct": false
    },
    {
      "text": "房间正乱在了，不想让人进去参观。",
      "is_correct": false
    },
    {
      "text": "正乱着房间，不想让人进去参观。",
      "is_correct": false
    },
    {
      "text": "房间正乱着，不想让人进去参观。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误。形容词“乱”表示状态，不能直接加动态助词“在了”，应改为“正乱着”。 语序错误。形容词谓语“乱”及其体标记应放在主语“房间”之后，不能构成“正乱着房间”的动宾结构。 方向补语误用。“起来”表示动作或状态的开始与向上发展，不能用于描述房间已经处于混乱的持续状态，应使用“着”。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "房間正亂起來，不想讓人進去參觀。",
        "is_correct": false
      },
      {
        "text": "房間正亂在了，不想讓人進去參觀。",
        "is_correct": false
      },
      {
        "text": "正亂著房間，不想讓人進去參觀。",
        "is_correct": false
      },
      {
        "text": "房間正亂著，不想讓人進去參觀。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤。形容詞“亂”表示狀態，不能直接加動態助詞“在了”，應改為“正亂著”。 語序錯誤。形容詞謂語“亂”及其體標記應放在主語“房間”之後，不能構成“正亂著房間”的動賓結構。 方向補語誤用。“起來”表示動作或狀態的開始與向上發展，不能用於描述房間已經處於混亂的持續狀態，應使用“著”。",
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
    "拥挤",
    "干净",
    "整齐",
    "明亮"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容事物没有条理、没有秩序的状态。",
      "explanation": "反义项：形容事物有条理、有秩序，与没有条理的‘乱’构成反义"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "擁擠",
      "乾淨",
      "整齊",
      "明亮"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容事物沒有條理、沒有秩序的狀態。",
        "explanation": "反義項：形容事物有條理、有秩序，與沒有條理的‘亂’構成反義"
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
      "text": "乱的时候东西，就动手收拾一下。",
      "is_correct": false
    },
    {
      "text": "东西乱起来了的时候，就动手收拾一下。",
      "is_correct": false
    },
    {
      "text": "东西乱着的时候，就动手收拾一下。",
      "is_correct": false
    },
    {
      "text": "东西乱的时候，就动手收拾一下。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置/选用错误。“乱”作为形容词表示状态，通常不与动态助词“着”连用表示动作进行，应去掉“着”或改为“正乱的时候”。 语序错误。时间/条件状语“东西乱的时候”中，主语“东西”和谓语“乱”的语序被破坏，导致句子结构不完整、不符合汉语表达习惯。 方向/结果补语误用。“乱起来”表示状态开始发生变化，而原句“东西乱的时候”强调的是处于混乱状态的当下，添加“起来”改变了原句的体貌和语义焦点。",
  "target_word": "乱",
  "hant": {
    "sentences": [
      {
        "text": "亂的時候東西，就動手收拾一下。",
        "is_correct": false
      },
      {
        "text": "東西亂起來了的時候，就動手收拾一下。",
        "is_correct": false
      },
      {
        "text": "東西亂著的時候，就動手收拾一下。",
        "is_correct": false
      },
      {
        "text": "東西亂的時候，就動手收拾一下。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置/選用錯誤。“亂”作為形容詞表示狀態，通常不與動態助詞“著”連用表示動作進行，應去掉“著”或改為“正亂的時候”。 語序錯誤。時間/條件狀語“東西亂的時候”中，主語“東西”和謂語“亂”的語序被破壞，導致句子結構不完整、不符合漢語表達習慣。 方向/結果補語誤用。“亂起來”表示狀態開始發生變化，而原句“東西亂的時候”強調的是處於混亂狀態的當下，新增“起來”改變了原句的體貌和語義焦點。",
    "target_word": "亂"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "乱",
  "relation": "antonym",
  "options": [
    "密集",
    "稀疏",
    "干净",
    "整齐"
  ],
  "correct_answer": "整齐",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "形容事物没有条理、没有秩序的状态。",
      "explanation": "反义项：整齐形容有条理、有秩序，与乱的'没有条理、没有秩序'正好相反。"
    }
  },
  "hant": {
    "word": "亂",
    "relation": "antonym",
    "options": [
      "密集",
      "稀疏",
      "乾淨",
      "整齊"
    ],
    "correct_answer": "整齊",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "形容事物沒有條理、沒有秩序的狀態。",
        "explanation": "反義項：整齊形容有條理、有秩序，與亂的'沒有條理、沒有秩序'正好相反。"
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
      "text": "数据要干净，不能乱。",
      "is_correct": true
    },
    {
      "text": "桌上的东西很乱，不知道该怎么收拾。",
      "is_correct": true
    },
    {
      "text": "他做事乱太，经常丢三落四。",
      "is_correct": false,
      "error_description": "语序错误。程度副词“太”应放在形容词“乱”的前面作状语，不能放在形容词后面。"
    },
    {
      "text": "你把桌子上的书弄得这么乱。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "資料要乾淨，不能亂。",
        "is_correct": true
      },
      {
        "text": "桌上的東西很亂，不知道該怎麼收拾。",
        "is_correct": true
      },
      {
        "text": "他做事亂太，經常丟三落四。",
        "is_correct": false,
        "error_description": "語序錯誤。程度副詞“太”應放在形容詞“亂”的前面作狀語，不能放在形容詞後面。"
      },
      {
        "text": "你把桌子上的書弄得這麼亂。",
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
      "text": "这种乱的局面让人很心烦。",
      "is_correct": true
    },
    {
      "text": "他把房间收拾得乱极了。",
      "is_correct": false,
      "error_description": "结果补语误用。'收拾'的结果不能是'乱'，'乱'表示没有条理，与'收拾'（整理）的动作方向相反。应改为表示整理好的结果补语，如'干净'或'整齐'。"
    },
    {
      "text": "东西乱的时候，就动手收拾一下。",
      "is_correct": true
    },
    {
      "text": "他的书桌上堆满了各种文件和书籍，看起来非常乱，需要好好整理一下。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "這種亂的局面讓人很心煩。",
        "is_correct": true
      },
      {
        "text": "他把房間收拾得亂極了。",
        "is_correct": false,
        "error_description": "結果補語誤用。'收拾'的結果不能是'亂'，'亂'表示沒有條理，與'收拾'（整理）的動作方向相反。應改為表示整理好的結果補語，如'乾淨'或'整齊'。"
      },
      {
        "text": "東西亂的時候，就動手收拾一下。",
        "is_correct": true
      },
      {
        "text": "他的書桌上堆滿了各種檔案和書籍，看起來非常亂，需要好好整理一下。",
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
