---
title: Daily Session Modules (include / exclude) — Technical Specification
type: feature-tech
status: planned
prose_page: ./session-modules.md
last_updated: 2026-10-12
dependencies:
  - "table: user_study_plans (new column excluded_modules)"
  - "table: dim_study_plan_templates (read: weekly_test_counts, practice_total_minutes)"
  - "table: weekly_plan_states, daily_test_loads (written by existing RPCs)"
  - "RPC: build_daily_session (redefined)"
  - "RPC: compute_weekly_plan_persist (unchanged — replace semantics on target_counts)"
  - "service: services/study_plan_service.py (Tier B)"
  - "routes: routes/study_plan.py, routes/study_session.py"
  - "service: services/test_service.py (legacy fallback)"
  - "template: templates/study_plan.html + static/i18n/{en,zh,ja,es}.json"
breaking_change_risk: medium
---

# Daily Session Modules — Technical Specification

## Architecture Overview

A **module** is a daily-session planning unit. The module vocabulary is the union of the
`dim_study_plan_templates.weekly_test_counts` keys and the literal `practice`:

| Module key | Kind in Tier C | Languages (via template keys) | Scaled on redistribution |
|---|---|---|---|
| `reading` | test | all | yes |
| `listening` | test | all | yes |
| `dictation` | test | all | yes |
| `pinyin` | test | zh | yes |
| `classifier_drill` | test | zh | yes |
| `pitch_accent` | test | ja | yes |
| `flashcards` | surface | all | **no** (one block/day, sized by due cards) |
| `dual_translation` | surface | all | yes |
| `practice` | maint + acq practice chunks + speed-round tail | all | yes |

`listening_lab` and `mystery` are *not* modules. They are outside the planner by ADR-021 and are
pinned by `tests/test_plannable_surfaces.py`.

Exclusion is applied at **two layers**, per [[decisions/ADR-032-session-module-exclusion]]:

```
PUT /api/study-plan {excluded_modules}
   │  validate → UPDATE user_study_plans.excluded_modules
   │
   ├─► Tier B  StudyPlanService.compute_weekly_plan(current local week)
   │     apply_module_exclusions(template)  ← drops excluded keys, rescales the
   │       rest so total template minutes are preserved
   │     → allocate_test_counts / rebalance_practice / carry-over (unchanged math)
   │     → compute_weekly_plan_persist (REPLACES target_counts → excluded keys gone)
   │
   └─► Tier C  build_daily_session(user, lang, local_today)  [only if today's row exists]
         reads v_plan.excluded_modules and filters target_counts, practice,
         retry and word_upload (defence in depth: a stale or failed Tier B
         recompute still never schedules an excluded module).
         TASK-705 re-entrancy keeps today's completed slots.
```

Tier B is where the *time* is redistributed. Tier C is only a filter. If Tier C dropped an
excluded skill without Tier B having rescaled, the TASK-732 budget split would give that time
to the other side (test ↔ practice) instead of to the remaining modules.

## Database Impact

### Migration `migrations/session_module_exclusions.sql` (new)

```sql
BEGIN;

ALTER TABLE public.user_study_plans
    ADD COLUMN IF NOT EXISTS excluded_modules text[] NOT NULL DEFAULT '{}'::text[];

-- Known module vocabulary. Mirrors services/study_plan_service.py::ALL_MODULES.
-- Adding a module means changing both, and test_session_modules.py pins that they agree.
ALTER TABLE public.user_study_plans
    ADD CONSTRAINT user_study_plans_excluded_modules_known
    CHECK (excluded_modules <@ ARRAY[
        'reading','listening','dictation','pinyin','classifier_drill',
        'pitch_accent','flashcards','dual_translation','practice'
    ]::text[]) NOT VALID;

COMMENT ON COLUMN public.user_study_plans.excluded_modules IS
    'Modules left out of daily-session planning (Tier B + Tier C) for this language. '
    'Does not restrict manual use. See wiki/features/session-modules.tech.md.';

COMMIT;

ALTER TABLE public.user_study_plans
    VALIDATE CONSTRAINT user_study_plans_excluded_modules_known;
```

- The `NOT VALID` + separate `VALIDATE` follows `migrations/CLAUDE.md`. The table is small, but
  the rule is cheap to follow. Every existing row gets `'{}'`, which satisfies the CHECK.
