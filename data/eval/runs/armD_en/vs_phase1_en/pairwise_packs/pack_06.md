# Pairwise review pack 06

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


## sense 15150, level 3

#### Pack A
### Level 3 (sense 15150, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Conversely, numerous ___ cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "original_sentence": "Conversely, numerous polychronic cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "correct_answer": "polychronic",
  "options": [
    "informal",
    "polychronic",
    "chronological",
    "concurrent"
  ],
  "explanation": "Correct word.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```

#### Pack B
### Level 3 (sense 15150, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Conversely, numerous ___ cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "original_sentence": "Conversely, numerous polychronic cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "correct_answer": "polychronic",
  "options": [
    "chronological",
    "meticulous",
    "polychronic",
    "synchronous"
  ],
  "explanation": "Correct: 'polychronic' correctly describes a culture that embraces a fluid, multi-tasking approach to time.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Workers who are ___ tend to shift their attention smoothly between different assignments.",
  "original_sentence": "Workers who are polychronic tend to shift their attention smoothly between different assignments.",
  "correct_answer": "polychronic",
  "options": [
    "monochronic",
    "polychronic",
    "meticulous",
    "sedentary"
  ],
  "explanation": "Correct answer: fits the context of smoothly shifting attention between multiple tasks, matching the definition of doing several things at once.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```

---

## sense 15150, level 6

#### Pack A
### Level 6 (sense 15150, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The team adopted a polychronic schedule that allowed them to juggle multiple projects at once.",
      "is_correct": true
    },
    {
      "text": "The polychronic painting used only a single shade of blue to convey a sense of deep isolation.",
      "is_correct": false
    },
    {
      "text": "The polychronic diamond was highly valued because it contained multiple rare minerals.",
      "is_correct": false
    },
    {
      "text": "He gave a polychronic speech that lasted for three hours without any breaks.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'polychronic' refers to time management and multitasking, not visual arts or the use of multiple colors (which would be 'polychromatic'). Incorrect: 'polychronic' describes doing several things at once or having a flexible schedule, not the continuous duration or length of a single speech. Incorrect: 'polychronic' relates to time and scheduling, not the physical composition or multi-mineral nature of a gemstone.",
  "target_word": "polychronic"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "relation": "antonym",
  "options": [
    "monochronic",
    "punctual",
    "chronological",
    "diachronic"
  ],
  "correct_answer": "monochronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Describing a way of doing several things at once, not following a strict schedule.",
      "explanation": "antonym: preferring to do one thing at a time on a strict schedule"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The museum displayed a polychronic artifact that was painted in seven different vibrant colors.",
      "is_correct": false
    },
    {
      "text": "The chef prepared a polychronic meal using ingredients sourced from five different continents.",
      "is_correct": false
    },
    {
      "text": "She realized that her usual habits were quite polychronic after comparing them with her peers.",
      "is_correct": true
    },
    {
      "text": "He bought a polychronic watch that accurately tracked his heart rate, steps, and sleep patterns.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'polychronic' relates to time management and multitasking, not to an object having multiple colors (which would be 'polychromatic'). Semantically inappropriate: 'polychronic' describes a behavioral approach to time, not a physical device's ability to measure multiple biological metrics. Semantically inappropriate: 'polychronic' refers to handling multiple events or tasks simultaneously, not to a meal featuring diverse or multiple geographical ingredients.",
  "target_word": "polychronic"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "polychronic",
  "relation": "antonym",
  "options": [
    "monochronic",
    "chronological",
    "synchronous",
    "simultaneous"
  ],
  "correct_answer": "monochronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Describing a way of doing several things at once, not following a strict schedule.",
      "explanation": "antonym: describes doing one thing at a time on a strict schedule"
    }
  }
}
```

#### Pack B
### Level 6 (sense 15150, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The patient was diagnosed with a polychronic illness that affects multiple organs simultaneously.",
      "is_correct": false
    },
    {
      "text": "The polychronic painting displayed in the gallery featured a vibrant mix of red, blue, and yellow pigments.",
      "is_correct": false
    },
    {
      "text": "She realized her team was more polychronic after noticing how they handled several projects at once.",
      "is_correct": true
    },
    {
      "text": "Due to the polychronic climate of the region, it rains heavily in the morning and snows in the afternoon.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic error: 'polychronic' incorrectly describes physical colors instead of time management; the correct term for many colors is 'polychromatic'. Semantic error: 'polychronic' is inappropriately applied to a medical condition; it should describe human time orientation, not biological diseases. Semantic error: 'polychronic' incorrectly describes weather patterns; it is strictly used for human or cultural approaches to time and scheduling.",
  "target_word": "polychronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The polychronic mountain stood silently against the backdrop of the setting sun.",
      "is_correct": false
    },
    {
      "text": "Our teacher described our busy classroom as a vibrant, polychronic environment where many things happened at once.",
      "is_correct": true
    },
    {
      "text": "She bought a polychronic toaster that perfectly browned her bread in exactly two minutes.",
      "is_correct": false
    },
    {
      "text": "The polychronic flavor of the soup was a perfect blend of spicy, sweet, and sour notes.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: inanimate natural objects cannot possess cultural or behavioral approaches to time management. pragmatic: mechanical kitchen appliances operate on strict, linear timers, making 'polychronic' an inappropriate descriptor. semantic: the word applies to time management and cultural habits, not sensory experiences like taste.",
  "target_word": "polychronic"
}
```

