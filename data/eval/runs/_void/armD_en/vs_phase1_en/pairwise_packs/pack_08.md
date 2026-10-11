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


## sense 19521, level 6

#### Pack A
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She felt a deep sense of nineteenth when she finally finished her marathon.",
      "is_correct": false
    },
    {
      "text": "The art club has been meeting every Tuesday, and today is their nineteenth session.",
      "is_correct": true
    },
    {
      "text": "He drove his car in a very nineteenth manner through the busy city streets.",
      "is_correct": false
    },
    {
      "text": "The nineteenth of the water spilled all over the kitchen floor.",
      "is_correct": false
    }
  ],
  "explanation": "Incorrect: 'Nineteenth' is strictly an ordinal adjective and cannot be used as a noun to describe an abstract feeling or emotion. Incorrect: 'Nineteenth' denotes numerical sequence, not a qualitative style or adverbial manner of behavior. Incorrect: 'Nineteenth' cannot be used as a noun to refer to a physical substance or object like water.",
  "target_word": "nineteenth"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nineteenth flavor of ice cream was so spicy that it burned my tongue.",
      "is_correct": false
    },
    {
      "text": "He was the nineteenth person to ever walk on the surface of the moon.",
      "is_correct": false
    },
    {
      "text": "The nineteenth atom in the molecule caused the entire chemical structure to collapse.",
      "is_correct": false
    },
    {
      "text": "The teacher handed out the nineteenth assignment of the semester on Friday afternoon.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: flavors of ice cream are rarely counted to nineteen in a single context, making the high ordinal number feel arbitrary and unnatural. Semantically inappropriate: contradicts real-world historical facts, as only a very small number of people (twelve) have walked on the moon. Pragmatically inappropriate: atoms in a molecule are not naturally counted or referred to by ordinal numbers in standard scientific or everyday discourse.",
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
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "They reached the nineteenth hole on the golf course as the sun began to set.",
      "is_correct": true
    },
    {
      "text": "The school has exactly nineteenth classrooms on the second floor.",
      "is_correct": false,
      "error_description": "The ordinal number 'nineteenth' is incorrectly used to express a total quantity. The cardinal number 'nineteen' must be used when counting the total number of items."
    },
    {
      "text": "The teacher handed out the nineteenth assignment of the semester on Friday afternoon.",
      "is_correct": true
    },
    {
      "text": "My cousin is currently studying chemistry during his nineteenth term at university.",
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
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Great Wall of China",
    "Great Wail of China",
    "Great Whale of China",
    "Grate Wall of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "Correct: This is the exact spelling of the target phrase you heard.",
  "distractor_explanations": {
    "Grate Wall of China": "Homophone: 'grate' sounds exactly like 'great' /ɡreɪt/, but means to shred or a metal frame.",
    "Great Whale of China": "Minimal pair: 'whale' /weɪl/ differs from 'wall' /wɔːl/ by only one vowel sound.",
    "Great Wail of China": "Near-homophone: 'wail' /weɪl/ sounds very similar to 'wall' /wɔːl/, especially in some dialects."
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
  "sentence_with_blank": "Tourists from all over the world visit the ___ every year.",
  "original_sentence": "Tourists from all over the world visit the Great Wall of China every year.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Great Wall of China",
    "Great Barrier Reef",
    "Berlin Wall",
    "Eiffel Tower"
  ],
  "explanation": "Correct: This is the specific historical landmark that tourists from all over the world visit.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Workers used stone and brick to build the ___.",
  "original_sentence": "Workers used stone and brick to build the Great Wall of China.",
  "correct_answer": "Great Wall of China",
  "options": [
    "Hadrian's Wall",
    "Berlin Wall",
    "Great Wall of China",
    "Great Barrier Reef"
  ],
  "explanation": "Correct: This is the specific historical monument built with stone and brick in China.",
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
      "text": "She kept her Great Wall of China in a small wooden box on her desk.",
      "is_correct": false
    },
    {
      "text": "You can see the Great Wall of China winding across the mountains.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China is made entirely of soft, white marshmallows.",
      "is_correct": false
    },
    {
      "text": "I used the Great Wall of China to block the wind from my garden.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The Great Wall of China is a massive, ancient, and protected historical monument, not a movable object or a small personal fence used for gardening. Semantically inappropriate: The Great Wall of China was historically constructed from stone, brick, tamped earth, and wood, not food items. Pragmatically inappropriate: The Great Wall of China is thousands of miles long and physically impossible to store in a small box on a desk.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I keep my spare keys hidden inside the Great Wall of China for safekeeping.",
      "is_correct": false
    },
    {
      "text": "The government is working hard to preserve the Great Wall of China today.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China is a delicious dessert served in traditional Chinese restaurants.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China is a tiny insect that lives in the gardens of Beijing.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The Great Wall of China is a massive historical monument, not a food item. Semantically inappropriate: The wall is thousands of miles long and made of solid stone; it cannot be used as a small personal container. Semantically inappropriate: The target refers to a colossal architectural structure, not a biological organism or insect.",
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
      "text": "Tourists from all over the world visit the Great Wall of China every year.",
      "is_correct": true
    },
    {
      "text": "Last summer, my family traveled to China and visited Great Wall of China.",
      "is_correct": false,
      "error_description": "The definite article 'the' is missing before 'Great Wall of China'. Unique landmarks and monuments typically require the definite article."
    },
    {
      "text": "Ancient emperors ordered the construction of the Great Wall of China to protect their lands.",
      "is_correct": true
    },
    {
      "text": "Many people have walked along parts of the Great Wall of China.",
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
      "text": "Great Wall of China is one of the most visited tourist attractions in the world.",
      "is_correct": false,
      "error_description": "The definite article 'the' is required before the proper noun phrase 'Great Wall of China' because it refers to a specific, unique structure."
    },
    {
      "text": "The government is working hard to preserve the Great Wall of China today.",
      "is_correct": true
    },
    {
      "text": "Workers used stone and brick to build the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "My geography teacher talked about the incredible length of the Great Wall of China.",
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

## sense 40248, level 1

#### Pack A
### Level 1 (sense 40248, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pess ov vest-FAH-lee-uh",
  "ipa": "/ˈpɛs əv vɛstˈfɑːliə/",
  "syllable_count": 6,
  "audio_url": null,
  "options": [
    "Peace of Westphalia",
    "Pace of Westphalia",
    "Piece of Westphalia",
    "Peas of Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: This is the exact spelling of the historical treaty.",
  "distractor_explanations": {
    "Piece of Westphalia": "Homophone: 'Piece' sounds identical to 'Peace' but has a different spelling and meaning.",
    "Peas of Westphalia": "Homophone: 'Peas' sounds identical to 'Peace' but refers to a vegetable.",
    "Pace of Westphalia": "Near-homophone: 'Pace' differs from 'Peace' by only one vowel sound (/eɪ/ vs /iː/)."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 40248, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pehs uhv west-FAY-lee-uh",
  "ipa": "/ˌpiːs əv wɛstˈfeɪliə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Peas of Westphalia",
    "Peace of Westphalia",
    "Pace of Westphalia",
    "Piece of Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: the exact historical name of the 1648 treaty series.",
  "distractor_explanations": {
    "Piece of Westphalia": "homophone: 'Piece' sounds identical to 'Peace' but has a different spelling and meaning.",
    "Peas of Westphalia": "homophone: 'Peas' sounds identical to 'Peace' but refers to a vegetable.",
    "Pace of Westphalia": "near-homophone: 'Pace' /peɪs/ differs from 'Peace' /piːs/ by only one vowel phoneme."
  },
  "distractor_source": "llm"
}
```

---

## sense 40248, level 3

#### Pack A
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

#### Pack B
### Level 3 (sense 40248, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The ___ changed European history by establishing the idea that nations could govern themselves.",
  "original_sentence": "The Peace of Westphalia changed European history by establishing the idea that nations could govern themselves.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Magna Carta",
    "Peace of Westphalia",
    "Declaration of Independence",
    "Treaty of Versailles"
  ],
  "explanation": "Correct: This is the specific historical treaty that established national self-governance.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Because of the ___, each participating nation gained the right to choose its own official religion.",
  "original_sentence": "Because of the Peace of Westphalia, each participating nation gained the right to choose its own official religion.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Treaty of Paris",
    "Peace of Westphalia",
    "Magna Carta",
    "Declaration of Independence"
  ],
  "explanation": "Correct: This is the exact historical treaty that granted nations the right to choose their official religion.",
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

#### Pack B
### Level 6 (sense 40248, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She wore a beautiful Peace of Westphalia to the formal dance.",
      "is_correct": false
    },
    {
      "text": "Many experts believe the Peace of Westphalia marked the beginning of our current system of independent states.",
      "is_correct": true
    },
    {
      "text": "The Peace of Westphalia was a delicious recipe for a traditional German stew.",
      "is_correct": false
    },
    {
      "text": "The Peace of Westphalia barked loudly at the mail carrier.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: The Peace of Westphalia is a historical political treaty, not a culinary dish. semantic: The Peace of Westphalia is an abstract historical agreement, not a physical garment. semantic: The Peace of Westphalia is a diplomatic treaty, not a living animal.",
  "target_word": "Peace of Westphalia"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She wore a beautiful Peace of Westphalia to the formal dance last night.",
      "is_correct": false
    },
    {
      "text": "The Peace of Westphalia barked loudly at the mailman when he walked up the driveway.",
      "is_correct": false
    },
    {
      "text": "I decided to bake a Peace of Westphalia for the neighborhood potluck, but I forgot to add sugar.",
      "is_correct": false
    },
    {
      "text": "People studying political science frequently read about the Peace of Westphalia to understand modern political structures.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatic error: Treats the historical treaty as if it were a physical object or a type of food that can be baked. Semantic error: Attributes animal behaviors, like barking, to an abstract historical agreement. Pragmatic error: Treats the historical treaty as if it were an article of clothing or jewelry.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 7

#### Pack A
### Level 7 (sense 40248, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Peace of Westphalia, which it established state sovereignty, changed European politics.",
      "is_correct": false,
      "error_description": "The relative pronoun 'which' functions as the subject of the relative clause, so adding the pronoun 'it' creates a grammatical double subject error."
    },
    {
      "text": "When teachers explained the Peace of Westphalia, we learned about sovereignty and local laws.",
      "is_correct": true
    },
    {
      "text": "Many historians believe the Peace of Westphalia created the modern idea of national borders.",
      "is_correct": true
    },
    {
      "text": "History students often discuss the Peace of Westphalia because it changed how countries govern themselves.",
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
      "text": "Many historians study Peace of Westphalia to understand the origins of modern sovereignty.",
      "is_correct": false,
      "error_description": "The specific historical event 'Peace of Westphalia' requires the definite article 'the' to be grammatically correct in this context."
    },
    {
      "text": "They had already examined the Peace of Westphalia before starting the new unit on diplomacy.",
      "is_correct": true
    },
    {
      "text": "Before the Peace of Westphalia, outside powers often interfered in internal religious matters.",
      "is_correct": true
    },
    {
      "text": "People were studying the Peace of Westphalia while preparing for their history exams.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 40248, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Because of the Peace of Westphalia, each participating nation gained the right to choose its own official religion.",
      "is_correct": true
    },
    {
      "text": "Teachers explained that the Peace of Westphalia created a new framework for diplomacy between different governments.",
      "is_correct": true
    },
    {
      "text": "People studying political science frequently read about the Peace of Westphalia to understand modern political structures.",
      "is_correct": true
    },
    {
      "text": "Peace of Westphalia was a major turning point in European history.",
      "is_correct": false,
      "error_description": "The definite article 'The' is required before the proper noun phrase 'Peace of Westphalia' because it refers to a specific, unique historical event."
    }
  ]
}
```

---
