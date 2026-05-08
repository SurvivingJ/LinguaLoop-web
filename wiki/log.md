# Activity Log

## 2026-05-08 fix | First-attempt gating in ExerciseSessionService.record_attempt_with_updates

Source: Remaining gap #2 in `wiki/algorithms/bkt-implementation-analysis.md` ("First-Attempt Gating Inconsistency"). Non-ladder exercise attempts called `update_from_word_test()` on every retry, double-counting BKT evidence and inflating `p_known` on second/third attempts at the same exercise. The ladder service (`LadderService.record_attempt()`) already gated BKT on `is_first_attempt`, but the daily-session path didn't.

**Files updated: 3**
- `services/exercise_session_service.py` — In `record_attempt_with_updates()`, added a `(user_id, exercise_id)` existence check against `exercise_attempts` *before* inserting the new attempt row to derive `is_first_attempt` server-side (no client trust). The BKT call (`VocabularyKnowledgeService.update_from_word_test`) is now wrapped in `if is_first_attempt:` so retries no longer apply the Bayesian update. The attempt insert, exercise stats counters (`attempt_count`/`correct_count`), and FSRS scheduling (`_update_fsrs_for_exercise`) all still run on every attempt — FSRS reviews are legitimate scheduling signals on retries even when BKT shouldn't compound. The `is_first_attempt` flag is included in the response payload so callers/telemetry can observe gating.
- `wiki/algorithms/bkt-implementation-analysis.md` — Removed gap #2 from "Remaining Gaps"; renumbered the remaining gap (Data-Driven Parameter Calibration) #2 → #2; flipped the "First-attempt gating fix" row in the Implementation History table from ❌ TODO → ✅ Done with updated impact note.
- `wiki/algorithms/bkt-implementation-analysis.tech.md` — Replaced the "Remaining observation" paragraph in *Exercises → BKT* with a "Phase 7 fix — First-attempt gating" paragraph describing the server-side derivation and the FSRS-still-runs-on-retries semantics. Flipped section 7 ("First-Attempt Gating Consistency") from ❌ NOT YET IMPLEMENTED → ✅ IMPLEMENTED with a paragraph documenting the existence-check approach and noting the response payload now exposes the flag.

Notes: Chose server-side derivation over a `is_first_attempt` request parameter (which is what the ladder route uses) because (a) it doesn't require frontend changes, (b) it can't be spoofed, and (c) it correctly classifies retries that span page reloads. The cost is one extra SELECT per attempt, which is a single indexed lookup on `(user_id, exercise_id)`. The ladder route trusts client-supplied `is_first_attempt` because the ladder UI controls retry semantics tightly via the SQL RPC; the daily-session UI does not.

Verification:
1. Submit a new exercise attempt for a vocabulary exercise the user has never seen → response includes `is_first_attempt: true` and `bkt_update` populated.
2. Submit again with the same `exercise_id` → response includes `is_first_attempt: false` and no `bkt_update` field.
3. `SELECT p_known FROM user_vocabulary_knowledge` for the affected sense should not move on the second submission.
4. FSRS scheduling on `user_flashcards` should still update on the second submission (stability/difficulty/due_date change).

---

## 2026-05-08 fix | Wire up ELO volatility and exclude attempted tests in single rec

Source: Priorities 1 and 2 of `wiki/algorithms/elo-implementation-analysis.md`. Both fixes already existed in `migrations/phase3_rpc_fixes.sql` (sections 3.1 and 3.2, dated 2026-04-12) but were never applied to the live database — verified by reading `db_schema_live.sql` and confirming the V2 inlined ELO and the missing `NOT EXISTS` were both still present, alongside four other unapplied phase3 changes. To avoid pulling unrelated phase3 changes into scope, the two relevant rewrites were extracted into a fresh, narrowly-scoped migration.

**Files created: 1**
- `migrations/wire_volatility_and_exclude_attempted.sql` — Two `CREATE OR REPLACE FUNCTION` blocks. First, `process_test_submission()` replaces the V2 inlined ELO math with calls to the existing `calculate_volatility_multiplier()` and `calculate_elo_rating()` helpers — restoring user-side volatility (1.5x for <10 tests, +0.5x for >90 days inactive) and asymmetric K-factors (32 user / 16 test). Diverges from V1 by hardcoding test volatility to 1.0; tests don't go rusty so the inactivity branch of the multiplier doesn't apply, and the new-test branch is more cleanly handled by the difficulty-seeded backfill. Second, `get_recommended_test()` adds an `AND NOT EXISTS (SELECT 1 FROM test_attempts ta WHERE ta.user_id = p_user_id AND ta.test_id = t.id)` inside the expanding-radius `WHERE`, matching the behaviour of `get_recommended_tests()`. If the user has exhausted all tests in the language, the function returns nothing and the existing `/api/tests/random` 404 path serves clean degradation. Idempotent (`CREATE OR REPLACE`); no signature changes; no Python or service-layer edits required.

