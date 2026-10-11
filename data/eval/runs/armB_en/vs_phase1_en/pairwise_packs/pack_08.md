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


## sense 19480, level 7

#### Pack A
### Level 7 (sense 19480, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The school committee decided to fund all sports and arts programs equitably this year.",
      "is_correct": true
    },
    {
      "text": "The manager divided the bonus money equitable among the team members.",
      "is_correct": false,
      "error_description": "The adjective 'equitable' is incorrectly used to modify the verb 'divided'. An adverb ('equitably') is required to describe how the action was performed."
    },
    {
      "text": "They have always shared their household chores equitably so that nobody feels overwhelmed.",
      "is_correct": true
    },
    {
      "text": "The teacher made sure that the group project work was distributed equitably among all four students.",
      "is_correct": true
    }
  ]
}
```

#### Pack B
### Level 7 (sense 19480, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The referee managed the game equitably, making sure neither team had an unfair advantage.",
      "is_correct": true
    },
    {
      "text": "The discussion leader ensured that all participants could speak equitably during the debate.",
      "is_correct": true
    },
    {
      "text": "Our class treasurer tried to spend the club funds equitably on supplies for everyone.",
      "is_correct": true
    },
    {
      "text": "The teacher shared equitably the prizes among all the students in the class.",
      "is_correct": false,
      "error_description": "The adverb 'equitably' is incorrectly placed between the transitive verb 'shared' and its direct object 'the prizes'. In English, adverbs should not separate a verb from its direct object; it should be placed after the object."
    }
  ]
}
```

---

## sense 19521, level 1

#### Pack A
### Level 1 (sense 19521, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nin-teenth",
  "ipa": "/ˈnɪnˈtiːnθ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "ninety",
    "ninetieth",
    "nineteenth",
    "nineties"
  ],
  "correct_answer": "nineteenth",
  "explanation": "Correct: This is the target word.",
  "distractor_explanations": {
    "ninety": "Phonetic distractor: Shares the initial /naɪn/ sound but differs in the final syllable (/ti/ vs /tiːnθ/).",
    "ninetieth": "Minimal pair: Differs only in the final vowel and consonant cluster (/iːθ/ vs /iːnθ/), creating a similar rhythmic pattern.",
    "nineties": "Rhyme/Near-homophone: Ends in a similar sibilant sound and shares the same stress pattern, potentially causing confusion in rapid speech."
  },
  "distractor_source": "llm"
}
```

#### Pack B
### Level 1 (sense 19521, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "pronunciation": "nineteenth",
  "ipa": "/ˈnaɪn.tiːnθ/",
  "syllable_count": 2,
  "audio_url": null,
  "options": [
    "nineteen",
    "nineteenth",
    "ninth",
    "ninetieth"
  ],
  "correct_answer": "nineteenth",
  "explanation": "Correct target word.",
  "distractor_explanations": {
    "nineteen": "Minimal pair: differs only in the missing final /θ/ sound.",
    "ninth": "Minimal pair: differs by the omission of the /tiːn/ syllable.",
    "ninetieth": "Near-homophone: differs in the second syllable vowel /iː/ vs /i/ and overall syllable structure."
  },
  "distractor_source": "llm"
}
```

---

## sense 19521, level 3

#### Pack A
### Level 3 (sense 19521, difficulty None)
**cloze_completion** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "She celebrated her ___ birthday with a big party last weekend.",
  "original_sentence": "She celebrated her nineteenth birthday with a big party last weekend.",
  "correct_answer": "nineteenth",
  "options": [
    "teenage",
    "annual",
    "nineteenth",
    "final"
  ],
  "explanation": "Correct: Fits the ordinal sequence required for a specific birthday celebration.",
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

---

## sense 19521, level 4

#### Pack A
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

