# Pairwise review pack 01

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


## sense 34998, level 1

#### Pack A
### Level 1 (sense 34998, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "ipa": "/it͡ɕi/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "一",
    "家",
    "井戸",
    "自知"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "自知": "「自知」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「じ」、一部の音の違い）。",
    "家": "「家」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「う」、一部の音の違い）。",
    "井戸": "「井戸」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 34998, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "ipa": "/itɕi/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "糸",
    "言う",
    "行き",
    "一"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "行き": "「行き」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「き」、一部の音の違い）。",
    "糸": "「糸」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「と」、一部の音の違い）。",
    "言う": "「言う」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「う」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 34998, level 3

#### Pack A
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "試験の答えは「___」です。",
  "original_sentence": "試験の答えは「一」です。",
  "correct_answer": "一",
  "options": [
    "全て",
    "一",
    "理由",
    "一の"
  ],
  "explanation": "正解です。文脈に合う「ひとつだけの数」を表す名詞です。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

#### Pack B
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "机の上に本が___冊あります。",
  "original_sentence": "机の上に本が一冊あります。",
  "correct_answer": "一",
  "options": [
    "一",
    "多",
    "毎",
    "全"
  ],
  "explanation": "正解です。文脈「机の上に本が＿冊あります」において、数を表す「一」が適切です。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "公園で犬を___匹見かけました。",
  "original_sentence": "公園で犬を一匹見かけました。",
  "correct_answer": "一",
  "options": [
    "公園",
    "一",
    "犬",
    "大きい"
  ],
  "explanation": "正解です。動物を数える助数詞「匹」の前には、数を表す「一」が入ります。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

---

## sense 34998, level 4

#### Pack A
### Level 4 (sense 34998, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "私は鉛筆___一本持っています。",
  "original_sentence": "私は鉛筆を一本持っています。",
  "options": [
    "で",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "一",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「持つ」の直接目的語（鉛筆）を標示する格助詞です。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 34998, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一___始めてください。",
  "original_sentence": "一から始めてください。",
  "options": [
    "で",
    "から",
    "まで",
    "に"
  ],
  "correct_answer": "から",
  "target_word": "一",
  "error_tags": {
    "まで": "source_vs_goal",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "物事の起点を標示する格助詞であり、「一」を始まりとして順に進めることを表す。"
    }
  }
}
```

---

## sense 34998, level 6

#### Pack A
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "正解の一は数です。",
      "is_correct": false
    },
    {
      "text": "正解の数は一匹です。",
      "is_correct": false
    },
    {
      "text": "正解の数は一です。",
      "is_correct": true
    },
    {
      "text": "正解の数へ一です。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「数」に対する助数詞として「匹」は不適切です。 助詞の混同：主題や説明を表す助詞は「は」が適切で、「へ」は方向を表すため不適切です。 語順・係り受けの誤り：「正解の数」という名詞句が分断され、意味が通じなくなっています。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一からやり直してあります。",
      "is_correct": false
    },
    {
      "text": "一まで数えます。",
      "is_correct": false
    },
    {
      "text": "一冊の犬を飼っています。",
      "is_correct": false
    },
    {
      "text": "一からやり直しています。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：犬を数えるときは「一匹」を用い、「一冊」は本やノートなどに使います。 助詞の混同：数え始めを表すときは「から」を用い、「まで」は終わりを表します。 アスペクトの誤り：「やり直す」のような動作動詞の結果の状態を表す場合は「ています」を用い、「てあります」は他動詞の意図的な結果の残存に用います。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "昨日、りんごを一個食べました。",
      "is_correct": true
    },
    {
      "text": "昨日、りんごを一匹食べました。",
      "is_correct": false
    },
    {
      "text": "昨日、りんごを一枚食べました。",
      "is_correct": false
    },
    {
      "text": "昨日、りんごを一本食べました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：細長いものには「本」を使いますが、丸い果物であるりんごには「個」を使うのが適切です。 助数詞の誤り：「匹」は動物に使う助数詞です。植物の果実であるりんごには使えません。 助数詞の誤り：「枚」は薄くて平たいものに使う助数詞です。立体感のあるりんごには「個」が適切です。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "カバンの中は鍵が一入っています。",
      "is_correct": false
    },
    {
      "text": "カバンの中に鍵が一冊入っています。",
      "is_correct": false
    },
    {
      "text": "カバンの中に鍵が一つ入っています。",
      "is_correct": true
    },
    {
      "text": "カバンの中に鍵が一入りています。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「冊」は本や雑誌など、綴じられた物を数える際に用います。鍵のような小物を数える場合は「個」や「つ」を用いるべきです。 助詞の混同：存在や状態を表す文では、場所を示す「に」または主題を示す「は」を用いますが、ここでの「中」に対する格助詞として「は」を用い、主語を「鍵が」とすると文法的に不自然、あるいは意味焦点がずれます。元の文「中に～が」の構造に対し、場所の主格化が不適切です。より明確な誤りとしては、存在文の構文エラーとして捉えます。 活用・アスペクトの誤り：動詞「入る」のテ形は「入って」です。「入りて」は文語的あるいは誤った活用形であり、現代口語の「～ています」の形にはなりません。",
  "target_word": "一"
}
```

