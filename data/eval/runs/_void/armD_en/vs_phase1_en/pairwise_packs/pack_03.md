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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Our history teacher is always very demanding when we write our weekly essays.",
      "is_correct": true
    },
    {
      "text": "The history teacher is very demanding because she always lets us leave class five minutes early to beat the traffic.",
      "is_correct": false
    },
    {
      "text": "Our history teacher is extremely demanding, so she never assigns any homework and gives everyone an automatic A.",
      "is_correct": false
    },
    {
      "text": "The history teacher is quite demanding, often allowing us to submit our weekly essays a month late without any penalty.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Letting students leave early is a lenient and accommodating action, which directly contradicts the meaning of 'demanding' (expecting a lot). Semantically inappropriate: Giving no homework and automatic A's represents low expectations, the exact opposite of a teacher who is 'demanding'. Pragmatically inappropriate: Allowing massive extensions without penalty shows a lack of strictness or high expectations, making 'demanding' the wrong adjective for this context.",
  "target_word": "demanding"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The demanding breeze gently cooled the runners down after their long marathon.",
      "is_correct": false
    },
    {
      "text": "The demanding pillow made it very easy for him to fall asleep the moment his head touched it.",
      "is_correct": false
    },
    {
      "text": "She found the math problem completely demanding because she solved it in just five seconds without any effort.",
      "is_correct": false
    },
    {
      "text": "Working on the school magazine has been challenging and demanding, but also very rewarding.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: Inanimate objects like pillows do not possess the agency to 'expect a lot' from people, and a comfortable pillow is the opposite of requiring effort. Semantically contradictory: The second clause describes a task requiring zero effort, which directly negates the definition of 'demanding'. Collocationally and semantically inappropriate: 'Demanding' is not used to describe weather phenomena, and a gentle cooling breeze does not require effort or attention.",
  "target_word": "demanding"
}
```

---

## sense 14001, level 3

#### Pack A
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bugs talk to your body's defense ___, which is your immunity.",
  "original_sentence": "These bugs talk to your body's defense system, which is your immunity.",
  "correct_answer": "system",
  "options": [
    "routine",
    "system",
    "machine",
    "process"
  ],
  "explanation": "Correct: 'defense system' is the natural collocation referring to the body's immunity network.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "correct_answer": "system",
  "options": [
    "machine",
    "schedule",
    "network",
    "system"
  ],
  "explanation": "Correct: 'open system' is the standard scientific collocation for an entity that exchanges matter and energy with its environment.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that form a complex whole.",
  "target_word": "system"
}
```

#### Pack B
### Level 3 (sense 14001, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bugs talk to your body's defense ___, which is your immunity.",
  "original_sentence": "These bugs talk to your body's defense system, which is your immunity.",
  "correct_answer": "system",
  "options": [
    "routine",
    "strategy",
    "system",
    "machine"
  ],
  "explanation": "Correct: 'defense system' is the standard collocation for the body's immunity network.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A living plant is an open ___.",
  "original_sentence": "A living plant is an open system.",
  "correct_answer": "system",
  "options": [
    "machine",
    "mechanism",
    "system",
    "process"
  ],
  "explanation": "Correct: 'system' is the exact word from the base sentence, correctly identifying a plant as a set of connected parts.",
  "distractor_tags": {},
  "word_definition": "A set of connected parts that work together to form a complex whole.",
  "target_word": "system"
}
```

---

## sense 14001, level 6

#### Pack A
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system of the book was very heavy to carry in my backpack.",
      "is_correct": false
    },
    {
      "text": "The system was very loud and barked at the mailman.",
      "is_correct": false
    },
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    },
    {
      "text": "She baked a delicious system for the birthday party.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'system' refers to a set of connected parts, not a single physical object like a book. semantic: 'system' cannot refer to a baked good or food item. semantic: 'system' refers to an interconnected network of parts, not a living animal like a dog.",
  "target_word": "system"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The system was very tall and had green leaves.",
      "is_correct": false
    },
    {
      "text": "She poured a system of milk into her cereal bowl for breakfast.",
      "is_correct": false
    },
    {
      "text": "He felt a sharp pain in his system when he stubbed his toe.",
      "is_correct": false
    },
    {
      "text": "They designed a new computer system to help organize our homework files.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: 'system' refers to a complex whole of connected parts, not a physical liquid or a measurable quantity of food. semantic: A 'system' is an abstract or functional collection of parts, not a single physical organism that can grow leaves. collocational: While 'system' can refer to the body, we do not use it to describe a localized, specific physical injury like a stubbed toe; we use 'toe' or 'foot'.",
  "target_word": "system"
}
```

