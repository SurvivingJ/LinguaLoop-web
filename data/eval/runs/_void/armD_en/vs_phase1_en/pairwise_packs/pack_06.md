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


## sense 14473, level 6

#### Pack A
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

#### Pack B
### Level 6 (sense 14473, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Over time, the rock remained completely unchanged and exactly the same forever.",
      "is_correct": false
    },
    {
      "text": "His confidence grew over time as he practiced speaking in public.",
      "is_correct": true
    },
    {
      "text": "Over time, the chef instantly chopped the onions in a single second.",
      "is_correct": false
    },
    {
      "text": "I will finish this entire book over time in the next five minutes.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'over time' implies a gradual process, which directly contradicts the instantaneous action of 'instantly' and 'in a single second'. Semantically inappropriate: reading an entire book is a long task that cannot logically be completed 'over time' within a mere five-minute window. Pragmatically inappropriate: 'over time' suggests a gradual process of change or development, which clashes with the stative concept of remaining 'unchanged' and 'exactly the same'.",
  "target_word": "over time"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Over time, the rock was completely unchanged for millions of years.",
      "is_correct": false
    },
    {
      "text": "The secrets of the ancient civilization were revealed over time.",
      "is_correct": true
    },
    {
      "text": "Over time, she quickly finished her homework in five minutes.",
      "is_correct": false
    },
    {
      "text": "Over time, the sun instantly vaporized the puddle of water.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'over time' implies a gradual process, which directly contradicts the instantaneous action of 'instantly vaporized'. Semantically inappropriate: 'over time' means gradually as time goes by, which conflicts with the rapid, completed action of finishing in just five minutes. Pragmatically inappropriate: 'over time' suggests a gradual change or progression, making it illogical to pair with a state of being 'completely unchanged'.",
  "target_word": "over time"
}
```

---

## sense 14473, level 7

#### Pack A
### Level 7 (sense 14473, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Over time, she learned how to play the difficult piano piece.",
      "is_correct": true
    },
    {
      "text": "The old wooden fence started to fade over time.",
      "is_correct": true
    },
    {
      "text": "Over time, it got better.",
      "is_correct": true
    },
    {
      "text": "He had to work over time to complete the assignment before the deadline.",
      "is_correct": false,
      "error_description": "The phrase 'over time' (two words) is an adverbial phrase meaning 'gradually' or 'as time passes'. To express working extra hours beyond a normal schedule, the correct single-word noun/adverb is 'overtime'."
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They realized their misunderstandings would clear up over time.",
      "is_correct": true
    },
    {
      "text": "Over time goes by, you will understand the complex rules of the game.",
      "is_correct": false,
      "error_description": "The learner incorrectly blended the fixed adverbial phrase 'over time' with the clause 'as time goes by'. 'Over time' functions as a standalone adverbial phrase and should not be followed by a verb like 'goes'."
    },
    {
      "text": "Over time, cities expand and change their appearance.",
      "is_correct": true
    },
    {
      "text": "The secrets of the ancient civilization were revealed over time.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14473, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Her confidence grew slowly over time.",
      "is_correct": true
    },
    {
      "text": "He was not paid for the over time he worked last night.",
      "is_correct": false,
      "error_description": "The two-word phrase 'over time' is an adverbial phrase meaning 'gradually.' When referring to extra hours worked beyond a regular schedule, the correct single-word noun is 'overtime'."
    },
    {
      "text": "Over time, it got better.",
      "is_correct": true
    },
    {
      "text": "Languages can change significantly over time.",
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
      "text": "Skills are developed over time with patience and hard work.",
      "is_correct": true
    },
    {
      "text": "The heavy rain eroded the soil over the time.",
      "is_correct": false,
      "error_description": "The phrase 'over time' is a fixed adverbial expression meaning 'gradually' and does not take a definite article. Adding 'the' is a common structural error."
    },
    {
      "text": "The heavy rain eroded the soil over time.",
      "is_correct": true
    },
    {
      "text": "Memories can fade over time.",
      "is_correct": true
    }
  ]
}
```

---

## sense 14544, level 3

