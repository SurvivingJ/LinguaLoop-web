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


## sense 35127, level 7

#### Pack A
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "この地域には総合病院がなく、住民たちは毎回遠くまで通院しなければならない状況です。",
      "is_correct": true
    },
    {
      "text": "現在のプロジェクトには十分な資金がなく、新たな投資家を探すのが急務となっています。",
      "is_correct": true
    },
    {
      "text": "この地域には総合病院がなくなくて、住民たちは毎回遠くまで通院しなければならない状況です。",
      "is_correct": false,
      "error_description": "誤り型：活用・アスペクトの誤り。形容詞「ない」の連用形「なく」に、さらに口語的な接続助詞「なくて」を冗長に付加しており、文法的に誤っています。正しくは「なく」とします。"
    },
    {
      "text": "この山奥の村には満足な医療施設がなく、住民たちはいざという時に大変な不安を抱えています。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "彼の説明には裏付けるための証拠がなく、周囲の人間を納得させることはできませんでした。",
      "is_correct": true
    },
    {
      "text": "この部屋には収納するためのクローゼットがなく、家具の配置にとても頭を悩ませています。",
      "is_correct": true
    },
    {
      "text": "大切な書類がないことに気づいて、慌てて探した。",
      "is_correct": true
    },
    {
      "text": "彼の説明には裏付けるための証拠がなくて、周囲の人間を納得させることはできませんでした。",
      "is_correct": false,
      "error_description": "誤り型：活用・接続の誤り。正しい形：「なく」。解説：「証拠がなくて」は文法的に間違いではありませんが、「証拠がなく、〜できない」という形式的な書き言葉の文脈では、中頓を表す連用形「なく」を用いるのが自然で適切です。「なくて」は口語的であり、原因・理由のニュアンスが強くなるため、この文の硬い表現には馴染みません。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
      "is_correct": true
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りなければなりません。",
      "is_correct": true
    },
    {
      "text": "机の上で消しゴムがなく、友達に借りなければなりません。",
      "is_correct": false,
      "error_description": "助詞の混同（に／で）。物が存在する場所を表す場合は助詞「に」を使います。「で」は動作が行われる場所を表すため、この文脈では誤りです。"
    },
    {
      "text": "この地域には大きなスーパーがなく、日々の買い物をするのにとても不便です。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35147, level 1

#### Pack A
### Level 1 (sense 35147, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "ipa": "/iku/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "奥",
    "行く",
    "柵",
    "入る"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。また、物事が進む。」という意味です。",
  "distractor_explanations": {
    "奥": "「奥」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「お」、一部の音の違い）。",
    "入る": "「入る」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「る」、一部の音の違い）。",
    "柵": "「柵」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「さ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35147, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "行く",
  "pronunciation": "いく",
  "ipa": "/iku/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "鋳る",
    "ズク",
    "行く",
    "遺址"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。また、物事が進む。」という意味です。",
  "distractor_explanations": {
    "ズク": "「ズク」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ず」、一部の音の違い）。",
    "鋳る": "「鋳る」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「る」、一部の音の違い）。",
    "遺址": "「遺址」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「し」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35147, level 4

#### Pack A
### Level 4 (sense 35147, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "友達と映画を見に___。",
  "original_sentence": "友達と映画を見に行っています。",
  "correct_answer": "いった",
  "base_form": "行く",
  "form_label": "た形（過去）",
  "options": [
    "いく",
    "いった",
    "いって",
    "いかない"
  ],
  "explanation": "「昨日」があるので過去のた形が必要。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行っています"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この道は狭くて、車で___。",
  "original_sentence": "この道は狭くて、車で行けません。",
  "correct_answer": "行けません",
  "base_form": "行く",
  "form_label": "可能＋ない形（丁寧）",
  "options": [
    "行きません",
    "行ける",
    "行きます",
    "行けません"
  ],
  "explanation": "「狭くて」により不可能な状況なので、可能の否定形が適切です。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行けません"
}
```

#### Pack B
### Level 4 (sense 35147, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "休みの日は、よく家族と公園へ___ませんか。",
  "original_sentence": "休みの日は、よく家族と公園へ行きませんか。",
  "correct_answer": "行き",
  "base_form": "行く",
  "form_label": "連用形（ます形語幹）",
  "options": [
    "行く",
    "行き",
    "行って",
    "行か"
  ],
  "explanation": "「ませんか」に接続するため、動詞の連用形（ます形語幹）が必要です。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行き"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "計画は順調に___ません。",
  "original_sentence": "計画は順調に行きません。",
  "correct_answer": "行き",
  "base_form": "行く",
  "form_label": "連用形（ます形）",
  "options": [
    "行かない",
    "行く",
    "行き",
    "行って"
  ],
  "explanation": "「ません」に接続するには連用形（ます形）の「行き」が必要です。",
  "word_definition": "ある場所から別の場所へ移動する。また、物事が進む。",
  "target_word": "行き"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "来週、私たちは一緒に東京___行きましょう。",
  "original_sentence": "来週、私たちは一緒に東京へ行きましょう。",
  "options": [
    "へ",
    "で",
    "を",
    "が"
  ],
  "correct_answer": "へ",
  "target_word": "行き",
  "error_tags": {
    "を": "object_marking",
    "が": "topic_vs_subject",
    "で": "location_vs_target"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "移動の方向や着点を示す格助詞「へ」が、動詞「行き」の目的地を正しく標示する"
    }
  }
}
```

---

## sense 35147, level 6

#### Pack A
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この切符で、新宿まで行きません。",
      "is_correct": false
    },
    {
      "text": "このバスは、どのルートを経由して行きません。",
      "is_correct": false
    },
    {
      "text": "明日の会議には、どの電車で行きません。",
      "is_correct": false
    },
    {
      "text": "このバスは、どのルートを経由して行きません。",
      "is_correct": true
    }
  ],
  "explanation": "語順・係り受けの誤り：「どの電車」で移動するかを尋ねる疑問詞を含む文で、否定の「行きません」を結びつけると意味が破綻します。「どの電車で行きますか」とするのが自然です。 語順・係り受けの誤り：「どのルート」を経由するのかを問う疑問詞の文であり、否定形「行きません」とは結びつきません。「どのルートを経由して行きますか」とすべきです。 助詞の混同：「この切符で」は手段や方法を表しますが、単に「新宿まで行く」という事実を述べる文脈では、存在・場所を表す「は」や、単に動作を提示する形が適切であり、「で」を用いて否定するのは不自然です。",
  "target_word": "行く"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "行き",
  "relation": "antonym",
  "options": [
    "来",
    "帰",
    "止",
    "出"
  ],
  "correct_answer": "来",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "目標語の「行き」は「行く」の連用形であり、話し手や基準点へ移動する「来る」の連用形「来（き）」が対義語として成立します。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "もう行きません。",
      "is_correct": false
    },
    {
      "text": "もう行きません。",
      "is_correct": true
    },
    {
      "text": "もう行き行きました。",
      "is_correct": false
    },
    {
      "text": "もう一行きません。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：動作の回数には「一回」を用います。「一」だけでは回数を表す接尾辞として機能しません。 助詞の混同：「行きます」の否定形は「行きません」です。「ません」は存在や所有の否定「ありません」の混同です。 活用・アスペクトの誤り：動詞の連用形が重複しており、文法的に成立しません。過去の完了は「行きました」とします。",
  "target_word": "行っ"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "行き",
  "relation": "antonym",
  "options": [
    "来",
    "居",
    "戻り",
    "止まり"
  ],
  "correct_answer": "来",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある場所から別の場所へ移動する。また、物事が進む。",
      "explanation": "対象の場所へ移動する動作を表し、目標語の「行き」と対義関係にある。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "来週、私は東京を行けます。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けています。",
      "is_correct": false
    },
    {
      "text": "来週、私は東京に行けます。",
      "is_correct": true
    },
    {
      "text": "行けます私は来週、東京に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：目的地を表す場合は「に」を使います。「を」は通過点を表します。 活用・アスペクトの誤り：未来の事柄「来週」に対して、状態継続の「ています」は使えません。 語順の誤り：日本語の動詞は文末に置きます。また、主題「私は」は文の初めに置くのが自然です。",
  "target_word": "行けます"
}
```

---

## sense 35147, level 7

#### Pack A
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は毎日学校に行きます。",
      "is_correct": true
    },
    {
      "text": "昨日行った公園は広かったです。",
      "is_correct": true
    },
    {
      "text": "友達と映画を見に行っています。",
      "is_correct": true
    },
    {
      "text": "彼と一緒に行くには楽しい。",
      "is_correct": false,
      "error_description": "助詞：名詞化の「の」を「に」に置き換えるのは誤り。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "雨が降っているけど、傘を持たずに行きます。",
      "is_correct": true
    },
    {
      "text": "この道は狭くて、車で行けません。",
      "is_correct": true
    },
    {
      "text": "私は毎日電車を使って学校を行きます。",
      "is_correct": false,
      "error_description": "目的地を表す助詞は「に」または「へ」を使います。「を」は移動の経路や通過点に使います。"
    },
    {
      "text": "電車に乗って、町に行って、買い物しました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "休みの日は、よく家族と公園へ行きです。",
      "is_correct": false,
      "error_description": "「行き」は動詞「行く」の連用形であり、単独で「です」に接続して述語を作ることはできません。習慣や誘いを表す文脈では、「行きませんか」や「行きます」などの適切な活用形を用いる必要があります。"
    },
    {
      "text": "来週、私たちは一緒に東京へ行きましょう。",
      "is_correct": true
    },
    {
      "text": "明日の会議には、どの電車で行きません。",
      "is_correct": true
    },
    {
      "text": "休みの日は、よく家族と公園へ行きませんか。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "もう行きません。",
      "is_correct": true
    },
    {
      "text": "計画は順調に行きません。",
      "is_correct": true
    },
    {
      "text": "この電車は、大阪へ行きません。",
      "is_correct": true
    },
    {
      "text": "明日の会議には、どの電車で行きません。",
      "is_correct": false,
      "error_description": "「会議には」は目的地ではなく手段や手段の範囲を表すため、移動の帰着点を示す「へ」や「に」ではなく、手段・方法を表す「で」を使うのが適切です。"
    }
  ]
}
```

