# Pairwise review pack 14

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


## sense 19521, level 2

#### Pack A
### Level 2 (sense 19521, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "correct_definition": "Coming next after the eighteenth in a series.",
  "options": [
    "Toward a higher position, level, or amount.",
    "To state or describe something in detail, giving exact information.",
    "A major change in the form or nature of something, especially a transformation from one stage to another in an animal's life cycle.",
    "Coming next after the eighteenth in a series."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A story in a book or movie.",
        "Coming next after the eighteenth in a series.",
        "used to say that something is small or unimportant, or not the only thing.",
        "young people, used here in the plural form"
      ],
      "correct_answer": "Coming next after the eighteenth in a series."
    }
  }
}
```

#### Pack B
### Level 2 (sense 19521, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "correct_definition": "Coming next after the eighteenth in a series.",
  "options": [
    "Toward a higher position, level, or amount.",
    "To state or describe something in detail, giving exact information.",
    "A major change in the form or nature of something, especially a transformation from one stage to another in an animal's life cycle.",
    "Coming next after the eighteenth in a series."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A story in a book or movie.",
        "Coming next after the eighteenth in a series.",
        "used to say that something is small or unimportant, or not the only thing.",
        "young people, used here in the plural form"
      ],
      "correct_answer": "Coming next after the eighteenth in a series."
    }
  }
}
```

---

## sense 19521, level 3

#### Pack A
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She celebrated her ___ birthday with a big party.",
  "original_sentence": "She celebrated her nineteenth birthday with a big party.",
  "correct_answer": "nineteenth",
  "options": [
    "final",
    "twentieth",
    "eighteenth",
    "nineteenth"
  ],
  "explanation": "Correct: matches the exact ordinal form used in the sentence to describe her birthday.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "If you look at the ___ item on the list, you will find the answer.",
  "original_sentence": "If you look at the nineteenth item on the list, you will find the answer.",
  "correct_answer": "nineteenth",
  "options": [
    "loudest",
    "nineteenth",
    "wooden",
    "asleep"
  ],
  "explanation": "Correct: fits the sentence as an ordinal number identifying a specific position in a list.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```

#### Pack B
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She celebrated her ___ birthday with a big party.",
  "original_sentence": "She celebrated her nineteenth birthday with a big party.",
  "correct_answer": "nineteenth",
  "options": [
    "final",
    "twentieth",
    "eighteenth",
    "nineteenth"
  ],
  "explanation": "Correct: matches the exact ordinal form used in the sentence to describe her birthday.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "If you look at the ___ item on the list, you will find the answer.",
  "original_sentence": "If you look at the nineteenth item on the list, you will find the answer.",
  "correct_answer": "nineteenth",
  "options": [
    "loudest",
    "nineteenth",
    "wooden",
    "asleep"
  ],
  "explanation": "Correct: fits the sentence as an ordinal number identifying a specific position in a list.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```

---

## sense 19521, level 4

