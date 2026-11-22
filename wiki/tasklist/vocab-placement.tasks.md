---
title: "Vocabulary placement — Task Breakdown"
feature: vocab-placement
prose_page: ../features/vocab-placement.md
tech_page: ../features/vocab-placement.tech.md
total_tasks: 23
done: 10
---

# Vocabulary placement — Task Breakdown

Spec: [[features/vocab-placement]], [[features/vocab-placement.tech]];
decisions [[decisions/ADR-057-adaptive-placement-with-conditional-reading]],
[[decisions/ADR-058-meaning-and-reading-recognition-pair-estimator]],
[[decisions/ADR-059-placement-evidence-kind]]; evidence [[evaluations/vocab-placement-research-2026-11-18]].

**Owner answers (2026-11-18).** PQ3 for Chinese: tones are scored with wrong tone combinations built only
from syllable+tone pairs that exist (ADR-060; TASK-1092 is now a zh launch item). PQ5: approved (ADR-059
accepted; TASK-1081 unblocked). PQ2: no exam-level output for now (TASK-1090 parked). PQ10: about 60 questions
for zh/ja (cap 60, 9-minute time cap; en stays 40).

**Sequence.**
1. Bug fixes and data (1074, 1075, 1082), zh tone variants (1092).
2. Schema and SQL (1076, 1077, 1079).
3. Pure design (1078).
4. Service (1080).
5. Evidence (1081).
6. UI and entry points (1084, 1085).
7. Report integration (1086).
8. Harness and launch (1087, 1088).
9. Validation and later work (1089–1091, 1093, 1094).
10. Docs (1095).

**Knowledge Report prerequisites:** TASK-1034, TASK-1035, TASK-1036, TASK-1039, TASK-1040, TASK-1044
([[tasklist/knowledge-report.tasks]]).

**Adjust existing tasks** (the orchestrator edits those files):
- TASK-1063 gains "Depends On: TASK-1074".
- TASK-1036 embeds `knowledge_calibration_inputs` (TASK-1079) instead of its own calibration block.
- TASK-1071 (estimated percentage per exam level) should reference TASK-1090's gates.
- TASK-1073 is done when this design is filed.

**LIVE-DB** marks a migration or data change on the only Supabase project. The task's author writes the
files; **the owner applies them**. Checks after apply are read-only.

---

## TASK-1074: Fix the zh reading normaliser and syllable count (LIVE-DB, owner-applied)

**Status:** [x] Done — applied live 2026-11-22 (VERIFY clean; fixtures yuan2xing2, nü3er2, ying4yong4) — `migrations/calibration_zh_normaliser_fix.sql`; suffixed readings byte-identical, 0 rows with syllable count 0
**Feature:** vocab-placement
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
6,621 of 8,110 zh standard readings no longer carry the `(yuan2 xing2)` suffix. For them
`calibration_normalise_pronunciation` returns diacritics and `calibration_syllable_count` returns 0, so any
zh pronunciation cache fill (TASK-1063, or a refill) would rank wrong readings with a broken length and
syllable test (tech §0 E7). This task derives numbered pinyin from the diacritics when no suffix exists.

**Acceptance Criteria:**
- [ ] For every zh standard native reading, the normalised form matches `^([a-zv]+[1-5])+$` after space
  removal, and the syllable count equals the number of space-separated syllables of the display form.
  Record the read-only check query and its output.
- [ ] Rows that already carry the numbered suffix normalise exactly as before (diff over the 1,489 rows = 0).
- [ ] Fixtures: `yuán xíng` → `yuan2xing2`; `bēi zi` → `bei1zi5`; `lǜ shī` → `lv4shi1`; `nǚ ér` → `nv3er2`.
- [ ] The 9 rows with no tone mark normalise with tone 5 and are listed in the task log.
- [ ] Migration lint passes; the rollback restores the previous bodies.

**Technical Notes:**
- Tone 1–4 comes from the marked vowel (ā á ǎ à, ē é ě è, ī í ǐ ì, ō ó ǒ ò, ū ú ǔ ù, ǖ ǘ ǚ ǜ); tone 5 for
  unmarked syllables. Strip the mark and map ü → v, matching today's comparison form.
- Split on spaces. Readings without spaces stay as today (no syllable segmentation).
- Read the live bodies first (`pg_get_functiondef`), then archive any superseded migration file per
  `migrations/CLAUDE.md`. No cache refill in this task.
- TASK-1082 ports the same mapping to Python; keep the fixtures identical.

**Files to Create / Modify:**
- `migrations/calibration_pronunciation_normaliser_fix.sql` — new: replaces both function bodies.
- `migrations/calibration_pronunciation_normaliser_fix_rollback.sql` — new.
- `tests/test_calibration_normaliser_migration.py` — new: static checks (`SET search_path`, REVOKE/GRANT,
  identical signatures).

**Verification:**
After the owner applies it, the read-only query of research-audit §1.3 (quoted in
[[evaluations/vocab-placement-research-2026-11-18]] §4) returns `syllable_count_zero = 0` for both groups.
Run `python -m pytest tests/test_calibration_normaliser_migration.py tests/test_migration_security_lint.py -q`.

---

## TASK-1075: Japanese reading readiness — katakana exclusion, kana-consistent foils, ja-only pool refresh and cache refill (LIVE-DB, owner-applied)

**Status:** [~] Code done (2026-11-19); both migrations applied live 2026-11-22 (ja (3, 2) ready 2,099 / 3,175 = 66% before the data steps); owner: apply, ja-only pool refresh, cache delete/refill, gate (runbook Phase 2)
**Feature:** vocab-placement
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1077 (for the gate measurement only; the migrations can be applied earlier)

**Description:**
Japanese placement needs ≥ 90% of the frame placement-ready (≥ 80% per band), with ready words that look
like the rest (tech §2 launch gate). Today readiness is 69% (band 1 50%): 841 pool rows predate their
readings, and 214 katakana-only lemmas sit in the reading pool. In addition, 199 kanji+kana anchors have fewer
than 3 wrong readings consistent with their visible kana (E10). This task excludes katakana-only lemmas,
adds the visible-kana filter to the foil picker, refreshes the **ja** pool only, and refills the ja
pronunciation cache.

**Acceptance Criteria:**
- [ ] `calibration_refresh_anchor_pool` gains `p_word_language_id smallint DEFAULT NULL` (NULL = all
  languages, as today) and excludes `^[ァ-ヿー・]+$` lemmas from `has_pronunciation`. Existing callers with
  `{}` still work. Rollback file included.
- [ ] `pronunciation_distractors` keeps, for word language 3, only candidates matching
  `'^' || regexp_replace(anchor_lemma, '[^ぁ-ゟー]+', '.+', 'g') || '$'` when the lemma contains hiragana.
  Rollback included.
- [ ] Pool refreshed for ja only, with `scripts/build_calibration_distractor_cache.py --refresh-pool
  --word-language 3`. zh and en pool row counts are unchanged (before/after counts recorded).
- [ ] The ja pronunciation cache rows of anchors with fewer than 3 rule-3b-consistent cached foils are
  deleted (count recorded, ≈ 199 expected) and refilled. The fill is then run for all missing ja anchors.
