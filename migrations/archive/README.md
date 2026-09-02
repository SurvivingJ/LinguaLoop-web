# Archived migrations

Files here have been **superseded**: every database object they define
(function signature / column) is now defined by a newer migration that was
verified against the live Supabase DB (project `kpfqrjtfxmujzolwsvdq`). They are
kept for history only — **do not re-run them** and do not treat them as the
current definition of anything.

Determining staleness (2026-06-06 audit): for each function defined in more than
one migration, the live `pg_get_functiondef(...)` body was probed for a
distinguishing marker to identify the single canonical file; every *other*
single-purpose file defining only that function was archived. Multi-object
migrations (e.g. `phase*.sql`, `bkt_vocabulary_tracking.sql`,
`elo_functions.sql`) were **kept** even when one of their objects was superseded,
because they remain the sole repo record of other still-live objects.

| Archived file | Defined object | Now lives in (canonical) | Live marker checked |
|---|---|---|---|
| `process_test_submission_v2.sql` | `process_test_submission(...)` | `task704_process_test_submission_retry_elo.sql` | `elo_reduction_factor` in INSERT + `slot_type='retry'` scan present (TASK-704) |
| `process_test_submission_reduced_repeats.sql` | `process_test_submission(...)` | `task704_process_test_submission_retry_elo.sql` | `elo_reduction_factor` in INSERT + `slot_type='retry'` scan present (TASK-704) |
| `phase14_test_kfactor_decay.sql` | `process_test_submission(...)` | `task704_process_test_submission_retry_elo.sql` | `elo_reduction_factor` in INSERT + `slot_type='retry'` scan present (TASK-704; see CR-04 caveat below) |
| `fix_get_recommended_tests_signature.sql` | `get_recommended_tests(uuid,smallint)` | `task702_get_recommended_tests_rank_cap.sql` | `rank_in_type <= 10` present |
| `add_pinyin_to_get_recommended_tests.sql` | `get_recommended_tests(uuid,smallint)` | `task702_get_recommended_tests_rank_cap.sql` | `rank_in_type <= 10` present |
| `update_get_recommended_tests_for_dictation.sql` | `get_recommended_tests(uuid,smallint)` | `task702_get_recommended_tests_rank_cap.sql` | `rank_in_type <= 10` present |
| `add_pitch_accent_to_get_recommended_tests.sql` | `get_recommended_tests(uuid,smallint)` | `task702_get_recommended_tests_rank_cap.sql` | `rank_in_type <= 10` present (TASK-702) |
| `get_distractors_drop_auth_check.sql` | `get_distractors(integer,smallint,integer)` | `get_distractors_filter_gloss_language.sql` | standard-level filter + `auth.uid` present |
| `restore_get_distractors_auth_check.sql` | `get_distractors(integer,smallint,integer)` | `get_distractors_filter_gloss_language.sql` | standard-level filter + `auth.uid` present |
| `get_distractors_filter_standard_level.sql` | `get_distractors(integer,smallint,integer)` | `get_distractors_definition_language_param.sql` | `dws.definition_language_id = p_language_id` predicate present (gloss-row exclusion, 2026-08-23) |
| `get_distractors_filter_gloss_language.sql` | `get_distractors(integer,smallint,integer,smallint)` | `get_distractors_definition_language_param.sql` | `p_definition_language_id` 4th param + `v_def_lang` present (2026-08-24) |
| `phase13_build_daily_session_test_objs.sql` | `build_daily_session(uuid,smallint,date)` | `task702_build_daily_session.sql` | `requested_counts` / `slot_type='replay'` present |
| `phase13_build_daily_session_classifier_drill.sql` | `build_daily_session(uuid,smallint,date)` | `task702_build_daily_session.sql` | `requested_counts` / `slot_type='replay'` present (TASK-702) |
| `phase12_deprecation_wrappers.sql` | `get_exercise_session(...)`, `get_ladder_session(...)` | *(dropped — no canonical)* | both `DROP`ped by `phase17_drop_deprecation_wrappers.sql` (TASK-220) |
| `phase13_record_session_progress.sql` | `record_session_progress(uuid,smallint,uuid,text,text,int,int)` | `phase18_practice_time_seconds.sql` | 8-arg signature with `p_delta_seconds`; accrues `practice_completed_*_sec` and derives `*_min` (TASK-701) |

## Note: CR-04 drift parked in `phase14_test_kfactor_decay.sql`

