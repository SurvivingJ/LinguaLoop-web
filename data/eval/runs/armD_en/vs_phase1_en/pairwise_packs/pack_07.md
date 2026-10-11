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


## sense 19521, level 3

#### Pack A
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She celebrated her ___ birthday with a big party.",
  "original_sentence": "She celebrated her nineteenth birthday with a big party.",
  "correct_answer": "nineteenth",
  "options": [
    "nineteenth",
    "twentieth",
    "continuous",
    "biannual"
  ],
  "explanation": "Correct ordinal adjective indicating the specific age being celebrated.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "They are studying ___-century history in social studies class.",
  "original_sentence": "They are studying nineteenth-century history in social studies class.",
  "correct_answer": "nineteenth",
  "options": [
    "umpteenth",
    "several",
    "nineteenth",
    "hourly"
  ],
  "explanation": "Correct ordinal adjective for the century.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```

#### Pack B
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She celebrated her ___ birthday with a big party.",
  "original_sentence": "She celebrated her nineteenth birthday with a big party.",
  "correct_answer": "nineteenth",
  "options": [
    "nineteenth",
    "primary",
    "annual",
    "major"
  ],
  "explanation": "Correct: 'Nineteenth' is the exact ordinal adjective needed to specify the 19th occurrence of her birthday.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "For her ___ project, she decided to build a website.",
  "original_sentence": "For her nineteenth project, she decided to build a website.",
  "correct_answer": "nineteenth",
  "options": [
    "nineteen's",
    "nineteen",
    "ninetieth",
    "nineteenth"
  ],
  "explanation": "Correct: 'Nineteenth' is the correct ordinal number indicating the sequence of her project.",
  "distractor_tags": {},
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```

---

## sense 19521, level 4

#### Pack A
### Level 4 (sense 19521, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "We are reading the ___ chapter of the novel today.",
  "original_sentence": "We are reading the nineteenth chapter of the novel today.",
  "required_pos": "adjective",
  "options": [
    "nineteenthly",
    "nineteenth",
    "nineteenal",
    "nineteenment"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal form derived from nineteen with -th"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "They have reached the ___ hole on the golf course.",
  "original_sentence": "They have reached the nineteenth hole on the golf course.",
  "required_pos": "adjective",
  "options": [
    "nineteenify",
    "nineteenthness",
    "nineteenthment",
    "nineteenth"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the established ordinal adjective formed with -th"
    }
  }
}
```

#### Pack B
### Level 4 (sense 19521, difficulty None)
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "He is reading the ___ chapter of the book.",
  "original_sentence": "He is reading the nineteenth chapter of the book.",
  "required_pos": "adjective",
  "options": [
    "nineteenment",
    "nineteenth",
    "nineteenic",
    "nineteenation"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal adjective formed by adding -th to the cardinal nineteen"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "I noticed the ___ item on the list was missing.",
  "original_sentence": "I noticed the nineteenth item on the list was missing.",
  "required_pos": "adjective",
  "options": [
    "nineteenth",
    "nineteenic",
    "nineteenal",
    "nineteenment"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal adjective formed from nineteen with the -th suffix"
    }
  }
}
```

---

## sense 19521, level 6

#### Pack A
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nineteenth color of the rainbow is a deep shade of purple.",
      "is_correct": false
    },
    {
      "text": "He felt a nineteenth emotion when he heard the tragic news.",
      "is_correct": false
    },
    {
      "text": "Our school team won its nineteenth game of the season.",
      "is_correct": true
    },
    {
      "text": "The nineteenth ingredient in the recipe is a pinch of salt.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Recipes are procedural sequences, not typically counted up to nineteen in a way that highlights the nineteenth step as a distinct milestone. Semantically inappropriate: Human emotions are not conventionally categorized or counted as a discrete, numbered sequence up to nineteen. Semantically inappropriate: The rainbow is universally recognized as having only seven colors, making a 'nineteenth' color physically and conceptually impossible.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She nineteenth the book on the table.",
      "is_correct": false
    },
    {
      "text": "He felt very nineteenth after eating the large meal.",
      "is_correct": false
    },
    {
      "text": "I am currently reading the nineteenth page of the assignment.",
      "is_correct": true
    },
    {
      "text": "The nineteenth liquid in the glass was water.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Ordinal numbers like 'nineteenth' denote sequence or order, not the physical state or identity of a substance like a liquid. Semantically inappropriate: 'Nineteenth' is an ordinal adjective and cannot be used as a predicate adjective to describe a physical or emotional state. Grammatically inappropriate: 'Nineteenth' is an adjective and cannot function as a transitive verb to take a direct object like 'the book'.",
  "target_word": "nineteenth"
}
```

