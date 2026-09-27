# Pairwise review pack 05

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


## sense 14010, level 4

#### Pack A
### Level 4 (sense 14010, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "This means how people in ___ places think.",
  "original_sentence": "This means how people in different places think.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
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
  "stem": "differ",
  "sentence_with_blank": "This means how people in ___ places think.",
  "original_sentence": "This means how people in different places think.",
  "required_pos": "adjective",
  "options": [
    "differal",
    "differment",
    "differous",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjective meaning 'not the same'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
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
  "stem": "differ",
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "required_pos": "adjective",
  "options": [
    "differous",
    "differity",
    "differment",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the correct adjective form meaning unlike or not the same"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14010, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "This means how people in ___ places think.",
  "original_sentence": "This means how people in different places think.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
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
  "stem": "differ",
  "sentence_with_blank": "This means how people in ___ places think.",
  "original_sentence": "This means how people in different places think.",
  "required_pos": "adjective",
  "options": [
    "differal",
    "differment",
    "differous",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjective meaning 'not the same'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "differently"
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
  "stem": "differ",
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "required_pos": "adjective",
  "options": [
    "differous",
    "differity",
    "differment",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the correct adjective form meaning unlike or not the same"
    }
  }
}
```

---

## sense 14010, level 6

#### Pack A
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The two songs sounded identical, yet they were different in every possible way.",
      "is_correct": false
    },
    {
      "text": "The twins were completely different because they looked exactly alike.",
      "is_correct": false
    },
    {
      "text": "He always eats the same breakfast, which is different every single day.",
      "is_correct": false
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    }
  ],
  "explanation": "Contradiction: looking 'exactly alike' cannot logically result in being 'completely different'. Contradiction: eating 'the same breakfast' every day cannot also be 'different' every day. Contradiction: sounding 'identical' directly conflicts with being 'different in every possible way'.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "varied",
    "diverse",
    "same",
    "distinct"
  ],
  "correct_answer": "same",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "antonym: being identical rather than unlike"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He eats the same different breakfast every morning: eggs and toast.",
      "is_correct": false
    },
    {
      "text": "The underlying physics also dictates the behavior of air at different altitudes and speeds.",
      "is_correct": true
    },
    {
      "text": "The twins have different faces, so people always confuse them for each other.",
      "is_correct": false
    },
    {
      "text": "These two photos are different, even though they are exact copies of the same image.",
      "is_correct": false
    }
  ],
  "explanation": "Contradictory: if their faces are truly different, people should not confuse them; this misuses 'different' against the logic of the sentence. Contradictory: 'same' and 'different' cannot both describe an unchanging daily breakfast, making this usage nonsensical. Contradictory: exact copies of the same image cannot logically be called 'different', so the word is misapplied here.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "unusual",
    "distinct",
    "diverse",
    "identical"
  ],
  "correct_answer": "identical",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "antonym: exactly the same as another, the opposite of unlike"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The two songs sounded identical, yet they were different in every possible way.",
      "is_correct": false
    },
    {
      "text": "The twins were completely different because they looked exactly alike.",
      "is_correct": false
    },
    {
      "text": "He always eats the same breakfast, which is different every single day.",
      "is_correct": false
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    }
  ],
  "explanation": "Contradiction: looking 'exactly alike' cannot logically result in being 'completely different'. Contradiction: eating 'the same breakfast' every day cannot also be 'different' every day. Contradiction: sounding 'identical' directly conflicts with being 'different in every possible way'.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "varied",
    "diverse",
    "same",
    "distinct"
  ],
  "correct_answer": "same",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "antonym: being identical rather than unlike"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He eats the same different breakfast every morning: eggs and toast.",
      "is_correct": false
    },
    {
      "text": "The underlying physics also dictates the behavior of air at different altitudes and speeds.",
      "is_correct": true
    },
    {
      "text": "The twins have different faces, so people always confuse them for each other.",
      "is_correct": false
    },
    {
      "text": "These two photos are different, even though they are exact copies of the same image.",
      "is_correct": false
    }
  ],
  "explanation": "Contradictory: if their faces are truly different, people should not confuse them; this misuses 'different' against the logic of the sentence. Contradictory: 'same' and 'different' cannot both describe an unchanging daily breakfast, making this usage nonsensical. Contradictory: exact copies of the same image cannot logically be called 'different', so the word is misapplied here.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "unusual",
    "distinct",
    "diverse",
    "identical"
  ],
  "correct_answer": "identical",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "antonym: exactly the same as another, the opposite of unlike"
    }
  }
}
```

---

## sense 14010, level 9

#### Pack A
### Level 9 (sense 14010, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Across the world, different societies have always used stories."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Across the world, different societies have always used stories.",
  "chunks": [
    "Across the world",
    "different societies",
    "have used",
    "always",
    "stories"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "different societies",
    "have used",
    "stories",
    "always",
    "Across the world"
  ],
  "target_word": "different",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
  "chunks": [
    "Sometimes",
    "this can lead",
    "to misunderstandings",
    "when people from different cultural backgrounds interact"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "this can lead",
    "when people from different cultural backgrounds interact",
    "Sometimes",
    "to misunderstandings"
  ],
  "target_word": "different",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14010, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Across the world, different societies have always used stories."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Across the world, different societies have always used stories.",
  "chunks": [
    "Across the world",
    "different societies",
    "have used",
    "always",
    "stories"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "different societies",
    "have used",
    "stories",
    "always",
    "Across the world"
  ],
  "target_word": "different",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
  "chunks": [
    "Sometimes",
    "this can lead",
    "to misunderstandings",
    "when people from different cultural backgrounds interact"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "this can lead",
    "when people from different cultural backgrounds interact",
    "Sometimes",
    "to misunderstandings"
  ],
  "target_word": "different",
  "chunk_count": 4
}
```

---

## sense 14015, level 1

#### Pack A
### Level 1 (sense 14015, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "ipa": "ˈroʊstɪŋ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "Roasting",
    "Coasting",
    "Toasting",
    "Roosting"
  ],
  "correct_answer": "Roasting",
  "explanation": "This is the target word exactly as it is pronounced and spelled.",
  "distractor_explanations": {
    "Roosting": "Minimal pair: differs from the target by the vowel sound (/uː/ vs /oʊ/), refers to birds settling to rest.",
    "Toasting": "Rhymes with the target but starts with a different consonant sound (/t/ vs /r/); refers to browning bread.",
    "Coasting": "Rhymes with the target but starts with a different consonant sound (/k/ vs /r/); means moving without effort."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14015, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "ipa": "ˈroʊstɪŋ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "Roasting",
    "Coasting",
    "Toasting",
    "Roosting"
  ],
  "correct_answer": "Roasting",
  "explanation": "This is the target word exactly as it is pronounced and spelled.",
  "distractor_explanations": {
    "Roosting": "Minimal pair: differs from the target by the vowel sound (/uː/ vs /oʊ/), refers to birds settling to rest.",
    "Toasting": "Rhymes with the target but starts with a different consonant sound (/t/ vs /r/); refers to browning bread.",
    "Coasting": "Rhymes with the target but starts with a different consonant sound (/k/ vs /r/); means moving without effort."
  },
  "distractor_source": "llm"
}
```

