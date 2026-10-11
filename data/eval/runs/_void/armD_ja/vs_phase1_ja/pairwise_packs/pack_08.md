# Pairwise review pack 08

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


## sense 39661, level 1

#### Pack A
### Level 1 (sense 39661, difficulty None)
**phonetic_recognition** variant `A`, tier `advanced`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "[itoːnami]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "家並",
    "イザナミ",
    "営み",
    "伊奘冉"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「生活や生物が生命を維持するための活動。」という意味です。",
  "distractor_explanations": {
    "伊奘冉": "「伊奘冉」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。",
    "イザナミ": "「イザナミ」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。",
    "家並": "「家並」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「え」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 39661, difficulty None)
**phonetic_recognition** variant `A`, tier `T6`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "/itonami/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "伊奘冉",
    "営み",
    "人並み",
    "岩波"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「人や動物が生活し、生命を保つための活動。」という意味です。",
  "distractor_explanations": {
    "岩波": "「岩波」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「わ」、一部の音の違い）。",
    "伊奘冉": "「伊奘冉」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。",
    "人並み": "「人並み」は「営み」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「ひ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 39661, level 7

#### Pack A
### Level 7 (sense 39661, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "それはまさに、自然の営みが時間が凝縮したかような深紅を纏うリンゴであった。",
      "is_correct": false,
      "error_description": "助詞：並列を表す「と」を「が」に置き換えるのは誤り。"
    },
    {
      "text": "我々大人が往々にして見落とす微小な営みを、彼は無心に、そして厳粛に刻み続けています。",
      "is_correct": true
    },
    {
      "text": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解されます。",
      "is_correct": true
    },
    {
      "text": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれます。",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "小さな営みを積み重なる。",
      "is_correct": false,
      "error_description": "助詞：自動詞「積み重なる」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "私たちは、自然の営みを守らなければなりません。",
      "is_correct": true
    },
    {
      "text": "日々の営みの中で、多くの発見があります。",
      "is_correct": true
    },
    {
      "text": "この地域では、昔ながらの農業を中心とした素朴な営みが今も大切にされています。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 39661, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのです。",
      "is_correct": true
    },
    {
      "text": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解されます。",
      "is_correct": true
    },
    {
      "text": "我々大人が往々にして見落とす微小な営みを、彼は無心に、そして厳粛に刻み続けているのです。",
      "is_correct": true
    },
    {
      "text": "それはまさに、自然の営みが時間が凝縮したかような深紅を纏うリンゴでした。",
      "is_correct": false,
      "error_description": "「自然の営み」と「時間」は並列されて「凝縮した」にかかるため、並立助詞「と」を用いるのが適切です。「が」を用いると「自然の営み」だけが主語となり、「時間が」との係り受けが破綻します。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "小さな営みを積み重なる。",
      "is_correct": false,
      "error_description": "助詞：自動詞「積み重なる」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "生物の営みは不思議ですね。",
      "is_correct": true
    },
    {
      "text": "人々の営みを守りたいです。",
      "is_correct": true
    },
    {
      "text": "日々の営みが続いています。",
      "is_correct": true
    }
  ]
}
```

---

## sense 53352, level 1

#### Pack A
### Level 1 (sense 53352, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "超える",
  "pronunciation": "こえる",
  "ipa": "/koeru/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "仔猿",
    "超える",
    "据える",
    "生える"
  ],
  "correct_answer": "超える",
  "explanation": "正解です。「超える」は「限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。」という意味です。",
  "distractor_explanations": {
    "据える": "「据える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「す」、一部の音の違い）。",
    "仔猿": "「仔猿」は「超える」と一モーラだけ異なる実在語です（2モーラ目: 「え」→「ざ」、一部の音の違い）。",
    "生える": "「生える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「は」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 53352, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "超える",
  "pronunciation": "こえる",
  "ipa": "/ko.e.ru/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "超える",
    "篭める",
    "小江戸",
    "燃える"
  ],
  "correct_answer": "超える",
  "explanation": "正解です。「超える」は「限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。」という意味です。",
  "distractor_explanations": {
    "燃える": "「燃える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「も」、一部の音の違い）。",
    "小江戸": "「小江戸」は「超える」と一モーラだけ異なる実在語です（3モーラ目: 「る」→「ど」、一部の音の違い）。",
    "篭める": "「篭める」は「超える」と一モーラだけ異なる実在語です（2モーラ目: 「え」→「め」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 53352, level 4

#### Pack A
### Level 4 (sense 53352, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "学校の行事では、Tシャツのデザインはただの飾りを___、グループの中の立場や個性を表すものとして使われることがあります。",
  "original_sentence": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形（中止法）",
  "options": [
    "超えない",
    "超えた",
    "超え",
    "超えよう"
  ],
  "explanation": "連用形で読点の後の句へ並べてつなぐ中止法になる",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "学校の行事では、Tシャツのデザインはただの飾り___超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "original_sentence": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
  "options": [
    "が",
    "を",
    "に",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "が": "object_marking",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語（飾り）を標示する格助詞"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "original_sentence": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "未然形（ない形）",
  "options": [
    "超えた",
    "超える",
    "超えろ",
    "超え"
  ],
  "explanation": "「ない」に続く未然形で「超えない」となる",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超える"
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想___超え、そこには素晴らしい景色が広がっていました。",
  "original_sentence": "予想を超え、そこには素晴らしい景色が広がっていました。",
  "options": [
    "で",
    "を",
    "が",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "超える",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語（基準）を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 53352, difficulty None)
**morphology_slot** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "学校の行事という特別な場において、Tシャツのデザインはただの飾りを___、グループ内の細かい違いや個性を表すものとして働きます。",
  "original_sentence": "学校の行事という特別な場において、Tシャツのデザインはただの飾りを超え、グループ内の細かい違いや個性を表すものとして働きます。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形（中止法）",
  "options": [
    "超えます",
    "超える",
    "超えない",
    "超え"
  ],
  "explanation": "書き言葉の文脈において、連用形による中止法として後続の句を自然に導く正しい形です。",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "学校の行事という特別な場において、Tシャツのデザインはただの飾り___超え、グループ内の細かい違いや個性を表すものとして働きます。",
  "original_sentence": "学校の行事という特別な場において、Tシャツのデザインはただの飾りを超え、グループ内の細かい違いや個性を表すものとして働きます。",
  "options": [
    "で",
    "に",
    "が",
    "を"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "が": "topic_vs_subject",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」が超えるべき基準や限度（この場合は「飾り」）の直接目的語を標示する"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "想像を___結果だった。",
  "original_sentence": "想像を超える結果だった。",
  "correct_answer": "超える",
  "base_form": "超える",
  "form_label": "辞書形（連体形）",
  "options": [
    "超えます",
    "超えて",
    "超える",
    "超え"
  ],
  "explanation": "名詞「結果」を修飾するには連体形（辞書形）の「超える」が必要です。",
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超える"
}
```
**particle_selection** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "この活動は、ただ植物___育てることを超え、自然環境を元に戻し、人々の結びつきを深めることを同時に目指している点に特徴があります。",
  "original_sentence": "この活動は、ただ植物を育てることを超え、自然環境を元に戻し、人々の結びつきを深めることを同時に目指している点に特徴があります。",
  "options": [
    "が",
    "を",
    "で",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "が": "object_marking",
    "に": "location_vs_target",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語を標示する"
    }
  }
}
```

---

## sense 53352, level 6

#### Pack A
### Level 6 (sense 53352, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼女の能力は、超えています私たちの予想を。",
      "is_correct": false
    },
    {
      "text": "彼女の能力は、私たちの予想を超えています。",
      "is_correct": true
    },
    {
      "text": "彼女の能力は、私たちの予想を超えっています。",
      "is_correct": false
    },
    {
      "text": "彼女の能力は、私たちの予想に超えています。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「超える」は「を」格の目的語を取ります。「に」は誤りです。 活用・アスペクトの誤り：「超える」の継続・状態を表すには「超えています」が正しく、「超えっています」は活用形が誤りです。 語順・係り受けの誤り：目的語「私たちの予想を」は動詞「超えています」の直前に配置するのが自然な日本語の語順です。",
  "target_word": "超え"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "超え",
  "relation": "antonym",
  "options": [
    "及ぶ",
    "下回る",
    "低下する",
    "上回る"
  ],
  "correct_answer": "下回る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
      "explanation": "数量や水準が基準より小さいことを表し、対義関係が成立する"
    }
  }
}
```

