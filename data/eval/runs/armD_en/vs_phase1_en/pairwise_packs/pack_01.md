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


## sense 13898, level 3

#### Pack A
### Level 3 (sense 13898, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "This is a ___.",
  "original_sentence": "This is a coffee bean.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee shop",
    "coffee bean",
    "coffee cup",
    "coffee blend"
  ],
  "explanation": "Correct completion: refers to the seed of the coffee plant, fitting the context of identifying the object.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "You can smell the rich scent whenever a fresh ___ is crushed.",
  "original_sentence": "You can smell the rich scent whenever a fresh coffee bean is crushed.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee leaf",
    "coffee cup",
    "coffee extract",
    "coffee bean"
  ],
  "explanation": "Correct completion. The sentence describes crushing a fresh seed to release its characteristic scent.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 3 (sense 13898, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "That dark brown ___ looks ready for grinding.",
  "original_sentence": "That dark brown coffee bean looks ready for grinding.",
  "correct_answer": "coffee bean",
  "options": [
    "chocolate bar",
    "coffee bean",
    "sugar cube",
    "tea leaf"
  ],
  "explanation": "Correct: Fits the context perfectly, as a dark brown, roasted seed is ready to be ground.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 4

#### Pack A
### Level 4 (sense 13898, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She examined each ___ carefully before putting them into the roaster.",
  "original_sentence": "She examined each coffee bean carefully before putting them into the roaster.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beans'",
    "coffee bean's",
    "coffee beans",
    "coffee bean"
  ],
  "explanation": "singular form is required by the distributive determiner 'each'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 4 (sense 13898, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She examined the raw ___ carefully before roasting it.",
  "original_sentence": "She examined the raw coffee bean carefully before roasting it.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee bean",
    "coffee bean's",
    "coffee beans'",
    "coffee beans"
  ],
  "explanation": "singular form agrees with the singular pronoun 'it' later in the sentence",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He showed his friends how to crush a roasted ___.",
  "original_sentence": "He showed his friends how to crush a roasted coffee bean.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beans",
    "coffee bean",
    "coffee bean's",
    "coffee beans'"
  ],
  "explanation": "singular noun is required by the preceding indefinite article 'a'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 6

