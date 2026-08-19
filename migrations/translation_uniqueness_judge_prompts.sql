-- ============================================================================
-- translation_uniqueness_judge — prompt seeds (TASK-525)
-- Date: 2026-08-08
--
-- The eval scored tl_nl at 0% accept. The translations themselves were fine;
-- the DISTRACTORS were the problem — two or three options were each an
-- acceptable rendering of the TL sentence, so a learner who chose correctly
-- could still be marked wrong. This judge is the gate that must be in place
-- before translation types are scaled to ZH and JA.
--
-- ----------------------------------------------------------------------------
-- Rating orientation — DO NOT INVERT.
--   The Likert scale runs in the direction of KEEP, matching every other
--   ladder judge, so services/test_generation/schemas.likert_to_verdict maps
--   straight through with no negation on the Python side:
--
--     5 = clearly NOT an acceptable translation -> ideal distractor -> accept
--     4 = probably not acceptable                                   -> accept
--     3 = arguable                                                  -> flag
--     2 = probably also acceptable                                  -> reject
--     1 = a fully acceptable rendering (also-correct)               -> reject
--
--   Writing the scale the intuitive way round ("5 = yes, this is also an
--   acceptable translation") would silently KEEP exactly the distractors the
--   judge exists to remove, and the resulting item would still look
--   well-formed. tests/test_translation_uniqueness_judge.py asserts the
--   direction so a prompt edit cannot quietly flip it.
--
-- Output contract (consumed by judges/translation_uniqueness.py):
--   JSON object keyed by the 1-based candidate number; each value is
--   {"rating": <int 1-5>, "reason": "<short string>"}. A missing or
--   unparseable entry maps to `flag` (kept), never to a manufactured reject.
--
-- Template variables: {tl_sentence} {correct_translation} {nl_language}
--                     {candidates_numbered}
--
-- Model rationale: this is a short discrimination task over 2-3 candidates,
-- so it uses the same cheap per-language verifier tier as the other ladder
-- judges — EN/JA google/gemini-2.5-flash-lite, ZH qwen/qwen3.7-plus (the
-- currently-live zh slug; qwen/qwen-max was delisted by OpenRouter).
--
-- Each language is wrapped in its own BEGIN/COMMIT so a partial apply is safe.
-- Re-runnable: each block first deactivates every existing row for the same
-- (task_name, language_id), then upserts v1 back to is_active = true. The
-- upsert is ON CONFLICT ... DO UPDATE, not a bare INSERT: there is a UNIQUE
-- index on (task_name, language_id, version) (idx_prompt_templates_task_lang_ver),
-- so a bare INSERT aborts the whole block on a second run — and because the
-- deactivating UPDATE runs first inside the same transaction, the rollback
-- would leave the judge exactly as it started. The "re-runnable" claim in this
-- header was false in that specific way until TASK-525's live apply.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- English (language_id = 2), v1
-- ----------------------------------------------------------------------------
BEGIN;

UPDATE public.prompt_templates
   SET is_active = false
 WHERE task_name = 'translation_uniqueness_judge' AND language_id = 2;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'translation_uniqueness_judge',
    2,
    1,
    $PROMPT$You are checking a multiple-choice translation question for a fatal flaw: more than one option being right.

Source sentence (the language being learned): {tl_sentence}
The keyed answer (the option marked correct): {correct_translation}
Options are written in: {nl_language}

Candidate distractors (the options marked WRONG):
{candidates_numbered}

For each candidate, decide how clearly it is NOT an acceptable translation of the source sentence. A distractor is only doing its job if a competent bilingual speaker would say it is wrong. Paraphrases, synonyms, and differences of register or word order do NOT make a translation wrong — if the candidate conveys the same meaning as the source sentence, it is ALSO CORRECT and the question is broken.

Rate each candidate 1-5. Note the direction carefully:
5 = clearly not an acceptable translation; it changes the meaning, omits or adds information, or mistranslates a key word. An ideal distractor.
4 = probably not acceptable; a competent speaker would call it wrong, though it is close.
3 = arguable; it could be defended as a loose translation.
2 = probably also acceptable; most speakers would accept it.
1 = fully acceptable; it means the same as the source sentence. This option is also correct and must be removed.

Return JSON ONLY, keyed by the 1-based candidate number. Each value is an object with an integer "rating" (1-5) and a short "reason" (<= 15 words):
{{"1": {{"rating": 5, "reason": "reverses the subject and object"}}, "2": {{"rating": 1, "reason": "same meaning, only word order differs"}}}}

Rate EVERY candidate. No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'TASK-525: rejects tl_nl distractors that are also acceptable translations. Rating 5 = ideal distractor, 1 = also-correct.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- Chinese (language_id = 1), v1
-- ----------------------------------------------------------------------------
BEGIN;

UPDATE public.prompt_templates
   SET is_active = false
 WHERE task_name = 'translation_uniqueness_judge' AND language_id = 1;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'translation_uniqueness_judge',
    1,
    1,
    $PROMPT$You are checking a multiple-choice translation question for a fatal flaw: more than one option being right. The source sentence is Chinese (Mandarin).

Source sentence (Chinese): {tl_sentence}
The keyed answer (the option marked correct): {correct_translation}
Options are written in: {nl_language}

Candidate distractors (the options marked WRONG):
{candidates_numbered}

For each candidate, decide how clearly it is NOT an acceptable translation of the Chinese sentence. Paraphrases, synonyms, and differences of register or word order do NOT make a translation wrong — if the candidate conveys the same meaning, it is ALSO CORRECT and the question is broken.

Pay particular attention to features Chinese leaves implicit, because a distractor that only differs on one of them is usually still acceptable:
  - number (Chinese nouns are usually unmarked for singular/plural)
  - tense and aspect (only 了 / 过 / 在 / 着 mark it explicitly)
  - definiteness (there is no article; "the book" and "a book" can both be 书)
  - dropped subjects and objects recoverable from context

Differences in the actual event, participants, negation, or modality DO make a translation wrong.

Rate each candidate 1-5. Note the direction carefully:
5 = clearly not an acceptable translation; it changes the meaning, omits or adds information, or mistranslates a key word. An ideal distractor.
4 = probably not acceptable; a competent speaker would call it wrong, though it is close.
3 = arguable; it could be defended as a loose translation.
2 = probably also acceptable; most speakers would accept it.
1 = fully acceptable; it means the same as the source sentence. This option is also correct and must be removed.

Return JSON ONLY, keyed by the 1-based candidate number. Each value is an object with an integer "rating" (1-5) and a short "reason" (<= 15 words):
{{"1": {{"rating": 5, "reason": "negates the verb; source is affirmative"}}, "2": {{"rating": 1, "reason": "only differs on plural, unmarked in Chinese"}}}}

Rate EVERY candidate. No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'qwen/qwen3.7-plus',
    'openrouter',
    'TASK-525: rejects tl_nl distractors that are also acceptable translations. Rating 5 = ideal distractor, 1 = also-correct.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;


-- ----------------------------------------------------------------------------
-- Japanese (language_id = 3), v1
-- ----------------------------------------------------------------------------
BEGIN;

UPDATE public.prompt_templates
   SET is_active = false
 WHERE task_name = 'translation_uniqueness_judge' AND language_id = 3;

INSERT INTO public.prompt_templates (
    task_name, language_id, version, template_text, is_active, model, provider, description
)
VALUES (
    'translation_uniqueness_judge',
    3,
    1,
    $PROMPT$You are checking a multiple-choice translation question for a fatal flaw: more than one option being right. The source sentence is Japanese.

Source sentence (Japanese): {tl_sentence}
The keyed answer (the option marked correct): {correct_translation}
Options are written in: {nl_language}

Candidate distractors (the options marked WRONG):
{candidates_numbered}

For each candidate, decide how clearly it is NOT an acceptable translation of the Japanese sentence. Paraphrases, synonyms, and differences of register or word order do NOT make a translation wrong — if the candidate conveys the same meaning, it is ALSO CORRECT and the question is broken.

Pay particular attention to features Japanese leaves implicit, because a distractor that only differs on one of them is usually still acceptable:
  - number (nouns are usually unmarked for singular/plural)
  - definiteness (there is no article)
  - dropped subjects and objects recoverable from context
  - politeness level, which rarely changes the propositional content

Differences in the actual event, participants, negation, modality, or in who is doing what to whom (watch the particles は / が / を / に) DO make a translation wrong.

Rate each candidate 1-5. Note the direction carefully:
5 = clearly not an acceptable translation; it changes the meaning, omits or adds information, or mistranslates a key word. An ideal distractor.
4 = probably not acceptable; a competent speaker would call it wrong, though it is close.
3 = arguable; it could be defended as a loose translation.
2 = probably also acceptable; most speakers would accept it.
1 = fully acceptable; it means the same as the source sentence. This option is also correct and must be removed.

Return JSON ONLY, keyed by the 1-based candidate number. Each value is an object with an integer "rating" (1-5) and a short "reason" (<= 15 words):
{{"1": {{"rating": 5, "reason": "swaps the に and が participants"}}, "2": {{"rating": 1, "reason": "only differs on politeness level"}}}}

Rate EVERY candidate. No prose outside the JSON. No markdown fences.$PROMPT$,
    true,
    'google/gemini-2.5-flash-lite',
    'openrouter',
    'TASK-525: rejects tl_nl distractors that are also acceptable translations. Rating 5 = ideal distractor, 1 = also-correct.'
)
ON CONFLICT (task_name, language_id, version) DO UPDATE
SET template_text = EXCLUDED.template_text,
    is_active     = EXCLUDED.is_active,
    model         = EXCLUDED.model,
    provider      = EXCLUDED.provider,
    description   = EXCLUDED.description;

COMMIT;
