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


## sense 13898, level 2

#### Pack A
### Level 2 (sense 13898, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "coffee bean",
  "pronunciation": "KAW-fee been",
  "correct_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "options": [
    "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
    "kind and gentle; not dangerous",
    "A large number, especially of people.",
    "Causing or tending to cause disruption, especially to normal activities or processes."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "coffee bean",
  "pronunciation": "KAW-fee been",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "in a way that is suggested but not directly stated",
        "the force pulling an object down because of gravity.",
        "relating to or used for measuring",
        "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee."
      ],
      "correct_answer": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13898, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "coffee bean",
  "pronunciation": "ko-fee been",
  "correct_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "options": [
    "Made smaller in amount, size, or degree.",
    "A word or phrase used to describe a specific idea, especially in a particular field or subject.",
    "The ability to grasp the meaning or significance of something.",
    "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "coffee bean",
  "pronunciation": "ko-fee been",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To cause something to spread, increase, or be transmitted, especially widely.",
        "To attempt to deal with a problem or difficult task.",
        "To make something by heating and hitting metal.",
        "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee."
      ],
      "correct_answer": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee."
    }
  }
}
```

---

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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "This is a ___.",
  "original_sentence": "This is a coffee bean.",
  "correct_answer": "This is a coffee bean.",
  "options": [
    "This is a coffee drink.",
    "This is a coffee leaf.",
    "This is a coffee bean.",
    "This is a coffee cup."
  ],
  "explanation": "Correct usage identifying the object.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 4

#### Pack A
### Level 4 (sense 13898, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She examined the raw ___ carefully before putting it into the small grinder.",
  "original_sentence": "She examined the raw coffee bean carefully before putting it into the small grinder.",
  "target_word": "coffee bean",
  "word": "coffee bean",
  "answer": {
    "accepted": [
      "coffee bean",
      "coffee beans"
    ],
    "accepted_normalized": [
      "coffee bean",
      "coffee beans"
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
  "sentence_with_blank": "She examined the raw ___ carefully before putting it into the small grinder.",
  "original_sentence": "She examined the raw coffee bean carefully before putting it into the small grinder.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beanning",
    "coffee beans",
    "coffee beaned",
    "coffee bean"
  ],
  "explanation": "singular",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "After grinding every ___, she poured hot water over the brown powder.",
  "original_sentence": "After grinding every coffee bean, she poured hot water over the brown powder.",
  "target_word": "coffee bean",
  "word": "coffee bean",
  "answer": {
    "accepted": [
      "coffee bean",
      "coffee beans"
    ],
    "accepted_normalized": [
      "coffee bean",
      "coffee beans"
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
  "sentence_with_blank": "After grinding every ___, she poured hot water over the brown powder.",
  "original_sentence": "After grinding every coffee bean, she poured hot water over the brown powder.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beans",
    "coffee beaned",
    "coffee bean",
    "coffee beaning"
  ],
  "explanation": "singular",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 4 (sense 13898, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She examined each ___ carefully before putting them into the roaster.",
  "original_sentence": "She examined each coffee bean carefully before putting them into the roaster.",
  "target_word": "coffee bean",
  "word": "coffee bean",
  "answer": {
    "accepted": [
      "coffee bean",
      "coffee beans"
    ],
    "accepted_normalized": [
      "coffee bean",
      "coffee beans"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Finding the best ___ for his morning drink became his new hobby.",
  "original_sentence": "Finding the best coffee bean for his morning drink became his new hobby.",
  "target_word": "coffee bean",
  "word": "coffee bean",
  "answer": {
    "accepted": [
      "coffee bean",
      "coffee beans"
    ],
    "accepted_normalized": [
      "coffee bean",
      "coffee beans"
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

## sense 13898, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 13898, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They dropped a single coffee bean onto the wooden table to see how it looked.",
      "is_correct": true
    },
    {
      "text": "They dropped a single coffee bean onto the floor to plant a forest instantly.",
      "is_correct": false
    },
    {
      "text": "They dropped a single coffee bean into the ocean to feed the fish.",
      "is_correct": false
    },
    {
      "text": "They dropped a single coffee bean onto the page to write a letter with it.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: Coffee beans are not used as fish food; this violates real-world knowledge. Functional error: Coffee beans cannot be used as writing instruments. Causal error: Dropping a bean does not instantly create a forest.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Holding a small coffee bean in his palm, he wondered how it became a hot drink.",
      "is_correct": true
    },
    {
      "text": "Holding a small coffee bean in his palm, he used it to unlock his door.",
      "is_correct": false
    },
    {
      "text": "Holding a small coffee bean in his palm, he threw it into space.",
      "is_correct": false
    },
    {
      "text": "Holding a small coffee bean in his palm, he ate it like a grape.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: Raw or roasted beans are not typically eaten whole like fruit due to hardness and bitterness. Pragmatic/Scale error: Highly unlikely action for a casual observer. Functional error: A bean cannot function as a key.",
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
      "text": "Each single coffee bean holds a rich and deep flavor inside its hard shell.",
      "is_correct": true
    },
    {
      "text": "This is a coffee bean.",
      "is_correct": true
    },
    {
      "text": "She examined the raw coffee bean carefully before putting it into the small grinder.",
      "is_correct": true
    },
    {
      "text": "She bought a bag of coffee beans from the store, but she forgot to grind the coffee bean before brewing.",
      "is_correct": false,
      "error_description": "The sentence shifts from plural 'coffee beans' in the first clause to singular 'coffee bean' in the second clause without justification. Since she is grinding the contents of the bag, the plural form should be maintained for consistency and logical agreement."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Finding a rare coffee bean from another country was exciting for the young collector.",
      "is_correct": true
    },
    {
      "text": "Holding a small coffee bean in his palm, he wondered how it became a hot drink.",
      "is_correct": true
    },
    {
      "text": "The farmer picked many coffee beans from the tree and put it in a basket.",
      "is_correct": false,
      "error_description": "Pronoun agreement error: The plural noun phrase 'coffee beans' requires the plural object pronoun 'them', not the singular 'it'."
    },
    {
      "text": "After grinding every coffee bean, she poured hot water over the brown powder.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13898, level 9

#### Pack A
### Level 9 (sense 13898, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The artisan roasted each coffee bean until it turned a rich brown color."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The artisan roasted each coffee bean until it turned a rich brown color.",
  "chunks": [
    "The artisan",
    "roasted",
    "each coffee bean",
    "until it turned a rich brown color"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "each coffee bean",
    "roasted",
    "The artisan",
    "until it turned a rich brown color"
  ],
  "target_word": "coffee bean",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Every coffee bean has a unique aroma depending on where it was grown."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Every coffee bean has a unique aroma depending on where it was grown.",
  "chunks": [
    "Every coffee bean",
    "has",
    "a unique aroma depending on where it was grown"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a unique aroma depending on where it was grown",
    "has",
    "Every coffee bean"
  ],
  "target_word": "coffee bean",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13898, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He picked up a roasted coffee bean and tasted it to check the overall quality."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He picked up a roasted coffee bean and tasted it to check the overall quality.",
  "chunks": [
    "He picked up",
    "a roasted coffee bean",
    "and tasted it to check the overall quality"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "and tasted it to check the overall quality",
    "a roasted coffee bean",
    "He picked up"
  ],
  "target_word": "coffee bean",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They dropped a single coffee bean onto the wooden table to see how it looked."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They dropped a single coffee bean onto the wooden table to see how it looked.",
  "chunks": [
    "They dropped",
    "a single coffee bean",
    "onto the wooden table",
    "to see how it looked"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "They dropped",
    "onto the wooden table",
    "to see how it looked",
    "a single coffee bean"
  ],
  "target_word": "coffee bean",
  "chunk_count": 4
}
```

