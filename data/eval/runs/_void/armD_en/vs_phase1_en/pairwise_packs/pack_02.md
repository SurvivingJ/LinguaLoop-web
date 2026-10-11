# Pairwise review pack 02

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


## sense 13929, level 4

#### Pack A
### Level 4 (sense 13929, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "correct_answer": "worked",
  "base_form": "work",
  "form_label": "past simple",
  "options": [
    "working",
    "worked",
    "works",
    "work"
  ],
  "explanation": "past simple form correctly indicates a completed action",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "worked"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "work",
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "required_pos": "noun",
  "options": [
    "workers",
    "workials",
    "workations",
    "workments"
  ],
  "correct_answer": "workers",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agentive nominalisation fitting the plural subject role"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The miners have to ___ hard in the tunnels.",
  "original_sentence": "The miners have to work hard in the tunnels.",
  "correct_answer": "work",
  "base_form": "work",
  "form_label": "base form",
  "options": [
    "works",
    "worked",
    "work",
    "working"
  ],
  "explanation": "base form is required after the semi-modal 'have to'",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

#### Pack B
### Level 4 (sense 13929, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Many men ___ on the construction.",
  "original_sentence": "Many men worked on the construction.",
  "correct_answer": "worked",
  "base_form": "work",
  "form_label": "past simple",
  "options": [
    "work",
    "worked",
    "works",
    "working"
  ],
  "explanation": "past simple is required because the sentence describes a completed past action",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "worked"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The crew must ___ hard.",
  "original_sentence": "The crew must work hard.",
  "correct_answer": "work",
  "base_form": "work",
  "form_label": "base form",
  "options": [
    "working",
    "worked",
    "work",
    "works"
  ],
  "explanation": "base form is required after the modal verb 'must'",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

---

## sense 13929, level 6

#### Pack A
### Level 6 (sense 13929, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sleeping baby worked loudly to finish the marathon.",
      "is_correct": false
    },
    {
      "text": "They had to work hard every single day.",
      "is_correct": true
    },
    {
      "text": "She worked incredibly hard to ensure she failed all her exams.",
      "is_correct": false
    },
    {
      "text": "The wooden chair worked all day to cook a delicious meal.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: inanimate objects like chairs cannot perform conscious tasks or cook. pragmatic: working hard implies striving for success, making the goal of failing exams a contradictory and inappropriate use of the word. semantic: a sleeping baby cannot exert physical effort or run a marathon, contradicting the definition of performing a task.",
  "target_word": "work"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "strive",
    "labor",
    "perform",
    "rest"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease activity and relax, the opposite of performing a task"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The silent alarm works loudly to wake up the sleeping baby.",
      "is_correct": false
    },
    {
      "text": "We watch them work every single day.",
      "is_correct": true
    },
    {
      "text": "The textbook works in the backpack to teach the math lesson.",
      "is_correct": false
    },
    {
      "text": "The heavy rain works outside to dry the wet pavement.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: textbooks are inanimate objects and cannot perform the active task of teaching on their own. Semantically inappropriate: rain wets surfaces, so it contradicts the physical reality of drying the pavement. Pragmatically inappropriate: a 'silent' alarm by definition does not make loud noises, creating a logical contradiction.",
  "target_word": "work"
}
```

#### Pack B
### Level 6 (sense 13929, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They had to work hard every single day.",
      "is_correct": true
    },
    {
      "text": "The engineers will work to move water from far away, even though they are currently asleep in their beds.",
      "is_correct": false
    },
    {
      "text": "The engineers will work to move water from far away using a single spoon and a lot of patience.",
      "is_correct": false
    },
    {
      "text": "The engineers will work to move water from far away by simply wishing for it to happen.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: one cannot actively perform physical tasks like moving water while asleep. Semantically inappropriate: 'work' implies physical or mental effort and action, not magical or passive wishing. Pragmatically inappropriate: using a spoon to move large amounts of water contradicts the logical, real-world application of engineering work.",
  "target_word": "work"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "rest",
    "plan",
    "manage",
    "organize"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease activity and relax rather than perform a task"
    }
  }
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "plan",
    "build",
    "manage",
    "rest"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease laboring and relax instead of performing a task"
    }
  }
}
```

---

## sense 13929, level 7

