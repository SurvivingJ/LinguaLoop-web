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
    "A way of behaving or doing something that is usual or traditional in a particular place or situation.",
    "Happening without stopping or very often.",
    "A hat is a covering for the head, often with a brim, worn for protection or fashion.",
    "A scale is a device used to measure weight, or a system for measuring or comparing things."
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
        "Something that is hard to understand or explain.",
        "Happening without stopping or very often.",
        "The land on the side of a hill, where plants can grow.",
        "Something that is basic, essential, or necessary for something else."
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
  "sentence_with_blank": "The demand for coffee means that this supply chain is ___ in motion.",
  "original_sentence": "The demand for coffee means that this supply chain is constantly in motion.",
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
  "original_sentence": "Technology is constantly evolving to meet the needs of modern users."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Technology is constantly evolving to meet the needs of modern users.",
  "chunks": [
    "Technology",
    "is evolving",
    "constantly",
    "to meet the needs of modern users"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "constantly",
    "to meet the needs of modern users",
    "is evolving",
    "Technology"
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
  "pronunciation": "multi-faceted",
  "correct_definition": "Having many different aspects, features, or elements.",
  "options": [
    "A separate section or part of a larger structure, often used for display or control.",
    "Of considerable or relatively great size, extent, or capacity.",
    "A log is a thick piece of wood from a tree, or a record of events or data.",
    "Having many different aspects, features, or elements."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "multifaceted",
  "pronunciation": "multi-faceted",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "feeling weary or uninterested, possibly leading to a physical reaction.",
        "A standard or principle by which something is judged or decided.",
        "The quality of having a plain, uncluttered, or uncomplicated visual appearance.",
        "Having many different aspects, features, or elements."
      ],
      "correct_answer": "Having many different aspects, features, or elements."
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

## sense 14090, level 4

#### Pack A
### Level 4 (sense 14090, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Choosing a career path can be a ___ decision because students must balance their personal interests with future job stability.",
  "original_sentence": "Choosing a career path can be a multifaceted decision because students must balance their personal interests with future job stability.",
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

## sense 14090, level 9

#### Pack A
### Level 9 (sense 14090, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities.",
  "chunks": [
    "Environmental protection",
    "is",
    "a multifaceted challenge that requires cooperation between governments scientists and local communities"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted challenge that requires cooperation between governments scientists and local communities",
    "is",
    "Environmental protection"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination.",
  "chunks": [
    "Learning to play a musical instrument",
    "is",
    "a multifaceted process that requires patience daily practice and coordination"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted process that requires patience daily practice and coordination",
    "Learning to play a musical instrument",
    "is"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14090, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The historical novel offered a multifaceted view of the revolution through the eyes of various citizens."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The historical novel offered a multifaceted view of the revolution through the eyes of various citizens.",
  "chunks": [
    "The historical novel",
    "offered",
    "a multifaceted view of the revolution",
    "through the eyes of various citizens"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "The historical novel",
    "through the eyes of various citizens",
    "a multifaceted view of the revolution",
    "offered"
  ],
  "target_word": "multifaceted",
  "chunk_count": 4
}
```

---

## sense 14100, level 2

#### Pack A
### Level 2 (sense 14100, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "correct_definition": "To move upward or to a higher position.",
  "options": [
    "Hydropower is energy produced by the flow of water, typically using dams or turbines.",
    "Faster than the speed of sound.",
    "Covered or soaked with water or another liquid.",
    "To move upward or to a higher position."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "allows for a slower change to happen",
        "To move upward or to a higher position.",
        "To produce or provide something, such as information, results, or products.",
        "Special skill or knowledge in a particular field."
      ],
      "correct_answer": "To move upward or to a higher position."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14100, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascend",
  "pronunciation": "uh-SEND",
  "correct_definition": "To move upward or to a higher position.",
  "options": [
    "To move upward or to a higher position.",
    "Not protected from danger or harm; able to be hurt.",
    "The power to produce a desired result.",
    "A room or building equipped for scientific experiments, research, or teaching."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascend",
  "pronunciation": "uh-SEND",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "put into bags for storage or transport",
        "To move upward or to a higher position.",
        "to build, create, or produce something.",
        "A person who is admired for their courage, outstanding achievements, or noble qualities."
      ],
      "correct_answer": "To move upward or to a higher position."
    }
  }
}
```

---

## sense 14100, level 3

#### Pack A
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "correct_answer": "ascend",
  "options": [
    "board",
    "ascend",
    "plummet",
    "hoist"
  ],
  "explanation": "Correct: fits the context of aerodynamic lift enabling upward movement.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings.",
  "original_sentence": "She watched her team ascend to the top of the league standings.",
  "correct_answer": "ascend",
  "options": [
    "sprout",
    "fall",
    "ascend",
    "elevate"
  ],
  "explanation": "correct: appropriately describes moving upward in a competitive ranking",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

#### Pack B
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ___ to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "original_sentence": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ascended to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "correct_answer": "ascended",
  "options": [
    "landed",
    "descended",
    "ascended",
    "wandered"
  ],
  "explanation": "Correctly describes coffee's rise in status from a wild plant to a globally valued commodity.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascended"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings after winning the championship game.",
  "original_sentence": "She watched her team ascend to the top of the league standings after winning the championship game.",
  "correct_answer": "ascend",
  "options": [
    "ascend",
    "sit",
    "descend",
    "arrive"
  ],
  "explanation": "Correct: matches the exact verb form used in the sentence, describing the team's rise in the standings.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

---

## sense 14100, level 4

#### Pack A
### Level 4 (sense 14100, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "As an airplane ___, the air becomes less dense, meaning there are fewer air molecules.",
  "original_sentence": "As an airplane ascends, the air becomes less dense, meaning there are fewer air molecules.",
  "target_word": "ascends",
  "word": "ascend",
  "answer": {
    "accepted": [
      "ascends"
    ],
    "accepted_normalized": [
      "ascends"
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
  "sentence_with_blank": "As an airplane ___, the air becomes less dense, meaning there are fewer air molecules.",
  "original_sentence": "As an airplane ascends, the air becomes less dense, meaning there are fewer air molecules.",
  "correct_answer": "ascends",
  "base_form": "ascend",
  "form_label": "third-person singular present",
  "options": [
    "ascend",
    "ascends",
    "ascending",
    "ascended"
  ],
  "explanation": "This third-person singular present form agrees with the singular subject 'airplane'.",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascends"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Birds were seen ___ high above the trees as the storm approached.",
  "original_sentence": "Birds were seen ascending high above the trees as the storm approached.",
  "target_word": "ascending",
  "word": "ascend",
  "answer": {
    "accepted": [
      "ascending"
    ],
    "accepted_normalized": [
      "ascending"
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
  "sentence_with_blank": "Birds were seen ___ high above the trees as the storm approached.",
  "original_sentence": "Birds were seen ascending high above the trees as the storm approached.",
  "correct_answer": "ascending",
  "base_form": "ascend",
  "form_label": "present participle",
  "options": [
    "ascended",
    "ascending",
    "ascend",
    "ascends"
  ],
  "explanation": "present participle is required after the passive verb of perception to indicate ongoing active action",
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascending"
}
```

#### Pack B
### Level 4 (sense 14100, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "required_pos": "verb",
  "options": [
    "ascendous",
    "ascendment",
    "ascendful",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base verb form required after the infinitive marker 'to'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "required_pos": "verb",
  "options": [
    "ascendment",
    "ascendous",
    "ascendify",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the bare infinitive required after the modal 'can'"
    }
  }
}
```

---

## sense 14100, level 6

#### Pack A
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sun will ascend at midnight to provide light for the nocturnal animals.",
      "is_correct": false
    },
    {
      "text": "The heavy iron anvil will naturally ascend to the ceiling when dropped in a vacuum.",
      "is_correct": false
    },
    {
      "text": "We watched the hot air balloon slowly ascend into the morning sky.",
      "is_correct": true
    },
    {
      "text": "The submarine was designed to ascend deep into the ocean floor to explore the dark trenches.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: heavy objects fall due to gravity; they do not naturally move upward. semantic: ascending means moving upward, which contradicts moving down into the ocean floor. pragmatic: the sun does not rise at midnight, making this factually and contextually impossible.",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small drone ascended quickly when he pushed the control stick forward.",
      "is_correct": true
    },
    {
      "text": "The liquid will ascend into a solid state when placed in the freezer.",
      "is_correct": false
    },
    {
      "text": "He tried to ascend the mathematical equation by adding more variables.",
      "is_correct": false
    },
    {
      "text": "The miners had to ascend deeper into the earth to find the rare minerals.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'ascend' refers to physical upward movement, not the phase change of a liquid to a solid semantic: 'ascend' cannot take an abstract concept like an 'equation' as a direct object for upward movement pragmatic: 'ascend' means to move upward, which directly contradicts the directional phrase 'deeper into the earth'",
  "target_word": "ascended"
}
```

#### Pack B
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The negotiations ascended into a heated argument about salary increases.",
      "is_correct": false
    },
    {
      "text": "The soup ascended in temperature after being left on the stove overnight.",
      "is_correct": false
    },
    {
      "text": "The hikers began to ascend the steep mountain trail early in the morning before the sun got too hot.",
      "is_correct": true
    },
    {
      "text": "He ascended his phone number into the database for future reference.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: abstract escalation of conflict is normally described with 'escalated,' not 'ascended,' which implies literal or status-based upward movement. Semantically inappropriate: entering data has no upward movement or rise in position, so 'ascended' does not fit this action. Pragmatically inappropriate: temperature changes are normally described with 'rose' or 'increased'; 'ascended' is not the natural verb for this kind of gradual heating.",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "As the elevator doors closed, the car began to ascend smoothly to the tenth floor.",
      "is_correct": true
    },
    {
      "text": "He decided to ascend his resignation letter to the manager before leaving the office.",
      "is_correct": false
    },
    {
      "text": "The temperature will ascend rapidly overnight, making the room impossible to sleep in.",
      "is_correct": false
    },
    {
      "text": "The river will ascend into the ocean after passing through the delta.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'ascend' is used for physical or spatial movement upward, not for a temperature increase, which should use 'rise'. semantic: 'ascend' does not mean to submit or hand over a document; this misuses the verb's core meaning of upward movement. semantic: rivers flow downward into the ocean, so 'ascend' contradicts the natural direction of water flow.",
  "target_word": "ascend"
}
```

---
