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
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They are trying to pick a team captain for the upcoming debate competition."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They are trying to pick a team captain for the upcoming debate competition.",
  "chunks": [
    "They",
    "are trying",
    "to pick a team captain for the upcoming debate competition"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to pick a team captain for the upcoming debate competition",
    "are trying",
    "They"
  ],
  "target_word": "pick",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you had to pick one movie to watch tonight, which one would you choose?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you had to pick one movie to watch tonight, which one would you choose?",
  "chunks": [
    "If you had to pick one movie to watch tonight",
    "which one",
    "would choose",
    "you"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "would choose",
    "If you had to pick one movie to watch tonight",
    "which one",
    "you"
  ],
  "target_word": "pick",
  "chunk_count": 4
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
    "To begin or proceed with an action, event, or process.",
    "To damage or weaken something, making it less effective.",
    "In a way that achieves the intended result.",
    "to a high degree or extent"
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
        "A bean is an edible seed that grows in pods on certain plants, often used as food.",
        "An amount of money spent on something.",
        "To begin or proceed with an action, event, or process.",
        "Something that warns you to be careful."
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
  "sentence_with_blank": "Let us ___ with our history project after a short break.",
  "original_sentence": "Let us go on with our history project after a short break.",
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with our history project after a short break.",
  "original_sentence": "Let us go on with our history project after a short break.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "go on",
    "going on",
    "goes on",
    "went on"
  ],
  "explanation": "base form is required after the causative verb 'let'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He paused for a second before he chose to ___.",
  "original_sentence": "He paused for a second before he chose to go on.",
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He paused for a second before he chose to ___.",
  "original_sentence": "He paused for a second before he chose to go on.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "went on",
    "going on",
    "goes on",
    "go on"
  ],
  "explanation": "base form required after the infinitive marker 'to'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---

## sense 13902, level 9

#### Pack A
### Level 9 (sense 13902, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "We cannot go on ignoring these important safety rules."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "We cannot go on ignoring these important safety rules.",
  "chunks": [
    "We",
    "can not go on",
    "ignoring these important safety rules"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "We",
    "ignoring these important safety rules",
    "can not go on"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Why did you go on arguing about such a small mistake?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Why did you go on arguing about such a small mistake?",
  "chunks": [
    "Why did go on",
    "you",
    "arguing about such a small mistake"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "arguing about such a small mistake",
    "you",
    "Why did go on"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13902, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He encouraged his team to go on to the next task."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He encouraged his team to go on to the next task.",
  "chunks": [
    "He encouraged",
    "his team",
    "to go on to the next task"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "He encouraged",
    "to go on to the next task",
    "his team"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The students watched the experiment go on."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The students watched the experiment go on.",
  "chunks": [
    "The students",
    "watched",
    "the experiment go on"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "the experiment go on",
    "watched",
    "The students"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```

---
