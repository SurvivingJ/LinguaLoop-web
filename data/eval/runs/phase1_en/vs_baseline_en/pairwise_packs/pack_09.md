# Pairwise review pack 09

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


## sense 14390, level 6

#### Pack A
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Enormously talented young musicians performed at the annual youth festival last weekend.",
      "is_correct": true
    },
    {
      "text": "She enormously agreed with the plan before leaving early.",
      "is_correct": false
    },
    {
      "text": "He arrived enormously on time for the meeting.",
      "is_correct": false
    },
    {
      "text": "The tiny kitten was enormously small, hiding behind the cushion.",
      "is_correct": false
    }
  ],
  "explanation": "Contradictory: 'enormously' signals a very great degree, which conflicts logically with 'small'. Pragmatically odd: 'agree' is a binary, non-gradable action, so it cannot be intensified by a degree adverb like 'enormously'. Pragmatically odd: 'on time' is not a gradable state, so modifying it with 'enormously' doesn't make sensible use of the degree meaning.",
  "target_word": "Enormously"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The number seven is enormously prime.",
      "is_correct": false
    },
    {
      "text": "People rely enormously on digital maps nowadays to find their way around unfamiliar cities.",
      "is_correct": true
    },
    {
      "text": "The battery was enormously dead by the next morning.",
      "is_correct": false
    },
    {
      "text": "He nodded enormously to confirm he understood the question.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'prime' is an absolute, binary property with no scale of degree, so it cannot logically be intensified by 'enormously'. semantic: 'dead' is an absolute state without gradations, making the degree adverb 'enormously' pragmatically inappropriate here. collocational: nodding is a small, discrete gesture, so pairing it with a large-degree adverb like 'enormously' creates an odd mismatch in scale.",
  "target_word": "enormously"
}
```

#### Pack B
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The enormously silent room was filled with loud music.",
      "is_correct": false
    },
    {
      "text": "Technology has changed our daily lives enormously since we were kids.",
      "is_correct": true
    },
    {
      "text": "He enormously forgot to buy milk at the grocery store yesterday.",
      "is_correct": false
    },
    {
      "text": "She enormously walked to the corner store to get some bread.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Enormously' modifies degree or extent, but 'forgetting' is a punctual, binary cognitive event that cannot logically be done to a 'great degree'. Semantically inappropriate: 'Enormously silent' is an oxymoron when immediately followed by 'filled with loud music', creating a direct logical contradiction in the same clause. Collocationally inappropriate: 'Walked' is a simple physical activity. While one can walk 'quickly' or 'far', one cannot walk 'enormously', as the adverb does not naturally collocate with the physical act of walking in this manner.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 9

#### Pack A
### Level 9 (sense 14390, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Traffic congestion in the city center increases enormously during the evening rush hour.",
  "chunks": [
    "Traffic congestion in the city center",
    "increases",
    "enormously",
    "during the evening rush hour"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "increases",
    "during the evening rush hour",
    "enormously",
    "Traffic congestion in the city center"
  ],
  "target_word": "enormously",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Enormously talented young musicians performed at the annual youth festival last weekend.",
  "chunks": [
    "Enormously talented young musicians",
    "performed",
    "at the annual youth festival",
    "last weekend"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "last weekend",
    "Enormously talented young musicians",
    "at the annual youth festival",
    "performed"
  ],
  "target_word": "Enormously",
  "chunk_count": 4
}
```

#### Pack B
### Level 9 (sense 14390, difficulty None)
**jumbled_sentence** variant `A`, tier `3`
```json
{
  "original_sentence": "The small town has changed enormously since the new factory opened."
}
```
**jumbled_sentence** variant `A`, tier `3`
```json
{
  "schema_version": 2,
  "original_sentence": "The small town has changed enormously since the new factory opened.",
  "chunks": [
    "The small town",
    "has changed",
    "enormously",
    "since the new factory opened"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "has changed",
    "since the new factory opened",
    "enormously",
    "The small town"
  ],
  "target_word": "enormously",
  "chunk_count": 4
}
```
**jumbled_sentence** variant `B`, tier `3`
```json
{
  "original_sentence": "Technology has changed our daily lives enormously since we were kids."
}
```
**jumbled_sentence** variant `B`, tier `3`
```json
{
  "schema_version": 2,
  "original_sentence": "Technology has changed our daily lives enormously since we were kids.",
  "chunks": [
    "Technology",
    "has changed",
    "our daily lives",
    "enormously",
    "since we were kids"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "Technology",
    "enormously",
    "our daily lives",
    "since we were kids",
    "has changed"
  ],
  "target_word": "enormously",
  "chunk_count": 5
}
```

---

## sense 14473, level 2

