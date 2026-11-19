"""placement_design: warm-up, allocation, stopping, eligibility, groups and result estimates
(vocab-placement tech §5–§8, §19)."""
import random

import pytest

from services import placement_design as pd
from services.vocabulary import knowledge_estimate as ke

FRAME_ZH = [303, 617, 742, 691, 664, 435, 171]
FRAME_JA = [577, 425, 621, 655, 537, 283, 77]
ZH, EN, JA = pd.LANG_ZH, pd.LANG_EN, pd.LANG_JA


def _tallies(m=None, mr=None, scored=0, active_ms=0, warmup=None, zh=False):
    m = m or [[0, 0, 0] for _ in range(7)]
    if mr is None:
        mr = [[0, 0, 0, 0] if zh else [0, 0, 0] for _ in range(7)]
    t = dict(m=m, mr=mr, scored=scored, active_ms=active_ms)
    if warmup is not None:
        t['warmup_done'] = warmup
    return t


def test_warmup_first_pass_is_commonest_first_and_covers_every_band_twice():
    order = pd.warmup_order(random.Random(1))
    assert order[:7] == [7, 6, 5, 4, 3, 2, 1]
    assert sorted(order) == sorted(list(range(1, 8)) * 2)


def test_warmup_sequence_follows_the_order():
    rng = random.Random(3)
    order = pd.warmup_order(random.Random(9))
    t = _tallies()
    seen = []
    for _ in range(14):
        b = pd.next_band(t, FRAME_ZH, EN, rng, order=order)
        seen.append(b)
        t['m'][b - 1][0] += 1
    assert seen == order
    assert pd.warmup_done(t)


def test_warmup_skips_bands_without_ready_words():
    t = _tallies()
    avail = [True] * 6 + [False]
    assert pd.next_band(t, FRAME_ZH, EN, random.Random(0), available=avail) == 6


def test_allocation_picks_the_largest_delta_hand_computed():
    # after warm-up: band 4 has the most uncertain share and the biggest frame weight among equals
    m = [[2, 0, 0], [2, 0, 0], [2, 1, 1], [2, 1, 1], [2, 2, 0], [2, 2, 0], [2, 2, 0]]
    t = _tallies(m=m, scored=14)
    units = [pd._m_unit(r) for r in m]
    var = pd.total_sd(units, FRAME_ZH) ** 2
    deltas = [pd._delta(units, FRAME_ZH, h, var) for h in range(7)]
    best = max(range(7), key=lambda h: deltas[h]) + 1
    assert pd.next_band(t, FRAME_ZH, EN, random.Random(0)) == best


def test_allocation_adds_the_reading_term_for_cjk_and_skips_exhausted_bands():
    m = [[2, 1, 1]] * 7
    mr = [[2, 0, 0, 0]] * 3 + [[2, 1, 1, 0]] + [[2, 0, 0, 0]] * 3
    t = _tallies(m=[list(r) for r in m], mr=[list(r) for r in mr], scored=20, zh=True)
    b = pd.next_band(t, FRAME_ZH, ZH, random.Random(0))
    assert 1 <= b <= 7
    avail = [False] * 7
    assert pd.next_band(t, FRAME_ZH, ZH, random.Random(0), available=avail) is None
    avail[1] = True
    assert pd.next_band(t, FRAME_ZH, ZH, random.Random(0), available=avail) == 2


def test_stop_reasons_cap_time_precision():
    m = [[9, 4, 3]] * 7
    assert pd.should_stop(_tallies(m=m, scored=60), FRAME_ZH, ZH) == 'cap'
    assert pd.should_stop(_tallies(m=m, scored=61), FRAME_JA, JA) == 'cap'
    assert pd.should_stop(_tallies(m=m, scored=39), FRAME_ZH, ZH) is None
    assert pd.should_stop(_tallies(m=m, scored=30, active_ms=540_000), FRAME_ZH, ZH) == 'time'
    assert pd.should_stop(_tallies(m=m, scored=60), FRAME_ZH, ZH, pending_reading=True) is None
    # en: cap 40, earliest stop 20
    assert pd.should_stop(_tallies(m=m, scored=40), FRAME_ZH, EN) == 'cap'


def test_precision_exit_needs_both_sds_for_cjk():
    m = [[40, 0, 40]] * 7                      # all known: tiny meaning SD
    mr_wide = [[2, 1, 1, 0]] * 7
    mr_tight = [[40, 40, 0, 0]] * 7
    assert pd.should_stop(_tallies(m=m, mr=mr_wide, scored=45, zh=True), FRAME_ZH, ZH) is None
    assert pd.should_stop(_tallies(m=m, mr=mr_tight, scored=45, zh=True), FRAME_ZH, ZH) == 'precision'
    assert pd.should_stop(_tallies(m=m, scored=20), FRAME_ZH, EN) == 'precision'


def test_may_start_new_word_and_end_now():
    t = _tallies(scored=59)
    assert pd.may_start_new_word(t, ZH) and not pd.may_start_new_word(_tallies(scored=60), ZH)
    assert not pd.may_start_new_word(_tallies(scored=10, active_ms=540_000), ZH)
    m2 = [[2, 1, 1]] * 7
    assert not pd.can_end_now(_tallies(m=m2, scored=19))
    assert pd.can_end_now(_tallies(m=m2, scored=20))
    assert pd.needed_for_result(_tallies(m=m2, scored=19)) == 1
    assert pd.needed_for_result(_tallies(m=[[1, 1, 0]] + [[2, 1, 1]] * 6, scored=25)) == 1


