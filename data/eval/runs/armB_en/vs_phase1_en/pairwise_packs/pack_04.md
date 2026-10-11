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


## sense 14010, level 1

#### Pack A
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-fuh-rent",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "indifferent",
    "deferent",
    "different"
  ],
  "correct_answer": "different",
  "explanation": "Correct: matches the target word exactly.",
  "distractor_explanations": {
    "diffident": "Near-homophone: shares initial syllables and stress pattern, but ends in /ənt/ vs /ənt/ with a distinct medial vowel quality and meaning (shy/reserved).",
    "deferent": "Phonetic confusability: similar stress pattern and ending, differs mainly in the medial vowel /ɪ/ vs /e/.",
    "indifferent": "Rhyme/Near-homophone: contains the target sound sequence but adds a prefix, potentially causing mishearing of the whole word."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "DIF-uh-ruhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "different",
    "deferent",
    "diffident",
    "defiant"
  ],
  "correct_answer": "different",
  "explanation": "Correct target word.",
  "distractor_explanations": {
    "diffident": "Minimal pair: differs only in the /r/ vs /d/ sound in the second syllable.",
    "deferent": "Near-homophone: shares the same syllable structure but differs in the first vowel sound (/ɪ/ vs /ɛ/).",
    "defiant": "Rhymes with the target but differs in stress pattern and the second vowel sound."
  },
  "distractor_source": "llm"
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
    "similar",
    "uniform",
    "identical",
    "different"
  ],
  "explanation": "Correct: Fits the context of varying manners or methods.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "This means how people in ___ places think.",
  "original_sentence": "This means how people in different places think.",
  "correct_answer": "different",
  "options": [
    "different",
    "identical",
    "remote",
    "similar"
  ],
  "explanation": "Correct: fits the context of comparing thinking styles across locations.",
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
    "heterogeneous",
    "different",
    "identical",
    "contrary"
  ],
  "explanation": "Correct option: the target word as it appears in the sentence.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

---

## sense 14010, level 4

#### Pack A
### Level 4 (sense 14010, difficulty None)
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "differ",
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "required_pos": "adjective",
  "options": [
    "differive",
    "differation",
    "differment",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival derivation from differ"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14010, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "correct_answer": "different",
  "base_form": "different",
  "form_label": "base form",
  "options": [
    "different",
    "differently",
    "differences",
    "difference"
  ],
  "explanation": "base adjective form required to modify the noun 'countries'",
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

---

## sense 14010, level 6

#### Pack A
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "This apple is different than that apple because they are both red delicious apples from the same tree.",
      "is_correct": false
    },
    {
      "text": "The growth of globalism means more and more people are working and living across different cultures.",
      "is_correct": true
    },
    {
      "text": "She felt different happy after receiving the good news.",
      "is_correct": false
    },
    {
      "text": "The two twins wore different outfits that were exactly the same color and style.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Different' contradicts the description 'exactly the same', creating a logical inconsistency. Grammatically/Semantically inappropriate: 'Different' is an adjective and cannot modify another adjective ('happy') in this manner without a preposition or adverbial form (e.g., 'differently'). Semantically weak/inappropriate: While grammatically possible, the justification provided ('because they are both...') supports similarity, making the use of 'different' pragmatically confusing and contradictory to the evidence given.",
  "target_word": "different"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "He bought a different car because he wanted the exact same model and color as his old one.",
      "is_correct": false
    },
    {
      "text": "Water is different from H2O.",
      "is_correct": false
    },
    {
      "text": "The two identical twins looked completely different from each other.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Identical twins' are defined by their physical similarity, making the claim that they look 'completely different' logically contradictory in a standard context. Semantically incorrect: Water and H2O are the same substance, so stating they are 'different' is factually wrong. Pragmatically contradictory: Buying the 'exact same' item negates the typical implication of 'different' as a change in type or identity.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "same",
    "varied",
    "distinct",
    "separate"
  ],
  "correct_answer": "same",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "direct antonym meaning identical or not different"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The number four is a different flavor than the number nine.",
      "is_correct": false
    },
    {
      "text": "I want to buy a different car, so I will purchase the exact same model I already own.",
      "is_correct": false
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "Since both identical twins have the exact same DNA, their genetic makeup is completely different.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: contradicts the premise that the twins have the exact same DNA. semantic: numbers are abstract concepts and do not possess physical flavors. pragmatic: purchasing the exact same model contradicts the stated goal of buying a different car.",
  "target_word": "different"
}
```

---

## sense 14010, level 7

#### Pack A
### Level 7 (sense 14010, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "People see time in different ways.",
      "is_correct": true
    },
    {
      "text": "They learn about different times.",
      "is_correct": true
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    },
    {
      "text": "The climate in this region is completely different than the climate in my home country.",
      "is_correct": false,
      "error_description": "The adjective 'different' should be followed by the preposition 'from' rather than 'than' when making comparisons in standard English."
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14010, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "This means how people in different places think.",
      "is_correct": true
    },
    {
      "text": "People in different places thinks differently.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The plural subject 'People' requires the plural verb form 'think', not the singular 'thinks'."
    },
    {
      "text": "The beans travel for weeks, crossing many borders, to reach different countries.",
      "is_correct": true
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    }
  ]
}
```

---

## sense 14015, level 3

