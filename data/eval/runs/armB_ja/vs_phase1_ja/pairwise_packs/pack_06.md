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


## sense 35331, level 1

#### Pack A
### Level 1 (sense 35331, difficulty None)
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

#### Pack B
### Level 1 (sense 35331, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "pronunciation": "とくに",
  "ipa": "tokɯtɕi",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "特に",
    "徳利",
    "特使",
    "特異"
  ],
  "correct_answer": "特に",
  "explanation": "正解です。「特に」は「ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。」という意味です。",
  "distractor_explanations": {
    "特使": "「特使」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「し」、一部の音の違い）。",
    "徳利": "「徳利」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「り」、一部の音の違い）。",
    "特異": "「特異」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「い」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35331, level 3

#### Pack A
### Level 3 (sense 35331, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまらない。",
  "original_sentence": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまらない。",
  "correct_answer": "特に",
  "options": [
    "特に",
    "決して",
    "偶然",
    "すでに"
  ],
  "explanation": "正解です。文脈において、他の事柄と区別して「初期段階のスタートアップ資金調達」を強調しています。",
  "distractor_tags": {},
  "word_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
  "target_word": "特に"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___理由はありません。",
  "original_sentence": "特に理由はありません。",
  "correct_answer": "特に",
  "options": [
    "決して",
    "特に",
    "非常に",
    "単に"
  ],
  "explanation": "正解です。「理由はありません」という文脈で、他の理由と比較して際立ったものがないことを強調するために使います。",
  "distractor_tags": {},
  "word_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
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
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまらな。",
      "is_correct": false,
      "error_description": "誤り型：活用・アスペクトの誤り。否定の助動詞「ない」の前には、動詞の終止形（辞書形）である「とどまる」が来る必要があります。「とどまら」は未然形であり、これだけでは文として成立しません。"
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまらない。",
      "is_correct": true
    },
    {
      "text": "今日は特に寒いですね。",
      "is_correct": true
    },
    {
      "text": "私は特に数学が好きです。",
      "is_correct": true
    }
  ]
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
    "任意",
    "不可欠",
    "簡易",
    "余計"
  ],
  "explanation": "正解です。文脈「職人の緻密な管理が＿＿な工程」において、その工程を行うために絶対に必要であることを示す「不可欠」が適切です。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この実験では、正確なデータ収集が___な要素です。",
  "original_sentence": "この実験では、正確なデータ収集が不可欠な要素です。",
  "correct_answer": "不可欠",
  "options": [
    "重要",
    "不可欠",
    "有益",
    "可能"
  ],
  "explanation": "正解です。文脈「正確なデータ収集が＿＿な要素です」において、実験の成功のために絶対に必要であることを示す「不可欠」が最も適切です。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```

#### Pack B
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

---

## sense 35341, level 4

#### Pack A
### Level 4 (sense 35341, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "そこに、発酵の___な役割が凝縮されているのである。",
  "original_sentence": "そこに、発酵の不可欠な役割が凝縮されているのである。",
  "correct_answer": "不可欠な",
  "base_form": "不可欠",
  "form_label": "連体形",
  "options": [
    "不可欠に",
    "不可欠だ",
    "不可欠な",
    "不可欠で"
  ],
  "explanation": "名詞「役割」を修飾するには形状詞の連体形「な」が必要である。",
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "睡眠は___な要素です。",
  "original_sentence": "睡眠は不可欠な要素です。",
  "correct_answer": "不可欠な",
  "base_form": "不可欠",
  "form_label": "連体形",
  "options": [
    "不可欠だ",
    "不可欠さ",
    "不可欠な",
    "不可欠に"
  ],
  "explanation": "名詞「要素」を修飾するため、形状詞の連体形「な」が必要である。",
  "word_definition": "何かをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

