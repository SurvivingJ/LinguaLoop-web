"""Prompt + structured-output schema for the DT single-call grader (ADR-044), v2.

History
-------
v1 (``dt-single-call/p1_expl/2026-11-14``) was a byte-for-byte port of the Track B
``p1_expl`` prompt. v2 (this file) is a NEW prompt, written after owner review of
v1, and the Track B numbers do not transfer to it: it was re-measured on the v6
gold set and the Track E stress set through the production path
(``data/eval/dt_decision_2026-11-14/prod_check/v2/REPORT.md``;
wiki/evaluations/dt-decision-grading-2026-11-14.md section 9). What v2 adds, all in the
same single call:

  * per error: an exact ``learner_quote`` AND the ``reference_quote`` it should
    have been (so the correction is the model's local fragment, not a sentence
    alignment guess), a ``confidence`` (high / medium / low), a ``source``
    (interlingual / intralingual, judged against the learner's L1, which the user
    message names) and an ``explanation`` written in the learner's L1;
  * after the error list: evidence-backed band judgments for ``naturalness`` and
    ``range`` (band 1-4 + a verbatim learner quote), read against the active
    rubric's band descriptors for the passage's age tier - the same descriptors
    and the same "no evidence, no band" rule as the v2 Verifier.

The output order is deliberate: ``errors`` first, the two judgments last, so the
added judgments cannot change what the model has already written for detection.

Any change to a prompt string, the type list, the schema or the request parameters
is a new prompt and must bump ``PROMPT_VERSION`` (written to
``grader_trace.single_call.prompt_version`` and ``dt_grading_call.prompt_version``,
which is what makes a stored grade reproducible without storing the prompt) and
must be re-measured.

Instructions are in English and ask for slugs, not numeric indices (ADR-044 records
the deviation from the L2-only rule of ``services.dual_translation.prompts``).

Error-type list
---------------
``TYPE_DEFINITIONS`` is a literal, per L2: (slug, native name, one-line English
definition, usual severity). It is hardcoded because the definition and native
name are not stored in ``dt_taxonomy_version`` (which has L1/L2 glosses instead).
It must be EXHAUSTIVE: every subtype taxonomy v6 allows for an L2 (``pairs[l2]``
and every directed pair ``<l1>-<l2>``), each with a definition, and nothing else.
``tests/test_dual_translation_single_call_grader.py::TestTypeListExhaustive`` fails
if the literal and ``migrations/dt_taxonomy_v6_seed.sql`` ever diverge (missing or
extra slug per language, wrong order, empty definition, severity hint different
from the taxonomy default). At run time ``single_call_grader`` also refuses to run
(and falls back to the configured flow) when the loaded taxonomy's subtype set for
the pair is not exactly this list.

``FREE_TRANSLATION_PARAGRAPH`` is Track E's mitigation ("free translations are
expected"), appended only when ``Config.DT_SINGLE_CALL_FREE_TRANSLATION`` is on
(default off); it is its own prompt variant in the trace.
"""

from __future__ import annotations

# Bump on ANY change to the strings, type lists, schema or request parameters below.
PROMPT_VERSION = "dt-single-call/v2-quotes-5dim/2026-11-14"

PROMPT_VARIANT_BASE = "v2"
PROMPT_VARIANT_FREE = "v2_mit"

# Temperature 0; strict json_schema response format. v1 used 600 tokens; v2 returns
# two quotes, an L1 explanation and two judgments, so the cap is higher.
MAX_TOKENS = 1400
TEMPERATURE = 0.0

LANG_NAME: dict[str, str] = {
    "en": "English",
    "zh": "Chinese (Mandarin, simplified)",
    "ja": "Japanese",
}

SEVERITIES: tuple[str, ...] = ("minor", "major", "critical")

# Per-error confidence: a small ordinal, mapped to the numeric `confidence` column.
CONFIDENCE_LABELS: tuple[str, ...] = ("high", "medium", "low")
CONFIDENCE_VALUES: dict[str, float] = {"high": 0.9, "medium": 0.6, "low": 0.3}

# = services.dual_translation.prompts.SOURCE_ENUM (pinned equal by test).
SOURCES: tuple[str, ...] = ("interlingual", "intralingual")

# = services.dual_translation.prompts.JUDGE_DIMENSIONS (pinned equal by test).
JUDGED_DIMENSIONS: tuple[str, ...] = ("naturalness", "range")
BANDS: tuple[int, ...] = (1, 2, 3, 4)

