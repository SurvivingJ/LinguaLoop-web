"""Static checks of the TASK-1075 migrations and the readiness gate's verdict logic."""
from pathlib import Path

from scripts.placement_readiness_gate import evaluate

M = Path(__file__).resolve().parent.parent / 'migrations'


def _read(name):
    return (M / name).read_text(encoding='utf-8')


def test_pool_refresh_takes_a_language_and_excludes_kana_only_lemmas():
    sql = _read('calibration_pool_refresh_language_and_katakana.sql')
    assert 'DROP FUNCTION IF EXISTS public.calibration_refresh_anchor_pool();' in sql
    assert 'calibration_refresh_anchor_pool(p_word_language_id smallint DEFAULT NULL)' in sql
    assert sql.count("v.lemma !~ '^[ぁ-ゟァ-ヿー・]+$'") == 2
    assert 'WHERE p_word_language_id IS NULL OR word_language_id = p_word_language_id' in sql
    assert 'SET search_path' in sql and "auth.role() <> 'service_role'" in sql
    assert 'REVOKE ALL ON FUNCTION public.calibration_refresh_anchor_pool(smallint) FROM PUBLIC, anon, authenticated' in sql
    rb = _read('calibration_pool_refresh_language_and_katakana_rollback.sql')
    assert 'DROP FUNCTION IF EXISTS public.calibration_refresh_anchor_pool(smallint);' in rb
    assert 'CREATE OR REPLACE FUNCTION public.calibration_refresh_anchor_pool()' in rb


def test_pronunciation_distractors_filters_ja_by_visible_kana():
    sql = _read('pronunciation_distractors_ja_kana_pattern.sql')
    assert "IF p_word_language_id = 3 AND v_lemma ~ '[ぁ-ゟ]' THEN" in sql
    assert "regexp_replace(v_lemma, '[^ぁ-ゟー]+', '.+', 'g')" in sql
    assert 'AND (v_kana_re IS NULL OR c.norm ~ v_kana_re)' in sql
    assert 'AND c.norm <> v_norm' in sql                     # homophones still excluded
    rb = _read('pronunciation_distractors_ja_kana_pattern_rollback.sql')
    assert 'v_kana_re' not in rb


def _counts(ready_shares, frame_n=100, zipf=(4.0, 4.0), len3=(0.2, 0.2)):
    bands = [dict(band=i + 1, frame_n=frame_n, ready_n=int(s * frame_n), ready_mean_zipf=zipf[0],
                  unready_mean_zipf=zipf[1], ready_share_len3=len3[0], unready_share_len3=len3[1])
             for i, s in enumerate(ready_shares)]
    return dict(frame=frame_n * len(ready_shares), ready=sum(b['ready_n'] for b in bands), bands=bands)


def test_gate_verdicts():
    assert evaluate(_counts([0.96] * 7))['pass']
    assert not evaluate(_counts([0.96] * 6 + [0.79]))['pass']                     # one band below 80%
    assert not evaluate(_counts([0.85] * 7))['pass']                              # overall below 90%
    assert not evaluate(_counts([0.92] * 7, zipf=(4.2, 4.0)))['pass']            # unready differ in Zipf
    assert evaluate(_counts([0.97] * 7, zipf=(4.5, 4.0)))['pass']                # < 5% unready: not checked
    assert not evaluate({'frame': 0, 'ready': 0, 'bands': []})['pass']
