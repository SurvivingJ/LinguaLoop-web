"""knowledge_estimate: the estimator and rules of knowledge-report tech §2 and vocab-placement tech §5.1."""
import math
from datetime import date, timedelta

import pytest

from services.vocabulary import knowledge_estimate as ke

FRAME_JA = [577, 425, 621, 655, 537, 283, 77]
FRAME_ZH = [303, 617, 742, 691, 664, 435, 171]
DE6_JA = [[26, 16, 7], [23, 16, 5], [26, 14, 9], [24, 12, 9], [25, 9, 13], [25, 8, 15], [23, 0, 21]]


# ---------------------------------------------------------------- §2.6 fixture and rows

def test_de6fd05b_ja_fixture():
    e = ke.estimate_range(DE6_JA, FRAME_JA)
    assert e['shown'] and e['kind'] == 'range' and e['label'] == 'medium'
    assert e['T'] == pytest.approx(1110.7, abs=0.5)
    assert e['SD'] == pytest.approx(131.3, abs=0.5)
    assert e['lo'] == pytest.approx(853.3, abs=1) and e['hi'] == pytest.approx(1368.1, abs=1)
    assert e['rel'] == pytest.approx(0.232, abs=0.001)
    assert (e['lo_disp'], e['hi_disp'], e['N']) == (850, 1400, 3175)
    assert e['tick'] == 1111 and e['reason'] is None


def test_per_band_values_match_the_table():
    expected = [(0.231, 0.093), (0.188, 0.091), (0.308, 0.099), (0.333, 0.106), (0.480, 0.108),
                (0.573, 0.103), (0.884, 0.074)]
    for (n, s, c), Nb, (K, sd) in zip(DE6_JA, FRAME_JA, expected):
        k, v = ke.band_stats(n, s, c, Nb)
        assert k == pytest.approx(K, abs=0.001) and math.sqrt(v) == pytest.approx(sd, abs=0.001)


def test_row1_too_few_answers_reports_have():
    bands = [list(r) for r in DE6_JA]
    bands[0] = [9, 5, 3]
    e = ke.estimate_range(bands, FRAME_JA)
    assert not e['shown'] and e['kind'] == 'none' and e['reason'] == 'too_few_answers'
    assert e['have'] == 9 + 10 * 6


def test_row2_out_of_date_when_all_time_counts_pass():
    bands = [[5, 2, 2]] * 7
    e = ke.estimate_range(bands, FRAME_JA, alltime_n=[12] * 7)
    assert e['reason'] == 'out_of_date' and e['have'] is None
    assert ke.estimate_range(bands, FRAME_JA, alltime_n=[12] * 6 + [9])['reason'] == 'too_few_answers'


def test_row3_lo_zero_is_upper_only_and_zh_beginner_fewer_than_510():
    prof = [0, 0, 0, .01, .03, .15, .5]
    bands = [[20, 0, round(20 * (k + (1 - k) * ke.G))] for k in prof]
    e = ke.estimate_range(bands, FRAME_ZH)
    assert e['shown'] and e['kind'] == 'upper_only' and e['label'] == 'low'
    assert e['hi_disp'] == 510 and e['reason'] != 'too_uncertain'


def test_row4_good_needs_30_per_band_and_rel_015():
    bands = [[40, 0, 36]] * 7
    e = ke.estimate_range(bands, FRAME_JA)
    assert e['label'] == 'good' and e['rel'] <= 0.15
    bands29 = [[29, 0, 26]] * 7
    assert ke.estimate_range(bands29, FRAME_JA)['label'] == 'medium'