---

## sense 34998, level 7

#### Pack A
### Level 7 (sense 34998, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一が足りなくて困りました。",
      "is_correct": true
    },
    {
      "text": "一からやり直しています。",
      "is_correct": true
    },
    {
      "text": "一を足して二にします。",
      "is_correct": true
    },
    {
      "text": "一が足して二にします。",
      "is_correct": false,
      "error_description": "助詞の混同。他動詞「足す」の目的語を示す助詞は「を」です。「一が足して」は誤りです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 34998, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "机の上に本が一冊あります。",
      "is_correct": true
    },
    {
      "text": "机の上に本が一匹あります。",
      "is_correct": false,
      "error_description": "助数詞の誤りです。「本」を数える場合は「冊」を使います。「匹」は動物を数える際に使用します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "公園で犬を一匹見かけました。",
      "is_correct": true
    },
    {
      "text": "花瓶に花が一輪咲いています。",
      "is_correct": true
    },
    {
      "text": "カバンの中に鍵が一つ入っています。",
      "is_correct": true
    },
    {
      "text": "公園で犬を一輪見かけました。",
      "is_correct": false,
      "error_description": "助数詞の誤りです。「犬」のような動物を数える場合は「匹」を使います。「輪」は花や車輪など丸いものを数える際に用います。"
    }
  ]
}
```

---

## sense 34999, level 3

#### Pack A
### Level 3 (sense 34999, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この絵画は、___から丁寧に描き上げました。",
  "original_sentence": "この絵画は、一から丁寧に描き上げました。",
  "correct_answer": "一",
  "options": [
    "表",
    "一",
    "末",
    "二"
  ],
  "explanation": "「一から」で「最初から」という意味の慣用的な表現になります。",
  "distractor_tags": {},
  "word_definition": "数や順番の最初。一つだけ。",
  "target_word": "一"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___つの目標に向かって頑張っています。",
  "original_sentence": "一つの目標に向かって頑張っています。",
  "correct_answer": "一",
  "options": [
    "二",
    "幾",
    "一",
    "万"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "数や順番の最初。一つだけ。",
  "target_word": "一"
}
```

