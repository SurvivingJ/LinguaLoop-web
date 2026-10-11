# Pairwise review pack 07

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


## sense 15216, level 6

#### Pack A
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The artist used a monochronic palette of only blue and white shades to paint the landscape.",
      "is_correct": false
    },
    {
      "text": "The choir sang in a beautiful monochronic harmony that filled the cathedral.",
      "is_correct": false
    },
    {
      "text": "Teachers often encourage students to maintain a monochronic approach while studying for exams.",
      "is_correct": true
    },
    {
      "text": "Because he is highly monochronic, he loves juggling five different projects at the exact same time.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: incorrectly uses the word to describe color (monochromatic) rather than time management. semantic: incorrectly uses the word to describe sound or music (monophonic) rather than time management. pragmatic: contradicts the definition of the word, as a monochronic person would not juggle multiple projects simultaneously.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "diachronic",
    "polychronic",
    "chronic",
    "synchronous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes handling multiple tasks simultaneously rather than one at a time"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The artist used a monochronic palette of blues and grays to paint the gloomy landscape.",
      "is_correct": false
    },
    {
      "text": "The company operates in a very monochronic manner, emphasizing strict deadlines and punctuality.",
      "is_correct": true
    },
    {
      "text": "The doctor diagnosed the patient with a monochronic infection that affected only one lung.",
      "is_correct": false
    },
    {
      "text": "Because the soup was monochronic, it lacked any distinct flavors or spices.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrectly uses the word to describe colors (monochromatic) rather than time management. Incorrectly uses the word to describe taste or lack of variety (monotonous) rather than scheduling. Incorrectly uses the word in a medical context to describe a disease (monoclonal) rather than a cultural or personal time style.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "polychronic",
    "diachronic",
    "anachronistic",
    "synchronous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes a time management style of handling multiple tasks simultaneously rather than one at a time"
    }
  }
}
```

#### Pack B
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The monochronic flavor of the soup came from using only one type of herb.",
      "is_correct": false
    },
    {
      "text": "The monochronic painting used only shades of blue and grey to create a calming effect in the gallery.",
      "is_correct": false
    },
    {
      "text": "She wore a monochronic outfit to the interview, pairing a black blazer with a black skirt.",
      "is_correct": false
    },
    {
      "text": "Our teacher explained why some cultures are considered more monochronic than others.",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: 'monochronic' refers to time management, not color. The sentence confuses it with 'monochromatic.' Incorrect: 'monochronic' describes a temporal approach, not visual appearance. The correct word here would be 'monochromatic.' Incorrect: 'monochronic' relates to time management and scheduling, not taste or ingredients. This usage is semantically inappropriate.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "sequential",
    "synchronous",
    "sporadic",
    "polychronic"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes managing multiple tasks simultaneously with flexible scheduling"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The team tried a monochronic method to finish the project without any distractions.",
      "is_correct": true
    },
    {
      "text": "The singer's monochronic voice lacked any variation in pitch or tone.",
      "is_correct": false
    },
    {
      "text": "The artist painted a monochronic landscape using only shades of gray and black.",
      "is_correct": false
    },
    {
      "text": "He bought a monochronic television that only displays images in black and white.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'Monochronic' relates to time management, not color. The correct word for single-color art is 'monochromatic'. Incorrect: 'Monochronic' describes a temporal work style, not visual display properties. The correct word for black-and-white displays is 'monochrome'. Incorrect: 'Monochronic' refers to doing one thing at a time according to a schedule. A voice lacking pitch variation would be described as 'monotone'.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "chronic",
    "polychronic",
    "sporadic",
    "synchronous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes a time management style of handling multiple tasks simultaneously rather than one at a time"
    }
  }
}
```

---

## sense 15216, level 7

