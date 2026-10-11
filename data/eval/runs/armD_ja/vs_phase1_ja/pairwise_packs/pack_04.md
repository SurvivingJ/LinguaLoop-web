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


## sense 35147, level 7

#### Pack A
### Level 7 (sense 35147, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "毎日歩いて学校に行きます。",
      "is_correct": true
    },
    {
      "text": "私は毎日電車で行きます。",
      "is_correct": true
    },
    {
      "text": "私は毎日電車へ行きます。",
      "is_correct": false,
      "error_description": "手段・方法を表す「電車」には、場所の方向を表す「へ」ではなく、手段を表す助詞「で」を使う必要があります。"
    },
    {
      "text": "友達の家に遊びに行きました。",
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

## sense 35201, level 4

#### Pack A
### Level 4 (sense 35201, difficulty None)
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "いろいろな要素が組み合わさることで、私たちの生活に多くの便利な変化___もたらしています。",
  "original_sentence": "いろいろな要素が組み合わさることで、私たちの生活に多くの便利な変化をもたらしています。",
  "options": [
    "を",
    "が",
    "で",
    "に"
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
      "explanation": "他動詞「もたらす」の直接目的語（変化）を標示する格助詞として正しい"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "日々の努力が、良い結果を___います。",
  "original_sentence": "日々の努力が、良い結果をもたらしています。",
  "correct_answer": "もたらして",
  "base_form": "もたらす",
  "form_label": "て形",
  "options": [
    "もたらした",
    "もたらします",
    "もたらして",
    "もたらす"
  ],
  "explanation": "「ています」の補助動詞に接続するため、て形である必要があります。",
  "word_definition": "ある結果や変化を、人や場所に与えたり引き起こしたりすること。",
  "target_word": "もたらして"
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "日々の努力が、良い結果___もたらしています。",
  "original_sentence": "日々の努力が、良い結果をもたらしています。",
  "options": [
    "に",
    "を",
    "で",
    "が"
  ],
  "correct_answer": "を",
  "target_word": "もたらして",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「もたらす」の直接目的語を標示する正しい格助詞である"
    }
  }
}
```

#### Pack B
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

---

## sense 35201, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35201, difficulty None)
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "もたらしています",
  "relation": "antonym",
  "options": [
    "及ぼす",
    "残す",
    "奪う",
    "促す"
  ],
  "correct_answer": "奪う",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある結果や変化を、人や場所に与えたり引き起こしたりすること。",
      "explanation": "ある結果や利益を与え引き起こす「もたらす」に対し、それを取り去ることは対義関係が成立します。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "もたらしています",
  "relation": "antonym",
  "options": [
    "奪っています",
    "招いています",
    "与えています",
    "促しています"
  ],
  "correct_answer": "奪っています",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある結果や変化を、人や場所に与えたり引き起こしたりすること。",
      "explanation": "与え生じさせることの反対として、持っているものを取り上げる意味で対義関係が成立します"
    }
  }
}
```

---

## sense 35201, level 7

#### Pack A
### Level 7 (sense 35201, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしてあります。",
      "is_correct": false,
      "error_description": "「〜てある」は他動詞の動作結果の意図的な状態維持を表しますが、「可能性をもたらす」のような自然な結果や継続的な状態には不適切です。ここでは進行・継続の「〜ています」を使うのが正しいアスペクトの選択です。"
    },
    {
      "text": "しかし、産業革命以降の急激な人間活動、とりわけ化石燃料の大量消費と森林破壊は、この循環に深刻な破綻をもたらしています。",
      "is_correct": true
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "いろいろな要素が組み合わさることで、私たちの生活に多くの便利な変化をもたらしています。",
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

---

## sense 35227, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___です。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "correct_answer": "プロセス",
  "options": [
    "現象",
    "結果",
    "プロセス",
    "習慣"
  ],
  "explanation": "文脈に合致する正解です。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "製造___を確認します。",
  "original_sentence": "製造プロセスを確認します。",
  "correct_answer": "プロセス",
  "options": [
    "天気",
    "プロセス",
    "アイデア",
    "結果"
  ],
  "explanation": "正解です。「製造」と結びつき、製品を作るための一連の操作を指す自然な表現です。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

---

## sense 35227, level 4

#### Pack A
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

#### Pack B
### Level 4 (sense 35227, difficulty None)
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "再生可能エネルギー___導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "options": [
    "が",
    "を",
    "は",
    "の"
  ],
  "correct_answer": "の",
  "target_word": "プロセス",
  "error_tags": {
    "が": "topic_vs_subject",
    "は": "topic_vs_subject",
    "を": "object_marking"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "名詞「性質」を修飾し、「Aの性質上」という慣用的な副詞句を作る格助詞。"
    }
  }
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "学習のプロセス___大事です。",
  "original_sentence": "学習のプロセスが大事です。",
  "options": [
    "を",
    "に",
    "が",
    "で"
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
      "explanation": "形容動詞「大事だ」の対象（主語）を提示する格助詞"
    }
  }
}
```

---

## sense 35227, level 6

#### Pack A
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄とだと言えるでしょう。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えるでしょう。",
      "is_correct": true
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えるでしょう静かに。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスそれこそが、指紋分析の真髄と言えるでしょう。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「論理的なプロセス」と「それこそが」の間に、同格や強調を表す読点（、）や「という」などの接続要素が不足しており、統語的に不自然です。 活用・アスペクトの誤り：「と言える」の「と」の後に、推量や様態の助動詞「だ」を不必要に挿入しており、文法的に誤りです。 語順・係り受けの誤り：「静かに」という副詞句が文末に不適切に配置されており、修飾すべき述語「言える」から離れすぎているため、係り受けが破壊されています。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "手段",
    "システム",
    "結果",
    "事象"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "経過や手順を指す目標語に対し、その帰結を指すため対義関係が成立する"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "マニュアル",
    "ステップ",
    "結果",
    "システム"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "順序立てた操作の経緯を指すプロセスに対し、その最終的な帰結を指す結果は対義関係にある"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスをだ。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えます。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": false
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスについてだ。",
      "is_correct": false
    }
  ],
  "explanation": "語域：基礎例文は「意味する重要なプロセスです」という丁寧な表現（語域）ですが、この文は「だ」という常体（だ・である調）になっており、文体の丁寧度が一致していません。 語順・係り受けの誤り：「〜を意味する重要なプロセスについてだ」とすると、文全体が「〜について（説明・言及する）」という主題提示の構造になり、「これは〜プロセスです」というイコールの関係が崩れて意味が通りません。 助詞の混同：「重要なプロセスをだ」とはなりません。名詞を提示して断定する場合は「が」または「は」を使い、「を」は目的語を作る格助詞なのでここでは誤りです。",
  "target_word": "プロセス"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "この作業は、二羽のプロセスに分けられる。",
      "is_correct": false
    },
    {
      "text": "新しいプロセスが生まれました。",
      "is_correct": true
    },
    {
      "text": "このプロセスは、もう完成してある。",
      "is_correct": false
    },
    {
      "text": "プロセスが見直せば、時間を減らせる。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：作業の段階を数えるのに鳥用の「羽」は使えない。正しくは「二つのプロセス」や「二段階のプロセス」である。 助詞の混同：「見直す」の対象は「を」で示すべきで、「が」では対象が主語扱いになり不自然になる。正しくは「プロセスを見直せば」である。 活用・アスペクトの誤り：「〜てある」は他動詞にしか接続できず、自動詞「完成する」には使えない。正しくは「完成している」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "手法",
    "結果",
    "手順",
    "作業"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "「過程」である目標語の語義に対し、その行き着く先である「結果」は対義関係にある。"
    }
  }
}
```