#### Pack A
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She work very hard at her new job.",
      "is_correct": false,
      "error_description": "The subject 'She' is third-person singular, so the verb must take the '-s' inflection ('works') rather than the base form ('work')."
    },
    {
      "text": "The engineers will work to move water from far away.",
      "is_correct": true
    },
    {
      "text": "They had to work for a very long time.",
      "is_correct": true
    },
    {
      "text": "Many men worked on the construction.",
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
      "text": "We watch the builders to work every day.",
      "is_correct": false,
      "error_description": "After perception verbs like 'watch', the object is followed by a bare infinitive without 'to'."
    },
    {
      "text": "The miners have to work hard in the tunnels.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
      "is_correct": true
    },
    {
      "text": "We watch the builders work every day.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They had to work for a very long time.",
      "is_correct": true
    },
    {
      "text": "The engineer work to move water from far away.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the singular subject 'engineer' requires the third-person singular present tense verb 'works' instead of the base form 'work'."
    },
    {
      "text": "Many men worked on the construction.",
      "is_correct": true
    },
    {
      "text": "The engineers will work to move water from far away.",
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
      "text": "The crew must work hard.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
      "is_correct": true
    },
    {
      "text": "He work very hard every day.",
      "is_correct": false,
      "error_description": "The subject 'He' is third-person singular, so the present tense verb must take the '-s' inflection ('works') rather than the base form ('work')."
    },
    {
      "text": "We watch them work every single day.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13931, level 1

#### Pack A
### Level 1 (sense 13931, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "ipa": "/ɡriːn/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "grin",
    "green",
    "glean",
    "greed"
  ],
  "correct_answer": "green",
  "explanation": "Correct: the target word /ɡriːn/ as naturally written.",
  "distractor_explanations": {
    "greed": "Minimal pair: differs only in final consonant /n/ vs /d/.",
    "grin": "Minimal pair: differs only in vowel /iː/ vs /ɪ/.",
    "glean": "Minimal pair: differs only in consonant /r/ vs /l/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 13931, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "green",
  "pronunciation": "green",
  "ipa": "/ɡriːn/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "glean",
    "greed",
    "green",
    "grin"
  ],
  "correct_answer": "green",
  "explanation": "Correct target word: matches the spoken /ɡriːn/.",
  "distractor_explanations": {
    "glean": "minimal pair: differs only in the liquid consonant /r/ vs /l/.",
    "grin": "minimal pair: differs only in the vowel sound /iː/ vs /ɪ/.",
    "greed": "minimal pair: differs only in the final consonant /n/ vs /d/."
  },
  "distractor_source": "llm"
}
```

---

## sense 13931, level 3

#### Pack A
### Level 3 (sense 13931, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The animal walks in a ___ forest.",
  "original_sentence": "The animal walks in a green forest.",
  "correct_answer": "green",
  "options": [
    "savory",
    "posh",
    "green",
    "metallic"
  ],
  "explanation": "correct: appropriately describes the natural color of a forest.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Is that sweater blue or is it ___?",
  "original_sentence": "Is that sweater blue or is it green?",
  "correct_answer": "green",
  "options": [
    "wooden",
    "square",
    "green",
    "expensive"
  ],
  "explanation": "Correct target word: fits the context of contrasting visual colors.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```

#### Pack B
### Level 3 (sense 13931, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The animal walks in a ___ forest.",
  "original_sentence": "The animal walks in a green forest.",
  "correct_answer": "green",
  "options": [
    "loud",
    "blue",
    "green",
    "metallic"
  ],
  "explanation": "Correct: 'green' naturally describes the color of a forest.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Some tropical frogs have amazingly bright ___ skin.",
  "original_sentence": "Some tropical frogs have amazingly bright green skin.",
  "correct_answer": "green",
  "options": [
    "green",
    "metallic",
    "square",
    "transparent"
  ],
  "explanation": "Correct: accurately describes the typical bright, natural color of tropical frog skin.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```

---

## sense 13931, level 6

