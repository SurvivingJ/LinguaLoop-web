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


## sense 35615, level 3

#### Pack A
### Level 3 (sense 35615, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題はとても___です。",
  "original_sentence": "この問題はとても複雑です。",
  "correct_answer": "複雑",
  "options": [
    "複雑",
    "簡単",
    "明確",
    "単純"
  ],
  "explanation": "正解です。文脈にある「多くの要素がからみ合って簡単には理解できない」という意味に合致します。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

#### Pack B
### Level 3 (sense 35615, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この問題は___です。",
  "original_sentence": "この問題は複雑です。",
  "correct_answer": "複雑",
  "options": [
    "複雑",
    "単純",
    "明確",
    "簡単"
  ],
  "explanation": "正解です。問題の内容や構造が簡単ではないことを表します。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___な気持ちになった。",
  "original_sentence": "複雑な気持ちになった。",
  "correct_answer": "複雑",
  "options": [
    "複雑",
    "簡単",
    "明確",
    "平気"
  ],
  "explanation": "正解です。「複雑な気持ち」は、単純ではない様々な感情が混ざり合った状態を指す自然な表現です。",
  "distractor_tags": {},
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

---

## sense 35615, level 4

#### Pack A
### Level 4 (sense 35615, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "機械の仕組みは___だ。",
  "original_sentence": "機械の仕組みは複雑だ。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "終止形",
  "options": [
    "複雑で",
    "複雑な",
    "複雑",
    "複雑さ"
  ],
  "explanation": "文の末尾で断定を表す終止形（辞書形）が適切である",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "その話は___すぎる。",
  "original_sentence": "その話は複雑すぎる。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹",
  "options": [
    "複雑な",
    "複雑",
    "複雑で",
    "複雑さ"
  ],
  "explanation": "「すぎる」に接続する語幹（連用形）として正しい",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

#### Pack B
### Level 4 (sense 35615, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "人間の気持ちは___ですね。",
  "original_sentence": "人間の気持ちは複雑ですね。",
  "correct_answer": "複雑",
  "base_form": "複雑",
  "form_label": "語幹（「で」に続く形）",
  "options": [
    "複雑に",
    "複雑な",
    "複雑",
    "複雑さ"
  ],
  "explanation": "形状詞の語幹で、後ろの「で」（だ・で）に直接つながり、「通路が複雑で」と述語になる",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "物語の筋が___になっています。",
  "original_sentence": "物語の筋が複雑になっています。",
  "correct_answer": "複雑に",
  "base_form": "複雑",
  "form_label": "連用形（に）",
  "options": [
    "複雑さ",
    "複雑に",
    "複雑な",
    "複雑だ"
  ],
  "explanation": "「～になる」に接続するため、形状詞の連用形「に」が必要",
  "word_definition": "多くの要素がからみ合って、簡単に理解したり処理したりできない様子。",
  "target_word": "複雑"
}
```

---

## sense 35615, level 7

#### Pack A
### Level 7 (sense 35615, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この問題は複雑だです。",
      "is_correct": false,
      "error_description": "形状詞（ナ形容詞）の丁寧語は「です」を直接付けます。「だ」は普通体であり、「だです」と重ねることは文法的に誤りです。"
    },
    {
      "text": "この問題は複雑です。",
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
      "text": "複雑な手順を覚えた。",
      "is_correct": true
    },
    {
      "text": "複雑な気持ちになった。",
      "is_correct": true
    },
    {
      "text": "その話は複雑すぎる。",
      "is_correct": true
    },
    {
      "text": "その話は複雑すぎるだ。",
      "is_correct": false,
      "error_description": "「すぎる」は動詞や形容詞・形状詞の語幹に直接接続する接尾辞であり、その後には断定の助動詞「だ」を付けることはできません。形状詞「複雑」＋「すぎる」で一つの述語として完結します。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35615, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "人間の気持ちは複雑ですね。",
      "is_correct": true
    },
    {
      "text": "複雑の話は苦手だ。",
      "is_correct": false,
      "error_description": "助詞・活用の誤り。形状詞「複雑」が名詞を修飾するときは「の」ではなく「な」を使い、「複雑な話」が正しい形です。"
    },
    {
      "text": "複雑なルールで困っています。",
      "is_correct": true
    },
    {
      "text": "この問題はとても複雑です。",
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
      "text": "複雑な問題を解くのは大変です。",
      "is_correct": true
    },
    {
      "text": "物語の筋が複雑だになっています。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り。形状詞「複雑」の連用形は「複雑に」であり、「複雑だに」とはなりません。"
    },
    {
      "text": "物語の筋が複雑になっています。",
      "is_correct": true
    },
    {
      "text": "複雑な人間関係に疲れています。",
      "is_correct": true
    }
  ]
}
```

