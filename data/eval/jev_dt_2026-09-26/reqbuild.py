# -*- coding: utf-8 -*-
"""Jev Decisions API request builders for the three arms of this experiment.
All instructions/option text are wholly in the item's own L2 (native), per
the same HARD RULE the prior jev_2026-09-26/exp_c run followed.

Arm A1 (passage-level): one call per item. 3 questions:
    has_error (noul), subtype (choice, native v5 subtypes + "no error"),
    meaning_changed (noul).

Arm A2 (sentence-level with passage context): one call per aligned sentence
pair. Same 3 questions, scoped to the focus sentence; state carries the full
passages too so jev has context. Callers should skip (not call) pairs whose
ref/repro sentence text is byte-identical -- clean by construction.

Arm NR (naturalness + range): one call per item. 2 score-mode questions
using the v6 rubric band descriptors (rubric_data.band_descriptors), the
same tier-resolution rubric_data.build_request uses.
"""
from __future__ import annotations

import rubric_data as R
import taxonomy_data as T


def _subtype_choice_criteria(lang: str) -> dict:
    subtypes = T.SUBTYPES[lang]
    gloss = T.SUBTYPE_GLOSS[lang]
    criteria = {s: gloss[s] for s in subtypes}
    criteria["no_error"] = T.NO_ERROR_OPTION[lang]
    return criteria


def build_a1_request(item: dict, lang: str) -> tuple[dict, dict]:
    ref_key = R.REF_KEY[lang]
    learner_key = R.LEARNER_KEY[lang]
    state = {ref_key: item["reference"], learner_key: item["reproduction"]}

    he = R.HAS_ERROR_NOUL[lang]
    mc = R.MEANING_CHANGED_NOUL[lang]

    questions = {
        "has_error": {
            "type": "noul",
            "instructions": he["instructions"].format(ref_key=ref_key, learner_key=learner_key),
            "criteria": {"true": he["true"], "false": he["false"]},
        },
        "subtype": {
            "type": "choice",
            "instructions": R.SUBTYPE_CHOICE_INSTRUCTION[lang].format(ref_key=ref_key, learner_key=learner_key),
            "criteria": _subtype_choice_criteria(lang),
        },
        "meaning_changed": {
            "type": "noul",
            "instructions": mc["instructions"].format(ref_key=ref_key, learner_key=learner_key),
            "criteria": {"true": mc["true"], "false": mc["false"]},
        },
    }
    return state, questions


def build_a2_request(reference: str, reproduction: str, focus_ref: str, focus_repro: str, lang: str) -> tuple[dict, dict]:
    full_ref_key = R.FULL_REF_KEY[lang]
    full_learner_key = R.FULL_LEARNER_KEY[lang]
    focus_ref_key = R.FOCUS_REF_KEY[lang]
    focus_learner_key = R.FOCUS_LEARNER_KEY[lang]

    state = {
        full_ref_key: reference,
        full_learner_key: reproduction,
        focus_ref_key: focus_ref,
        focus_learner_key: focus_repro,
    }

    he = R.HAS_ERROR_NOUL[lang]
    mc = R.MEANING_CHANGED_NOUL[lang]
    he_suffix = R.HAS_ERROR_NOUL_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key)
    mc_suffix = R.MEANING_CHANGED_NOUL_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key)
    subtype_suffix = R.SUBTYPE_CHOICE_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key)

    questions = {
        "has_error": {
            "type": "noul",
            "instructions": he["instructions"].format(ref_key=full_ref_key, learner_key=full_learner_key) + he_suffix,
            "criteria": {"true": he["true"], "false": he["false"]},
        },
        "subtype": {
            "type": "choice",
            "instructions": R.SUBTYPE_CHOICE_INSTRUCTION[lang].format(ref_key=full_ref_key, learner_key=full_learner_key) + subtype_suffix,
            "criteria": _subtype_choice_criteria(lang),
        },
        "meaning_changed": {
            "type": "noul",
            "instructions": mc["instructions"].format(ref_key=full_ref_key, learner_key=full_learner_key) + mc_suffix,
            "criteria": {"true": mc["true"], "false": mc["false"]},
        },
    }
    return state, questions


def build_nr_request(item: dict, lang: str) -> tuple[dict, dict]:
    ref_key = R.REF_KEY[lang]
    learner_key = R.LEARNER_KEY[lang]
    state = {ref_key: item["reference"], learner_key: item["reproduction"]}

    questions = {}
    for dim in ("naturalness", "range"):
        dim_label = R.DIMENSION_NAMES[lang][dim]
        levels = R.band_descriptors(dim, lang)
        instr = R.SCORE_INSTRUCTION_TMPL[lang].format(dim=dim_label, ref_key=ref_key, learner_key=learner_key)
        questions[f"score_{dim}"] = {
            "type": "score",
            "instructions": instr,
            "criteria": list(levels),
        }
    return state, questions


def build_nr_v2_request(item: dict, lang: str) -> tuple[dict, dict]:
    """NR variant 2: same state/criteria as build_nr_request, reworded
    instructions (rubric_data.SCORE_INSTRUCTION_V2) anchoring naturalness on
    "would a native of this age tier phrase it" and range on "kept the
    reference's specific vocab/structures vs flattened to generic ones"."""
    ref_key = R.REF_KEY[lang]
    learner_key = R.LEARNER_KEY[lang]
    state = {ref_key: item["reference"], learner_key: item["reproduction"]}

    questions = {}
    for dim in ("naturalness", "range"):
        levels = R.band_descriptors(dim, lang)
        instr = R.SCORE_INSTRUCTION_V2[dim][lang].format(ref_key=ref_key, learner_key=learner_key)
        questions[f"score_{dim}"] = {
            "type": "score",
            "instructions": instr,
            "criteria": list(levels),
        }
    return state, questions


