# Pairwise review pack 02

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


## sense 13929, level 1

#### Pack A
### Level 1 (sense 13929, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "ipa": "/wɜːrk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "word",
    "work",
    "worm",
    "were"
  ],
  "correct_answer": "work",
  "explanation": "Correct: this is the target word pronounced /wɜːrk/.",
  "distractor_explanations": {
    "worm": "minimal pair: differs only in the final consonant sound /m/ instead of /k/.",
    "word": "minimal pair: differs only in the final consonant sound /d/ instead of /k/.",
    "were": "near-homophone: shares the /wɜːr/ vowel sound but lacks the final /k/ consonant."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13929, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "works",
  "pronunciation": "wurk",
  "ipa": "/wɜːrk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "walks",
    "worse",
    "worms",
    "works"
  ],
  "correct_answer": "works",
  "explanation": "Correct target word matching the sound /wɜːrks/.",
  "distractor_explanations": {
    "worms": "minimal pair: shares the /wɜːr/ onset but ends in /mz/ instead of /ks/.",
    "worse": "rhymes with target's core vowel sound but lacks the final /k/ consonant.",
    "walks": "near-homophone by rhythm and stress, but differs in vowel /ɔː/ vs /ɜːr/."
  },
  "distractor_source": "llm"
}
```

---

## sense 13929, level 2

#### Pack A
### Level 2 (sense 13929, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "works",
  "pronunciation": "wurk",
  "correct_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "options": [
    "Connected with acting, the performance of plays, or the style of theater.",
    "To damage or weaken something, making it less effective.",
    "Arranged in a particular order, often from smallest to largest or alphabetically.",
    "To perform an activity or task, especially for pay or to achieve a result."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "works",
  "pronunciation": "wurk",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To organize or arrange people or things so that they work together effectively.",
        "To prepare data or information before it is used or analyzed.",
        "To perform an activity or task, especially for pay or to achieve a result.",
        "To give something to someone younger in your family."
      ],
      "correct_answer": "To perform an activity or task, especially for pay or to achieve a result."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13929, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "correct_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "options": [
    "A person who receives or entertains guests, or an organism that provides a home for another.",
    "To perform an activity or task, especially for pay or to achieve a result.",
    "feeling that you need to rest or sleep because you have been working, playing, or doing something for a long time",
    "The part of the face that sticks out above the mouth, used for breathing and smelling."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "relating to a dynasty, which is a series of rulers from the same family.",
        "To take control of something or someone, or to record something.",
        "relating to the way a society is organized and makes decisions.",
        "To perform an activity or task, especially for pay or to achieve a result."
      ],
      "correct_answer": "To perform an activity or task, especially for pay or to achieve a result."
    }
  }
}
```

---

## sense 13929, level 3

#### Pack A
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The engineers will ___ to move water from far away.",
  "original_sentence": "The engineers will work to move water from far away.",
  "correct_answer": "work",
  "options": [
    "bring",
    "work",
    "rest",
    "schlep"
  ],
  "explanation": "Correct: fits the context of engineers performing physical or mental effort to achieve a result.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "This medical step gives many people a second chance at life because their bodies can ___ well again.",
  "original_sentence": "This medical step gives many people a second chance at life because their bodies can work well again.",
  "correct_answer": "work",
  "options": [
    "act",
    "work",
    "labor",
    "build"
  ],
  "explanation": "Correct: naturally describes the body returning to a state of physiological functioning.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

#### Pack B
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "After morning classes, Marcus ___s on reading and numbers with his teacher.",
  "original_sentence": "After morning classes, Marcus works on reading and numbers with his teacher.",
  "correct_answer": "works",
  "options": [
    "cooks",
    "works",
    "arrives",
    "waits"
  ],
  "explanation": "Correct: matches the verb form used in the sentence describing Marcus's activity with his teacher.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

---

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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "target_word": "worked",
  "word": "works",
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

---

## sense 13929, level 6

