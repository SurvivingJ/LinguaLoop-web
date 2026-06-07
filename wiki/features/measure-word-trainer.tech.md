---
title: Measure Word Trainer — Technical Specification
type: feature-tech
status: complete
prose_page: ./measure-word-trainer.md
last_updated: 2026-06-07
dependencies:
  - "dim_classifiers, dim_classifier_distractor_groups, dim_classifier_noun_pairs"
  - "dim_test_types row classifier_drill (id=14)"
  - "tests sentinel row slug='__classifier_drill_zh'"
  - "test_attempts / user_skill_ratings / test_skill_ratings"
  - "get_classifier_drill_session() RPC"
  - "process_classifier_drill_submission() RPC"
  - "services/classifier_curation/ (offline LLM authoring pipeline, qwen via OpenRouter)"
breaking_change_risk: low
---

# Measure Word Trainer — Technical Specification

## Architecture Overview

```
Dictionary build (rebuildable; NOT incremental — wipes + re-inserts):
  1. migrations/add_classifier_drill_mode.sql   seeds 12 base distractor groups
     migrations/add_classifier_groups.sql       adds 4 groups
                                                 (abstract, small_round, strands, sections)
  2. (optional) scripts/generate_classifier_curation.py  qwen → data/classifier_curation/<hanzi>.json
     scripts/merge_classifier_curation.py                → data/classifier_curation/approved_curation.json
  3. scripts/build_classifier_dictionary.py
       embedded CLASSIFIERS + NOUN_CLASSIFIERS, MERGED with approved_curation.json if present
       *** DELETES all language_id=1 rows in dim_classifiers + dim_classifier_noun_pairs,
           then re-inserts (serial ids regenerate) ***
       → dim_classifier_distractor_groups  (16 rows)
       → dim_classifiers                   (75 curated rows, language_id=1)
       → dim_classifier_noun_pairs         (~872 curated rows)
  4. scripts/import_cedict_classifiers.py   MUST run after the build to restore the
       CC-CEDICT long tail (~1.8k cedict pairs + ~71 lazy tier-4 'general' classifiers)

Session serving:
  GET /api/classifier-drill/session?language_id=1&count=20
    → routes/classifier_drill.py: get_drill_session
    → services/classifier_drill_service.py: get_session
    → db.rpc('get_classifier_drill_session', {user_id, language_id, count})
    → returns up to `count` items, each:
        {pair_id, noun_lemma, noun_sense_id, noun_gloss, noun_pronunciation,
         correct_classifier_ids[], correct_classifier_hanzi[],
         distractor_ids[], distractor_hanzi[], distractor_pinyin[],
         semantic_label, distractor_group_label, difficulty_tier}

Gameplay (static/js/session/players/classifier_drill.js + templates/classifier_drill.html):
  State: {mode, items, cursor, correct, errors, startTime, currentOptions,
          isLocked, currentItem}. Toggle [Choose | Type] persisted to localStorage.cd_mode.
  MC mode: 4 shuffled buttons (1 correct + 3 distractors), keys 1-4.
  Type mode: <input> accepts any hanzi in correct_classifier_ids.
  Wrong → feedback modal (canonical 一<correct><noun>, group label, also-acceptable list).

Submission:
  POST /api/classifier-drill/submit  body:{language_id,correct_items,total_items,
                                            time_taken,idempotency_key?}
    → routes/classifier_drill.py: submit_drill
    → services/classifier_drill_service.py: submit_session (caches sentinel test_id)
    → db.rpc('process_classifier_drill_submission', ...)
    → K=32 ELO update on user_skill_ratings + test_skill_ratings
    → INSERT INTO test_attempts (percentage column is GENERATED ALWAYS)
```

## The 个 exclusion (2026-06-07)

个 (gè) is the catch-all classifier. Drilling it teaches nothing and offering it as a
distractor lets the learner default to it, so it is **never an option**:

