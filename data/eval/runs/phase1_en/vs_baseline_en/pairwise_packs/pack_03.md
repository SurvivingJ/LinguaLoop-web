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
      "text": "He brushed his teeth with green shoe polish.",
      "is_correct": false
    },
    {
      "text": "The green light told him to stop the car immediately.",
      "is_correct": false
    },
    {
      "text": "She wore a bright green jacket to the school party.",
      "is_correct": true
    },
    {
      "text": "The green blood pumped through his veins.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: a green traffic light signals drivers to go, not to stop. pragmatic: shoe polish is a toxic substance meant for leather, completely inappropriate for oral hygiene. semantic: human and most animal blood is red, making green blood biologically inaccurate in a standard context.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The snow on the mountain was bright green in the middle of winter.",
      "is_correct": false
    },
    {
      "text": "The blood from his cut was a vibrant shade of green.",
      "is_correct": false
    },
    {
      "text": "The sky is always green during a clear sunny day.",
      "is_correct": false
    },
    {
      "text": "The small frog sitting on the rock was dark green.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate because the sky is blue, not green, on a clear day. Semantically inappropriate because snow is naturally white, not green. Pragmatically inappropriate because human blood is red, not green.",
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
  "original_sentence": "They painted their old wooden treehouse completely green."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They painted their old wooden treehouse completely green.",
  "chunks": [
    "They",
    "painted",
    "their old wooden treehouse completely green"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "They",
    "their old wooden treehouse completely green",
    "painted"
  ],
  "target_word": "green",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "She wore a bright green jacket to the school party."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She wore a bright green jacket to the school party.",
  "chunks": [
    "She wore",
    "a bright green jacket",
    "to the school party"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She wore",
    "to the school party",
    "a bright green jacket"
  ],
  "target_word": "green",
  "chunk_count": 3
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
    "A layer of rock or sand that holds water and allows it to flow, used as a water source.",
    "at a great distance; a long way off",
    "An expert is a person who has special skill or knowledge in a particular subject.",
    "Diversity is the state of having a variety of different elements, such as cultures, backgrounds, or types."
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
        "A capital is a big city where the government works.",
        "at a great distance; a long way off",
        "Trade is when you give something and get something else.",
        "In a way that causes a major, basic change."
      ],
      "correct_answer": "at a great distance; a long way off"
    }
  }
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
  "sentence_with_blank": "My best friend moved ___ last summer, and I miss her terribly.",
  "original_sentence": "My best friend moved far away last summer, and I miss her terribly.",
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
  "sentence_with_blank": "They dreamed of traveling to a mysterious island ___ across the ocean.",
  "original_sentence": "They dreamed of traveling to a mysterious island far away across the ocean.",
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
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "elsewhere",
    "abroad",
    "nearby",
    "ahead"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "genuine antonym: at a short distance rather than a great one"
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
  "original_sentence": "She spotted the hidden cabin nestled far away in the dense mountain forest."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She spotted the hidden cabin nestled far away in the dense mountain forest.",
  "chunks": [
    "She",
    "spotted",
    "the hidden cabin nestled far away in the dense mountain forest"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "spotted",
    "She",
    "the hidden cabin nestled far away in the dense mountain forest"
  ],
  "target_word": "far away",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Is your new school far away from our house?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Is your new school far away from our house?",
  "chunks": [
    "Is",
    "your new school",
    "far away from our house"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "Is",
    "far away from our house",
    "your new school"
  ],
  "target_word": "far away",
  "chunk_count": 3
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
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "correct_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "options": [
    "Relating to the process of making laws or the group of people who make laws.",
    "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
    "The process of making something start to work or be used, such as a system, plan, or law.",
    "A person or company that buys goods from another country to sell in their own country."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "demanding",
  "pronunciation": "de-mand-ing",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
        "To keep someone or something safe from damage, injury, or loss.",
        "Paper is a thin material made from wood pulp, used for writing, printing, or wrapping.",
        "to develop into a clear form or idea"
      ],
      "correct_answer": "Needing a lot of effort, skill, or attention; expecting a lot from other people."
    }
  }
}
```

---

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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "fragile",
    "mandatory",
    "demanding",
    "stagnant"
  ],
  "explanation": "Correct: fits the context of a process requiring significant physical effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Balancing schoolwork and sports can be extremely ___ for teenagers.",
  "original_sentence": "Balancing schoolwork and sports can be extremely demanding for teenagers.",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "heavy",
    "sudden",
    "relaxing"
  ],
  "explanation": "The correct adjective describing a task that requires a lot of effort and attention.",
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
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
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
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
  "required_pos": "adjective",
  "options": [
    "demandation",
    "demandment",
    "demanding",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning requiring great effort or skill"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
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
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
  "required_pos": "adjective",
  "options": [
    "demandive",
    "demandity",
    "demanding",
    "demandous"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning needing effort"
    }
  }
}
```

---

## sense 13981, level 6

#### Pack A
### Level 6 (sense 13981, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The demanding puppy slept quietly in its bed all day, requiring absolutely no attention from its owners.",
      "is_correct": false
    },
    {
      "text": "That teacher is known for having a demanding grading policy that challenges all her students.",
      "is_correct": true
    },
    {
      "text": "The wooden chair is extremely demanding, often asking the room to rearrange its furniture.",
      "is_correct": false
    },
    {
      "text": "She found the taste of plain water to be very demanding, so she added sugar to it.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: inanimate objects like chairs do not possess the agency to have expectations or make requests of others. Semantically inappropriate: 'demanding' describes tasks or people requiring effort and attention, not the flavor profile of a basic liquid. Pragmatically inappropriate: 'demanding' means expecting a lot of attention, which directly contradicts the subsequent clause about requiring no attention.",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Breathing air is a highly demanding process that takes up all of our daily energy.",
      "is_correct": false
    },
    {
      "text": "They faced a demanding situation when the project deadline was suddenly moved forward.",
      "is_correct": true
    },
    {
      "text": "The water in the pool was very demanding, requiring a lot of effort to stay wet.",
      "is_correct": false
    },
    {
      "text": "The hallway was extremely demanding, stretching for over five miles without any turns.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'demanding' applies to tasks or people requiring effort or attention, not the physical state of water. pragmatic: breathing is an automatic, effortless process for a healthy person, contradicting the definition of needing a lot of effort. semantic: 'demanding' describes the requirement of effort or attention, not the physical length or spatial dimensions of a location.",
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
