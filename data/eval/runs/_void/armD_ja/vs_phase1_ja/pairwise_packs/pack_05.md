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


## sense 35227, level 6

#### Pack A
### Level 6 (sense 35227, difficulty None)
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスに、それこそが指紋分析の真髄と言えよう。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスだ、それこそが指紋分析の真髄と言えよう。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセスたち、それこそが指紋分析の真髄と言えよう。",
      "is_correct": false
    },
    {
      "text": "真実を解き明かすための静謐かつ論理的なプロセス、それこそが指紋分析の真髄と言えよう。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「プロセス」のような無形の名詞に、個数を数える助数詞「たち」を付けるのは不自然です。 助詞の混同：提示や同格を表す「それこそが」に続けるためには、格助詞「で」ではなく「が」や「は」などを用いるか、文構造を見直す必要があります。ここでは「プロセスに」の「に」が誤りです。 語順・係り受けの誤り：「プロセスだ」と言い切った後に「それこそが」と続けるのは、文の係り受けとして不自然です。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "結果",
    "経過",
    "前提",
    "手法"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "目的を達成するために、順番に行われる一連の動作や操作のこと。",
      "explanation": "目的達成への経過であるプロセスに対し、その到達点である結果は対義関係にある"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "良い結果を出すにはプロセスに大切だ。",
      "is_correct": false
    },
    {
      "text": "良い結果を出すにはプロセスが大切だ。",
      "is_correct": true
    },
    {
      "text": "良い結果を出すにはプロセスが一つ大切だ。",
      "is_correct": false
    },
    {
      "text": "良い結果を出すにはプロセスが大切だ。",
      "is_correct": false
    }
  ],
  "explanation": "正しい文です。 助数詞の誤り：「プロセス」は抽象的な手順を指すため、「一つ」という助数詞は不自然です。 助詞の混同：「大切だ」にかかる主語を示す助詞は「が」または「は」であり、「に」は誤りです。",
  "target_word": "プロセス"
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "システム",
    "手順",
    "結果",
    "目標"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "目的を達成するために、順番に行われる一連の動作や操作のこと。",
      "explanation": "物事の経過や手順に対する、最終的に得られる事柄として対義関係にある"
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
**spot_incorrect_sentence** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": true
    },
    {
      "text": "私たちは、問題を解決するために正しいプロセスによって経た。",
      "is_correct": false,
      "error_description": "助詞の混同です。「プロセス」は「経る」という他動詞の目的語となるため、動作の手段や経路を表す「によって」ではなく、目的語を示す「を」を使う必要があります。"
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
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
      "text": "このプロセスを守ることで安全が保たれるだ。",
      "is_correct": false,
      "error_description": "誤り型：活用・アスペクトの誤り。名詞修飾節（このプロセスを守ることで）の述語である「保たれる」の後に、断定の助動詞「だ」が誤って付加されています。名詞やな形容詞ではなく、動詞や助動詞の終止形に直接「だ」を付けることはできません。"
    },
    {
      "text": "プロジェクトの遂行には、目的達成に向けた順序立てた一連の動作からなるプロセスが必要である。",
      "is_correct": true
    },
    {
      "text": "このプロセスを守ることで安全が保たれる。",
      "is_correct": true
    },
    {
      "text": "良い結果を出すにはプロセスが大切だ。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
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

---

## sense 35293, level 6

#### Pack A
### Level 6 (sense 35293, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難な局面を迎えている。",
      "is_correct": false
    },
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難だ局面を迎えている。",
      "is_correct": false
    },
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって極めて歪められ、その修復は困難な局面を迎えている。",
      "is_correct": false
    },
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難な局面を迎えている。",
      "is_correct": true
    }
  ],
  "explanation": "正しい文です。 語順・係り受けの誤り：「極めて」は「困難な」を修飾すべきであり、「歪められ」を修飾すると文脈の焦点がずれます。 活用・アスペクトの誤り：連体修飾節では「困難な」とするのが適切であり、「困難だ」は格助詞「の」を伴わない限り誤りです。",
  "target_word": "極めて"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その社会的意義は極めて大きい。",
      "is_correct": true
    },
    {
      "text": "この問題は極めて難しいだ。",
      "is_correct": false
    },
    {
      "text": "極めてこの問題は難しい。",
      "is_correct": false
    },
    {
      "text": "この問題は極めて難しかった。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「難しい」はイ形容詞であり、その後に断定の助動詞「だ」を直接付けることはできません。 語順の誤り：程度を表す副詞「極めて」は、それが修飾する形容詞「難しい」の直前に置くのが自然です。 活用・アスペクトの誤り：文脈や他の選択肢との対比から、現在の状態を表す「難しい」が適切であり、過去の「難しかった」は不自然です。",
  "target_word": "極めて"
}
```

#### Pack B
### Level 6 (sense 35293, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "かつては安定していた生態系のサイクルが、現代文明の経済活動によって歪められ、その修復は極めて困難な局面を迎えている。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担うう。",
      "is_correct": false
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割が担う。",
      "is_correct": false
    },
    {
      "text": "担う役割を重要な極めてCCUSは、領域において炭素発生をゼロ化し得ない。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「担う」の対象は「を」で示す。「が」は誤り。 活用：辞書形は「担う」であり、「担うう」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "極めて"
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

#### Pack B
### Level 7 (sense 35293, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その社会的意義は極めて大きい。",
      "is_correct": true
    },
    {
      "text": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
      "is_correct": true
    },
    {
      "text": "こうした文脈下、人工知能アルゴリズムによるリアルタイムの習熟度分析を通じて学習者の認知特性に最適化された教材提示を可能にするアダプティブラーニングプラットフォームの導入は、教育学の観点から極めて示唆に富む。",
      "is_correct": true
    },
    {
      "text": "その社会的意義は極めてに大きい。",
      "is_correct": false,
      "error_description": "「極めて」は程度を表す副詞であり、助詞「に」を伴って「極めてに」となることはありません。副詞はそのまま形容詞や動詞を修飾します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼の態度は極めて失礼だ。",
      "is_correct": true
    },
    {
      "text": "この料理は極めてに美味しい。",
      "is_correct": false,
      "error_description": "「極めて」は副詞です。副詞は助詞「に」を伴わず、そのまま後ろの形容詞や動詞を修飾します。"
    },
    {
      "text": "この料理は極めて美味しい。",
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
    "特使",
    "特に",
    "み国",
    "供に"
  ],
  "correct_answer": "特に",
  "explanation": "正解です。「特に」は「ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。」という意味です。",
  "distractor_explanations": {
    "み国": "「み国」は「特に」と一モーラだけ異なる実在語です（1モーラ目: 「と」→「み」、一部の音の違い）。",
    "供に": "「供に」は「特に」と一モーラだけ異なる実在語です（2モーラ目: 「く」→「も」、一部の音の違い）。",
    "特使": "「特使」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「し」、一部の音の違い）。"
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

## sense 35331, level 6

#### Pack A
### Level 6 (sense 35331, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "特にこの町は歴史を感じています。",
      "is_correct": false
    },
    {
      "text": "特にこの町は歴史で感じます。",
      "is_correct": false
    },
    {
      "text": "特にこの町は歴史を感じます。",
      "is_correct": false
    },
    {
      "text": "この町は特に歴史を感じます。",
      "is_correct": true
    }
  ],
  "explanation": "語順・係り受けの誤り：「特に」は強調したい要素（この場合は「歴史」）の直前に置くのが自然です。「特にこの町は」とすると、町そのものが他と区別されて強調されてしまい、文脈（歴史を感じる度合い）とずれます。 助詞の混同：「歴史を感じます」が正しいコロケーション（連語）です。「で」を使うと、歴史を手段や材料として感じる不自然な意味になってしまいます。 活用・アスペクトの誤り：「感じます」は現在の事実や発見を述べていますが、「感じています」は状態の継続を表します。町を訪れた際の印象を述べる文脈では、単純な現在形「感じます」が適切です。",
  "target_word": "特に"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "特にこの問題が解けます。",
      "is_correct": true
    },
    {
      "text": "特にこの問題が解けます。",
      "is_correct": false
    },
    {
      "text": "特に今日は早く寝たいです。",
      "is_correct": false
    },
    {
      "text": "特に運動していません。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「特に」で強調された名詞「この問題」に続く助詞は「が」ではなく「を」を使い、「特にこの問題を解けます」とするのが自然な項構造です。 活用・アスペクトの誤り：「特に」で強調された動作の否定状態を表す場合、「していません」ではなく、動作の習慣性を否定する「特に運動しません」が適切です。 語順・係り受けの誤り：「特に」は強調したい要素の直前に置くのが自然であり、「今日は特に早く寝たいです」とするのが適切な語順です。",
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
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "特に注意して歩いてください。",
      "is_correct": true
    },
    {
      "text": "特にに注意して歩いてください。",
      "is_correct": false,
      "error_description": "「特に」は副詞であり、助詞を伴いません。副詞の後ろに「に」などの助詞を付けるのは誤りです。"
    },
    {
      "text": "私は特に数学の勉強が好きです。",
      "is_correct": true
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまりません。",
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
      "text": "特に理由はないと思います。",
      "is_correct": true
    },
    {
      "text": "特にこの問題が解けます。",
      "is_correct": true
    },
    {
      "text": "特に理由がないです。",
      "is_correct": false,
      "error_description": "「特に」は否定表現と結びついて「特に〜ない」という自然な連語（慣用表現）を作ります。単に「ないです」とするのではなく、強調や対比のニュアンスを含む「ない」という形、または「特に理由はない」という名詞修飾の形にするのが適切です。"
    },
    {
      "text": "特にこの曲はよく聞いています。",
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
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "天然酵母を用いた製パンは、職人の緻密な管理が___な工程です。",
  "original_sentence": "天然酵母を用いた製パンは、職人の緻密な管理が不可欠な工程です。",
  "correct_answer": "不可欠",
  "options": [
    "不可欠",
    "有害",
    "不要",
    "任意"
  ],
  "explanation": "文脈にぴったり合致します。職人の緻密な管理が「どうしても必要」であることを表しています。",
  "distractor_tags": {},
  "word_definition": "あることをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "外国語を学ぶとき、毎日の努力が___になります。",
  "original_sentence": "外国語を学ぶとき、毎日の努力が不可欠になります。",
  "correct_answer": "不可欠",
  "options": [
    "有害",
    "無関係",
    "不可欠",
    "不要"
  ],
  "explanation": "正解です。文脈に合っており、自然な日本語です。",
  "distractor_tags": {},
  "word_definition": "あることをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

---

## sense 35341, level 4

#### Pack A
### Level 4 (sense 35341, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "そこに、発酵の___な役割が凝縮されているのである。",
  "original_sentence": "そこに、発酵の不可欠な役割が凝縮されているのである。",
  "correct_answer": "不可欠",
  "base_form": "不可欠",
  "form_label": "語幹（無活用形）",
  "options": [
    "不可欠に",
    "不可欠で",
    "不可欠",
    "不可欠な"
  ],
  "explanation": "「発酵の不可欠役割」という複合的な名詞修飾として形状詞の語幹が直接名詞に接続している",
  "word_definition": "あることをするために、どうしても必要なこと。",
  "target_word": "不可欠"
}
```