- [ ] `calibration_placement_ready_counts(3, 2)`, `(3, 1)` and `(3, 3)` meet the gate: ≥ 90% overall, ≥ 80% per
  band, and the representativeness checks of tech §2. Output, plus `pg_database_size` before and after,
  recorded in `wiki/log.md`.

**Technical Notes:**
- Today `--refresh-pool` calls `calibration_refresh_anchor_pool` with `{}` (scripts/build_calibration_distractor_cache.py:151-153).
  Pass `{'p_word_language_id': args.word_language}` when `--word-language` is given.
- Replace the function with `DROP FUNCTION … ; CREATE FUNCTION …(p_word_language_id smallint DEFAULT NULL)`,
  not an overload.
- Fill: `--word-language 3 --definition-language 3 --mode pronunciation`, then `--coverage`. Cache misses may
  need `calibration_clear_distractor_cache_misses()` first.
- Size ≈ 0.2 MB (ESTIMATE, research-audit §5.1).
- The list-share part of the representativeness check needs the ADR-054 JLPT file. If TASK-1053 has not
  uploaded it, use the source list files (krmanik/HSK-3.0 2025 and jamsinclair/open-anki-jlpt-decks, see ADR-054) for that measurement and say so in the log.

**Files to Create / Modify:**
- `migrations/calibration_pool_refresh_language_and_katakana.sql` — new.
- `migrations/calibration_pool_refresh_language_and_katakana_rollback.sql` — new.
- `migrations/pronunciation_distractors_ja_kana_pattern.sql` — new.
- `migrations/pronunciation_distractors_ja_kana_pattern_rollback.sql` — new.
- `scripts/build_calibration_distractor_cache.py` — pass `--word-language` through to the refresh.
- `scripts/placement_readiness_gate.py` — new, read-only: calls the ready counts, adds list shares from
  the ADR-054 file, and prints pass/fail per band.
- `tests/test_calibration_pool_refresh_migration.py` — new, static.

**Verification:**
Run `python scripts/placement_readiness_gate.py --word-language 3` after the owner applies the changes and
runs the refresh and fill; it prints PASS for every (3, D). Run
`python -m pytest tests/test_calibration_pool_refresh_migration.py tests/test_migration_security_lint.py -q`.

---

## TASK-1076: Placement schema migration (LIVE-DB, owner-applied)

**Status:** [x] Done — applied live 2026-11-22 (additive; relfilenode 179439 / 179461 unchanged) — `migrations/calibration_placement.sql`
**Feature:** vocab-placement
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Adds the `placement` session mode, `stop_reason` (including `time`) and the frozen `result` on
`calibration_sessions`. Adds `item_kind`, `probe_kind`, `instrument` (including `reading_tone_v1`),
`pair_response_id`, `option_sense_ids`, `key_position`, `option_roles`, `option_texts` and `chosen_position`
on `calibration_responses`, plus the partial index `(user_id, anchor_vocab_id) WHERE
answered_at IS NOT NULL`, exactly as tech §13. The UVK counters belong to TASK-1081.

**Acceptance Criteria:**
- [ ] `calibration_sessions_mode_chk` admits `placement`: added `NOT VALID`, then `VALIDATE`. Existing rows
  are untouched.
- [ ] New columns are nullable or have constant defaults; no table rewrite (`pg_class.relfilenode`
  unchanged before and after).
- [ ] CHECK constraints exactly as tech §13 (enumerated values for `stop_reason`, `item_kind`, `probe_kind`,
  `instrument`).
- [ ] The rollback drops the columns and the index and restores the old constraint.
- [ ] Read-only check after apply: the column list via `information_schema.columns`; index size recorded.

**Technical Notes:**
- `calibration_responses.id` is `bigserial` (`migrations/calibration_sessions_and_ability.sql`);
  `pair_response_id` references it `ON DELETE CASCADE`.
- No grants to client roles: the table has none (`migrations/security_calibration_answer_keys.sql`).
- `item_kind NULL` means a legacy row.

**Files to Create / Modify:**
- `migrations/calibration_placement.sql` — new.
- `migrations/calibration_placement_rollback.sql` — new.
- `tests/test_calibration_placement_migration.py` — new, static: columns, checks, rollback symmetry.

**Verification:**
`python -m pytest tests/test_calibration_placement_migration.py tests/test_migration_security_lint.py -q`;
the read-only column and index query after the owner applies the migration.

---

## TASK-1077: Placement SQL functions — ready counts, next item, answer, close, close stale (LIVE-DB, owner-applied)

**Status:** [x] Done — applied live 2026-11-22 (31 functions, identical to the harness; service role only; en (2, 2) ready 3,753 / 3,754). Live smoke test on the test account, all five pairs × 200 draws: 1,000 words, 1,470 answers, every check passed; RPC round trip p50 274 ms, p95 317 ms over 818 calls; test sessions deleted — `migrations/calibration_placement_rpcs.sql` (31 functions); scripted sessions green on the harness
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1076; TASK-1092 for zh reading items

**Description:**
Writes the five functions of tech §14 with the item rules of tech §2:
- rank-1 only; no reading on meaning items;
- same display syllable or mora count;
- ja visible-kana consistency (3b);
- zh reading items as two tone pairs K, K′, F, F′ (rule 4, ADR-060), with K′ and F′ from
  `calibration_zh_tone_variants` (TASK-1092), roles and texts stored in `option_roles`/`option_texts`, and the
  answer's `chosen_position` recorded;
- cross-CJK prefix strip covering `；`, `;`, `——`, `—`, and exclusion of residual anchors (rule 5);
- readiness and the 180-day per-user exclusion;
- the branch rules of `calibration_placement_answer`: a scored reading item after a right meaning, probes
  under the budget, the reveal, the next meaning item in `p_next_band`;
- the tallies payload.

**Acceptance Criteria:**
- [ ] Signatures, returns and errors exactly as tech §14; `SET search_path`; REVOKE/GRANT per
  `migrations/CLAUDE.md`; `tests/sql/check_function_acls.sql` returns nothing.
- [ ] Read-only checks after apply, run by a script on a test account (its rows deleted afterwards).
  Over 200 draws per (L, D) pair, the functions never return:
  - a non-ready lemma;
  - a lemma the account answered in 180 days;
  - a key, or a reading in a meaning payload;
  - a reading item whose 4 options differ in display syllable or mora count;
  - a zh reading item whose roles are not exactly K, KT, F, FT, whose KT or FT is not in
    `calibration_zh_tone_variants` of K or F, or whose F is a tone variant of K;
  - a kana-inconsistent foil in a ja item.
- [ ] **Measured rule-5 residual** (query Q4 of the research record, rewritten with the new strip): the share
  of zh/ja and ja/zh rank-1 anchors whose stripped key contains the prompt lemma while no served foil does
  is ≤ 1% before exclusion, and 0 after.
- [ ] `calibration_placement_answer`:
  - rejects a second answer, a foreign session and an out-of-range position;
  - its tallies match a hand count on a scripted session;
  - never serves more than 4 probes per session, 2 per kind, or 1 per word.
