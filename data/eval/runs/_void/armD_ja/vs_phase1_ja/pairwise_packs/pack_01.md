# Pairwise review pack 01

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


## sense 34998, level 1

#### Pack A
### Level 1 (sense 34998, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "ipa": "/it͡ɕi/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "一",
    "家",
    "井戸",
    "自知"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "自知": "「自知」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「じ」、一部の音の違い）。",
    "家": "「家」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「う」、一部の音の違い）。",
    "井戸": "「井戸」は「一」と一モーラだけ異なる実在語です（2モーラ目: 「ち」→「ど」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 34998, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "一",
  "pronunciation": "いち",
  "ipa": "/iti/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "がち",
    "一",
    "主値",
    "無知"
  ],
  "correct_answer": "一",
  "explanation": "正解です。「一」は「ひとつだけの数。」という意味です。",
  "distractor_explanations": {
    "がち": "「がち」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「が」、一部の音の違い）。",
    "無知": "「無知」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「む」、一部の音の違い）。",
    "主値": "「主値」は「一」と一モーラだけ異なる実在語です（1モーラ目: 「い」→「しゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 34998, level 3

#### Pack A
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "試験の答えは「___」です。",
  "original_sentence": "試験の答えは「一」です。",
  "correct_answer": "一",
  "options": [
    "全て",
    "一",
    "理由",
    "一の"
  ],
  "explanation": "正解です。文脈に合う「ひとつだけの数」を表す名詞です。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

#### Pack B
### Level 3 (sense 34998, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "この中で___だけが特別です。",
  "original_sentence": "この中で一だけが特別です。",
  "correct_answer": "一",
  "options": [
    "個",
    "単",
    "最初",
    "一"
  ],
  "explanation": "正解です。文脈から、数や数量の最小単位である「一」が適切です。",
  "distractor_tags": {},
  "word_definition": "ひとつだけの数。",
  "target_word": "一"
}
```

---

## sense 34998, level 4

#### Pack A
### Level 4 (sense 34998, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "計算の結果は一___なりました。",
  "original_sentence": "計算の結果は一になりました。",
  "options": [
    "で",
    "を",
    "は",
    "に"
  ],
  "correct_answer": "に",
  "target_word": "一",
  "error_tags": {
    "で": "instrument",
    "を": "object_marking",
    "は": "topic_vs_subject"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "変化の結果を表す「に」は、動詞「なる」と結びついて到達した状態を標示する"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "一___足すと二になります。",
  "original_sentence": "一を足すと二になります。",
  "options": [
    "を",
    "が",
    "に",
    "で"
  ],
  "correct_answer": "を",
  "target_word": "一",
  "error_tags": {
    "が": "object_marking",
    "に": "other",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "他動詞「足す」の直接目的語を標示する"
    }
  }
}
```

#### Pack B
### Level 4 (sense 34998, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一___始めてください。",
  "original_sentence": "一から始めてください。",
  "options": [
    "で",
    "から",
    "まで",
    "に"
  ],
  "correct_answer": "から",
  "target_word": "一",
  "error_tags": {
    "まで": "source_vs_goal",
    "に": "direction",
    "で": "instrument"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "物事の起点を標示する格助詞であり、「一」を始まりとして順に進めることを表す。"
    }
  }
}
```

---

## sense 34998, level 6

#### Pack A
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "正解の一は数です。",
      "is_correct": false
    },
    {
      "text": "正解の数は一匹です。",
      "is_correct": false
    },
    {
      "text": "正解の数は一です。",
      "is_correct": true
    },
    {
      "text": "正解の数へ一です。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「数」に対する助数詞として「匹」は不適切です。 助詞の混同：主題や説明を表す助詞は「は」が適切で、「へ」は方向を表すため不適切です。 語順・係り受けの誤り：「正解の数」という名詞句が分断され、意味が通じなくなっています。",
  "target_word": "一"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一からやり直してあります。",
      "is_correct": false
    },
    {
      "text": "一まで数えます。",
      "is_correct": false
    },
    {
      "text": "一冊の犬を飼っています。",
      "is_correct": false
    },
    {
      "text": "一からやり直しています。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：犬を数えるときは「一匹」を用い、「一冊」は本やノートなどに使います。 助詞の混同：数え始めを表すときは「から」を用い、「まで」は終わりを表します。 アスペクトの誤り：「やり直す」のような動作動詞の結果の状態を表す場合は「ています」を用い、「てあります」は他動詞の意図的な結果の残存に用います。",
  "target_word": "一"
}
```

