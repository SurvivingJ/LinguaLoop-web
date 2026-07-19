---
title: "Ladder Judge Layer (Phase 4) — Task Breakdown"
feature: ladder-judge-layer
prose_page: ../reviews/exercise-generation-audit-2026-06-07.md
tech_page: ../reviews/exercise-generation-audit-2026-06-07.md
total_tasks: 16
done: 16
---

# Ladder Judge Layer (Phase 4) — Task Breakdown

Implements **B3.1** (extend the judge layer to every LLM-authored ladder level)
and **B3.6** (judge-as-data feedback loop) from the
[[reviews/exercise-generation-audit-2026-06-07]] audit. The audit is the
governing spec — there is no separate feature/tech page; this breakdown plus
the audit's Part B is the contract.

**Problem (audit B1).** Comprehension tests run two judges
([question_generator.py:446-505](../../services/test_generation/agents/question_generator.py#L446-L505));
the vocabulary ladder judges **only L3 cloze**
([exercise_renderer.py:276-342](../../services/vocabulary_ladder/exercise_renderer.py#L276-L342)).
L1, L5, L6, L7, L8 ship with structural validation only, and P1's 10 sentences
— which every downstream level inherits — have no judge at all.

**Coverage delivered by this phase:** English (`language_id=2`) **and** Chinese
(`language_id=1`) prompt rows for every new judge, mirroring the existing
P1/P2/P3 + `cloze_distractor_judge` per-language coverage.

---

## Architecture decisions (read before any task)

These bind the whole phase. Changing one of them changes several tasks.

1. **Reuse the existing `judges/` package and contract.** Every new judge lives
   in `services/exercise_generation/judges/`, loads its prompt+model via
   [get_template_config](../../services/prompt_service.py#L8) (per-language row,
   no silent fallback), calls `services.llm_service.call_llm` with
   `pipeline='vocab_ladder'`, logs to `llm_calls`, and is **fail-open**: any
   error (template missing, LLM failure, malformed response) behaves as if the
   judge were absent. This is the [base.py](../../services/exercise_generation/judges/base.py)
   `safe_accept` / [cloze.py](../../services/exercise_generation/judges/cloze.py)
   `_all_keep` contract — do not invent a new failure mode.

2. **Two judge shapes, picked by what the level drops.**
   - **Filter shape** (like [cloze.py](../../services/exercise_generation/judges/cloze.py)
     `filter_distractors → (kept, judge_meta)`): used where the level has a list
     of distractors and we drop the bad ones — **L1**, **L5**. Polarity is the
     cloze polarity: *reject a distractor that could itself be a correct answer*
     (a real collocate, a synonym, an also-acceptable option); *keep* genuine
     wrong options. Skip the variant (return `None`) if fewer than 3 survive,
     exactly like the L3 path at [exercise_renderer.py:320-325](../../services/vocabulary_ladder/exercise_renderer.py#L320-L325).
   - **Verdict shape** (like [distractor_plausibility.py](../../services/exercise_generation/judges/distractor_plausibility.py)
     → `JudgeOutcome`): used where the level has a single crafted-wrong artifact
     to validate, not a distractor list — **L8** (one `error_collocate`), **L7**
     (one `incorrect_sentence`), **L6** (three `wrong_sentences`, judged per
     sentence), and **P1** (ten corpus sentences, judged per sentence). `reject`
     → drop that artifact/sentence; `flag` → keep + record for review;
     `accept` → pass through.

3. **One `collocation` judge, two call sites.** The same prompt — "is CANDIDATE a
   genuine non-collocate of TARGET in this sentence, or could it pass as a valid
   collocate?" — drives both L5 (filter over 3 distractors: reject also-valid
   collocates) and L8 (verdict over the single `error_collocate`: the error word
   must be judged a genuine non-collocate, else the exercise is wrong). This is
   the semantic replacement for the brittle `_l8_correctness_ok` string-match
   retry at [prompt3_transforms.py:124-139](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L124-L139).

4. **P1 sentence judge must preserve sentence indices.** Sentence positions are
   referenced positionally everywhere — `SENTENCE_ASSIGNMENTS_A/B`,
   `L7_CORRECT_INDICES_A/B` ([config.py:481-504](../../services/vocabulary_ladder/config.py#L481-L504)).
   Physically removing a flagged sentence renumbers the pool and silently
   repoints every level. Therefore the P1 judge **never deletes a sentence
   in place**. It (a) judges all sentences, (b) attempts one targeted P1 repair
   of only the rejected indices, (c) re-judges, (d) persists per-sentence
   verdicts as a `validation_warnings` sidecar on the `prompt1_core` asset, and
   (e) blocks the asset (`is_valid=False`) only if fewer than
   `P1_MIN_ACCEPTABLE_SENTENCES` (default 6) survive. Indices stay stable;
   downstream renderers already skip a level when its assigned sentence is thin.

5. **Tag schema for observability (4.3).** Generalize the existing
   `tags.cloze_judge` sidecar. Each judged renderer writes
   `tags['<judge>_judge'] = {rejected, kept, model, version, rejected_items}`
   under a per-judge key (`cloze_judge`, `l1_distractor_judge`,
   `collocation_judge`, `sentence_validity_judge`). The existing `cloze_judge`
   key and its consumers are unchanged. The reject-rate view (TASK-414) reads
   these keys from `exercises.tags` joined to `word_assets.prompt_version`.

6. **L1 distractor polarity is audio-confusability, not spelling.** Per project
   memory [[l1-is-listening]]: L1 distractors must be audio-confusable and never
   merely visually similar, in **every** language. The L1 judge must REJECT a
   distractor that is (a) not a real word, (b) a synonym of the target, or
   (c) selected on spelling similarity with no phonetic confusability
   (e.g. en `tough`/`though`; zh visually-similar but tonally-distinct chars).
   It KEEPs only real, non-synonymous, genuinely mishearable options.

7. **Judge confidence is a 5-point Likert rating, never a raw 0.0-1.0 float.**
   Every judge prompt that reports a strength/confidence emits an integer
   `rating` 1-5 per item, mapped to a verdict by
   [likert_to_verdict](../../services/test_generation/schemas.py#L50)
   (5/4 → accept, 3 → flag, 2/1 → reject) — the same cut points the v3
   distractor judge uses (project memory [[distractor-judge-v3-likert]]), which
   roughly halved good-item false-rejects and keeps the cut points tunable
   without re-prompting. The raw rating is carried through unchanged as
   `JudgeOutcome.confidence`. A purely binary filter judge (L1: keep/reject) may
   stay binary, but any judge expressing *how strongly* — P1
   (`ladder_p1_sentence_judge`), collocation (`ladder_collocation_judge`), and
   sentence-validity (`ladder_sentence_validity_judge`) — uses the Likert. For
   the collocation judge specifically, `rating` measures how clearly the
   candidate is a genuine **non-collocate** (5 = obviously unnatural with the
   target → ideal distractor / valid L8 error word; 1 = a fully idiomatic,
   also-correct collocate → drop as an L5 distractor, reject as an L8 error
   word).

---

## TASK-401: Generalize the renderer judge-meta tag sidecar

**Status:** [x] Done (2026-06-07)
**Type:** refactor
**Complexity:** S
**Depends On:** none

**Description:**
Today `_render_cloze` returns a single `__judge_meta` sidecar that
`build_rows` lifts into `tags['cloze_judge']`
([exercise_renderer.py:118-128](../../services/vocabulary_ladder/exercise_renderer.py#L118-L128)).
Generalize this so any renderer can attach one or more named judge metas.
Replace the single `__judge_meta` convention with `__judge_metas: {judge_key:
meta_dict}` (keep reading the legacy `__judge_meta` for the cloze path during
the transition, mapping it to `cloze_judge`). `build_rows` merges every entry
of `__judge_metas` into `tags` under its key. No behavior change for L3.

**Acceptance Criteria:**
- [ ] `build_rows` lifts an arbitrary set of judge metas into `tags`, each under
      its own `<judge>_judge` key.
- [ ] L3 output is byte-identical: `tags.cloze_judge` shape unchanged.
- [ ] A renderer attaching `__judge_metas={'l1_distractor': {...}}` produces
      `tags.l1_distractor_judge == {...}`.

**Files:**
- `services/vocabulary_ladder/exercise_renderer.py` — `build_rows` lift logic.

**Verification:** `pytest tests/test_vocab_ladder_renderer.py -k judge_meta` (add a
case); existing L3 render test still green.

---

## TASK-402: P1 sentence judge module (`ladder_p1_sentence_judge`)

**Status:** [x] Done (2026-06-07)
**Type:** feature
**Complexity:** M
**Depends On:** none

**Description:**
New `services/exercise_generation/judges/p1_sentences.py`. Verdict shape
(decision 2). Public API:
`judge_p1_sentences(db, lemma, definition, sense_fingerprint, register,
sentences, language_id) -> list[JudgeOutcome]` — one outcome per sentence, in
order. The judge asks, per sentence: **sense-match** (does the target carry the
intended sense/`sense_fingerprint`, not a homonym?), **register** (does the
sentence's formality match the declared `register`?), and **whole-word /
whole-sense** (is the target a discrete whole word doing the sense's job, not a
substring or a different sense?). Fail-open to `[safe_accept() for _ in
sentences]`. Per-language cfg cache like the other judges.

**Acceptance Criteria:**
- [ ] Returns exactly `len(sentences)` outcomes, order-aligned.
- [ ] Length-mismatch and non-dict responses → safe-accept all (mirror
      [distractor_plausibility.py:157-171](../../services/exercise_generation/judges/distractor_plausibility.py#L157-L171)).
- [ ] Missing template / LLM error → safe-accept all, warning logged.
- [ ] Unit tests: clean sentence → accept; wrong-sense homonym → reject;
      off-register → flag/reject; fail-open paths.

**Files:**
- `services/exercise_generation/judges/p1_sentences.py` — new.
- `tests/test_vocab_ladder_judges.py` — new, P1 section.

**Verification:** `pytest tests/test_vocab_ladder_judges.py -k p1` green.

---

## TASK-403: Seed `ladder_p1_sentence_judge` prompts (en + zh) · Opus high

**Status:** [x] Done (2026-06-07)
**Type:** infra
**Complexity:** M
**Depends On:** TASK-402
**Note:** Prompt authoring is the high-leverage work of this phase — author with
Opus high. Wiring is mechanical; the prompt quality is what moves reject rates.

**Description:**
Add `prompt_templates` rows for `ladder_p1_sentence_judge`, `language_id` 2
(English) and 1 (Chinese), into `migrations/seed_ladder_judge_prompts.sql`.
Each prompt: input placeholders for lemma, definition, sense fingerprint,
declared register, and the numbered sentence list; output is per-sentence JSON
(`{"1": {"rating": 1-5, "reason": "..."}, ...}` or verdict+confidence — match
whatever schema TASK-402's parser consumes, and document the schema in the
migration header). The English prompt reasons over IPA-irrelevant sense/register;
the Chinese prompt must handle 义项 (sense) match and 语域 (register) and the
whole-**character**-sense rule (target character still bears the locked sense,
not a homograph), consistent with the Chinese P1 rule set.

**Acceptance Criteria:**
- [ ] Two rows inserted (lang 2 + lang 1), each with model+provider populated
      (follow the per-language model choice used by the existing ladder prompts;
      see "Model choices" note below).
- [ ] `$PROMPT$`-quoted; `ON CONFLICT (task_name, language_id, version) DO
      NOTHING`; wrapped in `BEGIN; … COMMIT;` like
      [cloze_distractor_quality.sql](../../migrations/cloze_distractor_quality.sql).
- [ ] Output schema in the prompt exactly matches the parser in TASK-402.
- [ ] Migration header documents the output schema and the model rationale.

**Files:**
- `migrations/seed_ladder_judge_prompts.sql` — new (this is the first of four
  judge task_names that land in this one file; later seed tasks append to it).

**Verification:** Apply migration to a scratch DB;
`SELECT task_name, language_id, version, model FROM prompt_templates WHERE
task_name='ladder_p1_sentence_judge';` returns two active rows.

---

## TASK-404: Wire the P1 sentence judge into `asset_pipeline`

**Status:** [x] Done (2026-06-07)
**Type:** feature
**Complexity:** M
**Depends On:** TASK-402, TASK-403

**Description:**
Run `judge_p1_sentences` in `VocabAssetPipeline.generate_for_sense` **after** P1
structural validation succeeds and **before** the variant fan-out
([asset_pipeline.py:107-129](../../services/vocabulary_ladder/asset_pipeline.py#L107-L129)).
Per decision 4: collect rejected sentence indices; attempt **one** targeted P1
repair of only those sentences via the existing `p1_gen.repair` path
(extend it to accept a sentence-index subset, or regenerate + splice by index —
keeping all other indices fixed); re-judge the repaired sentences; persist the
final per-sentence verdicts into the `prompt1_core` asset's
`validation_warnings` (the `phase15_word_assets_validation_warnings.sql` column
already exists). Block the asset (`is_valid=False`, return early like the P1
validation failure path) only if surviving acceptable sentences <
`P1_MIN_ACCEPTABLE_SENTENCES` (new constant in
[config.py](../../services/vocabulary_ladder/config.py), default 6). Never delete
or reorder sentences.

**Acceptance Criteria:**
- [ ] Judge runs once per sense after P1 validation; failures fail-open (asset
      stored, no block).
- [ ] Sentence count and indices are identical pre/post judge (assert in test).
- [ ] Rejected sentences trigger at most one targeted repair attempt.
- [ ] Per-sentence verdicts land in `word_assets.validation_warnings`.
- [ ] Asset blocked only when acceptable sentences < `P1_MIN_ACCEPTABLE_SENTENCES`.
- [ ] `result['warnings']` surfaces the judge summary to the admin caller.

**Files:**
- `services/vocabulary_ladder/asset_pipeline.py` — judge call + repair + warning persistence.
- `services/vocabulary_ladder/asset_generators/prompt1_core.py` — subset-aware repair (if taken).
- `services/vocabulary_ladder/config.py` — `P1_MIN_ACCEPTABLE_SENTENCES`.
- `tests/test_vocab_ladder_judges.py` — index-stability + block-threshold cases.

**Verification:** Generate assets for a seeded sense with one off-sense sentence;
confirm the asset retains 10 indices, the bad index carries a warning, and a
sense with ≥5 bad sentences is blocked.

---

## TASK-405: L1 distractor judge module (`ladder_l1_distractor_judge`)

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** S
**Depends On:** TASK-401

**Description:**
New `services/exercise_generation/judges/l1_distractor.py`. Filter shape
(decision 2), polarity per decision 6. Public API mirrors
[cloze.py](../../services/exercise_generation/judges/cloze.py):
`filter_l1_distractors(db, target, distractors, language_id) -> (kept,
judge_meta)`. Reject any distractor that is not a real word, is a synonym of the
target, or is only visually similar without audio-confusability. `judge_meta`
shape matches the generalized sidecar (decision 5). Fail-open to keep-all.

**Acceptance Criteria:**
- [ ] Keep/reject per distractor; returns `(kept, meta)`.
- [ ] `meta` carries `rejected`, `rejected_items`, `model`, `version`.
- [ ] Fail-open paths keep all distractors.
- [ ] Unit tests assert the three reject reasons and the audio-confusable keep.

**Files:**
- `services/exercise_generation/judges/l1_distractor.py` — new.
- `tests/test_vocab_ladder_judges.py` — L1 section.

**Verification:** `pytest tests/test_vocab_ladder_judges.py -k l1` green.

---

## TASK-406: Seed `ladder_l1_distractor_judge` prompts (en + zh) · Opus high

**Status:** [x] Done (2026-06-08)
**Type:** infra
**Complexity:** S
**Depends On:** TASK-405

**Description:**
Append en + zh rows for `ladder_l1_distractor_judge` to
`migrations/seed_ladder_judge_prompts.sql`. The English prompt encodes
homophone / minimal-pair / mishearable-rhyme acceptance and the spelling-only +
synonym + non-word rejects. The Chinese prompt encodes **声调混淆** (tone
confusability) acceptance and rejects pure homographs, synonyms, and
visually-similar-but-tonally-distinct chars — consistent with the Chinese P2 L1
block in [cloze_distractor_quality.sql:147-155](../../migrations/cloze_distractor_quality.sql#L147-L155)
and memory [[l1-is-listening]].

**Acceptance Criteria:**
- [ ] Two active rows (lang 2 + lang 1); model+provider populated.
- [ ] Output schema matches TASK-405's parser.
- [ ] Polarity examples present in both prompts (≥1 keep, ≥1 reject each).

**Files:** `migrations/seed_ladder_judge_prompts.sql` — append.

**Verification:** scratch-DB select returns two active `ladder_l1_distractor_judge` rows.

---

## TASK-407: Wire the L1 judge into `_render_phonetic`

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** S
**Depends On:** TASK-405, TASK-406

**Description:**
In `_render_phonetic` ([exercise_renderer.py:179-215](../../services/vocabulary_ladder/exercise_renderer.py#L179-L215)),
run `filter_l1_distractors` over the 3 option distractors before building the
MCQ. If fewer than 3 survive, return `None` (skip the variant), matching the L3
contract. Attach `__judge_metas['l1_distractor']`. Drop rejected distractors'
`distractor_explanations` entries.

**Acceptance Criteria:**
- [ ] `<3` survivors → variant skipped (`None`), logged like L3.
- [ ] Surviving options shuffled into the MCQ; correct answer preserved.
- [ ] `tags.l1_distractor_judge` populated on the rendered row.

**Files:** `services/vocabulary_ladder/exercise_renderer.py` — `_render_phonetic`.

**Verification:** Render L1 for a sense whose options include a synonym distractor;
confirm the synonym is dropped and the meta records it.

---

## TASK-408: Collocation judge module (`ladder_collocation_judge`)

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** M
**Depends On:** TASK-401

**Description:**
New `services/exercise_generation/judges/collocation.py`. One prompt, two entry
points (decision 3):
- `filter_collocation_distractors(db, sentence, target, correct_collocate,
  distractors, language_id) -> (kept, judge_meta)` — filter shape for **L5**;
  reject distractors that are themselves valid collocates of the target in this
  sentence.
- `judge_collocation_repair(db, sentence, target, correct_collocate,
  error_collocate, language_id) -> JudgeOutcome` — verdict shape for **L8**;
  `accept` only when `error_collocate` is a genuine non-collocate (clearly
  wrong) AND `correct_collocate` is the valid one. Fail-open both paths.

**Acceptance Criteria:**
- [ ] Both functions implemented over a shared `_load_cfg`/prompt.
- [ ] L5 filter rejects an also-valid collocate; keeps a genuine non-collocate.
- [ ] L8 verdict rejects an `error_collocate` that actually collocates (the
      failure the `_l8_correctness_ok` hack was patching).
- [ ] Fail-open: errors → keep-all (L5) / safe_accept (L8).

**Files:**
- `services/exercise_generation/judges/collocation.py` — new.
- `tests/test_vocab_ladder_judges.py` — collocation section.

**Verification:** `pytest tests/test_vocab_ladder_judges.py -k collocation` green.

---

## TASK-409: Seed `ladder_collocation_judge` prompts (en + zh) · Opus high

**Status:** [x] Done (2026-06-08)
**Type:** infra
**Complexity:** S
**Depends On:** TASK-408

**Description:**
Append en + zh rows for `ladder_collocation_judge` to
`migrations/seed_ladder_judge_prompts.sql`. The prompt must answer, for a
CANDIDATE word in a sentence with TARGET: "is CANDIDATE a genuine non-collocate
(clearly unnatural with TARGET here), or could it pass as a valid collocate?" —
the single question both call sites consume. Chinese prompt handles 搭配 fixity
and measure-word/aspect interactions.

**Acceptance Criteria:**
- [ ] Two active rows (lang 2 + lang 1); model+provider populated.
- [ ] Output schema serves both `filter_*` (per-candidate verdict) and
      `judge_collocation_repair` (single-candidate verdict) parsers.

**Files:** `migrations/seed_ladder_judge_prompts.sql` — append.

**Verification:** scratch-DB select returns two active `ladder_collocation_judge` rows.

---

## TASK-410: Wire collocation judge into L5/L8; retire the L8 string-match hack

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** M
**Depends On:** TASK-408, TASK-409

**Description:**
L5: in `_render_collocation_gap` ([exercise_renderer.py:392-431](../../services/vocabulary_ladder/exercise_renderer.py#L392-L431))
run `filter_collocation_distractors`; `<3` survivors → skip variant; attach
`__judge_metas['collocation']`. L8: in `_render_collocation_repair`
([exercise_renderer.py:510-543](../../services/vocabulary_ladder/exercise_renderer.py#L510-L543))
run `judge_collocation_repair`; on `reject` return `None`; attach the verdict to
`__judge_metas['collocation']`. Then **remove** the post-parse
`_l8_correctness_ok` retry/drop block in
[prompt3_transforms.py:124-139](../../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L124-L139)
(decision 3 supersedes it) — keep the cheaper pre-LLM `_can_generate_l8`
whole-word gate, which is structural, not semantic.

**Acceptance Criteria:**
- [ ] L5 drops also-valid-collocate distractors; skips when `<3` survive.
- [ ] L8 exercise dropped when the judge rejects the `error_collocate`.
- [ ] `_l8_correctness_ok` and its retry loop removed; no regression in the
      existing P3 tests (the structural `_can_generate_l8` gate stays).
- [ ] `tags.collocation_judge` populated for both L5 and L8 rows.

**Files:**
- `services/vocabulary_ladder/exercise_renderer.py` — L5 + L8 renderers.
- `services/vocabulary_ladder/asset_generators/prompt3_transforms.py` — remove hack.
- `tests/test_vocab_ladder_judges.py` / existing P3 tests — update.

**Verification:** Render L8 for the sense that triggered the old correctness flip;
confirm the judge (not the string match) now governs, and a genuinely-wrong
error word is accepted.

---

## TASK-411: Sentence-validity judge module (`ladder_sentence_validity_judge`)

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** M
**Depends On:** TASK-401

**Description:**
New `services/exercise_generation/judges/sentence_validity.py`. Verdict shape,
judged per candidate sentence. Public API:
`judge_wrong_sentences(db, target, sentences_with_reasons, language_id) ->
list[JudgeOutcome]` where each item is `(sentence_text, labeled_reason)`. The
judge rules: is this sentence wrong **only** for its labeled reason, and not
(a) accidentally grammatical/acceptable, nor (b) wrong for a *different* reason
than labeled? `reject` a sentence that is actually fine or mislabeled. Serves
both L6 (3 wrong sentences) and L7 (1 incorrect sentence). Fail-open.

**Acceptance Criteria:**
- [ ] Per-sentence outcomes, order-aligned; length-mismatch → safe-accept all.
- [ ] Rejects an accidentally-grammatical "wrong" sentence and a mislabeled one.
- [ ] Fail-open on template/LLM error.
- [ ] Unit tests for L6 (3-item) and L7 (1-item) call patterns.

**Files:**
- `services/exercise_generation/judges/sentence_validity.py` — new.
- `tests/test_vocab_ladder_judges.py` — sentence-validity section.

**Verification:** `pytest tests/test_vocab_ladder_judges.py -k sentence_validity` green.

---

## TASK-412: Seed `ladder_sentence_validity_judge` prompts (en + zh) · Opus high

**Status:** [x] Done (2026-06-08)
**Type:** infra
**Complexity:** S
**Depends On:** TASK-411

**Description:**
Append en + zh rows for `ladder_sentence_validity_judge` to
`migrations/seed_ladder_judge_prompts.sql`. Prompt takes a target word and a
list of (sentence, labeled-reason) pairs and rules per sentence on
"wrong-only-for-the-labeled-reason". Chinese prompt must cover the L6 error
taxonomy already encoded in the zh P2 prompt (量词/体标/语序/方向补语 — see
[cloze_distractor_quality.sql:183-188](../../migrations/cloze_distractor_quality.sql#L183-L188)).

**Acceptance Criteria:**
- [ ] Two active rows (lang 2 + lang 1); model+provider populated.
- [ ] Output schema matches TASK-411's parser; reason taxonomy aligned with the
      generators' labels.

**Files:** `migrations/seed_ladder_judge_prompts.sql` — append.

**Verification:** scratch-DB select returns two active `ladder_sentence_validity_judge` rows.

---

## TASK-413: Wire sentence-validity judge into L6/L7

**Status:** [x] Done (2026-06-08)
**Type:** feature
**Complexity:** M
**Depends On:** TASK-411, TASK-412

**Description:**
L6: in `_render_semantic_discrimination` ([exercise_renderer.py:433-472](../../services/vocabulary_ladder/exercise_renderer.py#L433-L472))
judge the 3 `wrong_sentences` (paired with their explanations as the labeled
reason); drop rejected ones; if `<3` survive, return `None` (L6 needs exactly 3
wrong + 1 correct). L7: in `_render_spot_incorrect`
([exercise_renderer.py:474-508](../../services/vocabulary_ladder/exercise_renderer.py#L474-L508))
judge the single `incorrect_sentence` against its `error_description`; on
`reject`, return `None`. Attach `__judge_metas['sentence_validity']` in both.

**Acceptance Criteria:**
- [ ] L6 drops a "wrong" sentence the judge finds acceptable; skips when `<3` remain.
- [ ] L7 dropped when the incorrect sentence isn't actually incorrect-as-labeled.
- [ ] `tags.sentence_validity_judge` populated for L6 and L7 rows.

**Files:** `services/vocabulary_ladder/exercise_renderer.py` — L6 + L7 renderers.

**Verification:** Render L6/L7 for a sense with a mislabeled wrong sentence;
confirm it is dropped and recorded.

---

## TASK-414: Reject-rate SQL view (judge-as-data, 4.3)

**Status:** [x] Done (2026-06-09)
**Type:** infra
**Complexity:** M
**Depends On:** TASK-407, TASK-410, TASK-413, TASK-404

**Description:**
Create a read-only view `v_ladder_judge_reject_rates` aggregating, per
`(language_id, ladder_level, prompt_version, judge_key)`, the reject counts and
exercise counts pulled from `exercises.tags.<judge>_judge.rejected` joined to
`word_assets.prompt_version` (via `exercises.word_asset_id`). Surfaces a
reject-rate so prompt regressions are visible before learners see them. Ship in
a new `migrations/phase16_ladder_judge_reject_rates.sql`. Follow
[migrations/CLAUDE.md](../../migrations/CLAUDE.md): if it redefines an existing
view, search + archive superseded files.

**Acceptance Criteria:**
- [ ] View created; one row per `(language, level, prompt_version, judge)` with
      `exercises_n`, `rejected_n`, `reject_rate`.
- [ ] Reads the four judge keys (`cloze_judge`, `l1_distractor_judge`,
      `collocation_judge`, `sentence_validity_judge`) plus the P1 judge's
      warning sidecar.
- [ ] Pure SQL, no writes; safe to query on the live DB.

**Files:** `migrations/phase16_ladder_judge_reject_rates.sql` — new.

**Verification:** After rendering a batch, `SELECT * FROM
v_ladder_judge_reject_rates ORDER BY reject_rate DESC;` returns sane rates.

---

## TASK-415: Admin panel — judge reject-rate dashboard (4.3)

**Status:** [x] Done (2026-06-09)
**Type:** feature
**Complexity:** S
**Depends On:** TASK-414

**Description:**
Add a read-only admin route + template rendering `v_ladder_judge_reject_rates`
as a sortable table (language × level × prompt_version × judge, reject-rate
highlighted). Follow the existing admin route/template conventions in
`routes/admin_local.py`. No mutations.

**Acceptance Criteria:**
- [ ] Route registered behind the existing admin auth.
- [ ] Table sortable/filterable by language and level; high reject-rate rows flagged.
- [ ] No write paths; view-only query.

**Files:**
- `routes/admin_local.py` — new read-only handler.
- `templates/…` — new admin template (match existing admin template style).

**Verification:** Load the admin page on staging after a render batch; confirm
rates render and match the SQL view.

---

## TASK-416: Judge-layer integration test + smoke query

**Status:** [x] Done (2026-06-09)
**Type:** test
**Complexity:** S
**Depends On:** TASK-407, TASK-410, TASK-413, TASK-404

**Description:**
Add an end-to-end test that renders all judged levels for a fixture sense with
known-bad inputs (a synonym L1 distractor, an also-valid L5 collocate, a
genuinely-correct L8 error word, a mislabeled L6 sentence, an off-sense P1
sentence) and asserts each judge drops/flags the planted defect and writes its
tag meta. Add the `llm_calls` smoke query (accept/flag/reject distribution by
`task_name LIKE 'ladder_%'`) to the test-docs, mirroring the existing judge
smoke test.

**Acceptance Criteria:**
- [ ] One integration test covering all five judged levels' drop/flag paths.
- [ ] Asserts `tags.*_judge` populated per level.
- [ ] Smoke query documented and returns rows for the `ladder_*` task names.

**Files:**
- `tests/test_vocab_ladder_judges.py` — integration section.
- `wiki/features/exercise-generation-prompts.md` — smoke query note.

**Verification:** `pytest tests/test_vocab_ladder_judges.py` fully green.

---

## Model choices (applies to TASK-403/406/409/412)

Follow the per-language model pairing already used by the ladder prompts, set in
each seed row (no hardcoded model in Python — `get_template_config` is the single
source of truth):
- **English (lang 2):** the cheap-verifier tier used by `cloze_distractor_judge`
  (`google/gemini-2.5-flash-lite`, `openrouter`).
- **Chinese (lang 1):** the qwen tier used by the zh ladder prompts
  (`qwen/qwen-max` or the `qwen` judge model per memory
  [[distractor-judge-v3-likert]] — confirm against the live `prompt_templates`
  rows before seeding).

Judges are temperature-0, fail-open. If a judge proves too aggressive in the
reject-rate dashboard (TASK-414), re-tune the prompt and bump the row `version`
— never weaken the fail-open contract.

---

## Sequencing

Audit-recommended order (B3 leverage ranking): **4.2 first** (P1 sentence judge
— every level inherits these sentences), then **4.1** (L1 → collocation →
sentence-validity), then **4.3** (view → admin).

```
TASK-401 (tag sidecar)                    ── foundation for all wiring + 4.3
  ├─ TASK-402 → 403 → 404                  4.2  P1 sentence judge
  ├─ TASK-405 → 406 → 407                  4.1  L1 distractor judge
  ├─ TASK-408 → 409 → 410                  4.1  collocation (L5/L8, retires hack)
  └─ TASK-411 → 412 → 413                  4.1  sentence-validity (L6/L7)
TASK-414 (view)  ← needs 404,407,410,413   4.3  reject-rate view
TASK-415 (admin) ← needs 414               4.3  dashboard
TASK-416 (integration) ← needs 404,407,410,413
```

Within each judge: **module → prompt seed (Opus high) → wire**. The three
4.1 judge chains are independent of each other and of the 4.2 chain after
TASK-401, so they can be worked in parallel once the sidecar lands.
