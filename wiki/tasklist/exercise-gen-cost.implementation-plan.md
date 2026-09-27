---
title: "Exercise Generation Cost Reduction — Implementation Plan (TASK-809..816)"
feature: exercise-gen-cost
tech_page: ../decisions/ADR-028-exercise-gen-cost-under-1c.md
tasks_page: exercise-gen-cost.tasks.md
last_updated: 2026-09-26
status: Phase 1 (809-813) approved 2026-09-26; Phase 2 (814-816) gated on baseline + Phase 1 score
---

# Exercise Generation Cost Reduction — Implementation Plan

Exact, file:line-anchored implementation plans for TASK-809..816, written so a coding agent can
execute without re-exploring the codebase. Written 2026-09-26 against the live repo state
(commit tree at session start — `services/`/`scripts/` were NOT modified while writing this;
a baseline eval run was in progress in background processes at the time this plan was drafted).

**Do not implement any of this while a baseline/eval run is in flight** — every task below
touches a file a live `services/vocabulary_ladder/*` or `scripts/*` process may have already
imported; a lazy re-import or hot class reload could contaminate the run. Wait for the TASK-808
baseline to finish and file before touching code.

---

## TASK-809: Move zh generation to the qwen family

**Finding, not an implementation task.** A live query against `prompt_templates` (Supabase
project `kpfqrjtfxmujzolwsvdq`) on 2026-09-26 found the target state is **already live**:

| task_name | lang | version | model | is_active |
|---|---|---|---|---|
| `vocab_prompt1_core` | zh | 2 | `qwen/qwen3.7-plus` | true |
| `vocab_prompt1_core` | ja | 3 | `qwen/qwen3.7-plus` | true |
| `vocab_prompt2_exercises` | zh | 4 | `qwen/qwen3.7-plus` | true |
| `vocab_prompt2_exercises` | ja | 4 | `qwen/qwen3.7-plus` | true |
| `vocab_prompt3_transforms` | zh | 2 | `qwen/qwen3.7-plus` | true |
| `vocab_prompt3_transforms` | ja | 1 | `qwen/qwen3.7-plus` | true |
| every `ladder_*_generation` row, zh/ja | zh/ja | — | `qwen/qwen3.7-plus` | true |

All ten rows contain the literal substring `"JSON"` in `template_text` (confirmed via
`position('JSON' in template_text) > 0`), so the Qwen3.x `response_format: json_object` 400
landmine does not fire for any of them. `services/prompt_service.get_template_config` (lines
8-59) and `get_template_text` (62-96) both filter `is_active = true` and
`ORDER BY version DESC LIMIT 1`, so this is genuinely what's served, not a stale-loader artifact.

ADR-028's "Current model assignment" paragraph (dated 2026-09-24) describing zh
prompt2/prompt3 as `anthropic/claude-sonnet-5` is **stale** — those rows' `updated_at` is
`2026-08-17 21:49:11+00`, one day after `migrations/generator_model_routing_policy.sql`
(2026-08-16), which explicitly *preserved* them as claude-sonnet-5 exclusions. Something moved
them to qwen anyway on 2026-08-17, and no migration file in this repo records it. En rows for
the same task_names remain on claude-sonnet-5 (permitted — en generation may use any model).

**Action:** `migrations/exercise_gen_zh_generation_to_qwen.sql` is filed as the deliverable (a
generic, idempotent `DO` block that only touches a row if it's zh/ja, GENERATION-scoped, and NOT
already `qwen/%`). It is a no-op today. Do not re-run TASK-517's model-family work on these three
prompts believing it is still needed — verify with the query above before doing anything.

**Remaining real work for TASK-809 to be marked Done:** run it through the TASK-807 scoring
script (`scripts/score_exercise_gen_run.py`) against the TASK-806 reference set anyway — this
validates *current production quality* on qwen, which has never been scored against the frozen
reference set, not a new change. If it fails non-inferiority, that is a live quality problem
today, independent of this task.

**Test:** none needed (no code change). Re-run the verification SELECT after TASK-808's baseline
lands, to confirm no drift occurred during the baseline run.

**Risk:** low. The only residual risk is that the 2026-08-17 unrecorded change also altered
something else undocumented — worth a `git log -p -- migrations/ | grep -B5 '2026-08-17'`-style
check (there is no such migration file, so this was likely applied via `execute_sql` directly,
same as this investigation used) before assuming zh generation quality is fully understood.

---

## TASK-810: Cap retries at ≤2 real calls/step; remove the P3 salvage call

### Problem

