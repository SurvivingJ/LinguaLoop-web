"""
FAT SEED prompt text, per language, plus the two-call split (variant b) and
the ~10-call fan-out control's prompt set (variant c).

Designed for structured JSON output (a real call would use response_format=
json_schema / tool-calling against the FatSeed shape in seed_schema.py).
Token counts are estimated with the SAME len(text)//4 heuristic
lab/mock_llm.py uses (`_estimate_tokens`), for direct comparability with the
harness's own accounting -- not a real tokenizer, order-of-magnitude only
(see mock_llm.py's own FIDELITY GAP docstring).
"""
from __future__ import annotations

_LANG_NAME = {1: "Mandarin Chinese", 2: "English", 3: "Japanese"}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_fat_seed_prompt(lemma: str, language_id: int, pos_hint: str | None = None) -> str:
    """The ONE-CALL variant's full prompt (variant a)."""
    lang = _LANG_NAME.get(language_id, "the target language")
    zh_en_l1_note = (
        "6. l1_audio_confusables: exactly 3 REAL words in this language that are "
        "audio-confusable with the target word (differ by one phoneme/tone/mora), "
        "each with a one-sentence explanation of the confusion. Required for "
        "Chinese and English only -- Japanese never needs this field, its L1 is "
        "served by a separate deterministic phonetic-trie lookup."
        if language_id in (1, 2) else
        "6. l1_audio_confusables: OMIT this field. Japanese L1 phonetic-recognition "
        "distractors are produced by a deterministic mora-trie lookup elsewhere, "
        "not by this seed."
    )
    return f"""You are generating the complete exercise-authoring seed for ONE
vocabulary sense in {lang}. Target word: "{lemma}"{f' (expected part of speech: {pos_hint})' if pos_hint else ''}.

Return ONE JSON object with ALL of the following fields. This single response
replaces what used to be 8-14 separate calls (core definition, per-level
exercise content, per-level judges) -- you must author BOTH the correct
content AND the deliberately WRONG content for every level below, because no
downstream step will invent wrong content for you and no synchronous judge
will check your work before it ships as provisional (unpublished) content.
Quality matters precisely because nothing else will catch a mistake before an
asynchronous review pass runs.

1. definition_simple, definition_standard: two definitions of this sense, in
   {lang}-native/appropriate register, or your working language if source-language
   definitions are not requested.
2. pos: this language's own part-of-speech label for the word.
3. semantic_class: ONE of concrete | abstract | action | property | function | proper.
4. sentences: EXACTLY 10 example sentences using "{lemma}" as a whole word, each
   tagged with a difficulty tier T1 (easiest) through T6 (hardest), spanning a
   spread of tiers, not all the same one. This is not negotiable down to 3 --
   the ladder's own sentence-assignment contract needs distinct sentences for
   levels 3/4/5/6/7/9 in TWO non-overlapping variants, with headroom for
   review-time attrition.
5. morphological_forms: if this word inflects/derives in {lang}, list at least
   2 real forms with labels (e.g. past_tense, plural, comparative). If the word
   is invariant, return an empty list -- do not pad with fake entries.
   morphology_wrong_forms: for EACH morphological_forms entry, 3 INVENTED WRONG
   inflected forms a learner might plausibly produce by mistake, each with a
   one-sentence explanation of the error.
{zh_en_l1_note}
7. primary_collocate: the single most natural fixed collocate of this word (or
   null if none exists / not applicable in this language). collocation_distractors:
   3 words that are semantically related to the target but are NOT genuine
   collocates, each with a one-sentence explanation of why not.
   collocation_wrong_collocate: ONE additional word that looks like it could
   collocate but does not, for a "spot and repair" exercise.
8. cloze_distractors: 3 wrong words for a fill-in-the-blank exercise built on
   one of your sentences, each with a one-sentence reason it's wrong (wrong
   sense, wrong register, or trivially unrelated -- vary the reasons).
9. discrimination_wrong_sentences: 3 sentences using "{lemma}" that are WRONG
   for a SPECIFIC, stated linguistic reason each (e.g. wrong argument
   structure, wrong register, wrong collocate) -- not just "different" from a
   correct sentence, genuinely and describably wrong.
10. spot_incorrect: ONE sentence with a single planted error, plus a one-
    sentence error_description and the corrected version.
11. word_family_forms: real derived forms in other parts of speech (if
    applicable). word_family_fake_forms: 3 INVENTED, plausible-LOOKING but
    non-existent derived forms (a learner should not immediately recognize
    them as fake).
12. syn_ant_candidates: up to 4 candidates, each tagged synonym or antonym,
    anchored to THIS SPECIFIC SENSE's meaning (not just the bare lemma --
    a polysemous word's synonym for one sense can be wrong for another).
13. particle_candidates: Japanese only -- for one of your sentences, list the
    3-4 particles a learner might choose, marking exactly one correct, each
    with a one-sentence explanation.

Output strict JSON matching this field list. No prose outside the JSON object."""