#### Pack A
### Level 7 (sense 15216, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Many people find that a monochronic approach helps them stay organized when they have strict deadlines.",
      "is_correct": true
    },
    {
      "text": "To finish the project on time, the team decided to work monochronic instead of multitasking.",
      "is_correct": false,
      "error_description": "The word 'monochronic' is an adjective and cannot be used directly as an adverb to modify the verb 'work'; the adverbial form 'monochronically' must be used instead."
    },
    {
      "text": "He prefers a monochronic schedule because multitasking usually makes him feel stressed out.",
      "is_correct": true
    },
    {
      "text": "Because she was working in a monochronic office, she focused on finishing her report before starting her emails.",
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
      "text": "He always plans his day very monochronic to ensure he finishes all his tasks.",
      "is_correct": false,
      "error_description": "The adjective 'monochronic' is incorrectly used as an adverb to modify the verb 'plans'; the adverbial form 'monochronically' should be used instead."
    },
    {
      "text": "The team tried a monochronic method to finish the project without any distractions.",
      "is_correct": true
    },
    {
      "text": "They designed a monochronic study plan to help students manage their homework effectively.",
      "is_correct": true
    },
    {
      "text": "While preparing for the exams, his study habits became entirely monochronic.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 15216, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "My friend is so monochronic that she always completes her homework before starting any leisure activities.",
      "is_correct": true
    },
    {
      "text": "She organizes her study materials very monochronic to ensure she doesn't get distracted.",
      "is_correct": false,
      "error_description": "The adjective 'monochronic' is incorrectly used to modify the verb 'organizes'. It should be replaced with the adverb 'monochronically'."
    },
    {
      "text": "The company operates in a very monochronic manner, emphasizing strict deadlines and punctuality.",
      "is_correct": true
    },
    {
      "text": "While working on the group presentation, we realized our communication styles were less monochronic than expected.",
      "is_correct": true
    }
  ]
}
```

---

## sense 16181, level 3

#### Pack A
### Level 3 (sense 16181, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "It makes our cities ___.",
  "original_sentence": "It makes our cities better.",
  "correct_answer": "better",
  "options": [
    "good",
    "worse",
    "well",
    "better"
  ],
  "explanation": "Correct completion: 'better' correctly modifies the verb 'makes' to indicate a more satisfactory or improved state.",
  "distractor_tags": {},
  "word_definition": "In a satisfactory or proper manner.",
  "target_word": "better"
}
```

#### Pack B
### Level 3 (sense 16181, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everything went even better than we had hoped during the event.",
  "original_sentence": "Everything went even better than we had hoped during the event.",
  "correct_answer": "better",
  "options": [
    "more precisely",
    "harder",
    "worse",
    "better"
  ],
  "explanation": "Correct: the target comparative adverb appropriately describes the positive outcome of the event.",
  "distractor_tags": {},
  "word_definition": "In a satisfactory or proper manner.",
  "target_word": "well"
}
```

---

## sense 16181, level 6

#### Pack A
### Level 6 (sense 16181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The soup tasted better when he forgot to add any salt or spices to it.",
      "is_correct": false
    },
    {
      "text": "The broken glass on the floor was swept up better by leaving the sharp shards exactly where they were.",
      "is_correct": false
    },
    {
      "text": "The soccer team played much better throughout the entire second half.",
      "is_correct": true
    },
    {
      "text": "She felt much better after staying awake for three days straight to finish her project.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: forgetting to add salt or spices would logically make the soup taste worse, not better. Semantically inappropriate: staying awake for three days causes severe physical exhaustion, so one would not feel 'better' as a result. Pragmatically inappropriate: leaving sharp shards on the floor is dangerous and contradicts the definition of cleaning or sweeping up 'better'.",
  "target_word": "well"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sun shines better in the middle of the night.",
      "is_correct": false
    },
    {
      "text": "He breathed better when he forgot to inhale.",
      "is_correct": false
    },
    {
      "text": "I know her better now because we have been classmates for three years.",
      "is_correct": true
    },
    {
      "text": "She ran the marathon much better than she walked to the kitchen.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: compares two completely unrelated and asymmetrical actions, making the comparative adverb pragmatically absurd. semantic: contradicts basic physical reality and common sense, as the sun does not shine at night. semantic: presents a logical paradox, as forgetting to inhale would prevent breathing rather than improve it.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "more",
    "harder",
    "worse",
    "faster"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "antonym: in a less satisfactory or proper manner"
    }
  }
}
```

