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


## sense 13900, level 7

#### Pack A
### Level 7 (sense 13900, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students can pick any topic they want for their history presentation this Friday.",
      "is_correct": true
    },
    {
      "text": "People pick the beans.",
      "is_correct": true
    },
    {
      "text": "She want to pick a new dress for the party.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The third-person singular subject 'She' requires the verb form 'wants', not 'want'."
    },
    {
      "text": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
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
      "text": "She picked up the phone and pick it to her ear.",
      "is_correct": false,
      "error_description": "The verb 'pick' is incorrectly used to mean 'place' or 'move'. Additionally, there is a tense inconsistency between 'picked' (past) and 'pick' (present). The correct action for moving an object to one's ear is 'put' or 'held', not 'pick'."
    },
    {
      "text": "We need to pick a leader for our group project before the class ends today.",
      "is_correct": true
    },
    {
      "text": "They were asked to pick three options from the list of available activities.",
      "is_correct": true
    },
    {
      "text": "He always takes a long time to pick what he wants to eat at a restaurant.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 13900, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students can pick their favorite topics for the upcoming history project.",
      "is_correct": true
    },
    {
      "text": "When doctors use this information, they can pick a safer drug therapy that works just right for one specific person, stopping bad side effects before they even start.",
      "is_correct": true
    },
    {
      "text": "She wants pick the blue dress for the party.",
      "is_correct": false,
      "error_description": "The verb 'want' requires the infinitive marker 'to' to introduce the verb 'pick'. Omitting 'to' creates an incorrect verb complement structure."
    },
    {
      "text": "People pick the beans.",
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
      "text": "She decided pick the blue dress for the school dance.",
      "is_correct": false,
      "error_description": "The verb 'decide' requires a to-infinitive complement. The preposition 'to' is missing before the target verb 'pick'."
    },
    {
      "text": "Can you help me pick a good book from the library shelf?",
      "is_correct": true
    },
    {
      "text": "Everyone wanted to pick the best seat on the bus.",
      "is_correct": true
    },
    {
      "text": "We need to pick a date for our group meeting next week.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13900, level 9

#### Pack A
### Level 9 (sense 13900, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They are trying to pick a team captain for the upcoming debate competition."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They are trying to pick a team captain for the upcoming debate competition.",
  "chunks": [
    "They",
    "are trying",
    "to pick a team captain for the upcoming debate competition"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to pick a team captain for the upcoming debate competition",
    "are trying",
    "They"
  ],
  "target_word": "pick",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you had to pick one movie to watch tonight, which one would you choose?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you had to pick one movie to watch tonight, which one would you choose?",
  "chunks": [
    "If you had to pick one movie to watch tonight",
    "which one",
    "would choose",
    "you"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "would choose",
    "If you had to pick one movie to watch tonight",
    "which one",
    "you"
  ],
  "target_word": "pick",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 13900, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many teenagers find it difficult to pick a career path while they are still in school."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many teenagers find it difficult to pick a career path while they are still in school.",
  "chunks": [
    "Many teenagers",
    "find",
    "it difficult to pick a career path while they are still in school"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "it difficult to pick a career path while they are still in school",
    "find",
    "Many teenagers"
  ],
  "target_word": "pick",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "If you had to pick a favorite movie from last year, which one would it be?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "If you had to pick a favorite movie from last year, which one would it be?",
  "chunks": [
    "If you had to pick a favorite movie from last year",
    "which one",
    "would be",
    "it"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "would be",
    "If you had to pick a favorite movie from last year",
    "which one",
    "it"
  ],
  "target_word": "pick",
  "chunk_count": 4
}
```

---

## sense 13902, level 2

#### Pack A
### Level 2 (sense 13902, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "correct_definition": "To begin or proceed with an action, event, or process.",
  "options": [
    "The amount of something that is wasted or lost, especially in a process.",
    "To begin or proceed with an action, event, or process.",
    "The act of carrying out a plan, order, or course of action.",
    "The brainstem is the lower part of the brain that controls basic life functions like breathing and heartbeat."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To say that something is not true or to fight for something.",
        "The act of spreading something onto land for a specific purpose.",
        "To begin or proceed with an action, event, or process.",
        "The buying and selling of coffee and cocoa beans as a commodity."
      ],
      "correct_answer": "To begin or proceed with an action, event, or process."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13902, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "correct_definition": "To begin or proceed with an action, event, or process.",
  "options": [
    "To begin or proceed with an action, event, or process.",
    "To damage or weaken something, making it less effective.",
    "In a way that achieves the intended result.",
    "to a high degree or extent"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "go on",
  "pronunciation": "goh on",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A bean is an edible seed that grows in pods on certain plants, often used as food.",
        "An amount of money spent on something.",
        "To begin or proceed with an action, event, or process.",
        "Something that warns you to be careful."
      ],
      "correct_answer": "To begin or proceed with an action, event, or process."
    }
  }
}
```

