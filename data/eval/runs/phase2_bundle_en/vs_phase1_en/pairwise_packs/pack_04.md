# Pairwise review pack 04

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


## sense 13946, level 2

#### Pack A
### Level 2 (sense 13946, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-wey",
  "correct_definition": "at a great distance; a long way off",
  "options": [
    "to enter a place, especially without knocking or arranging a meeting",
    "To change the form, appearance, or structure of something.",
    "Very great in intensity, seriousness, or harshness.",
    "at a great distance; a long way off"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-wey",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A fact or event that is observed to exist or happen, especially one whose cause or explanation is in question.",
        "at a great distance; a long way off",
        "Discipline is the practice of training people to obey rules or a code of behavior, using punishment to correct disobedience.",
        "Done in a clever way."
      ],
      "correct_answer": "at a great distance; a long way off"
    }
  }
}
```

#### Pack B
### Level 2 (sense 13946, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "correct_definition": "at a great distance; a long way off",
  "options": [
    "A layer of rock or sand that holds water and allows it to flow, used as a water source.",
    "at a great distance; a long way off",
    "An expert is a person who has special skill or knowledge in a particular subject.",
    "Diversity is the state of having a variety of different elements, such as cultures, backgrounds, or types."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A capital is a big city where the government works.",
        "at a great distance; a long way off",
        "Trade is when you give something and get something else.",
        "In a way that causes a major, basic change."
      ],
      "correct_answer": "at a great distance; a long way off"
    }
  }
}
```

---

## sense 13946, level 4

#### Pack A
### Level 4 (sense 13946, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My best friend moved ___ last summer.",
  "original_sentence": "My best friend moved far away last summer.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
  "sentence_with_blank": "They live ___ in a small mountain village.",
  "original_sentence": "They live far away in a small mountain village.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
### Level 4 (sense 13946, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My best friend moved ___ last summer, and I miss her terribly.",
  "original_sentence": "My best friend moved far away last summer, and I miss her terribly.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
  "sentence_with_blank": "They dreamed of traveling to a mysterious island ___ across the ocean.",
  "original_sentence": "They dreamed of traveling to a mysterious island far away across the ocean.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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

## sense 13946, level 6

#### Pack A
### Level 6 (sense 13946, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "elsewhere",
    "abroad",
    "nearby",
    "ahead"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "genuine antonym: at a short distance rather than a great one"
    }
  }
}
```

#### Pack B
### Level 6 (sense 13946, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I have never traveled far away in my kitchen.",
      "is_correct": false
    },
    {
      "text": "The ant walked far away across the sugar cube.",
      "is_correct": false
    },
    {
      "text": "I have never traveled far away from my hometown.",
      "is_correct": true
    },
    {
      "text": "She blinked far away her tears.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic/Pragmatic error. One cannot travel a great distance within the confined space of a kitchen. Pragmatic scale error. 'Far away' implies a significant human-scale or geographic distance, inappropriate for microscopic movements on a small object. Syntactic/Valency error. 'Far away' is an adverb of place/distance, not a verb particle that can act transitively on 'tears'.",
  "target_word": "far away"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Even though he is far away, we still talk every weekend.",
      "is_correct": true
    },
    {
      "text": "He is far away in the same room as me.",
      "is_correct": false
    },
    {
      "text": "The thought was far away in his pocket.",
      "is_correct": false
    },
    {
      "text": "She ran far away the race.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic contradiction. One cannot be a great distance away while in the same room. Category error. Abstract concepts like thoughts cannot be located physically in pockets. Syntactic error. 'Far away' cannot take a direct object like 'the race'.",
  "target_word": "far away"
}
```

---

## sense 13946, level 9