#### Pack A
### Level 3 (sense 14544, difficulty None)
**cloze_completion** variant `A`, tier `3`
```json
{
  "sentence_with_blank": "Around the 9th century, the development of ___ marked a crucial step forward.",
  "original_sentence": "Around the 9th century, the development of neumes marked a crucial step forward.",
  "correct_answer": "neumes",
  "options": [
    "neumes",
    "instruments",
    "compositions",
    "gigs"
  ],
  "explanation": "Correct target word.",
  "distractor_tags": {},
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neumes"
}
```
**cloze_completion** variant `B`, tier `3`
```json
{
  "sentence_with_blank": "The scribe drew a tiny ___ above the Latin lyrics.",
  "original_sentence": "The scribe drew a tiny neume above the Latin lyrics.",
  "correct_answer": "neume",
  "options": [
    "doodle",
    "fresco",
    "melody",
    "neume"
  ],
  "explanation": "correct: the exact inflected form of the target word fitting the singular context 'a tiny...'",
  "distractor_tags": {},
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```

#### Pack B
### Level 3 (sense 14544, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Around the 9th century, the development of ___ marked a crucial step forward.",
  "original_sentence": "Around the 9th century, the development of neumes marked a crucial step forward.",
  "correct_answer": "neumes",
  "options": [
    "neumes",
    "scripts",
    "clefs",
    "temples"
  ],
  "explanation": "Correct: refers to the medieval musical symbols whose development advanced notation.",
  "distractor_tags": {},
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neumes"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The professor explained that a single ___ could represent multiple notes.",
  "original_sentence": "The professor explained that a single neume could represent multiple notes.",
  "correct_answer": "neume",
  "options": [
    "clef",
    "measure",
    "melody",
    "neume"
  ],
  "explanation": "Correct: 'neume' is the singular noun form required by the determiner 'a single'.",
  "distractor_tags": {},
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```

---

## sense 14544, level 4

#### Pack A
### Level 4 (sense 14544, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The choir director pointed to each tiny ___ on the aged parchment.",
  "original_sentence": "The choir director pointed to each tiny neume on the aged parchment.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neume's",
    "neumes'",
    "neumes",
    "neume"
  ],
  "explanation": "singular form required by the distributive determiner 'each'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "By examining the ___ closely, they understood how the chant was sung.",
  "original_sentence": "By examining the neume closely, they understood how the chant was sung.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neume",
    "neume's",
    "neumes'",
    "neumes"
  ],
  "explanation": "singular noun required by the singular determiner 'the' and singular context",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```

#### Pack B
### Level 4 (sense 14544, difficulty None)
**morphology_slot** variant `A`, tier `3`
```json
{
  "sentence_with_blank": "The music historian carefully studied each ___ written on the old parchment.",
  "original_sentence": "The music historian carefully studied each neume written on the old parchment.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neume",
    "neumes'",
    "neume's",
    "neumes"
  ],
  "explanation": "singular noun required by the determiner 'each'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```
**morphology_slot** variant `B`, tier `3`
```json
{
  "sentence_with_blank": "Experts debated how those specific ___ represented the original vocal rhythm.",
  "original_sentence": "Experts debated how those specific neumes represented the original vocal rhythm.",
  "correct_answer": "neumes",
  "base_form": "neume",
  "form_label": "plural",
  "options": [
    "neumes",
    "neume",
    "neumes'",
    "neume's"
  ],
  "explanation": "plural noun required by the determiner 'those'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neumes"
}
```

---

## sense 14544, level 6

#### Pack A
### Level 6 (sense 14544, difficulty None)
**semantic_discrimination** variant `A`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The government passed a law requiring all citizens to pay taxes in neumes.",
      "is_correct": false
    },
    {
      "text": "The chef sprinkled the neumes over the pasta to add a crunchy texture.",
      "is_correct": false
    },
    {
      "text": "The flock of neumes migrated south for the winter to find warmer climates.",
      "is_correct": false
    },
    {
      "text": "Several unusual neumes appeared at the top of the manuscript page.",
      "is_correct": true
    }
  ],
  "explanation": "neumes are abstract written symbols, not physical food items that can be eaten. neumes are musical notation symbols, not a form of currency or legal tender. neumes are inanimate written characters, not living animals or birds that can migrate.",
  "target_word": "neumes"
}
```
**semantic_discrimination** variant `B`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The modern pop producer used neumes to program the synthesizer beats for the new album.",
      "is_correct": false
    },
    {
      "text": "The architect drew neumes on the blueprint to indicate where the load-bearing walls should be placed.",
      "is_correct": false
    },
    {
      "text": "The students examined how each neume guided the singer's voice.",
      "is_correct": true
    },
    {
      "text": "The chef sprinkled neumes over the pasta to add a crunchy texture and savory flavor.",
      "is_correct": false
    }
  ],
  "explanation": "pragmatic: neumes are historical medieval symbols, not tools used in modern electronic music production semantic: neumes are musical notation symbols, not architectural drafting marks for building structures semantic: neumes are abstract written symbols, not physical food items that can be sprinkled for flavor",
  "target_word": "neume"
}
```

