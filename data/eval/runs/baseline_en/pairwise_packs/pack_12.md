# Pairwise review pack 12

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


## sense 15328, level 6

#### Pack A
### Level 6 (sense 15328, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The cabin is located two miles away from itself.",
      "is_correct": false
    },
    {
      "text": "The cabin was away from the main road for three hours yesterday.",
      "is_correct": false
    },
    {
      "text": "The cabin is located two miles away from the main road.",
      "is_correct": true
    },
    {
      "text": "The bakery sells fresh bread two miles away from happiness.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: a place cannot be distant from itself, making the sentence logically incoherent. semantic: 'away from' requires a physical or locational reference point, not an abstract concept like happiness. semantic: this implies the cabin temporarily left its location, but buildings are fixed and cannot be 'away' in the sense of absence.",
  "target_word": "away"
}
```

#### Pack B
### Level 6 (sense 15328, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The cabin is located two miles away from itself.",
      "is_correct": false
    },
    {
      "text": "The cabin was away from the main road for three hours yesterday.",
      "is_correct": false
    },
    {
      "text": "The cabin is located two miles away from the main road.",
      "is_correct": true
    },
    {
      "text": "The bakery sells fresh bread two miles away from happiness.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: a place cannot be distant from itself, making the sentence logically incoherent. semantic: 'away from' requires a physical or locational reference point, not an abstract concept like happiness. semantic: this implies the cabin temporarily left its location, but buildings are fixed and cannot be 'away' in the sense of absence.",
  "target_word": "away"
}
```

---

## sense 15328, level 9

#### Pack A
### Level 9 (sense 15328, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "My best friend moved away to another city last summer."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "My best friend moved away to another city last summer.",
  "chunks": [
    "My best friend",
    "moved",
    "away to another city",
    "last summer"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "away to another city",
    "My best friend",
    "last summer",
    "moved"
  ],
  "target_word": "away",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They ran away from the noise in the dark forest."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They ran away from the noise in the dark forest.",
  "chunks": [
    "They",
    "ran",
    "away from the noise in the dark forest"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "away from the noise in the dark forest",
    "ran",
    "They"
  ],
  "target_word": "away",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 15328, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "My best friend moved away to another city last summer."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "My best friend moved away to another city last summer.",
  "chunks": [
    "My best friend",
    "moved",
    "away to another city",
    "last summer"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "away to another city",
    "My best friend",
    "last summer",
    "moved"
  ],
  "target_word": "away",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They ran away from the noise in the dark forest."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They ran away from the noise in the dark forest.",
  "chunks": [
    "They",
    "ran",
    "away from the noise in the dark forest"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "away from the noise in the dark forest",
    "ran",
    "They"
  ],
  "target_word": "away",
  "chunk_count": 3
}
```

---

## sense 16031, level 2

#### Pack A
### Level 2 (sense 16031, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "correct_definition": "To make something so full of water that it cannot float.",
  "options": [
    "To make something so full of water that it cannot float.",
    "Music that is pleasant and enjoyable to hear.",
    "A fundamental change in the underlying assumptions or methods of a field or system.",
    "to change or make something change into a different form, system, or purpose."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Coming at the end of a process or series; last.",
        "To make something so full of water that it cannot float.",
        "relating to art or being good at making art",
        "The existence or availability of something in a particular place or situation."
      ],
      "correct_answer": "To make something so full of water that it cannot float."
    }
  }
}
```

#### Pack B
### Level 2 (sense 16031, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "correct_definition": "To make something so full of water that it cannot float.",
  "options": [
    "To make something so full of water that it cannot float.",
    "Music that is pleasant and enjoyable to hear.",
    "A fundamental change in the underlying assumptions or methods of a field or system.",
    "to change or make something change into a different form, system, or purpose."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Coming at the end of a process or series; last.",
        "To make something so full of water that it cannot float.",
        "relating to art or being good at making art",
        "The existence or availability of something in a particular place or situation."
      ],
      "correct_answer": "To make something so full of water that it cannot float."
    }
  }
}
```

---

## sense 16031, level 3

#### Pack A
### Level 3 (sense 16031, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "They plan to waterlog the timber logs in the basin to prevent them from drying out and cracking before construction.",
  "original_sentence": "They plan to waterlog the timber logs in the basin to prevent them from drying out and cracking before construction.",
  "correct_answer": "waterlog",
  "options": [
    "dry",
    "polish",
    "measure",
    "waterlog"
  ],
  "explanation": "Correct: this is the exact verb form used in the sentence, meaning to soak the logs so fully that they cannot float.",
  "distractor_tags": {},
  "word_definition": "To make something so full of water that it cannot float.",
  "target_word": "waterlogged"
}
```

