---
title: Furigana Overlay
type: feature
status: in-progress
tech_page: furigana-overlay.tech.md
last_updated: 2026-05-20
open_questions:
  - "Should the dampener factor (currently 0.5) scale with kanji density of the passage?"
  - "Backfill strategy: lazy on next edit, or a one-off script pass over existing JP tests?"
---

# Furigana Overlay

## Purpose
Lower-ability Japanese learners often stall on kanji they cannot yet read,
which makes otherwise-appropriate passages unreadable. The furigana overlay
gives learners an opt-in hiragana reading above each kanji so they can engage
with content at the level their vocabulary and grammar already support.

Because reading with furigana is materially easier than reading bare, leaving
the toggle freely on would inflate ratings. So toggling it on dampens the ELO
change for that attempt — the learner still progresses, but at a discounted
rate that reflects the assistance they received.

## User Story
A learner with ~600 known Japanese words wants to take a comprehension test at
their actual difficulty level, but the passage uses kanji they recognize as
words they *know in speech* without recognizing the written form. They flip
the ふりがな toggle on, the kanji sprout small hiragana above them, and they
can take the test. Their score still counts; the ELO gain/loss is halved.

## How It Works
1. Every Japanese test stores a pre-computed furigana payload (generated at
   creation time using a deterministic morphological analyzer — no LLM call).
2. On the test page, a small "ふりがな" toggle appears in the header. Default
   state comes from the learner's preference (off by default).
3. Flipping the toggle on rewrites the passage, question text, and MCQ choices
   so each kanji-run is wrapped in HTML `<ruby>` with its hiragana reading.
4. The toggle state for the attempt is sticky: if it was ever on during the
   attempt, the submission carries `furigana_used: true` and the ELO RPC halves
   the user-side K-factor. The test's intrinsic rating is unaffected.
5. The same overlay also applies to the Pitch Accent trainer, where kanji
   surfaces above the existing mora/contour widgets get ruby tags.

## Constraints & Edge Cases
- Tokens with no kanji render verbatim — the toggle has no effect on them.
- For jukujikun like 今日→きょう we use *group ruby* (the whole compound gets
  one reading) rather than per-character alignment, which would be wrong.
- If the tokenizer returns no reading for a token (rare; usually unknown proper
  nouns), the surface renders plain.
- Mid-attempt toggles still count as "used" for ELO; we don't allow learners
  to peek-then-hide to avoid the dampener.
- Tests created before this feature have `NULL` furigana_payload; the toggle
  is hidden for those (backfill is a separate task).

## Business Rules
- Furigana dampener factor is `0.5` on user K only; test K is unchanged so
  one learner's display preference cannot move the test's published rating.
- The dampener only applies on first attempts (consistent with existing
  first-attempt-only ELO rule).
- The preference is stored in `users.exercise_preferences.furigana_enabled`.

## Open Questions
- OPEN: Should the dampener scale with kanji density (e.g. 0.3 for kanji-heavy
  newspaper-style passages, 0.7 for mostly-kana children's stories)?
- OPEN: Backfill — eagerly compute payloads for existing JP tests via a
  one-off script, or lazily on next edit?

## Related Pages
- [[furigana-overlay.tech]]
- [[comprehension-tests]]
- [[pitch-accent-trainer]]
- [[../algorithms/elo-ranking]]
