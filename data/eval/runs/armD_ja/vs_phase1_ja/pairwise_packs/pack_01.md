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
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___つでも間違えると悔しいです。",
  "original_sentence": "一つでも間違えると悔しいです。",
  "correct_answer": "一",
  "options": [
    "全",
    "多",
    "一",
    "個"
  ],
  "explanation": "「一つでも間違えると」という表現で、最小単位の数を表す「一」が自然に使われています。",
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

#### Pack B
### Level 4 (sense 34998, difficulty None)
**particle_selection** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "答えは必ず一つだけ___なります。",
  "original_sentence": "答えは必ず一つだけになります。",
  "options": [
    "が",
    "へ",
    "で",
    "に"
  ],
  "correct_answer": "に",
  "target_word": "一",
  "error_tags": {
    "が": "topic_vs_subject",
    "で": "instrument",
    "へ": "direction"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "変化の結果としての帰着点・状態を標示する格助詞"
    }
  }
}
```
**particle_selection** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "一つ___も多くの本を読みたいです。",
  "original_sentence": "一つでも多くの本を読みたいです。",
  "options": [
    "で",
    "に",
    "が",
    "を"
  ],
  "correct_answer": "で",
  "target_word": "一",
  "error_tags": {
    "に": "direction",
    "を": "object_marking",
    "が": "topic_vs_subject"
  },
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "数量詞に付いて下限を示し『たとえ～であっても』の意味を作る"
    }
  }
}
```

---

## sense 34998, level 6