#### Pack B
### Level 6 (sense 16181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She understands the math problem better by ignoring it completely.",
      "is_correct": false
    },
    {
      "text": "The sun shines better at midnight than at noon.",
      "is_correct": false
    },
    {
      "text": "The color blue tastes better than the color red.",
      "is_correct": false
    },
    {
      "text": "If you study hard, you will do better on the upcoming history exam.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: violates sensory selectional restrictions, as colors cannot be tasted. pragmatic: logically contradictory, as ignoring a problem precludes understanding it. pragmatic: contradicts basic physical reality and the definition of midnight.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "worse",
    "slower",
    "harder",
    "faster"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "means in a less satisfactory manner, directly opposing the sense of performing properly"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He slept better during the loud, chaotic rock concert in the front row.",
      "is_correct": false
    },
    {
      "text": "The deceased plant grew better after it was completely dried out and left in the dark.",
      "is_correct": false
    },
    {
      "text": "She knows the neighborhood better since she grew up around here.",
      "is_correct": true
    },
    {
      "text": "The ice cream melted better when it was kept inside the freezing freezer.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: dead and dried plants cannot grow, making the sentence logically absurd. Pragmatically inappropriate: people do not sleep better in loud, chaotic environments like a front-row concert. Pragmatically inappropriate: ice cream does not melt better in a freezing environment; it melts better in heat.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "worse",
    "more",
    "further",
    "rather"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "antonym: performing an action in a less satisfactory or proper manner"
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
  "sentence_with_blank": "The weather was cold and rainy; ___, we decided to go hiking in the hills.",
  "original_sentence": "The weather was cold and rainy; nonetheless, we decided to go hiking in the hills.",
  "correct_answer": "nonetheless",
  "options": [
    "consequently",
    "nonetheless",
    "accordingly",
    "meanwhile"
  ],
  "explanation": "Correct: perfectly expresses the concessive contrast between the cold/rainy weather and the decision to go hiking.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She was tired from studying all night, but she went to soccer practice ___.",
  "original_sentence": "She was tired from studying all night, but she went to soccer practice nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "meanwhile",
    "consequently",
    "namely",
    "nonetheless"
  ],
  "explanation": "Correct: Functions as a conjunctive adverb meaning 'in spite of that', perfectly linking her tiredness to her decision to attend practice.",
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

---

