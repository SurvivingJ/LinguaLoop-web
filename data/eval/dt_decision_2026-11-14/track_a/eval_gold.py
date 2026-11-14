# -*- coding: utf-8 -*-
"""ONE-SHOT gold evaluation of the frozen configs (frozen_config.json).
Gold labels are read here only, for scoring."""
import itertools, json, random, statistics, sys
import lib as L, feats as F, pipeline as P
from search import SRC
from freeze import obj_lang
from freeze2 import ROUTE, item_signal

LIVE = {"en": {"accuracy": .778, "fidelity": .487, "understandability": .746},
        "zh": {"accuracy": .570, "fidelity": .891, "understandability": .577},
        "ja": {"accuracy": .412, "fidelity": .371, "understandability": .332}}
OTHER_MODELS = {"pplx-decider-v1.2": "perplexity/pplx-decider-v1.2", "liquid-d1-ultra": "liquid/d1-ultra",
                "gemini-decision-1": "google/gemini-decision-1"}


def paired_boot(yt, ya, yb, n=2000, seed=0):
    """bootstrap CI of QWK(a) - QWK(b) on the same items."""
    rng = random.Random(seed); N = len(yt); ds = []
    for _ in range(n):
        idx = [rng.randrange(N) for _ in range(N)]
        a = L.qwk([yt[i] for i in idx], [ya[i] for i in idx]); b = L.qwk([yt[i] for i in idx], [yb[i] for i in idx])
        if a == a and b == b:
            ds.append(a - b)
    ds.sort()
    return [ds[int(.025 * len(ds))], ds[int(.975 * len(ds))]] if ds else [float("nan")] * 2


def sept_pred(lang):
    c = json.load(open(f"{L.SEPT}/results/frozen_config_{lang}.json"))
    by = L.SA3.a3_units(lang, "gold")
    return {i: L.SA3.predict_item_bands(u, lang, c["tau"], c["tau_n"], c["tau_c"], c["variant"]) for i, u in by.items()}


def evaluate(rows, meta, cfg, lang, sept, cost_keys):
    ids = list(meta)
    pred = P.predict_items(rows, ids, cfg)
    out = {"qwk": {}, "qwk_ci95": {}, "delta_vs_sept": {}, "delta_vs_sept_ci95": {}}
    for d in L.DIMS:
        yt = [meta[i]["bands"][d] for i in ids]; yp = [pred[i][d] for i in ids]; ys = [sept[i][d] for i in ids]
        out["qwk"][d] = L.qwk(yt, yp); out["qwk_ci95"][d] = list(L.bootstrap_ci(yt, yp))
        out["delta_vs_sept"][d] = out["qwk"][d] - L.qwk(yt, ys); out["delta_vs_sept_ci95"][d] = paired_boot(yt, yp, ys)
    out["exact_3dim"] = statistics.mean(all(pred[i][d] == meta[i]["bands"][d] for d in L.DIMS) for i in ids)
    out["within1_all"] = statistics.mean(all(abs(pred[i][d] - meta[i]["bands"][d]) <= 1 for d in L.DIMS) for i in ids)
    out["unit"] = P.unit_metrics(rows, cfg)
    # every gold error counted (not only one per sentence): recall by severity
    by_sev = {}
    for r in rows:
        hit = P.decide(r, cfg) is not None
        for e in r["gold_errors"]:
            b = by_sev.setdefault(e["severity"], [0, 0]); b[1] += 1; b[0] += hit
    out["recall_by_severity"] = {k: {"found": v[0], "n": v[1]} for k, v in by_sev.items()}
    usd = {i: 0.0 for i in ids}; lat = {i: 0.0 for i in ids}
    for r in rows:
        usd[r["item_id"]] += sum(r.get(k, 0.0) for k in cost_keys)
        lat[r["item_id"]] = max(lat[r["item_id"]], max(r.get(k.replace("usd", "lat"), 0.0) for k in cost_keys))
    out["usd_per_item"] = statistics.mean(usd.values()); out["usd_per_item_max"] = max(usd.values())
    out["latency_s_item_median_parallel"] = statistics.median(lat.values())
    out["latency_s_item_p95_parallel"] = sorted(lat.values())[int(.95 * (len(lat) - 1))]
    return out


def routing_eval(rows, meta, name, tau_r):
    sig = item_signal(rows, meta, ROUTE[name])
    routed = [i for i, v in sig.items() if v < tau_r]
    over = [i for i in routed if any(meta[i]["bands"][d] < 4 for d in L.DIMS)]
    two = [i for i in routed if any(meta[i]["bands"][d] <= 2 for d in L.DIMS)]
    has_err = [i for i in routed if any(r["gold_has"] for r in rows if r["item_id"] == i)]
    return {"tau_r": tau_r, "n": len(meta), "n_routed": len(routed), "pct_routed": len(routed) / len(meta),
            "over_graded": over, "two_band_miss": two, "routed_with_any_gold_error": has_err}


