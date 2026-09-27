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


## sense 35227, level 2

#### Pack A
### Level 2 (sense 35227, difficulty None)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "correct_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "options": [
    "相手に物や情報などを渡すこと。",
    "本。書物。文字や絵が印刷された、綴じた紙の集まり。",
    "人や物を車や電車などの上にのせること。",
    "ある目的を達成するために、順序立てて行われる一連の動作や操作。"
  ]
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "tier": "T6",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
        "官民",
        "use; to utilize — using an item or service for a certain purpose",
        "病気や悪いことが、どんどん広がること。"
      ],
      "correct_answer": "ある目的を達成するために、順序立てて行われる一連の動作や操作。"
    }
  }
}
```

#### Pack B
### Level 2 (sense 35227, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "ある目的のために、順序立てて行われる一連の動作や操作。",
        "何かを、自分のしたいように動かすこと。",
        "衣服などの原料となる、植物の種子からとれる繊維です。",
        "will; determination — a firm resolve to achieve a certain goal"
      ],
      "correct_answer": "ある目的のために、順序立てて行われる一連の動作や操作。"
    }
  },
  "tier": "T6",
  "word": "プロセス",
  "pronunciation": "ぷろせす",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "options": [
    "すでに書かれた文字や内容などを、別のものに変更すること。",
    "本。書物。文字や絵が印刷された、綴じた紙の集まり。",
    "ある目的のために、順序立てて行われる一連の動作や操作。",
    "ある場所に定期的に行き来すること。"
  ],
  "pronunciation": "ぷろせす",
  "correct_definition": "ある目的のために、順序立てて行われる一連の動作や操作。"
}
```

---

## sense 35227, level 3

#### Pack A
### Level 3 (sense 35227, difficulty None)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "真実を解き明かすための静謐かつ論理的な___こそが、指紋分析の真髄と言えるでしょう。",
  "original_sentence": "真実を解き明かすための静謐かつ論理的なプロセスこそが、指紋分析の真髄と言えるでしょう。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "お祭り騒ぎ",
    "パーティー",
    "ジャケット"
  ],
  "explanation": "「静謐かつ論理的な」に続き、真実を解き明かすための一連の手順を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "sentence_with_blank": "この___を踏むことで、成功することができます。",
  "original_sentence": "このプロセスを踏むことで、成功することができます。",
  "correct_answer": "プロセス",
  "options": [
    "消しゴム",
    "スプーン",
    "台風",
    "プロセス"
  ],
  "explanation": "「学ぶ」に続き、学習が進む一連の過程を表すので、意味・連語ともに自然に成立する。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

