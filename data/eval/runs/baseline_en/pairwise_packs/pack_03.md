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

---

## sense 13931, level 6

#### Pack A
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The grass in the backyard became green after the heavy rain.",
      "is_correct": true
    },
    {
      "text": "The heavy silence in the room was green.",
      "is_correct": false
    },
    {
      "text": "My alarm clock rang green at midnight.",
      "is_correct": false
    },
    {
      "text": "The glass of water tasted green in the morning.",
      "is_correct": false
    }
  ],
  "explanation": "Taste cannot be described with a color adjective like 'green'; this misapplies a visual term to a flavor sense. A sound cannot be 'green'; this incorrectly applies a color term to an auditory event. Silence is an abstract, non-visual concept, so describing it as 'green' is a semantic mismatch.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Birds flew over the green hills while the sun was setting.",
      "is_correct": true
    },
    {
      "text": "He felt extremely green after finishing the interview.",
      "is_correct": false
    },
    {
      "text": "The soup tasted very green after simmering all day.",
      "is_correct": false
    },
    {
      "text": "The library was completely green during the exam period.",
      "is_correct": false
    }
  ],
  "explanation": "Inappropriate: 'green' describes color, not flavor, so it doesn't logically apply to taste. Inappropriate: 'green' here would need to describe a visible color, not the mood or atmosphere of a place. Inappropriate: this uses 'green' to suggest inexperience or nausea, not the color meaning intended for the target word.",
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
      "text": "The grass in the backyard became green after the heavy rain.",
      "is_correct": true
    },
    {
      "text": "The heavy silence in the room was green.",
      "is_correct": false
    },
    {
      "text": "My alarm clock rang green at midnight.",
      "is_correct": false
    },
    {
      "text": "The glass of water tasted green in the morning.",
      "is_correct": false
    }
  ],
  "explanation": "Taste cannot be described with a color adjective like 'green'; this misapplies a visual term to a flavor sense. A sound cannot be 'green'; this incorrectly applies a color term to an auditory event. Silence is an abstract, non-visual concept, so describing it as 'green' is a semantic mismatch.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Birds flew over the green hills while the sun was setting.",
      "is_correct": true
    },
    {
      "text": "He felt extremely green after finishing the interview.",
      "is_correct": false
    },
    {
      "text": "The soup tasted very green after simmering all day.",
      "is_correct": false
    },
    {
      "text": "The library was completely green during the exam period.",
      "is_correct": false
    }
  ],
  "explanation": "Inappropriate: 'green' describes color, not flavor, so it doesn't logically apply to taste. Inappropriate: 'green' here would need to describe a visible color, not the mood or atmosphere of a place. Inappropriate: this uses 'green' to suggest inexperience or nausea, not the color meaning intended for the target word.",
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
  "original_sentence": "Look at those bright green apples growing on the tree."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Look at those bright green apples growing on the tree.",
  "chunks": [
    "Look at",
    "those bright green apples",
    "growing on",
    "the tree"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "growing on",
    "Look at",
    "those bright green apples",
    "the tree"
  ],
  "target_word": "green",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The grass in the backyard became green after the heavy rain."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The grass in the backyard became green after the heavy rain.",
  "chunks": [
    "The grass in the backyard",
    "became",
    "green",
    "after the heavy rain"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "after the heavy rain",
    "The grass in the backyard",
    "became",
    "green"
  ],
  "target_word": "green",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 13931, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Look at those bright green apples growing on the tree."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Look at those bright green apples growing on the tree.",
  "chunks": [
    "Look at",
    "those bright green apples",
    "growing on",
    "the tree"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "growing on",
    "Look at",
    "those bright green apples",
    "the tree"
  ],
  "target_word": "green",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The grass in the backyard became green after the heavy rain."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The grass in the backyard became green after the heavy rain.",
  "chunks": [
    "The grass in the backyard",
    "became",
    "green",
    "after the heavy rain"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "after the heavy rain",
    "The grass in the backyard",
    "became",
    "green"
  ],
  "target_word": "green",
  "chunk_count": 4
}
```

---

## sense 13946, level 2

#### Pack A
### Level 2 (sense 13946, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "correct_definition": "at a great distance; a long way off",
  "options": [
    "a person who is older than others, especially in a family or community",
    "To go somewhere with someone, or to happen at the same time as something else.",
    "Having existed or been used for a long time; not young or new.",
    "at a great distance; a long way off"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The process of becoming fully grown or developed.",
        "at a great distance; a long way off",
        "Made to be the same for everyone.",
        "Finding something again that you found before."
      ],
      "correct_answer": "at a great distance; a long way off"
    }
  }
}
```

