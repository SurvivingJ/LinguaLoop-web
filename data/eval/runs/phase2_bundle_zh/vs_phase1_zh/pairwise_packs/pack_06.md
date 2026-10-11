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
      "text": "这种大胆尝试的做法，可谓开了行业改革的先河。",
      "is_correct": true
    },
    {
      "text": "这种大胆尝试的做法，可谓开了行业改革的三个先河。",
      "is_correct": false
    },
    {
      "text": "这种大胆尝试的做法，可谓开出来行业改革的先河。",
      "is_correct": false
    },
    {
      "text": "这种大胆尝试的做法，可谓正在开行业改革的先河。",
      "is_correct": false
    }
  ],
  "explanation": "量词错误。'先河'作为抽象名词，指代一种开创性的行为或状态，通常不可数，不能用'三个'等具体数量词修饰。 体貌错误。'开先河'通常指已经完成的开创性动作或既成事实，用'正在'表示进行时态不符合该词描述历史地位的语用习惯。 趋向补语冗余。'开'在此处为喻义动词，直接带宾语'先河'即可，加'出来'显得口语化且破坏了书面语的凝练感，不符合'先河'的正式语域。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "這種大膽嘗試的做法，可謂開了行業改革的先河。",
        "is_correct": true
      },
      {
        "text": "這種大膽嘗試的做法，可謂開了行業改革的三個先河。",
        "is_correct": false
      },
      {
        "text": "這種大膽嘗試的做法，可謂開出來行業改革的先河。",
        "is_correct": false
      },
      {
        "text": "這種大膽嘗試的做法，可謂正在開行業改革的先河。",
        "is_correct": false
      }
    ],
    "explanation": "量詞錯誤。'先河'作為抽象名詞，指代一種開創性的行為或狀態，通常不可數，不能用'三個'等具體數量詞修飾。 體貌錯誤。'開先河'通常指已經完成的開創性動作或既成事實，用'正在'表示進行時態不符合該詞描述歷史地位的語用習慣。 趨向補語冗餘。'開'在此處為喻義動詞，直接帶賓語'先河'即可，加'出來'顯得口語化且破壞了書面語的凝練感，不符合'先河'的正式語域。",
    "target_word": "先河"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "这个决定可能会开启一段新的先河。",
      "is_correct": false
    },
    {
      "text": "这个决定可能会向新的先河开启。",
      "is_correct": false
    },
    {
      "text": "这个决定可能会开启新的先河。",
      "is_correct": true
    },
    {
      "text": "这个决定可能会开启着新的先河。",
      "is_correct": false
    }
  ],
  "explanation": "体貌错误。'开启'是瞬间动词或结果性动词，不宜与表示持续状态的'着'连用。 量词错误。'先河'作为抽象比喻，通常不与'一段'等描写过程或片段的量词搭配。 语序错误。动宾结构'开启先河'被错误地拆分为介词短语前置，导致句法混乱。",
  "target_word": "先河",
  "hant": {
    "sentences": [
      {
        "text": "這個決定可能會開啟一段新的先河。",
        "is_correct": false
      },
      {
        "text": "這個決定可能會向新的先河開啟。",
        "is_correct": false
      },
      {
        "text": "這個決定可能會開啟新的先河。",
        "is_correct": true
      },
      {
        "text": "這個決定可能會開啟著新的先河。",
        "is_correct": false
      }
    ],
    "explanation": "體貌錯誤。'開啟'是瞬間動詞或結果性動詞，不宜與表示持續狀態的'著'連用。 量詞錯誤。'先河'作為抽象比喻，通常不與'一段'等描寫過程或片段的量詞搭配。 語序錯誤。動賓結構'開啟先河'被錯誤地拆分為介詞短語前置，導致句法混亂。",
    "target_word": "先河"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "先河",
  "relation": "synonym",
  "options": [
    "跟随",
    "肇始",
    "常规",
    "末流"
  ],
  "correct_answer": "肇始",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "比喻某项事业或行动的开创者或最早的做法",
      "explanation": "近义。'肇始'指开始、发端，与'先河'的'开创'义项相近，均为书面语。"
    }
  },
  "hant": {
    "word": "先河",
    "relation": "synonym",
    "options": [
      "跟隨",
      "肇始",
      "常規",
      "末流"
    ],
    "correct_answer": "肇始",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "比喻某項事業或行動的開創者或最早的做法",
        "explanation": "近義。'肇始'指開始、發端，與'先河'的'開創'義項相近，均為書面語。"
      }
    }
  }
}
```

---

## sense 10113, level 7

#### Pack A
### Level 7 (sense 10113, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "谁愿意在这个新项目中开创先河呢？",
      "is_correct": true
    },
    {
      "text": "谁愿意在这个新项目中开创一个先河呢？",
      "is_correct": false,
      "error_description": "错误句中误加了数量词'一个'。'先河'比喻开创性的做法，属于抽象概念，一般不加个体量词，直接说'开创先河'。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "誰願意在這個新專案中開創先河呢？",
        "is_correct": true
      },
      {
        "text": "誰願意在這個新專案中開創一個先河呢？",
        "is_correct": false,
        "error_description": "錯誤句中誤加了數量詞'一個'。'先河'比喻開創性的做法，屬於抽象概念，一般不加個體量詞，直接說'開創先河'。"
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
      "text": "老师鼓励我们在学术研究中勇于开创了一条先河。",
      "is_correct": false,
      "error_description": "错误句中误加了量词短语'了一条'。'开创先河'作为固定比喻结构，中间不插入量词，以保持其抽象性和整体性。"
    },
    {
      "text": "老师鼓励我们在学术研究中勇于开创先河。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師鼓勵我們在學術研究中勇於開創了一條先河。",
        "is_correct": false,
        "error_description": "錯誤句中誤加了量詞短語'了一條'。'開創先河'作為固定比喻結構，中間不插入量詞，以保持其抽象性和整體性。"
      },
      {
        "text": "老師鼓勵我們在學術研究中勇於開創先河。",
        "is_correct": true
      }
    ]
  }
}
```