#### Pack B
### Level 6 (sense 14544, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The mechanic tightened the neumes with a wrench to fix the car's engine.",
      "is_correct": false
    },
    {
      "text": "She planted the neumes in the garden, hoping they would bloom into beautiful flowers by spring.",
      "is_correct": false
    },
    {
      "text": "The chef sprinkled the neumes over the pasta like a fine, musical seasoning.",
      "is_correct": false
    },
    {
      "text": "Music historians studied how the strange neume showed the direction of the melody.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: neumes are abstract visual symbols for music, not physical objects that can be used as food seasoning. Semantically inappropriate: neumes are written notation marks, not biological seeds or plants that can grow. Semantically inappropriate: neumes are graphical symbols on a page, not physical mechanical parts or hardware.",
  "target_word": "neume"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The mechanic replaced the broken neumes in the car's engine to improve its speed.",
      "is_correct": false
    },
    {
      "text": "She carefully arranged the neumes in the garden to attract more butterflies.",
      "is_correct": false
    },
    {
      "text": "The chef sprinkled the neumes over the pasta like a fine, musical seasoning.",
      "is_correct": false
    },
    {
      "text": "Each ornate neume guided the singers through the complex liturgical music.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: Neumes are abstract written symbols for musical notation, not physical objects that can be used as food seasoning. semantic: Neumes are ink marks on a page, not physical plants or objects that can be planted in a garden. semantic: Neumes are medieval musical symbols, not mechanical parts or components of a car engine.",
  "target_word": "neume"
}
```

---

## sense 14544, level 7

#### Pack A
### Level 7 (sense 14544, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `3`
```json
{
  "sentences": [
    {
      "text": "Around the 9th century, the development of neumes marked a crucial step forward.",
      "is_correct": true
    },
    {
      "text": "The neumes on the ancient parchment was very difficult for the historian to decipher.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the plural subject 'neumes' requires the plural verb 'were', not the singular 'was'."
    },
    {
      "text": "The music historian carefully studied each neume written on the old parchment.",
      "is_correct": true
    },
    {
      "text": "Monks used every neume to remember how the sacred chants should sound.",
      "is_correct": true
    }
  ]
}
```
**spot_incorrect_sentence** variant `B`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The scribe drew a tiny neume above the Latin lyrics.",
      "is_correct": true
    },
    {
      "text": "There is several neumes written in the margin of the page.",
      "is_correct": false,
      "error_description": "The plural noun 'neumes' requires the plural verb 'are' instead of the singular 'is' in an existential 'there' construction."
    },
    {
      "text": "Experts debated how those specific neumes represented the original vocal rhythm.",
      "is_correct": true
    },
    {
      "text": "The students examined how each neume guided the singer's voice.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14544, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The ancient neumes is very hard to read for modern musicians.",
      "is_correct": false,
      "error_description": "The subject 'neumes' is plural, so it requires the plural verb 'are' instead of the singular verb 'is'."
    },
    {
      "text": "Monks drew every single neume carefully above the sacred Latin texts.",
      "is_correct": true
    },
    {
      "text": "The choir director pointed to each tiny neume on the aged parchment.",
      "is_correct": true
    },
    {
      "text": "Around the 9th century, the development of neumes marked a crucial step forward.",
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
      "text": "The professor explained that a single neume could represent multiple notes.",
      "is_correct": true
    },
    {
      "text": "Each ornate neume guided the singers through the complex liturgical music.",
      "is_correct": true
    },
    {
      "text": "By examining the neume closely, they understood how the chant was sung.",
      "is_correct": true
    },
    {
      "text": "The ancient neumes was used by the monks to guide the singers.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the plural subject 'neumes' requires the plural verb 'were' instead of the singular 'was'."
    }
  ]
}
```

---

## sense 15150, level 1

