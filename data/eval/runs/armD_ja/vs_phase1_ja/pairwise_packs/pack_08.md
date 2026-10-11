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


## sense 39187, level 6

#### Pack A
### Level 6 (sense 39187, difficulty None)
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "自らの",
  "relation": "antonym",
  "options": [
    "他人の",
    "彼の",
    "我々の",
    "誰かの"
  ],
  "correct_answer": "他人の",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "自分自身を指す言葉。",
      "explanation": "自分自身以外の者を指す言葉であり、「自らの」の対義語となる。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "自らの夢を諦めないでください。",
      "is_correct": true
    },
    {
      "text": "自らの未来は自分で決めるは大切だ。",
      "is_correct": false
    },
    {
      "text": "自らのの未来は自分で決める。",
      "is_correct": false
    },
    {
      "text": "自らの未来は自分で決めった。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の重複：「自らの」の後ろにさらに「の」が余分に重ねられており、文法的に誤りです。 活用の誤り：動詞「決める」の過去形は「決めた」であり、「決めった」という活用形は存在しません。 語順・係り受けの誤り：「自分で決める」が名詞節として機能しておらず、主題「は」の提示が文法的に破綻しています。",
  "target_word": "自らの"
}
```

#### Pack B
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "自ら守るがルールです。",
      "is_correct": false
    },
    {
      "text": "自らをルールが守る。",
      "is_correct": false
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
      "is_correct": true
    },
    {
      "text": "自らが守るルールだ。",
      "is_correct": false
    }
  ],
  "explanation": "項構造：「自ら」は「守る」動作の主体（主語）ではなく、対象（目的語）です。正しくは「自らが守るルール」です。 語域：「だ」は口語的な断定表現であり、基礎例文の「自らが守るルールです」という丁寧な表現と語域が一致しません。 語順：「自ら守るが」の「が」の位置が誤りです。名詞を修飾する場合は「自ら守るルール」となるべきです。",
  "target_word": "自ら"
}
```

---

## sense 39187, level 7

