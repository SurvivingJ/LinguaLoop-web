-- ============================================================
-- Add distractor_types column to questions table
-- ============================================================
-- Stores the distractor type label for each option in a question.
-- Array of: "semantic" | "grammatical" | "contextual" | null (for correct answer)
-- Example: ["semantic", null, "contextual", "grammatical"]
-- ============================================================

ALTER TABLE questions ADD COLUMN IF NOT EXISTS distractor_types jsonb;

COMMENT ON COLUMN questions.distractor_types IS 'Array of distractor type labels per option: semantic|grammatical|contextual|null (null = correct answer)';