#### Pack B
### Level 7 (sense 10113, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "中国早在唐代便已广泛应用雕版印刷，宋代毕昇更首创泥活字，开启了可重复排版的技术先河。",
      "is_correct": true
    },
    {
      "text": "先河已开，同学们都跟着做。",
      "is_correct": true
    },
    {
      "text": "这本先河之作非常受欢迎。",
      "is_correct": true
    },
    {
      "text": "他昨天开着先河，大家都跟着学。",
      "is_correct": false,
      "error_description": "体标选用错误。“开先河”表示开创先例，是已经完成的动作，应使用表示完成的体标“了”，而不是表示动作持续的“着”。"
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "中國早在唐代便已廣泛應用雕版印刷，宋代畢昇更首創泥活字，開啟了可重複排版的技術先河。",
        "is_correct": true
      },
      {
        "text": "先河已開，同學們都跟著做。",
        "is_correct": true
      },
      {
        "text": "這本先河之作非常受歡迎。",
        "is_correct": true
      },
      {
        "text": "他昨天開著先河，大家都跟著學。",
        "is_correct": false,
        "error_description": "體標選用錯誤。“開先河”表示開創先例，是已經完成的動作，應使用表示完成的體標“了”，而不是表示動作持續的“著”。"
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
      "text": "老师表扬了他，说他开了先河。",
      "is_correct": true
    },
    {
      "text": "先河一开，后面的事就好办了。",
      "is_correct": true
    },
    {
      "text": "他开先河了，大家都跟着做。",
      "is_correct": false,
      "error_description": "“开先河”是动宾结构，表示动作完成的动态助词“了”应放在动词“开”和宾语“先河”之间，即“开了先河”，不能放在句末。"
    },
    {
      "text": "先河之作的销量非常好。",
      "is_correct": true
    }
  ],
  "hant": {
    "sentences": [
      {
        "text": "老師表揚了他，說他開了先河。",
        "is_correct": true
      },
      {
        "text": "先河一開，後面的事就好辦了。",
        "is_correct": true
      },
      {
        "text": "他開先河了，大家都跟著做。",
        "is_correct": false,
        "error_description": "“開先河”是動賓結構，表示動作完成的動態助詞“了”應放在動詞“開”和賓語“先河”之間，即“開了先河”，不能放在句末。"
      },
      {
        "text": "先河之作的銷量非常好。",
        "is_correct": true
      }
    ]
  }
}
```

---

## sense 10113, level 9

#### Pack A
### Level 9 (sense 10113, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "这是先河之作，大家都很喜欢。",
  "hant": {
    "original_sentence": "這是先河之作，大家都很喜歡。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这是先河之作，大家都很喜欢。",
  "chunks": [
    "这",
    "是先河之作",
    "大家",
    "都很喜欢"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "大家",
    "这",
    "是先河之作",
    "都很喜欢"
  ],
  "target_word": "先河",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這是先河之作，大家都很喜歡。",
    "chunks": [
      "這",
      "是先河之作",
      "大家",
      "都很喜歡"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "大家",
      "這",
      "是先河之作",
      "都很喜歡"
    ],
    "target_word": "先河",
    "chunk_count": 4
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "既然此举已开先河，后继者便可循其轨迹继续探索。",
  "hant": {
    "original_sentence": "既然此舉已開先河，後繼者便可循其軌跡繼續探索。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "既然此举已开先河，后继者便可循其轨迹继续探索。",
  "chunks": [
    "既然此举",
    "已开先河",
    "后继者",
    "便可循其轨迹",
    "继续探索"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "继续探索",
    "既然此举",
    "后继者",
    "便可循其轨迹",
    "已开先河"
  ],
  "target_word": "先河",
  "chunk_count": 5,
  "hant": {
    "schema_version": 2,
    "original_sentence": "既然此舉已開先河，後繼者便可循其軌跡繼續探索。",
    "chunks": [
      "既然此舉",
      "已開先河",
      "後繼者",
      "便可循其軌跡",
      "繼續探索"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3,
      4
    ],
    "shuffled_chunks": [
      "繼續探索",
      "既然此舉",
      "後繼者",
      "便可循其軌跡",
      "已開先河"
    ],
    "target_word": "先河",
    "chunk_count": 5
  }
}
```

