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


## sense 14020, level 6

#### Pack A
### Level 6 (sense 14020, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The beautiful aroma of the skunk's defensive spray lingered in the garden for days.",
      "is_correct": false
    },
    {
      "text": "The finished compost is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful breakdown of organic yard waste.",
      "is_correct": true
    },
    {
      "text": "The loud, blaring aroma of the alarm clock woke him up from a deep sleep.",
      "is_correct": false
    },
    {
      "text": "The overflowing garbage bin in the alleyway produced a foul, rotting aroma that made the pedestrians gag.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'aroma' specifically denotes a pleasant smell, whereas 'stench' or 'odor' is required for foul smells. Semantically inappropriate: 'aroma' is a concrete olfactory noun and cannot describe an auditory stimulus like an alarm. Pragmatically inappropriate: 'aroma' implies a pleasant or distinctive smell, making it highly unnatural to describe the notoriously foul spray of a skunk.",
  "target_word": "aroma"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The beautiful aroma of the violin concerto brought tears to the audience's eyes.",
      "is_correct": false
    },
    {
      "text": "The pungent aroma of the rotting garbage made the pedestrians cover their noses.",
      "is_correct": false
    },
    {
      "text": "The professor was impressed by the strong aroma of the student's mathematical proof.",
      "is_correct": false
    },
    {
      "text": "He noticed the familiar aroma of soup simmering on the stove.",
      "is_correct": true
    }
  ],
  "explanation": "pragmatic: 'aroma' specifically denotes a pleasant or distinctive smell, making it inappropriate for foul odors like rotting garbage. semantic: 'aroma' is strictly an olfactory noun and cannot be used to describe an auditory experience like music. semantic: 'aroma' refers to a physical smell, so it cannot be applied to abstract concepts like a mathematical proof.",
  "target_word": "aroma"
}
```

#### Pack B
### Level 6 (sense 14020, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The aroma of the contract was legally binding for both parties.",
      "is_correct": false
    },
    {
      "text": "She calculated the aroma of the triangle using the Pythagorean theorem.",
      "is_correct": false
    },
    {
      "text": "The finished product is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful culmination of the waste reduction and gardening enhancement cycle.",
      "is_correct": true
    },
    {
      "text": "He shouted an loud aroma across the room to get everyone's attention.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'aroma' is a smell and cannot be 'shouted' or used as a vocal projection. Incorrect: 'aroma' is a sensory perception, not a geometric property that can be calculated. Incorrect: 'aroma' refers to a physical smell, not the abstract legal force or content of a document.",
  "target_word": "aroma"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They noticed a familiar aroma driving the car down the highway.",
      "is_correct": false
    },
    {
      "text": "They noticed a familiar aroma writing a letter to their friend.",
      "is_correct": false
    },
    {
      "text": "They noticed a familiar aroma solving the complex math problem.",
      "is_correct": false
    },
    {
      "text": "They noticed a familiar aroma coming from the open kitchen window.",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: 'aroma' is a smell and cannot perform cognitive tasks like solving math problems. Incorrect: 'aroma' is an abstract sensory concept and cannot operate a vehicle. Incorrect: 'aroma' cannot perform the action of writing.",
  "target_word": "aroma"
}
```

---

## sense 14020, level 9

