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


## sense 38099, level 3

#### Pack A
### Level 3 (sense 38099, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと___させる、高度な技術と美意識の結晶なのである。",
  "original_sentence": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
  "correct_answer": "昇華",
  "options": [
    "変化",
    "固化",
    "昇華",
    "劣化"
  ],
  "explanation": "正解です。文脈にある「恒久の美へと～させる」という表現は、自然の産物をより高い芸術的・精神的価値へ高めるプロセスを表しており、「昇華」が適切です。",
  "distractor_tags": {},
  "word_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "target_word": "昇華"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "悲しみが芸術作品へと___した。",
  "original_sentence": "悲しみが芸術作品へと昇華した。",
  "correct_answer": "昇華",
  "options": [
    "変化",
    "進化",
    "発展",
    "昇華"
  ],
  "explanation": "「自信へと昇華する」は高い段階への高まりを表す固定表現。",
  "distractor_tags": {},
  "word_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "target_word": "昇華"
}
```

#### Pack B
### Level 3 (sense 38099, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと___させる、高度な技術と美意識の結晶なのである。",
  "original_sentence": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
  "correct_answer": "昇華",
  "options": [
    "昇華",
    "変化",
    "進化",
    "発展"
  ],
  "explanation": "「確立へと昇華される」は高い段階への高まりを表す固定表現。",
  "distractor_tags": {},
  "word_definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
  "target_word": "昇華"
}
```

---

## sense 38099, level 6

#### Pack A
### Level 6 (sense 38099, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
      "is_correct": true
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと三つ昇華される。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華している。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物は、生命の維持と豊かな食体験を同時に叶える食文化へを昇華する。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「昇華」は抽象的な過程や状態の変化を表す名詞（サ変名詞）であり、具体的な物体のように「三つ」といった個数を数える助数詞をつけることはできません。 助詞の混同：到達点や変化の結果を表す場合は「～へ」または「～へと」を用います。「へを」と二重に助詞を重ねることは文法的に誤りです。 アスペクトの誤り：この文脈では、穀物が食文化という完成された状態へと至った事実や定義を述べており、進行中や状態の継続を表す「ている」よりも、完了や事実叙述に適した形（原文のような受動態や単純過去など）の方が自然です。また、無生物主語による自発的な変化の文脈では、他動詞的な用法としての「昇華される」あるいは結果状態を示す表現が一般的です。",
  "target_word": "昇華"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "苦労が喜びへと昇華しった。",
      "is_correct": false
    },
    {
      "text": "昇華した喜びへと、苦労が。",
      "is_correct": false
    },
    {
      "text": "長年の苦悩と努力は、最終的に偉大な芸術作品へと昇華した。",
      "is_correct": true
    },
    {
      "text": "苦労が喜びへが昇華した。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：結果を示す「へと」を「へが」に置き換えるのは誤り。 活用：過去形は「昇華した」であり、「昇華しった」は促音を誤って挿入した形。 語順：述語を文頭付近に置き、係り受けが崩れている。",
  "target_word": "昇華"
}
```

#### Pack B
### Level 6 (sense 38099, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華せれる。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化へと昇華される。",
      "is_correct": true
    },
    {
      "text": "叶える食文化へと昇華される、生命の維持と豊かな食体験を同時に、穀物が。",
      "is_correct": false
    },
    {
      "text": "単なるエネルギー源に過ぎなかった穀物が、生命の維持と豊かな食体験を同時に叶える食文化が昇華される。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：結果を示す「へと」を「が」に置き換えるのは誤り。 活用：受身形は「される」であり、「せれる」は存在しない形。 語順：修飾関係が崩れ、係り受けが不明瞭になっている。",
  "target_word": "昇華"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "想いは、歌へと昇華している。",
      "is_correct": true
    },
    {
      "text": "想いは、歌へと昇華したことがある。",
      "is_correct": false
    },
    {
      "text": "想いは、昇華している歌へと。",
      "is_correct": false
    },
    {
      "text": "想いは、歌で昇華している。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「で」は場所や手段を表します。変化の到達点を表すには「へと」や「に」を使う必要があります。 活用・アスペクトの誤り：「たことがある」は過去の経験を表します。現在の状態や継続的な変化には「ている」が適切です。 語順・係り受けの誤り：「昇華している」が直後の「歌」を修飾する形になり、「想い」が昇華するという本来の意味が壊れています。",
  "target_word": "昇華"
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "antonym",
  "options": [
    "転換",
    "停滞",
    "堕落",
    "進化"
  ],
  "correct_answer": "堕落",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。",
      "explanation": "価値や精神が低い状態へ落ちることを表し、高まることの対義となる"
    }
  }
}
```