#### Pack A
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The green arithmetic melted the loud triangle.",
      "is_correct": false
    },
    {
      "text": "The grass in the park is always bright green during the spring.",
      "is_correct": true
    },
    {
      "text": "The green ideas slept furiously in the abstract corner.",
      "is_correct": false
    },
    {
      "text": "She tasted the green silence of the number seven.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically anomalous: 'green' cannot modify abstract 'ideas,' and ideas cannot 'sleep furiously.' Pragmatically inappropriate: 'green' cannot describe 'silence,' and numbers cannot be tasted. Semantically incoherent: 'green' cannot describe 'arithmetic,' and arithmetic cannot melt physical shapes.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She tasted the green flavor of the invisible soup.",
      "is_correct": false
    },
    {
      "text": "The heavy stone felt incredibly green when I lifted it.",
      "is_correct": false
    },
    {
      "text": "The loud siren was a very green noise that hurt my ears.",
      "is_correct": false
    },
    {
      "text": "His eyes were a striking shade of green.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'green' is a visual color adjective and cannot logically describe an auditory stimulus like a siren. Semantically inappropriate: 'green' describes visual appearance, not a gustatory flavor, especially for something explicitly described as 'invisible'. Pragmatically inappropriate: 'green' is a visual property and cannot be perceived through the tactile sense of feeling a stone's weight or texture.",
  "target_word": "green"
}
```

#### Pack B
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He brushed his teeth with green shoe polish.",
      "is_correct": false
    },
    {
      "text": "The green light told him to stop the car immediately.",
      "is_correct": false
    },
    {
      "text": "She wore a bright green jacket to the school party.",
      "is_correct": true
    },
    {
      "text": "The green blood pumped through his veins.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: a green traffic light signals drivers to go, not to stop. pragmatic: shoe polish is a toxic substance meant for leather, completely inappropriate for oral hygiene. semantic: human and most animal blood is red, making green blood biologically inaccurate in a standard context.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The snow on the mountain was bright green in the middle of winter.",
      "is_correct": false
    },
    {
      "text": "The blood from his cut was a vibrant shade of green.",
      "is_correct": false
    },
    {
      "text": "The sky is always green during a clear sunny day.",
      "is_correct": false
    },
    {
      "text": "The small frog sitting on the rock was dark green.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate because the sky is blue, not green, on a clear day. Semantically inappropriate because snow is naturally white, not green. Pragmatically inappropriate because human blood is red, not green.",
  "target_word": "green"
}
```

---

## sense 13946, level 6

#### Pack A
### Level 6 (sense 13946, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "elsewhere",
    "abroad",
    "nearby",
    "ahead"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "genuine antonym: at a short distance rather than a great one"
    }
  }
}
```

#### Pack B
### Level 6 (sense 13946, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He kept his keys far away in his own front pocket.",
      "is_correct": false
    },
    {
      "text": "The mountains look so far away in the morning fog.",
      "is_correct": true
    },
    {
      "text": "The tiny ant walked far away across the small leaf in just one second.",
      "is_correct": false
    },
    {
      "text": "The moon is far away, so it takes light over eight minutes to reach us from it.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: an ant walking across a single leaf is a very short physical distance, making 'far away' a contradictory and unnatural description. Semantically inappropriate: a front pocket is immediately on one's person, which directly contradicts the definition of being 'at a great distance'. Factually and pragmatically inappropriate: the description of light taking over eight minutes applies to the Sun, not the Moon (which takes about 1.3 seconds), making the sentence logically flawed.",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "overseas",
    "abroad",
    "nearby",
    "elsewhere"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: at a short distance, the opposite of far away"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The tiny ant walked far away in just one single second.",
      "is_correct": false
    },
    {
      "text": "He tasted the soup and realized the salt was added far away.",
      "is_correct": false
    },
    {
      "text": "Birds migrate far away during the cold winter months.",
      "is_correct": true
    },
    {
      "text": "She kept her favorite book far away on the desk right in front of her.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'right in front of her' indicates close proximity, which directly contradicts the meaning of 'far away'. Semantically inappropriate: an ant cannot physically cover a 'great distance' in a single second, making the event structure and physical reality illogical. Semantically inappropriate: 'far away' describes physical spatial distance, which cannot be logically perceived through the sense of taste.",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "aside",
    "nearby",
    "abroad",
    "ahead"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: means at a short distance, the direct opposite of far away"
    }
  }
}
```

---

## sense 13946, level 7

