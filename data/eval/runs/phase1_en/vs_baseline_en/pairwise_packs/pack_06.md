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
    "A measurement of how heavy an object or person is.",
    "A device or signal that warns of danger or reminds you to do something.",
    "To construct or create something by putting parts together.",
    "If you say something is nutty, you mean it is crazy, eccentric, or insane."
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
        "The length of time that someone has lived or that something has existed.",
        "to make something known or available to others.",
        "A river is a large natural stream of water that flows across land into another body of water.",
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
  "sentence_with_blank": "My younger brother came up with a really ___ plan to build a treehouse.",
  "original_sentence": "My younger brother came up with a really nutty plan to build a treehouse.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Sometimes my friends can act a little ___ when they are tired.",
  "original_sentence": "Sometimes my friends can act a little nutty when they are tired.",
  "target_word": "nutty",
  "word": "nutty",
  "answer": {
    "accepted": [
      "nutty",
      "nuttier",
      "nuttiest"
    ],
    "accepted_normalized": [
      "nutty",
      "nuttier",
      "nuttiest"
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
  "original_sentence": "He looked a bit nutty wearing winter gloves in the middle of summer."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "He looked a bit nutty wearing winter gloves in the middle of summer.",
  "chunks": [
    "He looked",
    "a bit nutty",
    "wearing winter gloves in the middle of summer"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "He looked",
    "wearing winter gloves in the middle of summer",
    "a bit nutty"
  ],
  "target_word": "nutty",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The sci-fi movie started normally before it got completely nutty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The sci-fi movie started normally before it got completely nutty.",
  "chunks": [
    "The sci fi movie",
    "started",
    "normally",
    "before it got completely nutty"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "started",
    "before it got completely nutty",
    "The sci fi movie",
    "normally"
  ],
  "target_word": "nutty",
  "chunk_count": 4
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
  "word": "small ",
  "pronunciation": "smawl",
  "correct_definition": "Of a size that is less than average.",
  "options": [
    "Of a size that is less than average.",
    "The act of making something less in amount, size, or degree.",
    "Free from tension or anxiety; not strict or formal.",
    "To bring or hand over something to another person."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "small ",
  "pronunciation": "smawl",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A specific action or strategy planned to achieve a particular goal.",
        "To look at something and decide what it is like or how good it is.",
        "To express disagreement with an opinion, group, or authority, often in a formal or public way.",
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

## sense 14033, level 4

#### Pack A
### Level 4 (sense 14033, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "small",
  "sentence_with_blank": "It is made of small parts.",
  "original_sentence": "It is made of small parts.",
  "required_pos": "adjective",
  "options": [
    "smallal",
    "smallify",
    "small",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective is the correctly derived form needed to modify the noun"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "target_word": "small",
  "word": "Small",
  "answer": {
    "accepted": [
      "small",
      "smaller",
      "smallest"
    ],
    "accepted_normalized": [
      "small",
      "smaller",
      "smallest"
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
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "small",
  "sentence_with_blank": "He had a ___ wooden toy horse.",
  "original_sentence": "He had a small wooden toy horse.",
  "required_pos": "adjective",
  "options": [
    "smallify",
    "small",
    "smallment",
    "smallation"
  ],
  "correct_answer": "small",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective used directly to modify the noun"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14033, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The parent turns on a ___ yellow lamp.",
  "original_sentence": "The parent turns on a small yellow lamp.",
  "target_word": "small",
  "word": "small ",
  "answer": {
    "accepted": [
      "small",
      "smaller",
      "smallest"
    ],
    "accepted_normalized": [
      "small",
      "smaller",
      "smallest"
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "This final stage can happen in large factories or ___, local roasteries.",
  "original_sentence": "This final stage can happen in large factories or smaller, local roasteries.",
  "target_word": "smaller",
  "word": "small ",
  "answer": {
    "accepted": [
      "smaller"
    ],
    "accepted_normalized": [
      "smaller"
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

## sense 14033, level 6

#### Pack A
### Level 6 (sense 14033, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The elephant was small enough to hide inside a matchbox.",
      "is_correct": false
    },
    {
      "text": "They built small walls.",
      "is_correct": true
    },
    {
      "text": "They gave him a small mansion for his birthday.",
      "is_correct": false
    },
    {
      "text": "The skyscraper was small, casting a tiny shadow that covered the whole city.",
      "is_correct": false
    }
  ],
  "explanation": "Semantically impossible: elephants are among the largest land animals and cannot be matchbox-sized. Contradictory: a skyscraper is by definition huge, and a 'tiny shadow' covering a whole city is logically inconsistent. Pragmatically odd: 'mansion' inherently implies a large residence, so pairing it with 'small' creates a contradiction.",
  "target_word": "small"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Every night, the small child goes to bed early.",
      "is_correct": true
    },
    {
      "text": "The ocean is small and stretches for thousands of miles in every direction.",
      "is_correct": false
    },
    {
      "text": "The small giant lifted the entire building with ease.",
      "is_correct": false
    },
    {
      "text": "She let out a small shout across the quiet library.",
      "is_correct": false
    }
  ],
  "explanation": "Contradiction: 'giant' inherently means huge, so pairing it with 'small' creates a logical clash. Contradiction: describing something that spans thousands of miles as 'small' is factually inconsistent. Pragmatic mismatch: a 'shout' is inherently loud, so calling it 'small' clashes with the word's normal meaning.",
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

## sense 14033, level 9

#### Pack A
### Level 9 (sense 14033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "It is made of small parts."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "It is made of small parts.",
  "chunks": [
    "It",
    "is made",
    "of small parts"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "of small parts",
    "is made",
    "It"
  ],
  "target_word": "Small ",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Small animals can hide."
}
```

#### Pack B
### Level 9 (sense 14033, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Small plastic things go in the water."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Small plastic things go in the water.",
  "chunks": [
    "Small plastic things",
    "go",
    "in the water"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in the water",
    "go",
    "Small plastic things"
  ],
  "target_word": "Small",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "They built small walls."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They built small walls.",
  "chunks": [
    "They",
    "built",
    "small walls"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "built",
    "They",
    "small walls"
  ],
  "target_word": "small",
  "chunk_count": 3
}
```

---