- [ ] `calibration_placement_close` leaves no unanswered row in the session and is idempotent.
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` of the build step: the best warm run is ≤ 50 ms (record every run).
- [ ] `calibration_placement_ready_counts` for (1, 2), (1, 3), (3, 1), (3, 2) and (2, 2) recorded in
  `wiki/log.md`, including the counts excluded by rules 3b and 5 and by the zh tone rule.

**Technical Notes:**
- Reuse `calibration_cached_options(mode, anchor)` and `calibration_display_pronunciation`.
- Syllables and morae come from the display form, never from the normaliser.
- Random within band: `ORDER BY random() LIMIT 1` over the band's ready set (≤ ~750 rows) is acceptable.
- F must not be a tone variant of K: `translate(lower(x), 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü', 'aaaaeeeeiiiioooouuuuvvvvv')`
  differs for key and foil.
- The tallies for zh pairs are [n', pc, pkt, pf] (tech §5.1, §14); the grade of a zh reading answer is
  `option_roles[chosen_position + 1]`.
- ja special-mora/voicing detection for `sound_pair` (ja only; zh has no `sound_pair` probe): research Q3's normalisation (NFD, drop dakuten,
  handakuten, っ, ん, ー, う, い) equal and the strings different.
- `recheck` foils come from the anchor's cached foils minus the earlier serving's `option_sense_ids`.
- Probe draws arrive in `p_draws`; never call `random()` for probe decisions, so tests are deterministic.

**Files to Create / Modify:**
- `migrations/calibration_placement_rpcs.sql` — new.
- `migrations/calibration_placement_rpcs_rollback.sql` — new.
- `tests/test_calibration_placement_migration.py` — extend with static checks of the new functions.
- `scripts/verify_placement_rpcs.py` — new, owner-run: service role; reads only, apart from creating and
  then deleting the test account's own placement rows.

**Verification:**
`python scripts/verify_placement_rpcs.py --user <test account>` prints every check green after the owner
applies the migration; `python -m pytest tests/test_calibration_placement_migration.py -q`.

---

## TASK-1078: Pure placement design and estimator functions

**Status:** [x] Done (repo) (2026-11-19) — `services/placement_design.py`
**Feature:** vocab-placement
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1035

**Description:**
Writes `services/placement_design.py`: `CONFIG`, warm-up order (7 → 1, then random), next-band allocation from
the previous call's tallies, `should_stop` (precision, cap, time, exhausted), eligibility (a)/(b)/(c), word
groups (with zh `tones_not_yet`), and minutes left. `CONFIG`: cap 60 (zh/ja) / 40 (en), time cap 540 s, zh pair
pseudo-count 0.25. Extends `services/vocabulary/knowledge_estimate.py` with `pair_counts`,
`estimate_range_pairs` (ja), `estimate_range_tone_pairs` (zh, ADR-060), `gap_range` (ja gap, zh reading gap, zh
tone gap), `apply_guard` (M8 direction), the eligibility amendment, and `compare`
(the ADR-053 rule). Everything follows tech §5.1, §6 and §7. There is **no `level_range`** (tech §5.3).

**Acceptance Criteria:**
- [ ] Every pure unit case of tech §19 passes. This includes End now at 20, 30 and 45 scored items
  returning a result and at 19 returning `not_enough`, and the gap equalling T_m − T_mr on identical samples.
- [ ] `estimate_range_pairs` on (pc, prw) inputs equal to (c, w) inputs returns the ADR-051 fixture
  (de6fd05b/ja: 853.3–1,368.1).
- [ ] `apply_guard` sets `lo_m := max(lo_m, lo_mr)` and `hi_mr := min(hi_mr, hi_m)` before rounding.
- [ ] zh: `estimate_range_tone_pairs` matches hand-computed fixtures of (pc, pkt, pf, IDK) counts with the 0.25
  pseudo-count; on one sample K_m = K_mr + tone gap + reading gap; `should_stop` returns `cap` at 60 scored items
  (61 with a due reading item) and `time` at 540 s.
- [ ] No I/O and no Flask or Supabase imports; the RNG is injected.

**Technical Notes:**
- `SD_RATIO = 0.12/1.645`.
- Allocation uses this session's tallies; the "combined" estimate pools (tech §5.1).
- A pending scored reading item blocks stopping.
- Active time = Σ min(gap, 60 s).
- `CONFIG['version'] = 1` is stored in `result.version`.

**Files to Create / Modify:**
- `services/placement_design.py` — new.
- `services/vocabulary/knowledge_estimate.py` — modify (created by TASK-1035).
- `tests/test_placement_design.py` — new.
- `tests/test_knowledge_estimate.py` — extend.

**Verification:**
`python -m pytest tests/test_placement_design.py tests/test_knowledge_estimate.py -q`

---

## TASK-1079: `knowledge_calibration_inputs` SQL function (LIVE-DB, owner-applied)

**Status:** [x] Done — applied live 2026-11-22 — `migrations/knowledge_calibration_inputs.sql`
**Feature:** vocab-placement
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1076, TASK-1034

**Description:**
One STABLE function returning the calibration inputs of report §2.6 plus placement pairs and gap bands (tech
§9, §14). It applies the report's D and instrument rule, or restricts to one session (`p_session_id`), so
the placement result and the report share inputs. TASK-1036 embeds it.

**Acceptance Criteria:**
- [ ] With `p_session_id`, only that session's scored items count.
- [ ] Without it: if an eligible placement exists in the window, D = that placement's D and instrument =
  `meaning_bare_v1`; otherwise ADR-051 rule 1 on legacy rows (`instrument IS NULL`, `mode = 'definition'`).
- [ ] Meaning bands are the latest scored answer per `anchor_vocab_id`, rank-1, `probe_kind IS NULL`. Pair and
  gap bands follow the tech §5.1 tables (reading-ready vs exempt; probes and abandoned pairs excluded).
- [ ] For de6fd05b/ja (no placement yet), `bands` equals the report §2.6 fixture, and `pairs` and `gap` are null.
- [ ] Unit fixture: a learner with legacy check answers in D = en and a placement in D = ja gets D = ja and only
  placement rows (PSY M15).
- [ ] `SECURITY INVOKER`, service role only, lint and ACL clean; best warm run ≤ 50 ms.

**Files to Create / Modify:**
- `migrations/knowledge_calibration_inputs.sql` — new.
- `migrations/knowledge_calibration_inputs_rollback.sql` — new.
- `tests/test_knowledge_report_migration.py` — create or extend with static checks.

**Verification:**
Read-only `SELECT knowledge_calibration_inputs('<de6fd05b uuid>', 3::smallint)`, compared with the report §2.6
fixture after the owner applies the function.

---

## TASK-1080: Placement service and routes

**Status:** [x] Done (repo) (2026-11-19) — service + routes; driven end to end against the real SQL on the harness. The production latency check moves to TASK-1088
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1077, TASK-1078, TASK-1079

**Description:**
Writes `services/calibration_placement.py` (`start`, `answer`, `end`, `finish`, `result`, `latest`,
`close_stale_for`) and the five routes of tech §14 in `routes/calibration.py`:
- one SQL round trip per answer (`calibration_placement_answer` with `p_next_band` from the previous call's
  tallies and injected draws);
- server-side stop and the frozen `result` (tech §8 JSON);
- eligibility (c) for End now and abandoned sessions;
- 24 h resume, and an abandoned result shown once through `latest`;
- the retake comparison;
- the fast flag, rate limits and the `PLACEMENT_ENABLED_LANGS` flag.

`finish()` calls the evidence writer (TASK-1081) through an injectable hook. The hook is a no-op only in
tests; launch requires the real writer (TASK-1088).

**Acceptance Criteria:**
- [ ] A scripted learner (Supabase fake) runs start → … → done for zh, ja and en; stop reasons `precision`,
  `cap`, `time`, `exhausted`, `learner` and `abandoned` are each reachable in tests.
- [ ] `/answer` returns `reveal` only when a word is complete and never a key for an unanswered item.
- [ ] An open placement younger than 24 h is resumed; older ones are closed `abandoned` on start and by the
  nightly function; an eligible abandoned session's result is returned once by `/latest` with
  `unseen: true`.
- [ ] Retake: with a previous eligible placement for (L, D), `result.previous.verdict` follows the ADR-053
  rule; with a frame change > 1%, `previous` is null.
- [ ] Rate limits registered in `web/rate_limits.py`; the per-language cap of 3 starts per day returns 429;
  404 when the language is not enabled.
- [ ] `/answer` server time p50 ≤ 250 ms and p95 ≤ 600 ms over 50 calls against production with a test account
  (recorded).

**Technical Notes:**
- `p_draws` comes from `random.Random` seeded per session, stored nowhere.
- On stop, `finish()` calls `calibration_placement_close`, which deletes the pre-built next row.
- `result` must be ≤ 2 KB (assert in tests).

**Files to Create / Modify:**
- `services/calibration_placement.py` — new.
- `routes/calibration.py` — add the placement routes.
- `web/rate_limits.py` — add `calibration.placement_start` and `calibration.placement_answer`.
- `config.py` — add `PLACEMENT_ENABLED_LANGS`.
- `tests/test_placement_routes.py` — new.

**Verification:**
`python -m pytest tests/test_placement_routes.py -q`; a manual local run with the flag on for zh.

---

## TASK-1081: Placement evidence — UVK counters, pair-based BKT batch, A2 and A2r admission on the native sense (LIVE-DB, owner-applied)

**Status:** [~] Applied live 2026-11-22 (columns present; function service role only); end-to-end intro-drill check after deploy — `migrations/placement_evidence_kind.sql` + admission queues; the end-to-end intro-drill check runs after apply
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1076, TASK-1080

**Description:**
Implements ADR-059:
- adds `placement_correct`/`placement_wrong` to `user_vocabulary_knowledge`;
- writes `update_vocabulary_from_placement_batch` (BKT as `migrations/bkt_word_test_batch.sql`, other
  counters);
- calls it from `finish()` with the pair outcomes of tech §10, claimed by `bkt_applied_at`;
- extends `new_word_admission._calibration_ledger` to placement sessions: A2 for missed meanings, the new
  A2r for meaning ✓ / reading not ✓;
- maps anchor senses to the native rank-1 sense before the veto and the supply gate.

**Acceptance Criteria:**
- [ ] After a scripted placement:
  - meaning ✓ reading ✓ and exempt meaning ✓ rows get `placement_correct` +1;
  - meaning ✗/IDK rows get `placement_wrong` +1;
  - meaning ✓ reading ✗/IDK rows get **no** write (zh: K′, F and F′ are all "reading ✗");
  - `word_test_*` is unchanged;
  - `p_known` updates equal `bkt_update_word_test` on the same inputs.
- [ ] Probes write nothing, and a session is applied at most once (including `abandoned` sessions closed by
  the nightly job).
- [ ] A missed placement meaning appears as an A2 candidate and a meaning ✓ / reading ✗ word as an A2r
  candidate, each under the **native rank-1 sense id** of its `vocab_id`; a probe never does.
- [ ] **End-to-end (L6 point 5):** after a scripted zh placement with 5 meaning-only words and TASK-1082 merged,
  the next practice session's intro block contains `read_typed` items for those 5 senses (within the daily
  budget).
