# Blind age-tier grading — reader brief

You are an independent reader grading language-learning passages on LinguaLoop's six-step
**age tier** scale. Each passage is a listening/reading comprehension text written in its own
language (Chinese, English or Japanese).

## The scale

| Tier | Reader the text suits | Rough CEFR |
|---|---|---|
| T1 | a 4–5 year old native child | A1 |
| T2 | an 8–9 year old | A2 |
| T3 | a 13–14 year old | B1 |
| T4 | a 16–17 year old | B2 |
| T5 | a 19–21 year old university student | C1 |
| T6 | an educated 30+ professional | C2 |

Your batch file opens with the official rubric for each tier, in the passage language. Grade
against it.

## How to judge

Ask: *what is the youngest native reader who would understand this passage comfortably?*
Weigh, together:
- **Vocabulary**: frequency, abstraction, idiom, domain jargon (and whether jargon is glossed).
- **Grammar**: sentence length, subordinate clauses, conditionals, passives, register.
- **Ideas**: concrete and literal vs abstract, implied or rhetorical.

Do not raise the tier for a single hard word if the rest is simple, and do not lower it for a
simple topic written in hard language. Length alone is not difficulty.

## Rules

- Read ONLY your batch file. Do not open any other file, search the repository, or look up
  existing labels. You are blind on purpose.
- Grade every item. Do not skip.
- `tier` is your best single answer (integer 1–6). `alt` is the adjacent tier you would also
  accept if the passage is genuinely borderline, else `null`.
- `why` is one short clause (≤ 15 words, in English) naming the decisive evidence.

## Output

Write exactly one JSON file at the output path you were given, and nothing else:

```json
{
  "01": {"tier": 3, "alt": 4, "why": "conditionals and mild idioms; everyday topic"},
  "02": {"tier": 1, "alt": null, "why": "one concrete idea per short sentence"}
}
```

Keys are the item numbers exactly as in the file (`"01"`, `"02"`, …). Validate the JSON
(e.g. `python -c "import json;json.load(open('PATH'))"`) before finishing. Reply with one line:
the number of items graded.
