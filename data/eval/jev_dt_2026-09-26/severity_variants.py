# -*- coding: utf-8 -*-
"""Pluggable severity operationalisations for A2/A3, built per the
coordinator's correction: gold MQM "major" != "meaning changed" (major =
clearly wrong to a native reader / noticeably impairs the sentence, even
when the intended meaning is still recoverable; only "critical" implies the
meaning itself is lost/inverted/misleading).

Each Sx function takes ONE unit's raw A2/A3 `answers` dict (plus, where
needed, the jev-picked subtype and tunable thresholds) and returns a
severity string in {"minor","major","critical"}. All are pure -- no I/O,
no API calls -- so they can be applied identically whether replaying cached
gold responses (diagnostic only, per the coordinator's "no tuning on gold"
rule) or the future silver responses (where tau/tau_n/tau_c are meant to be
fit, via 5-fold CV, once silver/*_final3.json exists).

S1 requires only A2's existing `meaning_changed` question (works on already-
cached A2 gold/silver responses). S2/S4 require A3's new `severity_choice`/
`native_wrong` questions (A3 has not been run anywhere yet). S3 requires
only `subtype` (present in A2) plus `meaning_changed` for its critical
promotion, so it also already works on cached A2 responses.
"""
from __future__ import annotations

import reqbuild as REQ
import taxonomy_data as T

SEVERITY_LEVELS = ("minor", "major", "critical")


def s1_meaning_changed(answers: dict, tau_major: float = 0.5) -> str:
    """Baseline (score.py's severity_major_minor): major if meaning_changed
    p >= tau_major else minor. Never emits "critical" -- kept as the
    pre-correction reference point, not a recommended variant."""
    p = REQ.decode_noul(answers, "meaning_changed")
    p = p if p is not None else 0.0
    return "major" if p >= tau_major else "minor"


def s2_argmax(answers: dict) -> str:
    """3-way choice (A3 `severity_choice`), argmax over minor/major/critical,
    excluding the "no_error" option from contention (same convention as the
    subtype argmax: a real severity level is always returned)."""
    _, _, probs = REQ.decode_choice(answers, "severity_choice")
    if not probs:
        return "minor"
    best, best_p = "minor", -1.0
    for lvl in SEVERITY_LEVELS:
        p = probs.get(lvl, 0.0) or 0.0
        if p > best_p:
            best, best_p = lvl, p
    return best


def s2_threshold(answers: dict, tau_major: float = 0.3, tau_critical: float = 0.6) -> str:
    """3-way choice (A3 `severity_choice`), via tunable expected-severity
    thresholds on the probability mass rather than a bare argmax: critical
    if P(critical) >= tau_critical; else major if P(major)+P(critical) >=
    tau_major; else minor. tau_major/tau_critical are meant to be fit on
    silver (5-fold CV), not gold."""
    _, _, probs = REQ.decode_choice(answers, "severity_choice")
    if not probs:
        return "minor"
    p_major = probs.get("major", 0.0) or 0.0
    p_critical = probs.get("critical", 0.0) or 0.0
    if p_critical >= tau_critical:
        return "critical"
    if (p_major + p_critical) >= tau_major:
        return "major"
    return "minor"


def s3_prior(subtype: str | None, answers: dict, tau_c: float = 0.9) -> str:
    """Python prior only: taxonomy_data.SUBTYPE_DEFAULT_SEVERITY[subtype]
    (from migrations/dt_taxonomy_v5_seed.sql subtype_meta.default_severity),
    promoted to critical when meaning_changed p >= tau_c. Needs no new A3
    question -- works off A2's existing subtype + meaning_changed answers,
    or off jev/oracle subtype in the decomposition harness."""
    base = T.SUBTYPE_DEFAULT_SEVERITY.get(subtype, "minor") if subtype else "minor"
    p = REQ.decode_noul(answers, "meaning_changed")
    p = p if p is not None else 0.0
    if p >= tau_c:
        return "critical"
    return base


def s4_native_wrong(answers: dict, tau_c: float = 0.9) -> str:
    """A3 `native_wrong` noul -> major if fired, else minor; meaning_changed
    p >= tau_c promotes to critical (same promotion rule as S3, so S3 vs S4
    isolates "subtype prior" vs "explicit native-judgment" as the major
    signal, independent of the critical-promotion mechanism)."""
    wrong_p = REQ.decode_noul(answers, "native_wrong")
    wrong_p = wrong_p if wrong_p is not None else 0.0
    mc_p = REQ.decode_noul(answers, "meaning_changed")
    mc_p = mc_p if mc_p is not None else 0.0
    if mc_p >= tau_c:
        return "critical"
    return "major" if wrong_p >= 0.5 else "minor"


VARIANTS = {
    "S1_meaning_changed": s1_meaning_changed,
    "S2_argmax": s2_argmax,
    "S2_threshold": s2_threshold,
    "S3_prior": s3_prior,
    "S4_native_wrong": s4_native_wrong,
}
