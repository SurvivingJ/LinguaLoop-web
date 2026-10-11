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


## sense 14015, level 4

#### Pack A
### Level 4 (sense 14015, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Different ___ techniques can bring out chocolatey, nutty, or fruity notes.",
  "original_sentence": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "correct_answer": "roasting",
  "base_form": "roast",
  "form_label": "gerund",
  "options": [
    "roasts",
    "roasted",
    "roasting",
    "roast"
  ],
  "explanation": "gerund functioning as an attributive noun modifier for 'techniques'",
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "roast",
  "sentence_with_blank": "Different ___ techniques can bring out chocolatey, nutty, or fruity notes.",
  "original_sentence": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "required_pos": "noun",
  "options": [
    "roasting",
    "roastation",
    "roastment",
    "roastage"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund-noun for the dry-heat cooking method"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Proper ___ brings out the natural sweetness in root vegetables.",
  "original_sentence": "Proper roasting brings out the natural sweetness in root vegetables.",
  "correct_answer": "roasting",
  "base_form": "roast",
  "form_label": "gerund",
  "options": [
    "roasts",
    "roasted",
    "roast",
    "roasting"
  ],
  "explanation": "gerund functioning as a singular noun to agree with the verb 'brings'",
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "roast",
  "sentence_with_blank": "Proper ___ brings out the natural sweetness in root vegetables.",
  "original_sentence": "Proper roasting brings out the natural sweetness in root vegetables.",
  "required_pos": "noun",
  "options": [
    "roastment",
    "roastage",
    "roasting",
    "roastation"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund functioning as a noun for the cooking method"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14015, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "roast",
  "sentence_with_blank": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "original_sentence": "Different roasting techniques can bring out chocolatey, nutty, or fruity notes.",
  "required_pos": "noun",
  "options": [
    "roasting",
    "roastation",
    "roastment",
    "roastive"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund functioning as a noun modifier for techniques"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "roast",
  "sentence_with_blank": "The secret to this recipe is the careful ___ of the green coffee beans.",
  "original_sentence": "The secret to this recipe is the careful roasting of the green coffee beans.",
  "required_pos": "noun",
  "options": [
    "roasture",
    "roastation",
    "roastment",
    "roasting"
  ],
  "correct_answer": "roasting",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established gerund functioning as a noun after the adjective"
    }
  }
}
```

---

## sense 14015, level 6

#### Pack A
### Level 6 (sense 14015, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The roasting of the documents in the fireplace destroyed all the evidence before the audit.",
      "is_correct": false
    },
    {
      "text": "She spent the entire afternoon roasting her hair under the hot summer sun.",
      "is_correct": false
    },
    {
      "text": "The chef prefers slow roasting to keep the meat tender and juicy.",
      "is_correct": true
    },
    {
      "text": "The mechanic was roasting the engine parts in a vat of cold water to clean them.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Roasting' implies cooking for consumption, whereas 'burning' is the correct term for destroying documents. Semantically inappropriate: 'Roasting' is a culinary term for food; 'baking' or 'frying' are used metaphorically for people in the sun. Semantically inappropriate: 'Roasting' requires dry heat, making it physically contradictory to submerge parts in cold water.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "grilling",
    "boiling",
    "frying",
    "baking"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a cooking method using wet heat as opposed to the dry heat of roasting"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She is experimenting with dark roasting to find a bolder flavor profile.",
      "is_correct": true
    },
    {
      "text": "She spent the entire afternoon roasting a new software update to fix the server bugs.",
      "is_correct": false
    },
    {
      "text": "He was roasting the delicate silk scarf in the washing machine to clean it.",
      "is_correct": false
    },
    {
      "text": "The gentle roasting of the ice cubes kept the drinks perfectly cold all afternoon.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'roasting' is a physical cooking method using dry heat, not a valid term for debugging or compiling software. Semantically inappropriate: 'roasting' involves applying intense dry heat, which would melt ice cubes rather than keep them cold. Semantically inappropriate: 'roasting' requires an oven or open flame for dry heat, making it physically impossible and destructive to use inside a washing machine.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "grilling",
    "boiling",
    "frying",
    "baking"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a moist-heat cooking method contrasting with the dry heat of roasting"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14015, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They spent the afternoon roasting marshmallows over the backyard fire pit.",
      "is_correct": true
    },
    {
      "text": "The mechanic spent the afternoon roasting the motor oil to make the engine run smoother.",
      "is_correct": false
    },
    {
      "text": "The students were roasting the chalk on their desks to get ready for the math test.",
      "is_correct": false
    },
    {
      "text": "She was roasting the ice cubes in the oven to prepare a cold beverage.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'roasting' specifically refers to cooking food with dry heat, not heating mechanical fluids. Semantically inappropriate: ice cubes melt when exposed to heat and cannot be 'roasted' like solid food. Pragmatically inappropriate: chalk is an inanimate mineral tool, not a food item that can be cooked or roasted.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "frying",
    "grilling",
    "boiling",
    "baking"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a cooking method using moist heat, contrasting with the dry heat of roasting"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The roasting of the documents in the fireplace ensured that the secret information was completely destroyed.",
      "is_correct": false
    },
    {
      "text": "The loud roasting of the thunderstorm kept the children awake throughout the entire night.",
      "is_correct": false
    },
    {
      "text": "Dark roasting gives the coffee beans a bold and slightly bitter taste.",
      "is_correct": true
    },
    {
      "text": "She spent the entire afternoon roasting the heavy winter blankets to keep them warm for the bed.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Roasting' specifically refers to cooking with dry heat; 'burning' or 'incinerating' is the correct term for destroying documents. Semantically inappropriate: 'Roasting' applies to food items undergoing a chemical change via heat, not to inanimate objects like blankets which would simply catch fire. Semantically inappropriate: 'Roasting' denotes a cooking method or intense physical heat, whereas the correct auditory word for a storm is 'roaring'.",
  "target_word": "roasting"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Roasting",
  "relation": "antonym",
  "options": [
    "grilling",
    "frying",
    "baking",
    "boiling"
  ],
  "correct_answer": "boiling",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
      "explanation": "antonym: a moist-heat cooking method contrasting with the dry heat of roasting"
    }
  }
}
```