#### Pack A
### Level 6 (sense 13898, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The coffee bean drove to the supermarket to buy some milk.",
      "is_correct": false
    },
    {
      "text": "She whispered a secret to the coffee bean because it was her best friend.",
      "is_correct": false
    },
    {
      "text": "They dropped a single coffee bean onto the wooden table.",
      "is_correct": true
    },
    {
      "text": "The coffee bean brewed a perfect cup of espresso in just thirty seconds.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: A single seed cannot physically brew a cup of coffee on its own without being ground and processed. Semantically inappropriate: A coffee bean is an inanimate plant seed and cannot listen, understand, or be a friend. Pragmatically inappropriate: A coffee bean is an inanimate object and lacks the physical ability to drive a vehicle.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He wore the giant coffee bean around his neck as a formal piece of jewelry to the black-tie gala.",
      "is_correct": false
    },
    {
      "text": "The mechanic used a heavy coffee bean to hammer the nail into the wooden board.",
      "is_correct": false
    },
    {
      "text": "The small shop sells every type of exotic coffee bean imaginable.",
      "is_correct": true
    },
    {
      "text": "She planted the roasted coffee bean in the garden, expecting it to sprout into a new bush by tomorrow.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: roasting a coffee bean kills the seed, making it biologically impossible for it to sprout. Semantically inappropriate: a coffee bean is a small, fragile seed and lacks the physical mass or hardness to be used as a hammer. Pragmatically inappropriate: coffee beans are small agricultural seeds, not large gemstones suitable for formal jewelry.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 6 (sense 13898, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The coffee bean flew across the ocean using its large, feathered wings.",
      "is_correct": false
    },
    {
      "text": "The coffee bean barked loudly at the stranger walking past the house.",
      "is_correct": false
    },
    {
      "text": "She used the coffee bean to chop down the tall tree in the forest.",
      "is_correct": false
    },
    {
      "text": "Every coffee bean has a unique aroma depending on where it was grown.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: attributes animal behavior (barking) to an inanimate plant seed. pragmatic: describes a physically impossible action, as a small seed cannot be used as an axe to chop down a tree. semantic: attributes biological features of a bird (feathered wings, flying) to a plant seed.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "A dark coffee bean usually produces a stronger flavor in your cup.",
      "is_correct": true
    },
    {
      "text": "She used a heavy coffee bean to hammer the nail deep into the solid oak wall.",
      "is_correct": false
    },
    {
      "text": "He planted a roasted coffee bean in the garden, expecting it to sprout into a new plant by tomorrow.",
      "is_correct": false
    },
    {
      "text": "The mechanic poured a liquid coffee bean directly into the car's engine to lubricate the moving parts.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: roasted coffee beans are dead and cannot germinate or sprout. Pragmatically inappropriate: a coffee bean is small, light, and fragile, making it completely useless as a hammer. Semantically inappropriate: a coffee bean is a solid seed, not a liquid lubricant that can be poured.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 7

#### Pack A
### Level 7 (sense 13898, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He dropped a single coffee bean onto the wooden table.",
      "is_correct": true
    },
    {
      "text": "She examined each coffee bean carefully before putting them into the roaster.",
      "is_correct": true
    },
    {
      "text": "She bought three coffee bean at the store.",
      "is_correct": false,
      "error_description": "After a cardinal number such as 'three', a countable noun must take the plural form. Therefore, 'coffee bean' should be corrected to 'coffee beans'."
    },
    {
      "text": "This is a coffee bean.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13898, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "This is a coffee bean.",
      "is_correct": true
    },
    {
      "text": "She examined the raw coffee bean carefully before roasting it.",
      "is_correct": true
    },
    {
      "text": "Every single coffee bean contains rich flavors and aromas.",
      "is_correct": true
    },
    {
      "text": "She put three coffee bean into the grinder.",
      "is_correct": false,
      "error_description": "The noun 'coffee bean' is a countable noun and must be pluralized when referring to more than one, especially after a quantifier like 'three'."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He showed his friends how to crush a roasted coffee bean.",
      "is_correct": true
    },
    {
      "text": "The small shop sells every type of exotic coffee bean imaginable.",
      "is_correct": true
    },
    {
      "text": "He bought a bag of freshly roasted coffee bean from the local market.",
      "is_correct": false,
      "error_description": "The noun 'coffee bean' is countable and must be pluralized as 'coffee beans' when referring to multiple beans contained in a bag."
    },
    {
      "text": "That dark brown coffee bean looks ready for grinding.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13900, level 3

#### Pack A
### Level 3 (sense 13900, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "When doctors use this information, they can ___ a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
  "original_sentence": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
  "correct_answer": "pick",
  "options": [
    "pick",
    "nominate",
    "pluck",
    "gather"
  ],
  "explanation": "Correct word: fits the context of selecting a specific drug therapy from available options.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everyone wanted to ___ the best seat on the bus.",
  "original_sentence": "Everyone wanted to pick the best seat on the bus.",
  "correct_answer": "pick",
  "options": [
    "eat",
    "pluck",
    "pick",
    "elect"
  ],
  "explanation": "Correct: naturally means to select or choose the best seat.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

#### Pack B
### Level 3 (sense 13900, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "When doctors use this information, they can ___ a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
  "original_sentence": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
  "correct_answer": "pick",
  "options": [
    "grab",
    "pick",
    "swallow",
    "invent"
  ],
  "explanation": "Correct: 'Pick' means to select or choose, which perfectly fits the context of doctors choosing a specific drug therapy.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They were trying to ___ a reliable team captain before the big match started.",
  "original_sentence": "They were trying to pick a reliable team captain before the big match started.",
  "correct_answer": "pick",
  "options": [
    "pick",
    "gaze",
    "build",
    "follow"
  ],
  "explanation": "Correct: means to select or choose someone for a specific role.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

---

## sense 13900, level 4

#### Pack A
### Level 4 (sense 13900, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "plural present",
  "options": [
    "pick",
    "picks",
    "picked",
    "picking"
  ],
  "explanation": "plural present form agrees with the plural subject 'People'",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "required_pos": "noun",
  "options": [
    "pickal",
    "pickation",
    "picker",
    "pickment"
  ],
  "correct_answer": "picker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agent noun formed by adding -er to the verb"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Can you help me ___ a good book from the library shelf?",
  "original_sentence": "Can you help me pick a good book from the library shelf?",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "bare infinitive",
  "options": [
    "picked",
    "picking",
    "pick",
    "picks"
  ],
  "explanation": "the bare infinitive is required after the verb 'help' plus an object",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

#### Pack B
### Level 4 (sense 13900, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "base form",
  "options": [
    "pick",
    "picks",
    "picking",
    "picked"
  ],
  "explanation": "base form agrees with the plural subject 'People' in the present simple",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "required_pos": "noun",
  "options": [
    "pickment",
    "pickal",
    "picker",
    "pickation"
  ],
  "correct_answer": "picker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agent noun formed with -er"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "If you had to ___ one favorite song, which one would it be?",
  "original_sentence": "If you had to pick one favorite song, which one would it be?",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "base form",
  "options": [
    "picking",
    "picked",
    "pick",
    "picks"
  ],
  "explanation": "base form is required after the semi-modal 'had to'",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "If you had to ___ one favorite song, which one would it be?",
  "original_sentence": "If you had to pick one favorite song, which one would it be?",
  "required_pos": "noun",
  "options": [
    "pickation",
    "picker",
    "pickment",
    "pickal"
  ],
  "correct_answer": "picker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agent noun formed with -er"
    }
  }
}
```

---

## sense 13900, level 6

#### Pack A
### Level 6 (sense 13900, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The blindfolded man picked the red shirt from the closet by looking closely at the colors.",
      "is_correct": false
    },
    {
      "text": "The solitary prisoner picked a fellow inmate to play chess with, despite being locked in an isolated cell alone.",
      "is_correct": false
    },
    {
      "text": "The newborn baby picked the most advanced calculus textbook to read for pleasure.",
      "is_correct": false
    },
    {
      "text": "If you had to pick one movie to watch tonight, which one would you choose?",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: newborns lack the cognitive and physical ability to read or select textbooks. Pragmatically inappropriate: contradicts the physical reality of being in solitary confinement where no other inmates are present. Pragmatically inappropriate: being blindfolded prevents a person from looking closely at colors to make a visual selection.",
  "target_word": "pick"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "relation": "antonym",
  "options": [
    "consider",
    "arrange",
    "reject",
    "examine"
  ],
  "correct_answer": "reject",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To select or choose something from a group.",
      "explanation": "antonym of the target sense: to refuse to select rather than choose from a group"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The refrigerator decided to pick the milk to keep it fresh.",
      "is_correct": false
    },
    {
      "text": "He tried to pick the water from the river with his bare hands.",
      "is_correct": false
    },
    {
      "text": "We need to pick a date for our group meeting next week.",
      "is_correct": true
    },
    {
      "text": "I will pick the nose of my boss during the formal interview.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: picking one's nose is a highly offensive and socially unacceptable behavior in a formal setting. Semantically inappropriate: inanimate objects like refrigerators lack the cognitive agency required to 'select' or 'choose' items. Semantically inappropriate: the verb 'pick' requires discrete, selectable items, not a continuous liquid like water.",
  "target_word": "pick"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "relation": "antonym",
  "options": [
    "decide",
    "combine",
    "arrange",
    "reject"
  ],
  "correct_answer": "reject",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To select or choose something from a group.",
      "explanation": "antonym of the selection sense, meaning to refuse to choose"
    }
  }
}
```

