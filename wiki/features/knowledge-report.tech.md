---
title: Knowledge Report ("My vocabulary") — Technical Specification
type: feature-tech
status: planned
prose_page: ./knowledge-report.md
last_updated: 2026-11-18
dependencies:
  - "user_vocabulary_knowledge, user_flashcards, user_word_ladder, user_word_watchlist (read)"
  - "dim_word_senses, dim_vocabulary, dim_exercise_types, exercises (exercise_type only, by PK) (read)"
  - "calibration_sessions, calibration_responses, calibration_anchor_pool, calibration_anchor_blocklist (read; definition mode)"
  - "exercise_attempts, word_quiz_results, question_attempt_results, questions, tests (read)"
  - "NEW table: user_knowledge_snapshots"
  - "NEW Storage bucket: reference-data (private; exam-list files word-lists/<list_code>/v<N>.json; ADR-054)"
  - "NEW RPCs: knowledge_frame_bands, knowledge_active_pairs, knowledge_snapshots_prune, knowledge_report_summary, knowledge_report_words, knowledge_report_word_detail, knowledge_list_buckets, knowledge_report_list_words"
  - "NEW code: routes/knowledge.py, services/vocabulary/knowledge_report.py, services/vocabulary/knowledge_estimate.py, services/vocabulary/word_lists.py, services/knowledge_snapshots.py, utils/csv_export.py, scripts/build_word_lists.py, templates/knowledge.html, static/js/pages/knowledge.js, static/css/pages/knowledge.css"
  - "EXISTING: POST /api/word-list/submit, GET /api/practice/extra, get_recommended_tests, services/prestudy.share_plan, services/optional_rpc.py, services/request_cache.py, services/vocabulary/gloss_lookup.py, services/pinyin_format.py, web/scheduler.py, services/exercise_content/backends.py (SupabaseStorageBackend, InMemoryBackend)"
  - "billing TASK-980 get_entitlements / bkt_report_detail (a stub seam is used until it exists)"
breaking_change_risk: medium
---

# Knowledge Report ("My vocabulary") — Technical Specification

> **Risk is medium** because every database object is created by a migration the owner applies to
> production (the only Supabase project; no staging). Every change is additive: no existing table,
> column, index or function is altered by the core tasks. The live decay functions are **not used**
> by this feature in v1 (see §2.5 and [[decisions/ADR-052-report-leads-with-measured-evidence]]).

> **Revision 2026-11-18 — exam lists moved from tables to Storage
> ([[decisions/ADR-054-exam-word-lists-in-storage]]).** The HSK/JLPT lists are no longer the tables
> `dim_word_lists` / `dim_word_list_items`: they are immutable, versioned JSON files
> (`word-lists/<list_code>/v<N>.json`) in a new private Storage bucket `reference-data`, built and
> uploaded by `scripts/build_word_lists.py` with lemmas resolved to `vocab_id` at build time, and read
> by `services/vocabulary/word_lists.py` (per-process cache, fail-soft). SQL functions take the list's
> `vocab_id`s as arrays from Python (`knowledge_list_buckets`, `knowledge_report_list_words`, the
> `vocab_ids` filter of `knowledge_report_words`). Database cost falls from ~1.8–2.0 MB to ~1.2 KB of
> `storage.objects` rows, so the list upload and the Pro launch gate (TASK-1059) no longer wait for the
> database size question (OQ13). Changed: §1, §2.8, §3.1, §4, §5.2, §5.3, §6.1–§6.3, §6.6, §8, §9,
> §10 (i18n), §11 (5), §12, §13, §14, §15 (OQ3, OQ13).

**Labels used on this page.** **MEASURED** = read from code (file:line) or the live database
(read-only SQL, quoted in Appendix B or in the research reports named). **ESTIMATE** = arithmetic or
simulation on measured inputs. **INFERENCE** = a conclusion not tested directly. **DECISION** = a
design choice; each contestable one is also an open question in §15 with the default used.

Users are named by the first 8 characters of their UUID. `de6fd05b` is the one human learner with
months of mixed evidence; `110fb390` looks automated (OQ6).

---

## 0. Evidence base

| # | Fact | Label / source |
|---|---|---|
| F1 | 18 users; 3 have any `user_vocabulary_knowledge` (UVK) row; 1,136 rows in 5 (user, language) pairs: 110fb390/zh 575, de6fd05b/ja 251, 110fb390/ja 165, 705007b9/en 87, de6fd05b/zh 58. `user_word_watchlist` has 0 rows. | MEASURED (data-audit research Q3, Q21) |
| F2 | Raw `p_known` is not calibrated: on 203 attempts with a stored prediction its Brier score is worse than a per-user constant (0.205 vs 0.192 for de6fd05b; 0.309 vs 0.158 for 110fb390), AUC 0.62 / 0.46. For de6fd05b, words the model held below 0.20 were answered correctly 12/17 (70.6%) and at 0.20–0.40 10/14 (71.4%). | MEASURED (data-audit Q17–Q18) |
| F3 | Decay pulls every word toward 0.10 regardless of frequency, lifts rows below 0.10, is declared IMMUTABLE while reading `now()`, and is erased by the next write (raw 0.95 idle 90 d → effective 0.281 → a *wrong* answer → raw 0.581). The 2-argument `bkt_effective_p_known` fails on every call (`ERROR 42725 … is not unique`). | MEASURED (data-audit Q19–Q20a; performance research §3) |
| F4 | Under a decay-based "due" rule, 24 of de6fd05b/ja's 46 "due" meanings are in Zipf bands 6–7 (中, 今, 仕事, 言う, 関係), while the same learner's vocabulary check puts band 7 at ~88% known. | MEASURED (product review Q-R1, Q-R2); ESTIMATE (§2.6 fixture) |
| F5 | Contextual-inference inserts look like one correct test question; frequency inference and lapse penalties leave no counter trace; only `word_test_correct + word_test_wrong > 0` marks a word-level check, and reading tests move `p_known` across 0.75 in both directions (0.92 → 0.613 after one wrong linked question; 0.70 → 0.896 after one right one). | MEASURED (data-audit §1.3; statistician review R16) |
| F6 | No history of `p_known`/status exists and replay is impossible (5 of 7 writers log nothing per word; 203 of 906 attempts carry `p_known_after`). | MEASURED (data-audit §6; performance §7.1) |
| F7 | The vocabulary check (Calibration, definition mode) samples **senses** from `calibration_anchor_pool` for one (word language, definition language), uniformly within each Zipf band (`row_number() OVER (PARTITION BY zipf_band ORDER BY random())`), excluding only anchors already served in the current session. | MEASURED (statistician review R3, live `calibration_next_anchors` body) |
| F8 | The check's frame (pool lemmas whose rank-1 sense is eligible) covers ja/en 3,175 of 3,422 dictionary lemmas but zh/en only 3,623 of 12,790 (band 4: 691 of 4,881). Frame lemmas are not exchangeable with the rest: zh band 4 frame lemmas appear in a test transcript 98.3% of the time vs 22.0% for non-frame lemmas of the same mean Zipf. | MEASURED (Appendix B K1; statistician review R4, R5) |
| F9 | The zh pool is stale, not structurally small: all 13,137 zh native-standard senses have an embedding, but the zh/zh pool holds 3,643 rank-1 lemmas; 8,840 zh lemmas entered the dictionary in the weeks of 2026-10-26 and 2026-11-09, and the pool is DERIVED and "goes stale silently" (`wiki/features/calibration.tech.md:667-675`). | MEASURED (Appendix B K6; product review Q-R7, Q-R8) |
| F10 | de6fd05b/ja has 178 definition-mode answers on 174 lemmas, all with English definitions, 2026-09-13 → 2026-11-15; 172 remain after keeping the latest answer per lemma and rank-1 anchors only (23–26 per band). | MEASURED (Appendix B K2; statistician review R1) |
| F11 | `dim_vocabulary.level_tag` is NULL on all 20,613 rows and is read as an age-tier code (`services/vocabulary_ladder/asset_generators/prompt1_core.py:225`); no HSK/JLPT/CEFR data exists. | MEASURED (level-lists research §1.2) |
| F12 | HSK 3.0 2025 syllabus entries matching a lemma with senses: L1–L5 87.6–92.1%, L6 75.4%, L7-9 37.9%, all 60.2% (6,559 / 10,896). JLPT (Waller, stephenmk files): N5 48.7%, N4 42.0%, N3 40.4%, N2 18.4%, N1 20.5%, all 28.2%; the ja dictionary is too small for overall JLPT coverage to exceed ~43%. | MEASURED / ESTIMATE (level-lists §3.2–3.4) |
| F13 | Summary aggregate for the largest pair: 21–36 ms warm; sorted keyset page 39.7 ms; synthetic 26,469 rows: summary 55.5 ms without decay, 178 ms with inlined decay, 552 ms with the PL/pgSQL decay. Host jitter is 20–50× (same all-hit query 4.7–245 ms). | MEASURED (performance research §1, §4, §5) |
| F14 | PostgREST silently caps results at 1,000 rows (`services/pagination.py:3-7`); a single `jsonb` return is one row. | MEASURED (code-map research §3) |
| F15 | `/api/reports`, the top-bar Report button and `report.*` keys belong to "Report an issue" (`routes/reports.py:1,22-55`; `templates/base.html:99-101,271-313`). `/api/knowledge` and `/knowledge` are free. | MEASURED (code-map research §0) |
| F16 | No `get_entitlements`, no `tier_entitlements`; live tiers free/premium/enterprise/moderator/admin; `dim_subscription_tiers.can_access_analytics` is false only for free; users: free 17, admin 1. No prestudy quota exists in code (grep for `prestudy_per_week` in `*.py` returns nothing). | MEASURED (code-map §11; this stage) |
| F17 | Database size 513,526,931 B on 2026-11-17. Whether the Free cap is 500 MiB (~10.8 MB headroom) or 500,000,000 B (~13.5 MB over) is unverified. ADR-049's content drop (~119 MB) is the planned relief. | MEASURED (Appendix B K6); open (OQ13) |
| F18 | `POST /api/word-list/submit` takes `{words: [...], language: 'zh'|'en'|'ja'}`, at most 50 words (`routes/word_list_import.py:77,220-266`), 5 batches a day per user (`services/word_list_import/batch_limits.py:34`), answers 202 with an `upload_batch_id` or 429 `RATE_LIMITED` (`routes/word_list_import.py:96-97`), and **generates ladder exercises for any resolved sense that has none** (`services/word_list_import/upload_handler.py:1-20`). | MEASURED |
| F19 | Practice mode (`/session?mode=practice`) shows today's queue and, when it is empty, "No exercises due right now." plus the extra-round panel with reviews preselected (`static/js/session/controller.js:119`, `:1093-1112`); `GET /api/practice/extra?reviews=1` builds a review round (`routes/practice.py:92-134`). Practice's maintenance pool is not the report's word set. | MEASURED |
| F20 | The prestudy "share of key words new to you" is `services/prestudy.py:872-882` `share_plan` (p < 0.5 over `tests.vocab_sense_ids`), the auto threshold is 0.25 (`:852`), `plan_for_tests` computes it for a list of tests (`:907`); `get_recommended_tests(p_user_id, p_language_id, p_topic_recency_days)` returns `test_id, slug, test_type, title, …` (Appendix B K9). | MEASURED |

---

## 1. Architecture Overview

```
Browser /knowledge (templates/knowledge.html + static/js/pages/knowledge.js, classic IIFE)
  │  authFetch (Bearer)                         the page handles 402 / 404 / 503 itself
  ▼
routes/knowledge.py  (knowledge_bp, url_prefix /api/knowledge)
  @supabase_jwt_required → @api_errors → @require_language_id → UUID guard → flag guard
  ├─ GET /summary ─────────────► knowledge_report.summary()
  │                                ├─ user_knowledge_snapshots: anchor rows (PostgREST, ≤ 100 rows, memoised)
  │                                ├─ optional_rpc.call_bundle('knowledge_report_summary', …)   one round trip
  │                                ├─ knowledge_frame_bands() (process TTL cache, 3,600 s)
  │                                ├─ knowledge_estimate.* (pure Python: range, label, groups, skills, growth)
  │                                ├─ zh/ja: word_lists.WordListStore (Storage bucket reference-data,
  │                                │    per-process cache, fail-soft) → arrays → knowledge_list_buckets
  │                                └─ report_detail_level() (entitlement seam, ADR-055)
  ├─ GET /prestudy-suggestion ─► get_recommended_tests + prestudy.plan_for_tests (top reading/listening test)
  ├─ GET /words ─────(Pro)─────► knowledge_report_words  (keyset, filters, sort, gloss on page rows;
  │                                a list filter arrives as vocab_ids from WordListStore)
  ├─ GET /words/<vocab_id>/<sense_rank> ─(Pro)─► knowledge_report_word_detail
  ├─ GET /lists/<list_code>/words ─(Pro)─► WordListStore → knowledge_report_list_words (arrays)
  └─ GET /export ────(Pro)─────► words or list-words RPC in 1,000-row chunks → utils/csv_export
                                  (format=csv | anki)
Page actions that reuse existing endpoints (ADR-056):
  "Add these {n} words to my word list" → POST /api/word-list/submit (existing)
  "Review in Practice" → /session?mode=practice (optional deep link &extra=reviews, TASK-1043)
  "Prepare for {test}" → /test/<slug>/prestudy (existing)

APScheduler 04:25 UTC (web/scheduler.py) → services/knowledge_snapshots.run_nightly()
  knowledge_active_pairs → per pair: knowledge_report_summary + knowledge_estimate → upsert
  user_knowledge_snapshots (idempotent on PK) → knowledge_snapshots_prune(120)

Owner, offline (ADR-054): scripts/build_word_lists.py — pinned source + read-only dim_vocabulary →
  word-lists/<list_code>/v<N>.json (dry run locally; --upload = new immutable version in Storage)
```

**DECISION:** per-row data work runs in SQL (no 1,000-row cap, one round trip, one copy of every
rule); statistics, labels, rounding, merged groups, clustered intervals, growth and next steps run
in pure Python on small aggregates (unit-tested, reused by the snapshot job). Entitlement, L1
gloss choice, CSV formatting and HTTP live in Python. **No BKT or decay formula is copied into
Python, and the report calls no decay function in v1.**

---

## 2. Units and every metric

### 2.1 Units

| Unit | Definition | Used for |
|---|---|---|
| **row** | one UVK row = (user, `sense_id`); a `sense_id` is a definition row (lemma, `sense_rank`, definition language, definition level) | storage only; **never counted in the UI** |
| **meaning** | (`vocab_id`, `sense_rank`) | Pro rows, export rows, evidence states, missed recently |
| **word** | `vocab_id` (lemma); for the headline, list coverage and "rated known" a word is credited through its **rank-1 meaning** only | headline counts, frequency groups, lists |
| **frame F(L, D)** | lemmas `v` that have a rank-1 sense row in `calibration_anchor_pool` with `word_language_id = L`, `definition_language_id = D`, `has_embedding`, not in `calibration_anchor_blocklist`; band sizes `N_b` = `count(DISTINCT vocab_id)` grouped by the pool's `zipf_band` | estimate denominator |

MEASURED frames (Appendix B K1; rank-1 lemmas, bands 1…7):

| (L, D) | N_1…N_7 | ΣN | dictionary lemmas with a band (U) |
|---|---|---|---|
| ja / en, ja / zh | 577 / 425 / 621 / 655 / 537 / 283 / 77 | 3,175 | 3,422 |
| ja / ja | 573 / 422 / 617 / 653 / 536 / 280 / 77 | 3,158 | 3,422 |
| zh / en, zh / ja | 303 / 617 / 742 / 691 / 664 / 435 / 171 | 3,623 | 12,790 |
| zh / zh | 314 / 615 / 749 / 690 / 665 / 438 / 172 | 3,643 | 12,790 |
| en / en | 412 / 517 / 737 / 794 / 722 / 425 / 147 | 3,754 | 4,243 |

Why rows are never counted (INFERENCE from data-audit §4.6): ja has ~5.9 definition rows per lemma,
so counting rows would inflate Japanese about 6×. Why rank-1 (level-lists §5): crediting any
meaning over-credits basic polysemous words (6 vs 9 "known" HSK 1 words for 110fb390).

### 2.2 Meaning aggregation (the primary-row rule)

Rows of one learner and language are grouped by (`vocab_id`, `sense_rank`) through `dim_word_senses`.
**DECISION:**
- **primary row** = latest `last_evidence_at`; ties → higher `evidence_count`; ties → lower `sense_id`.
- `p_last` = primary row `p_known` (raw); `last_seen_at` = max `last_evidence_at`; `first_seen_at` =
  min `created_at`.
- Counters are summed over the group: `tests_correct = Σ comprehension_correct`, `tests_wrong =
  Σ comprehension_wrong`, `checks_correct = Σ word_test_correct`, `checks_wrong = Σ word_test_wrong`,
  `evidence_events = Σ evidence_count`.
- `marked_unknown` = any row has `status = 'user_marked_unknown'` (0 rows today; no writer).
- Ladder: max `current_ring` and that row's `word_state` over the group's `sense_id`s; flashcard
  lapses: max `user_flashcards.lapses` over the group.

### 2.3 Logged direct outcomes

`O(u, L)` = first-try outcomes that have a per-word log, mapped to meanings through
`dim_word_senses` (`word_language_id = L`):
- `exercise_attempts` with `is_first_attempt` (any `source`: practice NULL, `prestudy`, `intro`);
- `word_quiz_results` (one fixed format, family `form_recognition`).

Not in `O` (no per-word log exists — data-audit §6.2): prestudy prime/follow-up answers, flashcard
ratings, dictation, Dual-translation Produce, frequency inference, lapse penalties. Vocabulary-check
answers are excluded from `O` because the check samples random words; they are reported in the
estimate card (§2.6). The "How this works" sheet lists what is not counted.

### 2.4 Evidence states (per meaning) and "rated known after a direct check"

**`rated_known`** (meaning) = `checks_correct > checks_wrong AND p_last >= 0.75 AND NOT marked_unknown`.
This is **model output on top of a measured check**, never called "measured" or "confirmed".

**Rated known after a direct check** (headline) = `count(DISTINCT vocab_id)` over rank-1 meanings
with `rated_known`. de6fd05b/ja: **69** (the draft's looser `checks_correct > 0` rule gave 72; 3
lemmas with at least as many direct wrongs as rights drop out) — MEASURED (Appendix B K3).
**Checked several times** (Pro filter) = `rated_known AND checks_correct >= 2`: de6fd05b/ja **22**.

**Evidence state** (exactly one per meaning, first match wins; DECISION):

| # | State code | en label | Rule |
|---|---|---|---|
| 1 | `missed_last` | Missed last time | the latest outcome in `O` for the meaning is wrong |
| 2 | `rated_known` | Rated known after a direct check | §2.4 rule |
| 3 | `checked` | Checked, not yet rated known | `checks_correct + checks_wrong > 0` |
| 4 | `not_checked` | Seen in tests only | otherwise (evidence only from reading/listening tests, including contextual inference) |

de6fd05b/ja: 10 / 69 / 30 / 142 = 251 meanings (MEASURED, Appendix B K4). The five-level
`bkt_status` labels are **not shown anywhere in v1** (ADR-052); they return only after TASK-1056(c)
shows next-answer accuracy rises with the label.

