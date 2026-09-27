# Pairwise review pack 09

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


## sense 14189, level 4

#### Pack A
### Level 4 (sense 14189, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "input_mode": "text"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "required_pos": "adverb",
  "options": [
    "technologial",
    "technologicness",
    "technologically",
    "technologyment"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way that relates to technology'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "input_mode": "text"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "required_pos": "adverb",
  "options": [
    "technologically",
    "technologal",
    "technologment",
    "technologful"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way related to technology'"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14189, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "input_mode": "text"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "required_pos": "adverb",
  "options": [
    "technologial",
    "technologicness",
    "technologically",
    "technologyment"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way that relates to technology'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "input_mode": "text"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "technology",
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "required_pos": "adverb",
  "options": [
    "technologically",
    "technologal",
    "technologment",
    "technologful"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way related to technology'"
    }
  }
}
```

---

## sense 14189, level 6

#### Pack A
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The river flows technologically through the valley every spring.",
      "is_correct": false
    },
    {
      "text": "She smiled technologically at her friend across the room.",
      "is_correct": false
    },
    {
      "text": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
      "is_correct": true
    },
    {
      "text": "Technologically, the chef added more salt to balance the flavors of the dish.",
      "is_correct": false
    }
  ],
  "explanation": "Misuse: seasoning and cooking technique are unrelated to technology, so the adverb doesn't fit the action. Misuse: smiling is an emotional/physical expression, not something that can be described in terms of technology. Misuse: a river's natural flow is a geological/natural process, not related to technology or machinery.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "scientifically",
    "digitally",
    "electronically",
    "traditionally"
  ],
  "correct_answer": "traditionally",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: describes doing something in an old, established way without modern technology"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather turned technologically rainy overnight.",
      "is_correct": false
    },
    {
      "text": "The city aims to become more technologically efficient in managing public transport.",
      "is_correct": true
    },
    {
      "text": "She felt technologically sad after the funeral.",
      "is_correct": false
    },
    {
      "text": "The soup was technologically delicious, according to the chef.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: taste and flavor are not properties that can be described as technological. Semantically inappropriate: emotions like sadness are not related to technology or machinery. Semantically inappropriate: weather conditions are natural phenomena, not something that can be 'technological'.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "digitally",
    "manually",
    "efficiently",
    "scientifically"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand without machines or technology"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The river flows technologically through the valley every spring.",
      "is_correct": false
    },
    {
      "text": "She smiled technologically at her friend across the room.",
      "is_correct": false
    },
    {
      "text": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
      "is_correct": true
    },
    {
      "text": "Technologically, the chef added more salt to balance the flavors of the dish.",
      "is_correct": false
    }
  ],
  "explanation": "Misuse: seasoning and cooking technique are unrelated to technology, so the adverb doesn't fit the action. Misuse: smiling is an emotional/physical expression, not something that can be described in terms of technology. Misuse: a river's natural flow is a geological/natural process, not related to technology or machinery.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "scientifically",
    "digitally",
    "electronically",
    "traditionally"
  ],
  "correct_answer": "traditionally",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: describes doing something in an old, established way without modern technology"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather turned technologically rainy overnight.",
      "is_correct": false
    },
    {
      "text": "The city aims to become more technologically efficient in managing public transport.",
      "is_correct": true
    },
    {
      "text": "She felt technologically sad after the funeral.",
      "is_correct": false
    },
    {
      "text": "The soup was technologically delicious, according to the chef.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: taste and flavor are not properties that can be described as technological. Semantically inappropriate: emotions like sadness are not related to technology or machinery. Semantically inappropriate: weather conditions are natural phenomena, not something that can be 'technological'.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "digitally",
    "manually",
    "efficiently",
    "scientifically"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand without machines or technology"
    }
  }
}
```

---

## sense 14189, level 9

#### Pack A
### Level 9 (sense 14189, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly.",
  "chunks": [
    "Many teenagers",
    "today",
    "are",
    "technologically savvy",
    "and learn new software very quickly"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "today",
    "technologically savvy",
    "are",
    "Many teenagers",
    "and learn new software very quickly"
  ],
  "target_word": "technologically",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
  "chunks": [
    "Technologically speaking",
    "this new smartphone",
    "is",
    "a major upgrade from the previous model"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "a major upgrade from the previous model",
    "is",
    "Technologically speaking",
    "this new smartphone"
  ],
  "target_word": "technologically",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14189, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly.",
  "chunks": [
    "Many teenagers",
    "today",
    "are",
    "technologically savvy",
    "and learn new software very quickly"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "today",
    "technologically savvy",
    "are",
    "Many teenagers",
    "and learn new software very quickly"
  ],
  "target_word": "technologically",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
  "chunks": [
    "Technologically speaking",
    "this new smartphone",
    "is",
    "a major upgrade from the previous model"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "a major upgrade from the previous model",
    "is",
    "Technologically speaking",
    "this new smartphone"
  ],
  "target_word": "technologically",
  "chunk_count": 4
}
```

---

## sense 14390, level 2

#### Pack A
### Level 2 (sense 14390, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "correct_definition": "To a very great degree or extent.",
  "options": [
    "A garage is a building or part of a building where a car or other vehicle is kept.",
    "To a very great degree or extent.",
    "All the people living together in a single residence.",
    "to become a member of a group or to go to someone so that you are together"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To a very great degree or extent.",
        "Involving three groups or parts.",
        "The state of being simple, not complicated.",
        "The ability to use your eyes and hands together in a coordinated way, especially for tasks like catching, throwing, or writing."
      ],
      "correct_answer": "To a very great degree or extent."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14390, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "correct_definition": "To a very great degree or extent.",
  "options": [
    "A garage is a building or part of a building where a car or other vehicle is kept.",
    "To a very great degree or extent.",
    "All the people living together in a single residence.",
    "to become a member of a group or to go to someone so that you are together"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To a very great degree or extent.",
        "Involving three groups or parts.",
        "The state of being simple, not complicated.",
        "The ability to use your eyes and hands together in a coordinated way, especially for tasks like catching, throwing, or writing."
      ],
      "correct_answer": "To a very great degree or extent."
    }
  }
}
```

