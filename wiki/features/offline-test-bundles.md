---
title: Offline test bundles
type: feature
status: complete
tech_page: offline-test-bundles.tech.md
last_updated: 2026-11-27
open_questions:
  - "When to upload the 2026-11-27 bundles (ja 506 + 503 + N2–N1 251, zh 500 + HSK 7–9 250 + 250, it 250 = 2,510 tests; the whole set ~113 MB with vocabulary linking at ~45 KB a test): the database was 451 MB of the 500 MB Free cap after the build (llm_calls had been pruned to today's rows outside this session); each uploaded test costs roughly 45 KB with its vocabulary linking, so the whole bundle ~23 MB (OPEN)"
  - "Whether to keep Claude's uncalibrated tier ratings or re-tier the bundle with jev before upload (OPEN)"
  - "Adding Italian to the app (dim_languages, prompt templates seeded from data/offline_tests/it-2026-11-28/prompts, language maps, vocabulary processor, UI) before its bundle can be uploaded (OPEN)"
---

# Offline test bundles

## Purpose
Generate comprehension tests now, store them in the repository as one compressed file,
and load them into the live database later. This lets a large batch be written while the
database is close to its size cap, or before the content should go live.

## User Story
As the owner, I want a few hundred new tests written and checked now, so that adding them
later is one command and nothing they need has to be generated again.

## How It Works
1. A runner splits the work into "slots". Each slot is one topic at one target level
   (tier 1–4), plus a writing angle such as "a short news-style report" or "advice for a
   beginner". The angle makes passages on the same topic differ, because headless Claude
   writes the same passage for the same prompt every time.
2. Several runner processes (shards) work through the slots in parallel. Each one runs the
   normal test-writing steps: translate the topic, write the passage, rate its tier, write a
   title, write the questions and have the judges check them, and build the furigana and
   pitch-accent data. With the settings used for this bundle, every one of these calls is
   served by headless Claude. Nothing goes to OpenRouter or the Anthropic API.
3. Instead of saving to the database, each finished test is appended to its shard's file.
   A shard that stops can be restarted and skips the slots it already finished.
4. An "assemble" step merges the shard files, removes repeated passages, and writes the
   bundle: `tests.jsonl.xz` (one test per line, xz-compressed) and `manifest.json` (counts,
   levels, checksum).
5. Later, an upload script reads the bundle and saves each test through the same code a
   live run uses. That includes the audio, which is made at upload time, and the links from
   the transcript's words to the dictionary. By default it only reports what it would do;
   it writes only with `--apply`.

## Constraints & Edge Cases
- **Audio is not in the bundle.** One listening test's MP3 is about 0.5 MB, so 500 would add
  ~300 MB to git. Audio is synthesised at upload.
- **Vocabulary linking is not in the bundle.** It creates dictionary rows, and the dictionary
  will have changed by upload time.
- **No passage embeddings.** There was no OpenAI key at build time, so the near-duplicate check
  was skipped. The upload script embeds and checks each passage if a key is available then.
- **Tiers are Claude's ratings, not jev's.** They are not fitted to a gold set. They are marked
  `claude-uncalibrated` and lean high (a tier-3 target was once rated T5), so the seeded ELOs
  are a starting point that real attempts correct.
- **A bundle can be for a language the app does not have yet.** The Italian bundle was written with
  Italian prompt files and English's judges and topics. It cannot be uploaded until Italian is added to
  the app (language row, prompts, vocabulary support); the upload refuses it until then.
- **Duplicates at upload.** The upload skips any test whose id is already in the database, whose
  topic was deleted, or whose passage text matches a live test on the same topic.

## Business Rules
- A bundle record is never edited by hand. To change a test, regenerate its slot.
- The upload writes only with `--apply`, in line with the scripts convention (TASK-1218).
- Database headroom is checked before any upload (see open questions).

## Open Questions
- OPEN: when to upload, given the database size (see frontmatter).
- OPEN: keep Claude tiers or re-tier with jev before upload.

## Related Pages
- [[features/offline-test-bundles.tech]]
- [[decisions/ADR-069-claude-only-offline-test-generation]]
- [[features/comprehension-tests]]
- [[features/test-tier-assignment]]
- [[database/schema.tech]]
