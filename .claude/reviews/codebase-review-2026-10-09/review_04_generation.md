# Review 04 - services/exercise_generation, test_generation, topic_generation (read-only)

### [HIGH] Queue item silently marked "active"/completed with 0 tests when generation throws
- Category: correctness
- Location: services/test_generation/orchestrator.py:440-445 (then 448-449)
- Problem: `_process_queue_item` wraps `_generate_test` in `except Exception` that only logs, then unconditionally calls `mark_queue_completed(item.id, 0)`. Any non-Judge/non-Jev failure (LLM error, prose/question validation, DB write) permanently consumes the topic's queue slot as "active" with zero tests; it is never retried and `mark_queue_failed` is unreachable for it. The `_run_impl` "tests_failed" counter is also not incremented.
- Evidence: lines 440-443 `except Exception as e: logger.error(...)` -> falls through to `self.db.mark_queue_completed(item.id, tests_generated)`.
- Fix: re-raise (so the caller's `mark_queue_failed` path runs) or mark failed when `tests_generated == 0` after an exception.

### [HIGH] Queue items stuck in 'processing' forever after a JudgeUnavailable abort or crash; claim is non-atomic
- Category: correctness
- Location: services/test_generation/database_client.py:178-266 (get_pending/mark_queue_processing); orchestrator.py:338-345,424-428
- Problem: pending rows are SELECTed then flipped to 'processing' per item with a separate UPDATE (no `WHERE status=pending`, no lease/timeout, no reaper), so two concurrent runners (cron + manual run_batch) can take the same item, and an item whose run aborts via `JudgeUnavailable` (re-raised at 424) or a process kill stays 'processing' and is never selected again (only 'pending' is fetched). The batch path (`_run_batch_impl`) leaves items pending on abort, so the two paths disagree. `mark_queue_processing` also resets `tests_generated=0` and `processed_at`.
- Evidence: `.eq('status_id', pending_status_id)` only; `update_queue_item_status` has no status guard.
- Fix: atomic claim (UPDATE ... WHERE status=pending RETURNING, or RPC with FOR UPDATE SKIP LOCKED) plus a stale-`processing` reaper; on JudgeUnavailable revert the item to pending.

### [HIGH] Legacy collocation/vocab batch runners are not inside batch_mode(), so judges fail OPEN
- Category: correctness
- Location: services/exercise_generation/run_exercise_generation.py:12-115 (run_vocabulary_batch, run_collocation_batch)
- Problem: both batch entry points call `VocabAssetPipeline.generate_for_sense` / `ExerciseGenerationOrchestrator.run` without `with batch_mode():`. A dead judge slug returns `safe_accept` for every item and the batch ships unjudged content - exactly the TASK-510 outage. Only scripts (run_content_build, run_generation_batch, run_exercise_gen_eval, run_ladder_from_existing) and test_gen run/run_batch wrap it. Also `except Exception` at lines 94/127 would swallow a `JudgeUnavailable` anyway if it did fire.
- Evidence: `grep batch_mode(` over repo shows no use in this module.
- Fix: wrap the loops in `batch_mode()` and re-raise `JudgeUnavailable` before the generic `except`.

### [HIGH] Legacy orchestrator reports success when the exercise insert fails
- Category: correctness
- Location: services/exercise_generation/orchestrator.py:238-262 (`_batch_insert`) and run() lines 122-143
- Problem: `_batch_insert` catches every insert exception, logs, and returns None. `run()` then returns `counts`/`total` from generated rows as if persisted, and run_collocation_batch records it as success. Generated (paid) work is silently lost.
- Evidence: `except Exception as exc: logger.error("Batch insert failed: %s", exc)` with no re-raise/return value.
- Fix: return/raise the failure and report `inserted` separately from `generated`.

### [MEDIUM] JudgeUnavailable abort does not stop queued work in the batch thread pool
- Category: correctness
- Location: services/test_generation/orchestrator.py:1794-1830
- Problem: all slots are `submit`ted up-front, then the first `JudgeUnavailable` is re-raised from `future.result()`; leaving the `with BatchModeThreadPoolExecutor` block calls `shutdown(wait=True)` without `cancel_futures=True`, so every remaining queued slot still runs prose + question LLM calls (each then fails at its judge). Comment claims only "already-running" futures finish.
- Evidence: no `cancel_futures`/`pool.shutdown` in `_run_batch_impl`; same pattern in `_generate_vocabulary` (line 1116) and question_generator.py:249.
- Fix: on JudgeUnavailable call `pool.shutdown(wait=True, cancel_futures=True)` (or a shared stop Event checked at the top of `_generate_one`).

### [MEDIUM] cfg['template'].format(...) is outside every judge's try block
- Category: correctness
- Location: judges/cloze.py:81, l1_distractor.py:75, particle.py:159, distractor_plausibility.py:191, answer_entailment.py:302, sentence_validity.py:105, p1_sentences.py:85, translation_uniqueness.py:191, collocation.py:203, relation.py:248
- Problem: a DB-edited template with a stray `{`/`}` or a renamed placeholder raises KeyError/IndexError/ValueError that is neither fail-open nor JudgeUnavailable; it propagates as a generic exception, which the test-gen orchestrator then turns into a swallowed per-item failure (see HIGH 1) and the legacy pipeline into a dropped sense. Prompts are hot-edited via migrations, so this is a realistic failure.
- Evidence: `.format` follows the template-load try/except but precedes the LLM-call try/except in each file.
- Fix: do the format inside the same try as the load and route to the `_failopen`/`safe_accept` chokepoint (so batch mode aborts loudly).

### [MEDIUM] Three judges hard-code provider='openrouter', ignoring prompt_templates.provider and LLM_DEFAULT_PROVIDER
- Category: correctness
- Location: judges/answer_entailment.py:311, judges/cloze.py:106, judges/distractor_plausibility.py:207
- Problem: other judges pass `cfg['provider']`; these three bypass both the DB row and the claude_cli routing that exercise_generation/llm_client.py documents as its fix, so a provider change in prompt_templates is silently ignored for them.
- Evidence: literal `provider='openrouter'` vs `provider=cfg['provider']` in particle.py:186.
- Fix: use `cfg['provider']` everywhere.

### [MEDIUM] Production-queue topics fall back to the ENGLISH prompt silently
- Category: correctness
- Location: services/test_generation/database_client.py:711-780; services/topic_generation/database_client.py:553-595
- Problem: when a zh/ja template row is missing/inactive, both loaders silently serve the language_id=2 template (only a debug log). A Chinese/Japanese test can be generated with an English prompt; the docstring in the same function ("fails loudly ... no silent fallback") contradicts this. Topic loader also returns None with only a warning, so callers must remember to check.
- Evidence: `if language_id != 2: ... .eq('language_id', 2)` block in both.
- Fix: remove the fallback for language-bound tasks (raise), keep only for explicitly language-neutral keys.

### [MEDIUM] Three+ divergent prompt-template loaders
- Category: redundancy
- Location: services/prompt_service.py:8 (get_template_config), prompt_service get_template_text, test_generation/database_client.py:711, topic_generation/database_client.py:553, (also conversation_generation per project memory)
- Problem: all four re-implement `prompt_templates` select (is_active + order version desc + limit 1) with different behavior on miss (raise / English fallback / None), different returned shape (text vs config incl. model/provider/version), and different caching. Judge `_cfg_cache` dicts add a 5th layer with no invalidation (see next).
- Fix: have the two DB-client methods delegate to prompt_service with an explicit `fallback_language` parameter.

### [MEDIUM] Judge config caches never expire; keyed inconsistently
- Category: correctness
- Location: judges/*.py `_cfg_cache` (cloze.py:174 keyed (task,lang); particle/l1/p1/translation/answer_entailment/distractor_plausibility keyed by lang only; relation.py:317 keyed (pt_name,lang))
- Problem: module-level dict, no TTL/version check. A prompt version bump, model-slug rotation or is_active toggle (the exact failure model_health.py exists for) is not seen by a long-lived process (APScheduler/web worker) until restart, and a cached cfg for a dead slug keeps failing open. Also a `get_template_config` exception is not cached, so a missing template costs one DB roundtrip per item.
- Fix: put one cache (TTL ~60s) in prompt_service and delete the ten copies.

### [MEDIUM] Judge scaffolding duplicated across ~10 files
- Category: redundancy
- Location: judges/{cloze,l1_distractor,particle,collocation,relation,translation_uniqueness,p1_sentences,sentence_validity,distractor_plausibility,answer_entailment}.py
- Problem: each re-implements `_load_cfg`/`_cfg_cache`, `_LANG_ID_TO_CODE`, template-load try/except, numbered-list prompt building, `call_llm`+non-dict check, index read, `_failopen`/`_all_keep`/`_empty_result`/`_empty_meta`. cloze.py and l1_distractor.py are near byte-identical (`_load_cfg`, `_empty_result`, `_all_keep`). Fix to guards (above) must be applied 10 times.
- Fix: a `run_numbered_judge(db, task, lang, build_prompt, parse)` helper in judges/base.py.

### [MEDIUM] Topic-generation BaseAgent bypasses llm_service.call_llm (no llm_calls row, own retry, own JSON parser)
- Category: redundancy
- Location: services/topic_generation/agents/base.py:60-135, explorer.py:207-241, gatekeeper.py:75
- Problem: raw `client.chat.completions.create` with tenacity `retry_if_exception_type(Exception)` x3 (retries non-transient 4xx/ValueError too), plus Explorer's own 3-attempt loop (up to 9 calls per tier), no cost/`cost_usd` logging so topic-gen spend never reaches the llm_calls budget tables, no `usage:{include:true}`, hand-rolled fence-stripping JSON extractor duplicating llm_service. `json_mode=True` sends `response_format=json_object` straight to the configured model (the documented Qwen/Seed 400 landmine if TOPIC_LLM_MODEL is switched).
- Fix: route `_call_llm` through `services.llm_service.call_llm` (pipeline='topic_gen') and delete the tenacity/parse copies.

### [MEDIUM] Gatekeeper fails closed per-candidate with no outage detection
- Category: correctness
- Location: services/topic_generation/agents/gatekeeper.py:75-100
- Problem: any LLM exception returns False (reject) and only bumps `rejection_count`; with a dead slug every candidate is silently "rejected" and a run yields 0 topics with INFO-level output, indistinguishable from content rejection. `_parse_decision` also rejects any answer starting with neither word if it contains "no" as a substring ("know", "note", "not").
- Fix: re-raise after N consecutive transport errors; parse with a word-boundary regex or json.

### [MEDIUM] Slug collision risk in concurrent batch generation
- Category: correctness
- Location: services/test_generation/database_client.py:1008-1036; orchestrator.py:630, 1748
- Problem: slug = `{lang}-d{difficulty}-{topic[:30]}-{YYYYmmddHHMMSS}`; `_generate_one` cycles `i % len(queue_items)` and `batch_test_workers > 1`, so same topic+tier in the same second yields a duplicate slug (also R2 key `slug.mp3` overwrite). A CJK `topic_concept` slugifies to '' giving `zh-d1--<ts>`. PLAUSIBLE (depends on unique constraint on tests.slug and workers>1 config).
- Fix: append a short uuid4 suffix.

### [MEDIUM] Dead generator modules (~770 lines) and dead legacy exercise pipeline
- Category: legacy/dead
- Location: services/exercise_generation/generators/{cloze,context_spectrum,jumbled_sentence,semantic,spot_incorrect,timed_speed_round,translation}.py
- Problem: none are imported by orchestrator.py (only flashcard, collocation, verb_noun_match are) or by any script; only generators/cloze.py is referenced, solely by tests/test_cloze_generator.py and comments in apply_task733/734 scripts. `cloze_judge.py` is a compat shim whose stated caller (`generators.cloze`) is itself dead. Vocabulary source is retired (orchestrator.py:21-35) so the remaining live surface is collocation only.
- Fix: delete (or move to archive/) with their tests; keep cloze_judge shim until exercise_renderer/run_exercise_gen_eval import `judges.cloze` directly.

### [MEDIUM] CLI entry point calls undefined run_grammar_batch
- Category: legacy/dead
- Location: services/exercise_generation/run_exercise_generation.py:136-146
- Problem: `--source grammar` is still an argparse choice and calls `run_grammar_batch`, which does not exist (grammar archived 2026-09-21) -> NameError. Also module calls `logging.basicConfig(level=INFO)` at import (line 7), reconfiguring root logging for anything importing `run_vocabulary_batch`.
- Fix: drop the grammar branch/choice and move basicConfig under `__main__`.

### [LOW] Unreferenced functions
- Category: legacy/dead
- Location: exercise_generation/base_generator.py:152 batch_insert; language_processor.py:29 matches_pattern, :77 merge_short_chunks; judges/particle.py:113 judge_particle; judges/relation.py:198 judge_derivation; generators/semantic.py:150 OddOneOutGenerator; test_generation/database_client.py:959 get_config_value; test_generation/difficulty_scorer.py:109 as_dict; agents/audio_synthesizer.py:253 generate_speed_variants, :321 check_audio_exists; agents/question_validator.py:250 fix_question; agents/title_generator.py:146 _clean_response; topic_generation/config.py:218 get_topic_gen_config; topic_generation/database_client.py:181 get_lens_by_code, :214 get_language_by_code; agents/archivist.py:45 get_lens_by_id, :175 batch_check_novelty; agents/gatekeeper.py:182 reset_counts
- Problem: zero references repo-wide (git grep -w incl. scripts/tests; one-word-match counts only the definition). `judge_particle`/`judge_derivation` are described as "for admin tools/planted-defect test" - confirm before deleting.
- Fix: remove after a final grep; keep documented admin helpers.

### [LOW] Two config singletons in topic_generation
- Category: maintainability
- Location: services/topic_generation/config.py:218-227
- Problem: `get_topic_gen_config()` (lazy, comment says "lazily evaluated") is unused; everything imports the eagerly built `topic_gen_config = TopicGenConfig()`, reading env at import time and emitting key warnings on any import of the package.
- Fix: delete the unused getter or make the module attribute the getter.

### [LOW] Legacy inline prompt fallbacks that the live path can no longer reach
- Category: legacy/dead
- Location: test_generation/agents/question_generator.py:69-... (QUESTION_TYPE_PROMPTS) and :485-492,532 (_build_question_prompt); prose_writer.py:146 _build_default_prompt; title_generator.py:106
- Problem: orchestrator always passes a DB template and `get_prompt_template(required=True)` raises on a missing row ("no silent fallback"), so the English inline fallbacks only matter to smoke scripts, and they contradict the stated policy (a caller passing `prompt_template=None` silently gets an English-only prompt for any language).
- Fix: make `prompt_template` required and delete the inline builders.

### [LOW] Per-judge Likert-vs-probability dual scales and permanently-default-off flag
- Category: legacy/dead
- Location: judges/base.py:97-130 (classify, THRESHOLD_ACCEPT/REJECT; one caller judges/cloze.py), test_generation/orchestrator.py:150-175 (`JUDGE_SUBJECT_KEYWORDS`)
- Problem: `classify` is marked LEGACY "do not add callers" with a documented scale-inversion hazard; cloze judge still the sole 0-1 judge. `_subject_kwargs` is gated by an env var that defaults off (and is only exercised by tests and measure_judge_flag_rate.py), so the keyword plumbing through question_generator/_apply_judges is inert in prod.
- Fix: convert cloze to Likert (as base.py already plans) and delete classify; delete or hard-enable the subject-keyword path once the gold set decides.

### [LOW] exercise_generation/llm_client.py hardcodes temperature 0.7 and a 30s timeout for hosted calls
- Category: maintainability
- Location: services/exercise_generation/llm_client.py:55-64
- Problem: thin wrapper that pins temperature=0.7 for all generator callers (no override parameter), and duplicates the claude_cli provider detection in llm_service; the `json_object` landmine is untouched here because callers pass `'json'` (safe).
- Fix: expose temperature; take the cli-timeout rule from llm_service.

### [LOW] Gatekeeper/Explorer model not sourced from prompt_templates
- Category: maintainability
- Location: services/topic_generation/config.py:125-126, agents/explorer.py:33-37
- Problem: model is `TOPIC_LLM_MODEL` env/default (comment admits the DB rows have model NULL) while every other pipeline is "prompt_templates is the single source of truth"; slug rotation (model_health.py) must be remembered separately for this one.
- Fix: read model/provider via `get_template_config` like the rest.
