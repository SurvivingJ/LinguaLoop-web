# Pairwise review pack 11

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


## sense 15216, level 1

#### Pack A
### Level 1 (sense 15216, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "ipa": "/ˌmɒnəˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "monogenic",
    "monochromic",
    "monotonic",
    "monochronic"
  ],
  "correct_answer": "monochronic",
  "explanation": "This is the target word exactly as it is spoken and spelled.",
  "distractor_explanations": {
    "monochromic": "Near-homophone: shares 'mono-' and the final '-ic', differing only in the middle consonant (/n/ vs /m/) and vowel, easily confused by ear.",
    "monotonic": "Minimal pair: same stress pattern and syllable count, but the middle syllable 'ton' replaces 'chron', making it sound very similar when spoken quickly.",
    "monogenic": "Rhyming distractor: matches the 'mono-...-ic' shape and rhythm, but the middle syllable 'gen' differs from 'chron', creating a plausible mishearing."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 15216, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "ipa": "/ˌmɒnəˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "monogenic",
    "monochromic",
    "monotonic",
    "monochronic"
  ],
  "correct_answer": "monochronic",
  "explanation": "This is the target word exactly as it is spoken and spelled.",
  "distractor_explanations": {
    "monochromic": "Near-homophone: shares 'mono-' and the final '-ic', differing only in the middle consonant (/n/ vs /m/) and vowel, easily confused by ear.",
    "monotonic": "Minimal pair: same stress pattern and syllable count, but the middle syllable 'ton' replaces 'chron', making it sound very similar when spoken quickly.",
    "monogenic": "Rhyming distractor: matches the 'mono-...-ic' shape and rhythm, but the middle syllable 'gen' differs from 'chron', creating a plausible mishearing."
  },
  "distractor_source": "llm"
}
```

---

## sense 15216, level 2

#### Pack A
### Level 2 (sense 15216, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "correct_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "options": [
    "Relating to or using electricity; powered by electricity.",
    "A wave is a raised line of water that moves across the surface of the sea or a lake.",
    "Shared or used by members of a group or community.",
    "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The power to affect how someone or something develops, behaves, or thinks.",
        "A strong desire to know or learn something new.",
        "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
        "A written record of events in the order they happened."
      ],
      "correct_answer": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
    }
  }
}
```

#### Pack B
### Level 2 (sense 15216, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "correct_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "options": [
    "Relating to or using electricity; powered by electricity.",
    "A wave is a raised line of water that moves across the surface of the sea or a lake.",
    "Shared or used by members of a group or community.",
    "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The power to affect how someone or something develops, behaves, or thinks.",
        "A strong desire to know or learn something new.",
        "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
        "A written record of events in the order they happened."
      ],
      "correct_answer": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
    }
  }
}
```

---

## sense 15216, level 3

#### Pack A
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Being ___ means that interrupting a scheduled activity can cause unnecessary stress.",
  "original_sentence": "Being monochronic means that interrupting a scheduled activity can cause unnecessary stress.",
  "correct_answer": "monochronic",
  "options": [
    "scheduled",
    "monochronic",
    "monotonous",
    "polychronic"
  ],
  "explanation": "Correct: this matches the sentence's meaning of focusing on one scheduled activity at a time.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```

#### Pack B
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Being ___ means that interrupting a scheduled activity can cause unnecessary stress.",
  "original_sentence": "Being monochronic means that interrupting a scheduled activity can cause unnecessary stress.",
  "correct_answer": "monochronic",
  "options": [
    "scheduled",
    "monochronic",
    "monotonous",
    "polychronic"
  ],
  "explanation": "Correct: this matches the sentence's meaning of focusing on one scheduled activity at a time.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```

---

## sense 15216, level 4

#### Pack A
### Level 4 (sense 15216, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She is a very ___ person who relies heavily on her daily planner.",
  "original_sentence": "She is a very monochronic person who relies heavily on her daily planner.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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
  "sentence_with_blank": "Our teacher explained why some societies are traditionally viewed as ___.",
  "original_sentence": "Our teacher explained why some societies are traditionally viewed as monochronic.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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
### Level 4 (sense 15216, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She is a very ___ person who relies heavily on her daily planner.",
  "original_sentence": "She is a very monochronic person who relies heavily on her daily planner.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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
  "sentence_with_blank": "Our teacher explained why some societies are traditionally viewed as ___.",
  "original_sentence": "Our teacher explained why some societies are traditionally viewed as monochronic.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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

## sense 15216, level 6

