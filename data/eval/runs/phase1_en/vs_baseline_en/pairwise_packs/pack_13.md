# Pairwise review pack 13

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
    "The system or means of carrying people or goods from one place to another.",
    "A big wall built a long time ago in China to keep people safe.",
    "Extremely small; visible only with a microscope.",
    "A domain is a specific area of activity, knowledge, or influence."
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
        "Relating to society or the way people live together in communities.",
        "A way or means used to express or communicate something.",
        "The action of throwing the ball toward the batter in baseball."
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
  "sentence_with_blank": "Many tourists visit the ___ every year to see its incredible history.",
  "original_sentence": "Many tourists visit the Great Wall of China every year to see its incredible history.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Great Wall of China",
    "corporate headquarters",
    "Great Barrier Reef",
    "local shopping mall"
  ],
  "explanation": "This is the exact target phrase required to complete the sentence logically and grammatically.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Guard towers were placed at regular intervals along the ___ for defense.",
  "original_sentence": "Guard towers were placed at regular intervals along the Great Wall of China for defense.",
  "correct_answer": "Great Wall of China",
  "options": [
    "the Great Pyramid of Giza",
    "the big fence",
    "the Silk Road",
    "Great Wall of China"
  ],
  "explanation": "This is the correct historical structure located in China, fitting the context of guard towers and defense.",
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
  "sentence_with_blank": "My history teacher explained how the ancient emperors built the ___.",
  "original_sentence": "My history teacher explained how the ancient emperors built the Great Wall of China.",
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
  "sentence_with_blank": "During our geography lesson, we located the famous ___ on the map.",
  "original_sentence": "During our geography lesson, we located the famous Great Wall of China on the map.",
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
      "text": "She packed the Great Wall of China in her suitcase to take it home as a souvenir.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China was constructed entirely out of modern steel and glass in the 1990s.",
      "is_correct": false
    },
    {
      "text": "People say that the Great Wall of China is so long that it took centuries to finish.",
      "is_correct": true
    },
    {
      "text": "I used the Great Wall of China to block the wind from my backyard garden.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: the scale of the structure makes it absurd to use for a small backyard. Semantically inappropriate: contradicts the historical fact that it was built a long time ago using ancient materials. Pragmatically inappropriate: it is physically impossible to pack a massive geographical structure in a suitcase.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China was built last week using modern plastic and steel.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China is a popular type of spicy noodle soup served in Beijing restaurants.",
      "is_correct": false
    },
    {
      "text": "I keep my digital passwords stored safely inside the Great Wall of China.",
      "is_correct": false
    },
    {
      "text": "My older brother dreams of hiking along the entire length of the Great Wall of China.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: incorrectly categorizes the Great Wall of China as a food item rather than a physical historical structure. pragmatic: inappropriately treats a physical, ancient monument as a digital storage device for computer passwords. semantic: contradicts the historical and material reality of the target word, which is an ancient structure made of stone and brick.",
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

## sense 40142, level 7

#### Pack A
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "My friend wants to travel to Great Wall of China next year.",
      "is_correct": false,
      "error_description": "The proper noun phrase 'Great Wall of China' requires the definite article 'the' before it."
    },
    {
      "text": "Have you ever seen pictures of the Great Wall of China winding across the mountains?",
      "is_correct": true
    },
    {
      "text": "My history teacher explained how the ancient emperors built the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "Many tourists visit the Great Wall of China every year to see its incredible history.",
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
      "text": "The Great Wall of China were built over many centuries to protect the empire.",
      "is_correct": false,
      "error_description": "The subject 'The Great Wall of China' is a singular noun phrase, so it requires the singular verb 'was' instead of the plural verb 'were'."
    },
    {
      "text": "Guard towers were placed at regular intervals along the Great Wall of China for defense.",
      "is_correct": true
    },
    {
      "text": "During our geography lesson, we located the famous Great Wall of China on the map.",
      "is_correct": true
    },
    {
      "text": "My older brother dreams of hiking along the entire length of the Great Wall of China.",
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
  "original_sentence": "The school library has a fascinating book about the construction of the Great Wall of China."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The school library has a fascinating book about the construction of the Great Wall of China.",
  "chunks": [
    "The school library",
    "has",
    "a fascinating book about the construction of the Great Wall of China"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a fascinating book about the construction of the Great Wall of China",
    "has",
    "The school library"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "People say that the Great Wall of China is so long that it took centuries to finish."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "People say that the Great Wall of China is so long that it took centuries to finish.",
  "chunks": [
    "People",
    "say",
    "that the Great Wall of China is so long that it took centuries to finish"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "say",
    "that the Great Wall of China is so long that it took centuries to finish",
    "People"
  ],
  "target_word": "Great Wall of China",
  "chunk_count": 3
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
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-FAY-lee-uh",
  "ipa": "/ˌpiːs əv wɛstˈfeɪliə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Peas of Westphalia",
    "Peace of Westphalia",
    "Pace of Westphalia",
    "Piece of Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: the exact historical name of the 1648 treaty series.",
  "distractor_explanations": {
    "Piece of Westphalia": "homophone: 'Piece' sounds identical to 'Peace' but has a different spelling and meaning.",
    "Peas of Westphalia": "homophone: 'Peas' sounds identical to 'Peace' but refers to a vegetable.",
    "Pace of Westphalia": "near-homophone: 'Pace' /peɪs/ differs from 'Peace' /piːs/ by only one vowel phoneme."
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
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-FAY-lee-uh",
  "correct_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "options": [
    "A big agreement that ended a war and said each country can make its own rules.",
    "relating to or used for measuring",
    "able to be used more than once",
    "To cut a material such as wood or stone into a shape or design, especially with a knife or chisel."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-FAY-lee-uh",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A big agreement that ended a war and said each country can make its own rules.",
        "The process of using machines to do tasks that were previously done by people.",
        "not happening often",
        "To keep information in your mind so you can think about it later."
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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "History students often discuss the ___ because it changed how countries govern themselves.",
  "original_sentence": "History students often discuss the Peace of Westphalia because it changed how countries govern themselves.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "school rules",
    "Industrial Revolution",
    "the handshake",
    "Peace of Westphalia"
  ],
  "explanation": "Correct: the specific historical treaty that established the modern concept of national sovereignty.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Before the ___, outside powers often interfered in internal religious matters.",
  "original_sentence": "Before the Peace of Westphalia, outside powers often interfered in internal religious matters.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "armistice",
    "Peace of Westphalia",
    "peace deal",
    "Treaty of Paris"
  ],
  "explanation": "Correct: This is the specific 1648 treaty that established state sovereignty and ended the Thirty Years' War, fitting the historical context perfectly.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 4

#### Pack A
### Level 4 (sense 40248, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Many historians believe the ___ created the modern idea of national borders.",
  "original_sentence": "Many historians believe the Peace of Westphalia created the modern idea of national borders.",
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "People were studying the ___ while preparing for their history exams.",
  "original_sentence": "People were studying the Peace of Westphalia while preparing for their history exams.",
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
