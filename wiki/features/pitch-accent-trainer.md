---
title: Pitch Accent Trainer
type: feature
status: complete
tech_page: ./pitch-accent-trainer.tech.md
last_updated: 2026-05-17
open_questions: []
---

# Pitch Accent Trainer

## Purpose

The Pitch Accent Trainer is a Japanese-only interactive game mode that drills the four classical accent classes — heiban (平板), atamadaka (頭高), nakadaka (中高), and odaka (尾高) — against authentic comprehension-test passages. It is the Japanese counterpart to the Chinese [[features/pinyin-trainer]], sharing the same architectural pattern: a deterministic linguistic preprocessor produces a JSON payload at test save time, and the trainer replays it as a per-word guessing game with ELO updates on first attempt.

## User Story

A learner studying Japanese opens a Japanese test's preview page and sees a "Pitch Accent" option alongside the standard reading/listening modes. They click it and enter a game where each content word in the passage is highlighted one at a time. They can play in **Quick mode** — pressing one of four arrow keys to identify the pattern class — or toggle to **Contour mode** to draw the full HIGH/LOW shape mora by mora. Correct answers reveal the canonical contour and colour the word by class; mistakes pop up a modal showing the correct contour (including any trailing particle), a one-line explanation of the rule, and the class name. After all words are guessed, a results screen shows accuracy, time, mistakes, and ELO change.

## How It Works

1. User navigates to a Japanese test's preview page (`/test/{slug}/preview`).
2. A "Pitch Accent" button appears (Japanese tests only).
3. User clicks it and is taken to `/test/{slug}/pitch-accent`.
4. The page loads the test's pre-computed `pitch_payload` — a tokenised breakdown of every content word with its kana pronunciation, mora segmentation, accent nucleus, pattern class, and HL contour. The next particle's pitch (if any) is also captured.
5. All content-word tokens become playable; punctuation and unknown-class tokens are rendered for layout but skipped.
6. The current word is highlighted, scaled, and underlined.
7. The learner toggles between two renderers (mode preference is persisted in `localStorage` as `pa_mode`):
   - **Quick mode** — 4 arrow keys map to the 4 pattern classes: ← Heiban, ↑ Atamadaka, → Nakadaka, ↓ Odaka. Class match = correct.
   - **Contour mode** — a two-track scratchpad shows HIGH and LOW dots above each mora. The learner clicks or uses `1`/`2` (or `L`/`H`) per mora, then presses Enter. The submission is validated against the two universal rules (mora 1 ≠ mora 2; at most one H→L drop) and then matched against the dictionary accent nucleus.
8. On **correct**: the word is coloured by class, the kana appears below it, a mini HL-contour SVG appears, and the game advances.
9. On **incorrect**: the word shakes, an error modal opens showing the canonical contour (with any trailing particle), the correct class name, and either the rule that was violated (contour mode) or the class mismatch (quick mode). Dismissing returns to the same word.
10. After all words are guessed, a results screen shows accuracy with a grade (Excellent ≥ 95%, Good ≥ 80%, Fair ≥ 60%, Poor < 60%), stats (words correct/total, time MM:SS, mistakes, ELO change), and retry/exit buttons.
11. Results are submitted to the backend, which records the attempt and updates ELO via the dedicated `process_pitch_accent_submission` RPC — identical to the pinyin RPC's K=32 first-attempt-only formula.

## Pattern Class Rules (briefly)

Japanese prosody operates on mora (拍), not syllables. Each mora is either High or Low, with the contour fully determined by a single integer A ∈ [0, N] for an N-mora word — the **accent nucleus**, naming the mora *after which* pitch drops:

- **Heiban (A = 0)** — no drop. L-H-H-H... including any following particle.
- **Atamadaka (A = 1)** — drop after mora 1. H-L-L-L...
- **Nakadaka (A in 2..N−1)** — drop in the middle. L-H-...-H-L-L...
- **Odaka (A = N)** — drop on the word boundary. L-H-H-...-H inside the word, but a following particle drops to L. Without a particle, indistinguishable from heiban.

Two universal rules hold for any pattern: mora 1 and mora 2 always differ in pitch, and pitch can drop at most once per accent phrase.

## Constraints & Edge Cases

- **Japanese only** — the pitch-accent button only appears for tests with `language_id = 3`.
- **Requires pre-computed payload** — if `pitch_payload` is null (generation failed or not yet run), the mode is unavailable.
- **No audio in v1** — this is a visual recall drill, like the pinyin trainer. Audio (per-word TTS with は/が appended for odaka/heiban disambiguation) is documented as Phase 2.
- **Unknown-class tokens skipped** — pyopenjtalk occasionally fails to assign an accent to rare loanwords or proper nouns; those tokens are rendered greyed-out and excluded from scoring.
- **Particles are not their own tokens** — they're attached to the previous content word as `trailing_particle` so the contour visualization can extend through the H/L drop on the particle (essential for showing odaka).
- **Error-penalised accuracy** — accuracy = `(total_words − error_count) / total_words`. Wrong answers retry in place; the score is the count of unforced first-try misses.
- **ELO** — separate `pitch_accent` skill rating per test, K=32 first-attempt-only, same bounds (400–3000) as all other test types.

## Business Rules

- Pitch accent test type has its own ELO track (`dim_test_types.type_code = 'pitch_accent'`).
- Initial pitch_accent ELO for all Japanese tests is 1400 (default).
- Pitch accent mode does not require audio (`requires_audio = false`).
- Pitch payload is generated automatically when a Japanese test is created, and can be backfilled via [scripts/batch_generate_pitch_accent.py](../../scripts/batch_generate_pitch_accent.py).
- The learner must get every word correct for the game to end (wrong answers retry in place).
- Tests with all-unknown payloads fall back to an error-state message and cannot be played.

## Related Pages

- [[features/pitch-accent-trainer.tech]] — Technical specification
- [[features/pinyin-trainer]] — Chinese counterpart (same architectural pattern)
- [[features/comprehension-tests]] — Parent feature (pitch accent is a test mode)
- [[algorithms/elo-ranking]] — ELO calculation shared with all test types
- [[database/schema.tech]] — `tests.pitch_payload`, `dim_test_types`, `test_skill_ratings`
