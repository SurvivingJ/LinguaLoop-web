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

- Smoke test on the test account (`TEST_USER_EMAIL`, 110fb390): `verify_placement_rpcs.py`, pairs 1:2, 1:3, 3:1, 3:2,
  2:2 × 200 draws — every check passed (1,000 words, 1,470 answers; reading, forced-guess, reading-after-miss and
  sound-pair items); RPC round trip p50 274 ms, p95 317 ms; its sessions deleted. Two checker fixes on the way: it
  counted っ as no mora (5 false failures on ja; the SQL is right), and it now retries dropped connections on reads.
- Gates: en (2, 2) **PASS** (100%); `placement_readiness_gate.py` now initialises its client without `--psql`. ja and
  zh ready counts exceed PostgREST's 8 s timeout: run them with `--psql` or `tests/sql/check_calibration_placement.sql`
  in the SQL editor.

### 2026-11-23 — Phase 2 data steps and both gates

- ja pool refresh (`calibration_refresh_anchor_pool(3)`): ja 3,278 → 3,350 / 3,350 / 3,447 rows (katakana now in);
  zh 4,048 / 3,682 / 3,682 and en 6,110 unchanged.
- ja pronunciation cache: 277 of 567 kanji+kana anchors deleted (fewer than 3 kana-consistent foils), then every ja
  pair refilled: definition 99.5–99.6% cached, pronunciation 2,827 / 2,984 (94.7%; 210 anchors short).
- **ja (3, 2) gate: FAIL** — 2,864 / 3,241 ready (88.4%, was 66%); band 1 79%; in every band the unready words are
  mostly ≥ 3 characters (band 1: 84% of unready vs 51% of ready).
- **zh (1, 2) and (1, 3) gate: FAIL** (identical; computed in four vocab-id chunks with the function's own query,
  scored with `evaluate()`): 3,389 / 3,623 ready (93.5%), every band ≥ 84%, but the length check fails in bands
  1–3 (band 1: 92% of unready are ≥ 3 characters vs 55% of ready) and band 7's Zipf gap is 0.15 (> 0.10, 13 words).
- Causes (zh): (a) 74 words (马, 母亲, 父亲, 青少年…) have a native reading but the stale zh pool marks
  `has_pronunciation = false`, so no reading key — fixed by the zh pool refresh (TASK-1063, OQ29); (b) long words
  (理论体系, 科学研究…) have no cached wrong reading of the same syllable count (rule 3). ja unready words are the
  same long-word shape.

- PQ23 (owner, 2026-11-23): long words get the meaning question only. Where reading items fail, by shape (live):
  zh — 1 char 247/263 reading-ready, 2 chars 2,501/2,522, 3 chars 440/470, 4 chars 220/290, 5+ 0/4, no reading key 74
  (stale pool); ja (3, 2) — 2-kanji words ≥ 99%, but 3+ character words with kana endings (食べる, 大きい, 新しい)
  192/470, readings of 5+ morae mostly fail, 76 number/symbol lemmas have no key. A fixed length rule would drop
  ≈ 660 working zh reading items and ≈ 190 ja ones; the alternative is "no buildable reading item → meaning only",
  recorded per response (new column), which touches the answer function, tallies, `knowledge_calibration_inputs`,
  the Python outcomes and evidence writer. Waiting on the owner's choice.

### 2026-11-23 (later) — owner decisions applied; gates pass

- **PQ23 → per-word meaning-only** (a word with no buildable reading item is asked the meaning question only;
  `calibration_responses.reading_exempt`; [[features/vocab-placement.tech]] §23b). Applied live; the 7 changed
  functions are identical to the local harness copy; answer still service-role only.
- **OQ29 → zh pool refreshed now** (TASK-1063): zh/zh 4,048 → 13,125 rows (12,790 lemmas, frame 12,711); zh/en and
  zh/ja 3,682 → 3,909 (bounded by en/ja definitions); tone inventory rebuilt (381, unchanged). Cache refilled
  (one connection reset, resumed): zh/zh definition 99.9%, pronunciation 99.8%, zh/en and zh/ja 99.8%.
- Bytes: pool 10.10 → 10.47 MB, cache 7.50 → 10.37 MB; database 362.5 → 366.7 MB.
- **Gates** (ready = meaning-ready; computed through the MCP because the API times out at 8 s):
  zh (1, 2) and (1, 3) **PASS** 3,824 / 3,849 (99.4%, every band ≥ 99%); ja (3, 2) **PASS** 98.5%;
  ja (3, 3) **PASS** 98.6%; ja (3, 1) **FAIL** by two words — band 1 has 31 / 610 unready (5.1%, the
  representativeness threshold is 5%), 29 of them rare katakana culture/history terms (ルネサンス, バロック, グーテンベルク)
  with too few usable definition foils (`few_foils`) and 2 rule 5; en (2, 2) PASS.
- Live smoke test on the test account after the change: all five pairs × 200 draws, every check passed (1,440 answers,
  68 meaning-only words), p50 274 ms / p95 342 ms; sessions deleted.