---

## sense 36181, level 6

#### Pack A
### Level 6 (sense 36181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "それは私にとって新たな嬉しいことです。",
      "is_correct": false
    },
    {
      "text": "私は新たな本を読みました。",
      "is_correct": false
    },
    {
      "text": "彼は新たな人です。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    }
  ],
  "explanation": "語域・連語：「新たな」は抽象的な概念や状態の変化（課題、可能性、段階など）に用いられることが多く、単に「新しい人」という意味で個人を指す場合は「新しい人」を用いるのが自然的です。 連語：物理的な物体としての「本」が新しく購入したものである場合、「新しい本」を使います。「新たな」は、その本によって得られる知見や局面が新しい場合に用いられます。 項構造・接続：「新たな」は名詞を修飾します。「嬉しいこと」という節や形容動詞的な性質を持つ語を直接修飾するのは不自然です。「新たな喜び」のように名詞化するのが適切です。",
  "target_word": "新た"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "新た",
  "relation": "antonym",
  "options": [
    "正しい",
    "大きな",
    "明るい",
    "旧い"
  ],
  "correct_answer": "旧い",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
      "explanation": "「新た（新しい）」の対義語であり、以前から存在していた状態を表す"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈における自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": true
    },
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈において自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": false
    },
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈による自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": false
    },
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈な自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：元の文の「〜における」は名詞を修飾する連体修飾節を作る形式ですが、これを「〜において」に変えると副詞的用法となり、直後の名詞「自己の再構築」との係り受けが不自然になります。文法的には「〜において、自己の再構築を迫られる」という節全体を作る必要がありますが、元の文構造（名詞句の一部）を維持するなら「における」が必須です。 助詞の混同：「における」を「による」に変えています。「文脈による再構築」は「文脈が手段・原因となって再構築する」という意味になり、元々の「その文脈の中で行われる」という場所・状況の意味とは異なります。 活用・接続の誤り：形状詞「新た」が名詞「社会的文脈」を修飾する場合、通常は「な」をつけて「新たな」とします。しかし、この選択肢では「新たな」の「な」が欠落しているか、あるいは「文脈な」という不自然な接続になっています。正しくは「新たな社会的文脈」です。もし「文脈な」を「文脈である」と解釈しても、連体形として機能せず文法誤りです。",
  "target_word": "新た"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "新た",
  "relation": "antonym",
  "options": [
    "鮮",
    "異",
    "奇",
    "古"
  ],
  "correct_answer": "古",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
      "explanation": "「新た（新しい）」の対義語であり、時間が経って旧くなった状態を表す"
    }
  }
}
```

#### Pack B
### Level 6 (sense 36181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなを課題として浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題に浮上しているのです。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たなに課題として浮上しているのです。",
      "is_correct": false
    }
  ],
  "explanation": "助詞・活用の誤り：形状詞「新た」に副詞的な誤った接尾辞「に」が直接付いています。「新たな」として名詞を修飾するのが正しい用法です。 助詞の混同：形状詞「新た」の後に格助詞「を」が誤って配置されています。名詞「課題」を修飾する連体修飾語としては機能せず、文構造が破綻しています。 連語・格の誤り：「浮上する」は「〜として」や「〜が」といった格助詞を伴って、何かが表面化することを表します。「課題に浮上する」という結びつきは不自然です。",
  "target_word": "新た"
}
```

---

## sense 36191, level 1