#### Pack B
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Our team finished in nineteenth place during the tournament.",
      "is_correct": true
    },
    {
      "text": "The nineteenth letter of the English alphabet is 'Z'.",
      "is_correct": false
    },
    {
      "text": "He was the nineteenth person to walk on the moon.",
      "is_correct": false
    },
    {
      "text": "The nineteenth day of the week is dedicated to resting.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic: logically impossible and pragmatically inappropriate because there are only seven days in a standard week. Semantic: factually incorrect and pragmatically inappropriate since only twelve people have walked on the moon to date. Semantic: factually incorrect as the nineteenth letter of the alphabet is 'S', not 'Z'.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "His artwork was featured on the nineteenth page of the magazine.",
      "is_correct": true
    },
    {
      "text": "The nineteenth side of the square was painted a bright blue color.",
      "is_correct": false
    },
    {
      "text": "She carefully poured the nineteenth water into the mixing bowl.",
      "is_correct": false
    },
    {
      "text": "The nineteenth month of the year always brings the first snow.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: there are only twelve months in a year, making a nineteenth month logically impossible. semantic: 'water' is an uncountable mass noun and cannot be sequentially enumerated with an ordinal number. semantic: a square is geometrically defined as having exactly four sides, so a nineteenth side cannot exist.",
  "target_word": "nineteenth"
}
```

---

## sense 19521, level 7

#### Pack A
### Level 7 (sense 19521, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "We are reading the nineteenth chapter of the novel today.",
      "is_correct": true
    },
    {
      "text": "She celebrated her nineteenth birthday with a big party.",
      "is_correct": true
    },
    {
      "text": "Nineteenth of the students in the class were absent today.",
      "is_correct": false,
      "error_description": "The sentence incorrectly uses the ordinal number 'nineteenth' instead of the cardinal number 'nineteen' to express a specific quantity or count of students."
    },
    {
      "text": "The museum is hosting an exhibition about nineteenth-century art.",
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
      "text": "I am currently reading the nineteenth page of the assignment.",
      "is_correct": true
    },
    {
      "text": "They have reached the nineteenth hole on the golf course.",
      "is_correct": true
    },
    {
      "text": "She was born in the nineteenth of May, 1998.",
      "is_correct": false,
      "error_description": "When referring to a specific day of the month using an ordinal number, the correct preposition is 'on' rather than 'in'."
    },
    {
      "text": "For her nineteenth project, she decided to build a website.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 19521, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She celebrated her nineteenth birthday with a big party.",
      "is_correct": true
    },
    {
      "text": "He lives on nineteenth floor of the building.",
      "is_correct": false,
      "error_description": "Ordinal numbers modifying a singular noun require the definite article 'the', which is missing in the incorrect sentence."
    },
    {
      "text": "He is reading the nineteenth chapter of the book.",
      "is_correct": true
    },
    {
      "text": "That building was constructed in the nineteenth century.",
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
      "text": "She was nineteenth person to arrive at the meeting.",
      "is_correct": false,
      "error_description": "The definite article 'the' is missing before the ordinal adjective 'nineteenth'."
    },
    {
      "text": "They are studying nineteenth-century history in social studies class.",
      "is_correct": true
    },
    {
      "text": "I noticed the nineteenth item on the list was missing.",
      "is_correct": true
    },
    {
      "text": "His artwork was featured on the nineteenth page of the magazine.",
      "is_correct": true
    }
  ]
}
```

---

## sense 40142, level 1

