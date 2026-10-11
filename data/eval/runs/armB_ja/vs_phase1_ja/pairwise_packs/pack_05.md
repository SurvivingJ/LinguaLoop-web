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


## sense 35201, level 3

#### Pack A
### Level 3 (sense 35201, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "近年、精密農業の導入が小規模農家の経営に新たな可能性を___ています。",
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
  "correct_answer": "もたらし",
  "options": [
    "与え",
    "生み",
    "招き",
    "もたらし"
  ],
  "explanation": "正解です。文脈に合う正しい語形です。",
  "distractor_tags": {},
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらし"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "そのニュースは皆に喜びを___。",
  "original_sentence": "そのニュースは皆に喜びをもたらした。",
  "correct_answer": "もたらした",
  "options": [
    "もたらすだろう",
    "もたらした",
    "もたらしている",
    "もたらせ"
  ],
  "explanation": "正解です。文脈「そのニュースは皆に喜びを＿＿＿。」には、過去の事実を表す動詞の過去形「もたらした」が適切です。",
  "distractor_tags": {},
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらした"
}
```

#### Pack B
### Level 3 (sense 35201, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、精密農業の導入が小規模農家の経営に新たな可能性を___ています。",
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
  "correct_answer": "もたらし",
  "options": [
    "読み",
    "食べ",
    "避け",
    "もたらし"
  ],
  "explanation": "正解。人間の活動が破綻という結果を引き起こしたので「もたらし」が合う。",
  "distractor_tags": {},
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらし"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "平和を___いる笑顔。",
  "original_sentence": "平和をもたらしている笑顔。",
  "correct_answer": "もたらしている",
  "options": [
    "もたらして",
    "もたらしている",
    "もたらされる",
    "もたらされた"
  ],
  "explanation": "正解です。「もたらしている」は、動作の結果である状態が継続していることを表し、「平和をもたらしている笑顔」として自然な修飾関係を作ります。",
  "distractor_tags": {},
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらして"
}
```

---

## sense 35201, level 4

