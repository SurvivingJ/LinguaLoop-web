---
title: "DT Taxonomy v6 (ADR-031) — Task Breakdown"
feature: dt-taxonomy-v6
prose_page: ../business-rules/translation-error-taxonomy.md
tech_page: ../decisions/ADR-031-dt-taxonomy-v6-merge.md
total_tasks: 20
done: 0
---

# DT Taxonomy v6 (ADR-031) — Task Breakdown

**DRAFT 2026-09-28 — awaiting user review before it is finalised (CLAUDE.md §5d).**

Takes the merged v5+jev taxonomy ([[decisions/ADR-031-dt-taxonomy-v6-merge]]) live in Dual
Translation grading. Source data (read-only inputs to these tasks):
`data/eval/taxonomy_merge_2026-09-27/` — `merged_taxonomy.json` (zh 20 / ja 23 / en 20 types, all
fields incl. `explanation_variant`), `v5_to_merged.csv` (32 v5 rows → v6, kind 1:1/merge/split/dropped),
`v6_label_overlay.json` (174 gold+silver errors relabelled, all `final`), `overlay_band_changes.json`
(12 band changes + the `en_silver_24` v5 defect).

## Ground truth the tasks rely on (code as of 2026-09-28)

- **Loading.** `grader_cascade.get_active_taxonomy()` → `_fetch_active_config()` reads the highest
  `is_active` row of `dt_taxonomy_version`, cached in `_cfg_cache` for the process life. The v5 seed
  (`migrations/dt_taxonomy_v5_seed.sql`) deactivated every other row and upserted itself active in one
  transaction — i.e. **seeding was the cutover**. v6 splits those two steps (seed inactive, activate later).
- **Taxonomy JSON keys:** `pairs` (9 keys: `en`/`ja`/`zh` baselines + 6 directed `L1-L2`; list order is the
  subtype index contract read by `_resolve_subtypes` → `_enum_lookup`), `subtype_meta` (**global**, keyed by
  slug — `scoring.compute_dimension_bands` reads only `.dimension`; `particle` carries `historical_alias: true`),
  `subtype_glosses[slug][lang]` (L2 gloss shown to the Detector/Verifier; L1 gloss used by `explainer._subtype_gloss`),
  `templates[slug][l1]` (Rule-layer explanation rendered by `grader_cascade.render_explanation` inside `_decode_error`).
  Checked: no v6 slug has different dimension/severity/treatable/cloze_suitable across languages, so a
  global `subtype_meta` still works.
- **Rubric exemplars drift.** Live rubric v6 (`migrations/dt_rubric_v6_seed.sql`) exemplars carry
  `subtype_slug` `tense_aspect` (en), `particle_wa_ga` (ja), `aspect_marker` (zh). None exist in v6's pair
  lists, so `prompts._slug_index` returns None and **every Detector/Verifier exemplar is silently dropped**
  (logged warning, ADR-020) the moment v6 activates unless alias resolution is added (TASK-841).
- **Storage.** `dt_error_instance` (`migrations/dual_translation_groundwork.sql`) has free-text `subtype`, no
  taxonomy version, no variant column; the insert is whitelisted by `routes/dual_translation.py::_ERROR_INSERT_COLUMNS`.
  The grade's taxonomy version is only recoverable from `dt_grade.grader_trace->'prompt_version'->>'taxonomy'`
  (v2 grades only). `dt_error_profile_entry` is `UNIQUE (user_id, l1_language_id, l2_language_id, subtype)`;
  `dt_card` has `profile_entry_id` + its own `subtype`.
- **Remediation reads subtype literally.** `scripts/dt_nightly_synthesis.py::fetch_error_records` groups a
  30-day window of `dt_error_instance.subtype` (`synthesis.cluster_key`); `cards._latest_error_for_subtype`
  does `.eq("subtype", entry.subtype)`. A mixed v5/v6 window or a re-keyed profile row breaks both unless
  normalised (TASK-851).
- **Eval.** `scripts/run_dt_grading_eval.py` loads `tests/fixtures/dt_gold/{l2}.json` (30 items/L2, fixed
  dir), compares `expected_errors[].subtype` + `severity_v2`, has `--rubric-file` (evaluate-before-activate)
  but **no taxonomy equivalent**. `scripts/dt_gold_seed_helper.derive_bands` hard-codes `V5_DIMENSION` keyed
  on `subtype_v5_target`. Baseline to beat: [[evaluations/dt-grading-v2-2026-07-19]] (EN span F1 .941 /
  subtype acc 1.000 / overall QWK .824; JA .880 / .864 / .419; ZH .880 / .818 / .245; n=30/L2, QWK noise ±.1).
- **Live data volume was NOT checked** (a read-only Supabase query was refused by the permission guard in
  the planning session) — TASK-836 does it first.