#### Pack B
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
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠なだ。",
      "is_correct": false
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠でである。",
      "is_correct": false
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠だ。",
      "is_correct": false
    },
    {
      "text": "テクノロジー産業の持続的発展において、ベンチャーキャピタルの存在は極めて不可欠である。",
      "is_correct": true
    }
  ],
  "explanation": "活用・終止形の誤り：「不可欠」は形状詞であり、名詞的用法を除き、文末では「不可欠だ」となるのが正しい終止形です。「不可欠だ」の「だ」が欠落しています。 活用の誤り：「不可欠」の連用形は「不可欠で」ですが、それに「である」を続けることはできません。「不可欠である」とするのが正しい形です。 連体形と終止形の混同：「不可欠な」は連体形（名詞を修する形）であり、文末で文を終わらせる終止形としては使えません。正しくは「不可欠だ」となります。",
  "target_word": "不可欠"
}
```
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "不可欠",
  "relation": "antonym",
  "options": [
    "主要",
    "重要",
    "必須",
    "不要"
  ],
  "correct_answer": "不要",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "あることをするために、どうしても必要なこと。",
      "explanation": "「どうしても必要」という語義の対義語は「必要ない」を意味する「不要」である。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "良い関係を保つには、お互いの思いやり不可欠です。",
      "is_correct": false
    },
    {
      "text": "良い関係を保つには、お互いの思いやりが不可欠です。",
      "is_correct": true
    },
    {
      "text": "良い関係を保つには、不可欠がお互いの思いやりです。",
      "is_correct": false
    },
    {
      "text": "良い関係を保つには、お互いの思いやりが不可欠なだ。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：形状詞「不可欠」に「な」を直接続けることはできず、「不可欠だ」とするのが正しいです。 助詞の混同：主語「思いやり」と述語「不可欠です」を結ぶ格助詞「が」が欠落しています。 語順・係り受けの誤り：主題と解説の構造が破壊されており、自然な日本語の語順になっていません。",
  "target_word": "不可欠"
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "不可欠",
  "relation": "antonym",
  "options": [
    "任意",
    "重要",
    "不要",
    "必須"
  ],
  "correct_answer": "不要",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "あることをするために、どうしても必要なこと。",
      "explanation": "「どうしても必要である」の対義語は「必要ないこと」を表す本語である。"
    }
  }
}
```

---
