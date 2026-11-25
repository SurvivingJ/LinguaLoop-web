---
title: "zh/ja Content Seeding (staged exercise assets + topics) — Task Breakdown"
feature: zh-ja-content-seeding
prose_page: none  # operational batch; the spec is this file + the package READMEs
tech_page: ../decisions/ADR-049-exercise-content-in-storage.md
total_tasks: 10
done: 0
---

# zh/ja Content Seeding — Task Breakdown

Filed 2026-11-22. **Draft for owner review** (task decomposition is a design act — see
CLAUDE.md §5d). Nothing in this file has been applied to the database.

## What is staged (2026-11-17 → 2026-11-19)

| Item | Where | Size |
|------|-------|------|
| ja exercise-asset package | `data/exercise_seeding/ja/upload_2026-11-17/` (archive: `data/exercise_seeding/ja/archive/upload_2026-11-17.tar.gz`) | 3,298 senses, 23,086 `word_assets` rows, 7,100 UPDATEs, 38 SQL chunks |
| zh exercise-asset package | `data/exercise_seeding/zh/upload_2026-11-19/` (archives: `…/zh/archive/upload_2026-11-19.tar.gz` + `…_apply_all.sql.gz`) | 15,624 senses, 109,368 `word_assets` rows, 31,248 UPDATEs, 179 SQL chunks |
| Run records (one reviewed JSON per sense) | `data/exercise_seeding/{ja,zh}/archive/new_r*.tar.gz`; older restored runs in `main` history (`0dce7d1` ja, `cfb6fd1` zh) | ja r0506–r0539, zh r0902–r1890 (989 runs, all finished) |
| Topic batch | `data/topics/staged/2026-11-17/` | 573 topics (zh 315, ja 325, 67 shared), 35 categories |
| Staging tools | `scratch_offline/staging/` (`staged_check.py`, `overwrite_report.py`, `rest_snapshot.py`); `data/exercise_seeding/tools/archive/README.md` lists every archive | — |

How the assets were made: `.claude/skills/fat-seed-authoring/SKILL.md` (tool-free `claude -p`
pipeline; Sonnet core, Haiku audits/variants/review), assembled through the real uploader under
the offline shim (`scratch_offline/run.py`), packaged by `scratch_offline/package_upload.py`
with `--exclude-csv` (senses that already had a `prompt1_core` row on 2026-11-17 are left out:
ja 3,151, zh 7,786). Each package README has a "Staging notes … NOT applied" section.

**QA spot-check (Opus judge, rubric v3, 36 senses each):** ja mean 6.95, zh mean 6.80. About
19–22% of senses carry a fatal defect, almost all the same pattern: a level_3 distractor or a
level_6/level_7 "incorrect" sentence that is actually acceptable. Judge files:
`wf2/<run>/fat_seed/judge.reviewed.v3.opus-medium.json` (ja r0510/r0522/r0535; zh r1003/r1420/r1777).

**Drift check (2026-11-22, `staged_check.py`, read-only):** every staged sense exists, 0 edited
since the 2026-11-17 snapshot, 0 lemma/semantic_class changes, 0 with `word_assets`, 0 with
`exercises`. 28 zh staged senses are in `calibration_anchor_blocklist` (their exercises would be
inserted inactive by trigger `exercises_sense_quarantine`).

## The open decision: database space (blocks TASK-1037 onward)

Live 2026-11-22: database **362 MB** of the Free plan's 500 MB; `exercise-content` bucket 144 MB.
Estimated growth if everything is applied (per-sense sizes scaled from live zh/ja rows):

| Added | zh 15,624 | ja 3,298 |
|-------|-----------|----------|
| `word_assets` rows | ~116 MB | ~32 MB |
| `exercises` rows (no content since ADR-049; ~13 per sense, ~520 B each incl. indexes) | ~106 MB | ~23 MB |
| `storage.objects` rows (~1.6 KB per file) | ~25 MB | ~5 MB |
| Dictionary UPDATE churn (dead tuples) | ~12 MB | ~3 MB |
| Render judge logs in `llm_calls` (unless archived as you go) | ~35 MB | ~8 MB |

Topics add ~13 MB. Total **+330–380 MB → ~690–740 MB**, over the cap. Storage would grow
144 → ~380 MB (peak ~620 MB before a sweep), inside the 1 GB Free limit. The pilot
(TASK-1037) replaces these estimates with measured numbers.

Options (TASK-1034): **A** Supabase Pro (8 GB) and apply everything; **B** stay on Free: topics +
all ja + ~2,000 most frequent zh senses now; **C** stay on Free and first move `word_assets`
content to Storage (renderer, admin re-render, typed/split generators and
`v_ladder_judge_reject_rates` read it; `exercises.word_asset_id` is a FK, so rows stay).

## Order

TASK-1034 and TASK-1042 are owner decisions. TASK-1041 (topics) is independent. TASK-1035 →
1036 → 1037 (pilot) → 1038 → 1039 → 1040 → 1043. Every live write is an **operator task**:
the owner approves it in the session that runs it.