#### Pack B
### Level 3 (sense 35227, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "プロセス",
    "パーティー",
    "お祭り騒ぎ",
    "ジャケット"
  ],
  "explanation": "「静謐かつ論理的な」に続き、真実を解き明かすための一連の手順を表すので、意味・連語ともに自然に成立する。",
  "target_word": "プロセス",
  "correct_answer": "プロセス",
  "distractor_tags": {},
  "word_definition": "ある目的のために、順序立てて行われる一連の動作や操作。",
  "original_sentence": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えよう。",
  "sentence_with_blank": "真実を解き明かすための静謐かつ論理的な___、それこそが指紋分析の真髄と言えよう。"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "options": [
    "スプーン",
    "プロセス",
    "台風",
    "消しゴム"
  ],
  "explanation": "「学ぶ」に続き、学習が進む一連の過程を表すので、意味・連語ともに自然に成立する。",
  "target_word": "プロセス",
  "correct_answer": "プロセス",
  "distractor_tags": {},
  "word_definition": "ある目的のために、順序立てて行われる一連の動作や操作。",
  "original_sentence": "学ぶプロセスで、多くのことを知った。",
  "sentence_with_blank": "学ぶ___で、多くのことを知った。"
}
```

---

## sense 35227, level 4

#### Pack A
### Level 4 (sense 35227, difficulty None)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___です。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": null
  },
  "input_mode": "ime"
}
```
**particle_selection** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行___意味する重要なプロセスです。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
  "options": [
    "で",
    "に",
    "が",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "プロセス",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「意味する」の直接目的語を標示する"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "___が長くて疲れてしまいます。",
  "original_sentence": "プロセスが長くて疲れてしまいます。",
  "target_word": "プロセス",
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "プロセス化"
    ],
    "accepted_normalized": [
      "プロセス",
      "プロセス化"
    ]
  },
  "normalization": {
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "case": "fold",
    "trailing_punctuation": "strip",
    "quotes": "straighten",
    "script": null
  },
  "input_mode": "ime"
}
```
**particle_selection** variant `B`, tier `T6`
```json
{
  "sentence_with_blank": "プロセス___長くて疲れてしまいます。",
  "original_sentence": "プロセスが長くて疲れてしまいます。",
  "options": [
    "を",
    "で",
    "が",
    "に"
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
      "explanation": "形容詞「長い」の対象を主格で標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 35227, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "製造プロセス",
      "開発プロセス",
      "思考プロセス",
      "プロセス管理"
    ],
    "accepted_normalized": [
      "プロセス",
      "製造プロセス",
      "開発プロセス",
      "思考プロセス",
      "プロセス管理"
    ]
  },
  "input_mode": "ime",
  "target_word": "プロセス",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___だ。"
}
```
**particle_selection** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "explanation": "他動詞「意味する」の目的語「移行」を標示するので「を」が入る"
    }
  },
  "options": [
    "を",
    "に",
    "と",
    "で"
  ],
  "error_tags": {
    "で": "instrument",
    "と": "other",
    "に": "location_vs_target"
  },
  "target_word": "プロセス",
  "correct_answer": "を",
  "schema_version": 2,
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行___意味する重要なプロセスだ。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "プロセス",
  "answer": {
    "accepted": [
      "プロセス",
      "製造プロセス",
      "開発プロセス",
      "思考プロセス",
      "プロセス管理"
    ],
    "accepted_normalized": [
      "プロセス",
      "製造プロセス",
      "開発プロセス",
      "思考プロセス",
      "プロセス管理"
    ]
  },
  "input_mode": "ime",
  "target_word": "プロセス",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "このプロセスには、三つの段階がある。",
  "sentence_with_blank": "この___には、三つの段階がある。"
}
```
**particle_selection** variant `B`, tier `T6`
```json
{
  "nl": {
    "en": {
      "explanation": "存在を表す「ある」の対象「段階」を主格として標示するので「が」が入る"
    }
  },
  "options": [
    "が",
    "へ",
    "と",
    "を"
  ],
  "error_tags": {
    "と": "other",
    "へ": "direction",
    "を": "object_marking"
  },
  "target_word": "プロセス",
  "correct_answer": "が",
  "schema_version": 2,
  "original_sentence": "このプロセスには、三つの段階がある。",
  "sentence_with_blank": "このプロセスには、三つの段階___ある。"
}
```

---

## sense 35227, level 6

