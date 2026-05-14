# Activity Log

## 2026-05-15 change | Pinyin test history fix on Chinese profile dashboard

User report: "the pinyin test history does not properly update." Plan at [`C:\Users\James\.claude\plans\the-pinyin-test-history-foamy-parnas.md`](../../.claude/plans/the-pinyin-test-history-foamy-parnas.md).

Root cause: [submit_pinyin_attempt](../routes/tests.py) at `routes/tests.py:871` built a synthetic response `{selected_answer: "pinyin_accuracy_0.87"}` and called `process_test_submission`. The RPC ignores the synthetic value — it iterates the test's real MC `questions` and string-compares each correct answer against the synthetic string. The comparison always fails, so every pinyin attempt landed in `test_attempts` with `score=0, total_questions=<n_mc>, percentage=0` and the user's pinyin ELO dropped on every play. Confirmed pre-fix: 2 pinyin rows in `test_attempts`, both 0/N; user pinyin ELO at 1177 (down from 1200 default).

Fix shipped:
- New RPC [migrations/process_pinyin_submission.sql](../migrations/process_pinyin_submission.sql): accepts `p_correct_chars` / `p_total_chars` directly, writes truthful `test_attempts.score / total_questions / percentage`, reuses the K=32 ELO formula and `test_attempts` triggers. Applied to remote project.
- [routes/tests.py:871](../routes/tests.py#L871) (`submit_pinyin_attempt`): removed the synthetic-response block and the unused `questions` lookup; now calls a new `_call_pinyin_submission_rpc` helper that hits the dedicated RPC.
- [templates/profile.html](../templates/profile.html): added a `SKILL_ICONS` map (listening 🎧, reading 📖, dictation ✍️, pinyin 🀄) used by `renderSkillTabs` and `renderStats`; `renderHistory` now renders pinyin rows as `87/100 chars` to disambiguate from MC-question scores.
- i18n: added `test_list.pinyin` to [en](../static/i18n/en.json), [zh](../static/i18n/zh.json), [ja](../static/i18n/ja.json), [es](../static/i18n/es.json).
- Cleanup [migrations/cleanup_corrupt_pinyin_attempts.sql](../migrations/cleanup_corrupt_pinyin_attempts.sql): deleted 2 corrupt pinyin attempts, recomputed `tests.total_attempts` for affected tests, reset all pinyin `user_skill_ratings` to 1200 and `test_skill_ratings` to 1400. Applied to remote project.
- Wiki: [features/pinyin-trainer.tech.md](features/pinyin-trainer.tech.md) — updated architectural-decision section #2 ("Reuse RPC with synthetic response" → "Dedicated `process_pinyin_submission` RPC") with the failure-mode explanation; bumped dependencies/last_updated; appended Recent Changes entry. [database/rpcs.tech.md](database/rpcs.tech.md) — catalogued the new RPC and the cleanup migration.

Pages updated: 3. Pages created: 0. Open questions remaining: 0.

## 2026-05-15 change | Jumbled & cloze exercise pipeline revamp

Two exercise types were producing low-quality output. Plan at [`C:\Users\James\.claude\plans\plan-out-how-to-toasty-willow.md`](../../.claude/plans/plan-out-how-to-toasty-willow.md). Both sections shipped together.

**Section A — Jumbled Sentence.** Root cause: serve-time [`prepare_jumbled_content`](../services/exercise_generation/language_processor.py) called `tokenize()` instead of `chunk_sentence()`, so every learner saw one-word-per-chunk despite a multi-word chunker existing on the same class.
- [services/exercise_generation/language_processor.py](../services/exercise_generation/language_processor.py): flipped the call to `chunk_sentence`; rewrote `EnglishProcessor.chunk_sentence` with a spaCy dep-parse anchor algorithm (each token belongs to the chunk whose anchor is its closest ancestor that's either ROOT or a direct constituent child of ROOT). Added pronoun-subject + verb merging so "She made | a wise decision | yesterday" replaces "She | made | a wise decision | yesterday"; multi-word subject NPs remain distinct from the verb chunk. Rewrote `ChineseProcessor.chunk_sentence` with `jieba.posseg` (coverb/conjunction starters, NP→predicate transitions, sticky particles). Tightened `JapaneseProcessor` to skip punct/space and cap at 6.
- [tests/test_exercise_generation/test_chunk_sentence.py](../tests/test_exercise_generation/test_chunk_sentence.py): 70 new tests — chunk-count range, full token coverage, no dangling function-word singletons, multi-word majority, pronoun-subject merge, multi-word subject preservation, Chinese coverb attachment, end-to-end `prepare_jumbled_content`.

**Section B — Cloze Completion.** Two interventions:
- *Prompt strengthening.* New migration [migrations/cloze_distractor_quality.sql](../migrations/cloze_distractor_quality.sql) supersedes `vocab_prompt2_exercises` lang=2 v3 → v4 (English) and lang=1 v1 → v2 (Chinese), changing **only the L3 block** in each — every distractor now requires an explicit failure-dimension tag (`semantic`/`collocational`/`aspectual`/`register`/`valency`) and a substitution audit (swap the target with a near-synonym; if the distractor becomes valid, reject it). At least two distinct failure dimensions must appear across the three distractors. Legacy `cloze_distractor_generation` bumped v1 → v2 with the same rules in single-block form.
- *Post-generation Distractor Judge.* New task `cloze_distractor_judge` v1 (cheap model: `google/gemini-2.5-flash-lite`). New module [services/exercise_generation/cloze_judge.py](../services/exercise_generation/cloze_judge.py) (`judge_distractors`, `filter_distractors`). Wired into both pipelines:
  - [services/exercise_generation/generators/cloze.py](../services/exercise_generation/generators/cloze.py) — judge after `_generate_distractors`; on rejection, retry once; if still <3 valid distractors, return None. Judge metadata recorded under `exercises.tags.cloze_judge` via overridden `_build_tags`.
  - [services/vocabulary_ladder/exercise_renderer.py](../services/vocabulary_ladder/exercise_renderer.py) `_render_cloze` — judge applied before option shuffle; rejected distractors dropped; if <3 remain, return None so the variant is skipped. A `__judge_meta` sidecar in returned content is lifted into `tags['cloze_judge']` at row construction.
  - Judge failure mode (template missing, LLM down, malformed JSON): falls back to keeping all distractors and logs a warning — degrades to generator quality, never silently drops content.
- *Tests.* 14 new tests across [test_cloze_judge.py](../tests/test_exercise_generation/test_cloze_judge.py) (template loading, verdict parsing, fallback behaviour, cache) and [test_cloze_generator.py](../tests/test_exercise_generation/test_cloze_generator.py) (judge-keep, judge-reject-retry, judge-reject-final-fail, tag propagation).

**Test suite:** 232 passed, 1 skipped, 1 pre-existing failure on `test_difficulty_frequency.py::test_tier_still_dominates` (unrelated, present on main before this change).

**Wiki updates:** [wiki/features/exercise-generation-prompts.md](features/exercise-generation-prompts.md) (added Prompt 2 v4 L3 block, judge prompt verbatim, legacy v2 prompt), [wiki/features/exercises.tech.md](features/exercises.tech.md) (judge in cloze flow, chunk_sentence at serve time), [wiki/features/vocab-dojo.tech.md](features/vocab-dojo.tech.md) (chunking note).

**Out of scope (per user scoping decisions during planning):** LLM-based jumbled chunking at generation time; validator-level lemma/inflection/substring checks (the judge subsumes most of these). Japanese chunker rewrite was limited to robustness fixes since `ja_core_news_sm` is not installed locally; live spaCy testing was English + Chinese only.

## 2026-05-13 follow-up | Restore admin dashboard vocab browser after admin auth fix

Source: The 2026-05-13 admin-auth fix (entry below) added `@admin_required` to every route in [routes/vocab_admin.py](../routes/vocab_admin.py), which immediately broke the local admin dashboard's Vocab Browser tab — [static/js/admin-dashboard.js](../static/js/admin-dashboard.js) hits `/api/admin/vocab/*` with plain `fetch()` (no Authorization header), so all 4 calls now return `401 Token missing`. Per user direction, production security on `/api/admin/vocab/*` must remain, and the local dashboard should regain access without weakening that.

**Approach.** Mirror the 4 dashboard-relevant handlers into [routes/admin_local.py](../routes/admin_local.py) (the local-only `admin_local_bp` mounted only by [admin_app.py](../admin_app.py)) under a new `/admin/api/vocab/*` prefix with no decorator — auth is provided by deployment posture, consistent with the rest of `admin_local.py`. Dashboard JS repointed at the new paths. Production `/api/admin/vocab/*` and its `@admin_required` gate are untouched. The other production route still hitting `/api/admin/vocab/*` is [templates/admin_vocab_preview.html](../templates/admin_vocab_preview.html) (at `/admin/vocab-preview`), which uses `authFetch` to send a Bearer token — that caller is unaffected.

The 3 other vocab_admin routes (`upload-words`, `generate-assets`, `render-exercises`) are not called from the dashboard, so they're not mirrored — they stay only on the production surface behind `@admin_required`.

**Files modified: 4**
- [routes/admin_local.py](../routes/admin_local.py) — added imports (`api_success`, `bad_request`, `server_error`) and a new section `# ── Vocab admin browser (local mirror of /api/admin/vocab) ───` with 4 handlers (`vocab_list_words`, `vocab_preview_word`, `vocab_wipe_word`, `vocab_remove_level`). Handler bodies copied verbatim from [routes/vocab_admin.py](../routes/vocab_admin.py) lines 163-301 — keep in lockstep.
- [static/js/admin-dashboard.js](../static/js/admin-dashboard.js) — 4 single-line URL changes from `/api/admin/vocab/*` to `/admin/api/vocab/*` (lines 880, 952, 1051, 1060).
- [wiki/api/rpcs.tech.md](api/rpcs.tech.md) — added a callout to the `/api/admin/vocab` section pointing at the mirror; added a new "Vocab browser mirror" sub-section under admin_local.py listing the 4 new routes; `last_updated` bumped.
- [wiki/log.md](log.md) — this entry.

Notes:
- **Duplication is intentional.** The user-selected design accepts ~140 lines of duplicated route bodies as the price of keeping the production decorator firm and the local dashboard auth-free. A header comment in the new section flags the lockstep requirement.
- **Response shape is identical.** Both endpoints use `utils.responses.api_success(...)` which returns `{"status": "success", "data": {...}}` — the existing dashboard JS already checks `data.status === 'success'`, so no parsing changes were needed.
- **`admin_vocab_preview.html` is not in scope.** That separate admin page (mounted at `/admin/vocab-preview` in production too) uses `authFetch()` with a Bearer token; it correctly hits the production-gated `/api/admin/vocab/*` route and continues to work.

Verification (passed):
1. `grep -r "/api/admin/vocab" static/` → zero matches. ✅
2. `grep -r "/admin/api/vocab" static/` → exactly 4 matches in `static/js/admin-dashboard.js` (lines 880, 952, 1051, 1060). ✅
3. Smoke (deferred to next admin_app.py run): hit `/admin` → Vocab Browser tab → verify list/preview/wipe/level-remove all return 200 in DevTools Network and no 401s in Flask stdout.

---

## 2026-05-13 fix | Close 3 audit-flagged gaps — admin auth, daily_test_loads FK, get_recommended_tests signature

Source: Cleanup pass on the three remaining issues from the 2026-05-12 wiki audit ([wiki/log.md](log.md) entry below) — `vocab_admin` had no auth in production, `daily_test_loads.user_id` FK'd to `auth.users` instead of `public.users` like every other user-owning table, and `get_recommended_tests` was the lone RPC taking `p_language text` instead of `p_language_id smallint`. Per user direction, `admin_local_bp` and `model_arena_bp` are out of scope — they live only in `admin_app.py` which is run only on the operator's local machine, so deployment posture is sufficient.

**Fix 1 — vocab_admin gated with `@admin_required`.** [routes/vocab_admin.py](../routes/vocab_admin.py) — added `from middleware.auth import admin_required` and decorated all 7 routes (`/upload-words`, `/generate-assets`, `/render-exercises`, `/words`, `/word/<sense_id>/wipe`, `/word/<sense_id>/level/<level>`, `/word/<sense_id>/preview`). Blueprint is registered in production at `/api/admin/vocab` ([app.py:262](../app.py#L262)), so the decorator is now the only access boundary. Mirrors the pattern already in use on [routes/corpus.py](../routes/corpus.py).

**Fix 2 — daily_test_loads.user_id FK retargeted to public.users.** New migration [migrations/fix_daily_test_loads_user_id_fk.sql](../migrations/fix_daily_test_loads_user_id_fk.sql) drops the autogenerated `auth.users` FK (via a DO block so the constraint name doesn't need to be known up front), re-adds it as `REFERENCES public.users(id) ON DELETE CASCADE`, and drops two narrow legacy RLS policies (`"Users can read own daily loads"` / `"Users can update own daily loads"`) that were superseded by `dtl_own_data` (FOR ALL) from the 2026-05-12 migration. Source-of-truth migrations [migrations/daily_test_loads.sql](../migrations/daily_test_loads.sql) and [migrations/create_all_tables.sql](../migrations/create_all_tables.sql) updated so future re-applies match prod. The stale NOTE comment in [migrations/enable_rls_on_user_owned_tables.sql](../migrations/enable_rls_on_user_owned_tables.sql) about the FK inconsistency was removed. No data move was needed: `public.users.id` is PK-FK'd 1:1 to `auth.users.id`, so every existing row already satisfies the new constraint.

**Fix 3 — get_recommended_tests signature swap.** New migration [migrations/fix_get_recommended_tests_signature.sql](../migrations/fix_get_recommended_tests_signature.sql) drops the old `(uuid, text)` function and creates `(uuid, smallint)` with the same body minus the in-function `dim_languages` lookup block (which resolved the language code/name to a smallint anyway). DROP+CREATE was required because Postgres doesn't allow `CREATE OR REPLACE` to change a parameter type. Both Python callers — [routes/tests.py:get_recommended_tests](../routes/tests.py) and [services/test_service.py:_compute_daily_load](../services/test_service.py) — were updated to pass `p_language_id` directly (removing the `LANGUAGE_ID_TO_NAME` reverse-lookup at each call site). The orphaned `LANGUAGE_ID_TO_NAME` import in [routes/tests.py](../routes/tests.py) was dropped.

**Files created: 2**
- [migrations/fix_daily_test_loads_user_id_fk.sql](../migrations/fix_daily_test_loads_user_id_fk.sql) — Fix 2.
- [migrations/fix_get_recommended_tests_signature.sql](../migrations/fix_get_recommended_tests_signature.sql) — Fix 3.

**Files modified: 8**
- [routes/vocab_admin.py](../routes/vocab_admin.py) — `@admin_required` on every route + import.
- [routes/tests.py](../routes/tests.py) — caller passes `p_language_id`; orphaned `LANGUAGE_ID_TO_NAME` import removed.
- [services/test_service.py](../services/test_service.py) — caller passes `p_language_id`.
- [migrations/daily_test_loads.sql](../migrations/daily_test_loads.sql) — FK retargeted; redundant policies removed (now defer entirely to `enable_rls_on_user_owned_tables.sql`).
- [migrations/create_all_tables.sql](../migrations/create_all_tables.sql) — FK retargeted to `public.users` with `ON DELETE CASCADE`.
- [migrations/enable_rls_on_user_owned_tables.sql](../migrations/enable_rls_on_user_owned_tables.sql) — stale "schema inconsistency" NOTE removed from the `daily_test_loads` section.
- [wiki/api/rpcs.tech.md](api/rpcs.tech.md) — `get_recommended_tests` outlier note removed; signature corrected in two places; vocab_admin table reflects the new `@admin_required` decoration; `last_updated` bumped.
- [wiki/database/schema.tech.md](database/schema.tech.md) — `daily_test_loads` FK line updated to point at `public.users.id` with migration link; `get_recommended_tests` signature in the RPC index corrected to `language_id`; `last_updated` bumped.
- [wiki/database/rpcs.tech.md](database/rpcs.tech.md) — full body of `get_recommended_tests` rewritten in place to match new signature; migration history added; `last_updated` bumped.
- [wiki/log.md](log.md) — this entry.

Verification (deferred to deploy):
1. `curl -X POST $HOST/api/admin/vocab/upload-words` with no auth → 401; with non-admin JWT → 403; with admin JWT → 200.
2. `SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'public.daily_test_loads'::regclass AND contype='f'` → `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`.
3. `SELECT policyname FROM pg_policies WHERE tablename = 'daily_test_loads' ORDER BY policyname` → exactly `dtl_admin_view`, `dtl_own_data`, `dtl_service_role`.
4. `\df public.get_recommended_tests` → exactly one row with `(uuid, smallint)`.
5. End-to-end: log in, hit `GET /api/tests/recommended?language_id=1` and `GET /api/tests/daily-load?language_id=1` — both should return 200 with no behavior change.

Out of scope:
- `admin_local_bp` and `model_arena_bp` remain undecorated. Confirmed with user that deployment posture (mounted only by `admin_app.py`, gitignored, run only on operator's local machine) is sufficient and adding JWT decorators would just add friction to the local dashboard for no real security gain.

---

## 2026-05-12 fix | RLS hardening for 7 user-owning tables

Source: Closes the RLS audit gap surfaced earlier today in the full-codebase audit ([wiki/log.md](log.md) entry below) and recorded as the headline open_question on [wiki/database/schema.md](database/schema.md). Anyone holding the anon Supabase API key could previously read or write every row of `user_vocabulary_knowledge`, `user_flashcards`, `user_word_ladder`, `word_quiz_results`, `exercise_attempts`, `daily_test_loads`, and `daily_test_load_items` — i.e. every user's learning history across all users. This entry locks them down.

Pre-flight exploration confirmed the migration is safe and additive: every backend call site for these 7 tables (13 Python sites + 7 RPCs) goes through `get_supabase_admin()` (service-role key) which bypasses RLS entirely, and `static/js/*.js` has zero direct queries against any of them. So enabling RLS does not require any Python or JS changes.

**Files created: 1**
- [migrations/enable_rls_on_user_owned_tables.sql](../migrations/enable_rls_on_user_owned_tables.sql) — Single idempotent migration. For each of the 7 tables: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` (idempotent), followed by three policies wrapped in `DROP POLICY IF EXISTS` + `CREATE POLICY` pairs so the migration is re-runnable. Policy triple mirrors the established pattern on `user_languages` / `user_skill_ratings` / `user_tokens` / `user_exercise_history` / `user_pack_selections`: (a) `*_own_data` — `FOR ALL USING/WITH CHECK (auth.uid() = user_id)`, (b) `*_service_role` — `FOR ALL USING (auth.role() = 'service_role')` so the Flask app's service-role client stays unaffected, (c) `*_admin_view` — `FOR SELECT USING (is_admin(auth.uid()))` for support / moderation. The `daily_test_load_items` table has no `user_id` column so its policies use an `EXISTS (SELECT 1 FROM daily_test_loads d WHERE d.id = daily_test_load_items.load_id AND d.user_id = auth.uid())` subquery instead, with the admin view OR-ing the same subquery so admins still see all rows.

**Files modified: 3**
- [wiki/database/schema.tech.md](database/schema.tech.md) — Per-table `RLS:` line on all 7 affected tables flipped from "Disabled" to "Enabled (2026-05-12 via [migration link]). Policies: [policy triple]." Inline note added to `daily_test_loads.user_id` calling out the `auth.users.id` vs `public.users.id` FK inconsistency (functionally harmless because `handle_new_user` keeps them equal; tracked as separate follow-up).
- [wiki/database/schema.md](database/schema.md) — Domain table prefixes flipped from "⚠ RLS DISABLED" to "(RLS)" for the 7 tables with 2026-05-12 enable-date annotations. RLS audit snapshot at the bottom rewritten: enabled count 36 → 41, disabled count 28 → 23 (the original raw count was 30; my earlier audit undercounted by 2). The disabled list now only contains content/infrastructure tables (categories, topics, production_queue, prompt_templates, exercises, corpus_*, conversations, personas, scenarios, word_assets, style_*, pack_*, test/topic_generation_runs/_config, question_type_distributions) — i.e. tables with no per-user state. `open_questions` frontmatter entry rewritten to reflect that the user-owning gap is closed and to record the remaining decision about content tables.
- [wiki/log.md](log.md) — This entry.

Notes:
- **No Python or JS changes.** All existing access continues to work because every call path uses the service-role client. The own-data policy future-proofs the tables for direct frontend (anon-client) access if the architecture ever shifts.
- **RPC behaviour.** All SECURITY INVOKER RPCs that touch these tables (`ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`, `update_vocabulary_from_test`, `update_vocabulary_from_word_test`, `get_exercise_session`, `get_ladder_session`) run inside a service-role connection in the live app, so their inner queries hit the `*_service_role` policy and pass cleanly. If a future direct-from-frontend caller invokes one of these RPCs over the anon client with a user JWT, the inner queries would hit the `*_own_data` policy and the `auth.uid()` check would correctly scope rows to the authenticated user.
- **The 4 legacy Phase 4 counter columns on `user_word_ladder`** (`first_try_success_count`, `first_try_failure_count`, `total_attempts`, `last_success_session_date`) remain written-but-never-read after Phase 8; RLS does not change their status. Separate cleanup tracked in [algorithms/ladder-implementation-analysis.md](algorithms/ladder-implementation-analysis.md).
- **Daily test loads FK quirk** (`user_id -> auth.users.id` instead of `public.users.id`) remains as a future schema-realignment migration. Behaviour-neutral because the two ids are identical post-`handle_new_user`.

Out of scope (flagged):
- The 23 remaining RLS-disabled tables are content/infrastructure with no per-user state. Decide later whether to RLS-lock them as defence-in-depth or document them as deliberately public. The anon role can already read `tests`, `questions`, `mysteries` etc. through existing public-read policies, so locking content tables doesn't necessarily improve the threat model — it might just add maintenance burden.
- Frontend integration of direct supabase-js queries against these now-RLS-enabled tables is not a planned change; the current architecture has all Postgres traffic flow through the Flask API.

Verification (all passed):
1. **RLS state.** `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename IN (...7 tables...)` returned 7 rows, all `rowsecurity = true`. ✅
2. **Policy count.** `SELECT tablename, count(*) FROM pg_policies WHERE schemaname='public' AND tablename IN (...) GROUP BY tablename` returned 7 rows, each with exactly 3 policies — 21 policies total, naming convention `<prefix>_own_data` (cmd=ALL), `<prefix>_service_role` (cmd=ALL), `<prefix>_admin_view` (cmd=SELECT). ✅
3. **Smoke test (deferred for live app).** Recommended end-to-end check: GET `/api/flashcards/due?language_id=2`, POST `/api/flashcards/review`, GET `/api/exercises/session?language_id=2`, POST `/api/exercises/attempt`, GET `/api/vocab-dojo/session?language_id=2&count=20`, POST `/api/vocab-dojo/attempt`, GET `/api/tests/daily-load?language_id=2`. All should behave identically to pre-deploy because they use service-role.
4. **Rollback path.** Each `CREATE POLICY` has a matching `DROP POLICY IF EXISTS`; `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` instantly reverts. Migration is idempotent and safe to re-run.

---

## 2026-05-12 audit | Full codebase + live DB pass — API endpoint reference, schema/RLS audit, services tree refresh

Source: User-directed comprehensive wiki refresh. Ran a full live-database introspection via Supabase MCP (`list_tables verbose`, `pg_proc` dump, triggers/policies/indexes/enums/views queries) and a complete route-file pass to ensure the wiki is current and accurate for technical developers picking up the codebase cold.

Findings worth surfacing:
- **`language_model_config` table was dropped** by `migrations/drop_dim_languages_model_columns.sql` but [wiki/database/schema.tech.md](database/schema.tech.md) still documented it as a live Phase 4 table. Replaced the section with a "DROPPED" notice pointing at the 2026-05-05 model-routing refactor that consolidated routing onto `prompt_templates.model`.
- **`dim_languages` model columns also dropped** (`prose_model`, `question_model`, `exercise_model`, `exercise_sentence_model`, `conversation_model`, `vocab_prompt1_model`, `vocab_prompt2_model`, `vocab_prompt3_model`). Wiki still listed them — fixed.
- **RLS audit gap.** 28 of 64 tables have RLS disabled. Content tables (exercises, corpus_*, conversations, personas, scenarios, prompt_templates) plausibly stay public. **The user-owning ones in the disabled set (`user_vocabulary_knowledge`, `user_flashcards`, `user_word_ladder`, `word_quiz_results`, `exercise_attempts`, `daily_test_loads`, `daily_test_load_items`) deserve a security audit pass** — anyone with the anon Supabase key can read every row today. Surfaced in [[database/schema]] open-questions plus in-line on the schema.tech reference; not auto-remediated since enabling RLS without policies would lock out the legitimate service-role pipeline.
- **`daily_test_loads.user_id` FKs to `auth.users.id` instead of `public.users.id`** — inconsistent with every other user-owning table. Likely a relic; logged but not fixed.
- **`get_recommended_tests` takes `p_language text` (language code)** while every other RPC takes `p_language_id smallint`. The wiki now flags this outlier explicitly on the API endpoint table.
- **Stripe webhook handler is not registered.** `process_stripe_payment` RPC exists in the DB, but no Flask route currently calls it. Surfaced as an open_question on the overview and api pages.
- **Several admin blueprints (`vocab_admin`, `admin_local`, `model_arena`) have no auth decorators** — they rely on deployment posture (only mounted by `admin_app.py`, which is operator-only). Surfaced inline with ⚠ on each route table.
- **Live DB has ~77 application RPCs** (50 plpgsql + 23 sql + 4 internal aggregates) plus ~199 extension functions from pgvector / pg_trgm / intarray / GIN-GiST handlers. Wiki claim of 65 functions was understating it; new counts written into the schema overview.
- **64 tables live** (not 62 or 65); count reconciled against introspection.

**Pages rewritten (5):**
- `wiki/api/rpcs.tech.md` — Full rewrite. Now the canonical endpoint reference covering every blueprint (15) plus core routes, web routes, admin endpoints, and a complete RPC call-site map. Each endpoint table shows method, path, auth decorator, body/query schema, RPC dependencies, and key response shape. 2747 lines → ~440 lines, but covering ~3x the surface area (previously omitted: model_arena, vocab_admin, admin_local, full vocab-dojo battery flow, pinyin submit, mystery scene flow, daily-load endpoints, etc.).
- `wiki/overview/project.tech.md` — Refreshed services directory tree to reflect current layout (`services/irt/`, `services/model_arena/`, `services/exercise_generation/audio_voice.py`); architecture diagram now shows the APScheduler; tech stack table updated for Postgres 17 + 64 tables + 77 RPCs; admin dashboard tab count corrected to 10 with two extra rows for L1 Audio Backfill and IRT Calibration; Stripe webhook gap surfaced.
- `wiki/overview/project.md` — Brand-name banner pointing to ADR-004; feature table flipped Vocab Dojo, Mysteries, and the Daily Mixed Session from "Planned/In-Progress" to "Working" with Phase 8/9/10/11 anchors; Stripe webhook + subscription gating recorded as open questions.
- `wiki/api/rpcs.md` — Blueprint map expanded from 13 to 15 entries (admin_local + model_arena now listed) with line counts; admin-only callout explicit; production vs admin variant separation clarified.
- `wiki/pages/pages-overview.md` — All 18 page routes documented with the API endpoints each calls; admin-only pages (`/admin`, `/admin/vocab-preview`) separated from production routes; static asset layout described.

**Pages updated (3):**
- `wiki/database/schema.md` — Domain-by-domain count refresh (64 tables, 11 triggers, 3 views, ~77 RPCs); RLS audit snapshot listing all 36 enabled + 28 disabled tables; Phase 8/10/11 columns on `user_word_ladder` and `exercises` called out; conversation/persona/style domains pulled apart from the older bundling.
- `wiki/database/schema.tech.md` — Surgical edits: bumped `last_updated` to 2026-05-12; replaced the `dim_languages` model columns block with a 2026-05-05 deprecation note; rewrote the `language_model_config` section as a "DROPPED" notice; updated the overview header counts (64 tables, 36/28 RLS split, 77 application RPCs).
- `wiki/index.md` — Brand text updated `LinguaLoop` → `LinguaDojo`; `last_updated` annotation refreshed.

**Pages NOT updated (left as current):**
- All `wiki/features/*` — feature pages were comprehensively refreshed by the 2026-05-12 Phase 10/11 entries earlier today and accurately describe current code.
- All `wiki/algorithms/*` — likewise current as of today's Phase 11 entry.
- `wiki/decisions/*` — ADRs are append-only history; no new decisions to record.
- `wiki/database/rpcs.tech.md` — already documents Phases 7-11 RPCs with full SQL definitions; spot-checked against live DB and counts are within tolerance (the IRT lock pair, IRT calibration, theta computation, and Phase 9 selection helpers are all present). The 4-arg vs 3-arg `get_exercise_session` overloads, the 4-arg vs 3-arg `bkt_apply_decay`/`bkt_effective_p_known` overloads, and the 5-arg vs 4-arg `update_vocabulary_from_word_test` overloads all live in the live DB — verified.
- `wiki/business-rules/auth-and-access.md` — not surveyed in this pass; defer.
- `wiki/tasklist/*` — left as-is.

Notes:
- The live DB has function overloading for `get_exercise_session` (3-arg legacy, 4-arg Phase 11), `update_vocabulary_from_word_test` (4-arg, 5-arg with `p_exercise_type`), `bkt_apply_decay` (3-arg flat half-life, 4-arg FSRS-stability), `bkt_effective_p_known` (same split). The Python session service passes 4-arg; the legacy 3-arg signatures are intentionally retained so older callers (e.g. raw SQL probes, the admin SSE console) don't break.
- `daily_test_loads.user_id` mis-FK to `auth.users.id` is a documented oversight, not a behavioural bug — auth.users.id and public.users.id are guaranteed equal by the `handle_new_user` trigger. Future cleanup migration could realign without behavioural changes.
- The Model Arena pricing cache lives in-process per worker; the `data/arena_runs/<task_id>.json` files are the persistent record. Worth noting if anyone tries to reproduce a comparison weeks later.

Verification:
1. `grep -n "language_model_config" wiki/database/schema.tech.md` returns only the "DROPPED" callout and one historical reference in the RPC helper note.
2. `grep -n "prose_model\|question_model\|exercise_model" wiki/database/schema.tech.md` returns zero matches in the dim_languages column list.
3. `grep -rn "2026-04-2[0-9]\|2026-04-1[0-9]" wiki/overview/ wiki/api/ wiki/pages/` returns no stale `last_updated` frontmatter — all overview/api/pages tops are 2026-05-12.
4. `wiki/api/rpcs.tech.md` enumerates every route that grep against `routes/*.py` for `@\w+_bp\.route` finds (97 routes across 15 blueprints), plus the 5 core routes and 18 web routes from `app.py`.
5. `wiki/database/schema.md` RLS audit lists all 28 RLS-disabled tables exactly as `list_tables` reports them.

---

## 2026-05-12 ship | Chinese TTS renderer — language-aware Azure voices + L1 audio playback

Source: Track A of [C:\Users\James\.claude\plans\plan-out-how-to-partitioned-yao.md](C:\Users\James\.claude\plans\plan-out-how-to-partitioned-yao.md). Closes the "most pressing follow-up" recorded at [wiki/log.md:220 (2026-05-07)](log.md) and the open question on [wiki/features/exercise-generation-prompts.md](features/exercise-generation-prompts.md): Chinese L1 listening exercises were rendering as MCQs that displayed pinyin + 4 Hanzi options — an answer-giveaway because the pinyin IS the answer for a Chinese learner. The fix was twofold: (a) language-aware voice plumbing through the existing Azure synthesizer (`listening_flashcard` previously always voiced sentences with English `en-US-AvaMultilingualNeural` regardless of language); (b) actually generate and play audio for Vocab Dojo L1, which the v3 prompt template assumed but no renderer implemented.

**Files created: 3**
- `services/exercise_generation/audio_voice.py` — Thin helper that reads `dim_languages.tts_voice_ids` jsonb + `tts_speed` for a language and caches the result at module level. `pick_voice(db, language_id) -> (voice, speed)` randomly picks one voice from the configured list (or returns `(None, None)` so the synthesizer falls through to its Azure default). Used by both the listening flashcard generator and the L1 ladder renderer.
- `migrations/seed_chinese_tts_voices.sql` — Idempotent `UPDATE dim_languages SET tts_voice_ids = '[zh-CN-XiaoxiaoMultilingualNeural, zh-CN-YunxiNeural, zh-CN-YunyangNeural]'::jsonb WHERE id=1` (Chinese) and similar for `id=2` (English: Ava/Andrew/Brian/Emma Multilingual). Predicate filters to NULL / empty / `["alloy"]`-default rows so an operator-curated list is never overwritten. Fixes a long-standing config rot: the seeded English voices were the OpenAI catalog (`alloy/echo/fable/...`) which the Azure runtime silently ignores in favour of `en-US-AvaMultilingualNeural`.
- (Implicit) Plan file at `C:\Users\James\.claude\plans\plan-out-how-to-partitioned-yao.md` was approved and split into Track A (this entry) + Track B (Phase 11 IRT, shipped earlier the same day).

**Files modified: 7**
- `services/exercise_generation/generators/flashcard.py` — `_assemble_listening_flashcard` now resolves a per-language voice via `audio_voice.pick_voice(self.db, self.language_id)` and passes `voice=` / `speed=` into `AudioSynthesizer.generate_and_upload`. Previously every language used Azure's hardcoded English default; Chinese listening flashcards now actually sound Chinese.
- `services/vocabulary_ladder/exercise_renderer.py` — `LadderExerciseRenderer.__init__` accepts an optional `audio_synthesizer`. `_render_phonetic` (L1) now produces an `audio_url` field by calling a new `_generate_l1_audio(target, sense_id, language_id)` helper. Slug `l1_{sense_id}_{language_id}` is deterministic so re-renders overwrite the same R2 object (no orphans, CDN cache stable across regenerations). Audio generation failures degrade gracefully — `audio_url` is set to `None` and the frontend falls back to the textual IPA / pronunciation display so an Azure outage doesn't break L1 serving entirely.
- `static/js/exercise-renderers.js` — `renderPhonetic` now branches on `c.audio_url`. When present: renders a single round play button (FontAwesome `fa-volume-up`, reusing the `.audio-play-btn` style from `static/css/styles.css`), auto-plays on first render, supports tap-to-replay, and **hides** the IPA / pinyin / syllable-count text (those would give away the answer in a listening exercise). When absent: behaves identically to the pre-change implementation (graceful fallback before backfill is complete or in test environments without R2 creds). Instruction text also flips from "Which word matches this pronunciation?" → "Which word did you hear?" when audio is present.
- `routes/admin_local.py` — Two additions:
  1. `_do_vocab_generate` now passes `audio_synthesizer=AudioSynthesizer()` into `LadderExerciseRenderer`, so admin-triggered regeneration produces L1 audio automatically.
  2. New `POST /admin/api/run/l1-audio-backfill` endpoint + `_do_l1_audio_backfill(body)` worker that iterates `exercises WHERE language_id=N AND ladder_level=1 AND is_active=true`, regenerates audio via `AudioSynthesizer + audio_voice.pick_voice`, and writes the new `audio_url` back into `content`. Supports the existing stop-signal pattern.
- `templates/admin_dashboard.html` — New "L1 Audio Backfill" tab (language `<select>`, run/stop buttons, SSE console) wired to the new endpoint. Sits right after the "IRT Calibration" tab in the nav.
- `static/js/admin-dashboard.js` — `btnRunL1Audio` click handler dispatches via `submitTask('/run/l1-audio-backfill', ...)`.
- `wiki/features/exercise-generation-prompts.md` — Open-question line about Chinese TTS being absent flipped to RESOLVED with the implementation pointer.
- `wiki/features/vocab-dojo.tech.md` — Future Direction list gains a ✅ Shipped row for L1 audio rendering with full implementation pointer.
- `wiki/index.md` — Bumped `last_updated` annotation.

Notes:
- **English impact:** Existing English L1 exercises will start showing the play button only after they're regenerated (via the new admin backfill) or naturally re-created by `_do_vocab_generate`. Until then, English L1 exercises continue to render text-only — by design, since the listening reframe of EN P2 v3 (deployed 2026-05-07) presupposed audio playback that never shipped. Recommend running the backfill for `language_id=2` shortly after deploying.
- **Cost:** Azure TTS is billed per character. L1 audio is the spoken target word (typically 1-3 syllables), so per-exercise cost is negligible (< $0.0001 per item). The deterministic slug means re-runs don't duplicate-bill (overwrites same R2 key).
- **Frontend backwards compatibility:** The audio-url-aware branch in `renderPhonetic` is null-safe. Old session caches that don't contain `audio_url` render exactly as before. Mixed-cohort sessions where some L1 exercises have audio and others don't are handled per-exercise.
- **Voice rotation:** The picker uses `random.choice` over the configured voice list, so successive renders of different senses can draw different voices for variety. Each individual sense's audio is deterministic-by-slug so the same sense plays the same recording every time it appears in a session.

Verification:
1. **Apply migration**: `seed_chinese_tts_voices.sql` is idempotent (the WHERE clause filters to default/empty rows). Apply via Supabase MCP `apply_migration`, then `SELECT id, language_name, tts_voice_ids FROM dim_languages WHERE is_active = true;` and confirm Chinese row has 3 zh-CN voices and English row has 4 en-US voices.
2. **Listening flashcard language-awareness**: `python -m services.exercise_generation.run_exercise_generation --source vocabulary --language 1 --ids <chinese_sense_id>` and confirm any generated `listening_flashcard` exercise's `content.front_audio_url` plays as Mandarin (manually verify with browser audio).
3. **L1 audio generation at admin trigger**: Open `/admin` → Vocab Browser → pick a Chinese sense → trigger vocab generation. After completion, `SELECT content->>'audio_url' FROM exercises WHERE word_sense_id = <sid> AND ladder_level = 1;` returns an `https://audio.linguadojo.com/l1_<sid>_1.mp3` URL.
4. **Frontend playback**: Open `/vocab-dojo` with `localStorage.setItem('selectedLanguageId', '1')`. Start a session; when an L1 (phonetic recognition) exercise appears, confirm (a) audio auto-plays on first render, (b) the play button replays on tap, (c) the IPA / pinyin text is hidden, (d) the instruction reads "Which word did you hear?", (e) the 4 written options render as Hanzi (the answer).
5. **Backfill for English**: Open `/admin` → "L1 Audio Backfill" tab → select English → run. SSE logs stream "L1 audio backfill: N exercises to process" and progress every 25 items. After completion, `SELECT COUNT(*) FROM exercises WHERE language_id=2 AND ladder_level=1 AND is_active=true AND content ? 'audio_url';` matches the pre-run count.
6. **Idempotent backfill**: re-run the same backfill — R2 objects overwrite at the same key; no orphaned MP3s accumulate. Final `audio_url` values are identical pre- and post-rerun.

---

## 2026-05-12 ship | Phase 11 — IRT 2PL calibration + IRT-weighted selection

Source: Track B of [C:\Users\James\.claude\plans\plan-out-how-to-partitioned-yao.md](C:\Users\James\.claude\plans\plan-out-how-to-partitioned-yao.md). Closes the long-standing gap recorded as Priority 5 in [wiki/algorithms/ladder-implementation-analysis.md](algorithms/ladder-implementation-analysis.md): `exercises.irt_difficulty` / `irt_discrimination` were seeded from `complexity_tier` at generation time and never updated, so within-family exercise selection was effectively random.

**Files created: 4**
- `migrations/add_irt_calibration_metadata.sql` — Adds three columns to `exercises` (`irt_n_attempts integer NOT NULL DEFAULT 0`, `irt_calibrated_at timestamptz`, `irt_se_difficulty numeric(5,3)`) plus a partial index `idx_exercises_irt_calibrated` on the calibrated subset. Also defines four small RPCs: `irt_apply_calibration(p_exercise_id, p_discrimination, p_difficulty, p_se_difficulty, p_n_attempts)` (single-row UPDATE with server-side `now()`); `irt_compute_user_theta(p_user_id, p_language_id)` (logit of clipped first-attempt accuracy from `user_exercise_history`, returns 0.0 when no history); `irt_try_lock()` / `irt_release_lock()` wrappers around `pg_try_advisory_lock(8901234567890123)` since postgrest can't invoke the built-in with positional bigint args via supabase-py.
- `migrations/phase11_irt_selection.sql` — Redefines `get_exercise_session` with one new parameter `p_user_theta numeric DEFAULT 0.0` and an `EXP(-0.5 · ((irt_difficulty − p_user_theta)/σ)²)` factor multiplied into `type_weight` inside the `sense_candidates` CTE. σ hard-coded at 1.0 logit; gating predicate is `irt_n_attempts ≥ 20` so newly-generated items keep a flat weight of 1.0 and remain selectable. All other CTE shape, slot caps, bucket priorities, supplementary filling, and `LIMIT p_session_size` are byte-identical to Phase 9 — degrades gracefully when no exercise is calibrated.
- `services/irt/__init__.py` — empty package marker.
- `services/irt/calibrator.py` — 2PL MLE fitter (`fit_2pl` via `scipy.optimize.minimize` L-BFGS-B with explicit gradient and clamps `a ∈ [0.3, 3.0]`, `b ∈ [-3, 3]`). SE for `b` from the inverse Hessian diagonal (NaN-safe). `apply_prior(b_fit, b_seed, n, k=10)` shrinks toward the tier-seeded difficulty (n=20 → 2:1 fit-vs-seed; n=100 → 10:1 fit-dominant), so a fresh cohort can't swing an item violently. `compute_user_thetas` aggregates first-attempt accuracy per user from a single page-loaded `user_exercise_history` snapshot. `calibrate_language(language_id, min_attempts=20)` orchestrates: page-load rows → bucket by exercise → fit each ≥ min_attempts → persist via `irt_apply_calibration`. `calibrate_all_active_languages` wraps the per-language sweep in an `irt_try_lock` / `irt_release_lock` advisory-lock pair so only one gunicorn worker runs the nightly job. `compute_user_theta_for_selection` is the request-time wrapper called from the daily-session builder; delegates to the SQL `irt_compute_user_theta` for parity with calibration-time theta.

**Files modified: 9**
- `requirements.txt` — Adds `scipy>=1.10` (needed for `optimize.minimize`) and `APScheduler>=3.10` (nightly cron).
- `app.py` — New `_initialize_scheduler(app)` called from `create_app`. Boots a `BackgroundScheduler(timezone='UTC')` with one cron job (`irt_calibration_nightly` at 04:00 UTC, `coalesce=True, max_instances=1`). The job calls `calibrate_all_active_languages()`. Disable with `DISABLE_SCHEDULER=true` env var (used by tests). Cross-worker safety comes from the advisory lock, not from the env gate — the scheduler boots in every gunicorn worker, but only one will acquire the lock per fire.
- `services/exercise_session_service.py` — `_compute_session` now resolves `p_user_theta` via `compute_user_theta_for_selection(...)` before the RPC call, then passes it as a 4th positional arg to `get_exercise_session`. Theta lookup failure falls back to 0.0 (population mean) so a calibration outage doesn't break session serving.
- `routes/admin_local.py` — New `POST /admin/api/run/irt-calibration` endpoint dispatching to `_do_irt_calibration` via the existing `run_in_thread()` (services/task_runner.py). Body: `{language_id?: int, min_attempts?: int}`. Omit `language_id` to sweep every active language under the advisory lock.
- `templates/admin_dashboard.html` — New `<li id="irt-tab">` in the nav + new `<div id="irt">` panel with a language `<select>` (defaults to "All active languages"), `min_attempts` numeric input, run/stop buttons, and SSE console wired to `irtConsole` / `irtStatus`.
- `static/js/admin-dashboard.js` — `btnRunIrt` click handler calls `submitTask('/run/irt-calibration', body, ...)`. Language dropdown is hand-populated (rather than via `.lang-select`) so the "All active languages" placeholder option survives `populateLanguageDropdown`'s `innerHTML = ''`.
- `wiki/algorithms/ladder-implementation-analysis.md` — Priority 5 section flipped from open to ✅ Resolved (Phase 11) with implementation notes. Impact-assessment table's "IRT calibration" row stamped ✅ Phase 11, 2026-05-12.
- `wiki/algorithms/ladder-implementation-analysis.tech.md` — Implementation-status table row "IRT calibration" flipped from "Not done" to ✅ Live (Phase 11) with description of the σ=1.0 Gaussian weighting, the 20-attempt gate, and the flat-fallback for unfitted items.
- `wiki/database/schema.tech.md` — `exercises` columns table extended with three Phase 11 rows (`irt_n_attempts`, `irt_calibrated_at`, `irt_se_difficulty`); `irt_difficulty` / `irt_discrimination` descriptions extended to note the nightly-fit behaviour; index list extended with `idx_exercises_irt_calibrated`.
- `wiki/database/rpcs.tech.md` — `get_exercise_session` signature updated to four parameters; new "IRT Calibration (Phase 11)" section before Security Summary documents the four new RPCs; overview totals bumped 61 → 65 functions (24 → 27 DEFINER, 37 → 38 INVOKER, 12 → 13 STABLE); new category row added.
- `wiki/index.md` — Bumped `last_updated` to 2026-05-12.

Notes: The session response shape (`/api/exercises/session` JSON) is unchanged — frontend takes no diff. Phase 9 callers that pass only the original three arguments to `get_exercise_session` still work because `p_user_theta DEFAULT 0.0` collapses the Gaussian around 0 (population-mean weighting), and the gating predicate `irt_n_attempts ≥ 20` means no row is affected until calibration data accrues. The 04:00 UTC cron picks a quiet window for most timezones; tune via `replace_existing=True` in `app._initialize_scheduler` if a different time is needed. The Bayesian prior pull (`k=10`) was chosen so a 20-attempt fit still gets pulled 33% toward the seed — enough to absorb idiosyncratic early adopters without erasing real signal.

Out-of-scope (flagged):
- IRT weighting inside `get_ladder_session` — the family-BKT already targets weak families; difficulty refinement inside a family is the next layer if needed.
- Backfilling `irt_n_attempts` from historical `exercise_attempts` (we only count `user_exercise_history.is_first_attempt=true` going forward, since `exercise_attempts` doesn't track first-attempt flags). The first nightly run will start populating from the live history table.
- Multi-process scheduler coordination via a persistent jobstore (currently the BackgroundScheduler is in-memory per worker). Acceptable because the advisory lock makes duplicate fires harmless; revisit if observability needs grow.

Verification:
1. **Apply migrations**: `add_irt_calibration_metadata.sql` is idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`). Then `phase11_irt_selection.sql` is idempotent (`CREATE OR REPLACE FUNCTION`). Apply both via Supabase MCP `apply_migration`.
2. **Manual calibration**: open the admin dashboard, switch to the "IRT Calibration" tab, leave language as "All active languages", click Run. SSE logs stream "Loaded N first-attempt rows", "Computed theta for M users", "X exercises have ≥ 20 attempts", "Progress: 50 / 200 fitted", and a final summary. After completion, `SELECT count(*) FROM exercises WHERE irt_calibrated_at IS NOT NULL` is non-zero.
3. **Sanity-check fitted values**: `SELECT id, complexity_tier, irt_difficulty, irt_n_attempts, attempt_count, correct_count FROM exercises WHERE irt_calibrated_at IS NOT NULL ORDER BY irt_difficulty LIMIT 10` — easy items (low `irt_difficulty`) should have high empirical pass-rate, hard items (high `irt_difficulty`) low pass-rate. Tier seed mapping (T1=-2.0 → T6=2.0) provides the rough reference frame.
4. **Selection-side smoke test**: `SELECT * FROM get_exercise_session('<user_uuid>', 2, 20, 0.5);` returns up to 20 rows. With `p_user_theta=0.5` and σ=1.0, exercises near `irt_difficulty=0.5` should rank higher than ones at -2 or +2 for the same sense.
5. **No regression on stale callers**: `SELECT * FROM get_exercise_session('<user_uuid>', 2, 20);` (three-arg form) also returns ≤ 20 rows — `p_user_theta` defaults to 0.0.
6. **Nightly cron**: restart the app and look for "APScheduler started (irt_calibration_nightly @ 04:00 UTC)" in the log. To validate the wiring without waiting, in a python shell against the running process: `from app import app; app.scheduler.get_job('irt_calibration_nightly').modify(next_run_time=datetime.now(timezone.utc) + timedelta(seconds=30))` then watch for the lock-acquired log line and the language summary log.
7. **Advisory lock**: with two gunicorn workers running, both will fire at 04:00. One acquires the lock and runs; the other logs "Another worker holds the IRT calibration lock; skipping." and exits cleanly.

---

## 2026-05-12 ship | Phase 10 — cross-session ring advancement gating + ring demotion

Source: Phase B2 of the architectural-debt plan ([C:\Users\James\.claude\plans\plan-phase-b.md](C:\Users\James\.claude\plans\plan-phase-b.md)). Wires the existing Phase 4 counter columns (`consecutive_failures`, `last_exercised_family`) and a new `family_success_dates` JSONB into the Phase 8 Momentum Bands progression logic. Two new behaviours layered onto `ladder_record_attempt`:

1. **Cross-session advancement gate.** Ring clearing now requires both (a) every required family ≥ its confidence threshold (R1/R2: 0.50, R3: 0.65, R4: 0.72) AND (b) every required family has had first-attempt successes on at least 2 distinct calendar days. Prevents a single good afternoon from racing a word up the rings.
2. **Ring demotion.** A first-attempt failure on a family that gates the current ring demotes the word by one ring when `consecutive_failures ≥ 3`. R1 is the floor. The gate guarding exit from the dropped-into ring resets (gate_a on demote→R2, gate_b on demote→R3); other gates survive as lifetime achievements. `family_success_dates` for the demoted-into-ring required families is cleared.

**Files created: 1**
- `migrations/phase10_ladder_advancement_demotion.sql` — `ALTER TABLE user_word_ladder ADD COLUMN family_success_dates jsonb` with a six-family-keyed default (all empty arrays). Then a `CREATE OR REPLACE FUNCTION ladder_record_attempt(...)` that fully redefines the Phase 8 version with: (a) pre-UPDATE computation of `v_new_consecutive_failures` so demotion can read it; (b) in-memory mutation of `v_fc_dates` (append-CURRENT_DATE → dedupe by date → keep most recent 2) BEFORE the ring-clear check, so the same attempt that adds the second date can clear the ring; (c) cross-session gate after the confidence-threshold check (iterates `required_families`, fails the clear if any has `< 2` dates); (d) demotion block after `word_state` computation, conditional on `NOT correct AND first_attempt AND word_state NOT IN ('mastered','new') AND current_ring > 1 AND v_family = ANY(required) AND v_new_consecutive_failures >= 3` — drops ring, resets the exit gate of the dropped-into ring via `jsonb_set`, clears `family_success_dates` for the demoted-into-ring required families, sets `word_state='active'`; (e) UPDATE block uses `v_new_consecutive_failures` (or `0` if demoted) and writes `family_success_dates`; (f) return JSONB extended with `family_success_sessions jsonb` (per-family count of distinct cross-session successes, capped at 2 by storage trim) and `demoted boolean`. Other behaviour — family BKT update, momentum band scheduling, lapse path, FSRS schedule on lapse, BKT lapse penalty, overall BKT UPSERT — is byte-identical to Phase 8.

**Files modified: 6**
- `wiki/algorithms/vocabulary-ladder.md` — "Ring Advancement" rewritten with the cross-session gate as a second clearing condition. New "Ring Demotion" section after Ring Advancement. New business rule line about gate symmetry on demotion. Removed the "ring demotion" open_question from frontmatter (resolved).
- `wiki/algorithms/vocabulary-ladder.tech.md` — Dependencies list includes phase10 migration. `user_word_ladder` DDL gains `family_success_dates jsonb` in a new Phase 10 block. New paragraph documenting the cross-session gate after the ring-threshold table. New "Ring Demotion (Phase 10)" subsection documenting the trigger conditions and effects line-by-line. `ladder_record_attempt` RPC signature documentation updated with the two new return-JSONB keys.
- `wiki/algorithms/ladder-implementation-analysis.md` — `open_questions` reduced from 2 → 1 (advancement-gating + demotion questions resolved; only the legacy-counter cleanup remains). Priority 2 flipped to ✅ Resolved with implementation notes. Impact-assessment table: "Use or drop Phase 4 counters" row replaced with "Cross-session advancement gating + ring demotion (counter-driven)" marked ✅ Phase 10, 2026-05-12.
- `wiki/algorithms/ladder-implementation-analysis.tech.md` — Dependencies list extended. "Phase 4 columns — written but unread" section rewritten as a table showing read-side status after Phase 10 (consecutive_failures, last_exercised_family, family_success_dates all read; first_try_success_count, first_try_failure_count, last_success_session_date, total_attempts still unread). Implementation-status table: two rows flipped to ✅ Live (Phase 10).
- `wiki/database/schema.tech.md` — `user_word_ladder` columns table extended with `family_success_dates` row under a new "Phase 10 (advancement gating + demotion)" block.
- `wiki/database/rpcs.tech.md` — `ladder_record_attempt` signature documentation rewritten with cross-session-gate and ring-demotion behaviour paragraphs. Returns-JSONB section gains `family_success_sessions` (with explanation) and `demoted` keys.
- `wiki/decisions/ADR-005-momentum-bands.md` — New "2026-05-12 amendment: cross-session gating + ring demotion (Phase 10)" section at the bottom recording the refinement and noting which legacy columns are now dead schema.

Notes: Behavioural changes are user-visible but conservative.
- The first time any word's family confidence crosses its ring threshold, the word stays in the current ring until a *second-day* first-attempt success on each required family. Same-attempt advancement is preserved when the second-date success happens to be the threshold-crossing attempt — the in-memory `v_fc_dates` mutation handles this so we don't force an extra round trip.
- Demotion fires on three consecutive first-attempt failures on the *same family* (per the existing `last_exercised_family` heuristic from Phase 8) — failures on different families reset the counter to 1, so a learner sampling broadly across families isn't penalised.
- The frontend can opt-in to consume `family_success_sessions` (per-family date count, capped at 2) to surface "one more session" badges, and `demoted` to surface a "you stepped back" notification — both optional, no required UI work.
- The legacy `first_try_success_count`, `first_try_failure_count`, `last_success_session_date`, and `total_attempts` columns remain written but unread. Future cleanup migration could drop them once we're confident no future analytics need them; tracked as the sole remaining `open_question` on the implementation-analysis page.

Verification:
1. **Apply migration**: `phase10_ladder_advancement_demotion.sql` is idempotent (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, `CREATE OR REPLACE FUNCTION`). Apply via Supabase MCP `apply_migration`.
2. **Cross-session gate**: pick a test sense, set `current_ring=1` and `family_confidence.form_recognition=0.10`. Call `ladder_record_attempt` with `is_correct=true, is_first_attempt=true, ladder_level=1` enough times in one day to push confidence above 0.50. Assert returned `current_ring` is still 1 and `family_success_sessions.form_recognition = 1`. Then `UPDATE user_word_ladder SET family_success_dates = jsonb_set(family_success_dates, '{form_recognition}', '["2026-05-11"]'::jsonb) WHERE ...` to simulate yesterday's success. Call again: assert `current_ring = 2` and `family_success_sessions.form_recognition = 2`.
3. **Demotion**: pick a sense at `current_ring=3, gates_passed={gate_a:true, gate_b:false}`. Three calls to `ladder_record_attempt` with `is_correct=false, is_first_attempt=true, ladder_level=6` (semantic_discrimination, a required family for R3). Assert third call returns `demoted=true, current_ring=2, gates_passed.gate_a=false, gates_passed.gate_b=false (unchanged), word_state='active'`.
4. **R1 floor**: pick a sense at `current_ring=1`. Three first-attempt failures on form_recognition. Assert `demoted=false, current_ring=1, consecutive_failures` keeps growing.
5. **No regression on existing return keys**: any prior caller that destructures `{is_correct, family, word_state, current_ring, requeue, ...}` is unaffected — keys are additive.

---

## 2026-05-12 ship | Phase 9 — daily-session merged into SQL (get_exercise_session)

Source: Phase B1 of the architectural-debt plan ([C:\Users\James\.claude\plans\plan-phase-b.md](C:\Users\James\.claude\plans\plan-phase-b.md)). Fixes the silently-broken bucket-5 in `ExerciseSessionService._compute_session()` (which called a non-existent `LadderService.get_words_for_session()` and returned `[]`) by collapsing the entire 6-bucket Python builder into a single SQL RPC. Ladder content is now sourced from `get_ladder_session` inside the new RPC — one source of truth for ladder selection.

**Files created: 1**
- `migrations/phase9_get_exercise_session.sql` — Defines `get_exercise_session(p_user_id, p_language_id, p_session_size)` as a STABLE plpgsql function returning an 8-column TABLE (`out_exercise_id, out_sense_id, out_exercise_type, out_content, out_complexity_tier, out_phase, out_slot_type, out_priority`). Also defines three IMMUTABLE helpers — `exercise_type_phase_weight(type, phase)` (mirrors `PHASE_MAP` weighting: 100% A on A; 70%/30% on B/C/D with previous-phase fallback; tiny floor weight of 0.001 so any type is selectable as last-resort), `tier_window_for_p_known(avg)` (T1–T6 windows by average vocabulary p_known), `tier_to_phase(tier)` (T-tier → phase letter for supplementary slot phase tagging). CTE pipeline: `recent_seen` (7-day indexed scan of `user_exercise_history` — replaces the legacy 500-row scan of `exercise_attempts`) → `raw_senses` via `get_session_senses` (Phase 7) → `new_fallback` from `user_flashcards.state='new'` → `senses_deduped` (PARTITION BY sense_id, prefer due > learning > new) → `ladder_picks` via `get_ladder_session` (Phase 8; capped at `LEAST(5, session_size)`) → `sense_candidates` JOIN `exercises` with phase weight attached → `ranked_sense_picks` (ROW_NUMBER per sense by `type_weight DESC, RANDOM()`) → `vocab_picks_capped` (ROW_NUMBER per bucket, enforce 40/40/20 from session_size) → `vocab_picks` (slot_type label + priority) → `supplementary_picks` (`word_sense_id IS NULL`, tier-window match, fills remaining gap) → UNION ALL → `ORDER BY priority DESC, RANDOM() LIMIT p_session_size`. Virtual jumbled-sentence picks are NOT produced in SQL (language-specific tokenisation stays Python).

**Files modified: 8**
- `services/exercise_session_service.py` — Trimmed from ~1003 to ~500 lines. Deleted four scheduling helpers (`_select_exercises_for_senses`, `_get_supplementary_exercises`, `_get_ladder_exercises`, `_get_recent_exercise_ids`) and three module-level phase helpers (`_determine_phase`, `_get_eligible_types_weighted`, `_pick_weighted_type`). `_compute_session()` is now ~25 lines: call `get_exercise_session` RPC → append up to 3 virtual picks from `_get_user_test_sentences` → `random.shuffle`. Kept: `get_or_create_daily_session`, `mark_exercise_complete`, `record_attempt_with_updates`, `_update_fsrs_for_exercise`, `_get_user_test_sentences`, `_get_user_session_size`, `_enrich_session`. Removed unused imports (`Tuple`, `PHASE_MAP`, `TIER_TO_PHASE`, `random.choices`).
- `wiki/algorithms/ladder-implementation-analysis.md` — Front-matter `open_questions` reduced from 3 → 2 (bucket-5 question resolved). Priority 1 and Priority 3 marked ✅ Resolved with implementation notes. Architecture line updated: two SQL-RPC surfaces, no broken edge. Comparison-with-old-audit table's "Two competing session builders" row rewritten to describe the consolidated state. Impact-assessment table folds P1+P3 into a single ✅ row.
- `wiki/algorithms/ladder-implementation-analysis.tech.md` — "Architecture: Two Paths (Plus One Broken Edge)" renamed to "Architecture: Two SQL-RPC Surfaces" and the Path B / Broken Edge sections rewritten to describe the new CTE pipeline. File inventory updated (`exercise_session_service.py` 1003 → 500 lines; new row for `phase9_get_exercise_session.sql`). "Daily Session: `ExerciseSessionService._compute_session()`" section replaced with "Daily Session: `get_exercise_session` RPC (Phase 9)" — full CTE table, slot distribution, exercise_type_phase_weight rule, virtual-sentences-stay-Python paragraph. Implementation-status table: three rows flipped to ✅ Live (Phase 9) for N+1 fix, bucket-5 delegation, full SQL consolidation.
- `wiki/database/rpcs.tech.md` — New "Exercise Session (Phase 9 Daily Mixed Session)" section before Security Summary with full per-RPC documentation for `exercise_type_phase_weight`, `tier_window_for_p_known`, `tier_to_phase`, `get_exercise_session`. Overview totals updated: 57 → 61 functions; SECURITY INVOKER 33 → 37; IMMUTABLE 13 → 16; STABLE 11 → 12. New category row "Exercise Session (Phase 9) | 4".
- `wiki/api/rpcs.tech.md` — `/api/exercises` blurb rewritten to describe the Phase 9 RPC backing and Python wrapper responsibilities (call RPC + append virtuals + cache + enrich); the "Bucket 5 broken" callout removed. RPC-from-API table extended with `get_exercise_session`, `get_session_senses`, `bkt_apply_lapse_penalty`.
- `wiki/database/schema.tech.md` — Added a new "Exercise Serving (Daily Mixed Session, Phase 9)" subsection listing `get_exercise_session` + the three helpers. Removed the obsolete note about Python being the daily-session builder.
- `wiki/features/vocab-dojo.tech.md` — Future Direction first bullet flipped from open to ✅ Shipped, linking to phase9_get_exercise_session.sql.
- `wiki/index.md` — Bumped `last_updated` to 2026-05-12.

Notes: The session response shape (`/api/exercises/session` JSON) is unchanged — frontend takes no diff. The new CTE pipeline still produces `out_phase` per row, the Python wrapper still maps `slot_type` exactly like before. The slight phase-weighting semantic drift (Python used `random.choices` with weights; SQL uses `ORDER BY weight DESC, RANDOM()`) is acceptable: at session_size=20 the per-type expectation matches within ±1 exercise. Virtual jumbled-sentence picks behave identically because the Python `_get_user_test_sentences` is unchanged.

Verification:
1. **Apply migration**: `phase9_get_exercise_session.sql` is idempotent (`CREATE OR REPLACE FUNCTION`). Run via Supabase MCP `apply_migration` against the dev DB, then `SELECT * FROM get_exercise_session('<test_user_uuid>', 2, 20);` and confirm a row count up to 20 with `slot_type` values across `due_review / active_learning / new_word / ladder / supplementary`.
2. **Bucket-5 surfaces ladder content**: `SELECT count(*) FROM user_exercise_sessions WHERE exercise_ids @> '[{"slot_type":"ladder"}]'::jsonb;` should rise from 0 (pre-deploy) to nonzero after a real user opens `/api/exercises/session`.
3. **Anti-repetition**: complete an exercise via `/api/exercises/attempt`, then force a session rebuild (`DELETE FROM user_exercise_sessions WHERE user_id = '<uuid>'` then GET `/api/exercises/session`). Confirm the just-completed exercise is absent from the new session unless no alternative exists for its sense.
4. **No regression on existing endpoints**: a smoke test of GET `/api/exercises/session?language_id=2` should return the same response shape (status 200, JSON keys: `load_date`, `exercises[]`, `progress`, `session_size`).
5. **Python syntax**: `python -c "from services.exercise_session_service import ExerciseSessionService"` ✅ verified.

---

## 2026-05-11 ingest | phase8_momentum_bands.sql + ladder service refresh

Source: User-directed wiki refresh in response to the "consolidate session builders + proper promotion/demotion" architectural-debt task. Investigation revealed the wiki's ladder pages were anchored to a pre-Phase-8 world. The actual codebase moved to a Momentum Bands system (per-family BKT × 4 rings × 2 threshold gates × 8-exercise stress test → FSRS-4.5 graduation) on 2026-04-18 via [migrations/phase8_momentum_bands.sql](../migrations/phase8_momentum_bands.sql), and the wiki had never been brought current.

Material discrepancies identified before writing:
- Wiki described promotion as "2 first-try successes across separate sessions"; actual progression is ring-clearing on family-confidence thresholds (0.50 / 0.65 / 0.72) plus two threshold gates plus a stress test.
- Wiki said `LadderService` was one of two competing session builders. Actually, `LadderService` is now a thin RPC wrapper with no session-building methods. The competing builders are the SQL `get_ladder_session` RPC (canonical, used by `/api/vocab-dojo/session`) and the Python 6-bucket `ExerciseSessionService` (used by `/api/exercises/session`). The latter's bucket-5 silently fails because it calls a `LadderService.get_words_for_session()` method that doesn't exist.
- Wiki said Phase 4 counter columns were missing; they're present and *written by Phase 8 RPC every attempt*, but no progression code reads them.
- Wiki featured a `get_exercise_session` RPC SQL block — that RPC was never built; the file documented an aspirational design.

**Files created: 1**
- `wiki/decisions/ADR-005-momentum-bands.md` — New decision record. Captures the move from the original 10-level chain / Phase-4-counter design to the Momentum Bands model. Records consequences (graduation FSRS bootstrap, family-level skill resolution, concrete-noun routing preserved) and constraints (all `user_word_ladder` mutations must go through the three RPCs; the `word_state` CHECK is rewritten; Phase 4 counters are de facto observability).

**Files rewritten: 6**
- `wiki/algorithms/vocabulary-ladder.md` — Replaced "promote on 2 cross-session successes" prose with the ring/family/gate/stress-test model. New tables: levels-by-ring-with-family, six cognitive families with weights, ring thresholds, momentum bands. Documented the lapse path and FSRS handoff. New `word_states` list (`new/active/gated/pre_mastery/relearning/mastered`).
- `wiki/algorithms/vocabulary-ladder.tech.md` — Replaced the imaginary `user_word_progress` schema and the Python promotion/demotion sketch with the actual current state: combined Phase 4 + Phase 8 DDL for `user_word_ladder`, full RPC surface (`ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`, `get_ladder_session`, plus helpers), family BKT update formulas with context-aware learn/slip rates, momentum band scheduling, FSRS graduation seeding equations, A/B variant logic.
- `wiki/algorithms/ladder-implementation-analysis.md` — Reframed as the 2026-05-11 audit. Old "critical discrepancies" table now reads as 6 obsolete claims → 6 current realities. New "what works well" list (atomic SQL progression, family-level skill resolution, single RPC source of truth, frontend-friendly returns, A/B variants). New "what needs improvement" priorities: P1 fix broken bucket-5, P2 wire-or-drop Phase 4 counters, P3 consolidate daily session into SQL, P4 L10 capstone, P5 IRT calibration. Three open questions in frontmatter.
- `wiki/algorithms/ladder-implementation-analysis.tech.md` — New architecture diagrams (Path A dojo, Path B daily mixed, broken bucket-5 edge). Detailed `ladder_record_attempt` flow chart. Phase 4 counter handling block quoted from SQL. Updated file inventory. New implementation-status table (13 rows: shipped / not done / open). A/B variant sentence-index assignments.
- `wiki/features/vocab-dojo.md` — Replaced the "40/40/20 phase-gated" description with the priority-scoring model (0.35·overdue + 0.25·weakness + 0.20·gate + 0.10·novelty + 0.10·relapse). Documented family targeting, gate/stress-test branching, anti-repetition, and explicit "dojo ≠ daily mixed session" distinction.
- `wiki/features/vocab-dojo.tech.md` — Replaced the fictional `get_exercise_session` RPC SQL with the real `get_ladder_session` CTE pipeline. Full endpoint surface table (7 endpoints). Lazy ladder-row init flow. Family targeting + variant alternation details.

**Files updated: 4**
- `wiki/database/schema.tech.md` — Rewrote the `user_word_ladder` table section. Added Phase 8 columns (`family_confidence` jsonb, `gates_passed` jsonb, `current_ring` int, `stress_test_score` real, `last_exercised_family` text). Updated `word_state` CHECK to Phase 8 enum (`new/active/gated/pre_mastery/relearning/mastered`). Annotated which Phase 4 columns are "written but never read." Added `idx_user_word_ladder_ring`.
- `wiki/database/rpcs.tech.md` — Added a "Vocabulary Ladder (Phase 8 Momentum Bands)" section before the security summary, with full per-RPC documentation for `ladder_get_family`, `ladder_get_ring`, `ladder_ring_families`, `ladder_compute_p_known`, `fsrs_schedule_review`, `ladder_record_attempt`, `ladder_pass_gate`, `ladder_graduate`, `get_ladder_session`. Updated the Overview totals (48 → 57 functions; SECURITY INVOKER 24 → 33).
- `wiki/api/rpcs.tech.md` — Replaced the 2-row `/api/exercises` endpoint stub with the 3-endpoint reality (`/session`, `/session/complete`, `/attempt`) plus a flag that bucket-5 is broken. Added a new `/api/vocab-dojo` blueprint section with all 7 endpoints. Extended the "RPC functions called from API" table with the four Phase 8 functions.
- `wiki/index.md` — Added the ADR-005 link; bumped `last_updated` to 2026-05-11; page count 47 → 48.

Notes: All code references in the new pages cite specific line ranges in `migrations/phase8_momentum_bands.sql`, `services/vocabulary_ladder/ladder_service.py`, `services/vocabulary_ladder/config.py`, `routes/vocab_dojo.py`, or `services/exercise_session_service.py`. Phase B of the architectural-debt plan (move the daily session into a SQL `get_exercise_session` RPC + wire the Phase 4 counters into ring gating / demotion) is deferred — these are now well-defined follow-ups recorded as `open_questions` on the analysis pages.

Verification:
1. `grep -r "promote on single first-try success" wiki/` returns nothing.
2. `grep -r "fragile_receptive\|stable_receptive\|fragile_productive\|stable_productive" wiki/` returns nothing (old word_state values purged).
3. `wiki/index.md` lists ADR-005; opening the ADR resolves the link.
4. Every claim about a SQL RPC in the rewritten pages cites a specific line range in `migrations/phase8_momentum_bands.sql`.

---

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
