---
title: "DT Taxonomy v6 (ADR-031) — Task Breakdown"
feature: dt-taxonomy-v6
prose_page: ../business-rules/translation-error-taxonomy.md
tech_page: ../decisions/ADR-031-dt-taxonomy-v6-merge.md
total_tasks: 21
done: 17
---

# DT Taxonomy v6 (ADR-031) — Task Breakdown

**FINALISED 2026-10-04** after user review of the 2026-09-28 draft (CLAUDE.md §5d). The four user decisions
of 2026-10-04 are recorded in [[decisions/ADR-031-dt-taxonomy-v6-merge]] ("User decisions 2026-10-04") and
applied below:
1. The third `word_choice` `explanation_variant` is **`false_synonym`** (was `shared_translation`): a different
   word that the learner's L1 glosses the same way but with a different meaning/usage (知道 vs 认识). Detected by
   exact match on normalised L1 gloss terms.
2. Split rows are bulk-remapped to the closest v6 type with a review flag.
3. **One-time rewrite** of all historical records to v6 names at cutover (snapshot first; rollback = restore
   snapshot + revert taxonomy version). No translate-on-read layer.
4. ja `script_choice` profile entries, their `dt_error_instance` rows and their `dt_card`s (with those cards'
   `dt_card_review` rows) are **deleted** after the snapshot. Past `dt_grade` bands are not recalculated.

Takes the merged v5+jev taxonomy ([[decisions/ADR-031-dt-taxonomy-v6-merge]]) live in Dual Translation
grading. Source data (inputs to these tasks): `data/eval/taxonomy_merge_2026-09-27/` — `merged_taxonomy.json`
(zh 20 / ja 23 / en 20 types, all fields incl. `explanation_variant`), `v5_to_merged.csv` (32 v5 rows → v6,
kind 1:1/merge/split/dropped), `v6_label_overlay.json` (174 gold+silver errors relabelled, all `final`),
`overlay_band_changes.json` (12 band changes + the `en_silver_24` v5 defect).

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
  (logged warning, ADR-020) the moment v6 activates unless the grader resolves them (TASK-841).
- **Storage + FKs** (`migrations/dual_translation_groundwork.sql`, `dt_error_profile.sql`, `dt_cards.sql`):
  `dt_error_instance` has free-text `subtype`, no taxonomy version, no variant column; insert whitelisted by
  `routes/dual_translation.py::_ERROR_INSERT_COLUMNS`. `dt_error_profile_entry` is
  `UNIQUE (user_id, l1_language_id, l2_language_id, subtype)`. `dt_card.profile_entry_id` →
  `dt_error_profile_entry(id)` and `dt_card.origin_error_id` → `dt_error_instance(id)`; `dt_card_review.card_id`
  (NOT NULL) → `dt_card(id)`. **All three FKs are default NO ACTION — no `ON DELETE CASCADE`/`SET NULL`**, so
  deletes must run child-first (reviews → cards → profile entries / error rows) or they fail.
  `dt_grade.submission_id` cascades from `dt_submission` only; `dt_grade` holds no subtype column (`scores`,
  `diff`, `grader_trace` jsonb). Grading-time taxonomy version is in `dt_grade.grader_trace->'prompt_version'->>'taxonomy'` (v2 grades).
- **Remediation reads subtype literally.** `scripts/dt_nightly_synthesis.py::fetch_error_records` groups a
  30-day window of `dt_error_instance.subtype`; `cards._latest_error_for_subtype` does `.eq("subtype", ...)`.
  Because every historical row is rewritten to v6 at cutover (decision 3), neither needs a translation layer.
- **Eval.** `scripts/run_dt_grading_eval.py` loads `tests/fixtures/dt_gold/{l2}.json` (30 items/L2, fixed
  dir), compares `expected_errors[].subtype` + `severity_v2`, has `--rubric-file` (evaluate-before-activate)
  but **no taxonomy equivalent**. `scripts/dt_gold_seed_helper.derive_bands` hard-codes `V5_DIMENSION` keyed
  on `subtype_v5_target`. Baseline: [[evaluations/dt-grading-v2-2026-07-19]] (EN span F1 .941 / subtype acc
  1.000 / overall QWK .824; JA .880 / .864 / .419; ZH .880 / .818 / .245; n=30/L2, QWK noise ±.1).
- **Live data volume was NOT checked** (a read-only Supabase query was refused by the permission guard in
  the planning session) — TASK-836 does it first.

## Conventions for every task here
- Per-L2 prompt text is authored **in the L2** (zh blocks in zh, ja in ja, en in en), matching the existing
  `prompts.py` per-L2 dicts; parser enums/placeholders stay Latin.
- Run tests with `PYTHONPATH=. pytest tests/<file>` (explicit path).
- Nothing here is applied live except in TASK-853, and only with operator approval.
- **`taxonomy_version` on a row means "the version whose slug vocabulary this row's `subtype` is in"**, not
  "the version that graded it" (that stays in `dt_grade.grader_trace`). Rewritten historical rows therefore
  carry 6.

## Critical path
837 → 838 → 845 → 846 → 850 → 853 → 854, joined by 841 → 849 → 850, 847 → 849, and
836/842 → 852 → 853. Native review (839/840) runs in parallel and does **not** gate cutover
(same policy v5 shipped under, ADR-019); its fixes are re-seeded before or after cutover.

---

## TASK-836: Live DT data inventory (read-only)

**Status:** [x] Done (2026-10-04)
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** XS (<1h)
**Depends On:** none

**Description:**
Size the cutover rewrite before writing it. Count live rows per subtype in `dt_error_instance`,
`dt_error_profile_entry` (by subtype × remediation_status) and `dt_card`; list `dt_taxonomy_version` /
`dt_rubric_version` rows with `is_active`; and sweep the schema for any other column that stores a subtype.
The planning session could not run this (permission guard refused the production read) — an
operator-approved session must.

