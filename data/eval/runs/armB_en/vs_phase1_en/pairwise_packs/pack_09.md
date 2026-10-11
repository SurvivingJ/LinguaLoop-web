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


## sense 40248, level 1

#### Pack A
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

#### Pack B
### Level 1 (sense 40248, difficulty None)
**phonetic_recognition** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "pronunciation": "pess ov vest-FAY-lee-uh",
  "ipa": "/ˈpiːs ɒv vɛstˈfeɪliə/",
  "syllable_count": 5,
  "audio_url": null,
  "options": [
    "Peace of Westphalia",
    "Piece of Westphalia",
    "Peas of Westphalia",
    "Pace of Westphalia"
  ],
  "correct_answer": "Peace of Westphalia",
  "explanation": "Correct: This is the target phrase as written.",
  "distractor_explanations": {
    "Piece of Westphalia": "Homophone: 'Piece' sounds identical to 'Peace' (/piːs/) but refers to a part or fragment.",
    "Peas of Westphalia": "Near-homophone: 'Peas' sounds very similar to 'Peace' (/piːz/ vs /piːs/) but refers to the vegetable.",
    "Pace of Westphalia": "Minimal pair: 'Pace' differs by one phoneme (/p/ vs /p/, /eɪ/ vs /iː/) and refers to speed."
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
  "sentence_with_blank": "Historians often discuss how the ___ changed European politics.",
  "original_sentence": "Historians often discuss how the Peace of Westphalia changed European politics.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Treaty of Versailles",
    "Magna Carta",
    "Declaration of Independence",
    "Peace of Westphalia"
  ],
  "explanation": "Correct: This is the specific historical treaty mentioned in the context of changing European politics.",
  "distractor_tags": {},
  "word_definition": "A big agreement that ended a war and said each country can make its own rules.",
  "target_word": "Peace of Westphalia"
}
```
**cloze_completion** variant `B`, tier `T3`
```json
{
  "sentence_with_blank": "After years of conflict, leaders finally negotiated the ___.",
  "original_sentence": "After years of conflict, leaders finally negotiated the Peace of Westphalia.",
  "correct_answer": "Peace of Westphalia",
  "options": [
    "Peace of Westphalia",
    "Declaration of Independence",
    "Treaty of Versailles",
    "Magna Carta"
  ],
  "explanation": "Correct: This is the specific historical treaty mentioned in the context.",
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
      "text": "The Peace of Westphalia was signed yesterday in the school cafeteria.",
      "is_correct": false
    },
    {
      "text": "I hope we can reach a Peace of Westphalia over who gets the last slice of pizza.",
      "is_correct": false
    },
    {
      "text": "She bought a new Peace of Westphalia at the department store.",
      "is_correct": false
    },
    {
      "text": "By signing the Peace of Westphalia, nations agreed to respect each other's independence.",
      "is_correct": true
    }
  ],
  "explanation": "Register/Scale mismatch: The term refers to a major geopolitical treaty ending a continental war, making its use for a trivial domestic dispute pragmatically inappropriate and hyperbolic. Temporal/Factual error: The Peace of Westphalia is a specific historical event from 1648, so claiming it happened recently in a school setting is semantically impossible. Category error: The Peace of Westphalia is an abstract historical agreement/event, not a physical consumer good that can be purchased.",
  "target_word": "Peace of Westphalia"
}
```
**synonym_antonym_match** variant `A`, tier `T3`
```json
{
  "word": "Peace of Westphalia",
  "relation": "antonym",
  "options": [
    "pact",
    "war",
    "accord",
    "treaty"
  ],
  "correct_answer": "war",
  "schema_version": 2,
  "nl": {
    "en": {
      "definition": "A big agreement that ended a war and said each country can make its own rules.",
      "explanation": "antonym: a state of armed conflict opposed to a peace treaty"
    }
  }
}
```
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Peace of Westphalia barked loudly at the mailman.",
      "is_correct": false
    },
    {
      "text": "She wore a beautiful Peace of Westphalia to the party.",
      "is_correct": false
    },
    {
      "text": "Everyone in the classroom studied the impact of the Peace of Westphalia.",
      "is_correct": true
    },
    {
      "text": "I added a Peace of Westphalia to my coffee to make it sweeter.",
      "is_correct": false
    }
  ],
  "explanation": "Pragmatic error: The target is a historical political agreement, not a physical substance or condiment. Semantic error: The target is an abstract concept/event, not a living creature capable of barking. Category error: The target is a diplomatic treaty, not an article of clothing or accessory.",
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
**spot_incorrect_sentence** variant `A`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "The Peace of Westphalia was signed by the leaders in 1648, which ended the war.",
      "is_correct": false,
      "error_description": "The original sentence contains a comma splice or awkward relative clause structure that disrupts the flow. Using a participle phrase ('ending the war') is more concise and stylistically appropriate for historical narration than the relative clause 'which ended the war' in this specific context, or the error may be interpreted as a run-on if punctuation is missing. However, a more distinct learner error would be: 'The Peace of Westphalia it was signed in 1648.' Let's use a clear structural error: 'The Peace of Westphalia, it was a major treaty.'"
    },
    {
      "text": "Historians often discuss how the Peace of Westphalia changed European politics.",
      "is_correct": true
    },
    {
      "text": "Many experts believe the Peace of Westphalia established modern international law.",
      "is_correct": true
    },
    {
      "text": "Students learned that the Peace of Westphalia created the idea of national borders.",
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
      "text": "The Peace of Westphalia was signed in 1648 and it end the Thirty Years' War.",
      "is_correct": false,
      "error_description": "The sentence contains a subject-verb agreement error or tense inconsistency. The auxiliary verb 'was' indicates past tense, so the coordinated verb should also be in the past tense ('ended') rather than the present tense ('end')."
    },
    {
      "text": "After years of conflict, leaders finally negotiated the Peace of Westphalia.",
      "is_correct": true
    },
    {
      "text": "Everyone in the classroom studied the impact of the Peace of Westphalia.",
      "is_correct": true
    },
    {
      "text": "Classmates discussed what led up to the Peace of Westphalia in their group project.",
      "is_correct": true
    }
  ]
}
```

---