#### Pack B
### Level 9 (sense 10113, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "他的发明为后来的技术发展开创了先河。",
  "hant": {
    "original_sentence": "他的發明為後來的技術發展開創了先河。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他的发明为后来的技术发展开创了先河。",
  "chunks": [
    "他的发明",
    "为后来的技术",
    "发展开创了先河"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "他的发明",
    "发展开创了先河",
    "为后来的技术"
  ],
  "target_word": "先河",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他的發明為後來的技術發展開創了先河。",
    "chunks": [
      "他的發明",
      "為後來的技術",
      "發展開創了先河"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "他的發明",
      "發展開創了先河",
      "為後來的技術"
    ],
    "target_word": "先河",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "这种大胆尝试的做法，可谓开了行业改革的先河。",
  "hant": {
    "original_sentence": "這種大膽嘗試的做法，可謂開了行業改革的先河。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "这种大胆尝试的做法，可谓开了行业改革的先河。",
  "chunks": [
    "这种大胆",
    "尝试的做法",
    "可谓开了行业",
    "改革的先河"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "这种大胆",
    "改革的先河",
    "可谓开了行业",
    "尝试的做法"
  ],
  "target_word": "先河",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "這種大膽嘗試的做法，可謂開了行業改革的先河。",
    "chunks": [
      "這種大膽",
      "嘗試的做法",
      "可謂開了行業",
      "改革的先河"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "這種大膽",
      "改革的先河",
      "可謂開了行業",
      "嘗試的做法"
    ],
    "target_word": "先河",
    "chunk_count": 4
  }
}
```

---

## sense 10125, level 1

#### Pack A
### Level 1 (sense 10125, difficulty None)
**hanzi_to_pinyin** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "真正",
  "options": [
    "zhén zhèng",
    "zhēn zhèng",
    "zhēn zhéng",
    "zhēn zhēng"
  ],
  "correct_answer": "zhēn zhèng",
  "word": "真正",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "真正",
    "options": [
      "zhén zhèng",
      "zhēn zhèng",
      "zhēn zhéng",
      "zhēn zhēng"
    ],
    "correct_answer": "zhēn zhèng",
    "word": "真正",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "zhēn zhèng",
  "options": [
    "正是",
    "肯定",
    "跟着",
    "真正"
  ],
  "correct_answer": "真正",
  "word": "真正",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "肯定": "component",
    "正是": "component",
    "跟着": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "zhēn zhèng",
    "options": [
      "正是",
      "肯定",
      "跟著",
      "真正"
    ],
    "correct_answer": "真正",
    "word": "真正",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "肯定": "component",
      "正是": "component",
      "跟着": "component"
    }
  }
}
```
**tone_id_word** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "真正",
  "toneless_pinyin": "zhen zheng",
  "full_pinyin": "zhēn zhèng",
  "options": [
    "12",
    "14",
    "13",
    "11"
  ],
  "correct_answer": "14",
  "option_labels": {
    "12": "high level (1) + rising (2)",
    "14": "high level (1) + falling (4)",
    "13": "high level (1) + dipping (3)",
    "11": "high level (1) + high level (1)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "真正",
    "toneless_pinyin": "zhen zheng",
    "full_pinyin": "zhēn zhèng",
    "options": [
      "12",
      "14",
      "13",
      "11"
    ],
    "correct_answer": "14",
    "option_labels": {
      "12": "high level (1) + rising (2)",
      "14": "high level (1) + falling (4)",
      "13": "high level (1) + dipping (3)",
      "11": "high level (1) + high level (1)"
    },
    "syllable_count": 2
  }
}
```

#### Pack B
### Level 1 (sense 10125, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "真正",
  "options": [
    "zhēn zhēng",
    "zhēn zhéng",
    "zhén zhèng",
    "zhēn zhèng"
  ],
  "correct_answer": "zhēn zhèng",
  "word": "真正",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "真正",
    "options": [
      "zhēn zhēng",
      "zhēn zhéng",
      "zhén zhèng",
      "zhēn zhèng"
    ],
    "correct_answer": "zhēn zhèng",
    "word": "真正",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "zhēn zhèng",
  "options": [
    "真正",
    "正是",
    "跟着",
    "肯定"
  ],
  "correct_answer": "真正",
  "word": "真正",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "肯定": "component",
    "正是": "component",
    "跟着": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "zhēn zhèng",
    "options": [
      "真正",
      "正是",
      "跟著",
      "肯定"
    ],
    "correct_answer": "真正",
    "word": "真正",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "肯定": "component",
      "正是": "component",
      "跟着": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "真正",
  "toneless_pinyin": "zhen zheng",
  "full_pinyin": "zhēn zhèng",
  "options": [
    "12",
    "11",
    "14",
    "13"
  ],
  "correct_answer": "14",
  "option_labels": {
    "12": "high level (1) + rising (2)",
    "11": "high level (1) + high level (1)",
    "14": "high level (1) + falling (4)",
    "13": "high level (1) + dipping (3)"
  },
  "syllable_count": 2,
  "hant": {
    "schema_version": 2,
    "word": "真正",
    "toneless_pinyin": "zhen zheng",
    "full_pinyin": "zhēn zhèng",
    "options": [
      "12",
      "11",
      "14",
      "13"
    ],
    "correct_answer": "14",
    "option_labels": {
      "12": "high level (1) + rising (2)",
      "11": "high level (1) + high level (1)",
      "14": "high level (1) + falling (4)",
      "13": "high level (1) + dipping (3)"
    },
    "syllable_count": 2
  }
}
```

