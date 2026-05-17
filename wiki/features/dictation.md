---
title: Dictation
type: feature
status: complete
tech_page: ./dictation.tech.md
last_updated: 2026-05-17
open_questions: []
---

# Dictation

## Purpose

Dictation turns every listening test into a productive-recall exercise. The learner hears the audio, types the full transcript from memory, and gets per-word feedback that simultaneously updates their test ELO and their per-word vocabulary BKT. It is the highest-density vocabulary signal in the app: one dictation submission produces 50-100 BKT data points vs ~5 from a comprehension MCQ.

## User Story

A learner browsing tests sees the **Dictation** option on the preview page next to Listening and Reading. They click it, hear the audio play, type what they heard into a single textarea, and submit. The results screen shows an inline diff of the canonical transcript with their mistakes highlighted - wrong words struck through, missed words underlined, extra words greyed. Their ELO updates and any words they got wrong nudge those word senses down in their vocabulary knowledge.

## How It Works

1. From the test preview page, learner picks **Dictation** and clicks Start. The route navigates to `/test/<slug>/dictation`.
2. The page loads test metadata via `GET /api/tests/test/<slug>?mode=dictation` — server-side withholds the canonical transcript so the learner only sees an audio player.
3. Learner presses Play. Each press increments a replay counter shown in the UI. A speed toggle cycles between 1.0x / 0.75x / 0.5x using HTML5 `playbackRate` (zero TTS cost).
4. Learner types into the textarea and clicks Submit (or presses Cmd/Ctrl+Enter).
5. Server fetches the canonical transcript, runs `services/dictation/grader.grade_dictation()` to produce per-word correctness, then calls `process_dictation_submission` RPC which records the attempt, updates ELO, and persists the diff.
6. After the RPC succeeds, per-word BKT updates fire for every transcript word that maps to a `dim_word_senses` row.
7. The result screen renders the inline diff with color-coded spans for correct / wrong / missing / extra words plus stats (word accuracy, replay count, time, ELO change).

## Scoring

- **Normalization**: case-insensitive, punctuation-stripped, diacritic-stripped (`café` == `cafe`). Word-internal apostrophes and hyphens preserved.
- **Tokenization**: whitespace for most languages, `jieba` for Chinese, char-level fallback for Japanese.
- **Alignment**: `difflib.SequenceMatcher` opcode walk.
- **Fuzzy tolerance**: words of length ≥ 4 are accepted if Levenshtein distance ≤ 1 (`helo` ≈ `hello`). Shorter words require exact match (`cat` ≠ `bat`).
- **Extra user words** are recorded for the diff display but never inflate or deflate the score.
- **Missing words** count against the canonical denominator.

## Replay Penalty

Replays are unlimited but tracked. The ELO K-factor multiplier follows: `max(0.5, 1.0 - 0.10 * (replay_count - 1))`. One replay is free (no penalty); each additional play reduces K by 10% down to a 0.50 floor. The composed factor is persisted to `test_attempts.elo_reduction_factor` so the existing "Review · 0.45× ELO" badge renderer surfaces it automatically.

## Test Pool

All existing listening tests are dictation-eligible without any new content generation — the same `tests` row, the same R2 audio file, the same canonical transcript. The recommendation lane caps dictation candidates to transcripts ≤ 80 words (longer passages remain reachable via direct URL).

## Constraints & Edge Cases

- Dictation requires `tests.audio_url` and `tests.transcript`. Tests without audio cannot be served in dictation mode.
- The recommendation lane key was changed from `(user_id, test_id)` to `(user_id, test_id, test_type_id)` so a learner who already took the listening version of a test still sees it in the dictation lane.
- Idempotency: client generates a `crypto.randomUUID()` per attempt; the RPC returns cached results on duplicate keys.
- Server-side guard rejects submissions where `len(user_transcript) > 10 * len(canonical_transcript)`.
- Pathological dictation submissions (entirely empty after normalization) return an error rather than crashing the grader.

## Business Rules

- Dictation is free per the standard test token rules — `was_free_test=true` is the default.
- Per-word BKT updates fire even if the user got the word wrong (correctness becomes the BKT evidence).
- A retake of the same dictation test (not in the daily retry slot) yields zero ELO movement, same as comprehension.

## Related Pages

- [[features/dictation.tech]] — Technical specification
- [[features/comprehension-tests]] — Sibling MC-based test modes
- [[features/vocabulary-knowledge]] — BKT word-test updates fed by dictation
- [[algorithms/elo-ranking]] — ELO with replay K-multiplier
- [[features/pinyin-trainer]] — Other free-form-input test mode (closest precedent)
- [[database/schema.tech]] — `test_attempts` columns: `replay_count`, `dictation_word_correct`, `dictation_word_total`, `dictation_diff`