- The session RPC excludes 个 as both a correct answer and a distractor.
- Nouns whose *only* acceptable classifier is 个 are dropped from the pool entirely.
- The "answer classifier" used for distractor grouping is therefore always a SPECIFIC
  classifier (it re-bases on the best non-个 pair, even when 个 was the noun's primary).
- 个 is referenced **by hanzi, not id** — the build regenerates serial ids, so a hard-coded
  id would silently break after any rebuild.
- 个 rows remain in `dim_classifier_noun_pairs` as inert reference data; they are simply
  never served.

## Database Impact

### Tables (migrations: `add_classifier_drill_mode.sql`, `add_classifier_groups.sql`)

```sql
dim_classifier_distractor_groups (16 rows for language_id=1):
  id smallserial PK, language_id smallint FK→dim_languages,
  label text, description text, created_at timestamptz,
  UNIQUE(language_id, label)
  -- base 12: general, people, animals, long_thin, flat, bound, vehicles,
  --          containers, places, garments, events, plants
  -- added 4: abstract, small_round, strands, sections

dim_classifiers (~146 rows: 75 curated + ~71 CC-CEDICT lazy tier-4 'general'):
  id smallserial PK, language_id smallint FK→dim_languages,
  hanzi text, pinyin text, pinyin_display text,
  semantic_label text, example_nouns text[] DEFAULT '{}',
  frequency_rank integer, distractor_group_id smallint FK,
  difficulty_tier smallint,           -- 1=HSK1-2 core .. 4=rare/advanced
  created_at timestamptz,
  UNIQUE(language_id, hanzi)
  INDEX on distractor_group_id

dim_classifier_noun_pairs (~2.6k rows: ~872 curated + ~1.8k source='cedict'):
  id serial PK, language_id smallint FK, noun_sense_id integer FK→dim_word_senses (nullable),
  lemma_text text, classifier_id smallint FK→dim_classifiers ON DELETE CASCADE,
  is_primary boolean, frequency_score numeric, source text DEFAULT 'curated',
  UNIQUE(language_id, lemma_text, classifier_id)
  INDEX on (language_id, lemma_text)
  INDEX on classifier_id
```

### Modified tables (existing)

- `dim_test_types` — row `(id=14, type_code='classifier_drill', type_name='Measure Words', ...)`.
- `tests` — sentinel row `slug='__classifier_drill_zh'`, `is_active=false`, language_id=1.
- `test_skill_ratings` — anchors `(sentinel_test_id, classifier_drill_type_id)` at ELO 1400.
- `user_skill_ratings` — created lazily by the submission RPC on first attempt.
- `test_attempts` — written by the submission RPC. `percentage` is GENERATED ALWAYS.

### Reads / writes

- Session RPC reads `dim_classifier_noun_pairs`, `dim_classifiers`, `dim_classifier_distractor_groups`, `dim_word_senses`.
- Submission RPC reads/writes `test_attempts`, `user_skill_ratings`, `test_skill_ratings`, `user_languages`.

## API / RPC Surface

### `GET /api/classifier-drill/session`
- **Auth:** JWT required.
- **Query:** `language_id` (required, only `1` accepted in v1); `count` (default 20, max 40).
- **Returns:** `{"data": {"items": [{...}], "count": 20, "language_id": 1}}`
- **Errors:** 400 if `language_id` missing or != 1.

### `POST /api/classifier-drill/submit`
- **Auth:** JWT required.
- **Body:** `language_id`, `correct_items`, `total_items`, optional `time_taken`, `idempotency_key`.
- **Side effects:** Inserts `test_attempts`, mutates `user_skill_ratings` + `test_skill_ratings`, increments `user_languages.total_tests_taken`.
- **Returns:** accuracy, correct/total, `user_elo_change`, `test_elo_change`, `attempt_id`, `is_first_attempt`, `test_mode`.
- **Errors:** 400 on invalid body, 500 on RPC failure.

### RPC `get_classifier_drill_session(p_user_id uuid, p_language_id smallint, p_count integer)`
- `SECURITY DEFINER`, `STABLE`. GRANTed to `authenticated`. Canonical:
  `migrations/get_classifier_drill_session.sql`.
- Returns **13 columns** (the v1 12 + `out_difficulty_tier smallint`).
- Resolves `v_ge_id` = id of 个 **by hanzi** at the top.
- Sampling: `DISTINCT ON (lemma_text)` over rows where `classifier_id <> v_ge_id`, weighted by
  `random()*frequency_score` (primary first), then `LIMIT count`. 个-only nouns drop out here.
- `correct_ids`: all acceptable classifier ids for the lemma **excluding 个** (multi-valid).
- Distractors (always 3):
  - answer in a **specific** group → 3 same-group peers, `ORDER BY difficulty_tier ASC, random()`,
    excluding 个 + correct ids; topped up from the **core pool** if short.
  - answer in **`general`** → skip the polluted general bucket; fill all 3 from the **core pool**
    (`difficulty_tier <= 2 AND id <> v_ge_id`, excluding correct + already-chosen).
- No minimum-noun gate (per product decision); coverage is supplied by curation.

### RPC `process_classifier_drill_submission(...)`
- `SECURITY DEFINER`. K=32 ELO, first-attempt-only motion; repeats increment `tests_taken`
  without moving ELO. Idempotent on `(user_id, idempotency_key)`.

## Component Specification (UI)

- Player: `static/js/session/players/classifier_drill.js` (rendered in the unified /session
  runner) + standalone `templates/classifier_drill.html`.
- MC mode renders `[correct] + distractor_hanzi` shuffled → 4 buttons. Type mode checks the
  typed hanzi against `correct_classifier_ids`.
- Keyboard 1–4 (MC), Enter (Type submit / dismiss feedback). Touch + click for mobile.

## Offline curation pipeline (`services/classifier_curation/`)

LLM-assisted **authoring** tool; nothing here runs at request time.

- `config.py` — model slugs (`CLASSIFIER_GEN_MODEL`, default `qwen/qwen3.7-plus`), the fixed
  16-group vocabulary, target counts, judge threshold, output paths.
- `schemas.py` — `NounExample`, `NounList`, `ClassifierMeta`, `JudgeRatings` (Pydantic, used
  with `call_llm(..., schema=...)`).
- `generator.py` — `classify_classifier()` (group/tier/label for new/promoted measure words)
  and `generate_nouns()` (12–20 idiomatic nouns + 数词+量词+名词 example phrase, never 个).
- `judge.py` — `judge_nouns()`, a 1-5 Likert idiomatic-validity pass (fail-open).
- `scripts/generate_classifier_curation.py` — driver (`--smoke | --classifiers | --underserved`,
  `--classify`); writes per-classifier review JSON; cross-checks `dim_vocabulary`.
- `scripts/merge_classifier_curation.py` — consolidates accepted review JSON →
  `approved_curation.json`. Existing classifiers keep curated group/tier (only nouns folded in);
  new/promoted classifiers contribute an LLM-classified meta block for human review.

## Key Architectural Decisions

1. **Infinite session via sentinel test row** — reuses `test_attempts`/RLS/ELO/profile rendering.

2. **Deterministic runtime; LLM only offline (revised 2026-06-07)**
   - The serving path is fully deterministic and LLM-free. The original "no LLM at all" stance
     was relaxed for **offline authoring**: CC-CEDICT was exhausted as a coverage source (its
     `CL:` ceiling already matched the DB; 锅 0 / 束 1 nouns), so an LLM (qwen via OpenRouter)
     now proposes noun + example content, gated by a judge + human review of JSON before merge.
   - **Alternatives rejected:** per-request LLM (latency/cost/non-determinism); corpus mining
     (sparse); leaving classifiers starved (the drill repeats the same 1–3 nouns).

3. **Semantic distractor groups (16 groups, 75 curated classifiers)**
   - Plausibility of distractors is the key quality lever. Promoting real measure words out of
     the catch-all `general` bucket into proper groups (abstract/sections/strands/small_round/…)
     keeps same-group distractors confusable. `general`-answer items draw from a common core pool.

4. **MC + Typed runtime toggle** — MC scaffolds early learners; Typed forces recall. `localStorage.cd_mode`.

5. **First-attempt-only ELO motion** — matches pinyin/pitch-accent; prevents farming an infinite trainer.

## Security Considerations

- Both endpoints require JWT via `@supabase_jwt_required`; backend rejects `language_id != 1` in v1.
- Submission RPC validates `0 ≤ correct_items ≤ total_items`; `auth.uid() != p_user_id` guard.
- Idempotency key recommended for retry safety; server-generated UUID fallback.

## Testing Strategy

- **Data quality:** `COUNT(*)` on the three dim tables; spot-check high-frequency lemmas
  (`猫→只`, `车→辆`, `书→本`).
- **个 exclusion (regression):** run `get_classifier_drill_session(gen_random_uuid(),1,300)` and
  assert zero rows have 个 in `out_correct_classifier_hanzi` or `out_distractor_hanzi`, and every
  row has `array_length(out_distractor_ids,1) = 3`.
- **Curation quality:** spot-check `data/classifier_curation/*.json` (nouns truly take the
  classifier; example sentences well-formed; no 个-only nouns).
- **Submission RPC:** `correct=16,total=20` → non-zero first-attempt ELO; replay same key → `cached=true`.

## Verification History

- 2026-05-17 — Initial build: 40 classifiers, 269 pairs, 78 with sense linkage. RPCs green.
- 2026-06-07 — 个 excluded in the session RPC (by hanzi); added `out_difficulty_tier`; re-based
  distractor grouping on the specific classifier; core-pool distractors for `general` answers.
  Added 4 distractor groups; promoted ~20 measure words out of tier-4 `general`; built the
  offline qwen curation pipeline and merged ~495 authored noun-pairs. Roster 55→75 curated
  classifiers; previously-starved classifiers (束/锅/群/串/…) went from 1–9 nouns to 12–43.
  Rebuild verified: 0 个 in 300 sampled items, always 3 distractors.

## Related Pages

- [[features/measure-word-trainer]] — Prose description
- [[features/pinyin-trainer.tech]] — Sibling RPC layout
- [[features/pitch-accent-trainer.tech]] — Sibling RPC layout
- [[algorithms/elo-ranking.tech]] — K=32 formula shared by trainer
- [[database/schema.tech]] — Schema for the three classifier tables