#### Pack A
### Level 1 (sense 40142, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "ipa": "/ɡreɪt wɔːl ɒv ˈtʃaɪnə/",
  "syllable_count": 4,
  "audio_url": null,
  "options": [
    "Great Wall of Chino",
    "Great Wall of China",
    "Grate Wall of China",
    "Great Well of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "Correct: This is the exact spelling of the target phrase.",
  "distractor_explanations": {
    "Grate Wall of China": "Homophone: 'Grate' sounds exactly like 'Great' but refers to a metal frame or shredding food.",
    "Great Well of China": "Minimal pair: 'Well' differs from 'Wall' by only one vowel sound (/ɛ/ vs /ɔː/).",
    "Great Wall of Chino": "Near-homophone: 'Chino' sounds very similar to 'China' but refers to a type of cotton fabric or pants."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 40142, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Great Wall of China",
  "pronunciation": "grayt wawl ov chy-nuh",
  "ipa": "/ɡreɪt wɔːl ɒv ˈtʃaɪnə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Great Wall of Chino",
    "Great Wall of China",
    "Grate Wall of China",
    "Great Whale of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "This is the exact correct spelling and pronunciation of the target proper noun phrase.",
  "distractor_explanations": {
    "Grate Wall of China": "homophone: 'grate' has the exact same /ɡreɪt/ sound as 'great', but different spelling and meaning.",
    "Great Whale of China": "minimal pair: 'whale' differs from 'wall' only in the vowel sound /iː/ versus /ɔː/.",
    "Great Wall of Chino": "near-homophone: 'chino' sounds very similar to 'China', differing only in the final vowel /oʊ/ versus /ə/."
  },
  "distractor_source": "llm"
}
```

---

## sense 40142, level 3

#### Pack A
### Level 3 (sense 40142, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Many tourists visit the ___ every year to see its incredible history.",
  "original_sentence": "Many tourists visit the Great Wall of China every year to see its incredible history.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Great Wall of China",
    "corporate headquarters",
    "Great Barrier Reef",
    "local shopping mall"
  ],
  "explanation": "This is the exact target phrase required to complete the sentence logically and grammatically.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Guard towers were placed at regular intervals along the ___ for defense.",
  "original_sentence": "Guard towers were placed at regular intervals along the Great Wall of China for defense.",
  "correct_answer": "Great Wall of China",
  "options": [
    "the Great Pyramid of Giza",
    "the big fence",
    "the Silk Road",
    "Great Wall of China"
  ],
  "explanation": "This is the correct historical structure located in China, fitting the context of guard towers and defense.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```

#### Pack B
### Level 3 (sense 40142, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The ___ is one of the most famous historical landmarks in the world.",
  "original_sentence": "The Great Wall of China is one of the most famous historical landmarks in the world.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Great Wall of China",
    "Eiffel Tower",
    "Great Barrier Reef",
    "Berlin Wall"
  ],
  "explanation": "Correct: This is the specific historical landmark referenced in the sentence.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "People often wonder if the ___ can actually be seen from outer space.",
  "original_sentence": "People often wonder if the Great Wall of China can actually be seen from outer space.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Eiffel Tower",
    "Great Wall of China",
    "Maginot Line",
    "Berlin Wall"
  ],
  "explanation": "Correct: This is the specific historical landmark that people debate seeing from space.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```

---

## sense 40142, level 6

#### Pack A
### Level 6 (sense 40142, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She packed the Great Wall of China in her suitcase to take it home as a souvenir.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China was constructed entirely out of modern steel and glass in the 1990s.",
      "is_correct": false
    },
    {
      "text": "People say that the Great Wall of China is so long that it took centuries to finish.",
      "is_correct": true
    },
    {
      "text": "I used the Great Wall of China to block the wind from my backyard garden.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: the scale of the structure makes it absurd to use for a small backyard. Semantically inappropriate: contradicts the historical fact that it was built a long time ago using ancient materials. Pragmatically inappropriate: it is physically impossible to pack a massive geographical structure in a suitcase.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China was built last week using modern plastic and steel.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China is a popular type of spicy noodle soup served in Beijing restaurants.",
      "is_correct": false
    },
    {
      "text": "I keep my digital passwords stored safely inside the Great Wall of China.",
      "is_correct": false
    },
    {
      "text": "My older brother dreams of hiking along the entire length of the Great Wall of China.",
      "is_correct": true
    }
  ],
  "explanation": "semantic: incorrectly categorizes the Great Wall of China as a food item rather than a physical historical structure. pragmatic: inappropriately treats a physical, ancient monument as a digital storage device for computer passwords. semantic: contradicts the historical and material reality of the target word, which is an ancient structure made of stone and brick.",
  "target_word": "Great Wall of China"
}
```

#### Pack B
### Level 6 (sense 40142, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She wore a beautiful Great Wall of China to the formal evening gala.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China is a delicious traditional dish served at many Chinese restaurants.",
      "is_correct": false
    },
    {
      "text": "Walking along the Great Wall of China can be quite tiring because of the steep stairs.",
      "is_correct": true
    },
    {
      "text": "I built a small Great Wall of China in my backyard using plastic bricks and toy soldiers.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The Great Wall of China is a massive, singular historical monument, not a small toy model. Semantically inappropriate: The target word is a physical stone structure, not a type of food or culinary recipe. Semantically inappropriate: The target word is a massive architectural landmark, not an item of clothing or fashion.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China is a delicious dessert made with sweet rice and red beans.",
      "is_correct": false
    },
    {
      "text": "I keep my Great Wall of China in my pocket to pay for the bus.",
      "is_correct": false
    },
    {
      "text": "Local governments work hard to preserve the remaining sections of the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China barks loudly whenever the mail carrier arrives.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: The Great Wall of China is a massive stone structure, not a food item. semantic: The Great Wall of China is a gigantic geographical landmark, not a small coin or piece of currency. semantic: The Great Wall of China is an inanimate architectural structure, not a living animal.",
  "target_word": "Great Wall of China"
}
```

