---
title: "Knowledge Report — Task Breakdown"
feature: knowledge-report
prose_page: ../features/knowledge-report.md
tech_page: ../features/knowledge-report.tech.md
total_tasks: 40
done: 0
---

# Knowledge Report — Task Breakdown

Supersedes billing **TASK-993** (which becomes "Superseded by TASK-1034–TASK-1071"); TASK-980's 402
helper is amended by TASK-1038; billing TASK-997 must reference the Pro launch gate (TASK-1059).
**LIVE-DB** marks a task whose migration or data change the **owner applies to production** (the only
Supabase project; no staging). Every LIVE-DB task ships a rollback file and ends with the read-only
`tests/sql/check_function_acls.sql` check. **LIVE-STORAGE** marks a task in which the **owner writes
files to the production Storage bucket** `reference-data` (no database rows change except Storage's own
object metadata, ~0.6 KB per file). `[?]` = blocked on an open question (OQn in
[[features/knowledge-report.tech]] §15) or on another blocked task.

*Revised 2026-11-18:* the exam lists are versioned JSON files in Storage, not database tables
([[decisions/ADR-054-exam-word-lists-in-storage]]). TASK-1034 now creates the bucket instead of list
tables; TASK-1049 adds the word-list reader and array-based RPCs; TASK-1052 builds and uploads files;
TASK-1053 is an owner-run Storage upload; neither TASK-1053 nor the Pro gate TASK-1059 waits for the
database size question (OQ13) any more.

## Phases and order

| Phase | Tasks | Gate |
|---|---|---|
| K0 data foundations | TASK-1034 – TASK-1037 | owner applies TASK-1034 / TASK-1036 |
| K1 summary for everyone | TASK-1038 – TASK-1043 | K0 |
| K2 Pro word by word | TASK-1044 – TASK-1048 | K1 (TASK-1048 also needs TASK-1049) |
| K3 lists and study action (critical path for the Pro gate) | TASK-1049 – TASK-1053 | TASK-1052/1053 blocked on OQ2 and OQ3 only (list files live in Storage; no database size gate) |
| K4 measure, document, launch | TASK-1054 – TASK-1059 | TASK-1056 and TASK-1059 blocked |
| Deferred | TASK-1060 – TASK-1071 | each blocked on an owner decision |

**Critical path — summary launch:** TASK-1034 → TASK-1036 → TASK-1037 (snapshots must start early: a
30-day trend needs 30 days of rows) → TASK-1039 → TASK-1040 → TASK-1058.
**Critical path — Pro enforcement / marketing (TASK-1059):** OQ2 + OQ3 (+ TASK-1034 and TASK-1049) →
TASK-1052 → TASK-1053 (owner upload); and TASK-1044 → TASK-1045 → TASK-1046 → TASK-1049 → TASK-1050 →
TASK-1051, TASK-1048. The database size question (OQ13) is not on this path.

| ID | Title | Status | Complexity | Depends On | LIVE |
|----|-------|--------|------------|------------|------|
| TASK-1034 | Foundation migration: snapshot table, frame/pairs/prune functions, `reference-data` bucket | [ ] | M | — | DB |
| TASK-1035 | Pure estimator and rules module | [ ] | M | — | |
| TASK-1036 | Summary RPC `knowledge_report_summary` | [ ] | L | TASK-1034 | DB |
| TASK-1037 | Nightly snapshot job | [ ] | M | TASK-1034, TASK-1035, TASK-1036 | |
| TASK-1038 | Entitlement seam, shared 402 helper, flags, intent log | [ ] | S | — | |
| TASK-1039 | `GET /api/knowledge/summary` and the summary service | [ ] | M | TASK-1035, TASK-1036, TASK-1038 | |
| TASK-1040 | `/knowledge` page: summary cards, states, Me row, i18n | [ ] | L | TASK-1039 | |
| TASK-1041 | Prestudy next step (`/prestudy-suggestion`) | [ ] | S | TASK-1039, TASK-1040 | |
| TASK-1042 | Calibration result shows the same range | [ ] | S | TASK-1039 | |
| TASK-1043 | Practice deep link `extra=reviews` | [ ] | XS | TASK-1040 | |
| TASK-1044 | Words RPC `knowledge_report_words` | [ ] | M | TASK-1034 | DB |
| TASK-1045 | `GET /api/knowledge/words` (Pro) | [ ] | M | TASK-1044, TASK-1038, TASK-1039 | |
| TASK-1046 | Pro UI: All words, Missed recently, filters, sorts | [ ] | L | TASK-1045, TASK-1040 | |
| TASK-1047 | Word sheet: detail RPC, route and UI | [ ] | M | TASK-1044, TASK-1046 | DB |
| TASK-1048 | Export: filtered and list CSV, Anki text | [ ] | M | TASK-1045, TASK-1046, TASK-1049 | |
| TASK-1049 | List RPCs, word-list store and route | [ ] | L | TASK-1034, TASK-1038 | DB |
| TASK-1050 | List cards (summary) and Pro Lists tab | [ ] | M | TASK-1049, TASK-1046 | |
| TASK-1051 | "Add these words to my word list" | [ ] | S | TASK-1050, TASK-1046 | |
| TASK-1052 | Word-list builder and upload script | [?] | M | TASK-1049 | |
| TASK-1053 | Upload the exam lists to Storage | [?] | S | TASK-1034, TASK-1052 | Storage (owner) |
| TASK-1054 | Performance evaluation | [ ] | S | TASK-1036, TASK-1044 | |
| TASK-1055 | End-to-end smoke and visual fixtures | [ ] | S | TASK-1040, TASK-1046 | |
| TASK-1056 | Validate the estimator and the ratings | [?] | M | TASK-1035, TASK-1037, TASK-1061 | |
| TASK-1057 | Documentation reconciliation | [ ] | S | TASK-1034, TASK-1036, TASK-1038, TASK-1040 | |
| TASK-1058 | Enable the report in production | [ ] | XS | TASK-1037, TASK-1040, TASK-1041, TASK-1054 | env |
| TASK-1059 | Pro launch gate | [?] | XS | TASK-1046, TASK-1048, TASK-1051, TASK-1053 | owner |
| TASK-1060 | Import not-in-dictionary words with credits | [?] | L | TASK-1051 | |
| TASK-1061 | Calibration forced-choice probe items | [?] | M | — | DB |
| TASK-1062 | Calibration selector: one lemma, rank-1 sense | [?] | M | — | DB |
| TASK-1063 | Refresh the zh calibration anchor pool | [?] | S | — | DB |
| TASK-1064 | Targeted practice of an explicit word set | [?] | L | TASK-1046, TASK-1050 | |
| TASK-1065 | Evidence-kind counters or evidence log | [?] | L | — | DB |
| TASK-1066 | Decay function clean-ups | [?] | S | — | DB |
| TASK-1067 | Frequency-aware decay and a model review flag | [?] | XL | TASK-1065, TASK-1066 | DB |
| TASK-1068 | Learner corrections on the word sheet | [?] | M | TASK-1047 | |
| TASK-1069 | Today card | [?] | S | TASK-1040 | |
| TASK-1070 | "Upcoming tests" coverage card (Pro) | [?] | M | TASK-1041, TASK-1046 | |
| TASK-1071 | Estimated percentage per exam level | [?] | M | TASK-1050, TASK-1056 | |

---

## TASK-1034: Foundation migration — snapshot table, frame, pairs and prune functions, `reference-data` bucket (LIVE-DB)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Write `migrations/knowledge_report_foundation.sql` with everything later tasks build on:
`user_knowledge_snapshots` (tech §5.1) and three functions — `knowledge_frame_bands()`,
`knowledge_active_pairs(p_since)` and `knowledge_snapshots_prune(p_keep_daily_days)` (§6.1) — and the
small separate `migrations/reference_data_bucket.sql`, which creates the private Storage bucket
`reference-data` for the exam-list files (tech §5.2; ADR-054, revised 2026-11-18). No table for list
data is created. The owner applies both files to production.

