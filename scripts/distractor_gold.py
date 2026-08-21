"""Pure logic for the distractor-plausibility gold set (TASK-726).

Split out of the two CLIs that use it -- `build_distractor_gold_frame.py`
(sample, pre-rate, emit the unlabelled frame) and `measure_judge_flag_rate.py
--gold` (score an arm against the adjudicated file) -- so the statistics are
unit-testable without a database or a paid LLM call.

THE THREE THINGS THIS MODULE EXISTS TO GET RIGHT
------------------------------------------------
1. **Reweighting.** The frame is stratified uniformly by question type (10
   questions per type per language) because a per-type estimate needs a usable
   n in every cell. Production is NOT uniform -- `vocabulary_context` is ~30%
   of live questions and `supporting_detail` ~5%. A raw rate off this frame is
   therefore a rate for a question mix that does not exist. Every published
   number goes through `frame_weight`, which post-stratifies each item back to
   its language's production share, and (when the adjudication set is a subset
   of the frame) divides by the item's selection probability.

2. **Disagreement enrichment is a bias, not a bonus.** Pre-rating with two
   judge models and force-including every disagreement concentrates the
   adjudicator's time where it buys signal, but it oversamples exactly the
   items a judge is most likely to get wrong. An unweighted rate off such a set
   is biased high and reads as a regression. `assign_frame_weights` divides it
   back out; `selection_prob` is stored per item so the correction is auditable
   rather than implicit.

3. **The two axes stay two axes.** `topical_distance` and `confusable` are
   never collapsed into one field here. The entire finding of
   `distractor-judge-language-divergence-2026-08-16` §3 is that the live 1-5
   bands conflate them, and a gold set that repeats the conflation cannot
   arbitrate TASK-719. `gold_reject` combines them only at the moment a
   *verdict* is needed, and says so explicitly.

VOCABULARY
----------
* **item** -- one distractor of one question. The unit of adjudication.
* **frame** -- every item drawn, pre-rated, and eligible for adjudication.
* **selected** -- the items actually sent to an adjudicator.
* **stratum** -- a (language, type_code) cell.
* **overlap slice** -- items deliberately labelled twice, by two independent
  labellers, so Cohen's kappa can be computed.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

LANG_NAME = {1: 'zh', 2: 'en', 3: 'ja'}

# Gold label vocabularies. Kept here rather than in the labelling guide's prose
# so the loader can reject a typo'd label instead of silently scoring it as a
# category of its own.
TOPICAL_DISTANCE = ('on-topic', 'related', 'unrelated')
CONFUSABLE = ('yes', 'borderline', 'no')

# Verdict bands as `LIKERT_TO_VERDICT` defines them, restated as an ordered
# grouping so band-level reporting does not have to invert a dict.
BANDS = (1, 2, 3, 4, 5)
BAND_VERDICT = {1: 'reject', 2: 'reject', 3: 'flag', 4: 'accept', 5: 'accept'}


# ------------------------------------------------------------------- frame build


def explode_items(rows: Iterable[dict]) -> list[dict]:
    """One frame item per distractor, carrying the context a labeller needs.

    `item_id` is `<qid>#<index>` so an adjudicated file can be re-joined to the
    frame after a round trip through a spreadsheet, which is how the labelling
    is actually going to happen.
    """
    items: list[dict] = []
    for r in rows:
        for i, d in enumerate(r['distractors']):
            items.append({
                'item_id': f"{r['qid']}#{i}",
                'qid': r['qid'],
                'lang': r['lang'],
                'lang_code': LANG_NAME[r['lang']],
                'type_code': r['type_code'],
                'difficulty': r.get('difficulty'),
                'passage': r['passage'],
                'question': r['question'],
                'answer': r['answer'],
                'distractor': d,
                'distractor_index': i,
            })
    return items


def stratum(item: dict) -> tuple[int, str]:
    return (item['lang'], item['type_code'])


def disagreement(a: int | None, b: int | None) -> tuple[bool, str | None]:
    """Do two pre-rating arms disagree about one distractor?

    Two kinds, both recorded, because they mean different things:

    * `verdict` -- the arms land in different accept/flag/reject buckets. This
      is the disagreement that actually changes what production does with the
      item, and it is the TASK-718 finding in miniature (two models, disjoint
      reject sets).
    * `rating` -- same bucket, two or more bands apart. Under the current band
      map this is unreachable (no verdict band spans three ratings), and
      `test_rating_gap_within_one_verdict_band_is_a_rating_disagreement` pins
      that it stays unreachable. It is kept because TASK-719 may re-cut the
      bands, and a re-cut that widens one would otherwise silently start
      calling a two-band gap agreement.

    A missing rating from either arm counts as a disagreement: an item one
    model refused to rate is precisely the kind the gold set should cover, and
    treating it as agreement would quietly drop it.
    """
    if a is None or b is None:
        return (True, 'unrated')
    if BAND_VERDICT.get(int(a)) != BAND_VERDICT.get(int(b)):
        return (True, 'verdict')
    if abs(int(a) - int(b)) >= 2:
        return (True, 'rating')
    return (False, None)


def select_for_adjudication(
    items: Sequence[dict],
    per_lang: int | None,
    rng: random.Random,
) -> None:
    """Mark which items go to an adjudicator; record the selection probability.

    `per_lang=None` selects the whole frame -- the honest default when the
    frame is already sized to the adjudication budget, and the case in which
    enrichment does nothing and `selection_prob` is 1.0 throughout.

    Otherwise every disagreement is force-included and the remainder is filled
    at random, per the TASK-726 construction plan. The fill probability is
    stored on each *eligible* item (selected or not) so the weight is
    reconstructible from the file alone.
    """
    by_lang: dict[int, list[dict]] = defaultdict(list)
    for it in items:
        by_lang[it['lang']].append(it)

    for lang, pool in by_lang.items():
        if per_lang is None or per_lang >= len(pool):
            for it in pool:
                it['selected'] = True
                it['selection_prob'] = 1.0
                it['disagreement_selected'] = bool(it.get('disagreement'))
            continue

        forced = [it for it in pool if it.get('disagreement')]
        rest = [it for it in pool if not it.get('disagreement')]
        n_fill = max(0, per_lang - len(forced))
        # Disagreements alone can overrun the budget. Trimming them at random
        # keeps the design describable (a known probability per item) rather
        # than "the first N we happened to pre-rate".
        if n_fill == 0 and len(forced) > per_lang:
            rng.shuffle(forced)
            keep = set(id(x) for x in forced[:per_lang])
            p_forced = per_lang / len(forced)
            for it in forced:
                it['selected'] = id(it) in keep
                it['selection_prob'] = p_forced
                it['disagreement_selected'] = it['selected']
            for it in rest:
                it['selected'] = False
                it['selection_prob'] = 0.0
                it['disagreement_selected'] = False
            continue

        rng.shuffle(rest)
        chosen = set(id(x) for x in rest[:n_fill])
        p_fill = (n_fill / len(rest)) if rest else 0.0
        for it in forced:
            it['selected'] = True
            it['selection_prob'] = 1.0
            it['disagreement_selected'] = True
        for it in rest:
            it['selected'] = id(it) in chosen
            it['selection_prob'] = p_fill
            it['disagreement_selected'] = False


def assign_frame_weights(
    items: Sequence[dict],
    production_shares: dict[tuple[int, str], float],
) -> None:
    """Post-stratify the selected items back to the production question mix.

    weight = (production share of the stratum / selected share of the stratum)
             * 1 / selection_prob

    then normalised so the mean weight within a language is 1.0. Normalisation
    is cosmetic -- every consumer computes ratios -- but it makes a stray
    weight visible by eye in the file, which an unnormalised one is not.

    A stratum with production share 0 (a type that language never generates)
    gets weight 0: it is in the frame by construction, not by production, and
    including it would inflate a rate with questions production never asks.
    """
    sel = [it for it in items if it.get('selected')]
    by_lang: dict[int, list[dict]] = defaultdict(list)
    for it in sel:
        by_lang[it['lang']].append(it)

    for lang, pool in by_lang.items():
        counts = Counter(stratum(it) for it in pool)
        n = len(pool)
        raw: list[float] = []
        for it in pool:
            share_frame = counts[stratum(it)] / n
            share_prod = production_shares.get(stratum(it), 0.0)
            p = it.get('selection_prob') or 1.0
            raw.append((share_prod / share_frame) / p if share_frame else 0.0)
        mean = sum(raw) / len(raw) if raw else 0.0
        for it, w in zip(pool, raw):
            it['frame_weight'] = round(w / mean, 6) if mean else 0.0

    for it in items:
        if not it.get('selected'):
            it['frame_weight'] = 0.0


def pick_overlap_slice(
    items: Sequence[dict],
    per_lang: int,
    rng: random.Random,
) -> None:
    """Mark `per_lang` selected items per language for double labelling.

    Spread proportionally across strata and across the disagreement flag, so
    kappa is not computed entirely on the easy agreement items (which would
    flatter it) nor entirely on the disputed ones (which would deflate it).
    """
    for it in items:
        it['overlap_slice'] = False
    by_lang: dict[int, list[dict]] = defaultdict(list)
    for it in items:
        if it.get('selected'):
            by_lang[it['lang']].append(it)

    for lang, pool in by_lang.items():
        buckets: dict[Any, list[dict]] = defaultdict(list)
        for it in pool:
            buckets[(it['type_code'], bool(it.get('disagreement')))].append(it)
        for b in buckets.values():
            rng.shuffle(b)
        # Round-robin across buckets until the quota is met: proportional
        # without needing a largest-remainder pass.
        order = sorted(buckets, key=lambda k: (-len(buckets[k]), str(k)))
        taken = 0
        while taken < min(per_lang, len(pool)):
            progressed = False
            for key in order:
                if not buckets[key]:
                    continue
                buckets[key].pop()['overlap_slice'] = True
                taken += 1
                progressed = True
                if taken >= min(per_lang, len(pool)):
                    break
            if not progressed:
                break


# ------------------------------------------------------------------- gold labels


def primary_label(item: dict) -> dict | None:
    """The label a rate is computed from when an item was labelled twice.

    The first entry, which `build_distractor_gold_frame.py` documents as the
    primary labeller's. Deliberately not an average: `confusable` is ordinal
    with a meaningful middle, and averaging two labellers into a synthetic
    `borderline` would invent an agreement neither of them expressed.
    """
    labels = item.get('labels') or []
    return labels[0] if labels else None


def gold_reject(label: dict | None) -> bool | None:
    """Should the judge have rejected this distractor, per the adjudicator?

    The two axes are kept separate everywhere else; this is the one place they
    combine, and only because a *verdict* is a single decision:

    * `also_correct` -- a second right answer. Rejected regardless of topic.
    * `confusable == 'no'` -- nothing a learner would ever pick. Rejected.
    * `confusable == 'borderline'` -- returns None, i.e. excluded from the
      binary metrics rather than forced to a side. This is what the review band
      exists for (TASK-720), and coercing it would erase the very population
      that task is about.
    """
    if not label:
        return None
    if label.get('also_correct') is True:
        return True
    c = label.get('confusable')
    if c == 'no':
        return True
    if c == 'yes':
        return False
    return None


def labelled_items(items: Iterable[dict]) -> list[dict]:
    return [it for it in items if primary_label(it) is not None]


# ---------------------------------------------------------------------- metrics


def cohens_kappa(pairs: Sequence[tuple[Any, Any]], categories: Sequence[Any]) -> float | None:
    """Unweighted Cohen's kappa over a list of (labeller A, labeller B) pairs.

    Returns None for fewer than two pairs. Returns 1.0 when both labellers used
    a single identical category on every item -- expected agreement is then 1
    and kappa is 0/0; reporting "perfect but uninformative" as 1.0 with the
    n alongside is less misleading than a NaN in a results table.
    """
    pairs = [p for p in pairs if p[0] is not None and p[1] is not None]
    n = len(pairs)
    if n < 2:
        return None
    obs = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    exp = sum((ca[c] / n) * (cb[c] / n) for c in categories)
    if abs(1.0 - exp) < 1e-12:
        return 1.0 if obs == 1.0 else 0.0
    return (obs - exp) / (1.0 - exp)


def weighted_auc(
    scores: Sequence[float],
    labels: Sequence[bool],
    weights: Sequence[float] | None = None,
) -> float | None:
    """Weighted AUC, ties counted as half.

    Pairwise rather than rank-based: the sets here are a few hundred items, the
    cost is irrelevant, and the pairwise form is the definition -- there is no
    tie-correction subtlety to get wrong in it. Returns None unless both
    classes are present.
    """
    w = list(weights) if weights is not None else [1.0] * len(scores)
    pos = [(s, wi) for s, l, wi in zip(scores, labels, w) if l and wi > 0]
    neg = [(s, wi) for s, l, wi in zip(scores, labels, w) if not l and wi > 0]
    if not pos or not neg:
        return None
    num = 0.0
    for sp, wp in pos:
        for sn, wn in neg:
            if sp > sn:
                num += wp * wn
            elif sp == sn:
                num += 0.5 * wp * wn
    den = sum(wp for _, wp in pos) * sum(wn for _, wn in neg)
    return num / den


def band_metrics(rated: Sequence[dict]) -> dict:
    """Per-band precision/recall for `gold_reject`, reweighted to the frame.

    Each row of `rated` is `{band, gold, weight}` with `gold` in {True, False,
    None}; None (a borderline the adjudicator would not force) is carried in
    `n_borderline` and excluded from precision and recall, never silently
    dropped.

    * precision(band) -- of the weight this band caught, how much the
      adjudicator agrees should have been rejected. A band-as-classifier
      reading, which is what "is band 2 real?" actually asks.
    * recall(band) -- of all the weight the adjudicator says should be
      rejected, how much this band caught.
    """
    scored = [r for r in rated if r['gold'] is not None]
    total_pos = sum(r['weight'] for r in scored if r['gold'])
    out: dict[int, dict] = {}
    for band in BANDS:
        sel = [r for r in scored if r['band'] == band]
        w_all = sum(r['weight'] for r in sel)
        w_pos = sum(r['weight'] for r in sel if r['gold'])
        out[band] = {
            'verdict': BAND_VERDICT[band],
            'n': sum(1 for r in rated if r['band'] == band),
            'n_borderline': sum(
                1 for r in rated if r['band'] == band and r['gold'] is None
            ),
            'weight': round(w_all, 4),
            'precision': (w_pos / w_all) if w_all else None,
            'recall': (w_pos / total_pos) if total_pos else None,
        }
    return out


def verdict_metrics(rated: Sequence[dict]) -> dict:
    """Precision/recall/F1 for the deployed reject rule, reweighted.

    The bands are what TASK-719 may re-cut; the *verdict* is what production
    acts on today, so it gets its own line rather than being reconstructed by
    eye from five band rows.
    """
    scored = [r for r in rated if r['gold'] is not None]
    total_pos = sum(r['weight'] for r in scored if r['gold'])
    pred = [r for r in scored if BAND_VERDICT.get(r['band']) == 'reject']
    w_pred = sum(r['weight'] for r in pred)
    w_hit = sum(r['weight'] for r in pred if r['gold'])
    prec = (w_hit / w_pred) if w_pred else None
    rec = (w_hit / total_pos) if total_pos else None
    f1 = (
        2 * prec * rec / (prec + rec)
        if prec is not None and rec is not None and (prec + rec) > 0
        else None
    )
    return {
        'n_scored': len(scored),
        'n_borderline': len(rated) - len(scored),
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'weighted_reject_rate': (w_pred / sum(r['weight'] for r in scored))
        if scored else None,
        'gold_reject_rate': (total_pos / sum(r['weight'] for r in scored))
        if scored else None,
    }


def confusion_by_axis(items: Sequence[dict]) -> dict:
    """Cross-tab of `topical_distance` x `confusable` over labelled items.

    The direct test of TASK-719's premise: if the two axes were redundant this
    table would be diagonal. Every off-diagonal cell -- an `unrelated` item a
    learner still finds confusable, or an `on-topic` one nobody would pick --
    is a question the single 1-5 scale cannot answer.
    """
    tab: dict = defaultdict(int)
    for it in items:
        lab = primary_label(it)
        if lab:
            tab[(lab.get('topical_distance'), lab.get('confusable'))] += 1
    return dict(tab)