- The language-specific rules ("pinyin only for zh" and "at least one module left") are **not** in
  the DB. They depend on the template, so they are enforced in the route (see API below). The
  CHECK only rejects unknown strings.
- No RLS change. The existing `user_study_plans_self_modify` policy covers the column.
- No index. The column is only ever read by PK lookup.

### Migration `migrations/session_module_exclusions_build_daily_session.sql` (new)

This file redefines `public.build_daily_session(uuid, smallint, date)`.

**Start from the live definition, not the repo file.** Dump it with
`pg_get_functiondef('public.build_daily_session(uuid,smallint,date)'::regprocedure)` and confirm
it contains the `word_upload` marker. The current canonical repo file is
`migrations/word_upload_slot_scheduling.sql`. That file also adds
`user_word_watchlist.last_matched_surfaced_at`, so by rule 4 of `migrations/CLAUDE.md` it is
**not archived**. Add a header note to it saying the function body is superseded by the new file.

Edits (each tagged `-- session-modules` in comments):

1. Add `v_excluded text[];` to DECLARE. After the `v_plan` lookup, set
   `v_excluded := COALESCE(v_plan.excluded_modules, '{}'::text[]);`.
2. Add `WHERE tc.skill_key <> ALL(v_excluded)` to the TASK-732 `v_test_minutes_total` sum.
3. Wrap the `v_practice_minutes_total` computation:
   `IF 'practice' = ANY(v_excluded) THEN v_practice_minutes_total := 0; ELSE … END IF;`
4. In the test/surface candidate INSERT (`FROM jsonb_each_text(v_state.target_counts) … generate_series`),
   add `WHERE tc.skill_key <> ALL(v_excluded)`.
5. Guard both practice candidate INSERTs (`'maint'`, `'acq'`) with
   `WHERE NOT ('practice' = ANY(v_excluded))`.
6. In the TASK-704 retry SELECT, add `AND dtt.type_code <> ALL(v_excluded)`.
7. In the word_upload SELECT, add `AND dtt.type_code <> ALL(v_excluded)`. This sits inside the
   `JOIN dim_test_types` predicate's WHERE, so a multi-skill test can still be served as one of
   its non-excluded skills, since the ELO-closeness ORDER BY picks among the remaining rows.
8. Leave the TASK-705 carry-over block unchanged. Completed slots of a now-excluded skill are
   retained as completed (prose: "Completed today, then excluded").
9. Add `'excluded_modules', to_jsonb(v_excluded)` to the `daily_session_targets` object. This is
   for observability, and the session route also reads it to gate the speed round.

With `practice` excluded, steps 3 and 5 give `v_practice_budget = 0` and
`v_test_budget = v_today_budget`. With every test/surface module excluded, `v_test_minutes_total`
is 0 and the whole day goes to practice. Both cases fall out of the existing TASK-732 formula
without new branches.

**Surfaces.** The `surface_budget` / `surface_counts` hydration reads `skill_counts`, which only
holds skills that survived step 4. It needs no change.

## Tier B — `services/study_plan_service.py`

### New constants

```python
MODULE_PRACTICE = 'practice'
# Module vocabulary. MUST equal the SQL CHECK user_study_plans_excluded_modules_known.
ALL_MODULES = (
    'reading', 'listening', 'dictation', 'pinyin', 'classifier_drill',
    'pitch_accent', 'flashcards', 'dual_translation', MODULE_PRACTICE,
)
# Modules whose weekly count is NOT rescaled when others are excluded:
# flashcards is one review block a day whose real size is set by due cards.
NON_SCALABLE_MODULES = ('flashcards',)
```

### `apply_module_exclusions(weekly_counts: Dict[str, int], practice_total_minutes: int, excluded: Iterable[str], minutes_of: Callable[[str], float]) -> Tuple[Dict[str, int], int]`

- **Purpose:** Remove excluded modules from the template and rescale the scalable remaining
  modules (test counts and practice minutes) by one common factor. This preserves the template's
  total minutes and its relative mix.
- **Arguments:**
  - `weekly_counts`: the template's `weekly_test_counts`.
  - `practice_total_minutes`: the template's `practice_total_minutes`.
  - `excluded`: the plan's `excluded_modules`. Keys absent from the template (other than
    `practice`) are ignored.
  - `minutes_of`: per-slot minutes, i.e. `lambda s: _test_time_estimate(s, self.db)`, memoised
    per call.