---

## sense 35227, level 7

#### Pack A
### Level 7 (sense 35227, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
      "is_correct": true
    },
    {
      "text": "正しいプロセスに守ってください。",
      "is_correct": false,
      "error_description": "助詞の混同。「守る」の目的語を示すには「を」を使います。「に」は方向や着点を示す助詞であり、ここでは不適切です。"
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのです。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
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
      "text": "プロセスを経て成長します。",
      "is_correct": true
    },
    {
      "text": "プロセスの結果が出ました。",
      "is_correct": true
    },
    {
      "text": "新しいプロセスが生まれました。",
      "is_correct": true
    },
    {
      "text": "プロセスに経て成長します。",
      "is_correct": false,
      "error_description": "動詞「経る」は経過する過程を表す名詞を受けて助詞「を」をとります。「に」を使うのは誤りです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35227, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "学習のプロセスが大事です。",
      "is_correct": true
    },
    {
      "text": "製造プロセスに確認します。",
      "is_correct": false,
      "error_description": "「確認する」は他動詞であり、その対象（動作の及ぶもの）を示すには格助詞「を」を使います。「に」は存在場所や着地点などを示すため、この文脈では不適切です。"
    },
    {
      "text": "良いプロセスで仕事をします。",
      "is_correct": true
    },
    {
      "text": "製造プロセスを確認します。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35293, level 7

#### Pack A
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "その社会的意義は極めてに大きい。",
      "is_correct": false,
      "error_description": "「極めて」は副詞であるため、格助詞「に」を伴うことはできません。副詞はそのままの形で用言（この場合は形容詞「大きい」）を修飾します。"
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "その社会的意義は極めて大きい。",
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
      "text": "彼の態度は極めて非礼である。",
      "is_correct": true
    },
    {
      "text": "本問題は極めて難解である。",
      "is_correct": true
    },
    {
      "text": "その影響は極めて甚大である。",
      "is_correct": true
    },
    {
      "text": "彼の態度は極めて非礼だである。",
      "is_correct": false,
      "error_description": "「だ」と「である」はともに丁寧さや文体を司る助動詞ですが、これらを重複して「だである」とすることはできません。文語的で改まった表現である「である」を単独で用いるのが正しい用法です。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入は、現代社会において極めてに重要な課題である。",
      "is_correct": false,
      "error_description": "副詞「極めて」の後に助詞「に」を付けるのは誤りです。副詞は助詞を介さずに直接形容詞や動詞を修飾します。"
    },
    {
      "text": "その社会的意義は極めて大きい。",
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
      "text": "この問題は極めてに難しい。",
      "is_correct": false,
      "error_description": "助詞の混同。副詞「極めて」の後に格助詞「に」を誤って付加している。副詞は助詞を伴わずに直接形容詞を修飾する。"
    },
    {
      "text": "極めて珍しい花が咲いている。",
      "is_correct": true
    },
    {
      "text": "極めて大切な友達です。",
      "is_correct": true
    },
    {
      "text": "この問題は極めて難しい。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35311, level 1

#### Pack A
### Level 1 (sense 35311, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "/kanoː/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "火口",
    "可能",
    "嘉保",
    "下層"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "下層": "「下層」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「そ」、一部の音の違い）。",
    "嘉保": "「嘉保」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ほ」、一部の音の違い）。",
    "火口": "「火口」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「こ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35311, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "/ka.noː/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "仮寓",
    "可能",
    "稼働",
    "架橋"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "架橋": "「架橋」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「きょ」、一部の音の違い）。",
    "仮寓": "「仮寓」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ぐ」、一部の音の違い）。",
    "稼働": "「稼働」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
