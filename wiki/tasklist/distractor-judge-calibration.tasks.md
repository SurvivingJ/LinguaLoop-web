---
title: "Distractor Judge Calibration — Task Breakdown"
feature: comprehension-tests
prose_page: ../features/comprehension-tests.md
tech_page: ../features/comprehension-tests.tech.md
analysis_page: ../evaluations/distractor-judge-language-divergence-2026-08-16.md
two_axis_page: ../evaluations/distractor-judge-two-axis-2026-08-20.md
total_tasks: 10
done: 8
last_updated: 2026-08-20
---

# Distractor Judge Calibration — Task Breakdown

Implements the fixes identified in
[[evaluations/distractor-judge-language-divergence-2026-08-16]]. The v4 Likert judge rejects 30% of
zh questions (vs 4% en) and its review-queue channel fires only in English. The analysis found
three independent causes plus one unrelated content defect.

---

## Established facts — read before starting

Verified 2026-08-16 against the live DB and working tree. Do not re-derive these.

1. **The three v4 judge prompts are faithful translations of each other.** Same corrective
   paragraph, anchors, worked example and output contract. Do **not** go looking for a translation
   bug — there isn't one. The zh/ja missing middle is model behaviour.
2. **`qwen3.6-flash` emits only {5, 4, 2}; `gemini-3.1-flash-lite` emits {5, 4, 3, 2}.** No model
   emitted a single **1** across 450 distractors. Band 1 ("also arguably correct") has never fired.
   *Refined by TASK-718 over 1,800 further ratings: qwen's collapse to {5, 4, 2} is near-total but
   not absolute (one 3 and one 1, both in ja), and band 1 has now fired three times. Both stay rare
   enough that the substance holds — but do not assert either as a hard invariant.*
   **Superseded operationally: qwen no longer judges anything. See TASK-718.**
3. **`keywords=` is accepted by `judge_distractor_plausibility` and never passed by its only
   caller** (`question_generator.py:480`). Slot `{5}` always renders the fallback string.
4. **The prompt never uses slot `{4}` for anything** beyond printing the label, despite the module
   docstring at `distractor_plausibility.py:89-93` claiming it drives type-specific handling.
5. **Rejects do not reach `generation_review_queue`.** Only `_judge_flags` (band 3) does, via
   `orchestrator.py:66`. Human review load is 2.7%, not 18%.
6. **The old measurement harness passed a bare integer into `{4}`.** Any re-measurement must pass
   the `type_code` string (`vocabulary_context`, …) as production does, or the numbers are not
   comparable to live behaviour.
7. **Live judge prompt version is 4**, rows exist for all three languages
   (`task_name='test_distractor_plausibility'`).
   *Superseded 2026-08-19: versions are **not uniform** — live is **zh v6, en v4, ja v4**. zh went
   to v6 via `zh_ja_prompt_metalanguage_sweep.sql` (v5 already existed, inactive). Always SELECT
   before assuming a version.*
8. **The live judge model is `google/gemini-3.5-flash-lite` for all three languages** — not the
   `3.1-flash-lite` that TASK-718 and the analysis page record. Both are right about their own
   scope: TASK-718 moved zh/ja off qwen onto 3.1, then
   `migrations/consolidate_gemini_on_3_5_flash_lite.sql` (2026-08-16, operator policy: one gemini
   slug system-wide) moved every **active** gemini row to 3.5. Inactive rows keep the slug they
   ran under, which is why the v5 rows still read 3.1. **TASK-718's policy stands; its slug is
   stale.** Any reject-rate comparison against §1 must account for this — the §1 numbers were
   measured on qwen for zh/ja.
9. **The §1 baseline reject rates are superseded twice over and must not be reused.** Fresh
   generation on the live stack (2026-08-19, TASK-721) measures **zh 0/59, en 1/60, ja 0/60** —
   0.6% overall, against §1's 30% / 4% / 12%. Re-measure the baseline before writing any
   reject-rate acceptance criterion.
10. **`prompt_templates.task_name` and `llm_calls.task_name` are DIFFERENT namespaces, and the
    judges rename themselves between them.** The judge modules define both and the `llm_calls` one
    carries a `judge_` prefix — e.g. `answer_entailment.py:74-75` sets `_PT_NAME =
    'test_answer_entailment'` (prompt row) and `_TASK_NAME = 'judge_answer_entailment'` (telemetry).
    Querying `llm_calls` with the prompt-row name returns **zero rows for a judge that is logging
    perfectly well**, which reads exactly like a missing-telemetry defect. This cost TASK-723 a
    false finding. Grep the module for `_TASK_NAME` before concluding a judge does not log.
11. **The distractor judge's two axes are NOT symmetric in usefulness, measured 2026-08-20
    (TASK-719).** Under v7 the **fit** axis is effectively binary — zero 3s across 537 distractors
    in all three languages, and band 4 nearly vanished (zh 47→2, ja 65→2) — while **confusability**
    carries the entire middle and produced 100% of the flags. Do not "simplify" this judge by
    keeping fit and dropping confusability; fit alone now carries almost no information, and the
    v4 appearance that it did was the conflation. Also: **the also-correct failure is rare, not
    newly detectable.** It fires 1/537 on the confusability axis vs 3/1,800 for the old band 1 —
    the same rate. Any argument for v7 has to rest on the review signal, not on catching
    also-correct distractors.