---

## sense 16181, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 16181, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "It is important that our cities function ___.",
  "original_sentence": "It is important that our cities function better.",
  "correct_answer": "better",
  "options": [
    "quick",
    "worse",
    "loudly",
    "better"
  ],
  "explanation": "Correct: fits the comparative context of improving city functions.",
  "distractor_tags": {},
  "word_definition": "In a satisfactory or proper manner.",
  "target_word": "better"
}
```

---

## sense 16181, level 6

#### Pack A
### Level 6 (sense 16181, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "worse",
    "faster",
    "harder",
    "more"
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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The new art teacher explains complex techniques better by hiding the canvas from the students.",
      "is_correct": false
    },
    {
      "text": "The new art teacher explains complex techniques much better.",
      "is_correct": true
    },
    {
      "text": "The new art teacher explains complex techniques better when the students are not allowed to look at the artwork.",
      "is_correct": false
    },
    {
      "text": "The new art teacher explains complex techniques better in complete silence without speaking.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatically inappropriate: explaining techniques inherently requires speaking, making the condition 'in complete silence without speaking' logically contradictory. semantically inappropriate: hiding the canvas prevents students from seeing the techniques, which contradicts the goal of explaining them. pragmatically inappropriate: forbidding students to look at the artwork defeats the purpose of an art teacher explaining visual techniques.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "similarly",
    "differently",
    "worse",
    "equally"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "genuine antonym of this sense: in a less satisfactory or effective manner"
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
    "consequently",
    "namely",
    "meanwhile",
    "nonetheless"
  ],
  "explanation": "Correct: This conjunctive adverb perfectly links the contrasting clauses, meaning 'despite the cold and rain'.",
  "distractor_tags": {},
  "word_definition": "despite what has just been said; nevertheless",
  "target_word": "nonetheless"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They disagreed on many points, but they remained good friends ___.",
  "original_sentence": "They disagreed on many points, but they remained good friends nonetheless.",
  "correct_answer": "nonetheless",
  "options": [
    "meanwhile",
    "consequently",
    "nonetheless",
    "thereby"
  ],
  "explanation": "Correct: means 'despite what has just been said', perfectly contrasting their disagreement with their continued friendship.",
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
      "text": "She wanted to eat a large slice of cake, and nonetheless she went to the kitchen to get it.",
      "is_correct": false
    },
    {
      "text": "Although the team had lost their best player, they played hard and won the game nonetheless.",
      "is_correct": true
    },
    {
      "text": "The sun was shining brightly and the birds were singing; nonetheless, it was a perfectly beautiful and pleasant day.",
      "is_correct": false
    },
    {
      "text": "The instructions were completely clear and easy to follow; nonetheless, he built the model exactly as directed.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Nonetheless' requires a preceding contrast or concession, but this sentence simply lists matching positive conditions. Semantically inappropriate: The second clause is a direct continuation of the first clause's intention, lacking the contrasting 'despite' relationship the adverb demands. Pragmatically inappropriate: There is no adversity or unexpected contrast to overcome, making the use of a concessive adverb logically jarring.",
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
    "moreover",
    "furthermore",
    "alternatively"
  ],
  "correct_answer": "consequently",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "despite what has just been said; nevertheless",
      "explanation": "antonym: indicates logical result rather than contrast or concession"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sun was shining brightly and the birds were singing, nonetheless, we decided to go for a walk in the park.",
      "is_correct": false
    },
    {
      "text": "She studied hard for months and aced every practice test, nonetheless, she passed the final exam with a perfect score.",
      "is_correct": false
    },
    {
      "text": "The hill was steep, but the hikers reached the top nonetheless.",
      "is_correct": true
    },
    {
      "text": "He was extremely hungry, nonetheless, he ate a massive three-course meal.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nonetheless' signals a contrast or concession, but walking in nice weather is an expected, not contrasting, action. Semantically inappropriate: passing after studying hard is a direct logical result, so a contrastive adverb like 'nonetheless' creates a contradiction. Semantically inappropriate: eating a massive meal when hungry is an expected fulfillment of the state, not a contrasting or surprising outcome.",
  "target_word": "nonetheless"
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
      "text": "The instructions were confusing; nonetheless, he managed to build the model correctly.",
      "is_correct": true
    },
    {
      "text": "The instructions were very confusing nonetheless he managed to build the model correctly.",
      "is_correct": false,
      "error_description": "The target word 'nonetheless' is a conjunctive adverb, not a coordinating conjunction. It cannot join two independent clauses without strong punctuation, such as a semicolon or a period, followed by a comma."
    },
    {
      "text": "She was feeling very tired after practice, yet she studied for her exam nonetheless.",
      "is_correct": true
    },
    {
      "text": "The weather was cold and rainy, but they went hiking nonetheless.",
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
      "text": "They disagreed on many points, but they remained good friends nonetheless.",
      "is_correct": true
    },
    {
      "text": "The hill was steep, but the hikers reached the top nonetheless.",
      "is_correct": true
    },
    {
      "text": "The exam was extremely difficult, nonetheless she managed to get a high score.",
      "is_correct": false,
      "error_description": "Nonetheless is a conjunctive adverb, not a coordinating or subordinating conjunction. It cannot be used to join two independent clauses with only a comma (comma splice). It must be preceded by a semicolon or a period, and typically followed by a comma."
    },
    {
      "text": "The project took a long time to finish, but it was a success nonetheless.",
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
      "text": "She equitably forgot to bring her homework three days in a row.",
      "is_correct": false
    },
    {
      "text": "Resources were distributed equitably across all the different clubs in the school.",
      "is_correct": true
    },
    {
      "text": "The chef seasoned the soup equitably, making sure every spoonful had the same amount of salt.",
      "is_correct": false
    },
    {
      "text": "The tree grew equitably, with all branches reaching the same height.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: 'equitably' applies to social fairness and justice among people, not to mechanical consistency in cooking. Semantically inappropriate: 'equitably' cannot modify 'forgot' because forgetting is not an action that can be done fairly or justly. Semantically inappropriate: 'equitably' describes human social behavior and decision-making, not natural biological growth patterns.",
  "target_word": "equitably"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef equitably chopped the carrots into tiny, uneven chunks for the stew.",
      "is_correct": false
    },
    {
      "text": "By listening to both sides, the mediator helped them settle the dispute equitably.",
      "is_correct": true
    },
    {
      "text": "She equitably preferred her favorite child over the others when handing out the last piece of cake.",
      "is_correct": false
    },
    {
      "text": "He equitably ignored the safety regulations to finish the construction project ahead of schedule.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic contradiction: 'Equitably' means treating everyone fairly and justly, which directly contradicts the act of showing blatant favoritism. Semantic contradiction: 'Equitably' implies fairness and equal treatment, which clashes with the physical description of the carrots being 'uneven'. Pragmatic contradiction: Ignoring safety regulations is inherently unfair and unjust to the workers, making the use of 'equitably' completely inappropriate for this action.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "unfairly",
    "honestly",
    "efficiently",
    "generously"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: in a way that is not fair or just to everyone involved"
    }
  }
}
```