def test_row6_rough_and_row7_upper_only_and_row8_too_uncertain():
    # row 6: rel' between 0.30 and 0.50 with a positive lower bound
    e6 = ke.estimate_range([[10, 0, 6]] * 7, FRAME_JA)
    assert e6['kind'] == 'range' and e6['label'] == 'low' and 0.30 < e6['rel'] <= 0.50
    # synthetic states for rows 7 and 8: build _estimate inputs directly
    ns = [10] * 7
    Ks = [0.05] * 7
    Vs7 = [0.004] * 7          # small positive lo, rel' > 0.5, hi <= N/2
    e7 = ke._estimate(Ks, Vs7, ns, FRAME_JA, None, 10)
    assert e7['kind'] == 'upper_only' and e7['label'] == 'low' and e7['lo'] == 0.0
    Ks8 = [0.5] * 7
    Vs8 = [0.3] * 7            # rel' ≈ 0.88 with lo > 0 and hi > N/2 → too uncertain
    e8 = ke._estimate(Ks8, Vs8, ns, FRAME_JA, None, 10)
    assert e8['reason'] == 'too_uncertain' and not e8['shown']


def test_row8_answers_needed_example():
    # answers_needed_per_band = ceil(n̄((rel'/0.5)² − 1)) = 32 at rel' 0.8, n̄ 20
    assert math.ceil(20 * ((0.8 / 0.5) ** 2 - 1)) == 32
    ns = [20] * 7
    N = sum(FRAME_JA)
    T = 0.6 * N
    # choose a common variance so that rel' = 0.8 exactly
    SD = 0.8 * T / ke.Z
    V = SD ** 2 / sum(Nb * Nb for Nb in FRAME_JA)
    e = ke._estimate([0.6] * 7, [V] * 7, ns, FRAME_JA, None, 10)
    assert e['reason'] == 'too_uncertain' and e['answers_needed'] == 32


def test_all_skip_and_all_correct_bands_have_nonzero_sd_and_k_is_not_clamped():
    k_skip, v_skip = ke.band_stats(20, 20, 0, 500)
    k_full, v_full = ke.band_stats(20, 0, 20, 500)
    assert v_skip > 0 and v_full > 0 and k_skip == 0 and k_full == 1
    k_neg, _ = ke.band_stats(20, 0, 0, 500)        # all attempted, all wrong
    assert k_neg == pytest.approx(-1 / 3)


def test_hi_uses_max_T_zero():
    bands = [[20, 0, 0]] * 7                        # T negative
    e = ke.estimate_range(bands, FRAME_JA)
    assert e['T'] < 0 and e['kind'] == 'upper_only' and e['hi'] > 0


@pytest.mark.parametrize('x,lo,hi', [(9, 9, 9), (37, 37, 37), (853.3, 850, 860), (1368.1, 1300, 1400),
                                     (3175, 3100, 3200), (12790, 12000, 13000)])
def test_rounding(x, lo, hi):
    assert ke.floor2(x) == lo and ke.ceil2(x) == hi


# ---------------------------------------------------------------- §2.7 groups

def test_groups_fixture():
    g = {r['group']: r for r in ke.group_shares(DE6_JA, FRAME_JA, headline_eligible=True)}
    assert (g['most_common']['share_lo'], g['most_common']['share_hi']) == (0.73, 1.0)
    assert not g['common']['shown'] and g['common']['half_width'] == pytest.approx(0.155, abs=0.001)
    assert (g['mid']['share_lo'], g['mid']['share_hi']) == (0.17, 0.47)
    assert (g['rare']['share_lo'], g['rare']['share_hi']) == (0.08, 0.35)
    assert [r['answers'] for r in g.values()] == [23, 50, 50, 49]
    assert [r['universe'] for r in g.values()] == [77, 820, 1276, 1002]
    assert not any(r['shown'] for r in ke.group_shares(DE6_JA, FRAME_JA, headline_eligible=False))


# ---------------------------------------------------------------- §2.11 skills

REC = [(12, 14), (10, 10), (9, 10), (8, 8), (7, 7), (6, 6), (5, 5), (5, 5), (4, 4), (3, 4), (3, 3), (2, 2),
       (1, 2), (1, 1), (1, 1), (1, 1), (1, 1)]