#### Pack B
### Level 3 (sense 34999, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "こうして、___枚の絵画が完成します。",
  "original_sentence": "こうして、一枚の絵画が完成します。",
  "correct_answer": "一",
  "options": [
    "毎",
    "何",
    "一",
    "全"
  ],
  "explanation": "正解です。文脈「こうして、[ ]枚の絵画が完成します」において、数量を限定する連体詞として適切です。",
  "distractor_tags": {},
  "word_definition": "数や順番の最初。一つだけ。",
  "target_word": "一"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "カレンダーの___日を赤く丸で囲みました。",
  "original_sentence": "カレンダーの一日を赤く丸で囲みました。",
  "correct_answer": "一",
  "options": [
    "一",
    "毎",
    "初",
    "全"
  ],
  "explanation": "正解です。カレンダーの日付を示す「一日（ついたち／いちにち）」という表現において、数を表す「一」が使われます。",
  "distractor_tags": {},
  "word_definition": "数や順番の最初。一つだけ。",
  "target_word": "一"
}
```

---

## sense 34999, level 6

#### Pack A
### Level 6 (sense 34999, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は一冊の意見を持っています。",
      "is_correct": false
    },
    {
      "text": "私は一つに意見を持っています。",
      "is_correct": false
    },
    {
      "text": "一つ私はの意見を持っています。",
      "is_correct": false
    },
    {
      "text": "私は一つの意見を持っています。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「意見」に使う助数詞は「冊」ではなく「つ」や「個」です。「一つの」が正しいです。 助詞の混同：所有や付帯状況を表す場合は「に」ではなく「の」を使います。「一つの意見」が正しいです。 語順・係り受けの誤り：連体修飾語「一つの」は被修飾語「意見」の直前に置く必要があります。語順が誤っています。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一まで十から覚えてきました。",
      "is_correct": false
    },
    {
      "text": "一から十までが覚えてきました。",
      "is_correct": false
    },
    {
      "text": "一から十まで覚えてあります。",
      "is_correct": false
    },
    {
      "text": "一から十まで覚えてきました。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：「一から十まで」は範囲を表す副詞的用法であり、主格助詞「が」は不適切です。 語順・係り受けの誤り：「一から十まで」は固定した語順の慣用表現であり、入れ替えると意味が破綻します。 活用・アスペクトの誤り：「てある」は他動詞の結果の残存を表すため、経験を表すこの文脈では「てきた」が適切です。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34999, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "箱の中には、一匹のおもちゃが入っています。",
      "is_correct": false
    },
    {
      "text": "箱の中には、一つのおもちゃが入っています。",
      "is_correct": true
    },
    {
      "text": "箱の中はおもちゃが一入っています。",
      "is_correct": false
    },
    {
      "text": "箱の中に一のおもちゃが入っています。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「おもちゃ」は動物ではないため、「一匹」ではなく「一つ」などの助数詞を使う必要があります。 連語の誤り：連体詞「一」は名詞を直接修飾せず、通常は助数詞（例：一つ）を伴って数量を表します。 語順・係り受けの誤り：連体詞「一」は名詞の前に置く必要があり、動詞の前に置くことはできません。",
  "target_word": "一"
}
```

---

## sense 34999, level 7

