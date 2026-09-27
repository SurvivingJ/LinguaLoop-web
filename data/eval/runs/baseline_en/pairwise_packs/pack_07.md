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


## sense 14033, level 4

#### Pack A
### Level 4 (sense 14033, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "small",
  "sentence_with_blank": "It is made of small parts.",
  "original_sentence": "It is made of small parts.",
  "required_pos": "adjective",
  "options": [
    "smallal",
    "smallify",
    "small",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective is the correctly derived form needed to modify the noun"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "target_word": "small",
  "word": "Small",
  "answer": {
    "accepted": [
      "small",
      "smaller",
      "smallest"
    ],
    "accepted_normalized": [
      "small",
      "smaller",
      "smallest"
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
  "stem": "small",
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "required_pos": "adjective",
  "options": [
    "smallify",
    "small",
    "smallment",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective used directly to modify the noun"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14033, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "small",
  "sentence_with_blank": "It is made of small parts.",
  "original_sentence": "It is made of small parts.",
  "required_pos": "adjective",
  "options": [
    "smallal",
    "smallify",
    "small",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective is the correctly derived form needed to modify the noun"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "target_word": "small",
  "word": "Small",
  "answer": {
    "accepted": [
      "small",
      "smaller",
      "smallest"
    ],
    "accepted_normalized": [
      "small",
      "smaller",
      "smallest"
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
  "stem": "small",
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "required_pos": "adjective",
  "options": [
    "smallify",
    "small",
    "smallment",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective used directly to modify the noun"
    }
  }
}
```

---

## sense 14033, level 6

#### Pack A
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The elephant was small enough to hide inside a matchbox.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "They gave him a small mansion for his birthday.",
      "is_correct": false
    },
    {
      "text": "The skyscraper was small, casting a tiny shadow that covered the whole city.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically impossible: elephants are among the largest land animals and cannot be matchbox-sized. Contradictory: a skyscraper is by definition huge, and a 'tiny shadow' covering a whole city is logically inconsistent. Pragmatically odd: 'mansion' inherently implies a large residence, so pairing it with 'small' creates a contradiction.",
  "target_word": "small"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Every night, the small child goes to bed early.",
      "is_correct": true
    },
    {
      "text": "The ocean is small and stretches for thousands of miles in every direction.",
      "is_correct": false
    },
    {
      "text": "The small giant lifted the entire building with ease.",
      "is_correct": false
    },
    {
      "text": "She let out a small shout across the quiet library.",
      "is_correct": false
    }
  ],
  "explanation": "Contradiction: 'giant' inherently means huge, so pairing it with 'small' creates a logical clash. Contradiction: describing something that spans thousands of miles as 'small' is factually inconsistent. Pragmatic mismatch: a 'shout' is inherently loud, so calling it 'small' clashes with the word's normal meaning.",
  "target_word": "small"
}
```

#### Pack B
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The elephant was small enough to hide inside a matchbox.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "They gave him a small mansion for his birthday.",
      "is_correct": false
    },
    {
      "text": "The skyscraper was small, casting a tiny shadow that covered the whole city.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically impossible: elephants are among the largest land animals and cannot be matchbox-sized. Contradictory: a skyscraper is by definition huge, and a 'tiny shadow' covering a whole city is logically inconsistent. Pragmatically odd: 'mansion' inherently implies a large residence, so pairing it with 'small' creates a contradiction.",
  "target_word": "small"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Every night, the small child goes to bed early.",
      "is_correct": true
    },
    {
      "text": "The ocean is small and stretches for thousands of miles in every direction.",
      "is_correct": false
    },
    {
      "text": "The small giant lifted the entire building with ease.",
      "is_correct": false
    },
    {
      "text": "She let out a small shout across the quiet library.",
      "is_correct": false
    }
  ],
  "explanation": "Contradiction: 'giant' inherently means huge, so pairing it with 'small' creates a logical clash. Contradiction: describing something that spans thousands of miles as 'small' is factually inconsistent. Pragmatic mismatch: a 'shout' is inherently loud, so calling it 'small' clashes with the word's normal meaning.",
  "target_word": "small"
}
```

---

## sense 14033, level 9

#### Pack A
### Level 9 (sense 14033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Small plastic things go in the water."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Small plastic things go in the water.",
  "chunks": [
    "Small plastic things",
    "go",
    "in the water"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in the water",
    "go",
    "Small plastic things"
  ],
  "target_word": "Small",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They built small walls."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They built small walls.",
  "chunks": [
    "They",
    "built",
    "small walls"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "built",
    "They",
    "small walls"
  ],
  "target_word": "small",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Small plastic things go in the water."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Small plastic things go in the water.",
  "chunks": [
    "Small plastic things",
    "go",
    "in the water"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in the water",
    "go",
    "Small plastic things"
  ],
  "target_word": "Small",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They built small walls."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They built small walls.",
  "chunks": [
    "They",
    "built",
    "small walls"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "built",
    "They",
    "small walls"
  ],
  "target_word": "small",
  "chunk_count": 3
}
```

---

## sense 14040, level 2

#### Pack A
### Level 2 (sense 14040, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "constantly",
  "pronunciation": "kon-stuhnt-lee",
  "correct_definition": "Happening without stopping or very often.",
  "options": [
    "to remove something from a container or place",
    "To use something carelessly or in a way that is not sensible, often resulting in a loss.",
    "To pull something or someone along with effort, often behind you.",
    "Happening without stopping or very often."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "constantly",
  "pronunciation": "kon-stuhnt-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "An alcoholic drink made by mixing spirits with other ingredients like juice or soda.",
        "Happening without stopping or very often.",
        "Working together.",
        "to separate items into groups based on specific characteristics like size or quality."
      ],
      "correct_answer": "Happening without stopping or very often."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14040, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "constantly",
  "pronunciation": "kon-stuhnt-lee",
  "correct_definition": "Happening without stopping or very often.",
  "options": [
    "to remove something from a container or place",
    "To use something carelessly or in a way that is not sensible, often resulting in a loss.",
    "To pull something or someone along with effort, often behind you.",
    "Happening without stopping or very often."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "constantly",
  "pronunciation": "kon-stuhnt-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "An alcoholic drink made by mixing spirits with other ingredients like juice or soda.",
        "Happening without stopping or very often.",
        "Working together.",
        "to separate items into groups based on specific characteristics like size or quality."
      ],
      "correct_answer": "Happening without stopping or very often."
    }
  }
}
```

---

## sense 14040, level 4

#### Pack A
### Level 4 (sense 14040, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "By ___ removing heat, the system stops bacteria from multiplying, which protects our health and prevents premature spoiling.",
  "original_sentence": "By constantly removing heat, the system stops bacteria from multiplying, which protects our health and prevents premature spoiling.",
  "target_word": "constantly",
  "word": "constantly",
  "answer": {
    "accepted": [
      "constantly",
      "constant",
      "constancy"
    ],
    "accepted_normalized": [
      "constantly",
      "constant",
      "constancy"
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
### Level 4 (sense 14040, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "By ___ removing heat, the system stops bacteria from multiplying, which protects our health and prevents premature spoiling.",
  "original_sentence": "By constantly removing heat, the system stops bacteria from multiplying, which protects our health and prevents premature spoiling.",
  "target_word": "constantly",
  "word": "constantly",
  "answer": {
    "accepted": [
      "constantly",
      "constant",
      "constancy"
    ],
    "accepted_normalized": [
      "constantly",
      "constant",
      "constancy"
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

## sense 14040, level 9

#### Pack A
### Level 9 (sense 14040, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Weather patterns in the mountains change constantly throughout the spring season."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Weather patterns in the mountains change constantly throughout the spring season.",
  "chunks": [
    "Weather patterns in the mountains",
    "change",
    "constantly",
    "throughout the spring season"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "constantly",
    "throughout the spring season",
    "change",
    "Weather patterns in the mountains"
  ],
  "target_word": "constantly",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14040, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Weather patterns in the mountains change constantly throughout the spring season."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Weather patterns in the mountains change constantly throughout the spring season.",
  "chunks": [
    "Weather patterns in the mountains",
    "change",
    "constantly",
    "throughout the spring season"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "constantly",
    "throughout the spring season",
    "change",
    "Weather patterns in the mountains"
  ],
  "target_word": "constantly",
  "chunk_count": 4
}
```

