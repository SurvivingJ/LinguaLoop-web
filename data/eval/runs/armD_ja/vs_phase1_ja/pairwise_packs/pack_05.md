# Pairwise review pack 05

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


## sense 35311, level 3

#### Pack A
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "明日は会議が___な時間です。",
  "original_sentence": "明日は会議が可能な時間です。",
  "correct_answer": "可能",
  "options": [
    "可能",
    "適当",
    "自由",
    "許可"
  ],
  "explanation": "正解です。「会議が可能な時間」で、会議を行うことができる性質・状態を表す「可能」が適切です。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "頂戴したデータにつきましては、専門家の分析を経た上で、来週中に詳細な回答をお返しすることが___です。",
  "original_sentence": "頂戴したデータにつきましては、専門家の分析を経た上で、来週中に詳細な回答をお返しすることが可能です。",
  "correct_answer": "可能",
  "options": [
    "可能",
    "実現",
    "成功",
    "許可"
  ],
  "explanation": "正解です。文脈に合致します。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 4

#### Pack A
### Level 4 (sense 35311, difficulty None)
**morphology_slot** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "自然エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロにすることが___ではない領域において、CCUSは極めて重要な役割を担っています。",
  "original_sentence": "自然エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロにすることが可能ではない領域において、CCUSは極めて重要な役割を担っています。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹",
  "options": [
    "可能な",
    "可能",
    "可能で",
    "可能だ"
  ],
  "explanation": "助動詞「ではない」に直接接続するには、形状詞の語幹の形が必要である",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 4 (sense 35311, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが___です。",
  "original_sentence": "製造プロセスの性質上、炭素発生を完全にゼロ化することは困難ですが、CCUS技術を組み合わせれば実質的な排出ゼロを実現することが可能です。",
  "correct_answer": "可能です",
  "base_form": "可能",
  "form_label": "です形（丁寧）",
  "options": [
    "可能な",
    "可能です",
    "可能だ",
    "可能で"
  ],
  "explanation": "丁寧な文体（polite）の文末に接続する「です形」が適切です。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼が手伝うことは___です。",
  "original_sentence": "彼が手伝うことは可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "可能",
    "簡単",
    "重要",
    "必要"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 6

#### Pack A
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "皆様の迅速なご対応により、早期の解決が可能となりました。",
      "is_correct": true
    },
    {
      "text": "皆様の迅速なご対応により、早期の解決が早期に可能となりました。",
      "is_correct": false
    },
    {
      "text": "皆様の迅速なご対応により、早期の解決が一つ可能となりました。",
      "is_correct": false
    },
    {
      "text": "皆様の迅速なご対応により、早期の解決を可能となりました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「解決」という抽象的な事柄に対して「一つ」という助数詞は不適切です。 語順・意味の重複：「早期の解決」と「早期に」が重複しており、冗長で不自然な表現です。 助詞の混同：「可能となりました」は状態の変化を表す自動詞的な述語構造をとるため、目的語を示す「を」ではなく主語を示す「が」を使う必要があります。",
  "target_word": "可能"
}
```

#### Pack B
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この技術を使えば、新しいエネルギーを生み出すことを可能です。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で市場に出荷することが可能な体重にまで達します。",
      "is_correct": true
    },
    {
      "text": "最新のAIにより、複雑な計算を可能しています。",
      "is_correct": false
    },
    {
      "text": "この計画により、一本の新しい工場を建設することが可能です。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「工場」の助数詞は「一本」ではなく「一軒」または「一つ」が適切です。 助詞の混同：「～ことを可能だ」とは言いません。「～ことが可能だ」とするのが正しいです。 活用・アスペクトの誤り：「可能」は形状詞なので「～している」のような動詞の活用はつきません。「可能にしています」や「可能となっています」が正しいです。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "不可能",
    "必須",
    "必然",
    "容易"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態を指し、目標語の対義語となる。"
    }
  }
}
```

---

