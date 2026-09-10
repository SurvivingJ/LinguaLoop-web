# services/calibration_service.py
"""Calibration service — build items, record answers, report the ability curve.

Calibration is a measuring instrument, not a lesson. It sits outside session
planning: nothing here writes to ELO, mastery, or weekly plan state directly. See
decision 4 in ``migrations/calibration_sessions_and_ability.sql`` for why — a
measurement that silently moved the thing it measures would be a feedback loop,
not a calibration. The one sanctioned path to the ratings is the hand-off at the
end of a definition-mode run (:func:`apply_calibration_to_ratings`, TASK-752),
which calls the guarded SQL writer and owns none of its policy.

The item shape is: one prompt word, four definitions, exactly one of them right.
The three wrong ones come from ``semantic_distractors()`` (ADR-025), which makes
them semantically near and difficulty-matched rather than random.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Optional

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

#: Options per item. Four is a product constant, not a tunable: the UI, the
#: 1-in-4 guess rate the ability curve assumes, and the over-fetch in
#: semantic_distractors' pool all assume it.
OPTIONS_PER_ITEM = 4
DISTRACTORS_PER_ITEM = OPTIONS_PER_ITEM - 1

#: Chance of a correct answer with no knowledge at all. Fixed, not fitted: with
#: four options it is known a priori, and fitting it as a free parameter on a few
#: dozen responses makes the fit wander badly.
GUESS_RATE = 1.0 / OPTIONS_PER_ITEM

#: log(0.85 / 0.15) — the logit of the 85% knowledge target the ADR-024 contract
#: names. Precomputed because it is a constant of the contract, not of the data.
_LOGIT_85 = math.log(0.85 / 0.15)

#: Below this many answers the curve is not identifiable and the fit returns None
#: rather than a confident-looking number derived from nothing.
MIN_RESPONSES_FOR_FIT = 12

#: Measured standard error of ability_zipf_85, in Zipf points, by answer count.
#:
#: From 60 simulated learners per row (scripts/calibration_estimator_bias.py,
#: --learner logistic, 2026-09-08). The headline finding is that after TASK-764
#: **bias is negligible at every size** (|bias| <= 0.12, mostly <= 0.05) and
#: PRECISION is the binding constraint instead:
#:
#:     items    bias      sd   p90|err|
#:        20  -0.118   0.631      0.95
#:        40  -0.053   0.416      0.57
#:        60  -0.035   0.270      0.43
#:        84  -0.040   0.238      0.39
#:       120  -0.044   0.157      0.26
#:       200  -0.002   0.156      0.26
#:       300  -0.051   0.109      0.20
#:
#: This matters for ADR-024, whose Zipf->ELO mapping the wiki log records as
#: swinging 430 points across plausible definitions: a +-0.27 Zipf standard error
#: at 60 items is not a rounding detail there. Consumers should read
#: `ability_zipf_85_sd` and propagate it rather than treating the point estimate
#: as exact.
_SD_BY_ITEMS = [(20, 0.63), (40, 0.42), (60, 0.27), (84, 0.24),
                (120, 0.16), (200, 0.16), (300, 0.11)]


def expected_sd(answered: int) -> Optional[float]:
    """Expected standard error of ability_zipf_85 at this many answers.

    Linearly interpolated between the measured points above, flat outside them.
    An estimate of the estimate's own precision, not a guarantee.
    """
    if answered < MIN_RESPONSES_FOR_FIT:
        return None
    if answered <= _SD_BY_ITEMS[0][0]:
        return _SD_BY_ITEMS[0][1]
    if answered >= _SD_BY_ITEMS[-1][0]:
        return _SD_BY_ITEMS[-1][1]
    for (n0, sd0), (n1, sd1) in zip(_SD_BY_ITEMS, _SD_BY_ITEMS[1:]):
        if n0 <= answered <= n1:
            span = n1 - n0
            return sd0 + (sd1 - sd0) * ((answered - n0) / span) if span else sd0
    return None


class CalibrationError(Exception):
    """Raised when an item cannot be built or an answer cannot be recorded."""


#: The two item shapes. They are different distractor problems, not a display
#: toggle: 'definition' needs semantic nearness, 'pronunciation' needs
#: audio/orthographic confusability, and they share no picker.
MODE_DEFINITION = 'definition'
MODE_PRONUNCIATION = 'pronunciation'
MODES = (MODE_DEFINITION, MODE_PRONUNCIATION)

#: Languages with enough stored readings to run pronunciation mode. English has
#: 21 senses with a pronunciation out of 6,555 (0.3%), so an English
#: pronunciation run would fail to build almost every item; it is refused at the
#: route rather than silently degrading. zh has 3,890 words and ja 2,385.
PRONUNCIATION_LANGUAGE_IDS = (1, 3)


def start_session(user_id: str, word_language_id: int,
                  definition_language_id: int,
                  mode: str = MODE_DEFINITION) -> dict:
    """Open a calibration session and return it."""
    if mode not in MODES:
        raise CalibrationError(f'unknown calibration mode {mode!r}')
    if mode == MODE_PRONUNCIATION and int(word_language_id) not in PRONUNCIATION_LANGUAGE_IDS:
        raise CalibrationError(
            'pronunciation calibration is available for Chinese and Japanese only')

    db = get_supabase_admin()
    resp = db.table('calibration_sessions').insert({
        'user_id': user_id,
        'word_language_id': int(word_language_id),
        'definition_language_id': int(definition_language_id),
        'mode': mode,
    }).execute()
    if not resp.data:
        raise CalibrationError('could not open calibration session')
    return resp.data[0]


def get_session(user_id: str, session_id: str) -> Optional[dict]:
    """Fetch a session, but only if it belongs to this user.

    The ownership check is here rather than left to RLS because the Flask layer
    talks to Supabase with the service role, which bypasses RLS entirely. Without
    this, a session id from another account would be readable.
    """
    db = get_supabase_admin()
    resp = (db.table('calibration_sessions')
              .select('*')
              .eq('id', session_id)
              .eq('user_id', user_id)
              .limit(1)
              .execute())
    rows = resp.data or []
    return rows[0] if rows else None


def _fetch_distractors(db, anchor: dict, word_language_id: int,
                       definition_language_id: int) -> list[dict]:
    """Semantic distractors for one anchor, with a documented fallback.

    Falls back to the older random picker only when the semantic one cannot fill
    the item. That is a real quality drop — random foils make an item answerable
    by elimination — so it is logged at WARNING rather than passed over. It should
    be rare: over 1,400 sampled items exactly one came up short.
    """
    try:
        rows = db.rpc('semantic_distractors', {
            'p_sense_id': anchor['sense_id'],
            'p_word_language_id': int(word_language_id),
            'p_definition_language_id': int(definition_language_id),
            'p_count': DISTRACTORS_PER_ITEM,
        }).execute().data or []
    except Exception as exc:
        logger.error('semantic_distractors failed for sense %s: %s',
                     anchor['sense_id'], exc)
        rows = []

    options = [{
        'sense_id': r.get('out_sense_id'),
        'vocab_id': r.get('out_vocab_id'),
        'lemma': r.get('out_lemma'),
        'definition': r.get('out_definition'),
        'similarity': r.get('out_similarity'),
        'frequency': r.get('out_frequency'),
        'freq_tier': r.get('out_freq_tier'),
    } for r in rows]

    if len(options) >= DISTRACTORS_PER_ITEM:
        return options[:DISTRACTORS_PER_ITEM]

    logger.warning(
        'semantic_distractors returned %d/%d for sense %s (%s) — falling back to '
        'random foils; this item measures less than it should',
        len(options), DISTRACTORS_PER_ITEM, anchor['sense_id'], anchor.get('lemma'))

    try:
        filler = db.rpc('get_distractors', {
            'p_sense_id': anchor['sense_id'],
            'p_language_id': int(word_language_id),
            'p_count': DISTRACTORS_PER_ITEM - len(options),
            'p_definition_language_id': int(definition_language_id),
        }).execute().data or []
    except Exception as exc:
        logger.error('get_distractors fallback failed for sense %s: %s',
                     anchor['sense_id'], exc)
        filler = []

    seen = {o['definition'] for o in options}
    for row in filler:
        text = (row.get('out_definition') or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        options.append({
            'sense_id': None, 'vocab_id': None, 'lemma': None,
            'definition': text, 'similarity': None,
            'frequency': None, 'freq_tier': None,
        })
    return options[:DISTRACTORS_PER_ITEM]


def _fetch_pronunciation_foils(db, anchor: dict, word_language_id: int) -> list[dict]:
    """Audio/orthographically confusable readings for one anchor.

    A different problem from the semantic case and so a different picker. There is
    no fallback to a random one: a random reading is trivially discardable, and an
    item with random readings would measure nothing while still counting toward
    the ability curve. Better to skip the anchor.
    """
    try:
        rows = db.rpc('pronunciation_distractors', {
            'p_sense_id': anchor['sense_id'],
            'p_word_language_id': int(word_language_id),
            'p_count': DISTRACTORS_PER_ITEM,
        }).execute().data or []
    except Exception as exc:
        logger.error('pronunciation_distractors failed for sense %s: %s',
                     anchor['sense_id'], exc)
        return []

    return [{
        'sense_id': r.get('out_sense_id'),
        'vocab_id': r.get('out_vocab_id'),
        'lemma': r.get('out_lemma'),
        'definition': r.get('out_pronunciation'),   # the rendered option text
        'similarity': None,
        'frequency': r.get('out_frequency'),
        # Reuse freq_tier to carry edit distance, so the response-options table
        # records how close each reading was without needing another column.
        'freq_tier': r.get('out_distance'),
    } for r in rows]


def next_item(user_id: str, session: dict) -> Optional[dict]:
    """Build the next calibration item, persisting what was served.

    Returns None when the language pair has no anchors left for this session.
    The correct answer is recorded server-side and never sent to the client as a
    flag — the client learns which option was right only when it submits one.
    """
    db = get_supabase_admin()
    word_lang = int(session['word_language_id'])
    def_lang = int(session['definition_language_id'])
    mode = session.get('mode') or MODE_DEFINITION

    try:
        rows = db.rpc('calibration_next_anchor', {
            'p_session_id': session['id'],
            'p_word_language_id': word_lang,
            'p_definition_language_id': def_lang,
            'p_mode': mode,
        }).execute().data or []
    except Exception as exc:
        logger.error('calibration_next_anchor failed: %s', exc)
        raise CalibrationError('could not select a word') from exc

    if not rows:
        return None

    r = rows[0]
    anchor = {
        'sense_id': r.get('out_sense_id'),
        'vocab_id': r.get('out_vocab_id'),
        'lemma': r.get('out_lemma'),
        'definition': r.get('out_definition'),
        'pronunciation': r.get('out_pronunciation'),
        'zipf': r.get('out_zipf'),
        'zipf_band': r.get('out_zipf_band'),
    }

    if mode == MODE_PRONUNCIATION:
        distractors = _fetch_pronunciation_foils(db, anchor, word_lang)
        key_text = anchor['pronunciation']
    else:
        distractors = _fetch_distractors(db, anchor, word_lang, def_lang)
        key_text = anchor['definition']

    if not key_text or len(distractors) < DISTRACTORS_PER_ITEM:
        # Came up short. Skip this anchor rather than render a two- or
        # three-option item, which would silently change the guess rate the
        # ability curve is built on — every band's known-share is interpreted
        # against a 1-in-4 floor.
        logger.info('only %d foils for sense %s (%s, mode=%s) — skipping anchor',
                    len(distractors), anchor['sense_id'], anchor.get('lemma'), mode)
        raise CalibrationError('could not build an item for this word')

    response_resp = db.table('calibration_responses').insert({
        'session_id': session['id'],
        'user_id': user_id,
        'anchor_sense_id': anchor['sense_id'],
        'anchor_vocab_id': anchor['vocab_id'],
        'anchor_zipf': anchor['zipf'],
        'zipf_band': anchor['zipf_band'],
    }).execute()
    if not response_resp.data:
        raise CalibrationError('could not record the served item')
    response_id = response_resp.data[0]['id']

    options = [{
        'sense_id': anchor['sense_id'], 'vocab_id': anchor['vocab_id'],
        'definition': key_text, 'is_key': True,
        'similarity': None, 'frequency': anchor['zipf'], 'freq_tier': None,
    }] + [{
        'sense_id': d['sense_id'], 'vocab_id': d['vocab_id'],
        'definition': d['definition'], 'is_key': False,
        'similarity': d['similarity'], 'frequency': d['frequency'],
        'freq_tier': d['freq_tier'],
    } for d in distractors]
    random.shuffle(options)

    db.table('calibration_response_options').insert([{
        'response_id': response_id,
        'sense_id': o['sense_id'] if o['sense_id'] is not None else -(pos + 1),
        'vocab_id': o['vocab_id'] if o['vocab_id'] is not None else -1,
        'is_key': o['is_key'],
        'position': pos,
        'similarity': o['similarity'],
        'frequency': o['frequency'],
        'freq_tier': o['freq_tier'],
    } for pos, o in enumerate(options)]).execute()

    db.table('calibration_sessions').update({
        'items_served': int(session.get('items_served', 0)) + 1,
    }).eq('id', session['id']).execute()
    session['items_served'] = int(session.get('items_served', 0)) + 1

    return {
        'response_id': response_id,
        'lemma': anchor['lemma'],
        # In pronunciation mode the reading IS the answer, so it must not also be
        # shown under the prompt.
        'pronunciation': None if mode == MODE_PRONUNCIATION else anchor['pronunciation'],
        'zipf_band': anchor['zipf_band'],
        'mode': mode,
        # No `is_key` here. The client is told which option was correct only in
        # the answer response.
        'options': [{'position': pos, 'definition': o['definition']}
                    for pos, o in enumerate(options)],
    }


def record_answer(user_id: str, session: dict, response_id: int,
                  position: Optional[int], latency_ms: Optional[int] = None) -> dict:
    """Grade and persist one answer. Returns what the client needs to render feedback.

    `position` may be None, meaning the learner skipped. A skip is recorded as
    incorrect: not knowing is the thing being measured, and dropping skips would
    bias the curve upward.
    """
    db = get_supabase_admin()

    resp = (db.table('calibration_responses')
              .select('id, session_id, user_id, is_correct')
              .eq('id', response_id)
              .eq('user_id', user_id)
              .limit(1)
              .execute())
    rows = resp.data or []
    if not rows:
        raise CalibrationError('unknown item')
    if str(rows[0]['session_id']) != str(session['id']):
        raise CalibrationError('item does not belong to this session')
    if rows[0]['is_correct'] is not None:
        raise CalibrationError('item already answered')

    opt_resp = (db.table('calibration_response_options')
                  .select('sense_id, is_key, position, similarity, frequency, freq_tier')
                  .eq('response_id', response_id)
                  .execute())
    options = opt_resp.data or []
    if not options:
        raise CalibrationError('item has no recorded options')

    key = next((o for o in options if o['is_key']), None)
    chosen = next((o for o in options if o['position'] == position), None) \
        if position is not None else None

    if position is not None and chosen is None:
        raise CalibrationError('no such option')

    is_correct = bool(chosen and chosen['is_key'])

    db.table('calibration_responses').update({
        'chosen_sense_id': chosen['sense_id'] if chosen else None,
        'is_correct': is_correct,
        'latency_ms': latency_ms,
        'answered_at': 'now()',
    }).eq('id', response_id).execute()

    if chosen is not None:
        (db.table('calibration_response_options')
           .update({'was_chosen': True})
           .eq('response_id', response_id)
           .eq('sense_id', chosen['sense_id'])
           .execute())

    db.table('calibration_sessions').update({
        'items_answered': int(session.get('items_answered', 0)) + 1,
        'items_correct': int(session.get('items_correct', 0)) + (1 if is_correct else 0),
    }).eq('id', session['id']).execute()
    session['items_answered'] = int(session.get('items_answered', 0)) + 1
    session['items_correct'] = int(session.get('items_correct', 0)) + (1 if is_correct else 0)

    return {
        'is_correct': is_correct,
        'correct_position': key['position'] if key else None,
        'skipped': position is None,
    }


def _log_likelihood(points: list[tuple[float, bool]], slope: float,
                    midpoint: float) -> float:
    """Log-likelihood of the responses under a guess-floored logistic.

    p(z) = c + (1 - c) * sigma(slope * (z - midpoint)), with c fixed at the
    1-in-4 guess rate. `midpoint` is the Zipf at which *true knowledge* is 0.5,
    so the observed accuracy there is 0.625, not 0.5 — the guess floor lifts the
    whole curve and is exactly what the band-interpolation estimator ignored.
    """
    total = 0.0
    for zipf, correct in points:
        # Guard the exponent: a steep slope far from the midpoint overflows.
        x = slope * (zipf - midpoint)
        if x < -60.0:
            knowledge = 0.0
        elif x > 60.0:
            knowledge = 1.0
        else:
            knowledge = 1.0 / (1.0 + math.exp(-x))
        p = GUESS_RATE + (1.0 - GUESS_RATE) * knowledge
        p = min(max(p, 1e-9), 1.0 - 1e-9)
        total += math.log(p) if correct else math.log(1.0 - p)
    return total


def _fit_ability(points: list[tuple[float, bool]]) -> tuple[Optional[float], Optional[float]]:
    """Maximum-likelihood fit of the knowledge curve. Returns (zipf_85, zipf_50).

    Replaces the piecewise-linear interpolation between band midpoints that
    TASK-764 measured as biased high by ~+0.24 Zipf. Two things change:

    * It fits the RAW responses, so nothing is discretized into 0.5-wide bands.
      The old bias was a discretization artifact — a step in ability falling
      inside a band was smeared into a partial average, and interpolating up to a
      high target landed late.
    * It models the 1-in-4 guess floor explicitly, so "85%" means 85% of words
      genuinely known rather than 85% of items answered right. Those differ by a
      lot near the bottom of the curve, which is where a struggling learner sits.

    Coarse-to-fine grid search rather than gradient descent: the surface is
    two-dimensional and well behaved, a grid cannot diverge or land in a local
    optimum the way an unbounded Newton step can, and at these sizes it costs
    under a millisecond.

    Returns (None, None) when the data cannot identify a curve — too few
    responses, or every answer the same, where the likelihood is maximised by an
    arbitrarily steep slope anywhere outside the observed range.
    """
    if len(points) < MIN_RESPONSES_FOR_FIT:
        return None, None
    outcomes = {correct for _, correct in points}
    if len(outcomes) < 2:
        return None, None

    zipfs = [z for z, _ in points]
    lo, hi = min(zipfs), max(zipfs)
    if hi - lo < 0.5:
        return None, None

    #: A curve flatter than this shows no relationship between word frequency and
    #: whether the learner got it right. The likelihood is then maximised by an
    #: almost-flat logistic whose 85% point sits arbitrarily far away, which is how
    #: a session of random answers produced ability_zipf_85 = 8.43 — a Zipf no word
    #: in the corpus reaches (the maximum is 6.56). Unidentifiable, so report None.
    min_slope = 0.35

    # Slope is searched in log space: the difference between 1.0 and 2.0 matters,
    # the difference between 19 and 20 does not.
    slope_grid = [math.exp(v) for v in
                  [(-0.7 + 0.13 * i) for i in range(28)]]        # ~0.50 .. ~26
    span = hi - lo
    mid_lo, mid_hi = lo - 0.5 * span, hi + 0.5 * span

    def search(slopes: list[float], mids: list[float]) -> tuple[float, float, float]:
        best = (-math.inf, slopes[0], mids[0])
        for slope in slopes:
            for mid in mids:
                ll = _log_likelihood(points, slope, mid)
                if ll > best[0]:
                    best = (ll, slope, mid)
        return best

    coarse_mids = [mid_lo + (mid_hi - mid_lo) * i / 47.0 for i in range(48)]
    _, slope, mid = search(slope_grid, coarse_mids)

    # Refine around the coarse optimum.
    fine_slopes = [slope * math.exp(-0.13 + 0.013 * i) for i in range(21)]
    step = (mid_hi - mid_lo) / 47.0
    fine_mids = [mid - step + (2 * step) * i / 20.0 for i in range(21)]
    best_ll, slope, mid = search(fine_slopes, fine_mids)

    if slope < min_slope:
        return None, None

    # IDENTIFIABILITY. A two-parameter curve can always be bent through noise, and
    # a fit of noise still yields a confident-looking number — a session of random
    # answers produced a midpoint of 3.77 with no frequency relationship in the
    # data at all. So require the curve to beat the null model (one constant
    # accuracy, no dependence on frequency) by more than chance would give. The
    # threshold is a likelihood-ratio test at 2 degrees of freedom: chi-square
    # 5.99 at p=0.05, i.e. a log-likelihood gain of about 3.
    accuracy = sum(1 for _, correct in points if correct) / len(points)
    accuracy = min(max(accuracy, 1e-9), 1.0 - 1e-9)
    null_ll = sum(math.log(accuracy) if correct else math.log(1.0 - accuracy)
                  for _, correct in points)
    if best_ll - null_ll < 3.0:
        return None, None

    # knowledge(z) = 0.5 at the midpoint; = 0.85 at midpoint + logit(0.85)/slope.
    zipf_50 = mid
    zipf_85 = mid + _LOGIT_85 / slope

    # A crossing outside the words actually asked about is an extrapolation, not a
    # measurement. The bound is the OBSERVED range, not the wider search envelope:
    # a learner who got everything right has a crossing somewhere below the easiest
    # word we showed them, and the honest answer is "not measured yet", not a
    # number invented past the edge of the evidence.
    if not (lo <= zipf_85 <= hi):
        zipf_85 = None
    if not (lo <= zipf_50 <= hi):
        zipf_50 = None
    return zipf_85, zipf_50


def _fit_points(db, session_id: str) -> list[tuple[float, bool]]:
    """Raw (zipf, correct) pairs for a session — the fit's input."""
    rows = (db.table('calibration_responses')
              .select('anchor_zipf, is_correct')
              .eq('session_id', session_id)
              .not_.is_('is_correct', 'null')
              .not_.is_('anchor_zipf', 'null')
              .limit(5000)
              .execute().data) or []
    return [(float(r['anchor_zipf']), bool(r['is_correct'])) for r in rows]