---

## sense 14090, level 2

#### Pack A
### Level 2 (sense 14090, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "multifaceted",
  "pronunciation": "mul-ti-fac-et-ed",
  "correct_definition": "Having many different aspects, features, or parts.",
  "options": [
    "to clean something with water and often soap.",
    "To travel across or through an area, especially when exploring it.",
    "to take out something and put something else in its place.",
    "Having many different aspects, features, or parts."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "multifaceted",
  "pronunciation": "mul-ti-fac-et-ed",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To put things into a box or bag.",
        "Something you can buy or sell.",
        "A manager is someone who is responsible for controlling or directing a group of people, a business, or a part of a business.",
        "Having many different aspects, features, or parts."
      ],
      "correct_answer": "Having many different aspects, features, or parts."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14090, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "multifaceted",
  "pronunciation": "mul-ti-fac-et-ed",
  "correct_definition": "Having many different aspects, features, or parts.",
  "options": [
    "to clean something with water and often soap.",
    "To travel across or through an area, especially when exploring it.",
    "to take out something and put something else in its place.",
    "Having many different aspects, features, or parts."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "multifaceted",
  "pronunciation": "mul-ti-fac-et-ed",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To put things into a box or bag.",
        "Something you can buy or sell.",
        "A manager is someone who is responsible for controlling or directing a group of people, a business, or a part of a business.",
        "Having many different aspects, features, or parts."
      ],
      "correct_answer": "Having many different aspects, features, or parts."
    }
  }
}
```

---

## sense 14090, level 3

#### Pack A
### Level 3 (sense 14090, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The intricate tapestry of the global coffee bean supply chain is a testament to the ___ nature of international trade, agriculture, and sophisticated logistical networks.",
  "original_sentence": "The intricate tapestry of the global coffee bean supply chain is a testament to the multifaceted nature of international trade, agriculture, and sophisticated logistical networks.",
  "correct_answer": "multifaceted",
  "options": [
    "temporary",
    "casual",
    "singular",
    "multifaceted"
  ],
  "explanation": "Correctly describes the many aspects (trade, agriculture, logistics) of the supply chain.",
  "distractor_tags": {},
  "word_definition": "Having many different aspects, features, or parts.",
  "target_word": "multifaceted"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The committee faced a ___ challenge that required insights from economics, psychology, and public policy.",
  "original_sentence": "The committee faced a multifaceted challenge that required insights from economics, psychology, and public policy.",
  "correct_answer": "multifaceted",
  "options": [
    "multifaceted",
    "trivial",
    "punctual",
    "delicious"
  ],
  "explanation": "Correct: the challenge requires insight from several distinct fields, matching the meaning of having many aspects.",
  "distractor_tags": {},
  "word_definition": "Having many different aspects, features, or parts.",
  "target_word": "multifaceted"
}
```