#### Pack B
### Level 4 (sense 35341, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "外国語を学ぶとき、毎日続けることが___です。",
  "original_sentence": "外国語を学ぶとき、毎日続けることが不可欠です。",
  "correct_answer": "不可欠",
  "base_form": "不可欠",
  "form_label": "語幹（名詞的用法）",
  "options": [
    "不可欠で",
    "不可欠だ",
    "不可欠な",
    "不可欠"
  ],
  "explanation": "文の末尾で断定を表すため、形状詞の語幹（または名詞的用法）が正解です。",
  "word_definition": "ある物事をするために、どうしても必要であること。",
  "target_word": "不可欠"
}
```

---

## sense 35341, level 6

#### Pack A
### Level 6 (sense 35341, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "協力も不可欠なものです。",
      "is_correct": true
    },
    {
      "text": "練習は上達に不可欠にだ。",
      "is_correct": false
    },
    {
      "text": "練習は上達を不可欠だ。",
      "is_correct": false
    },
    {
      "text": "不可欠だ練習は上達に。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：形容動詞「不可欠」の対象は「に」で示す。「を」は誤り。 活用：終止形は「不可欠だ」であり、「不可欠にだ」は「に」を余計に挟んだ誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "不可欠"
}
```

#### Pack B
### Level 6 (sense 35341, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は不可欠に発展している。",
      "is_correct": false
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。",
      "is_correct": true
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は不可欠をされている。",
      "is_correct": false
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠だそうだ。",
      "is_correct": false
    }
  ],
  "explanation": "語域・様態の誤り：「不可欠」は客観的な事実や強い必要性を表す形状詞です。「～だそうだ」という伝聞表現と組み合わせると、必要性の確度や話者の断定性が弱まり、文脈上の「極めて」という強調と矛盾して不自然になります。 項構造・結合の誤り：「不可欠」は状態や性質を表す形状詞であり、動詞「発展する」を修飾したり、進行形を作ることはできません。「不可欠である」という述語用法が正解です。 活用・構文の誤り：「不可欠」は形状詞（ナ形容詞）であり、受身形「～をされる」の対象になる名詞ではありません。「不可欠である」または「不可欠な要素とされている」などが正しい表現です。",
  "target_word": "不可欠"
}
```

---

## sense 35419, level 1

#### Pack A
### Level 1 (sense 35419, difficulty None)
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "ipa": "jagate",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "簳",
    "遣り手",
    "軈て",
    "やり手"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "簳": "「簳」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「ら」、一部の音の違い）。",
    "遣り手": "「遣り手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。",
    "やり手": "「やり手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35419, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "軈て",
  "pronunciation": "やがて",
  "ipa": "/jaɡate/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "遣り手",
    "軈て",
    "苦手",
    "野外"
  ],
  "correct_answer": "軈て",
  "explanation": "正解です。「軈て」は「「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。」という意味です。",
  "distractor_explanations": {
    "苦手": "「苦手」は「軈て」と一モーラだけ異なる実在語です（1モーラ目: 「や」→「に」、一部の音の違い）。",
    "野外": "「野外」は「軈て」と一モーラだけ異なる実在語です（3モーラ目: 「て」→「い」、一部の音の違い）。",
    "遣り手": "「遣り手」は「軈て」と一モーラだけ異なる実在語です（2モーラ目: 「が」→「り」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35419, level 3

#### Pack A
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "水は瞬く間に闇色の大地へと吸い込まれ、___目に見えぬ根の網目へと伝わっていくだろう。",
  "original_sentence": "水は瞬く間に闇色の大地へと吸い込まれ、軈て目に見えぬ根の網目へと伝わっていくだろう。",
  "correct_answer": "軈て",
  "options": [
    "突如",
    "決して",
    "軈て",
    "実に"
  ],
  "explanation": "正解です。水が大地に吸い込まれ、時間の経過を経て根の網目に広がるという自然なプロセスを表す「軈て」が適切です。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___彼らは故郷へ帰るだろう。",
  "original_sentence": "軈て彼らは故郷へ帰るだろう。",
  "correct_answer": "軈て",
  "options": [
    "すでに",
    "けっして",
    "軈て",
    "とくに"
  ],
  "explanation": "正解です。文脈に合う副詞「軈て」が入ります。",
  "distractor_tags": {},
  "word_definition": "「軈て」は、時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 3 (sense 35419, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "水は瞬く間に闇色の大地へと吸い込まれ、___目に見えぬ根の網目へと伝わっていくだろう。",
  "original_sentence": "水は瞬く間に闇色の大地へと吸い込まれ、やがて目に見えぬ根の網目へと伝わっていくだろう。",
  "correct_answer": "やがて",
  "options": [
    "決して",
    "すでに",
    "まさに",
    "やがて"
  ],
  "explanation": "正解です。文脈に合う、時間が経った後の変化を表す副詞です。",
  "distractor_tags": {},
  "word_definition": "時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "やがて"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "春が来て、___桜が咲くでしょう。",
  "original_sentence": "春が来て、軈て桜が咲くでしょう。",
  "correct_answer": "軈て",
  "options": [
    "軈て",
    "かつて",
    "すでに",
    "すぐに"
  ],
  "explanation": "正解です。文脈に合う適切な表記（歴史的仮名遣い由来の漢字表記）です。",
  "distractor_tags": {},
  "word_definition": "時間が経過した後に何かが起こることを表す副詞で、「やがて」の異表記です。現代ではあまり使われず、文語的な表現です。",
  "target_word": "軈て"
}
```