#### Pack A
### Level 1 (sense 15150, difficulty None)
**phonetic_recognition** variant `B`, tier `T3`
```json
{
  "word": "polychronic",
  "pronunciation": "pol-ee-KRON-ik",
  "ipa": "/ˌpɒliˈkrɒnɪk/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "polychromic",
    "polyclinic",
    "polytechnic",
    "polychronic"
  ],
  "correct_answer": "polychronic",
  "explanation": "Correct: This is the exact target word.",
  "distractor_explanations": {
    "polychromic": "Near-homophone: differs only in the middle syllable sounds (/krɒn/ vs /krəʊm/).",
    "polyclinic": "Minimal pair: differs in the consonant cluster and vowel of the stressed syllable (/krɒn/ vs /klɪn/).",
    "polytechnic": "Structural rhyme: shares the same stress pattern and syllable count, but differs in the middle syllable (/krɒn/ vs /tek/)."
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
    "chronological",
    "synchronous",
    "polychronic",
    "punctual"
  ],
  "explanation": "Correct: Fits the context of cultures that embrace a fluid, multi-layered approach to time.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He prefers a ___ workflow instead of focusing on just one assignment from morning until evening.",
  "original_sentence": "He prefers a polychronic workflow instead of focusing on just one assignment from morning until evening.",
  "correct_answer": "polychronic",
  "options": [
    "monochronic",
    "synchronous",
    "polychronic",
    "sporadic"
  ],
  "explanation": "Correct: Fits the context of handling multiple tasks simultaneously rather than sequentially.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
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
      "text": "People with a polychronic lifestyle often feel comfortable handling several conversations at the same time.",
      "is_correct": true
    },
    {
      "text": "He took a polychronic pill that cured his headache instantly and lasted for exactly twenty-four hours.",
      "is_correct": false
    },
    {
      "text": "The polychronic bridge was built using a highly durable alloy that resisted rust and corrosion for decades.",
      "is_correct": false
    },
    {
      "text": "The polychronic painting featured a single, solid color applied uniformly across the entire canvas.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: 'polychronic' refers to time management, not visual art or color palettes (which would use 'polychromatic'). Semantic error: 'polychronic' describes a behavioral approach to time, not a medical treatment or pharmacological property. Semantic error: 'polychronic' applies to human behavior and cultural attitudes toward time, not physical engineering materials.",
  "target_word": "polychronic"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "polychronic",
  "relation": "antonym",
  "options": [
    "synchronous",
    "monochronic",
    "chronic",
    "episodic"
  ],
  "correct_answer": "monochronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Describing a way of doing several things at once, not following a strict schedule.",
      "explanation": "antonym: describes doing one thing at a time on a strict schedule, the direct opposite of polychronic"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The polychronic sculpture was painted in vibrant shades of red, blue, and gold to represent different historical eras.",
      "is_correct": false
    },
    {
      "text": "He took a polychronic nap, sleeping for exactly twenty minutes before his alarm went off.",
      "is_correct": false
    },
    {
      "text": "The polychronic diet requires you to eat only one type of food group per day to improve digestion.",
      "is_correct": false
    },
    {
      "text": "They adapted to the polychronic routine by keeping their minds open to sudden changes.",
      "is_correct": true
    }
  ],
  "explanation": "Incorrect: Uses the word to mean 'multicolored' (confusing it with polychromatic), rather than relating to time management. Incorrect: Misapplies the term to a brief, strictly timed physical rest, ignoring its definition regarding multitasking and fluid schedules. Incorrect: Uses the word to mean 'single-focus' or 'restricted', which is the exact opposite of doing several things at once.",
  "target_word": "polychronic"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "polychronic",
  "relation": "antonym",
  "options": [
    "monochronic",
    "diachronic",
    "chronic",
    "synchronous"
  ],
  "correct_answer": "monochronic",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Describing a way of doing several things at once, not following a strict schedule.",
      "explanation": "genuine antonym: describes doing one thing at a time on a strict schedule"
    }
  }
}
```

---

## sense 15216, level 3

#### Pack A
### Level 3 (sense 15216, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Because she was working in a ___ office, she focused on finishing her report before starting her emails.",
  "original_sentence": "Because she was working in a monochronic office, she focused on finishing her report before starting her emails.",
  "correct_answer": "monochronic",
  "options": [
    "polychronic",
    "sporadic",
    "monochronic",
    "synchronous"
  ],
  "explanation": "Correct: 'monochronic office' describes a workplace culture where tasks are handled one at a time in sequence.",
  "distractor_tags": {},
  "word_definition": "Monochronic describes a way of managing time where you focus on one task or event at a time, following a schedule.",
  "target_word": "monochronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They designed a ___ study plan to help students manage their homework effectively.",
  "original_sentence": "They designed a monochronic study plan to help students manage their homework effectively.",
  "correct_answer": "monochronic",
  "options": [
    "chronic",
    "spontaneous",
    "monochronic",
    "monotonous"
  ],
  "explanation": "Correct: 'Monochronic' perfectly fits the context of a study plan designed to manage homework effectively by focusing on one task at a time.",
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
