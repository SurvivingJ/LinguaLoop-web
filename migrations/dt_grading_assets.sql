-- ============================================================================
-- Dual Translation — grading assets: per-error grader fields + dt_grading_call
-- Date: 2026-11-14
--
-- Storage for what the single-call generative grader (ADR-044,
-- services/dual_translation/single_call_grader.py) produces beyond the grade
-- itself, so that real submissions can be used for later design work (shadow
-- comparisons, native review of explanations, guided self-repair, re-using a
-- learner's own erroneous sentences in daily practice).
--
-- Pure additive schema change. Safe to apply before any code change and before
-- the grader flag is turned on: every new column is NULLable with no default,
-- and nothing reads or writes the new objects until Config.DT_GRADING_ASSET_COLUMNS
-- is turned on (config.py) — which MUST happen only after this file is applied
-- (PostgREST rejects an insert/select naming a column that does not exist).
--
--   1. dt_error_instance — five columns the grader knows per error:
--        sentence_index     0-based index of the aligned sentence pair
--                           (services/dual_translation/sentence_pairs.py) whose
--                           learner sentence contains span_reproduction. This is
--                           the unit the guided-self-repair flow marks and
--                           re-checks, and what daily practice re-uses. NULL =
--                           written by a flow that does not compute it.
--        model_severity     the severity the model returned, before the
--                           per-language severity rule; `severity` stays the
--                           applied (scored) one.
--        model_note         the model's own short explanation (English, <= 240
--                           chars, guard-checked). Kept apart from `explanation`,
--                           which stays the template-rendered text (ADR-015).
--        span_source        model | repaired | sentence — whether
--                           span_reproduction is the model's fragment verbatim,
--                           a relocated one, or the whole learner sentence
--                           because the fragment could not be located.
--        correction_source  aligned_diff | reference_sentence — whether
--                           corrected_form/span_reference is a local fragment
--                           found by aligning the two sentences, or the whole
--                           reference sentence (free rewrites; not cloze-safe).
--
--   2. dt_grading_call — one row per grading model call (attempt). A graded
--      submission normally has exactly one row; a model fallback adds a second;
--      `role = 'shadow'` is reserved for a second grader run alongside the live
--      one (the shadow run recommended in
--      wiki/evaluations/dt-decision-grading-2026-11-14.md), whose decoded result
--      has no dt_grade row and goes in `result`. No code writes shadow rows yet.
--
-- SIZE (design constraint: keep as much as possible, in as little as possible)
--   * The PROMPT IS NOT STORED. It is reproducible from prompt_version +
--     prompt_variant + dt_passage.l2_text + dt_submission.reproduction, and it is
--     ~1,000 tokens (~4-6 KB) that would be identical for every row of a language.
--   * No learner or reference text is copied: errors keep offsets + the short
--     forms they already had; `response` holds only the model's own error list
--     (sentence no., fragment, type, severity, <=15-word note; each string capped
--     at 300 chars, at most 50 entries).
--   * raw_response (the unparsed text) is stored ONLY when the response could not
--     be parsed, and is cut to 4,000 chars (CHECK below).
--   Estimate per graded submission, single-call flow, primary model succeeds:
--     dt_grading_call row    ~0.25 KB fixed + ~0.15 KB per model error
--     dt_error_instance      ~0.12 KB per error for the five new columns
--     dt_grade.grader_trace  ~0.7 KB + ~0.2 KB per error (existing jsonb column;
--                            carries slug, prompt version, usage, cost, latency,
--                            parse status, drop counts, per-error raw fields)
--     => ~1 KB for a clean submission, ~2 KB with two errors (the gold-set mean
--        is 0.9 errors per submission). Worst case (both models return unparsable
--        text): two rows x 4 KB raw = ~9 KB, and that submission is then graded
--        by the v2 flow.
--   At 10,000 graded submissions/month this is ~15-20 MB/month including indexes.
--   In addition each call writes one llm_calls row (existing table, ~0.3 KB; its
--   raw_response is likewise only filled on a parse failure).
--
-- NOT HERE (belongs to the guided-self-repair UI task, see
-- wiki/features/dual-translation.tech.md "Single-call grader"): tables for UI
-- interaction tracking — hint level reached, revision attempts, per-sentence
-- re-check results, daily-practice scheduling of a learner's own sentences.
--
-- RLS: dt_grading_call is enabled with NO policies and all client-role grants
-- revoked (deny-all through PostgREST; Flask writes with the service role). It
-- holds model output about every learner's submissions and is never read by a
-- client.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS, CREATE TABLE / INDEX IF NOT EXISTS,
-- drop-then-add CHECKs. Per migrations/CLAUDE.md the CHECKs on the existing
-- table are added NOT VALID inside the transaction (brief lock, no scan) and
-- VALIDATEd after COMMIT; the new columns are all NULL at that point, so
-- validation cannot fail.
--
-- SEARCH-BEFORE-ARCHIVE (migrations/CLAUDE.md): this file only ADDS columns and
-- constraints to dt_error_instance (dual_translation_groundwork.sql,
-- dt_severity_triad.sql, dt_taxonomy_v6_columns.sql) and creates one new table;
-- it redefines nothing, so no file is superseded. The dt_v5_snapshot_* tables
-- (dt_taxonomy_v6_columns.sql) are `LIKE` copies frozen at their creation and do
-- NOT gain these columns — the TASK-852 snapshot/restore already names its
-- columns explicitly.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. dt_error_instance — per-error grader fields
-- ============================================================================

