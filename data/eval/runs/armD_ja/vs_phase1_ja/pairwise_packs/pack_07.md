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


## sense 36181, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 36181, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "近年、精密農業の導入が小規模農家の経営に新たな可能性をもたらしています。",
      "is_correct": true
    },
    {
      "text": "地元の風景を愛するロックバンドが、新たなオリジナルTシャツを製作しました。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新たな創造への移行を意味する重要なプロセスだ。",
      "is_correct": true
    },
    {
      "text": "これは事業の終了ではなく、資本の循環と新た創造への移行を意味する重要なプロセスだ。",
      "is_correct": false,
      "error_description": "「新た」は形状詞であり、名詞を修飾する際には助動詞「な」を付けて「新たな」とする必要がある連語の形です。"
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "それは、確立された安住の地からの離脱であり、新たな社会的文脈における自己の再構築を迫られる、極めて重要な通過儀礼なのである。",
      "is_correct": true
    },
    {
      "text": "しかし現代ファッションの文脈では、この伝統的な職人技はデジタルデザインという新たなパラダイムと衝突し、あるいは融合しつつある。",
      "is_correct": true
    },
    {
      "text": "戦後の都市計画において、ブルータリズムは機能性を重視した新たな住宅様式として普及しました。",
      "is_correct": true
    },
    {
      "text": "しかし現代ファッションの文脈では、この伝統的な職人技はデジタルデザインという新ただパラダイムと衝突し、あるいは融合しつつある。",
      "is_correct": false,
      "error_description": "活用：名詞の前では連体形「新たな」を使う。「新ただ」は誤り。"
    }
  ]
}
```

---

## sense 36191, level 1

#### Pack A
### Level 1 (sense 36191, difficulty None)
**phonetic_recognition** variant `B`, tier `T4`
```json
{
  "word": "見る",
  "pronunciation": "みる",
  "ipa": "/miɾu/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "見る",
    "Ｌ",
    "ブル",
    "擂る"
  ],
  "correct_answer": "見る",
  "explanation": "正解です。「見る」は「目で物の存在や様子を確かめる。」という意味です。",
  "distractor_explanations": {
    "Ｌ": "「Ｌ」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「え」、一部の音の違い）。",
    "ブル": "「ブル」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「ぶ」、一部の音の違い）。",
    "擂る": "「擂る」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「す」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

#### Pack B
### Level 1 (sense 36191, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "見る",
  "pronunciation": "みる",
  "ipa": "/miɾɯ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "猟る",
    "見る",
    "マル",
    "神子"
  ],
  "correct_answer": "見る",
  "explanation": "正解です。「見る」は「目で物の存在や様子を確かめる。」という意味です。",
  "distractor_explanations": {
    "猟る": "「猟る」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「か」、一部の音の違い）。",
    "マル": "「マル」は「見る」と一モーラだけ異なる実在語です（1モーラ目: 「み」→「ま」、一部の音の違い）。",
    "神子": "「神子」は「見る」と一モーラだけ異なる実在語です（2モーラ目: 「る」→「こ」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

## sense 36191, level 3

#### Pack A
### Level 3 (sense 36191, difficulty None)
**cloze_completion** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "彼が描いたのは、私たちがよく___る商店街の風景でした。",
  "original_sentence": "彼が描いたのは、私たちがよく見る商店街の風景でした。",
  "correct_answer": "見",
  "options": [
    "見",
    "聞き",
    "書き",
    "食べ"
  ],
  "explanation": "正解です。文脈に自然に合う対象語の表記です。",
  "distractor_tags": {},
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```

#### Pack B
### Level 3 (sense 36191, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "彼が描いたのは、実際に自分の目で___た商店街の風景でした。",
  "original_sentence": "彼が描いたのは、実際に自分の目で見た商店街の風景でした。",
  "correct_answer": "見",
  "options": [
    "感じ",
    "見",
    "聞",
    "読"
  ],
  "explanation": "正解です。視覚によって風景を確認する文脈に合致します。",
  "distractor_tags": {},
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見"
}
```

---

## sense 36191, level 4

#### Pack A
### Level 4 (sense 36191, difficulty None)
**morphology_slot** variant `A`, tier `T4`
```json
{
  "sentence_with_blank": "実際に農村の風景を___と、労働需要の質が変化したことがよく分かります。",
  "original_sentence": "実際に農村の風景を見ると、労働需要の質が変化したことがよく分かります。",
  "correct_answer": "見る",
  "base_form": "見",
  "form_label": "辞書形",
  "options": [
    "見て",
    "見た",
    "見る",
    "見ない"
  ],
  "explanation": "条件を表す格助詞「と」は動詞の辞書形に接続します",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```
**morphology_slot** variant `B`, tier `T4`
```json
{
  "sentence_with_blank": "私は週末に窓の外を___ことができます。",
  "original_sentence": "私は週末に窓の外を見ることができます。",
  "correct_answer": "見る",
  "base_form": "見る",
  "form_label": "辞書形",
  "options": [
    "見て",
    "見た",
    "見る",
    "見ない"
  ],
  "explanation": "「～ことができる」の形式には動詞の辞書形が接続します。",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```

#### Pack B
### Level 4 (sense 36191, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "一方で、農村の実際の街並みを自分の目で___と、労働需要の質が変化していることがよく分かります。",
  "original_sentence": "一方で、農村の実際の街並みを自分の目で見ると、労働需要の質が変化していることがよく分かります。",
  "correct_answer": "見る",
  "base_form": "見る",
  "form_label": "辞書形（連体形）",
  "options": [
    "見れば",
    "見る",
    "見よう",
    "見て"
  ],
  "explanation": "名詞化の「の」の前は連体形（辞書形）が必要で、「見る」が文法的に成立する",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "この映画は___ことができません。",
  "original_sentence": "この映画は見ることができません。",
  "correct_answer": "見る",
  "base_form": "見る",
  "form_label": "辞書形",
  "options": [
    "見ます",
    "見",
    "見て",
    "見る"
  ],
  "explanation": "名詞「こと」に接続するには辞書形が必要です。",
  "word_definition": "目で物の存在や様子を確かめる。",
  "target_word": "見る"
}
```

---

## sense 36191, level 6

#### Pack A
### Level 6 (sense 36191, difficulty None)
**synonym_antonym_match** variant `A`, tier `T4`
```json
{
  "word": "見",
  "relation": "antonym",
  "options": [
    "隠す",
    "触る",
    "忘れる",
    "聞く"
  ],
  "correct_answer": "隠す",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "目で物の存在や様子を確かめる。",
      "explanation": "対象を見えないようにする点で、目で確かめることの対義語となる"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T4`
```json
{
  "word": "見",
  "relation": "antonym",
  "options": [
    "聞く",
    "隠す",
    "触る",
    "忘れる"
  ],
  "correct_answer": "隠す",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "目で物の存在や様子を確かめる。",
      "explanation": "対象を人目から遠ざける意味で、目で確かめる「見る」の対義語となる"
    }
  }
}
```

#### Pack B
### Level 6 (sense 36191, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "テレビにニュースを見ています。",
      "is_correct": false
    },
    {
      "text": "テレビでニュースを見ています。",
      "is_correct": true
    },
    {
      "text": "見ていますテレビでニュースを。",
      "is_correct": false
    },
    {
      "text": "テレビでニュースを見っています。",
      "is_correct": false
    }
  ],
  "explanation": "助詞の混同：手段や場所を表す場合は「で」を使います。「に」は誤りです。 活用の誤り：動詞「見る」のて形は「見て」です。「見って」は存在しません。 語順の誤り：日本語の基本的な語順は「場所＋目的語＋動詞」です。動詞が文頭に来る語順は不自然です。",
  "target_word": "見て"
}
```

