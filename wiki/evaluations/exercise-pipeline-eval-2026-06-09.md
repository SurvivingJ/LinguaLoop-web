---
title: "Exercise-Generation Pipeline Evaluation — 2026-06-09 (EN vocabulary)"
type: evaluation
status: complete
last_updated: 2026-06-09
scope: "services/exercise_generation vocabulary pipeline; English (language_id=2) only — Chinese aborted (see §3)"
open_questions:
  - "OPEN: Is the legacy services/exercise_generation vocabulary pipeline still meant to run, or is it fully superseded by the vocabulary_ladder pipeline? Its only configured generation model is 404-delisted and it has not made a logged call in 21+ days."
  - "OPEN: Should tl_nl_translation be disabled when tl_language == nl_language (i.e. English-target learners with English UI)? As built it is not a translation task."
  - "OPEN: Should the cloze_distractor_judge's rejections actually remove/replace options? Today rejected distractors are still shipped (judge is observability-only)."
  - "OPEN: semantic_discrimination has no judge and a systematic keyed-answer bug for polysemous words — does it need an entailment/validity judge like the ladder pipeline got?"
  - "OPEN: Chinese quality dimension (hanzi/pinyin/audio-confusable distractors) is unmeasured this round — re-run ZH on a non-rate-limited live slug."
---

# Exercise-Generation Pipeline Evaluation — 2026-06-09 (EN vocabulary)

> Evaluator: independent Opus grading of every generated exercise, compared against the pipeline's own judges.
> Pipeline under test: `services/exercise_generation` (the legacy VOCABULARY_DISTRIBUTION pipeline reached via
> `run_exercise_generation.run_vocabulary_batch` → `ExerciseGenerationOrchestrator`), **not** the newer
> `services/vocabulary_ladder` pipeline that recent [[log]] entries (qwen slug-rot, ladder judges) describe.

---

## 1. Summary verdict

**The pipeline is not production-healthy.** As *configured* it is dead on arrival for both target languages
(missing/inactive templates + a 404-delisted model slug); it produced **zero** exercises until templates were
temporarily re-pointed at live models. Once unblocked, generation *mechanics* are solid (correct 16/16
distribution per sense, audio synthesised, no crashes), and two of the five exercise types are good — but the
other two are systematically broken, and the judge layer barely functions.