#### Pack A
### Level 1 (sense 36191, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "見る",
  "pronunciation": "みる",
  "ipa": "miɾu",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "刈る",
    "ずる",
    "見る",
    "乗る"
  ],
  "correct_answer": "見る",
  "explanation": "正解です。「見る」は「目で物の存在や様子を確かめる。」という意味です。",
  "distractor_explanations": {
    "刈る": "「刈る」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「か」、一部の音の違い）。",
    "ずる": "「ずる」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「ず」、一部の音の違い）。",
    "乗る": "「乗る」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「の」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 36191, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "見る",
  "pronunciation": "みる",
  "ipa": "/miɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "猟る",
    "見る",
    "マル",
    "神子"
  ],
  "correct_answer": "見る",
  "explanation": "正解です。「見る」は「目で物の存在や様子を確かめる。」という意味です。",
  "distractor_explanations": {
    "猟る": "「猟る」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「か」、一部の音の違い）。",
    "マル": "「マル」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「ま」、一部の音の違い）。",
    "神子": "「神子」は「見る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「こ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 36191, level 3

#### Pack A
### Level 3 (sense 36191, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼が描いたのは、実際に自分の目で___た商店街の風景でした。",
  "original_sentence": "彼が描いたのは、実際に自分の目で見た商店街の風景でした。",
  "correct_answer": "見",
  "options": [
    "感じ",
    "見",
    "聞",
    "読"
  ],
  "explanation": "正解です。視覚によって風景を確認する文脈に合致します。",
  "distractor_tags": {},
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```

#### Pack B
### Level 3 (sense 36191, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "窓の外には、___慣れた商店街の景色が広がっていました。",
  "original_sentence": "窓の外には、見慣れた商店街の景色が広がっていました。",
  "correct_answer": "見",
  "options": [
    "聞き",
    "走り",
    "食べ",
    "見"
  ],
  "explanation": "正解です。文脈「窓の外には、～景色が広がっていました」において、視覚的に確認する動作を表す動詞「見」が適切です。",
  "distractor_tags": {},
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "彼は黒板を___ながら話を聞きました。",
  "original_sentence": "彼は黒板を見ながら話を聞きました。",
  "correct_answer": "見",
  "options": [
    "食べ",
    "走り",
    "聞き",
    "見"
  ],
  "explanation": "正解です。文脈「黒板を＿＿ながら話を聞きました」では、視線を向けて確認する行為を表す「見」が適切です。",
  "distractor_tags": {},
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```

---

## sense 36191, level 4

#### Pack A
### Level 4 (sense 36191, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方で、農村の実際の街並みを自分の目で___と、労働需要の質が変化していることがよく分かります。",
  "original_sentence": "一方で、農村の実際の街並みを自分の目で見ると、労働需要の質が変化していることがよく分かります。",
  "correct_answer": "見る",
  "base_form": "見る",
  "form_label": "辞書形（連体形）",
  "options": [
    "見れば",
    "見る",
    "見よう",
    "見て"
  ],
  "explanation": "名詞化の「の」の前は連体形（辞書形）が必要で、「見る」が文法的に成立する",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この映画は___ことができません。",
  "original_sentence": "この映画は見ることができません。",
  "correct_answer": "見る",
  "base_form": "見る",
  "form_label": "辞書形",
  "options": [
    "見ます",
    "見",
    "見て",
    "見る"
  ],
  "explanation": "名詞「こと」に接続するには辞書形が必要です。",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```

#### Pack B
### Level 4 (sense 36191, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方で、農村の実際の様子を___と、労働需要の質が変化していることがわかります。",
  "original_sentence": "一方で、農村の実際の様子を見ると、労働需要の質が変化していることがわかります。",
  "correct_answer": "見る",
  "base_form": "見",
  "form_label": "辞書形",
  "options": [
    "見て",
    "見た",
    "見ない",
    "見る"
  ],
  "explanation": "様態や条件を表す「と」に接続するため、辞書形（基本形）が適切です。",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方で、農村の実際の様子___見ると、労働需要の質が変化していることがわかります。",
  "original_sentence": "一方で、農村の実際の様子を見ると、労働需要の質が変化していることがわかります。",
  "options": [
    "で",
    "に",
    "が",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "見る",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「見る」の直接目的語（対象）を示す格助詞です。"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この絵本は色彩豊かで、子どもがよく___ています。",
  "original_sentence": "この絵本は色彩豊かで、子どもがよく見ています。",
  "correct_answer": "見",
  "base_form": "見",
  "form_label": "連用形",
  "options": [
    "見る",
    "見ない",
    "見",
    "見て"
  ],
  "explanation": "文脈から連用形中止法（または名詞的用法）として機能し、文末でリズムを整える適切な形です。",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```

---

## sense 36191, level 6

#### Pack A
### Level 6 (sense 36191, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私はあの映画を見ことできます。",
      "is_correct": false
    },
    {
      "text": "あの映画はもう見ますか。",
      "is_correct": false
    },
    {
      "text": "あの映画はもう見ましたか。",
      "is_correct": true
    },
    {
      "text": "あの映画は私に見ました。",
      "is_correct": false
    }
  ],
  "explanation": "アスペクトの誤り：完了した事柄や経験の有無を問う場合、「もう～ましたか（過去形・完了）」とするのが自然です。「見ますか」では未来の意志や習慣を問うニュアンスになり、文脈「もう（already）」と整合しません。 活用の誤り：動詞の可能表現を作る際、一段動詞（見る）は「見ることができます」または「見られます」となります。「見ことできます」は活用規則に従っていない誤った形式です。 助詞の混同：動作の対象（映画）を示す助詞は「を」を用います。「に」は方向や相手、存在場所などを示すため、この文脈では不適切です。正しくは「あの映画を見ました」です。",
  "target_word": "見"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "テレビを見ています時間短くしましょう。",
      "is_correct": false
    },
    {
      "text": "テレビに見る時間は短くしましょう。",
      "is_correct": false
    },
    {
      "text": "テレビを見るは好きです。",
      "is_correct": false
    },
    {
      "text": "テレビを見る時間は短くしましょう。",
      "is_correct": true
    }
  ],
  "explanation": "語順・係り受けの誤り：不正解です。動詞の辞書形「見る」を直接主語として扱うことはできません。「見ること」または「見るの」のように名詞化する必要があります。 助詞の混同：不正解です。「テレビを見る」は他動詞構文であり、対象物は助詞「を」で示します。「に」は方向や到着点を示すため、この文脈では誤りです。 活用・アスペクトの誤り：不正解です。「見ています」は進行形・状態の継続を表しますが、ここでの「見る時間」は習慣的な行為の量を指しており、辞書形または名詞修飾としての「見る」が適切です。また、文末との接続も不自然です。",
  "target_word": "見る"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "見",
  "relation": "antonym",
  "options": [
    "読む",
    "隠す",
    "聞く",
    "探す"
  ],
  "correct_answer": "隠す",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "目で物の存在や様子を確かめる。",
      "explanation": "対象を見えないようにする行為であり、見る行為の対義である。"
    }
  }
}
```

#### Pack B
### Level 6 (sense 36191, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "テレビにニュースを見ています。",
      "is_correct": false
    },
    {
      "text": "テレビでニュースを見ています。",
      "is_correct": true
    },
    {
      "text": "見ていますテレビでニュースを。",
      "is_correct": false
    },
    {
      "text": "テレビでニュースを見っています。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：手段や場所を表す場合は「で」を使います。「に」は誤りです。 活用の誤り：動詞「見る」のて形は「見て」です。「見って」は存在しません。 語順の誤り：日本語の基本的な語順は「場所＋目的語＋動詞」です。動詞が文頭に来る語順は不自然です。",
  "target_word": "見て"
}
```

