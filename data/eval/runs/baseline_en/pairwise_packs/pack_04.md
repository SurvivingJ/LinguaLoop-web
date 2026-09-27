# Pairwise review pack 04

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


## sense 13981, level 3

#### Pack A
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He felt exhausted after finishing such a ___ science project over the weekend.",
  "original_sentence": "He felt exhausted after finishing such a demanding science project over the weekend.",
  "correct_answer": "demanding",
  "options": [
    "quick",
    "cheap",
    "colorful",
    "demanding"
  ],
  "explanation": "Correct: a demanding project requires great effort, matching the context of feeling exhausted.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He felt exhausted after finishing such a ___ science project over the weekend.",
  "original_sentence": "He felt exhausted after finishing such a demanding science project over the weekend.",
  "correct_answer": "demanding",
  "options": [
    "quick",
    "cheap",
    "colorful",
    "demanding"
  ],
  "explanation": "Correct: a demanding project requires great effort, matching the context of feeling exhausted.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 4

#### Pack A
### Level 4 (sense 13981, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Learning to speak a new language fluently is a slow and ___ process.",
  "original_sentence": "Learning to speak a new language fluently is a slow and demanding process.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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
### Level 4 (sense 13981, difficulty None)
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Learning to speak a new language fluently is a slow and ___ process.",
  "original_sentence": "Learning to speak a new language fluently is a slow and demanding process.",
  "target_word": "demanding",
  "word": "demanding",
  "answer": {
    "accepted": [
      "demanding",
      "demand",
      "demands",
      "demanded"
    ],
    "accepted_normalized": [
      "demanding",
      "demand",
      "demands",
      "demanded"
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

## sense 13981, level 6

#### Pack A
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather today is demanding, with clear skies and sunshine.",
      "is_correct": false
    },
    {
      "text": "She has always been a demanding leader who expects everyone to do their absolute best.",
      "is_correct": true
    },
    {
      "text": "The cake was very demanding because it tasted incredibly sweet.",
      "is_correct": false
    },
    {
      "text": "He gave her a demanding smile that lit up the whole room.",
      "is_correct": false
    }
  ],
  "explanation": "Demanding describes effort or expectation, not the taste of food, so this usage is semantically inappropriate. Calm, pleasant weather does not require effort or attention, making 'demanding' an odd, inappropriate choice here. A smile that lights up a room suggests warmth, not the effort or high expectations implied by 'demanding'.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather today is demanding, with clear skies and sunshine.",
      "is_correct": false
    },
    {
      "text": "She has always been a demanding leader who expects everyone to do their absolute best.",
      "is_correct": true
    },
    {
      "text": "The cake was very demanding because it tasted incredibly sweet.",
      "is_correct": false
    },
    {
      "text": "He gave her a demanding smile that lit up the whole room.",
      "is_correct": false
    }
  ],
  "explanation": "Demanding describes effort or expectation, not the taste of food, so this usage is semantically inappropriate. Calm, pleasant weather does not require effort or attention, making 'demanding' an odd, inappropriate choice here. A smile that lights up a room suggests warmth, not the effort or high expectations implied by 'demanding'.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 9

#### Pack A
### Level 9 (sense 13981, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind.",
  "chunks": [
    "Training for the marathon",
    "was",
    "a demanding experience that tested both his body and his mind"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a demanding experience that tested both his body and his mind",
    "Training for the marathon",
    "was"
  ],
  "target_word": "demanding",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13981, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Training for the marathon was a demanding experience that tested both his body and his mind.",
  "chunks": [
    "Training for the marathon",
    "was",
    "a demanding experience that tested both his body and his mind"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a demanding experience that tested both his body and his mind",
    "Training for the marathon",
    "was"
  ],
  "target_word": "demanding",
  "chunk_count": 3
}
```

---

## sense 14001, level 2

#### Pack A
### Level 2 (sense 14001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "correct_definition": "A set of connected parts that form a complex whole.",
  "options": [
    "A set of connected parts that form a complex whole.",
    "Removing the outer layer or skin from something, like a fruit or vegetable.",
    "A final point or limit of something, like a journey or a process.",
    "The ability to make good decisions based on knowledge and experience."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A set of connected parts that form a complex whole.",
        "When food changes and gets bubbles or a funny smell, it is fermenting.",
        "The lowest part or foundation of something, on which it rests or is built.",
        "potential dangers or harm to people's health."
      ],
      "correct_answer": "A set of connected parts that form a complex whole."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14001, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "correct_definition": "A set of connected parts that form a complex whole.",
  "options": [
    "A set of connected parts that form a complex whole.",
    "Removing the outer layer or skin from something, like a fruit or vegetable.",
    "A final point or limit of something, like a journey or a process.",
    "The ability to make good decisions based on knowledge and experience."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "systems",
  "pronunciation": "SIS-tuhm",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A set of connected parts that form a complex whole.",
        "When food changes and gets bubbles or a funny smell, it is fermenting.",
        "The lowest part or foundation of something, on which it rests or is built.",
        "potential dangers or harm to people's health."
      ],
      "correct_answer": "A set of connected parts that form a complex whole."
    }
  }
}
```