SEVERITY_RUBRIC = """Severity (reader-impact, judged as a native reader):
- minor: a small slip a native reader notices but reads straight past (slightly off form or near-synonym).
- major: CLEARLY WRONG to a native reader - an ungrammatical or plainly incorrect form, particle, word or order - EVEN IF the intended meaning is still obvious. "Major" does NOT require a change of meaning.
- critical: the meaning breaks or is reversed, so the reader is misled (e.g. negation flipped, antonym, with -> without)."""

NOT_ERRORS = """NOT errors (never report): true synonyms and equally good rewordings, contractions, kana/kanji or simplified/variant spellings of the same word, optional commas and punctuation, spacing. A learner sentence may differ from the reference and still be correct."""

ERROR_FIELDS = """For each error give:
- sentence: the sentence number.
- learner_quote: the exact offending learner text, copied verbatim from that LRN sentence, as short as possible.
- reference_quote: the exact REF text that learner_quote should have been, copied verbatim from that REF sentence, as short as possible - only the matching words, never the whole sentence. Replacing learner_quote with reference_quote must fix the error, so when a word is missing or extra, include the same neighbouring word in both quotes.
- type: the error type id.
- severity: minor, major or critical.
- confidence: how sure you are that a careful native teacher would mark this as an error rather than accept it as a variant: high (certain), medium (probably), low (it could well be acceptable - such entries are not shown to the learner).
- source: interlingual if the error is best explained by transfer from the learner's first language (L1, named in the user message), otherwise intralingual (a slip or overgeneralisation inside the target language).
- explanation: one sentence for the learner, WRITTEN IN THE LEARNER'S L1, at most 25 words, saying what is wrong here and quoting the learner's words or the correct words exactly."""

# The types whose taxonomy-v6 `subtype_meta.dimension` is "naturalness" (pinned by
# test): the only listed errors that should pull the naturalness band down.
NATURALNESS_TYPES: tuple[str, ...] = ("collocation", "cohesion_connective", "topic_comment")

JUDGMENT_INSTRUCTIONS = """After the error list, judge the learner text as a whole on two dimensions, each with a band from 1 to 4:
- naturalness: does LRN read the way a native speaker would say it? Start from 4. Lower it ONLY for phrasing a native speaker would not use even though it is grammatical: errors you listed above with type {naturalness_types}, or clearly non-native phrasing you did not list. Do NOT lower naturalness for grammar, spelling, missing or extra words, word-form or meaning errors - other dimensions score those. Different wording from REF is not unnatural in itself, and sentences marked SAME are natural.
- range: is the vocabulary and sentence structure of LRN as varied as REF's? Judge against REF only: if LRN did not flatten REF into simpler or repeated forms, range is 4. Errors do not lower range.
For each dimension give the band and `evidence`: one short phrase copied verbatim from an LRN or SAME sentence that best supports the band (for band 4, any phrase that shows natural phrasing / the preserved variety). A judgment without verbatim evidence is discarded."""

FREE_TRANSLATION_PARAGRAPH = """

IMPORTANT - free translations. The learner did NOT see the reference; the learner translated the same source text independently. Different wording, word order, sentence structure, synonyms, more or less explicit phrasing, and small differences of emphasis or tone are EXPECTED and are NOT errors. Judge each LRN sentence on its own: (1) is it correct, natural {lang}? (2) does it convey the same message as REF? Report an error only if you can point to a specific word or form in LRN that is wrong in itself, or to a fact in REF that LRN states differently, reverses or leaves out. Never report "differs from the reference" as an error. When in doubt, do not report."""