def build_correct_content_prompt(lemma: str, language_id: int, pos_hint: str | None = None) -> str:
    """Variant (b), call 1 of 2: correct content only."""
    lang = _LANG_NAME.get(language_id, "the target language")
    return f"""Generate the CORRECT-content half of a vocabulary exercise seed for
"{lemma}" in {lang}{f' ({pos_hint})' if pos_hint else ''}. Return JSON with:
definition_simple, definition_standard, pos, semantic_class, 10 tier-tagged
example sentences (T1-T6 spread), morphological_forms (>=2 real forms if the
word inflects), primary_collocate (or null), word_family_forms (real derived
forms), syn_ant_candidates (synonyms/antonyms anchored to this specific
sense). Do not invent any wrong/incorrect content -- that is generated by a
separate call. Strict JSON, no prose outside it."""


def build_wrong_content_prompt(lemma: str, language_id: int, pos_hint: str | None = None) -> str:
    """Variant (b), call 2 of 2: wrong content only. Runs IN PARALLEL with
    build_correct_content_prompt -- this call does not see that call's output,
    so it must re-state enough about the word to generate plausible wrong
    content without depending on the sibling call's specific sentence text."""
    lang = _LANG_NAME.get(language_id, "the target language")
    l1_line = (
        "l1_audio_confusables (3 real audio-confusable words + explanations)"
        if language_id in (1, 2) else
        "(omit l1_audio_confusables -- Japanese L1 uses a deterministic trie)"
    )
    return f"""Generate the WRONG-content half of a vocabulary exercise seed for
"{lemma}" in {lang}{f' ({pos_hint})' if pos_hint else ''}. A separate call is
generating the correct definition/sentences/collocate independently -- assume
generic sentence contexts. Return JSON with: morphology_wrong_forms (3
invented wrong inflections + explanations, if applicable), {l1_line},
collocation_distractors (3 non-collocates + explanations),
collocation_wrong_collocate (1 planted wrong collocate), cloze_distractors (3
wrong cloze options + reasons), discrimination_wrong_sentences (3 sentences
wrong for a specific stated reason each), spot_incorrect (1 sentence + planted
error + error_description + corrected version), word_family_fake_forms (3
invented plausible-looking non-words), particle_candidates (Japanese only: 3-4
particle options for a generic sentence with this word, one correct). Strict
JSON, no prose outside it."""


# ---------------------------------------------------------------------------
# Variant (c): the ~10-call fan-out CONTROL baseline's prompt set. Mirrors
# today's real architecture (recon-generation.md §2-4): 1 sequential P1 core
# call, then up to 10 concurrent P2/P3/L4/L8/typed calls, PLUS 1 sequential
# P1-sentence judge call. This is what the fat seed is being compared against.
# ---------------------------------------------------------------------------

def build_legacy_p1_prompt(lemma: str, language_id: int) -> str:
    lang = _LANG_NAME.get(language_id, "the target language")
    return (f"[P1 core] Generate definition, POS, semantic_class, pronunciation, "
            f"10 example sentences, primary_collocate, and morphological_forms for "
            f'"{lemma}" in {lang}. Strict JSON.')


def build_legacy_p1_judge_prompt(lemma: str, language_id: int) -> str:
    return (f"[P1 sentence judge] For each of 10 example sentences for \"{lemma}\", "
            f"verdict accept/flag/reject on sense fit, register, and whole-word usage.")


def build_legacy_fanout_prompts(lemma: str, language_id: int) -> list[str]:
    """The up-to-10 concurrent P2/P3/L4/L8/typed calls, 2 variants (A/B) each.
    Returned as a flat list; the caller times this batch as max(latency), not
    sum, mirroring asset_pipeline.py's BatchModeThreadPoolExecutor(max_workers=12)."""
    stages = [
        "P2 exercises (L1/L3/L5/L6 option content)",
        "P3 transforms (L7)",
        "L4 morphology (own prompt since TASK-520)",
        "L8 collocation repair (own prompt since TASK-520)",
        "typed: synonym_antonym_match",
        "typed: word_family",
    ]
    if language_id == 3:
        stages.append("typed: particle_selection (JA only)")
    prompts = []
    for variant in ("A", "B"):
        for stage in stages:
            prompts.append(f'[{stage}, variant {variant}] for "{lemma}".')
    return prompts
