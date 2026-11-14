"""
services.exercise_generation.judges
====================================
LLM-backed quality judges for generated content.

All judges share the JudgeOutcome type and threshold constants defined in
base.py. Each module exposes a single public function that accepts a Supabase
client, the content to evaluate, and a language_id; it returns JudgeOutcome
(or list[JudgeOutcome] for per-distractor judges).

Modules
-------
base                    -- JudgeOutcome, batch mode, and the shared runner
                           (JudgeSpec + run_likert_judge / run_candidate_judge /
                           run_keep_reject_judge) every judge module is a spec for
cloze                   -- Refactored cloze distractor judge (Batch 2)
answer_entailment       -- Does the passage entail the correct answer? (Batch 2)
distractor_plausibility -- Are distractors plausible-but-wrong? (Batch 2)
"""