#### Pack A
### Level 6 (sense 35227, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "明日、私はそのプロセスを見直した。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "この製品は、三匹のプロセスを経て完成する。",
      "is_correct": false
    },
    {
      "text": "工場は新しい技術でプロセスが導入した。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：手順や段階を数えるのに動物用の「匹」は使えない。正しくは「三つのプロセス」や「三段階のプロセス」である。 助詞の混同：「導入する」の対象は「を」で示すべきで、「が」では主語になってしまい文が成り立たない。正しくは「プロセスを導入した」である。 活用・テンスの誤り：未来を表す「明日」と過去形の「た」が矛盾し、文として成立しない。正しくは「見直す」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "definition": "ある目的のために、順序立てて行われる一連の動作や操作。",
      "explanation": "過程・手順に対して、それを経て得られる終着の成果を指す対の語"
    }
  },
  "word": "プロセス",
  "options": [
    "結果",
    "手法",
    "工程",
    "段階"
  ],
  "relation": "antonym",
  "correct_answer": "結果",
  "schema_version": 2
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "プロセスを見直せば、時間を減らせる。",
      "is_correct": true
    },
    {
      "text": "プロセスが見直せば、時間を減らせる。",
      "is_correct": false
    },
    {
      "text": "この作業は、二羽のプロセスに分けられる。",
      "is_correct": false
    },
    {
      "text": "このプロセスは、もう完成してある。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：作業の段階を数えるのに鳥用の「羽」は使えない。正しくは「二つのプロセス」や「二段階のプロセス」である。 助詞の混同：「見直す」の対象は「を」で示すべきで、「が」では対象が主語扱いになり不自然になる。正しくは「プロセスを見直せば」である。 活用・アスペクトの誤り：「〜てある」は他動詞にしか接続できず、自動詞「完成する」には使えない。正しくは「完成している」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T6`
```json
{
  "nl": {
    "en": {
      "definition": "ある目的のために、順序立てて行われる一連の動作や操作。",
      "explanation": "過程・手順に対して、それを経て得られる終着の成果を指す対の語"
    }
  },
  "word": "プロセス",
  "options": [
    "結果",
    "方法",
    "手順",
    "過程"
  ],
  "relation": "antonym",
  "correct_answer": "結果",
  "schema_version": 2
}
```

#### Pack B
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "工場は新しい技術でプロセスが導入した。",
      "is_correct": false
    },
    {
      "text": "明日、私はそのプロセスを見直した。",
      "is_correct": false
    },
    {
      "text": "この製品は、三匹のプロセスを経て完成する。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：手順や段階を数えるのに動物用の「匹」は使えない。正しくは「三つのプロセス」や「三段階のプロセス」である。 助詞の混同：「導入する」の対象は「を」で示すべきで、「が」では主語になってしまい文が成り立たない。正しくは「プロセスを導入した」である。 活用・テンスの誤り：未来を表す「明日」と過去形の「た」が矛盾し、文として成立しない。正しくは「見直す」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `A`, tier `T6`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "方法",
    "経過",
    "結果",
    "手順"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "過程に対する帰結を指し、目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "このプロセスは、もう完成してある。",
      "is_correct": false
    },
    {
      "text": "この作業は、二羽のプロセスに分けられる。",
      "is_correct": false
    },
    {
      "text": "プロセスが見直せば、時間を減らせる。",
      "is_correct": false
    },
    {
      "text": "正しいプロセスで問題を解くことができます。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：作業の段階を数えるのに鳥用の「羽」は使えない。正しくは「二つのプロセス」や「二段階のプロセス」である。 助詞の混同：「見直す」の対象は「を」で示すべきで、「が」では対象が主語扱いになり不自然になる。正しくは「プロセスを見直せば」である。 活用・アスペクトの誤り：「〜てある」は他動詞にしか接続できず、自動詞「完成する」には使えない。正しくは「完成している」である。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T6`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "経過",
    "結果",
    "手法",
    "手順"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "ある作用によって生じた事柄。順序立った動作そのものを指す「プロセス」の対義語となる。"
    }
  }
}
```

---

## sense 35227, level 7

#### Pack A
### Level 7 (sense 35227, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのです。",
      "is_correct": true
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスこそが、指紋分析の真髄と言えるでしょう。",
      "is_correct": true
    },
    {
      "text": "この仕事のプロセスを複雑だ。",
      "is_correct": false,
      "error_description": "助詞の混同（を／は）。「複雑だ」は状態を述べる述語で目的語を取らないので、主題を表す「は」を使い、「プロセスは複雑だ」とするのが正しい。"
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスです。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "プロセスが長くて疲れてしまいます。",
      "is_correct": true
    },
    {
      "text": "正しいプロセスで問題を解くことができます。",
      "is_correct": true
    },
    {
      "text": "このプロセスを踏むことで、成功することができます。",
      "is_correct": true
    },
    {
      "text": "彼女は仕事のプロセスに見直した。",
      "is_correct": false,
      "error_description": "助詞の混同（に／を）。「見直す」の対象は目的語なので、「に」ではなく「を」を使い、「プロセスを見直した」が正しい。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35227, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": true
    },
    {
      "text": "この仕事のプロセスを複雑だ。",
      "is_correct": false,
      "error_description": "助詞の混同（を／は）。「複雑だ」は状態を述べる述語で目的語を取らないので、主題を表す「は」を使い、「プロセスは複雑だ」とするのが正しい。"
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えよう。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "彼女は仕事のプロセスに見直した。",
      "is_correct": false,
      "error_description": "助詞の混同（に／を）。「見直す」の対象は目的語なので、「に」ではなく「を」を使い、「プロセスを見直した」が正しい。"
    },
    {
      "text": "このプロセスには、三つの段階がある。",
      "is_correct": true
    },
    {
      "text": "学ぶプロセスで、多くのことを知った。",
      "is_correct": true
    },
    {
      "text": "プロセスを見直せば、時間を減らせる。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35227, level 9

#### Pack A
### Level 9 (sense 35227, difficulty None)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "私たちは正しいプロセスを経ています。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "私たちは正しいプロセスを経ています。",
  "chunks": [
    "私たちは",
    "正しいプロセスを",
    "経て",
    "います"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "います",
    "経て",
    "正しいプロセスを",
    "私たちは"
  ],
  "target_word": "プロセス",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "schema_version": 2,
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担います。",
  "chunks": [
    "再生可能エネルギーの",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "ゼロ化し得ない領域に",
    "おいてCCUSは",
    "極めて重要な役割を担います"
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
    "ゼロ化し得ない領域に",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "おいてCCUSは",
    "再生可能エネルギーの",
    "極めて重要な役割を担います"
  ],
  "target_word": "プロセス",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 35227, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "chunks": [
    "大切なの",
    "は",
    "結果より",
    "プロセスだ"
  ],
  "chunk_count": 4,
  "target_word": "プロセス",
  "schema_version": 2,
  "shuffled_chunks": [
    "プロセスだ",
    "結果より",
    "は",
    "大切なの"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "original_sentence": "大切なのは、結果より、プロセスだ。"
}
```
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "大切なのは、結果より、プロセスだ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "再生可能エネルギーの",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "ゼロ化し得ない領域に",
    "おいてCCUSは",
    "極めて重要な役割を担う"
  ],
  "chunk_count": 6,
  "target_word": "プロセス",
  "schema_version": 2,
  "shuffled_chunks": [
    "ゼロ化し得ない領域に",
    "導入加速にもかかわらず",
    "製造プロセスの性質上炭素発生を",
    "おいてCCUSは",
    "再生可能エネルギーの",
    "極めて重要な役割を担う"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。"
}
```

---

## sense 35293, level 1

#### Pack A
### Level 1 (sense 35293, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "きわめて",
  "schema_version": 2
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "極めて",
  "schema_version": 2,
  "distractor_sources": {
    "分厚い": "component",
    "大好き": "component",
    "認める": "frequency"
  }
}
```