#### Pack A
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    },
    {
      "text": "私は自らの手で花を植えった。",
      "is_correct": false,
      "error_description": "動詞「植える」の過去形の活用誤りです。「植えった」ではなく、正しくは「植えた」となります。"
    },
    {
      "text": "私は自らの手で花を植えた。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼は自らでそのプロジェクトを成功させた。",
      "is_correct": false,
      "error_description": "「自ら」は副詞的・名詞的に「自分自身」を指しますが、「自分で」とは異なり、助詞「で」を伴って動作の主体を表す用法はありません。「自分で」との混同による助詞の誤用です。正しくは「自ら」または「自らが」とします。"
    },
    {
      "text": "自らを責めて、泣きました。",
      "is_correct": true
    },
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められます。",
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
      "text": "自らが守るルールです。",
      "is_correct": true
    },
    {
      "text": "自らが進む道です。",
      "is_correct": true
    },
    {
      "text": "自らを進む道です。",
      "is_correct": false,
      "error_description": "助詞の混同。「自ら」は動詞「進む」の主語であるため、格助詞「が」を使うのが適切です。「を」は動作の目的語を示す際に使います。"
    },
    {
      "text": "自らが考えたアイデアです。",
      "is_correct": true
    }
  ]
}
```

---

## sense 39661, level 1

#### Pack A
### Level 1 (sense 39661, difficulty None)
**phonetic_recognition** variant `B`, tier `T6`
```json
{
  "word": "営み",
  "pronunciation": "いとなみ",
  "ipa": "/itonami/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "伊弉冉",
    "家並み",
    "営み",
    "伊邪那美"
  ],
  "correct_answer": "営み",
  "explanation": "正解です。「営み」は「生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。」という意味です。",
  "distractor_explanations": {
    "伊弉冉": "「伊弉冉」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。",
    "家並み": "「家並み」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「え」、一部の音の違い）。",
    "伊邪那美": "「伊邪那美」は「営み」と一モーラだけ異なる実在語です（2モーラ目: 「と」→「ざ」、一部の音の違い）。"
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

#### Pack B
### Level 7 (sense 39661, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T6`
```json
{
  "sentences": [
    {
      "text": "それはまさに、自然の営みが時間が凝縮したかような深紅を纏うリンゴであった。",
      "is_correct": false,
      "error_description": "助詞：並列を表す「と」を「が」に置き換えるのは誤り。"
    },
    {
      "text": "しかし、微生物の営みを経ることで、難消化性の成分は低分子化され、栄養価が劇的に向上するのみならず、フィチン酸などの抗栄養因子も分解されます。",
      "is_correct": true
    },
    {
      "text": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれます。",
      "is_correct": true
    },
    {
      "text": "我々大人が往々にして見落とす微小な営みを、彼は無心に、そして厳粛に刻み続けています。",
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
      "text": "日々の営みを大切にしたいです。",
      "is_correct": true
    },
    {
      "text": "小さな営みを積み重なる。",
      "is_correct": false,
      "error_description": "助詞：自動詞「積み重なる」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "私は自然の営みを勉強しています。",
      "is_correct": true
    },
    {
      "text": "この地域の営みを守りましょう。",
      "is_correct": true
    }
  ]
}
```

---

## sense 53352, level 3

#### Pack A
### Level 3 (sense 53352, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この活動は、ただ植物を育てることを___、自然環境を守りながら、人々の絆を深めることにもつながっています。",
  "original_sentence": "この活動は、ただ植物を育てることを超え、自然環境を守りながら、人々の絆を深めることにもつながっています。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "通り",
    "抜け",
    "過ぎ"
  ],
  "explanation": "正解です。「超え」は限度や範囲をこえることを表し、文脈に適切に適合しています。",
  "distractor_tags": {},
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "予想を___て、とても嬉しかったです。",
  "original_sentence": "予想を超えて、とても嬉しかったです。",
  "correct_answer": "超え",
  "options": [
    "超え",
    "過ぎ",
    "外れ",
    "慣れ"
  ],
  "explanation": "正解です。",
  "distractor_tags": {},
  "word_definition": "限度や範囲より、むこうへいくこと。数量や水準が、基準より、おおきいこと。",
  "target_word": "超え"
}
```

#### Pack B
### Level 3 (sense 53352, difficulty None)
**cloze_completion** variant `A`, tier `advanced`
```json
{
  "sentence_with_blank": "この活動は、単なる植物を育てることを___、自然を元に戻し、人々の協力を深めることを同時に目指している点に特徴があります。",
  "original_sentence": "この活動は、単なる植物を育てることを超え、自然を元に戻し、人々の協力を深めることを同時に目指している点に特徴があります。",
  "correct_answer": "超え",
  "options": [
    "抜け",
    "過ぎ",
    "渡り",
    "超え"
  ],
  "explanation": "正解です。単なる植物を育てるという限界をむこうへ行き、自然を元に戻す段階に至っていることを表します。",
  "distractor_tags": {},
  "word_definition": "きまりや限界をむこうへいくこと。数や程度が、もとよりおおきいこと。",
  "target_word": "超え"
}
```
**cloze_completion** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "私たちは困難を___まして、新しい未来を作っていくことができます。",
  "original_sentence": "私たちは困難を超えまして、新しい未来を作っていくことができます。",
  "correct_answer": "超え",
  "options": [
    "忘れ",
    "超え",
    "破り",
    "下げ"
  ],
  "explanation": "正解です。「困難を超える」で、限界や壁を突破するという意味が適切です。",
  "distractor_tags": {},
  "word_definition": "きまりや限界をむこうへいくこと。数や程度が、もとよりおおきいこと。",
  "target_word": "超え"
}
```

---

## sense 53352, level 4

