---
title: "Ladder Prompt Numeric-Key Output Contract — Task Breakdown"
feature: exercise-generation-v2
prose_page: ../features/exercises.md
tech_page: ../features/exercises.tech.md
total_tasks: 4
done: 4
last_updated: 2026-08-11
---

# Ladder Prompt Numeric-Key Output Contract — Task Breakdown

All 16 ladder prompt rows (EN/ZH/JA) currently return JSON with **English field
names** (`options`, `is_correct`, `explanation`, `base_form`…). For the Chinese and
Japanese prompts those English keys sit inside the generation context and pull the
model toward English, degrading natural ZH/JA text. This breakdown replaces every
named key with a **numeric index whose meaning is declared in the prompt itself**,
so no English appears in the output contract of a ZH or JA prompt.

Three further requirements ride along: every prompt must carry at least one worked
example per rule that needs one; the JSON contract must be **provider-enforced**,
not merely parsed client-side; and the two ladder judges must agree on Likert
polarity.

---

## Established facts — read before starting

These were verified on 2026-08-10. Do not re-derive them; do not "fix" item 4.

1. **The numeric-key convention already exists in this codebase.** P1 uses it —
   see `services/vocabulary_ladder/asset_generators/prompt1_core.py:94` and
   `:368` ("Transform numeric-keyed LLM output to descriptive keys"). **Read that
   remap first and match its convention** rather than inventing a parallel one.
   Note that `schemas/ladder_l4_morphology.py`'s docstring currently argues
   *against* numeric keys for single-level prompts, on the grounds that named keys
   give better error messages. That reasoning is superseded — the ZH/JA
   contamination cost outweighs the error-message benefit. **Update that docstring**
   rather than leaving it contradicting the code.

2. **`prompt_version` stays at 1 — replace in place, do NOT bump to v2.**
   Verified by query: `word_assets` has **0 rows** with `asset_type LIKE 'llm_types%'`.
   The five new types have never generated a single asset, so no stored output is
   bound to the v1 shape. The only assets present are 16 legacy
   `prompt3_transforms_A/B` rows from the pre-split monolith, which these prompts do
   not touch. Bumping to v2 would leave permanently dead v1 schema code.
   Keep each module's `PROMPT_VERSIONS` as `frozenset({1})`.

3. **The 6 English rows are already LIVE and need `UPDATE`, not `INSERT`.**
   Applied 2026-08-10 to project `kpfqrjtfxmujzolwsvdq`. Every row in these
   migration files carries `ON CONFLICT (task_name, language_id, version) DO NOTHING`,
   so **re-running a corrected file is a silent no-op**. The live EN rows must be
   changed with an explicit `UPDATE ... SET template_text = ...`. The 10 zh/ja rows
   are not yet live and can still be plain `INSERT`s.

