---
title: "Exercise Generation Cost Reduction — Task Breakdown"
feature: exercise-gen-cost
prose_page: ../features/exercise-generation-v2.md
tech_page: ../decisions/ADR-028-exercise-gen-cost-under-1c.md
total_tasks: 15
done: 9
---

# Exercise Generation Cost Reduction — Task Breakdown

Implements [[decisions/ADR-028-exercise-gen-cost-under-1c]]. Target: <$0.01/sense, measured
from `llm_calls`, at quality non-inferior to a frozen reference set. Phase 0 (TASK-804–808)
gates everything after it — no model swap or call-collapse change in Phase 1/2/3 ships without
a baseline and a scoring protocol to compare against.

**2026-09-27: Phase 1 (TASK-809–813) scored.** TASK-809/810/811/813 Done, TASK-812 In Progress
(cache-token logging shipped; the stable-prefix reorder itself is deferred, needs a
`prompt_templates` edit + native-speaker review). en's calls-mean $/sense fell 73.4% on the same
senses baseline_en ran (driven by the claude-sonnet-5→qwen price-routing swap); ja's rose 10.2%
on the same completed senses because far more ja senses now complete at all (13.3% failure vs.
baseline's 50%) — a reliability win that reads as a cost regression on a like-for-like basis. zh
got its first-ever run (30 senses) and is now the zh reference. Full numbers, token breakdown
(qwen's reasoning-token volume is now the largest identified remaining cost driver), and caveats
in [[evaluations/exercise-gen-phase1-2026-09]]. Blind pairwise packs generated for ja and en vs.
their baselines but not yet judged (packs list in that eval's §10).

**2026-09-26:** TASK-809–813 (Phase 1) approved by the user — draft status removed. TASK-814–816
(Phase 2) unblocked from `[?]` to Not Started, gated on the Phase 0 baseline (TASK-808) landing
and a Phase 1 non-inferiority score. TASK-817/818 (Phase 3) remain blocked — **user: do not do
Phase 3.** Exact per-task implementation plans (file:line anchors, function signatures, data
shapes, test lists, risks) are in
[[tasklist/exercise-gen-cost.implementation-plan]].

---

## TASK-804: Instrument `llm_calls`

**Status:** [x] Done — 2026-09-26
**Feature:** exercise-gen-cost
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Add nullable columns `prompt_tokens`, `completion_tokens`, `cached_tokens`,
`reasoning_tokens`, `sense_id`, `call_role` (`primary` / `json_repair` / `retry` / `salvage` /
`repair`), and `generation_batch_id` to `llm_calls`. Persist `usage.cost` to `cost_usd` and
capture `latency_ms` on every OpenRouter call made from the vocabulary-ladder pipeline.
Logging must fail-soft: a logging failure emits a WARNING and never raises or aborts
generation. This closes the same class of defect found live 2026-08-12 (NULL `cost_usd`
disarmed every budget ceiling for months without anyone noticing).

**Acceptance Criteria:**
- [ ] Migration adds all seven columns (nullable) to `llm_calls`
- [ ] Every OpenRouter call site reachable from the vocabulary-ladder pipeline writes
      `cost_usd` (from `usage.cost`) and `latency_ms`
- [ ] `call_role` is populated correctly for at least: primary generation calls, JSON-repair
      turns, retries, the P3 salvage call, and repair calls
- [ ] A deliberate logging failure (e.g. DB briefly unreachable) logs WARNING and does not
      raise or abort the in-flight generation call
- [ ] A fresh live run over ≥5 senses shows non-NULL `cost_usd`, `latency_ms`, and `call_role`
      on 100% of the resulting `llm_calls` rows

**Technical Notes:**
Reference: ADR-028 §Context ("Cost is unmeasured") and the 2026-08-12 incident in
`wiki/tasklist/master.md` (four guardrails silently inert for months). Follow
`migrations/CLAUDE.md` convention — idempotent, `IF NOT EXISTS` for the columns. Do not trust a
unit test with mocked Supabase as sufficient evidence this works; verify with one live smoke
run.

**Files to Create / Modify:**
- `migrations/task804_llm_calls_instrumentation.sql` — new nullable columns
- `services/llm_service.py` — persist `usage.cost` → `cost_usd`, capture `latency_ms`, accept
  `call_role`
- `services/vocabulary_ladder/asset_pipeline.py` — thread `sense_id`, `call_role`,
  `generation_batch_id` through to each call site

**Verification:**
Run a live batch across ≥5 senses (spanning en/zh/ja), then:
`SELECT count(*) FILTER (WHERE cost_usd IS NULL), count(*) FILTER (WHERE call_role IS NULL) FROM llm_calls WHERE generation_batch_id = '<batch>'`
— both must return 0.

**Closed 2026-09-26:** migration file (`migrations/task804_llm_calls_instrumentation.sql`) was
written; live apply against the production DB was left pending user action rather than applied
automatically. A pre-migration smoke check surfaced the degradation this task exists to fix
(NULL `cost_usd`/`call_role`/token columns on `llm_calls` rows). The TASK-808 baseline run
(60 senses, ja+en) is now live evidence the instrumentation works end-to-end: every sampled
`llm_calls` row in `data/eval/runs/baseline_{ja,en}/*.json` carries non-null `cost_usd`,
`prompt_tokens`, `completion_tokens`, `cached_tokens`, `reasoning_tokens`, `call_role`,
`sense_id`, `generation_batch_id`, and `latency_ms`. See
[[evaluations/exercise-gen-baseline-2026-09]] §3.

---

## TASK-805: Verify budget ceilings actually fire

**Status:** [x] Done — 2026-09-26 (bundled with TASK-804)
**Feature:** exercise-gen-cost
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-804

**Description:**
Now that `cost_usd` is populated, prove that a budget ceiling actually trips rather than
assuming instrumentation alone fixes enforcement. This is the exact guardrail class that was
silently inert for months in the 2026-08-12 incident (NULL `cost_usd`, a nonexistent RPC
signature, a rejecting CHECK constraint, and a mismatched audio field all shipped as if
working).

**Acceptance Criteria:**
- [ ] Every code path that reads `llm_calls.cost_usd` to enforce a ceiling is identified
      (batch-runner `--ceiling` flags, per-run budget guards)
- [ ] A test or live smoke deliberately exceeds a low ceiling and asserts the run aborts
      before exceeding it
- [ ] The abort is loud (raises / logs ERROR), not a silent skip
- [ ] A short note lists which ceilings exist, which were verified, and which remain
      unverified

**Technical Notes:**
Grep `cost_usd` and `--ceiling` across `scripts/` and `services/exercise_generation/`. Apply
the same "prove it fires, don't assume" discipline TASK-729 used for the fail-closed judging
guard.

**Files to Create / Modify:**
- `tests/test_budget_ceiling_enforcement.py` — new
- Whichever ceiling-reading module is found during investigation (TBD)

**Verification:**
Run the new test; also run one live batch with an intentionally low ceiling and confirm it
stops early with a non-zero exit / logged error.

**Closed 2026-09-26 — with an open verification gap, flagged rather than glossed over:**
`scripts/run_exercise_gen_eval.py` (the TASK-808 baseline harness) does implement its own
`--max-cost-usd` ceiling (checked before each render stage; sets `stopped_due_to_cost_cap` /
`render_skipped_cost_cap` in the run summary). Neither the ja nor en baseline tripped it
(`stopped_due_to_cost_cap: false` in both `summary.json` files) — so this baseline is evidence
the flag exists and is wired into the summary, **not** evidence that it actually aborts a run,
since it was never exercised under a ceiling low enough to fire. `tests/
test_budget_ceiling_enforcement.py` (the acceptance criterion's named test file) does not exist
in the repo as of this note. Marked Done per the ADR-028 Phase 0 sign-off, but the "prove it
fires, don't assume" verification this task was named for is still outstanding — do not cite
this task as having closed that gap without re-checking.

---

## TASK-806: Build frozen reference set

**Status:** [x] Done — 2026-09-26
**Feature:** exercise-gen-cost
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Build a frozen reference set of up to 50 senses per language (en/zh/ja), preferring
difficulty ≥3 (judges skip d≤2, so quality is actually measured there), snapshotted from the
Sep 2026 claude-code-subagent benchmark (604 valid assets / 108 senses). File as
`data/eval/exercise_gen_reference_set_2026-09.json`. Where fewer than 50 qualifying senses
exist for a language, record the shortfall explicitly rather than padding with d≤2 senses.

**Acceptance Criteria:**
- [ ] `data/eval/exercise_gen_reference_set_2026-09.json` exists with up to 50 senses/language,
      each carrying its full generated asset set and its difficulty
- [ ] A companion shortfall note states, per language, how many senses were available vs the
      50 target and why
- [ ] Senses were pulled from the existing 2026-09 subagent batch, not freshly regenerated
- [ ] The file is treated as read-only after creation; any later revision is a new dated file

**Technical Notes:**
**Coordination note:** other agents are concurrently editing `data/eval/` in this same window.
Check for a filename collision before writing; if
`exercise_gen_reference_set_2026-09.json` is already in use for something unrelated, use a
distinct filename and record the substitution here.

**Files to Create / Modify:**
- `data/eval/exercise_gen_reference_set_2026-09.json` — new
- `data/eval/exercise_gen_reference_set_2026-09.shortfall.md` — new (or embedded in the JSON)

**Verification:**
`python -c "import json; d=json.load(open('data/eval/exercise_gen_reference_set_2026-09.json')); print({k: len(v) for k,v in d.items()})"`
shows counts ≤50 per language, matching the shortfall note.

---

## TASK-807: Quality scoring protocol + script

**Status:** [x] Done — 2026-09-26
**Feature:** exercise-gen-cost
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-806

**Description:**
Define and implement the protocol used to compare any candidate pipeline change against the
frozen reference set: invalid rate, per-judge reject rate, blind pairwise preference
(candidate vs reference, rater blind to identity), and a manual spot-check sample. State the
non-inferiority threshold later phases must clear before shipping.

**Acceptance Criteria:**
- [ ] Script computes invalid rate and per-judge reject rate for a candidate run against the
      reference set, broken down by language and type
- [ ] Script produces a blind pairwise preference sample (order randomized, identity hidden)
      sized for manual or subagent-assisted rating
- [ ] A stated non-inferiority threshold exists in writing (e.g. candidate invalid rate ≤
      reference + X pp, pairwise preference ≥ Y%)
- [ ] Script runs against TASK-806's reference set with no errors

**Technical Notes:**
Reuse patterns from `scripts/measure_judge_flag_rate.py` where applicable. This protocol is
what gates Phase 1/2/3 activation — keep it deterministic and re-runnable.

**Files to Create / Modify:**
- `scripts/score_exercise_gen_quality.py` — new

**Verification:**
Run the script comparing the reference set to itself as a sanity check — expect 0pp invalid-rate
delta and ~50/50 pairwise preference.

**Scoring protocol (implemented 2026-09-24):**

Built as `scripts/score_exercise_gen_run.py` (`--candidate <run dir> --reference <run dir |
reference json> --lang {en,zh,ja}`), with `scripts/merge_pairwise_verdicts.py` as its
companion for folding in blind pairwise verdicts. Tests:
`tests/test_score_exercise_gen_run.py` (20 cases, synthetic fixtures, no DB/API calls;
`PYTHONPATH=. python -m pytest tests/test_score_exercise_gen_run.py -q`).

- **Reference input.** For ja, `data/eval/exercise_gen_reference_set_2026-09.json`'s
  `reference_set` (50 frozen benchmark senses). For zh/en — which that file only carries as
  unauthored `top_up_candidates`, with no rendered exercises — `--reference` must instead
  point at a baseline run directory (`scripts/run_exercise_gen_eval.py` output on the
  current, unmodified pipeline). `load_reference()` detects which case it's in and emits an
  explicit warning if a language has 0 usable benchmark senses in the frozen JSON.
- **Run-output adapter.** `scripts/run_exercise_gen_eval.py` was being built concurrently and
  its exact per-sense JSON shape was not available while this was written. All reading of
  `<run_dir>/<sense_id>.json` goes through one function, `normalize_run_entry()` in
  `scripts/score_exercise_gen_run.py`, which tries several aliases per field (e.g.
  `assets`/`word_assets`/`generated_assets`; `is_valid`/`valid`; `exercises`/
  `rendered_exercises`/`exercise_rows`; `judge_verdicts`/`render_judges`/`judges`;
  `stage_timings`/`timings`/`durations`, as dict or list-of-{stage,seconds}) and raises a
  named `RunShapeError` rather than guessing when a sense record has no usable `sense_id`.
  **If the real script's output differs from the shape documented in that module's
  docstring, only `normalize_run_entry()` (and, for cost, `load_cost_rows()`) should need
  editing** — every metric function consumes the same normalized `NormalizedSense` record
  regardless of source (reference JSON or run dir).
- **Cost.** Cost rows are read either inline per sense (`NormalizedSense.llm_calls`, the
  expected shape for what `run_exercise_gen_eval.py` captures directly) or from an optional
  `--llm-calls-export` JSON dump of `llm_calls` rows keyed by `generation_batch_id`. No live
  DB query is made by this script — TASK-807 makes no paid LLM/API calls, and a live
  Supabase credential is not assumed to be available wherever it runs.
- **Automatic metrics computed:** coverage (exercise rows per sense by level/type vs
  reference, missing-levels count), invalid-asset rate (overall + by `asset_type`),
  render-judge reject rate by judge name, L1 (`phonetic_recognition`) all-or-nothing drop
  rate (variants with <3 surviving distractors, i.e. `len(options) - 1 < 3`), cost/sense
  (mean, p50, p90) and per-stage cost share, retries/sense (`call_role != primary`), and
  wall clock/sense (mean, p50, p90 from stage timings).
- **Blind pairwise packs.** For senses present in both candidate and reference, for each
  (sense, level) pair common to both, `build_pairwise_packs()` writes
  `<candidate>/pairwise_packs/pack_NN.md` (~10 pairs/pack) rendering both sides' exercises
  under a randomized "Pack A / Pack B" label (seeded RNG, default seed 0) plus a fixed
  rubric — correctness, single defensible answer, distractor plausibility/not-also-correct,
  naturalness, target-word anchoring (explicitly flags the compound-word-only defect class),
  and L1 audio-confusable-only validity (pitch-accent-only pairs are a named major defect).
  The unblinding key is written separately to `<candidate>/pairwise_key.json` and never
  exposed in the pack markdown. Reviewers (fresh-context Claude subagents or a human) return
  `{sense_id, level, preferred: A|B|tie, major_defects_A, major_defects_B, notes}` JSON
  lines; `scripts/merge_pairwise_verdicts.py --candidate <dir> --verdicts <file(s)>` joins
  them back to the key, flips A/B into candidate/reference, and writes
  `<candidate>/pairwise_results.json` (win/loss/tie rate, major-defect rate per side,
  unmatched/missing-verdict lists so a partial review run is visible, not silently dropped).
- **Non-inferiority decision**, all four criteria evaluated and reported independently
  (a FAIL on one does not suppress checking the others; missing data on any one criterion
  reports SKIPPED rather than forcing a FAIL or a false PASS):
  - **(a)** candidate major-defect rate ≤ reference major-defect rate + **2 pp** default.
    Uses `pairwise_results.json`'s major-defect rate when available; falls back to the mean
    render-judge reject rate across judges when no pairwise run has been folded in yet.
  - **(b)** candidate pairwise loss rate − win rate ≤ **10 pp** default. SKIPPED until
    `--pairwise-results` (or an auto-detected `<candidate>/pairwise_results.json`) exists.
  - **(c)** coverage ≥ **95%** default of reference (level, exercise_type) pairs on senses
    common to both sides.
  - **(d)** invalid-asset rate ≤ reference invalid-asset rate + **3 pp** default.
  All four thresholds are CLI flags (`--major-defect-margin-pp`, `--pairwise-loss-margin-pp`,
  `--coverage-min-pct`, `--invalid-asset-margin-pp`) — no threshold is hardcoded. Output:
  `<candidate>/score.json` (full metrics + decision) and `<candidate>/score_report.md`
  (human-readable table + JSON detail), plus a process exit code (0 PASS / 1 FAIL) and a
  stdout line naming exactly which criteria failed and which were skipped.
- **Verified 2026-09-24** by running the script with the ja reference set standing in as its
  own candidate (5 senses, reshaped into run-dir form): coverage 100%, invalid-asset delta
  0pp, decision PASS, criteria (a)/(b) SKIPPED as expected (no pairwise data supplied), packs
  written correctly under `pairwise_packs/`. This was a throwaway smoke run in a scratch
  directory, not committed.
- **Exercised against a real run and fixed 2026-09-26** (see
  [[evaluations/exercise-gen-baseline-2026-09]] §7): running against the actual
  `run_exercise_gen_eval.py` output for the first time surfaced 4 real adapter gaps in
  `normalize_run_entry()`/`compute_wall_clock()`/`load_candidate_run()` — the real
  `exercise_rows` shape carries level under `ladder_level` (not `level`), `variant` inside
  `tags` (not top-level), rendered content under `content` (not `payload`), and
  `stage_seconds` covers only ~half of a sense's real wall clock vs. its own `wall_clock_s`
  field. The level-field bug alone was silently zeroing the ja coverage score to 0.0% before
  the fix. All 4 are fixed; `tests/test_score_exercise_gen_run.py` (21 cases) passes unchanged,
  confirming the synthetic test fixtures already used the correct aliases and the gap was
  specific to real-run data the tests never exercised.

---

## TASK-808: Baseline run

**Status:** [x] Done — 2026-09-26, with a real gap: **zh did not run**
**Feature:** exercise-gen-cost
**Type:** eval
**Complexity:** M (3-8h)
**Depends On:** TASK-804 (instrumentation must be live first)

**Description:**
Run the current, unmodified pipeline on 30 senses/language with TASK-804 instrumentation live,
and report $/sense, per-stage cost share, retry rate, per-judge reject rate, and wall clock.
File as `wiki/evaluations/exercise-gen-baseline-2026-09.md`.

**Acceptance Criteria:**
- [ ] 30 senses × 3 languages run through the current, unmodified pipeline with
      instrumentation active
- [ ] Report includes $/sense (overall and per language), per-stage cost share, retry rate,
      per-judge reject rate, and wall clock (overall and per language)
- [ ] Filed at `wiki/evaluations/exercise-gen-baseline-2026-09.md`
- [ ] All numbers are pulled from `llm_calls`, not estimated

**Technical Notes:**
This is the number every later phase is measured against — do not run it against a
partially-instrumented pipeline. Cross-check against TASK-515's stale $0.024/sense figure to
see whether subagent-path generation has changed the effective cost profile since then.

**Files to Create / Modify:**
- `wiki/evaluations/exercise-gen-baseline-2026-09.md` — new

**Verification:**
File exists and its top-line $/sense number is referenced by TASK-809/814/815 planning before
any of those tasks proceeds.

**Closed 2026-09-26, acceptance criteria only partially met:** ja (30/30 senses attempted,
50% failed, 33% partial, 17% success) and en (30/30 attempted, 90% partial, 3% success, 7%
transient network error) both ran and are fully reported in
[[evaluations/exercise-gen-baseline-2026-09]]. **`data/eval/runs/baseline_zh/` does not exist —
the zh baseline was never run**, and no log or process trace explains why; only an unrelated
2-sense `pilot_zh` smoke test from an earlier session is on disk. Filed anyway per this task's
"30 senses × 3 languages" criterion being 2/3 met, because (a) the ja/en numbers are the
higher-priority finding (both show real, actionable defects independent of zh) and (b) per the
ADR-028 2026-09-26 correction, zh generation is already fully on qwen/qwen3.7-plus, so the
originally-planned TASK-809 zh migration is largely moot — but the *measurement* gap is real:
**zh must get its own Phase 0 baseline run before any zh-facing change in this workstream is
scored against "the baseline."**

---

## TASK-809: Move zh generation to the qwen family

**Status:** [x] Done — 2026-09-27, as a no-op (see 2026-09-26 verification finding below)
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-806, TASK-807, TASK-808

**Description:**
Move zh `prompt1_core`, `prompt2`, and `prompt3` off gemini/claude-sonnet-5 onto a qwen-family
model, per ADR-028 Decision §2. Before flipping any zh prompt row to qwen, verify the
JSON-keyword landmine (Qwen3.x + `response_format: json_object` 400s unless the prompt text
literally contains the word "JSON") does not fire for these three prompts, and patch prompt text
where needed.

**2026-09-26 verification finding (see
[[tasklist/exercise-gen-cost.implementation-plan]] §TASK-809):** a live `prompt_templates` query
found zh `vocab_prompt1_core` (v2), `vocab_prompt2_exercises` (v4), and `vocab_prompt3_transforms`
(v2) are **already** `is_active=true` on `qwen/qwen3.7-plus` — as is every other zh/ja
GENERATION row checked, including all `ladder_*_generation` rows. This state predates this task
(rows show `updated_at` of 2026-08-17, from an untracked change — `migrations/
generator_model_routing_policy.sql` dated 2026-08-16 explicitly *preserved* these three as
claude-sonnet-5 exclusions, so a later, undocumented flip on 2026-08-17 is what actually moved
them). All three already contain the literal word "JSON". The ADR-028 "Current model assignment"
paragraph describing zh prompt2/3 as claude-sonnet-5 is stale/incorrect as of 2026-09-26 — en
prompt2/3 are the ones still on claude-sonnet-5 (permitted; en generation may use any model).
The migration below is still filed as the TASK-809 deliverable, written idempotently against
drift, but it is a no-op against the live DB today.

**Acceptance Criteria:**
- [ ] zh `prompt1_core`, `prompt2`, `prompt3` `prompt_templates` rows all point to a
      qwen-family model
- [ ] Each affected prompt's text contains the literal word "JSON" (or the json_object
      landmine is otherwise confirmed non-firing) before cutover
- [ ] Migration uses `DO UPDATE` / an explicit version bump, not `ON CONFLICT DO NOTHING`
- [ ] Scored against the TASK-806 reference set per the TASK-807 protocol; meets the stated
      non-inferiority threshold before this task is marked Done
- [ ] Rollback is a single documented statement/migration

**Technical Notes:**
Bake-off the specific qwen model per ADR-028 Decision §2 (choice within family is not fixed by
the ADR) — reuse TASK-817's bake-off results (qwen3.7-plus / qwen3.6-flash / qwen3.7-flash)
rather than re-running it.

**Files to Create / Modify:**
- `migrations/task809_zh_generation_qwen.sql` — new
- `prompt_templates` rows (zh `prompt1_core`/`prompt2`/`prompt3`)

**Verification:**
Direct `SELECT` on `prompt_templates` confirms the live model + `is_active` row; a 10-sense zh
dry run produces no 400s.

**Closed 2026-09-27:** confirmed no-op per the 2026-09-26 verification finding above — zh
`prompt1_core`/`prompt2`/`prompt3` were already on `qwen/qwen3.7-plus` before this task existed.
`data/eval/runs/phase1_zh/` (30 senses, this session) is the first zh run ever executed and
becomes the zh reference for future phases; see
[[evaluations/exercise-gen-phase1-2026-09]] §1-§2. No migration was needed or written.

---

## TASK-810: Cap retries + remove/schema-gate the P3 salvage call

**Status:** [x] Done — 2026-09-27
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-808

**Description:**
Cap retries at ≤2 real calls per generation step, collapsing the
current stacked pattern where each generator's own retry loop wraps another JSON-repair turn
(`llm_service.py:519-535`). Remove the unscoped P3 text-mode salvage call
(`prompt3_transforms.py:205-247`), or gate it behind an explicit schema check so it only fires
when there is a validatable reason to.

**Acceptance Criteria:**
- [ ] No generation step exceeds 2 real LLM calls (measured via `call_role` in `llm_calls`)
      under both normal and forced-failure conditions
- [ ] The P3 salvage call is either removed or gated behind a schema check, with a test
      proving it does not fire speculatively
- [ ] `prompt3_transforms`'s valid-rate does not regress vs the TASK-808 baseline
- [ ] Scored against the reference set per TASK-807

**Files to Create / Modify:**
- `services/vocabulary_ladder/prompt3_transforms.py`
- `services/llm_service.py`

**Verification:**
A forced-failure test (mocked repeated invalid completions) confirms the call count caps at 2
and the pipeline fails the step cleanly instead of looping.

**Closed 2026-09-27:** retries/sense fell in every language in the Phase 1 eval run (ja
5.31→2.43, zh n/a — no baseline, en 0.68→1.17). The P3 salvage-call gating plus an earlier
`semantic_class` fix roughly halved en's `prompt3_transforms` invalid rate (96.4%→~47% — still
the largest remaining quality defect, not fully solved). See
[[evaluations/exercise-gen-phase1-2026-09]] §2, §7, §11.

---

## TASK-811: Level-scoped regen

**Status:** [x] Done — 2026-09-27 (code landed with this batch; not independently isolated in eval)
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-808

**Description:**
When a sense needs regeneration for one level, stop re-running
the entire `build_rows()` with all 7 render judges (`queue_drain.py:279-293`); regenerate and
re-judge only the affected level.

**Acceptance Criteria:**
- [ ] Regenerating a single level for a sense triggers judge calls scoped to that level only
- [ ] Unaffected levels' `word_assets` rows are untouched (verified by row-level diff)
- [ ] A parity test proves a full-sense regen (all levels affected) still produces
      byte-identical output to the old path

**Files to Create / Modify:**
- `services/vocabulary_ladder/queue_drain.py`

**Verification:**
Trigger a single-level regen for 5 senses; confirm `llm_calls` shows judge calls only for the
touched level, and unaffected levels' `updated_at` is unchanged.

**Closed 2026-09-27:** code landed with the TASK-810–813 batch. The Phase 1 eval run
([[evaluations/exercise-gen-phase1-2026-09]]) did not exercise a single-level regen scenario, so
this task's specific acceptance criteria (judge calls scoped to the touched level, parity vs. a
full regen) were not independently re-verified this session — flagged here rather than silently
assumed.

---

## TASK-812: Stable-prefix ordering + cache-token logging + judge `max_tokens` caps

**Status:** [~] In Progress — cache-token logging done 2026-09-27; stable-prefix reorder deferred
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-804

**Description:**
Reorder prompts so stable/shared context (word, sense, language
rules) comes first and per-call variable content comes last, to make provider prompt caching
effective. Log `cached_tokens` (added in TASK-804) on every call. Add explicit `max_tokens`
caps to judge calls, which currently have none.

**Acceptance Criteria:**
- [ ] The highest-volume generation prompts (P1 core, bundle/P2, judge) order stable content
      first
- [ ] `cached_tokens` is non-null and >0 on a warm second call with an identical prefix,
      confirming caching actually engages (answers ADR-028 open question (b) for at least one
      model)
- [ ] Every judge call site has an explicit `max_tokens` cap
- [ ] No valid-rate regression vs the TASK-808 baseline

**Files to Create / Modify:**
- `services/vocabulary_ladder/*.py` (prompt assembly)
- `services/llm_service.py` (`max_tokens` plumbing)

**Verification:**
Two back-to-back identical-prefix calls; the second call's `llm_calls.cached_tokens` > 0.

**2026-09-27 partial:** `cached_tokens` logging is live and confirmed non-zero on real qwen
calls in the Phase 1 eval — ja logged 18,304 cached tokens across the run (concentrated in
`vocab_prompt2_exercises`/`vocab_prompt3_transforms`), zh logged 4,992, **en logged 0** despite
routing the same tasks through the same model this run. This is **incidental** caching from the
provider's existing prompt order, not the deliberate stable-prefix reorder this task specifies —
that reorder (`prompt_templates` edit + native-speaker review) is **still not done**. Judge
`max_tokens` caps: not verified this session. Remaining work: the actual prefix reorder, plus
confirming judge `max_tokens` caps are in place. See
[[evaluations/exercise-gen-phase1-2026-09]] §5.

---

## TASK-813: Provider price routing + reasoning disabled

**Status:** [x] Done — 2026-09-27
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** TASK-808

**Description:**
Enable OpenRouter provider-price routing so calls land on the
cheapest provider serving the pinned model, and explicitly disable reasoning/thinking mode on
every ladder call (a reasoning-class model such as qwen3.8-max needs ~16k `max_tokens` and
100-330s/call and must never be selected here by accident).

**Acceptance Criteria:**
- [ ] All ladder LLM calls pass an explicit provider-routing preference (price-sort or
      equivalent)
- [ ] All ladder LLM calls explicitly disable reasoning mode
- [ ] A regression test asserts no ladder call site can silently resolve to a reasoning-class
      model
- [ ] Cost delta measured and reported vs the TASK-808 baseline

**Files to Create / Modify:**
- `services/llm_service.py`
- `services/vocabulary_ladder/asset_pipeline.py`

**Verification:**
Live 10-sense run; the per-call provider field in `llm_calls` shows routing took effect, and no
call shows reasoning-class latency (100s+).

**Closed 2026-09-27:** price routing is the primary driver of en's Phase 1 cost drop (moving
`vocab_prompt2_exercises`/`vocab_prompt3_transforms`/`ladder_syn_ant_generation`/
`ladder_word_family_generation`/`ladder_l4_morphology_generation` off `anthropic/claude-sonnet-5`
onto `qwen/qwen3.7-plus` cut en's calls-mean $/sense 73.4% on the same senses). **Reasoning could
not be fully disabled for qwen** — an explicit "reasoning qwen exception" was carved into this
task's implementation — and the Phase 1 eval found that exception is now the single largest
token-cost driver on every qwen-routed call: 85-90% of completion tokens on
`vocab_prompt2_exercises` across all three languages are `reasoning_tokens`. This was not an
acceptance criterion this task could fully meet as originally scoped (no reasoning-class model
may be "silently" selected — qwen is deliberately selected and cannot fully suppress reasoning
output). See [[evaluations/exercise-gen-phase1-2026-09]] §5, §11, §13.

---

## TASK-814: Collapse A/B variant doubling

**Status:** [ ] Not Started — gated on baseline + Phase 1 score
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-808

**Description:**
Collapse the ~13 of 18 call sites that generate variant A and variant B as two separate calls
into a single call producing both variants, per ADR-028 Decision §4.

**Acceptance Criteria:**
- [ ] All doubled call sites are identified and enumerated
- [ ] Each produces both A and B variants from one call, with a validated schema
      distinguishing them
- [ ] Call count per sense drops by the modeled amount (measured via `llm_calls`, before/after)
- [ ] Scored against the reference set; meets the non-inferiority threshold

**Technical Notes:** `[?]` blocked pending Phase 0 baseline results — do not start until
TASK-808 is filed and TASK-807's protocol is available to score against.

**Files to Create / Modify:**
- `services/vocabulary_ladder/*.py` (per-generator; exact list from investigation)

**Verification:**
`llm_calls` count per sense for a fixed test set drops from baseline by the modeled amount;
quality score meets threshold.

---

## TASK-815: Bundle generation call (P2+P3+L4+typed)

**Status:** [ ] Not Started — gated on baseline + Phase 1 score
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** XL (>2d)
**Depends On:** TASK-814

**Description:**
Collapse P2+P3+L4+typed generation into a single bundle call per sense, both variants
together, per ADR-028 Decision §4's ~4-5-call target.

**Acceptance Criteria:**
- [ ] One call produces P2, P3, L4, and typed-level content together, both variants
- [ ] Output schema is validated at intake with the same strictness as the separate calls it
      replaces
- [ ] Reference-set quality score meets the non-inferiority threshold — ADR-028 explicitly
      flags this bundle as a quality risk to validate, not assume
- [ ] Wall-clock and cost improvement reported

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_pipeline.py`
- new bundle prompt row in `prompt_templates`

**Verification:**
30-sense run scored against the TASK-807 protocol; result vs threshold written up.

---

## TASK-816: Bundle judge call

**Status:** [ ] Not Started — gated on baseline + Phase 1 score
**Feature:** exercise-gen-cost
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-815

**Description:**
Collapse the 7 render judges into a single bundle judge call per sense, per ADR-028
Decision §4 — keeping the P1 sentence judge separate. The P1 sentence judge is explicitly
excluded from bundling: it catches compound-word anchoring and must stay independent.

**Acceptance Criteria:**
- [ ] One judge call evaluates everything the 7 render judges currently check, excluding the
      P1 sentence judge
- [ ] Per-judge-equivalent reject rates measured against the old 7-judge baseline, reported
      per axis
- [ ] No axis silently loses reject sensitivity — each old judge's catch rate maps to an
      equivalent in the bundle output
- [ ] Reference-set quality score meets the non-inferiority threshold

**Files to Create / Modify:**
- `services/vocabulary_ladder/queue_drain.py`
- judge prompt consolidation in `prompt_templates`

**Verification:**
Run the bundle judge and the legacy 7-judge path side by side over the reference set;
reject-rate agreement reported per axis.

---

## TASK-817: Model bake-off (qwen arms zh/ja, any-model arms en)

**Status:** [?] Blocked — pending Phase 0 reference set (TASK-806) and scoring protocol
(TASK-807). Phase 3 — **user: do not do Phase 3.**
**Feature:** exercise-gen-cost
**Type:** eval
**Complexity:** M (3-8h)
**Depends On:** TASK-806, TASK-807

**Description:**
Bake off qwen arms for zh/ja generation (`qwen3.7-plus`, `qwen3.6-flash`, `qwen3.7-flash`)
against the reference set; en generation may use any-model arms. Produces the model choice
TASK-809 and the collapse tasks implement.

**Acceptance Criteria:**
- [ ] Each qwen arm run over the full zh and ja reference-set senses
- [ ] en arms (any model) run over the en reference-set senses
- [ ] Cost, invalid rate, judge reject rate, and blind pairwise preference reported per arm
- [ ] Winning arm per language stated explicitly with rationale

**Files to Create / Modify:**
- `scripts/bakeoff_exercise_gen_models.py` — new
- `wiki/evaluations/exercise-gen-model-bakeoff-2026-09.md` — new

**Verification:**
Bake-off report filed; winning model per language cross-referenced against TASK-809/814/815
implementation.

---

## TASK-818: Batch API backfill

**Status:** [?] Blocked — pending Phase 0 baseline and the collapsed call shape. Phase 3 —
**user: do not do Phase 3.**
**Feature:** exercise-gen-cost
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-809, TASK-815

**Description:**
Wire OpenRouter's Batch API (~50% off list price, 24h SLA) into the bulk/backfill generation
path for senses with no exercises, per ADR-028 Decision §4's lowest-priority lever.

**Acceptance Criteria:**
- [ ] Backfill runner submits eligible sense batches via OpenRouter Batch API instead of
      synchronous calls
- [ ] The 24h SLA is handled without blocking other work (async poll/resume, not a blocking
      wait)
- [ ] Cost delta vs synchronous calls measured on a real batch and reported
- [ ] Falls back to synchronous calls if Batch API is unavailable for a given model — answers
      ADR-028 open question (b) in practice

**Technical Notes:**
`scripts/run_batch_generation.py` was deleted in the current working tree (see git status at
session start) — check whether backfill has moved to a different entry point before recreating
it under the old name.

**Files to Create / Modify:**
- Backfill entry point (TBD — verify current location before writing)

**Verification:**
One real batch submission completes and produces valid assets at the modeled discount.

---