- [ ] Report rule check: a word with only placement evidence is never `rated_known`.

**Technical Notes:**
- Sessions read: `mode = 'placement' AND bkt_applied_at IS NOT NULL`; rows `probe_kind IS NULL`.
- A2r joins each scored meaning row to its reading row through `pair_response_id`. For zh, "reading not ✓" means
  the chosen role is not K (K′ is a tone gap, still A2r).
- Age limit: `CALIBRATION_EVIDENCE_MAX_AGE_DAYS` (`services/practice/constants.py:61-62`, 90).
- Veto as today (`new_word_admission.py:660-673`), applied to the native sense.
- A2r alternates with A2 in ranking, inside the same budget (ADR-033).
- Native sense lookup: `dim_word_senses` with `vocab_id` = anchor's, `definition_language_id = word_language_id`,
  `definition_level = 'standard'`, `sense_rank = 1`. If none exists, keep the anchor and log it.

**Files to Create / Modify:**
- `migrations/placement_evidence_kind.sql` — new: UVK columns and the batch function.
- `migrations/placement_evidence_kind_rollback.sql` — new.
- `services/calibration_placement.py` — call the batch in `finish()`.
- `services/practice/new_word_admission.py` — ledger, A2r and native-sense mapping.
- `tests/test_placement_evidence.py` — new.

**Verification:**
`python -m pytest tests/test_placement_evidence.py tests/test_ladder_new_word_quota.py -q`; a read-only UVK
check for the test account after a live run.

---

## TASK-1082: Intro drill shows zh pinyin for diacritic-only readings (zh launch dependency)

**Status:** [x] Done (repo) (2026-11-19) — `intro_drill._reading`; also `prestudy._load_senses` (the prestudy page had the same gap)
**Feature:** vocab-placement
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
`intro_drill._reading` returns None for zh unless the reading ends in a numbered `(…)` part
(`services/intro_drill.py:238-251`). Most zh native readings are now diacritic-only (E7), and
`dim_vocabulary.reading` is empty for zh pool words (E16). So `read_typed` formats are dropped for the words
the placement sends to reading practice. This task derives the numbered form from the diacritics, with the
same mapping as TASK-1074.

**Acceptance Criteria:**
- [ ] `_reading({'reading': 'yuán xíng'}, 'zh')` returns `{'shown': 'yuán xíng', 'numbered': 'yuan2 xing2'}`.
  Readings that already carry `(…)` are unchanged.
- [ ] The TASK-1074 fixtures (`bēi zi`, `lǜ shī`, `nǚ ér`) produce the same numbered syllables in Python as
  in SQL.
- [ ] `word_formats(1, 'zh', has_reading=True, …)` starts with `read_typed` for a diacritic-only word (existing
  rule, now reachable).

**Technical Notes:**
- Put the mapping in a small pure helper, `services/vocabulary/pinyin_tones.py`
  (`diacritics_to_numbered(text) -> str`), and keep `numbered` space-separated as the client expects.
- Do not change ja handling.

**Files to Create / Modify:**
- `services/vocabulary/pinyin_tones.py` — new.
- `services/intro_drill.py` — use the helper in `_reading`.
- `tests/test_intro_drill.py` — extend.
- `tests/test_pinyin_tones.py` — new.

**Verification:**
`python -m pytest tests/test_intro_drill.py tests/test_pinyin_tones.py -q`