@pytest.mark.parametrize('scored,expected', [(19, False), (20, True), (30, True), (45, True)])
def test_end_now_eligibility(scored, expected):
    t = _tallies(m=[[2, 1, 1]] * 7, scored=scored)
    assert pd.eligible(t, 'learner') is expected
    assert pd.eligible(t, 'abandoned') is expected


def test_complete_stop_eligibility_needs_two_per_band():
    assert pd.eligible(_tallies(m=[[2, 1, 1]] * 7, scored=60), 'cap')
    assert not pd.eligible(_tallies(m=[[1, 1, 0]] + [[2, 1, 1]] * 6, scored=60), 'exhausted')
    assert not pd.eligible(_tallies(m=[[2, 1, 1]] * 7, scored=60), None)


def test_active_time_and_minutes_left():
    assert pd.active_ms([5000, 70000, -3]) == 65000
    assert pd.minutes_left(_tallies(), ZH) == 7 and pd.minutes_left(_tallies(), EN) == 5
    t = _tallies(scored=30, active_ms=210_000)   # 7 s per item, 30 left → 210 s → 4 min
    assert pd.minutes_left(t, ZH) == 4
    t = _tallies(scored=30, active_ms=500_000)   # capped by the 540 s time cap
    assert pd.minutes_left(t, ZH) == 1


def test_fast_flag():
    assert pd.is_fast(700, 10) and not pd.is_fast(700, 9) and not pd.is_fast(900, 30)


def test_word_groups_zh_ja_en():
    words = [dict(vocab_id=1, meaning='right', reading_ready=True, reading='K'),
             dict(vocab_id=2, meaning='right', reading_ready=True, reading='KT'),
             dict(vocab_id=3, meaning='right', reading_ready=True, reading='F'),
             dict(vocab_id=4, meaning='right', reading_ready=True, reading='idk'),
             dict(vocab_id=5, meaning='idk'), dict(vocab_id=6, meaning='wrong')]
    zh = pd.word_groups(words, ZH)
    assert zh['counts'] == dict(asked=6, both=1, tones_not_yet=1, meaning_only=2, not_yet=2)
    assert zh['vocab_ids']['tones_not_yet'] == [2]
    ja = pd.word_groups([dict(vocab_id=1, meaning='right', reading_ready=False),
                         dict(vocab_id=2, meaning='right', reading_ready=True, reading='wrong')], JA)
    assert ja['counts'] == dict(asked=2, both=1, meaning_only=1, not_yet=0)
    en = pd.word_groups([dict(vocab_id=1, meaning='right'), dict(vocab_id=2, meaning='idk')], EN)
    assert en['counts'] == dict(asked=2, both=1, not_yet=1)


def test_estimates_ja_and_zh_shapes_and_guard():
    bands = [[20, 6, 10]] * 7
    ja = pd.estimates(dict(bands=bands, pairs=[[20, 8, 2]] * 7, gap=[[20, 2, 0, 4]] * 7), FRAME_JA, JA,
                      min_per_band=2)
    assert ja['m']['shown'] and ja['mr']['shown']
    assert ja['m']['lo'] >= ja['mr']['lo'] and ja['mr']['hi'] <= ja['m']['hi']
    zh = pd.estimates(dict(bands=bands, pairs=[[20, 7, 1, 2]] * 7, gap=[[20, 2, 0, 4, 1]] * 7), FRAME_ZH, ZH,
                      min_per_band=2)
    assert zh['mr']['T'] == pytest.approx(sum(FRAME_ZH) * 6 / 20)
    assert zh['tone_gap']['G'] == pytest.approx(sum(FRAME_ZH) * (2 * 1 - 2) / 20)
    en = pd.estimates(dict(bands=bands), FRAME_JA, EN, min_per_band=2)
    assert en['mr'] is None and en['display']['mr'] is None and en['display']['m'] is not None
    assert pd.headline(en, EN) is en['m'] and pd.headline(zh, ZH) is zh['mr']


def test_retake_verdicts():
    assert pd.retake_verdict(dict(T=1000.0, SD=100.0), dict(T=1400.0, SD=100.0)) == 'clearly_up'
    assert pd.retake_verdict(dict(T=1000.0, SD=100.0), dict(T=1100.0, SD=100.0)) == 'not_clearly_different'
    assert pd.retake_verdict(None, dict(T=1.0, SD=1.0)) is None


def test_probe_rules_and_budgets():
    left = lambda k: 2  # noqa: E731
    assert pd.probe_kind_for(0.10, event='meaning_idk', language_id=ZH, budget_left=4, kind_left=left) == 'forced_guess'
    assert pd.probe_kind_for(0.20, event='meaning_idk', language_id=ZH, budget_left=4, kind_left=left) == 'reading_after_miss'
    assert pd.probe_kind_for(0.20, event='meaning_idk', language_id=EN, budget_left=4, kind_left=left) is None
    assert pd.probe_kind_for(0.40, event='reading_right', language_id=JA, budget_left=4, kind_left=left,
                             sound_pair_available=True) == 'sound_pair'
    assert pd.probe_kind_for(0.40, event='reading_right', language_id=ZH, budget_left=4, kind_left=left,
                             sound_pair_available=True) is None              # zh has no sound pair (ADR-060)
    assert pd.probe_kind_for(0.01, event='meaning_idk', language_id=ZH, budget_left=0, kind_left=left) is None
    assert pd.probe_kind_for(0.01, event='meaning_idk', language_id=ZH, budget_left=3,
                             kind_left=lambda k: 0 if k == 'forced_guess' else 2) == 'reading_after_miss'


def test_config_values():
    assert pd.CONFIG['cap'] == {'cjk': 60, 'en': 40} and pd.CONFIG['time_cap_s'] == 540
    assert pd.CONFIG['version'] == 1 and ke.TONE_PSEUDO_COUNT == 0.25
