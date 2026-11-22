---
title: Knowledge Report and Vocabulary placement — apply and launch runbook
type: overview
status: in-progress
last_updated: 2026-11-22
---

# Knowledge Report and Vocabulary placement — apply and launch runbook

The code and migration files are built on branch `claude/beautiful-planck-0fftk4` (2026-11-19). **Phases 0, 1 and
the Phase 2 migrations were applied live on 2026-11-22** (see "Applied 2026-11-22" below); the Phase 2 data steps, the
owner smoke test and Phase 3 remain. This page is the owner's ordered checklist: what to apply, what each step
should print, and when to turn the features on. Specs: [[features/knowledge-report.tech]],
[[features/vocab-placement.tech]]. Tasks: [[tasklist/knowledge-report.tasks]], [[tasklist/vocab-placement.tasks]].

All migrations were applied **in this order** to one fresh local PostgreSQL 16 database (UTF8) holding the live
DDL and a real sample of the word pool, and every SQL suite passed there: `tests/sql/test_calibration_placement.sql`
(13 checks), `tests/sql/test_knowledge_calibration_inputs.sql` (5), `tests/sql/test_knowledge_report.sql` (94,
with the real `knowledge_calibration_inputs`, not the stub). The Python placement service was then driven end to
end against that database (zh, ja, en, a learner with tone trouble, End now, abandon, retake).

Record `SELECT pg_database_size(current_database())` before Phase 1 and after Phase 2 (358.4 MB on 2026-11-19;
expected growth well under 1 MB).

## Applied 2026-11-22

- 0.1, 1.1, 1.2 and 1.3 parts 1–3 by the agent (Supabase MCP); 1.3 part 4 (`_answer`, `_close`, `_close_stale`,
  the lock-down block) and 1.4–1.9, 2.1, 2.2 by the owner in the SQL editor (the MCP's destructive-statement
  prompt timed out on the `DELETE`s inside function bodies).
- 1.2 needed one change: live has the `intarray` extension, which makes `smallint[] <@ smallint[]` ambiguous
  (42725); the CHECK now says `OPERATOR(pg_catalog.<@)`.
