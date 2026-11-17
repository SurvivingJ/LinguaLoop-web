---
title: "ADR-049: Two agreeing reviews override the tightness floor"
status: accepted
date: 2026-11-17
---

# ADR-049: Two agreeing reviews override the tightness floor

## Context

[[decisions/ADR-037-sentence-level-l1-references]] made tightness the quality gate for
sentence references: a reviewer back-translates the reference blind, and the similarity of that
back-translation to the original sentence (Tier 0, character-level for CJK, word-level for
English) must reach a floor (zh 0.70, en 0.60, ja 0.65, from
[[evaluations/sentence-refs-pilot-2026-10-30]]) as a window mean before the window is served.

The 2026-11-17 full run showed the score is noisy. Of 193 references below the floor, a second
reviewer (Opus, fresh context, blind back-translation first) judged 150 faithful as written, and
110 of those still scored below the floor on the second back-translation. The reviewers' reason
was consistent: literary or idiomatic golds (亦/也, 判若云泥, 倘若), synonyms (省水 / 节约用水),
subjects and tense the source leaves implicit, and very short sentences where one word changes
the ratio. In two cases the second blind back-translation matched the gold exactly while the
first had scored low. The second pass on the 2026-11-14 batch (89 references) gave the same
picture: 74 pass, 15 rewritten.

## Decision

Developer, 2026-11-17: "Blind reviewers agreement can override."

- `test_sentence_references.faithful_reviews` counts the independent reviews (distinct
  `run_id`) that gave this exact `l1_text` a `pass` or wrote it as their `rewritten` text, for
  the same (sentence, L1). The upload script sets it on every new row; the migration
  backfilled existing rows.
- A sentence with `faithful_reviews >= 2` (`sentence_refs.FLOOR_OVERRIDE_REVIEWS`) is left out of
  the window's mean tightness. A window made only of such sentences passes. Everything else is
  unchanged: unagreed sentences still have to carry the mean to the floor.
- The same gate (`passage_builder.window_meets_floor`, inside `select_window_for_primed`) serves
  both `/next` (`dt_next_inputs` returns the agreed indices as `ag`) and the prestudy Produce
  window; `build_daily_session` applies the same rule to its adjacent-pair availability count.
- A second review is always blind-first (`scripts/sentence_ref_recheck.py`), so any count of 2
  includes a blind judgement of this exact text. A reviewer's own rewrite counts once, for that
  reviewer; it needs another review to reach 2.

## Consequences

- Faithful references are no longer hidden by a noisy score. After the decision, 99.5% of
  Japanese and 99.2% of Chinese sentences pass the gate (96.6% / 95.9% by tightness alone); with fixed
  2–4 sentence packing, eligible windows went from 850 to 856 (zh) and 81 to 83 (ja), and the daily
  session's availability count for the test account from 266 to 267 (zh) and 69 to 71 (ja) tests.
- Tightness stays the honest measurement; nothing rewrites it.
- References rewritten by a second reviewer (35 + 15 on 2026-11-17) have one review of their
  new text; the low ones stay gated until a third review agrees.
- Identical text from two independent arms (the pilot's sentencewise and aligned runs) also
  counts as agreement. That is intended: two authors and two reviewers converged on it.
- Deploy order: the column exists (applied 2026-11-17) before the code that reads it.

## Alternatives Considered

- **Lower the floors.** Rejected: it admits loose references the reviewers would rewrite, and the
  noise is per sentence, not per language.
- **Store the higher of the two tightness scores.** Rejected: it turns a measurement into a
  judgement and hides that the score was low.
- **Skip the floor for any second-review `pass`, without a column.** Rejected: it needs run-id
  naming conventions at serve time and cannot tell a rewrite from a confirmation.
