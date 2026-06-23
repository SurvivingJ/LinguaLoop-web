---
title: Dual Translation
type: feature
status: planned
tech_page: ./dual-translation.tech.md
last_updated: 2026-06-22
open_questions:
  - "RESOLVED 2026-06-23: privacy — no special posture required; learner reproduction text is retained for analysis (an asset, not a risk)."
  - "RESOLVED 2026-06-23: embeddings not needed — cluster errors deterministically by taxonomy subtype; pgvector optional for later intra-subtype refinement."
---

# Dual Translation

## Purpose
A practice loop where the learner reproduces a target-language (L2) passage from its
native-language (L1) reference, then sees a precise, explained comparison against the
original. The point is not the score — it is the **noticing of the gap** between what the
learner produced and the gold L2, and the **explanation of why each difference is an error**.

## User Story
> "I am an English speaker learning Japanese. The app shows me an English reference of a
> short passage and asks me to write it in Japanese. When I submit, it shows my version next
> to the original Japanese, highlights exactly where I went wrong, tells me *why* (e.g. 'you
> used は where the original uses が because this clause introduces new information, not the
> topic'), and later drills the corrected form back to me until I stop making that mistake."

This serves learners who want to be **tested and scored on production**, not just shown
flashcards — the core LinguaDojo audience. It closes the loop from passive recognition
(comprehension tests, flashcards) to active, corrected production.

## How It Works
1. The learner is given an **L1 reference** of a short passage (2–4 sentences) — drawn from a test
   they have **already completed** (via reading, listening, or dictation) so the content is
   already at their level — and asked to translate it into the L2 ("the reproduction"). *(MVP is
   L1→L2 only — see [[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]].)*
2. On submit, the system compares the reproduction against the **original L2 passage** (the
   gold reference). A free deterministic pass aligns the two texts and finds the differences
   before any AI model is involved.
3. Differences that need judgement are graded on a small **analytic rubric** — Accuracy,
   Understandability, Fidelity/Register, Range, and a deliberately low-stakes Naturalness —
   each on a 4-band scale anchored to the learner's **age tier** ([[decisions/ADR-003-age-tiers]]),
   never CEFR.
4. The result screen makes the **diff the visual centrepiece** (the noticing surface), with a
   per-dimension band and, for every detected error, a plain-language **explanation of which
   rule was broken and why** — generated up-front, because explaining the error is the whole
   point ([[decisions/ADR-015-eager-error-explanations]]).
5. Errors are tagged, persisted and aggregated into a **per-learner error profile**. Only
   *systematic* errors (recurring, not one-off slips) are promoted into a spaced-repetition
   queue and remediated with cloze cards and "isolate-and-re-translate" drills — always
   toward the **corrected** form, never the learner's wrong form.

## Constraints & Edge Cases
- **Reference-based, not open-ended.** Because every reproduction is graded against an existing
  gold L2, a large share of grading is deterministic and free. The pipeline is designed
  diff-first ([[algorithms/translation-grading-cascade]]).
- **Understandability and Accuracy are weighted highest; Naturalness is lowest and overridable.**
  A heavily non-native but fully intelligible reproduction must not be over-penalised
  (Munro & Derwing). Pedagogy and cost align here — the fuzzy dimension is also the expensive
  one, so we under-invest in it deliberately.
- **Per-user L1.** Learners may have any of ZH/EN/JA as their L1, so a passage stores the L2
  gold once and an L1 reference *per supported L1*. Interlingual error rules are defined per
  **directed L1↔L2 pair** ([[decisions/ADR-016-per-pair-error-taxonomy]]).
- **Source from existing corpus — `tests.transcript` only.** Passages are drawn from existing L2
  test transcripts (not mystery scenes); the L1 reference(s) are generated and stored alongside.
  We never invent new L2 source content. Passages are served from tests the learner has **already
  completed** (reading/listening/dictation), so content is inherently at their level.
- **Grading is level-neutral; only naturalness is level-dependent.** Because difficulty is
  controlled at *selection* (at-level completed tests), the grade is measured against the gold
  reference at face value — an error is an error at any tier, and the explanation is never
  softened. The sole level-dependent dial is `naturalness`, which is de-emphasized and hidden at
  the lowest age tiers. See [[decisions/ADR-018-level-neutral-grading]].
- **Privacy:** no special posture required; learner reproduction text is retained for analysis.
- **Error vs mistake.** Self-corrected or one-off slips are logged but not drilled; only errors
  that recur ≥ N times (tunable) enter the SRS.

## Business Rules
See [[business-rules/translation-error-taxonomy]] for the full taxonomy, severity model,
error-vs-mistake gate, and promotion threshold.

## Open Questions
- ANSWERED: privacy → no special posture; retain learner text for analysis.
- ANSWERED: embeddings → not needed; cluster errors by taxonomy subtype (pgvector optional later).
- ANSWERED: grading is level-neutral; naturalness alone is level-dependent ([[decisions/ADR-018-level-neutral-grading]]).
- ANSWERED: source → `tests.transcript` only, from the learner's already-completed tests.
- ANSWERED: directionality → L1→L2 only for MVP.
- ANSWERED: difficulty banding → age tiers, not CEFR.
- ANSWERED: model access → flash-style, language-dependent OpenRouter slugs in `prompt_templates`
  (Gemini-flash for EN content, Qwen for ZH/JA); grading prompts are target-language-only and
  emit numerical indices (no English, no prose).

## Related Pages
- [[features/dual-translation.tech]] — architecture, data model, grading pipeline (Feature 1)
- [[features/dual-translation-remediation.tech]] — error synthesis + spaced remediation (Feature 2)
- [[algorithms/translation-grading-cascade]] — Tier 0 deterministic + OpenRouter cascade
- [[business-rules/translation-error-taxonomy]] — error taxonomy and promotion rules
- [[features/dictation]] — reuses the same Levenshtein diff grader for Tier 0
- [[features/flashcards]] — reuses FSRS-4 for remediation card scheduling
- [[decisions/ADR-014-reference-first-grading]], [[decisions/ADR-015-eager-error-explanations]], [[decisions/ADR-016-per-pair-error-taxonomy]], [[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]]