#### Pack A
### Level 4 (sense 19521, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our team finished in ___ place during the national competition.",
  "original_sentence": "Our team finished in nineteenth place during the national competition.",
  "target_word": "nineteenth",
  "word": "nineteenth",
  "answer": {
    "accepted": [
      "nineteenth",
      "nineteenths"
    ],
    "accepted_normalized": [
      "nineteenth",
      "nineteenths"
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
  "stem": "nineteen",
  "sentence_with_blank": "Our team finished in ___ place during the national competition.",
  "original_sentence": "Our team finished in nineteenth place during the national competition.",
  "required_pos": "adjective",
  "options": [
    "nineteenthness",
    "nineteenthly",
    "nineteenth",
    "nineteenthal"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal adjective for this position"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Today is the ___ of October, which means autumn is well underway.",
  "original_sentence": "Today is the nineteenth of October, which means autumn is well underway.",
  "target_word": "nineteenth",
  "word": "nineteenth",
  "answer": {
    "accepted": [
      "nineteenth",
      "nineteenths"
    ],
    "accepted_normalized": [
      "nineteenth",
      "nineteenths"
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
  "stem": "nineteen",
  "sentence_with_blank": "Today is the ___ of October, which means autumn is well underway.",
  "original_sentence": "Today is the nineteenth of October, which means autumn is well underway.",
  "required_pos": "adjective",
  "options": [
    "nineteenth",
    "nineteenic",
    "nineteenal",
    "nineteenous"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal adjective form"
    }
  }
}
```

#### Pack B
### Level 4 (sense 19521, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our team finished in ___ place during the national competition.",
  "original_sentence": "Our team finished in nineteenth place during the national competition.",
  "target_word": "nineteenth",
  "word": "nineteenth",
  "answer": {
    "accepted": [
      "nineteenth",
      "nineteenths"
    ],
    "accepted_normalized": [
      "nineteenth",
      "nineteenths"
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
  "stem": "nineteen",
  "sentence_with_blank": "Our team finished in ___ place during the national competition.",
  "original_sentence": "Our team finished in nineteenth place during the national competition.",
  "required_pos": "adjective",
  "options": [
    "nineteenthness",
    "nineteenthly",
    "nineteenth",
    "nineteenthal"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal adjective for this position"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Today is the ___ of October, which means autumn is well underway.",
  "original_sentence": "Today is the nineteenth of October, which means autumn is well underway.",
  "target_word": "nineteenth",
  "word": "nineteenth",
  "answer": {
    "accepted": [
      "nineteenth",
      "nineteenths"
    ],
    "accepted_normalized": [
      "nineteenth",
      "nineteenths"
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
  "stem": "nineteen",
  "sentence_with_blank": "Today is the ___ of October, which means autumn is well underway.",
  "original_sentence": "Today is the nineteenth of October, which means autumn is well underway.",
  "required_pos": "adjective",
  "options": [
    "nineteenth",
    "nineteenic",
    "nineteenal",
    "nineteenous"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal adjective form"
    }
  }
}
```

---

## sense 19521, level 6

#### Pack A
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nineteenth silence filled the room after his joke fell flat.",
      "is_correct": false
    },
    {
      "text": "Chapter nineteen is usually considered the most exciting part of the book.",
      "is_correct": true
    },
    {
      "text": "She whispered her nineteenth secret to the wind.",
      "is_correct": false
    },
    {
      "text": "The nineteenth cloud drifted quietly across the sky.",
      "is_correct": false
    }
  ],
  "explanation": "Clouds are not naturally counted in an ordered series, so using an ordinal number here is pragmatically odd. Secrets are abstract and not typically enumerated as a sequence, making the ordinal usage unnatural. Silence is not a countable, ordered event, so assigning it an ordinal number is semantically inappropriate.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They stopped to rest after completing the nineteenth mile of the hike.",
      "is_correct": true
    },
    {
      "text": "The nineteenth color of the rainbow appeared after the storm.",
      "is_correct": false
    },
    {
      "text": "The nineteenth ocean stretched endlessly beyond the horizon.",
      "is_correct": false
    },
    {
      "text": "She poured herself a nineteenth glass of water before breakfast.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: there are only a handful of oceans, so referring to a 'nineteenth ocean' is nonsensical. pragmatic: drinking nineteen glasses of water before breakfast is implausible and makes the sentence oddly exaggerated. semantic: rainbows are conventionally described as having only seven colors, so a 'nineteenth color' does not fit real-world knowledge.",
  "target_word": "nineteenth"
}
```

#### Pack B
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nineteenth silence filled the room after his joke fell flat.",
      "is_correct": false
    },
    {
      "text": "Chapter nineteen is usually considered the most exciting part of the book.",
      "is_correct": true
    },
    {
      "text": "She whispered her nineteenth secret to the wind.",
      "is_correct": false
    },
    {
      "text": "The nineteenth cloud drifted quietly across the sky.",
      "is_correct": false
    }
  ],
  "explanation": "Clouds are not naturally counted in an ordered series, so using an ordinal number here is pragmatically odd. Secrets are abstract and not typically enumerated as a sequence, making the ordinal usage unnatural. Silence is not a countable, ordered event, so assigning it an ordinal number is semantically inappropriate.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They stopped to rest after completing the nineteenth mile of the hike.",
      "is_correct": true
    },
    {
      "text": "The nineteenth color of the rainbow appeared after the storm.",
      "is_correct": false
    },
    {
      "text": "The nineteenth ocean stretched endlessly beyond the horizon.",
      "is_correct": false
    },
    {
      "text": "She poured herself a nineteenth glass of water before breakfast.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: there are only a handful of oceans, so referring to a 'nineteenth ocean' is nonsensical. pragmatic: drinking nineteen glasses of water before breakfast is implausible and makes the sentence oddly exaggerated. semantic: rainbows are conventionally described as having only seven colors, so a 'nineteenth color' does not fit real-world knowledge.",
  "target_word": "nineteenth"
}
```