#### Pack B
### Level 1 (sense 35293, difficulty None)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "極めて",
  "options": [
    "ぎわめて",
    "きわめで",
    "きいわめて",
    "きわめて"
  ],
  "correct_answer": "きわめて",
  "word": "極めて",
  "direction": "kanji_to_reading"
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "prompt": "きわめて",
  "options": [
    "極めて",
    "分厚い",
    "大好き",
    "認める"
  ],
  "correct_answer": "極めて",
  "word": "極めて",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "大好き": "component",
    "分厚い": "component",
    "認める": "frequency"
  }
}
```

---

## sense 35293, level 2

#### Pack A
### Level 2 (sense 35293, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "極めて",
  "options": [
    "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
    "物の位置が、下よりも高い方にあること。また、その方向や場所。",
    "塩分を含まない、陸上の河川や湖沼などに存在する水。飲料水や農業・工業用水として利用される。",
    "劇場などで上映される、物語を映像と音声で表現した作品。"
  ],
  "pronunciation": "きわめて",
  "correct_definition": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "培育",
        "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。",
        "数量が多いこと。",
        "人や物の間で、情報や気持ちを送ったり受け取ったりすること。"
      ],
      "correct_answer": "程度がはなはだしいことを表す。状態や動作の度合いが非常に高いことを示す。"
    }
  },
  "tier": "T6",
  "word": "極めて",
  "pronunciation": "きわめて",
  "schema_version": 2
}
```