Two independent retry layers stack:

1. **Generator-level outer retry** — each generator's own `_call_with_retry` loops
   `for attempt in (1, 2)`.
2. **`llm_service`-level repair** — `call_llm` (`services/llm_service.py:639`) catches
   `json.JSONDecodeError`/`RuntimeError` from `_make_one_call` (line 750-787) and — for any
   non-`'text'` `response_format` — unconditionally fires one more call via
   `_repair_malformed_json` (line 1162), regardless of whether the caller already plans to retry
   itself.

A single bad completion on generator attempt 1 can therefore cost: attempt 1 (primary) + attempt
1's internal json_repair + attempt 2 (retry) + attempt 2's internal json_repair = **4 real
calls**, before P3's salvage call (a 5th) even engages.

### Fix: `allow_internal_repair` flag on `call_llm`

**File:** `services/llm_service.py`

1. Add a new parameter to `call_llm` (signature at line 639-660):
   ```python
   def call_llm(
       prompt: str,
       *,
       ...
       generation_batch_id: str | None = None,
       allow_internal_repair: bool = True,
   ) -> dict | list | str | BaseModel:
   ```
2. In the `except (json.JSONDecodeError, RuntimeError) as exc:` block (line 760-787): when
   `response_format != 'text'` AND `not allow_internal_repair`, re-raise `exc` immediately
   instead of calling `_repair_malformed_json` — the caller's own outer loop is the intended
   single retry, not this one. Diff shape:
   ```python
   except (json.JSONDecodeError, RuntimeError) as exc:
       if response_format == 'text' or not allow_internal_repair:
           raise
       return _repair_malformed_json(...)
   ```
3. The schema-validation repair path (`_repair_and_retry`, triggered only when `schema=` is
   passed) is NOT used by any of the four call sites touched below (none pass `schema=`), so it
   needs no change for this task — leave it as the one true repair path for schema-gated callers
   (there are none yet in `vocab_ladder`; `SplitLevelGenerator` validates with
   `validate_ladder_output` *after* the call, not via the `schema=` kwarg).

### Call sites to update — pass `allow_internal_repair=False`

Each of these already implements its own 2-attempt outer loop; disabling the internal repair
makes attempt 2 a fresh primary-style call instead of a context-carrying repair turn, capping the
step at exactly 2 real calls under both normal and forced-failure conditions.

- `services/vocabulary_ladder/asset_generators/prompt1_core.py:212-224` (`_call_with_retry`) —
  add `allow_internal_repair=False` to the `call_llm(...)` call.
- `services/vocabulary_ladder/asset_generators/prompt2_exercises.py:100-113` — same.
- `services/vocabulary_ladder/asset_generators/prompt3_transforms.py:156-169` (the primary call
  inside `_call_with_retry`) — same. Do NOT add it to `_salvage_from_text`'s call (line 217-230)
  — that whole method is being removed (below).
- `services/vocabulary_ladder/asset_generators/_split_base.py:177-193`
  (`SplitLevelGenerator._call_with_retry`, shared by L4/L8/typed_llm generators) — same. This one
  call fixes the retry cap for every `TypedLLMGenerator` subclass and `MorphologySlotGenerator`/
  `CollocationRepairGenerator` in one place.

`prompt1_core.repair()` (line 247-303) and `repair_sentences()` (305-389), and
`prompt3_transforms`'s `salvage`, are **pipeline-level semantic repairs** (`call_role='repair'`),
triggered at most once per asset by `VocabAssetPipeline._generate_for_sense_impl` after
structural/judge validation — these are a distinct, already-capped-at-1 step and are out of
scope for the "≤2 calls per generation step" rule (which is about the raw LLM-call attempt loop
inside one generator's `generate()`, not the pipeline's separate repair stage).

### Remove the P3 salvage call

**File:** `services/vocabulary_ladder/asset_generators/prompt3_transforms.py`

1. Delete `_salvage_from_text` (lines 207-251) entirely.
2. In `_call_with_retry` (143-205), the `except Exception as e:` branch at attempt 2 (lines
   170-188) currently calls `self._salvage_from_text(...)` on total failure. Replace with a
   direct `return None` and a log line — matches every other generator's failure contract, and
   removing the salvage call is exactly TASK-810's stated acceptance criterion ("removed or
   schema-gated"; removing is simpler and the split levels already show the schema-gated
   alternative works better for a monolithic-prompt-feels-fragile problem, so removal — forcing a
   *level loss*, not a *malformed-response guess* — is the recommended choice here, not a partial
   implementation).
