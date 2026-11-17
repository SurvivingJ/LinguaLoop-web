---
title: "ADR-055: Knowledge Report entitlement seam, one 402 envelope, and a Pro launch gate"
status: proposed
date: 2026-11-17
---

# ADR-055: Knowledge Report entitlement seam, one 402 envelope, and a Pro launch gate

## Context
The full view is gated by `bkt_report_detail` (0 = summary for Free and Core, 1 = full for Pro and
above), read through `get_entitlements` (billing TASK-980), which does not exist yet. Live tiers are
free, premium, enterprise, moderator and admin; 17 users are free and 1 is admin. TASK-980 specifies a
shadow mode (`ENTITLEMENTS_ENFORCED` off → log `entitlement_shadow_deny` and allow) and a 402 helper
returning `{error: <code>, upgrade: true}`, which conflicts with the app's envelope `{status, error:
<message>, error_code: <CODE>}`.

Two challenge-stage findings shape the rest:
- Pro could be enforced and sold with none of the value serious learners pay for: without exam-list
  data, a study action and a useful export, the paid view is a read-only table of the learner's ~251
  tracked words, and Pro is only US$4 a month more than Core (product review P1; billing Q1 already
  warns Pro "may be hard to sell").
- If the page auto-loads Pro data in shadow mode, every Free page view logs a "deny", so the logs
  cannot size demand (P14).

## Decision
1. `report_detail_level(db, user_id) -> (level, enforced)` uses TASK-980's module when it exists; until
   then a stub reads `dim_subscription_tiers.can_access_analytics` and **always reports `enforced =
   False`**, so it can never deny.
2. Pro routes: level 1 → serve; level 0 and not enforced → serve and log `entitlement_shadow_deny`;
   level 0 and enforced → HTTP 402 `{"status":"error","error":"The word-by-word view is part of Pro.",
   "error_code":"PLAN_REQUIRED","upgrade":true,"entitlement":"bkt_report_detail","required":1,"current":0}`.
3. One helper for the whole app: `utils/responses.payment_required(error_code, message, **extra)`, and
   `402: ('PAYMENT_REQUIRED', None)` in `web/errors.py`. TASK-980 adopts it.
4. The summary never returns 402; it reports `detail = {level, enforced, preview}` so the page can show
   the Pro view with a neutral note (shadow) or one honest Pro card (enforced).
5. Demand is logged as `knowledge_pro_intent` only on explicit actions (search, filter, sort change,
   load more, word sheet, lists tab, export), never on the automatic first load.
6. **Pro launch gate (TASK-1059):** `bkt_report_detail` is not enforced, and the report is not named as
   a Pro benefit, until (1) the HSK 2025 list is loaded, (2) "Add these words to my word list" ships,
   (3) filtered and list export ships, and (4) evidence-first rows ship. Billing TASK-997 references
   the gate. The summary can launch for everyone before it passes.

## Consequences
- Easier: the report ships and can be demoed before billing; one paywall payload for TASK-995;
  demand is measured by actions, not page views.
- Harder: until the gate passes, Pro must be sold on its other differences; because the HSK load waits
  for the size gate (DB ≤ 490,000,000 B or a confirmed MiB cap) and the licence answers, the gate
  cannot pass while the database is at 513.5 MB.
- Constrained: enforcement is switched only by billing's rollout (TASK-997), never by this feature.

## Alternatives Considered
- **`tier_required` decorator:** returns 403 and hard-codes tiers; the billing plan rejects it.
- **Hide Pro data from Free users even in shadow mode:** contradicts TASK-980's contract and removes
  the demo; kept as OQ4.
- **TASK-980's `{error: code}` payload:** breaks the envelope and `LinguaI18n.tError` mapping.
- **Enforce as soon as billing launches:** sells a read-only dashboard as the main reason to pay.