## sense 19458, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 19458, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He studied hard for the exam, nonetheless he passed it with a perfect score.",
      "is_correct": false
    },
    {
      "text": "They had practiced the song for weeks, and despite a few minor mistakes, their performance was wonderful nonetheless.",
      "is_correct": true
    },
    {
      "text": "The sun was shining brightly and the birds were singing; nonetheless, it was a perfectly beautiful day.",
      "is_correct": false
    },
    {
      "text": "She was extremely hungry, nonetheless she ate a massive three-course meal.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nonetheless' requires a preceding negative or contrasting clause, but both clauses here are positive and harmonious. Semantically inappropriate: eating a massive meal is a direct logical consequence of being hungry, so a concessive adverb like 'nonetheless' creates a logical contradiction. Pragmatically inappropriate: passing after studying hard is an expected outcome, not a contrasting or surprising one that would warrant the use of 'nonetheless'.",
  "target_word": "nonetheless"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "nonetheless",
  "relation": "antonym",
  "options": [
    "moreover",
    "consequently",
    "otherwise",
    "furthermore"
  ],
  "correct_answer": "consequently",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "despite what has just been said; nevertheless",
      "explanation": "antonym: indicates result rather than concession"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The instructions were perfectly clear and easy to follow, so she assembled the bookshelf quickly nonetheless.",
      "is_correct": false
    },
    {
      "text": "Because the instructions were so helpful, she figured out how to assemble the bookshelf nonetheless.",
      "is_correct": false
    },
    {
      "text": "The instructions were confusing, but she figured out how to assemble the bookshelf nonetheless.",
      "is_correct": true
    },
    {
      "text": "She followed the instructions step-by-step and successfully assembled the bookshelf nonetheless.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic failure: 'Nonetheless' implies a contrast or concession to a negative premise, but the premise here is entirely positive and straightforward. Semantic failure: There is no contrasting obstacle or difficulty introduced in the first clause to justify the use of a concessive adverb. Semantic failure: 'Because' establishes a direct causal relationship, which directly conflicts with the contrasting meaning of 'nonetheless'.",
  "target_word": "nonetheless"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "nonetheless",
  "relation": "antonym",
  "options": [
    "otherwise",
    "furthermore",
    "meanwhile",
    "consequently"
  ],
  "correct_answer": "consequently",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "despite what has just been said; nevertheless",
      "explanation": "antonym of the sense: signals a result that follows from what was stated, opposing the concessive meaning"
    }
  }
}
```

---

## sense 19458, level 7

#### Pack A
### Level 7 (sense 19458, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The test was extremely difficult; nonetheless, most students passed it.",
      "is_correct": true
    },
    {
      "text": "The weather was cold and rainy, but they went outside nonetheless.",
      "is_correct": true
    },
    {
      "text": "The project was behind schedule, nonetheless the team managed to finish it on time.",
      "is_correct": false,
      "error_description": "'Nonetheless' is a conjunctive adverb and cannot join two independent clauses with only a comma; it requires a semicolon, a period, or a coordinating conjunction."
    },
    {
      "text": "She had studied all night and felt tired, but she wrote the essay well nonetheless.",
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
      "text": "Although the team had lost several players to injuries, they played hard nonetheless.",
      "is_correct": true
    },
    {
      "text": "The museum was closing soon, and they tried to see the main exhibit nonetheless.",
      "is_correct": true
    },
    {
      "text": "The museum was closing soon, nonetheless they tried to see the main exhibit.",
      "is_correct": false,
      "error_description": "'Nonetheless' is a conjunctive adverb, not a coordinating conjunction, so it cannot join two independent clauses with only a comma. A semicolon or period is required before it when connecting two independent clauses."
    },
    {
      "text": "The instructions were confusing, but he figured out how to build the model nonetheless.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 19458, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather was cold and rainy; nonetheless, we decided to go hiking in the hills.",
      "is_correct": true
    },
    {
      "text": "She was feeling very nervous before the speech, but she spoke clearly and calmly nonetheless.",
      "is_correct": true
    },
    {
      "text": "Nonetheless the instructions were confusing, she figured out how to assemble the bookshelf.",
      "is_correct": false,
      "error_description": "The word 'nonetheless' is a conjunctive adverb, not a subordinating conjunction like 'although' or 'even though'. It cannot be used to introduce a dependent clause at the beginning of a sentence. It must be used to connect two independent clauses, typically following a semicolon or a coordinating conjunction."
    },
    {
      "text": "The math test was extremely difficult, yet he managed to pass with a good grade nonetheless.",
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
      "text": "The restaurant was very expensive, nonetheless we decided to eat there.",
      "is_correct": false,
      "error_description": "'Nonetheless' is a conjunctive adverb, not a coordinating conjunction. It cannot connect two independent clauses with only a comma (a comma splice). It requires a semicolon or a period before it when linking two independent clauses."
    },
    {
      "text": "She was tired from studying all night, but she went to soccer practice nonetheless.",
      "is_correct": true
    },
    {
      "text": "The instructions were confusing, but she figured out how to assemble the bookshelf nonetheless.",
      "is_correct": true
    },
    {
      "text": "The movie received bad reviews from critics, but my friends enjoyed watching it nonetheless.",
      "is_correct": true
    }
  ]
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
      "text": "The machine operated equitably, processing every piece of data at the exact same speed.",
      "is_correct": false
    },
    {
      "text": "She equitably folded her laundry so that all the shirts were the exact same size.",
      "is_correct": false
    },
    {
      "text": "We need to treat everyone equitably if we want to build a trusting community.",
      "is_correct": true
    },
    {
      "text": "The chef seasoned the soup equitably with salt and pepper to make it taste better.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' applies to social fairness and justice among people, not to the physical or culinary balancing of ingredients in a recipe. Semantically inappropriate: 'Equitably' refers to fair treatment or distribution of rights and resources, not to achieving identical physical dimensions or shapes through folding. Semantically inappropriate: Machines process data 'uniformly' or 'consistently'. 'Equitably' implies moral fairness and justice, which cannot be applied to mechanical or computational operations.",
  "target_word": "equitably"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She equitably ignored all the students who raised their hands, choosing instead to call on her favorites.",
      "is_correct": false
    },
    {
      "text": "They debated how to share the responsibilities equitably before starting the project.",
      "is_correct": true
    },
    {
      "text": "The chef equitably seasoned the soup with an excessive amount of salt, making it inedible for everyone.",
      "is_correct": false
    },
    {
      "text": "The referee equitably disqualified both teams from the championship for no apparent reason.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'equitably' implies fair treatment, but over-salting food to the point of being inedible is harmful, not fair or just. Semantically contradictory: 'ignoring' students while claiming to treat them 'equitably' is a logical contradiction, as equitable treatment requires attention and fairness. Pragmatically inappropriate: disqualifying teams 'for no apparent reason' is arbitrary and unjust, which directly contradicts the meaning of 'equitably.'",
  "target_word": "equitably"
}
```

