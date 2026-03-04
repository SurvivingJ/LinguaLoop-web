-- Vocabulary Phrase Detection Prompt Templates
-- Inserts prompts used by the vocabulary extraction pipeline
-- to detect multi-word expressions via LLM.

INSERT INTO prompt_templates (task_name, language_id, template_text, description, version)
VALUES
(
    'vocab_phrase_detection',
    2,  -- English
    'You are a linguistics expert. Given the following lemma list extracted from a text, identify all multi-word expressions (phrasal verbs, compound nouns, collocations, idioms).

Original text: {original_text}

Lemma list: {lemma_list}

Return a JSON object with a "phrases" array. Each phrase should have:
- "phrase": the combined expression (e.g., "throw up")
- "components": array of component lemmas (e.g., ["throw", "up"])
- "phrase_type": one of "phrasal_verb", "compound_noun", "collocation", "idiom"

Only return phrases where the meaning differs from the individual words.
Return ONLY valid JSON, no explanation.',
    'Detect multi-word expressions from English lemma list',
    1
),
(
    'vocab_phrase_detection',
    3,  -- Japanese
    'You are a Japanese linguistics expert. Given the following lemma list extracted from Japanese text, identify compound expressions (複合語), set phrases (慣用句), and collocations.

Original text: {original_text}

Lemma list: {lemma_list}

Return a JSON object with a "phrases" array. Each phrase should have:
- "phrase": the combined expression
- "components": array of component lemmas
- "phrase_type": one of "compound", "idiom", "collocation"

Return ONLY valid JSON, no explanation.',
    'Detect compound expressions from Japanese lemma list',
    1
);