# Per-L2 error types: (slug, native name, definition, usual severity), in taxonomy
# v6 order (= pairs[l2].subtypes). EXHAUSTIVE - see the module docstring.
TYPE_DEFINITIONS: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    'en': (
        ('omission', '', 'A required word or element from the source is missing from the translation', 'major'),
        ('addition', '', 'Extra words or information not present in the source (padding, repetition, or an inserted element)', 'minor'),
        ('word_choice', '', 'A wrong or unnatural lexical choice', 'minor'),
        ('collocation', '', "The words are individually correct but do not naturally combine (e.g. 'make a decision', not 'do a decision')", 'minor'),
        ('word_order', '', 'Wrong order in questions or embedded questions, adjective order, or adverb placement between verb and object', 'major'),
        ('register', '', 'Wrong level of formality or tone for the declared register/tier', 'major'),
        ('orthography', '', 'A spelling or capitalisation error where the intended word is clear', 'minor'),
        ('cohesion_connective', '', 'A missing, wrong, or misused linking word (however, therefore, so, but) that weakens how sentences connect', 'minor'),
        ('article_determiner', '', 'A missing, extra, or wrong article/determiner, or a countability clash (an advice, many information)', 'minor'),
        ('preposition', '', 'A wrong preposition for a verb, adjective, noun, location, or time', 'minor'),
        ('verb_form_tense', '', 'A wrong tense/aspect for the time frame, or a wrong irregular/participle form', 'major'),
        ('complementation', '', 'A wrong complement type after a verb: to-infinitive, -ing, bare infinitive, or that-clause', 'minor'),
        ('agreement', '', 'Subject-verb disagreement, including attraction from an intervening noun', 'minor'),
        ('pronoun', '', "Wrong case, a reflexive without a local antecedent, 'which' for a person, a resumptive pronoun, or a pronoun that refers to the wrong antecedent or the wrong number of things ('it' for 'them')", 'major'),
        ('plural_number', '', 'Wrong singular/plural form or countability (a missing -s, or a plural on an uncountable noun)', 'minor'),
        ('phrasal_verb', '', 'Wrong particle or wrong/avoided phrasal-verb form', 'minor'),
        ('lexical_form', '', 'The wrong member of the right word family (success/successful, economic/economical)', 'minor'),
        ('semantic_anomaly', '', 'Grammatical, but the event described is impossible or absurd', 'major'),
        ('contradiction', '', 'Grammatical, but the sentence contradicts itself, or a connective asserts the wrong logical relation (because/although, before/after)', 'major'),
        ('meaning_inversion', '', 'the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit', 'critical'),
    ),
    'zh': (
        ('omission', '成分缺失', 'A required word or element from the source is missing from the translation', 'major'),
        ('addition', '多余添加', 'Extra words or information not present in the source (padding, repetition, or an inserted element)', 'minor'),
        ('word_choice', '词语选择', 'A wrong or unnatural lexical choice', 'minor'),
        ('collocation', '词语搭配', 'The words are individually correct but do not naturally combine (e.g. 骑自行车, not 开自行车)', 'minor'),
        ('word_order', '语序', 'Adverbs, time/place phrases, prepositional phrases, 比-comparatives or other constituents in the wrong position', 'major'),
        ('register', '语域', 'Wrong level of formality or tone for the declared register/tier', 'major'),
        ('orthography', '拼写／书写', 'A spelling, capitalisation, or basic writing-form error where the intended word is clear', 'minor'),
        ('cohesion_connective', '衔接／连接词', "A missing, wrong, or misused linking word that weakens how sentences connect (lexical choice of connective, distinct from `connective`'s paired-structure rule)", 'minor'),
        ('measure_word', '量词短语', 'Wrong or missing classifier in a numeral/demonstrative + classifier + noun phrase, or 们 after a numeral', 'minor'),
        ('aspect_negation', '体标记与否定', 'Misuse of 了/过/着/正在, or 不 vs 没 selection that clashes with the aspect', 'major'),
        ('de_particle', '结构助词“的／地／得”', 'Wrong 的/得/地 choice: any confusion among the three structural particles (的-for-得, 的-for-地, 地-for-的, etc.), or an obligatory 得 missing', 'minor'),
        ('complement', '补语（结果／趋向／可能／程度）', 'Wrong form or position of a resultative, directional, potential or degree complement', 'major'),
        ('ba_bei', '把字句／被字句', '把 with a bare verb, an indefinite object, a non-disposal verb, or a potential complement; or a malformed/missing 被-passive', 'major'),
        ('separable_verb', '离合词', 'An object or aspect marker placed after a separable verb instead of inside it or before it', 'minor'),
        ('coverb', '介词', 'Wrong coverb (对, 给, 跟, 向, 离, 从, 在) or a broken fixed frame (对…来说)', 'minor'),
        ('connective', '关联词搭配', "Mismatched or misplaced paired connectives (虽然…但是, 只要…就, 只有…才, 不但…而且) — a structural pairing rule, distinct from `cohesion_connective`'s lexical-choice sense", 'major'),
        ('topic_comment', '话题—述题结构', "Topic/subject-comment structure used inappropriately, often over-transfer from the learner's L1", 'minor'),
        ('semantic_anomaly', '语义反常', 'Grammatical, but the event described is impossible or absurd (a selectional/role violation) — the translation no longer describes what the source describes', 'major'),
        ('contradiction', '矛盾／逻辑冲突', 'Grammatical, but the sentence contradicts itself: a time clash, a relational impossibility (e.g. kinship order), or a world-knowledge clash within the sentence', 'major'),
        ('meaning_inversion', '语义反转（极性／方向／数量／施受）', 'the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit', 'critical'),
    ),
    'ja': (
        ('omission', '要素の欠落', 'A required word or element from the source is missing from the translation', 'major'),
        ('addition', '余分な追加', 'Extra words or information not present in the source (padding, repetition, or an inserted element)', 'minor'),
        ('word_choice', '語彙選択', 'A wrong or unnatural lexical choice', 'minor'),
        ('collocation', 'コロケーション', 'The words are individually correct but do not naturally combine (e.g. 薬を飲む, not 薬を食べる)', 'minor'),
        ('word_order', '語順', 'Words or phrases arranged in an unnatural or ungrammatical sequence', 'major'),
        ('register', '文体・語調', 'Word-level or stylistic register clashes with the declared register/tier (written vs spoken vocabulary, stiff vs casual expressions, slang)', 'major'),
        ('orthography', '表記・綴り', 'A spelling, okurigana, or basic writing-form error where the intended word is clear', 'minor'),
        ('cohesion_connective', '結束性・接続表現', 'A missing, wrong, or misused linking word (しかし、したがって、だから) that weakens how sentences connect', 'minor'),
        ('wa_ga', '「は」「が」（構造規則）', 'は used where a structural rule requires が: a question-word subject, the subject inside a relative clause, or the subject of a subordinate clause that differs from the main-clause subject', 'major'),
        ('case_particle', '格助詞', 'Wrong case particle (を, に, で, へ, と, から) for the verb or predicate', 'major'),
        ('particle_other', 'その他の助詞', 'Parallel particles (や・と), focus particles (も・だけ・しか), or sentence-final particles used incorrectly', 'minor'),
        ('conjugation', '活用（動詞・形容詞）', 'A wrong inflected form of a verb, i-adjective, or na-adjective, including the wrong verb class (godan treated as ichidan)', 'major'),
        ('tam', 'テンス・アスペクト・モダリティ', 'Wrong tense for the time frame, wrong ている/てある/ておく, relative-tense errors in 前に/後で clauses, or the まだ+negative form', 'major'),
        ('keigo', '敬語・丁寧さ', "Wrong politeness level — plain style (だ, dictionary-form verbs) where the polite style (です/ます) is needed, or the reverse — or honorific (尊敬語) used for the speaker's own/in-group action, or humble (謙譲語) used for someone else's action", 'major'),
        ('counter', '助数詞', 'Wrong counter for the noun, including homophonous counters (軒/件)', 'minor'),
        ('transitivity_voice', '自動詞・他動詞／受身・使役', 'The wrong member of a transitive/intransitive pair, or passive/causative mismatched with its particles', 'major'),
        ('modification', '連体修飾形（い・な・の）', 'Wrong connecting form before a noun (い/な/の), or a modifier that does not precede its head', 'minor'),
        ('clause_linkage', '節の接続', 'Wrong connector or conditional: から/ので/のに, と/たら/ば/なら with a request, ために vs ように', 'major'),
        ('kanji_choice', '漢字の選択（同音異義）', 'The wrong kanji among homophones: a real, correctly written word, but the wrong one for the meaning (計る/測る/量る)', 'minor'),
        ('topic_comment', '主題—解説構造', 'は-based topic presentation used inappropriately', 'minor'),
        ('semantic_anomaly', '意味的な破綻', 'Grammatical, but the event described is impossible or absurd', 'major'),
        ('contradiction', '矛盾・論理の破綻', 'Grammatical, but the sentence contradicts itself: a time clash, a relational impossibility (e.g. kinship order), or a world-knowledge clash within the sentence', 'major'),
        ('meaning_inversion', '意味の反転（極性・方向・数量・動作主）', 'the learner text says the REVERSE of the reference: negation dropped/added, antonym, reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). Judge by effect, whatever the surface edit', 'critical'),
    ),
}