#### Pack A
### Level 6 (sense 34998, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "無",
    "二",
    "全",
    "多"
  ],
  "correct_answer": "多",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "数量の「一」に対して、数が多いことを表す「多」は対義関係にある"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "一",
  "relation": "antonym",
  "options": [
    "少",
    "二",
    "多",
    "全"
  ],
  "correct_answer": "多",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "ひとつだけの数。",
      "explanation": "同一語義：数量が一つであることの対義語として、数がおおいことを表す"
    }
  }
}
```

#### Pack B
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "一つでも多くの本を読みたいです。",
      "is_correct": true
    },
    {
      "text": "一つでも間違えると悔しいです。",
      "is_correct": true
    },
    {
      "text": "一つでも多くの本を読みたいあります。",
      "is_correct": false,
      "error_description": "誤り型：活用・アスペクトの誤り。形容詞の連用形「たい」の後に直接「あります」を続けることはできません。願望を表す「たい」は形容詞型活用をし、丁寧語にする場合は「ございます」を用いて「たいございます」とするか、または「たい」と「ます」が融合した「 싶습니다（たいです）」を用いるのが正しい形です。"
    },
    {
      "text": "一つでも多くの経験が大切です。",
      "is_correct": true
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
**phonetic_recognition** variant `B`, tier `T4`
```json
{
  "word": "機械",
  "pronunciation": "きかい",
  "ipa": "[kikai]",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "奇形",
    "機械",
    "きもい",
    "規定"
  ],
  "correct_answer": "機械",
  "explanation": "正解です。「機械」は「電気や動力で動き、人の代わりに仕事をする装置。」という意味です。",
  "distractor_explanations": {
    "きもい": "「きもい」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「も」、一部の音の違い）。",
    "奇形": "「奇形」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「け」、一部の音の違い）。",
    "規定": "「規定」は「機械」と一モーラだけ異なる実在語です（2モーラ目: 「か」→「て」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
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
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "最新の機械が導入されました。",
      "is_correct": true
    },
    {
      "text": "機械が人の代わりに働きます。",
      "is_correct": true
    },
    {
      "text": "従来の肉体労働は減少しますが、機械が操作する専門知識を持つ人材の確保が、新たな課題として浮上しているのです。",
      "is_correct": false,
      "error_description": "「機械を操作する」（機械を対象とする）を「機械が操作する」（機械が主体になる）に誤って変えている。"
    },
    {
      "text": "この機械は壊れていて直せません。",
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
    "発明",
    "判明",
    "別名",
    "発売"
  ],
  "correct_answer": "発明",
  "explanation": "正解です。「発明」は「新しいものや方法を考え出して、実際に作ること。」という意味です。",
  "distractor_explanations": {
    "別名": "「別名」は「発明」と一モーラだけ異なる実在語です（1モーラ目: 「は」→「べ」、一部の音の違い）。",
    "発売": "「発売」は「発明」と一モーラだけ異なる実在語です（3モーラ目: 「め」→「ば」、一部の音の違い）。",
    "判明": "「判明」は「発明」と一モーラだけ異なる実在語です（2モーラ目: 「つ」→「ん」、撥音「ん」の有無）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 35011, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 35011, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "発見",
    "開発",
    "創造",
    "研究"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しいものや方法を考え出して、実際に作ること。",
      "explanation": "すでに存在するものや法則を明らかにすることであり、新しいものを作り出す発明の対義語となる"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "発明",
  "relation": "antonym",
  "options": [
    "創造",
    "発見",
    "開発",
    "改良"
  ],
  "correct_answer": "発見",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "新しいものや方法を考え出して、実際に作ること。",
      "explanation": "すでに存在するものを見つけることで、新しいものを作り出す「発明」と対義の関係にある。"
    }
  }
}
```

---

## sense 35011, level 7

#### Pack A
### Level 7 (sense 35011, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "学校に発明の発表をしました。",
      "is_correct": false,
      "error_description": "動作が行われる場所を表す場合は助詞『で』を使います。『に』は存在場所や到着点を表すため、この文脈では不適切です。"
    },
    {
      "text": "私は新しい発明をしたいです。",
      "is_correct": true
    },
    {
      "text": "彼の発明はすごく便利です。",
      "is_correct": true
    },
    {
      "text": "この発明は世界を変えます。",
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
      "text": "学校で発明の発表をしました。",
      "is_correct": true
    },
    {
      "text": "発明は難しいが楽しいです。",
      "is_correct": true
    },
    {
      "text": "その発明には驚きました。",
      "is_correct": true
    },
    {
      "text": "発明を学校で発表をしました。",
      "is_correct": false,
      "error_description": "「発明を」と「発表をしました」で助詞「を」が重複しています。「発明の発表をしました」または「発明を学校で発表しました」とするのが正しいです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 35011, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "この発明は多くの人に役立っている。",
      "is_correct": true
    },
    {
      "text": "私は新しい発明をしたいです。",
      "is_correct": true
    },
    {
      "text": "彼女はすばらしい発明がした。",
      "is_correct": false,
      "error_description": "動詞「する」の対象を表す「を」を使うべきところを「が」にしている誤り。"
    },
    {
      "text": "彼の発明は世界を変えました。",
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
      "text": "私は毎日発明について考えています。",
      "is_correct": true
    },
    {
      "text": "この発明は生活を変えてくれるでしょう。",
      "is_correct": true
    },
    {
      "text": "素晴らしい発明がここから生まれる。",
      "is_correct": true
    },
    {
      "text": "彼は新しい機械が発明した。",
      "is_correct": false,
      "error_description": "「機械を発明する」の「を」を「が」に誤って変えている（意味が「機械が発明する」に変わってしまう）。"
    }
  ]
}
```

---

## sense 35017, level 1

#### Pack A
### Level 1 (sense 35017, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "/ɸɯeɾɯ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "消える",
    "合える",
    "カエル",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "カエル": "「カエル」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「か」、一部の音の違い）。",
    "消える": "「消える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「き」、一部の音の違い）。",
    "合える": "「合える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「あ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 35017, difficulty None)
**phonetic_recognition** variant `A`, tier `T4`
```json
{
  "word": "増える",
  "pronunciation": "ふえる",
  "ipa": "/ɸɯeɾɯ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "萌える",
    "デュエル",
    "返る",
    "増える"
  ],
  "correct_answer": "増える",
  "explanation": "正解です。「増える」は「数量や程度が多くなる。」という意味です。",
  "distractor_explanations": {
    "萌える": "「萌える」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「も」、一部の音の違い）。",
    "返る": "「返る」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「か」、一部の音の違い）。",
    "デュエル": "「デュエル」は「増える」と一モーラだけ異なる実在語です（1モーラ目: 「ふ」→「でゅ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---
