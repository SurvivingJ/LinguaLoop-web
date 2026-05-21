---
title: Study Plan Adaptation — Technical Specification
type: algorithm-tech
status: planned
prose_page: ./study-plan-adaptation.md
last_updated: 2026-05-21
dependencies:
  - "weekly_plan_states, user_study_plans (write)"
  - "user_skill_ratings, user_word_ladder, user_vocabulary_knowledge, user_flashcards (read)"
  - "test_attempts (read, 28d window)"
  - "daily_test_loads (read last 3 days for spacing)"
  - "dim_study_plan_templates (read)"
  - "Config.STUDY_PLAN_TIER_C_ALPHA_M, ALPHA_A, GAMMA"
breaking_change_risk: low
---

# Study Plan Adaptation — Technical Specification

## Tier B — Weekly Adapter

### 1. Weakness signal

```python
def weakness(s: str) -> float:
    if total_attempts(s, 28d) < 5:
        return 0.50                          # cold-start (R2.6)

    user_mean_elo = avg(user_skill_ratings.elo_rating where language=lang)
    elo_gap = clamp(0, (user_mean_elo - user_skill_ratings.elo_rating[s]) / 200, 1)

    n28 = count(test_attempts WHERE skill=s AND created_at>now-28d AND is_first_attempt)
    acc = sum(score)/sum(total_questions) over that window
    accuracy_trend = clamp(0, 0.75 - acc, 1)

    # global per language in V1 (R2.4)
    subs = senses with user_word_ladder row
    stagnant = subs WHERE no family_confidence delta in 14d AND no
                          consecutive_failures reset in 14d
    ladder_stagnation = stagnant_count / max(subs_count, 1)

    # global per language in V1 (R2.5)
    lapses_28d  = sum(user_flashcards.lapses 28d window)
    reviews_28d = count(fsrs reviews 28d window)
    fsrs_lapse_rate = clamp(0, lapses_28d / max(reviews_28d, 1), 1)

    return ( 0.40 * elo_gap
           + 0.25 * accuracy_trend
           + 0.20 * ladder_stagnation
           + 0.15 * fsrs_lapse_rate )

def weakness_adjusted(s):
    override = user_study_plans.skill_weight_overrides.get(s, 1.0)
    return weakness(s) * override
```

### 2. Value with diminishing returns

```python
def value(s):
    elo_s = user_skill_ratings.elo_rating[s]
    diminishing = clamp(0, (elo_s - 1800) / 600, 1)
    return weakness_adjusted(s) * (1 - diminishing)
```

### 3. Bandit allocation

```python
import hashlib, numpy

def bandit_score(user_id, week_start, skill_id, s):
    alpha = 2 + first_attempt_correct_28d(s)
    beta  = 2 + first_attempt_wrong_28d(s)
    seed  = int(hashlib.sha256(
        f"{user_id}|{week_start}|{skill_id}".encode()
    ).hexdigest()[:16], 16) % (2**32)
    rng = numpy.random.default_rng(seed)
    acc_sample = float(rng.beta(alpha, beta))         # ONE sample
    return value(s) * (1 - acc_sample)
```

### 4. Allocation algorithm (water-fill on clamped proportional shares)

```python
import math

def allocate_test_counts(user, language, week_start, template):
    skills = list(template.weekly_test_counts.keys())
    scores = {s: bandit_score(user.id, week_start, skill_id(s), s) for s in skills}
    total = sum(template.weekly_test_counts.values())
    total_score = sum(scores.values()) or 1.0

    raw_counts = {s: scores[s] / total_score * total for s in skills}
    floors   = {s: math.ceil(template.weekly_test_counts[s] * 0.5) for s in skills}
    ceilings = {s: math.ceil(template.weekly_test_counts[s] * 1.5) for s in skills}

    counts = {s: max(floors[s], min(ceilings[s], round(raw_counts[s])))
              for s in skills}
    diff = total - sum(counts.values())
    while diff != 0:
        if diff > 0:
            cand = [s for s in skills if counts[s] < ceilings[s]]
            if not cand: break
            target = max(cand, key=lambda s: scores[s])
            counts[target] += 1; diff -= 1
        else:
            cand = [s for s in skills if counts[s] > floors[s]]
            if not cand: break
            target = min(cand, key=lambda s: scores[s])
            counts[target] -= 1; diff += 1
    return counts
```

