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


## sense 35311, level 7

#### Pack A
### Level 7 (sense 35311, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "この新システムにより、世界中のどこからでもデータにアクセスすることが可能ている。",
      "is_correct": false,
      "error_description": "「可能」は形状詞であり、動詞ではないため、直接「ている」を接続することはできません。「可能だ」や「可能になっている」とするのが正しい用法です。"
    },
    {
      "text": "また、限られた環境で効率的に生産を行う「資源管理」の観点からも、持続可能な食料供給の実現において重要な役割を果たしています。",
      "is_correct": true
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35311, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
      "is_correct": true
    },
    {
      "text": "近年の精密農業の導入により、小規模農家であっても効率的な経営を行うことが可能となりました。",
      "is_correct": true
    },
    {
      "text": "この新しいシステムを導入すれば、社内のデータ管理を可能となります。",
      "is_correct": false,
      "error_description": "「可能となります」は自動詞的な表現であり、その対象には主格を表す「が」を用います。「を」を用いる場合は「可能にします」とするのが正しい用法です。"
    }
  ]
}
```

---

## sense 35311, level 9

#### Pack A
### Level 9 (sense 35311, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "明日の会議はオンラインで可能です。"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "明日の会議はオンラインで可能です。",
  "chunks": [
    "明日の",
    "会議は",
    "オンラインで",
    "可能です"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "可能です",
    "明日の",
    "オンラインで",
    "会議は"
  ],
  "target_word": "可能",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。",
  "chunks": [
    "彼らは",
    "驚くべきスピードで",
    "成長しわずか数週間で",
    "市場に出荷することが",
    "可能な体重に",
    "まで達します"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "彼らは",
    "まで達します",
    "可能な体重に",
    "驚くべきスピードで",
    "市場に出荷することが",
    "成長しわずか数週間で"
  ],
  "target_word": "可能",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35311, difficulty None)
**jumbled_sentence** variant `A`, tier `advanced`
```json
{
  "original_sentence": "この計画なら、実現は可能だと思います。"
}
```
**jumbled_sentence** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "original_sentence": "この計画なら、実現は可能だと思います。",
  "chunks": [
    "この計画なら",
    "実現は",
    "可能だと",
    "思います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "思います",
    "この計画なら",
    "可能だと",
    "実現は"
  ],
  "target_word": "可能",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `advanced`
```json
{
  "original_sentence": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となっています。"
}
```
**jumbled_sentence** variant `B`, tier `advanced`
```json
{
  "schema_version": 2,
  "original_sentence": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となっています。",
  "chunks": [
    "近年精密農業の",
    "導入により",
    "小規模農家で",
    "も効率的な経営を",
    "行うことが",
    "可能となっています"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "近年精密農業の",
    "可能となっています",
    "行うことが",
    "導入により",
    "も効率的な経営を",
    "小規模農家で"
  ],
  "target_word": "可能",
  "chunk_count": 6
}
```

---

## sense 35331, level 1

#### Pack A
### Level 1 (sense 35331, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "特に",
  "options": [
    "とぐに",
    "どくに",
    "とうくに",
    "とくに"
  ],
  "correct_answer": "とくに",
  "word": "特に",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "ipa": "/tokuni/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "御国",
    "時に",
    "お国",
    "特に"
  ],
  "correct_answer": "特に",
  "explanation": "正解です。「特に」は「ほかのことと分けて、あることを強調するときに使います。」という意味です。",
  "distractor_explanations": {
    "御国": "「御国」は「特に」と一モーラだけ異なる実在語です（1モーラ目: 「と」→「お」、一部の音の違い）。",
    "時に": "「時に」は「特に」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「き」、一部の音の違い）。",
    "お国": "「お国」は「特に」と一モーラだけ異なる実在語です（1モーラ目: 「と」→「お」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "とくに",
  "options": [
    "特別",
    "特定",
    "特に",
    "特徴"
  ],
  "correct_answer": "特に",
  "word": "特に",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "特別": "component",
    "特徴": "component",
    "特定": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35331, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "特に",
  "options": [
    "とぐに",
    "どくに",
    "とうくに",
    "とくに"
  ],
  "correct_answer": "とくに",
  "word": "特に",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "ipa": "/tokuni/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "特需",
    "特に",
    "得意",
    "特殊"
  ],
  "correct_answer": "特に",
  "explanation": "正解です。「特に」は「ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。」という意味です。",
  "distractor_explanations": {
    "特殊": "「特殊」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「しゅ」、一部の音の違い）。",
    "得意": "「得意」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「い」、一部の音の違い）。",
    "特需": "「特需」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「じゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "とくに",
  "options": [
    "特別",
    "特定",
    "特に",
    "特徴"
  ],
  "correct_answer": "特に",
  "word": "特に",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "特別": "component",
    "特徴": "component",
    "特定": "component"
  }
}
```