4. **The two judges are ALREADY polarity-aligned. There is no bug to fix here.**
   `judges/relation.py:45` and `judges/particle.py:36` import the same
   `likert_to_verdict` from `services.test_generation.schemas`, and both call it on
   the raw rating with no per-judge threshold (`relation.py:271`, `particle.py:174`).
   `particle.py:19-24` documents it: *"Polarity matches the other ladder judges"* —
   5 = ideal distractor, 1 = also-correct, drop. What differs between them is the
   **question asked** ("is this a non-relation?" vs "does this also yield a natural
   sentence?"), which is deliberate and type-specific. The only work item here is a
   regression test pinning the shared polarity so it cannot silently drift.

5. **Provider-enforced JSON is available and currently unused.** All seven ladder
   call sites pass `response_format='json'`, which is client-side parsing only.
   `call_llm` already supports `response_format='json_object'`, which sets
   `{'type': 'json_object'}` on the provider payload
   (`services/llm_service.py:445-446`), and an optional Pydantic `schema=` argument.

---

## The index scheme

Uniform rule: **`0` is always `options`; `9` is always the error escape.**

| Type | Top-level keys | Option-object keys |
|---|---|---|
| `morphology_slot` | 0=options, 1=base_form, 2=form_label, 3=sentence_index | 0=text, 1=is_correct, 2=explanation |
| `collocation_repair` | 0=options, 1=error_collocate | 0=text, 1=is_correct, 2=explanation |
| `synonym_antonym_match` | 0=options, 1=relation | 0=text, 1=is_correct, 2=explanation |
| `word_family` | 0=options, 1=stem | 0=text, 1=is_correct, 2=explanation, **3=part_of_speech** |
| `particle_selection` | 0=options, 1=blanked_particle, 2=error_tags | 0=text, 1=is_correct, 2=explanation |
| `ladder_relation_judge` | keyed by 1-based candidate index (unchanged) | 0=rating, 1=reason |
| `ladder_word_family_judge` | keyed by 1-based candidate index (unchanged) | 0=rating, 1=reason |
| `ladder_particle_judge` | keyed by 1-based candidate index (unchanged) | 0=rating, 1=reason |

Error escapes become `{"9": "no_inflection"}`, `{"9": "no_collocation"}`,
`{"9": "no_relation"}`, `{"9": "no_family"}`, `{"9": "no_particle_slot"}`.

The error **token values stay in English ASCII** — they are machine enum values
matched by code, never shown to a learner, and localising them would break the
generators' branch conditions.

Each prompt declares its own legend near the top, in the prompt's own language.
English shape (adapt per language):

```
Keys (the JSON you return uses these numeric keys, not names):
0: options — the four-option array
1: base_form — the dictionary headword
2: form_label — the grammatical name of the correct form
Within each option object:
0: text   1: is_correct   2: explanation
```

---

## TASK-537: Numeric-key schema layer

**Status:** [x] Done (2026-08-11)
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** none

**Description:**
Move the four schema modules from named-key reads to index reads, keeping
`PROMPT_VERSIONS = {1}`. The validators are the enforcement point for the new
contract, so they change first and everything else follows their shape.

**Acceptance Criteria:**
- [ ] `validate_options` reads `0`/`1`/`2` (and optional `3`) from each option object
- [ ] Error strings still name the offending position (`options[2]: missing "text" (key 0)`) — do not regress to `key '0' missing`, which was the original argument against numeric keys
- [ ] All four modules accept the indexed shape and reject the old named shape
- [ ] The error escape `{"9": "<token>"}` is recognised by every type
- [ ] `ladder_l4_morphology.py`'s docstring no longer argues against numeric keys
- [ ] Accept **string** keys (`"0"`) as well as int — JSON object keys deserialise as strings

**Files to Create / Modify:**
- `services/exercise_generation/schemas/_shared.py` — index-based option validation; add a shared key-legend constant
- `services/exercise_generation/schemas/ladder_l4_morphology.py` — indices + docstring correction
- `services/exercise_generation/schemas/ladder_l8_repair.py` — indices
- `services/exercise_generation/schemas/ladder_typed.py` — `_SynAnt`, `_WordFamily`, `_ParticleSelection`

**Verification:**
`PYTHONPATH=. python -m pytest tests/test_prompt_split_l4_l8.py tests/test_typed_llm_generators.py -q`

---

## TASK-538: Rewrite all 16 prompt bodies

**Status:** [x] Done (2026-08-11)
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** L (1-2d)
**Depends On:** TASK-537

**Description:**
Rewrite every ladder prompt body to declare its numeric-key legend and return the
indexed shape, and audit each for worked examples. The legend must be written in
the prompt's own language.

**The 16 rows, with current line anchors:**

| # | task_name | lang | file:line |
|---|---|---|---|
| 1 | `ladder_l4_morphology_generation` | en | `ladder_prompt_split_l4_l8.sql:70` |
| 2 | `ladder_l4_morphology_generation` | zh | `ladder_prompt_split_l4_l8.sql:129` |
| 3 | `ladder_l4_morphology_generation` | ja | `ladder_prompt_split_l4_l8.sql:180` |
| 4 | `ladder_l8_collocation_repair_generation` | en | `ladder_prompt_split_l4_l8.sql:231` |
| 5 | `ladder_l8_collocation_repair_generation` | zh | `ladder_prompt_split_l4_l8.sql:286` |
| 6 | `ladder_l8_collocation_repair_generation` | ja | `ladder_prompt_split_l4_l8.sql:340` |
| 7 | `ladder_syn_ant_generation` | en | `syn_ant_word_family_prompts.sql:66` |
| 8 | `ladder_syn_ant_generation` | zh | `syn_ant_word_family_prompts.sql:109` |
| 9 | `ladder_syn_ant_generation` | **ja** | `syn_ant_word_family_prompts.sql:152` |
| 10 | `ladder_word_family_generation` | en | `syn_ant_word_family_prompts.sql:198` |
| 11 | `ladder_relation_judge` | en | `syn_ant_word_family_prompts.sql:245` |
| 12 | `ladder_relation_judge` | zh | `syn_ant_word_family_prompts.sql:287` |
| 13 | `ladder_relation_judge` | ja | `syn_ant_word_family_prompts.sql:329` |
| 14 | `ladder_word_family_judge` | en | `syn_ant_word_family_prompts.sql:371` |
| 15 | `ladder_particle_selection_generation` | ja | `particle_selection_prompts.sql:66` |
| 16 | `ladder_particle_judge` | ja | `particle_selection_prompts.sql:117` |

**Acceptance Criteria:**
- [ ] Every prompt declares its key legend in its own language before the rules
- [ ] Every JSON example uses indices, including nested option objects
- [ ] **Row 9 (JA `syn_ant`) gains a worked example for the polysemy rule.** It is currently the only one of the three that states rule 3 abstractly — EN names bank/shore, ZH names 行(银行)/走, JA names nothing. This is the single most important rule in the prompt.
- [ ] Every other rule that asserts a distinction carries at least one concrete example; audit all 16 and add where missing
- [ ] Generation prompts keep **single** braces (`render_template`); judge prompts keep **doubled** braces (`str.format`). Rows 11, 12, 13, 14, 16 are judges.
- [ ] ZH/JA examples use ZH/JA lexical material, not translated English examples

**Technical Notes:**
Row 2 (ZH L4) is seeded but inert — the `('morphology_slot', lang 1)` capability
row is `is_enabled = FALSE`. Rewrite it anyway for consistency; it must not become
the one row left on the old contract.

**Files to Create / Modify:**
- `migrations/ladder_prompt_split_l4_l8.sql` — rows 1-6
- `migrations/syn_ant_word_family_prompts.sql` — rows 7-14
- `migrations/particle_selection_prompts.sql` — rows 15-16

---

## TASK-539: Generators + judges read indices; enforce JSON at the provider

**Status:** [x] Done (2026-08-11)
**Feature:** exercise-generation-v2
**Type:** refactor
**Complexity:** M (3-8h)
**Depends On:** TASK-537

**Description:**
Update every consumer of the rewritten prompts to read indices, and switch the
ladder call sites from client-side JSON parsing to provider-enforced JSON.

**Acceptance Criteria:**
- [ ] All six generators read the indexed shape; `options_to_content` in `_split_base.py` maps indices back to the descriptive keys the renderer expects
- [ ] Both relation/word-family judges and the particle judge read `0`=rating, `1`=reason
- [ ] Seven call sites move from `response_format='json'` to `response_format='json_object'`
- [ ] The downstream renderer/validator contract is unchanged — the indexed shape is an LLM-boundary concern only and must not leak into `word_assets` content
- [ ] A regression test pins the shared judge polarity (see fact 4): same rating in → same verdict out for both judges

**Files to Create / Modify:**
- `services/vocabulary_ladder/asset_generators/_split_base.py` — index remap + `json_object`
- `services/vocabulary_ladder/asset_generators/l4_morphology.py`
- `services/vocabulary_ladder/asset_generators/l8_repair.py`
- `services/vocabulary_ladder/asset_generators/syn_ant.py`
- `services/vocabulary_ladder/asset_generators/word_family.py`
- `services/vocabulary_ladder/asset_generators/particle_selection.py`
- `services/exercise_generation/judges/relation.py`
- `services/exercise_generation/judges/particle.py`

---

## TASK-540: Tests green + apply to the live DB

**Status:** [x] Done (2026-08-11)
**Feature:** exercise-generation-v2
**Type:** test
**Complexity:** M (3-8h)
**Depends On:** TASK-537, TASK-538, TASK-539

**Description:**
Update the ~57 tests that assert the named-key shape, then apply the rewritten
prompts to Supabase — `UPDATE` for the 6 live EN rows, `INSERT` for the 10 zh/ja.

**Acceptance Criteria:**
- [ ] Full suite green (baseline before this work: **1609 passed, 3 skipped**)
- [ ] A test asserts the old named-key shape is now *rejected*, so a half-migrated prompt fails loudly
- [ ] 6 EN rows `UPDATE`d in place — verify `template_text` actually changed, since `ON CONFLICT DO NOTHING` will silently no-op an `INSERT`
- [ ] 10 zh/ja rows present and `is_active = true`
- [ ] Step 7 of `ladder_prompt_split_l4_l8.sql` (the description annotation on the surviving `vocab_prompt3_transforms` rows) applied — it was held back on 2026-08-10

**Files to Create / Modify:**
- `tests/test_prompt_split_l4_l8.py` (31 tests)
- `tests/test_typed_llm_generators.py` (26 tests)

**Verification:**

`task_name LIKE 'ladder_%'` is too broad — it also matches 12 rows outside this
work (`ladder_collocation_judge`, `ladder_p1_sentence_judge`,
`ladder_sentence_validity_judge`, `ladder_l1_distractor_judge` × 3 languages),
which are owned by other tasks and were deliberately left on their existing
contract. Scope by the eight task_names instead, or the count reads 28.

```sql
SELECT task_name, language_id, version, is_active,
       (template_text LIKE '%Keys (%' OR template_text LIKE '%键（%'
        OR template_text LIKE '%キー（%') AS has_legend,
       (template_text LIKE '%"options"%' OR template_text LIKE '%"rating"%'
        OR template_text LIKE '%"is_correct"%') AS old_contract
FROM public.prompt_templates
WHERE task_name IN (
    'ladder_l4_morphology_generation','ladder_l8_collocation_repair_generation',
    'ladder_syn_ant_generation','ladder_word_family_generation',
    'ladder_relation_judge','ladder_word_family_judge',
    'ladder_particle_selection_generation','ladder_particle_judge')
ORDER BY task_name, language_id;
-- expect 16 rows: has_legend true and old_contract false on all
```

**Applied 2026-08-11** to project `kpfqrjtfxmujzolwsvdq`. All 16 rows verified
`is_active`, legend present, old contract absent; each row's `md5(template_text)`
was compared against the `$PROMPT$` body in its migration file and all 16 match,
so the live text is byte-identical to the repo. Step 7 landed on the three active
`vocab_prompt3_transforms` rows (the one inactive lang-2 row is untouched, as its
`WHERE is_active = true` intends). Suite: **1634 passed, 3 skipped** (baseline
1609/3 plus 25 new tests).

---

## Out of scope

- Bumping `prompt_version` to 2 (see fact 2)
- Any change to judge Likert polarity (see fact 4)
- Running the TASK-515 generation batch — still operator-gated on spend
