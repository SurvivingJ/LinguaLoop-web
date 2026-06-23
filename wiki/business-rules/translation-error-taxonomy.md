---
title: Translation Error Taxonomy
type: business-rule
status: planned
last_updated: 2026-06-23
open_questions:
  - "OPEN: value of N (recurrence threshold) and window W for promotion to SRS — tunable config, default proposed below."
---

# Translation Error Taxonomy

Versioned, language-scoped reference data (stored in `dt_taxonomy_version`, never hardcoded in
application code). A shared cross-linguistic schema plus per-directed-pair subtype tables.

## Shared cross-linguistic schema (every error is tagged on four axes)
1. **category** — `grammatical` | `lexical` | `pragmatic_expressional`
2. **source** — `interlingual` (L1 transfer) | `intralingual` (within-L2 overgeneralisation).
   Interlingual classification depends on the learner's **L1**, so it is defined per directed
   pair — see [[decisions/ADR-016-per-pair-error-taxonomy]].
3. **severity** — `global` (impairs comprehension) | `local` (noticeable but meaning survives).
   Global errors rank first in the profile.
4. **error vs mistake** — only **systematic errors** are remediated. A `mistake` is a
   self-corrected or one-off slip; it is logged but never drilled (Corder).

## Explaining the error is mandatory
Every error carries an `explanation`: *which rule was broken and why*, written in the learner's
L1. This is a first-class output, not optional polish — see
[[decisions/ADR-015-eager-error-explanations]].

**Explanations are template-rendered, not model prose.** The grader emits a **numerical subtype
index** (L2-only prompt, no English); the explanation is then rendered from a **versioned
per-subtype × per-L1 template table** (part of `dt_taxonomy_version`), with `corrected_form` and
`learner_form` slotted in. Each `(subtype, L1)` pair has one template, e.g. for subtype
`particle` shown to an English-L1 learner:

> "You wrote 〈learner_form〉 but the original uses 〈corrected_form〉. は marks the known *topic*;
> が marks a *newly introduced* subject — here the subject is new information, so が is required."

This keeps "why each error is an error" eager and precise across all L1↔L2 pairs at ~zero marginal
model cost, and honours the target-language-only / numerical-output rule. A `(subtype, L1)` with no
template yet falls back to a generic "corrected: 〈corrected_form〉" string and is flagged for
authoring — never blank.

**Distinct from the above: per-subtype × per-L2 "glosses" (TASK-606).** The explanation template is
keyed by the learner's **L1** and rendered *after* grading, for the learner to read — the grading
model never sees it. But the grading prompt itself must also describe each subtype to the model, in
the **L2 being graded** (the prompt is L2-only), without leaking a bare English identifier slug like
`particle` or `keigo_register` into an otherwise-Chinese or Japanese prompt. That's a second,
separate table — `dt_taxonomy_version.taxonomy.subtype_glosses[subtype][l2_code]` — a short L2
phrase describing the subtype for the model's benefit. Missing for a given (subtype, L2) it falls
back to the bare English slug (logged for authoring) rather than crashing, same non-blocking pattern
as the explanation-template fallback. See
[[algorithms/translation-grading-cascade.tech]] "Implementation contracts" for the exact JSON shape.

## Per-language subtype tables (ship shared schema first, then localise)

### English (L2) — analytic, SVO, article-heavy
`article_omission/misuse`, `preposition`, `phrasal_verb`, `tense_aspect`,
`subject_verb_agreement`. Article + preposition errors dominate and are ideal cloze targets.

### Japanese (L2) — SOV, agglutinative, 3 scripts, honorifics
`particle` (は/が, を, に/で — empirically the largest category), `keigo_register`
(teineigo/sonkeigo/kenjougo), `counter_classifier` (助数詞), `script_choice` (kana/kanji),
`topic_comment`. **Weight overrides:** raise `fidelity` and `particle`; `keigo_register` is a
first-class **fidelity** failure (a grammatically correct reproduction at the wrong politeness
level is a real error), not optional polish.

### Chinese / Mandarin (L2) — SVO + topic-prominent, isolating, no inflection
`classifier` (over-use of 个; classifier–noun agreement), `aspect_marker` (了/过/着, not tense),
`topic_comment` over-transfer, `ba_construction`, `resultative_complement`. **Weight overrides:**
raise `classifier` and `aspect_marker`.

### Out of scope (text modality)
Tones (Chinese) and pitch accent (Japanese) are **pronunciation-only** — excluded from text
translation grading; gated behind a future `modality='speech'` flag. (LinguaDojo already has
dedicated [[features/pinyin-trainer]] and [[features/pitch-accent-trainer]] surfaces for these.)

## Promotion rule (error → remediation queue)
An error subtype is promoted into the SRS only when **either**:
- it **recurs ≥ N times** within window **W** (proposed default: N=3, W=last 30 days / 20 submissions); **or**
- it is **wrong under production load but correct when attention is drawn** (a proceduralization
  gap, not a knowledge gap).

`N` and `W` are tunable config, not constants. Self-corrected slips never promote.

## Anti-gamification rule
Surface the **shrinking error profile** as the motivator ("article errors down 40% this month"),
**not** the score. Do not gamify the grade (Black & Wiliam — reward-chasing undermines the
self-regulation goal).

## Related Pages
- [[features/dual-translation]] — feature using this taxonomy
- [[features/dual-translation.tech]] — `dt_error_instance` schema
- [[features/dual-translation-remediation.tech]] — promotion → cards pipeline
- [[decisions/ADR-016-per-pair-error-taxonomy]]
