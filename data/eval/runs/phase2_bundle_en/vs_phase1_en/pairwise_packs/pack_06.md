# Pairwise review pack 06

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


## sense 14010, level 7

#### Pack A
### Level 7 (sense 14010, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "People see time in different ways.",
      "is_correct": true
    },
    {
      "text": "They learn about different times.",
      "is_correct": true
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    },
    {
      "text": "The climate in this region is completely different than the climate in my home country.",
      "is_correct": false,
      "error_description": "The adjective 'different' should be followed by the preposition 'from' rather than 'than' when making comparisons in standard English."
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14010, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "People have different opinion about the movie.",
      "is_correct": false,
      "error_description": "The adjective 'different' implies variety or distinction among multiple items, so it typically modifies a plural noun when referring to countable entities like 'opinions'. Using the singular 'opinion' suggests only one view exists, which contradicts the meaning of 'different'."
    },
    {
      "text": "They learn about different times.",
      "is_correct": true
    },
    {
      "text": "People see time in different ways.",
      "is_correct": true
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
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
      "text": "Cultural values shape how people in different places think about the world.",
      "is_correct": true
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "The beans travel for weeks, crossing many borders, to reach different countries.",
      "is_correct": true
    },
    {
      "text": "People in different places has different opinions.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The plural subject 'People' requires the plural verb 'have', not the singular 'has'."
    }
  ]
}
```

---

## sense 14010, level 9

#### Pack A
### Level 9 (sense 14010, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The underlying physics also dictates the behavior of air at different altitudes and speeds."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The underlying physics also dictates the behavior of air at different altitudes and speeds.",
  "chunks": [
    "The underlying physics",
    "also",
    "dictates",
    "the behavior of air",
    "at different altitudes and speeds"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "also",
    "dictates",
    "at different altitudes and speeds",
    "the behavior of air",
    "The underlying physics"
  ],
  "target_word": "different",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The growth of globalism means more and more people are working and living across different cultures."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The growth of globalism means more and more people are working and living across different cultures.",
  "chunks": [
    "The growth of globalism",
    "means",
    "more and more people are working and living across different cultures"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "more and more people are working and living across different cultures",
    "The growth of globalism",
    "means"
  ],
  "target_word": "different",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14010, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The underlying physics also dictates the behavior of air at different altitudes and speeds."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The underlying physics also dictates the behavior of air at different altitudes and speeds.",
  "chunks": [
    "The underlying physics",
    "also",
    "dictates",
    "the behavior of air",
    "at different altitudes and speeds"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "also",
    "dictates",
    "at different altitudes and speeds",
    "the behavior of air",
    "The underlying physics"
  ],
  "target_word": "different",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The growth of globalism means more and more people are working and living across different cultures."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The growth of globalism means more and more people are working and living across different cultures.",
  "chunks": [
    "The growth of globalism",
    "means",
    "more and more people are working and living across different cultures"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "more and more people are working and living across different cultures",
    "The growth of globalism",
    "means"
  ],
  "target_word": "different",
  "chunk_count": 3
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
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "correct_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "options": [
    "A thin, soft piece of paper used for wiping the nose or cleaning surfaces.",
    "to put something in a particular position or location",
    "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
    "The state of being aware of and able to think about your own existence, thoughts, and surroundings."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROHS-ting",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "An examination is a detailed inspection or study of something, or a formal test of knowledge or ability.",
        "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
        "The act of eating or drinking something.",
        "A benefit is an advantage or something that improves a situation."
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
  "sentence_with_blank": "Careful ___ prevents the prime rib from drying out while ensuring a beautiful browned crust.",
  "original_sentence": "Careful roasting prevents the prime rib from drying out while ensuring a beautiful browned crust.",
  "correct_answer": "Roasting",
  "options": [
    "Poaching",
    "Microwaving",
    "Grilling",
    "Roasting"
  ],
  "explanation": "Correct. 'Roasting' fits the context of preventing prime rib from drying out.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```

#### Pack B
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

---

## sense 14015, level 4

#### Pack A
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