#### Pack B
### Level 6 (sense 14001, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "This essential box utilizes a closed loop system filled with a special liquid called a refrigerant.",
      "is_correct": true
    },
    {
      "text": "The system of the book was very interesting to read.",
      "is_correct": false
    },
    {
      "text": "She felt a system of sadness when her friend left.",
      "is_correct": false
    },
    {
      "text": "The system of the painting was blue and green.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'system' refers to connected parts forming a whole, not a property of a book's content or narrative. Semantically inappropriate: 'system' denotes organized structures, not emotions or feelings like sadness. Semantically inappropriate: 'system' cannot describe color properties; colors are attributes, not organized networks of parts.",
  "target_word": "system"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "system",
  "relation": "antonym",
  "options": [
    "chaos",
    "element",
    "component",
    "entity"
  ],
  "correct_answer": "chaos",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "A set of connected parts that form a complex whole.",
      "explanation": "antonym: a state of complete disorder, opposite of an organized set of connected parts"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He ate the entire chocolate system in just one sitting.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful blue system to the formal evening gala.",
      "is_correct": false
    },
    {
      "text": "The chef used a wooden system to stir the thick soup in the large pot.",
      "is_correct": false
    },
    {
      "text": "Scientists were studying weather systems before the heavy storm arrived.",
      "is_correct": true
    }
  ],
  "explanation": "Semantic: A 'system' refers to a complex set of connected parts, not a simple physical tool like a wooden spoon. Semantic: A 'system' is an abstract or structural concept, not a physical piece of clothing that can be worn. Semantic: A 'system' cannot refer to a countable, edible object like a chocolate bar or dessert.",
  "target_word": "systems"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "system",
  "relation": "antonym",
  "options": [
    "entity",
    "component",
    "chaos",
    "collection"
  ],
  "correct_answer": "chaos",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "A set of connected parts that form a complex whole.",
      "explanation": "antonym: a state of complete disorder with no organized structure, opposite of a connected, organized whole"
    }
  }
}
```

---

## sense 14001, level 7

#### Pack A
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
      "is_correct": true
    },
    {
      "text": "The engineers designed three new computer system for the office.",
      "is_correct": false,
      "error_description": "The noun 'system' is a countable noun and must be pluralized as 'systems' when referring to more than one, such as after the number 'three'."
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
      "is_correct": true
    },
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14001, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The engineers designed several new cooling system for the server room.",
      "is_correct": false,
      "error_description": "The noun 'system' is countable and must be pluralized as 'systems' when preceded by a quantifier like 'several'."
    },
    {
      "text": "Furthermore, these systems often process vast amounts of sensitive data, raising valid concerns about privacy and security.",
      "is_correct": true
    },
    {
      "text": "Sometimes, the defense system gets confused.",
      "is_correct": true
    },
    {
      "text": "These bugs talk to your body's defense system, which is your immunity.",
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
      "text": "Scientists were studying weather systems before the heavy storm arrived.",
      "is_correct": true
    },
    {
      "text": "Students struggled to learn how the new computer network system operated.",
      "is_correct": true
    },
    {
      "text": "A living plant is an open system.",
      "is_correct": true
    },
    {
      "text": "The new computer network system require a strong password to access the files.",
      "is_correct": false,
      "error_description": "The singular noun 'system' acts as the subject of the sentence and requires the singular verb form 'requires', not the plural form 'require'."
    }
  ]
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

#### Pack B
### Level 3 (sense 14010, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People see time in ___ ways.",
  "original_sentence": "People see time in different ways.",
  "correct_answer": "different",
  "options": [
    "identical",
    "similar",
    "different",
    "same"
  ],
  "explanation": "Correct: Fits perfectly to mean 'not the same', contrasting with 'ways'.",
  "distractor_tags": {},
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```

---

## sense 14010, level 4

