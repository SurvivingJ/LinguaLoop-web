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


## sense 14390, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 14390, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Scientists were ___ surprised by the unusual data collected from the deep ocean trench.",
  "original_sentence": "Scientists were enormously surprised by the unusual data collected from the deep ocean trench.",
  "correct_answer": "enormously",
  "options": [
    "slightly",
    "legally",
    "physically",
    "enormously"
  ],
  "explanation": "Correct: fits the context of a high degree of surprise.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```

---

## sense 14390, level 6

#### Pack A
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Enormously popular among teenagers, the new fantasy novel sold out within hours of its release.",
      "is_correct": true
    },
    {
      "text": "He was enormously identical to his twin brother.",
      "is_correct": false
    },
    {
      "text": "She enormously knew the answer to the question.",
      "is_correct": false
    },
    {
      "text": "The ant was enormously small compared to the elephant.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Enormously' implies a very great degree, which conflicts with the concept of 'small'. One would use 'tiny' or 'minutely', not an intensifier associated with bigness, for something inherently small. Semantically inappropriate: 'Identical' is an absolute state (binary); it cannot be modified by a degree adverb like 'enormously'. Something is either identical or it is not. Collocationally/Semantically inappropriate: 'Know' is a stative verb representing a binary state of awareness. It does not accept degree modifiers like 'enormously' because knowledge is not typically viewed as having variable magnitude in this context.",
  "target_word": "Enormously"
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

## sense 14473, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 14473, difficulty None)
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The heavy rain carved a deep path into the hill ___.",
  "original_sentence": "The heavy rain carved a deep path into the hill over time.",
  "correct_answer": "over time",
  "options": [
    "instantly",
    "reluctantly",
    "over time",
    "loudly"
  ],
  "explanation": "Correct: fits the context of gradual erosion caused by rain.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "over time"
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
      "text": "Old buildings can wear down over time due to bad weather.",
      "is_correct": true
    },
    {
      "text": "She decided to accept the job offer over time.",
      "is_correct": false
    },
    {
      "text": "The bomb exploded over time.",
      "is_correct": false
    },
    {
      "text": "He finished the race over time.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'over time' implies a long, gradual duration, which conflicts with the typical goal of finishing a race quickly or within a specific limit. Semantically inappropriate: explosions are instantaneous events, making the gradual aspect of 'over time' logically contradictory. Pragmatically inappropriate: decisions are typically punctual mental acts; while deliberation takes time, the act of deciding is not usually described as happening gradually 'over time' in this phrasing.",
  "target_word": "over time"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She decided to quit her job over time during the meeting.",
      "is_correct": false
    },
    {
      "text": "He arrived at the station over time to catch the 8:05 train.",
      "is_correct": false
    },
    {
      "text": "The bomb exploded over time, destroying the building in a split second.",
      "is_correct": false
    },
    {
      "text": "People often change their opinions about important issues over time.",
      "is_correct": true
    }
  ],
  "explanation": "Semantic contradiction: 'exploded' and 'split second' denote instantaneous events, incompatible with the gradual nature of 'over time'. Pragmatic inappropriate: Arrival for a specific scheduled train is a punctual event, not a gradual process occurring 'over time'. Aspectual mismatch: Making a decision is typically a punctual mental act, whereas 'over time' implies a extended duration inconsistent with a single meeting context.",
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
    "concerts",
    "lyrics",
    "neumes",
    "instruments"
  ],
  "explanation": "Correct: Fits the historical context of medieval musical notation development.",
  "distractor_tags": {},
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neumes"
}
```

---

## sense 14544, level 4

#### Pack A
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

#### Pack B
### Level 4 (sense 14544, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The music historian studied every single ___ written on the old parchment.",
  "original_sentence": "The music historian studied every single neume written on the old parchment.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neumed",
    "neumes",
    "neume",
    "neuming"
  ],
  "explanation": "singular noun required by the quantifier 'every single'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Early musicians used the simple ___ system before modern musical notes were invented.",
  "original_sentence": "Early musicians used the simple neume system before modern musical notes were invented.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neumes",
    "neumed",
    "neume",
    "neuming"
  ],
  "explanation": "singular noun required by the singular determiner 'the' and modifier 'simple'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```