#### Pack A
### Level 9 (sense 13946, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "She stared into space, her mind wandering far away."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She stared into space, her mind wandering far away.",
  "chunks": [
    "She stared",
    "into space",
    "her mind wandering far away"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "into space",
    "She stared",
    "her mind wandering far away"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "I have never traveled far away from my hometown."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "I have never traveled far away from my hometown.",
  "chunks": [
    "I",
    "have never traveled",
    "far away from my hometown"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "I",
    "far away from my hometown",
    "have never traveled"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13946, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "She spotted the hidden cabin nestled far away in the dense mountain forest."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She spotted the hidden cabin nestled far away in the dense mountain forest.",
  "chunks": [
    "She",
    "spotted",
    "the hidden cabin nestled far away in the dense mountain forest"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "spotted",
    "She",
    "the hidden cabin nestled far away in the dense mountain forest"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Is your new school far away from our house?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Is your new school far away from our house?",
  "chunks": [
    "Is",
    "your new school",
    "far away from our house"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "Is",
    "far away from our house",
    "your new school"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```

---

## sense 13981, level 2

#### Pack A
### Level 2 (sense 13981, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "correct_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "options": [
    "Relating to the process of making laws or the group of people who make laws.",
    "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
    "The process of making something start to work or be used, such as a system, plan, or law.",
    "A person or company that buys goods from another country to sell in their own country."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
        "To keep someone or something safe from damage, injury, or loss.",
        "Paper is a thin material made from wood pulp, used for writing, printing, or wrapping.",
        "to develop into a clear form or idea"
      ],
      "correct_answer": "Needing a lot of effort, skill, or attention; expecting a lot from other people."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13981, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "correct_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "options": [
    "To sharpen or smooth something by rubbing it against a hard surface, often with a fine abrasive.",
    "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
    "A route or course along which something moves or can be found.",
    "A single sheet or level of material that is laid over or under another."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
        "Meat is the flesh of an animal used as food.",
        "is needed to make something happen or be achieved.",
        "A detail or decoration added to make something more attractive or interesting."
      ],
      "correct_answer": "Needing a lot of effort, skill, or attention; expecting a lot from other people."
    }
  }
}
```

---

## sense 13981, level 3

#### Pack A
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "fragile",
    "mandatory",
    "demanding",
    "stagnant"
  ],
  "explanation": "Correct: fits the context of a process requiring significant physical effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Balancing schoolwork and sports can be extremely ___ for teenagers.",
  "original_sentence": "Balancing schoolwork and sports can be extremely demanding for teenagers.",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "heavy",
    "sudden",
    "relaxing"
  ],
  "explanation": "The correct adjective describing a task that requires a lot of effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "demandingly",
    "demanded",
    "demandable"
  ],
  "explanation": "Correct. The process of harvesting coffee by hand requires significant physical effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Learning to play the piano can be quite ___ for young beginners.",
  "original_sentence": "Learning to play the piano can be quite demanding for young beginners.",
  "correct_answer": "demanding",
  "options": [
    "demander",
    "demanding",
    "demands",
    "demanded"
  ],
  "explanation": "Correct. Learning piano requires significant attention and skill for beginners.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 4

#### Pack A
### Level 4 (sense 13981, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She found her new job very ___ because it required working long hours every single week.",
  "original_sentence": "She found her new job very demanding because it required working long hours every single week.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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
  "stem": "demand",
  "sentence_with_blank": "She found her new job very ___ because it required working long hours every single week.",
  "original_sentence": "She found her new job very demanding because it required working long hours every single week.",
  "required_pos": "verb/noun",
  "options": [
    "demandful",
    "demandness",
    "demandly",
    "demand"
  ],
  "correct_answer": "demand",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. Base form of the word family."
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The hike up the steep mountain was more ___ than they had originally expected.",
  "original_sentence": "The hike up the steep mountain was more demanding than they had originally expected.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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
  "sentence_with_blank": "The hike up the steep mountain was more ___ than they had originally expected.",
  "original_sentence": "The hike up the steep mountain was more demanding than they had originally expected.",
  "correct_answer": "demanding",
  "base_form": "base_form",
  "form_label": "demand",
  "options": [
    "demands",
    "demanding",
    "demand",
    "demanded"
  ],
  "explanation": "Correct. The present participle acts as an adjective describing the hike.",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "The hike up the steep mountain was more ___ than they had originally expected.",
  "original_sentence": "The hike up the steep mountain was more demanding than they had originally expected.",
  "required_pos": "verb/noun",
  "options": [
    "demandous",
    "demand",
    "demandation",
    "demandish"
  ],
  "correct_answer": "demand",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. Base form of the word family."
    }
  }
}
```

#### Pack B
### Level 4 (sense 13981, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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
  "stem": "demand",
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
  "required_pos": "adjective",
  "options": [
    "demandation",
    "demandment",
    "demanding",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning requiring great effort or skill"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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
  "stem": "demand",
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
  "required_pos": "adjective",
  "options": [
    "demandive",
    "demandity",
    "demanding",
    "demandous"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning needing effort"
    }
  }
}
```

---

## sense 13981, level 6

