# -*- coding: utf-8 -*-
"""Silver-only config search with 5-fold CV (3 seeds). Reports an ablation table
(out-of-fold mean QWK per idea family) and freezes one config per language.
Never reads gold."""
import itertools, json, sys
import lib as L, feats as F, pipeline as P

JEV = "typesafe/jev-1.13"
SRC = {"": (JEV, "en"), "d2": (JEV, "en", "D2"), "n_": (JEV, "l2"),
       "g_": ("google/gemini-decision-1", "en"), "p_": ("perplexity/pplx-decider-v1.2", "en"),
       "q_": ("liquid/d1-ultra", "en"), "j_": ("typesafe/jev-1.14", "en")}
TAUS = (0.3, 0.4, 0.5, 0.6, 0.7)
TAUC = (0.5, 0.7, 0.85)


def grid(dets, subs, crits, sevs, taus=TAUS):
    return [{"det": d, "tau": t, "sub": s, "crit": c, "tau_c": tc, "sev": sv}
            for d, t, s, c, tc, sv in itertools.product(dets, taus, subs, crits, TAUC, sevs)]


FAMILIES = {
    # name: (description, grid)
    "0_sept_frozen": None,  # filled per language
    "1_sept_refit_wider_tau": grid(["S"], ["S"], ["S"], ["prior", "argmaxS"], taus=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)),
    "2_D_only_argmax_sev": grid(["D"], ["D"], ["D"], ["argmaxD"]),
    "3_D_only_prior_sev": grid(["D"], ["D"], ["D"], ["prior"]),
    "4_D_+variant_ok": grid(["Dv"], ["D"], ["D"], ["prior"]),
    "5_D_+paraphrase_ens": grid(["Dtf", "Dall"], ["D"], ["D"], ["prior"]),
    "6_D_+question_lang_ens": grid(["Dl2"], ["D", "ens:,n_"], ["D"], ["prior"]),
    "7_D_+impair_sev": grid(["D", "Dv"], ["D"], ["D"], ["impair", "prior+impair"]),
    "8_D+Sept_combined": grid(["maxDS", "maxDvS", "meanDS"], ["D", "S", "ens"], ["DS"], ["prior", "argmaxS"]),
    "9_multi_model_ens_cheap": grid(["mean:err,p_err,q_err"], ["ens:,p_,q_"], ["D"], ["prior"]),
    "10_jev+gemini": grid(["mean:err,g_err", "mean:g_err"], ["ens:,g_", "ens:g_"], ["D"], ["prior"]),
    "11_jev1.14_D": grid(["mean:j_err"], ["ens:j_"], ["D"], ["prior"]),
}
ALL_JEV = ("2_D_only_argmax_sev", "3_D_only_prior_sev", "4_D_+variant_ok", "5_D_+paraphrase_ens", "7_D_+impair_sev",
           "8_D+Sept_combined")


def sept_cfg(lang):
    c = json.load(open(f"{L.SEPT}/results/frozen_config_{lang}.json"))
    return c


def main():
    out = {}
    for lang in L.LANGS:
        src = dict(SRC)
        if lang == "en":
            src.pop("n_")
        rows = F.table(lang, "silver", src)
        assert all(r["complete"] for r in rows), [r["key"] for r in rows if not r["complete"]]
        meta = L.item_meta(lang, "silver")
        out[lang] = {}
        print(f"== {lang}  items={len(meta)} units={len(rows)}")
        # Sept frozen config re-scored on silver through the Sept code path (in-sample for Sept!)
        c = sept_cfg(lang)
        by = L.SA3.a3_units(lang, "silver"); m2 = L.SA3.item_meta(lang, "silver")
        r0 = L.SA3.score_config_on_items(by, m2, list(by), lang, c["tau"], c["tau_n"], c["tau_c"], c["variant"])
        print(f"  {'0_sept_frozen (in-sample)':28s} full {r0['qwk']['accuracy']:.2f}/{r0['qwk']['fidelity']:.2f}/{r0['qwk']['understandability']:.2f} mean {r0['mean_qwk']:.3f}  (Sept CV mean {c['cv_mean']:.3f})")
        out[lang]["0_sept_frozen"] = {"full": r0["qwk"], "sept_cv_mean": c["cv_mean"]}
        fams = dict(FAMILIES); fams.pop("0_sept_frozen")
        if lang == "en":
            fams.pop("6_D_+question_lang_ens")
        fams["12_all_jev_union"] = [c for k in ALL_JEV for c in fams[k]]
        for name, g in fams.items():
            r = P.cv_select(rows, meta, g)
            full = P.band_qwk(rows, meta, list(meta), r["best"])
            um = P.unit_metrics(rows, r["best"])
            o = r["oof"]
            print(f"  {name:28s} OOF {o['accuracy']:.2f}/{o['fidelity']:.2f}/{o['understandability']:.2f} mean {o['mean']:.3f} | full mean {full['mean']:.3f} exact {full['exact']:.2f} P {um['precision']:.2f} R {um['recall']:.2f} sub {um['subtype_top1']:.2f} sev {um['severity_acc']:.2f} | best {r['best']} (ties {r['n_tied']})")
            out[lang][name] = {"oof": o, "full": full, "unit": um, "best": r["best"], "n_tied": r["n_tied"]}
    json.dump(out, open("results_silver_search.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
