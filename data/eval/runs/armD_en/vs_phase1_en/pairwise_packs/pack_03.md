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


## sense 13946, level 7

#### Pack A
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

#### Pack B
### Level 7 (sense 13946, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The beans come from far away.",
      "is_correct": true
    },
    {
      "text": "My brother decided to move to far away for his new job.",
      "is_correct": false,
      "error_description": "The phrase 'far away' functions as an adverbial phrase of place and cannot act as the object of the preposition 'to'. The preposition should be removed, or 'far away' should be replaced with a noun phrase like 'a faraway place'."
    },
    {
      "text": "My best friend moved far away last summer.",
      "is_correct": true
    },
    {
      "text": "Do you ever dream about traveling far away to exotic places?",
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
      "text": "We could see the mountains glowing far away in the dusk.",
      "is_correct": true
    },
    {
      "text": "They decided to build a house in a far away forest.",
      "is_correct": false,
      "error_description": "The phrase 'far away' functions as an adverbial phrase of place and should not be used directly before a noun as an adjective. It must be placed after the noun it modifies, or the single-word adjective 'faraway' should be used instead."
    },
    {
      "text": "Looking back, that difficult time feels like it happened far away.",
      "is_correct": true
    },
    {
      "text": "He kept his childhood diary hidden far away in the attic.",
      "is_correct": true
    }
  ]
}
```

---

## sense 13981, level 4

#### Pack A
### Level 4 (sense 13981, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She found her new job very ___ because it required working long hours every single week.",
  "original_sentence": "She found her new job very demanding because it required working long hours every single week.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "adjective",
  "options": [
    "demand",
    "demanded",
    "demanding",
    "demands"
  ],
  "explanation": "adjective form required to complete the object complement after the intensifier 'very'",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "She found her new job very ___ because it required working long hours every single week.",
  "original_sentence": "She found her new job very demanding because it required working long hours every single week.",
  "required_pos": "adjective",
  "options": [
    "demanding",
    "demandive",
    "demandment",
    "demandance"
  ],
  "correct_answer": "demanding",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the correct adjectival participle form for this context"
    }
  }
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "A ___ schedule left her with very little free time to spend with friends.",
  "original_sentence": "A demanding schedule left her with very little free time to spend with friends.",
  "correct_answer": "demanding",
  "base_form": "demand",
  "form_label": "adjective",
  "options": [
    "demanded",
    "demands",
    "demandingly",
    "demanding"
  ],
  "explanation": "adjective correctly modifies the noun 'schedule'",
  "word_definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
  "target_word": "demanding"
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "demand",
  "sentence_with_blank": "A ___ schedule left her with very little free time to spend with friends.",
  "original_sentence": "A demanding schedule left her with very little free time to spend with friends.",
  "required_pos": "adjective",
  "options": [
    "demandment",
    "demandive",
    "demandation",
    "demanding"
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

#### Pack B
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

---

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
      "text": "She found the empty box surprisingly demanding because it contained absolutely nothing inside.",
      "is_correct": false
    },
    {
      "text": "Learning to play the violin can be a demanding hobby for young teenagers.",
      "is_correct": true
    },
    {
      "text": "The demanding puppy slept peacefully on the couch all afternoon without needing anything.",
      "is_correct": false
    },
    {
      "text": "The demanding color blue looked exactly the same as it did yesterday with no changes.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'demanding' implies needing a lot of attention or effort, which contradicts the puppy sleeping peacefully and needing nothing. Semantically incoherent: an empty box cannot be 'demanding' since there is nothing to require effort, skill, or attention from. Semantically inappropriate: a color cannot be 'demanding' in the sense of requiring effort or attention; colors are visual properties, not agents that expect things from people.",
  "target_word": "demanding"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "demanding",
  "relation": "antonym",
  "options": [
    "tedious",
    "easy",
    "challenging",
    "rewarding"
  ],
  "correct_answer": "easy",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Needing a lot of effort, skill, or attention; expecting a lot from other people.",
      "explanation": "opposite sense: not requiring much effort or skill"
    }
  }
}
```

---

