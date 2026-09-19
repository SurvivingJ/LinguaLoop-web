"""
A deterministic, SYNTHETIC-BUT-SCHEMA-VALID FatSeed generator.

WHY THIS EXISTS: `lab/mock_llm.py`'s "synthetic" mode returns a fixed tiny
placeholder JSON (`{"sentences": [...3...], "distractors": [...3...]}`)
regardless of prompt content (see mock_llm.py `_synthesize`) - it is built
for timing/plumbing measurement, not for exercising a specific schema. This
prototype needs to measure "how many exercises pass the REAL structural
validators" (task requirement), which is meaningless against mock_llm's
placeholder shape. So this module fabricates a FatSeed that is
STRUCTURALLY as complete as a real model's response would need to be
(right field counts, whole-word target matches, a real semantic_class,
non-colliding invented word_family forms) while being LINGUISTICALLY
templated/fake, exactly like mock_llm's own synthetic content -- same
fidelity gap, just schema-aware instead of schema-blind.

Latency/cost accounting still goes through mock_llm.MockLLMClient.complete()
(see variants.py) using the REAL prompt text length for tokens_in and this
module's serialized output length for tokens_out -- mock_llm's own fixed
placeholder is never used for either.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_LAB_ROOT = Path(__file__).resolve().parents[2]
if str(_LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(_LAB_ROOT))

from lab.models import SenseRow  # noqa: E402

from prototypes.fat_seed.seed_schema import (  # noqa: E402
    ASK_SENTENCE_COUNT, FatSeed, LabelledDistractor, LabelledWrongSentence,
    MorphologicalForm, SeedSentence, SynAntCandidate, WordFamilyFakeForm,
    WordFamilyForm, WrongForm, ParticleCandidate,
)

_LANG_CODE = {1: "zh", 2: "en", 3: "ja"}
_DEFAULT_POS = {1: "名词", 2: "noun", 3: "名詞"}
# Crude, illustrative-only POS -> semantic_class heuristic. Real production
# gets this from the LLM's own classification; this prototype only needs a
# value that normalizes cleanly for the capability-matrix gate to route on.
_POS_TO_CLASS = {
    "verb": "action", "动词": "action", "動詞": "action",
    "adjective": "property", "adverb": "property",
    "形容词": "property", "副词": "property", "形容詞": "property", "副詞": "property",
}


def _class_for(pos: str | None) -> str:
    return _POS_TO_CLASS.get((pos or "").strip(), "concrete")


def _sentences(lemma: str, n: int, rng: random.Random) -> list[SeedSentence]:
    tiers = ["T1", "T2", "T2", "T3", "T3", "T4", "T4", "T5", "T2", "T3"]
    out = []
    for i in range(n):
        tier = tiers[i % len(tiers)]
        out.append(SeedSentence(
            index=i,
            text=f"[synthetic sentence {i}] ...{lemma}... rest of a {tier}-tier example.",
            target_word=lemma,
            tier=tier,
            sentence_source="generated",
            contains_collocate=(i == 0),
        ))
    return out


def synthesize_fat_seed(sense: SenseRow, *, seed_variant_tag: str = "") -> FatSeed:
    """Deterministic given (sense.sense_id, seed_variant_tag) -- same sense
    always yields the same synthetic seed for a given variant tag, so repeat
    harness runs are reproducible."""
    rng = random.Random(f"fatseed:{sense.sense_id}:{seed_variant_tag}")
    lang = sense.language_id
    lemma = sense.lemma
    pos = sense.part_of_speech or _DEFAULT_POS.get(lang, "noun")
    semantic_class = _class_for(pos)

    seed = FatSeed(
        sense_id=sense.sense_id,
        vocab_id=sense.vocab_id,
        language_id=lang,
        lemma=lemma,
        pos=pos,
        semantic_class_raw=semantic_class,
        definition_simple=(sense.definition or f"[simple def for {lemma}]")[:80],
        definition_standard=(sense.definition or f"[standard def for {lemma}]"),
        sentences=_sentences(lemma, ASK_SENTENCE_COUNT, rng),
        pronunciation=sense.pronunciation,
    )

    # --- L3 cloze: all languages ---------------------------------------
    seed.cloze_sentence_index = 1
    seed.cloze_distractors = [
        LabelledDistractor(f"{lemma}_wrongA", "wrong sense, plausible surface fit"),
        LabelledDistractor(f"{lemma}_wrongB", "different register, plausible surface fit"),
        LabelledDistractor(f"{lemma}_wrongC", "trivially wrong, semantically unrelated"),
    ]

    # --- L6 semantic_discrimination: all languages ----------------------
    seed.discrimination_correct_index = 2
    seed.discrimination_wrong_sentences = [
        LabelledWrongSentence(f"[wrong-for-reason-A] ...{lemma}...", "reason A: wrong argument structure"),
        LabelledWrongSentence(f"[wrong-for-reason-B] ...{lemma}...", "reason B: wrong register"),
        LabelledWrongSentence(f"[wrong-for-reason-C] ...{lemma}...", "reason C: wrong collocate"),
    ]

    # --- L7 spot_incorrect: all languages ---------------------------------
    seed.spot_incorrect_text = f"[incorrect] ...{lemma}... has an error."
    seed.spot_incorrect_reason = "synthetic labelled grammar error"
    seed.spot_incorrect_corrected = f"[corrected] ...{lemma}... is fixed."
    seed.spot_incorrect_correct_sentence_indices = [3, 4]

    # --- L1: zh/en only (ja uses the real mora trie, never this field) ----
    if lang in (1, 2):
        seed.l1_audio_confusables = [
            LabelledDistractor(f"{lemma}_snd1", "one-phoneme substitution, real-word neighbor"),
            LabelledDistractor(f"{lemma}_snd2", "shares onset, plausible mishearing"),
            LabelledDistractor(f"{lemma}_snd3", "shares rime, plausible mishearing"),
        ]

    # --- morphological_forms / L4 / word_family: gated by language+class --
    if lang in (2, 3) and semantic_class in ("action", "property"):
        seed.morphological_forms = [
            MorphologicalForm(f"{lemma}ed", "past_tense"),
            MorphologicalForm(f"{lemma}ing", "gerund"),
        ]
        seed.morphology_wrong_forms = {
            f"{lemma}ed": [
                WrongForm(f"{lemma}eded", "double-suffix error"),
                WrongForm(f"{lemma}d", "malformed suffix"),
                WrongForm(f"{lemma}s", "wrong tense entirely"),
            ]
        }

    if lang == 2 and semantic_class in ("abstract", "action", "property"):
        seed.word_family_forms = [
            WordFamilyForm(f"{lemma}tion", "noun"),
            WordFamilyForm(f"{lemma}ive", "adjective"),
        ]
        seed.word_family_fake_forms = [
            WordFamilyFakeForm(f"{lemma}zzment", "invented, non-attested suffix combination"),
            WordFamilyFakeForm(f"{lemma}qful", "invented, phonotactically implausible"),
            WordFamilyFakeForm(f"{lemma}xity", "invented, mimics -ity but not attested"),
        ]

    # --- L5/L8 collocation: EN only (zh/ja disabled in prod regardless) ---
    if lang == 2:
        seed.primary_collocate = f"{lemma} up"
        seed.collocate_sentence_index = 0
        seed.collocation_distractors = [
            LabelledDistractor(f"{lemma} in", "wrong preposition, not a fixed collocate"),
            LabelledDistractor(f"{lemma} at", "plausible surface fit, not attested"),
            LabelledDistractor(f"{lemma} on", "plausible surface fit, not attested"),
        ]
        seed.collocation_wrong_collocate = LabelledDistractor(
            f"{lemma} of", "planted non-collocate for L8 repair")

    # --- typed: synonym_antonym_match, all languages -----------------------
    seed.syn_ant_candidates = [
        SynAntCandidate(f"{lemma}_syn", "synonym", "close in this sense"),
        SynAntCandidate(f"{lemma}_ant", "antonym", "opposite pole"),
    ]

    # --- typed: particle_selection, JA only --------------------------------
    if lang == 3:
        seed.particle_sentence_index = 0
        seed.particle_candidates = [
            ParticleCandidate("が", True, "subject marker, correct here"),
            ParticleCandidate("を", False, "object marker, wrong case role"),
            ParticleCandidate("に", False, "wrong case role for this verb"),
        ]

    return seed
