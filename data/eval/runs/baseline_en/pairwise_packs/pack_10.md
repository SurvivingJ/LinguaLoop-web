# Pairwise review pack 10

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


## sense 14473, level 3

#### Pack A
### Level 3 (sense 14473, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___, it got better.",
  "original_sentence": "Over time, it got better.",
  "correct_answer": "Over time",
  "options": [
    "By chance",
    "In vain",
    "Over time",
    "At once"
  ],
  "explanation": "Correct: matches the gradual, process-based meaning of the sentence.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "Over time"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Secret information can leak out ___, so it is best to be careful.",
  "original_sentence": "Secret information can leak out over time, so it is best to be careful.",
  "correct_answer": "over time",
  "options": [
    "on time",
    "over time",
    "at times",
    "in no time"
  ],
  "explanation": "Correct: fits the sentence, showing information leaking gradually as time passes.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```

#### Pack B
### Level 3 (sense 14473, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___, it got better.",
  "original_sentence": "Over time, it got better.",
  "correct_answer": "Over time",
  "options": [
    "By chance",
    "In vain",
    "Over time",
    "At once"
  ],
  "explanation": "Correct: matches the gradual, process-based meaning of the sentence.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "Over time"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Secret information can leak out ___, so it is best to be careful.",
  "original_sentence": "Secret information can leak out over time, so it is best to be careful.",
  "correct_answer": "over time",
  "options": [
    "on time",
    "over time",
    "at times",
    "in no time"
  ],
  "explanation": "Correct: fits the sentence, showing information leaking gradually as time passes.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```

---

## sense 14473, level 4

