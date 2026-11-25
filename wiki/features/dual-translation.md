---
title: Dual Translation
type: feature
status: in-progress
tech_page: ./dual-translation.tech.md
last_updated: 2026-11-23
open_questions:
  - "OPEN (owner, 2026-11-23): grading currently uses two free models that failed the gold-set check ([[evaluations/dt-free-grader-goldset-2026-11-23]]); revert to the validated pair? See [[decisions/ADR-044-dt-single-call-generative-grader]]."
  - "OPEN (owner, 2026-11-23): two proposals are not decided: [[decisions/ADR-061-one-transactional-write-per-dt-submission]] and [[decisions/ADR-062-retire-dt-card-and-select-next-window-in-sql]]."
  - "RESOLVED 2026-11-17 (TASK-989): 'all done' screen first, with an explicit 'Translate an earlier passage again' action that re-serves the least recently graded passage; a repeat is graded but kept out of the error profile."
  - "OPEN (2026-11-17): spoiler rule — should the first rated attempt of a test whose passage was translated beforehand count at half weight, as a prestudied attempt does? Needs a hook in routes/tests/submit.py (TASK-1001)."
  - "OPEN (2026-11-17): confirm what a repeat counts towards — today study minutes, the daily token budget and prestudy Produce bookkeeping, but not the error profile, trends, error cards, guided repair or word-knowledge evidence (TASK-1001)."
  - "OPEN (2026-11-17): skips — every fresh GET /next still creates a new empty submission; should /next resume the most recent never-started passage first? And should an old whole passage and the sentence windows of the same test count as repeats of each other? (TASK-991)"
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
   toward the **corrected** form, never the learner's wrong form. *(Since 2026-11-16 the result screen
   itself is the guided self-repair flow: the learner fixes their own flagged sentences before the correction is
   shown, see [[features/dt-guided-self-repair]]. The spaced card queue exists but is hardly used: 4 cards and no
   reviews on 2026-11-23.)*

### Which passage comes next (updated 2026-11-17)
- The passage is always in the language the learner is studying right now (the language picked
  in the app). Older app versions that do not say which language get the language of the
  learner's most recent test. A link opened for one test (from its preview page) uses that test's
  own language, whatever language is selected.
- Order: first the passage the learner was last shown and has neither translated nor skipped;
  then a new short passage (2–4 sentences, built from the reviewed sentence-by-sentence
  translations) from a test the learner has taken; then the same from tests they have **not taken
  yet**, nearest their level first; then a passage they skipped, oldest first. The older
  whole-passage pool is no longer served (retired and deleted 2026-11-17).
  Only existing reviewed translations are used — nothing is generated on the spot.
- A passage from a test the learner has not taken says so above the reference: "This passage is
  from a test you haven't taken yet, so you'll see part of that test's text."
- When everything has been graded, the learner sees an honest "all done" screen ("You've
  translated every passage…") with two actions in the pinned bar: **Translate an earlier passage
  again** (the passage graded longest ago) and **Browse tests**. A re-served passage says above the
  reference when it was translated and what band it got, and that this try does not count towards
  the error profile. The repeat is graded and shown as usual, but its errors do not feed the error
  profile, error cards, guided repair or word-knowledge evidence; it still counts as study time.
- Entry points: the Practice / Today "Quick access" chip, a "Dual Translation" row on the Me page,
  and on a test's preview page a "Translate a passage from this test" link, shown only when a
  passage for that test is ready.
- If the grading service refuses to grade (for example because the account's credit has run out),
  the learner sees "Grading is temporarily unavailable" and keeps what they wrote; nothing is
  saved, so they can try again later.
- What the learner writes is cleaned of invisible and control characters and limited to 2000
  characters; text the model writes back is shown as plain text only (no HTML or formatting).

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
  test transcripts (not mystery scenes); the L1 references are the reviewed sentence-by-sentence translations
  ([[features/test-sentence-references]]), not generated on the spot.
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
- ANSWERED 2026-11-17: "all done" first, then an explicit re-serve of the least recently graded passage (TASK-989).
- OPEN: spoiler rule for passages from untaken tests, and what a repeat counts towards (TASK-1001).
- OPEN: no new row on a skip; overlap of old whole passages and windows (TASK-991).
- ANSWERED: privacy → no special posture; retain learner text for analysis.
- ANSWERED: embeddings → not needed; cluster errors by taxonomy subtype (pgvector optional later).
- ANSWERED: grading is level-neutral; naturalness alone is level-dependent ([[decisions/ADR-018-level-neutral-grading]]).
- ANSWERED: source → `tests.transcript` only, from the learner's already-completed tests.
- ANSWERED: directionality → L1→L2 only for MVP.
- ANSWERED: difficulty banding → age tiers, not CEFR.
- ANSWERED (superseded for grading, 2026-11-23): model access was first planned as flash-style, language-dependent OpenRouter slugs in
  `prompt_templates` (Gemini-flash for EN content, Qwen for ZH/JA). Grading is now one structured call to a model named in `config.py`
  ([[decisions/ADR-044-dt-single-call-generative-grader]]); the validated model is `openai/gpt-6-luna`, but production currently runs two free models (see the open question above).

## Related Pages
- [[features/dual-translation.tech]] — architecture, data model, grading pipeline (Feature 1)
- [[features/test-sentence-references]] — where the passages and their native-language references come from
- [[features/dual-translation-remediation.tech]] — error synthesis + spaced remediation (Feature 2)
- [[algorithms/translation-grading-cascade]] — Tier 0 deterministic + OpenRouter cascade
- [[business-rules/translation-error-taxonomy]] — error taxonomy and promotion rules
- [[features/dictation]] — reuses the same Levenshtein diff grader for Tier 0
- [[tasklist/fixes-2026-11-16.tasks]] — open items from the 2026-11-16 fixes
- [[features/dt-guided-self-repair]] — the result screen is a guided self-repair flow (live since 2026-11-16)
- [[decisions/ADR-044-dt-single-call-generative-grader]], [[decisions/ADR-045-dt-guided-self-repair]]
- [[evaluations/dt-free-grader-goldset-2026-11-23]] — gold-set check of the free models in use
- [[decisions/ADR-061-one-transactional-write-per-dt-submission]] and [[decisions/ADR-062-retire-dt-card-and-select-next-window-in-sql]] — proposals
- [[features/flashcards]] — reuses FSRS-4 for remediation card scheduling
- [[decisions/ADR-014-reference-first-grading]], [[decisions/ADR-015-eager-error-explanations]], [[decisions/ADR-016-per-pair-error-taxonomy]], [[decisions/ADR-017-dual-translation-standalone-l1l2-mvp]]
