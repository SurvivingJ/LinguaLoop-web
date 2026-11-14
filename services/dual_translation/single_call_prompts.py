"""Frozen prompt + structured-output schema for the DT single-call grader (ADR-044).

This is a faithful port of the Track B ``p1_expl`` ("span + explanation") variant
that the 2026-11-14 experiment validated on the v6 gold set
(``data/eval/dt_decision_2026-11-14/track_b/common.py`` — ``system_p1(lang, "expl")``,
``user_p1``, ``schema(lang, "p1_expl")``; report:
wiki/evaluations/dt-decision-grading-2026-11-14.md §4.2). The numbers in that report
belong to THIS wording, so the text below is not to be "improved" in place: any
change to a prompt string, the type list, the schema or the request parameters is a
new prompt and must bump ``PROMPT_VERSION`` (it is written to
``grader_trace.single_call.prompt_version`` and to ``dt_grading_call.prompt_version``,
which is what makes a stored grade reproducible without storing the prompt).

Unlike every other prompt in ``services.dual_translation.prompts`` these
instructions are in English and ask for slugs, not numeric indices — that is the
validated design (ADR-044 records the deviation from the L2-only rule).

Why the type list is a literal here and not built from ``dt_taxonomy_version``:
the validated type lines carry a one-line English definition and a native name that
come from ``data/eval/taxonomy_merge_2026-09-27/merged_taxonomy.json`` and are NOT
stored in the taxonomy row (which has L1/L2 glosses instead). The slugs, their order
and the "(usually <severity>)" hints equal taxonomy v6's ``pairs[l2].subtypes`` /
``subtype_meta[*].default_severity``; ``single_call_grader`` refuses to run (and
falls back to the configured flow) when the active taxonomy does not contain every
slug below, so the literal can never grade under a taxonomy it does not match.
``tests/test_dual_translation_single_call_grader.py`` pins the rendered prompt and
schema byte-for-byte against the Track B harness.

``FREE_TRANSLATION_PARAGRAPH`` is Track E's mitigation ("free translations are
expected"), appended only when ``Config.DT_SINGLE_CALL_FREE_TRANSLATION`` is on
(default off): it removed false flags on rephrased sentences and lowered recall on
near-verbatim answers (gpt-6-luna .88 -> .80), so it is a product decision, and it is
its own prompt variant (``PROMPT_VARIANT_FREE``) in the trace.
"""

from __future__ import annotations

# Bump on ANY change to the strings, type lists, schema or request parameters below.
PROMPT_VERSION = "dt-single-call/p1_expl/2026-11-14"

PROMPT_VARIANT_BASE = "p1_expl"
PROMPT_VARIANT_FREE = "p1_expl_mit"

# Track B MAX_TOKENS["p1_expl"]; temperature 0; strict json_schema response format.
MAX_TOKENS = 600
TEMPERATURE = 0.0

LANG_NAME: dict[str, str] = {
    "en": "English",
    "zh": "Chinese (Mandarin, simplified)",
    "ja": "Japanese",
}

SEVERITIES: tuple[str, ...] = ("minor", "major", "critical")

SEVERITY_RUBRIC = """Severity (reader-impact, judged as a native reader):
- minor: a small slip a native reader notices but reads straight past (slightly off form or near-synonym).
- major: CLEARLY WRONG to a native reader - an ungrammatical or plainly incorrect form, particle, word or order - EVEN IF the intended meaning is still obvious. "Major" does NOT require a change of meaning.
- critical: the meaning breaks or is reversed, so the reader is misled (e.g. negation flipped, antonym, with -> without)."""

NOT_ERRORS = """NOT errors (never report): true synonyms and equally good rewordings, contractions, kana/kanji or simplified/variant spellings of the same word, optional commas and punctuation, spacing. A learner sentence may differ from the reference and still be correct."""

_FIELDS = "the sentence number, the exact offending learner text (copied verbatim from LRN, as short as possible), the error type, the severity and an explanation for the learner, in English, of at most 15 words"

