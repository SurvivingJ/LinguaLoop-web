# -*- coding: utf-8 -*-
import json
import math
import numpy as np
from collections import defaultdict

def roc_auc(scores, labels):
    """labels: 1=positive class. scores: higher = more likely positive.
    Mann-Whitney U based AUC, handles ties. Returns None if one class empty."""
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return None
    all_scores = np.array(scores)
    ranks = np.argsort(np.argsort(all_scores)) + 1  # average-tie-free ranks; fix ties below
    # proper tie handling via scipy-free rankdata
    order = np.argsort(all_scores, kind="mergesort")
    ranks_arr = np.empty(len(all_scores), dtype=float)
    sorted_scores = all_scores[order]
    i = 0
    n = len(sorted_scores)
    while i < n:
        j = i
        while j < n - 1 and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        ranks_arr[order[i:j + 1]] = avg_rank
        i = j + 1
    labels_arr = np.array(labels)
    r_pos = ranks_arr[labels_arr == 1].sum()
    n_pos, n_neg = len(pos), len(neg)
    auc = (r_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)

def best_threshold_accuracy(scores, labels):
    """Grid-search threshold in [0,1] step .02 maximizing accuracy (score>=t -> predict 1)."""
    best_t, best_acc = 0.5, 0.0
    for t in np.arange(0.0, 1.01, 0.02):
        preds = [1 if s >= t else 0 for s in scores]
        acc = sum(p == l for p, l in zip(preds, labels)) / len(labels)
        if acc > best_acc:
            best_acc, best_t = acc, t
    return float(best_t), float(best_acc)

def prec_recall_at(scores, labels, threshold=0.5):
    preds = [1 if s >= threshold else 0 for s in scores]
    tp = sum(p == 1 and l == 1 for p, l in zip(preds, labels))
    fp = sum(p == 1 and l == 0 for p, l in zip(preds, labels))
    fn = sum(p == 0 and l == 1 for p, l in zip(preds, labels))
    tn = sum(p == 0 and l == 0 for p, l in zip(preds, labels))
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    acc = (tp + tn) / len(labels)
    return dict(threshold=threshold, precision=prec, recall=rec, accuracy=acc, tp=tp, fp=fp, fn=fn, tn=tn)

def cohens_kappa(a_labels, b_labels, categories=None):
    """a_labels/b_labels: parallel lists of category labels (same items)."""
    if categories is None:
        categories = sorted(set(a_labels) | set(b_labels))
    n = len(a_labels)
    if n == 0:
        return None
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    conf = np.zeros((k, k))
    for a, b in zip(a_labels, b_labels):
        conf[idx[a], idx[b]] += 1
    po = np.trace(conf) / n
    row_marg = conf.sum(axis=1) / n
    col_marg = conf.sum(axis=0) / n
    pe = float((row_marg * col_marg).sum())
    if pe == 1.0:
        return 1.0
    return float((po - pe) / (1 - pe))

def pearson(a, b):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])

def percentile(vals, p):
    if not vals:
        return None
    return float(np.percentile(vals, p))

# ---------------------------------------------------------------------------
# axes_to_verdict reimplementation (services/test_generation/schemas.py),
# used to derive a jev-side verdict from jev's fit/confusability scores so it
# can be compared to the live judge's stored verdict on identical content.
FIT_REJECT_MAX = 2
REVIEW_BAND = 3
CONFUSABILITY_ALSO_CORRECT = 5
CONFUSABILITY_INERT_MAX = 1
_RANK = {"reject": 0, "flag": 1, "accept": 2}

def fit_to_verdict(fit):
    if fit is None:
        return "accept"
    if fit <= FIT_REJECT_MAX:
        return "reject"
    if fit == REVIEW_BAND:
        return "flag"
    return "accept"

def confusability_to_verdict(conf):
    if conf is None:
        return "accept"
    if conf >= CONFUSABILITY_ALSO_CORRECT:
        return "reject"
    if conf == REVIEW_BAND:
        return "flag"
    if conf <= CONFUSABILITY_INERT_MAX:
        return "flag"
    return "accept"

def axes_to_verdict(fit, conf):
    vf, vc = fit_to_verdict(fit), confusability_to_verdict(conf)
    return min([vf, vc], key=lambda v: _RANK[v])

if __name__ == "__main__":
    # quick self-test of roc_auc against a known case
    s = [0.9, 0.8, 0.7, 0.6, 0.4, 0.3, 0.2, 0.1]
    l = [1, 1, 1, 0, 1, 0, 0, 0]
    print("auc sanity", roc_auc(s, l))
