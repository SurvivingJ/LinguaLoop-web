# Pairwise review pack 08

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


## sense 14100, level 9

#### Pack A
### Level 9 (sense 14100, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Smoke started to ascend from the chimney in a thin, grey line."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Smoke started to ascend from the chimney in a thin, grey line.",
  "chunks": [
    "Smoke",
    "started",
    "to ascend from the chimney in a thin grey line"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to ascend from the chimney in a thin grey line",
    "started",
    "Smoke"
  ],
  "target_word": "ascend",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "We watched the hot air balloon slowly ascend into the morning sky."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "We watched the hot air balloon slowly ascend into the morning sky.",
  "chunks": [
    "We",
    "watched",
    "the hot air balloon slowly ascend into the morning sky"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "We",
    "the hot air balloon slowly ascend into the morning sky",
    "watched"
  ],
  "target_word": "ascend",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14100, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Smoke started to ascend from the campfire as the logs caught fire."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Smoke started to ascend from the campfire as the logs caught fire.",
  "chunks": [
    "Smoke",
    "started",
    "to ascend from the campfire as the logs caught fire"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "to ascend from the campfire as the logs caught fire",
    "started",
    "Smoke"
  ],
  "target_word": "ascend",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The hikers began to ascend the steep mountain trail early in the morning before the sun got too hot."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The hikers began to ascend the steep mountain trail early in the morning before the sun got too hot.",
  "chunks": [
    "The hikers",
    "began",
    "to ascend the steep mountain trail early in the morning before the sun got too hot"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "The hikers",
    "to ascend the steep mountain trail early in the morning before the sun got too hot",
    "began"
  ],
  "target_word": "ascend",
  "chunk_count": 3
}
```

---

## sense 14189, level 1

#### Pack A
### Level 1 (sense 14189, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "ipa": "/ˌtɛknəˈlɒdʒɪkəli/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "technologically",
    "chronologically",
    "theologically",
    "mythologically"
  ],
  "correct_answer": "technologically",
  "explanation": "correct: this is the target word spoken aloud",
  "distractor_explanations": {
    "chronologically": "near-minimal pair: differs only in the initial consonant cluster /kr/ versus /t/ and the following vowel sound",
    "theologically": "same-stress same-syllable-count rhyme: shares the exact rhythm and final four syllables, differing only in the initial consonant",
    "mythologically": "same-stress same-syllable-count rhyme: shares the exact rhythm and final four syllables, differing only in the initial consonant"
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14189, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "ipa": "/ˌtɛknəˈlɒdʒɪkəli/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "theologically",
    "technologically",
    "biologically",
    "chronologically"
  ],
  "correct_answer": "technologically",
  "explanation": "This is the target word exactly as pronounced, with primary stress on the syllable 'nol' and full ending '-ically'.",
  "distractor_explanations": {
    "theologically": "rhyme: shares the same '-ologically' ending and stress pattern, but the root differs (theology vs. technology).",
    "chronologically": "rhyme: same suffix and syllable count, easily confused by ear despite a different root meaning 'time-related'.",
    "biologically": "rhyme: matches the '-ologically' sound pattern and rhythm, but refers to biology, not technology."
  },
  "distractor_source": "llm"
}
```

---

## sense 14189, level 2

#### Pack A
### Level 2 (sense 14189, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "correct_definition": "in a way that relates to technology or using machines and equipment",
  "options": [
    "Dedication is the quality of being committed to a task or purpose.",
    "To communicate a thought, feeling, or opinion through words, actions, or art.",
    "The lower extremity of the leg below the ankle, on which a person stands or walks.",
    "in a way that relates to technology or using machines and equipment"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "in a way that relates to technology or using machines and equipment",
        "To make or create something using skill and effort.",
        "Steering is when you move the wheel in a car to make it go left or right.",
        "Relating to the way something is made from different parts or elements."
      ],
      "correct_answer": "in a way that relates to technology or using machines and equipment"
    }
  }
}
```

#### Pack B
### Level 2 (sense 14189, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "correct_definition": "in a way that relates to technology or using machines and equipment.",
  "options": [
    "Forming the basis or starting point for something; basic and important.",
    "in a way that relates to technology or using machines and equipment.",
    "Showing cleverness and skill, especially in solving problems or creating new things.",
    "Inhabited by people or animals."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "pronunciation": "tek-nuh-loj-i-kuh-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "in a way that relates to technology or using machines and equipment.",
        "To get something by paying money for it.",
        "A group that makes rules for airplanes.",
        "To fall or fall down suddenly, often with a loud sound, or to fail or break down suddenly."
      ],
      "correct_answer": "in a way that relates to technology or using machines and equipment."
    }
  }
}
```