---

## sense 36191, level 7

#### Pack A
### Level 7 (sense 36191, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "彼が描いたのは、実際に自分の目で見た商店街の風景でした。",
      "is_correct": true
    },
    {
      "text": "姉は毎晩ニュースに見ます。",
      "is_correct": false,
      "error_description": "助詞の混同（を／に）：「見る」は見る対象を「を」で示すので、「ニュースに見ます」ではなく「ニュースを見ます」が正しい。"
    },
    {
      "text": "一方で、農村の実際の街並みを自分の目で見ると、労働需要の質が変化していることがよく分かります。",
      "is_correct": true
    },
    {
      "text": "友達の顔をみて、安心しました。",
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
      "text": "先生が黒板を見るのをやめました。",
      "is_correct": true
    },
    {
      "text": "この映画は見ることができません。",
      "is_correct": true
    },
    {
      "text": "道を渡る時は左右を見てください。",
      "is_correct": true
    },
    {
      "text": "道を渡る時は左右に見てください。",
      "is_correct": false,
      "error_description": "「見る」の目的語を示す助詞は「を」です。「に」は誤りです。"
    }
  ]
}
```

#### Pack B
### Level 7 (sense 36191, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T4`
```json
{
  "sentences": [
    {
      "text": "私は週末に窓の外に見ることができます。",
      "is_correct": false,
      "error_description": "「見る」の目的語を示す助詞は「を」です。「に」は方向や対象を示しますが、他動詞「見る」の直接的な目的語には「を」を使います。"
    },
    {
      "text": "私は週末に窓の外を見ることができます。",
      "is_correct": true
    },
    {
      "text": "あの人は人の心を見るのがとても上手です。",
      "is_correct": true
    },
    {
      "text": "私は毎日、窓の外を見ます。",
      "is_correct": true
    }
  ]
}
```

