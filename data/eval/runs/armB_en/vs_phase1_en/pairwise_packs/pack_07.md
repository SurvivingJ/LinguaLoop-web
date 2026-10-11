# Pairwise review pack 07

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
      "text": "The choir's performance was beautifully polychronic, with each section singing a different melody.",
      "is_correct": false
    },
    {
      "text": "Working in a polychronic environment means that meetings often start late and overlap with other tasks.",
      "is_correct": true
    },
    {
      "text": "The ancient vase was polychronic, featuring intricate designs in blue, red, and gold.",
      "is_correct": false
    },
    {
      "text": "He suffered from a polychronic virus that attacked multiple organs simultaneously.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect usage: Confuses 'polychronic' (time-related) with 'polychromatic' or 'polychrome' (color-related). Incorrect usage: Applies the term to a medical/biological context where 'systemic' or 'multi-organ' would be appropriate, not a temporal one. Incorrect usage: Misapplies the term to music; the correct term for multiple independent melodies is 'polyphonic'.",
  "target_word": "polychronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She suffered from a severe polychronic fever that lasted for three days.",
      "is_correct": false
    },
    {
      "text": "The ancient statue was carved from a single block of polychronic marble.",
      "is_correct": false
    },
    {
      "text": "The chef added a polychronic spice to enhance the flavor of the soup.",
      "is_correct": false
    },
    {
      "text": "He felt that being polychronic helped him manage his creative hobbies and schoolwork simultaneously.",
      "is_correct": true
    }
  ],
  "explanation": "Semantic error: 'Polychronic' describes time perception or behavior, not physical materials or colors. The correct term might be 'monolithic' or 'polychrome'. Semantic error: 'Polychronic' is not a medical term and cannot describe a biological condition like a fever. It applies to cultural or individual time-use patterns. Semantic error: 'Polychronic' does not describe taste, ingredients, or culinary properties. It is unrelated to food preparation.",
  "target_word": "polychronic"
}
```

---

## sense 15216, level 1

#### Pack A
### Level 1 (sense 15216, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "monochronic",
  "pronunciation": "mah-nuh-KRON-ik",
  "ipa": "/ˌmɒnəˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "monochrome",
    "chronic",
    "monotonic",
    "monochronic"
  ],
  "correct_answer": "monochronic",
  "explanation": "Correct: matches the target word exactly.",
  "distractor_explanations": {
    "monochrome": "Near-homophone: shares the first syllable /ˈmɒnə/ and similar ending, but refers to color rather than time management.",
    "chronic": "Phonetic overlap: contains the root /krɒnɪk/ but lacks the prefix, changing the meaning to 'long-lasting' or 'severe'.",
    "monotonic": "Minimal pair/Rhyme: differs mainly in the vowel sound of the third syllable (/ɒ/ vs /ə/) and stress pattern, referring to unvarying tone."
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

## sense 15216, level 3

#### Pack A
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She has always preferred a ___ approach to studying because multitasking distracts her from finishing essays on time.",
  "original_sentence": "She has always preferred a monochronic approach to studying because multitasking distracts her from finishing essays on time.",
  "correct_answer": "monochronic",
  "options": [
    "chaotic",
    "collaborative",
    "spontaneous",
    "monochronic"
  ],
  "explanation": "Correct: fits the context of focusing on one task at a time.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Working in a ___ office means that meetings start promptly and schedules are rarely changed at the last minute.",
  "original_sentence": "Working in a monochronic office means that meetings start promptly and schedules are rarely changed at the last minute.",
  "correct_answer": "monochronic",
  "options": [
    "spontaneous",
    "monochronic",
    "flexible",
    "chaotic"
  ],
  "explanation": "Correct: Fits the context of an office culture where schedules are strict and meetings start promptly.",
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

## sense 15216, level 6

#### Pack A
### Level 6 (sense 15216, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She suffered from a monochronic illness that lasted for several years.",
      "is_correct": false
    },
    {
      "text": "The artist painted the entire canvas in a monochronic shade of blue.",
      "is_correct": false
    },
    {
      "text": "People who are monochronic typically view time as a limited resource that must be carefully divided among different activities.",
      "is_correct": true
    },
    {
      "text": "The choir sang in a monochronic voice that bored the audience.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic error: 'Monochronic' relates to time management, not color; the correct term for single-color art is 'monochromatic'. Semantic error: 'Monochronic' does not describe medical conditions or duration of disease; 'chronic' would be the appropriate term. Semantic error: 'Monochronic' does not describe sound or pitch; 'monotone' or 'monotonous' is the correct descriptor for unvarying vocal delivery.",
  "target_word": "monochronic"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He suffered from a monochronic illness that lasted for several years without improvement.",
      "is_correct": false
    },
    {
      "text": "The monochronic engine ran smoothly because all its parts were made of the same metal alloy.",
      "is_correct": false
    },
    {
      "text": "The monochronic painting featured only shades of blue and gray, creating a somber mood.",
      "is_correct": false
    },
    {
      "text": "Is your teacher usually monochronic about project deadlines, or does she allow students to submit work late?",
      "is_correct": true
    }
  ],
  "explanation": "Semantic error: Uses 'monochronic' to describe visual color uniformity (monochromatic), confusing time management with visual aesthetics. Semantic error: Uses 'monochronic' to describe the duration of a medical condition (chronic), confusing time management style with health terminology. Semantic error: Uses 'monochronic' to describe material composition or mechanical uniformity, which is unrelated to the concept of managing time or tasks.",
  "target_word": "monochronic"
}
```

