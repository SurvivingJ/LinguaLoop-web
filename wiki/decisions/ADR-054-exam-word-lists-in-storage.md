---
title: "ADR-054: Exam word lists are versioned reference files in Storage; v1 shows measured coverage buckets only"
status: proposed
date: 2026-11-17
---

# ADR-054: Exam word lists are versioned reference files in Storage; v1 shows measured coverage buckets only

> **Revision 2026-11-18.** The first version of this ADR (2026-11-17, file
> `ADR-054-exam-word-lists-as-reference-tables.md`) stored the lists in two new database tables,
> `dim_word_lists` and `dim_word_list_items` (~1.8–2.0 MB), and therefore made the list load — and
> with it the Pro launch gate TASK-1059 — wait for a database size gate (`pg_database_size` ≤
> 490,000,000 B or a confirmed 500 MiB cap, OQ13). On 2026-11-18 the owner asked for the lists
> to be kept as versioned JSON files in Supabase Storage instead, and this revision adopts that (the ADR
> stays proposed until the owner accepts it), following the ADR-049 precedent. Decisions 1,
> 3 and 6 below are new; decisions 2, 4 and 5 (which lists, what "knowing a list word" means, how
> JLPT is presented) are unchanged. The list load no longer depends on OQ13.

## Context
Coverage of an exam's word list, with the missing words, is what serious learners build for
themselves when a product lacks it. The database has no exam data: `dim_vocabulary.level_tag` is NULL
on all 20,613 rows and the exercise generator reads it as an age-tier code
(`services/vocabulary_ladder/asset_generators/prompt1_core.py:225`). "HSK 3.0" names two lists (the
2021 national standard and the November 2025 CLEC exam syllabus); 41.5% of the ~9,700 words they
share changed level. JLPT has published no official list since 2010.

Match rates against the dictionary (MEASURED, level-lists research §3): HSK 2025 L1–L5 87.6–92.1%,
L6 75.4%, L7-9 37.9%; Waller's JLPT lists N5 48.7%, N4 42.0%, N3 40.4%, N2 18.4%, N1 20.5% — **every
JLPT level is majority "not in LinguaDojo"**, and the ja dictionary is too small for overall JLPT
coverage to exceed ~43%. Creating the missing words would cost ~20 MB (senses) to ~140 MB (with ladder
content). The challenge stage also showed that an estimated coverage percentage double-counted
confirmed words, understated its variance and assumed list words behave like random words of the same
frequency (statistician review S8).

Storage facts behind the revision:
- The database was 513,526,931 B on 2026-11-17 (MEASURED) on the Supabase Free plan, whose 500 MB cap
  is either 500,000,000 B or 500 MiB (unverified, OQ13). Two list tables (~2 MB) would have had to wait
  for that question or for ADR-049's content drop.
- File bytes in Storage do not count toward the database cap (the Free plan has 1 GB of file storage).
  Each file costs one `storage.objects` metadata row, 595 B on average (MEASURED in ADR-049), so two
  list files cost ~1.2 KB of database.
- A Storage client already exists: `SupabaseStorageBackend(url, service_key, bucket=…, http_timeout_s=2.0)`
  (`services/exercise_content/backends.py:357`: `get`, a `put` that never overwrites (`AlreadyExists`),
  `delete`, and `list` paged by 1,000), with `InMemoryBackend` (`backends.py:100`) as its test fake.
  ADR-049 already stores immutable, versioned JSON in a private bucket.
- Size of one list file (ESTIMATE, compact JSON from the krmanik 2025 and jamsinclair source files with
  synthetic 5-digit `vocab_id`s at the measured match rates): HSK 2025 ~10.9k entries ≈ 0.29 MB raw
  (≈ 27 B per entry), ≈ 80 KB gzipped; JLPT ~8.0k entries ≈ 0.30 MB raw (≈ 37 B per entry), ≈ 82 KB
  gzipped. Details in [[features/knowledge-report.tech]] §5.2.

## Decision
1. **Versioned files in Storage, not tables.** A new private bucket `reference-data` (JSON only,
   5 MB per-file limit) is created by a small owner-applied migration (`INSERT INTO storage.buckets`,
   with a rollback). Each list is stored as `word-lists/<list_code>/v<N>.json`. Files are immutable
   (`put` never overwrites); a change is a new version. There is no mutable manifest: a reader lists
   `word-lists/<list_code>/` and uses the highest `N` (compared as a number). No list table is created;
   `level_tag` is not used.
2. Lists at launch: **HSK 3.0, 2025-11 CLEC syllabus** (levels 1–6 and 7–9; krmanik files, CC BY-SA
   4.0) and **JLPT N5–N1 community lists by Jonathan Waller** via jamsinclair (MIT + Waller CC BY),
   labelled unofficial. English: none.
