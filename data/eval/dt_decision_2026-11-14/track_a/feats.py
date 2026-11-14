# -*- coding: utf-8 -*-
"""Feature tables: one row per unit with probabilities from arm D (any model /
variant) and from the cached Sept A3 responses."""
from __future__ import annotations

import lib as L
import reqs as RQ
from collect import collect

SEVS = ("none", "minor", "major", "critical")


def d_features(ans: dict, lang: str, prefix: str = "") -> dict:
    f = {}
    for k in RQ.NOUL_KEYS:
        v = (ans.get(k) or {}).get("noul")
        f[prefix + k] = float(v) if v is not None else 0.0
    sp = (ans.get("severity") or {}).get("probabilities") or {}
    for s in SEVS:
        f[prefix + "sev_" + s] = float(sp.get(s, 0) or 0)
    sub = (ans.get("subtype") or {}).get("probabilities") or {}
    f[prefix + "sub_noerr"] = float(sub.get("no_error", 0) or 0)
    f[prefix + "_subprobs"] = {k: float(v or 0) for k, v in sub.items()}
    return f


def sept_features(ans: dict) -> dict:
    g = lambda k: float((ans.get(k) or {}).get("noul") or 0.0)
    f = {"s_err": g("has_error"), "s_mc": g("meaning_changed"), "s_nw": g("native_wrong")}
    for n in ("negation", "quantity", "agent_direction", "meaning_omitted", "meaning_added"):
        f["s_n_" + n] = g("narrow_" + n)
    sp = (ans.get("severity_choice") or {}).get("probabilities") or {}
    for s in ("no_error", "minor", "major", "critical"):
        f["s_sev_" + ("none" if s == "no_error" else s)] = float(sp.get(s, 0) or 0)
    sub = (ans.get("subtype") or {}).get("probabilities") or {}
    f["s__subprobs"] = {k: float(v or 0) for k, v in sub.items()}
    return f


def table(lang: str, set_name: str, sources: dict[str, tuple[str, str]] | None = None, with_sept: bool = True,
          verbose: bool = False) -> list[dict]:
    """sources: prefix -> (model, variant). Default: {"": (jev-1.13, en)}."""
    sources = sources or {"": ("typesafe/jev-1.13", "en")}
    units = L.build_units(lang, set_name)
    res = {p: collect(v[0], v[1], lang, set_name, verbose=verbose, arm=(v[2] if len(v) > 2 else "D"))
           for p, v in sources.items()}
    sept = L.sept_a3_answers(lang, set_name) if with_sept else {}
    rows = []
    for u in units:
        row = dict(u)
        ok = True
        for p, r in res.items():
            v = sources[p]
            if u["key"] not in r:
                ok = False
                break
            if not (len(v) > 2 and v[2] == "D2"):
                row.update(d_features(r[u["key"]]["answers"], lang, p))
            if isinstance(v, tuple) and len(v) > 2 and v[2] == "D2":
                for kk in RQ.D2_EN:
                    row[kk] = float((r[u["key"]]["answers"].get(kk) or {}).get("noul") or 0.0)
                row["_usd2"] = r[u["key"]]["usd"]
                row["_lat2"] = r[u["key"]]["latency_s"]
                continue
            row[p + "_usd"] = r[u["key"]]["usd"]
            row[p + "_lat"] = r[u["key"]]["latency_s"]
        if with_sept:
            if u["key"] in sept:
                row.update(sept_features(sept[u["key"]]["answers"]))
            else:
                ok = False
        row["complete"] = ok
        rows.append(row)
    return rows