---

## sense 10125, level 2

#### Pack A
### Level 2 (sense 10125, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "真正",
  "pronunciation": "zhēn zhèng",
  "correct_definition": "真实地；确实（常用来强调所说的话是真实的）。",
  "options": [
    "用手做出的各种姿势或动作，用来表达意思或情感。",
    "指物质（如有机物或岩石）经过地质作用转变为矿物或矿物集合体的过程。",
    "真实地；确实（常用来强调所说的话是真实的）。",
    "指能够引起生物体产生反应或感受的某种作用，如感官上的兴奋或情绪上的激动。"
  ],
  "hant": {
    "word": "真正",
    "pronunciation": "zhēn zhèng",
    "correct_definition": "真實地；確實（常用來強調所說的話是真實的）。",
    "options": [
      "用手做出的各種姿勢或動作，用來表達意思或情感。",
      "指物質（如有機物或岩石）經過地質作用轉變為礦物或礦物集合體的過程。",
      "真實地；確實（常用來強調所說的話是真實的）。",
      "指能夠引起生物體產生反應或感受的某種作用，如感官上的興奮或情緒上的激動。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "真正",
  "pronunciation": "zhēn zhèng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "〜おきに；同じ間隔で繰り返すこと",
        "指把自己的财物或身体的一部分无偿地给予他人或组织，用于公益或帮助他人。",
        "真实地；确实（常用来强调所说的话是真实的）。",
        "調号"
      ],
      "correct_answer": "真实地；确实（常用来强调所说的话是真实的）。"
    }
  },
  "hant": {
    "word": "真正",
    "pronunciation": "zhēn zhèng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "〜おきに；同じ間隔で繰り返すこと",
          "指把自己的財物或身體的一部分無償地給予他人或組織，用於公益或幫助他人。",
          "真實地；確實（常用來強調所說的話是真實的）。",
          "調號"
        ],
        "correct_answer": "真實地；確實（常用來強調所說的話是真實的）。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 10125, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "真正",
  "pronunciation": "zhēn zhèng",
  "correct_definition": "真实地；确实（强调事实）",
  "options": [
    "支点是指杠杆上起支撑作用并让杠杆能绕其转动的固定点，也可以比喻为事情发展的关键或基础。",
    "算法是解决问题或完成计算的一系列明确步骤，常用于数学和计算机编程。",
    "双方激烈地互相攻击、拼杀，常指战斗或竞争中的激烈对抗。",
    "真实地；确实（强调事实）"
  ],
  "hant": {
    "word": "真正",
    "pronunciation": "zhēn zhèng",
    "correct_definition": "真實地；確實（強調事實）",
    "options": [
      "支點是指槓桿上起支撐作用並讓槓桿能繞其轉動的固定點，也可以比喻為事情發展的關鍵或基礎。",
      "演算法是解決問題或完成計算的一系列明確步驟，常用於數學和計算機程式設計。",
      "雙方激烈地互相攻擊、拼殺，常指戰鬥或競爭中的激烈對抗。",
      "真實地；確實（強調事實）"
    ]
  }
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "真正",
  "pronunciation": "zhēn zhèng",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "指在学校里学习并遵循正式规则和方法的群体。",
        "表示某事正在发生或逐渐发展",
        "積み重ねる",
        "真实地；确实（强调事实）"
      ],
      "correct_answer": "真实地；确实（强调事实）"
    }
  },
  "hant": {
    "word": "真正",
    "pronunciation": "zhēn zhèng",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "指在學校裡學習並遵循正式規則和方法的群體。",
          "表示某事正在發生或逐漸發展",
          "積み重ねる",
          "真實地；確實（強調事實）"
        ],
        "correct_answer": "真實地；確實（強調事實）"
      }
    }
  }
}
```

---

## sense 10125, level 4

#### Pack A
### Level 4 (sense 10125, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "材料创新必须与配套回收设施、政策法规及公众认知协同演进，才能___实现可持续发展。",
  "original_sentence": "材料创新必须与配套回收设施、政策法规及公众认知协同演进，才能真正实现可持续发展。",
  "target_word": "真正",
  "word": "真正",
  "answer": {
    "accepted": [
      "真正"
    ],
    "accepted_normalized": [
      "真正"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "材料創新必須與配套回收設施、政策法規及公眾認知協同演進，才能___實現可持續發展。",
    "original_sentence": "材料創新必須與配套回收設施、政策法規及公眾認知協同演進，才能真正實現可持續發展。",
    "target_word": "真正",
    "word": "真正",
    "answer": {
      "accepted": [
        "真正"
      ],
      "accepted_normalized": [
        "真正"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "她___关心你的感受。",
  "original_sentence": "她真正关心你的感受。",
  "target_word": "真正",
  "word": "真正",
  "answer": {
    "accepted": [
      "真正"
    ],
    "accepted_normalized": [
      "真正"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "她___關心你的感受。",
    "original_sentence": "她真正關心你的感受。",
    "target_word": "真正",
    "word": "真正",
    "answer": {
      "accepted": [
        "真正"
      ],
      "accepted_normalized": [
        "真正"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

#### Pack B
### Level 4 (sense 10125, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "你___明白我的意思吗？",
  "original_sentence": "你真正明白我的意思吗？",
  "target_word": "真正",
  "word": "真正",
  "answer": {
    "accepted": [
      "真正",
      "真正地",
      "真假",
      "真诚"
    ],
    "accepted_normalized": [
      "真正",
      "真正地",
      "真假",
      "真诚"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": "t2s"
  },
  "input_mode": "ime",
  "hant": {
    "schema_version": 2,
    "sentence_with_blank": "你___明白我的意思嗎？",
    "original_sentence": "你真正明白我的意思嗎？",
    "target_word": "真正",
    "word": "真正",
    "answer": {
      "accepted": [
        "真正",
        "真正地",
        "真假",
        "真誠"
      ],
      "accepted_normalized": [
        "真正",
        "真正地",
        "真假",
        "真誠"
      ]
    },
    "normalization": {
      "unicode": "NFKC",
      "whitespace": "collapse+trim",
      "case": "fold",
      "trailing_punctuation": "strip",
      "quotes": "straighten",
      "script": "t2s"
    },
    "input_mode": "ime"
  }
}
```