---

## sense 14390, level 3

#### Pack A
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "rarely",
    "enormously",
    "loudly"
  ],
  "explanation": "Correctly conveys that coffee preparation varies to a very great degree across cultures, matching the examples that follow.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He felt ___ relieved when he finally found his lost backpack on the school bus.",
  "original_sentence": "He felt enormously relieved when he finally found his lost backpack on the school bus.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "hardly",
    "enormously",
    "rarely"
  ],
  "explanation": "Correctly conveys that he felt relieved to a very great degree after finding his lost backpack.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "rarely",
    "enormously",
    "loudly"
  ],
  "explanation": "Correctly conveys that coffee preparation varies to a very great degree across cultures, matching the examples that follow.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He felt ___ relieved when he finally found his lost backpack on the school bus.",
  "original_sentence": "He felt enormously relieved when he finally found his lost backpack on the school bus.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "hardly",
    "enormously",
    "rarely"
  ],
  "explanation": "Correctly conveys that he felt relieved to a very great degree after finding his lost backpack.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 4

#### Pack A
### Level 4 (sense 14390, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
  "input_mode": "text"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "enormous",
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "required_pos": "adverb",
  "options": [
    "enormousity",
    "enormously",
    "enormousive",
    "enormousment"
  ],
  "correct_answer": "enormously",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverb formed by adding -ly to the adjective"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Interest in environmental clubs has risen ___ among students concerned about climate change.",
  "original_sentence": "Interest in environmental clubs has risen enormously among students concerned about climate change.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
  "input_mode": "text"
}
```

#### Pack B
### Level 4 (sense 14390, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
  "input_mode": "text"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "enormous",
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "required_pos": "adverb",
  "options": [
    "enormousity",
    "enormously",
    "enormousive",
    "enormousment"
  ],
  "correct_answer": "enormously",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverb formed by adding -ly to the adjective"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Interest in environmental clubs has risen ___ among students concerned about climate change.",
  "original_sentence": "Interest in environmental clubs has risen enormously among students concerned about climate change.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
  "input_mode": "text"
}
```

---

## sense 14390, level 6