---

## TASK-1034: Decide the database-space approach

**Status:** [?] Awaiting owner decision
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Pick option A, B or C above. The choice sets which senses TASK-1035 packages and whether
TASK-1038/1039 run once or stop at a size line.

**Acceptance Criteria:**
- [ ] Decision recorded in this file and in `wiki/log.md`
- [ ] If B: the zh subset rule written down (e.g. top N by `dim_vocabulary.frequency_rank` Zipf, N chosen so the estimate stays under 470 MB)
- [ ] If C: an ADR filed before any work starts

**Technical Notes:** A needs no code. B needs only a sense list. C is a multi-day refactor in the
style of ADR-049 and leaves the database near the cap.

**Files to Create / Modify:** `wiki/tasklist/zh-ja-content-seeding.tasks.md`, `wiki/log.md`

**Verification:** The decision is in both files.

---

## TASK-1035: Rebuild the packages for the current database

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-1034

**Description:**
Re-package both languages from the archived writes (`payload_all_writes.tar.gz`) so that the
UPDATEs follow the 2026-11-12 POS rule and the package holds only senses we want. No database
writes.

**Acceptance Criteria:**
- [ ] ja package has no `part_of_speech` UPDATE that replaces a non-null live value (68 today); NULL fills stay
- [ ] zh package excludes the 28 blocklisted senses (`calibration_anchor_blocklist`)
- [ ] If option B: the zh package holds only the chosen subset
- [ ] `staged_check.py` on each new package reports 0 for `senses_updated_since_snapshot`, `senses_with_word_assets`, `senses_with_exercises`
- [ ] New `overwrites_live_values.csv` per package; README staging notes updated

**Technical Notes:**
- `scratch_offline/package_upload.py WRITES OUT --lang L --exclude-csv CSV`: build the exclude CSV
  as the original one (`data/exercise_seeding/tools/archive/staging_tools.tar.gz`: `exclude_{ja,zh}.csv`)
  plus the blocklisted / out-of-subset sense ids.
- Drop the ja POS overwrites by filtering the writes.jsonl before packaging: for `dim_vocabulary`
  UPDATEs of language 3, remove the `part_of_speech` key when the live value is non-null.
- zh `part_of_speech` UPDATEs can stay: since 2026-11-22 the trigger stores `名词` as `noun`
  (original in `part_of_speech_raw`), which is the intended zh model override.
- `pronunciation` (zh 3,578: `shì (shi4)` → `shì`) and `semantic_class` (zh 311, ja 189) overwrites
  stay unless the owner says otherwise: plain pinyin is what every sense with exercises already
  has, and the semantic class matches the core the exercises are rendered from.
- The snapshot in `scratch_offline/snap/` is git-ignored; refresh it with
  `python scratch_offline/staging/rest_snapshot.py ja zh` if more than a few days old, and pass
  the new time to `staged_check.py --since`.

**Files to Create / Modify:** `data/exercise_seeding/{ja,zh}/upload_<date>/` (git-ignored; archive the result as before)

**Verification:** `python scratch_offline/staging/staged_check.py data/exercise_seeding/zh/upload_<date>` (and ja) prints the zeros above.

---

## TASK-1036: REST applier for a staged package

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
The cloud container has `psql` but no database password, and `apply_all.sql` is too large for
the SQL editor. Write `scripts/apply_staged_word_assets.py` that replays a package through
PostgREST with the service key: `word_assets` upserts on `(sense_id, asset_type)` and the
`dim_vocabulary` / `dim_word_senses` UPDATEs, in sense batches, idempotent.

**Acceptance Criteria:**
- [ ] `--package DIR --lang {ja,zh} [--senses-file F] [--limit N] [--dry-run]`
- [ ] Never writes `exercises` and never touches a sense that already has `exercises` rows
- [ ] Writes the same rows as `apply_all.sql` (test: dry-run diff against the SQL for 20 senses)
- [ ] Resumable: a re-run skips senses whose 7 assets already match
- [ ] Offline unit tests with a fake client

