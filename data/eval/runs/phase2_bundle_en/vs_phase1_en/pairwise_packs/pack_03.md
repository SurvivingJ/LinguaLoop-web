# Pairwise review pack 03

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


## sense 13929, level 4

#### Pack A
### Level 4 (sense 13929, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "target_word": "worked",
  "word": "work",
  "answer": {
    "accepted": [
      "worked"
    ],
    "accepted_normalized": [
      "worked"
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
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "correct_answer": "worked",
  "base_form": "work",
  "form_label": "past simple",
  "options": [
    "work",
    "worked",
    "works",
    "working"
  ],
  "explanation": "past simple is required because the sentence describes a completed past action",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "worked"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The crew must ___ hard.",
  "original_sentence": "The crew must work hard.",
  "target_word": "work",
  "word": "work",
  "answer": {
    "accepted": [
      "work",
      "works",
      "worked",
      "working"
    ],
    "accepted_normalized": [
      "work",
      "works",
      "worked",
      "working"
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
  "sentence_with_blank": "The crew must ___ hard.",
  "original_sentence": "The crew must work hard.",
  "correct_answer": "work",
  "base_form": "work",
  "form_label": "base form",
  "options": [
    "working",
    "worked",
    "work",
    "works"
  ],
  "explanation": "base form is required after the modal verb 'must'",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

#### Pack B
### Level 4 (sense 13929, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "target_word": "worked",
  "word": "work",
  "answer": {
    "accepted": [
      "worked"
    ],
    "accepted_normalized": [
      "worked"
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
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "correct_answer": "worked",
  "base_form": "base_form",
  "form_label": "past tense",
  "options": [
    "works",
    "worked",
    "working",
    "work"
  ],
  "explanation": "past tense",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "worked"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "work",
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "required_pos": "noun",
  "options": [
    "workment",
    "workless",
    "worker",
    "workful"
  ],
  "correct_answer": "worker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Noun derived from 'work'."
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "It is not easy to ___ that hard.",
  "original_sentence": "It is not easy to work that hard.",
  "target_word": "work",
  "word": "work",
  "answer": {
    "accepted": [
      "work",
      "works",
      "worked",
      "working"
    ],
    "accepted_normalized": [
      "work",
      "works",
      "worked",
      "working"
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
  "sentence_with_blank": "It is not easy to ___ that hard.",
  "original_sentence": "It is not easy to work that hard.",
  "correct_answer": "work",
  "base_form": "base_form",
  "form_label": "base form",
  "options": [
    "working",
    "worked",
    "work",
    "works"
  ],
  "explanation": "base form",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "work",
  "sentence_with_blank": "It is not easy to ___ that hard.",
  "original_sentence": "It is not easy to work that hard.",
  "required_pos": "noun",
  "options": [
    "workdom",
    "workhood",
    "workish",
    "workplace"
  ],
  "correct_answer": "workplace",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Noun derived from 'work'."
    }
  }
}
```

---

## sense 13929, level 6

#### Pack A
### Level 6 (sense 13929, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They need to work hard every single day.",
      "is_correct": true
    },
    {
      "text": "They need to work hard every single night.",
      "is_correct": false
    },
    {
      "text": "They need to work hard every single quickly.",
      "is_correct": false
    },
    {
      "text": "They need to work hard every single blue.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic/Contextual error: While grammatically correct, 'night' contradicts the typical implication of daily routine labor unless specified as shift work; however, a stronger error is needed. Let's use: 'They need to work hard every single idea.' -> Semantic error. Semantic/Grammatical error: 'blue' is an adjective/noun that does not fit as a time marker or object here. Grammatical error: 'quickly' is an adverb and cannot follow 'every single' which requires a noun.",
  "target_word": "work"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We watch them work on the project every day.",
      "is_correct": true
    },
    {
      "text": "We watch them work on the project every happiness.",
      "is_correct": false
    },
    {
      "text": "We watch them work on the project every blue.",
      "is_correct": false
    },
    {
      "text": "We watch them work on the project every quickly.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic/Grammatical error: 'blue' does not fit as a time expression. Grammatical error: Adverb 'quickly' cannot follow 'every'. Semantic error: 'Happiness' is an abstract noun, not a time unit.",
  "target_word": "work"
}
```

#### Pack B
### Level 6 (sense 13929, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sleeping baby worked loudly to finish the marathon.",
      "is_correct": false
    },
    {
      "text": "They had to work hard every single day.",
      "is_correct": true
    },
    {
      "text": "She worked incredibly hard to ensure she failed all her exams.",
      "is_correct": false
    },
    {
      "text": "The wooden chair worked all day to cook a delicious meal.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: inanimate objects like chairs cannot perform conscious tasks or cook. pragmatic: working hard implies striving for success, making the goal of failing exams a contradictory and inappropriate use of the word. semantic: a sleeping baby cannot exert physical effort or run a marathon, contradicting the definition of performing a task.",
  "target_word": "work"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "strive",
    "labor",
    "perform",
    "rest"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease activity and relax, the opposite of performing a task"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The silent alarm works loudly to wake up the sleeping baby.",
      "is_correct": false
    },
    {
      "text": "We watch them work every single day.",
      "is_correct": true
    },
    {
      "text": "The textbook works in the backpack to teach the math lesson.",
      "is_correct": false
    },
    {
      "text": "The heavy rain works outside to dry the wet pavement.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: textbooks are inanimate objects and cannot perform the active task of teaching on their own. Semantically inappropriate: rain wets surfaces, so it contradicts the physical reality of drying the pavement. Pragmatically inappropriate: a 'silent' alarm by definition does not make loud noises, creating a logical contradiction.",
  "target_word": "work"
}
```

---

## sense 13929, level 7

#### Pack A
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They had to work for a very long time.",
      "is_correct": true
    },
    {
      "text": "The engineer work to move water from far away.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the singular subject 'engineer' requires the third-person singular present tense verb 'works' instead of the base form 'work'."
    },
    {
      "text": "Many men worked on the construction.",
      "is_correct": true
    },
    {
      "text": "The engineers will work to move water from far away.",
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
      "text": "The crew must work hard.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
      "is_correct": true
    },
    {
      "text": "He work very hard every day.",
      "is_correct": false,
      "error_description": "The subject 'He' is third-person singular, so the present tense verb must take the '-s' inflection ('works') rather than the base form ('work')."
    },
    {
      "text": "We watch them work every single day.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Many men worked on the construction.",
      "is_correct": true
    },
    {
      "text": "The engineers will work to move water from far away.",
      "is_correct": true
    },
    {
      "text": "The engineers works to move water from far away.",
      "is_correct": false,
      "error_description": "The subject 'engineers' is plural, so the verb should be 'work', not 'works'."
    },
    {
      "text": "They had to work for a very long time.",
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
      "text": "We watch them work on the project every day.",
      "is_correct": true
    },
    {
      "text": "It is not easy to work that hard.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can works well again.",
      "is_correct": false,
      "error_description": "After the modal verb 'can', the base form 'work' must be used, not 'works'."
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13929, level 9

#### Pack A
### Level 9 (sense 13929, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Then, the printer works in a special way."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Then, the printer works in a special way.",
  "chunks": [
    "Then",
    "the printer",
    "works",
    "in a special way"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "Then",
    "works",
    "the printer",
    "in a special way"
  ],
  "target_word": "works",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They had to work hard every single day."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They had to work hard every single day.",
  "chunks": [
    "They",
    "had",
    "to work hard every single day"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to work hard every single day",
    "had",
    "They"
  ],
  "target_word": "work",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13929, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Then, the printer works in a special way."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Then, the printer works in a special way.",
  "chunks": [
    "Then",
    "the printer",
    "works",
    "in a special way"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "Then",
    "works",
    "the printer",
    "in a special way"
  ],
  "target_word": "works",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They need to work hard every single day."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They need to work hard every single day.",
  "chunks": [
    "They",
    "need",
    "to work hard every single day"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to work hard every single day",
    "need",
    "They"
  ],
  "target_word": "work",
  "chunk_count": 3
}
```

---

## sense 13931, level 1

#### Pack A
### Level 1 (sense 13931, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "ipa": "/ɡriːn/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "glean",
    "greed",
    "green",
    "grin"
  ],
  "correct_answer": "green",
  "explanation": "Correct target word: matches the spoken /ɡriːn/.",
  "distractor_explanations": {
    "glean": "minimal pair: differs only in the liquid consonant /r/ vs /l/.",
    "grin": "minimal pair: differs only in the vowel sound /iː/ vs /ɪ/.",
    "greed": "minimal pair: differs only in the final consonant /n/ vs /d/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13931, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "ipa": "/ɡriːn/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "grain",
    "queen",
    "glean",
    "green"
  ],
  "correct_answer": "green",
  "explanation": "Correct. This is the target word.",
  "distractor_explanations": {
    "grain": "Incorrect. 'Grain' sounds similar but refers to small particles or cereal crops.",
    "glean": "Incorrect. 'Glean' sounds similar but means to gather information or leftover grain.",
    "queen": "Incorrect. 'Queen' rhymes with the target but refers to a female monarch."
  },
  "distractor_source": "llm"
}
```

---

## sense 13931, level 2

#### Pack A
### Level 2 (sense 13931, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "correct_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "options": [
    "having superior status or importance; outstanding",
    "Green is a color between blue and yellow on the spectrum, often associated with nature.",
    "A spark is a small, glowing particle that comes from fire or a hard strike, or it can mean a small sign of something starting.",
    "If something is predictable, you know what will happen because it always happens in the same way."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Special skill or knowledge in a particular field.",
        "To point or direct something toward a goal or purpose.",
        "Green is a color between blue and yellow on the spectrum, often associated with nature.",
        "Allow time to pass for a natural process to occur."
      ],
      "correct_answer": "Green is a color between blue and yellow on the spectrum, often associated with nature."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13931, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "correct_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "options": [
    "A rock is a solid piece of stone or mineral material that is often found in nature.",
    "A belief or way of doing something that has been passed from parents to children.",
    "A subway train is an electric train that runs on tracks in a tunnel underground, used for public transportation in cities.",
    "Green is a color between blue and yellow on the spectrum, often associated with nature."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "belonging to the very distant past and no longer in existence",
        "To cause something to happen suddenly or sooner than expected.",
        "Green is a color between blue and yellow on the spectrum, often associated with nature.",
        "in a way that is basic and important, affecting the main part or nature of something"
      ],
      "correct_answer": "Green is a color between blue and yellow on the spectrum, often associated with nature."
    }
  }
}
```

---

## sense 13931, level 3

#### Pack A
### Level 3 (sense 13931, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The animal walks in a ___ forest.",
  "original_sentence": "The animal walks in a green forest.",
  "correct_answer": "green",
  "options": [
    "savory",
    "posh",
    "green",
    "metallic"
  ],
  "explanation": "correct: appropriately describes the natural color of a forest.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Is that sweater blue or is it ___?",
  "original_sentence": "Is that sweater blue or is it green?",
  "correct_answer": "green",
  "options": [
    "wooden",
    "square",
    "green",
    "expensive"
  ],
  "explanation": "Correct target word: fits the context of contrasting visual colors.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```

#### Pack B
### Level 3 (sense 13931, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The animal walks in a ___ forest.",
  "original_sentence": "The animal walks in a green forest.",
  "correct_answer": "green",
  "options": [
    "green",
    "happy",
    "fast",
    "loud"
  ],
  "explanation": "Correct. The forest is described by its color, which is associated with nature.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We noticed that the young apples on the tree were still ___.",
  "original_sentence": "We noticed that the young apples on the tree were still green.",
  "correct_answer": "green",
  "options": [
    "tasty",
    "noisy",
    "green",
    "angry"
  ],
  "explanation": "Correct. The hills are described by their color after the rain.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```

---

## sense 13931, level 4

#### Pack A
### Level 4 (sense 13931, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Then, they are ___.",
  "original_sentence": "Then, they are green.",
  "target_word": "green",
  "word": "green",
  "answer": {
    "accepted": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
    ],
    "accepted_normalized": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
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
  "sentence_with_blank": "We found several small ___ apples hanging from the branch.",
  "original_sentence": "We found several small green apples hanging from the branch.",
  "target_word": "green",
  "word": "green",
  "answer": {
    "accepted": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
    ],
    "accepted_normalized": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
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
### Level 4 (sense 13931, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Then, they are ___.",
  "original_sentence": "Then, they are green.",
  "target_word": "green",
  "word": "green",
  "answer": {
    "accepted": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
    ],
    "accepted_normalized": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
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
  "sentence_with_blank": "Then, they are ___.",
  "original_sentence": "Then, they are green.",
  "correct_answer": "green",
  "base_form": "green",
  "form_label": "base",
  "options": [
    "green",
    "greenly",
    "greener",
    "greenest"
  ],
  "explanation": "base",
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "green",
  "sentence_with_blank": "Then, they are ___.",
  "original_sentence": "Then, they are green.",
  "required_pos": "noun",
  "options": [
    "greenation",
    "greenity",
    "greenness",
    "greenment"
  ],
  "correct_answer": "greenness",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "The state or quality of being green."
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They wore ___ jackets while walking through the park.",
  "original_sentence": "They wore green jackets while walking through the park.",
  "target_word": "green",
  "word": "green",
  "answer": {
    "accepted": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
    ],
    "accepted_normalized": [
      "green",
      "greener",
      "greenest",
      "greenly",
      "greenness"
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
  "sentence_with_blank": "They wore ___ jackets while walking through the park.",
  "original_sentence": "They wore green jackets while walking through the park.",
  "correct_answer": "green",
  "base_form": "green",
  "form_label": "base",
  "options": [
    "greenly",
    "greenest",
    "greener",
    "green"
  ],
  "explanation": "base",
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "green",
  "sentence_with_blank": "They wore ___ jackets while walking through the park.",
  "original_sentence": "They wore green jackets while walking through the park.",
  "required_pos": "adjective",
  "options": [
    "greenful",
    "greenous",
    "greenish",
    "greenive"
  ],
  "correct_answer": "greenish",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Somewhat green."
    }
  }
}
```

---

## sense 13931, level 6

#### Pack A
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He brushed his teeth with green shoe polish.",
      "is_correct": false
    },
    {
      "text": "The green light told him to stop the car immediately.",
      "is_correct": false
    },
    {
      "text": "She wore a bright green jacket to the school party.",
      "is_correct": true
    },
    {
      "text": "The green blood pumped through his veins.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: a green traffic light signals drivers to go, not to stop. pragmatic: shoe polish is a toxic substance meant for leather, completely inappropriate for oral hygiene. semantic: human and most animal blood is red, making green blood biologically inaccurate in a standard context.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The snow on the mountain was bright green in the middle of winter.",
      "is_correct": false
    },
    {
      "text": "The blood from his cut was a vibrant shade of green.",
      "is_correct": false
    },
    {
      "text": "The sky is always green during a clear sunny day.",
      "is_correct": false
    },
    {
      "text": "The small frog sitting on the rock was dark green.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate because the sky is blue, not green, on a clear day. Semantically inappropriate because snow is naturally white, not green. Pragmatically inappropriate because human blood is red, not green.",
  "target_word": "green"
}
```