---

## sense 14189, level 3

#### Pack A
### Level 3 (sense 14189, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "However, the industry is increasingly seeing a shift towards more consolidated and ___ advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "original_sentence": "However, the industry is increasingly seeing a shift towards more consolidated and technologically advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "correct_answer": "technologically",
  "options": [
    "technologically",
    "financially",
    "geographically",
    "emotionally"
  ],
  "explanation": "Correct: matches the context of advanced machinery and equipment in agricultural operations.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The museum created a ___ immersive experience for all visitors.",
  "original_sentence": "The museum created a technologically immersive experience for all visitors.",
  "correct_answer": "technologically",
  "options": [
    "formally",
    "financially",
    "nutritionally",
    "technologically"
  ],
  "explanation": "Correct: describes an experience made immersive through technology, matching the museum context.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment.",
  "target_word": "technologically"
}
```

#### Pack B
### Level 3 (sense 14189, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "However, the industry is increasingly seeing a shift towards more consolidated and ___ advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "original_sentence": "However, the industry is increasingly seeing a shift towards more consolidated and technologically advanced agricultural operations, especially in larger estates, aiming for increased efficiency and yield.",
  "correct_answer": "technologically",
  "options": [
    "technologically",
    "ecologically",
    "psychologically",
    "bureaucratically"
  ],
  "explanation": "correct: fits the context of using machines and equipment for increased agricultural efficiency",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment",
  "target_word": "technologically"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Some traditional industries have struggled because they have not evolved ___ over the past decade.",
  "original_sentence": "Some traditional industries have struggled because they have not evolved technologically over the past decade.",
  "correct_answer": "technologically",
  "options": [
    "technologically",
    "retroactively",
    "biologically",
    "chronologically"
  ],
  "explanation": "Correct: fits the context of industries advancing through the use of machines and equipment.",
  "distractor_tags": {},
  "word_definition": "in a way that relates to technology or using machines and equipment",
  "target_word": "technologically"
}
```

---

## sense 14189, level 4

