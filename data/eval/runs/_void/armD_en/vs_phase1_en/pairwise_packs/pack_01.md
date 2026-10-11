# Pairwise review pack 01

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


## sense 13898, level 3

#### Pack A
### Level 3 (sense 13898, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "This is a ___.",
  "original_sentence": "This is a coffee bean.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee shop",
    "coffee bean",
    "coffee cup",
    "coffee blend"
  ],
  "explanation": "Correct completion: refers to the seed of the coffee plant, fitting the context of identifying the object.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "You can smell the rich scent whenever a fresh ___ is crushed.",
  "original_sentence": "You can smell the rich scent whenever a fresh coffee bean is crushed.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee leaf",
    "coffee cup",
    "coffee extract",
    "coffee bean"
  ],
  "explanation": "Correct completion. The sentence describes crushing a fresh seed to release its characteristic scent.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 3 (sense 13898, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "This is a ___.",
  "original_sentence": "This is a coffee bean.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee maker",
    "coffee bean",
    "coffee shop",
    "coffee cup"
  ],
  "explanation": "Correct: Fits the context perfectly as the physical seed being examined and ground.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The farmer picked every ripe ___ by hand during the harvest season.",
  "original_sentence": "The farmer picked every ripe coffee bean by hand during the harvest season.",
  "correct_answer": "coffee bean",
  "options": [
    "coffee stem",
    "coffee bean",
    "coffee leaf",
    "coffee root"
  ],
  "explanation": "Correct: fits the context of a farmer harvesting a specific crop by hand.",
  "distractor_tags": {},
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 4

#### Pack A
### Level 4 (sense 13898, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She examined each ___ carefully before putting them into the roaster.",
  "original_sentence": "She examined each coffee bean carefully before putting them into the roaster.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee beans'",
    "coffee bean's",
    "coffee beans",
    "coffee bean"
  ],
  "explanation": "singular form is required by the distributive determiner 'each'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 4 (sense 13898, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She examined the single ___ closely before tossing it into the grinder.",
  "original_sentence": "She examined the single coffee bean closely before tossing it into the grinder.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee bean's",
    "coffee beans",
    "coffee bean",
    "coffee beans'"
  ],
  "explanation": "singular noun form required by the determiner 'single' and the pronoun 'it'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Smelling a fresh ___ always wakes me up in the morning.",
  "original_sentence": "Smelling a fresh coffee bean always wakes me up in the morning.",
  "correct_answer": "coffee bean",
  "base_form": "coffee bean",
  "form_label": "singular",
  "options": [
    "coffee bean",
    "coffee beans'",
    "coffee beans",
    "coffee bean's"
  ],
  "explanation": "singular noun required by the indefinite article 'a'",
  "word_definition": "A coffee bean is the seed of the coffee plant, which is roasted and ground to make coffee.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 6

#### Pack A
### Level 6 (sense 13898, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef used a giant coffee bean to hammer the nail into the wooden wall.",
      "is_correct": false
    },
    {
      "text": "He drank a hot, liquid coffee bean to wake up before his early morning meeting.",
      "is_correct": false
    },
    {
      "text": "They have been searching for the rarest type of coffee bean all morning.",
      "is_correct": true
    },
    {
      "text": "She planted the roasted coffee bean in the garden, expecting it to sprout into a new bush.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Roasted coffee beans are dead and cannot germinate or sprout. Semantically inappropriate: A coffee bean is a solid seed, not a liquid beverage that can be drunk directly. Pragmatically inappropriate: Coffee beans are small, brittle seeds and lack the physical mass or hardness to be used as a hammer.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He used a heavy coffee bean to hammer the nail into the wooden wall.",
      "is_correct": false
    },
    {
      "text": "The liquid coffee bean flowed smoothly from the espresso machine into the waiting ceramic mug.",
      "is_correct": false
    },
    {
      "text": "She planted a single coffee bean in the soil and expected a fully grown tree by the next afternoon.",
      "is_correct": false
    },
    {
      "text": "We were grinding a fresh coffee bean when the machine suddenly stopped working.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: coffee plants take several years to mature, making this expectation physically impossible. Semantically inappropriate: a coffee bean is a solid seed, not a liquid that can flow from a machine. Pragmatically inappropriate: a coffee bean is small, fragile, and entirely unsuited for use as a hammer.",
  "target_word": "coffee bean"
}
```

#### Pack B
### Level 6 (sense 13898, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The coffee bean flew across the ocean using its large, feathered wings.",
      "is_correct": false
    },
    {
      "text": "The coffee bean barked loudly at the stranger walking past the house.",
      "is_correct": false
    },
    {
      "text": "She used the coffee bean to chop down the tall tree in the forest.",
      "is_correct": false
    },
    {
      "text": "Every coffee bean has a unique aroma depending on where it was grown.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: attributes animal behavior (barking) to an inanimate plant seed. pragmatic: describes a physically impossible action, as a small seed cannot be used as an axe to chop down a tree. semantic: attributes biological features of a bird (feathered wings, flying) to a plant seed.",
  "target_word": "coffee bean"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "A dark coffee bean usually produces a stronger flavor in your cup.",
      "is_correct": true
    },
    {
      "text": "She used a heavy coffee bean to hammer the nail deep into the solid oak wall.",
      "is_correct": false
    },
    {
      "text": "He planted a roasted coffee bean in the garden, expecting it to sprout into a new plant by tomorrow.",
      "is_correct": false
    },
    {
      "text": "The mechanic poured a liquid coffee bean directly into the car's engine to lubricate the moving parts.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: roasted coffee beans are dead and cannot germinate or sprout. Pragmatically inappropriate: a coffee bean is small, light, and fragile, making it completely useless as a hammer. Semantically inappropriate: a coffee bean is a solid seed, not a liquid lubricant that can be poured.",
  "target_word": "coffee bean"
}
```