#### Pack B
### Level 4 (sense 14015, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Different roasting techniques can create a crispy exterior and tender, juicy interior for root vegetables.",
  "original_sentence": "Different roasting techniques can create a crispy exterior and tender, juicy interior for root vegetables.",
  "correct_answer": "Roasting",
  "base_form": "roast",
  "form_label": "present participle",
  "options": [
    "Roast",
    "Roasting",
    "Roasts",
    "Roasted"
  ],
  "explanation": "present participle",
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "Roasting"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The kitchen was filled with the warm scent of ___ garlic.",
  "original_sentence": "The kitchen was filled with the warm scent of roasting garlic.",
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The kitchen was filled with the warm scent of ___ garlic.",
  "original_sentence": "The kitchen was filled with the warm scent of roasting garlic.",
  "correct_answer": "Roasting",
  "base_form": "roast",
  "form_label": "present participle",
  "options": [
    "Roasted",
    "Roast",
    "Roasts",
    "Roasting"
  ],
  "explanation": "present participle",
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
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
      "text": "I am roasting in this hot car without air conditioning.",
      "is_correct": false
    },
    {
      "text": "The comedian was roasting the audience with his sharp jokes.",
      "is_correct": false
    },
    {
      "text": "We prefer roasting nuts at home instead of buying them ready-made.",
      "is_correct": false
    },
    {
      "text": "We prefer roasting nuts at home instead of buying them ready-made.",
      "is_correct": true
    }
  ],
  "explanation": "This sentence is correct and uses 'roasting' appropriately as a cooking method. Incorrect sense. Here 'roasting' means mocking or criticizing humorously. Incorrect sense. Here 'roasting' means feeling extremely hot, not cooking food.",
  "target_word": "roasting"
}
```

---

## sense 14015, level 9

#### Pack A
### Level 9 (sense 14015, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They spent the afternoon roasting marshmallows over the campfire."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They spent the afternoon roasting marshmallows over the campfire.",
  "chunks": [
    "They spent",
    "the afternoon roasting marshmallows",
    "over the campfire"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "over the campfire",
    "They spent",
    "the afternoon roasting marshmallows"
  ],
  "target_word": "roasting",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The chef checked the temperature while roasting the large chicken."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The chef checked the temperature while roasting the large chicken.",
  "chunks": [
    "The chef",
    "checked",
    "the temperature",
    "while roasting the large chicken"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "while roasting the large chicken",
    "The chef",
    "checked",
    "the temperature"
  ],
  "target_word": "roasting",
  "chunk_count": 4
}
```

#### Pack B
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

---

## sense 14020, level 2

#### Pack A
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

#### Pack B
### Level 2 (sense 14020, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "aroma",
  "pronunciation": "uh-ROH-muh",
  "correct_definition": "A pleasant, distinctive smell, often of food or drink.",
  "options": [
    "A pleasant, distinctive smell, often of food or drink.",
    "To be unsuccessful in achieving a goal or completing a task.",
    "To cut or tear something into small, thin pieces, often using a tool or by pulling.",
    "A set of connected parts that form a complex whole."
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
        "A long, flat piece of material used for building.",
        "To produce a baby from the body; to bring a new life into the world.",
        "a scientific study of materials to understand their properties or behavior.",
        "A pleasant, distinctive smell, often of food or drink."
      ],
      "correct_answer": "A pleasant, distinctive smell, often of food or drink."
    }
  }
}
```

---

## sense 14020, level 3

#### Pack A
### Level 3 (sense 14020, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___ of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aroma of rising dough.",
  "correct_answer": "aroma",
  "options": [
    "smoke",
    "taste",
    "warmth",
    "aroma"
  ],
  "explanation": "Correct: fits the context of a pleasant smell from baking dough filling the shop.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Different spices create a wonderful ___ when they are heated in the pan.",
  "original_sentence": "Different spices create a wonderful aroma when they are heated in the pan.",
  "correct_answer": "aroma",
  "options": [
    "texture",
    "dish",
    "aroma",
    "recipe"
  ],
  "explanation": "The correct target word that naturally completes the sentence.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```

#### Pack B
### Level 3 (sense 14020, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___ of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aroma of rising dough.",
  "correct_answer": "aroma",
  "options": [
    "noise",
    "taste",
    "aroma",
    "sight"
  ],
  "explanation": "Correct. 'Aroma' fits the context of a pleasant smell from rising dough.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Sweet floral ___ filled the garden during the warm spring evening.",
  "original_sentence": "Sweet floral aromas filled the garden during the warm spring evening.",
  "correct_answer": "aromas",
  "options": [
    "sounds",
    "aromas",
    "views",
    "touches"
  ],
  "explanation": "Correct. 'Aromas' fits the context of multiple floral smells filling the garden.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aromas"
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The compost is deemed mature when it has cooled, turned a uniform dark brown, and possesses an earthy ___, free from any discernible food scrap remnants.",
  "original_sentence": "The compost is deemed mature when it has cooled, turned a uniform dark brown, and possesses an earthy aroma, free from any discernible food scrap remnants.",
  "correct_answer": "aroma",
  "base_form": "aroma",
  "form_label": "singular",
  "options": [
    "aromatic",
    "aroma",
    "aromas",
    "aromatically"
  ],
  "explanation": "Correct singular form fitting the context 'an earthy aroma'.",
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The sudden ___ of burning wood alerted them to the campfire.",
  "original_sentence": "The sudden aroma of burning wood alerted them to the campfire.",
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The sudden ___ of burning wood alerted them to the campfire.",
  "original_sentence": "The sudden aroma of burning wood alerted them to the campfire.",
  "correct_answer": "aromas",
  "base_form": "aroma",
  "form_label": "plural",
  "options": [
    "aromass",
    "aroma",
    "aromas",
    "aromatics"
  ],
  "explanation": "Correct plural form fitting the context 'Sweet floral aromas'.",
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
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