### 5. Practice rebalancing

```python
def rebalance_practice(user, language, template):
    dm = user_study_plans[(user, language)].daily_minutes
    target_review_rate = math.floor(dm * 0.5)    # per day
    target_active_pool = dm                       # words
    target_new_rate    = math.floor(dm / 6)       # per week

    fsrs_due_7d  = count(user_flashcards WHERE due ≤ today+7)
    bkt_decayed  = count(senses WHERE effective_p_known < raw - 0.05)
    stuck        = count(user_word_ladder WHERE
                          (no progress 14d OR consecutive_failures >= 3))
    new_intro_7d = count(user_word_ladder WHERE created_at > now-7d)
    known_words  = count(user_vocabulary_knowledge WHERE p_known >= 0.80)

    maintenance_pressure = (
        clamp01(fsrs_due_7d / max(target_review_rate * 7, 1))
      + 0.5 * clamp01(bkt_decayed / max(known_words, 1))
    )
    acquisition_pressure = (
        clamp01(stuck / max(target_active_pool, 1))
      + 0.3 * clamp01(new_intro_7d / max(target_new_rate, 1))
    )

    pressure_sum = maintenance_pressure + acquisition_pressure
    if pressure_sum == 0:
        acq_share = 1 - template.base_maintenance_share        # default 0.70
    else:
        raw = acquisition_pressure / pressure_sum
        acq_share = clamp(0.50, raw, 0.85)
    maint_share = 1 - acq_share

    weakness_global = mean(weakness(s) for s in test_skills(language))
    flex_factor = 1 + template.practice_minutes_flex_pct * (2*weakness_global - 1)
    practice_minutes = round(template.practice_total_minutes * flex_factor)
    practice_minutes = min(practice_minutes, dm * 7)

    return practice_minutes, maint_share, acq_share
```

### 6. compute_weekly_plan orchestration

```python
def compute_weekly_plan(user_id, language_id, week_start):
    if not Config.STUDY_PLAN_ENABLED:
        return None

    plan = user_study_plans[(user_id, language_id)]
    template = dim_study_plan_templates[plan.template_id]

    counts = allocate_test_counts(plan, language_id, week_start, template)
    practice_min, maint_share, acq_share = rebalance_practice(plan, language_id, template)

    # Carry-over decay (R3.4)
    prev = weekly_plan_states.get((user_id, language_id, week_start - 7d))
    if prev:
        for s in counts:
            remaining = max(0, prev.target_counts.get(s, 0)
                            - prev.completed_counts.get(s, 0))
            counts[s] += round(0.5 * remaining)
        prev_practice_left = max(0, prev.practice_target_minutes
                            - (prev.practice_completed_maint_min
                               + prev.practice_completed_acq_min))
        practice_min += round(0.5 * prev_practice_left)

    test_min = sum(counts[s] * test_time_estimate(s) for s in counts)
    total_weekly_minutes = test_min + practice_min

    UPSERT weekly_plan_states
      PK=(user_id, language_id, week_start)
      SET
        target_counts            = counts,
        practice_target_minutes  = practice_min,
        maintenance_share        = maint_share,
        acquisition_share        = acq_share,
        total_weekly_minutes     = total_weekly_minutes,
        computed_at              = NOW()
      ON CONFLICT preserve:
        completed_counts, practice_completed_maint_min,
        practice_completed_acq_min, session_progress_log
      (only initialize these fields if the row is new)
```