#### Pack B
### Level 6 (sense 53352, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "その行為は単なるガーデニングの域に超え、自然の摂理に対する静かなる祈りにも似ています。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超えで、自然の摂理に対する静かなる祈りにも似ています。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ています。",
      "is_correct": true
    },
    {
      "text": "その行為は単なるガーデニングの域を超え、自然の摂理に対する静かなる祈りにも似ているです。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：「超え」の後に「で」を続けることはできません。連用形「超え」で一度文を区切るか、「超えて」とする必要があります。 語域・形態素の誤り：「似ている」の後に丁寧語の「です」を直接続けることはできません。「似ています」とするのが正しい日本語の語法です。 助詞の混同：「域」は「超える」動作の起点や通過点ではなく、直接目的語（対象）です。ここでは「を」を使い「域を超え」とする必要があります。",
  "target_word": "超え"
}
```
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "超え",
  "relation": "antonym",
  "options": [
    "維持する",
    "達する",
    "上回る",
    "下回る"
  ],
  "correct_answer": "下回る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
      "explanation": "数量や水準が基準より小さいことを表し、目標語の厳密な対義語となる。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "その悲痛な叫び声は、想定されていた音量の限界を超えて、会場全体に響き渡った。",
      "is_correct": false
    },
    {
      "text": "その悲痛な叫び声は、想定されていた音量の限界を超えて、会場全体に響き渡りました。",
      "is_correct": true
    },
    {
      "text": "その悲痛な叫び声は、会場全体に響き渡り、想定されていた音量の限界を超えていました。",
      "is_correct": false
    },
    {
      "text": "その悲痛な叫び声は、想定されていた音量の限界を超え、会場全体に響き渡りました。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「超える」は他動詞であり、「限界」という目的語を取るため、格助詞「て」ではなく「を」が必要です。 活用・アスペクトの誤り：文全体が過去の出来事（響き渡りました）を述べているため、後続の動詞「響き渡る」も過去の助動詞「た」を伴う必要があります。 語順・係り受けの誤り：「限界を超えていた」という状態が先にあり、その結果として「響き渡った」という自然な因果関係にするため、原因・程度を表す句は結果の動詞より前に置くべきです。",
  "target_word": "超え"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "超え",
  "relation": "antonym",
  "options": [
    "及ぶ",
    "上回る",
    "下がる",
    "下回る"
  ],
  "correct_answer": "下回る",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
      "explanation": "数量や水準が基準より小さいことを表し、目標語の語義と対義関係にある"
    }
  }
}
```