- **Algorithm:**
  1. `ex = set(excluded)`. `kept = {s: c for s, c in weekly_counts.items() if s not in ex}`.
     `practice_kept = 0 if 'practice' in ex else practice_total_minutes`.
  2. If `ex` does not intersect `set(weekly_counts) | {'practice'}`, return the inputs unchanged.
     This short-circuit makes the default plan byte-identical to today's behaviour.
  3. `M_total = Σ_all c_s·m_s + practice_total_minutes`.
     `M_fixed = Σ_{s ∈ kept ∩ NON_SCALABLE} c_s·m_s`.
     `M_scalable = Σ_{s ∈ kept \ NON_SCALABLE} c_s·m_s + practice_kept`.
  4. If `M_scalable == 0` (only flashcards left), return `(kept, 0)` with no redistribution. The
     prose documents this "short session" edge case.
  5. `k = (M_total − M_fixed) / M_scalable`. Here `k ≥ 1` because `M_total − M_fixed ≥ M_scalable`.
  6. Scalable counts use **largest-remainder rounding**. `raw_s = c_s·k`,
     `N = round(Σ raw_s)`, and each `count_s = floor(raw_s)`. Hand the remaining `N − Σ floor`
     units one by one to skills ordered by `(raw_s − floor(raw_s))` descending, then by skill
     key ascending (deterministic). Every kept skill keeps `count_s ≥ c_s ≥ 1`.
  7. `practice = round(practice_kept · k)`.
  8. Return `({**fixed_kept, **scaled}, practice)`.
- **Returns:** `(adjusted_weekly_counts, adjusted_practice_total_minutes)`.
- **Errors:** none. The function is pure and deterministic.

### `compute_weekly_plan` changes

- Plan SELECT adds `excluded_modules`.
- After loading the template, call
  `weekly_template, practice_total = apply_module_exclusions(template['weekly_test_counts'], template['practice_total_minutes'], plan.get('excluded_modules') or [], minutes_of)`
  and use these two values everywhere the raw template values are used today: the weakness loop,
  bandit scores, `allocate_test_counts`, and `rebalance_practice(practice_total_minutes=…)`.
  The ±50% floors and ceilings therefore apply around the *adjusted* counts.
- If `'practice' in excluded`, skip `rebalance_practice`. Set `practice_minutes = 0`,
  `maint_share = base_maintenance_share`, `acq_share = 1 − base_maintenance_share`. The shares are
  persisted for schema compatibility only and are unused at 0 minutes.
- Carry-over: the test loop already iterates `target_counts` keys, so excluded skills get no
  carry-over automatically. Apply practice carry-over only when practice is not excluded.
- `weakness_global` is averaged over the kept skills only (it already is, since `skill_weakness`
  is built from `weekly_template`).
- The weekly ceiling clamp (`daily_minutes·7`) is unchanged.

### `StudyPlanService.rebuild_today(user_id, language_id) -> bool` (new)

- **Purpose:** Re-resolve today's not-yet-completed slots after a settings change.
- **Behaviour:** `local_today = plan_today(self.db, user_id, language_id)`. If a
  `daily_test_loads` row exists for `(user, lang, local_today)`, call
  `self.build_daily_session(user_id, language_id, local_today)` and return `True` unless the
  result has an `error` key. If no row exists, return `False`, because the next
  `GET /api/study-session` builds a fresh day anyway.
- **Side effects:** `build_daily_session` UPSERTs `daily_test_loads`. `test_ids` and
  `daily_session_targets` are replaced. `completed_test_ids` and `completed_blocks` are kept
  (TASK-705). `daily_test_load_items` is rewritten. word_upload keeps its surfaced stamp
  (COALESCE-guarded).

## API / RPC Surface

### `GET /api/study-plan?language_id=L` (modified)

- The plan SELECT adds `excluded_modules`.
- The response adds `available_modules: string[]`. This is the ordered union of the keys of
  **every** template for the language (so it is stable across template switches), filtered to
  `ALL_MODULES`, then `'practice'` appended. Order follows `ALL_MODULES`.

### `PUT /api/study-plan` (modified)

- **New body field:** `excluded_modules?: string[]`.
- **Validation** (new helper `_validate_excluded_modules(value, available) -> list[str] | None`):
  - Must be a list of strings. Return 400 `"excluded_modules must be a list of module codes"`.
  - De-duplicate, then sort by `ALL_MODULES` order.
  - Every element must be in `available` for this language. Return 400
    `"unknown module for this language: <code>"`.
  - `set(available) − set(excluded)` must be non-empty. Return 400
    `"at least one module must remain included"`.