---

## sense 35331, level 2

#### Pack A
### Level 2 (sense 35331, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "correct_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
  "options": [
    "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
    "複数の物や事柄が、一部分または全体において、互いの上にのるように位置すること。また、複数の要素が同じ部分で一致すること。",
    "眠いときや退屈なときに、無意識に口を大きく開けて息を吸い込む動作。",
    "年齢が低い、大人になっていない状態。また、それに関係する様子。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "考えや理論を、実際の行動や活動に移すこと。",
        "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
        "负荷",
        "道のことを言う言葉で、車や人が通る場所です。"
      ],
      "correct_answer": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35331, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "correct_definition": "ほかのことと分けて、あることを強調するときに使います。",
  "options": [
    "植物を植えたり育てたりして、地面を緑色で覆うこと。環境改善や景観向上のために行われる。",
    "ある地域や環境で、生物とその周囲の環境が相互に影響し合い、一つのまとまりとして機能するシステム。また、ビジネスやテクノロジーの分野でも、関係する要素が連携して全体を形作る仕組みを指す。",
    "人々が共同生活を営む集団。また、その組織や仕組み。",
    "ほかのことと分けて、あることを強調するときに使います。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "报纸 —— 每天发行、报道社会事件与信息的印刷品",
        "ほかのことと分けて、あることを強調するときに使います。",
        "目に見えない小さな生き物で、食べ物を腐らせるものもある。",
        "a procedure; steps — the staged method or order used to do something"
      ],
      "correct_answer": "ほかのことと分けて、あることを強調するときに使います。"
    }
  }
}
```

---

## sense 35331, level 3

#### Pack A
### Level 3 (sense 35331, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___好きな食べ物は何ですか。",
  "original_sentence": "特に好きな食べ物は何ですか。",
  "correct_answer": "特に",
  "options": [
    "ときどき",
    "特に",
    "そろそろ",
    "たまたま"
  ],
  "explanation": "正解。「特に」は、資本の提供だけでなく、それにとどまらない点を取り立てて強調する副詞です。",
  "distractor_tags": {},
  "word_definition": "ほかのことと分けて、あることを強調するときに使います。",
  "target_word": "特に"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___急いでいるわけではありません。",
  "original_sentence": "特に急いでいるわけではありません。",
  "correct_answer": "特に",
  "options": [
    "ぜひ",
    "特に",
    "そろそろ",
    "もっと"
  ],
  "explanation": "正解。「特に予定がありません」は、これといった予定がないことを表す決まった言い方です。",
  "distractor_tags": {},
  "word_definition": "ほかのことと分けて、あることを強調するときに使います。",
  "target_word": "特に"
}
```

#### Pack B
### Level 3 (sense 35331, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "___、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
  "original_sentence": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
  "correct_answer": "特に",
  "options": [
    "わざわざ",
    "まず",
    "たまたま",
    "特に"
  ],
  "explanation": "正解です。「特に」は、他の事柄と区別して強調する意味で使われます。",
  "distractor_tags": {},
  "word_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
  "target_word": "特に"
}
```

---

## sense 35331, level 6

#### Pack A
### Level 6 (sense 35331, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "今日は特に寒くですね。",
      "is_correct": false
    },
    {
      "text": "今日に特に寒いですね。",
      "is_correct": false
    },
    {
      "text": "特に今日はですね寒い。",
      "is_correct": false
    },
    {
      "text": "特に、今日は早く寝ます。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同です。「今日は」と主題を示すところを「今日に」とすると、時を表す「に」と「寒い」がうまくつながらず不自然です。 活用の誤りです。「ですね」の前は「寒い」のままにするので、連用形の「寒く」は使えません。 語順・係り受けの誤りです。「ですね」が述語の「寒い」の前に割り込み、文の組み立てが壊れています。",
  "target_word": "特に"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "週末は特に、海が行きたいです。",
      "is_correct": false
    },
    {
      "text": "特に決まりはありません。",
      "is_correct": true
    },
    {
      "text": "週末は海に行きたい特にです。",
      "is_correct": false
    },
    {
      "text": "週末は特に、海に行きたいでした。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同です。「行く」は自動詞で向かう先は「に」で示すため、「海が行きたい」では海が行くことになり成り立ちません。 活用・アスペクトの誤りです。「行きたい」の後ろに「でした」は付かず、過去なら「行きたかったです」とします。 語順・係り受けの誤りです。「特に」は強調する語句の前に置く副詞で、文末で名詞のように「です」を付けるのは不自然です。",
  "target_word": "特に"
}
```