---

## sense 38099, level 1

#### Pack A
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

#### Pack B
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
    "昇華",
    "工科",
    "小誌",
    "道家"
  ],
  "correct_answer": "昇華",
  "explanation": "正解です。「昇華」は「物事が、より高い価値や状態に変わること。気持ちが深まることにも使います。」という意味です。",
  "distractor_explanations": {
    "道家": "「道家」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「ど」、一部の音の違い）。",
    "工科": "「工科」は「昇華」と一モーラだけ異なる実在語です（1モーラ目: 「しょ」→「こ」、一部の音の違い）。",
    "小誌": "「小誌」は「昇華」と一モーラだけ異なる実在語です（3モーラ目: 「か」→「し」、一部の音の違い）。"
  },
  "distractor_source": "phonetic_trie"
}
```

---

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
    "変遷",
    "昇華",
    "変化",
    "転換"
  ],
  "explanation": "正解です。自然の産物が人間の手によって恒久の美という「より高い価値や状態」に変わっているため、文脈に合致します。",
  "distractor_tags": {},
  "word_definition": "物事が、より高い価値や状態に変わること。気持ちが深まることにも使います。",
  "target_word": "昇華"
}
```
**cloze_completion** variant `B`, tier `T5`
```json
{
  "sentence_with_blank": "個人が抱える深い悲しみは、長い時間を経て、やがて他者への静かな慈愛へと___されるのである。",
  "original_sentence": "個人が抱える深い悲しみは、長い時間を経て、やがて他者への静かな慈愛へと昇華されるのである。",
  "correct_answer": "昇華",
  "options": [
    "転換",
    "昇進",
    "昇華",
    "変遷"
  ],
  "explanation": "正解です。悲しみや怒りなどの感情が、時間や表現活動を経て、より高い価値や慈愛へと変わることを表します。",
  "distractor_tags": {},
  "word_definition": "物事が、より高い価値や状態に変わること。気持ちが深まることにも使います。",
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
**synonym_antonym_match** variant `A`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "antonym",
  "options": [
    "退化",
    "向上",
    "転換",
    "深化"
  ],
  "correct_answer": "退化",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事が、より高い価値や状態に変わること。気持ちが深まることにも使います。",
      "explanation": "事物がより低級で劣った状態へ変わることを指し、より高い価値へ変わる「昇華」の対義語となる。"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T5`
```json
{
  "word": "昇華",
  "relation": "antonym",
  "options": [
    "深化",
    "進化",
    "堕落",
    "変遷"
  ],
  "correct_answer": "堕落",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "物事が、より高い価値や状態に変わること。気持ちが深まることにも使います。",
      "explanation": "精神や価値が低い状態へ落ちる点で、高い状態へ変わる昇華の対義語となる"
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

## sense 39187, level 1

#### Pack A
### Level 1 (sense 39187, difficulty None)
**phonetic_recognition** variant `B`, tier `T5`
```json
{
  "word": "自ら",
  "pronunciation": "みずから",
  "ipa": "/mizukara/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "水替え",
    "水換え",
    "自ら",
    "水カビ"
  ],
  "correct_answer": "自ら",
  "explanation": "正解です。「自ら」は「自分自身を指す言葉。」という意味です。",
  "distractor_explanations": {
    "水換え": "「水換え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。",
    "水カビ": "「水カビ」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「び」、一部の音の違い）。",
    "水替え": "「水替え」は「自ら」と一モーラだけ異なる実在語です（4モーラ目: 「ら」→「え」、一部の音の違い）。"
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
