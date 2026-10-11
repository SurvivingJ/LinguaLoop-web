# Pairwise review pack 05

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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The way coffee is prepared and consumed varies ___ across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "original_sentence": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
  "correct_answer": "enormously",
  "options": [
    "virtually",
    "namely",
    "chronically",
    "enormously"
  ],
  "explanation": "Correct: 'Enormously' correctly modifies the verb 'varies' to indicate a very great degree of difference across cultures.",
  "distractor_tags": {},
  "word_definition": "To a very great degree or extent.",
  "target_word": "enormously"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "He was working ___ hard to finish the assignment before the deadline.",
  "original_sentence": "He was working enormously hard to finish the assignment before the deadline.",
  "correct_answer": "enormously",
  "options": [
    "barely",
    "enormously",
    "slightly",
    "loudly"
  ],
  "explanation": "Correct: Modifies the adjective 'hard' to indicate a very great degree of effort.",
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

## sense 14390, level 6

#### Pack A
### Level 6 (sense 14390, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Prices for everyday goods have increased enormously over the past few years.",
      "is_correct": true
    },
    {
      "text": "The tiny, delicate snowflake was enormously large and covered the entire driveway.",
      "is_correct": false
    },
    {
      "text": "He was enormously asleep during the entire three-hour lecture.",
      "is_correct": false
    },
    {
      "text": "She enormously the heavy boxes up the stairs because she was in a hurry.",
      "is_correct": false
    }
  ],
  "explanation": "Grammatical error: 'Enormously' is an adverb and cannot function as the main transitive verb of the sentence. Semantic contradiction: 'Enormously' means to a very great degree, which directly contradicts the adjectives 'tiny' and 'delicate' used to describe the snowflake. Collocational/Aspectual error: 'Asleep' is a stative adjective describing a state of being. 'Enormously' modifies dynamic verbs or gradable adjectives (like 'helpful' or 'hard'), not absolute states like sleep.",
  "target_word": "enormously"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "enormously",
  "relation": "antonym",
  "options": [
    "somewhat",
    "slightly",
    "rapidly",
    "entirely"
  ],
  "correct_answer": "slightly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "To a very great degree or extent.",
      "explanation": "antonym: to a very small degree, the opposite of to a very great degree"
    }
  }
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

## sense 14390, level 7