ALTER TABLE public.dt_error_instance
    ADD COLUMN IF NOT EXISTS sentence_index    smallint,
    ADD COLUMN IF NOT EXISTS model_severity    text,
    ADD COLUMN IF NOT EXISTS model_note        text,
    ADD COLUMN IF NOT EXISTS span_source       text,
    ADD COLUMN IF NOT EXISTS correction_source text;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_sentence_index_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_sentence_index_check
    CHECK (sentence_index IS NULL OR sentence_index >= 0) NOT VALID;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_model_severity_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_model_severity_check
    CHECK (model_severity IS NULL OR model_severity IN ('minor', 'major', 'critical')) NOT VALID;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_model_note_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_model_note_check
    CHECK (model_note IS NULL OR char_length(model_note) <= 240) NOT VALID;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_span_source_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_span_source_check
    CHECK (span_source IS NULL OR span_source IN ('model', 'repaired', 'sentence')) NOT VALID;

ALTER TABLE public.dt_error_instance
    DROP CONSTRAINT IF EXISTS dt_error_instance_correction_source_check;
ALTER TABLE public.dt_error_instance
    ADD CONSTRAINT dt_error_instance_correction_source_check
    CHECK (correction_source IS NULL
           OR correction_source IN ('aligned_diff', 'reference_sentence')) NOT VALID;

COMMENT ON COLUMN public.dt_error_instance.sentence_index IS
    '0-based index of the aligned sentence pair whose learner sentence contains '
    'span_reproduction (services/dual_translation/sentence_pairs.py; ADR-044). '
    'NULL = written by a flow that does not compute it (v1/v2 grades).';

COMMENT ON COLUMN public.dt_error_instance.model_severity IS
    'Severity the grading model returned, before the per-language severity rule '
    '(ADR-044). `severity` is the applied, scored value. NULL for v1/v2 grades.';

COMMENT ON COLUMN public.dt_error_instance.model_note IS
    'The single-call grader model''s own short explanation (English, guard-checked, '
    '<= 240 chars). Never shown as the eager explanation — `explanation` stays the '
    'template-rendered text (ADR-015). Unreviewed model prose.';

COMMENT ON COLUMN public.dt_error_instance.span_source IS
    'model = span_reproduction is the model''s fragment found verbatim; repaired = '
    'relocated/normalisation-matched; sentence = the fragment could not be located '
    'and the whole learner sentence is used (ADR-044).';

COMMENT ON COLUMN public.dt_error_instance.correction_source IS
    'aligned_diff = corrected_form/span_reference is a local fragment found by '
    'aligning the learner sentence with its reference sentence; reference_sentence '
    '= the whole reference sentence (free rewrite or no local difference). Rows '
    'with reference_sentence are not suitable for cloze cards (ADR-044).';

