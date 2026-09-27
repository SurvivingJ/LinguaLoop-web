# -*- coding: utf-8 -*-
"""Builds one Jev Decisions API request per gold item: 5 dims x {score,choice}
+ 2 noul error-detection questions = 12 questions in a single request.

`prompt_lang` controls which language the INSTRUCTIONS/CRITERIA/state-field
labels are written in; `content_lang` controls which band-descriptor set and
gold file the item's actual text comes from. For the native-language runs
these are equal. For the English-on-zh/ja control, prompt_lang='en' while
content_lang stays 'zh'/'ja' (band descriptors are still read in English,
per rubric_data.BAND_DESCRIPTORS_*['en'] combined with content_lang's tier).
"""
from __future__ import annotations

import rubric_data as R


def build_request(item: dict, content_lang: str, prompt_lang: str) -> tuple[dict, dict]:
    ref_key = R.REF_KEY[prompt_lang]
    learner_key = R.LEARNER_KEY[prompt_lang]

    state = {
        ref_key: item["reference"],
        learner_key: item["reproduction"],
    }

    questions: dict = {}

    for dim in R.DIMENSIONS:
        dim_label = R.DIMENSION_NAMES[prompt_lang][dim]
        # naturalness band text is tier-varying; tier comes from CONTENT lang
        # (the learner's actual age tier), descriptor language from prompt_lang.
        if dim == "naturalness":
            tier = R.AGE_TIER[content_lang]
            levels = R.BAND_DESCRIPTORS_NATURALNESS[tier][prompt_lang]
        else:
            levels = R.BAND_DESCRIPTORS_INVARIANT[dim][prompt_lang]

        score_instr = R.SCORE_INSTRUCTION_TMPL[prompt_lang].format(
            dim=dim_label, ref_key=ref_key, learner_key=learner_key
        )
        questions[f"score_{dim}"] = {
            "type": "score",
            "instructions": score_instr,
            "criteria": list(levels),  # index 0..3 == band 1..4
        }

        choice_instr = R.CHOICE_INSTRUCTION_TMPL[prompt_lang].format(
            dim=dim_label, ref_key=ref_key, learner_key=learner_key
        )
        questions[f"choice_{dim}"] = {
            "type": "choice",
            "instructions": choice_instr,
            "criteria": {R.CHOICE_LEVEL_KEYS[i]: levels[i] for i in range(4)},
        }

    omission = R.NOUL_OMISSION[prompt_lang]
    questions["noul_omission"] = {
        "type": "noul",
        "instructions": omission["instructions"].format(ref_key=ref_key, learner_key=learner_key),
        "criteria": {"true": omission["true"], "false": omission["false"]},
    }

    grammar = R.NOUL_GRAMMAR[prompt_lang]
    questions["noul_grammar"] = {
        "type": "noul",
        "instructions": grammar["instructions"].format(ref_key=ref_key, learner_key=learner_key),
        "criteria": {"true": grammar["true"], "false": grammar["false"]},
    }

    return state, questions


def decode_answers(answers: dict) -> dict:
    """Turn a Jev `answers` dict into {dim: {"score_band": float|None, "score_conf":...,
    "choice_band": int|None, "choice_conf":...}} plus noul probabilities."""
    out: dict = {"dims": {}, "noul": {}}
    for dim in R.DIMENSIONS:
        s = answers.get(f"score_{dim}", {})
        c = answers.get(f"choice_{dim}", {})
        score_val = s.get("score")
        score_band = None
        if score_val is not None:
            score_band = max(1, min(4, round(float(score_val)) + 1))
        choice_key = c.get("choice")
        choice_band = None
        if choice_key in R.CHOICE_LEVEL_KEYS:
            choice_band = R.CHOICE_LEVEL_KEYS.index(choice_key) + 1
        out["dims"][dim] = {
            "score_raw": score_val,
            "score_band": score_band,
            "score_confidence": s.get("confidence"),
            "score_probabilities": s.get("probabilities"),
            "choice_key": choice_key,
            "choice_band": choice_band,
            "choice_confidence": c.get("confidence"),
            "choice_probabilities": c.get("probabilities"),
        }
    for key in ("noul_omission", "noul_grammar"):
        a = answers.get(key, {})
        out["noul"][key] = a.get("noul")
    return out