DIS = [(7, 9), (4, 9), (2, 3), (1, 2), (0, 2), (0, 2), (1, 1), (1, 1), (1, 1), (0, 1), (0, 1)]
PROD = [(18, 23), (12, 14), (0, 6), (3, 3), (1, 3), (2, 2), (2, 2), (0, 1), (0, 1)]


def _families():
    return [dict(family='form_recognition', **ke.sufficient_stats(REC)),
            dict(family='semantic_discrimination', **ke.sufficient_stats(DIS)),
            dict(family='form_production', **ke.sufficient_stats(PROD))]


def test_clustered_wilson_fixture_and_sentence():
    s = ke.family_summary(_families())
    fam = {r['family']: r for r in s['families']}
    rec, dis, prod = fam['form_recognition'], fam['semantic_discrimination'], fam['form_production']
    assert (rec['n'], rec['correct'], rec['meanings']) == (84, 79, 17)
    assert (round(rec['lo'], 2), round(rec['hi'], 2)) == (0.87, 0.97)
    assert (round(dis['lo'], 2), round(dis['hi'], 2)) == (0.35, 0.71)
    assert not prod['shown'] and prod['meanings'] == 9          # 9 of 10 meanings
    assert s['sentence'] == {'weak': 'semantic_discrimination', 'strong': 'form_recognition'}


def test_sentence_needs_separated_intervals():
    fams = [dict(family='a', **ke.sufficient_stats([(2, 3)] * 10)),
            dict(family='b', **ke.sufficient_stats([(2, 3)] * 10))]
    assert ke.family_summary(fams)['sentence'] is None


# ---------------------------------------------------------------- §2.8 next level

def test_next_level():
    levels = [dict(level='N5', rated_known=90, in_dictionary=100), dict(level='N4', rated_known=0, in_dictionary=0),
              dict(level='N3', rated_known=10, in_dictionary=100)]
    assert ke.next_level(levels) == 'N3'
    assert ke.next_level([dict(level='1', rated_known=80, in_dictionary=100)]) is None
    assert ke.next_level([]) is None


# ---------------------------------------------------------------- §2.10 growth

TODAY = date(2026, 12, 31)


def _snap(days_ago, **kw):
    s = dict(snapshot_date=(TODAY - timedelta(days=days_ago)).isoformat(), method_version=ke.METHOD_VERSION,
             rated_known_words=60, frame_bands=FRAME_JA, cal_bands=ke.bands_to_snapshot(DE6_JA))
    s.update(kw)
    return s


def test_anchor_none_young_since_exact():
    assert ke.select_anchor([], TODAY, 30)['first_trend_on'] == TODAY + timedelta(days=14)
    young = ke.select_anchor([_snap(10)], TODAY, 30)
    assert young['anchor'] is None and young['first_trend_on'] == TODAY + timedelta(days=4)
    since = ke.select_anchor([_snap(20)], TODAY, 30)
    assert since['anchor'] is not None and since['since']
    exact = ke.select_anchor([_snap(40), _snap(30), _snap(20)], TODAY, 30)
    assert exact['anchor']['snapshot_date'] == (TODAY - timedelta(days=30)).isoformat() and not exact['since']
    slack = ke.select_anchor([_snap(37), _snap(33)], TODAY, 30)
    assert slack['anchor']['snapshot_date'] == (TODAY - timedelta(days=33)).isoformat()


def test_method_version_mismatch_suppresses_deltas():
    g = ke.growth(dict(rated_known_words=69, d30={}, d90={}), [_snap(30, method_version=0)], TODAY, FRAME_JA)
    assert g['d30']['anchor_date'] is not None and g['d30']['rated_known_delta'] is None