TYPE_IDS: dict[str, tuple[str, ...]] = {
    l2: tuple(row[0] for row in rows) for l2, rows in TYPE_DEFINITIONS.items()
}


def supports(l2_code: str) -> bool:
    """True when a prompt exists for this L2."""
    return l2_code in TYPE_DEFINITIONS


def type_block(l2_code: str) -> str:
    """The rendered error-type lines for one L2."""
    lines = []
    for slug, native, definition, usual in TYPE_DEFINITIONS[l2_code]:
        name = f"{slug} [{native}]" if native else slug
        lines.append(f"- {name}: {definition} (usually {usual})")
    return "\n".join(lines)


def build_system_prompt(
    l2_code: str, *, free_translation: bool = False, band_descriptors: str = "",
) -> str:
    """The system prompt for one L2. Everything up to the band descriptors is
    byte-stable per (l2, variant), so the provider's prefix cache is shared across
    age tiers; ``band_descriptors`` (the active rubric's naturalness/range text for
    the passage's age tier, ``prompts._band_descriptors_text``) comes last. Without
    descriptors the judgments are still asked for, against the definitions above."""
    text = f"""You grade a learner's {LANG_NAME[l2_code]} translation against a reference translation of the same passage. Sentences are paired: REF is the reference, LRN is the learner's version. "SAME" means the learner sentence is identical to the reference.

Find every translation error in the LRN sentences. One entry per distinct error; a sentence can have several. If there are no errors return an empty list.

{NOT_ERRORS}

{ERROR_FIELDS}

Error types (pick exactly one id per error):
{type_block(l2_code)}

{SEVERITY_RUBRIC}
The "(usually ...)" hint is the typical severity for that type; override it when the reader impact differs."""
    if free_translation:
        text += FREE_TRANSLATION_PARAGRAPH.format(lang=LANG_NAME[l2_code])
    natural = [t for t in NATURALNESS_TYPES if t in TYPE_IDS[l2_code]]
    text += "\n\n" + JUDGMENT_INSTRUCTIONS.format(naturalness_types=", ".join(natural))
    if band_descriptors:
        text += "\nBand descriptors:\n" + band_descriptors
    return text


