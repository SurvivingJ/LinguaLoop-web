---
title: "ADR-054: Exam word lists are reference tables; v1 shows measured coverage buckets only"
status: proposed
date: 2026-11-17
---

# ADR-054: Exam word lists are reference tables; v1 shows measured coverage buckets only

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

## Decision
1. Two new tables: `dim_word_lists` (one row per list edition, with licence, attribution and an
   `allow_export` switch) and `dim_word_list_items` (one row per distinct headword at its lowest level,
   matched or not, with `vocab_id` and the match method). `level_tag` is not used.
2. Lists at launch: **HSK 3.0, 2025-11 CLEC syllabus** (levels 1–6 and 7–9; krmanik files, CC BY-SA
   4.0) and **JLPT N5–N1 community lists by Jonathan Waller** via jamsinclair (MIT + Waller CC BY),
   labelled unofficial. English: none.
3. Matching is offline in a re-runnable loader that emits an SQL package; Japanese matches record
   their method; reading-only homophones are not matched; a final 儿 may be stripped.
4. "Knowing a list word" = the lemma's **rank-1 meaning** is rated known after a direct check. v1 shows
   **measured buckets only** per level: rated known after a direct check / seen, not yet rated known /
   no evidence yet / not yet in LinguaDojo. Items without a lemma are their own bucket and never count
   as unknown. No estimated percentage (a corrected formula is fixed in the tech spec §2.8a, gated by
   TASK-1071).
5. The JLPT card states its not-in-LinguaDojo share first and offers the import action; JLPT coverage
   is **not used in Pro marketing**. Positioning: "At launch, exam coverage is strong for HSK 1–5 and
   partial for JLPT."
6. Data load waits for the size gate (DB ≤ 490,000,000 B or a confirmed 500 MiB cap) and licence
   sign-off. List-subset exports are allowed only where `allow_export` is true (JLPT yes, HSK after
   share-alike is accepted) and carry the attribution on every row.

## Consequences
- Easier: exam-level coverage and missing-word lists for zh and ja at ~2 MB; re-resolving fills
  matches as the dictionary grows.
- Harder: Japanese learners at every level see a large "not yet in LinguaDojo" bucket; seeding the
  ~722 missing N5–N4 lemmas (≈ 3.4 MB of senses) is a separate content decision (OQ31).
- Constrained: the CC BY-SA HSK file brings attribution and possibly share-alike duties; the UI always
  names the edition and marks community lists unofficial.

## Alternatives Considered
- **Reuse `level_tag`:** collides with the age-tier meaning used by exercise generation.
- **Reuse `user_word_watchlist`:** per-user, sense-level, no list entity, and creates senses.
- **HSK GF0025-2021:** the national standard, but not the syllabus of the exams sat from 2026.
- **Create the missing exam words:** 20–140 MB, impossible on the Free plan.
- **stephenmk JLPT files (CC BY-SA 4.0):** cleaner, but adds share-alike; used offline only.
- **Estimated coverage percentage in v1:** its error is dominated by an untestable exchangeability
  assumption, so it cannot honestly carry a 95% label.
- **Hide JLPT N2/N1 or all JLPT at launch:** hides an honest gap; the import action makes the gap
  actionable.