FREE_TRANSLATION_PARAGRAPH = """

IMPORTANT - free translations. The learner did NOT see the reference; the learner translated the same source text independently. Different wording, word order, sentence structure, synonyms, more or less explicit phrasing, and small differences of emphasis or tone are EXPECTED and are NOT errors. Judge each LRN sentence on its own: (1) is it correct, natural {lang}? (2) does it convey the same message as REF? Report an error only if you can point to a specific word or form in LRN that is wrong in itself, or to a fact in REF that LRN states differently, reverses or leaves out. Never report "differs from the reference" as an error. When in doubt, do not report."""

# Per-L2 error types, in the validated order (= taxonomy v6 pairs[l2].subtypes).
FROZEN_TYPE_IDS: dict[str, tuple[str, ...]] = {
    'en': (
        'omission',
        'addition',
        'word_choice',
        'collocation',
        'word_order',
        'register',
        'orthography',
        'cohesion_connective',
        'article_determiner',
        'preposition',
        'verb_form_tense',
        'complementation',
        'agreement',
        'pronoun',
        'plural_number',
        'phrasal_verb',
        'lexical_form',
        'semantic_anomaly',
        'contradiction',
        'meaning_inversion',
    ),
    'zh': (
        'omission',
        'addition',
        'word_choice',
        'collocation',
        'word_order',
        'register',
        'orthography',
        'cohesion_connective',
        'measure_word',
        'aspect_negation',
        'de_particle',
        'complement',
        'ba_bei',
        'separable_verb',
        'coverb',
        'connective',
        'topic_comment',
        'semantic_anomaly',
        'contradiction',
        'meaning_inversion',
    ),
    'ja': (
        'omission',
        'addition',
        'word_choice',
        'collocation',
        'word_order',
        'register',
        'orthography',
        'cohesion_connective',
        'wa_ga',
        'case_particle',
        'particle_other',
        'conjugation',
        'tam',
        'keigo',
        'counter',
        'transitivity_voice',
        'modification',
        'clause_linkage',
        'kanji_choice',
        'topic_comment',
        'semantic_anomaly',
        'contradiction',
        'meaning_inversion',
    ),
}