---

## sense 38099, level 7

#### Pack A
### Level 7 (sense 38099, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    },
    {
      "text": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
      "is_correct": true
    },
    {
      "text": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へが昇華されるのである。",
      "is_correct": false,
      "error_description": "誤り型：助詞の混同。変化や到達点を示す方向性には「へ」または「に」を用います。「が」は主語を示す格助詞であり、ここでは不適切です。"
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 38099, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "生徒たちが繊維の纹理に想いを込め、独自のプロットを紡ぎ出すとき、それは単なる被服製作ではなく、記号的な自己主張の確立へと昇華されるのである。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへが昇華させるのである。",
      "is_correct": false,
      "error_description": "助詞：結果を示す「へと」を「へが」に置き換えるのは誤り。"
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
      "is_correct": true
    }
  ]
}
```

---

## sense 39187, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 39187, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "先生は自ら答えを教えてくれった。",
      "is_correct": false,
      "error_description": "動詞の活用形の誤りです。「くれる」の過去形・丁寧語は「くれました」が正しく、「くれった」は存在しない形、または「くれた」の誤用です。文脈に合わせて正しい活用形を選びましょう。"
    },
    {
      "text": "先生は自ら答えを教えてくれました。",
      "is_correct": true
    },
    {
      "text": "彼女は自らの夢について話しました。",
      "is_correct": true
    },
    {
      "text": "友達は自ら荷物を持っています。",
      "is_correct": true
    }
  ]
}
```

---

## sense 39661, level 3

#### Pack A
### Level 3 (sense 39661, difficulty None)
**cloze_completion** variant `A`, tier `T6`
```json
{
  "sentence_with_blank": "童子の行為は、単なる日常的な___の模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのです。",
  "original_sentence": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのです。",
  "correct_answer": "営み",
  "options": [
    "営み",
    "仕事",
    "業務",
    "動作"
  ],
  "explanation": "正解です。文脈にある「生命の循環に対する原初的な祈りにも似た」活動は、自然や生物の「営み」と結びつくのが適切です。",
  "distractor_tags": {},
  "word_definition": "人や動物が生活し、生命を保つための活動。",
  "target_word": "営み"
}
```

#### Pack B
### Level 3 (sense 39661, difficulty None)
**cloze_completion** variant `A`, tier `T5`
```json
{
  "sentence_with_blank": "童子の行為は、単なる日常的な___の模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのである。",
  "original_sentence": "童子の行為は、単なる日常的な営みの模倣を超え、生命の循環に対する原初的な祈りにも似た、崇高な儀式としてそこに刻まれるのである。",
  "correct_answer": "営み",
  "options": [
    "仕事",
    "動作",
    "習慣",
    "営み"
  ],
  "explanation": "正解です。文脈にある「日常的な〜」という表現には、人間が行う継続的な活動や生活そのものを指す「営み」が最も適しています。",
  "distractor_tags": {},
  "word_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
  "target_word": "営み"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "日々の___を大切にしよう。",
  "original_sentence": "日々の営みを大切にしよう。",
  "correct_answer": "営み",
  "options": [
    "仕組み",
    "計らい",
    "営み",
    "段取り"
  ],
  "explanation": "正解です。「日々の営み」は、日常生活の活動や暮らしそのものを指す自然な表現です。",
  "distractor_tags": {},
  "word_definition": "生活や生計を立てるための活動、または生物が生命を維持し続けるための行動。",
  "target_word": "営み"
}
```

---

## sense 39661, level 7