---

## sense 14001, level 4

#### Pack A
### Level 4 (sense 14001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "target_word": "system",
  "word": "systems",
  "answer": {
    "accepted": [
      "system"
    ],
    "accepted_normalized": [
      "system"
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
### Level 4 (sense 14001, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "target_word": "system",
  "word": "systems",
  "answer": {
    "accepted": [
      "system"
    ],
    "accepted_normalized": [
      "system"
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

## sense 14001, level 9

#### Pack A
### Level 9 (sense 14001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
  "chunks": [
    "This essential box",
    "utilizes",
    "a closed loop system filled with a special liquid called a refrigerant"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "This essential box",
    "a closed loop system filled with a special liquid called a refrigerant",
    "utilizes"
  ],
  "target_word": "system",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14001, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
  "chunks": [
    "This essential box",
    "utilizes",
    "a closed loop system filled with a special liquid called a refrigerant"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "This essential box",
    "a closed loop system filled with a special liquid called a refrigerant",
    "utilizes"
  ],
  "target_word": "system",
  "chunk_count": 3
}
```

---

## sense 14010, level 1

#### Pack A
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "defiant",
    "deferent",
    "different"
  ],
  "correct_answer": "different",
  "explanation": "Correct: this is the target word as naturally spoken and spelled.",
  "distractor_explanations": {
    "deferent": "Near-homophone: sounds almost identical to 'different' but means respectful or yielding, a different word.",
    "diffident": "Minimal pair: swaps the middle sound for /d/ instead of /r/, meaning shy or lacking confidence.",
    "defiant": "Rhymes closely with 'different' when heard quickly, but means openly resistant, a distinct word."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "defiant",
    "deferent",
    "different"
  ],
  "correct_answer": "different",
  "explanation": "Correct: this is the target word as naturally spoken and spelled.",
  "distractor_explanations": {
    "deferent": "Near-homophone: sounds almost identical to 'different' but means respectful or yielding, a different word.",
    "diffident": "Minimal pair: swaps the middle sound for /d/ instead of /r/, meaning shy or lacking confidence.",
    "defiant": "Rhymes closely with 'different' when heard quickly, but means openly resistant, a distinct word."
  },
  "distractor_source": "llm"
}
```

---

## sense 14010, level 2

#### Pack A
### Level 2 (sense 14010, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "correct_definition": "Not the same as another or each other; unlike.",
  "options": [
    "A device or person that roasts food, especially coffee beans or meat.",
    "Longer is used to say something continues for a greater amount of time than something else.",
    "Not the same as another or each other; unlike.",
    "The way in which you pronounce words or parts of words clearly and distinctly."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A job or position that suits someone’s skills and interests perfectly.",
        "Not the same as another or each other; unlike.",
        "To stay in a place or delay action until something expected happens.",
        "To recognize or show the difference between things."
      ],
      "correct_answer": "Not the same as another or each other; unlike."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14010, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "correct_definition": "Not the same as another or each other; unlike.",
  "options": [
    "A device or person that roasts food, especially coffee beans or meat.",
    "Longer is used to say something continues for a greater amount of time than something else.",
    "Not the same as another or each other; unlike.",
    "The way in which you pronounce words or parts of words clearly and distinctly."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-ruhnt",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A job or position that suits someone’s skills and interests perfectly.",
        "Not the same as another or each other; unlike.",
        "To stay in a place or delay action until something expected happens.",
        "To recognize or show the difference between things."
      ],
      "correct_answer": "Not the same as another or each other; unlike."
    }
  }
}
```

---

## sense 14010, level 3

#### Pack A
### Level 3 (sense 14010, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People see time in ___ ways.",
  "original_sentence": "People see time in different ways.",
  "correct_answer": "different",
  "options": [
    "different",
    "difficult",
    "similar",
    "distant"
  ],
  "explanation": "Correct: matches the original sentence, describing how people perceive time in varied, unlike ways.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We can learn about ___ perspectives.",
  "original_sentence": "We can learn about different perspectives.",
  "correct_answer": "different",
  "options": [
    "afraid",
    "expensive",
    "different",
    "curious"
  ],
  "explanation": "Correct: fits the sentence, meaning we can learn about perspectives that are not the same as each other.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

#### Pack B
### Level 3 (sense 14010, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People see time in ___ ways.",
  "original_sentence": "People see time in different ways.",
  "correct_answer": "different",
  "options": [
    "different",
    "difficult",
    "similar",
    "distant"
  ],
  "explanation": "Correct: matches the original sentence, describing how people perceive time in varied, unlike ways.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We can learn about ___ perspectives.",
  "original_sentence": "We can learn about different perspectives.",
  "correct_answer": "different",
  "options": [
    "afraid",
    "expensive",
    "different",
    "curious"
  ],
  "explanation": "Correct: fits the sentence, meaning we can learn about perspectives that are not the same as each other.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

---
