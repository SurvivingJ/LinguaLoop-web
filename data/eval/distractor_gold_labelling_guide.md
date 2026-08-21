# Distractor gold set — labelling guide (TASK-726)

You are adjudicating multiple-choice **distractors** (the wrong options). For each row you
answer three questions and, sometimes, write a note. About 100–150 rows an hour is normal;
accuracy matters far more than speed.

**Label in your native language only.** If you are labelling the Chinese or Japanese sheet you
must be a native speaker of that language. Do not label a language through a translation — the
judgment below is about what a *learner reading the original* would plausibly pick, and a
translation destroys exactly that.

**Do not consult a model, a dictionary of "right answers", or the other labeller.** Your
independent judgment is the product. Two people labelling the overlap sheet must not compare
notes; the agreement between you is a published number (Cohen's κ) and coordinating would
falsify it.

---

## The columns you fill in

| Column | Values | |
|---|---|---|
| `topical_distance` | `on-topic` / `related` / `unrelated` | What the distractor is *about* |
| `confusable` | `yes` / `borderline` / `no` | Whether a learner would plausibly pick it |
| `also_correct` | `true` / `false` | Whether it is, in fact, a second right answer |
| `notes` | free text | **Required** when `confusable = borderline` |

Leave a row completely blank only if you cannot label it (a corrupt passage, say). A blank row
is recorded as *unlabelled*, not as agreement.

---

## `topical_distance` — what is it about?

Judge the distractor against the **passage**, not against the correct answer.

- **`on-topic`** — it names something the passage actually discusses: a person, object, event,
  claim or idea that appears in or follows directly from the text.
- **`related`** — it belongs to the passage's subject area but is not in the passage. A different
  chemical in a passage about chemistry; a different year in a passage about a war.
- **`unrelated`** — it comes from somewhere else entirely. A cooking term in a passage about
  monetary policy.

Do not let wrongness pull you toward `unrelated`. A distractor can be flatly wrong and still be
`on-topic` — that is the *good* kind of distractor, and confusing the two axes is the exact
defect this gold set exists to measure.

## `confusable` — would a learner plausibly pick it?

Imagine a learner who read the passage but did **not** fully understand it. Would this option
tempt them?

- **`yes`** — a learner with a partial or surface reading could reasonably choose it. It fits the
  question grammatically, matches its register and length, and is not absurd on its face.
- **`no`** — nobody who read the passage would pick it. It is obviously off, absurd, the wrong
  part of speech, wildly the wrong length, or it answers a different question entirely.
- **`borderline`** — you genuinely cannot decide, or it depends on the learner's level. **Write a
  note saying which way it leans and why.** Borderline is a real answer, not an escape hatch;
  it is the population the review band will be redesigned around, and your note is the evidence.

`confusable` is **not** the same question as `topical_distance`. Both combinations occur and both
are informative:

- `unrelated` + `yes` — off-subject but superficially attractive (right shape, right register).
- `on-topic` + `no` — squarely on-subject but nobody would ever pick it.

If you find yourself answering the same thing in both columns every row, re-read this section.

## `also_correct` — is it actually right?

`true` if, read strictly, the option is **also** a correct answer to the question — the passage
supports it, or it is a synonym or paraphrase of the marked correct answer. This is the worst
defect a distractor can have: the item is unanswerable and the learner is marked wrong for being
right.

Mark it `true` regardless of the other two columns, and mark it whenever you are *reasonably*
sure — an item where a careful native reader can defend two answers is broken even if the
author intended only one.

---

## Worked examples (English; the same reasoning applies in zh and ja)

> **Passage (extract):** …the 1815 eruption of Mount Tambora injected sulphate aerosols into the
> stratosphere, cooling global temperatures and producing crop failures across Europe in 1816…
>
> **Question:** Why did European crops fail in 1816?
> **Correct answer:** Volcanic aerosols cooled the atmosphere.

| Distractor | `topical_distance` | `confusable` | `also_correct` | Why |
|---|---|---|---|---|
| A late-season drought struck the region. | `related` | `yes` | `false` | Plausible crop-failure cause, not this passage's |
| Mount Tambora erupted in 1815. | `on-topic` | `yes` | `false` | Straight from the passage, but it is the cause of the cooling, not the answer to "why did crops fail" — a strong, legitimate distractor |
| Sulphate particles blocked sunlight and lowered temperatures. | `on-topic` | `yes` | **`true`** | A paraphrase of the correct answer. Broken item |
| The recipe called for more salt. | `unrelated` | `no` | `false` | Nobody picks this |
| Farmers switched to a new lunar calendar. | `unrelated` | `yes` | `false` | Off-subject, but plausibly-shaped enough that a guessing learner might take it — the `unrelated` + `yes` cell |

---

## After you finish

Save the sheet as CSV with the same columns and hand it back. It is merged with
`scripts/merge_distractor_gold.py`, which will reject the file if a value is outside the
vocabularies above or a `borderline` has no note.

Cohen's κ is then computed on the overlap sheet. **If κ on `confusable` comes out below 0.60,
the definitions above are the defect, not you** — the guide gets revised and the overlap slice is
relabelled before any judge model is scored. A gold set two careful people disagree about cannot
arbitrate a disagreement between two models.