`test_time_estimate(s)` returns `dim_test_types.expected_minutes_p50` if not NULL, else `Config.TEST_TYPE_MINUTES[s]`.

## Tier C — Daily Resolver

### Inputs

| Variable | Source |
|---|---|
| `state` | `weekly_plan_states[(user, language, this_week_monday)]` |
| `plan.weekday_shape` | `user_study_plans` row |
| `today_budget` | `state.total_weekly_minutes · plan.weekday_shape[weekday(today)] / 7` |
| `remaining_weekly(s)` | `state.target_counts[s] - state.completed_counts[s]` |
| `m_remaining` | `state.practice_target_minutes · state.maintenance_share - state.practice_completed_maint_min` |
| `a_remaining` | `state.practice_target_minutes · state.acquisition_share - state.practice_completed_acq_min` |
| `last_3_days_skills` | List of (date, skill) from `daily_test_loads` last 3 days |

### Optimization

```
maximize  Σ x_s · value(s)
        + α_m · m · maintenance_share
        + α_a · a · acquisition_share
        − γ · spacing_penalty(today_skills, last_3_days_skills)

subject to
  Σ x_s · time(s) + m + a  ≤  1.5 · today_budget       # R3.4 soft cap
  Σ x_s · time(s) + m + a  ≥  0.70 · today_budget      # not trivially small
  0 ≤ x_s ≤ remaining_weekly(s)
  0 ≤ m ≤ m_remaining
  0 ≤ a ≤ a_remaining
  m + a > 0

constants:  α_m = α_a = 0.02   (Config.STUDY_PLAN_TIER_C_*)
            γ   = 0.15

spacing_penalty(today_skills, last) =
    Σ_s  I(s ∈ today_skills) · count_in_last_3d(s) / 3
```

### Algorithm (greedy + local swap)

```python
def build_daily_session(user_id, language_id, date):
    state = weekly_plan_states.get((user_id, language_id, week_start_of(date)))
    if state is None or not Config.STUDY_PLAN_ENABLED:
        return legacy_compute_daily_load(user_id, language_id, date)

    plan = user_study_plans[(user_id, language_id)]
    weekday_w = plan.weekday_shape[date.weekday()]  # Mon=0..Sun=6
    today_budget = state.total_weekly_minutes * weekday_w / 7
    upper_cap = today_budget * 1.5

    last_3 = list_last_3_days_skills(user_id, language_id, date)

    # Build candidate list: test slots + 10-min Practice chunks
    candidates = []
    for s in test_skills(language_id):
        remaining = state.target_counts.get(s, 0) - state.completed_counts.get(s, 0)
        for _ in range(max(0, remaining)):
            candidates.append(('test', s, time_minutes(s),
                               value(s) / time_minutes(s)))
    m_left = max(0, state.practice_target_minutes * state.maintenance_share
                       - state.practice_completed_maint_min)
    a_left = max(0, state.practice_target_minutes * state.acquisition_share
                       - state.practice_completed_acq_min)
    for _ in range(int(m_left / 10)):
        candidates.append(('maint', None, 10,
                           Config.STUDY_PLAN_TIER_C_ALPHA_M * state.maintenance_share))
    for _ in range(int(a_left / 10)):
        candidates.append(('acq', None, 10,
                           Config.STUDY_PLAN_TIER_C_ALPHA_A * state.acquisition_share))
    candidates.sort(key=lambda c: -c[3])

    plan_today = {'tests': [], 'maint_min': 0, 'acq_min': 0}
    used_min = 0
    today_skills = set()
    for kind, skill, mins, _ in candidates:
        # Spacing cost only applies to test skills not yet added to today
        spacing = (0 if skill is None or skill in today_skills
                   else Config.STUDY_PLAN_TIER_C_GAMMA
                        * count_in_last_3d(skill, last_3) / 3)
        # Defer if spacing would consume the marginal value
        if used_min + mins > upper_cap: continue
        if kind == 'test':
            plan_today['tests'].append(skill); today_skills.add(skill)
        elif kind == 'maint': plan_today['maint_min'] += mins
        elif kind == 'acq':   plan_today['acq_min']   += mins
        used_min += mins
        if used_min >= today_budget: break

    plan_today = local_swap_pass(plan_today, candidates, last_3)

    test_ids = hydrate_tests(plan_today['tests'], user_id, language_id)

    UPSERT daily_test_loads
      PK=(user_id, language_id, load_date=date)
      SET
        test_ids              = test_ids,
        completed_test_ids    = '[]',
        daily_session_targets = {
            'practice_maintenance_min': plan_today['maint_min'],
            'practice_acquisition_min': plan_today['acq_min'],
            'resolver_solved_at':       NOW(),
            'objective_value':          objective_value(plan_today, last_3)
        }
    UPSERT daily_test_load_items rows for each test_id.
    return plan_today
```

