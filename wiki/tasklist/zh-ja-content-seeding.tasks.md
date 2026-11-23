---
title: "zh/ja Content Seeding — every generated word and exercise asset not yet in the database — Task Breakdown"
feature: zh-ja-content-seeding
prose_page: none  # operational batch; the spec is this file + the package READMEs
tech_page: ../decisions/ADR-049-exercise-content-in-storage.md
total_tasks: 13
done: 0
---

# zh/ja Content Seeding — Task Breakdown

Filed 2026-11-22, **rewritten 2026-11-23** after an audit of every Claude Code session and all 58
remote branches. **Draft for owner review** (task decomposition is a design act, CLAUDE.md §5d).
Nothing in this file has been applied to the database.

Task ids: first filed as TASK-1034–1043, renumbered to **TASK-1097–1109** because the unmerged
branches `claude/beautiful-planck-0fftk4` and `claude/busy-hawking-pvgz8d` (knowledge report)
already use TASK-1034–1096.

## 1. Inventory: generated but not in the database (checked 2026-11-23)

Compared by sense id / lemma against the live database (read-only REST and SQL).

### 1a. Exercise assets (`word_assets` material for senses that already exist)

| Source | Where | Senses | Not in DB | Review |
|--------|-------|-------:|----------:|--------|
| **zh final package** (session "Chinese senses word assets pipeline", 2026-10-30 → 11-09) | branch `claude/zh-word-assets-10k`, commit `e2747db` (**not merged**; PR #19 merged only the 11-07 interim commit `cfb6fd1`): `data/exercise_seeding/zh/upload/` (`apply_all.sql.gz`, `word_assets.csv.gz`, 164 chunks) + records `data/exercise_seeding/zh/archive/zh_fatseed_records.tar.gz.part_00–02` | 16,361 | **11,199** (5,162 already live) | Sonnet core, Haiku review, then an **Opus/low second review of every sense**: +0.78 to +0.96 points, fatal share ~0.04–0.15 by run range ([[evaluations/zh-fat-seed-word-assets-2026-11-09]] on that branch) |
| **zh package, this effort** (2026-11-17 → 11-19) | `data/exercise_seeding/zh/upload_2026-11-19/` (archives on `claude/hopeful-johnson-iv4k69`, PR #43) | 15,624 | 15,624 | Haiku review only (zh effort high); Opus spot-check 6.80 mean, ~19% of senses with a fatal defect |
| **ja package, this effort** | `data/exercise_seeding/ja/upload_2026-11-17/` (archives on PR #43; 3,183 of its senses restored from `0dce7d1`) | 3,298 | 3,298 | Haiku review; spot-check 6.95, ~22% fatal |

**Overlap.** 10,677 zh senses are in both zh packages: 4,877 because this effort restored the 11-07
interim records, about 5,800 because its worklist was built from the live database and could not
see the unmerged final package. For those, **use the final package** (stronger review).

**zh set to apply = 16,146 senses**: 11,199 from the final package + 4,947 only in this effort's
package; minus 32 in `calibration_anchor_blocklist` (25 + 7) = **16,114** (lists:
draft lists committed in `data/exercise_seeding/apply_sets/`: `zh_from_final.txt`, `zh_from_2026-11-19.txt`, `ja.txt`).
**ja set = 3,298.** About 132,000 `word_assets` rows; ~245,000 exercises once rendered.

**Drift (2026-11-23):** all 16,146 + 3,298 senses exist; none has `word_assets` or `exercises`.
2,608 of the final package's not-live senses were edited after its 2026-11-09 build. Their UPDATEs
would replace a different non-null value in 3,512 `pronunciation` (numbered pinyin → plain, the
format every sense with exercises already uses) and 276 `semantic_class`. The ja package would
replace 68 ja `part_of_speech` tags (against the 2026-11-12 rule; must be dropped). zh POS label
differences no longer matter: since 2026-11-22 the trigger stores `名词` as `noun`.

### 1b. New dictionary words (lemmas not in `dim_vocabulary`)

| Source | Where | Words | Not in DB | Content |
|--------|-------|------:|----------:|---------|
| ja 5k words (commit `f1c4c303`, 2026-10-30; no log entry, never uploaded) | `main`: `data/sense_seeding/ja_5k/ja_new_senses_5k.csv` (+ `candidates/`, `defs/`, `worklist.tsv`) | 4,996 lemmas | **4,913** (83 exist, 76 with a ja sense) | reading, POS, ja simple + standard, en simple + standard, zh simple + standard, ja example sentence |

The live dictionary has 3,533 ja words, so this more than doubles Japanese. These words have **no
exercise assets** yet: fat-seed needs a sense id. The zh sense batches (`data/sense_seeding/zh/wave_a`,
133/133) were all uploaded.

### 1c. Topics

573 staged topics in `data/topics/staged/2026-11-17/` (zh 315, ja 325, 67 shared). The 11-14 zh
HSK7 daily-life and data-analysis topic lists (branch `claude/clever-feynman-ixf8id`) are already live.

### 1d. Not generated (for the record)

The 100-test ja N5/N4 plan (`data/topic_plans/` on `claude/optimistic-volta-totkli`) was never run:
ja still has 5 tests at difficulty 1 and 5 at difficulty 3. 31 listening tests still lack audio
(session "listening-test audio generation"). Neither is in scope here.

**Not visible to this audit:** anything another session kept only on its own container disk.

## 2. The space problem (TASK-1097)

Live 2026-11-23: database **362 MB** of the Free plan's 500 MB; `exercise-content` bucket 144 MB.
Per-sense costs scaled from live rows (the pilot replaces them with measurements):

| Added | zh 16,114 | ja 3,298 | ja 5k words |
|-------|----------:|---------:|------------:|
| `word_assets` | ~119 MB | ~32 MB | (~47 MB once authored) |
| `exercises` rows (~13/sense, ~520 B incl. indexes) | ~110 MB | ~23 MB | (~35 MB) |
| `storage.objects` (~1.6 KB/file) | ~26 MB | ~5 MB | (~8 MB) |
| UPDATE churn | ~13 MB | ~3 MB | — |
| Render judge logs (`llm_calls`, unless archived) | ~35 MB | ~8 MB | (~12 MB) |
| Dictionary rows (vocab + ja/en/zh sense rows + vectors) | — | — | ~13 MB |

Topics ~13 MB. **Everything except the 5k words' exercises: +~400 MB → ~760 MB. With them: ~870 MB.**
Storage: 144 → ~390 MB, peak ~650 MB before a sweep (Free limit 1 GB).

Options: **A** Supabase Pro (8 GB) and apply everything. **B** Stay on Free: topics + all ja (~84 MB)
leaves room for only ~1,300–1,500 zh senses. **C** Stay on Free and first move `word_assets` content
to Storage (renderer, admin re-render, typed/split generators and `v_ladder_judge_reject_rates` read
it; `exercises.word_asset_id` is a FK, so rows stay): saves ~150 MB of the new load plus ~75 MB
existing, still near the cap. A multi-day refactor needing its own ADR.

## 3. Order

Owner decisions first: TASK-1097 (space), TASK-1098 (level_6 defect). Independent now:
TASK-1099 (secure the final package), TASK-1101 (applier), TASK-1106 (topics).

```
1097, 1098 ─┐
1099 ───────┼─> 1100 (build sets) ─> 1102 (pilot) ─> 1103 (apply) ─> 1104 (render) ─> 1105 (audio) ─┐
1101 ───────┘                                                                                        ├─> 1109
1106 (topics) ───────────────────────────────────────────────────────────────────────────────────────┤
1107 (ja 5k words) ─> 1108 (author their assets; then they join 1102–1105 as a second wave) ──────────┘
```

Every live write is an **operator task**: the owner approves it in the session that runs it.

---

## TASK-1097: Decide the database-space approach

**Status:** [?] Awaiting owner decision
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Pick option A, B or C (§2). It sets which senses TASK-1100 packages, whether TASK-1103/1104 stop at
a size line, and whether the ja 5k words get exercises (TASK-1108) now.

**Acceptance Criteria:**
- [ ] Decision recorded here and in `wiki/log.md`
- [ ] If B: the subset rule written down (e.g. zh top N by `dim_vocabulary.frequency_rank` Zipf, N chosen so the estimate stays under 470 MB)
- [ ] If C: an ADR filed before any work starts

**Technical Notes:** A needs no code. B needs a sense list. C is ADR-049-sized.

**Files to Create / Modify:** this file, `wiki/log.md`

**Verification:** The decision is in both files.

---

## TASK-1098: Decide how to handle the level_6 "incorrect sentence is correct" defect

**Status:** [?] Awaiting owner decision
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
The largest defect class in every sample: a level_3 distractor or a level_6/level_7 "wrong" sentence
that is acceptable language (this effort's samples ~19–22% of senses; the final zh package lower
after its Opus review, but still its largest class). Render inserts each sense once, so a fix must
come before TASK-1102. Options: accept (the renderer's `judge_ladder_sentence_validity` drops some at
render time; the pilot measures how many survive); or run a stricter level_6/level_7 audit over the
staged documents (this effort's 4,947 zh + 3,298 ja first) and re-package.

**Acceptance Criteria:**
- [ ] Decision recorded here and in `wiki/log.md`

**Technical Notes:** Prompt changes to the production authoring configuration need owner approval
(fat-seed SKILL rule).

**Files to Create / Modify:** this file, `wiki/log.md`

**Verification:** Decision recorded.

---

## TASK-1099: Secure the final zh package from the unmerged branch

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** none

**Description:**
The best zh assets exist only on `claude/zh-word-assets-10k` (`e2747db`). Bring its package and
records onto `main` (or a long-lived branch the owner names) so they cannot be lost when old
branches are cleaned up, and record the location in the wiki.

**Acceptance Criteria:**
- [ ] `e2747db`'s `data/exercise_seeding/zh/upload/` (gzipped SQL, gzipped CSV, `verify.sql`, README; chunks optional), `data/exercise_seeding/zh/archive/zh_fatseed_records.tar.gz.part_*`, `data/exercise_seeding/zh/issues/` and `wiki/evaluations/zh-fat-seed-word-assets-2026-11-09.md` reachable from `main`
- [ ] No file over 50 MB (GitHub warns at 50 MB, refuses at 100 MB)
- [ ] `wiki/index.md` links the evaluation page; log entry

**Technical Notes:** `git checkout e2747db -- <paths>` on a branch from `main`, commit, PR. The
interim files of `cfb6fd1` are already on `main` and are superseded; keep them only if the owner
wants the history.

**Files to Create / Modify:** the paths above, `wiki/index.md`, `wiki/log.md`

**Verification:** `git ls-tree -r origin/main -- data/exercise_seeding/zh/archive` lists the three parts.

---

## TASK-1100: Build the apply sets (combined zh, rebuilt ja)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1097, TASK-1098, TASK-1099

**Description:**
Produce one package per language containing exactly the senses to apply, each in its best version,
with UPDATEs that follow the current dictionary rules. No database writes.

**Acceptance Criteria:**
- [ ] zh: 11,174 senses from the final package (its 11,199 not-live minus 25 blocklisted) + 4,940 from `upload_2026-11-19` (its 4,947 not in the final package minus 7 blocklisted), or the TASK-1097 subset of them
- [ ] ja: `upload_2026-11-17` without the 68 `part_of_speech` UPDATEs that replace a non-null ja tag (NULL fills stay)
- [ ] Sense-id lists in `data/exercise_seeding/apply_sets/` recomputed after TASK-1097 (draft lists of 2026-11-23 already committed there)
- [ ] `staged_check.py` on each set: 0 with `word_assets`, 0 with `exercises`
- [ ] Overwrite report per set against a fresh snapshot; the README lists what is kept (pinyin format, semantic_class) and what was dropped

**Technical Notes:**
- Both packages come from `scratch_offline/package_upload.py`, so they share the formats:
  `word_assets.csv` rows and `UPDATE dim_vocabulary|dim_word_senses SET … WHERE id = N;` lines
  (a dim_vocabulary UPDATE precedes its sense's dim_word_senses UPDATE). Select per sense id from each
  source and write one combined set; or let TASK-1101 take `(package, sense-list)` pairs directly.
- The final package was built against the 2026-11-09 database: 2,608 of its senses were edited
  later. The only fields its UPDATEs set are `ipa_pronunciation`, `morphological_forms`,
  `pronunciation`, `register` (senses) and `semantic_class`, `part_of_speech` (vocab); against the
  2026-11-17 snapshot they replace 3,512 pronunciations (format only) and 276 semantic classes.
  Refresh the snapshot (`python scratch_offline/staging/rest_snapshot.py ja zh`) and re-run
  `python scratch_offline/staging/package_updates.py <apply_all.sql.gz> --senses <list> --out <csv>`
  (on the draft list today: 3,488 pronunciations, 276 semantic classes).
- Blocklisted senses' exercises would be inserted inactive by trigger `exercises_sense_quarantine`; leave them out.

**Files to Create / Modify:** `data/exercise_seeding/apply_sets/*` (lists + README; the packages
themselves stay git-ignored and archived)

**Verification:** `python scratch_offline/staging/staged_check.py <set dir>` prints zeros for assets and exercises; counts match the criteria.

---

## TASK-1101: REST applier for a staged package

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
The cloud container has `psql` but no database password, and the packages are too large for the
SQL editor (zh ~190 MB of SQL). Write `scripts/apply_staged_word_assets.py` that replays a package
through PostgREST with the service key: `word_assets` upserts on `(sense_id, asset_type)` and the
dictionary UPDATEs, in sense batches, idempotent.

**Acceptance Criteria:**
- [ ] `--package DIR --lang {ja,zh} [--senses-file F] [--limit N] [--dry-run]`; accepts the gzipped files of the final zh package
- [ ] Never writes `exercises`; skips a sense that already has `exercises` rows
- [ ] Writes the same rows as the package SQL (test: dry-run diff against `apply_all.sql` for 20 senses)
- [ ] Resumable: a re-run skips senses whose 7 assets already match
- [ ] Prints `pg_database_size` before and after (via a read-only RPC or the SQL editor note) so the operator can hold a size line
- [ ] Offline unit tests with a fake client

**Technical Notes:** Read `word_assets.csv` and parse the UPDATE lines with
`scratch_offline/staging/package_updates.py` (`iter_sense_updates`, `parse_set`; tested on both packages). Use
`services.supabase_factory.get_supabase_admin()`. `word_assets.id` is `GENERATED ALWAYS`; do not send it.

**Files to Create / Modify:** `scripts/apply_staged_word_assets.py`, `tests/test_apply_staged_word_assets.py`

**Verification:** `pytest tests/test_apply_staged_word_assets.py`; `--dry-run --limit 20` prints the planned writes.

---

## TASK-1102: Pilot — 100 zh + 50 ja senses end to end (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1100, TASK-1101

**Description:**
Apply, render and voice a small slice to measure real cost per sense before scaling up. Take the zh
pilot from both sources (e.g. 70 final package + 30 this effort) so their quality can be compared live.

**Acceptance Criteria:**
- [ ] Assets applied with `apply_staged_word_assets.py --senses-file`; `verify.sql` counts match
- [ ] Rendered: `python scripts/render_existing_assets.py --language zh --sense-ids …` (live judges via OpenRouter; writes through `store.write_sense`, file first)
- [ ] `exercises`: `count(*) = count(word_asset_id)` for the pilot senses; one Storage file per sense under `exercise-content/{zh,ja}/`
- [ ] Audio: `python scripts/backfill_exercise_audio.py --language zh --cap …`, then `python scripts/sweep_exercise_content.py --language all` (dry run) and `--apply`
- [ ] Measured and recorded here: DB bytes per sense, Storage bytes per sense, judge cost and seconds per sense, render-time reject rate per source
- [ ] A few pilot words checked in the app (Practice and prestudy)

**Technical Notes:** Run from current `main` code. Record `pg_database_size` before and after.

**Files to Create / Modify:** this file (measurements), `wiki/log.md`

**Verification:** The measurements table is filled in; the app serves the pilot words.

---

## TASK-1103: Apply the remaining assets in tranches (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1102

**Description:** Apply the rest of the sets in tranches of ~2,000 senses: ja first, then zh by frequency.

**Acceptance Criteria:**
- [ ] Database size checked after every tranche; on the Free plan stop at 470 MB
- [ ] `verify.sql` per language matches the set counts
- [ ] `VACUUM (ANALYZE) dim_vocabulary, dim_word_senses` after the last tranche

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `verify.sql` output recorded in the log.

---

## TASK-1104: Render the remaining senses (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** L (1-2d)
**Depends On:** TASK-1103

**Description:** Render every applied sense with `scripts/render_existing_assets.py`, in parallel
shards (disjoint sense-id lists), archiving judge logs and sweeping after each shard.

**Acceptance Criteria:**
- [ ] Every applied sense has exercises or a logged reason (0 rows rendered / blocked)
- [ ] `count(*) = count(word_asset_id)` on `exercises` for the new senses
- [ ] `sweep_exercise_content.py --language all --apply` after each shard
- [ ] `llm_calls` judge rows archived to the `llm-logs-archive` bucket when the size line needs it

**Technical Notes:** The script skips senses that already have rows, so shards can be re-run. The
budget ceiling watches judge spend; the pilot gives the per-sense cost.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** Count query above; the sweep report shows no orphan versions.

---

## TASK-1105: Audio for the new listening items (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-1104

**Description:** `python scripts/backfill_exercise_audio.py --language {zh,ja}` (Azure TTS to R2;
nightly `--cap`), then the sweep, because each touched sense gets a new content version.

**Acceptance Criteria:**
- [ ] No active L1 phonetic / listening item for a new sense lacks `audio_url` (`--report-only`)
- [ ] Sweep applied afterwards

**Technical Notes:** Failures queue in `generation_queue`; the item still works as reading.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `backfill_exercise_audio.py --language zh --report-only` reports 0 missing.

---

## TASK-1106: Import the 573 staged topics (operator)

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

**Technical Notes:** `--dry-run` each file first. The category per file is in the README table. ~13 MB.

**Files to Create / Modify:** `wiki/log.md`

**Verification:** `select count(*) from topics where target_age_tier is null` returns the same number after the import as just before it.

---

## TASK-1107: Load the 4,913 new Japanese words into the dictionary (operator)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-1097

**Description:**
`data/sense_seeding/ja_5k/ja_new_senses_5k.csv` holds 4,996 ja lemmas with reading, POS and
definitions in ja / en / zh at two levels plus an example; 4,913 are not in `dim_vocabulary`. Write a
loader that creates the `dim_vocabulary` rows and their senses from this file (no regeneration),
then embed. Words already in the dictionary are skipped, not overwritten.

**Acceptance Criteria:**
- [ ] `scripts/load_ja_new_words.py --file … [--limit N] [--dry-run]`: one `dim_vocabulary` row per new lemma (reading, POS through the normalise trigger), ja-defined senses at both levels, en and zh gloss rows (`definition_language_id` 2 and 1) as the cross-language-gloss path writes them
- [ ] The 83 existing lemmas are reported, not written
- [ ] Lemma checked against the ja tokenizer (MeCab/UniDic): a lemma the tokenizer reduces to another word is reported, not created (lesson of 2026-11-12)
- [ ] Embeddings written (`python -m scripts.backfill_sense_embeddings --language 3`), 0 senses left without a vector
- [ ] Offline tests with a fake client; a 50-word dry run reviewed by the owner before the full load

**Technical Notes:** Reuse the sense write path of `scripts/upload_senses.py` and the gloss upload of
the `cross-language-glosses` skill rather than inserting rows by hand. The 2026-10-30 seeding runs
logged "OpenAI API key is required for embeddings": check the embedding provider key before the
load. ~13 MB of database.

**Files to Create / Modify:** `scripts/load_ja_new_words.py`, `tests/test_load_ja_new_words.py`, `wiki/log.md`

**Verification:** `select count(*) from dim_vocabulary where language_id = 3` rises by the loaded count; every new sense has an embedding.

---

## TASK-1108: Author exercise assets for the new Japanese words (no DB writes)

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** infra
**Complexity:** XL (>2d)
**Depends On:** TASK-1107, TASK-1098

**Description:**
Run the fat-seed pipeline (`.claude/skills/fat-seed-authoring/SKILL.md`) over the senses TASK-1107
creates, then package them like the other sets. They then go through TASK-1102–1105 as a second wave.

**Acceptance Criteria:**
- [ ] Worklist exported from the live database after TASK-1107
- [ ] Every sense reviewed (with the review setting TASK-1098 decides) or listed in an issues file with its reason
- [ ] Package + overwrite report + Opus spot-check of ≥ 36 senses; archives pushed in files ≤ 50 MB

**Technical Notes:** ja uses `--skip-l1` (the renderer builds level_1 from the phonetic trie). This
effort's ja throughput: ~35 runs/hour at 20 workers, ≤ 12 senses per run. Cloud containers restart
often; the pipeline resumes from finished work.

**Files to Create / Modify:** `data/exercise_seeding/ja/upload_<date>/` (git-ignored; archived), `wiki/log.md`

**Verification:** `staged_check.py` on the package; spot-check recorded in the log.

---

## TASK-1109: Close-out

**Status:** [ ] Not Started
**Feature:** zh-ja-content-seeding
**Type:** docs
**Complexity:** S (1-3h)
**Depends On:** TASK-1105, TASK-1106 (and TASK-1108's second wave if it runs)

**Description:** Final checks and wiki update after everything is applied.

**Acceptance Criteria:**
- [ ] `v_ladder_judge_reject_rates` reviewed for the new senses, per source
- [ ] Database and Storage sizes recorded
- [ ] `wiki/database/schema.tech.md` row counts, index, log and master list updated
- [ ] Superseded branches named for deletion (`claude/zh-word-assets-10k` once TASK-1099 is merged)

**Files to Create / Modify:** `wiki/log.md`, `wiki/index.md`, `wiki/tasklist/master.md`, this file

**Verification:** Log entry with final sizes and counts.