#### Pack B
### Level 6 (sense 13900, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "relation": "antonym",
  "options": [
    "reject",
    "sort",
    "gather",
    "examine"
  ],
  "correct_answer": "reject",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To select or choose something from a group.",
      "explanation": "antonym: to refuse or decline rather than select from available options"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "relation": "antonym",
  "options": [
    "arrange",
    "sort",
    "reject",
    "gather"
  ],
  "correct_answer": "reject",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To select or choose something from a group.",
      "explanation": "antonym: to refuse to select or accept, the opposite of choosing from a group"
    }
  }
}
```

---

## sense 13900, level 7

#### Pack A
### Level 7 (sense 13900, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students can pick their favorite topics for the upcoming history project.",
      "is_correct": true
    },
    {
      "text": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
      "is_correct": true
    },
    {
      "text": "She wants pick the blue dress for the party.",
      "is_correct": false,
      "error_description": "The verb 'want' requires the infinitive marker 'to' to introduce the verb 'pick'. Omitting 'to' creates an incorrect verb complement structure."
    },
    {
      "text": "People pick the beans.",
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
      "text": "She decided pick the blue dress for the school dance.",
      "is_correct": false,
      "error_description": "The verb 'decide' requires a to-infinitive complement. The preposition 'to' is missing before the target verb 'pick'."
    },
    {
      "text": "Can you help me pick a good book from the library shelf?",
      "is_correct": true
    },
    {
      "text": "Everyone wanted to pick the best seat on the bus.",
      "is_correct": true
    },
    {
      "text": "We need to pick a date for our group meeting next week.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13900, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "People pick the beans.",
      "is_correct": true
    },
    {
      "text": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
      "is_correct": true
    },
    {
      "text": "She picked to buy the blue dress instead of the red one.",
      "is_correct": false,
      "error_description": "The verb 'pick' is not typically followed by a to-infinitive. When expressing a decision to do an action, 'choose' is the correct verb to use with the infinitive, whereas 'pick' should be followed directly by a noun or noun phrase."
    },
    {
      "text": "You should pick a topic that really interests you for the class presentation tomorrow.",
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
      "text": "They picked to go to the beach for their summer vacation.",
      "is_correct": false,
      "error_description": "The verb 'pick' cannot be directly followed by an infinitive (to + verb). When expressing a choice of action, use 'choose' or 'decide' with an infinitive, or use 'pick' with a direct noun object."
    },
    {
      "text": "They were trying to pick a reliable team captain before the big match started.",
      "is_correct": true
    },
    {
      "text": "We need to pick a date for our upcoming club meeting by this Friday.",
      "is_correct": true
    },
    {
      "text": "If you had to pick one favorite song, which one would it be?",
      "is_correct": true
    }
  ]
}
```