---

## sense 10125, level 6

#### Pack A
### Level 6 (sense 10125, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "真正天气冷起来了。",
      "is_correct": false
    },
    {
      "text": "天气真正冷过起来了。",
      "is_correct": false
    },
    {
      "text": "天气真正冷得下去了。",
      "is_correct": false
    },
    {
      "text": "天气真正冷起来了。",
      "is_correct": true
    }
  ],
  "explanation": "体标位置错误：'过'表示经历，'起来'表示开始并持续，两者连用造成体貌冲突，且'真正'应直接修饰形容词或动词短语核心，此处结构混乱。 语序错误：'真正'作为副词，通常紧贴其所修饰的谓语部分（冷起来），放在主语'天气'之前会改变句子焦点，使句子听起来像是在对比'真正的天气'和'假的天气'，不符合原意。 方向补语误用：'冷起来'表示状态开始并增强，'冷下去'通常表示状态减弱或结束。这里语境是变冷，应用'起来'，用'下去'语义相反。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "真正天氣冷起來了。",
        "is_correct": false
      },
      {
        "text": "天氣真正冷過起來了。",
        "is_correct": false
      },
      {
        "text": "天氣真正冷得下去了。",
        "is_correct": false
      },
      {
        "text": "天氣真正冷起來了。",
        "is_correct": true
      }
    ],
    "explanation": "體標位置錯誤：'過'表示經歷，'起來'表示開始並持續，兩者連用造成體貌衝突，且'真正'應直接修飾形容詞或動詞短語核心，此處結構混亂。 語序錯誤：'真正'作為副詞，通常緊貼其所修飾的謂語部分（冷起來），放在主語'天氣'之前會改變句子焦點，使句子聽起來像是在對比'真正的天氣'和'假的天氣'，不符合原意。 方向補語誤用：'冷起來'表示狀態開始並增強，'冷下去'通常表示狀態減弱或結束。這裡語境是變冷，應用'起來'，用'下去'語義相反。",
    "target_word": "真正"
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "真正",
  "relation": "antonym",
  "options": [
    "非常",
    "虚假",
    "大概",
    "确实"
  ],
  "correct_answer": "虚假",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "真实地；确实（强调事实）",
      "explanation": "反义关系：'真正'强调事实的真实存在，'虚假'指与事实不符，二者在'真实性'维度上构成反义。"
    }
  },
  "hant": {
    "word": "真正",
    "relation": "antonym",
    "options": [
      "非常",
      "虛假",
      "大概",
      "確實"
    ],
    "correct_answer": "虛假",
    "schema_version": 2,
    "nl": {
      "en": {
        "definition": "真實地；確實（強調事實）",
        "explanation": "反義關係：'真正'強調事實的真實存在，'虛假'指與事實不符，二者在'真實性'維度上構成反義。"
      }
    }
  }
}
```

#### Pack B
### Level 6 (sense 10125, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "真正他关心我，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心着了，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心起我去，是我值得信赖的知己。",
      "is_correct": false
    },
    {
      "text": "他真正关心我，是我值得信赖的知己。",
      "is_correct": true
    }
  ],
  "explanation": "语序错误：“真正”作为副词，通常放在主语之后、谓语动词之前。放在主语“他”之前修饰整个句子不符合汉语语法习惯。 体标选用错误：“关心”是心理动词，通常不与表示完成的“了”和表示持续的“着”直接连用，此处体标叠加使用导致语法错误。 补语误用：“起……去”不是合法的趋向补语结构。表示动作开始并继续应使用“起……来”，此处误用了“去”。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "真正他關心我，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心著了，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心起我去，是我值得信賴的知己。",
        "is_correct": false
      },
      {
        "text": "他真正關心我，是我值得信賴的知己。",
        "is_correct": true
      }
    ],
    "explanation": "語序錯誤：“真正”作為副詞，通常放在主語之後、謂語動詞之前。放在主語“他”之前修飾整個句子不符合漢語語法習慣。 體標選用錯誤：“關心”是心理動詞，通常不與表示完成的“了”和表示持續的“著”直接連用，此處體標疊加使用導致語法錯誤。 補語誤用：“起……去”不是合法的趨向補語結構。表示動作開始並繼續應使用“起……來”，此處誤用了“去”。",
    "target_word": "真正"
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "只有长期相处，两人才能真正建立感情。",
      "is_correct": true
    },
    {
      "text": "只有长期相处，两人建立感情真正。",
      "is_correct": false
    },
    {
      "text": "只有长期相处，两人真正了建立感情。",
      "is_correct": false
    },
    {
      "text": "只有长期相处，两人真正能建立感情。",
      "is_correct": false
    }
  ],
  "explanation": "语序错误：能愿动词'能'应放在副词'真正'之前，正确语序为'能真正建立'。 体标位置错误：动态助词'了'表示完成，不能放在副词'真正'和动词'建立'之间，应放在句末或动词后。 语序错误：副词'真正'必须放在它所修饰的动词'建立'之前，不能放在句末。",
  "target_word": "真正",
  "hant": {
    "sentences": [
      {
        "text": "只有長期相處，兩人才能真正建立感情。",
        "is_correct": true
      },
      {
        "text": "只有長期相處，兩人建立感情真正。",
        "is_correct": false
      },
      {
        "text": "只有長期相處，兩人真正了建立感情。",
        "is_correct": false
      },
      {
        "text": "只有長期相處，兩人真正能建立感情。",
        "is_correct": false
      }
    ],
    "explanation": "語序錯誤：能願動詞'能'應放在副詞'真正'之前，正確語序為'能真正建立'。 體標位置錯誤：動態助詞'了'表示完成，不能放在副詞'真正'和動詞'建立'之間，應放在句末或動詞後。 語序錯誤：副詞'真正'必須放在它所修飾的動詞'建立'之前，不能放在句末。",
    "target_word": "真正"
  }
}
```