#### Pack A
### Level 3 (sense 14015, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___ is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "original_sentence": "Roasting is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "correct_answer": "Roasting",
  "options": [
    "Harvesting",
    "Frying",
    "Planting",
    "Roasting"
  ],
  "explanation": "Correct completion. It is the noun/gerund referring to the dry-heat cooking method that develops coffee flavors.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "Roasting"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Before making soup, he tried ___ the tomatoes to deepen their flavor.",
  "original_sentence": "Before making soup, he tried roasting the tomatoes to deepen their flavor.",
  "correct_answer": "roasting",
  "options": [
    "roasting",
    "peeling",
    "eating",
    "boiling"
  ],
  "explanation": "Correct: 'Roasting' is the exact gerund form required by the sentence to describe the cooking method applied to the tomatoes.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
}
```

#### Pack B
### Level 3 (sense 14015, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___ is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "original_sentence": "Roasting is a critical step that develops the distinct flavors and aromas we associate with coffee.",
  "correct_answer": "Roasting",
  "options": [
    "Roasting",
    "Packaging",
    "Brewing",
    "Serving"
  ],
  "explanation": "Correct: fits the context of developing flavors in coffee through dry heat.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "Roasting"
}
```

---

## sense 14015, level 4

#### Pack A
### Level 4 (sense 14015, difficulty None)
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Their family enjoys the process of ___ nuts during the winter holidays.",
  "original_sentence": "Their family enjoys the process of roasting nuts during the winter holidays.",
  "correct_answer": "roasting",
  "base_form": "roast",
  "form_label": "gerund",
  "options": [
    "roast",
    "roasting",
    "roasted",
    "roasts"
  ],
  "explanation": "gerund form is required after the preposition 'of'",
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "roasting"
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

## sense 14020, level 3

#### Pack A
### Level 3 (sense 14020, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___ of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aroma of rising dough.",
  "correct_answer": "aroma",
  "options": [
    "smoke",
    "taste",
    "warmth",
    "aroma"
  ],
  "explanation": "Correct: fits the context of a pleasant smell from baking dough filling the shop.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Different spices create a wonderful ___ when they are heated in the pan.",
  "original_sentence": "Different spices create a wonderful aroma when they are heated in the pan.",
  "correct_answer": "aroma",
  "options": [
    "texture",
    "dish",
    "aroma",
    "recipe"
  ],
  "explanation": "The correct target word that naturally completes the sentence.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aroma"
}
```

#### Pack B
### Level 3 (sense 14020, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Sweet floral ___ filled the garden during the warm spring evening.",
  "original_sentence": "Sweet floral aromas filled the garden during the warm spring evening.",
  "correct_answer": "aromas",
  "options": [
    "sounds",
    "textures",
    "aromas",
    "views"
  ],
  "explanation": "Correct: plural noun fitting the context of multiple scents filling the garden.",
  "distractor_tags": {},
  "word_definition": "A pleasant, distinctive smell, often of food or drink.",
  "target_word": "aromas"
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
      "text": "As we opened the oven door, a rich, earthy aroma filled the kitchen and made our mouths water.",
      "is_correct": true
    },
    {
      "text": "The chemical spill released a toxic aroma that required immediate evacuation.",
      "is_correct": false
    },
    {
      "text": "He could hear the sharp aroma of the vinegar from across the room.",
      "is_correct": false
    },
    {
      "text": "The aroma of the rotting garbage was so strong that we had to hold our noses.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'aroma' specifically denotes a pleasant or distinctive smell, whereas rotting garbage produces a foul odor (stench). Semantically inappropriate: 'aroma' is an olfactory sensation (smell), not an auditory one (sound); one cannot 'hear' an aroma. Pragmatically inappropriate: 'aroma' carries a positive connotation of pleasantness; a toxic chemical release would be described as a 'fume', 'gas', or 'odor', not an aroma.",
  "target_word": "aroma"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The aroma of the bright red paint was visible from across the room.",
      "is_correct": false
    },
    {
      "text": "The aroma of the loud music was too intense for the neighbors.",
      "is_correct": false
    },
    {
      "text": "He analyzed the aroma of the complex mathematical equation.",
      "is_correct": false
    },
    {
      "text": "Pine needles added a refreshing aroma to the winter air.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatic error: 'aroma' refers to smell, but 'music' is an auditory stimulus and does not have a scent. Semantic error: abstract concepts like equations do not possess physical properties like smell. Category error: 'aroma' is an olfactory perception and cannot be 'visible' or seen.",
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

---

## sense 14024, level 1

#### Pack A
### Level 1 (sense 14024, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "nutty",
  "pronunciation": "NUH-tee",
  "ipa": "/ˈnʌti/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "naughty",
    "natty",
    "knotty",
    "nutty"
  ],
  "correct_answer": "nutty",
  "explanation": "Correct: matches the target word /ˈnʌti/.",
  "distractor_explanations": {
    "naughty": "Near-homophone: similar vowel and ending sounds, but distinct initial consonant cluster /nɔːti/ vs /ˈnʌti/.",
    "natty": "Minimal pair: differs only in the vowel sound /æ/ vs /ʌ/.",
    "knotty": "Homophone: identical pronunciation /ˈnɒti/ or /ˈnʌti/ depending on dialect, but different spelling and meaning."
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