---

## sense 35419, level 6

#### Pack A
### Level 6 (sense 35419, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "軈て準備が整い、彼は勢いよく扉を押し開ける。",
      "is_correct": true
    },
    {
      "text": "準備が軈て整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備に整い、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    },
    {
      "text": "軈て準備が整く、彼は勢いよく扉を押し開ける。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「整う」は自動詞であり、主語を示す助詞は「が」が適切です。「準備に」という表現は、格助詞の取り違えです。 活用・アスペクトの誤り：自動詞「整う」の連用形は「整い」ですが、誤って「整く」と活用させています。 語順・係り受けの誤り：副詞「軈て」は通常、文頭や時間の経過を示す句の後に置かれます。「準備が」と「整い」の間に挿入されるのは不自然です。",
  "target_word": "軈て"
}
```

#### Pack B
### Level 6 (sense 35419, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "やがて準備は整い、彼は静かに扉を開いている。",
      "is_correct": false
    },
    {
      "text": "彼は静かに扉を開けた。やがて準備は整い。",
      "is_correct": false
    },
    {
      "text": "やがて準備は整い、彼は静かに扉を開いた。",
      "is_correct": true
    },
    {
      "text": "やがて準備は整い、彼が静かに扉をを開けた。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：「やがて」は未来や過去の一点での出来事への移行を示すため、状態継続や進行を表す「～ている」との結びつきは不自然です。文脈上「開いた」などが適切です。 助詞の混同：目的語を示す格助詞「を」が重複しており、文法的に誤っています。 語順・係り受けの誤り：「やがて」は後ろに来る事柄への時間的橋渡しをする副詞です。文末に置いたり、独立した断片として用いることはできず、文脈論理的にも順序が逆転しています。",
  "target_word": "やがて"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "待ち合わせをして、軈て彼が来た。",
      "is_correct": true
    },
    {
      "text": "待ち合わせをして、やがて彼を来た。",
      "is_correct": false
    },
    {
      "text": "待ち合わせをして、やがて彼が来ている。",
      "is_correct": false
    },
    {
      "text": "やがて待ち合わせをして、彼が来た。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：「やがて」は未来や推移を表すため、完了や状態を表す「ている」と共起させるのは不自然です。正しくは「来た」など過去形を用います。 助詞の混同：自動詞「来る」の主語を示す格助詞は「が」であり、「を」を使うことはできません。 語順・係り受けの誤り：「やがて」は結果（彼が来たこと）にかかるべきであり、前提条件（待ち合わせをする）にかかる位置に置くと意味論的に不自然になります。",
  "target_word": "軈て"
}
```

---

## sense 35615, level 1

#### Pack A
### Level 1 (sense 35615, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "ɸɯkɯzat͡sɯ",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "服罪",
    "伏罪",
    "福笹",
    "複雑"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。",
    "服罪": "「服罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。",
    "伏罪": "「伏罪」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「い」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35615, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "複雑",
  "pronunciation": "ふくざつ",
  "ipa": "/ɸɯkɯzatsɯ/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "複雑",
    "錯雑",
    "福笹",
    "覆没"
  ],
  "correct_answer": "複雑",
  "explanation": "正解です。「複雑」は「多くの要素がからみ合って、簡単に理解したり処理したりできない様子。」という意味です。",
  "distractor_explanations": {
    "錯雑": "「錯雑」は「複雑」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「さ」、一部の音の違い）。",
    "覆没": "「覆没」は「複雑」と一モーラだけ異なる実在語です（3モーラ目: 「ざ」→「ぼ」、一部の音の違い）。",
    "福笹": "「福笹」は「複雑」と一モーラだけ異なる実在語です（4モーラ目: 「つ」→「さ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
