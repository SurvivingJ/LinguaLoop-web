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


## sense 19480, level 4

#### Pack A
### Level 4 (sense 19480, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Group members worked hard to distribute the project tasks ___ so that no one felt overwhelmed.",
  "original_sentence": "Group members worked hard to distribute the project tasks equitably so that no one felt overwhelmed.",
  "target_word": "equitably",
  "word": "equitably",
  "answer": {
    "accepted": [
      "equitably",
      "equitable",
      "equitability",
      "equity"
    ],
    "accepted_normalized": [
      "equitably",
      "equitable",
      "equitability",
      "equity"
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
  "sentence_with_blank": "Our class treasurer tried to spend the club funds ___ on supplies for everyone.",
  "original_sentence": "Our class treasurer tried to spend the club funds equitably on supplies for everyone.",
  "target_word": "equitably",
  "word": "equitably",
  "answer": {
    "accepted": [
      "equitably",
      "equitable",
      "equitability",
      "equity"
    ],
    "accepted_normalized": [
      "equitably",
      "equitable",
      "equitability",
      "equity"
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
### Level 4 (sense 19480, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "We must share the project tasks ___ so nobody feels overwhelmed.",
  "original_sentence": "We must share the project tasks equitably so nobody feels overwhelmed.",
  "target_word": "equitably",
  "word": "equitably",
  "answer": {
    "accepted": [
      "equitably",
      "equitable"
    ],
    "accepted_normalized": [
      "equitably",
      "equitable"
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
  "sentence_with_blank": "She ensured that the responsibilities were assigned ___ across the department.",
  "original_sentence": "She ensured that the responsibilities were assigned equitably across the department.",
  "target_word": "equitably",
  "word": "equitably",
  "answer": {
    "accepted": [
      "equitably",
      "equitable"
    ],
    "accepted_normalized": [
      "equitably",
      "equitable"
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
  "stem": "equitable",
  "sentence_with_blank": "She ensured that the responsibilities were assigned ___ across the department.",
  "original_sentence": "She ensured that the responsibilities were assigned equitably across the department.",
  "required_pos": "adverb",
  "options": [
    "equitablement",
    "equitably",
    "equitablic",
    "equitablely"
  ],
  "correct_answer": "equitably",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb form meaning fairly and justly"
    }
  }
}
```

---

## sense 19480, level 6

#### Pack A
### Level 6 (sense 19480, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef chopped the onions equitably, ensuring every piece was exactly the same size.",
      "is_correct": false
    },
    {
      "text": "The sun shone equitably on the plants, giving each one the exact same amount of light.",
      "is_correct": false
    },
    {
      "text": "Resources should be divided equitably across all the different clubs at our school.",
      "is_correct": true
    },
    {
      "text": "She equitably tied her shoes so that both laces were perfectly symmetrical.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' refers to fairness and justice in human treatment or resource distribution, not the physical, geometric precision of chopping vegetables. Semantically inappropriate: 'Equitably' requires an agent capable of moral reasoning and intent; natural phenomena like the sun cannot act with a sense of justice or fairness. Pragmatically inappropriate: 'Equitably' describes fair treatment of people or distribution of resources, not the physical symmetry or aesthetic balance of tying shoelaces.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "proportionally",
    "adequately",
    "unfairly",
    "equally"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: means in a way that is not fair or just to everyone involved"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef chopped the vegetables equitably so that they would cook at the exact same speed in the pan.",
      "is_correct": false
    },
    {
      "text": "She equitably tied her shoelaces before going for a long run in the park.",
      "is_correct": false
    },
    {
      "text": "The discussion leader ensured that all participants could speak equitably during the debate.",
      "is_correct": true
    },
    {
      "text": "The sun shone equitably on the flowers in the garden, helping them all grow tall.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' refers to moral fairness and justice among people, not the physical uniformity of chopped vegetables (which would be 'uniformly' or 'evenly'). Semantically inappropriate: Tying shoelaces is a physical action that does not involve treating multiple parties fairly or justly. Semantically inappropriate: Natural phenomena like sunlight cannot possess moral agency or distribute resources with a sense of justice; 'equally' would be the correct word here.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "impartially",
    "equally",
    "reasonably",
    "unfairly"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: in a way that is not fair or just to everyone"
    }
  }
}
```

#### Pack B
### Level 6 (sense 19480, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef equitably burned the toast this morning.",
      "is_correct": false
    },
    {
      "text": "They agreed to resolve the dispute by sharing the resources equitably.",
      "is_correct": true
    },
    {
      "text": "The thief equitably stole the jewels from the museum.",
      "is_correct": false
    },
    {
      "text": "She ran equitably to catch the bus before it left.",
      "is_correct": false
    }
  ],
  "explanation": "Stealing is an unfair act by nature, so pairing it with 'equitably' creates a logical contradiction. Running to catch a bus is a physical action with no element of fairness or shared distribution, making the adverb inappropriate. Burning toast is an accidental, single-outcome event, not something that can be done in a fair or equal manner.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "unfairly",
    "diplomatically",
    "generously",
    "cautiously"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: treating people unequally or unjustly, opposite of the target sense"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The runner finished the race equitably in record time.",
      "is_correct": false
    },
    {
      "text": "The artist painted the mural equitably with bright colors.",
      "is_correct": false
    },
    {
      "text": "They have always handled disagreements equitably and calmly.",
      "is_correct": true
    },
    {
      "text": "The chef seasoned the soup equitably before serving it.",
      "is_correct": false
    }
  ],
  "explanation": "Seasoning a soup is a single culinary act with no parties needing fair or equal treatment, so 'equitably' doesn't fit. Finishing a race is about speed and personal performance, not about distributing something fairly among people. Choosing colors for a painting is an aesthetic choice, not a matter of fairness or equal treatment, so 'equitably' is misapplied.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "generously",
    "equally",
    "unfairly",
    "harshly"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "true antonym: treating people unequally or unjustly"
    }
  }
}
```

---

## sense 19480, level 9

#### Pack A
### Level 9 (sense 19480, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Friends can avoid arguments by deciding things equitably when they plan activities together."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Friends can avoid arguments by deciding things equitably when they plan activities together.",
  "chunks": [
    "Friends",
    "can avoid",
    "arguments",
    "by deciding things equitably when they plan activities together"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "can avoid",
    "by deciding things equitably when they plan activities together",
    "arguments",
    "Friends"
  ],
  "target_word": "equitably",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Resources should be divided equitably across all the different clubs at our school."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Resources should be divided equitably across all the different clubs at our school.",
  "chunks": [
    "Resources",
    "should be divided",
    "equitably",
    "across all the different clubs",
    "at our school"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "equitably",
    "should be divided",
    "across all the different clubs",
    "Resources",
    "at our school"
  ],
  "target_word": "equitably",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 19480, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Our coach treated everyone equitably during the team tryouts."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Our coach treated everyone equitably during the team tryouts.",
  "chunks": [
    "Our coach",
    "treated",
    "everyone",
    "equitably",
    "during the team",
    "tryouts"
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
    "equitably",
    "treated",
    "during the team",
    "everyone",
    "tryouts",
    "Our coach"
  ],
  "target_word": "equitably",
  "chunk_count": 6
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They agreed to resolve the dispute by sharing the resources equitably."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They agreed to resolve the dispute by sharing the resources equitably.",
  "chunks": [
    "They",
    "agreed",
    "to resolve the dispute by sharing the resources equitably"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "agreed",
    "They",
    "to resolve the dispute by sharing the resources equitably"
  ],
  "target_word": "equitably",
  "chunk_count": 3
}
```