## sense 14010, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 14010, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "different",
  "pronunciation": "dif-ur-uhnt",
  "ipa": "/ˈdɪfərənt/",
  "syllable_count": 3,
  "audio_url": null,
  "options": [
    "diffident",
    "defiant",
    "deferent",
    "different"
  ],
  "correct_answer": "different",
  "explanation": "Correct word: matches the target pronunciation /ˈdɪf.rənt/.",
  "distractor_explanations": {
    "diffident": "near-rhyme: differs in the medial vowel /ɪ/ vs /ə/ and lacks the /r/ sound.",
    "deferent": "near-rhyme: differs in the first vowel /e/ vs /ɪ/ and the presence of the /r/ sound.",
    "defiant": "near-rhyme: differs in stress pattern and the medial vowel /aɪ/ vs /ə/."
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
    "similar",
    "different",
    "identical",
    "separate"
  ],
  "explanation": "Correct: 'Different' is the correct adjective meaning 'not the same', perfectly fitting the context of varying perceptions of time.",
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
    "differal",
    "different",
    "differment",
    "differive"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival derivation"
    }
  }
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
    "differency",
    "differentment",
    "different",
    "differentation"
  ],
  "correct_answer": "different",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adjectival form from the stem"
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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The different water tasted exactly like the other water.",
      "is_correct": false
    },
    {
      "text": "We can learn about different perspectives.",
      "is_correct": true
    },
    {
      "text": "He gave the different answer that was identical to the first one.",
      "is_correct": false
    },
    {
      "text": "She wore a different dress to be exactly the same as her sister.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'different' implies a distinction, which contradicts the statement that it tasted exactly the same. pragmatic: wearing a 'different' dress achieves the opposite of being exactly the same, making the sentence logically contradictory. semantic: 'different' means not the same, which directly conflicts with the answer being 'identical' to the first one.",
  "target_word": "different"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "different",
  "relation": "antonym",
  "options": [
    "identical",
    "various",
    "separate",
    "unique"
  ],
  "correct_answer": "identical",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Not the same as another or each other; unlike.",
      "explanation": "means exactly the same, which is the direct antonym of not the same"
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
      "text": "People from different countries speak English very different.",
      "is_correct": false,
      "error_description": "The adjective 'different' is incorrectly used to modify the verb 'speak'. The adverb 'differently' must be used to describe how the action is performed."
    },
    {
      "text": "Sometimes, this can lead to misunderstandings when people from different cultural backgrounds interact.",
      "is_correct": true
    },
    {
      "text": "They learn about different times.",
      "is_correct": true
    },
    {
      "text": "People see time in different ways.",
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
      "text": "This analysis compares how people in different regions approach the same problem.",
      "is_correct": true
    },
    {
      "text": "People in different countries celebrate the new year very different.",
      "is_correct": false,
      "error_description": "The adjective 'different' is incorrectly used to modify the verb 'celebrate'; the adverb 'differently' is required to describe how the action is performed."
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
    "nutty",
    "muddy",
    "natty",
    "putty"
  ],
  "correct_answer": "nutty",
  "explanation": "Correct: This is the exact target word pronounced /ˈnʌti/.",
  "distractor_explanations": {
    "natty": "Minimal pair: differs only in the vowel sound /æ/ in 'natty' versus /ʌ/ in 'nutty'.",
    "putty": "Minimal pair: differs only in the initial consonant /p/ in 'putty' versus /n/ in 'nutty'.",
    "muddy": "Near-homophone: shares the same /ʌ/ vowel and syllable structure, differing only in the initial /m/ and the voiced /d/ versus voiceless /t/."
  },
  "distractor_source": "llm"
}
```

---

## sense 14024, level 3

#### Pack A
### Level 3 (sense 14024, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They laughed about the ___ weather we experienced while camping last week.",
  "original_sentence": "They laughed about the nutty weather we experienced while camping last week.",
  "correct_answer": "nutty",
  "options": [
    "legislative",
    "tasty",
    "rigid",
    "nutty"
  ],
  "explanation": "Correct: 'nutty' means crazy or unpredictable, which perfectly describes the chaotic weather they laughed about.",
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
