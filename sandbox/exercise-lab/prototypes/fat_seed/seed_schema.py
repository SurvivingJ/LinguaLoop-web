"""
The FAT SEED schema — one structured LLM response per sense that carries
BOTH correct content and invented wrong content for every ladder level that
needs it.

WHY THIS EXISTS (read `docs/redteam-generation.md` and `docs/design-01-generation.md`
first — this module is the orchestrator's answer to both)
----------------------------------------------------------------------------
`design-01-generation.md`'s G1 ("seed-and-render") proposed a thin seed
(definition + 3 sentences + collocations + a morphology "note") and tried to
derive WRONG content — L1 audio-confusables, L3/L5/L8 distractors, L6/L7
crafted-wrong sentences, word_family fake words, particle foils — from a
cosine-similarity band over sense embeddings. `redteam-generation.md` axis 2
and axis 3 killed that: cosine similarity is a SEMANTIC-adjacency signal, and
none of L1 (phonetic), L5/L8 (collocational), L6/L7 (labelled-wrong-for-a-
specific-reason), or word_family (invented non-words) are semantic-adjacency
problems. No embedding, however well-tuned, tells you a word is *audio*-
confusable, or that a fake word *looks* morphologically real, or that a
sentence is wrong for pedagogical reason X rather than merely "different".

The orchestrator's response (this module) is not to try harder with cosine —
it is to stop asking a distance metric to author content, and have the ONE
LLM call that already runs per sense also author the wrong content directly.
Ten wrong things authored in one JSON response is cheap; the redteam's own
axis-5 latency analysis says the round trip is what costs 5.5 minutes, not
token volume. This resolves the *existence* half of redteam objection #3 (a
correctly-sized seed the ladder's own contract, `P1_MIN_ACCEPTABLE_SENTENCES`
= 6 sentences post-attrition, `config.py:202`, needs 8-10 asked-for to survive
any attrition at all — not G1's 3). It does **not** resolve the *correctness*
half of objections #1/#4/#7: nothing here verifies that an LLM-invented
"audio confusable" is actually audio-confusable, or that a "wrong for reason
X" sentence is actually wrong for reason X and not accidentally also-correct.
That verification gap is Phase B's job (`pipeline.py`), and Phase B is
asynchronous — see `docs/results-fat-seed.md` for the honest accounting of
what that trade costs.

Every field below is documented with (a) which ladder level(s)/typed type(s)
consume it, (b) which real production module/gate reads an equivalently-named
field today (so `render.py` can map it 1:1), and (c) what is NOT covered.

Levels this seed explicitly CANNOT serve, stated up front rather than left to
be discovered: `classifier_match`, `counter_match`, `hanzi_to_pinyin`,
`pinyin_to_hanzi`, `kanji_to_reading`, `reading_to_kanji`. These are already
zero-LLM in production (`services/vocabulary_ladder/deterministic/{classifier_match,
counter_match,readings}.py`) and gated on a classifier/counter dictionary or a
same-tier lexicon distractor pool read from the database — orthogonal to what
an LLM seed can or should provide, and out of scope for this prototype (that
is `design-01-generation.md`'s G2, not G1/this FAT SEED design). See
`docs/results-fat-seed.md`'s capability matrix for the explicit RED/AMBER
verdict on each.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Read-only imports of REAL production constants/functions. Verified safe to
# import (no DB/network touched at import time or by these specific pure
# functions) by direct test before writing this file — see the session's
# `venv/Scripts/python -c "from services.vocabulary_ladder.config import ..."`
# smoke check. This is exactly the "call/adapt the real renderer... import
# read-only" instruction: gating on the SAME normalize_semantic_class /
# LANGUAGE_VALIDATION_PROFILES / P1_MIN_ACCEPTABLE_SENTENCES the real pipeline
# gates on means a seed that passes this validator would also pass
# `VocabAssetValidator.validate_prompt1`'s structural checks (not its judge
# calls, which this prototype does not have and does not fake).
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.vocabulary_ladder.config import (  # noqa: E402
    LANGUAGE_VALIDATION_PROFILES,
    SEMANTIC_CLASSES,
    normalize_semantic_class,
)
from services.vocabulary_ladder.validators import contains_target_whole_word  # noqa: E402
from config import Config  # noqa: E402  (root config.py — VOCAB_SENTENCES_PER_WORD lives here)

# The real floor. redteam-generation.md issue #1: G1's 3-sentence seed was
# ~3x under this AFTER attrition, i.e. before any judge/tier-gate even runs.
# This prototype asks for VOCAB_SENTENCES_PER_WORD (10) up front, same as
# production's P1 prompt, specifically so the fat seed does not repeat that
# mistake. See ASK_SENTENCE_COUNT below.
P1_MIN_ACCEPTABLE_SENTENCES = 6  # mirrors services/vocabulary_ladder/config.py:202
ASK_SENTENCE_COUNT = Config.VOCAB_SENTENCES_PER_WORD  # 10, mirrors production's own ask

# ---------------------------------------------------------------------------
# Sub-shapes
# ---------------------------------------------------------------------------


@dataclass
class SeedSentence:
    """One tier-graded example sentence.

    Consumed by: L3 cloze (blank at target_word), L4 morphology_slot (blank +
    inflect target_word), L5/L8 collocation (when `contains_collocate`), L6
    semantic_discrimination (the ONE correct sentence), L7 spot_incorrect
    (the 2-3 correct sentences shown alongside the seed's crafted-wrong one),
    L9 jumbled_sentence (chunked via the REAL `deterministic/jumbled.py`).

    Mirrors `word_assets.prompt1_core.sentences[i]` exactly
    (`target_word`/`text`/`tier` — see `config.get_sentence_target`, which
    also accepts the legacy `target_substring` key for old rows; this
    prototype only ever writes `target_word`, never the legacy alias).
    """

    index: int
    text: str
    target_word: str
    tier: str  # 'T1'..'T6', per services/vocabulary_ladder/tier_gate.py
    sentence_source: str = "generated"  # 'generated' | 'mined' (SENTENCE_SOURCE_* in config.py)
    contains_collocate: bool = False


@dataclass
class MorphologicalForm:
    """One real inflected/derived form. Consumed by: the `morphological_forms`
    capability gate (`morph_forms>=2`, `config.py:481-483,508`) for
    `morphology_slot` (L4, EN/JA action|property) and `word_family` (EN,
    abstract|action|property) — both read `len(core_asset.get(
    'morphological_forms'))` as a COUNTABLE LIST, per
    `capability_context_from_core` (config.py:694-711) and
    redteam-generation.md issue #7. This dataclass IS that countable list
    element — "a morphology note" (G1's mistake) cannot satisfy this gate
    without a parser; a `list[MorphologicalForm]` needs none.
    """

    form: str
    label: str  # e.g. 'past_tense', 'plural', 'comparative', '连用形'


@dataclass
class WrongForm:
    """One invented WRONG inflected form for L4's distractor options.
    Consumed by: L4 `morphology_slot` options (3 of these + 1 correct
    `MorphologicalForm.form`, mirrors `exercise_renderer._render_morphology_slot`'s
    `options_data` / `correct_form` / `explanations` shape).
    """

    text: str
    explanation: str  # why this form is wrong, shown to the learner on miss


@dataclass
class LabelledDistractor:
    """A wrong option with a stated reason. Consumed by: L3 cloze (wrong-word
    distractors), L5 collocation_gap_fill (non-collocate distractors), L1
    zh/en audio-confusables. Mirrors the `{text, is_correct, explanation}`
    option shape `validators._validate_option_level` checks (every option,
    correct or not, needs a non-empty `explanation` — see validators.py:232-236)."""

    text: str
    explanation: str


@dataclass
class LabelledWrongSentence:
    """A sentence invented to be wrong for a SPECIFIC, stated reason.
    Consumed by: L6 `semantic_discrimination` (3 of these + 1 correct
    sentence), L7 `spot_incorrect_sentence` (exactly 1, paired with
    `error_description`, mirrors `validators._validate_level_7` and
    `exercise_renderer._render_spot_incorrect`'s `incorrect_sentence`/
    `error_description` fields). `corrected_sentence` is carried because
    `redteam-generation.md` issue 3's L7 row cites it as consumed downstream;
    the two production sites this prototype actually read
    (`exercise_renderer.py:916-977`, `validators.py:267-278`) only require
    `error_description` — `corrected_sentence` is written defensively as
    optional extra metadata, not asserted as a hard requirement, since this
    prototype could not independently confirm a consumer for it.
    """

    text: str
    reason: str
    corrected_sentence: Optional[str] = None


@dataclass
class SynAntCandidate:
    """One synonym/antonym foil anchored to THIS sense's definition (not the
    lemma) — `redteam-generation.md`'s "bank/shore" polysemy warning
    (`services/exercise_generation/judges/relation.py:8-16`). Consumed by:
    typed `synonym_antonym_match`. `relation` in {'synonym','antonym'}.
    Verdict: PARTIAL per the redteam's own axis-3 table — foil *sourcing* is
    exactly what an LLM seed can do; final adjudication that a candidate is
    genuinely NOT synonymous with *this* sense (not just the lemma) is what
    the (now-absent, Phase-A) judge used to do. This prototype does not
    pretend to have solved that; see the capability matrix.
    """

    text: str
    relation: str
    note: str = ""


@dataclass
class WordFamilyForm:
    """A REAL derived form for `word_family`'s correct answer, e.g.
    {"decision", "noun"} for base "decide". Consumed by: typed `word_family`."""

    text: str
    label: str  # 'noun' | 'verb' | 'adjective' | ...


@dataclass
class WordFamilyFakeForm:
    """An INVENTED, plausible-looking non-word for `word_family`'s
    distractors, e.g. "decisionment". Consumed by: typed `word_family`
    distractor options. `design-01-generation.md`'s own risk list: "A
    dictionary can veto a real word; nothing can generate a plausible fake
    one deterministically" — this is the fat seed's answer (an LLM invents
    it), and `render.py`'s validator adds the ONE deterministic check that
    IS possible on top of it: veto any "fake" word that turns out to be a
    real word via `wordfreq.zipf_frequency` (catches the accidental-real-word
    failure mode; cannot catch the harder "does this look plausible" failure
    mode — see the capability matrix's AMBER, not GREEN, verdict).
    """

    text: str
    explanation: str


@dataclass
class ParticleCandidate:
    """One particle option for JA `particle_selection`.
    `design-01-generation.md`'s Risks section names this the one type it
    could not cover at all ("no particle-frequency structure analogous to
    the mora trie exists... recommend staying on the LLM path for this one
    type only"). The fat seed's answer: keep it on the LLM path, but inside
    the SAME call instead of a dedicated one. This does not reduce the
    verification risk design-01 already flagged — see the capability matrix.
    """

    particle: str
    is_correct: bool
    explanation: str


# ---------------------------------------------------------------------------
# The seed itself
# ---------------------------------------------------------------------------


@dataclass
class FatSeed:
    """One sense's complete generation seed: correct content AND invented
    wrong content, from ONE structured LLM response.

    Field -> consumer map (see each sub-dataclass's own docstring for the
    downstream detail):

      sense_id, vocab_id, language_id, lemma      -> identity, all levels
      pos                                          -> L2 display, word_family gate
      semantic_class_raw                           -> normalize_semantic_class()
                                                       -> compute_active_levels()
                                                       (THE level-routing gate)
      definition_simple, definition_standard       -> L2 definition_match
      register                                     -> JA keigo metadata (P1 key '10')
      ipa                                          -> EN L1 metadata (validators.py
                                                       ipa_required warning only)
      pronunciation                                -> L1 metadata; normally filled
                                                       deterministically (pypinyin/
                                                       fugashi) upstream of the seed,
                                                       echoed here for convenience
      sentences (8-10x SeedSentence)                -> L3/L4/L5/L6/L7/L9, tone_id_word's
                                                       target (indirectly)
      morphological_forms (>=2x MorphologicalForm)  -> morph_forms>=2 capability gate;
                                                       L4 correct_form source; word_family
                                                       real-form source
      morphology_wrong_forms (form -> 3x WrongForm) -> L4 distractor options
      primary_collocate                             -> L5/L8 capability gate
                                                       (`requires=('primary_collocate',)`)
                                                       AND `_collocation_is_fixed`'s
                                                       `core_asset['primary_collocate']`
                                                       read (asset_pipeline.py:894)
      collocate_sentence_index                      -> which `sentences[i]` L5/L8 blank
      collocation_distractors (>=3x LabelledDistractor) -> L5 wrong options
      collocation_wrong_collocate (1x LabelledDistractor) -> L8's planted error
      collocate_grounding                           -> NOT real PMI grounding — see
                                                       field docstring below; carried
                                                       only so `render.py` can tag rows
                                                       identically to production's shape
                                                       (`{'status': ...}`)
      cloze_sentence_index, cloze_distractors        -> L3 cloze_completion
      discrimination_correct_index,
      discrimination_wrong_sentences (3x)            -> L6 semantic_discrimination
      spot_incorrect (1x, wraps LabelledWrongSentence
        + correct_sentence_indices)                  -> L7 spot_incorrect_sentence
      l1_audio_confusables (>=3x LabelledDistractor)  -> L1 phonetic_recognition,
                                                        ZH/EN ONLY. JA never reads this
                                                        field — l1_lookup.build_candidates
                                                        (the REAL mora trie) is used
                                                        unchanged; see render.py.
      word_family_forms, word_family_fake_forms      -> typed word_family (EN only,
                                                        per config.py:508)
      syn_ant_candidates                             -> typed synonym_antonym_match
      particle_candidates                            -> typed particle_selection
                                                        (JA only, per config.py:485)

    NOT served by ANY field here (stated explicitly, not left implicit):
    `classifier_match`, `counter_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`,
    `kanji_to_reading`, `reading_to_kanji` — see module docstring.
    """

    sense_id: int
    vocab_id: int
    language_id: int
    lemma: str
    pos: str
    semantic_class_raw: str

    definition_simple: str
    definition_standard: str

    sentences: list[SeedSentence] = field(default_factory=list)
    morphological_forms: list[MorphologicalForm] = field(default_factory=list)
    morphology_wrong_forms: dict[str, list[WrongForm]] = field(default_factory=dict)

    primary_collocate: Optional[str] = None
    collocate_sentence_index: Optional[int] = None
    collocation_distractors: list[LabelledDistractor] = field(default_factory=list)
    collocation_wrong_collocate: Optional[LabelledDistractor] = None
    # Deliberately NOT corpus-PMI-verified. Production's `ground_core_asset`
    # (collocation_grounding.py) runs a DETERMINISTIC corpus-PMI check against
    # this asserted collocate; that grounding step is explicitly OUT of scope
    # for this prototype (it needs the real corpus_collocations table / EN
    # frequency list, neither of which the sandbox seeds). Tagged
    # 'seed_asserted' rather than 'corpus_validated' so `render.py` and the
    # results doc never conflate the two. `_collocation_is_fixed`
    # (asset_pipeline.py:869-897) would DROP L5/L8 on a non-'corpus_validated'
    # tag in production — this prototype's render.py documents that gap
    # rather than silently granting itself a pass it hasn't earned.
    collocate_grounding: dict[str, Any] = field(
        default_factory=lambda: {"status": "seed_asserted"}
    )

    cloze_sentence_index: int = 0
    cloze_distractors: list[LabelledDistractor] = field(default_factory=list)

    discrimination_correct_index: int = 0
    discrimination_wrong_sentences: list[LabelledWrongSentence] = field(default_factory=list)

    spot_incorrect_text: Optional[str] = None
    spot_incorrect_reason: Optional[str] = None
    spot_incorrect_corrected: Optional[str] = None
    spot_incorrect_correct_sentence_indices: list[int] = field(default_factory=list)

    l1_audio_confusables: list[LabelledDistractor] = field(default_factory=list)

    word_family_forms: list[WordFamilyForm] = field(default_factory=list)
    word_family_fake_forms: list[WordFamilyFakeForm] = field(default_factory=list)

    syn_ant_candidates: list[SynAntCandidate] = field(default_factory=list)

    particle_candidates: list[ParticleCandidate] = field(default_factory=list)
    particle_sentence_index: Optional[int] = None

    register: Optional[str] = None
    ipa: Optional[str] = None
    pronunciation: Optional[str] = None


# ---------------------------------------------------------------------------
# Structural validator
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]
    warnings: list[str]
    normalized_semantic_class: Optional[str]


def validate_fat_seed(seed: FatSeed) -> ValidationResult:
    """Structural-only validation — the SAME class of check
    `VocabAssetValidator.validate_prompt1` does today (shape, counts,
    whole-word target matches, the semantic_class CHECK-constraint gate).

    This is explicitly NOT a judge. It cannot tell you an L6 sentence is
    wrong for the RIGHT reason, that an L1 confusable is actually
    audio-confusable, or that a word_family fake form looks plausible rather
    than absurd. Those are exactly the checks Phase A's "no synchronous
    judge" design forgoes — see `docs/results-fat-seed.md`.
    """
    errors: list[str] = []
    warnings: list[str] = []

    profile = LANGUAGE_VALIDATION_PROFILES.get(seed.language_id)
    if profile is None:
        errors.append(f"no LANGUAGE_VALIDATION_PROFILES entry for language_id={seed.language_id}")
        return ValidationResult(False, errors, warnings, None)

    # --- identity / definitions -------------------------------------------------
    if not seed.lemma:
        errors.append("lemma is empty")
    if not seed.definition_simple.strip():
        errors.append("definition_simple is empty")
    if not seed.definition_standard.strip():
        errors.append("definition_standard is empty")
    if not seed.pos.strip():
        errors.append("pos is empty")
    if seed.pos not in profile.pos_set:
        warnings.append(
            f"pos {seed.pos!r} not in this language's declared POS set "
            f"({sorted(profile.pos_set)}) — non-blocking per validate_prompt1"
        )

    # --- semantic_class: THE routing + CHECK-constraint gate ---------------------
    # This is redteam issue #7's sharpest point: writing an un-normalized
    # label either violates the live CHECK constraint (write fails) or falls
    # through to the permissive "full ladder" default (config.py:591-593),
    # silently defeating the capability matrix. Calling the REAL function
    # means this prototype cannot make that mistake even by accident.
    normalized = normalize_semantic_class(seed.semantic_class_raw)
    if normalized is None:
        errors.append(
            f"semantic_class_raw {seed.semantic_class_raw!r} does not normalize to a "
            f"ratified class ({sorted(SEMANTIC_CLASSES)}) — would violate the live "
            f"CHECK constraint or silently fall back to the permissive full-ladder default"
        )

    # --- sentences ----------------------------------------------------------------
    if len(seed.sentences) < ASK_SENTENCE_COUNT:
        warnings.append(
            f"asked-for sentence count is {len(seed.sentences)}, production's own P1 "
            f"prompt asks for {ASK_SENTENCE_COUNT} — fewer leaves no headroom for "
            f"variant A/B differentiation or (in a design with a judge) attrition"
        )
    if len(seed.sentences) < P1_MIN_ACCEPTABLE_SENTENCES:
        errors.append(
            f"only {len(seed.sentences)} sentences, below the ladder's own floor "
            f"P1_MIN_ACCEPTABLE_SENTENCES={P1_MIN_ACCEPTABLE_SENTENCES} "
            f"(config.py:202) — this is the exact defect redteam issue #1 found in G1"
        )
    seen_indices = set()
    for s in seed.sentences:
        if s.index in seen_indices:
            errors.append(f"duplicate sentence index {s.index}")
        seen_indices.add(s.index)
        if not s.text.strip():
            errors.append(f"sentence {s.index}: empty text")
            continue
        if not s.target_word.strip():
            errors.append(f"sentence {s.index}: empty target_word")
        elif not contains_target_whole_word(s.text, s.target_word):
            errors.append(
                f"sentence {s.index}: target_word {s.target_word!r} is not a "
                f"whole-word match in text {s.text!r} (mirrors validators.py's "
                f"contains_target_whole_word check)"
            )

    # --- morphological_forms: countable-list gate, not prose ----------------------
    form_count = len(seed.morphological_forms)
    if form_count < profile.min_morphological_forms:
        warnings.append(
            f"expected at least {profile.min_morphological_forms} morphological_forms "
            f"for language_id={seed.language_id}, got {form_count} (non-blocking, "
            f"mirrors validate_prompt1's own warning-not-error treatment)"
        )
    for form, wrongs in seed.morphology_wrong_forms.items():
        if len(wrongs) < 3:
            errors.append(
                f"morphology_wrong_forms[{form!r}] has {len(wrongs)} wrong forms, "
                f"L4 needs 3 (validators._validate_option_level: 4 options, 1 correct)"
            )

    # --- L3 cloze -------------------------------------------------------------
    if seed.cloze_distractors and len(seed.cloze_distractors) < 3:
        errors.append(
            f"cloze_distractors has {len(seed.cloze_distractors)}, L3 needs 3"
        )

    # --- L5/L8 collocation -----------------------------------------------------
    if seed.primary_collocate:
        if len(seed.collocation_distractors) < 3:
            errors.append(
                f"collocation_distractors has {len(seed.collocation_distractors)}, "
                f"L5 needs 3"
            )
        if seed.collocate_grounding.get("status") != "corpus_validated":
            warnings.append(
                "collocate_grounding is not 'corpus_validated' — production's "
                "_collocation_is_fixed would DROP L5/L8 for this asset "
                "(asset_pipeline.py:869-897); this prototype renders them anyway "
                "and reports it as a named gap, see docs/results-fat-seed.md"
            )

    # --- L6 semantic_discrimination ---------------------------------------------
    if seed.discrimination_wrong_sentences and len(seed.discrimination_wrong_sentences) < 3:
        errors.append(
            f"discrimination_wrong_sentences has "
            f"{len(seed.discrimination_wrong_sentences)}, L6 needs 3 "
            f"(validators._validate_level_6)"
        )

    # --- L7 spot_incorrect --------------------------------------------------------
    if seed.spot_incorrect_text is not None and not seed.spot_incorrect_reason:
        errors.append(
            "spot_incorrect_text is set but spot_incorrect_reason (error_description) "
            "is missing (validators._validate_level_7 requires it)"
        )

    # --- L1 zh/en audio confusables ----------------------------------------------
    if seed.language_id in (1, 2) and seed.l1_audio_confusables:
        if len(seed.l1_audio_confusables) < 3:
            errors.append(
                f"l1_audio_confusables has {len(seed.l1_audio_confusables)}, L1 needs "
                f"3 kept after judging in production — Phase A here has no judge, so "
                f"this prototype requires >=3 up front rather than over-generating "
                f"(cf. validators.py's OPTION_COUNTS=(4,8) over-generation allowance, "
                f"which exists BECAUSE a judge thins the pool; this design has no judge "
                f"to thin it, a real quality risk — see the capability matrix)"
            )

    # --- word_family ---------------------------------------------------------------
    if seed.word_family_fake_forms:
        from wordfreq import zipf_frequency

        lang_code = {1: "zh", 2: "en", 3: "ja"}.get(seed.language_id, "en")
        for fake in seed.word_family_fake_forms:
            score = zipf_frequency(fake.text, lang_code)
            if score > 0:
                errors.append(
                    f"word_family_fake_forms: {fake.text!r} scores zipf={score:.2f} "
                    f"in wordfreq — it is a REAL word, not an invented non-word "
                    f"(the one deterministic veto design-01-generation.md's Risks "
                    f"section says IS possible: 'a dictionary can veto a real word')"
                )
        if len(seed.word_family_fake_forms) < 3:
            errors.append(
                f"word_family_fake_forms has {len(seed.word_family_fake_forms)}, "
                f"needs 3 distractors"
            )

    return ValidationResult(
        passed=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        normalized_semantic_class=normalized,
    )