#### Pack B
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

---

## sense 15216, level 7

#### Pack A
### Level 7 (sense 15216, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He felt stressed when his team tried to mix polychronic habits with his usual monochronic schedule.",
      "is_correct": true
    },
    {
      "text": "She has always preferred a monochronic approach to studying because multitasking distracts her from finishing essays on time.",
      "is_correct": true
    },
    {
      "text": "She prefers to work in a monochronic way, so she likes to handle several tasks at the same time.",
      "is_correct": false,
      "error_description": "The sentence contains a semantic contradiction. 'Monochronic' refers to doing one thing at a time, while the context describes handling several tasks simultaneously, which is 'polychronic'."
    },
    {
      "text": "Because our school operates in a monochronic culture, students are expected to arrive at every class exactly when the bell rings.",
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
      "text": "The manager is very monochronicly and insists that we stick to the agenda without deviation.",
      "is_correct": false,
      "error_description": "The word 'monochronic' is an adjective and should be used to describe the noun 'manager'. The adverb form 'monochronically' cannot follow the linking verb 'is' to describe a person's trait in this structure; it would need to modify a verb (e.g., 'works monochronically')."
    },
    {
      "text": "They realized their communication problems stemmed from one partner being monochronic and the other being much more flexible.",
      "is_correct": true
    },
    {
      "text": "Is your teacher usually monochronic about project deadlines, or does she allow students to submit work late?",
      "is_correct": true
    },
    {
      "text": "Working in a monochronic office means that meetings start promptly and schedules are rarely changed at the last minute.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 15216, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "My friend is so monochronic that she always completes her homework before starting any leisure activities.",
      "is_correct": true
    },
    {
      "text": "She organizes her study materials very monochronic to ensure she doesn't get distracted.",
      "is_correct": false,
      "error_description": "The adjective 'monochronic' is incorrectly used to modify the verb 'organizes'. It should be replaced with the adverb 'monochronically'."
    },
    {
      "text": "The company operates in a very monochronic manner, emphasizing strict deadlines and punctuality.",
      "is_correct": true
    },
    {
      "text": "While working on the group presentation, we realized our communication styles were less monochronic than expected.",
      "is_correct": true
    }
  ]
}
```

---

## sense 16181, level 1

#### Pack A
### Level 1 (sense 16181, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "well",
  "ipa": "/wɛl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "batter",
    "bettor",
    "better",
    "bitter"
  ],
  "correct_answer": "better",
  "explanation": "Correct: matches the spoken target word /ˈbɛtər/.",
  "distractor_explanations": {
    "bettor": "Homophone: same /ˈbɛtər/ sound, different spelling and meaning (a person who bets).",
    "bitter": "Minimal pair: differs only in the vowel sound /ɪ/ instead of /ɛ/.",
    "batter": "Minimal pair: differs only in the vowel sound /æ/ instead of /ɛ/."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 16181, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "better",
  "pronunciation": "wel",
  "ipa": "/wɛl/",
  "syllable_count": 1,
  "audio_url": null,
  "options": [
    "better",
    "batter",
    "butter",
    "letter"
  ],
  "correct_answer": "better",
  "explanation": "Target word: matches the spoken audio exactly.",
  "distractor_explanations": {
    "butter": "Minimal pair: differs only in the vowel sound (/ɛ/ vs /ʌ/) and final consonant cluster.",
    "letter": "Rhyme: shares the same ending stress and syllable structure but starts with a different consonant.",
    "batter": "Near-homophone: similar consonant framework and vowel quality, easily confused in rapid speech."
  },
  "distractor_source": "llm"
}
```

---

## sense 16181, level 3

