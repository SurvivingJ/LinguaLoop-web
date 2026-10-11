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


## sense 13902, level 6

#### Pack A
### Level 6 (sense 13902, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The sun will go on at exactly six o'clock tomorrow morning.",
      "is_correct": false
    },
    {
      "text": "After a brief pause, the speaker decided to go on with her speech.",
      "is_correct": true
    },
    {
      "text": "I decided to go on the refrigerator to see what was inside.",
      "is_correct": false
    },
    {
      "text": "She will go on the bus to travel to the city center.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'go on' means to proceed with an action, not to physically climb onto a surface (which requires 'go on top of' or 'climb on'). Incorrect: When boarding a vehicle, the correct preposition is 'on' as a standalone particle (e.g., 'get on' or 'go on the bus' is less standard than 'take the bus' or 'get on the bus'), but 'go on' as a phrasal verb for 'proceed' does not fit here. Incorrect: 'go on' means to proceed with an action or event, whereas 'rise' or 'come up' is the correct verb for the sun appearing in the sky.",
  "target_word": "go on"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The heavy snow will go on the roof and stay there all winter.",
      "is_correct": false
    },
    {
      "text": "I will go on the milk from the fridge into this glass.",
      "is_correct": false
    },
    {
      "text": "Please go on the table and sit down to eat your dinner.",
      "is_correct": false
    },
    {
      "text": "After a brief pause, the speaker decided to go on with her speech.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'go on' meaning 'proceed' cannot be used to instruct someone to physically climb onto a piece of furniture. Semantically inappropriate: 'go on' is an intransitive phrasal verb and cannot take a direct physical object like 'the milk' to mean 'pour'. Semantically inappropriate: 'go on' means to continue an action or event, not to physically accumulate or rest on a surface like snow.",
  "target_word": "go on"
}
```

#### Pack B
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
      "text": "Let us go on with the presentation now.",
      "is_correct": true
    },
    {
      "text": "After a short break, the teacher told the class to go on reading.",
      "is_correct": true
    },
    {
      "text": "Let us go on with our history project after lunch.",
      "is_correct": true
    },
    {
      "text": "After a short break, the teacher told the class to go on their reading.",
      "is_correct": false,
      "error_description": "The phrasal verb 'go on' cannot take a direct noun object. To continue an activity, it must be followed directly by a gerund (verb + -ing) or by the preposition 'with' plus a noun."
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
    "worm",
    "worth",
    "word",
    "work"
  ],
  "correct_answer": "work",
  "explanation": "Correct: this is the exact target word heard in the audio.",
  "distractor_explanations": {
    "word": "Minimal pair: differs only in the final consonant sound (/k/ vs /d/).",
    "worm": "Minimal pair: differs only in the final consonant sound (/k/ vs /m/).",
    "worth": "Minimal pair: differs only in the final consonant sound (/k/ vs /θ/)."
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

---

## sense 13929, level 3

#### Pack A
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The local engineers ___ hard to move water from far away.",
  "original_sentence": "The local engineers work hard to move water from far away.",
  "correct_answer": "work",
  "options": [
    "think",
    "rest",
    "play",
    "work"
  ],
  "explanation": "Correct: fits the grammatical structure and means to perform physical or mental effort.",
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
    "labor",
    "work",
    "rest",
    "grow"
  ],
  "explanation": "Correct: Fits the context of biological systems operating or functioning properly.",
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
    "will work",
    "working",
    "works",
    "worked"
  ],
  "explanation": "past simple tense correctly indicates a completed action",
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
    "workal",
    "workage",
    "workers",
    "workment"
  ],
  "correct_answer": "workers",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agentive nominalisation for those who perform tasks"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The miners ___ hard underground.",
  "original_sentence": "The miners work hard underground.",
  "correct_answer": "work",
  "base_form": "work",
  "form_label": "plural present",
  "options": [
    "working",
    "worked",
    "works",
    "work"
  ],
  "explanation": "plural subject requires the base form in the present tense",
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "work",
  "sentence_with_blank": "The miners ___ hard underground.",
  "original_sentence": "The miners work hard underground.",
  "required_pos": "noun",
  "options": [
    "workment",
    "workal",
    "workure",
    "worker"
  ],
  "correct_answer": "worker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established agentive nominalisation"
    }
  }
}
```

---

## sense 13929, level 6

