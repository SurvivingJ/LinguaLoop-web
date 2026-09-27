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


## sense 14090, level 9

#### Pack A
### Level 9 (sense 14090, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities.",
  "chunks": [
    "Environmental protection",
    "is",
    "a multifaceted challenge that requires cooperation between governments scientists and local communities"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted challenge that requires cooperation between governments scientists and local communities",
    "is",
    "Environmental protection"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination.",
  "chunks": [
    "Learning to play a musical instrument",
    "is",
    "a multifaceted process that requires patience daily practice and coordination"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted process that requires patience daily practice and coordination",
    "Learning to play a musical instrument",
    "is"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 14090, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Environmental protection is a multifaceted challenge that requires cooperation between governments, scientists, and local communities.",
  "chunks": [
    "Environmental protection",
    "is",
    "a multifaceted challenge that requires cooperation between governments scientists and local communities"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted challenge that requires cooperation between governments scientists and local communities",
    "is",
    "Environmental protection"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Learning to play a musical instrument is a multifaceted process that requires patience, daily practice, and coordination.",
  "chunks": [
    "Learning to play a musical instrument",
    "is",
    "a multifaceted process that requires patience daily practice and coordination"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "a multifaceted process that requires patience daily practice and coordination",
    "Learning to play a musical instrument",
    "is"
  ],
  "target_word": "multifaceted",
  "chunk_count": 3
}
```

---

## sense 14100, level 1

#### Pack A
### Level 1 (sense 14100, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "ipa": "/əˈsɛnd/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "extended",
    "attended",
    "ascended",
    "descended"
  ],
  "correct_answer": "ascended",
  "explanation": "This is the target word, correctly matching the sound /əˈsɛndɪd/.",
  "distractor_explanations": {
    "descended": "minimal pair: same stressed syllable '-scended/-cended' but different opening syllable ('de-' vs 'a-').",
    "attended": "near-rhyme: same stress pattern and syllable count, differs mainly in the consonant before the stressed vowel.",
    "extended": "near-rhyme: shares the '-ended' ending sound but differs in the initial consonant cluster."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 14100, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "ipa": "/əˈsɛnd/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "extended",
    "attended",
    "ascended",
    "descended"
  ],
  "correct_answer": "ascended",
  "explanation": "This is the target word, correctly matching the sound /əˈsɛndɪd/.",
  "distractor_explanations": {
    "descended": "minimal pair: same stressed syllable '-scended/-cended' but different opening syllable ('de-' vs 'a-').",
    "attended": "near-rhyme: same stress pattern and syllable count, differs mainly in the consonant before the stressed vowel.",
    "extended": "near-rhyme: shares the '-ended' ending sound but differs in the initial consonant cluster."
  },
  "distractor_source": "llm"
}
```

---

## sense 14100, level 2

#### Pack A
### Level 2 (sense 14100, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "correct_definition": "To move upward or to a higher position.",
  "options": [
    "Hydropower is energy produced by the flow of water, typically using dams or turbines.",
    "Faster than the speed of sound.",
    "Covered or soaked with water or another liquid.",
    "To move upward or to a higher position."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "allows for a slower change to happen",
        "To move upward or to a higher position.",
        "To produce or provide something, such as information, results, or products.",
        "Special skill or knowledge in a particular field."
      ],
      "correct_answer": "To move upward or to a higher position."
    }
  }
}
```

#### Pack B
### Level 2 (sense 14100, difficulty None)
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "correct_definition": "To move upward or to a higher position.",
  "options": [
    "Hydropower is energy produced by the flow of water, typically using dams or turbines.",
    "Faster than the speed of sound.",
    "Covered or soaked with water or another liquid.",
    "To move upward or to a higher position."
  ]
}
```
**definition_match** variant `A`, tier `T3`
```json
{
  "word": "ascended",
  "pronunciation": "uh-SEND",
  "tier": "T3",
  "schema_version": 2,
  "nl": {
    "en": {
      "options": [
        "allows for a slower change to happen",
        "To move upward or to a higher position.",
        "To produce or provide something, such as information, results, or products.",
        "Special skill or knowledge in a particular field."
      ],
      "correct_answer": "To move upward or to a higher position."
    }
  }
}
```

---

## sense 14100, level 3

#### Pack A
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ___ to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "original_sentence": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ascended to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "correct_answer": "ascended",
  "options": [
    "landed",
    "descended",
    "ascended",
    "wandered"
  ],
  "explanation": "Correctly describes coffee's rise in status from a wild plant to a globally valued commodity.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascended"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings after winning the championship game.",
  "original_sentence": "She watched her team ascend to the top of the league standings after winning the championship game.",
  "correct_answer": "ascend",
  "options": [
    "ascend",
    "sit",
    "descend",
    "arrive"
  ],
  "explanation": "Correct: matches the exact verb form used in the sentence, describing the team's rise in the standings.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