---

## sense 13898, level 7

#### Pack A
### Level 7 (sense 13898, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He dropped a single coffee bean onto the wooden table.",
      "is_correct": true
    },
    {
      "text": "She examined each coffee bean carefully before putting them into the roaster.",
      "is_correct": true
    },
    {
      "text": "She bought three coffee bean at the store.",
      "is_correct": false,
      "error_description": "After a cardinal number such as 'three', a countable noun must take the plural form. Therefore, 'coffee bean' should be corrected to 'coffee beans'."
    },
    {
      "text": "This is a coffee bean.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13898, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She examined the single coffee bean closely before tossing it into the grinder.",
      "is_correct": true
    },
    {
      "text": "This is a coffee bean.",
      "is_correct": true
    },
    {
      "text": "The coffee bean are roasted to perfection before being packaged for sale.",
      "is_correct": false,
      "error_description": "The subject 'coffee bean' is singular, but it is paired with the plural verb 'are'. To fix this subject-verb agreement error, the noun must be pluralized to 'coffee beans' to match the plural verb."
    },
    {
      "text": "Each coffee bean contains the essential oils that give the brew its rich flavor.",
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
      "text": "We were grinding a fresh coffee bean when the machine suddenly stopped working.",
      "is_correct": true
    },
    {
      "text": "She bought a bag of roasted coffee bean from the local market.",
      "is_correct": false,
      "error_description": "The noun 'coffee bean' is countable. When referring to multiple beans contained within a bag, it must take the plural form 'coffee beans'."
    },
    {
      "text": "Smelling a fresh coffee bean always wakes me up in the morning.",
      "is_correct": true
    },
    {
      "text": "The farmer picked every ripe coffee bean by hand during the harvest season.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13902, level 3

#### Pack A
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "These bags ___ big boats.",
  "original_sentence": "These bags go on big boats.",
  "correct_answer": "go on",
  "options": [
    "fly past",
    "go into",
    "go on",
    "ride on"
  ],
  "explanation": "Correct: fits the context of items being placed onto the surface of the boats.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "After finishing the first task, they had to ___ to the next one.",
  "original_sentence": "After finishing the first task, they had to go on to the next one.",
  "correct_answer": "go on",
  "options": [
    "listen",
    "holler",
    "return",
    "go on"
  ],
  "explanation": "Correct: matches the target word and fits the context of proceeding to the next task.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

#### Pack B
### Level 3 (sense 13902, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The committee decided to ___ with the meeting despite the delays.",
  "original_sentence": "The committee decided to go on with the meeting despite the delays.",
  "correct_answer": "go on",
  "options": [
    "go up",
    "go off",
    "go out",
    "go on"
  ],
  "explanation": "Correct: 'go on' perfectly fits the context of proceeding with the meeting after delays.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We are curious to see how the play will ___ tonight.",
  "original_sentence": "We are curious to see how the play will go on tonight.",
  "correct_answer": "go on",
  "options": [
    "go on",
    "go off",
    "go up",
    "go out"
  ],
  "explanation": "Correct: 'go on' correctly means to proceed or continue with the play.",
  "distractor_tags": {},
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---

## sense 13902, level 4

#### Pack A
### Level 4 (sense 13902, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with our history project after a short break.",
  "original_sentence": "Let us go on with our history project after a short break.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "go on",
    "going on",
    "goes on",
    "went on"
  ],
  "explanation": "base form is required after the causative verb 'let'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He paused for a second before he chose to ___.",
  "original_sentence": "He paused for a second before he chose to go on.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "went on",
    "going on",
    "goes on",
    "go on"
  ],
  "explanation": "base form required after the infinitive marker 'to'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