`local_swap_pass` tries replacing each accepted test slot with an alternative skill if `value(other) - value(s) > spacing_savings`. Single pass; trivial with ≤ 6 skills.

`hydrate_tests` calls existing `get_recommended_tests(user, language)`, filters to each requested skill, picks the top-ELO-matched test not already attempted today.

## Cron registration

```python
# app.py — add to existing BackgroundScheduler block
scheduler.add_job(
    _run_weekly_plan_recompute,
    trigger=CronTrigger(day_of_week='sun', hour=23, minute=0),
    id='study_plan_weekly_recompute',
    coalesce=True, max_instances=1,
)

def _run_weekly_plan_recompute():
    with advisory_lock('study_plan_weekly_recompute'):
        week_start = (date.today() - timedelta(days=date.today().weekday()))
        for row in iterate_user_study_plans():
            try:
                compute_weekly_plan(row.user_id, row.language_id, week_start)
            except Exception as e:
                logger.error(f"Tier B failed for {row.user_id}/{row.language_id}: {e}")
                continue
```

## Idempotency

- `compute_weekly_plan` UPSERTs `weekly_plan_states` on PK `(user_id, language_id, week_start)`. Re-running mid-week with changed inputs (e.g. new ELO after a Tuesday test) produces new `target_counts` but preserves `completed_counts`, `practice_completed_*_min`, and `session_progress_log` via the conditional UPDATE.
- `build_daily_session` UPSERTs `daily_test_loads` on PK `(user_id, language_id, load_date)`. Re-running same day with same `weekly_plan_states` state produces the same plan (greedy is deterministic given a stable sort).
- `record_session_progress` is idempotent on `attempt_id` (see [[features/study-plans.tech]]).

## Numerical worked example

See [[features/study-plans.tech#worked-example]] for full end-to-end numbers — User U, Chinese, 45 min/day, week 4, listening ELO 1100.

## Performance

- Tier B per user: ≤ 8 RNG draws + a small SQL bundle for 28-day windows. < 50ms with proper indices.
- Tier C per user per day: ≤ 30 candidates × O(log N) sort + 1 swap pass + 1 hydrate per slot. < 200ms target.
- Tier B cron sweeping all users: parallelizable; expect O(N) with N = active users with plans. For 10K users × 2 langs: ~ 20K invocations × 50ms = ~ 1000s = 17 min. Acceptable for a once-weekly cron. Future: chunk by user_id and use multi-worker dispatch.

## Related Pages

- [[algorithms/study-plan-adaptation]] — Prose counterpart.
- [[features/study-plans.tech]] — Schema, RPC contracts, rollout.
- [[features/practice-engine.tech]] — Reads `daily_session_targets`.
- [[features/comprehension-tests.tech]] — `get_or_create_daily_load` routes through `build_daily_session` when flag enabled.
- [[decisions/ADR-010-value-weighted-thompson-skill-mix]] — Bandit choice.
- [[decisions/ADR-013-global-feature-flag-rollout]] — Flag flow.
