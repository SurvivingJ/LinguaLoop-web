# Activity Log

## [2026-08-16] execute | TASK-718 — cross-model judge A/B; the zh divergence was the judge
Pages updated: [[evaluations/distractor-judge-language-divergence-2026-08-16]] (new §11),
[[tasklist/distractor-judge-calibration.tasks]], [[tasklist/master]].
Judge spend **$1.11** (600 calls, 11 min, `pipeline='diag'`). Files: new
`scripts/measure_judge_flag_rate.py`, new `migrations/distractor_judge_model_zh_ja_gemini.sql`
(applied live).

**Verdict: judge-driven, ~100%.** A 2×2×3 factorial over the frozen 150-question sample —
`{v4, v5} × {qwen3.6-flash, gemini-3.1-flash-lite} × {zh, en, ja}`, identical content in every arm,
subject line off to match production. Question-level rejects on the live v4 prompt:

| lang | qwen | gemini |
|------|------|--------|
| zh | 16/50 (32%) | **1/50 (2%)** |
| en | 5/50 (10%) | 2/50 (4%) |
| ja | 4/50 (8%) | 3/50 (6%) |

Read the columns. Under a **common judge** zh is the *cleanest* of the three, not the worst; the
published 26pp zh–en gap becomes **−2pp**. The mechanism is a qwen×Chinese interaction, not general
harshness — qwen scores en 10% / ja 8% but zh 32%. Widened past the task's v5-only spec because v5
is reverted and v4 is live, and to add the crossover cell (qwen on English) the original design
omitted.

**The decisive number:** of the 25 zh distractors qwen rated 2 (reject), gemini rated **19 a 4 and
6 a 5** — none in its own reject or review band. Question-level the zh reject sets are **disjoint**
(both 0, qwen-only 16, gemini-only 1). zh `vocabulary_context`, stuck at 9/16 across all four
TASK-717 prompt arms, is **1/16** under gemini.

**Applied:** zh + ja → `google/gemini-3.1-flash-lite` (v4 live and v5 retained, so activating v5
later cannot silently restore qwen). Side effects: a middle band appears in zh (1) and ja (2), so
`generation_review_queue` is no longer English-only; per-call cost drops **6.7×**. Band 1 fired for
the first time ever (3 in 1,800 ratings). v5 stays inactive — harmful under *both* models.

**What this does not settle, and it changes the plan:** inter-judge agreement on the reject class is
~0, so no model's reject signal is validated in absolute terms — the support for "the zh rejects
were false" remains the manual read in §5. gemini also missed the one zh reject §5 judged
defensible, so the swap likely trades some recall for precision by an unmeasured amount. **A gold
set now gates TASK-719/720** (unfiled, needs an ID); TASK-721/722 are unaffected and are the best
next work. Not Started 10 → **9**.

## [2026-08-16] execute | TASK-717 — judge prompt v5 built, measured, and reverted
Pages updated: [[evaluations/distractor-judge-language-divergence-2026-08-16]] (new §10),
[[tasklist/distractor-judge-calibration.tasks]], [[tasklist/master]].
Suite 1781 → **1792 passed, 3 skipped**. Judge spend $1.48 (600 calls, `pipeline='diag'`).

**The task's own premises did not survive measurement.** Both §4 hypotheses were tested on the
frozen 150-question sample and both are wrong, so v5 was rolled back the same day it shipped.

Four arms, identical content, models unchanged: **B** v4 baseline · **D** v4 + subject line ·
**C** v5 rubric only · **A** v5 + subject line. Question-level rejects —
zh 18/18/17/15, en 2/2/**5**/**4**, ja 6/**8**/4/**11** (published baseline: 15/2/6).

1. **zh `vocabulary_context` was 9/16 in all four arms.** Not reduced, not noisy — identical
   under every intervention. §4 read this bucket as a rubric mis-specification; it is judge-model
   behaviour, matching the established fact that `qwen3.6-flash` collapses to {5, 4, 2}. This
   **promotes TASK-718 to the load-bearing task** and means the bucket is unreachable from the
   prompt layer.
2. **The type-conditional rubric backfired in English**: 0 → 5 `vocabulary_context` rejects. The
   bullet closed with "2 is reserved for an option that is not a possible meaning of the
   expression at all" — meant to narrow band 2, it instead *named a condition under which band 2
   applies* to vocab questions, and gemini took it up. Generalisable: stating a reject condition
   raises its use even inside a sentence restricting it.
3. **The domain slot works backwards from §4's model.** An authoritative subject line was meant
   to loosen the off-topic band; "concept + five keywords" is *narrower* than a
   passage-inferred domain, so it tightened it. ja rose in both arms containing it.
4. **§8's caveat is also backwards** — passing the `type_code` string moved zh 15 → 18, so the
   published baseline was not an over-estimate. §1's numbers stand.

Shipped and kept: the caller plumbing (`keywords=` finally reaching prompt slot `{5}`), with a
mutation-verified regression test — deleting the argument fails the suite. Gated
`JUDGE_SUBJECT_KEYWORDS`, **default off**, with both branches pinned by tests so the off-state
stays a documented decision rather than decaying back into the silent dead-parameter bug the task
existed to fix. v5 rows retained `is_active = false` for TASK-718 to re-test under another model.

## [2026-08-11] execute | Exercise Generation v2 — nine `[~]` rows closed, two latent defects fixed
TASK-517, 520, 522, 523, 525, 527, 529, 532, 533 → `[x]`. Suite 1634 → **1676 passed, 3 skipped**.
Exercise Generation v2 In Progress 14 → **5** (515, 521, 526, 530, 531 — all spend- or
review-gated). Pages updated: [[tasklist/master]], [[tasklist/archive/exercise-generation-v2.tasks]].

**Three of the nine needed no code — only the checkbox was stale.** The "migration not applied
live" notes on TASK-520/522/527 were false: all sixteen prompt rows were already present. Only
TASK-525's three `translation_uniqueness_judge` rows were genuinely missing. Lesson for the next
session: query `prompt_templates` before believing a not-applied note.

Real work: the queue-drain advisory lock + 04:15 cron + `subscribe_topup` (517); the OANC
collocation list vendored at 73.7k dependency-parsed pairs (523); `dim_character_components`
populated with 27,131 rows from cjk-decomp (Apache-2.0) + Unihan, after rejecting cjkvi-ids as
GPLv2 (529); the `cloze_typed` IME renderer with grading moved server-side (532); and the
speed-round bonus block appended outside the planner per ADR-021 (533).

**Two latent defects, both found by doing the work rather than by looking for them:**
`deterministic._load_builders()` guarded on `if _REGISTRY:`, so importing any single builder
module disabled the other six — and TASK-532's own `routes/practice.py` import was exactly that
trigger. `BundledCollocationList.load()` treated *any* row starting `head` as the header,
discarding every collocation headed by the noun *head*. Both fixed and pinned by tests.

Also closed two repo-record gaps (`migrations/CLAUDE.md`): `dim_character_components` and the
three `dim_counter_*` tables were live with no migration file at all.

TASK-530 advanced but still `[~]`: `get_counter_drill_session` applied live and verified over the
full corpus (0 bad distractor counts, 0 answer/foil overlap, 7 multi-acceptable nouns), and
`build_counter_dictionary.py` seeded 54 counters / 173 pairs. Route, template, LLM curation pass
and the ladder round-trip remain.

## [2026-08-11] execute | TASK-537–540 — ladder numeric-key contract shipped & applied live
All four tasks done; 16/16 prompt rows live on project `kpfqrjtfxmujzolwsvdq`. Suite 1609 → **1634
passed, 3 skipped** (25 new tests; the two ladder test files went 56 → 81).

**537 — schema layer.** `_shared.py` now owns the contract: `OPTIONS_KEY='0'`,
`ERROR_ESCAPE_KEY='9'`, `OPT_TEXT/IS_CORRECT/EXPLANATION/PART_OF_SPEECH = 0/1/2/3`,
`OPTION_KEY_LEGEND`, plus `read_index` (accepts `'0'` **and** `0`, since JSON gives strings but
fixtures give ints), `error_escape`, `validate_escape`, and `labelled()`. Matched P1's *mechanism*
rather than inventing one — numeric string keys, a `KEY_MAP` in `vocabulary_ladder/config.py`, and
the existing `remap_keys()` — but used the spec's 0-based numbering. **P2's `OPTION_KEY_MAP` is
1-based and was left alone**: it is live, its stored assets are bound to that numbering, and
aligning it would mean re-authoring P2 for no gain, so a new `LADDER_OPTION_KEY_MAP` sits beside
it with a comment explaining why the two differ. Error strings name field *and* index
(`base_form (key 1): missing non-empty string`), which retires the one real argument the
`ladder_l4_morphology.py` docstring made against numeric keys — that docstring now records why the
reasoning was superseded instead of contradicting the code.

**538 — 16 prompt bodies.** Every row declares its legend in its own language before the rules.
Rewrote the ZH L4 row too, though it is inert (`morphology_slot` lang 1 is `is_enabled = FALSE`):
an inert row left on the old contract is the one most likely to be enabled later by someone who
does not know it was skipped. Two things the numeric legend *forced*, both easy to miss: the
`relation` value and the particle `error_tags` values must stay ASCII enums, so each ZH/JA prompt
now says so explicitly — a legend reading "1：关系类型" otherwise invites a translated `"近义词"`
that fails `ladder_typed.RELATIONS`. Row 9 (JA `syn_ant`) gained the worked polysemy example it
lacked — 甘い taught as *taste* must not take 厳しい, the antonym of the *lenient* sense — and the
JA relation judge, which stated the same rule abstractly, now names the same pair.

**539 — consumers + provider-enforced JSON.** `options_to_content` is the boundary: indices stop
there and `word_assets.content` still receives descriptive keys, pinned by a test. The escape (key
9) routes to the **clean-skip** branch (`{}`), not the failure branch, and is not retried. Seven
logical ladder call sites moved to `response_format='json_object'` — implemented in three code
locations (`_split_base` serves all five generators, plus the two judge modules). Per fact 4 the
judges were **not** re-polarised; instead a parametrised test asserts both give the same verdict at
every rating 1–5, and a second asserts they share one `likert_to_verdict` object.

**540 — live apply.** The 6 EN rows needed `UPDATE`: all three migration files carried
`ON CONFLICT … DO NOTHING`, which made a corrected re-run a silent no-op, so every row is now
`DO UPDATE` and the files are re-runnable *and* corrective. Verified live: 16 rows `is_active`,
legend present, no `"options"`/`"rating"`/`"is_correct"` surviving, and each row's
`md5(template_text)` hash-matched against the `$PROMPT$` body in its migration file (16/16) — the
bodies were transcribed into MCP calls, so the hash check is what makes "the DB has what the repo
says" a fact rather than an assumption. Step 7 (the `vocab_prompt3_transforms` narrowing note),
held back on 2026-08-10, applied to the three active rows; the one inactive lang-2 row is untouched,
as its `WHERE is_active = true` intends.

**Two corrections to the task file itself**, both recorded there: its verification query used
`task_name LIKE 'ladder_%'`, which also matches 12 rows owned by other tasks
(`ladder_collocation_judge`, `ladder_p1_sentence_judge`, `ladder_sentence_validity_judge`,
`ladder_l1_distractor_judge` × 3) — the count reads 28, not 16, so it is now scoped by the eight
task_names. And the L8 schema no longer validates a `sentence_index`: the spec table omits it and
the generator supplies its own verified index, so a model-nominated one could only disagree with
the sentence the model was shown.

## [2026-08-10] plan | TASK-537–540 filed — ladder prompt numeric-key output contract
User review of the 16 ladder prompts produced four requirements: numeric JSON keys with the
legend declared in-prompt (so English field names stop contaminating ZH/JA generation), a worked
example in every rule that needs one, provider-enforced JSON, and judge-polarity parity.
Decomposed into TASK-537 (schema layer) → 538 (16 prompt bodies) / 539 (generators, judges,
`json_object`) → 540 (tests + live apply). Filed as `tasklist/ladder-numeric-keys.tasks.md`;
4 rows added to master.

Three findings recorded in that file so a cold session need not re-derive them:
(a) the numeric-key convention already exists in `prompt1_core.py:94,368` — match it, and fix the
`ladder_l4_morphology.py` docstring that argues against it; (b) `prompt_version` stays at 1
because `word_assets` holds **0** `llm_types%` rows, so nothing is bound to the v1 shape;
(c) the 6 live EN rows need `UPDATE`, since `ON CONFLICT DO NOTHING` makes a corrected re-run a
silent no-op.
**Corrected a claim from earlier in this session:** the particle and relation judges are already
polarity-aligned — same `likert_to_verdict`, same direction, no per-judge threshold. There is no
inversion bug; the only work is a regression test pinning the shared polarity.

## [2026-08-10] task | TASK-520/522 English prompt rows applied live
Applied 6 English `prompt_templates` rows to project `kpfqrjtfxmujzolwsvdq` after user review:
`ladder_l4_morphology_generation` (sonnet-4-6), `ladder_l8_collocation_repair_generation`
(gemini-3.5-flash), `ladder_syn_ant_generation` + `ladder_word_family_generation` (sonnet-4-6),
`ladder_relation_judge` + `ladder_word_family_judge` (gemini-2.5-flash-lite). All lang 2, v1,
`is_active = true`, verified by `SELECT` on the six task_names.
**Deliberately NOT applied:** the zh/ja rows in the same two migration files, and all of
`particle_selection_prompts.sql` (JA-only). Reason: every row carries
`ON CONFLICT ... DO NOTHING`, so seeding before review would make a corrected re-run a silent
no-op. Also held: step 7 of `ladder_prompt_split_l4_l8.sql` (the description annotation on the
surviving `vocab_prompt3_transforms` rows), so the remainder still applies as one unit.
EN `word_family` is now fully live — that generator is English-only by design.

## [2026-08-10] lint | Reconciled 9 stale task headers in exercise-generation-v2.tasks.md
The per-task `**Status:**` headers for TASK-515, 516, 517, 518, 521, 528, 529, 530 and 532
still read `[ ] Not Started` for work that shipped on 2026-08-08. The session-status summary
table at the foot of the same file and `tasklist/master.md` already agreed with each other and
with the code; only the headers had drifted. Rewrote all nine to match, carrying the summary
table's "what is outstanding" note into each status line so the header alone now says why a
task is `[~]` rather than `[x]`. No status was *changed* — 516/518/528 → `[x]`,
515/517/521/529/530/532 → `[~]`. The file now contains zero `[ ] Not Started` rows, which
matches the true 5xx picture: 19 done, 14 in progress, 3 blocked on post-launch data.
Second time this file has misled a session; see memory `tasklist-status-drifts-from-code`.

## [2026-08-08] task | TASK-510/512/519 done, TASK-514 partial — Exercise Generation v2 pre-batch hardening
Four rows attempted from Exercise Generation v2; three closed, one deliberately left `[~]`.
One migration applied live to `kpfqrjtfxmujzolwsvdq` and verified. Full Python suite
**1,342 passed / 3 skipped** (the skips are self-guarding — see TASK-514). 26 files touched.

**TASK-510 — slug health cron + fail-closed batch judges.** Two past outages came from
delisted model slugs: the model lives in `prompt_templates`, not code, so a delisting is
invisible to review, and judges fell open and shipped unjudged content. Detection half:
`services/model_health.py` probes every DISTINCT active slug against the provider's
`/models`, memoised 15 min. Only `provider='openrouter'` rows are probed — an ollama slug
missing from OpenRouter is not rot, so those report under `skipped`. Routing suffixes
(`:free`, `@preset/…`) resolve against the bare id. A probe failure sets `error` and leaves
`ok` True: a flaky network must not manufacture a false "everything is dead" banner.
Prevention half: `judges/base.py` gains `batch_mode()` — a **thread-local** flag, so a batch
in an APScheduler thread cannot flip the contract for a request thread in the same process —
plus `JudgeUnavailable` and `guard_fail_open()`. Every judge already funnelled errors through
`safe_accept()`, so one chokepoint converts them all.

*Judgement call:* `safe_accept` (judge **outage**) now raises in batch mode, but a new
`accept_item()` handles **per-item** gaps (one unparseable rating in a healthy response) and
never raises. Killing a 3,000-sense batch over a single malformed entry would be worse than
shipping that item, and the v3 Likert contract already forbids manufacturing a rejection from
a missing verdict. Migrated call sites: `p1_sentences.py` ×2, `sentence_validity.py` ×2, and
collocation's "nothing to judge" early return.

Cron `slug_health_nightly` @ 04:10 UTC; advisory lock key 1298417772 ('MdHl'), distinct from
IRT and the Study-Plan pacer's 1467840848. `migrations/task510_model_health_advisory_lock.sql`
**applied live 2026-08-08** — verified 2 functions present, acquire→true, release→true, 0
locks left. Admin banner + manual re-check endpoint. `tests/test_model_health.py` (18).

**TASK-519 — nl-keyed content maps.** New `services/exercise_generation/schemas/` package:
TL-facing content stays flat and nl-free, nl-facing text lives under `content.nl.<code>`.
Reading is tolerant (`validate_envelope` no-ops below `schema_version 2`, so the v1 corpus is
not retroactively invalidated); writing is strict. `ExerciseValidator` runs the envelope check
first and returns immediately on violation — otherwise every nl field reports "missing" and
buries the real cause — then validates v2 through a flattened view so per-type checkers keep
their expected field names. Serve side: `exercise-renderers.js` flattens once in `dispatch()`,
leaving all ~16 renderers untouched.

*The lint tests earned their keep immediately*, finding two real offenders:
`ExerciseGenerationOrchestrator.__init__(nl_language_code='en')` — the literal that actually
made the corpus English-only, now `Config.DEFAULT_NATIVE_LANGUAGE`, one declared
env-overridable knob; and `generators/style.py`, **not fixed by design** since TASK-512
freezes that path, recorded in `_FROZEN_LEGACY` so the exemption is visible and reviewable.
`tests/test_nl_keyed_content.py` (22).

**TASK-512 — ladder is the sole vocab generator.** `source_type='vocabulary'` now raises from
**both** `_get_distribution()` and `_build_generators()`, so there is no path back in via
either. `VOCABULARY_DISTRIBUTION` deleted. `run_vocabulary_batch()` routes to
`generate_for_sense()` → `render_all()` and **skips rendering when assets failed** — rendering
half-built assets is how blank exercises reach learners. Freeze table added to
[[features/exercises.tech]]. *Not verified:* the AC's live smoke runs for
grammar/conversation/style need LLM + DB spend and were not run.

**TASK-514 — left `[~]`, and the reason matters.** B1 (non-destructive regen) and B6 (P1
retry + targeted repair) were found **already implemented**; the `[ ] Not Started` status was
stale. B5 is half done. Level-gating helpers (`requirements_met`,
`active_levels_for_context`, `_capability_context`) landed, but the AC — "ZH concrete noun's
plan contains no `morphology_slot`" — **cannot be met by gating levels**, because TASK-504
seeded richer L4 rows than the task text assumed: ZH concrete L4 is also served by
`classifier_match` (TASK-528) and `cloze_typed` (TASK-532), so the level legitimately
survives. Suppressing the *type* needs per-type gating in `prompt3_transforms.py`. The three
skipped tests are the guards that surfaced this: they `skip` with a message when a
non-morphology L4 capability exists rather than passing vacuously.
`tests/test_matrix_gated_planning.py` (14).

**Still blocked, unchanged:** TASK-515 (top-1,000 × 3-language batch) is a paid multi-night
run needing operator budget approval — not started. TASK-534/535/536 remain `[?]`, gated on
post-launch attempt volume that does not exist. Nine tasks (518, 520, 523, 526, 527, 531-533)
can be coded now but cannot have their acceptance criteria verified until 515 runs.

## [2026-08-07] task | TASK-714/715/716 — plannable surfaces, tier-scaled dictation, local-day boundary
Closes the last three open rows in Daily Session Hardening; the feature now has no open work.
All five migrations applied live and verified against `kpfqrjtfxmujzolwsvdq`. Full suite
1290 passed / 1 skipped; 3 new test files (106 cases).

**TASK-714 (ADR-021, F11).** `flashcards` and `dual_translation` join the weekly budget. They are
not `dim_test_types` rows and never resolve to an ELO-rated `tests` row, so rather than inventing
type codes the resolver splits its candidate rows into `kind='test'` vs `kind='surface'`: both are
budgeted by the same greedy value-per-minute loop and compete for the same minutes, but surfaces
hydrate from their own pools (`user_flashcards` due today, ≤15 cards per slot; `dt_passage` rows
`/api/dual-translation/next` can actually serve) and never enter `chosen_tests`, so `test_ids`,
`daily_test_load_items`, ELO and the retry/replay machinery are untouched. `surface_counts` in
`daily_session_targets` drives queue composition; new `players/flashcards.js` and
`players/dual_translation.js` mount off `item.kind`. `record_session_progress` gained
`p_kind='surface'`, called from `POST /complete-block` with a deterministic uuid5 so retries
dedupe — without it every completed block would have moved no counter (the F2/TASK-701 shape).
Verified live: `completed_counts` → `{"flashcards":1,"dual_translation":1}`, second call `false`.

**Budgets do not lengthen the day.** Counting the new surfaces adds real minutes to
`total_weekly_minutes`, which would have *inflated* `today_budget` — the opposite of the intent.
`compute_weekly_plan` now clamps the week to `daily_minutes * 7`, so the new surfaces displace
lower-value test slots instead. That is what ADR-021 means by "DT competes directly with test time".

**TASK-715 (ADR-021, second decision).** The flat 80-word dictation cap became per-tier
(T1 80 · T2 120 · T3 160 · T4 220 · T5 300 · T6 400) via `public.dictation_max_words(difficulty)`,
mirrored in `services/dictation/cap.py`. Every value is `>=` 80, so the eligible set only grows and
no existing test needs regenerating. `test_time_estimate` gained a 2-arg tier-aware overload
(`2.0 + cap/20`: 6.0 at T1, unchanged from the old scalar, → 22.0 at T6); the resolver prices a
dictation slot at the learner's *expected* tier when budgeting and the placed test's *actual* tier
when accounting. Two latent defects surfaced and were fixed: the stored diff was capped at 200
entries (chosen when passages were ≤80 words — it would have truncated a T6 attempt mid-passage
with no error), and `get_word_count_range` was feeding the prose prompt
`dim_complexity_tiers.word_count_max`, which is a **vocabulary size** (up to 25000), not a passage
length — the generator was literally told to write "600-25000 words" at T6, which is why live EN
difficulty-9 transcripts average ~777 words. New T5/T6 passages will be materially shorter;
existing rows are untouched.

**TASK-716 (ADR-022, F15).** "Today" now resolves through `user_study_plans.timezone`. One shared
helper — `services/day_boundary.py`, with SQL twin `public.plan_local_date` for RPC bodies that
have no Python caller. It replaced **three** independent derivations, not two: the route, the
service, and `build_daily_session`'s `date.today()` default (the *process* timezone). A test
asserts both Python call sites reference the same function object, so a re-inlined
`datetime.now(utc)` fails the build. Unusable zones fail safe to UTC at every layer (ADR-020);
route validation now rejects new bad values. **`week_start_date` moved too** — verified that at
2026-08-09 15:30 UTC a UTC+9 learner is already on Monday 2026-08-10 while UTC says week
2026-08-03, so leaving it would have credited 9 hours of completions to a week the resolver was no
longer reading. Backwards timezone moves are handled by the caller's existing-row short-circuit
(serve as-is, never re-solve). Cutover: no backfill — the zone a historical row was written under
is recorded nowhere.

**Caught before shipping:** the first draft hydrated DT against `dt_passage.status = 'approved'`,
a value that does not exist in that table (it is `'active'`), so DT would have hydrated zero slots
forever while reporting a shortfall. The predicate now mirrors `/next` exactly. Also archived
`task702_build_daily_session.sql` and `task702_get_recommended_tests_rank_cap.sql`;
`phase13_build_daily_session.sql` and `phase18_practice_time_seconds.sql` deliberately kept under
archive rule #4.

## [2026-07-20] task | TASK-707 — Legacy `_compute_daily_load` fallback correctness (type labels + ELO band)
Closes F9 on the de-facto Monday path. The step-4 last-resort fallback in `services/test_service.py`
hardcoded `test_type='listening'` (wrong player mounted, wrong skill rated) and computed an ELO band
from `user_elo_after` — a column the step-1 attempts `select(...)` never fetched, so `user_elo` was
always 1200 and the band always [1000,1400] (dead). Fix: (1) added `user_elo_after` to the step-1
`test_attempts` select so the band is live; (2) rewrote step 4 to read `test_skill_ratings` instead of
the bare `tests` table — `select('test_id, elo_rating, dim_test_types(type_code),
tests!inner(id, is_active, language_id)')` scoped by `tests.language_id` + `tests.is_active`, with the
`gte/lte` band centred on the user's most recent `user_elo_after`. Each pick now carries its real
`type_code` (defaults to `'listening'` only if the type embed is absent). New unit test
`tests/test_daily_load_fallback_type.py` (4 cases, fake Supabase admin, no live DB): dictation-only
pool → items labeled `dictation`; fallback queries `test_skill_ratings` not `tests`; default band
[1000,1400] when unrated; band shifts to [1300,1700] for `user_elo_after=1500` (proves the column is
now read). `pytest tests/ -k daily_load` → 12 passed. Wiki: TASK-707 → Done in [[tasklist/master]]
(counts 43→42 / 99→100) + [[tasklist/archive/daily-session-hardening.tasks]]. See
[[resolver-hydration-skill-gap]].

## [2026-07-20] task | TASK-705 — Make build_daily_session same-day-safe; built + verified live (rollback-only), live apply owed
Closes F6: the resolver's `ON CONFLICT (user_id,language_id,load_date) DO UPDATE SET completed_test_ids='[]'` plus the unconditional `daily_test_load_items` rebuild-as-`is_completed=false` erased a learner's progress on **any** same-day re-solve (E_NOWEEK lazy-compute retry, manual regenerate, Sunday pacer overlap) — only caller-side "row already exists → skip" checks in `get_or_create_daily_load` masked it. **Folded into `task702_build_daily_session.sql`** (the same file TASK-702/704 own). Before the retry/hydration passes, a new block reads the prior row's `test_ids`+`completed_test_ids` and **carries over every already-completed slot** (element of `test_ids` whose `test_id` ∈ `completed_test_ids`) into `pg_temp.chosen_tests` with its original `slot_type`/`original_percentage` and `is_completed=true`, then **decrements that skill's budgeted `skill_counts`** (same free-a-slot mechanic as the retry pick) so only the still-incomplete portion is re-resolved — retained-completed + fresh ≈ today's budget, `used_minutes` stays sane. New `is_completed boolean` column on `chosen_tests`; the `ON CONFLICT` branch **no longer touches `completed_test_ids` or `completed_blocks`** (completed_blocks was never in the SET list; the wipe was `completed_test_ids` only), and the items-mirror INSERT now carries per-slot `ct.is_completed`, keeping `completed_test_ids ⊆ test_ids`. Added `NOT IN (SELECT test_id FROM chosen_tests)` guards to the retry pick, the `get_recommended_tests` hydration, and the `classifier_drill` sentinel fill so a retained slot is never re-inserted as a duplicate (defensive: real completions are attempts and thus already excluded by `get_recommended_tests`, but a completion that isn't an attempt would otherwise double-insert). Shortfall bookkeeping (`hydrated_counts`/`replay_counts`) gained `AND NOT is_completed` so carried-over slots neither mask nor inflate this call's fresh fill vs `requested_counts`. **Verified live in a rollback-only txn** (`kpfqrjtfxmujzolwsvdq`, 2026-07-20): synthetic plan+week+two never-attempted listening tests for an existing user in `en`; first call → 2 slots; mark test A complete + `completed_blocks=["practice_acq_1"]`; second call → `completed_test_ids` still has A, `completed_blocks` intact, A retained exactly once, incomplete slot B re-resolved, `daily_test_load_items` A `is_completed=true`; all 5 assertions passed, whole txn `ROLLBACK` (nothing persisted). Confirmed a `RAISE EXCEPTION` sanity-check surfaces as an error so "clean run = pass" is trustworthy. **SQL unit test** `tests/sql/test_task705_same_day_safe.sql` (new; self-contained rollback-only double-call, first `.sql` test in the repo — the DB-side counterpart to `tests/test_daily_load_retry_slot.py`). **Live apply OWED:** the `CREATE OR REPLACE` to persist the new function was blocked by the auto-mode classifier; live still runs the TASK-704 (no-705) body — the user must apply `task702_build_daily_session.sql`. See [[resolver-hydration-skill-gap]]. Wiki updated: [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-19] task | TASK-704 — Retry slots in the plan path (ADR-006); built, tested, applied live
Closes F5 and re-lands ADR-006. `build_daily_session` emitted only `slot_type='new'`; the reduced-volatility retry mechanic ([[decisions/ADR-006-retry-slot-reduced-elo]]) ran only in the legacy `_compute_daily_load`. User scoped **"Both A+B now"** because criterion 3 ("ELO uses the ADR-006 damped path") could not be met by the resolver alone — the live `process_test_submission` no longer had any `slot_type`/`elo_reduction_factor` path (phase14/CR-04 drift, see [[process-test-submission-cr04-drift]]), so the damping had to be re-landed. Both applied live (`kpfqrjtfxmujzolwsvdq`) and mirrored in repo. **Part A** `task702_build_daily_session.sql` (folded per the task): before the hydration loop, select the single worst sub-70% latest attempt older than 24h (`DISTINCT ON (test_id)` → worst `percentage`, oldest first), stamp it `slot_type='retry'` with `original_percentage`, and **free one budgeted `new` slot of the same skill** (`skill_counts` decrement + delete-if-zero) so `used_minutes` stays ~constant — additive +1 only when that skill isn't budgeted today. Bypasses the never-attempted filter (`get_recommended_tests` excludes attempted tests); respects the 24h cooldown via `created_at < NOW() - INTERVAL '24 hours'`. `test_ids` elements carry `original_percentage` on retry slots only (conditional `|| jsonb_build_object` so `new`/`replay` shapes are unchanged). **Part B** `task704_process_test_submission_retry_elo.sql` (**new**, now canonical definer of the 8-arg RPC; partG stays canonical for the QAR `response_time_ms` drop): the partG live body verbatim with the repeat-attempt `ELSE` rewritten — reduced-volatility ELO iff the test is in today's `daily_test_loads` with `slot_type='retry'` for this user+lang AND no prior attempt today already carries `elo_reduction_factor` (anti-grind, one reduced repeat/test/day). `factor = LEAST(1, GREATEST(0.20, days_since/60) + (0.25 if current−prev_best ≥ 15))`, applied in the **live inline-ELO style** (logistic expected score; user K = 32·(furigana?0.5:1)·factor, test K = 16·factor), both clamped [400,3000], factor persisted to `test_attempts.elo_reduction_factor` (no longer an orphan column). Off-slot / already-earned repeats keep the status-quo 0-ELO path. Return adds `elo_reduction_factor` + a "reduced-volatility ELO applied" message; `test_elo_change` now reports the delta on damped repeats too. **Verified live in rollback-only txns**: cloned a plan user's 2026-07-06 weekly state into the current week, seeded a 50% attempt 2 days old on one of their active listening tests → `build_daily_session` returned exactly one `retry` slot `{slot_type:'retry', original_percentage:50.0}`, `requested.listening` 2→1, `used=22 < budgeted=26`; the whole txn aborted via `RAISE EXCEPTION` (no persistence). Damping math (2-day gap, no improvement) checked separately: retry-slot detection subquery → true, factor **0.20**, user ELO **+2** (was 0 pre-fix), test ELO **−1**. **Tests** `tests/test_daily_load_retry_slot.py` (3, green — pins the retry `slot_type`/`original_percentage` normalization contract; pytest wrapper is broken in-env so run directly). Archive README: the three archived `process_test_submission*` rows now point to `task704_*` as canonical; orphan-column note updated (column written again). Wiki updated: [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-19] task | TASK-703 — Interleave the session queue (round-robin tests + chunked mid-session practice); built + tested
Closes F4: the daily session ran all tests grouped by type, then two monolithic practice blocks at the tail. **Ordering moved into `routes/study_session.py`** (Python, out of the RPC) as a pure, unit-tested layer. New `build_session_queue(tests, targets, completed_blocks, user_id, load_date)` composes: (1) `_round_robin_tests()` — groups by `test_type`, seeds group order from `_stable_seed(user_id, load_date)` (SHA-256 → 32-bit) and deque round-robins, so no two same-type tests are adjacent while another type still has items (the only same-type run is the unavoidable tail once other types exhaust); (2) `_build_practice_chunks()` + `_chunk_minutes()` — split each base `_PRACTICE_BLOCKS` budget into **≤10-min** chunks with ids `practice_acq_1`, `practice_acq_2`, `practice_maint_1`, … (`completed_blocks` jsonb already stores strings, no schema change); (3) `_interleave_practice()` — inserts the P chunks at `((i+1)·T)//(P+1)` positions so practice lands mid-session (~⅓, ⅔), not only at the end. Determinism is structural (same inputs → same order every GET), so resume is stable and `next_index` still points at the first incomplete item in the new order. `complete-block` now validates `block_id` against `_valid_practice_block_ids(targets)` (recomputed from the persisted `daily_session_targets`) instead of the two legacy base ids. **FE unchanged (verified):** `controller.js` renders dots/progress generically off `q.kind`/`q.is_completed`; `players/practice.js` already forwards `item.minutes` to `/api/practice/session?minutes=`, and `routes/practice.py` validates `minutes` 1..180 so small chunk values are honored. **Tests** `tests/test_study_session_ordering.py` — 20 green (chunk math, adjacency across seeds, mid-session placement, per-user determinism, item-preservation, resume/next_index, completed-chunk flag); `tests/test_daily_load_shortfall.py` still 5 green. Wiki updated: [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-19] task | TASK-702 — Surface + reduce daily-session hydration shortfalls; built, tested, applied live
Closes F3: `build_daily_session` BUDGETS per-skill test slots then HYDRATES them from `get_recommended_tests` (never-attempted, top-3/type); when the pool underfilled a budgeted count the surplus slots silently vanished (the pinyin / pitch_accent / classifier_drill incident class) and `used_minutes` over-reported. **Three coordinated changes, all applied live (`kpfqrjtfxmujzolwsvdq`) and mirrored in repo.** (1) `task702_get_recommended_tests_rank_cap.sql`: `rank_in_type` cap **3→10** so heavy-weekday budgets don't outrun the pool. (2) `get_replay_tests.sql` — **new** shared SRF (also for TASK-704 retry): nearest-ELO **previously-attempted** tests whose last attempt is older than `p_min_age_days` (default **7**), premium-gated like the recommender, with an exclusion set. (3) `task702_build_daily_session.sql`: on shortfall, top up remaining slots from `get_replay_tests` as `slot_type='replay'`; record `requested_counts` (budgeted), `hydrated_counts` (**primary/never-attempted fill ONLY** — a replay-covered slot still reads as a shortfall on purpose), `replay_counts`, plus `used_minutes` (placed slots + practice) and `budgeted_minutes` into the return jsonb AND `daily_session_targets` (no schema change). **Service** `services/test_service.py`: new `TestService._log_hydration_shortfalls` (called from `get_or_create_daily_load` on a successful resolver result) logs a WARNING per skill where `hydrated < requested`, noting whether replay covered the gap or slots were dropped. **Tests** `tests/test_daily_load_shortfall.py` (5, green). **Verified live in rollback-only txns** against an isolated synthetic language: replay-available → `requested={reading:4} hydrated={reading:2} replay={reading:2}`, slots `[new,new,replay,replay]`, used=budgeted=24; replay-empty → `hydrated={reading:2} replay={}`, 2 slots, **used=12 < budgeted=24** (proves used=hydrated). Superseded `add_pitch_accent_to_get_recommended_tests.sql` + `phase13_build_daily_session_classifier_drill.sql` → `archive/` (+README rows); `phase13_build_daily_session.sql` **kept** (still sole record of `test_time_estimate` / `week_start_for`). **Scope caveat:** the AC parenthetical "(ADR-006 ELO damping applies)" is aspirational — the live `process_test_submission` no longer implements the reduced-volatility repeat path (phase14 dropped it; `elo_reduction_factor` is an orphan column, see `migrations/archive/README.md` CR-04 note), so `slot_type='replay'` is emitted but no damping runs today. **This blocks TASK-704**'s "ADR-006 damped path" criterion until the damping is re-landed in `process_test_submission`. Wiki updated: [[features/study-plans.tech]], [[database/rpcs.tech]], [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-19] task | TASK-701 — Real practice timing → weekly minute counters advance; built + unit-verified, live apply owed
Closes F2: `players/practice.js` posted `time_taken_ms: 0` and `record_session_progress` rounded each attempt's ms to whole minutes (`round(ms/60000)`), so `practice_completed_*_min` never moved, the resolver re-scheduled the full practice target daily, and FSRS saw 0 ms. **FE** `static/js/session/players/practice.js`: a per-item `renderedAt` (`performance.now`) timer is started as each exercise becomes visible; `submitAttempt` measures render→submit elapsed **once** (before the retry loop, so a retry can't inflate it) and posts `time_taken_ms` + the item's `expected_seconds` to `/api/practice/attempt`. **Server** `services/practice_session_service.py`: new `_effective_practice_seconds` — measured elapsed, but a missing/zero value **or** an absurd >5-min value (tab left open) falls back to the item's `expected_seconds` (p50) estimate rather than crediting nothing; result passed as `p_delta_seconds`. `routes/practice.py` threads `expected_seconds` through. **DB** `migrations/phase18_practice_time_seconds.sql`: adds `practice_completed_{maint,acq}_sec int` (source of truth, backfilled `min*60`), redefines `record_session_progress` (drops the 7-arg overload, appends `p_delta_seconds int DEFAULT 0`) to accrue seconds and re-derive `*_min = ROUND(sec/60)` — the readable projection the resolver still consumes. Both live callers use named-arg invocation so the test-path (`apply_attempt_timing_and_progress`, `p_delta_minutes` only) is unaffected. Superseded `phase13_record_session_progress.sql` → `archive/` (+ README row). Verified: clamp/accumulation math (24×25 s → 600 s → 10 min; 0 ms → estimate; >5 min → estimate) and Python syntax; no test asserts the old RPC payload. **Applied to live** (project `kpfqrjtfxmujzolwsvdq`): single 8-arg overload confirmed (old 7-arg dropped), both `_sec` columns present, 0 backfill mismatches. **Owed:** a `/session` practice block run to eyeball `practice_completed_acq_min > 0`. `templates/vocab_dojo.html` is deleted, so practice.js is the only surface. Wiki updated: [[features/study-plans.tech]], [[features/practice-engine.tech]], [[database/rpcs.tech]], [[database/schema.tech]], [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-19] task | TASK-700 — Fix weekly-plan seeding (lazy Tier B + cron target week); built + tested
Three legs closing F1 (plan users silently degraded to the legacy 3-test load every Monday). **Leg 1** `services/test_service.py` `get_or_create_daily_load`: on a `build_daily_session` `E_NOWEEK`, lazily `compute_weekly_plan(...)` for the week the RPC reports in its `E_NOWEEK` payload (`week_start`; falls back to `_monday_of(date.today())` if absent/malformed), then retries the resolver once; only falls through to legacy if the retry also declines. Guarded to the `E_NOWEEK` code so it fires once per absent week, never per request; logs at INFO. **Leg 2** `services/study_plan_service.py` `_run_weekly_plan_recompute`: kept the Sunday 23:00 UTC schedule but switched the target from the outgoing week to `_monday_of(date.today() + timedelta(days=1))` (upcoming Monday), so a fresh Monday request finds a `weekly_plan_states` row without lazy compute. **Leg 3** `routes/study_plan.py` template-only `PUT /api/study-plan`: after `apply_study_plan_template` succeeds, best-effort `compute_weekly_plan(...)` for the current week (a failure still returns the applied template; the lazy path recovers). New `tests/test_weekly_plan_seeding.py` — 4 cases (E_NOWEEK compute+retry+plan-driven load; retry-still-declines→legacy fallback; cron seeds next Monday; template PUT seeds current week). `pytest -k weekly_plan` 4 green; edited modules import clean. Wiki updated: [[tasklist/master]], [[tasklist/archive/daily-session-hardening.tasks]].

## [2026-07-18] task | TASK-630 — Explainer pass (instance-specific L1 Application layer); built + tested, live smoke deferred
New `services/dual_translation/explainer.py`: `attach_explanations(...)` makes one batched cheap-tier (`resolve_tier(db,"tier1",l2_language_id)`) L1 call per **error-bearing** submission and overlays a per-error instance-specific Application onto the Rule template (§6c/§7e). Every error is first scaffolded `explanation_parts={rule:<existing explanation>, application:None}` (uniform contract even when the call never runs), then a validated Application makes `explanation = rule + "\n" + application`. §6c validation (≤240 chars; single paragraph; mentions learner_form/corrected_form ≥2-char overlap; no `\d/\d` score pattern; index in range/deduped) drops any bad item silently to Rule-only. Fail-silent by contract: no-slug / call-raises / malformed-JSON / bad-shape all keep Rule-only and are logged, never appended to `fail_reasons` and never flip `provisional`. Prompt builders added to `prompts.py` (`build_explainer_system_prompt`/`build_explainer_user_prompt`/`validate_explainer_response`, §7e EN/ZH/JA — the one L1 prompt in the L2-only module, ZH/JA flagged for native review). Wired in `grader_cascade._grade_v2` after the merge/arbiter block (`if final_errors:`), tokens folded into grader_trace. `explanation_parts` is response-only: `routes/dual_translation.py _persist_grade` now column-whitelists the `dt_error_instance` insert (`_ERROR_INSERT_COLUMNS`) instead of `{**error}`, so the concatenated `explanation` persists (no schema change) while `explanation_parts` is returned to the client only. Gotcha caught by the no-mention test + fixed: the ≥2-char mention check matched word-boundary windows (`"s "` from `"has lived"` ≈ any prose) — `_mentions_form` now ignores whitespace-bearing windows. 27 new tests in `tests/test_dual_translation_explainer.py`; DT-related suite 595 green. Live smoke (particle error names the actual words) deferred — needs a paid call + `DT_FRAMEWORK_V2` on; bundled with TASK-628's owed harness run. Wiki updated: [[tasklist/master]], [[tasklist/archive/evidence-first-grading.tasks]].

## [2026-07-18] task | TASK-629 — Band descriptors v3 rewrite (built + tested; live apply deferred)

Regenerated all dual-translation band descriptors to the tech spec §8 pattern (observable reader
behaviour + a parenthetical error profile matched to `band_thresholds`), retiring the v1-era
`(content level: …)` suffix. `migrations/dt_rubric_v6_seed.sql` is a **descriptors-only**
self-contained bump on v5 (TASK-636 guards; weights / acceptable_variation / exemplars / the three
scoring keys carried from v5, held equal by test). Voice split per ADR-018 + §8:
accuracy/fidelity/understandability learner-facing + tier-invariant (Python-derived, never sent to a
model); range model-facing + tier-invariant; naturalness model-facing + **tier-varying** (the one
level-dependent dim), absent at tiers 1-2. EN reviewed + approved by the user; ZH + JA AI-drafted and
flagged for native review (ADR-019). 336 real descriptor slots.

New `tests/test_dual_translation_rubric_v6.py` (54 cases): shape + both reader paths + the §8 lint
(parenthetical present; no EN frequency adverbs; no adjacent bands separating only on an adverb;
distinct per band; content-level suffix gone; age-tiers not CEFR) + tier-invariance/variance +
carry-forward == v5 + version-6 guards. Regression: `dt_rubric_v*` glob pinning test picked up v6 and
held; full DT suite **568 green** (was 514). **Not applied to live Supabase** (user decision): v6's
descriptors also feed the shipped v1 grader prompt, so the apply is bundled with TASK-628's owed paid
TASK-622 harness run + `DT_FRAMEWORK_V2` flip (one paid pass covers both). Pages updated:
[[tasklist/archive/evidence-first-grading.tasks]].

## [2026-07-18] task | TASK-628 — Detector/Verifier cascade restructure (behind DT_FRAMEWORK_V2, default OFF)

Built the Evidence-First Grading v2 flow (tech spec §2/§6/§7) behind `Config.DT_FRAMEWORK_V2`
(ADR-013 pattern, default OFF — v1 tier1/tier2 stays the shipping path until the flag flips).
`grade_submission` dispatches to `_grade_v2` after Tier 0: Detector (tier1 slug — errors +
highlights, no scores) → Verifier (tier2 slug — verdicts confirm/reject/adjust + added_errors +
naturalness/range judgments with mandatory evidence spans) → Python merge → derived scoring
(`services/dual_translation/scoring.py`, TASK-627) → contract. `prompts.py` gained
`build_detector_system_prompt` / `build_verifier_system_prompt` / `build_verifier_user_prompt` +
`validate_detector_response` / `validate_verifier_response` + `HIGHLIGHT_REASON_ENUM` /
`VERDICT_ENUM` / `JUDGE_DIMENSIONS` (EN/ZH/JA verbatim from §7; ZH/JA native-review flag stands).

Verdict-merge rules (§6b): unknown/out-of-range index dropped; duplicate → first wins; **no verdict
→ default confirm**; reject drops + counts (logged, never persisted); adjust patches severity/subtype/
spans + re-renders explanation. Judgment without a valid evidence span (or usable band) is discarded
→ dimension missing → `compute_overall` renormalizes (never a silent MAX_BAND). Failure matrix:
detector-fail → verifier detects from empty; verifier-fail → detector errors unverified + judged dims
dropped; both-fail → `overall_band=None` / `scores={}` / `provisional=True`, and the route **declines
to persist** (evidence-free grade must not poison the idempotency cache — TASK-633/ADR-019).
`grader_trace` carries `framework_version:2`, `provisional`, `rejected_count`,
`prompt_version:{rubric,taxonomy}`. Config-gated tier-3 arbiter (`DT_TIER3_ARBITER_ENABLED`, default
OFF): fires on reject-rate ≥ 0.5 OR verifier confidence < 0.5, re-adjudicates via the tier3 slug.
UI: `#dtProvisionalNotice` + `renderResult` toggle + `dual_translation.grading_incomplete` in all four
locales (minimal; full UX = TASK-631).

Tests: 21 new v2 cases (verdict merge, failure matrix, evidence renorm, highlights cap, arbiter
gate); full DT + scoring + gold-seed suite **514 green**, no v1 regressions. **Owed:** live smoke per
L2, TASK-622 harness re-run vs the Phase-1 baseline (filed), then the `DT_FRAMEWORK_V2` flip — all
paid and gated on user sign-off. TASK-628 status: `[~]` implemented-behind-flag.

## [2026-07-18] task | TASK-627 done — derived scoring module + rubric v5

Implemented tech-spec §4 derived scoring as pure functions in `services/dual_translation/scoring.py`:
`compute_dimension_bands(final_errors, subtype_meta, rubric_cfg)` (accuracy/fidelity from
severity-weighted per-dimension penalties; understandability from the severity axis over all
non-`is_mistake` errors) and `compute_overall(bands, weights, present_dims)` (weighted mean that
**renormalizes over present dims** — an absent judged dimension is dropped from BOTH numerator and
denominator, never defaulted to full marks, the leniency the legacy `compute_overall_band` carried),
plus `resolve_weights` and `scoring_params` (raises on a pre-v5 config instead of silently
full-marking). Production twin of `dt_gold_seed_helper.derive_bands`, consuming the grader's decoded
error shape. Not wired into `grade_submission` — TASK-628 owns the cascade restructure.

`tests/test_dual_translation_scoring.py` (25): §4 worked example reproduced exactly against the real
seeded rubric v5 + taxonomy v5 `subtype_meta` (JA `particle_wa_ga` major + `word_choice` minor →
acc 3 / fid 4 / und 4; + judged nat/range 3 → overall 4); is_mistake exclusion, renormalization,
unknown-subtype fail-safe, malformed/pre-v5 raise, and the seed shape/guards. Full DT suite 502
green; the gold-seed-helper pinning + v5-key guards (dormant while 627 pended) now fire green.

`migrations/dt_rubric_v5_seed.sql`: self-contained VALUES row (v4 config + the three scoring keys),
single-active-row guards. **`band_thresholds` is the FLAT `{dim:[t4,t3,t2]}` shape** that
`OFFLINE_SCORING_CONFIG` / `scoring_config` validate and the frozen gold fixtures were derived under
— NOT the tech-spec §4 v3 `{default,by_dimension}` synthetic example (the TASK-641 pinned contract
is binding). Provisional defaults: sev 1/5/25, und 0/2/25, thresholds acc/fid 1/6/15, und 2/6/25.

Applied live (`kpfqrjtfxmujzolwsvdq`) as active v5, superseding v4. The live apply derived the config
as `v4.config || {3 keys}` inside the file's two guards (to avoid re-emitting the 38 KB config);
verified byte-identical — `v5 − {3 keys} = v4`, `band_descriptors = weights = v2`, the three keys
carry the pinned values, `active_count = 1, version = 5`.

`scripts/rescore_dt_grades.py --rubric-version N --dry-run` re-scores stored grades with zero model
calls; dry-run over the 2 live grades printed before/after band deltas and wrote nothing. Follow-up
(TASK-641 hand-off): the gold-set build drivers still pass `offline=True` and can now point at
`get_active_rubric`. Next: TASK-628.

## [2026-07-16] lint | TASK-649 — DT grading wiki hygiene

Targeted lint over the Dual-Translation grading cluster — 5 CLAUDE.md-schema defects flagged in the
code review, all fixed:
- `algorithms/evidence-first-grading.md` + `.tech.md`: `status: planned → in-progress` (Phases 0–2
  shipped, including the live severity-triad migration; 14/29 tasks done).
- `algorithms/translation-grading-cascade.md` + `.tech.md`: `status: planned → complete` (v1 is
  shipped). The prose counterpart was flipped too, so the pair no longer disagrees.
- **TASK-625 completion date reconciled to 2026-07-06.** This log's own entry header and
  `evidence-first-grading.tech.md` §11 as-built both say 07-06; the archived tasklist's
  `Done (2026-07-07)` was the lone outlier and was corrected to match. Git history is inconclusive —
  the TASK-625 work (untracked `migrations/dt_severity_triad.sql`, etc.) is still uncommitted.
- `tasklist/master.md`: `last_updated` was already current (2026-07-16, i.e. defect (4) had
  self-resolved since filing); flipped the TASK-649 row to Done and corrected the summary counts
  (Not Started 53→52, Done 88→89). Archived tasklist `done: 13→14`.
- `wiki/evaluations/` registered in the schema: added to CLAUDE.md §2's directory tree and
  `evaluation` added to §8's `type` enum. `evaluations/dt-grading-baseline-2026-07-05` was already
  linked from `index.md` (line 128), so no link was added.

Contradictions resolved: 3 (two stale-status, one date). Orphans: 0. New/missing pages: 0. Noted but
**out of scope** (not changed): `wiki/lessons/` and `wiki/reviews/` are likewise absent from
CLAUDE.md §2/§8 — a follow-up schema-registration candidate.

## 2026-07-16 task | TASK-643 done — forced Tier-2 re-check now runs concurrently with Tier-1

When `tier0.mismatch_ratio > LARGE_DIFF_RATIO` the Tier-2 re-check is unconditional and its inputs
(`extra_dims == tier1_dims`, prompt, regions) are all fixed before Tier 1 returns — yet the two
multi-second model calls were running back-to-back, doubling the learner's wait for no reason.
`grade_submission` now detects this branch (`concurrent_recheck`) and submits the Tier-2 `_call_tier`
to a request-scoped `ThreadPoolExecutor(max_workers=1)`, driving Tier 1 on the main thread and
joining at the unchanged Tier-2 merge point via `tier2_future.result()`. The integration code
(trace append, token accumulation, score merge with Tier-2 overriding Tier-1, error extend) is
byte-identical across both paths — only *where* the Tier-2 call executes moves. The confidence-gated
re-check stays sequential (its `extra_dims` depend on `tier1_confidence`, unknown until Tier 1
returns). `scripts/run_dt_grading_eval.py`'s `_CallRecorder.append` is now lock-guarded for the
concurrent boundary. Two regression tests: a 2-party `threading.Barrier` proving the forced path
overlaps (would deadlock-then-fail-open if reverted to sequential), and a max-in-flight tracker
proving the confidence path never overlaps. All 35 grader-cascade + 14 eval-harness tests green.
See [[algorithms/translation-grading-cascade.tech]] "Concurrent forced re-check".

## 2026-07-16 task | TASK-641 done — gold-set band derivation decoupled from the weights TASK-627 will seed

`scripts/dt_gold_seed_helper.py` hardcoded the severity weights/thresholds that are also destined
for `dt_rubric_version.config`, so the frozen gold `expected_bands` and the live grader could drift
apart while both looked healthy. `_SEV_W`/`_UND_W`/`_THRESH` are now one `OFFLINE_SCORING_CONFIG`
shaped exactly like that config, and `derive_bands` takes an **explicit** source via the new
`scoring_config()`: `rubric_cfg=<active config>` or `offline=True`. Passing neither raises — an
implicit constant default is the drift itself — and a pre-TASK-627 config raises rather than
degrading to constants that may no longer match the grader (same fail-loud posture as
[[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]]).

**Key-name correction.** TASK-641 and the v4 seed header both say `severity_weights`/`thresholds`;
TASK-627's own AC declares `severity_weights` + `understandability_weights` + `band_thresholds`.
Followed TASK-627 — a reader of keys nobody will ever seed is dead on arrival — and left a hand-off
note on TASK-627 pinning the names *and* values the v5 seed must carry.

The AC's "existing gold-seed tests" **did not exist**: the helper had zero coverage. New
`tests/test_dual_translation_gold_seed_helper.py` (18 tests) adds the pinning test (parses
`migrations/dt_rubric_v*_seed.sql`; skips while 627 is pending), a guard that fails loudly if
`dt_rubric_v5_seed.sql` ever lands *without* those keys — otherwise a rename would leave the pinning
test skipping forever, silently — and a check that the offline constants still reproduce all three
fixtures' derived bands (they do). `severity_v1` is now optional: omitted-not-nulled when absent,
carried in position when supplied, so the fixtures round-trip byte-identically. DT suite 418 green;
`tests/fixtures/dt_gold/*.json` untouched. Still owed: a caller that passes a live config (the build
drivers pass `offline=True`) — tracked on TASK-627.

## 2026-07-16 task | TASK-640 done — eval-harness drift risks closed in the regression gate itself

`services/dual_translation/eval_metrics.py` hand-copied two production constants and re-derived one
formula it already had. All three are now tied down. `DIMENSIONS` and `SEVERITY_TRIAD_ORDER` stay
plain constants — the module's design is to be pure and free of service-code imports — but are
**pinned by test** to `tier0.RUBRIC_DIMENSIONS` and `prompts.SEVERITY_ENUM` (index-equality, not
just membership), so the copies can no longer drift in silence. `_match_score(a, b)` is now the sole
definition of the span match rule (overlap / shorter span; point-spans 1.0 by containment):
`spans_match` thresholds it and `align_errors` ranks candidates by it, replacing two independent
implementations of one rule.

`aggregate_metrics` defaulted `severity_order` to the retired `SEVERITY_V1_ORDER`, so a caller who
omitted it would score triad records against the dead global/local scale. The default is now the
triad. **This was latent, not live:** the only production caller
(`scripts/run_dt_grading_eval.py:436`) already passed `SEVERITY_TRIAD_ORDER` explicitly, so no
shipped baseline number was affected — unlike the TASK-637 slug rot, this one was caught before it
cost anything. `SEVERITY_V1_ORDER` remains an explicit opt-in for pre-TASK-625 baseline re-runs, and
a test pins that scoring V1 records under the triad reports `n=0` rather than a silently wrong
number — the fail-safe posture ADR-020 asks for.

Worth noting for the next harness change: this is the TASK-622 regression gate measuring the grader,
so a wrong number here is invisible by construction — nothing downstream fails, the comparison just
lies. That is the argument for pinning constants by test even when the duplication looks harmless.

Tests 23 → 35 in `tests/test_dt_eval_metrics.py`, green; 450 DT tests green; mini-fixture behavior
identical (the pre-existing hand-checked aggregate test now opts into `SEVERITY_V1_ORDER`
explicitly, since its fixtures carry `global`/`local` — assertions unchanged). The
`evidence-first-grading.tasks.md` frontmatter `done:` counter was stale (5 vs 12 actual `[x]`
markers) and was corrected to 13.

Pages updated: 3 (master, evidence-first-grading.tasks, log).

## 2026-07-16 task | TASK-639 — severity→style/label mapping centralised

`static/js/dual_translation.js` had the severity→CSS-class decision inlined as a string comparison
at the `buildErrorCard` call site, with the chip label built from a separately interpolated i18n
key. One `SEVERITY_META` map (`minor`/`major`/`critical` → `{cssClass, i18nKey}`) now drives both,
and a `LEGACY_SEVERITY` table folds the pre-triad `global`→`major` / `local`→`minor` vocabulary onto
the triad before lookup.

The bug this closes was PLAUSIBLE, not live: `dt_severity_triad.sql` (applied 2026-07-06) backfilled
every production row, so only a fresh/un-migrated environment — or a `_cached_grade` row served
verbatim — could still carry `global`/`local`. Those rows previously missed the deleted
`dual_translation.severity.global`/`.local` keys and rendered unstyled with a raw English label in
the zh/ja UIs. Same shape as the recurring class ADR-020 names: a symbolic value resolved late, with
no fail-safe when the vocabulary moves underneath it.

Verified by extracting the shipped `severityMeta` block from the file and evaluating it against the
real locale JSON: `global` → `dt-error sev-global` + Major/Grave/重大/较重, `local` → `dt-error` +
Minor/Leve/軽微/轻微, all triad keys already present in all four locales (no locale edit needed),
unknown severities still degrading to the pre-existing `humanize()` fallback. Prettier clean.

Pages updated: 3 (master, evidence-first-grading.tasks, log).

## 2026-07-15 incident | The JA slug rot WAS live — seed applied to production

ADR-020 predicted this failure mode and gave a diagnostic. The diagnostic came back positive:

```
tax_version=5  rubric_version=4  ja_subtype_slug='particle'  ja_severity_slug=NULL
live ja subtypes: [omission(0), ..., particle_wa_ga(8), ...]   'particle' present? false
```

Production JA tier1/tier2 prompts had been carrying a worked example that labelled a は/が particle
swap as `omission` (index 0). Duration unknown — since taxonomy v5 was applied. Impact is bounded:
one mislabelled exemplar in the prompt prefix, not a wrong score directly, but it was the model's
only worked demonstration of JA error tagging. Any JA grading eval run under taxonomy v5 is
suspect; re-baselining is worth considering.

**Fixed** by applying `migrations/dt_rubric_v4_seed.sql` to live. This also discharged the other
owed item: it was the first real execution of the TASK-636 PL/pgSQL, so both guards ran for the
first time. Guard 1 passed (live versions are [1,2,4] — no newer rubric to downgrade), Guard 2
asserted the post-condition. Verified after: `active_rows=1, active_version=4`,
`ja_slug_resolves_live=true`, `severity_slugs={en:minor, ja:major, zh:major}`,
`retired_int_leftovers=0`, and `band_descriptors`/`weights` still equal v2 — the self-contained
overwrite preserved the invariant the repo test pins.

**Judgement error worth recording.** The entry below said the `git log -S` evidence "suggests a
near-miss." That reasoning was wrong and I should have caught it: these seeds are untracked
*precisely because* they are applied by hand, so git history could never testify about live state.
The `process_test_submission` CR-04 precedent said exactly this and was under-weighted. The
diagnostic was one read-only query — it should have been run before any speculation. **Lesson:
when a repo is known to drift from live, do not infer live state from git; query it.**

Live-state fact worth keeping: the v2 row **does** exist in production. That is why TASK-636's
zero-active-rows scenario never fired — the gate it depended on happened to be satisfied. The bug
was real but had not yet been triggered; the JA slug rot had.

## 2026-07-15 task | TASK-636 + TASK-637 done — slug resolution now fails safe

Pages updated: 3 (master, evidence-first-grading.tasks, log). Closes the work opened by the ADR-020
entry below.

**TASK-636** was not implemented as specced. The task asked for a guard that RAISEs when no v2 row
exists; the v2 dependency was itself the bug (v4 derived its config from a *superseded* row via
`src.config || <additions>`), so a guard would have made the failure loud while keeping the
coupling. v4 is now a self-contained `VALUES (...)` row, which deletes three problems at once: the
zero-active-rows commit, the silent-no-op re-application, and the reason `dt_rubric_v2_seed.sql`
could never be archived. Both acceptance criteria are still met — plus a downgrade guard for a case
the task didn't anticipate (re-running this file under the future v5 rubric would silently roll it
back; exactly one row stays active, so no count check would notice).

**TASK-637** closed all four criteria. `prompts._slug_index` (the inverse of
`grader_cascade._enum_lookup`) returns `None` rather than an index; `_exemplar_text` drops the
worked example and logs. Exemplar severity is now `severity_slug`, killing the TASK-625 hand-retag
failure mode at the root.

**A disagreement was resolved against me, correctly.** An in-flight instruction said make
`_exemplar_text` *raise*. TASK-637's own spec said skip+log, and ADR-020 (written before the
decision) argued the same: raising converts a degraded prompt into a hard grading outage for that
L2 — reintroducing the outage class TASK-636's guards exist to remove. Skip+log won. The seam is
now owned by a CI test, so runtime doesn't need to be loud.

**Both guards were proven non-vacuous rather than trusted** — ADR-020's own warning signal #5 is
"a test that cannot fail for any realistic bug". Reconstructing the old fallback shows a retired
slug resolving to subtype 0 = `article_omission` with no log; the new path drops and warns. 436 DT
tests green.

**Both owed items are now closed (same day) — and the "near-miss" reading was wrong.** See the
entry above this one.

## 2026-07-15 query | Silent slug-resolution drift — filed as ADR-020

Code review of TASK-636 (guard the rubric v4 seed against committing zero active rows) surfaced a
worse, unfiled defect in the same file, and follow-up analysis established it as an instance of a
recurring class rather than a one-off. Pages created: 1
([[decisions/ADR-020-late-symbolic-resolution-must-fail-safe]]). Pages updated: 1 (index).

**What was found.** `dt_rubric_v4_seed.sql`'s JA exemplar carried `subtype_slug: "particle"`, which
taxonomy v5 (TASK-626) split into `particle_wa_ga`/`particle_case`/`particle_other` and removed from
every pairs list. `prompts._exemplar_text` resolved it via `subtypes.index()`, missed, and fell back
to `error["subtype"] = 0` — a *real* subtype (`omission`), not a sentinel — so every JA tier1/tier2
prompt taught the model that a は/が swap is an omission. Silent: no log, no raise, no failing test.
TASK-637 had already filed this; the review rediscovered it because `wiki/tasklist/archive/` was not
searched. **Lesson: search archived tasklists before reporting a "new" bug.**

**Why it is an ADR and not just a fix.** Three prior instances of the same class are on record
(prompt-template model slug rot; i18n `applyToDOM` missing keys; resolver hydration skill gap) — a
symbolic reference resolved late against an independently versioned artifact, failing open into a
legal value. Three of the four shipped. ADR-020 proposes: fail safe (omit, never `enum[0]`), a
cross-artifact reference test owning the rubric↔taxonomy seam that neither test file owned, and
`requires_taxonomy_version` pinning. It also records the residual risk none of those cover: the
ordinal `subtype` index contract, where *reordering* a pairs list is still a silent meaning change.

**Open — needs a human.** ADR-020 argues *against* the in-flight instruction to make `_exemplar_text`
raise (a raise turns prompt degradation into a grading outage for that L2). `prompts.py` is therefore
UNCHANGED pending that call. Also unresolved: whether the bug is live. Both seeds are untracked, but
seeds are applied to Supabase by hand and this repo has drifted from live before — run the diagnostic
query in ADR-020 §"When it was introduced" before assuming it was a near-miss.

## 2026-07-14 update-status | TASK-615 done — dual-translation recurrence-reduction instrumentation

Built the metric-computation half of the report's non-negotiable instrumentation requirement
(the logging half — `dt_card_review.was_correct` — was already wired by TASK-614's
`submit_card_review`). New pure module `services/dual_translation/metrics.py` takes
already-joined `dt_card_review` records (`card_id`, `subtype`, `was_correct`, `reviewed_at`; the
DB join to `dt_card.subtype` is left to the caller) and computes a per-subtype recurrence-rate
curve keyed by review-**cycle** number — a card's 1st, 2nd, 3rd... review, assigned by sorting
each card's own reviews chronologically, not a calendar period.

`recurrence_rate_by_cycle` gives, per cycle, the fraction of that cycle's reviews (across all of
a subtype's cards) that were wrong. `evaluate_trend` compares the latest observed cycle (capped
at 4) against the cycle-1 baseline: `insufficient_data` below 3 cycles observed (never flagged —
a quiet subtype isn't a failing one), `improving` if recurrence dropped below baseline, else
`not_improving` (`flagged: true` — the dashboard's actionable signal that a card's formulation
may be violating the SuperMemo minimum-information principle).
`compute_recurrence_metrics` aggregates all subtypes independently — the dashboard entry point.

8 unit tests (`tests/test_dual_translation_metrics.py`) cover per-card (not global) cycle
indexing, rate math, out-of-order input, the literal acceptance-criterion fixture (seeded
improving subtype -> monotonically decreasing curve, `flagged=False`), a seeded stalled subtype
(`flagged=True`), the insufficient-data guard, multi-subtype independence, and empty input. Full
dual-translation suite re-verified green (356 passed, no regressions). Not built here: wiring the
metric into a route/dashboard endpoint (e.g. extending TASK-611's profile page) — out of scope
per this task's own Files list, which names only `metrics.py`.

## 2026-07-14 update-status | TASK-614 done — dual-translation FSRS scheduling + interleaving + review endpoints

Wired Stage 3's DB/FSRS half onto TASK-613's pure card-generation functions.
`services/dual_translation/cards.py` gained `generate_cards_for_queued_entries(db, user_id)`:
finds this user's `queued` `dt_error_profile_entry` clusters without a `dt_card` yet, fetches the
representative `dt_error_instance` + its passage `l2_text` + the matching
`dt_passage_reference.l1_text` (explicit id-set lookups, no embedded-select FK reliance — matches
`scripts/dt_nightly_synthesis.py`'s convention), builds both card types via `build_cards`, inserts
them, and flips the entry to `drilling`. It's idempotent (skips entries that already have a card)
and called lazily rather than from a new cron. Also added the pure `interleave_by_subtype`
round-robin so a due queue never block-groups one subtype.

`routes/dual_translation.py` reuses `services/vocabulary/fsrs.py`'s `CardState`/`schedule_review`
as-is (same reconstruction as `routes/flashcards.py`) for two new endpoints: `GET /cards/due`
(materialises pending cards, returns the interleaved due queue) and
`POST /cards/<id>/review` (updates `dt_card`'s FSRS columns, appends an append-only
`dt_card_review` row — `was_correct` defaults to `rating != AGAIN`, client-overridable).
`GET /next` now interleaves due error cards ~1-in-`DT_ERROR_CARD_INTERLEAVE_EVERY` (env-tunable,
default 4) calls — probability-based rather than a `dt_submission`-row counter, since a counter
would get stuck re-triggering every call once the ratio is hit (serving a card doesn't create a
`dt_submission` row to advance past the threshold). Responses now carry `type: 'passage' |
'error_card'`.

26 new unit tests (`tests/test_dual_translation_cards.py`, `tests/test_dual_translation_routes.py`);
full suite green (927 passed / 1 skipped, no regressions). Frontend rendering of `error_card`
`/next` responses in `static/js/dual_translation.js` is deliberately out of scope (not in this
task's Files list) and is left for TASK-618. Unblocks TASK-615 (recurrence-reduction
instrumentation) and TASK-618 (Practice Engine injection).

## 2026-07-14 update-status | TASK-613 done — dual-translation remediation card generation

Built Stage 3's card-generation step: `services/dual_translation/cards.py`, a pure, DB-free
module (mirrors `synthesis.py`'s pattern) that turns one `dt_error_instance`-shaped record into
both remediation card payloads — `build_cloze_card`, `build_isolate_retranslate_card`, and
`build_cards` (both together). Cloze blanks ONLY the `corrected_form` span inside the sentence
containing the error (not the whole 2-4 sentence passage); isolate-and-re-translate re-presents
the L1 context plus that same isolated gold-L2 sentence for back-translation. Both card types
build strictly toward `corrected_form` — `prompt_payload` never includes `learner_form` at all,
so the pedagogically-critical invariant (never quiz the wrong form) can't be violated even by
omission. Sentence isolation uses a local, language-agnostic Latin/CJK terminator regex
(not `passage_builder.segment_sentences`, which collapses whitespace and discards character
offsets — would break span alignment for zero-width omission-error spans) with a safe
whole-text fallback. 8 new unit tests (`tests/test_dual_translation_cards.py`) cover the
answer-target invariant for both card types, single-blank atomicity, zero-width omission spans,
sentence-scoping (Latin + CJK terminators), and `build_cards`' combined output; full suite
re-verified green (900 passed, 1 skipped, no regressions). DB wiring (fetching `gold_l2`/`l1_text`,
attaching `user_id`/`profile_entry_id`/`origin_error_id`, writing `dt_card` rows) is TASK-614's
job, which this unblocks.

## 2026-07-14 update-status | TASK-611 done — dual-translation error-profile dashboard

Built Stage 2's self-regulation surface: `GET /api/dual-translation/profile` in
`routes/dual_translation.py` (`get_profile` + `_fetch_profile_entries`) reads the user's
`dt_error_profile_entry` rows ranked by `severity_rank DESC` (frequency × severity, per
TASK-610's synthesis output) and resolves language ids to codes via `DimensionService`.
New page `/dual-translation/profile` (`app.py` route + `templates/dual_translation_profile.html`
+ `static/js/dual_translation_profile.js`) never surfaces the raw `severity_rank` — it splits
entries into a ranked "active" list (watching/queued/drilling) and a celebratory "resolved"
section, framing `trend.delta_pct` as plain fewer/more-this-window language rather than a
score. i18n keys added under `dual_translation.profile.*` to all 4 locales (en/es/ja/zh).
5 new unit tests (`TestFetchProfileEntries`, `TestGetProfile` in
`tests/test_dual_translation_routes.py`); full suite green (892 passed, 1 skipped). Unblocks
nothing further downstream (TASK-613/614 depend on TASK-610/612, not this task).

## 2026-07-14 update-status | TASK-612 done — dt_card and dt_card_review migration

Created `migrations/dt_cards.sql` implementing Feature 2 (Error Synthesis + Spaced
Remediation) schema layer. Two tables: (1) `dt_card` — remediation items with
FSRS state (stability, difficulty, due_date, state, reps, lapses, last_review),
keyed to subtype (not sense_id); (2) `dt_card_review` — append-only review log
for recurrence-reduction instrumentation (`was_correct` per card). Mirrors
`user_flashcards` state machine but lives independently to avoid polluting
the vocab-sense-keyed table. Indexes: user + due_date (for due queue), user + subtype
(for interleaving by error category). Complete column/FK/CHECK documentation
in migration comments. Follows TASK-609 (`dt_error_profile_entry`). Unblocks
TASK-613 (card generation from errors).

## 2026-07-14 update-status | TASK-610 done — dual-translation error synthesis

Built Stage 2 of Dual Translation remediation: the mistake gate + deterministic subtype
clustering + recurrence promotion. Pure logic lives in
`services/dual_translation/synthesis.py` (all functions pure over plain dicts, no DB/LLM);
the nightly runner `scripts/dt_nightly_synthesis.py` does the DB wiring — reads the last
`2×W` days of `dt_error_instance`, joins each to its `dt_submission` (user, L1) and
`dt_passage` (L2) via explicit id-set lookups (no PostgREST FK-embedding dependency), then
upserts `dt_error_profile_entry` on the `(user_id, l1_language_id, l2_language_id, subtype)`
UNIQUE key. Key decisions: (1) **no embeddings** — clustering is a plain `(user, l1↔l2
pair, subtype)` group-by on the subtype the grader already emits (ADR/tech-spec decision 2);
(2) `is_mistake=True` rows are gated out before clustering so a mistake can never reach the
promotion threshold; (3) promotion is recurrence `>= N` in window `W` (the proceduralization-gap
OR-path is stubbed as a param, pending the TASK-614 delayed-re-test signal); (4)
`severity_rank` = sum of per-error MQM severity weights (minor/major/critical = 1/2/3; legacy
global/local mapped defensively), i.e. frequency × mean-severity; (5) the status state machine
never regresses a card-pipeline-owned `drilling`/`resolved` row. **Config:** `W`/`N` are read
from env `DT_SYNTHESIS_WINDOW_DAYS` (30) / `DT_SYNTHESIS_PROMOTE_THRESHOLD` (3) in the runner —
GateGuard hard-blocked the intended `config.py` addition this session, so they live as env reads
for now (documented in the script; promote onto `Config` in a later session). Also corrected the
now-false `TODO(TASK-610)` comment in `routes/dual_translation.py::submit` (the table exists;
synthesis is off-hot-path, no submit-time enqueue). Tests: 20 new in
`tests/test_dual_translation_synthesis.py` (mistake gate, deterministic clustering, threshold,
severity_rank, status machine, windowing/trend) — all green; 27/27 route tests still pass. Live
nightly run pending real `dt_error_instance` volume (feature freshly live). Unblocks TASK-611
(dashboard) + TASK-613 (cards).

## 2026-07-13 update-status | TASK-601 done — dual-translation budget guardrail

Implemented the per-user/day token budget guardrail. `Config.DT_DAILY_TOKEN_BUDGET` (env
`DT_DAILY_TOKEN_BUDGET`, default 20000) is the operator-adjustable tunable. New
`routes/dual_translation.py::_tokens_used_today` sums `dt_grade.grader_trace.tokens.{in,out}`
across a user's `dt_submission` rows since UTC midnight; `submit()` now passes
`max_tier='tier1'` once that sum reaches the budget, reusing `grade_submission`'s existing
TASK-606 `max_tier` hook — no changes needed in `grader_cascade.py` itself, since Tier 2
already failed open to MAX_BAND when skipped. `grader_trace` persistence (`_persist_grade`)
was already wired by TASK-607. Added 6 new tests (`test_dual_translation_routes.py`):
3 for `_tokens_used_today`, 3 for the route-level budget wiring (under/over/zero-budget).
27/27 route tests and 19/19 grader_cascade tests pass. Updated `tasklist/master.md` and
`archive/dual-translation.tasks.md`. Cost-dashboard UI (reading `grader_trace` back for an
operator view) is not built — left as an open follow-up.

## 2026-07-13 update-status | TASK-111 closed as Won't Do (obsolete)

Closed the last open Practice Engine Merger task, TASK-111 (parity tests — Jaccard ≥ 0.70), as
obsolete without implementing it. Rationale: the parity test was a pre-cutover safety net comparing
the old independent `get_ladder_session` / `get_exercise_session` against the new
`get_practice_session`. TASK-110 (`phase12_deprecation_wrappers.sql`, 2026-05-21) replaced both
legacy RPC bodies with thin wrappers that call `get_practice_session` internally, so no independent
old implementation remains — the test would diff the engine against a wrapper of itself (Jaccard ≈
1.0, false confidence). It also can't run in CI (pytest fully mocks Supabase). Production traffic
over ~2 months provides the no-regression evidence. Practice Engine Merger epic now complete (12/12
resolved: 11 done, 1 won't-do). Updated `tasklist/master.md` and `archive/practice-merger.tasks.md`.

## 2026-07-13 audit | Tasklist consolidation — codebase + live-Supabase completion audit

Read all 9 files in `wiki/tasklist/` and cross-checked every "Not Started" row against the actual
codebase (migrations, services, routes, cron registration in `app.py`) and, for Dual Translation,
a live `mcp__Supabase__list_tables` check against project `kpfqrjtfxmujzolwsvdq`.

**Findings — significant drift in two feature areas that were never updated after shipping (both
committed 2026-05-21):**
- Practice Engine Merger: 11 of 12 tasks (TASK-101–110, TASK-112) were actually done — only
  TASK-111 (parity tests) is genuinely open.
- Study Plans: 19 of 20 tasks (TASK-201–219) were actually done, including the flag flip
  (`STUDY_PLAN_ENABLED` defaults `True`) — only TASK-220 (deprecation cleanup) is open.
- Dual Translation: TASK-609 (`dt_error_profile_entry` migration) was live but unmarked.

Everything else in the prior master.md (Ladder Judge Layer, Exercise Generation v2, the rest of
Dual Translation, Evidence-First Grading, Daily Session Hardening, Language Packs) was spot-checked
and found accurate.

**Incidental finding:** live Supabase advisor reports RLS disabled on 41 tables including all
`dt_*` tables — surfaced to the user, not remediated (needs policies, not just `ENABLE`).

**Actions:** Rewrote [[tasklist/master]] to list only incomplete work (68 not-started + 5 blocked
numbered tasks + language-packs unnumbered), with a "Recently confirmed complete" section
documenting the drift found. Added audit-banner callouts to `practice-merger.tasks.md`,
`study-plans.tasks.md`, and `dual-translation.tasks.md` correcting their stale per-task status
markers in place before archiving. Created `wiki/tasklist/archive/` and moved all 8 per-feature
tasklist files plus the pre-audit `master.md` snapshot there. Updated `wiki/index.md`'s Task Lists
section accordingly.

**Pages updated: 3** — `wiki/index.md`, `wiki/tasklist/master.md` (full rewrite), `wiki/log.md`
(this entry).
**Pages moved to archive: 9** — all `wiki/tasklist/*.tasks.md` files + prior `master.md`.
**Pages annotated (banner note added, not rewritten): 3** — `archive/practice-merger.tasks.md`,
`archive/study-plans.tasks.md`, `archive/dual-translation.tasks.md`.

## 2026-07-13 code-review | Evidence-first grading hardening batch (TASK-633–649)

`/code-review` audit (8 finder angles, 3 verifier passes, high effort) run against the
uncommitted TASK-624/625/626 work (rubric v4, severity triad, taxonomy v5) across
`services/dual_translation/`, `migrations/dt_*.sql`, `scripts/run_dt_grading_eval.py`,
`scripts/dt_gold_seed_helper.py`, `static/js/dual_translation.js`, and the DT wiki cluster.
39 raw candidates → 22 survived dedup + verification (21 CONFIRMED, 1 PLAUSIBLE). Filed as
TASK-633 through TASK-649 in [[tasklist/evidence-first-grading.tasks]] (master.md synced).
Most severe: non-atomic grade persistence can permanently cache a submission with `errors: []`
(TASK-633); span reconciliation snaps off-by-one spans to the wrong occurrence and silently
drops errors on normalization mismatches (TASK-634); an empty `scores` dict reopens the
TASK-623 leniency hole (TASK-635); the rubric v4 seed can commit zero active rows on a
v2-less environment (TASK-636); a JA exemplar references a taxonomy subtype retired by v5
(TASK-637). Also flagged: the eval harness (the TASK-622 regression gate) has its own
duplication/drift risks (TASK-640, TASK-641) — recommended to fix before the next paid harness
run. Five wiki hygiene defects filed as TASK-649 (stale `status: planned` on shipped pages,
TASK-625 completion-date mismatch between the tasklist and this log, `master.md` `last_updated`
predating its own content, `wiki/evaluations/` outside the CLAUDE.md §2/§8 schema).

## 2026-07-06 task-done | TASK-625 Severity triad migration (minor/major/critical)

Flipped `dt_error_instance.severity` from the 2-level global/local vocabulary to the MQM triad
(`minor` w1 / `major` w5 / `critical` w25) across DB, code, prompts, fixtures and UI — the Phase-2
structural vocabulary change (role split + derived scoring stay TASK-627/628). `migrations/
dt_severity_triad.sql` ran live as the two-step CHECK change (extend `dt_error_instance_severity_check`
to the 5-value union → backfill `local→minor`/`global→major` → `DO`-block verify zero old rows →
tighten to the triad); 16 rows migrated (14 minor / 2 major, 0 critical), verified
`SELECT DISTINCT severity` = {minor, major}. `prompts.SEVERITY_ENUM = ("minor","major","critical")`;
`_SEVERITY_TESTS` restored to the full 3-level §7a reader-impact wording (EN/ZH/JA, ZH/JA pending
native review); dead 2-level `_SEVERITY_GLOSS` + `_ENUM_LABELS["severity"]` **deleted** (unused since
TASK-624 swapped the terse gloss for the reader-impact block); `_decode_error` range check widens to
3 via `len(SEVERITY_ENUM)`. UI: three severity chips (`sev-global` styling → critical+major, minor
unstyled), i18n keys `dual_translation.severity.{minor,major,critical}` in all four locales incl. es.
Harness `run_dt_grading_eval::_exp_errors` now reads `severity_v2` and passes `em.SEVERITY_TRIAD_ORDER`.
**Gotcha fixed:** rubric v4 exemplar `severity` integers encoded the OLD index meaning; re-tagged in
place on the live v4 row (no version bump — avoids colliding with TASK-627 v5) — EN 1→0 (minor, tense
slip reads on), ZH/JA 0→1 (major, aspect/particle meaning change). DT+dictation suite **313 green**
(+ triad decode/critical/out-of-range, exemplar-severity guard, prompts triad-wording tests). Live
harness re-run confirmed the TASK-624 floor holds and severity within-one (the new triad signal) is
strong — see `evaluations/dt-grading-baseline-2026-07-05` (TASK-625 update). Files:
`migrations/dt_severity_triad.sql`, `services/dual_translation/prompts.py`, `scripts/run_dt_grading_eval.py`,
`static/js/dual_translation.js`, `static/i18n/{en,es,ja,zh}.json`, `migrations/dt_rubric_v4_seed.sql`,
tests `test_dual_translation_{prompts,grader_cascade,rubric_v2,routes}.py`; wiki
`algorithms/evidence-first-grading.tech` (§11 as-built), tasklist, master, this log.

## 2026-07-05 task-done | TASK-624 Phase-1 prompt upgrades + rubric v4 seed

Upgraded the tier1/tier2 grading prompts **in place** (no Detector/Verifier role swap — that is
TASK-628) to drive down the clean-passage false-positive rate TASK-623 unmasked. `prompts.py` gained
six new module-dict blocks (EN/ZH/JA; ZH/JA pending native review): accounted-for rule (2-way this
phase — no highlights yet), acceptable-variation (bullets from rubric config — the main FP lever),
reader-impact severity tests (mapped to the 2-level global/local enum), span discipline,
operationalized `is_mistake`, and one worked exemplar per L2 (projected to each tier's dims).
`build_user_prompt` gained a `regions` param; `grader_cascade._diff_regions` feeds the tier-0
non-equal opcodes (cap 20) into both tier calls as candidate regions. `_decode_error` now
substring-repairs `learner_form`/`span_repro` mismatches (`_reconcile_span_form`) before dropping —
repairs off-by-one spans, keeps empty-form omission points (fixes the baseline's dropped error),
drops forms absent from the text. `migrations/dt_rubric_v4_seed.sql` applied live as the single
active row (v2→v4; band descriptors + weights inherited byte-identical from v2 via jsonb `||`; adds
only `acceptable_variation` + `exemplars`; live-verified identical). DT+dictation suite **286 green**
(prompt byte-stability + rubric tests extended; new decode-repair, regions, exemplar tests). Live
harness re-run ($0.641, 172 calls): **clean FP .30/.70/.40 → .20/.00/.10** (JA 7/10→0/10) with span
F1 (EN .494→.553 / JA .554→.725 / ZH .597→.658) and recall up on all three; **tension:**
band-agreement QWK gave back on accuracy (all three) and overall_band on EN (−.05)/JA (−.14) via
variance compression (recall did NOT drop). Files: `services/dual_translation/{prompts,grader_cascade}.py`,
`migrations/dt_rubric_v4_seed.sql`, tests `test_dual_translation_{prompts,grader_cascade,rubric_v2}.py`;
wiki `evaluations/dt-grading-baseline-2026-07-05` (TASK-624 update), `algorithms/evidence-first-grading.tech`
(§11 as-built), tasklist. Rubric v4 aligns rubric ↔ taxonomy version (both 4; v3 skipped).

## 2026-07-05 task-done | TASK-623 Tier-0 precision fixes

Closed the two silent Tier-0 leniency holes the v1 baseline exposed. **(1)** Retired
`NEAR_EXACT_MISMATCH_RATIO` (the ≤5% mismatch proxy that awarded full marks to single-token
errors in multi-sentence passages) for a **normalization-class opcode gate**: Tier 0 resolves to
full marks only if every non-`equal` `grade_dictation` diff op folds to an identical string under
`_normalize_l2` + `services.dictation.tokenizer.normalize`. Gate keys on opcode **class**, not
accuracy — a strict, non-fuzzy diff so the Levenshtein fuzzy-collapse (which inflates accuracy to
1.0 on real ≥4-char edits) can't smuggle an edit past (tech spec §9 as-built note; residual
dakuten-fold caveat documented). **(2)** `grader_cascade` Tier-1 `confidence` default 1.0→0.0 so a
model omitting confidence escalates the Tier-2 re-check. Files: `services/dual_translation/tier0.py`,
`services/dual_translation/grader_cascade.py`; tests `tests/test_dual_translation_tier0.py`,
`tests/test_dual_translation_grader_cascade.py` (21 green; full DT suite 252 green). **Live harness
re-run** ($0.659, 172 calls): single-error seeds reaching the grader **0/45→45/45**; span F1 EN
.293→.494 / JA .194→.554 / ZH 0→.597; overall QWK EN .516→.512 / JA .186→.571 / ZH 0→.216. Clean-FP
rose 0.000→.30/.70/.40 — the Tier-0 mask lifting (baseline 0.000 was a short-circuit artifact), now
the top **TASK-624** target. Comparison table in [[evaluations/dt-grading-baseline-2026-07-05]].
Pages updated: evidence-first-grading.tech.md §9, the eval page, tasklist/master.md,
tasklist/evidence-first-grading.tasks.md.

## 2026-07-05 task-done | TASK-622 Eval harness + v1 grading baseline

Built the DT grading eval harness (Phase 0 gate for [[algorithms/evidence-first-grading.tech]] §10):
`services/dual_translation/eval_metrics.py` (pure, I/O-free — greedy ≥50%-overlap span alignment,
span F1, subtype accuracy, severity within-one, clean-FP rate, per-dim + overall band QWK/exact/adjacent),
`tests/test_dt_eval_metrics.py` (23 hand-checked cases green), `scripts/run_dt_grading_eval.py`
(loads the TASK-621 gold sets, grades each item through the SHIPPED v1 cascade, `--live`-gated paid
calls, per-call cost via model-arena pricing). Filed [[evaluations/dt-grading-baseline-2026-07-05]].
Live run $0.030 total (14 model calls). **Dominant finding:** Tier-0 near-exact gate
(`NEAR_EXACT_MISMATCH_RATIO ≤ 0.05`) resolved 83/90 items to full marks before detection — **all 45
single-error seeds swallowed**, ZH 30/30 at Tier 0. Recall is the floor (EN .222 / JA .111 / ZH .000);
overall-band QWK EN .516 / JA .186 / ZH .000; clean-FP rate 0.000 across all three L2s (the predicted
high FP rate did not materialise — Tier 0 short-circuits clean items). Sets the regression floor and
motivates TASK-623 (retire the ratio gate). Grading code untouched. Pages updated: index.md,
tasklist/master.md, tasklist/evidence-first-grading.tasks.md.

## 2026-07-05 query | Daily training algorithm + /session runner audit

Full-pipeline audit (Tier B cron → build_daily_session resolver → /session runner) answering:
HTML ready? algorithm covers all types? schedules properly? interleaves? Pages created: 3
([[algorithms/daily-session-implementation-analysis]], its .tech twin with findings F1–F16,
[[tasklist/daily-session-hardening.tasks]] TASK-700–713). Pages updated: index.md, tasklist/master.md.
Key findings: (F1-critical) Sunday 23:00 UTC cron seeds the *outgoing* week via `_monday_of(today)` —
new week never gets a weekly_plan_states row, so plan users silently drop to legacy loads every Monday;
(F2-critical) session practice player posts time_taken_ms=0 and per-attempt minute-rounding floors the
rest — practice_completed_*_min never advance; (F3) hydration shortfalls silent (get_recommended_tests
rank<=3 cap + never-attempted filter); (F4) no within-session interleaving (ORDER BY skill; practice
appended last); plus ADR-006 retry slots unused in plan path, ON CONFLICT wipes completed_test_ids,
advisory-lock dead code, legacy fallback mislabels test_type. Study-plans tasklist statuses (TASK-201…220
"Not Started" though shipped) flagged for reconciliation as TASK-713. No code changed.

## 2026-07-05 task-done | TASK-621 Gold calibration sets (EN/ZH/JA) frozen

Built `tests/fixtures/dt_gold/{en,zh,ja}.json` — 30 items each (10 clean / 15 single-seeded /
5 multi), sourced from the 28 live `dt_passage` rows (project kpfqrjtfxmujzolwsvdq). Perturbations
LLM-drafted, spans scripted + verified, **every label user-adjudicated 2026-07-05**. Span-integrity
and normalization-survival checks pass for all 90 items; distinct v5 subtypes en=13 / zh=12 / ja=11
(≥10 each). Errors carry v4 `subtype` + `subtype_v5_target` (mechanical re-tag in TASK-626) and
severity in both vocabularies (global/local + minor/major/critical). Bands derived from tech-spec §4.
Reusable builder/verifier: `scripts/dt_gold_seed_helper.py`; provenance + adjudication record in the
fixture `README.md`. JA adjudication dropped `counter_classifier` (no counters in source) and
`script_choice` (beginner text) → replaced with `tense_aspect_ja` + `verb_conjugation`. Surfaced a
grader caveat for TASK-623: `grade_dictation._fuzzy_equal` swallows lone ≤1-edit morphology
(make→made) at Tier 0, so EN morphology seeds use registering agreement forms. No grading code or
migrations touched (fixtures only). Next: TASK-622 (eval harness + v1 baseline).

## 2026-07-04 tasklist | Evidence-First Grading v2 → TASK-621–632 (+ all 5 open decisions approved)

User approved all five framework decisions: severity triad migration, ADR-019 (Application
layer), provisional grades, provisional thresholds, native review deferred. ADR-019 flipped
proposed→accepted; prose-page open questions collapsed to the native-review flag. Converted
the framework to 12 tasks in `tasklist/evidence-first-grading.tasks` (IDs continue from
TASK-620): Phase 0 = 621 gold sets + 622 harness/baseline; Phase 1 = 623 tier-0 fixes + 624
prompt upgrades/rubric v4; Phase 2 = 625 severity triad, 626 taxonomy v5 (XL, authoring), 627
derived scoring/rubric v5, 628 Detector-Verifier restructure (XL, behind DT_FRAMEWORK_V2
flag), 629 descriptor rewrite; Phase 3 = 630 explainer, 631 UI v2, 632 final eval. Every
behaviour-changing task gated on the TASK-622 harness. master.md: Not Started 65→77 + new
section; index updated. Sequencing note: 621→622 must land first — nothing else ships
unmeasured.

## 2026-07-04 design | Evidence-First Grading (DT grading v2) — framework + complete prompts

User request: DT grading must be "specific and precise in pointing out mistakes, clear on grading."
Analysed shipped v1 (`services/dual_translation/{prompts,grader_cascade,tier0}.py`, rubric v2,
taxonomy v4) and found 5 structural gaps: gestalt (ungrounded) bands, generic per-subtype
explanation templates, coarse 9-subtype taxonomy, frequency-adverb band descriptors + no
exemplars, and precision traps (tier-0 ≤5% full marks, fail-open full marks, missing-confidence
default 1.0). Researched MQM severity-weighted scoring, WCF meta-analyses (Kang & Han 2015;
Bitchener & Knoch 2010: direct + metalinguistic wins), CEFR-CV mediation scales, AES/LLM-judge
literature (exemplar anchoring QWK 0.306→0.531; evidence-grounded judging; Hamel Husain/Eugene
Yan), learner-corpus tagsets (CLC ~80, HSK 46, NICT JLE).

Framework: scores COMPUTED from severity-weighted errors (minor 1/major 5/critical 25) — model
detects, Python scores, historical grades re-scorable for free; Detector/Verifier call split
(verify = confirm/reject/adjust each error); 3-layer explanations (Correction + Rule template +
NEW model-generated instance Application in L1); taxonomy v5 (~15–17 subtypes/pair, subtype_meta
with dimension/treatable/cloze flags); highlights[] positive evidence; behaviorally-anchored
descriptors; gold-set eval harness (span F1, FP rate, QWK) gating all version bumps; 4 rollout
phases (measure → prompts → structural → UX). Complete Detector/Verifier/Explainer prompts
authored in EN/ZH/JA (ZH/JA flagged for native review).

Pages created: 3 — `algorithms/evidence-first-grading{,.tech}`, `decisions/ADR-019-evidence-first-scoring`
(proposed). Pages updated: `index` (87→90), `log`, `algorithms/translation-grading-cascade.tech`
(cross-link). Open questions: 5 (severity-triad migration, ADR-019 approval, provisional-grade UX,
threshold calibration, native review). Tasklist conversion NOT done — awaiting user review of the
framework per §5d.

## 2026-07-04 implement | TASK-616 — localised taxonomy (v2/v3/v4) + rubric v2 weight bump, applied live + paid smoke

Stage-4 localisation. **Key correction (confirmed with user):** the brief said to seed per-pair
"weight overrides" into `dt_taxonomy_version`, but `compute_overall_band` reads dimension weights
**only** from `dt_rubric_version` — the taxonomy has no weight path, so taxonomy weights would be dead
config. So TASK-616 bumps two active versions (no code change): **rubric v2** (`ja.fidelity` 0.25→0.30,
`zh.accuracy` 0.35→0.40; band descriptors byte-identical to v1) + **taxonomy v4** (per-directed-pair
tables + enriched templates). This resolves the TASK-604 open question on weight ownership (weights stay
in `dt_rubric_version`).

Taxonomy is cumulative/self-contained, one active row: v2 (EN, adds `ja-en`/`zh-en` + article/preposition
enrichment) → v3 (JA, `en-ja`/`zh-ja` + particle は/が + keigo teineigo/sonkeigo/kenjougo) → v4 (ZH,
`en-zh`/`ja-zh` + classifier 个-overuse + aspect 了/过/着). Final v4 = all 6 directed pairs + baselines;
per-pair subtype lists mirror the L2 baseline (trivially-correct index round-trip), the payload is the
enriched per-L1 templates / per-L2 glosses. ZH/JA strings AI-authored first drafts pending native review.

**Applied live** (`kpfqrjtfxmujzolwsvdq`) via 4 tracked migrations `dt_rubric_v2_seed_task616` +
`dt_taxonomy_{en,ja,zh}_seed_task616`, each deriving the new version in-DB from the prior row (to apply
the exact committed artifacts without re-emitting 10–28 KB of JSON). A host script verified the live
active rows are **semantically identical** to the committed `.sql` files (dict-equality PASS); post-apply
`dt_taxonomy_version`=`1,2,3,4*`, `dt_rubric_version`=`1,2*` (one active each). v1 seeds not archived
(sole record of the still-present version=1 rows). **Paid live smoke (real OpenRouter):** JA keigo/register
downgrade → fidelity=2 + 2 `keigo_register` errors; ZH 个-overuse → accuracy=3 + 4 `classifier` errors;
explanations rendered from the new templates. Offline: 41 new tests + 80 baseline green.

Pages updated: `tasklist/dual-translation.tasks` (TASK-616 Done + weight-ownership note; TASK-604 open
question resolved), `tasklist/master` (Done 36→37), `business-rules/translation-error-taxonomy`,
`features/dual-translation.tech`, `index`, `log` (this entry). Files: `migrations/dt_rubric_v2_seed.sql`,
`migrations/dt_taxonomy_{en,ja,zh}_seed.sql`, `tests/test_dual_translation_taxonomy_localised.py`,
`tests/test_dual_translation_rubric_v2.py`.

## 2026-07-04 update | TASK-619 marked Done — native-language picker verified complete

All four acceptance criteria confirmed by codebase inspection. GET/PATCH /api/users/native-language
in routes/users.py (lines 158–211); picker in templates/onboarding.html (optional, fire-and-forget
PATCH, lines 218–317); view/change section in templates/profile.html (optimistic UI + rollback,
lines 41–51, 532–626); 2 smoke tests in tests/test_native_language_pages.py. _resolve_l1_language_id
unchanged — reads native_language_id directly from users table. Wiki and master.md summary counts
updated: Not Started 67→66, Done 35→36.

## 2026-07-02 implement | TASK-617 — correction-style A/B flag wired (config resolver + /next stamp + dt_submission column)

Turned TASK-608's static `data-correction-style` seam into a real, config-driven A/B assignment.
**Config (`config.py`):** `DT_CORRECTION_STYLE` env flag — `direct_metalinguistic` / `flag_only`
(force arms, the no-code-change QA/rollback lever) / `experiment` (default). New
`Config.resolve_correction_style(user_id)`: forced arm in a forced mode, else a **deterministic
50/50 split on `sha256(user_id)`** (`digest[0] & 1`) so a user is **stably bucketed**; an
unrecognized value fails safe to `experiment`. **Mechanism (lower blast radius): `GET /next` returns
`correction_style`** rather than a template context var — `/next` is already `@supabase_jwt_required`
with the user_id resolved and already returns the JSON the JS consumes, whereas the page route
`/dual-translation` is unauthenticated `render_template`. The static `.dt-wrap` attribute stays as a
safe fallback default. **Persistence (operator chose the durable option):** the arm is **stamped onto
new column `dt_submission.correction_style`** at `/next` time (nullable + CHECK on the two arms;
`migrations/dt_add_correction_style.sql` **applied live** to `kpfqrjtfxmujzolwsvdq` via tracked
`apply_migration` — column+CHECK confirmed), so the experiment stays analyzable even if the config
mode/bucketing changes later. **JS:** `loadNext` overrides `CORRECTION_STYLE` from the payload; the
TASK-608 `flag_only` reveal branch is untouched. **Verified (no OpenRouter spend):** 7 new resolver
unit tests + extended `TestGetNext` (arm returned in payload **and** written to the insert); full DT
suite **185 passed**. Skipped a live `/next` call (would leave a stray `dt_submission` row; the live
CHECK already matches the exact two resolver values and the unit test proves the payload). **Residual
(unchanged from 608):** human browser click-through (one live grade) + native ZH/JA/ES string review
(folds into TASK-616). Built on Opus 4.8 (routing recommends Sonnet 4.6; no functional difference).

## 2026-07-02 implement | TASK-608 — diff-centric result UI built (reproduce → diff/bands/errors), page route + 43 i18n keys ×4 locales

Built the noticing-loop UI on top of the now-live cascade. `templates/dual_translation.html` +
`static/js/dual_translation.js` (SPA-style, two phases, matching `classifier_drill` house style) +
`app.py` page route `/dual-translation` + `dual_translation.*` i18n (43 keys) added to all four
`static/i18n/*.json` (per memory `i18n-applytodom-clobbers-defaults`; ZH/JA/ES are AI first-drafts,
flagged for native review alongside TASK-616). **Phase 1 (feed-up):** L1 reference + collapsible
rubric (top-band descriptor per dim from `/next`'s `rubric_descriptors`) + optional pre-reveal
**self-rating 1–4, client-only** (operator's decision — no schema change; `localStorage`
`dt_selfrating_<submission_id>`, recalled on result). **Phase 2:** the **diff is the centrepiece** —
one aligned flex-cell per `WordDiff` opcode (reference gold-L2 on top, learner deviation below;
**token-level**, no JS re-diff; distinct colours for equal/replace/delete/insert + legend), works for
CJK without word spaces. Per-dim **bands** from `scores`; **naturalness** hidden at age tiers 1–2 and
low-stakes-behind-a-toggle at 3+ (mirrors `_rubric_descriptors_for`). **Feed-forward:** each error
shows `learner_form → corrected_form`, the template-rendered `explanation`, and enum chips (i18n +
humanized-slug fallback). **"Drill this"** = disabled placeholder with `data-subtype` (TASK-613 hook).
**TASK-617 seam:** correction style read from `data-correction-style` on `.dt-wrap` (default
`direct_metalinguistic`; `flag_only` branch present) — the A/B experiment itself is *not* built.
Double-submit latch + `crypto.randomUUID` idempotency key. **Verified (no extra OpenRouter spend):**
4 i18n files valid + identical 43-key set; `GET /dual-translation` → 200 with all element IDs + JS
include; the `/next`→`/submit` contract the JS consumes was live-proven in this session's 607 curl.
**Residual:** human visual browser click-through + native ZH/JA/ES string review. Built this session on
Opus 4.8 (tasklist routing recommends Sonnet 4.6; no functional difference). **DT critical path
602→605→606→607→608 now complete; next is the TASK-617 A/B seam it left clean.**

## 2026-07-02 verify-live | TASK-606 + TASK-607 — grading cascade + routes verified end-to-end against live OpenRouter + live DB

Closed both outstanding live verifications; no product code changed (harness-only fix + one authorized
fixture row). **606 grading smoke:** ran one imperfect reproduction per L2 through `grade_submission`
against real OpenRouter. The prior blocker was harness-only — `DimensionService.get_language_code`
returned `None` in a bare script because the `dim_languages` cache hydrates at Flask startup; fixed by
calling `DimensionService.initialize(db)` explicitly (the "call the load entrypoint" option). Full §2.2
contract confirmed for all three L2s: **zh** (tier1 `qwen/qwen3.6-flash` + tier2 `qwen/qwen3.7-plus`,
1942/7828 tok, 66 diff ops, 2 errors, band 3), **en** (`google/gemini-2.5-flash-lite` +
`google/gemini-3.5-flash`, 1804/223 tok, 30 ops, 0 errors, band 4), **ja** (same Qwen pair, 2283/9761
tok, 99 ops, 2 errors, band 2). Every error carried spans + learner_form + corrected_form + a
**template-rendered** explanation; `grader_trace` recorded real slugs + tokens + `fell_open:False`.
`_decode_error` fail-soft exercised live (one malformed model error dropped, not fatal). **607 live
route path:** drove the real `get_next`/`submit` handlers via Flask `test_client` (patched
`middleware.auth._authenticate` for the fixture user) against the live DB. Needed a completed attempt to
serve — the write classifier declined fabricating one last session, so per the operator's authorization
this session inserted one smoke `test_attempts` row (`72cd5618…`) for user `de6fd05b…` on zh test
`8658495d…`. `GET /next` 200 (served zh passage 1, English l1_text, all 5 rubric descriptors, created
`dt_submission` 1) → `POST /submit` 200 (tier2, persisted 1 `dt_grade` + 2 `dt_error_instance`, band 3)
→ `POST /submit` again 200 with **identical trace and zero new OpenRouter calls** (cached-grade
reconstruction; `dt_grade` stayed 1 row — the UNIQUE held). Idempotency + ownership + persistence all
live-confirmed. **Live smoke artifacts left in DB** (safe to purge): `test_attempts` `72cd5618…`,
`dt_submission` 1 + its grade/error rows. **Next:** TASK-608 diff-centric result UI (the only remaining
critical-path item before the A/B seam TASK-617).

## 2026-07-01 verify-live | TASK-603 — passage builder built + verified live (28 passages + 56 refs); applied the missing TASK-600 router seed

Supabase MCP back online; ran the live half of TASK-603 over a 3-test fixture (1 per L2) via a new
`--test-ids` runner flag. Result: **28 dt_passage** (zh 8 @ age_tier 6, en 10 @ tier 3, ja 10 @ tier 3;
all `active`/`test_transcript`) + **56 dt_passage_reference** (every passage both L1s; fan-out exact
zh→[en,ja]/en→[zh,ja]/ja→[zh,en]; `generator_slug` = en→`google/gemini-2.5-flash-lite`,
zh/ja→`qwen/qwen3.6-flash`). Serving proven read-only: the `_select_next_passage` query for an
English-L1 learner who completed the zh test returns a zh passage + its real English reference
(a persisted `test_attempts` smoke fixture was declined by the write classifier, so verified against
live rows, not a fabricated attempt). Idempotent re-run confirmed live (0 dup passages; refs backfilled).
**Confirmed live schema:** `tests` has NO `age_tier`/`register`/`type`/`status` — derive-from-difficulty
is correct. **Dependency gap found + fixed:** TASK-600's `dual_translation_router_seed.sql` had never
been applied live (0 `dual_translation_*` prompt_templates rows → refs + grading both fail open);
applied via tracked migration `dual_translation_router_seed` (9 vetted non-404 slugs). **Runner bug
fixed:** reference generation was coupled to passage *insertion*, so passages inserted while the router
was unseeded never got refs on re-run — refactored to reconcile refs against all in-scope passages.
**Outstanding:** the end-to-end *grading* smoke (TASK-606 cascade) hit a harness-only issue
(`DimensionService` cache not hydrated in a bare script; one-line fix) and was deferred on session cost —
not a product defect.

## 2026-06-29 implement | TASK-603 — passage builder (dt_passage + L1 dt_passage_reference) code+tests done; live build/smoke deferred (Supabase MCP offline)

Built the corpus passage builder: `services/dual_translation/passage_builder.py` (pure logic) +
`scripts/build_dt_passages.py` (off-hot-path runner) + `tests/test_dual_translation_passages.py`
(39 tests, all mocked — 39/39 green; 68/68 with the existing routes+tier0 suites).
**Key discovery / deviation:** live `tests` has **no** `age_tier`/`register`/`type`/`status` column
(verified via `schema.tech.md`) — it carries `difficulty` (1–9). age_tier is therefore **derived**,
folding difficulty → tier via `DIFFICULTY_TO_TIER` (1–2→T1…8–9→T6) → int 1–6; `register` left NULL;
"active test" filter = `tests.is_active`. Corrected the `dt_passage` row prose in
[[features/dual-translation.tech]] (was "inherited from source"). User confirmed (AskUserQuestion):
derive-from-difficulty, in-app dedupe on `(source_ref_id, normalized l2_text)` (no schema change),
CJK-aware regex segmentation with non-overlapping 2–4 sentence windows (short tail merged+rebalanced),
and a small first batch (`--limit 4` tests/lang). References reuse the grading router
(`resolve_tier('tier1', l2)`) as a plain L1 translation; `generator_slug` records provenance.
**Deferred (Supabase MCP not connected this session):** apply taxonomy seed if pending, run the live
fixture build, confirm `_select_next_passage` serves a passage, and the end-to-end per-L2 grading smoke.

## 2026-06-29 implement | TASK-620 — taxonomy v1 baseline seed (dt_taxonomy_version) authored + unit-tested (live apply pending)

The taxonomy twin of TASK-604. Authored + activated (offline) the single `dt_taxonomy_version`
row the cascade hard-requires: `grader_cascade.get_active_taxonomy` raises `RuntimeError` until an
`is_active` row exists, the same hard-block the rubric seed just cleared. `taxonomy` conforms to the
TASK-606 "Implementation contracts" shape ([[algorithms/translation-grading-cascade.tech]]) — **not**
reinvented: `pairs["<l2>"].subtypes` (ordered; index is the `_decode_error` contract),
`subtype_glosses["<subtype>"]["<l2>"]` (shown to the grading model, in the L2), and
`templates["<subtype>"]["<l1>"]` (learner-facing, `{learner_form}`/`{corrected_form}` only).
`category`/`source`/`severity` are intentionally absent (hardcoded enums + `dt_error_instance` CHECK).

Baseline = an `<l2>` table per L2 only (every L1 shares it via `_resolve_subtypes`' fallback,
maximizing prompt-cache reuse). Per the operator's choices: L1 templates cover **all three live L1s
(en/zh/ja)** and the subtype set is the **full per-language catalogue** from
[[business-rules/translation-error-taxonomy]] — shared `[word_order, word_choice, omission, register]`
+ EN article/preposition/phrasal_verb/tense_aspect/subject_verb_agreement, JA particle/keigo_register/
counter_classifier/script_choice/topic_comment, ZH classifier/aspect_marker/topic_comment/
ba_construction/resultative_complement. 18 distinct subtypes (9/L2), 27 L2 glosses, 54 L1 templates.

Two findings surfaced (not guessed): (1) `dim_languages` holds only zh(1)/en(2)/ja(3) — there is **no
`es` row**, and `l1_language_id` FKs to it, so an `es` L1 can never reach `render_explanation`;
Spanish is a UI i18n locale only. The brief's "all four L1s" was not achievable. (2) The brief
suggested TASK-617, but 617/618/619 were already assigned — filed as **TASK-620**. ZH/JA glosses +
templates are AI-authored first drafts pending native review, flagged for QA with TASK-616.

Authored `migrations/dt_taxonomy_v1_seed.sql` (idempotent: `ON CONFLICT (version) DO UPDATE` refreshes
taxonomy/description only; `is_active` set only on first INSERT — mirrors the rubric seed). New
`tests/test_dual_translation_taxonomy_seed.py` (31 cases) extracts the real seed JSON out of the
`.sql` and drives `get_active_taxonomy` / `_resolve_subtypes` / `_resolve_subtype_labels` /
`render_explanation` / `_decode_error` round-trip with no live DB — all pass (DT suite 101 green).

**Applied live (2026-06-29):** after the Supabase MCP reconnected, applied via tracked
`apply_migration` (`dual_translation_taxonomy_v1_seed`) to project `kpfqrjtfxmujzolwsvdq`.
Live-verified: exactly one `is_active=true` row (v1); top keys `pairs/subtype_glosses/templates`;
`pairs` = en/ja/zh (9 subtypes each); 18 gloss + 18 template subtypes — the query shape
`get_active_taxonomy` runs. No DATABASE_URL write was used. **TASK-620 Done.** TASK-603 (passages)
is now the sole remaining blocker for the end-to-end live grading smoke.

## 2026-06-27 implement | TASK-604 done — rubric v1 seed (dt_rubric_version) applied live

Seeded + activated the single `dt_rubric_version` row the grading cascade hard-requires:
`grader_cascade.get_active_rubric` raised `RuntimeError` until now, so `/api/dual-translation/next`
returned an empty feed-up and submit could not grade. `config` conforms to the TASK-606
"Implementation contracts" shape ([[algorithms/translation-grading-cascade.tech]]) — **not**
reinvented: `weights.default[dim]` + partial `weights.by_language[l2][dim]`, and
`band_descriptors[str(age_tier)][dim][l2] = {"1".."4": text}`. 5 dims; `accuracy`+`understandability`
highest weight (0.30), `naturalness` lowest (0.10) and omitted from band descriptors at age tiers
1–2 (ADR-018 level-neutral: per-tier descriptors calibrate content level, not a leniency curve).
Per-language baseline overrides: `ja fidelity 0.25` (particle/keigo), `zh accuracy 0.35`
(classifier/aspect). Band descriptors = 4 bands × 6 tiers × 3 L2 (zh/en/ja) = 336 strings — one
level-neutral quality ladder per dimension with a per-tier concrete→abstract content-level frame as
the only per-tier variation. ZH/JA text is an AI-authored first draft, flagged for native review
with TASK-616.

Authored `migrations/dt_rubric_v1_seed.sql` (idempotent: `ON CONFLICT (version) DO UPDATE`,
`is_active` set only on first INSERT, so a re-apply after a later version supersedes v1 will not
silently re-activate it). Applied live to project `kpfqrjtfxmujzolwsvdq` via Supabase MCP
`apply_migration` (tracked migration `dual_translation_rubric_v1_seed`). Verified live: exactly one
`is_active` row (v1); real `get_active_rubric` returns it; the live `config` is byte-identical to the
committed migration; and `compute_overall_band` / `routes…_rubric_descriptors_for` /
`prompts._band_descriptors_text` all read it without `KeyError`. New shape test
`tests/test_dual_translation_rubric_seed.py` (49 cases) extracts the real seed JSON straight out of
the `.sql` and feeds it through both consumer access paths (no live DB) — passes.

Remaining gap (flagged, not built): live end-to-end grading smoke is still blocked on a baseline
`dt_taxonomy_version` seed (`get_active_taxonomy` raises the same way) and on passages (TASK-603) —
do it as part of/after those. Open question surfaced (not decided): per-language weight ownership
overlaps TASK-616 (Stage 4 localisation); this seed ships a baseline `by_language` block only.

## 2026-06-25 implement | TASK-607 done (unit-tested) — dual-translation routes + idempotency

Built `routes/dual_translation.py` (`GET /api/dual-translation/next`, `POST
/api/dual-translation/<id>/submit`), registered in `app.py`. Thin orchestrator: every DB-touching
step is its own monkeypatchable helper (`_resolve_l1_language_id`, `_select_next_passage`,
`_rubric_descriptors_for`, `_get_submission`, `_get_passage`, `_cached_grade`, `_persist_grade`);
grading itself is delegated wholesale to TASK-606's `grader_cascade.grade_submission` — this module
only persists `dt_grade`/`dt_error_instance` rows, never re-implements grading.
**Real spec/schema mismatch found, not papered over:** the wiki's `GET /next` selection rule said
"L1 reference chosen from `user_languages`," but `user_languages` is the L2 *study*-language
enrollment table (verified against `Project Knowledge/12-PRD/.../08-language-selection.md`) — no
column anywhere recorded a learner's native language. Flagged this to the user via
clarifying question rather than guessing; the user chose to add a real column. Added
`users.native_language_id` (smallint, nullable, FK → `dim_languages`) via
`migrations/add_users_native_language.sql`, applied live to the Supabase project
(`kpfqrjtfxmujzolwsvdq`) via the Supabase MCP and verified through `information_schema.columns`.
`GET /next` falls back to English (id=2) while the column is NULL, which is every user today — no
onboarding UI sets it yet; that's a real follow-up, not built here.
Duplicate-submission detection is "does a `dt_grade` row already exist for this `submission_id`"
rather than a literal idempotency-key string compare — `dt_grade.submission_id` is UNIQUE, so this
is the crash-proof superset of the literal rule (the key does match on a same-key retry, since
`_persist_grade` writes it back onto `dt_submission` after the first successful grade) and avoids
hitting a DB integrity error on any later resubmission attempt regardless of what key it carries.
`_rubric_descriptors_for` also wires in ADR-018 (hides `naturalness` at age tiers 1–2) and degrades
to `{}` rather than 500ing when no `dt_rubric_version` is active (TASK-604 hasn't shipped — the
common case today). `BUDGET_EXCEEDED`/TASK-610's enqueue point are left as explicit `# TODO`
markers, scoped out exactly as briefed. 21 unit tests in `tests/test_dual_translation_routes.py`,
all passing; full suite re-verified green (589 passed, 1 skipped via `pytest tests/`). Live curl
against a real seeded passage remains blocked on TASK-603/604, as expected. Marked done in
[[tasklist/dual-translation.tasks]] and [[tasklist/master]].

## 2026-06-23 implement | TASK-606 done (unit-tested) — dual-translation grading cascade

Built `services/dual_translation/prompts.py` (L2-only system/user prompt builders for Tier 1/2;
fixed `CATEGORY_ENUM`/`SOURCE_ENUM`/`SEVERITY_ENUM` constants mirroring the live
`dt_error_instance` CHECK constraints; AI-authored first-draft EN/ZH/JA instructional templates,
flagged for native-speaker QA alongside TASK-616) and `services/dual_translation/grader_cascade.py`
(`grade_submission`: Tier 0 short-circuit → Tier 1 accuracy/range → Tier 2
understandability/fidelity/naturalness, which always runs once Tier 0 hasn't resolved since those
three dims are Tier-2-exclusive → eager explanation render → fail-open merge). Had to make two
JSON config shapes concrete that the wiki only described in prose — documented in
[[algorithms/translation-grading-cascade.tech]] "Implementation contracts": `dt_rubric_version.config`
(weights + band descriptors) and `dt_taxonomy_version.taxonomy` (per-pair subtype tables with an
L2-baseline fallback, **new** `subtype_glosses` for what the model sees in the L2-only prompt vs.
the existing per-L1 `templates` for the learner-facing explanation — also documented in
[[business-rules/translation-error-taxonomy]]). Escalation ("Tier 2 re-checks accuracy/range on low
confidence or large diff") is two module constants (`CONFIDENCE_ESCALATION_THRESHOLD=0.6`,
`LARGE_DIFF_RATIO=0.3`); the diff-ratio side reuses a new `Tier0Result.mismatch_ratio` field
(additive change to TASK-605's `tier0.py`, both existing test suites re-verified green) instead of
re-diffing. Fail-open is uniform across failure modes (no usable slug, malformed/unparseable JSON):
the affected tier's owned dimensions default to `MAX_BAND` and contribute no errors — total outage
degrades to a Tier 0-style full-marks grade, a deliberate generous reading of "fail-open to Tier 0
marks." 38 unit tests across 4 files (router 9, tier0 8, prompts 11, grader_cascade 10), all
passing; every DB/OpenRouter boundary is mocked (`get_active_rubric`, `get_active_taxonomy`,
`resolve_tier`, `call_model_with_usage`), mirroring TASK-600's `resolve_tier` mocking convention.
One of the new tests caught a real pre-ship bug: the first prompt draft leaked raw English
enum/subtype identifier strings (e.g. literal "grammatical", "article_omission") into the ZH/JA
prompts — fixed with per-language `_CATEGORY_GLOSS`/`_SOURCE_GLOSS`/`_SEVERITY_GLOSS` constants and
the `subtype_glosses` concept. **Outstanding:** live smoke (one passage per L2 end-to-end against
real OpenRouter) needs TASK-604 (rubric seed) and at least a baseline taxonomy seed first — neither
has shipped, so `get_active_rubric`/`get_active_taxonomy` currently raise loudly (by design, no
silent fallback) in any real environment. Marked done in [[tasklist/dual-translation.tasks]] and
[[tasklist/master]].

## 2026-06-23 implement | TASK-605 done — dual-translation Tier 0 deterministic pre-pass

Built `services/dual_translation/tier0.py`: `grade_tier0(passage_id, gold_l2, reproduction,
language_code)` — the always-first, no-model-call grading step. Pipeline: NFKC width
normalization + `jaconv.kata2hira` kana folding for JA (same pairing `services.furigana_service`
already uses for reading comparisons) on top of `services.dictation.grader.grade_dictation`, which
is reused unmodified for tokenization, Levenshtein-tolerant diffing, and the opcode array that
becomes `dt_grade.diff`. Exact or fuzzy-equal (`accuracy == 1.0`) resolves with all-4 scores across
the 5 rubric dimensions, empty `errors[]`, `grader_trace={tier:'tier0', deterministic_prefilter:true,
cache_hit:false, tokens:{in:0,out:0}, slugs:[]}`. The embedding-similarity gate (provider still
OPEN per [[algorithms/translation-grading-cascade.tech]]) is a literal diff-mismatch-ratio stub
(`NEAR_EXACT_MISMATCH_RATIO=0.05`) with a `TODO(embedding-provider)` marker — submissions within the
ratio resolve the same as a true fuzzy match; large diffs return `resolved=False` for the cascade
(TASK-606, not built yet) to pick up, diff already computed so it's never redone. Result cache is a
plain in-process `dict` keyed `sha256(passage_id:normalized_reproduction)`, matching this package's
existing convention (`router.py`'s `_cfg_cache`) rather than a new DB-backed layer. Tests:
`tests/test_dual_translation_tier0.py`, 8 new cases (exact match, fuzzy-typo tolerance, gate-stub
small diff, large-diff escalation, cache hit on resubmit, cache key includes passage_id, JA
full-width-digit normalization, JA kana normalization) — 17/17 passing alongside the existing router
suite. Marked done in [[tasklist/dual-translation.tasks]] and [[tasklist/master]].

## 2026-06-23 implement | TASK-602 done — dual-translation groundwork migration

Created `migrations/dual_translation_groundwork.sql` — the 7 `dt_*` tables exactly per
[[features/dual-translation.tech]] Database Impact: `dt_passage`, `dt_passage_reference`,
`dt_submission`, `dt_grade`, `dt_error_instance`, `dt_rubric_version`, `dt_taxonomy_version`.
Applied to the live DB via Supabase MCP and verified via `information_schema`/`pg_constraint`:
all 7 present; `dt_passage.source_kind` CHECK is `test_transcript`-only (no `mystery_scene`);
`dt_passage_reference` has `UNIQUE (passage_id, l1_language_id)` and `ON DELETE CASCADE` on
`passage_id`; `dt_grade.submission_id` is `UNIQUE` with `ON DELETE CASCADE`;
`dt_error_instance.explanation` is `NOT NULL`. One deliberate deviation from the literal spec:
`dt_passage.source_ref_id` is typed `uuid`, not the spec's `bigint` — `tests.id` is `uuid` in the
live schema (confirmed via `information_schema.columns`), so `bigint` could never have held a
real value; no FK was added to `tests(id)` (polymorphic source pointer, mirrors
`llm_calls.artifact_id` — `source_kind` is locked down via CHECK today but the column is designed
to support other source kinds later without a type change). RLS/grants were left out of scope —
not part of this task's acceptance criteria, and the tech spec calls out submission ownership as
an application-layer check, not a database-level one; flagged as a follow-up before TASK-607
(routes) ships. Marked done in [[tasklist/dual-translation.tasks]] and [[tasklist/master]].

## 2026-06-23 implement | TASK-600 done — dual-translation model router

Built `services/dual_translation/router.py`: `resolve_tier(db, tier, language_id)` resolves
tier1/tier2/tier3 to an OpenRouter slug via `prompt_service.get_template_config` (keyed by
`task_name='dual_translation_tier{1,2,3}'` + `language_id`), then re-verifies the slug against
`model_arena.pricing.fetch_model_list`. On a missing/delisted slug it walks down to the next
cheaper tier (and ultimately to a `tier0`/`slug=None` sentinel if nothing is usable) and logs the
fall-open — never hard-fails, per the cascade's existing fail-open contract. `ResolvedRoute.as_trace_entry()`
gives `grader_trace.slugs[]` the slug actually used, not the one originally requested.
Added `migrations/dual_translation_router_seed.sql` — 9 rows (3 tiers × ZH/EN/JA), EN on
`google/gemini-2.5-flash-lite` (tier1) / `google/gemini-3.5-flash` (tier2/3), ZH+JA on
`qwen/qwen3.6-flash` (tier1) / `qwen/qwen3.7-plus` (tier2/3) — all slugs already confirmed live
elsewhere in this repo, explicitly avoiding the delisted `qwen/qwen-max` / `google/gemini-flash-1.5`
(memory `prompt-template-model-slug-rot`). Tests: `tests/test_dual_translation_router.py`, 9 new
cases (basic resolution, per-language threading, single- and multi-step fall-open, exhausted-tiers
sentinel, verify=False short-circuit, cfg caching, model-list-fetch-failure non-fallback). Full
suite: 539 passed, 1 skipped. Marked done in [[tasklist/dual-translation.tasks]] and
[[tasklist/master]]. Did not touch `dt_*` table migrations (TASK-602, separate task).

## 2026-06-23 update | Dual Translation routing — model + thinking per task

Annotated [[tasklist/dual-translation.tasks]] with a per-task **model + thinking-level** execution
layer (cost-tiered: Opus 4.8 for hard/novel/linguistic-content, Sonnet 4.6 for standard
implementation, Haiku 4.5 for trivial single-table migrations). Added an **Execution routing**
section (routing table + dependency-ordered waves 0–5 + critical path 602→605→606→607→608→617).
No task re-scoped (still 19). Tally: Opus ×6 (603,604,606,610,616,618), Sonnet ×11, Haiku ×2
(609,612); ultrathink ×2 (606,616). Pages updated: [[tasklist/dual-translation.tasks]], this log.

## 2026-06-23 revise | Dual Translation — operator editing notes applied

Refinements after the initial ingest (same day):
- **Privacy:** no special posture; learner reproduction text is **retained for analysis**. Closed the OPEN privacy question.
- **Budget:** per-user/day token budget is a **required tunable config value** (not hardcoded).
- **Source:** `tests.transcript` **only** (mystery scenes dropped from `source_kind`).
- **Selection:** passages served from the learner's **already-completed** tests (reading/listening/dictation) → at-level by construction.
- **Grading level:** **level-neutral** (difficulty controlled at selection); only `naturalness` is tier-dependent and hidden at age tiers 1–2. New **[[decisions/ADR-018-level-neutral-grading]]**.
- **Remediation interleaving:** error exercises interleave into **both** the dual-translation queue **and** Practice Engine sessions; error cards are **not sense-linked** (subtype-keyed stream). New **TASK-618**; ADR-017 consequence revised.
- **Embeddings:** **not needed** — cluster errors deterministically by taxonomy subtype (pgvector optional later). Closed the OPEN embeddings question; TASK-610 revised.
- **Models:** **flash-style, language-dependent** OpenRouter slugs (Gemini-flash EN, Qwen ZH/JA). Grading prompts are **target-language-only, numerical-index output** (no English/prose); **explanations rendered from per-subtype × per-L1 templates** keyed by the numerical subtype index (ADR-015 revised; eager + cheap + rule-compliant).

Pages updated: [[features/dual-translation]] (+ .tech), [[features/dual-translation-remediation.tech]],
[[algorithms/translation-grading-cascade.tech]], [[business-rules/translation-error-taxonomy]],
ADR-015, ADR-017, **+ADR-018**, [[tasklist/dual-translation.tasks]] (18→19 tasks),
[[tasklist/master]] (Not Started 73→74), [[index]] (86→87), this log.

## 2026-06-23 ingest | Dual Translation feature (brief + learning-science report)

Source: `raw/dual-translation-implementation-brief.md` + `raw/compass_artifact_…_text_markdown.md`
(the "Designing a Dual-Translation Feature" learning-science report). Ingested per the brief's §0
("load repo conventions; established repo principles win; resolve [RECONCILE] against the codebase;
output a staged plan").

**Clarifying interview (4 questions answered before any page written):**
1. Source corpus → **short passages (2–4 sentences) from test transcripts / mysteries**; corpus is
   L2-only, so L1 references are generated and stored alongside (`dt_passage_reference`).
2. Direction → **L1→L2 back-translation only** (MVP).
3. L1 model → **per-user L1 (any of ZH/EN/JA)** → directed-pair taxonomy, L1 reference per supported L1.
4. Placement → **fully standalone surface** (`dt_*` tables/routes/pages), reuse existing services as code.

**[RECONCILE] resolutions (operator notes win over the brief):** OpenRouter slugs in `prompt_templates`
(not Anthropic Haiku/Sonnet/Opus tiers; no batch-discount tier exists → "batch" = off-hot-path);
**age tiers (ADR-003)** not CEFR for rubric bands; **explanations eager/first-class** (overrides brief
§4.4 lazy — operator: explaining *why* each error is an error is vital); source from **existing corpus**;
**reuse** dictation Levenshtein grader for Tier 0 and FSRS-4 code for remediation scheduling.

**Pages created (11):** [[features/dual-translation]] + .tech (Feature 1 grading) +
[[features/dual-translation-remediation.tech]] (Feature 2); [[algorithms/translation-grading-cascade]]
+ .tech; [[business-rules/translation-error-taxonomy]]; ADR-014 (reference-first grading), ADR-015
(eager explanations), ADR-016 (per-pair taxonomy), ADR-017 (standalone, L1→L2 MVP);
[[tasklist/dual-translation.tasks]] (TASK-600–617, 4 stages + cross-cutting).
**Pages updated:** [[index]] (75→86), [[tasklist/master]] (Not Started 55→73), this log.

**Open questions flagged (not blocking):** embeddings provider for error clustering (Stage 2);
privacy/retention posture for learner text sent to OpenRouter (resolve before Stage 1 ships);
N/W promotion thresholds (defaults proposed: N=3, W=30d/20 submissions); per-user/day token budget value.

## 2026-06-18 change | TASK-507 + TASK-509 done — semantic_class backfill + Traditional Chinese groundwork

**TASK-507** — classified all 9,865 lemmas (ZH 3,890 / EN 3,571 / JA 2,404) into the ratified 6-value
`semantic_class` enum, 100% coverage, 0 failed. New `migrations/semantic_class_backfill.sql` (adds
`dim_vocabulary.semantic_class_confidence` + 3 `prompt_templates` seeds on `google/gemini-3.5-flash`,
one per language since `language_id` is NOT NULL) and `scripts/backfill_semantic_class.py` (~50 lemmas/
call, context = POS + primary definition, low-confidence→`abstract`+flag, idempotent, llm_calls logged).
Run note: JA stalled at batch 26 on OpenRouter credit exhaustion (non-retryable, 0 retries); operator
topped up and `--language ja` re-ran idempotently to fill the last 1,154 rows. Distribution plausible
(action/abstract/concrete/property dominant; function/proper small). 198-row stratified spot-check CSV
(`spot_check_semantic_class.csv`) handed to operator — the ≥90% human sign-off is their step, not faked.
Idempotency proven (re-run found 0 lemmas).

**TASK-509** — dual-store Traditional Chinese. New `migrations/traditional_chinese_groundwork.sql`
(`dim_vocabulary.lemma_traditional` + `script_conversion_overrides`), `opencc==1.3.1` in requirements,
`services/vocabulary_ladder/script_converter.py` (`ScriptConverter`: OpenCC s2twp + sentinel-priority
overrides; non-Han passes through), renderer `_render_hant_mirror` step (ZH-only, after judge sidecars
popped), and `scripts/backfill_hant_mirrors.py` (lemmas + exercise mirrors, writes only on diff →
no-op re-run + override-correction both work). Results: lemma_traditional 100% (3,890; 2,406 differ),
all 2,393 exercises mirrored with option-count parity (2,388 updated + 5 pilot skipped). s2twp phrase
awareness resolved the 发/干/后/面 ambiguities (bare `干→幹` vs `晒干→曬乾`) so jieba was unnecessary.
Serve convention documented: `users.exercise_preferences.script_variant` (consumed by TASK-526).

Two Phase-0 prereqs for the TASK-515 batch gate now closed. Both repo migration files applied live (509
via `execute_sql` after `apply_migration` 502'd). Done 24→26, Not Started 57→55. Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-17 change | TASK-508 done — live JA P1 smoke passed

Ran the deferred TASK-508 acceptance (now unblocked: JA senses exist post-TASK-505). Generated one JA P1
asset via `CoreAssetGenerator(db, 3).generate(35000, [])` (機械, concrete noun; throwaway script in
c:\tmp, generate()-only so no DB write/cleanup). **SMOKE PASS** on model qwen/qwen3.7-plus: all 11 keys
present, 10 sentences; **all three JA-specific additions verified live** — register=`polite` (keigo),
per-sentence furigana=`きかい べんり`, 助数詞 counter=`台` in morphological_forms; and semantic_class
emitted the ratified English token `concrete` (normalises cleanly, as designed). This closes the last
TASK-508 acceptance criterion. TASK-508 [~]→[x]. Done 23→24, In Progress 1→0. With 505/506/508/511 all
done, the JA-data-dependent Phase-0 fan-out is fully closed. Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-16 change | TASK-505 done + TASK-506 done — JA vocab bootstrap (live batch over 82 tests)

Ran the deferred JA extraction batch (`scripts/backfill_vocab.py --language ja`) over all 82 JA tests.
**First live run surfaced two prerequisites the prior code-only session never hit** (both fixed):
(1) missing JA `vocab_phrase_detection` prompt — extraction hard-failed all 82; seeded
`migrations/ja_vocab_phrase_detection_seed.sql` (cloned from ZH/EN, JA MWE taxonomy, gemini-2.5-flash-lite,
idempotent). The sibling `vocab_definition_generation`/`vocab_sense_selection` JA rows already existed.
(2) `wordfreq` JA tokenization needs `MeCab` (separate binding from fugashi) — installed `mecab-python3`
+ `ipadic` into the venv, added to `requirements.txt`. Validated on a 2-test smoke before the full run.
**Results: all 82 tests processed, 0 failed → 2,404 JA vocab (100% POS), 4,792 senses, frequency_rank
98.59%, 0 助詞/助動詞 lemmas** (clean dictionary-form lemmatisation). Extraction degraded gracefully on
occasional malformed phrase-detection JSON with fallback to `qwen/qwen3.6-flash`. Then ran
`backfill_pronunciations.py --language ja` (deterministic fugashi→kana) → **JA pronunciation 100%
(4,792/4,792)**, closing **TASK-506** fully (ZH 100% + JA 100% + register column). Cost: the batch roughly
doubled session spend ($110→$245; one definition-gen LLM call per unique lemma); operator explicitly
approved the full run after a cost check at the 54/82 mark. TASK-505 [~]→[x], TASK-506 [~]→[x]. Done
21→23, In Progress 3→1 (only TASK-508's optional live P1 smoke remains, now runnable since JA senses
exist). Pages updated: [[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-14 change | TASK-506 in progress — register column + ZH pronunciation backfill (JA deferred)

`migrations/dim_word_senses_register.sql` (ADD COLUMN IF NOT EXISTS `register text`) applied live +
verified (committed under TASK-508 for sequencing). New deterministic, no-LLM-cost
`scripts/backfill_pronunciations.py`: ZH reuses the existing sandhi engine
`services/pinyin_service.process_passage` (jieba word-context + pypinyin + 三声/一/不 sandhi), storing
`"<tone-marked pinyin> (<tone digits, sandhi-applied>)"` (diacritics=base tones, digits=context tones);
JA uses fugashi + unidic-lite → hiragana (verified offline: 食べる→たべる, 学校→がっこう, 図書館→としょかん).
**ZH run hit 100% coverage (8084/8084)**, polyphones correctly disambiguated by word context
(便宜=pián yi, 重复=chóng fù, 重要=zhòng yào, 长大=zhǎng dà, 音乐=yīn yuè); idempotent re-run fetched 0
rows. (The run was launched via a `| findstr` pipe that errored under bash — `findstr` is a cmd builtin,
not a Unix tool — but the Python writer completed all DB updates; the script is clean.) **DEFERRED:**
the JA kana backfill (≥95%) — 0 JA senses exist until the TASK-505 batch; `--language ja` is a no-op
today, code path ready. Status 506 Not Started → In Progress. In Progress 2→3, Not Started 58→57.
Phase-0 fan-out for this session complete (511 done; 508 + 506 landed, JA-data-dependent pieces deferred
to TASK-505). Pages updated: [[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-14 change | TASK-508 in progress — JA prompt seeds (seeds + code landed; live smoke deferred)

Seeded all JA (lang=3) `prompt_templates` rows, structurally cloned from the active ZH set, all
`provider='openrouter'` / `model='qwen/qwen3.7-plus'`. `migrations/ja_prompt_seeds.sql` (idempotent
`WHERE NOT EXISTS` — there is **no** unique `(task_name,language_id,version)` constraint, only PK on
id, verified) applied live: `vocab_prompt1_core` (+ §6.6 JA additions), `vocab_prompt2_exercises`,
`vocab_prompt3_transforms`, the 4 ladder judges, `exercise_sentence_generation`; plus activated the
pre-existing `cloze_distractor_generation` lang=3 v1 (already a complete JA template, just inactive).
Verified: all 9 tasks have exactly 1 active row with model+provider populated → `get_template_config`
resolves for lang=3. **JA P1 numeric-key schema** (documented in the migration header): key 10=register
(keigo), key 5=lemma kana reading, per-sentence furigana=sentence key 5, 助数詞 counter under
morphological_forms (key 9, JA analogue of ZH rule 18). **`semantic_class` decision (flagged):**
`_LEGACY_SEMANTIC_CLASS_MAP` has no JA labels, so the JA P1 emits the ratified English enum tokens
directly (pass through `normalize_semantic_class`, no CHECK violation). **L1 distractor rules + judge
enforce AUDIO confusability** (long/short vowel, dakuten, sokuon/hatsuon, pitch) per
[[l1_is_listening]], never visual similarity. **Code:** register *parse* already handled by
`PROMPT1_KEY_MAP '10'→register`; added the missing *persist* of `register` to
`asset_pipeline._update_vocabulary_metadata` (no-op for ZH/EN), and `'5':'furigana'` to
`SENTENCE_KEY_MAP`. **Sequencing (flagged):** applied `migrations/dim_word_senses_register.sql`
(nominally TASK-506's file) now so the register write target exists — committed with this task.
**DEFERRED:** the live end-to-end P1 smoke sense — 0 JA senses exist until the TASK-505 batch; the
single LLM call is held for that cost-budgeted session (code ready, not fabricated). Status 508 Not
Started → In Progress. Suite: **530 passed, 1 skipped** (baseline). In Progress 1→2, Not Started 59→58.
Next: TASK-506 (pronunciation backfill — ZH deterministic run now; JA deferred). Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-14 change | TASK-511 done — generation_queue migration

Phase-0 infra (XS, no deps). Created `migrations/generation_queue.sql` (§6.5 DDL verbatim:
`id` bigint identity PK, `sense_id` int FK→dim_word_senses, `language_id` smallint, `reason`
text, `status` text default 'pending', `detail` jsonb, `requested_at`/`completed_at` timestamptz,
`UNIQUE (sense_id, reason)`) with idempotent `CREATE TABLE/INDEX IF NOT EXISTS` and the required
`(status, requested_at)` index. Applied live via Supabase MCP. Verified: 8 columns, 1 UNIQUE
constraint, status index present; round-trip DO-block smoke (insert → duplicate `ON CONFLICT DO
NOTHING` no-op confirmed → status update → cleanup) left the table empty. The FK to
`dim_word_senses(id)` is satisfied by existing ZH/EN senses (JA senses still absent — fine, the
queue can be empty of JA). Note for downstream: `dim_word_senses` has **no `language_id`** column;
the queue's `language_id` is producer-supplied. Done 20→21, Not Started 60→59. Next: TASK-508 (JA
prompt seeds). Pages updated: [[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-14 change | TASK-505 in progress — B4 CJK whole-word fix (code only; batch deferred)

Operator paused the expensive live LLM extraction batch (session cost guardrail, ~$74) and asked for the code
prerequisites only. **Key finding: most of B4 / TASK-505 was already in the repo before this session** —
(a) `asset_pipeline._extract_sentences_with_word` already takes `language_id` + uses
`LanguageProcessor.for_language(...)` (the `self.db_language_id` typo that hardcoded the English processor is gone);
(b) `services/vocabulary/frequency_service.py` is already language-agnostic with `ja` in `_LANG_MAP` and `wordfreq`
already in `requirements.txt`; (c) `scripts/backfill_vocab.py` already accepts `--language ja`, propagates
`language_id`, and sets `frequency_rank` from `compute_zipf_for_vocab_item` (zipf-as-rank, pre-existing). **Net-new
code:** the last remaining B4 item — CJK whole-word matching was still a substring fallback
(`contains_target_whole_word` → `word in sentence`, which false-positives 子 inside 椅子). Added
`LanguageProcessor.contains_whole_word` (ASCII → `\b`; non-ASCII → tokenise and accept only a standalone token or an
exact contiguous token run) and wired it into `_extract_sentences_with_word`. New `tests/test_contains_whole_word.py`
(7 tests: stub-tokenizer algorithm + real jieba). Suite: **530 passed, 1 skipped**. **Deferred (operator-approved):**
acceptance 2–4 — the live `backfill_vocab.py --language ja` run over the 82 JA tests (dim_vocabulary lang-3 rows > 0),
`frequency_rank` ≥90% coverage, and the 50-lemma spot-check — all need the LLM batch + live writes; held for a fresh
cost-budgeted session (code is ready to run it). Status: TASK-505 Not Started → In Progress; counts In Progress 0→1,
Not Started 61→60. Pages updated: [[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-14 change | TASK-504 done — dim_exercise_capabilities routing matrix

Phase-0 foundation. Created `dim_exercise_capabilities` (§6.2 DDL verbatim) and applied
`migrations/dim_exercise_capabilities.sql` live (Supabase MCP): **55 rows** (54 enabled, 1 disabled marker =
ZH `morphology_slot` — Chinese is analytic, its L4 is `classifier_match`). Seeds encode §5's Lang column across
ZH/EN/JA: per-(language, type) `pos_classes`, `ladder_level`, `generator`, `requires`, `judge_key`, `is_enabled`.
**DB-vs-spec resolution (flagged):** the live `dim_exercise_types` had 25 rows but **no `morphology_slot`** despite
it being L4's `exercise_type` in `config.py` LADDER_LEVELS, §5 #5, and the explicit `(1,'morphology_slot',…)` example
in the §6.2 DDL — TASK-503 added the 12 new types assuming it pre-existed (it never did). Capability rows FK-reference
`dim_exercise_types(type_code)`, so the migration additively backfills that one missing type row (`form_production`,
45s, `ON CONFLICT DO NOTHING`) — same additive pattern TASK-503 used for the `fluency` CHECK. **Routing rewire:**
`services/vocabulary_ladder/config.py` `compute_active_levels` is now matrix-derived (sorted distinct enabled
`ladder_level` over rows whose `pos_classes` cover the class), language-aware, but produces the *same* canonical level
sets as TASK-502 (`proper`→[], `function`→[1,2,3,6,7], `concrete`→[1,2,3,4,6,7,9] with L4 type per language:
ZH=classifier_match, EN=morphology_slot, JA=particle/counter, all+cloze_typed as the general productive L4) — so the
existing `test_active_levels_routing.py` stayed green unchanged. Legacy hardcoded routing kept only as
`_fallback_active_levels` (used when a language has no matrix rows); `'all'` pos sentinel = every class except `proper`.
In-code `CAPABILITY_MATRIX` mirrors the SQL seeds (offline routing + test source; DB copy is runtime SoT, cached at
startup by `DimensionService.get_exercise_capabilities`). New `tests/test_capability_matrix.py` (25 tests) enforces the
§4 inventory invariant (every (language × semantic_class) has ≥1 enabled type per required family) + structural checks
(judge_key NULL ⟺ deterministic) + the ZH-concrete verification (classifier_match@L4, no morphology_slot). Suite:
**523 passed, 1 skipped** (498 baseline + 25 new). Done 19→20, Not Started 62→61. Next: TASK-505 (JA vocab bootstrap,
no deps) or the Phase-0 fan-out (506–511) toward the TASK-515 batch gate. Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-13 change | TASK-503 done — dim_exercise_types family map fixed + 12 new types

Applied `migrations/fix_dim_exercise_types_families.sql` live (Supabase MCP), verified — all 25 rows match §5.
Corrected 6 mis-mapped legacy rows (cloze_completion→meaning_recall, definition_match→form_recognition,
jumbled_sentence→form_production, listening_flashcard→form_recognition, spot_incorrect_sentence +
spot_incorrect_part→semantic_discrimination — fixes finding G4 family mis-drilling). Inserted the 12 new type_codes
(`cloze_typed`, `classifier_match`, `particle_selection`, `counter_match`, `hanzi_to_pinyin`, `kanji_to_reading`,
`pinyin_to_hanzi`, `reading_to_kanji`, `tone_id_word`, `synonym_antonym_match`, `word_family`, `timed_speed_round`)
with §5 families + expected_seconds (readings/tone 15s, speed-round 8s, rest 45s). **DB-vs-spec resolution:** the live
`dim_exercise_types_family_check` forbade §5's `fluency` family (timed_speed_round), so the constraint was additively
extended to include it — safe, `fluency` is non-BKT (no `FAMILY_WEIGHTS` entry → never feeds p_known/coverage). The
constraint was first defined in `phase12_dim_exercise_types.sql` (kept as the table's canonical record; the new file is
the newest definer of that one constraint). Idempotent (keyed UPDATEs + DROP IF EXISTS/re-ADD + ON CONFLICT DO
NOTHING). No code/tests touched. Done 18→19, Not Started 63→62. Next: TASK-504 (the `dim_exercise_capabilities` routing
matrix — depends on 502+503, both now done). Pages updated: [[tasklist/exercise-generation-v2]], [[tasklist/master]],
this log.

## 2026-06-13 change | TASK-502 done — semantic_class 6-value enum ratified + migrated

Phase-0 foundation. Applied `migrations/semantic_class_enum.sql` live (Supabase MCP): remapped the 11 legacy
non-null rows (`abstract_noun→abstract`×4, `action_verb→action`×4, `adjective→property`×2, `具体名词→concrete`×1)
and added a `CHECK` constraint pinning `dim_vocabulary.semantic_class` to the ratified set
`{concrete, abstract, action, property, function, proper}` (NULL still allowed until the TASK-507 backfill). Verified:
distribution correct, constraint def present, a bogus UPDATE is rejected (`check_violation`). Rewired
`services/vocabulary_ladder/config.py` — `compute_active_levels` now routes off the 6-value enum (`proper`→[] not
subscribed; `function`→[1,2,3,6,7]; `concrete`→drop collocation L5/L8 but **keep L4** for the capability-matrix
classifier/counter routing; abstract/action/property→full ladder), `LANGUAGE_VALIDATION_PROFILES` key on a single
language-neutral `SEMANTIC_CLASSES`, and the legacy `COLLOCATION_SKIP_CLASSES`/`MORPHOLOGY_LEVELS`/
`NO_MORPHOLOGY_LANGUAGES`/`_SEMANTIC_CLASSES_EN/ZH` constants deleted. **Guardrail:** P1 prompts still emit old labels,
which would now violate the constraint, so added `normalize_semantic_class()` and applied it at the
`asset_pipeline` write boundary + the active_levels read — legacy labels map to the ratified enum (unknown→NULL), so
generation stays safe until the P1 prompts are reseeded. Tests: new `tests/test_active_levels_routing.py` (full routing
matrix + normalizer); existing validator fixtures moved to ratified values. Suite **498 passed, 1 skipped**. Done
17→18, Not Started 64→63. Next: TASK-503 (fix `dim_exercise_types.family` + add the 12 new type rows). Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-12 change | TASK-501 done — working tree verified + test suite green

First task of the [[tasklist/exercise-generation-v2]] execution. The 2026-06-10 judge/slug tree was **already
committed** before this session (`fcd1fd22` judge integration, `9c1e5fc9` cloze + judge prompting), so TASK-501
reduced to verification + cleanup. Verified live DB: 0 active `google/gemini-flash-1.5` rows, EN
`exercise_sentence_generation` row present; both migrations (`fix_exercise_generation_slugs_and_templates.sql`,
`improve_semantic_discrimination_prompts.sql`) tracked. Fixed **two stale committed tests** that were red:
`test_difficulty_frequency.py::test_tier_still_dominates` (obsolete CEFR keys `A1`/`C2` → `T1`/`T6`; `TIER_NUMERIC`
is T-tier-only post the CEFR→tier migration) and `test_cloze_generator.py::test_judge_rejects_one_retry_succeeds`
(asserted old wholesale-replace; `cloze.py` now POOLs judge survivors across batches). Git history confirms both
fixes follow shipped code, not the reverse. Cleaned the tree: untracked 103 already-committed `.pyc` files (covered by
the existing `__pycache__/` gitignore) and removed the stray 0-byte tracked `and` file. Suite: **457 passed, 1
skipped**. Done: 16→17, Not Started 65→64. Next: TASK-502 (semantic_class 6-value enum migration). Pages updated:
[[tasklist/exercise-generation-v2]], [[tasklist/master]], this log.

## 2026-06-11 tasklist | Exercise Generation v2 (TASK-501–536) — plan only

Converted [[features/exercise-generation-v2]] into [[tasklist/exercise-generation-v2.tasks]] — **36 tasks, no code
written**, IDs map 1:1 to the plan's deliverables (TASK-501 = P0.1 … TASK-536 = P4.3). Phase 0 (501–511) is mostly
parallelisable foundation work (commit pending tree, semantic_class enum + backfill, family-map fix, capability
matrix, JA bootstrap + prompt seeds, pronunciation/register enrichment, trad-ZH dual-store groundwork, slug-health
cron, generation_queue). **TASK-515 (top-1,000 senses × EN/ZH/JA batch run) is the integration gate** — depends on
504–511 + 513/514/519. Phases 2–3 (520–533) fan out after it; Phase 4 (534–536) marked `[?]` blocked on post-launch
attempt data. Master summary: Not Started 32→65, Blocked 1→4. Pages created: 1. Pages updated: [[tasklist/master]],
[[index]], this log. Awaiting operator review of the decomposition before work starts.

## 2026-06-11 update | Exercise-generation v2 plan — revision 2 with operator decisions

[[features/exercise-generation-v2]] rewritten after the operator answered all 13 open questions: **single ladder
factory** (legacy `exercise_generation` frozen for grammar/conversation/style; transcript mining folds into P1 as a
judged sentence source), **JA now**, **top-1,000 senses/language** first batch, **nl=EN with multi-nl coming**
(`content.nl` keyed maps from day one), **Traditional Chinese in scope** (serve-time OpenCC + `lemma_traditional` +
override table + user toggle — mechanism/scope still pending confirmation), **`cloze_typed` graded by exact/normalised
match** (no LLM), **semantic_class 6-value enum ratified** (concrete/abstract/action/property/function/proper) before
backfill, sense-less conversation exercises deferred, **no L10 capstone** (p_known cap ≈0.92 accepted), **JA counter
drill as classifier-drill clone**, no handwriting, no EN stress/homophone audio, **JA keigo `register` column** on
dim_word_senses. Roadmap deliverables now numbered (P0.1–P4.3) for task-list conversion.

**Revision 3 (same session):** final 4 decisions — trad-ZH **dual-store** (`content.hant` mirror at generation, zero
serve-time conversion), scope = practice/vocab first, JA seeded **transcripts only**, **nl-keyed content maps** from
batch 1. **All open questions resolved; brief ready for task-list decomposition.** Pages updated: 1 + this log.

## 2026-06-11 plan | Vocabulary exercise generation pipeline — v2 design plan

Full discovery (wiki + live Supabase) → engineering brief filed at [[features/exercise-generation-v2]]. Pages created: 1.
Pages updated: [[index]], this log. No code or DB changes.

**Key live-DB findings driving the plan:** platform is pre-launch (11 users, 0 ladder/BKT/FSRS/attempt rows — schema
changes are cheap *now*); ladder asset coverage ≈ 0.1% (9 EN + 3 ZH senses in `word_assets` vs ~17.5k senses); **JA has
zero vocab rows** despite 82 JA tests + pitch-accent trainer (extraction never ran; no JA ladder prompts/judges; JA cloze
row inactive); enrichment fields ~empty (`pronunciation`/`morphological_forms` ≈0%, `semantic_class` ≈0% → `active_levels`
POS routing is effectively off); live `dim_exercise_types.family` mis-maps legacy types (cloze→collocation,
jumbled→collocation, listening_flashcard→meaning_recall) so Acquisition family-targeting mis-drills; 7,235 EN
conversation-source exercises are sense-less (dark under ADR-012); `corpus_collocations` = 40 ZH rows, 0 validated.
Also confirmed: practice-merger objects (`get_practice_session`, `dim_practice_modes`, `dim_exercise_types`) ARE live —
[[features/practice-engine]] status `planned` is stale; and the 2026-06-09 slug-fix migration was applied
(EN→gemini-3.5-flash, ZH/JA→qwen3.7-plus; JA tl_nl/nl_tl seeded).

**Plan spine:** consolidate to ONE vocab factory (`vocabulary_ladder` pipeline; legacy `exercise_generation` keeps
grammar/conversation/style only); new `dim_exercise_capabilities` (language × type × POS routing matrix) +
`generation_queue`; 20-type taxonomy (incl. new JA `particle_selection`, kanji↔reading, ZH per-word tone/reading,
`classifier_match` as ladder L4 reusing the drill dictionary, `cloze_typed`, `synonym_antonym_match`, `word_family`);
judges mandatory + fail-closed in batch; nightly model-slug health probe; IRT difficulty priors from frequency_rank.
Roadmap: P0 data foundation (family-map fix, JA vocab bootstrap, pronunciation/semantic_class backfills, JA prompt
seeds) → P1 consolidation + top-1,000-senses/language batch → P2 quality (prompt split, sense embeddings, collocation
grounding) → P3 CJK depth → P4 adaptive. 4 blocking questions for the operator (consolidation scope, JA now-vs-later,
batch budget, nl=EN assumption) in the page frontmatter.

**Note:** the 2026-06-10 session's pipeline repairs (judge integration, language-aware templates, tl/nl skip) are still
uncommitted in the working tree — committing them is the first Phase-0 item.

## 2026-06-09 eval | exercise pipeline (planned 20 EN + 20 ZH; ran 10 EN, ZH aborted)

End-to-end evaluation of the **`services/exercise_generation`** vocabulary pipeline (the legacy VOCABULARY_DISTRIBUTION
pipeline via `run_vocabulary_batch` → `ExerciseGenerationOrchestrator`; **not** `vocabulary_ladder`). Full report:
[[evaluations/exercise-pipeline-eval-2026-06-09]]. Pages created: 1. Pages updated: [[index]], this log.

**Headline:** the pipeline is **dead on arrival as configured** — `_load_models` raised on all 20/20 senses (EN missing
`exercise_sentence_generation` row; ZH `cloze_distractor_generation` inactive), and its configured model
`google/gemini-flash-1.5` is **404-delisted on OpenRouter** (same rot class as the qwen-max outage, different pipeline;
0 logged calls in 21+ days). Per operator decision, templates were **temporarily** re-pointed at live slugs
(EN `google/gemini-2.5-flash-lite`, ZH `qwen/qwen3.7-plus`), run, then **fully reverted & verified** (ids 147/40/39
restored to `google/gemini-flash-1.5` + original active flags; inserted EN row id=179 deleted).

**Run:** 10 EN senses (27838,13895,14072,28016,14347,28652,14556,29140,27846,28106) → **160 exercises** (full 16/16
distribution, 0 shortfall, audio on). ZH **aborted** — `qwen/qwen3.7-plus` upstream 429 rate-limit; killed to cap cost;
0 ZH exercises (Chinese hanzi/pinyin/audio-confusable checks unmeasured). 10 batch_ids captured. Run window
2026-06-09T06:44:16Z.

**Independent grade (160 EN):** 59% accept / 14% flag / 27% reject. text_flashcard 90%, listening_flashcard 90%,
cloze 80% (abstract lemmas 100%, concrete "bean" 0–20%), **tl_nl_translation 0%** (degenerate: tl==nl==en, tense-only
options), **semantic_discrimination 0%** (mislabels valid English as "wrong" for polysemous words; gibberish distractors
for concrete words). Judge layer: only `cloze_distractor_judge` fired (live, healthy) but its rejections **don't remove
shipped distractors** (32 rejected across 18 items, all 50 cloze still ship 4 options); no judge at all on
tl_nl/semantic/flashcards; `judge_verdict`/`judge_confidence`/`cost_usd` never populated; gen calls log as
`task_name='unknown'`. Pipeline ships ~100% → ~41pp leniency gap vs independent.

**Cleanup:** all 160 generated rows DELETED (verified count(*)=0 for the 10 batch_ids); no rows touched outside captured
batch_ids; `llm_calls` left intact (audit trail). **Residual:** 30 listening_flashcard TTS mp3s on
`audio.linguadojo.com` are not removed by batch-delete (storage artifacts left in place, as noted).

## 2026-06-09 debug | Chinese exercise-gen outage — dead `qwen/qwen-max` slug repointed to `qwen/qwen3.7-plus`

**Symptom:** asset pipeline for sense 34995 returned `status: partial` with 4 blocking errors (Prompt 2 + Prompt 3, variants A/B). Logs showed repeated OpenRouter `404 — No endpoints found for qwen/qwen-max`.

**Root cause (not a code bug):** OpenRouter delisted `qwen/qwen-max`. All zh (`language_id=1`) `prompt_templates` rows pointing at it 404'd. `vocab_prompt1_core` survived only because it was already on `qwen/qwen-2.5-72b-instruct`. Prompt 2 (exercises) + Prompt 3 (transforms) are blocking → partial render (the 2 exercises that rendered came from the surviving P1 asset + distractors). The 4 ladder judges also ran on `qwen/qwen-max`, so they were **silently failing open (accept-all)** — zh exercises were getting zero judge filtering even when generation worked. lang 2 was unaffected (already on `anthropic/claude-opus-4-7` + `google/gemini-2.5-flash-lite`).

**Fix (applied live to `kpfqrjtfxmujzolwsvdq` via Supabase MCP):** `UPDATE prompt_templates SET model='qwen/qwen3.7-plus' WHERE language_id=1 AND is_active AND model='qwen/qwen-max'` — 6 rows: `vocab_prompt2_exercises`, `vocab_prompt3_transforms`, `ladder_p1_sentence_judge`, `ladder_l1_distractor_judge`, `ladder_collocation_judge`, `ladder_sentence_validity_judge`. Slug choice per user; `qwen/qwen3.7-plus` confirmed present in OpenRouter's live `/models` list (1M ctx, added 2026-06-03).

**Outstanding (not yet actioned):**
- **Re-seed risk** — the historical seed migrations still hardcode `qwen/qwen-max` and would reintroduce the bug on a fresh-DB rebuild: `migrations/seed_chinese_vocab_prompts.sql` (L239, L328), `migrations/seed_ladder_judge_prompts.sql` (L118, L205, L306, L403), `migrations/cloze_distractor_quality.sql` (L196 — a cloze distractor prompt, *not* among the 6 fixed; needs review for whether it's still 404ing). Fix should be a forward migration, not an edit to applied seeds.
- **Backfill** — sense 34995 (and any other zh senses generated during the outage) are missing P2/P3 assets and were never judge-filtered; re-run generation.
- **Stale docs** — `wiki/features/exercise-generation-prompts.md` (L65–66, L496) + several `Project Knowledge/*` pages still list `qwen-max`.

## 2026-06-09 change | Ladder Judge Layer — seed applied + 4.3 observability shipped (TASK-414→416); Phase 4 complete

Final slice of [[tasklist/ladder-judge-layer.tasks]]. **Migrations applied to the live DB** (project `kpfqrjtfxmujzolwsvdq`) via Supabase MCP, then verified by query: `seed_ladder_judge_prompts.sql` — 8 active rows (p1/l1/collocation/sentence_validity × en `google/gemini-2.5-flash-lite` + zh `qwen/qwen-max`, all `openrouter`, v1, Likert schema), and `phase15_word_assets_validation_warnings.sql` (the `word_assets.validation_warnings text[]` column TASK-404 writes to — was not yet live; now added). All four judges now act for real instead of failing open.

- **TASK-414** — new `migrations/phase16_ladder_judge_reject_rates.sql`: read-only view `v_ladder_judge_reject_rates`, one row per `(language_id, ladder_level, prompt_version, judge_key)` with `exercises_n / rejected_n / kept_n / items_n / reject_rate`. Reads the four `exercises.tags.<judge>_judge.{rejected,kept}` keys joined to `word_assets.prompt_version` via `exercises.word_asset_id`, plus the P1 `validation_warnings` sidecar (judged-asset detection via the `P1 sentence[` marker; clean all-accept assets leave no marker so P1 rate is an upper bound). Applied live; aggregation math validated against synthetic rows (L5/L8 correctly separated by level despite sharing `collocation_judge`); brand-new view (no archive needed per migrations/CLAUDE.md).
- **TASK-415** — `routes/admin_local.py`: read-only page `/admin/judge-reject-rates` + JSON `/admin/api/vocab/judge-reject-rates`, both via new `_fetch_judge_reject_rates()` (queries the view, worst-rate first). New `templates/judge_reject_rates.html` — sortable table (language × level × prompt_version × judge) with reject-rate pills flagged amber ≥15% / red ≥30%, language + judge filters. No mutations.
- **TASK-416** — `tests/test_vocab_ladder_judges.py`: end-to-end `test_integration_all_judges_drop_planted_defects` drives the real `build_rows` + the real P1 pipeline path (only each judge's `call_llm`/`get_template_config` mocked) over one fixture sense with five planted defects — synonym L1 distractor, also-valid L5 collocate, genuinely-correct L8 error word, mislabeled L6 sentence, off-sense P1 sentence — and asserts each is dropped (L7/L8 variants skipped; L1/L5/L6 keep + write `tags.<judge>_judge`) and the P1 warning sidecar names the bad index. Smoke query documented in [[features/exercise-generation-prompts]] (new "Ladder judge layer (Phase 4)" section), filtering `llm_calls.task_name LIKE 'judge_ladder_%'` — note the prefix swap: `prompt_templates.task_name` is `ladder_*_judge` but the logged label is `judge_ladder_*`.

**Verified** — full judge suite **32/32 green** via `rtk proxy python -m pytest`; `routes/admin_local.py` compiles. **Phase 4 is complete**: all 16 tasks done (TASK-401→416).

## 2026-06-08 change | Ladder Judge Layer — sentence-validity chain shipped (TASK-411→413)

Fourth slice of [[tasklist/ladder-judge-layer.tasks]] (Phase 4.1, sentence-validity — verdict per crafted-wrong sentence; serves L6 + L7). Built Likert-first per the new decision 7. **Verified** — full judge suite 31/31 green (10 P1 + 5 L1 + 8 collocation + 8 sentence-validity); modified renderer + module AST-clean.

- **TASK-411** — new `services/exercise_generation/judges/sentence_validity.py`. `judge_wrong_sentences(db, target, sentences_with_reasons, language_id) -> list[JudgeOutcome]`, one per (sentence, labeled-reason) pair, order-aligned (mirrors the P1 verdict shape). Rules "wrong ONLY for the labeled reason": rating 5 = cleanly wrong as labeled (accept/keep), 2 = wrong for a *different* reason (mislabeled → reject), 1 = actually acceptable (reject). 5-pt Likert via `likert_to_verdict`; fail-open to safe-accept-all; logs worst verdict.
- **TASK-412** — appended en (gemini-2.5-flash-lite) + zh (qwen-max) `ladder_sentence_validity_judge` rows to `migrations/seed_ladder_judge_prompts.sql`. Output schema `{"<idx>": {"rating":1-5,"reason":...}}`. zh prompt covers the L6 error taxonomy (量词/体标/语序/方向补语).
- **TASK-413** — wired L6 (`_render_semantic_discrimination`: judge the 3 `wrong_sentences` paired with their explanations, drop rejects, skip variant if `<3` survive) and L7 (`_render_spot_incorrect`: judge the single `incorrect_sentence` against `error_description`, return `None` on reject). Both attach `__judge_metas['sentence_validity']` → `tags.sentence_validity_judge`.

**Still not applied:** `seed_ladder_judge_prompts.sql` now holds 8 rows (p1 + l1 + collocation + sentence_validity, en+zh) — all using the 5-pt Likert schema. Per this session's decision, the full seed is applied via Supabase MCP in one pass after all judges are built; until then every judge fails open.

**All four judge chains (4.1 + 4.2) are now built.** Remaining: TASK-414 (reject-rate view), TASK-415 (admin dashboard), TASK-416 (integration test + smoke query) — the 4.3 observability layer.

## 2026-06-08 change | Ladder Judge Layer — collocation chain shipped (TASK-408→410)

Third slice of [[tasklist/ladder-judge-layer.tasks]] (Phase 4.1, collocation — one prompt, two call sites per decision 3). **Verified** — full judge suite 23/23 green (10 P1 + 5 L1 + 8 collocation); modified modules AST-clean; no other test references the changed renderers/hack.

- **TASK-408** — new `services/exercise_generation/judges/collocation.py`. Shared `_judge_candidates` over one prompt; two public entry points: `filter_collocation_distractors(...) -> (kept, judge_meta)` (L5 filter — drop distractors that are themselves valid collocates) and `judge_collocation_repair(...) -> JudgeOutcome` (L8 verdict — accept only when `error_collocate` is a genuine non-collocate). Confidence is a **5-point Likert `rating`** (decision 7 / memory [[distractor-judge-v3-likert]]) mapped via `schemas.likert_to_verdict`: rating 5 = clearly a non-collocate (ideal wrong-answer) → accept; 1 = idiomatic also-correct collocate → reject. L8 carries the raw rating as `JudgeOutcome.confidence`; L5 keeps a distractor unless its verdict is `reject`. Fail-open both paths (`ok=False` → keep-all / safe_accept).
- **TASK-409** — appended en (gemini-2.5-flash-lite) + zh (qwen-max) `ladder_collocation_judge` rows to `migrations/seed_ladder_judge_prompts.sql`. One question — "is CANDIDATE a genuine non-collocate of TARGET here, or could it pass as a valid collocate?" — serving both call sites. Output schema `{"<idx>": {"verdict":"non_collocate|valid_collocate","confidence":0-1,"reason":...}}`. zh prompt covers 量词/体标/固定搭配凝固性.
- **TASK-410** — wired L5 (`_render_collocation_gap`: filter distractors, skip variant if `<3` survive, attach `__judge_metas['collocation']`) and L8 (`_render_collocation_repair`: `judge_collocation_repair`, return `None` on reject, attach verdict meta). **Removed** the `_l8_correctness_ok` string-match retry/drop block AND the now-dead method in `asset_generators/prompt3_transforms.py`; kept the structural `_can_generate_l8` pre-gate.

**Still not applied:** `seed_ladder_judge_prompts.sql` now holds 6 rows (p1 + l1 + collocation, en+zh). Per this session's decision, the full seed is applied via Supabase MCP in one pass after all judges are built; until then every judge fails open.

**Next:** TASK-411→413 (sentence-validity, L6/L7), then 414→416 (reject-rate view + admin dashboard + integration test).

## 2026-06-08 change | Ladder Judge Layer — L1 distractor chain shipped (TASK-405→407)

Second slice of [[tasklist/ladder-judge-layer.tasks]] (Phase 4.1, L1). **Verified** — full judge suite 15/15 green (10 P1 + 5 L1); renderer + module import clean.

- **TASK-405** — new `services/exercise_generation/judges/l1_distractor.py`. `filter_l1_distractors(db, target, distractors, language_id) -> (kept, judge_meta)`, filter shape mirroring `judges/cloze.py`. Polarity per memory [[l1-is-listening]]: rejects non-words, synonyms, and spelling-only look-alikes; keeps only real, audio-confusable distractors. Fail-open (keep-all on any error).
- **TASK-406** — appended en (gemini-2.5-flash-lite) + zh (qwen-max) `ladder_l1_distractor_judge` rows to `migrations/seed_ladder_judge_prompts.sql`. zh prompt encodes 声调混淆 acceptance and rejects 同义词 / 纯形近字 / 完全同音同调字. Output schema `{"<idx>": {"verdict":"keep|reject","reason":...}}`.
- **TASK-407** — wired into `exercise_renderer._render_phonetic`: filters the 3 option distractors, skips the variant if `<3` survive (same contract as L3), shuffles surviving options, attaches `__judge_metas={'l1_distractor': meta}` → `tags.l1_distractor_judge`. Audio TTS now deferred until after the survive check.

**Still not applied:** `seed_ladder_judge_prompts.sql` (now holds 4 rows: p1 + l1, en+zh) must be run against the DB before either judge does anything — until then both fail open.

**Next:** TASK-408→410 (collocation, L5+L8; retires the `_l8_correctness_ok` hack at [prompt3_transforms.py:124-139](../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L124-L139)), 411→413 (sentence-validity L6/L7), 414→416 (reject-rate view + admin + integration test).

## 2026-06-07 change | Ladder Judge Layer — P1 chain shipped (TASK-401→404)

Built the first slice of [[tasklist/ladder-judge-layer.tasks]]: the foundation + the full P1 sentence-judge chain (4.2, the highest-leverage judge). **Verified** — 10 new unit tests + the existing validators suite green; all modified modules import clean.

- **TASK-401** — generalized the renderer judge-meta sidecar. `build_rows` now lifts `__judge_metas={judge_key: meta}` into `tags['<key>_judge']` for any number of judges; the legacy single `__judge_meta` (L3 cloze) still maps to `tags.cloze_judge` unchanged. ([exercise_renderer.py](../services/vocabulary_ladder/exercise_renderer.py))
- **TASK-402** — new `services/exercise_generation/judges/p1_sentences.py`. `judge_p1_sentences(...)` returns one `JudgeOutcome` per sentence (5-pt Likert via `likert_to_verdict`); fail-open on every error path (template/LLM/non-dict/missing-entry/unparseable → safe-accept that sentence).
- **TASK-403** — `migrations/seed_ladder_judge_prompts.sql` seeds en (gemini-2.5-flash-lite) + zh (qwen-max) `ladder_p1_sentence_judge` rows. Output schema `{"<idx>": {"rating":1-5, "reason":...}}` documented in the header; matches the parser.
- **TASK-404** — wired into `VocabAssetPipeline.generate_for_sense` after P1 validation, before the P2/P3 fan-out. **Index-preserving** (decision 4): never deletes/reorders — rejected sentences get one targeted `CoreAssetGenerator.repair_sentences` pass (rewrite-in-place by index), final verdicts persist to `word_assets.validation_warnings`, asset blocked only if acceptable (accept+flag) sentences < `P1_MIN_ACCEPTABLE_SENTENCES` (=6). Tests assert count/order stability, repair-in-place, block threshold, and length-mismatch fail-open.

**Not yet applied:** `seed_ladder_judge_prompts.sql` must be run against the DB before the judge does anything (until then it fails open — no rows → safe-accept all).

**Next:** TASK-405→407 (L1 distractor judge), 408→410 (collocation, retires the L8 hack), 411→413 (sentence-validity), then 414→416 (reject-rate view + admin + integration test).

**Note:** GateGuard's fact-force hook fired on every wiki + code edit this session — heavy friction for routine doc/bookkeeping writes. Consider scoping it off `wiki/**`.

## 2026-06-07 tasklist | Ladder Judge Layer (Phase 4) — plan only

Converted Phase 4 ("Extend the judge layer") into a task breakdown at [[tasklist/ladder-judge-layer.tasks]] — **no code written**, per the user's "just plan it first" instruction. Implements B3.1 + B3.6 of [[reviews/exercise-generation-audit-2026-06-07]].

**16 tasks (TASK-401 — TASK-416)**, en + zh coverage. Four new judges in the existing `judges/` package, all fail-open + DB-driven + logged to `llm_calls`:
- `ladder_p1_sentence_judge` (4.2, highest leverage) — sense/register/whole-sense per P1 sentence; **must preserve sentence indices** (positional refs in `SENTENCE_ASSIGNMENTS_A/B`, `L7_CORRECT_INDICES_A/B`) → flag + one targeted repair + warning sidecar, never delete-in-place.
- `ladder_l1_distractor_judge` (4.1) — filter shape; audio-confusable-only polarity per memory [[l1-is-listening]].
- `ladder_collocation_judge` (4.1) — one prompt, two call sites (L5 filter + L8 verdict); **subsumes/retires** the `_l8_correctness_ok` string-match retry hack ([prompt3_transforms.py:124-139](../services/vocabulary_ladder/asset_generators/prompt3_transforms.py#L124-L139)).
- `ladder_sentence_validity_judge` (4.1) — verdict per wrong-sentence; serves L6 (3) + L7 (1).
Plus 4.3: generalized `tags.<judge>_judge` sidecar (TASK-401, foundation), a `v_ladder_judge_reject_rates` view, and a read-only admin dashboard.

**Key design decisions** captured in the tasklist header: reuse `judges/` contract; two judge shapes (filter vs `JudgeOutcome`); single collocation prompt for L5/L8; P1 index-stability constraint; per-judge tag schema; L1 audio-confusability polarity.

**Sequencing:** 4.2 → 4.1 (3 independent judge chains) → 4.3, all gated behind TASK-401.

**Pages updated:** [[tasklist/master]] (new section + summary 32→48), [[index]] (Task Lists pointer), this log.

**Next:** awaiting go-ahead to build (suggested first slice: TASK-401 then the 402→403→404 P1 chain).

## 2026-06-07 change | Language-aware P1 validation (audit fix 1.1)

Implements step 2 of the sequencing in [[reviews/exercise-generation-audit-2026-06-07]] — the language-aware validator that fixes the 小熊 0-exercise failure (Chinese concrete noun rejected for `< 2 morphological_forms`).

**What changed:** `validate_prompt1` is now keyed on `language_id` via a per-language profile rather than one global gate.

**Files updated: 3**
- `services/vocabulary_ladder/config.py` — Added `LanguageValidationProfile` (frozen dataclass: `min_morphological_forms` default 0, `ipa_required`, `pos_set`, `semantic_class_set`), `LANGUAGE_VALIDATION_PROFILES` (1=zh: min 0 / no IPA / zh enums; 2=en: min 2 / IPA / en enums; 3=ja: permissive), and `get_validation_profile(language_id)` (falls back to merged EN∪zh enums for unconfigured languages). Split the old merged enums into `_POS_EN`/`_POS_ZH`, `_SEMANTIC_CLASSES_EN`/`_SEMANTIC_CLASSES_ZH`, retaining `DEFAULT_POS_SET`/`DEFAULT_SEMANTIC_CLASS_SET` as the union default.
- `services/vocabulary_ladder/validators.py` — Removed class-level `VALID_POS`/`VALID_SEMANTIC_CLASSES`. `validate_prompt1(content, language_id)` now returns `(is_valid, errors, warnings)`; POS/semantic_class validated against the profile's enum set; `morphological_forms` shortfall and missing IPA demoted from blocking errors to **non-blocking warnings** gated by the profile threshold.
- `services/vocabulary_ladder/asset_pipeline.py` — Passes `language_id` into the validator, unpacks the 3-tuple, logs warnings. (Persisting warnings onto the `word_assets` row is deferred to audit fix 1.2.)

**Verified:** English invariant word (`sheep`, no forms/IPA) now valid with 2 warnings; Chinese empty-forms asset valid with 0 warnings; invalid POS still a blocking error.

**Still open from the audit:** non-destructive regen (B1), CJK corpus-extraction `self.db_language_id` typo (B4), L4 config-gate for Chinese concrete nouns (B5), P1 retry/salvage (B6), judge coverage for L5/L6/L7/L8 + P1, warning persistence (1.2).

**Pages updated:** [[features/exercise-generation-prompts]] (validators.py + config.py dependency lines, date), this log.

## 2026-06-07 review | Exercise generation pipeline audit (triggered by 小熊 0-exercise failure)

Admin "generate exercises" for **小熊** (sense 34987, Chinese concrete noun) rendered **0 exercises** with one error: `Expected at least 2 morphological_forms`. Full audit filed at [[reviews/exercise-generation-audit-2026-06-07]].

**Root cause (confirmed against live DB):** language-blind validator contradicting its own prompt. The Chinese P1 prompt (rule 18, [seed_chinese_vocab_prompts.sql](../migrations/seed_chinese_vocab_prompts.sql)) tells the model it may return an empty `morphological_forms` array; the model correctly returned one form (`个`, the measure word). [validators.py:105-107](../services/vocabulary_ladder/validators.py#L105) hard-requires `>= 2` → P1 stored `is_valid=False` → P2/P3 skipped → renderer aborts ("No valid prompt1_core"). The Chinese seed migration ported the POS / semantic-class / non-ASCII-substring validator changes but left the `morphological_forms >= 2` and mandatory-IPA gates English-centric.

**Latent bugs flagged:** (B1) destructive regen — [admin_local.py:1339](../routes/admin_local.py#L1339) deletes exercises *before* the pipeline runs, so any P1 invalidation wipes a previously-good word; (B2) `>= 2` morph-forms also breaks invariant English words (`sheep`, `the`); (B3) mandatory IPA; (B4) `self.db_language_id` typo hardcodes the English LanguageProcessor + `\b` regex for CJK corpus extraction (no Chinese corpus reuse); (B5) L4 not config-gated for concrete Chinese nouns; (B6) P1 has no retry/salvage (P2/P3 do); (B7) opaque admin error.

**Prompting-infra audit (Part B):** judge coverage is asymmetric — comprehension tests run two judges (answer_entailment + distractor_plausibility, [question_generator.py:446](../services/test_generation/agents/question_generator.py#L446)), but the ladder judges only L3 cloze ([exercise_renderer.py:271](../services/vocabulary_ladder/exercise_renderer.py#L271)); L1/L5/L6/L7/L8 distractors ship with structural validation only. Improvement options: extend judges to every LLM-authored level + a P1 sentence judge; split monolith P2/P3 into per-exercise-type prompts (at least L4/L8); a per-language exercise capability matrix; bind output shape to `prompt_version` via JSON schema; add P1 retry/repair.

**Recommended sequencing:** soften morph/IPA gates → language-aware validator (+ fixture matrix: `sheep`/小熊/function-word) → non-destructive regen → judges for L5/L6/L7/L8 + P1 → capability matrix → prompt split → schema gate.

**Code changes:** none (documentation-only audit). **Pages created:** 1 ([[reviews/exercise-generation-audit-2026-06-07]]). **Pages updated:** [index](index.md) (Reviews section + date + page count 72→73), this log.

## 2026-06-07 change | Measure word drill — exclude 个 + build out classifier coverage

个 (the catch-all classifier) is now **never an option** in the measure word drill, and classifier coverage was greatly expanded.

**RPC** ([get_classifier_drill_session.sql](../migrations/get_classifier_drill_session.sql), rewritten in place + applied). Excludes 个 as both answer and distractor (keyed **by hanzi**, since the build regenerates ids); drops 个-only nouns; re-bases distractor grouping on the specific (non-个) answer classifier; `general`-group answers now draw distractors from a common-classifier core pool instead of the polluted general bucket; added `out_difficulty_tier`. Verified: 0 个 in 300 sampled items, always 3 distractors.

**Groups** ([add_classifier_groups.sql](../migrations/add_classifier_groups.sql), applied). +4 distractor groups: `abstract`, `small_round`, `strands`, `sections` (12 → 16).

**Coverage.** Promoted ~20 real measure words out of the tier-4 `general` dumping ground into proper groups (份/种/项/门→abstract, 段/节→sections, 股→strands, 粒→small_round, 副→garments, …) and hand/LLM-curated nouns for the starved ones — previously-thin classifiers (束/锅/群/串/列…) went from 1–9 nouns to 12–43. Curated roster 55 → 75 classifiers; ~361 → ~875 curated pairs (+~1.8k CC-CEDICT). CC-CEDICT was found **exhausted** as a coverage source (its `CL:` ceiling already matched the DB), so a new **offline LLM authoring pipeline** ([services/classifier_curation/](../services/classifier_curation/), qwen via OpenRouter) generates+judges noun/example content into review JSON, merged into the build via [merge_classifier_curation.py](../scripts/merge_classifier_curation.py). The serving path stays LLM-free/deterministic.

**Files:** [get_classifier_drill_session.sql](../migrations/get_classifier_drill_session.sql), [add_classifier_groups.sql](../migrations/add_classifier_groups.sql), [build_classifier_dictionary.py](../scripts/build_classifier_dictionary.py) (loads `approved_curation.json`), new `services/classifier_curation/` + `scripts/generate_classifier_curation.py` + `scripts/merge_classifier_curation.py`, `data/classifier_curation/*.json`. **Pages updated:** [[features/measure-word-trainer]], [[features/measure-word-trainer.tech]]. **Note:** schema.tech / rpcs.tech do not document the classifier tables/RPC (they live in the feature tech page). Minor: `墙→堵` pair skipped (堵 referenced in the curated dict but never defined as a classifier — pre-existing).

## 2026-06-06 change | Part G — drop per-question response_time_ms (comprehension is order-free)

Reverted Part F #4. Comprehension reading/listening tests let the learner answer questions in any order, so a per-question response time has no clean 1→2→3 sequence to attribute time to and is meaningless. Total test time is already captured at attempt grain via `started_at`/`finished_at` → `apply_attempt_timing_and_progress` (Phase 13). The per-question **outcome** capture (`is_correct`, `selected_answer`, `correct_answer`, `is_first_attempt`) is **kept** — it still powers distractor pick-rates and mis-key detection.

**Migration** ([partG](../migrations/partG_qar_drop_response_time.sql), applied + verified). `ALTER TABLE question_attempt_results DROP COLUMN IF EXISTS response_time_ms` + `CREATE OR REPLACE FUNCTION process_test_submission` = the live Part F body minus every response-time bit (the `v_response_time_ms` decl, the temp-table column, the `SELECT … INTO`, the `'response_time_ms'` result key, and the column+value in the QAR INSERT). Strictly subtractive: ELO maths, scoring, idempotency, the nested `BEGIN/EXCEPTION` QAR insert, and the temp-table / raw-`SQLERRM` error+auth surface are unchanged (still the non-CR-04 live body). Verified: column gone, function source clean, and a `BEGIN…ROLLBACK` smoke test still wrote 5 QAR rows with correct / wrong / unanswered→NULL classification. **partG is now canonical for `process_test_submission`; partF stays as canonical definer of the `question_attempt_results` table + RLS (multi-object, not archived).**

**Files:** [partF_question_attempt_results.sql](../migrations/partF_question_attempt_results.sql) (edited in place to final response-time-free state + header note), [routes/tests.py](../routes/tests.py) (`_to_db_response` reverted to the simple `{question_id, selected_answer}` map), [reading_listening.js](../static/js/session/players/reading_listening.js) (removed `responseTimes`/`questionShownAt`/`firstAnswered` state, the `showQuestion()` stamp, the answer-listener timing block, and the `response_time_ms` field in `submitTest()`). **Pages updated:** [[database/schema.tech]] (dropped the `response_time_ms` row + #4 mentions), [[api/rpcs.tech]] (dropped the body note; `Part F #1/#4` → `#1`).

## 2026-06-06 feature | Part F data collection — per-question outcomes + difficulty calibration

Executed Part F #1 + #4 + #2 of the data-collection plan (the content-QA feedback loop; ELO/BKT are already data-satisfied so the value is in catching LLM-generated content bugs, not the rating maths).

**#1/#4 — `question_attempt_results`** ([migration](../migrations/partF_question_attempt_results.sql), applied + verified). New table mirroring `word_quiz_results`: one row per gradable comprehension question per attempt — `(user_id, test_id, question_id, attempt_id, is_correct, selected_answer, correct_answer, is_first_attempt, response_time_ms)`. `process_test_submission` already computed this (`v_question_results`) and discarded it; now it persists it in a nested `BEGIN/EXCEPTION` block (logging can never fail a submission). Powers distractor pick-rates, mis-key detection, per-item p-values. `response_time_ms` (#4) is staged from the responses payload; reading/listening player now captures per-question decision time. RLS own-data+service+admin triple. **Strictly additive: ELO maths/scoring/idempotency unchanged.** End-to-end rolled-back smoke test passed (5 rows, correct/wrong/unanswered→NULL, response times captured).

**#2 — difficulty calibration** ([migration](../migrations/partF_test_difficulty_calibration.sql), applied). Views `v_test_difficulty_calibration` (per-test `seeded_elo` vs empirical `elo_rating`, `elo_error`, `abs_elo_error`) + `v_test_difficulty_calibration_summary` (MAE/bias, headline over the ≥20-attempt cohort) — the inputs to refit `difficulty_scorer.py` weights. Currently 0 rows (no live test has both a `seeded_elo` and attempts yet).

**Skipped (per plan):** #3 abandonment/partial sessions (Medium effort); all IRT-only items (deferred until IRT greenlit).

**Drift found + decision:** the live `process_test_submission` (temp-table staging, `RAISE EXCEPTION` unauthorized, raw `SQLERRM`) does **not** match the repo's `phase14_test_kfactor_decay.sql`, which carried unapplied **CR-04 hardening** (typed `error_code` envelope, `jsonb_to_recordset`, masked `SQLERRM`) that the route + `test_submission_rpc_error_envelope.py` already expect but which never reached live. The 2026-06-06 archive audit had keyed canonicality on `v_test_k_factor`, which doesn't distinguish the two bodies. Per user decision the Part F migration was based on the **live** (non-CR-04) body, strictly additive. `phase14_test_kfactor_decay.sql` archived (CR-04 version parked there + caveat in [archive README](../migrations/archive/README.md)); `partF_question_attempt_results.sql` is now canonical for `process_test_submission`.

**Files:** [routes/tests.py](../routes/tests.py) (`response_time_ms` passthrough), [reading_listening.js](../static/js/session/players/reading_listening.js) (per-question timing). **Pages updated:** [[database/schema.tech]] (new table), [[api/rpcs.tech]] (submit flow). **Not touched:** `db_schema_live.sql` (dated 2026-03-18 snapshot, already stale for this function).

## 2026-05-31 feature | Two-level sense dictionary (simple + standard)

Implemented the planned two-level sense pipeline. `dim_word_senses` gained `definition_level` (simple/standard), `source`, `source_ref`, `gen_confidence`; unique key swapped to `uq_sense_def_level (vocab_id, definition_language_id, definition_level, sense_rank)` + `idx_senses_source` (migrations/add_sense_levels_and_source.sql — applied). The 3-call sense pipeline (selection → generation → validation) collapsed to **one call per word** emitting both levels via numeric-key JSON `{"1"..."6"}` on `deepseek/deepseek-v4-flash` (fallback `qwen/qwen3.6-flash` on invalid JSON only); self-`confidence` retires the `vocab_validation` call. Prompts rewritten to numeric-key, integer-POS, output-language-locked, T1/T2 child register for `simple`, **+ new ja** rows (migrations/rewrite_sense_prompts_two_level.sql, v2 — applied). `get_distractors` + admin sense lookup now filter `definition_level='standard'` (read-path fan-out fix). New `scripts/backfill_senses.py` (resumable/concurrent); inline test-gen passes `prefer_existing=True`.

Dry-run verified on zh + en (monolingual, integer POS, `simple` at child register vs normal `standard`, fresh examples, confidence captured). **Open:** backfill scope (all test vocab vs N high-frequency lemmas/lang) + live idempotency demo pending user confirmation before bulk run. ja has no `dim_vocabulary` rows yet to seed.

**Pages updated:** [[database/schema.tech]] (dim_word_senses columns/constraints + Two-level sense generation section), [[api/rpcs.tech]] (get_distractors note).

## 2026-05-25 adr | ADR-014 — Dedicated batch-service credential

Followed up on the HI-02 fix (`7e074fd3`) that made the `SUPABASE_SERVICE_ROLE_KEY` HTTP bearer-token bypass symmetric across all three auth decorators. Symmetric exposure enlarged the blast radius of the credential (it now governs Postgres-direct RLS bypass + in-process admin client + HTTP identity bypass — three independent planes from one secret), so the existing open question in [[business-rules/auth-and-access]] became more urgent rather than less.

Audited HTTP callers: **none in repo** currently send `SUPABASE_SERVICE_ROLE_KEY` as an `Authorization: Bearer …` header. Every consumer in `scripts/`, `Corpuses/`, `services/corpus/`, `services/device_service.py`, `services/auth_service.py` uses it for direct `supabase.create_client(...)` calls. The HTTP bypass is a latent capability.

Confirmed direction with the user: HTTP batch jobs are planned (so don't remove the bypass entirely), credential should be a separate shared-secret env var (`BATCH_SERVICE_TOKEN`, `hmac.compare_digest`), and the new credential should be scoped to `jwt_required` only — `admin_required` and `tier_required` no longer honour the bypass, which intentionally re-narrows part of the HI-02 symmetric design.

**Pages updated:** [[decisions/ADR-014-batch-service-credential]] (new), [[business-rules/auth-and-access]] (frontmatter open_question marked ANSWERED, prose paragraph rewritten), [[index]] (Decisions section + date stamp).

**Implementation status:** design only. Code changes (env var validation, `_authenticate` swap, decorator short-circuit removal, test updates) are the follow-up PR; ADR-014 contains the full migration sequence and test plan.

## 2026-05-24 fix | CR-03 + CR-04 from code-review-2026-05-24 (TDD: RED 1bbf7e9a → GREEN 8989b0bf)

Hardened the two critical findings flagged in [[reviews/code-review-2026-05-24]] that were tagged as release blockers. Followed the `/ecc:tdd-workflow` skill end-to-end: failing reproducers first, then fix, then verify.

**CR-03 — `AIService.moderate_content` fail-closed contract.**
- [services/ai_service.py](../services/ai_service.py): added `ModerationServiceError(RuntimeError)`. The `except Exception` branch in `moderate_content` now `raise ModerationServiceError(...) from e` instead of returning `{'is_safe': True}`. `logger.error(..., exc_info=True)` preserves the traceback in backend logs.
- [routes/tests.py](../routes/tests.py) `POST /api/tests/moderate`: catches `ModerationServiceError` and returns **HTTP 503** `{"error":"moderation_unavailable","status":"error"}`. The flagged-input audit insert is intentionally skipped on this path so outages don't generate false-positive abuse rows against innocent users.

**CR-04 — generic error envelope across all four submission RPCs.**
- Python (defense-in-depth, [routes/tests.py](../routes/tests.py)): new `_submission_failure_response()` + `_unwrap_rpc_response()` helpers; all four wrappers (`_call_submission_rpc`, `_call_dictation_submission_rpc`, `_call_pinyin_submission_rpc`, `_call_pitch_accent_submission_rpc`) now return `{"error":"submission_failed","error_code":"submission_failed"}` (500) on any `{success:false}` payload, never forwarding upstream `error` (SQLERRM) or `error_detail` (SQLSTATE). Full payload still logged at `ERROR` level for operator visibility. The `submit_test` and `submit_dictation_attempt` fallback branches also stripped their `details=error_msg` echo.
- SQL (root cause): the `EXCEPTION WHEN OTHERS` blocks in [migrations/phase14_test_kfactor_decay.sql](../migrations/phase14_test_kfactor_decay.sql) (`process_test_submission`), [process_dictation_submission.sql](../migrations/process_dictation_submission.sql), [process_pinyin_submission.sql](../migrations/process_pinyin_submission.sql), [process_pitch_accent_submission.sql](../migrations/process_pitch_accent_submission.sql) now `RAISE WARNING 'process_X failed: % (SQLSTATE=%)', SQLERRM, SQLSTATE` for backend logs and return `{'success': false, 'error_code': 'submission_failed', 'sqlstate': SQLSTATE}`. `sqlstate` is the standardized 5-char Postgres class code (e.g. `23505` for unique violation, `40001` for serialization failure), safe to expose — does not reveal table / column / RLS policy names.

**SQL out of scope this pass (follow-up).** The same `error: SQLERRM` pattern still appears in `migrations/listening_lab_rpcs.sql` (×2), `migrations/process_mystery_submission.sql`, `migrations/process_classifier_drill_submission.sql`, `migrations/process_test_submission_v2.sql`, `migrations/process_test_submission_reduced_repeats.sql`, `migrations/phase3_rpc_fixes.sql`, `migrations/wire_volatility_and_exclude_attempted.sql`, and `migrations/elo_functions.sql`. Some are superseded by later versions; others are live and should be swept in a follow-up PR before any new external surface starts calling them.

**Tests added** (all GREEN; 0 regressions in the 317 pre-existing tests):
- [tests/test_ai_service_moderation.py](../tests/test_ai_service_moderation.py) — 7 unit tests against `AIService.moderate_content` with mocked OpenAI client; covers happy path, empty-content guard, and 4 error classes (`APIConnectionError`, `APITimeoutError`, `RateLimitError`, generic `Exception`).
- [tests/test_moderation_route.py](../tests/test_moderation_route.py) — 4 route-level tests via Flask test client; covers 200 safe, 200 flagged + audit, 503 + no audit when service raises, 400 empty.
- [tests/test_submission_rpc_error_envelope.py](../tests/test_submission_rpc_error_envelope.py) — 11 tests across the four wrappers + a route-boundary test on `/api/tests/<slug>/submit` that asserts no SQLERRM substring leaks into the response body.

**Manual verification still required.** The SQL change to the 4 RPCs is covered by unit + route Python tests only. Before / alongside applying the migrations to Supabase, validate the new EXCEPTION envelope by:
1. In a scratch DB / branch, apply the four migration files via the Supabase MCP `apply_migration`.
2. Call `process_test_submission` with a known-bad input — e.g. a non-existent `p_test_id` UUID or a duplicate `p_idempotency_key` — and assert the JSONB returned is `{success:false, error_code:'submission_failed', sqlstate:'...'}` with NO `error`/`error_detail` keys.
3. Check Postgres logs (`get_logs` MCP) for the matching `WARNING:  process_test_submission failed: ... (SQLSTATE=...)` line.
4. Repeat for `process_dictation_submission`, `process_pinyin_submission`, `process_pitch_accent_submission`.

**Out of scope but flagged.** CR-01 (Stripe webhook) and CR-02 (broken `PaymentService.create_payment_intent`) remain unfixed — both blockers for the next paid-tier release. See [[reviews/code-review-2026-05-24]] for full remediation guidance.

**Commits:** `1bbf7e9a` (RED — test reproducers), `8989b0bf` (GREEN — fix). **Pages updated:** [[reviews/code-review-2026-05-24]] (status banner), this log.

## 2026-05-24 review | Python code review of main LinguaLoop backend (post-2026-05-15-audit successor)

Read-only Python code review focused on what shipped since the 2026-05-15 production-code audit: the new `call_llm()` infrastructure (commits df85ebb4 / 7d530fac), batch test-generation pipeline rewrite, Study Plans rollout + destructive wipe (f0afbf2d), test-side K-factor decay (e1f35223 / [migrations/phase14_test_kfactor_decay.sql](../migrations/phase14_test_kfactor_decay.sql)), and APScheduler cron jobs (82764d6b). Files deep-read: ~20. Scope: main app only ([app.py](../app.py), [config.py](../config.py), [routes/](../routes/), [services/](../services/), [middleware/](../middleware/), [utils/](../utils/), [models/](../models/)). Out of scope: `Portal/*`, `Corpuses/*`, frontend, SQL schema depth.

**Headline findings:** 4 CRITICAL / 9 HIGH / 12 MEDIUM / 6 LOW / 5 redundancies. Full report at [[reviews/code-review-2026-05-24]].

**Critical (must address before next paid-tier release):**

1. **CR-01 — Stripe webhook missing.** Verified again this session; [routes/payments.py](../routes/payments.py) only registers `/token-packages` and `/create-intent` — there is no `payment_intent.succeeded` handler anywhere, so paid token purchases never credit the user. The team had already flagged this in [[api/rpcs.tech]] line 286 (*"Stripe webhook is currently NOT registered in `app.py`"*); the gap remains.
2. **CR-02 — `services/payment_service.py::create_payment_intent` is broken.** `package.price_cents` attribute access on the dict-of-dicts that [config.py:179-192](../config.py#L179-L192) provides — would raise `AttributeError` if called. Latent because nothing currently calls it; the live route bypasses the service entirely and does its own `stripe.PaymentIntent.create`. The whole `PaymentService` class is effectively dead code.
3. **CR-03 — `AIService.moderate_content` fails OPEN.** [services/ai_service.py:292-300](../services/ai_service.py#L292-L300) returns `is_safe: True` on any moderation error. OpenAI moderation timeout or rate-limit → all submitted content silently passes.
4. **CR-04 — `process_test_submission` leaks `SQLERRM` to clients.** [migrations/phase14_test_kfactor_decay.sql:349-355](../migrations/phase14_test_kfactor_decay.sql#L349-L355) `EXCEPTION WHEN OTHERS THEN RETURN jsonb_build_object('error', SQLERRM)` — exposes schema internals on error. Pattern likely mirrored in the other three submission RPCs.

**Notable HIGH items:** auth-decorator boilerplate (~70 lines triplicated across `jwt_required` / `admin_required` / `tier_required`); service-role bypass only present on `jwt_required`; `r2_service.upload_from_url` has no `timeout=` and no URL scheme validation (SSRF surface); `_initialize_services` silently leaves `app.supabase=None` on init failure but reports startup success; `_log_llm_call` falls back to anon client when admin is None and silently drops observability at DEBUG level.

**Redundancies worth consolidating:** four near-identical RPC wrappers in [routes/tests.py:677-786](../routes/tests.py#L677-L786) (~80 lines → ~30 via a `_call_rpc` helper); legacy `AIService.generate_audio` parallels the newer `test_generation/agents/audio_synthesizer.py`; duplicated tenacity retry decorators across `llm_service.py` and `ai_service.py`.

**Recon corrections:** the initial Explore-agent pass misreported several file sizes by 10-80× (`middleware/auth.py` 8,344 → actually 166; `utils/question_validator.py` 3,645 → 99; `utils/responses.py` 2,535 → 55; `models/requests.py` 2,261 → 57). The real god modules are [routes/admin_local.py](../routes/admin_local.py) (1,282), [routes/tests.py](../routes/tests.py) (1,281), [services/test_generation/orchestrator.py](../services/test_generation/orchestrator.py) (1,072).

**Pages created:** 1 (this review). **Pages updated:** 2 ([wiki/index.md](index.md), this log). **Code changes:** zero — review is documentation-only.


## 2026-05-22 launch | Study Plans wipe + flag flip + i18n + verification (two schema-accuracy bug fixes)

Executed the pre-launch rollout per plan §11b. Schema + RPCs were already applied to the live DB from a prior session; only the wipe, flag flip, and verification remained. Plus i18n keys for the new Study Plan UI.

**i18n keys** — added 51 keys (`common.nav.study_plan` + 50 `study_plan.*`) across all four locale files: [static/i18n/en.json](../static/i18n/en.json), [es.json](../static/i18n/es.json), [ja.json](../static/i18n/ja.json), [zh.json](../static/i18n/zh.json). [templates/study_plan.html](../templates/study_plan.html) updated to use `data-i18n` for static labels and a `T(key, params)` JS helper for dynamic strings (template buttons, stat tile labels, status messages, week-summary).

**Wipe** — [migrations/phase13_wipe_user_state_for_launch.sql](../migrations/phase13_wipe_user_state_for_launch.sql) ran cleanly via MCP `execute_sql`. Pre-wipe state: ~580 user-state rows across 12 tables (58 test_attempts, 312 user_vocabulary_knowledge, 131 user_flashcards, etc). Post-wipe: all 12 tables at 0. Reference data intact (11 auth.users, 11 public.users, 255 tests, 11225 exercises, 3 dim_languages, 9 dim_study_plan_templates, 3 dim_practice_modes, 13 dim_exercise_types).

**Flag flip** — [config.py](../config.py) `STUDY_PLAN_ENABLED` default flipped `False → True`. Env override (`STUDY_PLAN_ENABLED=false`) still respected for instant rollback without a deploy.

**Verification — two schema bugs found and patched live.** End-to-end smoke test against `auth.users[de6fd05b-…]` exercised `apply_study_plan_template` → `compute_weekly_plan_load_signals` → `compute_weekly_plan_persist` → `build_daily_session` → `get_practice_session`. Two functions referenced columns that don't exist on the live schema:

1. **`compute_weekly_plan_load_signals`** referenced `user_word_ladder.language_id`, `last_exercised_at`, `created_at` — none of which exist. Fix: join via `dim_word_senses → dim_vocabulary.language_id` for filtering; use `updated_at` as the recency proxy; `new_intro_7d` = `updated_at >= now-7d AND total_attempts = 0`. Patched live via `apply_migration` `phase13_compute_weekly_plan_load_signals_v2`. In-repo source updated at [migrations/phase13_compute_weekly_plan_helpers.sql](../migrations/phase13_compute_weekly_plan_helpers.sql) with an `IMPORTANT SCHEMA NOTE` block.

2. **`build_daily_session`** queried `public.tests.test_type_id` for the last-3-days spacing penalty — `tests` has no such column; a single test row can be served as reading/listening/dictation interchangeably, and the type is captured per-attempt on `test_attempts.test_type_id`. Fix: query `test_attempts` directly (better signal anyway — what the user *actually took*, not what was *scheduled*). Patched live via `apply_migration` `phase13_build_daily_session_v2`. In-repo source updated at [migrations/phase13_build_daily_session.sql](../migrations/phase13_build_daily_session.sql).

**Smoke-test results after the two patches:**

| Step | Result |
|---|---|
| `apply_study_plan_template(user, lang=1, template=101)` | row created with `daily_minutes=30, weekday_shape=[1,1,1,1,1,1,1]` ✅ |
| `compute_weekly_plan_load_signals(...)` | jsonb returned with all-zero counts (post-wipe), `user_mean_elo=1200` cold-start default ✅ |
| `compute_weekly_plan_persist(...)` | hand-crafted Tier-B-equivalent payload upserted; returned full row including `skill_values` ✅ |
| `build_daily_session(...)` | produced load_id=1 with 3 hydrated test_ids (pinyin + measure_word + listening), 28 used_minutes within 36.6 upper_cap, `daily_session_targets` jsonb populated ✅ |
| `get_practice_session('auto'|'acquisition'|'maintenance', 10min)` | all 3 returned `no_eligible_words` (correct — user has 0 ladder rows post-wipe; R4.9 cold-ladder auto-subscribe lives in the Python service layer, not the bare RPC). Maintenance also fell through to `mode_resolved='acquisition'` as designed ✅ |

**Deferred bug — known behavior:** the greedy fill in `build_daily_session` ordered by per-minute value tends to fill tests before practice chunks (test slots have value/min ≈ 0.10 vs practice chunks ≈ 0.014). For the cold-start case above, all 28 used minutes went to tests; practice_maintenance_min and practice_acquisition_min both came back 0. Spec-faithful behavior would mix both via the full Tier C objective (`Σ x_s·value(s) + α·m + α·a − γ·spacing`). The Python `services/study_plan_service.py::build_daily_session` could post-process the result to inject practice minutes if telemetry shows this skewing too test-heavy in steady state. Not blocking for V1 launch; the orchestrator is functional and the Practice surface is still reachable via the explicit `/api/practice/session?mode=...` endpoint regardless of resolver output.

**Repo files modified this session:** [config.py](../config.py), [migrations/phase13_compute_weekly_plan_helpers.sql](../migrations/phase13_compute_weekly_plan_helpers.sql), [migrations/phase13_build_daily_session.sql](../migrations/phase13_build_daily_session.sql), [templates/study_plan.html](../templates/study_plan.html), [static/i18n/en.json](../static/i18n/en.json), [es.json](../static/i18n/es.json), [ja.json](../static/i18n/ja.json), [zh.json](../static/i18n/zh.json). Two ad-hoc migrations applied live via MCP: `phase13_compute_weekly_plan_load_signals_v2`, `phase13_build_daily_session_v2`.


## 2026-05-22 revision | Study Plans rollout — backfill replaced with pre-launch wipe (R4.2)

User asked whether the planned backfill ([[tasklist/study-plans.tasks]] TASK-218 — "Backfill SQL — seed user_study_plans for existing users") was necessary, or whether a clean wipe would suffice. The target DB is pre-launch with no real-user history to preserve, so a wipe is both simpler and safer than a partial-seed backfill.

**Change:** Replaced the originally-planned non-destructive `INSERT … ON CONFLICT DO NOTHING` backfill with a one-shot `TRUNCATE … RESTART IDENTITY CASCADE` against all 12 user-state tables.

**New migration:** [migrations/phase13_wipe_user_state_for_launch.sql](../migrations/phase13_wipe_user_state_for_launch.sql) — single TRUNCATE statement, atomic, with a `RAISE NOTICE` that logs the post-wipe row total. Run once before flipping `Config.STUDY_PLAN_ENABLED = True`. Reference data (`dim_*`, content tables, auth) untouched.

**Safety net preserved:** [services/test_service.py::get_or_create_daily_load](../services/test_service.py) already falls through to legacy `_compute_daily_load` for any user without a `user_study_plans` row — so even if the wipe leaves orphan users, they keep functioning until they visit Settings / onboarding to create a plan via `apply_study_plan_template`.

**Pages updated:** [features/study-plans.tech](features/study-plans.tech.md) (migration sequence + rollout sequence + testing strategy), [decisions/ADR-013-global-feature-flag-rollout](decisions/ADR-013-global-feature-flag-rollout.md) (rollout steps 4–5 amended; Consequences rewritten), [tasklist/study-plans.tasks](tasklist/study-plans.tasks.md) (TASK-218 retitled "Wipe user-state tables for launch"; XS complexity), [tasklist/master](tasklist/master.md) (TASK-218 row updated). The original backfill SQL is kept as a collapsible reference-only block in the tech spec for possible future post-launch use.

**Verification (post-implementation, deferred):** Apply the wipe to staging; confirm all 12 tables `COUNT(*) = 0`; confirm reference tables unaffected; sign up a fresh test user, complete onboarding for a 30 min/day Chinese plan, take a test, then confirm `user_study_plans` row exists, `daily_test_loads.daily_session_targets` is non-NULL, and `weekly_plan_states` populates after the first Sunday cron tick.


## 2026-05-21 design | Adaptive Study Plans + Practice Engine Merger — full V1 spec

User requested a doc thorough enough to hand to a development team to implement without further architectural decisions. Four rounds of clarifying questions (24 design decisions resolved) produced the implementation spec at [C:\Users\James\.claude\plans\goal-continue-through-the-parsed-goblet.md](file:///C:/Users/James/.claude/plans/goal-continue-through-the-parsed-goblet.md). Then this session produced the full wiki artifact set documenting the design.

**Two intertwined V1 deliverables:**

- **Practice Engine merger** — `/api/exercises/session` (Daily Mixed) and `/api/vocab-dojo/session` (Vocab Dojo) collapse into one service exposing `get_practice_session(user, language, mode, target_minutes, theta)`. Two modes:
  - **Acquisition** — word-anchored loop using ladder priority to pick a word, then top-K items per required family by unified score (K = ring's required-family count). Gate batteries and stress tests dispatch inline. Auto-subscribes from selected packs if the eligible-word pool is empty.
  - **Maintenance** — batch-anchored over FSRS-due-≤7d OR BKT-decay-flagged senses (LIMIT 200 candidates, hard cap). Ranks by unified score. Falls through to Acquisition if the pool empties before `target_minutes`.
  - Single **unified score** with mode-dependent weights stored in new `dim_practice_modes` table: `score = α·ladder + β·irt_info + γ·bkt_uncertainty + δ·fsrs_urgency`. Per-term normalization fully specified in [[algorithms/practice-unified-score.tech]]. Grammar/style items (`sense_id IS NULL`) excluded V1 per [[decisions/ADR-012-grammar-items-excluded-v1]].
  - `get_exercise_session` / `get_ladder_session` kept as deprecation wrappers for one release. Full ladder mechanics from ADR-005 (rings, families, gates, stress test, demotion, cross-session advancement) preserved verbatim.

- **Study Plan orchestration** — adds two-tier adaptation per `(user_id, language_id)`:
  - **Tier B (weekly, Sun 23:00 UTC cron):** Composite weakness signal (`0.40·elo_gap + 0.25·accuracy_trend + 0.20·ladder_stagnation + 0.15·fsrs_lapse_rate`) plus value-weighted Thompson sampling (Beta(2,2) prior, deterministic seed) allocates weekly test counts across skills clamped to `[⌈target·0.5⌉, ⌈target·1.5⌉]`. Practice minutes rebalance Maintenance/Acquisition split (bounded `[0.15, 0.50] / [0.50, 0.85]`) by retention vs learning pressure. Outputs to new `weekly_plan_states` table.
  - **Tier C (lazy daily resolver):** Greedy + local-swap optimizer solves today's mix from `today_budget = total_weekly_minutes · weekday_shape[today] / 7`. Soft cap 1.5× notional; spacing penalty `0.15 · I(s ∈ today) · count_in_last_3d(s)/3`. Writes test slots to existing `daily_test_loads` plus new column `daily_session_targets jsonb` carrying Practice maint/acq minutes.
  - Per-language independent plans ([[decisions/ADR-011-per-language-independent-budgets]]); Goals deferred to V2 (schema hook present); shared UTC cron in V1 (`user_study_plans.timezone` column present for V2). Single global `Config.STUDY_PLAN_ENABLED` flag for rollout ([[decisions/ADR-013-global-feature-flag-rollout]]); rollback = toggle Config.

**Schema** — 6 new tables (`dim_exercise_types`, `dim_practice_modes`, `dim_study_plan_templates`, `dim_study_goals`, `user_study_plans`, `weekly_plan_states`); 4 new columns on existing tables (`test_attempts.started_at`, `test_attempts.duration_ms`, `daily_test_loads.daily_session_targets`, `user_exercise_sessions.mode`, `user_exercise_sessions.target_minutes`, `dim_test_types.expected_minutes_p50`).

**RPCs** — 5 new: `get_practice_session`, `practice_unified_score` (helper), `apply_study_plan_template`, `compute_weekly_plan`, `build_daily_session`, `record_session_progress`. Modified: `process_test_submission` + variants accept `started_at`/`finished_at`. Wrappers: legacy `get_exercise_session` + `get_ladder_session`.

**Cron** — two new jobs join `irt_calibration_nightly` in `app.py:227-251`: `study_plan_weekly_recompute` (Sun 23:00 UTC) and `exercise_time_estimate_refresh` (04:05 UTC). Same advisory-lock pattern.

**Worked example** — User U, Chinese, 45 min/day, week 4, listening ELO 1100. End-to-end trace in [[features/study-plans.tech#worked-example]]: weakness scores per skill, bandit allocation yielding `reading=4, listening=11, dictation=4, pinyin=1, measure_word=1`, Practice rebalance to `maint=51min/acq=64min/wk`, Monday resolve to a concrete 45-min session, then a Practice call producing 11 items across 4 words.

**Pages produced:** 4 new prose + 4 new tech specs (`practice-engine.md/.tech`, `study-plans.md/.tech`, `practice-unified-score.md/.tech`, `study-plan-adaptation.md/.tech`); 7 new ADRs (007–013); 2 new task files (`practice-merger.tasks.md` 12 tasks, `study-plans.tasks.md` 20 tasks); `tasklist/master.md` rewritten; updates to `schema.tech.md`, `database/rpcs.tech.md`, `api/rpcs.tech.md`, `flashcards.md`, `ladder-implementation-analysis.md`, `comprehension-tests.tech.md`, `elo-ranking.md`, `vocabulary-ladder.md`, `vocabulary-knowledge.md`; `exercises.md/.tech` + `vocab-dojo.md/.tech` marked `status: deprecated` with redirect notes (content preserved); `wiki/index.md` updated.

**Implementation status:** zero. This session shipped documentation only; code implementation is the downstream session (32 tasks across two task files). Rollout sequence + parity test thresholds + monitoring criteria fully specified.


## 2026-05-20 feature | Furigana overlay for Japanese tests (deterministic, fugashi + UniDic)

User asked whether furigana could be added to "low level" Japanese tests deterministically — no LLM. After clarification, the target surfaces were the comprehension test renderer ([templates/test.html](../templates/test.html)) and the pitch accent trainer ([templates/test_pitch_accent.html](../templates/test_pitch_accent.html)); learner-controlled toggle with an ELO dampener while it's on.

**Generator** — new [services/furigana_service.py](../services/furigana_service.py). Tokenizes with fugashi (already used by [services/vocabulary/processors/japanese.py](../services/vocabulary/processors/japanese.py)); reads `feature.kana` from UniDic, converts katakana→hiragana with jaconv. Per-token alignment strips matching kana from both ends of the reading where the surface kana already match, then emits group ruby for the kanji-runs in the middle. Single kanji-run + remaining reading → one segment (handles jukujikun like 今日→きょう correctly). The same generator powers both surfaces.

**Storage** — `tests.furigana_payload JSONB` mirrors the pinyin/pitch payload pattern; computed at test creation in [services/test_service.py](../services/test_service.py) alongside the existing pitch payload. Per-attempt audit on `test_attempts.furigana_used`. New migration [migrations/add_furigana_mode.sql](../migrations/add_furigana_mode.sql).

**Per-user opt-in** uses the existing `users.exercise_preferences` JSONB (key `furigana_enabled`), so no new users column. [routes/users.py](../routes/users.py) gains a `GET /api/users/preferences` endpoint and accepts `furigana_enabled` in `PATCH`.

**ELO dampener** — [migrations/process_test_submission_v2.sql](../migrations/process_test_submission_v2.sql) and [migrations/process_pitch_accent_submission.sql](../migrations/process_pitch_accent_submission.sql) gain a `p_furigana_used BOOLEAN` parameter. When true, the *user-side* K factor is halved (constant `c_furigana_dampener = 0.5`); test K unchanged so display preferences can't move the test's rating. The flag is persisted to the new `test_attempts.furigana_used` column for auditability.

**Frontend** — Sticky-on flag (`furiganaUsedThisAttempt`): once the toggle is flipped on during an attempt it stays "used" through submit, even if the learner flips it off — closes the peek-then-hide loophole. test.html re-renders transcript/question/choices via a `renderJpText(plainText, tokens)` helper. test_pitch_accent.html mutates only `.word-surface` innerHTML in place so mid-drill state (current/completed/cls-*) survives toggling.

**Deps** — added fugashi, unidic-lite, jaconv to [requirements.txt](../requirements.txt). fugashi was already imported in the Japanese vocab processor but not declared; declaring explicitly.

**Pages updated:** [features/furigana-overlay.md](features/furigana-overlay.md), [features/furigana-overlay.tech.md](features/furigana-overlay.tech.md), index.md.

**Verification pending.** Unit tests for the generator, migration application, and end-to-end test attempt with the toggle on/off (confirming ~½ ELO delta on the dampened run) are still to run.


## 2026-05-19 fix | Dictation submission: batched BKT (worker-timeout truncation)

Dictation submissions of 60+ words were producing Chrome's "Content-Length header of network response exceeds response Body" error — the submit handler did one Supabase RPC call per transcript word inside the request loop ([routes/tests.py](../routes/tests.py) `submit_dictation_attempt`), accumulating ~60-120 sequential round-trips and exceeding the gunicorn worker timeout. The worker was killed mid-write, truncating the announced response body.

**Fix** — new RPC [migrations/bkt_word_test_batch.sql](../migrations/bkt_word_test_batch.sql) `update_vocabulary_from_word_tests_batch(p_user_id, p_language_id, p_results jsonb)`. Single set-based UPSERT modelled on the existing batched `update_vocabulary_from_test` (comprehension flow), but for direct sense-level word-test evidence using the stronger `bkt_update_word_test` slip/guess parameters. The Python service ([services/vocabulary/knowledge_service.py](../services/vocabulary/knowledge_service.py) `update_from_word_tests_batch`) wraps the RPC and fires `_auto_create_flashcards` + `_trigger_frequency_inference` once over the batch result, not N times.

The dictation submit handler was rewritten to build a `word_results` list from the diff and call the batched method once. ~60-120 round-trips → 1 (plus the existing flashcard auto-create + sparse frequency-inference downstream calls).

**Behavioral change — BKT correctness fix.** The new RPC dedupes input via `bool_or` (credit as correct if any occurrence was correct). The previous per-word path incremented `word_test_correct`/`word_test_wrong` once per occurrence; a word appearing 3 times in a transcript got 3 independent BKT updates. BKT assumes independent samples — repeated tokens in one submission violate that. One-evidence-per-unique-sense is the correct shape. Documented inline in the migration header.

**Smoke test** confirmed via Supabase MCP: 3 distinct senses + 1 duplicate → 3 rows returned, BKT moved sensibly (0.35→0.69 on correct, 0.05→0.07 on wrong, 0.65→0.88 on correct), `bool_or` dedup credits the repeated sense as correct.

**Verification.** All 34 dictation grader unit tests still pass; import-smoke for the modified files clean. Manual browser submission still pending end-user verification.

**Pages updated:** [database/rpcs.tech.md](database/rpcs.tech.md) (new RPC entry), [features/dictation.tech.md](features/dictation.tech.md) (arch diagram + RPC list + dependencies frontmatter).


## 2026-05-19 change | Measure Word Trainer v2 — mastery, tiers, CC-CEDICT, Reverse + Cloze levels

User request: track per-classifier accuracy/attempts and auto-promote learners from MC → Typed → Reverse → Cloze; gate beginner exposure so 只/个 surface before 枪/壶; expand vocabulary coverage; mine cloze sentences from our own test corpus. Four phases shipped together.

**Phase 1 — Difficulty tiers + dictionary expansion.**
- Migration `add_classifier_difficulty_tier.sql` — added `dim_classifiers.difficulty_tier` (smallint, 1-4) and `dim_classifier_noun_pairs.example_sentence`. Indexed `(language_id, difficulty_tier)`.
- Updated [scripts/build_classifier_dictionary.py](../scripts/build_classifier_dictionary.py) with explicit tier assignments: T1 = 10 core HSK 1-2 classifiers (个/只/条/张/本/辆/杯/件/双/把), T2 = 17 HSK 3-4 (位/名/口/头/匹/棵/朵/座/间/套/场/次/顿/部/群/瓶/所 + new 块/台/家/首), T3 = 18 HSK 5+ (架/艘/列/支/根/束/包/袋/盒/碗/片/面/册/幅/枚/颗/串/阵/壶/锅), T4 = 4 advanced (栋/盆/瓣/则). Expanded NOUN_CLASSIFIERS from 207 to 243 lemmas (361 pairs).
- New [scripts/import_cedict_classifiers.py](../scripts/import_cedict_classifiers.py) — downloads `cedict_ts.u8` (5MB, CC-BY-SA 3.0) from MDBG if absent, parses every `CL:X[pin],Y[pin]/` annotation. Preserves curated rows (skips on `source='curated'` collision), inserts long-tail with `source='cedict'`. Inserted **1894** new noun-classifier pairs. Caveat: the first run had reversed-column parsing (CC-CEDICT writes TRADITIONAL first); fixed and re-imported. A subsequent SQL cleanup migration (`classifier_traditional_to_simplified_cleanup`) merged 13 traditional-form classifier rows into their simplified counterparts and renamed 15 traditional-only rows to simplified forms (盞→盏, 盤→盘, 種→种, etc.). Final state: **174 classifiers, 2255 pairs (361 curated + 1894 cedict)**.

**Phase 2 — Per-classifier BKT-style mastery + tiered serving.**
- Migration `create_user_classifier_mastery.sql` — new table `user_classifier_mastery (user_id, classifier_id, attempts, correct, ewma_accuracy, current_level, last_wrong_streak, promoted_at, last_attempted_at)` with PK `(user_id, classifier_id)`.
- New RPC `update_classifier_mastery(p_user_id, p_classifier_id, p_is_correct)` — upserts the row, updates EWMA with α=0.3, **promotes** on `attempts ≥ 5 AND ewma ≥ 0.80`, **demotes** on `last_wrong_streak ≥ 3`. Returns `{promoted, demoted, current_level, old_level, ewma, ...}`.
- New helper `max_unlocked_tier(user_id, language_id)` — Tier 1 always unlocked; Tier N+1 unlocks once ≥80% of Tier N classifiers have `current_level ≥ 2`.
- Rewrote `get_classifier_drill_session` (v2 → v5):
  - Restricts the sampled pool to classifiers with `difficulty_tier ≤ max_unlocked_tier(user)` so beginners only see 只/条/张/本/辆/杯/件/双/把/个.
  - Returns per-item `out_level` (the user's classifier-specific level), `out_difficulty_tier`, `out_classifier_id_primary`, and reverse-mode/cloze payloads.
  - When `user_level = 4` but no mined sentence exists for `(classifier, noun)`, the RPC silently downgrades the item to level 3 so cloze never blanks-out without content.
- Extended `services/classifier_drill_service.py` `submit_session()` to accept an `item_results: [{classifier_id, is_correct}]` array and call `update_classifier_mastery` per item (best-effort; failures don't fail the session). Returns `mastery_updates` in the envelope so the client can badge promotions/demotions.

**Phase 3 — Tri-state toggle, per-item level rendering, auto-focus.**
- Mode toggle in [templates/classifier_drill.html](../templates/classifier_drill.html) is now `[ Auto | Choose | Type ]` (default Auto, persists in `localStorage.cd_mode`). Auto picks each item's level from the RPC; manual modes globally pin Choose or Type.
- Per-item dispatch: `effectiveLevelForItem()` returns 1=MC / 2=Typed / 3=Reverse / 4=Cloze. The renderer branches accordingly:
  - **Reverse (level 3):** prompt shows `一 X ?`, learner picks the correct *noun* from 4 options (1 correct + 3 nouns sampled from other distractor groups via the new `out_reverse_noun_options` column).
  - **Cloze (level 4):** prompt shows the mined sentence with `___` blanked, learner picks the missing classifier from 4 options.
- Auto-focus: typed input now focuses on every render via `requestAnimationFrame(() => el.typedInput.focus())` so the cursor is always ready.
- Level badge in header (visible only in Auto mode) reads `· MC` / `· Type` / `· Reverse` / `· Cloze` so promotions are transparent.
- Submit payload now includes `item_results[]`; results screen renders promotion/demotion banners when `mastery_updates` contains any `promoted` or `demoted` entries.

**Phase 4 — Cloze sentence mining.**
- Migration `create_classifier_example_sentences.sql` — new `dim_classifier_example_sentences` table with `(classifier_id, noun_lemma, sentence, blanked_sentence, source_test_id)` and UNIQUE on `(classifier_id, sentence)`.
- New [scripts/mine_classifier_sentences.py](../scripts/mine_classifier_sentences.py) — splits every active Chinese `tests.transcript` on `[。！？]`, walks each ≤80-char sentence, finds `[一二三四五六七八九十百千两这那几多某半另每好0-9]<classifier><1-3 hanzi noun>` patterns, validates against `dim_classifier_noun_pairs`, and emits a `blanked_sentence` with `___` replacing the classifier. Ran across **91 tests, 1431 sentences → 71 hits across 12 classifiers** (个, 杯, 本, 种, etc.).

**i18n.** 24 new keys × 4 locales added to [static/i18n/{en,zh,ja,es}.json](../static/i18n/) (`classifier_drill.mode_auto`, `classifier_drill.reverse_prompt`, `classifier_drill.promoted_n`, `classifier_drill.demoted_n`, `classifier_drill.cloze_prompt`, plus the original 19). All four locales now contain exactly **374 keys**.

**Verification (in repo + remote).**
- `python -m py_compile app.py routes/classifier_drill.py services/classifier_drill_service.py scripts/build_classifier_dictionary.py scripts/import_cedict_classifiers.py scripts/mine_classifier_sentences.py` — all parse.
- Locale parity confirmed: `{en: 374, zh: 374, ja: 374, es: 374}`.
- Session RPC smoke: `get_classifier_drill_session(<uuid>, 1, 12)` returns mixed-level items when the user has mastery rows (Reverse and Cloze items appear for promoted classifiers); always level=1 when there are no mastery rows (beginner experience).
- Cloze JOIN smoke: `(咖啡, 杯)` → mined sentence `"虽然价格会受到天气、运输成本等因素影响，但人们还是愿意为一___咖啡付出费用"`.
- Smoke-test mastery rows cleaned up post-verification so user starts fresh.

**Out of scope (deferred):**
- Production level (number + gloss → full phrase) — decided against per planning interview (multi-language gloss generation overhead doesn't justify the marginal pedagogical benefit beyond the four shipped levels).
- Per-pack noun filtering of the session pool.
- Per-noun TTS playback (schema fields exist; audio URL surfacing deferred).
- Anti-repetition across rounds (Phase 5 candidate).
- Cloze pool currently 71 sentences / 12 classifiers — will grow naturally as new Chinese tests are generated; the mining script is idempotent and safe to re-run.

Pages updated: 1 (log.md). Wiki feature/tech pages will be refreshed in a follow-up sweep.

## 2026-05-17 change | Measure Word Trainer (classifier_drill) for Chinese

User request: build an *infinite* training tool for Chinese measure words (一只猫 / 一条狗 / 一辆车), promoting the L6/L7 `量词使用错误` cloze error category to its own first-class drill. Plan at [`C:\Users\James\.claude\plans\plan-out-how-to-moonlit-lynx.md`](../../.claude/plans/plan-out-how-to-moonlit-lynx.md). Locked design choices via /plan interview: curated dictionary with no LLM, MC + Typed runtime toggle, leave cloze prompts untouched (additive), Chinese-only (Japanese counters deferred).

**Database (3 migrations).**
- New [migrations/add_classifier_drill_mode.sql](../migrations/add_classifier_drill_mode.sql) — registers `dim_test_types('classifier_drill', id=14)`; creates 3 new tables (`dim_classifier_distractor_groups`, `dim_classifiers`, `dim_classifier_noun_pairs`); seeds 12 semantic distractor groups; inserts the sentinel `tests` row `slug='__classifier_drill_zh'` (is_active=false so it never surfaces in listings) plus its `test_skill_ratings` anchor at ELO 1400. Applied to remote.
- New [migrations/get_classifier_drill_session.sql](../migrations/get_classifier_drill_session.sql) — `get_classifier_drill_session(user_id, language_id, count)` returns N drill items. CTE pipeline: pick distinct lemmas weighted by `random()*frequency_score`, expand each to all acceptable classifier IDs (CC-CEDICT-style multi-valid), draw 3 distractors from the same `distractor_group_id` excluding all of the noun's correct answers, top up from `general` group if the primary group has < 3 alternatives. `SECURITY DEFINER`, `STABLE`, GRANTed to authenticated. Applied to remote.
- New [migrations/process_classifier_drill_submission.sql](../migrations/process_classifier_drill_submission.sql) — accuracy-based submission RPC, parameter rename of `process_pinyin_submission` (`p_correct_chars` → `p_correct_items`). Same K=32 first-attempt-only ELO formula, same idempotency block, same JSONB success/error envelope. Applied to remote; a v2 patch removed `percentage` from the INSERT after discovering it's a `GENERATED ALWAYS` column on `test_attempts`.

**Backend.**
- New [services/classifier_drill_service.py](../services/classifier_drill_service.py) — `get_session()`, `submit_session()`, sentinel-id cache.
- New [routes/classifier_drill.py](../routes/classifier_drill.py) — `classifier_drill_bp` blueprint with `GET /api/classifier-drill/session` and `POST /api/classifier-drill/submit`. Both endpoints reject `language_id != 1` in v1.
- [app.py](../app.py) — registered blueprint at `/api/classifier-drill`; added `/classifier-drill` page route.

**Dictionary (no LLM, fully deterministic).**
- New [scripts/build_classifier_dictionary.py](../scripts/build_classifier_dictionary.py) — curated dictionary embedded as Python data structures. 40 classifiers across 12 distractor groups (general, people, animals, long_thin, flat, bound, vehicles, containers, places, garments, events, plants), 269 noun-classifier pairs covering HSK 1–4 vocabulary. Idempotent rebuild: wipes and reinserts on every run. Build ran successfully: `Inserted 40 classifiers`, `Inserted 269 noun-classifier pairs`, 78/207 lemmas linked to `dim_word_senses`. 30 pairs were skipped because they reference classifiers not in the curated CLASSIFIERS list (台/幅/块/枚/首/壶/锅/栋/家/阵/串/颗/盆/瓣/则) — these can be added in a future iteration.

**Frontend.**
- New [templates/classifier_drill.html](../templates/classifier_drill.html) — single-file SPA, extends base.html. Header has a `[ Choose | Type ]` toggle that persists in `localStorage.cd_mode`. MC mode: 4 shuffled buttons + keys 1–4. Type mode: single `<input>` accepting any of the noun's correct hanzi. Feedback modal on wrong answer shows `一 <canonical> <noun>` plus the also-acceptable list and the semantic group label. Results screen shows accuracy, time, and an ELO badge from the submission response.
- [templates/base.html](../templates/base.html) — added "Measure Words" entry to both desktop nav and mobile dropdown.
- [templates/profile.html](../templates/profile.html) — added `classifier_drill: '🧮'` to SKILL_ICONS; history rows format as `N/M classifiers`.
- [static/i18n/{en,ja,zh,es}.json](../static/i18n/) — 19 new keys × 4 locales (common.nav.classifier_drill, test_list.classifier_drill, classifier_drill.* namespace). All four locales contain 369 keys.

**Verification (in repo + smoke against remote).**
- `python -m py_compile app.py routes/classifier_drill.py services/classifier_drill_service.py scripts/build_classifier_dictionary.py` — all parse.
- `python -c "import json; ..."` — all four i18n bundles valid and equal key count (369).
- Spot-check 13 high-frequency nouns: 猫→只 ✓, 狗→只(+条) ✓, 车→辆 ✓, 书→本(+册) ✓, 桌子→张 ✓, 水→杯(+瓶,碗) ✓, 人→个(+位,口) ✓, 朋友→个(+位) ✓, 电影→部(+场) ✓, 花→朵(+束) ✓, 鱼→条 ✓, 马→匹 ✓, 飞机→架 ✓.
- `SELECT * FROM get_classifier_drill_session(<uuid>, 1::smallint, 5)` — 5 items with correct distractor groups (针→根 with distractors 把/条/支 from long_thin; 树→棵 with 束/朵/个 from plants; 电影→部/场 with 册/本/个 from bound + general).
- `SELECT process_classifier_drill_submission(...)` with `correct=16, total=20` — `success: true, user_elo_change: 1200→1218 (+18), test_elo_change: 1400→1382 (-18), percentage: 80`. Idempotency replay returns `cached: true`. Smoke-test rows cleaned up afterwards.

**Verification (against running app — owner action required):**
1. Open `/classifier-drill` while signed in → expect 20-item batch to load, header shows `[ Choose | Type ]` toggle.
2. MC mode: keys 1–4 dispatch correctly; correct answers advance after a brief tick; wrong answers open the feedback modal showing the canonical `一<correct><noun>` plus the also-acceptable list and the semantic group label.
3. Toggle to Type mode → state persists across reload via `localStorage.cd_mode`. Type `只` for 猫, Enter → accepted. Type `本` for 猫, Enter → wrong, modal opens.
4. Complete the round → results screen shows accuracy/time/ELO badge; "Next round" loads a fresh batch.
5. Open `/profile` → measure-words tab visible (🧮 icon); history row shows the just-completed batch as `16/20 classifiers`.
6. Switch UI locale to ja/zh/es and confirm no dotted i18n keys appear on either page.

**Wiki updates.**
- New [features/measure-word-trainer.md](features/measure-word-trainer.md) (prose) and [features/measure-word-trainer.tech.md](features/measure-word-trainer.tech.md) (technical) — full feature + technical specs.
- [index.md](index.md) — registered both new pages, bumped page count 53 → 55, updated last-updated line.
- This log entry.

Pages updated: 2 (index.md, log.md). Pages created: 2 (feature prose + tech). Migrations applied: 4 (the submission RPC has v1 + v2_fix_generated_percentage). Open questions remaining: 0.

**Out of scope (deferred):**
- Per-classifier BKT mastery tracking (v1 is single-axis ELO).
- Pack-aware filtering (currently global Chinese).
- Per-noun TTS audio pre-rendering (template field is wired but no audio_url is populated yet).
- Japanese counters (助数詞) — requires morphophonological alternation pipeline; out of scope.
- Cloze L6/L7 prompt cleanup — left untouched per the planning Q3 decision; the new trainer is additive.
- CC-CEDICT expansion into long-tail nouns — the schema and script are designed for this (`source` column distinguishes `'curated'` from `'cedict'`); revisit if usage data shows coverage gaps.
- Anti-repetition log so back-to-back rounds don't show the same noun (Phase 2).
- Small-group distractor topup edge case: when an item's acceptable set includes 个 AND its primary group has < 3 alternatives, the general fallback is blocked and the item renders with 2 distractors instead of 3. Cosmetic.

## 2026-05-17 change | Pitch Accent Trainer for Japanese

User request: clone the Pinyin Trainer pattern for Japanese, drilling the four classical accent classes (heiban / atamadaka / nakadaka / odaka). Plan at [`C:\Users\James\.claude\plans\i-want-to-add-goofy-pixel.md`](../../.claude/plans/i-want-to-add-goofy-pixel.md). Locked design: hybrid Quick (4-key) + Contour (connect-the-dots) renderers, pre-computed `pitch_payload` JSONB on the test row via pyopenjtalk, no audio in v1.

**Backend (Python).**
- New [services/pitch_accent_service.py](../services/pitch_accent_service.py) — `process_passage(text)` runs `pyopenjtalk.run_frontend`, skips particles/aux-verbs (attached to host word as `trailing_particle`), mora-segments the katakana pronunciation, derives `pattern_class` and `contour` from `(accent, mora_size)`. Pure-function helpers `_derive_pattern_class`, `_derive_contour`, `_derive_particle_pitch`. Graceful degradation: returns `[]` on pyopenjtalk failure; logs but doesn't raise.
- [services/test_service.py:283-294](../services/test_service.py#L283) — `save_test` got a parallel branch for `language_id == 3` that calls `pitch_accent_service.process_passage(transcript)` and updates `tests.pitch_payload`. Same try/except pattern as the existing pinyin branch — payload failure doesn't block test save.
- [services/test_service.py:312-318](../services/test_service.py#L312) — `_create_skill_ratings` appends the `pitch_accent` test_type_id to the seed list for JA tests.
- [routes/tests.py](../routes/tests.py) — new `submit_pitch_accent_attempt` endpoint (clone of `submit_pinyin_attempt` with `language_id == 3` gate and `correct_units`/`total_units` parameters) and `_call_pitch_accent_submission_rpc` wrapper. `get_test_with_ratings` SELECT list extended to include `pitch_payload`; response payload includes a `pitch_payload` key for JA tests.
- [app.py:360-363](../app.py#L360) — registered `/test/<slug>/pitch-accent` page route.
- [requirements.txt](../requirements.txt) — added `pyopenjtalk`. On Windows the native `pyopenjtalk` source build needs cmake; `pyopenjtalk-prebuilt` (binary wheels) installs cleanly and exposes the same API.

**Database / migrations.**
- New [migrations/add_pitch_accent_mode.sql](../migrations/add_pitch_accent_mode.sql) — INSERT `dim_test_types('pitch_accent', 'Pitch Accent', requires_audio=false, display_order=5)`; ALTER TABLE `tests ADD COLUMN pitch_payload JSONB`; backfill `test_skill_ratings` at ELO 1400 for every `language_id=3` test. Applied to remote via Supabase MCP. Verified: 80/80 JA tests now have a pitch_accent skill rating row.
- New [migrations/process_pitch_accent_submission.sql](../migrations/process_pitch_accent_submission.sql) — accuracy-based RPC, parameter rename of `process_pinyin_submission` (`p_correct_chars`/`p_total_chars` → `p_correct_units`/`p_total_units`). Same K=32 first-attempt-only ELO formula, same idempotency check, same JSONB success/error envelope, `SECURITY DEFINER`, `GRANT EXECUTE TO authenticated`. Applied to remote.

**Frontend.**
- New [templates/test_pitch_accent.html](../templates/test_pitch_accent.html) — single-file game template with both Quick and Contour renderers and a `[ ⚡ Quick | 🎯 Contour ]` segmented toggle. Mode persists in `localStorage.pa_mode`. Quick mode: 4 arrow keys map to the 4 pattern classes. Contour mode: per-mora HIGH/LOW dot grid with live SVG polyline; keyboard `1/2` or `L/H` per mora; validates the two universal rules (mora 1 ≠ mora 2; at most one H→L drop) before checking the derived accent nucleus against `token.accent`. Error modal renders the canonical contour including the trailing particle (essential for showing odaka/heiban disambiguation). Completion screen mirrors the pinyin trainer: grade, stats, ELO delta, retry/exit buttons.
- [templates/test_preview.html:300-310, 501-504, 634-635](../templates/test_preview.html#L300) — added "Pitch Accent" test-type radio (Japanese-only visibility check) and the routing branch to `/test/<slug>/pitch-accent`.
- [templates/profile.html:105-111, 489-497](../templates/profile.html#L105) — added `pitch_accent: '🎵'` to `SKILL_ICONS`; pitch_accent history rows render as `N/M words`.
- [static/i18n/{en,ja,zh,es}.json](../static/i18n/) — added 45 keys under `pitch.*` and one `test_preview.pitch_accent` to every locale. All four locales now contain 350 keys.

**Backfill.**
- New [scripts/batch_generate_pitch_accent.py](../scripts/batch_generate_pitch_accent.py) (mirror of `batch_generate_pinyin.py`). Ran against all 80 active JA tests: 80 processed, 0 errors, 0 flagged for review.

**Wiki updates.**
- New [features/pitch-accent-trainer.md](features/pitch-accent-trainer.md) (prose) and [features/pitch-accent-trainer.tech.md](features/pitch-accent-trainer.tech.md) (technical) — full feature + technical specs including the pattern-class primer (mora rules, the four classes, particle-test disambiguation).
- [index.md](index.md) — registered both new pages, bumped page count 51 → 53, updated last-updated line.
- This log entry.

**Verification (in repo):**
- `python -m py_compile app.py routes/tests.py services/test_service.py services/pitch_accent_service.py` — all parse.
- `python -c "import json; [json.load(open(f'static/i18n/{l}.json', encoding='utf-8')) for l in ['en','es','ja','zh']]"` — all valid; all four contain exactly 350 keys.
- Service smoke test against 4 sentences confirmed correct classification: 東京 (heiban), 男 (odaka, particle drops), 命 (atamadaka), 日本 (nakadaka), 首都 (atamadaka), さくら (heiban).

**Verification (against running app — owner action required):**
1. Open a JA test preview → confirm the "Pitch Accent" button appears. Open a CN/EN test preview → confirm it does NOT appear.
2. Click → lands on `/test/<slug>/pitch-accent`. Confirm the kana grid renders and the first token is highlighted.
3. Quick mode loop: play through using arrow keys; make a deliberate mistake; confirm the error modal renders the canonical contour with trailing-particle pitch. Complete → confirm results screen shows accuracy = `(total − errors) / total`.
4. Toggle to Contour mode; submit `L-H-L-H-L` → confirm "multiple drops" error. Submit a valid-but-wrong contour → confirm position-mismatch error. Submit the correct contour → confirm acceptance.
5. After completion: verify in DB that `test_attempts` has the new row with `user_elo_before/after` populated, and `user_skill_ratings`/`test_skill_ratings` for the pitch_accent test_type moved by `K=32 × (actual − expected)`.
6. Submit the same test a second time → confirm `is_first_attempt = false` and ELO is unchanged.
7. Switch UI locale to ja/zh/es and confirm no dotted i18n keys appear on either page.

Pages updated: 2 (index.md, log.md). Pages created: 2 (feature prose + tech). Migrations applied: 2. Open questions remaining: 0.

**Out of scope (deferred to Phase 2):** per-word TTS audio playback (would need JP voice seeding into `dim_languages.tts_voice_ids` for `language_id=3`); admin override / LLM disambiguation for ambiguous compounds; compound-noun reassignment rule engine; word-sense disambiguation for same-spelling-different-accent homographs.

## 2026-05-17 change | Dictation mode shipped

Implemented dictation as a new test type, end-to-end. The `dictation` row in `dim_test_types` (id=3) had existed as an inactive placeholder since project bootstrap; this change activates it and wires the full pipeline.

**Design (locked via /plan):** whole-passage submission (single textarea, single submit), hybrid word-level scoring with Levenshtein typo tolerance, replays tracked with soft K-multiplier penalty, ignore punctuation + casing + diacritics, per-word BKT updates for every transcript word, reuse all existing listening tests verbatim, inline color-coded diff on the result screen.

**Database** ([migrations/add_dictation_mode.sql](../migrations/add_dictation_mode.sql), [process_dictation_submission.sql](../migrations/process_dictation_submission.sql), [update_get_recommended_tests_for_dictation.sql](../migrations/update_get_recommended_tests_for_dictation.sql)) — activated `dim_test_types.dictation`; added `replay_count`, `dictation_word_correct`, `dictation_word_total`, `dictation_diff` columns to `test_attempts`; backfilled 243 `test_skill_ratings` rows for `test_type_id=3`; new RPC `process_dictation_submission` mirrors `process_pinyin_submission` shape; `get_recommended_tests` changed exclusion key from `(user_id, test_id)` to `(user_id, test_id, test_type_id)` and added an 80-word transcript cap on the dictation lane.

**Backend** ([services/dictation/grader.py](../services/dictation/grader.py), [tokenizer.py](../services/dictation/tokenizer.py)) — new scoring service with `grade_dictation(canonical, user, language_code) → GradingResult`. Pure-Python bounded Levenshtein (no `python-Levenshtein` dependency); `difflib.SequenceMatcher` alignment; lazy `jieba` import for Chinese with char-level fallback for Japanese. [routes/tests.py](../routes/tests.py) gained `POST /api/tests/<slug>/submit-dictation` and a `?mode=dictation` query param on the existing GET handler that strips the canonical transcript pre-submit. [app.py](../app.py) added `GET /test/<slug>/dictation` page route. `DimensionService.get_language_code(language_id)` helper added.

**Frontend** ([templates/test_dictation.html](../templates/test_dictation.html)) — new self-contained client page with audio player, replay counter, speed toggle (1.0x / 0.75x / 0.5x via `playbackRate`, zero TTS cost), textarea, submit button, results overlay with inline diff (correct / wrong / missing / extra). [templates/test_preview.html](../templates/test_preview.html) `startTest()` routing updated to point dictation at `/test/<slug>/dictation`. 22 new `dictation.*` i18n keys added across en / zh / es / ja.

**Replay K-multiplier curve.** `max(0.5, 1.0 - 0.10 * max(0, replay_count - 1))` — one replay free, -10% per additional play, 0.50 floor. Composed multiplicatively with retry-slot factor per [ADR-006](decisions/ADR-006-retry-slot-reduced-elo.md). Persisted to `test_attempts.elo_reduction_factor` so the existing `profile.html` "Review · 0.45× ELO" badge renderer works unchanged. No new ADR; inline-documented.

**Per-word BKT.** Every canonical token that maps to a `dim_word_senses` row (via `tests.vocab_token_map` surface lookup) triggers `VocabularyKnowledgeService.update_from_word_test(sense_id, is_correct)`. One dictation submission ≈ 50-100 BKT data points vs ~5 from a comprehension test — the dominant learning-value upside of this feature.

**Tests** ([tests/test_dictation_grader.py](../tests/test_dictation_grader.py)) — 34 unit tests covering Levenshtein, fuzzy equality thresholds, normalization (case / diacritics / punctuation / apostrophes / hyphens / whitespace), tokenization, perfect/zero match, typo within and beyond tolerance, short-word strictness, extra/missing words, empty transcript, Chinese round-trip, diff payload serialization. All passing. Full pre-existing test suite still passes (the one unrelated `test_difficulty_frequency::test_tier_still_dominates` failure is a flaky `assert 2.1 < 2.1` in exercise generation, untouched here).

**Verification.** `SELECT test_type, COUNT(*) FROM get_recommended_tests(user_uuid, 1::smallint) GROUP BY test_type` returns 3 dictation candidates alongside the existing listening and reading lanes.

**Pages created/updated:** [features/dictation.md](features/dictation.md), [features/dictation.tech.md](features/dictation.tech.md), [index.md](index.md). Cross-references: [features/comprehension-tests.md](features/comprehension-tests.md) (dictation status updated to in-progress → complete).


## 2026-05-15 change | Production-code audit + HIGH/MEDIUM/LOW remediation

Full-codebase audit (Python backend, SQL/RPC layer, JS/templates frontend) followed by a graded remediation pass. Plan + findings at [`C:\Users\James\.claude\plans\crawl-the-code-base-eager-wilkes.md`](../../.claude/plans/crawl-the-code-base-eager-wilkes.md). Three parallel `Explore` agents produced 60+ findings; this entry covers the 22 items shipped and the 9 explicitly skipped.

**HIGH severity (8 of 9 shipped, 1 deferred to user decision).**
- [config.py](../config.py) — removed the `'temp-secret-change-in-production'` and `'jwt-secret-change-in-production'` fallback defaults; added `Config.validate()` that raises `RuntimeError` at startup if `SECRET_KEY`, `JWT_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, or `SUPABASE_SERVICE_ROLE_KEY` is unset. Wired into [app.py](../app.py) `create_app()` before any other init.
- [middleware/auth.py](../middleware/auth.py) — service-role-as-bearer-token compare in `jwt_required` switched from `token == service_role_key` to `hmac.compare_digest` (constant-time); also logs `'Service-role bypass used on %s'` so the bypass leaves an audit trail. A `TODO` flags the deeper fix (dedicated batch-service credential separate from the service-role key).
- [services/auth_service.py](../services/auth_service.py) — `AuthService.__init__` no longer builds a second admin Supabase client via `create_client(...)`. It now pulls the singleton from `SupabaseFactory.get_supabase_admin()` and raises if the factory wasn't initialized.
- [migrations/restore_get_distractors_auth_check.sql](../migrations/restore_get_distractors_auth_check.sql) (new) — restores an auth guard on `get_distractors` that was removed by `get_distractors_drop_auth_check.sql`. The new guard uses `auth.role() NOT IN ('authenticated', 'service_role')` so service-role calls still pass; `REVOKE EXECUTE ... FROM anon` adds defense-in-depth. **Not applied to remote yet — apply via Supabase MCP when ready.**
- [templates/base.html](../templates/base.html) — `JSON.parse(_getStored('user_data') || '{}')` now wrapped in try/catch; corrupt storage is cleared instead of permanently breaking page load for that user.
- [routes/tests.py](../routes/tests.py), [routes/admin_local.py](../routes/admin_local.py) — replaced bare `int(request.args.get('limit', 50))` patterns with Flask's `type=int` coercion so malformed query params no longer 500.
- [routes/payments.py](../routes/payments.py) — `create_payment_intent` was reading `flask_jwt_extended.get_jwt_identity()` despite being protected by our own `@supabase_jwt_required` decorator (which never populates the flask-jwt-extended context). Switched to `g.current_user_id`. **Found a latent bug along the way:** the route wrote `user_email` into Stripe metadata but `PaymentService.handle_successful_payment` reads `intent.metadata['user_id']` — so the webhook would have raised `KeyError` for any intent created by this route. Metadata key now matches the reader.
- [static/js/admin-dashboard.js](../static/js/admin-dashboard.js) — `populateTestLanguageChecks` now runs `lang.language_name` through `escapeHtml`; `loadExerciseItems` does the same for `labelFn(item)` output. `vocabBrowser`'s list-item `onclick="vocabBrowser.select(${w.sense_id})"` replaced with delegated handler on `#vbScroll` + `data-sense-id` attribute (idempotent attach via `dataset.delegated`). The 4 other inline onclicks in `renderPreview` use numeric DB IDs (zero XSS risk, CSP-only concern) — left for a future CSP-hardening pass.
- **Deferred to user**: `process_test_submission` defined in 5 migration files. Consolidation requires knowing which is canonical / how migrations are applied. Surfaced; awaiting decision.

**MEDIUM severity (10 of 14 shipped, 4 skipped with rationale).**
- [services/payment_service.py](../services/payment_service.py) `handle_successful_payment` — added an **idempotency check** against `token_transactions` where `payment_intent_id = p_payment_intent_id AND action = 'purchase'`. Duplicate Stripe webhook deliveries now return `{idempotent: true}` without re-crediting. Also tightened the `user_tokens` `select('*')` to the three columns consumers actually use (`user_id, purchased_tokens, last_free_token_date`).
- [routes/vocab_admin.py](../routes/vocab_admin.py) `upload_words` — the per-sense rendering loop swallowed `Exception` silently; it now collects `failed_senses[]` with `{sense_id, error}` and returns it alongside `rendered_count` so the admin UI can surface partial failures.
- Datetime standardization — replaced all 22 `datetime.utcnow()` calls with `datetime.now(timezone.utc)` across [services/payment_service.py](../services/payment_service.py), [services/test_generation/](../services/test_generation/) (orchestrator + database_client), [services/conversation_generation/](../services/conversation_generation/) (orchestrator + database_client), [services/topic_generation/](../services/topic_generation/) (orchestrator + database_client). `timezone` imports added where missing. `utcnow()` is deprecated in Python 3.12+.
- [migrations/add_test_attempts_idempotency_index.sql](../migrations/add_test_attempts_idempotency_index.sql) (new) — partial compound index `(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL` for `process_test_submission`'s duplicate-check `SELECT`. Index is partial because most attempts have NULL key.
- [migrations/drop_unused_rpcs.sql](../migrations/drop_unused_rpcs.sql) (new) — drops 4 verified-dead RPCs: `can_use_free_test(uuid)`, `get_model_for_task(text, smallint)`, `get_prompt_template(varchar, integer)`, `get_vocab_recommendations(uuid, integer, double, double, integer)`. Verified zero Python callers and zero in-SQL callers for each. **Audit was wrong about `calculate_volatility_multiplier` and `calculate_elo_rating`** — both are still called from `process_test_submission_reduced_repeats.sql` (latest active version). Kept.
- [static/i18n/es.json](../static/i18n/es.json) — added the 8 mystery-feature keys that were missing only from Spanish (`common.nav.mysteries`, `mystery.list_title`, `mystery.list_subtitle`, `mystery.recommended`, `mystery.filter_difficulty`, `mystery.all_levels`, `mystery.no_mysteries`, `mystery.no_mysteries_desc`). All four locales now have exactly 283 keys.
- [static/js/i18n-manager.js](../static/js/i18n-manager.js) — `t()` now logs `console.warn('[i18n] missing key:', key)` once per missing key instead of silently rendering the dotted key. Future locale drift surfaces immediately in dev.
- [static/js/admin-dashboard.js](../static/js/admin-dashboard.js) `setupCollocationFilters` — rewritten as a single delegated listener on `.colloc-filter-bar` with a `dataset.delegated` guard. Re-running setup no longer stacks listeners on individual `.btn` elements.
- [templates/exercises.html](../templates/exercises.html) — `initLanding` now manages an `AbortController`; `startPractice` calls `cancelLandingFetches()` before transitioning so late `/api/exercises/types` and `/api/exercises/session` responses can't overwrite the practice view.
- **Skipped:** (1) `.in_()` chunking — every call site is bounded by `.range()` pagination or session size; the audit's [unverified] flag was correct. (2) `ORDER BY random()` rewrite — needs EXPLAIN ANALYZE evidence on production data sizes first; the audit itself recommended measuring before rewriting. (3) `corpus_style_profiles.select('*')` — admin-only endpoint, no leak risk worth changing without schema lookup. (4) Rate limiting on expensive endpoints — adds a new dependency and infrastructure decisions; surfaced to user with three implementation options.

**LOW severity (4 of 8 shipped, 4 skipped with rationale).**
- [static/js/exercise-renderers.js](../static/js/exercise-renderers.js) — `escHtml` now delegates to `window.LinguaUtils.escapeHtml` when available (falls back to the local impl on pages like the admin dashboard that don't load `utils.js`). Three duplicate implementations down to two, with the second being a thin shim.
- [templates/exercises.html](../templates/exercises.html) — deleted the inline `function i18n(...)` block at lines 558-574. Turned out to be **dead code** (defined but never called inside the IIFE); the audit thought it was a duplicate map but it was unused.
- [middleware/auth.py](../middleware/auth.py) — deleted the `AuthMiddleware` class (~110 lines, lines 209-319). It was instantiated in [app.py](../app.py) and attached as `auth_bp.auth_middleware`, but no caller ever read that attribute. Removed the import and the assignment too. Net `-140` lines across the two files.
- **Skipped:** (1) `os.environ.get` vs `os.getenv` mix — purely cosmetic. (2) `logger.debug` containing user IDs — flag only if logs ship to a third-party aggregator; no code change required. (3) `alert()` replacement — the audit pointed at 2 instances, the file actually has 24. Replacing them all is a real toast-system project, not a LOW cleanup. (4) Moving the ~1000-line inline `<script>` in exercises.html — substantial refactor with Jinja-variable plumbing; risk-to-reward unfavourable at LOW priority.

**Verification (in repo):**
- `python -m compileall config.py app.py middleware/auth.py services/auth_service.py services/payment_service.py routes/tests.py routes/admin_local.py routes/payments.py routes/vocab_admin.py services/test_generation services/conversation_generation services/topic_generation` — all parse.
- `python -c "import json; [json.load(open(f'static/i18n/{l}.json', encoding='utf-8')) for l in ['en','es','ja','zh']]"` — all valid; all four contain exactly 283 keys.
- `grep -rn "datetime\.utcnow\(\)" services routes middleware models utils` — zero hits (Portal/ subfolder is out of scope).
- `grep -rn "AuthMiddleware" .` — zero hits in code (one historical mention remains in this log, which is correct).

**Verification (against running app — owner action required):**
1. Boot with `.env` missing `SECRET_KEY` → expect `RuntimeError: Missing required environment variables: SECRET_KEY...` at startup instead of silent insecure boot.
2. Boot with full `.env` → app starts normally; `Config.validate()` is a no-op.
3. Apply the three new migrations to remote via Supabase MCP: `restore_get_distractors_auth_check.sql`, `add_test_attempts_idempotency_index.sql`, `drop_unused_rpcs.sql`.
4. Smoke a payment intent: `POST /api/payments/create-intent` → confirm Stripe metadata contains `user_id` (not `user_email`); replay the webhook to confirm the idempotency check returns `idempotent: true` instead of double-crediting.
5. Smoke admin: open the admin dashboard, click the language test checkboxes (escapeHtml works), and a vocab browser row (data-sense-id delegation works).
6. Smoke i18n: switch locale to `es`, open the mysteries list, verify no dotted keys appear; switch to a locale and remove one key to confirm `console.warn` fires.

**Wiki updates.**
- This log entry.
- [database/rpcs.tech.md](database/rpcs.tech.md) — `get_distractors` documented with the restored `auth.role()` check + drop-then-restore history. `can_use_free_test`, `get_model_for_task`, `get_prompt_template`, `get_vocab_recommendations` marked deprecated / dropped. RPC count revised from 53 to 49.
- [business-rules/auth-and-access.md](business-rules/auth-and-access.md) — added "Startup invariants" section (`Config.validate`), service-role-bypass note, and a deprecation line for the removed `AuthMiddleware` class.
- [features/token-economy.tech.md](features/token-economy.tech.md) — added Stripe-webhook idempotency note; removed `can_use_free_test` from the key-functions list (dropped); flagged the recovered `user_id`-vs-`user_email` metadata bug.
- [index.md](index.md) — header bumped.

Pages updated: 5. Pages created: 0. New migrations queued for apply: 3. Open questions remaining: 2 (rate-limiting strategy, `process_test_submission` migration consolidation).

## 2026-05-15 change | Reduced-volatility ELO on daily-load retry-slot repeats

User intent: when the dashboard's daily-load retry slot resurfaces a test the learner previously scored sub-70% on, retaking it should grant ELO movement at reduced volatility rather than the previous flat zero. Plan at [`C:\Users\James\.claude\plans\i-think-that-if-elegant-pancake.md`](../../.claude/plans/i-think-that-if-elegant-pancake.md). Locked design: retry-slot scope only (not broader `get_recommended_tests`), time-decay factor + improvement bonus, test ELO scales symmetrically.

**Core change.** New migration [migrations/process_test_submission_reduced_repeats.sql](../migrations/process_test_submission_reduced_repeats.sql) — `ALTER TABLE test_attempts ADD COLUMN IF NOT EXISTS elo_reduction_factor numeric NULL` plus a `CREATE OR REPLACE FUNCTION public.process_test_submission(...)` rewrite. Same 7-arg signature; existing Python callers unchanged. Applied to remote project via Supabase MCP. Verified: column exists `numeric NULL`, function signature unchanged.

Inside the rewritten body:
- First-attempt path is identical to the prior 2026-05-08 V3 behaviour (full K=32 × volatility on user side, K=16 on test side).
- Repeat-attempt path now branches on three eligibility conditions, all server-side: (i) `is_first_attempt = false`, (ii) test is in today's `daily_test_loads.test_ids` with `slot_type='retry'` for this user+language (JSONB element scan with `(elem->>'test_id')::uuid = p_test_id`), (iii) no prior `test_attempts` row today for this `(user, test)` already has `elo_reduction_factor IS NOT NULL` (anti-grind sentinel).
- Eligible repeats compute `base = clamp(0.20, days_since_last/60, 1.0)`, `bonus = 0.25` if `(current_percentage − MAX(prior percentage)) ≥ 15` else 0, `factor = LEAST(1.0, base + bonus)`. The factor is composed into the volatility argument passed to `calculate_elo_rating` (user side: `volatility × factor`; test side: `factor`). Same K-factors as today (32 / 16), so the factor naturally scales both updates symmetrically.
- Applied factor is persisted to `test_attempts.elo_reduction_factor` — NULL when no factor was applied (first attempt with full ELO, or non-eligible repeat with zero ELO).

**API + UI plumbing.**
- [routes/tests.py](../routes/tests.py) `_build_submission_response` — added `elo_reduction_factor` field to the response so the front-end can badge the result screen.
- [routes/tests.py](../routes/tests.py) `get_test_history` — added `elo_reduction_factor` to both the `test_attempts` SELECT and the per-row history payload, so the profile history badge has data to render against.
- [templates/profile.html](../templates/profile.html) `renderHistory` — appends a small `<span class="badge bg-info">Review · {factor}× ELO</span>` next to the test title when `elo_reduction_factor` is non-null. Hovering shows the localised tooltip.
- i18n: added `profile.review_badge` / `profile.review_badge_tooltip` keys to [en](../static/i18n/en.json), [zh](../static/i18n/zh.json), [ja](../static/i18n/ja.json), [es](../static/i18n/es.json).

**Wiki updates.**
- New [decisions/ADR-006-retry-slot-reduced-elo.md](decisions/ADR-006-retry-slot-reduced-elo.md) — context, factor formula, anti-grind design, alternatives rejected (flat 0.5×, slot-typed buckets, broadened recommender).
- [algorithms/elo-ranking.md](algorithms/elo-ranking.md) — added "Reduced-Volatility Repeats" prose section; added repeat-attempt bullet to Constraints.
- [algorithms/elo-ranking.tech.md](algorithms/elo-ranking.tech.md) — data-flow diagram now shows the three-way branch (first / eligible repeat / non-eligible repeat); added a "Retry-Slot Reduced-Volatility Factor" section with the exact formula and notable values; `test_attempts.elo_reduction_factor` documented in the Tables section.
- [algorithms/elo-implementation-analysis.md](algorithms/elo-implementation-analysis.md) — appended a "Recently Fixed (2026-05-15)" entry crediting the migration.
- [features/comprehension-tests.tech.md](features/comprehension-tests.tech.md) — the `POST /api/tests/submit` documentation now lists the first/eligible-repeat/off-recommendation branches and includes `elo_reduction_factor` in the response shape.
- [index.md](index.md) — page count bumped to 49; ADR-006 added; header updated.

Pages updated: 6. Pages created: 1 (ADR-006). Migrations applied: 1.

**Out of scope (per planning Q1 decision):** Broadening `get_recommended_tests` to include previously-attempted tests under any criteria. The retry-slot remains the only repeat-surface. Surfacing the upcoming factor on the dashboard *before* submission (`up to 0.5× ELO`) was also deferred.

**Verification (deferred to next live submission):**
1. `\d test_attempts` includes `elo_reduction_factor` column. ✅ (confirmed via MCP `execute_sql`)
2. `pg_get_function_arguments` for `public.process_test_submission` still returns the 7-arg signature. ✅ (confirmed via MCP)
3. End-to-end smoke: with a user who has a sub-70% historic attempt currently in today's retry slot, submit a known-score response and verify (a) `test_attempts.is_first_attempt = false`, (b) `elo_reduction_factor` ≈ 0.20 (same-day no-improvement) or ≈ 0.45 (same-day with 15+pp improvement), (c) `user_skill_ratings.elo_rating` and `test_skill_ratings.elo_rating` deltas match `factor × K × (actual − expected)`.
4. Anti-grind: submit the same test again via direct slug nav; expect `elo_reduction_factor = NULL`, no ELO motion.
5. Off-recommendation regression: submit a different previously-attempted test that is *not* in today's load; expect `elo_reduction_factor = NULL`, no ELO motion.
6. First-attempt regression: submit a fresh never-attempted test; expect `elo_reduction_factor = NULL`, full-volatility K=32 motion (unchanged from today).
7. UI: profile history row for the reduced-ELO repeat shows the `Review · 0.45× ELO` badge in the active locale.

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

## [2026-07-13] task | TASK-626 done — dual-translation taxonomy v5 (expanded subtypes + subtype_meta)

Phase-2 taxonomy expansion for Evidence-First grading. Rubric untouched (stays v4); taxonomy-only bump.

**Applied live:** `migrations/dt_taxonomy_v5_seed.sql` as the single active `dt_taxonomy_version`
row (v5; v4 deactivated). Per-L2 subtype sets grown to tech-spec §5 sizes — EN 15 / JA 17 / ZH 17
(shared core 8 + per-target). New top-level **`subtype_meta`** (33 entries): per-subtype
`{dimension, default_severity, treatable, cloze_suitable}` — the §4 machinery TASK-627 derived
scoring reads. JA `particle` **split** into `particle_wa_ga` / `particle_case` / `particle_other`
(per-instance re-adjudication of the 8 JA particle gold items, user-adjudicated). `particle` kept in
`subtype_meta` only as a historical alias → accuracy (not in any pairs list) so v1–v4 stored rows
still resolve; all other v4 subtypes survive verbatim. 15 new subtypes' ZH/JA glosses+templates
AI-drafted, flagged for native review in the migration header (ADR-019 pattern).

**Files:** `migrations/dt_taxonomy_v5_seed.sql` (new); `tests/test_dual_translation_taxonomy_v5.py`
(new, 28 — shape/totality/alias/no-slug-fallback); `tests/fixtures/dt_gold/{en,zh,ja}.json`
(re-tagged to v5); `scripts/run_dt_grading_eval.py` (hardened: retry+backoff + `--resume`);
`tests/test_dt_eval_harness_retry.py` (new). Full DT/dictation suite 355 green.

**Paid harness re-run ($0.624):** subtype accuracy EN .714→.727 ↑ / JA .760→.875 ↑ / ZH .833→.739
(finer 17-way vs old 9-way tagset — not a detection regression); span F1 + clean FP held on all
three; severity within-one 1.000 all; **625-deferred JA floor re-confirmed** (span F1 .696 / clean
FP .000). The new retry wrapper recovered the JA run from a mid-run `getaddrinfo` DNS failure (the
exact TASK-625 orphaning cause). Full gate assessment: [[evaluations/dt-grading-baseline-2026-07-05]]
(TASK-626 update). As-built: [[algorithms/evidence-first-grading.tech]] §11. Unblocks TASK-627.

## [2026-07-14] task | TASK-220 done — Practice-merger deprecation cleanup
Dropped both wrapper RPCs (`migrations/phase17_drop_deprecation_wrappers.sql`; `phase12_deprecation_wrappers.sql` → `migrations/archive/`, recorded in archive README). `/api/exercises/session` and `/api/vocab-dojo/session` handlers now **302** to `/api/practice/session` (`auto` / `acquisition`). Last live `get_ladder_session` RPC caller removed; `get_exercise_session_service` alias + `services/exercise_session_service.py` shim deleted, `app.py` repointed to `get_practice_session_service`. Per the "retire both pages" decision, the standalone `/exercises` + `/vocab-dojo` page routes, their templates, and the Vocab Dojo nav link were removed — the unified `/session` Practice player is the sole live surface (the vocab-dojo gate/stress/word API endpoints stay). `grep --include="*.py"` clean; changed modules byte-compile; no tests referenced the retired surfaces. Wiki updated: [[tasklist/master]], [[tasklist/archive/study-plans.tasks]], [[features/practice-engine.tech]], [[database/rpcs.tech]], [[features/exercises]], [[features/vocab-dojo]]. Study Plans epic now complete.

## [2026-07-14] task | TASK-618 done — Inject DT error exercises into Practice Engine sessions
Cross-feature integration into the live session assembler. `services/dual_translation/cards.py` gained `select_error_exercises_for_practice`: materialises due cards (idempotent `generate_cards_for_queued_entries`), fetches due `dt_card` rows **L2-scoped** via `profile_entry_id → dt_error_profile_entry.l2_language_id` (dt_card has no language column, so a JA session never surfaces a ZH card), round-robins them through the existing `interleave_by_subtype`, and caps at `min(due, MAX, ceil(FRACTION × normal_items))`. Env knobs `DT_PRACTICE_ERROR_CARD_MAX`=3 / `DT_PRACTICE_ERROR_CARD_FRACTION`=0.34 (env-direct, matching `DT_ERROR_CARD_INTERLEAVE_EVERY`, not `Config`). `PracticeSessionService.get_session` injects **after** the RPC, spreading the capped, **non-sense-linked** (`word_sense_id: None`) items evenly through normal items via a new `_interleave_extras` staticmethod — best-effort (never breaks the session) and only into a non-empty session (empty stays empty; `GET /next` still owns the no-practice due queue). Items carry `card_id` for the existing `POST /cards/<id>/review` grade path. FE renderer deferred: the v1 practice player and legacy `get_or_create_daily_session` **skip** `is_error_exercise` items like gate/stress markers, so nothing renders broken; wiring the cloze/isolate UI into `static/js/session/players/practice.js` is the tracked follow-up. 12 new unit tests; full suite 951 passed / 1 skipped, no regressions. Wiki updated: [[tasklist/master]], [[tasklist/archive/dual-translation.tasks]].

## [2026-07-16] task | TASK-644 done — Append-only JSONL eval-harness checkpoint
Replaced the O(n²) resume checkpoint in `scripts/run_dt_grading_eval.py`: `_save_checkpoint` rewrote the entire records+skipped payload as indented JSON after every graded item (largest writes late in a run, between paid model calls). It now takes the single freshly-completed item (`record=` / `skipped=` kwargs) and **appends one `{"type","data"}` JSONL envelope** per item — O(1), `flush()`+`fsync()` after each write. `_load_checkpoint` streams the JSONL, partitions by envelope `type`, and skips an unparseable trailing line (a crash mid-append) instead of aborting. A legacy pre-644 whole-file `{records,skipped}` sidecar is detected (the whole file still parses as one JSON object; a JSONL log doesn't), loaded once, and rewritten to JSONL in place via new `_migrate_checkpoint_to_jsonl` (temp+replace). **Beyond spec:** the `--resume` simulation surfaced that a torn *newline-less* final line glues the next append onto it and loses that item, so `_needs_leading_newline` makes an append after a torn tail start a fresh line — else a re-graded item silently drops from the log on a double-crash. Both `main()` callsites updated. Tests: 20 green (was 19; +8 checkpoint cases: JSONL append, streaming load, legacy migration + follow-on append, torn-tail read + torn-tail append, empty file, no-op guards); a simulated `--resume` after interrupt recovers the same 4 done-ids. Wiki updated: [[tasklist/master]], [[tasklist/archive/evidence-first-grading.tasks]].

## [2026-07-19] task | TASK-632 done — Evidence-First v2 final eval; DT_FRAMEWORK_V2 flipped ON
Full TASK-622 harness run on the completed v2 stack (Detector/Verifier + derived scoring +
Explainer), rubric **v6 as candidate config** via the new `--rubric-file` flag (evaluate-before-
activate; live DB untouched) + new `--framework-v2` flag (explicit, env-independent framework
selection; report header now names the framework). Results filed as
[[evaluations/dt-grading-v2-2026-07-19]]: EN span F1 .543→**.941** / clean FP .200→**.000** /
overall QWK .512→**.824**; JA .696→**.880** / .000→.100 (1 item) / .419; ZH .639→**.880** /
.100→.200 (2 items) / .245 (±.1 ZH run variance; fidelity QWK .891 best-ever). Severity within-one
1.000 everywhere; zero provisional/skipped/fell-open across 90 items. **`Config.DT_FRAMEWORK_V2`
default flipped ON** (rollback = env false); 12 v1-path tests pinned `framework_v2=False`
(rollback-path tests); DT suite 596 green. Harness also gained: eval_metrics None-guard for v2
both-fail records (+1 test), honest cost caveat (checkpoint lacks per-item usage — improvement
filed). Wiki: framework pages → complete; v1 cascade pages → deprecated w/ v2-live banner;
[[business-rules/translation-error-taxonomy]] → v5/triad reality; index/master reconciled;
master's duplicated TASK-627 note deduped. **Owed:** `dt_rubric_v6_seed.sql` live apply (TASK-629
carry) — the session's permission classifier denied every DB-write wire (local script, MCP
execute_sql, apply_migration); seed is idempotent + guarded, one manual apply. Code-review +
improvement report delivered in-session (headline items: checkpoint per-item usage, JA latency/
output-token cap, naturalness/range gold coverage, `_fetch_active_scalar` None-caching, highlight↔
verdict reconciliation).

## 2026-07-20 ship | TASK-706 — advisory lock actually guards the weekly cron

Closes finding **F7** ([[algorithms/daily-session-implementation-analysis]]): the weekly
study-plan recompute's advisory-lock helpers existed but were never called, referenced a bogus
`irt_try_lock` RPC, and the lock RPCs they named didn't exist — so every gunicorn worker ran the
full `_run_weekly_plan_recompute` sweep (idempotent, but N× DB load, and the docstrings lied).

**Files created: 1**
- `migrations/study_plan_advisory_lock.sql` — `pg_try_advisory_lock_for_study_plan()` /
  `pg_advisory_unlock_for_study_plan()`, DEFINER wrappers around
  `pg_try_advisory_lock/unlock(1467840848)` (key `0x577D7950` = ASCII 'StPP', distinct from the
  IRT job's `8901234567890123`). Applied live to `kpfqrjtfxmujzolwsvdq` 2026-07-20.

**Files modified: 2**
- `services/study_plan_service.py` — rewrote `_try_advisory_lock` to drop the dead `irt_try_lock`
  call and mirror the IRT calibrator's shape (list/scalar `resp.data` handling; warn + fall through
  to `True` when the RPC is unavailable). `_run_weekly_plan_recompute` now acquires the lock and
  **early-returns `{skipped:True, fired:0,...}`** when another worker holds it, and wraps the paged
  sweep in `try/finally` to release. Removed the unused, misleading `_ADVISORY_LOCK_KEY` constant
  (key now lives server-side). `_release_advisory_lock` now logs on failure instead of silent pass.
- `tests/test_weekly_plan_seeding.py` — new `TestWeeklyRecomputeAdvisoryLock`: the lock-loser skips
  (no `db.table` paging, no `compute_weekly_plan`, no release), the lock-winner runs then releases.

**Verification:** live probe `SELECT took_lock, held_in_pg_locks, released` →
`true, 1, true` (correct key held under `pg_locks`); a second concurrent session gets `false` by
`pg_try_advisory_lock` semantics. `tests/test_weekly_plan_seeding.py` 6/6 green.

Wiki: F7 marked RESOLVED; TASK-706 → Done in the archived tasklist + master (counts 44→43 / 98→99);
both RPC catalogs (`api/rpcs.tech`, `database/rpcs.tech`) document the new lock pair. Per
`migrations/CLAUDE.md`, no archive step — the two function names are new, defined nowhere else.

## [2026-07-20] task | TASK-708 /session discoverability (navbar + entry flow) → Done
Made the daily `/session` runner discoverable. Added `common.nav.daily_session` to all 4 locale
JSONs (en/es/zh/ja) and a "Daily Session" nav item — placed **first** in both the desktop nav and
the mobile dropdown of `templates/base.html` — with an active-state highlight on
`request.endpoint == 'study_session_page'`.

Post-language-selection CTA redesigned (user chose **primary → session, tests secondary**):
`templates/language_selection.html` primary button relabelled (`lang_select.start_session`) and
repointed from `tests` to `study_session_page`; a new muted secondary link
(`lang_select.browse_tests` → `tests`) enables only once a language is chosen. Both paths persist
`selectedLanguageId` first. New keys `lang_select.start_session` + `lang_select.browse_tests` added
to all 4 locales. Login-landing criterion satisfied by the navbar entry (surfaces on every
authenticated page), so no login-page change.

**Files modified: 6** — `templates/base.html`, `templates/language_selection.html`,
`static/i18n/{en,es,zh,ja}.json`. All 4 JSONs re-validated with `json.load` (green).
Wiki: TASK-708 → Done in the archived tasklist; master row removed, counts 42→41 Not Started /
100→101 Done.

## [2026-08-07] task | TASK-710 — consolidate the duplicated greedy pass (F12) + live-land TASK-705
Merged `build_daily_session`'s two byte-identical greedy loops into one pass. The second loop
(parallel `v_replay_used`/`v_replay_skills` accumulators, only there to populate
`pg_temp.skill_counts`) was deleted; `skill_counts` is now created before the single budget loop
and the `INSERT … ON CONFLICT DO UPDATE` runs inline in the test-kind branch.
`migrations/task702_build_daily_session.sql` edited in place (header now `TASK-702/704/705/710`) —
the one final RPC file.
**Verification:** (AC1) 20-scenario rollback-only fixture matrix on Supabase compared old two-loop
`g_old()` vs new one-loop `g_new()` across varied budgets, spacing `CONTINUE`s, `pmv` ties and
interleaved practice slots → **0 mismatches** on used/objective/skills/counts; plus an end-to-end
rollback smoke call on a cloned current-week plan (5 test_ids, single-pass counts drove hydration +
shortfall). (AC3) deployed via `apply_migration task710_build_daily_session_single_pass`;
`pg_get_functiondef` confirms one `FOR v_cand IN` loop and `v_replay_used` gone.
**F13/AC2 archiving:** nothing archived — `phase13_build_daily_session.sql` is the sole repo record
of `test_time_estimate`/`week_start_for` (migrations/CLAUDE.md rule #4), so it stays despite its
stale `build_daily_session`; no new superseded file (edit-in-place).
**Scope note:** the same apply also landed **TASK-705** (same-day-safe re-entrancy), which was
built + rollback-verified on 2026-07-20 but its live apply was owed — the repo file bundles it and
the user chose to land 705+710 together. Live `build_daily_session` was 702+704 before this.
Wiki: TASK-710 → Done (archived tasklist + master row `[x]`, counts 41→40 Not Started / 101→102
Done); tech-page finding **F12 → RESOLVED**. Memory `resolver-hydration-skill-gap` updated
(705 now LIVE; 710 recorded).

## [2026-08-07] task | TASK-709 runner UX/a11y (F14) + TASK-701 live verification + TASK-713 wiki reconciliation (F16)
Closed every remaining non-blocked item in [[tasklist/archive/daily-session-hardening]].

**TASK-709 (F14) — runner UX/a11y.** Error card gained a Retry button wired to a new
`retryLoad()` that re-invokes `loadSession()` and re-renders the still-retryable card on a
second failure. `#sessionProgress` now carries `aria-live="polite"` + `data-i18n-aria`;
`#sessionDots` is `role="list"` with each dot `role="listitem"` and an `aria-label` of
`"{type} — {state}"`. `showSummary()` renders per-item rows (icon/title/type/state); skipped
rows are distinguished by opacity + line-through + amber, i.e. not by colour alone. Added
`escapeHtml()` — server-supplied titles land in both `innerHTML` and an attribute context.
**Latent bug found while verifying the i18n gotcha:** all 9 new `session.*` keys were already
present and localized in all 4 locales, but `itemTypeLabel()` resolves `test_list.<test_type>`
and **`test_list.pitch_accent` existed in none of them** (only `test_preview.pitch_accent` did) —
every JA pitch-accent item would have rendered/announced the raw key. Added to en/es/zh/ja reusing
each locale's existing wording; all four re-validated with `json.load` (542 keys each).
**Files: 6** — `static/js/session/controller.js`, `templates/study_session.html`,
`static/i18n/{en,es,zh,ja}.json`.

**TASK-701 tail — live verification (no re-implementation).** No browser session available, so the
owed eyeball check used the sanctioned rollback-only path. A trap had to be cleared first: there was
no `weekly_plan_states` row for the current week (`2026-08-03`; latest was `2026-07-06`) and the RPC
`RETURN true`s without one — a naive probe would have read as a false pass. Inside the txn the row
was moved to the current week and zeroed, then 24 × `record_session_progress(p_kind =>
'practice_acq', p_delta_seconds => 25)` — the AC's "10-minute block of 25 s attempts". Result:
`acq_sec 0 → 600`, `acq_min 0 → 10`, 24 attempts logged, **`practice_completed_acq_min > 0` true**
(the old `round(ms/60000)` credited 0 per attempt). Rollback proven clean: current-week rows 0,
original row intact. AC1/AC3 verified by code (`performance.now()` timer at
`players/practice.js:139/195/175`; `_effective_practice_seconds` clamps >5 min and missing/zero ms
to the p50 estimate). All 4 ACs checked; **no code changed**.

**TASK-713 (F16) — wiki truth reconciliation.** TASK-201–219 audited against the **live DB**, not
just the repo — every table, column, seed, RPC, cron and route leg probed on `kpfqrjtfxmujzolwsvdq`
— and flipped to Done. **One discrepancy recorded rather than papered over:** TASK-210 is titled
"RPC `compute_weekly_plan`" but no such DB function exists (`pg_proc` → 0 rows); it is
`StudyPlanService.compute_weekly_plan` over the two real RPCs `compute_weekly_plan_load_signals` +
`compute_weekly_plan_persist`. An audit note now sits on the task so a future 0-row probe isn't
misread as a missing object. master.md counts recomputed — the old "Not Started 40" disagreed with
its own tables; actual **28**, Blocked 5, Done 102 → **104**, plus a new In-Progress row for
TASK-629. [[pages/pages-overview]] gained `/session` **and** seven other missing live routes;
`/exercises` and `/vocab-dojo` were still listed as live pages though TASK-220 deleted their routes
and templates on 2026-07-14 — both now marked RETIRED with their 302 targets. New
[[pages/study-session]] + [[pages/study-session.tech]] capture the runner design that previously
lived only in an out-of-repo plan file (queue algorithm, both endpoint contracts, controller state
machine, the `authFetch` `res.ok` trap, a11y contract, 4 ADR-style decisions). Registered in
[[index]] (Pages 95 → 97).

**Lint:** 0 remaining `[ ] Not Started` in study-plans.tasks; daily-session-hardening shows 12 Done
and only TASK-711/712 `[?]`; no page still presents a retired route as live. Findings **F14 and F16
→ RESOLVED**. **TASK-711 and TASK-712 left [?] Blocked** — both are product decisions put to the
user rather than guessed.

## [2026-08-07] decision | TASK-711 + TASK-712 unblocked by user → ADR-021, ADR-022; TASK-714/715/716 filed
Both tasks were `[?]` Blocked on product intent. Options and trade-offs were put to the user and
**not guessed**; the ADRs were written only after the answers came back.

**TASK-711 (F11) — plannable-surface boundary.** Decision: **`flashcards` and `dual_translation`
JOIN the planner**; **`listening_lab` and `mystery` stay deliberately outside** (long-form,
exploratory — a daily minute budget fights their design). Dictation's 80-word transcript cap
**scales with tier**. Filed [[decisions/ADR-021-plannable-surface-boundary]] (accepted) and mirrored
the canonical surface × in-planner? × rationale table into [[features/study-plans.tech]].
Two things worth recording that surfaced while writing it: (1) `listening_lab` and `mystery`
**already exist as `dim_test_types.type_code` rows**, so they look plannable to anything reading
that table — documented as a modelling artefact so nobody "fixes" it; (2) `test_time_estimate(
p_skill text)` COALESCEs `dim_test_types.expected_minutes_p50` — **NULL for all 12 type codes** —
onto hardcoded constants ending in a catch-all **`ELSE 5.0`**, so a new plannable surface omitted
from that CASE gets budgeted at 5 min/item **silently**. Same silent-wrong-answer shape as F3.
(Checked before asserting it: the NULL column is *not* a live defect for existing types, since the
fallback constants cover all six — the risk is specific to newly added surfaces.)

**TASK-712 (F15) — day boundary.** Decision: **resolve `_today_iso()` through
`user_study_plans.timezone`** (UTC fallback), rather than keeping UTC or taking the
configurable-offset middle option. Filed [[decisions/ADR-022-local-day-boundary]] (accepted),
which records the four consequences that make this the expensive choice: `daily_test_loads`
uniqueness `(user, language, load_date)` becomes **per-user-derived** (a timezone edit can move
`load_date` backwards onto an existing row, which TASK-705's same-day-safe path reads as a
re-invocation); historical rows carry un-reinterpretable UTC semantics; the date is derived
**independently** in `routes/study_session.py` and `services/test_service.py` today and must
collapse to one shared helper or the two will yield different "today"s in one request; and
`weekly_plan_states.week_start_date` is still UTC `date_trunc`, so the week edge needs the same
treatment or an explicit exemption. Invalid timezone strings must fail safe to UTC (cf. ADR-020).

**No code was changed for either task** — both were decision + documentation only.

**New tasks filed** (the implementation the decisions generated, deliberately *not* folded into the
closed batch): **TASK-714** flashcards + DT as plannable surfaces (L), **TASK-715** tier-scaled
dictation cap (M), **TASK-716** local-day boundary (L). Findings **F11 and F15 → RESOLVED**, so all
of F1–F16 now carry a resolution or an explicit decision.

Wiki: ADR-021 + ADR-022 registered in [[index]] (Pages 97 → 99); daily-session-hardening frontmatter
`total_tasks` 14 → 17 / `done` 12 → 14; master.md recounted a second time — Blocked 5 → **3**
(TASK-534/535/536 only), Done 104 → **106**, Not Started 28 → **31**.

## [2026-08-07] lint | Finding-status sweep on daily-session-implementation-analysis.tech
The TASK-713 lint pass caught a stale-status class the task's own ACs didn't name: **8 of 16
findings (F1–F6, F9, F10) still read as open** although their remediation tasks (TASK-700–705, 707,
708) had been Done since 19–20 July — only F7 and F12 had ever been flipped. All 8 now carry
`✅ RESOLVED (TASK-nnn, date)` with each task's real completion date.

Two were **not** marked resolved, deliberately:
- **F8 — `daily_test_load_items` is dead dual bookkeeping: STILL OPEN, and no task was ever filed
  for it.** It is the only F1–F16 finding with no remediation task in the 700–716 range. Flagged to
  the user rather than silently inventing a task, since removing a table is a decision, not a
  cleanup.
- **F13 — migration/live drift risk: MITIGATED, not eliminated.** TASK-710 verified the live body
  via `pg_get_functiondef` post-apply, but the structural risk (repo file vs live definition can
  still diverge) is unchanged; `phase13_build_daily_session.sql` remains a stale-but-retained
  definer per migrations/CLAUDE.md rule #4.

Final state: 14/16 RESOLVED, 1 MITIGATED, 1 OPEN. Regression check after all edits:
`PYTHONPATH=. pytest -k "daily_load or weekly_plan or study_session"` → **38 passed**; all four
locale JSONs parse.

## [2026-08-08] implement | Exercise Generation v2 — TASK-513, 514(B5), 524, 525

Asked to execute 21 open rows from [[tasklist/archive/exercise-generation-v2.tasks]].
**Four landed; the other 17 were not started** — the batch is multi-day work (four L-complexity
rows, a pgvector migration, two new drill surfaces, frontend players, and a run that needs
operator budget approval). Pages updated: 3. Suite: 1,362 → **1,457 passed**, 3 skipped.

**TASK-514/B5 — per-type L4 gating.** The half-done bug. Level gating could not fix it because
TASK-504 seeded ZH `concrete` with `classifier_match` + `cloze_typed` at L4, so the level
legitimately survives and P3 kept asking Sonnet for Chinese morphology — which it invented.
New `PROMPT3_TYPE_FOR_LEVEL` / `type_is_available` / `prompt3_levels_for_context` gate per
*type*. Gated on both sides: generation (P3 omits the level, and skips the LLM call entirely
when the set empties) and rendering (a stale `level_4` blob of invented ZH plurals cannot
reach the corpus). `validate_prompt3` is held to the gated list so a correct suppression is
not read back as "Missing level_4".

**TASK-524 — sentence-tier hard gate.** New `tier_gate.py`, thresholds in config, running
*before* the paid P1 judge. Two thresholds rather than one: a soft floor with a budget catches
the C2 sentence, a hard floor catches a single very rare word that a budget would let through.
Calibrated empirically — an ordinary A1/A2 sentence scores 0–1 out-of-band, the eval's
coffee-corpus C2 sentence scores 6 (zh) / 8 (ja) / 10 (en). Uses `wordfreq.tokenize`, not
`LanguageProcessor`: the frequency tables were built with it, and it needs no spaCy/fugashi
model — the JA spaCy model is in fact absent from this environment.

**TASK-513 — transcript mining.** Replaced a blind 50-transcript lemma scan with the
`tests_containing_sense` RPC + `vocab_token_map`, so mining is sense-aware. `sentence_source`
is derived by matching against the seed, not taken from the model. **Finding:** ZH recall was
zero on obvious cases — jieba merges 喝+咖啡, so the whole-word check that correctly rejects
咖啡 inside 咖啡馆 also rejected it inside 喝咖啡. Told apart by position (Chinese compounding
is head-final); the suffix case is accepted as a mining-only fallback, not folded into the
shared validator.

**TASK-525 — tl_nl uniqueness judge.** `[~]`, not done: the en/zh/ja prompt migration is
written but **not applied live**, and the judge fails open without it. The load-bearing detail
is rating orientation — the Likert scale runs in the *keep* direction (5 = ideal distractor,
1 = also-correct), because the intuitive phrasing would keep exactly what the judge exists to
remove while the item still looked well-formed. Asserted in tests, flagged DO-NOT-INVERT in
the migration. The TASK-519 AST lint caught an `nl_language_code=''` default on the first
pass, which is what it is for.

Not verified anywhere: nothing was run against live LLMs or the live DB. TASK-514's regen
smoke, TASK-525's 10-sense ZH sample, and the prompt seeding all still need operator spend.

## [2026-08-08] build | TASK-515/516/517/518/521/528 + partial 529/530/532

Batch-execution session over the exercise-generation-v2 tail. Six tasks landed, four
partially, six untouched — see wiki/tasklist/archive/exercise-generation-v2.tasks.md for
per-task status.

**The deterministic package** (TASK-516) is the structural change. `LadderExerciseRenderer`
dispatched one renderer per *ladder level*, which the capability matrix had already
outgrown: ZH L1 is four types, and ZH concrete L4 is classifier_match + cloze_typed where
EN L4 is morphology_slot. Generators now register against a **type_code** and the renderer
walks the matrix rows for the (language, semantic_class) at hand. Adding a type is now a
module plus a matrix row, with no renderer surgery.

New: `services/vocabulary_ladder/deterministic/` — registry, `phonology` (pinyin/kana
confusion sets), `lexicon` (per-language in-memory corpus index, one load instead of ~9,000
round trips per batch), `dictionaries` (shared ZH-classifier / JA-counter index), and
builders for definition_match, hanzi_to_pinyin, pinyin_to_hanzi, kanji_to_reading,
reading_to_kanji, tone_id_word, jumbled_sentence, classifier_match, counter_match,
cloze_typed. `utils/answer_normalization.py` for typed grading.

**Two findings worth recording, both of which would have shipped silently:**

1. `dim_vocabulary.frequency_rank` is a **Zipf score** (range 0.25–6.56, higher = more
   common), not a rank. TASK-515 says "top 1,000 by frequency_rank"; sorting ascending — the
   obvious reading — selects the thousand *rarest* words. The dry run confirms DESC gives
   将/能/国家/大 rather than 酸丁二酯/嗜热菌群. `select_senses` is the only place that decides.
2. The corpus carries non-word lemmas ("1", "₂", "啄む ます た" — a verb glued to two of its
   own conjugation suffixes). Each would have cost three LLM calls to produce an asset that
   fails validation. The hygiene filter is language-aware: internal spaces are legitimate in
   English ("be on time") and are evidence of mis-segmentation in ZH/JA.

Live DB: `dim_word_senses.embedding` + HNSW + `nearest_senses()`; `dim_character_components`;
`dim_counters` / `dim_counter_noun_pairs` / `dim_counter_distractor_groups`;
`v_sense_family_coverage`; `__counter_drill_ja` ELO sentinel. The coverage view immediately
reported 9 of the 10 existing generated senses as having family gaps, which is the point of it.

Tests: `tests/test_deterministic_generators.py` (31). The distractor assertions are the
substance — "produces four options" passes for a generator padding with random words. Two
real defects surfaced: kana vowel-length picked the wrong mora (がっこう → がっこうう instead
of がっこ), and the frequency-band filler gave up instead of widening when a word sat at the
edge of the range, dropping the exercise entirely. `test_p3_type_gating` needed one
assertion tightened — it asserted ZH concrete renders *no* L4 row, true only while that cell
had no generator; it now asserts no L4 row comes from the P3 morphology path.

Full ladder suite: 161 passed.

**Not verified:** no live LLM batch was run — TASK-515's ≥90% acceptance criterion, the
per-chunk judge reject rates and the cost ceiling are all unexercised until an operator
spends on a real chunk. The embedding backfill, the character-component import (needs a
licensed source), and the counter dictionary curation are likewise operator-gated.

## [2026-08-09] build | TASK-520, 522, 523, 526, 527, 531, 533

Seven Exercise-Generation-v2 tasks, all `[ ]` → `[~]`. 1609 tests pass, 3 skipped.

**TASK-520 — L4/L8 out of the P3 monolith.** The audit's B3.2/B3.4 finding was that the
two failure-prone levels shared a `task_name` with the cheap one, and therefore shared a
model, a retry and a JSON parse. Now `ladder_l4_morphology_generation` and
`ladder_l8_collocation_repair_generation` each own a prompt, a model tier (EN L4 stays on
Sonnet, EN L8 drops to flash — a saving that was simply not expressible before) and an
isolated retry.

The part worth remembering is the **schema gate**. The old remaps carried four speculative
branches each — a bare list, an `options` key, a `"1"` key, `"0".."3"` keys — because
nothing validated the response, so a shape drift surfaced weeks later as an empty
exercise. The new gate is keyed by `(type_code, prompt_version)` and **raises** on an
unregistered version rather than falling back. Re-authoring a prompt at v2 without adding
2 to its `PROMPT_VERSIONS` now fails loudly, which is the whole point. All four
speculative branches are deleted, not merely unused, and a test asserts the methods are
gone.

**TASK-522 / TASK-527 — three new exercise types, one new layer.** `syn_ant`,
`word_family` and `particle_selection` are language- or class-specific, so folding them
into a shared prompt would have recreated exactly the coupling 520 spent its budget
undoing. Instead `asset_generators/typed_llm.py` mirrors the deterministic registry:
generators register against a `type_code`, the renderer walks the capability matrix. Each
has a judge whose question is chosen to catch its own also-correct failure:

- syn/ant → *is this foil in the relation to any OTHER sense?* (the "shore"/"bank" trap);
- word_family → *is this "invented" derivation actually a real word?*;
- particles → *does this particle ALSO yield a natural sentence?* (the に/へ trap — asking
  "is it plausible?" gets a yes for all three, which is useless).

Both planted-defect tests the tasks asked for are green. The JA blank is cut only at a
spaCy-confirmed particle span: `str.replace` would blank the に inside にんじん.

**TASK-523 — collocate grounding.** P1 asserts a `primary_collocate` for every sense and
never declines; *advertising* shipped as the collocate of **personalize**. The grounder
grades the assertion and tags it, and the L5 gate now reads that tag instead of running a
second `corpus_collocations` query with its own copy of the PMI threshold. The tag has
three values, not two: `no_source` (Japanese, deliberately) is not `llm_asserted` —
collapsing them would report JA as 0% validated rather than as unmeasured.

**TASK-526 — Traditional serve toggle.** Pure field selection over the TASK-509 mirror.
No OpenCC on the request path, because 發/髮 are both 发 and disambiguating them needs
phrase context only the generation-time converter had. A test parses the module to prove
no converter is imported, so the property survives a future "just this one field" edit.

**TASK-533 — speed round.** Mastered-only, and every other filter exists to keep that
honest. Results feed FSRS but never family confidence: a slow-but-correct answer under a
clock is not evidence that a mastered word has decayed. The tests assert on the *queries*,
not only the output — a composer that filtered nothing would pass an output-only test
given clean fixtures.

**Not verified / operator-gated.** Four prompt migrations are written but **not applied
live** (`ladder_prompt_split_l4_l8`, `syn_ant_word_family_prompts`,
`particle_selection_prompts`). The English collocation list is **not vendored** — OANC is
documented as the source in `data/collocations/README.md`, and until it is installed EN
grounding falls through to `corpus_collocations` alone. The audio backfill spends Azure
quota and has not been run, so its 95% coverage criterion is unmeasured. The syn/ant
embedding band is inert until TASK-521's backfill runs. Nothing yet schedules a speed
round, so the route and player are live but unreachable from the session runner.

## [2026-08-10] reconcile | TASK-638/642/645/647/648 — Evidence-First hardening batch closed

**Operation.** Asked to *execute* the five open Evidence-First Grading rows. Read each task spec,
then checked the source before writing anything — and found all five already implemented,
committed (`git status` on `services/dual_translation/` clean), and covered by tests. This was a
status reconciliation, not an implementation session. No code was changed.

**Evidence, per task** (verified against the source, not just test names):

- **TASK-638** — `render_explanation._generic()` branches on empty `corrected_form` →
  `_GENERIC_ADDITION_EXPLANATION_TEMPLATE` (`"remove: {learner_form}"`). Beyond spec: an *authored*
  template quoting `{corrected_form}` when none exists also falls back, so a seeded taxonomy
  template can't reintroduce the dangling quotation. Drop gate untouched, still AND.
  Pinned by `test_render_explanation_addition_with_empty_correction_omits_correction`.
- **TASK-642** — `grader_cascade._cfg_cache` keyed `'rubric'`/`'taxonomy'` + `clear_caches()`
  mirroring `router.py`. `_fetch_active_config` **raises rather than caching a miss**, so a
  transient outage can't pin a bad read for the process lifetime.
- **TASK-645** — `_resolves_full_marks` is one line; `_normalization_class_equal` deleted, grep
  confirms no callers. The dead code's reasoning survives as the docstring, including the TASK-623
  warning about keying on opcode class rather than `accuracy` (fuzzy tolerance inflates accuracy to
  1.0 on a `replace`).
- **TASK-647** — `_grade_once` under `@retry(stop_after_attempt(3),
  wait_exponential(1, 2, 10), retry_if_exception(_is_transient), reraise=True)`. `reraise=True`
  matters: without it `_grade_with_retry`'s classifier would see `RetryError` and mislabel every
  exhausted item non-transient. Tests patch `runner._grade_once.retry.sleep`, not `time.sleep`.
- **TASK-648** — all three cleanups landed (comment, required `reproduction`/`reference` +
  `if not text:` bypass removed, `cap` parameter gone). Surviving global/local mentions in
  `prompts.py:260` / `eval_metrics.py:47,285` / `synthesis.py:31` are deliberate historical
  references, not stale claims.

**Verification.** `pytest -k "dual_translation or dt_"` → **600 passed**. The four test files named
by the tasks → 113 passed.

**Owed.** TASK-642's Verification also named a live/staging smoke proving one rubric+taxonomy fetch
per activated version rather than per submission. Not run — flagged on the task and in `master.md`
rather than absorbed silently into the Done count.

**Counts.** Evidence-First Grading Not Started 5 → 0 (only TASK-629 `[~]` remains, live rubric-v6
apply owed). Master totals: Not Started 14 → 9, Done 115 → 120. Tasks-file frontmatter corrected
`done: 19` → `28` (was stale by nine).

**Recurrence note.** Third instance of the same drift class — shipped work whose checkboxes were
never flipped (cf. the 2026-07-13 Practice Engine / Study Plans audit, and TASK-609). The tasklist
is not a reliable read of what exists; check the source first.

## [2026-08-10] migration | TASK-629 — rubric v6 APPLIED LIVE (Supabase MCP)

**Operation.** Applied `migrations/dt_rubric_v6_seed.sql` to project `kpfqrjtfxmujzolwsvdq` via
Supabase MCP `apply_migration`, closing the live-apply carry that TASK-629 had held since
2026-07-19 (that session's permission classifier denied every DB-write wire). Live grading now
serves the v3 band descriptors instead of v5.

**Pre-state.** v1/v2/v4 inactive, **v5 active** (7 config keys), no v6 row, no v7+. Guard 1
(anti-downgrade) therefore passed cleanly — this was a straight v5→v6 bump, not a re-apply.

**How it was applied.** The file's outer `BEGIN;`/`COMMIT;` were stripped: `apply_migration`
supplies its own transaction, and a nested `BEGIN` would either warn or commit early. Both
`DO $guard$` blocks were kept and still abort the whole thing atomically inside the wrapping
transaction. Nothing else was altered.

**Verification (the file's own Verification block).** `active_count=1`, `active_version=6`;
`band_descriptors` **differs** from v5 while `weights`, `exemplars`, `acceptable_variation`,
`band_thresholds`, `severity_weights` and `understandability_weights` are all **equal** to v5 —
the descriptors-only contract held. No legacy `content level` suffix survives.

**Transcription check (beyond the file's own verification).** The 46 KB seed had to pass through
the MCP call as a string, so a typo was a real risk — and the v5-equality checks above prove only
6 of the 7 top-level keys, since `band_descriptors` is precisely the new content with no v5
counterpart to diff against. So it was checked independently: every descriptor leaf was extracted
from the live row (4× lateral `jsonb_each`) and from the repo file, canonicalised the same way, and
hashed. **336 leaves and md5 `62e6c6c35b9428fd501dd818eecb8166` on both sides** — the live config
is character-identical to the file. (336 = 6 tiers × 3 langs × 4 bands × dims, with `naturalness`
correctly absent at tiers 1–2 per ADR-018.)

**Post-apply tests.** `test_dual_translation_rubric_v6.py` + gold-seed helper + scoring →
**98 passed**.

**Still flagged, unchanged by this apply.** ZH and JA descriptors remain **AI-drafted and awaiting
native review** (ADR-019 pattern, carried in the seed header and the row description). EN was
user-approved 2026-07-18. Applying the seed does not discharge that review.

**Counts.** TASK-629 `[~]` → `[x]`. In Progress 9 → 8, Done 120 → 121. **Evidence-First Grading
(TASK-620–649) is now fully closed.**

## [2026-08-12] execute | Exercise Generation v2 — TASK-521/530/531/534 closed, 526/535/536 deferred, 515 part-run

**Operation.** Asked to execute the remaining exercise-generation-v2 rows plus a GPL cleanup.
Four of the six code tasks closed, three deferrals recorded with unblock conditions, and
TASK-515 part-run. Suite **1676 → 1718 passed, 3 skipped** (+42 tests, no regressions).

**The theme of this session was silent inertia.** Four separate features were reported as
working and were in fact doing nothing. None of them failed; each degraded into a no-op that
looked, in the logs, exactly like "not run yet". They are listed first because the fixes were
prerequisites for the tasks that followed.

1. **`llm_calls.cost_usd` was never written.** 12,947 rows, zero populated — `_log_llm_call`
   simply omitted the key. `run_generation_batch`'s `--ceiling` projects spend from that column,
   so it computed $0.00 no matter what a batch cost and could never abort; the per-chunk cost
   line, an explicit TASK-515 acceptance criterion, would have printed `$0.0000` forever.
   Spending a $10 authorisation behind a cap that reads zero is not a capped run, so this was
   fixed before any batch spend. `_make_one_call` now sends OpenRouter's usage-accounting flag
   and threads the returned cost through. Verified live (`cost_usd = 0.001638` on a probe).
   11 tests, including the `model_extra` path — the OpenAI SDK's Usage model does not declare
   `cost`, so it arrives in the pydantic extras bag and an attribute-only read returns None
   against the real provider while passing a naive test.

2. **The embedding band check called an RPC signature that has never existed.**
   `sense_neighbours` called `nearest_senses(p_sense_id, p_language_id, p_lemmas)` and read
   `lemma`/`similarity`; the live function takes `(p_sense_id, p_language_id, p_pos, p_k,
   p_cos_min, p_cos_max)` and returns `out_lemma`/`out_similarity`. Every call raised PGRST202,
   caught by a bare `except Exception` and logged at **INFO** as "RPC unavailable" — the same
   line the code emits when the backfill has not run. So TASK-522's band checks were never going
   to fire even after TASK-521 completed. Fixed with a companion function,
   `sense_similarity_to_lemmas`, rather than by repointing: `nearest_senses` *searches* for
   k-nearest, the band check *scores* named candidates, and a foil outside the band must return
   its similarity rather than be omitted from a k-nearest window. Log level raised to WARNING.
   **Fourth instance of the ADR-020 class** (late symbolic reference failing into a silent
   no-op), so the 12 new tests assert the RPC name, its argument keys and its result columns
   rather than just the happy path.

3. **`word_assets_asset_type_check` rejected every typed-LLM asset.** The CHECK enumerated the
   seven pre-TASK-520 types; TASK-522 writes `llm_types_A`/`llm_types_B`, so all of them failed
   with 23514. `_store_asset` catches and logs, so the pipeline reported success per sense while
   `synonym_antonym_match`, `word_family` and `particle_selection` produced nothing — and the
   valid-rate report would still have read ~100%, since it measures the P1/P2/P3 assets that did
   store. The first batch chunk hit it on sense 1 and would have hit all 300 at full LLM cost.
   Replaced the enumeration with a pattern matching how the code builds the value
   (`prefix_variant`); the enumeration is precisely what rotted. Confirmed in the live batch:
   `llm_types_A`/`_B` went 0 → 3 rows each.

4. **The audio backfill read one audio field for all types.** `listening_flashcard` keeps its URL
   in `front_audio_url`, not `audio_url`, so coverage reported **0/56 (0.0%)** over 56 items that
   were already fully voiced, and the text extractor listed four field names present in no such
   row. The write-back used the same wrong key, so any newly synthesised flashcard audio would
   have gone to R2, been recorded where the renderer never looks, and left the item silent *and*
   permanently uncovered — re-burning Azure quota every run.

**TASK-521 — sense embeddings. Done.** 22,348 senses embedded (ZH 8,084 / EN 9,472 / JA 4,792),
**100.00% coverage per language, 0 NULL**, for **$0.0047**. One row failed on the first pass and
was picked up by a re-run, which is what the idempotence was for. Post-fix spot-check over 3
lemmas per language is sane and correctly banded: `precision`/`accuracy` 0.79 IN,
`build`/`construct` 0.88 OUT (near-duplicate), `学习`/`学` 0.95 OUT, `朋友`/`石头` 0.21 OUT,
`食べる`/`飲む` 0.69 IN. *Noted, not fixed:* `車`/`林檎` scores 0.39, just inside the 0.35 floor —
the floor may want raising for JA once real reject data exists.

**TASK-531 — audio at scale. Done.** 8 items synthesised, **0 failures**, nothing queued for
retry. Coverage against the 95% target: ZH `listening_flashcard` **56/56**, ZH
`phonetic_recognition` **2/2**, EN `phonetic_recognition` **16/16** — 100% on every populated
type. JA has no audio-bearing items yet because the batch has not reached it. Azure usage was
8 short utterances, nowhere near the free tier; the per-run cap was set to 50 and never
approached.

**TASK-534 — exercise-type effectiveness. Done (real-data validation deferred).** The "Part F
outcome capture" the task depends on **did not exist**: `user_vocabulary_knowledge` holds only
the current `p_known` and there is no history table, so a per-attempt delta was unrecoverable
after the fact. The BKT RPC already returned `out_p_known_before`/`out_p_known_after` and the
service already read them — they were never persisted. Added both columns (nullable;
pre-2026-08-12 rows cannot be reconstructed and are not fabricated) plus a best-effort capture
that can never fail a learner's submission. `vw_exercise_type_effectiveness` counts only attempts
where BKT ran and time is positive, buckets on `p_known_before` (bucketing on *after* would
manufacture the correlation being measured), and caps per-attempt time at 5 min to match
`_effective_practice_seconds`. Admin page at `/exercise-type-effectiveness`.
**Fixture validation: all 8 hand-computed expectations hold** — and the harness earned its keep
by catching four errors in the *expectations* on first run (a missing 0.200 edge row, a
"6-minute" fixture that hits the 5-minute clamp, and a mis-added delta).

**TASK-530 — JA counter drill.** Route, service, template, both modes, nav and i18n all landed.
Two gaps found: there was **no `counter_drill` row in `dim_test_types`**, and
`get_test_type_id` filters on `is_active`, so every submission would have 500'd — the drill would
have served items and recorded none. Submission reuses `process_classifier_drill_submission`,
which is parameterised by test_id/test_type_id and contains nothing classifier-specific.
Live end-to-end check over a 20-item session: **0 malformed items, 0 answer/distractor overlap,
group-plausible foils** (鹿→頭 against 匹/羽/尾; テレビ→台 against 両/隻/機). Type mode reuses
TASK-532's IME handling verbatim (`compositionstart`/`end` **plus** the `keyCode === 229` guard).
7-test `counter_match` round-trip added, covering the generation→`ladder_record_attempt` join
that the 2026-08-08 session flagged as untested. All 17 new UI strings are in **all four**
locales. **The curation pass is authoring-only and merges nothing without human sign-off** — its
`counts_nouns` gate is already earning its place, declining 方 as counting no showable noun,
which is the error class flagged from the previous pass.

**TASK-515 — batch run. Still open, and the reason is wall clock, not spend.** After the two
fixes above, 7 ZH senses ran for **$0.1645** across 65 logged calls — **~$0.024/sense**, so a
100-sense chunk is ~$2.40 and all three languages ~$7.20, comfortably inside the $10
authorisation. Throughput is the blocker: **~5.5 min/sense ⇒ ~9 hours per 100-sense chunk**,
~27 hours for three. The run was stopped rather than left to burn the session; the runner is
resumable, so the 7 senses are kept. Parallelising the three languages is **not** safe as
written — `spend_since()` sums *all* `llm_calls` since a chunk began, so concurrent runs trip
each other's ceilings on each other's spend. Judge rates over the small sample:
`judge_ladder_p1_sentence` 2 accept / 2 flag / 2 reject (**33% reject**),
`judge_ladder_sentence_validity` 7 accept / 0 reject. **The ≥90% valid-rate criterion remains
unmeasured** — 7 senses cannot settle it, and the 33% figure is a signal to watch, not a result.
One content bug is worth fixing before a long run: the ZH P1 generator returned
`semantic_class: '功能词'` where the schema requires an English enum value, failing validation
and costing a retry.

**GPL cleanup (no spend).** `scripts/cleanup_classifier_data.py` was the last first-party
`zhconv` (GPLv2+) importer; rewritten onto `opencc` (Apache-2.0), matching how
`utils/answer_normalization.py` and `script_converter.py` construct and cache their converter.
Equivalence was *proved* rather than assumed: `zhconv.convert(s, 'zh-cn')` and OpenCC `t2s` were
compared over **3,040 real corpus strings — 0 divergences** — before `zhconv`, `fuzzywuzzy` and
`python-Levenshtein` were uninstalled (none was in `requirements.txt`; all three were ambient).
Dry-run output is byte-identical afterwards.

**Repo-record gaps closed (`migrations/CLAUDE.md`).** `dim_word_senses.embedding`, its HNSW index
and `nearest_senses()` had been live since 2026-08-08 with **no migration file at all**. Now
recorded, alongside three new ones: the widened `asset_type` CHECK, the TASK-534 view + capture
columns, and the `counter_drill` test type. All applied live via Supabase MCP.

**Deferrals recorded, with what unblocks each.** **TASK-526** — code and 27 tests done; the live
發/髮 spot-check needs `content.hant` mirrors to exist, which comes from TASK-509's backfill over
TASK-515 batch senses; verifying against a hand-inserted mirror would test the fixture, not the
pipeline. **TASK-535** — deferred entirely including the replay harness, since a replay needs real
(type, outcome) pairs and capture only began 2026-08-12; unblocked by ~50k attempts plus
TASK-534 returning non-empty cells. **TASK-536** — both halves kept together, since retirement and
preference weighting read the same per-item distribution; unblocked by launch-volume distractor
pick-rates. Retiring items on pre-launch data would deactivate content for having no attempts
rather than for being bad.

**Counts.** In Progress 8 → **5**, Done 125 → **128**.

## [2026-08-16] query | Why zh/ja distractor generation looks weaker and the judge distributions diverge

Pages consulted: 4. Output filed as [[evaluations/distractor-judge-language-divergence-2026-08-16]]
plus [[tasklist/distractor-judge-calibration.tasks]] (TASK-717–722). Pages created: 2. Updated: 2
(index, master).

Question raised from the v4 Likert measurement: all four review-queue flags were English, zh and ja
produced **zero** 3-ratings across 300 distractors, and zh rejected at 30% vs ja 12% / en 4%. Was zh
distractor generation materially weaker, or the zh judge harsher?

**The reject rate is mostly a judge artefact.** Three independent causes, separated from the prompt
text and a re-analysis of the surviving 450-distractor sample:

1. **Not prompt drift.** All three v4 judge templates are faithful translations — same corrective
   paragraph, anchors, worked example, output contract. The zh and ja prompts each *contain* a
   worked band-3 example and the model still never emits a 3. `qwen3.6-flash` uses {5,4,2};
   `gemini-3.1-flash-lite` uses {5,4,3,2}. Band 2 on qwen is a catch-all for "not a clean accept",
   which is why **100% of zh/ja rejects are a 2 and not one is a 1**.
2. **The scale conflates two axes.** Bands 5/4/2 measure topical distance from the passage; bands
   3/1 measure confusability with the answer. Bands 3 and 1 additionally overlap (a near-paraphrase
   of the answer *is* arguably correct). Even the four English band-3 flags are **not** paraphrases
   of the correct answer — gemini is using 3 as a generic "unsure" band, so the whole review queue
   rests on a signal no model applies as written.
3. **The rubric is ill-posed for half the question types.** "Same subject as the passage" is a
   category error for `vocabulary_context` (distractors are competing word senses) and for
   `author_purpose`/`main_idea` (competing intents). zh `vocabulary_context` rejects at **8/16**.
   Excluding that one type: zh 21%, ja 14%, en 5%.

**Two prompt slots are dead in production.** `keywords` (slot `{5}`, the domain the band-2 test
depends on) is accepted by `judge_distractor_plausibility` and **never passed** by its only caller,
`question_generator.py:480`. And slot `{4}` is printed but never acted on, despite
`distractor_plausibility.py:89-93` claiming the type drives sense-vs-fact handling — the behaviour
lives in a docstring and was never written into the prompt.

**Most zh rejects are false.** All 7 non-vocab zh rejects were read individually; ~6 are same-subject
options mislabelled off-topic (推荐回收旧衣服 in a fast-fashion passage; 因为人们不想读书 in a
printing-press passage). Scoring is not merely harsh but **incoherent** — nearer options scored 2
while further ones scored 4–5. Only 金属颗粒 (in a plastic/bacteria passage) is defensible.

**One real content defect, unrelated to the judge.** The zh and ja `question_vocabulary_context`
generator prompts are literal translations that kept the English lexical targets — they teach with
`'bright'`, `'pick up'`, `'turn a blind eye'` and embed English idioms inside their CJK few-shot
passages (「共同'pick up the pieces'」; 「事態を収拾し（pick up the pieces）」). A Chinese
vocabulary-question generator is being few-shotted on English phrasal verbs, a category Chinese
does not have; 成语/惯用语 and 慣用句/四字熟語 are never mentioned. Same defect class as
[[tasklist/ladder-numeric-keys.tasks]] one layer up — English *content* rather than English keys.
Separately, **no generator prompt in any language contains a single line of distractor guidance**:
the rubric exists only on the judge side, so content is filtered against a spec it was never given.

**Reject routing confirmed** (the question left open by the prior session): rejects do **not**
queue. `question_generator.py:498-508` drops the question; `orchestrator.py:66` writes
`generation_review_queue` from `_judge_flags` only. Human review load is **2.7%, not 18%**.

**Caveat recorded:** the measurement harness passed `question_type_id` (a bare integer) into slot
`{4}` where production sends the `type_code` string, so the measured zh reject rate is likely a
mild over-estimate. Any re-measurement must pass the string.

Counts. Not Started 5 → **11**.

## [2026-08-17] evaluation | Answer-entailment judge cross-model A/B (7 arms)
Harness: `scripts/measure_entailment_ab.py`. Sample frozen to
`data/eval/entailment_sample_150.json` (150 questions, 50/lang, rescued from a
prior session's scratchpad). 2700 + 450 judge calls, **$1.05 total spend**.
Filed [[evaluations/entailment-judge-model-ab-2026-08-17]].

**Cost premise refuted.** The expected 5–10× saving does not exist: measured best
case is **2.74×** (`deepseek-v4-flash`). `seed-2.0-mini` is **1.75× dearer** and
`gemini-3.7-flash` **2.1× dearer** than their incumbents despite lower list prices.
Output-token volume, not per-token price, drives this workload. Only measured
`llm_calls.cost_usd` is a valid cost metric here.

**Cost is not the deciding factor anyway.** Production has run 783 entailment
calls all-time (150 in 30 days). Best-case saving today is **$0.025/month**.
Promotions must rest on quality.

**Three models fail in ways no benchmark reveals.** `z-ai/glm-4.7-flash` returned
empty content on **210/450 (47%)** of calls — each one becomes `safe_accept()`, a
silent accept-everything no-op. `stepfun/step-3.5-flash` has no JSON mode.
`qwen/qwen3.5-flash-02-23` returns a bare float. A live pre-flight gate is
mandatory before spending on any candidate.

**Prior finding corrected.** The `response_format='json_object'` 400 was recorded
as breaking 100% of zh/ja calls. Measured: it was **latent, not active** — zh runs
on DeepSeek and ja's `qwen-2.5-72b` upstream does not enforce the rule. It arms
only on Alibaba-Qwen / ByteDance-Seed routing. Audited all 161 active
`prompt_templates` rows: only `test_answer_entailment` is exposed — DT rows are
routing-only (prompt in `services/dual_translation/prompts.py`, sent via
`call_model_with_usage`, no `response_format`), `prose_generation` is `'text'`.
`migrations/entailment_json_token_zh_ja.sql` **applied live** (zh id=150 v1→2,
ja id=151 v1→2; en already compliant); disarm verified — `qwen3.7-flash` now
passes zh/ja where it 400'd. Applied via service-key client, not the migration
runner, so migration history does not yet record it.

**Caveats recorded, not buried.** Labels are structural, not human-adjudicated →
every AUC is a lower bound. Production never sends this judge a distractor, so
**false-reject maps to production but false-accept is a proxy** for answer
hallucination; the ja incumbent's 8% false-accept is a valid cross-arm ranking, not
a production rate.

**Recommendations (none applied — awaiting decision):** en
`gemini-3.5-flash-lite` → `ling-3.0-flash` (AUC 0.974→0.996, false-rejects
3/50→0/50, retires a 32% JSON-repair rate); ja `qwen-2.5-72b` → change on a
structural 4-value score collapse that makes it permanently un-tunable; zh hold
(saturated at 0.999, no quality case).

## [2026-08-17] design | Judge evaluation campaign system — DEFERRED
Designed a generalised ~200-model campaign system (frozen 1000-item gold set,
tiered funnel, self-contained HTML report, explicit + autonomous model selection).
Filed as [[features/judge-eval-campaign]] / [[features/judge-eval-campaign.tech]],
status `planned`, three open questions in frontmatter.

Flat sweep is not executable (200k calls ≈ 35 h); the tiered funnel cuts it to
~35k calls, ~$13, ~4.5 h, sized so n=90 rejects duds and only n=1000 separates
finalists.

**Deferred for two reasons.** (1) More candidates would not change the answer — zh
is saturated, top four within 0.01 AUC; the binding constraint is label quality,
not candidate count. (2) TASK-723's 1–5 Likert migration retires the threshold and
score-distribution metrics, two of the six proposed modules. Recommended
sequencing: human-adjudicate ~100 gold items first, build after Likert lands.

Counts. Not Started 11 → 11 (no new tasks filed; deferral recorded as a planned feature).

## [2026-08-19] task | TASK-723 — entailment Likert v3 rollout verified, ja judge model fixed
Pages updated: 4 (index, log, tasklist/master, tasklist/distractor-judge-calibration).
Pages created: 1 ([[evaluations/entailment-likert-v3-rollout-2026-08-19]]).
Migrations applied live: 1 (`entailment_ja_v3_onto_gemini_3_5_flash_lite.sql`).

**Cutover state.** The tasklist said "staged, NOT activated". It was stale — v3 has been active in
zh/en/ja since 2026-08-19 10:11:32Z (all six rows share that `updated_at`, so one transaction; who
ran it is not recorded), and the Likert code is committed, not working-tree-only. The third move,
the restart that clears the process-lifetime `_cfg_cache`, is **moot rather than skipped**: no app
process exists (only VS Code isort LSP servers; nothing listening on 3000/5000/5001/8000/8080/8888),
so no process can be holding a pre-Likert config and `safe_accept`-ing everything. Next start loads
v3 clean.

**Two premises in the brief were false and are corrected in the wiki.**
1. "No production telemetry — `llm_calls` has zero rows for `test_answer_entailment`." That is the
   `prompt_templates` key; the telemetry label is `judge_answer_entailment` (`judge_` prefix, set at
   `answer_entailment.py:75`). 784 production rows exist. No telemetry gap, no task needed. Recorded
   as established fact #10 because it reads exactly like a missing-instrumentation defect.
2. "No gold set exists, so the v3 re-measurement is blocked." Not for entailment — its gold labels
   are *structural and free* (the correct answer is entailed by construction, its distractors are
   not), which is what `measure_entailment_ab.py` is built on. The blocker is real only for
   *distractor plausibility*, where confusability has no structural label. Filed as **TASK-726**
   with a construction plan (540 items, two-axis labels, native adjudication, published Cohen's κ,
   disagreement-enriched frame with stored reweighting).

**Prompt-abbreviation risk checked and cleared.** zh/en/ja v3 bodies are 402/1101/494 chars and en
is 2.7× zh, which looked like an abbreviated paraphrase in two languages. It is not — the gap is CJK
character density. All three carry the single-axis restriction, five anchored bands, the tie-break
rule and the JSON contract. `audit_prompt_latin.py` CLEAN for zh/ja v2 and v3; the literal `JSON`
token survives in both, so the Alibaba/Qwen `json_object` 400 is not reintroduced.

**Measurement (450 + 300 calls, `pipeline='diag'`, $0.2135 of a $3 budget).** All five bands fire in
all three languages with 0 unparsed responses — a first for this judge family. It works because
entailment is genuinely one axis; the distractor bands still conflate two, so TASK-717's lesson
("anchoring bands does not make a model use them") is not contradicted and TASK-719 stands.
AUC zh 0.990 / en 0.982 / ja 0.870. Best swept threshold is 4.0 for every language and every model
arm, identical to deployed `LIKERT_ACCEPT` — no retune indicated.

**ja was the model, not the language.** Holding the v3 prompt fixed and varying only the model:
qwen-2.5-72b 0.870 AUC / 18% false-accept / 24.7% band-3 load, vs `google/gemini-3.5-flash-lite`
**0.940 / 2% / 2.7%**, vs deepseek-chat 0.798 / 33%. Since zh and en score 0.99/0.98 on the *same*
prompt and ja audits CLEAN, the deficit is neither prompt nor content — the same conclusion TASK-718
reached about qwen. This was the one active judge row `consolidate_gemini_on_3_5_flash_lite.sql`
could not reach, because it swept gemini rows and this one was qwen. Applied live, model column
only, ja v3 body md5 verified unchanged.

**Still open on TASK-723:** "one verdict mapper, not two". `classify()`/`THRESHOLD_*` survive with
one caller and cannot retire until `cloze_distractor_judge` converts, which waits on TASK-719.

Suite: 1806 passed, 3 skipped.

## [2026-08-19] task | TASK-723 follow-up — production entailment path smoked on v3
Pages updated: 1 ([[evaluations/entailment-likert-v3-rollout-2026-08-19]] §0b).
Scripts created: 1 (`scripts/smoke_entailment_production_path.py`).

**The gap:** `measure_entailment_ab.py` calls `call_llm` directly and bypasses the production
wrapper — no `_load_cfg`, no `_is_pre_likert`, no `likert_to_verdict`, no `log_judge_verdict`. So
the day's 750-call measurement validated the prompt and the model but **not the plumbing**, and
`llm_calls` held zero rows at `template_version = 3`. The wrapper was unit-tested and the prompt was
measured; the two had never met on the live row.

**Closed. 6/6 pass across zh/en/ja**, calling `judge_answer_entailment` exactly as
`question_generator.py:500` does. Supported answers rate 5 → accept, unrelated answers rate 1 →
reject, in every language. Four things are now verified rather than assumed:
the version gate does **not** fire (so the judge is judging, not `safe_accept`-ing); ja loaded on
`google/gemini-3.5-flash-lite` through the production loader, confirming the §4 swap; the first
`template_version = 3` rows landed in `llm_calls`; and **`judge_confidence` carries the Likert
rating — 5 on accepts, 1 on rejects, no `0.8` probability constant anywhere.** That last one is the
two-scales-in-one-column collision `null_legacy_judge_confidence.sql` erased 888 rows to clear,
verified closed on the live path.

The smoke deliberately fails on a *missing* rating even for the accept fixture: a dead judge and a
healthy accept are otherwise indistinguishable, which is exactly how this class of defect has hidden
before.

7 calls, $0.00105, logged under `pipeline='test_gen'` (production, not `diag`) — that is what makes
it a production-path proof, and it is visible in production cost reporting by design.

Incidental: the script needed an explicit UTF-8 stdout reconfigure. A Windows cp1252 console raises
`UnicodeEncodeError` on the first CJK reason string and kills the run *after* the LLM has been paid
for. Worth copying into any script that prints zh/ja model output.

## [2026-08-19] task | TASK-726 — distractor gold-set frame built, pre-rated, and weighted
Pages created: 1 ([[evaluations/distractor-gold-frame-2026-08-19]]).
Pages updated: 3 (master, distractor-judge-calibration.tasks, index).
Scripts created: 3 (`distractor_gold.py`, `build_distractor_gold_frame.py`,
`merge_distractor_gold.py`). Scripts modified: 2 (`measure_judge_flag_rate.py`,
`generate_question_sample.py`). Tests added: 37. Suite: **1843 passed, 3 skipped** (was 1806).
Spend: **$0.7266** + ~$0.05 generation, all `pipeline='diag'`.

**Steps 1, 2, 5 and 6 of the construction plan are shipped; step 4 — native-speaker adjudication —
is the only remaining work and has not started.** The frame is **573 items** (zh 213 / en 180 /
ja 180 — above the ≥540 / ≥180 floor), pre-rated by both TASK-718 models, post-stratified to the
production question mix, and split into primary + 60-item overlap labeller sheets.

**Reused rather than regenerated.** `data/eval/task721_before.json` is 179 questions drawn the
same day by `generate_question_sample.py --templates live`, and the TASK-721 rewrite rows are
**staged, not active**, so "live" then is live now. Regenerating would have cost ~$0.57 and ~40
minutes for the same content. One zh cell had failed in that run, leaving zh at 177 items, so a
12-question top-up was generated the same way; `generate_question_sample.py` gained
`--exclude-passages` so the top-up drew passages the first run had not used.

**The disjointness is not an artefact of the frozen sample — it is worse on fresh content.**
Both arms ran the *live* judge prompt for their language (zh v6, en/ja v4) and differed only in
model. qwen rejects 56/573, gemini 3/573, overlapping on **3**. Per language the Jaccard is
zh 0.06 / en **0.00** / ja 0.10 — across 180 English items the two models agree on *zero*
rejects. The band cross-tab shows why no rate could ever have settled it: of the 55 distractors
qwen puts in band 2 ("off-topic, different subject, reject"), gemini rates **35 of them 5**, its
top band, and 16 more a 4. On the disputed population the models are opposites, not mis-scaled
versions of each other.

**Uniform-by-type sampling has been quietly mis-weighting every rate in this workstream.** A
uniform frame gives `supporting_detail` 16.7% when production gives it ~5.2–5.9%, and
`vocabulary_context` 16.7% when production gives it 26–30%. Because rejects concentrate in
`vocabulary_context`, reweighting the live judge to the production mix moves its reject rate
**0.52% → 0.92% (1.77×)**. **TASK-721's §1 "0.6% on fresh output" therefore understates the
production reject rate by ~1.8×** — right about direction, wrong as an acceptance threshold. The
correction is now automatic: `frame_weight` is stored per item and `--gold` applies it to every
published number.

**A contradiction in the task's own plan, resolved.** §1 sizes the frame at 540 and §2
force-includes disagreements *out of* it — which only bites when the frame exceeds the
adjudication budget. Adjudicating all 573 is cheaper in human time *and* removes the enrichment
bias entirely, so `selection_prob` is 1.0 throughout. The enrichment machinery is built and
tested anyway (`--adjudicate N`) because a later top-up may want it.

Three design choices worth keeping: **the labeller CSVs deliberately omit the pre-ratings** (a
gold set anchored to the models it arbitrates is worth nothing); **`confusable = borderline`
returns neither side** rather than being coerced, because that population is what TASK-720 will
redesign the review band around; and **`merge_distractor_gold.py` fires a `[BLOCK]` when κ on
`confusable` lands below 0.60**, naming the label definitions as the defect.

Also landed: `--arms "name=live:model"` resolves the judge prompt version per language, because
zh is on v6 while en/ja are on v4 and no integer spans a three-language arm.

Plumbing smoked end-to-end with *synthetic* labels in the scratchpad (never written to
`data/eval/`): merge, κ gate and `--gold` scoring all run clean, and AUC comes out **0.51** on
random labels — the harness manufactures no signal of its own.

**Blocked on:** adjudication of 573 items plus a 180-item overlap slice, by native speakers, zh
and ja not from translation. Four of seven acceptance criteria wait on it, including the
re-scoring that settles which TASK-718 model was right — now **free**, because the frame was
pre-rated with exactly that pair. TASK-719/720 stay blocked, but the blocker is now one named
file waiting on one named activity.

---

## [2026-08-20] task | TASK-719 + TASK-720 — the distractor judge splits onto two axes; v7 staged, not activated

Executed both tasks together, because they cannot ship apart: TASK-720 redefines a band that
TASK-719 puts on two axes, and both live in the same prompt rows.

**Scope call worth recording.** TASK-719 was blocked on the TASK-726 gold set. The operator
directed the split to proceed and the *scale redesign* to stay parked, and those are separable:
the blocker protects against **retuning cut points** on an unvalidated signal, not against
**asking the judge two questions instead of one**. The staging disposition preserves everything
the blocker was for — the rows are `is_active = false` and nothing changed at runtime.

**What shipped.**

* `schemas.axes_to_verdict(fit, confusability) -> (verdict, axes, rating)`, with `REVIEW_BAND`,
  `FIT_REJECT_MAX`, `CONFUSABILITY_ALSO_CORRECT` and `CONFUSABILITY_INERT_MAX` as named cut
  points. `likert_to_verdict` is untouched — seven other judges share it.
* `DistractorPlausibilityVerdict` gains `fit` and `confusability`; `per_distractor` survives as a
  read-only alias for `fit` and as an accepted input key, so no caller and no existing test moved.
* `JudgeOutcome.axes` / `.flag_axes`, both optional, so the eight single-axis judges are unchanged.
* `orchestrator._flag_reasons` writes `distractor_plausibility:confusability` into
  `generation_review_queue.flag_reasons`; the full per-axis map rides in `judge_scores`.
* v7 prompt rows, zh/en/ja, `[fit, confusability, reason]` triples. zh and ja authored natively
  with `qwen3.8-max` through `rewrite_prompt_native.py`; en written directly.
* `scripts/apply_distractor_judge_v7.py` — writes the rows and reads them back; `--emit-sql`
  generates `migrations/distractor_plausibility_prompt_v7_two_axis.sql` from the same source, so
  the file and the write cannot drift.
* 26 new tests (`tests/test_distractor_two_axis.py`); suite 1843 → **1869 passed, 3 skipped**.

**The compatibility property is the reason this could ship as code-first.** `fit`'s bands are
deliberately identical to the v4 single-axis bands, so a v4/v6 row's single rating lands in `fit`,
`confusability` is `None`, and a `None` axis contributes 'accept'. Verdicts are unchanged until
someone flips `is_active`. The `live` arm in the measurement reproduces the pre-split numbers,
which is the empirical proof. This is the *opposite* of the entailment cutover (TASK-723), where
the two scales inverted at `1`, 77% of historical responses were exactly `1.0`, and the guard had
to be a version gate.

**Measured** live-vs-v7 on the 179-question TASK-721 sample (537 distractors, zh 59 / en 60 /
ja 60), same model in every cell (`google/gemini-3.5-flash-lite`), 358 calls, 1.4 min, **$0.2738**.

1. **Every v7 flag is a confusability flag.** zh 31, en 13, ja 17 — and the fit axis produced
   **zero** in all three languages. The queue no longer says "a judge was unsure", it says "the
   judge could not tell how tempting this option would be", which is a question a reviewer can
   answer. Recording the axis paid for itself immediately.
2. **The fit axis went near-binary.** Zero 3s anywhere; band 4 collapsed (zh 47→2, en 33→10,
   ja 65→2) into band 5. Splitting made the model *more* decisive about subject membership, not
   less — coherent, since the single integer had been absorbing hesitation about both questions,
   but it means fit alone now carries almost no information. Anyone tempted to simplify this judge
   back to one axis would be keeping the wrong half.
3. **The also-correct failure is rare, not newly detectable.** Confusability 5 fires **1/537**
   (0.19%); the old band 1 fired 3/1,800 (0.17%). The same rate. TASK-719's acceptance criterion
   ("detectable on the confusability axis") is met, and the original premise behind it is wrong —
   the revised status note's guess that the case "may simply be rare rather than undetectable" is
   what the data says. **The case for v7 rests on the review signal, not on this catch.**
4. **Review volume is the number the decision turns on.** Question-level: zh **28/59 (47%)**,
   en **13/60 (22%)**, ja **17/60 (28%)**, against live 1.7% / 3.3% / 0.0%. Decomposed, ~75% is
   band-3 uncertainty and ~25% is the new inert rule, which is why `CONFUSABILITY_INERT_MAX` is a
   constant — that quarter can be dropped by setting it to 0 without touching three prompts.
5. Rejects moved little and not in one direction (zh 2→7, en 1→3, ja 2→1 questions); on n=60 per
   language that is not separable from noise.

**Staged rather than activated,** for the same reason TASK-717's v5 and TASK-721's generator spec
were: nothing here is gold-validated, and a 47% zh review rate could be an honest judge admitting
it cannot tell or a prompt that made a confident model timid. No measurement without labels can
separate those. Third build-measure-stage cycle in this workstream. TASK-726 is now the only work
between v7 and a rollout decision, and the split gave it a sharper question to answer than it had.

**Two smaller findings.**

* `rewrite_prompt_native.py`'s `required_literals` check **caught a real defect three times**:
  `qwen3.8-max` wrote the ja output-format section in fluent Japanese and rendered `JSON` as
  ジェイソンオブジェクト. Repaired by substituting the literal back; nothing else touched. Without
  the check this would have shipped as a quietly degraded judge, not an error —
  `response_format='json_object'` needs the token.
* `Spec` gained `render_positional`, because the judge rows use `{0}`-`{5}` and the existing
  `text.format(**render_args)` smoke check cannot render positional slots. It was passing rows it
  had not actually rendered.

**Still owed:** `classify()` and `THRESHOLD_ACCEPT`/`THRESHOLD_REJECT` survive with one caller
(`judges/cloze.py`). TASK-723's last open criterion — "one verdict mapper, not two" — was blocked
on this task settling the axis split. It is settled; `axes_to_verdict` is the template cloze
converts onto. That conversion was not in TASK-719/720's scope.

Pages: [[evaluations/distractor-judge-two-axis-2026-08-20]] (new),
[[tasklist/distractor-judge-calibration]], [[tasklist/master]], [[index]].


---

## [2026-08-20] query | Is the v7 unsure band honest, or did the wording make a confident model timid?

Asked directly by the operator after the TASK-719/720 write-up left it open. Answered, and the
answer is the opposite of the hypothesis.

**Framing correction first.** "The judge is correct" and "the wording made it timid" are not
mutually exclusive, and the comparison the two-axis report rested on could not separate them
because **neither arm is a neutral observer**: v4 says "THIS IS THE NORMAL, EXPECTED RATING —
most good distractors should score 5", v7 says "use 3 whenever you are unsure, do not guess a 4
or a 2". Each prompt contains an instruction sufficient to produce its own distribution.

**The ablation settles it.** Deletion-only edit of all three v7 bodies removing every directional
cue from BOTH ends (`scripts/build_distractor_judge_ablation.py`, every removed span asserted to
appear exactly once and the body asserted to shrink, because a silent no-op would report "the
wording made no difference" and look like a result). Unsure ratings **41 → 83**; flag rate zh
19.8 → 29.9%, en 6.1 → 21.7%, ja 6.7 → 18.1%. Replicates independently in three languages.
The fit axis, which used band 3 **zero** times under v7, starts using it (zh 1, en 7, ja 2) —
so its total confidence was the anchor, not the axis.

Therefore the "use 3 if unsure" nudge is *more than cancelled* by the confidence anchors v7
retained. v7's 22-47% review rate is a **floor** on this model's uncertainty. **The anomaly was
always v4's near-zero rate.**

**Three further findings.**

1. **Temperature 0 is not deterministic on this stack.** v7 measured twice on byte-identical
   content: ja unsure 14 → 12, flag 9.4% → 6.7% — a 30% swing. Nothing in this workstream had
   established that. The two-axis page's per-language rates are corrected to carry ~±3pp; the
   headline 0-3% → 22-47% jump is far larger and survives.
2. **The nudge does not change how much the judge hedges — it changes what lands there.**
   Band-3 reasons contain hedging language at 3-20× the rate of band 2 under v7 (zh 29%, en 20%)
   and barely above their neighbours under ablation (zh 13% vs band-4 12%). Reading them, the
   ablation's band-3 reasons are frequently confident judgments that restate a *neighbouring
   band's definition* ("a careful reader could rule it out" — that is band 4; "most learners
   would rule it out at once" — that is band 2). Without the push the model uses 3 as a
   **midpoint**, not an abstention. That is TASK-720's real achievement and it is a different
   claim from the one recorded there.
3. **The unsure band selects low-surface-overlap items.** Character-bigram similarity to the
   correct answer: bands 1/2/4 order correctly (0.070 / 0.078 / 0.096) and band 3 sits **below
   all of them** (0.039). Not "intermediate on temptingness" — the items where the surface gives
   no signal and the call has to be semantic. The review queue is enriched for exactly the items
   a human is best placed to judge and a cheap model worst.

**A retraction.** An earlier pass flagged a slot-position gradient in the unsure band as a
rating-process artefact. The control kills it — the live arm shows the same gradient on its own
scale. It pre-dates v7 and may not be an artefact at all.

**Defect found and fixed.** `measure_judge_flag_rate.py` parsed the judge's per-distractor reason
text, used it for nothing and dropped it, so **no measurement run in this workstream could be
audited after the fact** and no claim about *why* the judge flagged anything was checkable.
Finding 2 above is the first time it has been looked at and it is the sharpest result here.
Results now store `reasons` and `distractors`. Also added file-backed arms
(`--arms "name=@prefix:"`) reading `data/eval/<prefix>_<lang>.txt`, so a throwaway ablation never
needs a throwaway row in the live `prompt_templates` table — that is how TASK-723 destroyed two
live rows. The prefix is constrained to a bare filename stem.

**Unchanged:** v7 stays staged. The reason has moved — no longer "we cannot tell whether the
judge went timid" (answered) but "a 22-47% review rate is a real workload and nothing yet says
the items in it are the right ones". Only TASK-726's gold set, or per-option learner selection
data, can close that. Spend $0.2980. Suite 1869 passed.

Pages: [[evaluations/distractor-judge-unsure-band-audit-2026-08-20]] (new),
[[evaluations/distractor-judge-two-axis-2026-08-20]] (§1 correction), [[index]].

## [2026-08-21] tasks | TASK-727–730 — fail-closed judging wired into test generation, then measured

Filed [[tasklist/test-gen-fail-closed-judging.tasks]] (4 tasks) and executed all four.

**The gap.** `batch_mode()` — the fail-closed judge guard built after two total outages where a
delisted OpenRouter model slug made every judge `safe_accept()` and a whole batch shipped
unjudged — was wired into `scripts/run_generation_batch.py`, `judges/particle.py`,
`judges/relation.py`, `services/model_health.py` and `vocabulary_ladder/asset_pipeline.py`.
That is exercise generation. **Test generation never entered it**, so a bulk test run with a dead
slug or a missing prompt row wrote unjudged questions to `questions` with nothing louder than a
log warning.

**TASK-727 — wiring, two places not four.** `run()` and `run_batch()` now delegate to
`_run_impl`/`_run_batch_impl` inside `with batch_mode():`, so all four caller modules are covered
and a fifth cannot forget. The wrapper sits *outside* each implementation's `try` — inside it, the
outer `except Exception` would swallow the abort before the guard could mean anything.
`services/ai_service.py` turned out to have no call site at all, only a `# LEGACY:` pointer.

**TASK-728 — the actual work.** `JudgeUnavailable` is an ordinary exception and `orchestrator.py`
has 15 `except Exception` blocks. Classified all of them: **five are on the judge path** (`run()`
per-item and outer, `_process_queue_item` per-difficulty, `run_batch()` per-slot and outer) and
now re-raise; the other ten cannot reach a judge and were left untouched. Without this the abort
degrades into "that one test quietly failed to generate" — *quieter* than the bug it replaces.
Also corrected `question_generator._apply_judges`'s docstring, which asserted "this method never
raises and never blocks the pipeline"; that is now false by design, and the two-contract version
(fail-open serving, fail-closed in a batch, `accept_item` never aborting either way) replaced it.

**Thread fan-out: audited, nothing to do.** `services/test_generation/` has zero
`ThreadPoolExecutor`/`concurrent.futures`/`threading` references and `services/vocabulary/
sense_generator.py` imports no judge, so the thread-local flag has no boundary to cross today.
Recorded as an assumption, because parallelising the generation loop later would silently revert
the workers to fail-open — the original outage wearing a different hat.

**TASK-729 — proof, not a happy path.** 14 tests in `tests/test_test_gen_fail_closed.py`. The
load-bearing ones make an unresolvable judge template abort a real `run_batch()` and assert
**nothing was written** — no test row, no question rows, no queue items marked complete, no
generation_run filed. Counter-tests pin what must NOT change: the same outage outside
`batch_mode()` still fails open and still yields a question, and one unparseable per-distractor
rating still goes through `accept_item` without aborting. Fixtures use difficulty ≥ 3 deliberately
— `run_judges = difficulty > 2`, so a d1/d2 fixture never reaches a judge and would pass against
any amount of broken code. **Both halves of the fix were then reverted to confirm the suite goes
red**: handlers removed → 3 end-to-end tests fail; `batch_mode` wrap removed → 4 fail. Suite
1869 → **1883 passed, 3 skipped**.

**TASK-730 — measured.** 20 tests, en, balanced [1,3,6,9], listening, judges live:
**20/20 generated, 0 failed, 0 vocab shortfalls, $0.175027 ($0.00875/test), 3,532 s
(2.9 min/test).** Judges are 38.2% of spend and rejected 2 questions in 163 billed calls;
the *validator* rejected 17. Extrapolates to ~$8.75 and ~49 h per 1,000 tests — **spend is a
non-issue at any plausible scale; wall clock is the constraint, and 82% of it is vocabulary
enrichment, which is only 16% of the spend.** A d9 test takes 7.3× as long as a d1.

Two query traps found beyond the documented `judge_<name>` namespace one: **`pipeline='test_gen'`
is not the whole bill** (sense generation logs under `vocab_senses` — 16% of every test's cost,
invisible to that filter), and **half the `judge_%` rows are zero-cost verdict-log rows** written
by `log_judge_verdict`, so `count(*)` overstates judge call volume 2× (162/165 reported vs 81/82
real). Costs unaffected; call-volume claims were not.

`test_distractor_plausibility` v7 rows left `is_active = false` throughout, as instructed.

Pages: [[evaluations/test-gen-20-run-2026-08-21]] (new),
[[tasklist/test-gen-fail-closed-judging.tasks]] (new), [[tasklist/master]], [[index]].

## [2026-08-21] tasks | TASK-731 — DT spaced remediation, dead three ways, now live

Dual Translation's Feature 2 (error synthesis + spaced remediation) had never once run end to
end. Three independent breaks, fixed in the only safe order.

**1. The migration was never applied.** `migrations/dt_cards.sql` (TASK-612, dated 2026-07-14)
created `dt_card` and `dt_card_review`; neither table existed in project `kpfqrjtfxmujzolwsvdq`.
Applied 2026-08-21 and verified against the migration's own trailer: **16 columns on `dt_card`,
5 on `dt_card_review`, 3 FKs + 1 FK, 6 indexes**, RLS off matching its siblings.

Order mattered. `services/dual_translation/cards.py:267` early-returns before touching `dt_card`
when a user has no `queued` profile entries — the sole reason a missing table was latent rather
than a live 500. Scheduling synthesis *first* would have promoted clusters, ended the
early-return, and armed `GET /next` to fail on ~25% of calls and `/cards/due` on every one, with
the Practice Engine swallowing it as a `logger.warning`.

**2. Nothing scheduled the synthesis.** `app.py::_initialize_scheduler` registered 5 jobs; the
nightly runner was not among them, though `routes/dual_translation.py:215` documents it as "the
nightly job". Ruled out an external scheduler before writing anything: `Procfile` declares only
`web:`, there is no `app.json`, the one GitHub workflow has no `schedule:`, and **`pg_cron` is
not installed** on the live project. The gap was real.

Added `dt_error_synthesis_nightly` at **03:50 UTC** — ahead of the 04:00–04:15 chain so a
promotion is carded before the morning's first `GET /next`. APScheduler runs in both gunicorn
workers, so the job takes a Postgres advisory lock, key **1146377081** (`0x44545379` = `DTSy`),
distinct from Study-Plan `1467840848` and IRT `8901234567890123`
(`migrations/dt_synthesis_advisory_lock.sql`, applied live).

**3. No frontend renderer, on any of the three surfaces.** New shared global
`static/js/dt-error-card.js` (`window.DTErrorCard`), following the `ExRenderers` pattern because
the standalone page is a classic `<script>` IIFE while the two session players are ES modules.
Consumed by the daily-session DT player (its `MAX_ERROR_CARD_RETRIES` workaround and stale
comment removed), the standalone page (new `errorCard` phase), and the practice player (which
now keeps `is_error_exercise` items instead of filtering them out). Grading goes to
`POST /api/dual-translation/cards/<id>/review`, never `/api/practice/attempt`. 17 new keys in all
four `static/i18n/*.json`.

### Three findings

* **A `[x]` claiming a live migration is worth nothing without the live schema.** 30
  migration-defined tables checked; `dt_card` and `dt_card_review` were the only two missing — an
  isolated miss, not systemic drift, but it silently invalidated TASK-612/614/615/618.
* **The nightly runner had never been executed even once, by anyone.** `main()` called
  `get_supabase_admin()` without `SupabaseFactory.initialize()` — every other script in
  `scripts/` does. The CLI path raised `SupabaseFactory not initialized` immediately. Only the
  in-app scheduler path (where `_initialize_services` runs first) would ever have worked. Fixed
  with a shared `_get_db()`.
* **Grader `span_reference` and `corrected_form` drift apart, and it produces broken cards.**
  Live card 3 blanked `很贵的牌子，` while its answer was `也不是最新款式的` — a different clause —
  so the prompt *contained its own answer*: a copying exercise, not productive recall. 1 of 2 live
  cloze cards affected. `build_cloze_card` now realigns to a unique verbatim occurrence of
  `corrected_form` (conservative: ambiguous or absent → keep the grader's span), and `build_cards`
  drops a cloze that would still leak, leaving the isolate card to cover the subtype. **The
  underlying span-discipline defect is NOT fixed** — that is TASK-624's remit and an LLM-output
  quality problem, not a rendering one. Worth a follow-up task.

### Verification

Suite **1883 → 1904 passed, 3 skipped, 0 failed** (+21); vitest **66 → 90** (+24).
Revert-checks, per the TASK-729 convention that a happy path is not evidence a guard fires:
unregister the scheduler job → **2 fail**; remove the advisory-lock guard → **1 fail**; invert the
answer target to `learner_form` → **1 fail**; point grading at `/api/practice/attempt` →
**4 fail**; disable span realignment + leak guard → **2 fail**. All restored to green.

Live, against real data on the developer's own account: synthesis loaded all 16
`dt_error_instance` rows and wrote **4 `dt_error_profile_entry` rows (2 promoted to `queued`)**;
materialisation produced **4 `dt_card` rows** and was idempotent on re-run (0 carded);
`GET /next` returned **200 `type=error_card`**, `/cards/due` **200 with 4**, and
`POST /cards/<id>/review` **200**, advancing FSRS to `state=review, stability=2.4,
next_due=2026-08-23`. Rating `9` correctly rejected **400**; the passage branch still returns
`type=passage`. The synthetic review was then deleted and the 4 cards reset to `new` so nothing
pollutes the recurrence metric.

**Caveat on the default window.** With the default `DT_SYNTHESIS_WINDOW_DAYS=30` the sweep writes
**nothing**: every live error is from 2026-07-02, ~50 days old. The 4 rows above required
`--window-days 60`. Not a bug — the counting window is doing its job — but it means the nightly
job will legitimately no-op until fresh DT grading traffic exists.

Pages: [[tasklist/master]], [[log]].

## [2026-08-21] tasks | DT span↔form invariant — grader cleared, 16 rows backfilled, tripwire filed

Follow-up to TASK-731's third finding. That entry closed with "**The underlying span-discipline
defect is NOT fixed** — that is TASK-624's remit and an LLM-output quality problem, not a
rendering one." **That conclusion was wrong, and this entry corrects it.** There is no
prompt-quality defect. There never was one after 2026-07-19.

### The decisive check, which TASK-731 never ran

Fed the exact inputs behind the leaking card (`dt_error_instance` id 5 — `span_reference`
`[23, 29]` slicing `很贵的牌子，` while `corrected_form` was `也不是最新款式的`) through the
*current* `_reconcile_span_form`. It relocates to **`[29, 37]`** — precisely where the corrected
form sits — and repairs the reproduction span `[21, 28] → [23, 31]` as well. The grader is clean.

The timeline explains everything: `git log -S_reconcile_span_form` puts its introduction in
**7e46e4ae, 2026-07-19**. Every live `dt_error_instance` row was written **2026-07-02**. The 16
rows predate the fix by 17 days; they went through the un-reconciled decoder and were never
revisited. TASK-731 diagnosed live data as live behaviour.

### Repair at the source

`scripts/dt_backfill_error_spans.py` (new) re-runs the current reconciler over persisted rows and
rewrites `span_reference`/`span_reproduction` in place (and the form, where a normalization-folded
match changes it). Dry-run by default; `--apply` writes; idempotent.

Applied live: **16 rows | ok=1 repaired=15 unrepairable=0**. Post-check in SQL:
`ref_aligned = 16/16`, `repro_aligned = 16/16`. Every corrected form was present verbatim in its
own text, so nothing needed quarantining — the script still classifies and flags an unrepairable
row rather than half-writing it, since the current grader would have dropped such an error
outright.

Downstream artefacts were then checked rather than assumed: all **4 live `dt_card` rows rebuild
byte-identical** from the repaired sources, and neither cloze now trips the leak guard. No card
regeneration required.

### The actual gap: a tripwire, not repair logic

`_reconcile_span_form` *establishes* the invariant `reference[span_reference] == corrected_form`
(and the reproduction-side equivalent) but nothing anywhere **asserted** it had been established.
That absence is what let 15 misaligned rows sit for seven weeks and surface only as a broken card.

`tests/test_dt_error_span_invariant.py` (new, 18 tests) is that assertion, at two levels: over
`_decode_error`/`_decode_errors` output across a 10-case adversarial matrix (off-by-one at either
end, drift to a different clause, repeated token, out-of-bounds, malformed end, full-width fold,
casefold, two zero-width omission points), and over the rows that actually reach the
`dt_error_instance` insert via `_persist_grade` — the "every persisted row" form. Each matrix case
is pinned to **survive** decode, so the invariant can never be satisfied vacuously by dropping,
and a counter-test pins that an unlocatable form is still dropped rather than written misaligned.

**Revert-check.** Replacing `_reconcile_span_form` with the pre-TASK-624 pass-through takes the
file from **18 passed → 13 failed, 5 passed**. One test bakes that in permanently: it neuters the
reconciler via monkeypatch and asserts the invariant raises. Suite **1904 → 1922 passed,
3 skipped, 0 failed** (+18).

### The card-level guard is demoted, not removed

`_blank_span_for` and the drop-if-leaking check in `build_cards` stay, but their docstrings no
longer claim the grader "does not always keep `span_reference` and `corrected_form` aligned" —
that is now false. They are documented as **belt-and-braces**: cheap insurance against a
disproportionate failure (a cloze card showing its own answer tests nothing), explicitly not the
primary remedy. The leak WARNING is now re-framed as a regression signal — if it ever fires, the
upstream invariant has broken.

### Finding

**A guard written against live data is only as good as the dating of that data.** TASK-731 saw a
real broken card, correctly localised it, and then generalised from 16 rows to the live grader
without checking when those rows were written or feeding them back through the current code. The
one-line check — run the repaired function over the input that broke — was never run, and it
inverts the conclusion.

Pages: [[log]].

---

## [2026-08-22] fix | TASK-735: ja L1 fabrication, judge strictness, and the P1 write-off

Three defects from the `ja-20260822-232552` canary. Six `judge_ladder_l1_distractor` calls,
18 distractors, **17 rejected** — and because `_render_phonetic` drops the whole variant below
3 surviving distractors, ja produced **zero** L1 exercises rather than weakened ones.

### The generator was inventing words, and the mechanism was orthographic

Sense 34997 (昔) variant B emitted `向こうし` and `無蚊地`; the model's own explanation asserted
無蚊地 was "an existing word (a place name etc.)". Variant A, which answered in kana, invented
nothing. The prompt said nothing about how to **write** an option, so having committed to a kanji
surface the model composed kanji until the reading fitted. `vocab_prompt2_exercises` [ja] v1 → v4
adds an attestation gate, an orthography rule, a one-mora contrast rule, and a mora-substitution
search procedure. Measured: fabrication 2-of-6 → **0-of-7**.

### The generator and the judge disagreed about pitch accent — the judge was right

The generator *preferred* accent-only homophones (`はし(箸)`/`はし(橋)`); the judge rejected them as
`完全同音で区別不能`. L1 audio is a single TTS rendering, so an accent-only contrast is undecidable
for the learner. Both rows now forbid it.

### The judge's keep-list was closed where en's is open

`ladder_l1_distractor_judge` [ja] v2 admitted exactly four contrast types, none of which is the
ordinary one-mora minimal pair — so むかし/むかえ died with `最小対立の条件を満たさず`, correctly by
its own rules. The en row (id 173) never had this bug. v3 restores the general case. Controlled
A/B on the recorded sets, same model, temp 0: **v2 kept 0/12, v3 kept 5/12, zero false keeps**.
With the judge fixed but the generator untouched, 0 of 4 variants still rendered — confirming the
brief's ordering.

### Exactly-3 distractors demanded a 100% hit rate

L1 now over-generates (4–6 options; the learner still sees 4). This needed `validators.py` to stop
pinning every option level at 4 — the renderer reads only `is_valid=True` assets, so an
over-generated L1 would have taken L3/L5/L6 down with it. `OPTION_COUNTS` relaxes **L1 only**,
because L1's distractors are the only ones individually judged before rendering.

### The P1 threshold was not the problem

`P1_MIN_ACCEPTABLE_SENTENCES = 6` did not misfire. Sense 34999 (一/いち) was blocked because all ten
sentences rated 2 with `対象語が全単語で現れない` / `接頭辞として使用` — 一 is a bound numeral that
never stands alone. Loosening the threshold would admit sentences where the target is a character
fragment, poisoning every level L3–L9 that inherits them. The real defect is upstream: bound
morphemes (一, 様, 度 — ~15% of the pool) sit in the ja sense pool, and `phase_select` ranks by test
frequency, which puts them at the **top** of the selection. `part_of_speech` cannot gate it — 一, 度
and 人 are all `名詞`. Left open as a sense-pool decision.

### Finding

**A closed enumeration in a judge prompt is a silent allow-list.** The ja judge's four contrast
types read as guidance but functioned as an exhaustive list, and the model obeyed the list over the
concept — rejecting the textbook case the level exists to teach. The en row survived only because
its taxonomy was phrased openly. Where two prompts rule on the same artefact, the second failure
mode is worse: the ja generator and judge disagreed about pitch accent for a day of real running,
and the disagreement was invisible because each was internally consistent.

Full suite: 1965 passed, 2 skipped. Review: `.claude/reviews/task735-ja-l1-fixes.md`.

Pages: [[log]].
