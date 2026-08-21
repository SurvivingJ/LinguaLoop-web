---
title: Master Task List
last_updated: 2026-08-21
---

# Master Task List

This file lists **only incomplete work** (Not Started / Blocked). Completed tasks are not
enumerated here — see the archived per-feature tasklists in `wiki/tasklist/archive/` for full
history, per-task Acceptance Criteria, Files, and Verification steps.

This version supersedes the previous `master.md`, which had drifted: a 2026-07-13 codebase +
live-Supabase audit found the **Practice Engine Merger** and **Study Plans** features were almost
entirely shipped (committed 2026-05-21) but their task checkboxes were never flipped, and one
Dual Translation migration (TASK-609) was live but unmarked. See "Recently confirmed complete"
below.

## Summary

| Status | Count |
|--------|-------|
| Not Started | 8 |
| In Progress (`[~]`) | 7 |
| Blocked / Deferred (numbered tasks) | 3 |
| Blocked (language-packs, unnumbered — design resolution needed) | all |
| Won't Do (obsolete) | 1 |
| Done (cumulative, not listed here) | 134 |

**TASK-719 + TASK-720 done 2026-08-20 — the distractor judge has two axes; rows staged, not
activated.** The single 1-5 rating split onto **fit** (is this the passage's subject?) and
**confusability** (would a learner take it for the answer?), with the verdict arithmetic moved into
`schemas.axes_to_verdict` behind named cut points, and band 3 on both axes redefined as *the judge
is not confident* with the triggering axis written into `generation_review_queue`. v7 prompt rows
authored in all three languages (zh/ja natively, qwen3.8-max) and landed **`is_active = false`**.
Measured live-vs-v7 on the 179-question TASK-721 sample, same model in every cell, 358 calls,
**$0.2738**. Three findings worth carrying forward:

* **The attribution is unanimous, not merely present.** 100% of v7 flags are *confusability*
  flags — zh 31, en 13, ja 17 — and the fit axis produced **zero**. The queue now says something
  specific enough to act on.
* **The fit axis went near-binary.** Zero 3s anywhere and band 4 nearly gone (zh 47→2, ja 65→2).
  Splitting made the model *more* decisive about subject membership, so fit alone now carries
  almost no information — it cannot be kept and confusability dropped.
* **The also-correct failure is rare, not newly detectable.** 1/537 on the confusability axis vs
  3/1,800 for the old band 1 — the same rate. TASK-719's acceptance criterion is met, but the case
  for v7 rests on the review signal, not on catching also-correct distractors.

**Why staged:** question-level review volume goes from 0-3% to **22-47%**, and TASK-726's gold set
— the only thing that could say whether that is honest uncertainty or a timid prompt — is still
unadjudicated. Third prompt intervention in this workstream to be built, measured and staged
(after TASK-717 v5 and TASK-721). The code is live-safe against the current v4/v6 rows, so staging
costs nothing. Suite 1843 → **1869**. Not Started 10 → **8**.
See [[evaluations/distractor-judge-two-axis-2026-08-20]].

**TASK-726 machine half done 2026-08-19 — the gold-set frame exists; only adjudication remains.**
573 items (zh 213 / en 180 / ja 180) drawn from live-stack output, pre-rated by both TASK-718
models, post-stratified to the production question mix, and split into primary + 60-item overlap
labeller sheets, with the merge/κ-gate/scoring harness shipped and unit-tested (37 tests; suite
1806 → **1843**). **Spend $0.73.** Two findings on the way: the **reject-set disjointness
reproduces on fresh content** and is worse than on the frozen 150 (qwen 56 rejects, gemini 3,
overlapping on 3; en agrees on **zero** across 180 items; of the 55 items qwen bands "off-topic,
reject" gemini rates **35 a 5**) — and **uniform-by-type sampling has been mis-weighting every
rate in this workstream**, so reweighting the live judge to the production mix moves it
**0.52% → 0.92%** and TASK-721's "0.6% on fresh output" understates production by ~1.8×. What is
left is human time, not spend: native zh/en/ja adjudication of 573 items plus a 180-item overlap.
Not Started 11 → **10**, In Progress 6 → **7**.
See [[evaluations/distractor-gold-frame-2026-08-19]].

**TASK-723 entailment half closed 2026-08-19 — v3 activated, measured, and the ja judge model
fixed.** The tasklist's "staged, NOT activated" status line was **stale**: v3 has been live in all
three languages since 2026-08-19 10:11:32Z. The third cutover move (restart) is **moot, not
skipped** — no app process exists, so no stale `_cfg_cache` can be holding a pre-Likert row.
Gold re-measurement and post-rollout band usage both ran (450 + 300 calls, **$0.2135**): **all five
bands fire in all three languages, 0 unparsed**, overall AUC 0.957 — the first time this judge
family has used its full scale. ja was the outlier (AUC 0.870, 18% false-accept) and it was the
**model, not the language**: moved `qwen/qwen-2.5-72b-instruct` →
`google/gemini-3.5-flash-lite` (AUC 0.940, false-accept 18% → 2%, review load 24.7% → 2.7%),
applied live. Two false premises corrected: the "no production telemetry" finding was a query
against the wrong namespace (784 rows exist under `judge_answer_entailment`), and the gold set was
never a blocker for entailment — its labels are structural and free. **New TASK-726** files the
*distractor* gold set, which is the genuine blocker on TASK-719/720, with a construction plan.
Only "one verdict mapper, not two" stays open, and it cannot close until cloze converts.
Not Started 10 → **11** (TASK-726 filed).
See [[evaluations/entailment-likert-v3-rollout-2026-08-19]].

**TASK-718 done 2026-08-16 — the zh divergence was the judge; model swapped, applied live.**
A 2×2×3 factorial (v4/v5 × qwen3.6-flash/gemini-3.1-flash-lite × zh/en/ja, 600 calls, **$1.11**)
over the frozen 150-question sample. zh rejects **16/50 → 1/50** on the live v4 prompt when only the
model changes; under a common judge zh is the cleanest language, so the content contribution is
~zero. zh and ja moved to `google/gemini-3.1-flash-lite`
(`migrations/distractor_judge_model_zh_ja_gemini.sql`), which also restores a middle band in zh/ja
and costs 6.7× less per call. Harness promoted to `scripts/measure_judge_flag_rate.py`.
**Caveat:** the two judges' reject sets are disjoint, so no reject signal is validated in absolute
terms — a gold set now gates TASK-719/720. Not Started 10 → **9**.
See [[evaluations/distractor-judge-language-divergence-2026-08-16]] §11.

**TASK-717 partially done 2026-08-16 — plumbing shipped, prompt fix measured and reverted.**
The v5 judge prompt was built, applied live, measured on the frozen 150-question sample across
four arms, and rolled back the same day. zh `vocabulary_context` rejects held at **9/16 in every
arm** — invariant to the `type_code` string, the type-conditional rubric and the subject line —
so that bucket is judge-model behaviour, not a rubric defect, and **TASK-718 is now the
load-bearing task**. The v5 rubric additionally created 5 en `vocabulary_context` rejects (v4:
0) and the subject line raised ja rejects in both arms containing it, so v4 is live and the
caller fix is gated `JUDGE_SUBJECT_KEYWORDS`, default off. Suite **1781 → 1792 passed, 3
skipped**. Not Started 11 → **10**, In Progress 5 → **6**.
See [[evaluations/distractor-judge-language-divergence-2026-08-16]] §10.

**Exercise Generation v2 batch closed 2026-08-12 — TASK-521/530/531/534 done,
526/535/536 deferred, 515 still open.** Suite **1676 → 1718 passed, 3 skipped**
(+42 tests, no regressions). In Progress 8 → **5**, Done 125 → **128**.

*Four defects were found and fixed along the way, three of which made a feature
silently inert rather than broken:*

1. **`llm_calls.cost_usd` was never written** — 12,947 rows, all NULL. Every
   budget ceiling reading it (including TASK-515's `--ceiling`) computed $0 spent
   and could never fire. Now populated from OpenRouter usage accounting.
2. **`sense_neighbours` called an RPC signature that has never existed**, and its
   `except Exception` logged the resulting PGRST202 at INFO as "RPC unavailable".
   TASK-522's embedding band checks would have stayed inert *after* the TASK-521
   backfill, indistinguishable from the backfill not having run. Fourth instance
   of the ADR-020 class.
3. **`word_assets_asset_type_check` rejected every typed-LLM asset** (23514), so
   `synonym_antonym_match` / `word_family` / `particle_selection` produced nothing
   while the pipeline reported success per sense.
4. **The audio backfill read `content.audio_url` for all types**, reporting
   0/56 coverage over 56 fully-voiced `listening_flashcard` items (they use
   `front_audio_url`) — and would have written new audio to a key the renderer
   never reads.

*Repo-record gaps closed (`migrations/CLAUDE.md`):* `dim_word_senses.embedding`,
its HNSW index and `nearest_senses()` were live since 2026-08-08 with **no
migration file at all**; the `counter_drill` test type was missing entirely, so
every counter-drill submission would have 500'd.

**TASK-537–540 closed 2026-08-11 — ladder numeric-key contract APPLIED LIVE.** All 16 ladder
prompt rows (EN/ZH/JA) now declare a numeric-key output contract with the legend written in the
prompt's own language, so no English field name sits in the output contract of a ZH or JA prompt.
`prompt_version` stayed at **1** (replace in place — `word_assets` has 0 rows bound to the v1
shape, so a bump would have left dead schema code). The 6 live EN rows were changed with
`ON CONFLICT … DO UPDATE`, since the files' previous `DO NOTHING` made a corrected re-run a
silent no-op. Every row's `md5(template_text)` was hash-matched against the `$PROMPT$` body in
its migration file (16/16) to rule out a transcription error in the CJK payload. Also landed:
worked examples for every rule that asserts a distinction (notably the JA `syn_ant` polysemy rule,
which was the only one of the three stated abstractly — now names 甘い taste-vs-lenient), the
error escape `{"9": "<token>"}` as a *clean skip* rather than a failure, provider-enforced
`response_format='json_object'` at all seven ladder call sites, and a regression test pinning the
two ladder judges to one shared Likert polarity. Step 7 of `ladder_prompt_split_l4_l8.sql`, held
back on 2026-08-10, applied. Suite 1609 → **1634 passed, 3 skipped**.
Not Started 9 → **5**, Done 121 → **125**.

**TASK-629 closed 2026-08-10 — rubric v6 APPLIED LIVE.** `migrations/dt_rubric_v6_seed.sql` was
applied to Supabase via MCP `apply_migration`; v5 → v6 is now the active rubric and live grading
uses the v3 band descriptors. Both seed guards passed, and the descriptors-only contract was
verified live (band_descriptors differ from v5; weights/exemplars/acceptable_variation/
band_thresholds/severity_weights/understandability_weights all still equal v5). All 336 descriptor
leaves were hash-matched against the repo file (md5 `62e6c6c3…`, both sides) to rule out a
transcription error in the 46 KB payload. In Progress 9 → **8**, Done 120 → **121**.
**Evidence-First Grading (TASK-620–649) is now fully closed — no open rows.**

**Recount 2026-08-10 (TASK-638/642/645/647/648 closed — reconciliation, not new code).**
All five were already implemented, committed and covered by tests; only their checkboxes were
stale — the same drift class as the 2026-07-13 audit below. Verified per-task against the source
(not just the test names) and by `pytest -k "dual_translation or dt_"` → **600 passed**.
`git status` on `services/dual_translation/` is clean, so this was shipped code, not
working-tree-only work. Evidence-First Grading Not Started 5 → **0**; the feature's only
remaining open row is TASK-629 (`[~]`, live rubric-v6 apply owed). Totals: Not Started 14 → **9**,
Done 115 → **120**. In Progress unchanged at 9.

**Caveat carried forward:** TASK-642's Verification also named a live/staging smoke proving one
rubric+taxonomy fetch per activated version rather than per submission. That smoke has **not**
been run — the in-process caching is proven by tests, the deployment-shape claim is not. Noted on
the task rather than silently absorbed into the Done count.

**Recount 2026-08-11 (operator-gated batch cleared).** Nine rows moved `[~]` → `[x]`:
TASK-517, 520, 522, 523, 525, 527, 529, 532, 533. Exercise Generation v2 In Progress
14 → **5** (515, 521, 526, 530, 531). The full suite is green at **1676 passed, 3 skipped**.

Three of those nine were **already satisfied and only the checkbox was stale** — the same
drift class as the 2026-07-13 audit. `ladder_prompt_split_l4_l8.sql` (TASK-520),
`syn_ant_word_family_prompts.sql` (TASK-522) and `particle_selection_prompts.sql` (TASK-527)
were all verified present live by querying `prompt_templates` directly; only TASK-525's three
`translation_uniqueness_judge` rows were genuinely missing, and they were applied. **Verify
against the live DB before trusting a "migration not applied" note** — the note outlived the
condition by a day in three cases out of four.

The other six were real work:
- **517** — `run_nightly_drain()` behind `pg_try_advisory_lock_for_queue_drain` (key
  1363440238, `task517_queue_drain_advisory_lock.sql`, applied), a 04:15 UTC cron in
  `_initialize_scheduler`, and the `subscribe_topup` enqueue on the dojo word-open path.
  The lock is what makes `_claim_batch`'s non-atomic claim safe — its docstring already
  assumed a lock that did not exist.
- **523** — the OANC list is vendored: `data/collocations/en_collocations.tsv`, 73.7k
  dependency-parsed pairs from 18.3M words, public domain, built by
  `scripts/build_en_collocations.py`. The finding-G6 case now behaves: `personalize` +
  `advertising` returns no match and tags `llm_asserted`.
- **525** — the migration was rewritten to `ON CONFLICT ... DO UPDATE` before applying. Its
  header claimed "re-runnable" but the bare `INSERT` would have aborted on the unique index
  `idx_prompt_templates_task_lang_ver`, *after* the deactivating `UPDATE` in the same
  transaction — so a second run would have rolled back to a deactivated judge.
- **529** — `dim_character_components` populated, 27,131 rows, 100% radical/stroke coverage.
  Source decision: **cjk-decomp (Apache-2.0) + Unihan (Unicode License)**. `cjkvi-ids` was
  rejected as **GPLv2** — copyleft on a vendored data file would follow it to every
  deployment, the same test `data/collocations/README.md` applies to the English list.
- **532** — `cloze_typed` renderer with IME composition handling, plus **server-side
  grading**: the normalisation rule (NFKC/t2s/case/punctuation) lives in Python, so the
  client's `is_correct` is overwritten for this type rather than reimplemented in JS.
  39-case normalisation matrix in `tests/test_answer_normalization.py`.
- **533** — the session queue now emits a `speed_round` bonus block. Deliberately **not** a
  `_SURFACE_BLOCKS` member: ADR-021 puts it outside the planner (mastered-only, no weekly
  target, must not move family confidence), so it is appended after the planned queue and
  credits no counter.

**Two latent defects were found while doing this and are fixed:**
1. `deterministic._load_builders()` guarded on `if _REGISTRY:`. A non-empty registry only
   means *one* builder was imported — and `routes/practice.py` now imports `cloze_typed`
   directly for `grade`. Under the old guard that single import made the loader a no-op and
   left the other six builders unregistered: every sense would generate one exercise type
   instead of seven, with no skip reason. Now guarded on a dedicated `_BUILDERS_LOADED` flag.
2. `BundledCollocationList.load()` skipped **any** row whose first column was `head`, not
   just the header — silently discarding every collocation headed by the noun *head*
   (head/coach, head/department). Now only the first non-comment row is treated as a header.

**Repo-record gaps closed** (`migrations/CLAUDE.md`: the directory must reflect every live
object). `dim_character_components` and the three `dim_counter_*` tables were live with **no
migration file at all**; `migrations/dim_character_components.sql` and
`migrations/counter_drill.sql` now record them, written `IF NOT EXISTS` to match live.

**Recount 2026-08-09 (TASK-520/522/523/526/527/531/533 opened).** All seven moved
`[ ]` → `[~]`: code, tests and migrations are written and the full suite is green
(1609 passed), but each is held short of `[x]` by something only an operator can do —
four unapplied prompt migrations, an un-vendored English collocation list, an Azure TTS
run, and a live 發/髮 spot-check. Totals: Not Started 21 → **14**, In Progress 2 → **9**,
Done unchanged at 115. The per-task "what is outstanding" column in
`archive/exercise-generation-v2.tasks.md` is the authoritative list.

**Recount 2026-08-08 (TASK-510/512/519 shipped, TASK-514 opened).** Exercise Generation v2
Not Started 23 → **19**: TASK-510, 512, 519 closed and TASK-514 moved to `[~]`. Totals:
Not Started 28 → **24**, In Progress 1 → **2** (TASK-629, TASK-514), Done 109 → **112**.

**Fourth recount, same day (TASK-513/514/524 closed, TASK-525 opened).** Exercise
Generation v2 Not Started 19 → **16**: TASK-513 and TASK-524 closed, TASK-514 moved
`[~]` → `[x]`, TASK-525 moved `[ ]` → `[~]`. Totals: Not Started 24 → **21**,
In Progress 2 → **2** (TASK-629, TASK-525), Done 112 → **115**.

TASK-514's B5 is now closed: gating is per exercise *type*, not per level, on both the
generation and render sides — a ZH concrete noun keeps L4 (classifier_match, cloze_typed)
while P3 stops asking for morphology. The one AC still owed is the regen smoke on a real
sense, which needs live LLM + DB spend.

TASK-525 is `[~]` rather than `[x]` because
`migrations/translation_uniqueness_judge_prompts.sql` is written but **not applied live**.
The judge fails open on a missing template, so until an operator runs it, tl_nl items ship
unjudged outside a batch.

**Third recount, same day, after TASK-714/715/716 shipped.** Those three were the last open rows in
Daily Session Hardening; closing them takes Not Started 31 → **28** and Done 106 → **109**. The
feature now has no open work.

**Counts recomputed 2026-08-07 (TASK-713).** The previous "Not Started 40" was stale — it did not
match this file's own tables. Recounted directly from the `[ ]` rows below: Exercise Generation v2
**23** (TASK-510, 512–533) + Evidence-First Grading **5** (TASK-638, 642, 645, 647, 648) + Daily
Session Hardening **0** = **28**. Blocked `[?]` = TASK-534, 535, 536, 711, 712 = **5**. In progress
`[~]` = TASK-629 (v6 authored + evaluated, live apply owed). Done incremented 102 → **104** for
TASK-709 and TASK-713. Note the Study Plans TASK-201–219 flip in
[[tasklist/archive/study-plans.tasks]] did **not** move the Done total — those were already counted
as complete in the 2026-07-13 audit below; only their per-task checkboxes were stale.

**Second recount, same day, after the TASK-711/712 decisions landed.** Those two moved from
Blocked to Done (Blocked 5 → **3**: only TASK-534/535/536 remain, all awaiting launch data; Done
104 → **106**), and the decisions filed three new implementation tasks — TASK-714, 715, 716 —
taking Not Started 28 → **31**. Net: the Daily Session Hardening *batch* is closed, but the work it
uncovered is not, and the counts say so rather than hiding it.

**Completed 2026-07-18:** **TASK-627** (derived-scoring module + rubric v5). `services/dual_translation/scoring.py`
— pure `compute_dimension_bands` (severity-weighted accuracy/fidelity penalties + understandability
axis, `is_mistake` excluded) and `compute_overall` (weighted mean **renormalized over present
dims**, so an absent judged dimension isn't defaulted to full marks); `scoring_params` RAISES on a
pre-v5 config rather than silently full-marking. §4 worked example reproduced exactly against the
real seeded v5 config + taxonomy v5 (acc 3 / fid 4 / und 4 / overall 4); 25 scoring tests + 502 DT
green; the gold-seed-helper pinning + v5-key guards now fire green. `dt_rubric_v5_seed.sql`
self-contained, `band_thresholds` FLAT `{dim:[t4,t3,t2]}` per the pinned TASK-641 contract (not the
tech-spec §4 nested example), provisional defaults sev 1/5/25 · und 0/2/25 · thresholds 1/6/15 &
und 2/6/25 — applied live as active v5, verified byte-identical to `v4 + keys` with
descriptors/weights = v2. `scripts/rescore_dt_grades.py --rubric-version N --dry-run` re-scores
stored grades with zero model calls; dry-run over 2 live grades printed before/after deltas, no
writes. NOT wired into `grade_submission` — TASK-628 owns that.

**Completed 2026-07-19:** **TASK-628 / 630 / 631 / 632** — the Evidence-First v2 stack is LIVE.
The TASK-632 harness ran the full gold sets through the v2 Detector/Verifier flow with the rubric
v6 config as a candidate (`--rubric-file`, new): EN span F1 .543→**.941**, clean FP .200→**.000**,
overall QWK .512→**.824**; JA span F1 .696→**.880** (clean FP .000→.100, one item — documented);
ZH filed. Results: [[evaluations/dt-grading-v2-2026-07-19]]. `Config.DT_FRAMEWORK_V2` now defaults
**ON** (rollback = env `DT_FRAMEWORK_V2=false`). v1 cascade pages marked deprecated/superseded.
**TASK-629 stays [~]:** v6 is authored+tested+evaluated but its live Supabase apply was blocked by
this session's permission classifier on every DB-write wire — apply
`migrations/dt_rubric_v6_seed.sql` manually (idempotent, guarded); live grading uses v5
descriptors until then (same scoring keys).

**Completed 2026-07-16:** **TASK-649** (wiki hygiene lint pass — no code touched. Flipped stale
`status: planned` frontmatter: `evidence-first-grading.md`/`.tech.md` → `in-progress`,
`translation-grading-cascade.md`/`.tech.md` → `complete` (v1 is shipped; prose counterpart flipped
too so it doesn't disagree with its tech page). Reconciled TASK-625's completion date to **2026-07-06**
across the tasklist ↔ `log.md` ↔ tech-spec §11 (the tasklist's 07-07 was the lone outlier; git
inconclusive — the work is uncommitted). Registered the `wiki/evaluations/` category in CLAUDE.md
§2/§8. `dt-grading-baseline-2026-07-05.md` was already linked from `index.md`.)

**Completed 2026-07-16 (cont.):** **TASK-644** (the eval-harness resume checkpoint in
`scripts/run_dt_grading_eval.py` no longer rewrites the whole records+skipped payload as indented
JSON after every item — O(n²) I/O over a run, worst late between paid calls. `_save_checkpoint` now
appends one `{"type","data"}` envelope per completed item (O(1), flush+fsync each), `_load_checkpoint`
streams the JSONL and skips a torn trailing line, and a legacy whole-file sidecar is migrated to JSONL
in place on first load. A torn newline-less final line was found to glue the next append onto it and
lose that item, so an append after a torn tail now leads with a newline. 20 tests green; a simulated
`--resume` after interrupt recovers the same done-ids).

**Completed 2026-07-16 (cont.):** **TASK-643** (the forced Tier-2 re-check — the `mismatch_ratio >
LARGE_DIFF_RATIO` branch, where the re-check is unconditional and its inputs are fixed before
Tier-1 returns — now issues the two multi-second model calls concurrently via a request-scoped
`ThreadPoolExecutor`, merging byte-identically to the sequential path; the confidence-gated
re-check stays sequential since its `extra_dims` depend on Tier-1's output. `_CallRecorder.append`
is lock-guarded. Two tests added: a barrier proving overlap on the forced path, an in-flight
tracker proving none on the confidence path).

**Completed 2026-07-16 (cont.):** **TASK-641** (the gold set's band derivation no longer hardcodes
the severity weights TASK-627 will seed: `derive_bands` now requires an explicit source — the live
rubric config, or `offline=True` for the pinned `OFFLINE_SCORING_CONFIG` the fixtures were frozen
under — and a pre-627 config raises rather than silently degrading to constants that may no longer
match the grader. Correction landed: TASK-641 and the v4 seed header call the keys
`severity_weights`/`thresholds`, but TASK-627's AC declares `severity_weights` +
`understandability_weights` + `band_thresholds`; followed TASK-627, since reading keys nobody seeds
would be dead on arrival. `severity_v1` is now optional residue. The helper had **zero** tests
despite the AC citing "existing gold-seed tests" — 18 written, incl. the pinning test and a guard
that fires if a v5 seed lands under renamed keys, which would otherwise leave that pinning test
skipping forever in silence).

**Completed 2026-07-16:** **TASK-639** (severity→style/label mapping centralised behind one
`SEVERITY_META` map in `static/js/dual_translation.js`; legacy `global`/`local` severities now fold
onto the triad before lookup, so an un-backfilled row renders styled and localised instead of
falling through to a raw English label in zh/ja) and **TASK-640** (the TASK-622 regression gate's
own drift risks closed: `eval_metrics.DIMENSIONS` and `SEVERITY_TRIAD_ORDER` are now pinned by
test to `tier0.RUBRIC_DIMENSIONS` / `prompts.SEVERITY_ENUM`, `aggregate_metrics` defaults to the
triad with V1 retained as an explicit baseline opt-in, and one shared `_match_score` helper
replaces the duplicated span match-score formula. The V1 default was latent — the only production
caller already passed the triad — so no shipped baseline number was affected. 35 metric tests
green).

**Completed 2026-07-15:** **TASK-636** (rubric v4 seed made self-contained + downgrade/post-condition
guards) and **TASK-637** (JA exemplar's retired `particle` slug -> `particle_wa_ga`; exemplar
severity moved to `severity_slug`; `_exemplar_text` now drops-and-logs instead of falling back to
subtype 0). The pair produced [[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]] — the
fourth instance of one recurring class, not a one-off. 436 DT tests green. The JA slug rot **was
live** — production JA prompts had been mislabelling a は/が swap as `omission`; the seed was
applied to Supabase the same day and verified. See the 2026-07-15 incident entry in [[log]].

**Completed 2026-07-14:** **TASK-610** (Dual Translation error synthesis) — mistake gate +
deterministic subtype clustering + recurrence promotion. Pure logic in
`services/dual_translation/synthesis.py`, nightly runner `scripts/dt_nightly_synthesis.py`,
20 unit tests (`tests/test_dual_translation_synthesis.py`) all green. No embeddings/LLM —
clustering is a plain `(user, l1↔l2 pair, subtype)` group-by. Live nightly run pending real
`dt_error_instance` volume (feature freshly live; profile table still ~0 rows). Unblocks
TASK-611 (dashboard) and TASK-613 (card generation).

**Also completed 2026-07-14:** **TASK-611** (Dual Translation error-profile dashboard) —
`GET /api/dual-translation/profile` + `/dual-translation/profile` page, ranked by
`severity_rank` with per-subtype trend. UI shows never the raw score, only status
(watching/queued/drilling/resolved) and a shrinking-profile framing. See
[[tasklist/archive/dual-translation.tasks]] for full notes.

**Also completed 2026-07-14:** **TASK-613** (Dual Translation card generation) — pure
`services/dual_translation/cards.py` builds cloze + isolate-and-re-translate `dt_card`
payloads from a `dt_error_instance` record, always toward `corrected_form` (`learner_form`
never appears in the payload at all). Cards scope to the sentence containing the error, not
the whole passage. 8 unit tests (`tests/test_dual_translation_cards.py`) all green; no DB/FSRS
wiring yet (TASK-614). Unblocks TASK-614.

**Also completed 2026-07-14:** **TASK-614** (Dual Translation FSRS scheduling + interleaving +
review endpoints) — `services/dual_translation/cards.py` gained
`generate_cards_for_queued_entries` (materialises `dt_card` rows from promoted
`dt_error_profile_entry` clusters, `queued` → `drilling`) and the pure `interleave_by_subtype`
round-robin. `routes/dual_translation.py` reuses `services/vocabulary/fsrs.py`'s
`CardState`/`schedule_review` as-is for the new `GET /cards/due` and
`POST /cards/<id>/review` endpoints, and `GET /next` now probabilistically interleaves due
error cards (~1-in-4, env-tunable) alongside passages, tagging responses with a `type` field
(`'passage'` | `'error_card'`). 26 new unit tests; full suite green (927 passed / 1 skipped).
Frontend rendering of `error_card` responses is not wired yet (left for TASK-618). Unblocks
TASK-615 and TASK-618.

**Also completed 2026-07-14:** **TASK-615** (Dual Translation recurrence-reduction
instrumentation) — pure `services/dual_translation/metrics.py` turns already-joined
`dt_card_review` rows (`card_id`/`subtype`/`was_correct`/`reviewed_at`) into a per-subtype
recurrence-rate curve keyed by review-cycle number (1st review, 2nd review, ... per card, not
calendar time), and flags any subtype whose recurrence hasn't dropped below its cycle-1
baseline by cycle 3–4 (`not_improving`) vs `improving` vs `insufficient_data` (fewer than 3
cycles observed — never flagged early). `dt_card_review.was_correct` logging itself was already
wired by TASK-614's `submit_card_review`; this task only adds the metric computation. 8 unit
tests (`tests/test_dual_translation_metrics.py`), including a seeded-improving fixture asserting
monotonically decreasing recurrence and a seeded-stalled fixture asserting the flag fires; full
suite green (356 dual-translation tests passed). Not yet wired into a dashboard endpoint/route —
that consumption step (analogous to TASK-611 reading `synthesis.py`'s output) is a future task,
out of scope per this task's own Files list.

**Also completed 2026-07-14:** **TASK-618** (Inject error exercises into Practice Engine sessions)
— `services/dual_translation/cards.py` gained `select_error_exercises_for_practice`, which
materialises due cards (idempotent), fetches due `dt_card` rows **scoped to the session's L2**
(`dt_card` has no language column, so scope resolves through
`profile_entry_id → dt_error_profile_entry.l2_language_id` — a JA practice session never surfaces
a ZH card), interleaves them by subtype, and caps the count at
`min(MAX, ceil(FRACTION × normal_items))` (env knobs `DT_PRACTICE_ERROR_CARD_MAX`=3,
`DT_PRACTICE_ERROR_CARD_FRACTION`=0.34, matching the `DT_ERROR_CARD_INTERLEAVE_EVERY` env
convention). `services/practice_session_service.py`'s `get_session` now spreads those
**non-sense-linked** items evenly through the RPC's normal items via a new `_interleave_extras`
helper — best-effort (a remediation hiccup never breaks the session) and only into a *non-empty*
session (an empty practice session stays empty; `GET /next` remains the surface for a due queue
with no accompanying practice). The legacy `get_or_create_daily_session` shape and the v1
practice player (`static/js/session/players/practice.js`) both **skip** `is_error_exercise` items
the same way they skip gate/stress markers — the error-card *renderer* in the practice player is
the tracked follow-up (the cards still ride in the payload so that follow-up and API-level
verification see them). 12 new unit tests (`tests/test_practice_error_card_injection.py`,
`tests/test_dual_translation_cards.py`); full suite green (951 passed / 1 skipped, no regressions).

## Recently confirmed complete (this audit, 2026-07-13)

Verified via codebase inspection + live Supabase `list_tables` check — not previously marked done:

- **Practice Engine Merger — TASK-101–110, TASK-112** (11 of 12 tasks). `dim_exercise_types`,
  `dim_practice_modes`, `practice_unified_score`, `get_practice_session` (both modes), `auto`
  dispatch, `/api/practice/session` + `/attempt` routes, deprecation wrappers, and the nightly
  `_refresh_exercise_time_estimates` cron are all live. **TASK-111** (parity tests) was the last
  open item — now closed as **Won't Do / obsolete** (see below). The epic is complete.
- **Study Plans — TASK-201–219** (19 of 20 tasks). All `phase13_*` migrations applied and
  confirmed live (`user_study_plans`, `weekly_plan_states`, `dim_study_plan_templates`, etc. all
  populated); `services/study_plan_service.py`, `routes/study_plan.py`, the
  `study_plan_weekly_recompute` cron, and `Config.STUDY_PLAN_ENABLED` (defaults `True`) are all
  wired. **TASK-220** (deprecation cleanup) closed 2026-07-14 — the epic is complete.
- **Dual Translation — TASK-609** (`dt_error_profile_entry` migration). Confirmed applied live
  (table exists with correct schema, 0 rows pending the TASK-610 pipeline that populates it).

Full detail for these tasks lives in `archive/practice-merger.tasks.md`,
`archive/study-plans.tasks.md`, and `archive/dual-translation.tasks.md` (each carries an audit
banner at the top).

**Security note (incidental finding, not a task list item):** the live Supabase advisor flagged
41 tables — including all `dt_*` tables — with Row Level Security **disabled**, exposing them to
the anon/authenticated Supabase client keys. This was not remediated (enabling RLS without
policies would break access); flagging here for the user to decide on a fix and policies.

## All Tasks

### Practice Engine Merger — COMPLETE
Full spec: [[tasklist/archive/practice-merger.tasks]]. Implements [[decisions/ADR-007-merge-exercises-vocab-dojo]]. Feature is live in production. No open tasks remain.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-111 | practice-engine | Parity tests — Jaccard ≥ 0.70 | ~~[ ]~~ Won't Do (obsolete) | M | TASK-110 (done) |

**TASK-111 closed 2026-07-13 as obsolete — not implemented.** The parity test was designed as a
*pre-cutover* safety net: run the old independent `get_ladder_session` / `get_exercise_session`
implementations against the new `get_practice_session` and prove Jaccard ≥ 0.70 before
decommissioning the old ones. That window closed on 2026-05-21 when TASK-110
(`phase12_deprecation_wrappers.sql`) replaced both legacy RPC bodies with **thin wrappers that call
`get_practice_session` internally**. There is no longer an independent old implementation to diff
against — the test would compare `get_practice_session` to a wrapper of itself (Jaccard ≈ 1.0 by
construction), yielding false confidence rather than real coverage. It also can't run in CI (the
pytest harness fully mocks Supabase; it would need live staging creds). The regression evidence it
was meant to produce has been supplied by ~2 months of production traffic without rollback.
Resurrecting the pre-merger RPC bodies from git history to get a meaningful diff was judged not
worth the effort for a shipped, stable feature.

### Study Plans — COMPLETE
Full spec: [[tasklist/archive/study-plans.tasks]]. Implements [[decisions/ADR-008-study-plan-orchestration-layer]]. Feature is live in production (`STUDY_PLAN_ENABLED=True`). No open tasks remain.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-220 | study-plans | Deprecation cleanup — drop `get_exercise_session`/`get_ladder_session` wrappers, 302 legacy routes | [x] Done (2026-07-14) | M | TASK-219 (done) |

**TASK-220 closed 2026-07-14.** `phase17_drop_deprecation_wrappers.sql` drops both wrapper RPCs (`phase12_deprecation_wrappers.sql` moved to `migrations/archive/`). `/api/exercises/session` and `/api/vocab-dojo/session` now 302 to `/api/practice/session` (`auto` / `acquisition` mode). The last live `get_ladder_session` RPC caller (the vocab-dojo route) and the `get_exercise_session_service` alias + shim were removed; grep of `*.py` is clean. The two standalone pages (`/exercises`, `/vocab-dojo`) were retired (routes, templates, and the Vocab Dojo nav link removed) — the unified `/session` Practice player is the sole live surface.

### Exercise Generation v2
Full spec: [[tasklist/archive/exercise-generation-v2.tasks]]. Implements [[features/exercise-generation-v2]]. TASK-515 (top-1,000 × 3-language batch run) is the integration gate most other rows depend on transitively.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-510 | exercise-generation-v2 | Slug health cron + fail-closed batch judges | [x] | S | TASK-501 |
| TASK-512 | exercise-generation-v2 | Consolidation — ladder is the sole vocab generator | [x] | M | TASK-501 |
| TASK-513 | exercise-generation-v2 | Transcript mining as a P1 sentence source | [x] | M | TASK-512 |
| TASK-514 | exercise-generation-v2 | Robustness: non-destructive regen, P1 retry, matrix-gated L4 | [x] | M | TASK-504 |
| TASK-515 | exercise-generation-v2 | Batch run — top 1,000 senses × EN/ZH/JA | [~] | L | 504–511, 513, 514, 519 |
| TASK-516 | exercise-generation-v2 | Deterministic generators (def-match, jumbled, readings, tone) | [x] | L | 503, 506 |
| TASK-517 | exercise-generation-v2 | Coverage check + batch report + queue drain | [x] Done (2026-08-11) | M | 504, 511 |
| TASK-518 | exercise-generation-v2 | Per-sense legacy exercise dedupe | [x] | S | TASK-515 |
| TASK-519 | exercise-generation-v2 | Multi-nl content rules (`content.nl` keyed maps) | [x] | S | TASK-501 |
| TASK-520 | exercise-generation-v2 | Prompt split — L4 + L8 out of P3 monolith | [x] Done (2026-08-11) | M | TASK-515 |
| TASK-521 | exercise-generation-v2 | Sense embeddings (pgvector) | [~] | M | TASK-501 |
| TASK-522 | exercise-generation-v2 | `synonym_antonym_match` + `word_family` generators | [x] Done (2026-08-11) | L | 504, 521 |
| TASK-523 | exercise-generation-v2 | Collocation grounding for L5/L8 | [x] Done (2026-08-11) | M | TASK-515 |
| TASK-524 | exercise-generation-v2 | Sentence-tier hard gate | [x] | S | TASK-513 |
| TASK-525 | exercise-generation-v2 | tl_nl uniqueness judge | [x] Done (2026-08-11) | S | TASK-501 |
| TASK-526 | exercise-generation-v2 | Traditional-script serve toggle (practice surfaces) | [~] | M | 509, 515 |
| TASK-527 | exercise-generation-v2 | JA `particle_selection` generator + judge | [x] Done (2026-08-11) | M | 508, 515 |
| TASK-528 | exercise-generation-v2 | ZH `classifier_match` as ladder L4 | [x] | M | TASK-504 |
| TASK-529 | exercise-generation-v2 | `reading_to_kanji` / `pinyin_to_hanzi` + component table | [x] Done (2026-08-11) | M | TASK-516 |
| TASK-530 | exercise-generation-v2 | JA counter drill (助数詞) + `counter_match` | [~] | L | TASK-504 |
| TASK-531 | exercise-generation-v2 | Audio at scale (L1 + listening) | [~] | M | TASK-515 |
| TASK-532 | exercise-generation-v2 | `cloze_typed` free input (normalised match) | [x] Done (2026-08-11) | M | TASK-515 |
| TASK-533 | exercise-generation-v2 | `timed_speed_round` serve-time composer | [x] Done (2026-08-11) | M | TASK-515 |
| TASK-534 | exercise-generation-v2 | Exercise-type effectiveness view | [?] | M | 515 + launch data |
| TASK-535 | exercise-generation-v2 | Thompson-sampling type tie-breaker | [?] | L | TASK-534 |
| TASK-536 | exercise-generation-v2 | Per-user format prefs + item retirement | [?] | M | TASK-534 |
(TASK-537–540, the ladder numeric-key output contract, closed 2026-08-11 — see the
note under Summary. Removed from this table per the "incomplete work only" rule above;
full record in [[tasklist/ladder-numeric-keys.tasks]].)

### Dual Translation
Full spec: [[tasklist/archive/dual-translation.tasks]]. Implements [[features/dual-translation]]. Stage 1 (grading MVP) and Stage 4 (localisation) are done; remaining work is Stage 2 (error synthesis) and Stage 3 (spaced remediation).

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-601 | dual-translation | Budget guardrail + cost dashboard hooks | [x] | S | TASK-600 (done) |
| TASK-610 | dual-translation | Mistake gate + deterministic subtype clustering + promotion | [x] | L | TASK-609 (done) |
| TASK-611 | dual-translation | Error-profile dashboard endpoint + UI | [x] Done (2026-07-14) | M | TASK-610 (done) |
| TASK-612 | dual-translation | Migration — `dt_card`, `dt_card_review` | [x] | S | TASK-609 (done) |
| TASK-614 | dual-translation | FSRS scheduling (reuse) + interleaving + review endpoints | [x] Done (2026-07-14) | M | TASK-613 (done) |
| TASK-615 | dual-translation | Recurrence-reduction instrumentation | [x] Done (2026-07-14) | S | TASK-614 (done) |
| TASK-618 | dual-translation | Inject error exercises into Practice Engine sessions (non-sense-linked) | [x] Done (2026-07-14) | M | TASK-614 (done) |

### Evidence-First Grading (Dual Translation v2)
Full spec: [[tasklist/archive/evidence-first-grading.tasks]]. Implements [[algorithms/evidence-first-grading.tech]] per [[decisions/ADR-019-evidence-first-scoring]]. TASK-633–649 are a code-review hardening batch (filed 2026-07-13) on the TASK-624/625/626 work — recommended **before** TASK-627 continues, since TASK-640/641 fix integrity bugs in the TASK-622 regression gate itself. Both are now done (2026-07-16); TASK-641 leaves a hand-off note on TASK-627 pinning the rubric-v5 scoring key names + values. **The whole batch is closed as of 2026-08-10** — the last five rows (638/642/645/647/648) were a status reconciliation, not new code. TASK-629's owed live apply also landed that day, so the feature has **no open rows**.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-638 | evidence-first-grading | Fix empty-correction dangling explanation text | [x] Done (2026-08-10) | XS | — |
| TASK-642 | evidence-first-grading | Cache active rubric/taxonomy config on grading hot path | [x] Done (2026-08-10) | S | — |
| TASK-645 | evidence-first-grading | Remove dead re-normalization in tier-0 full-marks gate | [x] Done (2026-08-10) | XS | — |
| TASK-646 | evidence-first-grading | Migration-authoring guidance: lock hold time on backfills | [x] Done (2026-07-16) | XS | — |
| TASK-647 | evidence-first-grading | Replace hand-rolled eval retry loop with tenacity | [x] Done (2026-08-10) | S | — |
| TASK-648 | evidence-first-grading | Delete stale severity comment + dead parameters | [x] Done (2026-08-10) | XS | — |
| TASK-649 | evidence-first-grading | Wiki hygiene — status frontmatter, dates, evaluations category | [x] Done (2026-07-16) | XS | — |
| TASK-628 | evidence-first-grading | Detector/Verifier cascade restructure | [x] | XL | TASK-627 (done) |
| TASK-629 | evidence-first-grading | Band descriptors v3 rewrite | [x] Done (2026-08-10) | L | TASK-627 (done) |
| TASK-630 | evidence-first-grading | Explainer pass — instance Application layer | [x] | M | TASK-628 |
| TASK-631 | evidence-first-grading | Result UI v2 — highlights, "because" lines, next focus | [x] | L | TASK-630 |
| TASK-632 | evidence-first-grading | Final eval + wiki reconciliation | [x] | S | TASK-631 |

### Daily Session Hardening
Full spec: [[tasklist/archive/daily-session-hardening.tasks]]. Remediates findings F1–F16 from [[algorithms/daily-session-implementation-analysis]]. TASK-700–702 are the scheduling-correctness tier and unblock everything user-visible.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-701 | daily-session-hardening | Real practice timing → weekly minute counters advance | [x] | M | — |
| TASK-702 | daily-session-hardening | Surface + reduce hydration shortfalls | [x] | M | — |
| TASK-703 | daily-session-hardening | Interleave the session queue | [x] | M | TASK-701 |
| TASK-704 | daily-session-hardening | Retry slots in the plan path (ADR-006) | [x] | S | TASK-702 |
| TASK-705 | daily-session-hardening | Make build_daily_session same-day-safe | [x] | S | — |
| TASK-706 | daily-session-hardening | Advisory lock actually guards the weekly cron | [x] | S | — |
| TASK-707 | daily-session-hardening | Legacy fallback correctness (type labels + ELO band) | [x] Done (2026-07-20) | S | — |
| TASK-709 | daily-session-hardening | Runner UX/a11y hardening | [x] Done (2026-08-07) | S | — |
| TASK-710 | daily-session-hardening | Consolidate the duplicated greedy pass | [x] Done (2026-08-07) | S | 702, 704, 705 |
| TASK-711 | daily-session-hardening | Document the plannable-type boundary | [x] Done (2026-08-07) | XS | product decision (taken) |
| TASK-712 | daily-session-hardening | Day-boundary timezone decision | [x] Done (2026-08-07) | XS | product decision (taken) |
| TASK-713 | daily-session-hardening | Wiki truth reconciliation (Phase 13) | [x] Done (2026-08-07) | S | — |
| TASK-714 | daily-session-hardening | `flashcards` + `dual_translation` as plannable surfaces | [x] Done (2026-08-07) | L | TASK-711 (done) |
| TASK-715 | daily-session-hardening | Tier-scaled dictation transcript cap | [x] Done (2026-08-07) | M | TASK-711 (done) |
| TASK-716 | daily-session-hardening | Local-day boundary via plan timezone | [x] Done (2026-08-07) | L | TASK-712 (done) |

**The Daily Session Hardening feature (TASK-700–716) is now fully closed.** TASK-701's owed
live verification was closed 2026-08-07 via a rollback-only DB check (24 × 25 s attempts →
`practice_completed_acq_sec 0 → 600`, `_min 0 → 10`). TASK-711 and TASK-712 were unblocked by user
decisions on 2026-08-07, producing [[decisions/ADR-021-plannable-surface-boundary]] and
[[decisions/ADR-022-local-day-boundary]]; **TASK-714/715/716 were the implementation work those
decisions generated** and landed the same day — applied live and verified against the DB. See
[[tasklist/archive/daily-session-hardening.tasks]] for per-criterion evidence.

### Distractor Judge Calibration

Full spec: [[tasklist/distractor-judge-calibration.tasks]]. Remediates
[[evaluations/distractor-judge-language-divergence-2026-08-16]] — the v4 Likert distractor judge
rejects 30% of zh questions vs 4% of en, and its review-queue channel fires only in English.
TASK-717 is the entry point and is correct regardless of every downstream outcome.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-717 | comprehension-tests | Make the judge's dead prompt slots load-bearing (`keywords`, `type_code`) | [~] | M | — |
| TASK-718 | comprehension-tests | Cross-model judge A/B — judge harshness vs content quality | [x] Done (2026-08-16) | S | TASK-717 (partial — not blocking) |
| TASK-719 | comprehension-tests | Split the rating onto two axes (topical fit / confusability) | [x] Done (2026-08-20) — v7 rows staged, inactive | M | TASK-718 |
| TASK-720 | comprehension-tests | Redefine the review band as explicit uncertainty | [x] Done (2026-08-20) — shipped with TASK-719 | S | TASK-719 |
| TASK-721 | comprehension-tests | Give the 18 generator prompts a distractor specification | [ ] | M | TASK-717 |
| TASK-722 | comprehension-tests | Rewrite the zh/ja `vocabulary_context` prompts natively | [ ] | M | — |
| TASK-726 | comprehension-tests | Build the distractor-plausibility gold set | [~] | M | none — this is the blocker |

**Sequencing revised 2026-08-16 by the TASK-718 result.** The zh divergence was the judge, not the
content: swapping zh/ja to `gemini-3.1-flash-lite` takes zh from **32% → 2%**, and under a common
judge zh is the *cleanest* of the three languages (zh 2%, en 4%, ja 6%). Applied live.

But the same run showed the two judges' reject sets are **disjoint** — across 150 questions they
agree on one reject, and all 25 zh distractors qwen rejected were rated 4–5 by gemini. The reject
signal is not merely mis-scaled, it is unvalidated. **A gold set is now the gate on TASK-719 and
TASK-720** and needs a task ID. TASK-721 and TASK-722 depend on none of this and are the best next
work.

The middle band is no longer missing: the model swap alone gives zh and ja band-3 ratings, so
`generation_review_queue` is multilingual without a prompt change. Band 1 has now fired three times
in 1,800 ratings — still rare enough that "the judge does not catch the failure it was built for"
holds in substance.

**Sequencing revised again 2026-08-20 by TASK-719/720.** The axis split was executed ahead of the
gold set on an explicit operator decision, on the ground that the blocker applies to *retuning cut
points* rather than to *asking the judge two questions instead of one*, and the rows are staged so
nothing changes at runtime. The gold set is still the gate — it is now the gate on **activation**
rather than on construction, and the question it has to answer is sharper: is a 22-47% review rate
honest uncertainty or a prompt that made a confident model timid? That question did not exist
before the split; it is the one thing that makes TASK-726 worth finishing. It also learned that
"the judge does not catch also-correct distractors" was **the wrong complaint** — the failure is
simply rare (1/537 on a dedicated axis). TASK-726 remains the best next work, and it is now the
only work between v7 and a rollout decision.

### Test Generation — Fail-Closed Judging (new 2026-08-21)

Full spec: [[tasklist/test-gen-fail-closed-judging.tasks]]. The `batch_mode()` fail-closed guard
(`services/exercise_generation/judges/base.py`, TASK-510) is wired into **exercise** generation
only. Test generation never enters it, so a bulk run with a delisted model slug or a missing
prompt row writes unjudged questions with nothing louder than a log warning — the exact shape of
the two outages the guard was built for. Blocks any large test-generation run.

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-727 | comprehension-tests | Wrap both test-gen batch entry points in `batch_mode()` | [x] Done (2026-08-21) | S | — |
| TASK-728 | comprehension-tests | Audit the orchestrator's 15 handlers so `JudgeUnavailable` propagates | [x] Done (2026-08-21) | M | TASK-727 |
| TASK-729 | comprehension-tests | Prove the guard actually fires (batch aborts, writes nothing) | [x] Done (2026-08-21) | M | TASK-728 |
| TASK-730 | comprehension-tests | Measure a 20-test run — cost and wall clock | [x] Done (2026-08-21) | S | TASK-729 |

**All four done 2026-08-21 — the guard is live in test generation and the 20-test number is
measured.** `run()`/`run_batch()` now execute inside `batch_mode()`, five judge-path
`except Exception` handlers re-raise `JudgeUnavailable`, and 14 tests pin it — including the
check that the suite goes **red** when either half of the fix is reverted (handlers removed:
3 end-to-end tests fail; `batch_mode` wrap removed: 4 fail). Thread fan-out: audited, none
exists in `services/test_generation/`, so no `BatchModeThreadPoolExecutor` was needed — but
that is now the assumption a future parallelisation would silently break. Suite 1869 →
**1883 passed, 3 skipped**.

**Measured run: 20/20 tests, $0.175 ($0.00875/test), 3,532 s (2.9 min/test).** Spend is a
non-issue at any plausible scale (~$8.75 per 1,000 tests); wall clock is the constraint
(~49 h per 1,000), and **82% of it is vocabulary enrichment for 16% of the spend**. Judges
are 38.2% of spend and rejected 2 questions in 163 calls. See
[[evaluations/test-gen-20-run-2026-08-21]].

TASK-728 is the substance, not TASK-727: `JudgeUnavailable` is an ordinary exception and five
`except Exception` blocks sit on the judge path, where they would degrade a loud abort into "that
one test quietly failed" — quieter than the bug it replaces. TASK-729 exists because four
guardrails in this codebase were silently inert for months (the exercise-gen v2 batch: NULL
`cost_usd` disarming every budget ceiling, a band-check RPC signature that never existed, an
`asset_type` CHECK rejecting all typed-LLM assets, a per-type audio-field mismatch); a happy-path
test is not evidence that a guard fires.

### Language Packs (existing — unchanged)

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| — | language-packs | (all tasks blocked) | [?] | — | Design resolution needed |

See [[tasklist/archive/language-packs.tasks]] and [[features/language-packs.tech]] `open_questions` for blockers.

## Fully complete (archived, nothing remaining)

- **Ladder Judge Layer** (TASK-401–416) — all 16 tasks done 2026-06-07–09. See [[tasklist/archive/ladder-judge-layer.tasks]].

## Notes

The Practice Engine merger and Study Plans are both live in production (only their respective
cleanup/test tasks remain open) — the old sequencing note ("ship 101–112 before starting
TASK-201") is no longer operative and has been removed.

Evidence-First Grading's hardening batch (TASK-633–649) was filed 2026-07-13 and is now **fully
closed** (last five reconciled 2026-07-16 … 2026-08-10). Its original sequencing note ("triage
before resuming TASK-627") is spent — TASK-627 and the whole TASK-628/630/631/632 v2 stack shipped
2026-07-18/19. **TASK-629 closed 2026-08-10**: `migrations/dt_rubric_v6_seed.sql` was applied live
via Supabase MCP, so grading now serves v6 band descriptors rather than v5. Evidence-First Grading
has no open rows.