def ability(user_id: str, session: dict, fit: bool = True) -> dict:
    """The Zipf knowledge curve and where it crosses.

    `ability_zipf_85` is the statistic the ADR-024 §1.2 contract names: the Zipf
    at which *knowledge* crosses 85%. It is None until the data can identify it —
    an honest "not measured yet" rather than an extrapolation.

    The per-band curve still comes from the SQL RPC, because that is the evidence
    the UI shows. The crossings come from :func:`_fit_ability`, which owns them
    outright: two estimators disagreeing about the headline number would be worse
    than either. Pass ``fit=False`` on the hot path (after every answer) where
    only the running counts are needed.
    """
    db = get_supabase_admin()
    try:
        resp = db.rpc('calibration_ability', {
            'p_session_id': session['id'],
        }).execute()
        report = resp.data or {}
    except Exception as exc:
        logger.error('calibration_ability failed for session %s: %s',
                     session['id'], exc)
        return {'answered': 0, 'correct': 0, 'bands': [],
                'ability_zipf_85': None, 'ability_zipf_50': None,
                'confidence': 'none'}

    if not fit:
        # The RPC's own interpolated crossings are the biased ones. Strip them
        # rather than return a number this function no longer stands behind.
        report['ability_zipf_85'] = None
        report['ability_zipf_50'] = None
        return report

    try:
        zipf_85, zipf_50 = _fit_ability(_fit_points(db, session['id']))
        report['ability_zipf_85'] = zipf_85
        report['ability_zipf_50'] = zipf_50
    except Exception as exc:
        logger.error('ability fit failed for session %s: %s', session['id'], exc)
        report['ability_zipf_85'] = None
        report['ability_zipf_50'] = None

    # Confidence is recomputed here, overriding the RPC's item-count heuristic.
    # The RPC's thresholds were a guess made before the estimator was measured;
    # these are read off the measured standard error, which is the honest basis —
    # bias is negligible at every size, so precision is what "confident" means.
    answered = int(report.get('answered') or 0)
    sd = expected_sd(answered)
    report['ability_zipf_85_sd'] = sd
    if report.get('ability_zipf_85') is None or sd is None:
        report['confidence'] = 'none'
    elif sd > 0.40:
        report['confidence'] = 'low'
    elif sd > 0.20:
        report['confidence'] = 'medium'
    else:
        report['confidence'] = 'good'
    return report