Still to do: deploy (both features go live with it; no switches). The ja exam-list check (TASK-1053) waits for the
owner's list; ja (3, 1) is two band-1 words over the gate (better definition foils for ~29 rare katakana terms).

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
the snapshot job (04:25 UTC) and the placement close job (04:30 UTC) log "skipped", and the practice admission's
placement read fails soft to nothing. **No feature switches (owner, 2026-11-23):** the placement is always on for zh,
en and ja, and the Knowledge Report is always on; `PLACEMENT_ENABLED_LANGS` and `KNOWLEDGE_REPORT_ENABLED` were
removed from the code.

| Step | What | When |
|---|---|---|
| 3.1 | Deploy the branch | any time |
| 3.2 | Snapshots start at 04:25 UTC the night after Phase 1 (the 30-day trend needs 30 days of rows) | after Phase 1 |
| 3.3 | Zh gate → PASS (done 2026-11-23) | — |
| 3.4 | After deploy: take your own placement in each language (V1) and record `/answer` latency over 50 calls (target p50 ≤ 250 ms, p95 ≤ 600 ms) — TASK-1088 | after 3.1 |
| 3.5 | ja: exam-list check (TASK-1053; owner is finding the list) | when the list arrives |
| 3.6 | Knowledge Report: live on deploy (no switch) — TASK-1058; TASK-1054's performance check still to record | after 3.1 |
| 3.7 | Leave `ENTITLEMENTS_ENFORCED` off until the Pro launch gate (TASK-1059) | — |

## Not built yet (blocks nothing above)

- Placement entry points and the onboarding offer (TASK-1085, blocked on PQ7). Until then the placement is reached
  at `/placement`.
- Report integration of placement ranges (TASK-1086), the Pro tier (TASK-1045–1053, 1059), the goal-path layout
  (TASK-1072), validation (TASK-1089), docs reconciliation (TASK-1057, TASK-1095).

## Related Pages
- [[features/knowledge-report]] · [[features/vocab-placement]]
- [[tasklist/master]]

### 2026-11-23 — JLPT N5/N4 seeding (OQ31)

- Coverage report of the owner's JLPT list (7,972 entries, 7,836 spellings): 2,233 (28%) in the dictionary before;
  5,718 missing (5,540 words + 178 affixes). Lists: `data/sense_seeding/ja_jlpt/`.
- **N5 + N4 seeded live**: 694 words (`scripts/load_vocab_list.py`), 1,388 ja definitions (480 ja_5k drafts, 53 of them
  fixed in review, + 214 written), 2,776 en/zh glosses, embeddings (OpenRouter `openai/text-embedding-3-small`,
  verified identical to a stored vector), pronunciations on the native rows. ja pool refreshed; caches filled.
- ja gates after seeding: (3,1) 97.2%, (3,2) 98.8%, (3,3) 98.8% — all PASS (frame 3,241 → 3,935).
- Exercises: fat-seed pipeline (`claude -p`, $28.51 notional) → 673 of 694 senses, 4,711 word assets, 8,272 exercise
  rows. Rendering judges were first on OpenRouter, whose key hit its total limit mid-run (judges fail open), so every
  new sense was re-rendered with all judges on Claude (`claude_cli`, Sonnet; 5,378 judge calls), replacing the old
  rows in one `write_sense` each. The ja spaCy model and the ja mora trie were installed/built in the container, so
  jumbled_sentence (106) and phonetic_recognition (569) are included. particle_selection is absent: the plan only
  offers it for words with mined corpus sentences.
- 21 senses without exercises: 13 definitions span 2+ meanings (split the sense first), 4 reviewer no-ops, 3 missing
  level_6 blocks, 1 proper noun (`n5n4_exercise_issues.csv`).
