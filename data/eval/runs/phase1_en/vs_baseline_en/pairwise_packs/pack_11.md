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


## sense 16031, level 4

#### Pack A
### Level 4 (sense 16031, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Heavy rains began to ___ the garden beds overnight.",
  "original_sentence": "Heavy rains began to waterlog the garden beds overnight.",
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

## sense 16031, level 9

#### Pack A
### Level 9 (sense 16031, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The constant rain threatened to waterlog the soccer ball, making it too heavy to kick properly."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The constant rain threatened to waterlog the soccer ball, making it too heavy to kick properly.",
  "chunks": [
    "The constant rain",
    "threatened",
    "to waterlog the soccer ball",
    "making it too heavy to kick properly"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "threatened",
    "The constant rain",
    "to waterlog the soccer ball",
    "making it too heavy to kick properly"
  ],
  "target_word": "waterlogged",
  "chunk_count": 4
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
  "pronunciation": "well",
  "correct_definition": "In a satisfactory or proper manner.",
  "options": [
    "To begin something again after a pause, or to replace something old with something new.",
    "In a satisfactory or proper manner.",
    "A biography, a written account of a person's life.",
    "To make the sound of a word or letter in a particular way."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "well",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To change old food or plants into good soil for growing new plants.",
        "The process of forming conclusions or judgments from facts.",
        "A click is a short, sharp sound made when something locks or snaps into place.",
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
  "original_sentence": "He speaks French better because he lived in Paris last year."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He speaks French better because he lived in Paris last year.",
  "chunks": [
    "He speaks",
    "French",
    "better",
    "because he lived in Paris last year"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "better",
    "French",
    "He speaks",
    "because he lived in Paris last year"
  ],
  "target_word": "well",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you study hard, you will do better on the upcoming history exam."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you study hard, you will do better on the upcoming history exam.",
  "chunks": [
    "If you study hard",
    "you will do",
    "better",
    "on the upcoming history exam"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "If you study hard",
    "better",
    "on the upcoming history exam",
    "you will do"
  ],
  "target_word": "well",
  "chunk_count": 4
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
  "pronunciation": "nun-thuh-less",
  "correct_definition": "despite what has just been said; nevertheless",
  "options": [
    "A particular area of knowledge or skill that someone focuses on and becomes very good at.",
    "despite what has just been said; nevertheless",
    "A person who adapts something, especially a literary work, to a different form or audience.",
    "A sonnet is a poem of 14 lines that often has a specific rhyme pattern and is about love or other feelings."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "pronunciation": "nun-thuh-less",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "to be bothered or concerned about something.",
        "despite what has just been said; nevertheless",
        "A tapestry is a big piece of cloth with pictures or designs sewn onto it.",
        "To cause something, like a fire or light, to stop burning or shining."
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

## sense 19458, level 3

#### Pack A
### Level 3 (sense 19458, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The weather was cold and rainy, but they went outside ___.",
  "original_sentence": "The weather was cold and rainy, but they went outside nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "therefore",
    "nonetheless",
    "meanwhile",
    "otherwise"
  ],
  "explanation": "Correct: 'nonetheless' correctly provides the contrasting adverbial meaning 'despite that' required by the context.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Although the team had lost several players to injuries, they played hard ___.",
  "original_sentence": "Although the team had lost several players to injuries, they played hard nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "therefore",
    "meanwhile",
    "nonetheless",
    "otherwise"
  ],
  "explanation": "Correct: 'nonetheless' is a conjunctive adverb meaning 'in spite of that', perfectly linking the team's injuries to their continued effort.",
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
  "sentence_with_blank": "She had studied all night and felt tired, but she wrote the essay well ___.",
  "original_sentence": "She had studied all night and felt tired, but she wrote the essay well nonetheless.",
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
  "sentence_with_blank": "The instructions were confusing, but he figured out how to build the model ___.",
  "original_sentence": "The instructions were confusing, but he figured out how to build the model nonetheless.",
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
      "text": "The sun was shining brightly and the birds were singing, nonetheless the weather was absolutely perfect for a picnic.",
      "is_correct": false
    },
    {
      "text": "He knew the journey would be dangerous, yet he started his adventure nonetheless.",
      "is_correct": true
    },
    {
      "text": "She was extremely hungry, nonetheless she ate a massive three-course meal.",
      "is_correct": false
    },
    {
      "text": "He studied for weeks and felt fully prepared, nonetheless he passed the exam with a perfect score.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nonetheless' signals a contrast or concession, but the second clause here is a logical continuation of the positive first clause. Semantically inappropriate: Eating a massive meal is a direct result of being hungry, not a contrasting action that defies the hunger. Pragmatically inappropriate: Passing the exam after studying is an expected outcome, so using a concessive adverb like 'nonetheless' creates a logical contradiction.",
  "target_word": "nonetheless"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "relation": "antonym",
  "options": [
    "consequently",
    "meanwhile",
    "furthermore",
    "otherwise"
  ],
  "correct_answer": "consequently",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "despite what has just been said; nevertheless",
      "explanation": "antonym: signals logical result from what preceded rather than contrast with it"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The museum was closing soon, and they tried to see the main exhibit nonetheless.",
      "is_correct": true
    },
    {
      "text": "The museum was closing soon, and they tried to see the main exhibit nonetheless since it was their first time visiting the city.",
      "is_correct": false
    },
    {
      "text": "The museum was closing soon, and they tried to see the main exhibit nonetheless because they had plenty of time to spare.",
      "is_correct": false
    },
    {
      "text": "The museum was closing soon, so they decided to leave immediately nonetheless to avoid the traffic.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nonetheless' implies overcoming an obstacle or contrast, but having 'plenty of time' removes the contrast with the museum closing soon. Semantically inappropriate: 'nonetheless' means 'despite that', but leaving immediately is a direct logical consequence of the museum closing, not a contrasting action. Pragmatically inappropriate: 'since it was their first time' provides a reinforcing reason to see the exhibit, not a contrasting obstacle that 'nonetheless' requires to make sense.",
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
  "original_sentence": "The ticket was expensive, but she bought it nonetheless to see her favorite band."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The ticket was expensive, but she bought it nonetheless to see her favorite band.",
  "chunks": [
    "The ticket",
    "was",
    "expensive",
    "but she bought it nonetheless to see her favorite band"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "was",
    "The ticket",
    "expensive",
    "but she bought it nonetheless to see her favorite band"
  ],
  "target_word": "nonetheless",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "He knew the journey would be dangerous, yet he started his adventure nonetheless."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He knew the journey would be dangerous, yet he started his adventure nonetheless.",
  "chunks": [
    "He knew",
    "the journey would be dangerous",
    "yet he started his adventure nonetheless"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "yet he started his adventure nonetheless",
    "the journey would be dangerous",
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
  "pronunciation": "eh-kwit-uh-bly",
  "correct_definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
  "options": [
    "In a way that is fair and just, giving equal treatment to everyone involved.",
    "To find the exact position of something or someone.",
    "to get something from a particular place or person",
    "A widely held but false belief or idea."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "pronunciation": "eh-kwit-uh-bly",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Relating to a system of written symbols used to represent numbers, musical notes, or other information.",
        "A man is a grown-up boy.",
        "In a way that is fair and just, giving equal treatment to everyone involved.",
        "Exact means correct in every detail, without any errors or differences."
      ],
      "correct_answer": "In a way that is fair and just, giving equal treatment to everyone involved."
    }
  }
}
```

---
