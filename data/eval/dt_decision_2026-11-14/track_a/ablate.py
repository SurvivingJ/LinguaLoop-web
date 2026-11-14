# -*- coding: utf-8 -*-
"""Silver-only side analyses: detection-score AUCs (ensembles) and whether a small
fitted model can separate major from minor (severity)."""
import json, statistics, warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
import lib as L, feats as F, pipeline as P
from search import SRC
warnings.filterwarnings("ignore")
out = {"detection_auc": {}, "severity": {}}
rows_all = {}
for lang in L.LANGS:
    src = dict(SRC)
    if lang == "en": src.pop("n_")
    rows_all[lang] = F.table(lang, "silver", src)
modes = {"Sept has_error (S)": "S", "D err": "D", "D err x variant_ok (Dv)": "Dv", "D 2-paraphrase mean (Dtf)": "Dtf",
         "D 3-paraphrase mean (Dall)": "Dall", "D EN+L2 question mean (Dl2)": "Dl2", "mean(D,S)": "meanDS", "max(D,S)": "maxDS",
         "3 cheap models mean (jev,pplx,liquid)": "mean:err,p_err,q_err", "jev+gemini mean": "mean:err,g_err",
         "gemini alone": "mean:g_err", "jev-1.14 alone": "mean:j_err"}
print(f"{'detection score':40s} " + "  ".join(f"{l}:AUC  R@P>=.95" for l in L.LANGS))
for name, m in modes.items():
    cells = []
    out["detection_auc"][name] = {}
    for lang in L.LANGS:
        rows = rows_all[lang]
        if m == "Dl2" and lang == "en":
            cells.append("   -        -  "); continue
        y = [r["gold_has"] for r in rows]; s = [P.det_score(r, m) for r in rows]
        a = L.auc(y, s)
        best = 0.0
        for t in sorted(set(s)):
            tp = sum(1 for yy, ss in zip(y, s) if yy and ss >= t); fp = sum(1 for yy, ss in zip(y, s) if not yy and ss >= t)
            if tp and tp / (tp + fp) >= 0.95: best = max(best, tp / sum(y))
        out["detection_auc"][name][lang] = {"auc": a, "recall_at_p95": best}
        cells.append(f"  {a:.3f}   {best:.2f}  ")
    print(f"{name:40s} " + "  ".join(cells))
# severity: major-or-worse vs minor among gold-positive, non-critical units (pooled languages)
pos = [r for l in L.LANGS for r in rows_all[l] if r["gold_has"] and r["gold_sev"] in ("minor", "major")]
y = np.array([r["gold_sev"] == "major" for r in pos], dtype=int)
print(f"\nseverity (major vs minor), pooled silver non-critical positives n={len(pos)}, major={int(y.sum())}")
single = {}
for k in ("clear_wrong", "impair", "sev_major", "s_nw", "s_sev_major", "flip", "s_mc", "fwd", "gram"):
    single[k] = L.auc(list(y.astype(bool)), [r[k] for r in pos]); print(f"  AUC {k:12s} {single[k]:.3f}")
feat = ["clear_wrong", "impair", "sev_major", "sev_minor", "flip", "fwd", "gram", "s_nw", "s_mc", "s_sev_major"]
X = np.array([[r[k] for k in feat] for r in pos])
pred = np.zeros(len(pos)); 
for tr, te in LeaveOneOut().split(X):
    m = LogisticRegression(C=1.0, max_iter=1000).fit(X[tr], y[tr]); pred[te] = m.predict_proba(X[te])[:, 1]
acc_lr = float(((pred >= .5) == y).mean()); auc_lr = L.auc(list(y.astype(bool)), list(pred))
prior_gold_sub = float(np.mean([(P.PRIOR.get(r["gold_subtype"], "minor") == "major") == bool(t) for r, t in zip(pos, y)]))
prior_pred_sub = float(np.mean([(P.PRIOR.get(P.top_subtype(r, r["lang"], "S"), "minor") == "major") == bool(t) for r, t in zip(pos, y)]))
# prior + probabilities
X2 = np.array([[r[k] for k in feat] + [float(P.PRIOR.get(P.top_subtype(r, r["lang"], "S"), "minor") == "major")] for r in pos])
pred2 = np.zeros(len(pos))
for tr, te in LeaveOneOut().split(X2):
    m = LogisticRegression(C=1.0, max_iter=1000).fit(X2[tr], y[tr]); pred2[te] = m.predict_proba(X2[te])[:, 1]
acc_lr2 = float(((pred2 >= .5) == y).mean())
print(f"  LOO logistic on 10 jev probabilities: acc {acc_lr:.3f} AUC {auc_lr:.3f}   (majority baseline {max(y.mean(), 1 - y.mean()):.3f})")
print(f"  taxonomy prior, predicted subtype: acc {prior_pred_sub:.3f} | prior with gold subtype (ceiling of the rule): {prior_gold_sub:.3f}")
print(f"  LOO logistic on probabilities + prior flag: acc {acc_lr2:.3f}")
out["severity"] = {"n": len(pos), "single_feature_auc": single, "loo_logistic_acc": acc_lr, "loo_logistic_auc": auc_lr,
                   "majority_baseline": float(max(y.mean(), 1 - y.mean())), "prior_pred_subtype_acc": prior_pred_sub,
                   "prior_gold_subtype_acc": prior_gold_sub, "loo_logistic_plus_prior_acc": acc_lr2}
json.dump(out, open("results_ablations_silver.json", "w"), indent=1)