#### Pack A
### Level 4 (sense 14189, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "stem": "technology",
  "sentence_with_blank": "Our school has become much more ___ equipped over the past two years.",
  "original_sentence": "Our school has become much more technologically equipped over the past two years.",
  "required_pos": "adverb",
  "options": [
    "technologial",
    "technologicness",
    "technologically",
    "technologyment"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way that relates to technology'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist"
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
  "stem": "technology",
  "sentence_with_blank": "She wondered how the ancient builders managed such feats without being ___ advanced.",
  "original_sentence": "She wondered how the ancient builders managed such feats without being technologically advanced.",
  "required_pos": "adverb",
  "options": [
    "technologically",
    "technologal",
    "technologment",
    "technologful"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established adverb meaning 'in a way related to technology'"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14189, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The company is planning to become ___ independent by developing its own software and hardware components.",
  "original_sentence": "The company is planning to become technologically independent by developing its own software and hardware components.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist",
      "technologists"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist",
      "technologists"
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
  "sentence_with_blank": "The museum created a ___ immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "original_sentence": "The museum created a technologically immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "target_word": "technologically",
  "word": "technologically",
  "answer": {
    "accepted": [
      "technologically",
      "technology",
      "technological",
      "technologist",
      "technologists"
    ],
    "accepted_normalized": [
      "technologically",
      "technology",
      "technological",
      "technologist",
      "technologists"
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
  "stem": "technology",
  "sentence_with_blank": "The museum created a ___ immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "original_sentence": "The museum created a technologically immersive experience that lets visitors explore ancient ruins in virtual reality.",
  "required_pos": "adverb",
  "options": [
    "technologive",
    "technologation",
    "technologically",
    "technologer"
  ],
  "correct_answer": "technologically",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverbial derivation modifying the adjective"
    }
  }
}
```

---

## sense 14189, level 6

#### Pack A
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The ancient philosopher argued that the human soul is technologically pure and cannot be corrupted by physical desires.",
      "is_correct": false
    },
    {
      "text": "She tasted the soup and realized it was technologically too salty for her liking.",
      "is_correct": false
    },
    {
      "text": "Our school library has become much more technologically equipped since they installed dozens of modern computers.",
      "is_correct": true
    },
    {
      "text": "The emotional support dog was technologically comforting to the patient after the tragic accident.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'technologically' relates to machines and equipment, which is pragmatically inappropriate for describing the spiritual purity of a soul semantic: 'technologically' cannot modify sensory perception or the physical taste of food pragmatic: 'technologically' implies the use of machines, which contradicts the organic and emotional nature of a support dog",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "manually",
    "scientifically",
    "mechanically",
    "digitally"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment",
      "explanation": "in a way done by hand rather than by machines, directly opposing the sense of using technology or equipment"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She baked the cake technologically by mixing flour, sugar, and eggs in a wooden bowl with a spoon.",
      "is_correct": false
    },
    {
      "text": "Although the region was isolated, it was surprisingly well-connected technologically thanks to satellite internet.",
      "is_correct": true
    },
    {
      "text": "The emotional healing process between the two friends progressed technologically as they shared their deepest feelings.",
      "is_correct": false
    },
    {
      "text": "The ancient oak tree grew technologically over the centuries, developing deep roots and a wide canopy.",
      "is_correct": false
    }
  ],
  "explanation": "technologically is semantically inappropriate here because trees grow through biological processes, not through the application of machines or equipment. technologically is pragmatically inappropriate because mixing ingredients in a wooden bowl by hand describes a manual, non-technological process, creating a direct contradiction. technologically is semantically mismatched because emotional healing and sharing feelings are interpersonal, psychological processes, not ones driven by machines or technical equipment.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "scientifically",
    "mechanically",
    "digitally",
    "primitively"
  ],
  "correct_answer": "primitively",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment",
      "explanation": "antonym of the target sense: in a primitive, non-technological manner"
    }
  }
}
```

#### Pack B
### Level 6 (sense 14189, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The river flows technologically through the valley every spring.",
      "is_correct": false
    },
    {
      "text": "She smiled technologically at her friend across the room.",
      "is_correct": false
    },
    {
      "text": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
      "is_correct": true
    },
    {
      "text": "Technologically, the chef added more salt to balance the flavors of the dish.",
      "is_correct": false
    }
  ],
  "explanation": "Misuse: seasoning and cooking technique are unrelated to technology, so the adverb doesn't fit the action. Misuse: smiling is an emotional/physical expression, not something that can be described in terms of technology. Misuse: a river's natural flow is a geological/natural process, not related to technology or machinery.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "scientifically",
    "digitally",
    "electronically",
    "traditionally"
  ],
  "correct_answer": "traditionally",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: describes doing something in an old, established way without modern technology"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The weather turned technologically rainy overnight.",
      "is_correct": false
    },
    {
      "text": "The city aims to become more technologically efficient in managing public transport.",
      "is_correct": true
    },
    {
      "text": "She felt technologically sad after the funeral.",
      "is_correct": false
    },
    {
      "text": "The soup was technologically delicious, according to the chef.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: taste and flavor are not properties that can be described as technological. Semantically inappropriate: emotions like sadness are not related to technology or machinery. Semantically inappropriate: weather conditions are natural phenomena, not something that can be 'technological'.",
  "target_word": "technologically"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "technologically",
  "relation": "antonym",
  "options": [
    "digitally",
    "manually",
    "efficiently",
    "scientifically"
  ],
  "correct_answer": "manually",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "in a way that relates to technology or using machines and equipment.",
      "explanation": "antonym: done by hand without machines or technology"
    }
  }
}
```

---

## sense 14189, level 9

#### Pack A
### Level 9 (sense 14189, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many modern vehicles are now technologically capable of driving themselves in certain highway conditions."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many modern vehicles are now technologically capable of driving themselves in certain highway conditions.",
  "chunks": [
    "Many modern vehicles",
    "are",
    "now",
    "technologically capable of driving themselves in certain highway conditions"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "are",
    "technologically capable of driving themselves in certain highway conditions",
    "now",
    "Many modern vehicles"
  ],
  "target_word": "technologically",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Our school library has become much more technologically equipped since they installed dozens of modern computers."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Our school library has become much more technologically equipped since they installed dozens of modern computers.",
  "chunks": [
    "Our school library",
    "has become",
    "much more technologically equipped",
    "since they installed dozens of modern computers"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "since they installed dozens of modern computers",
    "much more technologically equipped",
    "Our school library",
    "has become"
  ],
  "target_word": "technologically",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14189, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Many teenagers today are technologically savvy and learn new software very quickly.",
  "chunks": [
    "Many teenagers",
    "today",
    "are",
    "technologically savvy",
    "and learn new software very quickly"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "today",
    "technologically savvy",
    "are",
    "Many teenagers",
    "and learn new software very quickly"
  ],
  "target_word": "technologically",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Technologically speaking, this new smartphone is a major upgrade from the previous model.",
  "chunks": [
    "Technologically speaking",
    "this new smartphone",
    "is",
    "a major upgrade from the previous model"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "a major upgrade from the previous model",
    "is",
    "Technologically speaking",
    "this new smartphone"
  ],
  "target_word": "technologically",
  "chunk_count": 4
}
```

