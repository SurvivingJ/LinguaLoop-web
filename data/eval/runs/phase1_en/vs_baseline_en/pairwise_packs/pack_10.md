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
  "sentence_with_blank": "Students who are ___ often prefer working on multiple assignments at the exact same time.",
  "original_sentence": "Students who are polychronic often prefer working on multiple assignments at the exact same time.",
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
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "They found it difficult to adapt because their coworkers preferred a flexible, ___ approach to managing daily tasks.",
  "original_sentence": "They found it difficult to adapt because their coworkers preferred a flexible, polychronic approach to managing daily tasks.",
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

---

## sense 15150, level 6

#### Pack A
### Level 6 (sense 15150, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The patient was diagnosed with a polychronic illness that affects multiple organs simultaneously.",
      "is_correct": false
    },
    {
      "text": "The polychronic painting displayed in the gallery featured a vibrant mix of red, blue, and yellow pigments.",
      "is_correct": false
    },
    {
      "text": "She realized her team was more polychronic after noticing how they handled several projects at once.",
      "is_correct": true
    },
    {
      "text": "Due to the polychronic climate of the region, it rains heavily in the morning and snows in the afternoon.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic error: 'polychronic' incorrectly describes physical colors instead of time management; the correct term for many colors is 'polychromatic'. Semantic error: 'polychronic' is inappropriately applied to a medical condition; it should describe human time orientation, not biological diseases. Semantic error: 'polychronic' incorrectly describes weather patterns; it is strictly used for human or cultural approaches to time and scheduling.",
  "target_word": "polychronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The polychronic mountain stood silently against the backdrop of the setting sun.",
      "is_correct": false
    },
    {
      "text": "Our teacher described our busy classroom as a vibrant, polychronic environment where many things happened at once.",
      "is_correct": true
    },
    {
      "text": "She bought a polychronic toaster that perfectly browned her bread in exactly two minutes.",
      "is_correct": false
    },
    {
      "text": "The polychronic flavor of the soup was a perfect blend of spicy, sweet, and sour notes.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: inanimate natural objects cannot possess cultural or behavioral approaches to time management. pragmatic: mechanical kitchen appliances operate on strict, linear timers, making 'polychronic' an inappropriate descriptor. semantic: the word applies to time management and cultural habits, not sensory experiences like taste.",
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
  "original_sentence": "Are you feeling polychronic today, or would you rather focus on just one single task?"
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Are you feeling polychronic today, or would you rather focus on just one single task?",
  "chunks": [
    "Are feeling",
    "you",
    "polychronic",
    "today",
    "or would you rather focus on just one single task"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "you",
    "polychronic",
    "or would you rather focus on just one single task",
    "Are feeling",
    "today"
  ],
  "target_word": "polychronic",
  "chunk_count": 5
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "She realized her team was more polychronic after noticing how they handled several projects at once."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "She realized her team was more polychronic after noticing how they handled several projects at once.",
  "chunks": [
    "She",
    "realized",
    "her team was more polychronic after noticing how they handled several projects at once"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "her team was more polychronic after noticing how they handled several projects at once",
    "She",
    "realized"
  ],
  "target_word": "polychronic",
  "chunk_count": 3
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

## sense 15216, level 1

#### Pack A
### Level 1 (sense 15216, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "ipa": "/ˌmɒnəˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "monogenic",
    "monochromic",
    "monotonic",
    "monochronic"
  ],
  "correct_answer": "monochronic",
  "explanation": "This is the target word exactly as it is spoken and spelled.",
  "distractor_explanations": {
    "monochromic": "Near-homophone: shares 'mono-' and the final '-ic', differing only in the middle consonant (/n/ vs /m/) and vowel, easily confused by ear.",
    "monotonic": "Minimal pair: same stress pattern and syllable count, but the middle syllable 'ton' replaces 'chron', making it sound very similar when spoken quickly.",
    "monogenic": "Rhyming distractor: matches the 'mono-...-ic' shape and rhythm, but the middle syllable 'gen' differs from 'chron', creating a plausible mishearing."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 15216, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mon-uh-KRON-ik",
  "ipa": "/ˌmɒnəˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "monochromic",
    "monoclinic",
    "monotonic",
    "monochronic"
  ],
  "correct_answer": "monochronic",
  "explanation": "Correct answer: the exact target word.",
  "distractor_explanations": {
    "monochromic": "near-homophone: differs only in the vowel sound of the stressed syllable (/ɒ/ vs /əʊ/).",
    "monotonic": "rhyme: same stress and syllable count, but the stressed consonant cluster is /t/ instead of /kr/.",
    "monoclinic": "rhyme: same stress and syllable count, but the stressed consonant cluster is /kl/ instead of /kr/."
  },
  "distractor_source": "llm"
}
```

---

## sense 15216, level 2

#### Pack A
### Level 2 (sense 15216, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mon-uh-KRON-ik",
  "correct_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "options": [
    "Accountable means being responsible for your actions and expected to explain them when asked.",
    "Characterized by constant change, activity, or progress.",
    "The act of controlling and making use of something, especially a natural resource or power.",
    "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mon-uh-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A product or raw material that can be bought and sold.",
        "a specific historical period of 100 years, often used to denote a particular era.",
        "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
        "The ability of something to be pressed into a smaller size."
      ],
      "correct_answer": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
    }
  }
}
```

