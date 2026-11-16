-- Learner-facing exercise explanations are written in English for every
-- language (they were in the target language). New active versions of the
-- vocab ladder prompt-2 templates and the semantic-discrimination generators
-- get an override block appended; the previous versions are deactivated.
BEGIN;

WITH src AS (
  SELECT DISTINCT ON (task_name, language_id) *
  FROM public.prompt_templates
  WHERE is_active
    AND task_name IN ('vocab_prompt2_exercises',
                      'semantic_discrimination_generation',
                      'semantic_discrimination_from_context')
  ORDER BY task_name, language_id, version DESC
), ins AS (
  INSERT INTO public.prompt_templates
    (task_name, language_id, version, template_text, is_active, description, model, provider, tier_id)
  SELECT task_name, language_id, version + 1,
         template_text || E'\n\n' || $blk$
=== EXPLANATION LANGUAGE (overrides any earlier instruction about explanation language) ===
Write EVERY explanation field in ENGLISH — option explanations, wrong-sentence explanations and error descriptions — whatever the target language. Quote target-language words or phrases where they help. Exercise text itself (sentences, options) stays in the target language.
Each explanation must be informative: name the specific problem (wrong sense, wrong collocation, wrong particle/preposition, wrong part of speech, register, contradiction with the rest of the sentence) and say WHY, tied to what the target word means in this sense. 1–2 sentences, under ~40 words.
Good: "わずか means a tiny amount, but the sentence says he drank lots every day — the two contradict."
Good: "地点 is a place, but 下午三点 is a time; a meeting's time is 时间."
Never write vague lines such as "doesn't fit the context", "wrong usage", "unnatural", or "the meaning doesn't match". Each wrong sentence gets its own distinct explanation.
Failure tags that lead an explanation (e.g. "semantic: …") are written in English: semantic / collocation / aspectual / register / valency.
$blk$,
         true, description, model, provider, tier_id
  FROM src
  RETURNING task_name, language_id, version
)
UPDATE public.prompt_templates p SET is_active = false
FROM ins
WHERE p.task_name = ins.task_name AND p.language_id = ins.language_id
  AND p.version < ins.version AND p.is_active;

COMMIT;
