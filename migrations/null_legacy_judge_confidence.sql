-- Clear the pre-v4 `llm_calls.judge_confidence` history.
--
-- WHY: the column is a single `real` with no scale marker, and it holds TWO
-- incompatible scales. Some judges write a 0-1 probability
-- (`judge_answer_entailment`, `cloze_distractor_judge`); the Likert judges write
-- a 1-5 rating (`judge_distractor_plausibility`, `judge_ladder_*`). Worse,
-- `judge_distractor_plausibility` spans BOTH within one task_name -- it predates
-- the v3 Likert conversion, so 169 of its 389 rows are probabilities and 220 are
-- ratings.
--
-- The collision is not merely imprecise, it INVERTS: a stored 1.0 means
-- "maximum confidence, accept" on the probability scale and "worst rating,
-- reject" on the Likert scale. Nothing in the codebase can tell them apart.
--
-- WHY NULL AND NOT A `judge_scale` COLUMN: a repo-wide grep finds NO reader of
-- judge_confidence -- only writers (`services/llm_service.py` x8,
-- `services/exercise_generation/judges/base.py:306`), the column definition, and
-- one test fixture. There is no consumer to migrate and no analysis to preserve,
-- so a scale column would be bookkeeping for data nobody reads.
--
-- WHY NOT DELETE THE ROWS: `llm_calls` rows also carry `cost_usd`,
-- `latency_ms` and `raw_response` -- the only spend history that exists. Dropping
-- rows to clean one unread column would destroy the cost record. Only the
-- ambiguous column is cleared; every other field on every row is untouched.
--
-- BOUNDARY: 2026-08-16 00:00:00+00 sits inside a verified empty gap. The last
-- pre-v4 judge_confidence row is 2026-08-14 22:58:14+00; the first post-v4 rows
-- are the three v4 smoke calls at 2026-08-16 04:44 (confidences 4 / 5 / 2). Those
-- three are the first values written under a single known scale and are
-- deliberately preserved as the seed of the clean era.
--
-- EXPECTED: 888 rows cleared, 3 preserved (891 non-null before).
--
-- NOT REVERSIBLE. The prior values exist nowhere else. This is accepted
-- deliberately: they are unreadable by design and no consumer exists.
--
-- AFTER THIS: the column is consistent PER TASK, not globally.
-- `judge_distractor_plausibility` writes Likert 1-5 (v4 guarantees a real
-- integer); `judge_answer_entailment` still writes 0-1 probability. Do not build
-- anything that aggregates judge_confidence ACROSS judges without first adding a
-- scale marker.

BEGIN;

UPDATE llm_calls
   SET judge_confidence = NULL
 WHERE judge_confidence IS NOT NULL
   AND created_at < '2026-08-16 00:00:00+00';

COMMIT;