#### Pack B
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She painted her bedroom wall a green quickly.",
      "is_correct": false
    },
    {
      "text": "She painted her bedroom wall a loud green noise.",
      "is_correct": false
    },
    {
      "text": "She painted her bedroom wall a green yesterday.",
      "is_correct": false
    },
    {
      "text": "She painted her bedroom wall a bright green color.",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect. 'Green' is an adjective describing color, but 'noise' is a noun that cannot be modified by a color adjective in this literal sense; it creates a semantic contradiction. Incorrect. 'Green' is an adjective, but 'yesterday' is a temporal noun/adverb; adjectives cannot modify time words in this syntactic structure. Incorrect. 'Quickly' is an adverb. An adjective like 'green' cannot directly modify an adverb in this position without a head noun.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "His favorite soccer jersey has large green ideas on the sleeves.",
      "is_correct": false
    },
    {
      "text": "His favorite soccer jersey has large green smells on the sleeves.",
      "is_correct": false
    },
    {
      "text": "His favorite soccer jersey has large green stripes on the sleeves.",
      "is_correct": true
    },
    {
      "text": "His favorite soccer jersey has large green times on the sleeves.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect. 'Green' is a visual adjective and cannot modify 'smells', which is an olfactory noun. Incorrect. 'Ideas' are abstract concepts and cannot be physically printed on sleeves nor colored green in a literal sense. Incorrect. 'Times' is an abstract/temporal concept and cannot be a physical object on a sleeve modified by color.",
  "target_word": "green"
}
```

---

## sense 13931, level 9

#### Pack A
### Level 9 (sense 13931, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many plants have green leaves during the warm summer months."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many plants have green leaves during the warm summer months.",
  "chunks": [
    "Many plants",
    "have",
    "green leaves",
    "during the warm summer months"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "green leaves",
    "Many plants",
    "have",
    "during the warm summer months"
  ],
  "target_word": "green",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "She painted her bedroom wall a bright green color."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She painted her bedroom wall a bright green color.",
  "chunks": [
    "She painted",
    "her bedroom",
    "wall a bright green color"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She painted",
    "wall a bright green color",
    "her bedroom"
  ],
  "target_word": "green",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13931, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They painted their old wooden treehouse completely green."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They painted their old wooden treehouse completely green.",
  "chunks": [
    "They",
    "painted",
    "their old wooden treehouse completely green"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "They",
    "their old wooden treehouse completely green",
    "painted"
  ],
  "target_word": "green",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "She wore a bright green jacket to the school party."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She wore a bright green jacket to the school party.",
  "chunks": [
    "She wore",
    "a bright green jacket",
    "to the school party"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She wore",
    "to the school party",
    "a bright green jacket"
  ],
  "target_word": "green",
  "chunk_count": 3
}
```

---
