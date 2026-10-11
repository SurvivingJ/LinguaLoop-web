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


## sense 14001, level 3

#### Pack A
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "correct_answer": "A living plant is an open system.",
  "options": [
    "A living plant is an open idea.",
    "A living plant is an open method.",
    "A living plant is an open system.",
    "A living plant is an open unit."
  ],
  "explanation": "Correct. 'System' fits the scientific context of an entity exchanging matter/energy.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```

#### Pack B
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bugs talk to your body's defense ___, which is your immunity.",
  "original_sentence": "These bugs talk to your body's defense system, which is your immunity.",
  "correct_answer": "system",
  "options": [
    "routine",
    "strategy",
    "system",
    "machine"
  ],
  "explanation": "Correct: 'defense system' is the standard collocation for the body's immunity network.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "correct_answer": "system",
  "options": [
    "machine",
    "mechanism",
    "system",
    "process"
  ],
  "explanation": "Correct: 'system' is the exact word from the base sentence, correctly identifying a plant as a set of connected parts.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```

---

## sense 14001, level 4

#### Pack A
### Level 4 (sense 14001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "target_word": "system",
  "word": "system",
  "answer": {
    "accepted": [
      "system",
      "systems"
    ],
    "accepted_normalized": [
      "system",
      "systems"
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
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "correct_answer": "systems",
  "base_form": "system",
  "form_label": "plural",
  "options": [
    "systemed",
    "system's",
    "system",
    "systems"
  ],
  "explanation": "Correct. Plural form matches the determiner 'these'.",
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our school upgraded the computer network ___ over the summer break.",
  "original_sentence": "Our school upgraded the computer network system over the summer break.",
  "target_word": "system",
  "word": "system",
  "answer": {
    "accepted": [
      "system",
      "systems"
    ],
    "accepted_normalized": [
      "system",
      "systems"
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
  "sentence_with_blank": "Our school upgraded the computer network ___ over the summer break.",
  "original_sentence": "Our school upgraded the computer network system over the summer break.",
  "correct_answer": "system",
  "base_form": "system",
  "form_label": "singular",
  "options": [
    "system",
    "system",
    "systems",
    "system's"
  ],
  "explanation": "Correct. Singular form fits the specific network instance.",
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```

#### Pack B
### Level 4 (sense 14001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "target_word": "system",
  "word": "system",
  "answer": {
    "accepted": [
      "system",
      "systems",
      "system's"
    ],
    "accepted_normalized": [
      "system",
      "systems",
      "system's"
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
  "sentence_with_blank": "Sometimes, the defense ___ gets confused.",
  "original_sentence": "Sometimes, the defense system gets confused.",
  "correct_answer": "system",
  "base_form": "system",
  "form_label": "singular",
  "options": [
    "systems",
    "system",
    "system's",
    "systems'"
  ],
  "explanation": "the singular form is required to agree with the singular verb 'gets'",
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The school heating ___ broke down during the coldest week of winter.",
  "original_sentence": "The school heating system broke down during the coldest week of winter.",
  "target_word": "system",
  "word": "system",
  "answer": {
    "accepted": [
      "system",
      "systems",
      "system's"
    ],
    "accepted_normalized": [
      "system",
      "systems",
      "system's"
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

## sense 14001, level 6

#### Pack A
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The teacher asked the student to system his homework before submitting it.",
      "is_correct": false
    },
    {
      "text": "He bought a new system of shoes for the marathon.",
      "is_correct": false
    },
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    },
    {
      "text": "She felt a strong system of joy when she heard the good news.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect usage: 'System' is used as a verb here, but it is a noun. Incorrect usage: 'System' cannot refer to an emotion or feeling. Incorrect usage: 'System' is not used to describe a pair of clothing items.",
  "target_word": "system"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He put the books on the respiratory system shelf.",
      "is_correct": false
    },
    {
      "text": "The respiratory system tasted very salty.",
      "is_correct": false
    },
    {
      "text": "She studied how the respiratory system brings oxygen into the human body.",
      "is_correct": true
    },
    {
      "text": "She wore a beautiful respiratory system to the party.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect usage: 'Respiratory' modifies 'system', not 'shelf' in this awkward construction, and 'system' doesn't mean shelf. Incorrect usage: A system cannot taste; this attributes sensory perception to an abstract structure. Incorrect usage: 'System' is not an item of clothing.",
  "target_word": "system"
}
```

#### Pack B
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system of the book was very heavy to carry in my backpack.",
      "is_correct": false
    },
    {
      "text": "The system was very loud and barked at the mailman.",
      "is_correct": false
    },
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    },
    {
      "text": "She baked a delicious system for the birthday party.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'system' refers to a set of connected parts, not a single physical object like a book. semantic: 'system' cannot refer to a baked good or food item. semantic: 'system' refers to an interconnected network of parts, not a living animal like a dog.",
  "target_word": "system"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system was very tall and had green leaves.",
      "is_correct": false
    },
    {
      "text": "She poured a system of milk into her cereal bowl for breakfast.",
      "is_correct": false
    },
    {
      "text": "He felt a sharp pain in his system when he stubbed his toe.",
      "is_correct": false
    },
    {
      "text": "They designed a new computer system to help organize our homework files.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: 'system' refers to a complex whole of connected parts, not a physical liquid or a measurable quantity of food. semantic: A 'system' is an abstract or functional collection of parts, not a single physical organism that can grow leaves. collocational: While 'system' can refer to the body, we do not use it to describe a localized, specific physical injury like a stubbed toe; we use 'toe' or 'foot'.",
  "target_word": "system"
}
```

---

## sense 14001, level 7

#### Pack A
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
      "is_correct": true
    },
    {
      "text": "The engineers designed three new computer system for the office.",
      "is_correct": false,
      "error_description": "The noun 'system' is a countable noun and must be pluralized as 'systems' when referring to more than one, such as after the number 'three'."
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
      "is_correct": true
    },
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    },
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
      "is_correct": true
    },
    {
      "text": "The digestive system are responsible for breaking down food in the body.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The singular noun 'system' requires the singular verb 'is', not the plural verb 'are'."
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
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
      "text": "A living plant is an open system.",
      "is_correct": true
    },
    {
      "text": "Our school upgraded the computer network system over the summer break.",
      "is_correct": true
    },
    {
      "text": "She studied how the respiratory system brings oxygen into the human body.",
      "is_correct": true
    },
    {
      "text": "The digestive system are responsible for breaking down food in the body.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The singular noun 'system' requires the singular verb 'is', not the plural verb 'are'."
    }
  ]
}
```

---

## sense 14001, level 9

#### Pack A
### Level 9 (sense 14001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Open systems take in food and heat."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Open systems take in food and heat.",
  "chunks": [
    "Open systems",
    "take",
    "in food and heat"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "Open systems",
    "in food and heat",
    "take"
  ],
  "target_word": "systems",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
  "chunks": [
    "This essential box",
    "utilizes",
    "a closed loop system filled with a special liquid called a refrigerant"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a closed loop system filled with a special liquid called a refrigerant",
    "utilizes",
    "This essential box"
  ],
  "target_word": "system",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Open systems take in food and heat."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Open systems take in food and heat.",
  "chunks": [
    "Open systems",
    "take",
    "in food and heat"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "Open systems",
    "in food and heat",
    "take"
  ],
  "target_word": "systems",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
  "chunks": [
    "This essential box",
    "utilizes",
    "a closed loop system filled with a special liquid called a refrigerant"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a closed loop system filled with a special liquid called a refrigerant",
    "utilizes",
    "This essential box"
  ],
  "target_word": "system",
  "chunk_count": 3
}
```

---

## sense 14010, level 1

#### Pack A
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-ur-uhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "defiant",
    "different",
    "efficient"
  ],
  "correct_answer": "different",
  "explanation": "Correct target word.",
  "distractor_explanations": {
    "diffident": "Audio-confusable distractor; means shy or lacking confidence.",
    "defiant": "Audio-confusable distractor; means resisting authority.",
    "efficient": "Audio-confusable distractor; means achieving maximum productivity."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "DIF-uh-ruhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "different",
    "deferent",
    "diffident",
    "defiant"
  ],
  "correct_answer": "different",
  "explanation": "Correct target word.",
  "distractor_explanations": {
    "diffident": "Minimal pair: differs only in the /r/ vs /d/ sound in the second syllable.",
    "deferent": "Near-homophone: shares the same syllable structure but differs in the first vowel sound (/ɪ/ vs /ɛ/).",
    "defiant": "Rhymes with the target but differs in stress pattern and the second vowel sound."
  },
  "distractor_source": "llm"
}
```

---

## sense 14010, level 2

#### Pack A
### Level 2 (sense 14010, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "DIF-uh-ruhnt",
  "correct_definition": "Not the same as another or each other; unlike.",
  "options": [
    "A building or room where goods or services are sold to customers.",
    "To place a dead body in a grave, or to hide something by covering it.",
    "Not the same as another or each other; unlike.",
    "To be a symbol of; to represent something abstract."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "DIF-uh-ruhnt",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To show means to make something visible or demonstrate something.",
        "Not the same as another or each other; unlike.",
        "to keep changing and developing over time",
        "the typical activities and schedule of a person within a 24-hour period"
      ],
      "correct_answer": "Not the same as another or each other; unlike."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14010, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-ur-uhnt",
  "correct_definition": "Not the same as another or each other; unlike.",
  "options": [
    "Not the same as another or each other; unlike.",
    "Used to say that something is sad or bad, and you wish it were different.",
    "A person who believes in a particular religion, idea, or set of beliefs.",
    "A quality or feature that makes someone or something different from others."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-ur-uhnt",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To put a feeling into something.",
        "Not the same as another or each other; unlike.",
        "A layer of rock or sand that holds water and allows it to flow, used as a water source.",
        "relating to Italy, its people, or its language"
      ],
      "correct_answer": "Not the same as another or each other; unlike."
    }
  }
}
```

---

## sense 14010, level 3

#### Pack A
### Level 3 (sense 14010, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People see time in ___ ways.",
  "original_sentence": "People see time in different ways.",
  "correct_answer": "different",
  "options": [
    "heterogeneous",
    "different",
    "identical",
    "contrary"
  ],
  "explanation": "Correct option: the target word as it appears in the sentence.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

#### Pack B
### Level 3 (sense 14010, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People see time in ___ ways.",
  "original_sentence": "People see time in different ways.",
  "correct_answer": "different",
  "options": [
    "identical",
    "different",
    "similar",
    "uniform"
  ],
  "explanation": "Correct fit: People perceive time in varied (different) ways.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Cultural values shape how people in ___ places think about the world.",
  "original_sentence": "Cultural values shape how people in different places think about the world.",
  "correct_answer": "different",
  "options": [
    "different",
    "identical",
    "same",
    "uniform"
  ],
  "explanation": "Correct fit: We can learn about varied (different) perspectives.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

---

## sense 14010, level 4

#### Pack A
### Level 4 (sense 14010, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They learn about ___ times.",
  "original_sentence": "They learn about different times.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "difference"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "difference"
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
  "sentence_with_blank": "They learn about ___ times.",
  "original_sentence": "They learn about different times.",
  "correct_answer": "different",
  "base_form": "differ",
  "form_label": "base verb",
  "options": [
    "differ",
    "differently",
    "difference",
    "different"
  ],
  "explanation": "Correct adjective form modifying the noun 'times'.",
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
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
      "difference"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differs",
      "differed",
      "differing",
      "difference"
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
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "correct_answer": "different",
  "base_form": "differ",
  "form_label": "base verb",
  "options": [
    "differing",
    "different",
    "difference",
    "differ"
  ],
  "explanation": "Correct adjective form modifying 'countries'.",
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

#### Pack B
### Level 4 (sense 14010, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They learn about ___ times.",
  "original_sentence": "They learn about different times.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differently",
      "difference",
      "differences"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differently",
      "difference",
      "differences"
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
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "target_word": "different",
  "word": "different",
  "answer": {
    "accepted": [
      "different",
      "differ",
      "differently",
      "difference",
      "differences"
    ],
    "accepted_normalized": [
      "different",
      "differ",
      "differently",
      "difference",
      "differences"
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
    "differive",
    "differation",
    "differment",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival derivation from differ"
    }
  }
}
```