#### Pack A
### Level 4 (sense 14473, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Her English skills improved ___ as she practiced speaking every single day.",
  "original_sentence": "Her English skills improved over time as she practiced speaking every single day.",
  "target_word": "over time",
  "word": "Over time",
  "answer": {
    "accepted": [
      "over time"
    ],
    "accepted_normalized": [
      "over time"
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
  "sentence_with_blank": "___, the small town transformed into a busy modern city.",
  "original_sentence": "Over time, the small town transformed into a busy modern city.",
  "target_word": "Over time",
  "word": "Over time",
  "answer": {
    "accepted": [
      "Over time"
    ],
    "accepted_normalized": [
      "over time"
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
### Level 4 (sense 14473, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Her English skills improved ___ as she practiced speaking every single day.",
  "original_sentence": "Her English skills improved over time as she practiced speaking every single day.",
  "target_word": "over time",
  "word": "Over time",
  "answer": {
    "accepted": [
      "over time"
    ],
    "accepted_normalized": [
      "over time"
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
  "sentence_with_blank": "___, the small town transformed into a busy modern city.",
  "original_sentence": "Over time, the small town transformed into a busy modern city.",
  "target_word": "Over time",
  "word": "Over time",
  "answer": {
    "accepted": [
      "Over time"
    ],
    "accepted_normalized": [
      "over time"
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

## sense 14473, level 6

#### Pack A
### Level 6 (sense 14473, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She won the race over time after crossing the finish line first.",
      "is_correct": false
    },
    {
      "text": "The light switched on over time as soon as he flipped the switch.",
      "is_correct": false
    },
    {
      "text": "The old wooden fence started to fade and rust over time.",
      "is_correct": true
    },
    {
      "text": "Over time, the bomb exploded without warning.",
      "is_correct": false
    }
  ],
  "explanation": "An explosion is instantaneous, so 'over time' contradicts the sudden nature of the event. Winning a race is a single instant event, incompatible with the gradual meaning of 'over time'. Switching on a light is immediate, so 'over time' misapplies a gradual sense to a sudden action.",
  "target_word": "over time"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "relation": "antonym",
  "options": [
    "briefly",
    "instantly",
    "occasionally",
    "eventually"
  ],
  "correct_answer": "instantly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Gradually, as time goes by.",
      "explanation": "antonym: happening immediately rather than gradually over a period"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The light switched on over time when she flipped it.",
      "is_correct": false
    },
    {
      "text": "She won the race over time, finishing in first place after ten seconds.",
      "is_correct": false
    },
    {
      "text": "The bomb exploded over time, destroying the building instantly.",
      "is_correct": false
    },
    {
      "text": "The heavy rain eroded the soil over time, shaping the valley below.",
      "is_correct": true
    }
  ],
  "explanation": "Contradiction: an explosion is instantaneous, so pairing it with 'over time' (a gradual process) is semantically inconsistent. Contradiction: finishing a race in ten seconds is a quick, single event, not something that happens gradually over time. Contradiction: switching on a light is an instant action, so describing it as happening 'over time' is pragmatically odd.",
  "target_word": "over time"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Over time",
  "relation": "antonym",
  "options": [
    "eventually",
    "briefly",
    "occasionally",
    "instantly"
  ],
  "correct_answer": "instantly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Gradually, as time goes by.",
      "explanation": "antonym: happening at once rather than gradually across a period"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14473, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She won the race over time after crossing the finish line first.",
      "is_correct": false
    },
    {
      "text": "The light switched on over time as soon as he flipped the switch.",
      "is_correct": false
    },
    {
      "text": "The old wooden fence started to fade and rust over time.",
      "is_correct": true
    },
    {
      "text": "Over time, the bomb exploded without warning.",
      "is_correct": false
    }
  ],
  "explanation": "An explosion is instantaneous, so 'over time' contradicts the sudden nature of the event. Winning a race is a single instant event, incompatible with the gradual meaning of 'over time'. Switching on a light is immediate, so 'over time' misapplies a gradual sense to a sudden action.",
  "target_word": "over time"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "relation": "antonym",
  "options": [
    "briefly",
    "instantly",
    "occasionally",
    "eventually"
  ],
  "correct_answer": "instantly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Gradually, as time goes by.",
      "explanation": "antonym: happening immediately rather than gradually over a period"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The light switched on over time when she flipped it.",
      "is_correct": false
    },
    {
      "text": "She won the race over time, finishing in first place after ten seconds.",
      "is_correct": false
    },
    {
      "text": "The bomb exploded over time, destroying the building instantly.",
      "is_correct": false
    },
    {
      "text": "The heavy rain eroded the soil over time, shaping the valley below.",
      "is_correct": true
    }
  ],
  "explanation": "Contradiction: an explosion is instantaneous, so pairing it with 'over time' (a gradual process) is semantically inconsistent. Contradiction: finishing a race in ten seconds is a quick, single event, not something that happens gradually over time. Contradiction: switching on a light is an instant action, so describing it as happening 'over time' is pragmatically odd.",
  "target_word": "over time"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Over time",
  "relation": "antonym",
  "options": [
    "eventually",
    "briefly",
    "occasionally",
    "instantly"
  ],
  "correct_answer": "instantly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Gradually, as time goes by.",
      "explanation": "antonym: happening at once rather than gradually across a period"
    }
  }
}
```

---

## sense 14473, level 9

#### Pack A
### Level 9 (sense 14473, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "His confidence grew over time while working on different group projects at school."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "His confidence grew over time while working on different group projects at school.",
  "chunks": [
    "His confidence",
    "grew",
    "over time",
    "while working on different group projects at school"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "grew",
    "His confidence",
    "while working on different group projects at school",
    "over time"
  ],
  "target_word": "over time",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The old wooden fence started to fade and rust over time."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The old wooden fence started to fade and rust over time.",
  "chunks": [
    "The old wooden fence",
    "started",
    "to fade and rust over time"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "started",
    "to fade and rust over time",
    "The old wooden fence"
  ],
  "target_word": "over time",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14473, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "His confidence grew over time while working on different group projects at school."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "His confidence grew over time while working on different group projects at school.",
  "chunks": [
    "His confidence",
    "grew",
    "over time",
    "while working on different group projects at school"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "grew",
    "His confidence",
    "while working on different group projects at school",
    "over time"
  ],
  "target_word": "over time",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The old wooden fence started to fade and rust over time."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The old wooden fence started to fade and rust over time.",
  "chunks": [
    "The old wooden fence",
    "started",
    "to fade and rust over time"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "started",
    "to fade and rust over time",
    "The old wooden fence"
  ],
  "target_word": "over time",
  "chunk_count": 3
}
```

---

## sense 15150, level 1

