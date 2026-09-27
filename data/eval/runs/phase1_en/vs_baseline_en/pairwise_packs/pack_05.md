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


## sense 14015, level 1

#### Pack A
### Level 1 (sense 14015, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "roasting",
  "pronunciation": "ROHST-ing",
  "ipa": "ˈroʊstɪŋ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "roasting",
    "resting",
    "boasting",
    "rusting"
  ],
  "correct_answer": "roasting",
  "explanation": "Correct: This is the target word pronounced /ˈroʊstɪŋ/.",
  "distractor_explanations": {
    "boasting": "Rhyme: Shares the same /oʊstɪŋ/ ending sound but starts with a different consonant /b/ instead of /r/.",
    "rusting": "Minimal pair: Differs only in the vowel sound, using /ʌ/ (as in 'cup') instead of the /oʊ/ diphthong.",
    "resting": "Minimal pair: Differs only in the vowel sound, using /ɛ/ (as in 'bed') instead of the /oʊ/ diphthong."
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
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHST-ing",
  "correct_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "options": [
    "All people born and living at about the same time, regarded collectively.",
    "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
    "A part or element of a larger whole, especially one that is essential or characteristic.",
    "Extremely loud, like the sound of thunder."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHST-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to be bigger or more than something",
        "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
        "Having or showing the knowledge, ability, or training to do something well.",
        "to spoil or reduce the quality or effectiveness of something."
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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___ is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "original_sentence": "Roasting is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "correct_answer": "Roasting",
  "options": [
    "Harvesting",
    "Frying",
    "Planting",
    "Roasting"
  ],
  "explanation": "Correct completion. It is the noun/gerund referring to the dry-heat cooking method that develops coffee flavors.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "Roasting"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Before making soup, he tried ___ the tomatoes to deepen their flavor.",
  "original_sentence": "Before making soup, he tried roasting the tomatoes to deepen their flavor.",
  "correct_answer": "roasting",
  "options": [
    "roasting",
    "peeling",
    "eating",
    "boiling"
  ],
  "explanation": "Correct: 'Roasting' is the exact gerund form required by the sentence to describe the cooking method applied to the tomatoes.",
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
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "roast",
  "sentence_with_blank": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "original_sentence": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "required_pos": "noun",
  "options": [
    "roasting",
    "roastation",
    "roastment",
    "roastive"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund functioning as a noun modifier for techniques"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The secret to this recipe is the careful ___ of the green coffee beans.",
  "original_sentence": "The secret to this recipe is the careful roasting of the green coffee beans.",
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
  "sentence_with_blank": "The secret to this recipe is the careful ___ of the green coffee beans.",
  "original_sentence": "The secret to this recipe is the careful roasting of the green coffee beans.",
  "required_pos": "noun",
  "options": [
    "roasture",
    "roastation",
    "roastment",
    "roasting"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund functioning as a noun after the adjective"
    }
  }
}
```

---

## sense 14015, level 6

#### Pack A
### Level 6 (sense 14015, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They spent the afternoon roasting marshmallows over the backyard fire pit.",
      "is_correct": true
    },
    {
      "text": "The mechanic spent the afternoon roasting the motor oil to make the engine run smoother.",
      "is_correct": false
    },
    {
      "text": "The students were roasting the chalk on their desks to get ready for the math test.",
      "is_correct": false
    },
    {
      "text": "She was roasting the ice cubes in the oven to prepare a cold beverage.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'roasting' specifically refers to cooking food with dry heat, not heating mechanical fluids. Semantically inappropriate: ice cubes melt when exposed to heat and cannot be 'roasted' like solid food. Pragmatically inappropriate: chalk is an inanimate mineral tool, not a food item that can be cooked or roasted.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "frying",
    "grilling",
    "boiling",
    "baking"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a cooking method using moist heat, contrasting with the dry heat of roasting"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The roasting of the documents in the fireplace ensured that the secret information was completely destroyed.",
      "is_correct": false
    },
    {
      "text": "The loud roasting of the thunderstorm kept the children awake throughout the entire night.",
      "is_correct": false
    },
    {
      "text": "Dark roasting gives the coffee beans a bold and slightly bitter taste.",
      "is_correct": true
    },
    {
      "text": "She spent the entire afternoon roasting the heavy winter blankets to keep them warm for the bed.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Roasting' specifically refers to cooking with dry heat; 'burning' or 'incinerating' is the correct term for destroying documents. Semantically inappropriate: 'Roasting' applies to food items undergoing a chemical change via heat, not to inanimate objects like blankets which would simply catch fire. Semantically inappropriate: 'Roasting' denotes a cooking method or intense physical heat, whereas the correct auditory word for a storm is 'roaring'.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "grilling",
    "frying",
    "baking",
    "boiling"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a moist-heat cooking method contrasting with the dry heat of roasting"
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
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "We smelled the wonderful aromas of roasting chicken coming from the kitchen."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "We smelled the wonderful aromas of roasting chicken coming from the kitchen.",
  "chunks": [
    "We",
    "smelled",
    "the wonderful aromas of roasting chicken coming from the kitchen"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "the wonderful aromas of roasting chicken coming from the kitchen",
    "We",
    "smelled"
  ],
  "target_word": "roasting",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They spent the afternoon roasting marshmallows over the backyard fire pit."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They spent the afternoon roasting marshmallows over the backyard fire pit.",
  "chunks": [
    "They spent",
    "the afternoon roasting marshmallows",
    "over the backyard fire pit"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "They spent",
    "over the backyard fire pit",
    "the afternoon roasting marshmallows"
  ],
  "target_word": "roasting",
  "chunk_count": 3
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
  "word": "aroma",
  "pronunciation": "uh-ROH-muh",
  "correct_definition": "A pleasant, distinctive smell, often of food or drink.",
  "options": [
    "Attractive or pleasing, especially in a delicate or graceful way.",
    "A pleasant, distinctive smell, often of food or drink.",
    "A thin sphere of liquid filled with air or gas.",
    "The amount of money that you spend on something."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aroma",
  "pronunciation": "uh-ROH-muh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Longer is used to say something continues for a greater amount of time than something else.",
        "To notice something with the eyes; also, to understand.",
        "Relating to the social system of medieval Europe in which land was held by lords and worked by serfs or peasants under a hierarchy of obligations.",
        "A pleasant, distinctive smell, often of food or drink."
      ],
      "correct_answer": "A pleasant, distinctive smell, often of food or drink."
    }
  }
}
```