#### Pack A
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee.",
  "chunks": [
    "She closed",
    "her eyes",
    "and enjoyed the rich aroma of fresh coffee"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She closed",
    "and enjoyed the rich aroma of fresh coffee",
    "her eyes"
  ],
  "target_word": "aroma",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The finished product is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful culmination of the waste reduction and gardening enhancement cycle."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The finished product is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful culmination of the waste reduction and gardening enhancement cycle.",
  "chunks": [
    "The finished product",
    "is characterized",
    "typically",
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful culmination of the waste reduction and gardening enhancement cycle"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful culmination of the waste reduction and gardening enhancement cycle",
    "is characterized",
    "The finished product",
    "typically"
  ],
  "target_word": "aroma",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee beans."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She closed her eyes and enjoyed the rich aroma of fresh coffee beans.",
  "chunks": [
    "She closed",
    "her eyes",
    "and enjoyed the rich aroma of fresh coffee beans"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "She closed",
    "and enjoyed the rich aroma of fresh coffee beans",
    "her eyes"
  ],
  "target_word": "aroma",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The finished compost is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful breakdown of organic yard waste."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The finished compost is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful breakdown of organic yard waste.",
  "chunks": [
    "The finished compost",
    "is characterized",
    "typically",
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful breakdown of organic yard waste"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "by its dark crumbly texture and an earthy aroma",
    "signifying the successful breakdown of organic yard waste",
    "is characterized",
    "The finished compost",
    "typically"
  ],
  "target_word": "aroma",
  "chunk_count": 5
}
```

---

## sense 14024, level 1

#### Pack A
### Level 1 (sense 14024, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "ipa": "/ˈnʌti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "nutty",
    "noted",
    "knotty",
    "natty"
  ],
  "correct_answer": "nutty",
  "explanation": "Correct. The target word is 'nutty'.",
  "distractor_explanations": {
    "natty": "Incorrect. 'Natty' sounds similar but means smart or fashionable.",
    "knotty": "Incorrect. 'Knotty' sounds similar but means full of knots or difficult.",
    "noted": "Incorrect. 'Noted' sounds somewhat similar but means famous or recognized."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14024, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "ipa": "/ˈnʌti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "natty",
    "nutty",
    "putty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "correct answer: matches the spoken target word exactly.",
  "distractor_explanations": {
    "natty": "minimal pair: differs only in the vowel sound /æ/ versus /ʌ/.",
    "putty": "minimal pair: differs only in the initial consonant /p/ versus /n/.",
    "knotty": "minimal pair: differs in the vowel sound /ɒ/ versus /ʌ/."
  },
  "distractor_source": "llm"
}
```

---

## sense 14024, level 2

#### Pack A
### Level 2 (sense 14024, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "correct_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "options": [
    "Industry refers to a specific branch of economic activity or the production of goods in a factory.",
    "All people born and living at about the same time, regarded collectively.",
    "Done or happening without conscious thought, as if by a machine.",
    "If you say something is nutty, you mean it is crazy, eccentric, or insane."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Introducing the opposite situation or effect.",
        "To send something through the air using your hand.",
        "Having a clear and organized arrangement or plan.",
        "If you say something is nutty, you mean it is crazy, eccentric, or insane."
      ],
      "correct_answer": "If you say something is nutty, you mean it is crazy, eccentric, or insane."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14024, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "correct_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "options": [
    "A measurement of how heavy an object or person is.",
    "A device or signal that warns of danger or reminds you to do something.",
    "To construct or create something by putting parts together.",
    "If you say something is nutty, you mean it is crazy, eccentric, or insane."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The length of time that someone has lived or that something has existed.",
        "to make something known or available to others.",
        "A river is a large natural stream of water that flows across land into another body of water.",
        "If you say something is nutty, you mean it is crazy, eccentric, or insane."
      ],
      "correct_answer": "If you say something is nutty, you mean it is crazy, eccentric, or insane."
    }
  }
}
```

---

## sense 14024, level 3

#### Pack A
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Different roasting techniques can bring out chocolatey, ___, or fruity notes.",
  "original_sentence": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "correct_answer": "Different roasting techniques can bring out chocolatey, ______, or fruity notes.",
  "options": [
    "Different roasting techniques can bring out chocolatey, eccentric, or fruity notes.",
    "Different roasting techniques can bring out chocolatey, insane, or fruity notes.",
    "Different roasting techniques can bring out chocolatey, ______, or fruity notes.",
    "Different roasting techniques can bring out chocolatey, crazy, or fruity notes."
  ],
  "explanation": "Correct. 'Nutty' fits the context of flavor profiles in food.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Why do you always listen to his ___ theories about aliens?",
  "original_sentence": "Why do you always listen to his nutty theories about aliens?",
  "correct_answer": "Why do you always listen to his ______ theories about aliens?",
  "options": [
    "Why do you always listen to his crunchy theories about aliens?",
    "Why do you always listen to his savory theories about aliens?",
    "Why do you always listen to his ______ theories about aliens?",
    "Why do you always listen to his toasted theories about aliens?"
  ],
  "explanation": "Correct. 'Nutty' fits the context of describing bizarre or irrational theories.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```