#### Pack A
### Level 1 (sense 15150, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "ipa": "/ˌpɒliˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "polyphonic",
    "polychronic",
    "polytonic",
    "polychromic"
  ],
  "correct_answer": "polychronic",
  "explanation": "This is the target word, correctly matching what was heard: /ˌpɒliˈkrɒnɪk/.",
  "distractor_explanations": {
    "polychromic": "minimal pair: differs only in the middle consonant sound (/m/ vs /k/), easily confused by ear.",
    "polyphonic": "rhymes with the target and shares the 'poly-' prefix, but the middle syllable sound ('phon' vs 'chron') differs and could be misheard.",
    "polytonic": "same syllable count and stress pattern as the target, differing only in the 'ton' vs 'chron' sound, making it easy to mistake for polychronic."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 15150, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "ipa": "/ˌpɒliˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "polyphonic",
    "polychronic",
    "polytonic",
    "polychromic"
  ],
  "correct_answer": "polychronic",
  "explanation": "This is the target word, correctly matching what was heard: /ˌpɒliˈkrɒnɪk/.",
  "distractor_explanations": {
    "polychromic": "minimal pair: differs only in the middle consonant sound (/m/ vs /k/), easily confused by ear.",
    "polyphonic": "rhymes with the target and shares the 'poly-' prefix, but the middle syllable sound ('phon' vs 'chron') differs and could be misheard.",
    "polytonic": "same syllable count and stress pattern as the target, differing only in the 'ton' vs 'chron' sound, making it easy to mistake for polychronic."
  },
  "distractor_source": "llm"
}
```

---

## sense 15150, level 2

#### Pack A
### Level 2 (sense 15150, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "correct_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "options": [
    "A helpful person or thing makes it easier to do something.",
    "The lowest part or foundation of something, on which it rests or is built.",
    "Describing a way of doing several things at once, not following a strict schedule.",
    "To make an attempt to do or achieve something."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The process of bringing new employees into an organization.",
        "Let something go.",
        "Describing a way of doing several things at once, not following a strict schedule.",
        "A neighbor is someone who lives in a house or apartment close to your own home."
      ],
      "correct_answer": "Describing a way of doing several things at once, not following a strict schedule."
    }
  }
}
```

#### Pack B
### Level 2 (sense 15150, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "correct_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "options": [
    "A helpful person or thing makes it easier to do something.",
    "The lowest part or foundation of something, on which it rests or is built.",
    "Describing a way of doing several things at once, not following a strict schedule.",
    "To make an attempt to do or achieve something."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The process of bringing new employees into an organization.",
        "Let something go.",
        "Describing a way of doing several things at once, not following a strict schedule.",
        "A neighbor is someone who lives in a house or apartment close to your own home."
      ],
      "correct_answer": "Describing a way of doing several things at once, not following a strict schedule."
    }
  }
}
```

---

## sense 15150, level 3

#### Pack A
### Level 3 (sense 15150, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Conversely, numerous ___ cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "original_sentence": "Conversely, numerous polychronic cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "correct_answer": "polychronic",
  "options": [
    "polychronic",
    "chronological",
    "linguistic",
    "monochronic"
  ],
  "explanation": "Correct: matches the exact word used in the sentence describing cultures with a fluid, multi-tasking approach to time.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Is it better to be monochronic or ___ when managing a busy team?",
  "original_sentence": "Is it better to be monochronic or polychronic when managing a busy team?",
  "correct_answer": "polychronic",
  "options": [
    "punctual",
    "chronological",
    "monotonous",
    "polychronic"
  ],
  "explanation": "Correct: fits the contrast with 'monochronic' about handling multiple tasks without strict scheduling.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```

#### Pack B
### Level 3 (sense 15150, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Conversely, numerous ___ cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "original_sentence": "Conversely, numerous polychronic cultures, prevalent in parts of Latin America, the Middle East, and Africa, embrace a more fluid and multi-layered approach to time.",
  "correct_answer": "polychronic",
  "options": [
    "polychronic",
    "chronological",
    "linguistic",
    "monochronic"
  ],
  "explanation": "Correct: matches the exact word used in the sentence describing cultures with a fluid, multi-tasking approach to time.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Is it better to be monochronic or ___ when managing a busy team?",
  "original_sentence": "Is it better to be monochronic or polychronic when managing a busy team?",
  "correct_answer": "polychronic",
  "options": [
    "punctual",
    "chronological",
    "monotonous",
    "polychronic"
  ],
  "explanation": "Correct: fits the contrast with 'monochronic' about handling multiple tasks without strict scheduling.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```