#### Pack A
### Level 4 (sense 35201, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "むしろ、それらの複雑な関係性の中で起きる変化が、予期せぬ大きな秩序を___のである。",
  "original_sentence": "むしろ、それらの複雑な関係性の中で起きる変化が、予期せぬ大きな秩序をもたらすのである。",
  "correct_answer": "もたらす",
  "base_form": "もたらす",
  "form_label": "辞書形",
  "options": [
    "もたらす",
    "もたらして",
    "もたらさない",
    "もたらした"
  ],
  "explanation": "文末の「のである」に接続する辞書形（現在・未来・恒常）として適切である",
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらす"
}
```
**particle_selection** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "むしろ、それらの複雑な関係性の中で起きる変化が、予期せぬ大きな秩序___もたらすのである。",
  "original_sentence": "むしろ、それらの複雑な関係性の中で起きる変化が、予期せぬ大きな秩序をもたらすのである。",
  "options": [
    "で",
    "に",
    "を",
    "が"
  ],
  "correct_answer": "を",
  "target_word": "もたらす",
  "error_tags": {
    "に": "location_vs_target",
    "が": "topic_vs_subject",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「もたらす」の直接目的語（結果として生じる事柄）を標示する"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "努力が良い結果を___でしょう。",
  "original_sentence": "努力が良い結果をもたらすでしょう。",
  "correct_answer": "もたらす",
  "base_form": "もたらす",
  "form_label": "辞書形",
  "options": [
    "もたらさない",
    "もたらした",
    "もたらして",
    "もたらす"
  ],
  "explanation": "文末の「でしょう」に接続する辞書形（現在・未来）が正解です。",
  "word_definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
  "target_word": "もたらす"
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
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "甘味と塩気、滑らかさと粒感が口の中で調和し、短時間で頭をすっきりさせる効果をもたらす。",
      "is_correct": true
    },
    {
      "text": "甘味と塩気、滑らかさと粒感が口の中で調和し、短時間で頭をすっきりさせる効果をもたらしたいる。",
      "is_correct": false
    },
    {
      "text": "甘味と塩気、滑らかさと粒感が口の中で調和し、短時間で頭をすっきりさせる効果をもたらすを。",
      "is_correct": false
    },
    {
      "text": "甘味と塩気、滑らかさと粒感が口の中で調和し、短時間で頭をすっきりさせる効果をもたらしてある。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：「もたらした」（過去完了）と「いる」（進行・状態）を混同した誤った形式です。正しくは「もたらしている」または「もたらした」です。 アスペクトの誤り：「てある」は他動詞の結果の状態を残す場合に使いますが、「効果」という抽象的な事象に対しては「ている」（進行・結果の状態）を使うのが自然です。 語順・係り受けの誤り：文末に余分な「を」が付いており、文法的に破綻しています。動詞「もたらす」で文を終える必要があります。",
  "target_word": "もたらし"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "混乱は彼の発言をもたらしている。",
      "is_correct": false
    },
    {
      "text": "彼の発言は混乱をもたらしいる。",
      "is_correct": false
    },
    {
      "text": "彼の発言は混乱をもたらしている。",
      "is_correct": true
    },
    {
      "text": "彼の発言は混乱をもたらしているに。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：文末の「に」は不要です。動詞「もたらしている」で文を終えるべきところへ、格助詞「に」が付加されており、文法的に誤っています。 語順・係り受けの誤り：意味関係が逆転しています。「発言」が原因で「混乱」が生じているので、「発言」が主語、「混乱」が目的語であるべきです。 活用・アスペクトの誤り：進行・状態を表す補助動詞「いる」に接続するには、動詞の連用形「もたらし」ではなく「もたらして」を使う必要があります（もたらしている）。",
  "target_word": "もたらしている"
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "もたらし",
  "relation": "antonym",
  "options": [
    "取り除く",
    "運ぶ",
    "届ける",
    "生み出す"
  ],
  "correct_answer": "取り除く",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事や状態を、他の場所や人に持って来て、与えたり引き起こしたりすること。",
      "explanation": "存在や影響を消し去ることは、もたらす（与え引き起こす）ことの対義である"
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
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要な___だ。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "correct_answer": "プロセス",
  "options": [
    "理由",
    "結果",
    "プロセス",
    "瞬間"
  ],
  "explanation": "正解です。文脈にある「順序立てて行われる一連の動作」という意味に合致します。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "彼はその___を詳しく説明しました。",
  "original_sentence": "彼はそのプロセスを詳しく説明しました。",
  "correct_answer": "プロセス",
  "options": [
    "プロセス",
    "結果",
    "感情",
    "場所"
  ],
  "explanation": "正解です。文脈「彼はその____を詳しく説明しました」において、手順や経過を表す名詞として最も適切です。",
  "distractor_tags": {},
  "word_definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
  "target_word": "プロセス"
}
```

---

## sense 35227, level 4