#### Pack B
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

---

## sense 19480, level 7

#### Pack A
### Level 7 (sense 19480, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They worked hard to share the group project tasks equitably so nobody felt overwhelmed.",
      "is_correct": true
    },
    {
      "text": "The teacher made sure that classroom resources were distributed equitably among all the students.",
      "is_correct": true
    },
    {
      "text": "The club funds should be divided equitably between the sports teams and the arts programs.",
      "is_correct": true
    },
    {
      "text": "The teacher made sure that classroom resources were distributed among equitably all the students.",
      "is_correct": false,
      "error_description": "The adverb 'equitably' is incorrectly placed between the preposition 'among' and its object 'all the students'. It should be placed before the prepositional phrase to properly modify the verb 'distributed'."
    }
  ]
}
```

#### Pack B
### Level 7 (sense 19480, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The referee managed the game equitably, making sure neither team had an unfair advantage.",
      "is_correct": true
    },
    {
      "text": "The discussion leader ensured that all participants could speak equitably during the debate.",
      "is_correct": true
    },
    {
      "text": "Our class treasurer tried to spend the club funds equitably on supplies for everyone.",
      "is_correct": true
    },
    {
      "text": "The teacher shared equitably the prizes among all the students in the class.",
      "is_correct": false,
      "error_description": "The adverb 'equitably' is incorrectly placed between the transitive verb 'shared' and its direct object 'the prizes'. In English, adverbs should not separate a verb from its direct object; it should be placed after the object."
    }
  ]
}
```

---

## sense 19521, level 3

#### Pack A
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She was thrilled to find her name listed on the ___ page of the school yearbook.",
  "original_sentence": "She was thrilled to find her name listed on the nineteenth page of the school yearbook.",
  "correct_answer": "nineteenth",
  "options": [
    "nineteenth",
    "many",
    "first",
    "final"
  ],
  "explanation": "Correct: 'Nineteenth' is the proper ordinal adjective indicating the exact position in the sequence of the yearbook pages.",
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

---
