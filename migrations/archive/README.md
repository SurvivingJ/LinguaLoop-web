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
| `process_test_submission_v2.sql` | `process_test_submission(...)` | `partF_question_attempt_results.sql` | `question_attempt_results` insert present |
| `process_test_submission_reduced_repeats.sql` | `process_test_submission(...)` | `partF_question_attempt_results.sql` | `question_attempt_results` insert present |
| `phase14_test_kfactor_decay.sql` | `process_test_submission(...)` | `partF_question_attempt_results.sql` | `question_attempt_results` insert present (see CR-04 caveat below) |
| `fix_get_recommended_tests_signature.sql` | `get_recommended_tests(uuid,smallint)` | `add_pitch_accent_to_get_recommended_tests.sql` | pitch_accent + pinyin + dictation filter present |
| `add_pinyin_to_get_recommended_tests.sql` | `get_recommended_tests(uuid,smallint)` | `add_pitch_accent_to_get_recommended_tests.sql` | pitch_accent present |
| `update_get_recommended_tests_for_dictation.sql` | `get_recommended_tests(uuid,smallint)` | `add_pitch_accent_to_get_recommended_tests.sql` | pitch_accent present |
| `get_distractors_drop_auth_check.sql` | `get_distractors(integer,smallint,integer)` | `get_distractors_filter_standard_level.sql` | standard-level filter + `auth.uid` present |
| `restore_get_distractors_auth_check.sql` | `get_distractors(integer,smallint,integer)` | `get_distractors_filter_standard_level.sql` | standard-level filter + `auth.uid` present |
| `phase13_build_daily_session_test_objs.sql` | `build_daily_session(uuid,smallint,date)` | `phase13_build_daily_session_classifier_drill.sql` | `classifier_drill` present |

## Note: CR-04 drift parked in `phase14_test_kfactor_decay.sql`

The 2026-06-06 audit row above keyed canonicality on `v_test_k_factor`, but that
marker does **not** distinguish two divergent bodies. The live
`process_test_submission` (probed 2026-06-06 via `pg_get_functiondef`) uses a
`CREATE TEMP TABLE` for response staging, `RAISE EXCEPTION` on unauthorized, and
returns raw `SQLERRM`/`SQLSTATE` in its error envelope. `phase14_test_kfactor_decay.sql`
instead carries the **CR-04 hardening** — `jsonb_to_recordset` staging, a typed
`error_code` envelope, and masked `SQLERRM` — which **was never applied to live**.

The new canonical `partF_question_attempt_results.sql` is therefore based on the
*live* (non-CR-04) body plus the additive per-question `question_attempt_results`
capture — a deliberate, strictly-additive choice (Part F decision, 2026-06-06).
The CR-04 version is preserved **only** in this archived `phase14_*.sql` file: if
the team wants to land CR-04 on live (the route at `routes/tests.py` and
`tests/test_submission_rpc_error_envelope.py` already expect the typed envelope),
re-derive it from there into a new migration on top of the Part F body.

## Note: orphan column

`process_test_submission_reduced_repeats.sql` was the only migration that ran
`ALTER TABLE public.test_attempts ADD COLUMN elo_reduction_factor`. That column
**still exists in the live DB** but is no longer written by the live
`process_test_submission` (phase14 dropped the reduced-volatility repeat path).
It is an orphan column — recorded here so the history isn't lost. If a future
cleanup drops it, do so in a new migration; it is not currently in
`db_schema_live.sql`.