#### Pack A
### Level 3 (sense 16181, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Everything went even better than we had hoped during the event.",
  "original_sentence": "Everything went even better than we had hoped during the event.",
  "correct_answer": "better",
  "options": [
    "more precisely",
    "harder",
    "worse",
    "better"
  ],
  "explanation": "Correct: the target comparative adverb appropriately describes the positive outcome of the event.",
  "distractor_tags": {},
  "word_definition": "In a satisfactory or proper manner.",
  "target_word": "well"
}
```

#### Pack B
### Level 3 (sense 16181, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "It makes our cities ___.",
  "original_sentence": "It makes our cities better.",
  "correct_answer": "better",
  "options": [
    "better",
    "yesterday",
    "loudly",
    "worse"
  ],
  "explanation": "Correct: fits the comparative context of improving city conditions.",
  "distractor_tags": {},
  "word_definition": "In a satisfactory or proper manner.",
  "target_word": "better"
}
```

---

## sense 16181, level 6

#### Pack A
### Level 6 (sense 16181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The soup tastes better than the color blue.",
      "is_correct": false
    },
    {
      "text": "The soccer team played much better throughout the entire second half.",
      "is_correct": true
    },
    {
      "text": "She sings better than the number seven.",
      "is_correct": false
    },
    {
      "text": "He runs better than the speed of light.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: compares sensory experiences from incompatible domains (taste vs. sight) without metaphorical context. Semantically inappropriate: asserts a physical impossibility that violates real-world constraints, making the comparison nonsensical. Pragmatically inappropriate: compares a human action to an abstract mathematical concept, lacking any logical basis for comparison.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "adequately",
    "worse",
    "preferably",
    "superiorly"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "antonym: in a less satisfactory or proper manner"
    }
  }
}
```

#### Pack B
### Level 6 (sense 16181, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She understands the math problem better by ignoring it completely.",
      "is_correct": false
    },
    {
      "text": "The sun shines better at midnight than at noon.",
      "is_correct": false
    },
    {
      "text": "The color blue tastes better than the color red.",
      "is_correct": false
    },
    {
      "text": "If you study hard, you will do better on the upcoming history exam.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: violates sensory selectional restrictions, as colors cannot be tasted. pragmatic: logically contradictory, as ignoring a problem precludes understanding it. pragmatic: contradicts basic physical reality and the definition of midnight.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "worse",
    "slower",
    "harder",
    "faster"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "means in a less satisfactory manner, directly opposing the sense of performing properly"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "He slept better during the loud, chaotic rock concert in the front row.",
      "is_correct": false
    },
    {
      "text": "The deceased plant grew better after it was completely dried out and left in the dark.",
      "is_correct": false
    },
    {
      "text": "She knows the neighborhood better since she grew up around here.",
      "is_correct": true
    },
    {
      "text": "The ice cream melted better when it was kept inside the freezing freezer.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: dead and dried plants cannot grow, making the sentence logically absurd. Pragmatically inappropriate: people do not sleep better in loud, chaotic environments like a front-row concert. Pragmatically inappropriate: ice cream does not melt better in a freezing environment; it melts better in heat.",
  "target_word": "well"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "better",
  "relation": "antonym",
  "options": [
    "worse",
    "more",
    "further",
    "rather"
  ],
  "correct_answer": "worse",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a satisfactory or proper manner.",
      "explanation": "antonym: performing an action in a less satisfactory or proper manner"
    }
  }
}
```

---

## sense 19458, level 7