**Row lead (evidence first; DECISION):** the first line of every Pro row is the most recent
measured fact: "Last direct check ✓ 3 Nov" / "Last direct check ✗ 3 Nov" (latest `O` outcome),
else "Checks ✓{cc} ✗{cw}" (counters only, no per-word log), else "Seen in tests only".

### 2.5 Staleness: "Not seen for {n} days" (no decay in v1)

`idle_days` (meaning) = whole days between `last_seen_at` and `as_of`. **Not seen in 60+ days** =
`idle_days >= 60`. de6fd05b/ja: **95** meanings (MEASURED, K3). `last_seen_at` is reset by any
evidence write, including contextual touches (data-audit §1.1), so the copy is "not seen", never
"not practised", "fading" or "forgotten".

**DECISION (ADR-052):** no decay-based value (effective p, "due for a check", "fading") appears in
v1: the decay is frequency-blind (F3, F4), and Practice's maintenance pool is a different set
(197 of 251 rows vs 46 "due" for de6fd05b/ja — statistician review R19), so a numbered "review the
due words" promise cannot be kept. A model-based flag can return with TASK-1067.

### 2.6 Vocabulary-size estimate (headline) — ADR-051

**Inputs** (learner u, word language L, `as_of`, window `W = 180` days):
1. `A` = definition-mode answers: `calibration_sessions.mode = 'definition'`, `word_language_id = L`,
   `calibration_responses.answered_at IS NOT NULL`, `answered_at <= as_of`, anchor sense
   `sense_rank = 1` (S9). An explicit "I don't know" is stored with `chosen_sense_id NULL`,
   `is_correct false` and `answered_at` set (`services/calibration_service.py:660-662`).
2. `D*` = the definition language with the most answers of `A` inside the window; ties → the later
   `max(answered_at)`; ties → lower id. If no answer falls inside the window, `D*` is chosen the same
   way over all of `A` (this feeds state E1c). Definition languages are **never pooled** (S1, S9).
   `alltime_n` = the per-band distinct-lemma counts for `D*` without the window.
3. `A*` = answers of `A` in `(as_of − W, as_of]` with definition language `D*`, keeping only the
   **latest answer per `anchor_vocab_id`** (S10).
4. Per band b = `calibration_responses.zipf_band` (1…7): `n_b` = |A*_b| (distinct lemmas),
   `s_b` = skips, `c_b` = correct, `w_b = n_b − s_b − c_b`.
5. `N_b` = frame F(L, D*) (§2.1).

**Estimator** (G = 0.25, four options; r = G/(1−G) = 1/3; z = 1.96):
- `K_b = c_b/n_b − r·w_b/n_b` — **no clamp** (skip = not known; an attempted unknown word is a
  1-in-4 guess).
- `p̃c = (c_b + 0.5)/(n_b + 1.5)`, `p̃w = (w_b + 0.5)/(n_b + 1.5)` (Jeffreys pseudo-counts, variance only).
- `Var_b = [p̃c(1−p̃c) + r²·p̃w(1−p̃w) + 2r·p̃c·p̃w] / n_b × max(0, 1 − n_b/N_b)`.
- `T = Σ N_b·K_b`, `SD = sqrt(Σ N_b²·Var_b)`, `N = Σ N_b`.
- `lo = max(0, T − z·SD)`; `hi = min(N, max(T, 0) + z·SD)`; bar tick at `min(N, max(0, T))`.
  (The `max(T, 0)` in `hi` is a synthesis-stage guard: it keeps `hi > 0` when T is negative, which
  happens for a learner who guesses and misses everything; it only widens the interval.)
- `rel' = z·SD / max(T, 0.10·N)`.

**Eligibility, display and label** (rows evaluated top to bottom; first match applies; DECISION
from S3 + P8; thresholds are OQ8):

| # | Condition | Result |
|---|---|---|
| 1 | any band with `n_b < 10` in the window, and the same counts **without** the window also fail | **no estimate**, state E1: "{have} of 70" where `have = Σ min(n_b, 10)` |
| 2 | any band with `n_b < 10` in the window, but the counts without the window pass | **no estimate**, state E1c "check out of date" (last answer date shown) |
| 3 | `lo = 0` | one-sided: "**Fewer than {ceil2(hi)}** of the {N} words the check draws from", label `low` |
| 4 | `rel' ≤ 0.15` and every `n_b ≥ 30` | range, label `good` |
| 5 | `rel' ≤ 0.30` and every `n_b ≥ 20` | range, label `medium` |
| 6 | `rel' ≤ 0.50` | range, label `low` |
| 7 | `hi ≤ 0.5·N` | one-sided "Fewer than {ceil2(hi)}", label `low` |
| 8 | otherwise | **no estimate**, state E1b "too uncertain"; `answers_needed_per_band = ceil(n̄·((rel'/0.50)² − 1))`, n̄ = mean `n_b` |