---

## sense 10125, level 9

#### Pack A
### Level 9 (sense 10125, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "看到孩子的笑脸，我才真正感受到快乐。",
  "hant": {
    "original_sentence": "看到孩子的笑臉，我才真正感受到快樂。"
  }
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "看到孩子的笑脸，我才真正感受到快乐。",
  "chunks": [
    "看到孩子的笑脸",
    "我",
    "才真正感受到快乐"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "才真正感受到快乐",
    "我",
    "看到孩子的笑脸"
  ],
  "target_word": "真正",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "看到孩子的笑臉，我才真正感受到快樂。",
    "chunks": [
      "看到孩子的笑臉",
      "我",
      "才真正感受到快樂"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "才真正感受到快樂",
      "我",
      "看到孩子的笑臉"
    ],
    "target_word": "真正",
    "chunk_count": 3
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "他真正关心我，是我值得信赖的知己。",
  "hant": {
    "original_sentence": "他真正關心我，是我值得信賴的知己。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他真正关心我，是我值得信赖的知己。",
  "chunks": [
    "他",
    "真正关心我",
    "是我",
    "值得信赖的知己"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "值得信赖的知己",
    "他",
    "是我",
    "真正关心我"
  ],
  "target_word": "真正",
  "chunk_count": 4,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他真正關心我，是我值得信賴的知己。",
    "chunks": [
      "他",
      "真正關心我",
      "是我",
      "值得信賴的知己"
    ],
    "correct_ordering": [
      0,
      1,
      2,
      3
    ],
    "shuffled_chunks": [
      "值得信賴的知己",
      "他",
      "是我",
      "真正關心我"
    ],
    "target_word": "真正",
    "chunk_count": 4
  }
}
```

#### Pack B
### Level 9 (sense 10125, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "他真正喜欢的是画画，不是唱歌。",
  "hant": {
    "original_sentence": "他真正喜歡的是畫畫，不是唱歌。"
  }
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "他真正喜欢的是画画，不是唱歌。",
  "chunks": [
    "他",
    "真正喜欢的是画画",
    "不是唱歌"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "真正喜欢的是画画",
    "不是唱歌",
    "他"
  ],
  "target_word": "真正",
  "chunk_count": 3,
  "hant": {
    "schema_version": 2,
    "original_sentence": "他真正喜歡的是畫畫，不是唱歌。",
    "chunks": [
      "他",
      "真正喜歡的是畫畫",
      "不是唱歌"
    ],
    "correct_ordering": [
      0,
      1,
      2
    ],
    "shuffled_chunks": [
      "真正喜歡的是畫畫",
      "不是唱歌",
      "他"
    ],
    "target_word": "真正",
    "chunk_count": 3
  }
}
```