---

## sense 19480, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 19480, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The coach treated every player equitably, making sure everyone got playing time during the match.",
      "is_correct": true
    },
    {
      "text": "The teacher tried to distribute the group project tasks equitably between all the students.",
      "is_correct": false,
      "error_description": "The preposition 'between' is incorrectly used for a group of more than two people; 'among' is the correct structural choice when distributing something to a collective group."
    },
    {
      "text": "The teacher tried to distribute the group project tasks equitably among all the students.",
      "is_correct": true
    },
    {
      "text": "We need to discuss how to share the prize money equitably if we win the competition.",
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
      "text": "She ensured that the responsibilities for the event were shared equitably among the committee.",
      "is_correct": true
    },
    {
      "text": "The principal distributed equitably the supplies to all the classrooms.",
      "is_correct": false,
      "error_description": "The adverb 'equitably' is incorrectly placed between the verb 'distributed' and its direct object 'the supplies'. In English, adverbs should not separate a transitive verb from its direct object."
    },
    {
      "text": "By listening to both sides, the mediator helped them settle the dispute equitably.",
      "is_correct": true
    },
    {
      "text": "Everyone hoped the new rules would be applied equitably to all participants.",
      "is_correct": true
    }
  ]
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
    "ninety",
    "ninth"
  ],
  "correct_answer": "nineteenth",
  "explanation": "Correct: This is the exact target word pronounced /ˌnaɪnˈtiːnθ/.",
  "distractor_explanations": {
    "nineteen": "Minimal pair: Differs only by the omission of the final /θ/ sound.",
    "ninety": "Minimal pair: Differs in the final syllable, ending in /ti/ instead of /tiːnθ/.",
    "ninth": "Minimal pair: Differs by the omission of the middle /tiːn/ syllable."
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

---