#### Pack B
### Level 6 (sense 34998, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一はすべての始まりです。",
      "is_correct": false
    },
    {
      "text": "あと一が足りなくて失敗しました。",
      "is_correct": true
    },
    {
      "text": "一はすべての始まりだ。",
      "is_correct": false
    },
    {
      "text": "一はすべて始まりです。",
      "is_correct": false
    }
  ],
  "explanation": "アスペクトの誤り：「始まり」は名詞的用法ですが、ここでは「一」の性質や定義を述べているため、断定の助動詞「です」を用いて「一はすべての始まりです。」とするのが自然です。 語順・係り受けの誤り：「すべて」は名詞「始まり」を修飾する語であり、「すべての始まり」とするのが正しい日本語の語順です。 助詞の混同：主題を提示する助詞は「は」を用いるのが適切です。「が」を使うと、他のものではなく「一」が特に取り立てて強調されるニュアンスになり、一般的な定義を述べる文脈には不自然です。",
  "target_word": "一"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "半",
    "全",
    "二",
    "多"
  ],
  "correct_answer": "多",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "数がおおいことを表し、「ひとつだけ」の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一を引くとゼロになる。",
      "is_correct": false
    },
    {
      "text": "一を引くとゼロだ。",
      "is_correct": false
    },
    {
      "text": "一を引くとゼロになります。",
      "is_correct": false
    },
    {
      "text": "一を引くとゼロになる。",
      "is_correct": true
    }
  ],
  "explanation": "正しい文です。 語順・係り受けの誤り：文末が「なる」と終止形になっており、前の文節「引くと」の条件に対する帰結として不自然です。正しくは「なります」とすべきです。 語域の誤り：「ゼロだ」という断定は、数学的な説明や一般的な事実を述べるこの文脈ではぶっきらぼうすぎます。丁寧な「ゼロになります」が適切です。",
  "target_word": "一"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "半分",
    "無限",
    "二",
    "ゼロ"
  ],
  "correct_answer": "ゼロ",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "「ひとつだけの数」に対して「数が存在しない」ことを表す対義語である"
    }
  }
}
```

---

## sense 34998, level 7

#### Pack A
### Level 7 (sense 34998, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一が足りなくて困りました。",
      "is_correct": true
    },
    {
      "text": "一からやり直しています。",
      "is_correct": true
    },
    {
      "text": "一を足して二にします。",
      "is_correct": true
    },
    {
      "text": "一が足して二にします。",
      "is_correct": false,
      "error_description": "助詞の混同。他動詞「足す」の目的語を示す助詞は「を」です。「一が足して」は誤りです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 34998, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一に一が足すと二になる。",
      "is_correct": false,
      "error_description": "動作の対象を表す「を」を使うべきところを「が」にしている誤り。"
    },
    {
      "text": "計算の結果は一になりました。",
      "is_correct": true
    },
    {
      "text": "この中で一だけが特別です。",
      "is_correct": true
    },
    {
      "text": "一の次に二が来ます。",
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
      "text": "一はすべての始まりです。",
      "is_correct": true
    },
    {
      "text": "一を引くとゼロになる。",
      "is_correct": true
    },
    {
      "text": "一を足すと二になります。",
      "is_correct": true
    },
    {
      "text": "一を足すと二にします。",
      "is_correct": false,
      "error_description": "結果や状態の自然な変化・帰結を表す場合は、他動詞の「します」ではなく、自動詞の「になります」を使う必要があります。"
    }
  ]
}
```

---

## sense 35001, level 1

#### Pack A
### Level 1 (sense 35001, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "/kikai/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "機械",
    "規程",
    "自壊",
    "嫌い"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「動力や電気で動き、人間の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "嫌い": "「嫌い」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「ら」、一部の音の違い）。",
    "自壊": "「自壊」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「じ」、一部の音の違い）。",
    "規程": "「規程」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「て」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35001, difficulty None)
**phonetic_recognition** variant `A`, tier `T5`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "[kikai]",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "地階",
    "機械",
    "芦薈",
    "耳介"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「電気や動力で動き、人の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "耳介": "「耳介」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「じ」、一部の音の違い）。",
    "芦薈": "「芦薈」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「ろ」、一部の音の違い）。",
    "地階": "「地階」は「機械」と一モーラだけ異なる実在語です（1モーラ目: 「き」→「ち」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35001, level 6