def pooled_ability(user_id: str, language_id: int,
                   mode: str = MODE_DEFINITION) -> dict:
    """Ability pooled over ALL of this user's sessions in one language and mode.

    Pooling rather than reporting the last session, because precision is the
    binding constraint on this estimate and precision is what pooling buys: the
    measured standard error falls from 0.63 Zipf at 20 answers to 0.27 at 60 and
    0.16 at 120. A learner who does three short runs should get the benefit of all
    three, and there is no reason to prefer the most recent one — vocabulary
    knowledge does not decay over the span of a few sessions.

    Modes are pooled separately, never averaged together: 'definition' measures
    vocabulary knowledge and 'pronunciation' measures reading ability, and the
    consumer of this number (test selection) wants the former.
    """
    db = get_supabase_admin()

    sessions = (db.table('calibration_sessions')
                  .select('id')
                  .eq('user_id', user_id)
                  .eq('word_language_id', int(language_id))
                  .eq('mode', mode)
                  .limit(1000)
                  .execute().data) or []
    session_ids = [s['id'] for s in sessions]
    if not session_ids:
        return {'ability_zipf': None, 'ability_se': None, 'items_answered': 0,
                'sessions_pooled': 0, 'bands': []}

    points: list[tuple[float, bool]] = []
    band_counts: dict[int, list[int]] = {}
    for start in range(0, len(session_ids), 50):
        chunk = session_ids[start:start + 50]
        rows = (db.table('calibration_responses')
                  .select('anchor_zipf, is_correct, zipf_band')
                  .in_('session_id', chunk)
                  .not_.is_('is_correct', 'null')
                  .not_.is_('anchor_zipf', 'null')
                  .limit(5000)
                  .execute().data) or []
        for r in rows:
            correct = bool(r['is_correct'])
            points.append((float(r['anchor_zipf']), correct))
            if r.get('zipf_band') is not None:
                slot = band_counts.setdefault(int(r['zipf_band']), [0, 0])
                slot[0] += 1
                slot[1] += 1 if correct else 0

    zipf_85, _zipf_50 = _fit_ability(points)
    return {
        'ability_zipf': zipf_85,
        'ability_se': expected_sd(len(points)) if zipf_85 is not None else None,
        'items_answered': len(points),
        'sessions_pooled': len(session_ids),
        'bands': [{'band': b, 'n': n, 'correct': c,
                   'known_share': round(c / n, 3) if n else None}
                  for b, (n, c) in sorted(band_counts.items())],
    }