3. **Lemmas are resolved at build time.** `scripts/build_word_lists.py` reads `dim_vocabulary`
   read-only, resolves each headword to a `vocab_id` with the matching rules already specified for the
   loader (Japanese matches record their method; reading-only homophones are not matched; a final 儿 may
   be stripped), validates the file and, with `--upload`, writes it as a new version with the service
   key (the default is a dry run that writes the file locally). `vocab_id = null` means "not yet in
   LinguaDojo". The file records `built_at` and the dictionary it was matched against; the list is
   rebuilt whenever the dictionary gains lemmas of its language, and the UI shows "List matched to the
   dictionary on {built_at}". Licence, attribution and the `allow_export` switch are file metadata.
   The app reads files through `WordListStore` (`services/vocabulary/word_lists.py`) with a per-process
   cache keyed by (list code, version) that re-checks for a newer version at most every 6 hours, and it
   fails soft: if Storage cannot be read, the list cards say "Word lists are unavailable right now" and
   the rest of the report works. SQL functions receive the list's `vocab_id`s as arrays from Python;
   no SQL joins a list table.
4. "Knowing a list word" = the lemma's **rank-1 meaning** is rated known after a direct check. v1 shows
   **measured buckets only** per level: rated known after a direct check / seen, not yet rated known /
   no evidence yet / not yet in LinguaDojo. Items without a lemma are their own bucket and never count
   as unknown. No estimated percentage (a corrected formula is fixed in the tech spec §2.8a, gated by
   TASK-1071).
5. The JLPT card states its not-in-LinguaDojo share first and offers the import action; JLPT coverage
   is **not used in Pro marketing**. Positioning: "At launch, exam coverage is strong for HSK 1–5 and
   partial for JLPT."
6. The upload waits only for the edition and licence answers (OQ2, OQ3), **not** for the database size
   question (OQ13). List-subset exports are allowed only where the file's `allow_export` is true (JLPT
   yes, HSK after share-alike is accepted) and carry the file's attribution on every row.

## Consequences
- Easier: exam-level coverage and missing-word lists for zh and ja at ~1.2 KB of database instead of
  ~2 MB; the Pro launch gate (TASK-1059) no longer waits for the database to shrink; a list update is a
  new file, not a migration or a deploy; old versions stay readable for audit.
- Harder: matches are a snapshot of the dictionary at `built_at` — a lemma added later counts as "not
  yet in LinguaDojo" until someone reruns the builder; the report depends on Storage being reachable
  (mitigated by the cache and the fail-soft card); each RPC call that needs list words carries up to
  ~11k ids (≈ 53 KB request body for today's HSK matches, ≤ ~90 KB if every entry matched — ESTIMATE).
- Harder (unchanged): Japanese learners at every level see a large "not yet in LinguaDojo" bucket;
  seeding the ~722 missing N5–N4 lemmas (≈ 3.4 MB of senses) is a separate content decision (OQ31) that
  still waits for the database size question (OQ13), and the lists must be rebuilt afterwards.
- Constrained: the CC BY-SA HSK file brings attribution and possibly share-alike duties; the UI always
  names the edition and marks community lists unofficial; list data is never committed to the app
  repository (sources are pinned by URL, commit and sha256 in the build script).

## Alternatives Considered
- **Two database tables (`dim_word_lists` + `dim_word_list_items`, the 2026-11-17 version of this
  ADR):** ~1.8–2.0 MB on a database that is at or over its Free cap (513.5 MB); the load, and with it
  the Pro launch gate, would wait for OQ13 or ADR-049's content drop. Rejected 2026-11-18.
- **A static JSON file shipped in the repository / app bundle:** no Storage dependency, but every list
  update (a rebuild after dictionary growth, a licence change) would need a deploy, and it puts CC BY-SA
  data in the app repository. Rejected; it is the **fallback if Storage proves unreliable** (the file
  format would stay the same).
- **Resolving lemmas to `vocab_id` at request time:** always current, but every summary and list page
  would look up ~11k headwords in `dim_vocabulary`. Rejected for per-request cost; build-time
  resolution plus a rebuild after dictionary growth gives the same answer.
- **Reuse `level_tag`:** collides with the age-tier meaning used by exercise generation.
- **Reuse `user_word_watchlist`:** per-user, sense-level, no list entity, and creates senses.
- **HSK GF0025-2021:** the national standard, but not the syllabus of the exams sat from 2026.
- **Create the missing exam words:** 20–140 MB, impossible on the Free plan.
- **stephenmk JLPT files (CC BY-SA 4.0):** cleaner, but adds share-alike; used offline only.
- **Estimated coverage percentage in v1:** its error is dominated by an untestable exchangeability
  assumption, so it cannot honestly carry a 95% label.
- **Hide JLPT N2/N1 or all JLPT at launch:** hides an honest gap; the import action makes the gap
  actionable.

## Related Pages
- [[features/knowledge-report.tech]] §2.8, §5.2, §6.1, §8 · [[features/knowledge-report]]
- [[decisions/ADR-049-exercise-content-in-storage]] — the Storage precedent
- [[decisions/ADR-055-knowledge-report-entitlement-seam-and-launch-gate]] — the Pro launch gate
- [[tasklist/knowledge-report.tasks]] — TASK-1034 (bucket), TASK-1049 (reader and RPCs), TASK-1052
  (builder), TASK-1053 (upload)