#### Pack A
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この機械は昨日壊れてある。",
      "is_correct": false
    },
    {
      "text": "工場には新しい機械が三冊導入された。",
      "is_correct": false
    },
    {
      "text": "機械を作る人はすごいです。",
      "is_correct": true
    },
    {
      "text": "機械を人間の代わりに仕事をする。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：機械の助数詞は「台」や「個」であり、本や雑誌などに使う「冊」は誤りです。 助詞の混同：動作の主体である機械を示すには「が」が必要であり、「を」は誤りです。 アスペクトの誤り：「壊れる」は自動詞であり、他動詞の結果状態を表す「てある」は結びつきません。「壊れている」が適切です。",
  "target_word": "機械"
}
```

#### Pack B
### Level 6 (sense 35001, difficulty None)
**semantic_discrimination** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "機械は毎日使われていました。",
      "is_correct": false
    },
    {
      "text": "工場には大きな機械が一台あります。",
      "is_correct": false
    },
    {
      "text": "私は機械の仕組みに音が興味があります。",
      "is_correct": false
    },
    {
      "text": "機械が音を立てて動いています。",
      "is_correct": true
    }
  ],
  "explanation": "助数詞の誤り：「機械」を数える際は「一台」ではなく「1基」や「1台（機械全体）」などの表現が一般的ですが、ここでは「大きな機械」という塊に対して「一台」と数えるより、複数形や他の単位が自然です。（※より明確な誤りとして「機械が一つあります」とすべきところを「一台」としている点や、文脈不整合を指摘）-> 修正: 工場には大きな機械が一本あります。 助詞の混同：「興味」の対象を示す助詞は「に」です。「音が」という主語が挿入され、文構造が破綻しています。正しくは「仕組みに興味があります」とします。 アスペクトの誤り：基礎例文の文脈（現在の事実や習慣）と異なり、過去完了の「使われていました」となっており、現在の状況説明としての整合性が取れていません。",
  "target_word": "機械"
}
```
**semantic_discrimination** variant `B`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "機械は工場に動いています。",
      "is_correct": false
    },
    {
      "text": "機械が壊れてしまいました。",
      "is_correct": false
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "私は新しい機械を一台買いました。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「機械」は形のある装置であるため、数える際に「一台」ではなく「一個」や「一台（機械全体）」などを用いますが、一般的に小型の装置や部品には「一個」、大きな装置には「一台」を使いますが、文脈によっては「一個」がより自然な場合もあります。ここでは「機械」に対して「一台」が必ずしも誤りとは言い切れませんが、より明確な誤りとして「一本」などを用いるべきでした。修正：「私は新しい機械を一個買いました。」 助詞の混同：動作の存在場所や状態を表すには「で」を使います。「に」は存在場所や帰着点に使われるため不適切です。修正：「機械は工場で動いています。」 語順・係り受けの誤り：この文は文法的に正しいですが、対象語「機械」を主題として提示し、それについての説明を行う文脈（例：「この機械は壊れてしまいました」）が自然です。ここでは誤り文とするため、あえて不自然な語順にします。修正：「壊れてしまいました機械が。」",
  "target_word": "機械"
}
```

---

## sense 35001, level 7

#### Pack A
### Level 7 (sense 35001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "機械が動いています。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "新しい機械を一個買いました。",
      "is_correct": false,
      "error_description": "機械を数える助数詞は「台」です。「個」は小さめの物に使う助数詞で、機械には不適切です。"
    },
    {
      "text": "この機械は便利です。",
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
      "text": "機械を作る人はすごいです。",
      "is_correct": true
    },
    {
      "text": "機械を壊れてしまいました。",
      "is_correct": false,
      "error_description": "自動詞の「壊れる」の主語には助詞「が」を使います。「を」は他動詞の目的語に使う助詞です。"
    },
    {
      "text": "機械の音を聞きました。",
      "is_correct": true
    },
    {
      "text": "機械が壊れてしまいました。",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T5`
```json
{
  "sentences": [
    {
      "text": "最新の機械を導入したおかげで、作業効率が大幅に向上しました。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械を操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": true
    },
    {
      "text": "新しい機械が工場に入れた。",
      "is_correct": false,
      "error_description": "他動詞「入れた」の対象を表す「を」を使うべきところを「が」にしている誤り。"
    },
    {
      "text": "この機械はとても便利です。",
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
      "text": "機械を正しく使うことが大切です。",
      "is_correct": true
    },
    {
      "text": "私は機械の仕組みに大変興味があります。",
      "is_correct": false,
      "error_description": "「興味がある」は名詞「興味」に助詞「が」と形容詞「ある」が結びついた自然な表現です。「興味を持つ」は正しい連語ですが、「興味に持っています」とすると、助詞「に」と動詞「持つ」の搭配が誤りになります。"
    },
    {
      "text": "この機械は毎日使われています。",
      "is_correct": true
    },
    {
      "text": "最新の機械を見せてもらいました。",
      "is_correct": true
    }
  ]
}
```