def write_calibration_state(user_id: str, language_id: int,
                            mode: str = MODE_DEFINITION) -> Optional[dict]:
    """Persist pooled ability to `user_calibration_state` for test selection.

    This is the whole handoff. Calibration writes the table; selection reads it
    (features/vocabulary-aware-test-selection.tech §1.1). Neither calls the other,
    so this function does not touch `user_skill_ratings`, `get_recommended_tests`
    or `process_test_submission` — ADR-024 §4/§5 put the rating write behind hard
    guards and an audit trail that belong with that writer, not here.

    FAILS CLOSED. If the table is absent the migration has not been applied, and
    this logs and returns None rather than raising: a learner finishing a
    calibration run must not see an error because a downstream integration is not
    switched on yet. Returns None on any write failure for the same reason.
    """
    report = pooled_ability(user_id, language_id, mode)
    if not report['items_answered']:
        return None

    db = get_supabase_admin()
    try:
        db.table('user_calibration_state').upsert({
            'user_id': user_id,
            'language_id': int(language_id),
            'mode': mode,
            'ability_zipf': report['ability_zipf'],
            'ability_se': report['ability_se'],
            'band_accuracies': report['bands'],
            'items_answered': report['items_answered'],
            'sessions_pooled': report['sessions_pooled'],
            'last_run_at': 'now()',
        }, on_conflict='user_id,language_id,mode').execute()
    except Exception as exc:
        logger.warning(
            'user_calibration_state not written for user=%s lang=%s mode=%s (%s). '
            'If this is PGRST205, apply '
            'migrations/calibration_user_state_and_zipf_to_elo.sql — the handoff '
            'to test selection is off until then.',
            user_id, language_id, mode, str(exc)[:160])
        return None
    return report