---

## sense 13902, level 3

#### Pack A
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bags ___ big boats.",
  "original_sentence": "These bags go on big boats.",
  "correct_answer": "go on",
  "options": [
    "fly past",
    "go into",
    "go on",
    "ride on"
  ],
  "explanation": "Correct: fits the context of items being placed onto the surface of the boats.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "After finishing the first task, they had to ___ to the next one.",
  "original_sentence": "After finishing the first task, they had to go on to the next one.",
  "correct_answer": "go on",
  "options": [
    "listen",
    "holler",
    "return",
    "go on"
  ],
  "explanation": "Correct: matches the target word and fits the context of proceeding to the next task.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

#### Pack B
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with the presentation now.",
  "original_sentence": "Let us go on with the presentation now.",
  "correct_answer": "go on",
  "options": [
    "go up",
    "go off",
    "go out",
    "go on"
  ],
  "explanation": "Correct: 'go on' correctly completes the phrasal verb meaning to proceed with the presentation.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He paused for a moment before deciding to ___ with his speech.",
  "original_sentence": "He paused for a moment before deciding to go on with his speech.",
  "correct_answer": "go on",
  "options": [
    "go off",
    "go on",
    "go up",
    "go for"
  ],
  "explanation": "Correct: 'go on' correctly means to proceed or continue with the speech after a pause.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---

## sense 13902, level 4

#### Pack A
### Level 4 (sense 13902, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with our history project after lunch.",
  "original_sentence": "Let us go on with our history project after lunch.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "bare infinitive",
  "options": [
    "going on",
    "goes on",
    "went on",
    "go on"
  ],
  "explanation": "bare infinitive is required after the causative verb 'let' with an object",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He took a deep breath before he would ___ with the difficult task.",
  "original_sentence": "He took a deep breath before he would go on with the difficult task.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "bare infinitive",
  "options": [
    "went on",
    "go on",
    "going on",
    "goes on"
  ],
  "explanation": "bare infinitive is required after the modal auxiliary 'would'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

#### Pack B
### Level 4 (sense 13902, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with our history project after a short break.",
  "original_sentence": "Let us go on with our history project after a short break.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "go on",
    "going on",
    "goes on",
    "went on"
  ],
  "explanation": "base form is required after the causative verb 'let'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He paused for a second before he chose to ___.",
  "original_sentence": "He paused for a second before he chose to go on.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "went on",
    "going on",
    "goes on",
    "go on"
  ],
  "explanation": "base form required after the infinitive marker 'to'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---