**Acceptance Criteria:**
- [ ] The foundation file matches tech §5.1 and §6.1 exactly: names, types, CHECKs (including `array_length(cal_bands, 1) = 21` and `array_length(frame_bands, 1) = 7`), FKs and the PK.
- [ ] `knowledge_frame_bands` and `knowledge_active_pairs` are `LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp`; `knowledge_snapshots_prune` is `plpgsql VOLATILE`, same search_path, and raises `keep_daily_days_too_small` below 35.
- [ ] Every function has `REVOKE ALL … FROM PUBLIC, anon, authenticated` and `GRANT EXECUTE … TO service_role`; the table has `ENABLE ROW LEVEL SECURITY` and `REVOKE ALL … FROM PUBLIC, anon, authenticated` in the same file, and no policies.
- [ ] `migrations/knowledge_report_foundation_rollback.sql` drops the 3 functions and the table.
- [ ] `migrations/reference_data_bucket.sql` is exactly the tech §5.2 statement: `INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) VALUES ('reference-data', 'reference-data', false, 5242880, ARRAY['application/json']) ON CONFLICT (id) DO NOTHING`, with no `storage.objects` policy; `migrations/reference_data_bucket_rollback.sql` raises while the bucket holds any object and otherwise deletes the bucket row.
- [ ] `tests/test_knowledge_report_migration.py` (new) statically checks the above (including the bucket file's values and the absence of `CREATE POLICY`), that neither file creates a table for list data, and that the foundation file never mentions `bkt_effective_p_known`, `bkt_apply_decay` or `level_tag`; `tests/test_migration_security_lint.py` passes.
- [ ] After the owner applies them: `tests/sql/check_function_acls.sql` returns no rows; `SELECT knowledge_frame_bands()->'3:2'` returns `[577,425,621,655,537,283,77]` (if the pool has been refreshed since 2026-11-17, record the new values instead); `SELECT id, public, file_size_limit, allowed_mime_types FROM storage.buckets WHERE id = 'reference-data'` returns `reference-data | f | 5242880 | {application/json}`; `pg_database_size` grows by < 0.3 MB.

**Technical Notes:**
- Frame SQL is in tech §6.1: pool rows with `has_embedding`, not in `calibration_anchor_blocklist`, joined to `dim_word_senses` for `sense_rank = 1`, `count(DISTINCT vocab_id)` by `(word_language_id, definition_language_id, zipf_band)`, folded with `jsonb_object_agg` into `{"<L>:<D>": [N_1..N_7]}` (missing bands = 0).
- `knowledge_active_pairs`: `SELECT DISTINCT user_id, language_id FROM user_vocabulary_knowledge` UNION pairs from `calibration_sessions (mode = 'definition')` ⋈ `calibration_responses` with `answered_at > p_since`; returns a jsonb array.
- Bucket pattern: `migrations/exercise_content_storage.sql:376-378` (the `exercise-content` bucket). The bucket costs < 1 KB of database (ESTIMATE) and does not wait for the database size question (OQ13).
- Do **not** touch `bkt_apply_decay`, `bkt_effective_p_known`, `dim_vocabulary.level_tag` or any existing object.
- Production is the only project: the owner runs both files (SQL editor or migration tool), then the read-only checks.

**Files to Create / Modify:**
- `migrations/knowledge_report_foundation.sql`, `migrations/knowledge_report_foundation_rollback.sql` — new
- `migrations/reference_data_bucket.sql`, `migrations/reference_data_bucket_rollback.sql` — new
- `tests/test_knowledge_report_migration.py` — new

**Verification:**
`python -m pytest tests/test_knowledge_report_migration.py tests/test_migration_security_lint.py -q` passes.
After apply: run `tests/sql/check_function_acls.sql`, `SELECT knowledge_frame_bands()` and the
`storage.buckets` query in the SQL editor; record outputs and the `pg_database_size` before/after in
`wiki/log.md`.

---

## TASK-1035: Pure estimator and rules module (`knowledge_estimate.py`)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Implement every statistic and rule of tech §2.6, §2.7, §2.8 (next level), §2.10, §2.11 and §2.13 as pure,
deterministic Python with no I/O. The summary service and the snapshot job both call it; it is the single
home of the estimator (ADR-051).

**Acceptance Criteria:**
- [ ] `estimate_range(bands, frame, alltime_n) -> dict` returns `shown, kind (range|upper_only|none), lo, hi, lo_disp, hi_disp, tick, label (low|medium|good|None), rel, reason (None|too_few_answers|out_of_date|too_uncertain), have, answers_needed` exactly per the tech §2.6 table rows 1–8: unclamped `K_b`, Jeffreys-pseudo-count variance with `max(0, 1 − n_b/N_b)`, `hi = min(N, max(T, 0) + 1.96·SD)`, `rel' = 1.96·SD / max(T, 0.10·N)`.
- [ ] `group_shares(bands, frame)` returns the four groups of §2.7 with `shown` only when `1.96·sd_g ≤ 0.15`.
- [ ] `family_summary(families)` applies the ≥ 20 attempts and ≥ 10 meanings rule, the clustered variance from the sufficient statistics (`n, y, m, syy, syn, snn`), Wilson at `n_eff`, and the sentence rule of §2.11.
- [ ] `growth(now, anchors, today, frame_now)` implements anchor selection, the rated-known delta with its check count, the estimate comparison (only for disjoint, eligible sets; "no clear change" when `|Δ| < 1.96·SD_diff`) and the > 5 % pool-change notice of §2.10; `next_level(list)` per §2.8; `next_steps(facts)` per §2.13 (rule order, first three).
- [ ] Constants: `G = 0.25`, `R = 1/3`, `Z = 1.96`, `MIN_PER_BAND = 10`, `MEDIUM_PER_BAND = 20`, `GOOD_PER_BAND = 30`, `WINDOW_DAYS = 180`, `REL_GOOD = 0.15`, `REL_MEDIUM = 0.30`, `REL_LOW = 0.50`, `GROUP_MAX_HALF_WIDTH = 0.15`, `FAMILY_MIN_ATTEMPTS = 20`, `FAMILY_MIN_MEANINGS = 10`, `METHOD_VERSION = 1`. There is **no** alternative ("naive") skip model.
- [ ] `tests/test_knowledge_estimate.py` covers every pytest case in tech §13, including the de6fd05b/ja fixture: T 1,110.7 (± 0.5), SD 131.3 (± 0.5), 853.3–1,368.1 (± 1), rel' 0.232, `medium`, display 850–1,400; groups 73–100 / hidden / 17–47 / 8–35; recognition [0.87, 0.97] and discrimination [0.35, 0.71]; the zh beginner → `upper_only` "fewer than 510".
- [ ] `tests/test_knowledge_estimate_coverage.py` (marked `slow`; marker registered in `pyproject.toml`) runs the §2.6 simulation grid at n = 10, 20, 30 per band and asserts coverage ≥ 0.93 and zero zero-width outputs.

**Technical Notes:**
- Formulas in tech §2.6 are authoritative. A reference implementation was used to compute the fixtures (`kr/synth_scripts/final_estimator_v2.py` in the design session's scratchpad; not durable — reproduce from the spec).
- `floor2/ceil2`: step `10**(floor(log10(x)) - 1)` for x ≥ 10, else 1.
- `bands` input is the RPC's `[[n, s, c] × 7]`; `alltime_n` decides E1 vs E1c.
- Keep functions small and typed; no Flask or Supabase imports.

**Files to Create / Modify:**
- `services/vocabulary/knowledge_estimate.py` — new
- `tests/test_knowledge_estimate.py`, `tests/test_knowledge_estimate_coverage.py` — new
- `pyproject.toml` — add `markers = ["slow: long-running statistical tests"]` under `[tool.pytest.ini_options]`

**Verification:** `python -m pytest tests/test_knowledge_estimate.py -q`; `python -m pytest tests/test_knowledge_estimate_coverage.py -q -m slow` (under 2 minutes).

---

## TASK-1036: Summary RPC `knowledge_report_summary` (LIVE-DB)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1034

**Description:**
Write `migrations/knowledge_report_summary.sql` with `knowledge_report_summary(p_user_id, p_language_id,
p_as_of, p_window_days, p_cal_since)` returning the jsonb of tech §6.1: tracked counts, evidence states,
rated-known words, idle, activity, missed recently and its flag, per-band measured counts, calibration
inputs (D*, latest-answer-per-lemma rank-1 bands, all-time n, `since` bands, dates, rated-known-in-frame),
family sufficient statistics and watchlist buckets. One statement. Exam-list buckets are **not** computed
here (ADR-054, revised 2026-11-18): `knowledge_list_buckets` (TASK-1049) counts them from arrays.

**Acceptance Criteria:**
- [ ] Every rule follows the tech spec literally: meaning aggregation §2.2, logged outcomes §2.3, states and rated known §2.4, idle §2.5, calibration inputs §2.6 steps 1–4 (D* tie-breaks; `sense_rank = 1`; `DISTINCT ON (anchor_vocab_id)` latest answer), activity §2.10, families §2.11 (non-intro first attempts, 90 days), missed recently §2.12, watchlist §2.9; the jsonb has no `lists` key.
- [ ] `LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp`; REVOKE/GRANT as TASK-1034; no MATERIALIZED CTE; no call to any decay function; rollback file drops it.
- [ ] Read-only check after apply (values as of 2026-11-17; if de6fd05b has practised since, re-run tech Appendix B K2–K5 the same day and compare to those): for de6fd05b/ja `tracked.words = 251`, `rated_known_words = 69`, `rated_known_checked2_words = 22`, `states = {10, 69, 30, 142}`, `idle60_meanings = 95`, `activity.d30 = {41, 164, 44}`, `activity.d90 = {83, 318, 142}`, `missed_recent = {10, 1}`, `calibration.definition_language_id = 2`, `calibration.bands` = tech §2.6 table, families recognition `n 84 y 79 m 17` and discrimination `n 32 y 17 m 11`.
- [ ] A learner/language with no data returns zero counts and empty arrays (never NULL).
- [ ] `EXPLAIN (ANALYZE, BUFFERS) SELECT knowledge_report_summary(<110fb390 uuid>, 1::smallint)`: index scans on `idx_uvk_user_language` and pkeys, no temp writes, best warm run ≤ 100 ms (record every run; the host is noisy).
- [ ] The static migration test covers this file (STABLE, no INSERT/UPDATE/DELETE, no decay functions).

**Technical Notes:**
- `exercise_attempts` and `word_quiz_results` have no language column: filter through `dim_word_senses.word_language_id`.
- Missed-recently flag: per meaning `row_number() OVER (PARTITION BY vocab_id, sense_rank ORDER BY at DESC)`; flag when total outcomes ≥ 4, wrong among `rn ≤ 5` ≥ 3, and `count(DISTINCT at::date)` of those wrongs ≥ 2.
- `p_cal_since timestamptz[]`: `unnest(p_cal_since) WITH ORDINALITY` and one latest-per-lemma count per element.
- Families: return `n, y, m, Σy², Σy·n, Σn²` per family (not per-meaning arrays).
- `rated_known_in_frame`: rated-known rank-1 lemmas that appear in `calibration_anchor_pool` for (L, D*) with the frame filters.
- No list CTE: the summary service adds `lists` from the word-list files and `knowledge_list_buckets` (tech §6.3, TASK-1049). Keep the §2.4 rated-known expression textually identical to the one `knowledge_list_buckets` uses.

**Files to Create / Modify:**
- `migrations/knowledge_report_summary.sql`, `migrations/knowledge_report_summary_rollback.sql` — new
- `tests/test_knowledge_report_migration.py` — extend

**Verification:** pytest as TASK-1034; after apply, `SELECT knowledge_report_summary('<de6fd05b uuid>'::uuid, 3::smallint)` in the SQL editor (read-only) compared with the criteria; EXPLAIN output saved for TASK-1054.

---

## TASK-1037: Nightly snapshot job

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1034, TASK-1035, TASK-1036

**Description:**
Add `services/knowledge_snapshots.py` and register it in APScheduler at 04:25 UTC so history accrues
before the page ships (ADR-053, tech §7). It stores the estimator's inputs, not only its outputs.

**Acceptance Criteria:**
- [ ] `run_nightly(db=None)` follows tech §7: one `as_of` per run; pairs from `knowledge_active_pairs(as_of − 180 d)`; per pair the summary RPC (with `p_cal_since = '{}'`), the frame from `knowledge_frame_bands`, `knowledge_estimate.estimate_range`; one upsert with every column of tech §5.1 (`cal_bands` length 21, `frame_bands` length 7, `cal_first_answer_at`, `cal_last_answer_at`, `est_kind/lo/hi/label`), `source='nightly'`, `method_version`; then `knowledge_snapshots_prune(120)`; returns `{pairs, written, failed, pruned}`.
- [ ] A failing pair logs `knowledge_snapshot_failed user=<8 chars> lang=<id>` and does not stop the run.
- [ ] Running twice on the same day leaves exactly one row per pair.
- [ ] `web/scheduler.py` `JOBS` gains `Job('knowledge_snapshots_nightly', 'services.knowledge_snapshots:run_nightly', {'hour': 4, 'minute': 25}, 'Knowledge snapshots', _log_skippable, _admin_client)`; the schedule comment lists it; `DISABLE_SCHEDULER` still disables it.
- [ ] `python -m services.knowledge_snapshots --once` writes `source='manual'`.
- [ ] `tests/test_knowledge_snapshots.py` covers the cases in tech §13.

**Technical Notes:**
- Use `get_supabase_admin()`; upsert through PostgREST `.upsert(..., on_conflict='user_id,language_id,snapshot_date')`.
- Not gated by `KNOWLEDGE_REPORT_ENABLED` (history must accrue while the page is hidden).
- No advisory lock (performance research §7.4: the idempotent upsert is the safer pattern across the two gunicorn workers).

**Files to Create / Modify:**
- `services/knowledge_snapshots.py` — new
- `web/scheduler.py` — register the job after the 04:20 sweep
- `tests/test_knowledge_snapshots.py` — new

**Verification:** `python -m pytest tests/test_knowledge_snapshots.py -q`; the morning after deploy,
`SELECT count(*), min(snapshot_date), max(snapshot_date), max(array_length(cal_bands,1)) FROM user_knowledge_snapshots` (read-only) shows one row per active pair and 21.

---

## TASK-1038: Entitlement seam, shared 402 helper, feature flags and intent logging

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
Implement ADR-055: `report_detail_level()`, `payment_required()` in the app envelope, the 402 entry in
`web/errors.py`, the `KNOWLEDGE_REPORT_ENABLED` / `ENTITLEMENTS_ENFORCED` flags, and the
`knowledge_pro_intent` helper that decides which requests count as demand (tech §6.4).

**Acceptance Criteria:**
- [ ] `utils/responses.payment_required(error_code, message, **extra)` returns HTTP 402 with `{status:'error', error:message, error_code, upgrade:true, **extra}`.
- [ ] `web/errors.py` `_API_ERRORS[402] = ('PAYMENT_REQUIRED', None)`.
- [ ] `report_detail_level(db, user_id)` follows tech §6.4: TASK-980's module if importable; else the `can_access_analytics` stub via `request_cache.memo(('kr_tier', user_id), …)` with `enforced` forced to False (warning logged if the flag is on).
- [ ] `config.py` FEATURE FLAGS section (`config.py:219`): `KNOWLEDGE_REPORT_ENABLED = _env_bool('KNOWLEDGE_REPORT_ENABLED', False)`; `ENTITLEMENTS_ENFORCED = _env_bool('ENTITLEMENTS_ENFORCED', False)` if absent.
- [ ] `pro_intent_action(endpoint, args) -> str | None` returns `search | filter | sort | load_more | word_sheet | lists_tab | export_csv | export_anki` per tech §6.4 and `None` for the default first `/words` page; `log_pro_intent(action, user_id)` logs `knowledge_pro_intent action=<a> user=<8 chars>`.
- [ ] Unit tests: helper payload, stub (free → 0, admin → 1), forced `enforced=False`, one tier read per request, every intent case.

**Technical Notes:** the stub's only visible effect is the preview note and log lines; enforcement belongs to billing TASK-997 and the Pro launch gate (TASK-1059).

**Files to Create / Modify:**
- `utils/responses.py`, `web/errors.py`, `config.py` — modify
- `services/vocabulary/knowledge_report.py` — new (seam and intent helpers only in this task)
- `tests/test_knowledge_report_service.py` — new

**Verification:** `python -m pytest tests/test_knowledge_report_service.py -q`.

---

## TASK-1039: `GET /api/knowledge/summary` and the summary service

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1035, TASK-1036, TASK-1038

**Description:**
Create `routes/knowledge.py` (`knowledge_bp`, prefix `/api/knowledge`) with the summary route, and
`knowledge_report.summary()`: read snapshot anchors, call the RPC through `optional_rpc.call_bundle` with
`p_cal_since` from the anchors, add the cached frame, run the estimator and rules, and return tech §6.3.

**Acceptance Criteria:**
- [ ] Decorator stack and guards of tech §6.2 (JWT, `api_errors`, `require_language_id`, UUID guard → 403, language ∈ {1,2,3}, flag off → 404, RPC missing → 503).
- [ ] Snapshot read: one PostgREST select on `user_knowledge_snapshots` for (user, language) with `snapshot_date >= today − 97` plus the earliest row, memoised per request; anchors chosen by `knowledge_estimate.growth`; their `cal_last_answer_at` values passed as `p_cal_since`.
- [ ] `knowledge_frame_bands()` cached per process for 3,600 s; the frame for (L, D*) feeds the estimator.
- [ ] Response shape exactly tech §6.3, including `detail {level, enforced, preview}`, `estimate.kind/reason/answers_needed/disagreement`, `groups`, `growth.d30/d90/idle60`, `skills`, `missed_recent`, `next_steps` (rules 1, 3–6 of §2.13; rule 2 is added by TASK-1041) and `pro_teaser` (clauses with zero or undefined values omitted); `lists = []` and `lists_unavailable = false` until TASK-1049 fills them.
- [ ] `Cache-Control: private, no-store`; `knowledge.summary` limit in `web/rate_limits.py`; `app.py` registers `knowledge_bp` with `url_prefix='/api/knowledge'` (pattern `app.py:234`).
- [ ] Route and service tests of tech §13 pass, including "p_user_id is always the caller's".

**Technical Notes:**
- Do not copy `/api/flashcards/stats` (Python counting past the 1,000-row cap, server date — code-map research §13).
- Language name for the copy comes from `Config.LANGUAGES` (`config.py:202-206`).

**Files to Create / Modify:**
- `routes/knowledge.py` — new; `app.py` — register; `web/rate_limits.py` — limit
- `services/vocabulary/knowledge_report.py` — `summary()`
- `tests/test_knowledge_routes.py` — new; `tests/test_knowledge_report_service.py` — extend

**Verification:** `python -m pytest tests/test_knowledge_routes.py tests/test_knowledge_report_service.py tests/test_platform_rate_limits.py -q`;
locally with the flag on, `curl -H "Authorization: Bearer <token>" "localhost:5000/api/knowledge/summary?language_id=3"` returns the §6.3 shape.

---

## TASK-1040: `/knowledge` page — summary cards, states, Me row, i18n

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1039

**Description:**
Build the task-mode page of tech §3.1 and §10 (cards 1, 2, 5, 6, 7, 8), every state of tech §4 (E0–E10),
the Me hub row, and all summary `knowledge.*` keys in four locales. List cards come in TASK-1050, the Pro
section in TASK-1046.

**Acceptance Criteria:**
- [ ] `web/pages.py` adds `('/knowledge', 'knowledge_page', 'knowledge.html')`; `tests/test_platform_app.py` `EXPECTED_PAGE_URLS` updated; `templates/base.html` `'me'` tuple includes `knowledge_page`.
- [ ] `templates/profile.html` shows the "My vocabulary" row first, only when `config.KNOWLEDGE_REPORT_ENABLED`.
- [ ] Cards render per tech §3.1 with the copy rules of §2.14: every number carries its prefix (From your answers / Estimated / Model); the range uses an en dash, names the pool denominator, shows label and answer dates, and never prints the point; upper-only renders "Fewer than {hi}"; groups follow §2.7; growth shows the check count beside the rated-known delta and the "no direct checks" line when it is 0; Skills shows "{n} tries on {m} words", the sentence and footnote.
- [ ] States E0–E10 render as specified; "0 words" is never shown; no "due", "fading" or "forgotten" copy anywhere.
- [ ] The Pro card follows §3.1 item 8 (own counts, button only if `window.LinguaPaywall` exists, no blur, no modal).
- [ ] Every key used exists in `static/i18n/{en,es,ja,zh}.json`; new `tests/test_i18n_locale_parity.py` passes; es/ja/zh strings reviewed by a native speaker before TASK-1058 (OQ1).
- [ ] No emoji, streak, XP or praise copy; tokens only; ≥ 44 px targets; no horizontal scroll at 390 px.
- [ ] `tests/unit/knowledge-page.test.js` covers E0, E1, E1b, E1c, upper-only, full summary, preview note, 402 → Pro card, 404/503 → unavailable.

**Technical Notes:** classic IIFE (pattern `static/js/dual_translation_profile.js:14-103`); summary and i18n fetched in parallel (ADR-042); `localStorage` only for `kn.growthWindow` inside try/catch; database text via `textContent`.

**Files to Create / Modify:**
- `templates/knowledge.html`, `static/js/pages/knowledge.js`, `static/css/pages/knowledge.css` — new
- `web/pages.py`, `templates/base.html`, `templates/profile.html`, `static/i18n/en.json`, `static/i18n/es.json`, `static/i18n/ja.json`, `static/i18n/zh.json` — modify
- `tests/test_platform_app.py` — modify; `tests/test_i18n_locale_parity.py`, `tests/unit/knowledge-page.test.js` — new

**Verification:** `python -m pytest tests/test_platform_app.py tests/test_i18n_locale_parity.py -q`;
`npx vitest run tests/unit/knowledge-page.test.js`; `npm run check`; open `/knowledge` locally at 390 px and 1280 px.

---

## TASK-1041: Prestudy next step (`GET /api/knowledge/prestudy-suggestion`)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1039, TASK-1040

**Description:**
Add next-step rule 2 of tech §2.13: a separate endpoint that finds the top recommended reading or
listening test and its share of new key words, and the page inserts "Prepare for {title}: {u} of its {n}
key words are new to you" → `/test/<slug>/prestudy` when the share exceeds the auto threshold (P7).

**Acceptance Criteria:**
- [ ] `GET /api/knowledge/prestudy-suggestion?language_id=` (all tiers; guards as TASK-1039) calls `get_db().rpc('get_recommended_tests', {'p_user_id', 'p_language_id'})` (as `routes/tests/catalog.py:118-121`), takes the first row with `test_type ∈ ('reading','listening')`, and calls `services/prestudy.plan_for_tests(db, user_id, language_id, [{'id': test_id, 'test_type': test_type}])` (`services/prestudy.py:907`).
- [ ] Returns `suggestion` only when `unknown_share > AUTO_THRESHOLD` (`services/prestudy.py:852`, 0.25) and, if `services.billing.entitlements` is importable, a `prestudy_per_week` use remains; otherwise `suggestion: null`. Any RPC error → `suggestion: null` with an info log, never a 5xx.
- [ ] The page fetches it in parallel with the summary and inserts the button at rule position 2 (still at most three buttons).
- [ ] Rate limit `knowledge.prestudy_suggestion`; `Cache-Control: private, no-store`.
- [ ] Tests: share 0.25 → null; 0.26 → suggestion; no reading/listening test → null; RPC raises → null; vitest for insertion order.

**Technical Notes:** separate request so the summary never waits for `get_recommended_tests` (mean 214 ms, max 7.2 s in `pg_stat_statements` — performance research §1). No prestudy quota exists in code today (grep for `prestudy_per_week` in `*.py` returns nothing).

**Files to Create / Modify:**
- `routes/knowledge.py`, `services/vocabulary/knowledge_report.py`, `web/rate_limits.py` — modify
- `static/js/pages/knowledge.js`, `static/i18n/*.json` — modify
- `tests/test_knowledge_routes.py`, `tests/unit/knowledge-page.test.js` — extend

**Verification:** `python -m pytest tests/test_knowledge_routes.py -q`; `npx vitest run tests/unit/knowledge-page.test.js`.

---

## TASK-1042: Calibration result shows the same vocabulary range

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1039

**Description:**
So a learner finishing the check does not see two unlinked results for one concept (P16), the calibration
result screen shows the report's word range (same estimator and gate) with a link to "My vocabulary", and
labels its own frequency-level figure with what it measures (OQ33).

**Acceptance Criteria:**
- [ ] After `renderResults` (`static/js/pages/calibration.js:403-420`), the page calls `authFetch('/api/knowledge/summary?language_id=…')`; on 200 with `estimate.shown` it renders the range sentence, label and answer dates plus a link "See My vocabulary" (`/knowledge`); on 200 without an estimate it renders the reason line (e.g. "{have} of 70 answers so far") and the link; on 404/503/error it renders nothing.
- [ ] The existing figure gains the sub-line "The frequency level where you still know 85% of words (this check's own measure)".
- [ ] New keys in all four locales; parity test passes.
- [ ] `tests/unit/calibration-result-knowledge.test.js` (new) covers shown / not shown / 404.

**Technical Notes:** no change to `services/calibration_service.py` or the ability fit; the block appears only when the knowledge flag is on (the API answers 404 otherwise).

**Files to Create / Modify:**
- `static/js/pages/calibration.js`, `templates/calibration.html`, `static/i18n/*.json` — modify
- `tests/unit/calibration-result-knowledge.test.js` — new

**Verification:** `npx vitest run tests/unit/calibration-result-knowledge.test.js`; finish a short check locally with the flag on and off.

---

## TASK-1043: Practice deep link `?mode=practice&extra=reviews`

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** XS (<1h)
**Depends On:** TASK-1040

**Description:**
"Review in Practice" should land on reviews even when today's queue is done. Practice already shows the
extra-round panel with reviews preselected when the queue is empty (`static/js/session/controller.js:119`,
`:1103-1112`); this task starts that round directly when the URL asks for it (P6).

**Acceptance Criteria:**
- [ ] On `/session?mode=practice&extra=reviews`, when `showEmpty()` runs in practice mode and no new words are pending, the controller calls `startExtraRound({reviews: true, newWords: 0})` (`controller.js:1077`) once instead of waiting for a click; the URL parameter is consumed (a reload does not re-trigger it).
- [ ] When today's queue is not empty, behaviour is unchanged.
- [ ] The knowledge page's "Review in Practice" button uses the new URL.
- [ ] A vitest case for the auto-start and the no-op path.

**Technical Notes:** reuse `normalizeExtraChoice` / `isRunnableExtraChoice`; no API change (`GET /api/practice/extra?reviews=1`, `routes/practice.py:92-134`).

**Files to Create / Modify:**
- `static/js/session/controller.js`, `static/js/pages/knowledge.js` — modify
- `tests/unit/session-extra-deeplink.test.js` — new

**Verification:** `npx vitest run tests/unit/session-extra-deeplink.test.js`; open the URL locally after finishing today's practice.

---

## TASK-1044: Words RPC `knowledge_report_words` (LIVE-DB)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1034

**Description:**
Write `migrations/knowledge_report_words.sql`: one page of meanings with evidence state and evidence lead,
filters, search, the sorts, the 5-tuple keyset and page-only joins for gloss, pronunciation and ladder
(tech §6.1).

**Acceptance Criteria:**
- [ ] Filters (`states`, `checked_several`, `missed_recent`, `idle_days`, `bands`, `in_word_list`, `vocab_ids` (int[]; lemma in the array, rank-1 meaning — replaces `list_code` + `level`, ADR-054), `q`), toneless-pinyin key, sort table (`useful | recent | oldest | common | lemma | id`), keyset predicate, `p_limit + 1` fetch, `matching` and row fields exactly as tech §6.1. No numeric `p_known` and no five-level label in the output; `app_rates_known` boolean only.
- [ ] `last_direct` from the latest outcome in `O` (tech §2.3) with its family per tech §2.11 (intro `ex_*` via `exercise_attempts.exercise_id → exercises.exercise_type`, PK lookup reading `exercise_type` only — never `exercises.content`).
- [ ] Gloss fallback (L1 standard → L1 simple → native standard) via `uq_sense_def_level`; gloss, pronunciation and ladder joined only for page rows.
- [ ] Security header and grants as TASK-1034; rollback file.
- [ ] Read-only checks after apply: paging de6fd05b/ja with `limit 50` returns exactly 251 distinct meanings with no duplicate or gap for every sort; `states` filter counts equal the summary's `{10, 69, 30, 142}`; paging 110fb390/zh returns 574 meanings; `q='不'` returns only lemmas starting with 不.
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` of the default sort for 110fb390/zh ≤ 80 ms on the best warm run; all runs recorded.

**Technical Notes:** no decay function; `useful` k1 tiers 0 `missed_last` · 1 `checked` · 2 `not_checked` · 3 `rated_known`, k2 `-coalesce(zipf, -1)`; validate the cursor element types with explicit casts.

**Files to Create / Modify:**
- `migrations/knowledge_report_words.sql`, `migrations/knowledge_report_words_rollback.sql` — new
- `tests/test_knowledge_report_migration.py` — extend

**Verification:** pytest static test; after apply, the paging checks above in the SQL editor (read-only).

---

## TASK-1045: `GET /api/knowledge/words` (Pro) with validation, gate and intent log

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1044, TASK-1038, TASK-1039

**Description:**
Add the Pro words route: parameter validation (tech §6.2), base64url cursor, LIKE escaping, the entitlement
gate and intent logging (§6.4), the learner's definition language from
`gloss_lookup.get_user_definition_language_id`, and pinyin display via `services/pinyin_format.display_pronunciation`.

**Acceptance Criteria:**
- [ ] Every 400 case of tech §6.2 has a test; the cursor round-trips; `q` with `%`, `_`, `\` is escaped.
- [ ] Gate: level 1 → 200; level 0 not enforced → 200 + `entitlement_shadow_deny`; level 0 enforced → the 402 payload of tech §6.4.
- [ ] `knowledge_pro_intent` is logged for search, filter, non-default sort and cursor requests, and not for the default first page.
- [ ] Rate limit `knowledge.words`; `Cache-Control: private, no-store`.

**Technical Notes:** `limit` 1–100 (default 50); never pass a request-supplied user id to the RPC. The `list` + `level` parameters are resolved into `p_filters.vocab_ids` by the word-list store, which TASK-1049 adds; until TASK-1049 lands, any `list` value returns 400 "Unknown list".

**Files to Create / Modify:**
- `routes/knowledge.py`, `services/vocabulary/knowledge_report.py`, `web/rate_limits.py` — modify
- `tests/test_knowledge_routes.py` — extend

**Verification:** `python -m pytest tests/test_knowledge_routes.py -q`.

---

## TASK-1046: Pro UI — All words and Missed recently tabs, filters, sorts, search

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1045, TASK-1040

**Description:**
Build the Word-by-word section of tech §3.2 (All words and Missed recently; Lists is TASK-1050): rows that
lead with evidence, the four evidence-state chips, the filter bottom sheet, sort select, search, "Load
more", the shadow note (§3.3) and the 402 path.

**Acceptance Criteria:**
- [ ] Rows on phones and `.table` at ≥ 768 px with the fields of tech §3.2; the first line is the evidence lead ("Last direct check ✓/✗ {date}" / "Checks ✓{c} ✗{w}" / "Seen in tests only"); "Not seen for {n} days" when ≥ 60; no five-level label and no numeric rating anywhere.
- [ ] Missed recently tab lists §2.12 rows, most-missed first, with "Latest miss: {kind}, {date}" and the flag copy "Missed {w} of your last {k} tries, on {d} days".
- [ ] Filters and sorts map 1:1 to the API params (groups map to band lists); search debounced 300 ms; "Load more" uses `next_cursor`; `kn.sort` and `kn.wordTab` remembered in `localStorage` (try/catch).
- [ ] Shadow (`preview`) shows the neutral note; 402 replaces the section with the Pro card; E5 with "Clear filters".
- [ ] Vitest: load more appends; filters build the right query; Missed recently rendering; 402 path; database text escaped. Remaining `knowledge.words.*` keys in all four locales; parity test passes.

**Files to Create / Modify:**
- `static/js/pages/knowledge.js`, `templates/knowledge.html`, `static/css/pages/knowledge.css`, `static/i18n/*.json` — modify
- `tests/unit/knowledge-page.test.js` — extend

**Verification:** `npx vitest run tests/unit/knowledge-page.test.js`; `npm run check`; manual check at 390 px and 1280 px.

---

## TASK-1047: Word sheet — detail RPC, route and UI (LIVE-DB)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1044, TASK-1046

**Description:**
Write `migrations/knowledge_report_word_detail.sql` (tech §6.1), add `GET /api/knowledge/words/<vocab_id>/<sense_rank>`
(Pro gate, intent `word_sheet`, 404 on `null`) and the word sheet of tech §3.2 ("Why we think this").

**Acceptance Criteria:**
- [ ] Events from the four sources, newest first, ≤ 30; `itemised` and `other_updates` per tech §6.1; test-question events marked "linked by today's question links".
- [ ] Sheet shows the evidence lead, the events list, "about {k} other updates are not listed one by one (…)", flashcard and ladder state, and "Model · App's rating: rates this word as known / not yet as known, after your answer on {date}. This is a model rating, not a probability." — no five-level label, no number.
- [ ] Route gate as TASK-1045; rate limit `knowledge.word_detail`; security header, grants and rollback for the RPC.
- [ ] Read-only check after apply on one de6fd05b/ja meaning: `rows` and counters equal its UVK row; `events` include its `exercise_attempts`.

**Files to Create / Modify:**
- `migrations/knowledge_report_word_detail.sql`, `migrations/knowledge_report_word_detail_rollback.sql` — new
- `routes/knowledge.py`, `services/vocabulary/knowledge_report.py`, `web/rate_limits.py`, `static/js/pages/knowledge.js`, `static/i18n/*.json` — modify
- `tests/test_knowledge_routes.py`, `tests/unit/knowledge-page.test.js`, `tests/test_knowledge_report_migration.py` — extend

**Verification:** pytest and vitest as above; SQL editor check after apply.

---

## TASK-1048: Export — filtered and list CSV, Anki text (Pro)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1045, TASK-1046, TASK-1049

**Description:**
Implement tech §6.6 (P3, P15): `utils/csv_export.py`, `GET /api/knowledge/export` for `format=csv|anki` and
`scope=words|list` with the screen's filters, the licence rule for list subsets, and browser assembly with
progress. Export is one of the four Pro launch gate items.

**Acceptance Criteria:**
- [ ] Columns, formats and headers exactly as tech §6.6; no numeric `p_known` column; list exports add `list_level` and `list_source` (= the list file's `attribution`) on every row; the list file's `allow_export = false` → 403 "This list can't be exported yet."; `my_word_list` always exportable.
- [ ] Storage unavailable during a list export (scope `list`, or a `list` filter) → 200 with no rows and `X-Lists-Unavailable: 1`; the client saves nothing and shows "Word lists are unavailable right now"; a cursor from an older file version → 400 `LIST_UPDATED` and the client offers to restart the export.
- [ ] `safe_cell` neutralises `=`, `+`, `-`, `@`, TAB, CR as the first character in both formats; CJK survives a `csv.reader` round trip; CSV uses CRLF and a BOM on the first chunk only; the Anki file starts with `#separator:tab`, `#html:false`, `#tags column:4` and replaces TAB/CR/LF inside fields with a space.
- [ ] Entitlement checked on every chunk; intent logged on the first chunk only; rate limit `knowledge.export`.
- [ ] Client concatenates `blob()` parts, stops when `X-Next-Cursor` is absent or after 100 chunks, saves via an object URL and revokes it; the export menu exports the current tab and filter.
- [ ] Tests: `tests/test_csv_export.py` (new), route tests for headers, chunking, scope and the licence rule, vitest for assembly.
- [ ] Manual: the Anki file imports into Anki desktop (2.1.55 or later) as Basic notes with tags; the result is recorded in the PR.

**Technical Notes:** export `sort='id'` for scope `words` (stable while paging); scope `list` pages `knowledge_report_list_words` by its own keyset (`not_in_dictionary` pages come from the file, tech §6.1), every chunk from the file version in the cursor.

**Files to Create / Modify:**
- `utils/csv_export.py`, `tests/test_csv_export.py` — new
- `routes/knowledge.py`, `services/vocabulary/knowledge_report.py`, `web/rate_limits.py`, `static/js/pages/knowledge.js`, `static/i18n/*.json` — modify
- `services/static_assets.py` — optional: add `text/csv` to `COMPRESS_MIMETYPES`

**Verification:** `python -m pytest tests/test_csv_export.py tests/test_knowledge_routes.py -q`; locally export a
filtered view and a list level, open the CSV in a spreadsheet (Chinese/Japanese render; a lemma like `-ism`
appears as `'-ism`) and import the Anki file.

---

## TASK-1049: List RPCs, word-list store and route (LIVE-DB)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1034, TASK-1038

**Description:**
Everything that reads exam lists, per ADR-054 (revised 2026-11-18): `services/vocabulary/word_lists.py`
(`WordListStore` over `SupabaseStorageBackend(bucket='reference-data')`, `validate_word_list`,
`LIST_CODES_BY_LANGUAGE`, `WordList` arrays — tech §8); `migrations/knowledge_report_list_words.sql`
with `knowledge_list_buckets` and `knowledge_report_list_words`, which take the list's ids as arrays
(tech §6.1; no list table); the summary's `lists` / `lists_unavailable` (tech §6.3); the `/words`
`list` + `level` filter; and `GET /api/knowledge/lists/<list_code>/words` (Pro) for exam lists and the
virtual `my_word_list`. Works before any list file exists: tests use `InMemoryBackend`.

**Acceptance Criteria:**
- [ ] `WordListStore` exactly as tech §8: latest `v<N>` chosen as a number; `validate_word_list` covers every rule of tech §5.2/§8; per-process cache keyed by (list code, version); version re-check at most every 6 h (`RECHECK_S = 21600`); `RETRY_AFTER_FAILURE_S = 300`; serves the cached version when a re-check fails; `WordListsUnavailable` only when nothing is cached; `None` when no file exists; a list code reaches the backend only if registered in `LIST_CODES_BY_LANGUAGE` and matching `^[a-z0-9_]{3,40}$`.
- [ ] `knowledge_list_buckets` and `knowledge_report_list_words` follow tech §6.1 literally: parallel arrays, `LANGUAGE plpgsql STABLE` with the `list_arrays_mismatch` check, rank-1 rule and the §2.4 rated-known expression textually identical to `knowledge_report_summary`'s, NULL arrays → `my_word_list` (§2.9), keyset `(-coalesce(zipf, -1), item_no)`; `SECURITY INVOKER`, pinned `search_path`, REVOKE/GRANT as TASK-1034; the rollback drops both.
- [ ] Summary: for zh/ja the service adds `lists` per tech §6.3 (`items`, `in_dictionary`, `not_in_dictionary` from the file; the four SQL buckets from `knowledge_list_buckets`; `built_at`, `version`, `attribution`, `allow_export`, `is_official`); store failure, `call_bundle` → `None`, or an `in_dictionary` mismatch gives `lists: []`, `lists_unavailable: true` and HTTP 200 with every other field unchanged.
- [ ] Route `/lists/<list_code>/words`: validation (bucket, level ∈ the file's `level_codes`, cumulative, cursor); unregistered code or no file → 404; `not_in_dictionary` paged from the file with cursor `[1, item_no]`; cursor = base64url `[k1, item_no, version]`, an older version → 400 `LIST_UPDATED`; Storage down → 200 `lists_unavailable: true`, `rows: []`; returns `attribution`, `allow_export`, `built_at`; Pro gate, intent `lists_tab`, rate limit `knowledge.list_words`.
- [ ] `/words` (and export scope `words`): `list` + `level` resolved through the store into `p_filters.vocab_ids`; unregistered list → 400 "Unknown list"; Storage down → 200 with `lists_unavailable: true` and no rows.
- [ ] Tests: `tests/test_word_lists.py` (new) covers every store case of tech §13; `tests/test_knowledge_routes.py` covers Storage down (no 5xx), `LIST_UPDATED`, 404 and 400 cases; the migration test covers the new file.
- [ ] Read-only checks after the owner applies the migration: `SELECT knowledge_list_buckets('<de6fd05b uuid>'::uuid, 3::smallint, <its tracked vocab_ids>, <the same number of 1s>)` returns `rated_known` equal to the summary's `rated_known_words` (69 on 2026-11-17; compare on the same day); `EXPLAIN (ANALYZE, BUFFERS)` of a 10,896-element call for 110fb390/zh ≤ 50 ms on the best warm run (all runs recorded); one full-size call (10,896 ids) made from Python through PostgREST succeeds — record the request body size and the time (the PostgREST/gateway body limit is not documented in this wiki).

**Technical Notes:**
- Backend: `SupabaseStorageBackend(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY, bucket='reference-data', http_timeout_s=2.0)` (`services/exercise_content/backends.py:357`); only `list` and `get` are used at runtime. Its errors are `ContentStorageError` (`services/exercise_content/store.py`); catch them in the store, never in routes.
- `knowledge_report_list_words` gets only in-dictionary entries; Python adds `headword`, `reading`, `level` from the entry (`item_no` = 1-based position) and never sends `not_in_dictionary` to SQL.
- The full-size arrays are ESTIMATE ≈ 53 KB (today's ~6.6k HSK matches) to ≤ ~90 KB (every entry matched).

**Files to Create / Modify:**
- `services/vocabulary/word_lists.py` — new
- `migrations/knowledge_report_list_words.sql`, `migrations/knowledge_report_list_words_rollback.sql` — new
- `routes/knowledge.py`, `services/vocabulary/knowledge_report.py`, `web/rate_limits.py` — modify
- `tests/test_word_lists.py` — new; `tests/test_knowledge_routes.py`, `tests/test_knowledge_report_service.py`, `tests/test_knowledge_report_migration.py` — extend

**Verification:** `python -m pytest tests/test_word_lists.py tests/test_knowledge_routes.py tests/test_knowledge_report_service.py tests/test_knowledge_report_migration.py -q`; after apply, `SELECT knowledge_report_list_words('<uid>'::uuid, 3::smallint, NULL, NULL, 'no_evidence', 2::smallint)` returns `{"rows":[],"next_cursor":null,…}` today (0 watchlist rows) and the `knowledge_list_buckets` check above.

---

## TASK-1050: List cards (summary) and the Pro Lists tab

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1049, TASK-1046

**Description:**
Render the exam-list card and "My word list" card of tech §3.1 (items 3–4) from the summary payload, the
"next level" clause of the Pro card (P13), and the Pro Lists tab (picker + bucket chips + paged words) of
tech §3.2.

**Acceptance Criteria:**
- [ ] Four-segment bars with counts per level, the cumulative toggle (counts summed over levels ≤ the chosen one), attribution under the card, "List matched to the dictionary on {date}" (`built_at`), "unofficial" for `is_official = false`, the JLPT "{x} of {items} words are not yet in LinguaDojo" line first, the readiness footnote; **no estimated percentage**.
- [ ] `pro_teaser.missing_next_level` and `next_level` computed with `knowledge_estimate.next_level` (lowest level with rated-known share of in-dictionary items < 0.80); clause omitted when `lists` is empty (no file, or `lists_unavailable`).
- [ ] Lists tab picker remembers the last choice in `localStorage` `kn.listSel` (try/catch) and opens on it.
- [ ] States E4, E4b, E4c, E6 as specified; the exam card is hidden when `lists` is empty and `lists_unavailable` is false; with `lists_unavailable` the card and the Lists tab show only "Word lists are unavailable right now" and every other card renders; a `LIST_UPDATED` answer reloads the list from its first page.
- [ ] Vitest with a fixture containing one zh list and one ja list, and one with `lists_unavailable: true`.

**Files to Create / Modify:**
- `static/js/pages/knowledge.js`, `templates/knowledge.html`, `static/css/pages/knowledge.css`, `static/i18n/*.json` — modify
- `services/vocabulary/knowledge_report.py` — next-level teaser fields
- `tests/unit/knowledge-page.test.js`, `tests/test_knowledge_report_service.py` — extend

**Verification:** `npx vitest run tests/unit/knowledge-page.test.js`; `python -m pytest tests/test_knowledge_report_service.py -q`.

---

## TASK-1051: "Add these words to my word list" (Pro study action)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1050, TASK-1046

**Description:**
Add the study action of tech §3.4 / ADR-056 to the Lists tab (buckets `no_evidence` and `seen_not_rated`)
and the Missed recently tab: up to 50 lemmas of the current view go to the existing word-list import, so
the ladder shows them in daily practice (P2). One of the four Pro launch gate items.

**Acceptance Criteria:**
- [ ] The button reads "Add these {n} words to my word list" (n ≤ 50: the first n rows of the current view's order, loading more pages if needed) and posts `{words: [lemma…], language: 'zh'|'en'|'ja'}` to `POST /api/word-list/submit` (`routes/word_list_import.py:220-266`).
- [ ] 202 → toast "Added. They will appear in your daily practice." with a link to `/word-list`; 429 → the server's message; the button is disabled while a request is in flight; helper text "Up to 50 words at a time, 5 lists a day."
- [ ] The button is never shown for `not_in_dictionary`, `rated_known` or `my_word_list`.
- [ ] Vitest with a mocked `authFetch` (202 and 429 paths; payload ≤ 50 lemmas); the Playwright smoke never clicks it.

**Technical Notes:** the submit endpoint generates ladder exercises for resolved senses that have none (`services/word_list_import/upload_handler.py:1-20`); that indirect database growth is tracked under OQ30, and the endpoint's own caps apply (`routes/word_list_import.py:77`, `services/word_list_import/batch_limits.py:34`).

**Files to Create / Modify:**
- `static/js/pages/knowledge.js`, `templates/knowledge.html`, `static/i18n/*.json` — modify
- `tests/unit/knowledge-page.test.js` — extend

**Verification:** `npx vitest run tests/unit/knowledge-page.test.js`; locally, add 3 words from a list bucket and see them on `/word-list`.

---

## TASK-1052: Word-list builder and upload script [?]

**Status:** [?] Blocked — needs OQ2 (HSK edition) and OQ3 (licences, list-subset export) answered
**Feature:** knowledge-report
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1049

**Description:**
Write `scripts/build_word_lists.py` (tech §8; ADR-054, revised 2026-11-18): verify a pinned source file,
read `dim_vocabulary` read-only, resolve every headword to a `vocab_id` with the §8 matching rules,
build and validate the version-1 file (tech §5.2), and either write it locally (default dry run) or,
with `--upload`, store it as a new immutable version `word-lists/<list_code>/v<N>.json` in the
`reference-data` bucket. No database writes; no list data committed to the repository. (Replaces the
2026-11-17 SQL-package loader `scripts/load_word_lists.py`, which is not built.)

**Acceptance Criteria:**
- [ ] `SOURCES` in the script pins each list: URL with commit, sha256, licence, attribution, name, edition, `is_official`, `level_codes`, and `allow_export` per OQ3 (default JLPT true, HSK false); a `--source` file whose sha256 differs from the pin is refused.
- [ ] zh and ja rules exactly as tech §8 (homograph digits, optional parts, variants, lowest level, erhua `match_kind` 6; ja kinds 1–5; reading-only homophones unmatched); jamsinclair cleaning (strip `; alt`, `(…)` notes and `～`).
- [ ] HSK 2025 match rates reproduce level-lists research §3.2 (L1 271/300 …) within ±1 percentage point (+13 erhua matches); JLPT (jamsinclair) rates recorded in `match_report.json` and compared with the research table (N5 46.4% … N1 19.4%).
- [ ] The file passes `services/vocabulary/word_lists.validate_word_list` (TASK-1049), every non-null `vocab_id` exists among the `dim_vocabulary` rows read for the list's `language_id`, the file is ≤ 5,242,880 B, and `built_at` / `built_from {dictionary_max_vocab_id, dictionary_lemma_count}` are filled.
- [ ] Default (dry run) writes `data/word_lists/<list_code>/v<N>.json` and `match_report.json` with N = highest version in Storage + 1 (read-only `list`) and makes no `put`; `--upload` puts exactly that content with the never-overwrite `put`; `AlreadyExists` → non-zero exit, no retry; content equal to the latest version except `built_at` → no upload, prints "unchanged".
- [ ] `.gitignore` gains `data/word_lists/`.
- [ ] `tests/test_build_word_lists.py` (new) covers the tech §13 builder cases with `InMemoryBackend` and a fake dictionary read.

**Technical Notes:**
- Parse downloads with `python3 -I`; keep scripts outside the data folder.
- Dictionary read: `id, language_id, lemma, lemma_traditional, reading, frequency_rank` for one language, through PostgREST with the service key, 1,000 rows per page (the PostgREST cap, `services/pagination.py:3-7`); SELECT only.
- Storage: `SupabaseStorageBackend(…, bucket='reference-data')` `list` and `put` only; never `delete`.
- Rebuild (rerun with `--upload`) whenever zh or ja gains lemmas (after each sense-seeding batch; after OQ31's JLPT seeding); there is no `--re-resolve`.
- Expected size (ESTIMATE, tech §5.2): HSK ≈ 0.29 MB, JLPT ≈ 0.30 MB.

**Files to Create / Modify:**
- `scripts/build_word_lists.py`, `tests/test_build_word_lists.py` — new
- `.gitignore` — add `data/word_lists/`

**Verification:** `python -m pytest tests/test_build_word_lists.py -q`; `python -I scripts/build_word_lists.py --list hsk30_2025 --source <downloaded file or folder>` prints the per-level match table, the version it would write and the file size, and writes the file locally (no Storage write).

---

## TASK-1053: Upload the exam lists to Storage [?] (LIVE-STORAGE, owner)

**Status:** [?] Blocked — OQ2 and OQ3 only (the files live in Storage, so no database size gate — ADR-054, revised 2026-11-18)
**Feature:** knowledge-report
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1034, TASK-1052

**Description:** The owner runs the builder with `--upload` for `hsk30_2025` and `jlpt_waller` against
production (a live Storage write; the only database change is Storage's own object metadata, ~0.6 KB
per file), then checks the files and the report.

**Acceptance Criteria:**
- [ ] `python -I scripts/build_word_lists.py --list hsk30_2025 --source <file> --upload` and the same for `jlpt_waller` each print the version written (`v1` the first time) and the per-level match table; both tables are recorded in `wiki/log.md`.
- [ ] Read-only: `SELECT name, (metadata->>'size')::bigint FROM storage.objects WHERE bucket_id = 'reference-data' ORDER BY name` lists `word-lists/hsk30_2025/v1.json` and `word-lists/jlpt_waller/v1.json`, each ≤ 5,242,880 B (≈ 0.3 MB expected, ESTIMATE); the sizes are recorded.
- [ ] `/api/knowledge/summary` for a zh learner returns the HSK list (with `built_at` and `version`) and for a ja learner the JLPT list (locally against production, or in production with the flag on for staff); the time of the first, cold Storage read is recorded.

**Technical Notes:** rerunning is safe (an unchanged build uploads nothing; `put` never overwrites).
To withdraw a bad version the owner deletes that one file; processes fall back to the highest
remaining version at their next 6-hourly check (tech §14).

**Files to Create / Modify:** none in the repo (uploads built files to Storage).

**Verification:** the SQL above (read-only) and a local page check.

---

## TASK-1054: Performance evaluation on live data

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-1036, TASK-1044

**Description:**
Measure the budgets of tech §9 with `EXPLAIN (ANALYZE, BUFFERS)` of read-only SELECTs on the largest real
pair and on a synthetic 26k-row CTE (performance research §5 method), at least three runs each plus the
"healthy host" probe, and write `wiki/evaluations/knowledge-report-perf-<date>.md`.

**Acceptance Criteria:**
- [ ] Summary, `knowledge_frame_bands` and the words page meet the tech §9 budgets on the best warm run, or a follow-up task for the snapshot-plus-delta fallback is filed.
- [ ] No temp-file writes at 26k rows (`work_mem` 2,184 kB).

**Files to Create / Modify:** `wiki/evaluations/knowledge-report-perf-<date>.md` — new (through the wiki owner).

**Verification:** the evaluation page lists every run with its SQL.

---

## TASK-1055: End-to-end smoke and visual fixtures

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-1040, TASK-1046

**Description:** Read-only Playwright smoke and redesign visual-harness entries for E0, E1 and the full Pro view.

**Acceptance Criteria:**
- [ ] `tests/e2e/knowledge-report.spec.js` passes at 390 px and 1280 px: loads, no horizontal scroll, targets ≥ 44 px, Pro section or teaser present; it never clicks "Add these words" or any write action.
- [ ] `tests/e2e/redesign/fixtures/knowledge.json` and a `walk.py` entry render all three states.

**Files to Create / Modify:** `tests/e2e/knowledge-report.spec.js`, `tests/e2e/redesign/fixtures/knowledge.json` — new; `tests/e2e/redesign/walk.py` — modify.

**Verification:** `npx playwright test tests/e2e/knowledge-report.spec.js --trace off`.

---

## TASK-1056: Validate the estimator and the ratings [?]

**Status:** [?] Blocked — needs OQ6 (exclude 110fb390?), TASK-1061 (forced-choice items, OQ5) for part (a), and enough data (≥ 100 distinct senses for part (b); expect months)
**Feature:** knowledge-report
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1035, TASK-1037, TASK-1061

**Description:**
Before the range is used in marketing and before the five-level labels are shown anywhere: (a) what "I
don't know" hides; (b) how often "rated known after a direct check" holds at the next direct check;
(c) whether next-answer accuracy rises across the five `bkt_status` label bands; (d) whether ranges at
10–19 answers per band agree with later estimates. Record in
`wiki/evaluations/knowledge-report-validation-<date>.md` and update ADR-051/ADR-052.

**Acceptance Criteria:**
- [ ] (a) Per band, `K_forced = (c_f/n_f − G)/(1 − G)` on forced items vs the skip-aware `K` on the rest, with the delta-method interval of the difference; the SQL used is on the page.
- [ ] (b) Next-check accuracy of `rated_known` meanings with a sense-clustered interval (tech §2.11 method); n reported as attempts and distinct senses; ≥ 100 distinct senses; if the lower bound is < 0.80, a task to tighten the rule is filed.
- [ ] (c) Next-answer accuracy per label band with clustered intervals; the labels may be shown only if accuracy increases across bands with separated intervals.
- [ ] (d) For every learner who reaches 30 answers per band, the earlier 10–19-per-band range contains the later point estimate.
- [ ] 110fb390 handled per OQ6.

**Files to Create / Modify:** `wiki/evaluations/knowledge-report-validation-<date>.md` — new (through the wiki owner); ADR-051 / ADR-052 status lines.

**Verification:** the evaluation page is reviewed by the owner.

---

## TASK-1057: Documentation reconciliation

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** TASK-1034, TASK-1036, TASK-1038, TASK-1040

**Description:**
Record the live state after the core migrations: new tables and functions, the superseded billing task,
the amended 402 helper, the gate reference in TASK-997, and the calibration pool's staleness.

**Acceptance Criteria:**
- [ ] [[database/schema.tech]] documents `user_knowledge_snapshots` with its measured post-apply size, and the `reference-data` Storage bucket (path layout `word-lists/<list_code>/v<N>.json`, pointer to tech §5.2 for the file schema, measured `storage.objects` rows).
- [ ] [[api/rpcs.tech]] documents the eight new functions (including `knowledge_list_buckets`).
- [ ] [[features/vocabulary-knowledge.tech]] notes the report reads raw values only and that the 2-argument `bkt_effective_p_known` fails on every call.
- [ ] [[features/calibration.tech]] links the report and notes the pool refresh affects the report's denominator.
- [ ] [[tasklist/billing.tasks]]: TASK-993 → "Superseded by TASK-1034–TASK-1071"; TASK-980's `payment_required` amended to TASK-1038's signature; TASK-997 references TASK-1059.
- [ ] `lint` finds no contradiction on `payment_required`, TASK-993 or the Pro gate.

**Files to Create / Modify:** `wiki/database/schema.tech.md`, `wiki/api/rpcs.tech.md`, `wiki/features/vocabulary-knowledge.tech.md`, `wiki/features/calibration.tech.md`, `wiki/tasklist/billing.tasks.md`, `wiki/tasklist/master.md`, `wiki/index.md`, `wiki/log.md`.

**Verification:** run the wiki `lint` operation.

---

## TASK-1058: Enable the report in production (LIVE environment change)

**Status:** [ ] Not Started
**Feature:** knowledge-report
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** TASK-1037, TASK-1040, TASK-1041, TASK-1054

**Description:**
The owner sets `KNOWLEDGE_REPORT_ENABLED=true` on Railway after a staff walkthrough. Everyone gets the
summary; non-Pro learners see the Pro view as a shadow preview as those tasks land. Billing enforcement is
not touched here.

**Acceptance Criteria:**
- [ ] Me row visible; `/api/knowledge/summary` returns 200 for a learner; no new 5xx in `app_error_logs` within 24 h.
- [ ] es/ja/zh copy reviewed (OQ1).
- [ ] A weekly read of the logs counts unique users per `knowledge_pro_intent` action; the first count is recorded in `wiki/log.md`.

**Files to Create / Modify:** none (environment variable).

**Verification:** walkthrough on a phone and a desktop; read-only `app_error_logs` query.

---

## TASK-1059: Pro launch gate [?] (owner)

**Status:** [?] Blocked — needs TASK-1053 (OQ2, OQ3; no longer the database size gate OQ13 — ADR-054, revised 2026-11-18) and the owner's acceptance of the gate (OQ28)
**Feature:** knowledge-report
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** TASK-1046, TASK-1048, TASK-1051, TASK-1053

**Description:**
`bkt_report_detail` is not enforced, and the report is not named as a Pro benefit on the pricing page,
until this gate passes (ADR-055; tech §14 step 6). Billing TASK-997 must not enable enforcement for this
key before it.

**Acceptance Criteria:**
- [ ] (1) The HSK 2025 list file is uploaded to Storage (TASK-1053) and its card shows for a zh learner in production.
- [ ] (2) "Add these words to my word list" returns 202 from the Lists and Missed recently tabs.
- [ ] (3) A filtered CSV, a list-level CSV (JLPT; HSK only if `allow_export`) and an Anki file export and open correctly.
- [ ] (4) Every Pro row leads with evidence; no five-level label or numeric rating is visible.
- [ ] The owner records "Knowledge Report Pro gate passed" with the date in `wiki/log.md`; TASK-1056's status is noted (required before the range itself appears in marketing).

**Files to Create / Modify:** `wiki/log.md` (through the wiki owner).

**Verification:** the walkthrough above on production with a Pro-level account.

---

## TASK-1060: Import not-in-dictionary words with credits [?]

**Status:** [?] Blocked — billing's credit spend path (`spend_credits(8, 'sense_import')`, `wiki/business/pricing-plan.tech.md:401`) does not exist yet; OQ30 (database growth) and the size gate
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1051

**Description:** A separate button on the `not_in_dictionary` bucket: "Add {n} new words ({n} × 8 credits)",
which spends credits and submits the headwords through the import path that creates senses.

**Acceptance Criteria:**
- [ ] The quote shows the exact credit cost and the learner's balance before submit; insufficient credits → the 402 paywall payload.
- [ ] Credits are spent only for senses actually created (refund on failure), per billing's ledger rules.
- [ ] `pg_database_size` impact per created sense measured on the first 20 words and recorded.

**Files to Create / Modify:** `static/js/pages/knowledge.js`, `routes/word_list_import.py` (credit hook, coordinated with billing), billing service files named by the billing task.

**Verification:** to be finalised with the billing credit task; a local run with a test balance.

---

## TASK-1061: Calibration forced-choice probe items [?] (LIVE-DB)

**Status:** [?] Blocked — OQ5 (owner approval of a Calibration change)
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
To measure what "I don't know" hides (S4), hide the skip button on a random 1 in 8 definition-mode items
per band and record which items allowed a skip. The headline estimator needs no change: with no skips its
formula reduces to the standard `(c/n − G)/(1 − G)`.

**Acceptance Criteria:**
- [ ] Migration adds `calibration_responses.skip_allowed boolean NOT NULL DEFAULT true` (+ rollback); owner applies.
- [ ] The item builder marks ~1 in 8 items per band `skip_allowed = false`; the page hides the skip button for them and explains "Choose your best guess".
- [ ] Analysis SQL for TASK-1056(a) documented.
- [ ] Alternative (if the owner prefers it): two skip buttons, "Never seen it" / "Seen it, not sure", recorded in a `skip_kind` column — one of the two designs is built, not both.

**Files to Create / Modify:** `migrations/calibration_skip_allowed.sql` + rollback; `services/calibration_service.py`; `routes/calibration.py`; `static/js/pages/calibration.js`; `static/i18n/*.json`; tests for the builder.

**Verification:** a local session shows forced items at about the expected rate; responses carry `skip_allowed`.

---

## TASK-1062: Calibration selector — one lemma, rank-1 sense [?] (LIVE-DB)

**Status:** [?] Blocked — OQ9 (owner approval of a live Calibration function change)
**Feature:** knowledge-report
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Change `calibration_next_anchors` to draw a lemma uniformly within band and serve its rank-1 sense, so every
definition-mode answer counts toward the estimate (S9; today 38% of en/en pool items test a rank > 1 meaning).

**Acceptance Criteria:**
- [ ] Function replaced with identical signature and volatility; band round-robin unchanged; rollback restores the current body.
- [ ] Read-only check: for en/en, 0% of newly served anchors have `sense_rank > 1`.

**Files to Create / Modify:** `migrations/calibration_next_anchors_rank1.sql` + rollback; `wiki/features/calibration.tech.md` (through TASK-1057 or its own docs step).

**Verification:** serve 50 anchors in a local session against production (read-only check of served rows afterwards).

---

## TASK-1063: Refresh the zh calibration anchor pool [?] (LIVE-DB data)

**Status:** [?] Blocked — OQ29 and the size gate (≈ 5–7 MB, ESTIMATE from 369 B per pool row and 215 B per cache row)
**Feature:** knowledge-report
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The zh pool covers 3,643 of 12,802 zh lemmas because it was not refreshed after the October–November
seeding (`wiki/features/calibration.tech.md:667-675`). Refresh it so the zh/zh frame covers the dictionary.

**Acceptance Criteria:**
- [ ] `PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --refresh-pool` and the cache fill run; `--coverage` output recorded.
- [ ] Pool and cache bytes before and after recorded in `wiki/log.md`.
- [ ] `knowledge_frame_bands()->'1:1'` sums to ≥ 12,000; the growth card shows the pool-change notice for zh learners with snapshots.

**Files to Create / Modify:** none (data refresh through existing scripts).

**Verification:** the read-only `knowledge_frame_bands()` and size queries above.

---

## TASK-1064: Targeted practice of an explicit word set [?]

**Status:** [?] Blocked — OQ15 (scope with the Practice owner)
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1046, TASK-1050

**Description:** Let Practice accept an explicit set of meanings ("Drill these 10") — `routes/practice.py:44-80`
has no such input — and add the button to Missed recently and Lists, respecting `new_words_per_day`.

**Acceptance Criteria:**
- [ ] Specified with the Practice owner before work starts (API param, cap, interaction with today's budget).

**Files to Create / Modify:** `routes/practice.py`, `services/practice_session_service.py`, `static/js/session/controller.js`, `static/js/pages/knowledge.js`.

**Verification:** defined with the specification.

---

## TASK-1065: Evidence-kind counters or an evidence log [?] (LIVE-DB)

**Status:** [?] Blocked — OQ16 (worth changing the seven writer functions?) and the size gate
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** none

**Description:** Separate direct, contextual, inferred and lapse updates (data-audit research §3), so rows can
say "inferred" precisely and growth can count words newly rated known. Sizing: ~120 B per event.

**Acceptance Criteria:**
- [ ] Its own ADR, then a migration plan with a byte estimate at 1,000 learners.

**Files to Create / Modify:** to be listed in the ADR.

**Verification:** to be listed in the ADR.

---

## TASK-1066: Decay function clean-ups [?] (LIVE-DB)

**Status:** [?] Blocked — OQ14 (owner approval for a live change with no staging)
**Feature:** knowledge-report
**Type:** refactor
**Complexity:** S (1-3h)
**Depends On:** none

**Description:** Change `bkt_apply_decay` (both overloads) and `bkt_effective_p_known` from IMMUTABLE to STABLE,
and drop the 2-argument `bkt_effective_p_known` overload that fails on every call (performance research §3).
Not needed by the report (it calls no decay function).

**Acceptance Criteria:**
- [ ] The four live callers (`get_session_senses`, `get_practice_session`, `get_review_ahead_items`, `compute_weekly_plan_load_signals`) return identical results on a read-only comparison before and after; no caller uses the 2-argument form (catalog regexp check).

**Files to Create / Modify:** `migrations/bkt_decay_volatility_fix.sql` + rollback.

**Verification:** catalog query shows `provolatile = 's'`; caller comparison recorded.

---

## TASK-1067: Frequency-aware decay and a model review flag [?]

**Status:** [?] Blocked — OQ17 (its own ADR and validation data)
**Feature:** knowledge-report
**Type:** refactor
**Complexity:** XL (>2d)
**Depends On:** TASK-1065, TASK-1066

**Description:** Frequency-aware decay target, no floor lift, an FSRS-consistent curve, updates from effective p
(data-audit research §2.2); then, if validated, an inlinable as-of helper and a model-based "review soon" flag
in the report under the "Model" prefix (ADR-052 revisited).

**Acceptance Criteria:**
- [ ] Its own ADR with validation on held-out answers; changes Practice for everyone.

**Files to Create / Modify:** to be listed in the ADR.

**Verification:** to be listed in the ADR.

---

## TASK-1068: Learner corrections on the word sheet [?]

**Status:** [?] Blocked — OQ18 (should self-reports write BKT state?)
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1047

**Description:** "I know this" / "I don't know this" on the word sheet. `user_marked_unknown` exists but has no
writer; "I know this" would be new, shown as self-reported and never counted as rated known.

**Acceptance Criteria:**
- [ ] Specified after OQ18 (write path, display, effect on snapshots).

**Files to Create / Modify:** to be listed after OQ18.

**Verification:** to be listed after OQ18.

---

## TASK-1069: Today card [?]

**Status:** [?] Blocked — OQ19 (placement on Today)
**Feature:** knowledge-report
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1040

**Description:** A compact card on Today with one fact and one action, using the same definitions as the page
(e.g. "10 words missed recently · Review in Practice").

**Acceptance Criteria:**
- [ ] Specified after OQ19; no number may differ from the page's.

**Files to Create / Modify:** to be listed after OQ19.

**Verification:** to be listed after OQ19.

---

## TASK-1070: "Upcoming tests" coverage card (Pro) [?]

**Status:** [?] Blocked — OQ32
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1041, TASK-1046

**Description:** For each recommended test, the share of its key words that are new to the learner
(`services/prestudy.share_plan`), with a plain-language reading of coverage and a prestudy link.

**Acceptance Criteria:**
- [ ] Specified after OQ32, reusing `plan_for_tests`; no pass or readiness claim.

**Files to Create / Modify:** to be listed after OQ32.

**Verification:** to be listed after OQ32.

---

## TASK-1071: Estimated percentage per exam level [?]

**Status:** [?] Blocked — OQ34 and TASK-1056
**Feature:** knowledge-report
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1050, TASK-1056

**Description:** If approved after validation, add the estimate of tech §2.8a (frame items only, no double
counting, item-level variance, pooled per band for cumulative levels), shown beside — never added to — the
rated-known count, with the copy "If these words are like other words of the same frequency, you would know
about X–Y% of them."

**Acceptance Criteria:**
- [ ] Formula and copy exactly as tech §2.8a; unit tests in `tests/test_knowledge_estimate.py`.

**Files to Create / Modify:** `services/vocabulary/knowledge_estimate.py`, `migrations/knowledge_report_list_words.sql` (`knowledge_list_buckets` also returns per-band frame counts per level, from the same arrays), `static/js/pages/knowledge.js`, `static/i18n/*.json`.

**Verification:** `python -m pytest tests/test_knowledge_estimate.py -q`.

---

## TASK-1072: Goal-path layout (mockup C) in the spec and the page [?]

**Status:** [?] Blocked — OQ35 (where the goal and exam date are stored) and OQ36 (per-level 30-day change)
**Feature:** knowledge-report
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1040, TASK-1046, TASK-1050, TASK-1037

**Description:**
The owner prefers the goal-path design (`wiki/demos/knowledge-report-goal-path.html`). Rewrite tech §3 and §10 to that
order (estimate hero first; goal card with ring, focus level and exam date; level path with in-place drill-down; next
steps; this week; keep missing; read next; how you answer; 13 weeks; your lists; all words / export / method) and
build it on top of the cards from TASK-1040 and TASK-1046. Add the goal setting (level and optional exam date per study
language) and, if OQ36 is accepted, per-level counts in the snapshot so each level can show "+N rated known in the last
30 days". Core sees counts with a Pro row wherever Pro shows the words.

**Acceptance Criteria:**
- [ ] Tech §3/§10 describe the goal-path order and the Core gating shown in the mockup.
- [ ] The goal sheet saves a level and an optional date; the focus level is the lowest level up to the goal under 80% rated known.
- [ ] The exam countdown shows only a date the learner entered; no pass or readiness prediction anywhere.
- [ ] Per-level 30-day change is hidden until 30 days of snapshots exist.

**Technical Notes:** goal storage per OQ35; snapshot change per OQ36 (extends ADR-053's row). The mockup's JavaScript is
a layout reference only, not production code.

**Files to Create / Modify:** to be listed after OQ35/OQ36 (expected: `templates/knowledge.html`,
`static/js/pages/knowledge.js`, `static/css/pages/knowledge.css`, the snapshot migration, i18n files).

**Verification:** visual comparison with the mockup at 390 px in both themes; Playwright smoke from TASK-1055.

---

## TASK-1073: Vocabulary placement test — research and design [?]

**Status:** [?] Blocked — OQ37 (owner: run the research brief first)
**Feature:** knowledge-report
**Type:** docs
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Research approaches to a short, adaptive vocabulary placement test built on the existing vocabulary check
([[features/calibration]]: open-ended, stratified by frequency band, four-option meaning items, no stopping rule), and
write a feature spec and ADR. Candidate designs and the research brief are below.

**Acceptance Criteria:**
- [ ] A comparison of at least five designs against the owner's criteria (minutes, honesty of the result, exam-level output, item-bank cost, cold start for new learners).
- [ ] A recommended design with stopping rule, scoring model, item bank, validation plan, and how its result feeds the report and practice.

**Technical Notes — candidate designs (2026-11-18, not evaluated):**
1. *Adaptive vocabulary check:* the existing four-option meaning items, chosen adaptively at the learner's edge with an
   IRT model (guessing floor 0.25; starting difficulty from frequency, recalibrated from responses), stopping when the
   range is narrow enough (~25–40 items). Cheapest; reuses the check's pool, distractors and tables.
2. *Exam-level ladder:* items drawn from HSK/JLPT level lists; start at the learner's stated level and move a level up or
   down after short blocks; output per-level known shares (the sampling OQ34 needs). Weak for JLPT (low dictionary coverage).
3. *Yes/No with fake words:* tap "I know it" on 60–100 words, about a third of them fake; correct for false alarms.
   Fastest (~3 min); needs credible Chinese/Japanese fake words; self-report.
4. *Hybrid:* a Yes/No sweep to find the edge, then 15–20 meaning checks on "yes" words near it to measure and correct
   overclaiming.
5. *Read and tap:* 2–3 short graded passages; tap unknown words and answer two questions. Measures text coverage and sets
   the starting test level; self-report and fewer words covered.
6. *Embedded placement:* no separate test; one probe in eight in the first week's practice until the range converges.
Cross-cutting: "known" must mean recognition to match the report; Japanese↔Chinese learners recognise many words through
shared characters, so difficulty needs an L1 term; placement evidence must be stored as its own kind (TASK-1065) and
never counted as "rated known"; retakes use disjoint items.

**Research brief (paste into a research agent):**

```text
Research brief: a vocabulary placement test for LinguaDojo

Goal: recommend how LinguaDojo should place a learner's vocabulary in 3–8 minutes on a phone, with an honest result that (1) gives a vocabulary range on day one, (2) places them on HSK 3.0 or JLPT levels, and (3) can seed practice without pretending to know more than it does. Compare approaches; do not assume the answer.

Context (facts about the product):
- Study languages: Chinese, Japanese, English. Learners' own languages: English, Japanese, Chinese (UI also in Spanish). Serious adult learners preparing for HSK 3.0 (2025 syllabus: levels 1–6 plus a combined 7–9), JLPT N5–N1 (no official lists since 2010; community lists used), or professional work. The product must not feel gamified and must never predict pass/fail.
- An existing "vocabulary check" shows a word and four meanings (wrong options chosen to be semantically close and similar in frequency) or four readings, plus "I don't know". It samples evenly across 7 frequency bands (wordfreq Zipf, 0.5 wide), has no stopping rule, and needs about 70 answers (10 per band) before it shows a range. Scoring: per-band share known = right/n − (1/3)·wrong/n (guess correction, skip = not known), a finite-population interval, and band sizes from the check's word pool (Japanese 3,175 words, Chinese 3,623, English 3,754).
- Dictionary: about 3.4k Japanese, 12.8k Chinese and 4.2k English lemmas with frequency. HSK 2025 levels 1–5 are 88–92% in the dictionary, JLPT levels only 18–49%.
- A per-word Bayesian knowledge tracing model exists, but its probabilities are not calibrated, so the report leads with measured evidence. An IRT module exists in the codebase.
- Constraints: little user data so far (validation must work with small n); no paid model calls needed to score a test; the database is near its size limit (large item tables need justification).

Research questions:
1. Literature on vocabulary size and breadth tests: Vocabulary Size Test, (New) Vocabulary Levels Test, Yes/No tests with pseudowords (Meara; LexTALE and its Chinese and Japanese versions, if any), Japanese and Chinese specific instruments (e.g. J-CAT, SPOT/TTBJ, Chinese vocabulary size tests), and computerised adaptive testing for vocabulary (Rasch/2PL/3PL with a guessing floor, stopping rules, exposure control). What does each measure, in how many items, with what reliability, and how well does it predict reading or exam level?
2. Products: how Duolingo (including the Duolingo English Test's adaptive Yes/No and C-test items), Busuu, Babbel, HelloChinese, LingoDeer, Hack Chinese, Skritter, WaniKani, Bunpro, Renshuu, jpdb, Migaku and LingQ place learners: format, length, what they show afterwards, how they handle uncertainty and retakes.
3. Format trade-offs: meaning multiple choice vs Yes/No self-report with fake words vs typed recall vs reading a passage and tapping unknown words. Overclaiming and guessing corrections (formulas), distractor quality effects, recognition vs recall, polysemy (word vs sense).
4. Chinese and Japanese specifics: making credible fake words from real characters; the cognate effect when Japanese speakers learn Chinese and vice versa (shared characters), and katakana loanwords for English speakers; whether to show readings, kanji only, or audio.
5. Adaptive design: item selection by frequency band and by exam level from one item bank; cold-start item difficulties from frequency and level, then recalibration from responses; stopping rules that give a usable range in under 40 items; how many items for a given interval width (simulate).
6. Using the result: reporting a range and per-level estimates honestly; seeding a knowledge-tracing model as clearly labelled prior evidence rather than as known words; setting the starting difficulty of reading tests; retakes with disjoint items.
7. Validation with small numbers of users: test-retest, predictive checks against later first-try accuracy, agreement with self-reported exam level.

Deliverables:
- An annotated bibliography with links (mark paywalled or unverified sources).
- A product comparison table.
- At least five candidate designs scored on: minutes, honesty and width of the result, exam-level output, item-bank cost per language, behaviour for complete beginners and for advanced learners, Chinese/Japanese cross-language cognates, build effort given the existing check.
- One recommended design with: item formats; selection algorithm; scoring model with formulas; stopping rule; expected items and minutes from a simulation; item-bank requirements per language; what the learner sees afterwards; how results feed the report, practice and test selection; validation plan; risks; open questions.
- Separate measured facts from inference, and cite a source for every claim.
```

**Files to Create / Modify:** `wiki/features/vocab-placement.md`, `wiki/features/vocab-placement.tech.md`, an ADR.

**Verification:** owner review.

---