#### Pack A
### Level 7 (sense 13946, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Do you ever dream of traveling far away?",
      "is_correct": true
    },
    {
      "text": "The beans come from far away.",
      "is_correct": true
    },
    {
      "text": "My best friend moved far away last summer.",
      "is_correct": true
    },
    {
      "text": "My grandparents live in far away.",
      "is_correct": false,
      "error_description": "The phrase 'far away' functions as an adverb of place and does not require a preceding preposition like 'in'. Adding 'in' incorrectly treats the adverbial phrase as a noun phrase."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "His family lives far away across the ocean.",
      "is_correct": true
    },
    {
      "text": "Birds migrate far away during the cold winter months.",
      "is_correct": true
    },
    {
      "text": "The nearest hospital is ten miles far away from our town.",
      "is_correct": false,
      "error_description": "The phrase 'far away' should not be used immediately after a specific distance measurement. When stating an exact distance, use 'away' by itself."
    },
    {
      "text": "The old castle stands far away on a lonely hill.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13946, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nearest supermarket is far away of our house, so we need to drive.",
      "is_correct": false,
      "error_description": "The preposition 'of' is incorrectly used after 'far away'. The correct preposition to indicate distance from a specific location is 'from'."
    },
    {
      "text": "We could see the mountains standing far away against the bright blue sky.",
      "is_correct": true
    },
    {
      "text": "The beans come from far away.",
      "is_correct": true
    },
    {
      "text": "My best friend moved far away last summer, and I miss her terribly.",
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
      "text": "My grandparents live far away of the busy city.",
      "is_correct": false,
      "error_description": "The adverbial phrase 'far away' must be followed by the preposition 'from' when indicating a point of reference. Using 'of' is a common structural error for English learners."
    },
    {
      "text": "They dreamed of traveling to a mysterious island far away across the ocean.",
      "is_correct": true
    },
    {
      "text": "Sound travels slower than light, so the fireworks seemed far away before we heard them.",
      "is_correct": true
    },
    {
      "text": "The dark boat drifted quietly far away from the small island.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13981, level 3

#### Pack A
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "fragile",
    "demanding",
    "tedious",
    "spontaneous"
  ],
  "explanation": "Correct: 'Demanding' correctly describes a process that requires a significant amount of physical effort and hard work.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

#### Pack B
### Level 3 (sense 13981, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically ___ and crucial for the quality of the final product.",
  "original_sentence": "Farmers work hard, harvesting the coffee cherries by hand or with machines, a process that is physically demanding and crucial for the quality of the final product.",
  "correct_answer": "demanding",
  "options": [
    "fragile",
    "mandatory",
    "demanding",
    "stagnant"
  ],
  "explanation": "Correct: fits the context of a process requiring significant physical effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Balancing schoolwork and sports can be extremely ___ for teenagers.",
  "original_sentence": "Balancing schoolwork and sports can be extremely demanding for teenagers.",
  "correct_answer": "demanding",
  "options": [
    "demanding",
    "heavy",
    "sudden",
    "relaxing"
  ],
  "explanation": "The correct adjective describing a task that requires a lot of effort and attention.",
  "distractor_tags": {},
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```

---

## sense 13981, level 4

#### Pack A
### Level 4 (sense 13981, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "Playing the piano at such a high level requires a ___ practice schedule every single day.",
  "original_sentence": "Playing the piano at such a high level requires a demanding practice schedule every single day.",
  "required_pos": "adjective",
  "options": [
    "demandation",
    "demandment",
    "demanding",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning requiring great effort or skill"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "The hiking trail grew increasingly ___ as they climbed higher into the mountains.",
  "original_sentence": "The hiking trail grew increasingly demanding as they climbed higher into the mountains.",
  "required_pos": "adjective",
  "options": [
    "demandive",
    "demandity",
    "demanding",
    "demandous"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established participial adjective meaning needing effort"
    }
  }
}
```

#### Pack B
### Level 4 (sense 13981, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The young pianist practiced for hours every single day because her new piece was extremely ___.",
  "original_sentence": "The young pianist practiced for hours every single day because her new piece was extremely demanding.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "adjective",
  "options": [
    "demanding",
    "demand",
    "demands",
    "demanded"
  ],
  "explanation": "adjective form required after the linking verb and adverb to describe the piece",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "The young pianist practiced for hours every single day because her new piece was extremely ___.",
  "original_sentence": "The young pianist practiced for hours every single day because her new piece was extremely demanding.",
  "required_pos": "adjective",
  "options": [
    "demanding",
    "demandation",
    "demandment",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival participle meaning requiring great effort or skill"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Learning a second language is a ___ task that requires daily practice.",
  "original_sentence": "Learning a second language is a demanding task that requires daily practice.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "present participle / adjective",
  "options": [
    "demanding",
    "demanded",
    "demand",
    "demands"
  ],
  "explanation": "present participle functioning as an adjective to describe the task's difficulty",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "Learning a second language is a ___ task that requires daily practice.",
  "original_sentence": "Learning a second language is a demanding task that requires daily practice.",
  "required_pos": "adjective",
  "options": [
    "demandation",
    "demandment",
    "demanding",
    "demandful"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival present participle"
    }
  }
}
```

---