#### Pack B
### Level 4 (sense 13902, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "After a short break, the teacher told us to ___ with our reading.",
  "original_sentence": "After a short break, the teacher told us to go on with our reading.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "bare infinitive",
  "options": [
    "went on",
    "goes on",
    "go on",
    "going on"
  ],
  "explanation": "bare infinitive is required after the infinitive marker 'to'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He paused for a moment before he chose to ___ speaking.",
  "original_sentence": "He paused for a moment before he chose to go on speaking.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "bare infinitive",
  "options": [
    "went on",
    "goes on",
    "go on",
    "going on"
  ],
  "explanation": "bare infinitive required after the infinitive marker 'to'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

---

## sense 13902, level 6

#### Pack A
### Level 6 (sense 13902, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The wooden chair decided to go on barking at the mailman every morning.",
      "is_correct": false
    },
    {
      "text": "Why did you go on arguing about such a small mistake?",
      "is_correct": true
    },
    {
      "text": "In order to go on finishing the race, the runner sat down and refused to move his legs.",
      "is_correct": false
    },
    {
      "text": "She instructed the newborn baby to go on speaking fluent Russian to the guests.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic: inanimate objects like chairs cannot perform the action of barking. Pragmatic: newborn babies lack the cognitive and physical ability to speak fluent Russian. Pragmatic: sitting down and refusing to move contradicts the physical action required to finish a race.",
  "target_word": "go on"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She chose to go on interrupting the judge while he was delivering the final verdict.",
      "is_correct": false
    },
    {
      "text": "The teacher told the students to go on cheating during the final exam.",
      "is_correct": false
    },
    {
      "text": "Please go on explaining how you solved the math puzzle.",
      "is_correct": true
    },
    {
      "text": "He decided to go on sleeping while his house was burning down.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: ignoring a life-threatening emergency makes the action highly irrational and dangerous. Pragmatically inappropriate: encourages academic dishonesty and directly violates the rules of an examination. Pragmatically inappropriate: shows severe disrespect and contempt for formal court proceedings.",
  "target_word": "go on"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "go on",
  "relation": "antonym",
  "options": [
    "accelerate",
    "stop",
    "delay",
    "repeat"
  ],
  "correct_answer": "stop",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To begin or proceed with an action, event, or process.",
      "explanation": "opposite sense: to cease or discontinue an action or process"
    }
  }
}
```

#### Pack B
### Level 6 (sense 13902, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I need to go on my shoes before we leave the house.",
      "is_correct": false
    },
    {
      "text": "The soup will go on the stove for an hour.",
      "is_correct": false
    },
    {
      "text": "They watched the concert go on despite the sudden rain.",
      "is_correct": true
    },
    {
      "text": "She decided to go on the painting with a blue brush.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'go on' means to proceed or continue, whereas 'put on' is the correct phrasal verb for wearing shoes. Semantically inappropriate: 'go on' means to proceed with an action, whereas 'go on' (as in 'put on' or 'be placed on') is not the standard verb for placing an object on a surface. Collocationally inappropriate: 'go on' means to continue an event or process, whereas 'go over' or 'paint over' is required for applying paint to a surface.",
  "target_word": "go on"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Why did the discussion go on for so many hours?",
      "is_correct": true
    },
    {
      "text": "The soup will go on the stove for an hour.",
      "is_correct": false
    },
    {
      "text": "I need to go on the refrigerator to get the milk.",
      "is_correct": false
    },
    {
      "text": "He decided to go on his brother's nerves by tapping his pencil.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: Uses 'go on' to mean physically climbing onto a surface, which is a different sense than proceeding with an action or event. Incorrect: Uses 'go on' to mean being placed or located somewhere, rather than an event or process continuing. Incorrect: Misuses the phrase instead of the correct idiom 'get on someone's nerves'; 'go on' does not mean to annoy someone in this way.",
  "target_word": "go on"
}
```