3. Also remove the "missing levels → retry once → accept partial on second miss" three-way
   branch's dependency on `attempt == 2` triggering salvage; with salvage gone, the existing
   "accept partial" `else` branch at line 199-204 already does the right thing unchanged.

### Data shapes

No change — `_call_with_retry` still returns `dict | None`, same shape as today.

### Tests

New: `tests/test_generation_retry_caps.py`
- `test_call_llm_allow_internal_repair_false_reraises_on_bad_json` — mock `_make_one_call` to
  raise `json.JSONDecodeError`, call `call_llm(..., allow_internal_repair=False)`, assert the
  original exception propagates and `_repair_malformed_json` is never called (patch/spy it).
- `test_prompt1_core_caps_at_two_calls_on_repeated_failure` — mock `call_llm` (or the underlying
  HTTP client) to always fail; call `CoreAssetGenerator.generate(...)`; assert `call_llm` was
  invoked exactly 2 times and the method returns `None`.
- `test_prompt3_salvage_never_fires` — same forced-failure setup for
  `TransformAssetGenerator.generate(...)`; assert no `llm_calls` row (or CSV row, since this can
  run offline) is ever logged with `task_name='vocab_prompt3_transforms_salvage'`, and
  `_salvage_from_text` no longer exists as an attribute (`assert not hasattr(TransformAssetGenerator, '_salvage_from_text')`).
- Update existing `tests/test_asset_pipeline_p1_gate.py` / any test that mocks `call_llm` with 3+
  side effects expecting a 2-attempt-then-repair sequence — grep
  `tests/` for `_call_with_retry` and `salvage` before starting to find what already covers this
  path and would need its mock call-count assertions bumped down.

### Risks

- **Behavior change, not just a cap:** dropping `allow_internal_repair` means a single malformed
  JSON response on attempt 1 no longer gets an in-context repair turn before attempt 2 — attempt
  2 is a fresh sample instead. This could very slightly change the accept rate for P1/P2/P3 on
  transient malformed output. Mitigate: TASK-807 scoring run before/after on the reference set;
  the ADR explicitly requires no valid-rate regression for prompt3.
