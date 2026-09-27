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


## sense 13900, level 1

#### Pack A
### Level 1 (sense 13900, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "ipa": "/pɪk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "pick",
    "pig",
    "pit",
    "tick"
  ],
  "correct_answer": "pick",
  "explanation": "This is the target word exactly as it sounds, /pɪk/.",
  "distractor_explanations": {
    "tick": "Rhymes with the target but starts with a different consonant /t/ instead of /p/.",
    "pit": "Minimal pair: shares the initial /pɪ/ sound but ends in /t/ instead of /k/.",
    "pig": "Minimal pair: shares the initial /pɪ/ sound but ends in /g/ instead of /k/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13900, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "ipa": "/pɪk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "pick",
    "pig",
    "pit",
    "tick"
  ],
  "correct_answer": "pick",
  "explanation": "This is the target word exactly as it sounds, /pɪk/.",
  "distractor_explanations": {
    "tick": "Rhymes with the target but starts with a different consonant /t/ instead of /p/.",
    "pit": "Minimal pair: shares the initial /pɪ/ sound but ends in /t/ instead of /k/.",
    "pig": "Minimal pair: shares the initial /pɪ/ sound but ends in /g/ instead of /k/."
  },
  "distractor_source": "llm"
}
```

---

## sense 13900, level 2

#### Pack A
### Level 2 (sense 13900, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "correct_definition": "To select or choose something from a group.",
  "options": [
    "A reminder is a message or thing that makes you think about something you need to do or remember.",
    "A knitted garment worn on the upper part of the body, usually with long sleeves.",
    "To select or choose something from a group.",
    "Plastic pollution refers to the accumulation of plastic waste in the environment, which harms wildlife and ecosystems."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Businesses that sell products directly to consumers.",
        "The act or process of gathering crops when they are mature and ready to be used.",
        "To select or choose something from a group.",
        "A knot is something that feels tight and hard inside you when you are sad or worried."
      ],
      "correct_answer": "To select or choose something from a group."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13900, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "correct_definition": "To select or choose something from a group.",
  "options": [
    "A reminder is a message or thing that makes you think about something you need to do or remember.",
    "A knitted garment worn on the upper part of the body, usually with long sleeves.",
    "To select or choose something from a group.",
    "Plastic pollution refers to the accumulation of plastic waste in the environment, which harms wildlife and ecosystems."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "pick",
  "pronunciation": "pik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Businesses that sell products directly to consumers.",
        "The act or process of gathering crops when they are mature and ready to be used.",
        "To select or choose something from a group.",
        "A knot is something that feels tight and hard inside you when you are sad or worried."
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
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everyone in the class was asked to ___ a favorite book to review.",
  "original_sentence": "Everyone in the class was asked to pick a favorite book to review.",
  "correct_answer": "pick",
  "options": [
    "drop",
    "carry",
    "guess",
    "pick"
  ],
  "explanation": "Correct: 'pick' means to select one option, matching 'asked to pick a favorite book to review'.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

#### Pack B
### Level 3 (sense 13900, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everyone in the class was asked to ___ a favorite book to review.",
  "original_sentence": "Everyone in the class was asked to pick a favorite book to review.",
  "correct_answer": "pick",
  "options": [
    "drop",
    "carry",
    "guess",
    "pick"
  ],
  "explanation": "Correct: 'pick' means to select one option, matching 'asked to pick a favorite book to review'.",
  "distractor_tags": {},
  "word_definition": "To select or choose something from a group.",
  "target_word": "pick"
}
```

---

## sense 13900, level 4

#### Pack A
### Level 4 (sense 13900, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Can you help me ___ an outfit that matches the weather today?",
  "original_sentence": "Can you help me pick an outfit that matches the weather today?",
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
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "Can you help me ___ an outfit that matches the weather today?",
  "original_sentence": "Can you help me pick an outfit that matches the weather today?",
  "required_pos": "verb",
  "options": [
    "pick",
    "pickal",
    "pickment",
    "pickify"
  ],
  "correct_answer": "pick",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the bare infinitive form required after 'help me'"
    }
  }
}
```

#### Pack B
### Level 4 (sense 13900, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Can you help me ___ an outfit that matches the weather today?",
  "original_sentence": "Can you help me pick an outfit that matches the weather today?",
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
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "pick",
  "sentence_with_blank": "Can you help me ___ an outfit that matches the weather today?",
  "original_sentence": "Can you help me pick an outfit that matches the weather today?",
  "required_pos": "verb",
  "options": [
    "pick",
    "pickal",
    "pickment",
    "pickify"
  ],
  "correct_answer": "pick",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the bare infinitive form required after 'help me'"
    }
  }
}
```

---

## sense 13900, level 6

#### Pack A
### Level 6 (sense 13900, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They gathered together to pick the members of the new student council.",
      "is_correct": true
    },
    {
      "text": "The bird picked the sky before flying away.",
      "is_correct": false
    },
    {
      "text": "The weather picked the storm over the city.",
      "is_correct": false
    },
    {
      "text": "She picked her sleep early to prepare for the exam.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically inappropriate: 'sky' cannot be selected from a group, so 'pick' has no valid object here. Pragmatically odd: sleep is not a choosable item among alternatives, so 'pick' misuses the selection sense. Semantically inappropriate: weather is not an agent capable of making a selection, making the sentence nonsensical despite being grammatical.",
  "target_word": "pick"
}
```

#### Pack B
### Level 6 (sense 13900, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They gathered together to pick the members of the new student council.",
      "is_correct": true
    },
    {
      "text": "The bird picked the sky before flying away.",
      "is_correct": false
    },
    {
      "text": "The weather picked the storm over the city.",
      "is_correct": false
    },
    {
      "text": "She picked her sleep early to prepare for the exam.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically inappropriate: 'sky' cannot be selected from a group, so 'pick' has no valid object here. Pragmatically odd: sleep is not a choosable item among alternatives, so 'pick' misuses the selection sense. Semantically inappropriate: weather is not an agent capable of making a selection, making the sentence nonsensical despite being grammatical.",
  "target_word": "pick"
}
```