-- ============================================================================
-- 2. dt_grading_call — one row per grading model call
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_grading_call (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id     bigint NOT NULL REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    flow              text NOT NULL,
    role              text NOT NULL CHECK (role IN ('primary', 'fallback', 'shadow')),
    model_slug        text NOT NULL,
    provider          text,
    prompt_version    text NOT NULL,
    prompt_variant    text,
    severity_rule     text CHECK (severity_rule IS NULL OR severity_rule IN ('model', 'prior')),
    l2_code           text,
    status            text NOT NULL
                      CHECK (status IN ('ok', 'call_failed', 'malformed_json', 'malformed_shape')),
    error             text CHECK (error IS NULL OR char_length(error) <= 300),
    finish_reason     text,
    tokens_in         integer,
    tokens_out        integer,
    cached_tokens     integer,
    reasoning_tokens  integer,
    cost_usd          numeric(12, 8),
    latency_ms        integer,
    taxonomy_version  smallint,
    rubric_version    smallint,
    response          jsonb,
    errors_raw        smallint,
    errors_kept       smallint,
    dropped           jsonb,
    result            jsonb,
    raw_response      text CHECK (raw_response IS NULL OR char_length(raw_response) <= 4000),
    raw_truncated     boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.dt_grading_call IS
    'One row per Dual Translation grading model call (ADR-044): which model and '
    'prompt version graded a submission, what it cost, and the model''s own '
    'structured answer. The prompt is not stored (reproducible from prompt_version '
    '+ prompt_variant + the passage and submission texts). role: primary | fallback '
    '(second model after the first failed) | shadow (reserved: a second grader run '
    'alongside the live one; its decoded grade goes in `result`). Written by Flask '
    'with the service role, best-effort, after dt_grade; never client-readable.';

COMMENT ON COLUMN public.dt_grading_call.flow IS
    'Grading flow that issued the call. ''single_call'' today.';
COMMENT ON COLUMN public.dt_grading_call.prompt_version IS
    'services/dual_translation/single_call_prompts.PROMPT_VERSION at call time.';
COMMENT ON COLUMN public.dt_grading_call.prompt_variant IS
    'p1_expl (validated base prompt) | p1_expl_mit (with the Track E "free '
    'translations are expected" paragraph).';
COMMENT ON COLUMN public.dt_grading_call.severity_rule IS
    'model = the model''s severity was scored; prior = the taxonomy default severity '
    'of the predicted type was scored unless the model said critical. NULL when the '
    'call produced no usable answer.';
COMMENT ON COLUMN public.dt_grading_call.cost_usd IS
    'USD cost as reported by OpenRouter on usage.cost; NULL when not reported.';
COMMENT ON COLUMN public.dt_grading_call.response IS
    'The model''s parsed answer {"errors": [{sentence, span, type, severity, '
    'explanation}]}, each string capped at 300 chars, at most 50 entries. NULL when '
    'the response could not be parsed (see raw_response).';
COMMENT ON COLUMN public.dt_grading_call.dropped IS
    '{invalid_entry, span_unlocatable, decode_rejected}: model entries not turned '
    'into dt_error_instance rows, by reason.';
COMMENT ON COLUMN public.dt_grading_call.result IS
    'Reserved for role = ''shadow'': the decoded grade (scores, overall_band, '
    'errors) of a grader whose result is not the one in dt_grade. NULL otherwise.';
COMMENT ON COLUMN public.dt_grading_call.raw_response IS
    'Unparsed response text, stored only when parsing failed, cut to 4,000 chars '
    '(raw_truncated says whether it was cut).';

CREATE INDEX IF NOT EXISTS idx_dt_grading_call_submission
    ON public.dt_grading_call (submission_id);

CREATE INDEX IF NOT EXISTS idx_dt_grading_call_created
    ON public.dt_grading_call (created_at);

ALTER TABLE public.dt_grading_call ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dt_grading_call FROM PUBLIC, anon, authenticated;

COMMIT;

-- Validate the new CHECKs outside the transaction (SHARE UPDATE EXCLUSIVE; does
-- not block reads or writes). Every new column is NULL here, so these cannot fail.
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_sentence_index_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_model_severity_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_model_note_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_span_source_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_correction_source_check;