---

## sense 14390, level 2

#### Pack A
### Level 2 (sense 14390, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "correct_definition": "To a very great degree or extent.",
  "options": [
    "A garage is a building or part of a building where a car or other vehicle is kept.",
    "To a very great degree or extent.",
    "All the people living together in a single residence.",
    "to become a member of a group or to go to someone so that you are together"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "pronunciation": "ee-NOR-mus-lee",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To a very great degree or extent.",
        "Involving three groups or parts.",
        "The state of being simple, not complicated.",
        "The ability to use your eyes and hands together in a coordinated way, especially for tasks like catching, throwing, or writing."
      ],
      "correct_answer": "To a very great degree or extent."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14390, difficulty None)
**definition_match** variant `A`, tier `3`
```json
{
  "word": "enormously",
  "pronunciation": "en-or-mus-lee",
  "correct_definition": "To a very great degree or extent.",
  "options": [
    "To a very great degree or extent.",
    "A difference or change in the amount or level of something.",
    "Scope refers to the extent of the area or subject matter that something deals with or to which it is relevant.",
    "A period of time during which there is no rain or very little rain, often causing problems for plants and animals."
  ]
}
```
**definition_match** variant `A`, tier `3`
```json
{
  "word": "enormously",
  "pronunciation": "en-or-mus-lee",
  "tier": "3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "To a very great degree or extent.",
        "the act of spreading information or ideas to many people.",
        "A place, building, or container where things are stored or kept.",
        "Something you know is true or will happen."
      ],
      "correct_answer": "To a very great degree or extent."
    }
  }
}
```

---

## sense 14390, level 3

#### Pack A
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "rarely",
    "enormously",
    "loudly"
  ],
  "explanation": "Correctly conveys that coffee preparation varies to a very great degree across cultures, matching the examples that follow.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He felt ___ relieved when he finally found his lost backpack on the school bus.",
  "original_sentence": "He felt enormously relieved when he finally found his lost backpack on the school bus.",
  "correct_answer": "enormously",
  "options": [
    "briefly",
    "hardly",
    "enormously",
    "rarely"
  ],
  "explanation": "Correctly conveys that he felt relieved to a very great degree after finding his lost backpack.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `A`, tier `3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "enormously",
    "secretly",
    "slightly",
    "rarely"
  ],
  "explanation": "Correct: 'Enormously' is the target adverb meaning 'to a very great degree', which perfectly modifies the verb 'varies' to show the vast extent of the differences.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `3`
```json
{
  "sentence_with_blank": "Students benefited ___ from the extra tutoring sessions before the exam.",
  "original_sentence": "Students benefited enormously from the extra tutoring sessions before the exam.",
  "correct_answer": "enormously",
  "options": [
    "enormously",
    "continuously",
    "accidentally",
    "loudly"
  ],
  "explanation": "correct: fits the context of gaining a very great degree of benefit from extra tutoring.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 4

#### Pack A
### Level 4 (sense 14390, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
  "stem": "enormous",
  "sentence_with_blank": "The price of modern technology has dropped ___ over the past decade, making smartphones accessible to teenagers everywhere.",
  "original_sentence": "The price of modern technology has dropped enormously over the past decade, making smartphones accessible to teenagers everywhere.",
  "required_pos": "adverb",
  "options": [
    "enormousity",
    "enormously",
    "enormousive",
    "enormousment"
  ],
  "correct_answer": "enormously",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard adverb formed by adding -ly to the adjective"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Interest in environmental clubs has risen ___ among students concerned about climate change.",
  "original_sentence": "Interest in environmental clubs has risen enormously among students concerned about climate change.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
### Level 4 (sense 14390, difficulty None)
**cloze_typed** variant `A`, tier `3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Her confidence grew ___ after she finished her first big art project.",
  "original_sentence": "Her confidence grew enormously after she finished her first big art project.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
**cloze_typed** variant `B`, tier `3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "The weather can affect your mood ___ during the winter months.",
  "original_sentence": "The weather can affect your mood enormously during the winter months.",
  "target_word": "enormously",
  "word": "enormously",
  "answer": {
    "accepted": [
      "enormously",
      "enormous",
      "enormity"
    ],
    "accepted_normalized": [
      "enormously",
      "enormous",
      "enormity"
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