**Files updated: 3**
- `wiki/algorithms/elo-implementation-analysis.md` — Removed the two fixed gaps from the "Other Discrepancies" table; replaced "Critical Finding: Volatility Intentionally Removed in V2" header with "Volatility: Removed in V2, Restored in V3 (2026-05-08)" and added a paragraph describing what V3 actually does; added a "Recently Fixed (2026-05-08)" section above "What Needs Improvement" pointing at the new migration; deleted Priority 1 and Priority 2; renumbered remaining priorities 3-6 → 1-4; struck the two completed rows from the Quantitative Impact Assessment table; bumped `last_updated` to 2026-05-08; removed the now-resolved volatility-integration question from `open_questions` (the question of *whether* volatility belongs in `process_test_submission` is now answered by V3 having shipped).
- `wiki/algorithms/elo-implementation-analysis.tech.md` — Updated the architecture map to show the new helper-call sequence in place of the `◄── BUG` annotation; renamed "Migration History: V1 → V2" to "V1 → V2 → V3" and added a V3 section with the new code block plus a paragraph explaining the principled deviation from V1 (test volatility hardcoded to 1.0 because tests don't go rusty); deleted the now-applied "Fix: Re-enable Volatility" code block; flipped the "Excludes attempted" row in the recommendation comparison table from "**No**" to "Yes (V3)"; replaced the "Issues" list under `get_recommended_test` with a "V3" applied callout plus the three remaining issues; replaced the "Single-Recommendation Fix" code block under "Proposed Improvements" with a strikethrough pointing back at the V3 section; bumped `last_updated`.
- `wiki/log.md` — This entry.

Notes: The other four phase3 fixes (`can_use_free_test` actual-usage check, `get_token_balance` real lookup, `update_skill_attempts_count` COUNT(*) → increment, `get_distractors` SECURITY DEFINER + auth check) remain unapplied. The 2026-04-15 wiki log entry described them as synced because the *wiki was* updated to match the migration file's intent — but the migration itself never ran against Supabase. Each of those is a real fix that's worth picking up; left out here to keep this scope narrow.

Verification (deferred until migration is applied via Supabase MCP `apply_migration`):
1. New-user submission produces ~1.5× the ELO swing of an established user for an identical result (user K=32 × volatility 1.5 = effective 48; baseline V2 was 32). Confirm via `SELECT user_elo_after - user_elo_before FROM test_attempts ORDER BY created_at DESC LIMIT 1`.
2. Test ELO change is roughly half the magnitude of the user change (K=16 vs K=32 × volatility), opposite sign.
3. `SELECT * FROM get_recommended_test(<uuid>, <lang_id>);` repeated calls never return a test the user has attempted.
4. Sanity: `SELECT calculate_volatility_multiplier(5, NULL, 1.0);` → 1.5; `SELECT calculate_volatility_multiplier(50, CURRENT_DATE, 1.0);` → 1.0.

---

## 2026-05-07 sync | Wiki/code reconciliation — Model Arena documented; pinyin-trainer updated for scoring + tone-mark changes

Source: Codebase survey requested after the brand and theming work. Compared `git log` and the actual `services/` and `templates/` trees against the wiki and identified two material divergences: a complete subsystem (`services/model_arena/`, `routes/model_arena.py`) had no wiki page, and the pinyin-trainer pages were stale relative to two commits (`d056a169` scoring fix, `0a46c254` tone-mark rendering).

**Files created: 2**
- `wiki/features/model-arena.md` — Prose page describing the admin/operator tool that runs blind head-to-head OpenRouter model comparisons across prose generation and comprehension question generation, with a judge model scoring contestants on strict rubrics. Captures the operator workflow, business rules (admin-only, OpenRouter-only, no automatic feedback into production routing), and open questions (statistical significance estimation, automatic vs manual model swap, expansion to vocab-pipeline tasks).
- `wiki/features/model-arena.tech.md` — Technical specification covering the 6-file `services/model_arena/` module layout, the dataclass surface (`ArenaConfig`, `JudgeScores`, `TrialResult`, `ArenaResults`), the four-endpoint blueprint at `routes/model_arena.py` (`/api/models`, `/api/run/arena`, `/<id>/status|stop|results`), trial-execution detail for both prose and questions modes (including the rationale for having the judge model write the shared prose for questions trials), persistence to `data/arena_runs/{arena_id}.json`, OpenRouter pricing integration with 1h cache, and five key architectural decisions (blind-relabelled per-trial shuffle, judge-writes-shared-prose, OpenRouter-as-unified-provider, cooperative-cancel via `stop_check`, fixed temperatures matching production).

**Files updated: 3**
- `wiki/features/pinyin-trainer.md` — Bumped last-updated to 2026-05-07. Tightened the *How It Works* step that describes pinyin reveal to mention the precomposed tone marks. Replaced the *Accuracy-based scoring* edge-case bullet with an *Error-penalised accuracy* bullet that documents the new formula `(total − errors) / total` and explains why the old `correct_count / total` calc always returned 100% (wrong answers retry in place).
- `wiki/features/pinyin-trainer.tech.md` — Bumped last-updated. Rewrote the `submit-pinyin` *Arguments* section to clarify that `correct_chars` is now the client-encoded `max(0, total - error_count)`, not `state.correctCount`. Replaced the bare *Rendering* sub-bullet about pinyin with a full *Tone-mark rendering* subsection documenting the `applyToneMark(syllable, tone)` algorithm — its precomposed-glyph table for ā/á/ǎ/à and the ü family, its vowel-priority rules (a > e > o-of-ou > rightmost vowel), and why the precomposed approach replaced the previous appended-combining-diacritic path. Added a *Recent Changes (2026-05-06 → 07)* section anchoring both fixes to their commits.
- `wiki/index.md` — Added `[[features/model-arena]]` and `[[features/model-arena.tech]]` under the Features section. Bumped page count 45 → 47.

Notes: No code changes in this entry — wiki-only sync. The `services/model_arena/` subsystem itself was introduced in commit `778972dd` ("Exercise generation upgrades; library scanning upgrades") on the same day as the prompt-template and L5/L8 work but had not been written up. The pinyin-trainer changes shipped in `0a46c254` (tone marks) and `d056a169` (scoring), both predating the most recent wiki update of those pages — the prose page `last_updated` was 2026-04-21, so roughly two weeks of drift was reconciled.

Out-of-scope (flagged):
- The `Portal/Library/`, `Portal/MathDojo/`, `Portal/MusicDojo/`, `Portal/hub/` sibling apps under `linguadojo.com` are not part of the WebApp wiki's scope. They surface in the git log (commits about "library functionality", "music dojo improv gen", etc.) but live outside `WebApp/`. If the wiki is ever expanded to cover the full `linguadojo.com` portfolio, those would need their own documentation root rather than being wedged into the language-learning app's wiki.
- The earlier `git status` working-tree changes to `services/vocabulary_ladder/config.py`, `services/vocabulary_ladder/validators.py`, and `wiki/features/exercise-generation-prompts.md` were already covered by the 2026-05-07 Chinese-vocab-prompt-seed entry below; no further sync needed.
- Two known stale areas were noted but **not** updated in this pass because the underlying code questions are still open: the master tasklist (still shows 0 tasks because language-packs design is blocked), and the three implementation-analysis docs (ELO / BKT / ladder) which document gaps that haven't been closed yet — the analyses are correct as-is.

---

## 2026-05-07 decision | Brand name reconciled: LinguaDojo (camel-case)

Source: Brand-architect interrogation session. Surfaced a long-standing inconsistency — the wiki documentation and `CLAUDE.md` refer to the project as `LinguaLoop`, while the production codebase has been using `LinguaDojo` (camel-case) throughout: page titles, logo wordmark, the `window.LINGUADOJO` global, all four locales of i18n strings, production subdomains (`audio.linguadojo.com`, `library.linguadojo.com`, etc.), and the R2 audio bucket. The Project Knowledge corpus explicitly noted "Product Name: LinguaDojo (formerly LinguaLoop)" but no formal ADR captured the decision. This entry records the reconciliation and locks the casing as `LinguaDojo`.

The session also produced an alternative-name research pass over ~20 etymologically-rich candidates surfacing 7 with credible domain availability (Stoa, Caesura, Verbarium, Fermata, Hapax, Refrain, Phrasis). None were adopted; the existing `LinguaDojo` brand was kept. The exploration is archived in the ADR for historical reference rather than as a recommendation.

**Files created: 1**
- `wiki/decisions/ADR-004-brand-name.md` — Records the formal adoption of `LinguaDojo` as canonical brand text, documents the codebase reality that informed it, and archives the seven considered alternatives with full etymology and domain-status notes plus the ~20-entry eliminated-candidate appendix.

**Files updated: 1**
- `wiki/index.md` — Added ADR-004 to the Decisions section; bumped page count 44 → 45 and last-updated to 2026-05-07.

Notes: Brand-text only. The wiki and `CLAUDE.md` continue to say "LinguaLoop" — those references are not retroactively renamed by this entry. The accompanying brand brief (palette: Inkstone & Vermilion; typography: IBM Plex family; web architecture: vanilla HTML/CSS/JS over Flask) lives in the planning artifact at `~/.claude/plans/role-objective-you-happy-panda.md` and is reference material — not implemented as part of this entry.

---

## 2026-05-07 fix | Reframe English L1 in vocab_prompt2_exercises as listening-only (v3)

Source: While analysing whether the Chinese-side decisions reverse-applied to English, surfaced that English L1 had the same framing problem the Chinese seeding fixed — the prompt instructed the LLM to pick "form-similar" distractors (Levenshtein, first/last letter) for an exercise the renderer ([services/vocabulary_ladder/exercise_renderer.py:155](../../services/vocabulary_ladder/exercise_renderer.py#L155)) actually plays as audio-then-MCQ. Visual lookalikes test the wrong skill: "tough" / "though" look identical and sound completely different.

**Files created: 1**
- `migrations/reframe_english_l1_listening.sql` — Deactivates `vocab_prompt2_exercises` v2 for `language_id=2` and inserts v3. v3 swaps the L1 block for "Listening Recognition" with phonetic-only distractor types (homophones, near-homophones, minimal pairs, mishear-able rhymes) and an explicit anti-rule against visual-similarity distractors. L3, L5, L6, the global rules, and the output schema are byte-identical to v2. Model unchanged: `anthropic/claude-opus-4-7`.

**Files updated: 1**
- `wiki/features/exercise-generation-prompts.md` — Bumped EN P2 from v2 to v3 in the deployment table; rewrote the cross-cutting "Stronger L1 distractor rules" summary bullet to describe listening-only distractor families; updated both L1 verbatim blocks (the v2 design-intent section is renamed to v3 active and given a v3-vs-v2 changelog header; the legacy v1 section is correctly marked deactivated).

Notes: This is a behavioural change for English vocab generation but not a schema change — only the prompt text differs. Existing word_assets generated under v2 are untouched; future generations use v3. Pairs symmetrically with the Chinese P2 v1 deployed earlier today (which restricts CN L1 distractors to tonal confusables, the Mandarin manifestation of the same audio-confusable principle).

Out-of-scope (flagged):
- Regenerating existing English word_assets to take advantage of the listening reframe — operator decision; v3 will apply to all new generations automatically.
- The English TTS pipeline that L1 actually consumes — already deployed and working for English (uses OpenAI TTS via `dim_languages.tts_voice_ids`); only Chinese still lacks a TTS renderer.

---

## 2026-05-07 feature | Seed Chinese vocab pipeline prompt templates (language_id=1)

Source: Generation for sense 20125 (起来) errored with `No active prompt_templates row for task_name='vocab_prompt1_core' language_id=1`. The 2026-05-05 refactor noted this as out-of-scope follow-up; this entry resolves it.

**Files created: 1**
- `migrations/seed_chinese_vocab_prompts.sql` — Inserts v1 of `vocab_prompt1_core`, `vocab_prompt2_exercises`, `vocab_prompt3_transforms` for `language_id=1`. All three rows have `model`/`provider` set at insert time. Uses `$PROMPT$…$PROMPT$` dollar-quoting and `ON CONFLICT (task_name, language_id, version) DO NOTHING` for idempotency.

**Files updated: 3**
- `services/vocabulary_ladder/validators.py` — Extended `VALID_POS` and `VALID_SEMANTIC_CLASSES` to allow Chinese enum values (名词/动词/具体名词/抽象名词/etc.); rewrote `contains_target_whole_word` to fall back to substring presence for non-ASCII targets, since `\b` regex doesn't yield word boundaries between Hanzi.
- `services/vocabulary_ladder/config.py` — Extended `COLLOCATION_SKIP_CLASSES` to recognise `具体名词` alongside `concrete_noun` so the L5/L8 skip gate works for Chinese (academic since `corpus_collocations` is empty for Chinese, but consistent with the data model).
- `wiki/features/exercise-generation-prompts.md` — Added a Chinese row to the deployment table; updated the open-questions list to lift the CN-absent question, flag JP-still-absent and Chinese-TTS-still-required, and noted the validators.py dependency.

**Design decisions** (captured during planning interview):
- L4 reinterpreted as compound-completion slot (Chinese has no inflectional morphology, so the English morphology-slot frame doesn't translate).
- L1 distractors restricted to tonal confusables (same syllable, different tones — e.g. 妈/麻/马/骂 for monosyllabic targets, or one-syllable-tone-shift for disyllabic targets like 起来).
- Sentence-length caps measured in Hanzi characters: T1:10, T2:16, T3:22, T4:30, T5:40, T6:no cap.
- Substring rule: sense-match — target characters must appear contiguously AND with the locked sense (replaces the English "whole word" rule that doesn't apply to a script without word boundaries).
- L6/L7 error categories: wrong measure word, misplaced aspect particle (了/着/过), word-order errors, misused directional/resultative complement.
- All learner-facing fields and enum values in Chinese (no English in the prompt body except `{curly-brace variables}`, `JSON`, and `.md`).
- Models: Qwen family — `qwen/qwen-2.5-72b-instruct` for P1 (cheaper, runs more often), `qwen/qwen-max` for P2/P3 (more nuanced distractor / error generation).

Notes: Chinese L5/L8 will silently skip for every word until `corpus_collocations` is populated for `language_id=1` — the PMI gate at `asset_pipeline.py:102-109` handles this naturally. Chinese L1 listening exercises will render but cannot actually play audio until a Chinese TTS pipeline ships (P1's `pronunciation` field stores the pinyin, but no renderer consumes it yet). Both items are documented as open follow-ups in the feature page.

Out-of-scope (flagged):
- Japanese (`language_id=3`) seeds — same shape but distinct grammar / kana mixing / keigo register; defer.
- Chinese TTS pipeline for L1 listening exercises — most pressing follow-up.
- Populating `corpus_collocations` for Chinese to enable L5/L8.
- Iteration on the prompts after observing real Qwen output for 起来 — particles are an unusually hard test case.

---

## 2026-05-05 refactor | Centralise model+provider on prompt_templates; retire dim_languages model columns

Source: Today's hotfix surfaced a structural problem — `prompt_templates.model`/`.provider` weren't tracked in source migrations and several rows had NULL values, while a parallel set of `dim_languages.*_model` columns held the same routing information for non-vocab features. Two sources of truth that drifted apart silently.

**Files created: 2**
- `migrations/promote_prompt_templates_model_columns.sql` — `ADD COLUMN IF NOT EXISTS model text` + `ADD COLUMN IF NOT EXISTS provider text DEFAULT 'openrouter'` on `prompt_templates`. Then a series of idempotent `UPDATE`s that backfill model/provider on every active row across all 7 task families: vocab pipeline (P1 v4 / P2 v2 / P3 v2), test generation (`prose_generation` + 6 question types), conversation pipeline (5 tasks), legacy exercise generation (12 tasks), mystery (split: `mystery_plot`/`mystery_scene` → Sonnet, `mystery_question`/`mystery_clue`/`mystery_deduction` → Flash Lite), and `vocab_phrase_detection`. All idempotent via `WHERE model IS NULL OR provider IS NULL`. After applying, `prompt_templates.model` is the single source of truth.
- `migrations/drop_dim_languages_model_columns.sql` — Drops all eight `*_model` columns from `dim_languages` plus the dead `language_model_config` table (created by phase4 but never read by any code). Apply only after the code refactor below has shipped.

**Files updated: 5**
- `services/conversation_generation/database_client.py` — `get_conversation_model` now looks up `conversation_generation` via `get_template_config` instead of reading `dim_languages.conversation_model`.
- `services/mystery_generation/orchestrator.py` — Removed `prose_model` / `question_model` lookups. `generate()` now resolves five per-task models at the top (`mystery_plot`, `mystery_scene`, `mystery_question`, `mystery_clue`, `mystery_deduction`) and passes them individually to each agent. The clue designer specifically moves from prose-tier to Flash Lite per the new task→model split. `generation_model` stored on the mystery row is `plot_model`.
- `services/exercise_generation/orchestrator.py` — `_load_models` no longer SELECTs from `dim_languages`. Picks representative tasks (`cloze_distractor_generation` for the exercise model, `exercise_sentence_generation` for the sentence model) and reads from `prompt_templates.model`.
- `services/test_generation/database_client.py` — Added `_resolve_models` helper that queries `prose_generation` and `question_literal_detail` via `get_template_config`. Both `get_language_config` and `get_language_config_by_code` now call it instead of reading the old columns. The `LanguageConfig` dataclass surface is unchanged, so test_generation/orchestrator.py and the scripts (`run_test_generation.py`, `validate_sense_languages.py`, `backfill_token_maps.py`, `backfill_vocab.py`) work transparently.
- `services/vocabulary/pipeline.py` — Phrase-detection model now comes from the `vocab_phrase_detection` task via `get_template_config` rather than `lang_config.prose_model`.

**Pages updated: 2**
- `features/exercise-generation-prompts.md` — Added `services/prompt_service.py` to dependencies; bumped date.
- `log.md` — This entry.

Notes: Apply order matters — `promote_prompt_templates_model_columns.sql` first (idempotent backfill), then deploy the Python, then `drop_dim_languages_model_columns.sql`. Reversing the order would leave the non-vocab features without a model lookup. Mystery model split is per a product decision recorded in the plan file.

Out-of-scope (flagged for follow-up):
- `vocab_prompt{1,2,3}_*` rows for `language_id` 1 (Chinese) and 3 (Japanese) still don't exist. Today's `No active prompt_templates row for task_name='vocab_prompt1_core' language_id=1` error is unblocked by this refactor only insofar as the existing English row now has model/provider set; CN/JP need translated templates seeded separately.
- The dead `language_model_config` table is dropped in Step 4. Phase 4's intent (centralise on a normalised lookup table) is now realised, but with `prompt_templates.model` rather than a separate config table.

---

## 2026-05-03 hotfix | Backfill model/provider on vocab_prompt1_core v4

Source: Pipeline run on sense 19853 errored with `prompt_templates row for 'vocab_prompt1_core'/lang=2 v4 has no model configured.`

**Files created: 1**
- `migrations/fix_v4_model_provider.sql` — Idempotent UPDATE that sets `model = 'google/gemini-2.5-flash-lite'`, `provider = 'openrouter'` on the v4 row when those columns are NULL. Matches the model/provider that v3 was running with so the swap is behaviorally identical.

**Files updated: 1**
- `migrations/restrict_l5_and_lock_l8_sentence.sql` — Amended the INSERT to populate `model` and `provider` columns at insert time, and appended an idempotent UPDATE block so a re-apply (or a partial-apply state) self-heals.

Notes: The `model`/`provider` columns on `public.prompt_templates` are not defined in any tracked migration in this repo — they were added directly in Supabase. Existing rows like P1 v3 / P2 v2 / P3 v2 had them populated manually after their initial INSERT. My v4 INSERT in `restrict_l5_and_lock_l8_sentence.sql` didn't include them so they defaulted to NULL, and `services/prompt_service.get_template_config` raises a fail-fast `RuntimeError` on a NULL model. Future prompt-template migrations must remember to set both columns at INSERT time.

---

## 2026-05-03 fix | L5/L8 quality + P3 robustness + RPC auth

Source: Pipeline run on sense 19851 ("personalize") surfaced four issues simultaneously — junk L5 distractors (synonym soup), L8 skipped twice, P3 JSON parse failure killing the whole P3 response, and `get_distractors` RPC raising `Authentication required` from the admin pipeline.

**Files created: 2**
- `migrations/restrict_l5_and_lock_l8_sentence.sql` — Deactivates `vocab_prompt1_core` v3 and inserts v4. Rule 7 tightened: return `primary_collocate` only for fixed lexical collocations, with the "personalize" → "advertising" example called out as a negative case. Rule 14 (new): if `primary_collocate` is non-null, at least one of the 10 sentences must contain it as a whole word, so L8 always has a viable anchor sentence.
- `migrations/get_distractors_drop_auth_check.sql` — `CREATE OR REPLACE FUNCTION` removing the `IF auth.uid() IS NULL THEN RAISE` block. Service-role calls (admin pipeline) and authenticated user calls both pass now; definitions are non-sensitive public data.

**Files updated: 3**
- `services/vocabulary_ladder/asset_generators/prompt3_transforms.py`:
  - **P0 fix (regression):** `_remap_level_4` and `_remap_level_8` now read the options array from sub-key `"1"` when it's a list. The v2 template puts options there; the existing remap only handled `data['options']` and per-index dict shapes, so every L4/L8 since the v2 deploy was silently returning empty options. This explains the `"Level 4: expected 4 options, got 0"` validator error.
  - **P2:** new `_pick_l8_sentence_index` scans all 10 sentences for one containing the collocate as a whole word, preferring the variant's positional default. `generate()` builds an `effective_assignments` copy that hands the picked index to both `_build_prompt` and `_remap_output` so the rendered exercise points at the correct sentence. `_build_prompt` simplified — picking now happens once at the top of `generate`.
  - **P3.1:** `_call_with_retry` now falls through to `_salvage_from_text` after two strict-JSON failures. Salvage re-calls the LLM in `'text'` mode and uses `json.JSONDecoder.raw_decode` to peel each `"<level>": <value>` pair off independently, so a malformed L4 array no longer prevents L7 from being recovered.
- `services/vocabulary_ladder/asset_pipeline.py`:
  - **P1 pipeline gate:** `generate_for_sense` now drops level 5 from `active_levels` unless `corpus_collocations` has a `pmi_score >= 5.0` row backing the (lemma, collocate) pair (in either head/collocate orientation). Helper `_collocation_is_fixed` plus `_extract_lemma_from_core`. Threshold `L5_PMI_THRESHOLD = 5.0` is a class constant for easy tuning. Default behavior on DB error is to drop L5 (safe-by-default for a quality-sensitive exercise).
- `services/vocabulary_ladder/exercise_renderer.py` — **untouched**; the auth fix is RPC-side.

**Pages updated: 3**
- `features/exercise-generation-prompts.md` — Provenance table promoted to P1 v4; new "P1 v4 changes vs v3" callout; deployment artefacts section lists the two new migrations and the pipeline-side L5 gate; P1 prose body replaced with v4 text (added Rule 7 fixed-collocation criterion + Rule 14 collocate sentence coverage); historical section gained a P1 v3 entry; dependencies now mention `corpus_collocations` and `asset_pipeline.py`.
- `index.md` — Updated link description.
- `log.md` — This entry.

Notes: The headline issue was the silent L4/L8 remap regression — every word generated since the v2 P3 deploy had broken L4 and L8 because the remap didn't match the new template shape. Visible "L5 quality" complaints were a separate but coexisting issue. Both classes of problem are now addressed. P3.2 (flatten the v2 P3 template structure into a P3 v3) is held in reserve — if Sonnet keeps dropping commas inside the nested L4/L8 arrays even after the salvage path catches them, that's the next escalation. P3.3 (split P3 into per-level calls) remains shelved.

---

## 2026-05-03 feature | Vocab pipeline prompt revisions deployed

Source: `migrations/improve_vocab_pipeline_prompts.sql` (new), `services/vocabulary_ladder/config.py`, `services/vocabulary_ladder/asset_generators/prompt{1,2,3}_*.py`.

**Files created: 1**
- `migrations/improve_vocab_pipeline_prompts.sql` — Single transactional migration that deactivates `vocab_prompt1_core` v2, `vocab_prompt2_exercises` v1, `vocab_prompt3_transforms` v1, then inserts P1 v3 / P2 v2 / P3 v2 with the improved templates. Includes `ON CONFLICT (task_name, language_id, version) DO NOTHING` for idempotency and a verification query at the bottom.

**Files updated: 4**
- `services/vocabulary_ladder/config.py` — Extended `PROMPT1_KEY_MAP` with `"10": "register"` and `"11": "sense_fingerprint"` so P1's two new output fields land in `word_assets.content` with descriptive keys.
- `services/vocabulary_ladder/asset_generators/prompt1_core.py` — `_build_prompt` now passes `sense_id` (stringified) and `sense_definition` (mirrors `existing_definition` for now); `generate()` threads `sense_id` to the builder.
- `services/vocabulary_ladder/asset_generators/prompt2_exercises.py` — `generate()` accepts optional `used_distractors: list[str]`; `_build_prompt` passes `register` (default `'neutral'`), `sense_fingerprint`, and `used_distractors_json`.
- `services/vocabulary_ladder/asset_generators/prompt3_transforms.py` — Same plumbing as P2.

**Pages updated: 3**
- `features/exercise-generation-prompts.md` — Promoted "Proposed revisions" to "Active templates"; updated provenance table to show v3/v2 with the new migration; replaced "What needs to happen to deploy" with "Deployment artefacts" pointing to the migration and the four touched code files; rewrote the Template Variables table without the deployed/proposed split (all variables are now plumbed); flipped frontmatter to `status: complete`, bumped `last_updated: 2026-05-03`.
- `index.md` — Refreshed link description and date.
- `log.md` — This entry.

Notes: The improved prompts add tier calibration tables, sense lock + `sense_fingerprint` propagation, register lock, mandatory whole-word substring audit, mixed-L1 guardrail, distractor dedup via `used_distractors_json`, pre-output verification, stronger L1 form-similar distractor rules, and an L8 anti-substitution test. The migration is idempotent — re-running it is a no-op once the v3/v2 rows exist. `used_distractors` defaults to `[]` from the orchestrator; cross-variant dedup is a follow-up.

---

## 2026-05-02 update | Proposed v3/v2 prompt revisions

Source: User-supplied improved prompts adding tier calibration tables, sense lock, register lock, mixed-L1 guardrails, substring/whole-word audit, distractor dedup, and pre-output verification.

**Pages updated: 2**
- `features/exercise-generation-prompts.md` — Added "Proposed revisions" section with full text of P1 v3, P2 v2, P3 v2; called out templating mechanism (custom regex renderer, single braces) so the doubled-brace f-string escaping is explicitly inverted; documented new template variables (`{sense_id}`, `{sense_definition}`, `{register}`, `{sense_fingerprint}`, `{used_distractors_json}`) and the deploy-step checklist (migration + generator plumbing + `PROMPT1_KEY_MAP` extension); kept currently-deployed v2/v1 versions below as historical reference.
- `index.md` — Updated link description to mention the proposed revisions.

Notes: The supplied prompts had `{{` `}}` escaping intended for f-string evaluation. Our `services/vocabulary_ladder/asset_generators/_renderer.py` is a regex-only renderer that ignores non-identifier braces, so doubled braces would pass through verbatim and give the LLM malformed JSON literals. All JSON literals in the wiki use single braces accordingly.

---

## 2026-05-02 ingest | Verbatim exercise generation prompts

Source: `migrations/vocabulary_ladder_schema.sql`, `migrations/phase8_momentum_bands.sql`, `services/vocabulary_ladder/asset_generators/prompt{1,2,3}_*.py`, `services/prompt_service.py`.

**Pages created: 1**
- `features/exercise-generation-prompts.md` — Verbatim copies of all three vocabulary-ladder prompt templates (`vocab_prompt1_core` v2 active + v1 deactivated, `vocab_prompt2_exercises` v1 active, `vocab_prompt3_transforms` v1 active). Includes provenance table (task → version → model → migration), template-variable reference, and notes on whole-word L8 sanity check + the unset Chinese/Japanese seeds.

**Pages updated: 2**
- `index.md` — Added new entry under Features; bumped page count 43 → 44; updated date.
- `log.md` — This entry.

Notes: Prompts are not stored in source — they live in `public.prompt_templates` keyed by `(task_name, language_id, version, is_active)` and are loaded at runtime by `prompt_service.get_template_config`. The migrations cited above are the canonical seeders. Only `language_id=2` (English) variants exist; CN/JP seeds remain as an open question.

---

## 2026-04-25 feature | Full Pipeline admin tab

Source: `routes/admin_local.py`, `templates/admin_dashboard.html`, `static/js/admin-dashboard.js`, `scripts/backfill_question_sense_ids.py`.

**Pages updated: 5**
- `overview/project.tech.md` — Rewrote Admin Pipeline Dashboard section: replaced outdated `/admin/vocab` description with full 9-tab dashboard architecture, including endpoint/runner table for all tabs and detailed Full Pipeline step breakdown
- `features/exercises.md` — Added Full Pipeline as generation trigger in Business Rules; corrected Exercise Sources (added conversation + style, removed outdated study_pack)
- `features/exercises.tech.md` — Added Full Pipeline to Architecture Overview diagram; added backfill scripts to Generator Architecture tree; added architectural decision #6 (unified backfill orchestrator)
- `pages/pages-overview.md` — Added `/admin` route with `admin_dashboard.html` template
- `log.md` — This entry

Notes: The Full Pipeline tab is the 9th admin dashboard tab. It orchestrates 6 existing backfill scripts sequentially (vocab → token maps → question sense IDs → skill ratings → exercises → collocations) via `_do_full_pipeline()` in `admin_local.py`. All steps are idempotent with per-step try/except. Also fixed exercises.md which listed an outdated `study_pack` source type instead of the actual `conversation` and `style` source types.

---

## 2026-04-24 update | Style analysis schema added to wiki

Source: `migrations/style_analysis_tables.sql`, `migrations/style_exercise_fk.sql`.

**Pages updated: 3**
- `database/schema.tech.md` — Added 3 tables (`corpus_style_profiles`, `style_pack_items`, `pack_style_items`), added `style_pack_item_id` FK + `chk_source_fk` constraint to `exercises`, added 'style' to `exercise_source_type` enum, updated `collocation_packs.pack_type` CHECK, updated table count 62 → 65
- `features/corpus-analysis.tech.md` — Added style tables to Database Impact section and dependencies
- `wiki/log.md` — This entry

Notes: These tables were created by `style_analysis_tables.sql` (applied after `corpus_analysis_tables.sql`) and `style_exercise_fk.sql` but had never been documented in the wiki. The style exercise generators and orchestrator wiring were also added in this session (see backfill audit).

---

## 2026-04-21 ingest | Pinyin Tone Trainer feature

Source: `migrations/add_pinyin_mode.sql`, `services/pinyin_service.py`, `routes/tests.py`, `templates/test_pinyin.html`, `scripts/batch_generate_pinyin.py`.

**Pages created: 2**
- `features/pinyin-trainer.md` — Prose: Chinese tone-guessing game, sandhi rules, polyphone handling, user flow
- `features/pinyin-trainer.tech.md` — Tech spec: pypinyin pipeline, token schema, submit-pinyin endpoint, batch script, architectural decisions

**Pages updated: 4**
- `database/schema.tech.md` — Added `pinyin_payload` JSONB column to `tests` table; updated `dim_test_types` description to include pinyin
- `database/schema.md` — Updated `dim_test_types` description to include pinyin
- `features/comprehension-tests.md` — Added Pinyin Tones to Test Types list; added cross-reference to pinyin-trainer page
- `index.md` — Added 2 pinyin-trainer pages, page count 41 → 43, updated date

**Key details:**
1. **Chinese-only** test mode using existing test transcripts as source material
2. **Pre-computed pinyin_payload** JSONB on `tests` table — tokenised characters with base/context tones, sandhi rules, word context
3. **Deterministic sandhi engine** — third-tone, yi, bu rules applied via `pinyin_service._apply_sandhi()`
4. **Polyphone handling** — jieba segmentation + 45-char watchlist + optional DeepSeek LLM resolution (batch only)
5. **Reuses `process_test_submission` RPC** with synthetic accuracy-based response for ELO updates
6. **Keyboard arrows + touch swipes** mapped to tone contours (right=T1, up=T2, left=T3, down=T4, tap/space=neutral)
7. **Batch backfill script** (`scripts/batch_generate_pinyin.py`) with --resolve-polyphones and --dry-run flags

---

## 2026-04-16 implementation | Phase 7 BKT improvements

Source: `migrations/phase7_bkt_improvements.sql`, code changes in 5 Python files.

**Pages updated: 7**
- `algorithms/bkt-implementation-analysis.md` — Rewrote "What's Missing" → "What's Been Fixed" for 7 items; updated remaining gaps (3); replaced proposed improvements table with implementation history
- `algorithms/bkt-implementation-analysis.tech.md` — Updated architecture map (transit, lapse penalty, contextual inference, get_session_senses RPC); marked 6 improvements as implemented; updated evidence flow analysis; rewrote BKT↔FSRS interaction as bidirectional
- `features/vocabulary-knowledge.md` — Added decay, contextual inference, frequency inference, transit, lapse penalty to How It Works; updated constraints and business rules
- `features/vocabulary-knowledge.tech.md` — Updated architecture diagram; added full parameter table with transit; added decay model section; added implicit knowledge inference section; added 2 new architectural decisions
- `database/rpcs.tech.md` — Updated 3 existing functions (bkt_update_comprehension +transit, bkt_update_word_test +transit, bkt_update_exercise +transit); replaced 2 Phase 5 functions with Phase 7 versions (bkt_apply_decay 4-param, bkt_effective_p_known 4-param); added 5 new functions (get_session_senses, bkt_apply_lapse_penalty, bkt_infer_from_frequency, bkt_contextual_inference). RPC count 48→53
- `index.md` — Updated BKT page descriptions, RPC counts
- `log.md` — This entry

**Key changes in Phase 7:**
1. **Transit parameter P(T)** added to all 3 BKT update functions (0.02 comprehension, 0.05 recognition, 0.08 recall/nuanced, 0.10 production)
2. **FSRS stability-informed decay** replaces flat 60-day half-life — uses `exp(-days/stability)` with evidence-count-scaled fallback
3. **get_session_senses() RPC** — single SQL function replaces 3 Python fetch methods. All BKT math now in PostgreSQL only
4. **FSRS lapse → BKT penalty** — 20% p_known reduction on FSRS lapse, bridges the reverse FSRS→BKT gap
5. **Frequency-tier inference** — knowing rare words auto-boosts common words with low evidence
6. **Sentence-level contextual inference** — dampened BKT update for untested transcript words (0.30 × score_ratio)
7. **Per-question sense_ids** — questions now link only to vocabulary in their text + choices, not all transcript senses

**Code changes:**
- `migrations/phase7_bkt_improvements.sql` — 9 SQL functions (3 updated, 6 new)
- `services/exercise_session_service.py` — Removed Python decay logic + 3 fetch methods + stability map helper; replaced with single `get_session_senses()` RPC call
- `services/vocabulary/knowledge_service.py` — Added `apply_contextual_inference()`, `_trigger_frequency_inference()`, `apply_lapse_penalty()`
- `services/vocabulary_ladder/ladder_service.py` — Added lapse penalty trigger in `_update_fsrs()`
- `services/test_generation/orchestrator.py` — Fixed per-question sense_ids via `_match_question_senses()`
- `routes/tests.py` — Wired contextual inference after comprehension BKT update

---

## 2026-04-15 ingest | Phase 1-6 SQL migrations sync

Source: `migrations/phase1_quick_wins.sql`, `phase2_schema_cleanup.sql`, `phase3_rpc_fixes.sql`, `phase4_schema_evolution.sql`, `phase5_algorithm_fixes.sql`, `phase6_security_hardening.sql`.

**Pages updated: 7**
- `database/schema.md` — Table count 60→62, RPC count 43→48, RLS count 18→27, removed users_backup, added 3 new tables (user_exercise_history, language_model_config, daily_test_load_items), updated triggers list
- `database/schema.tech.md` — Renamed dim_complexity_tiers PK/sequence, enabled RLS on 8 tables with policies, rewrote user_pack_selections (text→uuid), added 7 columns to user_word_ladder, added 3 full table definitions, fixed FKs (user_reports, app_error_logs), fixed user_exercise_sessions.language_id type, updated triggers and Key Database Functions
- `database/rpcs.tech.md` — Removed 2 dropped RPCs (process_test_submission-old, migrate_test_json), added 7 new functions (bkt_update_exercise, bkt_apply_decay, bkt_effective_p_known, bkt_phase, bkt_phase_thresholds, get_model_for_task, sync_exercise_history), updated 12 existing RPCs (security model changes, parameter fixes, implementation fixes), rebuilt Security Summary (43→48 functions, 19→24 DEFINER)
- `algorithms/elo-ranking.tech.md` — Re-enabled volatility multiplier, asymmetric K-factors (32 user/16 test), get_recommended_test now excludes attempted tests
- `algorithms/bkt-implementation-analysis.tech.md` — Marked 3 improvements as implemented: exercise-type BKT (4 cognitive tiers), temporal decay (60-day half-life), canonical phase thresholds (bkt_phase/bkt_phase_thresholds)
- `algorithms/ladder-implementation-analysis.tech.md` — Updated user_word_ladder DDL (7 new columns), marked user_exercise_history as created, updated Missing From Implementation list, marked 2 improvement proposals as implemented (schema only, Python pending)
- `index.md` — Updated table/RPC counts, last_updated date

**Key changes by phase:**
1. Phase 1: Dropped duplicate trigger, 2 dead RPCs, empty users_backup table; fixed get_prompt_template (language_code→language_id)
2. Phase 2: Rebuilt user_pack_selections with uuid FK; fixed user_reports FK; fixed user_exercise_sessions type; renamed dim_complexity_tiers PK
3. Phase 3: Re-enabled ELO volatility with asymmetric K (32/16); fixed get_recommended_test exclusion; implemented can_use_free_test and get_token_balance; O(1 trigger increments; added auth to get_distractors
4. Phase 4: Extended user_word_ladder (7 columns); created user_exercise_history + trigger; created language_model_config + helper; created daily_test_load_items junction table
5. Phase 5: Created 5 BKT functions (exercise-type params, temporal decay, phase thresholds); added exercise_type param to update_vocabulary_from_word_test
6. Phase 6: Enabled RLS on 8 tables (users, 5 dim tables, app_error_logs); hardened 5 RPCs to SECURITY DEFINER + search_path

---

## 2026-04-11 analysis | ELO, BKT, and Ladder implementation audit

Source: Full codebase analysis — all Python services, SQL RPCs, database schema, exercise generation pipeline.

**Pages created: 6**
- `algorithms/elo-implementation-analysis.md` — ELO prose analysis: volatility bug, recommendation gaps, improvements
- `algorithms/elo-implementation-analysis.tech.md` — ELO technical analysis with fix code and schema proposals
- `algorithms/bkt-implementation-analysis.md` — BKT prose analysis: missing transit, no decay, type-agnostic params
- `algorithms/bkt-implementation-analysis.tech.md` — BKT technical analysis with improvement code
- `algorithms/ladder-implementation-analysis.md` — Ladder prose analysis: 9 vs 10 levels, no demotion, competing session builders
- `algorithms/ladder-implementation-analysis.tech.md` — Ladder technical analysis with consolidation proposals

**Pages updated: 1**
- `index.md` — Added 6 new pages, page count 35 → 41

**Critical findings:**
1. **ELO volatility intentionally removed in V2** — V1 migration called volatility; V2 migration inlined ELO calc without it. K-factor changed from asymmetric (32 user / 16 test) to symmetric 32. Helper functions left in DB but disconnected.
2. **BKT has only 2 of 4 standard parameters** — missing transit P(T) and has no temporal decay. All exercise types use identical slip/guess regardless of cognitive demand.
3. **Ladder has 9 levels, not 10** — Level 10 (Capstone Production) is documented but not implemented. No demotion logic exists. Promotion is immediate on single first-attempt success (designed as 2-session requirement).
4. **Phase threshold inconsistency** — Python session builder uses 0.30/0.55/0.80 thresholds; SQL RPC uses 0.40/0.65/0.80. Same word gets different exercise types depending on code path.
5. **Two competing session builders** — ExerciseSessionService (6-bucket daily) and LadderService (standalone) with different selection logic.
6. **N+1 query pattern** — ExerciseSessionService._select_exercises_for_senses() runs ~40 individual DB queries per session build.
7. **`user_word_progress` table from wiki does not exist** — actual table is `user_word_ladder` with simpler schema.
8. **`user_exercise_history` table from wiki does not exist yet** — anti-repetition uses exercise_attempts scan.
9. ~~**Missing UNIQUE constraints**~~ — CORRECTED: live schema (`db_schema_live.sql`) confirms both `user_skill_ratings` and `test_skill_ratings` DO have UNIQUE constraints on their natural keys. Wiki `schema.tech.md` omitted them.

**Improvement priorities identified (17 total):**
- ELO: wire up volatility (XS), exclude attempted in single rec (XS), vocab-ELO primary (S), adaptive K (M), Glicko-2 (L)
- BKT: exercise-type params (S), temporal decay (M), transit parameter (XS), BKT-FSRS sync (S), data-driven calibration (L)
- Ladder: promotion tracking (M), demotion logic (S), consolidate builders (M), Level 10 capstone (L), anti-repetition (XS), IRT calibration (M), N+1 fix (S), user_exercise_history table (S)

---

## 2026-04-10 bootstrap | Initial wiki creation

Session summary: Full wiki bootstrap from codebase analysis + developer interview.

**Pages created:** 28
- 2 overview pages (project + tech)
- 2 database pages (schema + tech)
- 14 feature pages (7 features x prose + tech)
- 2 algorithm pages (ELO + tech)
- 2 API pages (overview + tech)
- 1 pages overview
- 1 business rules page
- 2 ADRs
- 1 master task list
- 1 feature task stub (language-packs, blocked)

**Open questions remaining:** 18 (across language-packs, vocab-dojo, mysteries, conversations, token-economy, auth)

**Key findings from bootstrap interview:**
- Current priority: Language Pack generation pipeline
- Stack: Flask + Jinja2 + Supabase + OpenRouter + Azure TTS + R2 + Stripe on Railway
- Language Packs are themed conversation bundles with word study → exercises → comprehension progression
- All content is system-generated, manually triggered by admin
- Conversations serve as corpus for vocabulary extraction (not standalone feature)
- Vocab Dojo is a new feature being built for adaptive exercise serving
- Future B2B play via organizations, but individual users are current focus

## 2026-04-10 ingest | Raw documents + user answers to 18 lint questions

**Sources processed:**
- `raw/LinguaLoop Vocabulary Acquisition Pipeline.md` — 10-level exercise ladder spec (Nation's framework)
- `raw/TASK_ Using the specification below, design a rese.md` — Full pipeline report: 3-prompt architecture, age tiers, word states, promotion/demotion
- `raw/# Task_Analyse and interrogate the following plan,.md` — Study pack design: corpus-first, adaptive learning arc, inverted density, scenario generation
- `raw/The big question with linguadojo exercises is_ how.md` — Exercise serving algorithm: ExerciseScheduler, session composition, anti-repetition
- `raw/I want to eventually add the ability to track a us.md` — Test recommendation via set-based vocab matching (not embeddings)
- User's 18 answers to lint report questions (age tiers, NLP in DB, admin dashboard, etc.)

**Pages created: 5**
- `algorithms/vocabulary-ladder.md` — 10-level receptive-to-productive word acquisition
- `algorithms/vocabulary-ladder.tech.md` — Nation's framework, language specs, POS routing
- `features/vocab-dojo.tech.md` — ExerciseScheduler, anti-repetition, get_exercise_session RPC
- `decisions/ADR-003-age-tiers.md` — Age-tier difficulty system replacing CEFR

**Pages substantially rewritten: 7**
- `features/language-packs.md` — Corpus-first design, adaptive cycle, pack mastery tiers
- `features/language-packs.tech.md` — 7-stage pipeline, new tables, runtime orchestrator
- `features/exercises.md` — 21 types in 4 phases, age-tier table
- `features/exercises.tech.md` — 3-prompt LLM pipeline, numeric JSON schema, validation
- `features/vocab-dojo.md` — Full adaptive serving spec, 40/40/20 session split
- `features/conversations.tech.md` — Two-step scenario generation (Matrix Builder + Expander)
- `features/comprehension-tests.md` — 90-95% vocab coverage for recommendations

**Pages updated: 3**
- `database/schema.tech.md` — Added 7 new tables, 4 column additions, exercise session RPC
- `overview/project.tech.md` — Added admin pipeline dashboard spec
- `index.md` — Added 5 new pages, updated descriptions, page count 28 → 33

**Key decisions confirmed:**
- Corpus-first architecture (conversations generated naturally, vocab extracted post-hoc)
- Age tiers replace CEFR for LLM generation (ADR-003)
- Generate-once, use-forever: all exercise assets immutable after validation
- NLP analysis via Supabase pg_text_analysis plugin (in-database)
- Set-based vocabulary matching for test recommendations (not vector embeddings)
- Admin manually triggers pipelines via dashboard; no automated scheduling

**Open questions resolved: 14 of 18** (from bootstrap lint report)

## 2026-04-11 ingest | Complete Supabase database map

Source: Live Supabase project (kpfqrjtfxmujzolwsvdq) via MCP connector — direct SQL queries + list_tables API.

**Data pulled:**
- 60 tables with full column details (types, nullable, defaults, RLS status)
- 100+ foreign key constraints from information_schema
- All indexes (btree, GIN, IVFFlat)
- 11 triggers
- 1 custom enum (exercise_source_type)
- 3 views (corpus_statistics, vw_distractor_error_analysis, vw_exercise_performance_by_type)
- 43 application RPCs/functions with full SQL definitions
- 199 extension functions (pgvector, intarray, pg_trgm) catalogued but not documented

**Pages rewritten: 2**
- `database/schema.md` — Complete rewrite with 10 domains, 60 tables, row counts, RLS status, enum/view/trigger summaries
- `database/schema.tech.md` — Complete rewrite from Supabase data: every column, type, FK, index, trigger

**Pages created: 1**
- `database/rpcs.tech.md` — All 43 application RPCs with full function bodies, categorized by domain

**Pages updated: 2**
- `index.md` — Added rpcs.tech, updated schema descriptions, page count 33 → 35
- `log.md` — This entry

**Key findings:**
- 18 tables have RLS enabled (all user-facing + content tables)
- dim_languages is the central FK hub — nearly every content table references it
- 43 custom RPCs cover: auth (is_admin, is_moderator), ELO (update_elo_ratings, record_test_attempt), tokens (atomic add/consume), vocab (BKT updates, stats), exercises (session management), mysteries, and utilities
- users table FK to auth.users.id (Supabase auth integration)
- users_backup table exists (empty, legacy, no PK)
- pgvector extension in use (topics.embedding with IVFFlat index, 100 lists)
- intarray extension in use (tests.vocab_sense_ids with gin__int_ops)