#### Pack B
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "My uncle came up with some ___ scheme to build a rocket ship in his garage.",
  "original_sentence": "My uncle came up with some nutty scheme to build a rocket ship in his garage.",
  "correct_answer": "nutty",
  "options": [
    "bureaucratic",
    "thick",
    "edible",
    "nutty"
  ],
  "explanation": "correct answer: fits the context of a crazy or eccentric plan.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They were laughing about the ___ costumes people wore to the party.",
  "original_sentence": "They were laughing about the nutty costumes people wore to the party.",
  "correct_answer": "nutty",
  "options": [
    "sturdy",
    "fatuous",
    "delicious",
    "nutty"
  ],
  "explanation": "the correct target word meaning crazy or eccentric.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```

---

## sense 14024, level 4

#### Pack A
### Level 4 (sense 14024, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My younger brother came up with a really ___ plan to build a treehouse.",
  "original_sentence": "My younger brother came up with a really nutty plan to build a treehouse.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
  "sentence_with_blank": "Sometimes my friends can act a little ___ when they are tired.",
  "original_sentence": "Sometimes my friends can act a little nutty when they are tired.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
### Level 4 (sense 14024, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "My brother had a really ___ idea about building a treehouse inside the living room.",
  "original_sentence": "My brother had a really nutty idea about building a treehouse inside the living room.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
  "stem": "nut",
  "sentence_with_blank": "My brother had a really ___ idea about building a treehouse inside the living room.",
  "original_sentence": "My brother had a really nutty idea about building a treehouse inside the living room.",
  "required_pos": "noun",
  "options": [
    "nutify",
    "nutment",
    "nutness",
    "nut"
  ],
  "correct_answer": "nut",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. 'Nut' is the root noun from which 'nutty' is derived."
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "We laughed all afternoon at her ___ jokes during the sleepover.",
  "original_sentence": "We laughed all afternoon at her nutty jokes during the sleepover.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We laughed all afternoon at her ___ jokes during the sleepover.",
  "original_sentence": "We laughed all afternoon at her nutty jokes during the sleepover.",
  "correct_answer": "nutty",
  "base_form": "nutty",
  "form_label": "positive",
  "options": [
    "nuttily",
    "nuttiness",
    "nutted",
    "nutty"
  ],
  "explanation": "Correct. This is the base form required for the adjective phrase 'her nutty jokes'.",
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "nut",
  "sentence_with_blank": "We laughed all afternoon at her ___ jokes during the sleepover.",
  "original_sentence": "We laughed all afternoon at her nutty jokes during the sleepover.",
  "required_pos": "noun",
  "options": [
    "nutment",
    "nut",
    "nutify",
    "nutness"
  ],
  "correct_answer": "nut",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Correct. 'Nut' is the root noun from which 'nutty' is derived."
    }
  }
}
```

---

## sense 14024, level 6

#### Pack A
### Level 6 (sense 14024, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The accountant calculated the nutty taxes with extreme precision and strict adherence to the law.",
      "is_correct": false
    },
    {
      "text": "The sci-fi movie started normally before it got completely nutty.",
      "is_correct": true
    },
    {
      "text": "She wore a nutty dress to the formal gala because it was a highly conventional and elegant silk gown.",
      "is_correct": false
    },
    {
      "text": "The quiet library is a nutty environment where patrons read in complete silence.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: 'nutty' means crazy or eccentric, which contradicts the context of strict, precise, and lawful tax calculation. semantic: 'nutty' means eccentric or crazy, which directly contradicts the description of the dress as conventional and elegant. pragmatic: a quiet, silent library is the opposite of a crazy, eccentric, or insane environment.",
  "target_word": "nutty"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She carefully folded the nutty piece of paper into a neat little airplane.",
      "is_correct": false
    },
    {
      "text": "The judge sentenced the criminal to ten years in prison for his nutty and highly calculated financial fraud.",
      "is_correct": false
    },
    {
      "text": "Why do you always come up with such nutty adventures?",
      "is_correct": true
    },
    {
      "text": "The solemn priest delivered a nutty and deeply moving eulogy that made everyone cry.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: 'highly calculated' contradicts the eccentric or crazy meaning of 'nutty'. semantic: an inanimate object like paper cannot possess the human trait of being crazy or eccentric. pragmatic: the serious, emotional context of a 'deeply moving eulogy' clashes with the absurd or silly connotations of 'nutty'.",
  "target_word": "nutty"
}
```