---

## sense 35201, level 4

#### Pack A
### Level 4 (sense 35201, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "多くの要素が互いに影響し合うことで、予測できない新しい秩序をもたらし、全体として一つのまとまったシステムが形成されるのである。",
  "original_sentence": "多くの要素が互いに影響し合うことで、予測できない新しい秩序をもたらし、全体として一つのまとまったシステムが形成されるのである。",
  "correct_answer": "もたらし",
  "base_form": "もたらす",
  "form_label": "連用形（中止法）",
  "options": [
    "もたらさない",
    "もたらそう",
    "もたらし",
    "もたらした"
  ],
  "explanation": "連用形で読点の後の句へつなぐ中止法になる",
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらす"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "技術革新は社会に劇的な変化をもたらし、我々の生活様式を変革する。",
  "original_sentence": "技術革新は社会に劇的な変化をもたらし、我々の生活様式を変革する。",
  "correct_answer": "もたらし",
  "base_form": "もたらす",
  "form_label": "て形（連用形）",
  "options": [
    "もたらし",
    "もたらす",
    "もたらした",
    "もたらさ"
  ],
  "explanation": "「てくれた」に続く連用形",
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらされる"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "技術革新は社会に劇的な変化___もたらし、我々の生活様式を変革する。",
  "original_sentence": "技術革新は社会に劇的な変化をもたらし、我々の生活様式を変革する。",
  "options": [
    "が",
    "で",
    "に",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "もたらされる",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「もたらす」の直接目的語を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35201, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "多くの要素が様々に影響し合うことで、思いがけない新しい結果___もたらして、私たちの社会はさらに豊かに発展していくのです。",
  "original_sentence": "多くの要素が様々に影響し合うことで、思いがけない新しい結果をもたらして、私たちの社会はさらに豊かに発展していくのです。",
  "options": [
    "で",
    "が",
    "に",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "もたらす",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「もたらす」の直接目的語「結果」を標示する格助詞"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "新しい技術は生活___便利さをもたらして、私たちの毎日をより豊かなものにしています。",
  "original_sentence": "新しい技術は生活に便利さをもたらして、私たちの毎日をより豊かなものにしています。",
  "options": [
    "が",
    "に",
    "で",
    "を"
  ],
  "correct_answer": "に",
  "target_word": "もたらす",
  "error_tags": {
    "を": "object_marking",
    "で": "instrument",
    "が": "topic_vs_subject"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "利益や影響の及ぶ対象（着点）を標示する格助詞「に」が適切である。"
    }
  }
}
```

---

## sense 35201, level 6

#### Pack A
### Level 6 (sense 35201, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "甘味と塩気のバランスが絶妙で、短時間で体力を回復する効果をもたらして、忙しい現代人にとって理にかなった便利な食事となっています。",
      "is_correct": false
    },
    {
      "text": "甘味と塩気のバランスが絶妙で、短時間で体力を回復する効果をもたらして、忙しい現代人にとって理にかなった便利な食事となっています。",
      "is_correct": false
    },
    {
      "text": "甘味と塩気のバランスが絶妙で、短時間で体力を回復する効果をもたらして、忙しい現代人にとって理にかなった便利な食事となっています。",
      "is_correct": false
    },
    {
      "text": "甘味と塩気のバランスが絶妙で、短時間で体力を回復する効果をもたらして、忙しい現代人にとって理にかなった便利な食事となっています。",
      "is_correct": true
    }
  ],
  "explanation": "誤り：「効果をもたらして」の後に続く「忙しい現代人にとって」への接続が不自然です。「もたらして」は他動詞のて形であり、直後に「効果を」という目的語を既に取っているため、続けて「〜にとって（は）」という評価の枠組みを提示する文型にはスムーズに繋がりません。 誤り：「効果をもたらして」の後に続く「忙しい現代人にとって」への接続が不自然です。「もたらして」は他動詞のて形であり、直後に「効果を」という目的語を既に取っているため、続けて「〜にとって（は）」という評価の枠組みを提示する文型にはスムーズに繋がりません。 誤り：「効果をもたらして」の後に続く「忙しい現代人にとって」への接続が不自然です。「もたらして」は他動詞のて形であり、直後に「効果を」という目的語を既に取っているため、続けて「〜にとって（は）」という評価の枠組みを提示する文型にはスムーズに繋がりません。",
  "target_word": "もたらし"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "もたらして",
  "relation": "antonym",
  "options": [
    "与える",
    "生み出す",
    "届ける",
    "奪う"
  ],
  "correct_answer": "奪う",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
      "explanation": "与えたり生じさせたりする「もたらす」に対し、既にあるものを取り上げてなくさせる点で対義関係にある"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "運動は健康を良い結果をもたらす。",
      "is_correct": false
    },
    {
      "text": "ボランティア活動は社会に大きな変化をもたらして、多くの人々を勇気づけています。",
      "is_correct": true
    },
    {
      "text": "運動は昨日健康に良い結果をもたらす。",
      "is_correct": false
    },
    {
      "text": "運動は健康に良い結果をもたらしてある。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：影響を受ける先は「に」で示し、「健康に良い」が正しい。 活用・アスペクトの誤り：過去の「昨日」に非過去形は合わない。 アスペクトの誤り：「てある」は意図的な動作の結果に使い、この文には合わない。",
  "target_word": "もたらす"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "もたらして",
  "relation": "antonym",
  "options": [
    "与える",
    "生み出す",
    "奪う",
    "届ける"
  ],
  "correct_answer": "奪う",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
      "explanation": "対象となる物事や状態を無理やり取り上げて失わせる点で、与え引き起こす「もたらす」の対義語となる。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35201, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "昨日、台風が被害もたらしたを。",
      "is_correct": false
    },
    {
      "text": "異なる食材を組み合わせることは、単独では得られない深い味をもたらし、食事の満足度を大きく高める結果となる。",
      "is_correct": true
    },
    {
      "text": "明日、台風が被害をもたらした。",
      "is_correct": false
    },
    {
      "text": "新しい薬が希望がもたらす。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：もたらすものは「を」で示し、「希望をもたらす」が正しい。 活用・アスペクトの誤り：未来の「明日」に過去形は合わない。 語順の誤り：助詞「を」は目的語「被害」の直後に置き、「被害をもたらした」とする。",
  "target_word": "もたらし"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "心に安らぎをもたらして、精神を落ち着かせる音楽を聴く時間を持つ。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "心に安らぎをもたらした、精神を落ち着かせる音楽を聴く時間を持つ。",
      "is_correct": false
    },
    {
      "text": "心に安らぎをもたらしに、精神を落ち着かせる音楽を聴く時間を持つ。",
      "is_correct": false
    }
  ],
  "explanation": "語順・係り受けの誤り：「もたらしに」とすると目的を表し、「音楽を聴く時間を持つ」ことが「安らぎをもたらすための手段」という不自然な意味関係になってしまいます。 活用・アスペクトの誤り：「もたらして」とすると動作の連続や手段を表し、「音楽を聴く時間を持つ」ことと並列または因果関係で結ばれてしまい、本来の「安らぎを与える音楽」という修飾関係が崩れます。 活用・アスペクトの誤り：「もたらした」と完了・過去を表すため、すでに安らぎを与え終えた音楽を指すことになり、一般的・普遍的な性質を述べる文脈に合いません。",
  "target_word": "もたらし"
}
```