---

## sense 11315, level 1

#### Pack A
### Level 1 (sense 11315, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "拮抗剂",
  "options": [
    "jiē kàng jì",
    "jié kàng jì",
    "jié kāng jì",
    "jié kàng jī"
  ],
  "correct_answer": "jié kàng jì",
  "word": "拮抗剂",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "拮抗劑",
    "options": [
      "jiē kàng jì",
      "jié kàng jì",
      "jié kāng jì",
      "jié kàng jī"
    ],
    "correct_answer": "jié kàng jì",
    "word": "拮抗劑",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "jié kàng jì",
  "options": [
    "捕捉到",
    "抗逆性",
    "黏合剂",
    "拮抗剂"
  ],
  "correct_answer": "拮抗剂",
  "word": "拮抗剂",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "捕捉到": "component",
    "抗逆性": "component",
    "黏合剂": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "jié kàng jì",
    "options": [
      "捕捉到",
      "抗逆性",
      "黏合劑",
      "拮抗劑"
    ],
    "correct_answer": "拮抗劑",
    "word": "拮抗劑",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "捕捉到": "component",
      "抗逆性": "component",
      "黏合剂": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "拮抗剂",
  "toneless_pinyin": "jie kang ji",
  "full_pinyin": "jié kàng jì",
  "options": [
    "244",
    "243",
    "242",
    "241"
  ],
  "correct_answer": "244",
  "option_labels": {
    "244": "rising (2) + falling (4) + falling (4)",
    "243": "rising (2) + falling (4) + dipping (3)",
    "242": "rising (2) + falling (4) + rising (2)",
    "241": "rising (2) + falling (4) + high level (1)"
  },
  "syllable_count": 3,
  "hant": {
    "schema_version": 2,
    "word": "拮抗劑",
    "toneless_pinyin": "jie kang ji",
    "full_pinyin": "jié kàng jì",
    "options": [
      "244",
      "243",
      "242",
      "241"
    ],
    "correct_answer": "244",
    "option_labels": {
      "244": "rising (2) + falling (4) + falling (4)",
      "243": "rising (2) + falling (4) + dipping (3)",
      "242": "rising (2) + falling (4) + rising (2)",
      "241": "rising (2) + falling (4) + high level (1)"
    },
    "syllable_count": 3
  }
}
```

#### Pack B
### Level 1 (sense 11315, difficulty None)
**hanzi_to_pinyin** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "拮抗剂",
  "options": [
    "jiē kàng jì",
    "jié kàng jì",
    "jié kāng jì",
    "jié kàng jī"
  ],
  "correct_answer": "jié kàng jì",
  "word": "拮抗剂",
  "direction": "hanzi_to_pinyin",
  "hant": {
    "schema_version": 2,
    "prompt": "拮抗劑",
    "options": [
      "jiē kàng jì",
      "jié kàng jì",
      "jié kāng jì",
      "jié kàng jī"
    ],
    "correct_answer": "jié kàng jì",
    "word": "拮抗劑",
    "direction": "hanzi_to_pinyin"
  }
}
```
**pinyin_to_hanzi** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "jié kàng jì",
  "options": [
    "捕捉到",
    "显影剂",
    "抗逆性",
    "拮抗剂"
  ],
  "correct_answer": "拮抗剂",
  "word": "拮抗剂",
  "direction": "pinyin_to_hanzi",
  "distractor_sources": {
    "捕捉到": "component",
    "显影剂": "component",
    "抗逆性": "component"
  },
  "hant": {
    "schema_version": 2,
    "prompt": "jié kàng jì",
    "options": [
      "捕捉到",
      "顯影劑",
      "抗逆性",
      "拮抗劑"
    ],
    "correct_answer": "拮抗劑",
    "word": "拮抗劑",
    "direction": "pinyin_to_hanzi",
    "distractor_sources": {
      "捕捉到": "component",
      "显影剂": "component",
      "抗逆性": "component"
    }
  }
}
```
**tone_id_word** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "word": "拮抗剂",
  "toneless_pinyin": "jie kang ji",
  "full_pinyin": "jié kàng jì",
  "options": [
    "244",
    "243",
    "242",
    "241"
  ],
  "correct_answer": "244",
  "option_labels": {
    "244": "rising (2) + falling (4) + falling (4)",
    "243": "rising (2) + falling (4) + dipping (3)",
    "242": "rising (2) + falling (4) + rising (2)",
    "241": "rising (2) + falling (4) + high level (1)"
  },
  "syllable_count": 3,
  "hant": {
    "schema_version": 2,
    "word": "拮抗劑",
    "toneless_pinyin": "jie kang ji",
    "full_pinyin": "jié kàng jì",
    "options": [
      "244",
      "243",
      "242",
      "241"
    ],
    "correct_answer": "244",
    "option_labels": {
      "244": "rising (2) + falling (4) + falling (4)",
      "243": "rising (2) + falling (4) + dipping (3)",
      "242": "rising (2) + falling (4) + rising (2)",
      "241": "rising (2) + falling (4) + high level (1)"
    },
    "syllable_count": 3
  }
}
```