#### Pack A
### Level 6 (sense 13929, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He works hard every single day.",
      "is_correct": true
    },
    {
      "text": "The mountain works quietly at night.",
      "is_correct": false
    },
    {
      "text": "My shadow works two jobs downtown.",
      "is_correct": false
    },
    {
      "text": "The silence works overtime for the exam.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: an inanimate mountain cannot perform tasks or labor, so this usage is pragmatically odd. semantic: a shadow has no agency to hold employment, making the sentence nonsensical despite correct grammar. semantic: silence is an abstract state, not an agent capable of laboring, so this is an inappropriate use of the verb.",
  "target_word": "work"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "works",
  "relation": "antonym",
  "options": [
    "strives",
    "labors",
    "rests",
    "toils"
  ],
  "correct_answer": "rests",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to stop activity and relax rather than perform a task"
    }
  }
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
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "She works hard every single day."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She works hard every single day.",
  "chunks": [
    "She works",
    "hard",
    "every single day"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "every single day",
    "hard",
    "She works"
  ],
  "target_word": "work",
  "chunk_count": 3
}
```

---

## sense 13931, level 1

#### Pack A
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
    "green",
    "screen",
    "grin"
  ],
  "correct_answer": "green",
  "explanation": "This is the target word exactly as pronounced, matching the /ɡriːn/ sound.",
  "distractor_explanations": {
    "grin": "minimal pair: differs only in the vowel, /ɪ/ in 'grin' vs /iː/ in 'green'.",
    "screen": "rhymes with the target's /iːn/ ending but starts with a different consonant cluster (/skr/ vs /gr/).",
    "grain": "shares the initial /gr/ sound but has a different vowel and final consonant, /eɪn/ vs /iːn/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
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

#### Pack B
### Level 2 (sense 13931, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "correct_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "options": [
    "Difficult to find, catch, or achieve.",
    "Green is a color between blue and yellow on the spectrum, often associated with nature.",
    "to examine or observe something carefully with attention to detail",
    "Large in amount, size, or degree; significant."
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
        "to stay in a place where one cannot be seen or found.",
        "A walkway is a passage or path designed for walking, often found in parks, gardens, or buildings.",
        "Green is a color between blue and yellow on the spectrum, often associated with nature.",
        "Inhabited by people or animals."
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
  "sentence_with_blank": "Then, they are ___.",
  "original_sentence": "Then, they are green.",
  "correct_answer": "green",
  "options": [
    "loud",
    "wooden",
    "sleepy",
    "green"
  ],
  "explanation": "This is the correct form of the target word as it appears in the original sentence.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The old map showed a large ___ valley between the mountains.",
  "original_sentence": "The old map showed a large green valley between the mountains.",
  "correct_answer": "green",
  "options": [
    "loud",
    "brief",
    "salty",
    "green"
  ],
  "explanation": "Correct: matches the original sentence describing the valley's color.",
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
  "sentence_with_blank": "He puts yellow blocks and ___ blocks in a line.",
  "original_sentence": "He puts yellow blocks and green blocks in a line.",
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
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "green",
  "sentence_with_blank": "He puts yellow blocks and ___ blocks in a line.",
  "original_sentence": "He puts yellow blocks and green blocks in a line.",
  "required_pos": "adjective",
  "options": [
    "green",
    "greenful",
    "greenous",
    "greenal"
  ],
  "correct_answer": "green",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective directly describing the blocks' color"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "His painted skateboard was bright ___ and very easy to spot.",
  "original_sentence": "His painted skateboard was bright green and very easy to spot.",
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
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "green",
  "sentence_with_blank": "His painted skateboard was bright ___ and very easy to spot.",
  "original_sentence": "His painted skateboard was bright green and very easy to spot.",
  "required_pos": "adjective",
  "options": [
    "greenic",
    "green",
    "greenful",
    "greenous"
  ],
  "correct_answer": "green",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective form describing the color, fitting the descriptive slot"
    }
  }
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

---
