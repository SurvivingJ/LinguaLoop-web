-- ============================================================================
-- Dual Translation — guided self-repair: dt_repair_session, dt_repair_item,
-- dt_repair_event
-- Date: 2026-11-14
-- Spec: wiki/features/dt-guided-self-repair.tech.md (sections 4, 7, 9)
--
-- After a single-call grade (ADR-044) each flagged sentence becomes one repair
-- step: the learner fixes their own sentence with a hint ladder (where -> kind
-- -> clue -> answer) and each revision is re-checked by one grader call on that
-- sentence only. Unresolved items come back in daily practice.
--
--   1. dt_repair_session — one row per graded submission that entered the flow
--      (UNIQUE submission_id). Its presence records that the flow ran.
--   2. dt_repair_item    — one row per flagged sentence: the step, its live
--      sitting state, the repair-pass episode result, and the daily-practice
--      queue state.
--   3. dt_repair_event   — append-only event log: step opened, hint shown
--      (level + source + template id), each checked revision text with its
--      re-check result, latency, tokens, cost, model and prompt version, answer
--      shown, dispute, kept, skip, and one episode_closed per sitting.
--
-- Written by Flask (services/dual_translation/repair/store.py) with the service
-- role. routes/dual_translation.py degrades to today's submit response while
-- these tables are missing, so the file can be applied after the code deploys.
--
-- SIZE (design constraint: keep as much as possible, in as little as possible)
--   Not stored by design: prompts, raw model responses of successful calls
--   (failed re-checks get one llm_calls row), template hint texts (template id +
--   dt_repair_session.hint_version reproduce them), learner / reference sentence
--   copies (dt_repair_item keeps offsets into dt_submission.reproduction and
--   dt_passage.l2_text), revisions identical to the previous one (no call, no row).
--   Per row, incl. ~60 B tuple overhead and index entries:
--     session                                  ~0.4 KB
--     item                                     ~0.55 KB
--     event step_opened / hint_shown / answer  ~0.2 KB
--     event revision_checked                   ~0.55-0.8 KB
--     event episode_closed                     ~0.2 KB
--   Per error-bearing submission (1.5 steps, 1.6 checks, 1 hint per step):
--     0.4 + 1.5 x (0.55 + 0.2 + 0.2 + 1.6 x 0.65 + 0.2) ~= 3.2 KB; clean 0.4 KB;
--     at the gold set's 67 % error-bearing share ~= 2.3 KB per graded submission.
--     Worst case (4 steps x (open + 3 hints + 4 checks + closed) + session) ~= 18 KB.
--   Daily practice: ~1.6 KB per item sitting, <= 3 per user per day.
--   At 100 graded submissions/day + 50 practising users: ~0.5 MB/day, 15 MB/month.
--   At 1,000/day + 500 users: ~5 MB/day, ~150 MB/month -> apply retention.
--
-- RETENTION (not built here; a follow-up job once the three tables pass 50 MB):
--   delete step_opened / hint_shown events older than 180 days for items whose
--   queue_status <> 'due' (the item row keeps max_hint_level, outcome, n_checks);
--   keep revision_checked text indefinitely.
--
-- RLS: enabled on all three tables with NO policies and every client-role grant
-- revoked (deny-all through PostgREST; TASK-881). No client reads them.
--
-- Additive and idempotent: CREATE TABLE / INDEX IF NOT EXISTS, COMMENT, ENABLE
-- ROW LEVEL SECURITY, REVOKE. No DROP, no DELETE, no change to an existing table.
-- Re-running the file is a no-op.
--
-- SEARCH-BEFORE-ARCHIVE (migrations/CLAUDE.md): this file redefines nothing, so
-- nothing is superseded or archived.
--
-- VERIFY after applying:
--   SELECT relname, relrowsecurity FROM pg_class
--    WHERE relname IN ('dt_repair_session','dt_repair_item','dt_repair_event');  -- 3 rows, all t
--   SELECT grantee, table_name FROM information_schema.role_table_grants
--    WHERE table_name LIKE 'dt_repair_%' AND grantee IN ('anon','authenticated');  -- 0 rows
--   SELECT pg_size_pretty(sum(pg_total_relation_size(c)))
--     FROM unnest(array['dt_repair_session','dt_repair_item','dt_repair_event']::regclass[]) c;
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. dt_repair_session
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_repair_session (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    submission_id    bigint NOT NULL UNIQUE REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    user_id          uuid   NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    l2_language_id   integer NOT NULL REFERENCES public.dim_languages(id),
    l1_language_id   integer NOT NULL REFERENCES public.dim_languages(id),
    status           text NOT NULL CHECK (status IN ('open','finished','bypassed','abandoned')),
    n_sentences      smallint NOT NULL CHECK (n_sentences >= 0),
    n_flagged        smallint NOT NULL CHECK (n_flagged >= 0),
    n_steps          smallint NOT NULL CHECK (n_steps >= 0),
    grade_tier       text,
    prompt_version   text,
    hint_version     text NOT NULL,
    settings         jsonb NOT NULL,
    closed_early     boolean,
    total_ms         integer,
    created_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_session_user_status
    ON public.dt_repair_session (user_id, status);

COMMENT ON TABLE public.dt_repair_session IS
    'Guided self-repair pass of one graded Dual Translation submission '
    '(wiki/features/dt-guided-self-repair.tech.md). open while the learner works '
    'through the steps; finished (incl. clean: n_flagged = 0), bypassed (>= 5 '
    'flagged sentences or a band of 1: answers shown directly) or abandoned (open '
    'longer than DT_REPAIR_SESSION_STALE_HOURS). Written by Flask, never client-readable.';
COMMENT ON COLUMN public.dt_repair_session.grade_tier IS
    'dt_grade.grader_trace.tier at creation: single_call | tier0.';
COMMENT ON COLUMN public.dt_repair_session.prompt_version IS
    'grader_trace.single_call.prompt_version of the grade (re-checks use the same prompt).';
COMMENT ON COLUMN public.dt_repair_session.hint_version IS
    'services/dual_translation/repair/hint_templates.json version: with an event''s '
    'hint_template_id it reproduces the hint text that was shown.';
COMMENT ON COLUMN public.dt_repair_session.settings IS
    'Snapshot of the planning settings at creation: {max_targets, bypass, '
    'unsure_max, cap_pass, loc_share}.';
COMMENT ON COLUMN public.dt_repair_session.total_ms IS
    'Server time finished_at - created_at, ms.';

-- ============================================================================
-- 2. dt_repair_item
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_repair_item (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id        bigint NOT NULL REFERENCES public.dt_repair_session(id) ON DELETE CASCADE,
    user_id           uuid   NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    submission_id     bigint NOT NULL REFERENCES public.dt_submission(id) ON DELETE CASCADE,
    error_id          bigint NOT NULL REFERENCES public.dt_error_instance(id) ON DELETE CASCADE,
    l2_language_id    integer NOT NULL REFERENCES public.dim_languages(id),
    sentence_index    smallint NOT NULL CHECK (sentence_index >= 0),
    step_order        smallint CHECK (step_order IS NULL OR step_order >= 0),
    step_kind         text NOT NULL CHECK (step_kind IN ('repair','unsure','direct')),
    ladder            text NOT NULL CHECK (ladder IN ('full','short','none')),
    location_available boolean NOT NULL,
    subtype           text NOT NULL,
    severity          text NOT NULL CHECK (severity IN ('minor','major','critical')),
    confidence        real,
    repro_start       integer NOT NULL, repro_end integer NOT NULL,
    ref_start         integer NOT NULL, ref_end   integer NOT NULL,
    span_start        smallint, span_end smallint,
    -- live state of the current sitting
    sitting           smallint NOT NULL DEFAULT 0,
    sitting_open      boolean NOT NULL DEFAULT false,
    hint_level        smallint NOT NULL DEFAULT 0 CHECK (hint_level BETWEEN 0 AND 4),
    checks_used       smallint NOT NULL DEFAULT 0,
    calls_used        smallint NOT NULL DEFAULT 0,
    last_text         text CHECK (last_text IS NULL OR char_length(last_text) <= 400),
    active            jsonb,
    opened_at         timestamptz,
    check_lock_until  timestamptz,
    -- repair-pass episode result
    outcome           text CHECK (outcome IS NULL OR outcome IN ('self_repaired','repaired_alternative',
                        'answer_shown','shown_directly','disputed','skipped',
                        'unsure_revised','unsure_dismissed','unsure_skipped')),
    answer_reason     text CHECK (answer_reason IS NULL OR answer_reason IN ('asked','auto_cap','grader_failed','budget','direct')),
    max_hint_level    smallint CHECK (max_hint_level IS NULL OR max_hint_level BETWEEN 0 AND 4),
    n_checks          smallint NOT NULL DEFAULT 0,
    time_ms           integer,
    first_edit_ms     integer,
    closed_at         timestamptz,
    -- daily-practice queue
    queue_status      text NOT NULL DEFAULT 'none'
                        CHECK (queue_status IN ('none','due','resolved','retired','expired','disputed')),
    queued_at         timestamptz,
    due_on            date,
    not_before        timestamptz,
    expires_at        timestamptz,
    failed_sittings   smallint NOT NULL DEFAULT 0,
    hinted_sittings   smallint NOT NULL DEFAULT 0,
    last_practiced_at timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (repro_end >= repro_start AND ref_end >= ref_start),
    CHECK ((span_start IS NULL) = (span_end IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_session ON public.dt_repair_item (session_id);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_error   ON public.dt_repair_item (error_id);
CREATE INDEX IF NOT EXISTS idx_dt_repair_item_due
    ON public.dt_repair_item (user_id, l2_language_id, due_on) WHERE queue_status = 'due';

COMMENT ON TABLE public.dt_repair_item IS
    'One flagged sentence of a guided-repair session: the step (kind, ladder, '
    'primary error), the live state of the current sitting, the repair-pass '
    'episode result, and its daily-practice queue state.';
COMMENT ON COLUMN public.dt_repair_item.error_id IS
    'The sentence''s primary (most serious) dt_error_instance row.';
COMMENT ON COLUMN public.dt_repair_item.repro_start IS
    'Offsets, not copies: the learner sentence is dt_submission.reproduction[repro_start:repro_end] '
    '(whitespace-stripped pair bounds of sentence_pairs.build_sentence_pairs).';
COMMENT ON COLUMN public.dt_repair_item.ref_start IS
    'Offsets, not copies: the reference sentence is dt_passage.l2_text[ref_start:ref_end].';
COMMENT ON COLUMN public.dt_repair_item.span_start IS
    'Primary error span local to the learner sentence (NULL when not locatable).';
COMMENT ON COLUMN public.dt_repair_item.sitting IS
    '0 = the repair pass; n = the n-th daily-practice sitting.';
COMMENT ON COLUMN public.dt_repair_item.active IS
    'The current target error {subtype, severity, form, start, end, corrected_form, '
    'correction_source, span_source, error_id}, offsets into the text the learner '
    'currently has (the original sentence, or last_text after a re-check moved it).';
COMMENT ON COLUMN public.dt_repair_item.check_lock_until IS
    'Per-item re-check lock (prevents two parallel checks, e.g. two tabs).';
COMMENT ON COLUMN public.dt_repair_item.queue_status IS
    'Daily practice: none (never queued) | due | resolved | retired | expired | disputed.';
COMMENT ON COLUMN public.dt_repair_item.max_hint_level IS
    'Highest hint level of the repair pass (4 = answer shown); orders daily practice.';

-- ============================================================================
-- 3. dt_repair_event
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dt_repair_event (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id          bigint NOT NULL REFERENCES public.dt_repair_item(id) ON DELETE CASCADE,
    user_id          uuid   NOT NULL,
    surface          text NOT NULL CHECK (surface IN ('repair_pass','daily_practice')),
    sitting          smallint NOT NULL,
    kind             text NOT NULL CHECK (kind IN ('step_opened','hint_shown','revision_checked',
                        'answer_shown','disputed','kept','skipped','episode_closed')),
    hint_level       smallint NOT NULL CHECK (hint_level BETWEEN 0 AND 4),
    since_prev_ms    integer,
    hint_source      text CHECK (hint_source IS NULL OR hint_source IN ('grader_span','template','taxonomy_gloss','type_neutral')),
    hint_template_id text,
    client_check_id  uuid,
    text             text CHECK (text IS NULL OR char_length(text) <= 400),
    result           text CHECK (result IS NULL OR result IN ('fixed','no_issue_found','still_flagged','error')),
    result_detail    jsonb,
    latency_ms       integer,
    tokens_in        integer,
    tokens_out       integer,
    cost_usd         numeric(12, 8),
    model_slug       text,
    prompt_version   text,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dt_repair_event_item ON public.dt_repair_event (item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dt_repair_event_check
    ON public.dt_repair_event (item_id, client_check_id) WHERE client_check_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dt_repair_event_user_checks
    ON public.dt_repair_event (user_id, created_at) WHERE kind = 'revision_checked';

COMMENT ON TABLE public.dt_repair_event IS
    'Append-only guided-repair event log (one row per learner action / re-check / '
    'closed episode). Successful re-checks are recorded only here (model, tokens, '
    'cost, latency), not in llm_calls.';
COMMENT ON COLUMN public.dt_repair_event.user_id IS
    'Denormalised for the per-user daily re-check budget query; no FK on purpose '
    '(the item cascade covers deletion).';
COMMENT ON COLUMN public.dt_repair_event.client_check_id IS
    'Client idempotency key of a check: a replay returns the stored result without a new call.';
COMMENT ON COLUMN public.dt_repair_event.text IS
    'The revision the learner checked (normalised), <= 400 chars.';
COMMENT ON COLUMN public.dt_repair_event.result_detail IS
    'revision_checked: {"r": reason|null, "e": [[subtype, severity, start, end, conf_label], <= 5], '
    '"x": model note of the active error <= 240 chars}; episode_closed: {"o": outcome, '
    '"t": time_ms, "n": checks, "a": answer_reason, "h": max hint level}; hint_shown: '
    '{"leak_blocked": true} when a clue was replaced by the type-neutral text.';

ALTER TABLE public.dt_repair_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_repair_item    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dt_repair_event   ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.dt_repair_session FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.dt_repair_item    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.dt_repair_event   FROM PUBLIC, anon, authenticated;

COMMIT;