#### Pack B
### Level 3 (sense 16031, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "They plan to waterlog the timber logs in the basin to prevent them from drying out and cracking before construction.",
  "original_sentence": "They plan to waterlog the timber logs in the basin to prevent them from drying out and cracking before construction.",
  "correct_answer": "waterlog",
  "options": [
    "dry",
    "polish",
    "measure",
    "waterlog"
  ],
  "explanation": "Correct: this is the exact verb form used in the sentence, meaning to soak the logs so fully that they cannot float.",
  "distractor_tags": {},
  "word_definition": "To make something so full of water that it cannot float.",
  "target_word": "waterlogged"
}
```

---

## sense 16031, level 4

#### Pack A
### Level 4 (sense 16031, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Heavy rains will ___ the garden beds if the soil cannot drain properly.",
  "original_sentence": "Heavy rains will waterlog the garden beds if the soil cannot drain properly.",
  "target_word": "waterlog",
  "word": "waterlogged",
  "answer": {
    "accepted": [
      "waterlog"
    ],
    "accepted_normalized": [
      "waterlog"
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
  "stem": "waterlog",
  "sentence_with_blank": "Heavy rains will ___ the garden beds if the soil cannot drain properly.",
  "original_sentence": "Heavy rains will waterlog the garden beds if the soil cannot drain properly.",
  "required_pos": "verb",
  "options": [
    "waterlogate",
    "waterlogen",
    "waterlogify",
    "waterlog"
  ],
  "correct_answer": "waterlog",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base verb form required after the modal 'will'"
    }
  }
}
```

#### Pack B
### Level 4 (sense 16031, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Heavy rains will ___ the garden beds if the soil cannot drain properly.",
  "original_sentence": "Heavy rains will waterlog the garden beds if the soil cannot drain properly.",
  "target_word": "waterlog",
  "word": "waterlogged",
  "answer": {
    "accepted": [
      "waterlog"
    ],
    "accepted_normalized": [
      "waterlog"
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
  "stem": "waterlog",
  "sentence_with_blank": "Heavy rains will ___ the garden beds if the soil cannot drain properly.",
  "original_sentence": "Heavy rains will waterlog the garden beds if the soil cannot drain properly.",
  "required_pos": "verb",
  "options": [
    "waterlogate",
    "waterlogen",
    "waterlogify",
    "waterlog"
  ],
  "correct_answer": "waterlog",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base verb form required after the modal 'will'"
    }
  }
}
```

---

## sense 16031, level 6

#### Pack A
### Level 6 (sense 16031, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "relation": "antonym",
  "options": [
    "saturate",
    "soak",
    "irrigate",
    "drain"
  ],
  "correct_answer": "drain",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To make something so full of water that it cannot float.",
      "explanation": "antonym: to remove water so something becomes light enough to float"
    }
  }
}
```

#### Pack B
### Level 6 (sense 16031, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "relation": "antonym",
  "options": [
    "saturate",
    "soak",
    "irrigate",
    "drain"
  ],
  "correct_answer": "drain",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To make something so full of water that it cannot float.",
      "explanation": "antonym: to remove water so something becomes light enough to float"
    }
  }
}
```

---

## sense 16031, level 9

#### Pack A
### Level 9 (sense 16031, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "If you leave the cardboard box in the rain, the moisture will quickly waterlog it."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you leave the cardboard box in the rain, the moisture will quickly waterlog it.",
  "chunks": [
    "If you leave the cardboard box in the rain",
    "the moisture",
    "will waterlog",
    "quickly",
    "it"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "the moisture",
    "If you leave the cardboard box in the rain",
    "will waterlog",
    "quickly",
    "it"
  ],
  "target_word": "waterlog",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 16031, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "If you leave the cardboard box in the rain, the moisture will quickly waterlog it."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you leave the cardboard box in the rain, the moisture will quickly waterlog it.",
  "chunks": [
    "If you leave the cardboard box in the rain",
    "the moisture",
    "will waterlog",
    "quickly",
    "it"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "the moisture",
    "If you leave the cardboard box in the rain",
    "will waterlog",
    "quickly",
    "it"
  ],
  "target_word": "waterlog",
  "chunk_count": 5
}
```