---

## sense 13900, level 9

#### Pack A
### Level 9 (sense 13900, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you had to pick between the two movies, which one would you watch?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you had to pick between the two movies, which one would you watch?",
  "chunks": [
    "If",
    "you",
    "had to pick between",
    "the two movies",
    "which one",
    "would"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "had to pick between",
    "If",
    "which one",
    "you",
    "would",
    "the two movies"
  ],
  "target_word": "pick",
  "chunk_count": 6
}
```

#### Pack B
### Level 9 (sense 13900, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you had to pick between the two movies, which one would you watch?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you had to pick between the two movies, which one would you watch?",
  "chunks": [
    "If",
    "you",
    "had to pick between",
    "the two movies",
    "which one",
    "would"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "shuffled_chunks": [
    "had to pick between",
    "If",
    "which one",
    "you",
    "would",
    "the two movies"
  ],
  "target_word": "pick",
  "chunk_count": 6
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
  "ipa": "",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "go in",
    "go on",
    "goon",
    "gone"
  ],
  "correct_answer": "go on",
  "explanation": "Correct: this is the natural spelling and pronunciation of the target phrasal verb /ɡoʊ ɒn/.",
  "distractor_explanations": {
    "gone": "Near-homophone: in fast speech 'go on' can collapse into a sound close to 'gone', but it is a different single word.",
    "go in": "Minimal pair: differs only in the vowel sound (/ɒn/ vs /ɪn/), easily confused when heard quickly.",
    "goon": "Rhyming distractor: 'goon' is a single-syllable real word that can sound like a compressed version of 'go on'."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13902, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "ipa": "",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "go in",
    "go on",
    "goon",
    "gone"
  ],
  "correct_answer": "go on",
  "explanation": "Correct: this is the natural spelling and pronunciation of the target phrasal verb /ɡoʊ ɒn/.",
  "distractor_explanations": {
    "gone": "Near-homophone: in fast speech 'go on' can collapse into a sound close to 'gone', but it is a different single word.",
    "go in": "Minimal pair: differs only in the vowel sound (/ɒn/ vs /ɪn/), easily confused when heard quickly.",
    "goon": "Rhyming distractor: 'goon' is a single-syllable real word that can sound like a compressed version of 'go on'."
  },
  "distractor_source": "llm"
}
```

---

## sense 13902, level 2

#### Pack A
### Level 2 (sense 13902, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "correct_definition": "To begin or proceed with an action, event, or process.",
  "options": [
    "in a way that is sufficient or satisfactory for a particular purpose",
    "To begin or proceed with an action, event, or process.",
    "at a great distance; a long way off",
    "Belonging to or typical of the most common or widely accepted ideas, styles, or activities."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Something that is not flat and has height, width, and depth.",
        "Human beings in general, especially those who do things.",
        "To begin or proceed with an action, event, or process.",
        "having a strong and immediate effect or influence."
      ],
      "correct_answer": "To begin or proceed with an action, event, or process."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13902, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "correct_definition": "To begin or proceed with an action, event, or process.",
  "options": [
    "in a way that is sufficient or satisfactory for a particular purpose",
    "To begin or proceed with an action, event, or process.",
    "at a great distance; a long way off",
    "Belonging to or typical of the most common or widely accepted ideas, styles, or activities."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Something that is not flat and has height, width, and depth.",
        "Human beings in general, especially those who do things.",
        "To begin or proceed with an action, event, or process.",
        "having a strong and immediate effect or influence."
      ],
      "correct_answer": "To begin or proceed with an action, event, or process."
    }
  }
}
```

---

## sense 13902, level 3

#### Pack A
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with the important discussion.",
  "original_sentence": "Let us go on with the important discussion.",
  "correct_answer": "go on",
  "options": [
    "finish with",
    "interfere with",
    "go on",
    "help with"
  ],
  "explanation": "Correct: matches the sentence, meaning to continue or proceed with the discussion.",
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
  "sentence_with_blank": "Let us ___ with the important discussion.",
  "original_sentence": "Let us go on with the important discussion.",
  "correct_answer": "go on",
  "options": [
    "finish with",
    "interfere with",
    "go on",
    "help with"
  ],
  "explanation": "Correct: matches the sentence, meaning to continue or proceed with the discussion.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---

## sense 13902, level 4

#### Pack A
### Level 4 (sense 13902, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Let us ___ with our project after lunch.",
  "original_sentence": "Let us go on with our project after lunch.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
  "sentence_with_blank": "Please ___ reading the story from where you stopped.",
  "original_sentence": "Please go on reading the story from where you stopped.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
### Level 4 (sense 13902, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Let us ___ with our project after lunch.",
  "original_sentence": "Let us go on with our project after lunch.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
  "sentence_with_blank": "Please ___ reading the story from where you stopped.",
  "original_sentence": "Please go on reading the story from where you stopped.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
