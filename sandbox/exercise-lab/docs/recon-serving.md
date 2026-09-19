# Recon: How exercises/tests are selected and served — LinguaLoop WebApp
Read-only recon, 2026-09-17. All claims cite file:line. "LIVE" = stated in a migration's own applied-live header or in wiki/log.md; DB was never queried directly per instructions.

---

## 0. Headline (read this first)

**`vocab_weight` is now LIVE = 1, as of TODAY (2026-09-17).** This directly updates stale project memory that said "vocab-aware selection live but OFF." Per `wiki/log.md:3-31` (uncommitted addition, "Vocabulary-aware selection SWITCHED ON (`vocab_weight` 0 → 1)"): an operator ran `UPDATE selection_tuning SET value = 1 WHERE key = 'vocab_weight';` by hand (the agent's own permission guard blocked it), verified only behaviourally (0 unlinked zh tests served where 7-9/10 were before; `elo_diff` non-monotonic in 6/8 lists; pool size (M5) intact at 10/type; latency 5-14ms → 25-69ms). `combine_mode` stays `'sum'` — the multiplicative arm (`migrations/task780_selection_combine_mode.sql`, itself **uncommitted in git** but its own header claims **applied live 2026-09-16**) was measured and rejected (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md`).

Also note: `wiki/tasklist/master.md:50-52` (same day) still says "vocab_weight is left to the operator" — written before the flip landed later that day. Wiki is one entry behind the actual live state as of this recon.

---

## 1. The selection chain

```
Client
  └─ GET /api/study-session/... or dashboard load
       └─ services/test_service.py:455 get_or_create_daily_load(user_id, language_id)
            ├─ if today's row exists in daily_test_loads → return it (services/test_service.py:483-491)
            ├─ elif Config.STUDY_PLAN_ENABLED and user has a study plan (test_service.py:496):
            │     services/study_plan_service.py:525 StudyPlanService.build_daily_session()
            │       → RPC public.build_daily_session(user, lang, date)
            │            canonical def: migrations/word_upload_slot_scheduling.sql:116-...
            │            (supersedes migrations/archive/task732_build_daily_session_split_budget.sql)
            │            on E_NOWEEK: services/study_plan_service.py compute_weekly_plan() then retry
            │            (test_service.py:508-532)
            └─ else / on E_NOPLAN|E_NOWEEK|E_RPC: legacy fallback
                  services/test_service.py:~660-720 _compute_daily_load()
                    - up to 2 'retry' slots from the worst sub-70% attempts (test_service.py:690-707)
                    - remaining slots via RPC get_recommended_tests(user, lang) (test_service.py:712-715)

Inside build_daily_session (word_upload_slot_scheduling.sql):
  1. Greedy budget pass over test/surface/maint/acq candidates (objective function, §2 below)
  2. TASK-705 same-day carry-over of already-completed slots (lines 438-477)
  3. TASK-704/ADR-006 'retry' slot: ≤1/day, worst sub-70% attempt >24h old (lines 488-522)
  4. 'word_upload' slot: ≤1/day, most-recent unattempted watchlist match (lines 563-622)
  5. Hydration per skill (lines 630-670):
       classifier_drill → sentinel row per language
       else            → get_recommended_tests(user, lang)  [never-attempted, ELO-ranked]
                          shortfall topped up by get_replay_tests(user, lang, skill, min_age=7, exclude, n)
                          (slot_type='replay')
  6. Surface slots (flashcards, dual_translation) hydrated against their own live pools (674-740)
  7. requested/hydrated/replay/surface counts written to daily_session_targets;
     shortfalls logged as WARNING by services/test_service.py:582-620 _log_hydration_shortfalls

Submission:
  routes/tests.py:689-718 → RPC process_test_submission(...)
       canonical def: migrations/sec_submission_rpcs_auth_gate.sql:45-...
       (body = migrations/archive/task704_process_test_submission_retry_elo.sql VERBATIM + new auth gate)
       - first attempt: full-K ELO update
       - repeat attempt IN today's retry slot, not already earned today: ADR-006 damped ELO
       - repeat attempt otherwise: 0 ELO (status quo)
```

**Direct/legacy RPC endpoint:** `routes/tests.py:117-127` also exposes `get_recommended_tests` directly via `current_app.supabase_service.rpc('get_recommended_tests', ...)` — a second, simpler serving path outside `build_daily_session`.

### Live vs. repo drift (verified from migrations/wiki only, no DB query)

| Object | Canonical file (newest non-archive) | Signature | Note |
|---|---|---|---|
| `get_recommended_tests` | `migrations/task748_get_recommended_tests_vocab_aware.sql:435` | **3-arg**: `(p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint DEFAULT 14)` | Confirms memory: live is 3-arg, not the 2-arg archived shape. `migrations/get_recommended_tests_drop_ambiguous_overload.sql` exists specifically because a defaulted-parameter overload once broke PostgREST resolution — no new overload may ever be added. |
| `recommended_tests_ranked` (helper, service-role only) | **`migrations/task780_selection_combine_mode.sql:147`** (uncommitted in git, `??` in `git status`, but its own header claims **APPLIED LIVE 2026-09-16**) — supersedes the same-named function in `task748_get_recommended_tests_vocab_aware.sql:194` (kept, not archived, because it's still the sole repo record of `selection_vocab_ability` and of `get_recommended_tests` itself — `migrations/CLAUDE.md` rule 4) | | |
| `build_daily_session` | `migrations/word_upload_slot_scheduling.sql:116` (committed 2026-09-06) | `(p_user_id, p_language_id, p_date DEFAULT CURRENT_DATE)` | supersedes `migrations/archive/task732_build_daily_session_split_budget.sql` |
| `get_replay_tests` | `migrations/get_replay_tests.sql:28` (only non-archive def) | | TASK-702, shared with TASK-704 retry |
| `process_test_submission` | `migrations/sec_submission_rpcs_auth_gate.sql:45` (2026-09-12) | 8-arg incl. `p_furigana_used` | **Confirms memory: live ≠ repo phase14.** `migrations/archive/phase14_test_kfactor_decay.sql` (CR-04 hardening: typed error envelope, `jsonb_to_recordset`, masked `SQLERRM`) **was never applied**; the file's own comment says so (`migrations/partF_question_attempt_results.sql:18-24`, `migrations/partG_qar_drop_response_time.sql:16-19`). Canonical body descends from `migrations/archive/task704_process_test_submission_retry_elo.sql` verbatim. |
| `selection_tuning` | table: `migrations/task744_selection_tuning_table.sql` + `migrations/task780_selection_combine_mode.sql:112-140` (adds `value_text`/`combine_mode`) | | service_role-only; RLS on, no policy |

---

## 2. The objective function (exact, as of `task780_selection_combine_mode.sql`, which is what's live)

### `get_recommended_tests(p_user_id, p_language_id, p_topic_recency_days=14)`

```
v_vocab_weight = COALESCE(selection_tuning.vocab_weight, 0)   -- LIVE VALUE = 1 (see §0)

IF v_vocab_weight > 0:
    RETURN recommended_tests_ranked(...) WHERE rank_in_type <= 10
           ORDER BY score, elo_diff, test_id
ELSE:
    RETURN the pre-TASK-748 query VERBATIM (ABS(test_elo - user_elo) ranking only)
```
(`migrations/task748_get_recommended_tests_vocab_aware.sql:435-465`)

### `recommended_tests_ranked` — the scorer (`migrations/task780_selection_combine_mode.sql:147-391`)

For each candidate test `t` of type `τ` for user `u`:

```
e(t) = elo_weight · |test_elo(t) − user_elo(u, τ)| / 400
v(t) = vocab_weight · |unknown(t) − u*| / u_tol        (NULL/neutral handling below)

score(t) = e(t) + v(t)                    if combine_mode = 'sum'   [LIVE — default, unchanged]
         = (1 + e(t)) · (1 + v(t))        if combine_mode = 'product'
         = 1 + e(t) + v(t) + e(t)·v(t)                                [algebraically]
```
- `elo_weight = 1.0`, `unknown_target (u*) = 0.15`, `unknown_tolerance (u_tol) = 0.10`, `tier_ceiling_offset = 2`, `vocab_weight = 1` (live), `combine_mode = 'sum'` (live) — all from `selection_tuning`, read once per call, missing-row/missing-table always degrades to the inert value (`task748:...:242-247`, `task780:196-205`).
- `unknown(t) = 1 − mean(P_known(s))` over `S'` = distinct senses in `t.vocab_sense_ids` that resolve to a `dim_vocabulary` row with non-null `frequency_rank` (a **Zipf score, higher = more common** — reading it as a rank inverts every ordering, per ADR-024).
- `P_known(s) = user_vocabulary_knowledge.p_known` if a row exists, else the frequency prior:
  `σ(1.5·(zipf(s) − ability_zipf) + ln(0.85/0.15))` — **0.85 at `ability_zipf`, not 0.5** (a deliberate correction to the original ADR-024 spec; `task748:43-50`).
- `ability_zipf`: `user_calibration_state` (mode='definition') if present, **else** the Zipf where the learner's own `user_vocabulary_knowledge` known-share (bucketed 0.5-wide Zipf bands, n≥5, share = P(p_known≥0.6)) crosses 85%, walking down from the commonest band; **never a median of known senses** (`task748:125-179`). Currently `user_calibration_state` has 0 rows live, so every learner runs the `uvk_crossing` path (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md:116-118`: ja 5.025, zh 5.152 for the one active learner).
- **Neutral degradation** (never a filter): a test gets the **median raw penalty of its (user, type) candidate cohort** — not 0, not +∞ — when `vocab_sense_ids` is empty/NULL, or `|S'| < 5`, or `|S'|/|S| < 0.5`, or no `ability_zipf` at all (`task748:63-68,370-384`). Computed on the RAW penalty *before* sum/product combination, so a neutral candidate's penalty is identical in both modes (`task780:335-343`).
- **Tier ceiling (safety rail, never a filter):** if a `mode='definition'` calibration row exists AND `vocab_weight > 0`, candidates more than `tier_ceiling_offset` (2) tiers above the learner's calibrated tier are **demoted to the bottom of the ranking, not excluded** — deliberate deviation from the ADR-024 spec text, to protect the "pool never shrinks" invariant M5 (`task748:70-79,252-259,332-334`). Currently never arms live (no calibration rows).
- **Ranking / dedup:** `ROW_NUMBER() OVER (PARTITION BY test_type ORDER BY over_ceiling, score, elo_diff, test_id)`, `DISTINCT ON (test_id, test_type)` (`task748:393-405` / `task780:363-374`).
- **Filters (hard, unconditional):** `is_active`, tier gating (free-tier always eligible; paid tier only if premium), never-attempted by this user+type, no attempt on same-topic test within `p_topic_recency_days` (14) days, dictation transcripts capped by `dictation_max_words(difficulty)` (`task748:341-368` / same in `task780`).

### Why `combine_mode='product'` is rejected (measured, not theoretical)
`wiki/evaluations/selection-three-arm-replay-2026-09-17.md`: in-band share (5-25% unknown) `sum 0.952` vs `product 0.938`; product better on **0** of 21 attempts, worse on 3; product lets 2-5/10 previously-excluded zh "no vocabulary opinion" tests back into the top-10 because `product = sum + e·v` charges the smallest extra penalty exactly where `e` (ELO miss) is small — the opposite of the intended "penalize missing both axes" effect. Pinned by `tests/sql/test_task780_combine_mode.sql` fixtures (`too_hard` must rank last in both modes — the guard against a bare `e·v` product, which would score a 90%-unknown/perfect-ELO-match test 0 and rank it FIRST).

### `build_daily_session` budgeting objective (separate from the ranker above)
`migrations/word_upload_slot_scheduling.sql:140-158,344-408`: greedy knapsack over per-skill "candidates" (one row per remaining slot up to each skill's target count), ordered by `per_min_value DESC`:
```
per_min_value(skill) = skill_value(skill) / test_time_estimate(skill)
spacing_cost(skill)  = γ(=0.15) · (count of skill in last 3 chosen) / 3
objective += per_min_value·mins − spacing_cost      (test/surface side)
objective += per_min_value·mins                     (maint/acq practice side, no spacing cost)
```
Test/surface and maintenance/acquisition compete for **separate** budgets (`v_test_budget`/`v_practice_budget`, TASK-732 split) so practice never starves against test candidates on value density. `c_alpha_m = c_alpha_a = 0.02` weight maintenance/acquisition practice minutes.

---

## 3. Spaced repetition — there isn't one, in the SRS sense

No forgetting-curve / interval-scheduling SRS exists for tests. What exists instead:

| Mechanism | What it does | Cap |
|---|---|---|
| **`retry` slot** (TASK-704, ADR-006) | Resurfaces the single worst sub-70% attempt older than 24h, every day until it's no longer the worst | ≤1/day/language (`word_upload_slot_scheduling.sql:488-522`) |
| **`replay` slot** (TASK-702) | Fallback when the never-attempted pool (`get_recommended_tests`) can't fill a skill's budgeted slots: nearest-ELO **previously-attempted** tests older than `p_min_age_days` (default 7) | fills the shortfall only, `get_replay_tests.sql:28-96` |
| **Topic recency exclusion** | Any test whose topic was attempted within `p_topic_recency_days` (14 days) is excluded from `get_recommended_tests` candidates | 14-day window, hardcoded default param |
| **`word_upload` slot** | Surfaces a watchlist word match exactly once (tracked via `last_matched_surfaced_at`), never repeated | ≤1/day/language, once ever per match |
| **Flashcards** | `user_flashcards.due_date <= today` — this is the closest thing to real SRS, but it's a **separate surface**, not part of test/exercise selection | — |

**ADR-006 damping** (what "damps" a retry): `factor = LEAST(1.0, clamp(days_since/60, 0.20, 1.0) + (0.25 if improvement≥15pts else 0))`, applied to both user (`32·factor`, times a 0.5 furigana dampener if used) and test (`16·factor`) K-factors (`migrations/sec_submission_rpcs_auth_gate.sql:255-283`, matches ADR-006 text `wiki/decisions/ADR-006-retry-slot-reduced-elo.md:17-30`, except: **the live code does not call `calculate_volatility_multiplier()`** as ADR-006's pseudocode states — that function is dead for `process_test_submission` and is only still called by `process_dictation_submission` per its own comment, `migrations/elo_functions.sql:54-55`). Anti-grind: at most one damped-ELO repeat per test per day (`elo_reduction_factor IS NOT NULL AND created_at::date = CURRENT_DATE` guard).

No dedup/decay exists for **maintenance/acquisition practice** candidates beyond the `spacing_cost` term above, and no cross-session "don't show the same word again for N days" mechanism exists for vocabulary exposure specifically (only for whole *tests*, via topic recency + never-attempted).

---

## 4. Ability estimation

**Model:** per-user, per-language, per-**test-type** ELO in `user_skill_ratings` (default 1200 cold start). Test-side ELO in `test_skill_ratings` (default 1400 cold start).

**Update rule** (`sec_submission_rpcs_auth_gate.sql:210-249`, first attempt):
```
expected = 1 / (1 + 10^((test_elo − user_elo)/400))
user_K   = 32 × (0.5 if furigana_used else 1.0)
test_K   = 48 if test_attempts<20 else 24 if <50 else 16
new_user_elo = round(user_elo + user_K · (pct − expected))
new_test_elo = round(test_elo + test_K · ((1−pct) − (1−expected)))
clamp both to [400, 3000]
```
Repeat attempts: 0 ELO change unless in today's `retry` slot (§3).

**Cold start:** flat 1200/1400, no Bayesian prior, no calibration blend by default — `user_calibration_state` exists (`ADR-024` decision 4: seeds ELO under hard guards — <5 attempts writes directly, ≥5 attempts only on >200pt disagreement, moves ≤min(0.25·diff,150), ≤1/week, never within 1h of an attempt, clamped [875,1925], every decision logged to `user_skill_rating_adjustments`) but **has 0 rows live** (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md:117`), so this guard rail has never fired for a real user yet.

**Verified: the 191-point MC chance-floor cap and the 48/60 ja claim.** Both are quoted, sourced findings from `wiki/decisions/ADR-024-vocabulary-aware-test-selection.md:19-36`:
> "48 of 60 Japanese tests carry an identical ELO across all 8 test types, because TASK-732 seeded from prose complexity, which cannot know whether the task is reading, dictation or pitch accent." … "The Elo equilibrium gap is `400·log₁₀(1/s − 1)`, which at a 25% floor is **−191 points**." … learner's true ability spans 448 points (pitch accent ~1091, dictation ~1539) inside an assigned 88-point band (1182-1270); reading/listening/dictation under-rated, only pitch accent over-rated, so **ja is mostly too easy**, not too hard, despite pitch accent "feeling" broken (6/7 attempts <50%).

This is why ADR-024 deliberately does **not** try to fix the gap by raising K (`ADR-024:136-138`: "Raise the ELO K-factor so ratings converge faster. Rejected: it cannot work... a larger K only adds variance to a fixed point that is in the wrong place") and instead adds the independent vocabulary term (§2).

---

## 5. Inputs available at serve time but currently unused by the selector

| Signal | Table/column | Status |
|---|---|---|
| Per-question outcome (correct/incorrect, selected vs. correct answer) | `question_attempt_results` (`migrations/partF_question_attempt_results.sql`) | Captured every submission, used only for **distractor pick-rate calibration / mis-key detection** — never read by `get_recommended_tests`/`build_daily_session`. |
| Per-question **response latency** | `question_attempt_results.response_time_ms` | **Deliberately deleted**: `migrations/partG_qar_drop_response_time.sql:1-20` — comprehension tests are answered in any order, so per-question timing was judged meaningless; only whole-attempt `started_at`/`finished_at` survives (`phase13_apply_attempt_timing_and_progress.sql`), and even that isn't a selection input today. |
| Per-sense mastery (BKT `p_known`) | `user_vocabulary_knowledge` | Used **only** inside the vocabulary term's `unknown(t)` average — never as a standalone "pick words this user is 40-60% on" targeting signal, and never per-occurrence (TASK-780 explicitly rejected per-occurrence counting via `vocab_token_map`, `task780_selection_combine_mode.sql:39-45`). |
| Sense-level exposure count / recency | `vocab_token_map`, `user_vocabulary_knowledge.created_at` | `created_at` is read only to support the `p_as_of` replay reconstruction (§7) — not used to space out repeat exposure of the same word across tests. |
| Error-type taxonomy (DT error cards) | `dt_error_instance` (per memory: `webapp-dt-*` notes) | Entirely outside test selection — DT (dual translation) has its own remediation/practice-injection loop, disjoint from `get_recommended_tests`/`build_daily_session`. |
| Sentence-level readability / vocabulary coverage of the **passage itself** | `tests.transcript`, `tests.vocab_sense_ids` | `vocab_sense_ids` coverage feeds the vocabulary term, but only as an aggregate `unknown share` — no readability formula, sentence length, or grammar-complexity signal is used; `tests.difficulty` (1-9, legacy axis) and `target_age_tier` (TASK-740, the new sole axis for generation) are **not** used as filters in selection, only ELO is compared and difficulty determines `dictation_max_words` and `test_time_estimate`. |
| Furigana usage | `test_attempts` (via `p_furigana_used`) | Used only as an ELO K-factor dampener at submission time, not as a selection input. |
| Calibration state | `user_calibration_state` | Feeds `ability_zipf` and the tier-ceiling rail when present — currently 0 rows live, so unused in practice. |

---

## 6. Known documented defects in serving

1. **Resolver hydration shortfalls (TASK-702/704/705/710).** `build_daily_session` could silently drop budgeted slots when `get_recommended_tests`'s never-attempted pool was exhausted for a skill — fixed by adding `get_replay_tests` fallback (TASK-702), then made visible via requested/hydrated/replay/surface count logging + a WARNING in `services/test_service.py:582-620` (`_log_hydration_shortfalls`). TASK-705 made the RPC same-day-safe (carries over completed slots instead of wiping `completed_test_ids`). TASK-710 collapsed a duplicated greedy pass into one loop (proven output-identical on a 20-scenario fixture matrix).
2. **48/60 ja tests share one ELO across all 8 test types** (TASK-732 seeded from prose complexity, not per-type) — `ADR-024` §Context point 1. Root cause of "ja tests too hard/easy" symptom; **not yet fixed** — `ADR-024`'s "Known limit, stated up front" says selection cannot repair this on its own; needs a per-type ELO reseed (TASK-751, proposed-only, blocked: "no (language, type) has more than 8 first attempts" per `wiki/log.md` 2026-09-10 entry).
3. **ELO's chance floor caps reachable ability spread at ~191 points** regardless of K-factor — structural, not fixable by tuning (`ADR-024`).
4. **17-22% of en/zh tests carry no `vocab_sense_ids` link** (zh 27/125, en 21/121, ja 0/59) — these get the neutral/median penalty rather than being filtered, by design, but this means the vocabulary term has literally nothing to say about a fifth of the en/zh catalogue.
5. **`combine_mode='product'` is a documented dead end** — shipped inert, measured, and explicitly recommended against (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md`).
6. **Two parallel daily-load code paths exist**: the Study Plan resolver (`build_daily_session`, budgeted/greedy) and the legacy `_compute_daily_load` (`services/test_service.py:~660-720`, simple "2 retries + fill from `get_recommended_tests`"), selected by `Config.STUDY_PLAN_ENABLED` and whether the user has a `user_study_plans` row. The legacy path does not know about `get_replay_tests`, `word_upload` slots, or surfaces.
7. **`process_test_submission`'s repo has known drift**: `migrations/archive/phase14_test_kfactor_decay.sql` (CR-04 hardening) was written but **never applied live** — confirmed by two independent migration headers (`partF:18-24`, `partG:16-19`) stating the live body lacks it.
8. **`process_dictation_submission` still depends on now-mostly-dead helper functions** (`calculate_volatility_multiplier`, `calculate_elo_rating` in `elo_functions.sql`) that `process_test_submission` no longer calls — a second, divergent ELO-math code path for one test type.
9. **The vocabulary-aware ranker's ability estimate has never been backed by real calibration data** — `user_calibration_state` has 0 rows live, so `ability_zipf` always falls through to the `uvk_crossing` estimate, and the tier-ceiling safety rail has literally never armed for a real learner.
10. **n=1**: as of 2026-09-17, of 14 users, exactly one has ever taken a test — every replay/quality number in this recon (M1-M5, the 0.786→0.952 in-band improvement, the ADR-024 ability-spread figures) describes that single learner's history, in zh and ja only (en has zero attempts).
11. **Documentation lag**: `wiki/tasklist/master.md` (last_updated 2026-09-17) was not updated when `vocab_weight` was flipped to 1 later the same day (§0) — the wiki currently understates the live selection behavior.

---

## 7. Evaluation harnesses for selection quality

### `scripts/measure_selection_quality.py` (TASK-749, read-only, 650 lines)
Computes **M1-M5** per (language, type) from live `test_attempts`/`user_skill_ratings`, plus a **replay** mode:
- **M1 on-target rate**: first attempts with `60 < pct <= 85` (half-open band — the 2026-09-08 baseline is only reproducible excluding exactly-60 scores; inclusive count printed alongside).
- **M2 below-floor rate**: `pct < 50`, computed over **all** attempts (matching the original baseline's methodology), first-attempt variant printed beside it.
- **M3 compression**: spread of *implied* ability (`test_elo_before − 400·log10(1/s − 1)`, s clamped [0.05,0.95]) across types vs. spread of the live per-type rating — this is the metric that produces the "88-point band vs 448-point true spread" ADR-024 number.
- **M4 served unknown**: median `unknown(t)` over the top-10 per type, both arms.
- **M5 pool health**: candidate count per type, both arms — must never fall (the invariant the tier-ceiling-demotes-not-excludes design protects).
- **Replay** (`--until`, `--replay-language`): re-ranks every historical first attempt as of its own timestamp under each of 3 arms (`w0`=weight 0, `sum`=weight 1/sum, `product`=weight 1/product — TASK-781 extended it from 2 to 3 arms) and reports the `unknown(t)` distribution of that arm's top-10. The `product` arm requires a **live write** to `selection_tuning.combine_mode` (PostgREST has no transaction-local rollback), restored in a `finally`, and the script **refuses to flip the mode unless `vocab_weight=0`** (otherwise it could touch real traffic).
- **Recorded result** (`wiki/evaluations/selection-three-arm-replay-2026-09-17.md`): in-band share `w0 0.786 → sum 0.952 → product 0.938`; Spearman(unknown share served, score obtained) = **−0.584**, reproducing an already-on-record −0.59, and is arm-independent by construction (a validity check on the vocabulary signal itself, not an arm comparison).

### `tests/sql/test_task748_parity.sql` (604 lines, rollback-only transaction)
1. **Parity**: loads the pre-TASK-748 live body under a scratch name (`_grt_pre748`, byte-identical to `migrations/archive/task748_prev_get_recommended_tests_live_3arg.sql`) and asserts `vocab_weight=0` reproduces it **identically in content and order**, for every user × en/zh/ja.
2. **Pool health (M5)**: at `vocab_weight=1`, per-type candidate count never falls below the old function's, for every (user, language, type).
3/4. (TASK-780 additions) sum-mode parity against a frozen pre-780 ranker copy; product mode proven inert at `vocab_weight=0` and never shrinks a pool.
This is the script that produced the "APPLIED LIVE" pre/post-apply proofs quoted in both `task748_get_recommended_tests_vocab_aware.sql:111-118` and `task780_selection_combine_mode.sql:98-105`.

### `tests/sql/test_task780_combine_mode.sql` (283 lines, rollback-only, synthetic fixtures)
Deactivates real ja tests inside the transaction and substitutes 5 synthetic tests for one zero-history learner, hand-computing `e`/`v`/`sum`/`product` for each (`good_both`, `unlinked`, `bad_both`, `bad_elo`, `too_hard`). Asserts:
- `sum` ranks `bad_both` (half-miss on both axes) ahead of `bad_elo` (full miss on ELO alone), while `product` reverses them — the intended demotion of "wrong on both axes."
- `too_hard` (perfect ELO match, 90% unknown) must rank **LAST** in both modes — the guard against the wrong (bare `e·v`) multiplicative form, which would score it 0 and rank it FIRST.
- A "REVERT-RED" comment: deleting the product branch collapses the two expected orders to equal, which assertion 3 names explicitly (self-checking that the test can actually fail).

---

## Key files (all read-only in this recon)

- `migrations/task748_get_recommended_tests_vocab_aware.sql` — vocabulary term, `selection_vocab_ability`, `get_recommended_tests` 3-arg thin switch
- `migrations/task780_selection_combine_mode.sql` — **uncommitted**, canonical `recommended_tests_ranked` (sum/product), `selection_tuning.combine_mode`
- `migrations/task744_selection_tuning_table.sql` — tuning table + seeds
- `migrations/word_upload_slot_scheduling.sql` — canonical `build_daily_session`
- `migrations/get_replay_tests.sql` — replay fallback RPC
- `migrations/sec_submission_rpcs_auth_gate.sql` — canonical `process_test_submission` (ELO update + ADR-006 damping)
- `migrations/study_plan_advisory_lock.sql` — weekly recompute cron serialization
- `migrations/task740_collapse_difficulty_to_tier_schema.sql` — difficulty↔tier bridge
- `migrations/partF_question_attempt_results.sql`, `migrations/partG_qar_drop_response_time.sql` — captured-but-unused per-question data; deleted response-time signal
- `services/test_service.py:455-560,582-720` — daily-load routing + fallback + shortfall logging
- `services/study_plan_service.py:522-555` — `build_daily_session` RPC wrapper
- `routes/tests.py:117-127,689-718` — direct `get_recommended_tests` endpoint; submission endpoint
- `wiki/decisions/ADR-006-retry-slot-reduced-elo.md`, `wiki/decisions/ADR-024-vocabulary-aware-test-selection.md`
- `wiki/features/vocabulary-aware-test-selection.tech.md`, `wiki/tasklist/vocabulary-aware-test-selection.tasks.md`
- `wiki/evaluations/selection-three-arm-replay-2026-09-17.md` — **new, uncommitted**
- `wiki/log.md:3-160` (approx.) — **uncommitted**, records both the TASK-781 replay and the same-day `vocab_weight` flip
- `wiki/tasklist/master.md:1-60` — status summary, one entry behind the live flip
- `scripts/measure_selection_quality.py`, `tests/sql/test_task748_parity.sql`, `tests/sql/test_task780_combine_mode.sql`
