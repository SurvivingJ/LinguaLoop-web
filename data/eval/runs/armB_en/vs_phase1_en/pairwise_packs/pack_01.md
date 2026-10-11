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
  "sentence_with_blank": "That tiny ___ smells surprisingly sweet when crushed.",
  "original_sentence": "That tiny coffee bean smells surprisingly sweet when crushed.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee bean",
    "coffee cup",
    "coffee shop",
    "coffee bag"
  ],
  "explanation": "Correct: Fits the context of a small, crushable object with a sweet smell.",
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
  "sentence_with_blank": "She examined each ___ carefully before buying the bag.",
  "original_sentence": "She examined each coffee bean carefully before buying the bag.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee bean",
    "coffee beans'",
    "coffee bean's",
    "coffee beans"
  ],
  "explanation": "singular noun required after the determiner 'each'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He placed one roasted ___ into the small grinder.",
  "original_sentence": "He placed one roasted coffee bean into the small grinder.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beans",
    "coffee bean's",
    "coffee bean",
    "coffee beans'"
  ],
  "explanation": "singular noun required by the quantifier 'one'",
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
      "text": "She married a coffee bean last summer.",
      "is_correct": false
    },
    {
      "text": "The coffee bean solved the complex math problem.",
      "is_correct": false
    },
    {
      "text": "The farmer picked a fresh coffee bean from the branch.",
      "is_correct": true
    },
    {
      "text": "The coffee bean drove his car to the office.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: A coffee bean is an inanimate object and cannot perform actions like driving. Semantic error: Marriage is a social contract between humans, not involving plant seeds. Pragmatic error: A coffee bean lacks the cognitive ability to solve mathematical problems.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She wrote a long email using a coffee bean.",
      "is_correct": false
    },
    {
      "text": "The coffee bean solved the complex math problem.",
      "is_correct": false
    },
    {
      "text": "The coffee bean drove his car to the office.",
      "is_correct": false
    },
    {
      "text": "A raw coffee bean usually has a pale green color.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: A seed is an inanimate object and cannot perform actions like driving. Semantically inappropriate: A coffee bean is not a writing instrument or tool for communication. Pragmatically inappropriate: A seed lacks the cognitive ability to solve problems.",
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
      "text": "She bought a bag of coffee beans but forgot to grind the coffee bean before brewing.",
      "is_correct": false,
      "error_description": "The sentence shifts from plural 'coffee beans' in the first clause to singular 'coffee bean' in the second, creating a number agreement inconsistency. Since she is grinding the contents of the bag, the plural form is required for logical consistency."
    },
    {
      "text": "She examined each coffee bean carefully before buying the bag.",
      "is_correct": true
    },
    {
      "text": "Every single coffee bean contains rich flavors and aromas.",
      "is_correct": true
    },
    {
      "text": "This is a coffee bean.",
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
      "text": "He placed one roasted coffee bean into the small grinder.",
      "is_correct": true
    },
    {
      "text": "A raw coffee bean usually has a pale green color.",
      "is_correct": true
    },
    {
      "text": "That tiny coffee bean smells surprisingly sweet when crushed.",
      "is_correct": true
    },
    {
      "text": "The coffee bean are too dark for this blend.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The plural verb 'are' requires the plural subject 'coffee beans', not the singular 'coffee bean'."
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
    "consume",
    "invent",
    "pick",
    "ignore"
  ],
  "explanation": "Correct: fits the context of selecting a specific drug therapy from options.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He had to ___ three team members for the upcoming debate competition.",
  "original_sentence": "He had to pick three team members for the upcoming debate competition.",
  "correct_answer": "pick",
  "options": [
    "pick",
    "consume",
    "ignore",
    "invent"
  ],
  "explanation": "Correct: 'Pick' means to select specific individuals from a group, fitting the context of choosing team members.",
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
    "picks",
    "pick",
    "picking",
    "picked"
  ],
  "explanation": "base form agrees with the plural subject 'People'",
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
    "pickion",
    "pickal",
    "pickment",
    "picker"
  ],
  "correct_answer": "picker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the agent noun formed with -er"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "If you had to ___ one gift, which would you choose?",
  "original_sentence": "If you had to pick one gift, which would you choose?",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "base form",
  "options": [
    "picks",
    "pick",
    "picking",
    "picked"
  ],
  "explanation": "base form is required after the modal auxiliary 'had to'",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "If you had to ___ one gift, which would you choose?",
  "original_sentence": "If you had to pick one gift, which would you choose?",
  "required_pos": "noun",
  "options": [
    "pickal",
    "pickion",
    "choice",
    "pickment"
  ],
  "correct_answer": "choice",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established nominalisation of pick"
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I need to pick some water to drink.",
      "is_correct": false
    },
    {
      "text": "She tried to pick the truth from the air.",
      "is_correct": false
    },
    {
      "text": "She will pick the best photo for the school magazine cover.",
      "is_correct": true
    },
    {
      "text": "The heavy rain will pick the roof off the house.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'pick' implies careful selection by an agent, not the physical force of weather removing an object. Semantically inappropriate: 'pick' requires discrete, countable items to select from, not uncountable liquids like water. Semantically inappropriate: 'truth' is an abstract concept that cannot be physically selected or harvested from the environment like an object.",
  "target_word": "pick"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Many teenagers prefer to pick their own clothes when shopping with parents.",
      "is_correct": true
    },
    {
      "text": "The heavy rain will pick the roof off the house if it continues.",
      "is_correct": false
    },
    {
      "text": "He managed to pick the car into the garage after the engine failed.",
      "is_correct": false
    },
    {
      "text": "She tried to pick the truth out of his lie during the argument.",
      "is_correct": false
    }
  ],
  "explanation": "Inappropriate: 'Pick' implies careful selection, whereas removing a roof by force requires verbs like 'tear' or 'blow'. Inappropriate: Abstract concepts like 'truth' are usually 'extracted', 'discerned', or 'found', not physically 'picked' like an object. Inappropriate: 'Pick' does not mean to move or transport heavy machinery; verbs like 'push', 'tow', or 'drive' are required.",
  "target_word": "pick"
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
      "text": "She pick the red apple from the basket yesterday.",
      "is_correct": false,
      "error_description": "The sentence uses the time marker 'yesterday', which requires the past tense form of the verb. The base form 'pick' is incorrect here; it should be 'picked'."
    },
    {
      "text": "You should pick your favorite book from the shelf for our reading club.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13902, level 1

#### Pack A
### Level 1 (sense 13902, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "ipa": "/ɡoʊ ˈɒn/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "go in",
    "go on",
    "grow on",
    "gone"
  ],
  "correct_answer": "go on",
  "explanation": "Correct: exact transcription of the heard phrase.",
  "distractor_explanations": {
    "gone": "Near-homophone: 'go on' spoken quickly reduces to /ɡɒn/, sounding identical to 'gone'.",
    "grow on": "Minimal pair: differs only in the initial consonant cluster /ɡr/ versus /ɡ/.",
    "go in": "Minimal pair: the second word differs only in the vowel sound /ɪ/ versus /ɒ/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13902, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "ipa": "/ɡoʊ ˈɒn/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "go on",
    "grown",
    "groan",
    "gone"
  ],
  "correct_answer": "go on",
  "explanation": "Correct: matches the target phrase exactly.",
  "distractor_explanations": {
    "gone": "Phonetic distractor: shares the initial /ɡɒ/ sound but lacks the second syllable and final nasal.",
    "groan": "Near-homophone: similar vowel and final consonant /n/, but differs in the medial consonant cluster /r/ vs space.",
    "grown": "Rhyme/Near-homophone: rhymes with 'groan' and shares the /n/ ending, creating auditory confusion with the target's rhythm."
  },
  "distractor_source": "llm"
}
```

---

## sense 13902, level 3

#### Pack A
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let's ___ with the presentation now.",
  "original_sentence": "Let's go on with the presentation now.",
  "correct_answer": "go on",
  "options": [
    "go on",
    "finish",
    "stop",
    "delay"
  ],
  "explanation": "Correct: fits the context of proceeding with an activity after a pause or introduction.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Please ___ reading the story from where you stopped.",
  "original_sentence": "Please go on reading the story from where you stopped.",
  "correct_answer": "go on",
  "options": [
    "finish",
    "stop",
    "begin",
    "go on"
  ],
  "explanation": "Correct: fits the context of continuing an action (reading) from a specific point.",
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

---