#### Pack B
### Level 2 (sense 35293, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "correct_definition": "状態や動作の度合いが、とても高いことを表す副詞。",
  "options": [
    "物体が地球などに引かれる力。重さの原因となる。",
    "人が乗ってペダルをこぎ、車輪を回して進む乗り物。",
    "物事をより完全な状態にするために、手を加えて美しくしたり、技術を高めたりすること。",
    "状態や動作の度合いが、とても高いことを表す副詞。"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "極めて",
  "pronunciation": "きわめて",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "不要になったもの、捨てるもの、または材料の切れ端や残りの部分。",
        "状態や動作の度合いが、とても高いことを表す副詞。",
        "existence (viability)",
        "実際に経験して、確かにそうだと感じること。"
      ],
      "correct_answer": "状態や動作の度合いが、とても高いことを表す副詞。"
    }
  }
}
```

---

## sense 35311, level 1

#### Pack A
### Level 1 (sense 35311, difficulty None)
**kanji_to_reading** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "correct_answer": "かのう",
  "word": "可能",
  "direction": "kanji_to_reading"
}
```
**phonetic_recognition** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "/kanou/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "歌唱",
    "加号",
    "苦悩",
    "可能"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "苦悩": "「苦悩」は「可能」と一モーラだけ異なる実在語です（1モーラ目: 「か」→「く」、一部の音の違い）。",
    "歌唱": "「歌唱」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「しょ」、一部の音の違い）。",
    "加号": "「加号」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ご」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```
**reading_to_kanji** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "correct_answer": "可能",
  "word": "可能",
  "direction": "reading_to_kanji",
  "distractor_sources": {
    "機能": "component",
    "能力": "component",
    "知能": "component"
  }
}
```

#### Pack B
### Level 1 (sense 35311, difficulty 8)
**kanji_to_reading** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "prompt": "可能",
  "options": [
    "かあのう",
    "がのう",
    "かのう",
    "かの"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "かのう",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "ipa": "kanoː",
  "word": "可能",
  "options": [
    "下葉",
    "過少",
    "川鵜",
    "可能"
  ],
  "audio_url": null,
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "pronunciation": "かのう",
  "correct_answer": "可能",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "下葉": "「下葉」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「よ」、一部の音の違い）。",
    "川鵜": "「川鵜」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「わ」、一部の音の違い）。",
    "過少": "「過少」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「しょ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "prompt": "かのう",
  "options": [
    "可能",
    "能力",
    "知能",
    "機能"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "可能",
  "schema_version": 2,
  "distractor_sources": {
    "機能": "component",
    "知能": "component",
    "能力": "component"
  }
}
```

---

## sense 35311, level 2

#### Pack A
### Level 2 (sense 35311, difficulty 8)
**definition_match** variant `A`, tier `T6`
```json
{
  "nl": {
    "en": {
      "options": [
        "breathing — the process by which a living thing draws air into the body and lets it out again",
        "物事を行うことができる性質や状態。",
        "换句话说",
        "prosperity"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  },
  "tier": "T6",
  "word": "可能",
  "pronunciation": "かのう",
  "schema_version": 2
}
```
**definition_match** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "options": [
    "物事のはずれやまちがいがなく、ぴったりあっているさま。",
    "火をつけて燃やすことで熱やエネルギーを生み出す物質。車や飛行機を動かすためのガソリンや軽油、灯油などの総称。",
    "物事を行うことができる性質や状態。",
    "生物の体を構成する最小の単位。植物や動物の体は多くの細胞からできている。"
  ],
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。"
}
```

#### Pack B
### Level 2 (sense 35311, difficulty None)
**definition_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "correct_definition": "物事を行うことができる性質や状態。",
  "options": [
    "歴史や物事の流れの中で、特徴的な出来事や変化が起こった、特別な時期や時代。",
    "「かげつ」と読み、月を数える単位です。特に「一箇月」「二箇月」のように使います。",
    "複数の要素や人を集めて、一つのまとまりを作ること。",
    "物事を行うことができる性質や状態。"
  ]
}
```
**definition_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "tier": "advanced",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "物事を行うことができる性質や状態。",
        "原初",
        "模糊 —— 事物的区别或状态不清楚，无法明确判断",
        "a tomato — a red, round vegetable eaten raw or used in cooking"
      ],
      "correct_answer": "物事を行うことができる性質や状態。"
    }
  }
}
```

---