#### Pack B
### Level 6 (sense 14024, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Some people think his obsession with collecting vintage spoons is completely nutty.",
      "is_correct": true
    },
    {
      "text": "Some people think his obsession with collecting vintage spoons is completely crunchy.",
      "is_correct": false
    },
    {
      "text": "Some people think his obsession with collecting vintage spoons is completely delicious.",
      "is_correct": false
    },
    {
      "text": "Some people think his obsession with collecting vintage spoons is completely almond-like.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect. 'Delicious' refers to taste, not the eccentricity of a hobby. Incorrect. 'Crunchy' refers to texture, not the nature of an obsession. Incorrect. 'Almond-like' refers to physical resemblance or taste, not behavioral eccentricity.",
  "target_word": "nutty"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "nutty",
  "relation": "synonym",
  "options": [
    "calm",
    "logical",
    "sane",
    "crazy"
  ],
  "correct_answer": "crazy",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
      "explanation": "Correct. 'Crazy' is a synonym for 'nutty' in the sense of eccentric or insane."
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "It seemed rather almond-flavored to walk outside in the freezing rain without a jacket.",
      "is_correct": false
    },
    {
      "text": "It seemed rather nutty to walk outside in the freezing rain without a jacket.",
      "is_correct": true
    },
    {
      "text": "It seemed rather crunchy to walk outside in the freezing rain without a jacket.",
      "is_correct": false
    },
    {
      "text": "It seemed rather delicious to walk outside in the freezing rain without a jacket.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect. 'Delicious' refers to taste, not the wisdom of an action. Incorrect. 'Crunchy' refers to texture, not the logic of an action. Incorrect. 'Almond-flavored' refers to taste, not the sensibility of an action.",
  "target_word": "nutty"
}
```

---

## sense 14024, level 9

#### Pack A
### Level 9 (sense 14024, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The science fiction movie was filled with nutty inventions and wild adventures."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The science fiction movie was filled with nutty inventions and wild adventures.",
  "chunks": [
    "The science fiction movie",
    "was filled",
    "with nutty inventions and wild adventures"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "The science fiction movie",
    "with nutty inventions and wild adventures",
    "was filled"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Some people think his obsession with collecting vintage spoons is completely nutty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Some people think his obsession with collecting vintage spoons is completely nutty.",
  "chunks": [
    "Some people",
    "think",
    "his obsession with collecting vintage spoons is completely nutty"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "his obsession with collecting vintage spoons is completely nutty",
    "Some people",
    "think"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14024, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "He looked a bit nutty wearing winter gloves in the middle of summer."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He looked a bit nutty wearing winter gloves in the middle of summer.",
  "chunks": [
    "He looked",
    "a bit nutty",
    "wearing winter gloves in the middle of summer"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "He looked",
    "wearing winter gloves in the middle of summer",
    "a bit nutty"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The sci-fi movie started normally before it got completely nutty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The sci-fi movie started normally before it got completely nutty.",
  "chunks": [
    "The sci fi movie",
    "started",
    "normally",
    "before it got completely nutty"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "started",
    "before it got completely nutty",
    "The sci fi movie",
    "normally"
  ],
  "target_word": "nutty",
  "chunk_count": 4
}
```

---
