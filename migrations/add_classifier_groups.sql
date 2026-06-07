-- ============================================================================
-- add_classifier_groups.sql
--
-- Adds semantic distractor groups needed by the expanded classifier roster.
-- The original 12 groups (add_classifier_drill_mode.sql) dumped every
-- CC-CEDICT-imported measure word into 'general'. Promoting those real measure
-- words (份, 道, 种, 项, 颗, 粒, 股, 段 …) into proper buckets needs these
-- additional groups so same-group distractors stay semantically coherent.
--
-- build_classifier_dictionary.py only READS groups (it errors on an unknown
-- group label), so this migration MUST be applied before the next rebuild.
-- Idempotent via the UNIQUE (language_id, label) constraint.
-- ============================================================================

INSERT INTO dim_classifier_distractor_groups (language_id, label, description) VALUES
    (1, 'abstract',    'Abstract measures: kinds, items, portions, sums, subjects'),
    (1, 'small_round', 'Small round objects (seeds, grains, pearls, stars)'),
    (1, 'strands',     'Strands, wisps and streams (smoke, smell, hair, energy)'),
    (1, 'sections',    'Sections and segments (of road, time, text, sugarcane)')
ON CONFLICT (language_id, label) DO NOTHING;
