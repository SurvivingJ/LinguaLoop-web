# Pairwise review pack 15

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


## sense 40142, level 7

#### Pack A
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Many tourists visit the Great Wall of China every single year to see its incredible length.",
      "is_correct": true
    },
    {
      "text": "Historians have studied how ancient builders constructed the Great Wall of China across mountains.",
      "is_correct": true
    },
    {
      "text": "Many tourists visit Great Wall of China every single year to see its incredible length.",
      "is_correct": false,
      "error_description": "The definite article 'the' is missing before the proper noun 'Great Wall of China'; this landmark name requires 'the' in English."
    },
    {
      "text": "Walking along the Great Wall of China was an amazing experience for my older brother.",
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
      "text": "My parents took numerous pictures when they explored a Great Wall of China last summer.",
      "is_correct": false,
      "error_description": "The indefinite article 'a' is incorrectly used before 'Great Wall of China,' which is a unique, specific proper noun and must take the definite article 'the.'"
    },
    {
      "text": "Guard towers were built strategically along the Great Wall of China to watch for approaching enemies.",
      "is_correct": true
    },
    {
      "text": "Preserving the crumbling sections of the Great Wall of China requires a lot of careful work.",
      "is_correct": true
    },
    {
      "text": "My parents took numerous pictures when they explored the Great Wall of China last summer.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Many tourists visit the Great Wall of China every single year to see its incredible length.",
      "is_correct": true
    },
    {
      "text": "Historians have studied how ancient builders constructed the Great Wall of China across mountains.",
      "is_correct": true
    },
    {
      "text": "Many tourists visit Great Wall of China every single year to see its incredible length.",
      "is_correct": false,
      "error_description": "The definite article 'the' is missing before the proper noun 'Great Wall of China'; this landmark name requires 'the' in English."
    },
    {
      "text": "Walking along the Great Wall of China was an amazing experience for my older brother.",
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
      "text": "My parents took numerous pictures when they explored a Great Wall of China last summer.",
      "is_correct": false,
      "error_description": "The indefinite article 'a' is incorrectly used before 'Great Wall of China,' which is a unique, specific proper noun and must take the definite article 'the.'"
    },
    {
      "text": "Guard towers were built strategically along the Great Wall of China to watch for approaching enemies.",
      "is_correct": true
    },
    {
      "text": "Preserving the crumbling sections of the Great Wall of China requires a lot of careful work.",
      "is_correct": true
    },
    {
      "text": "My parents took numerous pictures when they explored the Great Wall of China last summer.",
      "is_correct": true
    }
  ]
}
```

---

## sense 40142, level 9

#### Pack A
### Level 9 (sense 40142, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The famous Great Wall of China snakes across hills and deserts for thousands of miles."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The famous Great Wall of China snakes across hills and deserts for thousands of miles.",
  "chunks": [
    "The famous Great Wall of China",
    "snakes",
    "across hills and deserts",
    "for thousands of miles"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "for thousands of miles",
    "across hills and deserts",
    "snakes",
    "The famous Great Wall of China"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "People often wonder if astronauts can actually spot the Great Wall of China from outer space."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "People often wonder if astronauts can actually spot the Great Wall of China from outer space.",
  "chunks": [
    "People",
    "often",
    "wonder",
    "if astronauts can actually spot the Great Wall of China from outer space"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "often",
    "wonder",
    "if astronauts can actually spot the Great Wall of China from outer space",
    "People"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 40142, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The famous Great Wall of China snakes across hills and deserts for thousands of miles."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The famous Great Wall of China snakes across hills and deserts for thousands of miles.",
  "chunks": [
    "The famous Great Wall of China",
    "snakes",
    "across hills and deserts",
    "for thousands of miles"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "for thousands of miles",
    "across hills and deserts",
    "snakes",
    "The famous Great Wall of China"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "People often wonder if astronauts can actually spot the Great Wall of China from outer space."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "People often wonder if astronauts can actually spot the Great Wall of China from outer space.",
  "chunks": [
    "People",
    "often",
    "wonder",
    "if astronauts can actually spot the Great Wall of China from outer space"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "often",
    "wonder",
    "if astronauts can actually spot the Great Wall of China from outer space",
    "People"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 4
}
```

---

## sense 40248, level 1