---

## TASK-1083: Placement feeds test selection and the guarded rating writer [?]

**Status:** [?] Blocked — OQ33 of the Knowledge Report (how a skip is scored in the ability fit) and PQ19
**Feature:** vocab-placement
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-1080

**Description:**
Placements stay out of `pooled_ability` and the rating writer until OQ33 is answered (tech §11, PSY M16).
If OQ33 chooses a skip-aware fit, this task does three things:
- adds the likelihood `P(right) = K + (1 − K)·(1 − ŝ)/4` (IDK and wrong ∝ 1 − K) for placement meaning items
  to `_fit_points`/`_fit_ability` (`services/calibration_service.py:315-448`);
- includes those items in the `definition` fit;
- calls `write_calibration_state` and `apply_calibration_to_ratings` from `finish()` for sessions that are not
  flagged fast.

If OQ33 chooses "label each", close this task as won't-do.

**Acceptance Criteria:**
- [ ] Written in its own short ADR revision of ADR-059 decision 6 before code.
- [ ] A pooled definition fit over one check session and one placement equals a fit over the union of their
  meaning answers under the chosen likelihood; readings and probes are excluded.
- [ ] The rating writer is called once per finished placement and not for a fast-flagged one; its G1–G6
  decisions are stored in `result.rating_decisions`.

**Files to Create / Modify:**
- `services/calibration_service.py` — the skip-aware fit and placement items.
- `services/calibration_placement.py` — call the state write and the rating writer.
- `tests/test_calibration_fast_path.py` — extend.
- `tests/test_placement_routes.py` — extend.

**Verification:**
`python -m pytest tests/test_calibration_fast_path.py tests/test_placement_routes.py -q`

---

## TASK-1084: Placement page and i18n

**Status:** [x] Done (repo) (2026-11-19) — `/placement`, 48 vitest cases, Playwright smoke at 390 px
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1080

**Description:**
Builds the `/placement` page per tech §8, §15 and §16:
- intro with neutral IDK copy and "about 7 / 5 minutes";
- meaning and reading items without reading leaks; "Choose the pinyin" (zh options are two tone pairs);
- labelled probes ("Extra question — not scored"; IDK hidden on `forced_guess`; 2 options for the ja `sound_pair`);
- the held word parts and the combined reveal;
- "about N minutes left" and "Stop here and see your result";
- the result blocks in order: word groups with actions (zh adds "Meaning and pinyin, not the tones"), the
  range band, the tone-gap (zh) and gap lines when present, the
  retake block, next steps, "How this works", flags;
- an unseen abandoned result shown on load.

There is no level line anywhere.

**Acceptance Criteria:**
- [ ] Meaning items show no reading; the reveal appears only when a word is complete; all ✓ auto-advances at
  450 ms, otherwise "Next word"; a zh tone-only miss is marked in the reveal ("right pinyin, wrong tones"); one
  advance per action; a tapped option is highlighted before the response
  arrives.
- [ ] Keys 1–4, 0 (absent on `forced_guess`) and Enter work; the page works at 390 px in both themes; `lang`
  is set on the word.
- [ ] The result renders the zh, ja and en fixtures; the gap line appears only when `result.this.gap` is
  non-null; the retake block appears only with `result.previous`; "lo = 0" uses the beginner phrasing.
- [ ] All `placement.*` and `onboarding.studied_*` keys exist in en, es, ja and zh; the i18n parity test passes;
  no string contains "know" without "recognis" (grep test on the en file).
- [ ] `tests/unit/placement.test.js` covers the reveal state machine, probe rendering and result rendering.

**Files to Create / Modify:**
- `templates/placement.html` — new.
- `static/js/pages/placement.js` — new.
- `web/pages.py` — register `/placement` next to `('/calibration', …)`.
- `static/css/redesign/trainers.css` — `.plc-*` classes.
- `static/i18n/en.json`, `es.json`, `ja.json`, `zh.json` — the keys of tech §16.
- `tests/unit/placement.test.js` — new.

**Verification:**
`npx vitest run tests/unit/placement.test.js`; `python -m pytest tests/test_i18n_locale_files.py -q`; a local
run per language; a Playwright smoke at 390 px (TASK-1055 pattern).

---

## TASK-1085: Entry points — onboarding gate, report empty state, calibration page, Me row [?]

**Status:** [?] Blocked — PQ7 (onboarding offer and the "studied before?" gate)
**Feature:** vocab-placement
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1084, TASK-1040

**Description:**
Adds the onboarding question "Have you studied {language} before?" ("Yes" → placement, skippable; "Only a
few words" or "No" → continue, nothing stored). It also offers "Take the 7-minute placement" in the report's
empty state and the Me row whenever the learner has no placement for that language, and "Short placement
instead" on the calibration page (tech §8, §15).

**Acceptance Criteria:**
- [ ] Each entry opens `/placement?lang=…` for the current study language.
- [ ] The two "not studied" answers write nothing and do not open the placement.
- [ ] The report and Me-row offers disappear once a placement with a frozen result exists for the language.
- [ ] Everything is hidden for a language not in `PLACEMENT_ENABLED_LANGS`.

**Files to Create / Modify:**
- `templates/onboarding.html`, `static/js/pages/onboarding.js` — the gate.
- `static/js/pages/knowledge.js` — the empty state and the Me row offer.
- `templates/calibration.html` — the link.
- `static/i18n/*.json` — the keys.

**Verification:**
A manual walk-through of each entry point per language; `python -m pytest tests/test_i18n_locale_files.py -q`.

---

## TASK-1086: Report integration — inputs, instrument and D rule, second range, gap, guard, eligibility, placement evidence state (LIVE-DB, owner-applied)

**Status:** [ ] Not Started
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1078, TASK-1079, TASK-1081, TASK-1036, TASK-1039, TASK-1040, TASK-1044

**Notes from the build (2026-11-19):**
- `knowledge_report_summary` computes its growth "since" sets from legacy definition-mode rows (no instrument
  filter); once placements exist they must follow the instrument and D rule. Add a `p_since` parameter to
  `knowledge_calibration_inputs` and use it from the summary.
- Unify the calibration block's date names (`first_at`/`last_at` from §14 vs `first_answer_at`/`last_answer_at`
  in report §6.1); the summary currently returns both and the service accepts both.
- Have the summary return `checked_meanings` (the snapshot job falls back to missed + rated known + checked).

**Description:**
- `knowledge_report_summary` embeds `knowledge_calibration_inputs`.
- The summary service computes `estimate_m`, `estimate_mr` and the gap, and applies the eligibility amendment
  and the M8 guard.
- The hero shows the m+r range first and the gap line.
- `knowledge_report_words` and the detail view add the `placement_only` state and the "Placement ✓ meaning ✓
  reading ✗" row lead.
- Snapshots store pair and gap bands and the instrument (tech §9).

**Acceptance Criteria:**
- [ ] For a test account after one finished zh placement, the report hero and the placement's combined line
  show identical ranges and labels on that day.
- [ ] Without any placement, the report is byte-identical to before for de6fd05b/ja (fixture unchanged).
- [ ] With a legacy check history in D = en and a placement in D = ja, the report uses D = ja and placement rows
  only (PSY M15).
