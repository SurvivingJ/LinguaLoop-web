---
title: "ADR-040: Tier-keyed question prompt templates"
status: proposed
date: 2026-11-09
---

# ADR-040: Tier-keyed question prompt templates

## Context
Question prompts live in `prompt_templates`, one active row per `(task_name, language_id)`
(`question_literal_detail`, `question_vocabulary_context`, …). Level is passed only as a
`{difficulty}` slot, and some templates carry a "requirements by difficulty" section (the ja
vocab template, v3, has bands 1–4 / 5–6 / 7–9 for *what* to ask). Nothing controls the
*language* of the question at a level: the [[evaluations/ja-test-review-2026-11-09]] found kanji
definitions as choices on all-hiragana beginner passages, and the fixed ja stem
`文中の「…」の意味として最も適切なものを選んでください` appears on T1 tests. One prompt has to
serve a toddler passage and a T6 essay, and the model follows the prompt's own register.
Stem rotation (`stem_rotation.py`) is keyed by language × type only, so a rotated main-idea stem
is equally formal at T2 and T6.

## Decision
Add a nullable `tier_id smallint` column to `prompt_templates`. The question-template loader asks
for `(task_name, language_id, tier_id)` first and falls back to the `tier_id IS NULL` row, then to
the existing English fallback. Tier rows are authored for **T1–T3** first; T4–T6 keep the current
rows. Stem pools in `stem_rotation.py` gain an optional tier band (`'1-3'`, `'4-6'`).
Use is behind `TEST_GEN_TIER_TEMPLATES` (default off) until the template experiment
(TASK-927) shows it is not worse, then the default flips per language.

## Consequences
- Easier: write a beginner prompt in beginner language (ja kana stems, zh HSK1–2 wording, en A1–A2)
  without bloating one prompt with every level's rules; compare arms by flipping one env var.
- Harder: every `prompt_templates` reader must keep its current result when tier rows exist — the
  test-generation loader, `prompt_service.get_template_config`, and the model/provider resolution
  that reads `model`/`provider` from template rows (`_resolve_models`). Tier rows must carry the
  same `model`/`provider` as their base row, or resolution must be pinned to the base row.
- 27 rows (the types each of T1–T3 uses × 3 languages) to keep in step with base-row edits. They are
  generated as `base.template_text || level block` by `scripts/build_tier_question_templates.py`, so
  after a base edit, refresh them by deleting the tier rows for that task and re-running the seed
  (it skips rows that already exist).
- The unique index `(task_name, language_id, version)` stays (other migrations upsert on it), so tier
  rows use versions 100 + tier.

## Alternatives Considered
- **Task-name suffix** (`question_vocabulary_context__t1`): no migration, but every reader that
  matches by `task_name` (cost logging, prompt audits, model resolution) would see unknown task
  names; rejected.
- **Bigger single template with per-tier sections**: no schema change, but the current v3 ja vocab
  template already does this for content and still produced off-level language; longer prompts
  also raise the cost of every call. Kept as the control arm in the experiment.
- **Post-hoc simplification of choices** (a rewrite pass): an extra model call per question and
  it can change meaning; rejected.