- **`is_template_only`:** add `'excluded_modules'` to the tuple of "other fields", so a request
  carrying it is never treated as template-only.
- **After a successful UPDATE**, and only when `excluded_modules` was in the request *and* differs
  from the stored value, run both steps best-effort:
  1. `StudyPlanService(db).compute_weekly_plan(user, lang, _monday_of(plan_today(db, user, lang)))`.
     Use the learner-local week, not the server-date `_monday_of(date.today())` that the
     template-only branch uses today. That branch is left as-is (out of scope).
  2. If `Config.STUDY_PLAN_ENABLED`, call `StudyPlanService(db).rebuild_today(user, lang)`.
  - A failure in either step logs a WARNING and does not fail the PUT. The settings are saved,
    and the lazy paths recover tomorrow.
- **Response adds:** `session_rebuilt: bool`.
- **Auth:** unchanged (`supabase_jwt_required`, user from `g.current_user_id`).

### `GET /api/study-session` (modified, `routes/study_session.py`)

- `speed_round_available` is forced to `False` when `'practice' in (targets.get('excluded_modules') or [])`.
  `targets` is today's `daily_session_targets`, which the session route already reads. This
  needs no extra query.

### Legacy fallback `TestService._compute_daily_load` (modified)

- When a `user_study_plans` row exists for `(user, lang)`, read its `excluded_modules` and drop
  candidates (poor-performance retries and recommended tests) whose `test_type` is in it.
  When no row exists there are no exclusions.

## Component Specification (UI)

### `templates/study_plan.html` — new card "Daily session modules"

- **Placement:** inside `#planEditor`, between the "Weekday shape" card and the "Advanced" collapse.
- **Markup:** `<div id="moduleToggles">`, with one Bootstrap `form-check form-switch` per entry of
  `available_modules`. Use `input.module-toggle[data-module=<code>]` and the label
  `T('study_plan.modules.<code>')`. Checked means **included**.
- **State:** derived from `plan.excluded_modules` on `showPlanEditor`. Re-evaluate on every
  change. When exactly one toggle is checked, disable it (`disabled` + `title` =
  `T('study_plan.modules.last_one')`). When the only checked toggle is `flashcards`, show
  `#moduleShortHint` (`T('study_plan.modules.flashcards_only_hint')`).
- **Hint text** under the heading: `T('study_plan.modules.hint')`, which reads "Excluded modules
  are only left out of your daily session — you can still use them any time from the rest of
  the app."
- **Save:** the existing `#saveBtn` handler adds
  `excluded_modules: [...unchecked data-module values]` to the PUT body. On success, if
  `session_rebuilt` is true, the banner uses `T('study_plan.modules.session_rebuilt')`.
- **Skill overrides:** no change. They already derive from `current_week.target_counts`, which
  no longer contains excluded skills after the recompute.
- **i18n keys** (add to `static/i18n/{en,zh,ja,es}.json`): `study_plan.modules.title`,
  `.hint`, `.last_one`, `.flashcards_only_hint`, `.session_rebuilt`, and one label per module
  code (`.reading`, `.listening`, `.dictation`, `.pinyin`, `.classifier_drill`, `.pitch_accent`,
  `.flashcards`, `.dual_translation`, `.practice`).

## Key Architectural Decisions

1. **Decision:** Store exclusions as `user_study_plans.excluded_modules text[]`.
   - **Rationale:** The setting is per language (ADR-011). The plan row is already the
     per-language settings record and is already read by both tiers.
   - **Alternatives rejected:** a separate `user_session_modules` table, which would add a join
     for one array. A global `users` column was rejected because the developer chose per-language
     scope, and language-specific modules make a global list awkward.
2. **Decision:** Redistribute in Tier B with one common scale factor, and filter in Tier C.
   See [[decisions/ADR-032-session-module-exclusion]].
3. **Decision:** `flashcards` is not rescaled.
   - **Rationale:** Its slot is one review block a day, and its real size comes from the due-card
     count (`ceil(due/15)` hydration). Scaling 7/week → 8/week would double-book a day, not add
     useful review.