---

## sense 13900, level 2

#### Pack A
### Level 2 (sense 13900, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "correct_definition": "To select or choose something from a group.",
  "options": [
    "To form a circle or be on all sides of something or someone.",
    "To select or choose something from a group.",
    "Talent is a natural ability or skill that someone has.",
    "To create clothing by sewing or assembling fabric."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To question someone or something thoroughly, often in an official or formal way.",
        "To select or choose something from a group.",
        "Based on or guided by the analysis of data rather than intuition or personal experience.",
        "To appear as a large, often threatening shape or object."
      ],
      "correct_answer": "To select or choose something from a group."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13900, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "correct_definition": "To select or choose something from a group.",
  "options": [
    "A person or thing that is preferred above others.",
    "To select or choose something from a group.",
    "To begin sleeping; to enter a state of sleep.",
    "The act of deliberately staying away from something or preventing something from happening."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Dust is fine particles of matter, such as dirt or pollen, that settle on surfaces.",
        "To select or choose something from a group.",
        "The front part of your body between your neck and your belly.",
        "to move or flow at a higher speed."
      ],
      "correct_answer": "To select or choose something from a group."
    }
  }
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
    "pick",
    "invent",
    "consume",
    "ignore"
  ],
  "explanation": "Correct: fits the context of selecting a specific drug therapy from options.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