---

## sense 13902, level 4

#### Pack A
### Level 4 (sense 13902, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Please ___ with your interesting story.",
  "original_sentence": "Please go on with your interesting story.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Please ___ with your interesting story.",
  "original_sentence": "Please go on with your interesting story.",
  "correct_answer": "go on",
  "base_form": "go on",
  "form_label": "base form",
  "options": [
    "went on",
    "going on",
    "go on",
    "goes on"
  ],
  "explanation": "base form is required after the imperative marker 'Please'",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "go on"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She paused to take a breath before she went on reading the report.",
  "original_sentence": "She paused to take a breath before she went on reading the report.",
  "correct_answer": "gone on",
  "base_form": "went on",
  "form_label": "simple past",
  "options": [
    "gone on",
    "go on",
    "gone on",
    "going on"
  ],
  "explanation": "Past participle is incorrect without an auxiliary verb (e.g., 'had').",
  "word_definition": "To begin or proceed with an action, event, or process.",
  "target_word": "gone on"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "go",
  "sentence_with_blank": "She paused to take a breath before she went on reading the report.",
  "original_sentence": "She paused to take a breath before she went on reading the report.",
  "required_pos": "adjective",
  "options": [
    "goance",
    "goify",
    "goning",
    "ongoing"
  ],
  "correct_answer": "ongoing",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "Real derived word: adjective."
    }
  }
}
```

#### Pack B
### Level 4 (sense 13902, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Let us ___ with our history project after a short break.",
  "original_sentence": "Let us go on with our history project after a short break.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He paused for a second before he chose to ___.",
  "original_sentence": "He paused for a second before he chose to go on.",
  "target_word": "go on",
  "word": "go on",
  "answer": {
    "accepted": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
    ],
    "accepted_normalized": [
      "go on",
      "goes on",
      "going on",
      "went on",
      "gone on"
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
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We must go on the experiment despite the unexpected delay.",
      "is_correct": false
    },
    {
      "text": "We must go on in the experiment despite the unexpected delay.",
      "is_correct": false
    },
    {
      "text": "We must go on with the experiment despite the unexpected delay.",
      "is_correct": true
    },
    {
      "text": "We must go on to the experiment despite the unexpected delay.",
      "is_correct": false
    }
  ],
  "explanation": "Missing preposition 'with': 'go on' meaning 'proceed' requires 'with' when followed by the activity noun. Wrong preposition 'to': 'go on to' implies moving to a *new* item, whereas 'with' implies continuing the *current* one. Wrong preposition 'in': 'in' suggests participation within bounds, not the act of proceeding/resuming.",
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
      "text": "After a brief pause, the speaker decided to go on with the lecture.",
      "is_correct": true
    },
    {
      "text": "Please go on with your interesting story.",
      "is_correct": true
    },
    {
      "text": "Let us go on with the presentation before we run out of time.",
      "is_correct": true
    },
    {
      "text": "The professor went on with explain the complex theory to the students.",
      "is_correct": false,
      "error_description": "The preposition 'with' must be followed by a noun or a gerund (verb + -ing), not the base form of the verb."
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

## sense 13902, level 9

#### Pack A
### Level 9 (sense 13902, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "We cannot go on ignoring these important safety rules."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "We cannot go on ignoring these important safety rules.",
  "chunks": [
    "We",
    "can not go on",
    "ignoring these important safety rules"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "We",
    "ignoring these important safety rules",
    "can not go on"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Why did you go on arguing about such a small mistake?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Why did you go on arguing about such a small mistake?",
  "chunks": [
    "Why did go on",
    "you",
    "arguing about such a small mistake"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "arguing about such a small mistake",
    "you",
    "Why did go on"
  ],
  "target_word": "go on",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 13902, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The committee decided to go on with the review process immediately."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The committee decided to go on with the review process immediately.",
  "chunks": [
    "The committee",
    "decided",
    "to go on with the review process immediately"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "The committee",
    "to go on with the review process immediately",
    "decided"
  ],
  "target_word": "going on",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "We must go on with the experiment despite the unexpected delay."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "We must go on with the experiment despite the unexpected delay.",
  "chunks": [
    "We must go on",
    "with the experiment",
    "despite the unexpected delay"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "despite the unexpected delay",
    "with the experiment",
    "We must go on"
  ],
  "target_word": "go on",
  "chunk_count": 3
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
    "walk",
    "work",
    "worth"
  ],
  "correct_answer": "work",
  "explanation": "Correct. This is the target word.",
  "distractor_explanations": {
    "walk": "Incorrect. 'Walk' sounds similar but means to move on foot.",
    "word": "Incorrect. 'Word' sounds similar but refers to language units.",
    "worth": "Incorrect. 'Worth' sounds similar but refers to value."
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

## sense 13929, level 2

#### Pack A
### Level 2 (sense 13929, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "correct_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "options": [
    "The main stem of a plant, especially one that supports flowers or fruit.",
    "A decision is a choice that you make after thinking about what to do.",
    "Something that protects or defends against danger or attack.",
    "To perform an activity or task, especially for pay or to achieve a result."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "helps or benefits something.",
        "A group of people living together in a place with laws and buildings.",
        "in a manner that is not the same as before or as something else",
        "To perform an activity or task, especially for pay or to achieve a result."
      ],
      "correct_answer": "To perform an activity or task, especially for pay or to achieve a result."
    }
  }
}
```