#### Pack A
### Level 7 (sense 39661, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "小さな営みを積み重なる。",
      "is_correct": false,
      "error_description": "助詞：自動詞「積み重なる」の主体は「が」で示す。「を」は誤り。"
    },
    {
      "text": "彼の営みは静かで美しい。",
      "is_correct": true
    },
    {
      "text": "日々の営みを大切にしよう。",
      "is_correct": true
    },
    {
      "text": "自然の営みを感じている。",
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
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "超える",
  "pronunciation": "こえる",
  "ipa": "ko.e.ru",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "食える",
    "副える",
    "植える",
    "超える"
  ],
  "correct_answer": "超える",
  "explanation": "正解です。「超える」は「きまった数やレベルより、多くなること。」という意味です。",
  "distractor_explanations": {
    "植える": "「植える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「う」、一部の音の違い）。",
    "食える": "「食える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「く」、一部の音の違い）。",
    "副える": "「副える」は「超える」と一モーラだけ異なる実在語です（1モーラ目: 「こ」→「そ」、一部の音の違い）。"
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
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "今年の売上は、去年の記録を大きく___ました。",
  "original_sentence": "今年の売上は、去年の記録を大きく超えました。",
  "correct_answer": "超え",
  "options": [
    "過ぎ",
    "超え",
    "抜け",
    "変わり"
  ],
  "explanation": "正解です。文脈「去年の記録を大きく__ました」には、数値や水準が上限を上回ることを示す「超え」が最も適しています。",
  "distractor_tags": {},
  "word_definition": "きまった数やレベルより、多くなること。",
  "target_word": "超え"
}
```
**cloze_completion** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "山の高さは三千メートルを___ます。",
  "original_sentence": "山の高さは三千メートルを超えます。",
  "correct_answer": "超え",
  "options": [
    "入り",
    "過ぎ",
    "超え",
    "抜け"
  ],
  "explanation": "正解です。「三千メートルを超えます」は、高さがその数値を上回ることを正しく表しています。",
  "distractor_tags": {},
  "word_definition": "きまった数やレベルより、多くなること。",
  "target_word": "超え"
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
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "参加者の数は、定員の五十人を___ています。",
  "original_sentence": "参加者の数は、定員の五十人を超えています。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "ます形語幹",
  "options": [
    "超えた",
    "超え",
    "超えて",
    "超える"
  ],
  "explanation": "「います」に接続する連用形（ます形の語幹）が正解です。",
  "word_definition": "きまった数やレベルより、多くなること。",
  "target_word": "超え"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "制限時間を___てはいけません。",
  "original_sentence": "制限時間を超えてはいけません。",
  "correct_answer": "超え",
  "base_form": "超える",
  "form_label": "未然形（ない形）",
  "options": [
    "超えた",
    "超え",
    "超える",
    "超えろ"
  ],
  "explanation": "「ない」に続く未然形で「超えない」となる",
  "word_definition": "きまった数やレベルより、多くなること。",
  "target_word": "超え"
}
```
**particle_selection** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "制限時間___超えてはいけません。",
  "original_sentence": "制限時間を超えてはいけません。",
  "options": [
    "と",
    "で",
    "を",
    "に"
  ],
  "correct_answer": "を",
  "target_word": "超え",
  "error_tags": {
    "に": "location_vs_target",
    "で": "instrument",
    "と": "other"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「超える」の直接目的語（基準となる数やレベル）を示す格助詞です。"
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
**semantic_discrimination** variant `A`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "今回の試験の平均点は、前回よりも十点を超えにしました。",
      "is_correct": false
    },
    {
      "text": "今回の試験の平均点は、前回よりも十点を超えられています。",
      "is_correct": false
    },
    {
      "text": "今回の試験の平均点は、前回よりも十点を超えがあります。",
      "is_correct": false
    },
    {
      "text": "今回の試験の平均点は、前回よりも十点超えました。",
      "is_correct": true
    }
  ],
  "explanation": "活用・アスペクトの誤り：「超える」は他動詞であり、受身形「超えられる」は通常、能力可能（超えられる＝超えることができる）または迷惑受身として使われます。単に事実として上回ったことを述べる文脈では、能動態の「超えました」が正しく、受身形は不自然です。 語形・構文の誤り：「超え」は動詞の連用形であり、名詞のように「～にしました」の対象とすることはできません。「十点を超えるようにしました」または「十点を超えました」とする必要があります。 構文の誤り：動詞の連用形「超え」に直接「があります」を接続することはできません。存在や所有を表す文型ではなく、事象の発生や状態変化を表すため、「超えています」または「超えました」を用いる必要があります。",
  "target_word": "超え"
}
```
**semantic_discrimination** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "温度が基準を超えています。",
      "is_correct": true
    },
    {
      "text": "温度が基準を超えいる。",
      "is_correct": false
    },
    {
      "text": "温度が基準を超えているです。",
      "is_correct": false
    },
    {
      "text": "温度が基準を超えてある。",
      "is_correct": false
    }
  ],
  "explanation": "活用・アスペクトの誤り：不自然です。形容動詞や名詞述語ではないため、「〜ている」の後に直接「です」をつけるのは口語的すぎます。通常は「超えています」と丁寧語尾をつけます。 活用・アスペクトの誤り：誤りです。「超える」は自動詞的な用法（状態変化）が多く、他動詞としての「〜てある」（誰かが意図的に行った結果の状態）の形をとるのは不自然です。 活用・アスペクトの誤り：誤りです。進行・状態を表す補助動詞「いる」に接続する場合、動詞はテ形「超えて」である必要があります。「超えいる」は文法錯誤です。",
  "target_word": "超え"
}
```

---
