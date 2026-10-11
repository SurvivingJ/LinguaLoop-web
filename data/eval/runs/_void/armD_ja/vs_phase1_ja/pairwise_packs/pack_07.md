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


## sense 36181, level 4

#### Pack A
### Level 4 (sense 36181, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "これは事業の終了ではなく、資本の循環と___な創造への移行を意味する重要なプロセスだ。",
  "original_sentence": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
  "correct_answer": "新た",
  "base_form": "新た",
  "form_label": "語幹（な形容動詞・連体形の前）",
  "options": [
    "新た",
    "新たに",
    "新ただ",
    "新たなら"
  ],
  "explanation": "「な」を伴い名詞を修飾する連体形の語幹。",
  "word_definition": "今までと違う、新しい状態になることです。",
  "target_word": "新た"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "戦後の都市計画において、ブルータリズムは機能性を重視した___な住宅様式として普及しました。",
  "original_sentence": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及しました。",
  "correct_answer": "新たな",
  "base_form": "新た",
  "form_label": "連体形",
  "options": [
    "新たに",
    "新たで",
    "新たな",
    "新ただ"
  ],
  "explanation": "名詞「住宅様式」を修飾するためには連体形の「新たな」が必要です。",
  "word_definition": "今までと違う、新しい状態になることです。",
  "target_word": "新た"
}
```

#### Pack B
### Level 4 (sense 36181, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この町には、___歴史が生まれます。",
  "original_sentence": "この町には、新たな歴史が生まれます。",
  "correct_answer": "新たな",
  "base_form": "新たな",
  "form_label": "連体形",
  "options": [
    "新ただ",
    "新たな",
    "新たに",
    "新たで"
  ],
  "explanation": "名詞「歴史」を修飾するには連体形「新たな」が必要です。",
  "word_definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
  "target_word": "新たな"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___目標を、ノートに書きました。",
  "original_sentence": "新たな目標を、ノートに書きました。",
  "correct_answer": "新たな",
  "base_form": "新たな",
  "form_label": "連体形",
  "options": [
    "新たで",
    "新たな",
    "新たに",
    "新ただ"
  ],
  "explanation": "名詞「目標」を修飾するには連体形「な」が必要です",
  "word_definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
  "target_word": "新たな"
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
      "text": "新たな時代が、静かに幕を開けました。",
      "is_correct": false
    },
    {
      "text": "新たなが時代を、静かに幕を開けました。",
      "is_correct": false
    },
    {
      "text": "新たな時代が、静かに幕を開けました。",
      "is_correct": true
    },
    {
      "text": "新たなを、私たちは歓迎しました。",
      "is_correct": false
    }
  ],
  "explanation": "正しい文です。 助詞の混同：「新たな」は形状詞であり、名詞のように単独で「を」の目的語になることはできません。「新たな仲間」のように名詞を修飾する必要があります。 語順・係り受けの誤り：「が」の位置が誤りです。「新たな」は「時代」を修飾すべきであり、「新たな時代が」とするのが正しい語順です。",
  "target_word": "新たな"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "新たな",
  "relation": "antonym",
  "options": [
    "旧套な",
    "斬新な",
    "古風な",
    "陳腐な"
  ],
  "correct_answer": "旧套な",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "「新た」は「新しい」という意味の形容動詞で、何かが今までと違う状態になることを表します。",
      "explanation": "「古い慣習ややり方」を意味し、「今までと違う新しい状態」という目標語の対義語となります。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "新たな始まりを、皆で祝いっています。",
      "is_correct": false
    },
    {
      "text": "新たな始まりを、皆で祝いました。",
      "is_correct": false
    },
    {
      "text": "新たなを始まり、皆で祝いました。",
      "is_correct": false
    },
    {
      "text": "新たな始まりを、皆で祝いました。",
      "is_correct": true
    }
  ],
  "explanation": "助詞の混同：「新たな」が修飾する「始まり」は動作の結果ではなく状態や事柄であるため、目的語を示す「を」ではなく、存在や状態の主体を示す「が」を使うのが自然です。（新たな始まりが…） 活用・アスペクトの誤り：進行形や状態の継続を表す補助動詞「いる」の活用が誤っており、正しくは「祝っています」とする必要があります。 語順・係り受けの誤り：形状詞「新たな」は直後に名詞を置いて修飾する必要があります。助詞「を」を挟んで名詞から離れており、文構造が破綻しています。",
  "target_word": "新たな"
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

## sense 36181, level 7

#### Pack A
### Level 7 (sense 36181, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この町には、新たな歴史が生まれます。",
      "is_correct": true
    },
    {
      "text": "私たちは、新たな仲間を歓迎しました。",
      "is_correct": true
    },
    {
      "text": "私は、新たな決意で勉強を始めました。",
      "is_correct": true
    },
    {
      "text": "この町に、新たな歴史が生まれます。",
      "is_correct": false,
      "error_description": "場所を表す名詞の後ろで、存在や出現の場所を示すには助詞「に」を使います。「は」を使うと主題が強調されすぎて不自然になります。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "新たな目標を、ノートに書きまし。",
      "is_correct": false,
      "error_description": "「ました」は「ました」が正しい形です。動詞の過去・丁寧形の活用を間違えないようにしましょう。"
    },
    {
      "text": "新たな始まりを、皆で祝いました。",
      "is_correct": true
    },
    {
      "text": "新たな道を選んで、歩き出しました。",
      "is_correct": true
    },
    {
      "text": "新たな目標を、ノートに書きました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 36181, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "地元の風景を愛するロックバンドが、新たな決意で新アルバムのレコーディングに臨みました。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": true
    },
    {
      "text": "単なる出資にとどまらず、経営戦略やネットワークを提供することで、市場に新ただ価値を生むイノベーションを加速させるのだ。",
      "is_correct": false,
      "error_description": "活用：名詞の前では連体形「新たな」を使う。「新ただ」は誤り。"
    },
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
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
      "text": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及する。",
      "is_correct": false,
      "error_description": "「戦後の都市計画」という過去の文脈であるため、動詞の活用は過去形の「普及しました」が適切です。「普及する」は現在・未来形であり、文脈に合いません。"
    },
    {
      "text": "しかし現代ファッションの文脈では、この伝統的な職人技はデジタルデザインという新たなパラダイムと衝突し、あるいは融合しつつある。",
      "is_correct": true
    },
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈における自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": true
    },
    {
      "text": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及しました。",
      "is_correct": true
    }
  ]
}
```