#### Pack A
### Level 2 (sense 14473, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "over time",
  "pronunciation": "oh-ver tahym",
  "correct_definition": "Gradually, as time goes by.",
  "options": [
    "A small building, often made of wood, used for storing things.",
    "Primary means first in order or importance.",
    "The total number of people living in a particular area, city, country, etc.",
    "Gradually, as time goes by."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "over time",
  "pronunciation": "oh-ver tahym",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Tell someone something.",
        "A part of a company's profit that is paid to shareholders.",
        "Gradually, as time goes by.",
        "To match means to be similar or to go together with something else."
      ],
      "correct_answer": "Gradually, as time goes by."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14473, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "correct_definition": "Gradually, as time goes by.",
  "options": [
    "A person who visits a place or person.",
    "Gradually, as time goes by.",
    "Coming next after the eighth in a series.",
    "Diversity is the state of having a variety of different elements, such as cultures, backgrounds, or types."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "pronunciation": "oh-ver tahym",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Cotton is a natural fiber harvested from the cotton plant, used to make textiles and other products.",
        "Something that can be broken down by nature.",
        "Gradually, as time goes by.",
        "The state of being unknown or not identified by name."
      ],
      "correct_answer": "Gradually, as time goes by."
    }
  }
}
```

---

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
  "sentence_with_blank": "Over time, it got better.",
  "original_sentence": "Over time, it got better.",
  "correct_answer": "Over time",
  "options": [
    "Inside",
    "Over time",
    "Loudly",
    "Simultaneously"
  ],
  "explanation": "Correct adverbial phrase indicating gradual change, fitting the context of gradual improvement.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The heavy rain eroded the soil ___.",
  "original_sentence": "The heavy rain eroded the soil over time.",
  "correct_answer": "over time",
  "options": [
    "over time",
    "upwards",
    "accidentally",
    "posthaste"
  ],
  "explanation": "Correct: fits the context of a gradual, long-term physical process.",
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
  "sentence_with_blank": "Languages can change significantly ___.",
  "original_sentence": "Languages can change significantly over time.",
  "target_word": "over time",
  "word": "over time",
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
  "sentence_with_blank": "Memories can fade ___.",
  "original_sentence": "Memories can fade over time.",
  "target_word": "over time",
  "word": "over time",
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
      "text": "You will see improvement over time if you practice daily.",
      "is_correct": true
    },
    {
      "text": "The glass shattered over time when it hit the floor.",
      "is_correct": false
    },
    {
      "text": "The number three became the number four over time.",
      "is_correct": false
    },
    {
      "text": "The fire ignited over time as soon as the match was struck.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'shattered' describes an instantaneous, punctual event, which contradicts the gradual, durative meaning of 'over time'. Semantically inappropriate: numbers are immutable mathematical concepts and cannot change their value gradually or at all. Pragmatically inappropriate: 'ignited' is a sudden, instantaneous action, making it incompatible with the gradual progression implied by 'over time'.",
  "target_word": "over time"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Water boils at exactly one hundred degrees Celsius over time.",
      "is_correct": false
    },
    {
      "text": "She blinked over time to clear her vision.",
      "is_correct": false
    },
    {
      "text": "Skills are developed over time with patience and hard work.",
      "is_correct": true
    },
    {
      "text": "The window shattered over time when the baseball hit it.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: shattering is an instantaneous event, which contradicts the gradual, cumulative nature of 'over time'. semantic: scientific constants do not change gradually, making a temporal shift adverb logically inappropriate here. pragmatic: blinking is a rapid, repetitive physical action, not a gradual developmental process that occurs 'over time'.",
  "target_word": "over time"
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
  "original_sentence": "Friendships often deepen over time through shared experiences."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Friendships often deepen over time through shared experiences.",
  "chunks": [
    "Friendships",
    "often",
    "deepen",
    "over time",
    "through shared experiences"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "over time",
    "through shared experiences",
    "often",
    "Friendships",
    "deepen"
  ],
  "target_word": "over time",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "You will see improvement over time if you practice daily."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "You will see improvement over time if you practice daily.",
  "chunks": [
    "You will see",
    "improvement",
    "over time",
    "if you practice daily"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "improvement",
    "over time",
    "if you practice daily",
    "You will see"
  ],
  "target_word": "over time",
  "chunk_count": 4
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
    "polytechnic",
    "polyphonic",
    "polyclinic",
    "polychronic"
  ],
  "correct_answer": "polychronic",
  "explanation": "Correct word.",
  "distractor_explanations": {
    "polytechnic": "Shares the same stress pattern and initial syllables, but differs in the middle consonant cluster (/t/ vs /kr/).",
    "polyphonic": "Minimal pair: differs only in the consonant cluster /f/ vs /kr/.",
    "polyclinic": "Minimal pair: differs in the consonant cluster /kl/ vs /kr/."
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
    "Describing a way of doing several things at once, not following a strict schedule.",
    "A degree is a unit used to measure temperature, angles, or the level of something like an academic qualification.",
    "To bring something into existence, to cause something to happen or exist.",
    "The process of designing and regulating the use of land and infrastructure in cities and towns."
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
        "To completely change something, especially a system or way of doing things, so that it works much better.",
        "To design or change something so that it fits someone's individual needs or preferences.",
        "Describing a way of doing several things at once, not following a strict schedule.",
        "Something that you can understand."
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
    "informal",
    "polychronic",
    "chronological",
    "concurrent"
  ],
  "explanation": "Correct word.",
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