---

## sense 53352, level 7

#### Pack A
### Level 7 (sense 53352, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "微生物の働きによる発酵は、ただの保存方法を超え、主食の持つ可能性を大きく広げる素晴らしい化学的な技術だと言います。",
      "is_correct": false,
      "error_description": "「〜と言える」という可能・推量の表現を用いて事物的な性質を客観的に評価する場面で、動作主の意志を表す「〜と言います」とするのは不自然です。文脈に合わせて「〜と言えます」を用いるのが適切です。"
    },
    {
      "text": "微生物の働きによる発酵は、ただの保存方法を超え、主食の持つ可能性を大きく広げる素晴らしい化学的な技術だと言えます。",
      "is_correct": true
    },
    {
      "text": "学校の行事という特別な場において、Tシャツのデザインはただの飾りを超え、グループ内の細かい違いや個性を表すものとして働きます。",
      "is_correct": true
    },
    {
      "text": "この活動は、ただ植物を育てることを超え、自然環境を元に戻し、人々の結びつきを深めることを同時に目指している点に特徴があります。",
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
      "text": "彼の成績は、いつも平均を超えしている。",
      "is_correct": false,
      "error_description": "誤り型：活用・アスペクトの誤り。動詞「超える」の連用形「超え」に、進行・継続の助動詞「している」を直接接続することはできません。正しくは「超えている」とします。"
    },
    {
      "text": "その悲痛な叫び声は、想定されていた音量の限界を超えて、会場全体に響き渡りました。",
      "is_correct": true
    },
    {
      "text": "目標を超えて努力する。",
      "is_correct": true
    },
    {
      "text": "想像を超える結果だった。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 53352, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "目に見えない菌の働きは、ただ食べ物を長持ちさせる方法を超え、私たちの食生活をより美味しく豊かにする素晴らしい技術です。",
      "is_correct": true
    },
    {
      "text": "この活動は、ただ植物を育てることを超え、自然環境を守りながら、人々の絆を深めることにもつながっています。",
      "is_correct": true
    },
    {
      "text": "気温が三十度が超えた。",
      "is_correct": false,
      "error_description": "助詞の混同：超える対象は「を」で示す。「三十度が」ではなく「三十度を」が正しい。"
    },
    {
      "text": "学校の行事では、Tシャツのデザインはただの飾りを超え、グループの中の立場や個性を表すものとして使われることがあります。",
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
      "text": "彼女の能力は、私たちの予想を超えています。",
      "is_correct": true
    },
    {
      "text": "明日、参加者は百人を超えた。",
      "is_correct": false,
      "error_description": "活用・アスペクトの誤り：未来の「明日」に過去形「超えた」は合わない。「超える」が正しい。"
    },
    {
      "text": "予想を超えて、とても嬉しかったです。",
      "is_correct": true
    },
    {
      "text": "予想を超え、そこには素晴らしい景色が広がっていました。",
      "is_correct": true
    }
  ]
}
```

---
