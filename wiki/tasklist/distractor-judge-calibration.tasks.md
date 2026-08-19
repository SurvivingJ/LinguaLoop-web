---
title: "Distractor Judge Calibration — Task Breakdown"
feature: comprehension-tests
prose_page: ../features/comprehension-tests.md
tech_page: ../features/comprehension-tests.tech.md
analysis_page: ../evaluations/distractor-judge-language-divergence-2026-08-16.md
total_tasks: 8
done: 4
last_updated: 2026-08-18
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

**Status:** [ ] Not Started — **motivation partly discharged, and the prerequisite has changed
(2026-08-16).** TASK-718 delivered the middle band in all three languages by swapping the model,
which was one of this task's two goals. What it also exposed is that the two judges' reject sets are
**disjoint** — agreement on the class that gates content is ~0. Redesigning the scale before a gold
set exists would tune an unvalidated signal. **Build the gold set first**; only then decide whether
the two-axis split is still needed, since band 1's target failure may simply be rare rather than
undetectable.
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
- [ ] Judge returns two ratings per distractor: topical fit and confusability-with-answer.
- [ ] A successor to `likert_to_verdict` maps the pair to accept/flag/reject, with cut points as
      named constants.
- [ ] Band 1's target failure (a distractor that is also correct) is detectable on the
      confusability axis — this is the case that has fired **zero** times to date.
- [ ] `DistractorPlausibilityVerdict` handles the two-field shape; the missing-rating (`None`)
      semantics from v4 are preserved on both axes.
- [ ] Existing normaliser tests still pass; new tests cover the two-field shape.

**Technical Notes:**
`schemas.py` `_normalize` is already a large defensive coercion layer for off-schema model output.
Extend it rather than replacing it — the hallucinated-extra-rows and bare-list paths are all
load-bearing and were each added in response to a real observed failure.

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
- `services/test_generation/schemas.py`
- `services/exercise_generation/judges/distractor_plausibility.py`
- `migrations/` — v6 prompt rows
- `tests/test_distractor_missing_rating.py` and siblings

**Verification:**
Re-measure; confirm the confusability axis produces non-zero counts in the "also correct" region,
which the single-axis scale never did.

---

## TASK-720: Redefine the review band as explicit uncertainty

**Status:** [ ] Not Started
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
- [ ] The review band is defined as judge uncertainty ("rate this if you are not confident the
      distractor is sound"), not a specific defect type.
- [ ] `generation_review_queue` rows carry which axis triggered the review.
- [ ] Measured queue rate is non-zero in **all three** languages.
      *Already true as of TASK-718 (zh 1, ja 2, en 5 band-3 ratings per 150 distractors) — the model
      swap did this without a prompt change. This criterion is now about making the rate **usable**,
      not non-zero.*
- [ ] Queue volume is sized and recorded before rollout, so review time can be budgeted.

**Files to Create / Modify:**
- `migrations/` — prompt rows
- `services/test_generation/orchestrator.py` — `_write_review_queue_rows` flag reasons

**Verification:**
Confirm zh and ja produce queue entries at all — currently they produce exactly zero.

---

## TASK-721: Give the generator prompts a distractor specification

**Status:** [ ] Not Started
**Feature:** comprehension-tests
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-717

**Description:**
No `question_*` generator prompt in any language contains a single line of distractor guidance —
all 18 describe only how to build the question. The distractor rubric exists solely on the judge
side, so content is filtered against a specification it was never given. Port the rubric into the
generators, inverted from "rate this" into "build distractors like this".

**Acceptance Criteria:**
- [ ] All 18 `question_*` rows carry a distractor-construction block appropriate to their type
      family (sense / intent / fact), mirroring the TASK-717 judge rubric.
- [ ] Each includes at least one worked distractor set showing a good distractor and a rejected
      one with the reason.
- [ ] Explicit prohibition on the two failure modes: a distractor that is also arguably correct,
      and a distractor that is a paraphrase of the answer.
- [ ] Reject rate measured before and after; the comparison is recorded.

**Technical Notes:**
This attacks reject rate at the source rather than filtering after the fact, so it should reduce
regeneration cost as well as reject rate. Keep the judge rubric and the generator instruction
textually aligned — if they drift, the generator is optimising against a stale spec.

**Files to Create / Modify:**
- `migrations/` — new versions of all 18 `question_*` rows

**Verification:**
Generate a fresh sample per language and compare reject rate to the TASK-717 post-fix baseline.

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

**Status:** [~] **Entailment half done (2026-08-17); staged, NOT activated. Cloze half not
started.** Code, tests, migration and harness are landed; the v3 prompt rows exist in the live DB
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

**Not done:** the gold-set re-measurement on v3 (harness ready, not run) · `cloze_distractor_judge`
— deliberately deferred, it has the same two-axis conflation and waits on TASK-719 · therefore
`classify()`/`THRESHOLD_*` survive, documented as legacy with one caller, so "one verdict mapper,
not two" is **not** yet satisfied · post-rollout per-language band-usage measurement.

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
- [ ] `judge_answer_entailment` and `cloze_distractor_judge` return a 1–5 integer rating; no
      caller reads a 0.0–1.0 confidence from either.
- [ ] Every band has a definition that is **mutually exclusive** with every other band, on a
      **single axis**. No band may be distinguishable from its neighbour only by degree.
- [ ] `judges/base.py` retires `classify()` and `THRESHOLD_ACCEPT`/`THRESHOLD_REJECT`, or they
      are documented as dead. One verdict mapper survives, not two.
- [ ] Band usage is **measured after rollout**, per language, per judge — not assumed.
- [ ] `judge_confidence` is documented as Likert-only, so it can be aggregated across judges for
      the first time (`null_legacy_judge_confidence.sql` explicitly forbids that today).
- [ ] Prompt rows versioned for zh/en/ja on each converted judge; `ON CONFLICT DO UPDATE`.

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
