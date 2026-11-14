# -*- coding: utf-8 -*-
"""Send (or load from cache) arm-D requests.

    python collect.py --model typesafe/jev-1.13 --variant en --sets silver --langs zh ja en [--limit 5]
"""
from __future__ import annotations

import argparse
import json
import statistics

import lib as L
import reqs as RQ


def collect(model: str, variant: str, lang: str, set_name: str, limit: int | None = None, verbose=True, arm: str = "D") -> dict[str, dict]:
    units = L.build_units(lang, set_name)
    if limit:
        units = units[:limit]
    jobs = []
    for u in units:
        st, q = RQ.BUILDERS[arm](u, variant)
        jobs.append((model, st, q, f"{arm}_{variant}/{lang}/{set_name}"))
    res = L.run_jobs(jobs)
    out = {}
    nerr = 0
    new = [r for r in res if r.get("ok") and not r.get("cached")]
    for u, r in zip(units, res):
        if r.get("ok"):
            out[u["key"]] = r
        else:
            nerr += 1
            if verbose and nerr <= 3:
                print("  FAIL", u["key"], r.get("error"))
    if verbose:
        usd = sum(r["usd"] for r in new)
        lat = [r["latency_s"] for r in res if r.get("ok")]
        print(f"[{model} {arm}_{variant} {lang}/{set_name}] units={len(units)} ok={len(out)} new={len(new)} err={nerr} "
              f"new_usd=${usd:.5f} med_lat={statistics.median(lat) if lat else float('nan'):.2f}s "
              f"ledger=${L.ledger_total():.4f}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="typesafe/jev-1.13")
    ap.add_argument("--variant", default="en")
    ap.add_argument("--sets", nargs="+", default=["silver"])
    ap.add_argument("--langs", nargs="+", default=list(L.LANGS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--arm", default="D")
    a = ap.parse_args()
    for s in a.sets:
        for l in a.langs:
            out = collect(a.model, a.variant, l, s, a.limit, arm=a.arm)
            if a.show:
                for k, r in list(out.items())[:2]:
                    print(k, json.dumps(r["answers"], ensure_ascii=False)[:900], r["usage"])
