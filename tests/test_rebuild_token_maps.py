"""TASK-779: the write/refuse decision for rebuilding drifted token maps."""

import pytest

pytest.importorskip('scripts.sense_linking_common')

from scripts.rebuild_token_maps import assess_rebuild, is_default_target, map_sense_ids

TEXT = 'シャツのデザイン。'


def test_map_sense_ids_skips_zero_and_malformed():
    assert map_sense_ids([['a', 0], ['b', 5], ['c'], None, ['d', '7'], ['e', 5]]) == {5}


def test_dangling_repair_is_written():
    old = [['シャツ', 999], ['の', 0], ['デザイン', 12], ['。', 0]]
    new = [['シャツ', 11], ['の', 0], ['デザイン', 12], ['。', 0]]
    r = assess_rebuild(old, new, TEXT, live_sense_ids={11, 12})
    assert r['verdict'] == 'write'
    assert (r['dangling_before'], r['dangling_after']) == (1, 0)
    assert (r['live_links_before'], r['live_links_after']) == (1, 2)


def test_identical_rebuild_is_not_written():
    same = [['シャツ', 11], ['の', 0], ['デザイン', 12], ['。', 0]]
    r = assess_rebuild(same, [list(e) for e in same], TEXT, {11, 12})
    assert r['verdict'] == 'unchanged'


def test_losing_a_working_link_is_refused_unless_allowed():
    old = [['シャツ', 11], ['の', 0], ['デザイン', 12], ['。', 0]]
    new = [['シャツ', 11], ['の', 0], ['デザイン', 0], ['。', 0]]
    assert assess_rebuild(old, new, TEXT, {11, 12})['verdict'] == 'refuse:would_unlink'
    assert assess_rebuild(old, new, TEXT, {11, 12}, allow_loss=True)['verdict'] == 'write'


def test_map_that_does_not_reproduce_transcript_is_refused():
    new = [['シャツ', 11], ['デザイン', 12], ['。', 0]]  # dropped 'の'
    r = assess_rebuild([], new, TEXT, {11, 12}, allow_loss=True)
    assert r['verdict'] == 'refuse:transcript_mismatch'


def test_rebuild_no_less_faithful_than_current_map_is_allowed():
    # The ja processor drops '\n': both maps lose it, so the rebuild is no worse.
    text = 'シャツ。\nデザイン'
    old = [['シャツ', 999], ['。', 0], ['デザイン', 12]]
    new = [['シャツ', 11], ['。', 0], ['デザイン', 12]]
    r = assess_rebuild(old, new, text, {11, 12})
    assert r['verdict'] == 'write'
    assert r['text_faithful'] is False


def test_rebuild_still_pointing_at_a_deleted_sense_is_refused():
    new = [['シャツ', 999], ['の', 0], ['デザイン', 12], ['。', 0]]
    assert assess_rebuild([], new, TEXT, {12})['verdict'] == 'refuse:dangling_after'


def test_default_targets():
    live = {11, 12}
    assert is_default_target({'vocab_token_map': [['x', 999]], 'vocab_sense_ids': [11]}, live)
    assert is_default_target({'vocab_token_map': None, 'vocab_sense_ids': [11]}, live)
    assert not is_default_target({'vocab_token_map': [['x', 11]], 'vocab_sense_ids': [11]}, live)
    assert not is_default_target({'vocab_token_map': None, 'vocab_sense_ids': []}, live)