#### Pack A
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The clock was monochronic because it kept perfect time for decades.",
      "is_correct": false
    },
    {
      "text": "The rainbow appeared monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "She painted her room in a monochronic color scheme to match her curtains.",
      "is_correct": false
    },
    {
      "text": "Is it better to be monochronic when you have many different projects to complete?",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: this confuses 'monochronic' (time-focus) with 'monochromatic' (single color), a different concept entirely. Incorrect: 'monochronic' describes a person's or culture's task-management style, not a device's accuracy. Incorrect: this misapplies the word to color design, which is unrelated to the meaning of focusing on one task at a time.",
  "target_word": "monochronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The rainbow looked completely monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "This monochronic soup tastes delicious with basil and garlic.",
      "is_correct": false
    },
    {
      "text": "I am trying to be more monochronic this week to avoid missing my deadlines.",
      "is_correct": true
    },
    {
      "text": "My phone battery is monochronic because it only lasts one hour.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect use: 'monochronic' describes time-management style, not color, so it should not describe a rainbow's appearance. Incorrect use: battery duration is unrelated to focusing on one task at a time, so 'monochronic' doesn't logically apply here. Incorrect use: taste and flavor have nothing to do with scheduling or task-focus, making this an inappropriate application of the word.",
  "target_word": "monochronic"
}
```

#### Pack B
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The clock was monochronic because it kept perfect time for decades.",
      "is_correct": false
    },
    {
      "text": "The rainbow appeared monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "She painted her room in a monochronic color scheme to match her curtains.",
      "is_correct": false
    },
    {
      "text": "Is it better to be monochronic when you have many different projects to complete?",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: this confuses 'monochronic' (time-focus) with 'monochromatic' (single color), a different concept entirely. Incorrect: 'monochronic' describes a person's or culture's task-management style, not a device's accuracy. Incorrect: this misapplies the word to color design, which is unrelated to the meaning of focusing on one task at a time.",
  "target_word": "monochronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The rainbow looked completely monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "This monochronic soup tastes delicious with basil and garlic.",
      "is_correct": false
    },
    {
      "text": "I am trying to be more monochronic this week to avoid missing my deadlines.",
      "is_correct": true
    },
    {
      "text": "My phone battery is monochronic because it only lasts one hour.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect use: 'monochronic' describes time-management style, not color, so it should not describe a rainbow's appearance. Incorrect use: battery duration is unrelated to focusing on one task at a time, so 'monochronic' doesn't logically apply here. Incorrect use: taste and flavor have nothing to do with scheduling or task-focus, making this an inappropriate application of the word.",
  "target_word": "monochronic"
}
```

---

## sense 15216, level 9

#### Pack A
### Level 9 (sense 15216, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic.",
  "chunks": [
    "They",
    "realized",
    "their working styles were different because one was monochronic and the other was polychronic"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "their working styles were different because one was monochronic and the other was polychronic",
    "They",
    "realized"
  ],
  "target_word": "monochronic",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?",
  "chunks": [
    "Is",
    "it",
    "better",
    "to be monochronic",
    "when you have many different projects to complete"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "when you have many different projects to complete",
    "to be monochronic",
    "Is",
    "it",
    "better"
  ],
  "target_word": "monochronic",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 15216, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic.",
  "chunks": [
    "They",
    "realized",
    "their working styles were different because one was monochronic and the other was polychronic"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "their working styles were different because one was monochronic and the other was polychronic",
    "They",
    "realized"
  ],
  "target_word": "monochronic",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?",
  "chunks": [
    "Is",
    "it",
    "better",
    "to be monochronic",
    "when you have many different projects to complete"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "when you have many different projects to complete",
    "to be monochronic",
    "Is",
    "it",
    "better"
  ],
  "target_word": "monochronic",
  "chunk_count": 5
}
```

---

## sense 15328, level 1

#### Pack A
### Level 1 (sense 15328, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "ipa": "/əˈweɪ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "away",
    "sway",
    "obey",
    "aweigh"
  ],
  "correct_answer": "away",
  "explanation": "This is the target word, correctly spelled and matching the spoken sound /əˈweɪ/.",
  "distractor_explanations": {
    "aweigh": "homophone: sounds identical to 'away' but is a nautical term meaning 'off the sea bottom' (anchor aweigh).",
    "obey": "rhyme: shares the same stress pattern and final /eɪ/ sound but starts with a different consonant (/b/ vs /w/).",
    "sway": "minimal pair: differs only in the initial consonant cluster, rhyming closely with 'away'."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 15328, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "ipa": "/əˈweɪ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "away",
    "sway",
    "obey",
    "aweigh"
  ],
  "correct_answer": "away",
  "explanation": "This is the target word, correctly spelled and matching the spoken sound /əˈweɪ/.",
  "distractor_explanations": {
    "aweigh": "homophone: sounds identical to 'away' but is a nautical term meaning 'off the sea bottom' (anchor aweigh).",
    "obey": "rhyme: shares the same stress pattern and final /eɪ/ sound but starts with a different consonant (/b/ vs /w/).",
    "sway": "minimal pair: differs only in the initial consonant cluster, rhyming closely with 'away'."
  },
  "distractor_source": "llm"
}
```