#### Pack B
### Level 3 (sense 14090, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The intricate tapestry of the global coffee bean supply chain is a testament to the ___ nature of international trade, agriculture, and sophisticated logistical networks.",
  "original_sentence": "The intricate tapestry of the global coffee bean supply chain is a testament to the multifaceted nature of international trade, agriculture, and sophisticated logistical networks.",
  "correct_answer": "multifaceted",
  "options": [
    "temporary",
    "casual",
    "singular",
    "multifaceted"
  ],
  "explanation": "Correctly describes the many aspects (trade, agriculture, logistics) of the supply chain.",
  "distractor_tags": {},
  "word_definition": "Having many different aspects, features, or parts.",
  "target_word": "multifaceted"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The committee faced a ___ challenge that required insights from economics, psychology, and public policy.",
  "original_sentence": "The committee faced a multifaceted challenge that required insights from economics, psychology, and public policy.",
  "correct_answer": "multifaceted",
  "options": [
    "multifaceted",
    "trivial",
    "punctual",
    "delicious"
  ],
  "explanation": "Correct: the challenge requires insight from several distinct fields, matching the meaning of having many aspects.",
  "distractor_tags": {},
  "word_definition": "Having many different aspects, features, or parts.",
  "target_word": "multifaceted"
}
```

---

## sense 14090, level 4

#### Pack A
### Level 4 (sense 14090, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Choosing a career path is a ___ decision that involves considering your personal interests, financial needs, and future goals.",
  "original_sentence": "Choosing a career path is a multifaceted decision that involves considering your personal interests, financial needs, and future goals.",
  "target_word": "multifaceted",
  "word": "multifaceted",
  "answer": {
    "accepted": [
      "multifaceted"
    ],
    "accepted_normalized": [
      "multifaceted"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Preparing for the school debate competition was a ___ task that involved research, writing, and public speaking practice.",
  "original_sentence": "Preparing for the school debate competition was a multifaceted task that involved research, writing, and public speaking practice.",
  "target_word": "multifaceted",
  "word": "multifaceted",
  "answer": {
    "accepted": [
      "multifaceted"
    ],
    "accepted_normalized": [
      "multifaceted"
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
### Level 4 (sense 14090, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Choosing a career path is a ___ decision that involves considering your personal interests, financial needs, and future goals.",
  "original_sentence": "Choosing a career path is a multifaceted decision that involves considering your personal interests, financial needs, and future goals.",
  "target_word": "multifaceted",
  "word": "multifaceted",
  "answer": {
    "accepted": [
      "multifaceted"
    ],
    "accepted_normalized": [
      "multifaceted"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Preparing for the school debate competition was a ___ task that involved research, writing, and public speaking practice.",
  "original_sentence": "Preparing for the school debate competition was a multifaceted task that involved research, writing, and public speaking practice.",
  "target_word": "multifaceted",
  "word": "multifaceted",
  "answer": {
    "accepted": [
      "multifaceted"
    ],
    "accepted_normalized": [
      "multifaceted"
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

## sense 14090, level 6

#### Pack A
### Level 6 (sense 14090, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination.",
      "is_correct": true
    },
    {
      "text": "He drank a multifaceted glass of water before bed.",
      "is_correct": false
    },
    {
      "text": "The empty room contained a multifaceted silence that lasted for hours.",
      "is_correct": false
    },
    {
      "text": "The straight line drawn on the paper was multifaceted.",
      "is_correct": false
    }
  ],
  "explanation": "Silence has no distinguishable parts or aspects, so calling it 'multifaceted' misuses the word's meaning. A plain glass of water is a simple, single-aspect object, not something with many facets or components. A straight line is a single, uniform shape with no multiple aspects, making 'multifaceted' contextually inappropriate here.",
  "target_word": "multifaceted"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The recipe calls for a multifaceted egg to make the cake rise properly.",
      "is_correct": false
    },
    {
      "text": "She gave a multifaceted nod to show she understood the instructions.",
      "is_correct": false
    },
    {
      "text": "Solving the complex math puzzle required a multifaceted approach involving logic, geometry, and trial-and-error strategies.",
      "is_correct": true
    },
    {
      "text": "The puddle in the parking lot was multifaceted after the rain.",
      "is_correct": false
    }
  ],
  "explanation": "An egg is a simple physical object with no distinct aspects or features, so 'multifaceted' cannot logically describe it. A nod is a single, simple gesture; it cannot consist of many different aspects or parts. A puddle is a plain, uniform physical thing with no multiple components or dimensions, making 'multifaceted' inappropriate here.",
  "target_word": "multifaceted"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "multifaceted",
  "relation": "antonym",
  "options": [
    "complex",
    "one-dimensional",
    "diverse",
    "intricate"
  ],
  "correct_answer": "one-dimensional",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Having many different aspects, features, or parts.",
      "explanation": "antonym: having only a single aspect or feature, opposite of many-faceted"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14090, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination.",
      "is_correct": true
    },
    {
      "text": "He drank a multifaceted glass of water before bed.",
      "is_correct": false
    },
    {
      "text": "The empty room contained a multifaceted silence that lasted for hours.",
      "is_correct": false
    },
    {
      "text": "The straight line drawn on the paper was multifaceted.",
      "is_correct": false
    }
  ],
  "explanation": "Silence has no distinguishable parts or aspects, so calling it 'multifaceted' misuses the word's meaning. A plain glass of water is a simple, single-aspect object, not something with many facets or components. A straight line is a single, uniform shape with no multiple aspects, making 'multifaceted' contextually inappropriate here.",
  "target_word": "multifaceted"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The recipe calls for a multifaceted egg to make the cake rise properly.",
      "is_correct": false
    },
    {
      "text": "She gave a multifaceted nod to show she understood the instructions.",
      "is_correct": false
    },
    {
      "text": "Solving the complex math puzzle required a multifaceted approach involving logic, geometry, and trial-and-error strategies.",
      "is_correct": true
    },
    {
      "text": "The puddle in the parking lot was multifaceted after the rain.",
      "is_correct": false
    }
  ],
  "explanation": "An egg is a simple physical object with no distinct aspects or features, so 'multifaceted' cannot logically describe it. A nod is a single, simple gesture; it cannot consist of many different aspects or parts. A puddle is a plain, uniform physical thing with no multiple components or dimensions, making 'multifaceted' inappropriate here.",
  "target_word": "multifaceted"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "multifaceted",
  "relation": "antonym",
  "options": [
    "complex",
    "one-dimensional",
    "diverse",
    "intricate"
  ],
  "correct_answer": "one-dimensional",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Having many different aspects, features, or parts.",
      "explanation": "antonym: having only a single aspect or feature, opposite of many-faceted"
    }
  }
}
```

---