Bottom line: on 160 EN exercises I **accept 59%, flag 14%, reject 27%**. The pipeline itself ships ~100% of what
it generates (it never drops an exercise; its one working judge doesn't even remove the distractors it rejects).
The gap between "shipped" and "acceptable" is concentrated entirely in `tl_nl_translation` and
`semantic_discrimination`.

**Grades (English):**

| Exercise type | Grade | One-line |
|---|---|---|
| text_flashcard | **B+** | Natural, on-sense; docked for corpus sentences too hard for A1 words + stray markdown bold |
| listening_flashcard | **B** | Same sentences + audio; no comprehension check beyond reveal; same difficulty/markup issues |
| cloze_completion | **B / C** | Excellent for abstract lemmas (clear antonym distractors); weak/trivial for concrete "bean"; sense-drift; judge ineffective |
| tl_nl_translation | **F** | Degenerate: `tl==nl==en`, not a translation; tense-only options, frequently >1 acceptable |
| semantic_discrimination | **D / F** | Correct sentence usually fine, but distractors are absurd (concrete words) or *actually valid English* mislabeled wrong (abstract words) |

Per-language: **English = C+ overall** (held up by flashcards + abstract-word cloze). **Chinese = not graded**
(generation aborted on upstream rate-limit; see §3).

---

## 2. Method

- **Pipeline entry:** in-process `ExerciseGenerationOrchestrator.run('vocabulary', sense_id, language_id)` per sense
  (mirrors `run_vocabulary_batch`, which discards batch_ids). Audio synthesis **ON**.
- **Scale:** reduced from the requested 20+20 to **10 EN + 10 ZH senses** (per the cost/slowness allowance), then
  ZH was abandoned — so the graded corpus is **10 EN senses × 16 = 160 exercises**.
- **Senses (EN, language_id=2)** — full requested set of 20 recorded for reproducibility; **first 10 were generated**:
  - Generated: `27838` bean, `13895` bean, `14072` appreciate, `28016` appreciate, `14347` heat, `28652` heat,
    `14556` precision, `29140` precision, `27846` grow, `28106` harvest.
    (Includes 4 polysemous pairs: bean/appreciate/heat/precision ×2.)
  - Selected-but-not-run (next 10): `14044` high, `14122` stringent, `14197` yield, `14361` acidity, `14433` change,
    `14536` subtle, `14614` learn, `14818` ornamentation, `29594` relaxed, `15029` example.
- **Senses (ZH, language_id=1)** — recorded, **not generated**: `9963, 20138, 10165, 20666, 10368, 21362, 10570,
  21740, 9964, 10047` (+10 more selected). All `is_validated=true`. (`semantic_category` is null and `sense_rank≈1`
  across this dataset, so spread came from lemma diversity, not rank/category.)
- **Batch IDs (cleanup key, 10 EN):** `0725c1a5…`, `e1e99980…`, `66c1a149…`, `dd7e3486…`, `03b3c436…`, `9e5a176a…`,
  `d64563be…`, `ee312676…`, `f17e5bd1…`, `6c86d30c…`. All 160 rows deleted at cleanup (§8).
- **Run window (UTC):** generation run start `2026-06-09T06:44:16Z`; llm_calls windowed from that timestamp.
- **Caveats / deviations (faithful disclosure):**
  1. **Templates were temporarily modified** (per operator instruction) to make the pipeline runnable, then fully
     reverted. The pipeline's *configured* model (`google/gemini-flash-1.5`) is **404-delisted** (§6), so it cannot
     generate at all as-shipped. To assess *quality* the temp rows used live, language-appropriate slugs:
     EN → `google/gemini-2.5-flash-lite`, (ZH → `qwen/qwen3.7-plus`). **Quality findings therefore describe those
     substitute models; the config/slug findings (§6) stand independently and are the more serious problem.**
     Exact reverts applied & verified: ids 147/40/39 restored to `google/gemini-flash-1.5` with original active flags;
     inserted EN `exercise_sentence_generation` (id=179) deleted.
  2. **Chinese aborted:** `qwen/qwen3.7-plus` returned upstream 429 rate-limits ("temporarily rate-limited upstream",
     Alibaba/BYOK) on the first ZH sense; the run was killed to stop cost. 0 ZH exercises. The Chinese-specific
     checks (hanzi correctness, pinyin/tone/sandhi, idiomatic classifiers, audio-confusable listening distractors)
     are **unmeasured this round.**
  3. **Grading method:** every one of the 160 exercises was read and graded 1–5 on correctness / distractor-quality
     (MCQ types) / pedagogical value; verdicts encoded in a reproducible rubric (`accept ≥4 avg / flag >2.5 / reject ≤2.5`).
     Machine-readable verdicts retained out-of-tree (`verdicts.json`, not committed).

---

## 3. Generation health

**Expected vs actual (EN, 10 senses):**

| Type | Expected/sense | Expected total | Actual | Shortfall |
|---|---|---|---|---|
| text_flashcard | 3 | 30 | 30 | 0 |
| listening_flashcard | 3 | 30 | 30 | 0 |
| cloze_completion | 5 | 50 | 50 | 0 |
| tl_nl_translation | 3 | 30 | 30 | 0 |
| semantic_discrimination | 2 | 20 | 20 | 0 |
| **Total** | **16** | **160** | **160** | **0** |

No shortfalls — every sense produced the full 16. Per-sense wall time ≈ 67–224 s (mean ~95 s) on
`gemini-2.5-flash-lite` + TTS.

**Failures / aborts:**
- **Run 1 (the real config): 20/20 senses errored in <0.2 s with 0 LLM calls.** `_load_models` raises before any
  generation because it requires *active* `prompt_templates` rows for `cloze_distractor_generation` **and**
  `exercise_sentence_generation` for the language:
  - EN(2): `exercise_sentence_generation` row **did not exist** →
    `RuntimeError: No active prompt_templates row for task_name='exercise_sentence_generation' language_id=2`.
  - ZH(1): `cloze_distractor_generation` existed but `is_active=false` → same RuntimeError on the first lookup.
- **ZH (run 2):** upstream 429 on `qwen/qwen3.7-plus`; aborted (0 exercises).
- **Cloze "judge short" churn:** for several senses the log repeatedly reported `cloze_judge still short after retry
  (0/1/2 kept)` — the judge rejected distractors, retried generation, and still came up short, yet the exercise
  shipped with a full 4 options anyway (see §5).

---

## 4. Independent quality (the 160 EN exercises)

**Accept/flag/reject by type (my grading):**

| Type | n | accept | flag | reject | accept% | meanC | meanD | meanP |
|---|---|---|---|---|---|---|---|---|
| text_flashcard | 30 | 27 | 3 | 0 | 90% | 4.90 | — | 4.67 |
| listening_flashcard | 30 | 27 | 3 | 0 | 90% | 4.90 | — | 4.60 |
| cloze_completion | 50 | 40 | 9 | 1 | 80% | 4.66 | 3.72 | 4.28 |
| tl_nl_translation | 30 | 0 | 0 | 30 | 0% | 2.00 | 2.00 | 2.00 |
| semantic_discrimination | 20 | 0 | 8 | 12 | 0% | 2.60 | 2.00 | 2.40 |
| **OVERALL** | **160** | **94** | **23** | **43** | **59%** | — | — | — |

**Cloze accept% by sense (note the abstract-vs-concrete split):**

| Lemma (sense) | accept% | Lemma (sense) | accept% |
|---|---|---|---|
| appreciate (14072) | 100% | precision (14556) | 100% |
| appreciate (28016) | 100% | precision (29140) | 100% |
| grow (27846) | 100% | heat (14347) | 100% |
| heat (28652) | 100% | harvest (28106) | 80% |
| **bean (27838)** | **20%** | **bean (13895)** | **0%** |

### Top failure patterns (with cited examples)

**Pattern 1 — `tl_nl_translation` is degenerate for English (30/30 reject).**
`tl_language == nl_language == "en"`, so the "translation" shows an English sentence and asks the learner to pick its
English "translation". The options are the *same sentence* in different tenses, and the keyed answer is just the
original — frequently **more than one option is perfectly grammatical**, so there is no unique correct answer.
- bean: tl `"He likes to eat a jelly bean for dessert."` → options = `["He likes…","He liked…","He will like…"]`.
- precision (`6498c847`): `"You need to measure with precision to get the recipe right."` → `["You need…","You needed…","You will need…"]` — all three acceptable English.
- grow (`6fe39f62`): `["…will grow…","…grew…","…are growing…"]` — all acceptable.
This type tests tense discrimination mislabeled as translation; it does not test the target sense at all.

**Pattern 2 — `semantic_discrimination` mislabels valid English as "wrong" for polysemous words (precision/grow/harvest → reject).**
The "only correct" sentence is not uniquely correct; several distractors are natural, valid uses of the word, just
not the narrow target sense.
- precision (`3841c9ca`): marks **False** → `"He admired the precision of the artist's brushstrokes, which brought the painting to life."` (a perfectly valid use of *precision*).
- grow (`90721af4`): marks **False** → `"I need to grow my career…"` and `"We will grow this company into a market leader…"` (both standard English).
- harvest (`f4e4661a`): marks **False** → `"The detective began to harvest clues from the crime scene."` (*harvest clues/data* is idiomatic).

**Pattern 3 — `semantic_discrimination` distractors are absurd gibberish for concrete words (bean → flag).**
Wrong options are nonsense rather than plausible misuse, making them trivially eliminable (no real discrimination).
- bean (`55b0882e`): `"He dropped his car keys and they made a loud bean."`, `"…full of hot air and no bean."`,
  `"She decided to bean the entire audience with a bouquet of flowers."`

**Pattern 4 — cloze distractors trivial / sense-drift for the concrete noun "bean".**
- Sense drift (`18ff39a9`): `"He likes to eat a jelly ___ for dessert."` keyed `bean` — but this is *jelly bean*
  (candy), **not** the target sense "a seed you can eat"; the explanation even calls it "a small, sweet confection".
  Distractors `sandwich/rock/cloud` mix one food with two non-foods.
- Trivial distractors (`5570fcbd`): `"She planted a small ___ in her garden."` → `bean/rock/cloud/idea` (rock, cloud,
  idea are not plantable — eliminable without knowing the word).

**Pattern 5 — flashcards: corpus sentences far above the word's level, plus stray markdown bold (flag).**
For the coffee-corpus senses (`13895` bean, `14347` heat) the mined sentences are C2-complex for an A1 definition,
and carry leftover bold markup on **non-target** words.
- text_flashcard (`c22198f1`, def = "an edible seed…"): *"The journey of a coffee **bean** from verdant plantation to
  steaming cup is an odyssey marked by complex cultivation practices, stringent quality controls, significant
  **import** and **export** operations, and ultimately, global **consumption**."* — three non-target words bolded;
  way over level. The identical sentences are reused verbatim for listening_flashcard, cloze and tl_nl (low diversity).

**For balance — what's genuinely good:** cloze for abstract lemmas is strong. e.g. precision (`37d6beca`):
*"The language model aims for ___ in its responses."* → `precision / vagueness / verbosity / ambiguity` — all same
register, all clearly wrong-but-plausible, single correct answer, squarely on-sense. appreciate, grow, heat cloze are
similarly good. Flashcard sentences for normal-level senses (precision, grow, harvest, heat-28652) are natural and
correctly highlight the target.

---

## 5. Judge agreement (pipeline vs independent)

Because `llm_calls` rows aren't joined to individual exercises, this compares **distributions**. The pipeline does
not drop exercises — it ships everything it generates — so its effective **exercise-level accept rate ≈ 100%** for
every type. Independent accept rates and the resulting leniency gap:

| Type | Pipeline accept (shipped) | My accept | Leniency gap (≈ false-accept) |
|---|---|---|---|
| text_flashcard | ~100% | 90% | ~10% |
| listening_flashcard | ~100% | 90% | ~10% |
| cloze_completion | ~100% | 80% | ~20% |
| tl_nl_translation | ~100% | 0% | **~100%** |
| semantic_discrimination | ~100% | 0% | **~100%** |
| **OVERALL** | **~100%** | **59%** | **~41 pp** |

So roughly **27% of shipped exercises I reject outright (43/160)** and another **14% I flag (23/160)** — ~41% of
output is problematic, almost all of it the 50 `tl_nl_translation` + `semantic_discrimination` items the pipeline
applies **no judge** to.

**Where judges fail-open / don't function (the core problem):**
- **Only one judge fired: `cloze_distractor_judge`** (225 calls on `google/gemini-2.5-flash-lite` for 50 cloze;
  +1 deepseek-chat call from the partial ZH sense). It did **not** fail-open (live slug, parsed_ok=true on all).
- **But its rejections have no effect on shipped content.** It rejected **32 distractors across 18 cloze items**
  (distribution: 32 items 0-rejected, 9×1, 4×2, 5×3), yet **all 50 cloze still ship 4 options** — rejected
  distractors are not removed/replaced; the pipeline falls back to the original generation. The one working judge is
  effectively **observability-only**.
- **No judge at all** on `tl_nl_translation`, `semantic_discrimination`, `text_flashcard`, `listening_flashcard`
  (`exercises.tags` carries no judge key for any of these — 0/30, 0/20, 0/30, 0/30). The judges that *would* cover
  distractor plausibility / answer entailment (`judge_distractor_plausibility`, `judge_answer_entailment`,
  `cloze_judge`) have **no prompt_templates rows** → they fail-open (silently accept) on every call.
- **Structured judge columns are never populated:** every `llm_calls` row in the window has
  `judge_verdict = NULL`, `judge_confidence = NULL`, `cost_usd = NULL`. Verdicts live only in `exercises.tags`.
- **`distractor_tags` cross-check:** the embedded `content.distractor_tags` are mostly the generic label
  `"semantic"` and are sometimes wrong (e.g. tagging a second-correct option as a clean distractor); they did not
  catch any of the trivial/sense-drift distractors I flagged.

---

## 6. Model / slug health  ⚠️ highest-severity, config-level

| task_name | lang | configured model | active? | concern |
|---|---|---|---|---|
| cloze_distractor_generation | 2 (EN) | `google/gemini-flash-1.5` | ✅ v2 | **Model slug 404-delisted** (see below) |
| cloze_distractor_generation | 1 (ZH) | `google/gemini-flash-1.5` | ❌ inactive | inactive **and** dead slug → `_load_models` raises |
| exercise_sentence_generation | 2 (EN) | — | **MISSING** | no row at all → `_load_models` raises for EN |
| exercise_sentence_generation | 1 (ZH) | `google/gemini-flash-1.5` | ✅ | dead slug |
| tl_nl_translation_generation | 2 (EN) | — | **MISSING** | EN falls back to the ZH prompt text (see language-blind bug) |
| tl_nl_translation_generation | 1 (ZH) | `google/gemini-flash-1.5` | ✅ | dead slug |
| semantic_discrimination_generation | 1 & 2 | `google/gemini-flash-1.5` | ✅ | dead slug (model only used for prompt text; gen uses cloze model) |
| context_spectrum_generation | 1 (ZH) | **NULL** | ✅ | active row with null model/provider |
| cloze_distractor_judge | 2 (EN) | `google/gemini-2.5-flash-lite` | ✅ | **live, healthy** |
| cloze_distractor_judge | 1 (ZH) | `deepseek/deepseek-chat` | ✅ | **live, healthy** |
| cloze_judge / judge_distractor_plausibility / judge_answer_entailment | 1 & 2 | — | **MISSING** | judges fail-open (no rows) |

**The dominant finding:** `google/gemini-flash-1.5` — the model configured for essentially the entire
`exercise_generation` pipeline (sentence gen, cloze/tl_nl/semantic generation, both languages) — is **delisted on
OpenRouter**. Live probe:
```
google/gemini-flash-1.5      → 404 NotFoundError: "No endpoints found for google/gemini-flash-1.5."
google/gemini-2.5-flash-lite → OK
deepseek/deepseek-chat       → OK
qwen/qwen3.7-plus            → OK
```
Corroborating: this slug has had **zero `llm_calls` in 21+ days**, while live traffic runs on
`gemini-2.5-flash-lite` (1202), `deepseek-chat` (356), `qwen3.7-plus` (109). **As configured, the
`services/exercise_generation` vocabulary pipeline cannot generate a single exercise for EN or ZH** — first it
fast-fails in `_load_models` (missing/inactive rows), and even past that every generation call would 404.

This is the **same failure class** as the 2026-06-09 `qwen/qwen-max` rot ([[log]]), but on a *different* pipeline.
That fix repaired the `vocabulary_ladder` templates; the legacy `exercise_generation` templates were never touched
and still point at a long-dead `gemini-flash-1.5`.

**Related code-level latent bug — language-blind template selection.** `base_generator.load_prompt_template`
(`services/exercise_generation/base_generator.py:123`) selects the prompt by `task_name` + latest `version`
**only — not filtered by `language_id` or `is_active`**. Consequences observed:
- ZH cloze would use the **English** `cloze_distractor_generation` v2 prompt (highest global version).
- EN sentence generation uses the **Chinese** `exercise_sentence_generation` prompt (only version that exists), which
  is also grammar-oriented (`{pattern_code}`/`{description}`) rather than vocabulary-oriented.

---

## 7. Prioritised recommendations

1. **(CRITICAL) Decide the pipeline's fate, then fix the model slug.** If `services/exercise_generation` is still
   live, replace `google/gemini-flash-1.5` everywhere via a forward migration (mirror the qwen-max fix). Affected
   rows: `prompt_templates` ids 39, 40, 68, 147 + the `*_generation` tasks for langs 1/2. Default in
   `services/exercise_generation/llm_client.py:17` is also `google/gemini-flash-1.5` — change it. If the pipeline is
   superseded by `vocabulary_ladder`, mark it deprecated and stop exposing `run_vocabulary_batch` (the admin
   "generate exercises" path) to avoid silent dead-on-arrival runs.
2. **(CRITICAL) Add the missing / inactive templates** so `_load_models` can resolve: insert EN(2)
   `exercise_sentence_generation` and `tl_nl_translation_generation`; activate ZH(1) `cloze_distractor_generation`;
   give `context_spectrum_generation` (lang 1) a real model/provider. Table: `prompt_templates`.
3. **(HIGH) Fix `tl_nl_translation` for same-language learners.** When `tl_language == nl_language`, the task is not a
   translation — either skip the type (drop from `VOCABULARY_DISTRIBUTION` in
   `services/exercise_generation/config.py:95` for EN-UI/EN-target) or change the distractor strategy so options are
   genuinely-incorrect, not tense variants. Today it is 0% acceptable.
4. **(HIGH) Add a validity/entailment judge to `semantic_discrimination`** (mirror the ladder's
   `sentence_validity` judge) to catch the keyed-answer bug where valid English is labeled "wrong" for polysemous
   words. Generator: `services/exercise_generation/generators/semantic.py`. Also constrain distractors to *plausible*
   misuse, not gibberish.
5. **(HIGH) Make the cloze judge actually act.** Today `cloze_distractor_judge` rejects distractors but the exercise
   still ships them. Wire rejections to remove/replace options (or block the item) in the cloze generator
   (`services/exercise_generation/generators/cloze.py`) — otherwise judging is wasted spend.
6. **(MEDIUM) Fix language-blind template selection** in `base_generator.load_prompt_template`
   (`services/exercise_generation/base_generator.py:123`): filter by `language_id` and `is_active`, order by version.
7. **(MEDIUM) Sentence sourcing / difficulty gating.** Constrain mined sentences to the sense's level (the coffee
   corpus yields C2 sentences for A1 words) and strip stray markdown bold from non-target tokens before persisting.
   Also diversify: the same 3 sentences are reused across text/listening/cloze/tl_nl per sense.