#### Pack B
### Level 3 (sense 14100, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ___ to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "original_sentence": "From its humble origins as a wild plant in the highlands of Ethiopia, coffee has ascended to become one of the world's most highly valued commodities, underpinning the livelihoods of millions and shaping diurnal rituals across continents.",
  "correct_answer": "ascended",
  "options": [
    "landed",
    "descended",
    "ascended",
    "wandered"
  ],
  "explanation": "Correctly describes coffee's rise in status from a wild plant to a globally valued commodity.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascended"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "She watched her team ___ to the top of the league standings after winning the championship game.",
  "original_sentence": "She watched her team ascend to the top of the league standings after winning the championship game.",
  "correct_answer": "ascend",
  "options": [
    "ascend",
    "sit",
    "descend",
    "arrive"
  ],
  "explanation": "Correct: matches the exact verb form used in the sentence, describing the team's rise in the standings.",
  "distractor_tags": {},
  "word_definition": "To move upward or to a higher position.",
  "target_word": "ascend"
}
```

---

## sense 14100, level 4

#### Pack A
### Level 4 (sense 14100, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "required_pos": "verb",
  "options": [
    "ascendous",
    "ascendment",
    "ascendful",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base verb form required after the infinitive marker 'to'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "required_pos": "verb",
  "options": [
    "ascendment",
    "ascendous",
    "ascendify",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the bare infinitive required after the modal 'can'"
    }
  }
}
```

#### Pack B
### Level 4 (sense 14100, difficulty None)
**cloze_typed** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ___ and traverse vast distances.",
  "original_sentence": "At the heart of this phenomenon lies the concept of lift, a force that perpetually battles gravity, enabling these massive machines to ascend and traverse vast distances.",
  "required_pos": "verb",
  "options": [
    "ascendous",
    "ascendment",
    "ascendful",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the base verb form required after the infinitive marker 'to'"
    }
  }
}
```
**cloze_typed** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "target_word": "ascend",
  "word": "ascended",
  "answer": {
    "accepted": [
      "ascend"
    ],
    "accepted_normalized": [
      "ascend"
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
  "stem": "ascend",
  "sentence_with_blank": "Birds can easily ___ to great heights by catching warm air currents.",
  "original_sentence": "Birds can easily ascend to great heights by catching warm air currents.",
  "required_pos": "verb",
  "options": [
    "ascendment",
    "ascendous",
    "ascendify",
    "ascend"
  ],
  "correct_answer": "ascend",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the bare infinitive required after the modal 'can'"
    }
  }
}
```

---

## sense 14100, level 6

#### Pack A
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The negotiations ascended into a heated argument about salary increases.",
      "is_correct": false
    },
    {
      "text": "The soup ascended in temperature after being left on the stove overnight.",
      "is_correct": false
    },
    {
      "text": "The hikers began to ascend the steep mountain trail early in the morning before the sun got too hot.",
      "is_correct": true
    },
    {
      "text": "He ascended his phone number into the database for future reference.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: abstract escalation of conflict is normally described with 'escalated,' not 'ascended,' which implies literal or status-based upward movement. Semantically inappropriate: entering data has no upward movement or rise in position, so 'ascended' does not fit this action. Pragmatically inappropriate: temperature changes are normally described with 'rose' or 'increased'; 'ascended' is not the natural verb for this kind of gradual heating.",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "As the elevator doors closed, the car began to ascend smoothly to the tenth floor.",
      "is_correct": true
    },
    {
      "text": "He decided to ascend his resignation letter to the manager before leaving the office.",
      "is_correct": false
    },
    {
      "text": "The temperature will ascend rapidly overnight, making the room impossible to sleep in.",
      "is_correct": false
    },
    {
      "text": "The river will ascend into the ocean after passing through the delta.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'ascend' is used for physical or spatial movement upward, not for a temperature increase, which should use 'rise'. semantic: 'ascend' does not mean to submit or hand over a document; this misuses the verb's core meaning of upward movement. semantic: rivers flow downward into the ocean, so 'ascend' contradicts the natural direction of water flow.",
  "target_word": "ascend"
}
```

#### Pack B
### Level 6 (sense 14100, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The negotiations ascended into a heated argument about salary increases.",
      "is_correct": false
    },
    {
      "text": "The soup ascended in temperature after being left on the stove overnight.",
      "is_correct": false
    },
    {
      "text": "The hikers began to ascend the steep mountain trail early in the morning before the sun got too hot.",
      "is_correct": true
    },
    {
      "text": "He ascended his phone number into the database for future reference.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically odd: abstract escalation of conflict is normally described with 'escalated,' not 'ascended,' which implies literal or status-based upward movement. Semantically inappropriate: entering data has no upward movement or rise in position, so 'ascended' does not fit this action. Pragmatically inappropriate: temperature changes are normally described with 'rose' or 'increased'; 'ascended' is not the natural verb for this kind of gradual heating.",
  "target_word": "ascend"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "As the elevator doors closed, the car began to ascend smoothly to the tenth floor.",
      "is_correct": true
    },
    {
      "text": "He decided to ascend his resignation letter to the manager before leaving the office.",
      "is_correct": false
    },
    {
      "text": "The temperature will ascend rapidly overnight, making the room impossible to sleep in.",
      "is_correct": false
    },
    {
      "text": "The river will ascend into the ocean after passing through the delta.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: 'ascend' is used for physical or spatial movement upward, not for a temperature increase, which should use 'rise'. semantic: 'ascend' does not mean to submit or hand over a document; this misuses the verb's core meaning of upward movement. semantic: rivers flow downward into the ocean, so 'ascend' contradicts the natural direction of water flow.",
  "target_word": "ascend"
}
```

---

## sense 14100, level 9

#### Pack A
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

---