def build_a3_request(reference: str, reproduction: str, focus_ref: str, focus_repro: str, lang: str) -> tuple[dict, dict]:
    """Arm A3 (BUILT, NOT YET RUN): A2's state/has_error/subtype/meaning_changed
    questions, PLUS 5 narrow noul probes on the focus sentence (negation,
    quantity, agent_direction, meaning_omitted, meaning_added), PLUS an
    explicit-acceptable-variation variant of has_error in place of A2's plain
    one. tau / tau_narrow (the narrow-hit threshold that forces an error) are
    NOT applied here -- this only builds the request; score_a3 (score.py,
    not yet written since this arm hasn't been run) is where tau/tau_narrow
    become tunable parameters to fit on silver.
    """
    full_ref_key = R.FULL_REF_KEY[lang]
    full_learner_key = R.FULL_LEARNER_KEY[lang]
    focus_ref_key = R.FOCUS_REF_KEY[lang]
    focus_learner_key = R.FOCUS_LEARNER_KEY[lang]

    state = {
        full_ref_key: reference,
        full_learner_key: reproduction,
        focus_ref_key: focus_ref,
        focus_learner_key: focus_repro,
    }

    he = R.HAS_ERROR_NOUL_VARIANT_ACCEPTABLE_VARIATION[lang]
    mc = R.MEANING_CHANGED_NOUL[lang]
    mc_suffix = R.MEANING_CHANGED_NOUL_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key)
    subtype_suffix = R.SUBTYPE_CHOICE_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key)

    questions = {
        "has_error": {
            "type": "noul",
            # NOTE: this template's {ref_key}/{learner_key} refer to the FULL
            # passage keys (matches A2's convention: has_error is judged
            # against the focus sentence but framed with the full-passage
            # labels the model already has in `state`); the focus-sentence
            # scoping is carried by the suffix, same as A2.
            "instructions": he["instructions"].format(ref_key=full_ref_key, learner_key=full_learner_key)
            + R.HAS_ERROR_NOUL_FOCUS_SUFFIX[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key),
            "criteria": {"true": he["true"], "false": he["false"]},
        },
        "subtype": {
            "type": "choice",
            "instructions": R.SUBTYPE_CHOICE_INSTRUCTION[lang].format(ref_key=full_ref_key, learner_key=full_learner_key) + subtype_suffix,
            "criteria": _subtype_choice_criteria(lang),
        },
        "meaning_changed": {
            "type": "noul",
            "instructions": mc["instructions"].format(ref_key=full_ref_key, learner_key=full_learner_key) + mc_suffix,
            "criteria": {"true": mc["true"], "false": mc["false"]},
        },
    }
    for name, spec in R.NARROW_NOUL.items():
        lang_spec = spec[lang]
        questions[f"narrow_{name}"] = {
            "type": "noul",
            "instructions": lang_spec["instructions"].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key),
            "criteria": {"true": lang_spec["true"], "false": lang_spec["false"]},
        }

    # S2: 3-way severity choice (minor/major/critical + no_error) on the focus
    # sentence -- targets severity directly instead of inferring it from
    # meaning_changed (S1).
    sev_levels = R.SEVERITY_CHOICE_LEVELS[lang]
    questions["severity_choice"] = {
        "type": "choice",
        "instructions": R.SEVERITY_CHOICE_INSTRUCTION[lang].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key),
        "criteria": {
            "minor": sev_levels["minor"],
            "major": sev_levels["major"],
            "critical": sev_levels["critical"],
            "no_error": T.NO_ERROR_OPTION[lang],
        },
    }

    # S4: "would a native reader immediately see this as clearly wrong" noul
    # -- major-vs-not, independent of whether meaning is still recoverable.
    nw = R.NATIVE_WRONG_NOUL[lang]
    questions["native_wrong"] = {
        "type": "noul",
        "instructions": nw["instructions"].format(focus_ref_key=focus_ref_key, focus_learner_key=focus_learner_key),
        "criteria": {"true": nw["true"], "false": nw["false"]},
    }

    return state, questions


# name -> "best-matching v5 subtype" a forced narrow-probe error is tagged
# with (task spec: "subtype = the best-matching v5 subtype, e.g. omission,
# word_choice"). Same taxonomy_data.SUBTYPES vocabulary A1/A2 use.
NARROW_SUBTYPE_MAP = {name: spec["subtype"] for name, spec in R.NARROW_NOUL.items()}


def decode_narrow(answers: dict, name: str) -> float | None:
    return answers.get(f"narrow_{name}", {}).get("noul")


def decode_noul(answers: dict, key: str) -> float | None:
    a = answers.get(key, {})
    return a.get("noul")


def decode_choice(answers: dict, key: str) -> tuple[str | None, float | None, dict | None]:
    a = answers.get(key, {})
    return a.get("choice"), a.get("confidence"), a.get("probabilities")


def decode_score(answers: dict, key: str) -> tuple[float | None, float | None]:
    a = answers.get(key, {})
    return a.get("score"), a.get("confidence")
