-- Seed prompt_templates rows for the two kana-homophone judges
-- (services/vocabulary/kana_homophone_judge.py). Japanese-only
-- (language_id=3) — see that module's docstring for why this problem is
-- ja-specific (zh true-homophones were evaluated and rejected as
-- out-of-scope for the L1 distractor system; this is a different feature,
-- vocab-identity resolution, but the same scoping decision applies).
--
-- Model: google/gemini-3.5-flash-lite via openrouter — the live model for
-- the ja distractor/entailment/translation-uniqueness judges as of this
-- migration (see prompt_templates rows for test_distractor_plausibility,
-- test_answer_entailment, translation_uniqueness_judge at language_id=3).

INSERT INTO prompt_templates (task_name, language_id, template_text, version, is_active, model, provider, description)
VALUES (
    'ja_kana_homophone_pick',
    3,
    'You are disambiguating a Japanese word for a dictionary lookup.

A learner tapped on this word inside a sentence: 「{surface}」
Sentence: {sentence}
Reading: {reading}

Below are all known Japanese words with this exact reading. Pick which one the tapped word actually is in this sentence, by number. If none of them are the right word (the tapped word is really something else, not yet in the dictionary), answer 0.

{candidates_numbered}

Respond with a JSON object only, no other text:
{{"choice": <number, or 0 if none fit>, "reason": "<one short sentence in Japanese explaining why>"}}',
    1,
    true,
    'google/gemini-3.5-flash-lite',
    'openrouter',
    'Serve-adjacent judge: given a kana-derived token''s sentence context and every dim_vocabulary row sharing its reading, picks which one (if any) the token actually is. See services/vocabulary/kana_homophone_judge.py::pick_homophone_sense.'
)
ON CONFLICT DO NOTHING;

INSERT INTO prompt_templates (task_name, language_id, template_text, version, is_active, model, provider, description)
VALUES (
    'ja_kana_fragment_check',
    3,
    'You are auditing a Japanese vocabulary database entry for data-quality problems.

Word (as stored): {lemma}
Part of speech (as stored): {pos}

Definitions currently attached to this entry:
{definitions_numbered}

Question: is 「{lemma}」 by itself a genuine, complete, standalone Japanese word — one a dictionary would list on its own? Or is it a mid-word fragment that was mistakenly split out of a longer word or verb form (for example, a sokuon-truncated syllable from a compound, or a stem cut off from a longer conjugation) — and the definitions above actually describe that longer word, not 「{lemma}」 itself?

Respond with a JSON object only, no other text:
{{"is_fragment": true or false, "likely_source_word": "<if is_fragment is true, your best guess at the complete word/compound this was cut from, in kanji if you can; otherwise empty string>", "reason": "<one short sentence in Japanese explaining your judgment>"}}',
    1,
    true,
    'google/gemini-3.5-flash-lite',
    'openrouter',
    'Offline audit judge: classifies an existing kana-only dim_vocabulary row as a real standalone word or a UniDic segmentation fragment. See services/vocabulary/kana_homophone_judge.py::classify_kana_lemma and scripts/audit_kana_fragments.py.'
)
ON CONFLICT DO NOTHING;