---

## sense 15328, level 2

#### Pack A
### Level 2 (sense 15328, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "correct_definition": "Away means to or at a distance from a particular place or person.",
  "options": [
    "Away means to or at a distance from a particular place or person.",
    "A drinking glass with a flat bottom and no handle, often used for water or juice.",
    "To use less water in order to avoid wasting it and keep it available for later.",
    "Existing in thought or as an idea but not having a physical or concrete existence."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Having great power, influence, or effect.",
        "Away means to or at a distance from a particular place or person.",
        "When people laugh, they make sounds because something is funny.",
        "You can drink water or juice from a cup."
      ],
      "correct_answer": "Away means to or at a distance from a particular place or person."
    }
  }
}
```

#### Pack B
### Level 2 (sense 15328, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "correct_definition": "Away means to or at a distance from a particular place or person.",
  "options": [
    "Away means to or at a distance from a particular place or person.",
    "A drinking glass with a flat bottom and no handle, often used for water or juice.",
    "To use less water in order to avoid wasting it and keep it available for later.",
    "Existing in thought or as an idea but not having a physical or concrete existence."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "away",
  "pronunciation": "uh-way",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Having great power, influence, or effect.",
        "Away means to or at a distance from a particular place or person.",
        "When people laugh, they make sounds because something is funny.",
        "You can drink water or juice from a cup."
      ],
      "correct_answer": "Away means to or at a distance from a particular place or person."
    }
  }
}
```

---

## sense 15328, level 3

#### Pack A
### Level 3 (sense 15328, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The clothes come from far ___.",
  "original_sentence": "The clothes come from far away.",
  "correct_answer": "away",
  "options": [
    "already",
    "together",
    "here",
    "away"
  ],
  "explanation": "Correct: 'far away' correctly describes distance from the source of the clothes.",
  "distractor_tags": {},
  "word_definition": "Away means to or at a distance from a particular place or person.",
  "target_word": "away"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He walked ___ from the recycling bin after dropping the papers in it.",
  "original_sentence": "He walked away from the recycling bin after dropping the papers in it.",
  "correct_answer": "away",
  "options": [
    "downward",
    "away",
    "together",
    "nearby"
  ],
  "explanation": "Correct: matches the original sentence, showing motion to a distance from the bin.",
  "distractor_tags": {},
  "word_definition": "Away means to or at a distance from a particular place or person.",
  "target_word": "away"
}
```

#### Pack B
### Level 3 (sense 15328, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The clothes come from far ___.",
  "original_sentence": "The clothes come from far away.",
  "correct_answer": "away",
  "options": [
    "already",
    "together",
    "here",
    "away"
  ],
  "explanation": "Correct: 'far away' correctly describes distance from the source of the clothes.",
  "distractor_tags": {},
  "word_definition": "Away means to or at a distance from a particular place or person.",
  "target_word": "away"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He walked ___ from the recycling bin after dropping the papers in it.",
  "original_sentence": "He walked away from the recycling bin after dropping the papers in it.",
  "correct_answer": "away",
  "options": [
    "downward",
    "away",
    "together",
    "nearby"
  ],
  "explanation": "Correct: matches the original sentence, showing motion to a distance from the bin.",
  "distractor_tags": {},
  "word_definition": "Away means to or at a distance from a particular place or person.",
  "target_word": "away"
}
```

---

## sense 15328, level 4

#### Pack A
### Level 4 (sense 15328, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "This big engineering work helped move water from far ___.",
  "original_sentence": "This big engineering work helped move water from far away.",
  "target_word": "away",
  "word": "away",
  "answer": {
    "accepted": [
      "away"
    ],
    "accepted_normalized": [
      "away"
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
  "sentence_with_blank": "The small boat drifted ___ while we were swimming.",
  "original_sentence": "The small boat drifted away while we were swimming.",
  "target_word": "away",
  "word": "away",
  "answer": {
    "accepted": [
      "away"
    ],
    "accepted_normalized": [
      "away"
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
### Level 4 (sense 15328, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "This big engineering work helped move water from far ___.",
  "original_sentence": "This big engineering work helped move water from far away.",
  "target_word": "away",
  "word": "away",
  "answer": {
    "accepted": [
      "away"
    ],
    "accepted_normalized": [
      "away"
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
  "sentence_with_blank": "The small boat drifted ___ while we were swimming.",
  "original_sentence": "The small boat drifted away while we were swimming.",
  "target_word": "away",
  "word": "away",
  "answer": {
    "accepted": [
      "away"
    ],
    "accepted_normalized": [
      "away"
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
