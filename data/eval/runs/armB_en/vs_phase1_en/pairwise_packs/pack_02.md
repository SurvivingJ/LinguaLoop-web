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


## sense 13902, level 4

#### Pack A
### Level 4 (sense 13902, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Let us ___ with our project after a short break.",
  "original_sentence": "Let us go on with our project after a short break.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "went on",
    "go on",
    "goes on",
    "going on"
  ],
  "explanation": "base form is required after the causative verb 'let'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "go on",
  "sentence_with_blank": "Let us ___ with our project after a short break.",
  "original_sentence": "Let us go on with our project after a short break.",
  "required_pos": "adjective",
  "options": [
    "goonal",
    "oningly",
    "gonement",
    "ongoing"
  ],
  "correct_answer": "ongoing",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjective meaning continuing or in progress"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "We cannot ___ ignoring this important problem.",
  "original_sentence": "We cannot go on ignoring this important problem.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "go on",
    "going on",
    "went on",
    "goes on"
  ],
  "explanation": "base form is required after the modal auxiliary 'cannot'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```

#### Pack B
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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Will the team go on to win the championship?",
      "is_correct": true
    },
    {
      "text": "Please go on forgetting your name immediately.",
      "is_correct": false
    },
    {
      "text": "I want to go on being dead after the funeral.",
      "is_correct": false
    },
    {
      "text": "The sun will go on rising in the west tomorrow.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: describes a physically impossible event, violating real-world knowledge constraints. Semantically inappropriate: 'go on' implies continuity of an active process or state that can be maintained, which conflicts with the permanent and passive nature of death. Pragmatically inappropriate: 'forgetting' is generally not a volitional action that one can be instructed to proceed with deliberately in this manner.",
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
      "text": "Let us go on with our project after a short break.",
      "is_correct": true
    },
    {
      "text": "She go on to explain the details yesterday.",
      "is_correct": false,
      "error_description": "The sentence uses the base form 'go' with a past time reference ('yesterday') and third-person singular subject. It requires the simple past tense 'went on'."
    },
    {
      "text": "She decided to go on talking even though the bell rang.",
      "is_correct": true
    },
    {
      "text": "Let's go on with the presentation now.",
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
      "text": "Please go on reading the story from where you stopped.",
      "is_correct": true
    },
    {
      "text": "Will the team go on to win the championship?",
      "is_correct": true
    },
    {
      "text": "We cannot go on ignoring this important problem.",
      "is_correct": true
    },
    {
      "text": "She wants to go on become a doctor.",
      "is_correct": false,
      "error_description": "The phrasal verb 'go on' indicating a progression to a new stage or action is typically followed by the infinitive with 'to' (go on to do something), not the bare infinitive."
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

---

## sense 13929, level 1

#### Pack A
### Level 1 (sense 13929, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "ipa": "/wɜːrk/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "word",
    "walk",
    "work",
    "woke"
  ],
  "correct_answer": "work",
  "explanation": "Correct: matches the target word /wɜːrk/.",
  "distractor_explanations": {
    "walk": "Minimal pair: differs only in the vowel sound (/ɔː/ vs /ɜː/) and final consonant cluster.",
    "woke": "Near-homophone: shares the initial /w/ and similar vowel quality but ends in a different consonant.",
    "word": "Rhyme/Minimal pair: shares the initial /w/ and vowel /ɜː/ but ends with /d/ instead of /k/."
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

#### Pack B
### Level 3 (sense 13929, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "This big engineering team plans to ___ together to move water from far away.",
  "original_sentence": "This big engineering team plans to work together to move water from far away.",
  "correct_answer": "work",
  "options": [
    "sleep",
    "rest",
    "play",
    "work"
  ],
  "explanation": "Correct: fits the context of an engineering team performing a task together.",
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
    "work",
    "rest",
    "break",
    "play"
  ],
  "explanation": "Correct: 'work' is the appropriate verb meaning to function or operate effectively in this biological context.",
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
    "working",
    "worked",
    "works",
    "work"
  ],
  "explanation": "past simple is required by the completed action context",
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
    "worker",
    "workness",
    "workal",
    "workment"
  ],
  "correct_answer": "worker",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard agent noun formed with -er"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "It is important to ___ hard.",
  "original_sentence": "It is important to work hard.",
  "correct_answer": "work",
  "base_form": "work",
  "form_label": "base form",
  "options": [
    "working",
    "worked",
    "works",
    "work"
  ],
  "explanation": "base form is required after the infinitive marker 'to'",
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
      "text": "The sun works in the sky every morning.",
      "is_correct": false
    },
    {
      "text": "I work a headache after reading too much.",
      "is_correct": false
    },
    {
      "text": "She works beautiful today.",
      "is_correct": false
    },
    {
      "text": "They need to work hard every day to meet their goals.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: Celestial bodies do not perform labor or tasks for pay; 'shine' or 'rise' is the appropriate verb. Semantically incorrect: One does not 'perform' a headache; this confuses the causative sense with experiencing a condition. Grammatically/Semantically flawed: 'Work' is not a linking verb used to describe a state of being or appearance; 'looks' is required.",
  "target_word": "work"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We watch the crew work every day.",
      "is_correct": true
    },
    {
      "text": "We watch the crew work silence into the room.",
      "is_correct": false
    },
    {
      "text": "The crew work to become invisible to the naked eye.",
      "is_correct": false
    },
    {
      "text": "The crew work yesterday at the park.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'work' implies effort toward a goal, but becoming invisible is physically impossible for humans, making the sentence nonsensical in a realistic context. Semantically inappropriate: 'work' typically takes a direct object that is a task or material; 'silence' is an abstract state that cannot be physically manipulated or 'worked' by a crew in this literal sense. Grammatically/Semantically inappropriate: The present tense 'work' conflicts with the past time marker 'yesterday', creating a temporal contradiction.",
  "target_word": "work"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "work",
  "relation": "antonym",
  "options": [
    "operate",
    "rest",
    "toil",
    "labor"
  ],
  "correct_answer": "rest",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To perform an activity or task, especially for pay or to achieve a result.",
      "explanation": "antonym: to cease work or activity"
    }
  }
}
```

---

## sense 13929, level 7

#### Pack A
### Level 7 (sense 13929, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The machine work very fast when it is new.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The singular subject 'machine' requires the third-person singular verb form 'works', not the base form 'work'."
    },
    {
      "text": "We watch the crew work every day.",
      "is_correct": true
    },
    {
      "text": "It is important to work hard.",
      "is_correct": true
    },
    {
      "text": "This medical step gives many people a second chance at life because their bodies can work well again.",
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
    "green",
    "glean",
    "grain",
    "queen"
  ],
  "correct_answer": "green",
  "explanation": "Correct: matches the target word /ɡriːn/.",
  "distractor_explanations": {
    "grain": "Minimal pair: differs only in the final consonant sound /n/ vs /n/ with a different vowel quality or diphthong perception /eɪ/ vs /iː/; often confused in rapid speech.",
    "glean": "Homophone: identical pronunciation /ɡliːn/ to 'green' for many speakers, but different spelling and meaning.",
    "queen": "Rhyme: shares the same ending sound /iːn/ but starts with a different consonant cluster /kw/."
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
    "green",
    "happy",
    "fast",
    "loud"
  ],
  "explanation": "Correct: fits the context of a forest's natural color.",
  "distractor_tags": {},
  "word_definition": "Green is a color between blue and yellow on the spectrum, often associated with nature.",
  "target_word": "green"
}
```

---