12. **Live `test_distractor_plausibility` state (verified 2026-08-20):** live is **zh v6, en v4,
    ja v4** on `google/gemini-3.5-flash-lite`. **v7 exists in all three languages and is
    INACTIVE** — the two-axis rubric, staged pending TASK-726. En and ja therefore have no v6;
    the gap is deliberate so one integer can name a three-language measurement arm. The v7 code is
    live-safe against v4/v6 rows (a single rating reads as `fit`, whose bands are v4's), so the
    activation flip needs no code deploy — only a process restart, because `_cfg_cache` is
    process-lifetime.

13. **Live `test_answer_entailment` state (verified 2026-08-19, post-TASK-723):** **v3 active in
    all three languages**, on the Likert 1-5 scale. Models: **zh `deepseek/deepseek-chat`, en and
    ja `google/gemini-3.5-flash-lite`** — ja moved off `qwen/qwen-2.5-72b-instruct` on 2026-08-19
    (`entailment_ja_v3_onto_gemini_3_5_flash_lite.sql`) on measured evidence. Inactive rows remain
    at en v1 / zh v2 / ja v2 on the old float scale; **v3 code refuses to judge on them**
    (`_is_pre_likert`), so do not reactivate one to "roll back" without reverting the code too.

---

## TASK-717: Make the judge's dead prompt slots load-bearing

**Status:** [~] Partially done (2026-08-16) — **plumbing shipped, prompt fix measured and
reverted.** Both §4 hypotheses were tested on the frozen sample and both are wrong. zh
`vocabulary_context` scored **9/16 in all four arms** — invariant to the type string, the
type-conditional rubric and the subject line — so the target bucket is model behaviour, not a
rubric defect. The v5 rubric also *created* 5 en `vocabulary_context` rejects (v4: 0), and the
subject line raised ja rejects in both arms containing it. v4 is live again; v5 rows retained
inactive. Full results and attribution:
[[evaluations/distractor-judge-language-divergence-2026-08-16]] §10.
**Remaining work moves to TASK-718**, which this result promotes to the load-bearing task.
**Feature:** comprehension-tests
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
The judge prompt has two placeholders that carry no signal in production: `{5}` (subject/domain
keywords) is never passed by the caller, and `{4}` (question type) is printed but never acted on.
Band 2 — which produces **100% of all zh and ja rejects** — is a domain-membership test, so the
judge is currently being asked to invent the domain boundary itself, and to apply a same-subject
test to question types where it is a category error. Fix both, in one prompt version bump (v5).

**Acceptance Criteria:**
- [x] `question_generator.py` passes `keywords=` to `judge_distractor_plausibility` on every call,
      sourced from the same topic/keyword data the prose generator already holds.
      *Threaded orchestrator → `generate_questions` → `_apply_judges` → judge, from the
      already-translated `translated_topic`/`translated_keywords`. Gated by
      `JUDGE_SUBJECT_KEYWORDS`, default OFF on the measured evidence below.*
- [x] v5 prompt rows exist for zh/en/ja with a **type-conditional rubric block** covering three
      families: sense-based (`vocabulary_context`), intent-based (`author_purpose`, `main_idea`),
      and fact-based (`literal_detail`, `supporting_detail`, `inference`).
      *Built by splicing into the live v4 text, so v5 is provably v4 + one block (md5-verified);
      bands, scale, worked example and models untouched.*
- [x] For `vocabulary_context`, the prompt states explicitly that distractors are competing
      meanings of the target expression and must be judged against **the word, not the passage
      subject** — an option unrelated to the passage topic is not off-topic.
- [x] For intent types, "off-topic" is redefined as an intent unrelated to the text, not a topic
      the passage omits.
- [~] v4 rows set `is_active = false`; v5 set true. Existing rows are not deleted.
      *Applied, then **reverted** — v4 active, v5 inactive, no rows deleted. Reverted because the
      measurement below showed net harm.*
- [ ] **FAILED.** Re-measurement over the same 150-question sample, **passing the `type_code`
      string**, shows zh `vocabulary_context` rejects materially reduced from the 8/16 baseline.
      *No reduction whatsoever: **9/16 in all four arms**. Not noise-limited — literally the same
      count under every intervention. en `vocabulary_context` went 0 → 5 (harm). See §10.*
- [x] A regression test asserts `keywords` reaches the template (guards against the parameter
      silently going dead again).
      *`tests/test_judge_subject_keywords.py`, 22 tests. Mutation-verified: deleting the
      argument at the judge call site makes the end-to-end test fail. Also pins the
      default-off gate in both directions, so the off-state cannot decay back into the
      original silent-dead-parameter bug.*

**Technical Notes:**
Prompt rows live in `prompt_templates`, not in code — see the memory note on model-slug rot. Keep
`model` unchanged in this task (zh/ja stay on `qwen3.6-flash`); model choice is TASK-718's decision
and mixing them makes the re-measurement uninterpretable. The migration must use `ON CONFLICT DO
UPDATE`, per the ladder-prompt migration lesson.

Do not touch the band definitions or the 1-5 scale in this task — that is TASK-719. This task is
purely about giving the existing rubric the inputs it already asks for.

**Files to Create / Modify:**
- `migrations/` — new migration seeding v5 rows for all three languages, deactivating v4
- `services/test_generation/agents/question_generator.py` — pass `keywords=` at the judge call
- `services/exercise_generation/judges/distractor_plausibility.py` — update the module docstring so
  it describes what the prompt now actually does
- `tests/` — regression test for keyword propagation

**Verification:**
Re-run the flag-rate harness over the frozen 150-question sample with the `type_code` string.
Compare per-type reject counts against the baseline table in
[[evaluations/distractor-judge-language-divergence-2026-08-16]] §1. Expect the largest movement in
zh `vocabulary_context` (8/16 baseline) and zh `author_purpose` (3/7 baseline).

---

## TASK-718: Cross-model judge A/B — settle judge harshness vs content quality

**Status:** [x] **Done (2026-08-16). Verdict: judge-driven — the model swap fixes it.** zh rejects
go **16/50 (32%) → 1/50 (2%)** on the live v4 prompt when only the judge model changes. Under a
common judge, zh is the *cleanest* of the three languages (zh 2%, en 4%, ja 6%), so the content
contribution is indistinguishable from zero. zh and ja moved to `google/gemini-3.1-flash-lite`,
applied live. Full results: [[evaluations/distractor-judge-language-divergence-2026-08-16]] §11.
**Feature:** comprehension-tests
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-717

**Description:**
The open question from the analysis: is the residual zh reject rate (21% excluding
`vocabulary_context`, vs en 5%) judge harshness or genuinely weaker zh content? The decisive
experiment holds content constant and varies only the judge model — run the identical zh and ja
samples through both `qwen3.6-flash` and `gemini-3.1-flash-lite` on the v5 prompt.

**Acceptance Criteria:**
- [x] Both zh and ja samples scored by both models on the v5 prompt; en included as control.
      *Widened to a full 2×2×3 factorial — **both prompt versions**, because v5 is reverted and v4
      is live, so a decision measured only on v5 could not be applied to the `model` column. The
      factorial also puts qwen on **English**, the crossover cell that separates "harsh model" from
      "harsh at Chinese". 600 calls over the frozen 150-question sample.*
- [x] Full rating distribution reported per (language × model), including whether gemini produces a
      middle band in zh/ja.
      *§11. **Yes** — gemini emits a middle band in zh (1) and ja (2) on v4, where qwen emits none.
      Thin, but `generation_review_queue` stops being English-only for free. Band 1 also fired for
      the first time ever (3 across 1,800 ratings).*
- [x] A verdict recorded: judge-driven, content-driven, or mixed with an estimated split.
      ***Judge-driven, ~100%.** The published gap was zh 30% vs en 4% (26pp); under a single judge
      it is −2pp. Mechanism is a qwen×Chinese interaction, not a general harshness gradient —
      qwen scores en 10% / ja 8% but zh 32%. Decisive evidence: all 25 zh distractors qwen rejected
      were rated 4 or 5 by gemini, and the two judges' zh reject sets are **disjoint**.*
- [x] Per-language judge model decided and, if changed, applied to the `model` column.
      *zh + ja → `google/gemini-3.1-flash-lite` via
      `migrations/distractor_judge_model_zh_ja_gemini.sql`, applied live. v5 rows updated too, so
      activating v5 later cannot silently restore qwen. v1–v3 left as history.*
- [x] Cost recorded (expected: cents — ~200 calls on flash-tier models).
      ***$1.11** for 600 calls / 11 min — over the estimate because the factorial tripled the call
      count and qwen is 6.7× gemini's per-call price ($0.00313 vs $0.00047). That price gap is
      itself a result: the swap cuts zh/ja judge cost ~85%.*

**Outcome notes:**
- The harness is now `scripts/measure_judge_flag_rate.py` (`--judge-model`, multi-arm,
  `--report-only`), no longer a scratchpad file.
- **v5 stays inactive.** It is neutral-to-harmful under *both* models (en 2→5 under gemini,
  ja 4→8 under qwen), so §10's revert stands on wider evidence.
- **What this does NOT establish:** that gemini's acceptances are correct. Inter-judge agreement on
  the reject class is ~0, so no model's reject signal is validated in absolute terms. The support
  for "the zh rejects were false" is the manual read in §5, not this experiment. A gold set is owed
  and is now the binding constraint on TASK-719/720 — see the revised note under TASK-719.

**Technical Notes:**
If gemini yields a middle band in zh/ja, the flag channel becomes multilingual for free and much of
TASK-719's motivation weakens — so **run this before committing to the two-axis redesign**.
Note this is the third time `qwen3.6-flash` has been the outlier on this prompt (it returned no
ratings at all under v3), which is itself evidence for the model swap.

**Files to Create / Modify:**
- `scripts/` — promote the scratchpad flag-rate harness into a committed script with a
  `--judge-model` override
- `wiki/evaluations/` — results appended to the 2026-08-16 analysis page, or a new dated page

**Verification:**
Reject rate for zh under gemini vs under qwen on identical content. A drop from ~21% to ~5%
indicates the judge; a rate that holds indicates the content.

---

## TASK-719: Split the rating onto two axes

**Status:** [x] **Done (2026-08-20) — built, measured, and NOT activated.** Code, tests and v7
prompt rows in all three languages are landed; the rows are `is_active = false`. Full results:
[[evaluations/distractor-judge-two-axis-2026-08-20]].

The task was executed on an explicit operator decision to split the axes now and park the
*scale redesign* — the two are separable, and the gold-set blocker recorded below applies to
retuning cut points, not to asking the judge two questions instead of one. The staging
disposition preserves everything the blocker was protecting: nothing changes at runtime.

**The revised status note below was right, and the measurement settled it.** Band 1's target
failure (a distractor that is also correct) is **rare, not undetectable**: it fires 1/537 on
the confusability axis, against 3/1,800 for the old band 1 — statistically the same rate. The
split did not uncover hidden also-correct distractors; it made a rare event legible and gave
it an unambiguous home. What the split *did* deliver is a usable review signal: every flag in
all three languages is a confusability flag, and the fit axis turns out to be near-binary.

**The cost is the finding to argue about.** Question-level review volume goes from 0-3% to
**22-47%**. That is what has to be justified before activation, and it cannot be justified
without the gold set.

*Original note, retained — its prediction held:* TASK-718 delivered the middle band in all
three languages by swapping the model, which was one of this task's two goals. What it also
exposed is that the two judges' reject sets are **disjoint** — agreement on the class that
gates content is ~0. Redesigning the scale before a gold set exists would tune an unvalidated
signal. **Build the gold set first**; only then decide whether the two-axis split is still
needed, since band 1's target failure may simply be rare rather than undetectable.
**Feature:** comprehension-tests
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-718

**Description:**
The 5-point scale conflates *topical distance from the passage* (bands 5/4/2) with *confusability
with the correct answer* (bands 3/1), forcing a 2-D judgment into one integer. Bands 3 and 1 also
overlap semantically. Replace with two explicit per-distractor fields and move the verdict
arithmetic entirely into Python, where it is already tunable.

**Acceptance Criteria:**
- [x] Judge returns two ratings per distractor: topical fit and confusability-with-answer.
      *v7 prompt rows, zh/en/ja, three-element `[fit, confusability, reason]` arrays. Both axes
      fire in all three languages; zh uses all five confusability bands, en and ja four of five.*
- [x] A successor to `likert_to_verdict` maps the pair to accept/flag/reject, with cut points as
      named constants.
      *`schemas.axes_to_verdict`, returning `(verdict, axes, rating)`. Constants: `REVIEW_BAND`,
      `FIT_REJECT_MAX`, `CONFUSABILITY_ALSO_CORRECT`, `CONFUSABILITY_INERT_MAX`. `likert_to_verdict`
      is untouched — seven other judges share it.*
- [x] Band 1's target failure (a distractor that is also correct) is detectable on the
      confusability axis — this is the case that has fired **zero** times to date.
      ***Detectable, and detected: 1/537.** But do not read that as vindication of the original
      premise. The old band 1 fired 3/1,800 (0.17%); this is 0.19% — the same rate. The failure was
      rare all along, which is what the revised status note predicted. The gain is that it now has
      an unambiguous home instead of sharing band 1 with "absurd".*
- [x] `DistractorPlausibilityVerdict` handles the two-field shape; the missing-rating (`None`)
      semantics from v4 are preserved on both axes.
      *Per-axis. A distractor rated on one axis only is judged on that axis; `None` on both routes
      to `accept_item` with no fabricated score. 3/537 unrated in en v7, handled as designed.*
- [x] Existing normaliser tests still pass; new tests cover the two-field shape.
      *`tests/test_distractor_missing_rating.py` unchanged and green — `per_distractor` survives as
      a read-only alias for `fit`. `tests/test_distractor_two_axis.py` adds 26. Full suite 1,869.*

**Outcome notes:**
- **A v4/v6 row still produces identical verdicts under v7 code**, because `fit`'s bands are
  deliberately the v4 bands and an absent `confusability` contributes nothing. So the code
  deployed without a coordinated prompt cutover — the opposite of TASK-723, where the two scales
  inverted at `1`. Pinned by `test_fit_reproduces_the_v4_scale_exactly`, and confirmed empirically
  by the `live` arm reproducing the pre-split numbers.
- **The fit axis lost its middle band and most of band 4** (zh 47→2, ja 65→2; zero 3s anywhere).
  Splitting made the model *more* decisive about subject membership, not less. Coherent — the
  single integer had been absorbing hesitation about both questions at once — but it means the fit
  axis alone now carries almost no information, so it cannot be kept and confusability dropped.
- **The ja prompt failed the contract check three times** on `required_literals`: qwen wrote `JSON`
  as ジェイソンオブジェクト. Repaired by substituting the token back. `response_format='json_object'`
  needs it and the failure would have been a quietly degraded judge, not an error.
- Cost $0.2738 for 358 calls / 1.4 min.

**Technical Notes:**
`schemas.py` `_normalize` is already a large defensive coercion layer for off-schema model output.
Extend it rather than replacing it — the hallucinated-extra-rows and bare-list paths are all
load-bearing and were each added in response to a real observed failure.
*Done as directed: `_pair` became `_triple`, a three-key field-selector shape was added, and every
existing branch was kept. The discriminator between `{"1":[fits],"2":[confs],"3":[reasons]}` and
three per-distractor triples is that a triple always carries its reason string inside its own
array — `tests/test_distractor_two_axis.py` pins both readings.*

**Inherited from TASK-724 (2026-08-18):** natively-authored zh/ja `cloze_distractor_judge`
prompts are already written and staged **inactive** at v2. They were rewritten out of English but
smoke-testing showed they change *verdict behaviour*, not just language — the zh rewrite catches an
also-correct distractor the live row misses, then over-rejects two clearly-wrong ones. Decide their
fate against the gold set rather than promoting them blind:

```sql
UPDATE prompt_templates SET is_active = (version = 2), updated_at = now()
 WHERE task_name = 'cloze_distractor_judge' AND language_id IN (1, 3);
```

Whatever this task does to the rubric should be authored *into* those rows, not back into the
English ones.

**Files to Create / Modify:**
- `services/test_generation/schemas.py` — **DONE.** Two axis fields, three verdict helpers, four
  named cut points, `_triple` normalisation.
- `services/exercise_generation/judges/distractor_plausibility.py` — **DONE.**
- `services/exercise_generation/judges/base.py` — **DONE (not in the original list).**
  `JudgeOutcome.axes` / `.flag_axes`, both optional so the eight single-axis judges are untouched.
- `migrations/distractor_plausibility_prompt_v7_two_axis.sql` — **DONE.** v7, not v6: zh was already
  on v6. Uniform 7 across all three languages so one integer spans a three-language measurement arm.
- `scripts/apply_distractor_judge_v7.py` — **DONE (new).** Writes the rows and reads them back;
  `--emit-sql` generates the migration from the same source of truth so the two cannot drift.
- `scripts/rewrite_prompt_native.py` — **DONE.** New `test_distractor_plausibility` spec; `Spec`
  gained `render_positional` because the judge rows use `{0}`-`{5}`, which `**render_args` cannot
  render — the check would otherwise have passed a row that explodes at judge time.
- `scripts/measure_judge_flag_rate.py` — **DONE.** Per-axis distributions and the review-load-by-axis
  table. `ratings` keeps its name and carries `fit`, so pre-split arms stay comparable.
- `tests/test_distractor_two_axis.py` — **DONE (new, 26 tests).**
  `tests/test_distractor_missing_rating.py` — **unchanged and green**, which is the point.
- `data/eval/distractor_judge_v7_{zh,en,ja}.txt`, `data/eval/distractor_two_axis_2026-08-20.json`

**Verification:**
Re-measure; confirm the confusability axis produces non-zero counts in the "also correct" region,
which the single-axis scale never did.
*Done. Non-zero (1/537) — and the honest reading is that the region is genuinely rare rather than
previously invisible; see the acceptance note above.*

---

## TASK-720: Redefine the review band as explicit uncertainty

**Status:** [x] **Done (2026-08-20) — shipped with TASK-719, measured, NOT activated.** Band 3
means "the judge is not confident" on both axes, and the queue records which axis fired. Full
results: [[evaluations/distractor-judge-two-axis-2026-08-20]].

**The single most useful thing this task produced is that the attribution is not uniform — it is
unanimous.** Every flag, in every language, is a **confusability** flag; the fit axis produced
zero. The queue no longer says "a judge was unsure", it says "the judge could not tell how
tempting this option would be", which is a specific question a reviewer can answer. That was
worth recording the axis for on its own.

**And the volume is the reason this is staged.** Question-level review goes from 0-3% to
**22-47%** — roughly one question in three. The task asked for the volume to be sized before
rollout; it is sized, and it is the number the activation decision turns on.
**Feature:** comprehension-tests
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-719

**Description:**
Band 3 is defined as "essentially a paraphrase of the correct answer" — a narrow defect category
overlapping band 1. No model applies it as written: all four English flags in the baseline were
*not* paraphrases of the answer. `gemini` is already using it as a generic "unsure" band, which is
what a review queue actually wants. Make that official.

**Acceptance Criteria:**
- [x] The review band is defined as judge uncertainty ("rate this if you are not confident the
      distractor is sound"), not a specific defect type.
      *Band 3 on **both** axes, worded per axis: "you cannot decide whether it belongs to this
      subject" / "you cannot judge how tempting it would be", each followed by an explicit "do not
      guess a 4 or a 2 instead". The old "essentially a paraphrase of the correct answer" defect did
      not vanish — it moved to confusability 5 (also-correct), where it is a **reject**, not a flag.*
- [x] `generation_review_queue` rows carry which axis triggered the review.
      *`orchestrator._flag_reasons` writes `distractor_plausibility:confusability`; the full per-axis
      rating map rides in `judge_scores`. Single-axis judges and pre-v7 distractor flags keep their
      bare name, so existing rows stay comparable.*
- [x] Measured queue rate is non-zero in **all three** languages.
      *zh 31, en 13, ja 17 flagged distractors per ~180 — and, unlike TASK-718's thin middle band,
      the rate is now large enough to be a workload rather than a curiosity.*
- [x] Queue volume is sized and recorded before rollout, so review time can be budgeted.
      ***zh 28/59 (47%), en 13/60 (22%), ja 17/60 (28%)** of questions, against live 1.7% / 3.3% /
      0.0%. Decomposed: ~75% is band-3 uncertainty, ~25% is the new inert rule
      (`CONFUSABILITY_INERT_MAX`), which is a named constant so that quarter can be dropped by
      setting it to 0 without touching three prompts.*

**Files to Create / Modify:**
- `migrations/distractor_plausibility_prompt_v7_two_axis.sql` — shared with TASK-719; the review
  band is defined in the same prompt rows as the axes, so they could not ship separately.
- `services/test_generation/orchestrator.py` — **DONE.** `_flag_reasons` extracted from
  `_write_review_queue_rows` so it is unit-testable; the writer itself is best-effort and swallows
  everything, which is exactly where a formatting bug would have hidden.
- `services/test_generation/agents/question_generator.py` — **DONE (not in the original list).**
  `_judge_flags` and the reject diagnostic both carry `axes` + `flag_axes`; the reject log line
  names the axis, because "rejected at 2" means nothing without it.

**Verification:**
Confirm zh and ja produce queue entries at all — currently they produce exactly zero.
*Done — zh 31 and ja 17 flagged distractors on the 537-item sample, all on the confusability axis.*

---

## TASK-721: Give the generator prompts a distractor specification

**Status:** [x] **Done (2026-08-19) — built, measured, and NOT activated.** All 18 rows authored
and landed as new versions, `is_active = false`, md5-verified. The before/after shows **no benefit
and a consistent adverse direction**, so the rows stay staged. This is the TASK-717 v5 outcome and
the same disposition applies.
**Feature:** comprehension-tests
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-717

**Description:**
No `question_*` generator prompt in any language contains a single line of distractor guidance —
all 18 describe only how to build the question. The distractor rubric exists solely on the judge
side, so content is filtered against a specification it was never given. Port the rubric into the
generators, inverted from "rate this" into "build distractors like this".

> **The premise was stale by the time it was executed.** "No prompt in any language contains a
> single line of distractor guidance — all 18" was true when written. On a full read of all 18
> live bodies (2026-08-19) it is **9 rows** with none at all, **6** with one incidental line, and
> **3** with a real partial specification (`zh inference`, `zh vocabulary_context`,
> `ja vocabulary_context` — all TASK-722/724 native rewrites). A keyword probe finds only 6 of
> those 9, missing `ja vocabulary_context` *and* both en rows, because the en prompts say "Wrong
> answers" and the probe had no English term. What no row stated: the arguably-correct prohibition,
> and the same-domain / absence-is-fine rule that is the most load-bearing sentence in the judge
> prompt.

**Acceptance Criteria:**
- [x] All 18 `question_*` rows carry a distractor-construction block appropriate to their type
      family (sense / intent / fact), mirroring the TASK-717 judge rubric.
      *Spliced immediately before each row's output contract at a per-row anchor asserted to occur
      exactly once, so each new body is provably the incumbent verbatim plus one block. zh/ja
      blocks authored natively by `qwen/qwen3.8-max` (all 12 clean on attempt 1); en hand-authored
      as a direct inversion of the live en v4 rubric, because `rewrite_prompt_native.LANG_ID` is
      `{'zh': 1, 'ja': 3}` and the "brief in the target language" rationale is vacuous for en.*
- [x] Each includes at least one worked distractor set showing a good distractor and a rejected
      one with the reason. *One GOOD plus **two** REJECTED per row, one per prohibition, reusing
      each row's own few-shot passage so no second scenario is introduced.*
- [x] Explicit prohibition on the two failure modes: a distractor that is also arguably correct,
      and a distractor that is a paraphrase of the answer.
- [x] Reject rate measured before and after; the comparison is recorded.
      ***Measured. The result does not support activation — see below.***

### Result — no benefit, consistent adverse direction, rows retained inactive

Fresh generation both arms: 10 passages per language from `data/eval/entailment_sample_150.json`,
6 types each, difficulty cycling 4/6/8, `previous_questions` accumulating per passage as in
production, one shot per cell (no regen — `avoid_context` would mutate the prompt under
measurement). Judged by the **live** judge (zh v6 / en v4 / ja v4, all
`google/gemini-3.5-flash-lite`). Generator models unchanged, per TASK-717.

| lang | rejects before | rejects after | flags before | flags after | mean rating before | after |
|------|---------------|---------------|--------------|-------------|--------------------|-------|
| zh | 0/59 (0.0%) | 2/60 (3.3%) | 1 | 4 | 4.718 | 4.683 |
| en | 1/60 (1.7%) | 1/60 (1.7%) | 1 | 2 | 4.789 | 4.772 |
| ja | 0/60 (0.0%) | 1/60 (1.7%) | 1 | 2 | 4.600 | 4.578 |

Pooled over 537 / 540 distractors: non-accept (rated ≤ 3) **0.74% → 2.22%**, Fisher exact
**p = 0.075**; mean rating **4.702 → 4.678**. Not significant at 0.05 — but there is no
significant *benefit* either, and the direction is adverse in all three languages independently
(mean down 3/3, rejects up 2/3, flags up 3/3). Nothing here argues for promotion.

**The acceptance criterion could not have succeeded, and that is the more important finding.**
The baseline reject rate is **1 in 179 questions (0.6%)**, against the 30% / 4% / 12% in
[[evaluations/distractor-judge-language-divergence-2026-08-16]] §1 that motivated this task.
TASK-718's model swap and TASK-722/724's native rewrites already removed the reject rate this task
was written to attack. A *reduction* is arithmetically unreachable from 0/59 and 0/60; only harm
was ever detectable. **Any future prompt task on this pipeline should re-measure the baseline
before adopting a reject-rate acceptance criterion** — the §1 table has been superseded twice.

Rows retained inactive rather than deleted (TASK-717 v5 precedent): targets v2–v4, not uniform.
Reversal is `scripts/apply_task721_rows.py --activate` if a gold set ever justifies it.

**Technical Notes:**
This attacks reject rate at the source rather than filtering after the fact, so it should reduce
regeneration cost as well as reject rate. Keep the judge rubric and the generator instruction
textually aligned — if they drift, the generator is optimising against a stale spec.

*Post-hoc: the type-family split (sense / intent / fact) is now measured on BOTH sides and has
moved nothing on either. It failed on the judge in TASK-717 (§10) and shows no benefit on the
generator here. Treat it as refuted rather than untested.*

**Files Created / Modified:**
- `migrations/task721_question_distractor_spec.sql` — 18 rows, staged inactive
- `scripts/task721_blocks.py` — blocks, splice anchors, type-family map
- `scripts/author_task721_blocks.py` — native zh/ja authoring (imports, does not fork,
  `rewrite_prompt_native`); rejects any block containing `{` or `}`, which would `KeyError`
  every generation of that type
- `scripts/stage_task721_templates.py` — splice + contract assertions
- `scripts/generate_question_sample.py` — **the missing generation half of the harness**;
  `measure_judge_flag_rate.py` only judges a frozen sample. Pins template *bodies* via
  `QuestionGenerator(prompt_template=...)`, so an inactive prompt is measurable without
  activating it
- `scripts/apply_task721_rows.py` — staged apply, md5 readback, `--activate`
- `scripts/report_task721.py` — the comparison above

**Verification:**
`audit_prompt_latin.py --all-versions`: all 12 staged zh/ja rows **CLEAN, 0 leaked tokens**, CJK
density up in every one (e.g. `zh literal_detail` 0.769 → 0.887). `apply_task721_rows.py --verify`
OK. `PYTHONPATH=. pytest tests/ -q`: 1806 passed, 3 skipped.

**Two traps recorded for whoever touches these rows next:**
1. **Line endings in `prompt_templates` are mixed** — nine rows CRLF, nine LF. A splice anchor
   containing a newline silently matches nothing in half the table, and reading a body back with
   universal-newline translation rewrites every line ending, so the stored row is no longer
   "incumbent + one block". Read and write with `newline=''`.
2. **Answer position remains unshuffled and badly skewed** — 108 of 179 baseline questions put the
   answer in position 2. Confirms TASK-722: prompt text only moves the mode. The fix is downstream
   shuffling in `question_generator.py`, not prompt wording. Not attempted here.

---

## TASK-722: Rewrite the zh/ja vocabulary_context prompts natively

**Status:** [x] **Done (2026-08-17) — applied live and verified.** Both rows authored from
scratch by `qwen/qwen3.8-max` against a target-language brief (not translated), landed as v2 with
v1 deactivated for zh/ja only; en untouched and still active. Body md5s in the DB match the
authored files byte-for-byte. Harness: `scripts/rewrite_vocab_context_prompt.py`,
smoke: `scripts/smoke_vocab_context_prompt.py`, migration:
`migrations/task722_vocab_context_native_zh_ja.sql`.

**Measured (Latin-script tokens of 2+ chars, excluding JSON keys / type code / placeholder names):**

| row | before | after |
|---|---|---|
| zh `question_vocabulary_context` | 21 leaked | **0** |
| ja `question_vocabulary_context` | 24 leaked | **0** |

Counting only real leaks — each row's own type code is machinery, and excluding it corrects an
earlier overstatement here — every other active row is at **0** except zh `question_inference` (2:
`Martinez` twice), ja `question_main_idea` (2: `vs`) and ja `question_author_purpose` (6). So
`vocabulary_context` was the outlier by an order of magnitude, exactly as the analysis claimed, and
the siblings are cleaner than first reported. Live smoke at
difficulty 8: **zh 3/3 and ja 3/3 clean**, targets 碰一鼻子灰 / 後の祭り / 高をくくって.

**Two findings not in the original brief:**
1. **`question_generator.py` does not shuffle choices** — whatever order the model emits is what
   the learner sees, and neither incumbent said anything about answer position. Both new rows now
   carry an explicit "never always first" rule. It half-worked: across 6 smoke questions the
   answer never landed in position 1, but landed in position **2 all six times** — the models are
   copying the position used in the prompt's own output example. The rule moved the mode rather
   than flattening it. A real fix is downstream shuffling, not prompt text.
2. **Two smaller residual leaks**, both worth folding into the TASK-721 sweep — and note these are
   *different defect classes*:
   - **zh `question_inference` contains `Martinez` twice** — an English proper name inside a
     Chinese few-shot passage. Same class as the TASK-722 defect (English *content* in a CJK
     prompt), just smaller. This is the one to fix first.
   - **ja `question_author_purpose` leaks 6** (`Author`, `Purpose`, `Tone`, `vs` ×3) and ja
     `question_main_idea` leaks 2 (`vs`). This is English *metalanguage* — section headings and
     terms — not English lexical targets, so it does not teach a wrong category. Lower risk.

**Owed:** native-speaker review of both rows (the acceptance criterion allows recording it as owed).
**Feature:** comprehension-tests
**Type:** bug
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
The zh and ja `question_vocabulary_context` generator prompts are literal translations that kept
the English lexical targets. The zh prompt teaches with `'bright'`, `'pick up'` and
`'turn a blind eye'`, and embeds English idioms inside its Chinese few-shot passages
(「共同'pick up the pieces'」); the ja version glosses them into Japanese
(「事態を収拾し（pick up the pieces）」). A Chinese vocabulary-question generator is being
few-shotted on English phrasal verbs — a category Chinese does not have. Independent of the judge
work; fix regardless of TASK-718's outcome.

**Acceptance Criteria:**
- [ ] zh prompt authored natively against 成语 / 惯用语 / 多义词, with Chinese few-shot passages
      containing no English lexical targets.
- [ ] ja prompt authored natively against 慣用句 / 四字熟語 / 多義語, no English glosses in the
      passages.
- [ ] The advanced-level rule is restated in terms meaningful for each language rather than
      transplanted from English ("multi-word expression" is an English-shaped constraint).
- [ ] Latin-run count in both rows drops to JSON keys only (baseline: 19-20 runs; other types
      are 9-14).
- [ ] Native-speaker review of both, or explicitly recorded as owed.

**Technical Notes:**
Same defect class as [[tasklist/ladder-numeric-keys.tasks]] one layer up — that batch removed
English *field names* from ZH/JA prompts; this removes English *content*. Worth a sweep of the
other five types for the same pattern, though the Latin-run counts suggest they are clean.

**Files to Create / Modify:**
- `migrations/` — new `question_vocabulary_context` rows for zh and ja

**Verification:**
Generate 20 zh and 20 ja vocabulary questions; confirm the targets are native lexical units and no
English appears in any generated question or option.

---

## TASK-723: Put every judge on one Likert 1-5 scale with anchored band definitions

**Status:** [~] **Entailment half DONE, activated, measured and verified (2026-08-19). Cloze half
not started — deferred to TASK-719.**

**Status line corrected 2026-08-19 — the "staged, NOT activated" text below was stale.** v3 is
**live in all three languages** (`is_active = true` for zh/en/ja; all six rows share `updated_at`
2026-08-19 10:11:32Z, so activation was one transaction — who ran it is not recorded). The Likert
code is committed, not merely in the working tree. Gold re-measurement and post-rollout band usage
are now both done: [[evaluations/entailment-likert-v3-rollout-2026-08-19]]. Headline: **all five
bands fire in all three languages, 0 unparsed in 450 calls**, overall AUC 0.957. Spend $0.2135.

*Historical account of the staging period retained below.*

Code, tests, migration and harness are landed; the v3 prompt rows exist in the live DB
**inactive**. The prompt and the code are coupled and must cut over together — activating v3 while
the deployed code still expects a float would make every entailment call fail schema validation,
land in the judge's except branch and `safe_accept()`, i.e. the answer-hallucination guard would
silently switch off in all three languages. Cutover order is documented at the top of
`migrations/entailment_likert_v2.sql`: apply → measure v3 on the gold set → deploy code →
activate.

**Correction (2026-08-18): the header's account of the mismatch was wrong, and the guard that was
supposed to make it loud did not work.** The header predicted that deploying v3 code against the
live v1/v2 rows would fail schema validation and `safe_accept` everything. Measured against 391
historical responses in `llm_calls.raw_response`, only 23% do that. **77% returned exactly `1.0`** —
which the prompts explicitly define as *"clearly and directly supports this answer"* — and `1.0` is
a structurally valid Likert `1`, so it passes `_reject_legacy_float_scale`, coerces to `rating=1`
and **inverts into a hard reject** at `question_generator.py:507`. The guard's own docstring named
`1` as the sole overlap point where the scales invert, then returned it unchanged. The 10 observed
`0.0` responses invert the other way: genuine hallucination catches become `safe_accept`.

**Fixed** by re-gating on the template *version* rather than the value shape:
`answer_entailment._is_pre_likert` refuses to judge on a pre-v3 row **before** the LLM call
(`safe_accept` when serving, `JudgeUnavailable` in batch). `_reject_legacy_float_scale` is retained
and re-documented as a backstop for the fractional case only. Tests:
`tests/test_generation/test_judges.py` — refusal path, batch abort, v3 pass-through, and an explicit
pin that a legacy `1.0` is invisible to the schema. The shared `_AE_CFG` fixture was on `version: 1`
and is now `3` (and seeded as a copy, so a test varying the version no longer leaks).

**Also found:** `_cfg_cache` is process-lifetime and never invalidated, so flipping `is_active` does
not reach a process that has already judged in that language. **Cutover is three moves: deploy →
activate → restart.** And `scripts/measure_entailment_ab.py` calls `call_llm` directly with
`AnswerEntailmentVerdict`, bypassing the gate — it can no longer measure v1/v2 rows, only v3.

**Bands (single axis, mutually exclusive — the property the distractor bands lack):**
5 stated explicitly · 4 not stated but the only conclusion allowed · 3 partly supported, another
answer fits equally · 2 unsupported, merely same topic · 1 contradicted or unrelated.
4-vs-3 is *uniqueness*, 2-vs-1 is *absence vs contradiction* — no band is reachable by "a bit less
than" its neighbour.

**Live bug found and fixed en route:** `judges/base.py:accept_item` stamped
`confidence=THRESHOLD_ACCEPT` (0.8) — a *probability* constant — into outcomes from judges that are
all Likert. `distractor_plausibility` logs `worst.confidence`, so whenever the worst outcome was an
unrated item, a 0.8 landed in `llm_calls.judge_confidence` for a task_name that migration declared
Likert-only. That is the same two-scales-in-one-column collision
`null_legacy_judge_confidence.sql` erased 888 rows to clear, quietly reintroducing itself. Now
`None`: substituting 5.0 would fabricate a rating, and the v3 lesson is that a missing rating must
stay visibly missing. `JudgeOutcome.confidence` is now `float | None`.

**Process failure worth recording:** the first apply attempt wrote these rows at **version 2** and
destroyed the live zh and ja templates. `entailment_json_token_zh_ja.sql` had bumped those two rows
in place with `version = version + 1`, so the live set was en v1 / zh v2 / ja v2 — not v1
everywhere — and `ON CONFLICT (task_name, language_id, version)` overwrote them and set them
inactive. Recovered from `phase14_judge_prompt_seeds.sql` plus that migration's suffix, verified by
restored lengths 208 (zh) / 267 (ja). **Always SELECT existing versions for a task before choosing
a version number**; per-task version numbering is not aligned across languages.

**Done:** `judge_answer_entailment` returns 1-5 · `likert_to_verdict` replaces `classify` for it ·
`_reject_legacy_float_scale` fails loudly if a pre-v3 row meets v3 code (the two scales invert at
1, so silently rounding 0.85 would invert every verdict) · `accept_item`/`None` semantics preserved
and tested · `measure_entailment_ab.py` reads ratings, gains `--template-version` so a staged row
can be measured before activation · 66 judge tests pass.

**Not done (as of 2026-08-17):** the gold-set re-measurement on v3 (harness ready, not run) ·
`cloze_distractor_judge` — deliberately deferred, it has the same two-axis conflation and waits on
TASK-719 · therefore `classify()`/`THRESHOLD_*` survive, documented as legacy with one caller, so
"one verdict mapper, not two" is **not** yet satisfied · post-rollout per-language band-usage
measurement.

**Resolved 2026-08-19** (full results: [[evaluations/entailment-likert-v3-rollout-2026-08-19]]):

1. **Cutover completed.** Deploy ✓ (committed), activate ✓ (10:11:32Z), restart — **moot, not
   skipped**: no app process exists (the only running Python processes are VS Code isort LSP
   servers; nothing listening on 3000/5000/5001/8000/8080/8888). `_cfg_cache` is process-lifetime,
   so the stale-cache failure mode needs a process that judged before 10:11:32Z. There isn't one.
   The next app start loads v3 cleanly.

2. **The "no production telemetry" premise was a query artefact — there is no telemetry gap and no
   task is needed for one.** `test_answer_entailment` is the `prompt_templates` key; the `llm_calls`
   label is **`judge_answer_entailment`** (`judge_` prefix set at `answer_entailment.py:75`). Under
   the correct label: **784 production rows**, `pipeline='test_gen'`, 2026-06-02 → 2026-08-16. The
   narrower true fact: every production row is `template_version = 1` and the newest predates
   activation, so **no v3 traffic has ever run** — which is why band usage had to be measured on the
   harness rather than on live traffic.

3. **The gold set was never a blocker for entailment**, and the harness docstring says so. Entailment
   gold labels are *structural and free* — the correct answer is entailed by construction, its
   distractors are not. No adjudication needed. The gold-set blocker is real only for TASK-719/720,
   which judge *distractor plausibility*, where "is this distractor confusable" has no structural
   label. The two cases had been collapsed into one blocker; they are separable. See **TASK-726**.

4. **zh/ja v3 prompts are genuinely band-anchored, not abbreviated paraphrases.** Worth checking —
   the bodies are 402 (zh) / 1101 (en) / 494 (ja) chars and en is 2.7× zh. The gap is entirely CJK
   character density. All three carry the single-axis restriction, all five anchored bands, the
   tie-break rule and the JSON contract. `audit_prompt_latin.py` returns CLEAN for zh/ja v2 and v3
   (CJK 0.971 / 0.979, zero leaks), and the literal `JSON` token survives in both.

5. **Band usage measured, per language.** All five bands fire in all three languages; 0 unparsed in
   450 calls. First time in this judge family — TASK-717 §2 had zh/ja distractor prompts carrying a
   worked band-3 example while `qwen3.6-flash` emitted zero 3s across 150 distractors. That lesson
   is not contradicted: anchoring bands does not *make* a model use them. What changed is that
   entailment is genuinely **one axis**, so the anchors describe a distinction the model can make.
   The distractor bands still conflate two axes — TASK-719 remains necessary.

   | lang | model | AUC | 1 / 2 / 3 / 4 / 5 |
   |---|---|---|---|
   | zh | `deepseek/deepseek-chat` | 0.990 | 57 / 30 / 10 / 19 / 34 |
   | en | `google/gemini-3.5-flash-lite` | 0.982 | 76 / 23 / 1 / 19 / 31 |
   | ja | `qwen/qwen-2.5-72b-instruct` *(replaced)* | 0.870 | 33 / 17 / 37 / 55 / 8 |

6. **ja was the model, not the language — fixed and applied live.** Holding the v3 prompt fixed and
   varying only the model: qwen-2.5-72b AUC 0.870 / 18% false-accept / 24.7% band-3 load, vs
   `google/gemini-3.5-flash-lite` **0.940 / 2% / 2.7%**, vs deepseek-chat 0.798 / 33%. Since zh and
   en score 0.99/0.98 on the *same* prompt and ja audits CLEAN, the deficit is neither the prompt nor
   ja content — the same conclusion TASK-718 reached about qwen. This was the one active judge row
   `consolidate_gemini_on_3_5_flash_lite.sql` could not reach (it swept gemini rows; this was qwen).
   Applied: `migrations/entailment_ja_v3_onto_gemini_3_5_flash_lite.sql`, model column only, ja v3
   body md5 `df168c48f2b9b92ea53715438788b680` verified unchanged. Trade is 18%→2% false-accept for
   2%→10% false-reject, the correct direction for an answer-hallucination guard.

7. **Live thresholds are correctly placed.** Best swept threshold is **4.0 for every language and
   every model arm** — identical to deployed `LIKERT_ACCEPT`. No retune indicated.

**Still not done** — `cloze_distractor_judge` conversion (waits on TASK-719), and therefore
`classify()`/`THRESHOLD_*` still survive with one caller: **"one verdict mapper, not two" remains
unsatisfied** and cannot be satisfied until cloze converts. This is the only acceptance criterion
still open for this task.

**Original brief below.**
**Feature:** comprehension-tests
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none (but see the warning under Technical Notes)

**Description:**
Two judge scales coexist today and they **invert**: `judge_answer_entailment` and
`cloze_distractor_judge` report a raw 0.0–1.0 confidence classified by
`judges/base.py:111-124` (≥0.8 accept, ≥0.6 flag, else reject), while
`judge_distractor_plausibility` and the `judge_ladder_*` family report a 1–5 Likert mapped by
`schemas.likert_to_verdict` (5/4 accept, 3 flag, 2/1 reject). A stored `1.0` therefore means
"maximum confidence, accept" on one scale and "worst rating, reject" on the other — the exact
collision that forced `migrations/null_legacy_judge_confidence.sql` to erase 888 rows of
`llm_calls.judge_confidence` because nothing in the codebase could tell them apart. Convert the
remaining float judges to Likert so one column means one thing.

**Acceptance Criteria:**
- [~] `judge_answer_entailment` and `cloze_distractor_judge` return a 1–5 integer rating; no
      caller reads a 0.0–1.0 confidence from either.
      — **entailment done and live; cloze deferred to TASK-719.**
- [x] Every band has a definition that is **mutually exclusive** with every other band, on a
      **single axis**. No band may be distinguishable from its neighbour only by degree.
      — verified in all three languages 2026-08-19; 4-vs-3 is uniqueness, 2-vs-1 is absence vs
      contradiction. zh/ja confirmed fully anchored, not abbreviated.
- [ ] `judges/base.py` retires `classify()` and `THRESHOLD_ACCEPT`/`THRESHOLD_REJECT`, or they
      are documented as dead. One verdict mapper survives, not two.
      — **unblocked 2026-08-20, still open.** TASK-719 has settled the axis split and
      `schemas.axes_to_verdict` is the template `cloze_distractor_judge` converts onto (its
      natively-authored zh/ja v2 rows are already staged inactive). Nothing blocks the conversion
      now except that it was out of TASK-719/720's scope. This is the one criterion still open.
- [x] Band usage is **measured after rollout**, per language, per judge — not assumed.
      — [[evaluations/entailment-likert-v3-rollout-2026-08-19]] §3. All five bands fire in all
      three languages, 0 unparsed in 450 calls.
- [x] `judge_confidence` is documented as Likert-only, so it can be aggregated across judges for
      the first time (`null_legacy_judge_confidence.sql` explicitly forbids that today).
- [x] Prompt rows versioned for zh/en/ja on each converted judge; `ON CONFLICT DO UPDATE`.
      — entailment v3 live in all three.

**Technical Notes:**
**Do not clone the distractor judge's existing 5 bands.** They are the worst available template:
[[evaluations/distractor-judge-language-divergence-2026-08-16]] §3 shows they conflate two
orthogonal axes — bands 5/4/2 measure topical distance, bands 3/1 measure confusability with the
answer — so the model must collapse a 2-D judgment into one integer. Bands 3 and 1 also overlap
semantically ("a paraphrase of the answer" vs "also arguably correct"). Fixing that is TASK-719.

**Clear definitions are necessary but demonstrably NOT sufficient.** §2 established that the zh
and ja v4 prompts each contained a worked band-3 example and `qwen3.6-flash` still emitted zero
3s across 150 distractors; §11 showed band 1 fired 3 times in 1,800 ratings across two models.
Anchoring the bands does not make a small model use them. This is why band usage must be
measured per (judge × language × model) rather than assumed from the prompt text.

Entailment is the easy case and should be done first: "does the passage support this answer" is
naturally **one axis**, so it can get clean non-overlapping anchors without the TASK-719 redesign.
Cloze distractor plausibility is the hard case — it has the same two-axis problem as the
comprehension distractor judge and should wait for TASK-719's resolution.

**Files to Create / Modify:**
- `services/exercise_generation/judges/answer_entailment.py` — Likert return, drop `classify()`
- `services/exercise_generation/judges/cloze.py` — same
- `services/exercise_generation/judges/base.py` — retire the float path
- `services/test_generation/schemas.py` — `AnswerEntailmentVerdict` to an integer rating
- `migrations/` — new prompt versions for both judges, zh/en/ja
- `tests/` — the missing-rating (`None`) semantics must be preserved on the new shape

**Verification:**
Re-measure each converted judge with `scripts/measure_judge_flag_rate.py` and report the full
1–5 distribution per language. A judge that emits only {5,4,2} has not gained a review band no
matter how the prompt reads.

---

## TASK-724: De-anglicise the remaining zh/ja prompt rows

**Status:** [x] **Done (2026-08-18) — applied live and verified.** Generalises TASK-722 from one
row to the whole table. 7 rows re-authored natively by `qwen/qwen3.8-max`, 22 more swept of English
format metalanguage, all verified by md5 readback.
**Feature:** comprehension-tests
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-722

**Description:**
TASK-722 fixed one row by reading it. This task asked the same question of all 106 active zh/ja
rows mechanically, then fixed what the evidence justified.

**The audit is the reusable result, not the rewrites.** `scripts/audit_prompt_latin.py` separates
Latin that is *machine contract* from Latin that is leaked English, because a raw token count
cannot tell them apart and acting on one would break the pipelines. Of 106 rows it found 44 already
clean and most of the rest "dirty" only in tokens that must never be translated.

**What was actually wrong, and fixed:**

| Row(s) | Defect | Outcome |
|---|---|---|
| `translation_uniqueness_judge` zh+ja | wholly English (0.3% / 0.4% CJK) | v2 **active** |
| `question_inference` zh | `Martinez博士` inside the Chinese few-shot passage; whole scenario transplanted | v2 **active** |
| `question_main_idea` ja | English `vs`; translated English-context example | v2 **active** |
| `question_author_purpose` ja | gloss `（Author Purpose/Tone）`, `vs`; 著者 → 筆者 | v2 **active** |
| `cloze_distractor_judge` zh+ja | wholly English, byte-identical across languages | v2 **staged inactive** — see TASK-719 |
| 22 rows | `markdown`, `schema`, `prompt`, `IPA`, `vs` metalanguage | version-bumped, no LLM |

**What was deliberately NOT touched, and why it matters more than what was:**
- `no_relation` / `no_inflection` / `no_collocation` — typed-schema escape tokens
  (`ladder_typed.py:74`); `corpus_validated` / `llm_asserted` — grounding constants
  (`collocation_grounding.py:53-54`); the 27 persona archetypes, matched literally
  (`scenario_generator.py:466`); the `plain/polite/honorific/humble/formal/casual` list, which must
  match the injected `{register}`.
- `{word}`, `{pos}`, `{semantic_class}` — **placeholders**. A token regex matches *inside* the
  braces, which is why the audit appears to report `word` as leaked in a dozen rows. It is not.
- `clean` in `ladder_p1_sentence_judge` [zh] — an emitted output *value*, not prose.
- HSK / JLPT / CEFR / ASCII / LinguaLoop, and the pinyin examples (`qǐ lái` vs `qi3 lai2`) that are
  the entire point of their instruction.
- The six `dual_translation_tier*` rows are not prompts: *"Model-routing row only; no prompt text"*.

**Two silent-failure modes drove the whole design:**
1. `cloze.py:110` is `verdicts[d] = 'reject' if v == 'reject' else 'keep'`. A translated or swapped
   verdict word does not raise — it falls through to `keep`, every distractor survives, and the
   judge becomes an expensive no-op.
2. `translation_uniqueness.py:17-21` runs an **inverted** Likert scale (5 = clearly NOT an
   acceptable translation = ideal distractor). A rewrite that "corrects" it keeps precisely the
   also-correct options the judge exists to delete.

Neither raises, so mechanical verification is not enough. `scripts/rewrite_prompt_native.py` carries
a per-task `required_literals` list and refuses any rewrite that drops one;
`scripts/smoke_judge_prompt.py` pins expected verdicts on fixtures and calls the real model.

**Measured 2026-08-18** (fixtures in `smoke_judge_prompt.py`):

| Judge | Rewrite | Incumbent | Decision |
|---|---|---|---|
| `translation_uniqueness` zh | 1/1 | — | activated |
| `translation_uniqueness` ja | 1/1 | — | activated |
| `cloze_distractor` zh | 0/2 | 1/2 | staged |
| `cloze_distractor` ja | 0/2 | 0/2 | staged |

The cloze numbers need reading, not just comparing. The zh rewrite is **not** inverted — reading its
verdicts as swapped would imply 蓝色 and 喝 are valid completions. It is *more conservative*: it
caught the also-acceptable synonym the incumbent **missed** (a real second-correct-answer shipping
today) and then over-rejected two clearly-wrong distractors. Two fixtures (爬床, 做会) are themselves
marginal, so 0/2 overstates the regression. ja is unchanged either way — both prompts return
all-keep, so the bottleneck is `qwen-2.5-72b-instruct`, not prompt language. Same
model-dominates-prompt finding as TASK-718.

**Acceptance Criteria:**
- [x] Every active zh/ja row classified as clean / metalanguage / content-leak, mechanically.
- [x] No parser-visible token altered anywhere — asserted per row, not assumed.
- [x] Content leaks re-authored natively, briefed **in** the target language.
- [x] Judge orientation proven by live fixtures before activation, not by reading.
- [x] Exactly one active row per (task, language) after the change.
- [ ] Native-speaker review of the seven new prompts — **owed**.

**Files Created / Modified:**
- `scripts/audit_prompt_latin.py` — the reusable classifier
- `scripts/rewrite_prompt_native.py` — task-registry rewrite harness with contract enforcement
- `scripts/smoke_judge_prompt.py` — orientation fixtures for both judges
- `scripts/apply_prompt_rewrites.py`, `scripts/sweep_prompt_metalanguage.py`
- `migrations/native_zh_ja_prompt_rewrites.sql`, `migrations/zh_ja_prompt_metalanguage_sweep.sql`
- `data/eval/*.txt` — the seven authored templates (md5s recorded in the migration header)

**Verification:**
```
python scripts/audit_prompt_latin.py            # residual is contract + proper nouns only
python scripts/apply_prompt_rewrites.py --verify
python scripts/smoke_judge_prompt.py --task translation_uniqueness_judge --lang zh --live
```

**Incidentally checked, both benign:** `vocab_validation` [zh] has 0 active rows (deliberately
retired, `rewrite_sense_prompts_two_level.sql:105-109`); `scenario_batch_generation` has 2 active
rows (harmless — `prompt_service.py:32-33` orders by version desc and takes 1).

---

## Sequencing

```
TASK-717 (dead slots) ──┬── TASK-718 (model A/B) ✔ ── [GOLD SET, unfiled] ── TASK-719 ── TASK-720
                        └── TASK-721 (generator spec)

TASK-722 (zh/ja vocab rewrite) ✔ ── TASK-724 (de-anglicise all zh/ja rows) ✔ ──┐
                                                                              │
                                    staged cloze_distractor_judge v2 rows ────┴──> TASK-719
```

Revised 2026-08-16, after TASK-718. The original plan assumed the judge's reject signal was
trustworthy and merely mis-scaled. It is not: two flash-tier judges scoring identical content
produce **disjoint** reject sets, and the language that looked worst under one judge looks best
under the other. Every remaining calibration task tunes that signal, so a gold set — human-labelled
distractors, per language, covering both target failures — is now the gate on TASK-719 and TASK-720.
It has no task ID yet and should get one before either is started.

**TASK-721 and TASK-722 are unaffected** and remain the best next work: neither depends on the judge
being calibrated. TASK-721 attacks reject rate at the generator, and TASK-722 fixes a content defect
established by reading the prompts, not by measuring the judge.

---

## TASK-725: Restore the `JSON` token to four live generator rows

**Status:** [x] **Done (2026-08-19) — applied live and verified.** Found while establishing the
TASK-721 baseline, not by a report. Fixed a live outage.
**Feature:** comprehension-tests
**Type:** bug
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Four active `question_*` rows contained no case-insensitive `json` token:
`question_vocabulary_context` [zh, ja], `question_main_idea` [ja], `question_author_purpose` [ja].
All four are TASK-722 / TASK-724 native rewrites and all four lost the token to
`migrations/zh_ja_prompt_metalanguage_sweep.sql`. All four run on `qwen/qwen3.7-plus`, which
OpenRouter routes to Alibaba, and Alibaba refuses `response_format=json_object` without it:

```
400 invalid_parameter_error: 'messages' must contain the word 'json' in some form,
to use 'response_format' of type 'json_object'
```

`question_generator.generate_question` always passes `response_format='json_object'`, so **every**
generation attempt for those four (question type × language) pairs failed. Measured: **4 of 4 such
cells failed** in an 18-cell pilot; with the token restored, **179 of 180** cells succeeded.

**This corrects a recorded belief.** The 2026-08-17 note has this failure mode as *latent* on
Qwen3.x and confined to `test_answer_entailment`. It was neither: it was live, and it was in the
generators. `JSON` here is machine contract, the same category
`rewrite_prompt_native.allowed_latin` already whitelists — the sweep was right about "markdown"
and "schema" and wrong about this one token.

**Acceptance Criteria:**
- [x] All four rows carry the token again, as new **active** versions (all v2 → v3).
- [x] The incumbent is deactivated; exactly one active row per (task_name, language_id).
- [x] Body is the incumbent verbatim plus one word — no other change.
- [x] All 18 live `question_*` rows verified to contain a `json` token.
- [x] The zh/ja Latin audit still reports CLEAN for all 12 rows (it already whitelists `JSON`).

**Files Created / Modified:**
- `migrations/question_prompt_json_token_repair.sql` — derived by `replace()` from the
  deactivated v2 bodies, so it is re-derivable byte-for-byte
- `scripts/apply_json_token_repair.py` — idempotent apply + md5 / active-count / token readback

**Verification:**
```sql
SELECT task_name, language_id, version, template_text ILIKE '%json%' AS has_json_token
  FROM public.prompt_templates WHERE task_name LIKE 'question\_%' AND is_active;
```
Expect `has_json_token = true` for all 18. Confirmed 2026-08-19.

**Follow-up worth doing:** `sweep_prompt_metalanguage.py` has no guard against removing a token a
provider requires. A pre-flight assertion that every touched body still contains `json` would have
caught this at authoring time.

---

## TASK-726: Build the distractor-plausibility gold set

**Status:** [~] In Progress — **machine half done 2026-08-19; blocked on human adjudication**
**Feature:** comprehension-tests
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none — **this is the blocker, not the blocked**

> **Progress 2026-08-19.** Steps 1, 2, 5 and 6 of the construction plan are shipped and the frame
> is built: **573 items** (zh 213 / en 180 / ja 180), pre-rated by both TASK-718 models, weighted,
> and split into primary + 60-item overlap labeller sheets. Step 4 — adjudication by native
> speakers — has not started and is the only remaining work. Findings, spend and design decisions:
> [[evaluations/distractor-gold-frame-2026-08-19]].
>
> Two things the build settled on the way:
> * **The disjointness reproduces on fresh live-stack content**, harder than on the frozen 150:
>   qwen rejects 56/573, gemini 3/573, overlapping on 3. En agrees on **zero** rejects across 180
>   items, and of the 55 items qwen bands as "off-topic, reject" gemini rates **35 a 5**.
> * **Uniform-by-type sampling was mis-weighting every rate in this workstream.** Reweighting the
>   live judge to the production question mix moves its reject rate **0.52% → 0.92% (1.77×)**, so
>   TASK-721's §1 "0.6% on fresh output" baseline understates production by ~1.8×.

**Description:**
TASK-719 and TASK-720 have both been gating on "a gold set", which has never had a task ID, an
owner, or a construction plan. This task gives it all three. Filed 2026-08-19 by TASK-723, which
established that the blocker is narrower than it had been recorded as.

**The scope is distractor plausibility only.** TASK-723 found that entailment does **not** need
this: entailment gold labels are *structural and free* — a question's correct answer is entailed by
its passage by construction, its distractors are not — which is why
`scripts/measure_entailment_ab.py` manufactures them and why the v3 gold re-measurement ran on
2026-08-19 without any human labelling. That trick does not transfer. "Is this distractor
plausibly confusable with the correct answer?" has no structural label: it is exactly the judgment
under dispute, so it must be adjudicated by a person.

**Why it is now the critical path.** TASK-718 measured two judge models whose reject sets were
**disjoint**. With no ground truth, neither reject rate can be called correct and no arm can be
promoted on the evidence — so *no reject signal in this workstream is gold-validated*. TASK-721
compounds it: the §1 baseline of 30% / 4% / 12% is superseded by a measured 0.6% on fresh output,
so rate-based acceptance criteria cannot be written against anything trustworthy either.

**Construction plan:**

1. **Sample frame.** Reuse `data/eval/entailment_sample_150.json`'s selection method, but draw
   fresh: 60 questions per language (zh/en/ja), stratified by `type_code` in production
   proportions, from output generated on the *current* live stack. 3 distractors each = **540
   items**. Sized so each language can support a per-band estimate with a usable CI, and so one
   adjudicator can finish a language in a sitting.
2. **Enrich the frame with disagreement.** Pure random sampling wastes adjudication on items every
   model already agrees on. Pre-rate all 540 with two judge models (the TASK-718 pair), then
   **force-include every disagreement** and fill the remainder at random. Record which items were
   disagreement-selected — the set is then stratified, not representative, and every rate computed
   from it must be reweighted back to the frame. Do not skip recording this; an unweighted rate off
   a disagreement-enriched set is biased high and will look like a regression.
3. **Label schema — two axes, deliberately not one.** The whole finding of
   [[evaluations/distractor-judge-language-divergence-2026-08-16]] §3 is that the live bands
   conflate topical distance with confusability. The gold set must therefore label them
   **separately**, or it cannot arbitrate TASK-719's split:
   - `topical_distance`: on-topic / related / unrelated
   - `confusable`: yes / borderline / no
   - `also_correct`: boolean — the band-1/band-3 overlap, adjudicated explicitly
   - `notes`: free text, required whenever `confusable = borderline`
4. **Adjudication.** Native speaker per language; zh and ja **must not** be labelled from
   translation. Two independent labellers on a 60-item overlap slice per language to get a
   **Cohen's κ**; publish it. If κ < 0.6 on `confusable`, the label definition is the defect —
   fix it and relabel before any judge is scored against the set. A gold set nobody agrees with
   cannot arbitrate a judge disagreement.
5. **Storage.** `data/eval/distractor_gold_2026-XX.json`, one row per item, carrying `qid`,
   `type_code`, `lang`, `distractor`, all four label fields, `labeller_id`, and the
   `disagreement_selected` flag and frame weight from step 2. Version it; never edit in place.
6. **Harness.** Extend `scripts/measure_judge_flag_rate.py` to score an arm against the gold file —
   per-band precision/recall and AUC on `confusable`, reweighted to the frame. Mirror
   `measure_entailment_ab.py`'s reporting so the two judges' numbers read the same way.

**Acceptance Criteria:**
- [~] ≥540 adjudicated items, ≥180 per language, stratified by `type_code`. — **573 items drawn,
      pre-rated and weighted (zh 213 / en 180 / ja 180); 0 adjudicated.**
- [ ] Cohen's κ computed and published per language on the overlap slice; ≥0.6 on `confusable`, or
      the label definitions are revised and the slice relabelled. — **computation and the `[BLOCK]`
      gate ship in `merge_distractor_gold.py`; needs labels.**
- [ ] zh and ja labelled by native speakers, not from translation. — **human step, not started.**
- [x] `topical_distance` and `confusable` stored as **separate** fields — a gold set on one
      collapsed axis cannot arbitrate TASK-719. **They combine only in `gold_reject`, at the one
      point a verdict is needed, and `borderline` is excluded rather than coerced.**
- [x] Frame weights and the `disagreement_selected` flag stored per item, and the harness applies
      them — every published rate is reweighted to the frame, never raw. **Weights derive from the
      live production type mix, queried not hardcoded; `selection_prob` is stored alongside so the
      correction is auditable.**
- [x] `measure_judge_flag_rate.py` scores an arm against the file and reports per-band
      precision/recall plus AUC. **`--gold`. Smoked end-to-end on synthetic labels; AUC 0.51 on
      random input confirms it manufactures no signal.**
- [~] TASK-718's two disjoint reject sets are re-scored against it, settling which model was right.
      **Now free rather than cheap: the frame was pre-rated with exactly that model pair, so the
      stored arms score against the labels with no new calls. Needs labels.**

**Technical Notes:**
Budget the adjudication honestly: 540 items plus a 180-item overlap slice is the dominant cost of
this task, and it is human time, not spend. Step 2's pre-rating is cheap (~$0.10 at the rates
measured on 2026-08-19) and worth it — it is what stops the adjudicator spending a whole sitting on
items no model ever disputed.

Do **not** let this task drift into re-running model A/Bs. Its output is a labelled file. The A/Bs
are TASK-719/720 and they are cheap once the file exists.

**Files to Create / Modify:**
- `scripts/distractor_gold.py` — **DONE.** Weighting, κ, AUC, band metrics; no DB, no LLM, so the
  statistics are unit-testable. The failure mode of a weighting bug is not a crash but a
  plausible-looking wrong rate, which is why this is split out and pinned by tests.
- `scripts/build_distractor_gold_frame.py` — **DONE.** Sample → pre-rate → select → weight → emit
  frame JSON + per-language labeller CSVs.
- `scripts/merge_distractor_gold.py` — **DONE (new, not in the original plan).** Labelled sheets →
  versioned gold file. Validates against the label vocabulary, requires a note on every
  `borderline`, refuses duplicate (item, labeller) pairs, and fires the κ < 0.6 `[BLOCK]`.
- `scripts/measure_judge_flag_rate.py` — **DONE.** `--gold` mode, frame reweighting, and `live` as
  a prompt version (zh is on judge v6 while en/ja are on v4, so no integer spans a three-language
  arm).
- `scripts/generate_question_sample.py` — **DONE.** `--exclude-passages`, so a top-up run draws
  passages the first run did not use.
- `data/eval/distractor_gold_frame_2026-08.json` + six labeller CSVs — **DONE, unlabelled.**
- `data/eval/distractor_gold_labelling_guide.md` — **DONE (new).** The label definitions κ tests,
  with worked examples of the two cells that prove the axes are not redundant (`unrelated` +
  confusable, `on-topic` + not confusable).
- `data/eval/distractor_gold_2026-08.json` — the adjudicated file. **Does not exist yet.**
- `wiki/evaluations/distractor-gold-frame-2026-08-19.md` — **DONE**, frame + pre-rating findings.

**Verification:**
```bash
# built and verified 2026-08-19
python scripts/build_distractor_gold_frame.py \
    --sample data/eval/task721_before.json --sample data/eval/task726_zh_topup.json \
    --arms "qwen=live:qwen/qwen3.6-flash,gemini=live:" --tag 2026-08

# after adjudication
python scripts/merge_distractor_gold.py --frame data/eval/distractor_gold_frame_2026-08.json \
    --labels zh:<labeller>:<sheet.csv> ... --out data/eval/distractor_gold_2026-08.json
python scripts/measure_judge_flag_rate.py --gold data/eval/distractor_gold_2026-08.json
```
Expect per-language per-band precision/recall, reweighted to the frame, and a published κ.
The gold-scoring step needs no `--arms`: the frame's stored pre-ratings are scoreable arms, which
is what settles TASK-718 for free. `--gold-live-arms` adds a paid live arm on top.