_TYPE_BLOCKS: dict[str, str] = {
    'en': """- omission: A required word or element from the source is missing from the translation (usually major)
- addition: Extra words or information not present in the source (padding, repetition, or an inserted element) (usually minor)
- word_choice: A wrong or unnatural lexical choice (usually minor)
- collocation: The words are individually correct but do not naturally combine (e.g. 'make a decision', not 'do a decision') (usually minor)
- word_order: Wrong order in questions or embedded questions, adjective order, or adverb placement between verb and object (usually major)
- register: Wrong level of formality or tone for the declared register/tier (usually major)
- orthography: A spelling or capitalisation error where the intended word is clear (usually minor)
- cohesion_connective: A missing, wrong, or misused linking word (however, therefore, so, but) that weakens how sentences connect (usually minor)
- article_determiner: A missing, extra, or wrong article/determiner, or a countability clash (an advice, many information) (usually minor)
- preposition: A wrong preposition for a verb, adjective, noun, location, or time (usually minor)
- verb_form_tense: A wrong tense/aspect for the time frame, or a wrong irregular/participle form (usually major)
- complementation: A wrong complement type after a verb: to-infinitive, -ing, bare infinitive, or that-clause (usually minor)
- agreement: Subject-verb disagreement, including attraction from an intervening noun (usually minor)
- pronoun: Wrong case, a reflexive without a local antecedent, 'which' for a person, a resumptive pronoun, or a pronoun that refers to the wrong antecedent or the wrong number of things ('it' for 'them') (usually major)
- plural_number: Wrong singular/plural form or countability (a missing -s, or a plural on an uncountable noun) (usually minor)
- phrasal_verb: Wrong particle or wrong/avoided phrasal-verb form (usually minor)
- lexical_form: The wrong member of the right word family (success/successful, economic/economical) (usually minor)
- semantic_anomaly: Grammatical, but the event described is impossible or absurd (usually major)
- contradiction: Grammatical, but the sentence contradicts itself, or a connective asserts the wrong logical relation (because/although, before/after) (usually major)
- meaning_inversion: the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit (usually critical)""",
    'zh': """- omission [成分缺失]: A required word or element from the source is missing from the translation (usually major)
- addition [多余添加]: Extra words or information not present in the source (padding, repetition, or an inserted element) (usually minor)
- word_choice [词语选择]: A wrong or unnatural lexical choice (usually minor)
- collocation [词语搭配]: The words are individually correct but do not naturally combine (e.g. 骑自行车, not 开自行车) (usually minor)
- word_order [语序]: Adverbs, time/place phrases, prepositional phrases, 比-comparatives or other constituents in the wrong position (usually major)
- register [语域]: Wrong level of formality or tone for the declared register/tier (usually major)
- orthography [拼写／书写]: A spelling, capitalisation, or basic writing-form error where the intended word is clear (usually minor)
- cohesion_connective [衔接／连接词]: A missing, wrong, or misused linking word that weakens how sentences connect (lexical choice of connective, distinct from `connective`'s paired-structure rule) (usually minor)
- measure_word [量词短语]: Wrong or missing classifier in a numeral/demonstrative + classifier + noun phrase, or 们 after a numeral (usually minor)
- aspect_negation [体标记与否定]: Misuse of 了/过/着/正在, or 不 vs 没 selection that clashes with the aspect (usually major)
- de_particle [结构助词“的／地／得”]: Wrong 的/得/地 choice: any confusion among the three structural particles (的-for-得, 的-for-地, 地-for-的, etc.), or an obligatory 得 missing (usually minor)
- complement [补语（结果／趋向／可能／程度）]: Wrong form or position of a resultative, directional, potential or degree complement (usually major)
- ba_bei [把字句／被字句]: 把 with a bare verb, an indefinite object, a non-disposal verb, or a potential complement; or a malformed/missing 被-passive (usually major)
- separable_verb [离合词]: An object or aspect marker placed after a separable verb instead of inside it or before it (usually minor)
- coverb [介词]: Wrong coverb (对, 给, 跟, 向, 离, 从, 在) or a broken fixed frame (对…来说) (usually minor)
- connective [关联词搭配]: Mismatched or misplaced paired connectives (虽然…但是, 只要…就, 只有…才, 不但…而且) — a structural pairing rule, distinct from `cohesion_connective`'s lexical-choice sense (usually major)
- topic_comment [话题—述题结构]: Topic/subject-comment structure used inappropriately, often over-transfer from the learner's L1 (usually minor)
- semantic_anomaly [语义反常]: Grammatical, but the event described is impossible or absurd (a selectional/role violation) — the translation no longer describes what the source describes (usually major)
- contradiction [矛盾／逻辑冲突]: Grammatical, but the sentence contradicts itself: a time clash, a relational impossibility (e.g. kinship order), or a world-knowledge clash within the sentence (usually major)
- meaning_inversion [语义反转（极性／方向／数量／施受）]: the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit (usually critical)""",
    'ja': """- omission [要素の欠落]: A required word or element from the source is missing from the translation (usually major)
- addition [余分な追加]: Extra words or information not present in the source (padding, repetition, or an inserted element) (usually minor)
- word_choice [語彙選択]: A wrong or unnatural lexical choice (usually minor)
- collocation [コロケーション]: The words are individually correct but do not naturally combine (e.g. 薬を飲む, not 薬を食べる) (usually minor)
- word_order [語順]: Words or phrases arranged in an unnatural or ungrammatical sequence (usually major)
- register [文体・語調]: Word-level or stylistic register clashes with the declared register/tier (written vs spoken vocabulary, stiff vs casual expressions, slang) (usually major)
- orthography [表記・綴り]: A spelling, okurigana, or basic writing-form error where the intended word is clear (usually minor)
- cohesion_connective [結束性・接続表現]: A missing, wrong, or misused linking word (しかし、したがって、だから) that weakens how sentences connect (usually minor)
- wa_ga [「は」「が」（構造規則）]: は used where a structural rule requires が: a question-word subject, the subject inside a relative clause, or the subject of a subordinate clause that differs from the main-clause subject (usually major)
- case_particle [格助詞]: Wrong case particle (を, に, で, へ, と, から) for the verb or predicate (usually major)
- particle_other [その他の助詞]: Parallel particles (や・と), focus particles (も・だけ・しか), or sentence-final particles used incorrectly (usually minor)
- conjugation [活用（動詞・形容詞）]: A wrong inflected form of a verb, i-adjective, or na-adjective, including the wrong verb class (godan treated as ichidan) (usually major)
- tam [テンス・アスペクト・モダリティ]: Wrong tense for the time frame, wrong ている/てある/ておく, relative-tense errors in 前に/後で clauses, or the まだ+negative form (usually major)
- keigo [敬語・丁寧さ]: Wrong politeness level — plain style (だ, dictionary-form verbs) where the polite style (です/ます) is needed, or the reverse — or honorific (尊敬語) used for the speaker's own/in-group action, or humble (謙譲語 (usually major)
- counter [助数詞]: Wrong counter for the noun, including homophonous counters (軒/件) (usually minor)
- transitivity_voice [自動詞・他動詞／受身・使役]: The wrong member of a transitive/intransitive pair, or passive/causative mismatched with its particles (usually major)
- modification [連体修飾形（い・な・の）]: Wrong connecting form before a noun (い/な/の), or a modifier that does not precede its head (usually minor)
- clause_linkage [節の接続]: Wrong connector or conditional: から/ので/のに, と/たら/ば/なら with a request, ために vs ように (usually major)
- kanji_choice [漢字の選択（同音異義）]: The wrong kanji among homophones: a real, correctly written word, but the wrong one for the meaning (計る/測る/量る) (usually minor)
- topic_comment [主題—解説構造]: は-based topic presentation used inappropriately (usually minor)
- semantic_anomaly [意味的な破綻]: Grammatical, but the event described is impossible or absurd (usually major)
- contradiction [矛盾・論理の破綻]: Grammatical, but the sentence contradicts itself: a time clash, a relational impossibility (e.g. kinship order), or a world-knowledge clash within the sentence (usually major)
- meaning_inversion [意味の反転（極性・方向・数量・動作主）]: the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit (usually critical)""",
}