#### Pack A
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The demanding puppy slept quietly in its bed all day, requiring absolutely no attention from its owners.",
      "is_correct": false
    },
    {
      "text": "That teacher is known for having a demanding grading policy that challenges all her students.",
      "is_correct": true
    },
    {
      "text": "The wooden chair is extremely demanding, often asking the room to rearrange its furniture.",
      "is_correct": false
    },
    {
      "text": "She found the taste of plain water to be very demanding, so she added sugar to it.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: inanimate objects like chairs do not possess the agency to have expectations or make requests of others. Semantically inappropriate: 'demanding' describes tasks or people requiring effort and attention, not the flavor profile of a basic liquid. Pragmatically inappropriate: 'demanding' means expecting a lot of attention, which directly contradicts the subsequent clause about requiring no attention.",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Breathing air is a highly demanding process that takes up all of our daily energy.",
      "is_correct": false
    },
    {
      "text": "They faced a demanding situation when the project deadline was suddenly moved forward.",
      "is_correct": true
    },
    {
      "text": "The water in the pool was very demanding, requiring a lot of effort to stay wet.",
      "is_correct": false
    },
    {
      "text": "The hallway was extremely demanding, stretching for over five miles without any turns.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'demanding' applies to tasks or people requiring effort or attention, not the physical state of water. pragmatic: breathing is an automatic, effortless process for a healthy person, contradicting the definition of needing a lot of effort. semantic: 'demanding' describes the requirement of effort or attention, not the physical length or spatial dimensions of a location.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Running a marathon is a demanding sport that requires months of daily training and dedication.",
      "is_correct": true
    },
    {
      "text": "Running a marathon is a demanding sport that requires no training at all.",
      "is_correct": false
    },
    {
      "text": "Running a marathon is a demanding sport that only takes five minutes to complete.",
      "is_correct": false
    },
    {
      "text": "Running a marathon is a demanding sport because it is very easy and relaxing.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic contradiction. A 'demanding' activity inherently requires effort and training, so saying it requires 'no training' contradicts the definition. Semantic contradiction. 'Demanding' means requiring effort, which is the opposite of 'easy and relaxing'. Pragmatic/Contextual error. Marathons are long-distance races; claiming they take five minutes contradicts general knowledge and the implication of 'demanding' (endurance).",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Working on the science project proved to be a demanding task that everyone finished in one minute.",
      "is_correct": false
    },
    {
      "text": "Working on the science project proved to be a demanding task for the group.",
      "is_correct": true
    },
    {
      "text": "Working on the science project proved to be a demanding task, so they decided to ignore it completely.",
      "is_correct": false
    },
    {
      "text": "Working on the science project proved to be a demanding task because it required zero effort from the group.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic contradiction. 'Demanding' implies high effort, so 'zero effort' contradicts the word's meaning. Pragmatic error. A task finished in one minute is rarely described as 'demanding' in terms of effort or skill. Logical/Pragmatic weakness. While possible, 'demanding' tasks usually require engagement, not ignoring. This creates a weak semantic link compared to the intended meaning of requiring dedication.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 9

#### Pack A
### Level 9 (sense 13981, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "That demanding boss always expected his employees to finish their reports ahead of schedule."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That demanding boss always expected his employees to finish their reports ahead of schedule.",
  "chunks": [
    "That demanding boss",
    "always",
    "expected",
    "his employees to finish their reports ahead of schedule"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "expected",
    "his employees to finish their reports ahead of schedule",
    "always",
    "That demanding boss"
  ],
  "target_word": "demanding",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Running a marathon is a demanding sport that requires months of daily training and dedication."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Running a marathon is a demanding sport that requires months of daily training and dedication.",
  "chunks": [
    "Running a marathon",
    "is",
    "a demanding sport that requires months of daily training and dedication"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a demanding sport that requires months of daily training and dedication",
    "Running a marathon",
    "is"
  ],
  "target_word": "demanding",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13981, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He has a demanding boss who expects him to work late on most weekends."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He has a demanding boss who expects him to work late on most weekends.",
  "chunks": [
    "He",
    "has",
    "a demanding boss who expects him to work late on most weekends"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "has",
    "He",
    "a demanding boss who expects him to work late on most weekends"
  ],
  "target_word": "demanding",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "That teacher is known for having a demanding grading policy that challenges all her students."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That teacher is known for having a demanding grading policy that challenges all her students.",
  "chunks": [
    "That teacher",
    "is known",
    "for having a demanding grading policy that challenges all her students"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "for having a demanding grading policy that challenges all her students",
    "That teacher",
    "is known"
  ],
  "target_word": "demanding",
  "chunk_count": 3
}
```

---

## sense 14001, level 2

#### Pack A
### Level 2 (sense 14001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tem",
  "correct_definition": "A set of connected parts that form a complex whole.",
  "options": [
    "in a way that involves a close personal relationship or thorough knowledge",
    "To move something smoothly along a surface, often by pushing it.",
    "A set of connected parts that form a complex whole.",
    "The size, range, or amount of something."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tem",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A set of connected parts that form a complex whole.",
        "To cause someone to do something through reasoning or argument.",
        "Being very good at something.",
        "Something that moves faster than sound."
      ],
      "correct_answer": "A set of connected parts that form a complex whole."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tuhm",
  "correct_definition": "A set of connected parts that work together to form a complex whole.",
  "options": [
    "A beekeeper is someone who keeps and raises bees, usually to collect honey or to help pollinate plants.",
    "A set of connected parts that work together to form a complex whole.",
    "A number of people or things arranged in a line, especially a line of seats in a theater or classroom.",
    "Following established customs or rules; suitable for official occasions."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "system",
  "pronunciation": "SIS-tuhm",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A set of connected parts that work together to form a complex whole.",
        "To describe the typical or distinctive features of.",
        "A large number, especially of people.",
        "A story about money that you keep at a bank."
      ],
      "correct_answer": "A set of connected parts that work together to form a complex whole."
    }
  }
}
```

---