## Conventions for every task here
- Per-L2 prompt text is authored **in the L2** (zh blocks in zh, ja in ja, en in en), matching the existing
  `prompts.py` per-L2 dicts; parser enums/placeholders stay Latin (see memory note "zh/ja prompt Latin is
  mostly contract").
- Run tests with `PYTHONPATH=. pytest tests/<file>` (explicit path).
- Nothing here is applied live except in TASK-853, and only with operator approval.

## Critical path
837 → 838 → 845 → 846 → 850 → 853 → 854, joined by 841 → 849 → 850 and 847 → 849, and by
836/842 → 851 → 852 → 853. Native review (839/840) runs in parallel and does **not** gate cutover
(same policy v5 shipped under, ADR-019), but its fixes are re-seeded before or after cutover.

---

## TASK-836: Live DT data inventory (read-only)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Size the migration before writing it. Count live rows per subtype in `dt_error_instance`,
`dt_error_profile_entry` (by subtype × remediation_status) and `dt_card`, list `dt_taxonomy_version` /
`dt_rubric_version` rows with `is_active`, and count `dt_error_instance` rows whose grade has no
`grader_trace.prompt_version.taxonomy` (pre-v2 grades). The planning session could not run this (permission
guard refused the production read) — an operator-approved session must.

**Acceptance Criteria:**
- [ ] Counts recorded in this task's Technical Notes (or a short `wiki/evaluations/dt-taxonomy-v6-inventory-<date>.md`).
- [ ] Explicit count of rows on split/dropped slugs: ja `particle_wa_ga`, ja `particle`, en `pronoun_reference`, ja `script_choice`.
- [ ] Explicit count of profile rows that will COLLIDE after merge (same user/pair holding two v5 slugs that map to one v6 slug, e.g. `ba_construction`+`bei_passive`, `resultative_complement`+`directional_complement`, `adverbial_order`+`word_order`).

**Technical Notes:**
Read-only SQL via Supabase MCP `execute_sql` (project `kpfqrjtfxmujzolwsvdq`). Collision query: join
`dt_error_profile_entry` to a VALUES list of the `v5_to_merged.csv` rows, group by
`(user_id, l1_language_id, l2_language_id, v6_slug)` having `count(*) > 1`. If total profile rows are tiny
(memory: DT traffic was ~50 days stale in Aug), note that TASK-852 can be a single reviewed script run.

**Files to Create / Modify:**
- none (report only)

**Verification:**
Numbers present; the collision count is stated even if zero.

---

## TASK-837: v6 taxonomy builder + inactive seed migration (pairs, subtype_meta, aliases)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Generate `migrations/dt_taxonomy_v6_seed.sql` from `merged_taxonomy.json` with a checked-in builder, so the
JSON stays the single source. The seed inserts version 6 **with `is_active = false`** and does NOT deactivate
v5 (activation is TASK-853). v5 must stay resolvable: every v5 slug absent from v6 is kept in `subtype_meta`
as a `historical_alias` and mapped in a new `legacy_aliases` key.

**Acceptance Criteria:**
- [ ] `scripts/build_dt_taxonomy_v6.py` reads `data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json` + `v5_to_merged.csv` (+ glosses/templates file from TASK-838 when present) and writes the SQL deterministically (byte-identical on re-run).
- [ ] `pairs`: 9 keys (`en`,`ja`,`zh`, `ja-en`,`zh-en`,`en-ja`,`zh-ja`,`en-zh`,`ja-zh`); each directed pair's list equals its L2 baseline list, in `merged_taxonomy.json` order (that order becomes the index contract).
- [ ] `subtype_meta`: one entry per distinct v6 slug (union across languages) with `dimension`, `default_severity` (minor/major/critical), `treatable`, `cloze_suitable`, `jev_bucket` (B1–B9, `null`, or the string `"pending"` for `plural_number` / `topic_comment`), `class`; plus every v5 slug not in v6 (`classifier`, `aspect_marker`, `de_particles`, `ba_construction`, `bei_passive`, `resultative_complement`, `directional_complement`, `adverbial_order`, `particle_wa_ga`, `particle_case`, `verb_conjugation`, `tense_aspect_ja`, `keigo_register`, `counter_classifier`, `script_choice`, `article`, `tense_aspect`, `subject_verb_agreement`, `pronoun_reference`, `particle`) copied verbatim from v5's meta with `historical_alias: true`. None of these aliases appear in any `pairs` list.
- [ ] New top-level key `legacy_aliases`: `{v5_slug: {"to": <v6 slug or null>, "kind": "1:1"|"merge"|"split"|"dropped"}}` for all 32 CSV rows. Split rows use their primary target (`particle_wa_ga`→`wa_ga`, `pronoun_reference`→`pronoun`, `particle`→`case_particle`) and keep `kind: "split"`; `script_choice` → `{"to": null, "kind": "dropped"}`.
- [ ] Seed SQL: `INSERT ... VALUES (6, false, $taxonomy$...$taxonomy$::jsonb, '<description>') ON CONFLICT (version) DO UPDATE SET taxonomy = EXCLUDED.taxonomy, description = EXCLUDED.description` — **no `is_active` change on conflict, no UPDATE of other rows**. Header comment carries the NATIVE-REVIEW FLAG list (every new/renamed type's zh/ja strings).
- [ ] `tests/test_dual_translation_taxonomy_v6.py` (pattern: `test_dual_translation_taxonomy_v5.py`, parses the SQL literal): pair lists match `merged_taxonomy.json` exactly; `subtype_meta` total over every pair slug; every `legacy_aliases` target is a v6 pair slug or null; `meaning_inversion` is fidelity/critical in all 3; `contradiction` is major; seed never sets `is_active = true` and never updates other rows.

**Technical Notes:**
Extra keys in `subtype_meta` are safe: `scoring.compute_dimension_bands` does `subtype_meta.get(slug, {}).get("dimension")`.
`definition` from `merged_taxonomy.json` is NOT copied into `subtype_meta` (it is English authoring text; the
model sees `subtype_glosses`). Until TASK-838 lands, the builder may emit glosses/templates only for the 8
unchanged core slugs (copied from v5) — the seed is not activatable before 838 is merged.

**Files to Create / Modify:**
- `scripts/build_dt_taxonomy_v6.py` — new builder.
- `migrations/dt_taxonomy_v6_seed.sql` — generated.
- `tests/test_dual_translation_taxonomy_v6.py` — new.

**Verification:**
`python scripts/build_dt_taxonomy_v6.py && git diff --exit-code migrations/dt_taxonomy_v6_seed.sql` (second run
clean); `PYTHONPATH=. pytest tests/test_dual_translation_taxonomy_v6.py tests/test_dual_translation_taxonomy_v5.py`.

---

## TASK-838: Author v6 glosses, Rule templates and word_choice variant templates (AI first draft)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-837

**Description:**
Every v6 slug needs `subtype_glosses[slug]` in en/zh/ja and `templates[slug]` in en/zh/ja (the L1 an
explanation is rendered in), plus three `word_choice` variant templates per L1. Write them into a data file
the builder merges, then regenerate the seed. Reuse v5's strings verbatim where the type is unchanged (8 core
slugs, `topic_comment`, `particle_other`, `plural_number`, `phrasal_verb`, en `preposition`); rewrite them where
a rename changed scope (`aspect_negation` +negation, `tam` +modality, `de_particle` widened to any 的/地/得
misuse, `complement`, `ba_bei`, `word_order` absorbing adverbial order, `wa_ga` narrowed, `pronoun` narrowed);
draft new ones for `separable_verb`, `coverb`, `connective`, `transitivity_voice`, `modification`,
`clause_linkage`, `kanji_choice`, `complementation`, `lexical_form`, `semantic_anomaly`, `contradiction`,
`meaning_inversion`.

**Acceptance Criteria:**
- [ ] `data/eval/taxonomy_merge_2026-09-27/v6_strings.json` = `{"subtype_glosses": {...}, "templates": {...}, "variant_templates": {"word_choice": {"wrong_word": {en,zh,ja}, "wrong_sense": {...}, "shared_translation": {...}}}}`, each string tagged in a sibling `provenance` map as `v5_verbatim` | `ai_draft`.
- [ ] Totality: every slug in any v6 `pairs` list has a gloss for en/zh/ja and a template for en/zh/ja (test in `test_dual_translation_taxonomy_v6.py`).
- [ ] Every template uses only `{learner_form}` / `{corrected_form}` placeholders and `str.format` succeeds with both (existing `render_explanation` contract).
- [ ] The `meaning_inversion` gloss states the by-effect rule in the L2 (polarity/negation, direction, quantity/degree, agent/recipient flipped vs the reference ⇒ this type, whatever the surface edit); the `omission` gloss states "content lost without reversal". The zh `de_particle` gloss/templates say any 的/地/得 misuse is an error.
- [ ] `shared_translation` templates can name the shared L1 gloss only through `{learner_form}`/`{corrected_form}` (no new placeholder) — e.g. en: "“{learner_form}” and “{corrected_form}” can both translate to the same word in your language, but here only “{corrected_form}” fits."
- [ ] Builder merges the file; `migrations/dt_taxonomy_v6_seed.sql` regenerated; EN strings approved by the user in review.

**Technical Notes:**
`variant_templates` is a NEW top-level key (not `templates["word_choice:wrong_word"]`) so v5-era code that
iterates `templates` never sees a non-slug key. `templates["word_choice"]` stays as the variant-less fallback.
Source definitions: `merged_taxonomy.json[*].definition` and `explanation_variant.definitions`.

**Files to Create / Modify:**
- `data/eval/taxonomy_merge_2026-09-27/v6_strings.json` — new.
- `scripts/build_dt_taxonomy_v6.py` — merge strings.
- `migrations/dt_taxonomy_v6_seed.sql` — regenerated.
- `tests/test_dual_translation_taxonomy_v6.py` — totality/placeholder tests.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_taxonomy_v6.py -k "gloss or template"`.

---

## TASK-839: Native-speaker review — zh strings and zh type judgements

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** docs
**Complexity:** M (3-8h, human)
**Depends On:** TASK-838

**Description:**
A native zh reader reviews every `ai_draft` zh string from TASK-838 (glosses + templates, incl. the zh-L1
renderings of ja/en types) and the zh-specific type judgements the ADR flags as AI-reviewed only:
`separable_verb`, `coverb`, `connective` (major), `de_particle` scope (all 的/地/得 misuse = error), `ba_bei`,
`complement`, `semantic_anomaly`, `contradiction`, `meaning_inversion`. Also the zh 的/地/得 prompt block (TASK-844).
Non-blocking for cutover (v5 precedent, ADR-019); fixes are re-seeded via the builder.

**Acceptance Criteria:**
- [ ] Review sheet `data/eval/taxonomy_merge_2026-09-27/native_review_zh.csv` (slug, field, string, verdict ok/fix, fix text) filled.
- [ ] Fixes applied to `v6_strings.json`, `provenance` flipped to `native_reviewed`, seed regenerated.
- [ ] Any dimension/severity disagreement is written up as an ADR-031 Open Question instead of silently changed.

**Technical Notes:**
Generate the sheet from `v6_strings.json` filtered to `provenance == ai_draft` and lang zh.

**Files to Create / Modify:**
- `data/eval/taxonomy_merge_2026-09-27/native_review_zh.csv`, `v6_strings.json`, `migrations/dt_taxonomy_v6_seed.sql`.

**Verification:**
No zh entry left at `ai_draft` in `v6_strings.json` provenance.

---

## TASK-840: Native-speaker review — ja strings and ja type judgements

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** docs
**Complexity:** M (3-8h, human)
**Depends On:** TASK-838

**Description:**
As TASK-839 for ja: all `ai_draft` ja strings plus the ja type judgements `transitivity_voice`,
`modification`, `clause_linkage`, `kanji_choice` (accuracy), `wa_ga` narrowed scope (relative-clause /
structural cases only; most main-clause は/が is not an error), `tam`, `semantic_anomaly`, `contradiction`,
`meaning_inversion`, and the ja precedence block from TASK-843. Confirm the drop of `script_choice`.

**Acceptance Criteria:**
- [ ] `native_review_ja.csv` filled; fixes applied; `provenance` → `native_reviewed`; seed regenerated.
- [ ] Rubric exemplar check: the live ja exemplar (tagged `particle_wa_ga`) is still a valid `wa_ga` error under the narrowed v6 definition — or a replacement exemplar is supplied for TASK-841's follow-up.

**Technical Notes:** as TASK-839.

**Files to Create / Modify:**
- `data/eval/taxonomy_merge_2026-09-27/native_review_ja.csv`, `v6_strings.json`, `migrations/dt_taxonomy_v6_seed.sql`.

**Verification:**
No ja entry left at `ai_draft`.

---

## TASK-841: Taxonomy version pin + alias-aware subtype resolution

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-837

**Description:**
Let a process grade under a specific taxonomy version without touching the DB active flag (eval, staging,
emergency rollback), and give every consumer one function that maps any historical slug to its v6 slug.
Also stop the rubric exemplars from being dropped under v6.

**Acceptance Criteria:**
- [ ] `DT_TAXONOMY_VERSION` env (read at call time, like the other DT_* knobs): unset → current behaviour (highest active row); set to an int → `get_active_taxonomy` / `get_active_taxonomy_version` load `.eq("version", N)` regardless of `is_active`; unknown version raises the existing RuntimeError. `grader_trace.prompt_version.taxonomy` reports the version actually used.
- [ ] New `services/dual_translation/taxonomy_compat.py`: `normalize_subtype(slug, taxonomy_cfg) -> tuple[str | None, str]` returning `(v6_slug, kind)` — identity for a pair slug; `legacy_aliases` lookup otherwise; `(None, "unknown")` for anything else; pure, no DB.
- [ ] Exemplar resolution is alias-aware: `build_detector_system_prompt` / `build_verifier_system_prompt` (and v1 `build_system_prompt`) accept `subtype_aliases: dict | None`; `_resolve_exemplar_error` / `_exemplar_text` retry `_slug_index` with `aliases[slug]["to"]` when the direct lookup misses and the alias kind is `1:1` or `merge` (never `split`/`dropped`). `_grade_v2` passes `taxonomy_cfg.get("legacy_aliases")`.
- [ ] Under v5 (no `legacy_aliases`) the built prompts are byte-identical to today (regression test).
- [ ] Under v6, the en (`tense_aspect`→`verb_form_tense`) and zh (`aspect_marker`→`aspect_negation`) exemplars render; the ja one (`particle_wa_ga`, kind split) is dropped with the existing warning until a v6 rubric re-slugs it (see Technical Notes).

**Technical Notes:**
Cache keys: `_cfg_cache["taxonomy"]` / `["taxonomy_version"]` must be invalidated when the env value changes
between calls in tests — key the cache on the resolved version, or document `clear_caches()`.
The ja exemplar: rather than alias a split, file a rubric v7 seed that only re-slugs exemplars (`verb_form_tense`,
`wa_ga`, `aspect_negation`) once TASK-840 confirms the ja exemplar — optional, and must be activated together
with v6 (TASK-853 runbook step) or it drifts back under v5.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — env pin in `get_active_taxonomy`, `get_active_taxonomy_version`, `_fetch_active_config`/`_fetch_active_scalar`; pass aliases in `_grade_v2`.
- `services/dual_translation/taxonomy_compat.py` — new.
- `services/dual_translation/prompts.py` — `subtype_aliases` kwarg + alias retry.
- `tests/test_dual_translation_grader_cascade.py`, `tests/test_dual_translation_prompts.py`, new `tests/test_dual_translation_taxonomy_compat.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py tests/test_dual_translation_grader_cascade.py tests/test_dual_translation_taxonomy_compat.py`.

---

## TASK-842: Schema — version + variant columns on error rows, remap columns on profile rows

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-836

**Description:**
Make every error row self-describing (which taxonomy it was graded under, which word_choice variant), and give
profile rows room to record how they were re-keyed. Additive, nullable, safe to apply before any code change.

**Acceptance Criteria:**
- [ ] `migrations/dt_taxonomy_v6_columns.sql`: `dt_error_instance` += `taxonomy_version smallint NULL`, `explanation_variant text NULL CHECK (explanation_variant IS NULL OR (subtype = 'word_choice' AND explanation_variant IN ('wrong_word','wrong_sense','shared_translation')))`.
- [ ] Backfill `dt_error_instance.taxonomy_version` from `dt_grade.grader_trace->'prompt_version'->>'taxonomy'` joined on `submission_id`; rows with no value stay NULL (meaning "pre-v2, ≤ v5").
- [ ] `dt_error_profile_entry` += `taxonomy_version smallint NULL`, `v5_subtype text NULL`, `remap_flag text NULL CHECK (remap_flag IN ('split_needs_review','dropped','merged'))`.
- [ ] `routes/dual_translation.py::_ERROR_INSERT_COLUMNS` += `taxonomy_version`, `explanation_variant`; the `_cached_grade` select list reads them back; `_grade_v2` stamps `taxonomy_version` on every final error dict.
- [ ] Idempotent (`ADD COLUMN IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` before `ADD CONSTRAINT`); verification queries in the footer.

**Technical Notes:**
The CHECK ties variant to `word_choice`; the grader must null the variant if the Verifier re-types an error.
Do not add a FK to `dt_taxonomy_version.version` (historical rows pre-date some versions).

**Files to Create / Modify:**
- `migrations/dt_taxonomy_v6_columns.sql` — new.
- `routes/dual_translation.py` — insert whitelist + cached select.
- `services/dual_translation/grader_cascade.py` — stamp version.
- `tests/test_dual_translation_routes.py` — insert carries the two columns.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_routes.py`; after apply (operator):
`select taxonomy_version, count(*) from dt_error_instance group by 1`.

---

## TASK-843: meaning_inversion by-effect precedence in Detector/Verifier prompts

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-837

**Description:**
ADR-031 rules label-by-effect: any error that flips polarity/negation, direction, quantity/degree or
agent/recipient relative to the reference is `meaning_inversion` (critical), whatever its surface form (a
preposition swap, a word swap, a dropped negator); a pure content loss stays `omission`. Add a per-L2
precedence block to both the Detector and Verifier system prompts, written in the L2, shown only when the
active subtype list contains `meaning_inversion` so v5 prompts stay byte-stable.

**Acceptance Criteria:**
- [ ] `prompts.py` gains `_PRECEDENCE_V6: dict[str, str]` for en/zh/ja; `build_detector_system_prompt` and `build_verifier_system_prompt` append it after the subtype list iff `"meaning_inversion" in subtypes`.
- [ ] Each block states: (1) by-effect rule with the four effect kinds; (2) dropped/added negator that reverses polarity → `meaning_inversion`, not `omission`/`addition`; (3) content lost without reversal → `omission`; (4) `contradiction` is only a sentence-internal clash visible without the reference; (5) severity for `meaning_inversion` is critical (index 2).
- [ ] The Verifier block tells it to re-type (adjust verdict) a Detector error whose effect is an inversion but whose subtype is `preposition`/`word_choice`/`omission`.
- [ ] Tests: v5 subtype list → prompts byte-identical to pre-change snapshot; v6 list → block present once in each of detector/verifier for all 3 L2s; zh/ja blocks contain no English prose (enum slugs excepted).
- [ ] Gold probe (offline assertion in TASK-850's report, not here): `en_seed_15` ("with"→"without") expected `meaning_inversion`/critical.

**Technical Notes:**
Byte stability matters for prompt caching (module docstring of `prompts.py`). Put the block in a fixed
position; do not interpolate anything per request.

**Files to Create / Modify:**
- `services/dual_translation/prompts.py` — `_PRECEDENCE_V6` + inclusion.
- `tests/test_dual_translation_prompts.py` — snapshot + presence tests.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py`.

---

## TASK-844: zh 的/地/得 rule in zh prompts

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-843

**Description:**
User ruling 2026-09-27: ANY 的/地/得 misuse (的-for-得, 的-for-地, 地-for-的 …) is a `de_particle`/minor error,
never acceptable variation. jev's original carve-out (的-for-地 not an error) is revoked. Put the rule in the
zh Detector and Verifier prompts so the model neither suppresses it as a variant nor files it under
`word_choice`/`orthography`.

**Acceptance Criteria:**
- [ ] The zh `_PRECEDENCE_V6` block (or a sibling `_ZH_DE_RULE` included under the same v6 condition) says, in zh: 的/地/得 用错一律标为 `de_particle`（轻微），不属于可接受的变体，包括“的”代替“地/得”; 不要标为 word_choice 或 orthography.
- [ ] The zh acceptable-variation list shown to the model (rubric `acceptable_variation.zh`) contains nothing that could cover a 的/地/得 swap — verified by test against `dt_rubric_v6_seed.sql`.
- [ ] Test: zh v6 detector + verifier prompts contain the rule exactly once; ja/en prompts do not.
- [ ] Gold probe (in TASK-850's report): `zh_seed_11`, `zh_multi_02`, `zh_silver_20`, `zh_silver_29` graded `de_particle`/minor.

**Technical Notes:**
`tests/fixtures/dt_gold/README.md`'s "得/的 variant acceptable" clause was already removed per ADR-031.

**Files to Create / Modify:**
- `services/dual_translation/prompts.py`, `tests/test_dual_translation_prompts.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py -k de_`.

---

## TASK-845: word_choice explanation_variant — grader output + deterministic resolver

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-838, TASK-841, TASK-842

**Description:**
Every `word_choice` error carries `explanation_variant` ∈ `wrong_word | wrong_sense | shared_translation`.
Precedence (ADR-031 Decision A): same lemma → `wrong_sense`; learner word and correct word share a gloss in
the learner's L1 → `shared_translation`; else `wrong_word`. The first two are decided in Python from the sense
dictionary where possible; the model's own call is used only for the residual.

**Acceptance Criteria:**
- [ ] `prompts.VARIANT_ENUM = ("wrong_word", "wrong_sense", "shared_translation")`; under v6 the Detector schema (`_detector_schema`) and Verifier `added_errors` accept an optional `explanation_variant` index on word_choice errors, with one short per-L2 line defining wrong_sense narrowly (same lemma, different own sense). `_decode_error` decodes it via `_enum_lookup`; invalid/missing → None (never drops the error).
- [ ] New `services/dual_translation/word_choice_variant.py::resolve_variant(db, *, learner_form, corrected_form, l2_code, l1_language_id, model_variant) -> tuple[str, str]` returning `(variant, basis)` with basis ∈ `same_lemma | shared_gloss | model | default`.
- [ ] Lemma resolution: exact `dim_vocabulary.lemma` match for the L2 first; else tokenize with `services/dictation/tokenizer.tokenize(form, l2_code)` and accept only when exactly one content token resolves. Unresolvable either side → skip the deterministic steps.
- [ ] Same `vocab_id` both sides → `wrong_sense`.
- [ ] Shared gloss: senses in `dim_word_senses` for both vocab_ids with `definition_language_id = <learner L1 id>`; split each definition on `;`, `,`, `、`, `，`, `／`, `/`; normalise (lowercase, strip parentheticals, strip leading "to "/"a "/"an "/"the "); non-empty exact intersection → `shared_translation`. No gloss rows in that L1 for either word (always the case for en L2 today — en words have no zh/ja glosses) → skip to the model's call.
- [ ] Residual: model variant if it is `wrong_word`/`wrong_sense`; a model `shared_translation` that the lookup could not confirm is kept only when the lookup was skipped for lack of glosses (basis `model`), else downgraded to `wrong_word`; missing → `wrong_word` (basis `default`).
- [ ] Runs once over `final_errors` after `_apply_verdicts` (so Verifier re-types are respected) and before the explainer; non-`word_choice` errors get `explanation_variant = None`. At most 2 DB round trips per word_choice error, batched per submission; any DB exception → basis `default`, logged, grading continues.
- [ ] `grader_trace.variant_basis` counts per basis. Unit tests with a fake db covering each branch, incl. the overlay pairs 知道/认识-style shared gloss, same-lemma, en L2 skip.

**Technical Notes:**
The variant does not change scoring (one `word_choice` `subtype_meta` row). Check the 3 `variant_uncertain`
overlay items (`zh_multi_02#1` 普通/简单, `ja_multi_04#1` 仕事/役割, `en_multi_03#0` key/important) through
`resolve_variant` and record the outcome in TASK-850's report — ADR-031 asks for exactly that re-check.
The gloss-matching rule above is this plan's choice (flagged to the user); if the user prefers embedding
similarity, only `_shared_gloss()` changes.

**Files to Create / Modify:**
- `services/dual_translation/word_choice_variant.py` — new.
- `services/dual_translation/prompts.py` — enum, schema, per-L2 definition line.
- `services/dual_translation/grader_cascade.py` — decode + post-pass in `_grade_v2`.
- `tests/test_dual_translation_word_choice_variant.py` — new; `tests/test_dual_translation_grader_cascade.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_word_choice_variant.py tests/test_dual_translation_grader_cascade.py`.

---

## TASK-846: Variant-aware Rule templates + explainer context

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-845

**Description:**
Render the word_choice Rule layer from the variant template, and let the explainer's Application layer know
which variant it is explaining.

**Acceptance Criteria:**
- [ ] `render_explanation(taxonomy_cfg, subtype, l1_code, learner_form, corrected_form, variant=None)`: when `variant` is set and `taxonomy_cfg["variant_templates"][subtype][variant][l1_code]` exists, use it; else today's behaviour. The post-pass in TASK-845 re-renders `explanation` (and `explanation_parts.rule`) after the variant is fixed.
- [ ] `explainer._numbered_error` adds `"variant"` (the variant slug, or omitted) to each numbered error; `prompts.build_explainer_user_prompt` includes it; the explainer system prompt gets one sentence per L1 on what each variant means for the learner (shared_translation → contrast the two words that share an L1 translation).
- [ ] Tests: each of the 3 variants × 3 L1 renders its own template; missing variant template falls back to `templates["word_choice"]` with `used_fallback=False`; explainer payload carries the variant.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py`, `services/dual_translation/explainer.py`, `services/dual_translation/prompts.py`.
- `tests/test_dual_translation_explainer.py`, `tests/test_dual_translation_grader_cascade.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_explainer.py tests/test_dual_translation_grader_cascade.py`.

---

## TASK-847: Promote the v6 overlay into v6 gold/silver fixtures + seed helper

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-837

**Description:**
Cut real v6 fixtures from `v6_label_overlay.json` so the harness can grade against v6 labels. The v5 fixtures
in `tests/fixtures/dt_gold/` stay untouched as the regression set until cutover.

**Acceptance Criteria:**
- [ ] `scripts/build_dt_gold_v6.py` writes `tests/fixtures/dt_gold_v6/{zh,ja,en}.json` (30 items each, same ids/order as v5) and `tests/fixtures/dt_silver_v6/{zh,ja,en}.json` (from `data/eval/jev_dt_2026-09-26/silver/{l}_final3.json`). Per error: `subtype` = overlay `v6_type`, `subtype_v6_target` = same, `severity_v2` = overlay `v6_severity`, `explanation_variant` for word_choice, original `subtype_v5_target` kept for traceability. Items matched by `(item_id, error_index)`; the build fails on any unmatched error.
- [ ] `expected_bands` updated for the 12 items in `overlay_band_changes.json`; all others unchanged.
- [ ] `en_silver_24` gets its missing `meaning_inversion`/critical error from `data/eval/jev_dt_2026-09-26/silver/en_silver_24_fix.json` in the v6 silver file (v5 silver untouched), clearing the `v5_baseline_mismatch`.
- [ ] `scripts/dt_gold_seed_helper.py`: `V6_DIMENSION` built from `merged_taxonomy.json`; `derive_bands(..., taxonomy_version=5|6)` reads `subtype_v5_target` or `subtype_v6_target`; default stays 5.
- [ ] Test: for every v6 gold/silver item, `derive_bands(offline=True, taxonomy_version=6)` reproduces `expected_bands` for accuracy/fidelity/understandability. Counts assertion: 21 `meaning_inversion`, 28 `word_choice` (20/0/8 by variant) across gold+silver.
- [ ] `tests/fixtures/dt_gold_v6/README.md` states provenance (overlay + reviewed resolutions) and that v5 fixtures are frozen for regression.

**Files to Create / Modify:**
- `scripts/build_dt_gold_v6.py` — new.
- `tests/fixtures/dt_gold_v6/*`, `tests/fixtures/dt_silver_v6/*` — new.
- `scripts/dt_gold_seed_helper.py` — v6 dimension map + version param.
- `tests/test_dual_translation_gold_seed_helper.py` — v6 cases.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_gold_seed_helper.py`.

---

## TASK-848: Add narrow wrong_sense gold items (coverage gap)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-847

**Description:**
0 of 28 word_choice labels in gold+silver is a narrow `wrong_sense` (ADR-031 OPEN), so the variant cannot be
measured. Add 2 single-error items per L2 where the learner uses the reference's own lemma in the wrong one of
its senses, marked `kind: "single"`, to the v6 gold files only.

**Acceptance Criteria:**
- [ ] 6 new items (`{l}_v6_ws_01..02`) with `expected_errors[0].subtype = word_choice`, `explanation_variant = wrong_sense`, severity per the word_choice default, bands via `derive_bands(taxonomy_version=6)`.
- [ ] Both lemmas exist in `dim_vocabulary` with ≥2 senses (so TASK-845's same-lemma check can fire) — recorded in the item `note`.
- [ ] zh/ja items added to the TASK-839/840 native review sheets.

**Technical Notes:**
Same-lemma wrong-sense in a *translation* task is rare by construction (learner and reference usually differ in
lemma); items will likely be a polysemous word placed where the reference uses it in another sense with a
different complement. If none can be made natural, record that and close the variant as "grader judgement only".

**Files to Create / Modify:**
- `tests/fixtures/dt_gold_v6/{zh,ja,en}.json`, `scripts/build_dt_gold_v6.py` (append hand items).

**Verification:**
Seed-helper test passes with the 6 items.

---

## TASK-849: Eval harness — taxonomy candidate + v6 fixtures + v6 metrics

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-841, TASK-847

**Description:**
Evaluate-before-activate for the taxonomy, mirroring `--rubric-file`.

**Acceptance Criteria:**
- [ ] `run_dt_grading_eval.py --taxonomy-file migrations/dt_taxonomy_v6_seed.sql` parses the `$taxonomy$...$taxonomy$` literal and pre-seeds `gc._cfg_cache["taxonomy"]` / `["taxonomy_version"]` (live DB untouched); `--fixture-set {v5,v6,v6_silver}` picks the fixture dir (default v5).
- [ ] Report adds: per-subtype confusion for `meaning_inversion` vs `omission`/`word_choice`/`preposition`/`contradiction`; `meaning_inversion` recall/precision; `explanation_variant` accuracy on word_choice TPs + `variant_basis` distribution; count of exemplar-drop warnings seen during the run (must be 0 for en/zh).
- [ ] Offline test: fixture loading + candidate taxonomy pre-seeding with a stubbed grader (no network).

**Files to Create / Modify:**
- `scripts/run_dt_grading_eval.py`, `services/dual_translation/eval_metrics.py`, `tests/test_dt_eval_metrics.py`, `tests/test_dt_eval_harness_retry.py` (or a new harness test).

**Verification:**
`python scripts/run_dt_grading_eval.py --l2 zh --out /tmp/x.md --taxonomy-file migrations/dt_taxonomy_v6_seed.sql --fixture-set v6` (dry run, no `--live`) prints the plan; `PYTHONPATH=. pytest tests/test_dt_eval_metrics.py`.

---

## TASK-850: Acceptance gate — v6 vs same-day v5 control

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h, ~wall clock)
**Depends On:** TASK-843, TASK-844, TASK-846, TASK-849

**Description:**
Paid live run, all three L2s, `--framework-v2`: (a) v5 control — live taxonomy, `--fixture-set v5`; (b) v6
candidate — `--taxonomy-file` v6, `--fixture-set v6`; (c) v6 on `v6_silver` as supplementary evidence.
Same day, same rubric, same model routing, so model drift since 2026-07-19 does not masquerade as a taxonomy
effect.

**Acceptance Criteria (gate — all must hold per L2 for GO):**
- [ ] Span F1 (v6) ≥ span F1 (v5 control) − 0.05.
- [ ] Subtype accuracy on v6 gold ≥ 0.80 (v5 baseline: en 1.000 / ja .864 / zh .818) — the finer tagset is allowed to cost ≤ .05 vs the same-day v5 control, no more.
- [ ] Overall-band QWK (v6) ≥ v5 control − 0.10 (the documented ±.1 noise floor).
- [ ] `meaning_inversion` recall ≥ 0.75 pooled over gold+silver (21 labels), and no clean item gets a critical error (clean-FP not above control).
- [ ] Probes reported: `en_seed_15` → meaning_inversion; the four zh de_particle items → de_particle/minor; the 3 `variant_uncertain` items' `resolve_variant` outcome.
- [ ] 0 "no explanation template" and 0 exemplar-drop warnings for en/zh under v6.
- [ ] Report `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` with the table vs [[evaluations/dt-grading-v2-2026-07-19]], cost, and a GO / NO-GO line.

**Technical Notes:**
Run with `--resume <path>` per L2 (checkpoints). Set a spend cap before starting (the 2026-07-19 pass is the
cost reference). NO-GO → file follow-ups against 843/845 and re-run; do not loosen thresholds in the report.

**Files to Create / Modify:**
- `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` — new.

**Verification:**
The report exists with all six gate rows filled and a GO/NO-GO verdict.

---

## TASK-851: Nightly synthesis + cards v6-aware (mixed-version windows)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-841, TASK-842

**Description:**
After cutover the 30-day synthesis window mixes v5 and v6 `dt_error_instance.subtype` values; without
normalisation `classifier` and `measure_word` would cluster as two subtypes and never reach the promotion
threshold together. Normalise at read time; never rewrite error rows.

**Acceptance Criteria:**
- [ ] `dt_nightly_synthesis.fetch_error_records` maps each row's subtype through `taxonomy_compat.normalize_subtype` against the ACTIVE taxonomy; kind `dropped`/`unknown` rows are excluded from clustering (counted in the run log); `split` rows cluster under their primary target.
- [ ] Upserted profile rows get `taxonomy_version` = active version.
- [ ] `cards._latest_error_for_subtype` looks up errors whose subtype is the v6 slug OR any legacy slug aliased to it (`.in_("subtype", [...])`), so a re-keyed profile entry still finds its origin error.
- [ ] Card building keeps using the error's stored forms/spans; the card's `subtype` is written as the v6 slug.
- [ ] Under v5 active (no `legacy_aliases`) behaviour is unchanged (tests).
- [ ] Tests: a window with `ba_construction` ×2 + `ba_bei` ×1 promotes one `ba_bei` entry at threshold 3; `script_choice` rows are ignored under v6.

**Files to Create / Modify:**
- `scripts/dt_nightly_synthesis.py`, `services/dual_translation/synthesis.py` (if the key needs it), `services/dual_translation/cards.py`.
- `tests/test_dual_translation_synthesis.py`, `tests/test_dual_translation_cards.py`, `tests/test_dt_remediation_infrastructure.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_synthesis.py tests/test_dual_translation_cards.py tests/test_dt_remediation_infrastructure.py`;
`python scripts/dt_nightly_synthesis.py --dry-run` against a DB with v6 pinned via `DT_TAXONOMY_VERSION=6`.

---

## TASK-852: Re-key profile history and cards to v6 (with snapshot + rollback)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** TASK-836, TASK-842, TASK-851

**Description:**
One-time rewrite of `dt_error_profile_entry.subtype` (and matching `dt_card.subtype`) from v5 to v6 slugs via
`v5_to_merged.csv`, run at cutover. Error rows are NOT rewritten (they keep the slug they were graded under;
TASK-851 normalises at read time).

**Acceptance Criteria:**
- [ ] `scripts/dt_rekey_profiles_v6.py`, `--dry-run` default, `--apply` to write; prints a per-kind summary.
- [ ] Snapshot first: `CREATE TABLE dt_error_profile_entry_v5_snapshot AS SELECT ...` and `dt_card_v5_subtype_snapshot (id, subtype)` (in `migrations/dt_taxonomy_v6_rekey_snapshot.sql`).
- [ ] 1:1 → rewrite `subtype`, set `v5_subtype`, `taxonomy_version = 6`.
- [ ] merge collisions (same user/l1/l2 landing on one v6 slug): keep the row with the most advanced `remediation_status` (drilling > queued > watching > resolved), set `count` = sum, `severity_rank` = max, `trend` = the kept row's, `remap_flag = 'merged'`; repoint `dt_card.profile_entry_id` of the losers to the survivor, then delete the losers (only after repointing).
- [ ] split (ja `particle_wa_ga`, `particle`, en `pronoun_reference`) → primary target, `remap_flag = 'split_needs_review'` (best-effort bulk remap per ADR-031; list the rows for later human triage).
- [ ] dropped (ja `script_choice`) → `remediation_status = 'resolved'`, `remap_flag = 'dropped'`, subtype left as `script_choice` (still resolvable as a historical alias); its cards are left in place but no new cards are generated (status resolved).
- [ ] `dt_card.subtype` updated to its profile entry's new subtype; post-condition query: 0 cards whose subtype ≠ their profile entry's subtype.
- [ ] `migrations/dt_taxonomy_v6_rekey_rollback.sql` restores both tables from the snapshots.
- [ ] Unit tests on the pure remap planner (collision merge, split, dropped) with fixture rows.

**Technical Notes:**
Idempotent: rows with `taxonomy_version = 6` are skipped. Run inside the TASK-853 window, after the nightly
cron is paused (the advisory lock in `dt_nightly_synthesis._try_advisory_lock` protects against a concurrent run).

**Files to Create / Modify:**
- `scripts/dt_rekey_profiles_v6.py`, `migrations/dt_taxonomy_v6_rekey_snapshot.sql`, `migrations/dt_taxonomy_v6_rekey_rollback.sql` — new.
- `tests/test_dt_rekey_profiles_v6.py` — new.

**Verification:**
`PYTHONPATH=. pytest tests/test_dt_rekey_profiles_v6.py`; dry-run output matches TASK-836's collision/split counts.

---

## TASK-853: Cutover — activate v6 (runbook + activation/rollback SQL)

**Status:** [?] Blocked — needs (1) ADR-031 moved from `proposed` to `accepted` by the user, (2) TASK-850 GO, (3) operator approval to apply live
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-850, TASK-852

**Description:**
Flip the live grader to v6 with a one-statement rollback.

**Acceptance Criteria:**
- [ ] `migrations/dt_taxonomy_v6_activate.sql`: `UPDATE dt_taxonomy_version SET is_active = false WHERE is_active AND version <> 6; UPDATE ... SET is_active = true WHERE version = 6;` in one transaction, with the v5 footer verification queries adapted (expect exactly one active row, version 6).
- [ ] `migrations/dt_taxonomy_v6_rollback.sql`: the mirror (reactivate 5), plus a pointer to `dt_taxonomy_v6_rekey_rollback.sql`.
- [ ] Runbook (in this task, executed in order): apply `dt_taxonomy_v6_columns.sql` (if not already) → deploy code (841–846, 851) → apply `dt_taxonomy_v6_seed.sql` (inactive) → pause nightly cron → snapshot + `dt_rekey_profiles_v6.py --apply` → `dt_taxonomy_v6_activate.sql` (+ optional rubric v7 exemplar re-slug from TASK-841 in the same window) → restart the app (process-wide `_cfg_cache`) → smoke: one graded submission per L2 shows `grader_trace.prompt_version.taxonomy = 6` and non-null `taxonomy_version` on its error rows → resume cron.
- [ ] Rollback drill done once on a non-prod pin (`DT_TAXONOMY_VERSION=5`) before the live flip; the emergency rollback path is `DT_TAXONOMY_VERSION=5` + restart (no DB write needed), then the rollback SQL at leisure.
- [ ] ADR-031 status → `accepted`; [[business-rules/translation-error-taxonomy]] updated to v6; `tests/fixtures/dt_gold_v6` becomes the default `--fixture-set` in the harness (v5 fixtures kept, frozen).

**Files to Create / Modify:**
- `migrations/dt_taxonomy_v6_activate.sql`, `migrations/dt_taxonomy_v6_rollback.sql` — new.
- `wiki/decisions/ADR-031-dt-taxonomy-v6-merge.md`, `wiki/business-rules/translation-error-taxonomy.md`.

**Verification:**
`select version from dt_taxonomy_version where is_active` → 6; smoke submissions as above.

---

## TASK-854: Post-cutover verification (1 week)

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-853

**Description:**
Confirm v6 behaves in production as it did in the gate.

**Acceptance Criteria:**
- [ ] 100% of new `dt_error_instance` rows have `taxonomy_version = 6`; every `word_choice` row has a non-null `explanation_variant`.
- [ ] Share of `meaning_inversion` errors and of critical severity per L2 reported (sanity: not dominating; compare with gate rates).
- [ ] 0 log lines "no explanation template" / "no subtype_glosses entry" / exemplar-drop for en/zh.
- [ ] First nightly synthesis after cutover: no profile rows created under legacy slugs.
- [ ] `split_needs_review` profile rows listed for human triage (or 0).
- [ ] Short note appended to the TASK-850 evaluation page.

**Files to Create / Modify:**
- `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` — append.

**Verification:**
Read-only SQL queries recorded in the note.

---

## TASK-855: (Optional, later) jev bucket question flow for DT grading

**Status:** [?] Blocked — needs: jev porting of `plural_number` / zh+ja `topic_comment` finished (their `jev_bucket` is still `"pending"`), a decision (new ADR) that a jev-backed DT grader is wanted at all, and v6 live (TASK-853)
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-853

**Description:**
Prototype an alternative, cheaper error typer: per detected error span, ask jev bucket yes/no questions
(B1–B9 from `subtype_meta.jev_bucket`), then a type choice within the bucket, plus the one residual
wrong_sense-vs-wrong_word yes/no from Decision A. Compare against the LLM Detector's subtype assignment on the
v6 gold/silver. Start from the existing harness `data/eval/jev_dt_2026-09-26/` (`run.py`, `routing.py`,
`decompose.py`, `taxonomy_data.py`, `score.py`) and the jev taxonomy
`data/eval/jev_grammar_2026-09-26/taxonomy.md` + `taxonomy_addendum_2026-09-27.md`; client `services/jev_client.py`.

**Acceptance Criteria:**
- [ ] Offline eval only (no production wiring): subtype accuracy + cost/latency vs the TASK-850 v6 numbers.
- [ ] Recommendation page under `wiki/evaluations/`; production wiring would be a new task set behind its own flag.

**Files to Create / Modify:**
- `data/eval/jev_dt_v6_<date>/` — new eval dir.

**Verification:**
Evaluation page with a go/no-go recommendation.

---