8. **(MEDIUM) Observability.** Generators log `llm_calls.task_name='unknown'` and never populate
   `judge_verdict / judge_confidence / cost_usd`. Tag generation calls and persist judge verdicts/cost so judge
   agreement and spend are queryable. Note for future evals: the judge label is `cloze_distractor_judge`, **not**
   `judge_%` — a `task_name LIKE 'judge_%'` filter misses it.
9. **(LOW) Re-run Chinese** on a non-rate-limited live slug (`deepseek/deepseek-chat`, or BYOK qwen) to measure the
   unmeasured hanzi/pinyin/audio-confusable-distractor dimension.

---

## 8. Open questions

See frontmatter `open_questions`. Summary: (a) is this pipeline still meant to run at all? (b) should
`tl_nl_translation` exist for same-language pairs? (c) should the cloze judge's verdicts change shipped content?
(d) does `semantic_discrimination` need a validity judge? (e) Chinese quality remains unmeasured.

---

## Related pages
- [[features/exercises]] / [[features/exercises.tech]] — this pipeline (marked DEPRECATED 2026-05-21, merged into [[features/practice-engine]])
- [[features/exercise-generation-prompts]] — verbatim prompt text + judge smoke queries
- [[reviews/exercise-generation-audit-2026-06-07]] — the *vocabulary_ladder* audit (sibling pipeline; judge-coverage gaps)
- [[database/schema.tech]] — `exercises`, `prompt_templates`, `llm_calls`
- [[log]] — 2026-06-09 qwen/qwen-max slug-rot (same failure class, ladder pipeline)