---

## sense 13902, level 7

#### Pack A
### Level 7 (sense 13902, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Even though it was getting dark, the children decided to go on play in the garden.",
      "is_correct": false,
      "error_description": "The phrasal verb 'go on' meaning 'to continue' must be followed by a gerund (verb + -ing), not a bare infinitive, when indicating the continuation of the same activity."
    },
    {
      "text": "Let us go on with our history project after a short break.",
      "is_correct": true
    },
    {
      "text": "These bags go on big boats.",
      "is_correct": true
    },
    {
      "text": "She decided to go on talking even though the bell rang.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13902, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "After a brief pause, the speaker decided to go on with his presentation.",
      "is_correct": true
    },
    {
      "text": "The committee decided to go on with the meeting despite the delays.",
      "is_correct": true
    },
    {
      "text": "After a short break, the teacher told us to go on with our reading.",
      "is_correct": true
    },
    {
      "text": "The committee decided to go on the meeting despite the unexpected delays.",
      "is_correct": false,
      "error_description": "The phrasal verb 'go on' is intransitive when meaning to continue an activity; it requires the preposition 'with' before a noun object, or it must be followed by a gerund or an infinitive."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Why did the discussion go on for so many hours?",
      "is_correct": true
    },
    {
      "text": "We are curious to see how the play will go on tonight.",
      "is_correct": true
    },
    {
      "text": "He paused for a moment before he chose to go on speaking.",
      "is_correct": true
    },
    {
      "text": "Despite the heavy rain, the players went on their game until the referee finally stopped it.",
      "is_correct": false,
      "error_description": "The phrasal verb 'go on' (meaning to continue) is intransitive and requires the preposition 'with' before a direct object noun phrase. Learners often omit 'with' by directly translating from their native language."
    }
  ]
}
```

---

## sense 13929, level 1

#### Pack A
### Level 1 (sense 13929, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "ipa": "/wɜːrk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "word",
    "work",
    "worm",
    "were"
  ],
  "correct_answer": "work",
  "explanation": "Correct: this is the target word pronounced /wɜːrk/.",
  "distractor_explanations": {
    "worm": "minimal pair: differs only in the final consonant sound /m/ instead of /k/.",
    "word": "minimal pair: differs only in the final consonant sound /d/ instead of /k/.",
    "were": "near-homophone: shares the /wɜːr/ vowel sound but lacks the final /k/ consonant."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13929, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "ipa": "/wɜːrk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "work",
    "word",
    "worth",
    "worm"
  ],
  "correct_answer": "work",
  "explanation": "Correct: matches the target word pronounced as /wɜːrk/.",
  "distractor_explanations": {
    "word": "Minimal pair: differs from the target only in the final consonant sound (/d/ vs /k/).",
    "worm": "Minimal pair: differs from the target only in the final consonant sound (/m/ vs /k/).",
    "worth": "Minimal pair: differs from the target only in the final consonant sound (/θ/ vs /k/)."
  },
  "distractor_source": "llm"
}
```

---

## sense 13929, level 3

#### Pack A
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The engineers will ___ to move water from far away.",
  "original_sentence": "The engineers will work to move water from far away.",
  "correct_answer": "work",
  "options": [
    "listen",
    "play",
    "rest",
    "work"
  ],
  "explanation": "Correct: fits the grammatical structure and means to perform a task to achieve a result.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "This medical step gives many people a second chance at life because their bodies can ___ well again.",
  "original_sentence": "This medical step gives many people a second chance at life because their bodies can work well again.",
  "correct_answer": "work",
  "options": [
    "move",
    "play",
    "work",
    "rest"
  ],
  "explanation": "Correct: 'work' is the base form of the verb, which correctly follows the modal auxiliary 'can' in this context.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

#### Pack B
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The engineers will ___ to move water from far away.",
  "original_sentence": "The engineers will work to move water from far away.",
  "correct_answer": "work",
  "options": [
    "bring",
    "work",
    "rest",
    "schlep"
  ],
  "explanation": "Correct: fits the context of engineers performing physical or mental effort to achieve a result.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "This medical step gives many people a second chance at life because their bodies can ___ well again.",
  "original_sentence": "This medical step gives many people a second chance at life because their bodies can work well again.",
  "correct_answer": "work",
  "options": [
    "act",
    "work",
    "labor",
    "build"
  ],
  "explanation": "Correct: naturally describes the body returning to a state of physiological functioning.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

---