#### Pack A
### Level 4 (sense 53352, difficulty None)
**morphology_slot** variant `A`, tier `advanced`
```json
{
  "sentence_with_blank": "学校行事という特別な空間において、Tシャツのデザインは単なる飾りを___、グループ内の細かい関係や個性の表れとして働くことがあります。",
  "original_sentence": "学校行事という特別な空間において、Tシャツのデザインは単なる飾りを超え、グループ内の細かい関係や個性の表れとして働くことがあります。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形（中止法）",
  "options": [
    "超える",
    "超え",
    "超えない",
    "超えた"
  ],
  "explanation": "連用形による中頓で、後続の節へ自然に接続しています。",
  "word_definition": "きまりや限界をむこうへいくこと。数や程度が、もとよりおおきいこと。",
  "target_word": "超え"
}
```
**morphology_slot** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "この山の標高は三千メートルを___ます。",
  "original_sentence": "この山の標高は三千メートルを超えます。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "連用形（ます形）",
  "options": [
    "超える",
    "超えて",
    "超えない",
    "超え"
  ],
  "explanation": "「ます」に接続するためには連用形である「超え」が必要です。",
  "word_definition": "きまりや限界をむこうへいくこと。数や程度が、もとよりおおきいこと。",
  "target_word": "超え"
}
```
**particle_selection** variant `B`, tier `advanced`
```json
{
  "sentence_with_blank": "この山の標高は三千メートル___超えます。",
  "original_sentence": "この山の標高は三千メートルを超えます。",
  "options": [
    "に",
    "が",
    "を",
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
      "explanation": "限界や基準をむこうへいく対象を標示する"
    }
  }
}
```

#### Pack B
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

---

## sense 53352, level 6

#### Pack A
### Level 6 (sense 53352, difficulty None)
**semantic_discrimination** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "その行為は単なるガーデニングの域を超えまして、自然の摂理に対する静かなる祈りにも似ております。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超えまして、自然の摂理に対する静かなる祈りにも似ております。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超えまして、自然の摂理に対する静かなる祈りにも似ております。",
      "is_correct": false
    },
    {
      "text": "その行為は単なるガーデニングの域を超えまして、自然の摂理に対する静かなる祈りにも似ております。",
      "is_correct": true
    }
  ],
  "explanation": "語域の誤り：「超えまして」の「まして」は丁寧語として過剰であり、静謐で文学的な「静かなる祈り」という表現と調和しません。 語域の誤り：「超えまして」の「まして」は丁寧語として過剰であり、静謐で文学的な「静かなる祈り」という表現と調和しません。 語域の誤り：「超えまして」の「まして」は丁寧語として過剰であり、静謐で文学的な「静かなる祈り」という表現と調和しません。",
  "target_word": "超え"
}
```

#### Pack B
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

---

## sense 53352, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 53352, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `advanced`
```json
{
  "sentences": [
    {
      "text": "微生物の働きである発酵は、単なる保存方法の域を超え、主食の持つ可能性を大きく広げる化学的な芸術だと言えます。",
      "is_correct": true
    },
    {
      "text": "学校行事という特別な空間において、Tシャツのデザインは単なる飾りが超え、グループ内の細かい関係や個性の表れとして働くことがあります。",
      "is_correct": false,
      "error_description": "「超える」は他動詞であり、その目的語を示す助詞は「を」になります。「飾りが超え」とすると「飾り」が主語と誤解されるため不自然です。正しくは「飾りを超え」とします。"
    },
    {
      "text": "この活動は、単なる植物を育てることを超え、自然を元に戻し、人々の協力を深めることを同時に目指している点に特徴があります。",
      "is_correct": true
    },
    {
      "text": "学校行事という特別な空間において、Tシャツのデザインは単なる飾りを超え、グループ内の細かい関係や個性の表れとして働くことがあります。",
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
      "text": "彼の努力は限界を予想を超えておりまして、心から尊敬申し上げております。",
      "is_correct": false,
      "error_description": "助詞の重複による誤りです。「限界を」と「予想を」が混ざってしまっています。正しくは「限界を超えて」または「予想を超えて」とします。"
    },
    {
      "text": "彼の努力は限界を超えておりまして、心から尊敬申し上げております。",
      "is_correct": true
    }
  ]
}
```

---