---

## sense 15150, level 4

#### Pack A
### Level 4 (sense 15150, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She has always been a ___ person who prefers to juggle multiple projects at the same time.",
  "original_sentence": "She has always been a polychronic person who prefers to juggle multiple projects at the same time.",
  "target_word": "polychronic",
  "word": "polychronic",
  "answer": {
    "accepted": [
      "polychronic",
      "polychronically",
      "polychronicity"
    ],
    "accepted_normalized": [
      "polychronic",
      "polychronically",
      "polychronicity"
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
  "stem": "polychronic",
  "sentence_with_blank": "She has always been a ___ person who prefers to juggle multiple projects at the same time.",
  "original_sentence": "She has always been a polychronic person who prefers to juggle multiple projects at the same time.",
  "required_pos": "adjective",
  "options": [
    "polychronicive",
    "polychronic",
    "polychronical",
    "polychronicous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective correctly describing the person's multitasking style"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Their team became much more ___ after they started sharing responsibilities.",
  "original_sentence": "Their team became much more polychronic after they started sharing responsibilities.",
  "target_word": "polychronic",
  "word": "polychronic",
  "answer": {
    "accepted": [
      "polychronic",
      "polychronically",
      "polychronicity"
    ],
    "accepted_normalized": [
      "polychronic",
      "polychronically",
      "polychronicity"
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
  "stem": "polychronic",
  "sentence_with_blank": "Their team became much more ___ after they started sharing responsibilities.",
  "original_sentence": "Their team became much more polychronic after they started sharing responsibilities.",
  "required_pos": "adjective",
  "options": [
    "polychronicous",
    "polychronific",
    "polychronic",
    "polychronical"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective form correctly describing the team's way of working"
    }
  }
}
```

#### Pack B
### Level 4 (sense 15150, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She has always been a ___ person who prefers to juggle multiple projects at the same time.",
  "original_sentence": "She has always been a polychronic person who prefers to juggle multiple projects at the same time.",
  "target_word": "polychronic",
  "word": "polychronic",
  "answer": {
    "accepted": [
      "polychronic",
      "polychronically",
      "polychronicity"
    ],
    "accepted_normalized": [
      "polychronic",
      "polychronically",
      "polychronicity"
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
  "stem": "polychronic",
  "sentence_with_blank": "She has always been a ___ person who prefers to juggle multiple projects at the same time.",
  "original_sentence": "She has always been a polychronic person who prefers to juggle multiple projects at the same time.",
  "required_pos": "adjective",
  "options": [
    "polychronicive",
    "polychronic",
    "polychronical",
    "polychronicous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective correctly describing the person's multitasking style"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Their team became much more ___ after they started sharing responsibilities.",
  "original_sentence": "Their team became much more polychronic after they started sharing responsibilities.",
  "target_word": "polychronic",
  "word": "polychronic",
  "answer": {
    "accepted": [
      "polychronic",
      "polychronically",
      "polychronicity"
    ],
    "accepted_normalized": [
      "polychronic",
      "polychronically",
      "polychronicity"
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
  "stem": "polychronic",
  "sentence_with_blank": "Their team became much more ___ after they started sharing responsibilities.",
  "original_sentence": "Their team became much more polychronic after they started sharing responsibilities.",
  "required_pos": "adjective",
  "options": [
    "polychronicous",
    "polychronific",
    "polychronic",
    "polychronical"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base adjective form correctly describing the team's way of working"
    }
  }
}
```

---

## sense 15150, level 6

#### Pack A
### Level 6 (sense 15150, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students often find that a polychronic approach helps them balance homework and social activities.",
      "is_correct": true
    },
    {
      "text": "The doctor recommended a polychronic diet to lower cholesterol.",
      "is_correct": false
    },
    {
      "text": "The polychronic paint dried within minutes, leaving a smooth surface.",
      "is_correct": false
    },
    {
      "text": "Her polychronic smile lit up the room.",
      "is_correct": false
    }
  ],
  "explanation": "Misuse: 'polychronic' describes multitasking behavior, not a property of paint or drying time. Misuse: a smile cannot be 'polychronic'; the word doesn't apply to facial expressions or emotions. Misuse: 'polychronic' relates to handling multiple tasks/time, not to dietary or health recommendations.",
  "target_word": "polychronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She painted the wall a bright polychronic color.",
      "is_correct": false
    },
    {
      "text": "The clock ticked in a slow, polychronic rhythm.",
      "is_correct": false
    },
    {
      "text": "They explained how polychronic societies view deadlines as flexible guidelines rather than strict rules.",
      "is_correct": true
    },
    {
      "text": "The polychronic recipe called for exactly one cup of flour.",
      "is_correct": false
    }
  ],
  "explanation": "A recipe with a precise measurement is about exactness, not about handling multiple tasks loosely at once. This misuses the word for a color concept; 'polychronic' concerns time management, not visual hues. A single steady rhythm describes one repeated action, which contradicts the idea of juggling several things simultaneously.",
  "target_word": "polychronic"
}
```

#### Pack B
### Level 6 (sense 15150, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Students often find that a polychronic approach helps them balance homework and social activities.",
      "is_correct": true
    },
    {
      "text": "The doctor recommended a polychronic diet to lower cholesterol.",
      "is_correct": false
    },
    {
      "text": "The polychronic paint dried within minutes, leaving a smooth surface.",
      "is_correct": false
    },
    {
      "text": "Her polychronic smile lit up the room.",
      "is_correct": false
    }
  ],
  "explanation": "Misuse: 'polychronic' describes multitasking behavior, not a property of paint or drying time. Misuse: a smile cannot be 'polychronic'; the word doesn't apply to facial expressions or emotions. Misuse: 'polychronic' relates to handling multiple tasks/time, not to dietary or health recommendations.",
  "target_word": "polychronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She painted the wall a bright polychronic color.",
      "is_correct": false
    },
    {
      "text": "The clock ticked in a slow, polychronic rhythm.",
      "is_correct": false
    },
    {
      "text": "They explained how polychronic societies view deadlines as flexible guidelines rather than strict rules.",
      "is_correct": true
    },
    {
      "text": "The polychronic recipe called for exactly one cup of flour.",
      "is_correct": false
    }
  ],
  "explanation": "A recipe with a precise measurement is about exactness, not about handling multiple tasks loosely at once. This misuses the word for a color concept; 'polychronic' concerns time management, not visual hues. A single steady rhythm describes one repeated action, which contradicts the idea of juggling several things simultaneously.",
  "target_word": "polychronic"
}
```