def test_rated_known_delta_and_pool_change():
    snaps = [_snap(30, rated_known_words=50, frame_bands=[x * 2 for x in FRAME_JA])]
    g = ke.growth(dict(rated_known_words=69, d30=dict(practised=41, direct_checks=164, met_in_texts=44)),
                  snaps, TODAY, FRAME_JA)
    assert g['d30']['rated_known_delta'] == 19 and g['d30']['practised'] == 41
    assert g['d30']['pool_changed'] == {'from': 6350, 'to': 3175}
    assert ke.pool_change(_snap(30, frame_bands=[x + 1 for x in FRAME_JA]), FRAME_JA) is None


def test_estimate_comparison_needs_both_eligible_and_says_no_clear_change():
    a = _snap(30)
    assert ke.estimate_change(a, None, FRAME_JA) is None
    assert ke.estimate_change(a, [[5, 2, 2]] * 7, FRAME_JA) is None                  # since-set not eligible
    same = ke.estimate_change(a, DE6_JA, FRAME_JA)
    assert same['verdict'] == 'no_clear_change'
    higher = ke.estimate_change(a, [[30, 0, 29]] * 7, FRAME_JA)
    assert higher['verdict'] == 'higher'


# ---------------------------------------------------------------- §2.13 next steps

def test_next_steps_rule_order_and_limit():
    est = ke.estimate_range([[9, 5, 3]] + DE6_JA[1:], FRAME_JA)
    facts = dict(state=ke.estimate_state(est), estimate=est, prestudy=dict(slug='t1', title='T', unknown=5, n=10),
                 days_since_evidence=10, idle60=95, missed_recently=10)
    steps = ke.next_steps(facts)
    assert [s['key'] for s in steps] == ['knowledge.next.check', 'knowledge.next.prestudy', 'knowledge.next.session']
    assert steps[0]['params']['n'] == 1


def test_next_steps_de6_today_and_refresh_and_stale():
    est = ke.estimate_range(DE6_JA, FRAME_JA)
    steps = ke.next_steps(dict(state=None, estimate=est, days_since_evidence=1, idle60=95, missed_recently=10,
                               last_check_answer_days=4))
    assert [s['key'] for s in steps] == ['knowledge.next.review_practice', 'knowledge.next.take_test']
    steps = ke.next_steps(dict(state=None, estimate=est, days_since_evidence=1, idle60=0, missed_recently=0,
                               last_check_answer_days=61))
    assert [s['key'] for s in steps] == ['knowledge.next.refresh_check', 'knowledge.next.take_test']
    stale = ke.next_steps(dict(state=None, estimate=est, days_since_evidence=40, idle60=10, missed_recently=0,
                               last_check_answer_days=61))
    assert stale[0]['key'] == 'knowledge.next.session'
    e0 = ke.next_steps(dict(state='E0'))
    assert e0[0]['params']['n'] == 70
    assert ke.next_steps(dict(state=None, estimate=est, days_since_evidence=1, reviews_deep_link=True,
                              missed_recently=1))[0]['href'] == '/session?mode=practice&extra=reviews'


def test_prestudy_threshold_is_strictly_above_a_quarter():
    base = dict(state=None, estimate=ke.estimate_range(DE6_JA, FRAME_JA), days_since_evidence=1)
    assert not any(s['key'] == 'knowledge.next.prestudy'
                   for s in ke.next_steps(dict(base, prestudy=dict(slug='x', title='X', unknown=25, n=100))))
    assert any(s['key'] == 'knowledge.next.prestudy'
               for s in ke.next_steps(dict(base, prestudy=dict(slug='x', title='X', unknown=26, n=100))))


# ---------------------------------------------------------------- placement extensions (vocab-placement §5.1)

def test_pair_estimator_equals_adr051_on_identical_inputs():
    pairs = [[n, c, n - s - c] for n, s, c in DE6_JA]          # pc = c, prw = w
    p = ke.estimate_range_pairs(pairs, FRAME_JA)
    e = ke.estimate_range(DE6_JA, FRAME_JA)
    assert p['lo'] == pytest.approx(e['lo']) and p['hi'] == pytest.approx(e['hi'])
    assert (p['lo_disp'], p['hi_disp']) == (850, 1400)