def main():
    fz = json.load(open("frozen_config.json"))
    res = {"configs": fz["configs"], "by_lang": {}, "other_models_D_only": {}}
    for lang in L.LANGS:
        src = {k: v for k, v in SRC.items() if k in ("", "d2")}
        rows = F.table(lang, "gold", src, verbose=True)
        assert all(r["complete"] for r in rows), [r["key"] for r in rows if not r["complete"]]
        sept_rows = {r["job_key"]: r for r in L.S.load_responses("A3", lang, "gold") if r.get("ok")}
        for r in rows:
            r["_usdS"] = float(sept_rows[r["key"]]["usage"].get("cost", 0)); r["_latS"] = sept_rows[r["key"]]["latency_s"]
        meta = L.item_meta(lang, "gold"); sept = sept_pred(lang)
        R = {"n_items": len(meta), "n_units": len(rows), "live": LIVE[lang]}
        ids = list(meta)
        R["sept_frozen"] = {"qwk": {d: L.qwk([meta[i]["bands"][d] for i in ids], [sept[i][d] for i in ids]) for d in L.DIMS},
                            "usd_per_item": sum(r["_usdS"] for r in rows) / len(meta)}
        ck = {"A_fused": ("_usd", "_usd2", "_usdS"), "A_fused_prior": ("_usd", "_usd2", "_usdS"), "A_sept_refit": ("_usdS",),
              "A_D_only": ("_usd",)}
        for name, cfg in fz["configs"].items():
            R[name] = evaluate(rows, meta, cfg, lang, sept, ck[name])
        R["routing"] = {n: routing_eval(rows, meta, n, fz["routing"][lang][n]["tau_r"]) for n in ROUTE}
        res["by_lang"][lang] = R
        # other decision models, single-call D-only; thresholds fitted on that model's own silver
        for short, mid in OTHER_MODELS.items():
            srows = F.table(lang, "silver", {"": (mid, "en")}); smeta = L.item_meta(lang, "silver")
            res["other_models_D_only"].setdefault(short, {"silver_rows": {}, "gold_rows": {}})
            res["other_models_D_only"][short]["silver_rows"][lang] = (srows, smeta)
            grows = F.table(lang, "gold", {"": (mid, "en")}, verbose=True)
            assert all(r["complete"] for r in grows)
            res["other_models_D_only"][short]["gold_rows"][lang] = (grows, meta, sept)
    GD = [{"det": "D", "tau": t, "sub": "D", "crit": "D", "tau_c": tc, "sev": "prior"}
          for t, tc in itertools.product((0.3, 0.4, 0.5, 0.6), (0.6, 0.7, 0.8))]
    for short, d in res["other_models_D_only"].items():
        best = max(GD, key=lambda c: statistics.mean(obj_lang(d["silver_rows"][l][0], d["silver_rows"][l][1], list(d["silver_rows"][l][1]), c) for l in L.LANGS))
        o = {"config_fit_on_own_silver": best, "by_lang": {}}
        for l in L.LANGS:
            grows, meta, sept = d["gold_rows"][l]
            o["by_lang"][l] = evaluate(grows, meta, best, l, sept, ("_usd",))
        res["other_models_D_only"][short] = o
    res["spend_usd_ledger"] = L.ledger_total()
    json.dump(res, open("results_gold_full.json", "w"), indent=1, default=str)
    # ---- print
    for lang in L.LANGS:
        R = res["by_lang"][lang]
        print(f"\n=== {lang} gold (n={R['n_items']} items, {R['n_units']} units)")
        print(f"  {'live grader':16s} acc {R['live']['accuracy']:.3f} fid {R['live']['fidelity']:.3f} und {R['live']['understandability']:.3f}")
        s = R["sept_frozen"]["qwk"]; print(f"  {'sept jev frozen':16s} acc {s['accuracy']:.3f} fid {s['fidelity']:.3f} und {s['understandability']:.3f}  ${R['sept_frozen']['usd_per_item']:.5f}/item")
        rowsets = [(n, R[n]) for n in fz["configs"]] + [(f"{k} D-only", v["by_lang"][lang]) for k, v in res["other_models_D_only"].items()]
        for n, e in rowsets:
            q = e["qwk"]; c = e["qwk_ci95"]; u = e["unit"]
            print(f"  {n:26s} acc {q['accuracy']:.3f} [{c['accuracy'][0]:.2f},{c['accuracy'][1]:.2f}] fid {q['fidelity']:.3f} [{c['fidelity'][0]:.2f},{c['fidelity'][1]:.2f}] und {q['understandability']:.3f} [{c['understandability'][0]:.2f},{c['understandability'][1]:.2f}]"
                  f" | ex {e['exact_3dim']:.2f} P {u['precision']:.2f} R {u['recall']:.2f} (fn {u['fn']}, minor {u['missed_minor']}) AUC {u['auc']:.3f} sub@1 {u['subtype_top1']:.2f} sev {u['severity_acc']:.2f} | ${e['usd_per_item']:.5f}/item lat {e['latency_s_item_median_parallel']:.2f}s")
        for n, r in R["routing"].items():
            print(f"  routing[{n}] tau_r={r['tau_r']}: routed {r['n_routed']}/{r['n']} over-graded {len(r['over_graded'])} two-band {len(r['two_band_miss'])} routed-with-any-error {len(r['routed_with_any_gold_error'])}")
    print("\nledger total $", round(L.ledger_total(), 5))


if __name__ == "__main__":
    main()