---

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
      "text": "She admired the beautiful aroma of the painting hanging in the gallery.",
      "is_correct": false
    },
    {
      "text": "The finished product is typically characterized by its dark, crumbly texture and an earthy aroma, signifying the successful culmination of the waste reduction and gardening enhancement cycle.",
      "is_correct": true
    },
    {
      "text": "The mathematical aroma of the equation helped him solve the complex problem.",
      "is_correct": false
    },
    {
      "text": "The loud aroma of the rock concert made it difficult for the audience to hear the band.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Aroma' refers to a smell, which cannot be 'loud' or interfere with hearing. Semantically inappropriate: Visual art is appreciated for its appearance, not its smell, making 'aroma' an illogical choice here. Semantically inappropriate: Abstract concepts like mathematics do not possess physical scents, so 'aroma' cannot apply to an equation.",
  "target_word": "aroma"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He could not detect any aroma from the silent, odorless gas leaking into the poorly ventilated basement.",
      "is_correct": false
    },
    {
      "text": "The mechanic wiped the grease from his hands, leaving behind a sharp, metallic aroma of industrial solvents.",
      "is_correct": false
    },
    {
      "text": "The strong aroma of the burning rubber tires made everyone in the neighborhood cover their noses in disgust.",
      "is_correct": false
    },
    {
      "text": "A subtle aroma of vanilla lingered in the room long after the cake was gone.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'aroma' specifically denotes a pleasant or distinctive smell, making it the wrong lexical choice for the foul stench of burning rubber. Semantically inappropriate: The sentence explicitly describes the gas as 'odorless', creating a direct logical contradiction with the presence of an 'aroma'. Pragmatically inappropriate: 'aroma' is not used to describe harsh, chemical, or industrial smells like solvents, which are typically referred to as fumes or odors.",
  "target_word": "aroma"
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
    "putty",
    "natty",
    "nutty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "Correct: This is the exact target word pronounced /ˈnʌti/.",
  "distractor_explanations": {
    "natty": "Minimal pair: differs only in the vowel sound /æ/ instead of /ʌ/.",
    "putty": "Minimal pair: differs only in the initial consonant /p/ instead of /n/.",
    "knotty": "Near-homophone: shares the /n/ and /ti/ sounds, but uses a different vowel /ɒ/ or /ɑ/."
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

## sense 14024, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He has always been known for having ___ hobbies like collecting ancient spoons.",
  "original_sentence": "He has always been known for having nutty hobbies like collecting ancient spoons.",
  "correct_answer": "nutty",
  "options": [
    "nervous",
    "nutty",
    "nutritious",
    "noisy"
  ],
  "explanation": "Correct: 'Nutty' correctly means eccentric or crazy, fitting the context of unusual hobbies.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
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
      "text": "She wore a very nutty dress to the formal gala, which was highly traditional and conservative.",
      "is_correct": false
    },
    {
      "text": "The chef prepared a nutty soup that was completely bland and lacked any flavor.",
      "is_correct": false
    },
    {
      "text": "The movie plot became completely nutty by the time the second half started.",
      "is_correct": true
    },
    {
      "text": "The math problem was completely nutty, as it only required simple addition to solve.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'nutty' implies a strong, eccentric, or crazy character, which directly contradicts the description of the soup being 'completely bland'. Pragmatically inappropriate: 'nutty' means eccentric or crazy, which clashes logically with the dress being described as 'highly traditional and conservative'. Pragmatically inappropriate: 'nutty' implies something is wildly complex, crazy, or insane, which contradicts the problem being a simple, straightforward addition task.",
  "target_word": "nutty"
}
```

---

## sense 14033, level 1

#### Pack A
### Level 1 (sense 14033, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "small",
  "pronunciation": "smawl",
  "ipa": "/smɔːl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "small",
    "smell",
    "smelt",
    "smile"
  ],
  "correct_answer": "small",
  "explanation": "Correct: This is the target word pronounced /smɔːl/.",
  "distractor_explanations": {
    "smell": "Minimal pair: differs only in the vowel sound /ɛ/ instead of /ɔː/.",
    "smile": "Minimal pair: differs only in the vowel sound /aɪ/ instead of /ɔː/.",
    "smelt": "Minimal pair: differs only by the addition of the final /t/ consonant."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14033, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "small",
  "pronunciation": "smawl",
  "ipa": "/smɔːl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "smell",
    "small",
    "shawl",
    "smile"
  ],
  "correct_answer": "small",
  "explanation": "correct word: the exact target word heard in the audio.",
  "distractor_explanations": {
    "smell": "minimal pair: differs only in the vowel sound /ɔː/ vs /ɛ/.",
    "smile": "minimal pair: differs only in the vowel sound /ɔː/ vs /aɪ/.",
    "shawl": "rhyme: shares the same /ɔːl/ ending and syllable count but starts with a different consonant cluster /ʃ/ vs /sm/."
  },
  "distractor_source": "llm"
}
```

---

## sense 14033, level 3

#### Pack A
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Every night, the ___child goes to bed early.",
  "original_sentence": "Every night, the small child goes to bed early.",
  "correct_answer": "small",
  "options": [
    "small",
    "fast",
    "loud",
    "heavy"
  ],
  "explanation": "Correct: 'small' correctly describes the size of the child, fitting the context of going to bed early.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small "
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He had a ___wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "correct_answer": "small",
  "options": [
    "small",
    "colossal",
    "minuscule",
    "loud"
  ],
  "explanation": "correct word: fits the context of describing the physical size of a toy horse.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small "
}
```

#### Pack B
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Every night, the ___ child goes to bed early.",
  "original_sentence": "Every night, the small child goes to bed early.",
  "correct_answer": "small",
  "options": [
    "small",
    "wooden",
    "tall",
    "loud"
  ],
  "explanation": "Correct: 'small' naturally describes a young child's physical size in this context.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "small"
}
```