#### Pack B
### Level 2 (sense 15216, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "correct_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "options": [
    "Relating to or using electricity; powered by electricity.",
    "A wave is a raised line of water that moves across the surface of the sea or a lake.",
    "Shared or used by members of a group or community.",
    "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "The power to affect how someone or something develops, behaves, or thinks.",
        "A strong desire to know or learn something new.",
        "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
        "A written record of events in the order they happened."
      ],
      "correct_answer": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule."
    }
  }
}
```

---

## sense 15216, level 3

#### Pack A
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Being ___ means that interrupting a scheduled activity can cause unnecessary stress.",
  "original_sentence": "Being monochronic means that interrupting a scheduled activity can cause unnecessary stress.",
  "correct_answer": "monochronic",
  "options": [
    "scheduled",
    "monochronic",
    "monotonous",
    "polychronic"
  ],
  "explanation": "Correct: this matches the sentence's meaning of focusing on one scheduled activity at a time.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```

#### Pack B
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "People in ___ cultures usually prefer to focus on one single task at a time.",
  "original_sentence": "People in monochronic cultures usually prefer to focus on one single task at a time.",
  "correct_answer": "monochronic",
  "options": [
    "synchronous",
    "monochronic",
    "punctual",
    "chronological"
  ],
  "explanation": "Correct answer: fits the context of a cultural preference for single-tasking.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "My friend is so ___ that she always completes her homework before starting any leisure activities.",
  "original_sentence": "My friend is so monochronic that she always completes her homework before starting any leisure activities.",
  "correct_answer": "monochronic",
  "options": [
    "spontaneous",
    "ongoing",
    "chronological",
    "monochronic"
  ],
  "explanation": "Correct answer: fits the context of focusing on one task at a time before moving to the next.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```

---

## sense 15216, level 4

#### Pack A
### Level 4 (sense 15216, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She is a very ___ person who relies heavily on her daily planner.",
  "original_sentence": "She is a very monochronic person who relies heavily on her daily planner.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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
  "sentence_with_blank": "Our teacher explained why some societies are traditionally viewed as ___.",
  "original_sentence": "Our teacher explained why some societies are traditionally viewed as monochronic.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically"
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
### Level 4 (sense 15216, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "She found it difficult to adapt to a ___ schedule when she started her new job.",
  "original_sentence": "She found it difficult to adapt to a monochronic schedule when she started her new job.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically",
      "monochronicity"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically",
      "monochronicity"
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
  "sentence_with_blank": "While working on the group presentation, we realized our communication styles were less ___ than expected.",
  "original_sentence": "While working on the group presentation, we realized our communication styles were less monochronic than expected.",
  "target_word": "monochronic",
  "word": "monochronic",
  "answer": {
    "accepted": [
      "monochronic",
      "monochronically",
      "monochronicity"
    ],
    "accepted_normalized": [
      "monochronic",
      "monochronically",
      "monochronicity"
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

## sense 15216, level 6

#### Pack A
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The artist used a monochronic palette of only blue and white shades to paint the landscape.",
      "is_correct": false
    },
    {
      "text": "The choir sang in a beautiful monochronic harmony that filled the cathedral.",
      "is_correct": false
    },
    {
      "text": "Teachers often encourage students to maintain a monochronic approach while studying for exams.",
      "is_correct": true
    },
    {
      "text": "Because he is highly monochronic, he loves juggling five different projects at the exact same time.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: incorrectly uses the word to describe color (monochromatic) rather than time management. semantic: incorrectly uses the word to describe sound or music (monophonic) rather than time management. pragmatic: contradicts the definition of the word, as a monochronic person would not juggle multiple projects simultaneously.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "diachronic",
    "polychronic",
    "chronic",
    "synchronous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes handling multiple tasks simultaneously rather than one at a time"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The artist used a monochronic palette of blues and grays to paint the gloomy landscape.",
      "is_correct": false
    },
    {
      "text": "The company operates in a very monochronic manner, emphasizing strict deadlines and punctuality.",
      "is_correct": true
    },
    {
      "text": "The doctor diagnosed the patient with a monochronic infection that affected only one lung.",
      "is_correct": false
    },
    {
      "text": "Because the soup was monochronic, it lacked any distinct flavors or spices.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrectly uses the word to describe colors (monochromatic) rather than time management. Incorrectly uses the word to describe taste or lack of variety (monotonous) rather than scheduling. Incorrectly uses the word in a medical context to describe a disease (monoclonal) rather than a cultural or personal time style.",
  "target_word": "monochronic"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "monochronic",
  "relation": "antonym",
  "options": [
    "polychronic",
    "diachronic",
    "anachronistic",
    "synchronous"
  ],
  "correct_answer": "polychronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
      "explanation": "antonym: describes a time management style of handling multiple tasks simultaneously rather than one at a time"
    }
  }
}
```

#### Pack B
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The clock was monochronic because it kept perfect time for decades.",
      "is_correct": false
    },
    {
      "text": "The rainbow appeared monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "She painted her room in a monochronic color scheme to match her curtains.",
      "is_correct": false
    },
    {
      "text": "Is it better to be monochronic when you have many different projects to complete?",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: this confuses 'monochronic' (time-focus) with 'monochromatic' (single color), a different concept entirely. Incorrect: 'monochronic' describes a person's or culture's task-management style, not a device's accuracy. Incorrect: this misapplies the word to color design, which is unrelated to the meaning of focusing on one task at a time.",
  "target_word": "monochronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The rainbow looked completely monochronic after the storm passed.",
      "is_correct": false
    },
    {
      "text": "This monochronic soup tastes delicious with basil and garlic.",
      "is_correct": false
    },
    {
      "text": "I am trying to be more monochronic this week to avoid missing my deadlines.",
      "is_correct": true
    },
    {
      "text": "My phone battery is monochronic because it only lasts one hour.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect use: 'monochronic' describes time-management style, not color, so it should not describe a rainbow's appearance. Incorrect use: battery duration is unrelated to focusing on one task at a time, so 'monochronic' doesn't logically apply here. Incorrect use: taste and flavor have nothing to do with scheduling or task-focus, making this an inappropriate application of the word.",
  "target_word": "monochronic"
}
```

