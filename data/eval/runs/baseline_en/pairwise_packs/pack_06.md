# Pairwise review pack 06

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


## sense 14020, level 4

#### Pack A
### Level 4 (sense 14020, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___s of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aromas of rising dough.",
  "target_word": "aroma",
  "word": "aromas",
  "answer": {
    "accepted": [
      "aroma"
    ],
    "accepted_normalized": [
      "aroma"
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
### Level 4 (sense 14020, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted ___s of rising dough.",
  "original_sentence": "His small shop, nestled at the cobblestone corner of the main square, quickly fills with the comforting, toasted aromas of rising dough.",
  "target_word": "aroma",
  "word": "aromas",
  "answer": {
    "accepted": [
      "aroma"
    ],
    "accepted_normalized": [
      "aroma"
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

---

## sense 14020, level 9

#### Pack A
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied.",
  "chunks": [
    "The rich aromas of brewing tea",
    "filled",
    "the quiet room",
    "while they studied"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "the quiet room",
    "The rich aromas of brewing tea",
    "filled",
    "while they studied"
  ],
  "target_word": "aroma",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14020, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The rich aromas of brewing tea filled the quiet room while they studied.",
  "chunks": [
    "The rich aromas of brewing tea",
    "filled",
    "the quiet room",
    "while they studied"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "the quiet room",
    "The rich aromas of brewing tea",
    "filled",
    "while they studied"
  ],
  "target_word": "aroma",
  "chunk_count": 4
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
    "putty",
    "nutty",
    "nitty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "This is the target word, correctly spelled as it would be pronounced /ˈnʌti/.",
  "distractor_explanations": {
    "knotty": "near-homophone: very close in sound, differing mainly in the vowel (/ɒ/ vs /ʌ/), but means 'full of knots'.",
    "nitty": "minimal pair: differs only in the vowel sound (/ɪ/ vs /ʌ/), as in the phrase 'nitty-gritty'.",
    "putty": "rhymes with the target but starts with a different consonant (/p/ vs /n/); means a soft moldable substance."
  },
  "distractor_source": "llm"
}
```

#### Pack B
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
    "putty",
    "nutty",
    "nitty",
    "knotty"
  ],
  "correct_answer": "nutty",
  "explanation": "This is the target word, correctly spelled as it would be pronounced /ˈnʌti/.",
  "distractor_explanations": {
    "knotty": "near-homophone: very close in sound, differing mainly in the vowel (/ɒ/ vs /ʌ/), but means 'full of knots'.",
    "nitty": "minimal pair: differs only in the vowel sound (/ɪ/ vs /ʌ/), as in the phrase 'nitty-gritty'.",
    "putty": "rhymes with the target but starts with a different consonant (/p/ vs /n/); means a soft moldable substance."
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
    "Openness is the quality of being honest, transparent, and willing to consider different ideas or experiences.",
    "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
    "In a way that is very noticeable, sudden, or exciting.",
    "A relationship between two different kinds of living things that helps both of them."
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
        "To spread out means to move or be distributed over a larger area.",
        "to finish or make something whole",
        "making something more complex or having more parts",
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
    "Openness is the quality of being honest, transparent, and willing to consider different ideas or experiences.",
    "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
    "In a way that is very noticeable, sudden, or exciting.",
    "A relationship between two different kinds of living things that helps both of them."
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
        "To spread out means to move or be distributed over a larger area.",
        "to finish or make something whole",
        "making something more complex or having more parts",
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
  "sentence_with_blank": "My uncle came up with some ___ plan to build a spaceship out of old lawnmowers.",
  "original_sentence": "My uncle came up with some nutty plan to build a spaceship out of old lawnmowers.",
  "correct_answer": "nutty",
  "options": [
    "punctual",
    "spicy",
    "formal",
    "nutty"
  ],
  "explanation": "Correct: matches the sentence, describing the uncle's crazy/eccentric plan.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everyone laughed at his ___ suggestion during the student council meeting.",
  "original_sentence": "Everyone laughed at his nutty suggestion during the student council meeting.",
  "correct_answer": "nutty",
  "options": [
    "polite",
    "quiet",
    "expensive",
    "nutty"
  ],
  "explanation": "Correct: matches the sentence exactly, describing an idea that seems crazy or eccentric enough to be laughed at.",
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
  "sentence_with_blank": "My uncle came up with some ___ plan to build a spaceship out of old lawnmowers.",
  "original_sentence": "My uncle came up with some nutty plan to build a spaceship out of old lawnmowers.",
  "correct_answer": "nutty",
  "options": [
    "punctual",
    "spicy",
    "formal",
    "nutty"
  ],
  "explanation": "Correct: matches the sentence, describing the uncle's crazy/eccentric plan.",
  "distractor_tags": {},
  "word_definition": "If you say something is nutty, you mean it is crazy, eccentric, or insane.",
  "target_word": "nutty"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everyone laughed at his ___ suggestion during the student council meeting.",
  "original_sentence": "Everyone laughed at his nutty suggestion during the student council meeting.",
  "correct_answer": "nutty",
  "options": [
    "polite",
    "quiet",
    "expensive",
    "nutty"
  ],
  "explanation": "Correct: matches the sentence exactly, describing an idea that seems crazy or eccentric enough to be laughed at.",
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
  "sentence_with_blank": "He had some really ___ ideas about building a flying bicycle in his garage.",
  "original_sentence": "He had some really nutty ideas about building a flying bicycle in his garage.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
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
  "sentence_with_blank": "He had some really ___ ideas about building a flying bicycle in his garage.",
  "original_sentence": "He had some really nutty ideas about building a flying bicycle in his garage.",
  "required_pos": "adjective",
  "options": [
    "nutty",
    "nuttal",
    "nuttic",
    "nuttous"
  ],
  "correct_answer": "nutty",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective form fits attributively before the noun"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "It seems a bit ___ to wear a winter coat during the middle of summer.",
  "original_sentence": "It seems a bit nutty to wear a winter coat during the middle of summer.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
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
  "sentence_with_blank": "He had some really ___ ideas about building a flying bicycle in his garage.",
  "original_sentence": "He had some really nutty ideas about building a flying bicycle in his garage.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
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
  "sentence_with_blank": "He had some really ___ ideas about building a flying bicycle in his garage.",
  "original_sentence": "He had some really nutty ideas about building a flying bicycle in his garage.",
  "required_pos": "adjective",
  "options": [
    "nutty",
    "nuttal",
    "nuttic",
    "nuttous"
  ],
  "correct_answer": "nutty",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective form fits attributively before the noun"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "It seems a bit ___ to wear a winter coat during the middle of summer.",
  "original_sentence": "It seems a bit nutty to wear a winter coat during the middle of summer.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest",
      "nuttily",
      "nuttiness"
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

---

## sense 14024, level 9

#### Pack A
### Level 9 (sense 14024, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "The movie featured a nutty scientist who invented a machine to talk to animals."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The movie featured a nutty scientist who invented a machine to talk to animals.",
  "chunks": [
    "The movie",
    "featured",
    "a nutty scientist who invented a machine to talk to animals"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "The movie",
    "a nutty scientist who invented a machine to talk to animals",
    "featured"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "That sounds like a nutty scheme that could never possibly work in real life."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That sounds like a nutty scheme that could never possibly work in real life.",
  "chunks": [
    "That",
    "sounds",
    "like a nutty scheme that could never possibly work in real life"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "like a nutty scheme that could never possibly work in real life",
    "That",
    "sounds"
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
  "original_sentence": "The movie featured a nutty scientist who invented a machine to talk to animals."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The movie featured a nutty scientist who invented a machine to talk to animals.",
  "chunks": [
    "The movie",
    "featured",
    "a nutty scientist who invented a machine to talk to animals"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "The movie",
    "a nutty scientist who invented a machine to talk to animals",
    "featured"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "That sounds like a nutty scheme that could never possibly work in real life."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "That sounds like a nutty scheme that could never possibly work in real life.",
  "chunks": [
    "That",
    "sounds",
    "like a nutty scheme that could never possibly work in real life"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "like a nutty scheme that could never possibly work in real life",
    "That",
    "sounds"
  ],
  "target_word": "nutty",
  "chunk_count": 3
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
    "squall",
    "shawl",
    "small",
    "stall"
  ],
  "correct_answer": "small",
  "explanation": "This is the target word as naturally spoken and spelled.",
  "distractor_explanations": {
    "stall": "rhymes with target (-all ending) but differs in the onset consonant cluster (st- vs sm-)",
    "shawl": "rhymes with target (-all ending) but starts with a different consonant sound (sh- vs sm-)",
    "squall": "rhymes with target (-all ending) but begins with a different consonant cluster (squ- vs sm-)"
  },
  "distractor_source": "llm"
}
```

#### Pack B
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
    "squall",
    "shawl",
    "small",
    "stall"
  ],
  "correct_answer": "small",
  "explanation": "This is the target word as naturally spoken and spelled.",
  "distractor_explanations": {
    "stall": "rhymes with target (-all ending) but differs in the onset consonant cluster (st- vs sm-)",
    "shawl": "rhymes with target (-all ending) but starts with a different consonant sound (sh- vs sm-)",
    "squall": "rhymes with target (-all ending) but begins with a different consonant cluster (squ- vs sm-)"
  },
  "distractor_source": "llm"
}
```

---

## sense 14033, level 2

#### Pack A
### Level 2 (sense 14033, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Small",
  "pronunciation": "smawl",
  "correct_definition": "Of a size that is less than average.",
  "options": [
    "The process of returning to a normal state after an illness, injury, or difficulty.",
    "Of a size that is less than average.",
    "If a person or thing is mature, they are fully developed or grown, either physically or mentally.",
    "The quality of being easy to use, reach, or understand, especially for people with disabilities."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Small",
  "pronunciation": "smawl",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "happening or continuing without stopping, driving further action.",
        "A cup without a handle.",
        "A country that stays alone and does not help other countries.",
        "Of a size that is less than average."
      ],
      "correct_answer": "Of a size that is less than average."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14033, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Small",
  "pronunciation": "smawl",
  "correct_definition": "Of a size that is less than average.",
  "options": [
    "The process of returning to a normal state after an illness, injury, or difficulty.",
    "Of a size that is less than average.",
    "If a person or thing is mature, they are fully developed or grown, either physically or mentally.",
    "The quality of being easy to use, reach, or understand, especially for people with disabilities."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Small",
  "pronunciation": "smawl",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "happening or continuing without stopping, driving further action.",
        "A cup without a handle.",
        "A country that stays alone and does not help other countries.",
        "Of a size that is less than average."
      ],
      "correct_answer": "Of a size that is less than average."
    }
  }
}
```

---

## sense 14033, level 3

#### Pack A
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___ things eat it.",
  "original_sentence": "Small things eat it.",
  "correct_answer": "Small",
  "options": [
    "Small",
    "Broken",
    "Sleepy",
    "Loud"
  ],
  "explanation": "Correct: matches the sentence exactly and fits the context of size.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "Small"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___ animals can hide.",
  "original_sentence": "Small animals can hide.",
  "correct_answer": "Small",
  "options": [
    "Small",
    "Large",
    "Wet",
    "Friendly"
  ],
  "explanation": "Correct: matches the sentence exactly, describing animals of below-average size that can hide.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "Small"
}
```

#### Pack B
### Level 3 (sense 14033, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___ things eat it.",
  "original_sentence": "Small things eat it.",
  "correct_answer": "Small",
  "options": [
    "Small",
    "Broken",
    "Sleepy",
    "Loud"
  ],
  "explanation": "Correct: matches the sentence exactly and fits the context of size.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "Small"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "___ animals can hide.",
  "original_sentence": "Small animals can hide.",
  "correct_answer": "Small",
  "options": [
    "Small",
    "Large",
    "Wet",
    "Friendly"
  ],
  "explanation": "Correct: matches the sentence exactly, describing animals of below-average size that can hide.",
  "distractor_tags": {},
  "word_definition": "Of a size that is less than average.",
  "target_word": "Small"
}
```

---