---

## sense 19521, level 1

#### Pack A
### Level 1 (sense 19521, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "ipa": "/ˈnaɪn.tiːnθ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "nineteen",
    "nineteenth",
    "ninth",
    "ninetieth"
  ],
  "correct_answer": "nineteenth",
  "explanation": "Correct target word.",
  "distractor_explanations": {
    "nineteen": "Minimal pair: differs only in the missing final /θ/ sound.",
    "ninth": "Minimal pair: differs by the omission of the /tiːn/ syllable.",
    "ninetieth": "Near-homophone: differs in the second syllable vowel /iː/ vs /i/ and overall syllable structure."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 19521, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "ipa": "/ˈnaɪn.tiːnθ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "nineteenth",
    "ninth",
    "nineteen",
    "ninetieth"
  ],
  "correct_answer": "nineteenth",
  "explanation": "This is the target word exactly as it would be spoken and written.",
  "distractor_explanations": {
    "nineteen": "Near-homophone: sounds almost identical but drops the final /θ/ sound, changing it from an ordinal to a cardinal number.",
    "ninetieth": "Minimal pair: very similar syllable rhythm and stress, but refers to the ordinal of ninety, not nineteen.",
    "ninth": "Rhymes with the ending '-nth' of the target but is a much shorter word, easily confused in fast speech."
  },
  "distractor_source": "llm"
}
```

---

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
    "To watch or notice something carefully, especially to learn something.",
    "In a way that is fixed or fastened so that it cannot move or be taken away.",
    "Coming next after the eighteenth in a series.",
    "The act of repeating a process or action, often to improve it."
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
        "To go from one side to the other.",
        "Coming next after the eighteenth in a series.",
        "To change something by adding the latest information or making it more modern.",
        "To narrate or recount a sequence of events."
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
    "nineteenth",
    "twentieth",
    "continuous",
    "biannual"
  ],
  "explanation": "Correct ordinal adjective indicating the specific age being celebrated.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They are studying ___-century history in social studies class.",
  "original_sentence": "They are studying nineteenth-century history in social studies class.",
  "correct_answer": "nineteenth",
  "options": [
    "umpteenth",
    "several",
    "nineteenth",
    "hourly"
  ],
  "explanation": "Correct ordinal adjective for the century.",
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
  "sentence_with_blank": "He is reading the ___ chapter of the book.",
  "original_sentence": "He is reading the nineteenth chapter of the book.",
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
  "sentence_with_blank": "He is reading the ___ chapter of the book.",
  "original_sentence": "He is reading the nineteenth chapter of the book.",
  "required_pos": "adjective",
  "options": [
    "nineteenment",
    "nineteenth",
    "nineteenic",
    "nineteenation"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal adjective formed by adding -th to the cardinal nineteen"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "I noticed the ___ item on the list was missing.",
  "original_sentence": "I noticed the nineteenth item on the list was missing.",
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
  "sentence_with_blank": "I noticed the ___ item on the list was missing.",
  "original_sentence": "I noticed the nineteenth item on the list was missing.",
  "required_pos": "adjective",
  "options": [
    "nineteenth",
    "nineteenic",
    "nineteenal",
    "nineteenment"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal adjective formed from nineteen with the -th suffix"
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
      "text": "Our team finished in nineteenth place during the tournament.",
      "is_correct": true
    },
    {
      "text": "The nineteenth letter of the English alphabet is 'Z'.",
      "is_correct": false
    },
    {
      "text": "He was the nineteenth person to walk on the moon.",
      "is_correct": false
    },
    {
      "text": "The nineteenth day of the week is dedicated to resting.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic: logically impossible and pragmatically inappropriate because there are only seven days in a standard week. Semantic: factually incorrect and pragmatically inappropriate since only twelve people have walked on the moon to date. Semantic: factually incorrect as the nineteenth letter of the alphabet is 'S', not 'Z'.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "His artwork was featured on the nineteenth page of the magazine.",
      "is_correct": true
    },
    {
      "text": "The nineteenth side of the square was painted a bright blue color.",
      "is_correct": false
    },
    {
      "text": "She carefully poured the nineteenth water into the mixing bowl.",
      "is_correct": false
    },
    {
      "text": "The nineteenth month of the year always brings the first snow.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: there are only twelve months in a year, making a nineteenth month logically impossible. semantic: 'water' is an uncountable mass noun and cannot be sequentially enumerated with an ordinal number. semantic: a square is geometrically defined as having exactly four sides, so a nineteenth side cannot exist.",
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
  "original_sentence": "She was the nineteenth person to arrive at the meeting."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She was the nineteenth person to arrive at the meeting.",
  "chunks": [
    "She",
    "was",
    "the nineteenth person to arrive at the meeting"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "was",
    "the nineteenth person to arrive at the meeting",
    "She"
  ],
  "target_word": "nineteenth",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Our team finished in nineteenth place during the tournament."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Our team finished in nineteenth place during the tournament.",
  "chunks": [
    "Our team",
    "finished",
    "in nineteenth place",
    "during the tournament"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "finished",
    "in nineteenth place",
    "Our team",
    "during the tournament"
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
    "Great Wall of Chino",
    "Great Wall of China",
    "Grate Wall of China",
    "Great Whale of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "This is the exact correct spelling and pronunciation of the target proper noun phrase.",
  "distractor_explanations": {
    "Grate Wall of China": "homophone: 'grate' has the exact same /ɡreɪt/ sound as 'great', but different spelling and meaning.",
    "Great Whale of China": "minimal pair: 'whale' differs from 'wall' only in the vowel sound /iː/ versus /ɔː/.",
    "Great Wall of Chino": "near-homophone: 'chino' sounds very similar to 'China', differing only in the final vowel /oʊ/ versus /ə/."
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
