"""Unit tests for ``passage_builder.select_window_for_primed`` (TASK-909).

Pure-function tests over synthetic ``test_sentences`` rows + token maps. The
demo's ``chooseWindow`` (wiki/demos/test-prestudy-demo.html) is the reference:
score = primed covered * 10 + wrong covered * 3 - chars / 100, lengths tried
ascending, strict ``>`` so ties keep the shorter / earlier window.
"""

from services.dual_translation.passage_builder import select_window_for_primed


def _build(sentence_tokens):
    """sentence_tokens: list of lists of (surface, sense_id|None). Returns
    (rows, token_map) with contiguous token/char spans."""
    rows, token_map = [], []
    char = 0
    for idx, toks in enumerate(sentence_tokens):
        ts = len(token_map)
        text = ''.join(t[0] for t in toks)
        token_map.extend([list(t) for t in toks])
        rows.append({
            'idx': idx, 'l2_text': text,
            'char_start': char, 'char_end': char + len(text),
            'token_start': ts, 'token_end': len(token_map),
        })
        char += len(text)
    return rows, token_map


# Five demo-like fixtures: short JA-ish sentences with sense ids 1..9.
FIX_A = _build([
    [('趣味', 1), ('で', None), ('手作り', 2), ('。', None)],       # 0: senses 1,2
    [('まず', 3), ('は', None), ('販売', 4), ('。', None)],          # 1: senses 3,4
    [('次に', 5), ('写真', 6), ('。', None)],                        # 2: senses 5,6
    [('最後に', 7), ('価格', 8), ('。', None)],                      # 3: senses 7,8
    [('終わり', 9), ('。', None)],                                   # 4: sense 9
])


def _all_ok(rows, t=0.9):
    idxs = {r['idx'] for r in rows}
    return idxs, {i: t for i in idxs}


class TestScoring:

    def test_picks_range_covering_most_primed_senses(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # primed 5,6,7,8 live in sentences 2-3
        assert select_window_for_primed(rows, [5, 6, 7, 8], [], refs, tight, 0.5, token_map=tm) == (2, 3)

    def test_wrong_senses_break_ties(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # primed 3,4 (sentence 1): windows (0,1) and (1,2) tie on primed; wrong
        # sense 6 in sentence 2 tips it to (1,2).
        assert select_window_for_primed(rows, [3, 4], [6], refs, tight, 0.5, token_map=tm) == (1, 2)

    def test_shorter_window_wins_when_coverage_equal(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # primed 1 only (sentence 0): every window containing 0 scores 10 - chars;
        # the 2-sentence window (0,1) is the shortest.
        assert select_window_for_primed(rows, [1], [], refs, tight, 0.5, token_map=tm) == (0, 1)

    def test_longer_window_when_it_adds_primed_senses(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # primed 1 and 7: sentences 0 and 3 -> needs a 4-window (0..3)
        assert select_window_for_primed(rows, [1, 7], [], refs, tight, 0.5, token_map=tm) == (0, 3)

    def test_no_primed_prefers_shortest_earliest(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # all scores negative (-chars/100); fewest chars wins: (3,4) = 7 chars
        # vs (0,1) = 10, (1,2)= 9, (2,3)= 8.
        assert select_window_for_primed(rows, [], [], refs, tight, 0.0, token_map=tm) == (3, 4)

    def test_explicit_sense_ids_on_rows_bypass_token_map(self):
        rows = [
            {'idx': 0, 'l2_text': 'aaaa', 'sense_ids': [1]},
            {'idx': 1, 'l2_text': 'bbbb', 'sense_ids': [2]},
            {'idx': 2, 'l2_text': 'cccc', 'sense_ids': [3]},
        ]
        refs, tight = _all_ok(rows)
        assert select_window_for_primed(rows, [2, 3], [], refs, tight, 0.5) == (1, 2)


class TestEligibility:

    def test_never_returns_range_with_missing_reference(self):
        rows, tm = FIX_A
        refs = {0, 1, 2, 4}  # sentence 3 has no usable reference
        tight = {i: 0.9 for i in refs}
        # primed senses are all in sentence 3 -> any window with 3 is ineligible;
        # the best eligible window has zero primed coverage and is the shortest.
        result = select_window_for_primed(rows, [7, 8], [], refs, tight, 0.5, token_map=tm)
        assert result is not None
        start, end = result
        assert 3 not in range(start, end + 1)

    def test_retired_reference_excludes_window(self):
        rows, tm = FIX_A
        refs = {2, 3}
        tight = {2: 0.9, 3: 0.9}
        assert select_window_for_primed(rows, [1, 2], [], refs, tight, 0.5, token_map=tm) == (2, 3)

    def test_tightness_floor_excludes_loose_window(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        tight[2] = 0.1
        tight[3] = 0.1
        # (2,3) would win on primed coverage but its mean tightness 0.1 < floor
        result = select_window_for_primed(rows, [5, 6, 7, 8], [], refs, tight, 0.5, token_map=tm)
        assert result != (2, 3)
        assert result is not None

    def test_missing_tightness_ignored_in_mean(self):
        rows, tm = FIX_A
        refs = {r['idx'] for r in rows}
        tight = {0: 0.9}  # only sentence 0 has a recorded tightness
        # (2,3) covers every primed sense but has no recorded tightness -> fails
        # a floor > 0; (0,3) also covers them and its mean over recorded values
        # (just sentence 0: 0.9) passes, so it wins despite being longer.
        assert select_window_for_primed(rows, [5, 6, 7, 8], [], refs, tight, 0.5, token_map=tm) == (0, 3)
        # with a zero floor the unrecorded window is eligible and shorter wins
        assert select_window_for_primed(rows, [5, 6, 7, 8], [], refs, tight, 0.0, token_map=tm) == (2, 3)

    def test_none_when_no_eligible_range(self):
        rows, tm = FIX_A
        assert select_window_for_primed(rows, [1], [], set(), {}, 0.5, token_map=tm) is None

    def test_none_when_too_few_sentences(self):
        rows, tm = _build([[('a', 1), ('。', None)]])
        refs, tight = _all_ok(rows)
        assert select_window_for_primed(rows, [1], [], refs, tight, 0.0, token_map=tm) is None

    def test_respects_max_size(self):
        rows, tm = FIX_A
        refs, tight = _all_ok(rows)
        # primed in sentences 0 and 4 need a 5-window -> capped at 4, so the best
        # 4-window covers one of them; result spans at most 4 sentences.
        start, end = select_window_for_primed(rows, [1, 9], [], refs, tight, 0.5, token_map=tm)
        assert end - start + 1 <= 4