The 2026-06-06 audit row above keyed canonicality on `v_test_k_factor`, but that
marker does **not** distinguish two divergent bodies. The live
`process_test_submission` (probed 2026-06-06 via `pg_get_functiondef`) uses a
`CREATE TEMP TABLE` for response staging, `RAISE EXCEPTION` on unauthorized, and
returns raw `SQLERRM`/`SQLSTATE` in its error envelope. `phase14_test_kfactor_decay.sql`
instead carries the **CR-04 hardening** — `jsonb_to_recordset` staging, a typed
`error_code` envelope, and masked `SQLERRM` — which **was never applied to live**.

Canonical for `process_test_submission` moved from `partF`/`partG` to
`task704_process_test_submission_retry_elo.sql` on 2026-07-19 (TASK-704). That
file is the *live* (non-CR-04) partG body verbatim, plus the re-landed ADR-006
reduced-volatility retry-slot ELO path in the repeat-attempt branch. `partG`
stays canonical for the `question_attempt_results` `response_time_ms` column
drop (multi-object, not archived); it is simply no longer the newest definer of
the function. The CR-04 version is still preserved **only** in the archived
`phase14_*.sql`: if the team wants to land CR-04 on live (the route at
`routes/tests.py` and `tests/test_submission_rpc_error_envelope.py` already
expect the typed envelope), re-derive it on top of the TASK-704 body.

## 2026-08-07 — TASK-714 / TASK-715 / TASK-716

| Archived file | Object | New canonical file | Marker verified on live |
|---|---|---|---|
| `task702_build_daily_session.sql` | `build_daily_session(uuid,smallint,date)` | `task714_build_daily_session_surfaces.sql` | `surface_counts` key in the return jsonb; `pg_temp.surface_budget` in the body |
| `task702_get_recommended_tests_rank_cap.sql` | `get_recommended_tests(uuid,smallint)` | `task715_get_recommended_tests_tier_cap.sql` | `public.dictation_max_words(t.difficulty)` replaces `v_dictation_max_words CONSTANT` |

Both were single-object files fully superseded by the newer definitions, which
were applied live and confirmed by round-tripping the resolver (a seeded plan
returned `surface_counts` for both new kinds) and by
`public.dictation_max_words(1..9)` returning the per-tier ladder 80→400.

## 2026-08-24 — TASK-732

| Archived file | Object | New canonical file | Marker verified on live |
|---|---|---|---|
| `task714_build_daily_session_surfaces.sql` | `build_daily_session(uuid,smallint,date)` | `task732_build_daily_session_split_budget.sql` | `v_test_budget`/`v_practice_budget` present; body has two `FOR v_cand IN ... WHERE kind IN (...)` loops instead of one combined loop |

Single-object file fully superseded by the newer definition, applied live and
confirmed by round-tripping the resolver for a real account: practice
(`practice_acquisition_min`) went from 0 on every prior `daily_test_loads` row
(back to 2026-05-22) to a nonzero value on the first post-migration call, for
both of that account's language plans, with `test_budget_minutes` /
`practice_budget_minutes` visible in the returned jsonb confirming the split.

**Not archived, deliberately** (rule #4 — each is still the sole repo record of
another live object):

- `phase13_build_daily_session.sql` — its `test_time_estimate` body is now
  superseded by `task715_test_time_estimate_tiered.sql`, but it remains the only
  file defining `public.week_start_for(date)`.
- `phase18_practice_time_seconds.sql` — its `record_session_progress` body is
  now superseded by `task716_local_day_boundary.sql`, but it remains the only
  file defining the `weekly_plan_states.practice_completed_maint_sec` /
  `practice_completed_acq_sec` columns. The seconds-ledger behaviour it
  introduced is carried forward verbatim in the new body.

## task715_get_recommended_tests_tier_cap.sql — superseded 2026-08-30

`public.get_recommended_tests(uuid, smallint)` is now canonically defined by
`migrations/task740_phase5b_topic_recency_exclusion.sql` (TASK-740 Phase 5b,
ADR-023), which adds a third, DEFAULT-valued `p_topic_recency_days`
parameter and a topic-recency exclusion clause. Verified against the live
`pg_get_functiondef` for the new signature and the `NOT EXISTS ... t2.topic_id
= t.topic_id` marker before archiving.

## Note: elo_reduction_factor column — no longer orphaned

`process_test_submission_reduced_repeats.sql` first added
`ALTER TABLE public.test_attempts ADD COLUMN elo_reduction_factor`. From
2026-06-06 to 2026-07-19 that column was an **orphan** (present but unwritten,
after phase14 dropped the reduced-volatility path). TASK-704
(`task704_process_test_submission_retry_elo.sql`) **re-lands the ADR-006 path**,
so the column is written again — the applied factor on an eligible daily-load
retry-slot repeat, NULL otherwise. It is no longer orphaned; do not drop it.