def build_user_prompt(pairs, l1_code: str = "", l2_code: str = "") -> str:
    """The per-submission message: the learner's L1, then numbered sentence pairs
    (1-based), then the L1 instruction again. A sentence identical to its
    reference is shown once as ``S<n> SAME``. ``pairs`` is
    ``sentence_pairs.build_sentence_pairs(...).pairs``.

    The L1 is stated twice on purpose: with it only at the top, the model wrote
    most explanations of Chinese/Japanese errors in Chinese/Japanese (measured on
    gold, 43 of 81) instead of the learner's L1."""
    l1 = LANG_NAME.get(l1_code, l1_code or "the learner's first language")
    l2 = LANG_NAME.get(l2_code, "target-language")
    out = [f"Learner's L1: {l1}."]
    for n, pair in enumerate(pairs, 1):
        ref, lrn = pair.ref.text.strip(), pair.repro.text.strip()
        if ref == lrn:
            out.append(f"S{n} SAME: {ref}")
        else:
            out.append(f"S{n} REF: {ref}\nS{n} LRN: {lrn}")
    out.append(f"Write every explanation in {l1} (the learner's L1), not in the language of the "
               f"passage; quote the {l2} words exactly as written.")
    return "\n".join(out)


def response_schema(l2_code: str) -> dict:
    """The strict ``json_schema`` object sent as ``response_format.json_schema``.
    Property order is the output order: errors, then naturalness, then range."""
    error_props = {
        "sentence": {"type": "integer"},
        "learner_quote": {"type": "string"},
        "reference_quote": {"type": "string"},
        "type": {"type": "string", "enum": list(TYPE_IDS[l2_code])},
        "severity": {"type": "string", "enum": list(SEVERITIES)},
        "confidence": {"type": "string", "enum": list(CONFIDENCE_LABELS)},
        "source": {"type": "string", "enum": list(SOURCES)},
        "explanation": {"type": "string"},
    }
    judgment = {
        "type": "object", "additionalProperties": False, "required": ["band", "evidence"],
        "properties": {
            "band": {"type": "integer", "enum": list(BANDS)},
            "evidence": {"type": "string"},
        },
    }
    props = {
        "errors": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": list(error_props), "properties": error_props}},
    }
    for dim in JUDGED_DIMENSIONS:
        props[dim] = judgment
    return {"name": "dt_grade", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "required": list(props), "properties": props}}


def prompt_variant(free_translation: bool) -> str:
    return PROMPT_VARIANT_FREE if free_translation else PROMPT_VARIANT_BASE