---

## sense 14015, level 2

#### Pack A
### Level 2 (sense 14015, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "correct_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "options": [
    "A period of time between two points or events.",
    "The act of confirming or proving that something is true, correct, or acceptable; also, the feeling of being recognized or approved by others.",
    "To arrange laws or rules into a systematic code.",
    "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The hard outer layer of bread that forms when it is baked.",
        "To make something smaller.",
        "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
        "A bag is something you use to carry things."
      ],
      "correct_answer": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14015, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "correct_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "options": [
    "A period of time between two points or events.",
    "The act of confirming or proving that something is true, correct, or acceptable; also, the feeling of being recognized or approved by others.",
    "To arrange laws or rules into a systematic code.",
    "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The hard outer layer of bread that forms when it is baked.",
        "To make something smaller.",
        "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
        "A bag is something you use to carry things."
      ],
      "correct_answer": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame."
    }
  }
}
```

---

## sense 14015, level 3

#### Pack A
### Level 3 (sense 14015, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Proper ___ requires careful attention so the garlic does not burn.",
  "original_sentence": "Proper roasting requires careful attention so the garlic does not burn.",
  "correct_answer": "roasting",
  "options": [
    "roasting",
    "freezing",
    "boiling",
    "chopping"
  ],
  "explanation": "Correct: 'roasting' is the cooking process that needs attention so garlic does not burn.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```

#### Pack B
### Level 3 (sense 14015, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Proper ___ requires careful attention so the garlic does not burn.",
  "original_sentence": "Proper roasting requires careful attention so the garlic does not burn.",
  "correct_answer": "roasting",
  "options": [
    "roasting",
    "freezing",
    "boiling",
    "chopping"
  ],
  "explanation": "Correct: 'roasting' is the cooking process that needs attention so garlic does not burn.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```

---

## sense 14015, level 4