---

## sense 40142, level 7

#### Pack A
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Ancient emperors ordered the construction of the Great Wall of China to protect their lands.",
      "is_correct": true
    },
    {
      "text": "My biggest dream is to visit Great Wall of China before I graduate from college.",
      "is_correct": false,
      "error_description": "The proper noun 'Great Wall of China' requires the definite article 'the' before it, as it refers to a specific, unique historical structure rather than a general concept."
    },
    {
      "text": "The Great Wall of China is one of the most famous historical landmarks in the world.",
      "is_correct": true
    },
    {
      "text": "Many tourists visit the Great Wall of China every year to take amazing photographs.",
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
      "text": "Local governments work hard to preserve the remaining sections of the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "Many people dream of visiting Great Wall of China at least once in their lifetime.",
      "is_correct": false,
      "error_description": "The specific landmark name 'Great Wall of China' requires the definite article 'the' before it when used as the object of a preposition."
    },
    {
      "text": "People often wonder if the Great Wall of China can actually be seen from outer space.",
      "is_correct": true
    },
    {
      "text": "Schools teach students about the history and significance of the Great Wall of China.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "My friend wants to travel to Great Wall of China next year.",
      "is_correct": false,
      "error_description": "The proper noun phrase 'Great Wall of China' requires the definite article 'the' before it."
    },
    {
      "text": "Have you ever seen pictures of the Great Wall of China winding across the mountains?",
      "is_correct": true
    },
    {
      "text": "My history teacher explained how the ancient emperors built the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "Many tourists visit the Great Wall of China every year to see its incredible history.",
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
      "text": "The Great Wall of China were built over many centuries to protect the empire.",
      "is_correct": false,
      "error_description": "The subject 'The Great Wall of China' is a singular noun phrase, so it requires the singular verb 'was' instead of the plural verb 'were'."
    },
    {
      "text": "Guard towers were placed at regular intervals along the Great Wall of China for defense.",
      "is_correct": true
    },
    {
      "text": "During our geography lesson, we located the famous Great Wall of China on the map.",
      "is_correct": true
    },
    {
      "text": "My older brother dreams of hiking along the entire length of the Great Wall of China.",
      "is_correct": true
    }
  ]
}
```

---

## sense 40248, level 3

#### Pack A
### Level 3 (sense 40248, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "Historians often study the ___ to understand how modern nations developed their borders.",
  "original_sentence": "Historians often study the Peace of Westphalia to understand how modern nations developed their borders.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Treaty of Versailles",
    "peacefulness",
    "Peace of Westphalia",
    "Magna Carta"
  ],
  "explanation": "Correct: This is the specific 1648 treaty that established modern state borders.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Few treaties had as much influence on international law as the ___.",
  "original_sentence": "Few treaties had as much influence on international law as the Peace of Westphalia.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Treaty of Versailles",
    "Magna Carta",
    "Treaty of Tordesillas",
    "Peace of Westphalia"
  ],
  "explanation": "Correct: the historical treaty that profoundly shaped international law.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```