#### Pack B
### Level 2 (sense 13929, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "correct_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "options": [
    "A person who receives or entertains guests, or an organism that provides a home for another.",
    "To perform an activity or task, especially for pay or to achieve a result.",
    "feeling that you need to rest or sleep because you have been working, playing, or doing something for a long time",
    "The part of the face that sticks out above the mouth, used for breathing and smelling."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "work",
  "pronunciation": "wurk",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "relating to a dynasty, which is a series of rulers from the same family.",
        "To take control of something or someone, or to record something.",
        "relating to the way a society is organized and makes decisions.",
        "To perform an activity or task, especially for pay or to achieve a result."
      ],
      "correct_answer": "To perform an activity or task, especially for pay or to achieve a result."
    }
  }
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
  "sentence_with_blank": "The engineers will ___ to move water from far away.",
  "original_sentence": "The engineers will work to move water from far away.",
  "correct_answer": "work",
  "options": [
    "rest",
    "work",
    "sleep",
    "play"
  ],
  "explanation": "Correct. Fits the context of performing a task for a result.",
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
  "correct_answer": "works",
  "options": [
    "works",
    "plays",
    "moves",
    "runs"
  ],
  "explanation": "Correct. Fits the context of a therapy functioning effectively.",
  "distractor_tags": {},
  "word_definition": "To perform an activity or task, especially for pay or to achieve a result.",
  "target_word": "work"
}
```

---