#### Pack A
### Level 6 (sense 13929, difficulty None)
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "manage",
    "earn",
    "rest",
    "produce"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease activity and relax, opposite of performing a task"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We watch the builders work to bake a delicious cake for the party.",
      "is_correct": false
    },
    {
      "text": "We watch the builders work to perform a complex heart surgery.",
      "is_correct": false
    },
    {
      "text": "We watch the builders work every day.",
      "is_correct": true
    },
    {
      "text": "We watch the builders work to paint a beautiful picture on the canvas.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: Builders construct structures; painting a picture is the domain of artists, making the subject mismatch the action. semantic: Builders work with construction materials; baking is a culinary task, creating a pragmatic mismatch. semantic: Builders are not medical professionals; performing surgery is entirely outside their occupational scope.",
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

---

## sense 13929, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The local engineers work hard to move water from far away.",
      "is_correct": true
    },
    {
      "text": "Many men worked on the construction.",
      "is_correct": true
    },
    {
      "text": "He work hard to move water from far away.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the third-person singular subject 'He' requires the inflected verb form 'works', not the base form 'work'."
    },
    {
      "text": "They work for a very long time every day.",
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
      "text": "The miners are work hard underground.",
      "is_correct": false,
      "error_description": "The auxiliary verb 'are' cannot be directly followed by the base form of the verb 'work'. To express a present habit or general fact, the simple present tense 'work' should be used without an auxiliary, or the present continuous 'are working' should be used."
    },
    {
      "text": "We watch the builders work every day.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
      "is_correct": true
    },
    {
      "text": "The miners work hard underground.",
      "is_correct": true
    }
  ]
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
    "plastic",
    "green",
    "rapid",
    "delicious"
  ],
  "explanation": "Correct option: accurately describes the natural color of a forest.",
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

---

## sense 13931, level 6

#### Pack A
### Level 6 (sense 13931, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She felt very green when she solved the complex math equation.",
      "is_correct": false
    },
    {
      "text": "The green temperature of the soup indicated it was ready to eat.",
      "is_correct": false
    },
    {
      "text": "The grass in the backyard looks especially green this spring.",
      "is_correct": true
    },
    {
      "text": "The loud green noise kept me awake all night.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'green' is a visual color adjective and cannot logically describe an auditory phenomenon like 'noise'. Semantically inappropriate: 'green' means the color or being inexperienced, neither of which logically describes the feeling of solving a math problem. Semantically inappropriate: 'green' is a color and cannot be used to describe a physical measurement like 'temperature'.",
  "target_word": "green"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We noticed that the leaves on the trees were turning green.",
      "is_correct": true
    },
    {
      "text": "She felt very green after listening to the sad and emotional song.",
      "is_correct": false
    },
    {
      "text": "The green ideas slept furiously in the middle of the night.",
      "is_correct": false
    },
    {
      "text": "The green math equation was too difficult for the students to solve.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Green' is a visual color and cannot logically describe an abstract, non-visual concept like a math equation. Semantically inappropriate: While 'green' can mean nauseous, it is not used to describe the emotional state of feeling sad or moved by music. Semantically inappropriate: 'Ideas' are abstract concepts and cannot possess physical color properties like being 'green' or perform physical actions like 'sleeping'.",
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
      "text": "He placed the book far away on the desk right in front of him.",
      "is_correct": false
    },
    {
      "text": "She whispered the secret far away so everyone in the room could hear.",
      "is_correct": false
    },
    {
      "text": "The sound of music echoed from far away.",
      "is_correct": true
    },
    {
      "text": "The tiny ant walked far away across the small leaf.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'far away' implies a great distance, which contradicts the microscopic scale of an ant walking across a single small leaf. Semantically contradictory: 'right in front of him' indicates immediate proximity, directly negating the 'great distance' meaning of 'far away'. Pragmatically inappropriate: Whispering is done to be heard only by those very close by, making the use of 'far away' logically inconsistent with the action.",
  "target_word": "far away"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "far away",
  "relation": "antonym",
  "options": [
    "ahead",
    "elsewhere",
    "abroad",
    "nearby"
  ],
  "correct_answer": "nearby",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "at a great distance; a long way off",
      "explanation": "antonym: at a short distance rather than a great distance"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The microscopic bacteria swam far away across the petri dish in just one second.",
      "is_correct": false
    },
    {
      "text": "He placed the hot coffee far away on the table right in front of him to drink it immediately.",
      "is_correct": false
    },
    {
      "text": "Looking back, that difficult time feels like it happened far away.",
      "is_correct": true
    },
    {
      "text": "She kept her favorite necklace far away in her pocket so she could touch it every five minutes.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'far away' contradicts the physical reality of the cup being 'right in front of him' for immediate drinking. Semantically inappropriate: 'far away' implies a great distance, which is incongruous with the microscopic scale of a petri dish and the brief timeframe. Pragmatically inappropriate: An item kept 'far away' cannot be easily accessed to be touched 'every five minutes', creating a logical contradiction.",
  "target_word": "far away"
}
```

---
