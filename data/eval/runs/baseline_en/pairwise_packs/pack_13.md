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


## sense 19458, level 3

#### Pack A
### Level 3 (sense 19458, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The weather was cold and rainy, but they went hiking ___.",
  "original_sentence": "The weather was cold and rainy, but they went hiking nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "beforehand",
    "nonetheless",
    "obviously",
    "similarly"
  ],
  "explanation": "Correctly signals contrast between the bad weather and their decision to hike anyway.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Traffic was terrible this morning; ___, she arrived at school on time.",
  "original_sentence": "Traffic was terrible this morning; nonetheless, she arrived at school on time.",
  "correct_answer": "nonetheless",
  "options": [
    "nonetheless",
    "therefore",
    "consequently",
    "meanwhile"
  ],
  "explanation": "Correctly signals contrast: despite bad traffic, she still arrived on time.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```

#### Pack B
### Level 3 (sense 19458, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The weather was cold and rainy, but they went hiking ___.",
  "original_sentence": "The weather was cold and rainy, but they went hiking nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "beforehand",
    "nonetheless",
    "obviously",
    "similarly"
  ],
  "explanation": "Correctly signals contrast between the bad weather and their decision to hike anyway.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Traffic was terrible this morning; ___, she arrived at school on time.",
  "original_sentence": "Traffic was terrible this morning; nonetheless, she arrived at school on time.",
  "correct_answer": "nonetheless",
  "options": [
    "nonetheless",
    "therefore",
    "consequently",
    "meanwhile"
  ],
  "explanation": "Correctly signals contrast: despite bad traffic, she still arrived on time.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```

---

## sense 19458, level 4