---

## sense 35201, level 7

#### Pack A
### Level 7 (sense 35201, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "しかし、産業革命以降の急激な人間活動、とりわけ化石燃料の大量消費と森林破壊は、この循環に深刻な破綻をもたらし、地球環境を脅かしている。",
      "is_correct": true
    },
    {
      "text": "昨日、大雨が町に被害をもたらす。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り：過去の「昨日」には過去形「もたらした」を使う。"
    },
    {
      "text": "多くの要素が互いに影響し合うことで、予測できない新しい秩序をもたらし、全体として一つのまとまったシステムが形成されるのである。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "心に安らぎをもたらし、精神を落ち着かせる音楽を聴く時間を持つ。",
      "is_correct": true
    },
    {
      "text": "彼の言葉が安心にもたらしてくれた。",
      "is_correct": false,
      "error_description": "助詞の混同：もたらすものは「を」で示し、「安心を」が正しい。"
    },
    {
      "text": "技術革新は社会に劇的な変化をもたらし、我々の生活様式を変革する。",
      "is_correct": true
    },
    {
      "text": "平和をもたらしている笑顔。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35201, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "しかし、産業革命以降の急激な人間活動、とりわけ化石燃料の大量消費と森林破壊は、この循環に深刻な破綻をもたらして、地球環境を脅かしています。",
      "is_correct": true
    },
    {
      "text": "多くの要素が様々に影響し合うことで、思いがけない新しい結果をもたらして、私たちの社会はさらに豊かに発展していくのです。",
      "is_correct": true
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "多くの要素が様々に影響し合うことで、思いがけない新しい結果をもたらして、私たちの社会はさらに豊かに発展していくのです。",
      "is_correct": false,
      "error_description": "「もたらす」の連用形は「もたらして」ではなく「もたらし」です。書き言葉では「もたらして」ではなく「もたらし」を用いるのが適切です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "新しい技術は生活に便利さをもたらして、私たちの毎日をより豊かなものにしています。",
      "is_correct": true
    },
    {
      "text": "ボランティア活動は社会に大きな変化をもたらして、多くの人々を勇気づけています。",
      "is_correct": true
    },
    {
      "text": "日々の努力がよい結果をもたらして、目標を達成できると思います。",
      "is_correct": true
    },
    {
      "text": "新しい技術は生活に便利さをもたらして、私たちの毎日をより豊かなものにする。",
      "is_correct": false,
      "error_description": "「もたらして」は接続助詞の「て形」であり、前後の文をつなぐ役割を持ちます。後ろの文が「しています」という現在の状態・継続を表す表現であるため、それに続く形として「する」ではなく「しています」とするのが自然な文脈のつながりです。"
    }
  ]
}
```

---

## sense 35227, level 3

#### Pack A
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___だ。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "結果",
    "状況",
    "機構"
  ],
  "explanation": "文脈に最も適した語です。",
  "distractor_tags": {},
  "word_definition": "目的を達成するために、順番に行われる一連の動作や操作のこと。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この___を守ることで安全が保たれる。",
  "original_sentence": "このプロセスを守ることで安全が保たれる。",
  "correct_answer": "プロセス",
  "options": [
    "現象",
    "状況",
    "プロセス",
    "結果"
  ],
  "explanation": "正解です。文脈は「安全を保つための手順」を指しており、「プロセス」が適切です。",
  "distractor_tags": {},
  "word_definition": "目的を達成するために、順番に行われる一連の動作や操作のこと。",
  "target_word": "プロセス"
}
```

