---
title: "Exercise Generation Pipeline Audit (2026-06-07)"
type: feature-tech
status: complete
date: 2026-06-07
trigger: "小熊 (sense 34987) produced 0 exercises — 'Expected at least 2 morphological_forms'"
scope:
  - services/vocabulary_ladder/*
  - services/exercise_generation/judges/*
  - migrations/seed_chinese_vocab_prompts.sql
breaking_change_risk: medium
---

# Exercise Generation Pipeline Audit (2026-06-07)

Triggered by a live failure: generating exercises for **小熊** ("bear cub",
sense 34987, Chinese) rendered **0 exercises** with the single error
`Expected at least 2 morphological_forms`. This audit covers (Part A) the
root cause and latent bugs in the ladder generation pipeline, and (Part B)
the prompting infrastructure and prompt structure, with improvement options.

Related: [[algorithms/vocabulary-ladder.tech]], [[features/exercise-generation-prompts]],
[[features/exercises.tech]], [[reviews/code-review-2026-05-24]].

---

## Part A — Root cause & latent bugs

### A0. Root cause (the 小熊 failure)

A **language-blind validator contradicting its own prompt**. Chain:

1. [admin_local.py:1339](../../routes/admin_local.py#L1339) deletes all existing
   exercises for the sense, then runs the pipeline.
2. The Chinese P1 template returns a structurally correct asset for 小熊 (a
   concrete noun): `pos 名词`, valid IPA `[ɕiɑʊ˨˩˦ xjɑŋ˧˥]`, 10 sentences, and
   **one** morphological form `[{"form":"个","label":"量词"}]` (its measure word).
3. [validators.py:105-107](../../services/vocabulary_ladder/validators.py#L105-L107)
   hard-requires `len(morphological_forms) >= 2`. One form → **invalid**.
4. P1 stored with `is_valid=False`; pipeline returns early
   ([asset_pipeline.py:82-88](../../services/vocabulary_ladder/asset_pipeline.py#L82-L88));
   P2/P3 never run.
5. [exercise_renderer.py:44-46](../../services/vocabulary_ladder/exercise_renderer.py#L44-L46)
   finds no valid `prompt1_core` and aborts. `exercises_rendered: 0`.

**The contradiction:** Chinese P1 rule 18
([seed_chinese_vocab_prompts.sql:110](../../migrations/seed_chinese_vocab_prompts.sql#L110))
explicitly tells the model *"如目标词无相关形式，可返回空数组"* (return an empty
array if the word has no relevant forms). The prompt sanctions 0 forms; the
validator rejects anything under 2. The model did the right thing; the
validator killed it.

**Why it slipped through:** the Chinese seed migration's header
([seed_chinese_vocab_prompts.sql:19-23](../../migrations/seed_chinese_vocab_prompts.sql#L19-L23))
lists the validator changes it needs — Chinese POS allow-list, Chinese
semantic-class allow-list, non-ASCII `contains_target_whole_word` fallback —
and those were applied. But the `morphological_forms >= 2` and mandatory-IPA
gates were left English-centric. **Incomplete port.**

### A1. Latent bugs (ranked)

| ID | Sev | Bug | Location |
|----|-----|-----|----------|
| B1 | High | **Destructive regen.** Exercises are deleted *before* the pipeline runs, and `render_all` returns `[]` on any P1 invalidation — so a failed/stricter regen **wipes a previously-good word's exercises**. | [admin_local.py:1338-1339](../../routes/admin_local.py#L1338-L1339) |
| B2 | High | **`morphological_forms >= 2` is wrong for English too.** Invariant words (`sheep`, `deer`, `must`, `the`, `very`) have <2 forms → 0 exercises. The only consumer (L4) already skips cleanly when morphology is absent. | [validators.py:105-107](../../services/vocabulary_ladder/validators.py#L105-L107) |
| B3 | Med | **Mandatory IPA gate** — same English-centric assumption; passed for 小熊 only because the model volunteered IPA. Any omission hard-fails (and triggers B1). | [validators.py:110-111](../../services/vocabulary_ladder/validators.py#L110-L111) |
| B4 | Med | **Corpus extraction broken for non-English.** `self.db_language_id` doesn't exist → `hasattr` always False → hardcodes language 2 (English processor); `\b…\b` regex forms no boundaries between CJK chars. Chinese gets no corpus reuse. | [asset_pipeline.py:340](../../services/vocabulary_ladder/asset_pipeline.py#L340), [:353](../../services/vocabulary_ladder/asset_pipeline.py#L353) |
| B5 | Med | **L4 (Morphology Slot) stays active for concrete Chinese nouns.** `compute_active_levels` only drops L5/L8 for concrete nouns; L4 relies on the model returning `null` rather than config gating. | [config.py:208-216](../../services/vocabulary_ladder/config.py#L208-L216) |
| B6 | Low | **Single-shot P1, no retry/repair** (P2/P3 have retry + salvage; P1 does not). Given the all-or-nothing P1 gate, one bad sample = 0 exercises. | [prompt1_core.py:83-94](../../services/vocabulary_ladder/asset_generators/prompt1_core.py#L83-L94) |
| B7 | Low | **Opaque admin error.** "Expected at least 2 morphological_forms" gives an admin no signal that it's a language/validator mismatch vs. render-blocking. | [admin_local.py:1345-1346](../../routes/admin_local.py#L1345-L1346) |

### A2. Fixes

1. **Make validation language-aware** — drive per-field rules (min morph forms,
   IPA required y/n, POS set, semantic-class set) from a per-language config
   instead of one global set. Prevents the next incomplete port.
2. **Soften gates with graceful downstream handling** — `morphological_forms`
   and IPA should be *warnings recorded on the asset*, not blockers; L1/L4 skip
   cleanly when thin. Reserve hard-fail for genuinely render-breaking defects
   (no sentences, no definition, no valid POS).
3. **Non-destructive regen** — render into a list first; only delete-and-replace
   when the new render is non-empty. Optionally retain the prior valid asset
   when the new P1 fails rather than overwriting with `is_valid=False`.
4. **Fix `db_language_id`** ([asset_pipeline.py:340](../../services/vocabulary_ladder/asset_pipeline.py#L340))
   and use the language processor's tokenizer (not `\b`) for CJK corpus matching.
5. **Gate L4 in config** for non-inflecting languages / concrete nouns, the way
   L5/L8 are gated.
6. **Fixture test matrix** over the validators: invariant English noun (`sheep`),
   Chinese concrete noun (小熊), function word — each asserts validate + render ≥1.

**One-line unblock for 小熊's class:** lower/replace the `>= 2` morphological-forms
check (and reconsider the IPA gate) so empty/single `morphological_forms` is
acceptable — exactly what the Chinese prompt already promises the model.

---

## Part B — Prompting infrastructure & prompt structure

### B0. How it works today

- **Storage & pairing.** Prompts live in the `prompt_templates` table keyed by
  `(task_name, language_id, version, is_active)`.
  [get_template_config](../../services/prompt_service.py#L8) returns the
  template **paired with its model+provider** and raises (no silent fallback)
  if a row is missing — a good invariant ("a prompt can only ship with its
  intended model"). Per-language rows already exist (English + Chinese seed).
- **Numeric-key JSON contract.** Prompts emit numeric string keys (`"1"`, `"2"`,
  …) for language neutrality; Python remaps to descriptive keys
  ([config.py:395-447](../../services/vocabulary_ladder/config.py#L395-L447)).
- **Three monolith prompts, not per-exercise.** P1 = core asset; **P2 = one
  call for L1+L3+L5+L6**; **P3 = one call for L4+L7+L8**. Each emits all its
  active levels in a single response.
- **Resilience.** P2/P3 have retry-on-missing-level and P3 has a text-mode
  **salvage** path ([prompt3_transforms.py:258-297](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L258-L297))
  that peels off level keys independently when strict JSON breaks. P1 has none.

### B1. Judge coverage is highly asymmetric (the biggest gap)

Two pipelines, very different rigor:

- **Comprehension tests** run a real judge layer:
  `judge_answer_entailment` + `judge_distractor_plausibility`
  ([question_generator.py:446-505](../../services/test_generation/agents/question_generator.py#L446-L505)),
  both per-language and fail-open. (The distractor judge is the v3 5-pt Likert
  rebuild — see memory `distractor-judge-v3-likert`.)
- **Vocabulary ladder** judges **only L3 cloze**
  ([exercise_renderer.py:271-297](../../services/vocabulary_ladder/exercise_renderer.py#L271-L297)).
  **L1, L5, L6, L7, L8** distractors / wrong-sentences go straight from the
  generator LLM into stored exercises with only *structural* validation
  (counts, non-empty, exactly-one-correct). Nothing checks whether:
  - an L1 tone-confusion distractor is actually a real word and not a synonym;
  - an L5/L8 collocation distractor is genuinely non-collocating (vs. a second
    valid collocate — the L8 generator already had to add a post-hoc
    correctness retry because the model flips the correct label,
    [prompt3_transforms.py:124-139](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L124-L139));
  - an L6/L7 "wrong" sentence is wrong for the stated reason and not
    accidentally grammatical.

The single in-code quality signal we trust (cloze_judge) demonstrably moves
the needle, yet 5 of 6 LLM-authored ladder levels bypass it.

### B2. Prompt-structure observations

1. **Monolith prompts dilute per-exercise quality.** One P2 call juggles
   listening (L1), cloze (L3), collocation (L5), and semantic discrimination
   (L6) instructions; one P3 call juggles morphology, spot-incorrect, and
   collocation repair. The model's attention and the token budget (8192) are
   split, instruction-following degrades on the harder levels, and a single
   malformed array can force a retry/salvage of all of them. The L8 correctness
   bug and the P3 salvage path are symptoms of overloading one call.
2. **English-centric scaffolding leaks across the abstraction.** Beyond A0:
   `morphological_forms`, `ipa`, `syllable_count`, the whole-word `\b` regex in
   both the corpus extractor and the P3 `_whole_word_match`
   ([prompt3_transforms.py:29-33](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L29-L33))
   are inflection/alphabet assumptions. The Chinese prompt **reinterprets**
   levels (L1→listening, L4→compound-completion) but the Python contract around
   it still speaks English morphology.
3. **No schema/version validation of prompt output shape.** Remap code carries
   3–4 fallback shapes per level ("v2 puts options at sub-key 1; older shapes…",
   [prompt3_transforms.py:394-417](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L394-L417))
   — evidence the output contract drifts silently between prompt versions.
   There is no JSON-schema gate tying a `prompt_version` to an expected shape.
4. **Judge model/prompt is per-language and DB-driven** (good), but there's no
   judge for the *sentence corpus itself* — bad P1 sentences (off-register,
   wrong sense, target not whole-word) propagate into every downstream level,
   and P1 is exactly the prompt with no retry and no judge.

### B3. Improvement options (prompting)

Ranked by leverage:

1. **Extend the judge layer to every LLM-authored level.** Reuse the existing
   `judges/` package pattern (per-language `prompt_templates` row, fail-open,
   logged to `llm_calls`). Concretely:
   - L1: "is each distractor a real word, not a synonym, tone-confusable only?"
   - L5/L8: "is each distractor a genuine non-collocate in this sentence?"
     (would subsume the L8 correctness hack).
   - L6/L7: "is each 'wrong' sentence wrong *only* for the labeled reason?"
   - **P1 sentence judge:** sense-match + register + whole-word/whole-sense —
     the highest-leverage judge because every level inherits these sentences.
2. **Split monolith prompts toward per-exercise-type prompts.** At minimum
   peel the hardest/most-failure-prone levels (L4 morphology, L8 collocation
   repair) into their own `task_name` so they get a focused prompt, their own
   model choice, and isolated retry — without dragging L7/L3 down with them.
   Keeps the single-call latency win for the easy levels.
3. **Per-language exercise capability matrix.** A small config declaring, per
   `(language, level)`, whether the level is supported, what "form" means, and
   which validator profile applies. Drives A2.1/A2.5 and makes adding a new
   language a data task, not a code-archaeology task.
4. **Bind output shape to `prompt_version` with a JSON schema** per task, and
   validate before remap. Collapses the 3–4 speculative fallback branches into
   one gate and turns silent drift into a loud, versioned failure.
5. **Add P1 retry/repair** mirroring P2/P3 (it's the single point of total
   failure) — and consider a cheaper "repair" call that, given the validation
   errors, asks the model to fix only the offending fields.
6. **Judge-as-data feedback loop.** `exercises.tags.cloze_judge` already stores
   reject counts; extend that to all levels and surface a per-`(language, level,
   prompt_version)` reject-rate dashboard so prompt regressions are visible
   before learners see them (ties into the Part F per-question outcome data,
   see log 2026-06-06).

---

## Recommended sequencing

1. **Now (unblocks 小熊-class words):** A2.2 soften the morph/IPA gates →
   language-aware validator (A2.1). Ship with the A2.6 fixture matrix.
2. **Next (prevents data loss):** B1 non-destructive regen.
3. **Then (quality):** B3.1 judge for L5/L6/L7/L8 + the P1 sentence judge.
4. **Structural:** B3.3 capability matrix → B3.2 prompt split → B3.4 schema gate.

## Related Pages
- [[algorithms/vocabulary-ladder.tech]] — ladder levels, POS routing
- [[features/exercise-generation-prompts]] — verbatim P1/P2/P3 text
- [[features/exercises.tech]] — legacy generation pipeline (still canonical)
- [[reviews/code-review-2026-05-24]] — prior backend review
