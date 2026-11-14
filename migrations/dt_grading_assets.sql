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
-- Pure additive schema change: every new column is NULLable with no default.
-- Config.DT_GRADING_ASSET_COLUMNS (config.py) defaults to TRUE since 2026-11-14,
-- so APPLY THIS FILE BEFORE (or together with) deploying that code. If it is not
-- applied the app still grades and saves every submission — routes/
-- dual_translation.py retries any statement that names these columns without
-- them and logs the problem once — but the fields below are then lost for those
-- submissions.
--
-- Revised 2026-11-14 (prompt v2, before this file was ever applied): span_source
-- and correction_source value sets changed, model_note now holds the L1
-- explanation shown to the learner, and confidence_label / explanation_source
-- were added.
--
--   1. dt_error_instance — seven columns the grader knows per error:
--        sentence_index     0-based index of the aligned sentence pair
--                           (services/dual_translation/sentence_pairs.py) whose
--                           learner sentence contains span_reproduction. This is
--                           the unit the guided-self-repair flow marks and
--                           re-checks, and what daily practice re-uses. NULL =
--                           written by a flow that does not compute it.
--        model_severity     the severity the model returned, before the
--                           per-language severity rule; `severity` stays the
--                           applied (scored) one.
--        model_note         the model's own one-sentence explanation in the
--                           learner's L1 (<= 240 chars), stored only when it
--                           passed the guards and is therefore SHOWN to the
--                           learner under the template text. `explanation`
--                           itself stays the template-rendered text (ADR-015).
--        explanation_source model | template | explainer — which text the
--                           learner was shown as the this-sentence explanation:
--                           the grading model's (model_note), none beyond the
--                           template (the model's text was rejected by a
--                           guard), or the opt-in v2 Explainer call's.
--        confidence_label   high | medium | low — the model's own confidence
--                           that this is a real error; `confidence` holds the
--                           mapped number (0.9 / 0.6 / 0.3).
--        span_source        exact | normalised | fuzzy | diff_hunk | sentence —
--                           how span_reproduction was resolved from the model's
--                           verbatim quote: found exactly; found after
--                           width/kana/case/punctuation folding; closest window
--                           in the sentence; the changed region of the sentence
--                           overlapping the quote; or (last resort) the error
--                           is marked on the whole learner sentence.
--        correction_source  model_quote | aligned_diff | reference_sentence —
--                           whether corrected_form/span_reference is the
--                           model's own reference quote, a local fragment found
--                           by aligning the two sentences, or the whole
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
--     (sentence no., learner quote, reference quote, type, severity, confidence,
--     source, one-sentence explanation; each string capped at 300 chars, at most
--     50 entries) and its two band judgments (band + evidence quote).
--   * raw_response (the unparsed text) is stored ONLY when the response could not
--     be parsed, and is cut to 4,000 chars (CHECK below).
--   Estimate per graded submission, single-call flow, primary model succeeds:
--     dt_grading_call row    ~0.35 KB fixed + ~0.25 KB per model error
--     dt_error_instance      ~0.15 KB per error for the seven new columns
--     dt_grade.grader_trace  ~1.1 KB + ~0.3 KB per error (existing jsonb column;
--                            carries slug, prompt version, usage, cost, latency,
--                            parse status, drop / span-resolution counts, the
--                            two judgments, per-error raw fields)
--     => ~1.5 KB for a clean submission, ~3 KB with two errors (the gold-set mean
--        is 0.9 errors per submission). Worst case (both models return unparsable
--        text): two rows x 4 KB raw = ~9 KB, and that submission is then graded
--        by the v2 flow.
--   At 10,000 graded submissions/month this is ~20-30 MB/month including indexes.
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
-- Additive and idempotent, with NO destructive statement (no DROP, no DELETE, no
-- column or type change): ADD COLUMN IF NOT EXISTS, CREATE TABLE / INDEX IF NOT
-- EXISTS, and each CHECK is added only if a constraint of that name is not
-- already there. Per migrations/CLAUDE.md the CHECKs on the existing table are
-- added NOT VALID inside the transaction (brief lock, no scan) and VALIDATEd
-- after COMMIT; the new columns are all NULL at that point, so validation cannot
-- fail. Re-running the file is a no-op. (Consequence of "no DROP": if a CHECK's
-- allowed values ever change, that is a new migration, not an edit of this one.)
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
    ADD COLUMN IF NOT EXISTS correction_source text,
    ADD COLUMN IF NOT EXISTS confidence_label  text,
    ADD COLUMN IF NOT EXISTS explanation_source text;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_sentence_index_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_sentence_index_check
        CHECK (sentence_index IS NULL OR sentence_index >= 0) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_model_severity_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_model_severity_check
        CHECK (model_severity IS NULL OR model_severity IN ('minor', 'major', 'critical')) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_model_note_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_model_note_check
        CHECK (model_note IS NULL OR char_length(model_note) <= 240) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_span_source_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_span_source_check
        CHECK (span_source IS NULL
               OR span_source IN ('exact', 'normalised', 'fuzzy', 'diff_hunk', 'sentence')) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_correction_source_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_correction_source_check
        CHECK (correction_source IS NULL
               OR correction_source IN ('model_quote', 'aligned_diff', 'reference_sentence')) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_confidence_label_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_confidence_label_check
        CHECK (confidence_label IS NULL OR confidence_label IN ('high', 'medium', 'low')) NOT VALID;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'dt_error_instance_explanation_source_check'
                   AND conrelid = 'public.dt_error_instance'::regclass) THEN
    ALTER TABLE public.dt_error_instance
        ADD CONSTRAINT dt_error_instance_explanation_source_check
        CHECK (explanation_source IS NULL
               OR explanation_source IN ('model', 'template', 'explainer')) NOT VALID;
  END IF;