#### Pack B
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___です。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "シンボル",
    "アイデア",
    "ルール"
  ],
  "explanation": "正解です。文脈に合う適切な名詞です。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___の結果が出ました。",
  "original_sentence": "プロセスの結果が出ました。",
  "correct_answer": "プロセス",
  "options": [
    "消しゴム",
    "プロセス",
    "スプーン",
    "台風"
  ],
  "explanation": "「学ぶ」に続き、学習が進む一連の過程を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

---

## sense 35227, level 4

#### Pack A
### Level 4 (sense 35227, difficulty None)
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "プロジェクトの遂行には、目的達成に向けた順序立てた一連の動作からなるプロセス___必要である。",
  "original_sentence": "プロジェクトの遂行には、目的達成に向けた順序立てた一連の動作からなるプロセスが必要である。",
  "options": [
    "に",
    "で",
    "を",
    "が"
  ],
  "correct_answer": "が",
  "target_word": "プロセス",
  "error_tags": {
    "を": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "形容動詞「必要だ」の主体（主格）を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35227, difficulty None)
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "プロセス___経て成長します。",
  "original_sentence": "プロセスを経て成長します。",
  "options": [
    "を",
    "が",
    "で",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "プロセス",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「経る」の直接目的語を標示する"
    }
  }
}
```

---