#### Pack A
### Level 7 (sense 34999, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "親である私にできるのは、その勇気ある第一歩を、ただ静かに、そして確かな祈りを込めて見守ることだけです。",
      "is_correct": true
    },
    {
      "text": "その一つひとつの動作が、彼女の認知能力と社会性を育む養分となります。",
      "is_correct": true
    },
    {
      "text": "この絵画は、一から丁寧に描き上げました。",
      "is_correct": true
    },
    {
      "text": "この絵画は、一を丁寧に描き上げました。",
      "is_correct": false,
      "error_description": "助詞の混同。「一から」は「何もない状態から」という意味の慣用表現であり、「一を」とは言いません。正しくは「一から」となります。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一つずつ順番に並んでいます。",
      "is_correct": true
    },
    {
      "text": "一から十まで覚えてきました。",
      "is_correct": true
    },
    {
      "text": "一つの目標に向かって頑張っています。",
      "is_correct": true
    },
    {
      "text": "一つの目標は向かって頑張っています。",
      "is_correct": false,
      "error_description": "助詞の混同。「目標」は「向かう」の方向・対象を表すため、助詞「は」ではなく「に」または「へ」を使うのが正しいです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 34999, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "机の上には、一つのリンゴが置かれています。",
      "is_correct": true
    },
    {
      "text": "机の上には、一匹のリンゴが置かれています。",
      "is_correct": false,
      "error_description": "助数詞の誤りです。「リンゴ」のような球形や塊状の物を数える場合は「個」や「つ」を使います。「匹」は動物を数える際に用いる助数詞です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "このケーキを一つください。",
      "is_correct": true
    },
    {
      "text": "その日は、月の一日でした。",
      "is_correct": true
    },
    {
      "text": "カレンダーの一日を赤く丸で囲みました。",
      "is_correct": true
    },
    {
      "text": "このケーキを一冊ください。",
      "is_correct": false,
      "error_description": "ケーキのような個数で数える物体には助数詞「個」や「つ」を使います。「冊」は本や雑誌など、綴じられた物に使うため不適切です。"
    }
  ]
}
```

---

## sense 35001, level 1

#### Pack A
### Level 1 (sense 35001, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "/kikai/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "機械",
    "規程",
    "自壊",
    "嫌い"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「動力や電気で動き、人間の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "嫌い": "「嫌い」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「ら」、一部の音の違い）。",
    "自壊": "「自壊」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「じ」、一部の音の違い）。",
    "規程": "「規程」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「て」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35001, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "kikai",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "既定",
    "棄世",
    "耳介",
    "機械"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「動力や電気で動き、人間の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "棄世": "「棄世」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「せ」、一部の音の違い）。",
    "耳介": "「耳介」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「じ」、一部の音の違い）。",
    "既定": "「既定」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「て」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35001, level 6

#### Pack A
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "機械はで壊れてしまいました。",
      "is_correct": false
    },
    {
      "text": "機械が壊れていますしまいました。",
      "is_correct": false
    },
    {
      "text": "一冊の機械が壊れてしまいました。",
      "is_correct": false
    },
    {
      "text": "機械が壊れてしまいました。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：不正解です。「冊」は本やノートなど紙でできた物を数える際に使います。機械のような装置には「台」を使います。 助詞の混同：不正解です。主語を示す助詞「が」または「は」が必要です。「で」は手段や場所を表すため、ここでは文法的に誤りです。 活用・アスペクトの誤り：不正解です。「ています」は状態の継続を表し、「てしまいました」は完了や後悔を表します。これらを重ねて使うことはできません。正しくは「壊れてしまいました」です。",
  "target_word": "機械"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "機械で絵を描けます。",
      "is_correct": true
    },
    {
      "text": "機械に絵を描けます。",
      "is_correct": false
    },
    {
      "text": "機械は絵を描けます。",
      "is_correct": false
    },
    {
      "text": "一冊の機械で絵を描けます。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「機械」のような一般の器物や装置を数える際は「台（だい）」や「個（こ）」を用います。「冊（さつ）」は本やノートなど綴じられた物を数える助数詞です。 助詞の混同：手段・道具を表す場合は「で」を使います。「に」を使うと、機械そのものに対して絵を描きつける（落書きするなど）意味になり、文脈「描けます（能力・可能）」との組み合わせとして不自然です。 意味・主語の誤り：「機械」自体が主体となって自発的に絵を描く能力を持っているように聞こえます。人間が機械という道具を使って描くという意味であれば、「機械で」とするべきです。",
  "target_word": "機械"
}
```

#### Pack B
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この機械は昨日壊れてある。",
      "is_correct": false
    },
    {
      "text": "工場には新しい機械が三冊導入された。",
      "is_correct": false
    },
    {
      "text": "機械を作る人はすごいです。",
      "is_correct": true
    },
    {
      "text": "機械を人間の代わりに仕事をする。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：機械の助数詞は「台」や「個」であり、本や雑誌などに使う「冊」は誤りです。 助詞の混同：動作の主体である機械を示すには「が」が必要であり、「を」は誤りです。 アスペクトの誤り：「壊れる」は自動詞であり、他動詞の結果状態を表す「てある」は結びつきません。「壊れている」が適切です。",
  "target_word": "機械"
}
```

---
