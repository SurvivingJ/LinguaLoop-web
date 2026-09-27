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


## sense 35311, level 3

#### Pack A
### Level 3 (sense 35311, difficulty 8)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "options": [
    "可能",
    "重要",
    "簡単",
    "必要"
  ],
  "explanation": "「可能となり」は実現できる性質を表す固定表現。",
  "target_word": "可能",
  "correct_answer": "可能",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
  "sentence_with_blank": "これらにより、壁を薄くして大きな窓を設けることが___となり、内部は光に満ちあふれました。"
}
```
**cloze_completion** variant `B`, tier `T6`
```json
{
  "options": [
    "簡単",
    "必要",
    "重要",
    "可能"
  ],
  "explanation": "「可能に見える」は実現できる性質を表す固定表現。",
  "target_word": "可能",
  "correct_answer": "可能",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "参加は可能ですか。",
  "sentence_with_blank": "参加は___ですか。"
}
```

#### Pack B
### Level 3 (sense 35311, difficulty None)
**cloze_completion** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "解決___な方法を、みんなで考えました。",
  "original_sentence": "解決可能な方法を、みんなで考えました。",
  "correct_answer": "可能",
  "options": [
    "完全",
    "可能",
    "必要",
    "容易"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

---

## sense 35311, level 4

#### Pack A
### Level 4 (sense 35311, difficulty None)
**cloze_typed** variant `A`, tier `advanced`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
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
**morphology_slot** variant `A`, tier `advanced`
```json
{
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "correct_answer": "可能な",
  "base_form": "可能",
  "form_label": "連体形（な）",
  "options": [
    "可能で",
    "可能な",
    "可能に",
    "可能だ"
  ],
  "explanation": "名詞「体重」を修飾するためには、形状詞の連体形「な」を用いる必要がある",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```
**cloze_typed** variant `B`, tier `advanced`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "早く終われば、間に合うことも___です。",
  "original_sentence": "早く終われば、間に合うことも可能です。",
  "target_word": "可能",
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能だ",
      "可能で",
      "可能に",
      "可能性"
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
**morphology_slot** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "早く終われば、間に合うことも___です。",
  "original_sentence": "早く終われば、間に合うことも可能です。",
  "correct_answer": "可能",
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "options": [
    "簡単",
    "可能",
    "重要",
    "必要"
  ],
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "word_definition": "物事を行うことができる性質や状態。",
  "target_word": "可能"
}
```

#### Pack B
### Level 4 (sense 35311, difficulty 8)
**cloze_typed** variant `A`, tier `T6`
```json
{
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ]
  },
  "input_mode": "ime",
  "target_word": "可能",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。"
}
```
**morphology_slot** variant `A`, tier `T6`
```json
{
  "options": [
    "簡単",
    "必要",
    "重要",
    "可能"
  ],
  "base_form": "可能",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "target_word": "可能",
  "correct_answer": "可能",
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
  "sentence_with_blank": "彼らは驚くべきスピードで成長し、わずか数週間で出荷___な体重になります。"
}
```
**cloze_typed** variant `B`, tier `T6`
```json
{
  "word": "可能",
  "answer": {
    "accepted": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ],
    "accepted_normalized": [
      "可能",
      "可能な",
      "可能に",
      "可能性"
    ]
  },
  "input_mode": "ime",
  "target_word": "可能",
  "normalization": {
    "case": "fold",
    "quotes": "straighten",
    "script": null,
    "unicode": "NFKC",
    "whitespace": "collapse+trim",
    "trailing_punctuation": "strip"
  },
  "schema_version": 2,
  "original_sentence": "それは十分に可能だ。",
  "sentence_with_blank": "それは十分に___だ。"
}
```
**morphology_slot** variant `B`, tier `T6`
```json
{
  "options": [
    "必要",
    "重要",
    "簡単",
    "可能"
  ],
  "base_form": "可能",
  "form_label": "語幹（連用形・に の前）",
  "explanation": "「に」を伴い述語を修飾する連用形の語幹。",
  "target_word": "可能",
  "correct_answer": "可能",
  "word_definition": "物事を行うことができる性質や状態。",
  "original_sentence": "それは十分に可能だ。",
  "sentence_with_blank": "それは十分に___だ。"
}
```

---

## sense 35311, level 6

#### Pack A
### Level 6 (sense 35311, difficulty 8)
**semantic_discrimination** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "もたらしています可能性を新たな、小規模農家の経営に精密農業の導入が。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしいます。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性がもたらしています。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    }
  ],
  "explanation": "助詞：他動詞「もたらす」の対象は「を」で示す。「が」は誤り。 活用：「もたらして」が正しい活用で、「もたらしい」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "可能"
}
```
**semantic_discrimination** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "彼にはそれが可能で見える。",
      "is_correct": false
    },
    {
      "text": "彼にはそれが可能に見える。",
      "is_correct": true
    },
    {
      "text": "見える可能にそれが、彼には。",
      "is_correct": false
    },
    {
      "text": "彼にそれが可能に見える。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：経験者を示す「には」を単なる「に」に置き換えると不自然。 活用：連用形は「可能に」であり、「可能で」は接続が誤り。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "可能"
}
```

