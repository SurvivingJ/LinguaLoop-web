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


## sense 13981, level 9

#### Pack A
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

#### Pack B
### Level 9 (sense 13981, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind.",
  "chunks": [
    "Training for the marathon",
    "was",
    "a demanding experience that tested both his body and his mind"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a demanding experience that tested both his body and his mind",
    "Training for the marathon",
    "was"
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

#### Pack B
### Level 2 (sense 14001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "correct_definition": "A set of connected parts that form a complex whole.",
  "options": [
    "A set of connected parts that form a complex whole.",
    "Removing the outer layer or skin from something, like a fruit or vegetable.",
    "A final point or limit of something, like a journey or a process.",
    "The ability to make good decisions based on knowledge and experience."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A set of connected parts that form a complex whole.",
        "When food changes and gets bubbles or a funny smell, it is fermenting.",
        "The lowest part or foundation of something, on which it rests or is built.",
        "potential dangers or harm to people's health."
      ],
      "correct_answer": "A set of connected parts that form a complex whole."
    }
  }
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
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "target_word": "system",
  "word": "systems",
  "answer": {
    "accepted": [
      "system"
    ],
    "accepted_normalized": [
      "system"
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
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant."
}
```
**jumbled_sentence** variant `A`, tier `T3`
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
    "This essential box",
    "a closed loop system filled with a special liquid called a refrigerant",
    "utilizes"
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
  "pronunciation": "dif-fuh-ruhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "defiant",
    "deferent",
    "different"
  ],
  "correct_answer": "different",
  "explanation": "Correct: this is the target word as naturally spoken and spelled.",
  "distractor_explanations": {
    "deferent": "Near-homophone: sounds almost identical to 'different' but means respectful or yielding, a different word.",
    "diffident": "Minimal pair: swaps the middle sound for /d/ instead of /r/, meaning shy or lacking confidence.",
    "defiant": "Rhymes closely with 'different' when heard quickly, but means openly resistant, a distinct word."
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
  "pronunciation": "dif-fuh-ruhnt",
  "correct_definition": "Not the same as another or each other; unlike.",
  "options": [
    "A device or person that roasts food, especially coffee beans or meat.",
    "Longer is used to say something continues for a greater amount of time than something else.",
    "Not the same as another or each other; unlike.",
    "The way in which you pronounce words or parts of words clearly and distinctly."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A job or position that suits someone’s skills and interests perfectly.",
        "Not the same as another or each other; unlike.",
        "To stay in a place or delay action until something expected happens.",
        "To recognize or show the difference between things."
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
    "different",
    "difficult",
    "similar",
    "distant"
  ],
  "explanation": "Correct: matches the original sentence, describing how people perceive time in varied, unlike ways.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We can learn about ___ perspectives.",
  "original_sentence": "We can learn about different perspectives.",
  "correct_answer": "different",
  "options": [
    "afraid",
    "expensive",
    "different",
    "curious"
  ],
  "explanation": "Correct: fits the sentence, meaning we can learn about perspectives that are not the same as each other.",
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