END $$;

COMMENT ON COLUMN public.dt_error_instance.sentence_index IS
    '0-based index of the aligned sentence pair whose learner sentence contains '
    'span_reproduction (services/dual_translation/sentence_pairs.py; ADR-044). '
    'NULL = written by a flow that does not compute it (v1/v2 grades).';

COMMENT ON COLUMN public.dt_error_instance.model_severity IS
    'Severity the grading model returned, before the per-language severity rule '
    '(ADR-044). `severity` is the applied, scored value. NULL for v1/v2 grades.';

COMMENT ON COLUMN public.dt_error_instance.model_note IS
    'The single-call grader model''s own one-sentence explanation, in the learner''s '
    'L1, <= 240 chars, stored only when it passed the guards (then explanation_source '
    '= model and the learner is shown it under the template text). `explanation` '
    'stays the template-rendered text (ADR-015). Unreviewed model prose.';

COMMENT ON COLUMN public.dt_error_instance.explanation_source IS
    'Which this-sentence explanation the learner was shown: model = model_note; '
    'template = only the template `explanation` (the model''s text was missing or '
    'rejected by a guard); explainer = the opt-in v2 Explainer call (its text is '
    'appended to `explanation`). NULL for v1/v2 grades (ADR-044).';

COMMENT ON COLUMN public.dt_error_instance.confidence_label IS
    'The grading model''s own confidence that this is a real error: high | medium | '
    'low. `confidence` holds the mapped number (0.9 / 0.6 / 0.3). NULL for v1/v2 '
    'grades, whose `confidence` is a model-reported number (ADR-044).';

COMMENT ON COLUMN public.dt_error_instance.span_source IS
    'How span_reproduction was resolved from the model''s verbatim quote: exact; '
    'normalised (width/kana/case/punctuation folding); fuzzy (closest window in the '
    'sentence); diff_hunk (the changed region of the sentence overlapping the quote); '
    'sentence (last resort: the error is marked on the whole learner sentence) (ADR-044).';

COMMENT ON COLUMN public.dt_error_instance.correction_source IS
    'model_quote = corrected_form/span_reference is the model''s own reference quote, '
    'located in the reference sentence; aligned_diff = a local fragment found by '
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
    'v2 (base prompt) | v2_mit (with the Track E "free translations are expected" '
    'paragraph). Prompt v1 used p1_expl | p1_expl_mit.';
COMMENT ON COLUMN public.dt_grading_call.severity_rule IS
    'model = the model''s severity was scored; prior = the taxonomy default severity '
    'of the predicted type was scored unless the model said critical. NULL when the '
    'call produced no usable answer.';
COMMENT ON COLUMN public.dt_grading_call.cost_usd IS
    'USD cost as reported by OpenRouter on usage.cost; NULL when not reported.';
COMMENT ON COLUMN public.dt_grading_call.response IS
    'The model''s parsed answer {"errors": [{sentence, learner_quote, reference_quote, '
    'type, severity, confidence, source, explanation}], "naturalness": {band, '
    'evidence}, "range": {band, evidence}}, each string capped at 300 chars, at most '
    '50 entries. NULL when the response could not be parsed (see raw_response).';
COMMENT ON COLUMN public.dt_grading_call.dropped IS
    '{invalid_entry, unknown_type, low_confidence, span_unlocatable, decode_rejected}: model entries not turned '
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
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_confidence_label_check;
ALTER TABLE public.dt_error_instance VALIDATE CONSTRAINT dt_error_instance_explanation_source_check;
