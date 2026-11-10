---
title: New-Word Drill — Technical Specification
type: feature-tech
status: in-progress
prose_page: ./new-word-drill.md
last_updated: 2026-11-10
dependencies:
  - "table: user_word_ladder (new intro_* columns)"
  - "table: exercise_attempts (source column from migrations/prestudy_workflow.sql; new source value 'intro')"
  - "table: user_study_plans.new_words_per_day (default 5 → 10)"
  - "RPC: get_practice_session, ladder_new_word_state, ladder_record_attempt"
  - "service: services/practice_session_service.py (admit_daily_new_words, _subscribe)"
  - "service: services/prestudy.py, routes/tests.py prestudy evidence route"
  - "client: static/js/prestudy/prestudy.js (drill engine to extract), static/js/session/controller.js, players/"
  - "service: VocabularyKnowledgeService.update_from_word_tests_batch"
breaking_change_risk: medium
---

# New-Word Drill — Technical Specification

## Implementation notes (as built, 2026-11-10)

Built and live (migration applied 2026-11-10; walked through in the browser with the test
account). Where the build differs from the plan above, **this section wins**:

1. **State:** a new `word_state = 'intro'` instead of new RPCs. Every existing ladder function
   filters `word_state` by an explicit list, so intro rows are invisible to `get_practice_session`,
   `get_ladder_session` and `build_daily_session` with no change to them. Stage logic lives in
   Python (`services/intro_drill.py`); the only SQL change besides columns/CHECKs is
   `ladder_new_word_state` (intro rows are servable; a word counts as started at its first intro
   session entry). Migration: `migrations/new_word_drill.sql`.