#### Pack A
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Enormously talented young musicians performed at the annual youth festival last weekend.",
      "is_correct": true
    },
    {
      "text": "She enormously agreed with the plan before leaving early.",
      "is_correct": false
    },
    {
      "text": "He arrived enormously on time for the meeting.",
      "is_correct": false
    },
    {
      "text": "The tiny kitten was enormously small, hiding behind the cushion.",
      "is_correct": false
    }
  ],
  "explanation": "Contradictory: 'enormously' signals a very great degree, which conflicts logically with 'small'. Pragmatically odd: 'agree' is a binary, non-gradable action, so it cannot be intensified by a degree adverb like 'enormously'. Pragmatically odd: 'on time' is not a gradable state, so modifying it with 'enormously' doesn't make sensible use of the degree meaning.",
  "target_word": "Enormously"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The number seven is enormously prime.",
      "is_correct": false
    },
    {
      "text": "People rely enormously on digital maps nowadays to find their way around unfamiliar cities.",
      "is_correct": true
    },
    {
      "text": "The battery was enormously dead by the next morning.",
      "is_correct": false
    },
    {
      "text": "He nodded enormously to confirm he understood the question.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'prime' is an absolute, binary property with no scale of degree, so it cannot logically be intensified by 'enormously'. semantic: 'dead' is an absolute state without gradations, making the degree adverb 'enormously' pragmatically inappropriate here. collocational: nodding is a small, discrete gesture, so pairing it with a large-degree adverb like 'enormously' creates an odd mismatch in scale.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Enormously talented young musicians performed at the annual youth festival last weekend.",
      "is_correct": true
    },
    {
      "text": "She enormously agreed with the plan before leaving early.",
      "is_correct": false
    },
    {
      "text": "He arrived enormously on time for the meeting.",
      "is_correct": false
    },
    {
      "text": "The tiny kitten was enormously small, hiding behind the cushion.",
      "is_correct": false
    }
  ],
  "explanation": "Contradictory: 'enormously' signals a very great degree, which conflicts logically with 'small'. Pragmatically odd: 'agree' is a binary, non-gradable action, so it cannot be intensified by a degree adverb like 'enormously'. Pragmatically odd: 'on time' is not a gradable state, so modifying it with 'enormously' doesn't make sensible use of the degree meaning.",
  "target_word": "Enormously"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The number seven is enormously prime.",
      "is_correct": false
    },
    {
      "text": "People rely enormously on digital maps nowadays to find their way around unfamiliar cities.",
      "is_correct": true
    },
    {
      "text": "The battery was enormously dead by the next morning.",
      "is_correct": false
    },
    {
      "text": "He nodded enormously to confirm he understood the question.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'prime' is an absolute, binary property with no scale of degree, so it cannot logically be intensified by 'enormously'. semantic: 'dead' is an absolute state without gradations, making the degree adverb 'enormously' pragmatically inappropriate here. collocational: nodding is a small, discrete gesture, so pairing it with a large-degree adverb like 'enormously' creates an odd mismatch in scale.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 9

#### Pack A
### Level 9 (sense 14390, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour.",
  "chunks": [
    "Traffic congestion in the city center",
    "increases",
    "enormously",
    "during the evening rush hour"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "increases",
    "during the evening rush hour",
    "enormously",
    "Traffic congestion in the city center"
  ],
  "target_word": "enormously",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend.",
  "chunks": [
    "Enormously talented young musicians",
    "performed",
    "at the annual youth festival",
    "last weekend"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "last weekend",
    "Enormously talented young musicians",
    "at the annual youth festival",
    "performed"
  ],
  "target_word": "Enormously",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14390, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour.",
  "chunks": [
    "Traffic congestion in the city center",
    "increases",
    "enormously",
    "during the evening rush hour"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "increases",
    "during the evening rush hour",
    "enormously",
    "Traffic congestion in the city center"
  ],
  "target_word": "enormously",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend.",
  "chunks": [
    "Enormously talented young musicians",
    "performed",
    "at the annual youth festival",
    "last weekend"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "last weekend",
    "Enormously talented young musicians",
    "at the annual youth festival",
    "performed"
  ],
  "target_word": "Enormously",
  "chunk_count": 4
}
```

---

## sense 14473, level 1

#### Pack A
### Level 1 (sense 14473, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "ipa": "/ˈoʊvər ˈtaɪm/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "Hover time",
    "Over rhyme",
    "Oven time",
    "Over time"
  ],
  "correct_answer": "Over time",
  "explanation": "This is the target phrase exactly as it would be spoken and written.",
  "distractor_explanations": {
    "Hover time": "minimal pair: 'hover' differs from 'over' only by the initial /h/ sound.",
    "Over rhyme": "minimal pair: 'rhyme' differs from 'time' only in the initial consonant /r/ vs /t/.",
    "Oven time": "minimal pair: 'oven' differs from 'over' by the medial consonant /v/ vs /n/ sound shift, easily confused in fast speech."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14473, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "ipa": "/ˈoʊvər ˈtaɪm/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "Hover time",
    "Over rhyme",
    "Oven time",
    "Over time"
  ],
  "correct_answer": "Over time",
  "explanation": "This is the target phrase exactly as it would be spoken and written.",
  "distractor_explanations": {
    "Hover time": "minimal pair: 'hover' differs from 'over' only by the initial /h/ sound.",
    "Over rhyme": "minimal pair: 'rhyme' differs from 'time' only in the initial consonant /r/ vs /t/.",
    "Oven time": "minimal pair: 'oven' differs from 'over' by the medial consonant /v/ vs /n/ sound shift, easily confused in fast speech."
  },
  "distractor_source": "llm"
}
```

---

## sense 14473, level 2

#### Pack A
### Level 2 (sense 14473, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "correct_definition": "Gradually, as time goes by.",
  "options": [
    "A person who visits a place or person.",
    "Gradually, as time goes by.",
    "Coming next after the eighth in a series.",
    "Diversity is the state of having a variety of different elements, such as cultures, backgrounds, or types."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Cotton is a natural fiber harvested from the cotton plant, used to make textiles and other products.",
        "Something that can be broken down by nature.",
        "Gradually, as time goes by.",
        "The state of being unknown or not identified by name."
      ],
      "correct_answer": "Gradually, as time goes by."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14473, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "correct_definition": "Gradually, as time goes by.",
  "options": [
    "A person who visits a place or person.",
    "Gradually, as time goes by.",
    "Coming next after the eighth in a series.",
    "Diversity is the state of having a variety of different elements, such as cultures, backgrounds, or types."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Cotton is a natural fiber harvested from the cotton plant, used to make textiles and other products.",
        "Something that can be broken down by nature.",
        "Gradually, as time goes by.",
        "The state of being unknown or not identified by name."
      ],
      "correct_answer": "Gradually, as time goes by."
    }
  }
}
```

---