def apply_calibration_to_ratings(user_id: str,
                                 language_id: int) -> Optional[list]:
    """Hand the freshly published state to the guarded rating writer (TASK-752).

    Every rule — gates G1-G6, seed vs. damped correction, the clamp, the audit
    row — lives in ``apply_calibration_to_skill_ratings`` (TASK-747). Nothing is
    re-checked here, so this cannot bypass a gate. A refusal is a normal outcome:
    it comes back as a ``skipped`` decision naming its gate, and is returned like
    any other so the result view can show it.

    NON-FATAL. Returns None, logged, if the call itself fails — a learner's
    calibration result must never be lost because the rating write could not run.
    """
    db = get_supabase_admin()
    try:
        resp = db.rpc('apply_calibration_to_skill_ratings', {
            'p_user_id': user_id,
            'p_language_id': int(language_id),
        }).execute()
    except Exception as exc:
        logger.warning(
            'apply_calibration_to_skill_ratings failed for user=%s lang=%s (%s); '
            'the calibration result is kept and ratings are unchanged.',
            user_id, language_id, str(exc)[:160])
        return None
    data = resp.data if isinstance(resp.data, dict) else {}
    decisions = data.get('decisions')
    return list(decisions) if isinstance(decisions, list) else []


def end_session(user_id: str, session: dict) -> dict:
    """Close a session, publish pooled ability, and return the final report."""
    db = get_supabase_admin()
    db.table('calibration_sessions').update({
        'ended_at': 'now()',
    }).eq('id', session['id']).eq('user_id', user_id).execute()

    report = ability(user_id, session)

    # Publish AFTER the session is closed so its answers are included in the pool.
    # Best-effort by design: the learner's result is already computed and must not
    # depend on a downstream integration being live.
    language_id = int(session['word_language_id'])
    mode = session.get('mode') or MODE_DEFINITION
    pooled = write_calibration_state(user_id, language_id, mode)
    if pooled:
        report['pooled'] = {
            'ability_zipf': pooled['ability_zipf'],
            'ability_se': pooled['ability_se'],
            'items_answered': pooled['items_answered'],
            'sessions_pooled': pooled['sessions_pooled'],
        }
        # Once, and only after the state write has landed. Definition mode only:
        # the writer reads the 'definition' row, so a pronunciation run changes
        # nothing it could act on.
        if mode == MODE_DEFINITION:
            decisions = apply_calibration_to_ratings(user_id, language_id)
            if decisions is not None:
                report['rating_decisions'] = decisions
    return report
