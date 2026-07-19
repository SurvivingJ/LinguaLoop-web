---
title: "Evidence-First Grading (DT v2) — Task Breakdown"
feature: evidence-first-grading
prose_page: ../algorithms/evidence-first-grading.md
tech_page: ../algorithms/evidence-first-grading.tech.md
total_tasks: 29
done: 19
---

# Evidence-First Grading (DT v2) — Task Breakdown

Implements [[algorithms/evidence-first-grading.tech]] per [[decisions/ADR-019-evidence-first-scoring]]
(accepted 2026-07-04; all five open decisions approved by user — severity triad, ADR-019,
provisional grades, provisional thresholds, ZH/JA native review deferred as authoring flags).
Phases: 0 measure → 1 prompts → 2 structural → 3 UX. **Rule: Phases 1–3 tasks that change
grader behaviour must re-run the TASK-622 harness and must not regress the baseline.**

---

## TASK-621: Gold calibration sets (EN/ZH/JA)

**Status:** [x] Done (2026-07-05)
**Feature:** evidence-first-grading
**Type:** test
**Complexity:** L
**Depends On:** none

**Description:**
Build the per-L2 gold sets the eval harness scores against: for each of EN/ZH/JA, 10 clean
passages (false-positive measurement), 15 single-seeded-error passages (one per high-frequency
taxonomy subtype, seeded by perturbing real `dt_passage` golds), 5 natural multi-error
passages. Each item carries the adjudicated expected error list (spans, subtype, severity)
and expected dimension bands.

**Acceptance Criteria:**
- [ ] `tests/fixtures/dt_gold/{en,zh,ja}.json` exist, 30 items each, schema: `{passage_id|text, reproduction, expected_errors[{span_repro,span_ref,subtype,severity}], expected_bands{dim:band}}`
- [ ] Seeded errors cover ≥ 10 distinct subtypes per L2 (current taxonomy v4 names; re-tag to v5 in TASK-626)
- [ ] Every item human-reviewed (present batches to the user for adjudication before freezing)
- [ ] A README in the fixture dir documents the seeding method per item (scripted vs LLM-assisted vs hand-written)

**Technical Notes:**
Use live `dt_passage.l2_text` rows as source golds (28 passages exist). LLM-assisted
perturbation is fine for drafting but every label is human-adjudicated — the gold set is the
measuring stick, it cannot itself be model-graded. Store expected severity in BOTH vocabularies
(`global/local` for baseline runs, `minor/major/critical` for post-TASK-625 runs).

**Files to Create / Modify:**
- `tests/fixtures/dt_gold/en.json`, `zh.json`, `ja.json` — the gold sets
- `tests/fixtures/dt_gold/README.md` — provenance + adjudication record
- `scripts/dt_gold_seed_helper.py` — optional perturbation helper (not part of the app)

**Verification:**
JSON loads, counts = 30/30/30, spot-check 5 items per L2 against their source passages.

---

## TASK-622: Eval harness + v1 baseline report

**Status:** [x] Done (2026-07-05)
**Feature:** evidence-first-grading
**Type:** infra
**Complexity:** L
**Depends On:** TASK-621

**Description:**
A runnable harness that grades every gold item through the real cascade (configurable slugs,
real OpenRouter calls) and computes: span detection F1 (relaxed ≥50% overlap), subtype
accuracy, severity agreement (within-one), clean-passage false-positive rate, per-dimension
band QWK + exact/adjacent agreement, overall-band QWK. Then run it against the SHIPPED v1
grader and file the baseline.

**Acceptance Criteria:**
- [x] `python scripts/run_dt_grading_eval.py --l2 ja --out report.md` produces the full metric set
- [x] Metrics implemented as pure functions with unit tests (synthetic mini-fixtures — 23 cases green)
- [x] Baseline report filed as `wiki/evaluations/dt-grading-baseline-2026-07-05.md` with per-L2 tables
- [x] Harness records grader_trace tokens/cost per run (reuses model-arena pricing)

**Outcome (2026-07-05):** Live baseline run, $0.030 total. Dominant finding: Tier-0 near-exact gate
(`NEAR_EXACT_MISMATCH_RATIO ≤ 0.05`) resolved 83/90 items — incl. all 45 single-error seeds — to full
marks before detection (ZH 30/30 at Tier 0). Recall is the floor (EN .222 / JA .111 / ZH .000);
clean-FP rate 0.000 across all L2s (the predicted high FP rate did not appear — Tier-0 short-circuits
clean items). Overall-band QWK EN .516 / JA .186 / ZH .000. Regression floor for TASK-623+. Grading
code untouched. See [[evaluations/dt-grading-baseline-2026-07-05]].

**Technical Notes:**
Score matching: greedy align predicted↔expected errors by span overlap, then judge
subtype/severity on matched pairs only. QWK over the 1–4 bands. Paid run — keep to one pass
per L2 per invocation; cache tier-0-resolved items. This harness is the regression gate every
later task cites.

**Files to Create / Modify:**
- `services/dual_translation/eval_metrics.py` — pure metric functions
- `scripts/run_dt_grading_eval.py` — runner (loads fixtures, calls grade_submission, reports)
- `tests/test_dt_eval_metrics.py` — metric unit tests
- `wiki/evaluations/dt-grading-baseline-<date>.md` — baseline results

**Verification:**
Unit tests green; baseline report exists with non-degenerate numbers (FP rate measured on all
30 clean items; QWK computed for all 5 dimensions).

---

## TASK-623: Tier-0 precision fixes

**Status:** [x] Done (2026-07-05)
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** S
**Depends On:** TASK-622

**Description:**
Close the two silent-leniency holes in the deterministic pre-pass: (1) near-exact full marks
only when EVERY non-equal diff opcode is normalization-class (punctuation/width/kana); retire
`NEAR_EXACT_MISMATCH_RATIO`; (2) missing/invalid tier confidence defaults to 0.0 (escalate),
not 1.0.

**Acceptance Criteria:**
- [x] A 1-char は→が swap in a 50-char passage no longer resolves at Tier 0 (regression test)
- [x] Punctuation-only and width-only diffs still resolve at Tier 0 with 0 tokens (regression test)
- [x] `_safe_float(raw.get("confidence"), default=0.0)` in grader_cascade; missing confidence triggers the tier-2 re-check path (test)
- [~] TASK-622 harness re-run: **single-error detection improved (0/45→45/45 reach grader; span recall EN .222→.704 / JA .111→.852 / ZH 0→.885)**; clean-passage FP rate **rose 0.000→.30/.70/.40** — the Tier-0 mask lifting, not a new regression (baseline 0.000 was a short-circuit artifact). FP reduction is TASK-624's remit.

**Outcome (2026-07-05):** Both leniency holes closed. `NEAR_EXACT_MISMATCH_RATIO` retired for an
op-class **normalization-class gate** (keys on `op != "equal"`, not accuracy — a strict,
non-fuzzy diff so `grade_dictation`'s Levenshtein fuzzy-collapse can't smuggle a real
single-char edit past; see tech spec §9 as-built note + the dakuten residual). Confidence
default 1.0→0.0. 21 unit tests green (`test_dual_translation_tier0.py`,
`test_dual_translation_grader_cascade.py`); full DT suite 252 green. Live harness re-run
($0.659 total, 172 calls): span F1 EN .293→.494 / JA .194→.554 / ZH 0→.597; overall QWK EN
.516→.512 / JA .186→.571 / ZH 0→.216. Comparison table filed in
[[evaluations/dt-grading-baseline-2026-07-05]]. **Headline handoff:** clean-passage
over-flagging (esp. JA 7/10) is now visible and is the top TASK-624 target.

**Technical Notes:**
Implement "normalization-class" by comparing the two span texts after `_normalize_l2` +
`services.dictation.tokenizer.normalize` — if normalized forms are equal, the op is
normalization-class. `tier0.grade_tier0` keeps its signature; only the resolve condition
changes. **As-built:** the gate iterates `grading.diff` opcodes and requires every non-`equal`
op to be normalization-class — deliberately opcode-class-driven, NOT accuracy-driven (fuzzy
tolerance inflates accuracy to 1.0 on real ≥4-char edits).

**Files to Create / Modify:**
- `services/dual_translation/tier0.py` — resolve condition; remove ratio constant
- `services/dual_translation/grader_cascade.py` — confidence default
- `tests/test_dual_translation_tier0.py`, `tests/test_dual_translation_grader_cascade.py` — new cases

**Verification:**
`pytest tests/test_dual_translation_tier0.py tests/test_dual_translation_grader_cascade.py` green;
harness comparison table appended to the baseline eval page.

---

## TASK-624: Phase-1 prompt upgrades + rubric v4 seed

**Status:** [x] Done (2026-07-05)
**Feature:** evidence-first-grading
**Type:** feature
**Complexity:** L
**Depends On:** TASK-623

