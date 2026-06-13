-- ============================================================================
-- Ratify the semantic_class controlled vocabulary (6-value enum)
-- Date: 2026-06-12
-- Task: TASK-502 (wiki/tasklist/exercise-generation-v2.tasks.md); plan §4.
--
-- Replaces the informal/legacy semantic_class values with the ratified enum:
--   concrete | abstract | action | property | function | proper
-- so active_levels routing and the capability matrix (TASK-504) have a stable,
-- language-neutral key. Platform is pre-launch; the ~11 existing non-null rows
-- are remapped here in the same migration.
--
-- Legacy -> ratified remap (keyed, idempotent):
--   abstract_noun -> abstract
--   action_verb   -> action
--   adjective     -> property
--   具体名词       -> concrete     (Chinese "concrete noun")
-- Any other stray non-null value is NULLed (NULL = unclassified, still allowed
-- pre-backfill); a NOTICE lists anything dropped.
--
-- NULL remains permitted until the semantic_class backfill (TASK-507).
-- Idempotent: keyed UPDATEs + DROP CONSTRAINT IF EXISTS before ADD.
-- ============================================================================

UPDATE public.dim_vocabulary SET semantic_class = 'abstract' WHERE semantic_class = 'abstract_noun';
UPDATE public.dim_vocabulary SET semantic_class = 'action'   WHERE semantic_class = 'action_verb';
UPDATE public.dim_vocabulary SET semantic_class = 'property' WHERE semantic_class = 'adjective';
UPDATE public.dim_vocabulary SET semantic_class = 'concrete' WHERE semantic_class = '具体名词';

-- Defensive: NULL any remaining non-null value outside the ratified set, after
-- logging it. (No-op on the current live data; guards against stray legacy rows.)
DO $$
DECLARE
    leftover text;
BEGIN
    FOR leftover IN
        SELECT DISTINCT semantic_class
        FROM public.dim_vocabulary
        WHERE semantic_class IS NOT NULL
          AND semantic_class NOT IN ('concrete','abstract','action','property','function','proper')
    LOOP
        RAISE NOTICE 'semantic_class: NULLing unrecognised legacy value %', leftover;
    END LOOP;

    UPDATE public.dim_vocabulary
    SET semantic_class = NULL
    WHERE semantic_class IS NOT NULL
      AND semantic_class NOT IN ('concrete','abstract','action','property','function','proper');
END $$;

ALTER TABLE public.dim_vocabulary DROP CONSTRAINT IF EXISTS dim_vocabulary_semantic_class_check;
ALTER TABLE public.dim_vocabulary ADD CONSTRAINT dim_vocabulary_semantic_class_check
    CHECK (
        semantic_class IS NULL
        OR semantic_class IN ('concrete','abstract','action','property','function','proper')
    );