---

## sense 11315, level 2

#### Pack A
### Level 2 (sense 11315, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "拮抗剂",
  "pronunciation": "jié kàng jì",
  "correct_definition": "能抵消另一种物质作用的药或成分。",
  "options": [
    "指因粮食短缺而引发的争夺或冲突。",
    "能抵消另一种物质作用的药或成分。",
    "地位指个人或事物在社会关系中所处的位置或等级。",
    "液体流动而消失；也比喻时间等逝去。"
  ],
  "hant": {
    "word": "拮抗劑",
    "pronunciation": "jié kàng jì",
    "correct_definition": "能抵消另一種物質作用的藥或成分。",
    "options": [
      "指因糧食短缺而引發的爭奪或衝突。",
      "能抵消另一種物質作用的藥或成分。",
      "地位指個人或事物在社會關係中所處的位置或等級。",
      "液體流動而消失；也比喻時間等逝去。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "拮抗剂",
  "pronunciation": "jié kàng jì",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "能抵消另一种物质作用的药或成分。",
        "班次的意思是车、船、飞机等出发的时间安排。",
        "建造する",
        "市井；一般の人々が暮らす日常の世界"
      ],
      "correct_answer": "能抵消另一种物质作用的药或成分。"
    }
  },
  "hant": {
    "word": "拮抗劑",
    "pronunciation": "jié kàng jì",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "能抵消另一種物質作用的藥或成分。",
          "班次的意思是車、船、飛機等出發的時間安排。",
          "建造する",
          "市井；一般の人々が暮らす日常の世界"
        ],
        "correct_answer": "能抵消另一種物質作用的藥或成分。"
      }
    }
  }
}
```

#### Pack B
### Level 2 (sense 11315, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "拮抗剂",
  "pronunciation": "jié kàng jì",
  "correct_definition": "指与某种物质作用相反、能抵消其效应的物质，常用于医学或生物学。",
  "options": [
    "表示程度加深，相当于“尤其、特别”，用于强调某个方面更加突出。",
    "对某人的优良行为或成绩给予表扬、奖品等。",
    "消费主义是一种提倡大量购买商品和服务的社会观念。",
    "指与某种物质作用相反、能抵消其效应的物质，常用于医学或生物学。"
  ],
  "hant": {
    "word": "拮抗劑",
    "pronunciation": "jié kàng jì",
    "correct_definition": "指與某種物質作用相反、能抵消其效應的物質，常用於醫學或生物學。",
    "options": [
      "表示程度加深，相當於“尤其、特別”，用於強調某個方面更加突出。",
      "對某人的優良行為或成績給予表揚、獎品等。",
      "消費主義是一種提倡大量購買商品和服務的社會觀念。",
      "指與某種物質作用相反、能抵消其效應的物質，常用於醫學或生物學。"
    ]
  }
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "拮抗剂",
  "pronunciation": "jié kàng jì",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "指与某种物质作用相反、能抵消其效应的物质，常用于医学或生物学。",
        "用力打败或控制住对方。",
        "usually; most of the time",
        "still"
      ],
      "correct_answer": "指与某种物质作用相反、能抵消其效应的物质，常用于医学或生物学。"
    }
  },
  "hant": {
    "word": "拮抗劑",
    "pronunciation": "jié kàng jì",
    "tier": "T3",
    "schema_version": 2,
    "nl": {
      "en": {
        "options": [
          "指與某種物質作用相反、能抵消其效應的物質，常用於醫學或生物學。",
          "用力打敗或控制住對方。",
          "usually; most of the time",
          "still"
        ],
        "correct_answer": "指與某種物質作用相反、能抵消其效應的物質，常用於醫學或生物學。"
      }
    }
  }
}
```

---
