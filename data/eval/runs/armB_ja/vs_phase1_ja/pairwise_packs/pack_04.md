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


## sense 35111, level 4

#### Pack A
### Level 4 (sense 35111, difficulty None)
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "植物が秘めた色素の解放は、熱と水という外的要因___因る。",
  "original_sentence": "植物が秘めた色素の解放は、熱と水という外的要因に因る。",
  "options": [
    "へ",
    "から",
    "に",
    "で"
  ],
  "correct_answer": "に",
  "target_word": "よっ",
  "error_tags": {
    "で": "instrument",
    "から": "source_vs_goal",
    "へ": "direction"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「～による（因る）」の形で原因・理由を表す格助詞として正しい"
    }
  }
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "収量の安定化は、センサー等を用いた技術導入___因る効果が大きい。",
  "original_sentence": "収量の安定化は、センサー等を用いた技術導入に因る効果が大きい。",
  "options": [
    "で",
    "から",
    "に",
    "と"
  ],
  "correct_answer": "に",
  "target_word": "より",
  "error_tags": {
    "で": "instrument",
    "から": "source_vs_goal",
    "と": "listing"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "「～に因る」は固定された連語であり、原因・理由の帰着点を示す格助詞「に」を伴う。"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35111, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "まず、季節の移ろいと共に採取された植物は、熱と水に___てその奥底に秘められた色素を解放される。",
  "original_sentence": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "correct_answer": "より",
  "base_form": "因る",
  "form_label": "連用形（〜により）",
  "options": [
    "より",
    "よった",
    "よれば",
    "よって"
  ],
  "explanation": "「これにより」は連用形で後に文が続く接続的な形。",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "よっ"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "まず、季節の移ろいと共___採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "original_sentence": "まず、季節の移ろいと共に採取された植物は、熱と水によってその奥底に秘められた色素を解放される。",
  "options": [
    "で",
    "が",
    "を",
    "に"
  ],
  "correct_answer": "に",
  "target_word": "よっ",
  "error_tags": {
    "で": "instrument",
    "が": "other",
    "を": "object_marking"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "原因・理由を表す動詞「よる」は格助詞「に」をとる"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "センサー等を用いた技術導入は、収量の安定化に___収益性を向上させます。",
  "original_sentence": "センサー等を用いた技術導入は、収量の安定化により収益性を向上させます。",
  "correct_answer": "よっ",
  "base_form": "因る",
  "form_label": "連用形＋て形（〜によって）",
  "options": [
    "よっ",
    "よった",
    "より",
    "よれば"
  ],
  "explanation": "「によって」は原因・手段を表す連用形＋て形の固定表現。",
  "word_definition": "物事の原因・理由を表す。主に「～に因る」の形で用いられ、「～が原因である」「～によって生じる」という意味になる。",
  "target_word": "より"
}
```

---

## sense 35111, level 6

#### Pack A
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "その失敗は、準備不足によってものです。",
      "is_correct": false
    },
    {
      "text": "その失敗は、準備不足によることものです。",
      "is_correct": false
    },
    {
      "text": "その失敗は、準備不足によるものです。",
      "is_correct": true
    },
    {
      "text": "その失敗は、準備不足によりますものです。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：原因を表す場合は「による」または「によって」を用いますが、「によってものです」という結びつきは文法的に不自然です。正しくは「によるものです」または「によって生じたものです」。 活用・アスペクトの誤り：名詞修飾節の中で理由を表す場合、連体形「よる」を用いて「によるものです」とするのが自然です。「よります」は丁寧語の終止形であり、ここで用いるのは不適切です。 語順・係り受けの誤り：「による」の後ろに直接名詞「もの」が続くのが自然な連語です。「こと」を挿入すると、「によること」と「ものです」の関係が不明確になり、文として成立しません。",
  "target_word": "よる"
}
```

#### Pack B
### Level 6 (sense 35111, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "間接照明に因れば陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "効果的です陰影の演出などが、間接照明による組み合わせと家具の白壁無垢材。",
      "is_correct": false
    },
    {
      "text": "間接照明が陰影の演出などが効果的です。",
      "is_correct": false
    },
    {
      "text": "やがて企業が成熟すると、創業者や投資家は投資した対価を得るために、他社による買収や株式上場といったエグジット、すなわち出口戦略を選択する。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：手段を表す「による」を省くと「が」が二重になり文が成立しない。 活用：仮定形「因れば」は条件の意味になり、手段を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
  "target_word": "よる"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "収益性を向上させます、センサー等を用いた技術導入は収量の安定化により。",
      "is_correct": false
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化がより収益性を向上させます。",
      "is_correct": false
    },
    {
      "text": "センサー等を用いた技術導入は、収量の安定化に因ったら収益性を向上させます。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：「により」の前に「が」を重ねるのは誤り。 活用：た系条件形「因ったら」は仮定の意味になり、原因を表す文脈に合わない。 語順：述語を文頭に置き、修飾関係が崩れている。",
  "target_word": "よる"
}
```

---

## sense 35127, level 1

#### Pack A
### Level 1 (sense 35127, difficulty None)
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "無い",
  "pronunciation": "ない",
  "ipa": "/nai/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "泰",
    "会",
    "無い",
    "姓"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "distractor_explanations": {
    "会": "「会」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「か」、一部の音の違い）。",
    "姓": "「姓」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「せ」、一部の音の違い）。",
    "泰": "「泰」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「た」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35127, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "無い",
  "pronunciation": "ない",
  "ipa": "/nai/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "ポイ",
    "無い",
    "貝",
    "なえ"
  ],
  "correct_answer": "無い",
  "explanation": "正解です。「無い」は「存在しないこと。何かがそこにないこと。」という意味です。",
  "distractor_explanations": {
    "ポイ": "「ポイ」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「ぽ」、一部の音の違い）。",
    "なえ": "「なえ」は「無い」と一モーラだけ異なる実在語です（2モーラ目: 「い」→「え」、一部の音の違い）。",
    "貝": "「貝」は「無い」と一モーラだけ異なる実在語です（1モーラ目: 「な」→「か」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35127, level 4

#### Pack A
### Level 4 (sense 35127, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "ポケットの中に時計が___。",
  "original_sentence": "ポケットの中に時計がない。",
  "correct_answer": "ない",
  "base_form": "なく",
  "form_label": "終止形（現在）",
  "options": [
    "なかった",
    "ない",
    "なくて",
    "なければ"
  ],
  "explanation": "現在の状態を表す終止形であり、文脈に合致する",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "ない"
}
```