---

## sense 36191, level 7

#### Pack A
### Level 7 (sense 36191, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "窓の外には、見慣れた商店街の景色が広がっていました。",
      "is_correct": true
    },
    {
      "text": "一方で、農村の実際の様子を見ると、労働需要の質が変化していることがわかります。",
      "is_correct": true
    },
    {
      "text": "私は公園で鳥を見います。",
      "is_correct": false,
      "error_description": "動詞「見る」のテ形は「見て」です。「見います」という活用形は存在しません。進行・状態を表す場合は「～ています」の形を使います。"
    },
    {
      "text": "私は公園で鳥を見ています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 36191, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼が描いたのは、実際に自分の目で見た商店街の風景でした。",
      "is_correct": true
    },
    {
      "text": "姉は毎晩ニュースに見ます。",
      "is_correct": false,
      "error_description": "助詞の混同（を／に）：「見る」は見る対象を「を」で示すので、「ニュースに見ます」ではなく「ニュースを見ます」が正しい。"
    },
    {
      "text": "一方で、農村の実際の街並みを自分の目で見ると、労働需要の質が変化していることがよく分かります。",
      "is_correct": true
    },
    {
      "text": "友達の顔をみて、安心しました。",
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
      "text": "先生が黒板を見るのをやめました。",
      "is_correct": true
    },
    {
      "text": "この映画は見ることができません。",
      "is_correct": true
    },
    {
      "text": "道を渡る時は左右を見てください。",
      "is_correct": true
    },
    {
      "text": "道を渡る時は左右に見てください。",
      "is_correct": false,
      "error_description": "「見る」の目的語を示す助詞は「を」です。「に」は誤りです。"
    }
  ]
}
```

---

## sense 38099, level 1

#### Pack A
### Level 1 (sense 38099, difficulty None)
**phonetic_recognition** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "ipa": "ɕoːka",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "瘴気",
    "公課",
    "少雨",
    "昇華"
  ],
  "correct_answer": "昇華",
  "explanation": "正解です。「昇華」は「ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。」という意味です。",
  "distractor_explanations": {
    "少雨": "「少雨」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「う」、一部の音の違い）。",
    "公課": "「公課」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「こ」、一部の音の違い）。",
    "瘴気": "「瘴気」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「き」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 38099, difficulty None)
**phonetic_recognition** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "ipa": "/ɕoːka/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "焦土",
    "老化",
    "象戯",
    "昇華"
  ],
  "correct_answer": "昇華",
  "explanation": "正解です。「昇華」は「ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。」という意味です。",
  "distractor_explanations": {
    "老化": "「老化」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「ろ」、一部の音の違い）。",
    "象戯": "「象戯」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ぎ」、一部の音の違い）。",
    "焦土": "「焦土」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