def supports(l2_code: str) -> bool:
    """True when a frozen prompt exists for this L2."""
    return l2_code in _TYPE_BLOCKS


def build_system_prompt(l2_code: str, *, free_translation: bool = False) -> str:
    """The cacheable system prompt for one L2 (byte-stable per (l2, variant))."""
    text = f"""You grade a learner's {LANG_NAME[l2_code]} translation against a reference translation of the same passage. Sentences are paired: REF is the reference, LRN is the learner's version. "SAME" means the learner sentence is identical to the reference.

Find every translation error in the LRN sentences. For each error give {_FIELDS}. One entry per distinct error; a sentence can have several. If there are no errors return an empty list.

{NOT_ERRORS}

Error types (pick exactly one id per error):
{_TYPE_BLOCKS[l2_code]}

{SEVERITY_RUBRIC}
The "(usually ...)" hint is the typical severity for that type; override it when the reader impact differs."""
    if free_translation:
        text += FREE_TRANSLATION_PARAGRAPH.format(lang=LANG_NAME[l2_code])
    return text


def build_user_prompt(pairs) -> str:
    """The per-submission suffix: numbered sentence pairs (1-based). A sentence
    identical to its reference is shown once as ``S<n> SAME``. ``pairs`` is the
    ``sentence_pairs.build_sentence_pairs(reference, reproduction).pairs`` list."""
    out = []
    for n, pair in enumerate(pairs, 1):
        ref, lrn = pair.ref.text.strip(), pair.repro.text.strip()
        if ref == lrn:
            out.append(f"S{n} SAME: {ref}")
        else:
            out.append(f"S{n} REF: {ref}\nS{n} LRN: {lrn}")
    return "\n".join(out)


def response_schema(l2_code: str) -> dict:
    """The strict ``json_schema`` object sent as ``response_format.json_schema``."""
    props = {
        "sentence": {"type": "integer"},
        "span": {"type": "string"},
        "type": {"type": "string", "enum": list(FROZEN_TYPE_IDS[l2_code])},
        "severity": {"type": "string", "enum": list(SEVERITIES)},
        "explanation": {"type": "string"},
    }
    return {"name": "dt_decisions", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["errors"],
        "properties": {"errors": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": list(props), "properties": props}}}}}


def prompt_variant(free_translation: bool) -> str:
    return PROMPT_VARIANT_FREE if free_translation else PROMPT_VARIANT_BASE