#### Pack A
### Level 4 (sense 35227, difficulty None)
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "再生可能エネルギー___導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "original_sentence": "再生可能エネルギーの導入加速にもかかわらず、製造プロセスの性質上、炭素発生をゼロ化し得ない領域において、CCUSは極めて重要な役割を担う。",
  "options": [
    "で",
    "に",
    "の",
    "を"
  ],
  "correct_answer": "の",
  "target_word": "プロセス",
  "error_tags": {
    "に": "location_vs_target",
    "で": "instrument",
    "を": "object_marking"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "名詞「製造プロセス」と名詞「性質」を結び、所有・属性関係を示す連体修飾を作る"
    }
  }
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "正しいプロセス___守ることが大切です。",
  "original_sentence": "正しいプロセスを守ることが大切です。",
  "options": [
    "を",
    "に",
    "が",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "プロセス",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「守る」の直接目的語（対象）を示す格助詞です。"
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

## sense 35227, level 6

#### Pack A
### Level 6 (sense 35227, difficulty None)
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "プロセス",
  "relation": "antonym",
  "options": [
    "結果",
    "開始",
    "原因",
    "手段"
  ],
  "correct_answer": "結果",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある目的を達成するために、順序立てて行われる一連の動作や操作。",
      "explanation": "過程や手順そのものではなく、それがもたらす最終的な帰結を指すため、対義関係にある。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "学習のプロセスへ時間がかかります。",
      "is_correct": false
    },
    {
      "text": "学習のプロセスは時間がかかりましたいる。",
      "is_correct": false
    },
    {
      "text": "学習のプロセスが三人います。",
      "is_correct": false
    },
    {
      "text": "学習のプロセスには時間がかかります。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「プロセス」は抽象的な事象や手順を表す名詞であり、人を数える助数詞「三人」を用いることはできません。 助詞の混同：かかる（時間・費用などが必要である）という動詞にかかる対象を示す場合、通常「に」ではなく「が」を用いて主語とし、あるいは「時間をかける」のように他動詞構文にします。「へ」は方向性を示すため不適切です。 活用・アスペクトの誤り：「かかりました」（過去・丁寧）と「ている」（進行・状態）を同時に接続することは文法的に誤りです。どちらか一方を選ぶ必要があります。",
  "target_word": "プロセス"
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
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "彼は極めて寡黙な人物だ。",
      "is_correct": true
    },
    {
      "text": "その課題は極めて難解であること。",
      "is_correct": false,
      "error_description": "誤り型：文末表現の冗長性・不自然さ。断定の文脈において「であること」と名詞化するのは不適切です。正しくは終止形の「である」で終わります。"
    },
    {
      "text": "この課題は極めて難解である。",
      "is_correct": true
    },
    {
      "text": "当該措置は極めて重要である。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35311, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 35311, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "pronunciation": "かのう",
  "ipa": "kanoː",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "加重",
    "過労",
    "可能",
    "下行"
  ],
  "correct_answer": "可能",
  "explanation": "正解です。「可能」は「物事を行うことができる性質や状態。」という意味です。",
  "distractor_explanations": {
    "下行": "「下行」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「こ」、一部の音の違い）。",
    "過労": "「過労」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「ろ」、一部の音の違い）。",
    "加重": "「加重」は「可能」と一モーラだけ異なる実在語です（2モーラ目: 「の」→「じゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35311, level 3

#### Pack A
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "近年、精密農業の導入は小規模農家の経営において___となっています。",
  "original_sentence": "近年、精密農業の導入は小規模農家の経営において可能となっています。",
  "correct_answer": "可能",
  "options": [
    "容易",
    "活発",
    "可能",
    "確実"
  ],
  "explanation": "正解です。文脈「小規模農家の経営において～となっています」に適合し、実現できる状態であることを示します。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "天気が良ければ、明日の遠足は実施___です。",
  "original_sentence": "天気が良ければ、明日の遠足は実施可能です。",
  "correct_answer": "可能",
  "options": [
    "開始",
    "容易",
    "確実",
    "可能"
  ],
  "explanation": "正解です。文脈「天気が良ければ、明日の遠足は実施＿＿です。」において、条件付きで実現できる状態を表す「可能」が最も適切です。",
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

## sense 35311, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷することが可能です。",
      "is_correct": true
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷することは不可能です。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷することが可能だです。",
      "is_correct": false
    },
    {
      "text": "彼らは驚くべきスピードで成長し、可能がわずか数週間で出荷することです。",
      "is_correct": false
    }
  ],
  "explanation": "意味矛盾：前半の「驚くべきスピードで成長し」という肯定的な文脈と、後半の「不可能」という否定的な結論が論理的に矛盾しています。 活用誤り：形状詞「可能」の断定表現は「可能です」または「可能だ」であり、「可能だです」という二重の丁寧表現は文法誤りです。 語順・係り受け誤り：主題と述語の関係が崩れており、「可能」が主語のように扱われているため、意味が通じません。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "有効",
    "確実",
    "容易",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができる状態の対義語である"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "その計画は現実的ではありませんが、理論的には三つの可能です。",
      "is_correct": false
    },
    {
      "text": "その計画は現実的ではありませんが、理論的には可能です。",
      "is_correct": true
    },
    {
      "text": "その計画は現実的ではありませんが、理論的には可能をします。",
      "is_correct": false
    },
    {
      "text": "その計画は現実的ではありませんが、理論的には可能ですこと。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：形状詞「可能」の後に「こと」を直接付けることはできません。「可能です」または「可能なことです」とする必要があります。 助詞の混同：「可能」は形状詞であり、他動詞のように「を」を取ることはありません。「可能です」または「可能になります」などが正しい形式です。 助数詞の誤り：「可能」は抽象的な状態や性質を表す形状詞であり、具体的な個数を数える「三つの」といった助数詞と一緒に使うことはできません。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "有効",
    "容易",
    "確実",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない状態であり、目標語の対義語です。"
    }
  }
}
```

---