#### Pack B
### Level 4 (sense 35127, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "このプロジェクトには十分な資金が___、計画通りに進めるのは難しい状況です。",
  "original_sentence": "このプロジェクトには十分な資金がなく、計画通りに進めるのは難しい状況です。",
  "correct_answer": "なく",
  "base_form": "ない",
  "form_label": "連用形（中頓）",
  "options": [
    "なければ",
    "なく",
    "ない",
    "なかった"
  ],
  "explanation": "形容詞の連用形「なく」は、文を中頓して後ろの句に接続する際に用いられます。",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "なく"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
  "original_sentence": "この冷蔵庫には牛乳がなく、朝のコーヒーを飲むことができません。",
  "correct_answer": "ない",
  "base_form": "ない",
  "form_label": "辞書形",
  "options": [
    "なければ",
    "なかった",
    "なく",
    "ない"
  ],
  "explanation": "現在の状態を表す形容詞の辞書形が文脈に合致する",
  "word_definition": "存在しないこと。何かがそこにないこと。",
  "target_word": "ない"
}
```

---

## sense 35127, level 6

#### Pack A
### Level 6 (sense 35127, difficulty None)
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "少ない",
    "ある",
    "空しい",
    "乏しい"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "「存在しない」の対義語であり、物やことがそこに存在することを表す"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "机の上に消しゴムが1冊なく、友達に借りなければなりません。",
      "is_correct": false
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りなければなりません。",
      "is_correct": true
    },
    {
      "text": "机の上に消しゴムがなく、友達で借りなければなりません。",
      "is_correct": false
    },
    {
      "text": "机の上に消しゴムがなく、友達に借りてあるなければなりません。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「消しゴム」の助数詞は「個」や「つ」であり、「冊」は本などに使います。 助詞の混同：「友達に」が正しく、「友達で」は動作の相手ではなく手段や共同動作を表す助詞です。 活用・アスペクトの誤り：「借りてあるなければ」は文法的に誤りです。",
  "target_word": "ない"
}
```