- [ ] A word with only placement evidence shows "Placement answer only" and is never counted as rated known.
- [ ] Snapshot rows carry `pairs`, `gap` and `instrument` (null when there is no placement).

**Files to Create / Modify:**
- `migrations/knowledge_report_summary.sql` and `migrations/knowledge_report_words.sql` (or their
  successors) — the embed, the evidence state and the row lead.
- `services/vocabulary/knowledge_report.py` — the ranges, guard and eligibility.
- `services/knowledge_snapshots.py` — pair and gap bands.
- `static/js/pages/knowledge.js` and `static/i18n/*.json` — the hero copy.
- `tests/test_knowledge_report*.py` — fixtures.

**Verification:**
`python -m pytest tests/test_knowledge_report*.py -q`; a read-only summary call for the test account after
the owner applies the SQL.

---

## TASK-1087: Simulation regression harness for the production code (V0)

**Status:** [x] Done (repo) (2026-11-19) — `tests/test_placement_coverage.py` (-m slow); results in the tech spec E34
**Feature:** vocab-placement
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1078

**Description:**
Ports the research learner model (`wiki/evaluations/vocab-placement-research-2026-11-18/sim/sim.py`, with `pool.py`) into a slow pytest that runs the
**production** `placement_design` and `knowledge_estimate` and asserts V0 (tech §20). Word pools come from
read-only fixture exports **with launch readiness flags** (PSY M13), an en population is added, and the zh
learners carry the tone state of `wiki/evaluations/vocab-placement-research-2026-11-18/tones/tone_sim.py` (E33).

**Acceptance Criteria:**
- [ ] 300 learners × populations (zh·en, zh·ja, ja·en, ja·zh, en·en; IDK 0.3 and 0.7), fixed seed, under 3
  minutes.
- [ ] The run meets every V0 threshold:
  - 95% coverage ≥ 0.90 for m, m+r, the reading gap and the zh tone gap;
  - |bias| ≤ 1.5% of the pool (zh m+r with tones included);
  - zh/ja mean scored items 55–61;
  - en mean ≤ 40 with coverage ≥ 0.90;
  - End-now coverage at 20/30 scored items ≥ 0.88.
- [ ] The run records and files the following:
  - the label distribution (Fewer than / Rough / …) by true m+r level and the early-stop share per L1,
    compared with E25, E31 and E33;
  - the zh partial-tone-memory case (t_partial 0.65) bias, compared with E33;
  - the share of results showing the gap line;
  - the `expected_sd` lookup error on placement-shaped samples.
- [ ] Results filed in `wiki/evaluations/vocab-placement-v0-<date>.md`.

**Technical Notes:**
- The harness must not import from the wiki archive: copy the model into `tests/placement_sim_model.py`,
  attributed.
- Fixtures hold ids, Zipf, band, reading flag, exempt flag and list level only; no learner data.
- If TASK-1090 ever proposes a level output, this harness gains its per-true-level gate.

**Files to Create / Modify:**
- `tests/test_placement_coverage.py` — new, marked `slow`.
- `tests/placement_sim_model.py` — new.
- `tests/fixtures/placement_pool_zh.json`, `placement_pool_ja.json`, `placement_pool_en.json` — new.
- `scripts/export_placement_fixtures.py` — new, read-only.

**Verification:**
`python -m pytest tests/test_placement_coverage.py -q -m slow`

---

## TASK-1088: Launch per language — readiness gate, nightly close, flag (LIVE environment change, owner)

**Status:** [~] In Progress (2026-11-19) — code part done (nightly close job, `scripts/placement_readiness_gate.py`); owner launch steps remain (runbook Phase 3)
**Feature:** vocab-placement
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1080, TASK-1081, TASK-1082 (zh), TASK-1092 (zh), TASK-1084, TASK-1087; ja also TASK-1075

**Description:**
Runs the readiness gate (tech §2) per language and adds the nightly `calibration_placement_close_stale` job
to `web/scheduler.py`. Then enables `PLACEMENT_ENABLED_LANGS`: zh and en first, ja once its gate passes (PQ6,
PQ13, PQ14). PQ3 and PQ5 were answered on 2026-11-18. **Launch requires** the evidence writer live (L7), and
for zh the intro-drill fix and the tone variants (TASK-1092).

**Acceptance Criteria:**
- [ ] Gate output recorded per language; a failing language stays off.
- [ ] The nightly job runs once, under an advisory lock (the `services/irt/calibrator.py:209-229` pattern), and
  finishes each closed session.
- [ ] A `wiki/log.md` entry with database sizes before and after.

**Files to Create / Modify:**
- `web/scheduler.py` — the nightly job.
- environment config — `PLACEMENT_ENABLED_LANGS`.

**Verification:**
A production placement by the owner per enabled language (V1), and a check that its evidence reached UVK and
the next session (read-only).

---

## TASK-1089: Validation study V1–V10 [?]

**Status:** [?] Blocked — needs learners (V2 needs 10–30 retest pairs per language) and PQ16 (exclusions)
**Feature:** vocab-placement
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-1088

**Description:**
Runs tech §20 V1–V10 with read-only SQL and pure Python as data arrives, and files the results. This covers:
- V1 as a mode-effect estimate;
- V2's variance inflation from every pair;
- V4's ω̂ and implied bias;
- V6 sound pairs, V8 hidden knowledge, V9 reading credit, V10 real length.

**Acceptance Criteria:**
- [ ] Each V-row's pass/action is evaluated and recorded with its n. Failed rows open follow-up tasks: an
  ω-correction ADR (V4), an r revision of ADR-058 (V9), interval widening (V2), copy changes (V10).

**Files to Create / Modify:**
- `scripts/placement_validation.py` — new, read-only.
- `wiki/evaluations/vocab-placement-validation-<date>.md` — new.

**Verification:**
Owner review of the evaluation page.

---

## TASK-1090: Exam-level output — redesign and gate [?]

**Status:** [?] Blocked — parked: the owner answered PQ2 "No, not at the moment" (2026-11-18). Reopen only if the owner asks for a level output; it also needs V5 data (≥ 30 placements per language)
**Feature:** vocab-placement
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1089, TASK-1049

**Description:**
This replaces the draft's level line, which was removed for failing (E23). The task designs and simulates a
level output, then ships it only if it passes gates **on the copy learners would see** (tech §5.3).
Candidates:
- level strata around a stated goal level (D3L);
- a longer optional "level check";
- the goal level's own share over a named subset with a range ("of the 290 HSK 4 words the check draws from:
  about 40–70%").

**Acceptance Criteria:**
- [ ] A new ADR that explicitly revises ADR-054's v1 rationale and names the measured subset in the copy.
- [ ] In TASK-1087's harness, for the shown copy:
  - within one level for ≥ 70% of learners at every true level 1–6 (zh) and 1–4 (ja);
  - containment ≥ 90%;
  - ≥ 50% of true-level-≥ 2 learners with a lower bound ≥ 1.
- [ ] V5 run with pair outcomes, a decision rule calibrated by simulation at the achieved n under the base and
  `gamma25` models, and an equivalence rule; it is stated that V5 cannot test frame vs non-frame words.
- [ ] Re-validated after the zh pool refresh (TASK-1063) if that has landed.