#### Pack B
### Level 4 (sense 19521, difficulty None)
**morphology_slot** variant `A`, tier `T3`
```json
{
  "sentence_with_blank": "The runner from Kenya crossed the finish line in ___ place.",
  "original_sentence": "The runner from Kenya crossed the finish line in nineteenth place.",
  "correct_answer": "nineteenth",
  "base_form": "nineteenth",
  "form_label": "ordinal adjective",
  "options": [
    "nineteen",
    "nineteenths",
    "nineteenth",
    "19th"
  ],
  "explanation": "ordinal adjective required to indicate position in a sequence",
  "word_definition": "Coming next after the eighteenth in a series.",
  "target_word": "nineteenth"
}
```
**word_family** variant `A`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "The runner from Kenya crossed the finish line in ___ place.",
  "original_sentence": "The runner from Kenya crossed the finish line in nineteenth place.",
  "required_pos": "adjective",
  "options": [
    "nineteenly",
    "nineteenth",
    "nineteenthness",
    "nineteenthy"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal form for the number nineteen"
    }
  }
}
```
**word_family** variant `B`, tier `T3`
```json
{
  "stem": "nineteen",
  "sentence_with_blank": "The committee reviewed the ___ item on the agenda.",
  "original_sentence": "The committee reviewed the nineteenth item on the agenda.",
  "required_pos": "adjective",
  "options": [
    "nineteenish",
    "nineteenly",
    "nineteenth",
    "nineteenment"
  ],
  "correct_answer": "nineteenth",
  "schema_version": 2,
  "nl": {
    "en": {
      "explanation": "the standard ordinal form of the number nineteen"
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

#### Pack B
### Level 6 (sense 19521, difficulty None)
**semantic_discrimination** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The nineteenth water in the glass was too cold to drink.",
      "is_correct": false
    },
    {
      "text": "He drove his car at a nineteenth speed down the highway.",
      "is_correct": false
    },
    {
      "text": "She felt very nineteenth after hearing the good news.",
      "is_correct": false
    },
    {
      "text": "The teacher assigned page nineteen for homework, but I accidentally read the nineteenth chapter instead.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: 'Nineteenth' implies a countable sequence of distinct items, but water is a mass noun and cannot be individually counted in this context without a unit like 'glass'. Semantically inappropriate: Ordinal numbers describe position in a series, not emotional states or feelings. Semantically inappropriate: Speed is a continuous measurement or described by adjectives like 'high' or 'fast', not by ordinal rank unless comparing specific predefined gear settings or records, which is not indicated here.",
  "target_word": "nineteenth"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "nineteenth",
  "relation": "antonym",
  "options": [
    "eighteenth",
    "twentieth",
    "ordinal",
    "first"
  ],
  "correct_answer": "first",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Coming next after the eighteenth in a series.",
      "explanation": "antonym: denotes the initial position rather than the nineteenth"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She found the nineteenth item on the scavenger hunt list hidden behind a tree.",
      "is_correct": true
    },
    {
      "text": "She added a nineteenth pinch of salt to the soup.",
      "is_correct": false
    },
    {
      "text": "The nineteenth color of the rainbow is indigo.",
      "is_correct": false
    },
    {
      "text": "The nineteenth second of the minute lasted longer than the others.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: Rainbows have only seven distinct colors, so referring to a 'nineteenth' one contradicts general knowledge. Semantically odd: While grammatically correct, counting individual pinches of an ingredient to such a high specific ordinal is pragmatically unnatural in cooking contexts. Factually incorrect: All seconds in a standard minute are of equal duration, making the distinction of a specific 'nineteenth' one having different properties illogical.",
  "target_word": "nineteenth"
}
```
**synonym_antonym_match** variant `B`, tier `T3`
```json
{
  "word": "nineteenth",
  "relation": "antonym",
  "options": [
    "nineteen",
    "eighteenth",
    "first",
    "twentieth"
  ],
  "correct_answer": "first",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "Coming next after the eighteenth in a series.",
      "explanation": "antonym: denotes the initial position rather than a late sequential one"
    }
  }
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
      "text": "The runner from Kenya crossed the finish line in nineteenth place.",
      "is_correct": true
    },
    {
      "text": "He finished in nineteenth place out of fifty runners in the race.",
      "is_correct": true
    },
    {
      "text": "She celebrated her nineteenth birthday with a big party last weekend.",
      "is_correct": true
    },
    {
      "text": "She is in the nineteenth grade and she like it very much.",
      "is_correct": false,
      "error_description": "The sentence contains a subject-verb agreement error. The singular subject 'she' requires the verb form 'likes', not 'like'."
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
    "Great Whale of China",
    "Great Fall of China",
    "Grate Wall of China",
    "Great Wall of China"
  ],
  "correct_answer": "Great Wall of China",
  "explanation": "Correct: This is the target phrase.",
  "distractor_explanations": {
    "Grate Wall of China": "Homophone/Near-homophone: 'Grate' sounds identical or very similar to 'Great' but refers to a metal frame or to shred food.",
    "Great Whale of China": "Minimal pair: 'Whale' differs from 'Wall' by only one phoneme (/w/ vs /l/ and vowel quality), creating a plausible auditory confusion.",
    "Great Fall of China": "Rhyme/Similar stress: 'Fall' rhymes with 'Wall' and shares the same syllable structure, making it a potential mishearing in fast speech."
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
    "local cuisine",
    "ancient dynasty",
    "Great Wall of China",
    "Yellow River"
  ],
  "explanation": "Correct: This is the specific historical landmark mentioned in the context of famous world landmarks.",
  "distractor_tags": {},
  "word_definition": "A big wall built a long time ago in China to keep people safe.",
  "target_word": "Great Wall of China"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "Can you see the ___ from outer space without using a telescope?",
  "original_sentence": "Can you see the Great Wall of China from outer space without using a telescope?",
  "correct_answer": "Great Wall of China",
  "options": [
    "Silk Road",
    "Forbidden City",
    "Yellow River",
    "Great Wall of China"
  ],
  "explanation": "Correct: This is the specific historical landmark mentioned in the context of visibility from space.",
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
      "text": "She ate the Great Wall of China for breakfast because it was delicious.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China fits easily into my backpack for the hike.",
      "is_correct": false
    },
    {
      "text": "I used the Great Wall of China to stir my morning coffee.",
      "is_correct": false
    },
    {
      "text": "Walking along the Great Wall of China can be quite tiring because of the steep stairs.",
      "is_correct": true
    }
  ],
  "explanation": "Pragmatically inappropriate: The target is a massive geographical structure, not a small utensil that can be held or used for stirring. Semantically inappropriate: The target is thousands of miles long and cannot be contained in a backpack. Semantically inappropriate: The target is made of stone and earth, not food, and cannot be eaten.",
  "target_word": "Great Wall of China"
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "I used the Great Wall of China to stir my coffee this morning.",
      "is_correct": false
    },
    {
      "text": "During our history class, we watched a documentary about the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "She ate the Great Wall of China for breakfast because it was delicious.",
      "is_correct": false
    },
    {
      "text": "The Great Wall of China fits perfectly in my pocket.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatically inappropriate: The target is a massive geographical landmark, not a small utensil that can be held or used for stirring. Semantically impossible: The target is thousands of kilometers long and cannot physically fit into a pocket. Semantically absurd: The target is a structure made of stone and earth, not an edible food item.",
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

#### Pack B
### Level 7 (sense 40142, difficulty None)
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Great Wall of China is one of the most famous historical landmarks in the world.",
      "is_correct": true
    },
    {
      "text": "Ancient emperors ordered workers to build the Great Wall of China to protect their lands.",
      "is_correct": true
    },
    {
      "text": "The Great Wall of China are a very long structure that stretches across northern China.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: 'The Great Wall of China' is a singular proper noun referring to a single entity, so it requires the singular verb 'is', not the plural verb 'are'."
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
      "text": "The Great Wall of China are a very long structure that stretches across northern China.",
      "is_correct": false,
      "error_description": "Subject-verb agreement error: 'The Great Wall of China' is a singular proper noun referring to a single landmark, so it requires the singular verb 'is', not the plural verb 'are'."
    },
    {
      "text": "Can you see the Great Wall of China from outer space without using a telescope?",
      "is_correct": true
    },
    {
      "text": "During our history class, we watched a documentary about the Great Wall of China.",
      "is_correct": true
    },
    {
      "text": "Sections of the Great Wall of China were built using stone, brick, and packed earth.",
      "is_correct": true
    }
  ]
}
```

---