---

## sense 19521, level 9

#### Pack A
### Level 9 (sense 19521, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "That historic event took place during the nineteenth century."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That historic event took place during the nineteenth century.",
  "chunks": [
    "That historic event",
    "took",
    "place",
    "during the nineteenth century"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "took",
    "during the nineteenth century",
    "That historic event",
    "place"
  ],
  "target_word": "nineteenth",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Chapter nineteen is usually considered the most exciting part of the book."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Chapter nineteen is usually considered the most exciting part of the book.",
  "chunks": [
    "Chapter nineteen",
    "is considered",
    "usually",
    "the most exciting part of the book"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "is considered",
    "usually",
    "Chapter nineteen",
    "the most exciting part of the book"
  ],
  "target_word": "nineteenth",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 19521, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "That historic event took place during the nineteenth century."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That historic event took place during the nineteenth century.",
  "chunks": [
    "That historic event",
    "took",
    "place",
    "during the nineteenth century"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "took",
    "during the nineteenth century",
    "That historic event",
    "place"
  ],
  "target_word": "nineteenth",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Chapter nineteen is usually considered the most exciting part of the book."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Chapter nineteen is usually considered the most exciting part of the book.",
  "chunks": [
    "Chapter nineteen",
    "is considered",
    "usually",
    "the most exciting part of the book"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "is considered",
    "usually",
    "Chapter nineteen",
    "the most exciting part of the book"
  ],
  "target_word": "nineteenth",
  "chunk_count": 4
}
```

---

## sense 40142, level 1

#### Pack A
### Level 1 (sense 40142, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "ipa": "/ɡreɪt wɔːl ɒv ˈtʃaɪnə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Great Wall of Chinatown",
    "Grey Wall of China",
    "Great Wall of China",
    "Great Hall of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "This is the correct written form matching the spoken phrase.",
  "distractor_explanations": {
    "Great Hall of China": "minimal pair: 'Hall' vs 'Wall' differ only in the initial consonant /h/ vs /w/.",
    "Grey Wall of China": "near-homophone: 'Grey' vs 'Great' sound similar when the final /t/ is dropped in fast speech.",
    "Great Wall of Chinatown": "near-homophone: 'Chinatown' shares the initial sound of 'China' but adds an extra syllable that could be misheard."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 40142, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "ipa": "/ɡreɪt wɔːl ɒv ˈtʃaɪnə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Great Wall of Chinatown",
    "Grey Wall of China",
    "Great Wall of China",
    "Great Hall of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "This is the correct written form matching the spoken phrase.",
  "distractor_explanations": {
    "Great Hall of China": "minimal pair: 'Hall' vs 'Wall' differ only in the initial consonant /h/ vs /w/.",
    "Grey Wall of China": "near-homophone: 'Grey' vs 'Great' sound similar when the final /t/ is dropped in fast speech.",
    "Great Wall of Chinatown": "near-homophone: 'Chinatown' shares the initial sound of 'China' but adds an extra syllable that could be misheard."
  },
  "distractor_source": "llm"
}
```