2. **Spacing rule:** the required gap is `min(4, active_words − 1)` *at the time each item is
   served* (it shrinks as the block's other words finish) and is sent with every attempt; the
   server clamps it to `0..min(4, n_words − 1)`. A fixed per-block gap made the last 2–3 words of a
   block unable to count anything (found by the shared fixture).
3. **Client:** engine + player in one module, `static/js/session/players/intro_drill.js`, run by
   the practice player (`players/practice.js`) before the regular items whenever the session
   payload has `intro_drill`. Reading graders are reused from `prestudy.js`
   (`window.LinguaPrestudy`), now also loaded on the session page (its `init` returns early when
   the prestudy DOM is absent). Ladder exercises render through `ExRenderers`; types that need
   server grading or preparation (`cloze_typed` exercises, `jumbled_sentence`) are not used.
4. **Posting:** one `POST /api/practice/intro/complete` per finished word (results list of 1–40),
   so a learner who stops mid-block keeps the words already finished. Failed posts retry once and
   are kept in `sessionStorage` for the next session.
5. **Where words are served:** stage 2–4 words (and stage-1 restarts/overloads) in every mode;
   brand-new stage-1 words only in acquisition/auto, within `effective quota − started today`,
   prestudy-queued first. When intro reviews are due and the day has no open maintenance chunk,
   `GET /api/study-session` adds an `intro_reviews` maintenance chunk (Practice mode shows it as
   the day's exercises). Intro words are filtered out of regular practice items (BKT/FSRS reviews
   could otherwise pick them).
6. **Extra rounds:** "new words" in an extra round are served as an intro block (session 1).
7. **Admission:** all three insert paths (`_insert_ladder_rows`, `LadderService.init_ladder`,
   prestudy) create intro rows; the 3-exercise supply gate is bypassed while the drill is on
   (starved words are still sent to generation).
8. **Ring-2 restart:** hooked in `LadderService.record_attempt`. Note: only Vocab Dojo records
   ladder attempts; Practice-engine attempts update BKT/FSRS but never call
   `ladder_record_attempt` (pre-existing behaviour, not changed here).
9. **Quota default:** new plans get `max(10, daily_minutes // 6)` new words a day
   (`routes/study_plan.py`); the DB default is 10.
10. **Flag:** `NEW_WORD_DRILL_ENABLED` (env, default true). Off: new words go to ring 1 as before;
    existing intro rows keep being served.
11. **Done 2026-11-10 (second pass):** the review governor counts due drill reviews weighted by
    expected items (`migrations/new_word_drill_governor.sql`); the forecast adds 10 drill review
    items per new word (`study_plan_service.reviews_per_new_word_30d`); measurement script
    `scripts/eval_new_word_drill.py` with a baseline at
    [[evaluations/new-word-drill-baseline-2026-11-10]].
12. **Atomic word commit:** `intro_commit_word` (`migrations/intro_commit_word.sql`) locks the
    row, checks it is still at the posted stage, inserts the attempt rows and updates the ladder
    row in one transaction; evidence, ledger and generation follow in Python.
13. **Spacers:** with fewer than 5 drill words, up to 3 of the session's ordinary items go
    between two showings of the same word when fewer than 2 items would separate them
    (`SPACER_MIN_GAP`); they are recorded as normal practice attempts and not served again.
14. **Shared counting:** `countWord` in `intro_drill.js` mirrors the server `recount` (pinned by
    the shared fixture); the prestudy page loads it and uses it to decide which primed words met
    session 1. Prestudy keeps its own staged UI (readiness check, boosters).
15. **Ladder handoff:** the ring-2 restart now fires from Practice attempts — see
    [[decisions/ADR-041-practice-moves-the-ladder]].

## Architecture Overview

A new per-word state machine, **intro stages 1–4**, sits in front of the ladder and replaces
ring 1 for newly admitted words. Stage state lives on `user_word_ladder`. The practice session
serves due intro words as one `kind: 'intro_drill'` block. The client runs the drill with a
criterion engine extracted from the prestudy prime and posts one result per word per session.
The server advances the stage, writes one knowledge-evidence point per word, and on completing
stage 4 hands the word to the ladder at ring 2.

```
admission (admit_daily_new_words / prestudy)        ── sets intro_stage=1 (or 2), intro_due_date
        │
get_practice_session ── excludes intro_stage IS NOT NULL from ladder pool
        │
PracticeSessionService._inject_intro_block ── intro_due_words() → services/intro_drill.build_block()
        │                                       (content: lemma, reading, gloss, example sentence,
        │                                        distractor pool, ladder exercises by group)
client players/intro_drill.js + static/js/drill/engine.js   (criterion counting, spacing, caps)
        │  POST /api/practice/intro/complete
services/intro_drill.complete() ── exercise_attempts rows (source='intro')
                                 ── update_from_word_tests_batch (1 row per word)
                                 ── RPC intro_complete_session() → next stage / graduate to R2
```

## Constants (`services/intro_drill.py`, mirrored in `static/js/drill/engine.js`, test-pinned)

| Name | Value | Meaning |
|---|---|---|
| `INTRO_TARGETS` | `{1: 5, 2: 3, 3: 2, 4: 2}` | counted correct answers to pass a stage |
| `INTRO_COLD_MISS_BUMP` | `1` | added to target for stages 2–4 when the opening cold recall is wrong or "I don't know" |
| `INTRO_ITEM_CAPS` | `{1: 12, 2: 8, 3: 6, 4: 6}` | max items served per word per session; reaching it without the target = stage not passed |
| `INTRO_GAP_DAYS` | `{2: 1, 3: 1, 4: 2}` | days after the *completion* date of the previous stage that the next stage is due (day 0 / 1 / 2 / 4) |
| `INTRO_MIN_GAP_ITEMS` | `4` | intervening items required before a correct answer counts; effective gap = `min(4, block_items_available)` |
| `INTRO_REQUEUE` | wrong: 3–5 places; idk: 2–4 places | as prestudy |
| `INTRO_GRADUATE_FORM_RECOGNITION` | `0.55` | `family_confidence.form_recognition := GREATEST(current, 0.55)` on graduation |
| `INTRO_DEMOTE_TO_STAGE` | `1` | a ring-2 word demoted by `ladder_record_attempt` makes a full intro restart (decided 2026-11-09) |
| `INTRO_STAGE_ITEMS_EST` | `{1: 7, 2: 4, 3: 3, 4: 3}` | expected items per word per stage, for estimates and the overload notice |

## Formats per stage and language

Format keys reuse prestudy stage keys where they exist. A **counted** correct answer needs a
format different from the word's previous counted answer.

| Stage | ja / zh order | en order (no reading) | Fallbacks when an item cannot be built |
|---|---|---|---|
| 1 | `read_typed`, `def_mc`, `read_typed2`, `rev_mc`, `cloze_mc` | `def_mc`, `rev_mc`, `cloze_mc`, `recall_typed`, `ex_use` | missing reading → drop reading stages, add `recall_typed`; missing sentence → `ex_use`, else drop |
| 2 | **cold** `read_typed`, then `ex_use`, `ex_judge`, `def_mc` | **cold** `recall_typed`, then `ex_use`, `ex_judge`, `rev_mc` | no exercises → `rev_mc`, `cloze_mc` |
| 3 | **cold** `read_typed`, then the first group/type in `ex_use`∪`ex_judge` not in `intro_history.formats` | **cold** `recall_typed`, same | `cloze_mc` |
| 4 | **cold** `read_typed`, then a productive item: `cloze_typed` or `ex_use` with typed answer (typed cloze, translation) | **cold** `recall_typed`, same | `recall_typed` (ja/zh: type word from gloss) |

New formats (not in prestudy today):
- `recall_typed`: prompt = learner-language gloss; answer = lemma (ja: kana or kanji form accepted; zh: hanzi or pinyin with tones; en: case-insensitive, trimmed, one-edit typo tolerance for words ≥ 6 letters reported as "almost").
- `cloze_typed`: example sentence with the word blanked; answer typed, graded as `recall_typed`.

The format sequence is a *preference order*. After a miss the engine re-queues the same item;
after a correct-but-not-counted answer (gap too short) it re-queues the next format.

## Database Impact

### Migration `migrations/new_word_drill.sql` (LIVE-DB, approval-gated)

```sql
ALTER TABLE public.user_word_ladder
  ADD COLUMN IF NOT EXISTS intro_stage     smallint NULL CHECK (intro_stage BETWEEN 1 AND 4),
  ADD COLUMN IF NOT EXISTS intro_due_date  date     NULL,
  ADD COLUMN IF NOT EXISTS intro_history   jsonb    NOT NULL DEFAULT '[]'::jsonb;
CREATE INDEX IF NOT EXISTS idx_user_word_ladder_intro_due
  ON public.user_word_ladder (user_id, intro_due_date) WHERE intro_stage IS NOT NULL;
-- exercise_attempts.source: add 'intro' to exercise_attempts_source_check
-- user_study_plans.new_words_per_day: ALTER ... SET DEFAULT 10;
--   UPDATE ... SET new_words_per_day = 10 WHERE new_words_per_day = 5  (old default; other values kept)
```

- `intro_stage` = the **next** stage to run; NULL = not in intro (legacy row or graduated).
- `intro_history` entries: `{stage, date, target, counted, items, cold_correct, formats:[...], passed}`;
  capped at the last 8 entries.
- While `intro_stage IS NOT NULL`: `word_state = 'new'`, `current_ring = 1`, `review_due_at = NULL`.
- No backfill: legacy ring-1 rows keep `intro_stage = NULL` and the old ring-1 path.

### `exercise_attempts`

Every intro item answer is one row: `source = 'intro'`, `sense_id` set, `exercise_id` NULL for
built formats (`exercise_type = 'intro_' || format`) or the real exercise id for `ex_*` items,
`is_first_attempt = (first time this item was shown in this session)`, `time_taken_ms`. This
makes `ladder_new_word_state.started_at` see intro starts with no change, and keeps the minutes
ledger and `review_item_seconds` honest. These rows do **not** call `ladder_record_attempt` or
per-attempt exercise BKT.

### Changed SQL

- `get_practice_session`: ladder candidate pool adds `AND uwl.intro_stage IS NULL`.
- `ladder_new_word_state`: `servable` becomes `(intro_stage IS NOT NULL AND has_intro_content) OR (>= 3 active exercises)`, where `has_intro_content` = sense has a gloss in the learner's definition language and an example sentence (and a reading for ja/zh). This relaxes the supply gate for admission (see Decision 4).
- `ladder_record_attempt` demotion branch: when demoting from ring 2, set `intro_stage := 1`, `intro_due_date := p_today + 1`, `word_state := 'new'`, `review_due_at := NULL`, reset `family_success_dates.form_recognition := []` and `gates_passed.gate_a := false`, instead of `current_ring := 1`. `intro_history` is kept (append `{event:'restart', date}`).

### New RPCs (SECURITY DEFINER, `service_role` EXECUTE only — ADR-034)

### `intro_due_words(p_user_id uuid, p_language_id smallint, p_today date, p_limit int DEFAULT 60): jsonb`
- **Purpose:** the intro words due today, ordered stage DESC (finish older words first), then `intro_due_date`, then admission time.
- **Returns:** `[{sense_id, stage, target_base, due_date, history}]`.
- **Errors:** none; empty array when nothing is due.

### `intro_complete_session(p_user_id uuid, p_language_id smallint, p_today date, p_results jsonb): jsonb`
- **Purpose:** apply one finished block atomically.
- **Arguments:** `p_results` = `[{sense_id, stage, target, counted, items, cold_correct, formats, passed}]`; rows whose `stage` ≠ the row's current `intro_stage` are ignored (idempotent replays).
- **Effects per word:** append to `intro_history`; if `passed` and stage < 4 → `intro_stage += 1`, `intro_due_date := p_today + INTRO_GAP_DAYS[next]`; if `passed` and stage = 4 → **graduate**: `intro_stage := NULL`, `current_ring := 2`, `word_state := 'active'`, `family_confidence.form_recognition := GREATEST(…, 0.55)`, `family_success_dates.form_recognition :=` the last two intro session dates, `review_due_at := now()`; if not `passed` → stage unchanged, `intro_due_date := p_today + 1`.
- **Returns:** `{advanced:[…], graduated:[…], repeated:[…]}`.

## API / RPC Surface

### Session payload: `kind: 'intro_drill'` item
Injected by `PracticeSessionService._inject_intro_block(payload, user_id, language_id)` in
`get_session` (modes `acquisition`, `maintenance`, `auto`; not `tail`), placed first in the queue.
Practice mode (2026-11-06 split): stage 2–4 words are review chunks; stage 1 words are held back
and offered with the "Learn new words" prompt (`static/js/session/tail.js` `splitPracticeQueue`).

```json
{ "kind": "intro_drill", "id": "intro-<date>", "words": [
  { "sense_id": 123, "stage": 2, "target": 3, "cap": 8,
    "lemma": "…", "reading": {"shown": "…", "numbered": "…"} | null, "gloss": "…",
    "sentence": "… ___ …" | null, "formats": ["read_typed", "ex_use", "ex_judge", "def_mc"],
    "exercises": {"use": [<trimmed exercise>], "judge": [<trimmed exercise>]} } ],
  "distractors": { "<sense_id>": {"defs": […], "lemmas": […]} },
  "spacers": [<up to 3 ordinary practice items, only when words < 3>],
  "est_minutes": 6 }
```
Content is built by `services/intro_drill.build_block(db, user_id, language_id, due)` reusing
`prestudy._load_senses`, `_load_exercises`, `trim_exercise`, `group_exercises`. Distractors:
other due/known senses of the same language and part of speech (prestudy's rule without a passage).

### `POST /api/practice/intro/complete`
- **Body:** `{block_id, results:[{sense_id, stage, target, counted, items, cold_correct, formats, passed}], attempts:[{sense_id, format, exercise_id?, correct, idk, first, ms, given}], active_ms, client_event_id}`
- **Validation:** sense_ids must be intro rows of this user with `intro_stage = stage`; `attempts` ≤ 400; `passed` is **recomputed server-side** from `attempts` with the same counting rules (client value ignored).
- **Side effects:** `exercise_attempts` rows (source `intro`); one `update_from_word_tests_batch` row per word with `side_effects=False` (stage 1: majority rule of `prestudy.evidence_rows`; stages 2–4: `cold_correct`); `intro_complete_session`; minutes to `study_time_ledger` (kind `practice`); generation request (reason `intro`) for words with < 3 exercises after stage 1.
- **Returns:** RPC result. **Auth:** `@supabase_jwt_required`.

### Prestudy integration (`routes/tests.py` evidence route, `services/prestudy.py`)
After a `prime` is recorded: for each drilled sense, `met = all five stage-1 formats answered correct at least once with prestudy's interleaving` (the client already records per-stage results). Admit via `PracticeSessionService.admit_prestudy_words(user_id, language_id, [(sid, met)])`:
- within today's remaining quota (`new_word_state.effective − (unstarted + started_today)`): insert/upsert row with `intro_stage = 2 if met else 1`, `intro_due_date = tomorrow if met else today`, and an `intro_history` entry `{stage:1, source:'prestudy', …}` when met;
- over quota: the evidence response carries `overflow: {fits, over, sense_ids:[…], extra_minutes_per_day}` where `extra_minutes_per_day = over × Σ INTRO_STAGE_ITEMS_EST / 4 × review_item_seconds / 60` (rounded up). Nothing is admitted for the over-quota words until the learner chooses:
  - **Queue for later** (default, also applied if the learner closes the page): nominate at the front of Queue A1 with reason `prestudy`; when admitted on a later day, `intro_stage = 1`.
  - **Add them all now**: `POST /api/tests/<id>/prestudy/admit-overflow` `{session_id, sense_ids}` → admitted exactly as within-quota words (stage 2 if met, else 1). Validated: sense_ids ⊆ the session's overflow list, session ≤ 6 h old, each id at most once. Logged in the prime session's metrics as `overloaded: n`.
- Existing ladder rows (any state) are left alone. `prestudy_followups` rows are not created for senses admitted here (their next-day review *is* intro stage 2).

## Component Specification (UI)

### `static/js/drill/engine.js` (new, extracted from `prestudy.js`)
- **Exports:** `createDrill({words, distractors, spacers, mode:'intro'|'prime'|'followup', rng})` → `{next(), answer(itemId, {correct, idk, given, ms}), state(), results()}`.
- **State per word:** `{stage, target, cap, served, counted, lastCountedFormat, lastShownAt, coldDone, coldCorrect, formatsUsed[]}`; global `pos` (item counter).
- **Counting rule:** `correct && !idk && pos − lastShownAt − 1 ≥ effGap && format ≠ lastCountedFormat` → `counted++`.
- **Scheduling:** round-robin across words with unmet targets in shuffled order; never the same word twice in a row; insert a spacer when the only remaining word would violate the gap; stop a word at `counted ≥ target` (passed) or `served ≥ cap` (not passed).
- **Cold item:** stages 2–4 always serve the stage's cold format first for each word; on wrong/idk, `target += 1`.
- Prestudy keeps its own stage list and readiness check but calls the same engine for typing grading and requeue, so both paths share one implementation (graders `gradeJa`, `gradeZh`, `gradeReading` move into the module).

### `static/js/session/players/intro_drill.js` (new)
- **Props (ctx):** `item` (the `intro_drill` payload), `languageId`, `onComplete`.
- **Renders:** typed and MC items with prestudy's markup and CSS classes; ladder `ex_*` items via `static/js/exercise-renderers.js`; spacer items via the practice player.
- **Header:** "New words — N to go", per-word pips (counted / target).
- **On finish:** POST `/api/practice/intro/complete`, then `onComplete()`. On POST failure: retry once, then keep results in `sessionStorage` under `intro:<block_id>` and retry on next session load (idempotent server side).
- Registered in `player_registry.js` under `intro_drill`.
- **i18n:** keys `intro.title`, `intro.progress`, `intro.cold_hint`, `intro.recall_typed_prompt`, `intro.cloze_typed_prompt`, `intro.almost`, `intro.done` × en/zh/ja/es.

## Key Architectural Decisions

1. **Criterion counting, not fixed question counts** — see [[decisions/ADR-040-criterion-based-new-word-drill]].
2. **Intro replaces ring 1 for new admissions only.** Rationale: ring 1's formats (phonetic recognition, definition match) are subsumed by the intro formats; keeping both would double-drill. Alternatives rejected: migrating legacy R1 rows (they already have attempt history the intro cannot represent).
3. **One knowledge-evidence point per word per session.** Rationale: 5–17 same-session answers would push BKT `p_known` to "known" in one sitting; the cold recall is the honest retention signal. Alternative rejected: per-item BKT with a lowered learn rate (harder to reason about, still inflates).
4. **Supply gate relaxed for intro.** Rationale: stage 1 needs only gloss + sentence (+ reading); ladder exercises are needed from stage 2 and generation is requested at admission. Under 7% of test-linked senses had 3+ exercises on 2026-10-29, so the old gate would starve the drill. Risk: a word reaches ring 2 with no exercises and stalls — already true today for ring-1 words; logged as a metric.
5. **Server recomputes `passed`.** The client is untrusted (ADR-034); attempts carry enough to recount.

## Security Considerations

- All writes go through the Flask route with the service client; new RPCs are not EXECUTE-able by `authenticated` (ADR-034).
- The route accepts only the caller's own intro rows at their current stage; replays are no-ops.
- `attempts` length-capped; `given` truncated to 500 chars as in prestudy.

## Testing Strategy

- **Engine (vitest):** counting rule (gap, distinct format, idk), cold bump, caps, never-twice-in-a-row, spacer insertion with 1–2 words, en format list without readings, deterministic with a seeded rng.
- **Python:** `intro_drill.build_block` fallbacks (no reading, no sentence, no exercises); server recount of `passed` matches engine fixtures (shared JSON fixtures in `tests/fixtures/intro_drill/`); prestudy admission within/over quota.
- **SQL (`tests/sql/new_word_drill_test.sql`):** stage advance and due dates 0/1/2/4 from completion date; repeat on fail; graduation fields; idempotent replay; ladder pool excludes intro rows; demotion R2 → stage 3; `ladder_new_word_state` counts an intro-only start.
- **Browser (Playwright, phone size):** one block of 3 words end to end in practice mode; summary card returns.

## Measurement

Compare words admitted after rollout with words admitted in the 60 days before:
- first-try pass rate of Gate A and of the stress test;
- ring-2 demotion rate within 14 days of reaching ring 2;
- cold-recall correctness at stages 2/3/4 (a direct 1-, 1- and 2-day retention curve);
- minutes per word to graduation from intro, and words graduated per week.
Script: `scripts/eval_new_word_drill.py` → `wiki/evaluations/new-word-drill-<date>.md`. Two learners: treat as a sanity check, not a significance test.