#### Pack B
### Level 6 (sense 35127, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "ある",
    "新しい",
    "多い",
    "広い"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "「ない（存在しない）」の対義語であり、何かがそこに存在することを表す。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "なく",
  "relation": "antonym",
  "options": [
    "少ない",
    "ある",
    "多い",
    "悪い"
  ],
  "correct_answer": "ある",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "存在しないこと。何かがそこにないこと。",
      "explanation": "「ない（存在しない）」の対義語は「ある（存在する）」です。"
    }
  }
}
```

---

## sense 35127, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 35127, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "机の上にペンがない。",
      "is_correct": true
    },
    {
      "text": "財布の中にお金が全くない。",
      "is_correct": true
    },
    {
      "text": "冷蔵庫の中に牛乳がなくて。",
      "is_correct": false,
      "error_description": "文末に「て」を残すと文が未完結になります。断定や存在の否定を表す終止形「ない」を使う必要があります。"
    },
    {
      "text": "冷蔵庫の中に牛乳がない。",
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
      "text": "冷蔵庫に卵がない。",
      "is_correct": true
    },
    {
      "text": "庭に猫がいない。",
      "is_correct": true
    },
    {
      "text": "ポケットの中に時計がない。",
      "is_correct": true
    },
    {
      "text": "ポケットの中に時計がなくて。",
      "is_correct": false,
      "error_description": "文末で状態を断定する場合、形容詞「ない」の終止形を用います。「なくて」は接続助詞的な用法であり、文を完結させることができません。"
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
    "行く",
    "塞く",
    "轢く",
    "要る"
  ],
  "correct_answer": "行く",
  "explanation": "正解です。「行く」は「ある場所から別の場所へ移動する。」という意味です。",
  "distractor_explanations": {
    "轢く": "「轢く」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ひ」、一部の音の違い）。",
    "塞く": "「塞く」は「行く」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「せ」、一部の音の違い）。",
    "要る": "「要る」は「行く」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「る」、一部の音の違い）。"
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "明日、友達と遊びに___ます。",
  "original_sentence": "明日、友達と遊びに行きます。",
  "correct_answer": "行き",
  "base_form": "行く",
  "form_label": "ます形",
  "options": [
    "行って",
    "行かない",
    "行く",
    "行き"
  ],
  "explanation": "「ます」に接続する連用形（ます形）である",
  "word_definition": "ある場所から別の場所へ移動する。",
  "target_word": "行き"
}
```

---

## sense 35147, level 6

#### Pack A
### Level 6 (sense 35147, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "バス停まで走って行いているました。",
      "is_correct": false
    },
    {
      "text": "バス停まで走って行きました。",
      "is_correct": true
    },
    {
      "text": "バス停まで走って行きますた。",
      "is_correct": false
    },
    {
      "text": "バス停まで走ってに行きました。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：過去の事柄を表す場合は「ました」を使います。「ますた」という形は存在しません。 助詞の混同：移動の経路や手段を表す場合、あるいは複合動詞を作る場合は「て」形を直接接続します。「走ってに」という接続は文法的に誤りです。 活用・アスペクトの誤り：「ている」（進行・状態）と「ました」（過去・丁寧）を直接結合させることはできません。文脈に応じて「走っていました」または「走っていきました」などが適切です。",
  "target_word": "行き"
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
      "text": "友達が家に行きました。",
      "is_correct": true
    },
    {
      "text": "駅まで歩いて行けます。",
      "is_correct": true
    },
    {
      "text": "私は学校へ行きです。",
      "is_correct": false,
      "error_description": "動詞の終止形やます形ではなく、名詞である「行き」を文末に置くことはできません。動作を表す場合は動詞として活用させる必要があります。"
    },
    {
      "text": "私は学校へ行きます。",
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

---