---

## sense 40142, level 2

#### Pack A
### Level 2 (sense 40142, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "correct_definition": "A big wall built a long time ago in China to keep people safe.",
  "options": [
    "Having a clear and organized arrangement or plan.",
    "An amount of money spent on something.",
    "A big wall built a long time ago in China to keep people safe.",
    "Erosion is the process by which natural forces like wind, water, or ice gradually remove soil and rock from one place and deposit it elsewhere."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A big wall built a long time ago in China to keep people safe.",
        "The distance from one end to the other.",
        "To cause something to move quickly through the air by using your hand.",
        "A type of story or film that is based on imagined future scientific discoveries or technology."
      ],
      "correct_answer": "A big wall built a long time ago in China to keep people safe."
    }
  }
}
```

#### Pack B
### Level 2 (sense 40142, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "correct_definition": "A big wall built a long time ago in China to keep people safe.",
  "options": [
    "Having a clear and organized arrangement or plan.",
    "An amount of money spent on something.",
    "A big wall built a long time ago in China to keep people safe.",
    "Erosion is the process by which natural forces like wind, water, or ice gradually remove soil and rock from one place and deposit it elsewhere."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A big wall built a long time ago in China to keep people safe.",
        "The distance from one end to the other.",
        "To cause something to move quickly through the air by using your hand.",
        "A type of story or film that is based on imagined future scientific discoveries or technology."
      ],
      "correct_answer": "A big wall built a long time ago in China to keep people safe."
    }
  }
}
```

---

## sense 40142, level 3

#### Pack A
### Level 3 (sense 40142, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Many tourists visit the ___ every single year to see its incredible length.",
  "original_sentence": "Many tourists visit the Great Wall of China every single year to see its incredible length.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Eiffel Tower",
    "shopping mall",
    "Statue of Liberty",
    "Great Wall of China"
  ],
  "explanation": "Correct: this is the exact phrase used in the sentence and fits the context of tourists visiting a long structure.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "My parents took numerous pictures when they explored the ___ last summer.",
  "original_sentence": "My parents took numerous pictures when they explored the Great Wall of China last summer.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Statue of Liberty",
    "Great Depression",
    "Great Wall of China",
    "Eiffel Tower"
  ],
  "explanation": "Correct: this matches the exact phrase used in the original sentence.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```

#### Pack B
### Level 3 (sense 40142, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Many tourists visit the ___ every single year to see its incredible length.",
  "original_sentence": "Many tourists visit the Great Wall of China every single year to see its incredible length.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Eiffel Tower",
    "shopping mall",
    "Statue of Liberty",
    "Great Wall of China"
  ],
  "explanation": "Correct: this is the exact phrase used in the sentence and fits the context of tourists visiting a long structure.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "My parents took numerous pictures when they explored the ___ last summer.",
  "original_sentence": "My parents took numerous pictures when they explored the Great Wall of China last summer.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Statue of Liberty",
    "Great Depression",
    "Great Wall of China",
    "Eiffel Tower"
  ],
  "explanation": "Correct: this matches the exact phrase used in the original sentence.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```

---

## sense 40142, level 4