---

## sense 14033, level 6

#### Pack A
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He felt very small because he was extremely tall.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "The small sun burned brightly in the sky all day.",
      "is_correct": false
    },
    {
      "text": "The small ocean was full of salt water.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatically inappropriate: the sun is universally understood as a massive celestial body, so calling it 'small' contradicts basic world knowledge. semantically contradictory: being extremely tall directly conflicts with the physical definition of 'small' (less than average size). pragmatically inappropriate: oceans are inherently vast bodies of water, making the adjective 'small' contextually and logically absurd.",
  "target_word": "small"
}
```

#### Pack B
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small ocean stretched out for thousands of miles.",
      "is_correct": false
    },
    {
      "text": "The small giant towered over the rest of the basketball team.",
      "is_correct": false
    },
    {
      "text": "Small animals can hide.",
      "is_correct": true
    },
    {
      "text": "The small elephant easily lifted the heavy car with its trunk.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: an elephant described as 'small' would not realistically possess the physical strength to lift a heavy car. Semantically inappropriate: an ocean is inherently massive; describing it as 'small' contradicts the fundamental definition of the word. Semantically inappropriate: 'small' and 'giant' are direct antonyms in the context of physical size, creating a logical contradiction.",
  "target_word": "Small "
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The small ocean covers more than seventy percent of the Earth's surface.",
      "is_correct": false
    },
    {
      "text": "The small skyscraper towered over the city at over a thousand feet tall.",
      "is_correct": false
    },
    {
      "text": "He ate a small feast consisting of fifty different dishes.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: an ocean is by definition a vast body of water, making 'small' semantically contradictory. pragmatic: a feast implies a large, abundant meal, which pragmatically contradicts the modifier 'small'. pragmatic: a skyscraper is inherently a very tall and large building, making 'small' pragmatically inappropriate.",
  "target_word": "small "
}
```

---

## sense 14100, level 3

#### Pack A
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "correct_answer": "ascend",
  "options": [
    "linger",
    "descend",
    "ascend",
    "dissolve"
  ],
  "explanation": "Correct: lift enables aircraft to move upward against gravity.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

#### Pack B
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "correct_answer": "ascend",
  "options": [
    "board",
    "ascend",
    "plummet",
    "hoist"
  ],
  "explanation": "Correct: fits the context of aerodynamic lift enabling upward movement.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings.",
  "original_sentence": "She watched her team ascend to the top of the league standings.",
  "correct_answer": "ascend",
  "options": [
    "sprout",
    "fall",
    "ascend",
    "elevate"
  ],
  "explanation": "correct: appropriately describes moving upward in a competitive ranking",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

---