**Technical Notes:** Read `word_assets.csv` and the UPDATE statements' source
(`payload_all/writes.jsonl` filtered by the package's sense ids), not the SQL text. Use
`services.supabase_factory.get_supabase_admin()`. `word_assets.id` is `GENERATED ALWAYS`; do not send it.

**Files to Create / Modify:** `scripts/apply_staged_word_assets.py`, `tests/test_apply_staged_word_assets.py`

**Verification:** `pytest tests/test_apply_staged_word_assets.py`; `--dry-run --limit 20` prints the planned writes.

---

## TASK-1037: Pilot — 100 zh + 50 ja senses end to end (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1034, TASK-1035, TASK-1036, TASK-1042

**Description:**
Apply, render and voice a small slice to measure the real cost per sense before scaling up.

**Acceptance Criteria:**
- [ ] Assets applied (`apply_staged_word_assets.py --limit`), then `verify.sql` counts match
- [ ] Rendered: `python scripts/render_existing_assets.py --language zh --sense-ids …` (live judges via OpenRouter; writes go through `store.write_sense`, file first)
- [ ] `exercises`: `count(*) = count(word_asset_id)` for the pilot senses; one Storage file per sense under `exercise-content/{zh,ja}/`
- [ ] Audio: `python scripts/backfill_exercise_audio.py --language zh --cap …`, then `python scripts/sweep_exercise_content.py --language all` (dry run) and `--apply`
- [ ] Measured and recorded here: DB bytes per sense, Storage bytes per sense, judge cost per sense, render seconds per sense, judge reject rate
- [ ] A few pilot words checked in the app (Practice and prestudy)

**Technical Notes:** Run from current `main` code (the branch that staged the packages predates
the cut-over). Check `pg_database_size` before and after.

**Files to Create / Modify:** this file (measurements), `wiki/log.md`

**Verification:** The measurements table is filled in; the app serves the pilot words.

---

## TASK-1038: Apply the remaining assets in tranches (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1037

**Description:** Apply the rest of the packages in tranches of ~2,000 senses, ja first.

**Acceptance Criteria:**
- [ ] Database size checked after every tranche; on the Free plan stop at 470 MB
- [ ] `verify.sql` per language matches the package counts
- [ ] `VACUUM (ANALYZE) dim_vocabulary, dim_word_senses` after the last tranche

**Technical Notes:** Tranches keep a mistake small and let the size line hold.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `verify.sql` output recorded in the log.

---

## TASK-1039: Render the remaining senses (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** L (1-2d)
**Depends On:** TASK-1038

**Description:** Render every applied sense with `scripts/render_existing_assets.py`, in
parallel shards (disjoint sense-id lists), archiving judge logs and sweeping after each shard.

**Acceptance Criteria:**
- [ ] Every applied sense has exercises or a logged reason (0 rows rendered / blocked)
- [ ] `count(*) = count(word_asset_id)` on `exercises` for the new senses
- [ ] `sweep_exercise_content.py --language all --apply` after each shard
- [ ] `llm_calls` judge rows archived to the `llm-logs-archive` bucket if the size line needs it

**Technical Notes:** The script skips senses that already have rows, so shards can be re-run.
Judge spend is watched by the budget ceiling; the pilot gives the per-sense cost.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** Count query above; sweep report shows no orphan versions.

---

## TASK-1040: Audio for the new listening items (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1039

**Description:** `python scripts/backfill_exercise_audio.py --language {zh,ja}` (Azure TTS to R2;
nightly `--cap`), then the sweep, because each touched sense gets a new content version.

**Acceptance Criteria:**
- [ ] No active L1 phonetic / listening item for a new sense lacks `audio_url` (`--report-only`)
- [ ] Sweep applied afterwards

**Technical Notes:** Failures queue in `generation_queue` and the item still works as reading.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `backfill_exercise_audio.py --language zh --report-only` reports 0 missing.

---

## TASK-1041: Import the 573 staged topics (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:** Import `data/topics/staged/2026-11-17/<category>.json` (35 files) with
`python scripts/run_topic_import.py -f <file> -t "<Category>"`, then stamp tiers.

**Acceptance Criteria:**
- [ ] Each file imported (gatekeeper and novelty on); rejects listed in the log
- [ ] `stamp_tiers.sql` run afterwards (the importer still drops `target_age_tier`), or the importer patched to carry it
- [ ] 0 new topics without a tier

**Technical Notes:** `--dry-run` each file first. The category name per file is in the README
table. ~13 MB of database (topic embeddings).

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `select count(*) from topics where target_age_tier is null` returns the same number after the import as just before it.

---

## TASK-1042: Decide on the level_6 "incorrect sentence is correct" defect before render

**Status:** [?] Awaiting owner decision
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
About 19–22% of sampled senses have a "wrong" sentence or distractor that is acceptable
language. Render inserts each sense once, so a fix must come before TASK-1037. Options: accept
(the renderer's `judge_ladder_sentence_validity` drops some at render time; the pilot measures
how many survive), or re-run the level_6 audit with a stricter prompt over the staged documents
before re-packaging.

**Acceptance Criteria:**
- [ ] Decision recorded here and in `wiki/log.md`

**Technical Notes:** Prompt changes to the production authoring configuration need owner approval (fat-seed SKILL rule).

**Files to Create / Modify:** this file, `wiki/log.md`

**Verification:** Decision recorded.

---

## TASK-1043: Close-out

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** TASK-1040, TASK-1041

**Description:** Final checks and wiki update after everything is applied.

**Acceptance Criteria:**
- [ ] `v_ladder_judge_reject_rates` reviewed for the new senses
- [ ] Database and Storage sizes recorded
- [ ] `wiki/database/schema.tech.md` row counts, index, log and master list updated

**Files to Create / Modify:** `wiki/log.md`, `wiki/index.md`, `wiki/tasklist/master.md`, this file

**Verification:** Log entry with final sizes and counts.