#### Pack A
### Level 1 (sense 40248, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "ipa": "/pɛs əv wɛstˈfeɪliə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Piece of Westphalia",
    "Peas of Westphalia",
    "Peace of Westphalia",
    "Peace off Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: this is the exact target phrase as it is naturally written and pronounced.",
  "distractor_explanations": {
    "Piece of Westphalia": "homophone: 'peace' and 'piece' share the same /piːs/ sound but differ in spelling and meaning.",
    "Peas of Westphalia": "homophone: 'peace' and 'peas' are pronounced identically as /piːs/, though 'peas' refers to vegetables.",
    "Peace off Westphalia": "minimal pair: 'of' /əv/ and 'off' /ɒf/ differ only by the final consonant sound, easily confused by ear."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 40248, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "ipa": "/pɛs əv wɛstˈfeɪliə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Piece of Westphalia",
    "Peas of Westphalia",
    "Peace of Westphalia",
    "Peace off Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: this is the exact target phrase as it is naturally written and pronounced.",
  "distractor_explanations": {
    "Piece of Westphalia": "homophone: 'peace' and 'piece' share the same /piːs/ sound but differ in spelling and meaning.",
    "Peas of Westphalia": "homophone: 'peace' and 'peas' are pronounced identically as /piːs/, though 'peas' refers to vegetables.",
    "Peace off Westphalia": "minimal pair: 'of' /əv/ and 'off' /ɒf/ differ only by the final consonant sound, easily confused by ear."
  },
  "distractor_source": "llm"
}
```

---

## sense 40248, level 2

#### Pack A
### Level 2 (sense 40248, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "correct_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "options": [
    "To combine or join something to another thing.",
    "To place a dead body in a grave, or to hide something by covering it.",
    "Located or situated near or adjacent to something else.",
    "A big agreement that ended a war and said each country can make its own rules."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A big agreement that ended a war and said each country can make its own rules.",
        "To absorb and adopt something into your own mind, beliefs, or habits so that it becomes a natural part of you.",
        "relating to or consisting of letters or correspondence, especially in a literary work",
        "over a large area or by a large number of people"
      ],
      "correct_answer": "A big agreement that ended a war and said each country can make its own rules."
    }
  }
}
```

#### Pack B
### Level 2 (sense 40248, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "correct_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "options": [
    "To combine or join something to another thing.",
    "To place a dead body in a grave, or to hide something by covering it.",
    "Located or situated near or adjacent to something else.",
    "A big agreement that ended a war and said each country can make its own rules."
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-fay-lee-uh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A big agreement that ended a war and said each country can make its own rules.",
        "To absorb and adopt something into your own mind, beliefs, or habits so that it becomes a natural part of you.",
        "relating to or consisting of letters or correspondence, especially in a literary work",
        "over a large area or by a large number of people"
      ],
      "correct_answer": "A big agreement that ended a war and said each country can make its own rules."
    }
  }
}
```

---

## sense 40248, level 3

#### Pack A
### Level 3 (sense 40248, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "During the history lesson, we discovered why the ___ matters so much.",
  "original_sentence": "During the history lesson, we discovered why the Peace of Westphalia matters so much.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Peace of Westphalia",
    "weather report",
    "birthday party",
    "class schedule"
  ],
  "explanation": "Correct: this matches the exact phrase used in the sentence about the history lesson.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```

#### Pack B
### Level 3 (sense 40248, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "During the history lesson, we discovered why the ___ matters so much.",
  "original_sentence": "During the history lesson, we discovered why the Peace of Westphalia matters so much.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Peace of Westphalia",
    "weather report",
    "birthday party",
    "class schedule"
  ],
  "explanation": "Correct: this matches the exact phrase used in the sentence about the history lesson.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 4

#### Pack A
### Level 4 (sense 40248, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Experts believe the ___ laid down important rules for international diplomacy.",
  "original_sentence": "Experts believe the Peace of Westphalia laid down important rules for international diplomacy.",
  "target_word": "Peace of Westphalia",
  "word": "Peace of Westphalia",
  "answer": {
    "accepted": [
      "Peace of Westphalia"
    ],
    "accepted_normalized": [
      "peace of westphalia"
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
### Level 4 (sense 40248, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Experts believe the ___ laid down important rules for international diplomacy.",
  "original_sentence": "Experts believe the Peace of Westphalia laid down important rules for international diplomacy.",
  "target_word": "Peace of Westphalia",
  "word": "Peace of Westphalia",
  "answer": {
    "accepted": [
      "Peace of Westphalia"
    ],
    "accepted_normalized": [
      "peace of westphalia"
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

## sense 40248, level 6

#### Pack A
### Level 6 (sense 40248, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She bought a Peace of Westphalia at the local bakery this morning.",
      "is_correct": false
    },
    {
      "text": "My favorite color is Peace of Westphalia.",
      "is_correct": false
    },
    {
      "text": "By signing the Peace of Westphalia, exhausted nations finally agreed to respect each other's borders.",
      "is_correct": true
    },
    {
      "text": "The dog chased the Peace of Westphalia around the backyard.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: treats an abstract historical agreement as a purchasable bakery item, which makes no sense. semantic: treats the abstract treaty as a movable physical object an animal could chase. semantic: treats a historical agreement as if it were a color, which is nonsensical.",
  "target_word": "Peace of Westphalia"
}
```

#### Pack B
### Level 6 (sense 40248, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She bought a Peace of Westphalia at the local bakery this morning.",
      "is_correct": false
    },
    {
      "text": "My favorite color is Peace of Westphalia.",
      "is_correct": false
    },
    {
      "text": "By signing the Peace of Westphalia, exhausted nations finally agreed to respect each other's borders.",
      "is_correct": true
    },
    {
      "text": "The dog chased the Peace of Westphalia around the backyard.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: treats an abstract historical agreement as a purchasable bakery item, which makes no sense. semantic: treats the abstract treaty as a movable physical object an animal could chase. semantic: treats a historical agreement as if it were a color, which is nonsensical.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 9

#### Pack A
### Level 9 (sense 40248, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty.",
  "chunks": [
    "The textbook",
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty",
    "The textbook"
  ],
  "target_word": "Peace of Westphalia",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 40248, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty.",
  "chunks": [
    "The textbook",
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty",
    "The textbook"
  ],
  "target_word": "Peace of Westphalia",
  "chunk_count": 3
}
```

---