#### Pack B
### Level 2 (sense 13946, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "correct_definition": "at a great distance; a long way off",
  "options": [
    "a person who is older than others, especially in a family or community",
    "To go somewhere with someone, or to happen at the same time as something else.",
    "Having existed or been used for a long time; not young or new.",
    "at a great distance; a long way off"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "pronunciation": "fahr uh-way",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The process of becoming fully grown or developed.",
        "at a great distance; a long way off",
        "Made to be the same for everyone.",
        "Finding something again that you found before."
      ],
      "correct_answer": "at a great distance; a long way off"
    }
  }
}
```

---

## sense 13946, level 3

#### Pack A
### Level 3 (sense 13946, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The beans come from ___.",
  "original_sentence": "The beans come from far away.",
  "correct_answer": "far away",
  "options": [
    "yonder",
    "everywhere",
    "far away",
    "nearby"
  ],
  "explanation": "Correctly completes the sentence, showing the beans originate from a great distance.",
  "distractor_tags": {},
  "word_definition": "at a great distance; a long way off",
  "target_word": "far away"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Birds migrate ___ during the cold winter months.",
  "original_sentence": "Birds migrate far away during the cold winter months.",
  "correct_answer": "far away",
  "options": [
    "far apart",
    "very slowly",
    "far away",
    "close by"
  ],
  "explanation": "correct: matches the original sentence, describing the great distance birds travel when migrating",
  "distractor_tags": {},
  "word_definition": "at a great distance; a long way off",
  "target_word": "far away"
}
```

#### Pack B
### Level 3 (sense 13946, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The beans come from ___.",
  "original_sentence": "The beans come from far away.",
  "correct_answer": "far away",
  "options": [
    "yonder",
    "everywhere",
    "far away",
    "nearby"
  ],
  "explanation": "Correctly completes the sentence, showing the beans originate from a great distance.",
  "distractor_tags": {},
  "word_definition": "at a great distance; a long way off",
  "target_word": "far away"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Birds migrate ___ during the cold winter months.",
  "original_sentence": "Birds migrate far away during the cold winter months.",
  "correct_answer": "far away",
  "options": [
    "far apart",
    "very slowly",
    "far away",
    "close by"
  ],
  "explanation": "correct: matches the original sentence, describing the great distance birds travel when migrating",
  "distractor_tags": {},
  "word_definition": "at a great distance; a long way off",
  "target_word": "far away"
}
```

---

## sense 13946, level 4

#### Pack A
### Level 4 (sense 13946, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My best friend moved ___ last summer.",
  "original_sentence": "My best friend moved far away last summer.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
  "sentence_with_blank": "Looking at the bright stars made the universe feel ___.",
  "original_sentence": "Looking at the bright stars made the universe feel far away.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
### Level 4 (sense 13946, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My best friend moved ___ last summer.",
  "original_sentence": "My best friend moved far away last summer.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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
  "sentence_with_blank": "Looking at the bright stars made the universe feel ___.",
  "original_sentence": "Looking at the bright stars made the universe feel far away.",
  "target_word": "far away",
  "word": "far away",
  "answer": {
    "accepted": [
      "far away"
    ],
    "accepted_normalized": [
      "far away"
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

## sense 13946, level 6

#### Pack A
### Level 6 (sense 13946, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He whispered the secret far away directly into her ear.",
      "is_correct": false
    },
    {
      "text": "The baby slept far away in the crib beside the bed.",
      "is_correct": false
    },
    {
      "text": "The remote control was far away, right on the coffee table in front of me.",
      "is_correct": false
    },
    {
      "text": "The old castle stands on a hill far away from the town.",
      "is_correct": true
    }
  ],
  "explanation": "Contradicts itself: 'right in front of me' means close, not far away. Whispering into someone's ear requires closeness, so 'far away' is pragmatically inappropriate. 'Beside the bed' indicates close proximity, making 'far away' contradictory here.",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "nearby",
    "quickly",
    "outside",
    "somewhere"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: means at a short distance, opposite of far away"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Her mind was far away while the teacher was explaining the lesson.",
      "is_correct": true
    },
    {
      "text": "The bakery just across the street is far away.",
      "is_correct": false
    },
    {
      "text": "The keys were far away, right here in my pocket.",
      "is_correct": false
    },
    {
      "text": "Her best friend, who lives next door, is far away.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic contradiction: 'just across the street' implies very close proximity, making 'far away' illogical here pragmatic contradiction: 'right here' signals immediate closeness, directly conflicting with 'far away' pragmatic contradiction: 'next door' means extremely close, so describing that person as 'far away' doesn't make sense",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "sometimes",
    "elsewhere",
    "quickly",
    "nearby"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: at a short distance, opposite of far away"
    }
  }
}
```

