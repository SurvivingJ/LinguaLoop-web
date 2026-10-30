---
title: Test Sentence References
type: feature
status: planned
tech_page: ./test-sentence-references.tech.md
last_updated: 2026-10-30
open_questions:
  - "OPEN: tightness floor. Proposed 0.55 Tier 0 similarity on back-translation; set from the pilot's distribution, not guessed."
  - "OPEN: which second L1 for English tests — both zh and ja, or only the L1s of current learners (today: one learner, L1 en)? Proposed: generate en for ja/zh tests first (serves the live learner), then the CJK pairs in a second run."
  - "OPEN: whether a transcript edit should retire or merely flag its sentence references. Proposed: retire by hash mismatch and re-queue."
---

# Test Sentence References

## Purpose

Give every sentence of every active test a reviewed native-language translation, stored at the
sentence grain, so that any 2–4 sentence window can be served for dual translation in the
Study → Test → Produce workflow ([[features/test-prestudy]]) and so the preview can show, play
and cloze one sentence at a time.

## User Story

A learner finishes a prestudied Japanese test. The app picks the three sentences that carry
most of the words they just learned, shows the English for them, and asks for the Japanese
back. For that to happen the English has to exist already, be faithful enough that a good answer
lands close to the original, and have been checked by someone other than the model that wrote
it.

## How It Works

1. **Cleanup.** Transcripts that carry a generation preamble ("この文章は、T3レベル…---") are
   stripped and their token maps re-checked. Nothing downstream is built from a dirty transcript.
2. **Segmentation.** Each transcript is split into sentences with the segmenter dual translation
   already uses, and each sentence is stored with its character span and token-map span, so it
   lines up with the glosses, furigana and pinyin the preview uses.
3. **Authoring.** A worklist of tests is exported; Claude author agents, driven by a skill, write
   one document per test per native language: the sentences translated in order, with the whole
   passage as context so the sentences read naturally together but each stands alone.
4. **Checks.** Deterministic checks reject documents with the wrong sentence count, target-language
   script in a translation, missing numbers or names, or a leaked preamble.
5. **Review.** A different agent, in a fresh context, reads each document blind, judges meaning
   equivalence sentence by sentence, back-translates the reference without seeing the original,
   and records a verdict and a tightness score per sentence. Weak sentences are rewritten.
6. **Upload.** Reviewed references go through the repo's own upload script to the database, dry
   run first, with the author, prompt version and reviewer verdict stored beside each one.
7. **Serving.** When the Produce stage opens, the app assembles the chosen window from sentences,
   creates or reuses a dual-translation passage for that range, and shows only the native-language
   side. Grading runs the existing live cascade.

Bulk generation uses Claude agents and skills, like word assets. OpenRouter is used only for live
grading.

## Constraints & Edge Cases

- **Pilot before scale.** Two authoring approaches (sentence by sentence with context, and whole
  passage aligned) are compared on 30 tests per language, judged blind, before the full run.
- **A transcript edit invalidates its references.** Sentence rows carry a hash of the transcript;
  a mismatch retires the references and re-queues the test.
- **Short tests.** A transcript with fewer than two sentences gets references but no Produce
  window; the preview still uses the sentences.
- **Existing passages.** Current `dt_passage` rows keep working until their tests have reviewed
  sentence references, then are retired, so no learner sees an unreviewed reference.
- **Reviewer time, not money, is the cost.** About one author turn per test per language and one
  reviewer turn per six tests; no OpenRouter spend.

## Business Rules

- A reference is served only if its reviewer verdict is `pass` and it is active.
- Each sentence has at most one active reference per native language.
- References never contain the studied language's script, a preamble, or added content.
- The Produce window prefers sentences at or above the tightness floor and never spans a
  retired reference.

## Open Questions

See frontmatter.

## Related Pages

- [[features/test-sentence-references.tech]] — Technical specification
- [[decisions/ADR-037-sentence-level-l1-references]] — The decision and the alternatives
- [[features/test-prestudy]] — The workflow this serves
- [[features/dual-translation]] — Grading, rubric and remediation (unchanged)
- [[tasklist/test-sentence-references.tasks]] — Task breakdown
- [[features/csv-exercise-authoring]] — The staged authoring pattern this mirrors
