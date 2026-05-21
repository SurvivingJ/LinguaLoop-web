---
title: "ADR-011: Per-Language Independent Study Plan Budgets"
status: accepted
date: 2026-05-21
---

# ADR-011: Per-Language Independent Study Plan Budgets

## Context

LinguaLoop supports multiple study languages (Chinese, English, Japanese active; more planned). A learner studying Chinese + Japanese has two simultaneous learning contexts. The Study Plan orchestrator ([[decisions/ADR-008-study-plan-orchestration-layer]]) needs to decide whether the time budget is:

1. **Per-language, independent** — each language has its own `daily_minutes`; totals are not capped.
2. **Shared total with per-language split %** — one global `daily_minutes`, split (e.g. 60% CN, 40% JP).
3. **Active-language-only** — the user picks one language at a time; the other is paused.

Each has UX, math, and operational implications.

## Decision

**Per-language, independent.** One `user_study_plans` row per `(user_id, language_id)`, each with its own `daily_minutes`, `weekday_shape`, `skill_weight_overrides`, and (V2) `goal_id`. Adapter, weakness signal, weekly recompute, and daily resolve all run independently per row. No cross-language coupling. Total time across languages is the sum; no system-enforced cap.

Multi-language users:
- See a language selector in the Study Plan settings tab, with one editor per language.
- Get N independent daily test loads (one per active language).
- Get N independent Practice sessions when they choose a language to study.

## Consequences

- **Easier:** Simplest mental model — "30 minutes of Chinese + 20 minutes of Japanese". Plans are isolated; tuning Japanese doesn't shift Chinese.
- **Easier:** Adapter math stays clean. Weakness signals, bandit allocation, and pressure formulas don't have to negotiate across languages.
- **Easier:** Adding/removing a language is trivial — INSERT/DELETE one `user_study_plans` row.
- **Harder:** Power users adding a 3rd or 4th language can balloon total daily commitment (3 × 45 min = 135 min) without the system warning them. Mitigated by the settings UI displaying a "Total across languages: N min/day" tally; no hard cap.
- **Constrained:** A user who wants "30 min total, however split" cannot express that in V1. V2 may add an optional shared-budget overlay; the per-language row structure is forward-compatible (V2 could add `user_global_budget(user_id, daily_minutes)` and treat per-language `daily_minutes` as targets that are pro-rated when the sum exceeds the global cap).

## Alternatives Considered

1. **Shared total + per-language split %.** Caps total time but adds UI complexity (one global slider + N per-language % sliders that must sum to 100). Adapter math has to pro-rate when shifting Practice minutes — the +25% flex on Japanese Practice could exceed the global cap and need to steal from Chinese. Rejected for V1 simplicity; revisit in V2 as an overlay.

2. **Active-language-only.** Simplest UX (one focus at a time) but doesn't fit users who alternate languages day-to-day or use sessions of different lengths for each. Rejected as too restrictive.

3. **Per-language with a soft warning when total > 90 min/day.** Rejected: the warning adds friction without preventing the issue; the displayed-tally approach achieves the same nudge without an interrupt.

## Related Pages

- [[features/study-plans]] — Plain-English description, including multi-language UX.
- [[features/study-plans.tech]] — Schema (`user_study_plans` PK = `(user_id, language_id)`).
- [[decisions/ADR-008-study-plan-orchestration-layer]] — Layer this decision affects.