def test_tone_pair_estimator_hand_computed():
    k, v = ke.tone_band_stats(10, 6, 2, 100)
    assert k == pytest.approx(0.4)
    pp, pm = 6.25 / 10.75, 2.25 / 10.75
    assert v == pytest.approx((pp + pm - (pp - pm) ** 2) / 10 * 0.9)
    pairs = [[20, 10, 2, 3]] * 7
    e = ke.estimate_range_tone_pairs(pairs, FRAME_ZH, min_per_band=2)
    assert e['T'] == pytest.approx(0.4 * sum(FRAME_ZH))


def test_zh_gaps_decompose_meaning_on_one_sample():
    # one band, n = 10 words: 4 K, 2 K′, 1 F, 1 IDK after a right meaning, 1 meaning wrong, 1 meaning IDK
    pc, pkt, pf, ridk, mw = 4, 2, 1, 1, 1
    n = 10
    K_m = (pc + pkt + pf + ridk) / n - mw / (3 * n)
    K_mr = (pc - pkt) / n
    K_syl = (pc + pkt - pf) / n
    tone = (2 * pkt - pf) / n
    reading = (2 * pf + ridk - mw / 3) / n
    assert K_m == pytest.approx(K_mr + tone + reading)
    assert K_syl - K_mr == pytest.approx(tone) and K_m - K_syl == pytest.approx(reading)
    frame = [100] * 7
    g = ke.gap_range([(n, [pkt, pf])] * 7, ke.ZH_TONE_GAP_XS, frame)
    assert g['G'] == pytest.approx(7 * 100 * tone)


def test_ja_gap_equals_m_minus_mr_on_identical_sample():
    n, rw, ridk, mw = 20, 4, 2, 3          # reading wrong, reading IDK, meaning wrong (plus pc and IDKs)
    g = ke.gap_range([(n, [rw, ridk, mw])] * 7, ke.JA_GAP_XS, FRAME_JA)
    D = (rw * 4 / 3 + ridk - mw / 3) / n
    assert g['G'] == pytest.approx(D * sum(FRAME_JA))
    with pytest.raises(ValueError):
        ke.gap_range([(2, [2, 1, 0])] * 7, ke.JA_GAP_XS, FRAME_JA)


def test_gap_hidden_when_lower_bound_small():
    g = ke.gap_range([(20, [0, 0, 0])] * 7, ke.JA_GAP_XS, FRAME_JA)
    assert not g['shown'] and g['lo_disp'] is None


def test_guard_direction():
    m = dict(shown=True, kind='range', lo=500.0, hi=1500.0, lo_disp=500, hi_disp=1500)
    mr = dict(shown=True, kind='range', lo=600.0, hi=1600.0, lo_disp=600, hi_disp=1600)
    gm, gmr = ke.apply_guard(m, mr)
    assert gm['lo'] == 600.0 and gm['lo_disp'] == 600 and gmr['hi'] == 1500.0 and gmr['hi_disp'] == 1500
    assert m['lo'] == 500.0                      # inputs untouched


def test_compare_rule():
    a = dict(T=1000.0, SD=100.0)
    assert ke.compare(a, dict(T=1200.0, SD=100.0)) == 'same'
    assert ke.compare(a, dict(T=1300.0, SD=100.0)) == 'up'
    assert ke.compare(a, dict(T=600.0, SD=100.0)) == 'down'
    assert ke.compare(a, dict(T=None, SD=None)) is None


def test_placement_min_per_band_amendment():
    bands = [[3, 1, 1]] * 7
    assert ke.estimate_range(bands, FRAME_JA)['reason'] == 'too_few_answers'
    assert ke.estimate_range(bands, FRAME_JA, min_per_band=ke.PLACEMENT_MIN_PER_BAND)['shown']


def test_shape_is_checked():
    with pytest.raises(ValueError):
        ke.estimate_range(DE6_JA[:6], FRAME_JA)