- **`_split_base.py` is shared** by every `TypedLLMGenerator` (syn/ant, word_family, particle
  selection) and `MorphologySlotGenerator`/`CollocationRepairGenerator` — one change here affects
  many generators at once. Good for consistency, higher blast radius if wrong; test broadly
  (at minimum one sense per affected type_code, per language it's active in).
- P3's "accept partial on missing levels" behavior is preserved, but callers downstream
  (`VocabAssetPipeline`, line ~403-421) already handle a partial P3 asset — verify no caller
  assumed salvage always eventually filled every level (grep `p3_asset` handling for an assumed
  non-None guarantee).

---

## TASK-811: Level-scoped regen in `queue_drain.py`

### Problem

`services/vocabulary_ladder/queue_drain.py:_regenerate` (lines 256-308) always does:
1. `pipeline.generate_for_sense(sense_id, language_id, force=True)` — **full P1+P2+P3+split+typed
   regeneration for both variants**, even when only one ladder level needs a fix.
2. `renderer.build_rows(sense_id, language_id)` (line 280) — **re-renders and re-judges every
   active level for both variants.** `LadderExerciseRenderer.build_rows`
   (`services/vocabulary_ladder/exercise_renderer.py:63`) iterates
   `for level in active_levels: content = self._render_level(level, ...)` (line 175-218) and,
   inside the per-level renderers, calls the 7 render judges directly — despite the module
   docstring's stale claim of "No LLM calls": confirmed call sites are
   `exercise_renderer.py:558` (`filter_l1_distractors`), `:840`
   (`filter_collocation_distractors`), `:888` and `:965` (`judge_wrong_sentences`, L6/L7), `:1024`
   (`judge_collocation_repair`, L8). The typed-capability loop (~line 380-445) similarly judges
   each type via `typed_llm.generator_class(type_code).render(...)`.
3. Lines 289-293: **deletes every existing exercise row for the sense** (`.eq('word_sense_id',
   sense_id).not_.is_('word_asset_id', 'null')`) and inserts the full fresh set — no level
   filter.

A coverage-gap regen (the common case — "this sense is missing its `form_production` family")
pays for every level's judge call, not just the missing one.

### Fix

**File:** `services/vocabulary_ladder/exercise_renderer.py`

1. Add an optional `levels: set[int] | None = None` parameter to `build_rows`:
   ```python
   def build_rows(
       self, sense_id: int, language_id: int,
       levels: set[int] | None = None,
   ) -> list[dict]:
   ```
2. After `active_levels = compute_active_levels(...)` and the per-type gate narrowing (lines
   83-110), add: `if levels is not None: active_levels = [lv for lv in active_levels if lv in levels]`.
3. The typed-capability loop (~380-445) iterates capability rows keyed by `cap['ladder_level']`
   (or `None` for non-ladder types like `timed_speed_round`) — add the same filter there:
   `if levels is not None and cap.get('ladder_level') is not None and cap['ladder_level'] not in levels: continue`.
   Non-ladder typed items (`ladder_level is None`) have no level to scope by; when `levels` is
   given, skip them (a level-scoped regen should not touch level-less types) unless the caller
   passes a sentinel to mean "also regen typed non-ladder items" — out of scope for this task,
   leave a `# TODO(TASK-811b)` comment if a future caller needs it.
4. `render_all` (line 42-61) does not need a `levels` param — it is only used for a full fresh
   render; `_regenerate` below calls `build_rows` directly (as it already does at line 280), not
   `render_all`.

**File:** `services/vocabulary_ladder/asset_pipeline.py`

5. `VocabAssetPipeline.generate_for_sense` / `_generate_for_sense_impl` have no partial-level mode
   today — they always regenerate P1 fully and fan out P2/P3/split/typed unconditionally. Add an
   optional `levels: set[int] | None = None` param threaded from `generate_for_sense` (line 59)
   into `_generate_for_sense_impl` (95). Inside the fan-out block (lines 321-356): P1 always
   regenerates (P1 is the shared foundation; there is no cheaper partial-P1). Gate the P2/P3/
   split/typed futures: P2 only if `levels is None or levels & {1,3,5,6}` (`PROMPT2_LEVELS`); P3
   only if `levels is None or levels & set(PROMPT3_MONOLITH_LEVELS) | set(split_levels)` similarly
   scoped per-future for split levels and typed generators (each future already knows its own
   level/type — skip submitting a future whose level isn't in `levels`). This is the bigger half
   of the win: today `_regenerate` re-runs P1 (cheap-ish, 1 call) but ALSO re-runs P2+P3+splits+
   typed for BOTH variants (the expensive half) even for a 1-level gap.
6. `_store_asset` (line 877) already upserts per `asset_type` (`on_conflict='sense_id,asset_type'`)
   — a P2/P3 fragment for a level-scoped regen still overwrites the WHOLE `prompt2_exercises_A`
   (etc.) asset row, because P2 emits levels 1/3/5/6 in ONE call — this is a real constraint: you
   cannot regenerate "only level 3" out of P2's single call without also re-asking for 1/5/6 in
   the same prompt (the model is asked for `active_levels_json`, which still includes all P2
   levels active for the sense — TASK-811 cannot narrow the *generation* call below "all levels
   owned by that particular prompt", only skip prompts (P2 vs P3 vs a specific split/typed
   generator) that own NONE of the requested levels. Document this precisely in the PR: "level
   scoped" means "prompt-scoped to the levels that need it", not "sub-prompt scoped" — full
   granularity would need TASK-815's per-level bundle collapse to go the other way (split further,
   not bundle), which is explicitly not the plan.

**File:** `services/vocabulary_ladder/queue_drain.py`

7. `_regenerate` (256-308): read the queue row's `detail['missing_families']` (already present
   for `coverage_gap` rows, `row['detail']` — see `enqueue_coverage_gaps`, lines 76-118) and map
   family → ladder level via the existing capability/level tables (`compute_active_levels`/
   `LADDER_LEVELS` in `services/vocabulary_ladder/config.py` — confirm the family→level mapping
   function; if none exists, add `families_to_levels(families: list[str], semantic_class, language_id) -> set[int]`
   to `config.py` next to `compute_active_levels`). For `regen`/`subscribe_topup` reasons (no
   `missing_families`), fall back to `levels=None` (full regen, current behavior) — those reasons
   don't carry a level hint today.
8. Pass `levels=` through to both `pipeline.generate_for_sense(..., levels=levels)` (line 272) and
   `renderer.build_rows(sense_id, language_id, levels=levels)` (line 280).