#### Pack B
### Level 6 (sense 35311, difficulty None)
**semantic_discrimination** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことを可能となっています。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となっています。",
      "is_correct": true
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも可能となっています、効率的な経営を行うことが。",
      "is_correct": false
    },
    {
      "text": "近年、精密農業の導入により、小規模農家でも効率的な経営を行うことが可能となってあります。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「ことが」を「ことを」と誤用しています。 活用・アスペクトの誤り：状態変化を表す「可能となる」に「てある」は不自然です。 語順・係り受けの誤り：述語と主語の語順が逆転しており不自然です。",
  "target_word": "可能"
}
```
**synonym_antonym_match** variant `A`, tier `advanced`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "至難",
    "困難",
    "容易",
    "不可能"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態。目標語「可能」の対義語。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `advanced`
```json
{
  "word": "可能",
  "relation": "antonym",
  "options": [
    "容易",
    "必然",
    "不可能",
    "困難"
  ],
  "correct_answer": "不可能",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事を行うことができる性質や状態。",
      "explanation": "物事を行うことができない性質や状態を表し、目標語の対義語となる。"
    }
  }
}
```

---

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
### Level 7 (sense 35311, difficulty 8)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "これらにより、壁を薄くして大きな窓を設けることが可能となり、内部は光に満ちあふれました。",
      "is_correct": true
    },
    {
      "text": "また、限られた環境で効率的に生産を行う「資源管理」の観点からも、持続可能な食料供給の実現において重要な役割を果たしています。",
      "is_correct": true
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能が体重になります。",
      "is_correct": false,
      "error_description": "活用：名詞の前では連体形「可能な」を使う。「可能が」は誤り。"
    },
    {
      "text": "彼らは驚くべきスピードで成長し、わずか数週間で出荷可能な体重になります。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35311, level 9

#### Pack A
### Level 9 (sense 35311, difficulty 8)
**jumbled_sentence** variant `A`, tier `T6`
```json
{
  "original_sentence": "これは可能な計画だ。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "chunks": [
    "近年精密農業の",
    "導入が",
    "小規模農家の",
    "経営に",
    "新たな可能性を",
    "もたらしています"
  ],
  "chunk_count": 6,
  "target_word": "可能",
  "schema_version": 2,
  "shuffled_chunks": [
    "近年精密農業の",
    "もたらしています",
    "新たな可能性を",
    "導入が",
    "経営に",
    "小規模農家の"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。"
}
```
**jumbled_sentence** variant `B`, tier `T6`
```json
{
  "original_sentence": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。"
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
### Level 1 (sense 35331, difficulty 5)
**kanji_to_reading** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "prompt": "特に",
  "options": [
    "とぐに",
    "どくに",
    "とうくに",
    "とくに"
  ],
  "direction": "kanji_to_reading",
  "correct_answer": "とくに",
  "schema_version": 2
}
```
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "ipa": "/tokɯni/",
  "word": "特に",
  "options": [
    "特殊",
    "砥草",
    "特に",
    "特需"
  ],
  "audio_url": null,
  "explanation": "正解です。「特に」は「ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。」という意味です。",
  "pronunciation": "とくに",
  "correct_answer": "特に",
  "syllable_count": 3,
  "distractor_source": "phonetic_trie",
  "distractor_explanations": {
    "特殊": "「特殊」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「しゅ」、一部の音の違い）。",
    "特需": "「特需」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「じゅ」、一部の音の違い）。",
    "砥草": "「砥草」は「特に」と一モーラだけ異なる実在語です（3モーラ目: 「に」→「さ」、一部の音の違い）。"
  }
}
```
**reading_to_kanji** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "prompt": "とくに",
  "options": [
    "特別",
    "特定",
    "特に",
    "特徴"
  ],
  "direction": "reading_to_kanji",
  "correct_answer": "特に",
  "schema_version": 2,
  "distractor_sources": {
    "特別": "component",
    "特定": "component",
    "特徴": "component"
  }
}
```

#### Pack B
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

---

## sense 35331, level 2

#### Pack A
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

#### Pack B
### Level 2 (sense 35331, difficulty 5)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "特に",
  "options": [
    "衣服や装飾品など、身につけるもの全般を指す言葉です。",
    "百の数倍ほどの、はっきりしない数。",
    "「調べる」は、疑問や目的のために、資料や観測などを用いて事実や原因などを明らかにすること。",
    "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。"
  ],
  "pronunciation": "とくに",
  "correct_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。"
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "nl": {
    "en": {
      "options": [
        "高级定制",
        "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
        "进展 —— 事情向前推进，进入新的阶段或状态",
        "何かが起きた理由のこと。"
      ],
      "correct_answer": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。"
    }
  },
  "tier": "T3",
  "word": "特に",
  "pronunciation": "とくに",
  "schema_version": 2
}
```