## sense 35311, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 35311, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "皆様の迅速なご対応により、早期の解決が可能となりました。",
      "is_correct": true
    },
    {
      "text": "明日は会議が可能な時間です。",
      "is_correct": true
    },
    {
      "text": "彼は可能な限り、最善を尽くして努力いたしました。",
      "is_correct": true
    },
    {
      "text": "皆様の迅速なご対応により、早期の解決が可能性となりました。",
      "is_correct": false,
      "error_description": "「解決が」という主語に対し、状態の変化を表す「可能となりました」とするのが適切です。「可能性」は名詞であるため、「可能性が生じました」などと表現する必要があります。"
    }
  ]
}
```

---

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
    "み国",
    "特旨",
    "特務",
    "特に"
  ],
  "correct_answer": "特に",
  "explanation": "正解です。「特に」は「ほかのものと区別して、あることを強調する副詞です。」という意味です。",
  "distractor_explanations": {
    "特旨": "「特旨」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「し」、一部の音の違い）。",
    "み国": "「み国」は「特に」と一モーラだけ異なる実在語です（1モーラ目: 「と」→「み」、一部の音の違い）。",
    "特務": "「特務」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「む」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
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

---

## sense 35331, level 3

#### Pack A
### Level 3 (sense 35331, difficulty None)
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "___この本は、何度も読んでいます。",
  "original_sentence": "特にこの本は、何度も読んでいます。",
  "correct_answer": "特に",
  "options": [
    "全く",
    "偶然",
    "相変わらず",
    "特に"
  ],
  "explanation": "正解です。他の本と区別して、この本を際立たせて強調する文脈に最も適切です。",
  "distractor_tags": {},
  "word_definition": "ほかのものと区別して、あることを強調する副詞です。",
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

#### Pack B
### Level 6 (sense 35331, difficulty None)
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "特に悪いところは見つかりませんでしたを。",
      "is_correct": false
    },
    {
      "text": "特に見つかりませんでした悪いところは。",
      "is_correct": false
    },
    {
      "text": "特に悪いところは見つかりませんだった。",
      "is_correct": false
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
      "is_correct": true
    }
  ],
  "explanation": "活用・アスペクトの誤り：「見つかりません」の後に、過去を表す「だった」を直接接続することはできません。正しくは「見つかりませんでした」とする必要があります。 助詞の混同：「見つかりませんでした」は自動詞の過去・丁寧語であり、その後に目的語を示す対格助詞「を」を配置することは文法的に誤りです。 語順・係り受けの誤り：副詞「特に」は修飾する形容詞「悪い」の直前に置くのが自然です。また、主題である「悪いところは」が文末に分離されており、標準的な日本語の語順から逸脱しています。",
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
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "今日は特に暑いので注意してください。",
      "is_correct": true
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
      "is_correct": true
    },
    {
      "text": "私は特にに数学の勉強が好きです。",
      "is_correct": false,
      "error_description": "「特に」は副詞であり、形容動詞ではありません。そのため、後ろに格助詞「に」を付けて「特にに」とすることはできません。副詞はそのままの形で用言（この場合は「好きです」）を修飾します。"
    },
    {
      "text": "私は特に数学の勉強が好きです。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "特に急ぐ必要はありませんから、ゆっくりしましょう。",
      "is_correct": true
    },
    {
      "text": "特にには急ぐ必要はありませんから、ゆっくりしましょう。",
      "is_correct": false,
      "error_description": "「特に」は副詞です。副詞の後に格助詞「には」を付けることはできません。「特に」の後に助詞を付けず、そのまま「急ぐ」を修飾します。"
    },
    {
      "text": "特に悪いところは見つかりませんでした。",
      "is_correct": true
    },
    {
      "text": "特にこの本は、何度も読んでいます。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35341, level 3

#### Pack A
### Level 3 (sense 35341, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "correct_answer": "不可欠",
  "options": [
    "不可避",
    "不変",
    "不可侵",
    "不可欠"
  ],
  "explanation": "正解です。文脈である「製パン」と「職人の緻密な管理」の関係から、絶対に必要な要素を指す「不可欠」が最も適切です。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この実験を成功させるには、正確なデータ測定が___になります。",
  "original_sentence": "この実験を成功させるには、正確なデータ測定が不可欠になります。",
  "correct_answer": "不可欠",
  "options": [
    "不可逆",
    "不可欠",
    "不規則",
    "不可避"
  ],
  "explanation": "正解です。文脈に最も適した「どうしても必要な」という意味の形状詞です。",
  "distractor_tags": {},
  "word_definition": "ある物事をするために、どうしても必要なこと。",
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
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "外国語を学ぶとき、毎日少しずつ練習することが___です。",
  "original_sentence": "外国語を学ぶとき、毎日少しずつ練習することが不可欠です。",
  "correct_answer": "不可欠",
  "base_form": "不可欠",
  "form_label": "基本形（語幹）",
  "options": [
    "不可欠な",
    "不可欠",
    "不可欠に",
    "不可欠だ"
  ],
  "explanation": "「です」の前では形状詞の語幹（基本形）がそのまま接続します。",
  "word_definition": "ある物事をするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

---