9. Scope the delete/insert (lines 289-293): when `levels is not None`, delete only
   `.eq('word_sense_id', sense_id).not_.is_('word_asset_id', 'null').in_('ladder_level', list(levels))`
   instead of every row; when `levels is None`, keep the current full delete. Insert `new_rows`
   unchanged (they're already scoped to what `build_rows` produced).

### Data shapes

`levels: set[int] | None` — a set of `exercises.ladder_level` values (1-8). `None` means "no
scoping, full regen" (today's only behavior) so this is purely additive/backward compatible —
every existing caller (`render_all`, the batch runner, `_regenerate` for non-coverage-gap
reasons) keeps working unchanged by never passing `levels`.

### Tests

New: `tests/test_level_scoped_regen.py`
- `test_build_rows_levels_filter_narrows_active_levels` — call `build_rows(sense_id, lang,
  levels={3})` against a fixture sense with assets for levels 1/3/5/6/7; assert only a level-3 row
  comes back.
- `test_build_rows_levels_none_is_unchanged` — parity test: `build_rows(sense_id, lang)` (no
  `levels`) produces byte-identical output to before this change, over the existing fixture set
  used by `tests/test_ladder_validation_profiles.py` or similar.
- `test_regenerate_scoped_delete_leaves_other_levels_untouched` — insert exercise rows for levels
  1/3/6 with known `updated_at`; call `_regenerate` with a `detail={'missing_families': [...]}`
  that maps to level 3 only; assert level 1/6 rows are untouched (`updated_at` unchanged, `id`
  unchanged) and only level 3 changed.
- `test_regenerate_full_regen_still_full` — a `reason='regen'` row (no `missing_families`) still
  wipes and rebuilds every level, matching today's behavior exactly (parity/regression guard).

### Risks

- **Coupling to `missing_families`.** If a family→level mapping doesn't already exist cleanly in
  `config.py`, building it correctly (some families span multiple levels, e.g. semantic
  discrimination) is itself real work and the highest-risk part of this task — spend the first
  hour confirming the mapping exists/is derivable before committing to the rest of the plan.
- **P2/P3 sub-prompt granularity ceiling** (point 6 above) — a level-scoped regen for a level P2
  owns still re-asks the model for every P2 level on that sense, not just the missing one. This
  is a real, permanent limitation of this task's scope, not a bug to fix here — document it
  clearly so nobody re-files it as a defect later.
- **Partial-variant drift.** If variant A's level 3 regenerates but variant B's doesn't (because
  only A had a gap), the two variants can end up generated at different times against a changed
  P1 core (if P1 also regenerated) — verify the pipeline's "P1 always regenerates" choice (step 5)
  doesn't itself invalidate the "level-scoped" framing when P1's sentences shift under an
  unrelated level's content. Consider gating P1 regen too (skip when `force=True` was only for a
  coverage gap and existing P1 is still valid) as a follow-up, not required for this task's AC.

---

## TASK-812: Stable-prefix ordering + cache-token logging + judge `max_tokens` caps

### Part A — stable-prefix ordering

**Current shape (all three generators build a flat string via `render_template`, no
system/user split):** `prompt1_core.py:_build_prompt` (171-198), `prompt2_exercises.py:
_build_prompt` (140-171), `prompt3_transforms.py:_build_prompt` (253-301) all call
`render_template(template, word=..., ...)` and hand the WHOLE result to `call_llm(prompt_text,
...)` as the single user message — `call_llm` (line 732-735) only ever sends
`[{'role': 'system', ...}]` (if `system_prompt` given — none of these callers pass one) +
`[{'role': 'user', 'content': prompt}]`. Provider prompt caching (OpenRouter/Anthropic/Qwen, all
prefix-based) needs the STABLE part of the prompt (language rules, output-format contract, the
"通用规则" numbered list seen in the zh P2/P3 templates above) to be a byte-identical PREFIX
across calls, with the per-sense variable content (word, sentences_json, active_levels_json)
LAST.

Looking at the actual zh template text (pulled live, `vocab_prompt2_exercises` v4 zh): the
template today interleaves stable rules and variables throughout (`目标词：{word}` appears in
line 1, rules in the middle, `{sentences_json}` before the rules) — the placeholder ORDER in the
template string, not just its content, determines what's a stable prefix once rendered.

**Change:** this is a `prompt_templates.template_text` content change (a migration, not a code
change) — reorder each active template so ALL `{...}` placeholders that vary per sense appear
strictly after all static rule text. Concretely, for `vocab_prompt2_exercises`/
`vocab_prompt3_transforms`/`vocab_prompt1_core` (all 3 languages): move the "通用规则"
(general rules) block to the TOP of the template, and the word/sentences/active_levels
placeholders to the BOTTOM. This is content-editing work, not a code change — plan it as a
follow-up migration (`migrations/task812_stable_prefix_reorder.sql`, not drafted here since it
requires per-language native-text-safe reordering of ~10 templates and should be reviewed
per-language, not auto-generated).

