"""
Deterministic renderers: FatSeed -> ExerciseRow, gated by the REAL production
capability matrix (services/vocabulary_ladder/config.py), not a hand-rolled
copy of it.

Gating strategy: build a `core`-shaped dict from the FatSeed (the same shape
`word_assets.prompt1_core` has), then call the REAL `capability_context_from_core`,
`enabled_capabilities`, and `requirements_met` (imported read-only, verified
import-safe -- no DB/network touched). This means the set of (type_code,
ladder_level) this module is even ASKED to render for a given
(language_id, semantic_class) is exactly production's live-configured set --
zh morphology_slot, zh/ja collocation_gap_fill/collocation_repair are excluded
automatically because their capability rows carry `is_enabled=False` in
config.py, not because this file special-cased them.

Where a REAL, DB-free production module exists, it is called directly and
unmodified: `l1_lookup.build_candidates` (ja L1, the real mora trie),
`deterministic.jumbled` (L9), `deterministic.cloze_typed` (L4 form_production),
`deterministic.tone` (tone_id_word, zh). Confirmed DB-free by direct grep
before this file was written (jumbled.py/cloze_typed.py/tone.py never touch
`ctx.db`).

Types needing a `ctx.db` lexicon/dictionary shim this prototype does not
build (`classifier_match`, `counter_match`, `hanzi_to_pinyin`, `pinyin_to_hanzi`,
`kanji_to_reading`, `reading_to_kanji`) are explicitly marked out of scope,
not silently dropped -- see `OUT_OF_SCOPE_TYPE_CODES` below and the Skip
records `render_all_for_seed` returns.
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_LAB_ROOT = Path(__file__).resolve().parents[2]
if str(_LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(_LAB_ROOT))

from lab.models import ExerciseRow  # noqa: E402

from services.vocabulary_ladder.config import (  # noqa: E402
    capability_context_from_core, enabled_capabilities, normalize_semantic_class,
    requirements_met,
)
from services.vocabulary_ladder import l1_lookup  # noqa: E402
from services.vocabulary_ladder.deterministic import (  # noqa: E402
    SenseContext as RealSenseContext, jumbled as real_jumbled,
    cloze_typed as real_cloze_typed, tone as real_tone,
)

from prototypes.fat_seed.seed_schema import FatSeed  # noqa: E402

# Needs a ctx.db lexicon/dictionary lookup this prototype does not shim.
OUT_OF_SCOPE_TYPE_CODES = frozenset({
    "classifier_match", "counter_match", "hanzi_to_pinyin",
    "pinyin_to_hanzi", "kanji_to_reading", "reading_to_kanji",
})
# Not a core ladder level / typed type this prototype scopes to measuring.
NOT_MODELLED_TYPE_CODES = frozenset({
    "tl_nl_translation", "nl_tl_translation", "text_flashcard",
    "listening_flashcard", "timed_speed_round",
})


@dataclass
class RenderSkip:
    type_code: str
    reason: str


def _core_dict(seed: FatSeed) -> dict:
    """A word_assets.prompt1_core-shaped dict, built from the FatSeed, for
    the REAL capability_context_from_core() to gate on."""
    return {
        "morphological_forms": [f.form for f in seed.morphological_forms],
        "pronunciation": seed.pronunciation or "",
        "definition": seed.definition_standard,
        "sentences": [
            {"text": s.text, "target_word": s.target_word, "tier": s.tier}
            for s in seed.sentences
        ],
        "primary_collocate": seed.primary_collocate,
        "semantic_class": seed.semantic_class_raw,
        "pos": seed.pos,
    }


def applicable_capabilities(seed: FatSeed) -> list[dict]:
    """The REAL, live-configured capability rows this (language, class) pair
    is allowed to attempt -- disabled rows (zh morphology_slot, zh/ja
    collocation) are already absent because config.py marks them
    is_enabled=False, not because this function filters them."""
    gate_class = normalize_semantic_class(seed.semantic_class_raw)
    core = _core_dict(seed)
    context = capability_context_from_core(core)
    return [
        cap for cap in enabled_capabilities(seed.language_id, gate_class)
        if requirements_met(cap.get("requires", ()), context)
    ]


def _real_ctx(seed: FatSeed, variant: str = "A") -> RealSenseContext:
    return RealSenseContext(
        sense_id=seed.sense_id, language_id=seed.language_id, lemma=seed.lemma,
        core=_core_dict(seed), semantic_class=normalize_semantic_class(seed.semantic_class_raw),
        tier=(seed.sentences[0].tier if seed.sentences else None),
        pronunciation=seed.pronunciation, definition=seed.definition_standard,
        db=None, variant=variant,
        sentence_assignments={3: 0, 4: 1, 5: 0, 6: 2, 7: 0, 8: 0, 9: min(5, len(seed.sentences) - 1)},
    )


# ---------------------------------------------------------------------------
# L1 phonetic_recognition
# ---------------------------------------------------------------------------

def render_l1(seed: FatSeed) -> Optional[ExerciseRow]:
    if seed.language_id == 3:  # ja: REAL mora trie, unmodified
        trie_result = l1_lookup.build_candidates(
            seed.lemma, seed.pronunciation or "", seed.language_id,
            definition=seed.definition_standard,
        )
        if trie_result is None:
            return None
        correct = trie_result["correct_answer"]
        distractors = trie_result["candidates"][:3]
        explanations = trie_result["explanations"]
        source = "phonetic_trie"
    else:  # zh/en: seed-authored, unverified confusability (AMBER)
        if len(seed.l1_audio_confusables) < 3:
            return None
        correct = seed.lemma
        distractors = [d.text for d in seed.l1_audio_confusables[:3]]
        explanations = {correct: "target"}
        explanations.update({d.text: d.explanation for d in seed.l1_audio_confusables[:3]})
        source = "fat_seed_llm_unverified"

    options = [correct] + distractors
    random.Random(f"l1:{seed.sense_id}").shuffle(options)
    valid = len(distractors) >= 3 and correct not in distractors
    content = {
        "word": correct, "pronunciation": seed.pronunciation or "",
        "options": options, "correct_answer": correct,
        "distractor_source": source, "explanations": explanations,
    }
    return ExerciseRow("phonetic_recognition", content, seed.sense_id, seed.language_id,
                        ladder_level=1, passed_validation=valid,
                        tags={"distractor_source": source})


# ---------------------------------------------------------------------------
# L2 definition_match -- distractors sourced from sibling seeds in the same
# batch (in-memory), NOT a ctx.db lexicon shim. # ADAPTED FROM
# services/vocabulary_ladder/deterministic/definition_match.py:32-78
# ---------------------------------------------------------------------------

def render_l2(seed: FatSeed, sibling_pool: list[FatSeed]) -> Optional[ExerciseRow]:
    definition = seed.definition_standard.strip()
    if not definition:
        return None
    pool = [
        s.definition_standard.strip() for s in sibling_pool
        if s.sense_id != seed.sense_id and s.definition_standard.strip()
        and s.definition_standard.strip() != definition
    ]
    rng = random.Random(f"l2:{seed.sense_id}")
    rng.shuffle(pool)
    distractors = pool[:3]
    if len(distractors) < 3:
        return None
    options = [definition] + distractors
    rng.shuffle(options)
    content = {"word": seed.lemma, "pronunciation": seed.pronunciation or "",
               "correct_definition": definition, "options": options}
    return ExerciseRow("definition_match", content, seed.sense_id, seed.language_id,
                        ladder_level=2, passed_validation=True)


# ---------------------------------------------------------------------------
# L3 cloze_completion -- # ADAPTED FROM exercise_renderer._render_cloze:669-735
# ---------------------------------------------------------------------------

def render_l3(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.cloze_distractors) < 3 or not seed.sentences:
        return None
    idx = min(seed.cloze_sentence_index, len(seed.sentences) - 1)
    sentence = seed.sentences[idx]
    if seed.lemma not in sentence.text:
        return None
    blanked = sentence.text.replace(seed.lemma, "___", 1)
    distractors = [d.text for d in seed.cloze_distractors[:3]]
    options = [seed.lemma] + distractors
    random.Random(f"l3:{seed.sense_id}").shuffle(options)
    content = {
        "sentence_with_blank": blanked, "original_sentence": sentence.text,
        "correct_answer": seed.lemma, "options": options,
        "distractor_reasons": {d.text: d.explanation for d in seed.cloze_distractors[:3]},
        "target_word": seed.lemma,
    }
    return ExerciseRow("cloze_completion", content, seed.sense_id, seed.language_id,
                        ladder_level=3, passed_validation=True)


# ---------------------------------------------------------------------------
# L4 morphology_slot (EN/JA action|property only) --
# # ADAPTED FROM exercise_renderer._render_morphology_slot:737-783
# ---------------------------------------------------------------------------

def render_l4_morphology(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.morphological_forms) < 2 or not seed.sentences:
        return None
    form = seed.morphological_forms[0]
    wrongs = seed.morphology_wrong_forms.get(form.form, [])
    if len(wrongs) < 3:
        return None
    sentence = seed.sentences[min(1, len(seed.sentences) - 1)]
    blanked = sentence.text.replace(seed.lemma, "___", 1)
    options = [form.form] + [w.text for w in wrongs[:3]]
    random.Random(f"l4:{seed.sense_id}").shuffle(options)
    content = {
        "sentence_with_blank": blanked, "correct_answer": form.form,
        "base_form": seed.lemma, "form_label": form.label, "options": options,
        "explanations": {w.text: w.explanation for w in wrongs[:3]},
    }
    return ExerciseRow("morphology_slot", content, seed.sense_id, seed.language_id,
                        ladder_level=4, passed_validation=True)


# ---------------------------------------------------------------------------
# L5 collocation_gap_fill (EN only, prod-enabled) --
# # ADAPTED FROM exercise_renderer._render_collocation_gap:785-842
# ---------------------------------------------------------------------------

def render_l5(seed: FatSeed) -> Optional[ExerciseRow]:
    if not seed.primary_collocate or len(seed.collocation_distractors) < 3 or not seed.sentences:
        return None
    idx = seed.collocate_sentence_index or 0
    sentence = seed.sentences[min(idx, len(seed.sentences) - 1)]
    text = f"{sentence.text} ({seed.primary_collocate})"  # synth seeds don't embed the collocate in prose
    blanked = text.replace(seed.primary_collocate, "___", 1)
    options = [seed.primary_collocate] + [d.text for d in seed.collocation_distractors[:3]]
    random.Random(f"l5:{seed.sense_id}").shuffle(options)
    content = {"sentence": blanked, "correct": seed.primary_collocate, "options": options,
               "grounding_status": seed.collocate_grounding.get("status")}
    return ExerciseRow("collocation_gap_fill", content, seed.sense_id, seed.language_id,
                        ladder_level=5, passed_validation=True)


# ---------------------------------------------------------------------------
# L6 semantic_discrimination -- ADAPTED FROM
# exercise_renderer._render_semantic_discrimination:844-914
# ---------------------------------------------------------------------------

def render_l6(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.discrimination_wrong_sentences) < 3 or not seed.sentences:
        return None
    idx = min(seed.discrimination_correct_index, len(seed.sentences) - 1)
    correct_sent = seed.sentences[idx]
    wrongs = seed.discrimination_wrong_sentences[:3]
    all_sentences = [{"text": correct_sent.text, "is_correct": True}]
    all_sentences += [{"text": w.text, "is_correct": False, "reason": w.reason} for w in wrongs]
    random.Random(f"l6:{seed.sense_id}").shuffle(all_sentences)
    content = {"sentences": all_sentences, "target_word": seed.lemma}
    return ExerciseRow("semantic_discrimination", content, seed.sense_id, seed.language_id,
                        ladder_level=6, passed_validation=True)


# ---------------------------------------------------------------------------
# L7 spot_incorrect_sentence -- ADAPTED FROM
# exercise_renderer._render_spot_incorrect:916-977
# ---------------------------------------------------------------------------

def render_l7(seed: FatSeed) -> Optional[ExerciseRow]:
    if not seed.spot_incorrect_text or not seed.spot_incorrect_reason:
        return None
    correct_sents = [
        {"text": s.text, "is_correct": True}
        for i, s in enumerate(seed.sentences)
        if i in (seed.spot_incorrect_correct_sentence_indices or [0, 1])
    ][:2] or [{"text": seed.sentences[0].text, "is_correct": True}] if seed.sentences else []
    if not correct_sents:
        return None
    all_sents = correct_sents + [{
        "text": seed.spot_incorrect_text, "is_correct": False,
        "error_description": seed.spot_incorrect_reason,
        "corrected_sentence": seed.spot_incorrect_corrected,
    }]
    random.Random(f"l7:{seed.sense_id}").shuffle(all_sents)
    content = {"sentences": all_sents}
    return ExerciseRow("spot_incorrect_sentence", content, seed.sense_id, seed.language_id,
                        ladder_level=7, passed_validation=True)


# ---------------------------------------------------------------------------
# L8 collocation_repair (EN only, prod-enabled) --
# # ADAPTED FROM exercise_renderer._render_collocation_repair:979-1037
# ---------------------------------------------------------------------------

def render_l8(seed: FatSeed) -> Optional[ExerciseRow]:
    if not seed.primary_collocate or seed.collocation_wrong_collocate is None or not seed.sentences:
        return None
    sentence = seed.sentences[0]
    text = f"{sentence.text} ({seed.primary_collocate})"
    error = seed.collocation_wrong_collocate
    sentence_with_error = text.replace(seed.primary_collocate, error.text, 1)
    content = {
        "sentence_with_error": sentence_with_error, "error_word": error.text,
        "correct_word": seed.primary_collocate, "explanation": error.explanation,
    }
    return ExerciseRow("collocation_repair", content, seed.sense_id, seed.language_id,
                        ladder_level=8, passed_validation=True)


# ---------------------------------------------------------------------------
# L9 jumbled_sentence -- REAL module, unmodified, db=None
# ---------------------------------------------------------------------------

def render_l9(seed: FatSeed) -> Optional[ExerciseRow]:
    ctx = _real_ctx(seed)
    skips: list = []
    items = real_jumbled.build(ctx, skips)
    if not items:
        return None
    return ExerciseRow("jumbled_sentence", items[0], seed.sense_id, seed.language_id,
                        ladder_level=9, passed_validation=True)


# ---------------------------------------------------------------------------
# L4 form_production: cloze_typed -- REAL module, unmodified, db=None
# ---------------------------------------------------------------------------

def render_cloze_typed(seed: FatSeed) -> Optional[ExerciseRow]:
    ctx = _real_ctx(seed)
    skips: list = []
    items = real_cloze_typed.build(ctx, skips)
    if not items:
        return None
    return ExerciseRow("cloze_typed", items[0], seed.sense_id, seed.language_id,
                        ladder_level=4, passed_validation=True)


# ---------------------------------------------------------------------------
# tone_id_word (zh) -- REAL module, unmodified, db=None
# ---------------------------------------------------------------------------

def render_tone_id_word(seed: FatSeed) -> Optional[ExerciseRow]:
    ctx = _real_ctx(seed)
    skips: list = []
    items = real_tone.build(ctx, skips)
    if not items:
        return None
    return ExerciseRow("tone_id_word", items[0], seed.sense_id, seed.language_id,
                        ladder_level=1, passed_validation=True)


# ---------------------------------------------------------------------------
# typed: synonym_antonym_match, word_family, particle_selection
# ---------------------------------------------------------------------------

def render_syn_ant(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.syn_ant_candidates) < 1:
        return None
    content = {"lemma": seed.lemma, "definition": seed.definition_standard,
               "candidates": [{"text": c.text, "relation": c.relation, "note": c.note}
                              for c in seed.syn_ant_candidates]}
    return ExerciseRow("synonym_antonym_match", content, seed.sense_id, seed.language_id,
                        ladder_level=6, passed_validation=True)


def render_word_family(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.word_family_forms) < 1 or len(seed.word_family_fake_forms) < 3:
        return None
    correct = seed.word_family_forms[0]
    options = [correct.text] + [f.text for f in seed.word_family_fake_forms[:3]]
    random.Random(f"wf:{seed.sense_id}").shuffle(options)
    content = {"base": seed.lemma, "correct_answer": correct.text, "form_label": correct.label,
               "options": options,
               "explanations": {f.text: f.explanation for f in seed.word_family_fake_forms[:3]}}
    return ExerciseRow("word_family", content, seed.sense_id, seed.language_id,
                        ladder_level=4, passed_validation=True)


def render_particle(seed: FatSeed) -> Optional[ExerciseRow]:
    if len(seed.particle_candidates) < 3 or not seed.sentences:
        return None
    idx = seed.particle_sentence_index or 0
    sentence = seed.sentences[min(idx, len(seed.sentences) - 1)]
    correct = [p for p in seed.particle_candidates if p.is_correct]
    if len(correct) != 1:
        return None
    content = {
        "sentence": sentence.text,
        "options": [{"particle": p.particle, "is_correct": p.is_correct, "explanation": p.explanation}
                    for p in seed.particle_candidates],
    }
    return ExerciseRow("particle_selection", content, seed.sense_id, seed.language_id,
                        ladder_level=4, passed_validation=True)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

_DISPATCH = {
    "phonetic_recognition": lambda seed, pool: render_l1(seed),
    "definition_match": lambda seed, pool: render_l2(seed, pool),
    "cloze_completion": lambda seed, pool: render_l3(seed),
    "cloze_typed": lambda seed, pool: render_cloze_typed(seed),
    "morphology_slot": lambda seed, pool: render_l4_morphology(seed),
    "collocation_gap_fill": lambda seed, pool: render_l5(seed),
    "semantic_discrimination": lambda seed, pool: render_l6(seed),
    "spot_incorrect_sentence": lambda seed, pool: render_l7(seed),
    "collocation_repair": lambda seed, pool: render_l8(seed),
    "jumbled_sentence": lambda seed, pool: render_l9(seed),
    "tone_id_word": lambda seed, pool: render_tone_id_word(seed),
    "synonym_antonym_match": lambda seed, pool: render_syn_ant(seed),
    "word_family": lambda seed, pool: render_word_family(seed),
    "particle_selection": lambda seed, pool: render_particle(seed),
}


def render_all_for_seed(
    seed: FatSeed, sibling_pool: Optional[list[FatSeed]] = None,
) -> tuple[list[ExerciseRow], list[RenderSkip]]:
    """Render every type_code the REAL capability matrix says this
    (language, semantic_class) pair is entitled to, using this seed."""
    sibling_pool = sibling_pool or []
    rows: list[ExerciseRow] = []
    skips: list[RenderSkip] = []
    seen_types: set[str] = set()
    for cap in applicable_capabilities(seed):
        type_code = cap["type_code"]
        if type_code in seen_types:
            continue  # a type can appear once per (language, sense) row list here
        seen_types.add(type_code)
        if type_code in OUT_OF_SCOPE_TYPE_CODES:
            skips.append(RenderSkip(type_code, "needs a ctx.db lexicon/dictionary shim; out of scope for this prototype"))
            continue
        if type_code in NOT_MODELLED_TYPE_CODES:
            skips.append(RenderSkip(type_code, "not modelled in this prototype (not a core ladder level)"))
            continue
        renderer = _DISPATCH.get(type_code)
        if renderer is None:
            skips.append(RenderSkip(type_code, "no renderer registered for this type_code"))
            continue
        try:
            row = renderer(seed, sibling_pool)
        except Exception as exc:  # noqa: BLE001
            skips.append(RenderSkip(type_code, f"renderer raised: {exc}"))
            continue
        if row is None:
            skips.append(RenderSkip(type_code, "seed lacked sufficient content for this type"))
        else:
            rows.append(row)
    return rows, skips
