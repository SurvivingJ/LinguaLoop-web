---
title: Pinyin Tone Trainer
type: feature
status: complete
tech_page: ./pinyin-trainer.tech.md
last_updated: 2026-04-21
open_questions: []
---

# Pinyin Tone Trainer

## Purpose

The Pinyin Tone Trainer is a Chinese-only interactive game mode that tests a learner's knowledge of Mandarin tones. It reuses existing comprehension test passages as source material, turning each character into a tone-guessing challenge. It sits alongside reading, listening, and dictation as a fourth test type.

## User Story

A learner studying Chinese opens a test preview page and sees a "Pinyin Tones" option alongside the standard reading/listening modes. They select it and enter an interactive game where each Chinese character in the passage is highlighted one at a time. Using keyboard arrows or touch swipes, the learner guesses the correct tone (1-4 or neutral). Correct guesses colour the character and reveal its pinyin; wrong guesses trigger an error modal explaining the correct tone and any sandhi rules that apply. After completing all characters, the learner sees their accuracy, time, mistakes, and ELO change.

## How It Works

1. User navigates to a Chinese test's preview page (`/test/{slug}/preview`).
2. A "Pinyin Tones" button appears (Chinese tests only).
3. User clicks it and is taken to `/test/{slug}/pinyin`.
4. The page loads the test's pre-computed `pinyin_payload` — a tokenised breakdown of every character with its base tone, context tone (after sandhi), pinyin romanisation, and word context.
5. All non-punctuation characters become playable tokens displayed in a grid.
6. The current character is highlighted and scaled up.
7. The learner inputs a tone guess:
   - **Keyboard:** Right = Tone 1, Up = Tone 2, Left = Tone 3, Down = Tone 4, Space = Neutral
   - **Touch:** Swipe right = T1, swipe up = T2, swipe left = T3, swipe down = T4, tap = Neutral
8. If **correct**: the character is coloured by its tone, pinyin appears below it, and the game advances to the next character.
9. If **incorrect**: the character shakes, and an error modal appears showing:
   - The character and its word context
   - The guessed tone vs. the correct tone
   - A sandhi rule explanation if the tone changed from its dictionary form
   - The learner must acknowledge (click or Enter) before retrying the same character.
10. After all characters are completed, a results screen shows:
    - Accuracy percentage with a grade (Excellent >= 95%, Good >= 80%, Fair >= 60%, Poor < 60%)
    - Stats: characters correct/total, time (MM:SS), mistakes, ELO change
11. Results are submitted to the backend, which records the attempt and updates ELO ratings via the standard `process_test_submission` RPC.

## Tone Sandhi Rules

The trainer tests **context tones**, not just dictionary tones. Three deterministic sandhi rule sets are applied:

1. **Third Tone Sandhi** — When two consecutive 3rd tones appear, the first becomes a 2nd tone. (Exception: characters yi and bu have their own rules.)
2. **Yi (one) Sandhi** — Between repeated verbs (A-yi-A) becomes neutral; before 4th tone becomes 2nd; before 1st/2nd/3rd becomes 4th; at end of phrase stays 1st.
3. **Bu (not) Sandhi** — In A-bu-A pattern becomes neutral; before 4th tone becomes 2nd.

When a sandhi rule changes a character's tone, the error modal explains which rule applied and why.

## Polyphone Handling

Some Chinese characters have multiple valid pronunciations depending on context (e.g., hai/huan, xing/hang). The system handles these through:

1. **Jieba word segmentation** — provides word-level context that helps pypinyin select the correct reading.
2. **Static polyphone watchlist** — 45+ high-risk characters are flagged for review.
3. **Optional LLM resolution** — a batch process can send flagged polyphones to DeepSeek for context-aware disambiguation.

## Constraints & Edge Cases

- **Chinese only** — the pinyin mode button only appears for tests with `language_id = 1`.
- **Requires pre-computed payload** — if `pinyin_payload` is null (generation failed or not yet run), the mode is unavailable.
- **No audio input** — this is a visual/input game, not speech recognition.
- **Punctuation excluded** — punctuation characters are rendered but not interactive.
- **ELO integration** — uses the same dual-ELO system as other test types, with a separate pinyin skill rating per test.
- **Accuracy-based scoring** — the accuracy percentage drives ELO calculation (not per-question correctness).
- **Sandhi coverage** — only the three most common rule sets are implemented; rarer sandhi patterns are not covered.

## Business Rules

- Pinyin test type has its own ELO track (`dim_test_types.type_code = 'pinyin'`).
- Initial pinyin ELO for all Chinese tests is 1400 (same default as other types).
- Pinyin mode does not require audio (`requires_audio = false`).
- Pinyin payload is generated automatically when a Chinese test is created, and can be backfilled via batch script.
- The learner must answer every character correctly before the game ends (wrong answers retry in place).

## Related Pages

- [[features/pinyin-trainer.tech]] — Technical specification
- [[features/comprehension-tests]] — Parent feature (pinyin is a test mode)
- [[algorithms/elo-ranking]] — ELO calculation shared with all test types
- [[database/schema.tech]] — `tests.pinyin_payload`, `dim_test_types`, `test_skill_ratings`
