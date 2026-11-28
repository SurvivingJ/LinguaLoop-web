# Comprehension tests for a language pack: content contract

A test is a short passage in the target language with multiple-choice
questions, the unit learners study in the app's daily session (listening and
reading). Paths are under `data/language_packs/<lang>/tests/`. Tool:
`python3 scripts/language_pack.py <command> <lang> …` from the repository root.

- `plan/t<tier>.json` — what each test is about, grouped in batches.
- `batches/t<tier>-NN.jsonl` — one test per line, written by an author.
- `reviewed/t<tier>-NN.jsonl` — the reviewed copy; only these are exported.

## Tiers

The app grades difficulty by the age of a native reader. The passage must be
readable by that reader and no harder.

| tier | reader | words | questions | passage |
|---|---|---|---|---|
| 1 | age 4-5 | 35-70 | 4 | the 500 commonest words, present tense, one idea per sentence |
| 2 | age 8-9 | 70-120 | 5 | ~2,000 words, compound sentences, literal and concrete, everyday past tense |
| 3 | age 13-14 | 120-190 | 5 | ~5,000 words, colloquial turns, mild idiom, conditionals |
| 4 | age 16-17 | 190-280 | 5 | standard adult grammar, moderate specialist words explained by context |
| 5 | age 19-21 | 280-400 | 5 | full breadth of the language, complex clauses, abstraction |
| 6 | educated adult | 400-650 | 5 | high register, domain vocabulary, argument and rhetoric |

Tier describes language, not subject: a tier 1 passage about a hospital is
simple sentences about a hospital.

## A test

```json
{"slug": "it-t2-mercato-del-sabato", "tier": 2, "category": "Cuisine & Food", "style": "academic",
 "topic": "<the plan's topic text>", "title": "Il mercato del sabato", "title_en": "The Saturday market",
 "sentences": [{"tl": "Ogni sabato mattina la piazza si riempie di bancarelle.", "en": "Every Saturday morning the square fills with stalls."}],
 "questions": [{"type": "literal_detail", "text": "Quando c'è il mercato?", "choices": ["La domenica sera", "Il sabato mattina", "Ogni giorno", "Solo d'estate"], "answer": 1, "evidence": [0], "explanation": "Sentence 1 says 'ogni sabato mattina'. The passage never mentions Sunday, a daily market or the summer."}],
 "vocab": [{"lemma": "bancarella", "pos": "noun", "en": "market stall"}]}
```

- `slug`, `tier`, `category`, `style`, `topic`: copied from the plan.
- `sentences`: the passage, one sentence per entry, in order. Joined with
  spaces they are the transcript. `en` is a faithful English translation of
  that sentence alone (it is shown to learners as the reference translation):
  complete, natural English, nothing added, nothing left out.
- `style: "conversational"`: a dialogue; every sentence also has `speaker`
  (a first name). Otherwise a single-voice text: a description, a short
  report, a story, an explanation, a letter, a notice.
- Passage text: the profile's characters; digits and `% € ° /` are allowed
  here (the passage is read aloud by a synthetic voice, so write what a
  newspaper would print). Straight apostrophes and quotation marks only.
- `questions`: in the target language, at the passage's own level or easier.
  Exactly 4 choices, `answer` is the index of the right one, `evidence` lists
  the sentence indexes (0-based) that decide it (may be empty only for
  `main_idea` and `author_purpose`), `explanation` is English: why the key is
  right and why each wrong choice is wrong.
- `vocab`: 5 to 14 words of the passage worth teaching at this tier, as
  dictionary forms, with part of speech and a short English meaning.

### Question types

| type | asks | tiers |
|---|---|---|
| `literal_detail` | a fact stated in one sentence: who, what, when, where | all |
| `vocabulary_context` | what a word or phrase means in this passage | all |
| `main_idea` | what the passage as a whole is about | 2+ |
| `supporting_detail` | a fact that supports a point the passage makes | 2+ |
| `inference` | something the passage implies but does not state | 3+ |
| `author_purpose` | why it was written, or the writer's attitude | 3+ |

At least two types per test; from tier 3 at least one of the last three, and
no more than two `literal_detail`.

### What makes a question usable

1. **Exactly one choice is right** for a careful reader of the passage. The
   commonest defect is a distractor that is also true or also supported.
2. **It cannot be answered without the passage.** If common sense or general
   knowledge picks the key, the question tests nothing. Make the passage say
   something specific (a time, a reason, a preference, an order of events)
   and ask about that. This matters most for `main_idea`: its wrong choices
   must be about things the passage does mention, at the wrong scope.
3. **Distractors are plausible and come from the passage's world**: another
   detail of the passage in the wrong role, a natural misreading, the
   opposite of what is said. Never a joke, never something from nowhere.
4. **The key does not give itself away**: same length and form as the other
   choices, not the only specific one, not a word-for-word copy of the
   sentence when the others are paraphrases. Spread the key over positions.
5. `vocabulary_context` asks about a word whose meaning the passage makes
   clear; the choices are meanings in simpler target-language words.
6. `inference` must really need two pieces of the passage put together, and
   the passage must settle it.

`python3 scripts/language_pack.py validate-tests <lang> <file>` until OK.

## Plan file

```json
{"tier": 2, "batches": [{"id": "t2-01", "tests": [
  {"slug": "it-t2-mercato-del-sabato", "category": "Cuisine & Food", "style": "academic",
   "topic": "A weekly open-air food market in a small town: who sells what, and why one family shops there."}]}]}
```

- `category` is one of the app's 17: Business & Commerce, Cuisine & Food,
  Family, Education, Work & Careers, Health & Medicine, Transportation,
  Architecture, Environment, Sports & Recreation, Language & Literature,
  Science & Technology, Fashion, Music & Performance, Art & Design, History,
  Agriculture.
- `topic`: one or two sentences saying what the passage is about and its
  angle, concrete enough that two authors would write the same kind of text
  and different enough from every other topic of the tier.
- About one test in six is `conversational`.
- Slugs: `<lang>-t<tier>-<three to five lowercase words>`, unique.

`python3 scripts/language_pack.py validate-test-plan <lang> t<tier>.json`.