---

## sense 14544, level 6

#### Pack A
### Level 6 (sense 14544, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Without modern staff lines, singers relied heavily on each tiny neume to guide their voices.",
      "is_correct": true
    },
    {
      "text": "The software engineer coded a new neume to fix the database error.",
      "is_correct": false
    },
    {
      "text": "The chef added a pinch of neumes to the soup to enhance the flavor.",
      "is_correct": false
    },
    {
      "text": "She wore a diamond neume around her neck for the gala.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Neumes are abstract visual symbols for music, not physical ingredients that can be tasted or added to food. Semantically inappropriate: Neumes are ink markings on parchment, not tangible jewelry or precious stones. Register/Domain inappropriate: Neumes belong to the domain of medieval musicology, not modern computer programming or database management.",
  "target_word": "neume"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Learning to read an ancient neume takes a lot of patience and practice.",
      "is_correct": true
    },
    {
      "text": "The software developer wrote a neume in Python to fix the bug.",
      "is_correct": false
    },
    {
      "text": "He bought a new neume for his car to replace the broken tire.",
      "is_correct": false
    },
    {
      "text": "The chef added a neume of salt to the soup for better flavor.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: 'neume' is a musical symbol, not a culinary measure or ingredient. Semantic error: 'neume' is not a mechanical part or automotive component. Register/Domain error: 'neume' belongs to medieval musicology, not computer programming.",
  "target_word": "neume"
}
```

#### Pack B
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
      "text": "The choir director explained that the neumes was difficult to interpret without a staff.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: 'neumes' is a plural noun and requires the plural verb 'were', not the singular 'was'."
    },
    {
      "text": "Monks drew each neume carefully above the sacred Latin texts.",
      "is_correct": true
    },
    {
      "text": "The music historian studied every single neume written on the old parchment.",
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
      "text": "Early musicians used the simple neume system before modern musical notes were invented.",
      "is_correct": true
    },
    {
      "text": "The choir director explained that the neumes was difficult to interpret without the original staff lines.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: The plural noun 'neumes' requires the plural verb 'were', not the singular 'was'."
    },
    {
      "text": "Learning to read an ancient neume takes a lot of patience and practice.",
      "is_correct": true
    },
    {
      "text": "They examined the faded manuscript to decode the meaning of each neume.",
      "is_correct": true
    }
  ]
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
    "polychrome",
    "polytonic"
  ],
  "correct_answer": "polychronic",
  "explanation": "Correct: This is the target word.",
  "distractor_explanations": {
    "polyphonic": "Near-homophone: differs only in the medial consonant cluster /kr/ vs /f/.",
    "polychrome": "Minimal pair: differs only in the final syllable /nɪk/ vs /roʊm/.",
    "polytonic": "Rhyme: shares the same stress pattern and ending sound /-tɒnɪk/, but starts with a different prefix meaning."
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
    "polychronic",
    "monochronic",
    "synchronous",
    "anachronistic"
  ],
  "explanation": "Correct: Fits the context of cultures that embrace a fluid approach to time.",
  "distractor_tags": {},
  "word_definition": "Describing a way of doing several things at once, not following a strict schedule.",
  "target_word": "polychronic"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "While some people prefer strict schedules, ___ individuals thrive in flexible and unpredictable situations.",
  "original_sentence": "While some people prefer strict schedules, polychronic individuals thrive in flexible and unpredictable situations.",
  "correct_answer": "polychronic",
  "options": [
    "polychronic",
    "rigid",
    "lethargic",
    "punctual"
  ],
  "explanation": "Correct: Fits the context of thriving in flexible and unpredictable situations, contrasting with strict schedules.",
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

---