---

## sense 38099, level 1

#### Pack A
### Level 1 (sense 38099, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "pronunciation": "しょうか",
  "ipa": "[ɕoːka]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "城下",
    "召致",
    "昇華",
    "松樹"
  ],
  "correct_answer": "昇華",
  "explanation": "正解です。「昇華」は「ある物事が、より高い段階や価値のある状態へと高まること。比喩的に、精神的な高まりを表すこともあります。」という意味です。",
  "distractor_explanations": {
    "召致": "「召致」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ち」、一部の音の違い）。",
    "城下": "「城下」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「じょ」、清濁・半濁音の対立）。",
    "松樹": "「松樹」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「じゅ」、一部の音の違い）。"
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

## sense 38099, level 3

#### Pack A
### Level 3 (sense 38099, difficulty None)
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "悲しみが芸術に___する。",
  "original_sentence": "悲しみが芸術に昇華する。",
  "correct_answer": "昇華",
  "options": [
    "昇進",
    "昇華",
    "変換",
    "転換"
  ],
  "explanation": "正解です。悲しみという感情が芸術という高い価値を持つものへと高められることを表します。",
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

#### Pack B
### Level 6 (sense 38099, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華した、高度な技術と美意識の結晶なのである。",
      "is_correct": false
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと一個の昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": false
    },
    {
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へを昇華、高度な技術と美意識の結晶なのである。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「昇華」は抽象的な概念を表す名詞であり、「一個」のような具体的な個数を表す助数詞を伴うことはできません。 助詞の混同：「美へと」の「と」が「を」に置き換わっており、到達点や結果の状態を示す格助詞の使い方が誤っています。 活用・アスペクトの誤り：「昇華させる」という使役の表現が「昇華した」という完了・過去の表現に置き換わっており、文の論理構造が破綻しています。",
  "target_word": "昇華"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "過酷な体験は、やがて人間としての真の精神的成長へに昇華されるのである。",
      "is_correct": false
    },
    {
      "text": "過酷な体験は、やがて人間としての真の精神的成長へと昇華したである。",
      "is_correct": false
    },
    {
      "text": "過酷な体験は、やがて人間としての真の精神的成長へと一冊の昇華されるのである。",
      "is_correct": false
    },
    {
      "text": "過酷な体験は、やがて人間としての真の精神的成長へと昇華されるのである。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「昇華」は抽象的な概念を表す名詞であり、「一冊の」といった物理的な本に用いる助数詞を伴うことはできません。 助詞の混同：到達点や変化の結果を表す「へと」が正しく、「へに」という助詞の組み合わせは文法的に誤りです。 活用・アスペクトの誤り：「昇華する」の過去・完了の丁寧な表現は「昇華した」または「昇華したのである」が正しく、「昇華したである」という活用形は存在しません。",
  "target_word": "昇華"
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
      "text": "この一連の作業は、移ろいやすい自然の産物を、人間の手によって恒久の美へと昇華させる、高度な技術と美意識の結晶なのである。",
      "is_correct": true
    },
    {
      "text": "この個人的な苦悩は、やがて偉大な芸術家によって巧妙に咀嚼され、普遍的な美意識へと昇華したのだ。",
      "is_correct": false,
      "error_description": "「昇華する」は他動詞的な意味合いで使われることが多く、受身形の「昇華される」を用いるのが自然です。また、文脈から完了の「た」よりも、一般的な真理やプロセスを表す「られる」が適切です。"
    },
    {
      "text": "この創造的プロセスこそが、行事の記憶を永続的なものへと変貌させ、参加者の帰属意識を強固なものへと昇華させるのである。",
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
      "text": "怒りが力へと昇華した。",
      "is_correct": true
    },
    {
      "text": "過酷な体験は、やがて人間としての真の精神的成長へと昇華されるのである。",
      "is_correct": true
    },
    {
      "text": "悲しみを芸術に昇華する。",
      "is_correct": false,
      "error_description": "「昇華する」は自動詞として「〜が〜に昇華する」の形をとります。対象を「を」で示す場合は、使役形の「昇華させる」を用いる必要があります。"
    },
    {
      "text": "悲しみが芸術に昇華する。",
      "is_correct": true
    }
  ]
}
```

---

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "みず垣",
    "水腹",
    "自ら",
    "水占"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "みず垣": "「みず垣」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「き」、一部の音の違い）。",
    "水腹": "「水腹」は「自ら」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「ば」、一部の音の違い）。",
    "水占": "「水占」は「自ら」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「う」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 39187, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "水カビ",
    "蹼",
    "自ら",
    "ミズカビ"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "ミズカビ": "「ミズカビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "蹼": "「蹼」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「き」、一部の音の違い）。",
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 39187, level 6

#### Pack A
### Level 6 (sense 39187, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "大切だ自らを信じることが。",
      "is_correct": false
    },
    {
      "text": "自らを信じるが大切だ。",
      "is_correct": false
    },
    {
      "text": "自らの意見を堂々と発表できました。",
      "is_correct": true
    },
    {
      "text": "自らが信じることが大切だ。",
      "is_correct": false
    }
  ],
  "explanation": "助詞：他動詞「信じる」の対象は「を」で示す。「が」は誤り。 活用：形式名詞「こと」を欠くのは誤り。「信じることが」が正しい。 語順：述語を文頭に置き、係り受けが崩れている。",
  "target_word": "自ら"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "自らに言葉で素直に謝りました。",
      "is_correct": false
    },
    {
      "text": "自らの言葉で素直に謝りました。",
      "is_correct": true
    },
    {
      "text": "自ら言葉ので素直に謝りました。",
      "is_correct": false
    },
    {
      "text": "自ら言葉で素直に謝みました。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：「自らの言葉」とすべきところを「に」を使っており、所有関係が正しく表せていません。 語順・係り受けの誤り：「言葉ので」という不自然な助詞の連続があり、文の構造が破綻しています。 活用・アスペクトの誤り：「謝りました」を「謝みました」と誤って活用させており、動詞の形が間違っています。",
  "target_word": "自ら"
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "しかし、農薬を使わずに野菜を育てるという仕事を通じて、彼は自然の厳しさと、土が命を育むという壮大な仕組みを、自らの肌で実感していくことになります。",
      "is_correct": true
    },
    {
      "text": "私は自らの手で未来を作ります。",
      "is_correct": true
    },
    {
      "text": "変化に適応し、自らの価値を高め続ける姿勢が、これからの職場では強く求められる。",
      "is_correct": true
    },
    {
      "text": "私は自ら手で未来を作ります。",
      "is_correct": false,
      "error_description": "「自ら」は名詞的な働きをする代名詞であり、後ろに続く名詞（手）を修飾する場合は格助詞「の」を入れて「自らの」とするのが正しい構造です。助詞「の」が省略されると、文法的に不自然な誤りとなります。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "自らの行動に責任を持たなければなりません。",
      "is_correct": false,
      "error_description": "「自ら」は代名詞（再帰代名詞）であり、名詞を修飾する場合は「自らの行動」のように助詞「の」を伴うのが正しい形です。副詞的に用いる場合を除き、名詞を直接修飾する際に「の」を省略することはできません。"
    },
    {
      "text": "自らの夢に向かって努力を続けています。",
      "is_correct": true
    },
    {
      "text": "自らの言葉で素直に謝りました。",
      "is_correct": true
    },
    {
      "text": "自らの行動に責任を持たなければなりません。",
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