4. **Decision:** `practice` is one module covering maint, acq and the speed-round tail.
   - **Rationale:** Learners see one "vocabulary practice" concept, while maint/acq is an internal
     ADR-009 split. The speed round drills the same mastered vocabulary.
5. **Decision:** Immediate effect through a same-day rebuild that reuses TASK-705 re-entrancy.
   - **Rationale:** The developer chose immediate effect. `build_daily_session` is already
     designed to be re-run for the same date and keep completed slots. Before this change nothing
     in Python exercised that path on an existing row, so this feature is its first production
     caller. It must be tested (see Testing Strategy).
   - **Alternative rejected:** apply from tomorrow, which is simpler but means the learner sees
     the module they just excluded for the rest of the day.

## Security Considerations

- All writes go through the authenticated route with `user_id` from the JWT. `language_id` is
  validated as an int, and module codes are validated against a server-side allowlist (route)
  plus the DB CHECK.
- `build_daily_session` stays `SECURITY DEFINER` with a pinned `search_path`. The new code only
  reads `v_plan.excluded_modules`, which is already scoped to the caller's own row.
- No new data exposure. `available_modules` is derived from public template data.

## Testing Strategy

- **Unit (`tests/test_session_modules.py`, new):**
  - `apply_module_exclusions`: no-op on `[]` (returns the identical dict and int); the ZH-30
    worked example below; practice-only exclusion; all-tests excluded except practice;
    flashcards-only (no redistribution, practice 0); unknown/absent keys ignored; deterministic
    tie-break; total minutes preserved to within one slot's rounding.
  - `ALL_MODULES` equals the SQL CHECK list. Parse it from `migrations/session_module_exclusions.sql`.
  - `compute_weekly_plan` with a stubbed DB: excluded keys absent from the persisted
    `target_counts`; `practice_target_minutes == 0` when practice is excluded; no carry-over for
    excluded skills.
- **Route (`tests/test_session_modules_routes.py`, new):** PUT validation (non-list, unknown
  code, a ja-only code on zh, all excluded → 400); `is_template_only` false when
  `excluded_modules` is present; recompute and `rebuild_today` called only when the value changed;
  `session_rebuilt` echoed; GET returns `available_modules` in `ALL_MODULES` order.
- **SQL (`tests/sql/test_session_module_exclusions.sql`, new, same harness as
  `tests/sql/test_task705_same_day_safe.sql`):** with `excluded_modules = {listening}`, no
  listening rows in `test_ids` and no listening key in `requested_counts`; retry and word_upload
  never pick an excluded type; `{practice}` gives `practice_*_min = 0` and
  `practice_budget_minutes = 0`; a same-day rebuild after excluding a skill keeps that skill's
  already-completed slot with `is_completed`.
- **Session route:** speed round suppressed when `excluded_modules` contains `practice`.
- **Regression:** the full `tests/test_weekly_plan_seeding.py`, `tests/test_plannable_surfaces.py`
  and `tests/test_daily_load_retry_slot.py` suites stay green, since the default `'{}'` must be a
  no-op.

## Worked Example

ZH 30-min template (101), with per-slot minutes from the `Config.TEST_TYPE_MINUTES` seeds (live
P50s may differ). Weekly counts are reading 6, listening 5, dictation 2, pinyin 1,
classifier_drill 1, flashcards 7, dual_translation 2, and practice is 90 min.

- `M_total` = 36 + 25 + 12 + 4 + 4 + 49 + 24 + 90 = **244**.
- Exclude `listening`. `M_fixed` (flashcards) = 49. `M_scalable` = 36 + 12 + 4 + 4 + 24 + 90 = 170.
  `k` = (244 − 49) / 170 = 1.1471.
- Raw values: reading 6.882, dictation 2.294, pinyin 1.147, classifier_drill 1.147,
  dual_translation 2.294. Σ = 13.765, so N = 14. The floors sum to 12. The 2 spare units go to
  reading (.882) and then dictation (.294, which wins the tie with dual_translation on key order).
- Result: reading 7, dictation 3, pinyin 1, classifier_drill 1, flashcards 7, dual_translation 2;
  practice round(90 × 1.1471) = 103 min. Minutes are 42 + 18 + 4 + 4 + 49 + 24 + 103 = **244**,
  the same as before. These adjusted counts then feed the unchanged bandit / ±50% / carry-over /
  `daily_minutes·7` clamp pipeline.