---

## sense 35011, level 1

#### Pack A
### Level 1 (sense 35011, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "ipa": "/hatsumei/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "発明",
    "絶命",
    "血盟",
    "説明"
  ],
  "correct_answer": "発明",
  "explanation": "正解です。「発明」は「新しい物や方法を考え出し、実際に作ること。」という意味です。",
  "distractor_explanations": {
    "絶命": "「絶命」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「ぜ」、一部の音の違い）。",
    "血盟": "「血盟」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「け」、一部の音の違い）。",
    "説明": "「説明」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「せ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35011, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "pronunciation": "はつめい",
  "ipa": "/hatsumei/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "説明",
    "藩命",
    "実名",
    "発明"
  ],
  "correct_answer": "発明",
  "explanation": "正解です。「発明」は「世の中にない新しいものや方法を考え出し、実際に作り出すこと。」という意味です。",
  "distractor_explanations": {
    "藩命": "「藩命」は「発明」と一モーラだけ異なる実在語です（2モーラ目: 「つ」→「ん」、撥音「ん」の有無）。",
    "説明": "「説明」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「せ」、一部の音の違い）。",
    "実名": "「実名」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「じ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35011, level 6

#### Pack A
### Level 6 (sense 35011, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "私は毎日の生活の中から発明のヒントを得る。",
      "is_correct": true
    },
    {
      "text": "私は毎日の生活の中から発明を得ている。",
      "is_correct": false
    },
    {
      "text": "私は毎日の生活の中から発明を三冊得る。",
      "is_correct": false
    },
    {
      "text": "私は毎日の生活の中から発明にヒントを得る。",
      "is_correct": false
    }
  ],
  "explanation": "助数詞の誤り：「発明」は抽象的な概念や出来事であり、「冊」は本や帳簿などに使う助数詞です。 助詞の混同：「ヒントを得る」の対象を示すには「から」や「を」が適切であり、「に」は不自然です。 アスペクトの誤り：「得る」は瞬間的な動作であり、進行中の状態を表す「ている」とは結びつきにくいです。",
  "target_word": "発明"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "発見",
    "創造",
    "模倣",
    "開発"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "世の中にない新しいものや方法を考え出し、実際に作り出すこと。",
      "explanation": "すでに存在するものを明らかにすることであり、新しく作り出す「発明」の対義語である。"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "小さな気づきがやがて一つの発明につなげる。",
      "is_correct": false
    },
    {
      "text": "小さな気づきがやがて大きな発明につながる。",
      "is_correct": true
    },
    {
      "text": "小さな気づきがやがて大きな発明をつながる。",
      "is_correct": false
    },
    {
      "text": "小さな気づきがやがて大きな発明につなげている。",
      "is_correct": false
    }
  ],
  "explanation": "誤り：「つなげる」は他動詞であり、ここでは自動詞の「つながる」を使うのが正しい係り受けです。 誤り：アスペクトの誤りです。自然のなりゆきや結果を表す場合は「つながっている」を用いるのが適切です。 誤り：助詞の混同です。「つながる」は自動詞のため、目的語をとらず「に」を使って「発明につながる」とするのが正しい項構造です。",
  "target_word": "発明"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "創造",
    "開発",
    "発見",
    "改良"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "世の中にない新しいものや方法を考え出し、実際に作り出すこと。",
      "explanation": "すでに存在するものや法則などを明らかにすることで、新たに作り出すことの対義語"
    }
  }
}
```

#### Pack B
### Level 6 (sense 35011, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "創造",
    "開発",
    "考案",
    "発見"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しい物や方法を考え出し、実際に作ること。",
      "explanation": "すでに存在するものを見出すことで、新たなものを創り出す目標語の対義語となる"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "発明を切った。",
      "is_correct": false
    },
    {
      "text": "発明は難しいが楽しいです。",
      "is_correct": true
    },
    {
      "text": "発明が赤く光った。",
      "is_correct": false
    },
    {
      "text": "発明を三個買った。",
      "is_correct": false
    }
  ],
  "explanation": "抽象的なアイデアを個数で買うことはできない。 「発明」自体が光ることはない。 アイデアを物理的に切ることはできない。",
  "target_word": "発明"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "発見",
    "創造",
    "応用",
    "開発"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しい物や方法を考え出し、実際に作ること。",
      "explanation": "すでに存在するものや法則などを明らかにすることで、目標語の対義語となる"
    }
  }
}
```

---