---

## sense 14020, level 4

#### Pack A
### Level 4 (sense 14020, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___s of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aromas of rising dough.",
  "target_word": "aroma",
  "word": "aromas",
  "answer": {
    "accepted": [
      "aroma"
    ],
    "accepted_normalized": [
      "aroma"
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
### Level 4 (sense 14020, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The compost is deemed mature when it has cooled, turned a uniform dark brown, and possesses an earthy ___, free from any discernible food scrap remnants.",
  "original_sentence": "The compost is deemed mature when it has cooled, turned a uniform dark brown, and possesses an earthy aroma, free from any discernible food scrap remnants.",
  "target_word": "aroma",
  "word": "aroma",
  "answer": {
    "accepted": [
      "aroma",
      "aromas"
    ],
    "accepted_normalized": [
      "aroma",
      "aromas"
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
  "sentence_with_blank": "A strong ___ of pine trees welcomed visitors as they entered the forest.",
  "original_sentence": "A strong aroma of pine trees welcomed visitors as they entered the forest.",
  "target_word": "aroma",
  "word": "aroma",
  "answer": {
    "accepted": [
      "aroma",
      "aromas"
    ],
    "accepted_normalized": [
      "aroma",
      "aromas"
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

## sense 14020, level 9

#### Pack A
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee beans."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee beans.",
  "chunks": [
    "She closed",
    "her eyes",
    "and enjoyed the rich aroma of fresh coffee beans"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She closed",
    "and enjoyed the rich aroma of fresh coffee beans",
    "her eyes"
  ],
  "target_word": "aroma",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The finished compost is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful breakdown of organic yard waste."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The finished compost is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful breakdown of organic yard waste.",
  "chunks": [
    "The finished compost",
    "is characterized",
    "typically",
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful breakdown of organic yard waste"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful breakdown of organic yard waste",
    "is characterized",
    "The finished compost",
    "typically"
  ],
  "target_word": "aroma",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied.",
  "chunks": [
    "The rich aromas of brewing tea",
    "filled",
    "the quiet room",
    "while they studied"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "the quiet room",
    "The rich aromas of brewing tea",
    "filled",
    "while they studied"
  ],
  "target_word": "aroma",
  "chunk_count": 4
}
```

---

## sense 14024, level 1

#### Pack A
### Level 1 (sense 14024, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "ipa": "/ˈnʌti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "putty",
    "nutty",
    "nitty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "This is the target word, correctly spelled as it would be pronounced /ˈnʌti/.",
  "distractor_explanations": {
    "knotty": "near-homophone: very close in sound, differing mainly in the vowel (/ɒ/ vs /ʌ/), but means 'full of knots'.",
    "nitty": "minimal pair: differs only in the vowel sound (/ɪ/ vs /ʌ/), as in the phrase 'nitty-gritty'.",
    "putty": "rhymes with the target but starts with a different consonant (/p/ vs /n/); means a soft moldable substance."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14024, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "ipa": "/ˈnʌti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "natty",
    "nutty",
    "putty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "correct answer: matches the spoken target word exactly.",
  "distractor_explanations": {
    "natty": "minimal pair: differs only in the vowel sound /æ/ versus /ʌ/.",
    "putty": "minimal pair: differs only in the initial consonant /p/ versus /n/.",
    "knotty": "minimal pair: differs in the vowel sound /ɒ/ versus /ʌ/."
  },
  "distractor_source": "llm"
}
```

---