---

## sense 15216, level 9

#### Pack A
### Level 9 (sense 15216, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They were raised in a society that is strictly monochronic about business meetings."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They were raised in a society that is strictly monochronic about business meetings.",
  "chunks": [
    "They",
    "were raised",
    "in a society that is strictly monochronic about business meetings"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "in a society that is strictly monochronic about business meetings",
    "They",
    "were raised"
  ],
  "target_word": "monochronic",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Teachers often encourage students to maintain a monochronic approach while studying for exams."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Teachers often encourage students to maintain a monochronic approach while studying for exams.",
  "chunks": [
    "Teachers",
    "often",
    "encourage",
    "students",
    "to maintain a monochronic approach while studying for exams"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "to maintain a monochronic approach while studying for exams",
    "students",
    "Teachers",
    "often",
    "encourage"
  ],
  "target_word": "monochronic",
  "chunk_count": 5
}
```

#### Pack B
### Level 9 (sense 15216, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "They realized their working styles were different because one was monochronic and the other was polychronic.",
  "chunks": [
    "They",
    "realized",
    "their working styles were different because one was monochronic and the other was polychronic"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "their working styles were different because one was monochronic and the other was polychronic",
    "They",
    "realized"
  ],
  "target_word": "monochronic",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?"
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Is it better to be monochronic when you have many different projects to complete?",
  "chunks": [
    "Is",
    "it",
    "better",
    "to be monochronic",
    "when you have many different projects to complete"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3,
    4
  ],
  "shuffled_chunks": [
    "when you have many different projects to complete",
    "to be monochronic",
    "Is",
    "it",
    "better"
  ],
  "target_word": "monochronic",
  "chunk_count": 5
}
```

---

## sense 16031, level 2

#### Pack A
### Level 2 (sense 16031, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "correct_definition": "To make something so full of water that it cannot float.",
  "options": [
    "To make something so full of water that it cannot float.",
    "Sustained means continuing for a long period without stopping.",
    "A team is a group of people who work together to achieve a common goal.",
    "to separate two things that are connected or linked, often in a system"
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "A plantation is a large estate or farm where crops such as cotton, tobacco, or sugar are grown, often historically worked by enslaved people.",
        "To make something so full of water that it cannot float.",
        "A symbol used in medieval musical notation to indicate pitch and rhythm.",
        "A person who plays music."
      ],
      "correct_answer": "To make something so full of water that it cannot float."
    }
  }
}
```

#### Pack B
### Level 2 (sense 16031, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "correct_definition": "To make something so full of water that it cannot float.",
  "options": [
    "To make something so full of water that it cannot float.",
    "Music that is pleasant and enjoyable to hear.",
    "A fundamental change in the underlying assumptions or methods of a field or system.",
    "to change or make something change into a different form, system, or purpose."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "waterlogged",
  "pronunciation": "WAW-ter-log",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "Coming at the end of a process or series; last.",
        "To make something so full of water that it cannot float.",
        "relating to art or being good at making art",
        "The existence or availability of something in a particular place or situation."
      ],
      "correct_answer": "To make something so full of water that it cannot float."
    }
  }
}
```

---