Labels display as en "Rough" (`low`), "Medium", "Good" (the calibration page's vocabulary).
Rule 7 is a synthesis-stage addition to S3: without it a learner with a small positive `lo` and a
large SD loops between "too uncertain" and "take the check".

**Display rounding:** `floor2(lo)`–`ceil2(hi)`; for x ≥ 10 the step is `10^(floor(log10 x) − 1)`,
else 1 (853.3 → 850; 1,368.1 → 1,400; 12,790 → 12,000 / 13,000). The point T is drawn only as a
tick, never printed.

**Copy (en):** "In the vocabulary check you recognised about **{lo}–{hi}** of the {N} {language}
words it draws from." Basis line: "From {answers} check answers, {first_date} – {last_date} ·
{label}." The "How this works" sheet adds: "Words LinguaDojo has not yet put into the check are not
counted." and "If you choose 'I don't know', we count the word as not known. Guesses are corrected
for the 1-in-4 chance of being right. If some of the words you skipped were partly known, the true
figure is higher."

**Disagreement line (S2):** if `rated_known_in_frame` (rated-known words whose `vocab_id` is in
F(L, D*)) `> hi`, show "Your practice has rated more words known than this check suggests. Take the
check again to update it." The count never moves the interval.

**Fixture — de6fd05b/ja** (MEASURED inputs, Appendix B K1/K2; ESTIMATE output,
`kr/synth_scripts/final_estimator_v2.py`):

| band | n_b | s_b | c_b | w_b | N_b | K_b | sd_b |
|---|---|---|---|---|---|---|---|
| 1 | 26 | 16 | 7 | 3 | 577 | 0.231 | 0.093 |
| 2 | 23 | 16 | 5 | 2 | 425 | 0.188 | 0.091 |
| 3 | 26 | 14 | 9 | 3 | 621 | 0.308 | 0.099 |
| 4 | 24 | 12 | 9 | 3 | 655 | 0.333 | 0.106 |
| 5 | 25 | 9 | 13 | 3 | 537 | 0.480 | 0.108 |
| 6 | 25 | 8 | 15 | 2 | 283 | 0.573 | 0.103 |
| 7 | 23 | 0 | 21 | 2 | 77 | 0.884 | 0.074 |

→ T = 1,110.7, SD = 131.3, interval 853.3–1,368.1, rel' = 0.232 → **"850–1,400 of 3,175", Medium,
from 172 check answers, 13 Sep – 15 Nov.** For comparison: the draft's whole-dictionary figure was
1,209 (929–1,489) of 3,422; with all 178 answers and the frame it is 1,126 (870–1,382).

**Simulation** (ESTIMATE; same script; 3,000 synthetic learners per cell, words drawn without
replacement from the frame; coverage of the true count by the displayed interval or one-sided bound):

| profile | n = 10 / band | n = 20 | n = 30 | zero-width outputs |
|---|---|---|---|---|
| ja de6fd05b-like | 0.939 | 0.948 | 0.947 | 0 |
| ja advanced, no skips | 0.954 | 0.953 | 0.943 | 0 |
| ja near-ceiling, no skips | 0.999 | 0.999 | 0.991 | 0 |
| zh beginner, never skips | 1.000 | 0.999 | 0.998 | 0 |
| zh beginner, honest skips | 1.000 | 0.994 | 0.992 | 0 |
| zh intermediate, some skips | 0.937 | 0.938 | 0.944 | 0 |

Every cell is ≥ 0.937 and every run produced an output (no "too uncertain" loop); the zh beginner
who never skips (expected counts at 20/band) gets "Fewer than 510 of 3,623", Rough.

**What it may claim:** recognition (choose the meaning from four) of the words in the check's
pool, with the stated interval and dates. **May not claim:** total vocabulary in the language,
productive knowledge, other meanings, exam readiness, today's state when the last answer is old.

**Known limits (INFERENCE):** answers are pooled over 180 days, so a fast-growing learner's range
lags; the zh frame is 28% of the zh dictionary until the pool is refreshed (F9, OQ29); "I don't
know" may hide partial knowledge, which would make the figure an underestimate (S4; validated by
TASK-1056(a) using TASK-1061's forced-choice items).

**Why not BKT rows** (INFERENCE backed by F2, F5): rows exist only for words the app chose to show,
one-event rows are mostly the frequency prior, and the p's are uncalibrated and correlated; summing
them or extrapolating them reports the model's assumptions (ADR-051).

### 2.7 Frequency groups (S12)

Four merged groups, most common first (DECISION): **Most common** = band 7 (Zipf ≥ 5.5);
**Common** = bands 5–6 (4.5–5.5); **Mid-frequency** = bands 3–4 (3.5–4.5); **Rare** = bands 1–2
(< 3.5). Per group g: frame size `N_g = Σ N_b`; share `K_g = Σ N_b·K_b / N_g`; `sd_g =
sqrt(Σ N_b²·Var_b) / N_g`; shown as `floor(100·max(0, K_g − 1.96 sd_g))`–`ceil(100·min(1, K_g +
1.96 sd_g))` % **only when** the headline is eligible (rows 3–7 of §2.6) **and** `1.96·sd_g ≤ 0.15`;
otherwise "Not enough check answers at this level yet ({n_g})". Measured counts per group (always
shown): tracked words and rated-known words, banded by `calibration_zipf_band(dim_vocabulary.frequency_rank)`;
band-less words are listed as "No frequency data".

de6fd05b/ja (ESTIMATE): Most common 73–100% (23 answers, 77 words); Common hidden (half-width
0.155; 50 answers, 820 words); Mid-frequency 17–47% (50 answers, 1,276 words); Rare 8–35% (49
answers, 1,002 words).

### 2.8 Exam-list coverage (measured buckets only; ADR-054)

Lists: `hsk30_2025` (zh; levels `1`,`2`,`3`,`4`,`5`,`6`,`7-9`) and `jlpt_waller` (ja; `N5`…`N1`,
unofficial). One item per distinct headword per list, at its lowest level (§8). Items are the
`entries` of the list's **latest file in Storage** (§5.2); each item's `vocab_id` was resolved when the
file was built (§8), not at request time. For item i with `vocab_id` v (may be NULL):

| Bucket code | en label | Rule |
|---|---|---|
| `rated_known` | Rated known after a direct check | v's rank-1 meaning is `rated_known` |
| `seen_not_rated` | Seen, not yet rated known | v's rank-1 meaning has a row but is not `rated_known` |
| `no_evidence` | No evidence yet | v exists, no row on its rank-1 meaning (sub-count `other_meaning_only` when rows exist only on rank ≥ 2) |
| `not_in_dictionary` | Not yet in LinguaDojo | v is NULL |

Per level the summary shows the four counts and `in_dictionary = items − not_in_dictionary`. The
"cumulative" toggle sums counts over levels ≤ the chosen one (counts add; no variance is involved).

**Where each count is computed (revised 2026-11-18).** Python, from the file: `items` (entries per
`level_idx`), `not_in_dictionary` (entries with `vocab_id = null`) and `in_dictionary`. SQL,
`knowledge_list_buckets` (§6.1): `rated_known`, `seen_not_rated`, `no_evidence` and
`other_meaning_only`, from two parallel arrays Python passes — `p_vocab_ids` and `p_level_idx`, one
element per in-dictionary entry (an id shared by two entries is passed twice and counted twice, like
the entries). Exact rules, with `m` = the learner's rank-1 meaning of v aggregated as §2.2 and
`rated_known(m)` = the §2.4 expression `wc > ww AND p_last ≥ 0.75 AND NOT marked_unknown` (the same
text as `knowledge_report_summary`'s `f.rated_known`):

```
rated_known        = #{elements e : m(e.vocab_id) exists AND rated_known(m)}
seen_not_rated     = #{elements e : m(e.vocab_id) exists AND NOT rated_known(m)}
no_evidence        = #{elements e : m(e.vocab_id) does not exist}
other_meaning_only = #{elements e in no_evidence : the learner has a row on a meaning of e.vocab_id with sense_rank ≥ 2}
```

Invariant per level: `rated_known + seen_not_rated + no_evidence = in_dictionary`. A lemma added to the
dictionary after the file's `built_at` stays in `not_in_dictionary` until the list is rebuilt (§8); the
card says "List matched to the dictionary on {built_at date}". If the file cannot be read, no counts
are shown and the card says "Word lists are unavailable right now" (E4c, §4).
**No estimated percentage in v1** (S8): the formula for a later estimate is fixed in §2.8a and
gated by TASK-1071. **JLPT card:** the not-in-LinguaDojo share is printed first ("{x} of {items} N5
words are not yet in LinguaDojo"), with the import action of §2.13 (P10).

**Next level** (P13): for the language's active list, the lowest level whose `rated_known /
in_dictionary < 0.80`; omitted when no list file is available (E4, E4c) or every level passes.

May claim: coverage of the list's words as defined. May not claim: exam readiness or pass chance,
anything about `not_in_dictionary` words, or that a community JLPT list is official.

#### 2.8a Deferred: estimated share of a level (TASK-1071, S8)

If the owner approves an estimate after validation: over the level's items in the frame,
`D_{L,b}` per band; `est_L = Σ_b D_{L,b}·K_b` (confirmation ignored — no double counting);
`Var(est_L) = Σ_b D_{L,b}²·Var_b + Σ_b D_{L,b}·K̃_b(1 − K̃_b)` with `K̃_b = clamp(K_b, 0, 1)`; for
cumulative levels pool `D` per band **before** computing the variance; rated-known shown beside,
never added. Copy: "If these words are like other words of the same frequency, you would know about
X–Y% of them."

### 2.9 Imported word list ("My word list")

Items = distinct (`vocab_id`, `sense_rank`) of active `user_word_watchlist` rows for (u, L). Buckets
as §2.8 but by **that meaning**; no `not_in_dictionary` bucket (imports create missing senses —
level-lists §1.7). No per-batch coverage (batches undercount — code-map §8). 0 rows today (F1).

### 2.10 Growth (30 / 90 days) — ADR-053

History-free (available at launch; MEASURED from rows and logs):

| Figure | Definition | de6fd05b/ja 30 d / 90 d |
|---|---|---|
| **Words practised** | distinct meanings with an outcome in `O` (§2.3) in the window | 41 / 83 |
| **Direct checks answered** | number of outcomes in `O` in the window | 164 / 318 |
| **Words met in texts** | meanings with `last_seen_at` in the window and `checks_correct + checks_wrong = 0` | 44 / 142 |
| **Not seen in 60+ days** | §2.5 (a state, shown beside the deltas) | 95 |

From snapshots (§7):
- **Anchor** for D ∈ {30, 90}: the latest snapshot with `snapshot_date ∈ [today − D − 7, today − D]`
  (UTC dates); if none and the earliest snapshot is ≥ 14 days old → that one, labelled "since
  {date}"; if the earliest is < 14 days old → "First trend on {earliest + 14 days}". Deltas are
  suppressed when the anchor's `method_version` differs from the current one.
- **Change in words rated known after a direct check** = now − anchor `rated_known_words`, always
  shown with "Direct checks in this period: {k}". When k = 0: "No direct checks in this period. Any
  change comes from your reading tests." Never "learned", "forgot", "gained" or "lost".
- **Estimate comparison** (S6): only when both the anchor's stored calibration counts (recomputed on
  **today's** frame, P9) and the answers **after** the anchor's `cal_last_answer_at` (disjoint by
  construction; `p_cal_since` in §6.1) each pass row 3–7 eligibility. `Δ = T_now − T_then`,
  `SD_diff = sqrt(SD_then² + SD_now²)`; if `|Δ| < 1.96·SD_diff` → "No clear change since {date}",
  else "Higher than on {date}" / "Lower than on {date}", with both ranges and their answer dates.
  Otherwise nothing is shown.
- **Pool change notice** (P9): if today's `N` differs from the anchor's stored `Σ frame_bands` by
  more than 5%: "The check's word pool changed from {x} to {y} words since {date}."

### 2.11 Skills (exercise kinds; S7 + P12)

- Attempts: `exercise_attempts` with `is_first_attempt`, `coalesce(source, 'practice') <> 'intro'`
  (practice and prestudy only — intro items are learning-phase drills on a word shown moments
  earlier), `created_at > as_of − 90 d`, sense in language L.
- Family = `dim_exercise_types.family` of `exercise_type` (every non-intro type is in that table —
  draft check S4).
- A family **qualifies** with ≥ 20 first attempts **and** ≥ 10 distinct meanings.
- Interval, clustered by meaning (m clusters, `p̂ = Σy/Σn`): `Var = m/(m−1)·Σ_i (y_i − p̂·n_i)² /
  (Σn)²`, `n_eff = min(Σn, p̂(1−p̂)/Var)`, then the Wilson interval at (`p̂`, `n_eff`):
  `center = (p̂ + z²/2n)/(1 + z²/n)`, `half = z·sqrt(p̂(1−p̂)/n + z²/4n²)/(1 + z²/n)`, n = `n_eff`.
  SQL returns the sufficient statistics `n, y, m, Σy², Σy·n, Σn²` per family, so
  `Σ(y_i − p̂ n_i)² = Σy² − 2p̂Σyn + p̂²Σn²`.
- **Sentence** (exact rule): among qualifying families, `strong` = highest interval lower bound,
  `weak` = lowest upper bound; shown only if `weak.hi < strong.lo`. Template: "Your first-try
  accuracy is lower in {weak kind} exercises ({weak pct}, {weak n} tries on {weak words} words) than
  in {strong kind} exercises ({strong pct}, {strong n} tries on {strong words} words)." Footnote:
  "Some kinds of exercise are harder for everyone; this compares your own results only." Card
  subtitle: "First-try accuracy, last 90 days." Never "retention", "skill level" or "weak skill".
- Display names (en): form_recognition "Recognition", meaning_recall "Recalling meanings",
  form_production "Producing words", semantic_discrimination "Telling similar words apart",
  collocation "Word partners", fluency "Speed".
- de6fd05b/ja (MEASURED counts, Appendix B K5; ESTIMATE intervals): recognition 79/84 on 17 words
  [0.87, 0.97]; telling similar words apart 17/32 on 11 words [0.35, 0.71]; producing words 38/55 on
  **9** words → "Not enough producing-words practice yet (9 of 10 words)"; recalling meanings 14/14
  on 5 words → not enough. Sentence shown: "Your first-try accuracy is lower in telling-similar-words-
  apart exercises (53%, 32 tries on 11 words) than in recognition exercises (94%, 84 tries on 17
  words)."
- No button: nothing in Practice targets a family (ladder `family_confidence` is at its default on
  295 of 296 rows — data-audit Q22).

**Family of a single outcome** (used for the "kind of exercise" shown on missed words; OQ11):
`dim_exercise_types.family`; else `intro_def_mc`, `intro_rev_mc`, `intro_read_typed`,
`intro_read_typed2` → form_recognition (see the word, recognise it or type its reading; the app files
`kanji_to_reading`/`hanzi_to_pinyin` under form_recognition — product review Q-R10);
`intro_cloze_mc` → meaning_recall; `intro_cloze_typed`, `intro_recall_typed` → form_production;
`intro_ex_use`, `intro_ex_judge` → family of `exercises.exercise_type` via `exercise_attempts.exercise_id`
(a PK join reading `exercise_type` only; all 84 intro `ex_*` first attempts carry an `exercise_id`,
statistician review R12); word quiz → form_recognition; anything else → `unmapped`.

### 2.12 Missed recently (P11 + S13)

- Per meaning, the latest outcome in `O`. **Missed recently** = latest outcome wrong **and** within
  90 days of `as_of`. Sorted by misses in the last 90 days (desc), then latest outcome (desc).
  de6fd05b/ja: **10** meanings (MEASURED, K4).
- **Flag** (shown inside the tab, never a separate list): ≥ 4 outcomes, ≥ 3 wrong among the last 5,
  and those wrong outcomes on ≥ 2 different UTC dates. Copy: "Missed {w} of your last {k} tries, on
  {d} days." de6fd05b/ja: 1 meaning.
- Each row shows the kind of exercise of its latest miss (§2.11) and flashcard lapses if any.
- May not claim the word is "hard for you" or that the learner "keeps forgetting" it.

### 2.13 What to do next (first three rules that apply; DECISION per P6, P7, S11)

| # | Condition | Button (en) | Target |
|---|---|---|---|
| 1 | no estimate (E0, E1, E1b, E1c) | "Take the vocabulary check (about {n} answers)" — n = `Σ max(0, 10 − n_b)` for E1, `7 × answers_needed_per_band` for E1b, 70 for E0/E1c | `/calibration` |
| 2 | the prestudy suggestion (§6.2 `/prestudy-suggestion`) returns a test with `unknown_share > 0.25` and, once TASK-980 exposes it, a remaining `prestudy_per_week` | "Prepare for {title}: {u} of its {n} key words are new to you" | `/test/<slug>/prestudy` |
| 3 | no evidence in the last 7 days | "Do today's session" | `/session` |
| 4 | `idle60 ≥ 5` or `missed_recently ≥ 1` | "Review in Practice" (no number) | `/session?mode=practice` (`&extra=reviews` once TASK-1043 lands) |
| 5 | estimate shown and last check answer > 60 days old | "Refresh your vocabulary check" | `/calibration` |
| 6 | fallback | "Take a test at your level" | `/tests` |

The Skills sentence is informational (no button). There is no "practise {family}" button and no
numbered review promise; nothing claims the report's words "agree with what Practice will
schedule". Copy is actions only — no praise. de6fd05b/ja today (ESTIMATE): [rule 2 if its top test
qualifies], "Review in Practice", "Take a test at your level".

### 2.14 Claim discipline in the copy

Every number carries one of three visible prefixes (i18n keys `knowledge.prefix.*`):
- **"From your answers"** — counts of logged events or rows: tracked words, words practised, direct
  checks, words met in texts, not seen in 60+ days, missed recently, list buckets `no_evidence` and
  `not_in_dictionary`, family n.
- **"Estimated"** — the calibration-sample range and frequency-group shares; always with the label
  and the answer dates.
- **"Model"** — anything that depends on `p_known`: "rated known after a direct check" (headline,
  bucket, delta) and the word sheet's "App's rating".
The "How this works" sheet states: the denominator is the check's word pool; recognition only; the
"I don't know" rule and its direction of bias; ratings are model ratings, not probabilities; which
practice is not logged per word (§2.3).

---

## 3. What each tier sees

Shell: **task mode** like the DT error profile (`templates/dual_translation_profile.html:1-47`):
Back (history → `/profile`), title "My vocabulary", subtitle = study language; one scrolling stage;
no dock. Language = `localStorage.selectedLanguageId` (as `static/js/pages/flashcards.js:3`).

### 3.1 Free and Core (`detail.level = 0`)

Cards in order:
1. **Words you know** — "Estimated" range bar (0 → N, tick at T) + label chip + basis line; the
   denominator sentence; under it "Model · Rated known after a direct check: {r} words" and "From
   your answers · Tracked: {t} words"; the disagreement line when it applies; "How this works" sheet.
2. **By word frequency** — four groups (§2.7): name, frame size, share range or "not enough", and
   measured tracked / rated-known counts.
3. **Exam word lists** (zh and ja, when a list file is uploaded) — edition and attribution; "List
   matched to the dictionary on {date}" (the file's `built_at`); per level a 4-segment bar
   (rated known / seen not rated / no evidence / not in LinguaDojo) with counts; cumulative toggle;
   footnote "Knowing a level's words is not the same as passing its exam."; JLPT not-in-LinguaDojo
   line first (§2.8). When Storage cannot be read: "Word lists are unavailable right now" (E4c).
4. **My word list** (only with active watchlist items) — 3-segment bar.
5. **Last 30 / 90 days** — `.ld-seg` toggle; words practised, direct checks, words met in texts,
   rated-known change (with its check count) or "First trend on {date}", estimate comparison when
   eligible, not seen in 60+ days.
6. **Skills** — per family: first-try accuracy bar with interval, "{n} tries on {m} words"; the
   sentence and footnote when eligible; "Not enough {kind} practice yet ({m} of 10 words)" otherwise.
7. **What to do next** — 1–3 buttons (§2.13).
8. **Pro card** — "Word by word — Pro"; body from the learner's own counts: "{t} words with their
   evidence · {m} missed recently · {k} missing words for {next level} · CSV and Anki export"
   (clauses with a zero or undefined value are omitted); one button "See what Pro includes" →
   `window.LinguaPaywall.open({reason:'bkt_report_detail'})` only if TASK-995's component exists,
   otherwise the line "Available with Pro". No blur, no scrambled rows, no modal, no repeat prompts.

Core sees exactly what Free sees (`wiki/business/pricing-plan.tech.md:128`).

### 3.2 Pro (`detail.level = 1`, or shadow preview)

Cards 1–7, then **Word by word** with a 3-way `.ld-seg`: **All words** | **Missed recently ({n})** | **Lists**.
- *All words:* search (lemma, traditional, reading, toneless pinyin; prefix); "Filter" sheet
  (evidence state, checked several times, missed recently, not seen in 30/60/90/180+ days, frequency
  group, in my word list, list + level); sort (Most useful first [default], Recently seen, Longest
  unseen, Most common, A–Z); "{matching} words"; rows on phones / `.table` at ≥ 768 px: word (+
  traditional), reading, gloss, **evidence lead** (§2.4), state chip, "tests ✓{tc} ✗{tw}", "checks
  ✓{cc} ✗{cw}", frequency group, "Not seen for {n} days" tag when ≥ 60, ladder ("Intro" / "Ring {n}"),
  flashcard lapses; "Load more" (50 per page).
- *Missed recently:* rows of §2.12 with "Latest miss: {kind}, {date}" and the flag; action bar "Add
  these {n} words to my word list" (§3.4).
- *Lists:* picker (exam list + level, or My word list; remembered in `localStorage` `kn.listSel`,
  try/catch) → bucket chips → words, most common first; action bar (§3.4); "Export this list".
- **Word sheet** (tap a row): meaning header; evidence lead; answers list (newest first, ≤ 30:
  kind, date, right / wrong / skipped, exercise kind); "about {k} other updates are not listed one by
  one (prestudy warm-ups, flashcard ratings, translation practice, reading inferences)"; flashcard
  and ladder state; "Model · App's rating: rates this word as known / not yet as known, after your
  answer on {date}. This is a model rating, not a probability."
- **Export** menu at the top of Word by word: "Spreadsheet (CSV)" and "Anki (text)"; exports the
  current tab and filter (§6.6).

### 3.3 Shadow mode (before billing enforcement; `level = 0`, `enforced = false`)

Follows TASK-980's shadow contract (`wiki/tasklist/billing.tasks.md:234`; OQ4): the API logs
`entitlement_shadow_deny` and serves Pro data; the page renders the Pro view plus one neutral note
above Word by word: "Word by word will be part of Pro when plans launch." No upsell button. Demand
is measured only by `knowledge_pro_intent` (§6.4), never by `entitlement_shadow_deny`.

### 3.4 Study actions (ADR-056)

- **"Add these {n} words to my word list"** (Lists tab buckets `no_evidence` and `seen_not_rated`;
  My word list never; Missed recently tab): takes up to 50 lemmas of the current view, most common
  first, and `POST /api/word-list/submit` with `{words, language: <code>}` (F18). 202 → toast "Added.
  They will appear in your daily practice." and a link to `/word-list`; 429 → the server's message
  (in-flight / daily cap / busy). Static helper text: "Up to 50 words at a time, 5 lists a day."
  Dictionary words are free for Core and Pro (`wiki/business/pricing-plan.tech.md:126,401`).
- **`not_in_dictionary` words:** no button in v1. TASK-1060 adds "Add {n} new words (8 credits each)"
  through billing's credit spend path once it exists and OQ30 is answered.
- **"Review in Practice"** and **"Prepare for {test}"** — §2.13.

### 3.5 Trial, downgrade, school and tutor seats

Trial (21-day Pro): level 1. Downgrade Pro → Core: level 0 from the end of the paid period; data
kept; the Pro card adds "Your full history is kept." `professional`, `school_student`, tutor seats:
level 1 (`wiki/business/pricing-plan.tech.md:128`).

---

## 4. Empty and low-data states, and minimum data per metric

| State | Condition (exact) | What shows |
|---|---|---|
| **E0 nothing yet** | 0 UVK rows for (u, L) **and** 0 definition-mode answers ever | One card: "We don't know your {language} vocabulary yet." Buttons "Take the vocabulary check" (`/calibration`), "Take a test" (`/tests`). No zeros anywhere; other cards hidden. |
| **E1 not enough check answers** | §2.6 row 1 | Card 1: tracked and rated-known lines plus "To estimate your vocabulary we need about 10 check answers at each of 7 frequency levels: {have} of 70 so far." + check button. Frequency card shows measured counts only. |
| **E1c check out of date** | §2.6 row 2 | "Your vocabulary-check answers are more than 6 months old (last on {date}). A short re-check refreshes the estimate." + check button. |
| **E1b too uncertain** | §2.6 row 8 | "Your answers so far don't pin the number down yet. About {k} more answers at each level would." + check button. |
| **E2 few tracked words** | tracked words < 50 | Note in card 1: "Most of what we know comes from {t} words." |
| **E3 stale** | no `last_seen_at` in 30 days and tracked > 0 | "Last practice {d} days ago." Next-step rule 3 promoted to first. No "fading"/"due" copy. |
| **E4 no list for language** | en, or no list file uploaded yet for the language's list code (§8) | Exam card hidden. |
| **E4b level without matches** | `in_dictionary = 0` | "None of this level's words are in LinguaDojo yet ({items} words)." |
| **E4c lists unavailable** | summary `lists_unavailable = true` (Storage unreadable and nothing cached, or `knowledge_list_buckets` failed — §8) | Exam card shows only "Word lists are unavailable right now."; the Lists tab shows the same line; every other card renders normally (HTTP 200, never E8/E9). |
| **E5 filter empty** (Pro) | `matching = 0` | "No words match." + "Clear filters". |
| **E6 no imported list** | 0 active watchlist items | Summary hides card 4; Lists tab shows "Add a word list (textbook, class, exam) to see your coverage" → `/word-list`. |
| **E7 no history** | no snapshot ≥ 14 days old | Growth shows history-free figures and "First trend on {date}". |
| **E8 service not ready** | API 503 `SERVICE_UNAVAILABLE` or 404 (flag off) | "This page isn't available yet." |
| **E9 error** | network / 5xx | "Couldn't load your vocabulary. Try again." + retry. |
| **E10 model vs check** | `rated_known_in_frame > hi` | Disagreement line under card 1 (§2.6). |

| Metric | Minimum to show |
|---|---|
| Estimated range or "fewer than" | every band `n_b ≥ 10` distinct lemmas in 180 days (§2.6) |
| "Medium" / "Good" | every `n_b ≥ 20` / `≥ 30` plus the `rel'` gates |
| Frequency-group share | headline eligible and group half-width ≤ 0.15 |
| Tracked, rated known, practised, met in texts, idle, missed, list buckets | ≥ 1 tracked row (else E0) |
| Family accuracy | ≥ 20 non-intro first attempts and ≥ 10 meanings in 90 days |
| Family sentence | ≥ 2 qualifying families with separated clustered intervals |
| Growth delta | an anchor snapshot ≥ 14 days old (§2.10) |
| Estimate comparison | both disjoint answer sets eligible (§2.10) |

---

## 5. Database Impact

No existing table, column, index or function is altered by the core tasks. `dim_vocabulary.level_tag`
is not touched (F11). New objects ship in migration files with rollback files, applied by the owner
to production. Every function follows `migrations/CLAUDE.md:27-70` (SECURITY INVOKER, pinned
`search_path`, REVOKE from PUBLIC/anon/authenticated, GRANT to service_role; new tables get RLS and
REVOKE in the same file). See [[database/schema.tech]].

### 5.1 `user_knowledge_snapshots` (file `migrations/knowledge_report_foundation.sql`)

```sql
CREATE TABLE public.user_knowledge_snapshots (
  user_id                  uuid        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  language_id              smallint    NOT NULL REFERENCES public.dim_languages(id),
  snapshot_date            date        NOT NULL,              -- UTC date of the job run
  method_version           smallint    NOT NULL DEFAULT 1,    -- bump when any §2 definition changes
  tracked_words            integer     NOT NULL,
  tracked_meanings         integer     NOT NULL,
  rated_known_words        integer     NOT NULL,
  checked_meanings         integer     NOT NULL,
  missed_recent_meanings   integer     NOT NULL,
  idle60_meanings          integer     NOT NULL,
  practised_30_meanings    integer     NOT NULL,
  direct_checks_30         integer     NOT NULL,
  cal_definition_language_id smallint  REFERENCES public.dim_languages(id),   -- D*; NULL = no answers
  cal_bands                smallint[]  CHECK (cal_bands IS NULL OR array_length(cal_bands, 1) = 21),
                                       -- n_1..n_7, s_1..s_7, c_1..c_7 (latest answer per lemma, rank 1, window)
  frame_bands              integer[]   CHECK (frame_bands IS NULL OR array_length(frame_bands, 1) = 7),
  cal_answers              integer     NOT NULL DEFAULT 0,
  cal_first_answer_at      timestamptz,
  cal_last_answer_at       timestamptz,
  est_kind                 smallint    NOT NULL DEFAULT 0 CHECK (est_kind BETWEEN 0 AND 2),  -- 0 none, 1 range, 2 upper only
  est_lo                   integer,
  est_hi                   integer,
  est_label                smallint    CHECK (est_label BETWEEN 1 AND 3),                    -- 1 rough, 2 medium, 3 good
  source                   text        NOT NULL DEFAULT 'nightly' CHECK (source IN ('nightly','manual')),
  computed_at              timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, language_id, snapshot_date)
);
ALTER TABLE public.user_knowledge_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.user_knowledge_snapshots FROM PUBLIC, anon, authenticated;
-- No policies: only Flask (service role) reads and writes it.
```

**Size** (MEASURED composite of these columns: 256 B, Appendix B K8; ESTIMATE stored ≈ 256 + 4 B line
pointer + ~36 B PK entry ≈ **300 B/row**): per pair 110 KB a year daily; with retention (daily for 120
days, then Mondays) ≈ 155 rows (≈ 46 KB) in year one and ≈ 52 rows (≈ 16 KB) per later year. Today's 5
pairs: ≈ 0.23 MB in year one (≤ 0.55 MB unpruned); 50 pairs ≈ 2.3 MB; 1,000 pairs ≈ 46 MB in year one
(a paid-plan scale).

### 5.2 Exam-list files in Storage (bucket file `migrations/reference_data_bucket.sql`; files uploaded by TASK-1053)

No list table is created ([[decisions/ADR-054-exam-word-lists-in-storage]], revised 2026-11-18). The
lists are JSON files in a new private bucket, created by a separate small migration in TASK-1034
(pattern: the `exercise-content` bucket, `migrations/exercise_content_storage.sql:376-378`):

```sql
-- migrations/reference_data_bucket.sql  (owner applies)
BEGIN;
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('reference-data', 'reference-data', false, 5242880, ARRAY['application/json'])   -- 5 MiB per file
ON CONFLICT (id) DO NOTHING;
COMMIT;
-- No storage.objects policy for this bucket: only the service role (which bypasses RLS) reads or writes it.

-- migrations/reference_data_bucket_rollback.sql
BEGIN;
DO $guard$
BEGIN
  IF EXISTS (SELECT 1 FROM storage.objects WHERE bucket_id = 'reference-data') THEN
    RAISE EXCEPTION 'reference_data_bucket rollback: delete the bucket''s files first (Storage dashboard or API)';
  END IF;
END
$guard$;
DELETE FROM storage.buckets WHERE id = 'reference-data';
COMMIT;
```

If the project refuses a direct `DELETE` on `storage.buckets` (unverified here), the owner removes the
empty bucket in the Storage dashboard instead. ADR-049's rollback goes further and never deletes its
bucket, pointing to the dashboard (`migrations/exercise_content_storage_rollback.sql:18-20`).

**Paths and versions.** One folder per list: `word-lists/<list_code>/v<N>.json`, `N` = 1, 2, 3, …
Files are immutable (`SupabaseStorageBackend.put` sends `x-upsert: false` and raises `AlreadyExists`,
`services/exercise_content/backends.py:485-496`); a change is a new version. There is no manifest:
the reader lists `word-lists/<list_code>/` and takes the highest `N` **as a number** (`list()` returns
paths sorted as text, `backends.py:548`, so `v10` sorts before `v9`). Only names matching `^v([1-9][0-9]*)\.json$` count.

**File schema, version 1** (UTF-8, compact JSON: `separators=(',', ':')`, `ensure_ascii=False`):

```json
{"schema": 1,
 "list_code": "hsk30_2025",
 "name": "HSK 3.0 (2025 syllabus)",
 "edition": "2025-11 CLEC syllabus",
 "is_official": true,
 "language_id": 1,
 "level_codes": ["1", "2", "3", "4", "5", "6", "7-9"],
 "source_url": "https://github.com/krmanik/HSK-3.0/…/<commit>/…",
 "source_sha256": "<64 hex>",
 "licence": "CC BY-SA 4.0",
 "attribution": "<shown verbatim in the UI and in list exports>",
 "allow_export": false,
 "built_at": "2026-…T…Z",
 "built_from": {"dictionary_max_vocab_id": 0, "dictionary_lemma_count": 0},
 "entries": [[1, "爱", null, 1234, 1], [7, "…", null, null, null]]}
```

| Field | Type | Rule |
|---|---|---|
| `schema` | integer | `1`. A reader rejects any other value (§8). |
| `list_code` | text | `^[a-z0-9_]{3,40}$`; equals the folder name. |
| `name`, `edition` | text | Shown in the UI. |
| `is_official` | boolean | `false` for community JLPT lists (drives the "unofficial" label). Added to the 2026-11-18 brief's field list because the UI needs it. |
| `language_id` | smallint | 1 (zh) or 3 (ja); must equal the language the list code is registered for (§8 `LIST_CODES_BY_LANGUAGE`). |
| `level_codes` | text[] | Display order; `{1,2,3,4,5,6,7-9}` or `{N5,N4,N3,N2,N1}`. |
| `source_url`, `source_sha256` | text | Provenance of the source file (pinned URL with commit; sha256 of the file read). `source_sha256` added for the same reason as `is_official`. |
| `licence`, `attribution` | text | Attribution is rendered from here in the UI and in list exports. |
| `allow_export` | boolean | List-subset export permitted (OQ3). Changing it means a new version. |
| `built_at` | text (ISO-8601 UTC) | When the builder matched the list to the dictionary; shown as "List matched to the dictionary on {date}". |
| `built_from` | object | `dictionary_max_vocab_id` = `max(id)` and `dictionary_lemma_count` = `count(*)` of the `dim_vocabulary` rows read for `language_id`. |
| `entries[i]` | `[level_idx, form, reading, vocab_id, match_kind]` | `level_idx` smallint, 1-based index into `level_codes` (the headword's lowest level); `form` = headword; `reading` = kana for JLPT, `null` for HSK; `vocab_id` = integer or `null` (= "not yet in LinguaDojo"); `match_kind` = 1–6 (§8 methods: 1 lemma exact, 2 kana-only = lemma, 3 kana-only = reading, 4 reading + shared kanji, 5 kanji word whose kana form is a lemma, 6 erhua stripped), `null` exactly when `vocab_id` is `null`. |

`item_no` = i + 1 (the entry's 1-based position in `entries`, source line order); stable within one
file version only.

**Size** (ESTIMATE, 2026-11-18): entries parsed from the krmanik `New HSK (2025)` `.txt` files and the
jamsinclair `n5…n1.csv` files with a simplified version of the §8 normalisation, `vocab_id`s replaced by
random 5-digit integers at the measured per-level match rates (F12), and the header above filled with
realistic text:

| List | Entries | Matched (ESTIMATE) | Raw JSON | Per entry | gzip -9 | Parsed in Python (per process) |
|---|---|---|---|---|---|---|
| `hsk30_2025` | 10,902 (research: 10,896) | ~6.6k | ≈ 292 KB | ≈ 27 B | ≈ 80 KB (27%) | ≈ 2.3 MB |
| `jlpt_waller` | 7,997 (research: ≤ 8,293) | ~2.3k | ≈ 300 KB | ≈ 37 B | ≈ 82 KB (27%) | ≈ 2.1 MB |

The header is ≈ 0.7 KB. Every file is ~17× under the 5 MiB bucket limit. Files are stored as plain
`application/json` (not pre-compressed), as in ADR-049. The parsed size was measured with
`tracemalloc` on the synthetic files (so it is itself an ESTIMATE for the real files).

**Database cost:** one `storage.buckets` row (< 1 KB, ESTIMATE) and one `storage.objects` row per file
version (595 B average, MEASURED in [[decisions/ADR-049-exercise-content-in-storage]]): two files ≈
**1.2 KB**; each later version ≈ +0.6 KB. File bytes (~0.6 MB for both lists, plus ~0.3 MB per later
version of one list) count against the Free plan's 1 GB of file storage, **not** the 500 MB database
cap. Egress (ESTIMATE): one ~0.3 MB `get` per list per app process when it starts or sees a new
version, plus one `list` request per list per process every 6 h.

### 5.3 Byte budget

| Object | At creation | Year one | Gate |
|---|---|---|---|
| 8 functions (catalog) | ~20–45 KB (ESTIMATE) | same | owner applies |
| `user_knowledge_snapshots` | ~24 KB empty | +0.23–0.55 MB at today's 5 pairs | owner applies |
| `reference-data` bucket row | < 1 KB (ESTIMATE) | same | owner applies (TASK-1034) |
| list file metadata (`storage.objects`) | — | ~1.2 KB for two files, +~0.6 KB per later version | owner uploads (TASK-1053); waits for OQ2 and OQ3 only — **no database size gate** |
| list file bytes | — | ~0.6 MB of Storage (outside the database cap) | — |
| exports | 0 B (generated per request, never stored) | 0 B | — |
| new indexes on existing tables | **none** (performance §6) | 0 B | — |
| **total (database)** | **≤ ~0.2 MB** | **≤ ~0.8 MB** | |

Indirect growth outside this budget (INFERENCE): "Add these words to my word list" makes the
existing import path generate ladder exercises for in-dictionary senses that have none (F18; about
19 KB per sense in `exercises` before ADR-049's content move — level-lists §6.3). Counted under OQ30,
which still waits for the database size gate (OQ13).

### 5.4 Tables read (writes only to the snapshot table)

`user_vocabulary_knowledge` (`idx_uvk_user_language`), `user_flashcards`
(`user_flashcards_user_id_sense_id_key`), `user_word_ladder` (`user_word_ladder_pkey`),
`user_word_watchlist`, `dim_word_senses` (`dim_word_senses_pkey`, `uq_sense_def_level`,
`idx_senses_rank`), `dim_vocabulary` (`dim_vocabulary_pkey`, `idx_vocab_lemma_lookup`),
`dim_exercise_types`, `exercises` (PK, `exercise_type` only), `calibration_sessions`
(`idx_calibration_sessions_user`), `calibration_responses` (`idx_calibration_responses_session`),
`calibration_anchor_pool`, `calibration_anchor_blocklist`, `exercise_attempts` (`idx_ea_user_created`,
`idx_ea_user_sense_type`), `word_quiz_results` (`idx_wqr_user`), `question_attempt_results`
(`idx_qar_user`), `questions` (pkey).

---

## 6. API / RPC Surface

All SQL functions: `LANGUAGE sql`, `STABLE` (prune: `plpgsql VOLATILE`; the two list functions:
`plpgsql STABLE`, for their array-length check), `SECURITY INVOKER`,
`SET search_path = public, pg_temp`, `REVOKE ALL … FROM PUBLIC, anon, authenticated`, `GRANT EXECUTE
… TO service_role`. Flask calls them with the service role after verifying the JWT and always passes
`p_user_id = g.current_user_id` (never a request value). Each returns one `jsonb` value (F14). See
[[api/rpcs.tech]].

### 6.1 SQL functions

Files: `migrations/knowledge_report_foundation.sql` (§5.1, `knowledge_frame_bands`,
`knowledge_active_pairs`, `knowledge_snapshots_prune`), `reference_data_bucket.sql` (§5.2; the bucket,
no function), `knowledge_report_summary.sql`, `knowledge_report_words.sql`,
`knowledge_report_word_detail.sql`, `knowledge_report_list_words.sql` (`knowledge_list_buckets` and
`knowledge_report_list_words`); each with `_rollback.sql`. No function reads a list table: exam-list
items reach SQL only as `integer[]` / `smallint[]` arguments built by Python from the list file
(ADR-054).

#### `knowledge_frame_bands(): jsonb`
- **Purpose:** frame sizes N_b for every (L, D) (§2.1).
- **SQL:** `SELECT p.word_language_id, p.definition_language_id, p.zipf_band, count(DISTINCT p.vocab_id)
  FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id AND s.sense_rank = 1
  WHERE p.has_embedding AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id =
  p.sense_id) GROUP BY 1, 2, 3`, folded into `{"3:2":[577,425,621,655,537,283,77], …}` (key
  `"<L>:<D>"`, arrays for bands 1…7, missing bands as 0).
- **Errors:** none. **Auth:** service_role. **Side effects:** none. Cached per process for 3,600 s.

#### `knowledge_active_pairs(p_since timestamptz): jsonb`
- **Returns:** `[{"user_id":…, "language_id":…}]` = pairs with ≥ 1 UVK row, UNION pairs with a
  definition-mode answer after `p_since`. **Auth:** service_role. **Side effects:** none.

#### `knowledge_snapshots_prune(p_keep_daily_days integer DEFAULT 120): integer`
- Deletes rows with `snapshot_date < current_date − p_keep_daily_days AND extract(isodow FROM
  snapshot_date) <> 1`; returns rows deleted. **Errors:** `p_keep_daily_days < 35` → `RAISE EXCEPTION
  'keep_daily_days_too_small'`. `LANGUAGE plpgsql VOLATILE`. **Auth:** service_role. **Side effects:**
  deletes snapshot rows.

#### `knowledge_report_summary(p_user_id uuid, p_language_id smallint, p_as_of timestamptz DEFAULT now(), p_window_days integer DEFAULT 180, p_cal_since timestamptz[] DEFAULT '{}'): jsonb`
- **Purpose:** every aggregate the summary page and the snapshot job need, in one statement (no
  MATERIALIZED CTE, no GROUPING SETS over all rows — performance §5), **except exam-list buckets**,
  which `knowledge_list_buckets` counts from arrays (revised 2026-11-18; the snapshot job needs no list
  data).
- **SQL shape:**
  ```sql
  WITH r AS (SELECT k.sense_id, k.p_known, k.status, k.evidence_count, k.comprehension_correct cc,
                    k.comprehension_wrong cw, k.word_test_correct wc, k.word_test_wrong ww,
                    k.last_evidence_at, k.created_at, s.vocab_id, s.sense_rank
             FROM user_vocabulary_knowledge k JOIN dim_word_senses s ON s.id = k.sense_id
             WHERE k.user_id = p_user_id AND k.language_id = p_language_id),
  m AS (SELECT vocab_id, sense_rank,
          (array_agg(p_known ORDER BY last_evidence_at DESC, evidence_count DESC, sense_id))[1] p_last,
          max(last_evidence_at) last_seen_at, min(created_at) first_seen_at,
          sum(cc) cc, sum(cw) cw, sum(wc) wc, sum(ww) ww,
          bool_or(status = 'user_marked_unknown') marked_unknown
        FROM r GROUP BY vocab_id, sense_rank),
  o AS (SELECT s.vocab_id, s.sense_rank, ea.created_at at, ea.is_correct
          FROM exercise_attempts ea JOIN dim_word_senses s ON s.id = ea.sense_id
         WHERE ea.user_id = p_user_id AND ea.is_first_attempt AND s.word_language_id = p_language_id
           AND ea.created_at <= p_as_of
        UNION ALL
        SELECT s.vocab_id, s.sense_rank, w.created_at, w.is_correct
          FROM word_quiz_results w JOIN dim_word_senses s ON s.id = w.sense_id
         WHERE w.user_id = p_user_id AND s.word_language_id = p_language_id AND w.created_at <= p_as_of),
  ol AS (SELECT vocab_id, sense_rank, at, is_correct,
                row_number() OVER (PARTITION BY vocab_id, sense_rank ORDER BY at DESC) rn FROM o),
  f AS (SELECT m.*, v.frequency_rank z, coalesce(calibration_zipf_band(v.frequency_rank), 0) band,
          (m.wc > m.ww AND m.p_last >= 0.75 AND NOT m.marked_unknown) rated_known,
          (SELECT NOT l.is_correct FROM ol l WHERE l.vocab_id = m.vocab_id AND l.sense_rank = m.sense_rank AND l.rn = 1) latest_wrong,
          (SELECT l.at FROM ol l WHERE l.vocab_id = m.vocab_id AND l.sense_rank = m.sense_rank AND l.rn = 1) latest_at
        FROM m JOIN dim_vocabulary v ON v.id = m.vocab_id),
  cal AS (SELECT cr.anchor_vocab_id v, cr.zipf_band band, cr.answered_at, cr.chosen_sense_id, cr.is_correct,
                 cs.definition_language_id d
            FROM calibration_sessions cs JOIN calibration_responses cr ON cr.session_id = cs.id
            JOIN dim_word_senses a ON a.id = cr.anchor_sense_id AND a.sense_rank = 1
           WHERE cs.user_id = p_user_id AND cs.word_language_id = p_language_id AND cs.mode = 'definition'
             AND cr.answered_at IS NOT NULL AND cr.answered_at <= p_as_of)
  -- + dstar (§2.6 step 2), win / alltime / since[i] (DISTINCT ON (v) … ORDER BY v, answered_at DESC),
  --   fam (§2.11 sufficient statistics), wl (§2.9); no exam-list CTE (knowledge_list_buckets)
  SELECT jsonb_build_object(...);
  ```
- **Returns** (de6fd05b/ja values MEASURED where shown — Appendix B K2–K5; `"…"` = not measured):
  ```json
  {"as_of":"2026-11-17T…Z","language_id":3,"method_version":1,
   "tracked":{"words":251,"meanings":251,"rows":251},
   "states":{"missed_last":10,"rated_known":69,"checked":30,"not_checked":142},
   "rated_known_words":69,"rated_known_checked2_words":22,
   "idle60_meanings":95,"last_seen_at":"2026-11-15T…Z",
   "activity":{"d30":{"practised_meanings":41,"direct_outcomes":164,"met_in_texts":44},
               "d90":{"practised_meanings":83,"direct_outcomes":318,"met_in_texts":142}},
   "missed_recent":{"meanings":10,"flagged":1},
   "groups":[{"band":0,"tracked_words":3,"rated_known_words":"…"},{"band":1,"tracked_words":18,"rated_known_words":"…"}],
   "calibration":{"definition_language_id":2,"window_days":180,
     "bands":[[26,16,7],[23,16,5],[26,14,9],[24,12,9],[25,9,13],[25,8,15],[23,0,21]],
     "alltime_n":[26,23,26,24,25,25,23],
     "first_answer_at":"2026-09-13T…Z","last_answer_at":"2026-11-15T…Z","answers":172,
     "since":[],"rated_known_in_frame":"…"},
   "families":[{"family":"form_recognition","n":84,"y":79,"m":17,"syy":"…","syn":"…","snn":"…"},
               {"family":"semantic_discrimination","n":32,"y":17,"m":11,"syy":"…","syn":"…","snn":"…"}],
   "watchlist":{"items":0,"rated_known":0,"seen_not_rated":0,"no_evidence":0}}
  ```
  `bands` entries are `[n, s, c]` for bands 1…7; `since` has one `{"since":ts,"bands":[…],"first_answer_at",
  "last_answer_at"}` per element of `p_cal_since`. There is no `lists` key (the summary service adds
  `lists` from the list files and `knowledge_list_buckets` — §6.3).
- **Errors:** none raised; no data → zero counts and empty arrays (Flask turns that into E0).
  **Auth:** service_role. **Side effects:** none.

#### `knowledge_report_words(p_user_id uuid, p_language_id smallint, p_definition_language_id smallint, p_filters jsonb DEFAULT '{}', p_sort text DEFAULT 'useful', p_cursor jsonb DEFAULT NULL, p_limit integer DEFAULT 50, p_as_of timestamptz DEFAULT now()): jsonb`
- **Purpose:** one page of meanings (Pro table, Missed recently tab, export chunks).
- **`p_filters` keys** (all optional; validated by Flask, read defensively with casts): `states
  text[]` (§2.4 codes), `checked_several bool`, `missed_recent bool`, `idle_days int`
  (30|60|90|180: `last_seen_at <= p_as_of − idle_days`), `bands int[]` (0–7), `in_word_list bool`,
  `vocab_ids int[]` (the lemma is in the array and the meaning is rank 1; Flask builds it from the
  list file for the `list` + `level` request parameters — that level's in-dictionary `vocab_id`s, ≤
  ~11k elements; revised 2026-11-18, replaces `list_code` + `level`), `q text` (already
  LIKE-escaped). Search: `v.lemma LIKE q||'%' ESCAPE '\'` OR `v.lemma_traditional LIKE …` OR `v.reading
  LIKE …` OR (zh and q ASCII) toneless key LIKE key(q)||'%', key(x) =
  `regexp_replace(lower(translate(split_part(x,' (',1), 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü',
  'aaaaeeeeiiiioooouuuuvvvvv')), '[^a-z]', '', 'g')` over the native rank-1 `pronunciation` (MEASURED
  format: 7,766 of 7,776 zh rank-1 pronunciations are tone-marked, 1,336 also carry a numbered copy in
  brackets — draft check S6).
- **Sort keyset:** 5-tuple `(kt text, k1 float8, k2 float8, vocab_id, sense_rank)` ascending; predicate
  `(kt,k1,k2,vocab_id,sense_rank) > (cursor…)`; fetch `p_limit + 1` rows to decide `next_cursor`.

  | sort | kt | k1 | k2 |
  |---|---|---|---|
  | `useful` | `''` | tier: 0 `missed_last` · 1 `checked` · 2 `not_checked` · 3 `rated_known` | `-coalesce(zipf, -1)` |
  | `recent` / `oldest` | `''` | `-epoch(last_seen_at)` / `epoch(last_seen_at)` | 0 |
  | `common` | `''` | `-coalesce(zipf, -1)` | 0 |
  | `lemma` | `lemma COLLATE "C"` | 0 | 0 |
  | `id` (export) | `''` | 0 | 0 |
- **Returns:** `{"rows":[{vocab_id, sense_rank, lemma, lemma_traditional, reading, pronunciation, gloss,
  gloss_language_id, zipf, band, state, app_rates_known, checks_correct, checks_wrong, tests_correct,
  tests_wrong, last_direct:{at, correct, family}|null, first_seen_at, last_seen_at, idle_days,
  missed_recent, missed_flag:{wrong, tries, days}|null, misses_90, ladder_ring, ladder_state,
  flashcard_lapses, in_word_list}], "next_cursor":[…]|null, "matching":int, "as_of":ts}`.
  `app_rates_known = p_last >= 0.75` (export and word sheet only). Gloss = first existing of
  (vocab_id, sense_rank, `p_definition_language_id`, 'standard') → (…, 'simple') → native standard, via
  `uq_sense_def_level`; pronunciation from the native standard row; gloss, pronunciation and ladder are
  joined **only for the page rows**. `p_limit` clamped in SQL to 1…1000.
- **Errors:** none raised (Flask rejects bad input with 400 first). **Auth:** service_role.
  **Side effects:** none.

#### `knowledge_report_word_detail(p_user_id uuid, p_language_id smallint, p_vocab_id integer, p_sense_rank smallint, p_definition_language_id smallint, p_as_of timestamptz DEFAULT now()): jsonb`
- **Returns:** `null` when the learner has no row for the meaning; else `{meaning:{…row fields…},
  rows:[{sense_id, definition_language_id, definition_level, p_known, evidence_count, cc, cw, wc, ww,
  last_evidence_at, created_at}], events:[{at, kind, correct, skipped, family, detail}], itemised:int,
  other_updates:int, flashcard:{stability, lapses, reps, due_date, state}|null, ladder:{current_ring,
  current_level, word_state}|null}`. Events (newest first, ≤ 30): `test_question`
  (`question_attempt_results ⋈ questions` where a meaning `sense_id` ∈ `questions.sense_ids`; marked
  "linked by today's question links"), `exercise` (`exercise_attempts`: type, family, source, first
  attempt), `word_quiz`, `vocabulary_check` (`calibration_responses` with `anchor_vocab_id =
  p_vocab_id`; skip shown as skipped). `itemised` = test_question + first-attempt exercise + word_quiz
  events; `other_updates = greatest(0, Σ evidence_count − itemised)`, shown as "about {k}".
- **Errors:** none raised. **Auth:** service_role. **Side effects:** none.

#### `knowledge_list_buckets(p_user_id uuid, p_language_id smallint, p_vocab_ids integer[], p_level_idx smallint[]): jsonb`
- **Purpose:** the SQL-side buckets of §2.8 for one exam list, per level (new 2026-11-18, ADR-054).
- **Arguments:** `p_vocab_ids` / `p_level_idx` — parallel arrays, one element per **in-dictionary**
  entry of the list file (entries with `vocab_id = null` are never passed; Python counts them as
  `not_in_dictionary`); order irrelevant; duplicates counted per element. Built by `WordList.bucket_arrays()`
  (§8). Size: ~6.6k elements for today's HSK matches, ≤ 10,896 if every entry matched; request body
  ≈ 53 KB today and ≤ ~90 KB at full match (ESTIMATE: 5-digit ids, compact JSON). No request-size limit
  for PostgREST RPC bodies is recorded in this wiki; TASK-1049 verifies a full-size call.
- **SQL shape:**
  ```sql
  WITH it AS (SELECT t.vocab_id, t.level_idx FROM unnest(p_vocab_ids, p_level_idx) AS t(vocab_id, level_idx)),
  r AS (SELECT s.vocab_id, s.sense_rank, k.sense_id, k.p_known, k.status, k.evidence_count,
               k.word_test_correct wc, k.word_test_wrong ww, k.last_evidence_at
          FROM user_vocabulary_knowledge k JOIN dim_word_senses s ON s.id = k.sense_id
         WHERE k.user_id = p_user_id AND k.language_id = p_language_id),
  m AS (SELECT vocab_id,
               coalesce(sum(wc) > sum(ww)
                        AND (array_agg(p_known ORDER BY last_evidence_at DESC, evidence_count DESC, sense_id))[1] >= 0.75
                        AND NOT bool_or(status = 'user_marked_unknown'), false) rated_known   -- §2.4, same text as the summary
          FROM r WHERE sense_rank = 1 GROUP BY vocab_id),
  o AS (SELECT DISTINCT vocab_id FROM r WHERE sense_rank >= 2)
  SELECT jsonb_build_object('levels', coalesce(jsonb_agg(jsonb_build_object(
           'level_idx', level_idx, 'in_dictionary', n, 'rated_known', rk, 'seen_not_rated', snr,
           'no_evidence', ne, 'other_meaning_only', omo) ORDER BY level_idx), '[]'::jsonb))
  FROM (SELECT it.level_idx, count(*) n,
               count(*) FILTER (WHERE m.rated_known) rk,
               count(*) FILTER (WHERE NOT m.rated_known) snr,
               count(*) FILTER (WHERE m.vocab_id IS NULL) ne,
               count(*) FILTER (WHERE m.vocab_id IS NULL AND o.vocab_id IS NOT NULL) omo
          FROM it LEFT JOIN m ON m.vocab_id = it.vocab_id LEFT JOIN o ON o.vocab_id = it.vocab_id
         GROUP BY it.level_idx) x;
  ```
- **Returns:** `{"levels":[{"level_idx":1,"in_dictionary":…,"rated_known":…,"seen_not_rated":…,
  "no_evidence":…,"other_meaning_only":…}, …]}`; levels with no in-dictionary entry are absent (Python
  fills them with zeros). `in_dictionary` here equals Python's count of non-null entries for the level
  (a mismatch is logged as `word_list_bucket_mismatch` and the list is shown as unavailable).
- **Language:** `LANGUAGE plpgsql STABLE` (not `sql`): `IF array_length(p_vocab_ids, 1) IS DISTINCT
  FROM array_length(p_level_idx, 1) THEN RAISE EXCEPTION 'list_arrays_mismatch'; END IF; RETURN (<the
  query above>);` — `unnest(a, b)` would otherwise pad the shorter array with NULLs and miscount.
- **Errors:** `list_arrays_mismatch` (unequal lengths); NULL or empty arrays → `{"levels":[]}`.
  **Auth:** service_role. **Side effects:** none.

#### `knowledge_report_list_words(p_user_id uuid, p_language_id smallint, p_vocab_ids integer[], p_item_nos integer[], p_bucket text, p_definition_language_id smallint, p_cursor jsonb DEFAULT NULL, p_limit integer DEFAULT 50): jsonb`
- **Purpose:** the words of one list level (or of the levels ≤ it when cumulative) in one bucket, or
  of the virtual `my_word_list` (§2.9). Revised 2026-11-18: the list's items arrive as arrays.
- **Arguments:** `p_vocab_ids` / `p_item_nos` — parallel arrays built by Python from the latest list
  file: the in-dictionary entries of the chosen level(s), `item_no` = the entry's 1-based position in
  `entries` (§5.2). **Both NULL selects `my_word_list`** (items = active `user_word_watchlist` meanings
  of (u, L), bucketed by the chosen meaning, no `not_in_dictionary`; keyset as before). `LANGUAGE
  plpgsql STABLE` with the same length check as `knowledge_list_buckets` (unequal lengths, or exactly
  one of the two NULL → `RAISE EXCEPTION 'list_arrays_mismatch'`). `p_bucket` ∈
  `rated_known | seen_not_rated | no_evidence` (Flask validates; for exam lists the rules of §2.8 on the
  rank-1 meaning). The `not_in_dictionary` bucket never reaches SQL: Python pages those entries straight
  from the file, in `item_no` order, with the same cursor shape `[1, item_no]` (their `zipf` is NULL, so
  `-coalesce(zipf, -1) = 1`).
- **Returns:** `{"rows":[{item_no, vocab_id, sense_rank, lemma, gloss, zipf, band, state, last_seen_at}],
  "next_cursor":[k1, item_no]|null, "matching":int}` ordered by `(-coalesce(zipf, -1), item_no)`; gloss
  as `knowledge_report_words`. Python adds `headword`, `reading` and `level` from entry `item_no` and
  `attribution`, `allow_export`, `built_at` from the file metadata before responding.
- **Errors:** `list_arrays_mismatch` only. **Auth:** service_role. **Side effects:** none.

### 6.2 Flask routes (`routes/knowledge.py`, `knowledge_bp`, `url_prefix='/api/knowledge'`)

Decorators: `@supabase_jwt_required` → `@api_errors("…")` → `@require_language_id`, then: if
`g.current_user_id` is not a UUID (including the batch token's `'service-account'`,
`middleware/auth.py:234-243`) → 403 `FORBIDDEN` "Learner token required"; `language_id ∉ {1,2,3}` →
400; `KNOWLEDGE_REPORT_ENABLED` false → 404 `NOT_FOUND`; `call_bundle` returns `None`
(`services/optional_rpc.py:22-43`) → 503 `SERVICE_UNAVAILABLE`. Every response sets `Cache-Control:
private, no-store`.

| Method + path | Endpoint | Tier | Query params | Success body |
|---|---|---|---|---|
| `GET /summary` | `knowledge.summary` | all | `language_id` | §6.3 |
| `GET /prestudy-suggestion` | `knowledge.prestudy_suggestion` | all | `language_id` | `{status, suggestion:{test_id, slug, title, test_type, unknown, n, unknown_share}|null}` |
| `GET /words` | `knowledge.words` | Pro | `language_id, sort, cursor, limit (1–100, default 50), states, checked_several, missed_recent, idle_days, bands, in_word_list, list, level, q` | `{status, rows, next_cursor, matching, as_of}` (`next_cursor` = base64url of the JSON array, ≤ 512 chars) |
| `GET /words/<int:vocab_id>/<int:sense_rank>` | `knowledge.word_detail` | Pro | `language_id` | `{status, …detail}`; 404 when `null` |
| `GET /lists/<list_code>/words` | `knowledge.list_words` | Pro | `language_id, level, bucket, cumulative, cursor, limit (1–100)` | `{status, rows, next_cursor, matching, attribution, allow_export, built_at, lists_unavailable}`; 404 unknown list (code not registered for the language in `LIST_CODES_BY_LANGUAGE`, or no file uploaded yet); Storage unreadable → 200 with `lists_unavailable: true`, `rows: []` |
| `GET /export` | `knowledge.export` | Pro | `language_id, format (csv|anki), scope (words|list), cursor` + the `/words` filters (scope words) or `list, level, bucket, cumulative` (scope list) | one chunk (§6.6) |

**List parameters (revised 2026-11-18, ADR-054).** `/words` (`list` + `level`), `/lists/<list_code>/words`
and `/export` resolve a list through `word_lists.default_store()` (§8) into arrays for the RPCs:
`/words` passes the level's in-dictionary `vocab_id`s as `p_filters.vocab_ids`; `/lists/…/words`
passes `p_vocab_ids` / `p_item_nos` for the chosen level (or levels ≤ it when `cumulative=1`), or
pages `not_in_dictionary` from the file without an RPC, or passes NULL arrays for `my_word_list`. The
list-words cursor is base64url of `[k1, item_no, version]` (`version` = the file version the page came
from); a cursor whose `version` is no longer the latest → 400 `LIST_UPDATED` "This list was updated.
Reload it." and the client restarts from the first page. When the store raises `WordListsUnavailable`,
`/words` with a `list` filter and `/lists/…/words` answer **200** with `lists_unavailable: true`,
`rows: []`, `next_cursor: null`, `matching: 0` (the page shows "Word lists are unavailable right
now"); `/export` behaves as §6.6. No route returns a 5xx because Storage is down.

`/prestudy-suggestion`: calls `get_recommended_tests(p_user_id, p_language_id, …)` (F20), takes the
first row with `test_type ∈ ('reading','listening')`, and returns `services/prestudy.plan_for_tests`
for that test (`unknown_share`, `unknown`, `n`); `suggestion` is non-null only when `unknown_share >
AUTO_THRESHOLD` (0.25, `services/prestudy.py:852`) and, when `services.billing.entitlements` exists,
`prestudy_per_week` has a remaining use. It is a separate request so the summary never waits for
`get_recommended_tests` (mean 214 ms, max 7.2 s — performance §1).

Validation (400 `BAD_REQUEST` with a message): unknown `sort`, `format` or `scope`; `cursor` not
decodable or wrong shape; `states` not ⊆ the four codes; `bands` not ⊆ 0–7; `idle_days` ∉ {30, 60,
90, 180}; booleans not `0|1`; `q` after strip not 1–40 chars or with control characters; `level`
without `list`; `list` not registered for the language in `LIST_CODES_BY_LANGUAGE` (on `/export`
`my_word_list` is also accepted) → "Unknown list"; `level` not one of the file's `level_codes`;
`bucket` not one of the four codes; `scope=list` without `list`. `q` is LIKE-escaped
(`\` → `\\`, `%` → `\%`, `_` → `\_`); no SQL is built by string formatting.

### 6.3 Summary response (`services/vocabulary/knowledge_report.summary()`)

```json
{"status":"success","language_id":3,"as_of":"…",
 "detail":{"level":0,"enforced":false,"preview":true},
 "estimate":{"shown":true,"kind":"range","lo":850,"hi":1400,"label":"medium","rel":0.232,
   "universe_words":3175,"definition_language_id":2,"answers":172,
   "first_answer_at":"2026-09-13","last_answer_at":"2026-11-15","reason":null,
   "answers_needed":null,"disagreement":false,"tick":1111},
 "rated_known_words":69,"tracked_words":251,
 "groups":[{"group":"most_common","universe":77,"answers":23,"share_lo":0.73,"share_hi":1.0,"shown":true,
            "tracked":"…","rated_known":"…"},
           {"group":"common","universe":820,"answers":50,"shown":false,"tracked":"…","rated_known":"…"}],
 "lists":[],"lists_unavailable":false,"watchlist":null,
 "growth":{"d30":{"practised":41,"direct_checks":164,"met_in_texts":44,"rated_known_delta":null,
                  "anchor_date":null,"first_trend_on":"2026-12-…","estimate_change":null,"pool_changed":null},
           "d90":{"practised":83,"direct_checks":318,"met_in_texts":142,"…":"…"},"idle60":95},
 "skills":{"families":[{"family":"form_recognition","n":84,"correct":79,"meanings":17,"lo":0.87,"hi":0.97,"shown":true},
                       {"family":"semantic_discrimination","n":32,"correct":17,"meanings":11,"lo":0.35,"hi":0.71,"shown":true},
                       {"family":"form_production","n":55,"correct":38,"meanings":9,"shown":false}],
           "sentence":{"weak":"semantic_discrimination","strong":"form_recognition"}},
 "missed_recent":{"meanings":10,"flagged":1},
 "next_steps":[{"key":"knowledge.next.review_practice","href":"/session?mode=practice"},
               {"key":"knowledge.next.take_test","href":"/tests"}],
 "pro_teaser":{"tracked_meanings":251,"missed_recent":10,"missing_next_level":null,"next_level":null}}
```
`estimate.kind` ∈ `range | upper_only | none`; `estimate.reason` ∈ `null | too_few_answers |
out_of_date | too_uncertain`. Numbers above are ESTIMATE for de6fd05b/ja (§2.6, §2.7, §2.11) or
MEASURED (counts, Appendix B).

`lists` (zh and ja; revised 2026-11-18): one item per list code registered for the language whose
file exists — `{list_code, version, title (= the file's "name" field), edition, is_official,
attribution, allow_export, built_at, level_codes, levels:[{level, items, in_dictionary, rated_known,
seen_not_rated, no_evidence, other_meaning_only, not_in_dictionary}]}`; `items`, `in_dictionary` and
`not_in_dictionary` come from the file, the other four from `knowledge_list_buckets` (§2.8).
`lists_unavailable = true` (and `lists = []`) when the store raises `WordListsUnavailable` or
`call_bundle('knowledge_list_buckets', …)` returns `None`; the response is still 200 and every other
field is unaffected.

### 6.4 Entitlement seam, 402 and demand logging (ADR-055)

`services/vocabulary/knowledge_report.report_detail_level(db, user_id) -> tuple[int, bool]`:
1. If `services.billing.entitlements` (TASK-980) imports: `level = int(entitlements.limit('bkt_report_detail')
   or 0)`, `enforced = Config.ENTITLEMENTS_ENFORCED`.
2. Else (stub): `level = 1 if dim_subscription_tiers.can_access_analytics for users.subscription_tier_id
   else 0` (F16), read once per request through `request_cache.memo(('kr_tier', user_id), …)`;
   **`enforced` is forced to `False`** (a `WARNING knowledge_entitlement_stub_enforce_ignored` is
   logged if the flag is on), so the stub can never deny.

Gate in each Pro route: `level == 1` → serve. `level == 0 and not enforced` → serve and log
`entitlement_shadow_deny key=bkt_report_detail route=<endpoint> user=<8 chars>`. `level == 0 and
enforced` → **402**:
```json
{"status":"error","error":"The word-by-word view is part of Pro.","error_code":"PLAN_REQUIRED",
 "upgrade":true,"entitlement":"bkt_report_detail","required":1,"current":0}
```
built by a new `utils/responses.payment_required(error_code, message, **extra)`; `web/errors.py`
`_API_ERRORS` gains `402: ('PAYMENT_REQUIRED', None)`. TASK-980's `payment_required(error, **extra)`
(`wiki/tasklist/billing.tasks.md:236`) adopts this signature. `/summary` and `/prestudy-suggestion`
never return 402; the summary always carries `detail = {level, enforced, preview = (level == 0 and not
enforced)}`.

**Demand log (P14):** Pro routes log `knowledge_pro_intent action=<a> user=<8 chars>` only for
explicit actions: `/words` with any of `q`, a filter, `sort ≠ useful`, or a `cursor` (actions
`search`, `filter`, `sort`, `load_more`); `/words/<…>` (`word_sheet`); `/lists/…/words`
(`lists_tab`); `/export` first chunk (`export_csv` / `export_anki`). The page's automatic first
`/words` call logs nothing. Weekly unique users per action are counted from the logs (TASK-1058).
`entitlement_shadow_deny` stays for billing's contract and is never read as demand.

**Enforcement is not this feature's switch:** `ENTITLEMENTS_ENFORCED` is flipped by billing TASK-997,
which must not happen for `bkt_report_detail` until the Pro launch gate (TASK-1059, §14) passes.

### 6.5 Rate limits (`web/rate_limits.py` `ENDPOINT_LIMITS`, key `user_or_ip`)

| Endpoint | Limit |
|---|---|
| `knowledge.summary` | `30 per minute; 600 per hour` |
| `knowledge.prestudy_suggestion` | `30 per minute; 300 per hour` |
| `knowledge.words` | `60 per minute; 1200 per hour` |
| `knowledge.word_detail` | `60 per minute` |
| `knowledge.list_words` | `60 per minute; 1200 per hour` |
| `knowledge.export` | `120 per hour; 600 per day` (≈ 4 full 13k-row exports an hour at 1,000 rows a chunk) |

### 6.6 Export (Pro; P3, P15)

- **Endpoint:** `GET /api/knowledge/export?language_id=&format=csv|anki&scope=words|list&cursor=…`
  plus the `/words` filters (scope `words`; `sort='id'`, a stable order) or `list, level, bucket,
  cumulative` (scope `list`, from `knowledge_report_list_words`). Each call returns **one chunk** of
  up to 1,000 rows. Headers: `Content-Disposition: attachment; filename="linguadojo-vocabulary-<lang>-<YYYY-MM-DD>.csv"`
  (or `….txt` for Anki; ASCII only), `X-Next-Cursor` (absent on the last chunk), `X-Row-Count`,
  `Cache-Control: private, no-store`. Entitlement is checked on every chunk.
- **List scope licence rule:** allowed only when the list file's `allow_export` is true (file metadata,
  §5.2; OQ3: default true for `jlpt_waller`, false for `hsk30_2025` until share-alike is accepted;
  changing it means uploading a new file version); otherwise 403 `FORBIDDEN` "This list can't be
  exported yet." List exports add columns `list_level` and `list_source` (= the file's `attribution`)
  on every row; `my_word_list` is always exportable. Every chunk of one export is read from the file
  version in its cursor (`LIST_UPDATED` as §6.2 if a newer version appears mid-export).
- **Storage unavailable** (scope `list`, or scope `words` with a `list` filter, while the store raises
  `WordListsUnavailable`): **200** with no rows, header `X-Lists-Unavailable: 1`, no `X-Next-Cursor`;
  the client checks the header first, saves nothing and shows "Word lists are unavailable right now".
- **CSV** (`format=csv`, `text/csv; charset=utf-8`): first chunk starts with the UTF-8 BOM and the
  header row; later chunks have neither; CRLF line ends. Columns (stable machine names, v1):
  `language, lemma, traditional, reading, meaning_rank, gloss, gloss_language, evidence_state,
  app_rates_known, last_direct_check_date, last_direct_check_result, last_seen_date, not_seen_days,
  test_answers_correct, test_answers_wrong, word_checks_correct, word_checks_wrong, first_seen_date,
  zipf, frequency_group, missed_recently, ladder_ring, ladder_state, flashcard_lapses, in_my_word_list`
  (+ `list_level, list_source` for list scope). Booleans `yes|no`; dates `YYYY-MM-DD` (UTC); `zipf` 2
  decimals; reading = ja `dim_vocabulary.reading` or zh tone-marked pinyin
  (`services/pinyin_format.py:126`). **No numeric p_known column** (P15); `app_rates_known` is
  explained in "How this works" as a model rating.
- **Anki** (`format=anki`, `text/plain; charset=utf-8`, no BOM): first chunk starts with the header
  lines `#separator:tab`, `#html:false`, `#tags column:4`; rows `word<TAB>reading<TAB>meaning<TAB>tags`
  where tags = `linguadojo freq_<group>` plus `<list_code>_<level>` for list scope; TAB, CR and LF
  inside fields become a space. (INFERENCE from the Anki manual's text-import file headers; verify
  with a real import in TASK-1048.)
- **Escaping** (`utils/csv_export.py`): `safe_cell(v)`: `None` → `''`; numbers via `format`; a string
  whose **first character** is `=`, `+`, `-`, `@`, TAB or CR gets a leading `'` (OWASP CSV injection;
  real en lemmas can start with `-`, so only the first character is tested and the rest kept);
  applied to both formats. CSV via `csv.writer(…, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')`.
- **Client:** `authFetch` each chunk, `await res.blob()` (not `text()`, which drops the BOM), read
  `X-Next-Cursor`, repeat; `new Blob(parts)`, `URL.createObjectURL`, a temporary `<a download>`,
  revoke after click; progress "Preparing export… {n} words"; stop with an error after 100 chunks.
  No server streaming (Railway's request limit is unknown — performance §11 Q2).
- **Size:** ~120–180 B per row → ~2 MB for a 13k-meaning learner (ESTIMATE, performance §9.4).

---

## 7. History: the nightly snapshot job (ADR-053)

- **Code:** `services/knowledge_snapshots.py: run_nightly(db=None) -> dict`; registered in
  `web/scheduler.py` `JOBS` as `Job('knowledge_snapshots_nightly',
  'services.knowledge_snapshots:run_nightly', {'hour': 4, 'minute': 25}, 'Knowledge snapshots',
  _log_skippable, _admin_client)`, after the 04:20 sweep (`web/scheduler.py:72-95`).
- **Steps:** `as_of = now()` (UTC) once per run; `snapshot_date = as_of.date()`; pairs =
  `knowledge_active_pairs(as_of − 180 d)`; per pair, sequentially: `knowledge_report_summary(p_as_of =
  as_of)` → frame from `knowledge_frame_bands` → `knowledge_estimate.estimate_range` → upsert one row
  (`on_conflict='user_id,language_id,snapshot_date'`, `source='nightly'`, `method_version` from
  `knowledge_estimate.METHOD_VERSION`), storing `cal_bands`, `frame_bands`, `cal_*_answer_at` and the
  estimate outputs. A failing pair logs `knowledge_snapshot_failed user=<8> lang=<id>` and is skipped.
  Finally `knowledge_snapshots_prune(120)`.
- **Idempotent:** the job runs in both gunicorn workers (`Procfile:1`); the second run overwrites the
  same rows. No advisory lock (performance §7.4).
- **Inactive pairs:** written daily (windows move with time); pruning bounds the cost (§5.1; OQ26).
- **No back-fill** (OQ7): growth starts at the first snapshot, so **this job ships first**.
- **Manual run:** `python -m services.knowledge_snapshots --once` writes `source='manual'`.
- **Runtime:** 5 pairs × ~25–60 ms today; ≈ 5 min at 1,000 pairs (ESTIMATE; each call under the 120 s
  job client timeout, `config.py:157`).
- **Snapshot day:** UTC date (OQ10).

---

## 8. Exam-list data (ADR-054)

- **Lists (defaults; OQ2, OQ3):** HSK 3.0 **2025-11 CLEC syllabus** from `krmanik/HSK-3.0` "New HSK
  (2025)/HSK Words" (CC BY-SA 4.0); JLPT N5–N1 from **Jonathan Waller's lists via
  `jamsinclair/open-anki-jlpt-decks`** (repo MIT; data CC BY, confirmed only second-hand); stephenmk
  (CC BY-SA 4.0) offline only, to cross-check matches. English: none.
- **Where they live (revised 2026-11-18):** one immutable JSON file per list version in the private
  Storage bucket `reference-data` at `word-lists/<list_code>/v<N>.json` (schema, sizes and database cost
  in §5.2). No list table exists. Which lists a language shows is code, not data:
  `services/vocabulary/word_lists.py` `LIST_CODES_BY_LANGUAGE = {1: ('hsk30_2025',), 3: ('jlpt_waller',)}`
  (DECISION: a list appears once its code is registered **and** a file exists; withdrawing a list is a
  code change). This replaces the old `is_active` column.
- **Sources and provenance:** pinned in `scripts/build_word_lists.py` as `SOURCES[list_code]` = URL with
  commit, sha256, licence, attribution, name, edition, `is_official`, `level_codes` and `allow_export`
  (OQ3). **No list data is committed to the repository** (ADR-054): downloaded sources and built files
  live in the git-ignored `data/word_lists/<list_code>/`. The builder refuses a source whose sha256
  differs from its pin. Untrusted downloads are parsed with `python3 -I` from a separate scripts dir.
- **Builder** `scripts/build_word_lists.py --list <list_code> --source <path> [--upload]` (owner-run;
  no database writes): reads `dim_vocabulary (id, language_id, lemma, lemma_traditional, reading,
  frequency_rank)` for the list's language **read-only** with the service key, paged 1,000 rows at a
  time (F14); resolves every headword to a `vocab_id` at build time with these rules (unchanged from
  the 2026-11-17 loader; `match_kind` in the file = the method number):
  - zh: strip homograph digits (本1 → 本); expand optional parts `没（有）` → {没有, 没}; split `|`
    variants; drop `…`; one item per distinct headword at its lowest level; match `lemma` exactly
    (method 1); else strip a final 儿 and retry (method 6; +13 HSK 2025 matches, level-lists §3.4).
  - ja: T1 kanji = lemma (1); T2 kana-only = lemma (2); T3a kana-only = `reading` (3); T3b reading
    equal + ≥ 1 shared kanji (4); T3c kanji word whose kana form is a lemma (5); reading-only
    homophones are **not** matched.
  - Validation before anything is written: `word_lists.validate_word_list(doc, list_code)` (the
    reader's own validator, so builder and reader share one schema check), every non-null `vocab_id`
    exists among the rows read for `language_id`, file ≤ 5,242,880 B, `built_from` filled; the
    per-level match table is printed and written to `data/word_lists/<list_code>/match_report.json`.
  - **Default = dry run:** writes `data/word_lists/<list_code>/v<N>.json`, where `N` = the highest
    version in Storage + 1 (a read-only `list`; 1 when the folder is empty). **`--upload`** then `put`s
    exactly that content to `word-lists/<list_code>/v<N>.json` (never overwrites); `AlreadyExists` → exit
    non-zero without retrying (a concurrent upload; rerun). If `entries` and every metadata field except
    `built_at` equal the latest version's, nothing is uploaded and the script prints "unchanged".
  - **Rebuild** whenever the dictionary gains lemmas of the list's language — after each sense-seeding
    batch for zh or ja, and after OQ31's JLPT seeding. This replaces the old `--re-resolve` UPDATE
    path; earlier versions stay in Storage untouched.
- **Reader** `services/vocabulary/word_lists.py` (TASK-1049):
  - `default_store()` → one per-process `WordListStore(SupabaseStorageBackend(Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY, bucket='reference-data', http_timeout_s=2.0))`
    (`services/exercise_content/backends.py:357`). Tests pass `InMemoryBackend` (`backends.py:100`).
  - `WordListStore.latest(list_code) -> WordList | None`: `None` = no file uploaded (E4); raises
    `WordListsUnavailable` when Storage fails and nothing is cached (E4c). `list_code` must be
    registered in `LIST_CODES_BY_LANGUAGE` and match `^[a-z0-9_]{3,40}$` before any path is built.
  - Cache: parsed lists keyed by `(list_code, version)`, plus per code the time of the last version
    check. A request re-lists `word-lists/<list_code>/` only when that check is ≥ `RECHECK_S = 21600`
    (6 h) old, and `get`s a file only when the highest listed version differs from the cached one
    (normally a newer upload; a lower one after the owner deletes a bad version). After a failed check it serves the
    cached version (log `word_lists_recheck_failed`) and does not retry for `RETRY_AFTER_FAILURE_S =
    300`; with nothing cached, requests in that window raise `WordListsUnavailable` at once, so an
    outage costs at most one 2 s timeout per list per process every 5 minutes. A deploy or restart reads
    the latest version immediately.
  - A file that fails `validate_word_list` (wrong `schema`, `list_code` ≠ folder, `language_id` not the
    registered one, `level_idx` outside `1…len(level_codes)`, an entry not of length 5, `match_kind` set
    without `vocab_id` or missing with one) is never served: log `word_list_invalid list=<code> v=<N>`,
    keep the previous cached version, else raise `WordListsUnavailable`.
  - `WordList` (frozen): the metadata fields of §5.2, `version`, `entries`, and per level the derived
    `items`, `not_in_dictionary`, and in-dictionary `vocab_ids` / `item_nos` (file order);
    `bucket_arrays() -> (vocab_ids, level_idx)` for `knowledge_list_buckets`;
    `level_arrays(level, cumulative) -> (vocab_ids, item_nos)` for `knowledge_report_list_words` and
    the `/words` filter. Memory ≈ 2.1–2.3 MB per list per process (ESTIMATE, §5.2).
- **Sense mapping:** an item counts through its lemma's rank-1 meaning (OQ12).
- **Missing words are not created** by the builder (~20 MB of senses, ~140 MB with ladder content —
  level-lists §6.3).
- **Expected coverage (P10):** HSK 2025 L1–L5 87.6–92.1%, L6 75.4%, L7-9 37.9%. **Every JLPT level is
  majority "not yet in LinguaDojo"** with the stephenmk counts (N5 48.7% matched … N1 20.5%; jamsinclair
  N5 46.4% … N1 19.4%); an N5 beginner sees about half of N5 as not in LinguaDojo (歩く, 忙しい, 明日).
  Default (OQ20): show the JLPT card with that share stated first plus the import action; **do not use
  JLPT coverage in Pro marketing**. Seeding the ~722 missing N5–N4 lemmas (≈ 3.4 MB of senses, ESTIMATE)
  is OQ31.
- **UI wording:** "HSK 3.0 (2025 syllabus)"; "JLPT N3 — community list (unofficial; JLPT publishes no
  official vocabulary list)"; attribution from the file's `attribution` under the card; "List matched to
  the dictionary on {date}" from the file's `built_at` (UTC date); trademarks used descriptively.

---

## 9. Caching and performance

- **Server cache:** none for per-user data (no cross-request cache exists — performance §8; a
  per-worker cache would be stale right after practice). `request_cache.memo` within one GET for the
  entitlement level, the definition language (`gloss_lookup.get_user_definition_language_id`) and the
  snapshot read. `knowledge_frame_bands()` in a process-local TTL cache (3,600 s; global data; the pool
  is DERIVED and refreshed by hand). Exam-list files in the per-process `WordListStore` cache (§8:
  keyed by list code and version, version re-check at most every 6 h, 300 s back-off after a Storage
  failure); they are global, immutable data, so this is not per-user caching.
- **Client cache:** none for data. `localStorage` (try/catch) only for `kn.sort`, `kn.growthWindow`,
  `kn.wordTab`, `kn.listSel`.
- **Budgets** (warm, healthy host; jitter makes 10× tails normal — F13):

| Call | Today (575 rows) | At 26k rows | Basis |
|---|---|---|---|
| `knowledge_report_summary` | ≤ 100 ms | ≤ 600 ms | MEASURED 21–36 ms core aggregate today and 55.5 ms at 26k rows without decay (F13); + meaning grouping, logs, calibration, families, lists (ESTIMATE +100–400 ms) |
| `knowledge_frame_bands` | ≤ 300 ms (cached) | same | ESTIMATE: one pass over 27,356 pool rows (10.1 MB) with PK lookups |
| `knowledge_report_words` (50 rows) | ≤ 80 ms | ≤ 600 ms | MEASURED 39.7 ms today and 240 ms at 26k *with* decay (performance §5); v1 sorts need no decay |
| `knowledge_list_buckets` (≤ 10,896 ids) | ≤ 50 ms | ≤ 300 ms | ESTIMATE: one pass over the learner's UVK rows (as the summary's `r`) and a hash join to the unnested array; not measured — TASK-1049 records it |
| word-list file, cold (per list, per process) | `list` + one `get` of ~0.3 MB | same | not measured (TASK-1053 records the first cold read); each request is bounded by `http_timeout_s = 2.0`; warm requests make no Storage call |
| export chunk (1,000) | ≤ 400 ms | ≤ 1.5 s | MEASURED 331 ms cold for 575 rows by `sense_id` |
| `/summary` end-to-end p95 | ≤ 1.5 s | ≤ 3 s | + 2–3 PostgREST round trips (50–100 ms each, ADR-042), +1 for `knowledge_list_buckets` (zh, ja); a cold word-list read can add up to the Storage timeouts once per list per process |

  Hard limits: PostgREST client timeout 10 s (`config.py:156`); service_role has no statement timeout.
  TASK-1054 measures these and records them in `wiki/evaluations/knowledge-report-perf-<date>.md`.
  **Fallback if summary p50 > 500 ms for a real learner with ≥ 10k rows:** serve the snapshot row as
  "as of last night" plus a live delta (performance §8.3) — a new task, not v1.
- **Indexes:** none added (§5.3).

---

## 10. Component Specification (UI)

### `templates/knowledge.html`
- Extends `base.html`; `{% set task_mode = true %}`, `{% set task_back = 'history' %}`; blocks
  `task_title` ("My vocabulary", `data-i18n="knowledge.title"`), `task_subtitle` (language name, by
  JS), `task_glyph`; `{% block extra_css %}` loads `static/css/pages/knowledge.css`.
- Stage `.ld-screen.kn-page > .ld-stage`: `#knLoading`, `#knError`, `#knUnavailable`, `#knEmpty` (E0),
  then `<section class="ld-card kn-card">` cards (each `d-none` until rendered): `knEstimate`,
  `knGroups`, `knLists`, `knWordList`, `knGrowth`, `knSkills`, `knNext`, `knProTeaser`, `knWords`
  (Pro), and a bottom-sheet container `#knSheet` for "How this works", filters and the word sheet
  (pattern `wiki/pages/app-shell.md:67-68`).
- English defaults inside `data-i18n` elements; no inline styles; no hex colours.

### `static/js/pages/knowledge.js` (classic IIFE; pattern `static/js/dual_translation_profile.js:14-103`)
- **Props:** none (reads `localStorage.selectedLanguageId`).
- **State:** `{languageId, summary, detail, prestudy, words:{rows, cursor, sort, filters, q, matching,
  loading}, wordTab:'all'|'missed'|'lists', listSel:{code, level, bucket, cumulative, rows, cursor},
  growthWindow:30|90, exporting, adding}`.
- **Effects:** on `DOMContentLoaded`: start `authFetch('/api/knowledge/summary?language_id=…')`,
  `authFetch('/api/knowledge/prestudy-suggestion?…')` and `LinguaI18n.init()` in parallel (ADR-042);
  render when summary and i18n settle; insert the prestudy step when it arrives (rule 2 position). If
  `detail.level === 1 || detail.preview`, fetch the first words page (default params; not logged as
  intent). 401 is handled by `authFetch`; the page handles 402 (Pro card in place of the section), 404
  and 503 (E8), other errors (E9).
- **Queries/Mutations:** `GET /api/knowledge/summary`, `/prestudy-suggestion`, `/words`,
  `/words/<vocab_id>/<sense_rank>`, `/lists/<code>/words`, `/export` chunks; `POST /api/word-list/submit`
  (§3.4).
- **Rendering rules:** database text via `textContent` or `LinguaUtils.escapeHtml`; numbers via
  `Intl.NumberFormat(LinguaI18n.locale)`; ranges with an en dash; bars are `.ld-bar` spans (no chart
  library); search debounced 300 ms; "Load more" keeps scroll position. No emoji, no celebratory copy
  (do not copy the DT profile's `🎉`, `dual_translation_profile.js:120`).
- **Paywall:** if `window.LinguaPaywall` exists (TASK-995), the Pro card button calls
  `LinguaPaywall.open({reason: 'bkt_report_detail'})`; otherwise no button.

### `static/css/pages/knowledge.css`
Scoped under `.kn-page`; theme tokens only; ≥ 44 px targets; rows on phones, `.table` at ≥ 768 px;
reuses `.ld-card`, `.ld-note`, `.ld-rowlist`, `.ld-trow`, `.ld-stats`, `.ld-seg`, `.ld-chips`, `.ld-bar`
(`static/css/styles.css:3620-4146`).

### Entry points
- `templates/profile.html` Me hub: new `.ld-set` row first, rendered only when
  `config.KNOWLEDGE_REPORT_ENABLED` (Flask's Jinja `config` global): title `common.nav.knowledge`, sub
  `me.knowledge_sub`.
- `templates/base.html:64-70`: add `'knowledge_page'` to the `'me'` tab tuple.
- `web/pages.py`: `('/knowledge', 'knowledge_page', 'knowledge.html')`.
- Calibration result (`static/js/pages/calibration.js:403-420`, `templates/calibration.html`): when the
  flag is on, after `renderResults` the page fetches `/api/knowledge/summary` and shows the same range
  block with a link "See My vocabulary" (P16, TASK-1042). The existing frequency-level figure keeps its
  label and gains a sub-line naming what it measures (OQ33).

### i18n (`static/i18n/{en,es,ja,zh}.json`; flat keys; all four files in the same task)

Names (draft; native review required — OQ1):

| key | en | es | ja | zh |
|---|---|---|---|---|
| `common.nav.knowledge` | My vocabulary | Mi vocabulario | わたしの語彙 | 我的词汇 |
| `me.knowledge_sub` | What the app knows about your words | Lo que la app sabe de tus palabras | アプリが把握しているあなたの語彙 | 应用对你词汇掌握情况的了解 |
| `knowledge.title` | My vocabulary | Mi vocabulario | わたしの語彙 | 我的词汇 |
| `knowledge.prefix.answers` | From your answers | De tus respuestas | あなたの解答から | 来自你的作答 |
| `knowledge.prefix.estimated` | Estimated | Estimado | 推定 | 估计 |
| `knowledge.prefix.model` | Model | Modelo | モデル | 模型 |
| `knowledge.confidence.low` / `.medium` / `.good` | Rough / Medium / Good | Aproximada / Media / Buena | 目安 / 中程度 / 高い | 粗略 / 中等 / 较高 |

Remaining keys (en given; es/ja/zh written in the task that adds them and reviewed under OQ1):
`knowledge.estimate.headline` "In the vocabulary check you recognised about {lo}–{hi} of the {n}
{language} words it draws from" · `.upper_only` "Fewer than {hi} of the {n} {language} words the check
draws from" · `.basis` "From {answers} check answers, {first} – {last}" · `.need_answers` "To
estimate your vocabulary we need about 10 check answers at each of 7 frequency levels: {have} of 70 so
far." · `.out_of_date` · `.too_uncertain` · `.disagreement` · `knowledge.rated_known.line` "Rated known
after a direct check: 1 word|{count} words" · `.why` "This counts only words you have answered directly
at least once and that the app now rates as known. Reading tests can change these ratings." ·
`knowledge.tracked.line` · `knowledge.how.*` (title, pool_only, recognition_only, idk_rule,
ratings_not_probabilities, not_logged) · `knowledge.group.most_common|common|mid|rare|none`,
`.not_enough` · `knowledge.lists.*` (title, unofficial, not_readiness, not_in_ld_first, cumulative,
none_in_dictionary, bucket.rated_known|seen_not_rated|no_evidence|not_in_dictionary, export_blocked,
matched_on "List matched to the dictionary on {date}", unavailable "Word lists are unavailable right
now", updated "This list was updated. Reload it.") ·
`knowledge.wordlist.title` · `knowledge.growth.*` (title, practised, direct_checks, met_in_texts,
idle60, rated_known_delta, no_direct_checks, since, first_trend_on, no_clear_change, higher_than,
lower_than, pool_changed, window_30, window_90) · `knowledge.skills.*` (title, subtitle,
family.form_recognition|meaning_recall|form_production|semantic_discrimination|collocation|fluency,
tries, not_enough, sentence, footnote) · `knowledge.next.check|prestudy|session|review_practice|refresh_check|take_test` ·
`knowledge.pro.*` (title, teaser, see, available_with_pro, history_kept, preview_note) ·
`knowledge.words.*` (search_placeholder, filter, sort.*, matching, load_more, state.*, lead_last_check,
lead_checks, lead_tests_only, tests, checks, not_seen_days, ladder_intro, ladder_ring, lapses,
tab_all, tab_missed, tab_lists, missed_flag, latest_miss) · `knowledge.sheet.*` (events,
other_updates, linked_by_today, flashcard, ladder, app_rating_known, app_rating_not_known,
not_probability) · `knowledge.add.*` (button, helper, done, link) · `knowledge.export.*` (menu, csv,
anki, preparing, failed) · `knowledge.state.*` (empty_title, empty_body, stale, few_words,
unavailable, error, filter_empty, clear_filters, add_word_list). Plurals use the existing `"1 word|{count}
words"` form (`static/js/i18n-manager.js:123-161`). No key in the `report.*` namespace (F15).

---

## 11. Key Architectural Decisions

1. **Decision:** the headline is a range from the calibration sample over the check's own word pool
   (frame), one definition language, rank-1 anchors, latest answer per lemma, unclamped guess-corrected
   shares with Jeffreys-variance and finite-population correction ([[decisions/ADR-051-vocabulary-size-from-calibration-frame]]).
   - **Rationale:** the check is a random within-band sample of its pool (F7); BKT rows are selected,
     uncalibrated and correlated (F2, F5); extrapolating to the whole zh dictionary rests on words the
     check never samples (F8).
   - **Alternatives rejected:** Σp, threshold counts, band extrapolation of rows, hybrid prior,
     whole-dictionary denominator, the "naive" skip model (below chance — S4), Wald variance (zero
     width at the edges — S2).
2. **Decision:** Pro rows lead with measured evidence; four evidence states; the five model labels and
   any decay value are not shown in v1 ([[decisions/ADR-052-report-leads-with-measured-evidence]]).
   - **Rationale:** F2 (low labels wrong more often than right), F3/F4 (decay flags 今 and 言う).
   - **Alternatives rejected:** last-measured label with date (draft); effective p; "due for a check".
3. **Decision:** words (rank-1) for headlines and lists; meanings for Pro rows; rows never counted.
4. **Decision:** history = daily per-(user, language) snapshots that store the estimator's inputs
   ([[decisions/ADR-053-daily-knowledge-snapshots]]).
   - **Rationale:** replay impossible (F6); per-sense daily ~37 MB/year unaffordable; storing inputs
     lets "then" be recomputed on today's frame and tested for disjointness.
5. **Decision:** exam lists are immutable, versioned JSON files in the private Storage bucket
   `reference-data`, matched to the dictionary at build time and passed to SQL as arrays; measured
   buckets only; missing words not created ([[decisions/ADR-054-exam-word-lists-in-storage]], revised
   2026-11-18).
   - **Rationale:** ~1.2 KB of database instead of ~2 MB on a database at its Free cap (F17), so the
     list upload and the Pro gate do not wait for OQ13; the Storage client and the immutable-file
     pattern already exist (ADR-049).
   - **Alternatives rejected:** two reference tables (size gate); a file in the app repository (list
     updates need deploys; CC BY-SA data in the repo — the fallback if Storage proves unreliable);
     resolving lemmas per request (dictionary lookups on every page).
6. **Decision:** entitlement seam with a stub that can never enforce; one 402 envelope; enforcement
   and marketing wait for the Pro launch gate ([[decisions/ADR-055-knowledge-report-entitlement-seam-and-launch-gate]]).
7. **Decision:** study actions reuse existing paths — word-list import, Practice, prestudy — rather
   than a new targeted-drill engine in v1 ([[decisions/ADR-056-report-actions-reuse-existing-study-paths]]).
8. **Decision:** one SQL pass per page view returning `jsonb`; statistics in pure Python; no server cache.
   - **Alternatives rejected:** Python over PostgREST tables (1000-row cap, 4–6 round trips — performance §9.3).
9. **Decision:** exports assembled in the browser from short server-generated chunks, with a CSV and
   an Anki text format and the same filters as the screen.
   - **Alternatives rejected:** one big RPC (timeouts under jitter), server streaming (unknown proxy
     limit), JS-side CSV (second escaping copy), whole-set-only export (P3).
10. **Decision:** task-mode page reached from Me, named "My vocabulary"; `knowledge` in every code name (F15).

## 12. Security Considerations

- **AuthN/Z:** JWT on every route; user id only from `g.current_user_id`; non-UUID identities (batch
  token) → 403; no "view another learner" endpoint in v1. Pages have no server-side auth by design
  (`web/pages.py:38-42`); all data comes through the API.
- **SQL:** every function is `SECURITY INVOKER`, `service_role` only, `search_path` pinned; no dynamic
  SQL; filters passed as typed `jsonb` and read with explicit casts; `q` LIKE-escaped with `ESCAPE '\'`.
  No function is `SECURITY DEFINER`; if one ever becomes one it must use the NULL-safe check
  `IF p_user_id IS NULL OR (auth.uid() IS DISTINCT FROM p_user_id AND coalesce(auth.role(),'') <>
  'service_role') THEN RAISE …` (`migrations/sec_submission_rpcs_auth_gate.sql:88-97`). New tables have
  RLS on and no client grants; `tests/sql/check_function_acls.sql` must return empty after each migration.
- **Input limits:** `limit` ≤ 100 (UI) / 1,000 (export, server-fixed); cursor ≤ 512 chars and strict
  shape; `q` ≤ 40 chars; path ints validated by Flask converters; `list_code` matched against
  `^[a-z0-9_]{3,40}$` **and** against `LIST_CODES_BY_LANGUAGE` before any Storage path is built (no
  request value ever reaches a Storage path unchecked).
- **Output:** `Cache-Control: private, no-store`; CSV/Anki injection neutralised (§6.6); filename
  ASCII-only; no user id or email in exports; logs use the first 8 UUID characters only.
- **Write path reuse:** "Add these words" calls the existing `POST /api/word-list/submit`, which
  enforces its own JWT, 50-word cap and per-user daily cap (F18); the report adds no write endpoint.
- **Licences:** attribution rendered from the list file's `attribution` in the UI and in list exports;
  list-subset export controlled by the file's `allow_export` (OQ3); both are file metadata (§5.2), so a
  change is a new, auditable file version.
- **Storage (ADR-054):** bucket `reference-data` is private (`public = false`) with no
  `storage.objects` policy, so only the service role reads or writes it; no public or signed URL is
  ever handed to a browser — Flask reads the files and returns only the fields above. Uploads happen
  only from the owner-run builder with the service key, and `put` never overwrites. The reader treats
  file content as data: it validates the schema (§8) before use, passes ids to SQL only as typed
  `integer[]` / `smallint[]` RPC arguments (never string-built SQL), and the page renders `form` /
  `reading` / `attribution` with `textContent`; exported list rows go through `safe_cell` like every
  other cell.
- **Privacy of others:** no comparisons with other learners, no leaderboards (also a re-identification
  risk with 18 users — UX research §6).

## 13. Testing Strategy

**pytest**
- `tests/test_knowledge_estimate.py` (pure): de6fd05b/ja fixture (§2.6 table) → T 1,110.7 ± 0.5, SD
  131.3 ± 0.5, interval 853.3–1,368.1 (± 1), rel' 0.232, label `medium`, display 850–1,400 of 3,175;
  every row of the §2.6 table (a band with `n_b = 9` → E1 with `have`; window fails but all-time
  passes → E1c; `lo = 0` → upper-only; the zh beginner who never skips at 20/band → "fewer than
  510", never `too_uncertain`; rule 7; rule 8 with `answers_needed_per_band = 32` at rel' 0.8, n̄ 20);
  an all-skip band and an all-correct band give non-zero SD; K never clamped; `hi` uses `max(T, 0)`;
  rounding (9, 37, 853.3, 1,368.1, 3,175, 12,790); groups (most common 73–100, common hidden, mid
  17–47, rare 8–35); clustered Wilson (recognition [0.87, 0.97], discrimination [0.35, 0.71]); the
  sentence rule; anchor selection (none, < 14 days, 14–29 days, exact D-30, method_version mismatch);
  estimate comparison (overlapping → none; disjoint and eligible → "no clear change" when |Δ| <
  1.96·SD_diff); pool-change notice at > 5%; next level (P13).
- **Slow test** `tests/test_knowledge_estimate_coverage.py` (marked `slow`): the §2.6 simulation grid
  at n = 10, 20, 30 asserts coverage ≥ 0.93 and zero zero-width outputs.
- `tests/test_knowledge_routes.py` (pattern `tests/test_word_list_import_routes.py:290-318`): 401; 400
  without / with bad `language_id`; 403 for `service-account`; 404 flag off; 503 when `call_bundle`
  returns `None`; envelope shape; `p_user_id` always the caller's (spy on RPC params); shadow → 200 +
  `entitlement_shadow_deny`; enforced → exact 402 payload; stub ignores `ENTITLEMENTS_ENFORCED=true`;
  every 400 case of §6.2; `q` escaping; `Cache-Control`; `knowledge_pro_intent` logged for search /
  filter / sort / cursor / sheet / lists / export and **not** for the default first page. **Storage
  down** (the store raises `WordListsUnavailable`): `/summary` → 200 with `lists = []`,
  `lists_unavailable = true` and every other field equal to the Storage-up response; `/lists/…/words`
  and `/words?list=…` → 200 with `lists_unavailable = true`; `/export?scope=list` → 200,
  `X-Lists-Unavailable: 1`, no rows; no 5xx anywhere. A list-words cursor from an older file version →
  400 `LIST_UPDATED`; an unregistered list code → 400 (`/words`, `/export`) or 404 (`/lists/…/words`).
- `tests/test_knowledge_report_service.py` (pattern `tests/test_session_merges.py:19-66`): summary
  assembly from a canned RPC payload; next-step rule order; prestudy suggestion threshold; Pro teaser
  clauses omitted when zero; one entitlement read per request; frame cache TTL.
- `tests/test_csv_export.py`: `safe_cell` for `=`, `+`, `-`, `@`, TAB, CR, normal text, numbers, `None`;
  BOM only on the first CSV chunk; CRLF; CJK round trip through `csv.reader`; Anki header lines and
  TAB/newline replacement; list exports carry `list_source` (= the file's `attribution`); a file with
  `allow_export: false` → 403.
- `tests/test_word_lists.py` (new; `InMemoryBackend`, `services/exercise_content/backends.py:100`, seeded
  with small valid files): latest version chosen as a number (`v2`, `v9`, `v10` → v10; `v01.json` and
  `notes.txt` ignored); a second `latest()` within 6 h makes no Storage call (`calls_for('list')`), after
  6 h (injected clock) exactly one `list` and a `get` only if a higher version exists;
  `fail_next('list', ContentStorageError(…))` with nothing cached → `WordListsUnavailable`, and no
  further Storage call for 300 s; the same failure with a cached version → the cached version is served
  and `word_lists_recheck_failed` logged; empty folder → `None`; each invalid-file case of §8 →
  `word_list_invalid` and the previous version kept; an unregistered or malformed list code never
  reaches the backend; `bucket_arrays()` excludes null ids and keeps duplicates; `level_arrays(level,
  cumulative)` returns file order; per-level `items` / `not_in_dictionary` counts.
- `tests/test_build_word_lists.py` (new): zh/ja normalisation and every `match_kind` on small fixtures;
  the output passes `validate_word_list`; a sha256 mismatch is refused; a `vocab_id` absent from the
  dictionary read fails validation; dry run writes `data/word_lists/<code>/v<N>.json` and makes no
  `put`; `--upload` (with `InMemoryBackend`) puts once to `word-lists/<code>/v<N>.json` with N = latest
  + 1; `AlreadyExists` → non-zero exit, no retry; an unchanged rebuild (only `built_at` differs) puts
  nothing.
- `tests/test_knowledge_snapshots.py`: one upsert per pair with `cal_bands`/`frame_bands` lengths 21/7;
  idempotent second run; failing pair skipped; prune called with 120; `snapshot_date` = UTC date.
- `tests/test_knowledge_report_migration.py` (pattern `tests/test_dt_repair_migration.py:1-30`): every
  function has REVOKE/GRANT and pinned search_path; read RPCs are STABLE with no INSERT/UPDATE/DELETE;
  tables enable RLS; no reference to `bkt_effective_p_known` or `bkt_apply_decay`;
  `reference_data_bucket.sql` inserts exactly one bucket (`'reference-data'`, `public` false,
  `file_size_limit` 5242880, `allowed_mime_types` `{application/json}`, `ON CONFLICT DO NOTHING`) and
  creates no policy; its rollback refuses while objects exist; `tests/test_migration_security_lint.py`
  passes.
- `tests/test_i18n_locale_parity.py` (new): identical key sets and matching `{param}` placeholders.
- `tests/test_platform_app.py`: `'knowledge_page': '/knowledge'`; `tests/test_platform_rate_limits.py`
  sees the six endpoints.

**SQL (read-only on production, after each migration):** `tests/sql/check_function_acls.sql` empty;
`SELECT knowledge_frame_bands()->'3:2'` = `[577,425,621,655,537,283,77]` (until the pool is refreshed);
`SELECT knowledge_report_summary('<de6fd05b uuid>', 3::smallint)` returns `rated_known_words = 69`,
`states = 10/69/30/142`, calibration bands as §2.6. One rule in two functions: `knowledge_list_buckets`
called with de6fd05b/ja's 251 tracked `vocab_id`s (all at `level_idx` 1) returns `rated_known = 69`, the
summary's `rated_known_words`. After TASK-1034: `SELECT id, public, file_size_limit, allowed_mime_types
FROM storage.buckets WHERE id = 'reference-data'` returns one row.

**Vitest** (`tests/unit/knowledge-page.test.js`, pattern `tests/unit/dual-translation-page.test.js:1-70`):
E0, E1, E1b, E1c, upper-only, full summary, preview note, 402 → Pro card, 404/503 → unavailable;
`lists_unavailable` → "Word lists are unavailable right now" in the list card and Lists tab with every
other card rendered; "List matched to the dictionary on {date}"; never "0 words"; en dash and no bare midpoint; load more appends with the cursor; export concatenates blobs
and stops on a missing `X-Next-Cursor`; "Add these words" posts ≤ 50 lemmas and shows the 429 message;
database text escaped.

**Playwright:** `tests/e2e/knowledge-report.spec.js` — read-only smoke at 390 px and 1280 px (loads, no
horizontal scroll, targets ≥ 44 px, Pro section or teaser present; it never clicks "Add these words").
Visual harness: `tests/e2e/redesign/fixtures/knowledge.json` (E0, E1, full Pro) and a `walk.py` entry.

## 14. Rollout and the Pro launch gate

1. Owner applies `knowledge_report_foundation.sql` (snapshot table, 3 small functions) and
   `reference_data_bucket.sql` (the private `reference-data` bucket; no list table — ADR-054).
2. Owner applies `knowledge_report_summary.sql`; deploy the snapshot job (flag-independent) → history
   accrues. **This is the first deliverable**: a 30-day trend needs 30 days of rows.
3. Deploy summary + page with `KNOWLEDGE_REPORT_ENABLED=false`; staff check with the flag on locally
   against production data (read-only).
4. Flag on (TASK-1058): everyone sees the summary; non-Pro learners see the Pro view as a shadow preview.
5. Pro pieces (words, sheet, Missed recently, lists, add-to-word-list, filtered export) ship behind the
   same flag as they land.
6. **Pro launch gate (TASK-1059; P1).** `bkt_report_detail` is not enforced, and the report is not named
   as a Pro benefit on the pricing page, until all of: (1) the HSK 2025 list file is uploaded to
   Storage (TASK-1053), (2) "Add these words to my word list" ships (TASK-1051), (3) filtered and list
   export ships (TASK-1048), (4) evidence-first rows ship (TASK-1046). Billing TASK-997 references this
   gate. (1) waits only for OQ2 and OQ3: the list is a file in Storage (~1.2 KB of database for both
   lists), so since the 2026-11-18 revision the gate **does not depend on the database size question
   (OQ13)**.
7. TASK-1056 must be done before the range is used in marketing copy.

Rollback: flag off (UI disappears, API 404); `*_rollback.sql` drops the new functions and the snapshot
table (snapshots are lost); `reference_data_bucket_rollback.sql` removes the bucket only once its files
are deleted (§5.2). Withdrawing one list version: the owner deletes that file; processes keep serving
their cached copy until their next 6-hourly check, then fall back to the highest remaining version.

## 15. Open questions

Each row gives the default this spec uses, so nothing is blocked except tasks marked `[?]`.

| # | Question | Why it matters | Default | Affects |
|---|---|---|---|---|
| OQ1 | UI name? | "Report" already means "Report an issue" (F15). | en "My vocabulary", es "Mi vocabulario", ja 「わたしの語彙」, zh 「我的词汇」; native review before launch. | TASK-1040 |
| OQ2 | HSK list: 2025-11 CLEC syllabus or GF0025-2021? | 41.5% of ~9,700 shared words changed level. | 2025 syllabus, labelled "HSK 3.0 (2025 syllabus)". | TASK-1052/1053 [?] |
| OQ3 | Licences and list exports: is CC BY-SA 4.0 (krmanik HSK) acceptable, and may list subsets be exported? | Share-alike may attach to an exported adaptation; Waller CC BY was confirmed only second-hand. | Upload HSK (krmanik) and JLPT (jamsinclair + Waller CC BY) files with attribution; the files' `allow_export` true for JLPT, false for HSK until signed off (a change = a new file version). | TASK-1048, 1052, 1053 |
| OQ4 | Before enforcement, do non-Pro learners see the Pro view (shadow preview)? | Demo-ability; TASK-980's contract is "log and allow". | Yes, with the note; demand measured by `knowledge_pro_intent`. | TASK-1045, 1046 |
| OQ5 | Approve a Calibration change to measure what "I don't know" hides: forced-choice probe on 1 in 8 items, or two skip buttons ("Never seen it" / "Seen it, not sure")? | Skips counted as unknown make the figure a lower-side estimate if skips hide partial knowledge (S4). | Skip = not known; no "naive" model; probe proposed in TASK-1061. | TASK-1056, 1061 [?] |
| OQ6 | Is 110fb390 a test/automated account? | Its evidence looks automated; validation would then rest on one human learner. | Yes: excluded from validation; its report is still shown to it. | TASK-1056 [?] |
| OQ7 | Accept that growth starts at the first nightly snapshot (no back-fill)? | Replay is impossible. | Yes; snapshots ship first. | TASK-1037 |
| OQ8 | Estimate thresholds: floor 10/band (Rough), 20 (Medium), 30 (Good); rel' gates 0.15 / 0.30 / 0.50; 180-day window? | Too strict hides the number from trialists; too loose shows noise. Simulation: coverage ≥ 0.937 at 10/band. | As stated. | TASK-1035 |
| OQ9 | Change the selector to draw a lemma uniformly within band and serve its rank-1 sense (S9)? | en polysemy: 38% of en items test a rank > 1 meaning; v1 scores only rank-1 items, so en learners need more answers. | No change in v1. | TASK-1062 [?] |
| OQ10 | Snapshot day: UTC or the learner's plan-local day? | 04:25 UTC is afternoon in Australia. | UTC. | TASK-1037 |
| OQ11 | Confirm the per-outcome family mapping of intro formats (§2.11)? | Only used to label the kind of exercise on a missed word; Skills uses non-intro attempts. | As §2.11 (read_typed → recognition; ex_* via `exercise_id`). | TASK-1036 |
| OQ12 | Is `sense_rank = 1` reliably the most common meaning? | Decides "rated known" for words and list coverage; ranks are LLM-ordered. | Yes for v1 (98.0% zh, 99.3% ja lemmas have one meaning). | TASK-1036 |
| OQ13 | Is the Free cap 500 MiB or 500,000,000 B; must database-growing content work wait for the ADR-049 drop? | DB is 513,526,931 B. Since 2026-11-18 the exam lists do not depend on it (Storage files, ~1.2 KB of database — ADR-054); it still gates the zh pool refresh (OQ29), seeding missing JLPT lemmas (OQ31) and database growth from "Add these words" (OQ30). | Foundation (~0.2 MB) and the list upload any time the DB is writable; the **database size gate** — `pg_database_size` ≤ 490,000,000 B or a confirmed MiB cap — before OQ29/OQ30/OQ31 work and the evidence log (OQ16). | TASK-1060, TASK-1063, TASK-1065 [?] |
| OQ14 | Approve decay clean-ups (IMMUTABLE → STABLE; drop the broken 2-arg overload)? | Mislabelled volatility can freeze `now()`; the 2-arg call always fails. Not needed by the report. | Deferred. | TASK-1066 [?] |
| OQ15 | Build targeted practice of an explicit word set? | Most actionable later step; v1 uses word-list import instead (ADR-056). | Deferred. | TASK-1064 [?] |
| OQ16 | Add evidence-kind counters or an event log to the writer functions? | Needed to label "inferred" precisely and to count words newly rated known. | Deferred. | TASK-1065 [?] |
| OQ17 | Fix the decay model, and show a model-based review flag (only for bands 1–5 or last direct answer wrong) until then? | Would allow "probably known today"; changes Practice for everyone. | No model flag in v1. | TASK-1067 [?] |
| OQ18 | Let learners mark "I know this" / "I don't know this"? | Writes BKT state; `user_marked_unknown` has no writer. | Not in v1. | TASK-1068 [?] |
| OQ19 | A compact Today card? | Visibility vs a gamified feel. | Not in v1. | TASK-1069 [?] |
| OQ20 | JLPT at launch, given every level is majority "not in LinguaDojo"? | Free users see the card too. | Show all levels with the not-in-LinguaDojo share first and the import action; never in Pro marketing. | TASK-1050 |
| OQ21 | "Known" = recognition only? | Only recognition has enough data. | Yes; production appears only in Skills. | ADR-051 |
| OQ22 | Which tiers see list coverage counts? | The owner listed list coverage under Pro. | Counts for all tiers; word lists, actions and export are Pro. | TASK-1050 |
| OQ23 | Must a raw-answer export exist on every tier (data portability)? | Possibly a legal duty (GDPR Art. 20); not verified, not legal advice. | Not in v1; owner to check. | (future) |
| OQ24 | First official sitting of the new HSK (13 Dec 2026 vs July 2026)? | Copy about the "current" syllabus. | Name the edition only. | TASK-1050 |
| OQ25 | Task-mode page or a tab page under Me? | Consistency vs "home" feel. | Task mode. | TASK-1040 |
| OQ26 | Snapshot rows every day for inactive pairs? | ~110 KB per pair per year before pruning. | Yes, with pruning. | TASK-1037 |
| OQ27 | Is "rated known after a direct check" strict enough? | 47 of 72 draft-rule lemmas rested on one correct check (statistician R8). | `checks_correct > checks_wrong` and `p_last ≥ 0.75`; TASK-1056(b) measures next-check accuracy on ≥ 100 distinct senses (months away). | TASK-1036, 1056 |
| OQ28 | Accept the Pro launch gate (§14 step 6) and keep the report out of Pro marketing until it passes? | Without lists, actions and export, Pro is a read-only table of ~251 words (billing Q1). | Yes. | TASK-1059, billing TASK-997 |
| OQ29 | Refresh the zh calibration anchor pool (stale since the 2026-10/11 seeding) before or after the zh launch? | The zh frame is 3,623 of 12,790 words; a refresh adds ≈ 5–7 MB (ESTIMATE). | Launch zh with the frame denominator; refresh after the size gate. | TASK-1063 [?] |
| OQ30 | May "Add these words" grow the database (exercise generation for senses without exercises; new senses at 8 credits each for `not_in_dictionary`)? | Size cap and credit pricing. | v1: in-dictionary buckets only; credits path deferred. | TASK-1051, 1060 [?] |
| OQ31 | Seed the ~722 missing JLPT N5–N4 lemmas (≈ 3.4 MB senses) after the size gate? | Half of N5 is not in LinguaDojo. | Not in this feature; a content task later. | (content) |
| OQ32 | An "Upcoming tests" Pro card (known share of each recommended test's key words)? | LinguaDojo's unique angle (UX research #2). | Deferred. | TASK-1070 [?] |
| OQ33 | Align Calibration's own ability fit (skip scored as a wrong answer) with the report's skip rule, or label each output? | Two results for one concept on the result screen (P16). | Label the frequency-level figure; show the report's range beside it; fit unchanged. | TASK-1042 |
| OQ34 | Show a list-level estimated percentage (§2.8a) after validation? | List words are not exchangeable with frame words (S8). | No. | TASK-1071 [?] |

## 16. Related Pages
- [[features/knowledge-report]] · [[features/vocabulary-knowledge.tech]] · [[features/calibration.tech]] · [[features/test-prestudy.tech]] · [[features/practice-extra-rounds.tech]]
- [[business/pricing-plan.tech]] · [[tasklist/billing.tasks]] (TASK-980, TASK-993 superseded by [[tasklist/knowledge-report.tasks]], TASK-995, TASK-997)
- [[tasklist/word-list-import.plan]] · [[database/schema.tech]] · [[api/rpcs.tech]]
- [[decisions/ADR-051-vocabulary-size-from-calibration-frame]] · [[decisions/ADR-052-report-leads-with-measured-evidence]] · [[decisions/ADR-053-daily-knowledge-snapshots]] · [[decisions/ADR-054-exam-word-lists-in-storage]] · [[decisions/ADR-055-knowledge-report-entitlement-seam-and-launch-gate]] · [[decisions/ADR-056-report-actions-reuse-existing-study-paths]]
- [[decisions/ADR-042-request-scoped-caching-and-static-asset-caching]] · [[decisions/ADR-048-mobile-app-shell]] · [[decisions/ADR-049-exercise-content-in-storage]]

---

## Appendix A — Review outcomes

Two independent reviews (a statistician, S1–S13; a product reviewer who is also a serious learner,
P1–P16) challenged the design draft on 2026-11-17. Dispositions:

| Id | Severity | Decision | Where it landed |
|---|---|---|---|
| S1 | blocker | accepted | §2.1 frame, §2.6, ADR-051; de6fd05b/ja now "850–1,400 of 3,175" (rank-1 and latest-answer rules move S1's 860–1,400 slightly) |
| S2 | major | accepted (+ `hi` uses `max(T, 0)`) | §2.6 estimator; slow coverage test §13 |
| S3 | major | partly accepted | §2.6 rows 3–8: S3's rules with P8's 10/band floor; rule 7 added so beginners never loop |
| S4 | major | accepted | no naive model anywhere; copy §2.6; TASK-1061, TASK-1056(a) |
| S5 | major | accepted | §2.4 rename and rule (69, not 72); "Model" prefix; TASK-1056(b) clustered, ≥ 100 senses |
| S6 | major | partly accepted | §2.10; vocabulary-check answers stay in the estimate card, not in "words practised" |
| S7 | major | accepted | §2.11 (with P12: non-intro only; fixture 79/84 and 17/32); ex_* via `exercise_id` for miss labels |
| S8 | major | accepted | §2.8 measured buckets only; §2.8a formula; TASK-1071 |
| S9 | major | accepted | rank-1 anchors and rank-1 frame §2.6; one definition language; selector change TASK-1062 |
| S10 | minor | accepted | latest answer per lemma; distinct-lemma n_b; finite-population factor |
| S11 | minor | partly accepted | "Model" prefix and unnumbered "Review in Practice" adopted; the "due" fact itself dropped (P5) |
| S12 | minor | accepted | §2.7 four merged groups with the 0.15 half-width rule |
| S13 | minor | accepted | §2.12 flag inside "Missed recently" |
| P1 | blocker | accepted | §14 step 6; TASK-1059 |
| P2 | major | accepted (credits path deferred) | §3.4; TASK-1051; TASK-1060 [?]; OQ30 |
| P3 | major | accepted | §6.6 filtered and list export, Anki format; TASK-1048 |
| P4 | major | partly accepted | §2.4: four evidence states (a fourth, "checked, not yet rated known", makes the set exhaustive); five labels hidden until TASK-1056(c); sheet shows a binary app rating |
| P5 | major | accepted | §2.5: no "due" in v1; "Not seen for {n} days" |
| P6 | major | partly accepted | §2.13; the deep link is XS (TASK-1043) because Practice already offers the review extra round when the queue is empty (F19) |
| P7 | major | accepted | §2.13 rule 2, `/prestudy-suggestion`; quota condition waits for TASK-980 (F16); TASK-1070 [?] |
| P8 | major | accepted | §2.6 floor 10/20/30; E1c; TASK-1056(d) |
| P9 | major | partly accepted | (a) §5.1 stores inputs, §2.10 recompute and notice; (b) superseded by S1 (the frame is always the denominator); OQ29 |
| P10 | major | accepted | §2.8, §8, ADR-054, OQ20, OQ31; prose positioning line |
| P11 | major | accepted | §2.12; teaser uses the missed-recently count |
| P12 | minor | accepted | §2.11 |
| P13 | minor | accepted | §2.8 next level; `kn.listSel` |
| P14 | minor | accepted | §6.4 `knowledge_pro_intent` |
| P15 | minor | accepted | §6.6 no numeric p column |
| P16 | minor | partly accepted | TASK-1042 shows the same range on the calibration result; Calibration's fit unchanged (OQ33) |

## Appendix B — Evidence SQL run in the synthesis stage (read-only, 2026-11-17)

**K1 — frames (rank-1 lemmas per band) for every (L, D):**
```sql
WITH pool AS (SELECT p.word_language_id l, p.definition_language_id d, p.zipf_band band, p.sense_id, p.vocab_id, s.sense_rank
  FROM calibration_anchor_pool p JOIN dim_word_senses s ON s.id = p.sense_id
  WHERE p.has_embedding AND NOT EXISTS (SELECT 1 FROM calibration_anchor_blocklist bl WHERE bl.sense_id = p.sense_id))
SELECT l, d, count(*) rows_, count(DISTINCT vocab_id) lemmas, count(DISTINCT vocab_id) FILTER (WHERE sense_rank = 1) rank1_lemmas, …by band…
FROM pool GROUP BY l, d;
```
→ `1/1 3961 rows, 3644 lemmas, rank-1 314/615/749/690/665/438/172`; `1/2 and 1/3: 3623, 303/617/742/691/664/435/171`;
`2/2: 6080 rows, 3755 lemmas, 412/517/737/794/722/425/147`; `3/1 and 3/2: 3190 rows, 3175 lemmas, 577/425/621/655/537/283/77`;
`3/3: 3171, 3160, 573/422/617/653/536/280/77`.

**K2 — de6fd05b/ja definition-mode answers in 180 days, all vs latest per lemma with rank-1 anchors:**
```sql
WITH r AS (SELECT cs.definition_language_id d, cr.anchor_vocab_id v, s.sense_rank, cr.zipf_band band, cr.answered_at, cr.chosen_sense_id, cr.is_correct
  FROM calibration_responses cr JOIN calibration_sessions cs ON cs.id = cr.session_id JOIN dim_word_senses s ON s.id = cr.anchor_sense_id
  WHERE left(cs.user_id::text,8)='de6fd05b' AND cs.word_language_id=3 AND cs.mode='definition'
    AND cr.answered_at IS NOT NULL AND cr.answered_at > now() - interval '180 days'),
latest AS (SELECT DISTINCT ON (d, v) * FROM r WHERE sense_rank = 1 ORDER BY d, v, answered_at DESC)
SELECT d, band, count(*) n, count(*) FILTER (WHERE chosen_sense_id IS NULL) s, count(*) FILTER (WHERE is_correct) c, min(answered_at)::date, max(answered_at)::date
FROM latest GROUP BY d, band;   -- and the same over r
```
→ all answers (d = 2): 27/17/7, 24/16/6, 26/14/9, 24/12/9, 25/9/13, 26/8/16, 26/0/24 (rank > 1: 1 in band 1, 1 in band 2);
latest rank-1: 26/16/7, 23/16/5, 26/14/9, 24/12/9, 25/9/13, 25/8/15, 23/0/21; first 2026-09-13, last 2026-11-15 (bands 2–7 last 2026-10-17).

**K3 — de6fd05b/ja UVK aggregates:**
```sql
WITH k AS (SELECT k.*, s.vocab_id, s.sense_rank, calibration_zipf_band(dv.frequency_rank) band FROM user_vocabulary_knowledge k
  JOIN dim_word_senses s ON s.id = k.sense_id JOIN dim_vocabulary dv ON dv.id = s.vocab_id
  WHERE left(k.user_id::text,8)='de6fd05b' AND k.language_id=3)
SELECT count(*), count(DISTINCT (vocab_id, sense_rank)), count(DISTINCT vocab_id),
  count(DISTINCT vocab_id) FILTER (WHERE sense_rank=1 AND word_test_correct>0 AND p_known>=0.75),
  count(DISTINCT vocab_id) FILTER (WHERE sense_rank=1 AND word_test_correct>word_test_wrong AND p_known>=0.75 AND status<>'user_marked_unknown'),
  count(DISTINCT vocab_id) FILTER (WHERE sense_rank=1 AND word_test_correct>word_test_wrong AND p_known>=0.75 AND word_test_correct>=2),
  count(*) FILTER (WHERE word_test_correct+word_test_wrong>0), count(*) FILTER (WHERE last_evidence_at <= now()-interval '60 days'),
  count(*) FILTER (WHERE last_evidence_at > now()-interval '30 days' AND word_test_correct+word_test_wrong=0), … '90 days' …
FROM k;
```
→ `rows 251 | meanings 251 | words 251 | draft rule 72 | rated known 69 | checked several 22 | checked 109 | idle60 95 | met in texts 44 (30 d), 142 (90 d)`.

**K4 — de6fd05b/ja logged outcomes, missed recently, evidence states:** outcomes `o` = first-try
`exercise_attempts` ∪ `word_quiz_results` for ja senses, per meaning with `row_number() OVER (PARTITION BY vocab_id,
sense_rank ORDER BY at DESC)`; states joined to K3's rows.
→ `outcomes 164 (30 d), 318 (90 d) | practised 41 (30 d), 83 (90 d) | meanings with outcomes 83 | missed recently 10 | flag (≥4 outcomes, ≥3 wrong of last 5, ≥2 days) 1 | states missed_last 10, rated_known 69, checked 30, not_checked 142`.

**K5 — de6fd05b/ja non-intro first attempts by family (90 days), per meaning `correct/n`:**
```sql
… FROM exercise_attempts ea JOIN dim_word_senses s ON s.id = ea.sense_id LEFT JOIN dim_exercise_types det ON det.type_code = ea.exercise_type
WHERE left(ea.user_id::text,8)='de6fd05b' AND ea.is_first_attempt AND s.word_language_id = 3
  AND coalesce(ea.source,'practice') <> 'intro' AND ea.created_at > now() - interval '90 days' …
```
→ form_recognition 79/84 on 17 meanings (`12/14 10/10 9/10 8/8 7/7 6/6 5/5 5/5 4/4 3/4 3/3 2/2 1/2 1/1 1/1 1/1 1/1`);
semantic_discrimination 17/32 on 11 (`7/9 4/9 2/3 1/2 0/2 0/2 1/1 1/1 1/1 0/1 0/1`); form_production 38/55 on 9; meaning_recall 14/14 on 5; all source `practice`.

**K6 — embeddings, gloss rows and database size:** `SELECT word_language_id, definition_language_id, count(*), count(embedding), … FROM dim_word_senses WHERE definition_level='standard' GROUP BY 1,2`
→ zh/zh 13,137 senses all with embedding (avg 1,032 B); zh/en and zh/ja 3,914 each (gloss rows, no embedding); ja/ja 3,491 with embedding; en/en 6,602; `pg_database_size` = 513,526,931.

**K7 — pool and distractor-cache size:** `calibration_anchor_pool` 27,356 rows, 10,100,736 B (≈ 369 B/row);
`calibration_distractor_cache` 33,599 rows, 7,217,152 B (≈ 215 B/row). ESTIMATE for OQ29: ~9,160 more zh/zh pool rows ≈ 3.4 MB + 2–4 MB of cache rows.

**K8 — snapshot row width:** `SELECT pg_column_size(ROW(gen_random_uuid(), 3::smallint, current_date, 1::smallint, 251, 251, 69, 109, 10, 95, 41, 164, 2::smallint, ARRAY[…21 values…]::smallint[], ARRAY[577,…,77]::int[], 172, now(), now(), 1::smallint, 850, 1400, 2::smallint, 'nightly'::text, now()))` → **256 B** (smallint[21] 66 B, int[7] 52 B).

**K9 — `get_recommended_tests` signature:** `pg_get_function_result` → `TABLE(test_id uuid, slug text, test_type text, title text, difficulty_level integer, elo_rating integer, elo_diff integer, tier text)`; args `p_user_id uuid, p_language_id smallint, p_topic_recency_days smallint`.

Scripts (ESTIMATE work): `kr/synth_scripts/final_estimator_v2.py` (session scratchpad; fixture, groups,
clustered intervals, coverage grid). Research and review files referenced by name (data-audit,
level-lists, performance, UX, code-map, statistician review, product review) are in the same session
scratchpad and are summarised here; they are not durable.