**Outcome (2026-07-05):** tier1/tier2 prompts upgraded in place (no role swap): new module-dict
blocks (accounted-for [2-way, no highlights this phase], acceptable-variation, reader-impact
severity mapped to global/local, span-discipline, operationalized is_mistake, one worked exemplar
per L2 projected per tier) in `prompts.py`; `build_user_prompt` gained a `regions` param and
`grader_cascade._diff_regions` injects the tier-0 non-equal opcodes (cap 20) into both tier calls;
`_decode_error` now substring-repairs form↔span mismatches (`_reconcile_span_form`) before dropping
— fixes the baseline's dropped empty-`learner_form` omission and off-by-one spans. `migrations/
dt_rubric_v4_seed.sql` applied live as the single active row (v2→v4; band descriptors + weights
inherited byte-identical from v2 via jsonb `||`; adds `acceptable_variation` + `exemplars` only;
verified `descriptors_identical=weights_identical=true`). DT+dictation suite **286 green**
(prompt byte-stability test extended; new decode-repair + regions tests). Live harness re-run
($0.641, 172 calls): **clean FP .30/.70/.40 → .20/.00/.10** (JA's worst-case 7/10 → 0/10) with
span F1 (EN .494→.553 / JA .554→.725 / ZH .597→.658) and recall up on all three — acceptable-
variation did NOT suppress recall. **Tension:** band-agreement QWK gave back on accuracy (all
three) and overall_band on EN (−.05) / JA (−.14) from variance compression (fewer spurious errors
push the clean-heavy gold toward band 4); ZH overall QWK rose (+.04), JA fidelity rose (+.17). Not
a clean pass on the "no QWK regression" clause — documented as the tradeoff to weigh. See
[[evaluations/dt-grading-baseline-2026-07-05]] (TASK-624 update).

**Description:**
Upgrade the existing tier1/tier2 prompts in place (no schema change, severity still
global/local): candidate-regions block + accounted-for rule; acceptable-variation block;
reader-impact severity wording; span-discipline block + substring-repair in decode;
operationalized `is_mistake`; one worked exemplar per (L2, tier). New prompt content
(acceptable_variation lists, exemplars) lives in rubric config v4 — band descriptors and
weights byte-identical to v2.

**Acceptance Criteria:**
- [x] Detector-side user prompt includes tier-0 non-equal opcodes as candidate regions (cap 20), EN/ZH/JA labels per tech spec §7b
- [x] System prompts carry the §7a blocks (accounted-for, acceptable-variation, severity tests, span discipline, is_mistake, exemplar) in all three L2s
- [x] `_decode_error` repairs `learner_form`/`span_repro` mismatches by string search before dropping (unit test with off-by-one span)
- [x] `migrations/dt_rubric_v4_seed.sql` applied live; single-active-row invariant kept; prefix byte-stability test updated
- [~] Harness re-run vs baseline: **span F1 + FP rate improved on all three L2s** (FP .30/.70/.40→.20/.00/.10); **QWK not fully held — accuracy QWK regressed on all three and overall_band on EN/JA** (variance compression, not recall loss — recall rose). Results appended to eval page. Recovering the QWK give-back is deferred to the TASK-628 verifier pass.

**Technical Notes:**
Keep `prompts.build_system_prompt` block-assembly architecture; add blocks as module dicts
exactly like `_INSTRUCTION_HEADER`. ZH/JA strings are authored in the tech spec §7 — copy
verbatim (they carry the native-review flag). Exemplars: EN one from tech spec §7a; author ZH/JA
equivalents with a seeded error from TASK-621 fixtures. Severity stays 2-level in the JSON
contract this phase — present the reader-impact tests mapped to global(=reader stumbles or
worse)/local(=reads on).

**Files to Create / Modify:**
- `services/dual_translation/prompts.py` — new blocks EN/ZH/JA; user-prompt regions param
- `services/dual_translation/grader_cascade.py` — pass diff regions; substring repair
- `migrations/dt_rubric_v4_seed.sql` — acceptable_variation + exemplars keys
- `tests/test_dual_translation_rubric_v2.py` → extend; `tests/test_dual_translation_grader_cascade.py`

**Verification:**
Tests green; live one-passage smoke per L2; harness delta table filed.

---

## TASK-625: Severity triad migration (minor/major/critical)

**Status:** [x] Done (2026-07-06)
**Feature:** evidence-first-grading
**Type:** infra
**Complexity:** M
**Depends On:** TASK-624

**Outcome (2026-07-07):** `dt_error_instance.severity` moved from global/local to the MQM triad
(`minor` w1 / `major` w5 / `critical` w25) across DB, code, prompts, fixtures and UI — vocabulary
only; the Detector/Verifier split and derived severity-weighted scoring stay TASK-627/628.
`migrations/dt_severity_triad.sql` applied live as the two-step CHECK change (extend
`dt_error_instance_severity_check` to the 5-value union → backfill `local→minor`/`global→major` →
`DO`-block verify zero old rows → tighten to the triad); 16 rows migrated (14 minor / 2 major, 0
critical), `SELECT DISTINCT severity` = {minor, major}. `prompts.SEVERITY_ENUM` = the triad;
`_SEVERITY_TESTS` restored to the full 3-level §7a reader-impact wording (EN/ZH/JA, ZH/JA pending
native review); dead 2-level `_SEVERITY_GLOSS` + `_ENUM_LABELS["severity"]` **deleted** (unused since
TASK-624). `_decode_error` range check widens to 3 via `len(SEVERITY_ENUM)`. UI: three chips
(`sev-global` → critical+major, minor unstyled), i18n `dual_translation.severity.{minor,major,critical}`
in all four locales incl. es. Harness `_exp_errors` now reads `severity_v2` + passes
`SEVERITY_TRIAD_ORDER`. **Gotcha fixed:** rubric v4 exemplar `severity` integers encoded the OLD
index meaning; re-tagged in place on the live v4 row (no version bump — avoids colliding with
TASK-627 v5): EN 1→0 (minor), ZH/JA 0→1 (major), guard-tested. DT+dictation suite **313 green**
(added triad decode / critical / out-of-range, exemplar-severity guard, prompts triad-wording tests).
Harness re-run: **EN + ZH hold the 624 floor** (clean FP .200/.100; span F1 .553/.686) with
**severity within-one 1.000 on both** (the new triad signal), sev-exact .62/.71 the new baseline; JA
re-confirmation **deferred** (two runs orphaned by environment interruptions — DNS blip, then session
teardown — 0 items graded, ~$0; identical code path already proven by EN+ZH). See
[[evaluations/dt-grading-baseline-2026-07-05]] (TASK-625 update).

**Description:**
Move `dt_error_instance.severity` from global/local to the MQM triad. Extend the CHECK to
accept all five values, backfill `local→minor` / `global→major`, verify zero rows carry old
values, then tighten the CHECK to the triad. Update code enums (new indices 0=minor 1=major
2=critical), prompt severity block to the triad wording, and UI severity labels/i18n.

**Acceptance Criteria:**
- [x] Migration applied live: CHECK = `('minor','major','critical')`, all rows backfilled, verification query in the migration comment run
- [x] `prompts.SEVERITY_ENUM = ("minor","major","critical")` + triad reader-impact tests EN/ZH/JA; decode range check covers 3 values
- [x] UI renders three severity chips; `sev-global` styling maps to critical+major; i18n keys `dual_translation.severity.{minor,major,critical}` present in ALL FOUR `static/i18n/*.json`
- [x] Harness re-tagged to the triad: gold `severity_v2` verified complete/correct; `_exp_errors` reads `severity_v2`; runner passes `SEVERITY_TRIAD_ORDER`

**Technical Notes:**
Two-step CHECK change (extend → backfill → tighten) so the constraint never blocks the
backfill. Follow migrations/CLAUDE.md: search for other files defining the constraint before
archiving anything. The remediation promotion logic (Feature 2, TASK-609+) reads severity —
it is not yet built, so no consumer migration needed beyond the UI.

**Files to Create / Modify:**
- `migrations/dt_severity_triad.sql` — CHECK extension + backfill + tighten
- `services/dual_translation/prompts.py` — enum + glosses
- `static/js/dual_translation.js` + `static/i18n/{en,es,ja,zh}.json` — labels
- `tests/` — enum decode + UI contract tests

**Verification:**
`SELECT DISTINCT severity FROM dt_error_instance` returns only triad values; pytest green;
one live graded submission shows triad severities end-to-end.

---

## TASK-626: Taxonomy v5 — expanded subtypes + subtype_meta

**Status:** [x] Done
**Feature:** evidence-first-grading
**Type:** feature
**Complexity:** XL
**Depends On:** TASK-625

**Description:**
Seed taxonomy v5 per tech spec §5: shared core (8) + EN (+7) + JA (+9, splitting `particle`
into `particle_wa_ga`/`particle_case`/`particle_other`) + ZH (+9, adding `de_particles`,
`bei_passive`, `directional_complement`, `adverbial_order`), each with `subtype_meta`
(dimension, default_severity, treatable, cloze_suitable), per-L2 `subtype_glosses`, and
per-L1 Rule templates for all six directed pairs.

**Acceptance Criteria:**
- [x] `migrations/dt_taxonomy_v5_seed.sql` applied live as the single active row; subtype lists match §5 exactly (15 EN / 17 JA / 17 ZH)
- [x] Every subtype has a gloss in its L2 and a Rule template in each of the 3 L1s (no fallback-to-slug in a live prompt for the seeded pairs)
- [x] `subtype_meta` complete and total (every subtype maps to exactly one of accuracy/fidelity/naturalness) — enforced by a seed test
- [x] Existing dt_error_instance subtype values remain decodable (`particle` kept as a historical alias in `subtype_meta` → accuracy; all other v4 names survive verbatim)
- [x] Gold fixtures re-tagged to v5 subtype names; ZH/JA strings flagged for native review in the migration header

**Outcome (2026-07-13):** v5 live as the single active row (v4 → deactivated). `subtype_meta`
has 33 entries (32 distinct pair subtypes across 15/17/17 + the `particle` alias, `historical_alias:true`,
NOT in any pairs list). JA `particle` split re-adjudicated per instance across the 8 JA particle gold
items (user-adjudicated); `treatable`/`cloze_suitable` flags user-adjudicated; ZH/JA strings for the 15
new subtypes AI-drafted, flagged for native review in the migration header (ADR-019 pattern); 17
carry-over subtypes reuse v4 strings verbatim. Seed test `tests/test_dual_translation_taxonomy_v5.py`
(28 cases: shape, totality, alias resolution, no-slug-fallback via the real resolver) green; full DT
suite 355 green. Harness hardened first (retry+backoff + `--resume`, `tests/test_dt_eval_harness_retry.py`),
which recovered the JA run from a mid-run `getaddrinfo` DNS failure (the exact TASK-625 orphaning cause).
Paid re-run ($0.624): subtype acc EN .714→**.727** ↑ / JA .760→**.875** ↑ / ZH .833→**.739** (finer
17-way tagset vs the old 9-way — not a detection regression); span F1 + clean FP held on all three;
sev within-one 1.000 all; **JA floor re-confirmed** (span F1 .696 / clean FP .000). See
[[evaluations/dt-grading-baseline-2026-07-05]] (TASK-626 update). Derived severity-weighted scoring
stays TASK-627 (this task only supplies `subtype_meta`).

**Technical Notes:**
Cumulative/self-contained row like v2–v4 (TASK-616 pattern). Old subtype `particle` splits: keep
`particle` in `subtype_meta` as a historical alias mapping to accuracy so v1 rows still resolve.
Authoring volume is the real work: 51 subtype entries × glosses + ~150 templates. Draft with the
tech spec's linguistics, batch-present to user for review before applying (same flow as TASK-616).

**Files to Create / Modify:**
- `migrations/dt_taxonomy_v5_seed.sql`
- `tests/test_dual_translation_taxonomy_v5.py` — shape, totality, alias resolution
- `tests/fixtures/dt_gold/*.json` — subtype re-tag

**Verification:**
Seed test green; live active row = v5; one graded submission per L2 resolves subtypes with no
fallback logs.

---

## Code-Review Hardening Batch (TASK-633 – TASK-649)

Sourced from the 2026-07-13 `/code-review` audit of the uncommitted TASK-624/625/626 work
(rubric v4, severity triad, taxonomy v5). All findings independently reproduced or verified
CONFIRMED unless noted PLAUSIBLE. **Recommended order:** TASK-633–639 (correctness, touch the
live grading path) before the next commit; TASK-640–641 (eval-harness integrity) before the next
paid harness run — they corrupt the TASK-622 regression gate itself; the rest are unordered
hygiene. TASK-634's fix changes what the grader sees, so re-run
`scripts/run_dt_grading_eval.py` after it lands and file the delta next to
[[evaluations/dt-grading-baseline-2026-07-05]] per the phase rule at the top of this file.

---

## TASK-633: Fix non-atomic grade persistence poisoning the submission cache

**Status:** [x] Done — checkbox was stale; `_persist_grade` (routes/dual_translation.py) already writes error rows before the grade row, docstring cites TASK-633. Completion date predates this session, unknown.
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** M
**Depends On:** none

**Description:**
`_persist_grade` in `routes/dual_translation.py` inserts `dt_grade` and `dt_error_instance` as
two separate non-transactional calls. If the error-row insert fails for any reason (an
un-migrated severity CHECK, a transient DB error, a future constraint), the request 500s — and
on retry, `_cached_grade` finds the `dt_grade` row (UNIQUE on `submission_id`, never re-graded)
and permanently serves that grade with `errors: []`. Silent, permanent loss of all error
feedback for that submission.

**Acceptance Criteria:**
- [ ] A simulated failure of the `dt_error_instance` insert does NOT leave a cache-satisfying `dt_grade` row behind
- [ ] A retried submission after such a failure re-grades instead of returning `errors: []`
- [ ] Existing successful-persist tests still pass unchanged

**Technical Notes:**
Prefer making the two inserts atomic from the cache's perspective: either wrap both in a single
Postgres RPC/transaction, or insert `dt_error_instance` rows first and `dt_grade` last (if no FK
requires the reverse order), or add a `persist_complete` flag on `dt_grade` set only after error
rows land, with `_cached_grade` falling through to re-grading when unset. Evidence-first
invariant (ADR-019): a persisted grade must always carry its evidence.

**Files to Create / Modify:**
- `routes/dual_translation.py` — `_persist_grade`, `_cached_grade`
- `tests/test_dual_translation_routes.py` — simulated partial-failure test

**Verification:**
New test simulates the error-row insert raising; asserts a subsequent request re-grades rather
than returning a cached empty-errors grade.

---

## TASK-634: Fix span reconciliation — nearest-occurrence snapping, normalization fallback, raw-text regions

**Status:** [x] Done — checkbox was stale; `_reconcile_span_form`/`_diff_regions` (grader_cascade.py) already implement nearest-occurrence snapping, normalization-aware fallback, and raw-substring diff regions; both cite TASK-634. Completion date predates this session, unknown.
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** L
**Depends On:** none

**Description:**
Three related defects in the TASK-624 substring-repair mechanism (`grader_cascade.py`):
(1) `_reconcile_span_form` snaps a mismatched span to the FIRST occurrence of the form via
`text.find()`, so an off-by-one span on a repeated token relocates the persisted span/UI
highlight to the wrong (correct) occurrence; (2) the exact-substring gate drops any error whose
form isn't a verbatim substring, with no normalization fallback, so a model echoing an
NFKC/half-width/kana/case-folded form gets a real error silently discarded (log warning only) —
breaking the ADR-019 evidence-first invariant; (3) `_diff_regions` feeds the model
doubly-normalized diff tokens (dictation-normalized + tier0 NFKC/kata2hira) as candidate-region
hints, which often don't occur literally in the raw text, actively steering the model into (2).

**Acceptance Criteria:**
- [ ] Repeated-token off-by-one span (EN: "the cat saw the dog", error on 2nd "the") relocates to the occurrence nearest the model's original span, not the first
- [ ] Full-width/half-width katakana form mismatch (JA) is resolved via a normalization-aware fallback search instead of being dropped
- [ ] Capitalized/punctuated EN token mismatch ("The" vs "the") is resolved the same way
- [ ] `_diff_regions` emits raw (non-normalized) substrings from `gold_l2`/`reproduction` as region hints
- [ ] No regression in `tests/test_dual_translation_grader_cascade.py`, `tests/test_dual_translation_tier0.py`

**Technical Notes:**
For (1): scan all occurrences of `form` in `text`, pick the one whose start index is closest to
the model's given span start. For (2): if raw `text.find()` fails, fold both `text` and `form`
through the same normalization tier0 uses (`_normalize_l2`: NFKC + `jaconv.kata2hira`, plus
casefold for EN), locate the match in folded space, and map offsets back to the raw string via a
per-character folded→raw index map (NFKC can change string length). Only drop the error if the
folded search also fails. For (3): map diff-token positions back to the original
`gold_l2`/`reproduction` text before building region hints, rather than passing the normalized
tokens through.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — `_reconcile_span_form`, `_diff_regions`
- `tests/test_dual_translation_grader_cascade.py` — repeated-token, JA width-fold, EN case-fold cases

**Verification:**
`pytest tests/test_dual_translation_grader_cascade.py tests/test_dual_translation_tier0.py`
green; re-run `scripts/run_dt_grading_eval.py` and file the delta vs
[[evaluations/dt-grading-baseline-2026-07-05]] (span F1 and recall should not regress; false
drops on normalized-form echoes should measurably decrease).

---

## TASK-635: Require complete per-dimension scores before skipping Tier-2 recheck

**Status:** [x] Done — checkbox was stale; `validate_raw_response`/`missing_score_dims` (prompts.py) already require a usable band for every asked dimension; docstring cites TASK-635. Completion date predates this session, unknown.
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
`validate_raw_response` (`prompts.py`) only checks that `scores` is a dict — a Tier-1 response
of `{"confidence": 0.9, "scores": {}, "errors": []}` passes validation. High self-reported
confidence then suppresses the Tier-2 recheck, and `grader_cascade.py`'s
`scores.setdefault(dim, MAX_BAND)` fills every missing dimension with a perfect band, producing
an inflated grade with `fell_open=False` and no trace — the same leniency hole TASK-623 closed
for confidence, still open via the scores path.

**Acceptance Criteria:**
- [ ] A Tier-1 response with `scores={}` and `confidence=0.9` fails validation (or otherwise forces the same retry/recheck path as malformed JSON)
- [ ] A response missing exactly one of the required dimensions is also treated as incomplete
- [ ] `fell_open` trace correctly reflects this failure mode when it occurs

**Technical Notes:**
Require `scores` to contain a valid integer band, in range, for every dimension in
`tier0.RUBRIC_DIMENSIONS` the tier was asked to score. Treat a missing/invalid dimension as a
validation failure that triggers the existing retry/fall-open path.

**Files to Create / Modify:**
- `services/dual_translation/prompts.py` — `validate_raw_response`
- `tests/test_dual_translation_prompts.py`, `tests/test_dual_translation_grader_cascade.py`

**Verification:**
New test: `scores={}` + `confidence=0.9` must not produce band-4 dimensions or skip the recheck.

---

## TASK-636: Guard rubric v4 seed against committing zero active rows

**Status:** [x] Done (2026-07-15) — solved at the root, not as specced; see Outcome
**Feature:** evidence-first-grading
**Type:** infra
**Complexity:** XS
**Depends On:** none

**Description:**
`migrations/dt_rubric_v4_seed.sql`'s deactivation `UPDATE` is unconditional, but its
`INSERT..SELECT` is gated on `WHERE src.version = 2`. On an environment with no v2 row, the
transaction commits with zero active `dt_rubric_version` rows, and every subsequent
non-Tier-0 submission raises `RuntimeError` from `get_active_rubric` — grading hard-down.

**Acceptance Criteria:**
- [ ] Running the migration against a DB with no v2 row raises an explicit error instead of silently committing zero active rows
- [ ] A post-insert assertion confirms exactly one active row before commit

**Technical Notes:**
Add a `DO $$ BEGIN IF NOT EXISTS (...) THEN RAISE EXCEPTION ... END IF; END $$;` guard before the
deactivation UPDATE, matching the RAISE-if-invalid pattern already used in
`migrations/dt_severity_triad.sql` step 3.

**Files to Create / Modify:**
- `migrations/dt_rubric_v4_seed.sql`

**Verification:**
Dry-run the guarded migration against a scratch DB with the v2 row deleted; confirm it raises
instead of committing.

**Outcome (2026-07-15):**
The specced fix — a guard that RAISEs when no v2 row exists — was rejected as treating the
symptom. The v2 dependency was the bug: v4 built its config as `src.config || <additions>` via
`INSERT..SELECT ... WHERE src.version = 2`, making a *superseded* row a hard runtime dependency.
A guard would have made the failure loud while keeping the coupling. Instead v4 was regenerated
as a **self-contained** `VALUES (...)` row matching the v1/v2 pattern, which deletes the zero-
active-rows failure mode, the "re-application is a silent no-op" failure mode, and the reason
`dt_rubric_v2_seed.sql` could never be archived per `migrations/CLAUDE.md`.

Both acceptance criteria are still met, by different means:
- Guard 1 refuses to **downgrade** (RAISEs if a newer rubric — e.g. the TASK-627 v5 — is active).
  This covers a case the task didn't anticipate: exactly one row stays active, so no count check
  would ever notice the silent rollback.
- Guard 2 asserts the post-condition (exactly 1 active row, and it is v4) before COMMIT.

`band_descriptors` + `weights` are now equal to v2 **by test**
(`test_v4_band_descriptors_and_weights_match_v2`) rather than by construction — that test is the
only thing preventing drift now that the `jsonb ||` inheritance is gone.

**Verified (2026-07-15):** the seed was applied to live Supabase, which executed the PL/pgSQL for
the first time. Guard 1 passed (live rubric versions are [1,2,4] — no newer row to downgrade);
Guard 2's post-condition held. After: `active_rows=1`, `active_version=4`, and
`band_descriptors`/`weights` still equal v2.

Two caveats on that verification. First, it exercised only the *happy path* — neither guard's
RAISE branch has ever fired, so the error paths remain covered by text assertions
(`test_v4_seed_guards_the_single_active_row_invariant`) rather than execution. Second, the
zero-active-rows scenario this task was written about **cannot occur on live as it stands**: the v2
row exists, so the old gate was satisfied all along. The bug was real but untriggered; the fix is
now structural rather than incidental.

---

## TASK-637: Fix JA exemplar's retired subtype slug + move exemplar severity to slug resolution

**Status:** [x] Done (2026-07-15)
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** S
**Depends On:** none

**Description:**
The JA exemplar in `migrations/dt_rubric_v4_seed.sql` references `subtype_slug: "particle"`,
which taxonomy v5 retired (split into `particle_wa_ga`/`particle_case`/`particle_other`).
`prompts._exemplar_text`'s `except ValueError: error["subtype"] = 0` fallback silently renders
the worked は/が exemplar as subtype 0 (= whatever slug sits at index 0, e.g. omission) in every
JA prompt now that v5 is active — no log, wrong signal. Separately, exemplar `severity` is
encoded as a bare integer that must stay aligned with `SEVERITY_ENUM`'s order by hand; the
migration's own header documents this integer already had to be hand-retagged once.

**Acceptance Criteria:**
- [x] JA exemplar's `subtype_slug` updated to `particle_wa_ga`
- [x] `_exemplar_text`'s except-fallback no longer silently substitutes subtype 0 — a resolution failure logs and skips the exemplar instead
- [x] Exemplar severity moves from a bare integer to a `severity_slug` resolved via `SEVERITY_ENUM.index(slug)` at prompt-build time, mirroring the `subtype_slug` mechanism
- [x] Test asserts every seeded exemplar slug (subtype and severity) resolves against the currently active taxonomy/severity enums

**Technical Notes:**
A missing/wrong worked example is strictly better than a silently wrong one — prefer skipping
the exemplar over guessing an index.

**Files to Create / Modify:**
- `migrations/dt_rubric_v4_seed.sql` — JA exemplar subtype_slug fix; severity_slug field
- `services/dual_translation/prompts.py` — `_exemplar_text` fallback + severity_slug resolution
- `tests/test_dual_translation_rubric_v2.py` or taxonomy tests — exemplar-resolves-cleanly assertion

**Outcome (2026-07-15):**
Resolution now goes through `prompts._slug_index(enum_values, slug) -> int | None`, the inverse
of `grader_cascade._enum_lookup` (index -> slug). It lives in `prompts` rather than beside its
twin because `grader_cascade` imports `prompts`, not the reverse. `_exemplar_text` drops the
worked example and logs when either slug misses; the rest of the prompt still builds, so this is
degradation, not an outage.

The task's "prefer skipping over guessing" note settled an open disagreement: an in-flight
instruction had called for `raise` instead. Raise would have converted a degraded prompt into a
hard grading outage for that L2 — reintroducing the outage class TASK-636's guards exist to
remove. This task's spec won; see [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]],
which generalises the rule.

Severity is now a `severity_slug` string, killing the TASK-625 failure mode at the root: the
integers had to be hand-retagged once already when `SEVERITY_ENUM` flipped from global/local to
the MQM triad, and nothing failed at the time because every index was still *legal*.
`test_v4_exemplar_severities_encode_the_triad_meaning` survives the migration to pin the
editorial judgement (which error deserves which level) — no mechanism can check that, since
swapping two valid slugs still resolves cleanly and is still wrong.

Verified the guard is not vacuous rather than trusting it: reconstructing the old fallback shows
a retired slug resolving to subtype 0 = `article_omission` with no log, while the new path drops
the exemplar and warns. 436 DT tests pass.

**Verification:**
`pytest` green; live JA smoke shows the particle exemplar tagged with the correct subtype and
severity in the rendered prompt.

---

## TASK-638: Fix empty-correction dangling explanation text

**Status:** [ ] Not Started
**Feature:** evidence-first-grading
**Type:** bug
**Complexity:** XS
**Depends On:** none

**Description:**
The drop rule in `grader_cascade.py` was weakened to `not learner_form and not corrected_form`
(AND), so an addition-type error with `learner_form` set but `corrected_form=""` now flows into
`render_explanation`, whose generic template interpolates the empty string, persisting
`"corrected: "` into `dt_error_instance.explanation` and showing it on the learner's error card.

**Acceptance Criteria:**
- [ ] An addition error with `corrected_form=""` renders a template variant that doesn't reference a correction (no dangling "corrected: " text)
- [ ] The drop gate itself stays AND (empty `corrected_form` is legitimate for zero-width-span addition errors per TASK-624 — do not re-tighten to OR)

**Technical Notes:**
Branch in `render_explanation` on empty `corrected_form` to select an omission/addition-appropriate
template, rather than touching the drop gate.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — `render_explanation`
- `tests/test_dual_translation_grader_cascade.py` — addition error with empty corrected_form

**Verification:**
New rendering test for an addition error with `corrected_form=""` shows no dangling correction text.

---

## TASK-639: Centralize severity→style/label mapping; handle legacy severities gracefully in UI

**Status:** [x] Done
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`static/js/dual_translation.js` inlines the severity→CSS-class mapping as string comparisons at
one render call site, with a separate ad-hoc chip-label branch nearby. The old
`dual_translation.severity.global`/`.local` i18n keys were deleted from all four locale files, so
any row still carrying a legacy severity (un-backfilled env, or served verbatim by
`_cached_grade`) renders unstyled with an untranslated English fallback label in zh/ja UIs.
Code-review verdict: PLAUSIBLE — the live backfill (`dt_severity_triad.sql`, applied 2026-07-06)
converts all existing rows, so this only bites fresh/un-migrated environments or a future
severity-vocabulary change, not current production data.

**Acceptance Criteria:**
- [x] One exported `SEVERITY_META` map (`minor`/`major`/`critical` → `{cssClass, i18nKey}`) drives both the CSS class and the chip label
- [x] Legacy `global`→`major` / `local`→`minor` mapped before lookup so old rows still render sensibly
- [x] All referenced i18n keys present in all four `static/i18n/{en,es,ja,zh}.json` files

**Files to Create / Modify:**
- `static/js/dual_translation.js` — severity rendering (~line 401)
- `static/i18n/{en,es,ja,zh}.json` — verify triad keys present

**Verification:**
Manual render check with a synthetic legacy-severity row; confirm styled + localized output in
all four locales.

---

## TASK-640: Fix eval-harness severity/dimension duplication and align_errors score drift risk

**Status:** [x] Done (2026-07-16)
**Feature:** evidence-first-grading
**Type:** test
**Complexity:** S
**Depends On:** none

**Description:**
`services/dual_translation/eval_metrics.py` hand-copies three things that can silently drift
from the production contract they measure: (1) `SEVERITY_TRIAD_ORDER` re-encodes
`prompts.SEVERITY_ENUM` with nothing tying them together, and `aggregate_metrics` still
*defaults* `severity_order` to the retired `SEVERITY_V1_ORDER`; (2) `DIMENSIONS` duplicates
`tier0.RUBRIC_DIMENSIONS` verbatim; (3) `align_errors` re-derives the same span match-score
formula (`overlap / min(span length)`, point-spans = 1.0) that `spans_match` already computes a
few lines up. This is the TASK-622 regression gate itself — drift here corrupts every future
harness comparison silently.

**Acceptance Criteria:**
- [x] `SEVERITY_TRIAD_ORDER` is derived from `prompts.SEVERITY_ENUM` (or a test in `tests/test_dt_eval_metrics.py` asserts they stay equal)
- [x] `aggregate_metrics`'s default `severity_order` is the triad, not the retired V1 order (V1 remains available as an explicit opt-in for baseline re-runs)
- [x] `DIMENSIONS` has a regression test asserting equality with `tier0.RUBRIC_DIMENSIONS`
- [x] `spans_match` and `align_errors` share one `_match_score(a, b)` helper instead of two independent implementations of the same rule

**Files to Create / Modify:**
- `services/dual_translation/eval_metrics.py`
- `tests/test_dt_eval_metrics.py`

**Verification:**
`pytest tests/test_dt_eval_metrics.py` green; behavior identical on the existing synthetic
mini-fixtures.

**Resolution (2026-07-16):**
Both hand-copied constants kept as plain constants and *pinned by test* rather than derived —
the module's stated design is to stay free of service-code imports, and the AC allows the
test-based tie for severity while requiring it for dimensions. New pins:
`test_dimensions_match_tier0_rubric_dimensions` and
`test_severity_triad_order_matches_prompts_severity_enum` (asserts index-equality with
`prompts.SEVERITY_ENUM`, not just membership).

`_match_score(a, b)` is now the sole definition of the match rule (overlap / shorter span;
point-spans scored 1.0 by containment). `spans_match` is `_match_score(a, b) >= threshold`;
`align_errors` ranks candidates by the same call. Pinned by a parametrized
`test_spans_match_agrees_with_match_score_threshold` (overlap/disjoint/point cases) and
`test_align_errors_ranks_by_match_score`.

The V1 default was **latent, not live**: the only production caller
(`scripts/run_dt_grading_eval.py:436`) already passed `SEVERITY_TRIAD_ORDER` explicitly, so
no shipped baseline number was affected. `SEVERITY_V1_ORDER` remains an explicit opt-in;
`test_aggregate_v1_order_remains_available_for_baseline_reruns` also pins that triad-scoring
V1 records reports `n=0` rather than a silently wrong number. The pre-existing
`test_aggregate_metrics_hand_checked` now passes `severity_order=em.SEVERITY_V1_ORDER`
explicitly (its fixtures carry `global`/`local`); its assertions are unchanged, so mini-fixture
behavior is identical as required.

Tests 23 -> 35, green; 450 DT tests green. Frontmatter `done:` counter was stale (5 vs 12
actual `[x]` markers) and was corrected to 13 in the same edit.

---

## TASK-641: Decouple gold-seed band derivation from hardcoded severity weights; drop dead severity_v1 requirement

**Status:** [x] Done (2026-07-16)
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** S
**Depends On:** none

`_SEV_W`/`_UND_W`/`_THRESH` → `OFFLINE_SCORING_CONFIG`, restructured into the exact shape the
rubric config will carry. `derive_bands(errors, *, rubric_cfg=None, offline=False)` now demands an
explicit source via the new `scoring_config()`: a live config, or the pinned fallback. Passing
neither raises — defaulting to the constants is precisely the silent drift this task removes — and
a pre-TASK-627 config raises rather than degrading to constants that may no longer match the
grader. **Key-name correction:** this task (and the v4 seed header) says `severity_weights`/
`thresholds`, but TASK-627's own AC declares `severity_weights` + `understandability_weights` +
`band_thresholds`. Followed TASK-627, since a reader of keys nobody seeds is dead on arrival;
see the hand-off note on TASK-627. `severity_v1` is now omitted-not-nulled when a spec lacks it,
and carried in position when supplied, so the frozen fixtures round-trip byte-identically.

`--offline` landed as an explicit `offline=True` keyword, not a CLI flag: the helper is a library
with no `__main__` (its only callers are the session build drivers), so there is no argv to hang a
flag on. Semantics are as specified — the fallback is opt-in, never implicit.

The AC's "existing gold-seed tests" did not exist — the helper had **zero** test coverage. New
`tests/test_dual_translation_gold_seed_helper.py` (18 tests): the pinning test parses
`migrations/dt_rubric_v*_seed.sql` for seeded scoring keys (skips while TASK-627 is pending), plus
a guard that fails loudly if `dt_rubric_v5_seed.sql` ever lands *without* those keys — otherwise a
TASK-627 rename would leave the pinning test skipping forever, silently. Also pins that the offline
constants still reproduce all three fixtures' derived bands (they do, EN/JA/ZH unchanged). DT suite
**418 green**, fixtures byte-unchanged.

**Description:**
`scripts/dt_gold_seed_helper.py` hardcodes `_SEV_W`/`_THRESH` band-derivation constants that
`migrations/dt_rubric_v4_seed.sql`'s own header comment reserves for TASK-627's
`severity_weights`/`thresholds` keys in `dt_rubric_version.config`. Once TASK-627 seeds those
into the DB, the gold fixtures' `expected_bands` and the live grader's `compute_overall_band` can
silently diverge. Separately, `build_item` hard-requires `severity_v1` (`KeyError` if absent) on
every edit spec, but nothing downstream reads it any more — pure severity-migration residue.

**Acceptance Criteria:**
- [x] `derive_bands` reads the scoring keys from the active rubric config when available, with the current constants as an explicit offline fallback (`offline=True`; keyword, not a CLI flag — no `__main__` exists)
- [x] A pinning test fails if the DB-seeded values (once TASK-627 lands) ever disagree with the fallback constants — plus a companion guard against a v5 seed landing under renamed keys, which would leave the pinning test silently skipped
- [x] `severity_v1` becomes optional in `build_item`; existing frozen fixtures in `tests/fixtures/dt_gold/` are unchanged (omitted-not-nulled when absent; kept in position when supplied)

**Technical Notes:**
This task's DB-config-reading half is only exercisable once TASK-627 seeds `dt_rubric_version.config`
— land the `--offline` fallback + `severity_v1`-optional parts now; wire the DB read when
TASK-627 ships, or track that follow-up explicitly if TASK-627 is still pending.

DONE: `scoring_config(rubric_cfg)` reads + validates the live keys today; what is still owed is a
*caller* that passes one (the build drivers pass `offline=True`). Tracked on TASK-627's hand-off
note, which also pins the key names/values v5 must seed.

**Files to Create / Modify:**
- `scripts/dt_gold_seed_helper.py` — `OFFLINE_SCORING_CONFIG` + `scoring_config()`; `derive_bands` source now explicit; `severity_v1` optional
- `tests/test_dual_translation_gold_seed_helper.py` — NEW; pinning + v5-key guard + fixture-band reproduction + spec shape
- `tests/fixtures/dt_gold/README.md` — derivation source + optional `severity_v1`
- `wiki/tasklist/archive/evidence-first-grading.tasks.md` — TASK-627 hand-off note

**Verification:**
Existing gold-seed tests pass with `severity_v1` omitted from a synthetic edit spec.
(No such tests existed — written as part of this task;
`test_build_item_without_severity_v1` is the named check. `pytest -k dual_translation` → 418 passed.)

---

## TASK-642: Cache active rubric/taxonomy config on the grading hot path

**Status:** [ ] Not Started
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`grade_submission` fetches `get_active_rubric`/`get_active_taxonomy` from Supabase on every
escalated submission with no caching — two extra DB round trips per user-facing grading request
for ~700 lines of JSONB that only changes when an operator activates a new version. The sibling
`router.py` already caches its equivalent config in `_cfg_cache`.

**Acceptance Criteria:**
- [ ] `grade_submission`'s rubric/taxonomy fetch is cached in-process, following `router.py`'s `_cfg_cache` convention
- [ ] A `clear_caches()` hook exists for tests and for operator version-activation flows
- [ ] `scripts/run_dt_grading_eval.py` benefits automatically (no per-item re-fetch)

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — `get_active_rubric`, `get_active_taxonomy`
- Tests relying on per-call fetching updated to call `clear_caches()` in setup

**Verification:**
`pytest` green; a live/staging smoke shows only one rubric+taxonomy fetch per activated version,
not per submission.

---

## TASK-643: Run forced Tier-2 recheck concurrently with Tier-1 when inputs are predetermined

**Status:** [x] Done (2026-07-16)
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** M
**Depends On:** none

**Description:**
When `mismatch_ratio > LARGE_DIFF_RATIO`, the Tier-2 recheck fires unconditionally and all of its
inputs are fixed before Tier-1 returns — yet the calls run sequentially, so the learner waits two
multi-second model calls back-to-back for no reason.

**Acceptance Criteria:**
- [x] In the `mismatch_ratio > LARGE_DIFF_RATIO` branch only, Tier-1 and Tier-2 calls are issued concurrently and merged identically to the sequential path (including usage/cost accounting order)
- [x] The confidence-gated recheck path (where Tier-2 inputs genuinely depend on Tier-1 output) remains sequential
- [x] `scripts/run_dt_grading_eval.py`'s `_CallRecorder` still captures both calls correctly under concurrency (thread-safe append)

**Implementation notes (2026-07-16):**
`grade_submission` computes `forced_recheck = mismatch_ratio > LARGE_DIFF_RATIO` and
`concurrent_recheck` (forced + tier2 budget-allowed + tier1 has a slug). On the concurrent path it
submits the Tier-2 `_call_tier` to a request-scoped `ThreadPoolExecutor(max_workers=1)` and drives
Tier-1 on the main thread, then reads `tier2_future.result()` at the existing Tier-2 merge point —
so trace/token/score/error merge order is byte-identical to the sequential path. `extra_dims` is
provably `tier1_dims` whenever the future is used (forced ⇒ recheck). Confidence-gated re-checks
never enter this branch. `_CallRecorder.append` is now lock-guarded. Tests:
`test_forced_recheck_runs_tier1_and_tier2_concurrently` (2-party barrier proves overlap) and
`test_confidence_gated_recheck_stays_sequential` (max-in-flight tracker proves no overlap).

**Technical Notes:**
Use a request-scoped `concurrent.futures.ThreadPoolExecutor` — don't capture large closures in
long-lived objects. `_CallRecorder` monkeypatches the shared `call_model_with_usage`; guard its
list append with a lock or confirm `list.append` is safe under the executor's threading model.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — forced-recheck branch
- `tests/test_dual_translation_grader_cascade.py` — both calls made + merged identically in the forced-recheck branch

**Verification:**
`pytest` green; measure wall-clock latency improvement on a forced-recheck case in a live smoke.

---

## TASK-644: Replace O(n²) eval-harness checkpoint with append-only JSONL

**Status:** [x] Done (2026-07-16)
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`_save_checkpoint` in `scripts/run_dt_grading_eval.py` rewrites the entire accumulated
records+skipped arrays as indented JSON after every graded item — O(n²) I/O over a run, with the
largest writes landing late in the run between paid model calls.

**Acceptance Criteria:**
- [x] Checkpointing appends one JSONL line per completed item instead of rewriting the full file
- [x] `_load_checkpoint` reconstructs the records/skipped arrays by streaming the JSONL file
- [x] Crash-safe resume semantics preserved (flush/fsync after each append)
- [x] Backward compatible: an existing old-format `.json` checkpoint is loaded once and migrated

**Files to Create / Modify:**
- `scripts/run_dt_grading_eval.py` — `_save_checkpoint`, `_load_checkpoint`
- `tests/test_dt_eval_harness_retry.py`

**Verification:**
`pytest tests/test_dt_eval_harness_retry.py` green; a `--resume` run after a simulated interrupt
recovers the same state as before.

**Outcome (2026-07-16):**
`_save_checkpoint(path, *, record=None, skipped=None)` now appends one `{"type": "record"|"skipped",
"data": {...}}` envelope per completed item (O(1) per item), flush()+fsync() after each write. Both
`main()` callsites pass the single freshly-completed item instead of the full lists. `_load_checkpoint`
streams the JSONL, partitions by envelope `type`, and skips an unparseable trailing line (crash
mid-append) rather than aborting. Legacy pre-644 whole-file sidecars are detected (whole file parses as
one `{records,skipped}` object), loaded once, and rewritten to JSONL in place via new
`_migrate_checkpoint_to_jsonl` (temp+replace). **Beyond spec:** a torn newline-less final line was found
(via the resume simulation) to glue the next append onto it and lose that item; added
`_needs_leading_newline` so an append after a torn tail starts a fresh line — otherwise a re-graded item
would silently drop from the log on a double-crash. Tests: 20 green (was 19; +8 checkpoint cases covering
JSONL append, streaming load, legacy migration + subsequent append, torn-tail read + torn-tail append,
empty file, no-op guards). Verification simulation (`--resume` after a torn interrupt) recovers the same
4 done-ids and drops the torn line as re-gradable.

---

## TASK-645: Remove dead re-normalization in tier-0 full-marks gate

**Status:** [ ] Not Started
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** XS
**Depends On:** none

**Description:**
`_resolves_full_marks` in `tier0.py` re-applies `_normalize_l2` + dictation normalization to diff
span texts that `grade_tier0` and `services/dictation/grader.py` have already fully folded before
tokenizing — `_normalization_class_equal` can never return `True` for a non-equal opcode, making
the per-opcode double-normalization pure wasted work on the request hot path.

**Acceptance Criteria:**
- [ ] `_resolves_full_marks` behavior is unchanged (verified by existing tests) after simplifying to `all(e.op == "equal" for e in grading.diff)`
- [ ] `_normalization_class_equal` removed if it has no other callers

**Files to Create / Modify:**
- `services/dual_translation/tier0.py`

**Verification:**
`pytest tests/test_dual_translation_tier0.py` green with identical pass/fail outcomes on all
existing cases.

---

## TASK-646: Reduce lock hold time in future severity/taxonomy backfill migrations

**Status:** [x] Done
**Feature:** evidence-first-grading
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
`migrations/dt_severity_triad.sql` (already applied live 2026-07-06 — do not touch that history)
holds an `ACCESS EXCLUSIVE` lock across two full-table `UPDATE`s, a `count(*)` verification, and
a validating `ADD CONSTRAINT`, all in one transaction. Fine for the current small table; a future
backfill migration on a larger `dt_error_instance` should not repeat the pattern.

**Acceptance Criteria:**
- [x] A short note is added (migration-authoring guidance, e.g. in `migrations/CLAUDE.md` if one exists, or this task's own Technical Notes) documenting the cheaper pattern for future backfills: collapse multi-value UPDATEs into one `CASE` expression, and add new CHECK constraints as `NOT VALID` + a separate `VALIDATE CONSTRAINT` outside the exclusive-lock window

**Files to Create / Modify:**
- `migrations/CLAUDE.md` — added "Backfill migrations — keep the exclusive-lock window short" section (CASE-collapsed UPDATE, `NOT VALID` + separate `VALIDATE CONSTRAINT`, and avoid in-txn `count(*)` verify)

**Verification:**
N/A — documentation-only; apply the pattern the next time a similar backfill migration is written.

---

## TASK-647: Replace hand-rolled eval-harness retry loop with tenacity

**Status:** [ ] Not Started
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
`scripts/run_dt_grading_eval.py` hand-rolls `_is_transient` (message-substring sniffing) and
`_grade_with_retry` (manual sleep/backoff) instead of using `tenacity`, already a project
dependency and the established pattern for LLM-call retries elsewhere (`services/ai_service.py`,
`services/exercise_generation/base_generator.py`,
`services/conversation_generation/agents/conversation_writer.py`).

**Acceptance Criteria:**
- [ ] The grade call is wrapped with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))` matching the existing project convention, with a custom `retry_if_exception` predicate reusing the current transient-marker check
- [ ] Same attempt count/backoff envelope and skipped-item bookkeeping preserved
- [ ] `tests/test_dt_eval_harness_retry.py` updated to patch tenacity's sleep rather than `time.sleep`

**Files to Create / Modify:**
- `scripts/run_dt_grading_eval.py`
- `tests/test_dt_eval_harness_retry.py`

**Verification:**
`pytest tests/test_dt_eval_harness_retry.py` green.

---

## TASK-648: Delete stale severity comment and dead parameters

**Status:** [ ] Not Started
**Feature:** evidence-first-grading
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
Three mechanical cleanups flagged independently by three review angles as regression bait: (1)
a comment in `prompts.py` still claims severity is "the 2-level global/local enum" though
`SEVERITY_ENUM` has been the minor/major/critical triad since TASK-625; (2) `_decode_error`'s
`reproduction`/`reference` parameters keep `""` defaults plus a test-only `if not text:` legacy
branch in `_reconcile_span_form` that silently bypasses the substring repair if a future caller
omits an argument (production always passes both); (3) `_diff_regions`' `cap` parameter is never
passed by any caller.

**Acceptance Criteria:**
- [ ] Stale global/local parenthetical comment deleted
- [ ] `_decode_error`'s `reproduction`/`reference` parameters made required; `if not text:` legacy branch removed; test callsites updated to pass both texts
- [ ] `_diff_regions`' unused `cap` parameter removed; `DIFF_REGION_CAP` referenced directly

**Files to Create / Modify:**
- `services/dual_translation/prompts.py`
- `services/dual_translation/grader_cascade.py`
- `tests/test_dual_translation_grader_cascade.py`, taxonomy tests

**Verification:**
`pytest` on the dual_translation test files green, no behavior change.

---

## TASK-649: Wiki hygiene — status frontmatter, date reconciliation, evaluations category

**Status:** [x] Done (2026-07-16)
**Feature:** evidence-first-grading
**Type:** docs
**Complexity:** XS
**Depends On:** none

**Description:**
Five CLAUDE.md-schema hygiene defects found during the code review: (1)
`wiki/algorithms/evidence-first-grading.md`/`.tech.md` still say `status: planned` despite 5/12
tasks done including a live production migration; (2)
`wiki/algorithms/translation-grading-cascade.tech.md` says `status: planned` while other pages
call it "v1, shipped"; (3) TASK-625's completion date disagrees between the tasklist (2026-07-07)
and `wiki/log.md` (2026-07-06); (4) `wiki/tasklist/master.md`'s `last_updated` predates the
TASK-625-done row it contains; (5) `wiki/evaluations/dt-grading-baseline-2026-07-05.md` uses
`type: evaluation` and lives in a directory absent from CLAUDE.md §2/§8's schema.

**Acceptance Criteria:**
- [x] `evidence-first-grading.md`/`.tech.md` status → `in-progress`
- [x] `translation-grading-cascade.tech.md` status → `complete` (v1 is shipped) — prose counterpart `.md` also flipped to keep them consistent
- [x] TASK-625 completion date reconciled to 2026-07-06 (log.md header + tech-spec §11 as-built both say 07-06; the tasklist's 07-07 was the lone outlier; git history inconclusive — work is uncommitted)
- [x] `master.md` `last_updated` already current (2026-07-16); TASK-649 row flipped to Done + summary counts adjusted
- [x] `wiki/evaluations/` added to CLAUDE.md §2's directory tree and `evaluation` added to §8's type enum; `dt-grading-baseline-2026-07-05.md` was already linked from `wiki/index.md` (line 128)
- [x] `wiki/log.md` entry appended for this lint pass per §6

**Files to Create / Modify:**
- `wiki/algorithms/evidence-first-grading.md`, `.tech.md`
- `wiki/algorithms/translation-grading-cascade.tech.md`
- `wiki/tasklist/evidence-first-grading.tasks.md`, `wiki/log.md`, `wiki/tasklist/master.md`
- `CLAUDE.md` (root) — §2 directory tree, §8 type enum
- `wiki/index.md`

**Verification:**
Lint pass over the DT wiki cluster shows no remaining status/date contradictions.

---

## TASK-627: Derived scoring module + rubric v5 config

**Status:** [x] Done (2026-07-18)
**Feature:** evidence-first-grading
**Type:** feature
**Complexity:** L
**Depends On:** TASK-626

**Description:**
Implement §4: pure functions computing accuracy/fidelity bands from severity-weighted
per-dimension penalties, understandability from the severity axis, threshold banding, and
weighted-mean renormalization when judged dimensions are missing. Rubric config v5 adds
`severity_weights`, `understandability_weights`, `band_thresholds` (approved provisional
defaults). Includes a re-score utility over stored `dt_error_instance` rows.

**Acceptance Criteria:**
- [ ] `services/dual_translation/scoring.py`: `compute_dimension_bands(final_errors, subtype_meta, rubric_cfg) -> dict`, `compute_overall(bands, weights, present_dims) -> int` — pure, no I/O
- [ ] Worked example from tech spec §4 reproduced exactly by a unit test (JA: major particle + minor word_choice → acc 3, fid 4, und 4, overall 4)
- [ ] `is_mistake` errors excluded from penalties (test)
- [ ] Renormalization: overall computed correctly with naturalness/range absent (test)
- [ ] `scripts/rescore_dt_grades.py --rubric-version N --dry-run` recomputes bands for historical grades with zero model calls
- [ ] `migrations/dt_rubric_v5_seed.sql` applied live (thresholds t4/t3/t2 = 1/6/15 default; understandability 2/6/25)

**Technical Notes:**
Do NOT wire into grade_submission yet — TASK-628 swaps the call flow and consumes this module.
Keeping this task pure-function-only makes the worked-example test the contract.

TASK-641 hand-off: `scripts/dt_gold_seed_helper.py` already reads these three keys off the
active rubric config (`SCORING_KEYS` / `OFFLINE_SCORING_CONFIG`), and the gold fixtures'
`expected_bands` are frozen under the provisional defaults. So the v5 seed must (a) use exactly
these key names — `severity_weights`, `understandability_weights`, `band_thresholds` — and (b)
keep the values (1/5/25, 0/2/25, 1/6/15, und 2/6/25) unless the fixtures are re-derived in the
same change. `tests/test_dual_translation_gold_seed_helper.py` enforces both: it fails if a
`dt_rubric_v5_seed.sql` exists without those keys, and if the seeded values disagree with the
pinned fallback. When it fires, re-derive the fixtures — do not edit the constants to match.
Remaining TASK-641 wiring: the gold-set build drivers still pass `offline=True`; point them at
`grader_cascade.get_active_rubric` once v5 is live.

**Files to Create / Modify:**
- `services/dual_translation/scoring.py` + `tests/test_dual_translation_scoring.py`
- `migrations/dt_rubric_v5_seed.sql`
- `scripts/rescore_dt_grades.py`

**Verification:**
pytest green; dry-run rescore over live grades prints before/after band deltas without writes.

**Outcome (2026-07-18):**
`services/dual_translation/scoring.py` implements §4 as pure functions:
`compute_dimension_bands(final_errors, subtype_meta, rubric_cfg)` (accuracy/fidelity from
severity-weighted per-dimension penalties; understandability from the severity axis over ALL
non-`is_mistake` errors), `compute_overall(bands, weights, present_dims)` (weighted mean
**renormalized over present dims** — an absent judged dimension is dropped from BOTH numerator and
denominator, never defaulted to full marks, the leniency `compute_overall_band` had), plus
`resolve_weights` (mirrors `compute_overall_band`'s language-override resolution) and
`scoring_params` (extract+validate the three keys; RAISES on a pre-v5 config rather than silently
full-marking — the same hole TASK-623 closed for confidence). It is the production twin of
`dt_gold_seed_helper.derive_bands`, consuming the grader's decoded error shape
(`severity`/`subtype` slugs, `is_mistake`) + taxonomy `subtype_meta`. NOT wired into
`grade_submission` — TASK-628 owns that.

`tests/test_dual_translation_scoring.py` (25 cases): the §4 worked example reproduced EXACTLY
against the *real seeded* rubric v5 config + taxonomy v5 `subtype_meta` (JA major `particle_wa_ga`
+ minor `word_choice` → acc 3 / fid 4 / und 4; + judged nat 3 / range 3 → overall 4); is_mistake
excluded from every penalty (with a scored contrast); renormalization (all-band-1 derived + judged
absent → overall 1, not pulled to 2); unknown-subtype fail-safe (understandability-only, never
crashes); threshold boundaries; pre-v5 + malformed config raise; and the v5-seed shape/guards.
Full DT suite 502 green; the previously-skipped gold-seed-helper pinning + v5-key guards now fire
green.

`migrations/dt_rubric_v5_seed.sql` is SELF-CONTAINED (generated from the v4 config + the three
keys; TASK-636 pattern + single-active-row guards). **`band_thresholds` uses the FLAT
`{dim:[t4,t3,t2]}` shape** that the pinned `OFFLINE_SCORING_CONFIG` / `scoring_config._validated`
require — NOT the tech-spec §4 v3 `{default,by_dimension}` synthetic example; the TASK-641 pinned
contract is the binding one. Values = the approved provisional defaults (sev 1/5/25, und 0/2/25,
thresholds acc/fid 1/6/15, und 2/6/25).

Applied live (project `kpfqrjtfxmujzolwsvdq`) as active v5, superseding v4. To avoid re-emitting
the 38 KB config, the live apply derived it as `v4.config || {3 keys}` inside the file's two guards;
verified byte-identical to the file's intent — `v5.config − {3 keys} = v4.config`,
`band_descriptors = weights = v2`, the three keys carry the pinned values, `active_count = 1,
version = 5`.

`scripts/rescore_dt_grades.py --rubric-version N [--dry-run|--apply]` re-scores stored grades with
ZERO model calls (derived bands from `dt_error_instance` rows; judged nat/range kept; overall
renormalized). Dry-run over the 2 live grades printed before/after deltas and wrote nothing (tier-0
grades are reported but skipped on `--apply` unless `--include-tier0`, since they hold no stored
errors and would derive to full marks). Deltas are real — the derived bands differ from the v4-era
model-emitted per-dimension scores, which is exactly the shift this migration introduces.

Follow-up owed (TASK-641 hand-off): the gold-set build drivers still pass `offline=True`; now that
v5 is live they can point at `grader_cascade.get_active_rubric`. Next: TASK-628.

---

## TASK-628: Detector/Verifier cascade restructure

**Status:** [x] Done (2026-07-19) — TASK-632 harness re-run passed on the v2 stack (EN span F1
.941 / clean FP .000 / QWK .824; JA .880 / .100 / .419; ZH filed in
[[evaluations/dt-grading-v2-2026-07-19]]); `Config.DT_FRAMEWORK_V2` default flipped ON. The
bundled rubric-v6 live apply is still owed (carried on TASK-629 — session permission classifier
blocked all DB-write wires; harness ran v6 as a candidate config via `--rubric-file`).
**Feature:** evidence-first-grading
**Type:** refactor
**Complexity:** XL
**Depends On:** TASK-627

**Description:**
Restructure `grade_submission` to the v2 flow: Detector call (errors + highlights, NO scores)
→ Verifier call (verdicts confirm/reject/adjust + added_errors + naturalness/range judgments
with mandatory evidence spans) → Python merge → derived scoring (TASK-627) → contract.
Implement provisional-grade failure modes (never silent full marks), verdict-merge rules
(default-confirm on missing verdict, drop unknown indices), rejected-error logging, and the
config-gated tier-3 arbiter escalation (default OFF).

**Acceptance Criteria:**
- [x] Detector prompt/JSON per §6a/§7a-b (highlights ≤3 enforced in code); Verifier per §6b/§7c-d, all three L2s
- [x] Judgment without valid evidence_spans discarded → dimension treated as missing → renormalized (test)
- [x] Failure matrix tested: detector-fail→verifier-detects-from-empty; verifier-fail→unverified detector errors + renormalized overall; both-fail→no scores, `provisional=true`, diff-only contract
- [x] `grader_trace` carries `framework_version:2`, `provisional`, `rejected_count`, `prompt_version`
- [x] Route/contract passes `provisional` through; UI shows a "grading incomplete — retry" notice when set
- [x] Harness re-run (2026-07-19): span F1 up on all three (EN .543→.941 / JA .696→.880 / ZH filed); clean FP EN .200→.000, ZH held, JA .000→.100 (one clean item, documented caveat); overall QWK EN .512→.824, JA .429→.419 (flat), ZH filed. Results in [[evaluations/dt-grading-v2-2026-07-19]]; flag flipped ON.

**Technical Notes:**
Keep tier1/tier2 router slugs — only the roles change. Verifier user prompt embeds the compact
numbered proposed-error list (§7d). Escalation constants (`CONFIDENCE_ESCALATION_THRESHOLD`,
`LARGE_DIFF_RATIO`) are replaced by the arbiter rule (reject-rate ≥ 0.5 OR verifier confidence
< 0.5; config-gated, default OFF). This is the highest-risk task — land behind a config flag
(`DT_FRAMEWORK_V2`, default off, flip after harness pass; follow ADR-013 flag pattern).

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — restructure
- `services/dual_translation/prompts.py` — detector/verifier builders
- `routes/dual_translation.py` — provisional passthrough
- `static/js/dual_translation.js` — provisional notice (minimal; full UI = TASK-631)
- `tests/test_dual_translation_grader_cascade.py` — verdict merge + failure matrix

**Verification:**
pytest green; live smoke per L2 with a deliberately bad reproduction (verify verdicts + derived
bands in the response); harness comparison filed; flag flip after user sign-off.

**Outcome (2026-07-18) — implemented behind the flag; harness + flip owed:**
The v2 Detector/Verifier flow is built and unit-tested but NOT yet live — `Config.DT_FRAMEWORK_V2`
defaults OFF (ADR-013 pattern), so `grade_submission` still runs the shipped v1 tier1/tier2 body
until the flag flips post-harness. `grade_submission` gained a `framework_v2` override (None → read
Config) and dispatches to `_grade_v2` after Tier 0 fails to resolve; the Tier-0 short-circuit and the
shared rubric/taxonomy/subtype/region context are identical to v1.

- **prompts.py** — `build_detector_system_prompt` (§7a: 3-way accounted-for with the highlights
  branch, severity tests, enum/subtype lines, span discipline, is_mistake, highlights block, no
  scores, no band descriptors) + `build_verifier_system_prompt` (§7c: verdict/added_errors/judgments
  header with `{dims}`, shared detection blocks, naturalness/range band descriptors — the only
  model-facing descriptors left) + `build_verifier_user_prompt` (§7d numbered proposed list) +
  `validate_detector_response`/`validate_verifier_response`. New enums `HIGHLIGHT_REASON_ENUM`,
  `VERDICT_ENUM`, `JUDGE_DIMENSIONS`. EN/ZH/JA blocks copied verbatim from tech-spec §7 (ZH/JA carry
  the standing native-review flag). Detector exemplar reuses the already-seeded v4-shape
  `exemplars[l2]` reshaped (drop scores, empty highlights); verifier exemplar renders from
  `exemplars.verifier[l2]` if seeded, else omitted (not in v5 yet — authoring follow-up), matching
  every other rubric-config block's graceful degradation.
- **grader_cascade.py** — `_grade_v2`: Detector (tier1 slug) → Verifier (tier2 slug) → `_apply_verdicts`
  merge → `scoring.compute_dimension_bands` + judged naturalness/range → `scoring.compute_overall`.
  Verdict rules per §6b: unknown/out-of-range `error_index` dropped; duplicate index → first wins;
  **no verdict → default confirm**; reject drops + increments `rejected_count` (logged, never
  persisted); adjust patches severity/subtype/spans and re-renders the explanation.
  `_judgment_band` discards a judgment lacking a valid in-bounds evidence span **or** a usable band
  (never `_clip_band`'s silent MAX_BAND) → dimension missing → `compute_overall` renormalizes.
  Highlights validated + capped at 3 (`HIGHLIGHT_CAP`). Failure matrix: detector-fail → verifier
  detects from an empty proposed list; verifier-fail → detector errors unverified + judged dims
  dropped; both-fail → `overall_band=None`, `scores={}`, `errors=[]`, `provisional=True`.
  `grader_trace` carries `framework_version:2`, `provisional`, `rejected_count`,
  `prompt_version:{rubric,taxonomy}` (new `get_active_rubric_version`/`get_active_taxonomy_version`
  boundary getters, cached like the config; the existing config fetch is untouched so the seed tests
  are unaffected). Arbiter (`_maybe_arbitrate`, `DT_TIER3_ARBITER_ENABLED` default OFF): fires when
  reject-rate ≥ 0.5 OR verifier confidence < 0.5, re-runs the Verifier role on the tier3 slug over the
  full proposed list and replaces the tier2 merge; NOT gated on `max_tier` (the budget cap governs the
  normal cascade; the arbiter is fenced by `verifier_ok` + the config flag + the trigger). Replaces the
  v1 `CONFIDENCE_ESCALATION_THRESHOLD`/`LARGE_DIFF_RATIO` (which have no meaning in the two-role flow;
  the v1 constants remain in the still-live v1 body).
- **routes/dual_translation.py** — surfaces `provisional` in the contract; **declines to persist**
  when `overall_band is None` (both-fail) so an evidence-free grade never poisons the idempotency
  cache (TASK-633/ADR-019) and the learner's retry re-grades; `_cached_grade` re-surfaces
  `provisional` from `grader_trace`.
- **UI** — `templates/dual_translation.html` `#dtProvisionalNotice` + `static/js/dual_translation.js`
  toggle in `renderResult`; i18n key `dual_translation.grading_incomplete` in all four locales
  (en/es/ja/zh). Minimal by design — full provisional UX is TASK-631.
- **Tests** — 21 new v2 cases in `tests/test_dual_translation_grader_cascade.py` (happy path + derived
  scoring; reject/adjust/default-confirm/unknown-index verdict merge; evidence-gate renormalization;
  the three-way failure matrix; highlights cap; arbiter off-by-default + fires-when-enabled). Full DT
  + scoring + gold-seed suite **514 green**, no v1 regressions.

**Owed before Done:** live smoke per L2 (paid, v5 active + flag on), the TASK-622 harness re-run vs
the Phase-1 baseline filed next to [[evaluations/dt-grading-baseline-2026-07-05]], then the
`DT_FRAMEWORK_V2` flip after user sign-off.

**Bundled in (TASK-629, 2026-07-18):** the rubric v6 band-descriptor rewrite is built + tested but
**unapplied** by user decision — apply `migrations/dt_rubric_v6_seed.sql` in this same paid run so
one harness pass covers both the v2 flow and the new §8 descriptors (which also feed the live v1
prompt). v6 supersedes v5 as the active rubric; both single-active-row guards target v6.

---

## TASK-629: Band descriptors v3 rewrite (authoring)

**Status:** [~] Authored + built + tested + EVALUATED (2026-07-19) — the TASK-632 harness ran the
full v2 pass WITH the v6 config (pre-seeded as a candidate via the new `--rubric-file`, so the
filed numbers correspond to the v2+v6 stack). **Live apply still owed:** this session's
permission classifier denied every DB-write wire (local script, MCP execute_sql, apply_migration);
apply `migrations/dt_rubric_v6_seed.sql` manually (idempotent, guarded) — until then live grading
uses v5 descriptors (scoring keys identical; only descriptor text differs).
**Feature:** evidence-first-grading
**Type:** docs
**Complexity:** L
**Depends On:** TASK-627

**Description:**
Regenerate all band descriptors (6 tiers × 5 dims × 3 L2s × 4 bands) in the §8 pattern —
observable reader behaviour + typical error profile matching the TASK-627 thresholds; no
frequency adverbs; distinct content per band. Ships inside rubric v5 (or a v6 bump if v5 is
already live).

**Acceptance Criteria:**
- [x] Every descriptor names an observable behaviour and a parenthetical error profile consistent with band_thresholds
- [x] Naturalness/range descriptors read as model-facing calibration text (they enter the Verifier prompt); other dims are learner-facing
- [x] No two adjacent bands differ only by an adverb (lint check over the config JSON)
- [x] User reviewed EN set before ZH/JA authoring; ZH/JA flagged for native review

**Files to Create / Modify:**
- `migrations/dt_rubric_v6_seed.sql` (or fold into v5 if unapplied) — descriptors only

**Verification:**
Seed test green; feed-up panel + verifier prompt render the new text live.

**Outcome (2026-07-18) — authored + built + tested; live apply deferred:**
Band descriptors regenerated to the §8 pattern (observable reader behaviour + a parenthetical
error profile matched to `band_thresholds`), retiring the v1-era `(content level: …)` suffix.
`migrations/dt_rubric_v6_seed.sql` is a **descriptors-only** self-contained bump on v5 (TASK-636
guards; weights / acceptable_variation / exemplars / severity_weights / understandability_weights /
band_thresholds carried from v5, held equal BY TEST). Design per ADR-018 + the §8 voice split:
accuracy/fidelity/understandability **learner-facing + tier-invariant** (Python-derived by
`scoring.py`, never sent to a model); range **model-facing + tier-invariant** (judged vs the
reference); naturalness **model-facing + tier-varying** — the one level-dependent dim — absent at
tiers 1-2. EN user-approved (2026-07-18); ZH + JA AI-drafted and **flagged for native review** in
the migration header (ADR-019). Generated via a checked scratchpad script: 336 real slots (not 360
— naturalness is omitted at tiers 1-2).

New `tests/test_dual_translation_rubric_v6.py` (54 cases): shape + both reader paths
(`routes._rubric_descriptors_for`, `prompts._band_descriptors_text`) KeyError-free; the §8 lint
(every descriptor carries a parenthetical; no EN frequency adverbs; **no two adjacent bands differ
only by an adverb**; distinct per band; no surviving content-level suffix; age-tiers not CEFR);
tier-invariance of the derived dims + range vs tier-variance of naturalness; carry-forward == v5;
version-6 single-active-row guards. Regression: the `dt_rubric_v*` glob pinning test picked up v6
and confirmed its scoring keys still match the frozen gold-fixture fallback; full DT suite **568
green** (was 514).

**NOT applied to live Supabase** (user decision): v6's descriptors also feed the **shipped v1**
grader prompt (`build_system_prompt` → `_band_descriptors_text`), so activating them changes live
grader behaviour and — per the phase rule at the top of this file — wants a TASK-622 harness re-run.
Bundled with TASK-628's already-owed paid harness run + `DT_FRAMEWORK_V2` flip: apply v6, run the
harness once, flip the flag together. Migration + test are committed and green; only the live apply
and the "renders live" half of Verification remain.

---

## TASK-630: Explainer pass — instance-specific Application layer

**Status:** [x] Done (2026-07-19) — the TASK-632 harness exercised the Explainer live on every
error-bearing v2 item (its calls + tokens are in the run's accounting); Application layers
validated in code, Rule-only fallback confirmed on rejects. Flag now ON.
**Feature:** evidence-first-grading
**Type:** feature
**Complexity:** M
**Depends On:** TASK-628

**Description:**
One cheap batched L1 call per error-bearing submission (§6c/§7e): input = reference, learner
text, numbered final errors with Rule templates; output = per-error 1–2 sentence Application
text. Code validation (≤240 chars, single paragraph, mentions learner_form or corrected_form,
no score-like patterns) with silent Rule-only fallback. Persist `explanation = Rule + "\n" +
Application`; contract adds `explanation_parts {rule, application|null}`.

**Acceptance Criteria:**
- [x] Explainer prompts EN/ZH/JA (as L1s) per §7e; router slug = cheap tier (`resolve_tier(db, "tier1", l2_language_id)`)
- [x] Validation unit-tested: overlong / no-mention / score-pattern / missing index → Rule-only (27 cases in `tests/test_dual_translation_explainer.py`)
- [x] Explainer failure never blocks or delays the grade response beyond its own call (fail-silent, logged) — no-slug / call-raises / malformed-JSON / bad-shape all keep Rule-only; never flips `provisional`
- [ ] Live smoke: a particle error's explanation names the actual words, not just the は/が rule — deferred (needs a paid call + `DT_FRAMEWORK_V2` on; runs with the TASK-628 bundle)

**Files to Create / Modify:**
- `services/dual_translation/explainer.py` + prompts additions
- `services/dual_translation/grader_cascade.py` or route — wiring after merge
- `tests/test_dual_translation_explainer.py`

**Verification:**
pytest green; live graded submission shows Rule + Application layers in the response JSON.

**Outcome (2026-07-18):**
New `services/dual_translation/explainer.py`: `attach_explanations(db, *, errors, reference,
reproduction, l1_code, l2_language_id, taxonomy_cfg) -> (errors, tokens_in, tokens_out, reason)`.
It first scaffolds `explanation_parts = {rule: <existing explanation>, application: None}` on
**every** error (the guaranteed floor, so the v2 contract stays uniform even when the model call
never happens), then makes one batched cheap-tier L1 call and overlays a validated Application
per index. On a valid item, `explanation = rule + "\n" + application`; otherwise the error stays
Rule-only. Prompt builders live in `prompts.py` (`build_explainer_system_prompt` /
`build_explainer_user_prompt` / `validate_explainer_response`, §7e EN/ZH/JA — the one L1 prompt in
that otherwise-L2-only module, ZH/JA flagged for native review). `call_model_with_usage` /
`resolve_tier` are imported into the explainer's namespace for test monkeypatching, mirroring
grader_cascade.

Wired in `grader_cascade._grade_v2` after the merge/arbiter block, gated on `if final_errors:`
(error-bearing only — this naturally also skips the both-tiers-failed no-scores case, whose
`final_errors` is empty). Explainer tokens are folded into the grader_trace token totals; its
`reason` is deliberately **not** appended to `fail_reasons` and does **not** set `provisional` —
an Explainer failure must never degrade the grade (AC 3).

`explanation_parts` is a response-only field, **not** a column. `routes/dual_translation.py
_persist_grade` now column-whitelists the `dt_error_instance` insert (`_ERROR_INSERT_COLUMNS`,
mirroring `_cached_grade`'s select list) instead of `{**error}`, so the concatenated
`explanation` string persists (§6c "no schema change") while `explanation_parts` is dropped from
the insert and returned to the client only.

Validation gotcha found + fixed by the no-mention test: the ≥2-char-overlap mention check
originally matched a window straddling a word boundary (`"s "` from `"has lived"` matches almost
any prose like `"This "`), waving through a text that names none of the actual words.
`_mentions_form` now ignores whitespace-bearing windows (falling back to whole-form match for a
1-char/all-boundary form). 27 explainer tests green; DT-related suite **595 green** (was 568).

---

## TASK-631: Result UI v2 — highlights, "because" lines, next focus

**Status:** [x] Done (2026-07-19) — offline DOM-shim verification (24/24 assertions, en+es) stands
as the render check; the v2 contract the renderer consumes (highlights / explanation_parts /
provisional) is now live-proven by the TASK-632 harness run, and `DT_FRAMEWORK_V2` defaults ON, so
the next real submission renders the full v2 result surface. (No separate browser smoke was run
this session.)
**Feature:** evidence-first-grading
**Type:** feature
**Complexity:** L
**Depends On:** TASK-630

**Description:**
Surface the new signal: highlights (positive evidence) rendered on the diff; per-dimension
computed "because" lines ("Accuracy 3 — one major particle error"); three-level severity
chips; provisional-grade banner; "next focus" feed-forward line (top recurring subtype, links
into remediation once Feature 2 lands). Explanation cards show Rule and Application as
distinct visual layers.

**Acceptance Criteria:**
- [x] Highlights render with reason labels; absent gracefully (v2-only `contract.highlights`; strip hidden when empty/absent — v1/cached grades never carry them)
- [x] "Because" lines generated client-side from errors+bands (no new API surface) for all scored dims
- [x] All new strings via data-i18n keys present in ALL FOUR `static/i18n/*.json` (en/es/ja/zh) — no raw-key rendering (72 DT keys, identical set across locales)
- [x] Naturalness visibility gate (age tiers 1–2) unchanged; anti-gamification: error-profile trend stays the headline (renderDims tier gate untouched; because-lines are a quiet sub-line)
- [x] Escaping: all model-derived text (Application, highlights) HTML-escaped

**Files to Create / Modify:**
- `static/js/dual_translation.js`, `templates/dual_translation.html`, `static/css/…`
- `static/i18n/{en,es,ja,zh}.json`

**Verification:**
Live submission with seeded errors renders highlights + because-lines + layered explanations;
i18n spot-check in es locale (UI locale only).

**Outcome (2026-07-18) — implemented + offline-verified; live paid smoke owed:**
Pure front-end change (no backend/contract touch — the AC's "no new API surface" is honoured; the
v2 contract from TASK-628/630 already carries `highlights[]`, `errors[].explanation_parts
{rule,application}`, and `provisional`).
- **highlights:** `renderHighlights()` slices each `span_reproduction:[a,b]` out of the just-
  submitted reproduction (kept in `state.reproduction`), labels it via
  `dual_translation.highlight_reason.*`, and renders a "What worked" strip under the diff; empty/
  absent → strip hidden (v1/cached grades degrade silently).
- **because-lines:** `becauseLineFor(dim, errors)` — judged dims (range/naturalness) get the fixed
  "judged from your whole translation" phrase; accuracy/fidelity/understandability get a terse
  worst-severity tally. Dimension attribution uses a documented client-side `CATEGORY_DIMENSION`
  proxy (grammatical→accuracy, lexical→fidelity; understandability = all errors' severity axis)
  because the authoritative `subtype_meta` dimension map is NOT in the contract and the AC forbids
  adding it. Approximate by design; the error-profile trend stays the headline.
- **three-level severity chips:** `SEVERITY_META` restructured to `{chipClass, cardClass, i18nKey}`
  — minor/major/critical each styled distinctly (minor was previously unstyled); dead `.sev-global`
  CSS removed. Legacy global/local still map through `canonicalSeverity`.
- **layered explanation:** `buildExplanation()` renders Rule (`.dt-expl-rule`) and Application
  (`.dt-expl-application`, accent border) as distinct layers from `explanation_parts`, falling back
  to the flat `explanation` string for v1/cached grades; both escaped.
- **next focus:** `renderNextFocus()` names the top recurring subtype in the submission + a
  "practice coming soon" hint (no remediation link until Feature 2 is user-facing).
- **provisional banner:** the TASK-628 `#dtProvisionalNotice` is retained as the banner.
- **i18n:** 13 new keys × 4 locales (en/es/ja/zh), inserted after `severity.critical`; all four
  parse and share an identical 72-key DT set.

**Verification done:** a jsdom-free DOM-shim harness loaded the REAL `dual_translation.js` and drove
a synthetic v2 `/submit` contract (mixed-severity errors, highlights, an Application containing
`<script>`, a null Application, a repeated subtype) through the actual submit→`renderResult` path —
**24/24 assertions green in BOTH `en` and `es`** (highlight slice+label, all-dim because-lines incl.
judged-dim after the naturalness toggle, three-level chip+card classes, both explanation layers,
`<script>`→`&lt;script&gt;` escaping, single Application layer for the null case, next-focus top
subtype, zero raw `dual_translation.*` keys). **Owed:** the live paid smoke with `DT_FRAMEWORK_V2`
on — folded into TASK-628's already-owed paid run + flag flip, since highlights/explanation_parts
don't exist on the shipped v1 path.

---

## TASK-632: Final eval + wiki reconciliation

**Status:** [x] Done (2026-07-19) — full v2 harness run (EN/JA/ZH, v6 candidate rubric) filed as
[[evaluations/dt-grading-v2-2026-07-19]]; framework pages → complete; v1 cascade pages →
deprecated with a v2-live banner; taxonomy business-rules page updated to v5/triad reality;
`DT_FRAMEWORK_V2` default ON; log/index/master reconciled. Code-review + harness-improvement
report delivered in-session (key items: checkpoint doesn't persist per-item token/cost so resumed
runs under-report spend; `_fetch_active_scalar` caches a None; JA per-item latency ~2-3 min under
v2). Residual: rubric v6 live apply (TASK-629 carry).
**Feature:** evidence-first-grading
**Type:** docs
**Complexity:** S
**Depends On:** TASK-631

**Description:**
Full harness run on the completed v2 stack; file the evaluation page with baseline→v2 deltas;
flip framework page statuses planned→complete; reconcile [[algorithms/translation-grading-cascade.tech]]
(mark superseded sections) and [[business-rules/translation-error-taxonomy]] (v5 reality).

**Acceptance Criteria:**
- [ ] `wiki/evaluations/dt-grading-v2-<date>.md` with per-phase metric progression
- [ ] Framework prose/tech pages status=complete; remaining open questions pruned or carried
- [ ] v1 cascade page banner points to v2 as live; taxonomy business-rules page updated
- [ ] log.md + index.md + master.md reconciled

**Verification:**
Lint pass over the DT wiki cluster (no contradictions v1↔v2 pages).