#### Pack A
### Level 4 (sense 14015, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They have been ___ green beans all morning to test the new machine.",
  "original_sentence": "They have been roasting green beans all morning to test the new machine.",
  "target_word": "roasting",
  "word": "Roasting",
  "answer": {
    "accepted": [
      "roasting",
      "roast",
      "roasts",
      "roasted"
    ],
    "accepted_normalized": [
      "roasting",
      "roast",
      "roasts",
      "roasted"
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
  "stem": "roast",
  "sentence_with_blank": "They have been ___ green beans all morning to test the new machine.",
  "original_sentence": "They have been roasting green beans all morning to test the new machine.",
  "required_pos": "noun",
  "options": [
    "roastness",
    "roasting",
    "roastal",
    "roastment"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the -ing nominalisation naming the dry-heat cooking method, correctly used here"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14015, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They have been ___ green beans all morning to test the new machine.",
  "original_sentence": "They have been roasting green beans all morning to test the new machine.",
  "target_word": "roasting",
  "word": "Roasting",
  "answer": {
    "accepted": [
      "roasting",
      "roast",
      "roasts",
      "roasted"
    ],
    "accepted_normalized": [
      "roasting",
      "roast",
      "roasts",
      "roasted"
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
  "stem": "roast",
  "sentence_with_blank": "They have been ___ green beans all morning to test the new machine.",
  "original_sentence": "They have been roasting green beans all morning to test the new machine.",
  "required_pos": "noun",
  "options": [
    "roastness",
    "roasting",
    "roastal",
    "roastment"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the -ing nominalisation naming the dry-heat cooking method, correctly used here"
    }
  }
}
```

---

## sense 14015, level 6

#### Pack A
### Level 6 (sense 14015, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She spent the morning roasting her paperwork before submitting it to HR.",
      "is_correct": false
    },
    {
      "text": "I tried roasting sweet potatoes with olive oil and rosemary last night.",
      "is_correct": true
    },
    {
      "text": "He was roasting his phone in the microwave to charge it faster.",
      "is_correct": false
    },
    {
      "text": "The scientist tried roasting the ice cubes to keep them frozen longer.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically wrong: roasting is a cooking method and cannot be used to charge electronic devices. Semantically contradictory: roasting applies dry heat, which would melt ice, not preserve it frozen. Pragmatically inappropriate: paperwork is not a food item that undergoes a cooking process like roasting.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "boiling",
    "baking",
    "grilling",
    "seasoning"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: cooking method using moist heat/water instead of dry heat"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14015, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She spent the morning roasting her paperwork before submitting it to HR.",
      "is_correct": false
    },
    {
      "text": "I tried roasting sweet potatoes with olive oil and rosemary last night.",
      "is_correct": true
    },
    {
      "text": "He was roasting his phone in the microwave to charge it faster.",
      "is_correct": false
    },
    {
      "text": "The scientist tried roasting the ice cubes to keep them frozen longer.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically wrong: roasting is a cooking method and cannot be used to charge electronic devices. Semantically contradictory: roasting applies dry heat, which would melt ice, not preserve it frozen. Pragmatically inappropriate: paperwork is not a food item that undergoes a cooking process like roasting.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "boiling",
    "baking",
    "grilling",
    "seasoning"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: cooking method using moist heat/water instead of dry heat"
    }
  }
}
```

---

## sense 14015, level 9

#### Pack A
### Level 9 (sense 14015, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "My dad loves roasting marshmallows over the campfire during our family trips."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "My dad loves roasting marshmallows over the campfire during our family trips.",
  "chunks": [
    "My dad",
    "loves",
    "roasting marshmallows",
    "over the campfire",
    "during our family trips"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "loves",
    "during our family trips",
    "My dad",
    "over the campfire",
    "roasting marshmallows"
  ],
  "target_word": "roasting",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 14015, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "My dad loves roasting marshmallows over the campfire during our family trips."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "My dad loves roasting marshmallows over the campfire during our family trips.",
  "chunks": [
    "My dad",
    "loves",
    "roasting marshmallows",
    "over the campfire",
    "during our family trips"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "loves",
    "during our family trips",
    "My dad",
    "over the campfire",
    "roasting marshmallows"
  ],
  "target_word": "roasting",
  "chunk_count": 5
}
```

---

## sense 14020, level 2

#### Pack A
### Level 2 (sense 14020, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aromas",
  "pronunciation": "uh-ROH-muh",
  "correct_definition": "A pleasant, distinctive smell, often of food or drink.",
  "options": [
    "Of considerable or relatively great size, extent, or capacity.",
    "A pleasant, distinctive smell, often of food or drink.",
    "A continent is one of the seven large landmasses on Earth, such as Europe, Asia, or Africa.",
    "The careful use and protection of natural resources like water, forests, and animals."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aromas",
  "pronunciation": "uh-ROH-muh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The soul is the part of a person that thinks and feels, not the body.",
        "To cause something, especially a problem or danger; also, to sit or stand in a particular position for a picture.",
        "A loud mix of many sounds that is not nice to hear.",
        "A pleasant, distinctive smell, often of food or drink."
      ],
      "correct_answer": "A pleasant, distinctive smell, often of food or drink."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14020, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aromas",
  "pronunciation": "uh-ROH-muh",
  "correct_definition": "A pleasant, distinctive smell, often of food or drink.",
  "options": [
    "Of considerable or relatively great size, extent, or capacity.",
    "A pleasant, distinctive smell, often of food or drink.",
    "A continent is one of the seven large landmasses on Earth, such as Europe, Asia, or Africa.",
    "The careful use and protection of natural resources like water, forests, and animals."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aromas",
  "pronunciation": "uh-ROH-muh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The soul is the part of a person that thinks and feels, not the body.",
        "To cause something, especially a problem or danger; also, to sit or stand in a particular position for a picture.",
        "A loud mix of many sounds that is not nice to hear.",
        "A pleasant, distinctive smell, often of food or drink."
      ],
      "correct_answer": "A pleasant, distinctive smell, often of food or drink."
    }
  }
}
```

---