- Database: 368.96 MB before → 394.72 MB after (owner's stop line: 475 MB).

### 2026-11-24 — JLPT N3 seeding

- **N3 seeded live**: 1,320 words (`load_vocab_list.py`), 2,640 ja definitions (588 drafts kept, 239 drafts fixed in
  review, 493 written), 5,280 en/zh glosses, hiragana pronunciations on the 2,640 native rows.
- **Not done — blocked on the OpenRouter key (total limit $11 spent):** N3 embeddings (1,320 senses, ≈$0.0002), then
  the ja pool refresh (`calibration_refresh_anchor_pool(3)`), cache fill
  (`build_calibration_distractor_cache.py --word-language 3`) and the ja gates. Until then N3 words have exercises but
  are not placement anchors.
- Exercises: fat-seed (110 runs × 12, `claude -p`, $58.75 notional incl. re-reviews), uploaded `--no-render`, then
  rendered with every judge on Claude (Sonnet, 12,445 judge calls, $163.13 notional) **fail-closed**: judges ran inside
  `batch_mode()` and the render stopped after 3 consecutive Claude-unavailable errors, so a usage limit could not
  ship unjudged rows. The Claude usage limit was never hit.
- 90 senses were dropped at assembly because the reviewer said "rewrite" but changed nothing; two blind re-review
  rounds recovered 88. Result: 1,313 of 1,320 senses live, 9,191 word assets, 18,557 exercise rows.
- 7 senses without exercises (`data/sense_seeding/ja_jlpt/n3_exercise_issues.csv`): 2 failed review 3 times, 2 missing
  blocks, 1 core rejected (大), 2 author skips (カー bound form; 棟 reading とう vs a むね definition — fix the
  definition).
- Run documents archived: `data/exercise_seeding/ja/archive/jlpt_n3_2026-11-24.tar.gz`; driver scripts:
  `scratch_offline/jlpt_n3_tools/`.
- Database: 395.99 MB before → 439.00 MB after (≈32.6 KB per sense). Headroom to the 475 MB stop line ≈ 36 MB
  ≈ 1,100 more senses; N2 + N1 (≈3,500 words) would need ≈115 MB.
- Later the same day: N3 embeddings done (owner topped up OpenRouter; 1,320 vectors, ≈$0.0001), ja pool refreshed,
  caches filled, gates PASS (3,1) 97.6% / (3,2) 99.0% / (3,3) 99.0%.
- **Correction:** every N5/N4/N3 Claude call ran through `claude -p` on the session's Claude Code login, not the
  owner's `CLAUDE_API` key; the dollar figures above are the CLI's notional per-token prices, not charges.

### 2026-11-24 — JLPT N2 (live up to the DB line) and N1 definitions (offline), billed to the owner's API key

> **Correction (2026-11-24, later):** none of the N2/N1 calls reached the owner's key. In this container the CLI
> bills the session login whenever `CLAUDE_CODE_REMOTE` is set, whatever `ANTHROPIC_API_KEY` says (proved with a
> fake key, which still succeeded). The wrapper now also unsets `CLAUDE_CODE_REMOTE`; through it a fake key fails
> ("Invalid API key") and the real key is refused with "Credit balance is too low", while direct Messages API calls
> with the same key succeed. The dollar figures below are the CLI's notional prices on the session login.
>
> **Fix (2026-11-24):** `scratch_offline/bin/claude` is now a drop-in replacement for `claude -p … --output-format
> json` that calls the Messages API directly with `CLAUDE_API` (official `anthropic` SDK, streaming, cached system
> prompt, `sonnet`/`haiku`/`opus` → `claude-*-5-5`, `--effort` → `output_config.effort`). It prints the CLI's JSON
> result envelope, so `nt_author`, `nt_review`, `jlpt_defs_cli.py` (PATH) and the renderer judges
> (`CLAUDE_CLI_PATH`) work unchanged. Proven: a fake key fails 401; the real key succeeds with request ids
> (`req_011ChNP9xxgBXXRoHzcQAMA3`, `req_011ChNPAuLReghJZYChgNFM1`); every call is logged with request id and real
> cost to `~/.claude_api_ledger.jsonl`. Definitions cost ≈ $0.007/word on Sonnet 5.5.

- From N2 on, every model call bills the owner's `CLAUDE_API` key: `scratch_offline/bin/claude` sets
  `ANTHROPIC_API_KEY=$CLAUDE_API` and unsets the session proxy URL; it is first on PATH for `nt_author`/`nt_review`
  and is `CLAUDE_CLI_PATH` for the renderer judges (`claude_cli_client` strips API keys from its own child env, so the
  wrapper is the only way in). Verified per process (`apiKeySource: ANTHROPIC_API_KEY`).
- Definitions: `scratch_offline/jlpt_defs_cli.py` (same brief as the N3 subagents, JSON on stdout, validated, retried).
- **N2 live**: 1,310 words, definitions, glosses, pronunciations, embeddings; ja pool refreshed (20,047), caches
  filled; gates PASS (3,1) 97.9% / (3,2) 99.1% / (3,3) 99.2%. Exercises: 80 of 110 runs uploaded (cap chosen from
  measured DB growth ≈27 KB/sense); 944 of 960 senses live; 16 without (`n2_exercise_issues.csv`).
- **N2 offline**: 30 runs / 350 senses authored, reviewed and ready but NOT uploaded (DB line):
  `data/exercise_seeding/ja/archive/jlpt_n2_offline_ready_to_upload_2026-11-24.tar.gz`, ids in
  `data/sense_seeding/ja_jlpt/n2_offline_sense_ids.txt`. Upload = `upload_run.sh` + render per run (≈10 MB).
- **N1 offline**: 2,130 definitions (1,212 written, 918 drafts reviewed, 237 fixed) in `n1_final.json`; no DB rows.
  Exercises need the words in the dictionary first (the export reads live senses).
- Spend on the key: N2 definitions $6.43, N2 authoring $57.26, N2 judges $109.99, N1 definitions $11.61 — $185.29.
- Database: 439.0 MB → 473.15 MB. Stopped under the 475 MB line.