**Additionally**, `call_llm` should optionally accept the stable/variable split explicitly rather
than relying on template author discipline: add a `system_prompt`-based path where generators
pass the STABLE rules block as `system_prompt=` and only the variable content as `prompt=` — most
providers cache the system-message prefix more reliably than a user-message prefix. This requires
each `_build_prompt` to return `(system_text, user_text)` instead of one string — a bigger
refactor than the template reorder; recommend doing the template reorder first (cheap, safe,
measurable) and treating the system/user split as a stretch goal inside this task, not a blocker
for the acceptance criteria (which only requires "the highest-volume generation prompts ... order
stable content first", satisfied by the template reorder alone).

### Part B — cache-token logging

Already implemented and live: `_extract_usage_tokens` (`services/llm_service.py:1038-1074`)
reads `prompt_tokens_details.cached_tokens` and `_log_llm_call`/`_insert_llm_call_row` already
persist `cached_tokens` to `llm_calls` (columns added by
`migrations/llm_calls_cost_instrumentation.sql`, per TASK-804). **No code change needed for Part
B** — it is already wired. TASK-812's acceptance criterion ("`cached_tokens` is non-null and >0
on a warm second call") is purely a VERIFICATION step once Part A's reorder ships: run 2
back-to-back identical-prefix calls (same sense, same template) and check
`llm_calls.cached_tokens` on the second. If it's still 0/NULL after the reorder, that answers
ADR-028 open question (b) in the negative for the model tested — file that as a finding, not a
bug.

### Part C — judge `max_tokens` caps

**Current state** (from `llm_calls` completion-length stats, pilot rows, `pipeline='vocab_ladder'`
— see table below) vs. current caps:

| judge (`llm_calls.task_name`) | file:line (current `max_tokens`) | current cap | observed `length(raw_response)` (chars): avg / p50 / p90 / max | recommended new cap |
|---|---|---|---|---|
| `judge_ladder_sentence_validity` | `services/exercise_generation/judges/sentence_validity.py:112` = 19000 | 19000 | 258 / 316 / 370 / 390 | **1500** (≈4x p90 chars ÷ ~4 chars/token ≈ 95 tokens raw; 1500 leaves generous headroom for CJK's lower chars/token ratio and multi-item batches) |
| `cloze_distractor_judge` | `services/exercise_generation/judges/cloze.py:88` = 4750 | 4750 | 316 / 330 / 373 / 396 | **1000** |
| `judge_ladder_l1_distractor` | `services/exercise_generation/judges/l1_distractor.py:81` = 4500 | 4500 | 309 / 308 / 355 / 366 | **1000** |
| `ladder_relation_judge` / `ladder_word_family_judge` | `services/exercise_generation/judges/relation.py:256` = 8000 | 8000 | (relation) 271 / 267 / 327 / 345; (word_family) 288 / 291 / 312 / 339 | **1500** (shared cap; relation's per-sense-checked-across-all-meanings answer is the longer of the two) |
| `judge_ladder_particle` | `services/exercise_generation/judges/particle.py:156` = 3000 | 3000 | no pilot rows captured yet (ja-only, low volume in the pilot sample) | **1500** (keep close to current until a ja-specific sample is captured; do not cut below cloze/l1's cap since particle's per-candidate object has 2 keys same as relation) |
| `judge_ladder_collocation` | `services/exercise_generation/judges/collocation.py` (no `max_tokens` set — line 212-222, `call_llm(...)` call has no `max_tokens` kwarg at all) | **unbounded** | not isolated in the pilot query (grouped generically) — re-run `select length(raw_response) from llm_calls where task_name='judge_ladder_collocation'` before finalizing | **1500** (highest-priority fix — this is the one judge with NO ceiling at all today, meaning a worst-case runaway completion is billed and latency'd in full) |

All figures are from `select task_name, count(*), avg/percentile_cont(length(raw_response)) ...
from llm_calls where pipeline='vocab_ladder' group by task_name` against the live Supabase
project on 2026-09-26 (21 task_names returned, pilot-scale row counts of 1-29 per task — small-n,
treat the p90 column as directional, not final; TASK-808's 30-senses/language baseline should
re-derive these before the caps ship, since n=1-2 for some rows here is not statistically
reliable). The recommended caps above use roughly 4x the observed p90 CHARACTER count translated
to a token estimate with generous headroom (judge outputs are short structured JSON, so
over-provisioning 10-20x the p90 is cheap insurance against a legitimate long multi-candidate
response while still being ~3-13x smaller than several of today's caps).

**Change:** add an explicit `max_tokens=<value>` kwarg to every judge's `call_llm(...)` call site
listed above (`collocation.py:212` needs the kwarg ADDED, not just changed). Do NOT change
`sentence_validity.py`'s 19000 without first re-deriving its p90 from a larger sample — a
19000-token judge cap costs real money per call if the model ever legitimately fills it (a
runaway/repeating completion), so lowering it is a pure win on the failure mode even though the
success-path savings from a lower cap on a short-JSON judge is `max_tokens` is a ceiling, not a
target — the provider does not bill for unused budget, so this cap change saves money ONLY on
runaway/pathological completions, not on the p50 case. Frame the estimated savings this way in
the writeup, don't overclaim per-call savings on well-behaved responses.

### Tests

- `tests/test_judge_max_tokens_caps.py` (new) — for each of the 7 judge modules, assert the
  `call_llm(...)` call site includes an explicit `max_tokens` kwarg (a source-inspection test via
  `inspect.getsource` + a regex, or a mocked-`call_llm` call-arg assertion per judge's public
  entry point) — this is a regression guard so a new judge or a refactor can't silently drop back
  to "unbounded".
- Cache-token verification is a live smoke test, not a unit test (see Part B) — record the result
  in `wiki/evaluations/exercise-gen-baseline-2026-09.md` or a follow-up note once run.

### Risks

- **Template reorder (Part A) is native-language content editing**, not mechanical — a badly
  reordered zh/ja template can change model behavior in ways a diff won't show. Route through a
  native-checked review or at minimum the TASK-807 pairwise-preference protocol before shipping,
  per-language.
- **`max_tokens` cap too tight** truncates a legitimate long response mid-JSON, which
  `clean_json_response`/`json.loads` will then fail to parse — this LOOKS like the malformed-JSON
  path from TASK-810 and would silently eat one of the newly-capped 2 real calls on a false
  positive. Ship the new caps only after confirming (from TASK-808's larger baseline) the p99, not
  just p90, comfortably clears the chosen cap.
- Collocation judge's current "no cap at all" — changing this is the highest-value, lowest-risk
  item in this task (pure downside removal); prioritize it first if time-boxing this task.

---

## TASK-813: Provider price routing + reasoning disabled

### Current state

`services/llm_service.py:_make_one_call` (923-997) builds the OpenRouter payload (940-957).
Today `payload['extra_body']` is set ONLY for usage-cost reporting (`{'usage': {'include':
True}}`, line 957) when `_is_openrouter(client)`. There is no `provider` routing preference and no
`reasoning` control anywhere in this payload — confirmed by reading the full function body.

### Change

**File:** `services/llm_service.py`

1. Add two new `call_llm` kwargs (signature, line 639-660):
   ```python
   provider_routing: dict | None = None,   # e.g. {'sort': 'price'}
   disable_reasoning: bool = True,         # default ON — see rationale below
   ```
2. In `_make_one_call` (923-940), extend the `payload['extra_body']` construction (957) to merge
   in both, only for OpenRouter clients, and only when the target model is not a known
   reasoning-only model:
   ```python
   if _is_openrouter(client):
       extra_body = {'usage': {'include': True}}
       if provider_routing:
           extra_body['provider'] = provider_routing
       if disable_reasoning and not _is_reasoning_only_model(model):
           extra_body['reasoning'] = {'exclude': True}
       payload['extra_body'] = extra_body
   ```
3. Add `_is_reasoning_only_model(model: str) -> bool` — a small denylist/allowlist function
   (e.g. matches `qwen3.8-max`, any future `-thinking`/`-reasoning` suffixed slug) so
   `reasoning: {exclude: True}` is never sent to a model that requires reasoning to function at
   all (per the "qwen3.8-max is a reasoning model" finding — needs ~16k max_tokens, 100-330s/call,
   and must never be silently selected here). Sending `reasoning: {exclude: True}` to a model
   that doesn't support the param should be harmless (OpenRouter typically ignores unknown
   `extra_body` keys per-provider), but the safety requirement in the AC ("don't send reasoning
   params to models that reject them") means this needs verifying per-provider, not assumed — see
   Risks.
4. Thread `provider_routing={'sort': 'price'}` as the DEFAULT for every `vocab_ladder` pipeline
   call site (`prompt1_core.py`, `prompt2_exercises.py`, `prompt3_transforms.py`,
   `_split_base.py`, all 7 judges) OR — lower-touch — make `provider_routing` default to
   `{'sort': 'price'}` inside `call_llm` itself when `pipeline == 'vocab_ladder'` and the caller
   didn't override it, avoiding a ~15-file mechanical edit. Recommend the pipeline-scoped default
   in `call_llm` for this task; a per-call-site override remains available for anything that
   needs a specific provider (none identified today).
5. `disable_reasoning=True` should default at the `call_llm` level for ALL pipelines, not just
   `vocab_ladder` — reasoning mode being silently engaged is a cross-pipeline risk (the
   `qwen3.8-max` finding was for fat-seed authoring, a different pipeline). Default True with an
   explicit opt-out for any pipeline that intentionally wants reasoning (search
   `pipeline='claude_cli'`/subagent paths before assuming none do).

### Data shapes

`provider_routing: dict | None` — passed through verbatim as OpenRouter's `provider` field
(see OpenRouter docs for the full shape; `{'sort': 'price'}` is the minimal form named in the
ADR). `disable_reasoning: bool` — a boolean flag, not a pass-through dict, so `call_llm` owns
translating it to `{'exclude': True}` (or `{'effort': 'none'}` if measurement shows `exclude` is
not honored by a given provider — verify against OpenRouter's actual behavior for at least
`qwen/qwen3.7-plus`, `anthropic/claude-sonnet-5`, and `google/gemini-3.5-flash-lite` before
picking one form and hardcoding it).

### Tests

- `tests/test_provider_routing_and_reasoning.py` (new):
  - `test_default_provider_routing_applied_for_vocab_ladder` — mock the OpenAI client's
    `chat.completions.create`, call `call_llm(..., pipeline='vocab_ladder')`, assert the captured
    `extra_body['provider'] == {'sort': 'price'}`.
  - `test_reasoning_excluded_by_default` — same mock, assert `extra_body['reasoning'] ==
    {'exclude': True}` for a non-reasoning model.
  - `test_reasoning_not_sent_to_reasoning_model` — call with `model='qwen/qwen3.8-max'` (or
    whatever `_is_reasoning_only_model` matches), assert `'reasoning'` key is ABSENT from
    `extra_body`.
  - `test_no_call_site_resolves_to_reasoning_class_model` — the AC's "regression test": iterate
    every `get_template_config`-resolved model currently active for `vocab_ladder` task_names
    (query `prompt_templates` or use a frozen fixture list) and assert none matches
    `_is_reasoning_only_model`.

### Risks

- **Sending an unsupported `extra_body` key to a provider that hard-errors on unknown fields**
  (rather than ignoring them) would turn "disable reasoning" into "break every call for that
  provider" — this must be verified live against each of the 3 models named above (a 1-sense
  smoke call per model, checking for a 400) before defaulting `disable_reasoning=True` globally.
  This is the single highest-risk item in TASK-813 and should be the first thing measured, not
  the last.
- **Provider routing changing which underlying provider serves a model** can change latency and,
  more importantly, could route to a provider with weaker JSON-mode support for a given model,
  reopening the Qwen3.x JSON-keyword landmine on a provider where it wasn't previously observed.
  Re-verify the "JSON" literal / 400 landmine check from TASK-809 after this ships, not just once.
- `qwen3.8-max` is named as the one confirmed reasoning-only model in scope today, but the
  denylist function needs to be a pattern/family check, not a hardcoded single-string match, so a
  future qwen reasoning variant doesn't silently slip through.

---

## Cross-cutting notes for TASK-814/815/816 (Phase 2 — gated, do not start yet)

Not implementation-planned here in file:line detail (out of scope for this pass — Phase 2 is
gated on the Phase 0 baseline and a Phase 1 non-inferiority score, per the tasklist). What IS
delivered now: the draft bundle-prompt migration
(`migrations/exercise_gen_bundle_prompts_draft.sql`) that TASK-815/816 will consume, with a
feature flag (`VOCAB_LADDER_BUNDLE_MODE`, default `"off"`) sketched in that file's header so the
eventual code change has a clean on/off switch from day one. See that file for the new
`prompt_templates` task_names, their draft template text (derived from the live zh templates read
2026-09-26, preserving every rule found: L1 audio-confusable-only / no pitch-accent-only pairs,
compound-word/whole-word anchoring via "义项/角色一致性", the four-way L3 failure-dimension
self-check, L8's four hard rules, and the "check ALL senses, not just the taught one" rule from
`ladder_relation_judge`), and the risk notes for the bundle-collapse approach itself.