#### Pack B
### Level 3 (sense 40248, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "History students often discuss the ___ because it changed how countries govern themselves.",
  "original_sentence": "History students often discuss the Peace of Westphalia because it changed how countries govern themselves.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "school rules",
    "Industrial Revolution",
    "the handshake",
    "Peace of Westphalia"
  ],
  "explanation": "Correct: the specific historical treaty that established the modern concept of national sovereignty.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Before the ___, outside powers often interfered in internal religious matters.",
  "original_sentence": "Before the Peace of Westphalia, outside powers often interfered in internal religious matters.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "armistice",
    "Peace of Westphalia",
    "peace deal",
    "Treaty of Paris"
  ],
  "explanation": "Correct: This is the specific 1648 treaty that established state sovereignty and ended the Thirty Years' War, fitting the historical context perfectly.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 6

#### Pack A
### Level 6 (sense 40248, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I signed the Peace of Westphalia at the bottom of my math homework to show I was done.",
      "is_correct": false
    },
    {
      "text": "The Peace of Westphalia tasted like sweet strawberries and fresh cream.",
      "is_correct": false
    },
    {
      "text": "During class, we discussed why the Peace of Westphalia was signed in 1648.",
      "is_correct": true
    },
    {
      "text": "My dog buried the Peace of Westphalia in the backyard next to his favorite bone.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The target is a major 17th-century historical treaty, not a personal signature or a casual stamp of approval. Semantically inappropriate: The target is an abstract historical agreement and cannot be eaten or possess a physical flavor. Pragmatically inappropriate: The target is a monumental diplomatic treaty, not a physical object like a bone that a dog could bury.",
  "target_word": "Peace of Westphalia"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Peace of Westphalia is a popular brand of German beer sold in supermarkets.",
      "is_correct": false
    },
    {
      "text": "By ending decades of conflict, the Peace of Westphalia allowed kingdoms to rebuild.",
      "is_correct": true
    },
    {
      "text": "The Peace of Westphalia barked loudly at the mailman every morning.",
      "is_correct": false
    },
    {
      "text": "She added the Peace of Westphalia to her soup recipe for extra flavor.",
      "is_correct": false
    }
  ],
  "explanation": "Semantic: 'Peace of Westphalia' refers to a historical treaty, not a commercial product or brand name. Semantic: 'Peace of Westphalia' is an abstract historical agreement, not a physical ingredient that can be used in cooking. Semantic: 'Peace of Westphalia' is a treaty, not a living creature capable of barking.",
  "target_word": "Peace of Westphalia"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "relation": "antonym",
  "options": [
    "Treaty of Versailles",
    "Congress of Vienna",
    "Magna Carta",
    "Thirty Years' War"
  ],
  "correct_answer": "Thirty Years' War",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "A big agreement that ended a war and said each country can make its own rules.",
      "explanation": "antonym: the prolonged conflict the treaty ended, representing war rather than peace"
    }
  }
}
```

#### Pack B
### Level 6 (sense 40248, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "To resolve the argument over who gets the last slice of pizza, my roommates drafted the Peace of Westphalia.",
      "is_correct": false
    },
    {
      "text": "The Peace of Westphalia is a popular flavor of ice cream in European countries during the summer.",
      "is_correct": false
    },
    {
      "text": "We will sign the Peace of Westphalia tomorrow to finalize the construction permits for the new shopping mall.",
      "is_correct": false
    },
    {
      "text": "By signing the Peace of Westphalia, nations agreed to respect each other's independence.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: trivializes a major geopolitical treaty by applying it to a petty domestic squabble. Semantically inappropriate: incorrectly categorizes a historical treaty and political agreement as a physical dessert. Semantically and pragmatically inappropriate: uses a specific 17th-century treaty ending the Thirty Years' War as a standard modern zoning document.",
  "target_word": "Peace of Westphalia"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The delegates will sign the Peace of Westphalia tomorrow to resolve the current international trade dispute.",
      "is_correct": false
    },
    {
      "text": "I added a pinch of salt and the Peace of Westphalia to the soup to enhance the flavor.",
      "is_correct": false
    },
    {
      "text": "They had already examined the Peace of Westphalia before starting the new unit on diplomacy.",
      "is_correct": true
    },
    {
      "text": "The two siblings agreed to the Peace of Westphalia to decide who would wash the dishes tonight.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The Peace of Westphalia is a specific historical event from 1648, not a generic template that can be signed today to resolve modern trade disputes. Semantically inappropriate: The Peace of Westphalia is an abstract historical agreement, not a physical object or ingredient that can be added to food. Pragmatically inappropriate: Applying a major international geopolitical treaty to a trivial household chore is a severe context and scale mismatch.",
  "target_word": "Peace of Westphalia"
}
```

---
