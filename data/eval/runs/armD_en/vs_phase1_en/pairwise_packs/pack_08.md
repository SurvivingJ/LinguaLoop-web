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


## sense 40248, level 7

#### Pack A
### Level 7 (sense 40248, difficulty None)
**spot_incorrect_sentence** variant `B`, tier `T3`
```json
{
  "sentences": [
    {
      "text": "Few treaties had as much influence on international law as the Peace of Westphalia.",
      "is_correct": true
    },
    {
      "text": "By ending decades of conflict, the Peace of Westphalia allowed kingdoms to rebuild.",
      "is_correct": true
    },
    {
      "text": "The Peace of Westphalia were signed in 1648 to end the Thirty Years' War.",
      "is_correct": false,
      "error_description": "The subject 'Peace of Westphalia' is a singular proper noun phrase, so it requires the singular verb 'was' instead of the plural verb 'were'."
    },
    {
      "text": "Our teacher asked what nations gained because of the Peace of Westphalia.",
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

---