**Acceptance Criteria:**
- [x] Counts recorded in `wiki/evaluations/dt-taxonomy-v6-inventory-2026-10-04.md`.
- [x] Explicit counts on split/dropped slugs: ja `particle_wa_ga`, ja `particle`, en `pronoun_reference`, ja `script_choice` — for `script_choice` also the number of `dt_card` rows (by `subtype`, `profile_entry_id` or `origin_error_id`) and of `dt_card_review` rows on those cards. **All zero.**
- [x] Explicit count of profile rows that will COLLIDE after rewrite (same user/l1/l2 holding two v5 slugs that map to one v6 slug, e.g. `ba_construction`+`bei_passive`, `resultative_complement`+`directional_complement`, `adverbial_order`+`word_order`, `aspect_marker`→`aspect_negation`). **Zero collisions** (only 4 live zh profile rows exist: aspect_marker/omission/word_choice/word_order, none of which pair up).
- [x] Subtype-bearing column sweep: `information_schema.columns` for any column named like `%subtype%` in `public`, plus a jsonb probe of `dt_card.prompt_payload`, `dt_grade.grader_trace` and `dt_grade.diff` for a `"subtype"` key. Every hit is listed; TASK-852 must cover each one or justify skipping it. **Exactly 3 columns found** (`dt_card.subtype`, `dt_error_instance.subtype`, `dt_error_profile_entry.subtype` — all already in TASK-842's list); jsonb probe found 0 embedded `"subtype"` keys.
- [x] Confirms the FK actions on `dt_card` / `dt_card_review` live (`pg_constraint.confdeltype`) match the repo (NO ACTION). **Confirmed** — all 4 FKs (`dt_card`→`dt_error_instance`, `dt_card`→`dt_error_profile_entry`, `dt_card`→`users`, `dt_card_review`→`dt_card`) are `confdeltype='a'` (NO ACTION).

**Technical Notes:**
Read-only SQL via Supabase MCP `execute_sql` (project `kpfqrjtfxmujzolwsvdq`). Collision query: join
`dt_error_profile_entry` to a VALUES list of the `v5_to_merged.csv` rows, group by
`(user_id, l1_language_id, l2_language_id, v6_slug)` having `count(*) > 1`.

**Result summary:** the live DT dataset is tiny — 4 `dt_submission` rows (single user/L1), 16
`dt_error_instance` rows, 4 `dt_error_profile_entry` rows, 4 `dt_card` rows, 5 `dt_card_review`
rows, **all of it zh**. Despite 67 `dt_passage` rows spanning zh/en/ja, ja and en have never
produced a graded submission. TASK-852's rewrite has almost nothing live to act on today. Full
detail in `wiki/evaluations/dt-taxonomy-v6-inventory-2026-10-04.md`.

**Files to Create / Modify:**
- `wiki/evaluations/dt-taxonomy-v6-inventory-2026-10-04.md` — new.

**Verification:**
Numbers present; collision count and script_choice delete counts stated even if zero.

---

## TASK-837: v6 taxonomy builder + inactive seed migration (pairs, subtype_meta, aliases)

**Status:** [x] Done (2026-10-04) — seed written, NOT applied (applies at TASK-853)
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Generate `migrations/dt_taxonomy_v6_seed.sql` from `merged_taxonomy.json` with a checked-in builder, so the
JSON stays the single source. The seed inserts version 6 **with `is_active = false`** and does NOT deactivate
v5 (activation is TASK-853). Until the cutover rewrite completes, v5 slugs must stay resolvable, so every v5
slug absent from v6 is kept in `subtype_meta` as a `historical_alias` and mapped in a `legacy_aliases` key
(read by the grader's exemplar resolution, TASK-841, and by the rewrite, TASK-852). Also renames the third
variant to `false_synonym` in the source data.

**Acceptance Criteria:**
- [x] Source data renamed: `shared_translation` → `false_synonym` in `merged_taxonomy.json` (`explanation_variant.values` + `definitions`, definition text: "a DIFFERENT word that the learner's L1 glosses the same way as the correct word but with a different meaning/usage, e.g. 知道 vs 认识"), `v6_label_overlay.json`, `overlay_reconciled.json`; `grep -r shared_translation data/eval/taxonomy_merge_2026-09-27` returns nothing.
- [x] `scripts/build_dt_taxonomy_v6.py` reads `merged_taxonomy.json` + `v5_to_merged.csv` (+ `v6_strings.json` from TASK-838 when present) and writes the SQL deterministically (byte-identical on re-run).
- [x] `pairs`: 9 keys (`en`,`ja`,`zh`, `ja-en`,`zh-en`,`en-ja`,`zh-ja`,`en-zh`,`ja-zh`); each directed pair's list equals its L2 baseline list, in `merged_taxonomy.json` order (that order becomes the index contract).
- [x] `subtype_meta`: one entry per distinct v6 slug with `dimension`, `default_severity` (minor/major/critical), `treatable`, `cloze_suitable`, `jev_bucket` (B1–B9, `null`, or `"pending"` for `plural_number` / `topic_comment`), `class`; plus every v5 slug not in v6 (`classifier`, `aspect_marker`, `de_particles`, `ba_construction`, `bei_passive`, `resultative_complement`, `directional_complement`, `adverbial_order`, `particle_wa_ga`, `particle_case`, `verb_conjugation`, `tense_aspect_ja`, `keigo_register`, `counter_classifier`, `script_choice`, `article`, `tense_aspect`, `subject_verb_agreement`, `pronoun_reference`, `particle`) copied from v5's meta with `historical_alias: true`, in no `pairs` list.
- [x] `legacy_aliases`: `{v5_slug: {"to": <v6 slug or null>, "kind": "1:1"|"merge"|"split"|"dropped"}}` for all 32 CSV rows. Split rows map to the closest v6 type (`particle_wa_ga`→`wa_ga`, `pronoun_reference`→`pronoun`, `particle`→`case_particle`) with `kind: "split"`; `script_choice` → `{"to": null, "kind": "dropped"}`.
- [x] Seed SQL: `INSERT ... VALUES (6, false, $taxonomy$...$taxonomy$::jsonb, '<description>') ON CONFLICT (version) DO UPDATE SET taxonomy = EXCLUDED.taxonomy, description = EXCLUDED.description` — no `is_active` change on conflict, no UPDATE of other rows. Header carries the NATIVE-REVIEW FLAG list.
- [x] `tests/test_dual_translation_taxonomy_v6.py` (pattern: `test_dual_translation_taxonomy_v5.py`): pair lists match `merged_taxonomy.json`; `subtype_meta` total over every pair slug; every `legacy_aliases` target is a v6 pair slug or null; `meaning_inversion` fidelity/critical in all 3; `contradiction` major; seed never sets `is_active = true` nor updates other rows.

**Technical Notes:**
Extra keys in `subtype_meta` are safe (`scoring` reads only `.dimension`). `definition` is NOT copied into
`subtype_meta`. The historical-alias meta entries are transitional: after TASK-852's rewrite no live row uses
them, but they stay in the v6 row so a rollback/restore never meets an unresolvable slug.

**Files to Create / Modify:**
- `data/eval/taxonomy_merge_2026-09-27/{merged_taxonomy.json, v6_label_overlay.json, overlay_reconciled.json}` — variant rename.
- `scripts/build_dt_taxonomy_v6.py` — new builder.
- `migrations/dt_taxonomy_v6_seed.sql` — generated.
- `tests/test_dual_translation_taxonomy_v6.py` — new.

**Verification:**
`python scripts/build_dt_taxonomy_v6.py && git diff --exit-code migrations/dt_taxonomy_v6_seed.sql` (second run
clean); `PYTHONPATH=. pytest tests/test_dual_translation_taxonomy_v6.py tests/test_dual_translation_taxonomy_v5.py`.

**Completion notes (2026-10-04):**
- Rename: already applied to `merged_taxonomy.json` + `v6_label_overlay.json` by the 2026-10-04 ADR session (before this task ran); `overlay_reconciled.json` never contained `shared_translation` (it predates Decision A). The only `grep` hits left are that session's untracked backups (`*.pre_rename_2026-10-04.*`, `merged_taxonomy.pre_knockon_2026-10-04.json`) — left in place, not this task's to delete. A test pins the three live files clean.
- `jev_bucket`: the source no longer has any `"pending"` (the 2026-09-28 port gave `plural_number` B4, zh `topic_comment` B4, ja `topic_comment` B3). Buckets differ by L2 for 3 slugs (`word_order` ja null vs B3, `cohesion_connective` en null vs B3, `topic_comment` zh B4 / ja B3), so `subtype_meta.jev_bucket` is a scalar when every L2 agrees and an `{l2: bucket}` map otherwise. All other fields are uniform (builder fails loudly if not).
- `legacy_aliases` has 33 keys (32 v5 pair slugs + `particle`; per-language CSV rows for a shared slug must agree or the builder fails). `kind` is taken verbatim from `v5_to_merged.csv`; the only `split` rows are `particle_wa_ga`, `particle`, `pronoun_reference` (a 2026-10-04 edit that had marked the same-slug rows `topic_comment` zh+ja, `particle_other`, `plural_number`, `phrasal_verb` as `split` was reverted to `1:1` — jev's narrower scope belongs in `jev_grammar_to_merged.csv`, not v5→v6). `impact.py` fixed to match (`de_particles` 1:1) and rerun: 6 need relabel (ja `particle_wa_ga` 3, en `pronoun_reference` 3) of 175 labels.
- `subtype_glosses`/`templates` are emitted EMPTY until `v6_strings.json` exists (TASK-838); the seed header and description say do not activate before then. The builder reads the v5 seed for the historical-alias meta and has a `--check` mode (exit 1 if stale). Test file: 45 tests; v5 tests unchanged (28).
- Not verifiable without a DB (left for apply): the INSERT actually parses/executes in Postgres, and the v6 row reads back `is_active = false` with v5 still active (verification SQL is in the seed footer).

---

## TASK-838: Author v6 glosses, Rule templates and word_choice variant templates (AI first draft)

**Status:** [x] Done (2026-10-04) — AI first draft authored, seed regenerated, NOT applied; **user review of the EN strings still outstanding**
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-837

**Description:**
Every v6 slug needs `subtype_glosses[slug]` in en/zh/ja and `templates[slug]` in en/zh/ja, plus three
`word_choice` variant templates per L1. Reuse v5's strings verbatim where the type is unchanged (8 core slugs,
`topic_comment`, `particle_other`, `plural_number`, `phrasal_verb`, en `preposition`); rewrite where a rename
changed scope (`aspect_negation`, `tam`, `de_particle` widened to any 的/地/得 misuse, `complement`, `ba_bei`,
`word_order` absorbing adverbial order, `wa_ga` narrowed, `pronoun` narrowed); draft new ones for
`separable_verb`, `coverb`, `connective`, `transitivity_voice`, `modification`, `clause_linkage`,
`kanji_choice`, `complementation`, `lexical_form`, `semantic_anomaly`, `contradiction`, `meaning_inversion`.

**Acceptance Criteria:**
- [x] `data/eval/taxonomy_merge_2026-09-27/v6_strings.json` = `{"subtype_glosses": {...}, "templates": {...}, "variant_templates": {"word_choice": {"wrong_word": {en,zh,ja}, "wrong_sense": {...}, "false_synonym": {...}}}}`, each string tagged in a sibling `provenance` map as `v5_verbatim` | `ai_draft`.
- [x] Totality: every pair slug has a gloss and a template for en/zh/ja (test in `test_dual_translation_taxonomy_v6.py`).
- [x] Every template uses only `{learner_form}` / `{corrected_form}` and `str.format` succeeds with both.
- [x] `meaning_inversion` gloss states the by-effect rule in the L2; `omission` gloss states "content lost without reversal"; zh `de_particle` gloss/templates say any 的/地/得 misuse is an error.
- [x] `false_synonym` templates explain the trap without a new placeholder — e.g. en: "“{learner_form}” and “{corrected_form}” can both translate to the same word in your language, but they are used differently: here only “{corrected_form}” fits."
- [x] Builder merges the file; seed regenerated. [ ] EN strings approved by the user in review — **pending**.

**Technical Notes:**
`variant_templates` is a NEW top-level key so code iterating `templates` never sees a non-slug key;
`templates["word_choice"]` stays as the variant-less fallback.

**Files to Create / Modify:**
- `data/eval/taxonomy_merge_2026-09-27/v6_strings.json` — new.
- `scripts/build_dt_taxonomy_v6.py`, `migrations/dt_taxonomy_v6_seed.sql`, `tests/test_dual_translation_taxonomy_v6.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_taxonomy_v6.py -k "gloss or template"`.

**Completion notes (2026-10-04):**
- 249 strings: 240 slug strings (40 v6 slugs × en/ja/zh × gloss+template) + 9 word_choice variant templates. **76 `v5_verbatim`** (28 glosses + 48 templates, byte-identical to the v5 seed — a test pins it), **173 `ai_draft`** (92 glosses + 72 templates + 9 variants). Conventions followed: glosses keyed and written by language (L2 gloss → Detector/Verifier, L1 gloss → explainer), templates keyed by L1 and written in it; v5 only had L2-language glosses for language-specific types, so every L1 gloss for e.g. `article_determiner`/`wa_ga`/`coverb` is new.
- Rename-only types reuse v5 under the old slug, recorded in `v5_renamed_from` (`case_particle`←`particle_case`, `counter`←`counter_classifier`, `agreement`←`subject_verb_agreement`).
- **Deviations from the description's reuse list** (v5 text would misdescribe v6 scope, checked against jev `taxonomy.md` "Not an error" lists): rewrote `measure_word` (v5 said "don't default to 个"; v6/jev: 个 is acceptable), `keigo` (v5 gloss counted 丁寧語 level, now `register`; v6 is direction only), `conjugation` (v5 gloss counted ら抜き as an error, v6 tolerates it; adds adjectives/verb class), `article_determiner` (adds determiners), `verb_form_tense` (adds irregular/participle forms). `omission` glosses rewritten (AC: "content lost without reversal") but its templates kept verbatim; `word_order` rewrote en+zh glosses only (zh absorbs 状语/介词短语/比; en jev scope), ja gloss and all templates verbatim (still accurate).
- `false_synonym` en = the AC example verbatim; ja/zh mirror it ("あなたの母語では" / "在你的母语里"). No new placeholders anywhere.
- Builder: new `validate_strings` (totality, placeholders ⊆ {learner_form, corrected_form}, brace-free glosses, complete variants, provenance tag on every string; fails loudly) and the seed header now lists every AI-drafted slug per language (the v5-style NATIVE-REVIEW flag for strings). `--check` OK; re-run byte-identical.
- zh `de_particle`: `merged_taxonomy.json` `native_name` fixed `结构助词“得/地”` → `结构助词“的/地/得”` (flagged by TASK-844; the builder does not seed `native_name`, so it only fixes the source). The zh gloss now spells out every direction (的→地/得, 地→的 incl. attributive, 得→的/地) and "不属于可接受的变体", matching TASK-844's `_ZH_DE_RULE`, which embeds this gloss as the `{de}` label.
- Tests: +66 in `test_dual_translation_taxonomy_v6.py` (111 total) incl. render-without-fallback for all 6 directed pairs and every baseline×L1, explainer `_subtype_gloss` non-fallback, placeholders tied to `explainer._numbered_error`'s form fields, v5-verbatim byte identity, builder rejection cases, de_particle directions/native_name. v5 28 unchanged; full `pytest tests/ -k "dual_translation or dt_"` = 837 passed.
- Not done here: user review of the EN strings (AC above); zh/ja native review is TASK-839/840.

**EN string review (2026-10-07):** an AI review of the en strings (Opus, at the developer's direction, not a
native-speaker review): `data/eval/taxonomy_merge_2026-09-27/string_review_2026-10-07/en_review.json`
(88 entries: 70 ok, 18 fix). All 18 fixes were applied, none skipped:
- **15 string fixes in `v6_strings.json`.** Glosses: `word_choice`, `word_order`, `meaning_inversion`
  (shortened to a label; the by-effect rule now lives in the precedence block), `case_particle`, `counter`.
  Templates: `omission`, `word_choice` fallback, `complementation`, `semantic_anomaly`, `meaning_inversion`,
  `conjugation`, `keigo`, `de_particle`. Variant templates: `wrong_sense`, `false_synonym`. Every revised
  string is now tagged `ai_draft`, including 3 formerly `v5_verbatim` ones (en `word_choice` gloss, en
  `omission` and `word_choice` templates). The v5 seed is untouched, and
  `test_unchanged_types_reuse_v5_templates` lists the revised keys with a note.
- **Precedence block (item 83).** `_PRECEDENCE_V6['en']` was rewritten as proposed: each placeholder is used
  once, "a clash with the reference" is narrowed to a reversal that only shows against the reference, `{co}`
  now carries both limbs of its definition, and "report once, never also under its surface-form type" is
  stated explicitly. The zh block was rewritten the same way. The ja wording is untouched (TASK-840).
- **Short-name references (item 84).** `prompts._short_label` makes every `index (label)` reference in the
  precedence, 的/地/得 and variant blocks render the gloss short name instead of the full definition. This
  applies to all 3 L2s.
- **Variant block (item 86).** In en and zh, `explanation_variant` is now *required* on every word_choice
  error. The block gives the decision order (same lemma → wrong_sense; else same L1 translation →
  false_synonym; else wrong_word) and names the learner's L1. To make that possible,
  `build_detector_system_prompt` / `build_verifier_system_prompt` take `l1_code=`, and
  `grader_cascade` passes it. The examples are per-L1 (borrow/lend "both 借 in Chinese",
  look/watch "both 見る in Japanese") with an L1-neutral fallback. Under v6 the cached prefix is now
  per-(L1, L2). ja only gains the L1 slot `（英語）/（中国語）`; its required/decision-order rewrite waits for
  TASK-840. The decoder still tolerates a missing key.
- **Empty quotes (items 40/59).** A v6 template that quotes an empty `learner_form`/`corrected_form` (for
  example a dropped "not") now renders as L1 fallback phrasing that quotes only the form that exists, never
  “” or 「」 (`explainer.empty_form_explanation`, called from `grader_cascade.render_explanation`, v6-gated so
  v5 output is unchanged). Variant templates that quote an empty form fall through to the subtype template.
  The ja phrasing is an AI draft for TASK-840. There are new tests for every v6 subtype × L1.
- The v5 prompt sha256 pins pass unchanged. Seed regenerated; `--check` OK.
- [ ] Explicit user sign-off on the revised EN strings is still not recorded.

---

## TASK-839: Native-speaker review — zh strings and zh type judgements

**Status:** [x] Done (2026-10-07) — AI review (Opus) at the developer's direction 2026-10-07, not a native-speaker review
**Feature:** dt-taxonomy-v6
**Type:** docs
**Complexity:** M (3-8h, human)
**Depends On:** TASK-838

**Description:**
A native zh reader reviews every `ai_draft` zh string from TASK-838 (incl. zh-L1 renderings of ja/en types)
and the zh type judgements the ADR flags as AI-reviewed only: `separable_verb`, `coverb`, `connective` (major),
`de_particle` scope, `ba_bei`, `complement`, `semantic_anomaly`, `contradiction`, `meaning_inversion`, the
`false_synonym` explanation, and the zh 的/地/得 prompt block (TASK-844). Non-blocking for cutover.

**Acceptance Criteria:**
- [ ] `data/eval/taxonomy_merge_2026-09-27/native_review_zh.csv` (slug, field, string, verdict ok/fix, fix text) filled.
- [ ] Fixes applied to `v6_strings.json`, `provenance` → `native_reviewed`, seed regenerated.
- [ ] Any dimension/severity disagreement is written up as an ADR-031 Open Question, not silently changed.

**Files to Create / Modify:**
- `native_review_zh.csv`, `v6_strings.json`, `migrations/dt_taxonomy_v6_seed.sql`.

**Verification:**
No zh entry left at `ai_draft`.

**Completion notes (2026-10-07):** AI review (Opus) at the developer's direction 2026-10-07, not a
native-speaker review. The review is in
`data/eval/taxonomy_merge_2026-09-27/string_review_2026-10-07/zh_review.json` (109 entries: 70 ok, 39 fix),
not the CSV named in the AC.
- **All 39 fixes applied.**
  - 29 in `v6_strings.json`: 17 glosses, 10 templates and 2 variant templates. One was modified: the
    `de_particle` zh template keeps the ruling's wording 一律算作错误 instead of the proposed
    任何一种混用都算错误. The zh `topic_comment` and `particle_other` templates and the `topic_comment`
    gloss were `v5_verbatim` before this review.
  - 6 `native_name`s in `merged_taxonomy.json`: full-width slashes, 介词/介动词 → 介词, 话题—述题结构, and
    施受 added to 语义反转.
  - 4 in `prompts.py`: the verifier's `{surface}` now reads "中的任一子类型"; `_ZH_DE_RULE` gains the
    missing-得 clause; `_VARIANT_BLOCK['zh']` is restructured (see TASK-838); the explainer variant
    guidance is revised.
- Revised strings stay `ai_draft`, because an AI review is not `native_reviewed`. So this task's
  Verification line ("no zh entry left at `ai_draft`") is **not** met, by design. A human native pass is
  still advisable (ADR-031 Open Questions).
- **Boundary — reviewer-proposed, pending user confirmation.** A missing 得 in a degree/state complement
  (跑快 → 跑得快) is `de_particle`, not `complement`. This is applied in the zh glosses, `_ZH_DE_RULE` and the
  merged `complement` definition, and recorded in ADR-031 (note dated 2026-10-07).
- **New ADR-031 Open Question:** whether `separable_verb` covers a duration/quantity phrase after the verb
  (睡觉八个小时).
- No dimension or severity was changed.

---

## TASK-840: Native-speaker review — ja strings and ja type judgements

**Status:** [x] Done (2026-10-08) — AI review (Opus) at the developer's direction 2026-10-08, not a native-speaker review
**Feature:** dt-taxonomy-v6
**Type:** docs
**Complexity:** M (3-8h, human)
**Depends On:** TASK-838

**Description:**
As TASK-839 for ja: all `ai_draft` ja strings plus `transitivity_voice`, `modification`, `clause_linkage`,
`kanji_choice` (accuracy), narrowed `wa_ga`, `tam`, `semantic_anomaly`, `contradiction`, `meaning_inversion`,
and the ja precedence block (TASK-843). Confirm the drop of `script_choice` (whose live rows TASK-852 deletes).

**Acceptance Criteria:**
- [ ] `native_review_ja.csv` filled; fixes applied; `provenance` → `native_reviewed`; seed regenerated.
- [ ] Rubric exemplar check: the live ja exemplar (tagged `particle_wa_ga`) is still a valid `wa_ga` error under the narrowed definition — or a replacement exemplar is supplied for the optional rubric v7 re-slug (TASK-841 notes).

**Files to Create / Modify:**
- `native_review_ja.csv`, `v6_strings.json`, `migrations/dt_taxonomy_v6_seed.sql`.

**Verification:**
No ja entry left at `ai_draft`.

**Note (2026-10-07):** still open. The AI ja string review (the counterpart of the en/zh reviews of
2026-10-07) was blocked and is pending. Items that are now in scope for it:
- the ja `_VARIANT_BLOCK` still says 任意 and gives no decision order (en/zh were made required + ordered);
  it only gained the L1 slot;
- the ja empty-form fallback phrasing in `explainer._EMPTY_FORM_PHRASES` (new AI draft);
- the ja `_PRECEDENCE_V6` wording, which was not rewritten when the en/zh blocks were (short-name references
  only).

**Completion notes (2026-10-08):** AI review (Opus) at the developer's direction 2026-10-08, not a
native-speaker review. The review is in
`data/eval/taxonomy_merge_2026-09-27/string_review_2026-10-07/ja_review.json` (125 entries: 93 ok, 32 fix,
plus `exemplar_proposal`), not the CSV named in the AC.
- **All 32 fixes applied, none skipped or modified.**
  - 23 in `v6_strings.json`: 15 glosses, 7 templates and the `false_synonym` variant template (it said
    あなたの母語では; it now names 日本語, as en/zh name their L1). Main themes: jargon and calques replaced
    for an age-tier-3 reader (補部, 相, 裸の動詞, 本＝本, 時間枠), 参照訳 → 参照文, the ambiguous wa_ga
    "主節と異なる従属節の主語" rule, `clause_linkage`'s と-conditional wording, and the missing-得 boundary
    mirrored into the ja-L1 `complement` gloss. The ja `meaning_inversion` template now quotes only
    `corrected_form` (as en does), so a dropped negation no longer falls back to the generic phrasing. The
    `topic_comment` gloss was `v5_verbatim` before this review.
  - 4 `native_name`s in `merged_taxonomy.json`: 活用（動詞・形容詞）, 自動詞・他動詞／受身・使役,
    連体修飾形（い・な・の）, 意味の反転（極性・方向・数量・動作主）.
  - 5 in `prompts.py`: `_PRECEDENCE_V6['ja']` was rewritten to the en/zh structure (reversal-only, each
    placeholder once, report once; `{co}` has no connective limb because ja connectives are
    `clause_linkage`). The verifier addendum now says のいずれか. `_VARIANT_BLOCK['ja']` is required, decision-ordered
    and names the L1 (`{l1_sentence}`/`{l1_ref}`/`{example}` replace `{l1_paren}`), with a new per-L1
    `_VARIANT_EXAMPLE['ja']` (着る/履く). The explainer variant guidance quotes 「語彙選択」.
  - The `explainer._EMPTY_FORM_PHRASES['ja']` phrasing was checked and kept unchanged.
- Revised strings stay `ai_draft`, so this task's Verification line is **not** met, by design (same as
  TASK-839). A human native pass is still advisable.
- **Type judgements:** all upheld. No dimension or severity was changed. The `script_choice` drop is confirmed.
- **Rubric exemplar:** the live ja exemplar (部品は/がセットになっている) is a main-clause は/が choice, so under the
  narrowed `wa_ga` it is **not an error**. A replacement (これは弟は作ったカレーです → 弟が, span [3, 5]) is
  proposed in ADR-031 (note dated 2026-10-08) for the optional rubric v7 re-slug. `dt_rubric_v6_seed.sql`
  is not edited.
- Tests: two tests were updated with notes (the ja variant marker; the placeholder-once test now covers ja),
  and two ja tests were added. Seed regenerated; `--check` OK; the v5 sha256 pins are unchanged.

---

## TASK-841: Taxonomy version pin + grader-side v5 alias for rubric exemplars

**Status:** [x] Done (2026-10-04) — pin default-unset (behaviour unchanged); nothing applied, v6 not activated
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-837

**Completion notes (2026-10-04):**
- **Pin.** `grader_cascade.taxonomy_version_pin()` reads `DT_TAXONOMY_VERSION` at call time (unset/blank → None; non-int
  → RuntimeError). `get_active_taxonomy`: None → the unchanged active-row path and `"taxonomy"` cache key; N →
  `_fetch_version_config` (`.eq("version", N)`, no `is_active` filter), cached under `taxonomy@N`, missing row →
  RuntimeError. `get_active_taxonomy_version` returns N under a pin, so `grader_trace.prompt_version.taxonomy` and the
  TASK-842/851 `taxonomy_version` stamps report the pinned version. The pinned row's pair list is the `subtypes` list
  TASK-843's `meaning_inversion` gate reads — no prompt wiring needed.
- **Deviation — alias lives in `grader_cascade`, not `prompts.py`** (TASK-844 was editing `prompts.py`). New
  `alias_rubric_exemplars(rubric_cfg, taxonomy_cfg, subtypes)` rewrites an exemplar's `subtype_slug` *before* the
  builders see it, when the slug is not in `subtypes`, the taxonomy's `legacy_aliases` kind is `1:1`/`merge`, and the
  target is in `subtypes`. Covers `exemplars[l2]` and `exemplars.detector[l2]`; verifier exemplars carry indices. Called
  once in `grade_submission` after subtype resolution, so v1, v2 and the arbiter all get it. No `subtype_aliases` kwarg
  on the builders. Returns the **same object** when nothing changes (always under v5, which has no `legacy_aliases`),
  so v5 prompts are byte-identical. It never mutates the cached rubric (it copies on write).
- **Exemplars under v6:** en `tense_aspect`→`verb_form_tense` and zh `aspect_marker`→`aspect_negation` render; ja
  `particle_wa_ga` (kind `split`) is still dropped with the existing prompts.py warning. The ja Detector/v1 prompt has
  no worked exemplar under v6 until the optional rubric v7 re-slug (`wa_ga`, after TASK-840 confirms the example) lands.
- Tests: new `tests/test_dt_taxonomy_pin.py` (19 passed; uses the real rubric v6 / taxonomy v5 / taxonomy v6 seeds).
  Run against every `tests/test_dual_translation*` + `tests/test_dt_*` file: 830 passed, 2 failed. Both failures
  are in `test_dual_translation_taxonomy_v6.py` (ja `subtype_glosses` script check; builder placeholder
  `KeyError`), from the in-flight TASK-838 seed-string work. They do not touch the grader.

**Description:**
Shrunk 2026-10-04 (decision 3: historical rows are rewritten, so there is no translate-on-read layer and no
`taxonomy_compat` module). Two things remain, both needed by the grader during the transition: (a) grade under
a chosen taxonomy version without touching the DB active flag (eval harness, staging, rollback drill); (b) keep
the live rubric's v5-slugged exemplars from being dropped under v6.

**Acceptance Criteria:**
- [x] `DT_TAXONOMY_VERSION` env (read at call time): unset → current behaviour (highest active row); an int → `get_active_taxonomy` / `get_active_taxonomy_version` load `.eq("version", N)` regardless of `is_active`; unknown version raises the existing RuntimeError. `grader_trace.prompt_version.taxonomy` reports the version actually used; the cache is keyed on the resolved version.
- [x] *(met by a different route — see completion notes: the alias is applied to the rubric in `grader_cascade.alias_rubric_exemplars`, not inside `prompts.py`)* `build_detector_system_prompt` / `build_verifier_system_prompt` (and v1 `build_system_prompt`) accept `subtype_aliases: dict | None`; `_resolve_exemplar_error` / `_exemplar_text` retry `_slug_index` with `aliases[slug]["to"]` on a miss when the alias kind is `1:1` or `merge` (never `split`/`dropped`). `_grade_v2` passes `taxonomy_cfg.get("legacy_aliases")`.
- [x] Under v5 (no `legacy_aliases`) the built prompts are byte-identical to today (regression test).
- [x] Under v6 the en (`tense_aspect`→`verb_form_tense`) and zh (`aspect_marker`→`aspect_negation`) exemplars render; the ja one (`particle_wa_ga`, split) is dropped with the existing warning.

**Technical Notes:**
Optional follow-up, same cutover window: a rubric v7 seed that only re-slugs exemplars (`verb_form_tense`,
`wa_ga`, `aspect_negation`) after TASK-840 confirms the ja exemplar; it makes the alias retry dead code and
must be activated together with v6 (TASK-853 runbook) or it drifts under v5.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — env pin; pass aliases in `_grade_v2`.
- `services/dual_translation/prompts.py` — `subtype_aliases` kwarg + alias retry.
- `tests/test_dual_translation_grader_cascade.py`, `tests/test_dual_translation_prompts.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py tests/test_dual_translation_grader_cascade.py`.

---

## TASK-842: Schema — version / variant / remap columns + snapshot tables

**Status:** [x] Done (2026-10-04) — migration written, NOT applied (applies at TASK-853, first runbook step); code gated behind `DT_TAXONOMY_COLUMNS` (default OFF)
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-836

**Description:**
Additive, nullable columns so every subtype-bearing row is version-stamped and split remaps are flagged, plus
the empty snapshot tables the cutover rewrite fills. Safe to apply before any code change.

**Completion notes (2026-10-04):**
- **Deviation — feature flag.** The code half (insert whitelist, `_cached_grade` read-back, `_grade_v2` stamp)
  would break every graded submission if deployed before the migration is applied: PostgREST rejects an
  insert/select naming a missing column. So it is gated on new `Config.DT_TAXONOMY_COLUMNS` (env, default
  OFF). Off = byte-identical behaviour (same select string, no new keys on error dicts or inserts, even if an
  error dict carries them). **TASK-853 runbook: apply `dt_taxonomy_v6_columns.sql`, then set
  `DT_TAXONOMY_COLUMNS=true` and restart.** TASK-845 must set `explanation_variant` knowing it only persists
  while the flag is on.
- **Addition — insert-side variant guard.** `_persist_grade` nulls `explanation_variant` on any non-`word_choice`
  row before insert, so a variant left on a re-typed error cannot trip the CHECK and fail the whole insert.
  TASK-845 should still null it at source.
- **Snapshot tables** are `LIKE <source>` (names, types, NOT NULL only — no identity/defaults/CHECKs/FKs) +
  `snapshot_at` + `PRIMARY KEY (id)`, created after the ALTERs so they include the new columns. LIKE freezes the
  column list: TASK-852's snapshot/restore must name columns explicitly. RLS enabled with **no policies**
  (deny-all to anon/authenticated; service role bypasses) — they hold every learner's errors; no `auth.*`
  reference, so the file also applies to a plain local Postgres for TASK-852's integration test.
- CHECKs are added `NOT VALID` in the transaction and `VALIDATE`d after `COMMIT` (migrations/CLAUDE.md).
  `remap_flag` CHECKs spell out `IS NULL OR …` (equivalent to the spec's form).
- No ordering dependency on `dt_taxonomy_v6_seed.sql` (TASK-837) — disjoint objects.
- Parsed OK with libpg_query (pglast, 35 statements); not executed against any database. Only an apply can
  confirm `LIKE … , PRIMARY KEY (id)` and the footer queries.
- Tests: `tests/test_dual_translation_routes.py` (+7, `TestTaxonomyColumns`) and
  `tests/test_dual_translation_grader_cascade.py` (+2, stamp on/off) — 108 passed across both files; 696 passed
  for `-k "dual_translation or dt_"` over `tests/`.

**Acceptance Criteria:**
- [x] `migrations/dt_taxonomy_v6_columns.sql`:
  - `dt_error_instance` += `taxonomy_version smallint NULL`, `explanation_variant text NULL CHECK (explanation_variant IS NULL OR (subtype = 'word_choice' AND explanation_variant IN ('wrong_word','wrong_sense','false_synonym')))`, `remap_flag text NULL CHECK (remap_flag IN ('split_needs_review'))`.
  - `dt_error_profile_entry` += `taxonomy_version smallint NULL`, `remap_flag text NULL CHECK (remap_flag IN ('split_needs_review','merged'))`.
  - `dt_card` += `taxonomy_version smallint NULL`.
  - Every other subtype-bearing column found by TASK-836 gets the same `taxonomy_version` column. (TASK-836 found none beyond the three above.)
- [x] Snapshot tables created empty, same column types as the source plus `snapshot_at timestamptz DEFAULT now()`: `dt_v5_snapshot_error_instance (id, subtype, taxonomy_version, remap_flag)` (all rows touched), `dt_v5_snapshot_profile_entry` (full rows), `dt_v5_snapshot_card` (full rows), `dt_v5_snapshot_card_review` (full rows), and `dt_v5_snapshot_error_instance_full` (full rows, for deleted `script_choice` errors).
- [x] `routes/dual_translation.py::_ERROR_INSERT_COLUMNS` += `taxonomy_version`, `explanation_variant`; the `_cached_grade` select reads them back; `_grade_v2` stamps `taxonomy_version` = active version on every final error. (All three only while `DT_TAXONOMY_COLUMNS` is on — see completion notes.)
- [x] Idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, drop-then-add CHECKs); verification queries in the footer.

**Technical Notes:**
No FK to `dt_taxonomy_version.version`. The variant CHECK ties variant to `word_choice`, so the grader must
null the variant if the Verifier re-types an error. Snapshot tables have no FKs (they hold deleted rows).

**Files to Create / Modify:**
- `migrations/dt_taxonomy_v6_columns.sql` — new.
- `routes/dual_translation.py`, `services/dual_translation/grader_cascade.py`.
- `tests/test_dual_translation_routes.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_routes.py`.

---

## TASK-843: meaning_inversion by-effect precedence in Detector/Verifier prompts

**Status:** [x] Done (2026-10-04) — v6-gated; inert while v5 is the resolved taxonomy
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** M (3-8h)
**Depends On:** TASK-837

**Description:**
ADR-031 rules label-by-effect: any error that flips polarity/negation, direction, quantity/degree or
agent/recipient relative to the reference is `meaning_inversion` (critical), whatever its surface form; a pure
content loss stays `omission`. Add a per-L2 precedence block to both the Detector and Verifier system prompts,
written in the L2, shown only when the subtype list contains `meaning_inversion` so v5 prompts stay byte-stable.

**Acceptance Criteria:**
- [x] `prompts.py` gains `_PRECEDENCE_V6: dict[str, str]` for en/zh/ja; detector + verifier builders append it after the subtype list iff `"meaning_inversion" in subtypes`.
- [x] Each block states: (1) the by-effect rule with the four effect kinds; (2) a dropped/added negator that reverses polarity → `meaning_inversion`, not `omission`/`addition`; (3) content lost without reversal → `omission`; (4) `contradiction` is only a sentence-internal clash visible without the reference; (5) `meaning_inversion` severity is critical (index 2).
- [x] The Verifier block tells it to re-type a Detector error whose effect is an inversion but whose subtype is `preposition`/`word_choice`/`omission`.
- [x] Tests: v5 subtype list → prompts byte-identical to a pre-change snapshot; v6 list → block present once in each of detector/verifier for all 3 L2s; zh/ja blocks contain no English prose (enum slugs excepted).

**Files to Create / Modify:**
- `services/dual_translation/prompts.py`, `tests/test_dual_translation_prompts.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py`.

**Completion notes (2026-10-04):**
- Gate = `"meaning_inversion" in subtypes`, where `subtypes` is the list `grader_cascade` resolved from the taxonomy row in
  use at runtime (active row today; the TASK-841 `DT_TAXONOMY_VERSION` pin feeds the same list, so no extra wiring is
  needed). v5 has no such slug → the block is never built. Snapshot proof: sha256 of the Detector + Verifier prompts for
  the v5 en/zh/ja baseline lists (bare and glossed labels) captured before the edit, pinned in the test.
- Deviation: subtypes are referenced as the live `index (label)` the model reads in the subtype list (`19 (meaning_inversion)`
  today; `19（语义反转）` once TASK-838 glosses land), not as bare slugs — the model reports indices and, under a
  glossed taxonomy, never sees the slug.
- Deviation: the Verifier re-type list is per-L2 — the adposition type is `preposition` (en) / `coverb` (zh) /
  `case_particle` (ja) — and also names `addition` (an added negator gets filed there, per rule 2).
- Verifier wording is a sentence appended to the shared block (`_PRECEDENCE_V6_VERIFIER`). zh/ja text is an AI draft,
  in scope for the TASK-839/840 native review.
- TASK-844 can add `_ZH_DE_RULE` alongside, under the same `_precedence_block` gate.
- Tests: `tests/test_dual_translation_prompts.py` 53 passed (+15 new); all `test_dual_translation*` + `test_dt_*` 707 passed.

---

## TASK-844: zh 的/地/得 rule in zh prompts

**Status:** [x] Done (2026-10-04) — v6-gated; inert while v5 is the resolved taxonomy
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-843

**Description:**
User ruling 2026-09-27: ANY 的/地/得 misuse is a `de_particle`/minor error, never acceptable variation. Put the
rule in the zh Detector and Verifier prompts so the model neither suppresses it as a variant nor files it under
`word_choice`/`orthography`.

**Acceptance Criteria:**
- [x] The zh `_PRECEDENCE_V6` block (or a sibling `_ZH_DE_RULE` under the same v6 condition) says, in zh: 的/地/得 用错一律标为 `de_particle`（轻微），不属于可接受的变体，包括“的”代替“地/得”；不要标为 word_choice 或 orthography。
- [x] Test asserts rubric `acceptable_variation.zh` (`dt_rubric_v6_seed.sql`) contains nothing that could cover a 的/地/得 swap.
- [x] Test: the zh v6 detector + verifier prompts contain the rule exactly once; ja/en prompts do not.

**Files to Create / Modify:**
- `services/dual_translation/prompts.py`, `tests/test_dual_translation_prompts.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_prompts.py -k de_`.

**Completion notes (2026-10-04):**
- Sibling `_ZH_DE_RULE` (+ Verifier addendum `_ZH_DE_RULE_VERIFIER`), appended by `_precedence_block` after the TASK-843
  text. Gate = TASK-843's (`meaning_inversion` in the resolved list) AND `l2 == "zh"` AND `"de_particle"` in the list
  (v6-only slug; v5 has `de_particles`). v5 prompts byte-identical — the pinned pre-TASK-843 sha256s still pass.
- Rule names every direction (的→地/得, 地→的 incl. attributive 地, 得→的/地), severity 轻微（0）, "not acceptable variation,
  don't ignore because meaning is unaffected", not word_choice/orthography (cited as live `index（label）`). Verifier
  addendum: don't reject（1）a 的/地/得 error as variation; re-type word_choice/orthography → adjust（2）to de_particle/minor.
- v5-era text audit: no prompt, rubric zh `acceptable_variation` (v4–v6 identical; v1/v2 have none) or v5 taxonomy gloss/Rule template says 的/地/得
  variation is acceptable. The revoked "的-for-地 is not an error" carve-out lived only in the jev eval taxonomy
  (ADR-031 §gold relabelling), never in grader text.
- **Gloss flag for TASK-838:** `merged_taxonomy.json` zh `de_particle` `native_name` is `结构助词“得/地”` — it omits 的,
  so a zh label taken from it would contradict the rule (attributive 地-for-的 and 的-for-地/得 are in scope). Suggested
  zh label: `结构助词“的/地/得”`. `v6_strings.json` does not exist yet; not edited here.
- Tests: `tests/test_dual_translation_prompts.py` 61 passed (+8 `de_`); all `test_dual_translation*` + `test_dt_*` 748 passed.

---

## TASK-845: word_choice explanation_variant — grader output + deterministic resolver

**Status:** [x] Done (2026-10-04) — v6-gated; inert while v5 is the resolved taxonomy; variant persists only with `DT_TAXONOMY_COLUMNS` on
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** L (1-2d)
**Depends On:** TASK-838, TASK-841, TASK-842

**Description:**
Every `word_choice` error carries `explanation_variant` ∈ `wrong_word | wrong_sense | false_synonym`.
Precedence (ADR-031 Decision A, renamed 2026-10-04): same lemma → `wrong_sense`; a different word whose
L1 gloss matches the correct word's → `false_synonym`; else `wrong_word`. The first two are decided in Python
from the sense dictionary where possible; the model's call is used only for the residual.

**Acceptance Criteria:**
- [x] `prompts.VARIANT_ENUM = ("wrong_word", "wrong_sense", "false_synonym")`; under v6 the Detector schema and Verifier `added_errors` accept an optional `explanation_variant` index on word_choice errors, with one short per-L2 line defining each variant. `_decode_error` decodes it via `_enum_lookup`; invalid/missing → None (never drops the error).
- [x] New `services/dual_translation/word_choice_variant.py::resolve_variant(db, *, learner_form, corrected_form, l2_code, l1_language_id, model_variant) -> tuple[str, str]` returning `(variant, basis)`, basis ∈ `same_lemma | shared_gloss | model | default`.
- [x] Lemma resolution: exact `dim_vocabulary.lemma` match in the L2 first; else `services/dictation/tokenizer.tokenize(form, l2_code)` and accept only when exactly one content token resolves. Unresolvable either side → skip the deterministic steps.
- [x] Same `vocab_id` → `wrong_sense`.
- [x] Gloss match (user-approved rule): senses in `dim_word_senses` for both vocab_ids with `definition_language_id = <learner L1 id>`; split definitions on `;` `,` `、` `，` `／` `/`; normalise (lowercase, strip parentheticals, strip leading "to "/"a "/"an "/"the "); non-empty **exact** intersection → `false_synonym`. No gloss rows in that L1 for either word (always so for en L2 today — en words have no zh/ja glosses) → skip to the model's call.
- [x] Residual: model variant if `wrong_word`/`wrong_sense`; a model `false_synonym` the lookup could not confirm is kept only when the lookup was skipped for lack of glosses (basis `model`), else downgraded to `wrong_word`; missing → `wrong_word` (basis `default`).
- [x] Runs once over `final_errors` after `_apply_verdicts` and before the explainer; non-`word_choice` errors get `explanation_variant = None`. ≤2 DB round trips per word_choice error, batched per submission; any DB exception → basis `default`, logged, grading continues.
- [x] `grader_trace.variant_basis` counts per basis. Unit tests with a fake db cover each branch (知道/认识-style gloss match, same-lemma, en-L2 skip, DB failure).

**Technical Notes:**
Scoring is unchanged (one `word_choice` `subtype_meta` row). TASK-850 re-checks the 3 `variant_uncertain`
overlay items (`zh_multi_02#1` 普通/简单, `ja_multi_04#1` 仕事/役割, `en_multi_03#0` key/important) through
`resolve_variant`.

**Files to Create / Modify:**
- `services/dual_translation/word_choice_variant.py` — new.
- `services/dual_translation/prompts.py`, `services/dual_translation/grader_cascade.py`.
- `tests/test_dual_translation_word_choice_variant.py` — new; `tests/test_dual_translation_grader_cascade.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_word_choice_variant.py tests/test_dual_translation_grader_cascade.py`.

**Completion notes (2026-10-04):**
- **Gate** = new `prompts.variants_enabled(subtypes)`: `meaning_inversion` (TASK-843's v6 marker) AND `word_choice` in the
  resolved list. Off (every v5 grade) → no prompt line, schema unchanged (`_error_schema_item` adds the key only when on),
  `_decode_error` adds no key, resolver never called, no `grader_trace.variant_basis` — the pinned pre-TASK-843 v5 sha256s
  still pass. Persistence still needs `DT_TAXONOMY_COLUMNS` (TASK-842); `_persist_grade`'s insert-side null stays as backup.
- **Prompt**: `_VARIANT_BLOCK` (en/zh/ja, each in its L2; key `explanation_variant` + index digits are the only Latin)
  placed after the precedence block in Detector + Verifier; word_choice cited as live `index (label)`. Examples: en
  borrow/lend, zh 知道/认识, ja 着る/履く. zh/ja are AI drafts → TASK-839/840 review. Verdict adjustments carry no variant.
- **Resolver** `services/dual_translation/word_choice_variant.py`: batched `resolve_variants(db, errors, …)` (what
  `_grade_v2` calls, after the merge + optional arbiter, before the explainer) + the spec's single `resolve_variant`
  wrapper (extra optional `l2_language_id`; derived via `DimensionService` when absent). Exactly 2 round trips per
  submission max (one `dim_vocabulary` `in_('lemma', …)`, one `dim_word_senses` filtered on `definition_language_id = L1`);
  the second is skipped when nothing needs a gloss check. `_grade_v2` gained `l1_language_id` (passed from `grade_submission`).
- **Deviations** (all toward the spec's intent): (1) separators also include full-width `；` — the zh/ja gloss format
  uses it ("紧张；不安"), without it no zh/ja gloss splits; (2) the `standard`-level clarifier after an em dash
  (`— no single English equivalent…`) is dropped before splitting — prose, and two lossy words would "share" it;
  (3) "exactly one content token": en tokens `a/an/the/to` are not content tokens (same list the gloss normaliser strips);
  ja tokenises char-level, so ja relies on the exact-lemma step; (4) "lookup unavailable" (model `false_synonym` kept, basis
  `model`) covers BOTH no-gloss-in-L1 on either side AND an unresolvable lemma — the lookup never ran, so it cannot refute;
  it downgrades only when glosses exist on both sides and share no exact term; (5) a model `wrong_sense` is downgraded to
  `wrong_word` when both lemmas resolved to different words (ADR-031: wrong_sense is same-lemma only); (6) downgrades and
  DB failures report basis `default` (variant `wrong_word`); a `dim_word_senses` failure keeps already-decided same-lemma
  results. `grader_trace.variant_basis` always carries all four keys.
- **For TASK-846**: the explanation is not yet re-rendered from the variant template — `_grade_v2`'s post-pass is the hook.
- Tests: `tests/test_dual_translation_word_choice_variant.py` 33 passed (new, fake db); grader cascade +8 (v5 inert, decode +
  resolve-before-explainer, invalid indices ×4, db=None → default, Verifier re-type clears the variant). Both files 90 passed;
  `tests/ -k "dual_translation or dt_"` 904 passed. No DB writes, no API calls, nothing applied.

---

## TASK-846: Variant-aware Rule templates + explainer context

**Status:** [x] Done (2026-10-05) — v6-only in effect (no variant is ever set under v5); v5 Rule text + explainer prompts byte-identical
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-845

**Description:**
Render the word_choice Rule layer from the variant template, and tell the explainer's Application layer which
variant it is explaining.

**Acceptance Criteria:**
- [x] `render_explanation(..., variant=None)`: when `taxonomy_cfg["variant_templates"][subtype][variant][l1_code]` exists, use it; else today's behaviour. TASK-845's post-pass re-renders `explanation` (and `explanation_parts.rule`) once the variant is fixed.
- [x] `explainer._numbered_error` adds `"variant"`; `prompts.build_explainer_user_prompt` includes it; the explainer system prompt gets one sentence per L1 on each variant (false_synonym → contrast the two words that share an L1 translation and say how their usage differs).
- [x] Tests: 3 variants × 3 L1 render their own template; a missing variant template falls back to `templates["word_choice"]` with `used_fallback=False`; explainer payload carries the variant.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py`, `services/dual_translation/explainer.py`, `services/dual_translation/prompts.py`.
- `tests/test_dual_translation_explainer.py`, `tests/test_dual_translation_grader_cascade.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_explainer.py tests/test_dual_translation_grader_cascade.py`.

**Completion notes (2026-10-05):**
- **Template load path:** `get_active_taxonomy` serves the whole `dt_taxonomy_version.taxonomy` JSONB and the TASK-849
  harness pre-seeds the whole `$taxonomy$` literal, so `variant_templates` (already in `dt_taxonomy_v6_seed.sql` from
  TASK-838) is reachable in both with no loader change. A test parses the real seed SQL the harness way.
- **`render_explanation(..., variant=None)`**: new helper `_render_variant_template`; a variant template that is missing at
  any level, has bad placeholders, or quotes an empty correction falls through to the plain subtype path unchanged
  (`used_fallback=False` when `templates["word_choice"]` exists). `variant=None` is the old code path.
- **Post-pass**: new `grader_cascade.rerender_variant_explanations(errors, taxonomy_cfg, l1_code)`, called in `_grade_v2`
  right after `resolve_variants` (inside the `variants_enabled` gate), before the explainer — so the explainer scaffolds
  `explanation_parts.rule` from the variant text. If parts already exist it also updates `rule` and keeps
  `rule + "\n" + application`. ADR-015 holds: every error still has a rendered explanation before write.
- **Explainer**: `_numbered_error` adds `"variant"` only when the error has a non-null `explanation_variant` (v5 and
  non-word_choice v6 items keep the old 5-key shape). `build_explainer_system_prompt(l1_code, variants=False)` appends
  `prompts._EXPLAINER_VARIANT_GUIDANCE[l1]` (one sentence per variant, slugs Latin as protocol tokens; zh/ja AI drafts →
  TASK-839/840) only when some item carries a variant. `build_explainer_user_prompt` needed no code change (it JSON-dumps
  the items) — docstring only.
- Tests: cascade +18 (3×3 seed-SQL variant renders, 4 fallback cases, empty-correction fall-through, variant=None, post-pass
  unit, v6 end-to-end before explainer, v5 ignores variant_templates); explainer +8. Explainer + cascade + variant files
  143 passed; `tests/ -k "dual_translation or dt_"` 953 passed, 7 skipped. No DB writes, nothing applied, no API calls.

---

## TASK-847: Promote the v6 overlay into v6 gold/silver fixtures + seed helper

**Status:** [x] Done (2026-10-04)
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-837

**Description:**
Cut real v6 fixtures from `v6_label_overlay.json`. The v5 fixtures in `tests/fixtures/dt_gold/` stay untouched
as the regression set until cutover.

**Acceptance Criteria:**
- [x] `scripts/build_dt_gold_v6.py` writes `tests/fixtures/dt_gold_v6/{zh,ja,en}.json` (30 items each, same ids/order as v5) and `tests/fixtures/dt_silver_v6/{zh,ja,en}.json` (from `data/eval/jev_dt_2026-09-26/silver/{l}_final3.json`). Per error: `subtype` = `subtype_v6_target` = overlay `v6_type`, `severity_v2` = overlay `v6_severity`, `explanation_variant` for word_choice (`false_synonym` naming), original `subtype_v5_target` kept. Matched by `(item_id, error_index)`; build fails on any unmatched error. *Done: all 175 labels consumed (also fails on unused labels / form mismatches); `variant_uncertain` carried on the 3 flagged errors; `severity_v1` dropped (stale once `severity_v2` moves); `--check` mode. Silver 34/32/34 items — **en_silver_26 held out** (kind=single, 0 errors: the merge dropped its 90→9 error for no severity majority; fails `verify_item`, no overlay label; needs a tie-break label like en_silver_24 got).*
- [x] `expected_bands` updated for the 12 items in `overlay_band_changes.json`; all others unchanged. *Done: 11 change, not 12 — that report predates en_silver_24's 2026-09-28 repair (it had no error → und 2→4). Restored, meaning_inversion/critical derives the same 4/2/1 as v5, so it is unchanged. The other 11 match the report exactly (test-asserted).*
- [x] `en_silver_24` gets its missing `meaning_inversion`/critical error from `data/eval/jev_dt_2026-09-26/silver/en_silver_24_fix.json` in the v6 silver file only. *Done: `en_final3.json` already carries it (2026-09-28 repair); the build re-inserts from the fix file if fed a pre-repair source.*
- [x] `scripts/dt_gold_seed_helper.py`: `V6_DIMENSION` from `merged_taxonomy.json`; `derive_bands(..., taxonomy_version=5|6)` reads `subtype_v5_target` or `subtype_v6_target`; default 5. *Done: dimension map resolved by module-global name at call time, so `build_overlay.py`'s V5_DIMENSION patching still works; unknown version raises.*
- [x] Test: every v6 item's `derive_bands(offline=True, taxonomy_version=6)` reproduces `expected_bands` for accuracy/fidelity/understandability. Count assertion: 21 `meaning_inversion`, 28 `word_choice` (20 wrong_word / 0 wrong_sense / 8 false_synonym) across gold+silver. *Done, asserting **22** meaning_inversion (21 + the repaired en_silver_24, now in the overlay's 175).*
- [x] `tests/fixtures/dt_gold_v6/README.md` states provenance and that v5 fixtures are frozen for regression.

**Files to Create / Modify:**
- `scripts/build_dt_gold_v6.py` — new; `tests/fixtures/dt_gold_v6/*`, `tests/fixtures/dt_silver_v6/*` — new.
- `scripts/dt_gold_seed_helper.py`, `tests/test_dual_translation_gold_seed_helper.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_gold_seed_helper.py`.

---

## TASK-848: Add narrow wrong_sense gold items (coverage gap)

**Status:** [x] Done (2026-10-06): 1 of 6 items. The shortfall is recorded per the Technical Notes, and the variant stays a grader judgement only for zh/ja.
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-847

**Description:**
0 of 28 word_choice labels is a narrow `wrong_sense` (ADR-031 OPEN). Add 2 single-error items per L2 where the
learner uses the reference's own lemma in the wrong one of its senses, to the v6 gold files only.

**Acceptance Criteria:**
- [~] 6 new items (`{l}_v6_ws_01..02`), `subtype = word_choice`, `explanation_variant = wrong_sense`, severity per the word_choice default, bands via `derive_bands(taxonomy_version=6)`. *Only 1 was added: `en_v6_ws_02` ("This is like a hand" → "This likes a hand"). It is `word_choice`/`wrong_sense`/**major**, not the default minor: the simile becomes an absurd claim, and the author conceded this to the reviewer. Bands are 4/4/3/4/4.*
- [x] Both lemmas exist in `dim_vocabulary` with ≥2 senses (so TASK-845's same-lemma check can fire), noted in the item `note`. *`like` = vocab 15338, with 4 distinct `sense_rank`s including "find pleasant" and "similar to". Count distinct `sense_rank`, not rows: every sense has a simple row and a standard row.*
- [x] zh/ja items added to the TASK-839/840 review sheets. *N/A: there are no zh/ja items, and the sheets do not exist yet.*

**Completion notes (2026-10-06):**
- *Process:* the author drafted 2 en items, and a blind opus reviewer labelled `blind.json` first. One exchange round followed. Records are in `data/eval/taxonomy_merge_2026-09-27/wrong_sense_2026-10-05/` (`draft.json`, `blind.json`, `reviewer.json`). Kept: `en_v6_ws_02`, agreed on type, variant and severity (author minor→major). Dropped: `en_v6_ws_01` pick up→pick, which the reviewer labelled `phrasal_verb`: "lift" is not one of pick's dictionary senses, and robotics usage ("pick-and-place") makes the item fragile.
- *Caveat (reviewer):* `like`/`likes` is a cross-POS homograph under one headword, not same-POS polysemy like 意思. It qualifies only under the "same `dim_vocabulary` headword" operationalization, which is also what TASK-845's resolver uses. It must not stay the only `wrong_sense` coverage, so ADR-031's OPEN item stays open in spirit.
- *zh, none:* zh has no inflection, so a same-lemma learner_form/corrected_form pair can only differ by function words. Those diffs are claimed by `aspect_negation`/`de_particle`/`complement`/`addition`. The one probe, 工作 (能够正常工作 → 能够有正常工作, where the "operate" sense flips to "job"), is a one-character insertion that Tier 0 swallows (`verify_item` reports it as fuzzy-identical).
- *ja, none:* only 20 of 3,439 ja lemmas have ≥2 distinct senses, and none occurs in dt_passage 20–28. Particle- or kanji-driven sense shifts are claimed by the particle types and `kanji_choice`.
- *Structural finding:* in a reference-anchored reproduction, a same-lemma diff is by construction a morphological or function-word diff, so narrow `wrong_sense` almost always competes with a grammar type. TASK-850 should read `wrong_sense` accuracy as n=1.
- *Build:* `scripts/build_dt_gold_v6.py` appends the specs in `data/eval/taxonomy_merge_2026-09-27/v6_only_gold_items.json` (`build_item` → v6 labels → `derive_bands(offline=True, taxonomy_version=6)` → `verify_item`) to the gold files only, after the 30 v5 ids. `not_added` in that file records the zh/ja/ws_01 reasons. v5 `tests/fixtures/dt_gold/` is untouched; `--check` is clean.
- *Tests:* the seed-helper tests now treat v5 ids as a prefix plus the v6-only ids, expect 178 errors, word_choice 29 = 20/1/8, skip v6-only items in the band-change comparison, and add `test_v6_only_wrong_sense_item`. `test_dual_translation_gold_seed_helper.py` + `test_dual_translation_taxonomy_v6.py`: 153 passed. `tests/ -k "dual_translation or dt_"`: 961 passed. DB reads only (sense counts); no writes.

**Technical Notes:**
If no natural same-lemma item can be built for an L2, record that and treat the variant as "grader judgement only" there.

**Files to Create / Modify:**
- `tests/fixtures/dt_gold_v6/{zh,ja,en}.json`, `scripts/build_dt_gold_v6.py`.

**Verification:**
Seed-helper test passes with the 6 items.

---

## TASK-849: Eval harness — taxonomy candidate + v6 fixtures + v6 metrics

**Status:** [x] Done (2026-10-04) — offline only; no model calls, no DB writes
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-841, TASK-847

**Description:**
Evaluate-before-activate for the taxonomy, mirroring `--rubric-file`.

**Acceptance Criteria:**
- [x] `run_dt_grading_eval.py --taxonomy-file migrations/dt_taxonomy_v6_seed.sql` parses the `$taxonomy$` literal and pre-seeds `gc._cfg_cache` taxonomy + version (live DB untouched); `--fixture-set {v5,v6,v6_silver}` picks the fixture dir (default v5).
- [x] Report adds: confusion of `meaning_inversion` vs `omission`/`word_choice`/`preposition`/`contradiction`; `meaning_inversion` recall/precision; `explanation_variant` accuracy on word_choice TPs + `variant_basis` distribution; count of exemplar-drop warnings (must be 0 for en/zh).
- [x] Offline test of fixture loading + candidate pre-seeding with a stubbed grader.

**Completion notes (2026-10-04):**
- *Offline v6 load:* `_load_candidate_taxonomy` parses the seed SQL (no DB), and `_preseed_candidate_taxonomy` seeds
  `_cfg_cache["taxonomy"]`, `["taxonomy@<v>"]` (the key the TASK-841 pin reads) and `["taxonomy_version"]`. A
  `DT_TAXONOMY_VERSION` pin naming a different version aborts the run. The v6 prompt gates (TASK-843/844) key on the
  resolved subtype list, so the pre-seed switches them on. The rubric is still the live DB row. No production code changed.
  Note that `DT_TAXONOMY_VERSION=6` on its own still needs the row in the DB, so use `--taxonomy-file` until TASK-853.
  The taxonomy file is parsed on dry runs too, so a broken seed fails before anything is spent.
- *Metrics:* pure functions in `eval_metrics` (`subtype_confusion`, `subtype_prf`, `explanation_variant_metrics`,
  `taxonomy_v6_metrics`) go into `metrics["v6"]`. `aggregate_metrics` and the QWK function are unchanged. MI
  recall/precision is end-to-end: a missed span counts as a miss and an unmatched MI prediction as a false alarm.
  Until TASK-845 ships, the grader emits no variant, so a missing predicted variant counts as wrong and is reported
  as `pred_missing`. `variant_basis` sums `grader_trace.variant_basis`.
- *Log counts:* `_LogCounter` is a logger filter. It counts prompts.py "dropping the … exemplar" warnings and
  grader_cascade "no explanation template" INFO lines, and suppresses the INFO lines so console output is unchanged.
  It only counts this invocation's grading, so resumed items are not counted.
- *Warnings:* the plan warns when the taxonomy and the fixture set disagree (e.g. v6 fixtures without `--taxonomy-file`).
- *Tests:* new `tests/test_dt_eval_harness_taxonomy.py` (stubbed perfect grader, v6 en run: F1/subtype/variant/MI recall all 1.0 and the
  report renders; dry-run main() with Supabase patched to raise) + 6 metric tests in `tests/test_dt_eval_metrics.py`.
  `test_dt_eval_metrics.py` + `test_dt_eval_harness_taxonomy.py` + `test_dt_eval_harness_retry.py`: 82 passed.

**Files to Create / Modify:**
- `scripts/run_dt_grading_eval.py`, `services/dual_translation/eval_metrics.py`, `tests/test_dt_eval_metrics.py`.

**Verification:**
Dry run (no `--live`) with `--taxonomy-file ... --fixture-set v6` prints the plan; `PYTHONPATH=. pytest tests/test_dt_eval_metrics.py`.

---

## TASK-850: Acceptance gate — v6 vs same-day v5 control

**Status:** [x] Done (2026-10-08): the gate ran and the verdict is **NO-GO**. A re-run is owed after the follow-ups
below, and TASK-853 stays blocked. See [[evaluations/dt-taxonomy-v6-gate-2026-10-08]].
**Re-run 2026-10-09 (after TASK-862 and the ADR-031 2026-10-09 rulings): BLOCKED, no results.** The OpenRouter account
is out of credit: $89.92 used of $90. Every model call returned 402 ("can only afford 31201 tokens"), so the harness
recorded 212 fell-open, zero-error grades. Those outputs are not a measurement. They are quarantined in
`data/eval/dt_v6_gate_2026-10-09/invalid_402_credit_exhausted/`; never pass them to `--resume`. Spend ≈ $0. The re-run
needs a credit top-up, then fresh checkpoints.
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** M (3-8h, mostly wall clock)
**Depends On:** TASK-843, TASK-844, TASK-846, TASK-849

**Description:**
Paid live run, all three L2s, `--framework-v2`: (a) v5 control — live taxonomy, `--fixture-set v5`; (b) v6
candidate — `--taxonomy-file` v6, `--fixture-set v6`; (c) v6 on `v6_silver` as supplementary evidence. Same day,
same rubric, same routing, so model drift since 2026-07-19 does not masquerade as a taxonomy effect.

**Acceptance Criteria (gate — all must hold per L2 for GO):**
- [~] Span F1 (v6) ≥ span F1 (v5 control) − 0.05. *EN .963 vs .923 ✅; ZH .826 vs .898 ❌ (min .848); JA .875 vs .880 ✅.*
- [ ] Subtype accuracy on v6 gold ≥ 0.80 and ≥ v5 control − 0.05. *EN .769 ❌; ZH .789 ❌; JA .810, below .814 by one item ❌.*
- [~] Overall-band QWK (v6) ≥ v5 control − 0.10. *EN .431 vs .695 ❌; ZH .615 vs .535 ✅; JA .839 vs .643 ✅.*
- [x] `meaning_inversion` recall ≥ 0.75 pooled over gold+silver (21 labels); clean-item FP not above control. *EN .90 (9/10), ZH 1.0 (7/7), JA 1.0 (6/6). The fixtures now carry 23 labels. Clean FP equals control in all three L2s.*
- [x] Probes reported: `en_seed_15` → meaning_inversion; `zh_seed_11`, `zh_multi_02`, `zh_silver_20`, `zh_silver_29` → de_particle/minor; the 3 `variant_uncertain` items' `resolve_variant` outcome. *All 5 probes ✅. Variant-uncertain: none reached the resolver at grade time. Offline, zh/ja bare lemmas → `wrong_word`/`default` (false_synonym refuted); en → the model's call.*
- [x] 0 "no explanation template" and 0 exemplar-drop warnings for en/zh under v6. *ja: 29/32 exemplar drops (the `particle_wa_ga` exemplar).*
- [x] Report `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` with the table vs [[evaluations/dt-grading-v2-2026-07-19]], cost, and a GO / NO-GO line.

**Completion notes (2026-10-08):**
- *Run:* 9 arms (3 L2 × v5 control / v6 gold / v6 silver), `--framework-v2`, live rubric v6, v6 taxonomy loaded offline,
  `DT_TAXONOMY_VERSION` unset. Artifacts are in `data/eval/dt_v6_gate_2026-10-08/`. 282 items, 0 skipped, 0 fell-open.
  Harness cost $2.20; the OpenRouter key delta was $3.21, an upper bound. ~2 h wall clock. No DB writes, no migrations,
  no code changes.
- *Main causes of NO-GO:*
  - **(1) The v6 gold contradicts the v6 glosses.** The 4 ja `keigo` labels are だ/です level, which the gloss
    assigns to `register`. The 4 zh `measure_word` 个 errors contradict the gloss's "个 is acceptable". en "it→them"
    is gold `word_choice` while the grader says `pronoun`.
  - **(2) A decode bug from before v6.** `_decode_error` drops an error whose `category` index is out of range;
    qwen copies the subtype index into it. This lost 2 zh B TPs, which alone flips the zh span gate, and 3 ja B TPs.
  - **(3)** The ja Detector exemplar is dropped under v6.
- *Follow-ups (need user decisions):* relabel or rule on (1) under TASK-847; a decode fallback for (2) as a new
  production task; the ja exemplar swap; then re-run all arms.

**Technical Notes:**
`--resume <path>` per L2. Set a spend cap first. NO-GO → follow-ups against 843/845 and re-run; never loosen thresholds in the report.

**Files to Create / Modify:**
- `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` — new.

**Verification:**
Report exists with all gate rows filled and a verdict.

---

## TASK-851: Remediation writers stamp taxonomy_version + legacy-slug guard

**Status:** [x] Done (2026-10-04) — gated on TASK-842's `Config.DT_TAXONOMY_COLUMNS` (default OFF: no new reads,
writes byte-identical). Version read failure → row/card written unstamped + WARNING (never NULL-overwrites).
"Pair lists" = union of every `pairs[*].subtypes` (per-pair and L2-baseline keys); records carry language ids,
not codes, so the check is per-taxonomy rather than per-pair. Unreadable taxonomy → guard skipped + WARNING.
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** S (1-3h)
**Depends On:** TASK-842

**Description:**
Shrunk 2026-10-04 (decision 3): after the cutover rewrite every row is in v6 names, so synthesis and cards need
no normalisation. They only need to stamp the version they write, and to shout if a non-active slug ever
reappears (which would mean the rewrite missed a table or an old process kept grading under v5).

**Acceptance Criteria:**
- [x] `dt_nightly_synthesis.upsert_profile_rows` sets `taxonomy_version` = `grader_cascade.get_active_taxonomy_version(db)` on every upserted row; `cards.generate_cards_for_queued_entries` sets it on every new `dt_card`.
- [x] `fetch_error_records`: any row whose `subtype` is not in the active taxonomy's pair lists is counted and logged at WARNING once per run with the slug list (still clustered as-is — no silent drop).
- [x] Under v5 active, behaviour is unchanged apart from the stamping (tests).

**Files to Create / Modify:**
- `scripts/dt_nightly_synthesis.py`, `services/dual_translation/cards.py`.
- `tests/test_dual_translation_synthesis.py`, `tests/test_dual_translation_cards.py`, `tests/test_dt_remediation_infrastructure.py`.

**Verification:**
`PYTHONPATH=. pytest tests/test_dual_translation_synthesis.py tests/test_dual_translation_cards.py tests/test_dt_remediation_infrastructure.py`.

---

## TASK-852: One-time rewrite of historical DT records to v6 (snapshot, aggregate, delete script_choice, restore)

**Status:** [x] Done (2026-10-05) — built + tested, NOT applied, never run against Supabase; inert until TASK-853 calls it

**Completion notes (2026-10-05):**
- **Design — the plan is the interface.** The pure Python planner (`plan_rewrite`) decides every row (v6 slug, flag,
  survivor, summed count, `synthesis.severity_rank`/`build_trend`, delete set) and passes it as `p_plan` jsonb to
  `dt_rewrite_history_v6(p_plan, p_dry_run DEFAULT true)`, which owns the transaction: locks the 4 tables (EXCLUSIVE),
  fails closed on non-empty snapshot / stale plan (any planned row's subtype, version or profile_entry_id changed) /
  target slug outside v6 / unmappable rows / a source column missing from its LIKE-frozen snapshot, snapshots, writes
  child-first, checks each statement's row count = plan, then the post-conditions (0 rows outside v6 slugs or with
  `taxonomy_version` ≠ 6, 0 dropped-slug rows, 0 card/entry subtype mismatch). Mapping is read from the seeded v6
  row's `legacy_aliases` + `pairs` (built from `v5_to_merged.csv`; `--offline-taxonomy` rebuilds from the CSV).
- **Modes:** `--dry-run` (default) SELECT-only report + `--plan-out`; `--rehearse` runs the real function with
  `p_dry_run=true` (rolled back via custom SQLSTATE `DTDRY`; allowed before activation); `--apply` (refused unless v6
  is active); `--restore [--confirm-drop-snapshot]` → `dt_restore_history_v5(p_confirm_drop_snapshot, p_dry_run)`.
- **Idempotency:** an empty plan returns `noop` after re-checking the post-conditions, without touching the snapshot,
  so a second run is a no-op; a non-empty plan with a non-empty snapshot is refused.
- **Deviations / decisions:** (1) every row not yet stamped v6 is touched — 1:1 same-slug rows are stamped 6 (needed
  for TASK-854's "taxonomy_version ≠ 6" check); (2) a merge that absorbs a split row gets `split_needs_review`, not
  `merged` (one CHECK value; the review flag wins); (3) `trend` is one `build_trend` dict per row, not a dated series,
  so the fallback sums `current_count`/`previous_count`, keeps the latest `as_of`, recomputes `delta_pct`;
  (4) in-window severity/trend gate `is_mistake` rows like the nightly does; (5) restore reverts only the columns the
  rewrite changed — a card's post-cutover FSRS progress and reviews survive a rollback; (6) the restore refuses if a
  rewritten error row was deleted after cutover (narrow snapshot cannot rebuild it); (7) the dropped set is generic
  (`legacy_aliases` with `to: null`), today only `script_choice`.
- **Tests:** `tests/test_dt_rewrite_history_v6.py` — 23 planner tests + 7 SQL tests on a disposable local PG 16
  (`pgserver` + `psycopg`, not repo deps — install to a scratch `--target` and put it on `PYTHONPATH`, else the 7 skip)
  built from the real migrations (groundwork, triad, profile, cards, v6 columns, v6 seed, this file). Verified:
  apply → post-conditions → re-plan empty → noop → restore byte-equal (`to_jsonb` of all 6 tables) → restore again →
  refused re-apply while snapshot present → restore+drop → re-apply; post-cutover rows/reviews/FSRS survive restore;
  dry-run byte-equal; inactive v6 refused; stale plan, unplanned review on a deleted card (FK), unplanned v5 row
  (post-condition) all roll back with the snapshot empty. 30 passed.
- **Only the apply can verify:** Supabase-side behaviour (PostgREST RPC with a jsonb arg, service_role grants,
  live column set vs the LIKE snapshots — the function checks the last one itself), and the
  `--dry-run`-against-live comparison with TASK-836 (not run: no DB access in this task).
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** L (1-2d)
**Depends On:** TASK-836, TASK-837, TASK-842

**Description:**
Build (and dry-run) the script that, inside the TASK-853 cutover window, snapshots then rewrites every
subtype-bearing record from v5 to v6 names via `legacy_aliases` / `v5_to_merged.csv`, aggregates profile rows
that collapse onto one v6 key, deletes everything on the dropped ja `script_choice`, and the restore that
undoes it all. Built here; executed only in TASK-853.

**Acceptance Criteria:**
- [x] `scripts/dt_rewrite_history_v6.py` with `--dry-run` (default; prints a per-table, per-kind plan) / `--apply` / `--restore`. All writes for one `--apply` run in a single transaction (one SQL function `dt_rewrite_history_v6()` in `migrations/dt_rewrite_history_v6.sql`, called via RPC, since PostgREST cannot do multi-statement transactions).
- [x] **Snapshot first** (same transaction, before any change), into the TASK-842 tables: every `dt_error_instance` row being rewritten (`id, subtype, taxonomy_version, remap_flag`); full rows of every `script_choice` error instance; full rows of every `dt_error_profile_entry`, `dt_card` and `dt_card_review` row that will be updated or deleted. Fails closed if the snapshot tables are non-empty (no double-snapshot).
- [x] **dt_error_instance**: 1:1/merge → v6 slug; split (`particle_wa_ga`, `particle`, `pronoun_reference`) → closest v6 type with `remap_flag = 'split_needs_review'`; all rewritten rows `taxonomy_version = 6`.
- [x] **dt_error_profile_entry**: same mapping + `taxonomy_version = 6`; split → `remap_flag = 'split_needs_review'`. **Merges** (several rows → one `(user, l1, l2, v6 slug)` key): keep the row with the most advanced `remediation_status` (drilling > queued > watching > resolved; tie → lowest id) as survivor; `count` = sum; `severity_rank` recomputed with `synthesis.severity_rank()` over the rewritten error instances of that user/pair/v6 slug inside the nightly window (`DT_SYNTHESIS_WINDOW_DAYS`), falling back to the max of the merged rows when none are in window; `trend` = rebuilt with `synthesis.build_trend()` over the same instances, falling back to the merged rows' trend entries combined by date (summed) when none are in window; `remap_flag = 'merged'`; non-survivors are deleted after their cards are repointed.
- [x] **dt_card**: `subtype` set to its (surviving) profile entry's v6 slug, `profile_entry_id` repointed from merged-away entries to the survivor, `taxonomy_version = 6`. Post-condition: 0 cards whose subtype ≠ their profile entry's subtype.
- [x] **ja `script_choice` deletion** (decision 4), child-first because every FK is NO ACTION: (1) delete `dt_card_review` rows whose card has `subtype = 'script_choice'` OR `profile_entry_id` → a script_choice entry OR `origin_error_id` → a script_choice error; (2) delete those `dt_card`s; (3) delete the script_choice `dt_error_profile_entry` rows; (4) delete the script_choice `dt_error_instance` rows. `dt_grade` and `dt_submission` are untouched — past bands are **not** recalculated.
- [x] Any other subtype-bearing column found by TASK-836 is rewritten the same way (or the skip is justified in the script header).
- [x] Post-conditions checked inside the function (raise → rollback): 0 rows in any covered table with a subtype outside the v6 pair lists; 0 `script_choice` rows anywhere; row counts equal the dry-run plan.
- [x] `--restore` (`dt_restore_history_v5()`): reinserts deleted rows from the full-row snapshots with `INSERT ... OVERRIDING SYSTEM VALUE` (identity columns are GENERATED ALWAYS) in parent-first order (error instances, profile entries, cards, reviews); restores updated rows' `subtype`/`profile_entry_id`/`count`/`severity_rank`/`trend`/`remediation_status`/`taxonomy_version`/`remap_flag` from the snapshot; leaves rows created after cutover untouched (see Technical Notes); then truncates the snapshot tables only when called with `--confirm-drop-snapshot`.
- [x] Unit tests on the pure planner (mapping, merge aggregation incl. status precedence, split flagging, delete set incl. reviews reached only through `origin_error_id`) with fixture rows; a local-Postgres integration test runs apply → restore and asserts the tables are byte-equal to the start.

**Technical Notes:**
Run only with the nightly cron paused (`dt_nightly_synthesis._try_advisory_lock` also guards it). Rows written
**after** cutover already carry v6 slugs and are not in the snapshot; after a rollback they keep v6 slugs that
v5 lacks (v5 scoring is grade-time only, so past grades are unaffected, but a later nightly would cluster them
under v6 keys). Flagged to the user: acceptable for a short rollback window; a long rollback would need a
reverse-map step for those rows (1:1 renames only — merges are not reversible).
Snapshot retention: kept until TASK-854 signs off, then dropped by a separate, operator-approved migration.

**Files to Create / Modify:**
- `scripts/dt_rewrite_history_v6.py`, `migrations/dt_rewrite_history_v6.sql` (apply + restore functions) — new.
- `tests/test_dt_rewrite_history_v6.py` — new.

**Verification:**
`PYTHONPATH=. pytest tests/test_dt_rewrite_history_v6.py`; `python scripts/dt_rewrite_history_v6.py --dry-run`
(against live, read-only) matches TASK-836's collision / split / script_choice counts.

---

## TASK-853: Cutover — activate v6 + rewrite history (runbook, activation/rollback SQL)

**Status:** [?] Blocked — needs (1) ADR-031 moved from `proposed` to `accepted` by the user, (2) TASK-850 GO, (3) operator approval to apply live
**Feature:** dt-taxonomy-v6
**Type:** infra
**Complexity:** S (1-3h)
**Depends On:** TASK-850, TASK-851, TASK-852

**Description:**
Flip the live grader to v6 and rewrite all historical records in one maintenance window, with a tested rollback
(revert taxonomy version + restore snapshot).

**Acceptance Criteria:**
- [ ] `migrations/dt_taxonomy_v6_activate.sql`: in one transaction deactivate every active row ≠ 6 and activate 6; footer verification (exactly one active row, version 6).
- [ ] `migrations/dt_taxonomy_v6_rollback.sql`: reactivate 5 (mirror), with a header pointing at `dt_rewrite_history_v6.py --restore`.
- [ ] Runbook, executed in order: apply `dt_taxonomy_v6_columns.sql` (if not already) → set `DT_TAXONOMY_COLUMNS=true` (TASK-842 gate; never before the columns exist) → deploy code (841–846, 851) → apply `dt_taxonomy_v6_seed.sql` (inactive) → pause nightly cron → `dt_taxonomy_v6_activate.sql` (+ optional rubric v7 exemplar re-slug, TASK-841 notes) → **immediately: restart ALL web workers** (every gunicorn/worker process; or call `grader_cascade.clear_caches()` in each) — the unpinned `taxonomy` / `taxonomy_version` entries in the process-wide `_cfg_cache` have no TTL, so a worker not restarted keeps grading AND stamping v5 indefinitely (`tests/test_dt_taxonomy_pin.py::test_activation_needs_clear_caches_before_v6_is_stamped`) → **verify with a single test grade** that its `grader_trace.prompt_version.taxonomy = 6` (and its errors carry `taxonomy_version = 6`); do NOT start the history rewrite until this passes → `dt_rewrite_history_v6.py --dry-run`, compare with TASK-836, then `--apply` (snapshot + rewrite + script_choice delete) → smoke: one graded submission per L2 shows `grader_trace.prompt_version.taxonomy = 6` and `taxonomy_version = 6` on its errors; 0 rows outside v6 slugs → resume cron.
- [ ] Rollback (rehearsed once on a local/staging DB before the live run): `dt_taxonomy_v6_rollback.sql` → restart → `dt_rewrite_history_v6.py --restore`. `DT_TAXONOMY_VERSION=5` + restart is a grading-only stopgap; it does not undo the rewrite.
- [ ] **Rollback scope, stated plainly:** `dt_restore_history_v5` restores **only the snapshot**. Rows graded under v6 after the cutover (new `dt_error_instance` / `dt_error_profile_entry` rows) keep their v6 names; profile progress since the cutover on snapshotted entries (`count` / `severity_rank` / `trend` / `remediation_status`) is **reset to the snapshot** (card FSRS progress and new reviews survive). So rollback is clean **only before new DT traffic**. After that the policy is **fix-forward**; re-pinning v5 (`DT_TAXONOMY_VERSION=5` + restart) is an emergency stop only. Restore refuses up front, changing nothing, if a v5 profile key `(user, l1, l2, subtype)` is now held by a post-cutover row (tests: `test_restore_after_v6_traffic_resets_profiles_keeps_new_rows`, `test_restore_refuses_when_v5_key_is_held_by_post_cutover_row`).
- [ ] ADR-031 → `accepted`; [[business-rules/translation-error-taxonomy]] updated to v6; harness default `--fixture-set` → v6 (v5 fixtures kept, frozen).

**Files to Create / Modify:**
- `migrations/dt_taxonomy_v6_activate.sql`, `migrations/dt_taxonomy_v6_rollback.sql` — new.
- `wiki/decisions/ADR-031-dt-taxonomy-v6-merge.md`, `wiki/business-rules/translation-error-taxonomy.md`.

**Verification:**
`select version from dt_taxonomy_version where is_active` → 6; post-conditions of TASK-852 hold; smoke submissions as above.

---

## TASK-854: Post-cutover verification (1 week) + snapshot retirement

**Status:** [ ] Not Started
**Feature:** dt-taxonomy-v6
**Type:** test
**Complexity:** S (1-3h)
**Depends On:** TASK-853

**Description:**
Confirm v6 behaves in production as in the gate, that the rewrite stuck, then retire the snapshot.

**Acceptance Criteria:**
- [ ] 0 rows in `dt_error_instance` / `dt_error_profile_entry` / `dt_card` with a subtype outside the v6 pair lists or with `taxonomy_version` ≠ 6; 0 `script_choice` rows; 0 TASK-851 legacy-slug warnings in the nightly logs.
- [ ] Every new `word_choice` row has a non-null `explanation_variant`; `variant_basis` distribution reported.
- [ ] Share of `meaning_inversion` and of critical severity per L2 reported vs gate rates.
- [ ] 0 log lines "no explanation template" / "no subtype_glosses entry" / exemplar-drop for en/zh.
- [ ] `remap_flag = 'split_needs_review'` rows listed for human triage (or 0); `merged` profile rows spot-checked (count = sum of snapshot counts).
- [ ] After sign-off: a separate operator-approved migration drops the `dt_v5_snapshot_*` tables (until then a snapshot restore stays *mechanically* possible — but it restores only the snapshot: post-cutover v6 rows keep v6 names and profile progress since cutover is reset, so once DT traffic has resumed the policy during this week is fix-forward, with a v5 re-pin only as an emergency stop; see TASK-853).
- [ ] Note appended to the TASK-850 evaluation page.

**Files to Create / Modify:**
- `wiki/evaluations/dt-taxonomy-v6-gate-<date>.md` — append; `migrations/dt_taxonomy_v6_drop_snapshots.sql` — new (applied only on sign-off).

**Verification:**
Read-only SQL recorded in the note.

---

## TASK-855: (Optional, later) jev bucket question flow for DT grading

**Status:** [?] Blocked — needs: jev porting of `plural_number` / zh+ja `topic_comment` finished (their `jev_bucket` is still `"pending"`), a new ADR deciding a jev-backed DT typer is wanted, and v6 live (TASK-853)
**Feature:** dt-taxonomy-v6
**Type:** feature
**Complexity:** XL (>2d)
**Depends On:** TASK-853

**Description:**
Prototype a cheaper error typer: per detected error span, ask jev bucket yes/no questions (B1–B9 from
`subtype_meta.jev_bucket`), then a type choice within the bucket, plus the residual wrong_sense-vs-wrong_word
yes/no from Decision A. Compare with the LLM Detector's subtype assignment on the v6 gold/silver. Start from
`data/eval/jev_dt_2026-09-26/` (`run.py`, `routing.py`, `decompose.py`, `taxonomy_data.py`, `score.py`), the jev
taxonomy `data/eval/jev_grammar_2026-09-26/taxonomy.md` + `taxonomy_addendum_2026-09-27.md`, client
`services/jev_client.py`.

**Acceptance Criteria:**
- [ ] Offline eval only: subtype accuracy + cost/latency vs the TASK-850 v6 numbers.
- [ ] Recommendation page under `wiki/evaluations/`; production wiring would be a new task set behind its own flag.

**Files to Create / Modify:**
- `data/eval/jev_dt_v6_<date>/` — new eval dir.

**Verification:**
Evaluation page with a go/no-go recommendation.

---

## TASK-862: `_decode_error` drops whole errors when `category` is an invalid index

**Status:** [x] Done 2026-10-09 (code + tests, local only; NOT deployed)
**Feature:** dt-taxonomy-v6
**Type:** bug
**Complexity:** S (1-3h)
**Depends On:** none (found by TASK-850; pre-dates v6)

**Description:**
`grader_cascade._decode_error` dropped the whole error when any enum index was out of range. qwen (the zh/ja
Detector) sometimes copies the subtype index into `category`, so real detections were discarded with an
"out-of-range enum index" WARNING. In the TASK-850 gate this cost zh A 1 / **zh B 2** / zh C 1 and ja A 1 /
**ja B 3** / ja C 1 errors; en 0. It hits live v5 grading as well as v6. Approved by the developer 2026-10-09.

Real dropped outputs (`data/eval/dt_v6_gate_2026-10-08/*.log`):
- zh A, `zh_multi_03` (v5): `{'span_repro': [44, 46], 'span_ref': [44, 46], 'category': 8, 'source': 1, 'severity': 1, 'subtype': 8, 'learner_form': '一个', 'corrected_form': '一只', ...}` (subtype 8 = `classifier`)
- zh B, `zh_multi_01` (v6): `{'span_repro': [68, 68], 'span_ref': [68, 69], 'category': 9, 'source': 0, 'severity': 0, 'subtype': 9, 'learner_form': '', 'corrected_form': '了', ...}` (subtype 9 = `aspect_negation`)
- ja B, `ja_seed_04` (v6): `{'span_repro': [118, 119], 'span_ref': [118, 120], 'category': 5, 'source': 0, 'severity': 0, 'subtype': 5, 'learner_form': 'だ', 'corrected_form': 'です', 'confidence': '0.95', 'is_mistake': True, 'explanation_variant': 0}` (subtype 5 = `register`)

**Acceptance Criteria:**
- [x] An invalid `category` (copied index, out of range, None, non-numeric) is derived from the decoded subtype
  and the error is kept; a WARNING `repaired invalid category <raw> -> <derived>` logs the raw value and the error.
- [x] An error whose subtype cannot be decoded is still dropped. Source/severity stay strict (out of scope).
- [x] A valid model `category` is never overridden.
- [x] Prompts unchanged (v5 prompt sha256 pins pass).

**Technical Notes:**
Neither taxonomy row stores a category, so `_derive_category(taxonomy_cfg, subtype)` uses, in order: an explicit
`subtype_meta[slug].category` (none today) → the v6 `class` letter (G→grammatical, S/F→lexical,
R/D→pragmatic_expressional; ADR-031) → a slug override for v5 slugs whose dimension misleads (`register`,
`keigo_register` → pragmatic_expressional; `collocation` → lexical) → `dimension` (accuracy→grammatical,
fidelity→lexical, naturalness→pragmatic_expressional) → `grammatical`. Category is stored on `dt_error_instance`
but is not graded or scored, so a heuristic value is safe.

**Live-behaviour change:** once deployed, live v5 grading keeps errors it previously dropped. More detected errors
can lower derived-scoring bands on affected submissions. The zh/ja gate arms should be re-run after deploy.

Not fixed here: ja B `ja_seed_07` (シンプルとても, invalid spans/forms) and ja C `ja_silver_32` are span drops,
a different cause. A kept empty-form error keeps the model's in-bounds span even when it is misplaced
(`ja_multi_03` ます at [109, 111]); this is existing `_reconcile_span_form` behaviour.

**Files to Create / Modify:**
- `services/dual_translation/grader_cascade.py` — `_decode_error` category repair; new `_derive_category`.
- `tests/test_dt_decode_category_repair.py` — 6 real gate drops (zh ×3, ja ×3, v5 and v6) kept with the right
  subtype/category, batch decode, valid-category passthrough, undecodable-subtype drop, derivation totality.

**Verification:**
`PYTHONPATH=. python -m pytest tests/test_dt_decode_category_repair.py` → 20 passed.
`PYTHONPATH=. python -m pytest tests/ -k "dual_translation or dt_"` → 1016 passed, 1 failed
(`test_v6_fixtures_are_fresh`: dt_gold_v6 en.json is being edited concurrently; unrelated to this change).

---