---

## sense 13900, level 4

#### Pack A
### Level 4 (sense 13900, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "target_word": "pick",
  "word": "pick",
  "answer": {
    "accepted": [
      "pick",
      "picks",
      "picked",
      "picking"
    ],
    "accepted_normalized": [
      "pick",
      "picks",
      "picked",
      "picking"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Can you help me ___ a good book from the library shelf?",
  "original_sentence": "Can you help me pick a good book from the library shelf?",
  "target_word": "pick",
  "word": "pick",
  "answer": {
    "accepted": [
      "pick",
      "picks",
      "picked",
      "picking"
    ],
    "accepted_normalized": [
      "pick",
      "picks",
      "picked",
      "picking"
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
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "target_word": "pick",
  "word": "pick",
  "answer": {
    "accepted": [
      "pick",
      "picks",
      "picked",
      "picking"
    ],
    "accepted_normalized": [
      "pick",
      "picks",
      "picked",
      "picking"
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
  "sentence_with_blank": "People ___ the beans.",
  "original_sentence": "People pick the beans.",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "base form",
  "options": [
    "picked",
    "pick",
    "picking",
    "picks"
  ],
  "explanation": "Correct. The subject 'People' is plural, so the base form is used in the present simple tense.",
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
    "pickly",
    "picker",
    "pickful"
  ],
  "correct_answer": "picker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. 'Picker' is a real noun derived from 'pick' (one who picks)."
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He always takes a long time to ___ what he wants to eat at a restaurant.",
  "original_sentence": "He always takes a long time to pick what he wants to eat at a restaurant.",
  "target_word": "pick",
  "word": "pick",
  "answer": {
    "accepted": [
      "pick",
      "picks",
      "picked",
      "picking"
    ],
    "accepted_normalized": [
      "pick",
      "picks",
      "picked",
      "picking"
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
  "sentence_with_blank": "He always takes a long time to ___ what he wants to eat at a restaurant.",
  "original_sentence": "He always takes a long time to pick what he wants to eat at a restaurant.",
  "correct_answer": "pick",
  "base_form": "pick",
  "form_label": "base form",
  "options": [
    "picks",
    "picked",
    "picking",
    "pick"
  ],
  "explanation": "Correct. The subject 'He' is third-person singular, but the sentence uses 'takes time to [verb]', so the infinitive/base form 'pick' is required after 'to'.",
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "He always takes a long time to ___ what he wants to eat at a restaurant.",
  "original_sentence": "He always takes a long time to pick what he wants to eat at a restaurant.",
  "required_pos": "adjective",
  "options": [
    "pickation",
    "pickive",
    "picky",
    "pickness"
  ],
  "correct_answer": "picky",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. 'Picky' is a real adjective meaning hard to please."
    }
  }
}
```

---

## sense 13900, level 6

#### Pack A
### Level 6 (sense 13900, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "pick",
  "relation": "synonym",
  "options": [
    "drop",
    "choose",
    "ignore",
    "reject"
  ],
  "correct_answer": "choose",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To select or choose something from a group.",
      "explanation": "Correct. 'Choose' is a direct synonym for 'pick' in the sense of selecting."
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The heavy rain began to pick on the roof tiles throughout the night.",
      "is_correct": false
    },
    {
      "text": "They were asked to pick three options from the list of available activities.",
      "is_correct": true
    },
    {
      "text": "He tried to pick the heavy sofa across the living room floor.",
      "is_correct": false
    },
    {
      "text": "She will pick her teeth with a fork during the formal dinner.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect usage: 'Pick' does not mean to strike or hit repeatedly; this confuses it with 'pelt' or 'beat'. Incorrect usage: 'Pick' implies selection, not physical lifting or moving; this confuses it with 'lift' or 'drag'. Incorrect usage: While 'pick at' exists, using a fork to 'pick teeth' is pragmatically inappropriate and semantically confused with 'clean'.",
  "target_word": "pick"
}
```

#### Pack B
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

---