**Files to Create / Modify:**
- To be listed in the ADR. Expected: `services/placement_design.py`, `services/vocabulary/word_lists.py`,
  `static/js/pages/placement.js`, `static/js/pages/knowledge.js`, i18n files, `tests/test_placement_coverage.py`.

**Verification:**
The harness gates are green and the owner has reviewed the ADR.

---

## TASK-1091: The check's meaning items become the bare instrument (LIVE-DB, owner-applied) [?]

**Status:** [?] Blocked — PQ11 (owner approval of a change to the live check's items)
**Feature:** vocab-placement
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-1076, TASK-1077

**Description:**
Makes open-ended check meaning items the same instrument as placement meaning items, so the report can pool
both (PSY M5):
- no reading line under the word (`calibration_build_items` stops returning `pronunciation` in definition
  mode, and `static/js/pages/calibration.js:243-244` hides the line);
- the rule-5 strip (`；`, `;`, `——`, `—`) on all four options;
- exclusion of rule-5 residual anchors;
- rank-1 only (coordinate with TASK-1062);
- `instrument = 'meaning_bare_v1'` on each new definition-mode response row.

**Acceptance Criteria:**
- [ ] 200 sampled zh/ja and ja/zh items carry no headword prefix in any form; the residual "key contains the
  prompt, no served foil does" share is 0 (was 13.3% zh/ja; 10.8% ja/zh after a `；`-only strip).
- [ ] New definition-mode rows carry `instrument = 'meaning_bare_v1'`; legacy rows stay NULL.
- [ ] `knowledge_calibration_inputs` pools converted check answers with placement meaning items (fixture).
- [ ] Rollback restores the old builder.

**Files to Create / Modify:**
- `migrations/calibration_build_items_bare_instrument.sql` — new.
- `migrations/calibration_build_items_bare_instrument_rollback.sql` — new.
- `static/js/pages/calibration.js` — hide the reading line on definition items.
- `wiki/features/calibration.tech.md` — through TASK-1095.

**Verification:**
A read-only sample query after apply; a local check session showing no reading under the word.

---

## TASK-1092: zh tone variants — inventory, variant generator, readiness (LIVE-DB, owner-applied; zh launch item)

**Status:** [x] Done — applied live 2026-11-22 (381 inventory rows, 2,379 character readings; 好 gives {háo}; `<@` written as `OPERATOR(pg_catalog.<@)` because live has intarray) — `migrations/calibration_zh_tones.sql` (+ character-reading table); SQL = Python on 10,390 readings
**Feature:** vocab-placement
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none
**Blocks:** TASK-1077 (zh reading items), TASK-1088 (zh launch)

**Description:**
Builds what rule 4 of tech §2 needs ([[decisions/ADR-060-zh-placement-scores-tones]]):
- the table `calibration_zh_tone_inventory` (toneless syllable → attested full tones);
- `calibration_refresh_zh_tone_inventory()`, which fills it from native zh `dim_word_senses` readings;
- `calibration_zh_tone_variants(p_pronunciation, p_vocab_id)`, which returns every valid tone variant of a
  reading in display form (tech §14).

A Python reference implementation (`services/placement_tones.py`) is ported from the research script
`wiki/evaluations/vocab-placement-research-2026-11-18/tones/tone_cover.py`, and the SQL function must agree
with it on every pool reading. Japanese long-vowel / っ / ん / voicing variants are **out of scope**: PQ3 was
answered for tones only.

**Acceptance Criteria:**
- [ ] After apply, the inventory has about 382 rows (E32); the refresh is idempotent and returns its row count.
- [ ] `calibration_zh_tone_variants` and `services/placement_tones.variants` return the same set for every zh
  pool reading (rank-1 native rows), checked by a read-only script; 0 mismatches.
- [ ] On the pool, ≥ 98% of readings have ≥ 1 variant and every band ≥ 90% (measured 99.1% and band 7 94.8%,
  E32); the counts are recorded in `wiki/log.md`.
- [ ] Unit cases (Python reference, mirrored by SQL spot checks):
  - 写 xiě → variants drawn only from tones the inventory lists for `xie`; never xiě itself;
  - 很好 hěn hǎo excludes hén hǎo (3→2 before 3, sandhi) but allows other combinations;
  - 东西 dōng xi keeps xi neutral; 一样 yí yàng never changes yí; 不是 bú shì never changes bú;
  - a polyphone (e.g. 长 cháng/zhǎng) never returns its other reading;
  - ü syllables (lǜ, nǚ) keep ü and re-mark correctly; the mark goes on a/e, on o in "ou", else the last vowel.
- [ ] No variant contains a syllable+tone absent from the inventory (grep over all pool variants).

**Technical Notes:**
- Parse the display form, not the numbered suffix (the zh normaliser is broken, E7; TASK-1074).
- Tone from the combining mark after NFD (U+0304, U+0301, U+030C, U+0300 → 1–4), 5 when none; ü is U+0308.
- Align 一/不 by character position only when the lemma's character count equals the syllable count.
- Cap at 16 variants per reading; the item builder draws one uniformly (`u_seed`).
- Run `calibration_refresh_zh_tone_inventory()` with every zh pool refresh (TASK-1063) and zh sense backfill.

**Files to Create / Modify:**
- `migrations/calibration_zh_tones.sql` — new: table, REVOKE, the two functions (SET search_path; service role).
- `migrations/calibration_zh_tones_rollback.sql` — new.
- `services/placement_tones.py` — new: pure reference implementation.
- `tests/test_placement_tones.py` — new: the unit cases above.
- `scripts/verify_zh_tone_variants.py` — new, owner-run, read-only: SQL vs Python on all pool readings, plus
  the coverage counts.

**Verification:**
`python -m pytest tests/test_placement_tones.py -q`; after the owner applies the migration,
`python scripts/verify_zh_tone_variants.py` prints 0 mismatches and the coverage per band.

---

## TASK-1093: IRT scoring v2 — item calibration and shadow model [?]

**Status:** [?] Blocked — data: per (language, L1 group), ≥ 6 exposures for ≥ 80% of frame words
**Feature:** vocab-placement
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-1089

**Description:**
Implements tech §5.4: the `calibration_item_params` table, nightly calibration (the bounded L-BFGS-B pattern
from `services/irt/calibrator.py`), EAP scoring in shadow (`result.irt_shadow`), and the per-group switch gate.
The model has θ and group means fixed at 0 and separate meaning and reading skip propensities. v1's uniform
within-band selection is kept.

**Acceptance Criteria:**
- [ ] Its own ADR revision of ADR-057, with shadow results meeting the per-group gate; no change to item
  selection without Horvitz–Thompson weights in the report estimator.

**Files to Create / Modify:**
- To be listed in the ADR.

**Verification:**
To be listed in the ADR.

---

## TASK-1094: Goal-path placement segment and hero copy [?]

**Status:** [?] Blocked — TASK-1072 (goal-path layout in the spec and page) and report OQ35 (stored goal)
**Feature:** vocab-placement
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1081, TASK-1086, TASK-1072

**Description:**
After a placement the goal-path level bars look unchanged, because placement evidence never makes a word
rated known (LRN L13). This task adds a bar segment "answered in a placement, not yet checked" (words with
`placement_correct > 0` and no direct check), visible to every tier, following Hack Chinese's assumed-known
segment. It also changes the hero copy "After about 70 answers you get a range" for learners with a placement.

**Acceptance Criteria:**
- [ ] The segment's count per level equals the number of list words in that level with `placement_only` evidence
  and a right placement answer.
- [ ] Core and Pro both see the segment; Pro rows open the words.
- [ ] Hero copy for a learner with a placement no longer mentions 70 answers.

**Files to Create / Modify:**
- `static/js/pages/knowledge.js`, `static/i18n/*.json`, and the goal-path summary fields added by TASK-1072.

**Verification:**
A local report for a test account with one placement.

---

## TASK-1095: Documentation reconciliation

**Status:** [ ] Not Started
**Feature:** vocab-placement
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** TASK-1086

**Description:**
- Correct `wiki/features/calibration.md:122-126` and `calibration.tech.md:260-266`: the check does call the
  guarded rating writer (E5).
- Add a "Placement mode" section to `calibration.tech.md`.
- Update `knowledge-report.tech.md` §2.4, §2.6 and §6.1 and the knowledge-report OQ37 to point to this feature.
- Add the schema and RPC changes to `database/schema.tech.md` and `api/rpcs.tech.md`.
- Update index, log and master.

**Acceptance Criteria:**
- [ ] No page contradicts the code on ELO writes, evidence kinds, instruments or the estimator inputs.

**Files to Create / Modify:**
- The wiki pages named above.

**Verification:**
A lint pass (CLAUDE.md §5e) shows no contradiction on these topics.

---

## TASK-1096: zh tone variants — heteronym list for single-character lemmas

**Status:** [ ] Not Started
**Feature:** vocab-placement
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-1092

**Description:**
A tone variant must never be a real reading of the prompt word (ADR-060). TASK-1092 checks a single-character
lemma against every reading its character has in the zh dictionary (`calibration_zh_char_readings`), which removed
15 of the 48 cases a pypinyin heteronym check flagged on 2026-11-19. 33 remain because no dictionary word attests
the reading; 14 of them are real, common readings that would be shown as "wrong": 强 qiǎng, 数 shǔ, 正 zhēng,
累 léi, 观 guàn, 钻 zuàn, 占 zhān, 扎 zhá, 喝 hè, 泥 nì, 可 kè, 打 dá, 轴 zhòu, 仅 jìn. This task adds a small
curated seed of heteronym readings for single-character pool lemmas (from pypinyin's MIT-licensed data, reviewed,
committed as a migration's INSERT list into `calibration_zh_char_readings`, kept by the refresh), so those variants
are excluded too.

**Acceptance Criteria:**
- [ ] The 14 real readings above are never returned by `calibration_zh_tone_variants` for their lemma; SQL and
  `services/placement_tones.variants` still agree on every pool reading.
- [ ] Coverage stays ≥ 98% of pool readings with ≥ 1 variant (99.0% before) and ≥ 90% in band 7.
- [ ] The seed's source and licence are recorded in the migration header.

**Files to Create / Modify:**
- `migrations/calibration_zh_char_readings_seed.sql` (+ rollback); `services/placement_tones.py`;
  `scripts/verify_zh_tone_variants.py`; `tests/test_placement_tones.py`.

**Verification:**
`python scripts/verify_zh_tone_variants.py` after apply: 0 mismatches; the 14 readings absent.

---

**Master list rows (for the orchestrator):**

| ID | Feature | Title | Status | Complexity | Depends On |
|----|---------|-------|--------|------------|------------|
| TASK-1074 | vocab-placement | Fix the zh reading normaliser and syllable count (LIVE-DB, owner) | Done (repo), awaiting live apply | S | — |
| TASK-1075 | vocab-placement | ja reading readiness: katakana, kana-consistent foils, ja-only refresh, refill (LIVE-DB, owner) | [~] code done; owner refresh/refill/gate | M | TASK-1077 (gate) |
| TASK-1076 | vocab-placement | Placement schema migration (LIVE-DB, owner) | Done (repo), awaiting live apply | M | — |
| TASK-1077 | vocab-placement | Placement SQL functions (LIVE-DB, owner) | Done (repo), awaiting live apply | L | TASK-1076; TASK-1092 (zh) |
| TASK-1078 | vocab-placement | Pure placement design and estimator functions | Done (repo) | M | TASK-1035 |
| TASK-1079 | vocab-placement | `knowledge_calibration_inputs` (LIVE-DB, owner) | Done (repo), awaiting live apply | M | TASK-1076, TASK-1034 |
| TASK-1080 | vocab-placement | Placement service and routes | Done (repo) | L | TASK-1077, TASK-1078, TASK-1079 |
| TASK-1081 | vocab-placement | Placement evidence: pair-based BKT, A2/A2r on the native sense (LIVE-DB, owner) | Done (repo), awaiting live apply | L | TASK-1076, TASK-1080 |
| TASK-1082 | vocab-placement | Intro drill (and prestudy) show zh pinyin for diacritic-only readings | Done (repo) | S | — |
| TASK-1083 | vocab-placement | Placement feeds test selection and the rating writer | [?] OQ33 | M | TASK-1080 |
| TASK-1084 | vocab-placement | Placement page and i18n | Done (repo) | L | TASK-1080 |
| TASK-1085 | vocab-placement | Entry points incl. onboarding gate | [?] PQ7 | S | TASK-1084, TASK-1040 |
| TASK-1086 | vocab-placement | Report integration (LIVE-DB, owner) | [ ] | L | TASK-1078, TASK-1079, TASK-1081, TASK-1036, TASK-1039, TASK-1040, TASK-1044 |
| TASK-1087 | vocab-placement | Simulation regression harness (V0) | Done (repo) | M | TASK-1078 |
| TASK-1088 | vocab-placement | Launch per language (LIVE env, owner) | [~] code done (nightly close, gate script); owner steps | S | TASK-1080, TASK-1081, TASK-1082, TASK-1084, TASK-1087, TASK-1092 (zh) (ja: TASK-1075) |
| TASK-1089 | vocab-placement | Validation study V1–V10 | [?] learners | M | TASK-1088 |
| TASK-1090 | vocab-placement | Exam-level output — redesign and gate | [?] parked (owner PQ2: not now), V5 | L | TASK-1089, TASK-1049 |
| TASK-1091 | vocab-placement | Check meaning items become the bare instrument (LIVE-DB, owner) | [?] PQ11 | M | TASK-1076, TASK-1077 |
| TASK-1092 | vocab-placement | zh tone variants: inventory, generator, readiness (LIVE-DB, owner; zh launch item) | Done (repo), awaiting live apply | M | — |
| TASK-1093 | vocab-placement | IRT scoring v2 | [?] data | XL | TASK-1089 |
| TASK-1094 | vocab-placement | Goal-path placement segment and hero copy | [?] TASK-1072 | S | TASK-1081, TASK-1086, TASK-1072 |
| TASK-1095 | vocab-placement | Documentation reconciliation | [ ] | S | TASK-1086 |
| TASK-1096 | vocab-placement | zh tone variants: heteronym list for single-character lemmas | [ ] | S | TASK-1092 |