---

## sense 15150, level 9

#### Pack A
### Level 9 (sense 15150, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many modern workplaces are becoming more polychronic to encourage teamwork and flexibility."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many modern workplaces are becoming more polychronic to encourage teamwork and flexibility.",
  "chunks": [
    "Many modern workplaces",
    "are becoming",
    "more polychronic",
    "to encourage teamwork and flexibility"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "are becoming",
    "Many modern workplaces",
    "more polychronic",
    "to encourage teamwork and flexibility"
  ],
  "target_word": "polychronic",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Students often find that a polychronic approach helps them balance homework and social activities."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Students often find that a polychronic approach helps them balance homework and social activities.",
  "chunks": [
    "Students",
    "often",
    "find",
    "that a polychronic approach helps them balance homework and social activities"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "find",
    "often",
    "Students",
    "that a polychronic approach helps them balance homework and social activities"
  ],
  "target_word": "polychronic",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 15150, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many modern workplaces are becoming more polychronic to encourage teamwork and flexibility."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many modern workplaces are becoming more polychronic to encourage teamwork and flexibility.",
  "chunks": [
    "Many modern workplaces",
    "are becoming",
    "more polychronic",
    "to encourage teamwork and flexibility"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "are becoming",
    "Many modern workplaces",
    "more polychronic",
    "to encourage teamwork and flexibility"
  ],
  "target_word": "polychronic",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Students often find that a polychronic approach helps them balance homework and social activities."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Students often find that a polychronic approach helps them balance homework and social activities.",
  "chunks": [
    "Students",
    "often",
    "find",
    "that a polychronic approach helps them balance homework and social activities"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "find",
    "often",
    "Students",
    "that a polychronic approach helps them balance homework and social activities"
  ],
  "target_word": "polychronic",
  "chunk_count": 4
}
```

---