---

## sense 16181, level 2

#### Pack A
### Level 2 (sense 16181, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "wel",
  "correct_definition": "In a satisfactory or proper manner.",
  "options": [
    "A material or substance used to fill a gap, cavity, or increase the bulk of something.",
    "In a satisfactory or proper manner.",
    "A particular method or way of doing something, especially one that involves skill or practice.",
    "Pe is the 17th letter of the Hebrew alphabet, used in writing Hebrew."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "wel",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "coming after number ten",
        "available for anyone to participate in or respond to.",
        "Shaped like a circle; also, describing a system in which materials are used again rather than thrown away.",
        "In a satisfactory or proper manner."
      ],
      "correct_answer": "In a satisfactory or proper manner."
    }
  }
}
```

#### Pack B
### Level 2 (sense 16181, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "wel",
  "correct_definition": "In a satisfactory or proper manner.",
  "options": [
    "A material or substance used to fill a gap, cavity, or increase the bulk of something.",
    "In a satisfactory or proper manner.",
    "A particular method or way of doing something, especially one that involves skill or practice.",
    "Pe is the 17th letter of the Hebrew alphabet, used in writing Hebrew."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "wel",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "coming after number ten",
        "available for anyone to participate in or respond to.",
        "Shaped like a circle; also, describing a system in which materials are used again rather than thrown away.",
        "In a satisfactory or proper manner."
      ],
      "correct_answer": "In a satisfactory or proper manner."
    }
  }
}
```

---

## sense 16181, level 9

#### Pack A
### Level 9 (sense 16181, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Everything worked out better in the end for everyone."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Everything worked out better in the end for everyone.",
  "chunks": [
    "Everything worked out",
    "better",
    "in the end for everyone"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in the end for everyone",
    "better",
    "Everything worked out"
  ],
  "target_word": "well",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 16181, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Everything worked out better in the end for everyone."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Everything worked out better in the end for everyone.",
  "chunks": [
    "Everything worked out",
    "better",
    "in the end for everyone"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in the end for everyone",
    "better",
    "Everything worked out"
  ],
  "target_word": "well",
  "chunk_count": 3
}
```

---

## sense 19458, level 2

#### Pack A
### Level 2 (sense 19458, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "pronunciation": "nuhn-thuh-les",
  "correct_definition": "despite what has just been said; nevertheless",
  "options": [
    "An arm is one of the two upper limbs of the human body, extending from the shoulder to the hand.",
    "despite what has just been said; nevertheless",
    "knowing or seeming to know everything",
    "Relating to business or trade, or an advertisement on TV or radio."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "pronunciation": "nuhn-thuh-les",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A position or way of thinking about an issue, or a physical position of the body.",
        "despite what has just been said; nevertheless",
        "To make something bigger.",
        "A container made of cloth, paper, or plastic, used for carrying things."
      ],
      "correct_answer": "despite what has just been said; nevertheless"
    }
  }
}
```

#### Pack B
### Level 2 (sense 19458, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "pronunciation": "nuhn-thuh-les",
  "correct_definition": "despite what has just been said; nevertheless",
  "options": [
    "An arm is one of the two upper limbs of the human body, extending from the shoulder to the hand.",
    "despite what has just been said; nevertheless",
    "knowing or seeming to know everything",
    "Relating to business or trade, or an advertisement on TV or radio."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "pronunciation": "nuhn-thuh-les",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A position or way of thinking about an issue, or a physical position of the body.",
        "despite what has just been said; nevertheless",
        "To make something bigger.",
        "A container made of cloth, paper, or plastic, used for carrying things."
      ],
      "correct_answer": "despite what has just been said; nevertheless"
    }
  }
}
```

---