#### Pack B
### Level 6 (sense 35331, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "家族の中でも、特に母に私の進学を応援してくれています。",
      "is_correct": false
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
      "is_correct": true
    },
    {
      "text": "家族の中でも、特に母が私の進学を応援するています。",
      "is_correct": false
    },
    {
      "text": "家族の中でも、母が私の進学を応援してくれています特に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「母に」と「応援してくれています」の組み合わせが不自然です。「母が」が適切です。 活用の誤り：「応援する」の連用形「し」に「ています」が結びつくべきところ、「する」のままになっており誤りです。 語順の誤り：副詞「特に」は文頭または修飾する語の直前に置きます。文末に置くことはできません。",
  "target_word": "特に"
}
```

---

## sense 35331, level 7

#### Pack A
### Level 7 (sense 35331, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "私は特に数学の勉強が好きです。",
      "is_correct": true
    },
    {
      "text": "彼は他の科目と比べて、特に数学が得意です。",
      "is_correct": true
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
      "is_correct": true
    },
    {
      "text": "私は特には数学の勉強が好きです。",
      "is_correct": false,
      "error_description": "副詞「特に」に助詞「は」を付けて「特には」とすることはできません。「特に」のままで使用します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "家族の中でも、特に母が私の進学を応援してくれています。",
      "is_correct": true
    },
    {
      "text": "彼は他の分野と比べて、特ににサッカーを打ち込んでいます。",
      "is_correct": false,
      "error_description": "「特に」は副詞であるため、後に助詞「に」を付けることはできません。「特にサッカーに」とするのが正しい用法です。"
    },
    {
      "text": "彼は他の分野と比べて、特にサッカーに打ち込んでいます。",
      "is_correct": true
    },
    {
      "text": "今朝のニュースの中で、特に寒波に関する注意報が発令されました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35331, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "特に大切な友達です。",
      "is_correct": true
    },
    {
      "text": "特に好きな食べ物は何ですか。",
      "is_correct": true
    },
    {
      "text": "特に注意して歩いてください。",
      "is_correct": true
    },
    {
      "text": "今日は寒い特にですね。",
      "is_correct": false,
      "error_description": "語順の誤り。副詞「特に」は修飾する語の前に置くので、「寒い特に」ではなく「特に寒い」が正しい。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "今日は特にの用事がありません。",
      "is_correct": false,
      "error_description": "助詞の誤り。「特に」は副詞なので、「の」を付けて名詞を修飾することはできない。「特に用事が」が正しい。"
    },
    {
      "text": "特に急いでいるわけではありません。",
      "is_correct": true
    },
    {
      "text": "特に意見はありません。",
      "is_correct": true
    },
    {
      "text": "特に決まりはありません。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35341, level 1

#### Pack A
### Level 1 (sense 35341, difficulty None)
**kanji_to_reading** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "不可欠",
  "options": [
    "ふかげつ",
    "ふがけつ",
    "ふかけづ",
    "ふかけつ"
  ],
  "correct_answer": "ふかけつ",
  "word": "不可欠",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "ipa": "/fukaketsu/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "風穴",
    "負荷率",
    "不可欠",
    "付加刑"
  ],
  "correct_answer": "不可欠",
  "explanation": "正解です。「不可欠」は「ある物事をするために、どうしても必要であること。」という意味です。",
  "distractor_explanations": {
    "付加刑": "「付加刑」は「不可欠」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "負荷率": "「負荷率」は「不可欠」と一モーラだけ異なる実在語です（3モーラ目: 「け」→「り」、一部の音の違い）。",
    "風穴": "「風穴」は「不可欠」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「う」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `T5`
```json
{
  "schema_version": 2,
  "prompt": "ふかけつ",
  "options": [
    "社内外",
    "大丈夫",
    "不可欠",
    "不可避"
  ],
  "correct_answer": "不可欠",
  "word": "不可欠",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "社内外": "component",
    "大丈夫": "component",
    "不可避": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35341, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "不可欠",
  "options": [
    "ふかげつ",
    "ふがけつ",
    "ふかけづ",
    "ふかけつ"
  ],
  "correct_answer": "ふかけつ",
  "word": "不可欠",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "ふかけつ",
  "options": [
    "社内外",
    "大丈夫",
    "不可欠",
    "不可避"
  ],
  "correct_answer": "不可欠",
  "word": "不可欠",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "社内外": "component",
    "大丈夫": "component",
    "不可避": "component"
  }
}
```

---

## sense 35341, level 2

#### Pack A
### Level 2 (sense 35341, difficulty None)
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "correct_definition": "ある物事をするために、どうしても必要であること。",
  "options": [
    "「ある」は存在を表す動詞で、物や事柄が存在することを示します。「ます」は丁寧な表現を作る助動詞です。",
    "ある物事をするために、どうしても必要であること。",
    "意見や利害の対立から起こる、言い合いやけんか。",
    "飛行機などの翼に働く、上向きの力。空気の流れの差によって生じ、機体を支える。"
  ]
}
```
**definition_match** variant `A`, tier `T5`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "tier": "T5",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある物事が持つ、良い結果や役に立つ性質。",
        "「カーボン」は、石炭や木炭のもとになる、黒い色の物質のことです。",
        "ある物事をするために、どうしても必要であること。",
        "trust"
      ],
      "correct_answer": "ある物事をするために、どうしても必要であること。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35341, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "correct_definition": "何かをするために、どうしても必要なこと。",
  "options": [
    "あるものや状態を、意図的あるいは自然に作り出すこと。",
    "「ます」は、動詞の後ろについて、丁寧な表現を作る助動詞です。現在・未来の動作や状態を丁寧に述べるときに使います。",
    "危険や困難を恐れずに、自分の信念や正しいと思うことに向かって進む心の力。",
    "何かをするために、どうしても必要なこと。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "不可欠",
  "pronunciation": "ふかけつ",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "何かが起こるもとになったこと。",
        "to win",
        "何かをするために、どうしても必要なこと。",
        "courage; bravery in the face of fear or difficulty"
      ],
      "correct_answer": "何かをするために、どうしても必要なこと。"
    }
  }
}
```

---

## sense 35341, level 3

#### Pack A
### Level 3 (sense 35341, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "correct_answer": "不可欠",
  "options": [
    "不変",
    "不可欠",
    "不可解",
    "不要"
  ],
  "explanation": "正解です。文脈から、職人の緻密な管理が「どうしても必要」であることがわかります。",
  "distractor_tags": {},
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "信頼は友達に___なものです。",
  "original_sentence": "信頼は友達に不可欠なものです。",
  "correct_answer": "不可欠",
  "options": [
    "必要",
    "不可欠",
    "重要",
    "十分"
  ],
  "explanation": "「彼の助けは不可欠だった」はどうしても必要なことを表す固定表現。",
  "distractor_tags": {},
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

#### Pack B
### Level 3 (sense 35341, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "そこに、発酵の___な役割が凝縮されているのです。",
  "original_sentence": "そこに、発酵の不可欠な役割が凝縮されているのです。",
  "correct_answer": "不可欠",
  "options": [
    "不十分",
    "不可欠",
    "不規則",
    "不可解"
  ],
  "explanation": "正解です。発酵において重要な役割を果たすことを表しています。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "信頼は、友人との関係に___な要素です。",
  "original_sentence": "信頼は、友人との関係に不可欠な要素です。",
  "correct_answer": "不可欠",
  "options": [
    "不可避",
    "不十分",
    "不相応",
    "不可欠"
  ],
  "explanation": "正解です。文脈上、信頼は友人関係において「どうしても必要」なものであり、形状詞「不可欠」が適切に機能しています。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```

---