---

## sense 14010, level 6

#### Pack A
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The number four is a different flavor than the number nine.",
      "is_correct": false
    },
    {
      "text": "I want to buy a different car, so I will purchase the exact same model I already own.",
      "is_correct": false
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "Since both identical twins have the exact same DNA, their genetic makeup is completely different.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: contradicts the premise that the twins have the exact same DNA. semantic: numbers are abstract concepts and do not possess physical flavors. pragmatic: purchasing the exact same model contradicts the stated goal of buying a different car.",
  "target_word": "different"
}
```

#### Pack B
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The growth of globalism means more and more people are working and living across different identical cultures.",
      "is_correct": false
    },
    {
      "text": "The growth of globalism means more and more people are working and living across different equal cultures.",
      "is_correct": false
    },
    {
      "text": "The growth of globalism means more and more people are working and living across different same cultures.",
      "is_correct": false
    },
    {
      "text": "The growth of globalism means more and more people are working and living across different cultures.",
      "is_correct": true
    }
  ],
  "explanation": "Semantic contradiction: 'different' and 'identical' are mutually exclusive. Semantic contradiction: 'different' cannot modify 'same'. Pragmatic/Collocational error: While grammatically possible, 'different equal' is not a standard collocation for describing cultural diversity in this context; 'different' usually contrasts with 'similar' or stands alone to denote variety.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "relation": "synonym",
  "options": [
    "like",
    "equal",
    "distinct",
    "same"
  ],
  "correct_answer": "distinct",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "Synonym: 'distinct' means recognizably different from others."
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We can learn about different identical perspectives.",
      "is_correct": false
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "We can learn about different single perspectives.",
      "is_correct": false
    },
    {
      "text": "We can learn about different same perspectives.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic contradiction: 'different' and 'same' are mutually exclusive. Semantic contradiction: 'different' cannot modify 'identical'. Pragmatic/Collocational error: 'different single' is awkward and contradictory in this context; 'different' implies plurality/variety.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "synonym",
  "options": [
    "alike",
    "equal",
    "similar",
    "unlike"
  ],
  "correct_answer": "unlike",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "Synonym: 'unlike' means not similar to."
    }
  }
}
```

---