#### Pack A
### Level 7 (sense 14390, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Her confidence improved enormously after she practiced her presentation several times.",
      "is_correct": true
    },
    {
      "text": "The new software is enormously than the old version.",
      "is_correct": false,
      "error_description": "The adverb 'enormously' cannot directly modify a comparative adjective without an intervening adjective or adverb like 'better' or 'more'. It requires an adjective to modify, such as 'enormously better' or 'enormously larger'."
    },
    {
      "text": "The way coffee is prepared and consumed varies enormously across cultures and regions, from strong, espresso-based drinks in Southern Europe to filter coffee in North America and functional beverages in various markets.",
      "is_correct": true
    },
    {
      "text": "The local community benefited enormously from the new library and community center.",
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
      "text": "He was working enormously hard to finish the assignment before the deadline.",
      "is_correct": true
    },
    {
      "text": "Weather conditions can influence outdoor sports events enormously during the winter season.",
      "is_correct": true
    },
    {
      "text": "Her enormously effort in the community project was finally recognized by the manager.",
      "is_correct": false,
      "error_description": "The word 'enormously' is an adverb and cannot be used to directly modify a noun. The adjective form 'enormous' must be used to modify the noun 'effort'."
    },
    {
      "text": "The school team played enormously well during the championship match.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 14390, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `3`
```json
{
  "sentences": [
    {
      "text": "The weather can affect your mood enormously during the winter months.",
      "is_correct": true
    },
    {
      "text": "Our understanding of space has expanded enormously thanks to modern telescopes.",
      "is_correct": true
    },
    {
      "text": "Students benefited enormously from the extra tutoring sessions before the exam.",
      "is_correct": true
    },
    {
      "text": "The weather can affect enormously your mood during the winter months.",
      "is_correct": false,
      "error_description": "The adverb 'enormously' is incorrectly placed between the transitive verb 'affect' and its direct object 'your mood'. Adverbs should not separate a verb from its direct object."
    }
  ]
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
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "___, it got better.",
  "original_sentence": "Over time, it got better.",
  "correct_answer": "Over time",
  "options": [
    "In the room",
    "Suddenly",
    "With effort",
    "Over time"
  ],
  "explanation": "Correct: 'Over time' means gradually, fitting the context of gradual improvement.",
  "distractor_tags": {},
  "word_definition": "Gradually, as time goes by.",
  "target_word": "Over time"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Feelings of sadness often lessen ___ for most teenagers.",
  "original_sentence": "Feelings of sadness often lessen over time for most teenagers.",
  "correct_answer": "over time",
  "options": [
    "over time",
    "by chance",
    "at once",
    "suddenly"
  ],
  "explanation": "Correct: This adverbial phrase perfectly expresses the gradual lessening of sadness as time passes.",
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
      "text": "Over time, the number three became the number five instantly.",
      "is_correct": false
    },
    {
      "text": "Old buildings can wear down significantly over time due to weather.",
      "is_correct": true
    },
    {
      "text": "Over time, the rock was already millions of years old before it formed.",
      "is_correct": false
    },
    {
      "text": "She over time the book on the table.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'over time' implies gradual change, but 'instantly' contradicts this by indicating immediate change. Grammatically inappropriate: 'over time' is an adverbial phrase and cannot function as a transitive verb taking a direct object. Semantically inappropriate: 'over time' describes a process of gradual change, but the sentence describes a static state that existed before any process began.",
  "target_word": "over time"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Over time",
  "relation": "antonym",
  "options": [
    "permanently",
    "suddenly",
    "eventually",
    "occasionally"
  ],
  "correct_answer": "suddenly",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Gradually, as time goes by.",
      "explanation": "antonym: implies immediate occurrence rather than gradual change over a period"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We realized that our worries had disappeared over time.",
      "is_correct": true
    },
    {
      "text": "Over time, he immediately realized his mistake and apologized.",
      "is_correct": false
    },
    {
      "text": "Over time, the lightbulb instantly shattered into a million pieces.",
      "is_correct": false
    },
    {
      "text": "She finished the entire math test over time in just five minutes.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Over time' implies a gradual process, which directly contradicts the instantaneous action of 'instantly shattered'. Semantically inappropriate: 'Over time' means gradually as time goes by, which clashes with the rapid, completed timeframe of 'in just five minutes'. Pragmatically inappropriate: The gradual progression implied by 'over time' is logically incompatible with the sudden, instantaneous realization denoted by 'immediately'.",
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

## sense 14473, level 7

#### Pack A
### Level 7 (sense 14473, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Over time, it got better.",
      "is_correct": true
    },
    {
      "text": "You will notice your skills improving slowly over time.",
      "is_correct": true
    },
    {
      "text": "Over time, she will getting better at speaking English fluently.",
      "is_correct": false,
      "error_description": "After the modal verb 'will,' the base form of the verb must be used ('get'), not the present participle ('getting'). The phrase 'over time' is correctly placed, but the verb form following 'will' is incorrect."
    },
    {
      "text": "Her confidence grew over time as she practiced speaking in front of the class.",
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
      "text": "His attitude toward studying changed completely over time.",
      "is_correct": true
    },
    {
      "text": "Feelings of sadness often lessen over time for most teenagers.",
      "is_correct": true
    },
    {
      "text": "We realized that our worries had disappeared over time.",
      "is_correct": true
    },
    {
      "text": "Over time, she is understanding the complex math concepts perfectly.",
      "is_correct": false,
      "error_description": "The adverbial phrase 'over time' describes a gradual process or change, which requires a verb tense that reflects progression or completion (such as past simple, present perfect, or 'came to + verb'), rather than the present continuous tense ('is understanding') which describes an action happening right now."
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
    "stanzas",
    "glyphs",
    "chords",
    "neumes"
  ],
  "explanation": "Correct: 'neumes' refers to medieval musical notation symbols, fitting the historical context of the 9th century.",
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
  "sentence_with_blank": "The music historian studied every single ___ written on the ancient parchment.",
  "original_sentence": "The music historian studied every single neume written on the ancient parchment.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neume",
    "neume's",
    "neumes'",
    "neumes"
  ],
  "explanation": "singular noun required by the quantifier 'every single'",
  "word_definition": "A symbol used in medieval musical notation to indicate pitch and rhythm.",
  "target_word": "neume"
}
```
**morphology_slot** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "The choir director explained how each ___ represented a specific vocal movement.",
  "original_sentence": "The choir director explained how each neume represented a specific vocal movement.",
  "correct_answer": "neume",
  "base_form": "neume",
  "form_label": "singular",
  "options": [
    "neume",
    "neumes",
    "neume's",
    "neumes'"
  ],
  "explanation": "singular form required by the distributive determiner 'each'",
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
      "text": "The gardener planted neumes along the border of the flower bed.",
      "is_correct": false
    },
    {
      "text": "Without modern staff lines, these early neumes guided the choir through the melody.",
      "is_correct": true
    },
    {
      "text": "The chef sprinkled neumes over the pasta like dried herbs.",
      "is_correct": false
    },
    {
      "text": "She wore a necklace made of golden neumes to the formal dinner.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: neumes are abstract musical notation symbols, not physical objects that can be sprinkled as a garnish. Pragmatically inappropriate: neumes are notional symbols written on manuscripts, not physical jewelry items one can wear. Pragmatically inappropriate: neumes are written musical symbols, not seeds or plants that can be cultivated in a garden.",
  "target_word": "neumes"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The chef sprinkled the neumes over the pasta like a fine, musical seasoning.",
      "is_correct": false
    },
    {
      "text": "The neumes barked loudly at the mailman when he approached the front door.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful necklace made of polished neumes that sparkled in the sun.",
      "is_correct": false
    },
    {
      "text": "He had never seen such an elaborate neume in any other manuscript.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: Neumes are visual symbols for musical notation, not physical objects that can be used as food seasoning. Semantically inappropriate: Neumes are ink symbols drawn on parchment, not physical gemstones or beads that can be carved into jewelry. Semantically inappropriate: Neumes are inanimate written symbols, not living animals capable of barking.",
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
      "text": "Monks drew each neume carefully above the sacred Latin lyrics.",
      "is_correct": true
    },
    {
      "text": "The ancient neumes was difficult to read without the modern staff lines.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the plural subject 'neumes' requires the plural verb 'were' instead of the singular 'was'."
    },
    {
      "text": "Around the 9th century, the development of neumes marked a crucial step forward.",
      "is_correct": true
    },
    {
      "text": "The music historian studied every single neume written on the ancient parchment.",
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
      "text": "He had never seen such an elaborate neume in any other manuscript.",
      "is_correct": true
    },
    {
      "text": "The choir director explained how each neume represented a specific vocal movement.",
      "is_correct": true
    },
    {
      "text": "A faded neume near the top of the page puzzled the young scholar.",
      "is_correct": true
    },
    {
      "text": "The ancient neumes was difficult for the modern choir to interpret correctly.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: the plural subject 'neumes' requires the plural verb 'were' instead of the singular 'was'."
    }
  ]
}
```

---