#### Pack A
### Level 7 (sense 19458, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The science test was hard, but he studied hard and passed nonetheless.",
      "is_correct": true
    },
    {
      "text": "The movie received bad reviews, nonetheless it was a box office hit.",
      "is_correct": false,
      "error_description": "When 'nonetheless' is used as a conjunctive adverb to connect two independent clauses, it must be preceded by a semicolon (or a period) and followed by a comma. Using only a comma creates a comma splice error."
    },
    {
      "text": "The rules seemed unfair, but the students followed them nonetheless.",
      "is_correct": true
    },
    {
      "text": "It was an expensive ticket, and she bought it nonetheless.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 19458, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The test was extremely difficult; nonetheless, most students passed it.",
      "is_correct": true
    },
    {
      "text": "The weather was cold and rainy, but they went outside nonetheless.",
      "is_correct": true
    },
    {
      "text": "The project was behind schedule, nonetheless the team managed to finish it on time.",
      "is_correct": false,
      "error_description": "'Nonetheless' is a conjunctive adverb and cannot join two independent clauses with only a comma; it requires a semicolon, a period, or a coordinating conjunction."
    },
    {
      "text": "She had studied all night and felt tired, but she wrote the essay well nonetheless.",
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
      "text": "Although the team had lost several players to injuries, they played hard nonetheless.",
      "is_correct": true
    },
    {
      "text": "The museum was closing soon, and they tried to see the main exhibit nonetheless.",
      "is_correct": true
    },
    {
      "text": "The museum was closing soon, nonetheless they tried to see the main exhibit.",
      "is_correct": false,
      "error_description": "'Nonetheless' is a conjunctive adverb, not a coordinating conjunction, so it cannot join two independent clauses with only a comma. A semicolon or period is required before it when connecting two independent clauses."
    },
    {
      "text": "The instructions were confusing, but he figured out how to build the model nonetheless.",
      "is_correct": true
    }
  ]
}
```

---

## sense 19480, level 6

#### Pack A
### Level 6 (sense 19480, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The virus spread equitably through the population, infecting everyone regardless of health status.",
      "is_correct": false
    },
    {
      "text": "During the club meeting, the president distributed the fundraising tasks equitably.",
      "is_correct": true
    },
    {
      "text": "The heavy rain fell equitably on the roof, the garden, and the street.",
      "is_correct": false
    },
    {
      "text": "He equitably forgot his keys on the kitchen counter before leaving for work.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Natural phenomena like rain do not have intent or moral agency to distribute things 'fairly' or 'justly'; this is a category error. Semantically inappropriate: 'Forgetting' is an involuntary mental lapse, not an action that can be performed with fairness or justice toward others. Pragmatically inappropriate: While the spread may be uniform, attributing 'fairness' or 'justice' to a harmful biological process is semantically conflicting and socially tone-deaf.",
  "target_word": "equitably"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The rain fell equitably on the roof throughout the night.",
      "is_correct": false
    },
    {
      "text": "The students discussed how to solve the problem equitably without causing any arguments.",
      "is_correct": true
    },
    {
      "text": "He solved the math equation equitably using the quadratic formula.",
      "is_correct": false
    },
    {
      "text": "The chef chopped the onions equitably to prepare the soup.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' refers to social fairness and justice among people, not the physical precision or uniformity of cutting vegetables. Semantically incorrect: Mathematical solutions are judged by accuracy or efficiency, not by moral fairness or justice. Category error: Natural phenomena like rain cannot act with moral intent or justice; 'steadily' or 'heavily' would be appropriate.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "justly",
    "rightly",
    "equally",
    "unfairly"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: in a way that is not just or equal"
    }
  }
}
```

#### Pack B
### Level 6 (sense 19480, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef chopped the onions equitably, ensuring every piece was exactly the same size.",
      "is_correct": false
    },
    {
      "text": "The sun shone equitably on the plants, giving each one the exact same amount of light.",
      "is_correct": false
    },
    {
      "text": "Resources should be divided equitably across all the different clubs at our school.",
      "is_correct": true
    },
    {
      "text": "She equitably tied her shoes so that both laces were perfectly symmetrical.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' refers to fairness and justice in human treatment or resource distribution, not the physical, geometric precision of chopping vegetables. Semantically inappropriate: 'Equitably' requires an agent capable of moral reasoning and intent; natural phenomena like the sun cannot act with a sense of justice or fairness. Pragmatically inappropriate: 'Equitably' describes fair treatment of people or distribution of resources, not the physical symmetry or aesthetic balance of tying shoelaces.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "proportionally",
    "adequately",
    "unfairly",
    "equally"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: means in a way that is not fair or just to everyone involved"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef chopped the vegetables equitably so that they would cook at the exact same speed in the pan.",
      "is_correct": false
    },
    {
      "text": "She equitably tied her shoelaces before going for a long run in the park.",
      "is_correct": false
    },
    {
      "text": "The discussion leader ensured that all participants could speak equitably during the debate.",
      "is_correct": true
    },
    {
      "text": "The sun shone equitably on the flowers in the garden, helping them all grow tall.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Equitably' refers to moral fairness and justice among people, not the physical uniformity of chopped vegetables (which would be 'uniformly' or 'evenly'). Semantically inappropriate: Tying shoelaces is a physical action that does not involve treating multiple parties fairly or justly. Semantically inappropriate: Natural phenomena like sunlight cannot possess moral agency or distribute resources with a sense of justice; 'equally' would be the correct word here.",
  "target_word": "equitably"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "equitably",
  "relation": "antonym",
  "options": [
    "impartially",
    "equally",
    "reasonably",
    "unfairly"
  ],
  "correct_answer": "unfairly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "In a way that is fair and just, giving equal treatment to everyone involved.",
      "explanation": "antonym: in a way that is not fair or just to everyone"
    }
  }
}
```

---