#### Pack A
### Level 4 (sense 14010, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "differ",
  "sentence_with_blank": "They learn about ___ times.",
  "original_sentence": "They learn about different times.",
  "required_pos": "adjective",
  "options": [
    "differous",
    "differment",
    "differity",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival derivation from the verb"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "correct_answer": "different",
  "base_form": "different",
  "form_label": "base form",
  "options": [
    "differences",
    "different",
    "difference",
    "differently"
  ],
  "explanation": "base adjective form required to modify the noun 'countries'",
  "word_definition": "Not the same as another or each other; unlike.",
  "target_word": "different"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "differ",
  "sentence_with_blank": "The beans travel for weeks, crossing many borders, to reach ___ countries.",
  "original_sentence": "The beans travel for weeks, crossing many borders, to reach different countries.",
  "required_pos": "adjective",
  "options": [
    "differous",
    "differment",
    "differation",
    "different"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival derivation using -ent"
    }
  }
}
```

#### Pack B
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

---

## sense 14010, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 14010, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He wore a different shirt every single day for a year, but they were all the exact same blue color and size.",
      "is_correct": false
    },
    {
      "text": "The two identical twins had completely different faces, making them impossible to tell apart.",
      "is_correct": false
    },
    {
      "text": "The growth of globalism means more and more people are working and living across different cultures.",
      "is_correct": true
    },
    {
      "text": "The different water in the glass tasted exactly like the water in the bottle.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Different' implies a distinction, which contradicts the statement that they tasted 'exactly like' each other. Semantically contradictory: Describing the shirts as 'different' clashes with the immediate clarification that they were all the exact same color and size. Logically inappropriate: If they have 'completely different' faces, it would be easy to tell them apart, contradicting the second half of the sentence.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "individual",
    "particular",
    "separate",
    "identical"
  ],
  "correct_answer": "identical",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "antonym: exactly the same, not different"
    }
  }
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    },
    {
      "text": "People see time in different ways.",
      "is_correct": true
    },
    {
      "text": "They learn about different times.",
      "is_correct": true
    },
    {
      "text": "The new software version is very different the previous one in terms of user interface.",
      "is_correct": false,
      "error_description": "The adjective 'different' requires the preposition 'from' (or 'to' in British English) to introduce the entity being compared. Omitting the preposition creates a structural error."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "People in different cultures communicate different.",
      "is_correct": false,
      "error_description": "The word 'different' is an adjective and cannot be used to modify the verb 'communicate'. The adverb form 'differently' must be used to describe how the action is performed."
    },
    {
      "text": "The beans travel for weeks, crossing many borders, to reach different countries.",
      "is_correct": true
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "People living in different towns often have unique traditions.",
      "is_correct": true
    }
  ]
}
```

---

## sense 14015, level 1

#### Pack A
### Level 1 (sense 14015, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "roasting",
  "pronunciation": "ROHST-ing",
  "ipa": "ˈroʊstɪŋ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "roasting",
    "resting",
    "boasting",
    "rusting"
  ],
  "correct_answer": "roasting",
  "explanation": "Correct: This is the target word pronounced /ˈroʊstɪŋ/.",
  "distractor_explanations": {
    "boasting": "Rhyme: Shares the same /oʊstɪŋ/ ending sound but starts with a different consonant /b/ instead of /r/.",
    "rusting": "Minimal pair: Differs only in the vowel sound, using /ʌ/ (as in 'cup') instead of the /oʊ/ diphthong.",
    "resting": "Minimal pair: Differs only in the vowel sound, using /ɛ/ (as in 'bed') instead of the /oʊ/ diphthong."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14015, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Roasting",
  "pronunciation": "ROST-ing",
  "ipa": "ˈroʊstɪŋ",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "posting",
    "boasting",
    "resting",
    "Roasting"
  ],
  "correct_answer": "Roasting",
  "explanation": "Correct: This is the target word, pronounced /ˈroʊstɪŋ/.",
  "distractor_explanations": {
    "resting": "Minimal pair: differs only in the vowel sound (/ɛ/ in 'resting' vs /oʊ/ in 'roasting').",
    "boasting": "Minimal pair: differs only in the initial consonant (/b/ in 'boasting' vs /r/ in 'roasting').",
    "posting": "Minimal pair: differs only in the initial consonant (/p/ in 'posting' vs /r/ in 'roasting')."
  },
  "distractor_source": "llm"
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
    "Roasting",
    "Brewing",
    "Harvesting",
    "Packaging"
  ],
  "explanation": "Correct: 'Roasting' is the specific dry-heat cooking method that develops coffee's distinct flavors.",
  "distractor_tags": {},
  "word_definition": "Roasting is a cooking method that uses dry heat, either in an oven or over an open flame.",
  "target_word": "Roasting"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Are you ___ those peppers for the homemade salsa tonight?",
  "original_sentence": "Are you roasting those peppers for the homemade salsa tonight?",
  "correct_answer": "roasting",
  "options": [
    "roasting",
    "boiling",
    "freezing",
    "cultivating"
  ],
  "explanation": "Correct: fits the grammatical structure and context of applying dry heat to peppers for salsa.",
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

---
