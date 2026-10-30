---
title: "ADR-037: Sentence-level L1 references for test transcripts, authored by Claude agents"
status: accepted
date: 2026-10-30
updated: 2026-10-30 (pilot result)
---

# ADR-037: Sentence-level L1 references for test transcripts, authored by Claude agents

## Context

The Study → Test → Produce workflow ([[features/test-prestudy]]) ends with a dual-translation
stage on a 2–4 sentence window of the test the learner just took, chosen per learner for the
most primed words. Dual translation today stores references at the **window** grain:
`dt_passage` holds fixed, non-overlapping windows packed by `passage_builder.window_sentences`,
and `dt_passage_reference` holds one L1 text per window per L1 (live: 67 windows over 13 tests,
references from `qwen/qwen3.6-flash` for ja/zh and `google/gemini-2.5-flash-lite` for en,
generated lazily after a test is attempted).

Three facts make that grain wrong for the workflow:

1. The window is no longer fixed. It depends on which words a learner was primed on, so any
   sentence range of a transcript must be servable, with its reference, at the moment the
   attempt is submitted.
2. The reference must exist **before** the session, not after the attempt, or the Produce stage
   has nothing to show.
3. The live references were produced through OpenRouter without a judge, and the sample read
   during this decision shows a generation preamble ("この文章は、T3レベル（B1-B2）の学習者向けに…---")
   leaked from `tests.transcript` into a passage and its references. There is no quality gate.

Separately, the developer has decided (2026-10-30) that content generation for this feature
follows the word-asset pattern — Claude subagents driven by skills, with a fresh-context
reviewer, pushed through the repo's own upload path — and that OpenRouter is used only for live
grading. The OpenRouter account is also the one shared by every production judge and has hit its
credit limit once this month; keeping bulk content work off it is a resilience gain as well as a
cost one.

## Decision

1. **Grain: the sentence.** A new table `test_sentences` stores the canonical segmentation of
   every active transcript (character span and token-map span per sentence), produced by the
   existing CJK-aware `segment_sentences`. A new table `test_sentence_references` stores one L1
   text per sentence per supported L1, with provenance (author model, prompt version, reviewer
   verdict, tightness score) and an active flag. Any sentence range can be assembled into a
   passage by concatenation on both sides.
2. **`dt_passage` stays the grading anchor.** The Produce stage creates (or reuses) a
   `dt_passage` row for the chosen range, with new nullable `sentence_start` / `sentence_end`
   columns, and its reference is the concatenation of the active sentence references. The
   submission, grade and error tables are unchanged, so live grading through the OpenRouter
   cascade (`dual_translation_tier1..3`) is untouched.
3. **Generation by Claude agents through skills, not OpenRouter.** Two skills,
   `sentence-reference-authoring` and `sentence-reference-review`, plus a runner
   (`scripts/sentence_ref_runner.py`) mirroring `fat_seed_runner.py`: export worklist → briefs →
   author subagents write one aligned JSON document per test per L1 → deterministic checks →
   review pack → fresh-context reviewer → assemble → `upload_sentence_references.py` through the
   service-role write path, dry run first. No step calls a hosted model API.
4. **Quality gate before scale.** A two-arm pilot (30 tests per language) compares
   sentence-wise translation with passage context against whole-passage aligned translation,
   judged blind, on three measures: mutual entailment per sentence, **tightness** (Tier 0
   character similarity between a blind back-translation of the reference and the gold), and
   leakage (no L2 script, no preamble, counts and numbers preserved). The winning arm runs the
   full catalogue. Every reference carries its tightness score; the Produce window selector
   prefers sentences above the tightness floor.
5. **Transcript cleanup first.** The preamble artefact is audited and stripped from
   `tests.transcript` (and the derived token map re-checked) before segmentation, because every
   downstream asset inherits it.
6. **Model choice inside the skills.** Authors run on Sonnet (CJK quality at a fraction of Opus
   cost); the reviewer runs on Opus for a stratified 15% sample plus every item the
   deterministic checks flag, and on Sonnet for the rest; Haiku is not used for authoring or
   review because the deterministic checks already cover what it would be good at.

## Pilot result (2026-10-30, [[evaluations/sentence-refs-pilot-2026-10-30]])

The two arms are indistinguishable on tightness and entailment (median tightness within 0.015 in
every language, entailment pass 99.8–100%). `sentencewise` is adopted for all languages: it wins
ja and zh and halves the Japanese rewrite rate (3.4% vs 6.7%). Tightness floors from the pilot's
p10: ja 0.65, zh 0.70, en 0.60, applied as a preference in the window selector, never a block.
The review pack is now split into a blind file and a gold file after 5 of 30 reviewers read past
the single-file marker; those tests were excluded from the tightness statistics.

## Consequences

- **Easier:** any window is servable instantly; references exist the night before a session;
  the preview's per-sentence playback and the passage cloze get a canonical sentence table;
  provenance and a quality score sit on every reference; bulk generation spends no OpenRouter
  credit and cannot be blocked by its limit.
- **Harder:** two new tables and a backfill; the DT passage builder gains a second selector;
  references must be regenerated when a transcript is edited (the sentence hash guards this);
  the review step costs agent time per test (about one reviewer turn per 6 tests).
- **Constrained:** sentence references must be translatable in isolation yet read as a passage,
  which is exactly what the pilot measures; existing `dt_passage` rows keep working but will be
  retired once their tests have sentence references, so no learner sees a reference without a
  reviewer verdict.
- **Not changed:** live grading models, the DT rubric and taxonomy, the 0.5× ELO policy.

## Alternatives Considered

1. **Keep window references, pre-build every 2–4 window.** Rejected: 3 window sizes × every
   start index is roughly 3× the sentence count in rows, each needing its own reference and
   review, and the references still would not align at sentence level for the per-word
   production rows.
2. **Generate the reference on demand with OpenRouter at session time.** Rejected: latency
   inside the daily session, no reviewer in the loop, and dependence on the shared credit
   account that has already run dry once this month.
3. **Reuse the existing `tl_nl_translation` exercise content as references.** Rejected: those
   sentences are mined or generated per sense with distractor variants, not the transcript's own
   sentences in order, and cover under 7% of test senses.
4. **Two competing agents on this schema.** Rejected: the design space is two options (above)
   and is constrained by the existing `dt_*` tables; parallel design agents would reproduce this
   page. Parallel agents are used where they pay: the two generation arms of the pilot.