- All 46 functions the 12 files define compare equal to the local harness that passed the SQL suites (md5 of body,
  config, security, volatility and result type; the editor's CRLF line endings ignored). Two zh helpers
  (`calibration_normalise_pronunciation`, `calibration_zh_parse_pinyin`) hold the tone marks as literal characters
  where the files write `\uXXXX` regex escapes: the MCP turns `\u` sequences into characters before the SQL reaches
  the database. Same results (checked on 20,000 zh readings); re-paste those two from the files in the SQL editor if
  byte equality matters.
- Security checks: no violation from any new object; every new function is service role only. **Pre-existing,
  not from these migrations:** check 5 of `tests/sql/check_function_acls.sql` lists `anon` SELECT on 28 public
  tables (among them `users`, `user_tokens`, `token_transactions`, `trusted_devices`, `app_error_logs`); RLS is on
  for all of them. Needs its own look.
- Checks: normaliser fixtures `yuan2xing2`, `nü3er2`, `ying4yong4`, `いんく`; tones 381 inventory rows, 2,379
  character readings, 好 → `{háo}`; `relfilenode` 179439 / 179461 unchanged; `knowledge_frame_bands()->'3:2'` =
  `[577,425,621,655,537,283,77]`; 5 active pairs; de6fd05b/ja words `matching` = 251 and the summary returns;
  `reference-data` bucket private, 5 MB, JSON; new tables ≈ 0.35 MB. Ready counts: en (2, 2) 3,753 / 3,754;
  ja (3, 2) 2,099 / 3,175 = 66% (expected before the Phase 2 data steps); zh (1, 2) over the MCP timeout (SQL editor).
- Database 361.9 MB after (358.4 MB on 2026-11-19; the new objects account for ≈ 0.35 MB, the rest is three days of
  other activity).

Still to do: `python scripts/verify_placement_rpcs.py --user <test account>` (no test account identified), the zh
gate, Phase 2 steps 2–5, Phase 3.

## Phase 0 — bug fix, independent (any time)

| # | File | Task | Check after applying |
|---|---|---|---|
| 0.1 | `migrations/calibration_zh_normaliser_fix.sql` | TASK-1074 | the VERIFY query in its header: `syllable_count_zero = 0` and `not_numbered = 0` in both groups; `tests/sql/check_function_acls.sql` returns nothing |

## Phase 1 — schema and functions (in this order)

| # | File | Task | Notes / check |
|---|---|---|---|
| 1.1 | `migrations/calibration_placement.sql` | TASK-1076 | additive columns, no table rewrite (`relfilenode` 179439 / 179461 unchanged) |
| 1.2 | `migrations/calibration_zh_tones.sql` | TASK-1092 | NOTICE ≈ 381 inventory rows and ≈ 2,379 character-reading rows; header VERIFY (好 gives `{háo}`); then `python scripts/verify_zh_tone_variants.py` → 0 mismatches, ≈ 99.0% of pool readings with a variant (band 7 ≈ 94.8%) |
| 1.3 | `migrations/calibration_placement_rpcs.sql` | TASK-1077 | refuses to run without 1.1 and 1.2 |
| 1.4 | `migrations/knowledge_calibration_inputs.sql` | TASK-1079 | needs 1.1 |
| 1.5 | `migrations/knowledge_report_foundation.sql` | TASK-1034 | `SELECT knowledge_frame_bands()->'3:2'` = `[577,425,621,655,537,283,77]`; `knowledge_active_pairs(now() - interval '180 days')` returns 5 pairs today |
| 1.6 | `migrations/reference_data_bucket.sql` | TASK-1034 | `storage.buckets` row `reference-data`, private, 5 MB, `application/json` |
| 1.7 | `migrations/knowledge_report_words.sql` | TASK-1044 | per sort, `matching` = 251 for de6fd05b/ja (as of 2026-11-19) |
| 1.8 | `migrations/knowledge_report_summary.sql` | TASK-1036 | refuses without 1.4; compare `knowledge_report_summary(<de6fd05b>, 3)` with a same-day re-run of the K3/K4 counts |
| 1.9 | `migrations/placement_evidence_kind.sql` | TASK-1081 | `placement_correct` / `placement_wrong` columns exist; the function is service_role only |

After Phase 1:
- `tests/sql/check_calibration_placement.sql` in the **SQL editor** (not the API: the zh ready counts take about
  30 s, over PostgREST's 8 s statement timeout).
- `tests/sql/check_function_acls.sql` returns nothing.
- `python scripts/verify_placement_rpcs.py --user <test account>` (creates and deletes that account's own
  placement sessions only).
- `EXPLAIN (ANALYZE, BUFFERS)` of the summary and the default words page for 110fb390/zh, filed for TASK-1054
  (read-only indicators on 2026-11-19: summary ≈ 20 ms, words ≈ 13 ms warm).

Rollback, if needed, in reverse: 1.9, 1.8, 1.7, 1.4, 1.3, 1.2, 1.1, then 1.5 and 1.6 (the bucket rollback refuses
while it holds files; the placement schema rollback refuses while placement sessions exist).

## Phase 2 — Japanese readiness (TASK-1075; Japanese launch only)

1. Apply `migrations/calibration_pool_refresh_language_and_katakana.sql` and
   `migrations/pronunciation_distractors_ja_kana_pattern.sql`.
2. `python scripts/build_calibration_distractor_cache.py --refresh-pool --word-language 3` — rebuilds the ja pool
   only; record the zh and en pool row counts before and after (they must not change).
3. Delete the ja pronunciation-cache rows whose anchor has fewer than 3 cached wrong readings consistent with the
   word's visible kana. Count first (read-only, 2026-11-19: **277 of 567** kanji+kana anchors; the spec estimated
   ≈ 199):

   ```sql
   WITH a AS (
     SELECT c.anchor_sense_id, v.lemma, c.sense_ids
       FROM calibration_distractor_cache c
       JOIN dim_word_senses s ON s.id = c.anchor_sense_id
       JOIN dim_vocabulary  v ON v.id = s.vocab_id
      WHERE c.mode = 'pronunciation' AND s.word_language_id = 3 AND v.lemma ~ '[ぁ-ゟ]'),
   k AS (
     SELECT a.anchor_sense_id,
            count(*) FILTER (WHERE calibration_normalise_pronunciation(f.pronunciation, 3::smallint)
                                   ~ ('^' || regexp_replace(a.lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$')) AS consistent
       FROM a CROSS JOIN LATERAL unnest(a.sense_ids) AS fid
       JOIN dim_word_senses f ON f.id = fid
      GROUP BY a.anchor_sense_id)
   DELETE FROM calibration_distractor_cache c USING k
    WHERE c.anchor_sense_id = k.anchor_sense_id AND c.mode = 'pronunciation' AND k.consistent < 3;
   ```
4. Refill: `python scripts/build_calibration_distractor_cache.py --word-language 3 --definition-language 3 --mode
   pronunciation`, then `--coverage` (run `calibration_clear_distractor_cache_misses()` first if misses block it).
5. Gate: `python scripts/placement_readiness_gate.py --word-language 3 --psql "<DSN>"` must print PASS for (3, 1),
   (3, 2) and (3, 3). The exam-list share check needs the ADR-054 JLPT file (TASK-1053); until then say so in the log.
   On the local sample, before the refresh, (3, 2) fails at 69% ready, as live does.

## Phase 3 — deploy and turn on

The code is safe to deploy before any migration: with the migrations missing, `/api/knowledge/summary` answers 503,
the snapshot job (04:25 UTC) and the placement close job (04:30 UTC) log "skipped", the placement API answers 404
(flag off), and the practice admission's placement read fails soft to nothing.

| Step | What | When |
|---|---|---|
| 3.1 | Deploy the branch | any time |
| 3.2 | Snapshots start at 04:25 UTC the night after Phase 1 (the 30-day trend needs 30 days of rows) | after Phase 1 |
| 3.3 | Zh gate: `python scripts/placement_readiness_gate.py --word-language 1 --psql "<DSN>"` → PASS for (1, 2), (1, 3) | after Phase 1 |
| 3.4 | `PLACEMENT_ENABLED_LANGS="1,2"` (zh, en) — TASK-1088; take your own placement in each (V1) and record `/answer` latency over 50 calls (target p50 ≤ 250 ms, p95 ≤ 600 ms) | after 3.3 |
| 3.5 | Add `3` to `PLACEMENT_ENABLED_LANGS` | after Phase 2's gate passes |
| 3.6 | `KNOWLEDGE_REPORT_ENABLED=true` — TASK-1058 (needs TASK-1054's performance check and TASK-1041) | after Phase 1 |
| 3.7 | Leave `ENTITLEMENTS_ENFORCED` off until the Pro launch gate (TASK-1059) | — |

## Not built yet (blocks nothing above)

- Placement entry points and the onboarding offer (TASK-1085, blocked on PQ7). Until then the placement is reached
  at `/placement`.
- Report integration of placement ranges (TASK-1086), the Pro tier (TASK-1045–1053, 1059), the goal-path layout
  (TASK-1072), validation (TASK-1089), docs reconciliation (TASK-1057, TASK-1095).

## Related Pages
- [[features/knowledge-report]] · [[features/vocab-placement]]
- [[tasklist/master]]