#### Pack B
### Level 6 (sense 13946, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He whispered the secret far away directly into her ear.",
      "is_correct": false
    },
    {
      "text": "The baby slept far away in the crib beside the bed.",
      "is_correct": false
    },
    {
      "text": "The remote control was far away, right on the coffee table in front of me.",
      "is_correct": false
    },
    {
      "text": "The old castle stands on a hill far away from the town.",
      "is_correct": true
    }
  ],
  "explanation": "Contradicts itself: 'right in front of me' means close, not far away. Whispering into someone's ear requires closeness, so 'far away' is pragmatically inappropriate. 'Beside the bed' indicates close proximity, making 'far away' contradictory here.",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "nearby",
    "quickly",
    "outside",
    "somewhere"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: means at a short distance, opposite of far away"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Her mind was far away while the teacher was explaining the lesson.",
      "is_correct": true
    },
    {
      "text": "The bakery just across the street is far away.",
      "is_correct": false
    },
    {
      "text": "The keys were far away, right here in my pocket.",
      "is_correct": false
    },
    {
      "text": "Her best friend, who lives next door, is far away.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic contradiction: 'just across the street' implies very close proximity, making 'far away' illogical here pragmatic contradiction: 'right here' signals immediate closeness, directly conflicting with 'far away' pragmatic contradiction: 'next door' means extremely close, so describing that person as 'far away' doesn't make sense",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "sometimes",
    "elsewhere",
    "quickly",
    "nearby"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: at a short distance, opposite of far away"
    }
  }
}
```

---

## sense 13946, level 9

#### Pack A
### Level 9 (sense 13946, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He felt like his goals were still far away."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He felt like his goals were still far away.",
  "chunks": [
    "He",
    "felt",
    "like his goals were still far away"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "felt",
    "He",
    "like his goals were still far away"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The old castle stands on a hill far away from the town."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The old castle stands on a hill far away from the town.",
  "chunks": [
    "The old castle",
    "stands",
    "on a hill",
    "far away from the town"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "far away from the town",
    "The old castle",
    "stands",
    "on a hill"
  ],
  "target_word": "far away",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 13946, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He felt like his goals were still far away."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He felt like his goals were still far away.",
  "chunks": [
    "He",
    "felt",
    "like his goals were still far away"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "felt",
    "He",
    "like his goals were still far away"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The old castle stands on a hill far away from the town."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The old castle stands on a hill far away from the town.",
  "chunks": [
    "The old castle",
    "stands",
    "on a hill",
    "far away from the town"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "far away from the town",
    "The old castle",
    "stands",
    "on a hill"
  ],
  "target_word": "far away",
  "chunk_count": 4
}
```

---

## sense 13981, level 1

#### Pack A
### Level 1 (sense 13981, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "ipa": "/dɪˈmændɪŋ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "demeaning",
    "commanding",
    "commending",
    "demanding"
  ],
  "correct_answer": "demanding",
  "explanation": "This is the target word exactly as pronounced, matching the /dɪˈmændɪŋ/ sound.",
  "distractor_explanations": {
    "commanding": "Minimal pair: same stress and syllable pattern, but differs in the first consonant (/k/ vs /d/), easy to confuse by ear.",
    "demeaning": "Near rhyme: shares the 'de-' opening sound but differs in the middle vowel and final consonant sound.",
    "commending": "Rhyming distractor: similar stress pattern and ending sound (-ending vs -anding), which can be misheard in fast speech."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13981, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "ipa": "/dɪˈmændɪŋ/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "demeaning",
    "commanding",
    "commending",
    "demanding"
  ],
  "correct_answer": "demanding",
  "explanation": "This is the target word exactly as pronounced, matching the /dɪˈmændɪŋ/ sound.",
  "distractor_explanations": {
    "commanding": "Minimal pair: same stress and syllable pattern, but differs in the first consonant (/k/ vs /d/), easy to confuse by ear.",
    "demeaning": "Near rhyme: shares the 'de-' opening sound but differs in the middle vowel and final consonant sound.",
    "commending": "Rhyming distractor: similar stress pattern and ending sound (-ending vs -anding), which can be misheard in fast speech."
  },
  "distractor_source": "llm"
}
```

---

## sense 13981, level 2

#### Pack A
### Level 2 (sense 13981, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "correct_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "options": [
    "One of a pair of organs in the body that remove waste products from the blood and produce urine.",
    "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
    "A quantity that is more than what is needed or usual.",
    "having or showing great energy and effort without becoming tired"
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A hard outer skin that some animals have.",
        "Having a quality of beauty, emotion, or imagination like poetry.",
        "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
        "An activity that is done for pleasure or to take your mind off other things."
      ],
      "correct_answer": "Needing a lot of effort, skill, or attention; expecting a lot from other people."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13981, difficulty None)
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "correct_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "options": [
    "One of a pair of organs in the body that remove waste products from the blood and produce urine.",
    "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
    "A quantity that is more than what is needed or usual.",
    "having or showing great energy and effort without becoming tired"
  ]
}
```
**definition_match** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A hard outer skin that some animals have.",
        "Having a quality of beauty, emotion, or imagination like poetry.",
        "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
        "An activity that is done for pleasure or to take your mind off other things."
      ],
      "correct_answer": "Needing a lot of effort, skill, or attention; expecting a lot from other people."
    }
  }
}
```

---
