# Pairwise review pack 14

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
**semantic_discrimination** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "She bought a Peace of Westphalia at the local bakery this morning.",
      "is_correct": false
    },
    {
      "text": "My favorite color is Peace of Westphalia.",
      "is_correct": false
    },
    {
      "text": "By signing the Peace of Westphalia, exhausted nations finally agreed to respect each other's borders.",
      "is_correct": true
    },
    {
      "text": "The dog chased the Peace of Westphalia around the backyard.",
      "is_correct": false
    }
  ],
  "explanation": "semantic: treats an abstract historical agreement as a purchasable bakery item, which makes no sense. semantic: treats the abstract treaty as a movable physical object an animal could chase. semantic: treats a historical agreement as if it were a color, which is nonsensical.",
  "target_word": "Peace of Westphalia"
}
```

---

## sense 40248, level 9

#### Pack A
### Level 9 (sense 40248, difficulty None)
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "The textbook stated that the Peace of Westphalia helped establish the idea of national sovereignty.",
  "chunks": [
    "The textbook",
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "stated",
    "that the Peace of Westphalia helped establish the idea of national sovereignty",
    "The textbook"
  ],
  "target_word": "Peace of Westphalia",
  "chunk_count": 3
}
```

#### Pack B
### Level 9 (sense 40248, difficulty None)
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "original_sentence": "Our class project focused on the Peace of Westphalia and its impact on European politics."
}
```
**jumbled_sentence** variant `A`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "Our class project focused on the Peace of Westphalia and its impact on European politics.",
  "chunks": [
    "Our class project",
    "focused",
    "on the Peace of Westphalia and its impact on European politics"
  ],
  "correct_ordering": [
    0,
    1,
    2
  ],
  "shuffled_chunks": [
    "focused",
    "Our class project",
    "on the Peace of Westphalia and its impact on European politics"
  ],
  "target_word": "Peace of Westphalia",
  "chunk_count": 3
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "original_sentence": "By signing the Peace of Westphalia, nations agreed to respect each other's independence."
}
```
**jumbled_sentence** variant `B`, tier `T3`
```json
{
  "schema_version": 2,
  "original_sentence": "By signing the Peace of Westphalia, nations agreed to respect each other's independence.",
  "chunks": [
    "By signing the Peace of Westphalia",
    "nations",
    "agreed",
    "to respect each other 's independence"
  ],
  "correct_ordering": [
    0,
    1,
    2,
    3
  ],
  "shuffled_chunks": [
    "agreed",
    "nations",
    "to respect each other 's independence",
    "By signing the Peace of Westphalia"
  ],
  "target_word": "Peace of Westphalia",
  "chunk_count": 4
}
```

---