---

## sense 35331, level 3

#### Pack A
### Level 3 (sense 35331, difficulty 5)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "options": [
    "ぜひ",
    "もっと",
    "特に",
    "そろそろ"
  ],
  "explanation": "正解。「特に予定がありません」は、これといった予定がないことを表す決まった言い方です。",
  "target_word": "特に",
  "correct_answer": "特に",
  "distractor_tags": {},
  "word_definition": "ある事柄を、ほかの事柄と区別して強調するときに使う副詞です。",
  "original_sentence": "夏休みは特に予定がありません。",
  "sentence_with_blank": "夏休みは___予定がありません。"
}
```

#### Pack B
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

---

## sense 35331, level 6

#### Pack A
### Level 6 (sense 35331, difficulty 5)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "週末は特に、海に行きたいでした。",
      "is_correct": false
    },
    {
      "text": "週末は特に、海が行きたいです。",
      "is_correct": false
    },
    {
      "text": "週末は特に、海に行きたいです。",
      "is_correct": true
    },
    {
      "text": "週末は海に行きたい特にです。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同です。「行く」は自動詞で向かう先は「に」で示すため、「海が行きたい」では海が行くことになり成り立ちません。 活用・アスペクトの誤りです。「行きたい」の後ろに「でした」は付かず、過去なら「行きたかったです」とします。 語順・係り受けの誤りです。「特に」は強調する語句の前に置く副詞で、文末で名詞のように「です」を付けるのは不自然です。",
  "target_word": "特に"
}
```

#### Pack B
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

---

## sense 35331, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 35331, difficulty 5)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "特に理由はありません。",
      "is_correct": true
    },
    {
      "text": "今日は寒い特にですね。",
      "is_correct": false,
      "error_description": "語順の誤り。副詞「特に」は修飾する語の前に置くので、「寒い特に」ではなく「特に寒い」が正しい。"
    },
    {
      "text": "私は特に、数学が好きです。",
      "is_correct": true
    },
    {
      "text": "特に、初期段階のスタートアップ資金調達を担う彼らの役割は、単なる資本の提供にとどまらない。",
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
      "text": "夏休みは特に予定がありません。",
      "is_correct": true
    },
    {
      "text": "週末は特に、海に行きたいです。",
      "is_correct": true
    },
    {
      "text": "今日は特にの用事がありません。",
      "is_correct": false,
      "error_description": "助詞の誤り。「特に」は副詞なので、「の」を付けて名詞を修飾することはできない。「特に用事が」が正しい。"
    },
    {
      "text": "歌の中では、特にこの曲が好きです。",
      "is_correct": true
    }
  ]
}
```

---