#### Pack A
### Level 4 (sense 19458, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She had studied all night for the exam and felt exhausted, but she passed ___.",
  "original_sentence": "She had studied all night for the exam and felt exhausted, but she passed nonetheless.",
  "target_word": "nonetheless",
  "word": "nonetheless",
  "answer": {
    "accepted": [
      "nonetheless"
    ],
    "accepted_normalized": [
      "nonetheless"
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
  "sentence_with_blank": "The instructions were confusing, yet he completed the assignment correctly ___.",
  "original_sentence": "The instructions were confusing, yet he completed the assignment correctly nonetheless.",
  "target_word": "nonetheless",
  "word": "nonetheless",
  "answer": {
    "accepted": [
      "nonetheless"
    ],
    "accepted_normalized": [
      "nonetheless"
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
### Level 4 (sense 19458, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She had studied all night for the exam and felt exhausted, but she passed ___.",
  "original_sentence": "She had studied all night for the exam and felt exhausted, but she passed nonetheless.",
  "target_word": "nonetheless",
  "word": "nonetheless",
  "answer": {
    "accepted": [
      "nonetheless"
    ],
    "accepted_normalized": [
      "nonetheless"
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
  "sentence_with_blank": "The instructions were confusing, yet he completed the assignment correctly ___.",
  "original_sentence": "The instructions were confusing, yet he completed the assignment correctly nonetheless.",
  "target_word": "nonetheless",
  "word": "nonetheless",
  "answer": {
    "accepted": [
      "nonetheless"
    ],
    "accepted_normalized": [
      "nonetheless"
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

## sense 19458, level 6

#### Pack A
### Level 6 (sense 19458, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He knew the task was difficult, but he tried his best nonetheless.",
      "is_correct": true
    },
    {
      "text": "She likes chocolate ice cream nonetheless.",
      "is_correct": false
    },
    {
      "text": "The sun rose in the east nonetheless.",
      "is_correct": false
    },
    {
      "text": "He is happy today, nonetheless he laughed at the joke.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: there is no preceding contrasting statement, so 'nonetheless' has nothing to contrast with. Incorrect: this is a simple factual statement with no prior contrast, making 'nonetheless' logically out of place. Incorrect: laughing at a joke naturally follows from being happy, so there is no contrast for 'nonetheless' to signal.",
  "target_word": "nonetheless"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She was excited about the party, and she baked a cake nonetheless.",
      "is_correct": false
    },
    {
      "text": "The soup was delicious, so I ate it nonetheless.",
      "is_correct": false
    },
    {
      "text": "The climb up the mountain was steep, but the view from the top was worth it nonetheless.",
      "is_correct": true
    },
    {
      "text": "He is tall and strong; nonetheless, he plays basketball well.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: there is no contrast or obstacle here; 'nonetheless' requires a preceding statement that conflicts with the result. Incorrect: being tall and strong logically supports playing basketball well, so using 'nonetheless' creates an illogical contrast. Incorrect: 'so' already marks a causal reason, making 'nonetheless' redundant and contradictory in this context.",
  "target_word": "nonetheless"
}
```

#### Pack B
### Level 6 (sense 19458, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He knew the task was difficult, but he tried his best nonetheless.",
      "is_correct": true
    },
    {
      "text": "She likes chocolate ice cream nonetheless.",
      "is_correct": false
    },
    {
      "text": "The sun rose in the east nonetheless.",
      "is_correct": false
    },
    {
      "text": "He is happy today, nonetheless he laughed at the joke.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: there is no preceding contrasting statement, so 'nonetheless' has nothing to contrast with. Incorrect: this is a simple factual statement with no prior contrast, making 'nonetheless' logically out of place. Incorrect: laughing at a joke naturally follows from being happy, so there is no contrast for 'nonetheless' to signal.",
  "target_word": "nonetheless"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She was excited about the party, and she baked a cake nonetheless.",
      "is_correct": false
    },
    {
      "text": "The soup was delicious, so I ate it nonetheless.",
      "is_correct": false
    },
    {
      "text": "The climb up the mountain was steep, but the view from the top was worth it nonetheless.",
      "is_correct": true
    },
    {
      "text": "He is tall and strong; nonetheless, he plays basketball well.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: there is no contrast or obstacle here; 'nonetheless' requires a preceding statement that conflicts with the result. Incorrect: being tall and strong logically supports playing basketball well, so using 'nonetheless' creates an illogical contrast. Incorrect: 'so' already marks a causal reason, making 'nonetheless' redundant and contradictory in this context.",
  "target_word": "nonetheless"
}
```

---

## sense 19458, level 9

#### Pack A
### Level 9 (sense 19458, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Nonetheless, many students found the science project exciting and fun."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Nonetheless, many students found the science project exciting and fun.",
  "chunks": [
    "Nonetheless",
    "many students",
    "found",
    "the science project exciting and fun"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "many students",
    "Nonetheless",
    "found",
    "the science project exciting and fun"
  ],
  "target_word": "Nonetheless",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "He knew the task was difficult, but he tried his best nonetheless."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He knew the task was difficult, but he tried his best nonetheless.",
  "chunks": [
    "He knew",
    "the task was difficult",
    "but he tried his best nonetheless"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "but he tried his best nonetheless",
    "the task was difficult",
    "He knew"
  ],
  "target_word": "nonetheless",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 19458, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Nonetheless, many students found the science project exciting and fun."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Nonetheless, many students found the science project exciting and fun.",
  "chunks": [
    "Nonetheless",
    "many students",
    "found",
    "the science project exciting and fun"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "many students",
    "Nonetheless",
    "found",
    "the science project exciting and fun"
  ],
  "target_word": "Nonetheless",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "He knew the task was difficult, but he tried his best nonetheless."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He knew the task was difficult, but he tried his best nonetheless.",
  "chunks": [
    "He knew",
    "the task was difficult",
    "but he tried his best nonetheless"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "but he tried his best nonetheless",
    "the task was difficult",
    "He knew"
  ],
  "target_word": "nonetheless",
  "chunk_count": 3
}
```

---

## sense 19480, level 2

#### Pack A
### Level 2 (sense 19480, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "pronunciation": "eh-kwuh-tuh-bly",
  "correct_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "options": [
    "In a way that is fair and just, giving equal treatment to everyone involved.",
    "To get rid of something that is no longer useful or wanted.",
    "a town or city that has its own local government and can make its own laws",
    "The appearance of things as a result of the way they reflect light; a particular shade such as red, green, etc."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "pronunciation": "eh-kwuh-tuh-bly",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To interrupt or cause something to stop working or happening normally.",
        "A disease is a condition that causes harm to the body or mind and is not caused by an injury.",
        "In a way that is fair and just, giving equal treatment to everyone involved.",
        "Saying good things about an idea to help it."
      ],
      "correct_answer": "In a way that is fair and just, giving equal treatment to everyone involved."
    }
  }
}
```

#### Pack B
### Level 2 (sense 19480, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "pronunciation": "eh-kwuh-tuh-bly",
  "correct_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "options": [
    "In a way that is fair and just, giving equal treatment to everyone involved.",
    "To get rid of something that is no longer useful or wanted.",
    "a town or city that has its own local government and can make its own laws",
    "The appearance of things as a result of the way they reflect light; a particular shade such as red, green, etc."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "pronunciation": "eh-kwuh-tuh-bly",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To interrupt or cause something to stop working or happening normally.",
        "A disease is a condition that causes harm to the body or mind and is not caused by an injury.",
        "In a way that is fair and just, giving equal treatment to everyone involved.",
        "Saying good things about an idea to help it."
      ],
      "correct_answer": "In a way that is fair and just, giving equal treatment to everyone involved."
    }
  }
}
```

---

## sense 19480, level 3

#### Pack A
### Level 3 (sense 19480, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The teacher divided the supplies ___ among all the students in the class.",
  "original_sentence": "The teacher divided the supplies equitably among all the students in the class.",
  "correct_answer": "equitably",
  "options": [
    "hastily",
    "rarely",
    "noisily",
    "equitably"
  ],
  "explanation": "Correct: matches the sentence, describing a fair division of supplies among students.",
  "distractor_tags": {},
  "word_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "target_word": "equitably"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The council members voted to manage the community funds ___.",
  "original_sentence": "The council members voted to manage the community funds equitably.",
  "correct_answer": "equitably",
  "options": [
    "urgently",
    "occasionally",
    "loudly",
    "equitably"
  ],
  "explanation": "Correct: it describes managing the funds in a fair, equal way, matching the sentence's context of council decision-making.",
  "distractor_tags": {},
  "word_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "target_word": "equitably"
}
```

#### Pack B
### Level 3 (sense 19480, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The teacher divided the supplies ___ among all the students in the class.",
  "original_sentence": "The teacher divided the supplies equitably among all the students in the class.",
  "correct_answer": "equitably",
  "options": [
    "hastily",
    "rarely",
    "noisily",
    "equitably"
  ],
  "explanation": "Correct: matches the sentence, describing a fair division of supplies among students.",
  "distractor_tags": {},
  "word_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "target_word": "equitably"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The council members voted to manage the community funds ___.",
  "original_sentence": "The council members voted to manage the community funds equitably.",
  "correct_answer": "equitably",
  "options": [
    "urgently",
    "occasionally",
    "loudly",
    "equitably"
  ],
  "explanation": "Correct: it describes managing the funds in a fair, equal way, matching the sentence's context of council decision-making.",
  "distractor_tags": {},
  "word_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "target_word": "equitably"
}
```

---

## sense 19480, level 4

#### Pack A
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