#### Pack A
### Level 4 (sense 40142, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Historians have studied how ancient builders constructed the ___ across mountains.",
  "original_sentence": "Historians have studied how ancient builders constructed the Great Wall of China across mountains.",
  "target_word": "Great Wall of China",
  "word": "Great Wall of China",
  "answer": {
    "accepted": [
      "Great Wall of China"
    ],
    "accepted_normalized": [
      "great wall of china"
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
  "sentence_with_blank": "Guard towers were built strategically along the ___ to watch for approaching enemies.",
  "original_sentence": "Guard towers were built strategically along the Great Wall of China to watch for approaching enemies.",
  "target_word": "Great Wall of China",
  "word": "Great Wall of China",
  "answer": {
    "accepted": [
      "Great Wall of China"
    ],
    "accepted_normalized": [
      "great wall of china"
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
### Level 4 (sense 40142, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Historians have studied how ancient builders constructed the ___ across mountains.",
  "original_sentence": "Historians have studied how ancient builders constructed the Great Wall of China across mountains.",
  "target_word": "Great Wall of China",
  "word": "Great Wall of China",
  "answer": {
    "accepted": [
      "Great Wall of China"
    ],
    "accepted_normalized": [
      "great wall of china"
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
  "sentence_with_blank": "Guard towers were built strategically along the ___ to watch for approaching enemies.",
  "original_sentence": "Guard towers were built strategically along the Great Wall of China to watch for approaching enemies.",
  "target_word": "Great Wall of China",
  "word": "Great Wall of China",
  "answer": {
    "accepted": [
      "Great Wall of China"
    ],
    "accepted_normalized": [
      "great wall of china"
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

## sense 40142, level 6

#### Pack A
### Level 6 (sense 40142, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China whispered softly to the sleepy toddler.",
      "is_correct": false
    },
    {
      "text": "People often wonder if astronauts can actually spot the Great Wall of China from outer space.",
      "is_correct": true
    },
    {
      "text": "She microwaved the Great Wall of China for two minutes before dinner.",
      "is_correct": false
    },
    {
      "text": "He folded the Great Wall of China neatly into his backpack before school.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically impossible: the Great Wall is an enormous outdoor structure, not something that fits in a microwave. Pragmatically impossible: the Great Wall is an inanimate structure and cannot speak or whisper. Pragmatically impossible: the Great Wall is far too large to be folded or carried in a backpack.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Yesterday, the Great Wall of China was invented by a young scientist in a laboratory.",
      "is_correct": false
    },
    {
      "text": "Preserving the crumbling sections of the Great Wall of China requires a lot of careful work.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China fits perfectly into my pocket.",
      "is_correct": false
    },
    {
      "text": "She ate the Great Wall of China for breakfast this morning.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically impossible: a massive stone structure cannot be eaten as food. Pragmatically absurd: the wall is thousands of miles long and could never fit in a pocket. Semantically wrong: the wall is an ancient historical construction, not a recent lab invention.",
  "target_word": "Great Wall of China"
}
```

#### Pack B
### Level 6 (sense 40142, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China whispered softly to the sleepy toddler.",
      "is_correct": false
    },
    {
      "text": "People often wonder if astronauts can actually spot the Great Wall of China from outer space.",
      "is_correct": true
    },
    {
      "text": "She microwaved the Great Wall of China for two minutes before dinner.",
      "is_correct": false
    },
    {
      "text": "He folded the Great Wall of China neatly into his backpack before school.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically impossible: the Great Wall is an enormous outdoor structure, not something that fits in a microwave. Pragmatically impossible: the Great Wall is an inanimate structure and cannot speak or whisper. Pragmatically impossible: the Great Wall is far too large to be folded or carried in a backpack.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Yesterday, the Great Wall of China was invented by a young scientist in a laboratory.",
      "is_correct": false
    },
    {
      "text": "Preserving the crumbling sections of the Great Wall of China requires a lot of careful work.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China fits perfectly into my pocket.",
      "is_correct": false
    },
    {
      "text": "She ate the Great Wall of China for breakfast this morning.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically impossible: a massive stone structure cannot be eaten as food. Pragmatically absurd: the wall is thousands of miles long and could never fit in a pocket. Semantically wrong: the wall is an ancient historical construction, not a recent lab invention.",
  "target_word": "Great Wall of China"
}
```

---
